# Actor shadows on kit-built fields

**Status:** ★ rung 0 PASSED in-game (harness, bench 30920). Every actor casts the stock shadow; the opt-out
actor casts none. ★ rung 1 PASSED in-game (harness, bench 30930). An `--editable` fork now ships its donor's
MCF, so its grafted donor objects cast the stock shadow and take the room's tint. A reshaped walkmesh keeps
its per-floor lights. ★ The SET PIECES follow-up PASSED in-game (harness, bench 30921): props follow stock's
own per-model treatment, chests and the save moogle cast, held props never do (see "Set pieces" below).

## The defect

Actors on a kit-synthesized field had no blob shadow. It showed up by chance in the walkmesh-sensor rung-0
frame (bench 30910, `.harness-runs/20260923-094949-bgi-rung0/shots/1-spawn.png`): Zidane and two
`GEO_NPC_F0_CSO` NPCs stand on the checkerboard with nothing under them.

## The mechanism (source-read, then measured)

The first hypothesis was that the kit never emits `SetShadowSize` (0x81). That turned out to be half right.

- `new FF9Shadow()` has `xScale = zScale = 0` and `amp = 0` (`Global/ff9/FF9Shadow.2.cs`). It is created at
  `SetModel` (`EventEngine.DoEventCode.cs:1122`).
- `EventEngine.SetRenderer` copies `(xScale, 1, zScale)` into the shadow quad's `localScale` whenever
  `needUpdate || flag1`. `flag1` means "the object flags changed since last frame", which is true on the
  actor's first render. So the default zero is applied right away and the shadow quad has zero width.
- **Stock scripts almost never set shadows.** Across 817 exported scripts there are 16 `SetShadowSize` and 6
  `SetShadowAmplifier` calls. The shadows come from the field's **MapConfigData** instead
  (`CommonAsset/MapConfigData/<EVT>.bytes`). Every frame, `fldmcf.ff9fieldMCFService` calls
  `FF9ShadowSetAmpField(uid, shadowI << 3)` and `FF9ShadowSetScaleField(uid, shadowR, shadowR)` for each
  actor, using the per-model `DMSMapChar` row (or the `0xFFFF` default row) plus the floor's `DMSMapLight`.
- All 818 shipping fields ship an MCF. A synthesized field ships none, so `mcfPtr == null` and the service
  returns at its first line. Only a native fork carries one, copied verbatim from its donor through
  `[field] mapconfig`.

## The fix (`ff9mapkit/content/shadow.py`)

The build emits the two script ops that call the same engine functions, with values from a census of the
real MCFs:

- **Census** (`_regen_shadowparams.py` → `_shadowparams.py`). Each shipping field votes once per model it
  shows, with the value the engine actually applies: the model's row, else the default row, plus the default
  light. Per model the table takes the modal `shadowR` (size, which follows the model: Zidane 9, Garnet 8,
  Steiner 11, Quina 16, moogle 6) and the modal `shadowI` (intensity, which follows the room's light and is
  mostly 3-4). A model seen in fewer than 5 fields falls back to the overall intensity. Floor-specific lights
  add 0 in 886 of 1469 cases.
