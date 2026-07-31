# S7 — Ship it

```toml
[tutorial]
track = "S"
step = 7
builds_on = ["s6-danger"]
goal = "Bundle the rooms into a campaign, land New Game in it, and package a zip anyone can install."
requires = ["game", "gui", "assets"]
```

The last step of the spine: the rooms become one named thing — deployable as a unit, entered
from New Game, and packageable for someone who has never seen the toolkit.

**Starting from:** the spine's two connected, deployed rooms (S3 onward).

## 1. One campaign

**Toolbar → Campaign → New Campaign…**: give it a **Name**, a **Folder**, a **Mod folder** name
(the folder your players will drop into their game), and a **First field id**. Then bring the
two rooms in with the **Campaign** menu's add-field action, pointing at each room's
`field.toml` — the **Map** tab redraws with each member as it lands, entry marked, gateways
drawn as connections.

The Map is the campaign's honest mirror: if the S3 doors are wired, the two rooms show linked;
an unreachable member is named as such.

## 2. New Game lands here

Deploy the campaign from **Ship ▸ Build & Deploy** (campaign deploys replace the mod folder
wholesale — the Workspace warns when that would take a New Game override with it). Then point
New Game: open the entry room's project and press **Point New Game here**. The status line under
it says where New Game currently lands; **Revert New Game** undoes it.

One standing rule worth memorizing: **a campaign re-deploy wipes the New Game override** — after
any campaign-wide re-deploy, point New Game again.

**What you should see:** from the title screen, **New Game** → your first room. No warp menu, no
debug key — the game just starts in your mod.

## 3. A zip for a friend

Switch the Build tab to **Build only — compile every member to the campaign's dist/**, then
**Package (zip)…**. The result is a plain mod folder in a zip: a player unzips it into their FF9
install's mod folders, adds its name to `Memoria.ini`'s `FolderNames`, and plays — no toolkit on
their machine at all.

**The spine ends here.** What exists now: two connected rooms with a resident, persistent story
state, a staged scene, a soundtrack, battles, a New Game entry, and a shippable artifact — every
core loop of the toolkit, exercised once. The rest of the manual assumes exactly this much.

## Where to next

- **Going deeper** — pick a ladder: worlds, click-authoring from a picture, NPC behavior &
  minigames, models & characters, battle craft, or forking FF9 itself
  ([tutorial 07](07-gui-journey.md) territory).
- **The CLI track** — everything the spine did, terminal-native: start at
  [tutorial 01](01-first-fork.md) and [02](02-dev-loop.md).
- **The reference** — [`field.toml`](../FORMAT.md), block by block.
