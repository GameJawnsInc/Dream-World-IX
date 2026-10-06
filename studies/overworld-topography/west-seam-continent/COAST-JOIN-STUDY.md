# The coast-join study — can the horseshoe's forest-side coast join our coast, for R4 option (c2)?

Registered 2026-10-06 BEFORE the instrument (`coast_join_study.py`) existed or ran. Follows
[`GRASS-STEP-STUDY.md`](GRASS-STEP-STUDY.md), including its erratum.

## Why

The owner chose **(c2):** move the massif so its forest side BECOMES our west coast, and carry the
donor's own forested coastal slope and coastal rock as the shore. That is the home arrangement verbatim.

**The governing laws** (coast-mosaic LAW INDEX, read before registering):
- **THE LAW:** independently-authored 3D cliffs never meet cleanly; only WATER seams blend freely.
- **THE FUSE LAW:** land never knits, coastlines are components, the water knits.

A partial coast carry meets our coast on LAND at both of its ends. That is the class the laws call hard.
This study measures our specific case before anything is built:
- whether the massif fits there at all;
- what exactly meets what at each end;
- how stock varies a cliff top along a shore;
- what the no-land-join alternative would take.

**The facts in hand:**
- Our coast is `world-island`'s minted cliff: grass flat at 3.20 to the edge, then a 1u topo-58 wall to
  ~0.5 (the grass-step erratum).
- The home forest side: 8–16u of canopy, a 0–6u grass strip at y ≈ 1.4, then coastal rock and sea, all
  10–24u from the rim.
- The home is a small island with a topo-58 rim all round.

## Four parts, each with a positive control

**S1 — THE FIT.** Keep rot 90° (the forest already faces west-southwest). Translate the massif along the
forest side's mean outward direction, 0–80u in 2u steps, with lateral offsets of ±0/4/8/12/16/20u.
- **Score:** the share of the home forest-side coast points (the A1 transects' last grass before coastal
  rock or sea) that land within ±4u of our coastline (the grass|topo-58 edge of the pre-massif host).
- **Constraints:**
  - every non-forest rim station must stay ≥ 6u inside our land;
  - the rim must stay ≥ 8u short of x = 1536 (THE SEAM LAW).
- *Positive control:* at translation 0, the home coast must read 40–65u inland of our coast (sector map:
  our coast at 66–78u from the rim; home coast at 10–24u).

**S2 — STOCK CLIFF TOPS ALONG A SHORE.** Chain every disc-1 grass|topo-58 and grass|sea boundary edge
into shore polylines, and read the rim height along each by arc length.
- **For each rim point:** the shortest along-shore distance to a rim point ≥ 1.2u higher or lower; and
  the max rim change over any 4u of shore.
- *Positive control:* a synthetic shore with a 1.5u rim STEP over 1u, and one with a 1.5u RAMP over
  16u, must read as ≈1u and ≈13u.

**S3 — THE JOINS AT THE BEST SEAT.**
- **The two ends:** where the carried home coast stops. These are the outward rays of the first and last
  forest-contact stations, ±6 stations into the grass-contact sides.
- **At each end, report:**
  - the home rim height (placed) vs ours;
  - the home apron grass vs our lawn just inland;
  - the sea parts present within 4u of the coast foot on each side: home stock Sea1–5 vs our
    pre-massif sea overrides.
- *Calibration:* our rim must read 3.20, and the home forest-side rim ≈ 1.4 (the grass-step finding).

**S4 — THE NO-LAND-JOIN ALTERNATIVE: carry the WHOLE home island** (`world-transplant`, a proven
verbatim region carry; the water knits).
- **The island:** flood the home land (lower-world terrain cells) connected to the massif. Report its
  block footprint and any FOREIGN land in those blocks (other islands that a region carry would bring
  or have to excise).
- **Room for it:** blocks west of our continent (cols 17–20, rows 3–10) that hold no stock terrain AND
  no override in `FF9CustomMap-world`, and the largest free window adjacent to our west coast.
- *Positive control:* block (21,7) must read stock-free and mod-occupied (the R1 mint was over open
  ocean).

## Registered predictions

- **P-S1 (it fits).** A seat exists, within 60u of translation, where ≥ 60% of the home forest-side coast
  points land within ±4u of our coastline and both constraints hold.
- **P-S2 (cliff tops change gradually).** Over stock, a ≥ 1.2u along-shore rim change takes ≥ 8u of
  shore at p10. The p90 of max change per 4u of shore is ≤ 1.0u. Cliff tops ramp; they don't step.
- **P-S3 (the law bites).** At the best seat, BOTH ends pair a home rim ≤ 2.2u with our minted rim at
  3.20 (Δ ≥ 1.0u). So each end needs an AUTHORED along-shore rim transition on our minted cliff, at
  least S2's width long, plus a shallow-band (Wang) re-tile where the two water ladders meet.
- **P-S4 (the alternative is clean but foreign).** The home island's land fits in ≤ 3×3 blocks. That
  footprint carries ≥ 1 piece of foreign land (the plan view showed other land at the corners). A free
  window big enough for it exists west of our coast.

## What each outcome means

