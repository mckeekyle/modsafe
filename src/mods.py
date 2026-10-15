"""Essential mods lists (data/mods/<slug>.json) and install guides (data/guides/<slug>.md).

Curated by hand; we only ever link to official download pages (Nexus, GitHub, Thunderstore, Modrinth,
flightsim.to, official sites) and never host files. Compat badges are derived from our framework data.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODS_DIR = ROOT / "data" / "mods"
GUIDES_DIR = ROOT / "data" / "guides"
ALLOWED_HOSTS = ("www.nexusmods.com", "nexusmods.com", "github.com", "thunderstore.io", "modrinth.com", "flightsim.to",
                 "smapi.io", "skse.silverlock.org", "fsuipc.com", "www.fsuipc.com", "navigraph.com", "www.navigraph.com",
                 "flybywiresim.com", "docs.flybywiresim.com", "www.flightsimulator.com", "flightsimulator.com", "parallel42.com")
# Severity order for the "worst required framework" compat badge.
RANK = ["Breakage reported", "Not ported yet", "Just patched, wait", "No data", "Check manually", "Likely safe", "Safe",
        "Not affected by patches"]


def load_mods(slug: str) -> dict | None:
    p = MODS_DIR / f"{slug}.json"
    return json.loads(p.read_text()) if p.exists() else None


def load_guide(slug: str) -> str | None:
    p = GUIDES_DIR / f"{slug}.md"
    return p.read_text() if p.exists() else None


def _inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return re.sub(r"\[(.+?)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)


def md_to_html(md: str) -> str:
    """Tiny Markdown subset (headings, paragraphs, -/1. lists, bold, code, links): no build dependency."""
    out, lst = [], None
    for line in md.splitlines():
        m_ul, m_ol, m_h = re.match(r"^- (.*)", line), re.match(r"^\d+\. (.*)", line), re.match(r"^(#{1,3}) (.*)", line)
        kind = "ul" if m_ul else "ol" if m_ol else None
        if lst and kind != lst:
            out.append(f"</{lst}>")
            lst = None
        if m_h:
            lvl = len(m_h.group(1)) + 1  # page already has an h1
            slugid = re.sub(r"[^a-z0-9]+", "-", m_h.group(2).lower()).strip("-")
            out.append(f'<h{lvl} id="{slugid}">{_inline(m_h.group(2))}</h{lvl}>')
        elif kind:
            if not lst:
                out.append(f"<{kind}>")
                lst = kind
            out.append(f"<li>{_inline((m_ul or m_ol).group(1))}</li>")
        elif line.strip():
            out.append(f"<p>{_inline(line)}</p>")
    if lst:
        out.append(f"</{lst}>")
    return "\n".join(out)


def guide_parts(md: str) -> dict:
    """Split guide into title, intro and the ordered '## Steps' list (for HowTo JSON-LD)."""
    title = re.search(r"^# (.+)$", md, re.M).group(1)
    body = re.sub(r"^# .+\n", "", md, count=1, flags=re.M)
    steps_block = re.search(r"^## Steps\n(.*?)(?=^## |\Z)", body, re.M | re.S)
    steps = []
    for line in (steps_block.group(1) if steps_block else "").splitlines():
        m = re.match(r"^\d+\. \*\*(.+?)\*\*\s*(.*)", line)
        if m:
            steps.append({"name": m.group(1).rstrip("."), "text": m.group(2)})
    intro = body.strip().split("\n\n")[0]
    return {"title": title, "body": body, "steps": steps, "intro": re.sub(r"\*\*|`", "", intro)}


def compat(mod: dict, game_data: dict) -> tuple[str, str]:
    """(status, explanation) from our framework data: the mod's own status if it is a tracked framework,
    else the worst status among the tracked frameworks it requires, else 'Check manually'."""
    fws = {f["id"]: f for f in game_data.get("frameworks", [])}
    if mod.get("framework_id") in fws:
        f = fws[mod["framework_id"]]
        return f["status"], f"Tracked framework: {f['status']} for the latest patch."
    req = [fws[r] for r in mod.get("requires", []) if r in fws and fws[r].get("tracked", True)]
    if not req:
        return "Check manually", "Doesn't depend on a tracked framework; check its page after big patches."
    worst = min(req, key=lambda f: RANK.index(f["status"]) if f["status"] in RANK else 0)
    return worst["status"], "Needs " + ", ".join(f["short"] for f in req) + f"; weakest link: {worst['short']} ({worst['status']})."
