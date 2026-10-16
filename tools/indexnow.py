#!/usr/bin/env python3
"""Submit ModSafe URLs to IndexNow (https://www.indexnow.org). No account needed.

  python3 tools/indexnow.py --all                 # every sitemap URL (first run)
  python3 tools/indexnow.py --changed BASE HEAD   # pages for files changed between two git commits

Waits until the key file is live before submitting (Cloudflare deploy lag).
"""
import argparse, json, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import build  # noqa: E402

HOST = "modsafe.app"
SITE = f"https://{HOST}"
KEY = build.INDEXNOW_KEY
ENDPOINT = "https://api.indexnow.org/indexnow"


def all_urls():
    return [SITE + u for u in build.sitemap_urls()]


def changed_urls(base, head):
    files = subprocess.run(["git", "diff", "--name-only", base, head], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.split()
    slugs = {g["slug"] for g in build.GAMES}
    urls = set()
    for f in files:
        p = Path(f)
        if f.startswith("src/") or f.startswith("static/"):
            return all_urls()
        if p.parts[:2] in (("data", "games"), ("data", "mods")) and p.stem in slugs:
            urls |= {f"/{p.stem}/", f"/{p.stem}/history/", "/", "/games/", "/games.json", "/llms.txt"}
            if p.parts[1] == "mods":
                urls.add(f"/{p.stem}/mods/")
        elif p.parts[:2] == ("data", "guides") and p.stem in slugs:
            urls.add(f"/{p.stem}/install/")
        elif f == "data/news.json":
            urls |= {"/news/", "/"}
        elif p.parts[:2] == ("data", "manual"):
            urls |= {f"/{s}/" for s in slugs} | {"/llms.txt"}
    valid = set(build.sitemap_urls())
    return sorted(SITE + u for u in urls if u in valid)


def wait_for_key(timeout=600):
    url = f"{SITE}/{KEY}.txt"
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"Cache-Control": "no-cache"}), timeout=15) as r:
                if r.read().decode().strip() == KEY:
                    return True
        except Exception:
            pass
        time.sleep(20)
    return False


def submit(urls):
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"{SITE}/{KEY}.txt", "urlList": urls[:10000]}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode()[:300]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--changed", nargs=2, metavar=("BASE", "HEAD"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    urls = all_urls() if a.all else changed_urls(*a.changed) if a.changed else []
    print(f"{len(urls)} URL(s)")
    if not urls or a.dry_run:
        print("\n".join(urls)); return 0
    if not wait_for_key():
        print("Key file not live; skipping submission."); return 0
    status, text = submit(urls)
    print(f"IndexNow HTTP {status} {text}")
    return 0 if status in (200, 202) else 1


if __name__ == "__main__":
    sys.exit(main())
