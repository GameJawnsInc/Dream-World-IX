# The ground-family + ecotone decode round — 2026-07-19

Closes the SOON-tier item that **gates** the ensemble-carry and mixed-biome rungs
(`AUDIT-AND-ROADMAP-2026-07-18.md`). Six parallel decode lanes, each shipping a rerunnable
script; every lane then reviewed by three independent adversarial lenses (REPRODUCE /
METHOD / OVER-CLAIM) and a completeness critic. 25 agents, zero errors.

The four gaps the roadmap named were: topo-16 dirt has no translation formula · canyon's
un-chased 3rd v-level · topo 7/62 lumped with 49 unconfirmed · the earmarked 5dp ecotone
strip decode. Two more were added on inspection: **`wall_coastal` is UNMEASURED for
scrub/brush/dunes while a refusal gate reads exactly that field**, and an independent
re-derivation of all 14 shipped constants (the arc's #1 defect class is numbers that do not
reproduce from their cited scripts).

| Lane | Script | Outcome |
|---|---|---|
| topo-16 dirt | `dirt16_anatomy.py` | closed — falsified as a single translation |
| canyon 3rd v-level | `canyon_wall_courses.py` | partial — tally corrected, no 2nd constant |
| topo 7 / 62 / 51 | `mural_partition_settle.py` | closed — productized |
| ecotone strips | `ecotone_strip_decode.py` | closed — 2 pairs proven, table shipped |
| wall_coastal | `wall_coastal_unmeasured.py` | closed for scrub/dunes; brush deferred |
| re-derive shipped | `grounds_constants_reproof.py` | mains confirmed; walls + a new phenomenon |

---

## What shipped

**The live safety bug — `island.py`'s gate failed OPEN.** The test was
`gspec.get("wall_coastal") is False`. scrub/brush/dunes omit the key entirely, so `.get()`
returned `None`, `None is False` is `False`, and the gate **silently allowed an island mint
for every unmeasured family** — precisely the case it exists to catch. Its sibling
`transplant.py GroundRetile.for_donor` was always `is not True` (fail-closed), so the two
chokepoints disagreed. `island.py` is now fail-closed too, with a distinct message for
"measured interior-only" vs "no measured coastal usage". **An unmeasured family is not a
permitted one.**

**Measured `wall_coastal`.** scrub = `False` (touches topo-58 exactly ONCE map-wide — 1
face / 3 tris at ~(17,1), out of 41 scrub-bearing blocks; that face is open-sea with no
gorge counterexample, but n=1 cannot certify systematic usage — this *revises* the older
"scrub never touches topo-58" framing). dunes = `False` (exhaustive scan of all 9
dunes-bearing blocks: **zero** topo-58 edges anywhere — "borrow" is the honest word).

**`STRIPS` — the ecotone strip table (data only).** grass|desert `du=0.52442,
dv=-0.04687`; desert|dunes `du=-0.13476, dv=-0.09863`. Both proven-5dp map-wide, zero
outer-bound spread, exact 0.03125 row pitch. **This corrects a wrong shipped earmark**: the
desert|dunes `dv` was `-0.06738`, off by exactly one row pitch.

> **THE UNION METHOD** (why the earmark was wrong): a fit on ONE side of a boundary can TIE
> between row-alignment hypotheses, because B's row0 is exactly 1 texel (1/1024) shorter
> than rows 1–3 — so different k-consecutive-row windows span numerically identical
> v-extents. Unioning both sides recovers all 4 rows and forces the alignment unique.

