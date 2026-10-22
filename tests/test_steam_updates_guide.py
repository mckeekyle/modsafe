import json
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build  # noqa: E402
import guides  # noqa: E402
from games import GAMES, GAMES_BY_SLUG  # noqa: E402

PATH = "/guides/stop-steam-auto-updates/"


def jsonld(html: str) -> list[dict]:
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])


class TestBranchData(unittest.TestCase):
    def test_branch_file_is_consistent(self):
        b = guides.load_branches()
        self.assertRegex(b["verified"], r"^\d{4}-\d{2}-\d{2}$")
        listed = set(b["games"]) | set(b["none"]) | set(b.get("beta_only", []))
        for slug in listed:
            self.assertIn(slug, GAMES_BY_SLUG)
            self.assertTrue(GAMES_BY_SLUG[slug].get("steam_appid"), slug)
        self.assertEqual(len(listed), len(b["games"]) + len(b["none"]) + len(b.get("beta_only", [])), "a game is in two lists")
        # every Steam game (not the Deck platform) is classified, so the table never silently skips one
        self.assertEqual(listed, {g["slug"] for g in guides.steam_games()})
        for slug, info in b["games"].items():
            self.assertTrue(info["rollback"], slug)
            for r in info["rollback"]:
                self.assertRegex(r["branch"], r"^[A-Za-z0-9_.\-]+$")
                self.assertTrue(r["label"])

    def test_known_facts(self):
        b = guides.load_branches()
        self.assertIn("2_31_old", [r["branch"] for r in b["games"]["cyberpunk-2077"]["rollback"]])
        for slug in ("skyrim-se", "fallout-4"):  # no previous-version branch on Steam
            self.assertIn(slug, b["none"])


class TestGuidePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = build.build_steam_updates_guide()
        cls.index = build.build_guides_index()

    def test_seo_head(self):
        h = self.html
        title = re.search(r"<title>([^<]+)</title>", h).group(1)
        self.assertTrue(title.startswith("How to stop Steam auto-updating a game") and title.endswith("— ModSafe"), title)
        desc = re.search(r'<meta name="description" content="([^"]+)"', h).group(1)
        self.assertTrue(80 <= len(desc) <= 300, len(desc))
        self.assertIn(f'<link rel="canonical" href="{build.SITE_URL}{PATH}">', h)
        self.assertIn(f'content="{build.SITE_URL}/og/guide-stop-steam-auto-updates.png"', h)
        self.assertTrue((ROOT / "static/og/guide-stop-steam-auto-updates.png").exists())
        self.assertTrue((ROOT / "static/og/guides.png").exists())
        self.assertIn(f'{build.SITE_URL}/og/guides.png', self.index)

    def test_structured_data(self):
        blocks = {b["@type"]: b for b in jsonld(self.html)}
        for t in ("FAQPage", "BreadcrumbList", "TechArticle", "WebPage"):
            self.assertIn(t, blocks)
        qs = [q["name"] for q in blocks["FAQPage"]["mainEntity"]]
        self.assertEqual(qs, [f["q"] for f in guides.STEAM_GUIDE_FAQ])
        for q in qs:  # FAQ rich results need the questions visible on the page
            self.assertIn(build.esc(q), self.html)
        self.assertEqual(blocks["BreadcrumbList"]["itemListElement"][-1]["item"], build.SITE_URL + PATH)

    def test_honest_and_covers_methods(self):
        h = self.html
        self.assertIn("no “never update” option", h)
        for s in ("Wait until I launch the game", "Only update this game when I launch it", "Offline Mode", "Steam Deck",
                  "Game Versions &amp; Betas", "download_depot", "DepotDownloader", "Back up your game folder", "read-only"):
            self.assertIn(s, h, s)
        self.assertIn("2_31_old", h)
        self.assertIn('href="/skyrim-se/"', h)

    def test_links_and_anchors(self):
        p = Links()
        p.feed(self.html)
        for href in p.hrefs:
            if href.startswith("#"):
                self.assertIn(href[1:], p.ids, href)
        internal = {h for h in p.hrefs if h.startswith("/")}
        for g in guides.steam_games():
            self.assertIn(f"/{g['slug']}/", internal)
        self.assertIn("/feed.xml", internal)
        self.assertIn('src="/badge/skyrim-se.svg"', self.html)
        main = self.html.split('<main id="main">')[1].split("</main>")[0]
        self.assertNotIn('href="/minecraft/"', main)  # not a Steam game

    def test_index_lists_guides(self):
        self.assertIn(f'href="{PATH}"', self.index)
        for g in GAMES:
            if build.mods_mod.load_guide(g["slug"]):
                self.assertIn(f'href="/{g["slug"]}/install/"', self.index)


class TestSiteWiring(unittest.TestCase):
    def test_nav_footer_sitemap_llms_faq(self):
        self.assertIn('href="/guides/"', build.nav("faq"))
        self.assertIn('href="/guides/"', build.footer())
        self.assertIn("/guides/", build.sitemap_urls())
        self.assertIn(PATH, build.sitemap_urls())
        llms = build.build_llms_txt(build.load_games())
        self.assertIn(f"{build.SITE_URL}{PATH}", llms)
        faq = build.build_faq()
        self.assertIn(f'href="{PATH}"', faq)
        self.assertIn("How do I stop Steam from auto-updating a modded game?", faq)

    def test_game_pages_link_guide(self):
        games = dict((g["slug"], d) for g, d in build.load_games())
        for g in GAMES:
            page = build.build_game_page(g, games[g["slug"]])
            if g.get("steam_appid"):
                self.assertIn(f'href="{PATH}"', page, g["slug"])
                self.assertTrue(any("auto-updating" in f["q"] or "from updating" in f["q"]
                                    for f in build.game_faq(g, games[g["slug"]])), g["slug"])
            else:
                self.assertNotIn(f'href="{PATH}"', page, g["slug"])

    def test_game_faq_branch_text(self):
        cp = guides.game_faq_item(GAMES_BY_SLUG["cyberpunk-2077"])
        self.assertIn("2_31_old", cp["a"])
        sk = guides.game_faq_item(GAMES_BY_SLUG["skyrim-se"])
        self.assertIn("no previous-version branch", sk["a"])
        self.assertIsNone(guides.game_faq_item(GAMES_BY_SLUG["minecraft"]))

    def test_upcoming_notice_links_guide_for_steam_only(self):
        e = {"label": "Patch 9", "date": "2026-10-22", "stores": "Steam/GOG", "source": "https://example.com"}
        self.assertIn(f'href="{PATH}"', build.upcoming_notice(e))
        self.assertNotIn(f'href="{PATH}"', build.upcoming_notice({**e, "stores": "GOG"}))

    def test_built_files(self):
        dist = ROOT / "dist"
        if not (dist / "index.html").exists():
            self.skipTest("dist not built")
        self.assertTrue((dist / "guides/stop-steam-auto-updates/index.html").exists())
        self.assertTrue((dist / "guides/index.html").exists())
        self.assertTrue((dist / "og/guide-stop-steam-auto-updates.png").exists())
        self.assertIn(PATH, (dist / "sitemap.xml").read_text())


if __name__ == "__main__":
    unittest.main()
