import json, re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import build  # noqa

BANNED = re.compile(r"jailbreak|goldhen|etahen|exploit|homebrew|atmosph|hekate|collateral|\bhen\b|payload", re.I)


class ConsoleMods(unittest.TestCase):
    def setUp(self):
        self.d = build.load_console_mods()

    def test_games_and_fields(self):
        self.assertEqual(set(self.d), {"skyrim-se", "fallout-4", "starfield", "baldurs-gate-3"})
        for slug, c in self.d.items():
            for k in ("platforms", "system", "update", "answer", "summary", "limits", "sources", "last_verified"):
                self.assertIn(k, c, slug)
            self.assertRegex(c["last_verified"], r"^\d{4}-\d{2}-\d{2}$")
            for _, u in c["sources"] + [("u", c["update"]["url"])]:
                self.assertTrue(u.startswith("https://"), u)

    def test_no_exploit_content(self):
        txt = (ROOT / "data/manual/console-mods.json").read_text()
        self.assertIsNone(BANNED.search(txt))

    def test_section_renders(self):
        html = build.console_mods_section("fallout-4")
        self.assertIn("Did the latest patch disable console mods?", html)
        self.assertIn("Last manually verified", html)
        self.assertIn('class="plat">PS5', html)
        self.assertEqual(build.console_mods_section("valheim"), "")


if __name__ == "__main__":
    unittest.main()


class IndexNow(unittest.TestCase):
    def test_key_and_robots(self):
        k = build.INDEXNOW_KEY
        self.assertRegex(k, r"^[0-9a-f]{32}$")
        self.assertIn("Sitemap: https://modsafe.app/sitemap.xml", build.build_robots().replace(build.SITE_URL, "https://modsafe.app"))
        sys.path.insert(0, str(ROOT / "tools"))
        import indexnow
        urls = indexnow.all_urls()
        self.assertTrue(all(u.startswith("https://modsafe.app/") for u in urls))
        self.assertIn("https://modsafe.app/", urls)
