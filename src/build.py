#!/usr/bin/env python3
"""Static site generator for ModSafe — multi-game mod framework patch status."""

from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "games"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from games import GAMES  # noqa: E402
DIST = ROOT / "dist"
STATIC = ROOT / "static"

# Cloudflare Web Analytics (cookie-free). Optional: only needed for a manually created
# Web Analytics site. If Analytics is enabled on the Pages project itself, Cloudflare
# injects the beacon automatically and this stays empty. The token is public (it ships in HTML).
CF_ANALYTICS_TOKEN = os.environ.get("CF_ANALYTICS_TOKEN", "").strip()
SITE_URL = os.environ.get("SITE_URL", "https://modsafe.app").rstrip("/")
SITE_NAME = "ModSafe — Mod Compatibility After Game Patches"
SITE_DESC = (
    "Is it safe to update? Live status of core mod frameworks and loaders (script extenders, "
    "BepInEx, SMAPI, Fabric/Forge) after each official game patch, for Cyberpunk 2077, Skyrim SE, "
    "Fallout 4, Baldur\'s Gate 3, Stardew Valley, Lethal Company, GTA V and Minecraft."
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


def base_head(title: str, description: str, path: str, extra_jsonld: list | None = None) -> str:
    canon = f"{SITE_URL}{path}"
    seg = path.strip("/").split("/")[0]
    alt_json = f"{SITE_URL}/{seg}/status.json" if any(g["slug"] == seg for g in GAMES) else f"{SITE_URL}/games.json"
    og_image = f"{SITE_URL}/og-default.svg"
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
    blocks = "\n".join(
        f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>'
        for b in jsonld
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canon)}">
<link rel="alternate" type="application/json" href="{esc(alt_json)}">
<link rel="alternate" type="text/plain" title="llms.txt" href="{esc(SITE_URL)}/llms.txt">
<meta name="robots" content="index,follow">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE_NAME)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canon)}">
<meta property="og:image" content="{esc(og_image)}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="theme-color" content="#07090f">
<link rel="preload" href="/fonts/chakra-petch-latin-700-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/styles.css">
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
.muted, .disclaimer, .nl-note { color: var(--muted); }
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
.nav a.cta { border: 1px solid var(--neon2); color: #ffd1dd; }
.nav a.cta:hover { background: rgba(255,42,109,.18); }

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
.stats { display: flex; flex-wrap: wrap; gap: 1.5rem; margin-top: 1.6rem; color: var(--muted); font-size: .92rem; }
.stats strong { display: block; font-family: var(--head); font-size: 1.6rem; color: var(--text); line-height: 1.1; }

/* section headings */
.sec-head { display: flex; align-items: end; justify-content: space-between; gap: 1rem; margin: 2.2rem 0 1rem; }
.sec-head h2 { font-size: clamp(1.4rem, 3vw, 1.9rem); margin: 0; text-transform: uppercase; }
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
.panel, .newsletter, .faq-item, .hist-card { background: linear-gradient(180deg, var(--panel2), var(--panel)); border: 1px solid var(--line);
  border-radius: var(--r); padding: clamp(1.1rem, 2.5vw, 1.6rem); }
.newsletter { position: relative; overflow: hidden; border-color: rgba(255,42,109,.45);
  background: radial-gradient(600px 200px at 100% 0%, rgba(255,42,109,.22), transparent 70%), radial-gradient(500px 200px at 0% 100%, rgba(0,240,255,.15), transparent 70%), var(--panel); }
.newsletter h2 { text-transform: uppercase; }
.newsletter h2::before { content: "🔔 "; }

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

@media (max-width: 820px) {
  .vgrid { grid-template-columns: 1fr; }
  .footer-in { grid-template-columns: 1fr; }
  .footer nav, .footer .dev { justify-content: flex-start; text-align: left; }
}
@media (max-width: 560px) {
  .header-in { flex-wrap: wrap; padding: .6rem 1rem; }
  .nav a { padding: .35rem .65rem; font-size: .92rem; }
  main { padding: 1rem .85rem 2.5rem; }
  .home-hero, .game-hero { border-radius: 16px; }
  .vbadge { font-size: 1.1rem; }
  .micro { display: block; margin: .5rem 0 0; }
  .stats { gap: 1rem; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; scroll-behavior: auto !important; } }
"""


NEWSLETTER_FORM_ID = "f428d642-3e93-4ca7-969a-8882ba5d2129"
NEWSLETTER_URL = "https://modsafes-newsletter.beehiiv.com/subscribe"
NEWSLETTER_COPY = "Get patch-day alerts: know if your mods survived before you update."


def nav(active: str) -> str:
    links = [("/", "home", "Games"), ("/faq/", "faq", "FAQ"), ("/newsletter/", "newsletter", "🔔 Alerts")]
    items = []
    for href, key, label in links:
        aria = ' aria-current="page"' if key == active else ""
        cls = ' class="cta"' if key == "newsletter" and key != active else ""
        items.append(f'<a href="{href}"{aria}{cls}>{esc(label)}</a>')
    return f'<nav class="nav" aria-label="Primary">{" ".join(items)}</nav>'


def brand() -> str:
    return '<div class="brand"><a href="/"><img src="/img/logo.png" width="34" height="34" alt="" class="logo"><span>Mod<b>Safe</b></span></a></div>'


def footer() -> str:
    game_links = " ".join(f'<a href="/{g["slug"]}/">{esc(g["short"])}</a>' for g in GAMES)
    return f"""<footer class="footer"><div class="footer-in">
<div>{brand()}
<p>Know if your mods survived the patch before you hit update.</p>
<p>Not affiliated with any game developer, publisher, Nexus Mods, Thunderstore, Modrinth or Mojang. Game art © its respective owners. Data from public APIs (Steam, GitHub, Thunderstore, Mojang, Fabric, Forge, NeoForge, Modrinth).</p></div>
<div><nav aria-label="Footer">{game_links} <a href="/faq/">FAQ</a> <a href="/newsletter/">Alerts</a></nav>
<p class="dev">For developers &amp; AI: <a href="/games.json">Data (JSON)</a> · <a href="/llms.txt">llms.txt</a></p></div>
</div></footer>"""


def sponsor_slot() -> str:
    # Hidden until a real sponsor exists (placeholder text looked unfinished to visitors).
    return ""
    return """<aside class="sponsor" aria-label="Sponsor">
<p class="sponsor-label">Sponsor slot</p>
<p>Your modding tool or host here. <a href="mailto:sponsors@modsafe.app">Contact</a> (placeholder).</p>
</aside>"""


def newsletter(heading_level: str = "h2") -> str:
    return f"""<section class="newsletter" aria-labelledby="nl-heading">
<{heading_level} id="nl-heading">Patch-day alerts</{heading_level}>
<p>{esc(NEWSLETTER_COPY)}</p>
<script async src="https://subscribe-forms.beehiiv.com/v3/loader.js" data-beehiiv-form="{NEWSLETTER_FORM_ID}"></script>
<p class="nl-note">Form not loading? <a href="{NEWSLETTER_URL}">Subscribe on beehiiv →</a></p>
</section>"""


def cf_beacon() -> str:
    if not CF_ANALYTICS_TOKEN:
        return ""
    cfg = json.dumps({"token": CF_ANALYTICS_TOKEN})
    return f"<script defer src=\"https://static.cloudflareinsights.com/beacon.min.js\" data-cf-beacon='{esc(cfg)}'></script>\n"


def page_shell(title, description, path, active, body, extra_jsonld=None) -> str:
    return (
        base_head(title, description, path, extra_jsonld)
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
<script type="text/javascript" async src="https://subscribe-forms.beehiiv.com/attribution.js"></script>
{cf_beacon()}</body>
</html>
"""
    )


