# How to install Cyberpunk 2077 mods

Cyberpunk mods lean on six frameworks (CET, RED4ext, redscript, ArchiveXL, TweakXL, Codeware). After every game patch they need updates, so check this page before you play. **Vortex** handles most mods automatically; manual install (unzip into the game folder) also works because most mods use the right folder structure already.

## Steps

1. **Update the game and check ModSafe.** If the game patched in the last few days and the frameworks show "Just patched", wait.
2. **Install a mod manager (optional but easier).** Install Vortex and enable Cyberpunk 2077, or plan to unzip files into the game's root folder (the one containing bin/ and archive/).
3. **Install the frameworks first.** Cyber Engine Tweaks, RED4ext and redscript, then ArchiveXL, TweakXL and Codeware.
4. **Run the game once.** CET asks you to choose an overlay key on first launch. Get to the main menu, then quit. This confirms the frameworks load.
5. **Add settings menus.** Native Settings UI and Mod Settings let other mods show their options in-game.
6. **Add mods a few at a time.** Read each mod's requirements on its page and install them before the mod itself.
7. **Test after each batch.** Load a save and look for red error pop-ups or crashes before adding more.

## Common pitfalls

- **Outdated frameworks after a patch.** A crash on launch right after an update is nearly always an old RED4ext, redscript or CET.
- **redscript compilation errors.** The error window names the mod that failed; update or remove it.
- **Wrong folder.** Mods belong in the game install folder (e.g. Steam/steamapps/common/Cyberpunk 2077), not in Documents.
- **Antivirus quarantining DLLs.** Some antivirus tools flag RED4ext or CET; restore and whitelist them if they vanish.
- **Old mods in archive/pc/mod.** Leftover files from old versions can conflict. Remove a mod completely before reinstalling a new version.

## Rolling back

- In Vortex, disable the mod and deploy. Manually, delete the files the mod added (most mods list them).
- To test without mods, rename the archive/pc/mod, r6/scripts, bin/x64/plugins and red4ext folders temporarily.
- Your saves are in Saved Games/CD Projekt Red/Cyberpunk 2077. Back them up before big changes.
- Steam keeps older versions under Properties > Game Versions & Betas (e.g. `2_31_old` for Patch 2.31), and GOG Galaxy can roll back too. Rolling back is a stopgap; framework updates usually follow within days.
