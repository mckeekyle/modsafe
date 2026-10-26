import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build  # noqa: E402
from games import GAMES  # noqa: E402


class TestAssets(unittest.TestCase):
    def test_every_game_has_card_hero_and_og_art(self):
        for g in GAMES:
            s = g["slug"]
            for kind in ("cap", "hero"):
                ref = build.game_img(s, kind)
                self.assertTrue((ROOT / "static" / ref.lstrip("/")).is_file(), f"{s}: {ref} missing")
            self.assertTrue((ROOT / "static" / "og" / f"{s}.png").is_file(), f"{s}: og/{s}.png missing")

    def test_checker_flags_missing_refs(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "img").mkdir()
            (d / "img" / "a-cap.webp").write_bytes(b"x")
            (d / "index.html").write_text('<img src="/img/a-cap.webp"><img src="/img/b.jpg">'
                                          '<meta content="https://modsafe.app/og/x.png">')
            self.assertEqual(build.missing_asset_refs(d), [("/img/b.jpg", "index.html"), ("/og/x.png", "index.html")])

    def test_built_site_has_no_missing_images(self):
        dist = ROOT / "dist"
        if not (dist / "index.html").exists():
            self.skipTest("dist not built")
        self.assertEqual(build.missing_asset_refs(dist), [])

    def test_card_and_hero_urls_are_cache_busted(self):
        # /img/* is cached for a week; replaced art must get a new URL or visitors keep the old file.
        import hashlib
        u = build.busted(build.game_img("satisfactory"))
        path, _, v = u.partition("?v=")
        self.assertEqual(v, hashlib.sha1((ROOT / "static" / path.lstrip("/")).read_bytes()).hexdigest()[:8])
        self.assertEqual(build.busted("/img/does-not-exist.webp"), "/img/does-not-exist.webp")


if __name__ == "__main__":
    unittest.main()
