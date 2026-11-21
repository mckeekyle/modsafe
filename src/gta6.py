"""/gta-6/: "Does GTA 6 have mods?" A hand-maintained info page (data/manual/gta-6.json), not a tracked game:
GTA VI launched on consoles only (Nov 19, 2026) and has no PC version yet, so there is nothing to give a verdict on.
It shows a PC release countdown only once Rockstar announces an official date; reported windows are labelled as
unconfirmed and never counted down."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "manual" / "gta-6.json"
PATH = "/gta-6/"
TITLE = "Does GTA 6 have mods? PC release date and mod status"
H1 = "Does GTA 6 have mods?"


def esc(s: object) -> str:
    return escape(str(s), quote=True)


def load() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def fmt(d: str | None) -> str:
    if not d:
        return ""
    x = date.fromisoformat(d)
    return f"{x:%B} {x.day}, {x.year}"


def countdown_date(d: dict) -> date | None:
    """The official PC release date to count down to, or None (not announced / already released / not official)."""
    pc = d["pc_release"]
    if pc.get("status") == "announced" and pc.get("date") and pc.get("date_source"):
        return date.fromisoformat(pc["date"])
    return None


def days_until(target: date, today: date | None = None) -> int:
    return (target - (today or datetime.now(timezone.utc).date())).days


def pc_status_text(d: dict) -> str:
    pc = d["pc_release"]
    if pc.get("status") == "released":
        return f"Out now on PC (released {fmt(pc.get('date'))})"
    if countdown_date(d):
        return f"Coming {fmt(pc['date'])} (announced by Rockstar)"
    return "Not announced by Rockstar"


def mods_status_text(d: dict) -> str:
    if d["pc_release"].get("status") == "released":
        return "PC version is out: check this page for Script Hook and mod tool status"
    return "Not possible yet: GTA 6 mods need the PC version"


def faq(d: dict) -> list[dict]:
    c, pc, h = d["console_release"], d["pc_release"], d["history"]
    rep = pc.get("reported") or {}
    pc_answer = (f"Yes: Rockstar has announced {fmt(pc['date'])} for the PC version." if countdown_date(d) else
                 "Rockstar hasn't announced a PC version or date yet. "
                 + (f"{rep['by'].split(',')[0]} has reported a {rep['window']} PC window, but that's unconfirmed. " if rep else "")
                 + "Rockstar's last two big games reached PC "
                 + " and ".join(f"{x['gap']} after console ({x['game']})" for x in h) + ".")
    return [
        {"q": "Does GTA 6 have mods?",
         "a": f"Not yet. GTA 6 launched on {fmt(c['date'])} on {' and '.join(c['platforms'])} only, and console versions can't load mods. "
              "GTA mods have always needed the PC version, so they'll start once GTA 6 comes to PC."},
        {"q": "Can you mod GTA 6 on PS5 or Xbox?",
         "a": "No. Consoles only run unmodified, signed games. Anything sold or shared as a 'GTA 6 mod menu' for PS5 or Xbox is a scam "
              "or a cheat that can get your account banned."},
        {"q": "When is GTA 6 coming to PC?", "a": pc_answer},
        {"q": "When will GTA 6 PC mods come out?",
         "a": "Soon after the PC version, if GTA V is a guide: Script Hook V and the first script mods appeared within weeks of GTA V's "
              "April 2015 PC launch. Expect the first GTA 6 mods to be simple scripts and texture swaps, and expect early game "
              "patches to break them often."},
        {"q": "Will Rockstar allow GTA 6 mods?",
         "a": "Rockstar's current PC Single-Player Mods policy says Take-Two generally won't take legal action against PC mods that "
              "are single-player, non-commercial and respect others' intellectual property. It was written for Rockstar's existing PC "
              "games; Rockstar hasn't said yet how it will apply to GTA 6. Online mods are not allowed."},
        {"q": "Do GTA V mods work in GTA 6?",
         "a": "No. GTA 6 is a different game, so GTA V mods, Script Hook V, trainers and OpenIV won't load in it. GTA 6 will need its own tools."},
        {"q": "Is there a GTA 6 PC download?",
         "a": "No. There's no official PC version, so any 'GTA 6 PC download', 'crack', 'early access' or 'beta' file is fake and "
              "likely malware. Don't run it."},
    ]


def countdown_html(d: dict) -> str:
    target = countdown_date(d)
    if not target:
        return ""
    n = days_until(target)
    pc = d["pc_release"]
    fallback = f"{n} days to go" if n > 1 else ("1 day to go" if n == 1 else "Out today")
    return (f'<aside class="upcoming g6-countdown" role="note" aria-label="GTA 6 PC release countdown">'
            f'<p class="up-title">⏳ GTA 6 on PC: {esc(fmt(pc["date"]))}</p>'
            f'<p class="g6-count" data-target="{esc(pc["date"])}">{esc(fallback)}</p>'
            f'<p class="up-src">Official source: <a href="{esc(pc["date_source"])}" rel="noopener external">Rockstar Games</a>. '
            f'Mods can start once it\'s out; this page will then track Script Hook and mod tool support.</p></aside>'
            + COUNTDOWN_JS)


COUNTDOWN_JS = """<script>
(function(){var e=document.querySelector('.g6-count');if(!e)return;var p=e.getAttribute('data-target').split('-');
var t=new Date(+p[0],+p[1]-1,+p[2]).getTime();function u(){var s=Math.max(0,Math.floor((t-Date.now())/1000));
if(s===0){e.textContent='Out today';return;}var d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);
e.textContent=d+' days, '+h+' h, '+m+' min to go';}u();setInterval(u,30000);})();
</script>"""


def body(d: dict, editions: list[tuple[dict, dict]], badge, faq_html: str) -> str:
    """editions: [(game, data)] for GTA V Legacy/Enhanced; badge: build.badge."""
    c, pc = d["console_release"], d["pc_release"]
    rep = pc.get("reported") or {}
    hist = "".join(f"<li><strong>{esc(x['game'])}</strong>: console {esc(fmt(x['console']))}, PC {esc(fmt(x['pc']))} ({esc(x['gap'])} later)</li>"
                   for x in d["history"])
    reported = ""
    if rep and not countdown_date(d) and pc.get("status") != "released":
        reported = (f'<p><strong>Reported, not confirmed:</strong> a PC release in {esc(rep["window"])}. Source: {esc(rep["by"])} '
                    f'(<a href="{esc(rep["source"])}" rel="noopener external">report</a>). We\'ll start a countdown only when Rockstar '
                    f'announces an official date.</p>')
    gta5 = "".join(f'<li><a href="/{g["slug"]}/">{esc(g["name"])}</a> {badge(dd["verdict"])} '
                   f'<span class="muted">{esc(dd["game"]["latest_patch"]["label"])}</span> · '
                   f'<a href="/{g["slug"]}/mods/">essential mods</a> · <a href="/{g["slug"]}/install/">install guide</a></li>'
                   for g, dd in editions)
    return f"""
