# How to install Monster Hunter Wilds mods

Monster Hunter Wilds mods come from **Nexus Mods** and only work on the PC (Steam) version. Script mods run on **REFramework**, praydog's mod framework for RE Engine games, and most other mods are `.pak` or loose-file mods installed with **Fluffy Mod Manager**. Capcom doesn't support mods and, in its Title Update 4 notice, warns they can stop the game launching or cause crashes after an update.

## Steps

1. **Back up your saves.** Wilds saves live in `Steam\userdata\<your Steam ID>\2246340` ([Steam community guide](https://steamcommunity.com/sharedfiles/filedetails/?id=3471173834)). Copy that folder somewhere safe before adding mods, especially mods that add or edit items.
2. **Install Fluffy Mod Manager.** Download it from [its Nexus page](https://www.nexusmods.com/site/mods/818), extract it, run `Modmanager.exe` and pick Monster Hunter Wilds from the game list.
3. **Install REFramework.** Download `REFramework.zip` from the [latest nightly release](https://github.com/praydog/REFramework-nightly/releases/latest); one zip now covers every RE Engine game. Unless you play in VR, extract **only** `dinput8.dll` into the folder with `MonsterHunterWilds.exe`, as the [REFramework readme](https://github.com/praydog/REFramework#installation) says. You can also drag the zip onto Fluffy Mod Manager, as [FluffyQuack's guide](https://www.patreon.com/posts/113314784) shows.
4. **Check it loads.** Start the game. REFramework's menu opens with the **Insert** key; it creates a `reframework` folder in the game directory on first launch.
5. **Turn on the loose file loader.** For 2024 and later RE Engine games, FluffyQuack's guide says to enable **Loose file loader** in Fluffy Mod Manager so loose-file mods load.
6. **Add mods.** Drag each mod's archive (zip, 7z or rar) onto Fluffy Mod Manager, then click it in the list to install it. Script mods put `.lua` files in `reframework\autorun`, which REFramework loads automatically ([REFramework docs](https://cursey.github.io/reframework-book/)). Add one mod at a time and launch between each.
7. **Leave quest and online play alone.** Capcom has [warned players about modified quests](https://www.vg247.com/monster-hunter-wilds-game-quests-modding-cheating-warning) (more monsters or hunters than the game allows) and asks people not to play them. Keep reward, quest and item-editing mods to single player.
8. **Before each title update, uninstall all mods.** Click **Uninstall all mods** in Fluffy Mod Manager, let Steam update, launch once unmodded, then reinstall mods as their authors update them. Armor and other data mods usually break on title updates.

## Common pitfalls

- **Extracting the whole REFramework zip.** Outside VR, only `dinput8.dll` belongs in the game folder. The readme warns that extra files can make the game unstable.
- **The newest nightly isn't always the best one.** Each nightly is built for every RE Engine game at once, and some have crashed on Wilds (for example [issue #1850](https://github.com/praydog/REFramework/issues/1850)). If a new nightly crashes, go back to the previous one from the [nightly releases](https://github.com/praydog/REFramework-nightly/releases).
- **REFramework from Nexus.** The Nexus copy of REFramework is updated less often than GitHub's nightlies. Get it from GitHub after a title update.
- **Old mod versions left in Fluffy's mod folder.** Keep only the newest version of each mod in Fluffy Mod Manager's `Games\MonsterHunterWilds\Mods` folder, so an old archive isn't installed by mistake ([CatFood's clean-reinstall guide](https://www.patreon.com/CatFoodCan/posts/mhws-mod-clean-133063232)).
- **Frame generation and overlays.** REFramework can crash at launch when FSR3 frame generation is on ([issue #1845](https://github.com/praydog/REFramework/issues/1845)). Turn frame generation off if the game crashes right after installing it.
- **Linux and Steam Deck.** Add the launch option `WINEDLLOVERRIDES="dinput8.dll=n,b" %command%`, as the [REFramework readme](https://github.com/praydog/REFramework#protonlinux) says, or REFramework won't load.

## Common errors and fixes

- **The game won't start or crashes after a title update.** Capcom's advice is to completely uninstall all mods, verify the game files in Steam (Properties → Installed Files → **Verify integrity of game files**), then start the game. Reinstall mods once they are updated. Source: [Capcom's Preparation for Update & A Message on Mods](https://store.steampowered.com/news/app/2246340/view/1818752592134430).
- **Mods don't work and you don't know why.** Update Fluffy Mod Manager, uninstall all mods with it, delete the `Backup` folder under `Games\MonsterHunterWilds` in the manager's folder, reinstall the game (deleting any files left in its folder), then click **Re-read game archives**. Source: [Fluffy Manager 5000 Troubleshooting Guide](https://www.patreon.com/FluffyQuack/posts/fluffy-manager-68199696).
- **You deleted Fluffy Mod Manager before uninstalling mods.** Delete the `natives` folder in the game directory, if you installed PAK mods, delete any PAK file with "patch" in its name (Steam's verify downloads the official ones again), then verify the game files in Steam. Source: [Fluffy Manager 5000 Troubleshooting Guide](https://www.patreon.com/FluffyQuack/posts/fluffy-manager-68199696).
- **Black screen or crash at launch after a title update, even with mods updated.** An outdated mod file is usually still installed. Recent REFramework builds write any incompatible files they find to `reframework_faulty_files.txt` in the game folder, and Obsolete Mod Detector can tell you which mod each file came from. Remove those mods until they're updated. Source: [Obsolete Mod Detector on Nexus Mods](https://www.nexusmods.com/monsterhunterwilds/mods/1651).
- **REFramework crashes or shows script errors.** Script errors show in REFramework's ScriptRunner window. For crashes, report them with the whole `re2_framework_log.txt` and `reframework_crash.dmp` from the game folder. Source: [REFramework documentation](https://cursey.github.io/reframework-book/).

## Rolling back

- Click **Uninstall all mods** in Fluffy Mod Manager to undo pak and loose-file mods.
- To turn off REFramework, delete `dinput8.dll` from the game folder. To remove it completely, also delete the `reframework` folder, `re2_fw_config.txt`, `re2_framework_log.txt` and any `reframework_crash.dmp`. Back up `reframework\data` first if you want to keep script settings.
- Then verify the game files in Steam to put back anything a mod replaced.
- Steam has no older Monster Hunter Wilds branch, so you can't roll back the game itself. Restore the save backup you made before adding mods if a save stops loading.
