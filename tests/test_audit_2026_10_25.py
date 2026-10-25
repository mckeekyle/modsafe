"""Regressions from the 2026-10-25 audit."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class GuideRollbackClaims(unittest.TestCase):
    def test_guides_dont_deny_rollback_where_steam_has_branches(self):
        branches = json.loads((ROOT / "data/manual/steam-branches.json").read_text())["games"]
        for slug, info in branches.items():
            if not isinstance(info, dict) or not info.get("rollback"):
                continue
            g = ROOT / "data/guides" / f"{slug}.md"
            if g.exists():
                self.assertIsNone(re.search(r"Steam can'?t officially", g.read_text()), slug)


class WorkflowRefreshesModDates(unittest.TestCase):
    def test_workflow_refreshes_and_commits_mod_dates(self):
        wf = (ROOT / ".github/workflows/update-and-deploy.yml").read_text()
        self.assertIn("tools/verify_mods.py --write", wf)
        self.assertRegex(wf, r"git add [^\n]*data/mods")


if __name__ == "__main__":
    unittest.main()
