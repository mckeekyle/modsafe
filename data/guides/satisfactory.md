# How to install Satisfactory mods

Satisfactory mods come from **ficsit.app** (the Satisfactory Mod Repository) and run on the **Satisfactory Mod Loader (SML)**. Install them with the **Satisfactory Mod Manager (SMM)**. It downloads each mod, its dependencies and the right SML version, and puts the files in your game folder. Mods work on the Steam and Epic PC versions only; they don't work on consoles.

## Steps

1. **Launch the game once.** Start Satisfactory to the title screen at least once so the game folders and config exist.
2. **Back up your saves.** Copy `%LOCALAPPDATA%\FactoryGame\Saved\SaveGames` somewhere safe, especially before a game update.
3. **Install Satisfactory Mod Manager.** Download it from [smm.ficsit.app](https://smm.ficsit.app/) or its GitHub releases page (or run `winget install SatisfactoryModding.SatisfactoryModManager`). It finds your Steam or Epic install by itself.
4. **Pick the right install and branch.** Choose your game install in the Install dropdown. SMM still labels the stable branch "Early Access" (a leftover name from before 1.0); stable and Experimental are separate installs, and most mods target stable.
5. **Filter to Compatible.** Set the funnel filter to Compatible so SMM only shows mods that work with your selected install.
6. **Install mods.** Click the download arrow next to a mod. SMM adds SML and any required libraries (such as ModularUI or MarcioCommonLibs) for you.
7. **Launch the game.** Start from SMM's Launch button or from Steam/Epic as usual. The mod files stay in place either way, so mods still load.
8. **Share a profile for multiplayer.** Export your SMM profile and have friends import it. Every player generally needs the exact same mods.

## Common pitfalls

- **Switching to Experimental.** A big Experimental update often breaks most mods for a while. Check each mod's rocket (Early Access) and flask (Experimental) stickers on ficsit.app before switching.
- **Trusting stickers blindly.** The Works/Damaged/Broken stickers are set by hand and can lag behind a new update.
- **Uninstalling SMM to remove mods.** That leaves the mod files in your game. Turn mods off inside SMM first.
- **Saving without your mods.** Loading a modded save without the mods drops their content, and saving then makes that loss permanent.
- **Downloading mods elsewhere.** Only use ficsit.app and SMM; files there are checked before they're approved.

## Common errors and fixes

- **SMM says "No Satisfactory Installs Found".** SMM asks Steam and Epic where the game is. If you moved the game folder, add the new folder as a Steam library folder; on Epic, reinstall the game. Source: [Satisfactory Modding FAQ](https://docs.ficsit.app/satisfactory-modding/latest/faq.html).
- **Downloads fail with "Premature close", "ETIMEDOUT" or "3 attempts to download failed".** The download is being cut off. Disable SMM's download timeout, or download the zip from ficsit.app and put it in `%localappdata%\ficsit\downloadCache`. Source: [Satisfactory Modding FAQ](https://docs.ficsit.app/satisfactory-modding/latest/faq.html).
- **The game crashes after an update.** Use SMM's "Generate debug info" to collect game, SML and SMM logs, then pause half your mods at a time to find the culprit. Source: [Satisfactory Modding FAQ](https://docs.ficsit.app/satisfactory-modding/latest/faq.html).
- **Which mods did this save use?** SML stores the mod list in the save header; load the save with SML installed and it lists the mods and versions. Source: [Satisfactory Modding FAQ](https://docs.ficsit.app/satisfactory-modding/latest/faq.html).

## Rolling back

- Click "Mods off" in the top-left of SMM to play vanilla. If that fails, delete the `FactoryGame\Mods` folder in your game install.
- Pause a single mod with its Play/Pause button, or pick an older version from the mod's "Change version" dropdown.
- If an update broke your mods and you need the old game build, the [Satisfactory Modding FAQ](https://docs.ficsit.app/satisfactory-modding/latest/faq.html) explains backing up your game folder or downloading an older Steam depot. This isn't supported and you do it at your own risk.
- Verify game files in Steam or Epic to get back to a clean, current install.
