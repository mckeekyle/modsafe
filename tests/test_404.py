"""404 page: Cloudflare Pages returns a real 404 status only when a top-level 404.html exists
(otherwise it falls back to the home page with HTTP 200, i.e. soft 404s)."""
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build  # noqa: E402


class Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.srcs = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("href"):
            self.hrefs.append(a["href"])
        if a.get("src"):
            self.srcs.append(a["src"])


class Test404Page(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games_data = build.load_games()
        cls.html = build.build_404(cls.games_data)
        p = Refs()
        p.feed(cls.html)
        cls.refs = p

    def test_noindex_no_canonical_no_jsonld(self):
        h = self.html
        self.assertIn('<meta name="robots" content="noindex,follow">', h)
        self.assertNotIn('content="index,follow"', h)
        self.assertNotIn('rel="canonical"', h)
        self.assertNotIn("application/ld+json", h)
        self.assertIn("404", re.search(r"<title>(.*?)</title>", h).group(1))

    def test_links_home_games_guides_faq(self):
        for href in ("/", "/games/", "/guides/", "/faq/"):
            self.assertIn(href, self.refs.hrefs)

    def test_all_urls_root_absolute(self):
        # 404.html is served at any depth (/a/b/c/), so relative URLs would break.
        for u in self.refs.hrefs + self.refs.srcs:
            self.assertTrue(u.startswith(("/", "#", "https://", "http://")), u)
        m = re.search(r"--hero:url\('([^']+)'\)", self.html)
        self.assertTrue(m and m.group(1).startswith("/img/"))

    def test_uses_existing_art(self):
        imgs = [s for s in self.refs.srcs if s.startswith("/img/")]
        imgs.append(re.search(r"--hero:url\('([^']+)'\)", self.html).group(1))
        self.assertGreaterEqual(len(imgs), 2)
        for s in imgs:
            self.assertTrue((build.STATIC / s.removeprefix("/")).is_file(), s)

    def test_other_pages_still_indexable(self):
        home = build.build_home(self.games_data)
        self.assertIn('<meta name="robots" content="index,follow">', home)
        self.assertIn(f'<link rel="canonical" href="{build.SITE_URL}/">', home)

    def test_not_in_sitemap_and_redirects_kept(self):
        self.assertFalse(any("404" in u for u in build.sitemap_urls()))
        self.assertIn("/newsletter/ / 301", build.REDIRECTS)
        # no catch-all rule that would shadow the 404 page or the redirects
        for line in build.REDIRECTS.splitlines():
            if line.strip() and not line.startswith("#"):
                self.assertFalse(line.split()[0].startswith("/*"), line)

    def test_main_writes_top_level_404(self):
        src = (ROOT / "src" / "build.py").read_text(encoding="utf-8")
        self.assertIn('write(DIST / "404.html", build_404(games_data))', src)


if __name__ == "__main__":
    unittest.main()
