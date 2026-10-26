"""Satisfactory, Palworld and Monster Hunter Wilds: config, patch rules and verdict logic (offline)."""
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import update  # noqa: E402
from games import GAMES_BY_SLUG  # noqa: E402
from status_logic import V_BROKEN, V_LIKELY, V_WAIT, detect_patch, ficsit_compat_adjust  # noqa: E402


def unix(iso):
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())


def news(*items):
    return {"appnews": {"newsitems": [{"gid": str(i), "title": t, "date": unix(d), "url": f"https://x/{i}", "contents": ""}
                                      for i, (t, d) in enumerate(items)]}}


def pics(appid, buildid, iso):
    return {"data": {str(appid): {"depots": {"branches": {"public": {"buildid": str(buildid), "timeupdated": str(unix(iso))}}}}}}


class _NoSleep:
    """Stands in for update's `time` module so the API pacing sleeps don't slow the suite."""

    def __getattr__(self, name):
        return getattr(time, name)

    @staticmethod
    def sleep(_s):
        return None


class FakeHttp:
    """Patch update's network helpers for one test; restores them afterwards."""

    def __init__(self, get, post=None, sources=None):
        self.get, self.post, self.sources = get, post, sources or {}

    def __enter__(self):
        self.saved = (update.http_get_json, update.http_post_json, dict(update.SOURCES), update.DATA_DIR, update.time)
        update.time = _NoSleep()
        self.tmp = tempfile.TemporaryDirectory()
        update.DATA_DIR = Path(self.tmp.name)
        update.http_get_json = lambda url, *a, **k: self.get(url)
        if self.post:
            update.http_post_json = lambda url, payload, **k: self.post(url, payload)
        update.SOURCES.update(self.sources)
        return self

    def __exit__(self, *a):
        update.http_get_json, update.http_post_json, sources, update.DATA_DIR, update.time = self.saved
        update.SOURCES.clear()
        update.SOURCES.update(sources)
        self.tmp.cleanup()


def ficsit_resp(state="Works", versions=(("3.12.0", "2026-06-06T17:02:02Z", ">=491125"),)):
    return {"data": {"getModByReference": {"compatibility": {"EA": {"state": state, "note": "crashes on load" if state != "Works" else ""}},
                                           "versions": [{"id": f"id{n}", "version": v, "created_at": d, "game_version": g,
                                                         "changelog": f"* Satisfactory 1.2 (CL#491125) support" if v == "3.12.0" else ""}
                                                        for n, (v, d, g) in enumerate(versions)]}}}


