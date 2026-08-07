# C3 — Deploy automation: slots, reverts, relaunch rules

```toml
[tutorial]
track = "C"
step = 3
builds_on = ["c1-cli-fork-edit-deploy"]
goal = "Iterate without relaunching: test slots, reverts, mod-folder resolution, and when a relaunch is still required."
requires = ["game", "repo", "engine-bundle"]
```

The fast iteration loop. After the first registration, a field change is testable in seconds with
no game relaunch.

**Starting from:** C1's fork (`myroom\MYROOM.field.toml`) — any field project works.
**Prerequisites:** a repo checkout (the deploy scripts live in `tools/`), and the Dream World IX
engine bundle for the in-game debug menu (~) ([ENGINE.md](../ENGINE.md)). Without either, use the
standalone path at the bottom.

## The loop

1. **Edit** a `field.toml` (by hand, `ff9mapkit edit`, the Workspace, or a Blender export).

2. **Deploy into the test slot** (from the repo root):

   ```powershell
   py tools\deploy_field.py myroom\MYROOM.field.toml
   py tools\deploy_field.py myroom\MYROOM.field.toml --id 5000    # a different slot
   ```

   Pick any id outside **9000-9012** (reserved for the engine's world-map dispatchers -- a field id
   there black-screens) and at or below **32767** (`fldMapNo` is Int16); the 30000-32767 scratch band
   is safest for throwaway slots.

   `deploy_field.py` sandboxes any `field.toml` into the test slot: it overrides the build to the
   target id + a fixed name in memory (the source file is untouched), reverts that slot's previous
   deploy, backs up the live `DictionaryPatch.txt`/`.mes`, and writes a per-id
   `revert_deploy_<id>.py`. Default slot: **4003** (`TESTROOM`), unless a gitignored
   `.ff9deploy.toml` pins another id. Mod-folder resolution: `--mod-folder` → `$FF9_MOD_FOLDER` →
   `.ff9deploy.toml` → `FF9CustomMap`.

3. **Reload in-game with the debug menu.** Press the **`~` tilde/backquote key** (F6 in engine
   bundles before 2026-07-20 — it moved because stock Memoria binds F6 to a cheat hotkey) to open a
   draggable popup with context-adaptive tabs — **Go / Cheats / Flags** — available in fields and
   battles, plus a **World** tab on the overworld:

   - **Go** — *Reload field* (re-reads the current field's `.eb`/`.mes`/scene/walkmesh/art from
     disk) and *Warp to field* (any registered id, with a search filter and optional
     arrival-entrance / ScenarioCounter overrides). These two drive the loop.
   - **Cheats** — boosters, heal, give items, and a **Time** sub-panel (0.25–4× time scale).
   - **Flags** — get/set/clear/snapshot `gEventGlobal` story flags. The reliable proof that an
     event fired even when dialogue text is shadowed by another mod folder.
   - **World** (overworld only) — teleport, vehicle swap, disc switch.

   After an edit: redeploy → **~ → Go → Reload field**.

## When a relaunch is still required

- the **first deploy of a new field id** (registers its `DictionaryPatch` line);
- a **`BattlePatch.txt`** change (battle tuning, per-encounter BGM);
- **start-state CSVs** (`InitialItems`, `DefaultEquipment`, `BaseStats`, `Leveling`) or
  **`TextPatch.txt`** item names — read at startup / New Game;
- an **engine DLL** change.

## Reverting

```powershell
py tools\scroll_out\revert_deploy.py         # the latest deploy
py tools\scroll_out\revert_deploy_4003.py    # a specific id (drops only that id's lines)
```

Worth walking once deliberately, so the safety net is trusted before it is needed: deploy a
field into a slot, change something visible (move C1's NPC), deploy again, and
**~ → Go → Reload field** — the change is in-game. Now run the slot's `revert_deploy_<id>.py`
and reload again. **What you should see:** the previous deploy back in-game, exactly as it was —
the revert restored the slot's prior files, not merely deleted the new ones.

## Campaigns and journeys

`tools\deploy_campaign.py <campaign.toml>` and `tools\deploy_journey.py <journeys.toml>` install
multi-field projects; both are dry-run by default (`--apply` to write) and need a relaunch after
applying. `deploy_campaign` also wires New Game to the entry field; `deploy_journey` touches New
Game only with `--newgame hub|entry`. Installed copies without a repo checkout use the packaged
equivalents: `ff9mapkit deploy-campaign`, `ff9mapkit deploy-journey`, and `ff9mapkit newgame <id>`
(`newgame` writes immediately; `--dry-run` to preview).

## Standalone path (no test slot, no debug menu)

`ff9mapkit build … --mod-name MyMod` → copy the mod folder into the game install → register it in
`Memoria.ini [Mod] FolderNames` **and** `Priorities` (same order; the launcher rewrites
`FolderNames` from `Priorities` at every Play click) → launch. Engine-independent, but every
change costs a relaunch — the loop above exists because this is slow.
