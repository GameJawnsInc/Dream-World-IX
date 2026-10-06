# The grass-step study — what stock builds where lowland grass drops ~1u, for R4 option (c)

Registered 2026-10-06 BEFORE the instrument (`grass_step_study.py`) existed or ran. Follows
[`FOREST-FOOT-CENSUS.md`](FOREST-FOOT-CENSUS.md).

## Why

The census left one lawful option for R4's forest side: **(c) a coastal shelf.**
- The massif's terrace stays at our lawn (3.2).
- Southwest of it, the lawn becomes a shelf ~1.1u lower, running out to the sea.
- The donor's forest is carried verbatim onto that shelf, at its home height.

Only one surface would be authored: the transition between terrace and shelf. This study measures what
stock builds there before anything exists. It also measures the coast, because a shelf that reaches the
sea lowers that stretch of our coast. The west coast there runs flat at 3.2 to the edge, and stock cliff
coasts carry their interior land at a median of 3.1u (coast-mosaic memory).

## Three parts

**A — THE HOME EXEMPLAR.** The donor's own neighbourhood answers this exact configuration: at home, the
horseshoe's grass sides stand at terrace level and its forest stands ~1.1u lower. The stock bytes are
placed by the deployed carve transform (rot 90°, DY −0.6488, the carve's de-tilt) and measured relative
to our lawn (3.20).
- **Outward transects** from the forest-contact rim, to 40u.
- **Tangential rings** at 6u and 12u outside the rim, walked from the grass-contact side across the
  forest run's two ends.

**B — THE STOCK VOCABULARY.** All disc-1 lower-world ground (y ≤ 14), rasterized on a 2u grid.
- **A step** is a straight transect (8 directions, 8–40u long) between two LEVEL grass cells (3×3 range
  ≤0.2u) whose heights differ by 0.8–1.6u. Every cell along it must be grass, and the profile must be
  monotone within 0.15u. Only the shortest qualifying transect per start cell and direction is kept, and
  transects are de-duplicated by midpoint (8u) and axis.
- **Width** is the 10%→90% distance of the height change. **Max slope** is taken over adjacent samples.
- **Co-location** is the distance from the 50% point to the nearest forest, massif rock, coastal rock
  (topo 58), sea, and block border.

**C — THE COAST.**
- Our west coast where the forest side faces it, read from the pre-massif host: the land's last 10u and
  the topograph at the edge, plus any Beach1 verts nearby.
- Stock coastal-cliff land: grass cells within 6u of a topo-58 cell that is itself within 6u of sea.

## Registered predictions

- **P-A1 (a shelf, not a hollow).** Along outward transects from the forest-contact rim, the home ground
  never comes back up to within 0.3u of the terrace before it reaches coastal rock or sea within 40u.
  Holds on ≥80% of stations.
- **P-A2 (stock hides the step under the forest).** On both tangential rings (6u, 12u), at both ends of
  the forest run, the terrace→shelf crossing (from the last sample ≥ −0.3u to the first ≤ −0.9u) is ≥70%
  covered by forest canopy.
- **P-A3 (where it shows, it's a ramp).** Any open-grass part of that crossing is ≥8u wide tangentially.
- **P-B1 (open-grass steps are ramps).** Over stock, the step width p50 is ≥8u, max slope p90 is ≤20°,
  and lips (width ≤4u) are <10% of steps. Co-location is reported only, with no prediction.
- **P-C1 (our coast is a cliff there).** On ≥70% of the forest-side rays, the land runs flat to the edge
  with topo-58 or no tris beyond, and no Beach1 verts lie within 8u. A shelf reaching it therefore means
  lowering a cliff top, which is coast-mosaic work.
- **P-C2 (low cliff tops exist in stock).** Stock coastal-cliff land heights have p10 ≤ 2.2u, so a top
  at the home's ~1.6–2.0 is in-language.

## What each outcome means for (c)

| outcome | means |
|---|---|
| A1 + A2 hold | stock hides this exact step under the forest. (c) runs the shelf's edge under the carried forest, so the only visible authored ground is beyond the forest's two ends |
| A3 / B1 hold | that visible part is a RAMP of the measured width; its numbers are the spec |
| B1 fails (lips common) | the step may be a short lip, with a smaller footprint |
| A1 fails | at home the forest side comes back up (a hollow); the census's P5 is contradicted, so re-open |
| C1 holds + C2 holds | the shelf meets the sea by lowering a stretch of cliff top to a stock-lawful low height; that part goes to the coast-mosaic recipe |
| C2 fails | a low coastal shelf on a cliff coast is off-language, so (c) is dead here; (c') or (d) |

## Declared limits

- **Under the canopy, the ground isn't modelled.** The canopy IS the surface, so A2 can only say the
  crossing happens under forest, not what shape it has there.
- **2u raster.** Widths are quantized to ~2u.
- **The home exemplar is one site.** B is the general check.

## RESULT

(appended after the run, below this line; nothing above edited)

Run 2026-10-06 (`grass_step_study.py`, data `grass_step_study.json`). The raster is 768×640 at 2u, with
18,227 lower-world grass cells, of which 1,176 are level.

### The positive control (added before the scored run was trusted)

A detector that cannot see a lip cannot say stock has none. `--selftest` builds synthetic ground with a
1.2u LIP (one cell) and a 1.2u RAMP over 12u, and runs the same detector: the lip reads 0.0u wide and the
ramp 10.0 / 14.1u (axis / diagonal). **PASS.** The study refuses to run if it fails. The refactor that
made the detector testable was re-run against the first run: identical output.

### The registered score

| | measured | verdict |
|---|---|---|
| **P-A1** shelf, not hollow | 33 of 33 forest-run transects never return to terrace level; all reach coastal rock or sea within 10–24u | **HOLDS** |
| **P-A2** step hidden under the forest | the terrace→shelf crossing is 0% forest-covered at both ends, on both rings | **FAILS** |
| **P-A3** open part ≥ 8u | open-grass transition band (−0.3..−0.9) 6.4 / 7.8 / 10.9 / 7.2u: 3 of 4 under 8u | **FAILS** |
| **P-B1** stock steps are ramps | 48 steps; width p10 8.0, p50 12.0, p90 22.0u; max slope p50 5.5°, p90 7.7°; lips 0% | **HOLDS** |
| **P-C1** our coast is a cliff there | 0%: the land falls ~2.6u over its last 10u to y ≈ 0.6, mostly grass (some topo 58), no Beach1 within 26u | **FAILS** |
| **P-C2** low cliff tops in stock | stock coastal-cliff land p10 2.40, p50 3.04; ≤2.2u on 5% | **FAILS** |

**Co-location of stock steps (reported):** open ground 67%, block border 19%, coastal rock + sea 8%,
forest 4%. Of the 21 steps within 24u of the sea, the width p50 is 12.0u and the lower side sits at
y p50 3.11.

### What it says

- **The home is a small island.** The horseshoe stands on it with a narrow apron, a coastal-rock rim, and
  sea all round (see the plan view). Its forest side is not a broad shelf but a FORESTED COASTAL SLOPE: 8–16u
  of canopy, a 0–6u strip of grass at −1.2..−1.8u, then coastal rock and sea, all 10–24u from the rim. The
  home shelf's last grass before the drop sits at y ≈ 1.42.
- **Stock does not hide the step under the forest.** At both ends of the forest run, the change from
  terrace level to forest level is OPEN grass. The registered band (−0.3..−0.9) is only half of the 1.2u
  drop, so on B's 10–90% scale it would read wider. That is post hoc and not scored.
- **Stock's ~1u grass step is a gentle RAMP:** ~12u wide (p10 8, p90 22), ≤ ~8°, never a lip, and
  mostly in open ground. That is the vocabulary for any authored grass level change.
- **The coast predictions were wrong about the class.** Our west coast there is a low grass shore, not a
  cliff. So C2 (low cliff tops are rare, 5%) is moot for this site.

### What it means for (c)

- **(c1) A shelf from the forest out to our EXISTING shore, 66–78u away.**
  - *Lawful in its parts:* level grass lowered ~1.2u by pure-Y displacement (the `world-hill` mechanism,
    passed in-game, with UVs that stay lawful); two ~12u ramps at the forest run's ends (stock's measured
    step); the shore's top lowered ~1.2u; the forest carried verbatim and welded to the shelf.
  - *But its ARRANGEMENT isn't the home's.* A 45–60u-wide lowered coastal plain beside a massif has no
    exemplar here (the home's lower ground runs only 10–24u to the sea). It is composition, not carry.
- **(c2) Re-seat the massif ~50u west-southwest so its forest side BECOMES our west coast,** carrying the
  home's forested coastal slope and coastal rock as the shore.
  - *Gains:* the home arrangement, verbatim. The remaining junctions are the sea edge and the two lateral
    coast joins: the coast-mosaic class, which has proven machinery (Path D's S6 region-carry idea).
  - *Costs:* it re-seats R4 (its placement gates; R5's gap grows) and re-authors that stretch of coast.

Either way, the authored ground must follow P-B1: ramps ~8–22u wide at ≤ ~8°, and no lips.

### ERRATUM (2026-10-06, found while designing the coast-join study) — P-C1's instrument misread a cliff

P-C1 tested "flat over the ray's last 10u" (range ≤ 1.0u). A cliff whose WALL lies inside that window
reads as a 2.6u range. That is exactly what happened: the window took in the topo-58 tris at the end
of every ray. Re-measured at 0.25u steps on the same 33 rays, the coast there is a **CLIFF**:
- grass flat at y 3.20 right to the edge (p10 = p50 = 3.20);
- then a topo-58 wall of plan run 1.00u, falling to a foot at y p50 0.48 (~70°).

That is `world-island`'s minted cliff (land 3.2, rim_run 1.0). **P-C1's claim holds; its registered
verdict above is wrong for an instrument reason.** The "low grass shore" reading in the RESULT, and in
the chat report, is retracted. P-C2 (low cliff tops ≤ 2.2u are 5% of stock) therefore DOES apply: (c1)
would have lowered our cliff top to ~2.0, into that rare class. The lesson is the brief's: an instrument
needs a positive control. B had one; C did not.
