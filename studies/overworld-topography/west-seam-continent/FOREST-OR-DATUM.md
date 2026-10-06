# Forest or datum — what fails a bare carry's base? (and the context screen built on the answer)

Registered 2026-10-06 BEFORE the instrument (`context_screen.py`) existed or ran. Owner: "keep building
measuring tools or studying."

## The open question

The sector map found that the horseshoe's failed stretch is BOTH things at once:
- the one forest contact (H1a: 100% vs 99%);
- the one stretch where the rock ends high above the lawn (H2: E > 0.75u, 100% vs 94%).

One site cannot say which one CAUSES the failure. Every remaining R4/R5 option depends on the answer:
Uaho, comp20, crag, or anything else carried onto the continent.

## The discriminating case: Uaho

Uaho's July carry is the second verdict-bearing carry. It went onto a flat 3.2 bench with the SAME
construction, `world-mountain`'s ground apron rising to the rigid rim. It was **approved**: "the cliff
is great — walkable, seams against the grass great". Every fixed round was a grass mechanism (normals,
clamp streaks, a crack, a mint hole), never a base-transition complaint. The record also says its rim
deltas reached ±3u after de-tilt, and that "at real Uaho the ground rises to the foot."

**Labels:**
- horseshoe take 1: the forest run FAILED, the rest PASSED (the sector map's sets);
- Uaho July: every stretch PASSED.

## What is measured, per ~1u rim station, on both carry units (`_mountain_blob`, as the carve builds them)

- **C, the home contact,** by the global stock soup: grass / forest / coastal rock (58) / other / open.
- **E, the seat excess:** the de-tilted rim height minus the de-tilted rim MEDIAN. That is the carve's own
  seat on a flat lawn (`DY = ground_med − rim_med`). On the horseshoe it is cross-checked against the
  sector map's E.
- **R, the home approach:** grass-only home ground at 2/4/8u outward, minus the rim height. Does the home
  grass rise to (meet) the foot?

## Hypotheses

- **H-forest:** a stretch fails iff its home contact is forest.
- **H-datum:** a stretch fails iff E > +0.75u, whatever the contact.
- **H-context (the mechanism claim):** the carve's grass apron REPRODUCES a home context of grass that
  rises to the foot. It cannot reproduce forest. So raised stretches are safe where their home ground is
  rising grass, and fail where it is forest.

## Registered predictions

- **P1, H-datum is falsified as a sufficient cause.** Uaho has grass-contact stretches with E > +0.75u
  totalling ≥ 10% of its rim, and they passed.
- **P2.** Inside the horseshoe's PASSED set, the stretches with E > +0.75 (the sector map's 6%, ~14u) are
  grass contacts.
- **P3, H-context.** At the raised (E > +0.75) GRASS stretches of both donors, the home grass at 2u
  outward sits within 1.0u of the rim (it meets the foot). At the horseshoe's forest stretch, the
  nearest grass outward lies ≥ 1.0u BELOW the rim (the forest, not grass, meets the foot).

If P1 fails (Uaho has no raised grass stretches), the discriminant is unavailable: both hypotheses
survive, and the screen must flag raised stretches of ANY class.

## The tool: the context screen (built on whatever survives)

`context_screen.py --donor BX,BY[-BX2,BY2]` classifies every rim stretch of a carry unit as:
- **SAFE:** grass contact at/below the seat, or raised grass whose home ground rises to the foot;
- **FOREST:** the context must come along, or the stretch must not face open lawn;
- **UNTESTED:** a contact class with no verdict yet, e.g. coastal rock, desert;
- **DATUM:** raised with no rising home grass, if H-datum survives.

It reports the share of each, as rim runs with positions.

**Calibration, required before any donor row is quoted:**
- the horseshoe's FOREST run must reproduce the sector map's (29 ± 3u);
- Uaho must screen ≥ 90% SAFE by length, since it passed.
A screen that flags Uaho fails its own calibration.

**Then:** the four qualified donors (uaho, crag, horseshoe, comp20) and every stock massif ≥ 100 tris.

## Declared limits

- **Two verdict-bearing sites.** The screen's SAFE class is only as wide as those verdicts. UNTESTED
  means untested, not unsafe.
- **Uaho's verdict covers the WHOLE carry** (one approval), so it cannot tell which stretch carried the
  weight.

## RESULT

(appended after the run, below this line; nothing above edited)

Run 2026-10-06 (`context_screen.py`, data `context_screen.json`). **Cross-check:** the per-station E equals
the sector map's at all 307 horseshoe stations (|diff| p90 0.00).

### The registered score

