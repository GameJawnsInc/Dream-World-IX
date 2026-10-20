# The inlet floor: carry comp9's inlet snow with its rock

**Status:** registered before building (2026-10-20). Offline. `inlet_floor.py`.

**The problem** (`NOTES.md` section 6, `comp9_diagnose.py`). comp9, a snow massif, refuses 0/6 on a snow bench.
The cause is not a coarse rim:
- **An inlet.** Its mouth is 11.4u wide, with 42.7u of rim inside, between rim points 71 and 83, at (588.6, -85.7).
  The bench hole cannot follow it, and the zip bridges 14-17u.
- **A pocket at the inlet's back.** The rim climbs 3.57u there, to the rock at x = 576.

The pocket is not a hole. A 2-tri Object plate fills it: block (9,1), topo 59, area 56, event 0, flags 2, a
decoration rather than an entrance. Its four vertices are exactly the pocket's four rim points.

**The design: reuse Uaho's alcove floor.** `_mountain_blob` already carries one notch floor verbatim: Uaho's
alcove, in game since July. A box in the first donor block's local frame plus a height floor seed a flood fill
through floor tris that touch the rock. Uaho's notch also holds an Object.

comp9's inlet is the same anatomy in snow:
- **The kit change.** An alcove spec may name its floor topographs as an optional fourth element,
  `((x0, x1), (z0, z1), y_min, floor_topos)`. The default is grass, `(0,)`, so Uaho's alcove reads exactly as it
  does today.
- **comp9's inlet** is `((65, 77.5), (-100, -79.5), 3.0, (27,))`, in block (8,0)'s local frame: world x 577-589.5,
  z -100 to -79.5. That is the snow west of the mouth.
- **What follows from the existing code, with nothing new:**
  - the inlet snow joins the blob verbatim;
  - the rim closes across the mouth along the snow lattice, at y 3.3-4.4, which is low ground (THE CUT-LINE LAW);
  - the pocket becomes an enclosed ring whose points are all Object vertices;
  - the blob's Object-aperture path then carries the plate as a plug, the Object's own tris painted with the rock
    collar's UV chart, as Uaho's plugs are.
- **The CLI is not touched.** `world-mountain` keeps `alcove="auto"`, Uaho's box and nothing else. The experiment
  passes comp9's box straight to `carve_mountain`. Productizing a donor alcove from the catalog comes only after an
  owner pass, as it did for the desert peak.

## The instrument (`inlet_floor.py`)

- `anatomy`: comp9's blob with and without the inlet.
- `hashes`: every catalogued donor (uaho, crag, horseshoe, comp20, desert-peak) carved at rot 0 on a bench of its home
  ground, with sha256 of all 44 written block and part files.
  - Taken BEFORE the kit change: `out/inlet_hashes_before.json`, file sha256 `2326e55de8d3cedb...`.
  - Re-run on unchanged code, every donor came out identical, so the hashes are deterministic.
- `sweep`: the control (Uaho, grass), comp9 with the inlet, and comp9 bare, at the six sweep angles (0, 90, 180, 270,
  30, 200) on the lane's bench (centre (1380, -100), radius + 28).

## Registered predictions

| # | prediction | falsified if |
|---|---|---|
| I0 | the catalogued donors' carves are byte-identical after the change (44/44 files); `test_world_interior.py` stays green | any file differs, or a test fails |
| I1 | the control, Uaho on grass, passes 6/6 | any angle refuses |
| I2 | anatomy: the inlet adds 15-40 snow tris (topo 27 only, y 3.3-4.4); the pocket becomes exactly one Object aperture of 4 points; the rim's steepest rise falls from 3.57u to under 2.34u | any of these fails |
| I3 | **decisive:** comp9 with the inlet passes at least 4 of the 6 angles on snow | 3 or fewer |
| I4 | at no angle does comp9 with the inlet still refuse on maxEdge of 9u or more, or zipRise over 2.34u: the inlet was the source of both | either appears at any angle |
| I5 | the rock-rigid deviation stays at 1% or less on every passing angle (the floor rides the same rigid map) | above 1% |
| I6 | comp9 bare still refuses 0/6, as measured this morning (the sweep is stable) | any angle passes |

