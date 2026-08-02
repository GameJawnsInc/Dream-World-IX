# THE DONOR-RECT EXCISE — registered 2026-08-02, before implementation

## The gap this closes

Of 57 disc-1 landmasses, **7 are carryable**. The disqualifier is almost never the island
we want — it is a *neighbouring* mass crossing the donor rect frame, which the `land-fit`
gate correctly refuses because a cropped mass ends in a ruler-straight 64u slice of land
hanging in mid-air. Casualties include the three most interesting objects in the game:

* `(6,6)+2x2` — the **waisted island**, the only object in FF9 that reads AS an isthmus;
  disqualified by 43 cells of Forgotten Continent in one corner.
* `(5,15)+3x2` — **Daguerreo**, 9264u², 31.4u relief, the only chain anchor with a mountain.
* `(3,11)+2x4` — the **sinuous island**; three neighbours.

**Excise** = drop the foreign mass from the carry and re-zip sea over its footprint.

## Why this is the cheap authoring job

The patch lands on **sea4**, the deep-ocean sheet. Measured this session on `(6,6)+2x2`:

* sea4 is a **single flat plane — every one of 3075 verts is at y = 0.000**;
* its UV vocabulary is a **2×2 quadrant scheme** (u breaks 0/0.5039/0.9921, v breaks
  0/0.5079/1.0) and the quadrant is **uniformly distributed across world-cell parities**,
  i.e. the anti-tiling choice is genuinely free — a patch cannot pick a *wrong* tile;
* only **2 IDALL values** appear (228 dominant, 224).

No land, no land/sea junction, no wall, no walk surface, no height field. It is the one
authoring job in this arc that **cannot mint a walk trap** — which matters, because THE
DEFECT FOLLOWS THE AUTHORSHIP and every previous authoring round paid for it.

## What was measured before designing (not assumed)

1. **Terrain separates cleanly into vertex-connected components.** `(6,6)+2x2` yields
   exactly 3: the waisted island (578 tris, contained) and two frame-crossers (70 and 39
   tris). The drop set is therefore well-defined — no component shares a vertex with
   another.
2. **sea4 is CUT under land, not continuous** — only 11% of the island's plan cells carry
   any sea4 (the fringe). So an excise is *not* a pure drop: it must EMIT a patch.
3. **The hole boundary exists and is traceable.** 219 boundary edges over 218 boundary
   verts; 132 of them are interior (not on the rect frame), spanning the island extent.
   *A first pass reported "no island hole" — that was the instrument: connected components
   of the boundary graph merge two disjoint cycles that share a single junction vertex.
   Cycles must be traced as cycles.*

## The build

* `meshedit.boundary_cycles()` — trace true cycles (junction-safe), and
  `meshedit.flat_patch()` — fill a ring at constant y with free-choice quadrant UVs.
  Hermetic, unit-tested, no game access.
* `transplant.excise_plan()` — classify components, select foreign ones, build the
  `DropTris` set for every part and the `EmitTris` sea4 fill.
* `world-transplant --excise` — the CLI surface.

## Predictions (falsifiable, scored on completion)

* **E-1** Excising the two frame-crossers from `(6,6)+2x2` makes the **`land-fit` gate
  pass**, so the waisted island becomes carryable. This is the whole point; FALSIFIED IF
  the gate still refuses, which would mean the disqualifier was never the neighbours.
* **E-2** The fill welds **exactly** — every boundary vertex of the emitted patch is an
  existing sea4 vertex at 1e-4, no new boundary verts. *A repair that is not exact is a
  hole* (measured at 26 px of background last time this was relaxed). FALSIFIED IF any
  patch boundary vertex fails to match.
* **E-3** The carryable pool **at least triples** (7 → ≥21 mass-sets) once frame-crossing
  neighbours stop disqualifying a rect.
* **E-4** The emitted patch needs **no tone or texture gate** — unlike the ear cover,
  which needed neighbourhood tone matching and cost two playtests, sea4's free quadrant
  choice means any lawful tile is correct. FALSIFIED IF a rendered patch is visibly
  distinguishable from the surrounding sea.

## Stop rule

Offline gates green + the pool measurably widened is the deliverable. **This is a
capability, not a landmass** — nothing gets deployed to the game this round. The Fraying
Tail (or whatever the widened pool now allows) is a separate, owner-chosen build.

---

