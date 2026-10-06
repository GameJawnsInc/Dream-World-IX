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
