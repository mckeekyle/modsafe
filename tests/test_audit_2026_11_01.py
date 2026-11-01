"""Regressions from the 2026-11-01 audit."""
import re
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import build  # noqa: E402
from games import GAMES_BY_SLUG  # noqa: E402


def fake(slug, frameworks, verdict="Safe"):
    latest = {"label": "1.0", "version": "1.0", "published_at": "2026-10-28T10:00:00Z",
              "url": "https://example.com/notes", "title": "Patch 1.0"}
    return GAMES_BY_SLUG[slug], {"verdict": verdict, "game": {"latest_patch": latest}, "history": [latest],
                                 "verdict_log": [], "frameworks": frameworks, "reason": ""}


SHV = {"name": "Script Hook V", "short": "ScriptHookV", "source": "manual_shv", "tracked": True}
ASI = {"name": "Ultimate ASI Loader", "short": "ASI Loader", "source": "github", "tracked": True}
DECKY = {"name": "Decky Loader", "short": "Decky", "source": "github", "tracked": True}


class HomeCounts(unittest.TestCase):
    def test_hand_checked_script_hook_v_not_counted_as_auto_tracked(self):
        gd = [fake("gta-v-legacy", [SHV, ASI]), fake("gta-v-enhanced", [SHV, ASI]), fake("steam-deck", [DECKY])]
        home = build.build_home(gd)
        m = re.search(r"<strong>(\d+)</strong>frameworks auto-tracked", home)
        self.assertEqual(m.group(1), "3")  # ASI x2 + Decky; Script Hook V is checked by hand


class PatchesDescription(unittest.TestCase):
    def test_description_counts_games_not_status_pages(self):
        gd = [fake("gta-v-legacy", [SHV, ASI]), fake("gta-v-enhanced", [SHV, ASI]),
              fake("steam-deck", [DECKY]), fake("valheim", [])]
        page = build.build_patches_page(gd, now=datetime(2026, 11, 1, 20, 0, tzinfo=timezone.utc))
        desc = re.search(r'<meta name="description" content="([^"]+)"', page).group(1)
        self.assertIn("across 2 modded games and Steam Deck", desc)  # GTA V editions count once
        self.assertNotIn("4 modded games", desc)


if __name__ == "__main__":
    unittest.main()
