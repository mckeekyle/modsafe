#!/usr/bin/env python3
"""
Fetch Cyberpunk 2077 patch news (Steam) and core framework releases (GitHub),
compute honest compatibility statuses, write data/status.json.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Allow running as script from repo root or src/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from status_logic import (  # noqa: E402
    FRAMEWORKS,
    determine_with_lineage,
    list_game_patches,
    notes_mention_patch,
    parse_iso,
    pick_latest_stable_release,
    select_latest_game_patch,
    status_for_patch_history,
)

STEAM_APPID = 1091500
STEAM_NEWS_URL = (
    "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
    f"?appid={STEAM_APPID}&count=100&maxlength=800&feeds=steam_community_announcements"
)
USER_AGENT = "ModSafe/1.0 (Cyberpunk mod compatibility status; +https://modsafe.app)"


def http_get_json(url: str, timeout: int = 30) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_steam_news() -> list[dict]:
    data = http_get_json(STEAM_NEWS_URL)
    return data.get("appnews", {}).get("newsitems", [])


def fetch_github_releases(repo: str, per_page: int = 30, retries: int = 4) -> list[dict]:
    import time

    url = f"https://api.github.com/repos/{repo}/releases?per_page={per_page}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (403, 429):
                # Honor Retry-After when present; otherwise back off.
                retry_after = e.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else 15 * (attempt + 1)
                # Cap wait so local runs stay usable; scheduled CI has a token.
                wait = min(wait, 90)
                print(f"  GitHub {e.code} for {repo}; sleeping {wait}s (attempt {attempt+1}/{retries})", flush=True)
                time.sleep(wait)
                continue
            raise
    assert last_err is not None
    raise last_err


def build_status_payload() -> dict:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    news = fetch_steam_news()
    latest_patch = select_latest_game_patch(news)
    patches = list_game_patches(news, limit=15)

    if not latest_patch:
        raise RuntimeError("Could not find any Cyberpunk 2077 patch announcements in Steam news.")

    frameworks_out = []
    releases_by_id: dict[str, list] = {}

    import time

    for i, fw in enumerate(FRAMEWORKS):
        if i:
            time.sleep(1.2)  # stay under unauthenticated GitHub rate limits
        try:
            releases = fetch_github_releases(fw["repo"])
        except urllib.error.HTTPError as e:
            frameworks_out.append(
                {
                    "id": fw["id"],
                    "name": fw["name"],
                    "short": fw["short"],
                    "repo": fw["repo"],
                    "url": fw["url"],
                    "status": "Unknown / check",
                    "reason": f"Failed to fetch GitHub releases: HTTP {e.code}",
                    "release_tag": None,
                    "release_published_at": None,
                    "release_url": None,
                    "mentions_patch": False,
                    "newer_than_patch": False,
                    "error": str(e),
                }
            )
            releases_by_id[fw["id"]] = []
            continue

        releases_by_id[fw["id"]] = releases
        latest = pick_latest_stable_release(releases)
        if not latest:
            frameworks_out.append(
                {
                    "id": fw["id"],
                    "name": fw["name"],
                    "short": fw["short"],
                    "repo": fw["repo"],
                    "url": fw["url"],
                    "status": "Unknown / check",
                    "reason": "No GitHub releases found.",
                    "release_tag": None,
                    "release_published_at": None,
                    "release_url": None,
                    "mentions_patch": False,
                    "newer_than_patch": False,
                }
            )
            continue

        patch_dt = parse_iso(latest_patch["published_at"])
        lineage_mentions: list[str] = []
        for r in releases:
            if r.get("draft"):
                continue
            rdt = parse_iso(r.get("published_at"))
            notes = f"{r.get('tag_name') or ''}\n{r.get('name') or ''}\n{r.get('body') or ''}"
            if not notes_mention_patch(notes, latest_patch["version"]):
                continue
            if rdt and patch_dt and rdt >= patch_dt:
                tag = r.get("tag_name") or ""
                if tag and tag not in lineage_mentions:
                    lineage_mentions.append(tag)

        verdict = determine_with_lineage(
            release_published_at=latest.get("published_at"),
            release_notes=f"{latest.get('name') or ''}\n{latest.get('body') or ''}",
            release_tag=latest.get("tag_name") or "",
            patch_version=latest_patch["version"],
            patch_published_at=latest_patch["published_at"],
            lineage_mention_tags=lineage_mentions,
        )
        frameworks_out.append(
            {
                "id": fw["id"],
                "name": fw["name"],
                "short": fw["short"],
                "repo": fw["repo"],
                "url": fw["url"],
                "status": verdict["status"],
                "reason": verdict["reason"],
                "release_tag": latest.get("tag_name"),
                "release_name": latest.get("name"),
                "release_published_at": latest.get("published_at"),
                "release_url": latest.get("html_url"),
                "mentions_patch": verdict["mentions_patch"],
                "newer_than_patch": verdict["newer_than_patch"],
                "mention_releases": lineage_mentions,
            }
        )

    # Per-patch history with framework snapshots
    history = []
    for patch in patches:
        fw_hist = []
        for fw in FRAMEWORKS:
            rels = releases_by_id.get(fw["id"], [])
            snap = status_for_patch_history(
                releases=rels,
                patch_version=patch["version"],
                patch_published_at=patch["published_at"],
            )
            fw_hist.append(
                {
                    "id": fw["id"],
                    "short": fw["short"],
                    "name": fw["name"],
                    **snap,
                }
            )
        history.append({**patch, "frameworks": fw_hist})

    return {
        "generated_at": now,
        "game": {
            "name": "Cyberpunk 2077",
            "steam_appid": STEAM_APPID,
            "latest_patch": latest_patch,
        },
        "frameworks": frameworks_out,
        "history": history,
        "disclaimer": (
            "Statuses are inferred from public Steam news and GitHub release dates/notes. "
            "They are not guarantees. Always verify on the framework's GitHub/Nexus page "
            "and the Cyberpunk modding wiki before updating."
        ),
        "sources": {
            "steam_news": STEAM_NEWS_URL.split("?")[0],
            "github": "https://api.github.com",
        },
    }


def main() -> int:
    out_path = ROOT / "data" / "status.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print("Fetching Steam news and GitHub releases…", flush=True)
    payload = build_status_payload()
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    patch = payload["game"]["latest_patch"]
    print(f"Latest game patch: {patch['version']} ({patch['published_at']})")
    for fw in payload["frameworks"]:
        print(f"  {fw['short']:12} {fw['status']:28} {fw.get('release_tag') or '—'}")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
