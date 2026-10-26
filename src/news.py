"""Headline-only gaming news feed: Steam announcements for tracked games + a few reputable RSS feeds.

We store only headline, source, date and link (no article bodies) and always link out.
"""

from __future__ import annotations

import email.utils
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from games import GAMES  # noqa: E402

USER_AGENT = "ModSafe/2.0 (headline feed; +https://modsafe.app)"
RSS_FEEDS = [
    ("PC Gamer", "https://www.pcgamer.com/rss/"),
    ("Rock Paper Shotgun", "https://www.rockpapershotgun.com/feed"),
    ("Eurogamer", "https://www.eurogamer.net/feed"),
]
MAX_AGE_DAYS = 21
PATCH_RE = re.compile(r"(?i)\b(patch|hotfix|update|title update|version\s?\d|v\d+\.\d+)\b")

# Names/aliases used to tag headlines with tracked games.
ALIASES = {
    "msfs-2024": [r"flight simulator 2024", r"\bmsfs ?2024\b"], "msfs-2020": [r"flight simulator (?:\()?2020", r"\bmsfs ?2020\b"],
    "steam-deck": [r"steam ?deck", r"steamos", r"decky"],
    "cyberpunk-2077": [r"cyberpunk"], "skyrim-se": [r"skyrim"], "fallout-4": [r"fallout 4"],
    "baldurs-gate-3": [r"baldur'?s gate 3", r"\bbg3\b"], "stardew-valley": [r"stardew"],
    "lethal-company": [r"lethal company"], "gta-v": [r"\bgta (?:5|v)\b", r"grand theft auto v\b"],
    "starfield": [r"starfield"], "elden-ring": [r"elden ring(?! nightreign)"], "valheim": [r"valheim"],
    "terraria": [r"terraria"], "rimworld": [r"rimworld"], "bannerlord": [r"bannerlord"],
    "minecraft": [r"minecraft(?! dungeons| legends)"],
    # "satisfactory" is an ordinary word: require the capitalised name plus a game/update word nearby.
    "satisfactory": [r"(?-i:\bSatisfactory\b)(?!:? (?:the )?board game)(?=.*\b(?:update|patch|hotfix|mods?|factory|coffee stain|1\.\d))",
                     r"coffee stain'?s satisfactory"],
}


def tag_games(title: str) -> list[str]:
    return [slug for slug, pats in ALIASES.items() if any(re.search(p, title, re.I) for p in pats)]


def is_patch_headline(title: str) -> bool:
    return bool(PATCH_RE.search(title or ""))


def parse_rss(xml_text: str, source: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    out = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate")
        if not title or not link.startswith("http"):
            continue
        try:
            dt = email.utils.parsedate_to_datetime(pub).astimezone(timezone.utc) if pub else None
        except (TypeError, ValueError):
            dt = None
        if not dt:
            continue
        out.append({"title": re.sub(r"\s+", " ", title), "url": link, "source": source,
                    "published_at": dt.isoformat().replace("+00:00", "Z"), "games": tag_games(title),
                    "kind": "news"})
    return out


def steam_items(games_data: dict[str, dict]) -> list[dict]:
    out = []
    for g in GAMES:
        d = games_data.get(g["slug"]) or {}
        for n in d.get("news", [])[:6]:
            out.append({"title": n["title"], "url": n["url"], "source": f"Steam · {g['short']}",
                        "published_at": n["published_at"], "games": [g["slug"]],
                        "kind": "patch" if n.get("is_patch") else "announcement"})
    return out


def merge(items: list[dict], now: datetime | None = None, limit: int = 60) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    seen, out = set(), []
    for i in sorted(items, key=lambda x: x["published_at"], reverse=True):
        dt = datetime.fromisoformat(i["published_at"].replace("Z", "+00:00"))
        if dt < cutoff or i["url"] in seen:
            continue
        seen.add(i["url"])
        if i["kind"] == "news":
            i["highlight"] = bool(i["games"]) and is_patch_headline(i["title"])
        else:  # Steam: only announcements our patch detector classified as game patches
            i["highlight"] = i["kind"] == "patch"
        out.append(i)
    return out[:limit]


def build_news(games_data: dict[str, dict]) -> dict:
    items = steam_items(games_data)
    sources = []
    for name, url in RSS_FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=20) as r:
                got = parse_rss(r.read().decode("utf-8", "replace"), name)
            items += got
            sources.append({"name": name, "url": url, "ok": True, "items": len(got)})
        except Exception as e:  # noqa: BLE001
            print(f"  news feed {name} failed: {e}", file=sys.stderr)
            sources.append({"name": name, "url": url, "ok": False})
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "sources": sources, "items": merge(items)}


def main() -> int:
    games_data = {}
    for g in GAMES:
        f = ROOT / "data" / "games" / f"{g['slug']}.json"
        if f.exists():
            games_data[g["slug"]] = json.loads(f.read_text(encoding="utf-8"))
    news = build_news(games_data)
    (ROOT / "data" / "news.json").write_text(json.dumps(news, indent=2) + "\n", encoding="utf-8")
    print(f"News: {len(news['items'])} items from {[s['name'] for s in news['sources'] if s['ok']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
