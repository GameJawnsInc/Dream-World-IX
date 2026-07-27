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

---

# 7. R2a — THE STATE-RECORD FIX — **STOPPED BEFORE ANY WRITE** (historical; superseded by §8)

Run 2026-07-25 (third pass, same worktree), owner-authorized for install writes
(AskUserQuestion → "Fix + redeploy"). **The authorization was NOT spent.**

**0 install files written. 0 kit-source files written. 0 backups taken (none needed).
Nothing to revert — the install is byte-identical to the post-§6 state.**

The run was read-only by design after the diagnosis contradicted the designed fix. Full
machine-readable record: `studies/overworld-topography/out/world-design/r2a_fix_report.json`.

**Why it stopped.** The designed fix (seed `GLOB[1062] = 9011` hub-side + re-stamp it from the
quay handler) correctly repairs the ROUTING half of the 9009 fall-through — that half is
byte-confirmed. It does **not** repair the ARRIVAL half, and applying it alone is a
**regression**: the kit's `arrive=` preset writes the world player's position into
`C8:83 / D8:86 / C8:88 / D4:91`, which is the **vehicle-composite** actor's mirror block. The
**on-foot** world avatar — the object that actually takes control when `D4:190 == 0`, in all
nine free-roam dispatchers — reads `C8:64 / D8:67 / C8:69 / D4:72`. With `1062` seeded, `D8:2`
stays nonzero, which SUPPRESSES the destination world's own default-point write, so the player
would be `MoveInstantXZY`'d to the on-foot block's fresh-save value `(0, 0, 0)` — world origin,
which the live ground query resolves to **Sea4, topograph 57, open ocean**. That is the
actor-brick class, and strictly worse than today's playable-but-wrong 9009 landing.

**The corrected fix awaiting re-authorization** is smaller than the designed one and touches
only `ff9mapkit/ff9mapkit/content/worldexit.py`:

1. `_POS_X/_POS_Y/_POS_Z/_POS_FACE` → `(0xC8,64)/(0xD8,67)/(0xC8,69)/(0xD4,72)` (the on-foot block).
2. `POSITION_PRESET_KEY` `62` → `35` — key 62 is the ONE key whose cascade arm writes `D8:2 = 0`
   in every scenario band; key 35 is a real disc-1 → 9011 key (13 shipping fields write it) whose
   arm is a bare `WorldMap`, so the preset survives and the world state re-derives from the
   CURRENT band on later discs.

That needs **no** hub edit, **no** `--trigger-only` re-stamp and **no** dispatcher bytes — only a
rebuild + redeploy of field 6601 (7 `.eb` files, hot-reloadable, no relaunch).

**No git commit was made.**

---

# 8. R2a fix2 — THE CORRECTED FIX — **APPLIED**

Run 2026-07-25 (fourth pass, same worktree). The owner was asked a second time (AskUserQuestion,
2026-07-25) and selected **"Fix + redeploy"**, authorizing exactly the two constant-level edits in
`ff9mapkit/ff9mapkit/content/worldexit.py` plus a rebuild + redeploy of field 6601 — the fix §7
specified. Backup timestamp for this pass: **`20260725-202011`**.

**15 install files written, all in `FF9CustomMap-world`. `FF9CustomMap` untouched (0 files).
Zero terrain bytes, zero dispatcher bytes, zero hub bytes. NO relaunch required** — the
`DictionaryPatch` line SET is byte-identical (the two 6601 lines were removed and re-appended, so
only line ORDER changed), and `.eb`/`.mes` content hot-reloads via **~ → Reload field** or a fresh
New Game.

Machine-readable record: `studies/overworld-topography/out/world-design/r2a_fix2_report.json`.

## 8.1 Backups taken BEFORE writing

| Backup | Covers |
|---|---|
| `backups/r2a-fix2-preredeploy.20260725-202011/{us,uk,fr,gr,it,es,jp}/EVT_LANTERN_HALL.eb.bytes` | **all 7 langs** of the live field-6601 event script, 3162 B each (the pre-fix state) |
| `backups/r2a-fix2-preredeploy.20260725-202011/DictionaryPatch.txt` | the `-world` registry as of the pre-fix state |

No pre-image was kept for the 7 `6601.mes` text files: text was out of scope, no text source
changed, and the build is deterministic.

## 8.2 What was written

| # | Class | Files | Where |
|---|---|---|---|
| 1 | `DictionaryPatch.txt` (line reorder only, same set) | 1 (edit) | `FF9CustomMap-world/DictionaryPatch.txt` |
| 2 | Field 6601 event scripts | 7 | `.../eventbinary/field/<lang>/EVT_LANTERN_HALL.eb.bytes` — 3162 → **3198 B** (+36) in every lang |
| 3 | Field 6601 text block | 7 | `FF9CustomMap-world/FF9_Data/EmbeddedAsset/text/<lang>/field/6601.mes` |

Repo side (kit source — the orchestrator commits these, this pass did NOT):
`ff9mapkit/ff9mapkit/content/worldexit.py` (both edits + the ARRIVAL-MODEL docstring) and
`ff9mapkit/tests/test_worldexit.py` (the one stale-constant expectation, which had pinned the
*wrong* position block).

## 8.3 The change, in bytes

The deployed `us` `.eb` differs from the backup in exactly **three** things (whole-file byte diff +
a 24-function table comparison):

1. **+36 bytes inserted** in entry-4/tag-2 (the berth-exit Range body): the **on-foot** position
   block `C8:64 / D8:67 / C8:69 / D4:72` = `(60.0, 4.0, −1168.0)` face 192, written *before* the
   pre-existing vehicle block `C8:83 / D8:86 / C8:88 / D4:91`, which now carries the same values.
2. **One byte 0x3E → 0x23** — the `D8:2` position-preset key, **62 → 35**.
3. **Five offset-table bytes, each +36** — the header entries for the functions after the exit.

Every function before the exit is byte-identical and unmoved; every function after it shifted by
exactly 36. All 7 langs are identical in delta and content shape.

## 8.4 Undo

The redeploy is covered by the same generated revert script as §3a, but that **removes** 6601
entirely. To go back to the pre-fix *state of the field* instead (6601 still installed, exit lane
as it was), restore the 7 backed-up `.eb` files:

```sh
G="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
B="backups/r2a-fix2-preredeploy.20260725-202011"
for L in us uk fr gr it es jp; do
  cp "$B/$L/EVT_LANTERN_HALL.eb.bytes" \
     "$G/FF9CustomMap-world/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/$L/"
done
```

Then **~ → Reload field** (no relaunch). To also undo the kit source, `git checkout` the two files
listed in §8.2 — but note the redeploy above must happen *after* that, or the next build re-emits
the fixed bytes.

To remove 6601 altogether: `py tools/scroll_out/revert_deploy_6601.py` (§3a).

## 8.5 Verified from the DEPLOYED bytes (not the build output)

* both position blocks present exactly once, on-foot first, both `(60, −1168)` face 192;
* `D8:2 = 35` written once; **zero** `D8:2 = 62` writes remain in the file;
* the carried cascade is intact and verbatim — band gate `ScenarioCounter < 5990`, and key **35**'s
  arms are BARE `WorldMap`: band1 **9011**, band2 9003, band3 9007, band4 9008 (key 62's four arms
  still run `D8:2 = 0; WorldMap(9009)` and are simply no longer reached);
* the arrive point `(60, −1168)` ground-queried against the **live stacked meshes** → block (0,18),
  `Terrain`, y 3.0, `idall` 0, topograph 0 = walkable land, 12u clear of the quay trigger tile
  (which carries `idall` 16384) — THE ARRIVAL-CLEARANCE LAW holds. The same probe returns
  `Sea4` / topograph 57 at world (0,0), i.e. the open ocean this fix avoids.

## 8.6 The waystation-6500 precedent (read-only finding — nothing was modified)

The in-game-proven waystation loop used the **same defective constants** (vehicle block + key 62).
It worked because its entrance took the DIRECT route, which records `GLOB[1062]`, so the exit used
the computed lane and never hit key 62's `D8:2 = 0`; `D8:2` stayed nonzero, the destination skipped
its default write — and the on-foot block still held the tile the player had **walked in from**,
because that object's own main loop mirrors it every frame. The authored arrive point was 8u away
from that tile by construction, so the preset being inert was invisible. **The precedent proved the
mirror, not the preset.** The Lantern Hall exposed it because a New-Game player reaches 6601 without
ever walking the overworld, leaving the mirror at its fresh-save `(0,0,0)`.

⚠ Consequence: `ff9mapkit/examples/continent-v1/waystation.field.toml` will emit *different* bytes
the next time it is built (real arrive + key 35 → 9011). It was **not** rebuilt here; re-playtest
6500 if it is ever redeployed.

**No git commit was made.**

---

# 9. THE LANTERN QUAY MARKER — a baked Object landmark on the quay (R2b) — **APPLIED**

Run 2026-07-25 (fifth pass), worktree `gui-workspace-improvements-277c74`, branch
`claude/lantern-quay-marker-5b076a`. Gives the case-53 quay entrance something to LOOK at: until now
it was an invisible 6-tile trigger cluster on featureless grass. Backup timestamp for this pass:
**`20260725-212836`**.

**EXACTLY 2 install files written, both in `FF9CustomMap-world`. Zero Terrain bytes, zero `.eb`,
zero `DictionaryPatch`, zero text, zero files added or removed (891 before, 891 after).
`FF9CustomMap` untouched. NO relaunch required and none performed** — the s34 override is re-read
when the block streams in, so re-entering the overworld picks it up. **The game was never launched
during this pass.**

## 9.1 The design (as executed)

| | |
|---|---|
| Lane | a baked per-block **Object** mesh — stock's own landmark substrate — through the s34 `transform.name`-GENERIC override seam the ring already requires. NOT the scripted 3DModel/`.eb` lane, NOT SPS |
| Asset | **Alexandria Harbour, `Block[21][10] Object`** (disc 1) — FF9's literal harbour/quay gate, and the block's ENTIRE Object part, so it exports whole with no trimming or index slicing: **104 tris / 312 verts**, one submesh `(0, 312)`, single connected component over 66 shared positions, uniform IDALL **6382** (`0x18EE` = area 24, topo 59, flags 2). LOCAL bbox x[0.000, 6.277] y[0.000, 5.531] z[−43.441, −35.055] → footprint **6.277 × 8.387 u**, height **5.531 u**. Carried **verbatim** (positions + UVs + normals) |
| Placement | **ONE** instance, `--at (48, −1157)` → world span x[44.861, 51.139] z[−1161.193, −1152.807], base at **y 3.00** (Block[0][18]'s measured plateau) |
| IDALL | **4078** (`0x0FEE` = area 15, topo 59, flags 2) on all 104 tris — the engine's render-only skip id. Note the donor's own 6382 is *also* topo 59 / flags 2, so the restamp moves **only** the area field and keeps the donor's structural invariants |

**Placement arithmetic.** `--at` anchors the mesh's XZ **bounding-box centre** (`blendio.py:198-203` —
the bbox centre, *not* the vertex centroid) and shifts XZ only (`dy = 0`), so the base is
pre-translated to y 3.00 in the OBJ. The lawful window north of the trigger keep-out is
z ∈ (−1162, −1152] = 10 u for an 8.387 u gate; −1157 is its exact centre, giving **0.807 u** to spare
on each side. Measured clearances: **2.807 u** to the nearest real trigger tile (z ≤ −1164),
**11.565 u** to the arrive point, **0.807 u** to the block's north edge (fully inside block (0,18)).

## 9.1a ⚠ The donor was CORRECTED mid-run — two passes, second supersedes

This section covers **two builds of the same block**, both by the same script and pipeline:

| Pass | Donor | Result | Status |
|---|---|---|---|
| 1 | `Block[18][13] Object` — 9 tris, two instances flanking the trigger at (48, −1158)/(48, −1178) | 2828 B, 18 tris, md5 `6fe27586f1fffc216dd9c292afed6fbe` | **SUPERSEDED** |
| 2 | `Block[21][10] Object` — 104 tris, one instance at (48, −1157) | **16244 B**, 104 tris, md5 `c56e30d40cce10ad06648f8b849e0179` | **LIVE** |

Pass 1 passed all its own gates and probes, but its donor identity rested on `world/locate.py`'s
area→place join, which a deeper 63-block census then **proved broken**: the engine packs **CELL**
coordinates into the world dispatch key, not the IDALL (`ff9.cs:2233`
`num = 0x8000 | (z<<8 & 0x3F00) | (x<<2 & 0xFC) | (id&3)` with `x = cell%48`, `z = cell/48` from
`w_worldPos2Cell`, `ff9.cs:5299-5303`). Names checked against the engine's own navipos autopilot
table contradict `locate()` everywhere. The 9 carried tris are real geometry but a **fragment** of the
South Gate complex — which spans (18,13)+(18,14) at 140 tris — so the carry risked reading in-game as
a cut-off piece rather than a free-standing marker.

Pass 2 needed no separate revert: `world-mesh-build` replaces the block's Object part **wholesale**, so
it overwrote pass 1's file in place. The §9.3 backups are of the ORIGINAL 176-byte stub, so the undo in
§9.5 still returns the install to the true pre-marker state regardless of which pass ran.

## 9.2 Why 4078 is load-bearing, not cosmetic

`WMWorld.LoadBlock` registers `prefab.ObjectForm1` **before** `prefab.TerrainForm1`, and
`RegisterBlockComponent(block, ObjectForm1, form1: true, …)` feeds the loose Object override to
`block.AddWalkMeshForm1(mesh)` (`WMWorld.cs:775-814`). Block (0,18) is a reclaimed cell whose
`Donor.txt` names donor **(0,0)**, and (0,0) *does* have a stock Object component — so our override
takes the `RegisterBlockComponent` path and **enters the walkmesh ahead of Terrain**. Since the ground
query is first-mesh/first-tri-wins, an ordinary `--topograph 59` stamp would have made the gate
**shadow the quay trigger** and the entrance would have stopped firing.

`WMPhysics.Raycast` (`WMPhysics.cs:15-20`) skips triangles whose `tangent.x` is 4078 / 4088 / 2040
outright, so the on-foot walk query never sees the gate: walk-through, no shadow.
`ff9.w_movementUpdate` (`ff9.cs:5160-5164`) additionally keeps a *non-controlled* actor's own Y on a
4078 hit (remapping the id to `0xFD2`) instead of snapping it to the gate top, so followers don't
climb it. Both halves are **measured on the deployed bytes** in §9.8, not merely asserted.

**Stock precedent** (measured, disc 1): Chocobo's Forest ships **100** Object tris of 4078 —
(16,14) = 59, (17,14) = 35, (16,15) = 3, (17,15) = 3. 4078 is the shipping render-only idiom, not a
trick. (The donor's own 6382 / `0x18EE` is separately special-cased in the same `w_movementUpdate`
block, but it is *not* in `WMPhysics`'s skip set — which is why the stock harbour gate is solid and
ours needs the restamp.)

⚠ **4078 is NOT a blanket exemption.** Every sky-cast placement path (`ff9.w_nwpHitBool` callers, e.g.
`ff9.cs:4750`, `4849`) sets `WMPhysics.IgnoreExceptions = true`, which DEFEATS the skip. Marker
geometry under a spawn or an arrive point would still be hit. Hence the hard exclusion: nothing
within 6 u of the berth-exit arrive point (60, −1168) — measured clearance **11.565 u**.

## 9.3 Backups taken BEFORE writing

| Backup | Covers |
|---|---|
| `backups/quay-marker-premint.20260725-212836/Disc1-r18/Block[0][18] Object.ff9mesh` | the live Disc1 Object file, **176 B** (md5 `e4a62c30d82899d19f86bdd6e19df0c9`) |
| `backups/quay-marker-premint.20260725-212836/Disc4-r18/Block[0][18] Object.ff9mesh` | the live Disc4 Object file, **176 B** (same md5 — the two discs were identical) |

Both were the 176-byte **blanking stub** (one down-facing degenerate tri, idall 1, at y −80) that
`world-island` deploys to suppress reclaim-donor (0,0)'s 5 object tris. Pre-state archived at
`probe_marker/probe_before.txt`.

## 9.4 What was written

| # | File | Before | After (LIVE, pass 2) |
|---|---|---|---|
| 1 | `FF9CustomMap-world/FF9_Data/WorldMap/Disc1/0_1/r18/Block[0][18] Object.ff9mesh` | 176 B | **16244 B** |
| 2 | `FF9CustomMap-world/FF9_Data/WorldMap/Disc4/0_1/r18/Block[0][18] Object.ff9mesh` | 176 B | **16244 B** |

Both discs are byte-identical (md5 `c56e30d40cce10ad06648f8b849e0179`); #2 came from
`discmirror.auto_mirror`, which ran as the build's post-step and re-copied the cell's 9 files —
only the Object file differed in content. Whole-folder md5 proof (**891 files before and after — no
file added or removed** — these two the only content changes):
`probe_marker/writeset_md5_diff.txt`.

Pass 1 had written 2828 B / md5 `6fe27586f1fffc216dd9c292afed6fbe` to the same two paths; pass 2
overwrote both (see §9.1a). **No third file was ever touched by either pass.**

The build reported `replaced 0 stub tri(s)` because the replacement check reads **pristine** p0data,
and block (0,18) has no pristine parts (it is reclaimed ocean). The stub it actually replaced was a
mod-folder override. Either way the donor's tris stay overridden — that is the intended outcome.

## 9.5 Undo

```sh
G="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
B="backups/quay-marker-premint.20260725-212836"
cp "$B/Disc1-r18/Block[0][18] Object.ff9mesh" "$G/FF9CustomMap-world/FF9_Data/WorldMap/Disc1/0_1/r18/"
cp "$B/Disc4-r18/Block[0][18] Object.ff9mesh" "$G/FF9CustomMap-world/FF9_Data/WorldMap/Disc4/0_1/r18/"
```

Re-enter the overworld (no relaunch). That restores the blanking stub — the quay goes back to an
invisible trigger, everything else in R1/R2a untouched. Nothing else in the install was modified, so
there is nothing else to undo.

To rebuild the marker instead:
`py studies/overworld-topography/southern-ring/mint_quay_marker.py --build`.

## 9.6 ⚠ STANDING TRAP — `world-island` WIPES this marker

`ff9mapkit/ff9mapkit/world/island.py` (`:955-957` and `:966-969`, via `HIDDEN_PARTS` at `:53`)
**unconditionally** deploys `M.hidden_block_mesh` for the `Object` part of every cell it mints — the
same 176-byte blanking stub this pass replaced. Any future re-run of the island mint over block
(0,18) therefore **silently wipes the marker**. It is not merged, not warned about, not conditional
on an existing override.

**Re-run `mint_quay_marker.py --build` after any `world-island` pass that touches (0,18).** The same
applies to the three remaining R2 quays once they carry markers.

## 9.7 The kit lever added (repo side)

`world-mesh-build --topograph` can only reach IDALL bits 2-7: `obj_to_blockmesh` hard-coded
`encode_id(event=0, area=0, topograph=topograph)`, so **4078 was unreachable** (it needs area 15 +
flags 2). Closed with a raw `--idall N` lever:

| File | Change |
|---|---|
| `ff9mapkit/ff9mapkit/world/blendio.py` | `obj_to_blockmesh(..., idall=None)` stamps a raw 16-bit IDALL instead of the topograph encode (masked `& 0xFFFF`); `build_from_obj(..., idall=None)` plumbs it and reports the effective `idall` in its summary. Docstrings carry the WMPhysics/`w_movementUpdate` mechanism **and** the IgnoreExceptions caveat |
| `ff9mapkit/ff9mapkit/cli.py` | `world-mesh-build --idall N` (0..65535, validated), decoded in the receipt, plus a render-only note when the stamp is 4078/4088/2040 |
| `ff9mapkit/tests/test_world_mesh_deploy.py` | 4 new tests: the gap itself (`no topograph encodes to 4078`), the raw stamp lands on every corner of every tri **with UVs still carried**, `idall=None` keeps the old default, and the 16-bit mask |

`add_solid_base` deliberately does **not** take the raw id: that hull exists to COLLIDE, so it keeps
its topograph-derived id.

Also fixed, one-line doc drift (patch untouched): `memoria-patches/README.md`'s s34 row described the
override as terrain-only and never mentioned `RegisterBareObjectOverride`, which the patch has
carried all along. The row now states that the override is generic over `transform.name`, that an
`ObjectForm1` override IS fed to the Form1 walkmesh ahead of Terrain (the shadowing hazard above),
and that `RegisterBareObjectOverride` is the separate render-only path for a block with no stock
Object component.

## 9.8 Verified from the DEPLOYED bytes, both discs (offline — the game was not launched)

`probe_marker/probe_quay_marker.py` → `probe_marker/probe_output.txt`. **All checks PASS on disc 1 and
disc 4**:

* **the trigger is untouched** — exactly 6 event tris, all idall 16384, union bbox
  x[44.00, 52.00] z[−1172.00, −1164.00]; the ground query at (48, −1168) still returns idall 16384 @ y 3.00;
* **the arrive point is untouched** — (60, −1168) → Terrain, idall 0, topograph 0, y 3.00, in **both**
  query modes (walk-with-skip *and* sky-cast-with-IgnoreExceptions);
* **the marker is present** — the WHOLE donor part, **104 tris / 312 verts**, **every** tri idall 4078,
  per-face normal-Y distribution identical to the donor's (34 up / 60 vertical / 10 down — a pure
  translation must not alter one face normal), world span x[44.861, 51.139] y[3.000, 8.531]
  z[−1161.193, −1152.807] matching the planned footprint to ≤ 0.01 u, base exactly on y 3.00, inside
  the block (0.807 u north-edge margin), ≥ 6 u from the arrive point (**11.565 u**) and clear of the
  keep-out rect (**2.807 u** to the nearest real trigger tile);
