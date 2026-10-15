# ModSafe — mod framework status after game patches

**https://modsafe.app**

Static site that tracks whether each game's core mod frameworks/loaders have caught up after an official patch.

| Game | Page | Patch source | Frameworks |
|------|------|--------------|------------|
| Cyberpunk 2077 | `/cyberpunk-2077/` | Steam news (1091500) | CET, RED4ext, redscript, ArchiveXL, TweakXL, Codeware (GitHub releases) |
| Skyrim SE/AE | `/skyrim-se/` | Steam news (489830) | SKSE64 (GitHub tags), Engine Fixes, Papyrus Extender, Crash Logger (GitHub releases); Address Library (Nexus, manual) |
| Fallout 4 | `/fallout-4/` | Steam news (377160) | F4SE (GitHub tags); Address Library, Buffout 4 NG (Nexus, manual) |
| Baldur's Gate 3 | `/baldurs-gate-3/` | Steam news (1086940) | Norbyte/bg3se, LaughingLeader/BG3ModManager |
| Stardew Valley | `/stardew-valley/` | Steam news (413150) | SMAPI (+ link to smapi.io/mods) |
| Lethal Company | `/lethal-company/` | Steam news (1966720) | BepInExPack, LethalLib, LethalLevelLoader, MoreCompany (Thunderstore API) |
| GTA V (single-player) | `/gta-v/` | Hand-maintained `data/manual/gta-v.json` (Legacy 271590 + Enhanced 3240220 builds) | Script Hook V (manual, never fetched from dev-c.com), Ultimate ASI Loader (GitHub, version-agnostic) |
| Starfield | `/starfield/` | Steam news (1716740) | SFSE (GitHub tags); Address Library (Nexus, manual) |
| Elden Ring | `/elden-ring/` | Steam news (1245620) | Seamless Co-op, Mod Engine 3 (me3) |
| Valheim | `/valheim/` | Steam news (892970) | BepInExPack Valheim (Thunderstore), Jötunn (GitHub) |
| Terraria | `/terraria/` | Steam news (105600) | tModLoader (GitHub) |
| RimWorld | `/rimworld/` | Steam news (294100) | Harmony (agnostic), HugsLib (GitHub) |
| Mount & Blade II: Bannerlord | `/bannerlord/` | Steam news (261550) | BLSE, Harmony (agnostic) |
| Minecraft Java | `/minecraft/` | Mojang version manifest | Fabric Loader (meta), Fabric API/Sodium/Iris/Lithium (Modrinth), Forge (promotions), NeoForge (Maven) |

Games are configured in `src/games.py`. "Manual" items (Nexus-only) are linked but excluded from the verdict; ModSafe never scrapes Nexus or SteamDB.
A game's verdict is the weakest status among its auto-tracked frameworks.

Statuses are evidence-based and deliberately cautious:

| Label | Meaning |
|-------|---------|
| **Safe** | A release explicitly supports the current patch (notes mention it, incl. "upcoming" releases ≤7 days before; maintainer page e.g. silverlock.org lists the runtime; or a stable build exists for the MC version) |
| **Likely safe** | Release dated after the patch without naming it, or patch >7 days old with no open breakage issues (issues filed within 30 days of the patch whose titles mention crash/broken + update/patch/version) |
| **Just patched, wait** | Patch <7 days old and no post-patch release |
| **Breakage reported** | Open GitHub issues report breakage after the patch |
| **Not ported yet** | Minecraft: no build for that version |
| **Not affected by patches** | Version-agnostic tool (BG3 Mod Manager, BepInExPack); excluded from verdict |
| **Check manually** | Nexus-only (Address Library, Buffout 4); excluded from verdict |

A game's verdict is the worst label among its patch-sensitive, auto-tracked frameworks. Raw evidence (`base_status`, `breakage_reports`, `official`) is kept in each game's JSON.

## Quick start

```bash
# No third-party Python packages required (stdlib only).
./update          # fetch all games → data/games/<slug>.json (./update skyrim-se for one game)
./build           # generate dist/ (defaults SITE_URL=https://modsafe.app)
python3 -m http.server 8080 --directory dist
```

Override the public URL if needed:

```bash
export SITE_URL=https://modsafe.app
./build
```

Optional GitHub API token (higher rate limit for cron):

