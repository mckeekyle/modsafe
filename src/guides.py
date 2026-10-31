"""Site-wide guides (/guides/...). Content is hand-written HTML; Steam branch data comes from
data/manual/steam-branches.json (hand-checked against Steam's public app info)."""
from __future__ import annotations

import json
from datetime import date
from html import escape
from pathlib import Path

from games import GAMES, GAMES_BY_SLUG

ROOT = Path(__file__).resolve().parent.parent
BRANCHES_FILE = ROOT / "data" / "manual" / "steam-branches.json"

STEAM_GUIDE_PATH = "/guides/stop-steam-auto-updates/"
STEAM_GUIDE_OG = "guide-stop-steam-auto-updates.png"
GUIDES_OG = "guides.png"
STEAM_GUIDE_TITLE = "How to stop Steam auto-updating a game (and protect your mods)"
STEAM_GUIDE_DESC = ("Steam has no 'never update' button. Here's what actually works in 2026: Wait until I launch the game, "
                    "launching through your mod loader, Offline Mode, Steam Deck, beta branches, download_depot rollbacks and backups.")


def esc(s: object) -> str:
    return escape(str(s), quote=True)


def load_branches() -> dict:
    return json.loads(BRANCHES_FILE.read_text(encoding="utf-8"))


def verified_text(b: dict) -> str:
    d = date.fromisoformat(b["verified"])
    return f"{d:%b} {d.day}, {d.year}"


def steam_games() -> list[dict]:
    """Games sold on Steam (not the Steam Deck platform page)."""
    return [g for g in GAMES if g.get("steam_appid") and g.get("kind_label") != "platform"]


def branch_summary(slug: str, b: dict | None = None) -> str:
    """Plain-text sentence about rollback branches for one game (used in the per-game FAQ)."""
    b = b or load_branches()
    name = GAMES_BY_SLUG[slug]["name"]
    when = verified_text(b["games"][slug] if b["games"].get(slug, {}).get("verified") else b)
    if slug in b["games"]:
        rb = b["games"][slug]["rollback"]
        listed = ", ".join(f"{r['label']} ({r['branch']})" for r in rb)
        return (f"To roll back after a patch, Steam offers older {name} versions under Properties > Game Versions & Betas: "
                f"{listed} (checked {when}).")
    if slug in b.get("beta_only", []):
        return (f"{name} only has a beta (newer) branch on Steam, not a previous-version branch (checked {when}), "
                "so back up the game folder before patches.")
    return (f"Steam has no previous-version branch for {name} (checked {when}), so back up the game folder before patches; "
            "rolling back otherwise means the Steam console's download_depot command.")


def game_faq_item(game: dict, b: dict | None = None) -> dict | None:
    if not game.get("steam_appid") or game.get("kind") == "minecraft":
        return None
    if game.get("kind_label") == "platform":
        return {"q": "How do I stop Steam Deck games from updating and breaking mods?",
                "a": "Per game: select the game, press the gear icon > Properties > Updates and choose 'Wait until I launch the game'. "
                     "To keep playing without an update, enter Offline Mode (Steam button > Settings > Internet) while still online. "
                     "SteamOS itself updates separately and can break Decky Loader, which is what this page tracks. "
                     f"Step-by-step guide: modsafe.app{STEAM_GUIDE_PATH}"}
    name = game["name"]
    return {"q": f"How do I stop Steam from auto-updating {name}?",
            "a": (f"Steam has no 'never update' option. In your Library, open {name} > Manage > Properties > Updates and set "
                  "Automatic updates to 'Wait until I launch the game', then launch through your mod loader or play in Offline Mode. "
                  f"{branch_summary(game['slug'], b)} Full guide: modsafe.app{STEAM_GUIDE_PATH}")}