| outcome | means |
|---|---|
| S1 fails | (c2) does not fit this continent; back to the owner: (c1), (d), or (c2) as an island |
| S1 holds, S3 holds | (c2) as a partial carry needs TWO authored coast transitions: the hard class, though Path D's CLIFF RE-SKIN joined carried rock to a minted shore in its own vocabulary (owner-passed). S2 gives the transitions' length |
| S3 fails (an end matches within 1u) | that end can be a same-height butt join; the authored work shrinks |
| S4 holds | the zero-land-join option exists: the horseshoe becomes an OFFSHORE island, carried whole with its own coast. R4's carve on the continent reverts to the passed lawn. It changes the design (a massif beside the continent, not on it), so it's the owner's call |

## Declared limits

- **Read-only.** Nothing is carved or deployed.
- **A geometric fit, not a carve.** S1 is not a `world-mountain` placement scan; the carve's own gates
  stay the oracle for any real seat.
- **The water comparison is part presence only.** A Wang-level audit belongs to the build (`world-rim-retile`).

## RESULT

(appended after the run, below this line; nothing above edited)

Run 2026-10-06 (`coast_join_study.py`, data `coast_join_study.json`). **All four positive controls PASS:**
- the S2 synthetic step reads 1.0u and the 16u ramp 13.0u;
- at T = 0 the home coast reads +51.4u inland of ours;
- our rim reads 3.20 and the home forest-side rim 1.37;
- block (21,7) reads stock-free and mod-occupied.

### The registered score

| | measured | verdict |
|---|---|---|
| **P-S1** it fits | best seat: translate ~52u along the forest side's outward direction, T ≈ (−44, −29), rot 90°. 83% of the home forest-side coast points land within ±4u of our coastline. 451 seats tried; 77 refused (body too close to the coast); seam clear | **HOLDS** |
| **P-S2** cliff tops ramp | 53 stock shore chains (1,516 rim points). A ≥1.2u change takes p10 8.3u, p50 17.7u of shore (54% of points never change that much within 64u). Max change per 4u of shore: p50 0.00, p90 0.34, p99 1.16u | **HOLDS** |
| **P-S3** the law bites | **NW end:** home rim 1.26 vs our 3.20 (Δ −1.94); apron 1.34 vs our lawn 3.20; water sea4 \| sea4. **SE end:** home rim 1.93 vs 3.20 (Δ −1.27); apron 2.29 vs 3.20; water home **sea3** vs our **sea4**, an adjacency stock never builds (THE LATTICE ADJACENCY LAW) | **HOLDS** |
| **P-S4** whole island | the home island is ~8,356u² in a 3×2-block footprint (5-7, 15-16), with 305 FOREIGN land cells (~1,220u²) in that footprint. **No free 3×2 window west of our coast:** cols 16–20 are real map content | **FAILS** |

**Post-registration (not scored): open ocean around the whole continent.**
- **North:** cols 21–23 × rows 0–2 are free, and a 3×2 window there (21–23 × 1–2) fits the home island
  without crossing the seam.
- **South:** rows 10–13 are free at cols 22–23 and 0–1, but a 3-wide window there would cross the 23|0
  seam.

### What it says

**(c2) as a partial carry FITS.** Moving the massif ~52u west-southwest lands its home coast on ours.
But both ends meet our minted cliff on LAND, with the home rim 1.3–1.9u LOWER: the class the coast laws
call hard. Each end needs:
- **a cliff-top taper:** our minted cliff stepping down along the shore to the home rim. Stock's gradient
  is ≤ 0.34u per 4u of shore at p90, so ~15–25u of shore per end. The texture rule for a lowered wall is
  in-game proven (THE PER-COLUMN LIP ANCHOR, island B: "the cliffs look good now"). A kit verb that
  applies it to a stretch of `world-island`'s minted cliff is NOT established;
- **an inland grass ramp** (P-B1's ~12u) from our lawn down to the home apron;
- **at the SE end, a water re-tile:** the home sea3 against our sea4 (the `world-rim-retile` family).

Plus, everywhere the carried land lands, our sea beneath it must be CUT (THE SEA4-UNDER-LAND LAW), and our
cliff and water ladder between the ends are replaced by the home's. Every piece has a proven law or
machinery behind it; composed together, it is a first.

**The no-land-join version exists, but not on the continent.** The whole home island carried verbatim
(`world-transplant`, "looks verbatim") brings massif, apron, forest, coast and water ladder in their own
context. Its only junction is open water, which knits. It fits in the open ocean NORTH of the continent.
- **Cost:** the horseshoe becomes an offshore island rather than a mountain on the continent, and R4's
  continent carve reverts to the passed lawn.
- **Its own work:** ~1,220u² of neighbouring stock land in the footprint to excise (THE STRUCTURE NOTCH /
  GHOST TONGUE laws), and the area restamp (THE DONOR-AREA LAW).

## For the owner

- **(c2a) the massif on the continent's coast:** four authored joins (two cliff tapers, a ramp pair, a
  water re-tile, plus sea cuts), each law-backed, the combination untried.
- **(c2b) the horseshoe as its own island north of the continent:** everything verbatim, junctions in
  water only; the continent keeps its passed lawn.
