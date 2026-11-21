# How to install Total War: WARHAMMER III mods

Almost all Total War: WARHAMMER III mods come from the **Steam Workshop**. You subscribe on the Workshop, then turn mods on in the **Mod Manager** that opens when you launch the game. Creative Assembly patches the game often, and even small hotfixes can break script and database mods until their authors update them, so check the status before you let a patch install mid-campaign.

## Steps

1. **Back up your saves.** Copy your campaign saves before adding mods or updating. Modded saves often won't load once you remove a mod or after a patch changes the game, so keep a copy you can go back to.
2. **Check the mods are up to date.** On each mod's Workshop page, look at **Updated** in the right-hand panel and compare it with the latest patch date on [ModSafe's status page](/total-war-warhammer-3/). A mod last updated before the current patch may still work, but treat it with care.
3. **Subscribe on the Steam Workshop.** Open the [WARHAMMER III Workshop](https://steamcommunity.com/app/1142710/workshop/) and click **Subscribe**. If a mod lists **Required items** (MIXER needs Mod Configuration Tool, Mixu's Legendary Lords needs its Asset Pack), subscribe to those too.
4. **Open the Mod Manager.** Launch the game from Steam. The Mod Manager window opens first and lists your subscribed mods, with icons showing whether each is subscribed and up to date ([Creative Assembly's Mod Manager update notes](https://store.steampowered.com/news/app/1142710/view/1830797770244840)).
5. **Turn mods on and save a profile.** Tick the mods you want and save them as a **mod profile**, so you can switch between a modded and a vanilla setup in one click.
6. **Set the load order.** Libraries such as **Mod Configuration Tool** and **MIXER** go near the top; mods that change the same things load in list order. Many mod pages say where they want to go.
7. **Start a new campaign to test.** Play a few turns before committing to a long campaign. Big overhauls (SFO, Radious) usually need a new campaign anyway.

## Common pitfalls

- **Mixing overhauls.** SFO and Radious both rebalance the whole game. Pick one.
- **Missing required items.** A mod that needs MIXER or MCT can crash or do nothing without them. Check each mod's Required items list.
- **Old mods after a patch.** Mods untouched for many patches often break campaign scripts. Disable them first when something goes wrong.
- **Removing mods mid-campaign.** Taking a mod out can break an existing save. Finish the campaign, or keep the mod on.

## Common errors and fixes

- **The game crashes or the campaign won't load right after a patch. What now?** Turn off all mods in the Mod Manager and start the game. If it works, add mods back a few at a time until you find the one that breaks it, and wait for that mod's Workshop update. Steam forum threads after nearly every patch describe this routine. Source: [Steam discussion: mod-breaking patch fixes](https://steamcommunity.com/app/1142710/discussions/0/599657912443340337/).
- **A mod updated, but the game still uses the old version. How do I fix it?** Unsubscribe and subscribe again so Steam downloads a fresh copy, or delete the mod's `.pack` file in `steamapps\workshop\content\1142710\<mod ID>` and let Steam re-download it. The Victory Conditions Overhaul page gives this tip. Source: [Victory Conditions Overhaul Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=3140200173).
- **Can I stop Workshop mods from updating?** No. Steam always updates subscribed mods. To freeze a setup, keep your own copy of the mod files from before the update. Source: [Steam discussion: update issues](https://steamcommunity.com/app/1142710/discussions/0/591766834833796003/).

## Rolling back

- WARHAMMER III keeps rollback branches on Steam. In your Steam Library, right-click the game › **Properties** › **Game Versions & Betas** and pick **last_release** (the previous patch). **last_update** and **last_patch** go further back; each branch's description says which version it is ("Rollback to …").
- Mods that updated for the new patch may not work on the old version, so roll back only to finish a campaign with the mods you already have.
- Switch back to **None** (the default) to get the current version again. More options: [how to stop Steam auto-updates](/guides/stop-steam-auto-updates/).
