#!/usr/bin/env python3
"""One-time backfill of data/games/<slug>.json "verdict_log" from the git history of the committed data.

Replays every committed version of each game file (oldest first, optionally since --since) through
feeds.append_verdict_log, then appends the current file. Safe to re-run: it rebuilds the log from scratch.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import feeds  # noqa: E402
from games import GAMES  # noqa: E402


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=None, help="only replay commits after this date (git --since syntax)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    for g in GAMES:
        rel = f"data/games/{g['slug']}.json"
        args = ["log", "--reverse", "--format=%H", "--", rel]
        if a.since:
            args.insert(1, f"--since={a.since}")
        log: list = []
        for sha in git(*args).split():
            try:
                payload = json.loads(git("show", f"{sha}:{rel}"))
            except (subprocess.CalledProcessError, ValueError):
                continue
            log = feeds.append_verdict_log(log, payload)
        path = ROOT / rel
        cur = json.loads(path.read_text(encoding="utf-8"))
        log = feeds.append_verdict_log(log, cur)
        print(f"{g['slug']}: {len(log)} events")
        for e in log:
            print(f"   {e['at']}  {e['patch']}  {e['verdict']}  " + ", ".join(f"{f['short']}={f['status']}" for f in e["frameworks"]))
        if not a.dry_run:
            cur["verdict_log"] = log
            path.write_text(json.dumps(cur, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