def game_img(slug: str, kind: str = "cap") -> str:
    """kind: 'cap' (616x353 card art) or 'hero' (1600x516 banner). Falls back to SVG tile / header.jpg."""
    if (STATIC / "img" / f"{slug}-{kind}.webp").exists():
        return f"/img/{slug}-{kind}.webp"
    if (STATIC / "img" / f"{slug}.svg").exists():
        return f"/img/{slug}.svg"
    return f"/img/{slug}.jpg"


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
    if not tracked:
        status = "Check manually"
    return f'<span class="badge {status_class(status)}">{icon(status)}{esc(status)}</span>'


def verdict_sentence(game: dict, data: dict) -> str:
    v = data["verdict"]
    p = data["game"]["latest_patch"]["label"]
    fws = [f for f in data["frameworks"] if f.get("tracked", True) and f.get("sensitive", True)]
    manual = [f["short"] for f in data["frameworks"] if not f.get("tracked", True)]
    worst = [f["short"] for f in fws if f["status"] == v]
    tail = f" Also check {', '.join(manual)} manually (Nexus-only, not counted)." if manual else ""
    if v == "Safe":
        msg = f"Every patch-sensitive framework has explicit support for {p}."
    elif v == "Likely safe":
        msg = (f"No breakage evidence for {p}: {', '.join(worst)} {'has' if len(worst) == 1 else 'have'} no release that names the patch, "
               "but there are post-patch releases or no breakage reports since. Probably fine; skim the notes.")
    elif v == "Just patched, wait":
        msg = f"{p} is under a week old and {', '.join(worst)} {'has' if len(worst) == 1 else 'have'} not updated yet. Hold the update a few days."
    elif v == "Breakage reported":
        msg = f"Open issues report breakage after {p} for {', '.join(worst)}. Hold the update or check the linked reports."
    elif v == "Not ported yet":
        msg = f"{', '.join(worst)} {'has' if len(worst) == 1 else 'have'} no build for {p} yet. Stay on your current version if you depend on them."
    else:
        msg = "Some data could not be fetched; check the project pages."
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
    "patch. Not ported yet (Minecraft): no build exists for that version. Not affected by patches: version-agnostic "
    "tools such as mod managers or generic loaders; they don't count toward the verdict."
)


