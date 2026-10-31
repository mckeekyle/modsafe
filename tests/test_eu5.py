"""Europa Universalis V: registry, patch rule, Workshop verdict rules (major vs hotfix), rollback branch, pages, API, art."""
import json
import sys
import tempfile
import time
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import update  # noqa: E402
from games import GAMES, GAMES_BY_SLUG  # noqa: E402
from status_logic import (V_BROKEN, V_LIKELY, V_NODATA, V_NOT_PORTED, V_WAIT, detect_patch, rollback_branch,  # noqa: E402
                          series_release, version_series, workshop_mod_verdict)

SLUG = "europa-universalis-v"
G = GAMES_BY_SLUG[SLUG]
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


def iso(dt):
    return dt.isoformat().replace("+00:00", "Z")


def ago(days):
    return datetime.now(timezone.utc) - timedelta(days=days)


class TestRegistry(unittest.TestCase):
    def test_config(self):
        self.assertIn(SLUG, [g["slug"] for g in GAMES])
        self.assertEqual(G["steam_appid"], 3450310)
        self.assertEqual(G["kind"], "workshop")
        fws = G["frameworks"]
        self.assertEqual(fws[0]["id"], "cmf")
        self.assertEqual(fws[0]["workshop_id"], "3692202776")
        self.assertTrue(8 <= len(fws) <= 10)
        for fw in fws:
            self.assertEqual(fw["source"], "workshop")
            self.assertEqual(fw["url"], f"https://steamcommunity.com/sharedfiles/filedetails/?id={fw['workshop_id']}")
            self.assertFalse(fw.get("agnostic"))
        self.assertIn("workshop", update.SOURCES)

    def test_mods_list_matches_frameworks(self):
        d = json.loads((ROOT / "data/mods" / f"{SLUG}.json").read_text(encoding="utf-8"))
        self.assertEqual([m["framework_id"] for m in d["mods"]], [f["id"] for f in G["frameworks"]])
        cm = next(m for m in d["mods"] if m["id"] == "construction-manager")
        self.assertEqual(cm["requires"], ["cmf"])  # Workshop "Required items"

    def test_news_alias_and_branches(self):
        import guides
        import news as news_mod
        self.assertIn(SLUG, news_mod.tag_games("Europa Universalis V Update 1.4 is out"))
        self.assertIn(SLUG, news_mod.tag_games("EU5 hotfix lands"))
        self.assertNotIn(SLUG, news_mod.tag_games("Europa Universalis IV turns 13"))
        b = guides.load_branches()
        self.assertEqual(b["games"][SLUG]["rollback"][0]["branch"], "1.3.11")
        self.assertIn("1.3.11", guides.branch_summary(SLUG))
        self.assertIn("Oct 30, 2026", guides.branch_summary(SLUG))  # per-game verified date


class TestPatchRule(unittest.TestCase):
    def test_live_posts(self):
        r = G["patch_rule"]
        for t, v in (("Hotfix 1.4.6", "1.4.6"), ('Update 1.4 "Rio Salado" is out now!', "1.4"), ("Patch 1.3.11", "1.3.11"),
                     ("Update 1.3 - Out Now!", "1.3"), ("Patch 1.2.5 Out Now", "1.2.5"), ("Hotfix 1.2.3 Out Now + Progress Update", "1.2.3"),
                     ("Update 1.1 Rossbach Live Now", "1.1"), ("Patch 1.0.02", "1.0.02"),
                     ("Europa Universalis V - 1.0.5 Patch Notes", "1.0.5")):
            self.assertEqual(detect_patch(t, r)["version"], v, t)

    def test_not_patches(self):
        r = G["patch_rule"]
        for t in ("[Beta Version] Patch Notes - 1.3.10", "Open Beta 1.3 Live Now!", "1.1.0 Rossbach now in Open Beta!",
                  "Beta patch 1.0.10 is out now", "1.0.8 Open Beta", "Update 1.3 - Official Community Feedback Survey",
                  "Tinto Talks #109 - Patch 1.2.4 Thoughts and Pavia Preview", "Fate of the Phoenix + Update 1.2 Release Date",
                  "Tinto Talks #119 - Politics & Diplomacy [Update 1.4 Preview]", "Across the Pillars is out now!"):
            self.assertIsNone(detect_patch(t, r), t)


