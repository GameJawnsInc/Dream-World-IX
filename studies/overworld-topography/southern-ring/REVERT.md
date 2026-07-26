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
