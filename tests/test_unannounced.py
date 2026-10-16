import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from status_logic import (  # noqa: E402
    V_BROKEN, V_LIKELY, V_SAFE, V_WAIT, apply_unannounced, detect_unannounced_update, parse_steam_public_build,
)


def ts(s):
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())


PATCH = [{"label": "1.17", "version": "1.17", "published_at": "2026-08-27T14:00:00Z"}]


class TestParse(unittest.TestCase):
    def test_parse_ok_and_missing(self):
        info = {"status": "success", "data": {"1": {"depots": {"branches": {"public": {"buildid": "9", "timeupdated": "1788850938"}}}}}}
        b = parse_steam_public_build(info, 1)
        self.assertEqual(b["buildid"], "9")
        self.assertTrue(b["published_at"].endswith("Z"))
        self.assertIsNone(parse_steam_public_build({"status": "success", "data": {"1": {}}}, 1))  # e.g. SteamOS app
        self.assertIsNone(parse_steam_public_build({"status": "failed"}, 1))


class TestDetect(unittest.TestCase):
    def test_newer_build_without_news_is_event_without_version(self):
        e = detect_unannounced_update({"buildid": "5", "timeupdated": ts("2026-09-08T07:02:00"),
                                       "published_at": "2026-09-08T07:02:00Z"}, PATCH)
        self.assertIsNotNone(e)
        self.assertIsNone(e["version"])
        self.assertIn("2026-09-08", e["label"])

    def test_dedupe_within_two_days_of_patch(self):
        b = {"buildid": "5", "timeupdated": ts("2026-08-29T10:00:00"), "published_at": "x"}
        self.assertIsNone(detect_unannounced_update(b, PATCH))
        b = {"buildid": "5", "timeupdated": ts("2026-08-27T13:50:00"), "published_at": "x"}  # build just before post
        self.assertIsNone(detect_unannounced_update(b, PATCH))

    def test_older_build_is_no_event(self):
        b = {"buildid": "5", "timeupdated": ts("2026-08-01T00:00:00"), "published_at": "x"}
        self.assertIsNone(detect_unannounced_update(b, PATCH))
        self.assertIsNone(detect_unannounced_update(None, PATCH))


class TestApply(unittest.TestCase):
    ev = {"published_at": "2026-09-08T07:02:00Z", "buildid": "5"}

    def test_fresh_event_waits(self):
        now = datetime(2026, 9, 10, tzinfo=timezone.utc)
        lab, why = apply_unannounced(V_SAFE, "r", sensitive=True, release_published_at="2026-09-01T00:00:00Z", event=self.ev, now=now)
        self.assertEqual(lab, V_WAIT)
        self.assertIn("no announcement", why)

    def test_old_event_keeps_verdict_and_flags_recheck(self):
        now = datetime(2026, 10, 16, tzinfo=timezone.utc)
        lab, why = apply_unannounced(V_SAFE, "r", sensitive=True, release_published_at="2026-09-01T00:00:00Z", event=self.ev, now=now)
        self.assertEqual(lab, V_SAFE)
        self.assertIn("recheck", why)

    def test_release_after_event_or_agnostic_or_broken_unchanged(self):
        now = datetime(2026, 9, 10, tzinfo=timezone.utc)
        self.assertEqual(apply_unannounced(V_LIKELY, "r", sensitive=True, release_published_at="2026-09-09T00:00:00Z",
                                           event=self.ev, now=now), (V_LIKELY, "r"))
        self.assertEqual(apply_unannounced(V_SAFE, "r", sensitive=False, release_published_at=None, event=self.ev, now=now)[0], V_SAFE)
        self.assertEqual(apply_unannounced(V_BROKEN, "r", sensitive=True, release_published_at=None, event=self.ev, now=now)[0], V_BROKEN)


if __name__ == "__main__":
    unittest.main()