def game_faq(game: dict, data: dict) -> list[dict]:
    p = data["game"]["latest_patch"]
    tracked = [f["name"] for f in data["frameworks"] if f.get("tracked")]
    manual = [f["name"] for f in data["frameworks"] if not f.get("tracked")]
    src = ("the Mojang version manifest" if game.get("kind") == "minecraft"
           else "a hand-maintained record checked by ModSafe (Rockstar title updates and the Script Hook V page)" if game.get("kind") == "manual"
           else f"official Steam announcements (app {game.get('steam_appid')})")
    items = [
        {"q": f"Is it safe to update {game['name']} with mods?",
         "a": f"Current verdict: {data['verdict']}. {verdict_sentence(game, data)} Latest patch tracked: {p['label']} ({fmt_date(p.get('published_at'))})."},
        {"q": f"Why do {game['name']} mods break after a patch?", "a": game["blurb"]},
        {"q": f"Which {game['name']} frameworks does ModSafe track?",
         "a": "Automatically: " + ", ".join(tracked) + "." + (f" Linked for manual checks (no public release API): {', '.join(manual)}." if manual else "")},
        {"q": "What do the status labels mean?", "a": STATUS_EXPLAINER},
        {"q": "Where does the data come from?",
         "a": f"Game patches come from {src}. Framework data comes from public release APIs (GitHub, Thunderstore, Fabric/Forge/NeoForge meta, Modrinth). ModSafe does not scrape Nexus Mods or SteamDB."},
    ]
    if game["slug"] == "gta-v":
        items.append({"q": "Can I use mods in GTA Online?",
                      "a": "No. Only mod single-player (Story Mode). Script Hook V closes the game if you go online, and modding GTA Online risks a permanent ban. Keep a clean install or remove mods before playing Online."})
        items.append({"q": "Does this cover GTA V Enhanced and Legacy?",
                      "a": "Yes. ModSafe tracks the executable build for both the Legacy (Steam app 271590) and Enhanced (Steam app 3240220) editions, and checks that Script Hook V lists both."})
    if game["slug"] == "stardew-valley":
        items.append({"q": "How do I check individual Stardew mods?",
                      "a": "Use the official SMAPI mod compatibility list at smapi.io/mods, which tracks compatible, broken and obsolete mods."})
    return items


