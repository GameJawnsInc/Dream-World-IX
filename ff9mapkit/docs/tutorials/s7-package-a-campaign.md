# S7 — Package a campaign

```toml
[tutorial]
track = "S"
step = 7
builds_on = ["s6-encounters"]
goal = "Bundle the rooms into a campaign, point New Game at it, and package a zip installable without the toolkit."
requires = ["game", "gui", "assets"]
```

This step bundles the rooms into a campaign: deployable as a unit, entered from New Game, and
packageable as a zip for players who don't have the toolkit.

**Starting from:** the two connected, deployed rooms (S3 onward).

## 1. Create the campaign

**Toolbar → Campaign → New Campaign…**: a **Name**, a **Folder**, a **Mod folder** name (the
folder players will drop into their game), and a **First field id**. Then bring the two rooms in
with the **Campaign** menu's add-field action, pointing at each room's `field.toml`.

The **Map** tab shows the result: each member as a card, the entry marked, the S3 gateways drawn
as connections. An unreachable member is labeled as such.

## 2. Point New Game at it

Deploy the campaign from **Ship ▸ Build & Deploy** (campaign deploys replace the mod folder
wholesale — the Workspace warns when that would take an existing New Game override with it).
Then open the entry room's project and press **Point New Game here**. The status line under it
says where New Game currently lands; **Revert New Game** undoes it.

One standing rule: **a campaign re-deploy wipes the New Game override** — after any
campaign-wide re-deploy, point New Game again.

**What you should see:** from the title screen, **New Game** starts in your first room — no warp
menu, no debug key.

## 3. Package a zip

Switch the Build tab to **Build only — compile every member to the campaign's dist/**, then
**Package (zip)…**. The result is a plain mod folder in a zip: a player unzips it into their FF9
install, adds its name to `Memoria.ini`'s `FolderNames`, and plays — no toolkit on their machine.

**The core track ends here.** The finished mod has two connected rooms, an NPC, persistent story
state, an entry scene, a soundtrack, battles, a New Game entry, and a distributable zip — each
core mechanism of the toolkit used once. The rest of the documentation assumes this much.

## Where to next

- **Going deeper** — pick a track: worlds, click-authoring from a picture, NPC behavior and
  minigames, models and characters, battle design, or forking FF9 itself
  ([tutorial 07](07-gui-journey.md) territory).
- **The CLI track** — everything the core track did, terminal-native: start at
  [C1 — The CLI: fork, edit, deploy](c1-cli-fork-edit-deploy.md).
- **The reference** — [`field.toml`](../FORMAT.md), block by block.
