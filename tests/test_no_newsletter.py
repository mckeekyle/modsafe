import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNUP_RE = re.compile(r"(?i)beehiiv|patch[- ]day alerts|get patch alerts|subscribe-forms|data-beehiiv-form|nl-heading")


class TestNoNewsletter(unittest.TestCase):
    def test_no_beehiiv_or_signup_in_tracked_sources(self):
        files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
        hits = []
        for f in files:
            p = ROOT / f
            if f.startswith("tests/") or p.suffix in (".png", ".jpg", ".webp", ".ttf", ".ico", ".gif") or not p.is_file():
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            if SIGNUP_RE.search(text):
                hits.append(f)
        self.assertEqual(hits, [])

    def test_built_site_has_no_signup(self):
        dist = ROOT / "dist"
        if not (dist / "index.html").exists():
            self.skipTest("dist not built")
        self.assertFalse((dist / "newsletter").exists())
        bad = [str(p.relative_to(dist)) for p in dist.rglob("*") if p.is_file() and p.suffix in (".html", ".xml", ".txt", ".json")
               and (SIGNUP_RE.search(p.read_text(encoding="utf-8", errors="ignore"))
                    or 'href="/newsletter/' in p.read_text(encoding="utf-8", errors="ignore"))]
        self.assertEqual(bad, [])
        self.assertNotIn("/newsletter/", (dist / "sitemap.xml").read_text())
        self.assertIn("/newsletter/ / 301", (dist / "_redirects").read_text())


if __name__ == "__main__":
    unittest.main()
