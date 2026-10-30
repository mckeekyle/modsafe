#!/usr/bin/env python3
"""Static site generator for ModSafe — multi-game mod framework patch status."""

from __future__ import annotations

import html
import json
import re
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "games"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from games import GAMES, COMPAT_GAMES, HUBS, GAMES_BY_SLUG  # noqa: E402
import patches as patches_mod  # noqa: E402
import mods as mods_mod  # noqa: E402
import feeds  # noqa: E402
import badges  # noqa: E402
import guides as guides_mod  # noqa: E402
import history_stats as hstats  # noqa: E402
GAMES_SLUGS = {g["slug"] for g in GAMES}
HUB_SLUGS = set(HUBS)  # e.g. /gta-v/: short hub page linking to the per-edition pages


def distinct_games(games) -> int:
    """Games (not platforms), counting editions that share a hub (GTA V Legacy + Enhanced) once."""
    return len({g.get("hub") or g["slug"] for g in games if g.get("genre") != "Platform"})


def edition_label(game: dict) -> str:
    return (game.get("edition") or "").title()


def other_editions(game: dict) -> list[dict]:
    return [GAMES_BY_SLUG[s] for s in HUBS.get(game.get("hub"), []) if s != game["slug"]]
NEWS_FILE = ROOT / "data" / "news.json"
DIST = ROOT / "dist"
STATIC = ROOT / "static"

# Cloudflare Web Analytics (cookie-free). Optional: only needed for a manually created
# Web Analytics site. If Analytics is enabled on the Pages project itself, Cloudflare
# injects the beacon automatically and this stays empty. The token is public (it ships in HTML).
CF_ANALYTICS_TOKEN = os.environ.get("CF_ANALYTICS_TOKEN", "").strip()
SITE_URL = os.environ.get("SITE_URL", "https://modsafe.app").rstrip("/")
SITE_NAME = "ModSafe — Mod Compatibility After Game Patches"
SITE_DESC = (
    "Is it safe to update? Live status of core mod frameworks and loaders (script extenders, BepInEx, SMAPI, "
    "tModLoader, Fabric/Forge and more) after each official patch, for " + str(distinct_games(GAMES)) + " heavily modded PC games plus Steam Deck."
)


def esc(s: object) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def fmt_date(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        raw = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return iso[:10]


STATUS_CLASSES = {
    "Safe": "ok", "Likely safe": "likely", "Just patched, wait": "wait", "Breakage reported": "broken",
    "Not ported yet": "broken", "Not ported": "broken", "No data": "unknown", "No post-patch release": "unknown",
    "Not affected by patches": "agnostic", "Check manually": "manual",
}


def status_class(status: str) -> str:
    return STATUS_CLASSES.get(status, "unknown")


def base_head(title: str, description: str, path: str, extra_jsonld: list | None = None, og: str | None = None,
              noindex: bool = False) -> str:
    canon = f"{SITE_URL}{path}"
    seg = path.strip("/").split("/")[0]
    alt_json = f"{SITE_URL}/{seg}/status.json" if any(g["slug"] == seg for g in GAMES + COMPAT_GAMES) else f"{SITE_URL}/games.json"
    og_name = f"{seg}.png" if (STATIC / "og" / f"{seg}.png").exists() and (seg in GAMES_SLUGS or seg in HUB_SLUGS) else "default.png"
    if og and (STATIC / "og" / og).exists():
        og_name = og
    og_image = f"{SITE_URL}/og/{og_name}"
    jsonld = [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": SITE_NAME,
            "url": SITE_URL,
            "description": SITE_DESC,
        },
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "url": canon,
            "description": description,
            "isPartOf": {"@type": "WebSite", "url": SITE_URL},
        },
    ]
    if extra_jsonld:
        jsonld.extend(extra_jsonld)
    feed_links = f'<link rel="alternate" type="application/atom+xml" title="ModSafe: all games" href="{esc(SITE_URL)}/feed.xml">'
    gname = next((g["name"] for g in GAMES if g["slug"] == seg), None)
    if gname:
        feed_links = (f'<link rel="alternate" type="application/atom+xml" title="ModSafe: {esc(gname)}" '
                      f'href="{esc(SITE_URL)}/{esc(seg)}/feed.xml">\n' + feed_links)
    blocks = "\n".join(
        f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>'
        for b in jsonld
    )
    canon_link = f'<link rel="canonical" href="{esc(canon)}">\n'
    robots = "index,follow"
    if noindex:
        # Error pages: no canonical, no structured data, never indexed.
        canon_link, blocks, robots = "", "", "noindex,follow"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
{canon_link}<link rel="alternate" type="application/json" href="{esc(alt_json)}">
<link rel="alternate" type="text/plain" title="llms.txt" href="{esc(SITE_URL)}/llms.txt">
{feed_links}
<meta name="robots" content="{robots}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE_NAME)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canon)}">
<meta property="og:image" content="{esc(og_image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(title)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{esc(og_image)}">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="theme-color" content="#07090f">
<link rel="preload" href="/fonts/chakra-petch-latin-700-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/styles.css?v={CSS_VER}">
{blocks}
</head>
"""


CSS = """
@font-face { font-family: "Chakra Petch"; font-weight: 600; font-display: swap; src: url(/fonts/chakra-petch-latin-600-normal.woff2) format("woff2"); }
@font-face { font-family: "Chakra Petch"; font-weight: 700; font-display: swap; src: url(/fonts/chakra-petch-latin-700-normal.woff2) format("woff2"); }
@font-face { font-family: "Inter"; font-weight: 400; font-display: swap; src: url(/fonts/inter-latin-400-normal.woff2) format("woff2"); }
@font-face { font-family: "Inter"; font-weight: 600 800; font-display: swap; src: url(/fonts/inter-latin-600-normal.woff2) format("woff2"); }
:root {
  --bg: #07090f; --bg2: #0c111c; --panel: #111827; --panel2: #161f33; --line: #22304a;
  --text: #eef3ff; --muted: #a3b1c9; --dim: #7d8aa3;
  --neon: #00f0ff; --neon2: #ff2a6d; --lime: #b6ff3b;
  --ok: #22e07a; --likely: #ffd23f; --wait: #ff9f1c; --broken: #ff4d5e; --agn: #7aa2ff; --manual: #9aa5b8;
  --focus: #ffe66d; --r: 14px;
  --head: "Chakra Petch", "Inter", system-ui, sans-serif;
  --font: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --mono: ui-monospace, "Cascadia Code", "SF Mono", Menlo, Consolas, monospace;
}
*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; font-family: var(--font); color: var(--text); line-height: 1.6; min-height: 100vh;
  background:
    radial-gradient(900px 500px at 85% -10%, rgba(255,42,109,.16), transparent 60%),
    radial-gradient(900px 600px at 0% 0%, rgba(0,240,255,.12), transparent 60%),
    linear-gradient(180deg, var(--bg2), var(--bg) 40%);
  background-attachment: fixed; }
body::before { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: -1; opacity: .35;
  background-image: linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.03) 1px, transparent 1px);
  background-size: 48px 48px; }
