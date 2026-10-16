import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from status_logic import notes_cover_version, make_mention_fn, determine_framework_status, STATUS_UPDATED, STATUS_LIKELY


class TestVersionCoverage(unittest.TestCase):
    def test_wildcard_range_covers_patch(self):
        notes = "For v1.0.x/v1.1.x/v1.2.x/v1.3.x/v1.4.x/v1.5.x\n* Fixed launcher"
        assert notes_cover_version(notes, "1.4.8")
        assert not notes_cover_version("For v1.0.x/v1.1.x/v1.2.x/v1.3.x", "1.4.8")
        assert not notes_cover_version("For v1.4.x", "1.41.0")


    def test_bare_versions_do_not_count_as_range(self):
        assert not notes_cover_version("Fixed 1.4 crash", "1.4.8")
        assert not notes_cover_version("Update to Rimworld 1.6", "1.6.4850")  # no series opt-in


    def test_series_match_requires_opt_in_and_context(self):
        assert notes_cover_version("12.0.0: Update to Rimworld 1.6", "1.6.4850", series_depth=2)
        assert not notes_cover_version("Update to Rimworld 1.5", "1.6.4850", series_depth=2)
        assert not notes_cover_version("Update to Rimworld 1.61", "1.6.4850", series_depth=2)
        assert not notes_cover_version("Update to Rimworld 1.6.4500", "1.6.4850", series_depth=2)
        assert not notes_cover_version("bumped deps 1.6", "1.6.4850", series_depth=2)


    def test_no_patch_since_explicitly_supported_series_is_updated(self):
        mfn = make_mention_fn("1.6.4850", None, 2)
        v = determine_framework_status(release_published_at="2025-07-13T19:17:00Z",
                                       release_notes="12.0.0: Update to Rimworld 1.6", release_tag="v12.0.0",
                                       patch_version="1.6.4850", patch_published_at="2026-06-08T19:12:10Z", mention_fn=mfn)
        assert v["status"] == STATUS_UPDATED


    def test_post_patch_release_without_range_stays_likely(self):
        mfn = make_mention_fn("1.4.8", r"(?<![\w.])v?{v}\b")
        v = determine_framework_status(release_published_at="2026-10-13T00:00:00Z", release_notes="* Fixed launcher",
                                       release_tag="v1.7.4", patch_version="BL v1.4.8",
                                       patch_published_at="2026-08-10T00:00:00Z", mention_fn=mfn)
        assert v["status"] == STATUS_LIKELY


class TestFetchFallback(unittest.TestCase):
    def test_reuses_previous_entry_only_for_same_patch(self):
        import json, tempfile
        import update
        with tempfile.TemporaryDirectory() as d:
            old = update.DATA_DIR
            update.DATA_DIR = Path(d)
            try:
                lp = {"label": "BL v1.4.8", "published_at": "2026-08-10T12:09:06Z"}
                (Path(d) / "g.json").write_text(json.dumps({"game": {"latest_patch": lp}, "frameworks": [
                    {"id": "a", "status": "Safe"}, {"id": "b", "status": "No data", "error": "x"}]}))
                self.assertEqual(update.previous_framework("g", "a", lp)["status"], "Safe")
                self.assertIsNone(update.previous_framework("g", "b", lp))
                self.assertIsNone(update.previous_framework("g", "a", {**lp, "label": "BL v1.4.9"}))
            finally:
                update.DATA_DIR = old


if __name__ == '__main__':
    unittest.main()
