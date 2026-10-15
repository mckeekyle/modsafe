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
    STATUS_UPDATED,
    V_MANUAL,
    V_NODATA,
    determine_with_lineage,
    game_verdict,
    history_label,
    is_breakage_title,
    parse_silverlock,
    manual_hook_verdict,
    patch_age_days,
    user_verdict,
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


def http_get_text(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def official_support(fw: dict, rel: dict, patch_dt) -> dict | None:
    """silverlock.org lists the current runtime/build. Counts as support when the listed build is the
    latest tag and that tag isn't older than the patch minus a 3-day beta-branch window."""
    if not fw.get("official_page"):
        return None
    try:
        import html as _h
        import re as _re
        text = _h.unescape(_re.sub(r"<[^>]+>", " ", http_get_text(fw["official_page"])))
    except Exception as e:  # noqa: BLE001
        print(f"  official page failed for {fw['id']}: {e}", file=sys.stderr)
        return None
    info = parse_silverlock(text)
    if not info:
        return None
    tag = (rel.get("tag_name") or "").lstrip("v")
    rdt = parse_iso(rel.get("published_at"))
    from datetime import timedelta
    ok = info["build"] == tag and rdt is not None and patch_dt is not None and rdt >= patch_dt - timedelta(days=3)
    return {**info, "supports_current": ok, "page": fw["official_page"]}


_last_search = [0.0]


BREAKAGE_WINDOW_DAYS = 30
from datetime import timedelta as _td  # noqa: E402
PRE_PATCH_WINDOW = _td(days=7)


def breakage_reports(repo: str, since_iso: str, patch_version: str | None, patch_dt=None) -> list[dict]:
    """Open GitHub issues filed since `since_iso` (and within BREAKAGE_WINDOW_DAYS of the patch, when
    patch-caused breakage actually surfaces) whose titles report update-related breakage."""
    wait = 6.5 - (time.time() - _last_search[0])  # search API: 10 req/min unauthenticated
    if wait > 0:
        time.sleep(wait)
    _last_search[0] = time.time()
    q = urllib.parse.quote(f"repo:{repo} is:issue is:open created:>={since_iso[:10]}")
    try:
        res = http_get_json(f"https://api.github.com/search/issues?q={q}&per_page=50", gh_headers())
    except Exception as e:  # noqa: BLE001
        print(f"  issue search failed for {repo}: {e}", file=sys.stderr)
        return []
    from datetime import timedelta
    out = []
    for i in res.get("items", []):
        if not is_breakage_title(i["title"], patch_version):
            continue
        cdt = parse_iso(i["created_at"])
        if patch_dt and cdt and cdt > patch_dt + timedelta(days=BREAKAGE_WINDOW_DAYS):
            continue
        out.append({"title": i["title"], "url": i["html_url"], "created_at": i["created_at"]})
    return out


def manual_entry(fw: dict) -> dict:
    return {
        "id": fw["id"], "name": fw["name"], "short": fw["short"], "url": fw["url"],
        "source": "manual", "tracked": False, "sensitive": True, "status": V_MANUAL,
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
                "source": fw["source"], "repo": fw.get("repo") or fw.get("package"), "tracked": True,
                "sensitive": not fw.get("agnostic")}
        try:
            rels = SOURCES[fw["source"]](fw)
            time.sleep(0.5)
        except Exception as e:  # noqa: BLE001
            fws.append({**base, "status": V_NODATA, "base_status": None, "reason": f"Fetch failed: {e}", "release_tag": None,
                        "release_published_at": None, "release_url": fw["url"], "error": str(e)})
            continue
        rels_by[fw["id"]] = rels
        rel = pick_latest_stable_release(rels)
        if not rel:
            fws.append({**base, "status": V_NODATA, "base_status": None, "reason": "No releases found.", "release_tag": None,
                        "release_published_at": None, "release_url": fw["url"]})
            continue
        lineage = []
        for r in rels:
            rdt = parse_iso(r.get("published_at"))
            notes = f"{r.get('tag_name') or ''}\n{r.get('name') or ''}\n{r.get('body') or ''}"
            # Authors often ship "updated for the upcoming X" a few days before the announcement.
            if rdt and patch_dt and rdt >= patch_dt - PRE_PATCH_WINDOW and mfn(notes) and r.get("tag_name") not in lineage:
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
        age = patch_age_days(latest["published_at"])
        sensitive = not fw.get("agnostic")
        official = official_support(fw, rel, patch_dt) if sensitive and v["status"] != STATUS_UPDATED else None
        reports: list[dict] = []
        issues_repo = fw.get("issues_repo") or (fw.get("repo") if fw["source"] != "thunderstore" else None)
        if sensitive and v["status"] != STATUS_UPDATED and not (official and official["supports_current"]) and issues_repo:
            rdt = parse_iso(rel.get("published_at"))
            since = max([d for d in (patch_dt, rdt) if d]).isoformat()
            reports = breakage_reports(issues_repo, since, latest.get("version"), patch_dt)
        label = user_verdict(base_status=v["status"], age_days=age, sensitive=sensitive, breakage=reports,
                             official_support=bool(official and official["supports_current"]))
        if not sensitive:
            reason = fw.get("agnostic_note", "Version-agnostic tool.") + " Latest: " + reason
        elif official and official["supports_current"]:
            reason = (f"Official page ({official['page']}) lists build {official['build']} for runtime "
                      f"{official['runtime']}, matching the latest tag (Bethesda often ships updates to a beta branch first). ") + reason
        elif reports:
            reason += f" {len(reports)} open issue(s) report breakage since the patch/latest release."
        elif v["status"] != STATUS_UPDATED and label == "Likely safe" and v["status"] == STATUS_UNKNOWN:
            reason += f" No open breakage reports {int(age)} days after the patch." if issues_repo else f" Patch is {int(age)} days old; no breakage signal available."
        if fw["source"] == "github_tags":
            reason += " (Date is the tagged commit on GitHub; builds are published on the official site.)"
        if rel.get("deprecated"):
            reason += " (Package is marked deprecated on Thunderstore.)"
        fws.append({**base, "status": label, "base_status": v["status"], "reason": reason,
                    "breakage_reports": reports, "official": official, "release_tag": rel.get("tag_name"),
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
            snap["status"] = history_label(snap["status"]) if not fw.get("agnostic") else "Not affected by patches"
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
    age = patch_age_days(latest["published_at"])
    fws = []
    for fw in game["frameworks"]:
        ev = evaluate(fw, latest["version"])
        ev["base_status"] = ev["status"]
        ev["status"] = user_verdict(base_status=ev["status"], age_days=age, absence_is_definitive=True)
        fws.append({"id": fw["id"], "name": fw["name"], "short": fw["short"], "url": fw["url"], "source": fw["source"],
                    "tracked": True, "sensitive": True, "release_url": fw["url"], **ev})
    history = []
    for v in releases[:8]:
        p = patch_of(v)
        row = []
        for fw in game["frameworks"]:
            ev = evaluate(fw, p["version"])
            ev["status"] = {"Updated for latest patch": "Safe", "Likely OK": "Likely safe"}.get(ev["status"], "Not ported")
            row.append({"id": fw["id"], "short": fw["short"], "name": fw["name"], **ev})
        history.append({**p, "frameworks": row})
    return {"latest_patch": latest, "frameworks": fws, "history": history,
            "latest_snapshot": man["latest"].get("snapshot"),
            "sources": {"mojang_manifest": MC_MANIFEST, "fabric_meta": FABRIC_GAME, "forge_promotions": FORGE_PROMOS,
                        "neoforge_maven": NEOFORGE_VERSIONS, "modrinth": "https://api.modrinth.com/v2"}}


def build_manual_game(game: dict) -> dict:
    """Hand-maintained game (GTA V): patch + hook data from data/manual/*.json; never fetches dev-c.com."""
    man = json.loads((ROOT / game["manual_file"]).read_text(encoding="utf-8"))
    lp = man["latest_patch"]
    latest = {k: lp.get(k) for k in ("label", "version", "published_at", "title", "url", "builds", "sources", "notes")}
    verified_age = patch_age_days(man["last_verified"] + "T00:00:00Z")
    age = patch_age_days(lp["published_at"])
    fws = []
    for fw in game["frameworks"]:
        base = {"id": fw["id"], "name": fw["name"], "short": fw["short"], "url": fw["url"], "source": fw["source"],
                "tracked": True, "sensitive": not fw.get("agnostic"), "release_url": fw["url"]}
        if fw["source"] == "manual_shv":
            shv = man["script_hook_v"]
            v = manual_hook_verdict(supported=shv["supported_builds"], current=list(lp["builds"].values()),
                                    patch_age=age, verified_age=verified_age)
            fws.append({**base, **v, "release_tag": shv["version"], "release_published_at": shv["released"] + "T00:00:00Z",
                        "reason": v["reason"] + f" (Manually verified {man['last_verified']}.)", "manual_data": True})
            continue
        try:
            rel = pick_latest_stable_release(SOURCES[fw["source"]](fw))
        except Exception as e:  # noqa: BLE001
            rel = None
            print(f"  {fw['id']} fetch failed: {e}", file=sys.stderr)
        fws.append({**base, "status": "Not affected by patches" if fw.get("agnostic") else V_NODATA,
                    "reason": fw.get("agnostic_note", ""), "release_tag": rel.get("tag_name") if rel else None,
                    "release_published_at": rel.get("published_at") if rel else None,
                    "release_url": (rel or {}).get("html_url") or fw["url"]})
    return {"latest_patch": latest, "frameworks": fws, "history": [], "last_verified": man["last_verified"],
            "sources": {"manual": game["manual_file"], "patch_sources": lp.get("sources", [])}}


DISCLAIMER = ("Statuses are inferred from public release data (Steam news, GitHub, Thunderstore, Mojang/Fabric/Forge/"
              "NeoForge/Modrinth APIs). They are not guarantees — verify on each project's page before updating.")


def build_game(game: dict) -> dict:
    kind = game.get("kind")
    body = (build_minecraft(game) if kind == "minecraft" else build_manual_game(game) if kind == "manual"
            else build_steam_game(game))
    tracked = [f["status"] for f in body["frameworks"] if f.get("tracked") and f.get("sensitive", True)]
    return {
        "generated_at": now_iso(),
        "game": {"slug": game["slug"], "name": game["name"], "steam_appid": game.get("steam_appid"),
                 "latest_patch": body.pop("latest_patch")},
        "verdict": game_verdict(tracked),
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