def framework_cards(data: dict) -> str:
    out = []
    for fw in data["frameworks"]:
        tracked = fw.get("tracked", True)
        st = fw["status"] if tracked else "Check manually"
        reps = "".join(f'<li><a href="{esc(r["url"])}">{esc(r["title"])}</a></li>' for r in fw.get("breakage_reports") or [])
        out.append(f"""<article class="fw {status_class(st)}">
<h3><a href="{esc(fw['url'])}">{esc(fw['name'])}</a></h3>
{badge(st)}
<div class="rel"><span><code>{esc(fw.get('release_tag') or '—')}</code></span><span>{esc(fmt_date(fw.get('release_published_at')))} · <a href="{esc(fw.get('release_url') or fw['url'])}">source</a></span></div>
<details><summary>Why?</summary><p>{esc(fw.get('reason', ''))}</p>{f"<ul>{reps}</ul>" if reps else ""}</details>
</article>""")
    return "".join(out)


def build_game_page(game: dict, data: dict) -> str:
    p = data["game"]["latest_patch"]
    slug = game["slug"]
    def reason_li(fw):
        reps = "".join(f'<li><a href="{esc(r["url"])}">{esc(r["title"])}</a></li>' for r in fw.get("breakage_reports") or [])
        return f"<li><strong>{esc(fw['short'])}:</strong> {esc(fw.get('reason', ''))}" + (f"<ul>{reps}</ul>" if reps else "") + "</li>"
    faq = game_faq(game, data)
    faq_html = "".join(f'<article class="faq-item"><h3>{esc(i["q"])}</h3><p>{esc(i["a"])}</p></article>' for i in faq)
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
<p class="crumbs"><a href="/">Games</a> › {esc(game['name'])}</p>
<section class="game-hero v-{vc}" style="--hero:url('{game_img(slug, "hero")}')">
<div>
<h1>Is it safe to update {esc(game['name'])}?</h1>
<p>{vbadge(data['verdict'])}<span class="micro">{esc(MICROCOPY.get(data['verdict'], ''))}</span></p>
<p class="lede">{esc(game['blurb'])}</p>
{f'<p class="note" role="note"><strong>⚠ {esc(game["note"])}</strong></p>' if game.get("note") else ''}
</div>
</section>
<div class="vgrid">
<section class="panel" aria-labelledby="verdict-heading">
<h2 id="verdict-heading">Verdict for {esc(p['label'])}</h2>
<p class="big-say">{esc(verdict_sentence(game, data))}</p>
</section>
<section class="panel" aria-label="Patch details">
<dl class="patch-meta">
<dt>Latest patch</dt><dd><strong>{esc(p['label'])}</strong></dd>
<dt>Released</dt><dd>{esc(fmt_date(p.get('published_at')))}</dd>
<dt>Source</dt><dd><a href="{esc(p.get('url', ''))}">{esc(p.get('title', ''))}</a></dd>
{snap}
{f"<dt>Builds</dt><dd>" + ", ".join(f"{esc(k.title())} <code>{esc(v)}</code>" for k, v in p["builds"].items()) + "</dd>" if p.get("builds") else ""}
{f"<dt>Last manually verified</dt><dd><strong>{esc(data['last_verified'])}</strong> <span class='muted'>(hand-maintained data)</span></dd>" if data.get("last_verified") else ""}
<dt>Data refreshed</dt><dd>{esc(fmt_date(data.get('generated_at')))} <span class="muted">(UTC)</span></dd>
</dl>
</section>
</div>
<div class="sec-head"><h2 id="fw-heading">Frameworks &amp; loaders</h2></div>
<section class="fw-grid" aria-labelledby="fw-heading">{framework_cards(data)}</section>
{f'<ul>{extra}</ul>' if extra else ''}
<p class="disclaimer">{esc(data.get('disclaimer', ''))} Items marked “Check manually” are not counted in the verdict.</p>
{newsletter()}
<div class="sec-head"><h2 id="faq-heading">{esc(game['short'])} modding FAQ</h2></div>
<section class="faq-list" aria-labelledby="faq-heading">
{faq_html}
</section>
<section class="links"><a href="/{slug}/history/">📜 Patch history</a> <a href="{esc(game['wiki'])}">🛠 Modding resources</a> <a href="/">🎮 All games</a></section>
"""
    return page_shell(
        f"Is it safe to update {game['name']}? Mod status for {p['label']} — ModSafe",
        f"{game['name']} {p['label']}: {data['verdict']}. Live status of " + ", ".join(f['short'] for f in data['frameworks']) + " after the latest patch.",
        f"/{slug}/", slug, body,
        extra_jsonld=[dataset, faq_ld(faq), breadcrumb_ld([("Games", "/"), (game["name"], f"/{slug}/")])],
    )


def build_game_history(game: dict, data: dict) -> str:
    sections = []
    for entry in data.get("history", []):
        cells = "".join(
            f'<li>{badge(fw["status"])} <strong>{esc(fw["short"])}</strong> <code>{esc(fw.get("release_tag") or "—")}</code></li>'
            for fw in entry.get("frameworks", []))
        sections.append(f"""<article class="hist-card" id="patch-{esc(entry['label']).replace(' ', '-')}">
