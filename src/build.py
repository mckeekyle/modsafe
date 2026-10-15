#!/usr/bin/env python3
"""Static site generator for ModSafe — Cyberpunk 2077 framework patch status."""

from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "status.json"
DIST = ROOT / "dist"

SITE_URL = os.environ.get("SITE_URL", "https://modsafe.app").rstrip("/")
SITE_NAME = "ModSafe — Cyberpunk 2077 Mod Compatibility"
SITE_DESC = (
    "Live status of Cyberpunk 2077 core mod frameworks (CET, RED4ext, redscript, "
    "ArchiveXL, TweakXL, Codeware) after each official game patch."
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


def status_class(status: str) -> str:
    if status.startswith("Updated"):
        return "ok"
    if status.startswith("Likely"):
        return "likely"
    return "unknown"


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


def nav(active: str) -> str:
    links = [
        ("/", "home", "Status"),
        ("/history/", "history", "Patch history"),
        ("/faq/", "faq", "FAQ"),
        ("/status.json", "json", "JSON"),
    ]
    items = []
    for href, key, label in links:
        aria = ' aria-current="page"' if key == active else ""
        items.append(f'<a href="{href}"{aria}>{esc(label)}</a>')
    return f'<nav class="nav" aria-label="Primary">{" ".join(items)}</nav>'


def footer() -> str:
    return f"""<footer class="footer">
<p>Not affiliated with CD PROJEKT RED or Nexus Mods. Data from Steam Web API and GitHub public releases.</p>
<p><a href="{esc(SITE_URL)}">{esc(SITE_URL)}</a> · Not affiliated with CD PROJEKT RED.</p>
</footer>"""


def sponsor_slot() -> str:
    return """<aside class="sponsor" aria-label="Sponsor">
<p class="sponsor-label">Sponsor slot</p>
<p>Your modding tool or host here. <a href="mailto:sponsors@modsafe.app">Contact</a> (placeholder).</p>
</aside>"""


def newsletter() -> str:
    return """<section class="newsletter" aria-labelledby="nl-heading">
<h2 id="nl-heading">Get patch alerts</h2>
<p>Newsletter signup placeholder — wire this to Buttondown, Mailchimp, or ConvertKit.</p>
<form class="nl-form" action="#" method="post" onsubmit="return false;">
<label for="email">Email</label>
<input type="email" id="email" name="email" autocomplete="email" placeholder="you@example.com" required>
<button type="submit" disabled title="Connect a newsletter provider">Notify me</button>
</form>
<p class="nl-note">Form is disabled until you add a provider. No emails are collected by this static site.</p>
</section>"""


def page_shell(title: str, description: str, path: str, active: str, body: str, extra_jsonld: list | None = None) -> str:
    return (
        base_head(title, description, path, extra_jsonld)
        + f"""<body>
<a class="skip" href="#main">Skip to content</a>
<header class="header">
<div class="brand"><a href="/">ModSafe</a></div>
{nav(active)}
</header>
<main id="main">
{body}
</main>
{footer()}
</body>
</html>
"""
    )


def build_home(data: dict) -> str:
    patch = data["game"]["latest_patch"]
    generated = data.get("generated_at")
    rows = []
    for fw in data["frameworks"]:
        sc = status_class(fw["status"])
        rows.append(
            f"""<tr>
<td><a href="{esc(fw['url'])}">{esc(fw['name'])}</a></td>
<td><span class="badge {sc}">{esc(fw['status'])}</span></td>
<td><code>{esc(fw.get('release_tag') or '—')}</code></td>
<td>{esc(fmt_date(fw.get('release_published_at')))}</td>
<td><a href="{esc(fw.get('release_url') or fw['url'])}">Release</a></td>
</tr>"""
        )
    reasons = "".join(
        f"<li><strong>{esc(fw['short'])}:</strong> {esc(fw.get('reason',''))}</li>"
        for fw in data["frameworks"]
    )
    dataset_ld = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Cyberpunk 2077 core framework patch compatibility",
        "description": SITE_DESC,
        "url": f"{SITE_URL}/",
        "license": "https://creativecommons.org/publicdomain/zero/1.0/",
        "creator": {"@type": "Organization", "name": "ModSafe"},
        "distribution": [
            {
                "@type": "DataDownload",
                "encodingFormat": "application/json",
                "contentUrl": f"{SITE_URL}/status.json",
            }
        ],
        "temporalCoverage": patch.get("published_at", "")[:10],
        "variableMeasured": "Framework update status vs game patch",
    }
    body = f"""
<section class="hero">
<h1>Cyberpunk 2077 mod framework status</h1>
<p class="lede">After each official patch, core frameworks must catch up. This page tracks CET, RED4ext, redscript, ArchiveXL, TweakXL, and Codeware — honestly, with evidence.</p>
</section>
{sponsor_slot()}
<section class="panel" aria-labelledby="patch-heading">
<h2 id="patch-heading">Current game patch</h2>
<dl class="patch-meta">
<dt>Version</dt><dd><strong>{esc(patch['version'])}</strong></dd>
<dt>Announced</dt><dd>{esc(fmt_date(patch.get('published_at')))}</dd>
<dt>Source</dt><dd><a href="{esc(patch.get('url',''))}">{esc(patch.get('title',''))}</a></dd>
<dt>Data refreshed</dt><dd>{esc(fmt_date(generated))} <span class="muted">(UTC)</span></dd>
</dl>
</section>
<section class="panel" aria-labelledby="fw-heading">
<h2 id="fw-heading">Core frameworks</h2>
<div class="table-wrap">
<table>
<thead>
<tr><th scope="col">Framework</th><th scope="col">Status</th><th scope="col">Latest release</th><th scope="col">Released</th><th scope="col">Source</th></tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</div>
<details class="reasons">
<summary>Why these statuses?</summary>
<ul>{reasons}</ul>
</details>
<p class="disclaimer">{esc(data.get('disclaimer',''))}</p>
</section>
{newsletter()}
<section class="panel">
<p><a href="/history/">Browse patch history →</a> · <a href="/faq/">FAQ →</a> · <a href="/status.json">Machine-readable JSON →</a></p>
</section>
"""
    return page_shell(
        f"Status — {SITE_NAME}",
        f"Cyberpunk 2077 patch {patch['version']}: live compatibility status for CET, RED4ext, redscript, ArchiveXL, TweakXL, Codeware.",
        "/",
        "home",
        body,
        extra_jsonld=[dataset_ld],
    )


