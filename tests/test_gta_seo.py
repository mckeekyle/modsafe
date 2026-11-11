"""Search-phrased GTA V titles (games.py "seo"): patch naming, fallbacks, unchanged URLs (no network)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import build  # noqa: E402
from games import GAMES, GAMES_BY_SLUG  # noqa: E402


def data(title, version, label=None):
    return {"game": {"latest_patch": {"title": title, "version": version, "label": label or f"Build {version}"}}}


class TestPatchNames(unittest.TestCase):
    def test_title_update(self):
        self.assertEqual(build.patch_names(data("GTAV Title Update 1.73 Notes (Rockstar Support)", "1.0.3889.0")),
                         ("Title Update 1.73", "Title Update 1.73 (build 1.0.3889.0)"))

    def test_edition_only_hotfix_uses_build(self):
        d = data("GTAV Title Update 1.73 Notes (Rockstar Support; PC Enhanced-only update Sep 15, 2026)", "1.0.1158.16")
        self.assertEqual(build.patch_names(d), ("build 1.0.1158.16", "build 1.0.1158.16"))

    def test_no_version_falls_back_to_label(self):
        self.assertEqual(build.patch_names(data("Some update", None, "Update 2026-11-01")),
                         ("Update 2026-11-01", "Update 2026-11-01"))


class TestSeoText(unittest.TestCase):
    def test_only_gta_editions_have_overrides(self):
        self.assertEqual(sorted(g["slug"] for g in GAMES if g.get("seo")), ["gta-v-enhanced", "gta-v-legacy"])

    def test_templates_fill(self):
        g = GAMES_BY_SLUG["gta-v-legacy"]
        self.assertEqual(build.seo_text(g, "status_title", "x", patch="Title Update 1.73"),
                         "Is it safe to update GTA V Legacy? Mod status after Title Update 1.73")
        self.assertIn("13 essentials", build.seo_text(g, "mods_title", "x", patch="Title Update 1.73", n=13))
        for key in ("status_desc", "mods_desc", "guide_desc"):
            out = build.seo_text(g, key, "x", patch_full="p", verdict="Safe", n=1, top="A", fw="F", steps=8, errors=4)
            self.assertNotIn("{", out, key)

    def test_other_games_keep_defaults(self):
        self.assertEqual(build.seo_text(GAMES_BY_SLUG["skyrim-se"], "status_title", "default"), "default")


if __name__ == "__main__":
    unittest.main()
