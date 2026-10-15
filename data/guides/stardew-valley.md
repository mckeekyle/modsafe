# How to install Stardew Valley mods

Stardew modding is beginner-friendly: install **SMAPI**, then drop mods into the Mods folder. SMAPI checks for updates and tells you exactly which mod is broken or missing a requirement. **Stardrop** or **Vortex** are optional managers if you like a UI.

## Steps

1. **Back up your saves.** Copy %AppData%/StardewValley/Saves (Windows) or ~/.config/StardewValley/Saves (Linux/macOS) somewhere safe.
2. **Install SMAPI.** Download it from smapi.io, run the installer and pick your game folder. If the installer shows Steam launch options (Linux/macOS), add them so Steam starts SMAPI.
3. **Launch once.** Start the game; a SMAPI console window opens beside it. Quit once you reach the title screen.
4. **Install frameworks.** Unzip Content Patcher, Generic Mod Config Menu and SpaceCore into the Mods folder (each in its own subfolder).
5. **Install the mods you want.** Unzip each into Mods. Larger mods like Stardew Valley Expanded list extra requirements on their page; install those too.
6. **Read the SMAPI console.** Red lines name broken or missing mods; yellow lines usually mean an update is available.
7. **Check compatibility after game updates.** The smapi.io/mods list shows which mods work with the current game version.

## Common pitfalls

- **Nested folders.** A mod folder must contain its manifest.json directly (Mods/LookupAnything/manifest.json), not inside another folder.
- **Starting the game without SMAPI.** Mods only load when the game runs through SMAPI.
- **Missing dependencies.** SMAPI will skip a mod and tell you which requirement is missing.
- **Removing big content mods mid-save.** Uninstalling something like Stardew Valley Expanded from an ongoing save can lose items or areas.

## Rolling back

- Move a mod's folder out of Mods (or rename it to start with a dot) to disable it.
- If a game update broke SMAPI, wait for SMAPI to update, or use Steam's "beta" tab to switch to the previous version if ConcernedApe offers one.
- Restore your saves backup if a save starts misbehaving after removing mods.
