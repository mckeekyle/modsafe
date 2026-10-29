import html as html_mod
import json
import re
import sys
import unittest
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build  # noqa: E402
import guides  # noqa: E402
import patches  # noqa: E402
from games import GAMES_BY_SLUG  # noqa: E402

NOW = datetime(2026, 10, 29, 20, 0, tzinfo=timezone.utc)


def fake(slug, verdict, latest, history, log=()):
    g = GAMES_BY_SLUG[slug]
    data = {"verdict": verdict, "game": {"latest_patch": latest}, "history": history, "verdict_log": list(log),
            "frameworks": [], "reason": ""}
    return g, data


def patch(label, at, url="https://example.com/notes"):
    return {"label": label, "version": label, "published_at": at, "url": url, "title": f"Patch {label}"}


class Hrefs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])


class TestCollect(unittest.TestCase):
    def setUp(self):
        new = patch("1.2", "2026-10-28T10:00:00Z")
        old = patch("1.1", "2026-10-10T10:00:00Z")
        older = patch("1.0", "2025-01-01T10:00:00Z")  # outside the 12-month window
        log = [{"at": "2026-10-20T00:00:00Z", "patch": "1.1", "patch_key": "1.1", "verdict": "Likely safe", "frameworks": {}}]
        self.gd = [fake("valheim", "Just patched, wait", new, [new, old, older], log),
                   fake("elden-ring", "Safe", patch("1.17", "2026-10-20T00:00:00Z"), [patch("1.17", "2026-10-20T00:00:00Z")])]

    def test_newest_first_and_window(self):
        items = patches.collect_patches(self.gd, now=NOW)
        self.assertEqual([(i["game"]["slug"], i["label"]) for i in items],
                         [("valheim", "1.2"), ("elden-ring", "1.17"), ("valheim", "1.1")])

    def test_current_and_superseded(self):
        items = patches.collect_patches(self.gd, now=NOW)
        cur = [i for i in items if i["current"]]
        self.assertEqual({i["game"]["slug"] for i in cur}, {"valheim", "elden-ring"})
        self.assertEqual(items[0]["verdict"], "Just patched, wait")
        old = items[2]
        self.assertFalse(old["current"])
        self.assertEqual(old["superseded_by"], "1.2")
        self.assertEqual(old["verdict"], "Likely safe")  # last logged verdict for 1.1

    def test_limit_and_counts(self):
        items = patches.collect_patches(self.gd, now=NOW, limit=2)
        self.assertEqual(len(items), 2)
        c = patches.counts(patches.collect_patches(self.gd, now=NOW), NOW)
        self.assertEqual(c, {"7d": 1, "30d": 3})

    def test_formats(self):
        dt = datetime(2026, 10, 28, 10, 54, tzinfo=timezone.utc)
        self.assertEqual(patches.fmt_utc(dt), "Oct 28, 2026 · 10:54 UTC")
        self.assertEqual(patches.fmt_hst(dt), "12:54 AM HST, Oct 28")

    def test_page_render(self):
        html = build.build_patches_page(self.gd, now=NOW)
        self.assertIn("<h1>Every patch. <em>Every game.</em></h1>", html)
        self.assertIn('href="https://example.com/notes"', html)
        self.assertEqual(html.count("pt-row "), 3)
        self.assertIn('<link rel="canonical" href="https://modsafe.app/patches/"', html)
        self.assertIn("/og/patches.png", html)
        self.assertIn("Valheim: Just patched, wait", html)  # hold-the-update chip
        self.assertNotRegex(html, r"(?i)subscribe|newsletter|beehiiv")
        lds = [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
        self.assertIn("ItemList", [d.get("@type") for d in lds])
        self.assertIn("BreadcrumbList", [d.get("@type") for d in lds])


class TestRollbackCallout(unittest.TestCase):
    def test_only_wait_or_broken_steam_games(self):
        g = GAMES_BY_SLUG["valheim"]
        self.assertIn(guides.STEAM_GUIDE_PATH + "#rollback", build.rollback_callout(g, {"verdict": "Just patched, wait"}))
        self.assertIn(guides.branch_summary("valheim"), html_mod.unescape(build.rollback_callout(g, {"verdict": "Breakage reported"})))
        self.assertEqual(build.rollback_callout(g, {"verdict": "Safe"}), "")
        self.assertEqual(build.rollback_callout(g, {"verdict": "Likely safe"}), "")
        self.assertEqual(build.rollback_callout(GAMES_BY_SLUG["steam-deck"], {"verdict": "Just patched, wait"}), "")
        self.assertEqual(build.rollback_callout(GAMES_BY_SLUG["minecraft"], {"verdict": "Just patched, wait"}), "")

    def test_guide_anchors_exist(self):
        html = guides.build_steam_guide() if hasattr(guides, "build_steam_guide") else None
        dist = ROOT / "dist" / guides.STEAM_GUIDE_PATH.strip("/") / "index.html"
        text = html or (dist.read_text() if dist.exists() else None)
        if text is None:
            self.skipTest("guide not built")
        for anchor in ("branches", "rollback", "backup", "wait-until-launch"):
            self.assertIn(f'id="{anchor}"', text)


class TestSiteWiring(unittest.TestCase):
    def test_nav_sitemap_llms(self):
        self.assertIn('href="/patches/"', build.nav("home"))
        self.assertIn('aria-current="page">Patches', build.nav("patches"))
        self.assertIn("/patches/", build.sitemap_urls())
        self.assertIn('href="/patches/"', build.footer())
        self.assertIn("https://modsafe.app/patches/", build.build_llms_txt(build.load_games()))

    def test_built_page_links_resolve(self):
        dist = ROOT / "dist"
        page = dist / "patches" / "index.html"
        if not page.exists():
            self.skipTest("dist not built")
        p = Hrefs()
        p.feed(page.read_text())
        missing = []
        for h in p.hrefs:
            if h.startswith("/") and not h.startswith("//"):
                path = h.split("#")[0].split("?")[0]
                f = dist / path.lstrip("/")
                if not (f.is_file() or (f / "index.html").is_file()):
                    missing.append(h)
        self.assertEqual(missing, [])
        self.assertIn("https://modsafe.app/patches/", (dist / "sitemap.xml").read_text())
        self.assertIn('href="/patches/"', (dist / "index.html").read_text())

    def test_real_data_current_rows_match_verdicts(self):
        gd = build.load_games()
        items = patches.collect_patches(gd)
        verdicts = {g["slug"]: d["verdict"] for g, d in gd}
        seen = set()
        for i in items:
            s = i["game"]["slug"]
            if i["current"]:
                self.assertNotIn(s, seen)
                seen.add(s)
                self.assertEqual(i["verdict"], verdicts[s])
        self.assertEqual([i["at"] for i in items], sorted((i["at"] for i in items), reverse=True))


if __name__ == "__main__":
    unittest.main()