def build_history(data: dict) -> str:
    sections = []
    for entry in data.get("history", []):
        cells = []
        for fw in entry.get("frameworks", []):
            sc = status_class(fw["status"])
            tag = fw.get("release_tag") or "—"
            cells.append(
                f'<li><span class="badge {sc}">{esc(fw["status"])}</span> '
                f'<strong>{esc(fw["short"])}</strong> <code>{esc(tag)}</code></li>'
            )
        sections.append(
            f"""<article class="hist-card" id="patch-{esc(entry['version'])}">
<h3>Patch {esc(entry['version'])}</h3>
<p class="muted">{esc(fmt_date(entry.get('published_at')))} · <a href="{esc(entry.get('url',''))}">{esc(entry.get('title',''))}</a></p>
<ul class="hist-fw">{''.join(cells)}</ul>
</article>"""
        )
    body = f"""
<section class="hero">
<h1>Patch history</h1>
<p class="lede">How core frameworks looked relative to each recent official Cyberpunk 2077 patch. Historical rows use the same honest rules as the home page.</p>
</section>
<section class="hist-list">
{''.join(sections) or '<p>No patch history available.</p>'}
</section>
"""
    return page_shell(
        f"Patch history — {SITE_NAME}",
        "Historical Cyberpunk 2077 patch compatibility for CET, RED4ext, redscript, ArchiveXL, TweakXL, and Codeware.",
        "/history/",
        "history",
        body,
    )


FAQ_ITEMS = [
    {
        "q": "Is it safe to update Cyberpunk?",
        "a": (
            "It depends. Official patches from CD PROJEKT RED are safe for the vanilla game, "
            "but script and native frameworks (CET, RED4ext, redscript, ArchiveXL, TweakXL, Codeware) "
            "often break until their authors ship updates. If you use mods that depend on those "
            "frameworks, wait until this site (and the framework release notes) show support for "
            "the new patch — or block automatic Steam updates and play on your current build. "
            "We never claim certainty without evidence from release dates and notes."
        ),
    },
    {
        "q": "Why did my mods break?",
        "a": (
            "Most Cyberpunk mods that stop working after a patch fail because a core framework "
            "they require has not been updated yet. RED4ext-based plugins, CET scripts, redscript "
            "mods, and XL/Codeware mods are especially fragile across game versions. Update the "
            "frameworks first, then update dependent mods. See the "
            "official modding wiki troubleshooting guide for details."
        ),
    },
    {
        "q": "What do the status labels mean?",
        "a": (
            "Updated for latest patch: the framework's latest GitHub release notes explicitly "
            "mention the current game patch version. Likely OK: the latest release is dated on "
            "or after the patch, but notes do not name that version. Unknown / check: the latest "
            "release is older than the patch (or data is missing) — verify on GitHub/Nexus before updating."
        ),
    },
    {
        "q": "Where does the data come from?",
        "a": (
            "Game patches come from the Steam Web API ISteamNews/GetNewsForApp for app 1091500 "
            "(official community announcements). Framework versions come from the public GitHub "
            "Releases API for each project's repository. No Nexus API key is required for this MVP."
        ),
    },
]


