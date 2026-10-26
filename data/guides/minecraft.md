# How to install Minecraft mods (Java Edition)

Minecraft Java mods are built for one **mod loader** (Fabric, Forge or NeoForge) and one **exact game version**. The easiest way to manage them is a launcher with profiles, like the **Modrinth App** or **Prism Launcher**, which download mods and their requirements for you. Our Essential list uses Fabric.

## Steps

1. **Check the version.** Look at ModSafe's Minecraft page: if the newest release just came out, your favourite mods may not have ported yet. You can pick an older game version in the launcher.
2. **Install a launcher.** Download the Modrinth App or Prism Launcher from the official sites and sign in with your Microsoft account.
3. **Create a profile.** Choose Fabric as the loader and the Minecraft version you want. The launcher installs Fabric Loader for you.
4. **Add Fabric API first.** Almost every Fabric mod requires it.
5. **Add performance mods.** Sodium, Lithium, FerriteCore and Entity Culling, then Iris if you want shaders.
6. **Add the rest.** Mod Menu, the maps and interface mods. Use the launcher's search so you get the build for your version.
7. **Launch and test.** Make a new test world before loading your main save.

## Common pitfalls

- **Mixing loaders.** A Forge mod won't load on Fabric and vice versa. Check the loader tag on Modrinth.
- **Wrong game version.** Each mod file targets specific versions. The launcher filters for you; manual downloads don't.
- **Missing dependencies.** The game's crash screen lists what's missing. Install it and try again.
- **Download sites.** Only use Modrinth, CurseForge or the author's own site. Reupload sites often bundle malware.
- **Shaders without Iris.** Shader packs need Iris (Fabric) or another shader loader.

## Common errors and fixes

- **The Fabric installer won't run. What do I need?** The installer is a Java program. Fabric's docs say Minecraft 26.1 needs at least Java 25. Source: [Fabric docs: installing Java](https://docs.fabricmc.net/players/installing-java/windows).
- **I installed a mod but it doesn't show up in game. What did I miss?** Choose the Fabric profile in the launcher, and put the mod `.jar` files in your `.minecraft\mods` folder. Most mods also need Fabric API in the same folder. Source: [Fabric docs: installing mods](https://docs.fabricmc.net/players/installing-mods).
- **The game crashes. How do I find the mod responsible?** Open the newest file in `.minecraft/crash-reports` and read the stack trace. The first mod named there is usually the cause, and Mixin frames show up as `modid$handlerName`. Share the report on mclo.gs or a Gist when asking for help. Source: [Fabric docs: reading crash reports](https://docs.fabricmc.net/players/troubleshooting/crash-reports).

## Rolling back

- Disable a mod in the launcher (or remove its .jar from the profile's mods folder).
- To go back to an older game version, create a separate profile with that version and copy a backup of your world into it. Opening a world in a newer version upgrades it.
- Back up your world folder before opening it on a newer version. Worlds upgraded to a newer version can't safely go back.
