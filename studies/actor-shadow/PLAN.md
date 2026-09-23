# Actor shadows on kit-built fields

**Status:** ★ rung 0 PASSED in-game (harness, bench 30920). Every actor casts the stock shadow; the opt-out
actor casts none. ★ rung 1 PASSED in-game (harness, bench 30930). An `--editable` fork now ships its donor's
MCF, so its grafted donor objects cast the stock shadow and take the room's tint. A reshaped walkmesh keeps
its per-floor lights. ★ The SET PIECES follow-up PASSED in-game (harness, bench 30921): props follow stock's
own per-model treatment, chests and the save moogle cast, held props never do (see "Set pieces" below).
★ rung 2 PASSED in-game (harness, bench 30935). A plain (BG-borrow) `import` now ships its donor's MCF too,
so its grafted donor objects are shadowed and tinted exactly as the editable fork's are.
★ rung 3 PASSED in-game (harness, bench 30936). On a field that ships an MCF, a prop that must not cast (held,
stock-dark, or `shadow = false`) gets stock's `DisableShadow`, so the MCF no longer shadows it.
★ rung 4 PASSED in-game (harness, bench 30937). On an MCF field `shadow = false` switches off the player, an
`[[npc]]`, a `[[chest]]` and a `[[savepoint]]` too, and the player's stays off after a jump.
★ The INTENSITY WRAP is proven in-game (harness, bench 30922). An authored intensity of 16-31 draws as 0-15,
so the authored range is now capped at 15 (see "The intensity wrap" below).

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

## Rung 2 — a plain (BG-borrow) `import`'s grafted objects (bench 30935)

**The gap.** A plain `import` forks an area>=10 field as a BG-borrow: the engine renders the donor's own art,
walkmesh and camera while it runs the fork's script. It carries the donor's objects through the same
`_content_for_import` as `--editable`, but `write_field_project` wrote no MCF. Its grafted `[[object]]`s cast
no shadow and rendered bright and untinted, as the editable fork's did before rung 1.

**The fix.** `write_field_project` writes `mapconfig.bytes` + `[field] mapconfig`, mirroring
`write_editable_project`. Since rung 1 the build ships the MCF from any scene type. The MCF loads by the
fork's running event name (`HonoluluFieldMain`), whatever scene it borrows. Two consequences:

- **No re-key.** A borrow ships no walkmesh: the engine runs it on the donor's own `.bgi`, so every floor index
  is the donor's. `build.mapconfig_bytes` now ships a borrow's MCF verbatim whatever its `[walkmesh]` says
  (`bgs` still wins, as in `build_field`). A stray `[walkmesh] obj` on a borrow can't mis-key its lights.
- **Script shadows retire, as on every MCF field.** The player's census ops go (the MCF shadows him), and
  so do those of any kit set piece. The import's refused-graft `[[prop]]` stub is a moogle, which casts per
  `STOCK_CASTS` on a field with no MCF.

**Byte identity.** `tests/test_fork_mapconfig.py` now runs the on/off invariant over both fork shapes
(editable, borrow). A borrow fork changes by exactly the MCF file plus the kit shadow ops it retires. The
grafted object's entry is byte-identical to the donor's in both builds, and a borrow still ships no scene of
its own. An install-gated test imports field 1607 as a borrow and checks that the MCF ships byte for byte.
Each fix was broken once to confirm its test goes red: dropping the borrow short-circuit, skipping the MCF
write for a borrow, and writing no `mapconfig.bytes` in the importer.

**In-game** (`rung2_borrow_mcf.py`, `rung2_variants.py`, measured with `measure_rung1.py objects`; the bench
is `import 1607 --name MCF_KTB --id 30935`, the same donor as rung 1, SE-derived, regenerated under the
gitignored `imported/`). Runs are archived in the main repo's `.harness-runs/*-mcf-rung2-*`. Every run passed
its preflight:

- the deployed MCF is the donor's, byte for byte (ON), or absent;
- the slot is registered as a borrow of `MDSR_MAP579_MS_KTN_0`, and no scene of its own is deployed;
- the `.eb` carries no shadow op in ON. CONTROL carries the player's census plus the `[[prop]]` stub's
  (found by its position), and none on any of the 14 grafted objects;
- no exception passed through `fldmcf`/`ff9shadow`/`SetRenderer`.

