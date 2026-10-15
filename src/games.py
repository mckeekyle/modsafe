"""Per-game configuration: Steam app ids, patch-title rules, and tracked frameworks.

Framework `source` kinds:
  github      -> GitHub releases API (repo)
  github_tags -> GitHub tags + tag commit dates (projects that tag but don't publish releases)
  thunderstore-> Thunderstore public package API (namespace/name)
  manual      -> not tracked automatically (e.g. Nexus-only); shown with a link, excluded from verdict
Minecraft uses dedicated loader sources (see update.py).
"""

from status_logic import FRAMEWORKS as CP_FRAMEWORKS

GAMES = [
    {
        "slug": "cyberpunk-2077",
        "name": "Cyberpunk 2077",
        "short": "Cyberpunk",
        "developer": "CD PROJEKT RED",
        "steam_appid": 1091500,
        "patch_rule": {
            "include": r"\b(patch|update)\s+\d+\.\d+",
            "exclude": r"\b(coming|revealed|tomorrow|development update|insight|beta|sneak peek)\b",
            "version": r"(?:patch|update)\s+(\d+\.\d+(?:\.\d+)?)",
            "require_version": True,
            "label": "Patch {v}",
        },
        "frameworks": [dict(fw, source="github") for fw in CP_FRAMEWORKS],
        "wiki": "https://wiki.redmodding.org/cyberpunk-2077-modding",
        "blurb": "Script and native frameworks (CET, RED4ext, redscript, ArchiveXL, TweakXL, Codeware) usually break on every official patch until their authors ship updates.",
    },
    {
        "slug": "skyrim-se",
        "name": "Skyrim Special Edition",
        "short": "Skyrim SE/AE",
        "developer": "Bethesda Game Studios",
        "steam_appid": 489830,
        "patch_rule": {
            "include": r"\bupdate\s+\d+\.\d+|\d+\.\d+(?:\.\d+)?\s+update",
            "exclude": r"\bbeta\b|upcoming|a look at",
            "version": r"\b(\d+\.\d+(?:\.\d+)?)\b",
            "require_version": True,
            "label": "{v}",
        },
        "frameworks": [
            {"id": "skse64", "name": "Skyrim Script Extender (SKSE64)", "short": "SKSE64", "source": "github_tags",
             "repo": "ianpatt/skse64", "url": "https://skse.silverlock.org/"},
            {"id": "engine-fixes", "name": "SSE Engine Fixes", "short": "Engine Fixes", "source": "github",
             "repo": "aers/EngineFixesSkyrim64", "url": "https://github.com/aers/EngineFixesSkyrim64"},
            {"id": "papyrus-extender", "name": "powerofthree's Papyrus Extender", "short": "PapyrusExt", "source": "github",
             "repo": "powerof3/PapyrusExtenderSSE", "url": "https://github.com/powerof3/PapyrusExtenderSSE"},
            {"id": "crash-logger", "name": "Crash Logger SSE AE VR", "short": "CrashLogger", "source": "github",
             "repo": "alandtse/CrashLoggerSSE", "url": "https://github.com/alandtse/CrashLoggerSSE"},
            {"id": "address-library", "name": "Address Library for SKSE Plugins", "short": "Address Lib", "source": "manual",
             "url": "https://www.nexusmods.com/skyrimspecialedition/mods/32444",
             "note": "Distributed on Nexus Mods only; ModSafe does not scrape Nexus. Check the mod page."},
        ],
        "wiki": "https://skse.silverlock.org/",
        "blurb": "Every runtime bump breaks SKSE64 and native SKSE plugins (DLLs) until SKSE, Address Library and plugin authors catch up.",
    },
    {
        "slug": "fallout-4",
        "name": "Fallout 4",
        "short": "Fallout 4",
        "developer": "Bethesda Game Studios",
        "steam_appid": 377160,
        "patch_rule": {
            "include": r"\b(update|patch|hotfix)\b",
            "exclude": r"creation kit|upcoming|announc|getting free|texture pack|trailer|mods update|creation club|celebrate|arrives|free update|shelter",
            "version": r"\b(1\.\d+\.\d+)\b",
            "label": "{v}",
            "label_noversion": "Update {date}",
        },
        "frameworks": [
            {"id": "f4se", "name": "Fallout 4 Script Extender (F4SE)", "short": "F4SE", "source": "github_tags",
             "repo": "ianpatt/f4se", "url": "https://f4se.silverlock.org/"},
            {"id": "address-library-f4", "name": "Address Library for F4SE Plugins", "short": "Address Lib", "source": "manual",
             "url": "https://www.nexusmods.com/fallout4/mods/47327",
             "note": "Distributed on Nexus Mods only; ModSafe does not scrape Nexus. Check the mod page."},
            {"id": "buffout4", "name": "Buffout 4 / Buffout 4 NG", "short": "Buffout 4", "source": "manual",
             "url": "https://www.nexusmods.com/fallout4/mods/64880",
             "note": "Original Buffout 4 is unmaintained; the NG fork is distributed on Nexus Mods only. Check the mod page."},
        ],
        "wiki": "https://f4se.silverlock.org/",
        "blurb": "Bethesda's recent Fallout 4 updates (next-gen, Anniversary Edition and follow-up patches) break F4SE and DLL plugins until they are rebuilt.",
    },
    {
        "slug": "baldurs-gate-3",
        "name": "Baldur's Gate 3",
        "short": "BG3",
        "developer": "Larian Studios",
        "steam_appid": 1086940,
        "patch_rule": {
            "include": r"^(?:hotfix|patch|room temperature fix)\s*#?\s*\d+.*now live|^the final patch",
            "exclude": r"console only",
            "version": r"^((?:hotfix|patch|room temperature fix)\s*#?\s*\d+)",
            "label": "{v}",
            "label_noversion": "{title}",
        },
        "frameworks": [
            {"id": "bg3se", "name": "BG3 Script Extender", "short": "BG3SE", "source": "github",
             "repo": "Norbyte/bg3se", "url": "https://github.com/Norbyte/bg3se"},
            {"id": "bg3mm", "name": "BG3 Mod Manager", "short": "BG3MM", "source": "github",
             "repo": "LaughingLeader/BG3ModManager", "url": "https://github.com/LaughingLeader/BG3ModManager"},
        ],
        "wiki": "https://bg3.community/",
        "blurb": "Larian warns mods may break with each patch or hotfix; Script Extender mods need a matching BG3SE build.",
    },
    {
        "slug": "stardew-valley",
        "name": "Stardew Valley",
        "short": "Stardew",
        "developer": "ConcernedApe",
        "steam_appid": 413150,
        "patch_rule": {
            "include": r"\b(patch|update|available|hotfix|bug fix)\b",
            "exclude": r"\b(?:announced|sneak peek|release date|message|award|merch|sale|anniversary|nominat)",
            "version": r"\b(1\.\d+(?:\.\d+)?)\b",
            "require_version": True,
            "label": "{v}",
        },
        "frameworks": [
            {"id": "smapi", "name": "SMAPI (Stardew Modding API)", "short": "SMAPI", "source": "github",
             "repo": "Pathoschild/SMAPI", "url": "https://smapi.io/"},
        ],
        "extra_links": [("SMAPI mod compatibility list", "https://smapi.io/mods")],
        "wiki": "https://stardewvalleywiki.com/Modding:Index",
        "blurb": "SMAPI must support the current game version; per-mod status is tracked by the official SMAPI compatibility list.",
    },
    {
        "slug": "lethal-company",
        "name": "Lethal Company",
        "short": "Lethal Co.",
        "developer": "Zeekerss",
        "steam_appid": 1966720,
        "patch_rule": {
            "include": r"\bv(?:ersion)?\s?\d+\b",
            "exclude": r"\bbeta\b|anniversary|nominat|goty",
            "version": r"\bv(?:ersion)?\s?(\d+)\b",
            "require_version": True,
            "label": "v{v}",
            "mention": r"(?<![\w.])(?:v|version\s?){v}\b",
        },
        "frameworks": [
            {"id": "bepinexpack", "name": "BepInExPack", "short": "BepInEx", "source": "thunderstore",
             "package": "BepInEx/BepInExPack", "url": "https://thunderstore.io/c/lethal-company/p/BepInEx/BepInExPack/"},
            {"id": "lethallib", "name": "LethalLib", "short": "LethalLib", "source": "thunderstore",
             "package": "Evaisa/LethalLib", "url": "https://thunderstore.io/c/lethal-company/p/Evaisa/LethalLib/"},
            {"id": "lethallevelloader", "name": "LethalLevelLoader", "short": "LLL", "source": "thunderstore",
             "package": "IAmBatby/LethalLevelLoader", "url": "https://thunderstore.io/c/lethal-company/p/IAmBatby/LethalLevelLoader/"},
            {"id": "morecompany", "name": "MoreCompany", "short": "MoreCompany", "source": "thunderstore",
             "package": "notnotnotswipez/MoreCompany", "url": "https://thunderstore.io/c/lethal-company/p/notnotnotswipez/MoreCompany/"},
        ],
        "wiki": "https://thunderstore.io/c/lethal-company/",
        "blurb": "Game version bumps (v50, v70, v80…) regularly break level, item and lobby mods built on BepInEx.",
    },
    {
        "slug": "minecraft",
        "name": "Minecraft: Java Edition",
        "short": "Minecraft",
        "developer": "Mojang Studios",
        "kind": "minecraft",
        "frameworks": [
            {"id": "fabric-loader", "name": "Fabric Loader", "short": "Fabric", "source": "mc_fabric", "url": "https://fabricmc.net/"},
            {"id": "fabric-api", "name": "Fabric API", "short": "Fabric API", "source": "mc_modrinth", "project": "fabric-api", "loader": "fabric",
             "url": "https://modrinth.com/mod/fabric-api"},
            {"id": "forge", "name": "Minecraft Forge", "short": "Forge", "source": "mc_forge", "url": "https://files.minecraftforge.net/"},
            {"id": "neoforge", "name": "NeoForge", "short": "NeoForge", "source": "mc_neoforge", "url": "https://neoforged.net/"},
            {"id": "sodium", "name": "Sodium", "short": "Sodium", "source": "mc_modrinth", "project": "sodium", "url": "https://modrinth.com/mod/sodium"},
            {"id": "iris", "name": "Iris Shaders", "short": "Iris", "source": "mc_modrinth", "project": "iris", "url": "https://modrinth.com/mod/iris"},
            {"id": "lithium", "name": "Lithium", "short": "Lithium", "source": "mc_modrinth", "project": "lithium", "url": "https://modrinth.com/mod/lithium"},
        ],
        "wiki": "https://minecraft.wiki/w/Java_Edition",
        "blurb": "Each Java release needs new Fabric/Forge/NeoForge builds, and every mod must be ported to the new version.",
    },
]

GAMES_BY_SLUG = {g["slug"]: g for g in GAMES}
