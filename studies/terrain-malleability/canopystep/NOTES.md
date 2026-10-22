# comp26 in game: a desert massif carried with its walled canopy

**Status:** READY, NOT RUN (2026-10-22). Built and prepped offline while the harness serves s145; the round runs when
it is free. Offline result: `../mountaindonors/STEP.md` (comp26 carries with its canopy at 4 of 6 angles).

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
