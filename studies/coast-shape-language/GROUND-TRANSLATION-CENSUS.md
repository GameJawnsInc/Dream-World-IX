# THE GROUND TRANSLATION CENSUS — which retile pairs are actually lawful (2026-08-02)

## The question

`GroundRetile`'s mains branch is gated on `GRASS_TOPOS`, so only a **grass** source can
classify: the original census measured `grass -> X` and nothing else. The delta itself is
family-agnostic arithmetic, so the open question was empirical — **do a non-grass family's
mains occupy their rect the same way grass's do?**

## Measured (disc 1, the user's own install)

**All seven families have identical mains rects: 0.1230 x 0.0615.** They are congruent, so
the translation is a pure rigid shift. Nothing architectural blocks `X -> Y`.

| family | mains tris | blocks | distinct relative uv-triangles |
|---|---|---|---|
| grass | 12110 | 129 | 3524 |
| desert | 10643 | 120 | 2790 |
| snow | 2406 | 23 | 1197 |
| brush | 1900 | 52 | 525 |
| scrub | 1807 | 44 | 89 |
| canyon | 1533 | 28 | 946 |
| dunes | 690 | 9 | 224 |

### The layout-overlap table — the actual answer

Share of the source family's mains tris whose *relative* uv-triangle (position within its
own rect) also occurs in the destination family:

|  | brush | canyon | desert | dunes | grass | scrub | snow |
|---|---|---|---|---|---|---|---|
| **brush** | — | 0.009 | 0.009 | *0.298* | 0.012 | 0.000 | 0.000 |
| **canyon** | 0.022 | — | 0.004 | 0.000 | 0.003 | 0.007 | 0.000 |
| **desert** | 0.005 | 0.001 | — | 0.002 | **0.762** | 0.002 | 0.244 |
| **dunes** | *0.332* | 0.000 | 0.004 | — | 0.009 | 0.000 | 0.000 |
| **grass** | 0.011 | 0.001 | **0.708** | 0.004 | — | 0.007 | 0.300 |
| **scrub** | 0.000 | 0.003 | 0.003 | 0.000 | 0.003 | — | 0.000 |
| **snow** | 0.000 | 0.000 | 0.202 | 0.000 | 0.219 | 0.000 | — |

## Findings

**1. `grass <-> desert` is the strong pair, and it is exactly the pair that was measured
and proven in-game.** 0.708 / 0.762 — far above everything else. The desert bench works
because these two families genuinely tile their rects the same way, not because the
mechanism generalises. **The retile's in-game success is evidence about one pair, not
about the operator.**

**2. `desert -> grass` (0.762) is the single strongest translation in the table — stronger
than the proven `grass -> desert` (0.708).** So the answer to "can we retile FROM desert"
is: yes, and specifically **`desert -> grass` is the best-supported translation in the
whole vocabulary.** That is the one `X -> Y` extension the data justifies.

**3. A live concern in SHIPPED behaviour.** The kit today permits `grass -> snow`,
`grass -> canyon` and `grass -> scrub` with no warning, and their layout agreement is
**0.300, 0.001 and 0.007**. Those translations land inside the target family's rect — so
they sample the right *texture* — but they use sub-tile arrangements stock essentially
never uses for that family. They are not wrong the way a wrong atlas is wrong; they are
wrong the way invented massing is wrong, which is the failure mode this arc has been
falsified on repeatedly. **`grass -> desert` is the only currently-permitted target with
measured layout support.**

**4. `brush <-> dunes` (0.298 / 0.332) is a weak second pair**, and every remaining
combination is at or near zero. There is no universal ground translation.

## What this does NOT license

The overlap metric is a strict exact-match on relative uv triangles. A low share means the
output uses arrangements stock does not use for that family — it does **not** prove the
result looks broken, and no rendering evidence was gathered here. Converting these numbers
into a refusal or a warning needs the render gate at matched camera geometry, on the model
of THE PEER GATE.

## Recommended next steps, in order

1. **Warn (do not refuse) on the low-support targets.** `--ground snow|canyon|scrub` from
   grass should say its layout support is 0.30 / 0.00 / 0.01 against `grass -> desert`'s
   0.71, so the operator knows it is off the measured path. Cheap, honest, no behaviour
   change.
2. **Implement `desert -> grass`** — generalise `GRASS_TOPOS` to per-family topo sets (the
   interior census already has them: dirt-desert 16-23/41, scrub 4/5/6, snow 27/28, canyon
   45/46) and gate the new direction on this table. It is the best-supported pair we have.
3. **Render-gate the weak pairs** before deciding whether they should refuse outright.

**Deliberately not implemented in this session.** Step 2 touches the mains, sand, wall and
foam branches together, and this session has already produced one tail-end geometry fix
that regressed a clean case (`EXCISE-V2-PREDICTION.md`, attempt 2). The measurement is the
deliverable; the implementation deserves a fresh context.

Regenerate: `py studies/coast-shape-language/ground_translation_census.py --disc 1`

---

## WHAT `desert -> grass` ACTUALLY UNLOCKS TODAY — verified independently 2026-08-02

The implementation is correct and the mains now classify (355 on the comma island, where
it was 0). But its **practical intersection with the carryable donor pool is empty**, and
the implementing round did not state this — it demonstrated the retile gate passing on
`(14,1)`, a *continental* block that fails `land-fit` and can never be carried as an
island.

Every carryable unit, re-checked here against `--ground grass`:

| donor unit | detected src | result |
|---|---|---|
| `(9,5)+2x3` the comma | **desert** | retile builds, **full carry FAILS** — 395 unclassified (rock 49 x294, brush 38 x101) |
| `(6,4)+2x2` | snow | refused by the layout-support bar (0.219 < 0.50) — the new gate working |
| `(7,17)+4x2`, `(10,17)`, `(10,18)` | grass | no-op, already grass |
| `(12,10)` | grass | (was refused as "no dominant family" on 11 tris — fixed, see below) |

**So no landmass we can carry can currently be restyled.** The one desert-source carryable
island is blocked by its own mountain massif, and declining to mint a passthrough for that
massif was correct: measured map-wide on disc 1, **brush(38) shares 534 edges with desert
and ZERO with grass** (verified independently here, not taken on report). Retiling the
ground out from under that fringe would place brush on grass — a configuration stock builds
zero times.

**The honest status: `desert -> grass` is a correct capability with no current customer.**
It becomes useful the moment excise v2 lands a desert island without a massif, or a
rock/brush translation is measured.

### One over-strict refusal fixed

`_mains_family` refused donor `(12,10)` — a real carryable 1x1 island — because it read
`{'grass': 11}` and 11 fell below the ambiguity floor of 12. But there was no competing
family at all. **A unanimous read is not ambiguous**; the floor exists to stop a few stray
tris outvoting a family that is actually present. Now: unanimous (no runner-up, >= 4 tris)
is accepted; contested reads still require the margin AND the floor. Both cases are tested.