<h3>{esc(entry['label'])}</h3>
<p class="muted">{esc(fmt_date(entry.get('published_at')))} · <a href="{esc(entry.get('url', ''))}">{esc(entry.get('title', ''))}</a></p>
<ul class="hist-fw">{cells}</ul>
</article>""")
    slug = game["slug"]
    body = f"""
<p class="crumbs"><a href="/">Games</a> › <a href="/{slug}/">{esc(game['name'])}</a> › History</p>
<section class="page-hero"><h1>{esc(game['name'])} patch history</h1>
<p class="lede">How tracked frameworks looked relative to each recent {esc(game['name'])} patch, using the same rules as the main page.</p></section>
<section class="hist-list">{''.join(sections) or '<p>No patch history available.</p>'}</section>
"""
    return page_shell(f"{game['name']} patch history — ModSafe",
                      f"Historical {game['name']} patch compatibility for its core mod frameworks.",
                      f"/{slug}/history/", slug, body,
                      extra_jsonld=[breadcrumb_ld([("Games", "/"), (game["name"], f"/{slug}/"), ("History", f"/{slug}/history/")])])


def build_home(games_data: list[tuple[dict, dict]]) -> str:
    cards = []
    for i, (game, data) in enumerate(games_data):
        p = data["game"]["latest_patch"]
        chips = "".join(f'<span class="chip">{esc(f["short"])}</span>' for f in data["frameworks"])
        cards.append(f"""<article class="game-card v-{status_class(data['verdict'])}">
<div class="card-art"><img src="{game_img(game['slug'])}" width="616" height="353" {'loading="lazy" ' if i > 2 else ''}decoding="async" alt="{esc(game['name'])} cover art">{badge(data['verdict'])}</div>
<div class="card-body">
<h3><a href="/{game['slug']}/" class="stretched">{esc(game['name'])}</a></h3>
<p class="card-meta"><span>Patch <strong>{esc(p['label'])}</strong></span><span>{esc(fmt_date(p.get('published_at')))}</span></p>
<div class="chips">{chips}</div>
</div>
</article>""")
    itemlist = {"@context": "https://schema.org", "@type": "ItemList", "name": "Games tracked by ModSafe",
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": g["name"], "url": f"{SITE_URL}/{g['slug']}/"}
                                    for i, (g, _) in enumerate(games_data)]}
    n_fw = sum(len(d["frameworks"]) for _, d in games_data)
    n_ok = sum(1 for _, d in games_data if d["verdict"] in ("Safe", "Likely safe"))
    body = f"""
