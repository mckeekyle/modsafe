"""User-facing verdict logic (v3)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from games import GAMES  # noqa: E402
from status_logic import (  # noqa: E402
    STATUS_LIKELY, STATUS_UNKNOWN, STATUS_UPDATED, V_AGNOSTIC, V_BROKEN, V_LIKELY, V_NODATA, V_NOT_PORTED,
    V_SAFE, V_WAIT, game_verdict, is_breakage_title, parse_silverlock, user_verdict,
)


class TestUserVerdict(unittest.TestCase):
    def v(self, **kw):
        kw.setdefault("age_days", 30)
        return user_verdict(**kw)

    def test_explicit_support_is_safe(self):
        self.assertEqual(self.v(base_status=STATUS_UPDATED), V_SAFE)
        self.assertEqual(self.v(base_status=STATUS_UNKNOWN, official_support=True), V_SAFE)

    def test_agnostic(self):
        self.assertEqual(self.v(base_status=STATUS_UNKNOWN, sensitive=False), V_AGNOSTIC)

    def test_breakage_beats_likely(self):
        self.assertEqual(self.v(base_status=STATUS_LIKELY, breakage=[{"title": "x"}]), V_BROKEN)
        self.assertEqual(self.v(base_status=STATUS_UNKNOWN, breakage=[{"title": "x"}]), V_BROKEN)

    def test_time_signal(self):
        self.assertEqual(self.v(base_status=STATUS_UNKNOWN, age_days=3), V_WAIT)
        self.assertEqual(self.v(base_status=STATUS_UNKNOWN, age_days=30), V_LIKELY)
        self.assertEqual(self.v(base_status=STATUS_LIKELY, age_days=1), V_LIKELY)

    def test_minecraft_absence(self):
        self.assertEqual(self.v(base_status=STATUS_UNKNOWN, absence_is_definitive=True, age_days=30), V_NOT_PORTED)
        self.assertEqual(self.v(base_status=STATUS_UNKNOWN, absence_is_definitive=True, age_days=2), V_WAIT)

    def test_no_data(self):
        self.assertEqual(self.v(base_status=None), V_NODATA)

    def test_game_verdict_worst_wins_and_ignores_agnostic(self):
        self.assertEqual(game_verdict([V_SAFE, V_LIKELY, V_AGNOSTIC]), V_LIKELY)
        self.assertEqual(game_verdict([V_SAFE, V_AGNOSTIC]), V_SAFE)
        self.assertEqual(game_verdict([V_SAFE, V_WAIT, V_BROKEN]), V_BROKEN)
        self.assertEqual(game_verdict([V_AGNOSTIC]), V_NODATA)


class TestBreakageTitles(unittest.TestCase):
    def test_requires_update_context(self):
        self.assertTrue(is_breakage_title("Game crashes after latest update"))
        self.assertTrue(is_breakage_title("Not working with patch 2.31"))
        self.assertTrue(is_breakage_title("SMAPI crash on 1.6.15", "1.6.15"))
        self.assertFalse(is_breakage_title("Compiler backend crashes with a overflow if you have more than 254 arguments"))
        self.assertFalse(is_breakage_title("Update README"))
        self.assertFalse(is_breakage_title("Issues with Dying and exiting to menu."))


class TestSilverlock(unittest.TestCase):
    def test_f4se(self):
        t = "Fallout 4 runtime 1.11.240 - build: 0.7.9 - nexus Fallout 4 runtime 1.10.984 - build: 0.7.2"
        self.assertEqual(parse_silverlock(t), {"runtime": "1.11.240", "build": "0.7.9"})

    def test_skse(self):
        t = "Current Anniversary Edition build 2.3.1 (game version 1.7.104): Nexus Current GOG build 2.2.6 (game version 1.6.1179)"
        self.assertEqual(parse_silverlock(t), {"runtime": "1.7.104", "build": "2.3.1"})


class TestClassification(unittest.TestCase):
    def test_agnostic_set(self):
        agn = {f["id"] for g in GAMES for f in g["frameworks"] if f.get("agnostic")}
        self.assertEqual(agn, {"bg3mm", "bepinexpack", "asi-loader", "harmony", "harmony-bl", "decky-steamgriddb", "decky-cssloader", "decky-protondb", "decky-powertools", "navigraph"})
        for g in GAMES:
            for f in g["frameworks"]:
                if f["id"] in {"cet", "red4ext", "redscript", "skse64", "f4se", "bg3se", "smapi"}:
                    self.assertFalse(f.get("agnostic"), f["id"])


if __name__ == "__main__":
    unittest.main()


class TestManualGTA(unittest.TestCase):
    def test_hook_verdicts(self):
        from status_logic import manual_hook_verdict
        cur = ["1.0.3889.0", "1.0.1158.13"]
        self.assertEqual(manual_hook_verdict(supported=cur, current=cur, patch_age=90, verified_age=0)["status"], V_SAFE)
        self.assertEqual(manual_hook_verdict(supported=cur, current=cur, patch_age=90, verified_age=30)["status"], V_LIKELY)
        self.assertEqual(manual_hook_verdict(supported=cur[:1], current=cur, patch_age=2, verified_age=0)["status"], V_WAIT)
        self.assertEqual(manual_hook_verdict(supported=cur[:1], current=cur, patch_age=20, verified_age=0)["status"], V_NOT_PORTED)

    def test_manual_file_and_no_devc_fetch(self):
        import json
        root = Path(__file__).resolve().parents[1]
        d = json.loads((root / "data/manual/gta-v.json").read_text())
        self.assertIn("last_verified", d)
        self.assertEqual(set(d["latest_patch"]["builds"]), {"legacy", "enhanced"})
        src = (root / "src/update.py").read_text()
        self.assertNotIn("://www.dev-c.com", src)
        gta = next(g for g in GAMES if g["slug"] == "gta-v")
        self.assertTrue(next(f for f in gta["frameworks"] if f["id"] == "asi-loader")["agnostic"])
        self.assertIn("GTA Online", gta["note"])

    def test_build_shows_verified_and_warning(self):
        import json, tempfile, build
        from games import GAMES as G
        g = next(x for x in G if x["slug"] == "gta-v")
        d = {"generated_at": "2026-10-15T00:00:00Z", "verdict": V_SAFE, "disclaimer": "", "last_verified": "2026-10-15",
             "game": {"slug": "gta-v", "name": g["name"], "latest_patch": {"label": "TU 1.73", "published_at": "2026-07-14T00:00:00Z",
                      "builds": {"legacy": "1.0.3889.0", "enhanced": "1.0.1158.13"}, "url": "", "title": ""}},
             "frameworks": [], "history": []}
        html = build.build_game_page(g, d)
        self.assertIn("Last manually verified", html)
        self.assertIn("2026-10-15", html)
        self.assertIn("GTA Online", html)
        self.assertIn("1.0.1158.13", html)


class TestAnalyticsBeacon(unittest.TestCase):
    def test_beacon_optional(self):
        import build
        old = build.CF_ANALYTICS_TOKEN
        try:
            build.CF_ANALYTICS_TOKEN = ""
            self.assertNotIn("cloudflareinsights", build.page_shell("t", "d", "/", "home", "x"))
            build.CF_ANALYTICS_TOKEN = "abc123"
            html = build.page_shell("t", "d", "/", "home", "x")
            self.assertIn("static.cloudflareinsights.com/beacon.min.js", html)
            self.assertIn("abc123", html)
        finally:
            build.CF_ANALYTICS_TOKEN = old


class TestNavTidy(unittest.TestCase):
    def test_no_json_in_header_but_in_footer_and_head(self):
        import build
        html = build.page_shell("t", "d", "/skyrim-se/", "skyrim-se", "x")
        nav = html[html.index('<nav'):html.index('</nav>')]
        self.assertNotIn("json", nav.lower())
        foot = html[html.index('<footer'):]
        self.assertIn('href="/games.json"', foot)
        self.assertIn('rel="alternate" type="application/json" href="https://modsafe.app/skyrim-se/status.json"', html)
        self.assertNotIn("placeholder", html.lower())
