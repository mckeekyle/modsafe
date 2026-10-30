# How to install GTA V Enhanced mods

GTA V Enhanced is the March 2025 PC version with ray tracing settings, the one that runs `GTA5_Enhanced.exe`. Its Story Mode mods come mostly from **GTA5-Mods.com**, and Legacy mods don't automatically work on it: use builds marked *Enhanced* or *Legacy & Enhanced*. Script mods run on **Script Hook V**, C# mods on **Script Hook V .NET Enhanced**, and replacement or add-on files load through **OpenRPF**, because OpenIV.ASI doesn't work on Enhanced. Rockstar doesn't support mods, and they're for Story Mode only.

## Steps

1. **Check you have Enhanced.** Steam lists it as *Grand Theft Auto V Enhanced*, and the game folder contains `GTA5_Enhanced.exe`. If you see `GTA5.exe`, use the [Legacy guide](/gta-v-legacy/install/) instead.
2. **Back up first.** Copy your saves from `Documents\Rockstar Games\GTAV Enhanced\Profiles`. Note your build (right-click `GTA5_Enhanced.exe` › Properties › Details › Product version) and compare it with the build on [this page's verdict](/gta-v-enhanced/).
3. **Plan for patch days.** GTA V must be on the latest build to start, so you can't hold an update back for long. In Steam, set GTA V Enhanced to update only when you launch it ([how](/guides/stop-steam-auto-updates/)), and when a patch lands, play unmodded until [the verdict](/gta-v-enhanced/) says Script Hook V supports the new build.
4. **Install Script Hook V.** Download it from [GTA5-Mods.com](https://www.gta5-mods.com/tools/script-hook-v) and copy `ScriptHookV.dll` and `dinput8.dll` (the ASI loader) into the folder that holds `GTA5_Enhanced.exe`. Launch Story Mode and press F4 to check the bundled Native Trainer opens.
5. **Install DirectStorageFix.** With DirectStorage on, Enhanced stops scripts writing their own config and log files. [DirectStorageFix](https://www.gta5-mods.com/scripts/directstoragefix) restores that, and trainers such as Menyoo and Rampage recommend it.
6. **Set up OpenRPF for file mods.** Install [OpenRPF](https://www.gta5-mods.com/tools/openrpf-openiv-asi-for-gta-v-enhanced) as its readme explains, then create a `mods` folder in the game folder. Modified archives go there, so the original files stay untouched.
7. **Add Script Hook V .NET Enhanced if a mod needs it.** Install Microsoft .NET Framework 4.8, then copy [Script Hook V .NET Enhanced](https://www.gta5-mods.com/tools/script-hook-v-net-enhanced)'s files into the game folder. C# scripts go into a `scripts` folder you create there.
8. **Add mods one at a time.** Put `.asi` files next to `GTA5_Enhanced.exe`, scripts in `scripts`, and replacements or add-ons in `mods` exactly as each readme says. Launch between mods, so you know which one broke something.

## Common pitfalls

- **Installing Legacy-only mods.** Many older mods, and OpenIV.ASI, only work on Legacy. Check the mod page names Enhanced.
- **Taking mods into GTA Online.** Script Hook V closes the game when you try, but other mods don't. Rockstar can ban accounts for modding Online. [Straight To Story Mode](https://www.gta5-mods.com/scripts/straight-to-story-mode) skips the Online landing page so you don't start Online by accident.
- **BattlEye.** If BattlEye is turned on for GTA V, ASI mods won't load. Turn it off in the Rockstar Games Launcher's settings for GTA V before playing modded Story Mode.
- **Enhanced moves faster than Legacy.** Rockstar has patched Enhanced more often, and Script Hook V sometimes supports Legacy first. Check [the Enhanced verdict](/gta-v-enhanced/), not the Legacy one.

## Common errors and fixes

- **"Critical error. Unknown game version" from Script Hook V.** The game updated and Script Hook V doesn't support the new build yet. Wait for its update, or play without mods by moving `dinput8.dll` out of the folder. Source: [Script Hook V's page](https://www.gta5-mods.com/tools/script-hook-v).
- **Trainer settings don't save.** DirectStorage is blocking file writes. Install [DirectStorageFix](https://www.gta5-mods.com/scripts/directstoragefix). Source: [DirectStorageFix](https://www.gta5-mods.com/scripts/directstoragefix).
- **Crashes with many add-on archives.** Install [Packfile Limit Adjuster Enhanced](https://www.gta5-mods.com/scripts/packfile-limit-adjuster-enhanced). For add-on cars whose tuning parts are missing, add [Modkit Limit Adjuster Enhanced](https://www.gta5-mods.com/scripts/modkit-limit-adjuster-enhanced). Source: [Packfile Limit Adjuster Enhanced](https://www.gta5-mods.com/scripts/packfile-limit-adjuster-enhanced).

## Rolling back

- Steam has no older branch for GTA V Enhanced, and the game must be up to date to start, so you can't roll the game back. Wait for Script Hook V to catch up.
- To play unmodded meanwhile, move `dinput8.dll`, your `.asi` files and the `scripts` folder out of the game folder.
- If files are damaged, run Steam › Properties › Installed Files › Verify integrity of game files. Mods in the `mods` folder aren't affected.
