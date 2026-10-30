"""GTA V split into per-edition pages (Legacy / Enhanced) with /gta-v/ as a hub and a deprecated combined record."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build  # noqa: E402
import news  # noqa: E402
import update  # noqa: E402
from games import ALL_GAMES, COMPAT_GAMES, GAMES, GAMES_BY_SLUG, HUBS  # noqa: E402

EDS = ["gta-v-legacy", "gta-v-enhanced"]


class TestRegistry(unittest.TestCase):
    def test_hub_and_editions(self):
        self.assertEqual(HUBS, {"gta-v": EDS})
        self.assertNotIn("gta-v", [g["slug"] for g in GAMES])  # no duplicate page from the combined record
        self.assertIn("gta-v", [g["slug"] for g in ALL_GAMES])
        leg, enh = (GAMES_BY_SLUG[s] for s in EDS)
        self.assertEqual((leg["steam_appid"], enh["steam_appid"]), (271590, 3240220))
        self.assertEqual((leg["exe"], enh["exe"]), ("GTA5.exe", "GTA5_Enhanced.exe"))
        self.assertEqual(leg["manual_file"], enh["manual_file"])  # same guard data
        self.assertTrue(all(g["hub"] == "gta-v" for g in (leg, enh)))
        self.assertEqual(build.distinct_games(GAMES), build.distinct_games([g for g in GAMES if g["slug"] != EDS[1]]))

    def test_data_files_are_single_edition(self):
        for s in EDS:
            d = json.loads((ROOT / f"data/games/{s}.json").read_text())
            ed = GAMES_BY_SLUG[s]["edition"]
            self.assertEqual(set(d["game"]["latest_patch"]["builds"]), {ed})
            self.assertGreaterEqual(len(d["history"]), 2)
        c = json.loads((ROOT / "data/games/gta-v.json").read_text())
        self.assertEqual(set(c["game"]["latest_patch"]["builds"]), {"legacy", "enhanced"})

    def test_edition_version_must_match(self):
        lp = {"builds": {"legacy": "1.0.1"}, "build_dates": {}, "steam_builds": {}}
        with self.assertRaises(SystemExit):
            update.manual_edition_patch(lp, {"version": "1.0.2"}, "legacy")
        out = update.manual_edition_patch(lp, {"version": "1.0.1", "label": "Build 1.0.1"}, "legacy")
        self.assertEqual(out["builds"], {"legacy": "1.0.1"})


class TestPages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games_data = build.load_games()
        cls.by = {g["slug"]: (g, d) for g, d in cls.games_data}

    def test_hub_page_links_both_and_is_thin(self):
        hub = COMPAT_GAMES[0]
        html = build.build_hub_page(hub, build.hub_editions("gta-v", self.games_data))
        for s in EDS:
            for sub in ("", "install/", "mods/", "history/"):
                self.assertIn(f'href="/{s}/{sub}"', html)
        self.assertIn('rel="canonical" href="https://modsafe.app/gta-v/"', html)
        self.assertIn("GTA5_Enhanced.exe", html)
        self.assertNotIn("faq-heading", html)  # FAQs live on the edition pages only

    def test_edition_page_switch_and_crumbs(self):
        g, d = self.by["gta-v-enhanced"]
        html = build.build_game_page(g, d)
        self.assertIn('href="/gta-v-legacy/"', html)
        self.assertIn('class="ed-switch"', html)
        self.assertIn('"item": "https://modsafe.app/gta-v/"', html.replace("'", '"'))
        self.assertIn('rel="canonical" href="https://modsafe.app/gta-v-enhanced/"', html)

    def test_sitemap_redirects_llms(self):
        urls = build.sitemap_urls()
        self.assertIn("/gta-v/", urls)
        for s in EDS:
            for sub in ("", "install/", "mods/", "history/"):
                self.assertIn(f"/{s}/{sub}", urls)
        self.assertNotIn("/gta-v/history/", urls)
        red = build.build_redirects(self.games_data)
        self.assertIn("/gta-v/history/ /gta-v/ 301", red)
        self.assertFalse(any(l.split()[:1] == ["/gta-v/"] for l in red.splitlines()))  # hub itself is not redirected
        llms = build.build_llms_txt(self.games_data)
        self.assertIn("https://modsafe.app/gta-v-legacy/", llms)
        self.assertIn("superseded_by", llms)

    def test_games_index_marks_compat(self):
        gi = build.games_index(self.games_data)
        by = {g["slug"]: g for g in gi["games"]}
        self.assertTrue(by["gta-v"]["deprecated"])
        self.assertEqual(by["gta-v"]["superseded_by"], EDS)
        self.assertEqual(by["gta-v-legacy"]["edition"], "legacy")

    def test_mods_and_guides_exist(self):
        import mods
        for s in EDS:
            self.assertTrue(mods.load_mods(s)["mods"])
            self.assertIn(GAMES_BY_SLUG[s]["exe"], (ROOT / f"data/guides/{s}.md").read_text())
        enh = {m["id"] for m in mods.load_mods("gta-v-enhanced")["mods"]}
        self.assertNotIn("openiv", enh)  # OpenIV.ASI doesn't work on Enhanced

    def test_news_tags_both(self):
        self.assertEqual({"gta-v-legacy", "gta-v-enhanced"} & set(news.tag_games("Grand Theft Auto V patch")),
                         {"gta-v-legacy", "gta-v-enhanced"})


if __name__ == "__main__":
    unittest.main()


class TestYoungLog(unittest.TestCase):
    def test_new_log_does_not_quote_stretch(self):
        from datetime import datetime, timezone
        import history_stats as hs
        d = {"history": [], "verdict_log": [{"at": "2026-10-30T00:00:00Z", "verdict": "Just patched, wait", "patch": "B"}]}
        self.assertIsNone(hs.game_summary(d, now=datetime(2026, 10, 30, 2, tzinfo=timezone.utc))["longest_stretch"])
        self.assertIsNotNone(hs.game_summary(d, now=datetime(2026, 11, 5, tzinfo=timezone.utc))["longest_stretch"])
