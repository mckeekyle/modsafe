import copy
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import fast_check  # noqa: E402

STEAM_GAME = {"slug": "g", "name": "G", "steam_appid": 1,
              "patch_rule": {"include": r"(?i)patch", "version": r"Patch (\d+\.\d+)"},
              "frameworks": [{"id": "fw", "short": "FW", "source": "github", "repo": "a/b"},
                             {"id": "man", "short": "Man", "source": "manual"}]}
COMMITTED = {"verdict": "Safe",
             "game": {"latest_patch": {"label": "1.0", "published_at": "2026-10-01T00:00:00Z", "steam_build": "100"}},
             "frameworks": [{"id": "fw", "status": "Safe", "release_tag": "v1"}, {"id": "man", "status": "Check manually"}]}


class Fake:
    def __init__(self, build="100", news=None, tag="v1", fail=()):
        self.build, self.tag, self.fail = build, tag, set(fail)
        self.news = news if news is not None else [{"title": "Patch 1.0", "date": 1759276800, "url": "u", "gid": "1"}]

    def _f(self, what):
        if what in self.fail:
            raise OSError("boom")

    def steam_build(self, appid):
        self._f("build"); return self.build

    def steam_news(self, appid):
        self._f("news"); return self.news

    def releases(self, fw, source=None):
        self._f("rel"); return [{"tag_name": self.tag, "published_at": "2026-10-02T00:00:00Z", "prerelease": False, "draft": False}]

    def mc_latest(self):
        self._f("mc"); return "26.3"

    def atlan_entries(self, fw):
        self._f("atlan"); return ["e2"]

    def manual(self, game):
        return {"latest_patch": {"steam_builds": {"legacy": "10", "enhanced": "20"}}}


class TestProbe(unittest.TestCase):
    def setUp(self):
        self._silent = fast_check.update.silent_patches_for
        fast_check.update.silent_patches_for = lambda slug: []

    def tearDown(self):
        fast_check.update.silent_patches_for = self._silent

    def test_nothing_changed_is_quiet(self):
        self.assertEqual(fast_check.probe_game(STEAM_GAME, COMMITTED, Fake()), [])

    def test_new_steam_build(self):
        r = fast_check.probe_game(STEAM_GAME, COMMITTED, Fake(build="101"))
        self.assertEqual(r, ["Steam build 100 -> 101"])

    def test_new_framework_release(self):
        self.assertEqual(fast_check.probe_game(STEAM_GAME, COMMITTED, Fake(tag="v2")), ["FW v1 -> v2"])

    def test_new_patch_post(self):
        news = [{"title": "Patch 1.1", "date": 1761955200, "url": "u2", "gid": "2"}] + Fake().news
        r = fast_check.probe_game(STEAM_GAME, COMMITTED, Fake(news=news))
        self.assertEqual(r, ["patch 1.0 -> 1.1"])

    def test_fetch_errors_never_trigger(self):
        self.assertEqual(fast_check.probe_game(STEAM_GAME, COMMITTED, Fake(build="9", tag="v9", fail={"build", "news", "rel"})), [])

    def test_missing_baseline_never_triggers(self):
        self.assertEqual(fast_check.probe_game(STEAM_GAME, None, Fake(build="9")), [])
        old = copy.deepcopy(COMMITTED)
        del old["game"]["latest_patch"]["steam_build"]  # data written before steam_build was recorded
        self.assertEqual(fast_check.probe_game(STEAM_GAME, old, Fake(build="9")), [])

    def test_framework_with_error_is_ignored(self):
        old = copy.deepcopy(COMMITTED)
        old["frameworks"][0]["error"] = "rate limited"
        self.assertEqual(fast_check.probe_game(STEAM_GAME, old, Fake(tag="v2")), [])

    def test_minecraft(self):
        g = {"slug": "minecraft", "kind": "minecraft", "frameworks": []}
        d = {"game": {"latest_patch": {"label": "26.2"}}, "frameworks": []}
        self.assertEqual(fast_check.probe_game(g, d, Fake()), ["Minecraft 26.2 -> 26.3"])

    def test_atlan(self):
        g = {"slug": "doom", "kind": "atlan", "steam_appid": 5, "frameworks": [
            {"id": "atlan", "short": "Atlan", "source": "atlan", "release_source": "github", "config_url": "x"}]}
        d = {"game": {"latest_patch": {"buildid": "100"}},
             "frameworks": [{"id": "atlan", "supported_entries": ["e1"], "release_tag": "v1"}]}
        self.assertEqual(fast_check.probe_game(g, d, Fake(build="101")), ["Steam build 100 -> 101", "Atlan config e1 -> e2"])

    def test_manual_edition_drift(self):
        g = {"slug": "gta", "kind": "manual", "manual_file": "x", "steam_appids": {"legacy": 1, "enhanced": 2}, "frameworks": []}
        d = {"game": {"latest_patch": {}}, "frameworks": []}
        self.assertEqual(fast_check.probe_game(g, d, Fake(build="10")), ["enhanced Steam build 20 -> 10"])
        # An already-recorded unannounced build doesn't re-trigger.
        d2 = {"game": {"latest_patch": {"unannounced_update": {"edition": "enhanced", "buildid": "10"}}}, "frameworks": []}
        self.assertEqual(fast_check.probe_game(g, d2, Fake(build="10")), [])

    def test_probe_lists_waiting_and_signature(self):
        games = [dict(STEAM_GAME, slug="a"), dict(STEAM_GAME, slug="b"), dict(STEAM_GAME, slug="c")]
        data = {"a": COMMITTED, "b": dict(COMMITTED, verdict="Just patched, wait"), "c": COMMITTED}
        res = fast_check.probe(games, fetch=Fake(), load=data.get)
        self.assertEqual(res["games"], ["b"])
        self.assertEqual(res["waiting"], ["b"])
        self.assertEqual(res["sig"], "")
        res2 = fast_check.probe(games, fetch=Fake(tag="v2"), load=data.get)
        self.assertEqual(res2["games"], ["a", "b", "c"])
        self.assertEqual(len(res2["sig"]), 16)
        self.assertEqual(res2["sig"], fast_check.probe(games, fetch=Fake(tag="v2"), load=data.get)["sig"])
        self.assertIn("waiting: b", res2["reason"])