| measure (`1-spawn` frame) | rung 2, borrow | rung 1, editable |
|---|---|---|
| model tint, ON / CONTROL | (0.734, 0.661, 0.593) | (0.735, 0.658, 0.595) |
| shadow under the lower-right moogle | 581 px, the art darkened to 0.038 | 579 px, 0.038 |
| shadow at the top frame edge (clipped) | 326 px | 142 px |
| calibration: CONTROL-darkened background | 0 | 0 |

The repeat shot 120 frames later gives the same answer: tint (0.722, 0.659, 0.598), 594 + 290 px, calibration 0.
By eye (zoomed crops), the CONTROL moogles stand bright white on bare ground, and the ON moogles are warm-tinted
with a dark elliptical blob under them. The top-edge shadow falls partly under a co-op status overlay (the
shared ini had a `coop` client on). The overlay is identical in all three variants, so it masks out, but the
frame edge clips that shadow differently in the two benches. The bottom ellipse is the comparable number.

`FieldMapActorController.MovePC` threw its NullReferenceException 14-28 times per variant, EMPTY included:
the field-70 NRE, unrelated to the MCF.

## Rung 3 — set pieces on a field that ships MapConfigData (bench 30936)

**The gap.** The MCF service gives every actor a shadow at its own size. Stock's script then `DisableShadow`s
whatever must not cast, but on an MCF field the kit emitted nothing. On a native, editable or BG-borrow fork, a
held prop and a stock-dark prop (tent, cactus, save book) therefore cast a blob stock never shows. Kit props
on a verbatim fork did the same, since it ships its donor's MCF.

**Grounded in stock bytes** (`held_shadow_census.py`, and the same pass over free-standing objects):

- **Held objects:** 140 have a literal Init `SetModel`. 125 disable in the Init, always after `SetModel`,
  and 111 of those on every path. 116 are attached by another entry. The 9 that attach in their own Init, as
  the kit's held prop does, disable before the `AttachObject`: `93 80 4C 04`.
- **Free-standing objects of a stock-dark model:** 593 disable on every path. The op sits right after
  `SetObjectFlags` (`93 80`) or straight into the RETURN (86).
- **Engine:** `DisableShadow` sets character attribute bit 16 (`FF9ShadowOffField`). The MCF service only
  ever writes scale and amplifier, so the bit survives it. The only re-enables are WalkEx near the ground, a
  jump landing, and two field hacks.

**The fix.** `content.prop.inject_prop(mcf=True)` appends `DisableShadow` to the Init tail, straight into the
RETURN, for a part that must not cast: held, or `shadow` resolving to false (a stock-dark model, or the author's
`false`). A part that casts gets nothing: the MCF's values. The build passes `mcf` on all three prop paths:
`[[prop]]`, `[[npc]] holds`, and verbatim-fork props when the field ships its MCF. On an MCF field a prop's
`false`/`true` therefore take effect, and only a size table is reported as ignored. A field with no MCF builds
byte for byte as before.

**Byte identity.** `tests/test_shadow.py` builds the set-pieces fixture with a real `[field] mapconfig`. Against
the same field without one, the build differs by exactly the retired size/amp ops of the 9 casting actors, plus
5 `DisableShadow`: the stock-dark tent, the opted-out cask, the composite's book, the `holds` cup and an
attached cask. Four mutations each turn a test red: no op, held-only, the verbatim path unwired, `holds`
unwired. `tests/test_verbatim.py` covers a verbatim fork: a tent gets the op under the donor MCF and a cask
doesn't; without the MCF neither does.

**In-game** (`rung3_variants.py`, `rung3_deploy.py`, `rung3_mcf_set_pieces.py`). The bench is 30921's set-pieces
bench shipping field 1607's MCF, staged into the gitignored `imported/rung3/`. It is deployed as 30936 under
its own event name, `SHD3M`. ON and CONTROL are the SAME toml, built two ways:

- **ON** is this change.
- **CONTROL** is the pre-fix call: on an MCF field `inject_prop` got neither `mcf` nor a `shadow` value.
  Dropping only `mcf` would have cast census ops on the casting props, bytes no build ever shipped; the offline
  comparison caught that. A build of the same toml with the HEAD code is byte-identical to CONTROL (4119 bytes).
- **Preflight:** both runs passed 16/16. The MCF is 1607's byte for byte, no object carries a size/amp op, the
  act's book and feather keep their donor `DisableShadow`, and ON alone disables the cactus and the cup.
- **Exceptions:** none anywhere. Engine patch s87 removed the MovePC NREs.

`measure_shadows.py --bench set_pieces`, floor luminance ON / CONTROL (above 1 = CONTROL darker):

