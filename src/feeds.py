"""Verdict-change log + Atom feeds (stdlib only).

`./update` appends an event to each game's ``verdict_log`` (in data/games/<slug>.json) whenever the current patch,
the game verdict, or the status of a patch-sensitive tracked framework changes. The log is committed with the data,
so feed entries keep the timestamp they were first observed at and a GUID that never changes on rebuilds:

    tag:modsafe.app,2026:<slug>/<patch-key>/<verdict-id>/<YYYYMMDDTHHMMZ of the event>

``./build`` renders /feed.xml (all games) and /<slug>/feed.xml (one game) as Atom 1.0 from that log.
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone

LOG_MAX = 40            # events kept per game in data/games/<slug>.json
SITE_FEED_MAX = 50      # entries in /feed.xml
GAME_FEED_MAX = 25      # entries in /<slug>/feed.xml
FEED_FALLBACK_UPDATED = "2026-10-22T00:00:00Z"
SKIP_VERDICTS = {"No data"}  # fetch hiccups must not create feed entries

VERDICT_IDS = {
    "Safe": "safe", "Likely safe": "likely-safe", "Just patched, wait": "wait", "Breakage reported": "broken",
    "Not ported yet": "not-ported", "No data": "no-data", "Not affected by patches": "not-affected",
    "Check manually": "manual",
}


def verdict_id(label: str | None) -> str:
    if not label:
        return "no-data"
    return VERDICT_IDS.get(label) or (re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "no-data")


def patch_key(lp: dict) -> str:
    raw = str(lp.get("version") or lp.get("label") or "unknown")
    return re.sub(r"[^a-z0-9.]+", "-", raw.lower()).strip("-.") or "unknown"


def _sensitive(fw: dict) -> bool:
    return fw.get("tracked", True) and fw.get("sensitive", True)


def log_entry(payload: dict) -> dict:
    lp = payload["game"]["latest_patch"]
    return {
        "at": payload.get("generated_at") or FEED_FALLBACK_UPDATED,
        "patch": lp.get("label"),
        "patch_key": patch_key(lp),
        "patch_published_at": lp.get("published_at"),
        "patch_url": lp.get("url"),
        "verdict": payload.get("verdict"),
        "frameworks": [{"short": f.get("short") or f.get("name"), "status": f.get("status"),
                        "release_tag": f.get("release_tag")} for f in payload.get("frameworks", []) if _sensitive(f)],
    }


def _signature(e: dict) -> tuple:
    return (e.get("patch_key"), e.get("verdict"), tuple((f["short"], f["status"]) for f in e.get("frameworks", [])))


def append_verdict_log(prev_log: list | None, payload: dict, max_len: int = LOG_MAX) -> list:
    """Return the log with an event for ``payload`` appended if anything feed-worthy changed (pure function)."""
    log = list(prev_log or [])
    if payload.get("verdict") in SKIP_VERDICTS:
        return log
    e = log_entry(payload)
    if any(f["status"] in SKIP_VERDICTS for f in e["frameworks"]):
        # A single framework fetch failed; wait for a clean run rather than logging a fake change.
        return log
    if log and _signature(log[-1]) == _signature(e):
        return log
    log.append(e)
    return log[-max_len:]


def _compact(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)
        return dt.strftime("%Y%m%dT%H%MZ")
    except (ValueError, AttributeError):
        return re.sub(r"[^0-9TZ]", "", str(iso))[:14] or "0"


def _iso(iso: str | None) -> str:
    if not iso:
        return FEED_FALLBACK_UPDATED
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return FEED_FALLBACK_UPDATED


def entry_id(slug: str, e: dict) -> str:
    return f"tag:modsafe.app,2026:{slug}/{e['patch_key']}/{verdict_id(e['verdict'])}/{_compact(e['at'])}"


def game_events(game: dict, data: dict) -> list[dict]:
    """Feed events for one game, newest first. Falls back to the current state if no log exists yet."""
    log = data.get("verdict_log") or []
    if not log and data.get("verdict") not in SKIP_VERDICTS:
        log = [log_entry(data)]
    out, seen = [], set()
    prev = None
    for e in log:
        eid = entry_id(game["slug"], e)
        if eid in seen:
            prev = e
            continue
        seen.add(eid)
        kind, changed = "status", []
        if prev is not None and prev.get("patch_key") != e.get("patch_key"):
            kind = "new-patch"
        elif prev is not None:
            kind = "verdict" if prev.get("verdict") != e.get("verdict") else "framework"
            before = {f["short"]: f["status"] for f in prev.get("frameworks", [])}
            changed = [f for f in e.get("frameworks", []) if before.get(f["short"]) != f["status"]]
        out.append({"id": eid, "game": game, "entry": e, "kind": kind, "prev_verdict": (prev or {}).get("verdict"),
                    "changed": changed})
        prev = e
    return out[::-1]


def event_title(ev: dict) -> str:
    g, e = ev["game"], ev["entry"]
    name, patch, v = g["name"], e.get("patch") or "latest patch", e.get("verdict")
    if ev["kind"] == "new-patch":
        return f"{name}: {patch} is out — {v}"
    if ev["kind"] == "verdict":
        return f"{name} {patch}: now {v} (was {ev['prev_verdict']})"
    if ev["kind"] == "framework" and ev["changed"]:
        fws = ", ".join(f"{f['short']} {f['status']}" for f in ev["changed"][:3])
        more = f" +{len(ev['changed']) - 3}" if len(ev["changed"]) > 3 else ""
        return f"{name} {patch}: {fws}{more} (overall: {v})"
    return f"{name} {patch}: {v}"


def event_html(ev: dict, page_url: str) -> str:
    e = ev["entry"]
    esc = html.escape
    changed = {f["short"] for f in ev["changed"]}
    lis = "".join(
        f"<li>{'<strong>' if f['short'] in changed else ''}{esc(f['short'])}: {esc(f['status'] or '')}"
        f"{' (' + esc(f['release_tag']) + ')' if f.get('release_tag') else ''}{'</strong>' if f['short'] in changed else ''}</li>"
        for f in e.get("frameworks", []))
    patch_src = (f' — <a href="{esc(e["patch_url"])}">official notes</a>' if e.get("patch_url") else "")
    released = f", released {esc((e.get('patch_published_at') or '')[:10])}" if e.get("patch_published_at") else ""
    return (f"<p><strong>{esc(ev['game']['name'])}</strong> {esc(e.get('patch') or '')}{released}{patch_src}.</p>"
            f"<p>ModSafe verdict: <strong>{esc(e.get('verdict') or '')}</strong>"
            f"{' (was ' + esc(ev['prev_verdict']) + ')' if ev['kind'] == 'verdict' else ''}.</p>"
            f"{'<p>Patch-sensitive frameworks:</p><ul>' + lis + '</ul>' if lis else ''}"
            f'<p><a href="{esc(page_url)}">Full status, sources and FAQ on ModSafe</a></p>')


def _x(s: object) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def render_atom(events: list[dict], *, feed_id: str, title: str, subtitle: str, self_url: str, alt_url: str,
                site_url: str, limit: int) -> str:
    evs = sorted(events, key=lambda ev: (_iso(ev["entry"]["at"]), ev["id"]), reverse=True)[:limit]
    updated = _iso(evs[0]["entry"]["at"]) if evs else FEED_FALLBACK_UPDATED
    parts = ['<?xml version="1.0" encoding="utf-8"?>',
             '<feed xmlns="http://www.w3.org/2005/Atom">',
             f"  <title>{_x(title)}</title>",
             f"  <subtitle>{_x(subtitle)}</subtitle>",
             f"  <id>{_x(feed_id)}</id>",
             f'  <link rel="self" type="application/atom+xml" href="{_x(self_url)}"/>',
             f'  <link rel="alternate" type="text/html" href="{_x(alt_url)}"/>',
             f"  <updated>{updated}</updated>",
             f"  <author><name>ModSafe</name><uri>{_x(site_url)}/</uri></author>",
             f"  <icon>{_x(site_url)}/img/logo.png</icon>",
             '  <generator uri="https://modsafe.app/">ModSafe build.py</generator>']
    for ev in evs:
        e, g = ev["entry"], ev["game"]
        page = f"{site_url}/{g['slug']}/"
        ts = _iso(e["at"])
        parts += ["  <entry>",
                  f"    <id>{_x(ev['id'])}</id>",
                  f"    <title>{_x(event_title(ev))}</title>",
                  f'    <link rel="alternate" type="text/html" href="{_x(page)}"/>',
                  f"    <published>{ts}</published>",
                  f"    <updated>{ts}</updated>",
                  f'    <category term="{_x(verdict_id(e.get("verdict")))}" label="{_x(e.get("verdict"))}"/>',
                  f'    <category term="{_x(g["slug"])}" label="{_x(g["name"])}"/>',
                  f"    <summary>{_x(event_title(ev))}</summary>",
                  f'    <content type="html">{_x(event_html(ev, page))}</content>',
                  "  </entry>"]
    parts.append("</feed>")
    return "\n".join(parts) + "\n"


def site_feed(games_data, site_url: str) -> str:
    evs = [ev for g, d in games_data for ev in game_events(g, d)]
    return render_atom(evs, feed_id="tag:modsafe.app,2026:feed", title="ModSafe — mod status changes",
                       subtitle="New game patches and mod framework verdict changes for every game ModSafe tracks.",
                       self_url=f"{site_url}/feed.xml", alt_url=f"{site_url}/", site_url=site_url, limit=SITE_FEED_MAX)


def game_feed(game: dict, data: dict, site_url: str) -> str:
    return render_atom(game_events(game, data), feed_id=f"tag:modsafe.app,2026:feed/{game['slug']}",
                       title=f"ModSafe — {game['name']} mod status",
                       subtitle=f"New {game['name']} patches and mod framework verdict changes.",
                       self_url=f"{site_url}/{game['slug']}/feed.xml", alt_url=f"{site_url}/{game['slug']}/",
                       site_url=site_url, limit=GAME_FEED_MAX)