class TestWorkshopVerdict(unittest.TestCase):
    S14 = "2026-10-28T17:07:25Z"

    def v(self, **kw):
        args = dict(tags=[], updated_at="2026-10-29T10:00:00Z", series="1.4", series_released_at=self.S14,
                    patch_label="1.4", is_major=True, now=NOW)
        args.update(kw)
        return workshop_mod_verdict(**args)

    def test_major_not_updated_waits(self):
        r = self.v(updated_at="2026-08-18T00:00:00Z", tags=["1.3"])
        self.assertEqual(r["status"], V_WAIT)
        self.assertIn("before 1.4 went live", r["reason"])

    def test_beta_era_tag_is_not_enough(self):
        # CMF on 2026-10-30: tagged 1.3 + 1.4, but last updated 2026-10-03 during the 1.4 open beta.
        r = self.v(updated_at="2026-10-03T08:32:15Z", tags=["Utilities", "User Interface", "1.3", "1.4"])
        self.assertEqual(r["status"], V_WAIT)
        self.assertTrue(r["tagged"])
        self.assertIn("open-beta", r["reason"])

    def test_major_updated_after_release_is_likely_safe(self):
        r = self.v(tags=["1.4"])
        self.assertEqual(r["status"], V_LIKELY)
        self.assertIn("carries the 1.4 version tag", r["reason"])
        r = self.v(tags=["Map"])  # no version tags: inferred from the update date
        self.assertEqual(r["status"], V_LIKELY)
        self.assertIn("inferred from the update date", r["reason"])
        self.assertNotIn("hotfix", r["reason"])

    def test_release_day_grace(self):
        self.assertEqual(self.v(updated_at="2026-10-28T09:00:00Z")["status"], V_LIKELY)  # hours before the post
        self.assertEqual(self.v(updated_at="2026-10-26T09:00:00Z")["status"], V_WAIT)

    def test_hotfix_within_series(self):
        r = self.v(patch_label="1.4.6", is_major=False, tags=["User Interface"], ui=True)
        self.assertEqual(r["status"], V_LIKELY)
        self.assertIn("hotfix within 1.4", r["reason"])
        self.assertIn("UI mods can still break", r["reason"])
        r = self.v(patch_label="1.4.6", is_major=False, tags=["Map"])
        self.assertNotIn("UI mods", r["reason"])
        # A hotfix doesn't excuse a mod that never updated for the series.
        self.assertEqual(self.v(patch_label="1.4.6", is_major=False, updated_at="2026-09-01T00:00:00Z")["status"], V_WAIT)

    def test_old_series(self):
        later = NOW + timedelta(days=20)
        self.assertEqual(self.v(updated_at="2026-09-01T00:00:00Z", tags=["1.3"], now=later)["status"], V_NOT_PORTED)
        self.assertEqual(self.v(updated_at="2026-09-01T00:00:00Z", tags=[], now=later)["status"], V_LIKELY)
        self.assertEqual(self.v(updated_at="2026-10-03T00:00:00Z", tags=["1.4"], now=later)["status"], V_LIKELY)

    def test_missing_dates(self):
        self.assertEqual(self.v(updated_at=None)["status"], V_NODATA)

    def test_helpers(self):
        self.assertEqual(version_series("1.4.6"), "1.4")
        self.assertEqual(version_series("1.4"), "1.4")
        self.assertIsNone(version_series(None))
        patches = [{"version": "1.4.6", "label": "1.4.6", "published_at": "2026-10-30T10:00:27Z"},
                   {"version": "1.4", "label": "1.4", "published_at": "2026-10-28T17:07:25Z"},
                   {"version": "1.3.11", "label": "1.3.11", "published_at": "2026-07-16T00:00:00Z"}]
        self.assertEqual(series_release(patches, "1.4")["label"], "1.4")
        br = ["1.0.10", "1.0.11", "1.1.10", "1.2.0", "1.2.4", "1.2.5", "1.3.10", "1.3.11", "1.4-open-beta", "1.3.8-open-beta"]
        self.assertEqual(rollback_branch(br, "1.4.0"), "1.3.11")
        self.assertEqual(rollback_branch(br, "1.3.0"), "1.2.5")
        self.assertIsNone(rollback_branch(br, "1.0.0"))


class _NoSleep:
    def __getattr__(self, name):
        return getattr(time, name)

    @staticmethod
    def sleep(_s):
        return None


def news(*items):
    return {"appnews": {"newsitems": [{"gid": str(i), "title": t, "date": int(d.timestamp()), "url": f"https://x/{i}"}
                                      for i, (t, d) in enumerate(items)]}}


def pics(buildid, dt, branches=()):
    br = {"public": {"buildid": str(buildid), "timeupdated": str(int(dt.timestamp()))}}
    for b in branches:
        br[b] = {"buildid": "1", "timeupdated": "1", "description": b}
    return {"status": "success", "data": {"3450310": {"depots": {"branches": br}}}}


