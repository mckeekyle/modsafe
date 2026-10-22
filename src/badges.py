"""Shields-style SVG status badges (stdlib only): /badge/<slug>.svg.

Left: game + current patch on ModSafe navy with a neon edge. Right: the verdict on the site's verdict colour.
Text widths are estimated from Verdana 11px metrics and pinned with textLength, so the badge renders the same
in GitHub (camo), browsers and Nexus-style image embeds even if the font differs.
"""
from __future__ import annotations

import html

# Approximate Verdana 11px advance widths (px). Anything unlisted uses DEFAULT_W.
_W = {}
for chars, w in (("il.,:;!|'", 3.4), ("fjtrI()[]-/ ", 4.6), ("abcdeghknopqsuvxyzJ", 6.9), ("0123456789$#", 7.0),
                 ("mw", 10.7), ("ABCDEFGHKLNOPRSTUVXYZ", 7.6), ("MW", 9.6), ("Q", 8.6), ("—·&+", 7.0)):
    for c in chars:
        _W[c] = w
DEFAULT_W = 7.0
H = 20
PAD = 6

COLORS = {  # mirrors the --ok/--likely/... CSS variables
    "ok": "#22e07a", "likely": "#ffd23f", "wait": "#ff9f1c", "broken": "#ff4d5e",
    "agnostic": "#7aa2ff", "manual": "#9aa5b8", "unknown": "#9aa5b8",
}
LEFT_BG = "#161f33"
NEON = "#00f0ff"


def text_width(s: str) -> float:
    return round(sum(_W.get(c, DEFAULT_W) for c in s), 1)


def badge_label(game: dict, data: dict) -> str:
    name = game["name"] if len(game["name"]) <= 18 else game["short"]
    patch = (data.get("game") or {}).get("latest_patch", {}).get("label") or ""
    return f"{name} · {patch}" if patch else name


def render_badge(label: str, message: str, status_cls: str, title: str) -> str:
    x = html.escape
    lw = int(round(text_width(label) + 2 * PAD + 3))   # +3 for the neon edge
    mw = int(round(text_width(message) * 1.1 + 2 * PAD))  # bold is ~10% wider
    w = lw + mw
    color = COLORS.get(status_cls, COLORS["unknown"])
    ltw, mtw = text_width(label), round(text_width(message) * 1.1, 1)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{H}" viewBox="0 0 {w} {H}" role="img" aria-label="{x(title)}">
<title>{x(title)}</title>
<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#fff" stop-opacity=".12"/><stop offset="1" stop-opacity=".12"/></linearGradient>
<clipPath id="r"><rect width="{w}" height="{H}" rx="4" fill="#fff"/></clipPath>
<g clip-path="url(#r)">
<rect width="{lw}" height="{H}" fill="{LEFT_BG}"/>
<rect width="3" height="{H}" fill="{NEON}"/>
<rect x="{lw}" width="{mw}" height="{H}" fill="{color}"/>
<rect width="{w}" height="{H}" fill="url(#s)"/>
</g>
<g font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11" text-rendering="geometricPrecision">
<text x="{3 + PAD}" y="14" fill="#010101" fill-opacity=".3" textLength="{ltw}" lengthAdjust="spacingAndGlyphs">{x(label)}</text>
<text x="{3 + PAD}" y="13" fill="#eef3ff" textLength="{ltw}" lengthAdjust="spacingAndGlyphs">{x(label)}</text>
<text x="{lw + PAD}" y="13" fill="#07090f" font-weight="bold" textLength="{mtw}" lengthAdjust="spacingAndGlyphs">{x(message)}</text>
</g>
</svg>
"""


def game_badge(game: dict, data: dict, status_cls: str) -> str:
    label = badge_label(game, data)
    v = data.get("verdict") or "No data"
    return render_badge(label, v, status_cls, f"ModSafe: {label} — mod status {v}")


def png_badge_url(slug: str, site_url: str) -> str:
    from urllib.parse import quote
    return "https://raster.shields.io/endpoint?url=" + quote(f"{site_url}/badge/{slug}.json", safe="")


def embed_snippets(game: dict, site_url: str) -> dict:
    slug, name = game["slug"], game["name"]
    img, page = f"{site_url}/badge/{slug}.svg", f"{site_url}/{slug}/"
    alt = f"ModSafe: {name} mod status"
    return {
        "markdown": f"[![{alt}]({img})]({page})",
        "html": f'<a href="{page}"><img src="{img}" alt="{alt}"></a>',
        # Forum/Nexus BBCode often won't display SVG, so use a PNG rendered by shields.io from our endpoint JSON.
        "bbcode": f"[url={page}][img]{png_badge_url(slug, site_url)}[/img][/url]",
    }