def build_faq(data: dict) -> str:
    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
            }
            for item in FAQ_ITEMS
        ],
    }
    articles = []
    for i, item in enumerate(FAQ_ITEMS):
        articles.append(
            f"""<article class="faq-item" id="faq-{i}">
<h2>{esc(item['q'])}</h2>
<p>{esc(item['a'])}</p>
</article>"""
        )
    body = f"""
<section class="hero">
<h1>FAQ</h1>
<p class="lede">Common questions about updating Cyberpunk 2077 with mods installed.</p>
</section>
<section class="faq-list">
{''.join(articles)}
</section>
"""
    return page_shell(
        f"FAQ — {SITE_NAME}",
        "Is it safe to update Cyberpunk 2077 with mods? Why mods break after patches — FAQ.",
        "/faq/",
        "faq",
        body,
        extra_jsonld=[faq_ld],
    )


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
main { max-width: 960px; margin: 0 auto; padding: 1.5rem 1.25rem 3rem; }
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
@media (max-width: 600px) {
  .patch-meta { grid-template-columns: 1fr; }
  .patch-meta dt { margin-top: .35rem; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
}
"""


OG_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#0a0e17"/>
<text x="80" y="280" fill="#00f0ff" font-family="system-ui,sans-serif" font-size="64" font-weight="700">ModSafe</text>
<text x="80" y="360" fill="#e8eef8" font-family="system-ui,sans-serif" font-size="36">Cyberpunk 2077 framework patch status</text>
</svg>
"""


def build_llms_txt(data: dict) -> str:
    patch = data["game"]["latest_patch"]
    lines = [
        f"# {SITE_NAME}",
        "",
        f"> {SITE_DESC}",
        "",
        f"Site: {SITE_URL}/",
        f"JSON API: {SITE_URL}/status.json",
        f"Generated (UTC): {data.get('generated_at')}",
        "",
        "## Current game patch",
        f"- Version: {patch['version']}",
        f"- Announced: {patch.get('published_at')}",
        f"- Title: {patch.get('title')}",
        f"- URL: {patch.get('url')}",
        "",
        "## Framework statuses",
    ]
    for fw in data["frameworks"]:
        lines.append(
            f"- {fw['name']} ({fw['repo']}): {fw['status']}; "
            f"release {fw.get('release_tag')} on {fw.get('release_published_at')}; "
            f"{fw.get('reason')}"
        )
    lines.extend(
        [
            "",
            "## Pages",
            f"- Home: {SITE_URL}/",
            f"- Patch history: {SITE_URL}/history/",
            f"- FAQ: {SITE_URL}/faq/",
            "",
            "## Citation note",
            "Statuses are inferred from Steam news and GitHub releases; not official CDPR guidance.",
            data.get("disclaimer", ""),
            "",
        ]
    )
    return "\n".join(lines)


def build_robots() -> str:
    return f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""


def build_sitemap() -> str:
    urls = ["/", "/history/", "/faq/", "/status.json", "/llms.txt"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for u in urls:
        parts.append(
            f"  <url><loc>{esc(SITE_URL + u)}</loc><lastmod>{now}</lastmod></url>"
        )
    parts.append("</urlset>")
    return "\n".join(parts) + "\n"


def write(path: Path, content: str, binary: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        path.write_bytes(content)  # type: ignore[arg-type]
    else:
        path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


def main() -> int:
    if not DATA.exists():
        print(f"Missing {DATA}; run ./update first", file=sys.stderr)
        return 1
    data = json.loads(DATA.read_text(encoding="utf-8"))
    print(f"Building site → {DIST} (SITE_URL={SITE_URL})")
    if DIST.exists():
        for p in DIST.rglob("*"):
            if p.is_file():
                p.unlink()
    write(DIST / "index.html", build_home(data))
    write(DIST / "history" / "index.html", build_history(data))
    write(DIST / "faq" / "index.html", build_faq(data))
    write(DIST / "styles.css", CSS)
    write(DIST / "og-default.svg", OG_SVG)
    write(DIST / "status.json", json.dumps(data, indent=2) + "\n")
    write(DIST / "llms.txt", build_llms_txt(data))
    write(DIST / "robots.txt", build_robots())
    write(DIST / "sitemap.xml", build_sitemap())
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
