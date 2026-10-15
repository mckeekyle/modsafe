#!/usr/bin/env python3
"""Unit tests for status determination logic (no network)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from status_logic import (
    STATUS_LIKELY,
    STATUS_UNKNOWN,
    STATUS_UPDATED,
    determine_framework_status,
    determine_with_lineage,
    extract_patch_version_from_title,
    is_live_patch_announcement,
    list_game_patches,
    notes_mention_patch,
    pick_latest_stable_release,
    select_latest_game_patch,
    status_for_patch_history,
)


class TestPatchParsing(unittest.TestCase):
    def test_extract_patch_title(self):
        self.assertEqual(extract_patch_version_from_title("Patch 2.31"), "2.31")
        self.assertEqual(extract_patch_version_from_title("Update 2.3 Patch Notes"), "2.3")
        self.assertEqual(extract_patch_version_from_title("Update 2.2 is live!"), "2.2")
        self.assertIsNone(extract_patch_version_from_title("It’s All About You! — A Crew"))

    def test_live_vs_teaser(self):
        self.assertTrue(is_live_patch_announcement("Patch 2.31"))
        self.assertTrue(is_live_patch_announcement("Update 2.2 is live!"))
        self.assertFalse(is_live_patch_announcement("Update 2.0 date revealed!"))
        self.assertFalse(is_live_patch_announcement("Patch 1.2 — Development Update"))


class TestNotesMention(unittest.TestCase):
    def test_explicit_mention(self):
        self.assertTrue(notes_mention_patch("Add support for patch 2.31 and newer", "2.31"))
        self.assertTrue(notes_mention_patch("Patch 2.3 support", "2.3"))
        self.assertFalse(notes_mention_patch("Add support for patch 2.31", "2.3"))  # not 2.3 alone inside 2.31
        self.assertFalse(notes_mention_patch("Various fixes", "2.31"))

    def test_word_boundary_against_longer_version(self):
        # "2.3" must not match inside "2.31"
        self.assertFalse(notes_mention_patch("support for 2.31", "2.3"))
        self.assertTrue(notes_mention_patch("support for 2.3 and newer", "2.3"))


class TestDetermineStatus(unittest.TestCase):
    def test_updated_when_notes_and_newer(self):
        r = determine_framework_status(
            release_published_at="2025-09-12T00:00:00Z",
            release_notes="Add support for patch 2.31 and newer",
            release_tag="v1.29.0",
            patch_version="2.31",
            patch_published_at="2025-09-11T10:00:00Z",
        )
        self.assertEqual(r["status"], STATUS_UPDATED)
        self.assertTrue(r["mentions_patch"])
        self.assertTrue(r["newer_than_patch"])

    def test_likely_when_newer_no_mention(self):
        r = determine_framework_status(
            release_published_at="2026-10-05T00:00:00Z",
            release_notes="Fixed occasional crashes",
            release_tag="v1.27.4",
            patch_version="2.31",
            patch_published_at="2025-09-11T10:00:00Z",
        )
        self.assertEqual(r["status"], STATUS_LIKELY)
        self.assertFalse(r["mentions_patch"])

    def test_unknown_when_older(self):
        r = determine_framework_status(
            release_published_at="2025-08-28T00:00:00Z",
            release_notes="Implements struct constructor syntax",
            release_tag="v0.5.31",
            patch_version="2.31",
            patch_published_at="2025-09-11T10:00:00Z",
        )
        self.assertEqual(r["status"], STATUS_UNKNOWN)
        self.assertFalse(r["newer_than_patch"])

    def test_updated_on_mention_even_if_slightly_earlier_clock(self):
        r = determine_framework_status(
            release_published_at="2025-09-11T09:00:00Z",
            release_notes="Add support for patch 2.31",
            release_tag="v1.0.0",
            patch_version="2.31",
            patch_published_at="2025-09-11T10:00:00Z",
        )
        self.assertEqual(r["status"], STATUS_UPDATED)


class TestSelectLatestPatch(unittest.TestCase):
    def test_selects_newest_live_patch(self):
        items = [
            {"title": "It’s All About You!", "date": 1700000000, "url": "u0", "contents": ""},
            {"title": "Patch 2.21", "date": 1737630343, "url": "u1", "contents": "live"},
            {"title": "Update 2.3 Patch Notes", "date": 1752682358, "url": "u2", "contents": ""},
            {"title": "Patch 2.31", "date": 1757585343, "url": "u3", "contents": "live"},
            {"title": "Update 2.0 date revealed!", "date": 1694700000, "url": "u4", "contents": ""},
        ]
        latest = select_latest_game_patch(items)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["version"], "2.31")

    def test_list_unique_patches(self):
        items = [
            {"title": "Patch 2.31", "date": 1757585343, "url": "a"},
            {"title": "Patch 2.31", "date": 1757585000, "url": "b"},
            {"title": "Update 2.3 Patch Notes", "date": 1752682358, "url": "c"},
        ]
        patches = list_game_patches(items)
        versions = [p["version"] for p in patches]
        self.assertEqual(versions, ["2.31", "2.3"])


class TestPickRelease(unittest.TestCase):
    def test_skips_prerelease(self):
        releases = [
            {"tag_name": "v2.0.0-beta", "prerelease": True, "draft": False, "published_at": "2026-01-02T00:00:00Z", "body": ""},
            {"tag_name": "v1.9.0", "prerelease": False, "draft": False, "published_at": "2026-01-01T00:00:00Z", "body": ""},
        ]
        latest = pick_latest_stable_release(releases)
        self.assertEqual(latest["tag_name"], "v1.9.0")


class TestHistoryHelper(unittest.TestCase):
    def test_history_prefers_mention(self):
        releases = [
            {
                "tag_name": "v1.29.0",
                "body": "Add support for patch 2.31 and newer",
                "published_at": "2025-09-11T18:00:00Z",
                "prerelease": False,
                "draft": False,
            },
            {
                "tag_name": "v1.30.0",
                "body": "API changes",
                "published_at": "2026-03-09T00:00:00Z",
                "prerelease": False,
                "draft": False,
            },
        ]
        snap = status_for_patch_history(
            releases=releases,
            patch_version="2.31",
            patch_published_at="2025-09-11T10:00:00Z",
        )
        self.assertEqual(snap["status"], STATUS_UPDATED)
        # Newest release that mentions the patch wins (v1.29.0); v1.30 does not mention it.
        self.assertEqual(snap["release_tag"], "v1.29.0")



class TestLineage(unittest.TestCase):
    def test_lineage_upgrades_likely_to_updated(self):
        r = determine_with_lineage(
            release_published_at="2026-03-09T00:00:00Z",
            release_notes="API changes only",
            release_tag="v1.30.0",
            patch_version="2.31",
            patch_published_at="2025-09-11T10:00:00Z",
            lineage_mention_tags=["v1.29.0"],
        )
        self.assertEqual(r["status"], STATUS_UPDATED)
        self.assertIn("v1.29.0", r["reason"])

    def test_lineage_does_not_upgrade_unknown(self):
        r = determine_with_lineage(
            release_published_at="2025-08-01T00:00:00Z",
            release_notes="old",
            release_tag="v0.1",
            patch_version="2.31",
            patch_published_at="2025-09-11T10:00:00Z",
            lineage_mention_tags=["v0.1"],  # mention alone without newer date stays unknown path
        )
        # newer_than_patch is False, so lineage must not upgrade
        self.assertEqual(r["status"], STATUS_UNKNOWN)


if __name__ == "__main__":
    unittest.main()
