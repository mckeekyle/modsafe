import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import update  # noqa: E402
from status_logic import merge_silent_patches  # noqa: E402


class TestRefetchGuard(unittest.TestCase):
    def test_pages_never_refetches(self):
        self.assertIsNotNone(update.should_skip_refetch({"CF_PAGES": "1", "GITHUB_TOKEN": "x"}))

    def test_no_token_skips(self):
        self.assertIsNotNone(update.should_skip_refetch({}))

    def test_token_refetches_and_force_overrides(self):
        self.assertIsNone(update.should_skip_refetch({"GITHUB_TOKEN": "x"}))
        self.assertIsNone(update.should_skip_refetch({"GH_TOKEN": "x"}))
        self.assertIsNone(update.should_skip_refetch({"CF_PAGES": "1", "MODSAFE_FORCE_UPDATE": "1"}))


class TestSilentPatches(unittest.TestCase):
    v80 = {"version": "80", "label": "v80", "title": "Version 80", "published_at": "2026-04-05T08:27:11Z",
           "published_unix": 1775377631, "url": ""}

    def test_newer_silent_patch_becomes_latest(self):
        out = merge_silent_patches([self.v80], [{"version": "81", "label": "v81", "published_at": "2026-04-17T01:11:45Z"}])
        self.assertEqual(out[0]["label"], "v81")
        self.assertTrue(out[0]["silent"])
        self.assertEqual(out[1]["label"], "v80")

    def test_announced_patch_wins_and_no_duplicates(self):
        out = merge_silent_patches([self.v80], [{"version": "80", "label": "v80", "published_at": "2026-04-06T00:00:00Z"},
                                                {"label": "bad", "published_at": None}])
        self.assertEqual([p["label"] for p in out], ["v80"])

    def test_committed_overrides_cover_known_hotfixes(self):
        self.assertIn("v81", [p["label"] for p in update.silent_patches_for("lethal-company")])
        self.assertIn("1.4.5.8", [p["label"] for p in update.silent_patches_for("terraria")])
        for slug in ("lethal-company", "terraria"):
            for p in update.silent_patches_for(slug):
                self.assertTrue(p.get("sources"))


class TestReleaseLine(unittest.TestCase):
    def test_legacy_branch_is_not_same_line(self):
        from status_logic import same_release_line
        self.assertFalse(same_release_line("v0.11.8.11", "v2026.08.3.0"))
        self.assertTrue(same_release_line("v2026.08.2.1", "v2026.08.3.0"))
        self.assertTrue(same_release_line("1.7.12", "1.7.13"))
        self.assertTrue(same_release_line("updater-x", "v33"))


if __name__ == "__main__":
    unittest.main()
