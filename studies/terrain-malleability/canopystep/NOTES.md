# comp26 in game: a desert massif carried with its walled canopy

**Status:** in game, 2026-10-22 (round 22, `ingame/RESULTS.md` section 37): **77/77 on the first launch**, every
prediction held. The owner's verdict on the look is pending. Offline result: `../mountaindonors/STEP.md`.

## What the round asks

comp26's rim steps onto a forest canopy at home (topo 38, 62 tris, walled all round, its outer foot on desert at the
step's own height). Carried as the alcove floor, rock and canopy stand on a level foot and every gate passes. Offline
says nothing about two things only the game can answer:
- does the carried canopy behave as canopy: the party sinks 1.171875 into it, and walks across it to the rock;
- does the massif read as a stock desert massif with its scrub canopy (the owner's eye).

## The lab

- **Island** (`lab_build.py`): round 19's desert lab, `world-island --ground desert --center 1380,-100 --radius 55
  --lobes 1 --patches 0 --seed 42`, blocks (20,0)-(22,2), open ocean no live folder touches; mist off. It mints today
  with its 3 WARN rows, as in round 19.
- **Carve points** (`grid_probe.py`): all four angles carve from near (1380, -100) (4u grid: rot 0 11/25, 90 17/25,
  200 14/25, 270 19/25; the refusals are the geometry gate's long zip chord, as STEP.md found at 30 and 180).
- **Variants:** A rot 0, B rot 90, C rot 200, D rot 270, each the CLI's own steps in-process with the canopy spec
  `((67.5, 92.422), (-48.445, -30.078), 3.73, (38,))` (step_carry.py's registered rule) handed in. Every gate clean:
  77 rock + 62 canopy tris, peak 9.75, rock rigid 0.26%, zip rise 1.10, apron 2.5-4.7 deg; 3-4 Terrain files each.

## The prep (`lab_prep.py`)

Per variant: the summit; 12 ring points on desert 2u outside the whole carried blob (the canopy's wall foot
included), y 2.86-3.78; 5 canopy points, each its surface less 1.171875 (canopyspread's model); a desert home 8-16u
beyond the canopy's outer edge facing the rock, the canopy starting about 8u along the line and the rock about 28u;
four views about 28u from the blob.

## Registered predictions (before any launch)

| # | prediction |
|---|---|
| P1 | every stage reaches the world, and the summit reads its peak (9.32-9.38) |
| P2 | all 12 ring points read the built ground in every variant |
| P3 | every walk keeps to the built ground, never on rock, within 0.15 of a built surface (on canopy, less the sink), never below y 1.5 |
| P4 | every home reads its height |
| P5 | every canopy point reads its surface less 1.171875; the walk in climbs onto the canopy and crosses at least half of it (about 18u from the home) |
| Owner | comp26 reads as a stock desert massif with its scrub canopy at each angle |

## Run checklist (when the harness is free)

```
py studies/terrain-malleability/canopystep/lab_install.py install
py tools/play.py studies/terrain-malleability/canopystep/lab_session.py --label canopy-step
py studies/terrain-malleability/canopystep/lab_install.py uninstall <run dir>
py studies/terrain-malleability/canopystep/lab_post.py <run dir>
```

- `out/lab/` is gitignored: on a fresh checkout, rebuild with `lab_build.py` then `lab_prep.py` (about 4 minutes).
- If stage A never leaves 6603 with "the h axis on field 6603 is not a free axis", rerun once before debugging
  (round 21's first launch; 6603 is custom, so its axes are probed blind).
- Install refuses while FF9 runs or another lab is in the install; the ini backup goes to the main repo's `backups/`.
- If the owner passes it: catalogue it like the snow ridge (`blocks = "14-15,3"`, `alcove` = the spec's box and
  y_min, `alcove_floor = [38]`, `home_ground = "desert"`), and the CLI carries it with no further change.

## The run (`20261022-125735-canopy-step`)

77/77 on the first launch, in 502 s; the ini restored byte-exact (sha efaebbf47c36e752), the lab moved into the run dir.

| # | measured | verdict |
|---|---|---|
| P1 | summits 9.3750 / 9.3203 / 9.3672 / 9.3203 against 9.3815 / 9.3237 / 9.3710 / 9.3237 | holds |
| P2 | 48/48 ring points round the carried blob, the canopy's wall foot included | holds |
| P3 | 8/8 view walks on built ground, 0 samples off a surface or on rock | holds |
| P4 | every view and canopy home | holds |
| P5 | 20/20 canopy points read their surface less 1.171875 (to about 0.004); each walk in climbed onto the canopy (12-14 samples on it) and crossed it to the rock, 29.8-30.5u (need about 18u), min y 3.19 | holds |

Stills settled (at most 0.11% of pixels changed, 60 frames apart). Near-white pixels below the horizon across all 20
stills: 1 (a sea glint in C-south), so no gutter sliver: the round-21 fix holds on a second donor.

**The first deliberate canopy carry works as canopy:** the party sinks into it exactly as into stock forest, and walks
across it to the rock. The panels (`mountain_panel_*.png`) show the scrub canopy against the rock at every angle.

## Round 23: comp10, a grass massif with its forest canopy (`CANOPY_DONOR=comp10`; registered before the launch)

The same lane, driven by `rounds.py` (comp26 stays the default). comp10 carries only since the down gate keeps a
donor's own near-vertical walls (`../mountaindonors/STEP.md` round 2): its two stock tris (a canopy wall, ny -0.0074;
a rock, ny -0.0030) are kept by name at every angle.
- **Island:** `world-island --ground grass --center 1380,-96 --radius 66 --lobes 1 --patches 0 --seed 42`, blocks
  (20,0)-(22,2), holding comp10's r65 bench; it mints with 3 WARN rows.
- **Carve points** (`grid_probe.py`): 25/25 at every angle (0, 90, 200, 270); all four variants from near (1380, -96).
- **Variants:** A rot 0, B 90, C 200, D 270, donor 14-16,14 with the canopy spec `((99.418, 128.5), (-32.5, -4.199),
  2.234, (37,))`: 64 canopy tris, zip rise 1.45, rock-rigid 1.74% (the gate allows 3.5%), every gate clean.
- **Prep:** summits 25.90-26.05; ring y 2.36-4.33; 5 canopy points each; the walk in meets the canopy at about 8u and
  the rock at about 21.5u.

Predictions: round 22's P1-P5 unchanged (tolerance 0.15; on canopy, the 1.171875 sink). Owner: comp10 reads as a stock
grass massif with its forest canopy, and its 1.7% rock shear (the canopy's feet tilt the de-tilt plane) does not show.
