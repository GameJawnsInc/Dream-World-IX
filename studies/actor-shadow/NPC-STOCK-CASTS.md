# NPCs, the player and STOCK_CASTS

**Status:** decided NO, from stock bytes, and checked in-game (harness, bench 30925). An `[[npc]]` or the
`[player]` with no `shadow` key casts the census shadow for every model. It does not follow
`_shadowparams.STOCK_CASTS` the way a `[[prop]]` does. Pinned by `ff9mapkit/tests/test_shadow_npc_default.py`.

## The question

`STOCK_CASTS` is a per-model verdict: do a model's free-standing stock objects `DisableShadow` on every path
through their Init (the set-pieces section of `PLAN.md`)? A `[[prop]]` with no key follows it. `[[npc]]` did
not, so 24 non-accessory models that `STOCK_CASTS` marks as disabled still cast when worn by a kit NPC:
birds, frogs, tadpoles, Ramuh, the dragons and a few others. Is that a defect?

## The answer

No. For set dressing the verdict describes the ordinary case: the tent, the save book and the letter stand on
the floor with no shadow. For creatures and characters it does not. There the disable follows where the
object is, not what it is. A kit `[[npc]]` has only `pos = [x, z]`, with no height and no pathing key. It
always stands on the walkmesh, and stock's objects standing there cast.

## Method

`npc_standing_census.py` (reads the install, ships no game bytes) uses the same object selection and the
same dominator verdict as `_regen_shadowparams`. It then sorts each free-standing non-accessory object by
where its Init places it:

- **standing**: on the walkmesh. `MoveInstantXZY` within 60 units of the floor under it, or a
  `CreateObject` point on the mesh.
- **elevated**: above or off the walkmesh.
- **unbound**: the last `SetPathing` is 0.
- **stowed**: a `CreateObject` point shared by 2+ objects in the field, a pool its loop moves out of.
- **hidden**: a `HideObject` dominates the Init.

Positions come from const-propagating the Init's locals. The floor comes from each field's own walkmesh.

## Results (3938 objects in 800 field scripts)

| placement | casts | disabled |
|---|---|---|
| standing | 2141 | 50 (2.3%) |
| elevated | 665 | 76 |
| unbound | 108 | 72 (40%) |
| stowed | 674 | 35 |
| hidden | 22 | 11 |
| unresolved / no walkmesh | 82 | 2 |

The 24 models `STOCK_CASTS` disables, restricted to the standing case:

- **12 never stand on the walkmesh anywhere in stock:** the Silver Dragon, `F1_CCB`, the three
  frog-catching frogs (`FRC`, `FRF`, `F1_FRM`), the tadpole, `SUB_F2_BAK`, both Ralvuimago models, Lich,
  Ramuh and the Red Dragon. For these the table has no evidence about the kit's case.
- **4 cast every time they stand:** the frog `F0_FRM` (Qu's Marsh thicket, 2 of 2), the Lindblum trick bird
  (2 of 2), Black Waltz 3 and the `F4_JJY` old man.
- **8 have 1 to 7 standing votes that lean disabled.** Most of those disables are scripted scenes that also
  disable models `STOCK_CASTS` says cast:
  - L. Castle/Event (606): 3 of the bird's 5. The scene also disables the player chocobo.
  - Crystal World and the ending (2926, 2927, 2933): `KJG` and the `F3`/`F4`/`F5_ZDN` Zidanes. The scene
    also disables the player Zidane.
  - Prima Vista/Storage (58): one `F1_BRI` oglop. The scene also disables Steiner.
  - The Earth Shrine boss scene (2552): the one `FFF` object, beside Lich.

  The rest:
  - The bird's other 2 are Lindblum Station's fly-off birds (566).
  - `F4_GRN` is a 1-1 tie.
- **One real standing exception:** the `F1_BRI` oglops walking the Mountain Path trail (1550, 2 objects).
  Two votes do not justify a rule. The kit's own `oglop` archetype is `F0_BRI`, which casts 6 of 9.

## Why stock disables these models (read in the bytes)

- **Birds (`F0_CCB`, 43 objects).**
  - Alexandria's bird (100 e10) picks one of three rooftop perches at Y -3000/-4000, then `DisableShadow`.
  - The same bird's revisit (101 e10) is placed at Y 0 on some paths and keeps its shadow there. When its
    loop brings it down (height local set to 0), it calls `EnableShadow` and plays frames 50-66 of its fly
    clip into the idle. Stock turns a bird's shadow back on when it lands.
  - Lindblum Station's birds (566 e14/e16) peck on the ground and fly off (tag 22: `SetPathing(0)` then
    `WalkXZY` up). They disable at Init and on every loop tick.
  - Dali's village-road, inn and windmill birds cast.
