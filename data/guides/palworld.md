# How to install Palworld mods

Palworld mods come from the **Steam Workshop** (built into the game since 1.0) or from **Nexus Mods**. Most code mods run on **UE4SS**, using the Palworld build published by Okaetsu, a pwmodding.wiki maintainer. Data mods often use **PalSchema**, and simple mods are `.pak` files. Pocketpair supports modding but doesn't guarantee any mod works, and mods only work on the PC versions (Steam and Game Pass), not consoles.

## Steps

1. **Back up your saves.** Pocketpair warns that mods can corrupt or delete saves, and that a save loaded with mods can keep having problems after you remove them. In Steam, right-click Palworld → Manage → **Back up game files**, or copy `%LOCALAPPDATA%\Pal\Saved\SaveGames`.
2. **Start from a clean install.** If you modded before 1.0, delete the old mod files before you start (step 2 of [Pocketpair's guidelines](https://guideline.palworldgame.com/palworld-mod-guideline)). Then run Steam → Properties → Installed Files → **Verify integrity of game files**. Turning old mods off isn't enough, because leftover files still load.
3. **Easiest route: subscribe on the Workshop.** In your Steam Library, open Palworld → **Workshop**. Subscribe to a mod and pick **Subscribe to All** when Steam offers its required items (UE4SS, for example), as [pwmodding.wiki's Workshop guide](https://pwmodding.wiki/docs/users/workshop/installing-mods) shows.
4. **Turn mods on in the game.** On the title screen, go to Options → **Mod Management**, set **Enable Mod** to On, tick the mods you want, then click **Save**. The game restarts with the mods loaded.
5. **Manual route: install UE4SS.** Download `UE4SS-Palworld.zip` from [Okaetsu's latest release](https://github.com/Okaetsu/RE-UE4SS/releases/latest). Copy the `ue4ss` folder and `dwmapi.dll` into `Palworld\Pal\Binaries\Win64` (on Game Pass, `Pal\Binaries\WinGDK`). Details are in [pwmodding.wiki's installation guide](https://pwmodding.wiki/docs/users/ue4ss/installation).
6. **Configure UE4SS for play.** In `ue4ss\UE4SS-settings.ini`, set `bUseUObjectArrayCache = false`, `GuiConsoleEnabled = 0` and `GuiConsoleVisible = 0`. This avoids lag and stutter ([configuration guide](https://pwmodding.wiki/docs/users/ue4ss/configuration)).
7. **Add mods by type.** Put Lua and C++ mods in `Win64\ue4ss\Mods`. Put `.pak` mods in `Pal\Content\Paks\~mods`, and create the `~mods` folder if it doesn't exist. Put PalSchema mods where the mod's own page says. Add one mod at a time and launch between each.
8. **Keep mods off official servers.** [Pocketpair's guidelines](https://guideline.palworldgame.com/palworld-mod-guideline) strictly prohibit mods on official servers and warn that accounts can be banned. On dedicated servers, every player usually needs the same server-side mods.

## Common pitfalls

- **Two copies of UE4SS.** If you subscribed to a Workshop mod that needs UE4SS, delete or rename a manually installed `dwmapi.dll` in `Win64`. Otherwise the game crashes on launch.
- **Old UE4SS builds and "UE4SS Signatures".** Use the latest Palworld UE4SS build, which includes `MemberVariableLayout.ini`. Delete any `UE4SS_Signatures` folder, and don't use the February 2024 build or anything older than 3.0.1 ([troubleshooting](https://pwmodding.wiki/docs/users/ue4ss/troubleshooting)).
- **Vortex or CurseForge.** pwmodding.wiki says these managers currently install UE4SS and its mods incorrectly for Palworld. Install by hand or use the Workshop instead.
- **Deleting UE4SS's default mods.** Leave `BPModLoaderMod`, `BPML_GenericFunctions`, `mods.txt` and `mods.json` alone. Removing them breaks UE4SS.
- **Mods that add items, Pals or buildings.** Removing one, or letting it go out of date after a patch, can stop a world from loading. Keep a backup from before you added it.

## Common errors and fixes

- **Crash on launch after installing UE4SS.** Delete a leftover `xinput1_3.dll` from an old UE4SS install and check that `MemberVariableLayout.ini` is inside the `ue4ss` folder. If it still crashes, remove mods one by one. Source: [pwmodding.wiki UE4SS troubleshooting](https://pwmodding.wiki/docs/users/ue4ss/troubleshooting).
- **Mods don't load and there's no `UE4SS.log`.** UE4SS isn't installed in the right place. Check for `dwmapi.dll` in `Win64` (or `WinGDK`), and for `UE4SS.dll` and `UE4SS-settings.ini` inside `ue4ss`. Source: [pwmodding.wiki UE4SS troubleshooting](https://pwmodding.wiki/docs/users/ue4ss/troubleshooting).
- **Crash Reporter mentions corrupt data, or the game crashes right after a patch.** An outdated mod is the usual cause. Unsubscribe or disable mods one at a time until the game starts. Source: [pwmodding.wiki Workshop troubleshooting](https://pwmodding.wiki/docs/users/workshop/troubleshooting).
- **A world crashes mentioning `PalDynamicItemWorldSubsystem` or `StaticItemId`, or loads forever.** A mod that added items or buildings is missing or out of date. Reinstall it once it's updated, or restore your backup. Source: [pwmodding.wiki Workshop troubleshooting](https://pwmodding.wiki/docs/users/workshop/troubleshooting).

## Rolling back

- Untick mods under Options → Mod Management, or unsubscribe from them on the Workshop.
- To remove manual mods completely, follow [Pocketpair's removal steps](https://guideline.palworldgame.com/palworld-mod-guideline): back up your saves, delete the mod files in `Pal\Binaries\Win64` and `Pal\Content\Paks`, then verify the game files in Steam.
- If problems continue, Pocketpair recommends uninstalling Palworld, deleting the leftover game folder and reinstalling.
- Steam has no older Palworld branch, so you can't roll back the game itself. Restore the save backup you made before the patch or before adding mods.
