#!/usr/bin/env python3
"""Cheap patch-day probe for the 30-minute fast-check workflow.

  fast_check.py probe       Compare a few cheap live signals (Steam public build, Steam patch news, framework
                            latest release, Steam Workshop update times, Atlan config, Mojang manifest) with the
                            committed data/games/*.json.
                            Prints the games to refresh and, on GitHub Actions, writes `games`, `changed`, `waiting`,
                            `sig` and `reason` to $GITHUB_OUTPUT. Never fails the job on a fetch error: a source that
                            can't be read simply doesn't trigger anything (the 6-hourly full refresh still covers it).
  fast_check.py meaningful  Exit 0 when the working-tree data/games/*.json differ from HEAD in a field users see
                            (verdict, patch, builds, framework status/release), 1 when only timestamps/news moved.
                            The fast-mode workflow commits only on 0, so it doesn't spend Cloudflare Pages builds.

The baseline is the committed data, not a cache, so a full refresh automatically "acknowledges" every change.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import games as games_mod  # noqa: E402
import update  # noqa: E402
from status_logic import (V_WAIT, list_patches_generic, merge_silent_patches, parse_atlan_config,  # noqa: E402
                          parse_steam_public_build, pick_latest_stable_release)

GAMES = getattr(games_mod, "ALL_GAMES", games_mod.GAMES)
DATA = ROOT / "data" / "games"


class LiveFetch:
    """Network signals; each call may raise (the caller treats that as 'no signal')."""

    def steam_build(self, appid):
        b = parse_steam_public_build(update.http_get_json(update.STEAMCMD_INFO.format(appid=appid), timeout=15,
                                                          retries=1), appid)
        return b["buildid"] if b and b.get("buildid") else None

    def steam_news(self, appid):
        return update.http_get_json(update.STEAM_NEWS.format(appid=appid), timeout=15, retries=1).get(
            "appnews", {}).get("newsitems", [])

    def releases(self, fw, source=None):
        return update.SOURCES[source or fw["source"]](fw)

    def atlan_entries(self, fw):
        return parse_atlan_config(update.http_get_text(fw["config_url"], timeout=15))

    def workshop(self, ids):
        return update.workshop_details(ids)

    def mc_latest(self):
        man = update.http_get_json(update.MC_MANIFEST, timeout=15, retries=1)
        return next(v["id"] for v in man["versions"] if v["type"] == "release")

    def manual(self, game):
        return json.loads((ROOT / game["manual_file"]).read_text(encoding="utf-8"))


def _try(fn, *a):
    try:
        return fn(*a)
    except Exception as e:  # noqa: BLE001
        print(f"  ({getattr(fn, '__name__', 'fetch')} failed: {e}; ignored)", file=sys.stderr)
        return None


def probe_game(game: dict, committed: dict | None, fetch) -> list[str]:
    """Human-readable reasons this game's committed data looks stale ([] = nothing to do)."""
    if not committed:
        return []  # no baseline yet: the 6-hourly refresh creates it
    lp = (committed.get("game") or {}).get("latest_patch") or {}
    fws = {f.get("id"): f for f in committed.get("frameworks") or []}
    slug, kind, out = game["slug"], game.get("kind"), []

    if kind == "minecraft":
        mc = _try(fetch.mc_latest)
        if mc and lp.get("label") and mc != lp["label"]:
            out.append(f"Minecraft {lp['label']} -> {mc}")
        return out

    if kind == "manual":
        man = _try(fetch.manual, game) or {}
        recorded = ((man.get("latest_patch") or {}).get("steam_builds")) or {}
        uu = lp.get("unannounced_update") or {}
        for ed, appid in (game.get("steam_appids") or {}).items():
            if ed not in recorded:
                continue
            live = _try(fetch.steam_build, appid)
            if not live:
                continue
            known = uu.get("buildid") if uu.get("edition") == ed else recorded[ed]
            if str(live) != str(known):
                out.append(f"{ed} Steam build {known} -> {live}")
    elif kind == "atlan":
        live = _try(fetch.steam_build, game["steam_appid"])
        if live and lp.get("buildid") and str(live) != str(lp["buildid"]):
            out.append(f"Steam build {lp['buildid']} -> {live}")
    else:  # Steam news + Steam public build
        live = _try(fetch.steam_build, game["steam_appid"])
        if live and lp.get("steam_build") and str(live) != str(lp["steam_build"]):
            out.append(f"Steam build {lp['steam_build']} -> {live}")
        news = _try(fetch.steam_news, game["steam_appid"])
        if news and game.get("patch_rule"):
            patches = merge_silent_patches(list_patches_generic(news, game["patch_rule"], limit=12),
                                           update.silent_patches_for(slug))
            if patches and lp.get("label") and patches[0]["label"] != lp["label"]:
                out.append(f"patch {lp['label']} -> {patches[0]['label']}")

    if kind == "workshop":  # one keyless Workshop call for every tracked mod: compare last-update times
        wfw = [fw for fw in game.get("frameworks") or [] if fw.get("workshop_id")]
        items = _try(fetch.workshop, [fw["workshop_id"] for fw in wfw]) or {}
        for fw in wfw:
            prev, it = fws.get(fw["id"]) or {}, items.get(str(fw["workshop_id"]))
            if it and prev.get("release_published_at") and not prev.get("error") \
                    and it["time_updated"] != prev["release_published_at"]:
                out.append(f"{fw['short']} Workshop update {prev['release_published_at'][:16]} -> {it['time_updated'][:16]}")
        return out

    for fw in game.get("frameworks") or []:
        prev = fws.get(fw["id"]) or {}
        if kind == "atlan":
            entries = _try(fetch.atlan_entries, fw)
            old = (prev.get("supported_entries") or [None])[0]
            if entries and old and entries[0] != old:
                out.append(f"{fw['short']} config {old} -> {entries[0]}")
            src = fw.get("release_source")
            rels = _try(fetch.releases, fw, src) if src in update.SOURCES else None
            tag = (rels or [{}])[0].get("tag_name") if rels else None
        elif fw.get("source") in update.SOURCES:
            rels = _try(fetch.releases, fw)
            rel = pick_latest_stable_release(rels) if rels else None
            tag = rel.get("tag_name") if rel else None
        else:
            continue  # manual / Minecraft loader sources: covered by the 6-hourly refresh
        if tag and prev.get("release_tag") and not prev.get("error") and tag != prev["release_tag"]:
            out.append(f"{fw['short']} {prev['release_tag']} -> {tag}")
    return out