* **the UVs carried** — one per vertex, none degenerate, U and V sets byte-equal to the donor's,
  u[0.00391, 0.12793] v[0.12305, 0.18457] on the shared `res(1_24)_objects` atlas (a UV-less carry
  would render flat white off the atlas's alpha-0 corner);
* **the behavioural pair** — at the gate's centre (48, −1157) the walk query passes *through* to
  Terrain (idall 0, y 3.00) while the sky-cast query hits `Object` idall 4078 at y 7.34. That is both
  halves proven at once: the gate really IS in the walkmesh set (so the shadowing hazard was real) and
  the 4078 stamp really does make it walk-through.

## 9.9 Deviations from the written plan (and why)

1. **The donor was corrected mid-run** — see §9.1a. Pass 1's `Block[18][13]` post rested on a
   `world/locate.py` join that a later census proved broken; pass 2 carries Alexandria Harbour's gate
   instead. Both passes are recorded because both touched the install.
2. **`world-mesh-trim --floor` was SKIPPED** in both passes, for opposite reasons — which is why it is
   worth recording as a general finding rather than a footnote. The trim drops LOW UP-FACING faces (a
   building's dirt apron), and neither donor has an apron to drop:
   * the pass-1 post is 6.387 u tall, so at the default `base_height=6.0` its single up-facing face
     (the top cap) survived by just **0.387 u** — and is **decapitated at 6.5**;
   * the pass-2 harbour gate is only **5.531 u** tall, i.e. entirely *below* the default 6.0 threshold,
     so the trim would drop **all 34** of its up-facing faces and gut the structure.

   Lesson: `--floor` is calibrated for a tall building. On a SHORT landmark it is not a no-op, it is
   destructive — check the height against `base_height` before running it.
3. **`quay_marker.obj` is NOT committed** — it is a verbatim copy of stock FF9 mesh geometry
   (312 verts + UVs + normals from p0data), the same class as the battle-map FBX in
   `ff9mapkit/docs/PROVENANCE.md`: read from your own install, gitignored, never committed. The study's
   `.gitignore` now excludes `*.obj` with that reason, and `mint_quay_marker.py` regenerates it.
   (The task brief had listed the OBJ as a repo file; committing it would have breached the provenance
   gate, so the generator is committed in its place.)
4. `--seat` and `--keep-block` were omitted as planned (`--seat` samples pristine terrain and block
   (0,18) has none; `--keep-block` is a no-op against a stub). The base is pre-translated to y 3.00 in
   the OBJ because `--at` shifts XZ only.

## 9.10 Working files added (repo side)

| Path | Note |
|---|---|
| `studies/overworld-topography/southern-ring/mint_quay_marker.py` | the authoring + build script — the full decided design as executable constants, with 11 offline gates (whole-part carry, anchor identity, base y, in-block, UV carry ×3, normal-Y fidelity, both exclusions). `--build` writes the install |
| `studies/overworld-topography/southern-ring/quay_marker.obj` | the generated OBJ, 31387 B — **gitignored** (provenance, §9.9) |
| `studies/overworld-topography/southern-ring/probe_marker/probe_quay_marker.py` | the acceptance probe (reads the DEPLOYED bytes, both discs; exits non-zero on any failure) |
| `studies/overworld-topography/southern-ring/probe_marker/probe_output.txt` | its output — all checks pass |
| `studies/overworld-topography/southern-ring/probe_marker/probe_before.txt` | the pre-mint state, probed from the backups |
| `studies/overworld-topography/southern-ring/probe_marker/writeset_md5_diff.txt` | whole-folder md5 before/after — the 2-file write-set proof |

Two untracked research-round paths sit in this worktree but are **not** part of this commit (they were
written by the census agents, not this pass): `studies/overworld-topography/object-census/` and
`studies/overworld-topography/WORLD-SCRIPTED-OBJECT-LANE-2026-07-25.md`.

## 9.10a Test state (honest)

`py -m pytest` in `ff9mapkit/`, **after** `extract-templates` (the fresh-worktree template trap — the
first run warned "base templates not extracted" and would have silently skipped the byte-level slice):

**5286 passed, 10 skipped, 1 failed in 7m39s.** The one failure is
`tests/test_world_nameplate_surgery.py::test_author_entrance_surgery_summary`:
`dispatcher case 53 is already mapped (target 4642) to a different handler`.

**It is PRE-EXISTING and unrelated** — verified by `git stash`ing this pass's changes and re-running:
it fails identically on a clean tree (1 failed, 10 passed). The test reads the LIVE world dispatcher,
and R1 (§3b) legitimately occupies case 53 with the Lantern Quay handler, so the test now collides with
the install state it reads. Nothing in this pass touches `world/entrance.py` or any dispatcher byte.
Worth fixing separately: the test should use a synthetic dispatcher or a dead case, not the live one.

## 9.11 Playtest ask (owner)

No relaunch needed — re-enter the overworld (or `~ → World` teleport near the junction island's west
shore). Expect **Alexandria Harbour's gate** standing just north of the quay tile, on the trigger's
own x axis. Confirm:

1. it **renders**, and renders **textured** — not flat white (white = the UV carry failed) and not
   missing (missing = the s34 Object override didn't bind on this reclaimed cell);
2. it reads as a marker at the overworld camera's scale — 6.3 × 8.4 u footprint, 5.5 u tall, its south
   face 2.8 u from the trigger. Sizing/offset is the most likely thing to want tuning;
3. you can **walk through it** (the 4078 stamp) — and specifically that walking onto the quay tile
   still works from every direction;
4. the quay entrance still fires and the "Lantern Quay" plate still appears (the shadowing test);
5. arriving from the berth still lands you on the west shore with nothing underfoot;
6. nothing looks wrong at the block seam 0.8 u north of the gate, where block (0,17) begins.

The gate's base sits at y 3.00 on flat ground; in stock it stood at sea level with its foot in the
water, so if it reads as "floating" or "buried" the fix is a y nudge in `mint_quay_marker.py`'s
`BASE_Y`, not a re-carry.

**Commit:** this pass IS committed (the kit lever + study files + this section) — see the branch
`claude/lantern-quay-marker-5b076a`.

**⚠ SUPERSEDED by §10** — the harbour carry was playtested, REJECTED on design, and reverted. §9 is
kept for the engine findings (they all still hold and §10 depends on them), not as a live description
of the install.

---

# 10. THE LANTERN BEACON — the harbour carry REVERTED, replaced via the proven building layer — **APPLIED**

Run 2026-07-25 (sixth pass), same worktree/branch. Backup timestamp: **`20260725-230801`**.

## 10.1 The playtest verdict that forced the redo

§9's harbour carry worked FUNCTIONALLY — nameplate, action prompt, entry all fired, and it rendered
textured. It was rejected on **design**:

1. **Z-fighting** — the donor embeds water-plane quads under its arch, and its base sat coplanar with
   the y = 3.00 plateau.
2. **Back-face culling** — the donor's single-sided walls vanish when viewed from behind.
3. The owner's verdict: *"a harbor sitting on land is obviously wrong, patching it is pointless."*

So the carry was not patched. It was reverted and replaced.

## 10.2 What we had missed: the building layer was already proven

`world-entrance --building` (★ in-game proven 2026-07-01, a Blender castle at an entrance;
`ff9mapkit/docs/OVERWORLD_ENGINE.md:405-427`) exists precisely for this, and its four laws answer all
three playtest failures:

| law | what it fixes |
|---|---|
| the building mesh is **RENDER-ONLY**, never fed to `AddWalkMeshForm1` | no invisible collision from culled walls / buried base |
| **collision = the TERRAIN under the hull, stamped topo 59** via `split_retarget_by_polygon` | conforms to the ground; UV-only, zero render effect |
| **SEAT, don't flatten** — the skirt hides the float | also the anti-z-fight measure at the base |
| **place by bbox CENTRE**, not vertex centroid | an asymmetric model doesn't bulge off-cell |

## 10.3 ⚠ THE LAW IS CONDITIONAL — and on THIS cell it does not hold by itself

**The single most important finding of this pass.** "Render-only" is only automatic on a **BARE**
block, where `WMWorld.RegisterBareObjectOverride` creates the Object component with
`AddForm1Transform` and *no* `AddWalkMeshForm1`. The s34 dispatch is:

```
if (prefab.ObjectForm1)   RegisterBlockComponent(block, prefab.ObjectForm1,  true, false);  // -> AddWalkMeshForm1
if (prefab.TerrainForm1)  RegisterBlockComponent(block, prefab.TerrainForm1, true, false);
if (!prefab.ObjectForm1 && prefab.TerrainForm1) RegisterBareObjectOverride(...);            // render-only
```

Block (0,18) is a **reclaimed** cell whose `Donor.txt` names donor **(0,0)** — and (0,0) **has** a
stock Object component (5 tris). So the override takes the `RegisterBlockComponent` path, **is** fed to
the Form1 walkmesh (`WMWorld.cs:775-814`), and is registered **before** `TerrainForm1`, so it also wins
the first-mesh ground query. A plain `--topograph 59` building here would have become invisible
collision *and* shadowed the quay trigger — the exact bug §9 diagnosed.

**Fix:** stamp the Object mesh **IDALL 4078** (`0x0FEE`), the `WMPhysics.Raycast` skip id, so it is
genuinely render-only; footprint collision comes from the topo-59 terrain hull as designed. Both halves
are *measured on the deployed bytes* in §10.8, not assumed. This needed a new kit lever (§10.9).

The same trap applies to any building placed on a real town block or any reclaimed/`Donor.txt` cell —
which is most interesting places to put one.

## 10.4 The asset — an authored beacon, not a carry

`studies/overworld-topography/southern-ring/quay_beacon.obj`, generated by `mint_quay_beacon.py`.
**Original procedural geometry, so both the generator AND the OBJ are committed** (unlike §9's
SE-derived carry, which had to stay gitignored).

* a stacked-ring prismatoid: buried plinth → 4-band tapered stone shaft → gallery ledge → 2-band
  lantern room → pyramid roof. **222 tris / 113 unwelded verts**, footprint **4.60 × 4.60 u**, height
  **10.60 u** above ground (harbour gate 5.5u reads small; Alexandria castle 16.8u).
* **CLOSED and ORIENTABLE, proven not hoped**: every undirected edge used by exactly 2 faces, every
  *directed* edge exactly once, signed volume **+126.735 u³** > 0 ⇒ every face outward. That is the
  anti-back-face-culling guarantee. The winding is *derived* from the ring topology
  (`L[i]→U[i]→U[j]→L[j]`, which yields outward walls, up-facing lips and down-facing overhangs from one
  rule) rather than flipped per face — per-face guessing is what breaks global orientability.
* **no face coplanar with y = 3.00**, and the plinth skirt runs to y = 2.50 (**0.5 u buried**), so the
  bottom cap is underground. Both §9 z-fight causes are designed out.
* 8-point rings (square + edge midpoints) and 4 shaft bands keep every panel ≤ 5.29 u² (~2.3 × 1.4 u),
  near the ~1–2 u real-tile scale — the atlas stamp does not rescale, so a big face smears one tile.
* **UVs are authored per panel** against the shared `res(1_24)_objects` atlas: a stone tile
  (u 0.0041–0.0350, v 0.3508–0.3816) on the shaft/plinth/gallery/roof and a **warm tile**
  (u 0.3342–0.3611, v 0.4357–0.4568) on the 32-tri lantern room, each rect inset one 4096-texel to stop
  seam bleed. Only *coordinates* live in the repo, never atlas pixels. Mapping is per QUAD, so each
  panel shows one full tile with no diagonal half-cut.
* 20 offline gates run on every generate; a textured 4-view render (including from *behind*) is archived
  at `probe_marker/beacon_textured.png`.

Thematic intent: all four ring quays get this same beacon, so the silhouette becomes the ring's shared
"you can dock here" vocabulary. The generator is the reusable source.

## 10.5 Placement

`--building-at 48 -1157 --no-seat` → world span **x[45.70, 51.30... ] → x[45.70, 50.30] z[−1159.30, −1154.70]**,
base y 3.00 (skirt to 2.50). `--at` anchors the XZ **bbox centre** (`blendio.py:198-203`) and shifts XZ
only. `--no-seat` is deliberate: seating puts the mesh's *lowest* point on the ground, which would
un-bury the skirt and bring the coplanar bottom cap back.

Clearances (measured): **2.807 u** from the nearest real trigger tile, **11.17 u** from the arrive point,
**0.807 u** inside the block's north edge. The arrive→trigger corridor runs along z = −1168, entirely
south of the beacon.

## 10.6 Backups taken BEFORE writing

| Backup | Covers |
|---|---|
| `backups/quay-beacon-prebuild.20260725-230801/Disc{1,4}-r18/Block[0][18] Terrain.ff9mesh` | 35900 B each — the R1 terrain (event tiles, no hull) |
| `backups/quay-beacon-prebuild.20260725-230801/Disc{1,4}-r18/Block[0][18] Object.ff9mesh` | 176 B each — the blanking stub |
| `backups/quay-beacon-prebuild.20260725-230801/text68/{us,uk,fr,gr,it,es,jp}.68.mes` | the nameplate text block, in case the surgery step rewrote it |

Step 1 of this pass **restored §9's harbour** from `backups/quay-marker-premint.20260725-212836` first
(md5 `e4a62c30…`, 176 B, both discs) and confirmed the whole `FF9CustomMap-world` tree was then
**byte-identical to the pre-marker baseline** — required, because the building layer *stacks* on the
deployed override.

## 10.7 What was written — EXACTLY 4 files

| # | File | Before | After |
|---|---|---|---|
| 1 | `…/WorldMap/Disc1/0_1/r18/Block[0][18] Terrain.ff9mesh` | 35900 B | **39956 B** |
| 2 | `…/WorldMap/Disc4/0_1/r18/Block[0][18] Terrain.ff9mesh` | 35900 B | **39956 B** |
| 3 | `…/WorldMap/Disc1/0_1/r18/Block[0][18] Object.ff9mesh` | 176 B | **34652 B** |
| 4 | `…/WorldMap/Disc4/0_1/r18/Block[0][18] Object.ff9mesh` | 176 B | **34652 B** |

Terrain md5 `2d052e3f5b854746d0a7bf2517bafc41`, Object md5 `8314ab9f28bdb83b60ab06e95ec429e9` — identical
across discs. **891 files before and after; none added or removed.** Proof:
`probe_marker/writeset_md5_diff_pass3.txt`.

**This pass writes TERRAIN bytes — a first for this marker arc.** The terrain grew 230 → **256 tris**
(690 → 768 verts) because `split_retarget_by_polygon` **retriangulates**: it splits every triangle that
straddles the hull boundary so the blocked edge traces the footprint exactly. The *surface* is
unchanged (a split triangle is coplanar with its parent) — only topology and idall.

**Dispatchers: ZERO files written.** All 9 (`world00/02/03/05/07/08/09/10/11` × 7 langs) reported
`skipped (cell already has an entrance there)`. Dry-run evidence: `probe_marker/dryrun_pass3.txt`.

**The 7 nameplate `68.mes` files were rewritten by the surgery step but are byte-IDENTICAL to their
backups** (they do not appear in the md5 diff) — R1 had already deployed that exact content.

⚠ **Two traps found while choosing the invocation, both avoided:**
* Passing `--field-direct` **without** `--nameplate-name` does **NOT** skip — the dry run planned to
  write **all 9 dispatchers, +50 B each**. The skip is keyed on the surgery handler, not the cell alone.
  The full R1 form is the only safe invocation.
* Omitting `--no-tile-area` would have re-stamped the 6 trigger tiles from idall 16384 (area 0, as R1
  deployed them) to area 53. R1's report records `tile_area_stamped: false`; the flag is required to
  reproduce it.

## 10.8 Verified from the DEPLOYED bytes, both discs (offline — the game was NOT launched)

`probe_marker/probe_quay_beacon.py` → `probe_marker/probe_output_pass3.txt`. **ALL CHECKS PASS on disc 1
and disc 4.**

* **(a) trigger intact** — 6 event tris, all idall **16384** (event 1, area 0 — `--no-tile-area` held),
  union bbox x[44.00, 52.00] z[−1172.00, −1164.00] unmoved; (48,−1168) → idall 16384 @ y 3.00.
* **(b) arrival intact + the approach survives** — (60,−1168) → Terrain, idall 0, topo 0, y 3.00 in
  **both** query modes; **all 25 sampled steps** of the arrival→trigger path are walkable topographs,
  and so is a **±6 u corridor** around it. The hull did not wall the player off from the entrance.
* **(c) the beacon is render-only, collision is in the TERRAIN** — 222 tris / 666 verts, **every tri
  idall 4078**; span matches plan to ≤0.01 u; skirt at y 2.50 (buried). Measured behavioural pair: the
  **walk query passes through** the beacon to Terrain, while a **sky-cast hits `Object` idall 4078** —
  proving the mesh really *is* in the walkmesh set, so the 4078 stamp is load-bearing, not decorative.
* **the exact TERRAIN idall delta — 12 tiles, all `idall 0 → 236` (topo 0 → 59)**, matched by centroid
  across the retriangulation (indices aren't comparable before/after):

  | tri | centroid (x, z) | x range | z range |
  |---|---|---|---|
  | 48 | (48.77, −1155.13) | 48.0–50.3 | −1156.0…−1154.7 |
  | 49 | (49.53, −1155.57) | 48.0–50.3 | −1156.0…−1154.7 |
  | 62 | (47.23, −1157.10) | 45.7–48.0 | −1159.3…−1156.0 |
  | 63 | (47.00, −1158.20) | 45.7–48.0 | −1159.3…−1156.0 |
  | 64 | (46.23, −1157.67) | 45.7–47.3 | −1159.3…−1156.0 |
  | 72 | (46.80, −1155.13) | 45.7–48.0 | −1156.0…−1154.7 |
  | 73 | (46.47, −1155.57) | 45.7–48.0 | −1156.0…−1154.7 |
  | 104 | (47.57, −1155.13) | 46.7–48.0 | −1156.0…−1154.7 |
  | 111 | (49.53, −1156.77) | 48.0–50.3 | −1158.3…−1156.0 |
  | 165 | (48.77, −1157.87) | 48.0–50.3 | −1159.3…−1156.0 |
  | 166 | (49.53, −1158.97) | 48.0–50.3 | −1159.3…−1158.3 |
  | 194 | (46.23, −1158.77) | 45.7–47.3 | −1159.3…−1157.7 |

  Gated: every changed tile became topo 59; **no event tile was overwritten**; every changed tile lies
  **inside the beacon footprint**; **none overlaps the trigger rect**. Block total topo-59 tris: 12
  (i.e. the hull is the *only* impassable geometry in the cell).
* **(d) UVs valid** — one per vertex, none degenerate, all inside [0,1], **both** authored tiles present
  (570 stone corners + 96 lantern corners).
* **(e) disc parity** — Terrain and Object byte-identical between Disc1 and Disc4.

## 10.9 Kit changes (repo side)

| File | Change |
|---|---|
| `ff9mapkit/ff9mapkit/cli.py` | **`world-entrance --building-idall N`** (0–65535, validated) — stamp a raw IDALL on the building mesh instead of encoding `--topograph`. Help text states *why* (the conditional render-only law of §10.3) |
| `ff9mapkit/ff9mapkit/world/entrance.py` | `building["idall"]` plumbed to `build_from_obj`; reported in the dry-run summary; `author_entrance`'s docstring now carries **THE RENDER-ONLY LAW IS CONDITIONAL** with the `WMWorld.cs:775-814` citation — the law was previously only true for bare blocks and nothing said so |
| `ff9mapkit/ff9mapkit/cli.py` | **receipt honesty fix**: the event-tile line printed `area=<case>` unconditionally, so `--no-tile-area` runs *claimed* to have stamped an area they deliberately left alone. Now prints `area=KEPT (--no-tile-area)`, backed by a new `tile_area_stamped` summary key |
| `ff9mapkit/tests/test_world_mesh_deploy.py` | +1 test: the raw idall **survives the `keep_block=True` merge** (`world-entrance --building` defaults to merge, and `place_building` is called with no `set_idall`, so the appended mesh must carry 4078 in its own tangents or a building beside a stock town silently becomes collision again) |

## 10.10 Undo

```sh
G="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
B="backups/quay-beacon-prebuild.20260725-230801"
for D in 1 4; do
  cp "$B/Disc$D-r18/Block[0][18] Terrain.ff9mesh" "$G/FF9CustomMap-world/FF9_Data/WorldMap/Disc$D/0_1/r18/"
  cp "$B/Disc$D-r18/Block[0][18] Object.ff9mesh"  "$G/FF9CustomMap-world/FF9_Data/WorldMap/Disc$D/0_1/r18/"
done
```

Re-enter the overworld (no relaunch). That restores the R1 state exactly: quay trigger working, no
marker, no hull. The nameplate/dispatchers were never modified, so there is nothing else to undo.
To go back further, follow §3.

## 10.11 ⚠ STANDING TRAP — now BOTH halves must be restored

`ff9mapkit/ff9mapkit/world/island.py` (`HIDDEN_PARTS` at `:53`, deployed at `:955-957` and `:966-969`)
unconditionally re-deploys the 176-byte Object blanking stub, and a `world-island` / `world-reclaim`
re-run also rewrites the cell's TERRAIN from scratch. **Since this pass the marker is TWO things:**

* the beacon **Object** mesh → wiped by the stub re-deploy;
* the topo-59 **collision hull** *and* the 6 **event tiles**, both living in TERRAIN idall bits → wiped
  by a terrain re-deploy.

**One script restores both:** `studies/overworld-topography/southern-ring/rebuild_quay_marker.sh`
(regenerates the OBJ, re-runs the exact `world-entrance` invocation, prints the verify command). It is
idempotent — dispatchers skip, tiles re-stamp identically, the beacon replaces whatever is there.

## 10.12 Working files (repo side)

| Path | Note |
|---|---|
| `mint_quay_beacon.py` | the beacon generator — profile as data + 20 gates. **Committed** |
| `quay_beacon.obj` | the generated mesh, 17061 B — **COMMITTED** (original geometry; contrast §9.9's carry) |
| `rebuild_quay_marker.sh` | the one-command re-deploy for the §10.11 trap; also the canonical record of the deploy arguments |
| `probe_marker/probe_quay_beacon.py` | the pass-3 acceptance probe (exits non-zero on any failure) |
| `probe_marker/probe_output_pass3.txt` | its output — all checks pass, both discs |
| `probe_marker/dryrun_pass3.txt` | the dry-run: **0 dispatcher writes, all 9 skipped** |
| `probe_marker/writeset_md5_diff_pass3.txt` | whole-folder md5 before/after — the 4-file write-set proof |
| `probe_marker/beacon_textured.png` | 4-view textured render (incl. from behind) sampling the real atlas |
| `mint_quay_marker.py`, `probe_quay_beacon`'s §9 siblings | §9's harbour tooling, kept: the engine findings still stand and the `--idall` lever came from it |

`.gitignore` note: the study ignores `*.obj`, so `quay_beacon.obj` is committed with an explicit
`!quay_beacon.obj` un-ignore — the rule exists to block *game-derived* geometry, and this mesh is ours.

## 10.13 Playtest ask (owner)

No relaunch needed — re-enter the overworld (or `~ → World` teleport to the junction island's west
shore). Expect a **stone lighthouse-style beacon with a warm-lit lantern room**, standing ~12 u north
of the quay tile on its axis. Confirm:

1. it renders, **textured** (white = the UV carry failed) and **solid from every angle** — walk a full
   circle around it; the §9 rejection was partly "walls vanish from behind";
2. **no z-fighting** at the base — the skirt is 0.5 u buried, nothing coplanar with the ground;
3. it reads at the right scale (4.6 u footprint, 10.6 u tall) and the warm lantern room is legible;
4. you **stop at its edge** (topo-59 hull) rather than walking into it — and you are never *stuck*:
   the footprint is only 12 tiles and the arrive point is 11 u away;
5. the quay entrance still fires and the "Lantern Quay" plate still appears (the shadowing test);
6. arriving from the berth still lands you on the west shore, and walking arrival → quay is unobstructed.

If the silhouette or siting wants tuning, `PROFILE` / `ANCHOR` in `mint_quay_beacon.py` are the dials;
re-run `rebuild_quay_marker.sh`.

**⚠ The ANCHOR in §10 is SUPERSEDED by §11** — the beacon itself was accepted; only its siting moved.

---

# 11. PASS 4 — THE TRIGGER-AT-THE-FOOT RE-SITE — **APPLIED**

Run 2026-07-25 (seventh pass), same worktree/branch. **No new backups were needed or taken** — this
pass restored from, and re-verified against, §10.6's `quay-beacon-prebuild.20260725-230801` set.

## 11.1 The defect

Pass 3's beacon was **accepted on look and feel** — it rendered correctly, was solid from every angle,
and had working collision. One defect: *"the entrance is heavily offset to the south."* The beacon sat
at z −1157 while the 6 trigger tris sit at z[−1172, −1164] — about **12 u apart**, so the "!" fired in
open grass with the tower standing off by itself. Stock's idiom, and our own waystation precedent
(*"the tower landmark…, 7 trigger tiles at its foot"*), puts the trigger **at the structure's foot**.

Nothing about the mesh changed. Only the anchor moved.

## 11.2 The new anchor, and why it is exactly here

Solved rather than guessed. The hull must stay ≥ 1.0 u clear of the trigger rect (below that, the
retriangulating split can reach a trigger tri), and the footprint half-width is 2.30 u:

```
south edge = cz − 2.30  ≥  −1164.0 + 1.0    ⇒    cz ≥ −1160.70
```

**`ANCHOR = (48.0, −1160.5)`** — 0.20 u of slack inside that bound. `cz = −1161.00` was computed and
**REJECTED** (0.70 u clearance). Resulting footprint:

| | pass 3 | **pass 4** |
|---|---|---|
| centre | (48, −1157.0) | **(48, −1160.5)** |
| span | x[45.70, 50.30] z[−1159.30, −1154.70] | **x[45.70, 50.30] z[−1162.80, −1158.20]** |
| gap to the trigger rect | 4.70 u | **1.20 u** |
| distance to the arrive point | 13.03 u | **11.006 u** (gate ≥ 6 u) |
| block north-edge margin | 2.70 u | **6.20 u** |

The siting constraints are now **gates in `mint_quay_beacon.py` itself** (overlap, ≥1 u clearance, a
`< 3 u` "close enough to read as at the foot" upper bound, arrive clearance, in-block) — a gate that
lives only in the probe is one the next re-site can forget. 25 gates now run on every generate.

## 11.3 ⚠ ORDERING — restore before re-running, or you orphan the old hull

The live install carried pass 3's hull: **12 terrain tris stamped topo 59 at the OLD anchor**. A naive
re-run would have stamped the new hull while those 12 stayed blocked — **invisible walls standing in
open grass** ~5 u north of the tower, with nothing rendered above them. The building layer *stacks* on
the deployed override; it does not clean up after itself.

So pass 4 **restored first**, and proved it:

* `Block[0][18] Terrain.ff9mesh` ← `quay-beacon-prebuild…/Disc{1,4}-r18/`, md5
  **`1225065193757d7a12efcb324ab05c07`** (35900 B);
* `Block[0][18] Object.ff9mesh` ← the 176 B stub, md5 **`e4a62c30d82899d19f86bdd6e19df0c9`**;
* then the **whole `FF9CustomMap-world` tree was confirmed byte-identical to the pre-pass-3 baseline**
  before a single byte of pass 4 was written.

Only then was the placement re-run with the new `--building-at`. The final probe *proves* the old hull
is gone (§11.5), rather than assuming the restore worked.

## 11.4 What was written — the same 4 files

Pure re-invocation: **no kit code changed in this pass.**

| # | File | Baseline | After pass 4 |
|---|---|---|---|
| 1–2 | `…/Disc{1,4}/0_1/r18/Block[0][18] Terrain.ff9mesh` | 35900 B | **40580 B** |
| 3–4 | `…/Disc{1,4}/0_1/r18/Block[0][18] Object.ff9mesh` | 176 B | **34652 B** |

Terrain md5 **`db6e94d780f5923bfc9eaefe6c2f0ce8`**, Object md5 **`4acc87aba56ab8e5e164cb790c94d92b`** —
identical across discs. **891 files before and after; none added or removed.** Terrain grew
230 → **260 tris** (690 → 780 verts) from the hull split — 4 more than pass 3, because the new footprint
straddles a different set of donor triangles. Proof:
`probe_marker/writeset_md5_diff_pass4.txt`.

**Dispatchers: 0 files written**, all 9 skipped (`probe_marker/dryrun_pass4.txt`). The 7 nameplate
`68.mes` files were rewritten and are again byte-identical to their backups.

## 11.5 The four hard gates — ALL PASS, both discs

`probe_marker/probe_quay_beacon.py` → `probe_marker/probe_output_pass4.txt` (59 PASS, 0 FAIL).

**Gate 1 — the hull never touches or SPLITS a trigger tri.** Presence is not enough: the split
retriangulates, so a hull that reached the cluster would fragment it into pieces that *still* carry
idall 16384 and *still* cover the same area — every naive check would pass while the cluster silently
became 8 or 10 tris of different shape. So the probe now compares **actual vertex triples** against the
pre-run mesh: **the 6 trigger tris are GEOMETRY-IDENTICAL**. Union bbox unmoved
(x[44.00, 52.00] z[−1172.00, −1164.00]); (48,−1168) → idall 16384 @ y 3.00; closest hull tile is
**+1.70 u** north of the trigger rect.

**Gate 2 — arrival intact.** (60,−1168) → Terrain, idall 0, topo 0, y 3.00 in **both** query modes;
**11.006 u** from the footprint (measured, not assumed).

**Gate 3 — the approach survives.** All 25 sampled steps of arrival→trigger are walkable topographs,
and so is the **±6 u corridor**. The tower is now directly north of the trigger, so this mattered more
than in pass 3: the footprint's x span [45.70, 50.30] lies **west** of the eastern approach samples
(x 52–60) and its z span is ≥ 5.20 u north of the z = −1168 path, so walking in from the east cannot
clip the hull.

**Gate 4 — disc parity.** Terrain and Object byte-identical between Disc1 and Disc4.

**Old-hull-cleared proof (the §11.3 hazard):** zero topo-59 tris anywhere in pass 3's footprint
(z[−1159.30, −1154.70]) outside the new hull; a 5-point spot-probe of the old anchor area reads walkable
again; and **the block's total topo-59 count (14) equals the number of tiles this pass changed (14)** —
so the new hull is the *only* impassable geometry in the cell, with nothing orphaned.

**The NEW hull — 14 tiles, all `idall 0 → 236` (topo 0 → 59):**

| tri | centroid (x, z) | x range | z range |
|---|---|---|---|
| 58 | (47.40, −1158.80) | 46.2–48.0 | −1160.0…−1158.2 |
| 61 | (48.77, −1161.70) | 48.0–50.3 | −1162.8…−1160.0 |
| 62 | (49.53, −1162.63) | 48.0–50.3 | −1162.8…−1162.3 |
| 78 | (46.07, −1162.43) | 45.7–46.8 | −1162.8…−1161.7 |
| 107 | (50.27, −1158.23) | 50.2–50.3 | −1158.3…−1158.2 |
| 152 | (49.53, −1160.77) | 48.0–50.3 | −1162.3…−1160.0 |
| 165 | (48.73, −1158.80) | 48.0–50.2 | −1160.0…−1158.2 |
| 166 | (49.50, −1158.83) | 48.0–50.3 | −1160.0…−1158.2 |
| 167 | (49.53, −1159.43) | 48.0–50.3 | −1160.0…−1158.3 |
| 180 | (47.23, −1160.93) | 45.7–48.0 | −1162.8…−1160.0 |
| 181 | (46.83, −1161.87) | 45.7–48.0 | −1162.8…−1160.0 |
| 182 | (46.07, −1161.50) | 45.7–46.8 | −1162.8…−1160.0 |
| 198 | (46.63, −1158.80) | 45.7–48.0 | −1160.0…−1158.2 |
| 199 | (46.47, −1159.40) | 45.7–48.0 | −1160.0…−1158.2 |

Render-only re-confirmed at the **new** centre: the walk query passes through the mesh to the topo-59
hull (`Terrain idall 236`), while a sky-cast hits `Object idall 4078`.

## 11.6 A probe bug this pass caught — worth keeping in mind

The render-only test was hard-coded to (48, −1157) — pass 3's anchor. After the re-site that is open
grass, so its "the walk query reaches Terrain" half **passed for the wrong reason: nothing was there at
all.** Only the *paired* assertion ("a sky-cast DOES hit the Object") failed and exposed it. The probe
now derives the sample point from `BEACON_SPAN` and additionally asserts the walk query lands on
**topo 59**, so a miss can't masquerade as a pass. **Keep both halves of a positive/negative pair** —
a one-sided liveness check on a moved target is worthless.

## 11.7 Undo

Identical to §10.10 (the same backup set restores the pre-marker state):

```sh
G="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
B="backups/quay-beacon-prebuild.20260725-230801"
for D in 1 4; do
  cp "$B/Disc$D-r18/Block[0][18] Terrain.ff9mesh" "$G/FF9CustomMap-world/FF9_Data/WorldMap/Disc$D/0_1/r18/"
  cp "$B/Disc$D-r18/Block[0][18] Object.ff9mesh"  "$G/FF9CustomMap-world/FF9_Data/WorldMap/Disc$D/0_1/r18/"
done
```

Re-enter the overworld (no relaunch). Nothing else was modified.

## 11.8 Files updated

| Path | Change |
|---|---|
| `mint_quay_beacon.py` | `ANCHOR` → (48, −1160.5) with the derivation in a comment; **+5 siting gates** (trigger overlap / ≥1 u clearance / <3 u "at the foot" / arrive clearance / in-block) |
| `quay_beacon.obj` | regenerated at the new anchor (same 222 tris / 113 verts / 666 UVs — a pure translation) |
| `rebuild_quay_marker.sh` | recorded anchor → `--building-at 48 -1160.5`, **with the −1160.70 southern limit documented** so a future clobber-rebuild can't drift into the trigger |
| `probe_marker/probe_quay_beacon.py` | new `BEACON_SPAN`; +trigger-geometry-identity gate; +old-hull-cleared gate; +hull-clearance gate; the §11.6 fix |
| `probe_marker/probe_output_pass4.txt`, `dryrun_pass4.txt`, `writeset_md5_diff_pass4.txt`, `plan_pass4.png` | pass-4 evidence (the plan view shows trigger, hull, footprint, arrival + path in one image) |

## 11.9 Playtest ask (owner)

No relaunch — re-enter the overworld. Expect the beacon **immediately north of the quay tile, at its
foot** (1.2 u between the tower's south face and the trigger's north edge). Confirm:

1. the "!" now fires **at the tower's foot**, not in open grass;
2. you can still reach the trigger walking in **from the east** — the tower is north of it, and its
   collision hull starts 1.2 u north of the tile;
3. nothing invisible remains ~5 u north of the tower where pass 3's hull used to be (walk through it);
4. entry still works and the "Lantern Quay" plate still appears.

**⚠ §11's ANCHOR is superseded by §12** (−1160.5 → −1160.2), which is **not deployed yet**.

---

# 12. PASS 5 — THE ENTRANCE-FACE DOOR — **REPO ONLY, NOT DEPLOYED**

Run 2026-07-26, same worktree/branch, as R2 phase 1. **ZERO install writes. Zero backups needed.
The live install is still pass 4's beacon** — the door rolls out to all four quays in the R2
placement pass, once the scout returns the three new dock coords.

## 12.1 The defect

Owner, after the pass-4 playtest: *"most buildings have some obvious entrance feature; ours does not,
making the entrance seem offset."* Pass 4 put the trigger at the tower's foot, but the tower was a
blank stone box on every side, so nothing told the player **which** side was the way in — the entrance
still read as arbitrary.

## 12.2 What changed in the generator

Everything is in `mint_quay_beacon.py`; the tower body is untouched.

* **The plinth was raised, 1.30 → 2.90 u** (`PLINTH_H`), because a door needs somewhere to live. The
  four shaft bands re-space from ~1.4 u to ~1.0 u to keep the total height at 10.60 u — so the
  silhouette, footprint and legibility band are all unchanged.
* **A recessed doorway on the SOUTH face only** — the face the quay trigger sits at. 1.60 u wide,
  2.05 u tall, sunk 0.35 u into the wall, with a 0.40 u lintel band above it. **The asymmetry is the
  feature**: the other three faces are byte-for-byte the plain plinth they were, and a gate asserts it.
* **Two shallow steps** up to the threshold (0.20 u and 0.42 u treads, 1.20 u / 1.00 u half-widths),
  each its own closed box, projecting 0.45 u south.
* **A third atlas tile** for the recess, `TILE_DOOR`. Chosen **by measurement, not by eye**: of 685
  candidate rects sampled from the object palette it has the lowest mean luminance (**2.2/255**) at a
  near-zero stddev (**0.9**) — i.e. the flattest, darkest panel on the atlas, which is what reads as an
  opening. Jambs, lintel underside, threshold and back face all take it; the steps take the shaft's
  stone tile.

## 12.3 How the recess stays CLOSED (the risky part)

An inset doorway adds interior faces, and a polygon-with-a-hole invites an ad-hoc triangulation that
quietly breaks the mesh. Two rules kept it manifold:

1. **The frame is a quad STRIP between two 6-vertex loops**, not a triangulated polygon-with-a-hole.
   The outer loop is *exactly* the boundary of the two south panels being replaced — **the same
   vertices, with no new points inserted on the shared edges**. That matters: adding a vertex mid-edge
   would leave the neighbouring strip's edge used once and mine used twice, i.e. a T-junction, and the
   closedness gate would fail. The inner loop traces the opening with the same 6-fold structure, so the
   annulus is a plain strip and its winding follows the **same derived rule as every other strip**.
   Extruding the inner loop inward and capping it closes the cavity.
2. **No hand-flipping, anywhere.** The recess side walls and the step boxes reuse the pass-3 winding
   derivation (`L[i]→U[i]→U[j]→L[j]`, plus t-order bottom fans and reversed-order top fans). The step
   boxes are built through that same machinery rather than as 12 hand-written triangles.

Separate components are fine: the gates check every edge has exactly 2 faces and every *directed* edge
exactly one, which holds per component, and the signed volumes add.

**A real bug this caught.** The first recess back-face used a fan from one corner. The J loop is a
rectangle carrying collinear mid-points on its top and bottom edges, so a fan from *any* corner emits
one **zero-area sliver** along the edge its apex sits on. The existing "no degenerate triangles" gate
missed it completely — it only tests for a *repeated vertex*, and this triangle had three distinct
ones. Fixed by triangulating the cap as a 2-quad strip, **and by adding a real area gate**
(`min area > 1e-6`) so the next collinear triangle cannot slip through.

## 12.4 ⚠ THE SOUTHERN LIMIT WAS RE-SOLVED — the anchor moved 0.30 u north

The hull is the mesh's **full XZ extent**, so the steps count:

```
pass 4 (no steps):     south edge = cz − 2.30           ≥ −1163.0  ⇒  cz ≥ −1160.70   (used −1160.5)
pass 5 (+0.45 steps):  south edge = cz − (2.30 + 0.45)  ≥ −1163.0  ⇒  cz ≥ −1160.25   (uses −1160.2)
```

**`ANCHOR = (48.0, −1160.2)`**, 0.05 u of slack. The structure still gets **closer** to the trigger than
pass 4: its southern extent is now the bottom step at **z −1162.95** versus pass 4's bare plinth face at
−1162.80, so the door faces the trigger across a **1.05 u** gap. Arrival clearance **10.936 u**
(gate ≥ 6), block north margin 5.90 u.

**Do not site south of −1160.25 while the steps exist.** `rebuild_quay_marker.sh` now records the new
anchor *and* both derivations, so a future `island.py`-clobber rebuild cannot drift into the trigger.

## 12.5 Gate results — 29 checks, ALL PASS

| | |
|---|---|
| closed | every edge shared by exactly 2 faces — **0 bad** |
| orientable | every *directed* edge used exactly once — **0 bad** |
| outward | signed volume **+144.928 u³** > 0 ⇒ nothing culls from any angle |
| slivers | min face area **9.36e-02 u²** (the new gate) |
| ground plane | **0** faces coplanar with y = 3.00; skirt still buried 0.50 u |
| siting | 1.05 u off the trigger rect, `< 3 u` "at the foot", 10.936 u from arrival, inside the block |
| tiles | every UV in one of the 3 authored rects (222 stone / 32 lantern / 16 door tris); none degenerate; all in [0,1] |
| entrance face | frame on the south plane (16 faces), recess sunk behind it (4 faces), steps exactly 0.45 u south, **north face still at the plain plinth line** |

**Tri count 222 → 270 (+48):** door frame 12, recess walls 12, recess back 4, steps 24, minus the 4
replaced panel tris. Verts 113 → 141. The budget gate was raised 250 → 320 with that reasoning recorded.

## 12.6 Files

| Path | Change |
|---|---|
| `mint_quay_beacon.py` | plinth raised; `DOOR_*` / `STEP_*` / `TILE_DOOR` constants; the door surgery + `_box_solid`; anchor re-solve; +6 gates (sliver, 3-tile coverage, door tile, frame, recess, steps-project, north-face-untouched) |
| `quay_beacon.obj` | regenerated — 141 verts / 270 tris / 810 UVs, 41202 B |
| `probe_marker/beacon_textured.png` | re-rendered 4-view preview, **south face first**, sampling the real atlas |
| `rebuild_quay_marker.sh` | `--building-at 48 -1160.2` + both southern-limit derivations |
| `probe_marker/probe_quay_beacon.py` | `BEACON_TRIS/VERTS/SPAN` and `OLD_SPAN` advanced to the pass-5 mesh, with a header warning that **it will fail against the currently-live pass-4 beacon until R2 deploys** |

No kit code changed. World/mesh test set: **300 passed, 4 skipped**.

## 12.7 Rollout note for the R2 placement pass

Quay 1 (Lantern Quay) picks the door up on its rebuild alongside sites 2–4. The re-deploy is the
existing one-command script — and the §11.3 **restore-first** ordering still applies: pass 4's hull is
live, and the new footprint differs, so restore `quay-beacon-prebuild.20260725-230801`'s Terrain +
Object stub before re-running, or the old hull tiles orphan as invisible walls. `probe_quay_beacon.py`
is already primed with the pass-5 expectations and its old-hull-cleared gate points at pass 4's span.

---

# 13. R2 PHASE A0/A1 — the aux STOP, and the multi-site generator

> **WHY GRIMHORN SHIPS WITHOUT ITS FALLS — the closing word on the horseshoe aux.**
> The Daguerreo-horseshoe carry that once gave the Grimhorn bench its animated Falls / River /
> RiverJoint / Object ensemble (★ in-game proven 2026-07-15, closed over 3 rounds) **no longer exists in
> the deployed tree** — a later `world-island` / `world-reclaim` run over the bench span wiped it via the
> `HIDDEN_PARTS` stub trap (§10.11), leaving 176 B blanking stubs dated Jul 21 01:59 in its place.
> Restoring it is not a re-run: no runnable script or recorded command survives (README:346-351 is prose
> describing the *result*), so it would mean reconstructing a `world-mountain` invocation and rewriting
> terrain across a **10-block span** — through the very cell the Grimhorn quay now stands on.
> **A0 is formally DROPPED from R2 by owner ruling.** Grimhorn ships as a plain bench with a beacon.
> This paragraph is the record; do not re-litigate or re-cost it.

Run 2026-07-26. **ZERO install writes** (verified by whole-folder md5 against the pass-4/5 state).
Stopped at the A1/A2 boundary; A2 (the three new site deploys) and A3 (the Ashvale rebuild) are
dry-run-verified and ready but unwritten.

## 13.1 A0 — GRIMHORN AUX RE-DEPLOY: **STOPPED, severable by owner intent**

The directive allowed stopping if the aux restore turned out to be "more than a recorded re-run
(missing scripts, drifted state)". It is both:

* **The aux parts do not exist anywhere in the deployed tree.** A tree-wide search for `*Falls*` /
  `*River*` returns **nothing** — they were not stubbed, they were wiped. Every block in the bench span
  (18–21, 17–19) carries only the island-mint part set (`Beach1 / Donor / Object / Sea1-5 / Terrain`).
* **The Object files are island-mint blanking stubs dated Jul 21 01:59** — i.e. written by a LATER
  `world-island` / `world-reclaim` run than the mountain deploy. This is the same `HIDDEN_PARTS` trap
  recorded in §10.11, and it took the horseshoe's aux with it.
* **No runnable script or recorded command exists.** `studies/overworld-topography/README.md:346-351`
  is prose describing the *result* (r72 seed-42 bench at (1280,−1184), horseshoe at (1288,−1190) rot 0);
  the only grep hit for an invocation is a catalog row in `continent_layout.py`. Reconstructing it means
  re-running `world-mountain` across a 10-block span — a large terrain rewrite that would itself pass
  straight through the Grimhorn quay site.

**Consequence for R2 (good):** block (18,18)'s Object is a plain 176 B stub, so the Grimhorn beacon is
the same clean case as the other three — there is no aux to compose with and nothing to clobber.

## 13.2 A1 — the generator is now multi-site

`mint_quay_beacon.py` grew a `SITES` table (`Site` NamedTuple: anchor, ground_y, trigger rect, arrive
point + face, host block, cell, trigger_at). The geometry, the door and all 29 gates are unchanged and
run **per site** — a new quay is a row, not a fork. `--site <name>|all`; Ashvale keeps `quay_beacon.obj`
so the pass-4/5 history and deploy paths still resolve, the others get `quay_beacon_<site>.obj`.

`rebuild_quay_marker.sh <site>` now takes the site as an argument and carries the per-site deploy
arguments plus the shared southern-limit derivation.

**All four sites generate clean — 29/29 gates each, 270 tris / 141 verts / 810 UVs.**

| site | anchor | ground_y | hull→trigger | hull→arrive | arrive face |
|---|---|---|---|---|---|
| Ashvale | (48, −1160.2) | 3.00 | 1.05 u | 10.936 u | 192 (east) |
| Tidefall | (420, −1224.2) | 3.20 | 1.05 u | 10.936 u | 192 (east) |
| Grimhorn | (1204, −1184.2) | 3.20 | 1.05 u | 9.208 u | 192 (east) |
| Larkspur | (700, −608.2) | **3.03** | 1.05 u | 10.936 u | 64 (west) |

## 13.3 Contradictions with the plan-of-record (resolved, none blocking)

1. **Larkspur `GROUND_Y` is 3.03, NOT 3.15.** The plan said "GROUND_Y from probe (y 3.04..3.15)". The
   footprint has 0.116 u of relief (measured 3.037..3.154). Seating on the **max** keeps the skirt
   buried but leaves the plinth **floating 0.113 u over the low corner** — a visible gap with a shadow.
   Seating on the **min** buries the base 0.11 u into the high corner instead, which is invisible.
   **Sink, never float**; the rule is now a comment on the `SITES` table.
2. **`--no-tile-area` IS wanted at the new sites.** The directive said it was not, then said to match the
   live quay's tiles. Those are **idall 16384 = event 1 / area 0**, and `--no-tile-area` is exactly what
   keeps the area field at 0; omitting it stamps area 53 → idall 29952. Verified against the live block.
   The instruction's two halves conflicted; the *measurement* decided it.
3. **The kit lints both Tidefall and Grimhorn as "POOR SPOT"** (33 % / 23 % of the entrance cell is
   non-walkable) — a gate the scout's suite did not run. **Quantified and cleared, not waved through:**
   an 8-connected flood from each arrive point to its trigger, with the new topo-59 hull simulated, is
   **reachable at all three sites**, with a minimum corridor width of 13–14 of 17 sampled units and both
   endpoints walkable. The blocked fraction is coastline elsewhere in the 32 u cell, not the approach.

## 13.4 A2/A3 are dry-run-verified and ready

Each new site's dry run plans exactly what the directive predicted: **9 dispatchers × 7 langs = 63 `.eb`
files** (the trigger-func add), 6 event tris with `area=KEPT`, 16 hull tiles, and the beacon at the site
anchor. The case-53 repoint and the text-block-68 write are re-runs of already-live content (the repoint
is idempotent when the handler bytes match; block 68 was byte-identical on both prior passes) — to be
byte-confirmed per site on the real run.

**A3 still needs the §11.3 restore-first ordering**: Ashvale's live Object is the pass-4 beacon
(34652 B, 222 tris) and its hull sits at the pass-4 footprint, so restore
`quay-beacon-prebuild.20260725-230801`'s Terrain + Object stub before re-deploying, or the old hull
tiles orphan as invisible walls.

## 13.5 Files

| Path | Change |
|---|---|
| `mint_quay_beacon.py` | `Site`/`SITES` table + `--site`; `_ring`/`build_beacon`/`gates`/`write_obj` take the site; per-site OBJ path; the sink-never-float rule; docstring refreshed for multi-site |
| `quay_beacon.obj` | regenerated (unchanged content — Ashvale's anchor did not move) |
| `quay_beacon_{tidefall,grimhorn,larkspur}.obj` | **new**, 270 tris each |
| `rebuild_quay_marker.sh` | takes `<site>`; per-site args + the shared southern-limit derivation |

No kit code changed. World/mesh set: **300 passed, 4 skipped**.

---

# 14. R2 PHASE A2 + A3 — THE FOUR QUAYS ARE LIVE — **APPLIED**

Run 2026-07-26, same worktree/branch. Backup set: **`backups/r2-sweep.20260726-r2sweep/`**
(per-site Terrain+Object on both discs, the 7 text-block-68 `.mes`, and **all 63 world dispatchers**).
**No relaunch performed or required** — dispatcher `.eb` and world meshes hot-reload on world re-entry.

## 14.1 Write-set — 79 files, 891 before and after

| class | count | detail |
|---|---|---|
| world dispatchers | **63** | 9 dispatchers × 7 langs, **+99 B each = +3 functions** (the Tidefall, Grimhorn, Larkspur cell triggers) |
| world meshes | **16** | 4 sites × {Terrain, Object} × {Disc1, Disc4}; disc-identical per site |
| text block 68 | **0 changed** | rewritten by the surgery step, **byte-identical** to backup (verified all 7 langs, twice) |
| DictionaryPatch / field `.eb` / `FF9CustomMap` | **0** | untouched |

Proof: `probe_marker/writeset_md5_diff_pass6.txt`.

**Dispatcher integrity, proven by parsing rather than asserting:** both versions of all 63 files were
parsed with `EbScript` and their function bodies compared. **Every pre-existing body survives
byte-identical and in order**, with exactly +3 new functions each. The case-53 handler, the Ashvale
trigger and every stock function are untouched. (A byte-level "pure insertion" test *fails* here and
that is expected — the `.eb` header's offset table shifts too, and a new table entry is inserted. The
function-body comparison is the check that actually means something.)

| site | block | terrain tris | Object | trigger idall | hull tiles |
|---|---|---|---|---|---|
| Ashvale | (0,18) | 230 → 270 | 42140 B | 16384 (topo 0) | 16 |
| Tidefall | (6,19) | 293 → 333 | 42140 B | 16384 (topo 0) | 16 |
| Grimhorn | (18,18) | 209 → 249 | 42140 B | **16452 (topo 17)** | 16 |
| Larkspur | (10,9) | 566 → 606 | 42140 B | 16384 (topo 0) | 16 |

## 14.2 ⚠ THE BBOX-CENTRE DRIFT — caught on the first deploy, fixed at the source

`--building-at` re-anchors the mesh's **XZ BOUNDING-BOX CENTRE** (`blendio.py:198-203`), not its design
anchor. Until pass 5 the footprint was symmetric (±2.30), so the two coincided and passing the anchor
was an identity shift. **Pass 5's entrance steps project 0.45 u south, moving the bbox centre 0.225 u
south of the tower centre** — so passing the anchor slid the whole beacon **0.225 u NORTH of where all
29 gates had measured it**.

The first Tidefall deploy did exactly that; the probe's span check caught it (`z[-1226.73,-1221.68]`
against an expected `z[-1226.95,-1221.90]`). The clearance merely *improved*, so nothing was unsafe —
but the deployed mesh no longer matched the gated one, and that is how drift starts.

**Fixed at the source, not per call site:** `Site.building_at` now publishes the correct value
(`anchor_z + (DEEP_N − DEEP_S)/2`), the generator prints it after every build, and
`rebuild_quay_marker.sh` carries it with the derivation. Tidefall was **restored from backup and
re-deployed** with the corrected value before any other site was touched.

| site | anchor | `--building-at` |
|---|---|---|
| Ashvale | (48, −1160.2) | (48, **−1160.425**) |
| Tidefall | (420, −1224.2) | (420, **−1224.425**) |
| Grimhorn | (1204, −1184.2) | (1204, **−1184.425**) |
| Larkspur | (700, −608.2) | (700, **−608.425**) |

## 14.3 Verification — 160 checks, ALL PASS

`probe_marker/probe_quay_sites.py` (site-driven: expectations come from `mint_quay_beacon.SITES`, so
the probe cannot drift from the mesh it checks) → `probe_marker/probe_output_pass6.txt`. Per site, both
discs: trigger intact (6 tris, event 1 / area 0, bbox == the site rect, geometry-identical to the
pre-deploy mesh where one existed); arrive walkable in **both** query modes; beacon 270 tris / 810 verts
all idall 4078 with the walk query passing **through** to the topo-59 hull while a sky-cast hits the
Object; hull tiles enumerated, topo-59 only, inside the footprint, clear of the trigger, and the only
topo-59 geometry in the block; UVs valid; **Disc1/Disc4 byte-identical**.

**Two probe-expectation bugs found and fixed (not deploy bugs):**
1. **Grimhorn's trigger tiles read idall 16452, not 16384** — and that is CORRECT. `retarget_tiles`
   sets the event bit and (with `--no-tile-area`) leaves area alone, but it also **preserves each
   tile's own topograph**. Grimhorn's bench ground is topo 17; the other three sit on topo 0. The
   invariant is **event 1 / area 0**, never a raw idall equality — demanding 16384 everywhere would
   have condemned a correct deploy.
2. **Ashvale's delta baseline was the pass-4 state** (which already carried a hull), so the enumeration
   showed "16 blocked vs 1 stamped". The true pre-deploy baseline is the pass-3 backup that A3 restored
   from; corrected, and Ashvale's old hull is proven cleared by the same `n59 == len(hull)` gate.

## 14.4 A3 restore-first (the §11.3 ordering, honoured)

Ashvale's live Object was the pass-4 beacon with its hull at the pass-4 footprint. Restored from
`quay-beacon-prebuild.20260725-230801` (md5 `1225065193757d7a…` Terrain, `e4a62c30…` Object, verified
against the live files after copying) **before** deploying, so the old hull tiles could not orphan.
The probe's `n59 == len(hull)` gate confirms the block's only impassable geometry is the new hull.

## 14.5 Undo

Per site, restore its two meshes on both discs from the sweep backup; to remove the new entrances
entirely, also restore the 63 dispatchers:

```sh
G="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
B="backups/r2-sweep.20260726-r2sweep"
# meshes -- per site: ashvale 0 18 / tidefall 6 19 / grimhorn 18 18 / larkspur 10 9
for D in 1 4; do
  cp "$B/tidefall/Disc$D/Block[6][19] "*.ff9mesh "$G/FF9CustomMap-world/FF9_Data/WorldMap/Disc$D/0_1/r19/"
done
# all nine dispatchers, all seven langs (removes the three new triggers; Ashvale's stays)
cp -r "$B/dispatchers/." \
  "$G/FF9CustomMap-world/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world/"
```

⚠ Restoring the **Ashvale** meshes from this sweep's backup returns it to the **pass-4** beacon, not to
bare ground — the sweep snapshot was taken while pass 4 was live. For bare ground use
`quay-beacon-prebuild.20260725-230801` (§10.10).

Re-enter the overworld; no relaunch.

## 14.6 Standing trap, now ×4

`island.py`'s `HIDDEN_PARTS` re-stubs the Object part and a `world-island`/`world-reclaim` re-run
rewrites the terrain, so **each** quay is two things to restore. `rebuild_quay_marker.sh <site>` does
both for one site; run it per affected site.

## 14.7 Playtest ask (owner) — no relaunch

Re-enter the overworld (or `~ → World` teleport). All four quays should now be live:

| quay | trigger | beacon | arrive |
|---|---|---|---|
| Ashvale | (48, −1168) | (48, −1160.2) | (60, −1168) face 192 |
| Tidefall | (420, −1232) | (420, −1224.2) | (432, −1232) face 192 |
| Grimhorn | (1204, −1192) | (1204, −1184.2) | (1214, −1192) face 192 |
| Larkspur | (700, −616) | (700, −608.2) | (688, −616) **face 64 (west)** |

Confirm at each: the beacon renders textured with its dark doorway facing the trigger; the "!" fires at
the tower's foot; you can walk in from the arrive side without snagging; the "Lantern Quay" plate
appears. (All four currently share the case-53 name — per-berth naming is a B-phase concern.)
Larkspur's base is seated on the footprint **minimum** (0.116 u of relief there), so check it does not
read as sunk on the high side.

---

# 15. R2 PHASE B — THE BERTH ROW — **APPLIED** (hot; no relaunch)

Run 2026-07-26, same worktree/branch. Backups: **`backups/r2-sweep.20260726-r2sweep/field6601/`**
(all 7 `.eb`, all 7 `.mes`, and the pre-deploy `DictionaryPatch.txt`).

## 15.1 What the hall became

R1 shipped ONE berth door — field 2800's own exit region, a big quad across the hall's south end.
R2 replaces it with **four east-wall, depth-staggered alcoves**, one per ring island, so the saloon
reads as a ferry hall with a berth per destination.

| berth | gateway zone | sign zone | arrive | face |
|---|---|---|---|---|
| I Ashvale | x[80,205] z[−2790,−2610] | x[10,78], same z | (60, −1168) | 192 E |
| II Tidefall | x[80,205] z[−2440,−2260] | x[10,78], same z | (432, −1232) | 192 E |
| III Grimhorn | x[80,205] z[−2090,−1910] | x[10,78], same z | (1214, −1192) | 192 E |
| IV Larkspur | x[80,205] z[−1740,−1560] | x[10,78], same z | (688, −616) | **64 W** |

350 u of clear corridor between mouths, so you can never stand in two at once. Every arrive is the
quay's own gate-verified point — the same coords `mint_quay_beacon.SITES` gates the beacons against.

**The signs are `[[event]]` zones, not props.** A placard with a model would be an *actor* in a 410 u
corridor and would breach the ≥300 u spacing the probe enforces — in a shaft this narrow, any west-wall
actor lands 195–262 u from an east-wall sign and there is no arrangement that clears 300. A zone has no
collision and no footprint, so the sign costs nothing spatially. Each sits in the 68 u of corridor just
WEST of its mouth: you read the berth name on approach, then cross into the gateway.

Sign once-flags are **8760–8763**, explicitly set. The `[[event]]` default allocates from **8000**,
which is *below* `FIRST_SAFE_FLAG` = 8712 (`flags.py:46-48`) — the band CLAUDE.md flags as a live
save-corrupter. Never take the default here.

## 15.2 The Purser moved to the west wall — he was standing in a gateway

He stood at **(130, −1650)**, which the new layout turns into the **mouth of berth 4**: x 130 ∈ [80,205]
and z −1650 ∈ [−1740,−1560]. An actor inside a gateway zone is an instant warp the moment he is nudged.
Now at **(−130, −2400)** — 75 u off the west wall, facing the berth row across the hall, **420 u** from
the spawn and **950 u** from the ledger. His line is re-voiced to name the four berths and to point at
the ledger *up the hall* (it is now north of him, not west).

## 15.3 Layout probe — **WARNINGS: none**

`tools/field_layout_probe.py` → archived at `probe_marker/layout_pass7/`. Both PNGs read.

* Camera is the borrowed Daguerreo one: **pitch 2.5°, yaw −12.2°**, canvas 512×320. Yawed, so
  cardinals do not align with screen edges — the COMPASS table says world **north → up-right (66°)**,
  east → right, south → down-left. Narrate from that table, not from coordinates.
* `topdown.png`: the four gateway/sign pairs stack cleanly up the corridor's east side, all on the
  measured floor (x[−205,205] for z[−3400,−1000]); Purser opposite them on the west wall; ledger and
  spawn north and clear.
* `camview.png`: the berths recede up-screen as a staggered row — the depth-stagger reads exactly as
  intended at this near-level camera.
* Reachability: the player centre stops 48 u off the wall, so it enters each gateway across
  x ∈ [80, 157] — 77 u of usable depth per berth.

`ff9mapkit lint`: **0 errors**, 1 advisory (`entry_settle = "auto"` → 50 frames).

## 15.4 Write-set — 14 files, 891 before and after

| class | count | detail |
|---|---|---|
| `EVT_LANTERN_HALL.eb.bytes` | 7 | **3198 → 6962 B** (+3764) — four gateways + four sign events |
| `6601.mes` | 7 | sign text + the re-voiced purser line |
| everything else | **0** | zero world meshes, zero dispatchers, zero `FF9CustomMap` |

**The `DictionaryPatch` line SET is byte-identical** (`MessageFile`/`FieldScene 6601` were already
registered by R1), so despite `deploy_field`'s generic *"RELAUNCH to register"* notice, **no relaunch is
required** — `.eb`/`.mes` content hot-reloads. Proof: `probe_marker/writeset_md5_diff_pass7.txt`.

## 15.5 Verified from the DEPLOYED `.eb`, all 7 languages

Each language's shipped script was re-scanned for the exact byte blocks `worldexit.arrive_writes`
emits:

* **all four arrive blocks present, each exactly ONCE** (Ashvale / Tidefall / Grimhorn / Larkspur,
  with their own coords and face);
* **`D8:2 = 35` written 4×** — one preset key per berth (key 35 is the disc-correct bare-`WorldMap`
  idiom from §8);
* **`D8:2 = 62` written 0×** — the band-invariant key that caused the original 9009 fall-through
  never appears.

## 15.6 Undo

```sh
G="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
B="backups/r2-sweep.20260726-r2sweep/field6601"
for L in us uk fr gr it es jp; do
  cp "$B/$L.eb.bytes"  "$G/FF9CustomMap-world/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/$L/EVT_LANTERN_HALL.eb.bytes"
  cp "$B/$L.6601.mes"  "$G/FF9CustomMap-world/FF9_Data/EmbeddedAsset/text/$L/field/6601.mes"
done
```

Returns the hall to R1's single south-end berth door. **~ → Reload field** (no relaunch). To remove
6601 entirely: `py tools/scroll_out/revert_deploy_6601.py`.

## 15.7 Playtest ask (owner) — no relaunch, ~ → Reload field or re-enter

1. Four berth mouths along the **east** wall, staggered in depth; each announces its island as you
   approach (sign fires **once ever** per berth — the kit has no once-per-visit region yet).
2. Each berth lands you at its own quay: Ashvale (60,−1168) · Tidefall (432,−1232) · Grimhorn
   (1214,−1192) · **Larkspur (688,−616) facing WEST** — Larkspur is the one where inland is west.
3. Stepping out of a quay never instantly re-enters it (every arrive is ≥8 u off its trigger).
4. The Purser is on the **west** wall now and no longer standing in berth 4's doorway; his line names
   the four berths.
5. The ledger/save point still works and is reachable.

⚠ Known cosmetic gap: all four **overworld** quays still raise the same case-53 **"Lantern Quay"**
nameplate — per-quay naming needs three more dead AREA-switch cases and is not in this pass.

---

# 16. R2 PHASE D — WRAP-UP CROSS-CHECKS

Run 2026-07-26, immediately after §15. **Zero install writes** — verification only, plus one new
offline gate.

## 16.1 THE RING-CLOSURE CHECK (new)

The four berth arrives live in `lantern-hall.field.toml`; the four quay arrives live in
`mint_quay_beacon.SITES`. **They are the same four points written down in two files, and nothing tied
them together** — edit a quay's arrive without editing the hall (or the reverse) and the ring silently
half-breaks: you sail to a berth and land somewhere that is no longer beside its beacon. Offline, cheap,
and exactly the class of drift that only shows up in a playtest.

`probe_quay_sites.py` now parses the hall's `[[gateway]]` blocks and asserts each arrive **and face**
against `SITES`. Current state — **all four match**:

| berth | hall | quay table |
|---|---|---|
| Ashvale | (60, −1168) f192 | (60, −1168) f192 |
| Tidefall | (432, −1232) f192 | (432, −1232) f192 |
| Grimhorn | (1214, −1192) f192 | (1214, −1192) f192 |
| Larkspur | (688, −616) **f64** | (688, −616) **f64** |

## 16.2 Full-R2 install footprint — 93 files, 891 before and after

Re-measured end-to-end against the pre-A2 baseline, after every phase:

| class | count |
|---|---|
| world dispatchers (`EVT_WORLD_WORLDxx`, 9 × 7 langs) | 63 |
| world meshes (4 sites × Terrain/Object × 2 discs) | 16 |
| field 6601 `.eb` | 7 |
| field 6601 `.mes` | 7 |
| **total** | **93** |

No file added or removed. Zero `DictionaryPatch` content change, zero writes to `FF9CustomMap`.
**No relaunch was performed and none is required** for any of it.

## 16.3 Final verification state

* **`probe_quay_sites.py --backup-root backups/r2-sweep.20260726-r2sweep`: 162 checks, ALL PASS** —
  four sites × two discs, re-run *after* the 6601 deploy to confirm the field work regressed nothing,
  plus the new ring-closure section.
* **Deployed 6601 `.eb`, all 7 langs**: four `arrive_writes` blocks each exactly once, `D8:2 = 35` ×4,
  `D8:2 = 62` ×0.
* **Dispatchers**: every pre-existing function body byte-identical and in order, +3 functions each.
* **Layout probe**: zero warnings; both PNGs archived at `probe_marker/layout_pass7/`.
* **Tests**: world/mesh + worldexit + hub sets green (134 in the phase-B run; 310 in the A-phase run,
  with the one known pre-existing `test_world_nameplate_surgery` live-dispatcher failure).

## 16.4 What R2 did NOT do (open, deliberately)

* **Per-quay nameplates.** All four overworld quays raise the same case-53 *"Lantern Quay"* plate.
  Distinct names need three more dead high AREA-switch cases (49–59 band, avoiding 54–59/49/50) plus
  three more text-block-68 locId registrations. Cosmetic; flagged, not attempted.
* **The Grimhorn falls.** A0 dropped by owner ruling — see the §13 preamble. Not to be re-costed.
* **The ferry berth rows beyond four.** The design's Lamplight island (R3) and the forest pass (R4)
  are separate rungs.

---

# 17. R2 REDESIGN — **THE PURSER RUNS THE FERRY** — APPLIED (hot; no relaunch)

Run 2026-07-26. Backups: **`backups/r2-ferry.20260726/`** (all 7 `.eb`, all 7 `.mes`, pre-deploy
`DictionaryPatch.txt`).

## 17.1 Why the berth row was replaced, not tuned

Owner playtest of §15: *"everything is super clustered... I can't tell what I'm supposed to do. I can
randomly trigger 1 of 2 warps."* The causes are structural:

* the **spawn (0,−2000) sat inside berth III's z-band**, 10 u west of its sign zone;
* the **sign zones occupied the CENTRE** of a ±157 u walk band — you crossed them just walking up the hall;
* the **four warp zones ate the whole east half** of that band, so adjacent triggers were one nudge apart;
* and **the borrowed art paints nothing at any alcove** — an invisible door cannot be read.

Four unmarked, mutually-adjacent trigger zones in one corridor is not a layout problem with a tuning
fix; it is the wrong *mechanism* for borrowed art. Owner chose stock FF9's own boat-travel idiom.

## 17.2 The kit lane — `[[ferry]]` (productized, documented, tested)

A dialogue-CHOICE worldmap exit. **Talk to a person, pick a port.** Documented in
`ff9mapkit/docs/FORMAT.md` beside `[[choice]]`.

```toml
[[ferry]]
npc = "Purser"
prompt = "Where shall we sail, kupo?"
decline = "Not yet, kupo."                # REQUIRED
decline_reply = "Kupo! The ferry keeps her berth."

[[ferry.destination]]
name = "Ashvale"
arrive = [60.0, -1168.0]
arrive_face = 192
reply = "The Lantern Quay it is, kupo!"
```

**It desugars into an ordinary `[[choice]]`** (`build._desugar_ferries`, run in `FieldProject.load`)
whose destination rows carry a new `worldmap` action. That was deliberate: a ferry then inherits the
entire proven choice pipeline — the one-text-entry prompt+rows assembly (and with it the
**window-geometry law**, since the entry carries its own `[STRT]`/`[TAIL]`), CANCEL-picks-the-last-row,
the runtime availability mask, flag gating, and all 12 existing `raw["choice"]` consumers — instead of
growing a parallel implementation. A field with no `[[ferry]]` never gains a `choice` key, so existing
builds stay byte-identical.

The only new byte-level behaviour is the row action itself (`choice.option_body`'s `worldmap` arm),
which calls **`worldexit.worldmap_exit_body`** — the same primitive a walk-out gateway uses. So a ferry
row and a door behave identically once taken: usercontrol guard, fade, **both** position blocks,
`POSITION_PRESET_KEY` 35, computed `WorldMap`. The decline arm emits no transition at all.

**The decline arm is mandatory and appended LAST** because with no `[PCHC]` pre-tags the engine's
CANCEL (B) returns the last row — without it, a cancelled menu would sail you to the final destination.
Lint enforces it, along with at-least-one destination, a prompt, a real `[[npc]]` target, and
gateway-grade `arrive`/`arrive_face` validation. Errors are labelled `[[ferry]]`, pointing at what the
author wrote rather than at generated rows.

Existing worldmap-gateway restrictions were left untouched.

**Tests: `ff9mapkit/tests/test_ferry_lane.py`, 15 cases** — desugar shape and decline-last ordering,
`instant` default, the no-ferry no-op, six negative lint cases, and the byte contract (arrive block
verbatim, exactly one key-35 write, never key 62, per-destination coords differ, decline emits no
transition, `warp` and `worldmap` mutually exclusive).

## 17.3 The hall, redesigned

* **DELETED** all four `[[event]]` sign zones and all four berth `[[gateway]]`s. **Flags 8760-8763 are
  returned to the pool** — nothing references them (the probe asserts no `flag = 876x` assignment
  survives, and that no `[[event]]` remains).
* **RESTORED the R1-proven walk-on home door** — field 2800's own real exit region, the quad
  `[[201,-3377],[-193,-3305],[-193,-2315],[188,-2547]]`, recovered from git — landing at **Ashvale
  (60,-1168) f192**. This is the one exit the borrowed art actually paints.
* **THE FERRY** on the Purser, with all four ports at the `SITES`-gated arrives.
* **The Purser went back to R1's (130,-1650)** — and this mattered. The §15 pass had moved him to the
  west wall at (-130,-2400) to escape berth 4's mouth; with the row gone, the *west* wall is now the
  wrong side, because at x -130 the restored door quad reaches **z -2353**, so a west-wall purser at
  -2400 would have been standing **inside the home door** and warped out on his first nudge. Caught by
  re-deriving the quad's slanted edge instead of assuming the previous position was still safe — the
  same class of bug the berth row had, one pass later.

## 17.4 Layout probe — **WARNINGS: none**, and the corridor is legible

`probe_marker/layout_pass8/`; both PNGs read. The corridor now contains **exactly four things**, north
to south: the **ledger prop + savepoint press area** (west, z -1450 / -1550..-1350) · the **Purser**
(east, 130,-1650) · the **spawn** (centre, 0,-2000) · **one large door zone** filling the south end
(z -2315..-3377). Nothing overlaps, and there is a single obvious exit at the end you face.

Spawn clearance re-verified: at x 0 the door quad's slanted north edge sits at z ~ -2432, so the spawn
is **432 u clear** of the only remaining zone. `lint`: 0 errors, 1 advisory (`entry_settle` -> 50 frames).

## 17.5 Write-set — 14 files, 891 before and after

7 × `EVT_LANTERN_HALL.eb.bytes` (**6962 -> 7703 B**) + 7 × `6601.mes`. **DictionaryPatch line set
byte-identical, so no relaunch.** Zero world meshes, zero dispatchers, zero `FF9CustomMap`. Proof:
`probe_marker/writeset_md5_diff_pass8.txt`.

## 17.6 Verified from the DEPLOYED `.eb`, all 7 languages

* **Ashvale's arrive block appears exactly 2x** — once as the ferry row, once as the walk-out home door;
* **Tidefall / Grimhorn / Larkspur exactly 1x each**, with their own coords and face;
* **`D8:2 = 35` written 5x** (four ferry arms + the door), **`D8:2 = 62` written 0x**;
* **`[CHOO]` present in every `6601.mes`** — the choice window is really there;
* the script still parses to 10 entries / 24 functions.

## 17.7 The ring-closure check now covers BOTH declarations

`probe_marker/probe_quay_sites.py` previously parsed the hall's four `[[gateway]]` arrives. It now
parses the **`[[ferry.destination]]` rows** *and* the **single home-door gateway**, asserting each
against `SITES`, plus that exactly one walk-on exit remains and that the deleted sign flags are
unassigned. **169 checks, ALL PASS** (four sites × two discs + ring closure).

One self-inflicted lesson worth keeping: the first version of the "flags are gone" check was a
substring test for `"8760"`, which matched **this file's own explanatory comment** and failed on a
correct hall. It now matches a `flag = 876x` **assignment**. A prose-sensitive gate is a false-alarm
generator.

## 17.8 Undo

Restore the 7 `.eb` + 7 `.mes` from `backups/r2-ferry.20260726/` into
`FF9CustomMap-world/StreamingAssets/.../field/<lang>/EVT_LANTERN_HALL.eb.bytes` and
`FF9CustomMap-world/FF9_Data/EmbeddedAsset/text/<lang>/field/6601.mes` respectively.

That returns the hall to §15's four-alcove berth row. **~ -> Reload field** (no relaunch). For R1's
single door, use `backups/r2-sweep.20260726-r2sweep/field6601/` instead.

## 17.9 Playtest ask (owner) — no relaunch, ~ -> Reload field

1. The hall reads as **one room with one door and one person**: ledger north, Purser on the east wall,
   the south door out to our own quay.
2. **Talk to the Purser** -> a menu pops (fully drawn, no type-on) -> Ashvale / Tidefall / Grimhorn /
   Larkspur / "Not yet". Picking a port fades and lands you at that quay, beside its beacon.
3. **Cancel (B) declines** — it must never sail you anywhere.
4. **Walking out the south door** lands you at Ashvale, the home port.
5. No accidental warps anywhere in the corridor: the only walk-on trigger is the door itself.
6. Larkspur is the one that lands you facing **west** (inland is west there).

---

# 18. THE FERRY SOFTLOCK — root-caused from the deployed bytes — FIXED, + the hall stripped to two things

Run 2026-07-26. Backups: **`backups/r2-ferryfix.20260726/`** (7 `.eb`, 7 `.mes`, `DictionaryPatch.txt`).

## 18.1 ROOT CAUSE — `MOVEMENT_GATE` in a talk context

**Hypothesis 1 (double binding) is FALSE.** The deployed talk handler has **one** window at `[1120]`
(`WindowSync(1,128,501)` = the choice prompt). `build`'s talk-body selection assigns
`sb = _choice.speak_body(...)`, which *replaces* the plain `WindowSync`. The Purser's `dialogue` line was
allocated a txid and simply never referenced — dead text, not a second window.

**Hypothesis 2 is TRUE, but the mechanism is not a missing close-window op** — `WindowSync` is
synchronous (`MES` 0x1F waits for the close), so the window is already gone. The killer is the
**usercontrol prologue**. The deployed arm read:

```
[1119] DisableMove()                       <- the talk body disables movement
[1120] WindowSync(1, 128, 501)             <- the choice prompt (SYNC: pick is finalised)
[1126] op_05({op7A(9) ...})                <- GetChoose
[1134] op_02(1111)                         <- switch dispatch
[1137] WindowSync(1, 128, 502)             <- the picked row's reply
[1143] op_05({op7A(2) op7F})               <- IsMovementEnabled          ← THE BUG
[1147] op_03(1)                            <- JMP_TRUE +1
[1150] op_04()                             <- RETURN                     ← taken
[1151] DisableMove()                       <- never reached
[1152] FadeFilter(6, 24, ...)              <- never reached
...    position blocks, key 35, WorldMap   <- never reached
```

`region.MOVEMENT_GATE` is `ifnot (IsMovementEnabled) { return }` — `7a 02` — *"the verbatim
region-trigger prologue … exactly like every real exit/switch region."* It is correct for a **walk-on**
region, where the player is walking and movement is enabled. Inside a **talk** handler movement is
already disabled (the handler's own `DisableMove()` at `[1119]`), so `IsMovementEnabled` is **0**, the
gate takes its early `return`, and **the entire exit is skipped**. Because `DisableMove()` has already
run and nothing re-enables it, the player is left frozen with no window: **the softlock**.

A region-context prologue is not portable into a menu context. Nothing in the type system said so, which
is why it shipped.

## 18.2 The fix (kit level)

* `worldexit.worldmap_exit_body(..., **gate: bool = True**)` — emits `MOVEMENT_GATE` only when True.
  Both branches (with and without `arrive`) honour it. The docstring now carries the whole trap.
* `choice.option_body`'s `worldmap` arm passes **`gate=False`**, with the reason inline. Walk-on
  gateways are untouched and still emit the prologue.
* **Regression tests** (`test_ferry_lane.py`, now 22 cases):
  * a ferry arm must **not** contain `MOVEMENT_GATE`, **and** a region exit still must;
  * `gate=False` differs from `gate=True` by *exactly* the prologue and nothing else;
  * the fade still precedes the arrive writes in a ferry arm.

Confirmed in the redeployed bytes — the gate and its `RETURN` are gone, and the fade now runs
unconditionally:

```
[1093] WindowSync(1, 128, 501)   <- reply
[1099] DisableMove()
[1100] FadeFilter(6, 24, ...)    <- reached
```

## 18.3 Defect A — the south walk-on door REMOVED

Under the Purser-runs-the-ferry design it was redundant (its `arrive` *was* his Ashvale row) and it was
the same invisible walk-on quad class the berth row was condemned for. Deleted. **The hall is
exit-by-ferry-only.** Ring closure now asserts **ZERO walk-on exits** instead of "exactly one".

## 18.4 Defect C — the twin moogle MERGED into the menu

The ledger was a second `model = 220` moogle ~330 u from the Purser — on screen, two identical moogles
clumped beside Zidane. Deleted **both** the `[[prop]]` and the `[[savepoint]]` zone; the Purser gained a
**"Log the passage."** row that opens the real save menu.

New kit capability, kept minimal: `[[ferry]] save = "<row text>"` (+ optional `save_reply`) desugars to a
choice row carrying `savepoint.save_act()` — the latched `GLOB(184)=1; Wait(3); Menu(4,0); Wait(3);
GLOB(184)=0` both real save families use. It is **not** a transition (`Menu` returns to its caller), so
it may sit before other actions, and it is inserted **before** the decline row so CANCEL still lands on
"Nothing for now." Tests pin the emitted op, the non-transition property, and the row ordering.

Also added: **lint now rejects `dialogue` + `[[ferry]]` on one NPC** — the ferry prompt replaces the talk
window, so such a line is silently dead text. That is precisely what the Purser had.

## 18.5 The menu shape

Prompt: *"Kupo! I am the purser of this hall — I keep the ledger and I sail the ferry. What do you need,
kupo?"*

| row | action |
|---|---|
| Sail to Ashvale | worldmap exit → (60, −1168) f192 |
| Sail to Tidefall | worldmap exit → (432, −1232) f192 |
| Sail to Grimhorn | worldmap exit → (1214, −1192) f192 |
| Sail to Larkspur | worldmap exit → (688, −616) **f64** |
| Log the passage. | latched `Menu(4,0)` (save) |
| Nothing for now. | **decline — LAST, so CANCEL/B lands here** |

## 18.6 Layout probe — WARNINGS: none; the corridor holds TWO things

`probe_marker/layout_pass9/`; both PNGs read. `CONTENT` is **Purser (130,−1650)** and
**spawn (0,−2000)**, 373 u apart. The report has **no `ZONES` section at all** — there are zero regions
in the field now (no gateway, no savepoint, no events). You spawn, there is exactly one person, you talk
to them. `lint`: 0 errors, 1 advisory (`entry_settle` → 50 frames).

## 18.7 Write-set — 14 files, 891 before and after

7 × `EVT_LANTERN_HALL.eb.bytes` **7703 → 5600 B** (it SHRANK: the door's whole worldexit body and the
savepoint region are gone, the ferry gained one save row) + 7 × `6601.mes`. **DictionaryPatch line set
byte-identical → no relaunch.** Zero world meshes, zero dispatchers, zero `FF9CustomMap`. Proof:
`probe_marker/writeset_md5_diff_pass9.txt`.

## 18.8 Deployed-`.eb` assertions — all 7 languages

* **exactly ONE talk handler** (tag 3) on the Purser;
* **four arrive blocks, each ×1**, with their own coords and face;
* **`D8:2 = 35` ×4**, **`D8:2 = 62` ×0**;
* **zero `MOVEMENT_GATE` occurrences inside any talk body** (the regression that caused the softlock);
* the latched **save act present**;
* **`[CHOO]`** present in every `6601.mes`;
* **zero gateway regions** carrying a worldmap exit.

## 18.9 Undo

Restore the 7 `.eb` + 7 `.mes` from `backups/r2-ferryfix.20260726/`. That returns the softlocking
build with the south door and the twin moogle — useful only for re-confirming the bug. For earlier
states see §17.8 (four-alcove row) and §15.6 (R1 single door). **~ → Reload field**; no relaunch.

## 18.10 Playtest ask (owner) — no relaunch, ~ → Reload field

1. **Talk to the Purser — the menu must not softlock.** Pick a port: fade, then you land at that quay.
2. **"Log the passage."** opens the save menu and returns you to the hall.
3. **Cancel (B)** lands on "Nothing for now." and closes clean — never sails, never saves.
4. The hall contains **only** Zidane and the Purser. No second moogle, no invisible warps anywhere.
5. Larkspur still lands you facing **west**.

---

# 19. THE QUAY/BOAT CONFIRM RACE — the bench boat now MOORS HOME — APPLIED (hot; no relaunch)

Run 2026-07-26. Backups: **`backups/boat-moorhome.20260726/`** (all 7 `EVT_WORLD_WORLD11.eb.bytes`).

## 19.1 The bug

Pressing Enter at a Southern Ring quay entrance *sometimes* boarded the crimson Blue Narciss instead.
The bench boat (WORLD11 entry 15, uid 15, `studies/custom-vehicle/build_boat_world11.py`) had a v1
dismount that **parked the boat where it floated** while snapping only the player to its home dock
(493, −1114). A boat left floating near a quay leaves its own per-frame **bare-Confirm board check**
(`0x24000`, ~100 u radius) sitting right there, racing the quay's confirm gate.

Owner ruling: **MOOR-HOME** — the dismount returns the boat to its mooring too, so it can only ever
board at the block-(7,17) islet, 125 u+ from any quay. Proper boarding UX (a prompt, shore-legality)
stays R5.

## 19.2 The change — two ops, +24 bytes, in one function

Amended the dismount branch of the boat's tag-1 loop, after the existing detach/player-snap:

```
 L115:
   SET({Global.Byte[190] const(7) B_EQ const4(147456) B_KEYON B_ANDAND B_EXPR_END})
   JMP_IFNOT(L184)
   DisableMove()
   DetachObject(14)
   RunScriptSync(6, 14, 60)                                              # player -> DOCK  (unchanged)
+  MoveInstantXZY({const4(125952)}, {const(200)}, {const4(4294678016)})   # the BOAT -> BOAT_SPAWN
+  TurnInstant({const(0)})                                               # -> BOAT_FACE
   SET({Global.Byte[190] const(0) B_LET B_EXPR_END})                      # (unchanged from here)
   RunWorldCode(1, 0)
   op_22(8) ; EnableMove() ; EnableMenu()
 L184:
```

`125952/256 = 492`, `(4294678016 − 2³²)/256 = −1130`, y `200`, face `0` — i.e. exactly
`BOAT_SPAWN` / `BOAT_Y` / `BOAT_FACE`. Body **166 → 190 B**; the assembler recomputed every label
(`L160` → `L184`), so no hand jump-fixup was involved. Before/after disassembly archived at
`studies/custom-vehicle/moor_home/{before,after}_entry15.txt`.

## 19.3 (4) LOAD-PATH VERDICT — already covered, no extension needed

Checked from the deployed bytes rather than assumed. Entry 15's Init ends:

```
   JMP(L86)          <- the mode-7 attach arm jumps here
 L100: ...           <- the not-boarded arm falls through to here
 L86:
   MoveInstantXZY({const4(125952)}, {const(200)}, {const4(4294678016)})
   TurnInstant({const(0)})
   RET()
```

`L86` is the merge point of **both** branches, and a scan of the whole entry finds **no
`Global[74..82]` parked-record read anywhere** — consistent with the script's own "POSITION IS
HARD-CODED for the bench — NO gEventGlobal reads/writes" (an earlier build did use that stock record
and parked at garbage after relaunch, in-game 2026-07-22). So **a world load already re-moors the boat
at `BOAT_SPAWN` unconditionally**, whatever happened in the previous session. The fix did not need to
be extended to the load path.

## 19.4 How it was applied

**In place on the live deployed dispatchers** — `eb.edit.replace_function_body(data, 15, 1, new_body)`,
each of the 7 languages patched from **its own** bytes. `build_boat_world11.py` was **not** re-run
wholesale: the deployed WORLD11 carries the Southern Ring R1/R2 surgery (the case-53 nameplate handler
and four quay trigger funcs) that the study script's baseline predates, so a wholesale rebuild would
have clobbered it.

The study script's `BOAT_LOOP` source was updated to match, with a comment naming this bug, so any
future rebuild emits the fix. Safe to regenerate from source because the deployed bodies were first
proven **byte-identical** to `assemble_block(BOAT_INIT)` / `assemble_block(BOAT_LOOP)` (111 B and
166 B) before any edit.

## 19.5 Write-set — 7 files, 891 before and after

| file | before | after |
|---|---|---|
| `world/{us,uk,es,fr,gr,it}/EVT_WORLD_WORLD11.eb.bytes` | 9817 B | **9841 B** |
| `world/jp/EVT_WORLD_WORLD11.eb.bytes` | 9805 B | **9829 B** |

JP's 12-byte difference is its own legitimate layout (it carries localized inline dialogue) — which is
exactly why each language was patched from its own bytes and never cloned from `us`. Zero world meshes,
zero field `.eb`, zero `DictionaryPatch`, zero `FF9CustomMap`. Proof:
`studies/custom-vehicle/moor_home/writeset_md5_diff.txt`.

## 19.6 Assertions

* **Per language: the ONLY changed function is entry 15 / tag 1.** Every one of the other **102**
  functions in WORLD11 is byte-identical (compared body-by-body via `EbScript`, not by file hash).
* **The other 8 dispatchers: zero changed functions**, each still carrying its 3 new quay trigger
  funcs from the R2 sweep.
* **The case-53 nameplate handler and all four quay triggers are intact** — the ring's dispatcher
  assertions still hold across all 63 files.
* The 16 world marker meshes are byte-identical (WORLD11 dispatchers are not disc-scoped, so there is
  no disc mirror to re-run).

## 19.7 Undo

Restore the 7 files from `backups/boat-moorhome.20260726/` into
`FF9CustomMap-world/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world/<lang>/EVT_WORLD_WORLD11.eb.bytes`.
That returns the float-park dismount (and the quay race). Exit and re-enter the overworld; no relaunch.

## 19.8 Playtest ask (owner) — no relaunch

1. Board the boat at the islet, sail somewhere far (e.g. past a quay), press Enter to dismount: **the
   player lands on the islet dock AND the boat is back on its beach** — not floating where you left it.
2. **At every quay, Enter now only ever enters the field** — no boarding.
3. Sail out and back a few times: the boat should always be found beached at the islet.

---

# 20. THE BOARD GATE WAS A NO-OP — a 256× unit mismatch, broken open since rung 1 — FIXED

Run 2026-07-26. Backups: **`backups/boat-rangegate.20260726/`** (all 7 `EVT_WORLD_WORLD11.eb.bytes`).

## 20.1 First, a correction to the diagnosis

The brief said the board arm was "gated on input alone — no proximity term". **That was wrong**, and the
deployed bytes falsified it: there were always **two** gates, and gate 2 was a two-sided proximity test.
I stopped rather than build on it. The real defect is inside that existing gate.

## 20.2 ROOT CAUSE — `f[]` reads WORLD UNITS, the constant was FIXED POINT

Grounded in the decompiled evaluator, line by line (`C:\gd\FFIX\Memoria`):

| element | source | semantics |
|---|---|---|
| `obj(uid).f[0]` / `.f[2]` | `EBin.cs:1751-1793` (`getvobj` case 0/2) | `CastFloatToIntWithChecking(((PosObj)obj).pos[0 or 2])` |
| that cast | `EBin.cs:1830-1840` | Floor/Ceil/Round agreement — **a plain round-to-int, NO scaling** |
| `B_MINUS` | `EBin.cs:691-698` | `Int32` subtract, pushed via `expr_Push_v0_Int24` |
| `B_LT` | `EBin.cs:715-730` | **signed** `Int32 <`. Its two hardcoded hacks (Treno `fldMapNo` 908/1908 with `gCur.uid == 0 && t3 == 80`; `gCur.uid == 13 && t3 == -300`) do **not** apply to WORLD11 / uid 15 / our constants |
| `B_CONST4` | `EBin.cs:1241-1246` + read-back `EBin.cs:1682-1684` | `& 0x3FFFFFF` then sign-extend `(t0 << 6) >> 6` ⇒ signed 26-bit, so negatives are fine |
| `GetObjUID(250)` | `EventEngine.cs:943-955` | `uid = _context.controlUID` — whoever holds control (the walking avatar while on foot) |

So **`f[]` is the actor's position in plain world units**, while the gate compared differences against
`const4(25600)` — a constant authored as "100 u × 256", i.e. the **fixed-point** domain of
`MoveInstantXZY`'s arguments and the gEventGlobal position record. Two different domains, 256× apart.

**Why it passed at 445 u:** the FF9 overworld spans ~1536 u in x and ~1280 u in z, so the largest
possible |Δ| anywhere on the map (~2000 u) is still far below 25600. Every one of the four `B_LT` terms
is therefore **unconditionally true everywhere**. Measured at the Ashvale quay: |Δx| = 444, |Δz| = 38 —
both < 25600 ⇒ gate true ⇒ teleport-board, exactly the owner's *"it does do the boat-beach warp"*.

**The gate has been a no-op since rung 1.** Boarding "worked at the islet" because it worked
*everywhere*; nobody pressed Confirm far from the boat until now. The intended radius was 100 u; the
emitted constant expressed 25600 world units — about 12× the map diagonal.

The other two suspects are **ruled out**: uid resolution is fine (`250` → the walking avatar, `15` → the
boat; they are distinct, and a null or non-actor would have NullReferenced on `obj.cid` or read 0
asymmetrically, neither of which matches), and there is no float/int coercion problem — the cast is a
clean round-to-int and both `B_MINUS`/`B_LT` are signed integer ops.

## 20.3 The fix — an absolute window in the proven domain

Gate 2 is replaced (not preceded) by a constant window on the **player's** position, in world units:

```
SET({const4(451)  obj(uid=250).f[0] B_LT      # 451 < x   ->  x >= 452
     obj(uid=250).f[0] const4(533)  B_LT B_ANDAND   # x < 533   ->  x <= 532
     const4(4294966125) obj(uid=250).f[2] B_LT      # -1171 < z ->  z >= -1170
     obj(uid=250).f[2] const4(4294966207) B_LT B_ANDAND B_ANDAND B_EXPR_END})
```

`4294966125` / `4294966207` are −1171 / −1089 in the unsigned literal form; the 26-bit sign-extension
recovers them exactly (asserted in the test). The inclusive box is **[452, 532] × [−1170, −1090]** — the
±40 u window specified, which covers the beached hull and `DOCK` (16 u away) and reaches no event tile
and no other interactable (the nearest quay trigger, Tidefall, is 125 u from the mooring).

Absolute rather than relative on purpose: it no longer depends on the boat's own position, so it is
belt-and-braces with §19's moor-home rather than relying on it, and only the player's coordinates enter
the comparison. A new `wu()` helper sits beside `fp()` in the study script with the domain trap written
out, so the next author cannot repeat the mistake.

Gate 1 (`[190]==0 && KEY(Confirm)`) and the dismount arm are unchanged — a global Confirm while
`[190]==7` is correct, since the player is on the boat.

Once the gate actually works, §19's observation that *the dock is permanently inside the 100 u radius*
stops mattering: the window is deliberately islet-sized.

## 20.4 Offline verification against the proven semantics

`studies/custom-vehicle/range_gate/eval_gate.py` re-implements each op above from its cited source line
and evaluates **both** expressions over five probes. Output archived at `range_gate/eval_output.txt`.

| probe | deployed gate | corrected gate | expected |
|---|---|---|---|
| mooring (492, −1130) | true | **true** | yes |
| dock (493, −1114) | true | **true** | yes |
| Ashvale quay (48, −1168) | **true ← the bug** | **false** | no |
| Tidefall trigger (420, −1232) | **true ← the bug** | **false** | no |
| far ocean (1200, −400) | **true ← the bug** | **false** | no |

The test asserts *both* halves — that the deployed gate is always-true (the bug reproduced) and that the
corrected one matches every probe — so it fails if either claim stops holding.

## 20.5 Write-set — 7 files, 891 before and after

| file | before | after |
|---|---|---|
| `world/{us,uk,es,fr,gr,it}/EVT_WORLD_WORLD11.eb.bytes` | 9841 B | **9825 B** |
| `world/jp/…` | 9829 B | **9813 B** |

**−16 B each**: the 4-term absolute window is shorter than the 8-term difference test it replaces
(tag-1 body 190 → 174 B). Applied with `eb.edit.replace_function_body(data, 15, 1, …)`, each language
patched from **its own** bytes; `build_boat_world11.py` was again **not** re-run wholesale, since the
deployed WORLD11 carries the ring's R1/R2 surgery. Zero world meshes, zero field `.eb`, zero
`DictionaryPatch`, zero `FF9CustomMap`. Proof: `range_gate/writeset_md5_diff.txt`.

## 20.6 Assertions

* per language the **only** changed function is entry 15 / tag 1; the other **102** WORLD11 functions
  byte-identical (compared body-by-body via `EbScript`);
* the **other 8 dispatchers: zero changed functions**, each still carrying its 3 quay triggers;
* the **case-53 nameplate handler and all four quay triggers intact** across all 63 files;
* `25600` no longer appears anywhere in the boat loop;
* before/after tag-1 disassembly archived at `range_gate/{before,after}_tag1.txt`.

## 20.7 Undo

Restore the 7 files from `backups/boat-rangegate.20260726/` (that returns the broken-open gate). For the
pre-moor-home state use `backups/boat-moorhome.20260726/` (§19.7). Exit and re-enter the overworld; no
relaunch.

## 20.8 Playtest ask (owner) — no relaunch

1. **Press Confirm far from the islet — nothing should happen.** Try it at each quay, mid-ocean, and
   inland. No boat warp.
2. **At the islet, boarding still works** — stand by the beached hull or on the dock and press Confirm.
3. Dismount still lands you on the dock with the boat back on its beach (§19 unchanged).
4. The quay entrances should now respond to Confirm normally and exclusively.

---

# 21. R3 — LAMPLIGHT ISLAND (the r44 mint at the reserved case-52 slot) — **APPLIED**

Run 2026-07-26, worktree `r3-lamplight-island-overworld-44317f`. Backup root:
**`backups/r3-lamplight.20260726-r3lamplight/`** (main repo). **A RELAUNCH is required** (first-time
`FieldScene`/`MessageFile 6602` registration) — until then the live game ignores all of it; the world
meshes and dispatcher edits would hot-load on world re-entry but the entrance's destination would not
exist, so DO NOT walk onto the trigger before relaunching.

## 21.1 What R3 is

The design's one new landmass and the region's one NAMED landmark (design judgment: "Case 52 is held
in reserve for the region's one named landmark (Lamplight)"): a native-grass island mint in the
wrapwater corridor, carrying a case-52 native entrance ("Lamplight", locId 51 = block-68 split[52])
into a new interior field — **6602 LAMPLIGHT**, the lamp room (BG-borrow of L. Castle/Telescope,
field 615, `LDBM_MAP190_LB_OBS_0`, area 11) — with the R2 doored beacon as its visible landmark.
Reachability on foot is deliberately none (the island sits on the sailable west arc, R5's concern);
**R3 is judged by teleport**, per the judgment's own note on mint-first rungs.

## 21.2 The mint (blocks all previously FREE — verified live before deploying)

`world-island --center 1432,-1176 --radius 44 --lobes 1 --seed 44 --mod-folder FF9CustomMap-world`

* **Seed selection was MEASURED, not defaulted** (14 dry-runs): the default seed (718) mints 4
  zero-UV-area tris + 4 family-rect zero-area offenders; seed 44 mints ZERO hard texture defects
  (only the endemic one-window advisory, 76/702 mains tris — that gate's own docstring: blind
  judging refuses even real stock ground). Candidates were compared on the underlying gate
  fractions, never on printed warning-line counts (a REFUSED run prints zero warnings — the first
  sweep instrument was wrong exactly that way).
* **The outline was measured against the design's clearances**: r_max 47.1u (overshoot 1.07× — the
  design allowed 1.57× → 69.1u against the 88u forbidden ring), west sea channel 43.1u / east 57.3u
  vs the design's declared 44/60u corridor channels. The lobes=2 candidates narrowed the west
  channel to ~30-35u and were rejected for that.
* 6 blocks written: (21,17) (21,18) (22,17) (22,18) (22,19) (23,18) — centre grounds y 3.2 topo 0.
* Write-set: **108 new files, 0 changed, 0 removed** (54 per disc incl. Donor.txt sidecars, auto-
  mirrored); whole-folder md5 proof `probe_r3/mint_writeset.txt` (891 → 999 files).
* Offline acceptance: `probe_r3/probe_lamplight_mint.py` — **ALL CHECKS PASS on both discs**
  (files + sidecars, centre/trigger/anchor/arrive all walkable Terrain topo-0 at plateau y 3.2 in
  both query modes, 16-point r=20u interior ring walkable, full disc parity).
  Output: `probe_r3/probe_mint_output.txt`.

## 21.3 The interior field — 6602 LAMPLIGHT

`studies/overworld-topography/southern-ring/lamplight-tower.field.toml`, deployed
`py tools/deploy_field.py <toml> --id 6602 --name LAMPLIGHT --mod-folder FF9CustomMap-world`.

* Pre-flight: `FieldScene 6602` ABSENT from both live registries (main folder has 4003-30421 dev
  ids; `-world` had 4600 + 6601). Donor picked from the manifest: the telescope deck is the one
  stock room that reads as a beacon's lamp gallery; Daguerreo/Gargan Roo already spent.
* Content: spawn (0,-400) · keeper moogle "Moglow" (-450,200), model 220, one line · the donor's
  OWN east exit region (Region4 of field 615's real script, quad verbatim) as a walk-out
  `[[gateway]] to="worldmap"`, arrive **(1436,-1168) f192** — 12u east of the trigger, facing away
  (THE ARRIVAL-CLEARANCE LAW).
* Layout probe `probe_r3/layout_pass2/` — WARNINGS: none; both PNGs read (spawn/NPC 750u apart on
  the platform, the door zone on the SE stairway, 600u clear of the spawn). Caught en route: the
  gateway quad key is **`zone`**, not `region` — a `region` key is silently ignored (the pass-1
  probe drew no zone; that gap IS the catch).
* `lint`: 0 errors, 1 advisory (`entry_settle` auto → 50 frames).
* Write-set: 14 new files (7 `EVT_LAMPLIGHT.eb.bytes` + 7 `6602.mes`) + 2 registry lines. The
  New-Game field-70 override was byte-checked after the deploy: still `Field(4600)`, no 6602 —
  the deploy notice's "New-Game auto-warp" line is boilerplate.
* Revert: `py tools/scroll_out/revert_deploy_6602.py`.

## 21.4 The entrance + beacon (the reserved case-52 slot)

`rebuild_quay_marker.sh lamplight` — the canonical invocation (now parameterized FIELD/NAME/CASE
per site; the four quays keep 6601 / "Lantern Quay" / 53):

    world-entrance --cell 44 36 --field-direct 6602 --nameplate-name "Lamplight" --nameplate-case 52
      --trigger-at 1424 -1168 --trigger-radius 3.0 --no-tile-area --mod-folder FF9CustomMap-world
      --building quay_beacon_lamplight.obj --building-at 1424 -1160.425 --no-seat --replace-town
      --building-idall 4078

* `mint_quay_beacon.py` gained the **lamplight** `SITES` row (anchor (1424,-1160.2), ground_y 3.20,
  trigger rect x[1420,1428] z[-1172,-1164], arrive (1436,-1168) f192, block (22,18), cell (44,36))
  — the Ashvale disposition translated +1376 in x, southern-limit derivation identical. All 29
  generator gates PASS; `quay_beacon_lamplight.obj` committed (our own procedural geometry).
* Surgery: dead case **52** → `[set explored word 98 bit 3 (navi bit 787)] + Field(6602)`; name
  registered at block-68 **split[52]** (locId 51). Cell tag 0xA4B1.
* **7 event tris** (not the quays' 6 — the minted terrain's own triangulation; dry-run-predicted).
  16 terrain tiles topo-59 under the beacon hull.
* **Additive-only PROVEN on all 63 dispatchers**: per file exactly ONE changed function
  (entry-1/tag-1 — the 2-byte case-52 reloffset patch + the appended 15-B handler) and ONE new
  function (the 0xA4B1 trigger func); zero removed; every other function byte-identical — which is
  also the proof that the four quay triggers and the case-53 handler are intact.
* Site probe: `probe_marker/probe_quay_sites.py --backup-root backups/r3-lamplight.20260726-r3lamplight`
  (quay pre-states copied in from the R2 sweep) — **ALL CHECKS PASS, all FIVE sites × both discs +
  ring closure** (the four quays regression-clean at the mesh level). Output:
  `probe_r3/probe_sites_output.txt`. The probe grew `TRIGGER_TRIS_BY_SITE` (7 for lamplight).

## 21.5 ⚠ THE NAMEPLATE-WIPE BUG — found by the byte check, FIXED in the kit

The surgery's rename step (`navimap.deploy_marker_renames`) rebuilt every language's 68.mes **from
the BASE game text** and applied only its own rename — erasing R1's "Lantern Quay" from split[53]
in all 7 languages. Every gate passed; only the post-deploy byte check
(`"Lantern Quay" in 68.mes → False`) caught it. **Any second named entrance wiped the first's name.**

* **Kit fix** (`ff9mapkit/ff9mapkit/world/navimap.py`): when an override is already deployed it IS
  the base — renames splice on top of it (idempotent; `apply_marker_renames` touches only the
  locIds given). Regression test:
  `tests/test_navimap_rename.py::test_deploy_merges_with_the_already_deployed_override`
  (also pins idempotence and that the merge path never re-extracts the base).
* **Install repair**: the 7 pre-pass 68.mes restored from `text68/`, then BOTH renames re-applied
  through the fixed merge path via the new standing registry
  `studies/overworld-topography/southern-ring/marker_renames.toml` (locid 52 → "Lantern Quay",
  locid 51 → "Lamplight"). Verified by parsing: split[52]='Lamplight', split[53]='Lantern Quay',
  all 7 languages.

## 21.6 Full R3 install footprint — 891 → 1013 files, 0 removed

| class | count |
|---|---|
| ADDED world meshes (6 blocks × parts × 2 discs, incl. the entrance-carrying (22,18) pair) | 108 |
| ADDED field 6602 (`.eb` + `.mes` × 7 langs) | 14 |
| CHANGED `DictionaryPatch.txt` (+`MessageFile 6602` +`FieldScene 6602`) | 1 |
| CHANGED world dispatchers (9 × 7 langs, additive-only proven) | 63 |
| CHANGED block-68 nameplate text (both names) | 7 |

Machine-readable: `probe_r3/r3_total_writeset.txt` (+ per-phase `mint_writeset.txt`,
`entrance_writeset.txt`). `FF9CustomMap` untouched. Tests: 144 green across the targeted world /
entrance / worldexit / ferry / navimap suites (incl. the new merge regression).

## 21.7 Backups taken BEFORE writing

| Backup (under `backups/r3-lamplight.20260726-r3lamplight/`) | Covers |
|---|---|
| `DictionaryPatch.pre6602.txt` | the `-world` registry pre-R3 (4600 + 6601 only) |
| `lamplight/Disc{1,4}/Block[22][18] {Terrain,Object}.ff9mesh` | the pre-ENTRANCE minted state (the site probe's `pre` baseline) |
| `dispatchers/<lang>/EVT_WORLD_WORLD*.eb.bytes` (63) | every dispatcher pre-surgery (the kit's own backup is US-only) |
| `text68/<lang>.68.mes` (7) | the R1 nameplate text ("Lantern Quay", no "Lamplight") |
| `ashvale/ tidefall/ grimhorn/ larkspur/` | copied IN from the R2 sweep so the 5-site probe runs from one root |

The island blocks need no backup: every minted file is NEW (delete = revert).

## 21.8 Undo (reverse order)

    G="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
    B="backups/r3-lamplight.20260726-r3lamplight"

    # 1. entrance + beacon + trigger tiles + dispatchers + nameplate
    for D in 1 4; do
      cp "$B/lamplight/Disc$D/Block[22][18] Terrain.ff9mesh" "$G/FF9CustomMap-world/FF9_Data/WorldMap/Disc$D/0_1/r18/"
      cp "$B/lamplight/Disc$D/Block[22][18] Object.ff9mesh"  "$G/FF9CustomMap-world/FF9_Data/WorldMap/Disc$D/0_1/r18/"
    done
    cp -r "$B/dispatchers/." "$G/FF9CustomMap-world/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world/"
    for L in us uk fr gr it es jp; do cp "$B/text68/$L.68.mes" "$G/FF9CustomMap-world/FF9_Data/EmbeddedAsset/text/$L/field/68.mes"; done

    # 2. the interior field (assets + its 2 DictionaryPatch lines)
    py tools/scroll_out/revert_deploy_6602.py

    # 3. the island itself -- every minted file is NEW; delete the 108 listed in
    #    probe_r3/mint_writeset.txt (blocks (21,17) (21,18) (22,17) (22,18) (22,19) (23,18),
    #    both discs, all parts + Donor.txt)

Then RELAUNCH. Case 52 returns to dead, block-68 split[52] to the stock placeholder, the corridor
to open ocean.

## 21.9 Standing traps carried forward

* `world-island`/`world-reclaim` over block (22,18) WIPES the beacon + trigger/hull idalls (the §9.6
  class, now ×5) — re-run `rebuild_quay_marker.sh lamplight`.
* The kit's `world-entrance` dispatcher backup is still US-only — take all 7 langs yourself first.
* `deploy_field` prints "reachable via the New-Game auto-warp" unconditionally — it does NOT rewire
  New Game (byte-checked); don't panic, but don't trust the notice either.

## 21.10 Playtest ask (owner) — ONE relaunch, judged by teleport

1. RELAUNCH. New Game → the hub → the hall → the ferry still sails all four quays (nothing
   regressed: the ring must feel identical to the R2-confirmed state, and every quay plate still
   reads **"Lantern Quay"**).
2. `~ → World → Teleport` to **(1432, -1176)**. Expect: a grass island under you (flat plateau,
   cliff rim), the doored beacon standing just north of centre, door facing you-ish (south).
3. Walk onto the trigger at the tower's foot → the approach plate shows **"?"** (unexplored) →
   press Confirm → fade → **the lamp room** (the Lindblum telescope deck art): Moglow the keeper
   on the west side, one line, kupo.
4. Walk out the south-east stairway (the painted stairs) → land back on the island at the beacon's
   east side, facing east, no instant re-entry.
5. The plate now reads **"Lamplight"** (the explored bit stuck), and `~ → World` still says 9011.
6. Sail-by check (optional, the boat is R5-dormant): nothing else in the corridor looks disturbed —
   the horseshoe bench (west of the island) and the wrapwater channels unchanged.

**Committed** (this worktree, branch `claude/r3-lamplight-island-overworld-44317f`): the study files
(toml, SITES row, rebuild script, marker registry, probes, this section), the navimap kit fix + its
regression test, and the probe's per-site trigger table.

---

# 22. R3 FIX — THE QUICKSAND CASE + THE VIRGIN NAMEPLATE BAND — **APPLIED** (playtest pending)

Run 2026-07-26, after the owner's playtest of §21: *"the ? plate at 1432 -1176 puts me in battle 144
against Antlion. it doesn't warp me to 6602."* Owner ruling on the first two proposed fixes: both
hacky; note the prior nameplate research; find a robust solution.

## 22.1 ROOT CAUSE — case 52 was never dead: it is THE QUICKSAND

Decoded from the deployed bytes (`us/WORLD00` entry-1/tag-1 @2885, present in ALL NINE free-roam
dispatchers, BEFORE the AREA-switch confirm path):

```
if (Byte[24]==52 && B_KEYON(Confirm) && !Byte[35] && !bit(44,3) && !bit(43,3) && !Byte[37]) {
    CloseWindow(6); CloseWindow(7); Battle(0, 144);      // the desert quicksand -> Antlion
}
```

**THE QUICKSAND CASE LAW: switch-dead is NOT dead.** The AREA switch's case-52 arm genuinely routes
to default — because the main loop consumes case 52 first. The surgery's deadness check measures the
switch; its *model* (dead-in-switch ⇒ safe) was wrong for exactly one case in the game. The real
quicksand cell tag (0x8899 → cell (38,8), the Cleyra desert) exists only in WORLD03/WORLD09, but the
battle branch ships in every free-roam main loop — so OUR case-52 tile armed it in world 9011.

Corrected-model census (all 9 free-roam dispatchers: switch-dead ∧ no `Byte[24]==K` main-loop branch
∧ no stock cell tag ∧ no real label): **no clean surgery slot remains** — 43 = "Landing Site",
54 = "Memoria", 55–59 = "Chocobo's Air Garden", 52 = the quicksand. The judgment's "nameplate
ceiling is 2" collapses to **1** (case 53, spent on the quays). Census + branch decode preserved in
the session log; the enduring law lives in `--nameplate-case`'s help text and the memory store.

## 22.2 THE ROBUST SOLUTION — THE VIRGIN CASE BAND (61–64)

Grounded in the prior nameplate research (the fix-A2 saga's verified laws — summon gated on
`Byte[24]==100`, warp on the on-foot gate, warp-branch `Byte[24]=100` mute — plus the surgery's
explored-bit/name-table map), with three new byte-verified facts:

* the stock name table has 61 entries (cases 0–60) and the plate read is a plain split-array index —
  a table WE ship and can extend;
* the AREA switch is base 2 × 59 cases (2..60): 61+ takes the benign out-of-range default;
* func-0xB's 49+ arm has NO upper bound (`Byte[38] = w98 >> (case−49)`; `Byte[24] = case+100`), so
  cases 49–64 exactly fill explored word 98, and the plate window admits any case < 90.

**Cases 61–64 are therefore VIRGIN**: no stock cell tag, no switch slot, no main-loop branch, no
label, no navi marker — but full plate + explored-bit machinery. A custom-name entrance there needs
ZERO stock-byte edits: the trigger self-summons the plate with its own case and does its own warp.
This also raises the ring's named-entrance budget from 1 to 5 (53 + 61-64).

## 22.3 Kit changes

| File | Change |
|---|---|
| `ff9mapkit/ff9mapkit/world/entrance.py` | `nameplate_summon(case=)` parameterized; `entrance_func_body_direct(nameplate_case=, explored_case=)` — the A2 body with a custom summoned case + the surgery's own explored-bit expr on the WARP branch (before the fade), "!" bubble dropped in that mode (parity with the surgery-form quays); `author_entrance`: `nameplate_case` 61–64 routes to the VIRGIN lane (no repoint — there is no slot; validation rejects 65+, which has no w98 bit) |
| `ff9mapkit/ff9mapkit/world/navimap.py` | `apply_marker_renames` EXTENDS the table for a locId past its end (padding gaps with the game's own `'  ?  '` mystery-spot placeholder) instead of silently dropping the rename — the write-lands failure class |
| `ff9mapkit/ff9mapkit/cli.py` | `--nameplate-case` help carries THE QUICKSAND CASE LAW + the virgin band; the receipt honestly describes the virgin lane (no "repointed" claim) |
| `ff9mapkit/tests/test_worldexit.py` | +2: the virgin body (summon-61 bytes, `w98\|=0x1000` on the warp branch before the fade, no FICON, A2 structure, case 61 absent from every switch, 65+ raises) and the navimap table-extension (pad values + target + other txids untouched) |

Tests: **146 green** across the targeted world / entrance / worldexit / ferry / navimap suites.

## 22.4 Install repair + redeploy (backups: the §21.7 set, reused)

1. **All 63 dispatchers restored** from `backups/r3-lamplight.20260726-r3lamplight/dispatchers/` —
   removes the §21 case-52 repoint, its appended handler, and the old trigger func in one step.
2. **All 7 `68.mes` restored** from `text68/` — split[52] back to each language's OWN stock
   quicksand label (`'  ?  '` us/uk, `'?'` fr/gr/it/jp, `'¿?'` es; verified stock-exact per
   language, ring deltas only).
3. `marker_renames.toml`: the locid-51 entry REMOVED (never ours — documented in the file), replaced
   by **locid 60** ("Lamplight" at split[61]).
4. Redeploy: `world-entrance --cell 44 36 --field-direct 6602 --nameplate-name "Lamplight"
   --nameplate-case 61 --trigger-at 1424 -1168 --trigger-radius 3.0 --no-tile-area
   --mod-folder FF9CustomMap-world --trigger-only` — dispatch funcs + the name only; the §21 terrain
   / tiles / beacon were probe-verified and are untouched. `rebuild_quay_marker.sh` lamplight row →
   `CASE=61` (+ the law in its header).

## 22.5 Verified from the DEPLOYED bytes

* **63 dispatchers vs the pre-R3 baseline: ZERO changed functions, ZERO removed, exactly ONE new
  function (entry 0, tag 0xA4B1)** — the entrance is now purely additive; every stock byte,
  including the quicksand branch, is byte-identical to pre-R3 (entry-1/tag-1 compared whole).
* The deployed WORLD11/us trigger body (127 B) is **byte-exact** to
  `entrance_func_body_direct(6602, world_state=9011, prompt=True, nameplate=True, nameplate_case=61,
  explored_case=61)`: on-foot gate → Confirm → [Byte[24]=100 mute + `w98|=0x1000` + zone-in fade +
  D8:2=9999 + Field(6602)] / approach → gated summon(61).
* Block-68, all 7 languages: **stock-exact except the ring's two deltas** — split[53]="Lantern Quay",
  appended split[61]="Lamplight" (len 61 → 62). Registry re-run proven **idempotent** (md5 unchanged).
* Site probe (5 sites × 2 discs + ring closure): **ALL CHECKS PASS**
  (`probe_r3/probe_sites_output_fix.txt`).

## 22.6 Undo

Repeat §22.4 steps 1–2 (restore dispatchers + text) and skip the redeploy — that is the pre-R3
state. The §21.8 island/field undo steps are unchanged.

## 22.7 Why the battle can never fire at Lamplight now (and the quicksand still works)

Our tile sets `Byte[39]=61` → `Byte[24]=161→61` — the quicksand branch tests `==52`, never true on
the island. The real quicksand cells still set 52 in WORLD03/09 and battle exactly as stock (their
bytes are untouched). The two features share nothing: not a case, not a label, not an explored bit.
Residual known cosmetic: NONE — the §21 caveat about the quicksand plate reading "Lamplight" is GONE
(split[52] is stock again).

## 22.8 Playtest ask (owner) — RELAUNCH once if you haven't since the R3 deploy, then:

1. `~ → World → Teleport` to **(1432, −1176)**: walk to the beacon's foot → the plate shows **"?"**
   + "Enter with [X]" (no "!" bubble — parity with the quays) → **Confirm → fade → the lamp room**
   (no battle, ever).
2. Moglow's line, then walk out the SE stairway → land beside the beacon facing east, plate now reads
   **"Lamplight"**.
3. A quay sanity pass: one ferry hop still lands beside its beacon, plate "Lantern Quay".
4. (Only if you happen to have a stock save near Cleyra: the quicksand still ambushes with Antlion
   and its plate still shows the stock "?" — nothing borrowed, nothing renamed.)

---

# 23. THE EXTENDED NAMEPLATE BAND — cases 65–155 — **APPLIED** (hot; plate-sanity check pending)

Run 2026-07-26, owner-directed ("could we extend the nameplates past a measly limit of 5? ...
just hit it now, we will need it eventually"). Backups:
`backups/r3-lamplight.20260726-r3lamplight/dispatchers-post-r3fix/` (all 63, the §22 state) +
per-file copies in `ff9mapkit/backups/nameplate-band/`.

## 23.1 What it is

The named-entrance space was capped at 5 per world (case 53 + the virgin band 61–64) by ONE thing:
stock func-0xB's last range arm (`w98 >> (case−49)`) dies above 64. **The engine is unbounded** —
`GetTableText` splits whatever block-68 we ship and the plate read bounds-checks (verified in
`FF9TextTool.cs`/`ETb.cs`) — and `Byte[24] = case+100` caps the case space at 155. So the kit now
splices func-0xB's RANGE-ARM SECTION (its first 114 bytes — identical across all 63 files except
WORLD02's pending-flag var, Byte[35] vs Byte[38]) with a chain adding arms for **65–90 and 94–155**
(the 91–93 vehicle-HUD trio reserved), whose explored bits live in the kit's OWN reserved words —
**`flags.NAMEPLATE_EXPLORED_FLOOR`, gEventGlobal bytes 2006–2017** (a new reserved `BitRegion`;
the `[[flag]]` validator now refuses reserved regions — a pre-existing enforcement gap closed).
Each file's TAIL (the per-world vehicle switch, 7 distinct shapes) is kept verbatim.

**Named-entrance budget per world: 5 → 93** (case 53 + virgin 61–90 ∪ 94–155).

## 23.2 Proofs

* **The oracle**: the composed stock arm section reproduces the live dispatcher bytes exactly, both
  var forms (`test_stock_arm_section_is_the_oracle`).
* **The semantics**: a byte-walking interpreter (EBin rules: Int32 ops, C# `>>` masks count&31) ran
  ALL 256 Byte[39] values through both chains — 168 stock-domain cases byte-equivalent (1–64, the
  91–93 trio, 156–255), 88 new-band cases reading their assigned word/bit
  (`test_extended_chain_semantics_all_256_cases`).
* **The deploy**: per file, ONLY entry-1/tag-11 changed; its new body == extended-arms + that file's
  own old tail verbatim; idempotence proven (a re-run writes 0, skips 63). 138 tests green across
  the affected suites.

## 23.3 Kit surface

`world-entrance --extend-nameplate-band --mod-folder <F>` (standalone, idempotent; a virgin-case
deploy past 64 also auto-runs it) · `entrance.f0xb_arm_section` / `extend_nameplate_band` /
`EXTENDED_EXPLORED_RANGES` / `RESERVED_VIRGIN_CASES` / `VIRGIN_CASE_MAX` · `explored_word_bit` +
`explored_set_expr` cover 65–155 (region-encoded long-index var form `FC + u16`, engine-verified) ·
`navimap.resolve_renames` locids to 154 (dot-table paths stay capped at the real 64) ·
`tests/test_nameplate_band.py` (6) · the stale QTE "e.g. 2006" byte-offset suggestion corrected.

## 23.4 Undo

Restore the 63 files from `dispatchers-post-r3fix/` (returns the §22 state — Lamplight case 61
still works; it never needed the extension). Re-enter the overworld; no relaunch.

## 23.5 Playtest ask (owner) — a plain plate-sanity pass on next play, nothing dedicated

The splice byte-preserves every stock computation, so nothing SHOULD look different. On your next
session simply confirm: a stock town plate still shows (walk near any real entrance), a quay still
reads "Lantern Quay", Lamplight still reads "Lamplight", and vehicle overlays (gil/time on
board/dismount) still behave. First consumer of a 65+ case: the R4/R5 named spots when they come.

---

# 24. PER-QUAY NAMES (cases 65–68) + THE AIRBORNE SUMMONER — **APPLIED** (hot; playtest pending)

Run 2026-07-26, owner-directed ("do the per-quay names now") — the extended band's first consumers.
Backups: `backups/r3-lamplight.20260726-r3lamplight/dispatchers-post-band/` + `text68-post-band/`
(the §23 state).

## 24.1 The change

Each quay's trigger func converted from the shared case-53 SURGERY form to its own VIRGIN case
(the Lamplight-proven A2 self-summon body, same `Field(6601)` destination, per-dispatcher
world-state record, own explored bit):

| quay | case | locId / split | explored bit |
|---|---|---|---|
| Ashvale | 65 | 64 / split[65] | word 2006 bit 0 (gEventGlobal bit 16048) |
| Tidefall | 66 | 65 / split[66] | word 2006 bit 1 |
| Grimhorn | 67 | 66 / split[67] | word 2006 bit 2 |
| Larkspur | 68 | 67 / split[68] | word 2006 bit 3 |

Nothing else moved: meshes, beacons, and trigger TILES are case-agnostic (`--no-tile-area` kept
every tile at area 0 since R1), so this was four `world-entrance --trigger-only` runs + the
registry. `rebuild_quay_marker.sh` carries the new per-site CASE/NAME.

## 24.2 ⚠ THE AIRBORNE SUMMONER — case 53's label was NEVER free (found by the widened census)

The per-quay verification swept `Byte[39]=K` setters across **ALL entries** (the earlier censuses
swept only entry-0 cell tags — the same class of miss as the quicksand, one level milder):
**WORLD08/09 entry-6/7 tag-12 is a stock airship-flight summoner** — over the Memoria site with
`var190==8||9` it summons case **54** ("Memoria") or case **53** (the pre-reveal `'  ???  '`
plate). So R1's "Lantern Quay" rename had been cosmetically hijacking pre-reveal Memoria's plate
on disc-4 airship flight since it shipped (warp-safe — airborne states never reach the AREA
switch; unreachable in ring playtests). Complete census verdict: cases 55-59 and **61+ have ZERO
setters anywhere** (the virgin band is confirmed virgin at the all-entries level); the surgery
band has **zero** truly clean slots — the virgin band is the only honest lane, which the ring now
uses exclusively.

**The fix (both halves, since nothing of ours uses case 53 anymore):**
* split[53] restored to each language's OWN stock label (`'  ???  '` us/uk, `'????'` fr/gr/it/jp,
  `'¿¿??'` es) — verified per language against fresh stock extraction;
* the case-53 AREA-switch reloffset restored to the DEFAULT target in all 63 dispatchers
  (verified; R1's appended 15-B handler remains as unreachable padding — removing it would shift
  the function layout for nothing).

Residual on old ring saves: w98 bit 4 (the old shared explored bit) stays set — flying over
pre-reveal Memoria on such a save shows the explored `'  ???  '` variant instead of the
unexplored `?`. Visually near-identical, disc-4-airship-only, new saves unaffected.

## 24.3 Verified from the DEPLOYED bytes

* **63 dispatchers vs the §23 baseline: exactly the FOUR quay trigger funcs changed per file**,
  each byte-exact to `entrance_func_body_direct(6601, ws=900N, case=65..68)`; nothing added or
  removed (the case-53 un-repoint compared separately: reloffset now == the default in all 63).
* **No function anywhere sets Byte[39]=53** except the stock airborne summoner (as designed).
* **68.mes ×7 langs**: split[53] stock-exact, split[61] "Lamplight", split[65-68] the four island
  names, `'  ?  '` padding at 62-64, table length 69.
* 5-site probe + ring closure ALL PASS; 109 tests green.

## 24.4 Undo

Restore `dispatchers-post-band/` (63 files) + `text68-post-band/` (7 files) — returns the shared
"Lantern Quay" state (including its Memoria-plate defect). Re-enter the overworld; no relaunch.

## 24.5 Playtest ask (owner) — no relaunch, re-enter the world

1. Visit each quay (ferry or walk): the plate now reads **"?"** on first approach (fresh per-island
   bits — previously-visited quays reset once), then the ISLAND's name after entering the hall from
   it: **Ashvale · Tidefall · Grimhorn · Larkspur**. Entering still lands in the Lantern Hall.
2. Lamplight still reads "Lamplight"; a stock town plate still works.
3. (Disc-4 airship over the Memoria site, only if ever handy: the plate shows `???`/`?` again, not
   "Lantern Quay".)

---

# 25. R4 — THE FOREST/ENCOUNTER PASS — **APPLIED** (relaunch for the minimap; teleport playtest pending)

Run 2026-07-26 ("go R4"). The rung as ratified: carve_forest per THE TOPOGRAPH 36-38 ENCOUNTER LAW
+ the island-E bench re-sited at the free r96 pocket (136,−168).

## 25.1 The encounter architecture — ZERO table edits (the design decision of the rung)

* **The corrected census**: every 36-38 record in the 355-table is reachable from some stock tile —
  the "private zone 24 / area 63" idea is REFUTED (area 63 carries 95 stock topo-37 tiles: the
  airship-landable Yan island's live table, scenes 777-780). There is NO stock-dead encounter
  record to own; in-place re-tabling ALWAYS collides with stock.
* **The lawful lane**: our tiles already carry **area 0 → zone 0** (the Alexandria region), whose
  topo-37 rows are the game's own starter set — records 4/5: **Python + Goblin** (scenes 359/357),
  **Mu** incl. the friendly variant (361/363), both fog rows present. We CONSUME the stock table,
  never edit it. A bespoke per-island table = the doc's scoped `WorldEncounters.csv` engine seam
  (s23-class), deferred until a design needs distinct fauna.
* **The law, verified in the engine**: `SelectScene()` resolves zone×topograph×fog — no record ⇒ no
  battle — plus the case-205 sysvar and 3 EventCollision gates all requiring topo 36-38. Open
  ground is the safe road by construction; the rate lever (case-26 `w_frameEventBattleProb`,
  probs 231/365) is live in all 9 dispatchers.

## 25.2 THE SMALL-HOST LIMIT — the ring's own islands refuse v1 carves (measured, recorded)

Every carve attempt on ring islands refused:
* the **junction island** (a junction_compose CARRY): "hole ring not a simple cycle" at every
  window — the hole-carve assumes mint lattice topology;
* **Lamplight (r44) and Tidefall's isle** (the E-remnant): the default 132-tri blob finds no
  plain-grass pocket, and every small donor (18-53 tris: (15,9)/(19,9)/(13,16)) fails **THE CANOPY
  STEP LAW** with `zipNyMin 0.00` — a degenerate zip triangle on small hosts ((18,13)/(7,16) refuse
  earlier: degenerate donor rims).

⚠ Instrument lesson (twice this arc): piping verb output through `tail -N` EATS the stderr refusal
line that prints first — a FAIL is indistinguishable from a PASS. A pass ends with a plan/deploy
line; judge by the LAST line, never by the absence of an error.

**Consequence:** the route islands get canopy in a later pass once `world-forest` learns small
hosts (the degenerate-zip diagnosis is the entry point). R4's gameplay proof lands on the bench.

## 25.3 THE BENCH — the island-E showcase re-homed at the pocket, now the region's first encounter island

* **Mint**: `world-island --center 136,-168 --radius 46 --lobes 3 --seed 137` — the seed found by a
  driver testing BOTH properties per seed (hard-clean texture gates AND blob capacity; island E's
  own seed 55 was chosen for capacity but mints dirty at this centre; hard-clean 314 has no
  pocket). All gates clean; 3 lobes N/W/S; no meadow stamps.
* **Canopy**: `world-forest --center 124,-156` (the proven (15,15) donor, 132 tris; hole 161 tris,
  63 zip tris) — all gates clean incl. the perimeter walk-in sim (worst step 2.05 ≤ 2.3) and
  MISS=0. **The carve carries the donor's AREA 7** (zone 2 — the Lindblum set): restamped to
  **area 0** on both discs (534 vert-tangents, topo/event/flags preserved) so the canopy rolls
  zone 0's Python/Goblin/Mu. ⚠ LAW for future carves: **a verbatim canopy carry imports the
  donor's AREA — the encounter zone is location semantics, not look; restamp to the host's area.**
* **Hill**: `world-hill --center 132,-204 --radius 13 --height 3.6` on the south lobe (the default
  R18 finds no footprint on these narrower lobes; r13/h3.6 is inside the real language). Flank
  25.8° ≤ 28.6, peak y 6.8 ≤ 8.6, all gates clean.
* `world-minimap` re-drawn (the bench + Lamplight now on the all-world map) — **RELAUNCH to apply
  the PNG**; the meshes themselves hot-load on world re-entry.

## 25.4 Write-set + probes

**108 added** (the bench: blocks (1,1)(1,2)(2,1)(2,2)(2,3)(3,2)+(2,0?) × parts × 2 discs, all in
rows r0-r4) · **1 changed** (the minimap PNG redraw) · **4 removed** = STALE `.bak-20260719` files
(a prior session's live-tree pollution on the Tidefall blocks) relocated with this rung's 10 fresh
hill `.bak`s to `backups/r3-lamplight.20260726-r3lamplight/bench-hill-baks/`. **Nothing outside
the bench region + minimap; the ring untouched** (`probe_r3/r4_writeset.txt`).

Probes: centre (136,−168) walkable grass y3.2 area 0 · canopy (124,−156) **topo 37 / area 0 /
no event bits** y6.9 · hill peak y6.8 · zero area-7 residue · full disc parity · the ring's 5-site
probe + ring closure ALL PASS post-R4.

## 25.5 Undo

Delete the 108 bench files (rows r0-r4, both discs — `r4_writeset.txt` is the list) + the minimap
override PNG; restore nothing (all-new). The relocated `.bak`s stay in backups.

## 25.6 Playtest ask (owner) — RELAUNCH once (minimap), then teleport-judged

1. `~ → World → Teleport` to **(136, −168)**: the bench island renders (3 lobes, no stamps);
   walk the whole rim loop.
2. **Walk INTO the north-lobe canopy** (~(124,−156)): encounters fire — **Pythons, Goblins,
   maybe a Mu** — at vanilla cadence. **Open grass and the hill: ZERO encounters** (the law's
   whole point — please walk both for a few minutes each).
3. The south hill (132,−204): climbs naturally from all sides.
4. The all-world map shows the bench + Lamplight (the minimap redraw).
5. Ring sanity: one ferry hop + Lamplight still behave (nothing in the ring was touched).

---

# 26. R4b — THE TABLE IS THE LAW: the safe road AUTHORED via area 14 — **APPLIED** (hot; re-playtest pending)

Run 2026-07-26, from the owner's R4 playtest: *"ragtime mouse appears in the forest as well...
still getting normal encounters in the grass of the island though (Lizard man, serpion (swampy),
axe beak, ironite (beach)) — all sorts of backgrounds."*

## 26.1 THE 36-38 "ENGINE LAW" IS FALSIFIED IN-GAME — the diagnosis chain, fully grounded

The ratified law ("battles fire ONLY on forest/brush; open ground is the safe road") is FALSE as an
engine absolute. The roll path is `EventEngine.ProcessEncount` (usercontrol + step accumulator, NO
topograph clause) → `SelectScene()` → `w_worldGetBattleScenePtr()` = **zone × topograph × fog off
the WALKED TILE's area bits** (`m_GetIDArea(m_moveActorID)`; `status.id` is per-step fresh from the
movement raycast — no caching). The case-205 topo∈[36,38] sysvar exists but is NOT the operative
gate (exactly as OVERWORLD_ENGINE.md's own 2026-07-02 correction warned; the design round's
"verified" law repeated the misreading). **Safety is a TABLE property: ground is safe iff its
(zone, topograph, fog) triple has NO record.** Prior "no battles on ring grass" observations were
exposure time, not law.

Fingerprint (three hypotheses fell before the right one — each killed by data, in order):
1. "zone 0's topo-0 rows" — REFUTED: those are Python/Goblin/Mu (scenes 357-364), not the report.
2. "donor (0,0) free-riders / area 63" — REFUTED: zone 24 = Adamantoise/Worm Hydra, and (0,0) has
   only {terrain, object, sea4}, all overridden.
3. "cached area from the save" — REFUTED: `status.id` refreshes per movement step.
4. **CONFIRMED: Grimhorn's bench** — its carried ground is **area 12 → zone 5** (records 44-57,
   topos 0/3/10/16/30/31/41 = scenes 174-209): topo-16/41 walkable bench ground rolls **Lizard
   Man/Skeleton (201-209), Axe Beak (177/180, 206-209), Sand Scorpion (174-180 — the owner's
   "serpion")**, Ironite in the records' alternate scene slots — mixed battle backgrounds per
   scene metadata. The mints' area-0 grass is separately LIVE for zone 0's Pythons (unobserved).
   Ragtime Mouse in the canopy = the stock forest special (any topo-37 worldwide) — kept, stock-lawful.

## 26.2 The fix — THE SAFE-ROAD AREA STAMP (area 14)

Every kit island's OPEN walkable ground is stamped **area 14 → zone 6**, whose only records are
topos 10/36 — a TABLE HOLE for every topograph our ground carries ({0,3,16,17,31,32,41,...}).
The stamp rule per vert-tangent: `event==0 AND topo∉{36,37,38} → area:=14` (area bits only; topo/
event/flags byte-preserved). The canopy (36-38) keeps **area 0 → zone 0**: Python/Goblin/Mu remain
the region's uniform encounter fauna. Event tiles untouched (ours stay area 0 — the probes'
invariant; the horseshoe carry's 270 STOCK event verts keep their carried area 12 — pre-existing,
⚠ flagged for a future audit: carried stock event tiles can summon dispatcher cases).

Area choice is cosmetically free: `WorldLocationText(area)`'s only gameplay caller is the Memoria
debug PlayerWindow title (ff9.cs:3750) — no player-facing surface reads tile area for naming.

**Scope**: 56 Terrain files per disc (112 total) across the junction (r16-19 c0-4), Tidefall's isle,
Larkspur's relief island, Sandreach (areas 49/50 were zone 18 — live rows for its topo-17 sand!),
Grimhorn's bench (the area-12 offender), Lamplight, and the R4 bench. 85,236 open-ground verts
stamped; 1,068 canopy verts kept area 0; 456 event verts byte-identical; full disc parity.
Probe: `probe_r3/probe_area14_stamp.py` — ALL CHECKS PASS; the ring's 5-site probe + ring closure
ALL PASS after the stamp. Write-set: 112 changed, 0 added/removed, all Terrain
(`probe_r3/md5_after_r4b.txt`).

## 26.3 Standing consequences

* **New mints/carves must re-run the stamp** (or inherit it once the kit's emitters default open
  ground to area 14 — a follow-up kit change deliberately NOT made now: it would break the island-E
  byte-identity nets; do it with fresh identity baselines).
* The DESIGN's law is rewritten: **THE TABLE IS THE LAW** — "open ground is the safe road" is an
  AUTHORED property (a table-hole area), not an engine gift.
* Encounter-bearing ground anywhere on kit land = stamp it area 0 (zone 0) topo 36-38, or (for
  bespoke fauna) the future `WorldEncounters.csv` engine seam.

## 26.4 Undo

Restore the 112 Terrain files from
`backups/r3-lamplight.20260726-r3lamplight/pre-area14-terrains/` (returns the encounter-exposed
state). Re-enter the overworld; no relaunch.

## 26.5 Re-playtest ask (owner) — no relaunch, re-enter the world

1. **Grimhorn's bench**: walk the same ground that fought you — several minutes. Expect ZERO
   encounters now.
2. **The R4 bench island**: open grass + hill — ZERO encounters; the north canopy still fights
   (Python/Goblin/Mu — and Ragtime Mouse may still quiz you: stock, welcome).
3. Any quay island + Lamplight: plates, entrances, ferry all unchanged.

---

# 27. R4c — s60: THE ENCOUNTER TABLE HOLE (engine) — **BUILT + DEPLOYED** (relaunch + re-test pending)

Run 2026-07-26, from the owner's §26.5 re-test: *"still getting battles on the grass. reading area
14 topo 0, Lindblum Plateau."* The area-14 stamp had LANDED (the debug title showing "Lindblum
Plateau" IS area 14's name) — the engine defeated it.

## 27.1 ROOT CAUSE — the one line never read: the lookup-miss fallthrough

`ff9.w_worldGetBattleScenePtr` (ff9.cs:9209) ends `return w_frameBattleScenePtr[i + useAlternate - 1]`
— on a (zone, topograph, fog) MISS it returns the zone slice's **LAST record**. An authored table
hole was impossible: area-14 topo-0 grass resolved to zone 6, matched nothing, and was handed
zone 6's final row (the Lindblum Plateau topo-36 brush set). §26's model was right about the lookup
and wrong about the miss path — the lesson: **read the no-match tail before betting on a hole.**

## 27.2 THE FIX — s60, two functional lines at the seam we own

`memoria-patches/s60-encounter-table-hole.patch`: the miss returns **null**; `SelectScene` returns
0 on null (= no battle — the contract `ProcessEncount` already honors). Stock blast radius censused
BEFORE authoring: exactly ONE spot map-wide exercises the fallthrough — 22 stray area-10 topo-0
tiles in blocks (20,14)/(21,14)/(22,14) (plains slivers inside the zone-4 mountain region, which in
stock fight rec 43's brush set there) — those become encounter-silent under s60; every other
walkable stock (zone, topograph, fog) triple has a real record, byte-censused. Also checked: no
zone's last record carries zero scenes (a data-only fix was impossible), and no benign fallthrough
exists anywhere.

## 27.3 Build + deploy (owner-approved after the classifier gate)

Pre-build full DLL backup **`20260726-162739`** (`py tools/restore_memoria_dll.py 20260726-162739`
reverts the whole engine). MSBuild clean; `Output\Assembly-CSharp.dll` == both deployed x64/x86
copies, sha256 `79935c1bfdbaafcf…`. ⚠ Build lesson (it failed for the owner first): from Git Bash,
MSBuild switches MUST be dash-style (`-t:Build -p:…`) — MSYS path-conversion mangles `/t:`/`/m`
into paths (`M:/`).

## 27.4 The complete encounter architecture, as now deployed

**THE TABLE IS THE LAW** — data half: open kit ground = area 14 (zone 6, a record hole for every
ground topo we carry; §26); canopy = area 0 (zone 0: Python/Goblin/Mu). Engine half: s60 makes the
hole real. Consequence for the kit: forked fields / the stock game are untouched except the 22
censused tiles; the ring + bench become exactly the ratified design — canopy fights, open ground
safe, Ragtime Mouse optional garnish.

## 27.5 Undo

`py tools/restore_memoria_dll.py 20260726-162739` (the engine) · §26.4 (the area stamp) ·
earlier layers per their own sections.

## 27.6 Re-test (owner) — RELAUNCH (the DLL), then:

1. The same grass that fought you (Grimhorn's bench + the R4 bench's open grass/hill): several
   minutes each — **zero encounters**.
2. The bench canopy still fights (Python/Goblin/Mu; Ragtime Mouse possible).
3. A stock sanity spot if convenient (e.g. any real plains): stock encounters unchanged.

---

# 28. R5 — THE SEA LANES + THE BOAT WAKES — **APPLIED** (hot; playtest pending)

Run 2026-07-26 ("go R5"). Both halves of the rung landed offline-verified.

## 28.1 R5a — the dormant boat: §20 was a DOMAIN mis-diagnosis; the original gate restored

THE ×256 DOMAIN LAW (the missing link §20 never traced): `WMActor.pos`'s SETTER (WMActor.cs:17-19)
writes `RealPosition * 256f` into the eb-visible `PosObj.pos[]` — **on the world map, `obj(uid).f[]`
reads are ×256 fixed point**, not world units (the §20 chain read the CAST but never the WRITER).
Everything re-resolves:

* the ORIGINAL relative gate (`|Δf| < 25600` = 100u ×256) was CORRECT all along;
* the §19-era quay boarding was the v1 float-parked boat legitimately in range — MOOR-HOME alone
  was the complete fix for the race (kept, untouched);
* §20's world-unit absolute window could never be true live (mooring f[0] = 125,952, not 492) =
  the dormant boat.

**The fix is a RESTORATION, not a new derivation** (honoring the §20-era directive — no new window
was derived, so no live capture was owed): entry-15 tag-1 grafted back from the pre-§20 backup
(`gui-workspace-improvements-277c74/backups/boat-rangegate.20260726`), per language from each live
file's own bytes (174 → 190 B), verified per language that ONLY that function changed and equals
the oracle body — the R3/R4-era dispatcher additions (case-61/65-68 triggers, the extended
func-0xB) all preserved. Source parity: `build_boat_world11.py`'s gate rewritten to the relative
form + `wu()`'s docstring now carries the law as a warning. Backup of the pre-restore state:
`backups/r3-lamplight.20260726-r3lamplight/world11-pre-r5/`.

## 28.2 R5b — THE SEA-LANE PROBE: the west arc is tile-proven sailable

The Blue Narciss legality mask decoded from TransportControls.csv: `limit0=39845888 / limit1=0` →
legal topographs exactly **{53, 54, 57}** (the bit convention validated by reproducing THE ENGINE
FOOT-WALK TABLE byte-exact from the Walking row — the mask oracle). `probe_r3/probe_sea_lane.py`
walks candidate passages at 8u sampling over the STACKED live meshes, with pure-ocean cells
resolved to the runtime `SeaBlockPrefab` (generic deep sea, topo 57 — cells with no block files at
all; the probe's first run mis-scored those as holes, plus started on Ashvale's shore and ran its
final legs onto the horseshoe's own ground — three instrument errors, all corrected and recorded).

**VERDICT: the NORTH passage — Ashvale's west shore → the x=0/1536 wrap → north of Lamplight →
the west channel at the horseshoe — is FULLY SAILABLE, 47/47 samples.** The south passage's final
leg clips the horseshoe's SE ground (topo 16/17 at x 1276-1293): route north or berth wider.
Output: `probe_r3/probe_sea_lane_output.txt`.

## 28.3 Undo

Restore the 7 files from `world11-pre-r5/` (returns the dormant §20 gate). The lane probe wrote
nothing.

## 28.4 Playtest ask (owner) — no relaunch, re-enter the world

1. **Board at the islet**: stand by the beached crimson hull (or the dock) and press Confirm —
   boarding fires again. Dismount: you land on the dock, the boat re-moors.
2. **Confirm at each quay / in the open**: no boat hijack (moor-home keeps the 100u radius at the
   islet, 125u+ from everything).
3. **The voyage (the design's payoff, first sail):** board and sail WEST from Ashvale — through
   the wrap, keep Lamplight to your south (its plate on the way past, kupo), into the channel
   between Lamplight and the horseshoe. That is the design's "only block-proven voyage in the
   world", now tile-proven and — with a working boat — actually sailable.

---

# 29. R5c — THE STOCK BOARDING UX (plate + engine-legality dismount + the beachable fringe) — **APPLIED** (hot; playtest pending)

Run 2026-07-26, from the owner's §28.4 playtest: *"dismounting the boat always puts me back on the
island in the same spot and puts the boat back on the beach. also, it doesn't show a ? or ! bubble
when approaching the boat (although I'm not sure what stock behavior is)."* Both reports were the
scripted v1.1 state, not regressions — moor-home + the fixed dock snap were the §19 anti-race
stopgap, and the missing prompt was the study's own deferred "proper boarding UX... is R5" note.
This rung retires the stopgap with the REAL stock protocol, decoded end to end.

## 29.1 What stock actually does (the decode)

* **The prompt IS stock**: WORLD03's cell summoner (entry-0 tag 38809) arms `Byte[39]=92` — the
  Blue Narciss's own nameplate case — when you approach the parked boat on foot; the case machine
  draws the plate + "Enter with (X)". Boarding requests `Map.Byte[37]=12` into entry 2's vehicle
  machine (board = mode 7 + tag-21 pair).
* **Dismount is a SCRIPT-side request against an ENGINE legality service**: entry 3 tag 1 @L185 —
  Cancel while sailing → `RunWorldCode(28,0)` = `ff9.w_movementGetGetoff` (mode 7: the tile AHEAD
  of the hull must read **topograph 53** — beach-front water — then a raycast sweep around the hull
  finds FOOT-walkable ground) → answer in `SYSVAR[195..197]` (y==10000 = the refuse sentinel →
  silently nothing). On success the machine's arm 13 runs the boat's tag 22, which **saves the
  boat's LIVE position into the parked record** — stock parks WHERE IT FLOATS — and the player
  lands at the engine's point (entry 12 tag 22 reads the staged coords).

## 29.2 The fix — three pieces

**(a) The boat loop v2** (`build_boat_world11.py`, entry-15 tag-1 + entry-14 tag-60, all 7
languages, +38 B/file): on-foot approach within 40u (tightened from 100u; stock boards on hull
contact) self-summons **case 69** — the ring's next virgin case — so the plate reads "Crimson
Narciss" ("?" until first boarding; the explored bit = the kit word 2006 bit 4, written on the
board branch like every ring entrance). Board = Confirm while THAT plate is armed
(`Byte[24]==169`) → the case machine arbitrates every Confirm press: a quay plate and the boat
plate can never both take one press — the §19 race is dead by construction, so MOOR-HOME IS
RETIRED. Dismount = Confirm|Cancel while sailing → `RunWorldCode(28,0)` + the sentinel check →
the anchor snaps to `SYSVAR[195..197]` (the engine's landing point, entry-14 tag-60 v2) and THE
BOAT PARKS WHERE IT FLOATS. Write-set proven per language: exactly {entry-15 tag-1, entry-14
tag-60} changed (scratch verify), backups `backups/custom-vehicle/*.20260726-204224`.

**(b) The name**: `marker_renames.toml` locid 68 = "Crimson Narciss" (split[69]), deployed to all
7 languages' 68.mes.

**(c) THE BEACHABLE FRINGE** (`stamp_beach_fringe.py`): the landing probe
(`probe_r3/probe_landings.py`) proved the getoff gate could NEVER pass at any ring island — the
mints/carries built GROUND only, so pure Sea4 **topo-57 deep water laps directly at every sand
line**; only the stock (7,17) islet had the graded topo-53 fringe (stock's grammar: Sea1/Sea2
carry 53 at the sand). Fix under the coast-mosaic law "navigation and render are SEPARABLE (topo
= tangent.x, look = UV+material)": near-shore Sea4 tris (all-57, centroid ≤16u from island
ground) restamped **57 → 53, topo bits only** — 15,018 verts / 5,006 tris across 26 Sea4 files
(×2 discs). Zero geometry/UV/material change; the real Sea1/Sea2 shallow-LOOK ring stays a
separate fidelity arc. Integrity probe `probe_r3/probe_beach_fringe.py`: every diff is a
tangent.x 57→53 with event/area/flags preserved, everything else byte-identical, disc parity
holds, the north lane stays FULLY SAILABLE. Landing sites now exist at ALL SEVEN shores
(`probe_landings_output.txt`).

## 29.3 Known persistence gap (deliberate)

Entry-15's Init still re-moors the boat at BOAT_SPAWN on every world (re)load — the parked spot
survives the session, not a save or a field round-trip (enter a quay field and return = the boat
teleports home; the ferry keeps you un-stranded). Stock persists via Global[74..82], which real
saves corrupt for us (proven 2026-07-22); kit-allocated parked-position storage is a later rung.

## 29.4 Undo

1. Boat loop: restore the 7 files from `backups/custom-vehicle/*.20260726-204224` (returns v1.1
   moor-home + no prompt).
2. Fringe: restore the 26×2 Sea4 files from
   `backups/r3-lamplight.20260726-r3lamplight/pre-fringe-sea4/` (returns the unlandable coasts).
3. Name: remove the locid-68 entry from `marker_renames.toml` and redeploy (or leave — an unused
   name row is inert).

## 29.5 Playtest ask (owner) — re-enter the world (the name may want a relaunch)

1. **The prompt**: walk up to the beached crimson hull — the plate appears ("?" first time,
   "Crimson Narciss" after you've boarded once). Confirm while it shows = board. If the plate
   text shows "  ?  " even after boarding, relaunch once (the 68.mes table content is fresh).
2. **The landing**: sail to any ring island, nose the bow at the beach, press Confirm (or
   Cancel — stock's key): you step ashore AT THAT SHORE and the boat stays beached beside you.
   In open water the same press does nothing (the engine sentinel refusing — stock behavior).
3. **The voyage, full loop**: board at the islet → sail the north passage west from Ashvale →
   land ON Lamplight's shore, walk to the tower, come back, re-board where you left the boat →
   sail into the horseshoe channel and land on the horseshoe. That is the ring's first true
   port-to-port sail.

---

# 30. R5d — THE SAIL-THROUGH SEAL (the coast-nav stamp v2) — **APPLIED** (hot; playtest pending)

Run 2026-07-26, from the owner's R5c playtest: *"i'm able to board the boat and get off at any
beach i please - but found a major issue. for any of the islands we've created/forked, the boat
is able to sail right through the cliffs. this doesn't happen on the stock landmasses."*

## 30.1 Root cause — full-cell ocean under kit land

`w_movementRoundCheck` (ff9.cs:5633) legality = raycast the NEXT position via `w_cellHit` WITH
THE ACTOR'S TRI CACHE, then test the hit topo against the vehicle mask. Sailing, the cache holds
water tris — so at an under-land position the probe hits the kit cell's FULL-CELL ocean mesh
underneath the terrain (topo 57, and R5c's fringe had even made near-shore under-land water 53 —
both in the Narciss mask) → LEGAL → the hull crosses the cliff. Stock never has water under land
(the conforming-waterline grammar): the probe there hits rock/land (mask-illegal) or nothing.
Stock survey (cliff blocks (9,17)/(10,18)/(3,13)/(16,17) + beach (7,17)): **topo 53 fronts
beaches ONLY — never cliffs**; cliff-front water is 54/55/56/57 (stock blocks boats at cliffs by
GEOMETRY, not topo).

## 30.2 The fix — THE COAST NAVIGATION STAMP (three classes, every deployed sea cell)

`stamp_coast_nav.py` (supersedes stamp_beach_fringe.py's hand boxes — which had under-covered:
the junction landmass spans blocks (0-4,16-19), the R4 bench sits at (1-2,1-3)): every water tri
in every deployed kit Sea1..Sea5 override re-derives its NAVIGATION class, topo bits only:

* under HIGH ground (any of centroid+3 corners tops out on ground y≥1.5u) → **56 KEEL-BLOCK**
  (water-class, outside the Narciss mask, foot-illegal — the interior seals);
* under LOW ground / open water ≤16u from low ground → **53 beach-front** (landable);
* open water ≤16u from only-high ground → **54 cliff-front** (sailable up to the rock, NOT
  landable — kills the cliff-face dismount beam-up exploit R5c's 53-everywhere had left);
* open sea → unchanged.

Shared verts resolve **KEEL > BEACH > CLIFF** (round 1 ran beach-first and left 23 first-vert
holes in the seal; the flip's cost — a keel-adjacent beach tri can refuse a landing at that exact
spot — is bounded and measured by the landing probe). Two passes total: 38,970 + 3,189 verts
across **64 sea files ×2 discs**.

**Verification** (`probe_r3/probe_coast_nav.py`, output archived): THE SEAL — 4,541 high-ground
samples across all deployed sea cells, **0 sail-through leaks** (every water tri under high
ground reads outside {53,54,57}); byte integrity — all 64 files differ only in tangent.x topo
bits, old∈{53..57} new∈{53,54,56}, disc parity holds; landings — all seven shores keep healthy
53 sites (16-63 samples each); the north lane stays 47/47 sailable.

## 30.3 Undo

Restore the 64×2 sea files from
`backups/r3-lamplight.20260726-r3lamplight/pre-coastnav-sea/` (returns the sail-through state
with R5c's fringe); the deeper `pre-fringe-sea4/` returns the pre-R5c unlandable coasts.

## 30.4 Playtest ask (owner) — no relaunch, re-enter the world

1. **The seal**: sail straight at a kit cliff (Lamplight's outline, the horseshoe walls, the
   junction's high coast) — the boat now stops at the rock like stock, and cannot cross any
   island.
2. **Landings still work**: beaches still land (plate → Confirm ashore); a cliff face refuses
   (nothing happens — and no more beaming up cliff tops).
3. **The lanes**: the north voyage unchanged.

---

# 31. R5e — THE STANDOFF BELT + THE COMPATIBILITY LAW (coast-nav v2.3) — **APPLIED** (hot; playtest pending)

Run 2026-07-26, from the owner's R5d playtest (with screenshots): *"it's a little off, i can get
way closer to the 'inside' of the island on the forks than i can on actual cliffs... might be a
tricky one."* It was. Four instrument/model rounds:

## 31.1 What the rounds found

* **THE ORIGIN INSTRUMENT BUG** (the big one): `block_world_origin` returns the WEST,NORTH
  corner — a cell spans z DOWNWARD. Every origin-based scan (the stamp's ground lists, the seal
  probe's grid) had walked `oz + zi` — the NEIGHBOR ROW. The §30 "0 leaks" was measured on a
  displaced grid, and the stamp's open-water classes were derived against the wrong strip
  (v1's box-based 53s masked it at the landing sites). All scans corrected (`oz - zi`); the
  seal re-established on the TRUE grid.
* **KIT ISLANDS ARE PLATEAU ISLES**: transects (Ashvale vs the stock (7,17) islet) show every
  kit shore is a ~2u low trim then a 3.0u wall — there are NO graded aprons anywhere, so no
  geometric locale rule can split "beach" from "cliff" (each attempt killed every landing:
  locale 6u/4.5u/3u-on-2u-grid all zeroed the landing probe). Under stock grammar these are
  unlandable cliff isles; land-anywhere is the ring's confirmed-fun property.
* **THE COMPATIBILITY LAW**: the getoff GATE reads the tile UNDER THE HULL
  (`w_movementRoundCheck` at speed 0) and the landing SWEEP reaches at most
  `S(radius·8/4) = S(1120) = 4.375u` (Narciss `radius=560`, `ff9.S = /256`). A standoff belt
  wider than that makes a shore UNLANDABLE. Standoff and landing are compatible only under
  4.375u.

## 31.2 The v2.3 class map (deployed)

* under-land, raw ground ≥1.5u OR high-LOCALE (≥2u within 3u — a wall's waterline base or trim)
  → **56 KEEL** (the seal; raw-OR-locale closed a 1.8u-bank leak);
* open water hugging a HIGH-locale front (exact tri distance ≤ **3.5u**) → **55 THE STANDOFF
  BELT** — the widest standoff compatible with landing (3.5 < 4.375);
* all other water ≤16u of ANY ground → **53** (land ANYWHERE — the 54 cliff-front class is
  GONE: wall dismounts land on the plateau top, the behavior the owner enjoyed);
* shared verts: KEEL > BEACH > BELT (landing survival outranks the last half-tri of standoff).

Verification (`probe_r3/probe_coast_nav.py`, archived): SEAL 5,551 true-grid samples **0
leaks** · STANDOFF 332 wall-hug samples **0 legal** · integrity 65 files topo-bits-only ·
landings at ALL SEVEN shores (10-59 sites) · the north lane FULLY SAILABLE (the wrap crossing
moved to z≈-1165: the junction's west wall bulges to the wrap column near z-1152..-1157 and its
new belt closes the old crossing).

## 31.3 Honest residual

The hull is longer than 2×3.5u — at a tall vertical face the BOW may still overlap the rock a
little (the deep burial is gone). More padding is possible ONLY by sacrificing wall dismounts
(BELT_R up to ~8, landings then only at true aprons — which kit islands don't have; widening
aprons is a mesh job for a future rung). 3.5u is the ceiling under THE COMPATIBILITY LAW.

## 31.4 Undo

Same as §30.3 — `pre-coastnav-sea/` returns the pre-R5d state (the backups predate v2, so one
restore undoes v2 through v2.3).

## 31.5 Playtest ask (owner) — no relaunch, re-enter the world

1. Sail at the same fork cliffs as the screenshots: the hull should stop ~a half-hull off the
   face (bow tip near, not buried). Compare feel vs stock.
2. Land everywhere you did before — beaches AND walls (wall dismounts hop you up onto the
   plateau; that is intended, it is the ring's land-anywhere property).
3. The interior seal + the north voyage: unchanged.

## 31.6 ★ PLAYTEST-CONFIRMED (owner, 2026-07-26): "that did the trick"

The 3.5u standoff holds at the fork cliffs, landings stay everywhere, the seal and the voyage
stand. With this, THE RING'S RATIFIED BOARD IS CLOSED IN-GAME: R1 (hub/hall/ferry) · R2 (the
quays) · R3 (Lamplight + the virgin-case plates) · R4 (forest + the encounter table-hole chain)
· R5 (the boat: wake, plate, engine landings, the interior seal, the standoff) — all
owner-confirmed.
