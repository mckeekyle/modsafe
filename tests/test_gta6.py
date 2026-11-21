"""/gta-6/ info page: countdown only for an official date, facts sourced, wired into sitemap (no network)."""

from __future__ import annotations

import copy
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import build  # noqa: E402
import gta6  # noqa: E402


class TestGta6(unittest.TestCase):
    def setUp(self):
        self.d = gta6.load()

    def test_data_is_sourced(self):
        d = self.d
        self.assertTrue(d["console_release"]["source"].startswith("https://www.rockstargames.com/"))
        self.assertIn(d["pc_release"]["status"], ("not-announced", "announced", "released"))
        self.assertTrue(d["mod_policy"]["source"].startswith("https://support.rockstargames.com/"))
        date.fromisoformat(d["last_verified"])

    def test_no_countdown_without_official_date(self):
        self.assertIsNone(gta6.countdown_date(self.d))
        self.assertEqual(gta6.countdown_html(self.d), "")
        d = copy.deepcopy(self.d)
        d["pc_release"]["date"] = "2027-03-01"  # a rumoured date alone (no official announcement) never counts down
        self.assertIsNone(gta6.countdown_date(d))
        d["pc_release"]["status"] = "announced"  # announced but no Rockstar source: still no countdown
        self.assertIsNone(gta6.countdown_date(d))

    def test_countdown_once_announced(self):
        d = copy.deepcopy(self.d)
        d["pc_release"].update(status="announced", date="2027-03-01", date_source="https://www.rockstargames.com/newswire/x")
        self.assertEqual(gta6.countdown_date(d), date(2027, 3, 1))
        html = gta6.countdown_html(d)
        self.assertIn('data-target="2027-03-01"', html)
        self.assertIn("rockstargames.com", html)
        self.assertEqual(gta6.days_until(date(2027, 3, 1), date(2027, 2, 27)), 2)
        self.assertIn("Coming March 1, 2027", gta6.pc_status_text(d))
        self.assertNotIn("Reported, not confirmed", gta6.body(d, [], build.badge, ""))

    def test_rumour_is_labelled(self):
        page = gta6.body(self.d, [], build.badge, "")
        self.assertIn("Reported, not confirmed", page)
        self.assertIn("There is no GTA 6 PC download", page)

    def test_faq_and_wiring(self):
        qs = [i["q"] for i in gta6.faq(self.d)]
        self.assertIn("Does GTA 6 have mods?", qs)
        self.assertIn(gta6.PATH, build.sitemap_urls())


if __name__ == "__main__":
    unittest.main()
