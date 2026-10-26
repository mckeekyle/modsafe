# How to install Elden Ring mods

Elden Ring mods are **offline only**. Easy Anti-Cheat (EAC) protects normal online play, and modded files can get you flagged or soft-banned. Seamless Co-op is the exception: it runs on its own servers with its own save files. Use **me3** to load mods without touching your game files.

## Steps

1. **Back up your saves.** Copy %AppData%/EldenRing somewhere safe before anything else.
2. **Check ModSafe.** After a FromSoftware patch, Seamless Co-op and DLL mods often need an update.
3. **Install me3.** Download the latest release from its GitHub page and follow the installer. It creates a profile folder where your mods go.
4. **Add mods to the me3 profile.** Put file mods (regulation.bin, parts, map files) and DLL mods where each mod's instructions say. Mods packaged for Mod Engine 2 generally work too.
5. **Launch through me3.** me3 starts the game with EAC off and your mods loaded. Don't start the game normally with mods active.
6. **Seamless Co-op is separate.** Install it from its official page and launch it with its own launcher. All players need the same version.
7. **Test one mod at a time.** Big overhauls (Reforged, The Convergence) expect a new character and usually aren't compatible with each other.

## Common pitfalls

- **Going online with mods.** Never use modded files with EAC online play. Keep modded and vanilla saves apart.
- **Mixing overhauls.** Two mods that replace regulation.bin will overwrite each other.
- **Outdated mods after a patch.** A crash on startup after an update usually means a DLL mod or Seamless Co-op needs updating.
- **Antivirus.** Some tools flag mod loaders. Only download from the official pages.

## Common errors and fixes

- **Why won't the game launch through me3?** Make sure Steam is running, and check the paths in your `.me3` profile. `[[packages]]` and `[[natives]]` paths are relative to the profile file. On Windows, run `me3 info` to check the install. On Linux, set `windows_binaries_dir` in `~/.config/me3`. Source: [me3 docs: troubleshooting](https://me3.help/en/latest/user-guide/troubleshooting/).
- **A mod in my profile isn't loading. Why?** Most often there is a typo in the `.me3` file or a path that doesn't match where the mod was extracted. Fix the entry and relaunch. Source: [me3 docs: troubleshooting](https://me3.help/en/latest/user-guide/troubleshooting/).
- **My antivirus flags me3. Is it safe?** The me3 binaries are code-signed. Download them only from the official GitHub releases and add an exclusion if your antivirus blocks them. Source: [me3 docs: troubleshooting](https://me3.help/en/latest/user-guide/troubleshooting/).

## Rolling back

- Remove the mod from your me3 profile, or start the game normally from Steam to play vanilla.
- Restore your save backup if a save was used with an overhaul you removed.
- Steam can't officially roll back the game. Wait for mod updates, which ModSafe tracks for Seamless Co-op and me3.
