import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import mods  # noqa: E402
from games import GAMES_BY_SLUG  # noqa: E402


class TestModData(unittest.TestCase):
    def test_lists_are_valid(self):
        files = list((ROOT / "data/mods").glob("*.json"))
        self.assertGreaterEqual(len(files), 3)
        for f in files:
            d = json.loads(f.read_text())
            self.assertIn(d["game"], GAMES_BY_SLUG)
            self.assertTrue(10 <= len(d["mods"]) <= 15, f.name)
            ids = [m["id"] for m in d["mods"]]
            self.assertEqual(len(ids), len(set(ids)))
            fw_ids = {fw["id"] for fw in GAMES_BY_SLUG[d["game"]]["frameworks"]}
            for i, m in enumerate(d["mods"]):
                host = m["url"].split("/")[2]
                self.assertIn(host, mods.ALLOWED_HOSTS, m["url"])  # official sources only, never self-hosted
                self.assertTrue(m["url"].startswith("https://"))
                self.assertTrue(m["summary"] and len(m["summary"]) < 140)
                for r in m["requires"]:  # requirements reference a framework or an EARLIER mod (install order)
                    self.assertTrue(r in fw_ids or r in ids[:i], f"{m['id']} requires {r}")
                if m.get("framework_id"):
                    self.assertIn(m["framework_id"], fw_ids)

    def test_guides_have_steps(self):
        for f in (ROOT / "data/guides").glob("*.md"):
            g = mods.guide_parts(f.read_text())
            self.assertGreaterEqual(len(g["steps"]), 5, f.name)
            for sec in ("## Common pitfalls", "## Rolling back"):
                self.assertIn(sec, g["body"], f.name)


class TestCompat(unittest.TestCase):
    data = {"frameworks": [{"id": "a", "short": "A", "status": "Safe"}, {"id": "b", "short": "B", "status": "Just patched, wait"}]}

    def test_worst_required(self):
        self.assertEqual(mods.compat({"requires": ["a", "b"]}, self.data)[0], "Just patched, wait")
        self.assertEqual(mods.compat({"requires": ["a"]}, self.data)[0], "Safe")
        self.assertEqual(mods.compat({"framework_id": "b", "requires": []}, self.data)[0], "Just patched, wait")
        self.assertEqual(mods.compat({"requires": []}, self.data)[0], "Check manually")

    def test_markdown(self):
        h = mods.md_to_html("## Steps\n\n1. **Go.** now <b>\n2. two\n\n- x [l](https://e.com)")
        self.assertIn("<ol>", h); self.assertIn("&lt;b&gt;", h); self.assertIn('<a href="https://e.com">l</a>', h)


class TestPages(unittest.TestCase):
    def test_build_pages(self):
        import build
        games = dict((g["slug"], d) for g, d in build.load_games())
        g = GAMES_BY_SLUG["skyrim-se"]
        page = build.build_mods_page(g, games["skyrim-se"], mods.load_mods("skyrim-se"))
        self.assertIn('"@type": "ItemList"', page)
        self.assertIn("Get it on Nexus Mods", page)
        inst = build.build_install_page(g, games["skyrim-se"], mods.load_guide("skyrim-se"))
        self.assertIn('"@type": "HowTo"', inst)
        self.assertIn("HowToStep", inst)
        self.assertIn("/skyrim-se/mods/", build.sitemap_urls())
        self.assertIn("/skyrim-se/install/", build.sitemap_urls())
        self.assertIn('href="#mods"', build.build_game_page(g, games["skyrim-se"]))


if __name__ == "__main__":
    unittest.main()


class TestAgnosticReq(unittest.TestCase):
    def test_agnostic_loader_does_not_vouch(self):
        d = {"frameworks": [{"id": "bep", "short": "BepInEx", "status": "Not affected by patches"}]}
        self.assertEqual(mods.compat({"requires": ["bep"]}, d)[0], "Check manually")
        self.assertEqual(mods.compat({"framework_id": "bep", "requires": []}, d)[0], "Not affected by patches")