```bash
export GITHUB_TOKEN=ghp_...   # or GH_TOKEN
./update
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Project layout

```
update / build          CLI wrappers
src/games.py            Game + framework configuration
src/update.py           Fetchers (Steam, GitHub, Thunderstore, Mojang, Fabric, Forge, NeoForge, Modrinth)
src/build.py            Static site generator → dist/
src/status_logic.py     Pure status / parsing logic (unit-tested)
data/games/*.json       Generated per-game datasets (kept if a fetch fails)
dist/                   Deployable static site (Cloudflare Pages publish dir)
tests/                  Unit tests (no network)
.github/workflows/      Scheduled update + commit for Cloudflare rebuild
```

## Deploy to Cloudflare Pages (recommended)

Domain **modsafe.app** is on Cloudflare. Host the static site on **Cloudflare Pages** from GitHub user **mckeekyle**.

### One-time setup

1. Push this repo to GitHub, e.g. `https://github.com/mckeekyle/modsafe` (or any repo name under `mckeekyle`).
2. In [Cloudflare Dashboard](https://dash.cloudflare.com/) → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
3. Select the `mckeekyle` GitHub account and this repository.
4. Build settings:
   - **Framework preset:** None
   - **Build command:** `./update && ./build`  
     (or `SITE_URL=https://modsafe.app ./build` if you prefer to skip live fetch at build time and rely on the Actions cron committing `data/games/*.json`)
   - **Build output directory:** `dist`
   - **Root directory:** `/` (or the folder that contains `update` / `build` if the repo is nested)
5. Environment variables (Pages → Settings → Environment variables):
   - `SITE_URL` = `https://modsafe.app`
   - Optional: `GITHUB_TOKEN` is **not** required in Pages if you use the GitHub Actions workflow below to refresh data; for build-time `./update`, add a fine-grained PAT with `public_repo` read as a secret if you hit rate limits.
6. After the first deploy succeeds, open **Custom domains** → **Set up a custom domain** → `modsafe.app` (and optionally `www.modsafe.app`). Cloudflare will attach the zone you already bought.
7. Confirm https://modsafe.app serves the home page and https://modsafe.app/games.json returns JSON (legacy /status.json = Cyberpunk).

### Scheduled status refresh (GitHub Actions)

Cloudflare Pages rebuilds on git push. Use the included workflow to refresh `data/games/*.json` on a cron and push, which triggers a Pages deploy:

- File: `.github/workflows/update-and-deploy.yml`
- Schedule: every 6 hours + `workflow_dispatch`
- Needs: `contents: write` so the job can commit updated `data/games/*.json` (and rebuilt `dist/` if you choose to commit it)

In the GitHub repo (**Settings → Actions → General**): allow Actions to create PRs / grant read-write for workflows if required by your org policy. No paid services.

**Alternative:** Cloudflare **Deploy Hook** (Pages → Settings → Builds & deployments → Deploy hooks). Put the hook URL in a GitHub secret `CLOUDFLARE_PAGES_DEPLOY_HOOK` and have the workflow `curl -X POST` it after committing data — useful if you do not want Pages to run `./update` itself.

### DNS (already on Cloudflare)

If Pages asks you to add a CNAME for `modsafe.app`, follow the dashboard. For a zone already on Cloudflare, attaching the Pages project as a custom domain is usually enough (proxied orange-cloud).

## Other hosts (optional)

### GitHub Pages

Possible but not the primary target. Set Pages source to GitHub Actions and adapt the workflow to `actions/deploy-pages`, with `SITE_URL=https://modsafe.app` only if DNS points there; otherwise use `https://mckeekyle.github.io/<repo>`.

### Netlify

Build: `./update && SITE_URL=https://modsafe.app ./build` · Publish: `dist` · Trigger builds via build hook from the same cron if desired.

## Machine-readable / AI-friendly outputs

After build, `dist/` includes:

- `/<game>/status.json` — per-game dataset; `/games.json` — index; `/status.json` — legacy Cyberpunk dataset; `/_redirects` — legacy URL redirects
- `/llms.txt` — plain-language summary for AI chatbots
- `/sitemap.xml`, `/robots.txt`
- JSON-LD: `WebSite`, `WebPage`, `Dataset`, `FAQPage`

## What you must provide / already have

| Item | Status |
|------|--------|
| **Domain `modsafe.app`** | Bought (Cloudflare) — set as `SITE_URL` |
| **Cloudflare account + Pages project** | Connect GitHub `mckeekyle` repo and custom domain |
| **GitHub repo under `mckeekyle`** | Push this code; enable Actions |
| **Newsletter provider** | Form is a placeholder (Buttondown / Mailchimp / ConvertKit) |
| **Sponsor contact** | Placeholder `sponsors@modsafe.app` |

No paid APIs required. Steam news and GitHub releases are public.

## Disclaimer

Not affiliated with CD PROJEKT RED, Nexus Mods, or framework authors. Statuses are inferred from public timestamps and release notes — always confirm on the project page and the [redmodding wiki](https://wiki.redmodding.org/) before updating.

## Analytics (Cloudflare Web Analytics, cookie-free)

Preferred: Cloudflare dashboard → Workers & Pages → `modsafe` → Metrics → **Web Analytics → Enable**. Cloudflare injects the beacon itself on the next deploy, with no code change.
Alternative: create a Web Analytics site for `modsafe.app` (manual JS snippet), then set the Pages env var `CF_ANALYTICS_TOKEN=<site token>`. The build then adds the beacon to every page. The token is public.
