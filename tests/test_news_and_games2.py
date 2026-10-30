"""News feed + new games + site organization tests (no network)."""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import news  # noqa: E402
from games import GAMES_BY_SLUG  # noqa: E402
from status_logic import detect_patch  # noqa: E402

RSS = """<?xml version="1.0"?><rss><channel>
<item><title><![CDATA[Valheim patch 1.0.21 fixes boats]]></title><link>https://ex.com/a</link><pubDate>Wed, 14 Oct 2026 10:00:00 GMT</pubDate><description>BODY TEXT</description></item>
<item><title>Some unrelated game review</title><link>https://ex.com/b</link><pubDate>Tue, 13 Oct 2026 10:00:00 GMT</pubDate></item>
<item><title>Old Skyrim update news</title><link>https://ex.com/c</link><pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""


class TestNews(unittest.TestCase):
    def test_parse_headline_only(self):
        items = news.parse_rss(RSS, "Ex")
        self.assertEqual(len(items), 3)
        self.assertNotIn("BODY TEXT", json.dumps(items))
        self.assertEqual(items[0]["games"], ["valheim"])

    def test_merge_highlight_and_age(self):
        now = datetime(2026, 10, 15, tzinfo=timezone.utc)
        steam = [{"title": "Fallout 4 Creation Kit Update - October 15", "url": "s1", "source": "Steam", "published_at": "2026-10-15T00:00:00Z",
                  "games": ["fallout-4"], "kind": "announcement"},
                 {"title": "Patch 1.0.20", "url": "s2", "source": "Steam", "published_at": "2026-10-15T00:00:00Z", "games": ["valheim"], "kind": "patch"}]
        out = news.merge(news.parse_rss(RSS, "Ex") + steam, now=now)
        by = {i["url"]: i for i in out}
        self.assertTrue(by["https://ex.com/a"]["highlight"])
        self.assertFalse(by["https://ex.com/b"]["highlight"])
        self.assertNotIn("https://ex.com/c", by)  # older than MAX_AGE_DAYS
        self.assertFalse(by["s1"]["highlight"])  # CK update is not a game patch
        self.assertTrue(by["s2"]["highlight"])

    def test_tagging(self):
        self.assertEqual(news.tag_games("Elden Ring Nightreign gets DLC"), [])
        self.assertTrue({"gta-v-legacy", "gta-v-enhanced"} <= set(news.tag_games("GTA 5 mods are great")))
        self.assertIn("baldurs-gate-3", news.tag_games("Baldur's Gate 3 patch"))


class TestNewGameRules(unittest.TestCase):
    def check(self, slug, title, v):
        d = detect_patch(title, GAMES_BY_SLUG[slug]["patch_rule"])
        self.assertEqual(d["version"] if d else None, v, title)

    def test_rules(self):
        self.check("starfield", "Starfield Update 1.16.244 – June 11, 2026", "1.16.244")
        self.check("starfield", "Everything in Starfield’s Free Lanes Update & Terran Armada DLC", None)
        self.check("elden-ring", "Patch Notes Version 1.17", "1.17")
        self.check("elden-ring", "ELDEN RING - Patch Notes Version 1.16.1", "1.16.1")
        self.check("valheim", "Patch 1.0.20", "1.0.20")
        self.check("valheim", "Patch 0.221.13 (Public Test)", None)
        self.check("terraria", "Terraria 1.4.5.7 - Out Now for PC! (Console/Mobile Soon)", "1.4.5.7")
        self.check("terraria", "Terraria State of the Game - September 2026", None)
        self.check("rimworld", "Update 1.6.4850 released", "1.6.4850")
        self.check("rimworld", "Announcing the Waylith Engine and Update 1.7", None)
        self.check("bannerlord", "War Sails Modding Kit Release & Patch WS v1.2.8 / BL v1.4.8", "1.4.8")
        self.check("bannerlord", "Beta Patch Notes - WS v1.3.0 / BL v1.5.0", None)


class TestOrganization(unittest.TestCase):
    def test_games_menu_and_pages(self):
        import build
        html = build.page_shell("t", "d", "/", "home", "x")
        self.assertIn('class="games-menu"', html)
        self.assertIn('href="/games/"', html)
        for slug in ("starfield", "elden-ring", "bannerlord"):
            self.assertIn(f'href="/{slug}/"', html)
        self.assertIn("/games/", build.sitemap_urls())
        self.assertIn("/news/", build.sitemap_urls())


if __name__ == "__main__":
    unittest.main()


class TestPolish(unittest.TestCase):
    def test_og_tags(self):
        import build
        html = build.page_shell("t", "d", "/skyrim-se/", "skyrim-se", "x")
        self.assertIn('content="https://modsafe.app/og/skyrim-se.png"', html)
        self.assertIn('summary_large_image', html)
        self.assertIn('og:image:width" content="1200"', html)
        self.assertIn('/og/default.png', build.page_shell("t", "d", "/faq/", "faq", "x"))
        root = Path(__file__).resolve().parents[1]
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow not installed")
        for slug in ("default", "skyrim-se", "minecraft"):
            with Image.open(root / "static/og" / f"{slug}.png") as im:
                self.assertEqual(im.size, (1200, 630))

    def test_around_pc_prefers_relevant(self):
        import build
        mk = lambda t, d: {"title": t, "url": t, "source": "x", "published_at": d, "games": []}
        items = [mk("Razer mouse deal 40% off", "2026-10-15T00:00:00Z"), mk("Big RPG gets mod support on PC", "2026-10-14T00:00:00Z"),
                 mk("Studio layoffs", "2026-10-13T00:00:00Z")]
        out = [i["title"] for i in build.around_pc(items)]
        self.assertEqual(out[0], "Big RPG gets mod support on PC")
        self.assertNotIn("Razer mouse deal 40% off", out)

    def test_footer_and_shortcut(self):
        import build
        html = build.page_shell("t", "d", "/", "home", "x")
        self.assertIn('class=more', html)
        self.assertIn('All games →', html)
        self.assertIn("e.key==='/'", build.FILTER_JS)
        self.assertIn("time.ago", build.FILTER_JS)


class TestCacheBusting(unittest.TestCase):
    def test_css_versioned_and_headers(self):
        import build
        html = build.page_shell("t", "d", "/", "home", "x")
        self.assertIn(f'/styles.css?v={build.CSS_VER}', html)
        self.assertIn("immutable", build.HEADERS)
        self.assertIn(".games-menu:not([open]) .menu-pop { display: none; }", build.CSS)


class TestSteamDeck(unittest.TestCase):
    def test_stable_vs_beta_rule(self):
        from games import GAMES_BY_SLUG
        from status_logic import detect_patch
        g = GAMES_BY_SLUG["steam-deck"]
        self.assertEqual(detect_patch("SteamOS 3.8.28", g["patch_rule"])["version"], "3.8.28")
        for t in ("SteamOS 3.9.2 Beta", "SteamOS 3.9.1 Preview", "Steam Client Update: October 13th"):
            self.assertIsNone(detect_patch(t, g["patch_rule"]), t)
        import re
        self.assertTrue(re.search(g["channels"][0]["include"], "SteamOS 3.9.2 Beta", re.I))
        self.assertEqual(g["genre"], "Platform")
        self.assertFalse(g["frameworks"][0].get("agnostic"))  # Decky drives the verdict

    def test_decky_store_adapter(self):
        import update
        update._decky_cache[:] = [{"name": "PowerTools", "versions": [{"name": "2.0.3", "created": "2024-06-18T14:02:00Z"}]}]
        r = update.releases_decky_store({"package": "PowerTools", "url": "u"})
        self.assertEqual((r[0]["tag_name"], r[0]["prerelease"]), ("2.0.3", False))
        update._decky_cache.clear()


class TestMSFS(unittest.TestCase):
    def test_sim_update_rule(self):
        from games import GAMES_BY_SLUG
        from status_logic import detect_patch
        r = GAMES_BY_SLUG["msfs-2024"]["patch_rule"]
        self.assertEqual(detect_patch("Sim Update 7 Release Notes [1.9.18.0] - Available Now", r)["version"], "7")
        self.assertEqual(detect_patch("Release Notes - Sim Update 16 [1.39.9.0] Now Available", r)["version"], "16")
        self.assertEqual(detect_patch("Sim Update 5.1 Release Notes [1.7.35.0] - Available Now", r)["version"], "5.1")
        for t in ("Sim Update 16 Beta [1.39.0.0] Available Now!", "World Update 22: United States National Parks",
                  "October 15th, 2026 MSFS Weekly Briefing", "City Update 13: California Now Available"):
            self.assertIsNone(detect_patch(t, r), t)

    def test_fsuipc_parse_and_tag_prefix(self):
        import update
        orig = update.http_get_text
        update.http_get_text = lambda *_a, **_k: "<p>FSUIPC7</p> Version 7.5.9 <b>Released 29/09/2026</b>".replace("<p>FSUIPC7</p>", "FSUIPC7")
        try:
            r = update.releases_fsuipc({})[0]
        finally:
            update.http_get_text = orig
        self.assertEqual((r["tag_name"], r["published_at"][:10]), ("7.5.9", "2026-09-29"))
        orig_j = update.http_get_json
        update.http_get_json = lambda *_a, **_k: [{"tag_name": "v2020.15.0"}, {"tag_name": "v2024.1.0"}]
        try:
            self.assertEqual([x["tag_name"] for x in update.releases_github({"repo": "x/y", "tag_prefix": "v2024."})], ["v2024.1.0"])
        finally:
            update.http_get_json = orig_j


class TestMinecraftBuildRuns(unittest.TestCase):
    def test_build_minecraft_with_fixtures(self):
        """Regression: a NameError in build_minecraft silently kept stale data for hours."""
        import update
        from games import GAMES_BY_SLUG
        fx = {
            update.MC_MANIFEST: {"latest": {"release": "26.3", "snapshot": "x"},
                                 "versions": [{"id": "26.3", "type": "release", "releaseTime": "2026-09-15T11:23:02+00:00"}]},
            update.FABRIC_GAME: [{"version": "26.3", "stable": True}],
            update.FABRIC_LOADER: [{"version": "0.19.5", "stable": True}],
            update.FORGE_PROMOS: {"promos": {"26.3-latest": "66.0.12"}},
            update.NEOFORGE_VERSIONS: {"versions": ["26.3.0.84"]},
        }
        orig = update.http_get_json
        update.http_get_json = lambda url, *a, **k: fx.get(url, [{"version_number": "1.0", "game_versions": ["26.3"],
                                                                   "version_type": "release", "date_published": "2026-09-20T00:00:00Z"}])
        try:
            out = update.build_game(GAMES_BY_SLUG["minecraft"])
        finally:
            update.http_get_json = orig
        self.assertEqual(out["game"]["latest_patch"]["label"], "26.3")
        self.assertTrue(all(f["status"] for f in out["frameworks"]))


class TestConfirmedBreakage(unittest.TestCase):
    def test_single_unlabeled_report_is_not_confirmed(self):
        from status_logic import confirmed_breakage
        one = [{"title": "crash after 1.17", "labels": [], "thumbs_up": 0}]
        self.assertEqual(confirmed_breakage(one), [])
        self.assertEqual(len(confirmed_breakage([{**one[0], "labels": ["bug"]}])), 1)
        self.assertEqual(len(confirmed_breakage([{**one[0], "thumbs_up": 3}])), 1)
        self.assertEqual(len(confirmed_breakage(one * 2)), 2)
