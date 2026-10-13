# Rock stretch tolerance (X1)

**Question.** How far can carried rock stretch vertically before its painted texture reads stretched in game?
`world-mountain` keeps carried rock rigid (`MTN_ROCK_RIGID` 0.035: no carried edge may change length by 3.5% or
more), because the v1/v2 blend conform once smeared Uaho's east lobe in game. Relaxing it needs this experiment
first (`../uvclass/VERIFY.md` UV-07; `../README.md` section 7.1, rank 9).

**Registered prediction** (`../uvclass/NOTES.md`, X1): stretched pure-Y about its rim, UV carried, ×1.25 reads like
the rigid carry, ×1.5 is borderline, ×2.0 reads stretched. If ×1.25 passes, `MTN_ROCK_RIGID` can relax to about 0.10.

| file | what it does |
|---|---|
| `x1_build.py` | Offline. Builds the three variants from the live bench, runs gates G1-G5, measures each one's texture stretch, picks the viewpoints and the summit probe -> `out/x1/` (gitignored) |
| `x1_session.py` | The harness scenario: four world loads (rigid, ×1.25, ×1.5, ×2.0), two stills from each of two viewpoints, and a summit height per stage |
| `x1_post.py` | After the run: scores the summit probes, checks the stills settled, builds the blind panels (A-D, key in the run dir) |

## 1. The bench

The Uaho block, carried whole onto the Path D world: Disc9 cell (13,15) in `FF9CustomMap-world` (`Donor.txt` `0,0`,
so the alcove roof is the stock prefab's own Object). The disc-1 bench at (2,18)/(2,19) that the study first named
no longer holds the mountain: it was redeployed in July and carries no topograph-49 rock now.

Its rock is 134 topograph-49 triangles over 83 vertex positions, y 2.31 to 13.28. 30 positions are pinned:
- 26 the rock shares with grass, forest or cliff triangles (its foot welds);
- 4 more on the Terrain's open edges (the alcove aperture the prefab Object closes; all 7 Object vertices sit on
  Terrain positions).

The other 53 are free.

## 2. The map

`y' = b(x,z) + s (y - b(x,z))` on every free rock entry. `b` is the least-squares plane through the pinned
positions (tilt 3.1°) plus an inverse-distance blend of their residuals (max 2.8u), so it equals the rim height at
every pinned position and the rim never moves. `b` is a function of plan position only, so coincident entries (one
weld) map to one point. Normals take the map's inverse transpose; UVs and tangents (IDALL) are verbatim.

Gates, all passing for all three variants:
- G1: `s = 1.0` through the pipeline reproduces the live file byte for byte. It caught two float-rounding leaks on
  the way: the map is written `y + (s-1)(y-b)`, and normals keep their original length.
- G2: only free rock entries change.
- G3: no welded position moves, and the open-edge count is unchanged.
- G4: no rock triangle flips or degenerates.
- G5: the prefab Object's 7 vertices still meet the Terrain.

## 3. Offline numbers

| variant | summit y | texture stretch p50 / p90 / max | rock area stretched past ×1.1 | past ×1.25 | inside the M.flow envelope |
|---|---|---|---|---|---|
| rigid | 13.28 | 1 / 1 / 1 | 0 | 0 | 65.7% |
| ×1.25 | 15.32 | 1.128 / 1.180 / 1.253 | 67.3% | 0.3% | 70.9% |
| ×1.5 | 17.35 | 1.263 / 1.372 / 1.527 | 93.9% | 53.1% | 71.6% |
| ×2.0 | 21.44 | 1.553 / 1.779 / 2.102 | 100% | 90.8% | 67.2% |

"Texture stretch" is each rock triangle's larger principal stretch from the rigid triangle (UV carried, so it is the
texel stretch), area-weighted.

**The registered envelope numbers do not apply to this rock.** They are the M.flow class's survival under a pure
height scale, map-wide (95.4 / 89.9 / 63.5%). Uaho's rock is mostly M.free (114 of 134 triangles; 12 M.flow, 7
L.keyed, 1 L.free), and the rigid carry itself scores 65.7% on the M.flow envelope. Stretching moves some triangles in
and some out, so the measure stays flat (66-72%) and cannot separate the variants. The direct stretch above can, and
the in-game look decides.

The rim pin barely matters: a pure height scale scores the same 70.9 / 71.6% on these triangles at ×1.25 / ×1.5
(69.4% against 67.2% at ×2.0).

## 4. In game (round 15, `../ingame/RESULTS.md` section 30)

Two runs, 17/18 checks: every stage reached world 9013, faced the massif from both viewpoints, and read its own
variant's summit height (to the engine's 1/256 grid). The first run's rigid stage was lost to `world_face` learning its
turn rate next to the rock. The scenario now learns it on the open landing lawn first, and the rigid rerun passed 4/4.

Rerun: `py studies/terrain-malleability/rockstretch/x1_build.py`, then the lab deploy in `../ingame/d9_PLAN.md`
section 3 (bench 30950 + `inject_worldjump.py`), then
`py tools/play.py studies/terrain-malleability/rockstretch/x1_session.py --label x1-rockstretch`, then
`py studies/terrain-malleability/rockstretch/x1_post.py <run dir> [<rerun dir>]`.

**Verdict.** Pending the owner's eye on the blind panels.
