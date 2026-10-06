# Uaho's July record read against its stretches — does the approval cover a buried coastal-rock base?

Registered 2026-10-06 BEFORE the instrument (`uaho_july_stretches.py`) existed or ran. Owner: "yes, read
Uaho's July record against its stretches." Follows [`FOREST-OR-DATUM.md`](FOREST-OR-DATUM.md).

## The question

Every stock massif except the horseshoe and the Path D mesa sits at/below its seat all round, so the
forest-or-datum question doesn't arise for them. What remains open for comp20 (32% coastal rock), Uaho
(coastal rock + its notch) and crag (desert) is the CONTEXT CLASS of their buried contacts. No verdict yet
covers a buried coastal-rock base facing open lawn.

Uaho's July carry was APPROVED: "the cliff is great — walkable, seams against the grass great" (round 6),
then "closed" (round 8). Did its buried coastal-rock stretches face open bench lawn when it was approved?

## Method

**1. The July bench is gone, so it is rebuilt.**
- Neither the deployed (2,19) bench nor its `.pristine-r31s42` input survives. The live blocks were
  rewritten Jul 24–26, and the Aug 27 snapshot is post-July.
- So: re-mint the recorded bench, `world-island --center 160,-1246 --radius 31 --lobes 1 --patches 0
  --seed 42`, into a SCRATCH mod folder with today's kit.
- Then run `carve_mountain(near=(160,-1246))` in memory, exactly as the identity test does.

**Declared approximation:** today's mint differs from July's at least by the ring-conformity fix (July's
one-tri hole). Any other drift shows up in the calibration below.

**2. Calibration (required before any reading):** the rebuilt carve must reproduce the record's
placement: **rot 0, blob centre (162, −1246), clearance 11.1u** (to ±2u / ±1.5u).

**3. Per Uaho rim station** (`context_screen` classes: contact, E, class), on the rebuilt bench:
- NOTCH vs OUTER RIM: the station's distance from the blob centre (< 12u = the alcove notch);
- the bench ground in front: march outward over the carved bench and record the open-lawn width
  (topo 0 at bench height) before the bench coast (topo 58 / sea).

## Registered prediction

- **P-U1.** At least 70% of Uaho's BURIED coastal-rock rim (contact = crock, E ≤ 0.75) lies on the OUTER
  rim (≥ 12u from the blob centre). It faces ≥ 6u of open bench lawn before the bench coast. So the July
  approval covers "a buried coastal-rock contact facing open lawn".
- Also reported, no prediction: the same for Uaho's grass and forest stretches.

## What it means

| outcome | means |
|---|---|
| P-U1 holds | the buried coastal-rock class has ONE verdict (Uaho). comp20 and Uaho screen clean for a flat-lawn carry; the first carry still names its own targets |
| P-U1 fails (notch, or they faced the bench coast) | the class stays untested; the first comp20/Uaho carry IS the test |
| calibration fails | the rebuild isn't the July bench; nothing is read from it |

## RESULT

(appended after the run, below this line; nothing above edited)

Run 2026-10-06 (`uaho_july_stretches.py`, data `uaho_july_stretches.json`). The scratch re-mint wrote
the same two blocks the record describes: (2,19) and a 37-tri spill into (2,18) ("the centre shifted NORTH
to spill into legal row 18").

**CALIBRATION PASS, exact.** The rebuilt carve logs `placement: rot 0deg, blob centre -> (162,-1246)
(clearance 11.1u)`, matching the July record to the digit.

### The registered score

| | measured | verdict |
|---|---|---|
| **P-U1** buried coastal rock on the OUTER rim (≥ 12u from centre), facing ≥ 6u of open lawn | 0% of 10.9u lies ≥ 12u from the blob centre | **FAILS as registered** |

### Why the registered verdict is an instrument error, and what the direct measurement says

The "< 12u from the blob centre = the alcove notch" proxy was never checked against the alcove itself.
`interior.UAHO_ALCOVE` = x 31.0–40.5, z −38.5..−30.5 in the donor frame: **EAST** of the blob centre
(28.3, −35.7). Both coastal-rock stretches are on the **WEST** side:

| stretch | home x | E p50 | open lawn in front | from the July teleport (136.5, −1245.5, "face east") |
|---|---|---|---|---|
| buried coastal rock, 10.9u | 19.4–27.7 | −0.08 | p50 21.5u, then the bench coast | 16.9–27.8u, bearing −26..+10° |
| raised coastal rock, 8.0u | 19.9–23.7 | **+1.49** | p50 20.0u, then the bench coast | 17.1–21.7u, bearing −16..−1° |

Uaho's blob is narrow (24u wide), so its WEST rim simply runs close to the centre. Both stretches faced
open bench lawn, **straight ahead of the owner's July viewpoint**, and the carry was approved ("looks good";
"the cliff is great — seams against the grass great").

**On the rebuilt bytes, the July carve LIFTED a grass bank to the raised stretch.** Carved-bench grass over
the 3.2 lawn, outward from its foot: 1u +1.15, 2u +0.93, 4u +0.53, 8u +0.13, 12u +0.01. That is the same
apron-lift "knoll" construction, at the same height (+1.49 vs the horseshoe's +1.46), as the horseshoe
take-1 arc the owner rejected. The buried stretch gets no lift (flat within ±0.08).

**So, with the proxy replaced by the direct measure:**
1. **The buried coastal-rock class HAS a verdict.** One site, approved, in direct view.
2. **H-datum is falsified as a sufficient cause.** A raised (+1.49), lifted, non-forest stretch in direct
   view passed. The same height and construction failed on the horseshoe only where the home context was
   FOREST. The surviving rule is the forest context: a rock face that stood behind a forest at home reads
   wrong when carried bare.
3. **The same proxy error sits in FOREST-OR-DATUM.md's post-registration note** ("deep in the ALCOVE
   NOTCH"), corrected there by erratum.

**Limits:**
- one stretch, 8u, one site;
- the July verdict covers the whole carry, though this stretch was in its primary view;
- the bench is a rebuild with today's mint, but its placement calibrates exactly.

**Process note:** this is the second unvalidated proxy this session; the grass-step study's coast check
was the first. A proxy needs the same positive control as an instrument.
