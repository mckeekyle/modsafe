# How to install Skyrim Special Edition mods

Skyrim mods are safest with a mod manager that keeps your game folder clean. We recommend **Mod Organizer 2** (everything lives in a virtual folder you can switch off), or **Vortex** if you prefer Nexus Mods' own app. Check the ModSafe status for SKSE64 before you start: if Skyrim just patched, wait until it says Safe.

## Steps

1. **Start clean.** Launch the game once from Steam so it creates its settings files, then quit. Don't install mods into a game folder that already has leftovers from old attempts.
2. **Install a mod manager.** Download Mod Organizer 2 or Vortex from the links on this page and point it at your Skyrim Special Edition install.
3. **Install SKSE64.** Get the build that matches your game version from the official SKSE site or its Nexus page. Put the loader and DLLs in the game folder (next to SkyrimSE.exe) and add the scripts through your manager. From now on, start the game with skse64_loader.exe (MO2 and Vortex add a button for it).
4. **Add the foundation.** Install Address Library, SSE Engine Fixes (both parts), USSEP and powerofthree's Tweaks, in the order shown in our Essential mods list.
5. **Add interface mods.** SkyUI, then MCM Helper, then the dialogue and message box fixes.
6. **Test before going further.** Start a new game or load a save and play for a few minutes. If it crashes, the last mod you added is the first suspect.
7. **Add the rest a few at a time.** Visual and gameplay mods go last. Let your manager sort plugins (LOOT is built into both) and read each mod page's requirements.
8. **Lock your version.** Bethesda updates break SKSE plugins. Consider setting Steam to update only when you launch, and check ModSafe before letting it update.

## Common pitfalls

- **Game version mismatch.** SKSE, Address Library and Engine Fixes must match your exact game build; a "version mismatch" pop-up means one is outdated.
- **Launching from Steam.** Starting SkyrimSE.exe instead of the SKSE loader silently disables every SKSE plugin.
- **Mixing Anniversary and Special Edition files.** Use files for your build (1.5.97 vs 1.6.x); mod pages usually list both.
- **Too many plugins.** Regular plugins are capped at 254; prefer ESL-flagged (light) versions when offered.
- **Removing mods mid-save.** Uninstalling script-heavy mods from an ongoing save can corrupt it. Test on a new save.

## Rolling back

- In MO2, untick the mod (or switch to a backup profile); in Vortex, disable it and deploy.
- If a game update broke SKSE, wait for SKSE and Address Library to update (ModSafe shows when they do) rather than deleting mods.
- Keep a copy of your saves folder (Documents/My Games/Skyrim Special Edition/Saves) before big changes.
- Steam can't officially roll back the game. If you need to stay on an old build, back up the whole game folder before letting Steam update.
