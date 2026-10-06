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
