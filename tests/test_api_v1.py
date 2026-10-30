import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build  # noqa: E402
from games import COMPAT_GAMES, GAMES  # noqa: E402

GAME_KEYS = {"id", "name", "short_name", "kind", "steam_appid", "steam_appids", "current_patch", "verdict",
             "verdict_label", "severity", "updated_at", "upcoming_patch", "page_url", "json_url", "mods",
             # Added 2026-10-29 with the GTA V edition split (additive, api_version stays 1).
             "edition", "hub", "deprecated", "superseded_by"}
MOD_KEYS = {"id", "name", "short", "verdict", "verdict_label", "severity", "tracked", "counts_toward_verdict",
            "reason", "release", "release_published_at", "release_url", "url"}


class TestApiV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games_data = build.load_games()
        cls.api = build.api_v1_status(cls.games_data, today=date(2026, 10, 21), upcoming={})

    def test_top_level_contract(self):
        a = self.api
        self.assertEqual(a["api_version"], 1)
        for k in ("generated_at", "data_updated_at", "site", "disclaimer", "verdicts", "games"):
            self.assertIn(k, a)
        self.assertEqual(len(a["games"]), len(GAMES) + len(COMPAT_GAMES))
        json.dumps(a)  # serialisable

    def test_game_and_mod_shape(self):
        for g in self.api["games"]:
            self.assertEqual(set(g), GAME_KEYS, g["id"])
            self.assertTrue(g["page_url"].startswith(build.SITE_URL + "/"))
            self.assertIn(g["verdict"], build.VERDICT_SEVERITY, g["id"])
            self.assertIsInstance(g["steam_appids"], list)
            self.assertTrue(g["mods"], g["id"])
            for m in g["mods"]:
                self.assertEqual(set(m), MOD_KEYS)
                self.assertIn(m["verdict"], build.VERDICT_SEVERITY, (g["id"], m["id"]))

    def test_known_values(self):
        by = {g["id"]: g for g in self.api["games"]}
        self.assertEqual(by["cyberpunk-2077"]["steam_appid"], 1091500)
        self.assertEqual(by["gta-v"]["steam_appids"], [271590, 3240220])  # compat entry kept for v1 clients
        self.assertTrue(by["gta-v"]["deprecated"])
        self.assertEqual(by["gta-v"]["superseded_by"], ["gta-v-legacy", "gta-v-enhanced"])
        self.assertEqual(by["gta-v-legacy"]["steam_appids"], [271590])
        self.assertEqual(by["gta-v-enhanced"]["steam_appids"], [3240220])
        self.assertEqual((by["gta-v-legacy"]["edition"], by["gta-v-legacy"]["hub"]), ("legacy", "gta-v"))
        self.assertFalse(by["cyberpunk-2077"]["deprecated"])
        self.assertIsNone(by["cyberpunk-2077"]["superseded_by"])
        ids = [g["id"] for g in self.api["games"]]
        self.assertLess(ids.index("gta-v-enhanced"), ids.index("gta-v"))  # appid lookups hit the edition first
        self.assertIsNone(by["minecraft"]["steam_appid"])
        self.assertEqual(by["minecraft"]["steam_appids"], [])
        self.assertEqual(by["steam-deck"]["kind"], "platform")
        self.assertEqual(by["skyrim-se"]["kind"], "game")

    def test_verdict_ids(self):
        self.assertEqual(build.verdict_id("Just patched, wait"), "wait")
        self.assertEqual(build.verdict_id("Not ported yet"), "not-ported")
        self.assertEqual(build.verdict_id(None), "no-data")
        self.assertEqual(build.verdict_id("Something New"), "something-new")
        self.assertLess(build.VERDICT_SEVERITY["broken"], build.VERDICT_SEVERITY["safe"])

    def test_upcoming_included(self):
        g, d = next((g, d) for g, d in self.games_data if g["slug"] == "cyberpunk-2077")
        up = {"cyberpunk-2077": [{"version": "99.0", "label": "Patch 99.0", "date": "2099-01-02", "source": "https://example.com/p"}]}
        # Far-future date so live data (a real patch on/after the date) never hides the fixture entry.
        a = build.api_v1_status([(g, d)], today=date(2099, 1, 1), upcoming=up)
        self.assertEqual(a["games"][0]["upcoming_patch"]["label"], "Patch 99.0")

    def test_cors_headers(self):
        h = build.HEADERS
        block = h[h.index("/api/*"):]
        self.assertIn("Access-Control-Allow-Origin: *", block)
        self.assertEqual(h.count("Access-Control-Allow-Origin"), 1)  # duplicate rules would join to "*, *"

    def test_listed_in_llms_and_sitemap(self):
        self.assertIn("/api/v1/status.json", build.build_llms_txt(self.games_data))
        self.assertIn("/api/v1/status.json", build.sitemap_urls())


if __name__ == "__main__":
    unittest.main()
