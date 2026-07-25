---
name: deploying-ff9-mods
description: Deploy, hot-reload, and debug FF9 mod builds through the edit-deploy-~ loop -- the procedure every content task terminates in. Use whenever the user runs `tools/deploy_field.py` or `deploy_battle`; presses ~ (tilde) to reload/warp in-game; or hits a post-deploy symptom (black screen, wrong dialogue but correct flags, after-battle softlock, "nothing changed after deploy"). Covers `.ff9deploy.toml` resolution and the stacked mod-folder targets (`FF9CustomMap` + `FF9CustomMap-world`), id-bands (real 10-3100 / custom 4000-9899 / scratch 30000-32767), the GLOBAL EventDB/SceneData distinct-id rule and null-`.eb` black-screen diagnosis, text-block/`.mes` shadowing across stacked folders, mesID registration, reverting a deploy, and re-wiring New Game after a wholesale campaign deploy. For campaign/journey deploy see `building-ff9-campaigns`; for rebuilding the engine DLL see `building-the-memoria-engine`; for authoring a field's logic see `authoring-ff9-field-scripts`.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Deploying FF9 Mods

Every content change terminates in edit -> deploy -> ~. This skill owns that loop plus post-deploy
failure diagnosis. Campaign/journey deploys belong to `building-ff9-campaigns`; engine-DLL rebuilds
to `building-the-memoria-engine`; authoring the field's logic itself to `authoring-ff9-field-scripts`.
The Workspace GUI drives this loop, so a defect in the deploy UI itself (a dead button, a wrong
receipt, the revert ledger, the drift chip) belongs to `working-on-the-ff9-workspace`, not here.

## The edit->deploy->~ fast loop

1. Author/edit a `field.toml`.
2. `py tools/deploy_field.py <field.toml> [--id N]` — builds + deploys reversibly (default test
   slot 4003 = `TESTROOM`); writes a per-id `revert_deploy_<id>.py`.
3. In-game: **~ -> Reload field** (re-reads the current field's `.eb`/`.mes`/scene/walkmesh/art
   from disk) OR **~ -> Warp to field -> `<id>`**.
4. Ask the human to verify. One change = one commit = one in-game check.

## When a relaunch is required

Only three things — everything else is menu-hot:
- the FIRST deploy of a *new* id (registers its DictionaryPatch line),
- a BattlePatch change,
- an engine-DLL rebuild.

## Choosing a deploy target

Resolution order: CLI `--mod-folder` > `$FF9_MOD_FOLDER` > `.ff9deploy.toml` (gitignored) >
default `FF9CustomMap`/4003. Live targets (verified against the install 2026-07-24):
`FF9CustomMap` (master, scratch id 30000) and `FF9CustomMap-world` (overworld only) — the `-bb`/`-ih`
worktree-era slots no longer exist. Confirm with `.ff9deploy.toml` + `Memoria.ini [Mod] FolderNames`.

## The mod-folder stack & distinct-id rule

`Memoria.ini [Mod] FolderNames` stacks the folders; each folder's own DictionaryPatch/BattlePatch
is read at launch. **EventDB/SceneData are GLOBAL** across the stack -> distinct ids are required
even across folders. **THE LAUNCHER LAW (root-caused 2026-07-12): any edit that adds to or
reorders `FolderNames` MUST set `[Mod] Priorities` to the SAME entries in the SAME order, with
the game + launcher closed** — the Memoria Launcher treats `Priorities` as the MASTER order and
rewrites `FolderNames` from it at every Play click (`MainWindow_ModManager.cs`
`LoadModSettings`/`UpdateModSettings`), so a `FolderNames`-only edit is silently reverted.
`Priorities` may additionally list inactive (unchecked) mods — leave those entries in place. Kit
code routes writes through `ff9mapkit.coop.mod_order_updates` (the one helper that keeps the
invariant). Full lookup (id bands, slots, `.ff9deploy.toml` keys):
[references/id-bands-and-folders.md](references/id-bands-and-folders.md).

## Diagnosing a black screen

Registered + scene renders + null `.eb` = a global EventDB id collision across stacked folders ->
grep every stacked folder's `DictionaryPatch.txt` for the duplicate id. A BG-borrow black screen =
`<area>` < 10 (see `authoring-ff9-scenes`). Full symptom->cause->fix table:
[references/deploy-symptoms.md](references/deploy-symptoms.md).

## Text-block / .mes shadow

The engine reads a field's `.mes` from the highest-priority `FolderNames` folder that defines it ->
a lower folder's dialogue is SHADOWED (wrong text, right flags — ~ -> Flags is the reliable proof).
Fix: pick an unshadowed real `MesDB` id, or pin `text_block=N` in `.ff9deploy.toml` (arbitrary ids
don't load; a DictionaryPatch `MessageFile` line registers a custom mesID — read memory
`[[reference-ff9-mesid-registration]]`). `deploy_field.py` warns via `deploystack.py`.

## Reverting a deploy

`py tools/scroll_out/revert_deploy.py` (latest) or `revert_deploy_<id>.py`.

## Re-wiring New Game

A `deploy-campaign` wholesale-replace WIPES the field-70 override -> re-run
`py tools/wire_newgame_from_stock.py 6000` after every opening/campaign re-deploy. Detail: read
memory `[[project-ff9-new-game-entry]]`.

## Handoff

I cannot see the running game (CLAUDE.md §2): after any deploy, STOP and ask the human to playtest
and report. Never assume it worked because it built.

## Additional resources

- Docs: `SETUP.md` (repo root), `ff9mapkit/docs/TROUBLESHOOTING.md`, `ff9mapkit/docs/ENGINE.md`.
- Memory (read on demand): `[[project-ff9-git-layout]]`, `[[project-ff9-eventdb-id-collision]]`,
  `[[project-ff9-text-block-shadow]]`, `[[reference-ff9-mesid-registration]]`,
  `[[project-ff9-new-game-entry]]`, `[[project-ff9-test-suite-perf]]`.
