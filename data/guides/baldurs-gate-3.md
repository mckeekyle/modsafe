# How to install Baldur's Gate 3 mods

Baldur's Gate 3 has an **in-game mod manager** (mod.io) for mods published there, which is the simplest option. For Nexus mods and anything that needs the Script Extender, most players use **BG3 Mod Manager**. Don't mix both carelessly: keep track of where each mod came from.

## Steps

1. **Update the game and check ModSafe.** After a big Larian patch, the Script Extender and many mods need updates. Wait for them first.
2. **Back up your saves.** Copy %LocalAppData%/Larian Studios/Baldur's Gate 3/PlayerProfiles somewhere safe.
3. **Install BG3 Mod Manager.** Download it from GitHub, run it, and let it detect your game and data folders.
4. **Install the Script Extender.** In BG3 Mod Manager use Tools › Download & Extract the Script Extender, or follow the instructions on its GitHub page.
5. **Add framework mods.** Drag the .zip or .pak files for Community Library, Mod Configuration Menu and Compatibility Framework into the manager, then move them to the active list.
6. **Add your other mods.** Put libraries and frameworks above the mods that need them. Each mod page lists its requirements.
7. **Export the load order.** Click Save and Export Order to Game. Launch the game as usual.
8. **Use mod.io mods in game.** In the main menu, open Mod Manager to browse, install and enable mods published on mod.io.

## Common pitfalls

- **Forgetting to export.** Changes in BG3 Mod Manager only apply after Export Order to Game.
- **Missing Script Extender after a patch.** Mods that need it silently stop working until it updates.
- **Mods in the wrong folder.** .pak files go in the Mods folder under %LocalAppData%/Larian Studios/Baldur's Gate 3/Mods. Script Extender files go next to bg3.exe.
- **Removing mods mid-save.** Saves remember the mods that touched them. Removing a class, race or item mod can stop a save from loading.
- **Multiplayer mismatch.** Every player needs the same gameplay mods in the same order.

## Common errors and fixes

- **Why does my load order keep resetting?** The game resets `modsettings.lsx` if there are subfolders in `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods`. Keep only `.pak` files there. If it still resets, one of the active mods is erroring, so disable mods in halves until you find it. Source: [BG3 Mod Manager README](https://github.com/LaughingLeader/BG3ModManager).
- **I ordered my mods but nothing changed in game. Why?** BG3 Mod Manager only writes the order when you click **Export Load Order to Game**, which saves `modsettings.lsx`. Export with the main campaign selected. Source: [BG3 Mod Manager README](https://github.com/LaughingLeader/BG3ModManager).
- **BG3 Mod Manager won't start or can't find the game. What do I do?** Run the game once before using it, and install .NET 8 and the latest Visual C++ redistributable. Extract the manager somewhere outside Program Files, and set the Game Data Path in its preferences. Source: [BG3 Mod Manager README](https://github.com/LaughingLeader/BG3ModManager).
- **How do I see Script Extender errors?** Set `"CreateConsole": true` in `ScriptExtenderSettings.json` next to the game exe to open a debug console. `LogRuntime` writes logs, by default to `Documents\OsirisLogs`. Source: [BG3 Script Extender README](https://github.com/Norbyte/bg3se).

## Rolling back

- Move a mod back to the inactive list in BG3 Mod Manager and export again, or disable it in the in-game Mod Manager.
- If a patch broke things, disable all mods, check the game launches clean, then re-enable a few at a time.
- Restore your PlayerProfiles backup if a save stops loading.
- Steam only offers older major patches under Properties > Game Versions & Betas (Patch 7 Hotfix 3, Patch 6 Hotfix 9), not the previous hotfix, so after a small patch it's usually best to wait for Script Extender and mod updates.
