#!/usr/bin/env python3
"""ModSafe verdict alerts for Discord.

Posts a message to a Discord channel (through a channel webhook) whenever a game's ModSafe verdict changes,
for example "Just patched, wait" -> "Likely safe". It reads the public feed at
https://modsafe.app/api/v1/status.json, remembers the last verdict it saw for each game in a small JSON state
file, and posts only the differences. Python 3.9+ standard library only; no bot token, no hosting by ModSafe.

  python modsafe_alerts.py                 check once (run it every 30 minutes from cron / Task Scheduler / Actions)
  python modsafe_alerts.py --loop 30       keep running, checking every 30 minutes
  python modsafe_alerts.py --dry-run       print what would be posted; never contacts Discord
  python modsafe_alerts.py --test          post one sample message, to check the webhook works

Settings (command-line flags win over environment variables):
  --webhook  / MODSAFE_DISCORD_WEBHOOK   the channel webhook URL (required unless --dry-run). Keep it secret.
  --games    / MODSAFE_GAMES             optional comma-separated game ids to watch, e.g. "skyrim-se,fallout-4".
                                         Default: all games. Ids are listed by --list-games.
  --state    / MODSAFE_STATE_FILE        where to remember verdicts (default: modsafe_alerts_state.json next to this file)

The first run only records the current verdicts and posts nothing (use --announce-current to post them all once).
State is saved only after Discord accepts a message, so a failed post is retried on the next run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

FEED_URL = "https://modsafe.app/api/v1/status.json"
USER_AGENT = "ModSafe-Discord-Alerts/1.0 (+https://modsafe.app/)"
WEBHOOK_PREFIXES = ("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/",
                    "https://ptb.discord.com/api/webhooks/", "https://canary.discord.com/api/webhooks/")
DEFAULT_STATE = Path(__file__).resolve().parent / "modsafe_alerts_state.json"
MAX_EMBEDS = 10  # Discord's limit per message

COLORS = {
    "safe": 0x2ECC71, "likely-safe": 0x7BD88F, "not-affected": 0x5DADE2, "manual": 0x95A5A6,
    "no-data": 0x7F8C8D, "wait": 0xF1C40F, "not-ported": 0xE67E22, "broken": 0xE74C3C,
}
EMOJI = {
    "safe": "\U0001F7E2", "likely-safe": "\U0001F7E2", "not-affected": "\U0001F535", "manual": "⚪",
    "no-data": "⚪", "wait": "\U0001F7E1", "not-ported": "\U0001F7E0", "broken": "\U0001F534",
}


# ---------- feed ----------

def fetch_feed(url: str = FEED_URL, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        feed = json.load(r)
    if not isinstance(feed.get("games"), list):
        raise ValueError("feed has no games list")
    return feed


def snapshot(feed: dict, only: set[str] | None = None) -> dict[str, dict]:
    """{game id: the fields we compare and show} for every game in the feed (optionally filtered)."""
    out = {}
    for g in feed["games"]:
        gid = g.get("id")
        if not gid or not g.get("verdict") or (only and gid not in only):
            continue
        # Retired combined entries (e.g. "gta-v", replaced by its Legacy and Enhanced editions) mirror an edition's
        # verdict, so following them would post the same news twice. Still followed if asked for by id.
        if g.get("deprecated") and not (only and gid in only):
            continue
        patch = g.get("current_patch") or {}
        out[gid] = {
            "name": g.get("name") or gid,
            "verdict": g["verdict"],
            "verdict_label": g.get("verdict_label") or g["verdict"],
            "severity": g.get("severity"),
            "patch": patch.get("label"),
            "patch_published_at": patch.get("published_at"),
            "page_url": g.get("page_url") or f"https://modsafe.app/{gid}/",
            "updated_at": g.get("updated_at"),
            "holding_back": holding_back(g),
        }
    return out


def holding_back(game: dict, limit: int = 5) -> list[str]:
    """Names of the mods that set a not-yet-safe verdict (the ones with the game's own verdict), e.g. the mod
    with reported breakage. Empty when the verdict is safe-ish, since then there's nothing to point at."""
    if (game.get("severity") or 0) >= 5:  # likely-safe and better
        return []
    names = []
    for m in game.get("mods") or []:
        if m.get("counts_toward_verdict") and m.get("verdict") == game.get("verdict"):
            names.append(f"{m.get('name') or m.get('id')} ({m['release']})" if m.get("release") else (m.get("name") or m.get("id")))
    return names[:limit] + ([f"+{len(names) - limit} more"] if len(names) > limit else [])


# ---------- change detection ----------

def find_changes(old: dict[str, dict], new: dict[str, dict]) -> list[dict]:
    """Games whose verdict differs from the last one seen. Games seen for the first time are not reported."""
    changes = []
    for gid, cur in new.items():
        prev = old.get(gid)
        if prev and prev.get("verdict") != cur["verdict"]:
            changes.append({"id": gid, "old": prev, "new": cur})
    return changes


def direction(old: dict, new: dict) -> str:
    a, b = old.get("severity"), new.get("severity")
    if isinstance(a, int) and isinstance(b, int) and a != b:
        return "better" if b > a else "worse"
    return "changed"


def build_embed(change: dict, disclaimer: str | None = None) -> dict:
    old, new = change["old"], change["new"]
    trend = {"better": "⬆️ Better", "worse": "⬇️ Worse"}.get(direction(old, new), "Changed")
    patch = new.get("patch") or "unknown"
    if new.get("patch_published_at"):
        patch += f" ({new['patch_published_at'][:10]})"
    embed = {
        "title": f"{new['name']}: {EMOJI.get(new['verdict'], '')} {new['verdict_label']}".replace("  ", " "),
        "url": new["page_url"],
        "description": (f"Mod verdict changed from **{old.get('verdict_label') or old.get('verdict')}** "
                        f"to **{new['verdict_label']}**.\n[See mod status on ModSafe]({new['page_url']})"),
        "color": COLORS.get(new["verdict"], 0x95A5A6),
        "fields": [{"name": "Game patch", "value": patch, "inline": True},
                   {"name": "Trend", "value": trend, "inline": True}],
        "footer": {"text": (disclaimer or "ModSafe verdicts are inferred from public release data, not guarantees.")[:2048]},
    }
    if new.get("holding_back"):
        name = {"broken": "Breakage reported in", "wait": "Waiting on", "not-ported": "Not ported yet"}.get(new["verdict"], "Mods to check")
        embed["fields"].append({"name": name, "value": "\n".join(f"• {n}" for n in new["holding_back"])[:1024], "inline": False})
    if new.get("updated_at"):
        embed["timestamp"] = new["updated_at"]
    return embed


def build_messages(changes: list[dict], disclaimer: str | None = None) -> list[dict]:
    embeds = [build_embed(c, disclaimer) for c in changes]
    return [{"username": "ModSafe", "allowed_mentions": {"parse": []}, "embeds": embeds[i:i + MAX_EMBEDS]}
            for i in range(0, len(embeds), MAX_EMBEDS)]


# ---------- Discord ----------

def check_webhook(url: str | None) -> str:
    if not url:
        raise SystemExit("No webhook URL. Set MODSAFE_DISCORD_WEBHOOK or pass --webhook (or use --dry-run).")
    if not url.startswith(WEBHOOK_PREFIXES):
        raise SystemExit("That doesn't look like a Discord webhook URL (it should start with https://discord.com/api/webhooks/).")
    return url


def post(webhook: str, payload: dict, tries: int = 3) -> None:
    body = json.dumps(payload).encode()
    for attempt in range(tries):
        req = urllib.request.Request(webhook, data=body, method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30):
                return
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:  # rate limited: wait as told, then retry
                try:
                    wait = float(json.load(e).get("retry_after", 2))
                except Exception:
                    wait = 2.0
                time.sleep(min(wait, 60))
                continue
            # Never echo the webhook URL: it is a secret.
            raise RuntimeError(f"Discord rejected the message (HTTP {e.code}). Check the webhook still exists.") from None


# ---------- state ----------

def load_state(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("games", {})
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        print(f"warning: couldn't read {path}; starting fresh", file=sys.stderr)
        return None


def save_state(path: Path, games: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps({"games": games}, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


# ---------- run ----------

def run_once(args, feed: dict | None = None) -> int:
    only = {s.strip() for s in (args.games or "").split(",") if s.strip()} or None
    try:
        feed = feed or fetch_feed(args.feed)
    except Exception as e:  # the next run will try again
        print(f"couldn't read the ModSafe feed: {e}", file=sys.stderr)
        return 1
    if only:
        unknown = only - {g.get("id") for g in feed["games"]}
        if unknown:
            print(f"warning: unknown game id(s): {', '.join(sorted(unknown))} (see --list-games)", file=sys.stderr)
    new = snapshot(feed, only)
    old = load_state(args.state)

    if old is None and not args.announce_current:
        if not args.dry_run:
            save_state(args.state, new)
        print(f"First run: recorded {len(new)} games' current verdicts. Alerts start from the next change.")
        return 0
    if old is None:  # --announce-current: report every game as a change from "first seen"
        changes = [{"id": k, "old": {"verdict": None, "verdict_label": "not tracked yet"}, "new": v} for k, v in new.items()]
    else:
        changes = find_changes(old, new)

    if not changes:
        print("No verdict changes.")
        if not args.dry_run:
            save_state(args.state, {**(old or {}), **new})
        return 0

    for c in changes:
        print(f"{c['new']['name']}: {c['old'].get('verdict_label')} -> {c['new']['verdict_label']}")
    messages = build_messages(changes, feed.get("disclaimer"))
    if args.dry_run:
        print(json.dumps(messages, indent=2, ensure_ascii=False))
        return 0
    webhook = check_webhook(args.webhook)
    try:
        for m in messages:
            post(webhook, m)
    except Exception as e:
        print(f"error: {e} The verdicts weren't saved, so the next run will try again.", file=sys.stderr)
        return 1
    save_state(args.state, {**(old or {}), **new})
    print(f"Posted {len(changes)} change(s).")
    return 0


def send_test(args) -> int:
    webhook = check_webhook(args.webhook)
    sample = {"id": "example", "old": {"verdict": "wait", "verdict_label": "Just patched, wait", "severity": 2},
              "new": {"name": "Example Game (test message)", "verdict": "likely-safe", "verdict_label": "Likely safe",
                      "severity": 5, "patch": "Patch 1.2.3", "patch_published_at": None, "page_url": "https://modsafe.app/"}}
    msg = build_messages([sample])[0]
    msg["content"] = "ModSafe alerts are set up. This is a test message."
    post(webhook, msg)
    print("Test message sent.")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252, which can't print the emoji
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(description="Post ModSafe verdict changes to a Discord channel webhook.")
    p.add_argument("--webhook", default=os.environ.get("MODSAFE_DISCORD_WEBHOOK"))
    p.add_argument("--games", default=os.environ.get("MODSAFE_GAMES"))
    p.add_argument("--state", type=Path, default=Path(os.environ.get("MODSAFE_STATE_FILE") or DEFAULT_STATE))
    p.add_argument("--feed", default=FEED_URL, help=argparse.SUPPRESS)
    p.add_argument("--loop", type=float, metavar="MINUTES", help="keep running, checking every MINUTES (minimum 15)")
    p.add_argument("--dry-run", action="store_true", help="print what would be posted, don't contact Discord")
    p.add_argument("--announce-current", action="store_true", help="on the first run, post every game's current verdict")
    p.add_argument("--test", action="store_true", help="post a sample message to check the webhook")
    p.add_argument("--list-games", action="store_true", help="print game ids and current verdicts")
    args = p.parse_args(argv)

    if args.list_games:
        for gid, g in snapshot(fetch_feed(args.feed)).items():
            print(f"{gid:28} {g['verdict_label']:28} {g['name']}")
        return 0
    if args.test:
        return send_test(args)
    if not args.loop:
        return run_once(args)
    minutes = max(args.loop, 15.0)  # the feed changes at most every ~30 minutes; be polite
    while True:
        run_once(args)
        time.sleep(minutes * 60)


if __name__ == "__main__":
    sys.exit(main())
