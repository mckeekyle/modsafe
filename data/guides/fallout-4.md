# How to install Fallout 4 mods

Fallout 4 mods are safest with **Mod Organizer 2** (a virtual folder you can switch off) or **Vortex**. Since the 2024 Next-Gen update, the game has two builds (Next-Gen and Old-Gen), and F4SE plugins must match yours. Check the F4SE status on ModSafe before you start.

## Steps

1. **Launch once from Steam.** Let the game create its settings files, then quit.
2. **Install a mod manager.** Download Mod Organizer 2 or Vortex and point it at your Fallout 4 install.
3. **Install F4SE.** Get the build for your game version from the official F4SE site or its Nexus page. Put the loader and DLLs in the game folder next to Fallout4.exe. From now on, start the game with f4se_loader.exe (both managers add a button for it).
4. **Add the foundation.** Address Library, Buffout 4 NG and the Unofficial Fallout 4 Patch, in the order shown in our Essential mods list.
5. **Add crash and performance fixes.** Weapon Debris Crash Fix and High FPS Physics Fix.
6. **Add interface mods.** Mod Configuration Menu, HUDFramework, DEF_UI and Extended Dialogue Interface.
7. **Test, then add more.** Load a save for a few minutes. Add gameplay and settlement mods a few at a time. Let LOOT (built into both managers) sort plugins.

## Common pitfalls

- **Wrong game build.** Next-Gen and Old-Gen need different F4SE and plugin versions. Read the version list on each mod page.
- **Launching from Steam.** Starting Fallout4.exe directly disables every F4SE plugin.
- **Mods not loading at all.** If plugins don't show in game, make sure your manager's archive invalidation/INI setup ran. Both managers do this automatically on first use.
- **Plugin cap.** Regular plugins are capped at 254. Prefer ESL-flagged (light) versions when offered.
- **Removing script mods mid-save.** Can break saves. Test on a new save first.

## Common errors and fixes

- **Why does Fallout 4 start without F4SE?** Start the game with `f4se_loader.exe` (or your mod manager's F4SE entry), not the Steam Play button. Source: [F4SE readme](https://github.com/ianpatt/f4se/blob/master/f4se_readme.txt).
- **Where do the F4SE files go?** Copy the `f4se_*.dll`, `f4se_loader.exe` and the included `Data` folder into your Fallout 4 install folder. To uninstall, delete those files again. Source: [F4SE readme](https://github.com/ianpatt/f4se/blob/master/f4se_readme.txt).
- **Does F4SE work on Game Pass or Epic?** No. F4SE supports the Steam and GOG versions, and its readme lists the MS Store/Game Pass and Epic versions as unsupported. Each F4SE build targets one game runtime, so match it to your version. Source: [F4SE readme](https://github.com/ianpatt/f4se/blob/master/f4se_readme.txt).
- **My antivirus flags the loader. Is that normal?** F4SE injects a DLL into the game, which some antivirus tools flag. Add an exception for the game folder. Source: [F4SE readme](https://github.com/ianpatt/f4se/blob/master/f4se_readme.txt).

## Rolling back

- In MO2, untick the mod or switch to a backup profile. In Vortex, disable it and deploy.
- If a game update broke F4SE, wait for F4SE and Address Library to update (ModSafe shows when). Don't uninstall everything.
- Buffout 4's crash logs (Documents/My Games/Fallout4/F4SE) name the likely culprit.
- Back up Documents/My Games/Fallout4/Saves before big changes. To avoid surprise updates, set Steam to update only when you launch the game.
