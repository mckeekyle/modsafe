#!/usr/bin/env python3
"""
Fetch each game's latest patch (Steam news / Mojang manifest) and its core mod
frameworks (GitHub, Thunderstore, Fabric/Forge/NeoForge meta, Modrinth), compute
honest statuses, and write data/games/<slug>.json + data/index.json.

If a game's fetch fails, the previously committed JSON for that game is kept so a
transient API outage never breaks the Cloudflare Pages build.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from games import GAMES  # noqa: E402
from status_logic import (  # noqa: E402
    STATUS_UNKNOWN,
    determine_with_lineage,
    list_patches_generic,
    loader_support_status,
    make_mention_fn,
    neoforge_versions_for,
    overall_verdict,
    parse_iso,
    pick_latest_stable_release,
    status_for_patch_history,
)

USER_AGENT = "ModSafe/2.0 (mod framework patch status; +https://modsafe.app)"
DATA_DIR = ROOT / "data" / "games"
STEAM_NEWS = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={appid}&count=100&maxlength=600&feeds=steam_community_announcements"
MC_MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
FABRIC_GAME = "https://meta.fabricmc.net/v2/versions/game"
FABRIC_LOADER = "https://meta.fabricmc.net/v2/versions/loader"
FORGE_PROMOS = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
NEOFORGE_VERSIONS = "https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge"
MODRINTH_VERSIONS = "https://api.modrinth.com/v2/project/{project}/version"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def http_get_json(url: str, headers: dict | None = None, timeout: int = 30, retries: int = 3):
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    h.update(headers or {})
    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 429, 500, 502, 503):
                ra = e.headers.get("Retry-After")
                wait = min(int(ra) if ra and ra.isdigit() else 10 * (attempt + 1), 60)
                print(f"  HTTP {e.code} {url}; retry in {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(3)
    assert last is not None
    raise last


def gh_headers() -> dict:
    h = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


# --- source adapters: each returns a list of "release-like" dicts -------------

def releases_github(fw: dict) -> list[dict]:
    return http_get_json(f"https://api.github.com/repos/{fw['repo']}/releases?per_page=30", gh_headers())


def releases_github_tags(fw: dict, n: int = 4) -> list[dict]:
    tags = http_get_json(f"https://api.github.com/repos/{fw['repo']}/tags?per_page={n}", gh_headers())
    out = []
    for t in tags[:n]:
        c = http_get_json(t["commit"]["url"], gh_headers())
        out.append(
            {
                "tag_name": t["name"],
                "name": t["name"],
                "body": c.get("commit", {}).get("message", ""),
                "published_at": c.get("commit", {}).get("committer", {}).get("date"),
                "html_url": f"https://github.com/{fw['repo']}/releases/tag/{t['name']}",
                "prerelease": False,
                "draft": False,
            }
        )
    return out


def releases_thunderstore(fw: dict) -> list[dict]:
    d = http_get_json(f"https://thunderstore.io/api/experimental/package/{fw['package']}/")
    latest = d["latest"]
    return [
        {
            "tag_name": latest["version_number"],
            "name": f"{d['full_name']} {latest['version_number']}",
            "body": latest.get("description", ""),
            "published_at": latest["date_created"].split(".")[0] + "Z",
            "html_url": fw["url"],
            "prerelease": False,
            "draft": False,
            "deprecated": bool(d.get("is_deprecated")),
        }
    ]


SOURCES = {"github": releases_github, "github_tags": releases_github_tags, "thunderstore": releases_thunderstore}


def manual_entry(fw: dict) -> dict:
    return {
        "id": fw["id"], "name": fw["name"], "short": fw["short"], "url": fw["url"],
        "source": "manual", "tracked": False, "status": STATUS_UNKNOWN,
        "reason": fw.get("note", "Not tracked automatically — check the project page."),
        "release_tag": None, "release_published_at": None, "release_url": fw["url"],
    }


def build_steam_game(game: dict) -> dict:
    news = http_get_json(STEAM_NEWS.format(appid=game["steam_appid"])).get("appnews", {}).get("newsitems", [])
    rule = game["patch_rule"]
    patches = list_patches_generic(news, rule, limit=12)
    if not patches:
        raise RuntimeError(f"No patch announcements found in Steam news for {game['name']}")
    latest = patches[0]
    patch_dt = parse_iso(latest["published_at"])
    mfn = make_mention_fn(latest["version"], rule.get("mention"))

    fws, rels_by = [], {}
    for fw in game["frameworks"]:
        if fw["source"] == "manual":
            fws.append(manual_entry(fw))
            continue
        base = {"id": fw["id"], "name": fw["name"], "short": fw["short"], "url": fw["url"],
                "source": fw["source"], "repo": fw.get("repo") or fw.get("package"), "tracked": True}
        try:
            rels = SOURCES[fw["source"]](fw)
            time.sleep(0.5)
        except Exception as e:  # noqa: BLE001
            fws.append({**base, "status": STATUS_UNKNOWN, "reason": f"Fetch failed: {e}", "release_tag": None,
                        "release_published_at": None, "release_url": fw["url"], "error": str(e)})
            continue
        rels_by[fw["id"]] = rels
        rel = pick_latest_stable_release(rels)
        if not rel:
            fws.append({**base, "status": STATUS_UNKNOWN, "reason": "No releases found.", "release_tag": None,
                        "release_published_at": None, "release_url": fw["url"]})
            continue
        lineage = []
        for r in rels:
            rdt = parse_iso(r.get("published_at"))
            notes = f"{r.get('tag_name') or ''}\n{r.get('name') or ''}\n{r.get('body') or ''}"
            if rdt and patch_dt and rdt >= patch_dt and mfn(notes) and r.get("tag_name") not in lineage:
                lineage.append(r.get("tag_name"))
        v = determine_with_lineage(
            release_published_at=rel.get("published_at"),
            release_notes=f"{rel.get('name') or ''}\n{rel.get('body') or ''}",
            release_tag=rel.get("tag_name") or "",
            patch_version=latest["label"],
            patch_published_at=latest["published_at"],
            lineage_mention_tags=lineage,
            mention_fn=mfn,
        )
        reason = v["reason"]
        if fw["source"] == "github_tags":
            reason += " (Date is the tagged commit on GitHub; builds are published on the official site.)"
        if rel.get("deprecated"):
            reason += " (Package is marked deprecated on Thunderstore.)"
        fws.append({**base, "status": v["status"], "reason": reason, "release_tag": rel.get("tag_name"),
                    "release_name": rel.get("name"), "release_published_at": rel.get("published_at"),
                    "release_url": rel.get("html_url") or fw["url"], "mentions_patch": v["mentions_patch"],
                    "newer_than_patch": v["newer_than_patch"], "mention_releases": lineage})

    history = []
    for p in patches:
        pm = make_mention_fn(p["version"], rule.get("mention"))
        row = []
        for fw in game["frameworks"]:
            if fw["source"] == "manual" or fw["id"] not in rels_by:
                continue
            snap = status_for_patch_history(releases=rels_by[fw["id"]], patch_version=p["label"],
                                            patch_published_at=p["published_at"], mention_fn=pm)
            row.append({"id": fw["id"], "short": fw["short"], "name": fw["name"], **snap})
        history.append({**p, "frameworks": row})

    return {"latest_patch": latest, "frameworks": fws, "history": history,
            "sources": {"steam_news": STEAM_NEWS.format(appid=game["steam_appid"]).split("&maxlength")[0]}}


def build_minecraft(game: dict) -> dict:
    man = http_get_json(MC_MANIFEST)
    releases = [v for v in man["versions"] if v["type"] == "release"]
    fabric_games = {g["version"]: g["stable"] for g in http_get_json(FABRIC_GAME)}
    fabric_loader = next((l for l in http_get_json(FABRIC_LOADER) if l.get("stable")), None)
    forge = http_get_json(FORGE_PROMOS).get("promos", {})
    neo = http_get_json(NEOFORGE_VERSIONS).get("versions", [])
    modrinth: dict[str, list] = {}
    for fw in game["frameworks"]:
        if fw["source"] == "mc_modrinth":
            q = urllib.parse.quote(json.dumps([fw.get("loader")])) if fw.get("loader") else None
            url = MODRINTH_VERSIONS.format(project=fw["project"]) + (f"?loaders={q}" if q else "")
            modrinth[fw["id"]] = http_get_json(url)

    def evaluate(fw: dict, mc: str) -> dict:
        src = fw["source"]
        tag = None
        if src == "mc_fabric":
            st = loader_support_status(has_stable=fabric_games.get(mc) is True, has_any=mc in fabric_games,
                                       what="Fabric (intermediary mappings)", mc_version=mc)
            tag = fabric_loader["version"] if fabric_loader and mc in fabric_games else None
        elif src == "mc_forge":
            rec, lat = forge.get(f"{mc}-recommended"), forge.get(f"{mc}-latest")
            st = loader_support_status(has_stable=bool(rec), has_any=bool(lat), what="Forge", mc_version=mc)
            tag = rec or lat
        elif src == "mc_neoforge":
            vs = neoforge_versions_for(mc, neo)
            stable = [v for v in vs if "beta" not in v and "alpha" not in v]
            st = loader_support_status(has_stable=bool(stable), has_any=bool(vs), what="NeoForge", mc_version=mc)
            tag = (stable or vs or [None])[-1]
        else:
            vs = [v for v in modrinth.get(fw["id"], []) if mc in v.get("game_versions", [])]
            rel = [v for v in vs if v.get("version_type") == "release"]
            st = loader_support_status(has_stable=bool(rel), has_any=bool(vs), what=fw["name"], mc_version=mc)
            best = (rel or vs or [None])[0]
            tag = best["version_number"] if best else None
            return {**st, "release_tag": tag, "release_published_at": best.get("date_published") if best else None}
        return {**st, "release_tag": tag, "release_published_at": None}

    def patch_of(v: dict) -> dict:
        return {"version": v["id"], "label": v["id"], "title": f"Minecraft Java Edition {v['id']}",
                "published_at": v["releaseTime"].replace("+00:00", "Z"),
                "url": f"https://www.minecraft.net/en-us/article/minecraft-java-edition-{v['id'].replace('.', '-')}"}

    latest = patch_of(releases[0])
    fws = []
    for fw in game["frameworks"]:
        ev = evaluate(fw, latest["version"])
        fws.append({"id": fw["id"], "name": fw["name"], "short": fw["short"], "url": fw["url"], "source": fw["source"],
                    "tracked": True, "release_url": fw["url"], **ev})
    history = []
    for v in releases[:8]:
        p = patch_of(v)
        history.append({**p, "frameworks": [{"id": fw["id"], "short": fw["short"], "name": fw["name"],
                                             **evaluate(fw, p["version"])} for fw in game["frameworks"]]})
    return {"latest_patch": latest, "frameworks": fws, "history": history,
            "latest_snapshot": man["latest"].get("snapshot"),
            "sources": {"mojang_manifest": MC_MANIFEST, "fabric_meta": FABRIC_GAME, "forge_promotions": FORGE_PROMOS,
                        "neoforge_maven": NEOFORGE_VERSIONS, "modrinth": "https://api.modrinth.com/v2"}}


DISCLAIMER = ("Statuses are inferred from public release data (Steam news, GitHub, Thunderstore, Mojang/Fabric/Forge/"
              "NeoForge/Modrinth APIs). They are not guarantees — verify on each project's page before updating.")


def build_game(game: dict) -> dict:
    body = build_minecraft(game) if game.get("kind") == "minecraft" else build_steam_game(game)
    tracked = [f["status"] for f in body["frameworks"] if f.get("tracked")]
    return {
        "generated_at": now_iso(),
        "game": {"slug": game["slug"], "name": game["name"], "steam_appid": game.get("steam_appid"),
                 "latest_patch": body.pop("latest_patch")},
        "verdict": overall_verdict(tracked),
        "disclaimer": DISCLAIMER,
        **body,
    }


def main(argv: list[str]) -> int:
    only = set(argv)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    for game in GAMES:
        if only and game["slug"] not in only:
            continue
        path = DATA_DIR / f"{game['slug']}.json"
        print(f"== {game['name']}", flush=True)
        try:
            payload = build_game(game)
        except Exception as e:  # noqa: BLE001
            failures.append(game["slug"])
            print(f"  ERROR: {e}; keeping previous data" if path.exists() else f"  ERROR: {e}", file=sys.stderr)
            continue
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        lp = payload["game"]["latest_patch"]
        print(f"  patch {lp['label']} ({lp['published_at'][:10]}) → {payload['verdict']}")
        for fw in payload["frameworks"]:
            print(f"    {fw['short']:12} {fw['status']:26} {fw.get('release_tag') or '—'}")
    missing = [g["slug"] for g in GAMES if not (DATA_DIR / f"{g['slug']}.json").exists()]
    if missing:
        print(f"ERROR: no data at all for {missing}", file=sys.stderr)
        return 1
    if failures:
        print(f"WARNING: used cached data for {failures}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
