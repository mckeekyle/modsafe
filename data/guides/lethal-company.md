# How to install Lethal Company mods

Lethal Company mods come from **Thunderstore** and run on **BepInEx**. The easiest way is **r2modman** (or the Thunderstore Mod Manager), which installs BepInEx and every dependency for you, and lets you share a profile code so your whole lobby has the same mods.

## Steps

1. **Install r2modman.** Download it from its Thunderstore page and pick Lethal Company.
2. **Create a profile.** Keep a separate profile per modpack so you can switch easily.
3. **Install BepInExPack.** r2modman adds it automatically with your first mod.
4. **Install mods.** Search the Online tab. r2modman pulls in required libraries such as LethalLib and InputUtils.
5. **Start modded.** Launch the game with the Start modded button, not from Steam.
6. **Share the profile.** Use Settings › Profile › Export profile as code, and have friends import it. Everyone needs the same gameplay mods.
7. **Test in a solo lobby first.** Make sure the game reaches the ship without errors before inviting friends.

## Common pitfalls

- **Mismatched mods in a lobby.** Different mod lists or versions cause desyncs or failed joins. Share one profile code.
- **Outdated mods after a game update.** Big updates (v50, v60, v70...) break many mods. Check update dates on Thunderstore and ModSafe's status.
- **Launching from Steam.** That starts the vanilla game. Use the manager's Start modded button.
- **Too many content mods.** Mods that add many moons or monsters can clash. Add a few at a time.

## Common errors and fixes

- **How can I tell whether BepInEx is loading?** Set `Enabled = true` under `[Logging.Console]` in `BepInEx\config\BepInEx.cfg` to open a log console. If `BepInEx.cfg` was never created, BepInEx didn't start at all. Source: [BepInEx docs: troubleshooting](https://docs.bepinex.dev/articles/user_guide/troubleshooting.html).
- **Why won't BepInEx start on Linux or Steam Deck (Proton)?** BepInEx loads through a `winhttp.dll` proxy, which Proton ignores by default. Open winecfg for the game (for example with `protontricks --gui`) and add a `winhttp` override under Libraries, or use a manager that sets this for you. Source: [BepInEx docs: running under Proton/Wine](https://docs.bepinex.dev/articles/advanced/proton_wine.html).
- **Mods still don't load after a manual install. What do I check?** The BepInEx build has to match the game's platform and architecture. Avoid very long paths or paths with non-ASCII characters. If you modded the game a different way before, verify the game files to restore clean ones. Source: [BepInEx docs: troubleshooting](https://docs.bepinex.dev/articles/user_guide/troubleshooting.html).
- **How do I give friends the same mods?** In r2modman, export your profile as a code and have friends import it, so everyone in the lobby runs the same mods and configs. Source: [r2modman README](https://github.com/ebkr/r2modmanPlus).

## Rolling back

- Disable or uninstall a mod in r2modman, or switch back to another profile.
- Start vanilla from Steam to play without mods.
- r2modman can install an older version of a mod (Online tab › mod › select version) if a new one breaks.