- **Shape**: the ops are `SetShadowSize(s, s)` then `SetShadowAmplifier(i << 3)`, the byte order stock uses
  (field 207: `81 00 20 20 85 00 C0`). On an NPC they sit at the Init tail, running straight into its RETURN
  (field 576: `81 00 05 05 04`). On the player they sit right after `SetHeadFocusMask` (field 451's Zidane).
- **Scope**: the player and every `[[npc]]`, which includes behavior units. The ops are emitted only when the
  field ships no MCF. Verbatim and native forks build byte-identically.
- **Opt-out / override**: `shadow = false`, or `shadow = { size, intensity }`, on `[player]` or an `[[npc]]`.

## Byte identity

Each actor gains 7 bytes and nothing else changes. `tests/test_shadow.py` builds with shadows on and with them
forced off, then compares decompiled source with labels renumbered per function. It does this for a synthetic
field and for the four buildable bundled examples. With shadows forced off, the hut rebuilds to the old golden
hash exactly.

## Rung 0 — in-game (bench 30920, `rung0_shadow.py`)

One frame holds every case: the player, `stock` and the behavior unit `rover` at census values, `big` at
`{16, 8}`, and `none` with `shadow = false` as the in-frame negative control.

The reference is a **control run**: `bench/shadow0_control.field.toml` is the same bench with every actor at
`shadow = false`, which is what every kit field shipped before the fix. It was deployed to the same slot and
shot at the same moments. `measure_shadows.py` scores only pixels that are floor in both frames, inside a box
at each actor's feet. Runs are archived in the main repo's `.harness-runs/`: `20260923-104225-shadow-rung0-on`,
`20260923-104149-shadow-rung0-control`, and `20260923-103915-shadow-rung0` (a first shadows-on run, used as a
repeat).

| actor | ops in the deployed .eb | floor darkened >=5% | luminance on/control |
|---|---|---|---|
| player (Zidane, census) | SetShadowSize(9, 9) + SetShadowAmplifier(32) | 18.4% | 0.958 |
| stock (CSO, census) | (9, 9) + 24 | 10.4% | 0.981 |
| rover (behavior unit, census) | (9, 9) + 24 | 14.5% | 0.975 |
| big (CSO, `{16, 8}`) | (16, 16) + 64 | 41.1% | 0.844 |
| **none** (`shadow = false`) | none | **1.1%** | **0.999** |

- **Calibration:** control scored against itself reads exactly 1.000 / 0.0%. The repeat run agrees with the
  table to within 0.3 points on every row.
- **By eye:** each shadow is a soft dark blob centred under the feet. `big` is clearly larger and darker. The
  rover's blob follows it through the wander in shots 2 and 3.
- **Exceptions:** no exception passes through a shadow path (`ff9shadow` / `DoEventCode` / `SetRenderer` /
  `fldmcf`) in either log. `FieldMapActorController.MovePC` throws a NullReferenceException 26 times in BOTH
  the shadows-on run and the control run. It also appears 28-29 times in the pre-fix bgi runs on bench 30910,
  so it predates this change and is unrelated to it (not yet diagnosed; see follow-ups).

Census shadows are subtle on purpose. The intensity comes from stock rooms (mostly 3-4), so a 9-size shadow
darkens its footprint by about 5-10%. Whether that reads well on painted art is the owner's call. The
`intensity` override is the lever if it doesn't.

## Rung 1 — an `--editable` fork's grafted objects (bench 30930)

**The gap.** An `import --editable` fork is a synth build that shipped no MCF, and only `--native` wrote one. Its
player got the rung-0 script shadow, but the donor objects it carries (`[[object]]` grafts, content/object.py) are
not `[[npc]]`s. They cast no shadow, and nothing tinted any model.

**The choice: ship the donor MCF (a), not script ops in the grafted Inits (b).** It rests on how the engine reads
the MCF (`fldmcf.cs`):

- The per-model row is looked up by **model id** (`ff9fieldMCFGetCharByID(mcf, actor.model)` matches `geoNo`),
  not by object slot. A grafted object keeps its model, so it gets its own donor row. (The object-carry memory's
  claim that the rows key on donor object indices was wrong.)
- A model with no row reads the `0xFFFF` default row through `.Value`, which would throw every frame if the row
  were absent. The census found it present in all 818 shipping MCFs, so a kit `[[npc]]` of any model is safe.
- The service sets shadow AND tint (`(clr + light) << 3`) from the actor's floor light, re-applied whenever the
  floor changes. (b) could set one static shadow per object, with census values instead of the donor's, no tint
  and no per-floor change. It would also rewrite the verbatim-grafted entries that object carry keeps
  byte-identical.
- The MCF loads by the running event name for any scene type (`HonoluluFieldMain`), so the build now ships it
  from any branch (`build.mapconfig_bytes`), not only the native one.

**Do the per-floor lights still key correctly on a reshaped walkmesh?** Lights match `light.floor[i] & 255`
against `FieldMapActorController.activeFloor`, which is the BGI floor index.

- `[walkmesh] bgi` (what the importer writes) ships the donor walkmesh verbatim, so every index is the donor's.
- `[walkmesh] obj` rebuilds through `bgi.build`, which numbers floors in first-seen face order. The importer's
  re-export writes them in first-seen tri order, and the census shows the unedited round-trip is the identity on
  all 816 shipping walkmeshes. In 417 fields a floor light differs from the default, so the keying matters.
- An edit that deletes or reorders an `o floor_N` block renumbers the floors. The build re-keys the MCF's
  per-floor lights through the `floor_<donor index>` names that both exporters write (the importer and the
  Blender add-on's `mesh_to_ff9_obj`). A floor with no donor name takes the default light. A lit donor floor
  that is gone is reported.

**Byte identity.** Field 122 imported in all three modes, built at HEAD vs with this change: native and verbatim
trees are identical. The editable tree changes by exactly the MCF (equal to the donor's) plus the player's 7
retired shadow bytes per language. `tests/test_fork_mapconfig.py` pins the on/off invariant on an authored fork
with a grafted object, and was mutation-checked (four breaks, each caught).

**In-game** (`rung1_editable_mcf.py`, `rung1_variants.py`, `measure_rung1.py`; the bench is
`import 1607 --editable --name MCF_KTN --id 30930`, SE-derived, regenerated under the gitignored `imported/`).
Runs are archived in the main repo's `.harness-runs/*-mcf-rung1-*`. Every run passed its preflight: the deployed
MCF and `.eb` are the variant's, and no exception passed through `fldmcf`/`ff9shadow`/`SetRenderer`.

| variant | what it is | result |
|---|---|---|
| on | the import (ships the MCF) | carried moogles shadowed + tinted |
| control | on minus `mapconfig` (every editable fork before) | carried models bright, no shadow |
| empty | control minus every carried object | the background reference |

`measure_rung1.py objects on control empty`:

- **Shadow:** 721 background pixels that ON darkens to about 16% of the art's luminance, a clean ellipse under
  the lower-right moogle.
- **Calibration:** 0 such pixels in CONTROL.
- **Tint:** the carried models render at (0.735, 0.658, 0.595) of their pre-fix brightness, the room's warm light.

The first reshape (floors 1↔3) was a **null**: no in-view actor stands on either floor, and the un-keyed control
looked the same as the keyed one. It was an instrument blind to the defect, not a pass. The probe moved to the
player, spawned in view on donor floor 0 only. Floor 0's light is clr -1 / shadowI -3; floor 3's is clr -3 / -5.

| probe variant | Zidane's mean RGB / probe |
|---|---|
| probe, second shot (noise floor) | (0.999, 0.999, 0.999) |
| reshape: `.obj` floors 3,1,2,0,…, re-keyed | (1.002, 1.002, 1.002) |
| reshape-nokey: same, donor MCF shipped verbatim | (0.867, 0.866, 0.845) |
| predicted for the mis-key, `(15-3)/(15-1), (13-3)/(13-1)` | (0.857, 0.857, 0.833) |

`FieldMapActorController.MovePC` throws its NullReferenceException 26-28 times in every variant, EMPTY included:
it is unrelated to the MCF.

## Set pieces — props, chests, the save point (bench 30921, `set_pieces_shadow.py`)

### The census said the obvious design was wrong

"Stock MCFs shadow accessory models" is true of the MCF and false of the game. The MCF service gives EVERY
actor a shadow, but an object's Init can `DisableShadow` (0x80: char attr bit 16, and `SetRenderer` turns
the quad's renderer off), and stock does exactly that to most set dressing. Over all 817 scripts, one row per
object entry with a literal Init `SetModel`:

| class | objects | what stock does to the shadow |
|---|---|---|
| held (an `AttachObject` target) | 140 in 95 fields | disabled on 139 (125 in the Init) |
| chests (the four TBX models) | 224 | kept on 221; 218 have their own MCF row |
| other free-standing accessories | 556 | **disabled in the Init on 476** (tent 66/67, save book 58/58, letter 57/57, cactus 30/30); kept by the cask 19/19, the aircab, TRK, the fish |
| save moogles (own a `Menu(4,0)`) | 58 | kept on 58 -- no Init op; only `DisableShadow`/`EnableShadow` pairs around hops (the act's tag 3 on all 58, tag 1 on 3) |

So the prop rule has to be per model, and it has to come from stock's script. The regen now bakes a second
table, `_shadowparams.STOCK_CASTS`. A free-standing object votes "disabled" when a `DisableShadow` block
**dominates every exit** of its Init (`eb.cfg.FuncFlow`, not "an 0x80 anywhere"). A tie counts as disabled.
The dominator rule and the any-0x80 rule disagree on one model only (`GEO_SUB_F0_KUW`). The result: 235 of
327 models cast, and 16 of the 84 accessory models do. A model no stock object shows standing free casts none
(`PROP_DEFAULT_CASTS`, the accessory majority).

Why a held item must not cast, beyond the vote: `FieldMapActor.GetShadowCurrentPos` takes the quad's x/z from
the root bone's world position but its HEIGHT from `transform.localPosition`, which for an attached object is
its bone-local offset. Memoria carries hotfixes for exactly this class (the Synthesist's sword, the
pickaxes, Dante's glass).

### The rule

- `[[prop]]` casts when `STOCK_CASTS` says stock's objects of that model do (absent key), or when the author
  says so (`true` / a table); `false` = none. A composite applies an explicit value to every part; absent,
  each part follows its own model (the `save_point` composite's moogle casts, its book does not).
- A held prop (`attach_to`, `[[npc]] holds`) never casts. `inject_prop` drops the value, and `shadow = true`
  on one is a validate error.
- `[[chest]]` casts with the `[[npc]]` semantics (every TBX model casts).
- The save point's moogle casts (census `(6, 2)`), at its Init tail after the reveal/act preloads. Its
  barrel_pop cask casts by the prop rule. `[[savepoint]] shadow = false` darkens both; a table sizes the moogle.
  The act's book + feather keep their donor `DisableShadow` and get no ops.
- Same shape everywhere: `81 00 RR RR 85 00 AA` straight into the Init's RETURN. Only when the field ships no
  MCF (`build._casts_stock_shadows`).

### In-game (harness, bench 30921, against a same-bench control)

`bench/set_pieces.field.toml`: row A has a cask prop, a cactus (stock-dark), the same cactus with
`shadow = true`, and a chest. Row B has an instant save moogle, an NPC holding a cup, and a barrel_pop save
point. The control, `bench/set_pieces_control.field.toml`, puts `shadow = false` on every set piece: exactly
their pre-change bytes. The player and the NPC keep their rung-0 shadows in both builds.

The field camera FOLLOWS the player (the canvas is taller than the screen), so only the spawn frame is
pixel-comparable between runs. The spawn sits between the rows to frame both. Runs are archived in the main
repo's `.harness-runs/`: `20260923-112310-shadow-rung1-on`, `-112430-shadow-rung1-control`,
`-112656-shadow-rung1-caskdiag`. All three passed 19/19.

| actor | deployed ops | darkened >=5% | luminance on/control |
|---|---|---|---|
| cactus, `shadow = true` | (8, 8) + 32 | 25.8% | 0.935 |
| chest (TBX) | (10, 10) + 32 | 12.1% | 0.982 |
| instant save moogle | (6, 6) + 16 | 12.4% | 0.982 |
| **cactus** (stock-dark) | none | **0.0%** | **1.000** |
| player / holder NPC (unchanged by this change) | rung-0 ops, both builds | 0.0% / 0.4% | 1.000 / 1.000 |
| cask prop / barrel_pop cask | (11, 11) + 40 | 0.0% / 0.0% | 1.000 / 1.000 |

- **The casks, calibrated.** At census size the quad is 154 x 132u, and the barrel's own footprint is about
  380u across. So the blob is drawn entirely underneath it, as stock's casks' are (their MCF sizes run 10-18).
  To tell "hidden" from "the op did nothing on this object", the shadows-on `.eb` was byte-patched in place:
  only the two casks' `81 00 0B 0B` became `81 00 28 28`. That calibration run reads 0.564 / 77.4% (cask
  prop) and 0.643 / 63.7% (barrel_pop cask), with a wide halo around both. The ops are live on both Init
  paths; at census size stock's look is "no visible blob".
- **Repeatability:** the calibration run reproduces the census run's unaffected rows exactly (0.935 / 0.982 /
  0.982). Control scored against itself reads 1.000 / 0.0%.
- **The barrel_pop reveal still runs** with the 7 new bytes in both the moogle's and the cask's Init. Pressing
  the cask takes control and hands it back (its handshake poll). The zone then opens the menu, and its gate
  passes only after the moogle's pop arm wrote OUT. Cancel returns control. The popped moogle stands on the
  cask; its shadow on the cask top is not distinguishable by eye and not measured (the box scores floor
  pixels only).
- **Exceptions:** none through a shadow path. `FieldMapActorController.MovePC` throws its pre-existing
  NullReferenceException 26 times in both the shadows-on and control runs (24 in the calibration run).
- **Not exercised in-game:** the save act itself (its verbatim `DisableShadow`/`EnableShadow` hop pair).
  Offline, the book + feather keep `DisableShadow` and the moogle's ops sit ahead of the act body.

## Follow-ups (not in this change)

- `[[npc]]` still takes the census shadow for every model. `STOCK_CASTS` shows 23 non-accessory models whose
  stock objects mostly `DisableShadow` in their Init: chocobos (`GEO_NPC_F0_CCB` 32/43), frogs, tadpoles,
  several monsters. An NPC of those models casts a shadow stock never shows. The same per-model rule could
  apply, but it changes rung 0's semantics and needs its own in-game check.
- On a field that ships MapConfigData (a native fork, and since rung 1 an `--editable` one), a held prop gets
  the MCF's shadow, its height taken from the bone-local offset. Stock would `DisableShadow` it. The kit
  emits nothing on an MCF field by design.
- The pre-existing `FieldMapActorController.MovePC` NullReferenceException, about 26 per run on the
  checkerboard benches and on the 1607 fork (EMPTY included), with and without shadows or an MCF.
- A plain `import` (BG-borrow) carries objects too and ships no MCF: the same gap. Its walkmesh is the borrowed
  donor's, so the lights would key exactly.
- `walkmesh.links.toml` seams are keyed on donor floor numbers too (`apply_seams` looks up `(floor, edge)` on the
  rebuilt mesh), so a renumbering reshape drops them (2 of 14 on the 1607 swap). `obj_built_floor_donors` gives
  the map that would fix it.
- ~~`deploy_field.py` prints "TEXT OVERWRITES VANILLA" for a fork on its donor's real block even when the build
  ships no `.mes` (an editable fork without text carry). That fork only reads the block.~~ Fixed: the warning
  now fires only when the deploy copies a `.mes` for the block (`check_text_block_shadow(writes_mes=)`).
