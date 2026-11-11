"""Discord alert script: change detection, message shape, state handling (no network)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "discord-alerts"))

import modsafe_alerts as ma  # noqa: E402


def game(gid, verdict, label, sev, patch="Patch 1.0"):
    return {"id": gid, "name": gid.title(), "verdict": verdict, "verdict_label": label, "severity": sev,
            "current_patch": {"label": patch, "published_at": "2026-11-05T00:00:00Z"},
            "page_url": f"https://modsafe.app/{gid}/"}


def feed(*games):
    return {"disclaimer": "Not guarantees.", "games": list(games)}


class Args:
    def __init__(self, state, **kw):
        self.state, self.games, self.webhook, self.feed = state, None, None, ma.FEED_URL
        self.dry_run = self.announce_current = False
        self.__dict__.update(kw)


class TestChanges(unittest.TestCase):
    def test_only_verdict_changes_reported(self):
        old = ma.snapshot(feed(game("repo", "wait", "Just patched, wait", 2), game("skyrim-se", "safe", "Safe", 7)))
        new = ma.snapshot(feed(game("repo", "likely-safe", "Likely safe", 5),
                               game("skyrim-se", "safe", "Safe", 7, patch="Patch 9"),
                               game("new-game", "wait", "Just patched, wait", 2)))
        ch = ma.find_changes(old, new)
        self.assertEqual([c["id"] for c in ch], ["repo"])
        self.assertEqual(ma.direction(ch[0]["old"], ch[0]["new"]), "better")

    def test_game_filter(self):
        s = ma.snapshot(feed(game("repo", "wait", "W", 2), game("skyrim-se", "safe", "S", 7)), {"repo"})
        self.assertEqual(list(s), ["repo"])

    def test_embed_has_game_verdict_and_link(self):
        old = {"verdict": "safe", "verdict_label": "Safe", "severity": 7}
        new = ma.snapshot(feed(game("repo", "broken", "Breakage reported", 0)))["repo"]
        msgs = ma.build_messages([{"id": "repo", "old": old, "new": new}], "Not guarantees.")
        e = msgs[0]["embeds"][0]
        self.assertIn("Repo", e["title"])
        self.assertIn("Breakage reported", e["title"])
        self.assertEqual(e["url"], "https://modsafe.app/repo/")
        self.assertIn("https://modsafe.app/repo/", e["description"])
        self.assertEqual(msgs[0]["allowed_mentions"], {"parse": []})
        self.assertIn("Worse", json.dumps(e, ensure_ascii=False))

    def test_retired_combined_entry_skipped_unless_asked(self):
        hub = {**game("gta-v", "wait", "W", 2), "deprecated": True}
        f = feed(hub, game("gta-v-enhanced", "wait", "W", 2))
        self.assertEqual(list(ma.snapshot(f)), ["gta-v-enhanced"])
        self.assertEqual(list(ma.snapshot(f, {"gta-v"})), ["gta-v"])

    def test_alert_names_the_mods_behind_a_bad_verdict(self):
        g = game("skyrim-se", "broken", "Breakage reported", 0)
        g["updated_at"] = "2026-11-11T00:50:04Z"
        g["mods"] = [{"name": "SKSE", "verdict": "safe", "counts_toward_verdict": True, "release": "v2.3.1"},
                     {"name": "Engine Fixes", "verdict": "broken", "counts_toward_verdict": True, "release": "7.0.21"},
                     {"name": "Address Library", "verdict": "broken", "counts_toward_verdict": False}]
        new = ma.snapshot(feed(g))["skyrim-se"]
        e = ma.build_embed({"id": "skyrim-se", "old": {"verdict": "safe", "verdict_label": "Safe", "severity": 7}, "new": new})
        field = [f for f in e["fields"] if f["name"] == "Breakage reported in"]
        self.assertEqual(field[0]["value"], "• Engine Fixes (7.0.21)")
        self.assertEqual(e["timestamp"], "2026-11-11T00:50:04Z")
        g2 = game("repo", "safe", "Safe", 7)
        g2["mods"] = [{"name": "X", "verdict": "safe", "counts_toward_verdict": True}]
        e2 = ma.build_embed({"id": "repo", "old": {"verdict": "wait"}, "new": ma.snapshot(feed(g2))["repo"]})
        self.assertEqual([f["name"] for f in e2["fields"]], ["Game patch", "Trend"])

    def test_messages_split_at_ten_embeds(self):
        ch = [{"id": str(i), "old": {"verdict": "wait"}, "new": ma.snapshot(feed(game(f"g{i}", "safe", "Safe", 7)))[f"g{i}"]}
              for i in range(23)]
        self.assertEqual([len(m["embeds"]) for m in ma.build_messages(ch)], [10, 10, 3])

    def test_webhook_check(self):
        self.assertTrue(ma.check_webhook("https://discord.com/api/webhooks/1/abc"))
        with self.assertRaises(SystemExit):
            ma.check_webhook("https://example.com/hook")
        with self.assertRaises(SystemExit):
            ma.check_webhook(None)


class TestRun(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "state.json"

    def test_first_run_records_without_posting(self):
        with mock.patch.object(ma, "post") as p:
            self.assertEqual(ma.run_once(Args(self.state), feed(game("repo", "wait", "W", 2))), 0)
        p.assert_not_called()
        self.assertEqual(json.loads(self.state.read_text())["games"]["repo"]["verdict"], "wait")

    def test_change_posts_then_saves(self):
        ma.run_once(Args(self.state), feed(game("repo", "wait", "W", 2)))
        with mock.patch.object(ma, "post") as p:
            rc = ma.run_once(Args(self.state, webhook="https://discord.com/api/webhooks/1/x"),
                             feed(game("repo", "likely-safe", "Likely safe", 5)))
        self.assertEqual(rc, 0)
        p.assert_called_once()
        self.assertEqual(json.loads(self.state.read_text())["games"]["repo"]["verdict"], "likely-safe")
        with mock.patch.object(ma, "post") as p:  # same verdict again: nothing posted
            ma.run_once(Args(self.state, webhook="https://discord.com/api/webhooks/1/x"),
                        feed(game("repo", "likely-safe", "Likely safe", 5)))
        p.assert_not_called()

    def test_failed_post_keeps_old_state_for_retry(self):
        ma.run_once(Args(self.state), feed(game("repo", "wait", "W", 2)))
        with mock.patch.object(ma, "post", side_effect=RuntimeError("HTTP 404")):
            rc = ma.run_once(Args(self.state, webhook="https://discord.com/api/webhooks/1/x"),
                             feed(game("repo", "safe", "Safe", 7)))
        self.assertEqual(rc, 1)
        self.assertEqual(json.loads(self.state.read_text())["games"]["repo"]["verdict"], "wait")

    def test_dry_run_never_posts_or_saves(self):
        ma.run_once(Args(self.state), feed(game("repo", "wait", "W", 2)))
        with mock.patch.object(ma, "post") as p:
            ma.run_once(Args(self.state, dry_run=True), feed(game("repo", "safe", "Safe", 7)))
        p.assert_not_called()
        self.assertEqual(json.loads(self.state.read_text())["games"]["repo"]["verdict"], "wait")

    def test_filtered_state_keeps_other_games(self):
        ma.run_once(Args(self.state), feed(game("repo", "wait", "W", 2), game("skyrim-se", "safe", "S", 7)))
        ma.run_once(Args(self.state, games="repo", dry_run=False), feed(game("repo", "wait", "W", 2), game("skyrim-se", "safe", "S", 7)))
        self.assertIn("skyrim-se", json.loads(self.state.read_text())["games"])


if __name__ == "__main__":
    unittest.main()
