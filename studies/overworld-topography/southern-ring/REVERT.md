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
