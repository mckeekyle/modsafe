# How to install Schedule I mods

Schedule I mods run on **MelonLoader** and come mostly from **Thunderstore** and Nexus Mods. The easiest way is **r2modman** (or **Gale**), which installs MelonLoader and each mod's dependencies for you. Schedule I has two builds on Steam: the default **IL2CPP** version and an **alternate** (Mono) version, and many mods ship a separate build for each, so match them to the version you play.

## Steps

1. **Install a mod manager.** Download [r2modman](https://thunderstore.io/c/schedule-i/p/ebkr/r2modman/) or [Gale](https://thunderstore.io/c/schedule-i/p/Kesomannen/GaleModManager/) and pick Schedule I.
2. **Check which build you play.** In your Steam Library, right-click Schedule I › **Properties** › **Game Versions & Betas**. "None" is the default IL2CPP build; **alternate** is the Mono build. Pick mods marked IL2CPP or Mono to match (many say so in their name, like Cartel Enforcer IL2CPP).
3. **Create a profile.** Keep one profile per setup so you can switch quickly.
4. **Install mods.** Search the Online tab and install. The manager adds MelonLoader and libraries such as S1API automatically.
5. **Start modded.** Launch with the manager's **Start modded** button, not from Steam. The first modded start takes longer while MelonLoader sets itself up for the current game build.
6. **Check the console.** MelonLoader opens a console window. Red `[ERR]` lines name the mod that failed to load.
7. **Share the profile for co-op.** Export the profile as a code and have friends import it, so everyone runs the same gameplay mods.

## Common pitfalls

- **Wrong build of a mod.** An IL2CPP mod won't load on the Mono (alternate) version, and the other way round.
- **Mods after a game update.** Updates such as v0.4.6 or v0.4.7 change the game code mods hook into, so many mods break until their authors ship a rebuild. Check update dates on Thunderstore and ModSafe's status.
- **Launching from Steam.** That starts the game without mods. Use Start modded.
- **Mismatched co-op mods.** Different mod lists in a lobby cause desyncs. Share one profile code.

## Common errors and fixes

- **After a game update MelonLoader shows Il2CppAssemblyGenerator errors and mods won't load. What now?** Players report that rolling back to the previous game version fixed it until mods and MelonLoader caught up. Make sure you're on the latest MelonLoader, then roll back (below) or disable mods until they update. Source: [Steam discussion: MelonLoader broken in update?](https://steamcommunity.com/app/3164500/discussions/1/591811524772790163/).
- **How do I tell which mod is broken?** Read the MelonLoader console or its log: lines marked `[ERR]` name the mod that failed. Disable that one and try again. Source: [XGamingServer: updating a Schedule 1 server](https://xgamingserver.com/docs/schedule-1/update-server).
- **A mod says it needs S1API or another library. Where do I get it?** Install it from Thunderstore; r2modman and Gale add listed dependencies automatically. S1API's Thunderstore package is [S1API (Forked)](https://thunderstore.io/c/schedule-i/p/ifBars/S1API_Forked/). Source: [S1API on GitHub](https://github.com/ifBars/S1API).

## Rolling back

- Steam keeps the previous major version as a branch. Right-click Schedule I › **Properties** › **Game Versions & Betas** and pick **default-previous** (or **alternate-previous** for the Mono build).
- Use it to keep playing with mods that haven't updated yet, then switch back to **None** once they have.
- Back up your save folder first: saves from a newer version may not load in an older one.
- More options: [how to stop Steam auto-updates](/guides/stop-steam-auto-updates/).