- **Frogs and tadpoles.** Qu's Marsh Pond (656-659) is the frog-catching minigame. There the frogs are
  `SetPathing(0)` at Y 20-30, and in each marsh field every frog and tadpole spawns at one shared point
  before its loop places it. In 650-656 that point is (-463, 3843), which is off the mesh in the Entrance
  and Shore fields (650-654). The two thicket frogs (662) stand on the mesh and cast.
- **Cutscene monsters.**
  - The Silver Dragon is placed hundreds to thousands of units above its Iifa floors, or off the mesh.
  - The Red Dragon is `SetPathing(0)` in all four Gulug fields.
  - Ralvuimago is placed about 1900 units off the Gargan Roo floor (954), walkmesh-unbound (955), or off
    the mesh (957).
  - Black Waltz 3 is placed 2900 units off the cargo-deck floor (500) or unbound off the mesh (506). The
    standing, player-controlled one (501) casts.
  - Ramuh (3 of its 4 Pinnacle Rocks objects) and the `F4_JJY` old man (6 of 7) are `HideObject`-ed on
    every path through the Init and appear in the scene.
  - The `F3`/`F4`/`F5_ZDN` Zidanes appear only in the ending (2933).

## The player

1022 of stock's 1054 player-controlled objects cast. The 32 that do not are scripted scenes: Pinnacle Rocks,
Memoria, Crystal World, the Chocobo's Dream World and Air Garden, and high ledges. 10 of those 32 turn the
shadow back on in their own loop. Stock makes two `STOCK_CASTS`-disabled models the player: Black Waltz 3
(501) and `F4_JJY` (1604). Both cast. So `[player] model` re-skins keep `cast_player_shadow` as it is.

## In-game (harness, bench 30925)

`bench/npc_default.field.toml` sits on rung 0's floor, camera and actor slots:

- the player re-skinned to Black Waltz 3
- the kit's `frog`, `bird` and `ramuh` archetypes, none with a shadow key
- a second frog with `shadow = false` as the in-frame negative control

The control bench is the same bench with every actor off. Runs are archived in the main repo's `.harness-runs`:
`20260923-120815-shadow-npc-default` (with `npc_default_sheet.png`) and
`20260923-120909-shadow-npc-default-control`. Both passed 2/2:

- **PRE:** the deployed `.eb` carries exactly the census ops per actor, keyed by model and Init x/z.
- **A0:** no exception went through a shadow path. The field-70 `MovePC` NullReferenceExceptions came to 24
  in the shadows-on run and 22 in the control.

`measure_npc_default.py` scores the spawn frame, floor pixels only:

| actor | ops | luminance on/control | floor darkened >=5% |
|---|---|---|---|
| player (Black Waltz 3, census) | (8, 8) + 32 | 0.970 | 12.4% |
| ramuh (census) | (11, 11) + 40 | 0.990 | 5.3% |
| bird (census) | (5, 5) + 24 | 0.993 | 4.2% |
| frog (census) | (6, 6) + 16 | 0.999 | 0.8% |
| **frog_off** (`shadow = false`) | none | **1.000** | **0.0%** |

Calibration: the control measured against itself reads 1.000 / 0.0% on every row.

By eye, the player, the bird and Ramuh each show a soft blob at their feet. The frog's census blob is small
and faint (intensity 2, the MCF's own value for frogs). It falls almost entirely under the frog's flat body,
the way the cask's does under the barrel. So for the frog, casting and not casting look nearly the same.

## What the kit does

- An absent key, or `true`, casts `SetShadowSize` + `SetShadowAmplifier` from the census for any model, NPC
  or player.
- `shadow = false` is the author's lever for a creature placed where stock would hide its shadow.
- Tiny creatures already get tiny census values from the MCF half: the tadpole and `F1_CCB` get (1, 1),
  frogs (6, 2) and the bird (5, 3).

The rule is stated at the call site (`build.build_script`'s `[[npc]]` injection and
`content.shadow.cast_player_shadow`). `tests/test_shadow_npc_default.py` enforces it with four tests, each
shown to fail when its rule is broken:

- the NPC default routed through the prop rule
- the opt-out ignored
- the player re-skin dropping its shadow
- a `STOCK_CASTS` entry flipped under the premise test, which skips until `STOCK_CASTS` is on master

## Limits of the census

The placement classes are heuristics:

- a 60-unit floor tolerance
- a stow pool is inferred from shared spawn points
- positions are a union over Init branches
- 82 objects are unresolved (computed positions)

The standing total and every model named above hold to that heuristic, not to a hand-read of each field.
