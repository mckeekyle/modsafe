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
        self.assertIn("gta-v", news.tag_games("GTA 5 mods are great"))
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
        from PIL import Image  # noqa: F401  (dev-only dependency; skip if missing)
        for slug in ("default", "skyrim-se", "minecraft"):
            self.assertEqual(Image.open(root / "static/og" / f"{slug}.png").size, (1200, 630))

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