<p class="crumbs"><a href="/">Home</a> › <a href="/games/">Games</a> › GTA 6</p>
<section class="page-hero"><h1>{esc(H1)}</h1>
<p class="lede">Not yet. GTA 6 came out on {esc(fmt(c['date']))} for {esc(' and '.join(c['platforms']))} only, and console games can't be
modded. GTA mods need the PC version, which Rockstar hasn't announced. Here's what's confirmed, what's only rumoured, and what to
mod while you wait.</p></section>
{countdown_html(d)}
<section class="panel"><div class="ed-ids">
<div class="ed-id"><h2 class="panel-h">Consoles</h2><p>Out {esc(fmt(c['date']))} on {esc(', '.join(c['platforms']))}. No mods.</p>
<p class="muted"><a href="{esc(c['source'])}" rel="noopener external">Rockstar Newswire</a></p></div>
<div class="ed-id"><h2 class="panel-h">PC version</h2><p>{esc(pc_status_text(d))}.</p>
<p class="muted">{esc(pc.get('official_note') or '')} {f'<a href="{esc(pc["official_note_source"])}" rel="noopener external">Source</a>' if pc.get('official_note_source') else ''}</p></div>
<div class="ed-id"><h2 class="panel-h">Mods</h2><p>{esc(mods_status_text(d))}.</p>
<p class="muted">ModSafe will track GTA 6's PC patches and mod tools the way it tracks <a href="/gta-v/">GTA V</a>.</p></div>
</div></section>
<div class="sec-head"><h2 id="pc">When is GTA 6 coming to PC?</h2></div>
<section class="panel guide">
<p>Rockstar hasn't said. {reported}</p>
<p>Rockstar's recent big releases came to PC well after console:</p><ul>{hist}</ul>
<p class="muted">Last checked {esc(fmt(d['last_verified']))}.</p>
</section>
<p class="note" role="note"><strong>⚠ There is no GTA 6 PC download. Any "GTA 6 PC", crack, "early access" build or console "mod menu" is fake
and likely malware or a ban risk. Don't run it.</strong></p>
<div class="sec-head"><h2 id="gta5">Mod GTA V while you wait</h2><a href="/gta-v/">Which edition? →</a></div>
<section class="panel"><p>GTA V's PC mod scene is huge, and it works today. Check it's safe to update first:</p>
<ul class="hub-list">{gta5}</ul></section>
<div class="sec-head"><h2 id="faq-heading">GTA 6 modding FAQ</h2></div>
<section class="faq-list" aria-labelledby="faq-heading">{faq_html}</section>
<p class="disclaimer">ModSafe isn't affiliated with Rockstar Games or Take-Two. Facts on this page are hand-checked and sourced;
rumours are labelled. Mod policy: <a href="{esc(d['mod_policy']['source'])}" rel="noopener external">{esc(d['mod_policy']['source_title'])}</a>.</p>
<section class="links" aria-label="Related pages"><a href="/gta-v/">🎮 GTA V mod status</a> <a href="/gta-v-enhanced/">🎮 GTA V Enhanced</a>
<a href="/gta-v-legacy/">🎮 GTA V Legacy</a> <a href="/games/">🎮 All games</a></section>
"""


def description(d: dict) -> str:
    if countdown_date(d):
        return (f"No GTA 6 mods yet: it's console-only until the PC version on {fmt(d['pc_release']['date'])}. "
                "Countdown, what Rockstar allows, and when mods will start.")
    rep = d["pc_release"].get("reported") or {}
    window = f"the reported {rep['window']} PC window" if rep else "the PC rumours"
    return (f"No: GTA 6 is console-only and Rockstar hasn't announced a PC date. What's confirmed, {window}, "
            "and what to mod while you wait.")