<section class="home-hero" style="--hero:url('/img/cyberpunk-2077-hero.webp')">
<p class="eyebrow">Patch day, minus the panic</p>
<h1>Did your mods <em>survive</em> the patch?</h1>
<p class="lede">A new update drops, and script extenders and mod loaders break first. ModSafe watches every game's core frameworks so you know whether to hit update or hold the line.</p>
<div class="legend"><span class="badge ok">{icon("Safe")}Safe</span><span class="badge likely">{icon("Likely safe")}Likely safe</span><span class="badge wait">{icon("Just patched, wait")}Just patched, wait</span><span class="badge broken">{icon("Breakage reported")}Breakage reported</span></div>
<div class="hero-actions"><a class="btn" href="#games">🎮 Pick your game</a> <a class="btn ghost" href="/newsletter/">🔔 Get patch alerts</a></div>
<div class="stats"><div><strong>{len(games_data)}</strong>games tracked</div><div><strong>{n_fw}</strong>frameworks watched</div><div><strong>{n_ok}/{len(games_data)}</strong>safe or likely safe now</div></div>
</section>
<div class="sec-head" id="games"><h2>Choose your game</h2><span class="muted">Refreshed every few hours</span></div>
<section class="game-grid" aria-label="Games">
{''.join(cards)}
</section>
{newsletter()}
<section class="panel"><h2>How we call it</h2><p class="disclaimer">{esc(STATUS_EXPLAINER)}</p>
<p><a href="/faq/">Read the FAQ →</a></p></section>
"""
    return page_shell(f"Is it safe to update? — {SITE_NAME}", SITE_DESC, "/", "home", body, extra_jsonld=[itemlist])


GENERAL_FAQ = [
    {"q": "Is it safe to update my game with mods installed?",
     "a": "Vanilla patches are safe, but mods built on script extenders or loaders (SKSE, F4SE, RED4ext, BG3SE, SMAPI, BepInEx, Fabric/Forge) often break until those frameworks update. Check your game's page here first, or hold the update."},
    {"q": "What do the status labels mean?", "a": STATUS_EXPLAINER},
    {"q": "Why are some frameworks marked “Check manually”?",
     "a": "Some core mods (for example Address Library and Buffout 4) are only distributed on Nexus Mods. Nexus' API terms forbid scraping, so ModSafe links them instead of guessing, and leaves them out of the verdict."},
    {"q": "Where does the data come from?",
     "a": "Steam Web API news (official announcements), Mojang's version manifest, GitHub releases/tags, the Thunderstore package API, Fabric meta, Forge promotions, NeoForge Maven and the Modrinth API. Refreshed every few hours."},
    {"q": "Which games are covered?", "a": "Cyberpunk 2077, Skyrim Special Edition, Fallout 4, Baldur's Gate 3, Stardew Valley, Lethal Company, Grand Theft Auto V (single-player) and Minecraft: Java Edition."},
]


def build_faq() -> str:
    arts = "".join(f'<article class="faq-item" id="faq-{i}"><h2>{esc(it["q"])}</h2><p>{esc(it["a"])}</p></article>'
                   for i, it in enumerate(GENERAL_FAQ))
    body = f"""<section class="page-hero"><h1>FAQ</h1><p class="lede">Updating modded games after a patch.</p></section>
<section class="faq-list">{arts}</section>
{newsletter()}
<section class="panel"><p>Game-specific FAQs: {' · '.join(f'<a href="/{g["slug"]}/#faq-heading">{esc(g["name"])}</a>' for g in GAMES)}</p></section>"""
    return page_shell(f"FAQ — {SITE_NAME}", "Is it safe to update a modded game? How ModSafe decides — FAQ.", "/faq/", "faq", body,
                      extra_jsonld=[faq_ld(GENERAL_FAQ)])


def build_newsletter_page() -> str:
    body = f"""<section class="page-hero"><h1>Patch-day alerts</h1><p class="lede">{esc(NEWSLETTER_COPY)}</p></section>
{newsletter("h2")}"""
    return page_shell(f"Patch-day alerts — {SITE_NAME}", NEWSLETTER_COPY, "/newsletter/", "newsletter", body)


OG_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#0a0e17"/>
<text x="80" y="280" fill="#00f0ff" font-family="system-ui,sans-serif" font-size="64" font-weight="700">ModSafe</text>
<text x="80" y="360" fill="#e8eef8" font-family="system-ui,sans-serif" font-size="36">Is it safe to update? Mod framework status after game patches</text>
</svg>
"""


