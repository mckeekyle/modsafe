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

## Rolling back

- Move a mod back to the inactive list in BG3 Mod Manager and export again, or disable it in the in-game Mod Manager.
- If a patch broke things, disable all mods, check the game launches clean, then re-enable a few at a time.
- Restore your PlayerProfiles backup if a save stops loading.
- Steam can't officially roll back the game, so wait for Script Extender and mod updates.
