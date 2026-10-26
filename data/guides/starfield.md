# How to install Starfield mods

Starfield supports official **Creations** in game, but most popular PC mods are on Nexus and many need **SFSE** (the script extender). Use **Mod Organizer 2** or **Vortex** for those. After every Bethesda update, check ModSafe: SFSE and Address Library usually need an update first.

## Steps

1. **Launch once.** Start the game from Steam so it creates its settings, then quit.
2. **Install a mod manager.** Mod Organizer 2 or Vortex, pointed at your Starfield install.
3. **Install SFSE.** Download the build for your game version from the official SFSE site or its Nexus page. Place the loader and DLL next to Starfield.exe. From now on, start the game with sfse_loader.exe.
4. **Add Address Library and Starfield Engine Fixes.** Then Baka Achievement Enabler if you want achievements with mods.
5. **Add interface mods.** The StarUI mods, Compact Mission Menu and Undelayed Menus.
6. **Add gameplay and visual mods.** A few at a time; load a save to test after each batch.
7. **Keep plugin mods sorted.** Let your manager sort plugins and read each mod page for load order notes.

## Common pitfalls

- **Version mismatch.** SFSE plugins stop working after a game update until SFSE and Address Library update.
- **Launching from Steam.** Starting Starfield.exe directly disables SFSE plugins.
- **Mixing Creations and Nexus versions.** Don't install the same mod from both. Pick one source.
- **Loose file mods not loading.** Some mods need loose-file loading switched on in StarfieldCustom.ini. The mod page says if so.

## Common errors and fixes

- **Why does Starfield start without SFSE?** Make sure Steam is running, then start the game with `sfse_loader.exe`. Source: [SFSE readme](https://github.com/ianpatt/sfse).
- **Where do the SFSE files go?** Put the `.dll` and `sfse_loader.exe` in the Starfield folder, next to `Starfield.exe`, not in `Data`. The optional config file goes in `Data\SFSE\SFSE.ini`. Source: [SFSE readme](https://github.com/ianpatt/sfse).
- **Does SFSE work on Game Pass?** No. SFSE supports the Steam version, and its readme lists Game Pass/MS Store as unsupported. Source: [SFSE readme](https://github.com/ianpatt/sfse).
- **Where are the SFSE logs?** In `Documents\My Games\Starfield\SFSE\Logs\`. Source: [SFSE readme](https://github.com/ianpatt/sfse).

## Rolling back

- Disable the mod in your manager (MO2 profile or Vortex deploy).
- If an update broke SFSE, wait for SFSE and Address Library to update rather than uninstalling everything.
- Back up Documents/My Games/Starfield/Saves before big changes.
- Set Steam to update only when you launch the game to avoid surprise breakage.
