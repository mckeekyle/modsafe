"""Track-record statistics derived only from our own data/games/<slug>.json history + verdict_log.

Rules (so nothing is invented):
- A patch/framework pair counts only if the framework's release data reaches back to the patch
  (``data_from <= patch published_at``). Older pairs are "outside our release data" and are skipped.
- Frameworks that patches don't affect are skipped.
- "Days to an update" = time from the patch post to the framework's earliest stable release whose notes name the
  patch (a release up to 2 days before the patch counts as 0 days). Pairs with no naming release are counted
  separately: the framework may simply not have needed an update.
- "Next release" = days to the framework's first stable release after the patch for any reason, counted only when
  it came before the following patch (shown as context, not as a fix time).
- Unsafe stretches come from the verdict log (kept since it started), not from guesses.
"""

from __future__ import annotations

import statistics
from datetime import datetime, timezone

UNSAFE = ("Breakage reported", "Just patched, wait", "Not ported yet")
NOT_AFFECTED = "Not affected by patches"


def _dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def _days(a, b) -> float:
    return max(0.0, (b - a).total_seconds() / 86400)


def next_patch_dates(history: list[dict]) -> list:
    """For each history entry, the publish time of the following (newer) patch, or None for the newest."""
    dated = sorted(((_dt(e.get("published_at")), i) for i, e in enumerate(history) if _dt(e.get("published_at"))),
                   key=lambda t: t[0])
    out = [None] * len(history)
    for (_, i), (nd, _) in zip(dated, dated[1:]):
        out[i] = nd
    return out


def pair_info(entry: dict, fw: dict, until: datetime | None = None) -> dict:
    """Classify one patch/framework pair.

    kind: 'named' (a release naming the patch exists; ``days`` from patch post to the earliest such release),
    'unnamed' (our release data covers the patch but no release names it: the framework may not have needed
    an update, or it hasn't shipped one yet), 'outside' (patch predates our release data) or 'skip' (not affected).
    ``next_days`` is the time to the first stable release for any reason, only if it came before ``until``
    (the following patch).
    """
    if fw.get("status") == NOT_AFFECTED:
        return {"kind": "skip"}
    p_at, d_from = _dt(entry.get("published_at")), _dt(fw.get("data_from"))
    if not p_at or not d_from or d_from > p_at:
        return {"kind": "outside"}
    named = _dt(fw.get("first_mention_at"))
    nxt = _dt(fw.get("first_release_at"))
    if nxt and until and nxt > until:
        nxt = None  # first release came after the following patch: it belongs to that patch, not this one
    base = {"next_tag": fw.get("first_release_tag") if nxt else None, "next_days": _days(p_at, nxt) if nxt else None}
    if not named:
        return {"kind": "unnamed", **base}
    return {"kind": "named", "days": _days(p_at, named), "tag": fw.get("first_mention_tag"), **base}


def framework_stats(history: list[dict]) -> list[dict]:
    order, acc = [], {}
    bounds = next_patch_dates(history)
    for entry, until in zip(history, bounds):
        for fw in entry.get("frameworks", []):
            key = fw.get("short") or fw.get("id")
            if key not in acc:
                order.append(key)
                acc[key] = {"short": key, "name": fw.get("name") or key, "days": [], "next": [], "unnamed": 0, "outside": 0,
                            "longest": None, "affected": True}
            a, info = acc[key], pair_info(entry, fw, until)
            if info["kind"] == "skip":
                a["affected"] = False
            if info.get("next_days") is not None:
                a["next"].append(info["next_days"])
            if info["kind"] in ("outside", "unnamed"):
                a[info["kind"]] += 1
            elif info["kind"] == "named":
                a["days"].append(info["days"])
                if a["longest"] is None or info["days"] > a["longest"][0]:
                    a["longest"] = (info["days"], entry.get("label"))
    out = []
    for key in order:
        a = acc[key]
        d = a["days"]
        a["n"] = len(d)
        a["median"] = statistics.median(d) if d else None
        a["mean"] = statistics.fmean(d) if d else None
        a["next_median"] = statistics.median(a["next"]) if a["next"] else None
        out.append(a)
    return out


def unsafe_stretches(verdict_log: list[dict], now: datetime | None = None) -> list[dict]:
    """Contiguous runs of unsafe verdicts in the verdict log, with start, end (None if ongoing) and length."""
    now = now or datetime.now(timezone.utc)
    runs, cur = [], None
    for e in sorted(verdict_log or [], key=lambda e: e.get("at", "")):
        at = _dt(e.get("at"))
        if not at:
            continue
        if e.get("verdict") in UNSAFE:
            if cur is None:
                cur = {"start": at, "patch": e.get("patch"), "verdicts": []}
            if e["verdict"] not in cur["verdicts"]:
                cur["verdicts"].append(e["verdict"])
        elif cur is not None:
            cur.update(end=at, end_verdict=e.get("verdict"), days=_days(cur["start"], at))
            runs.append(cur)
            cur = None
    if cur is not None:
        cur.update(end=None, end_verdict=None, days=_days(cur["start"], now))
        runs.append(cur)
    return runs


def game_summary(data: dict, now: datetime | None = None) -> dict:
    history = data.get("history") or []
    dates = sorted(d for d in (_dt(e.get("published_at")) for e in history) if d)
    gaps = [_days(a, b) for a, b in zip(dates, dates[1:])]
    pairs, nexts, outside, unnamed, longest = [], [], 0, 0, None
    for entry, until in zip(history, next_patch_dates(history)):
        for fw in entry.get("frameworks", []):
            info = pair_info(entry, fw, until)
            if info.get("next_days") is not None:
                nexts.append(info["next_days"])
            if info["kind"] == "named":
                pairs.append(info["days"])
                if longest is None or info["days"] > longest["days"]:
                    longest = {"days": info["days"], "fw": fw.get("short"), "patch": entry.get("label"),
                               "tag": info["tag"]}
            elif info["kind"] == "outside":
                outside += 1
            elif info["kind"] == "unnamed":
                unnamed += 1
    runs = unsafe_stretches(data.get("verdict_log") or [], now)
    log_start = min((_dt(e.get("at")) for e in data.get("verdict_log") or [] if _dt(e.get("at"))), default=None)
    return {
        "patches": len(history),
        "first": dates[0] if dates else None,
        "last": dates[-1] if dates else None,
        "avg_gap": statistics.fmean(gaps) if gaps else None,
        "pairs": len(pairs),
        "mean_days": statistics.fmean(pairs) if pairs else None,
        "median_days": statistics.median(pairs) if pairs else None,
        "longest_wait": longest,
        "next_pairs": len(nexts),
        "next_median": statistics.median(nexts) if nexts else None,
        "outside": outside,
        "unnamed": unnamed,
        "frameworks": framework_stats(history),
        "stretches": runs,
        "longest_stretch": max(runs, key=lambda r: r["days"]) if runs else None,
        "log_start": log_start,
    }


def fmt_days(d: float | None) -> str:
    if d is None:
        return "—"
    if d < 1:
        h = round(d * 24)
        return "under 1 hour" if h < 1 else f"{h} hour{'s' if h != 1 else ''}"
    r = round(d, 1)
    return f"{r:g} day{'s' if r != 1 else ''}"
