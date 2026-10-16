import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from games import GAMES_BY_SLUG  # noqa: E402
from status_logic import V_NODATA, V_SAFE, V_WAIT, atlan_verdict, parse_atlan_config  # noqa: E402

CFG = '''checksums {
    "eternal_steam_03042026"         = "baa2"
    "darkage_steam_07292026"         = "367e"
    "darkage_steam_07292026_patched" = "848d"
\t"darkage_steam_10072026"         = "d8f5"
\t"darkage_steam_10072026_patched" = "da4f"
    "darkage_steam_13452026"         = "bad date"
}'''


class TestAtlan(unittest.TestCase):
    def test_parse_entries(self):
        self.assertEqual(parse_atlan_config(CFG), ["2026-10-07", "2026-07-29"])
        self.assertEqual(parse_atlan_config(""), [])

    def test_entry_same_day_as_build_is_safe(self):
        self.assertEqual(atlan_verdict(newest_entry="2026-10-07", build_published_at="2026-10-07T15:16:04Z")["status"], V_SAFE)

    def test_newer_build_without_entry_waits(self):
        now = datetime(2026, 10, 22, tzinfo=timezone.utc)
        v = atlan_verdict(newest_entry="2026-10-07", build_published_at="2026-10-21T10:00:00Z", now=now)
        self.assertEqual(v["status"], V_WAIT)
        self.assertIn("2026-10-21", v["reason"])

    def test_missing_entry_is_no_data(self):
        self.assertEqual(atlan_verdict(newest_entry=None, build_published_at="2026-10-07T15:16:04Z")["status"], V_NODATA)

    def test_game_config(self):
        g = GAMES_BY_SLUG["doom-the-dark-ages"]
        self.assertEqual(g["steam_appid"], 3017860)
        self.assertEqual(g["kind"], "atlan")
        self.assertIn("modloader_cache.bin", g["note"])
        self.assertIn("Steam only", g["note"])
        fw = g["frameworks"][0]
        self.assertEqual((fw["repo"], fw["tag"]), ("FlavorfulGecko5/EntityAtlan", "ModLoader"))


class TestAtlanFallback(unittest.TestCase):
    def test_config_failure_keeps_last_good(self):
        import json, tempfile
        import update
        g = GAMES_BY_SLUG["doom-the-dark-ages"]
        with tempfile.TemporaryDirectory() as d:
            old = (update.DATA_DIR, update.http_get_json, update.http_get_text, update.SOURCES.get("github_asset"))
            update.DATA_DIR = Path(d)
            (Path(d) / "doom-the-dark-ages.json").write_text(json.dumps({"frameworks": [
                {"id": "atlan-mod-loader", "supported_entries": ["2026-10-07"], "release_tag": "x.zip"}]}))
            pics = {"status": "success", "data": {"3017860": {"depots": {"branches": {"public": {"buildid": "25755602", "timeupdated": "1791386164"}}}}}}
            update.http_get_json = lambda url, **k: pics if "steamcmd" in url else {"appnews": {"newsitems": []}}
            def boom(*a, **k):
                raise OSError("down")
            update.http_get_text = boom
            update.SOURCES["github_asset"] = boom
            try:
                body = update.build_atlan_game(g)
            finally:
                update.DATA_DIR, update.http_get_json, update.http_get_text, update.SOURCES["github_asset"] = old
        fw = body["frameworks"][0]
        self.assertEqual(fw["status"], V_SAFE)
        self.assertIn("last good", fw["reason"])
        self.assertEqual(body["latest_patch"]["buildid"], "25755602")
        self.assertIsNone(body["latest_patch"]["version"])


if __name__ == "__main__":
    unittest.main()
