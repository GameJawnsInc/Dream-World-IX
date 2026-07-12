# 07 — Fork FF9 in the Workspace

Fork a multi-arc slice of *Final Fantasy IX* into a journey, change one line of its real dialogue,
deploy it, and play it back — entirely in the Workspace GUI. This is the full
**fork → edit → deploy → play** loop at game scale.

**Prerequisites:** the kit set up with the `gui` and `assets` extras ([SETUP.md](../../../SETUP.md)),
and the Dream World IX engine bundle installed for fork fidelity
([ENGINE.md](../ENGINE.md)). Launch the Workspace: **`ff9mapkit-workspace`** (installed) or
`py apps\ff9_workspace.pyw` (repo checkout).

Start with a small slice — one or two arcs; regions can be added at any time.

## 1. Create the journey

1. Toolbar → **Journey** → **New Journey**.
2. **Type:** *Multi-campaign arc*.
3. Fill **Hub name**, **First journey id**, and **First journey name** (any identifiers), and pick
   an empty working **folder**.
4. Click **Pick FF9 regions…** and select a starting slice — *Prima Vista → Evil Forest* covers
   the opening arcs.
5. **OK** writes a `journeys.toml` into the folder and opens the Journey Editor.

## 2. Fork the game data

If base templates are not yet extracted, the Import tab's **Regenerate base templates** button
does it (the toolkit ships no Square Enix data; everything is derived from the local install).

1. Click **Fork all missing**. Each selected region is forked from the game's own files — expect
   roughly 10 minutes for the two opening arcs. To restart with a different selection, delete the
   journey directory and recreate it.
2. The working folder now holds one directory per zone, one per field inside it. Per field:
   `field.toml` (the project file), `atlas.png` (the background texture atlas), `sps/` (particle
   effects), plus the script/text sidecars.
3. Click **Fill entry from forks** to wire the journey entry to the forked opening field.

## 3. Edit a line of real dialogue

1. In the tree, open **prima_vista** → the opening field (**PRIM_TH_CGR**).
2. Open its **Script (verbatim .eb)** node.
3. Open **entry 17: player GEO_MAIN_F0_ZDN** → **player_loop / tag 1**.
4. Select the line `"Sure is dark…"`, click **Edit…**, and change the text.
5. **Ctrl-S** (or the editor's **Save** button). Edits in this panel write directly into the
   fork's script — restrict changes to the intended line.

## 4. Check the logic

1. Select the journey root in the tree and open the **Build & Deploy** tab; the `journeys.toml`
   is pre-selected.
2. With the deploy mode on **Preview deploy playbook (dry-run)**, click **Check logic**.
3. Warnings list fields the fork slice references but does not carry (e.g. field 652, Qu's Marsh,
   used by a post-Evil-Forest ATE). These are playable-up-to gaps, not blockers: the journey runs
   until the missing beat, then hands back to the base game. Fix them now (step 5) or later.

## 5. Patch coverage gaps (optional)

1. In the Journey Editor, click **Add region to arc…**.
2. Check the regions containing the reported field ids (regions are listed by seed id — e.g.
   *Marsh (seed 650)* covers 652), then **Add selected**.
3. **Fork all missing** again to fetch the new regions. Repeat as coverage warnings surface.

## 6. Deploy

1. In **Deploy journey**, switch the mode to **Deploy journey to game (one-shot: campaigns →
   links → hub, reversible)**.
2. Under **New Game landing**, select **Wire New Game → straight into the opening (no menu; keeps
   the real FMV)**.
3. Optional: check **Single mod folder** to merge the whole journey into one `FolderNames` entry
   (a re-deploy then re-merges the whole journey). Unchecked, each region gets its own folder.
4. Click **Build / Deploy**. The Problems panel should end with the deploy summary.
5. Register the printed mod folder name(s) in `Memoria.ini [Mod] FolderNames` **and** `Priorities`
   (same order — the launcher rewrites `FolderNames` from `Priorities` at every Play click), or use
   the Memoria launcher itself. Folder order does not affect dialogue — each forked region owns its
   text blocks.

Compatibility note: the toolkit is tested alongside Moguri Mod (+ Moguri Video); keep backups of
any other mod folders before stacking.

## 7. Verify

Launch the game → **New Game**. The opening FMV plays, and the first spoken line is the edited
text. From here the forked slice plays like the original game — every further edit is a re-deploy
away.
