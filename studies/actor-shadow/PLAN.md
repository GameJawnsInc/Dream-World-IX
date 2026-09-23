# Actor shadows on kit-built fields

**Status:** ★ rung 0 PASSED in-game (harness, bench 30920). Every actor casts the stock shadow; the opt-out
actor casts none.

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

## Follow-ups (not in this change)

- `[[prop]]`, `[[chest]]` and the save-point moogle still cast no shadow. Stock gives accessory models one
  (the chest `GEO_ACC_F0_TBX` is `(10-11, 4)`), but held props must not get one. That needs its own design.
- An `--editable` fork's grafted donor objects still cast none: the fork ships no MCF, and the objects are not
  `[[npc]]`s.
- The pre-existing `FieldMapActorController.MovePC` NullReferenceException, about 26 per run on the
  checkerboard benches, both with and without shadows.
