"""Canonical host: www.modsafe.app / modsafe.pages.dev 301 to https://modsafe.app via
functions/_middleware.js; _routes.json keeps polled paths off the Function; machine-readable
files get exactly one X-Robots-Tag rule; every page canonical == its sitemap URL."""
import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import build  # noqa: E402

MIDDLEWARE = ROOT / "functions" / "_middleware.js"


def header_rules(text):
    rules, cur = [], None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            cur = (line.strip(), {})
            rules.append(cur)
        else:
            k, v = line.strip().split(":", 1)
            cur[1][k.strip().lower()] = v.strip()
    return rules


def rule_matches(pattern, path):
    rx = "^" + "".join(
        "[^/]+" if tok.startswith(":") else ".*" if tok == "*" else re.escape(tok)
        for tok in re.split(r"(:[a-z]+|\*)", pattern)) + "$"
    return re.match(rx, path) is not None


class TestCanonicalHost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Temp dir inside ROOT: build.write() prints paths relative to ROOT, and changing
        # build.ROOT would poison cached loaders used by other tests.
        cls.tmp = Path(tempfile.mkdtemp(dir=ROOT, prefix=".test-canonical-"))
        saved = build.DIST
        build.DIST = cls.tmp / "dist"
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                assert build.main() == 0
        finally:
            build.DIST = saved
        cls.dist = cls.tmp / "dist"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_functions_dir_at_project_root(self):
        # Pages CI compiles <root>/functions (not inside the dist/ output dir).
        self.assertTrue(MIDDLEWARE.exists())
        self.assertFalse((self.dist / "functions").exists())
        js = MIDDLEWARE.read_text()
        self.assertIn("export async function onRequest", js)
        self.assertIn('"www.modsafe.app"', js)
        self.assertIn('"modsafe.pages.dev"', js)

    def test_routes_json(self):
        r = json.loads((self.dist / "_routes.json").read_text())
        self.assertEqual(r["version"], 1)
        self.assertEqual(r["include"], ["/*"])
        self.assertLessEqual(len(r["include"]) + len(r["exclude"]), 100)
        self.assertTrue(all(len(x) <= 100 for x in r["exclude"]))
        for p in ("/api/*", "/badge/*", "/feed.xml", "/cyberpunk-2077/feed.xml", "/fonts/*", "/img/*"):
            self.assertIn(p, r["exclude"])
        # HTML pages must still hit the middleware.
        self.assertFalse(any(rule_matches(x, "/cyberpunk-2077/") for x in r["exclude"]))
        self.assertFalse(any(rule_matches(x, "/") for x in r["exclude"]))

    def test_robots_tag_single_rule_per_path(self):
        rules = header_rules(build.HEADERS)
        sitemap = set(build.sitemap_urls())
        files = ["/" + str(p.relative_to(self.dist)) for p in self.dist.rglob("*") if p.is_file()]
        for path in files:
            tagged = [pat for pat, h in rules if "x-robots-tag" in h and rule_matches(pat, path)]
            self.assertLessEqual(len(tagged), 1, (path, tagged))
            machine = path.endswith((".xml", ".json")) or path.startswith("/badge/")
            if path in sitemap or path in ("/sitemap.xml", "/_routes.json"):
                self.assertEqual(tagged, [], path)  # noindex + sitemap = GSC error
            elif machine:
                self.assertEqual(len(tagged), 1, path)
        for name in ("access-control-allow-origin", "content-type", "cache-control"):
            for path in files:
                n = [pat for pat, h in rules if name in h and rule_matches(pat, path)]
                if name == "cache-control" and path.endswith(".html"):
                    continue  # "/" and "/*.html" never both match one file path
                self.assertLessEqual(len(n), 1, (name, path, n))

    def test_canonical_equals_sitemap(self):
        locs = re.findall(r"<loc>([^<]+)</loc>", (self.dist / "sitemap.xml").read_text())
        site = build.SITE_URL
        canon = {}
        for p in self.dist.rglob("*.html"):
            m = re.search(r'<link rel="canonical" href="([^"]+)"', p.read_text())
            if p.name == "404.html":
                self.assertIsNone(m)
                continue
            rel = str(p.relative_to(self.dist))
            self.assertTrue(rel.endswith("index.html"), rel)
            self.assertEqual(m.group(1), f"{site}/{rel[:-len('index.html')]}")
            canon[m.group(1)] = rel
        html_locs = [u for u in locs if u.endswith("/")]
        self.assertEqual(sorted(html_locs), sorted(canon))
        self.assertTrue(all(u.startswith(site + "/") for u in locs))

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_middleware_behaviour(self):
        script = r"""
const m = await import(process.argv[1]);
const next = async () => new Response("ok", {status: 200, headers: {"content-type": "text/html"}});
const run = async (u) => { const r = await m.onRequest({request: new Request(u), next});
  return {s: r.status, loc: r.headers.get("location"), robots: r.headers.get("x-robots-tag")}; };
const out = {};
for (const u of ["https://www.modsafe.app/", "https://www.modsafe.app/cyberpunk-2077/?a=1&b=2",
                 "https://modsafe.pages.dev/gta-v/history/", "https://WWW.modsafe.app/x",
                 "https://modsafe.app/", "https://abc123.modsafe.pages.dev/", "http://localhost:8788/"])
  out[u] = await run(u);
console.log(JSON.stringify(out));
"""
        res = subprocess.run(["node", "--input-type=module", "-e", script, MIDDLEWARE.as_uri()],
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(res.returncode, 0, res.stderr)
        o = json.loads(res.stdout)
        self.assertEqual(o["https://www.modsafe.app/"], {"s": 301, "loc": "https://modsafe.app/", "robots": None})
        self.assertEqual(o["https://www.modsafe.app/cyberpunk-2077/?a=1&b=2"]["loc"], "https://modsafe.app/cyberpunk-2077/?a=1&b=2")
        self.assertEqual(o["https://modsafe.pages.dev/gta-v/history/"]["loc"], "https://modsafe.app/gta-v/history/")
        self.assertEqual(o["https://WWW.modsafe.app/x"]["s"], 301)
        self.assertEqual(o["https://modsafe.app/"], {"s": 200, "loc": None, "robots": None})
        self.assertEqual(o["https://abc123.modsafe.pages.dev/"], {"s": 200, "loc": None, "robots": "noindex"})
        self.assertEqual(o["http://localhost:8788/"]["s"], 200)


if __name__ == "__main__":
    unittest.main()
