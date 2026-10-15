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

SITE_URL = os.environ.get("SITE_URL", "https://modsafe.app").rstrip("/")
SITE_NAME = "ModSafe — Mod Compatibility After Game Patches"
SITE_DESC = (
    "Is it safe to update? Live status of core mod frameworks and loaders (script extenders, "
    "BepInEx, SMAPI, Fabric/Forge) after each official game patch, for Cyberpunk 2077, Skyrim SE, "
    "Fallout 4, Baldur's Gate 3, Stardew Valley, Lethal Company and Minecraft."
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
<meta name="theme-color" content="#0a0e17">
<link rel="stylesheet" href="/styles.css">
{blocks}
</head>
"""


CSS = """
:root {
  --bg: #0a0e17;
  --panel: #121826;
  --text: #e8eef8;
  --muted: #9aa8bc;
  --accent: #00f0ff;
  --accent2: #ff2a6d;
  --ok: #1f9d55;
  --likely: #c9a227;
  --unknown: #c0392b;
  --border: #243044;
  --focus: #ffe66d;
  --font: system-ui, -apple-system, "Segoe UI", Roboto, Ubuntu, Cantarell, sans-serif;
  --mono: ui-monospace, "Cascadia Code", "SF Mono", Menlo, Consolas, monospace;
}
*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: var(--font);
  background: radial-gradient(1200px 600px at 10% -10%, #1a2740 0%, var(--bg) 55%);
  color: var(--text);
  line-height: 1.55;
  min-height: 100vh;
}
a { color: var(--accent); }
a:hover { text-decoration-thickness: 2px; }
a:focus-visible, button:focus-visible, input:focus-visible, summary:focus-visible {
  outline: 3px solid var(--focus);
  outline-offset: 2px;
}
.skip {
  position: absolute; left: -9999px; top: auto;
}
.skip:focus {
  left: 1rem; top: 1rem; z-index: 100;
  background: var(--focus); color: #000; padding: .5rem 1rem;
}
.header {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: 1rem; padding: 1rem 1.25rem; border-bottom: 1px solid var(--border);
  background: rgba(10,14,23,.85); backdrop-filter: blur(8px);
  position: sticky; top: 0; z-index: 10;
}
.brand a { color: var(--text); text-decoration: none; font-weight: 700; letter-spacing: .02em; }
.nav { display: flex; flex-wrap: wrap; gap: .75rem 1.25rem; }
.nav a { color: var(--muted); text-decoration: none; font-weight: 600; }
.nav a[aria-current="page"], .nav a:hover { color: var(--accent); }
main { max-width: 1120px; margin: 0 auto; padding: 1.5rem 1.25rem 3rem; }
.hero h1 { font-size: clamp(1.6rem, 4vw, 2.2rem); margin: 0 0 .5rem; }
.lede { color: var(--muted); font-size: 1.05rem; max-width: 60ch; }
.panel, .sponsor, .newsletter, .hist-card, .faq-item {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 12px; padding: 1.25rem 1.35rem; margin: 1.25rem 0;
}
.sponsor { border-style: dashed; }
.sponsor-label { text-transform: uppercase; letter-spacing: .08em; font-size: .75rem; color: var(--accent2); margin: 0 0 .35rem; }
.patch-meta { display: grid; grid-template-columns: 10rem 1fr; gap: .4rem 1rem; margin: 0; }
.patch-meta dt { color: var(--muted); }
.patch-meta dd { margin: 0; }
.table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
table { width: 100%; border-collapse: collapse; min-width: 560px; }
th, td { text-align: left; padding: .65rem .5rem; border-bottom: 1px solid var(--border); vertical-align: top; }
th { color: var(--muted); font-size: .85rem; font-weight: 600; }
.badge {
  display: inline-block; padding: .2rem .55rem; border-radius: 999px;
  font-size: .8rem; font-weight: 700; color: #fff;
}
.badge.ok { background: var(--ok); }
.badge.likely { background: var(--likely); color: #111; }
.badge.unknown { background: var(--unknown); }
.disclaimer, .muted, .nl-note { color: var(--muted); font-size: .92rem; }
code { font-family: var(--mono); font-size: .9em; }
.reasons { margin-top: 1rem; }
.hist-fw { list-style: none; padding: 0; margin: .75rem 0 0; display: grid; gap: .5rem; }
.hist-fw li { display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; }
.nl-form { display: flex; flex-wrap: wrap; gap: .5rem; align-items: end; margin: .75rem 0; }
.nl-form label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
.nl-form input {
  flex: 1 1 220px; padding: .65rem .75rem; border-radius: 8px;
  border: 1px solid var(--border); background: var(--bg); color: var(--text);
}
.nl-form button {
  padding: .65rem 1rem; border-radius: 8px; border: none;
  background: var(--accent2); color: #fff; font-weight: 700; opacity: .55; cursor: not-allowed;
}
.faq-item h2 { font-size: 1.15rem; margin-top: 0; }
.footer {
  max-width: 960px; margin: 0 auto; padding: 1rem 1.25rem 2.5rem;
  color: var(--muted); font-size: .85rem; border-top: 1px solid var(--border);
}
.verdict-big { font-size: 1rem; padding: .35rem .8rem; }
.game-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
.game-card { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 1.1rem 1.2rem; }
.game-card h2 { font-size: 1.15rem; margin: 0 0 .4rem; }
.game-card h2 a { color: var(--text); text-decoration: none; }
.game-card p { margin: .35rem 0; }
.crumbs { color: var(--muted); font-size: .9rem; }
.badge.manual { background: #4a5568; }
.badge.wait { background: #e67e22; color: #111; }
.badge.broken { background: var(--unknown); }
.badge.agnostic { background: #3b5b8c; }
.badge.unknown { background: #6b7280; }
.logo { vertical-align: middle; margin-right: .5rem; border-radius: 8px; }
.brand a { display: inline-flex; align-items: center; }
.home-hero { display: grid; grid-template-columns: 1.2fr 1fr; gap: 1.5rem; align-items: center; margin: .5rem 0 1.5rem;
  padding: 1.75rem; border-radius: 16px; border: 1px solid var(--border);
  background: linear-gradient(135deg, #0f1a2e 0%, #111a2b 60%, #1a1030 100%); }
.home-hero h1 { font-size: clamp(1.8rem, 4.5vw, 2.8rem); line-height: 1.15; margin: .25rem 0 .75rem; }
.home-hero-img { width: 100%; height: auto; border-radius: 12px; }
.eyebrow { color: var(--accent); text-transform: uppercase; letter-spacing: .12em; font-size: .8rem; font-weight: 700; margin: 0; }
.home-hero .badge { margin: .15rem 0; }
.btn { display: inline-block; padding: .65rem 1.1rem; border-radius: 10px; background: var(--accent); color: #031018;
  font-weight: 800; text-decoration: none; margin: .25rem .4rem .25rem 0; transition: transform .15s, box-shadow .15s; }
.btn:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(0,240,255,.25); }
.btn.ghost { background: transparent; color: var(--accent); border: 1px solid var(--accent); }
.game-grid { grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 1.1rem; }
.game-card { position: relative; padding: 0; overflow: hidden; border-top: 4px solid var(--border);
  transition: transform .18s ease, box-shadow .18s ease, border-color .18s; }
.game-card.v-ok { border-top-color: var(--ok); }
.game-card.v-likely { border-top-color: var(--likely); }
.game-card.v-wait { border-top-color: #e67e22; }
.game-card.v-broken { border-top-color: var(--unknown); }
.game-card:hover, .game-card:focus-within { transform: translateY(-3px); box-shadow: 0 12px 30px rgba(0,0,0,.45); border-color: var(--accent); }
.card-img img { display: block; width: 100%; height: auto; aspect-ratio: 460 / 215; object-fit: cover; }
.card-body { padding: .9rem 1.1rem 1.1rem; }
.stretched::after { content: ""; position: absolute; inset: 0; }
.game-hero { position: relative; display: grid; grid-template-columns: minmax(0, 460px) 1fr; gap: 1.5rem; align-items: center;
  padding: 1.5rem; border-radius: 16px; overflow: hidden; border: 1px solid var(--border); margin: .5rem 0 1rem;
  background: linear-gradient(90deg, rgba(10,14,23,.92), rgba(10,14,23,.75)), var(--hero) center / cover; }
.game-hero img { width: 100%; height: auto; border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,.5); }
.game-hero h1 { font-size: clamp(1.5rem, 3.5vw, 2.2rem); margin: 0 0 .5rem; }
.note { background: rgba(255,42,109,.12); border-left: 3px solid var(--accent2); padding: .5rem .75rem; border-radius: 6px; }
@media (max-width: 760px) {
  .home-hero, .game-hero { grid-template-columns: 1fr; padding: 1.1rem; }
  .home-hero-img { order: -1; }
}
@media (max-width: 600px) {
  .patch-meta { grid-template-columns: 1fr; }
  .patch-meta dt { margin-top: .35rem; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
}
"""


NEWSLETTER_FORM_ID = "f428d642-3e93-4ca7-969a-8882ba5d2129"
NEWSLETTER_URL = "https://modsafes-newsletter.beehiiv.com/subscribe"
NEWSLETTER_COPY = "Get patch-day alerts: know if your mods survived before you update."


def nav(active: str) -> str:
    links = [("/", "home", "Games"), ("/faq/", "faq", "FAQ"), ("/newsletter/", "newsletter", "Alerts"),
             ("/games.json", "json", "JSON")]
    items = []
    for href, key, label in links:
        aria = ' aria-current="page"' if key == active else ""
        items.append(f'<a href="{href}"{aria}>{esc(label)}</a>')
    return f'<nav class="nav" aria-label="Primary">{" ".join(items)}</nav>'


def footer() -> str:
    return f"""<footer class="footer">
<p>Not affiliated with any game developer, publisher, Nexus Mods, Thunderstore, Modrinth or Mojang. Data from public APIs: Steam Web API, GitHub, Thunderstore, Mojang, Fabric, Forge, NeoForge, Modrinth.</p>
<p><a href="{esc(SITE_URL)}/">{esc(SITE_URL)}</a></p>
</footer>"""


def sponsor_slot() -> str:
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


def page_shell(title, description, path, active, body, extra_jsonld=None) -> str:
    return (
        base_head(title, description, path, extra_jsonld)
        + f"""<body>
<a class="skip" href="#main">Skip to content</a>
<header class="header">
<div class="brand"><a href="/"><img src="/img/logo.png" width="32" height="32" alt="" class="logo">ModSafe</a></div>
{nav(active)}
</header>
<main id="main">
{body}
</main>
{footer()}
<script type="text/javascript" async src="https://subscribe-forms.beehiiv.com/attribution.js"></script>
</body>
</html>
"""
    )


def game_img(slug: str) -> str:
    return f"/img/{slug}.svg" if (STATIC / "img" / f"{slug}.svg").exists() else f"/img/{slug}.jpg"


def badge(status: str, tracked: bool = True) -> str:
    if not tracked:
        status = "Check manually"
    return f'<span class="badge {status_class(status)}">{esc(status)}</span>'


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
    if game["slug"] == "stardew-valley":
        items.append({"q": "How do I check individual Stardew mods?",
                      "a": "Use the official SMAPI mod compatibility list at smapi.io/mods, which tracks compatible, broken and obsolete mods."})
    return items


def framework_rows(data: dict) -> str:
    rows = []
    for fw in data["frameworks"]:
        tracked = fw.get("tracked", True)
        rows.append(f"""<tr>
<td><a href="{esc(fw['url'])}">{esc(fw['name'])}</a></td>
<td>{badge(fw['status'], tracked)}</td>
<td><code>{esc(fw.get('release_tag') or '—')}</code></td>
<td>{esc(fmt_date(fw.get('release_published_at')))}</td>
<td><a href="{esc(fw.get('release_url') or fw['url'])}">Source</a></td>
</tr>""")
    return "".join(rows)


def build_game_page(game: dict, data: dict) -> str:
    p = data["game"]["latest_patch"]
    slug = game["slug"]
    def reason_li(fw):
        reps = "".join(f'<li><a href="{esc(r["url"])}">{esc(r["title"])}</a></li>' for r in fw.get("breakage_reports") or [])
        return f"<li><strong>{esc(fw['short'])}:</strong> {esc(fw.get('reason', ''))}" + (f"<ul>{reps}</ul>" if reps else "") + "</li>"
    reasons = "".join(reason_li(fw) for fw in data["frameworks"])
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
    body = f"""
<p class="crumbs"><a href="/">Games</a> › {esc(game['name'])}</p>
<section class="game-hero" style="--hero:url('{game_img(slug)}')">
<img src="{game_img(slug)}" width="460" height="215" alt="{esc(game['name'])} key art" fetchpriority="high">
<div>
<h1>Is it safe to update {esc(game['name'])}?</h1>
<p><span class="badge verdict-big {status_class(data['verdict'])}">{esc(data['verdict'])}</span> <span class="muted">for {esc(p['label'])}</span></p>
<p class="lede">{esc(game['blurb'])}</p>
{f'<p class="note">{esc(game["note"])}</p>' if game.get("note") else ''}
</div>
</section>
<section class="panel" aria-labelledby="verdict-heading">
<h2 id="verdict-heading">Verdict for {esc(p['label'])}</h2>
<p><span class="badge verdict-big {status_class(data['verdict'])}">{esc(data['verdict'])}</span></p>
<p>{esc(verdict_sentence(game, data))}</p>
<dl class="patch-meta">
<dt>Latest patch</dt><dd><strong>{esc(p['label'])}</strong></dd>
<dt>Released</dt><dd>{esc(fmt_date(p.get('published_at')))}</dd>
<dt>Source</dt><dd><a href="{esc(p.get('url', ''))}">{esc(p.get('title', ''))}</a></dd>
{snap}
<dt>Data refreshed</dt><dd>{esc(fmt_date(data.get('generated_at')))} <span class="muted">(UTC)</span></dd>
</dl>
</section>
<section class="panel" aria-labelledby="fw-heading">
<h2 id="fw-heading">Core frameworks &amp; loaders</h2>
<div class="table-wrap"><table>
<thead><tr><th scope="col">Framework</th><th scope="col">Status</th><th scope="col">Latest release</th><th scope="col">Released</th><th scope="col">Link</th></tr></thead>
<tbody>{framework_rows(data)}</tbody>
</table></div>
<details class="reasons"><summary>Why these statuses?</summary><ul>{reasons}</ul></details>
{f'<ul>{extra}</ul>' if extra else ''}
<p class="disclaimer">{esc(data.get('disclaimer', ''))} Items marked “Check manually” are not counted in the verdict.</p>
</section>
{newsletter()}
{sponsor_slot()}
<section class="faq-list" aria-labelledby="faq-heading">
<h2 id="faq-heading">{esc(game['name'])} modding FAQ</h2>
{faq_html}
</section>
<section class="panel"><p><a href="/{slug}/history/">Patch history →</a> · <a href="/{slug}/status.json">JSON →</a> · <a href="{esc(game['wiki'])}">Modding resources →</a></p></section>
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
<section class="hero"><h1>{esc(game['name'])} patch history</h1>
<p class="lede">How tracked frameworks looked relative to each recent {esc(game['name'])} patch, using the same rules as the main page.</p></section>
<section class="hist-list">{''.join(sections) or '<p>No patch history available.</p>'}</section>
"""
    return page_shell(f"{game['name']} patch history — ModSafe",
                      f"Historical {game['name']} patch compatibility for its core mod frameworks.",
                      f"/{slug}/history/", slug, body,
                      extra_jsonld=[breadcrumb_ld([("Games", "/"), (game["name"], f"/{slug}/"), ("History", f"/{slug}/history/")])])


def build_home(games_data: list[tuple[dict, dict]]) -> str:
    cards = []
    for game, data in games_data:
        p = data["game"]["latest_patch"]
        cards.append(f"""<article class="game-card v-{status_class(data['verdict'])}">
<a class="card-img" href="/{game['slug']}/" tabindex="-1" aria-hidden="true"><img src="{game_img(game['slug'])}" width="460" height="215" loading="lazy" decoding="async" alt=""></a>
<div class="card-body">
<h2><a href="/{game['slug']}/" class="stretched">{esc(game['name'])}</a></h2>
<p><span class="badge {status_class(data['verdict'])}">{esc(data['verdict'])}</span></p>
<p class="muted">Latest patch <strong>{esc(p['label'])}</strong> · {esc(fmt_date(p.get('published_at')))}</p>
<p class="muted">{esc(', '.join(f['short'] for f in data['frameworks']))}</p>
</div>
</article>""")
    itemlist = {"@context": "https://schema.org", "@type": "ItemList", "name": "Games tracked by ModSafe",
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": g["name"], "url": f"{SITE_URL}/{g['slug']}/"}
                                    for i, (g, _) in enumerate(games_data)]}
    body = f"""
<section class="home-hero">
<div class="home-hero-text">
<p class="eyebrow">Patch day, minus the panic</p>
<h1>Is it safe to update your modded game?</h1>
<p class="lede">When a patch drops, script extenders and mod loaders break first. ModSafe watches each game's core frameworks and tells you plainly: <span class="badge ok">Safe</span> <span class="badge likely">Likely safe</span> <span class="badge wait">Just patched, wait</span> <span class="badge broken">Breakage reported</span></p>
<p><a class="btn" href="#games">See your game ↓</a> <a class="btn ghost" href="/newsletter/">Get patch alerts</a></p>
</div>
<img class="home-hero-img" src="/img/brand-banner.jpg" width="1200" height="400" alt="ModSafe shield logo" fetchpriority="high">
</section>
<section class="game-grid" id="games" aria-label="Games">
{''.join(cards)}
</section>
{newsletter()}
{sponsor_slot()}
<section class="panel"><p class="disclaimer">{esc(STATUS_EXPLAINER)}</p>
<p><a href="/faq/">FAQ →</a> · <a href="/games.json">Machine-readable JSON →</a> · <a href="/llms.txt">llms.txt</a></p></section>
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
    {"q": "Which games are covered?", "a": "Cyberpunk 2077, Skyrim Special Edition, Fallout 4, Baldur's Gate 3, Stardew Valley, Lethal Company and Minecraft: Java Edition."},
]


def build_faq() -> str:
    arts = "".join(f'<article class="faq-item" id="faq-{i}"><h2>{esc(it["q"])}</h2><p>{esc(it["a"])}</p></article>'
                   for i, it in enumerate(GENERAL_FAQ))
    body = f"""<section class="hero"><h1>FAQ</h1><p class="lede">Updating modded games after a patch.</p></section>
<section class="faq-list">{arts}</section>
{newsletter()}
<section class="panel"><p>Game-specific FAQs: {' · '.join(f'<a href="/{g["slug"]}/#faq-heading">{esc(g["name"])}</a>' for g in GAMES)}</p></section>"""
    return page_shell(f"FAQ — {SITE_NAME}", "Is it safe to update a modded game? How ModSafe decides — FAQ.", "/faq/", "faq", body,
                      extra_jsonld=[faq_ld(GENERAL_FAQ)])


def build_newsletter_page() -> str:
    body = f"""<section class="hero"><h1>Patch-day alerts</h1><p class="lede">{esc(NEWSLETTER_COPY)}</p></section>
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
