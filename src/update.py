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
    confirmed_breakage,
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
    manual_build_drift,
    V_WAIT,
    merge_silent_patches,
    parse_atlan_config,
    atlan_verdict,
    parse_steam_public_build,
    detect_unannounced_update,
    apply_unannounced,
    same_release_line,
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
    rels = http_get_json(f"https://api.github.com/repos/{fw['repo']}/releases?per_page=30", gh_headers())
    if fw.get("tag_prefix"):  # monorepos shipping several products (e.g. FlyByWire v2020.* vs v2024.*)
        rels = [r for r in rels if (r.get("tag_name") or "").startswith(fw["tag_prefix"])]
    return rels


def releases_fsuipc(fw: dict) -> list[dict]:
    """fsuipc.com (official) front page states 'FSUIPC7 Version 7.5.9 Released 29/09/2026'."""
    import html as _h
    import re as _re
    t = _h.unescape(_re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", http_get_text("https://fsuipc.com/"))))
    m = _re.search(r"FSUIPC7 Version (\d+\.\d+\.\d+[a-z]?) Released (\d{1,2})/(\d{1,2})/(\d{4})", t)
    if not m:
        raise RuntimeError("FSUIPC7 version not found on fsuipc.com")
    v, d, mo, y = m.groups()
    return [{"tag_name": v, "name": f"FSUIPC7 {v}", "body": "", "published_at": f"{y}-{int(mo):02d}-{int(d):02d}T12:00:00Z",
             "html_url": "https://fsuipc.com/", "prerelease": False, "draft": False}]


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


DECKY_STORE = "https://plugins.deckbrew.xyz/plugins"
_decky_cache: list = []


def releases_decky_store(fw: dict) -> list[dict]:
    """Official Decky plugin store API (public JSON): versions with created timestamps."""
    if not _decky_cache:
        _decky_cache.extend(http_get_json(DECKY_STORE))
    p = next((x for x in _decky_cache if x.get("name") == fw["package"]), None)
    if not p:
        raise RuntimeError(f"Plugin {fw['package']!r} not in Decky store")
    return [{"tag_name": v["name"], "name": f"{p['name']} {v['name']}", "body": "", "published_at": v.get("created"),
             "html_url": fw["url"], "prerelease": False, "draft": False} for v in p.get("versions", [])[:10]]


SOURCES = {"github_asset": lambda fw: releases_github_asset(fw), "fsuipc": releases_fsuipc, "decky_store": releases_decky_store, "github": releases_github, "github_tags": releases_github_tags, "thunderstore": releases_thunderstore}


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


def breakage_reports(repo: str, since_iso: str, patch_version: str | None, patch_dt=None) -> list[dict] | None:
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
        return None  # unknown: callers must not claim "no breakage reports"
    from datetime import timedelta
    out = []
    for i in res.get("items", []):
        if not is_breakage_title(i["title"], patch_version):
            continue
        cdt = parse_iso(i["created_at"])
        if patch_dt and cdt and cdt > patch_dt + timedelta(days=BREAKAGE_WINDOW_DAYS):
            continue
        out.append({"title": i["title"], "url": i["html_url"], "created_at": i["created_at"],
                    "labels": [lb.get("name", "") for lb in i.get("labels", [])], "comments": i.get("comments", 0),
                    "thumbs_up": (i.get("reactions") or {}).get("+1", 0)})
    return out


def quiet_period_note(age: float, issues_repo: str | None, searched: bool) -> str:
    """Only claim "no breakage reports" when an issue tracker exists and the search actually succeeded."""
    if issues_repo and searched:
        return f" No open breakage reports {int(age)} days after the patch."
    return f" Patch is {int(age)} days old; no breakage signal available."


STEAMCMD_INFO = "https://api.steamcmd.net/v1/info/{appid}"


def unannounced_event(game: dict, patches: list[dict], latest: dict) -> Optional[dict]:
    """Steam public-branch build change with no matching patch post. On fetch failure, reuse the committed event
    for the same patch so a flaky source can't flip verdicts."""
    try:
        build = parse_steam_public_build(http_get_json(STEAMCMD_INFO.format(appid=game["steam_appid"]), retries=2),
                                         game["steam_appid"])
    except Exception as e:  # noqa: BLE001
        print(f"  WARNING: steamcmd build info failed ({e}); reusing committed value", file=sys.stderr)
        try:
            prev = json.loads((DATA_DIR / f"{game['slug']}.json").read_text(encoding="utf-8"))["game"]["latest_patch"]
        except Exception:  # noqa: BLE001
            return None
        return prev.get("unannounced_update") if prev.get("label") == latest.get("label") else None
    return detect_unannounced_update(build, patches)


def silent_patches_for(slug: str) -> list[dict]:
    try:
        d = json.loads((ROOT / "data" / "manual" / "silent-patches.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    return (d.get("patches") or {}).get(slug, [])


def manual_entry(fw: dict) -> dict:
    return {
        "id": fw["id"], "name": fw["name"], "short": fw["short"], "url": fw["url"],
        "source": "manual", "tracked": False, "sensitive": not fw.get("agnostic"),
        "status": "Not affected by patches" if fw.get("agnostic") else V_MANUAL,
        "reason": " ".join(x for x in (fw.get("agnostic_note"), fw.get("note") or fw.get("manual_note")) if x)
        or "Not tracked automatically — check the project page.",
        "release_tag": None, "release_published_at": None, "release_url": fw["url"],
    }


def build_steam_game(game: dict) -> dict:
    news = http_get_json(STEAM_NEWS.format(appid=game["steam_appid"])).get("appnews", {}).get("newsitems", [])
    for n in news:  # canonical store URL (the API's akamaihd links bounce through a slow http redirect)
        if n.get("gid"):
            n["url"] = f"https://store.steampowered.com/news/app/{game['steam_appid']}/view/{n['gid']}"
    rule = game["patch_rule"]
    patches = list_patches_generic(news, rule, limit=12)
    patches = merge_silent_patches(patches, silent_patches_for(game["slug"]))
    if not patches:
        raise RuntimeError(f"No patch announcements found in Steam news for {game['name']}")
    latest = patches[0]
    patch_dt = parse_iso(latest["published_at"])
    mfn = make_mention_fn(latest["version"], rule.get("mention"), rule.get("series_depth"))
    unannounced = unannounced_event(game, patches, latest)
    if unannounced:
        latest["unannounced_update"] = unannounced

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
            prev = previous_framework(game["slug"], fw["id"], latest)
            if prev:
                # Transient fetch failure (e.g. unauthenticated GitHub rate limit during a Pages build): keep the last
                # good evaluation for the same patch rather than downgrading the item to "No data".
                fws.append(prev)
                continue
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
            if not same_release_line(r.get("tag_name"), rel.get("tag_name")):
                continue  # e.g. tModLoader's 1.3-legacy v0.11.x branch says nothing about the current v2026.x line
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
        official = official_support(fw, rel, patch_dt) if sensitive else None
        reports: list[dict] = []
        issues_repo = None if fw.get("no_issue_tracker") else (
            fw.get("issues_repo") or (fw.get("repo") if fw["source"] != "thunderstore" else None))
        searched = False
        if sensitive and v["status"] != STATUS_UPDATED and not (official and official["supports_current"]) and issues_repo:
            rdt = parse_iso(rel.get("published_at"))
            since = max([d for d in (patch_dt, rdt) if d]).isoformat()
            found = breakage_reports(issues_repo, since, latest.get("version"), patch_dt)
            searched = found is not None
            reports = found or []
        confirmed = confirmed_breakage(reports)
        label = user_verdict(base_status=v["status"], age_days=age, sensitive=sensitive, breakage=confirmed,
                             official_support=bool(official and official["supports_current"]))
        if not sensitive:
            reason = (fw.get("agnostic_note", "Version-agnostic tool.") +
                      f" Latest release: {rel.get('tag_name')} ({(rel.get('published_at') or '')[:10]}).")
        elif official and official["supports_current"]:
            # The maintainer's page is the evidence; the timestamp-based sentence ("predates the patch;
            # compatibility is unverified") would contradict it, so it is dropped.
            reason = (f"Official page ({official['page']}) lists build {official['build']} for runtime "
                      f"{official['runtime']}, matching the latest tag (Bethesda often ships updates to a beta branch first).")
        elif confirmed:
            reason += f" {len(confirmed)} open issue(s) report breakage since the patch/latest release."
        elif reports:
            reason += (f" One unconfirmed user report of breakage is open ({reports[0]['title']!r}); not yet confirmed by the"
                       " maintainers or other users, so it isn't counted as breakage.")
        elif v["status"] != STATUS_UPDATED and label == "Likely safe" and v["status"] == STATUS_UNKNOWN:
            reason += quiet_period_note(age, issues_repo, searched)
        label, reason = apply_unannounced(label, reason, sensitive=sensitive,
                                          release_published_at=rel.get("published_at"), event=unannounced)
        if __import__("re").search(r"(?i)beta|alpha|\brc\d*\b|-pre", rel.get("tag_name") or ""):
            reason += " (Note: the author labels this build a beta/pre-release in its tag.)"
        if fw["source"] == "github_tags":
            reason += " (Date is the tagged commit on GitHub; builds are published on the official site.)"
        if rel.get("deprecated"):
            reason += " (Package is marked deprecated on Thunderstore.)"
        fws.append({**base, "status": label, "base_status": v["status"], "reason": reason,
                    "breakage_reports": reports, "official": official, "release_tag": rel.get("tag_name"),
                    "release_name": rel.get("name"), "release_published_at": rel.get("published_at"),
                    "release_url": rel.get("html_url") or fw["url"], "mentions_patch": v["mentions_patch"],
                    "newer_than_patch": v["newer_than_patch"], "mention_releases": lineage})

    for f in fws:
        off = f.get("official") or {}
        if off.get("runtime") and latest.get("version") and off["runtime"] != latest["version"]:
            latest["runtime_note"] = (f"{f['short']}'s official page lists game runtime {off['runtime']} as current "
                                      f"(the announcement title says {latest['version']}; Bethesda often ships silent hotfixes).")
            break

    history = []
    for p in patches:
        pm = make_mention_fn(p["version"], rule.get("mention"), rule.get("series_depth"))
        row = []
        for fw in game["frameworks"]:
            if fw["source"] == "manual" or fw["id"] not in rels_by:
                continue
            snap = status_for_patch_history(releases=rels_by[fw["id"]], patch_version=p["label"],
                                            patch_published_at=p["published_at"], mention_fn=pm)
            snap["status"] = history_label(snap["status"]) if not fw.get("agnostic") else "Not affected by patches"
            row.append({"id": fw["id"], "short": fw["short"], "name": fw["name"], **snap})
        history.append({**p, "frameworks": row})

    patch_urls = {p["url"] for p in patches}
    news_out = [{"title": n.get("title", ""), "url": n.get("url", ""),
                 "published_at": datetime.fromtimestamp(int(n["date"]), tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                 "is_patch": n.get("url") in patch_urls} for n in news
                if n.get("date") and (not game.get("news_include") or __import__("re").search(game["news_include"], n.get("title", ""), __import__("re").I))][:10]
    channels = []
    for ch in game.get("channels", []):
        hit = next((n for n in news if __import__("re").search(ch["include"], n.get("title", ""), __import__("re").I)), None)
        if hit:
            channels.append({"name": ch["name"], "title": hit["title"], "url": hit.get("url", ""),
                             "published_at": datetime.fromtimestamp(int(hit["date"]), tz=timezone.utc).isoformat().replace("+00:00", "Z")})
    pre = [r for r in rels_by.get(game["frameworks"][0]["id"], []) if r.get("prerelease")]
    stable = pick_latest_stable_release(rels_by.get(game["frameworks"][0]["id"], []) or [])
    pre = [r for r in pre if stable and (parse_iso(r.get("published_at")) or patch_dt) > parse_iso(stable.get("published_at"))]
    if channels and pre:
        channels.append({"name": f"{game['frameworks'][0]['short']} pre-release", "title": pre[0].get("tag_name"),
                         "url": pre[0].get("html_url"), "published_at": pre[0].get("published_at")})
    return {"latest_patch": latest, "frameworks": fws, "history": history, "news": news_out, "channels": channels,
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
    news_out = [{"title": f"Minecraft Java Edition {v['id']} released", "is_patch": True,
                 "url": patch_of(v)["url"], "published_at": patch_of(v)["published_at"]} for v in releases[:5]]
    return {"latest_patch": latest, "frameworks": fws, "history": history, "news": news_out,
            "latest_snapshot": man["latest"].get("snapshot"),
            "sources": {"mojang_manifest": MC_MANIFEST, "fabric_meta": FABRIC_GAME, "forge_promotions": FORGE_PROMOS,
                        "neoforge_maven": NEOFORGE_VERSIONS, "modrinth": "https://api.modrinth.com/v2"}}


def manual_steam_drift(game: dict, recorded: Optional[dict]) -> list[dict]:
    """Compare each edition's Steam public build (PICS) with the buildid recorded in the manual file.
    Never touches dev-c.com. On a failed lookup, reuse the committed drift for that edition so a flaky source
    can't flip the verdict either way."""
    if not recorded:
        return []
    public = {}
    prev = {}
    try:
        prev_lp = json.loads((DATA_DIR / f"{game['slug']}.json").read_text(encoding="utf-8"))["game"]["latest_patch"]
        pu = prev_lp.get("unannounced_update") or {}
        if pu.get("edition"):
            prev[pu["edition"]] = pu
    except Exception:  # noqa: BLE001
        pass
    for ed, appid in (game.get("steam_appids") or {}).items():
        try:
            public[ed] = parse_steam_public_build(http_get_json(STEAMCMD_INFO.format(appid=appid), retries=2), appid)
        except Exception as e:  # noqa: BLE001
            print(f"  WARNING: steamcmd build info failed for {ed} ({e}); reusing committed value", file=sys.stderr)
            pu = prev.get(ed)
            public[ed] = {"buildid": pu["buildid"], "published_at": pu["published_at"]} if pu else None
    return manual_build_drift(recorded, public)


def build_manual_game(game: dict) -> dict:
    """Hand-maintained game (GTA V): patch + hook data from data/manual/*.json; never fetches dev-c.com."""
    man = json.loads((ROOT / game["manual_file"]).read_text(encoding="utf-8"))
    lp = man["latest_patch"]
    latest = {k: lp.get(k) for k in ("label", "version", "published_at", "title", "url", "builds", "build_dates",
                                      "sources", "notes")}
    verified_age = patch_age_days(man["last_verified"] + "T00:00:00Z")
    age = patch_age_days(lp["published_at"])
    build_ages = {ed: patch_age_days(d + "T00:00:00Z") for ed, d in (lp.get("build_dates") or {}).items()}
    drift = manual_steam_drift(game, lp.get("steam_builds"))
    if drift:
        d0 = max(drift, key=lambda d: d["published_at"])
        latest["unannounced_update"] = {"version": None, "label": f"Unrecorded {d0['edition']} build {d0['published_at'][:10]}",
                                        "published_at": d0["published_at"], "buildid": d0["buildid"], "edition": d0["edition"],
                                        "source": "Steam public branch (api.steamcmd.net / PICS)"}
    fws = []
    for fw in game["frameworks"]:
        base = {"id": fw["id"], "name": fw["name"], "short": fw["short"], "url": fw["url"], "source": fw["source"],
                "tracked": True, "sensitive": not fw.get("agnostic"), "release_url": fw["url"]}
        if fw["source"] == "manual_shv":
            shv = man["script_hook_v"]
            v = manual_hook_verdict(supported=shv["supported_builds"], current=dict(lp["builds"]),
                                    patch_age=age, verified_age=verified_age, build_ages=build_ages)
            for d in drift:
                # Steam shipped a build the manual record doesn't know about: never claim support for it.
                v = {"status": V_WAIT, "reason": v["reason"] + (
                    f" Steam's public {d['edition'].title()} build changed on {d['published_at'][:10]} (build {d['buildid']}) "
                    "after the last manual check; Script Hook V support for it is unconfirmed, so hold that update.")}
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
    news_out = []
    try:
        items = http_get_json(STEAM_NEWS.format(appid=game["steam_appid"])).get("appnews", {}).get("newsitems", [])
        news_out = [{"title": n["title"], "url": n["url"], "is_patch": False,
                     "published_at": datetime.fromtimestamp(int(n["date"]), tz=timezone.utc).isoformat().replace("+00:00", "Z")}
                    for n in items[:10]]
    except Exception as e:  # noqa: BLE001
        print(f"  steam news failed for {game['slug']}: {e}", file=sys.stderr)
    return {"latest_patch": latest, "frameworks": fws, "history": [], "news": news_out, "last_verified": man["last_verified"],
            "sources": {"manual": game["manual_file"], "patch_sources": lp.get("sources", [])}}


DISCLAIMER = ("Statuses are inferred from public release data (Steam news, GitHub, Thunderstore, Mojang/Fabric/Forge/"
              "NeoForge/Modrinth APIs). They are not guarantees — verify on each project's page before updating.")


def steam_news_out(game: dict) -> list[dict]:
    try:
        items = http_get_json(STEAM_NEWS.format(appid=game["steam_appid"])).get("appnews", {}).get("newsitems", [])
    except Exception as e:  # noqa: BLE001
        print(f"  steam news failed for {game['slug']}: {e}", file=sys.stderr)
        return []
    out = []
    for n in items[:10]:
        url = f"https://store.steampowered.com/news/app/{game['steam_appid']}/view/{n['gid']}" if n.get("gid") else n.get("url", "")
        out.append({"title": n.get("title", ""), "url": url, "is_patch": False,
                    "published_at": datetime.fromtimestamp(int(n["date"]), tz=timezone.utc).isoformat().replace("+00:00", "Z")})
    return out


def releases_github_asset(fw: dict) -> list[dict]:
    """A rolling GitHub release whose asset is re-uploaded in place: date it by the asset's updated_at."""
    r = http_get_json(f"https://api.github.com/repos/{fw['repo']}/releases/tags/{fw['tag']}", headers=gh_headers())
    assets = [a for a in r.get("assets", []) if a.get("updated_at")]
    if not assets:
        raise RuntimeError(f"No assets on {fw['repo']}@{fw['tag']}")
    a = max(assets, key=lambda a: a["updated_at"])
    return [{"tag_name": a["name"], "name": r.get("name") or fw["tag"], "body": r.get("body") or "",
             "published_at": a["updated_at"], "html_url": r.get("html_url") or fw["url"], "prerelease": False, "draft": False}]


def build_atlan_game(game: dict) -> dict:
    """DOOM: The Dark Ages: Steam public build (PICS via api.steamcmd.net) vs Atlan patcher supported-build entries."""
    prev = {}
    try:
        prev = json.loads((DATA_DIR / f"{game['slug']}.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    build = parse_steam_public_build(http_get_json(STEAMCMD_INFO.format(appid=game["steam_appid"]), retries=2),
                                     game["steam_appid"])
    if not build:
        raise RuntimeError("No public build in Steam PICS data")
    latest = {"version": None, "label": f"Steam build {build['buildid']}", "title": f"Steam public build {build['buildid']}",
              "published_at": build["published_at"], "buildid": build["buildid"],
              "url": STEAMCMD_INFO.format(appid=game["steam_appid"]),
              "notes": "Steam doesn't publish version numbers for this game; the build id and its update time come from Steam's public branch."}
    fws = []
    for fw in game["frameworks"]:
        base = {"id": fw["id"], "name": fw["name"], "short": fw["short"], "url": fw["url"], "source": fw["source"],
                "repo": fw.get("repo"), "tracked": True, "sensitive": True}
        prev_fw = next((f for f in prev.get("frameworks", []) if f.get("id") == fw["id"]), None)
        try:
            entries = parse_atlan_config(http_get_text(fw["config_url"]))
            if not entries:
                raise RuntimeError("no dated darkage_steam entries")
            v = atlan_verdict(newest_entry=entries[0], build_published_at=build["published_at"])
        except Exception as e:  # noqa: BLE001
            print(f"  WARNING: Atlan config fetch failed ({e}); keeping last good result", file=sys.stderr)
            if prev_fw and prev_fw.get("supported_entries"):
                entries = prev_fw["supported_entries"]
                v = atlan_verdict(newest_entry=entries[0], build_published_at=build["published_at"])
                v["reason"] += " (Config temporarily unreachable; using the last good copy.)"
            else:
                fws.append({**base, "status": V_NODATA, "reason": f"Fetch failed: {e}", "error": str(e),
                            "release_tag": None, "release_published_at": None, "release_url": fw["url"]})
                continue
        try:
            rel = SOURCES[fw["release_source"]](fw)[0]
        except Exception as e:  # noqa: BLE001
            rel = {"tag_name": (prev_fw or {}).get("release_tag"), "published_at": (prev_fw or {}).get("release_published_at"),
                   "html_url": (prev_fw or {}).get("release_url") or fw["url"]}
            print(f"  WARNING: {fw['id']} release fetch failed ({e})", file=sys.stderr)
        fws.append({**base, **v, "base_status": None, "supported_entries": entries[:6], "config_url": fw["config_url"],
                    "release_tag": rel.get("tag_name"), "release_published_at": rel.get("published_at"),
                    "release_url": rel.get("html_url") or fw["url"], "mentions_patch": False, "newer_than_patch": False})
    return {"latest_patch": latest, "frameworks": fws, "history": [], "news": steam_news_out(game),
            "sources": {"steam_build": latest["url"], "atlan_config": game["frameworks"][0]["config_url"]}}


def build_game(game: dict) -> dict:
    kind = game.get("kind")
    body = (build_minecraft(game) if kind == "minecraft" else build_manual_game(game) if kind == "manual"
            else build_atlan_game(game) if kind == "atlan" else build_steam_game(game))
    tracked = [f["status"] for f in body["frameworks"] if f.get("tracked") and f.get("sensitive", True)]
    return {
        "generated_at": now_iso(),
        "game": {"slug": game["slug"], "name": game["name"], "steam_appid": game.get("steam_appid"),
                 "latest_patch": body.pop("latest_patch")},
        "verdict": game_verdict(tracked),
        "disclaimer": DISCLAIMER,
        **body,
    }


def previous_framework(slug: str, fw_id: str, latest: dict) -> Optional[dict]:
    """Last good committed entry for this framework, only if it was evaluated against the same latest patch."""
    try:
        prev = json.loads((DATA_DIR / f"{slug}.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    pp = (prev.get("game") or {}).get("latest_patch") or {}
    if pp.get("label") != latest.get("label") or pp.get("published_at") != latest.get("published_at"):
        return None
    for f in prev.get("frameworks") or []:
        if f.get("id") == fw_id and not f.get("error") and f.get("status") != V_NODATA:
            return f
    return None


def should_skip_refetch(env=os.environ) -> Optional[str]:
    """Pages builds (CF_PAGES) and token-less runs must not refetch: unauthenticated GitHub calls hit rate limits
    and would publish 'No data'. They use the data/games/*.json the scheduled Actions workflow commits."""
    if env.get("MODSAFE_FORCE_UPDATE") == "1":
        return None
    if env.get("CF_PAGES"):
        return "running on Cloudflare Pages (CF_PAGES set)"
    if not (env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")):
        return "no GITHUB_TOKEN/GH_TOKEN set"
    return None


def main(argv: list[str]) -> int:
    skip = should_skip_refetch()
    if skip:
        print(f"update: skipping refetch ({skip}); using committed data/games/*.json. "
              "Set GITHUB_TOKEN (or MODSAFE_FORCE_UPDATE=1) to refresh.")
        return 0
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
    if not only:
        try:
            import news as _news
            _news.main()
        except Exception as e:  # noqa: BLE001
            print(f"WARNING: news feed failed ({e}); keeping previous data/news.json", file=sys.stderr)
    missing = [g["slug"] for g in GAMES if not (DATA_DIR / f"{g['slug']}.json").exists()]
    if missing:
        print(f"ERROR: no data at all for {missing}", file=sys.stderr)
        return 1
    if failures:
        print(f"WARNING: used cached data for {failures}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
