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
