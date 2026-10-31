# How to install Europa Universalis V mods

Most Europa Universalis V mods are on the **Steam Workshop**. You turn them on in the game's own **mod manager** by adding them to a **playset**; there's no separate launcher. Each mod declares the game versions it supports (`supported_game_version`, such as `1.4.*`), so a major update like 1.3 to 1.4 breaks most mods until their authors update them. Hotfixes within a version (1.4.5 to 1.4.6) rarely do.

## Steps

1. **Back up your saves.** Copy `Documents\Paradox Interactive\Europa Universalis V\save games` somewhere safe before you add mods or update (Steam Cloud saves are under `Steam\userdata\<your Steam ID>\3450310\remote\save games`, per the [EU5 wiki](https://eu5.paradoxwikis.com/Save-game_editing)). Paradox's [1.4 release notes](https://store.steampowered.com/news/app/3450310/view/1847920302231984) say 1.3 saves load in 1.4 but can hit gameplay problems, so don't count on saves moving between versions.
2. **Check the game version against the mod.** The [EU5 wiki's mod page](https://eu5.paradoxwikis.com/Mod) says to check which game version a mod supports. The Workshop page title or tags (for example "1.4") usually say. ModSafe's status page shows whether the key mods have updated since the current version went live.
3. **Subscribe on the Steam Workshop.** Open the [EU5 Workshop](https://steamcommunity.com/app/3450310/workshop/) and click **Subscribe** on each mod. If a mod lists **Required items** (Construction Manager needs Community Mod Framework, for example), subscribe to those too. Steam downloads Workshop mods to `steamapps\workshop\content\3450310`, one folder per Workshop ID.
4. **Create a playset in the game.** Start EU5, open the mod manager from the main menu ("DLCs and Mods"), create a playset and add your mods to it, as the [EU5 wiki](https://eu5.paradoxwikis.com/Mod) describes.
5. **Set the load order.** Mods lower in the playset win when two mods change the same file ([mod compatibility](https://eu5.paradoxwikis.com/Mod_compatibility)). Put frameworks such as **Community Mod Framework** at the top (its author says to load it first), then interface mods like Glorp UI, then content and overhauls. Free Console Access asks to go at the bottom, after UI mods.
6. **Apply the playset.** Select the playset and click **Apply**. The game reloads with the mods active.
7. **Start with a new campaign for big mods.** Overhauls such as MEIOU and Taxes or Basileia Romaion 1337 change the setup and economy, so start a new game rather than adding them to a running save.
8. **Install non-Workshop mods by hand only if you must.** Extract them to `Documents\Paradox Interactive\Europa Universalis V\mod\`, one folder per mod with its `.metadata\metadata.json` inside, delete any older copy first, then add the mod to your playset ([EU5 wiki](https://eu5.paradoxwikis.com/Mod)). Never install mods into the game's install folder.
9. **Stop surprise updates.** In Steam, set EU5 to update only when you launch it, and check ModSafe before you let a new version install.

## Common pitfalls

- **Assuming a version tag means "updated".** Some authors add the new version's tag during the open beta, before the release. Check that the mod's Workshop "Updated" date is after the update went live.
- **Trusting the in-game version warning blindly.** The warning comes from the mod's `supported_game_version`, which authors sometimes forget to update. A mod can work with an old value, and a correct value doesn't prove it works.
- **Two mods replacing the same interface file.** Only the lower one in the playset wins, so one of them silently stops working. Keep at most one UI overhaul, or follow its authors' advice on order.
- **Removing mods from a running save.** Content-adding mods and overhauls can leave a save broken once they're removed. Finish or abandon that campaign instead.
- **Achievements and Ironman.** Only some mods say they're achievement or Ironman compatible (Thick borders and Better Road Builder do). Assume other mods turn achievements off unless their page says otherwise.

## Common errors and fixes

- **The game says a mod is for an older version.** The mod's `supported_game_version` doesn't match the game. If it was updated after the release went live, it often still works; otherwise disable it or roll back the game until the author updates it. Source: [EU5 wiki: mod structure](https://eu5.paradoxwikis.com/Mod_structure).
- **The map is blank or a save won't load after an update.** Players report this on the Workshop when a mod doesn't match the game version (for example a UI mod after 1.4). Switch to an empty playset to confirm, then re-add mods one by one to find the culprit. Source: [Glorp UI Workshop comments](https://steamcommunity.com/sharedfiles/filedetails/?id=3601047146).
- **A manually installed mod doesn't show up.** The game only loads mods with a `.metadata\metadata.json` inside their folder in `Documents\Paradox Interactive\Europa Universalis V\mod\`. Source: [EU5 wiki: modding](https://eu5.paradoxwikis.com/Modding).
- **Two mods conflict.** The mod lower in the playset overrides files of the same name from mods above it. Reorder them, or keep only one. Source: [EU5 wiki: mod compatibility](https://eu5.paradoxwikis.com/Mod_compatibility).
- **A Workshop mod won't update or looks corrupted.** Unsubscribe, wait for Steam to remove its folder from `steamapps\workshop\content\3450310`, then subscribe again so it downloads fresh. Source: [EU5 wiki: mods](https://eu5.paradoxwikis.com/Mod) (Workshop folder location).

## Rolling back

- Paradox keeps older EU5 versions on Steam. Right-click the game → **Properties** → **Game Versions & Betas**, pick a version and let it download. The steps are in [Paradox's 1.4 release notes](https://store.steampowered.com/news/app/3450310/view/1847920302231984).
- Pick the branch that matches your mods: `1.3.11` is the last 1.3 version, `1.2.5` the last 1.2, `1.1.10` the last 1.1 and `1.0.11` the last 1.0 (checked 2026-10-30). Ignore the open-beta branches.
- Before loading a save, check the version number in the main menu. If it's wrong, verify the game files in Steam (Properties → Installed Files) and check again, as Paradox's notes advise.
- Workshop mods always download their newest version, which may target the newer game. Back up the mod's folder from `steamapps\workshop\content\3450310` before you roll back if you need the old copy.
- Back up saves first: a save made on a newer version may not load on an older one.