**Known risk, no call made.** The plug-chart gate refuses a plug whose UVs leave the rock band (columns 5-10, rows
6-12 at the rock chart's phase). comp9's collar is snow-massif rock, whose chart phase was never measured. If I3
fails, this is the first place to look.

**What follows:**
- **If I3 holds:** comp9 becomes a candidate snow-massif donor (`snow-crag`, home ground snow). The owner's eye
  follows in game, as the desert peak's did, when the harness is free.
- **If I3 fails:** the refusal names the next blocker, and comp9 stays parked.

## Round 1 result (offline, 2026-10-20)

| # | measured | verdict |
|---|---|---|
| I0 | 44/44 catalogued files byte-identical to the before-hashes (the tests run with round 2) | **holds** |
| I1 | Uaho 6/6 | **holds** |
| I2 | the inlet adds 15 tris, all snow (27); one Object aperture of 4 points; the rim's steepest rise falls from 3.57u to 1.09u, and the rim from 92 to 83 points. But the floor reaches y 4.96, over the predicted 4.4. Two floor tris carry event bit 1, a scripted world-event tile, which the carve's dispatch strip drops | **holds, except the height range** |
| I3 | comp9 with the inlet: **0/6**. Every angle refuses at the plug chart: "plug chart left the rock band", with the plug at columns 2-3, rows 4-5 | **FALSIFIED**, at the registered risk |
| I4, I5 | not reached: the plug gate runs before the geometry gates | untested |
| I6 | comp9 bare 0/6, the morning's numbers to the decimal | **holds** |

**Why the plug chart refuses.** The gate keeps a plug inside the painted rock band: columns 5-10, rows 6-12 at
`ROCK_CHART_PHASE`, measured in July on Daguerreo, a grass-world massif. Rock is painted from a different band in
each biome. The columns and rows that each blob's rock vertex UVs occupy:

| donor | rock columns | rock rows |
|---|---|---|
| uaho (grass) | 6-10 | 7-11 |
| crag (desert) | 7-12 | 2-6, 13-14 |
| desert-peak (desert) | 7-11 | 3-6 |
| comp9 (snow) | -1 to 3 | 1-5 |

- comp9's plug (columns 2-3, rows 4-5) lies inside its own rock's band, and its 9-tri collar sits at columns -1 to 3,
  rows 3-5. The plug continues the snow rock's own chart, as the gate means it to.
- The gate is a grass-world calibration. The desert donors never met it because they have no apertures.

## Round 2: the plug chart judged against the donor's own rock (registered before building)

**The change.** A plug passes the chart gate if its columns and rows sit inside the July grass band (unchanged) OR
inside the band its own donor's rock occupies (the min-max columns and rows of the blob's rock vertex UVs).
- That is strictly more permissive, so no verdict that passed today can change, and the gate writes no bytes.
- Uaho's plugs sit at columns 6-7, rows 9-11: inside both bands.
- The check moves into a small helper, `_plug_chart_ok`, so its refusal can be tested directly.

| # | prediction | falsified if |
|---|---|---|
| R0 | catalogued hashes 44/44 identical; `test_world_interior.py` green; the new helper test refuses a plug outside both bands (break-it) and accepts one inside either | any fails |
| R1 | Uaho 6/6 | any angle refuses |
| R2 | **decisive:** comp9 with the inlet passes at least 4 of the 6 angles | 3 or fewer |
| R3 | no comp9-with-inlet angle refuses on maxEdge of 9u or more, or zipRise over 2.34u (round 1's I4) | either appears |
| R4 | rock-rigid deviation of 1% or less on every passing angle (round 1's I5) | above 1% |
