import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build  # noqa: E402
from games import GAMES_BY_SLUG  # noqa: E402

UP = {"g": [{"version": "2.5", "label": "Patch 2.5", "date": "2026-10-22", "expire_days": 3,
             "frameworks": ["CET", "RED4ext"], "stores": "Steam/GOG/Epic", "source": "https://example.com/post"}]}


def data(version="2.31", published="2025-09-11T10:09:03Z"):
    return {"game": {"latest_patch": {"version": version, "published_at": published}}}


class TestUpcoming(unittest.TestCase):
    def a(self, d, today):
        return build.active_upcoming("g", d, today=today, upcoming=UP)

    def test_shown_before_and_on_date(self):
        self.assertIsNotNone(self.a(data(), date(2026, 10, 20)))
        self.assertIsNotNone(self.a(data(), date(2026, 10, 22)))

    def test_hidden_once_detected_by_version_or_date(self):
        self.assertIsNone(self.a(data("2.5", "2026-10-22T09:00:00Z"), date(2026, 10, 22)))
        self.assertIsNone(self.a(data("2.5.1", "2026-10-23T09:00:00Z"), date(2026, 10, 23)))

    def test_older_hotfix_does_not_hide(self):
        self.assertIsNotNone(self.a(data("2.32", "2026-10-21T09:00:00Z"), date(2026, 10, 21)))

    def test_expires_three_days_after(self):
        self.assertIsNotNone(self.a(data(), date(2026, 10, 25)))
        self.assertIsNone(self.a(data(), date(2026, 10, 26)))

    def test_requires_source_and_other_games_unaffected(self):
        self.assertIsNone(build.active_upcoming("g", data(), today=date(2026, 10, 20),
                                                upcoming={"g": [{**UP["g"][0], "source": ""}]}))
        self.assertIsNone(build.active_upcoming("other", data(), today=date(2026, 10, 20), upcoming=UP))

    def test_notice_text_and_link(self):
        html = build.upcoming_notice(UP["g"][0])
        for t in ("Patch 2.5 arrives Oct 22", "CET, RED4ext", "usually break on big patches",
                  "Turn off auto-update in Steam/GOG/Epic and back up your mods folder",
                  "This page will update when frameworks catch up", 'href="https://example.com/post"',
                  'data-hide-after="2026-10-26"'):
            self.assertIn(t, html)
        self.assertNotIn("dismiss", html.lower())
        self.assertEqual(build.upcoming_notice(None), "")

    def test_committed_entries_are_valid(self):
        d = json.loads((ROOT / "data" / "manual" / "upcoming-patches.json").read_text())
        for slug, entries in d["patches"].items():
            self.assertIn(slug, GAMES_BY_SLUG)
            for e in entries:
                date.fromisoformat(e["date"])
                self.assertTrue(e["source"].startswith("https://"))
        cp = d["patches"]["cyberpunk-2077"][0]
        self.assertEqual((cp["version"], cp["date"]), ("2.5", "2026-10-22"))
        self.assertEqual(cp["frameworks"], ["CET", "RED4ext", "redscript", "ArchiveXL", "TweakXL", "Codeware"])


if __name__ == "__main__":
    unittest.main()
