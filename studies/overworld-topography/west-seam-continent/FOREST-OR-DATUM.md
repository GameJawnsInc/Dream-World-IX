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