STEAM_GUIDE_FAQ = [
    {"q": "Can I permanently stop Steam from updating a game?",
     "a": "No. Steam has no 'never update' setting. 'Wait until I launch the game' only delays the update until you press Play, "
          "and Steam updates the game before it starts. The only built-in way to keep playing an old version is Offline Mode, "
          "or a previous-version branch if the developer offers one under Game Versions & Betas."},
    {"q": "Does 'Wait until I launch the game' stop updates?",
     "a": "It stops background downloads, nothing more. When you press Play in Steam, the update downloads and installs first. "
          "Pair it with Offline Mode, or with launching through your script extender or mod manager, to stay on your current version. "
          "On older Steam clients the same option is called 'Only update this game when I launch it'."},
    {"q": "How do I roll back a Steam game to an older version?",
     "a": "First check Properties > Game Versions & Betas: some games (Cyberpunk 2077, Baldur's Gate 3, Stardew Valley, Valheim, RimWorld, "
          "Bannerlord, Lethal Company, Terraria, Europa Universalis V) keep previous versions there. If not, use the Steam console command "
          "download_depot <appid> <depotid> <manifestid> with IDs from SteamDB, or DepotDownloader, then copy the files over a backup "
          "of your game folder. Skyrim SE, Fallout 4, Starfield, Elden Ring and GTA V have no rollback branch."},
    {"q": "Does Steam Offline Mode still work in 2026?",
     "a": "Yes. Sign in with 'Remember my password', launch the game once while online, then use Steam > Go Offline (on Steam Deck: "
          "Steam button > Settings > Internet). Games with an extra launcher or online DRM may still need internet, and multiplayer won't work."},
    {"q": "Is making the appmanifest file read-only a good way to block updates?",
     "a": "No. Setting appmanifest_<appid>.acf read-only is an old hack that recent Steam clients overwrite or ignore, and players report "
          "games updating anyway. Use Offline Mode and a backup instead."},
    {"q": "How do I know when it's safe to update my modded game?",
     "a": "Check the game's ModSafe page: it shows whether script extenders and mod loaders (SKSE, F4SE, RED4ext, BG3SE, SMAPI, BepInEx and more) "
          "support the latest patch. Each game also has an Atom feed for verdict changes and an embeddable status badge."},
]


def steam_tips(b: dict) -> str:
    rows = []
    for slug, info in b["games"].items():
        g = GAMES_BY_SLUG[slug]
        brs = "<br>".join(f"<code>{esc(r['branch'])}</code> <span class=\"muted\">{esc(r['label'])}</span>" for r in info["rollback"])
        note = f'<br><span class="muted">{esc(info["note"])}</span>' if info.get("note") else ""
        rows.append(f'<tr><td><a href="/{esc(slug)}/">{esc(g["name"])}</a></td><td>{brs}{note}</td></tr>')
    return "".join(rows)


def none_list(b: dict) -> str:
    return ", ".join(f'<a href="/{esc(s)}/">{esc(GAMES_BY_SLUG[s]["name"])}</a>' for s in b["none"])