h1, h2, h3, .brand, .btn, .eyebrow, .vbadge { font-family: var(--head); letter-spacing: .01em; }
h1 { font-weight: 700; line-height: 1.05; }
h2 { font-size: 1.45rem; margin: 0 0 .75rem; }
a { color: var(--neon); text-underline-offset: 3px; }
a:hover { color: #7ff8ff; }
a:focus-visible, button:focus-visible, summary:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; border-radius: 6px; }
code { font-family: var(--mono); font-size: .88em; color: #cfe3ff; }
.skip { position: absolute; left: -9999px; }
.skip:focus { left: 1rem; top: 1rem; z-index: 100; background: var(--focus); color: #000; padding: .5rem 1rem; }
.muted, .disclaimer { color: var(--muted); }
.disclaimer { font-size: .9rem; }

/* header */
.header { position: sticky; top: 0; z-index: 20; backdrop-filter: blur(12px); background: rgba(7,9,15,.78);
  border-bottom: 1px solid rgba(0,240,255,.18); box-shadow: 0 1px 0 rgba(255,42,109,.12); }
.header-in { max-width: 1200px; margin: 0 auto; padding: .7rem 1.25rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.brand a { display: inline-flex; align-items: center; gap: .6rem; color: var(--text); text-decoration: none; font-weight: 700; font-size: 1.3rem; }
.brand b { color: var(--neon); text-shadow: 0 0 18px rgba(0,240,255,.55); }
.logo { border-radius: 9px; filter: drop-shadow(0 0 8px rgba(0,240,255,.45)); }
.nav { display: flex; gap: .3rem; flex-wrap: wrap; }
.nav a { color: var(--muted); text-decoration: none; font-weight: 600; padding: .45rem .8rem; border-radius: 999px; transition: .15s; }
.nav a:hover { color: var(--text); background: rgba(255,255,255,.06); }
.nav a[aria-current="page"] { color: #031018; background: var(--neon); box-shadow: 0 0 18px rgba(0,240,255,.45); }

main { max-width: 1200px; margin: 0 auto; padding: 1.5rem 1.25rem 3rem; }
section { margin: 0 0 1.75rem; }

/* buttons */
.btn { display: inline-flex; align-items: center; gap: .45rem; padding: .8rem 1.3rem; border-radius: 12px; font-weight: 700; font-size: 1.05rem;
  text-decoration: none; color: #031018; background: linear-gradient(135deg, var(--neon), #59ffb4); box-shadow: 0 0 0 1px rgba(255,255,255,.1) inset, 0 8px 28px rgba(0,240,255,.28);
  transition: transform .15s, box-shadow .15s; }
.btn:hover { color: #031018; transform: translateY(-2px); box-shadow: 0 12px 36px rgba(0,240,255,.4); }
.btn.ghost { background: transparent; color: var(--text); border: 1px solid rgba(255,42,109,.6); box-shadow: none; }
.btn.ghost:hover { background: rgba(255,42,109,.14); color: var(--text); }

/* status badges */
.badge { display: inline-flex; align-items: center; gap: .35rem; padding: .22rem .65rem; border-radius: 999px; font-size: .8rem; font-weight: 700;
  border: 1px solid currentColor; background: rgba(255,255,255,.04); white-space: nowrap; }
.badge .ico { font-size: .95em; line-height: 1; }
.badge.ok { color: var(--ok); background: rgba(34,224,122,.1); }
.badge.likely { color: var(--likely); background: rgba(255,210,63,.1); }
.badge.wait { color: var(--wait); background: rgba(255,159,28,.12); }
.badge.broken { color: var(--broken); background: rgba(255,77,94,.12); }
.badge.agnostic { color: var(--agn); background: rgba(122,162,255,.1); }
.badge.manual, .badge.unknown { color: var(--manual); background: rgba(154,165,184,.08); }
.vbadge { display: inline-flex; align-items: center; gap: .6rem; padding: .55rem 1.1rem; border-radius: 14px; font-weight: 700; font-size: 1.35rem;
  border: 2px solid currentColor; background: rgba(0,0,0,.45); backdrop-filter: blur(6px); }
.vbadge .ico { font-size: 1.3em; }
.vbadge.ok { color: var(--ok); box-shadow: 0 0 28px rgba(34,224,122,.35); }
.vbadge.likely { color: var(--likely); box-shadow: 0 0 28px rgba(255,210,63,.3); }
.vbadge.wait { color: var(--wait); box-shadow: 0 0 28px rgba(255,159,28,.35); }
.vbadge.broken { color: var(--broken); box-shadow: 0 0 28px rgba(255,77,94,.4); }
.vbadge.unknown { color: var(--manual); }

/* home hero */
.home-hero { position: relative; overflow: hidden; border-radius: 22px; padding: clamp(1.5rem, 4vw, 3.25rem); margin-top: .5rem;
  border: 1px solid rgba(0,240,255,.25); background: linear-gradient(120deg, rgba(7,9,15,.96) 0%, rgba(7,9,15,.82) 45%, rgba(7,9,15,.35) 100%), var(--hero) center / cover;
  box-shadow: 0 30px 80px rgba(0,0,0,.55), inset 0 0 0 1px rgba(255,255,255,.03); }
.home-hero::after { content: ""; position: absolute; inset: auto 0 0 0; height: 3px; background: linear-gradient(90deg, var(--neon), var(--neon2), var(--lime)); }
.home-hero h1 { font-size: clamp(2.2rem, 6vw, 4rem); margin: .4rem 0 .9rem; max-width: 14ch; text-transform: uppercase; }
.home-hero h1 em { font-style: normal; color: var(--neon); text-shadow: 0 0 28px rgba(0,240,255,.55); }
.home-hero .lede { font-size: 1.12rem; color: #cdd7ea; max-width: 56ch; }
.eyebrow { display: inline-block; margin: 0; color: var(--neon2); text-transform: uppercase; letter-spacing: .18em; font-size: .8rem; font-weight: 700;
  padding: .25rem .6rem; border: 1px solid rgba(255,42,109,.5); border-radius: 6px; background: rgba(255,42,109,.08); }
.legend { display: flex; flex-wrap: wrap; gap: .45rem; margin: 1rem 0 1.4rem; }
.hero-actions { display: flex; flex-wrap: wrap; gap: .7rem; }
.nf-hero .hero-actions { margin-top: var(--s5); }
.stats { display: flex; flex-wrap: wrap; gap: 1.5rem; margin-top: 1.6rem; color: var(--muted); font-size: .92rem; }
.stats strong { display: block; font-family: var(--head); font-size: 1.6rem; color: var(--text); line-height: 1.1; }

/* section headings */
.sec-head { display: flex; align-items: end; justify-content: space-between; gap: 1rem; margin: 2.2rem 0 1rem; }
.sec-head h2 { font-size: clamp(1.4rem, 3vw, 1.9rem); margin: 0; text-transform: uppercase; }
.sec-head > a { white-space: nowrap; }
.sec-head h2::before { content: ""; display: inline-block; width: 10px; height: 1.1em; margin-right: .6rem; vertical-align: -3px; border-radius: 3px;
  background: linear-gradient(var(--neon), var(--neon2)); box-shadow: 0 0 14px rgba(0,240,255,.6); }

/* game cards */
.game-grid { display: grid; gap: 1.1rem; grid-template-columns: repeat(auto-fill, minmax(min(100%, 330px), 1fr)); }
.game-card { position: relative; border-radius: var(--r); overflow: hidden; background: var(--panel); border: 1px solid var(--line);
  transition: transform .2s ease, box-shadow .2s ease, border-color .2s; isolation: isolate; }
.game-card:hover, .game-card:focus-within { transform: translateY(-4px); border-color: var(--glow, var(--neon)); box-shadow: 0 18px 50px rgba(0,0,0,.55), 0 0 0 1px var(--glow, var(--neon)), 0 0 34px -6px var(--glow, var(--neon)); }
.game-card.v-ok { --glow: var(--ok); } .game-card.v-likely { --glow: var(--likely); } .game-card.v-wait { --glow: var(--wait); } .game-card.v-broken { --glow: var(--broken); }
.card-art { position: relative; aspect-ratio: 616 / 353; overflow: hidden; }
.card-art img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform .35s ease; }
.game-card:hover .card-art img { transform: scale(1.05); }
.card-art::after { content: ""; position: absolute; inset: 0; background: linear-gradient(180deg, transparent 35%, rgba(17,24,39,.6) 70%, var(--panel) 100%); }
.card-art .badge { position: absolute; z-index: 2; left: .8rem; bottom: .7rem; font-size: .85rem; backdrop-filter: blur(6px); background: rgba(7,9,15,.75); }
.card-body { padding: .3rem 1.1rem 1.1rem; }
.card-body h3 { font-size: 1.3rem; margin: 0 0 .25rem; }
.card-body h3 a { color: var(--text); text-decoration: none; }
.card-body p { margin: .2rem 0; font-size: .92rem; }
.card-meta { display: flex; justify-content: space-between; gap: .5rem; color: var(--muted); }
.card-meta strong { color: var(--text); }
.chips { display: flex; flex-wrap: wrap; gap: .3rem; margin-top: .6rem; }
.chip { font-size: .74rem; padding: .12rem .5rem; border-radius: 6px; background: rgba(255,255,255,.05); border: 1px solid var(--line); color: var(--muted); }
.stretched::after { content: ""; position: absolute; inset: 0; z-index: 3; }

/* panels */
.panel, .faq-item, .hist-card { background: linear-gradient(180deg, var(--panel2), var(--panel)); border: 1px solid var(--line);
  border-radius: var(--r); padding: clamp(1.1rem, 2.5vw, 1.6rem); }
  background: radial-gradient(600px 200px at 100% 0%, rgba(255,42,109,.22), transparent 70%), radial-gradient(500px 200px at 0% 100%, rgba(0,240,255,.15), transparent 70%), var(--panel); }

/* game hero */
.crumbs { color: var(--dim); font-size: .88rem; margin: 0 0 .7rem; }
.crumbs a { color: var(--muted); }
.game-hero { position: relative; overflow: hidden; border-radius: 22px; min-height: clamp(300px, 42vw, 440px); display: flex; align-items: flex-end;
  padding: clamp(1.25rem, 4vw, 2.75rem); border: 1px solid rgba(255,255,255,.08);
  background: linear-gradient(0deg, rgba(7,9,15,.97) 8%, rgba(7,9,15,.6) 55%, rgba(7,9,15,.15) 100%), linear-gradient(90deg, rgba(7,9,15,.85), transparent 70%), var(--hero) center 30% / cover;
  box-shadow: 0 30px 80px rgba(0,0,0,.55); }
.game-hero::after { content: ""; position: absolute; inset: auto 0 0 0; height: 3px; background: linear-gradient(90deg, var(--glow, var(--neon)), transparent); }
.game-hero.v-ok { --glow: var(--ok); } .game-hero.v-likely { --glow: var(--likely); } .game-hero.v-wait { --glow: var(--wait); } .game-hero.v-broken { --glow: var(--broken); }
.game-hero h1 { font-size: clamp(1.9rem, 5vw, 3.4rem); margin: 0 0 .9rem; text-transform: uppercase; text-shadow: 0 4px 30px rgba(0,0,0,.6); max-width: 22ch; }
.game-hero .lede { color: #d5def0; max-width: 62ch; margin: .9rem 0 0; }
.micro { font-family: var(--head); font-weight: 600; font-size: 1.1rem; margin-left: .6rem; color: #e9f0ff; }
.plats { display: flex; gap: .4rem; }
.plat { padding: .15rem .55rem; border-radius: 6px; font-size: .78rem; font-weight: 700; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.2); }
.console-mods h3 strong { color: #6ee7a0; }
.upcoming { margin: var(--s4) 0; padding: var(--s4) var(--s5); border-radius: 14px; border: 2px solid #ffb020;
  background: linear-gradient(135deg, rgba(255,176,32,.22), rgba(255,42,109,.14)); color: #fff4dc; box-shadow: 0 0 24px rgba(255,176,32,.18); }
.upcoming p { margin: .35rem 0 0; max-width: 80ch; }
.upcoming .up-title { margin: 0; font-family: var(--head); font-size: 1.25rem; text-transform: uppercase; color: #ffd27a; }
.upcoming .up-src { font-size: .88rem; color: #f3dcb0; }
.upcoming a { color: #ffe2a6; }
.card-upcoming { margin: .3rem 0; padding: .3rem .55rem; border-radius: 8px; border: 1px solid #ffb020; background: rgba(255,176,32,.16);
  color: #ffd27a; font-size: .82rem; font-weight: 700; }
.note { margin: 1rem 0 0; padding: .8rem 1rem; border-radius: 10px; background: rgba(255,77,94,.16); border: 1px solid rgba(255,77,94,.65); color: #ffe3e6; max-width: 70ch; }

/* verdict grid */
.vgrid { display: grid; grid-template-columns: 1.4fr 1fr; gap: 1.1rem; margin-top: 1.25rem; }
.patch-meta { display: grid; grid-template-columns: auto 1fr; gap: .45rem 1rem; margin: 0; font-size: .95rem; }
.patch-meta dt { color: var(--dim); text-transform: uppercase; font-size: .76rem; letter-spacing: .08em; padding-top: .2rem; }
.patch-meta dd { margin: 0; }
.big-say { font-size: 1.12rem; margin: .3rem 0 0; }

/* framework cards */
.fw-grid { display: grid; gap: .8rem; grid-template-columns: repeat(auto-fill, minmax(min(100%, 280px), 1fr)); }
.fw { position: relative; background: var(--panel); border: 1px solid var(--line); border-left: 4px solid var(--c, var(--line)); border-radius: 12px; padding: .9rem 1rem;
  transition: border-color .15s, transform .15s; }
.fw:hover { transform: translateY(-2px); border-color: var(--c, var(--neon)); }
.fw.ok { --c: var(--ok); } .fw.likely { --c: var(--likely); } .fw.wait { --c: var(--wait); } .fw.broken { --c: var(--broken); } .fw.agnostic { --c: var(--agn); } .fw.manual, .fw.unknown { --c: var(--manual); }
.fw h3 { font-size: 1.08rem; margin: 0 0 .45rem; }
.fw h3 a { color: var(--text); text-decoration: none; }
.fw h3 a:hover { color: var(--neon); }
.fw .rel { display: flex; justify-content: space-between; gap: .5rem; margin-top: .55rem; font-size: .86rem; color: var(--muted); }
.fw details { margin-top: .5rem; font-size: .87rem; color: var(--muted); }
.fw summary { cursor: pointer; color: var(--dim); }
.fw ul { padding-left: 1.1rem; }
.links { display: flex; flex-wrap: wrap; gap: .6rem; }
.links a { padding: .5rem .9rem; border: 1px solid var(--line); border-radius: 10px; text-decoration: none; background: var(--panel); }
.links a:hover { border-color: var(--neon); }

/* faq + history */
.faq-list { display: grid; gap: .7rem; }
.faq-item h2, .faq-item h3 { font-size: 1.12rem; margin: 0 0 .4rem; color: #fff; }
.faq-item p { margin: 0; color: #c8d3e8; }
.page-hero { padding: 1.5rem 0 .5rem; }
.page-hero h1 { font-size: clamp(2rem, 5vw, 3.2rem); margin: 0 0 .5rem; text-transform: uppercase; }
.page-hero .lede { color: var(--muted); font-size: 1.1rem; max-width: 60ch; }
.hist-list { display: grid; gap: .8rem; }
.hub-nav a[aria-current="page"] { background: rgba(0,240,255,.14); color: var(--neon); }
.hist-t { color: var(--muted); font-size: .82rem; }
.hist-t.ok { color: var(--neon); }
.hist-stats { margin-top: 0; }
.track-record { color: var(--muted); max-width: var(--measure); }
.panel-h { font-size: 1.1rem; margin: 0 0 .6rem; display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; }
.order-list { margin: 0; padding-left: 1.4rem; display: grid; gap: .35rem; }
.order-list li { line-height: 1.5; }
.hist-card h3 { margin: 0; }
.hist-fw { list-style: none; padding: 0; margin: .7rem 0 0; display: flex; flex-wrap: wrap; gap: .45rem .9rem; }
.hist-fw li { display: flex; gap: .4rem; align-items: center; font-size: .9rem; }

/* footer */
.footer { border-top: 1px solid var(--line); background: rgba(7,9,15,.7); margin-top: 2rem; }
.footer-in { max-width: 1200px; margin: 0 auto; padding: 1.75rem 1.25rem 2.5rem; display: grid; grid-template-columns: 1.3fr 1fr; gap: 1.5rem; color: var(--dim); font-size: .86rem; }
.footer .brand a { font-size: 1.1rem; }
.footer nav { display: flex; flex-wrap: wrap; gap: .35rem 1rem; justify-content: flex-end; align-content: start; }
.footer nav a { color: var(--muted); text-decoration: none; }
.footer nav a:hover { color: var(--neon); }
.footer .dev { width: 100%; text-align: right; }

.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.games-menu { position: relative; }
.games-menu summary { list-style: none; cursor: pointer; color: var(--muted); font-weight: 600; padding: .45rem .8rem; border-radius: 999px; }
.games-menu summary::-webkit-details-marker { display: none; }
.games-menu summary::after { content: " ▾"; }
.games-menu[open] summary, .games-menu summary:hover, .games-menu summary[aria-current] { color: var(--text); background: rgba(255,255,255,.07); }
.menu-pop { position: absolute; right: 0; top: calc(100% + .4rem); z-index: 30; width: min(92vw, 520px); display: grid; grid-template-columns: 1fr 1fr; gap: .15rem;
  padding: .6rem; border-radius: 14px; background: #0d1422; border: 1px solid rgba(0,240,255,.3); box-shadow: 0 20px 60px rgba(0,0,0,.6); }
.menu-pop a { padding: .45rem .6rem; border-radius: 8px; color: var(--text); text-decoration: none; font-size: .92rem; }
.menu-pop a:hover, .menu-pop a[aria-current] { background: rgba(0,240,255,.12); color: var(--neon); }
.menu-pop .all { grid-column: 1 / -1; color: var(--neon); font-weight: 700; border-bottom: 1px solid var(--line); border-radius: 8px 8px 0 0; }
.nav { align-items: center; }
.games-menu:not([open]) .menu-pop { display: none; }
@media (max-width: 640px) { .menu-pop { position: fixed; left: 4vw; right: 4vw; top: 64px; width: auto; max-height: 75vh; overflow-y: auto; } }
.filters { display: flex; flex-wrap: wrap; gap: .6rem; align-items: center; margin: 0 0 1rem; }
.filters input, .filters select { background: var(--panel); color: var(--text); border: 1px solid var(--line); border-radius: 10px; padding: .6rem .8rem; font: inherit; }
.filters input { flex: 1 1 240px; }
.filters input:focus, .filters select:focus { outline: 2px solid var(--neon); outline-offset: 1px; }
.game-card[hidden] { display: none; }
.view { margin: .6rem 0 0 !important; color: var(--neon); font-weight: 700; font-family: var(--head); }
.game-card:hover .view { text-decoration: underline; }
.tabs { position: sticky; top: 58px; z-index: 15; display: flex; gap: .3rem; overflow-x: auto; margin: 1rem 0 0; padding: .45rem; border-radius: 14px;
  background: rgba(13,20,34,.92); backdrop-filter: blur(10px); border: 1px solid var(--line); scrollbar-width: none; }
.tabs a { white-space: nowrap; padding: .45rem .9rem; border-radius: 10px; color: var(--muted); text-decoration: none; font-weight: 600; font-family: var(--head); }
.tabs a:hover { background: rgba(0,240,255,.12); color: var(--neon); }
[id] { scroll-margin-top: 130px; }
.news { list-style: none; margin: 0; padding: 0; display: grid; gap: .1rem; }
.news li { padding: .65rem .5rem; border-bottom: 1px solid var(--line); }
.news li:last-child { border-bottom: 0; }
.news li > a { color: var(--text); font-weight: 600; text-decoration: none; }
.news li > a:hover { color: var(--neon); }
.news li.hl { background: linear-gradient(90deg, rgba(255,159,28,.1), transparent); border-left: 3px solid var(--wait); padding-left: .7rem; border-radius: 6px; }
.nmeta { display: flex; flex-wrap: wrap; gap: .35rem; align-items: center; color: var(--dim); font-size: .82rem; margin-top: .2rem; }
.nmeta .chip { text-decoration: none; }
.pt-list { list-style: none; margin: 0; padding: 0; display: grid; gap: .55rem; }
.pt-row { display: grid; grid-template-columns: 112px 1fr auto; gap: .9rem; align-items: center; padding: .55rem .7rem .55rem .55rem;
  border-radius: 12px; background: rgba(255,255,255,.025); border: 1px solid var(--line); border-left: 3px solid var(--line); }
.pt-row.v-ok { border-left-color: var(--lime); } .pt-row.v-likely { border-left-color: var(--neon); }
.pt-row.v-wait { border-left-color: #ffb020; } .pt-row.v-broken { border-left-color: var(--neon2); }
.pt-row.v-old { opacity: .82; }
.pt-art img { display: block; width: 112px; height: 64px; object-fit: cover; border-radius: 8px; }
.pt-main p { margin: 0; } .pt-main { min-width: 0; }
.pt-game { font-family: var(--head); font-size: 1.02rem; } .pt-game a { color: var(--text); text-decoration: none; }
.pt-game a:hover { color: var(--neon); }
.pt-patch { color: #cdd7ea; font-size: .92rem; overflow-wrap: anywhere; } .pt-time { color: var(--dim); font-size: .82rem; }
.pt-new { font-size: .68rem; font-weight: 700; letter-spacing: .08em; padding: .05rem .4rem; margin-left: .35rem; border-radius: 5px;
  background: rgba(0,240,255,.12); color: var(--neon); border: 1px solid rgba(0,240,255,.4); vertical-align: middle; }
.pt-verdict { display: flex; flex-direction: column; align-items: flex-end; gap: .25rem; text-align: right; }
.pt-note { color: var(--dim); font-size: .74rem; max-width: 18ch; }
.pt-month h3 { margin: 0; font-size: 1.05rem; text-transform: uppercase; letter-spacing: .08em; color: var(--neon2); }
.pt-hold p { margin: .3rem 0; } .pt-hold .chip { display: inline-block; margin: .15rem .2rem .15rem 0; text-decoration: none; color: var(--text); }
.rollback { border-color: rgba(255,176,32,.45); background: linear-gradient(135deg, rgba(255,176,32,.08), rgba(255,42,109,.05)); }
.rollback h2 { margin-top: 0; font-size: 1.2rem; } .rb-links { display: flex; flex-wrap: wrap; gap: .5rem; }
@media (max-width: 560px) {
  .pt-row { grid-template-columns: 72px 1fr; gap: .6rem; }
  .pt-art img { width: 72px; height: 41px; }
  .pt-verdict { grid-column: 1 / -1; flex-direction: row; align-items: center; justify-content: flex-start; text-align: left; gap: .5rem; }
  .pt-note { max-width: none; }
}
@media (max-width: 820px) {
  .vgrid { grid-template-columns: 1fr; }
  .footer-in { grid-template-columns: 1fr; }
  .footer nav, .footer .dev { justify-content: flex-start; text-align: left; }
}
@media (max-width: 560px) {
  .header-in { flex-wrap: wrap; padding: .6rem 1rem; }
  .menu-pop { position: fixed; left: 4vw; right: 4vw; width: auto; top: 96px; grid-template-columns: 1fr 1fr; }
  .tabs { top: 96px; }
  .nav a { padding: .35rem .65rem; font-size: .92rem; }
}
@media (max-width: 430px) {
  .nav { gap: 0; flex-wrap: nowrap; }
  .nav a, .games-menu summary { padding: .32rem .5rem; font-size: .86rem; white-space: nowrap; }
  main { padding: 1rem .85rem 2.5rem; }
  .home-hero, .game-hero { border-radius: 16px; }
  .vbadge { font-size: 1.1rem; }
  .micro { display: block; margin: .5rem 0 0; }
  .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: .75rem; font-size: .8rem; }
  .stats strong { font-size: 1.35rem; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; scroll-behavior: auto !important; } }
/* ===== spacing system & rhythm (v3 QA) ===== */
:root { --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 24px; --s6: 32px; --s7: 48px; --s8: 64px; --measure: 72ch; }
main { padding: var(--s5) var(--s5) var(--s8); }
main > * { margin-top: 0; margin-bottom: 0; }
main > * + * { margin-top: var(--s6); }
main > .sec-head { margin-top: var(--s7); margin-bottom: 0; }
main > .sec-head + * { margin-top: var(--s4); }
main > .sec-head + p.muted { margin-top: var(--s2); }
main > p.muted + .filters { margin-top: var(--s4); }
main > .filters + .game-grid { margin-top: var(--s4); }
main > .crumbs { margin: 0; }
main > .crumbs + * { margin-top: var(--s3); }
main > .tabs { margin-top: var(--s4); }
main > .tabs + * { margin-top: var(--s5); }
main > .disclaimer { margin-top: var(--s4); }
.panel, .faq-item, .hist-card { padding: var(--s5); }
.panel > :first-child, .faq-item > :first-child, .hist-card > :first-child { margin-top: 0; }
.panel > :last-child, .faq-item > :last-child, .hist-card > :last-child { margin-bottom: 0; }
.panel h2 { margin-bottom: var(--s3); }
.game-grid { gap: var(--s5); }
.fw-grid { gap: var(--s4); }
.faq-list, .hist-list { gap: var(--s3); }
.faq-item p, .page-hero .lede, .big-say, .disclaimer { max-width: var(--measure); }
.page-hero { padding: var(--s5) 0 0; }
.page-hero h1 { margin: 0 0 var(--s3); }
.page-hero .lede { margin: 0; }
.home-hero h1 { margin: var(--s4) 0 var(--s4); }
.home-hero .lede { margin: 0; }
.legend { margin: var(--s5) 0; }
.stats { margin-top: var(--s6); }
.game-hero h1 { margin: 0 0 var(--s4); }
.game-hero .lede { margin-top: var(--s4); }
.card-body { padding: var(--s3) var(--s4) var(--s4); }
.card-body h3 { margin: 0 0 var(--s1); }
.card-meta { margin: 0; }
.view { margin-top: var(--s3) !important; }
.patch-meta { gap: var(--s2) var(--s4); }
.patch-meta dt { font-size: .78rem; color: var(--muted); }
.news li { padding: var(--s3) var(--s2); }
.news li.hl { padding-left: var(--s3); }
.legend-dl { display: grid; grid-template-columns: max-content 1fr; gap: var(--s3) var(--s4); margin: 0; align-items: baseline; }
.legend-dl dd { margin: 0; color: #c8d3e8; }
.footer-in { padding: var(--s7) var(--s5) var(--s7); gap: var(--s6); }
.footer p { margin: 0 0 var(--s3); }
.footer nav { gap: var(--s2) var(--s4); }
html, body { overflow-x: hidden; }
.mod-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--s4); }
.mod-card { display: flex; flex-direction: column; gap: var(--s2); padding: var(--s4); border-radius: 14px; background: var(--panel); border: 1px solid var(--line); }
.mod-card p { margin: 0; }
.mod-top { display: flex; gap: var(--s3); align-items: center; }
.mod-top h3 { margin: 0; font-size: 1.05rem; }
.mod-n { flex: none; width: 32px; height: 32px; display: grid; place-items: center; border-radius: 50%; background: rgba(0,240,255,.12); color: var(--neon); font-family: var(--head); font-weight: 700; }
.mod-cat { font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; color: var(--dim); }
.mod-req, .mod-why, .mod-note { font-size: .85rem; color: var(--muted); }
.mod-note { border-left: 3px solid var(--neon); padding-left: var(--s2); }
.mod-foot { margin-top: auto; display: flex; flex-wrap: wrap; gap: var(--s2); align-items: center; justify-content: space-between; padding-top: var(--s2); }
.mod-foot .dl { font-weight: 700; color: var(--neon); text-decoration: none; }
.mod-foot .dl:hover { text-decoration: underline; }
.cta-row { display: flex; flex-wrap: wrap; gap: var(--s2); margin-top: var(--s4); }
.guide { max-width: 78ch; line-height: 1.7; }
.guide h2 { margin-top: var(--s6); } .guide h2:first-child { margin-top: 0; }
.guide li { margin: var(--s2) 0; }
.sec-links { display: flex; gap: var(--s4); }
.updated { margin: var(--s1) 0 0 !important; font-size: .8rem !important; color: var(--dim); }
.toggle { display: inline-flex; align-items: center; gap: var(--s2); padding: var(--s2) var(--s4); border: 1px solid var(--line); border-radius: 999px;
  background: var(--panel); cursor: pointer; font-weight: 600; }
.toggle input { accent-color: var(--neon); width: 18px; height: 18px; }
.footer .all-games { color: var(--neon); font-weight: 700; }
/* follow (RSS/Atom) + embeddable badge */
.follow-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: var(--s4); }
.follow-grid .panel h3 { margin: 0 0 var(--s2); font-family: var(--head); text-transform: uppercase; font-size: 1.05rem; letter-spacing: .03em; }
.follow-grid .panel p { margin: 0 0 var(--s3); color: #c8d3e8; font-size: .92rem; }
.snip { display: flex; gap: var(--s2); align-items: stretch; margin: 0 0 var(--s2); }
.snip label { flex: none; width: 4.6rem; align-self: center; font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; color: var(--dim); }
.snip input { flex: 1; min-width: 0; padding: .45rem .6rem; border-radius: 8px; border: 1px solid var(--line); background: var(--bg2); color: #cfe3ff;
  font-family: var(--mono); font-size: .8rem; }
.snip input:focus { outline: 2px solid var(--neon); outline-offset: 1px; }
.copy { flex: none; padding: .4rem .75rem; border-radius: 8px; border: 1px solid rgba(0,240,255,.5); background: rgba(0,240,255,.08); color: var(--neon);
  font-weight: 700; font-size: .8rem; cursor: pointer; font-family: var(--head); }
.copy:hover { background: rgba(0,240,255,.18); }
.badge-preview { display: block; margin: 0 0 var(--s3); max-width: 100%; height: auto; }
.follow-grid .fine { font-size: .8rem !important; color: var(--dim) !important; margin: var(--s2) 0 0 !important; }
[hidden] { display: none !important; }
@media (max-width: 820px) {
  main { padding: var(--s4) var(--s4) var(--s7); }
  main > * + * { margin-top: var(--s5); }
  main > .sec-head { margin-top: var(--s6); }
  .tabs { position: static; flex-wrap: wrap; overflow: visible; }
  .game-grid { gap: var(--s4); }
}
@media (max-width: 560px) {
  .panel, .faq-item, .hist-card { padding: var(--s4); }
  .legend-dl { grid-template-columns: 1fr; gap: var(--s1); }
  .legend-dl dd { margin-bottom: var(--s3); }
  .home-hero, .game-hero { padding: var(--s5) var(--s4); }
  .footer-in { padding: var(--s6) var(--s4); }
  .filters select { flex: 1 1 45%; }
  .footer nav a.more { display: none; }
}
.guide h3 { margin: var(--s5) 0 var(--s2); font-size: 1.15rem; }
.guide-hero h1 { max-width: 24ch; }
.guide-hero .note { margin-top: var(--s4); }
.table-wrap { overflow-x: auto; margin: var(--s3) 0; }
.ed-ids { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--s3); margin: var(--s3) 0; }
.ed-id { padding: .8rem 1rem; border: 1px solid var(--line); border-radius: 12px; }
.ed-id h3 { margin: 0 0 .4rem; }
.ed-id dl { margin: 0; display: grid; grid-template-columns: max-content 1fr; gap: .25rem .8rem; }
.ed-id dt { color: var(--muted, #9aa7bd); font-size: .85rem; }
.ed-id dd { margin: 0; overflow-wrap: anywhere; }
@media (max-width: 480px) { .ed-id dl { grid-template-columns: 1fr; } .ed-id dd { margin-bottom: .35rem; } }
.guide table { width: 100%; border-collapse: collapse; font-size: .95rem; line-height: 1.5; }
.guide th, .guide td { text-align: left; vertical-align: top; padding: .55rem .7rem; border-bottom: 1px solid var(--line); }
.guide th { font-family: var(--head); color: var(--muted); text-transform: uppercase; font-size: .8rem; letter-spacing: .06em; }
.guide td:first-child { white-space: nowrap; font-weight: 600; }
.guide pre { margin: var(--s3) 0; padding: .8rem 1rem; border-radius: 10px; background: #05070c; border: 1px solid var(--line); overflow-x: auto; white-space: pre; }
.guide code { overflow-wrap: anywhere; }
.guide pre code { overflow-wrap: normal; }
.guide .links { margin: var(--s3) 0; }
.guide .badge-preview { vertical-align: middle; }
.guide-grid { display: grid; gap: var(--s4); grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr)); margin-top: var(--s4); }
.guide-card h2 { font-size: 1.15rem; margin: 0 0 var(--s2); }
.guide-card h2 a { text-decoration: none; }
.guide-card p { margin: 0; color: var(--muted); }
@media (max-width: 560px) { .guide td:first-child { white-space: normal; } }
.ed-switch { margin: var(--s3) 0 0; font-size: .95rem; }
.ed-switch a { color: inherit; text-decoration: underline; text-underline-offset: 2px; font-weight: 600; }
.hub-list { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--s3); }
.hub-list li { line-height: 1.7; }
"""




def games_menu(active: str) -> str:
    items = "".join(f'<a href="/{g["slug"]}/"{" aria-current=page" if g["slug"] == active else ""}>{esc(g["name"])}</a>' for g in GAMES)
    cur = ' aria-current="page"' if active in ("games",) or active in GAMES_SLUGS or active in HUB_SLUGS else ""
    return (f'<details class="games-menu"><summary{cur}>🎮 Games</summary><div class="menu-pop">'
            f'<a class="all" href="/games/">All games →</a>{items}</div></details>')


def nav(active: str) -> str:
    links = [("/patches/", "patches", "Patches"), ("/news/", "news", "News"), ("/guides/", "guides", "Guides"), ("/faq/", "faq", "FAQ")]
    items = [games_menu(active)]
    for href, key, label in links:
        aria = ' aria-current="page"' if key == active else ""
        items.append(f'<a href="{href}"{aria}>{esc(label)}</a>')
    return f'<nav class="nav" aria-label="Primary">{" ".join(items)}</nav>'


def brand() -> str:
    return '<div class="brand"><a href="/"><img src="/img/logo.png" width="34" height="34" alt="" class="logo"><span>Mod<b>Safe</b></span></a></div>'


def footer() -> str:
    game_links = " ".join(f'<a href="/{g["slug"]}/"{" class=more" if i >= 6 else ""}>{esc(g["short"])}</a>' for i, g in enumerate(GAMES))
    game_links += ' <a href="/games/" class="all-games">All games →</a>'
    return f"""<footer class="footer"><div class="footer-in">
<div>{brand()}
<p>Know if your mods survived the patch before you hit update.</p>
<p>Not affiliated with any game developer, publisher, Nexus Mods, Thunderstore, Modrinth or Mojang. Game art © its respective owners. Data from public sources (Steam, api.steamcmd.net, GitHub, Thunderstore, Mojang, Fabric, Forge, NeoForge, Modrinth, the Decky plugin store, silverlock.org, fsuipc.com, the Atlan patcher list) plus hand-checked records (GTA V, console mods, off-Steam hotfixes). Dates are UTC.</p></div>
<div><nav aria-label="Footer">{game_links} <a href="/patches/">Patches</a> <a href="/news/">News</a> <a href="/guides/">Guides</a> <a href="/faq/">FAQ</a></nav>
<p class="dev">For developers &amp; AI: <a href="/games.json">Data (JSON)</a> · <a href="/llms.txt">llms.txt</a> · <a href="/feed.xml">Atom feed</a></p></div>
</div></footer>"""


def sponsor_slot() -> str:
    # Hidden until a real sponsor exists (placeholder text looked unfinished to visitors).
    return ""
    return """<aside class="sponsor" aria-label="Sponsor">
<p class="sponsor-label">Sponsor slot</p>
<p>Your modding tool or host here. <a href="mailto:sponsors@modsafe.app">Contact</a> (placeholder).</p>
</aside>"""


def cf_beacon() -> str:
    if not CF_ANALYTICS_TOKEN:
        return ""
    cfg = json.dumps({"token": CF_ANALYTICS_TOKEN})
    return f"<script defer src=\"https://static.cloudflareinsights.com/beacon.min.js\" data-cf-beacon='{esc(cfg)}'></script>\n"


def page_shell(title, description, path, active, body, extra_jsonld=None, og=None, noindex=False) -> str:
    return (
        base_head(title, description, path, extra_jsonld, og, noindex=noindex)
        + f"""<body>
<a class="skip" href="#main">Skip to content</a>
<header class="header"><div class="header-in">
{brand()}
{nav(active)}
</div></header>
<main id="main">
{body}
</main>
{footer()}
{cf_beacon()}{MENU_JS}{COPY_JS if 'class="copy"' in body else ''}
</body>
</html>
"""
    )


ASSET_REF_RE = re.compile(r"(?:https?://modsafe\.app)?(/(?:img|og)/[A-Za-z0-9._/-]+\.(?:png|jpe?g|webp|svg|gif|ico))")


def missing_asset_refs(dist: Path) -> list[tuple[str, str]]:
    """(reference, file) for every /img/ or /og/ image referenced by a generated page/feed that doesn't exist in dist."""
    out = []
    for f in sorted(dist.rglob("*")):
        if f.suffix not in (".html", ".css", ".xml", ".json", ".txt", ".webmanifest") or not f.is_file():
            continue
        for ref in sorted(set(ASSET_REF_RE.findall(f.read_text(encoding="utf-8", errors="replace")))):
            if not (dist / ref.lstrip("/")).is_file():
                out.append((ref, str(f.relative_to(dist))))
    return out


def asset_ver(rel: str) -> str:
    """Short content hash for cache-busting (/img/* is cached a week, so replaced art needs a new URL)."""
    import hashlib
    return hashlib.sha1((STATIC / rel).read_bytes()).hexdigest()[:8]


def game_img(slug: str, kind: str = "cap") -> str:
    """kind: 'cap' (616x353 card art) or 'hero' (1600x516 banner). Falls back to SVG tile / header.jpg."""
    if (STATIC / "img" / f"{slug}-{kind}.webp").exists():
        return f"/img/{slug}-{kind}.webp"
    if (STATIC / "img" / f"{slug}.svg").exists():
        return f"/img/{slug}.svg"
    return f"/img/{slug}.jpg"


def busted(url: str) -> str:
    """Append ?v=<content hash>: /img/* is cached for a week, so replaced art needs a new URL to show up."""
    f = STATIC / url.lstrip("/")
    return f"{url}?v={asset_ver(url.lstrip('/'))}" if f.is_file() else url


ICONS = {"ok": "✔", "likely": "◑", "wait": "⏳", "broken": "✖", "agnostic": "∞", "manual": "?", "unknown": "?"}
MICROCOPY = {
    "Safe": "GG — update away.",
    "Likely safe": "Looking good. Skim the notes, then go.",
    "Just patched, wait": "Fresh patch. Hold your horses.",
    "Breakage reported": "Ouch. Don't update yet.",
    "Not ported yet": "Mods haven't caught up yet.",
    "No data": "Couldn't reach the data. Check manually.",
}


def icon(status: str) -> str:
    return f'<span class="ico" aria-hidden="true">{ICONS[status_class(status)]}</span>'


def vbadge(status: str) -> str:
    return f'<span class="vbadge {status_class(status)}">{icon(status)}{esc(status)}</span>'


def badge(status: str, tracked: bool = True) -> str:
    if not tracked and status != "Not affected by patches":
        status = "Check manually"
    return f'<span class="badge {status_class(status)}">{icon(status)}{esc(status)}</span>'


def and_join(items: list) -> str:
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1] if items else ""


def verdict_sentence(game: dict, data: dict) -> str:
    v = data["verdict"]
    p = data["game"]["latest_patch"]["label"]
    fws = [f for f in data["frameworks"] if f.get("tracked", True) and f.get("sensitive", True)]
    manual = [f["short"] for f in data["frameworks"] if not f.get("tracked", True) and f["status"] == "Check manually"]
    worst = [f["short"] for f in fws if f["status"] == v]
    tail = f" Also check {and_join(manual)} manually (no public release feed, not counted)." if manual else ""
    if v == "Safe":
        msg = f"Every patch-sensitive framework has explicit support for {p}."
    elif v == "Likely safe":
        msg = (f"No sign of trouble with {p}. {and_join(worst)} {'hasn’t' if len(worst) == 1 else 'haven’t'} named this patch in a release, "
               "but there’s either a newer release or no breakage reports since. Probably fine — skim the notes before updating.")
    elif v == "Just patched, wait" and game.get("kind") == "manual" and data["game"]["latest_patch"].get("unannounced_update"):
        u = data["game"]["latest_patch"]["unannounced_update"]
        msg = (f"Steam shipped a new {str(u.get('edition') or '').title()} build on {u['published_at'][:10]} that isn’t in the "
               f"manual record yet, and {and_join(worst)} support for it is unconfirmed. Hold the update until it’s checked.")
    elif v == "Just patched, wait":
        msg = f"{p} is under a week old and {and_join(worst)} {'has' if len(worst) == 1 else 'have'} not updated yet. Hold the update a few days."
    elif v == "Breakage reported":
        msg = f"Open issues report breakage after {p} for {and_join(worst)}. Hold the update or check the linked reports."
    elif v == "Not ported yet" and game.get("kind") == "manual":
        # Hand-maintained hooks (Script Hook V) can lag on one edition only: say which, from the framework reason.
        why = " ".join(f"{f['name']}: {re.sub(r' [(]Manually verified [^)]*[)][.]?$', '', f.get('reason', ''))}"
                       for f in fws if f["status"] == v)
        msg = f"{why} Stay on your current version if you depend on it."
    elif v == "Not ported yet":
        msg = f"{and_join(worst)} {'has' if len(worst) == 1 else 'have'} no build for {p} yet. Stay on your current version if you depend on them."
    else:
        msg = "Some data could not be fetched; check the project pages."
    crashy = [f["short"] for f in fws if f.get("crash_reports")]
    if crashy:
        msg += (f" Separately, there are open crash reports against recent {and_join(crashy)} builds that aren’t tied to this patch;"
                " see “Why?” below.")
    return msg + tail


def breadcrumb_ld(items: list[tuple[str, str]]) -> dict:
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": f"{SITE_URL}{u}"}
                                for i, (n, u) in enumerate(items)]}


def faq_ld(items: list[dict]) -> dict:
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": i["q"], "acceptedAnswer": {"@type": "Answer", "text": i["a"]}}
                           for i in items]}


STATUS_EXPLAINER = (
    "Safe: a release explicitly supports the current patch (release notes, the maintainer's official page, or a stable "
    "build for that game version). Likely safe: a release is dated after the patch but doesn't name it, or the patch is "
    "over a week old with no breakage reports on the project's issue tracker. Just patched, wait: the patch is under 7 "
    "days old and the framework hasn't updated. Breakage reported: open issues report the framework broke after the "
    "patch. Not ported yet: no build exists for the current game version yet (Minecraft loaders, Script Hook V). Not affected by patches: version-agnostic "
    "tools such as mod managers or generic loaders; they don't count toward the verdict."
)


LEGEND = [
    ("Safe", "A release explicitly supports the current patch (release notes, the maintainer's official page, or a stable build for that version)."),
    ("Likely safe", "Released after the patch without naming it, or the patch is over a week old with no breakage reports."),
    ("Just patched, wait", "The patch is under 7 days old and the framework hasn't updated yet."),
    ("Breakage reported", "Open issues on the project's tracker say it broke after the patch."),
    ("Not ported yet", "No build exists for the current game version yet (Minecraft loaders, Script Hook V)."),
    ("Not affected by patches", "Version-agnostic tools (mod managers, generic loaders). Not counted in the verdict."),
    ("Check manually", "Tools without a public release feed (e.g. Nexus-only). Not counted in the verdict."),
]


def legend_html() -> str:
    return '<dl class="legend-dl">' + "".join(f"<dt>{badge(k)}</dt><dd>{esc(v)}</dd>" for k, v in LEGEND) + "</dl>"


def faq_article(item: dict, tag: str = "h3", idx: int | None = None) -> str:
    body = legend_html() if item["a"] == STATUS_EXPLAINER else f"<p>{esc(item['a'])}</p>"
    ident = f' id="faq-{idx}"' if idx is not None else ""
    return f'<article class="faq-item"{ident}><{tag}>{esc(item["q"])}</{tag}>{body}</article>'


SOURCE_NAMES = {"github": "GitHub releases", "github_tags": "GitHub tags", "thunderstore": "the Thunderstore API",
                "decky_store": "the Decky plugin store API", "fsuipc": "fsuipc.com", "mc_fabric": "Fabric meta",
                "mc_forge": "Forge promotions", "mc_neoforge": "NeoForge maven", "mc_modrinth": "the Modrinth API",
                "manual_shv": "a hand-checked Script Hook V record",
                "ficsit_sml": "the ficsit.app (Satisfactory Mod Repository) API, including its SML compatibility flag",
                "atlan": "the Atlan patcher's supported-build list and the mod loader's GitHub release", "manual": None}


def fw_sources(game: dict) -> str:
    names = []
    for fw in game["frameworks"]:
        n = SOURCE_NAMES.get(fw["source"], fw["source"])
        if n and n not in names:
            names.append(n)
        if fw.get("official_page") and "the official silverlock.org pages" not in names:
            names.append("the official silverlock.org pages")
    return (", ".join(names[:-1]) + " and " + names[-1]) if len(names) > 1 else (names[0] if names else "manual checks")


def game_faq(game: dict, data: dict) -> list[dict]:
    p = data["game"]["latest_patch"]
    by_hand = {f["name"] for f in game["frameworks"] if f.get("source") == "manual_shv"}
    tracked = [f["name"] for f in data["frameworks"] if f.get("tracked") and f["name"] not in by_hand]
    hand = [f["name"] for f in data["frameworks"] if f.get("tracked") and f["name"] in by_hand]
    manual = [f["name"] for f in data["frameworks"] if not f.get("tracked")]
    src = ("the Mojang version manifest" if game.get("kind") == "minecraft"
           else ("a hand-maintained record checked by ModSafe (Rockstar title update notes and the Script Hook V page), "
                 + ("cross-checked against this edition's Steam public build (api.steamcmd.net)" if game.get("edition")
                    else "cross-checked against each edition's Steam public build (api.steamcmd.net)")) if game.get("kind") == "manual"
           else (f"Steam's public build record (Steam PICS via api.steamcmd.net, app {game.get('steam_appid')}), "
                 "because this game's updates often ship without a Steam post") if game.get("kind") == "atlan"
           else f"official Steam announcements (app {game.get('steam_appid')}, stable-channel SteamOS posts)" if game.get("kind_label") == "platform"
           else (f"official Steam announcements (app {game.get('steam_appid')}), checked against Steam's public build "
                 "(api.steamcmd.net); updates announced only off Steam are added by hand with cited sources"))
    items = [
        {"q": f"Is it safe to update {game['name']} with mods?",
         "a": f"Current verdict: {data['verdict']}. {verdict_sentence(game, data)} Latest patch tracked: {p['label']} ({fmt_date(p.get('published_at'))})."},
        {"q": f"Why do {game['name']} mods break after a patch?", "a": game["blurb"]},
        {"q": f"Which {game['name']} frameworks does ModSafe track?",
         "a": (f"Checked by hand: {', '.join(hand)}. " if hand else "") + "Automatically: " + ", ".join(tracked) + "." + (f" Linked for manual checks (no public release API): {', '.join(manual)}." if manual else "")},
        {"q": "What do the status labels mean?", "a": STATUS_EXPLAINER},
        {"q": "Where does the data come from?",
         "a": f"Game patches come from {src}. Framework data comes from {fw_sources(game)}. ModSafe does not scrape Nexus Mods or SteamDB."},
    ]
    if game.get("hub") == "gta-v":
        items.append({"q": "Can I use mods in GTA Online?",
                      "a": "No. Only mod single-player (Story Mode). Script Hook V closes the game if you go online, and modding GTA Online risks a permanent ban. Keep a clean install or remove mods before playing Online."})
        others = other_editions(game)
        items.append({"q": f"Is this page for GTA V {edition_label(game)} or {' or '.join(edition_label(o) for o in others)}?",
                      "a": f"{game['name']} only (Steam app {game.get('steam_appid')}, {game.get('exe')}). Rockstar patches the PC editions "
                           "separately and Script Hook V can support one before the other, so each has its own verdict. "
                           + " ".join(f"{o['name']} (Steam app {o.get('steam_appid')}, {o.get('exe')}) is tracked at {SITE_URL}/{o['slug']}/." for o in others)
                           + f" Not sure which you have? See {SITE_URL}/gta-v/."})
        items.append({"q": f"Where do the {game['short']} patch history dates come from?",
                      "a": "From a hand-kept table of each PC build's release date and the date Script Hook V first listed it, cross-checked "
                           "against the lspdfrinfo wiki's GTA V build list. The sources give dates only, so update times are whole days."})
    if game["slug"] == "stardew-valley":
        items.append({"q": "How do I check individual Stardew mods?",
                      "a": "Use the official SMAPI mod compatibility list at smapi.io/mods, which tracks compatible, broken and obsolete mods."})
    if game["slug"] == "satisfactory":
        items.append({"q": "Does this cover the Experimental branch?",
                      "a": "No. ModSafe tracks the stable branch (labelled Early Access in SMM and on ficsit.app): stable Steam posts, Steam's public build and ficsit.app's stable-branch SML flag. Experimental often needs a different SML build, so check ficsit.app before switching branches."})
    if game["slug"] == "palworld":
        items.append({"q": "Can I use Palworld mods on official servers?",
                      "a": "No. Pocketpair's mod guidelines forbid mods on official servers and say accounts can be banned. Use mods in single-player, on your own world or on a community server that allows them."})
    if game["slug"] == "monster-hunter-wilds":
        items.append({"q": "What should I do with my mods when Monster Hunter Wilds updates?",
                      "a": "Capcom says mods aren't supported and can stop the game launching after an update. If that happens, uninstall all mods (in Fluffy Mod Manager, \"Uninstall all mods\"), remove dinput8.dll, verify the game files in Steam and launch once unmodded, then reinstall mods as they get updated for the new version."})
    if (steam_item := guides_mod.game_faq_item(game)):
        items.append(steam_item)
    return items


def stale_banner(data: dict) -> str:
    """Honesty guard: if the last successful refresh is old (fetch failures keep previous data), say so."""
    try:
        age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))).total_seconds() / 3600
    except Exception:  # noqa: BLE001
        return ""
    if age_h < 36:
        return ""
    return (f'<p class="note" role="note"><strong>⚠ Data last refreshed {esc(fmt_date(data["generated_at"]))} UTC.</strong> '
            "Recent automatic checks failed, so this may be out of date. Verify on the project pages.</p>")


def display_tag(tag) -> str:
    """Release tag for display: drop a full 40-char commit hash suffix (REFramework nightly-01433-<sha>)."""
    return re.sub(r"-[0-9a-f]{40}$", "", tag) if tag else "—"


def rel_line(fw: dict) -> str:
    if not fw.get("release_tag") and not fw.get("release_published_at"):
        return (f'<div class="rel"><span class="muted">No public release feed</span>'
                f'<span><a href="{esc(fw.get("release_url") or fw["url"])}">check its page</a></span></div>')
    return (f'<div class="rel"><span><code>{esc(display_tag(fw.get("release_tag")))}</code></span><span>{esc(fmt_date(fw.get("release_published_at")))} · '
            f'<a href="{esc(fw.get("release_url") or fw["url"])}">source</a></span></div>')


def framework_cards(data: dict) -> str:
    out = []
    for fw in data["frameworks"]:
        tracked = fw.get("tracked", True)
        st = fw["status"] if tracked else "Check manually"
        reps = "".join(f'<li><a href="{esc(r["url"])}">{esc(r["title"])}</a></li>' for r in fw.get("breakage_reports") or [])
        reps += "".join(f'<li><a href="{esc(r["url"])}">{esc(r["title"].strip())}</a> <span class="muted">(crash report, not tied to a patch)</span></li>'
                        for r in fw.get("crash_reports") or [])
        out.append(f"""<article class="fw {status_class(st)}">
<h3><a href="{esc(fw['url'])}">{esc(fw['name'])}</a></h3>
{badge(st)}
{rel_line(fw)}
<details><summary>Why?</summary><p>{esc(fw.get('reason', ''))}</p>{f"<ul>{reps}</ul>" if reps else ""}</details>
</article>""")
    return "".join(out)


def snippet_row(fid: str, label: str, value: str) -> str:
    return (f'<div class="snip"><label for="{fid}">{esc(label)}</label>'
            f'<input id="{fid}" type="text" readonly value="{esc(value)}" spellcheck="false">'
            f'<button type="button" class="copy" data-for="{fid}">Copy</button></div>')


def follow_section(game: dict, data: dict) -> str:
    slug = game["slug"]
    sn = badges.embed_snippets(game, SITE_URL)
    return f"""<div class="sec-head" id="follow"><h2>Follow &amp; embed</h2></div>
<section class="follow-grid" aria-label="Follow and embed">
<div class="panel">
<h3>📡 Follow via RSS / Discord</h3>
<p>Get a post when a new {esc(game['name'])} patch lands or the verdict changes. Paste this Atom feed into any feed reader
(Feedly, Inoreader, NetNewsWire, Thunderbird) or a Discord RSS bot such as MonitoRSS. No account needed.</p>
{snippet_row(f"feed-{slug}", "Feed", f"{SITE_URL}/{slug}/feed.xml")}
<p class="fine">Every game in one feed: <a href="/feed.xml">{esc(SITE_URL.split('//')[-1])}/feed.xml</a></p>
</div>
<div class="panel">
<h3>🏷 Embed this badge</h3>
<p>Show live {esc(game['name'])} mod status in your mod's README or description. Updates automatically.</p>
<a href="/{slug}/"><img class="badge-preview" src="/badge/{slug}.svg" alt="ModSafe: {esc(game['name'])} mod status badge" height="20" loading="lazy"></a>
{snippet_row(f"md-{slug}", "Markdown", sn['markdown'])}
{snippet_row(f"html-{slug}", "HTML", sn['html'])}
{snippet_row(f"bb-{slug}", "BBCode", sn['bbcode'])}
<p class="fine">BBCode is for Nexus and forum descriptions and uses a PNG copy rendered by shields.io, since many sites won't display SVG. Preview before publishing.</p>
</div>
</section>"""


def build_game_page(game: dict, data: dict) -> str:
    p = data["game"]["latest_patch"]
    slug = game["slug"]
    def reason_li(fw):
        reps = "".join(f'<li><a href="{esc(r["url"])}">{esc(r["title"])}</a></li>' for r in fw.get("breakage_reports") or [])
        reps += "".join(f'<li><a href="{esc(r["url"])}">{esc(r["title"].strip())}</a> <span class="muted">(crash report, not tied to a patch)</span></li>'
                        for r in fw.get("crash_reports") or [])
        return f"<li><strong>{esc(fw['short'])}:</strong> {esc(fw.get('reason', ''))}" + (f"<ul>{reps}</ul>" if reps else "") + "</li>"
    faq = game_faq(game, data)
    faq_html = "".join(faq_article(i) for i in faq)
    extra = "".join(f'<li><a href="{esc(u)}">{esc(n)}</a></li>' for n, u in game.get("extra_links", []))
    snap = f"<dt>Latest snapshot</dt><dd><code>{esc(data['latest_snapshot'])}</code> (not tracked)</dd>" if data.get("latest_snapshot") else ""
    dataset = {"@context": "https://schema.org", "@type": "Dataset",
               "name": f"{game['name']} mod framework patch compatibility",
               "description": f"Status of {game['name']} core mod frameworks relative to the latest official patch.",
               "url": f"{SITE_URL}/{slug}/", "license": "https://creativecommons.org/publicdomain/zero/1.0/",
               "creator": {"@type": "Organization", "name": "ModSafe"}, "dateModified": data.get("generated_at"),
               "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                                 "contentUrl": f"{SITE_URL}/{slug}/status.json"}]}
    vc = status_class(data["verdict"])
    body = f"""
{game_crumbs(game)}
<section class="game-hero v-{vc}" style="--hero:url('{busted(game_img(slug, "hero"))}')">
<div>
<h1>Is it safe to update {esc(game['name'])}?</h1>
<p>{vbadge(data['verdict'])}<span class="micro">{esc(MICROCOPY.get(data['verdict'], ''))}</span></p>
<p class="lede">{esc(game['blurb'])}</p>
{f'<p class="note" role="note"><strong>⚠ {esc(game["note"])}</strong></p>' if game.get("note") else ''}
{edition_switch(game)}
</div>
</section>
{upcoming_notice(active_upcoming(slug, data))}
{stale_banner(data)}
<nav class="tabs" aria-label="On this page"><a href="#status">Status</a><a href="#fw-heading">Frameworks</a>{'<a href="#history">Patch history</a>' if has_history(data) else ''}{'<a href="#mods">Essential ' + (mods_mod.load_mods(slug) or {}).get("noun", "mods") + '</a>' if mods_mod.load_mods(slug) else ''}{'<a href="#console">Console mods</a>' if slug in (CONSOLE_MODS if CONSOLE_MODS is not None else load_console_mods()) else ''}<a href="#news">News</a><a href="#follow">Follow</a><a href="#faq-heading">FAQ</a></nav>
<div class="vgrid" id="status">
<section class="panel" aria-labelledby="verdict-heading">
<h2 id="verdict-heading">Verdict for {esc(p['label'])}</h2>
<p class="big-say">{esc(verdict_sentence(game, data))}</p>
</section>
<section class="panel" aria-label="Patch details">
<dl class="patch-meta">
<dt>{"Latest Stable" if data.get("channels") else "Latest patch"}</dt><dd><strong>{esc(p['label'])}</strong></dd>
<dt>Released</dt><dd>{esc(fmt_date(p.get('published_at')))}</dd>
{f"<dt>Current runtime</dt><dd>{esc(p['runtime_note'])}</dd>" if p.get('runtime_note') else ""}
{f"<dt>Unannounced update</dt><dd>Steam's public {esc(p['unannounced_update']['edition'].title() + ' ') if p['unannounced_update'].get('edition') else ''}build changed on {esc(fmt_date(p['unannounced_update']['published_at']))} (build <code>{esc(p['unannounced_update'].get('buildid') or '?')}</code>) {'after the last manual check' if p['unannounced_update'].get('edition') else 'with no patch announcement'}. Version unknown.</dd>" if p.get('unannounced_update') else ""}
<dt>Source</dt><dd><a href="{esc(p.get('url', ''))}">{esc(p.get('title', ''))}</a></dd>
{snap}
{f"<dt>Builds</dt><dd>" + ", ".join(f"{esc(k.title())} <code>{esc(v)}</code>" + (f" <span class='muted'>(since {esc((p.get('build_dates') or {})[k])})</span>" if (p.get('build_dates') or {}).get(k) else "") for k, v in p["builds"].items()) + "</dd>" if p.get("builds") else ""}
{f"<dt>Last manually verified</dt><dd><strong>{esc(data['last_verified'])}</strong> <span class='muted'>(hand-maintained data)</span></dd>" if data.get("last_verified") else ""}
{"".join(f"<dt>{esc(c['name'])}</dt><dd><a href='{esc(c['url'])}'>{esc(c['title'])}</a> <span class='muted'>· {esc(fmt_date(c['published_at']))} · not counted in the verdict</span></dd>" for c in data.get("channels", []))}
<dt>Data refreshed</dt><dd>{esc(fmt_date(data.get('generated_at')))} <span class="muted">(UTC)</span></dd>
</dl>
</section>
</div>
{rollback_callout(game, data)}
<div class="sec-head"><h2 id="fw-heading">Frameworks &amp; loaders</h2></div>
<section class="fw-grid" aria-labelledby="fw-heading">{framework_cards(data)}</section>
{f'<ul>{extra}</ul>' if extra else ''}
<p class="disclaimer">{esc(data.get('disclaimer', ''))} Items marked “Check manually” are not counted in the verdict.</p>
{f'<div class="sec-head" id="history"><h2>Patch history</h2><a href="/{slug}/history/">Full history →</a></div><p class="track-record">{esc(track_record_sentence(game, data))} <a href="/{slug}/history/#frameworks">Per-framework times →</a></p><section class="hist-list">{history_cards(data, 4)}</section>' if has_history(data) else ""}
{mods_teaser(game, data)}
{console_mods_section(slug)}
<div class="sec-head" id="news"><h2>{esc(game['short'])} news</h2><a href="/news/">All news →</a></div>
<section class="panel">{news_list(game_news(slug, data), 8)}</section>
{follow_section(game, data)}
<div class="sec-head"><h2 id="faq-heading">{esc(game['short'])} modding FAQ</h2></div>
<section class="faq-list" aria-labelledby="faq-heading">
{faq_html}
</section>
{related_links(game, data, "status", wiki=True)}
"""
    return page_shell(
        f"Is it safe to update {game['name']}? Mod status for {p['label']} — ModSafe",
        f"{game['name']} {p['label']}: {data['verdict']}. Live status of " + ", ".join(f['short'] for f in data['frameworks']) + " after the latest patch.",
        f"/{slug}/", slug, body,
        extra_jsonld=[dataset, faq_ld(faq), breadcrumb_ld([("Games", "/")] + hub_crumb(game) + [(game["name"], f"/{slug}/")])],
    )


def hub_crumb(game: dict) -> list[tuple[str, str]]:
    h = game.get("hub")
    return [(GAMES_BY_SLUG[h]["short"], f"/{h}/")] if h and h in GAMES_BY_SLUG else []


def game_crumbs(game: dict, tail: str | None = None) -> str:
    """Home › Games › [GTA V ›] Game [› tail]. The game is a link when a tail follows."""
    hub = "".join(f'<a href="{u}">{esc(n)}</a> › ' for n, u in hub_crumb(game))
    me = (f'<a href="/{game["slug"]}/">{esc(game["name"])}</a> › {esc(tail)}' if tail else esc(game["name"]))
    return f'<p class="crumbs"><a href="/">Home</a> › <a href="/games/">Games</a> › {hub}{me}</p>'


def edition_switch(game: dict) -> str:
    others = other_editions(game)
    if not others:
        return ""
    links = " · ".join(f'<a href="/{o["slug"]}/">{esc(o["short"])} status →</a>' for o in others)
    return (f'<p class="ed-switch">This page covers {esc(edition_label(game))} only. Playing '
            f'{" or ".join(esc(edition_label(o)) for o in others)}? {links} · <a href="/{game["hub"]}/">Which edition do I have?</a></p>')


def history_cards(data: dict, limit: int | None = None) -> str:
    sections = []
    for entry in (data.get("history", []) or [])[:limit] if limit else data.get("history", []):
        cells = "".join(
            f'<li>{badge(fw["status"])} <strong>{esc(fw["short"])}</strong> <code>{esc(display_tag(fw.get("release_tag")))}</code></li>'
            for fw in entry.get("frameworks", []))
        sections.append(f"""<article class="hist-card" id="patch-{esc(entry['label']).replace(' ', '-')}">
<h3>{esc(entry['label'])}</h3>
<p class="muted">{esc(fmt_date(entry.get('published_at')))} · <a href="{esc(entry.get('url', ''))}">{esc(entry.get('title', ''))}</a></p>
<ul class="hist-fw">{cells}</ul>
</article>""")
    return "".join(sections) or '<p class="muted">No patch history for this game (data is hand-maintained or only the latest patch is known).</p>'


def game_news(slug: str, data: dict) -> list[dict]:
    items = [i for i in load_news().get("items", []) if slug in i.get("games", [])]
    if not items:
        items = [{"title": n["title"], "url": n["url"], "source": "Steam", "published_at": n["published_at"],
                  "games": [], "highlight": n.get("is_patch")} for n in data.get("news", [])]
    return items


def host_label(url: str) -> str:
    h = url.split("/")[2].replace("www.", "")
    return {"nexusmods.com": "Nexus Mods", "github.com": "GitHub", "thunderstore.io": "Thunderstore", "modrinth.com": "Modrinth",
            "flightsim.to": "flightsim.to", "ficsit.app": "ficsit.app", "gta5-mods.com": "GTA5-Mods.com"}.get(h, h)


def mod_cards(game: dict, data: dict, mods: dict, limit: int | None = None) -> str:
    names = {m["id"]: m["name"] for m in mods["mods"]}
    names.update({f["id"]: f["short"] for f in data.get("frameworks", [])})
    out = []
    for n, m in enumerate(mods["mods"][:limit] if limit else mods["mods"], 1):
        st, why = mods_mod.compat(m, data)
        req = ", ".join(esc(names.get(r, r)) for r in m.get("requires", []))
        out.append(f"""<article class="mod-card" id="mod-{esc(m['id'])}">
<div class="mod-top"><span class="mod-n">{n}</span><div><h3>{esc(m['name'])}</h3><p class="mod-cat">{esc(m['category'])}</p></div></div>
<p>{esc(m['summary'])}</p>
{f'<p class="mod-note">{esc(m["note"])}</p>' if m.get('note') else ''}
<p class="mod-req">{('Requires: ' + req) if req else 'No requirements listed by the author'}{('. Also needs: ' + ', '.join(esc(a) for a in m['also_requires'])) if m.get('also_requires') else ''}</p>
<div class="mod-foot">{badge(st)}<a class="dl" href="{esc(m['url'])}" rel="noopener external">Get it on {esc(host_label(m['url']))} ↗</a></div>
<p class="mod-why muted">{esc(why)}{(" Last updated on its download page: " + esc(m["last_updated"]) + ".") if m.get("last_updated") else ""}</p>
</article>""")
    return "".join(out)


def load_console_mods() -> dict:
    p = ROOT / "data" / "manual" / "console-mods.json"
    return json.loads(p.read_text()).get("games", {}) if p.exists() else {}


CONSOLE_MODS = None


def console_mods_section(slug: str) -> str:
    global CONSOLE_MODS
    if CONSOLE_MODS is None:
        CONSOLE_MODS = load_console_mods()
    c = CONSOLE_MODS.get(slug)
    if not c:
        return ""
    badges = "".join(f'<span class="plat">{esc(x)}</span>' for x in c["platforms"])
    u = c["update"]
    lims = "".join(f"<li>{esc(x)}</li>" for x in c["limits"])
    srcs = " · ".join(f'<a href="{esc(url)}">{esc(n)}</a>' for n, url in c["sources"])
    return f"""<div class="sec-head" id="console"><h2>Console mods</h2><span class="plats">{badges}</span></div>
<section class="panel console-mods" aria-labelledby="console-q">
<h3 id="console-q">Did the latest patch disable console mods? <strong>{esc(c['answer'])}</strong></h3>
<p class="muted">{esc(c['system'])}. Latest console-relevant update: <a href="{esc(u['url'])}">{esc(u['label'])}</a> ({esc(fmt_date(u['date']))}).</p>
<p>{esc(c['summary'])}</p>
<h4>Platform limits</h4><ul>{lims}</ul>
<p class="muted">Hand-maintained from official patch notes and studio announcements · <strong>Last manually verified {esc(c['last_verified'])}</strong> · Sources: {srcs}</p>
</section>"""


def mods_teaser(game: dict, data: dict) -> str:
    mods = mods_mod.load_mods(game["slug"])
    if not mods:
        return ""
    s = game["slug"]
    guide = f'<a href="/{s}/install/">How to install →</a>' if mods_mod.load_guide(s) else ""
    return (f'<div class="sec-head" id="mods"><h2>Essential {mods.get("noun", "mods")}</h2><span class="sec-links"><a href="/{s}/mods/">All {len(mods["mods"])} →</a> {guide}</span></div>'
            f'<section class="mod-grid">{mod_cards(game, data, mods, 6)}</section>')


MIN_HISTORY = 2  # a history page needs at least two patches to say anything beyond the main page


def has_history(data: dict) -> bool:
    return len(data.get("history") or []) >= MIN_HISTORY


def _clip(text: str, n: int = 158) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= n:
        return text
    return text[: text.rfind(" ", 0, n - 1)].rstrip(",;:") + "…"


def _md_plain(s: str) -> str:
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return re.sub(r"\*\*|`", "", s).strip()


def hub_pages(game: dict, data: dict) -> list[tuple[str, str, str]]:
    slug = game["slug"]
    mods = mods_mod.load_mods(slug)
    items = [("status", f"/{slug}/", f"{game['short']} status")]
    if has_history(data):
        items.append(("history", f"/{slug}/history/", "Patch history"))
    if mods:
        items.append(("mods", f"/{slug}/mods/", "Essential " + mods.get("noun", "mods")))
    if mods_mod.load_guide(slug):
        items.append(("install", f"/{slug}/install/", "Install guide"))
    return items


def hub_nav(game: dict, data: dict, current: str) -> str:
    cur = ' aria-current="page"'
    links = "".join(f'<a href="{u}"{cur if k == current else ""}>{esc(t)}</a>' for k, u, t in hub_pages(game, data))
    return f'<nav class="tabs hub-nav" aria-label="{esc(game["short"])} pages">{links}</nav>'


def related_links(game: dict, data: dict, current: str, wiki: bool = False) -> str:
    icons = {"status": "📊", "history": "📜", "mods": "🧩", "install": "📘"}
    out = [f'<a href="{u}">{icons[k]} {esc(t)}</a>' for k, u, t in hub_pages(game, data) if k != current]
    out += [f'<a href="/{o["slug"]}/">🔀 {esc(o["short"])}</a>' for o in other_editions(game)]
    if game.get("steam_appid"):
        out.append(f'<a href="{guides_mod.STEAM_GUIDE_PATH}">🛑 Stop Steam auto-updates</a>')
    if wiki and game.get("wiki"):
        out.append(f'<a href="{esc(game["wiki"])}">🛠 Modding resources</a>')
    out.append('<a href="/games/">🎮 All games</a>')
    return f'<section class="links" aria-label="Related pages">{" ".join(out)}</section>'


def track_record_sentence(game: dict, data: dict) -> str:
    """One data-derived sentence for the game page and the history page lede."""
    s = hstats.game_summary(data)
    if s["patches"] < MIN_HISTORY:
        return ""
    out = (f"ModSafe has tracked {s['patches']} {game['short']} patches between {fmt_date(s['first'].isoformat())} "
           f"and {fmt_date(s['last'].isoformat())}, about one every {hstats.fmt_days(s['avg_gap'])}.")
    if s["pairs"]:
        out += (f" When a framework release named the patch, it arrived a median of "
                f"{hstats.fmt_days(s['median_days'])} after the patch post ({s['pairs']} case{'' if s['pairs'] == 1 else 's'}).")
    elif s["next_median"] is not None and s["next_pairs"] >= 3:
        out += (f" No release in our data names a specific patch, but the next framework release came a median of "
                f"{hstats.fmt_days(s['next_median'])} after one ({s['next_pairs']} case{'' if s['next_pairs'] == 1 else 's'}).")
    return out


def _fw_timing(entry: dict, fw: dict, until) -> str:
    info = hstats.pair_info(entry, fw, until)
    if info["kind"] == "named":
        return f'<span class="hist-t ok">named in {esc(info["tag"] or "?")} +{esc(hstats.fmt_days(info["days"]))}</span>'
    if info["kind"] == "unnamed":
        if info.get("next_days") is not None:
            return f'<span class="hist-t">next release +{esc(hstats.fmt_days(info["next_days"]))}</span>'
        return '<span class="hist-t">no release before the next patch</span>' if until else '<span class="hist-t">no release yet</span>'
    if info["kind"] == "outside":
        return '<span class="hist-t">older than our release data</span>'
    return ""


def history_faq(game: dict, data: dict, s: dict) -> list[dict]:
    name, short = game["name"], game["short"]
    faq = [{"q": f"How often does {name} get patched?",
            "a": f"ModSafe has {s['patches']} {short} patches on record, from {fmt_date(s['first'].isoformat())} to "
                 f"{fmt_date(s['last'].isoformat())}. The average gap between them is {hstats.fmt_days(s['avg_gap'])}."}]
    if s["pairs"]:
        lw = s["longest_wait"]
        a = (f"Across {s['pairs']} {'patch-and-framework pair' if s['pairs'] == 1 else 'patch-and-framework pairs'} where a release named the patch, the update came a median "
             f"of {hstats.fmt_days(s['median_days'])} (mean {hstats.fmt_days(s['mean_days'])}) after the patch post. "
             f"The longest was {lw['fw']} {lw['tag']} for {lw['patch']}, at {hstats.fmt_days(lw['days'])}.")
    elif s["next_median"] is not None:
        a = (f"No framework release in our data names a specific {short} patch, so we can't time confirmed fixes. As "
             f"context, the next framework release came a median of {hstats.fmt_days(s['next_median'])} after a patch "
             f"({s['next_pairs']} cases where it came before the following patch).")
    else:
        a = (f"We can't say yet. Our framework release data doesn't reach back to these {short} patches, so we only "
             f"report each patch's verdict and wait for new patches to build a track record.")
    faq.append({"q": f"How long do {short} mod frameworks take to update after a patch?", "a": a})
    if s["log_start"] and not s.get("log_young"):
        ls = s["longest_stretch"]
        if ls:
            end = (f"It ended on {fmt_date(ls['end'].isoformat())} with the verdict {ls['end_verdict']}." if ls["end"]
                   else "It is still ongoing.")
            a = (f"Since our verdict log started on {fmt_date(s['log_start'].isoformat())}, the longest unsafe stretch was "
                 f"{hstats.fmt_days(ls['days'])} after {ls['patch']} ({', '.join(ls['verdicts'])}). {end}")
        else:
            a = (f"Since our verdict log started on {fmt_date(s['log_start'].isoformat())}, the {short} verdict hasn't "
                 f"been unsafe (Breakage reported, Just patched, wait or Not ported yet).")
        faq.append({"q": f"What is the longest {short} mods have been unsafe after a patch?", "a": a})
    return faq


def build_game_history(game: dict, data: dict) -> str:
    slug, name, short = game["slug"], game["name"], game["short"]
    hist = data.get("history") or []
    s = hstats.game_summary(data)
    bounds = hstats.next_patch_dates(hist)
    tiles = [(str(s["patches"]), "patches tracked"), (hstats.fmt_days(s["avg_gap"]), "average gap between patches")]
    if s["pairs"]:
        tiles.append((hstats.fmt_days(s["median_days"]), "median time to an update naming the patch"))
    elif s["next_median"] is not None and s["next_pairs"] >= 3:
        tiles.append((hstats.fmt_days(s["next_median"]), "median time to the next framework release"))
    if s["longest_stretch"]:
        ls = s["longest_stretch"]
        tiles.append((hstats.fmt_days(ls["days"]), "longest unsafe stretch" + (" (ongoing)" if ls["end"] is None else "")))
    tiles_html = "".join(f"<div><strong>{esc(v)}</strong>{esc(k)}</div>" for v, k in tiles)
    rows = []
    for f in s["frameworks"]:
        if not f["affected"]:
            continue
        lg = f"{hstats.fmt_days(f['longest'][0])} ({esc(f['longest'][1])})" if f["longest"] else "—"
        rows.append(f"<tr><td>{esc(f['short'])}</td><td>{f['n']}</td><td>{esc(hstats.fmt_days(f['median']))}</td><td>{lg}</td>"
                    f"<td>{esc(hstats.fmt_days(f['next_median']))}</td><td>{f['unnamed']}</td><td>{f['outside']}</td></tr>")
    table = (f"""<div class="sec-head"><h2 id="frameworks">Framework update times</h2></div>
<section class="panel guide"><div class="table-wrap"><table><thead><tr><th>Framework</th><th>Patches named</th><th>Median to named update</th><th>Longest</th><th>Median to next release</th><th>Not named</th><th>Older than data</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="muted">“Patches named”: releases whose notes name the patch. “Median to next release” covers any release, not only fixes, and counts it only if it shipped before the following patch. “Not named” pairs may simply not have needed an update. “Older than data”: the patch predates the releases we have for that framework.</p></section>""" if rows else "")
    faq = history_faq(game, data, s)
    cards = []
    for entry, until in zip(hist, bounds):
        cells = "".join(
            f'<li>{badge(fw["status"])} <strong>{esc(fw["short"])}</strong> <code>{esc(display_tag(fw.get("release_tag")))}</code> {_fw_timing(entry, fw, until)}</li>'
            for fw in entry.get("frameworks", []))
        cards.append(f"""<article class="hist-card" id="patch-{esc(entry['label']).replace(' ', '-')}">
<h3>{esc(entry['label'])}</h3>
<p class="muted">{esc(fmt_date(entry.get('published_at')))} · <a href="{esc(entry.get('url', ''))}">{esc(entry.get('title', ''))}</a></p>
<ul class="hist-fw">{cells}</ul>
</article>""")
    body = f"""
{game_crumbs(game, "Patch history")}
<section class="page-hero"><h1>{esc(name)} patch history &amp; mod update times</h1>
<p class="lede">{esc(track_record_sentence(game, data))}</p></section>
{hub_nav(game, data, "history")}
<section class="panel"><div class="stats hist-stats">{tiles_html}</div></section>
<div class="sec-head"><h2 id="summary">Track record</h2></div>
<section class="faq-list">{"".join(faq_article(i) for i in faq)}</section>
{table}
<div class="sec-head"><h2 id="patches">Patch by patch</h2></div>
<section class="hist-list">{''.join(cards)}</section>
<p class="disclaimer">Every number on this page comes from ModSafe's own data: the patch list, each framework's release history from its official source, and our verdict log (kept since {esc(fmt_date(s['log_start'].isoformat())) if s['log_start'] else 'recently'}). Times run from the official patch post to the framework release. See the <a href="/faq/">FAQ</a> for how verdicts are decided, or <a href="/{slug}/status.json">download the raw data</a>.</p>
{related_links(game, data, "history")}
"""
    if s["pairs"]:
        hl = f"framework updates named the patch a median {hstats.fmt_days(s['median_days'])} later"
    elif s["next_median"] is not None and s["next_pairs"] >= 3:
        hl = f"next framework release a median {hstats.fmt_days(s['next_median'])} after a patch"
    else:
        hl = "verdicts for each patch"
    ls = s["longest_stretch"]
    desc = (f"{s['patches']} {name} patches since {s['first'].year}: {hl}"
            + (f"; longest unsafe stretch {hstats.fmt_days(ls['days'])}." if ls else ".") + " Per framework, from our own data.")
    return page_shell(f"{name} patch history: {s['patches']} patches & mod update times — ModSafe", _clip(desc),
                      f"/{slug}/history/", slug, body,
                      extra_jsonld=[faq_ld(faq), breadcrumb_ld([("Games", "/")] + hub_crumb(game) + [(name, f"/{slug}/"), ("Patch history", f"/{slug}/history/")])])


def guide_errors(md: str) -> list[dict]:
    """FAQ items from the guide's '## Common errors and fixes' bullets ('- **Question?** Answer. Source: [..](..)')."""
    block = re.search(r"^## Common errors and fixes\n(.*?)(?=^## |\Z)", md, re.M | re.S)
    out = []
    for line in (block.group(1) if block else "").splitlines():
        m = re.match(r"^- \*\*(.+?)\*\*\s*(.+)", line)
        if m:
            out.append({"q": _md_plain(m.group(1)), "a": _md_plain(m.group(2))})
    return out


def install_order_html(game: dict, data: dict, mods: dict | None) -> str:
    if not mods:
        return ""
    slug = game["slug"]
    names = {m["id"]: m["name"] for m in mods["mods"]}
    names.update({f["id"]: f["short"] for f in data.get("frameworks", [])})
    lis = []
    for m in mods["mods"]:
        req = [names.get(r, r) for r in m.get("requires", [])]
        st, _ = mods_mod.compat(m, data)
        lis.append(f'<li><a href="/{slug}/mods/#mod-{esc(m["id"])}">{esc(m["name"])}</a> {badge(st)}'
                   + (f' <span class="muted">needs {esc(", ".join(req))}</span>' if req else "") + "</li>")
    return (f'<div class="sec-head"><h2 id="order">Install order at a glance</h2><a href="/{slug}/mods/">Details →</a></div>'
            f'<section class="panel"><ol class="order-list">{"".join(lis)}</ol>'
            f'<p class="muted">Frameworks first, then the mods that need them. Badges are our live status for '
            f'{esc(data["game"]["latest_patch"]["label"])}.</p></section>')


def build_install_page(game: dict, data: dict, md: str) -> str:
    slug = game["slug"]
    g = mods_mod.guide_parts(md)
    mods = mods_mod.load_mods(slug)
    errors = guide_errors(md)
    fws = [f for f in data.get("frameworks", []) if f.get("tracked", True)]
    fw_li = "".join(f'<li>{badge(f["status"])} <strong>{esc(f["short"])}</strong> <code>{esc(display_tag(f.get("release_tag")))}</code></li>' for f in fws)
    body = f"""
{game_crumbs(game, "Install guide")}
<section class="page-hero"><h1>{esc(g['title'])}</h1>
<p class="lede">{esc(g['intro'])}</p></section>
{hub_nav(game, data, "install")}
<section class="panel"><h2 class="panel-h">Before you start: {vbadge(data['verdict'])} for {esc(data['game']['latest_patch']['label'])}</h2>
<ul class="hist-fw">{fw_li}</ul>
<p class="muted">Live framework status, refreshed every few hours. <a href="/{slug}/">Full status →</a>{' · <a href="/' + slug + '/history/">How fast they update after patches →</a>' if has_history(data) else ''}</p></section>
{install_order_html(game, data, mods)}
<article class="panel guide">{mods_mod.md_to_html(g['body'].strip().split(chr(10) * 2, 1)[-1])}</article>
{f'<p class="disclaimer">Keep a working setup by stopping Steam from patching the game before your mods catch up: <a href="{guides_mod.STEAM_GUIDE_PATH}">how to stop Steam auto-updates</a>.</p>' if game.get("steam_appid") else ''}
{related_links(game, data, "install")}
"""
    howto = {"@context": "https://schema.org", "@type": "HowTo", "name": g["title"], "description": g["intro"][:300],
             "step": [{"@type": "HowToStep", "position": i, "name": s["name"], "text": s["text"],
                       "url": f"{SITE_URL}/{slug}/install/#steps"} for i, s in enumerate(g["steps"], 1)]}
    desc = (f"Mod {game['name']} with {fws[0]['short'] if fws else 'the core frameworks'}: {len(g['steps'])} steps, "
            f"install order, {len(errors)} common errors with sourced fixes, and how to roll back.")
    ld = [howto, breadcrumb_ld([("Games", "/")] + hub_crumb(game) + [(game["name"], f"/{slug}/"), ("Install guide", f"/{slug}/install/")])]
    if errors:
        ld.insert(1, faq_ld(errors))
    return page_shell(f"{g['title']} (beginner guide) — ModSafe", _clip(desc), f"/{slug}/install/", slug, body, extra_jsonld=ld)


def dependency_map_html(game: dict, data: dict, mods: dict) -> tuple[str, list[dict]]:
    names = {m["id"]: m["name"] for m in mods["mods"]}
    names.update({f["id"]: f["short"] for f in data.get("frameworks", [])})
    needed: dict[str, list[str]] = {}
    standalone = []
    for m in mods["mods"]:
        if not m.get("requires"):
            standalone.append(m["name"])
        for r in m.get("requires", []):
            needed.setdefault(r, []).append(m["name"])
    rows = "".join(f"<tr><td>{esc(names.get(r, r))}</td><td>{len(ms)}</td><td>{esc(', '.join(ms))}</td></tr>"
                   for r, ms in sorted(needed.items(), key=lambda kv: -len(kv[1])))
    faq = []
    if needed:
        top, ms = max(needed.items(), key=lambda kv: len(kv[1]))
        faq.append({"q": f"Which {game['short']} {mods.get('noun', 'mods')} depend on {names.get(top, top)}?",
                    "a": f"{len(ms)} of the {len(mods['mods'])} on our list need {names.get(top, top)}: {', '.join(ms)}. "
                         f"If {names.get(top, top)} breaks after a patch, all of them are affected."})
    first = [m["name"] for m in mods["mods"][:4]]
    faq.insert(0, {"q": f"What should I install first for {game['name']}?",
                   "a": f"Install in list order: {', '.join(first)}{', and so on' if len(mods['mods']) > 4 else ''}. "
                        f"Frameworks come first because the mods after them need them. We recommend {mods['manager']['name']} to manage them."})
    html_ = (f"""<div class="sec-head"><h2 id="deps">Dependency map</h2></div>
<section class="panel guide"><div class="table-wrap"><table><thead><tr><th>Requirement</th><th>Mods</th><th>Needed by</th></tr></thead><tbody>{rows}</tbody></table></div>
{f'<p class="muted">No listed requirements: {esc(", ".join(standalone))}.</p>' if standalone else ''}</section>""" if rows else "")
    return html_, faq


def build_mods_page(game: dict, data: dict, mods: dict) -> str:
    slug = game["slug"]
    mgr = mods["manager"]
    noun = mods.get("noun", "mods")
    deps, faq = dependency_map_html(game, data, mods)
    body = f"""
{game_crumbs(game, "Essential " + noun)}
<section class="page-hero"><h1>Essential {esc(game['name'])} {noun}</h1>
<p class="lede">{esc(mods['intro'])}</p>
<p class="muted">Hand-picked by ModSafe, listed in install order. We link only to the official download pages and never host files. Badges reflect our live framework status for {esc(data['game']['latest_patch']['label'])}. List verified {esc(mods['verified_at'])}.</p>
<p class="cta-row">{f'<a class="btn" href="/{slug}/install/">📘 How to install {noun}</a> ' if mods_mod.load_guide(slug) else ''}<a class="btn ghost" href="{esc(mgr['url'])}" rel="noopener external">Recommended manager: {esc(mgr['name'])} ↗</a>
{f'<a class="btn ghost" href="{esc(mods["compat_list"])}" rel="noopener external">Community compatibility list ↗</a>' if mods.get('compat_list') else ''}</p>
</section>
{hub_nav(game, data, "mods")}
<section class="mod-grid">{mod_cards(game, data, mods)}</section>
{deps}
<div class="sec-head"><h2 id="faq-heading">{esc(game['short'])} {esc(noun)} FAQ</h2></div>
<section class="faq-list">{"".join(faq_article(i) for i in faq)}</section>
<p class="disclaimer">Mod pages and requirements can change; always read the mod's own page before installing. Not affiliated with Nexus Mods or any mod author.</p>
{related_links(game, data, "mods")}
"""
    itemlist = {"@context": "https://schema.org", "@type": "ItemList", "name": f"Essential {game['name']} {noun}",
                "itemListOrder": "https://schema.org/ItemListOrderAscending",
                "itemListElement": [{"@type": "ListItem", "position": i, "name": m["name"], "url": m["url"]}
                                    for i, m in enumerate(mods["mods"], 1)]}
    top = ", ".join(m["name"] for m in mods["mods"][:3])
    desc = f"{len(mods['mods'])} essential {game['name']} {noun}, what each needs, and live {data['game']['latest_patch']['label']} status. Install order: {top}…"
    return page_shell(f"Essential {game['name']} {noun} ({len(mods['mods'])}) & install order — ModSafe", _clip(desc),
                      f"/{slug}/mods/", slug, body,
                      extra_jsonld=[itemlist, faq_ld(faq), breadcrumb_ld([("Games", "/")] + hub_crumb(game) + [(game["name"], f"/{slug}/"), ("Essential mods", f"/{slug}/mods/")])])


UPCOMING_FILE = ROOT / "data" / "manual" / "upcoming-patches.json"


def load_upcoming() -> dict:
    try:
        return json.loads(UPCOMING_FILE.read_text(encoding="utf-8")).get("patches", {})
    except FileNotFoundError:
        return {}


def active_upcoming(slug: str, data: dict, today=None, upcoming: dict | None = None) -> dict | None:
    """The officially announced upcoming patch for a game, unless it has already been detected (version match, or a
    tracked patch dated on/after the announced date) or expired (`expire_days`, default 3, after the date)."""
    from datetime import date, timedelta
    today = today or datetime.now(timezone.utc).date()
    lp = (data.get("game") or {}).get("latest_patch") or {}
    lp_day = (lp.get("published_at") or "")[:10]
    for e in (upcoming if upcoming is not None else load_upcoming()).get(slug, []):
        try:
            d = date.fromisoformat(e["date"])
        except (KeyError, ValueError):
            continue
        if not e.get("source"):
            continue
        if today > d + timedelta(days=int(e.get("expire_days", 3))):
            continue
        if (e.get("version") and lp.get("version") == e["version"]) or (lp_day and lp_day >= e["date"]):
            continue
        return e
    return None


def upcoming_hide_after(e: dict) -> str:
    from datetime import date, timedelta
    return (date.fromisoformat(e["date"]) + timedelta(days=int(e.get("expire_days", 3)) + 1)).isoformat()


UPCOMING_JS = ("<script>(function(){var n=Date.now();[].forEach.call(document.querySelectorAll('[data-hide-after]'),"
               "function(x){var d=Date.parse(x.getAttribute('data-hide-after')+'T00:00:00Z');if(d&&n>=d)x.hidden=true;});})();</script>")


def upcoming_date_text(e: dict) -> str:
    from datetime import date
    d = date.fromisoformat(e["date"])
    return f"{d.strftime('%b')} {d.day}"


def upcoming_notice(e: dict | None) -> str:
    if not e:
        return ""
    fws = ", ".join(e.get("frameworks", []))
    stores = e.get("stores") or "your launcher"
    return (f'<aside class="upcoming" role="note" aria-label="Update incoming" data-hide-after="{esc(upcoming_hide_after(e))}">'
            f'<p class="up-title">⚡ Update incoming: {esc(e.get("label") or e.get("name"))} arrives {esc(upcoming_date_text(e))}</p>'
            f'<p>Script frameworks{f" ({esc(fws)})" if fws else ""} usually break on big patches. '
            f'<strong>Turn off auto-update in {esc(stores)} and back up your mods folder.</strong> '
            + (f'<a href="{guides_mod.STEAM_GUIDE_PATH}">How to stop Steam updating it →</a> ' if "steam" in stores.lower() else '') +
            f'This page will update when frameworks catch up.</p>'
            f'<p class="up-src">Official source: <a href="{esc(e["source"])}" rel="noopener external">{esc(e.get("source_title") or e["source"])}</a></p>'
            f'</aside>{UPCOMING_JS}')


def game_cards(games_data, compact: bool = False) -> str:
    cards = []
    for i, (game, data) in enumerate(games_data):
        p = data["game"]["latest_patch"]
        chips = "" if compact else "".join(f'<span class="chip">{esc(f["short"])}</span>' for f in data["frameworks"])
        cls = status_class(data["verdict"])
        up = active_upcoming(game["slug"], data)
        up_html = (f'<p class="card-upcoming" data-hide-after="{esc(upcoming_hide_after(up))}">⚡ {esc(up.get("label") or up.get("name"))} arrives {esc(upcoming_date_text(up))}: '
                   f'turn off auto-update</p>') if up else ""
        cards.append(f"""<article class="game-card v-{cls}" data-name="{esc(game['name'].lower())} {esc(game['short'].lower())}" data-status="{cls}" data-genre="{esc(game.get('genre', ''))}">
<div class="card-art"><img src="{busted(game_img(game['slug']))}" width="616" height="353" {'loading="lazy" ' if i > 2 else ''}decoding="async" alt="{esc(game['name'])} cover art">{badge(data['verdict'])}</div>
<div class="card-body">
<h3><a href="/{game['slug']}/" class="stretched">{esc(game['name'])}</a></h3>
{up_html}<p class="card-meta"><span>{patch_label_html(p['label'])}</span><span>{esc(fmt_date(p.get('published_at')))}</span></p>
<p class="updated">Checked <time class="ago" datetime="{esc(data.get('generated_at', ''))}">{esc(fmt_date(data.get('generated_at')))}</time></p>
{f'<div class="chips">{chips}</div>' if chips else ''}
<p class="view">View status →</p>
</div>
</article>""")
    return "".join(cards) + (UPCOMING_JS if any("card-upcoming" in c for c in cards) else "")


AGO_JS = """<script>
(function(){var n=Date.now();[].forEach.call(document.querySelectorAll('time.ago'),function(t){var d=Date.parse(t.getAttribute('datetime'));if(!d)return;var m=Math.max(0,Math.round((n-d)/60000)),s=m<1?'just now':m<60?m+' min ago':m<1440?Math.round(m/60)+' h ago':Math.round(m/1440)+' d ago';t.textContent=s;t.title=new Date(d).toLocaleString();});})();
</script>"""


FILTER_JS = """<script>
(function(){var q=document.getElementById('gq'),st=document.getElementById('gs'),ge=document.getElementById('gg'),cards=[].slice.call(document.querySelectorAll('.game-card')),cnt=document.getElementById('gcount');
function f(){var t=(q.value||'').toLowerCase().trim(),s=st.value,g=ge.value,n=0;cards.forEach(function(c){var ok=(!t||c.dataset.name.indexOf(t)>-1)&&(!s||c.dataset.status===s)&&(!g||c.dataset.genre===g);c.hidden=!ok;if(ok)n++;});cnt.textContent=n+' of '+cards.length+' games';}
[q,st,ge].forEach(function(e){e.addEventListener('input',f);});f();
document.addEventListener('keydown',function(e){var t=e.target.tagName;if(e.key==='/'&&!/INPUT|SELECT|TEXTAREA/.test(t)&&!e.ctrlKey&&!e.metaKey){e.preventDefault();q.focus();}if(e.key==='Escape'&&e.target===q){q.value='';f();q.blur();}});})();
</script>""" + AGO_JS



def filter_bar(games_data) -> str:
    genres = sorted({g.get("genre", "") for g, _ in games_data if g.get("genre")})
    gopts = "".join(f'<option value="{esc(x)}">{esc(x)}</option>' for x in genres)
    return f"""<form class="filters" role="search" onsubmit="return false">
<label class="sr" for="gq">Search games</label><input id="gq" type="search" placeholder="🔍 Search games…  (press / )" autocomplete="off" aria-keyshortcuts="/">
<label class="sr" for="gs">Status</label><select id="gs"><option value="">All statuses</option><option value="ok">✔ Safe</option><option value="likely">◑ Likely safe</option><option value="wait">⏳ Just patched, wait</option><option value="broken">✖ Breakage / not ported</option></select>
<label class="sr" for="gg">Genre</label><select id="gg"><option value="">All genres</option>{gopts}</select>
<span id="gcount" class="muted" aria-live="polite"></span>
</form>"""


def load_news() -> dict:
    if NEWS_FILE.exists():
        try:
            return json.loads(NEWS_FILE.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {"items": [], "sources": []}


AROUND_LIMIT = 12
RELEVANT_RE = __import__("re").compile(
    r"(?i)\b(mods?|modding|modders?|patch(?:es)?|updates?|hotfix|pc|steam|nexus|dlc|early access|expansion|"
    r"remaster|remake|launch(?:es|ed)?|release[sd]?|free|demo|playtest|roadmap|1\.0)\b")
HARDWARE_RE = __import__("re").compile(r"(?i)\b(mouse|keyboard|headset|monitor|gpu|cpu|ssd|laptop|deal|sale|% off|razer|logitech|amd|intel|nvidia)\b")


def around_pc(items: list[dict]) -> list[dict]:
    """Untracked headlines, preferring modding/PC-game relevance over hardware, deals and industry chatter."""
    rest = [i for i in items if not i.get("games")]
    def score(i):
        t = i["title"]
        return (2 if RELEVANT_RE.search(t) else 0) - (2 if HARDWARE_RE.search(t) else 0)
    picked = [i for i in rest if score(i) > 0]
    if len(picked) < AROUND_LIMIT:
        picked += [i for i in rest if score(i) == 0][: AROUND_LIMIT - len(picked)]
    return sorted(picked, key=lambda i: i["published_at"], reverse=True)[:AROUND_LIMIT]


def patch_label_html(label: str) -> str:
    """'Patch 2.31' / 'Update 2026-08-18' read fine alone; bare versions like '1.7.99' get a 'Patch' prefix."""
    import re as _re
    if _re.match(r"(?i)(patch|update|hotfix|title update|tu\b|v?er(sion)?\b|release|build|snapshot|minecraft)", label.strip()):
        return f"<strong>{esc(label)}</strong>"
    return f"Patch <strong>{esc(label)}</strong>"


def news_list(items: list[dict], limit: int | None = None) -> str:
    names = {g["slug"]: g["short"] for g in GAMES}
    lis = []
    for it in items[:limit] if limit else items:
        tags = "".join(f'<a class="chip" href="/{s}/">{esc(names.get(s, s))}</a>' for s in it.get("games", []))
        hl = ' class="hl"' if it.get("highlight") else ""
        flag = '<span class="badge wait">🛠 Patch</span> ' if it.get("highlight") else ""
        lis.append(f"""<li{hl}>{flag}<a href="{esc(it['url'])}" rel="noopener" target="_blank">{esc(it['title'])}</a>
<span class="nmeta">{esc(it['source'])} · {esc(fmt_date(it['published_at']))} {tags}</span></li>""")
    return f'<ul class="news">{"".join(lis) or '<li class="muted">No headlines in the last few weeks.</li>'}</ul>'


def build_home(games_data: list[tuple[dict, dict]]) -> str:
    news = load_news()
    itemlist = {"@context": "https://schema.org", "@type": "ItemList", "name": "Games tracked by ModSafe",
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": g["name"], "url": f"{SITE_URL}/{g['slug']}/"}
                                    for i, (g, _) in enumerate(games_data)]}
    n_fw = sum(1 for _, d in games_data for f in d["frameworks"] if f.get("tracked", True))
    n_games = distinct_games([g for g, _ in games_data])
    n_plat = sum(1 for g, _ in games_data if g.get("genre") == "Platform")
    n_ok = sum(1 for _, d in games_data if d["verdict"] in ("Safe", "Likely safe"))
    body = f"""
<section class="home-hero" style="--hero:url('/img/cyberpunk-2077-hero.webp')">
<p class="eyebrow">Patch day, minus the panic</p>
<h1>Did your mods <em>survive</em> the patch?</h1>
<p class="lede">A new update drops, and script extenders and mod loaders break first. ModSafe watches every game's core frameworks so you know whether to hit update or hold the line.</p>
<div class="legend"><span class="badge ok">{icon("Safe")}Safe</span><span class="badge likely">{icon("Likely safe")}Likely safe</span><span class="badge wait">{icon("Just patched, wait")}Just patched, wait</span><span class="badge broken">{icon("Breakage reported")}Breakage reported</span></div>
<div class="hero-actions"><a class="btn" href="#games">🎮 Pick your game</a> <a class="btn ghost" href="/faq/">❓ How it works</a></div>
<div class="stats"><div><strong>{n_games}</strong>games{f" + {n_plat} platform" if n_plat else ""}</div><div><strong>{n_fw}</strong>frameworks auto-tracked</div><div><strong>{n_ok}/{len(games_data)}</strong>safe or likely safe now</div></div>
</section>
<div class="sec-head" id="games"><h2>Choose your game</h2><a href="/games/">All games →</a></div>
<p class="muted">Every game has its own page with the verdict, each framework, patch history, news and FAQ. Tap a card.</p>
{filter_bar(games_data)}
<section class="game-grid" aria-label="Games">
{game_cards(games_data, compact=True)}
</section>
<div class="sec-head"><h2>Latest patches</h2><a href="/patches/">Patch timeline →</a></div>
<section class="panel"><ul class="pt-list">{patch_rows(patches_mod.collect_patches(games_data, limit=5))}</ul></section>
<div class="sec-head"><h2>Latest gaming news</h2><a href="/news/">All news →</a></div>
<section class="panel">{news_list(news.get("items", []), 8)}</section>
<section class="panel"><h2>How we call it</h2>{legend_html()}
<p style="margin-top:var(--s4)"><a href="/faq/">Read the FAQ →</a></p></section>
"""
    return page_shell(f"ModSafe — Is it safe to update? Mod compatibility for {distinct_games(GAMES)} PC games & Steam Deck", SITE_DESC, "/", "home", body + FILTER_JS + LOCAL_TIME_JS, extra_jsonld=[itemlist])


def build_games_index(games_data) -> str:
    body = f"""<p class="crumbs"><a href="/">Home</a> › Games</p>
<section class="page-hero"><h1>All games</h1><p class="lede">Pick a game to see whether its mod frameworks survived the latest patch.</p></section>
{filter_bar(games_data)}
<section class="game-grid" aria-label="Games">{game_cards(games_data)}</section>"""
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": "Games tracked by ModSafe",
          "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": g["name"], "url": f"{SITE_URL}/{g['slug']}/"}
                              for i, (g, _) in enumerate(games_data)]}
    return page_shell(f"All games — {SITE_NAME}", "Mod framework patch status for every game ModSafe tracks.", "/games/", "games",
                      body + FILTER_JS, extra_jsonld=[ld, breadcrumb_ld([("Home", "/"), ("Games", "/games/")])])


def build_news_page() -> str:
    news = load_news()
    srcs = ", ".join(f'<a href="{esc(x["url"])}">{esc(x["name"])}</a>' for x in news.get("sources", []) if x.get("ok"))
    body = f"""<p class="crumbs"><a href="/">Home</a> › News</p>
<section class="page-hero"><h1>Latest gaming news</h1><p class="lede">Official Steam announcements for the games we track, plus headlines from PC gaming outlets. Patches are highlighted; every link goes to the original source.</p></section>
<label class="toggle"><input type="checkbox" id="tracked-only"> Show tracked games only</label>
<div class="sec-head"><h2>Patches &amp; tracked games</h2></div>
<section class="panel">{news_list([i for i in news.get("items", []) if i.get("games")])}</section>
<div class="sec-head around"><h2>Around PC gaming</h2></div>
<section class="panel around">{news_list(around_pc(news.get("items", [])), AROUND_LIMIT)}</section>
<script>(function(){{var c=document.getElementById('tracked-only'),k='modsafe-tracked-only';try{{c.checked=localStorage.getItem(k)==='1';}}catch(e){{}}
function a(){{[].forEach.call(document.querySelectorAll('.around'),function(x){{x.hidden=c.checked;}});try{{localStorage.setItem(k,c.checked?'1':'0');}}catch(e){{}}}}c.addEventListener('change',a);a();}})();</script>
<p class="disclaimer">Sources: Steam announcements{", " + srcs if srcs else ""}. Updated {esc(fmt_date(news.get("generated_at")))} (UTC). Headlines belong to their publishers.</p>"""
    return page_shell(f"Latest gaming news — {SITE_NAME}", "Patch notes for modded games and PC gaming headlines, updated several times a day.",
                      "/news/", "news", body, extra_jsonld=[breadcrumb_ld([("Home", "/"), ("News", "/news/")])])


GENERAL_FAQ = [
    {"q": "Is it safe to update my game with mods installed?",
     "a": "Vanilla patches are safe, but mods built on script extenders or loaders (SKSE, F4SE, RED4ext, BG3SE, SMAPI, BepInEx, Fabric/Forge) often break until those frameworks update. Check your game's page here first, or hold the update."},
    {"q": "How do I stop Steam from auto-updating a modded game?",
     "a": "Steam has no 'never update' option. Set the game's Properties > Updates to 'Wait until I launch the game', then launch through "
          "your script extender or mod manager, or play in Offline Mode. Some games keep older versions under Game Versions & Betas. "
          "Full guide with Steam Deck steps, rollbacks and backups: modsafe.app/guides/stop-steam-auto-updates/"},
    {"q": "What do the status labels mean?", "a": STATUS_EXPLAINER},
    {"q": "Why are some frameworks marked “Check manually”?",
     "a": "Some core mods (for example Address Library and Buffout 4) are only distributed on Nexus Mods, and some tools (like Navigraph) have no public release feed. ModSafe doesn't scrape Nexus Mods, so these are linked for you to check instead of guessed at, and they're left out of the verdict."},
    {"q": "Where does the data come from?",
     "a": "Steam Web API news (official announcements), Mojang's version manifest, GitHub releases/tags and issues, the Thunderstore package API, Fabric meta, Forge promotions, NeoForge Maven, the Modrinth API, the Decky plugin store API, the official silverlock.org script extender pages, fsuipc.com, Steam public-build info (api.steamcmd.net) and the Atlan patcher's build list. GTA V, console mods and hotfixes announced only off Steam use hand-checked records with cited sources (dates shown on each page). Refreshed automatically every 6 hours."},
    {"q": "Which games are covered?", "a": ", ".join(g["name"] for g in GAMES) + "."},
    {"q": "Can I get notified when a verdict changes?",
     "a": "Yes, with RSS/Atom feeds: no account and no email. modsafe.app/feed.xml covers every game, and each game has its own feed "
          "(for example modsafe.app/cyberpunk-2077/feed.xml). A new entry appears when a new patch is detected, the verdict changes, or a "
          "patch-sensitive framework changes status. Add a feed to any feed reader, or to a Discord server with an RSS bot such as MonitoRSS. "
          "The link is in the Follow section of every game page."},
    {"q": "Can I show a game's mod status on my mod page or README?",
     "a": "Yes. Every game has a live SVG status badge at modsafe.app/badge/<game>.svg (for example modsafe.app/badge/skyrim-se.svg) showing "
          "the current patch and verdict in ModSafe's colours. Copy the Markdown, HTML or BBCode snippet from the Follow & embed section of the game page. "
          "A shields.io endpoint (modsafe.app/badge/<game>.json) is also available if you prefer shields.io styling."},
]


def build_faq() -> str:
    arts = "".join(faq_article(it, "h2", i) for i, it in enumerate(GENERAL_FAQ))
    body = f"""<section class="page-hero"><h1>FAQ</h1><p class="lede">Updating modded games after a patch.</p></section>
<section class="faq-list">{arts}</section>
<section class="panel"><p>Guide: <a href="{guides_mod.STEAM_GUIDE_PATH}">How to stop Steam auto-updating a game (and roll back)</a> · <a href="/guides/">All guides</a></p>
<p>Game-specific FAQs: {' · '.join(f'<a href="/{g["slug"]}/#faq-heading">{esc(g["name"])}</a>' for g in GAMES)}</p></section>"""
    return page_shell(f"FAQ — {SITE_NAME}", "Is it safe to update a modded game? How ModSafe decides — FAQ.", "/faq/", "faq", body,
                      extra_jsonld=[faq_ld(GENERAL_FAQ)])


def build_steam_updates_guide() -> str:
    faq = guides_mod.STEAM_GUIDE_FAQ
    body = guides_mod.steam_guide_body("".join(faq_article(it, "h3") for it in faq))
    path = guides_mod.STEAM_GUIDE_PATH
    b = guides_mod.load_branches()
    article = {"@context": "https://schema.org", "@type": "TechArticle", "headline": guides_mod.STEAM_GUIDE_TITLE,
               "description": guides_mod.STEAM_GUIDE_DESC, "url": f"{SITE_URL}{path}", "dateModified": b["verified"],
               "image": f"{SITE_URL}/og/{guides_mod.STEAM_GUIDE_OG}", "author": {"@type": "Organization", "name": SITE_NAME},
               "publisher": {"@type": "Organization", "name": SITE_NAME, "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/img/logo.png"}}}
    return page_shell(f"{guides_mod.STEAM_GUIDE_TITLE} — ModSafe", guides_mod.STEAM_GUIDE_DESC, path, "guides", body,
                      extra_jsonld=[article, faq_ld(faq), breadcrumb_ld([("Home", "/"), ("Guides", "/guides/"),
                                                                         ("Stop Steam auto-updates", path)])],
                      og=guides_mod.STEAM_GUIDE_OG)


def build_guides_index() -> str:
    installs = [g for g in GAMES if mods_mod.load_guide(g["slug"])]
    return page_shell("Modding guides: hold Steam updates, roll back, install mods — ModSafe",
                      "Guides for modded PC games: stop Steam auto-updating a game, roll back a patch, and install mods step by step.",
                      "/guides/", "guides", guides_mod.guides_index_body(installs),
                      extra_jsonld=[breadcrumb_ld([("Home", "/"), ("Guides", "/guides/")])], og=guides_mod.GUIDES_OG)


ROLLBACK_VERDICTS = ("Just patched, wait", "Breakage reported", "Not ported yet")


def rollback_callout(game: dict, data: dict) -> str:
    """Shown on Steam game pages while the verdict says mods may be broken: how to get the old version back."""
    if data.get("verdict") not in ROLLBACK_VERDICTS or not game.get("steam_appid") \
            or game.get("kind_label") == "platform" or game.get("kind") == "minecraft":
        return ""
    g = guides_mod.STEAM_GUIDE_PATH
    return f"""<section class="panel rollback" id="rollback" aria-labelledby="rollback-heading">
<h2 id="rollback-heading">⏪ Already updated and your mods broke?</h2>
<p>{esc(guides_mod.branch_summary(game["slug"]))}</p>
<p class="rb-links"><a class="btn ghost" href="{g}#branches">Old versions on Steam</a> <a class="btn ghost" href="{g}#rollback">Roll back with download_depot</a> <a class="btn ghost" href="{g}#backup">Back up before the next patch</a></p>
<p class="muted">Not updated yet? <a href="{g}#wait-until-launch">Stop Steam auto-updating {esc(game["short"])}</a> until the frameworks catch up.</p>
</section>"""


LOCAL_TIME_JS = """<script>
(function(){[].forEach.call(document.querySelectorAll('time.utc'),function(t){var d=new Date(t.getAttribute('datetime'));if(isNaN(d))return;var s=d.toLocaleString([], {month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});var l=t.parentNode.querySelector('.local');if(l){l.textContent='· '+s+' your time';}});})();
</script>"""


def patch_rows(items: list[dict], now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    out = []
    for i in items:
        g = i["game"]
        slug = g["slug"]
        fresh = (now - i["at"]).total_seconds() < 7 * 86400
        src = (f' · <a href="{esc(i["url"])}" rel="noopener external" title="{esc(i["title"])}">patch notes</a>' if i.get("url")
               else ' · <span class="muted">no patch notes</span>')
        if i["current"]:
            right = f'{badge(i["verdict"])}<span class="pt-note">Current verdict</span>'
        elif i.get("verdict"):
            right = f'{badge(i["verdict"])}<span class="pt-note">Last verdict before {esc(i.get("superseded_by") or "the next patch")}</span>'
        else:
            right = f'<span class="chip">Superseded by {esc(i.get("superseded_by") or "a newer patch")}</span>'
        cls = status_class(i["verdict"]) if i["current"] and i.get("verdict") else "old"
        out.append(f"""<li class="pt-row v-{cls}">
<a class="pt-art" href="/{slug}/" tabindex="-1" aria-hidden="true"><img src="{busted(game_img(slug))}" width="112" height="64" loading="lazy" decoding="async" alt=""></a>
<div class="pt-main"><p class="pt-game"><a href="/{slug}/">{esc(g["name"])}</a>{' <span class="pt-new">NEW</span>' if fresh else ''}</p>
<p class="pt-patch">{patch_label_html(i["label"])}{src}</p>
<p class="pt-time"><time class="utc" datetime="{i["at"].strftime('%Y-%m-%dT%H:%M:%SZ')}">{esc(patches_mod.fmt_utc(i["at"]))}</time> <span class="local muted"></span></p></div>
<div class="pt-verdict">{right}</div>
</li>""")
    return "".join(out) or '<li class="muted">No patches in this window.</li>'


def event_rows(events: list[dict]) -> str:
    out = []
    for ev in events:
        g, e = ev["game"], ev["entry"]
        kind = {"new-patch": "🛠 New patch", "verdict": "⚖ Verdict", "framework": "🔧 Framework"}.get(ev["kind"], "Update")
        out.append(f"""<li><span class="badge {status_class(e.get('verdict') or '')}">{esc(kind)}</span> <a href="/{g['slug']}/">{esc(ev['title'])}</a>
<span class="nmeta"><time class="utc" datetime="{ev['at'].strftime('%Y-%m-%dT%H:%M:%SZ')}">{esc(patches_mod.fmt_utc(ev['at']))}</time> <span class="local muted"></span></span></li>""")
    return f'<ul class="news">{"".join(out) or "<li class=muted>No verdict changes yet.</li>"}</ul>'


def build_patches_page(games_data, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    items = patches_mod.collect_patches(games_data, now=now)
    events = patches_mod.recent_events(games_data)
    c = patches_mod.counts(items, now)
    holding = [(g, d) for g, d in games_data if d["verdict"] in ROLLBACK_VERDICTS]
    log_at = [e["at"] for _, d in games_data for e in d.get("verdict_log") or [] if e.get("at")]
    log_start = fmt_date(min(log_at)) if log_at else "recently"
    newest = items[0] if items else None
    hero_slug = newest["game"]["slug"] if newest else "cyberpunk-2077"
    groups, order = {}, []
    for i in items:
        k = f"{i['at'].strftime('%B')} {i['at'].year}"
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(i)
    months = "".join(f'<div class="sec-head pt-month"><h3>{esc(k)}</h3><span class="muted">{len(groups[k])} patch{"es" if len(groups[k]) != 1 else ""}</span></div>'
                     f'<section class="panel"><ul class="pt-list">{patch_rows(groups[k], now)}</ul></section>' for k in order)
    hold_html = (" ".join(f'<a class="chip" href="/{g["slug"]}/">{esc(g["short"])}: {esc(d["verdict"])}</a>' for g, d in holding)
                 if holding else '<span class="muted">None right now. Every tracked game is Safe or Likely safe.</span>')
    latest_line = (f'Latest drop: <a href="/{newest["game"]["slug"]}/">{esc(newest["game"]["name"])} {esc(newest["label"])}</a>, '
                   f'{esc(patches_mod.fmt_utc(newest["at"]))}.') if newest else ""
    body = f"""<p class="crumbs"><a href="/">Home</a> › Patches</p>
<section class="home-hero pt-hero" style="--hero:url('{busted(game_img(hero_slug, "hero"))}')">
<p class="eyebrow">Patch radar · all {len(games_data)} games</p>
<h1>Every patch. <em>Every game.</em></h1>
<p class="lede">The newest game patches across everything ModSafe tracks, with the verdict for your mods. {latest_line}</p>
<div class="stats"><div><strong>{c['7d']}</strong>patches in 7 days</div><div><strong>{c['30d']}</strong>patches in 30 days</div><div><strong>{len(holding)}</strong>games on hold now</div></div>
</section>
<section class="panel pt-hold"><h2 class="panel-h">⏳ Hold the update</h2><p>{hold_html}</p>
<p class="muted">Already patched? <a href="{guides_mod.STEAM_GUIDE_PATH}#rollback">How to roll back a Steam game</a> · <a href="{guides_mod.STEAM_GUIDE_PATH}">Stop Steam auto-updates</a></p></section>
<div class="sec-head"><h2 id="timeline">Patch timeline</h2><a href="/feed.xml">Atom feed →</a></div>
<p class="muted">Newest first, last 12 months (up to {patches_mod.PATCH_LIMIT} patches). Times are when the official patch post went live, in UTC. Older patches are on each game's history page.</p>
{months}
<div class="sec-head"><h2 id="changes">Recent verdict changes</h2><a href="/feed.xml">Atom feed →</a></div>
<p class="muted">New patches, verdict flips and framework catch-ups, as ModSafe first saw them (UTC).</p>
<section class="panel">{event_rows(events)}</section>
<p class="disclaimer">Built from ModSafe's own data: each game's official patch source (the “patch notes” link on each row) and our verdict log, kept since {esc(log_start)} and refreshed every 6 hours. “Last verdict” is the last status we recorded before the next patch replaced it; patches from before the log show no verdict. Raw data: <a href="/api/v1/status.json">API</a> · <a href="/games.json">games.json</a>.</p>
"""
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": "Recent game patches tracked by ModSafe",
          "itemListOrder": "https://schema.org/ItemListOrderDescending",
          "itemListElement": [{"@type": "ListItem", "position": n + 1, "name": f"{i['game']['name']} {i['label']}",
                               "url": f"{SITE_URL}/{i['game']['slug']}/"} for n, i in enumerate(items[:20])]}
    desc = (f"{c['7d']} game patches in the last 7 days and {c['30d']} in 30 days across {len(games_data)} modded games, "
            "with the current mod verdict for each: is it safe to update?")
    return page_shell("Recent game patches & mod status — patch timeline for every game — ModSafe", _clip(desc), "/patches/", "patches",
                      body + LOCAL_TIME_JS, extra_jsonld=[ld, breadcrumb_ld([("Home", "/"), ("Patches", "/patches/")])],
                      og="patches.png")


NOT_FOUND_HERO = "elden-ring"
NOT_FOUND_PICKS = ("cyberpunk-2077", "skyrim-se", "baldurs-gate-3", "fallout-4", "stardew-valley", "minecraft")


def build_404(games_data) -> str:
    """Top-level 404.html: Cloudflare Pages serves it with a real 404 status for unknown paths
    (instead of the SPA fallback to the home page). Served at any depth, so every URL is root-absolute."""
    picks = [(g, d) for g, d in games_data if g["slug"] in NOT_FOUND_PICKS]
    body = f"""
<section class="home-hero nf-hero" style="--hero:url('{game_img(NOT_FOUND_HERO, "hero")}')">
<p class="eyebrow">Error 404 · Respawn point</p>
<h1>You <em>died</em>. Well, this page did.</h1>
<p class="lede">This URL isn't on the map. It may have been moved, renamed or never existed. Your save is fine: pick a checkpoint below.</p>
<div class="hero-actions"><a class="btn" href="/">🏠 Home</a> <a class="btn ghost" href="/games/">🎮 All games</a> <a class="btn ghost" href="/guides/">📖 Guides</a> <a class="btn ghost" href="/faq/">❓ FAQ</a></div>
</section>
<div class="sec-head"><h2>Popular checkpoints</h2><a href="/games/">All games →</a></div>
<section class="game-grid" aria-label="Popular games">
{game_cards(picks, compact=True)}
</section>
"""
    return page_shell("Page not found (404) — ModSafe", "This page doesn't exist on ModSafe.", "/404.html", "",
                      body, noindex=True)


OG_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#0a0e17"/>
<text x="80" y="280" fill="#00f0ff" font-family="system-ui,sans-serif" font-size="64" font-weight="700">ModSafe</text>
<text x="80" y="360" fill="#e8eef8" font-family="system-ui,sans-serif" font-size="36">Is it safe to update? Mod framework status after game patches</text>
</svg>
"""


def build_hub_page(hub: dict, editions: list[tuple[dict, dict]]) -> str:
    """/gta-v/: a short 'which edition do I have?' page linking to each edition's own pages. Kept deliberately
    thin (no verdict text, framework cards or FAQ duplicated from the edition pages)."""
    slug, short = hub["slug"], hub["short"]
    rows = []
    for g, d in editions:
        links = " · ".join(f'<a href="{u}">{esc(t)}</a>' for _, u, t in hub_pages(g, d))
        rows.append(f'<li><strong><a href="/{g["slug"]}/">{esc(g["name"])}</a></strong> {badge(d["verdict"])} '
                    f'<span class="muted">{esc(d["game"]["latest_patch"]["label"])}</span><br>{links}</li>')
    which = "".join(f'<div class="ed-id"><h3><a href="/{g["slug"]}/">{esc(edition_label(g))}</a></h3><dl>'
                    f"<dt>Steam library name</dt><dd>{esc(g['name'])}</dd>"
                    f"<dt>Executable</dt><dd><code>{esc(g.get('exe') or '')}</code></dd>"
                    f"<dt>Tell-tale</dt><dd>{esc(g.get('edition_hint') or '')}</dd>"
                    f"<dt>Steam app ID</dt><dd>{g.get('steam_appid')}</dd></dl></div>" for g, _ in editions)
    body = f"""
<p class="crumbs"><a href="/">Home</a> › <a href="/games/">Games</a> › {esc(short)}</p>
<section class="page-hero"><h1>{esc(short)} mods: Legacy or Enhanced?</h1>
<p class="lede">Rockstar patches the two PC editions of {esc(hub['name'])} separately, and Script Hook V can support one before
the other. ModSafe gives each edition its own verdict, install guide, mod list and patch history. Pick yours.</p></section>
<div class="sec-head"><h2 id="editions">Choose your edition</h2></div>
<section class="game-grid" aria-label="{esc(short)} editions">{game_cards(editions, compact=True)}</section>
<section class="panel"><ul class="hub-list">{''.join(rows)}</ul></section>
<div class="sec-head"><h2 id="which">Which edition do I have?</h2></div>
<section class="panel guide"><div class="ed-ids">{which}</div>
<p class="muted">Bought GTA V on Steam before March 2025? You may own both: Steam lists them as two separate games. The Rockstar Games Launcher and Epic also show the edition in the game's name.</p></section>
<p class="note" role="note"><strong>⚠ {esc(hub.get('note') or '')}</strong></p>
<p class="disclaimer">Apps and bots: <a href="/{slug}/status.json">/{slug}/status.json</a>, <a href="/{slug}/feed.xml">/{slug}/feed.xml</a> and
<a href="/badge/{slug}.svg">/badge/{slug}.svg</a> still work and combine both editions (the worse verdict wins). New integrations should use
{' and '.join(f'<a href="/{g["slug"]}/status.json">/{g["slug"]}/status.json</a>' for g, _ in editions)}; in <a href="/api/v1/status.json">api/v1</a> the
<code>{esc(slug)}</code> entry is marked <code>deprecated</code> with <code>superseded_by</code>.</p>
<section class="links" aria-label="Related pages">{" ".join(f'<a href="/{g["slug"]}/">🎮 {esc(g["short"])}</a>' for g, _ in editions)} <a href="/guides/stop-steam-auto-updates/">🛑 Stop Steam auto-updates</a> <a href="/games/">🎮 All games</a></section>
"""
    itemlist = {"@context": "https://schema.org", "@type": "ItemList", "name": f"{hub['name']} PC editions",
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": g["name"], "url": f"{SITE_URL}/{g['slug']}/"}
                                    for i, (g, _) in enumerate(editions)]}
    return page_shell(f"{short} mod status: Legacy or Enhanced? — ModSafe",
                      _clip(f"Is it safe to update {hub['name']} with mods? Pick your PC edition: "
                            + " · ".join(f"{edition_label(g)}: {d['verdict']}" for g, d in editions)
                            + ". Each has its own verdict, install guide and mod list."),
                      f"/{slug}/", slug, body + AGO_JS,
                      extra_jsonld=[itemlist, breadcrumb_ld([("Games", "/"), (short, f"/{slug}/")])])


def hub_editions(hub_slug: str, games_data) -> list[tuple[dict, dict]]:
    by = {g["slug"]: (g, d) for g, d in games_data}
    return [by[s] for s in HUBS.get(hub_slug, []) if s in by]


def build_llms_txt(games_data) -> str:
    lines = [f"# {SITE_NAME}", "", f"> {SITE_DESC}", "", f"Site: {SITE_URL}/", f"Index JSON: {SITE_URL}/games.json",
             f"Stable API (v1, CORS-enabled, all games + per-mod verdicts): {SITE_URL}/api/v1/status.json",
             f"Legacy Cyberpunk JSON: {SITE_URL}/status.json",
             f"Atom feed of new patches and verdict changes (all games): {SITE_URL}/feed.xml (per game: {SITE_URL}/<slug>/feed.xml)",
             f"Status badges (SVG, per game): {SITE_URL}/badge/<slug>.svg (shields.io endpoint JSON: {SITE_URL}/badge/<slug>.json)", "",
             "Status meanings: " + STATUS_EXPLAINER, ""]
    for game, data in games_data:
        p = data["game"]["latest_patch"]
        lines += [f"## {game['name']}", f"- Page: {SITE_URL}/{game['slug']}/", f"- JSON: {SITE_URL}/{game['slug']}/status.json",
                  f"- Feed (Atom): {SITE_URL}/{game['slug']}/feed.xml", f"- Badge: {SITE_URL}/badge/{game['slug']}.svg",
                  f"- Latest patch: {p['label']} ({p.get('published_at')}) {p.get('url')}", f"- Verdict: {data['verdict']}",
                  f"- Generated (UTC): {data.get('generated_at')}"]
        if (mm := mods_mod.load_mods(game["slug"])):
            lines.append(f"- Essential mods: {SITE_URL}/{game['slug']}/mods/ (JSON: {SITE_URL}/{game['slug']}/mods.json): "
                         + "; ".join(f"{m['name']} {m['url']}" for m in mm["mods"]))
        if (cm := load_console_mods().get(game["slug"])):
            lines.append(f"- Console mods ({'/'.join(cm['platforms'])}, {cm['system']}): latest patch disabled console mods? {cm['answer']}. "
                         f"{cm['update']['label']} ({cm['update']['date']}) {cm['update']['url']}; hand-maintained, last verified {cm['last_verified']}")
        if mods_mod.load_guide(game["slug"]):
            lines.append(f"- Install guide: {SITE_URL}/{game['slug']}/install/")
        for fw in data["frameworks"]:
            tr = "" if fw.get("tracked", True) else " [not auto-tracked]"
            lines.append(f"  - {fw['name']}: {fw['status']}{tr}; release {fw.get('release_tag')} {fw.get('release_published_at') or ''}; {fw.get('reason')}")
        lines.append("")
    for hub in COMPAT_GAMES:
        eds = hub_editions(hub["slug"], games_data)
        if not eds:
            continue
        lines += [f"## {hub['name']} (hub)", f"- Hub page (pick an edition): {SITE_URL}/{hub['slug']}/",
                  "- Editions: " + "; ".join(f"{g['name']} {SITE_URL}/{g['slug']}/ (verdict: {d['verdict']})" for g, d in eds),
                  f"- Compatibility endpoints (both editions combined, worse verdict wins; deprecated, prefer the edition entries): "
                  f"{SITE_URL}/{hub['slug']}/status.json, {SITE_URL}/{hub['slug']}/feed.xml, {SITE_URL}/badge/{hub['slug']}.svg; "
                  f"api/v1 entry id '{hub['slug']}' has deprecated: true and superseded_by: {[g['slug'] for g, _ in eds]}", ""]
    lines += ["## Pages", f"- Patch timeline (newest game patches across all games, with verdicts and recent verdict changes): {SITE_URL}/patches/",
              f"- FAQ: {SITE_URL}/faq/", f"- Guides: {SITE_URL}/guides/",
              f"- Guide: How to stop Steam auto-updating a game (Wait until I launch, Offline Mode, Steam Deck, Game Versions & Betas, "
              f"download_depot/DepotDownloader rollback, backups): {SITE_URL}{guides_mod.STEAM_GUIDE_PATH}", "",
              "Statuses are inferred from public release data; not official developer guidance.", ""]
    return "\n".join(lines)


INDEXNOW_KEY = "1ee54d1d3f66ad12c8299573e61fc9ac"  # public IndexNow key; must match tools/indexnow.py


def build_robots() -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"


def _game_data(slug: str) -> dict:
    f = DATA_DIR / f"{slug}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def build_redirects(games_data) -> str:
    """Static rules plus a 301 to the game page for games whose history is too short to get its own page."""
    extra = [f"/{g['slug']}/history{t} /{g['slug']}/ 301" for g, d in games_data if not has_history(d) for t in ("", "/")]
    return REDIRECTS + ("# Games without enough patch history for a history page\n" + "\n".join(extra) + "\n" if extra else "")


def sitemap_urls() -> list[str]:
    urls = ["/", "/games/", "/patches/", "/news/", "/faq/", "/guides/", guides_mod.STEAM_GUIDE_PATH]
    urls += [f"/{h}/" for h in HUBS]
    for g in GAMES:
        urls.append(f"/{g['slug']}/")
        if has_history(_game_data(g["slug"])):
            urls.append(f"/{g['slug']}/history/")
        if mods_mod.load_mods(g["slug"]):
            urls.append(f"/{g['slug']}/mods/")
        if mods_mod.load_guide(g["slug"]):
            urls.append(f"/{g['slug']}/install/")
    return urls + ["/games.json", "/api/v1/status.json", "/llms.txt"]


def build_sitemap() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    parts += [f"  <url><loc>{esc(SITE_URL + u)}</loc><lastmod>{now}</lastmod></url>" for u in sitemap_urls()]
    return "\n".join(parts + ["</urlset>"]) + "\n"


REDIRECTS = """# Legacy Cyberpunk-only URLs (pre multi-game)
/history /cyberpunk-2077/history/ 301
/history/ /cyberpunk-2077/history/ 301
/cyberpunk /cyberpunk-2077/ 301
/skyrim /skyrim-se/ 301
/bg3 /baldurs-gate-3/ 301
/stardew /stardew-valley/ 301
# GTA V split into per-edition pages (2026-10-29); /gta-v/ is the hub. It never had a history page.
/gta-v/history /gta-v/ 301
/gta-v/history/ /gta-v/ 301
# Discontinued pages
/newsletter / 301
/newsletter/ / 301
"""


def games_index(games_data) -> dict:
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "games": [{"slug": g["slug"], "name": g["name"], "verdict": d["verdict"],
                       **({"edition": g["edition"], "hub": g.get("hub")} if g.get("edition") else {}),
                       **({"deprecated": True, "superseded_by": list(g.get("editions") or [])} if g.get("compat") else {}),
                       "latest_patch": {k: d["game"]["latest_patch"].get(k) for k in ("label", "version", "published_at", "url")},
                       "page": f"{SITE_URL}/{g['slug']}/", "json": f"{SITE_URL}/{g['slug']}/status.json",
                       "frameworks": [{"id": f["id"], "name": f["name"], "status": f["status"], "tracked": f.get("tracked", True),
                                       "release_tag": f.get("release_tag")} for f in d["frameworks"]]}
                      for g, d in list(games_data) + compat_data()]}


def compat_data() -> list[tuple[dict, dict]]:
    """Combined records kept for existing clients (gta-v): (game, data) for those with data on disk."""
    return [(g, _game_data(g["slug"])) for g in COMPAT_GAMES if _game_data(g["slug"])]


# ---- Public API v1 (/api/v1/status.json) -------------------------------------------------------------------------
# Stable, versioned contract for third-party clients (e.g. the ModSafe Decky Loader plugin). Additive changes only;
# a breaking change ships as /api/v2/. Served with Access-Control-Allow-Origin: * (see HEADERS).
API_VERSION = 1
VERDICT_IDS = {
    "Safe": "safe",
    "Likely safe": "likely-safe",
    "Just patched, wait": "wait",
    "Breakage reported": "broken",
    "Not ported yet": "not-ported",
    "No data": "no-data",
    "Not affected by patches": "not-affected",
    "Check manually": "manual",
}
# Lower = worse; lets clients sort or pick a badge colour without hard-coding labels.
VERDICT_SEVERITY = {"broken": 0, "not-ported": 1, "wait": 2, "no-data": 3, "manual": 4, "likely-safe": 5,
                    "not-affected": 6, "safe": 7}


def verdict_id(label: str | None) -> str:
    if not label:
        return "no-data"
    return VERDICT_IDS.get(label) or (re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "no-data")


def api_v1_status(games_data, today=None, upcoming: dict | None = None, compat=None) -> dict:
    """compat: combined records (gta-v) appended after the real games with deprecated/superseded_by; additive only,
    so v1 clients that look up 'gta-v' keep working. Defaults to the records on disk."""
    up_all = upcoming if upcoming is not None else load_upcoming()
    games = []
    for g, d in list(games_data) + list(compat_data() if compat is None else compat):
        lp = (d.get("game") or {}).get("latest_patch") or {}
        appids = sorted({int(a) for a in ([g.get("steam_appid")] + list((g.get("steam_appids") or {}).values())) if a})
        vid = verdict_id(d.get("verdict"))
        up = active_upcoming(g["slug"], d, today=today, upcoming=up_all)
        mods = []
        for fw in d.get("frameworks", []):
            mid = verdict_id(fw.get("status"))
            mods.append({
                "id": fw.get("id"), "name": fw.get("name"), "short": fw.get("short") or fw.get("name"),
                "verdict": mid, "verdict_label": fw.get("status"), "severity": VERDICT_SEVERITY.get(mid),
                "tracked": fw.get("tracked", True), "counts_toward_verdict": bool(fw.get("tracked", True)) and mid not in ("not-affected", "manual"),
                "reason": fw.get("reason"), "release": fw.get("release_tag"),
                "release_published_at": fw.get("release_published_at"), "release_url": fw.get("release_url"),
                "url": fw.get("url"),
            })
        games.append({
            "id": g["slug"], "name": g["name"], "short_name": g.get("short") or g["name"],
            "kind": "platform" if g.get("genre") == "Platform" else "game",
            "steam_appid": g.get("steam_appid"), "steam_appids": appids,
            "current_patch": {k: lp.get(k) for k in ("label", "version", "published_at", "url")},
            "verdict": vid, "verdict_label": d.get("verdict"), "severity": VERDICT_SEVERITY.get(vid),
            "updated_at": d.get("generated_at"),
            "upcoming_patch": ({k: up.get(k) for k in ("label", "version", "date", "source")} if up else None),
            "page_url": f"{SITE_URL}/{g['slug']}/", "json_url": f"{SITE_URL}/{g['slug']}/status.json",
            "mods": mods,
            "edition": g.get("edition"), "hub": g.get("hub"),
            "deprecated": bool(g.get("compat")),
            "superseded_by": list(g.get("editions") or []) if g.get("compat") else None,
        })
    updated = [x["updated_at"] for x in games if x["updated_at"]]
    return {
        "api_version": API_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "data_updated_at": max(updated) if updated else None,
        "site": SITE_URL + "/",
        "docs": f"{SITE_URL}/llms.txt",
        "disclaimer": "Statuses are inferred from public release data; they are not guarantees. Verify on each project's page before updating.",
        "verdicts": [{"id": v, "label": k, "severity": VERDICT_SEVERITY[v]} for k, v in VERDICT_IDS.items()],
        "games": games,
    }


MENU_JS = "<script>(function(){var d=document.querySelector('.games-menu');if(!d)return;document.addEventListener('click',function(e){if(d.open&&!d.contains(e.target))d.open=false;});document.addEventListener('keydown',function(e){if(e.key==='Escape'&&d.open){d.open=false;d.querySelector('summary').focus();}});})();</script>"
COPY_JS = ("<script>document.addEventListener('click',function(e){var b=e.target.closest('.copy');if(!b)return;"
           "var i=document.getElementById(b.dataset.for);if(!i)return;i.select();var done=function(){var t=b.textContent;b.textContent='Copied';"
           "setTimeout(function(){b.textContent=t;},1500);};if(navigator.clipboard){navigator.clipboard.writeText(i.value).then(done,function(){document.execCommand('copy');done();});}"
           "else{document.execCommand('copy');done();}});</script>")
CSS_VER = __import__("hashlib").sha256(CSS.encode()).hexdigest()[:10]
HEADERS = """/*
  X-Content-Type-Options: nosniff
/*.html
  Cache-Control: public, max-age=0, must-revalidate
/
  Cache-Control: public, max-age=0, must-revalidate
/styles.css
  Cache-Control: public, max-age=31536000, immutable
/fonts/*
  Cache-Control: public, max-age=31536000, immutable
/img/*
  Cache-Control: public, max-age=604800
/og/*
  Cache-Control: public, max-age=86400
/api/*
  Access-Control-Allow-Origin: *
  Access-Control-Allow-Methods: GET, HEAD, OPTIONS
  Cache-Control: public, max-age=300
/feed.xml
  Content-Type: application/atom+xml; charset=utf-8
  Cache-Control: public, max-age=600
  X-Robots-Tag: noindex
/:slug/feed.xml
  Content-Type: application/atom+xml; charset=utf-8
  Cache-Control: public, max-age=600
  X-Robots-Tag: noindex
/badge/*
  Cache-Control: public, max-age=900
  X-Robots-Tag: noindex
/badge/*.svg
  Content-Type: image/svg+xml; charset=utf-8
/status.json
  X-Robots-Tag: noindex
/:slug/status.json
  X-Robots-Tag: noindex
/:slug/mods.json
  X-Robots-Tag: noindex
"""
# X-Robots-Tag: machine-readable files that are NOT in the sitemap get noindex (one
# matching rule per path, or Pages joins duplicates as "noindex, noindex").
# /api/v1/status.json, /games.json and /llms.txt stay indexable: they are listed in
# the sitemap on purpose, and noindex + sitemap = "Submitted URL marked noindex".


def build_routes() -> str:
    """dist/_routes.json: which paths invoke functions/_middleware.js (canonical-host
    redirect). Free plan = 100k Function requests/day, so high-volume static/machine
    paths (polled feeds, API, badges, assets) bypass the Function entirely."""
    exclude = ["/api/*", "/badge/*", "/fonts/*", "/img/*", "/og/*", "/styles.css",
               "/feed.xml", "/status.json", "/games.json"]
    exclude += [f"/{g['slug']}/feed.xml" for g in GAMES + COMPAT_GAMES]
    return json.dumps({"version": 1, "include": ["/*"], "exclude": exclude}, indent=2) + "\n"


def shields_endpoint(game: dict, data: dict) -> dict:
    """https://shields.io/badges/endpoint-badge schema, for people who prefer shields.io styling."""
    return {"schemaVersion": 1, "label": badges.badge_label(game, data), "message": data.get("verdict") or "No data",
            "color": badges.COLORS.get(status_class(data.get("verdict") or ""), badges.COLORS["unknown"]).lstrip("#"),
            "labelColor": badges.LEFT_BG.lstrip("#"), "cacheSeconds": 900}


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


def load_games() -> list[tuple[dict, dict]]:
    out = []
    for g in GAMES:
        f = DATA_DIR / f"{g['slug']}.json"
        if not f.exists():
            raise SystemExit(f"Missing {f}; run ./update first")
        out.append((g, json.loads(f.read_text(encoding="utf-8"))))
    return out


def main() -> int:
    games_data = load_games()
    print(f"Building site → {DIST} (SITE_URL={SITE_URL})")
    if DIST.exists():
        for p in DIST.rglob("*"):
            if p.is_file():
                p.unlink()
        for p in sorted((p for p in DIST.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            if not any(p.iterdir()):
                p.rmdir()  # e.g. a history/ folder for a game that no longer gets one
    write(DIST / "index.html", build_home(games_data))
    for g, d in games_data:
        write(DIST / g["slug"] / "index.html", build_game_page(g, d))
        if has_history(d):
            write(DIST / g["slug"] / "history" / "index.html", build_game_history(g, d))
        write(DIST / g["slug"] / "status.json", json.dumps(d, indent=2) + "\n")
        write(DIST / g["slug"] / "feed.xml", feeds.game_feed(g, d, SITE_URL))
        write(DIST / "badge" / f"{g['slug']}.svg", badges.game_badge(g, d, status_class(d["verdict"])))
        write(DIST / "badge" / f"{g['slug']}.json", json.dumps(shields_endpoint(g, d), indent=2, ensure_ascii=False) + "\n")
        if (m := mods_mod.load_mods(g["slug"])):
            write(DIST / g["slug"] / "mods" / "index.html", build_mods_page(g, d, m))
            write(DIST / g["slug"] / "mods.json", json.dumps(m, indent=2, ensure_ascii=False) + "\n")
        if (md := mods_mod.load_guide(g["slug"])):
            write(DIST / g["slug"] / "install" / "index.html", build_install_page(g, d, md))
        if g["slug"] == "cyberpunk-2077":
            # Legacy endpoint kept for existing consumers (same shape as v1 + extra fields).
            legacy = json.loads(json.dumps(d))
            legacy["game"]["latest_patch"]["version"] = legacy["game"]["latest_patch"].get("version")
            write(DIST / "status.json", json.dumps(legacy, indent=2) + "\n")
    for hub, d in compat_data():
        # /gta-v/: hub page + the combined compat endpoints (status.json, feed, badges) for existing clients.
        write(DIST / hub["slug"] / "index.html", build_hub_page(hub, hub_editions(hub["slug"], games_data)))
        write(DIST / hub["slug"] / "status.json", json.dumps(d, indent=2) + "\n")
        write(DIST / hub["slug"] / "feed.xml", feeds.game_feed(hub, d, SITE_URL))
        write(DIST / "badge" / f"{hub['slug']}.svg", badges.game_badge(hub, d, status_class(d["verdict"])))
        write(DIST / "badge" / f"{hub['slug']}.json", json.dumps(shields_endpoint(hub, d), indent=2, ensure_ascii=False) + "\n")
    write(DIST / "games" / "index.html", build_games_index(games_data))
    write(DIST / "patches" / "index.html", build_patches_page(games_data))
    write(DIST / "news" / "index.html", build_news_page())
    write(DIST / "faq" / "index.html", build_faq())
    write(DIST / "guides" / "index.html", build_guides_index())
    write(DIST / "guides" / "stop-steam-auto-updates" / "index.html", build_steam_updates_guide())
    write(DIST / "404.html", build_404(games_data))
    import shutil
    shutil.copytree(STATIC, DIST, dirs_exist_ok=True)
    write(DIST / "styles.css", CSS)
    write(DIST / "og-default.svg", OG_SVG)
    write(DIST / "games.json", json.dumps(games_index(games_data), indent=2) + "\n")
    write(DIST / "api" / "v1" / "status.json", json.dumps(api_v1_status(games_data), indent=2, ensure_ascii=False) + "\n")
    write(DIST / "feed.xml", feeds.site_feed(games_data, SITE_URL))
    write(DIST / "llms.txt", build_llms_txt(games_data))
    write(DIST / "robots.txt", build_robots())
    write(DIST / f"{INDEXNOW_KEY}.txt", INDEXNOW_KEY)
    write(DIST / "sitemap.xml", build_sitemap())
    write(DIST / "_redirects", build_redirects(games_data))
    write(DIST / "_headers", HEADERS)
    write(DIST / "_routes.json", build_routes())
    missing = missing_asset_refs(DIST)
    if missing:
        raise SystemExit("Build check failed: referenced images missing from dist/:\n  " +
                         "\n  ".join(f"{ref}  (in {page})" for ref, page in missing))
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