| | measured | verdict |
|---|---|---|
| **P1** Uaho raised grass ≥ 10% | 3.5% (3.4u). Uaho's E: p50 −0.04, p90 +0.81, max +1.97. Its raised stretches are 3.4u of grass + 8.0u of coastal rock. The record's "±3u" did not survive measurement | **FAILS**: the discriminant is unavailable from Uaho |
| **P2** horseshoe passed-raised are grass | 16.6u raised in PASSED; 18 of 20 stations grass | **HOLDS** |
| **P3** H-context mechanism | raised grass (18.2u, both donors): home grass at 2u within 1.0u on 100%. But the forest stretch's nearest grass is ≥ 1.0u below on only 58%: some forest stations reach coastal rock before any grass | **FAILS** as registered |
| **calibration** | horseshoe FOREST run 25.7u (want 26–32: the FOREST class is raised-only, and its end stations sit at/below the seat; forest CONTACT is 28.4u). Uaho SAFE 74% (want ≥ 90) | **FAILS**: the screen is NOT quotable for donor rows |

### What the verdicts can and cannot say (post-registration)

- **Uaho's raised coastal-rock stretch can't be used.** It lies 5–6u from its blob centre, deep in the
  ALCOVE NOTCH, the part of the July carry that had its own floor carry and aperture plug. It is not open
  lawn. Uaho's open outer rim (r ≥ 12u, 49u) never rises above +0.62.
- **The one PASSED horseshoe station above the failed minimum (+1.13) is a FOREST contact** at (1436.2, −486.0),
  3.2u outside the take-1 box: the forest run's own SE end, the corner of later complaints. It is a label
  artifact, not evidence.
- **Excluding it, every passed station sits ≤ ~+1.1 and every failed station is forest at +1.13..+1.69.**
  So the verdicts are separated perfectly by BOTH:
  - **H-datum** with a threshold near +1.12;
  - **H-forest-raised** (forest contact AND raised).

  **They cannot be told apart by the evidence in hand.**
- **Pure H-forest (any forest contact fails) IS falsified:** Uaho's forest contacts at E +0.26..+0.58
  passed.

### THE STOCK-WIDE SCREEN (post-registration; uncalibrated, so read as structure, not verdicts)

Of 23 stock massifs ≥ 100 tris that form a carry unit (2 ranges skipped, 2 refused by `_mountain_blob`):
- **Only TWO have raised rim stretches at all:**
  - the horseshoe (raised forest);
  - **(14-15,14), the Path D mesa donor:** 14% raised forest + 5.3u of raised RISING GRASS up to E +1.48.
- **Every other massif's rim sits at or below its own seat everywhere** (SAFE / SAFE-SEAT / UNTESTED-low).
- crag: 100% SAFE-SEAT (desert contacts). comp20: SAFE 68% + SAFE-SEAT 32% (buried coastal rock). Uaho:
  SAFE 71%, SAFE-SEAT 13%, the notch 16%.

So for every donor except those two, **the forest-or-datum question does not arise**: a bare carry
leaves no raised foot. Their open risk is the CONTEXT CLASS of their buried contacts (coastal rock 58,
desert 17), and no verdict covers those classes yet on open lawn.

### The decisive test, if the owner wants the question settled

The (14-15,14) mesa's 5.3u of raised rising grass is the ONLY stock stretch that separates H-datum from
H-forest-raised. Path D carried that donor through many judged rounds. **Before any bench build, its
record should be read** (own prior art first): did any round seat that stretch, unlifted and unburied, on
open lawn?
- If yes, the verdict may already exist.
- If not, a bench carry of that stretch plus one owner look settles the question.

### ADDENDUM (post-registration, not scored): the Path D record read against the screen

The (14-15,14) mesa was Path D's donor, posed yaw 0 and translated on the 4u lattice so its centre landed
on the bench centre (416, −512); here (−576, +416), from the block's rock bbox. Its lift rounds (6–8) raised
the bench grass to the whole weld line. The owner's still of "the hill" was taken at **(439, −496)**
(GROUND-JUNCTION-SYNTHESIS.md, the localisation snaps).

- **The 12 rim stations nearest that still are ALL raised FOREST contacts** (E +1.8..+2.6), 8.5–10.7u
  away.
- **The mesa's raised RISING-GRASS stretches** (39.4u, of which 5.3u at E ≥ 1.3, max +1.48) lie ≥ 39.8u
  from it.
- **No Path D complaint is recorded at that grass sector.** The other photographed defect, the seams at
  (375, −508), was decoded as stitch-tolerance tears, not a lift shape.

**Read together, the three sites:**

| site | raised forest | raised grass at similar height |
|---|---|---|
| horseshoe take 1 | FAILED at +1.13..+1.69 | none above ~+1.1 |
| Path D mesa, lift rounds | the hill complaint lands on it (+1.8..+2.6) | no complaint, up to +1.48 |
| Uaho July | forest contacts at +0.26..+0.58 passed | none above +0.84 |

No single datum threshold fits both the horseshoe (fails at ≥ +1.13) and a Path D grass stretch passing at
+1.3..+1.48. So this **leans against H-datum and toward the forest context.**

**Its limits, stated plainly:**
- an ABSENT complaint is not a pass verdict;
- the Path D lift field was bench-wide, not `world-mountain`'s apron;
- 5.3u is a short stretch, and the owner may not have looked there;
- the cross-site E comparison assumes comparable seats (both are rim-median-to-lawn).

It is evidence, not a decision. The one clean test is still a bench carry of a raised rising-grass
stretch at ~+1.5u, judged by the owner.
