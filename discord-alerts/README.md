# ModSafe alerts for Discord

Get a message in your Discord channel whenever a game's ModSafe verdict changes, for example when Skyrim
goes from **Just patched, wait** to **Likely safe**. Each alert shows the game, the new verdict (and the old one),
the game patch, and a link to the game's ModSafe page.

It uses a Discord **channel webhook**, so there's no bot to invite and no permissions to grant. It only reads
ModSafe's public feed (`https://modsafe.app/api/v1/status.json`) and only posts to the one channel you choose.
It never pings anyone (`@everyone` and role mentions are disabled).

## Setup (about 5 minutes)

**1. Make a webhook for your channel** (needs the *Manage Webhooks* permission)

Discord → your server → the channel's ⚙️ *Edit Channel* → *Integrations* → *Webhooks* → *New Webhook*.
Name it "ModSafe", then *Copy Webhook URL*. Treat this URL like a password: anyone who has it can post in
that channel.

**2. Download the script:** [`modsafe_alerts.py`](https://raw.githubusercontent.com/mckeekyle/modsafe/main/discord-alerts/modsafe_alerts.py)
(right-click → *Save link as*). It's one file and needs Python 3.9 or newer, with no extra packages.

**3. Run it every 30 minutes.** Pick one:

- **GitHub Actions (free, nothing running at home):** follow the steps at the top of
  [`github-actions-example.yml`](github-actions-example.yml).
- **Linux or macOS:**

  ```bash
  export MODSAFE_DISCORD_WEBHOOK="https://discord.com/api/webhooks/..."
  python3 modsafe_alerts.py --test        # posts one sample message so you can see it works
  python3 modsafe_alerts.py --loop 30     # keeps checking every 30 minutes (leave it running)
  ```

  Or from cron instead of `--loop`:
  `*/30 * * * * MODSAFE_DISCORD_WEBHOOK="https://discord.com/api/webhooks/..." python3 /path/to/modsafe_alerts.py`

- **Windows (PowerShell):**

  ```powershell
  $env:MODSAFE_DISCORD_WEBHOOK = "https://discord.com/api/webhooks/..."
  py modsafe_alerts.py --test
  py modsafe_alerts.py --loop 30
  ```

  Or use Task Scheduler to run `py C:\path\to\modsafe_alerts.py --webhook "https://discord.com/api/webhooks/..."`
  every 30 minutes.

The first run only remembers the current verdicts; alerts start with the next change. To post every game's
current verdict once instead, add `--announce-current` to the first run. To preview without posting, add `--dry-run`.

## What an alert looks like

> **Skyrim Special Edition: 🔴 Breakage reported** (links to the game's ModSafe page)
> Mod verdict changed from **Likely safe** to **Breakage reported**.
> **Game patch** 1.7.99 (2026-08-20) · **Trend** ⬇️ Worse
> **Breakage reported in** • SSE Engine Fixes (7.0.21-beta5)

When a game is on *Just patched, wait*, *Breakage reported* or *Not ported yet*, the alert names the mods causing it.
Several changes found at once arrive as one message.

## Only some games

Set `MODSAFE_GAMES` (or `--games`) to a comma-separated list of ids:

```bash
python3 modsafe_alerts.py --list-games          # shows every id and its current verdict
export MODSAFE_GAMES="skyrim-se,fallout-4,cyberpunk-2077"
```

## Options

| Flag | Environment variable | What it does |
|---|---|---|
| `--webhook URL` | `MODSAFE_DISCORD_WEBHOOK` | Channel webhook to post to |
| `--games a,b` | `MODSAFE_GAMES` | Only watch these games (default: all) |
| `--state FILE` | `MODSAFE_STATE_FILE` | Where the last-seen verdicts are kept |
| `--loop MIN` | | Keep running; check every MIN minutes (at least 15) |
| `--dry-run` | | Print what would be posted; don't contact Discord |
| `--test` | | Post one sample message |
| `--announce-current` | | On the first run, post every game's current verdict |

If a post fails (for example, the webhook was deleted), nothing is marked as sent and the next run tries again.

## Good to know

- ModSafe's data refreshes about every 30 minutes on patch days and every 6 hours otherwise, so checking more
  often than every 30 minutes gains nothing.
- On GitHub Actions, GitHub pauses scheduled workflows in a repository with no activity for 60 days and emails
  you first. Click *Enable workflow* on the Actions tab to start it again.
- The old combined "Grand Theft Auto V" entry is skipped because its Legacy and Enhanced editions are followed
  separately (`gta-v-legacy`, `gta-v-enhanced`).
- Verdicts are inferred from public release data and are not guarantees. Check each mod's own page before
  updating.
- Questions or problems: open an issue at https://github.com/mckeekyle/modsafe/issues
