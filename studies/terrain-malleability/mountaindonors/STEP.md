# The raised step: carry comp26's and comp10's canopy with their rock

**Status:** registered 2026-10-22, before the decisive sweep. Offline only.

**The problem** (`NOTES.md` section 2). comp26 (a desert massif, blocks 14-15,3) and comp10 (a grass massif,
14-15,14) refuse 0/6 on a flat bench of their own ground. Each rim has an edge of ~zero plan length rising 1.95u, so
the zip can only close it with a vertical tri (zipNyMin 0.00).

## The anatomy (`step_anatomy.py`, measured before this registration)

The steps are not raised plain ground: **the rock meets a forest canopy** (THE CANOPY-FOOT LAW).
- **comp26:** both rim steps (rim points 8 and 12) meet one canopy of topo 38: 40 tris of shelf top at y 6.18-8.80.
  Flooded whole (topo 36-38, no height cutoff), it is 62 tris, y 4.23-8.80. Its boundary is 5 edges on the rock and
  11 outer edges, every one at y 4.23 (the step's own foot), with desert (17) across all 11. Inside blocks 14-15,3.
- **comp10:** the step (rim point 5) meets a forest canopy of topo 37. On blocks 14-15,14 it runs off the read window
  at x = 1024; on **14-16,14** it is whole: 64 tris, y 2.73-8.09, 8 edges on the rock and 12 outer edges at y
  2.73-3.34, grass (0) across all 12. The wider window reads the same rock (373 tris, rim 45 points, r 37.4).

So rock plus canopy, carried together, stand on a level foot. A canopy carried without its walls would only move the
same step to the canopy's outer edge; the unit is the whole walled canopy, as `world-forest` carries one.

## The design: the canopy rides as the alcove floor (no kit change)

The alcove spec already names its floor topographs (THE INLET FLOOR, `INLET.md`). Each donor's spec is the canopy's
own topograph, a box round the canopy component's plan extent (+0.5u), and a y floor 0.5u under its lowest vertex,
so its walls ride too:
- comp26: `alcove=(box, y_min, (38,))` in block (14,3)'s local frame;
- comp10: the donor rect **14-16,14**, `alcove=(box, y_min, (37,))` in block (14,14)'s local frame.

The alcove code's comment says "floor tris only, never canopy": that is the DEFAULT topograph set (grass). A canopy
carried deliberately, with its walls, is this experiment. No kit file changes, so the catalogued carves cannot move.

**Bench:** `sweep.py`'s, a `build_landmass` mint at (1380, -100) in each donor's home ground (comp26 desert, comp10
grass), radius = the carried blob's rim radius + 28 (the canopy widens the blob). Six angles (0, 90, 180, 270, 30, 200),
`carve_mountain(near=...)` + `census_gate(parts=...)`: every kit gate. Uaho on grass is the control.

## Registered predictions

| # | prediction | falsified if |
|---|---|---|
| T1 | the control, Uaho on grass, passes 6/6 | any angle refuses |
| T2 | anatomy with the spec: the alcove carries exactly the canopy component (comp26: 62 topo-38 tris; comp10: 64 topo-37 tris) and nothing else; the carried rim has NO step edge (plan < 0.1u and rise > 1u), and no rim edge rises more than 2.34u | any count differs, or a step or a > 2.34u edge remains |
| T3 | **decisive:** comp26 with its canopy passes at least 4 of 6 angles on desert, and comp10 at least 4 of 6 on grass | either 3 or fewer |
| T4 | no angle of either refuses on zipNyMin 0.00 (the step's signature): the canopy was its source | it appears at any angle |
| T5 | rock-rigid deviation at most 1% on every passing angle | above 1% |
| T6 | the bare donors (no spec) still refuse 0/6 on the same benches, on the step | any angle passes |

**Known risks, no call made:**
- The canopy is walkable forest ground the player sinks into (canopy sink 0.0015u); the mountain carve's gates were
  calibrated on rock and grass, and do not run `world-forest`'s perimeter walk-in simulation. A pass offline says
  nothing about walking into the carried canopy; that is the in-game round's question.
- The carved canopy changes what topograph the island has, so encounters resolve by (zone, topograph) there.

**What follows:**
- **If T3 holds:** each passing donor becomes an in-game round (harness + panels), queued behind s145.
- **If T3 fails:** the refusal names the next blocker; the donor stays parked.