Only these two pairs are translated B-columns. The other three real adjacencies are
structurally different art and must not be forced through this path: **desert|scrub** has no
strip at all (59% of the desert-side boundary tris simply wear *scrub's* own mains — literal
texture substitution); **desert|brush** has a brush-side edge column at u[0.72070,0.78125]
that is REFUTED as a lattice translation (515/517 cells fail the per-cell exact-linear test —
scattered independently-UV'd triangles); **grass|scrub** wears a third, previously
uncatalogued shared asset at u[0.34082,0.40332] v[0.83594,0.86621], width 0.0625.

**`MOUNTAIN_ROCK_TOPOS` narrowed `{49,7,62}` → `{49}`.** 7 and 62 were only ever lumped with
49 by assumption. The bytes refute it: topo 7 is **flat walkable** ground (430 tris / 11
blocks, bx 4–9), topo 62 is a **steep stream-bank** paired with topo-51 (480 tris / 10
blocks, bx 16–20). Neither appears even once in any of the four qualified `--donor` rects.
Proven a no-op by A/B carve: Uaho byte-identical (102824B), all other donors identical
refusal. Not merely inert, though — leaving them in meant a *future* donor near those
regions would silently pull walkable ground and stream-bank into its "rock" component.

**Two corrected tallies.** desert `wall_coastal` was commented "12/13 faces, to 5.03u" — a
specimen slice; map-wide is **19/20 faces, to 6.57u**. And the canyon figure has now been
wrong twice in the same way:

> **LAW: cite a wall figure ONLY from a topo-58-FILTERED count; a UV-rect count is a mural
> count.** "748 tris, 0 coastal" was a top-8-slice artifact presented as map-wide (caught
> 2026-07-18). Its replacement "655 tris / 48 faces" is *also* wrong: it counted the red-band
> UV rect topo-agnostically, and **594 of those 655 are topo-49 MURAL**, 1 is topo-59. True
> red wall = 60 tris / 8 faces (topo-58 strict), 43/7 by adjacency. Still zero open-sea —
> **the WALL-CONTEXT LAW's direction has never moved; only its arithmetic keeps breaking.**

---

## Deferred — and why (do not ship these without another round)

- **brush `wall_coastal`** — the lane recommended `True`; **rejected on review.** Its only
  coastal evidence is a single open-sea face, with the other 5 matching faces interior/gorge.
  Scrub was refused on a lone face that was *100% open-sea with zero gorge counterexamples* —
  strictly cleaner evidence. Certifying brush while refusing scrub applies an inconsistent,
  backwards bar. Left **unset**, which now fail-closes. To clear it: a second independent
  open-sea face (the adjacency test is **within-block only** — a cross-block-aware rerun is
  the obvious next probe) or a visual confirmation of the ~(8,15) candidate.
- **A canyon second wall constant** — the shipped pair describes the floor course, but the
  dominant body level (v=0.39453) is already ~44% inside the existing ±0.006 band, and
  discrete-course-vs-continuous-stretch is unresolved on 43 tris. Too thin to mint.
- **topo-16's write-up** — the lane reported its two dominant zones as "matching NONE of the
  shipped constants". The METHOD reviewer cross-checked them against *this same round's*
  strip catalog and found them **byte-identical to the grass|desert and desert|dunes strip
  rows**. So topo-16 is not novel territory at all: **100% of its footprint decomposes into
  three already-decoded desert-family pieces** (mains + 2 strips). Better than reported, but
  the lane's "verbatim layout-stamp carry" recommendation is stale and must be rewritten
  before anyone acts on it. *This is the round's clearest cross-lane defect.*
- **The "secondary mains rect"** — the control lane's own harness printed
  `>=1 required control FAILED` (grass wall ≠ (0,0)) while its headline claimed all controls
  passed; desert and brush print nonzero cross-specimen spread. Behind that is a real
  unexplained phenomenon: a minority of desert/canyon/brush specimen blocks lock onto a
  *second* translated region (desert's reads exactly du=0.85058/dv=-0.11425 on 3/8 blocks).
  Given the topo-16 precedent, this may well be another already-catalogued region. Undecoded.
- **The 7 mains pairs are confirmed; the shipped WALL pairs are not** — they read 2e-5 to
  6e-4 off under a uniform outer-bounds re-derivation. Below the 5dp bar, so not shipped as
  corrections, but they are no longer "byte-exact" claims.

## Is the downstream gate lifted?

**Ensemble-carry: no.** Two of three verdicts are safe REFUSEs; brush is unresolved.

**Mixed-biome / dunes patch carry: half.** The blocker was "dunes has no verbatim donor
window until the ecotone-strip vocabulary exists" (THE NO-ENCLOSED-DUNES LAW). The
*texture-rect* half now exists and is proven. But **a proven rect is not an authoring
recipe** — nobody has measured the per-cell row-placement policy (the mains 2×2 has an
avoid-repeat neighbour policy; the strips have no analogue yet). The next required work is a
placement/emission model, **not more byte-decoding.**

## Method lessons for the arc

- **Naive global-pooled min/max over specimen blocks is unsafe** — it produced a wrong result
  in three separate lanes this round (a dirt19 outlier block, canyon's topo-agnostic UV
  window, wall-coastal's first-try calibration mismatch). Prefer per-specimen fit → majority
  vote with outlier rejection.
- **A UV-rect count is not a topo count.** Two of this round's corrections were the same
  mistake: selecting geometry by atlas rect and reporting it as a class tally.
- **Zero offline-eye renders ran this round.** Every prior successful rung in this arc looked
  at the art before committing to a look; three lanes flag this as an open question. Any
  visual claim here is byte-derived only.
