# The raised step: carry comp26's and comp10's canopy with their rock

**Status:** offline result 2026-10-22. **comp26 carries with its canopy at 4 of 6 angles** (0, 90, 200, 270); bare it
is still 0/6 on the step. **comp10 stays parked:** 0/6 with or without its canopy, refused on two STOCK tris that face
down by a hair. Registered first (commit 7f293dd4); T2 and T3 are falsified as written, for the reasons below.
`step_carry.py`.

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

## Result (offline, 2026-10-22)

| # | measured | verdict |
|---|---|---|
| T1 | Uaho 6/6 | **holds** |
| T2 | comp26: the spec carries exactly its 62 topo-38 canopy tris, no step left on the rim, steepest rim edge 1.08u (was 1.95). comp10: the spec adds exactly its 64 topo-37 canopy tris, no step left, steepest edge 1.645u; but the blob's non-rock count is 108, because 44 topo-10 tris of its summit plateau (y 25.6-28.2, enclosed by rock) are already in the BARE blob | comp26 **holds**; comp10 **falsified as written** (the instrument counted the whole blob's non-rock tris, not what the spec adds) -- what the spec adds holds |
| T3 | comp26 with its canopy **4/6** on desert; comp10 with its canopy **0/6** on grass | **falsified** (it needed both) |
| T4 | no canopy carve refuses on zipNyMin (0.93-0.96 everywhere) | **holds** |
| T5 | comp26 rock-rigid 0.26% on every passing angle | **holds** (comp10 never passed; its rigidity reads 1.7% with the canopy, 0.4% bare) |
| T6 | comp26 bare 0/6, every refusal the step (rise 1.95, ny 0.00). comp10 bare 0/6, but on the geometry gate (down=1), with the step behind it (zipNyMin 0.01, rise 2.41) | comp26 **holds**; comp10 **falsified as written** |

**comp26's two refusals (30 and 180 deg)** are the zip's longest chord, 9.3u and 9.7u against the 9u ceiling. Every
other gate is clean there (down 0, near-miss 0, annulus 0, zipNyMin 0.93-0.96).

**comp26's passing carves:** 77 rock + 62 canopy tris (139 in all), peak 9.8u, zip rise 1.10u, rigid 0.26%, apron 2.5-4.2 deg, a
r51 desert bench.

**comp10's blocker: two stock tris that face down.** In the donor blob, a canopy wall tri (topo 37, ny -0.007) and a
rock tri (topo 49, ny -0.003) lean down by a hair: near-vertical walls in the shipping data. De-tilt does not change
them. The rock one is in the bare blob too (down=1); the canopy adds the other (down=2). This is comp9's class (a
stock rock face with ny 0.093 that misses the ground query at home): the gate cannot tell a donor's own stock
geometry from a defect the carve made, and changing that is the owner's call.

**What follows:**
- **comp26** becomes an in-game round when the harness is free: a desert island at the round-19 site (r55 desert,
  (1380, -100), blocks (20,0)-(22,2), which holds the r51 bench), carved at 0, 90, 200 or 270 with the canopy spec,
  harness + panels. If the owner passes it, catalogue it like the snow ridge (`alcove` + `alcove_floor = [38]`).
- **comp10** waits on a gate decision: whether a donor's own stock down-facing (or ground-query-missing) tris are
  lawful in a carry.

## Round 2: a stock near-vertical down face is lawful in a carry (registered before building; owner's go: option 1)

**The census** (`downface_census.py`). Disc 1 ships 83,937 Terrain tris; **233 face down**. The histogram has NO
quiet band: 81 below ny -0.5 (building undersides, topo 59, and a rock arch roof at (13,3), topo 49, ny -0.997), 46 in
[-0.5, -0.2), 25 in [-0.2, -0.1), 16 in [-0.1, -0.05), 10 in [-0.05, -0.02), and **55 in [-0.02, 0)**: near-vertical
walls, comp10's two among them. So the threshold is not read off a gap; it is a "near vertical" line, kept narrow.

**The rule.** The mountain gate's down count skips a new tri only if ALL hold:
- it is a verbatim carried donor tri (the blob or the footprint sweep: `fam == "mountain"`), its carried corner
  positions unchanged by any later pass;
- it faced down AT HOME too (the raw stock normal, before de-tilt) -- a tri the carry FLIPPED is never exempt;
- it is near-vertical at home and as carried: ny >= -0.02 (`MTN_STOCK_DOWN_NY`, about 1.15 deg past vertical).
Each exempted tri is logged by name. Every other down face still refuses, stock or not.

| # | prediction | falsified if |
|---|---|---|
| D1 | the 44 catalogued carve files are byte-identical (the gate writes nothing) | any differs |
| D2 | break-its, as tests: a carve-made down tri, a stock down tri steeper than -0.02, and a tri that faces UP at home but down as carried are each still refused | any passes |
| D3 | **decisive:** comp10 with its canopy (`step_carry.py`, r65 grass bench) passes at least 4 of 6 angles | 3 or fewer |
| D4 | at every angle comp10's exemption log names exactly its 2 stock tris (1 rock, 1 canopy wall) and no other | a count differs |
| D5 | comp10 bare still refuses 0/6, now on the step (zipNyMin), its rock down tri exempted | any angle passes, or another gate refuses first |

**Known risk, no call made:** comp10 with its canopy read rock-rigid 1.7% in round 1 (the gate allows 3.5%; round 1's
T5 asked 1%). If D3 holds, T5 will not, and the rigidity is reported, not explained away.
