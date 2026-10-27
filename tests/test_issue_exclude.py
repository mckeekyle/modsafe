"""Decky Loader's tracker also covers Steam Frame / SteamOS VR and pre-release builds (2026-10-27: issue #1005
"[BUG] Frame build installs a broken service on update" flipped /steam-deck/ to "Breakage reported")."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import update  # noqa: E402
from games import GAMES_BY_SLUG  # noqa: E402

DECKY = next(f for f in GAMES_BY_SLUG["steam-deck"]["frameworks"] if f["id"] == "decky-loader")
FRAME_BODY = ("### SteamOS version\n\n0.6.0 VR\n\n### Selected Update Channel\n\nPrerelease\n\n"
              "### Decky Loader Version\n\nv3.3.1-pre1-dev6\n")
DECK_BODY = ("### SteamOS version\n\n3.9.1\n\n### Selected Update Channel\n\nStable\n\n"
             "### Decky Loader Version\n\nv3.3.1\n")


def item(n, title, body):
    return {"title": title, "body": body, "html_url": f"https://github.com/x/y/issues/{n}",
            "created_at": "2026-10-27T05:57:44Z", "labels": [], "comments": 0, "reactions": {"+1": 0}}


class IssueExcludeTest(unittest.TestCase):
    def run_search(self, items):
        old = update.http_get_json
        update.http_get_json = lambda *_a, **_k: {"items": items}
        update._last_search[0] = 0.0
        try:
            return update.breakage_reports("SteamDeckHomebrew/decky-loader", "2026-10-27T04:26:19Z", "3.9", None,
                                           None, DECKY["issues_exclude_re"])
        finally:
            update.http_get_json = old

    def test_frame_and_dev_builds_excluded(self):
        got = self.run_search([
            item(1005, "[BUG] Frame build installs a broken service on update", FRAME_BODY),
            item(1, "[BUG] Decky broken after SteamOS update", FRAME_BODY.replace("0.6.0 VR", "3.9.1")),  # dev build
            item(2, "Decky not working on Steam Frame", DECK_BODY),
        ])
        self.assertEqual(got, [])

    def test_stable_deck_report_kept(self):
        got = self.run_search([item(7, "[BUG] Decky broken after SteamOS 3.9 update", DECK_BODY)])
        self.assertEqual([r["url"].rsplit("/", 1)[1] for r in got], ["7"])

    def test_no_exclude_keeps_everything(self):
        old = update.http_get_json
        update.http_get_json = lambda *_a, **_k: {"items": [item(1005, "[BUG] Frame build installs a broken service on update", FRAME_BODY)]}
        update._last_search[0] = 0.0
        try:
            got = update.breakage_reports("r/r", "2026-10-27T04:26:19Z", "3.9")
        finally:
            update.http_get_json = old
        self.assertEqual(len(got), 1)


if __name__ == "__main__":
    unittest.main()