def build_llms_txt(games_data) -> str:
    lines = [f"# {SITE_NAME}", "", f"> {SITE_DESC}", "", f"Site: {SITE_URL}/", f"Index JSON: {SITE_URL}/games.json",
             f"Legacy Cyberpunk JSON: {SITE_URL}/status.json", "",
             "Status meanings: " + STATUS_EXPLAINER, ""]
    for game, data in games_data:
        p = data["game"]["latest_patch"]
        lines += [f"## {game['name']}", f"- Page: {SITE_URL}/{game['slug']}/", f"- JSON: {SITE_URL}/{game['slug']}/status.json",
                  f"- Latest patch: {p['label']} ({p.get('published_at')}) {p.get('url')}", f"- Verdict: {data['verdict']}",
                  f"- Generated (UTC): {data.get('generated_at')}"]
        for fw in data["frameworks"]:
            tr = "" if fw.get("tracked", True) else " [not auto-tracked]"
            lines.append(f"  - {fw['name']}: {fw['status']}{tr}; release {fw.get('release_tag')} {fw.get('release_published_at') or ''}; {fw.get('reason')}")
        lines.append("")
    lines += ["## Pages", f"- FAQ: {SITE_URL}/faq/", f"- Alerts: {SITE_URL}/newsletter/", "",
              "Statuses are inferred from public release data; not official developer guidance.", ""]
    return "\n".join(lines)


def build_robots() -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"


def sitemap_urls() -> list[str]:
    urls = ["/", "/faq/", "/newsletter/"]
    for g in GAMES:
        urls += [f"/{g['slug']}/", f"/{g['slug']}/history/"]
    return urls + ["/games.json", "/llms.txt"]


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
"""


def games_index(games_data) -> dict:
    return {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "games": [{"slug": g["slug"], "name": g["name"], "verdict": d["verdict"],
                       "latest_patch": {k: d["game"]["latest_patch"].get(k) for k in ("label", "version", "published_at", "url")},
                       "page": f"{SITE_URL}/{g['slug']}/", "json": f"{SITE_URL}/{g['slug']}/status.json",
                       "frameworks": [{"id": f["id"], "name": f["name"], "status": f["status"], "tracked": f.get("tracked", True),
                                       "release_tag": f.get("release_tag")} for f in d["frameworks"]]}
                      for g, d in games_data]}


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
    write(DIST / "index.html", build_home(games_data))
    for g, d in games_data:
        write(DIST / g["slug"] / "index.html", build_game_page(g, d))
        write(DIST / g["slug"] / "history" / "index.html", build_game_history(g, d))
        write(DIST / g["slug"] / "status.json", json.dumps(d, indent=2) + "\n")
        if g["slug"] == "cyberpunk-2077":
            # Legacy endpoint kept for existing consumers (same shape as v1 + extra fields).
            legacy = json.loads(json.dumps(d))
            legacy["game"]["latest_patch"]["version"] = legacy["game"]["latest_patch"].get("version")
            write(DIST / "status.json", json.dumps(legacy, indent=2) + "\n")
    write(DIST / "faq" / "index.html", build_faq())
    write(DIST / "newsletter" / "index.html", build_newsletter_page())
    import shutil
    shutil.copytree(STATIC, DIST, dirs_exist_ok=True)
    write(DIST / "styles.css", CSS)
    write(DIST / "og-default.svg", OG_SVG)
    write(DIST / "games.json", json.dumps(games_index(games_data), indent=2) + "\n")
    write(DIST / "llms.txt", build_llms_txt(games_data))
    write(DIST / "robots.txt", build_robots())
    write(DIST / "sitemap.xml", build_sitemap())
    write(DIST / "_redirects", REDIRECTS)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