def steam_guide_body(faq_html: str) -> str:
    b = load_branches()
    when = verified_text(b)
    beta_links = [f'<a href="/{esc(s)}/">{esc(GAMES_BY_SLUG[s]["name"])}</a>' for s in b.get("beta_only", [])]
    beta = " and ".join(beta_links) if len(beta_links) <= 2 else ", ".join(beta_links[:-1]) + " and " + beta_links[-1]
    game_links = " ".join(f'<a href="/{esc(g["slug"])}/">{esc(g["short"])}</a>' for g in steam_games())
    return f"""
<p class="crumbs"><a href="/">Home</a> › <a href="/guides/">Guides</a> › Stop Steam auto-updates</p>
<section class="game-hero guide-hero v-wait" style="--hero:url('/img/steam-deck-hero.webp')">
<div>
<p class="eyebrow">Guide · checked {esc(when)}</p>
<h1>How to stop Steam auto-updating a game</h1>
<p class="lede">A patch can break your script extender and every mod that depends on it. Here's every method that still works in 2026 to hold an update, play your current version, and roll back if Steam updated anyway.</p>
<p class="note" role="note"><strong>Honest answer first: Steam has no “never update” option.</strong> The per-game setting only delays the download until you press Play. To keep playing an old version you need Offline Mode, your mod loader, a previous-version branch, or a backup.</p>
</div>
</section>
<nav class="tabs" aria-label="On this page"><a href="#quick">Quick fix</a><a href="#wait-until-launch">Update setting</a><a href="#loader">Mod loader</a><a href="#offline">Offline Mode</a><a href="#steam-deck">Steam Deck</a><a href="#branches">Old versions</a><a href="#rollback">Roll back</a><a href="#backup">Backup</a><a href="#after-patch">After a patch</a><a href="#faq-heading">FAQ</a></nav>

<section class="panel guide" id="quick">
<h2>Quick fix (before patch day)</h2>
<ol>
<li><strong>Back up</strong> the game folder and your mod manager's folder (<a href="#backup">how</a>).</li>
<li>Set the game to <strong>Wait until I launch the game</strong> (<a href="#wait-until-launch">steps</a>).</li>
<li>Launch through your <strong>script extender or mod manager</strong>, not Steam's Play button, or go <strong>Offline</strong> before you play (<a href="#offline">steps</a>).</li>
<li>Check the game's ModSafe page and only update once your frameworks say <strong>Safe</strong> (<a href="#after-patch">links</a>).</li>
<li>Already updated? Look for an older version under <strong>Game Versions &amp; Betas</strong> (<a href="#branches">which games have one</a>) or <a href="#rollback">roll back with download_depot</a>.</li>
</ol>
</section>

<article class="panel guide">
<h2 id="wait-until-launch">1. Set “Wait until I launch the game”</h2>
<p>This stops Steam downloading updates in the background. It's per game:</p>
<ol>
<li>In your Steam <strong>Library</strong>, right-click the game (or click the gear icon on its page) and choose <strong>Properties</strong>.</li>
<li>Open <strong>Updates</strong>.</li>
<li>Under <strong>Automatic Updates</strong>, choose <strong>Wait until I launch the game</strong>. Older clients and <a href="https://help.steampowered.com/en/faqs/view/71AB-698D-57EB-178C" rel="noopener external">Steam Support</a> call it “Only update this game when I launch it”.</li>
</ol>
<p>To make it the default for every game: <strong>Steam → Settings → Downloads → Updates to installed games</strong> and pick <strong>Wait until I launch the game</strong>. <strong>Manage exceptions</strong> next to it lists any game set differently. While you're there, turn off <strong>Allow downloads during gameplay</strong>.</p>
<p class="muted">The catch: pressing Play in Steam installs the update first, and Steam won't start the old version. The next two steps get around that.</p>

<h2 id="loader">2. Launch through your mod loader, not Steam</h2>
<p>Many modded games are started through a loader anyway: <code>skse64_loader.exe</code> (<a href="/skyrim-se/">Skyrim SE</a>), <code>f4se_loader.exe</code> (<a href="/fallout-4/">Fallout 4</a>), <code>sfse_loader.exe</code> (<a href="/starfield/">Starfield</a>), Mod Organizer 2, or a desktop shortcut. With the update set to wait, starting the game this way usually skips Steam's update step, because Steam only applies the queued update when you press Play in the client.</p>
<p class="muted">It's not guaranteed. Some games relaunch through Steam, and Steam may still start a queued download. If it matters, go offline first.</p>

<h2 id="offline">3. Play in Offline Mode</h2>
<p><a href="https://www.pcgamingwiki.com/wiki/Steam" rel="noopener external">PCGamingWiki</a> calls Offline Mode the only built-in way to play without taking an update. Set it up <em>before</em> the patch lands:</p>
<ol>
<li>Sign in with <strong>Remember my password</strong> ticked.</li>
<li>Launch the game once while online so Steam has a valid ticket for it.</li>
<li>Choose <strong>Steam → Go Offline…</strong> and restart into Offline Mode.</li>
</ol>
<p>If the library button says <strong>Update</strong> while you're offline, Steam usually lets you launch the installed version instead. When you go back online, a game set to “Wait until I launch the game” still won't update until you press Play.</p>
<p class="muted">Limits: multiplayer, the Workshop and cloud saves don't sync offline. Games with their own launcher or online DRM (for example the Rockstar launcher for <a href="/gta-v/">GTA V</a>) may still need internet.</p>

<h2 id="steam-deck">4. Steam Deck</h2>
<ul>
<li><strong>Update setting:</strong> select the game in your library, press the gear icon → <strong>Properties → Updates</strong> and choose <strong>Wait until I launch the game</strong>. <strong>Game Versions &amp; Betas</strong> is in the same menu.</li>
<li><strong>Offline Mode:</strong> while still online, launch the game once, then press the <strong>Steam</strong> button → <strong>Settings → Internet → Enter Offline Mode</strong>. Older SteamOS builds also had “Go Offline” in the Power menu.</li>
<li><strong>Backups:</strong> in Desktop Mode the games live in <code>~/.local/share/Steam/steamapps/common/</code>. Games on a microSD card are under <code>/run/media/</code>.</li>
<li><strong>SteamOS updates are separate.</strong> They can break Decky Loader and its plugins. ModSafe tracks that on the <a href="/steam-deck/">Steam Deck page</a>.</li>
</ul>

<h2 id="branches">5. Switch to an older version (Game Versions &amp; Betas)</h2>
<p>Some developers keep previous versions on Steam. Open <strong>Properties → Game Versions &amp; Betas</strong> (“Betas” on older clients) and pick one. Steam downloads that version and won't move you off it until you switch back. These branches existed on Steam on {esc(when)}, with no password needed:</p>
<div class="table-wrap"><table>
<thead><tr><th scope="col">Game</th><th scope="col">Previous-version branches</th></tr></thead>
<tbody>{steam_tips(b)}</tbody>
</table></div>
<p><strong>No rollback branch:</strong> {none_list(b)}. {beta} only offer a <em>beta</em> (newer) branch. For those games, back up before patches or use <a href="#rollback">download_depot</a>.</p>
<p class="muted">Saves made on a newer version may not load on an older one, and your frameworks must match the version you pick. Check the release notes on each game's ModSafe page.</p>

<h2 id="rollback">6. Roll back with the Steam console (download_depot)</h2>
<p>Steam can download any older build of a game you own. This is the method <a href="https://www.pcgamingwiki.com/wiki/Steam" rel="noopener external">PCGamingWiki</a> documents:</p>
<ol>
<li>Find the game's <strong>app ID</strong>, the <strong>depot ID</strong> holding the game files, and the <strong>manifest ID</strong> of the build you want. The game's <em>Depots → Manifests</em> page on SteamDB lists them by date, for example <a href="https://steamdb.info/app/1091500/depots/" rel="noopener external">Cyberpunk 2077's depots</a>.</li>
<li>Open the console: paste <code>steam://open/console</code> (or <code>steam://nav/console</code>) into your browser's address bar or Win+R and let it open Steam.</li>
<li>Run <code>download_depot &lt;appid&gt; &lt;depotid&gt; &lt;manifestid&gt;</code> and wait for “Depot download complete”. It reports the folder, inside <code>steamapps\\content\\app_&lt;appid&gt;\\depot_&lt;depotid&gt;</code>.</li>
<li>Move those files out of Steam's folder (Steam can clean it up), then copy them over a <a href="#backup">copy of your game folder</a>. Repeat for each depot that changed.</li>
<li>Play from that copy in Offline Mode or through your loader so Steam doesn't “fix” it. Some games need a <code>steam_appid.txt</code> with the app ID next to the .exe to run outside the Steam folder.</li>
</ol>
<p><strong>DepotDownloader</strong> does the same thing outside Steam. It's an open-source command-line tool, 3.4.0 at the time of writing, from <a href="https://github.com/SteamRE/DepotDownloader" rel="noopener external">SteamRE/DepotDownloader</a> (also <code>winget install --exact --id SteamRE.DepotDownloader</code>):</p>
<pre><code>DepotDownloader -app &lt;appid&gt; -depot &lt;depotid&gt; -manifest &lt;manifestid&gt; -username &lt;you&gt; -dir old-version</code></pre>
<p class="muted">DepotDownloader needs your Steam login. Use <code>-qr</code> to sign in by scanning a QR code with the Steam mobile app. Download it only from the official GitHub page. Neither method works for games you don't own.</p>

<h2 id="backup">7. Back up your game folder</h2>
<p>A backup is the only rollback that works for every game. Do it before patch day:</p>
<ol>
<li>Right-click the game → <strong>Manage → Browse local files</strong>. On Windows that's usually <code>C:\\Program Files (x86)\\Steam\\steamapps\\common\\&lt;Game&gt;</code>.</li>
<li>Copy the whole folder somewhere outside <code>steamapps</code>.</li>
<li>Also copy your <strong>mod manager's data</strong> (the Mod Organizer 2 instance or Vortex staging folder) and your <strong>saves</strong>, usually in <code>Documents\\My Games</code> or <code>%LOCALAPPDATA%</code>.</li>
<li>To restore after an unwanted patch, go offline and copy the backup back over the game folder.</li>
</ol>

<h3 id="read-only">What about the read-only appmanifest trick?</h3>
<p>Old guides suggest making <code>steamapps\\appmanifest_&lt;appid&gt;.acf</code> read-only (or using <code>chattr +i</code> on Linux and Steam Deck) so Steam thinks the game is current. Recent Steam clients overwrite or ignore it, and players still report games updating anyway. <strong>Don't rely on it.</strong> Use Offline Mode and a backup instead.</p>
</article>

<div class="sec-head" id="after-patch"><h2>After a patch: is it safe to update?</h2><a href="/games/">All games →</a></div>
<section class="panel guide">
<p>Every ModSafe game page checks whether the script extenders and mod loaders support the newest patch, and updates every 6 hours. Update once yours says <strong>Safe</strong>:</p>
<p class="links">{game_links} <a href="/steam-deck/">Steam Deck</a></p>
<p><strong>Get told when it changes:</strong> each game has an Atom feed for new patches and verdict changes (for example <a href="/cyberpunk-2077/feed.xml">/cyberpunk-2077/feed.xml</a>, or <a href="/feed.xml">/feed.xml</a> for every game) that works in any feed reader or a Discord RSS bot. No account or email needed.</p>
<p><strong>Mod authors:</strong> show players the live status on your mod page with a badge. Copy the snippet from the Follow &amp; embed section of any game page, for example <a href="/skyrim-se/#follow">Skyrim SE's</a>:</p>
<img class="badge-preview" src="/badge/skyrim-se.svg" alt="ModSafe status badge for Skyrim SE" height="20" loading="lazy">
</section>

<div class="sec-head"><h2 id="faq-heading">FAQ</h2></div>
<section class="faq-list" aria-labelledby="faq-heading">{faq_html}</section>
<p class="disclaimer">Sources: <a href="https://help.steampowered.com/en/faqs/view/71AB-698D-57EB-178C" rel="noopener external">Steam Support: Managing downloads &amp; updates</a>, <a href="https://store.steampowered.com/news/app/593110/view/4696782040345941641" rel="noopener external">Steam client update notes</a>, <a href="https://www.pcgamingwiki.com/wiki/Steam" rel="noopener external">PCGamingWiki: Steam</a>, <a href="https://github.com/SteamRE/DepotDownloader" rel="noopener external">DepotDownloader</a>. Branch list checked against Steam's public app info on {esc(when)}. Not affiliated with Valve.</p>
<section class="links"><a href="/guides/">📚 All guides</a> <a href="/faq/">❓ FAQ</a> <a href="/games/">🎮 All games</a></section>
"""


def guides_index_body(install_guides: list[dict]) -> str:
    items = [f'<article class="panel guide-card"><h2><a href="{STEAM_GUIDE_PATH}">How to stop Steam auto-updating a game</a></h2>'
             f'<p>{esc(STEAM_GUIDE_DESC)}</p></article>']
    for g in install_guides:
        items.append(f'<article class="panel guide-card"><h2><a href="/{esc(g["slug"])}/install/">How to install {esc(g["name"])} mods</a></h2>'
                     f'<p>Beginner step-by-step setup for {esc(g["name"])} mods, with common pitfalls and how to roll back.</p></article>')
    return f"""
<p class="crumbs"><a href="/">Home</a> › Guides</p>
<section class="page-hero"><h1>Guides</h1><p class="lede">Keeping modded games working through patches: holding updates, rolling back, and setting up mods properly.</p></section>
<section class="guide-grid">{"".join(items)}</section>
"""