def load_committed(slug: str) -> dict | None:
    try:
        return json.loads((DATA / f"{slug}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def probe(games: list[dict], fetch=None, load=load_committed, workers: int = 8) -> dict:
    fetch = fetch or LiveFetch()
    changed, waiting = {}, []
    committed = {g["slug"]: load(g["slug"]) for g in games}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda g: (g["slug"], probe_game(g, committed[g["slug"]], fetch)), games))
    for slug, reasons in results:
        if reasons:
            changed[slug] = reasons
    for g in games:
        d = committed[g["slug"]]
        if d and d.get("verdict") == V_WAIT:
            waiting.append(g["slug"])
    def expand(slugs) -> list[str]:
        # GTA V: the editions and the combined compat record share one manual file, so refresh them together.
        out = set(slugs)
        for g in games:
            group = {g["slug"], *(g.get("editions") or [])}
            if g.get("editions") and out & group:
                out |= {s for s in group if s in committed}
        return sorted(out)

    run = expand(set(changed) | set(waiting))
    # Signature of what changed (not of waiting games): the workflow dispatches a given change at most once.
    sig = hashlib.sha256(json.dumps(changed, sort_keys=True).encode()).hexdigest()[:16] if changed else ""
    reason = "; ".join(f"{s}: {', '.join(r)}" for s, r in sorted(changed.items()))
    if waiting:
        reason = (reason + "; " if reason else "") + "waiting: " + " ".join(waiting)
    # changed_run / waiting_run are the group-expanded sets the workflow dispatches (it re-combines them after
    # deciding whether this change signature was already handled).
    return {"games": run, "changed": changed, "waiting": waiting, "changed_run": expand(changed),
            "waiting_run": expand(waiting), "sig": sig, "reason": reason[:900]}


# --- meaningful diff -------------------------------------------------------------------------------------------

def fingerprint(d: dict | None):
    """The user-visible part of a data/games/<slug>.json (no generated_at, news, or check timestamps)."""
    if not d:
        return None
    lp = (d.get("game") or {}).get("latest_patch") or {}
    uu = lp.get("unannounced_update") or {}
    return {
        "verdict": d.get("verdict"),
        "patch": [lp.get(k) for k in ("label", "published_at", "steam_build", "buildid")],
        "builds": lp.get("builds"),
        "unannounced": [uu.get("buildid"), uu.get("published_at"), uu.get("edition")] if uu else None,
        "verdict_log": len(d.get("verdict_log") or []),
        "frameworks": [[f.get("id"), f.get("status"), f.get("release_tag"), f.get("release_published_at"),
                        f.get("reason"), (f.get("supported_entries") or [None])[0]] for f in d.get("frameworks") or []],
        "history": [h.get("label") for h in d.get("history") or []],
    }


def meaningful(changed: dict[str, tuple[dict | None, dict | None]]) -> list[str]:
    """Slugs whose (old, new) data differ in a user-visible way."""
    return sorted(s for s, (old, new) in changed.items() if fingerprint(old) != fingerprint(new))


def _git_show(path: str) -> dict | None:
    r = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


def worktree_changes() -> dict[str, tuple[dict | None, dict | None]]:
    out = subprocess.run(["git", "status", "--porcelain", "--", "data/games"], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout
    res = {}
    for line in out.splitlines():
        path = line[3:].strip()
        if path.endswith(".json"):
            slug = Path(path).stem
            res[slug] = (_git_show(path), load_committed(slug))
    return res


def write_outputs(res: dict) -> None:
    gh = os.environ.get("GITHUB_OUTPUT")
    if not gh:
        return
    with open(gh, "a", encoding="utf-8") as f:
        f.write(f"games={' '.join(res['games'])}\n")
        f.write(f"changed={' '.join(res['changed_run'])}\n")
        f.write(f"waiting={' '.join(res['waiting_run'])}\n")
        f.write(f"sig={res['sig']}\n")
        f.write(f"reason={res['reason'].replace(chr(10), ' ')}\n")


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "probe"
    if cmd == "probe":
        res = probe(GAMES)
        for s, r in sorted(res["changed"].items()):
            print(f"CHANGED {s}: {', '.join(r)}")
        print(f"waiting: {' '.join(res['waiting']) or '-'}")
        print(f"games to refresh: {' '.join(res['games']) or '(none)'}")
        write_outputs(res)
        return 0
    if cmd == "meaningful":
        m = meaningful(worktree_changes())
        print(f"meaningful changes: {' '.join(m) or '(none)'}")
        return 0 if m else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