## FINDINGS (2026-08-02) — the capability ships, with a measured boundary

**E-1 CONFIRMED.** `(6,6)+2x2` — the waisted island, the only object in FF9 that reads
AS an isthmus — went from `land-fit FAIL bbox [0.0, 128.0, -128.0, -10.37]` (land hard
against the frame on three sides) to **all gates CLEAN**: `land-fit ok`,
`weld-audit pairs=0`, `census miss=0 introduced=0`. 109 terrain tris dropped, 17 fill
tris emitted. It is carryable.

**E-2 CONFIRMED — and the exactness check earned its keep immediately.** It failed
first, with 16 near-miss pairs at distance 0.0000: `394.0039` against `394.003906`.
`boundary_cycles` was returning its own 4-decimal *hash keys* as geometry. That is
precisely the defect class this codebase already has a law about — *real donor verts are
off-lattice floats; never hand-round, capture the exact float* — reproduced by a helper
that rounded only to key and then emitted the key. Round to key, emit the float.

**E-3 PARTIALLY CONFIRMED, and the honest number is the smaller one.** At mask level the
pool goes from **28 rects / 4 masses** to **249 rects / 10 masses** (of 14 masses ≥60
cells) — 6 masses that nothing could reach before. But gate-verified, only **3 of 6**
sampled unlocked rects pass. The mask says what *should* qualify; only the gate suite
says what does, and the difference is the finding, not a rounding error.

**E-4 CONFIRMED for tone — but two properties I never predicted were load-bearing.** No
tone or cleanliness gate was needed; free quadrant choice is real. What was not free:

### THE WINDING LAW (cost 73 census misses)

**Stock sea4 winds negative — all 1025 tris in the donor rect.** An otherwise-exact fill
wound positive is **back-facing to the engine's downward ground raycast: it renders as
ocean and registers as void.** And stock sea normals are a shared byte constant like
`(-0.121, 0.9785, 0.1665)`, *not* the `(0, 1, 0)` that looks obviously correct.

Both are now taken from the neighbouring sheet rather than invented, and both are
mutation-covered. Worth recording how this was found: I guessed twice (a degenerate
plan projection, then a collinear crop profile) and both guesses were wrong and cost a
build-measure cycle each. Measuring the winding directly took one command. *Calibrate
the instrument before judging with it* applies to one's own hypotheses too.

### CROSSING IS JUDGED ON LAND ONLY

An island's shallow ladder (sea3/sea5) legitimately runs out to the rect frame while its
coast sits well inside. Testing the whole assembly condemned the very island being
carried. The first version papered over this with a "never excise the biggest assembly"
exception, which worked on `(6,6)` **by accident** and was exactly backwards on a rect
that clips a continent — there the biggest assembly IS the frame-crosser, so it kept the
continent and excised the island. The exception is gone; `land-fit` judges land, so this
does too.

### THE CAPABILITY BOUNDARY, ENFORCED NOT DOCUMENTED

Across the gate-verified sample the discriminant is crisp:

| excised mass | result |
|---|---|
| a bare land crumb (terrain only) | **CLEAN** — (6,6)+2x2, (6,4)+2x4, (8,5)+3x3 |
| a mass owning its own sea3/sea5 ladder | refused — (5,15), (4,13), (14,1) |

When the mass owns a ladder, the vacated region does not abut sea4 all the way round,
the fill cannot weld exactly, and the hairline-crack gate refuses downstream. So
`excise_plan` now **refuses up front with that reason** rather than handing back tweaks
that will fail later — a caller holding tweaks is entitled to assume they are sound.
Extending the fill to rebuild a ladder is the v2 job, and it is a genuinely bigger one:
the ladder is shore-bound, copy-only, and not free the way sea4 is.

**Not done:** Daguerreo `(5,15)+3x2` is still out of reach — its own land crosses the
rect frame, so it is not an excise case at all.

## Shipped

* `meshedit.vertex_components` / `boundary_cycles` / `flat_patch` — hermetic, 11 new
  tests, **all laws mutation-verified** (round-to-key, winding, quadrant clamp,
  union-find, edge-consumption).
* `transplant.excise_plan` — assemblies, land-only crossing test, drop set per part,
  sea4 re-zip, exactness gate, explicit refusal.
* `world-transplant --excise`.

Nothing deployed; this was a capability round, per the stop rule.
