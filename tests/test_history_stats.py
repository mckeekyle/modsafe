import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import history_stats as hs  # noqa: E402
import mods  # noqa: E402
from status_logic import status_for_patch_history  # noqa: E402


def fw(**kw):
    base = {"short": "X", "status": "Safe", "data_from": "2026-01-01T00:00:00Z"}
    base.update(kw)
    return base


class TestPairInfo(unittest.TestCase):
    def test_kinds(self):
        e = {"label": "P1", "published_at": "2026-03-01T00:00:00Z"}
        self.assertEqual(hs.pair_info(e, fw(status="Not affected by patches"))["kind"], "skip")
        self.assertEqual(hs.pair_info(e, fw(data_from="2026-04-01T00:00:00Z"))["kind"], "outside")
        un = hs.pair_info(e, fw(first_release_at="2026-03-03T00:00:00Z", first_release_tag="v2"))
        self.assertEqual((un["kind"], un["next_days"], un["next_tag"]), ("unnamed", 2.0, "v2"))
        named = hs.pair_info(e, fw(first_mention_at="2026-03-01T12:00:00Z", first_mention_tag="v3"))
        self.assertEqual((named["kind"], named["days"], named["tag"]), ("named", 0.5, "v3"))

    def test_next_release_after_following_patch_is_not_counted(self):
        e = {"published_at": "2026-03-01T00:00:00Z"}
        info = hs.pair_info(e, fw(first_release_at="2026-06-01T00:00:00Z"), until=datetime(2026, 4, 1, tzinfo=timezone.utc))
        self.assertIsNone(info["next_days"])

    def test_game_summary(self):
        data = {"history": [
            {"label": "P2", "published_at": "2026-03-11T00:00:00Z",
             "frameworks": [fw(first_mention_at="2026-03-12T00:00:00Z", first_mention_tag="v2")]},
            {"label": "P1", "published_at": "2026-03-01T00:00:00Z",
             "frameworks": [fw(first_mention_at="2026-03-04T00:00:00Z", first_mention_tag="v1")]},
        ], "verdict_log": [
            {"at": "2026-03-11T01:00:00Z", "verdict": "Just patched, wait", "patch": "P2"},
            {"at": "2026-03-12T01:00:00Z", "verdict": "Safe", "patch": "P2"},
        ]}
        s = hs.game_summary(data, datetime(2026, 3, 20, tzinfo=timezone.utc))
        self.assertEqual((s["patches"], s["avg_gap"], s["pairs"], s["median_days"]), (2, 10.0, 2, 2.0))
        self.assertEqual(s["longest_wait"]["tag"], "v1")
        self.assertEqual(s["longest_stretch"]["days"], 1.0)
        self.assertEqual(s["longest_stretch"]["end_verdict"], "Safe")

    def test_ongoing_stretch(self):
        runs = hs.unsafe_stretches([{"at": "2026-03-01T00:00:00Z", "verdict": "Breakage reported", "patch": "P"}],
                                   datetime(2026, 3, 4, tzinfo=timezone.utc))
        self.assertIsNone(runs[0]["end"])
        self.assertEqual(runs[0]["days"], 3.0)

    def test_fmt_days(self):
        self.assertEqual(hs.fmt_days(0.25), "6 hours")
        self.assertEqual(hs.fmt_days(3), "3 days")
        self.assertEqual(hs.fmt_days(None), "—")


class TestHistoryTiming(unittest.TestCase):
    def test_first_mention_and_line_filter(self):
        rels = [
            {"tag_name": "v1.0", "published_at": "2026-01-01T00:00:00Z", "body": ""},
            {"tag_name": "v1.1", "published_at": "2026-03-02T00:00:00Z", "body": "Support for patch 2.5"},
            {"tag_name": "v1.2", "published_at": "2026-03-05T00:00:00Z", "body": "More fixes for 2.5"},
            {"tag_name": "v0.11.9", "published_at": "2026-03-01T06:00:00Z", "body": "legacy 2.5"},
        ]
        r = status_for_patch_history(releases=rels, patch_version="2.5", patch_published_at="2026-03-01T00:00:00Z",
                                     line_tag="v1.2")
        self.assertEqual(r["first_mention_tag"], "v1.1")
        self.assertEqual(r["first_release_tag"], "v1.1")
        self.assertEqual(r["data_from"], "2026-01-01T00:00:00Z")


class TestGuideErrors(unittest.TestCase):
    def test_every_guide_has_sourced_errors(self):
        import build
        for f in (ROOT / "data/guides").glob("*.md"):
            items = build.guide_errors(f.read_text())
            self.assertGreaterEqual(len(items), 3, f.name)
            for i in items:
                self.assertIn("Source:", i["a"], (f.name, i["q"]))
                self.assertNotIn("](", i["a"])
            self.assertIn("](https://", f.read_text().split("## Common errors and fixes")[1].split("## Rolling back")[0])
            self.assertTrue(mods.guide_parts(f.read_text())["steps"], f.name)


if __name__ == "__main__":
    unittest.main()
