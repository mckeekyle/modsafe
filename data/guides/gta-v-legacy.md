# How to install GTA V Legacy mods

GTA V Legacy is the original 2015 PC version, the one that runs `GTA5.exe`. Its Story Mode mods come almost entirely from **GTA5-Mods.com**. Script mods run on **Script Hook V**, C# mods on **Script Hook V .NET**, and replacement or add-on files load through **OpenIV**'s mods folder. Rockstar doesn't support mods, and they're for Story Mode only: never take a modded game into GTA Online.

## Steps

1. **Check you have Legacy.** Steam lists it as *Grand Theft Auto V Legacy*, and the game folder contains `GTA5.exe`. If you see `GTA5_Enhanced.exe`, use the [Enhanced guide](/gta-v-enhanced/install/) instead: most Legacy mods don't work there.
2. **Back up first.** Copy your saves from `Documents\Rockstar Games\GTA V\Profiles`. Note your build (right-click `GTA5.exe` › Properties › Details › Product version) and compare it with the build on [this page's verdict](/gta-v-legacy/).
3. **Plan for patch days.** GTA V must be on the latest build to start, so you can't hold an update back for long. In Steam, set GTA V Legacy to update only when you launch it ([how](/guides/stop-steam-auto-updates/)), and when a patch lands, play unmodded until [the verdict](/gta-v-legacy/) says Script Hook V supports the new build.
4. **Install Script Hook V.** Download it from [GTA5-Mods.com](https://www.gta5-mods.com/tools/script-hook-v) and copy `ScriptHookV.dll` and `dinput8.dll` (the ASI loader) into the folder that holds `GTA5.exe`. Launch Story Mode and press F4 to check the bundled Native Trainer opens.
5. **Add Script Hook V .NET if a mod needs it.** Install Microsoft .NET Framework 4.8 and the Visual C++ redistributable, then copy [Community Script Hook V .NET](https://www.gta5-mods.com/tools/scripthookv-net)'s files into the game folder. C# scripts go into a `scripts` folder you create there.
6. **Set up OpenIV for file mods.** Install [OpenIV](https://www.gta5-mods.com/tools/openiv), choose GTA V for Windows, then use Tools › ASI Manager to install the ASI loader and OpenIV.ASI. Create a `mods` folder in the game folder, and let OpenIV copy each archive you edit into it, so the original files stay untouched.
7. **Add mods one at a time.** Put `.asi` files next to `GTA5.exe`, `.dll`/`.cs` scripts in `scripts`, and replacements or add-ons inside `mods` exactly as each mod's readme says. Launch between mods, so you know which one broke something.
8. **Add limit adjusters for big packs.** Large add-on vehicle, weapon or map packs can hit the game's built-in limits. Install [Packfile Limit Adjuster](https://www.gta5-mods.com/tools/packfile-limit-adjuster) and [HeapAdjuster](https://www.gta5-mods.com/tools/heapadjuster) before you add dozens of packs.

## Common pitfalls

- **Taking mods into GTA Online.** Script Hook V closes the game when you try, but other mods don't. Rockstar can ban accounts for modding Online. Remove or rename `dinput8.dll` and your `mods` folder before playing Online.
- **BattlEye.** If BattlEye is turned on for GTA V, ASI mods won't load. Turn it off in the Rockstar Games Launcher's settings for GTA V before playing modded Story Mode.
- **Editing the original archives.** Edit files only inside the `mods` folder. A Steam verify then restores the originals instead of downloading the whole game again.
- **Enhanced builds of mods.** A mod labelled *Enhanced only* won't load on Legacy. Check the mod page says Legacy, or both.

## Common errors and fixes

- **"Critical error. Unknown game version" from Script Hook V.** The game updated and Script Hook V doesn't support the new build yet. Wait for its update (the [verdict](/gta-v-legacy/) turns Safe when it ships), or play without mods by moving `dinput8.dll` out of the folder. Source: [Script Hook V's page](https://www.gta5-mods.com/tools/script-hook-v).
- **ERR_FIL_PACK_1 on launch.** You have more archives than the game allows. Install [Packfile Limit Adjuster](https://www.gta5-mods.com/tools/packfile-limit-adjuster). Source: [Packfile Limit Adjuster](https://www.gta5-mods.com/tools/packfile-limit-adjuster).
- **ERR_MEM_EMBEDDEDALLOC_ALLOC crash.** Too many add-ons for the game's memory heap. Install [HeapAdjuster](https://www.gta5-mods.com/tools/heapadjuster) and raise the heap in its ini. Source: [HeapAdjuster](https://www.gta5-mods.com/tools/heapadjuster).
- **C# scripts do nothing.** Script Hook V .NET or its .NET Framework prerequisite is missing, or the script targets a different SHVDN version. Check `ScriptHookVDotNet.log` in the game folder. Source: [Community Script Hook V .NET](https://www.gta5-mods.com/tools/scripthookv-net).

## Rolling back

- Steam has no older branch for GTA V Legacy, and the game must be up to date to start, so you can't roll the game back. Wait for Script Hook V to catch up.
- To play unmodded meanwhile, move `dinput8.dll`, your `.asi` files and the `scripts` folder out of the game folder. Your `mods` folder only loads through OpenIV.ASI, so it stays inactive.
- If files are damaged, run Steam › Properties › Installed Files › Verify integrity of game files. It doesn't touch the `mods` folder.
