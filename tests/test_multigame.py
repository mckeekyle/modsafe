"""Multi-game logic + site build tests (no network)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from games import GAMES, GAMES_BY_SLUG  # noqa: E402
from status_logic import (  # noqa: E402
    STATUS_LIKELY, STATUS_UNKNOWN, STATUS_UPDATED, detect_patch, determine_with_lineage,
    list_patches_generic, loader_support_status, make_mention_fn, neoforge_versions_for, overall_verdict,
)


def ts(y, m, d):
    return int(datetime(y, m, d, tzinfo=timezone.utc).timestamp())


def rule(slug):
    return GAMES_BY_SLUG[slug]["patch_rule"]


class TestPatchRules(unittest.TestCase):
    def check(self, slug, title, expected):
        d = detect_patch(title, rule(slug))
        if expected is None:
            self.assertIsNone(d, title)
        else:
            self.assertIsNotNone(d, title)
            self.assertEqual(d["version"], expected, title)

    def test_cyberpunk(self):
        self.check("cyberpunk-2077", "Patch 2.31", "2.31")
        self.check("cyberpunk-2077", "Update 2.0 date revealed!", None)
        # 2.5 is branded "Edgerunners 2 Update (2.5)"; teasers must stay excluded.
        self.check("cyberpunk-2077", "Cyberpunk 2077: Edgerunners 2 Update (2.5) is now live!", "2.5")
        self.check("cyberpunk-2077", "Edgerunners 2 Update (2.5) - Patch Notes", "2.5")
        self.check("cyberpunk-2077", "REDstreams — Cyberpunk 2077: Edgerunners 2 Update (2.5) is coming!", None)

    def test_skyrim(self):
        self.check("skyrim-se", "The Elder Scrolls V: Skyrim Anniversary Edition - Update 1.7.99 (Updated Aug 27)", "1.7.99")
        self.check("skyrim-se", "Skyrim Special Edition 1.5.16 Update", "1.5.16")
        self.check("skyrim-se", "Skyrim Special Edition 1.2 Update - Steam Beta", None)
        self.check("skyrim-se", "Adventure awaits in these Skyrim Creations!", None)

    def test_fallout4(self):
        d = detect_patch("Fallout 4 Update - August 18th ", rule("fallout-4"))
        self.assertIsNotNone(d)
        self.assertIsNone(d["version"])
        self.check("fallout-4", "Fallout 4: 1.10.40 Update", "1.10.40")
        self.check("fallout-4", "Fallout 4 Creation Kit Update - October 15", None)
        self.check("fallout-4", "Fallout 4 Upcoming Hotfixes and Creation Storage Increase", None)
        self.check("fallout-4", "Fallout 4: Anniversary Edition Announced!", None)

    def test_bg3(self):
        self.check("baldurs-gate-3", "Hotfix #36 Now Live!", "Hotfix #36")
        self.check("baldurs-gate-3", "Patch #7 Now Live!", "Patch #7")
        self.check("baldurs-gate-3", "Hotfix #29 Now Live! (Console Only)", None)
        self.check("baldurs-gate-3", "Community Update #36 A Very Moddy Christmas", None)
        d = detect_patch("The Final Patch: New Subclasses, Photo Mode, and Cross-Play", rule("baldurs-gate-3"))
        self.assertIsNotNone(d)

    def test_stardew(self):
        self.check("stardew-valley", "Stardew Valley 1.6.15 Patch now available", "1.6.15")
        self.check("stardew-valley", "1.6.14 Update", "1.6.14")
        self.check("stardew-valley", "1.6 Release Date Announced!", None)
        self.check("stardew-valley", "A Sneak Peek into the upcoming 1.6 update", None)

    def test_lethal(self):
        self.check("lethal-company", "Version 80 - The Blooming Update", "80")
        self.check("lethal-company", "Handy Patch V73", "73")
        self.check("lethal-company", "Version 80 Beta!", None)
        self.check("lethal-company", "1 Year Anniversary!", None)

    def test_labels_and_dedupe(self):
        news = [
            {"title": "Fallout 4 Update - August 18th", "date": ts(2026, 8, 18)},
            {"title": "Fallout 4 Update - May 27th", "date": ts(2026, 5, 27)},
            {"title": "Fallout 4 Creation Kit Update - October 15", "date": ts(2026, 10, 15)},
        ]
        ps = list_patches_generic(news, rule("fallout-4"))
        self.assertEqual([p["label"] for p in ps], ["Update 2026-08-18", "Update 2026-05-27"])
        lc = list_patches_generic([{"title": "Version 80 - The Blooming Update", "date": ts(2026, 4, 5)}], rule("lethal-company"))
        self.assertEqual(lc[0]["label"], "v80")


class TestMentions(unittest.TestCase):
    def test_lethal_mention_template(self):
        f = make_mention_fn("80", rule("lethal-company")["mention"])
        self.assertTrue(f("Updated for v80"))
        self.assertTrue(f("supports Version 80"))
        self.assertFalse(f("version 800"))
        self.assertFalse(f("1.0.80"))

    def test_unnumbered_patch_never_updated(self):
        f = make_mention_fn(None, None)
        v = determine_with_lineage(release_published_at="2026-09-01T00:00:00Z", release_notes="Update 2026-08-18",
                                   release_tag="v0.7.9", patch_version="Update 2026-08-18",
                                   patch_published_at="2026-08-18T00:00:00Z", lineage_mention_tags=[], mention_fn=f)
        self.assertEqual(v["status"], STATUS_LIKELY)
        v = determine_with_lineage(release_published_at="2026-08-16T00:00:00Z", release_notes="", release_tag="v0.7.9",
                                   patch_version="Update 2026-08-18", patch_published_at="2026-08-18T00:00:00Z",
                                   lineage_mention_tags=[], mention_fn=f)
        self.assertEqual(v["status"], STATUS_UNKNOWN)


class TestVerdictAndMinecraft(unittest.TestCase):
    def test_overall(self):
        self.assertEqual(overall_verdict([STATUS_UPDATED, STATUS_UPDATED]), STATUS_UPDATED)
        self.assertEqual(overall_verdict([STATUS_UPDATED, STATUS_LIKELY]), STATUS_LIKELY)
        self.assertEqual(overall_verdict([STATUS_LIKELY, STATUS_UNKNOWN]), STATUS_UNKNOWN)
        self.assertEqual(overall_verdict([]), STATUS_UNKNOWN)

    def test_neoforge_mapping(self):
        vs = ["21.4.10", "21.4.11-beta", "21.0.5", "21.1.2", "26.3.0.84", "26.1.2.5", "26.1.0.3"]
        self.assertEqual(neoforge_versions_for("1.21.4", vs), ["21.4.10", "21.4.11-beta"])
        self.assertEqual(neoforge_versions_for("1.21", vs), ["21.0.5"])
        self.assertEqual(neoforge_versions_for("26.3", vs), ["26.3.0.84"])
        self.assertEqual(neoforge_versions_for("26.1.2", vs), ["26.1.2.5"])
        self.assertEqual(neoforge_versions_for("26.4", vs), [])

    def test_loader_status(self):
        self.assertEqual(loader_support_status(has_stable=True, has_any=True, what="X", mc_version="1")["status"], STATUS_UPDATED)
        self.assertEqual(loader_support_status(has_stable=False, has_any=True, what="X", mc_version="1")["status"], STATUS_LIKELY)
        self.assertEqual(loader_support_status(has_stable=False, has_any=False, what="X", mc_version="1")["status"], STATUS_UNKNOWN)


class TestBuild(unittest.TestCase):
    def test_build_all_pages(self):
        import build

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "data"
            data_dir.mkdir()
            for g in GAMES:
                fws = [{"id": f["id"], "name": f["name"], "short": f["short"], "url": f["url"],
                        "tracked": f["source"] != "manual", "status": STATUS_LIKELY, "reason": "r",
                        "release_tag": "v1", "release_published_at": "2026-01-01T00:00:00Z", "release_url": f["url"]}
                       for f in g["frameworks"]]
                d = {"generated_at": "2026-10-15T00:00:00Z", "verdict": STATUS_LIKELY, "disclaimer": "d",
                     "game": {"slug": g["slug"], "name": g["name"], "latest_patch": {
                         "label": "P1", "version": "1", "title": "T", "published_at": "2026-01-01T00:00:00Z", "url": "https://x"}},
                     "frameworks": fws, "history": [{"label": "P1", "title": "T", "published_at": "2026-01-01T00:00:00Z",
                                                     "url": "https://x", "frameworks": []}]}
                (data_dir / f"{g['slug']}.json").write_text(json.dumps(d))
            saved = (build.DATA_DIR, build.DIST, build.ROOT)
            self.addCleanup(lambda: setattr(build, "DATA_DIR", saved[0]) or setattr(build, "DIST", saved[1]) or setattr(build, "ROOT", saved[2]))
            build.DATA_DIR, build.DIST, build.ROOT = data_dir, root / "dist", root
            self.assertEqual(build.main(), 0)
            dist = root / "dist"
            sitemap = (dist / "sitemap.xml").read_text()
            llms = (dist / "llms.txt").read_text()
            for g in GAMES:
                page = (dist / g["slug"] / "index.html").read_text()
                self.assertIn('"FAQPage"', page)
                self.assertIn("application/ld+json", page)
                self.assertNotIn("beehiiv", page)
                self.assertIn(f"/{g['slug']}/", sitemap)
                self.assertIn(f"/{g['slug']}/", llms)
                json.loads((dist / g["slug"] / "status.json").read_text())
                d = json.loads((dist / g["slug"] / "status.json").read_text())
                hist_page = (dist / g["slug"] / "history" / "index.html").exists()
                self.assertEqual(hist_page, build.has_history(d), g["slug"])
                if not hist_page:  # too little history: 301 to the game page, kept out of the sitemap
                    self.assertIn(f"/{g['slug']}/history/ /{g['slug']}/ 301", (dist / "_redirects").read_text())
                    self.assertNotIn(f"/{g['slug']}/history/", sitemap)
            home = (dist / "index.html").read_text()
            for g in GAMES:
                self.assertIn(f'href="/{g["slug"]}/"', home)
            self.assertFalse((dist / "newsletter").exists())
            self.assertIn("/newsletter/ / 301", (dist / "_redirects").read_text())
            self.assertIn("/history/ /cyberpunk-2077/history/ 301", (dist / "_redirects").read_text())
            self.assertIn("frameworks", json.loads((dist / "status.json").read_text()))
            self.assertEqual(len(json.loads((dist / "games.json").read_text())["games"]), len(GAMES))


if __name__ == "__main__":
    unittest.main()
