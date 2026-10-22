import copy
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import badges  # noqa: E402
import build  # noqa: E402
import feeds  # noqa: E402
from games import GAMES  # noqa: E402

ATOM = "{http://www.w3.org/2005/Atom}"
SVG = "{http://www.w3.org/2000/svg}"


def payload(at, version="2.5", verdict="Just patched, wait", cet="Just patched, wait"):
    return {"generated_at": at, "verdict": verdict,
            "game": {"slug": "cyberpunk-2077", "name": "Cyberpunk 2077",
                     "latest_patch": {"version": version, "label": f"Patch {version}",
                                      "published_at": "2026-10-22T10:00:00Z", "url": "https://example.com/p"}},
            "frameworks": [{"short": "CET", "tracked": True, "sensitive": True, "status": cet, "release_tag": "v1.38.0"}]}


class TestVerdictLog(unittest.TestCase):
    def test_appends_only_on_change(self):
        log = feeds.append_verdict_log([], payload("2026-10-22T12:00:00Z"))
        self.assertEqual(len(log), 1)
        same = feeds.append_verdict_log(log, payload("2026-10-22T18:00:00Z"))
        self.assertEqual(same, log)
        changed = feeds.append_verdict_log(log, payload("2026-10-22T19:00:00Z", verdict="Breakage reported"))
        self.assertEqual(len(changed), 2)
        self.assertEqual(log[0], changed[0])  # history never rewritten

    def test_skips_no_data_and_trims(self):
        log = feeds.append_verdict_log([], payload("2026-10-22T12:00:00Z", verdict="No data"))
        self.assertEqual(log, [])
        for i in range(feeds.LOG_MAX + 10):
            log = feeds.append_verdict_log(log, payload(f"2026-10-{1 + i // 24:02d}T{i % 24:02d}:00:00Z", version=f"1.{i}"))
        self.assertEqual(len(log), feeds.LOG_MAX)

    def test_pure(self):
        prev = feeds.append_verdict_log([], payload("2026-10-22T12:00:00Z"))
        snap = copy.deepcopy(prev)
        feeds.append_verdict_log(prev, payload("2026-10-22T13:00:00Z", verdict="Safe"))
        self.assertEqual(prev, snap)


class TestFeeds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games_data = build.load_games()

    def parse(self, text):
        root = ET.fromstring(text.encode("utf-8"))
        self.assertEqual(root.tag, ATOM + "feed")
        for req in ("id", "title", "updated", "author"):
            self.assertIsNotNone(root.find(ATOM + req), req)
        self.assertTrue(any(l.get("rel") == "self" for l in root.findall(ATOM + "link")))
        return root

    def check_entries(self, root):
        ids = []
        for e in root.findall(ATOM + "entry"):
            for req in ("id", "title", "updated", "link", "content"):
                self.assertIsNotNone(e.find(ATOM + req), req)
            eid = e.find(ATOM + "id").text
            self.assertRegex(eid, r"^tag:modsafe\.app,2026:[a-z0-9-]+/")
            self.assertRegex(e.find(ATOM + "updated").text, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
            ids.append(eid)
        self.assertEqual(len(ids), len(set(ids)), "duplicate entry ids")
        return ids

    def test_site_feed_valid_and_stable(self):
        a = feeds.site_feed(self.games_data, build.SITE_URL)
        b = feeds.site_feed(copy.deepcopy(self.games_data), build.SITE_URL)
        self.assertEqual(a, b, "feed output must be deterministic")
        ids = self.check_entries(self.parse(a))
        self.assertTrue(ids)
        self.assertLessEqual(len(ids), feeds.SITE_FEED_MAX)

    def test_every_game_feed(self):
        for g, d in self.games_data:
            root = self.parse(feeds.game_feed(g, d, build.SITE_URL))
            ids = self.check_entries(root)
            self.assertTrue(ids, g["slug"])
            self.assertTrue(all(i.startswith(f"tag:modsafe.app,2026:{g['slug']}/") for i in ids))

    def test_ids_survive_new_event(self):
        g, d = self.games_data[0]
        before = set(re.findall(r"<id>(tag:[^<]+)</id>", feeds.game_feed(g, d, build.SITE_URL)))
        d2 = copy.deepcopy(d)
        d2["verdict_log"] = feeds.append_verdict_log(d2.get("verdict_log") or [],
                                                     dict(d2, generated_at="2099-01-01T00:00:00Z", verdict="Breakage reported"
                                                          if d2.get("verdict") != "Breakage reported" else "Safe"))
        after = set(re.findall(r"<id>(tag:[^<]+)</id>", feeds.game_feed(g, d2, build.SITE_URL)))
        self.assertTrue(before & after, "old entry ids must not change")


class TestBadges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games_data = build.load_games()

    def test_badge_for_every_game(self):
        self.assertEqual(len(self.games_data), len(GAMES))
        for g, d in self.games_data:
            cls = build.status_class(d["verdict"])
            svg = badges.game_badge(g, d, cls)
            root = ET.fromstring(svg.encode("utf-8"))
            self.assertEqual(root.tag, SVG + "svg", g["slug"])
            self.assertIn(d["verdict"], svg)
            self.assertIn(badges.COLORS.get(cls, badges.COLORS["unknown"]), svg, g["slug"])
            self.assertEqual(root.get("role"), "img")

    def test_shields_endpoint(self):
        for g, d in self.games_data:
            e = build.shields_endpoint(g, d)
            self.assertEqual(e["schemaVersion"], 1)
            self.assertEqual(e["message"], d["verdict"])
            self.assertRegex(e["color"], r"^[0-9a-f]{6}$")
            json.dumps(e)

    def test_snippets(self):
        for g in GAMES:
            sn = badges.embed_snippets(g, build.SITE_URL)
            url = f"{build.SITE_URL}/badge/{g['slug']}.svg"
            for k in ("markdown", "html"):
                self.assertIn(url, sn[k])
            self.assertIn("raster.shields.io/endpoint?url=", sn["bbcode"])
            self.assertIn(f"badge%2F{g['slug']}.json", sn["bbcode"])


class TestPagesAndHeaders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games_data = build.load_games()

    def test_game_page_links(self):
        g, d = next((g, d) for g, d in self.games_data if g["slug"] == "cyberpunk-2077")
        page = build.build_game_page(g, d)
        self.assertIn('type="application/atom+xml"', page)
        self.assertIn(f"{build.SITE_URL}/cyberpunk-2077/feed.xml", page)
        self.assertIn(f"{build.SITE_URL}/feed.xml", page)
        self.assertIn('id="follow"', page)
        self.assertIn("/badge/cyberpunk-2077.svg", page)
        self.assertIn("MonitoRSS", page)
        self.assertIn('class="copy"', page)
        self.assertNotRegex(page.lower(), r"type=\"email\"|<form")

    def test_faq_mentions_feeds(self):
        faq = build.build_faq() if build.build_faq.__code__.co_argcount == 0 else build.build_faq(self.games_data)
        self.assertIn("feed.xml", faq)
        self.assertIn("MonitoRSS", faq)

    def test_headers(self):
        h = build.HEADERS
        self.assertIn("/feed.xml\n  Content-Type: application/atom+xml; charset=utf-8", h)
        self.assertIn("/:slug/feed.xml\n  Content-Type: application/atom+xml; charset=utf-8", h)
        self.assertIn("/badge/*", h)

    def test_llms_txt(self):
        txt = build.build_llms_txt(self.games_data)
        self.assertIn("/feed.xml", txt)
        self.assertIn("/badge/", txt)


if __name__ == "__main__":
    unittest.main()
