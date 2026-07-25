# REVERT — R1, THE DRY LOOP (Southern Ring)

Run 2026-07-25, worktree `ff9-special-effect-plugin-dll-2fdd97`, owner-authorized install writes.
Everything below is in `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\` unless noted.
Backup timestamp for this run: **`20260725-172814`**.

**472 install files written. `FF9CustomMap` (the main mod folder) was NOT touched — 0 files.
Zero terrain GEOMETRY bytes changed.** A relaunch is required to apply any of it, and **has not
happened yet** — until the owner relaunches, the live game is still running the pre-run state.

---

## 1. What was written

| # | Class | Files | Where |
|---|---|---|---|
| 1 | `DictionaryPatch.txt` (+2 lines) | 1 | `FF9CustomMap-world/DictionaryPatch.txt` |
| 2 | Field 6601 event scripts | 7 | `FF9CustomMap-world/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/<lang>/EVT_LANTERN_HALL.eb.bytes` |
| 3 | Field 6601 text block | 7 | `FF9CustomMap-world/FF9_Data/EmbeddedAsset/text/<lang>/field/6601.mes` |
| 4 | World nameplate text block 68 | 7 | `FF9CustomMap-world/FF9_Data/EmbeddedAsset/text/<lang>/field/68.mes` |
| 5 | World dispatchers (9 × 7 langs) | 63 | `FF9CustomMap-world/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world/<lang>/EVT_WORLD_WORLD{00,02,03,05,07,08,09,10,11}.eb.bytes` |
| 6 | Event tiles (Disc1) | 1 | `FF9CustomMap-world/FF9_Data/WorldMap/Disc1/0_1/r18/Block[0][18] Terrain.ff9mesh` |
| 7 | Disc4 mirror | 386 | `FF9CustomMap-world/FF9_Data/WorldMap/Disc4/0_1/**` |

Of #5, **only the 7 `EVT_WORLD_WORLD11.*` files already existed** (the boat work). The other 56 are new.
Of #7, the mirror rewrites the whole Disc4 tree from Disc1 and is **idempotent** — the only file whose
CONTENT changed for R1 is `Disc4/0_1/r18/Block[0][18] Terrain.ff9mesh`.

Full machine-readable manifest: `studies/overworld-topography/out/world-design/r1_build_report.json`
(`written_to_install`).

## 2. Backups taken BEFORE writing

| Backup | Covers |
|---|---|
| `backups/FF9CustomMap.DictionaryPatch.txt.20260725-172814` | the main folder's registry (untouched, kept as proof) |
| `backups/FF9CustomMap-world.DictionaryPatch.txt.20260725-172814` | pre-6601 `-world` registry (28 bytes, one `3DModel` line) |
| `backups/r1-entrance-presurgery.20260725-172814/world-eb/<lang>/EVT_WORLD_WORLD11.eb.bytes` | **all 7 langs** of the only pre-existing dispatcher |
| `backups/r1-entrance-presurgery.20260725-172814/Disc1-r18/Block[0][18] {Terrain,Object,Beach1}.ff9mesh` | the entrance block, Disc1 |
| `backups/r1-entrance-presurgery.20260725-172814/Disc4-r18/Block[0][18] {Terrain,Object,Beach1}.ff9mesh` | the entrance block, Disc4 |
| `ff9mapkit/backups/world-entrance/EVT_WORLD_WORLD11.us.20260725-173404.eb.bytes` | the kit's own backup — **US only**, which is why the 7-lang snapshot above was taken first |

## 3. Undo

### 3a. The field (steps 1–4)

```
py tools/scroll_out/revert_deploy_6601.py
```

Removes the 6601 assets and its `DictionaryPatch` lines. Written by `deploy_field.py`.

### 3b. The entrance surgery (step 5) — no generated revert script; do it by hand

```sh
G="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
B="backups/r1-entrance-presurgery.20260725-172814"

# 1. delete the 56 NEW dispatcher files (world00,02,03,05,07,08,09,10 -- keep world11)
for L in us uk fr gr it es jp; do
  for D in WORLD00 WORLD02 WORLD03 WORLD05 WORLD07 WORLD08 WORLD09 WORLD10; do
    rm -f "$G/FF9CustomMap-world/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world/$L/EVT_WORLD_$D.eb.bytes"
  done
done

# 2. restore the PRE-EXISTING world11 dispatcher, all 7 langs
cp -r "$B/world-eb/." "$G/FF9CustomMap-world/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world/"

# 3. restore the event-tile block on BOTH discs
cp "$B/Disc1-r18/Block[0][18] Terrain.ff9mesh" "$G/FF9CustomMap-world/FF9_Data/WorldMap/Disc1/0_1/r18/"
cp "$B/Disc4-r18/Block[0][18] Terrain.ff9mesh" "$G/FF9CustomMap-world/FF9_Data/WorldMap/Disc4/0_1/r18/"

# 4. drop the world nameplate text block (it is OURS -- nothing shadowed block 68 before)
rm -f "$G/FF9CustomMap-world/FF9_Data/EmbeddedAsset/text/"*"/field/68.mes"
```

Then RELAUNCH. Case 53 goes back to dead, the tile cluster back to plain ground.

### 3c. `.ff9deploy.toml`

`.ff9deploy.toml` at the worktree root is NEW this run (gitignored). Delete it to restore the
"no pin" state — but note that without it this worktree silently shares `FF9CustomMap` and the
4003 scratch slot with 18+ concurrent sessions.

### 3d. Step 6 — THE HUB (field 4600) + NEW GAME — see §6 below

**This section is superseded.** Step 6 was executed in a later pass the same day (plan A, owner-selected).
Undo commands:

```
py tools/scroll_out/revert_newgame_from_stock.py    # New Game -> back to stock
py tools/scroll_out/revert_deploy_4600.py           # remove hub 4600 + its DictionaryPatch lines
```

Historical note (why it was blocked in the first pass):

The hub / New-Game step was **STOPPED before any write** (see §4). No field-70 override exists in
any folder; New Game still plays stock.

## 4. Step 6 as it stood BEFORE the hub pass (HISTORICAL — now resolved, see §6)

`tools/wire_newgame_from_stock.py 4600` would point New Game at an id that **is registered nowhere**:

* no 4600 `field.toml` or `journeys.toml` exists in this worktree (the only journeys registry,
  `ff9mapkit/examples/world_hub/journeys.toml`, is hub id **4500**),
* neither live `DictionaryPatch.txt` contains `FieldScene 4600`,
* no 4600 assets exist under either mod folder.

The wire tool does not validate registration — its dry-run cheerfully planned `Field(50) -> Field(4600)`.
That is the null-`.eb` black screen, on the first thing a player sees. Unblock with either:

* **A (full loop)** — author `[hub] id = 4600` + a `[[journey]] id = "southern-ring", name = "The Southern
  Ring", entry = 6601, set_scenario = 4100` registry, `ff9mapkit gen-hub`, deploy `--id 4600
  --mod-folder FF9CustomMap-world`, then `py tools/wire_newgame_from_stock.py 4600 --mod-folder FF9CustomMap-world`.
* **B (playtest now)** — `py tools/wire_newgame_from_stock.py 6601 --mod-folder FF9CustomMap-world`.
  New Game lands straight in the Lantern Hall; proves berth → shore → nameplate → hall, i.e. everything
  except the hub's own journey row. Reversible via `tools/scroll_out/revert_newgame_from_stock.py`.

## 5. Working files (repo side, not the install)

| Path | Note |
|---|---|
| `studies/overworld-topography/southern-ring/lantern-hall.field.toml` | the authored field |
| `studies/overworld-topography/southern-ring/camera_lantern.bgx` | field 2800's camera — **gitignored**, game-derived |
| `studies/overworld-topography/southern-ring/walkmesh_lantern.bgi` | field 2800's walkmesh, validation-only, never shipped — **gitignored** |
| `studies/overworld-topography/southern-ring/.gitignore` | keeps `*.bgx` / `*.bgi` out of git (provenance gate) |
| `studies/overworld-topography/southern-ring/probe/{topdown,camview}.png`, `report.txt` | the layout probe output that caught the wall-hug |
| `studies/overworld-topography/out/world-design/r1_build_report.json` | the full manifest |
| `ff9mapkit/.ff9mapkit-cache/fields/2800/` | extracted camera + walkmesh (gitignored cache) |
| `ff9mapkit/ff9mapkit/data/**` | regenerated base templates (`extract-templates`, one-time, gitignored) |

**No git commit was made.**

---

# 6. THE HUB PASS — field 4600 + New Game (step 6, plan A) — DONE

Run 2026-07-25 (later the same day), same worktree. Owner selected **plan A: build the hub**
(AskUserQuestion, 2026-07-25), so authoring/deploying NEW field **4600** and rewriting the field-70
New-Game override are owner-authorized. Backup timestamp for this pass: **`20260725-182439`**.

**15 install files written, all in `FF9CustomMap-world`. `FF9CustomMap` untouched (0 files).
Zero pre-existing install files were OVERWRITTEN — every one of the 15 is new.
A RELAUNCH is required** (a first-time `FieldScene`/`MessageFile` registration + the field-70 override);
until the owner relaunches, New Game still plays stock.

## 6.1 Pre-flight (both live registries grepped BEFORE writing)

| Check | Result |
|---|---|
| `FieldScene 4600` in `FF9CustomMap/DictionaryPatch.txt` | **ABSENT** (has 4003/4005/4007/4008/4012 + 30003/30020/30110-30112/30210/30300/30301/30400/30410-30416) |
| `FieldScene 4600` in `FF9CustomMap-world/DictionaryPatch.txt` | **ABSENT** (had only 6601) |
| any `4600` string in either patch file | none |
| any `evt_alex1_ts_opening.eb.bytes` in `FF9CustomMap` / `-world` / `MoguriMain` / `MoguriVideo` | **none** — New Game was stock |

## 6.2 Backups taken BEFORE writing

| Backup | Covers |
|---|---|
| `backups/FF9CustomMap-world.DictionaryPatch.txt.20260725-182439` | the `-world` registry as of the pre-hub state (3 lines: 3DModel 6321, MessageFile 6601, FieldScene 6601) |
| `backups/FF9CustomMap.DictionaryPatch.txt.20260725-182439` | the main folder's registry (untouched by this pass; kept as proof) |

No backup exists — or is needed — for the 7 field-70 override files or the 4600 assets: **none of those
paths existed before this pass**, so reverting is a delete, not a restore (both revert scripts do exactly that).

## 6.3 What was written

| # | Class | Files | Where |
|---|---|---|---|
| 1 | `DictionaryPatch.txt` (+2 lines) | 1 (edit) | `FF9CustomMap-world/DictionaryPatch.txt` — `MessageFile 4600 MES_DWIX_4600` + `FieldScene 4600 21 GRGR_MAP420_GR_CEN_0 SOUTHERN_RING_HUB 4600` |
| 2 | Hub 4600 event scripts | 7 | `FF9CustomMap-world/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/<lang>/EVT_SOUTHERN_RING_HUB.eb.bytes` |
| 3 | Hub 4600 text block | 7 | `FF9CustomMap-world/FF9_Data/EmbeddedAsset/text/<lang>/field/4600.mes` |
| 4 | BG-borrow scene stub | 1 | `FF9CustomMap-world/StreamingAssets/assets/resources/FieldMaps/FBG_N21_SOUTHERN_RING_HUB` |
| 5 | Field-70 New-Game override | 7 | `FF9CustomMap-world/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/<lang>/evt_alex1_ts_opening.eb.bytes` (1396 B each, `Field(50)` → `Field(4600)`) |

Langs = us, uk, fr, gr, it, es, jp.

## 6.4 Undo

```
# 1. New Game back to stock (deletes the 7 field-70 override files)
py tools/scroll_out/revert_newgame_from_stock.py

# 2. remove the hub (deletes 4600's .eb/.mes/FieldMaps + its 2 DictionaryPatch lines)
py tools/scroll_out/revert_deploy_4600.py
```

Then RELAUNCH. That returns the install to the post-R1 / pre-hub state: 6601 still deployed and
reachable via the Lantern Quay entrance, New Game stock. To go further back, follow §3.

## 6.5 Working files added by this pass (repo side)

| Path | Note |
|---|---|
| `studies/overworld-topography/southern-ring/journeys.toml` | the hub registry (`[hub] id = 4600` + one `[[journey]]`) — the source of truth; regenerate the field.toml after editing |
| `studies/overworld-topography/southern-ring/hub.field.toml` | **generated** by `gen-hub` + ONE post-generation edit: the `[walkmesh] reference` probe block (validation-only, never shipped). Re-add it after any regenerate |
| `studies/overworld-topography/southern-ring/camera_hub.bgx` | field 950's camera — **gitignored**, game-derived |
| `studies/overworld-topography/southern-ring/walkmesh_hub.bgi` | field 950's walkmesh, validation-only, never shipped — **gitignored** |
| `studies/overworld-topography/southern-ring/probe_hub/{topdown,camview}.png`, `report.txt` | the layout probe that caught the example's 76u actor collision |
| `studies/overworld-topography/out/world-design/r1_hub_report.json` | this pass's machine-readable manifest |
| `ff9mapkit/.ff9mapkit-cache/fields/950/` | extracted camera + walkmesh (gitignored cache) |
| `tools/scroll_out/revert_deploy_4600.py`, `tools/scroll_out/revert_newgame_from_stock.py` | the generated revert scripts |

**No git commit was made.**