class TestEndToEnd(unittest.TestCase):
    BRANCHES = ("1.3.11", "1.3.10", "1.2.5", "1.0.11", "1.4-open-beta", "1.4.3-prev_open_beta")

    def run_game(self, posts, build_at, updated, issues=()):
        saved = (update.http_get_json, update.http_post_form, update.DATA_DIR, update.time)
        tmp = tempfile.TemporaryDirectory()
        searched = []

        def get(url, *a, **k):
            if "GetNewsForApp" in url:
                return news(*posts)
            if "steamcmd" in url:
                return pics(26300913, build_at, self.BRANCHES)
            if "search/issues" in url:
                searched.append(url)
                return {"items": list(issues)}
            raise AssertionError(url)

        def post(url, fields, **k):
            ids = [v for k2, v in fields.items() if k2.startswith("publishedfileids")]
            return {"response": {"publishedfiledetails": [
                {"publishedfileid": i, "result": 1, "title": f"Mod {i}", "subscriptions": 10,
                 "time_updated": int(updated.get(i, updated["*"])[0].timestamp()),
                 "tags": [{"tag": t} for t in updated.get(i, updated["*"])[1]]} for i in ids]}}
        update.http_get_json, update.http_post_form, update.DATA_DIR, update.time = get, post, Path(tmp.name), _NoSleep()
        try:
            return update.build_game(G), searched
        finally:
            update.http_get_json, update.http_post_form, update.DATA_DIR, update.time = saved
            tmp.cleanup()

    def test_fresh_major_waits_on_cmf(self):
        major = ago(2)
        posts = (('Update 1.4 "Rio Salado" is out now!', major), ("Patch 1.3.11", ago(100)), ("Update 1.3 - Out Now!", ago(110)))
        d, searched = self.run_game(posts, major, {"*": (ago(1), ["1.4"]), "3692202776": (ago(27), ["1.3", "1.4"])})
        self.assertEqual(d["verdict"], V_WAIT)
        lp = d["game"]["latest_patch"]
        self.assertEqual((lp["label"], lp["series"], lp["is_major"]), ("1.4", "1.4", True))
        self.assertEqual(lp["rollback_branch"], "1.3.11")
        self.assertNotIn("1.4-open-beta", lp["rollback_branches"])
        cmf = d["frameworks"][0]
        self.assertEqual(cmf["status"], V_WAIT)
        self.assertIn("Workshop comments since 1.4", cmf["reason"])  # hand-checked note, shown while CMF lags
        self.assertTrue(all(f["status"] == V_LIKELY for f in d["frameworks"][1:]))
        self.assertTrue(searched and "community-mod-framework" in searched[0])
        self.assertEqual(len(d["history"]), 3)

    def test_hotfix_after_mods_updated_is_likely_safe(self):
        posts = (("Hotfix 1.4.6", ago(1)), ('Update 1.4 "Rio Salado" is out now!', ago(3)), ("Patch 1.3.11", ago(100)))
        d, _ = self.run_game(posts, ago(1), {"*": (ago(2), ["User Interface", "1.4"])})
        self.assertEqual(d["verdict"], V_LIKELY)
        lp = d["game"]["latest_patch"]
        self.assertEqual((lp["label"], lp["series_label"], lp["is_major"]), ("1.4.6", "1.4", False))
        self.assertIn("UI mods can still break", d["frameworks"][1]["reason"])
        self.assertNotIn("Workshop comments", d["frameworks"][0]["reason"])  # CMF updated: note dropped

    def test_hand_note_stays_after_a_week_without_cmf_update(self):
        posts = (('Update 1.4 "Rio Salado" is out now!', ago(10)), ("Patch 1.3.11", ago(100)))
        d, _ = self.run_game(posts, ago(10), {"*": (ago(9), ["1.4"]), "3692202776": (ago(35), ["1.3", "1.4"])})
        cmf = d["frameworks"][0]
        self.assertEqual(cmf["status"], V_LIKELY)  # tagged 1.4, over a week, no confirmed breakage
        self.assertIn("Workshop comments since 1.4", cmf["reason"])  # but the user reports stay visible

    def test_confirmed_tracker_breakage_is_broken(self):
        posts = (('Update 1.4 "Rio Salado" is out now!', ago(3)), ("Patch 1.3.11", ago(100)))
        issues = [{"title": f"Crash after 1.4 update #{n}", "html_url": f"https://github.com/x/{n}",
                   "created_at": iso(ago(1)), "labels": []} for n in (1, 2)]
        d, _ = self.run_game(posts, ago(3), {"*": (ago(2), ["1.4"])}, issues=issues)
        self.assertEqual(d["frameworks"][0]["status"], V_BROKEN)
        self.assertEqual(d["verdict"], V_BROKEN)


class TestSiteAndApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build
        cls.build = build
        cls.games = dict((g["slug"], d) for g, d in build.load_games())
        cls.d = cls.games[SLUG]

    def test_data_file_is_real(self):
        d = self.d
        self.assertEqual(d["game"]["steam_appid"], 3450310)
        self.assertEqual(len(d["frameworks"]), len(G["frameworks"]))
        self.assertTrue(d["game"]["latest_patch"]["url"].startswith("https://store.steampowered.com/news/app/3450310/"))
        self.assertIn(d["verdict"], ("Safe", "Likely safe", "Just patched, wait", "Breakage reported", "Not ported yet"))

    def test_api_entry(self):
        a = self.build.api_v1_status(list(self.build.load_games()), today=date(2026, 10, 30), upcoming={})
        self.assertEqual(a["api_version"], 1)
        e = next(g for g in a["games"] if g["id"] == SLUG)
        self.assertEqual((e["steam_appid"], e["steam_appids"], e["kind"]), (3450310, [3450310], "game"))
        self.assertIn(e["verdict"], {"safe", "likely-safe", "wait", "broken", "not-ported", "no-data", "not-affected", "manual"})
        self.assertEqual([m["id"] for m in e["mods"]], [f["id"] for f in G["frameworks"]])

    def test_pages(self):
        b, d = self.build, self.d
        page = b.build_game_page(G, d)
        self.assertIn("1.37.5", page)  # EU4 is frozen, so EU5 is tracked
        self.assertIn("Is it safe to update Europa Universalis V?", page)
        self.assertIn('href="#mods"', page)
        mods_page = b.build_mods_page(G, d, b.mods_mod.load_mods(SLUG))
        self.assertIn("Get it on the Steam Workshop", mods_page)
        inst = b.build_install_page(G, d, b.mods_mod.load_guide(SLUG))
        self.assertIn("HowToStep", inst)
        self.assertIn("supported_game_version", inst)
        self.assertIn("1.3.11", inst)
        self.assertGreaterEqual(len(b.mods_mod.guide_parts(b.mods_mod.load_guide(SLUG))["steps"]), 5)
        urls = b.sitemap_urls()
        for p in ("", "mods/", "install/", "history/"):
            self.assertIn(f"/{SLUG}/{p}", urls)
        self.assertIn(f"/{SLUG}/", b.build_llms_txt(list(b.load_games())))

    def test_rollback_names_matching_branch(self):
        d = json.loads(json.dumps(self.d))
        d["verdict"] = "Just patched, wait"
        d["game"]["latest_patch"].update(rollback_branch="1.3.11", series="1.4", rollback_branch_series=None)
        html = self.build.rollback_callout(G, d)
        self.assertIn("<code>1.3.11</code>", html)
        self.assertIn("last version before 1.4", html)
        self.assertEqual(self.build.matching_branch_html({"game": {"latest_patch": {"label": "x"}}}), "")

    def test_art(self):
        for kind in ("cap", "hero"):
            ref = self.build.game_img(SLUG, kind)
            self.assertEqual(ref, f"/img/{SLUG}-{kind}.webp")
            self.assertTrue((ROOT / "static" / ref.lstrip("/")).is_file())
            self.assertRegex(self.build.busted(ref), r"\?v=[0-9a-f]{8}$")
        self.assertTrue((ROOT / "static/og" / f"{SLUG}.png").is_file())
        self.assertTrue((ROOT / "static/img" / f"{SLUG}.jpg").is_file())


class TestFastCheck(unittest.TestCase):
    def test_workshop_update_triggers_refresh(self):
        import fast_check

        class Fake:
            def steam_build(self, appid):
                return "26300913"

            def steam_news(self, appid):
                return []

            def workshop(self, ids):
                return {"3692202776": {"time_updated": "2026-10-31T09:00:00Z"}}

        g = {"slug": SLUG, "kind": "workshop", "steam_appid": 3450310, "patch_rule": G["patch_rule"],
             "frameworks": [{"id": "cmf", "short": "CMF", "source": "workshop", "workshop_id": "3692202776"},
                            {"id": "x", "short": "X", "source": "workshop", "workshop_id": "1"}]}
        d = {"game": {"latest_patch": {"label": "1.4.6", "steam_build": "26300913"}},
             "frameworks": [{"id": "cmf", "release_published_at": "2026-10-03T08:32:15Z"},
                            {"id": "x", "release_published_at": "2026-10-30T00:00:00Z"}]}
        self.assertEqual(fast_check.probe_game(g, d, Fake()),
                         ["CMF Workshop update 2026-10-03T08:32 -> 2026-10-31T09:00"])


if __name__ == "__main__":
    unittest.main()
