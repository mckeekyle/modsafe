"""Site-wide patch timeline (/patches/): pure data helpers, stdlib only.

Built from data already in data/games/<slug>.json:
- ``history`` + ``game.latest_patch`` (+ ``unannounced_update``) for the patch list, and
- ``verdict_log`` (via feeds.game_events) for the "verdict changes" stream and the last verdict
  ModSafe recorded for an older patch.
Everything is recomputed at build time, so the 6-hourly refresh keeps the page current.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import feeds

PATCH_WINDOW_DAYS = 365   # older patches are on each game's /history/ page
PATCH_LIMIT = 60
EVENT_LIMIT = 20
HST = timezone(timedelta(hours=-10), "HST")


def parse(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def fmt_utc(dt: datetime) -> str:
    """'Oct 28, 2026 · 10:54 UTC'"""
    dt = dt.astimezone(timezone.utc)
    return f"{dt.strftime('%b')} {dt.day}, {dt.year} · {dt.strftime('%H:%M')} UTC"


def fmt_hst(dt: datetime) -> str:
    """'12:54 AM HST, Oct 28' (US Pacific/Honolulu, no DST)"""
    dt = dt.astimezone(HST)
    return f"{dt.strftime('%I:%M %p').lstrip('0')} HST, {dt.strftime('%b')} {dt.day}"


def _last_logged_verdicts(data: dict) -> dict:
    out = {}
    for e in data.get("verdict_log") or []:
        if e.get("verdict") and e.get("verdict") not in feeds.SKIP_VERDICTS:
            out[e.get("patch_key")] = e["verdict"]
    return out


def collect_patches(games_data, now: datetime | None = None, window_days: int = PATCH_WINDOW_DAYS,
                    limit: int = PATCH_LIMIT) -> list[dict]:
    """Newest-first list of game patches across all games.

    Each item: game, label, title, url (official source or None), at (aware datetime), current (bool),
    verdict (current verdict for the current patch; for older patches the last verdict ModSafe logged
    for it, or None if the patch predates the log), unannounced (bool).
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    items = []
    for game, data in games_data:
        lp = data["game"]["latest_patch"]
        logged = _last_logged_verdicts(data)
        entries = list(data.get("history") or [])
        if not any(e.get("label") == lp.get("label") for e in entries):
            entries.insert(0, lp)
        seen = set()
        for e in entries:
            at = parse(e.get("published_at"))
            key = (e.get("label"), e.get("published_at"))
            if not at or key in seen:
                continue
            seen.add(key)
            current = e.get("label") == lp.get("label")
            verdict = data["verdict"] if current else logged.get(feeds.patch_key(e))
            items.append({"game": game, "label": e.get("label") or "Update", "title": e.get("title") or "",
                          "url": e.get("url"), "at": at, "current": current, "verdict": verdict, "unannounced": False})
        uu = lp.get("unannounced_update")
        if uu and parse(uu.get("published_at")):
            ed = f"{uu['edition'].title()} " if uu.get("edition") else ""
            items.append({"game": game, "label": f"{ed}Steam build {uu.get('buildid') or '?'}",
                          "title": "Steam build changed with no patch notes", "url": None,
                          "at": parse(uu["published_at"]), "current": True, "verdict": data["verdict"],
                          "unannounced": True})
    items = [i for i in items if cutoff <= i["at"] <= now + timedelta(days=1)]
    items.sort(key=lambda i: i["at"], reverse=True)
    # Only the newest row per game is "current"; an unannounced build after the announced patch supersedes it.
    newer: dict[str, str] = {}
    for i in items:
        slug = i["game"]["slug"]
        i["superseded_by"] = newer.get(slug)
        if i["current"] and slug in newer:
            i["current"], i["verdict"] = False, None
        newer[slug] = i["label"]
    return items[:limit]


def recent_events(games_data, limit: int = EVENT_LIMIT) -> list[dict]:
    """Newest verdict-log events across all games (new patches, verdict flips, framework catch-ups)."""
    evs = []
    for game, data in games_data:
        for ev in feeds.game_events(game, data):
            if ev["kind"] == "status":
                continue  # first observation of a game, not a change
            at = parse(ev["entry"].get("at"))
            if at:
                evs.append({**ev, "at": at, "title": feeds.event_title(ev)})
    evs.sort(key=lambda e: e["at"], reverse=True)
    return evs[:limit]


def counts(items: list[dict], now: datetime) -> dict:
    return {"7d": sum(1 for i in items if i["at"] >= now - timedelta(days=7)),
            "30d": sum(1 for i in items if i["at"] >= now - timedelta(days=30))}