class TestMeaningful(unittest.TestCase):
    def test_timestamps_only_is_not_meaningful(self):
        new = copy.deepcopy(COMMITTED)
        new["generated_at"] = "later"
        new["news"] = [{"title": "x"}]
        self.assertEqual(fast_check.meaningful({"g": (COMMITTED, new)}), [])

    def test_user_visible_changes_are_meaningful(self):
        for mut in (lambda d: d.update(verdict="Likely safe"),
                    lambda d: d["frameworks"][0].update(release_tag="v2"),
                    lambda d: d["frameworks"][0].update(status="Just patched, wait"),
                    lambda d: d["game"]["latest_patch"].update(steam_build="101"),
                    lambda d: d["game"]["latest_patch"].update(unannounced_update={"buildid": "5"}),
                    lambda d: d.update(verdict_log=[{}])):
            new = copy.deepcopy(COMMITTED)
            mut(new)
            self.assertEqual(fast_check.meaningful({"g": (COMMITTED, new)}), ["g"])
        self.assertEqual(fast_check.meaningful({"new": (None, COMMITTED)}), ["new"])


class TestWorkflows(unittest.TestCase):
    fast = (ROOT / ".github/workflows/fast-check.yml").read_text()
    main = (ROOT / ".github/workflows/update-and-deploy.yml").read_text()

    def test_staggered_from_full_refresh(self):
        fast_min = [int(m) for m in re.search(r'cron: "([\d,]+) \* \* \* \*"', self.fast).group(1).split(",")]
        main_min = int(re.search(r'cron: "(\d+) \*/6', self.main).group(1))
        self.assertEqual(len(fast_min), 2)  # every 30 minutes
        for m in fast_min:
            self.assertGreaterEqual(min((m - main_min) % 60, (main_min - m) % 60), 15)

    def test_least_privilege_and_cheap(self):
        self.assertIn("contents: read", self.fast)
        self.assertIn("actions: write", self.fast)
        self.assertNotIn("contents: write", self.fast)
        self.assertIn("timeout-minutes: 5", self.fast)
        self.assertNotIn("setup-python", self.fast)  # runner python3 is enough; no pip
        self.assertIn('--jq \'[.[] | select(.status != "completed")] | length\'', self.fast)

    def test_main_workflow_fast_mode(self):
        self.assertIn("cancel-in-progress: false", self.main)
        self.assertIn("./update $GAMES", self.main)
        self.assertIn("fast_check.py meaningful", self.main)
        self.assertRegex(self.main, r"Refresh mod list dates\n\s+if: inputs.games == ''")


if __name__ == "__main__":
    unittest.main()


class TestHubGrouping(unittest.TestCase):
    def test_edition_change_refreshes_hub_group(self):
        import fast_check
        games = [{"slug": "a-legacy"}, {"slug": "a-enhanced"}, {"slug": "a", "editions": ["a-legacy", "a-enhanced"]}, {"slug": "b"}]
        orig = fast_check.probe_game
        try:
            fast_check.probe_game = lambda g, c, f: ["steam build"] if g["slug"] == "a-legacy" else []
            res = fast_check.probe(games, fetch=object(), load=lambda s: {"verdict": "Safe"})
        finally:
            fast_check.probe_game = orig
        self.assertEqual(res["games"], ["a", "a-enhanced", "a-legacy"])
        self.assertEqual(list(res["changed"]), ["a-legacy"])
