# THE TERRACE WALL — prediction registration (BEFORE building)

2026-07-30. Per [`SYNTHESIS-RECONSIDERED.md`](SYNTHESIS-RECONSIDERED.md): the discriminant it
proposes has "never predicted anything prospectively", so the terrace wall runs as a
**prediction-registered test** — this file states the expected outcome before any code exists,
so the discriminant itself is what gets falsified. Written before the first line of the builder.

## The claim under test

> **THE DISCRIMINANT.** Synthesis passes when the target is expressible as an exact-linear TILE
> LANGUAGE (geometry, coastlines, cliff profiles, relief, band-quantized courses). Synthesis
> fails when it attempts hand-authored, non-lattice, CONTINUOUS-FLOW texture organization
> (massif flanks, gore panels, canopy, ecotone dressing).

An ex-post sort over n≈7 falsifications. This is its first prospective use.

## The test

Build THE TERRACE WALL from the decoded interior rock-wall tile language
(`rock_wall_language.py`, 2026-07-12: 8945 tile groups / 13929 neighbour pairs / 48 blocks —
`studies/overworld-topography/README.md` "The interior ROCK-WALL TILE LANGUAGE"):

- courses of ~4.7u-height 128×128px wall quads (p90 5.4; the stacked-wall 4–10u faces);
- vertical ROLE bands: crest (rows 3–4 × cols 4–7) → upper body (rows 6–9 × cols 0–3) →
  lower body/base (rows 7–10 × cols 6–9; the true foot course row 10 lives only here);
- u-continuation ALONG the wall by windowed atlas adjacency with 4-col band wraps
  (window-translate at wraps — the coastal smear lesson), v-descent through the role rows;
- lattice phase from data (dual u-phase families ≈ staggered courses; v phases 64/80px);
- a topo-13 grass mid-shelf pinned y 15.7–18.3 where a two-level build wants one; **no ramp**
  (no ramp class exists in stock — adding one is off-language);
- bench: the Disc9 junction landmass (or a fresh Disc9 mint) — footprint budget non-binding,
  THE ONE-SITE WORLD LAW void in the synthetic namespace.

Constraints carried from the record, all still binding: THE MOAT LAW v2 (walkable synth ground
ends ≥~4u inland of the outline), THE ASYMMETRIC STRIP, THE FORM LESSON (never warp real
bytes — this build mints, it does not bend carries), faces land on lowland grass, THE
SEA4-UNDER-LAND LAW + the coast-nav stamp on any new coast.

## REGISTERED PREDICTION

**PASS**, specifically:

1. The frozen offline eyes and an L7-class gate battery (band-membership per course role,
   one-window-per-tri, atlas-adjacency continuation rate in the measured ~46%+11% regime,
   texel-density band, weld/winding/census) go green without per-site hand exceptions.
2. The owner's in-game verdict reads it as FF9 interior rock wall — no "staircase" call, no
   "no form to it" call — on the first or second playtest round, not an 8-round fix ladder.

**Why this prediction:** the terrace wall is (a) fully decoded, (b) explicitly classified a
TILE LANGUAGE — course-quantized like the coastal column language that shipped — and (c) in
the category that has passed repeatedly (blob coastline, 73° cliff profile, relief, island E,
THE SPUR).

## Falsification semantics — declared in advance

- **If it FAILS on form** (jank/stacking/staircase verdicts despite green gates): THE
  DISCRIMINANT IS REFUTED — "tile language vs continuous-flow mural" is not the real boundary,
  and the record's seven verdicts need a different sort. That result is *more* valuable than a
  pass; record it in SYNTHESIS-RECONSIDERED and stop treating the category as safe.
- **If it fails on plumbing** (gates red offline, never reaches the owner): not a discriminant
  verdict either way — fix or abandon the builder; the prediction stays open.
- **If it PASSES:** the discriminant survives its first prospective test; the next synthesis
  target may cite it as *tested-once*, never as law.

Prerequisites already met: the read/write disc split (all verbs threaded), the coast-nav
emitter default + 0.8s stamp, the junction carry into 9013 (step 2 — in flight).

---

## SCORED — round 1 in-game: FAIL (2026-07-30)

Built (`terrace_wall_t1.py`), offline gates green, deployed to the (416,−512) Disc9 bench,
owner-playtested. Verdict, verbatim: *"it's a mess … the top grass is all banded, and the
sides look stamped together. some of the grass-cliff transition tiles are flipped upside
down. the bottom third is especially messy, even missing faces."* Wall REVERTED; the bench is
byte-identical to pre-wall (`backups/terrace-t1-prewall.20260730-173247`). Renders + the
playtest engine log archived in `out/terrace_t1/`.

**Defect classification — implementation vs form, because the scoring depends on it:**

- *Top grass banding* — **implementation, of a SOLVED class.** `junction_compose` L3 exists
  precisely because naive per-cell random (quad,ori) bands; T1 re-implemented the naive
  version instead of reusing the folded policy. [[feedback-own-prior-art-before-new-lanes]]
  fired AGAIN, the same day the handoff recorded its last firing.
- *Flipped grass-cliff transition tiles* — **implementation.** One exemplar's v-orientation
  was applied to every instance of a tile; stock orients per instance, and u-direction /
  mirroring is unrecoverable from min/max rects. Needs a per-instance orientation decode.
- *Missing faces, bottom third* — **implementation + gate gap.** Zip-tri winding by radial
  outward test fails on concave jag sections; the watertight gate counts once-edges, not
  winding — the D3 provenance-winding gate existed in `junction_compose` and was not ported.
- *"The sides look stamped together"* — **the form verdict on the continuation itself** —
  the discriminant's own territory — though confounded by the orientation defects above.
- *Overworld lag* — **unattributed.** The engine log shows no exception spam; transient CPU
  contention from concurrent sessions is the owner's own read and the likelier cause.

**Scoring against the declared semantics:** NOT a clean discriminant refutation — the build
did not faithfully implement the language (two known-solved defect classes re-derived
naively, one gate unported), so "fails on form despite green gates" is not established.
But the first of the two allowed rounds is consumed, and the owner invoked the meta-law:
*"looks like we don't have enough study knowledge to synth yet."* **The synthesis rung
PAUSES on that ruling.** A resumption must start with an anatomy study (per-instance tile
orientation/mirror statistics, course-transition decode) and must REUSE the folded
generators — L3 for tops, the D3 winding gate — rather than re-deriving them. The
prediction itself stays open: one round remains, and it may only be spent on a build that
faithfully implements the language.