| box | `1-spawn` | `2-spawn-later` |
|---|---|---|
| cactus (stock-dark) | 1.107 | 1.107 |
| holder (the held cup's blob) | 1.192 | 1.195 |
| cask, cactus_on, chest, barrel, player | 1.000 | 1.000 |
| moogle (idle animation) | 1.000 | 1.001 |

By eye, CONTROL has a soft blob beside the cactus and a large, very dark blob at the holder's feet; ON has
neither. The holder's own Init is byte-identical in both builds, so that blob is the cup's: the misplaced held
shadow stock never shows. Runs are archived in the main repo's `.harness-runs/*-mcf-rung3-*`.

## Rung 4 — `shadow = false` on a field that ships MapConfigData, for every actor (bench 30937)

**The gap.** After rung 3 a `[[prop]]`'s `shadow = false` worked on an MCF field, but the player, an `[[npc]]`,
a `[[chest]]` and a `[[savepoint]]` ignored it with a build warning. The MCF sets every actor's size and
intensity, but the script's one lever there -- stock's `DisableShadow` -- applies to any actor.

**What turns it back on** (engine source). `DisableShadow` sets character attribute bit 16. The MCF's
scale/amplifier writes never touch it, but five engine paths re-enable a shadow:

- WalkEx near the ground: Memoria's extended `0x115`, which the kit never emits.
- `RunLandAnimation` (`0x9D`).
- The end of a jump (`EventEngine.FinishJump`).
- Two field-specific hacks (1600, 1601).

So an Init op holds on an NPC, a chest or a cask. The player is the only kit actor that jumps: its `[[jump]]`
arcs and `[[ladder]]` climbs are `SetupJump; Jump` per hop or rung. The save act's own landings run
`EnableShadow` in the moogle's code.

**The fix.** `content.shadow.mcf_ops(value)` is the MCF-field shadow op: `DisableShadow` for False, nothing
otherwise. `inject_npc`, `inject_chest` and `inject_cask` take `mcf`, like `inject_prop`, and the build passes it
on the synth path and on the verbatim path when the fork ships its MCF. `savepoint.act_save_body
(keep_shadow_off=True)` swaps the act's two landing `EnableShadow` for `DisableShadow`, the same one-byte op.
`shadow.keep_player_shadow_off` puts the op after `SetHeadFocusMask` (where the census ops go), then before the
RETURN of every player function that Jumps. There's no relocating insert, so it relies on
`edit.insert_in_function`'s straddle check. In stock data every one of 51 jump arcs and 52 ladder climbs has
exactly one RETURN and takes it, and so does the kit's generated arc. Between a landing and the function's end
(the landing animation, the rungs of a climb) the shadow shows. The build warning now names only
`{ size, intensity }` tables.

**Byte identity.** Without an MCF, nothing changes. On an MCF field the build changes by exactly the
`DisableShadow` ops of the `false` actors and the act's swapped landings. On the bench, CONTROL -> ON is +7
`DisableShadow` and -2 `EnableShadow`, with labels renumbered. The seven are:

- the player's Init;
- the jump arc's tail;
- the holder's, the chest's and the save moogle's Inits;
- the act's two landings (the -2 `EnableShadow`).

INIT-ONLY -> ON is +1, the jump arc's.

**In-game** (`rung4_variants.py`, `rung4_deploy.py`, `rung4_shadow_off.py`, `measure_rung4.py`). The bench is the
set-pieces bench on field 1607's MCF, with `shadow = false` on the player, the chest, the instant save point
and the holder NPC. The cask, cactus_on and barrel save point keep their defaults as in-frame unchanged actors.
A tread `[[jump]]` (probed: no warnings, the zone clear of the spawn's bands) lands the player at (650, -600).
Three builds of the same toml share slot 30937:

- **ON** is this change.
- **INIT-ONLY** drops the post-jump re-disable. It is the instrument's negative control: the landing must bring
  the blob back.
- **CONTROL** replays the pre-change calls and is byte-identical to a HEAD build (4233 bytes).

Every run passed 10/10 (preflight per variant, the jump landed exactly at its `to`, no exceptions).

| measure | ON / CONTROL | ON / INIT-ONLY |
|---|---|---|
| spawn: player | 1.114 | 1.000 |
| spawn: save moogle | 1.112 | 1.000 |
| spawn: chest | 1.075 | 1.000 |
| spawn: holder | 1.051 | 1.000 |
| spawn: cask, cactus, cactus_on, barrel (unchanged) | 1.000 | 1.000 |
| landed player's feet, `2-landed` | 1.158 | 1.160 |
| landed player's feet, `3-landed-later` | 1.159 | 1.159 |

The noise floor (ON's own two landed shots, same box) is 0.999. By eye, CONTROL and INIT-ONLY show a dark blob
at the landed player's feet and ON none, in both shots. INIT-ONLY equals CONTROL after the landing, so the
engine's re-enable is real and complete, and the post-jump re-disable is what removes it. The save act's
landings are proven offline only (bytes); the harness did not run a save. Runs are archived in the main repo's
`.harness-runs/*-mcf-rung4-*`.

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

## The intensity wrap (bench 30922, `intensity_wrap.py`)

`content/shadow.py` used to accept an authored `intensity` of 0-31, because `intensity << 3` fits
`SetShadowAmplifier`'s one-byte argument. The byte is not where it breaks. `SHADOWAMP` stores the amp as an
`Int32` (`FF9ShadowSetAmpField`), and `EventEngine.SetRenderer` draws the blob in colour `(Byte)(amp * 2)`
(`EventEngine.ProcessEvents.cs:612`). From amp 128 up that wraps, so intensity `i >= 16` should draw exactly as
`i - 16`: 16 draws colour 0 and 31 draws colour 240, the same as 15. The shader ships compiled, so the source
cannot say what colour 0 looks like. The run below settles that too: it draws no blob.

**Design.** Four size-9 `GEO_NPC_F0_CSO` NPCs stand at the rung-0 bench's calibrated slots, on the same floor
and camera, so `measure_shadows.py`'s feet boxes apply. Runs A and B swap the intensities between slots, which
makes every wrap claim a same-slot comparison across two runs. The player casts nothing in any run, and the
control run casts nothing at all. The control is what shows the op is live: if SetShadowAmplifier did nothing,
every slot would draw the same colour, and "15 matches 31" would hold vacuously.
`measure_intensity_wrap.py` scores pixels that are floor in the CONTROL frame. The rung-0 mask requires floor
in both frames, which would drop exactly the pixels a strong blob darkens.

| slot | A | B | A/control (darkened) | B/control (darkened) | A vs B mean abs dRGB | repeat-shot noise A / B / ctl |
|---|---|---|---|---|---|---|
| player | none | none | 1.000 (0.0%) | 0.999 (0.2%) | 0.13 | 1.65 / 1.81 / 1.49 |
| s1 | 15 | 31 | 0.921 (16.4%) | 0.921 (16.5%) | **0.03** | 0.40 / 0.37 / 0.61 |
| s2 | 16 | 0 | 0.999 (0.8%) | 0.998 (0.8%) | **0.81** | 0.99 / 0.83 / 0.62 |
| s3 | 31 | 15 | 0.896 (20.8%) | 0.894 (21.8%) | **0.76** | 1.06 / 0.71 / 0.44 |
| s4 | 0 | 16 | 0.999 (1.0%) | 1.000 (0.3%) | **0.63** | 0.79 / 1.47 / 1.38 |

- **31 draws as 15, and 16 draws as 0.** In every slot the A-vs-B difference sits at or under that slot's own
  repeat-shot noise. The second shot (`2-spawn-later`) agrees: 0.16 / 0.05 / 0.21 / 1.25 against its noise
  0.35-2.30.
- **16 draws no blob at all.** Slots at 16 and at 0 read 0.998-1.000 against the control, as the player does. So
  colour 0 is invisible: the blend darkens by the colour, and an author asking for 16 got no shadow.
- **Deployed bytes:** PRE passed in each run. The `.eb` the engine loaded carried amps 120/128/248/0 (A),
  248/0/120/128 (B), and no shadow op in the control. No exception in any run.
- Runs are archived in the main repo's `.harness-runs/`: `20260923-174850-shadow-wrap-a`,
  `20260923-174928-shadow-wrap-b`, `20260923-174957-shadow-wrap-control`.

**The fix.** An authored intensity is capped at `INTENSITY_MAX = 15`. Validate and the build refuse 16-31, and
the message explains the wrap and names the model's census value where the model is known. The old one-byte
limit survives as `INTENSITY_ENCODABLE_MAX = 31`, which is what the census must satisfy, and
`shadow.blob_colour` states the engine's formula. The census is untouched: models 200 and 488
(`GEO_ACC_F0_V10`/`_V11`) carry stock's own MapConfigData 16, which wraps the same way in stock, so an absent
key reproduces stock. `tests/test_shadow_intensity_wrap.py` pins all of it.

The bench's A and B tomls author 16 and 31 on purpose. Validate refuses them now, so they rebuild only from a
checkout that predates the cap.

## Follow-ups (not in this change)

- OPEN (rung 4): the save act's landings under `shadow = false` on an MCF field are proven offline only (its two
  `EnableShadow` become `DisableShadow`, pinned by `test_shadow.py`). An in-game check needs a harness SAVE on
  bench 30937's instant save point, then the moogle's feet after its return hop.
- DECIDED, no change: `[[npc]]` and `[player]` take the census shadow for every model and do not follow
  `STOCK_CASTS`. Stock's disables for creatures and characters follow where the object is (perched, flying,
  walkmesh-unbound, hidden until a scene), not the model; stock's standing objects cast 2141 of 2191. Bench
  30925 PASSED in-game (merge 3a2e55c5, `NPC-STOCK-CASTS.md`, `tests/test_shadow_npc_default.py`).
- CLOSED, rung 3: on a field that ships MapConfigData, a held prop (and a stock-dark or `shadow = false` one)
  got the MCF's shadow, the held one misplaced at its bone-local height. It now gets stock's `DisableShadow`.
- ~~The pre-existing `FieldMapActorController.MovePC` NullReferenceException, about 26 per run~~ -- NOT the
  benches' or the 1607 fork's: all of them were thrown in field 70 (the New Game FMV field, no walkmesh)
  before the warp. A stock Memoria bug, FIXED by engine patch s87
  (`memoria-patches/s87-field70-movepc-walkmesh-guard.patch`).
- ~~A plain `import` (BG-borrow) carries objects too and ships no MCF~~ -- DONE, rung 2.
- CLOSED: `campaign.missing_assets` did not require `mapconfig.bytes` for a borrow or a native member, though
  both writers emit it and the member toml references it. A member with its art present and its MCF gone went
  unreported, so `fetch_assets` skipped it. The required set now adds the MCF the member's own toml declares
  (`campaign._declared_mapconfig`). On a stolen-ember copy with only TRAIL's MCF deleted, `fetch-assets`
  restores it byte-identical to the original.
- CLOSED: `walkmesh.links.toml` seams were keyed on donor floor numbers too, so a renumbering reshape dropped
  them (2 of 14 on the 1607 swap). The build now re-keys them through the same map as the lights
  (`build._donor_floor_map` -> `apply_seams(seams, floor_map)`). `census_seam_rekey.py` checked all 674 field
  walkmeshes: the unedited round-trip is the identity on every one. With the floors reversed, the re-keyed build
  keeps every one of the 5,983 seams, where the old reconcile dropped 3,756 in 353 walkmeshes. On this rung's
  `reshape` bench (`walkmesh verify`, offline) 14 of 14 seams now link (7 of 14 with the old code), reproducing
  the donor's six seam floor pairs exactly. Floor 4 stays unreachable on foot: stock 1607 has no seam to it
  either.
  **In-game PASSED** (harness, `seam_rekey_ingame.py`, slot 30930, the `reshape` variant). From the probe spawn on
  donor floor 0 the player walks south across the floor 0<->5 seam onto donor floor 5 and back north onto floor 0:
  5/5 checks. The negative control is the same bench built with `apply_seams` ignoring its map (the old
  reconcile, the MCF re-key untouched). There the player is stopped at the seam and slides along it, 4/4. Over
  every published sample, the fixed build's player stands on donor floor 5 in 64 of 292, the old build's in 0 of
  600. Two check criteria were corrected mid-arc and both builds re-run under the final ones. S2 first demanded
  arrival at the spawn, which sits inside an edge's collision radius. The floor test was first 2-D, and floor 4
  (a basement, y ~-1500) lies under the seam in XZ. Runs are archived in the main repo's
  `.harness-runs/*-seam-rekey-*` (final: `20260923-132726-seam-rekey-new`, `20260923-132636-seam-rekey-old`).
  The 24 `MovePC` NullReferenceExceptions per run appear in both builds (see above).
- ~~`deploy_field.py` prints "TEXT OVERWRITES VANILLA" for a fork on its donor's real block even when the build
  ships no `.mes` (an editable fork without text carry). That fork only reads the block.~~ Fixed: the warning
  now fires only when the deploy copies a `.mes` for the block (`check_text_block_shadow(writes_mes=)`).