class TestSatisfactory(unittest.TestCase):
    g = GAMES_BY_SLUG["satisfactory"]

    def test_config(self):
        self.assertEqual(self.g["steam_appid"], 526870)
        sml = self.g["frameworks"][0]
        self.assertEqual((sml["id"], sml["source"]), ("sml", "ficsit_sml"))
        self.assertEqual(sml["issues_repo"], "satisfactorymodding/SatisfactoryModLoader")
        self.assertTrue(self.g["frameworks"][1]["agnostic"])
        self.assertIn("ficsit_sml", update.SOURCES)

    def test_patch_rule_stable_only(self):
        r = self.g["patch_rule"]
        self.assertEqual(detect_patch("1.2 Update Fixes v1.2.4.1", r)["version"], "1.2.4.1")
        self.assertEqual(detect_patch("Satisfactory 1.2 Update out now!", r)["version"], "1.2")
        self.assertEqual(detect_patch("1.1 Fixes v1.1.2.2", r)["version"], "1.1.2.2")
        for t in ("1.2 Experimental Hotfix v1.2.2.2", "EXPERIMENTAL Update v1.1.1.6", "Update 1.2 is out now on Experimental!",
                  "Satisfactory: The board game – Campaign live now!", "Satisfactory 1.0 - 2nd Anniversary!"):
            self.assertIsNone(detect_patch(t, r), t)

    def test_compat_flag(self):
        lab, why = ficsit_compat_adjust(V_LIKELY, "x.", {"state": "Broken", "note": "crash"}, min_cl=">=491125")
        self.assertEqual(lab, V_BROKEN)
        self.assertIn("Broken", why)
        self.assertIn("491125", why)
        self.assertEqual(ficsit_compat_adjust(V_LIKELY, "x.", {"state": "Damaged"})[0], V_BROKEN)
        lab, why = ficsit_compat_adjust(V_WAIT, "x.", {"state": "Works"})
        self.assertEqual(lab, V_WAIT)  # a hand-set 'Works' never upgrades a fresh patch
        self.assertIn("may not reflect this patch", why)
        self.assertEqual(ficsit_compat_adjust(V_LIKELY, "x.", {"state": "Works"})[0], V_LIKELY)
        self.assertIn("no compatibility flag", ficsit_compat_adjust(V_LIKELY, "x.", None)[1])

    def test_parse_ficsit(self):
        rels = update.parse_ficsit_sml(ficsit_resp(versions=(("3.11.3", "2025-08-09T03:19:09Z", ">=416835"),
                                                             ("3.12.0", "2026-06-06T17:02:02Z", ">=491125"))))
        self.assertEqual(rels[0]["tag_name"], "v3.12.0")
        self.assertEqual(rels[0]["game_version"], ">=491125")
        self.assertEqual(rels[0]["ficsit_compat"]["state"], "Works")
        self.assertTrue(rels[0]["html_url"].startswith("https://ficsit.app/mod/SML"))
        with self.assertRaises(RuntimeError):
            update.parse_ficsit_sml({"data": {"getModByReference": None}})

    def _run(self, state, patch_iso):
        def get(url):
            if "GetNewsForApp" in url:
                return news(("1.2 Update Fixes v1.2.4.1", patch_iso), ("1.2 Experimental Hotfix v1.2.9.9", "2026-10-20T10:00:00Z"),
                            ("Satisfactory 1.2 Update out now!", "2026-06-02T15:05:04Z"))
            if "steamcmd" in url:
                return pics(526870, 25782416, patch_iso)
            if "search/issues" in url:
                return {"items": []}
            raise AssertionError(url)
        smm = lambda fw: [{"tag_name": "v3.1.0", "name": "v3.1.0", "body": "", "published_at": "2026-06-06T00:00:00Z",
                           "html_url": fw["url"], "prerelease": False, "draft": False}]
        with FakeHttp(get, post=lambda url, p: ficsit_resp(state), sources={"github": smm}):
            return update.build_game(self.g)

    def test_end_to_end_old_patch_likely_safe(self):
        d = self._run("Works", "2026-10-12T14:39:03Z")
        self.assertEqual(d["game"]["latest_patch"]["label"], "1.2.4.1")  # experimental post ignored
        self.assertEqual(d["verdict"], V_LIKELY)
        self.assertIn("ficsit.app lists SML as Works", d["frameworks"][0]["reason"])

    def test_end_to_end_broken_flag_wins(self):
        d = self._run("Broken", "2026-10-12T14:39:03Z")
        self.assertEqual(d["verdict"], V_BROKEN)

    def test_end_to_end_fresh_patch_waits(self):
        fresh = datetime.fromtimestamp(time.time() - 86400, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        self.assertEqual(self._run("Works", fresh)["verdict"], V_WAIT)


def gh_rel(tag, iso, url="https://github.com/x"):
    return {"tag_name": tag, "name": tag, "body": "", "published_at": iso, "created_at": iso, "html_url": url,
            "prerelease": False, "draft": False}


class TestPalworld(unittest.TestCase):
    g = GAMES_BY_SLUG["palworld"]

    def test_config(self):
        self.assertEqual(self.g["steam_appid"], 1623730)
        ue, ps = self.g["frameworks"]
        self.assertEqual((ue["id"], ue["repo"], ue["issues_repo"]), ("ue4ss", "Okaetsu/RE-UE4SS", "Okaetsu/PalSchema"))
        self.assertEqual((ps["id"], ps["repo"]), ("palschema", "Okaetsu/PalSchema"))

    def test_patch_rule(self):
        r = self.g["patch_rule"]
        for t, v in (("v1.0.5: Bug fixes", "1.0.5"), ("v1.0.2.101103:Bug fixes", "1.0.2.101103"),
                     ("Update v0.6.8: Halloween! Zoe's Halloween costume and Depresso suit!", "0.6.8"),
                     ("Palworld v1.0 - Official Release Changelog", "1.0"), ("v0.6.5\uff1aMission Bug Fixes", "0.6.5")):
            self.assertEqual(detect_patch(t, r)["version"], v, t)
        for t in ("Global Popularity Poll 2026 Results & New Update", "Palworld \u00d7 RuneScape: Dragonwilds Steam Bundle is Out Now!",
                  "Palworld 1.0 Official Launch Trailer is OUT!", "Important: About MODs and 1.0!",
                  "Palworld to exit early access and officially release (Ver 1.0) in 2026!"):
            self.assertIsNone(detect_patch(t, r), t)

    def test_experimental_tag_ignored(self):
        rels = [gh_rel("2281fa31", "2026-09-03T21:06:13Z"), gh_rel("experimental-palworld", "2025-02-20T15:16:34Z")]
        with FakeHttp(lambda url: rels):
            got = update.releases_github(self.g["frameworks"][0])
        self.assertEqual([r["tag_name"] for r in got], ["2281fa31"])

    def _run(self, patch_iso, issues=()):
        searched = []

        def get(url):
            if "GetNewsForApp" in url:
                return news(("v1.0.5: Bug fixes", patch_iso), ("Global Popularity Poll 2026 Results & New Update", "2026-10-20T13:06:39Z"),
                            ("v1.0.4: Balance Adjustments & Bug Fixes", "2026-09-07T03:04:45Z"))
            if "steamcmd" in url:
                return pics(1623730, 25246127, patch_iso)
            if "search/issues" in url:
                searched.append(url)
                return {"items": list(issues)}
            raise AssertionError(url)
        rels = {"ue4ss": [gh_rel("2281fa31", "2026-09-03T21:06:13Z")], "palschema": [gh_rel("0.6.71", "2026-09-09T14:45:21Z")]}
        with FakeHttp(get, sources={"github": lambda fw: rels[fw["id"]]}):
            return update.build_game(self.g), searched

    def test_end_to_end_likely_safe(self):
        d, searched = self._run("2026-09-15T03:03:47Z")
        self.assertEqual(d["game"]["latest_patch"]["label"], "v1.0.5")  # poll post with "New Update" ignored
        self.assertEqual(d["verdict"], V_LIKELY)
        self.assertTrue(searched and all("repo%3AOkaetsu/PalSchema%20" in u for u in searched), searched)

    def test_fresh_patch_waits(self):
        fresh = datetime.fromtimestamp(time.time() - 86400, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        self.assertEqual(self._run(fresh)[0]["verdict"], V_WAIT)


if __name__ == "__main__":
    unittest.main()
