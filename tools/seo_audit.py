#!/usr/bin/env python3
"""Thin/duplicate-content audit of every HTML URL in dist/sitemap.xml (stdlib only).

Per page: main-content word count (inside <main>, minus scripts), words unique to the page vs its sibling
group (same path template, e.g. all /<slug>/history/), max 5-word-shingle Jaccard similarity to a sibling,
title/description duplicates, H1, internal links out/in, JSON-LD types, robots meta.

    python3 tools/seo_audit.py [--dist dist] [--csv out.csv] [--top 40]
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SITE = "https://modsafe.app"


def page_file(dist: Path, url: str) -> Path | None:
    p = url.replace(SITE, "") or "/"
    if not p.endswith("/"):
        return None
    return dist / p.lstrip("/") / "index.html"


def main_text(doc: str) -> str:
    m = re.search(r"<main[^>]*>(.*)</main>", doc, re.S)
    s = m.group(1) if m else doc
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S)
    s = re.sub(r'<input[^>]*value="([^"]*)"[^>]*>', " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def words(t: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9.'’+-]*", t.lower())


def shingles(ws: list[str], n: int = 5) -> set:
    return {tuple(ws[i:i + n]) for i in range(max(0, len(ws) - n + 1))}


def group_of(path: str) -> str:
    parts = [p for p in path.strip("/").split("/") if p]
    if len(parts) == 2 and parts[0] != "guides":
        return f"/<slug>/{parts[1]}/"
    if len(parts) == 1 and parts[0] not in ("games", "news", "faq", "guides"):
        return "/<slug>/"
    return path


def audit(dist: Path) -> list[dict]:
    urls = re.findall(r"<loc>([^<]+)</loc>", (dist / "sitemap.xml").read_text())
    pages = {}
    for u in urls:
        f = page_file(dist, u)
        if not f or not f.exists():
            continue
        doc = f.read_text(encoding="utf-8")
        path = u.replace(SITE, "") or "/"
        t = main_text(doc)
        ws = words(t)
        links = set()
        for h in re.findall(r'<a [^>]*href="([^"#]*)', re.search(r"<main[^>]*>(.*)</main>", doc, re.S).group(1)):
            h = h.replace(SITE, "")
            if h.startswith("/") and not h.startswith("//"):
                links.add(h if h.endswith("/") or "." in h.rsplit("/", 1)[-1] else h + "/")
        ld = []
        for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
            try:
                j = json.loads(blk)
            except ValueError:
                continue
            for o in (j if isinstance(j, list) else j.get("@graph", [j])):
                ld.append(o.get("@type"))
        pages[path] = {
            "path": path, "group": group_of(path), "words": len(ws), "ws": ws, "sh": shingles(ws),
            "title": html.unescape((re.search(r"<title>(.*?)</title>", doc, re.S) or [None, ""])[1]),
            "desc": html.unescape((re.search(r'<meta name="description" content="([^"]*)"', doc) or [None, ""])[1]),
            "h1": html.unescape(re.sub(r"<[^>]+>", "", (re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S) or [None, ""])[1])).strip(),
            "noindex": bool(re.search(r'<meta name="robots" content="[^"]*noindex', doc)),
            "links_out": links, "ld": sorted({str(x) for x in ld}),
        }
    inbound = Counter()
    for p in pages.values():
        for l in p["links_out"]:
            if l in pages and l != p["path"]:
                inbound[l] += 1
    titles = Counter(p["title"] for p in pages.values())
    descs = Counter(p["desc"] for p in pages.values())
    groups = defaultdict(list)
    for p in pages.values():
        groups[p["group"]].append(p)
    rows = []
    for p in pages.values():
        sibs = [s for s in groups[p["group"]] if s is not p]
        sim, sib = 0.0, ""
        for s in sibs:
            u = len(p["sh"] | s["sh"]) or 1
            j = len(p["sh"] & s["sh"]) / u
            if j > sim:
                sim, sib = j, s["path"]
        other = Counter()
        for s in sibs:
            other.update(set(s["ws"]))
        uniq = sum(1 for w in p["ws"] if other[w] == 0) if sibs else len(p["ws"])
        # Distinct words: tokens in this page that appear on fewer than half of its siblings.
        distinct = sum(1 for w in p["ws"] if other[w] < max(1, len(sibs) / 2)) if sibs else len(p["ws"])
        rows.append({
            "path": p["path"], "group": p["group"], "words": p["words"], "distinct_words": distinct, "unique_words": uniq,
            "max_sibling_sim": round(sim, 3), "most_similar": sib, "title_dup": titles[p["title"]] > 1,
            "desc_dup": descs[p["desc"]] > 1, "title_len": len(p["title"]), "desc_len": len(p["desc"]),
            "h1": p["h1"], "links_out": len([l for l in p["links_out"] if l in pages]), "links_in": inbound[p["path"]],
            "jsonld": "+".join(p["ld"]), "noindex": p["noindex"], "title": p["title"], "desc": p["desc"],
        })
    for r in rows:  # crude weakness score: thin + templated + poorly linked
        r["score"] = round(min(r["distinct_words"], 600) / 600 + (1 - r["max_sibling_sim"]) + min(r["links_in"], 10) / 20
                           - 0.3 * r["title_dup"] - 0.3 * r["desc_dup"], 3)
    return sorted(rows, key=lambda r: r["score"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default=str(Path(__file__).resolve().parent.parent / "dist"))
    ap.add_argument("--csv")
    ap.add_argument("--top", type=int, default=100)
    a = ap.parse_args()
    rows = audit(Path(a.dist))
    if a.csv:
        with open(a.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"{'path':34} {'words':>5} {'dist':>5} {'uniq':>4} {'sim':>5} {'in':>3} {'out':>3} dupT dupD  jsonld")
    for r in rows[:a.top]:
        print(f"{r['path']:34} {r['words']:5} {r['distinct_words']:5} {r['unique_words']:4} {r['max_sibling_sim']:5} "
              f"{r['links_in']:3} {r['links_out']:3} {'Y' if r['title_dup'] else '.':4} {'Y' if r['desc_dup'] else '.':4} {r['jsonld']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
