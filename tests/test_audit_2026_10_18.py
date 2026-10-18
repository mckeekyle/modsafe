"""Regressions found in the 2026-10-18 site audit."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import update  # noqa: E402
from games import GAMES_BY_SLUG  # noqa: E402
from status_logic import (  # noqa: E402
    V_NOT_PORTED, V_SAFE, V_WAIT, determine_framework_status, make_mention_fn, manual_build_drift, manual_hook_verdict,
)


class TestGtaPerEdition(unittest.TestCase):
    """GTA V showed Safe while Enhanced (1.0.1158.16, Sep 15) had no Script Hook V build: a flat list hid
    which edition lagged and the Enhanced update was never recorded."""
    sup = ["1.0.3889.0", "1.0.1158.13"]
    cur = {"legacy": "1.0.3889.0", "enhanced": "1.0.1158.16"}

    def test_lagging_edition_is_named(self):
        v = manual_hook_verdict(supported=self.sup, current=self.cur, patch_age=96, verified_age=0,
                                build_ages={"legacy": 96, "enhanced": 33})
        self.assertEqual(v["status"], V_NOT_PORTED)
        self.assertIn("Supports Legacy 1.0.3889.0", v["reason"])
        self.assertIn("No build yet for Enhanced 1.0.1158.16", v["reason"])

    def test_per_edition_age_decides_wait(self):
        v = manual_hook_verdict(supported=self.sup, current=self.cur, patch_age=96, verified_age=0,
                                build_ages={"legacy": 96, "enhanced": 2})
        self.assertEqual(v["status"], V_WAIT)

    def test_both_supported_is_safe(self):
        v = manual_hook_verdict(supported=self.sup, current={"legacy": "1.0.3889.0", "enhanced": "1.0.1158.13"},
                                patch_age=10, verified_age=0)
        self.assertEqual(v["status"], V_SAFE)
        self.assertIn("Enhanced 1.0.1158.13", v["reason"])

    def test_list_form_still_works(self):
        self.assertEqual(manual_hook_verdict(supported=self.sup, current=self.sup, patch_age=9, verified_age=0)["status"], V_SAFE)

    def test_build_drift(self):
        rec = {"legacy": "24129523", "enhanced": "25261616"}
        same = {"legacy": {"buildid": "24129523", "published_at": "x"}, "enhanced": {"buildid": "25261616", "published_at": "y"}}
        self.assertEqual(manual_build_drift(rec, same), [])
        moved = dict(same, enhanced={"buildid": "26000000", "published_at": "2026-10-20T00:00:00Z"})
        d = manual_build_drift(rec, moved)
        self.assertEqual([(x["edition"], x["buildid"]) for x in d], [("enhanced", "26000000")])
        # failed lookups / unrecorded editions never invent a change
        self.assertEqual(manual_build_drift(rec, {"legacy": None, "enhanced": {"buildid": None}}), [])
        self.assertEqual(manual_build_drift({}, moved), [])

    def test_committed_record(self):
        d = json.loads((ROOT / "data/manual/gta-v.json").read_text())
        lp = d["latest_patch"]
        self.assertEqual(set(lp["steam_builds"]), {"legacy", "enhanced"})
        self.assertEqual(set(lp["build_dates"]), {"legacy", "enhanced"})
        self.assertNotIn("://www.dev-c.com", (ROOT / "src/update.py").read_text())
        self.assertNotIn("://dev-c.com", (ROOT / "src/update.py").read_text())


class TestSilentPatches1018(unittest.TestCase):
    def test_new_entries_are_sourced(self):
        want = {"elden-ring": "1.17.1", "baldurs-gate-3": "Update 4.1.1.7631656",
                "msfs-2020": "Sim Update 16.1", "rimworld": "1.6.4871"}
        for slug, label in want.items():
            sp = update.silent_patches_for(slug)
            hit = [p for p in sp if p["label"] == label]
            self.assertTrue(hit, slug)
            self.assertTrue(hit[0].get("sources"), slug)
            self.assertTrue(hit[0].get("published_at"), slug)


class TestBreakageClaims(unittest.TestCase):
    def test_no_claim_without_tracker_or_search(self):
        self.assertIn("No open breakage reports 40 days", update.quiet_period_note(40.2, "a/b", True))
        for repo, searched in ((None, False), ("a/b", False), (None, True)):
            n = update.quiet_period_note(40, repo, searched)
            self.assertNotIn("No open breakage", n)
            self.assertIn("no breakage signal available", n)

    def test_seamless_coop_has_no_issue_tracker(self):
        fw = next(f for f in GAMES_BY_SLUG["elden-ring"]["frameworks"] if f["id"].startswith("seamless"))
        self.assertTrue(fw.get("no_issue_tracker"))
        self.assertIn("yuiamoroll/", fw["repo"])


class TestRangeMentionWording(unittest.TestCase):
    mfn = staticmethod(make_mention_fn("1.4.8", r"(?<![\w.])v?{v}\b", None))  # Bannerlord rule

    def test_series_match_does_not_claim_exact_mention(self):
        v = determine_framework_status(release_published_at="2026-10-17T00:00:00Z", release_notes="Supports v1.4.x",
                                       release_tag="v1.7.5", patch_version="BL v1.4.8",
                                       patch_published_at="2026-08-10T00:00:00Z", mention_fn=self.mfn)
        self.assertIn("series/range", v["reason"])
        exact = determine_framework_status(release_published_at="2026-10-17T00:00:00Z", release_notes="Fixes for v1.4.8",
                                           release_tag="v1.7.5", patch_version="BL v1.4.8",
                                           patch_published_at="2026-08-10T00:00:00Z", mention_fn=self.mfn)
        self.assertTrue(exact["mentions_patch"])
        self.assertNotIn("series/range", exact["reason"])


class TestOfficialPageReason(unittest.TestCase):
    def test_safe_by_official_page_is_not_also_unverified(self):
        """F4SE/SFSE said "lists build X for runtime Y" and then "compatibility is unverified" in one reason."""
        for slug in ("fallout-4", "starfield", "skyrim-se"):
            d = json.loads((ROOT / f"data/games/{slug}.json").read_text())
            for f in d["frameworks"]:
                if (f.get("official") or {}).get("supports_current"):
                    self.assertNotIn("unverified", f["reason"], slug)
                    self.assertNotIn("predates", f["reason"], slug)


class TestBuildCopy(unittest.TestCase):
    def test_manual_not_ported_sentence_names_edition(self):
        import build
        g = GAMES_BY_SLUG["gta-v"]
        d = {"verdict": V_NOT_PORTED, "game": {"latest_patch": {"label": "Title Update 1.73"}},
             "frameworks": [{"name": "Script Hook V", "short": "SHV", "status": V_NOT_PORTED, "tracked": True,
                             "reason": "Supports Legacy 1.0.3889.0. No build yet for Enhanced 1.0.1158.16. (Manually verified 2026-10-18.)"}]}
        s = build.verdict_sentence(g, d)
        self.assertIn("No build yet for Enhanced 1.0.1158.16", s)
        self.assertNotIn("Manually verified", s)

    def test_doom_source_copy_is_readable(self):
        import build
        g = GAMES_BY_SLUG["doom-the-dark-ages"]
        self.assertNotEqual(build.fw_sources(g), "atlan")
        self.assertIn("Atlan patcher", build.fw_sources(g))


if __name__ == "__main__":
    unittest.main()
