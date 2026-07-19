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

## Round 2 outcomes (same day — 5 lanes × 3 lenses, 20/21 agents)

Round 2 ran exactly the deferred list below. **No shipped-code contradiction was found** —
round 2 cross-checked shared objects between lanes *before* publishing, which is precisely
what round 1 failed to do. Status of each deferred item is marked inline below. Scripts:
`topo16_ecotone_crosscheck.py` · `secondary_mains_rect_decode.py` ·
`wall_coastal_crossblock.py` · `strip_placement_policy.py` · `offline_eye_disputed_assets.py`.

**The one thing still open is the strip PLACEMENT policy — the arc's actual remaining
blocker.** Depth-alone determinism is falsified (0.5–3.1% purity, both schemes, both pairs).
The real structure is a locally-alternating small-step dither (|Δrow|=1 dominant, negative
lag-1 autocorrelation) riding a soft family-relative bias — but the emission recipe built
from those statistics is explicitly speculative: never implemented, never rendered, never
in-game tested.

**The offline eye narrowed the risk usefully**, and this is the round's most actionable
finding: the **grass|desert** strip reads as an ordinary hard jigsaw boundary with *no
visible blend ribbon* — row placement there is very likely cosmetically free. The
**desert|dunes** strip shows a genuine soft halo transition — placement actually matters
there. So the remaining work is not "solve placement for both pairs"; it is desert|dunes
only, and it terminates in a playtest.

## Deferred — and why (do not ship these without another round)

- **brush `wall_coastal`** — the lane recommended `True`; **rejected on review.** Its only
  coastal evidence is a single open-sea face, with the other 5 matching faces interior/gorge.
  Scrub was refused on a lone face that was *100% open-sea with zero gorge counterexamples* —
  strictly cleaner evidence. Certifying brush while refusing scrub applies an inconsistent,
  backwards bar. Left **unset**, which now fail-closes. To clear it: a second independent
  open-sea face (the adjacency test is **within-block only** — a cross-block-aware rerun is
  the obvious next probe) or a visual confirmation of the ~(8,15) candidate.
  → **★ ROUND 2: SETTLED `False`.** The cross-block-aware scan was built and run map-wide
  (`wall_coastal_crossblock.py`): it adds **zero** new evidence for brush, scrub *or* dunes,
  while proving itself non-null on the desert control (+9/1838 tris). So the blind spot was
  real but empirically empty here. brush and scrub **tie at exactly one open-sea face each**,
  and under the bar that disqualified canyon both fail. brush is now explicitly `False`; no
  family carries an unset key any more. Round 1's conservative call was vindicated.
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
  → **★ ROUND 2: CLOSED, and it is a real structural finding.** Independently re-derived from
  topo-16's *own* bytes (not re-quoted): **100.0% zero-residual** decomposition into
  `GROUNDS["desert"]` mains (36.5% of tris) + `STRIPS[("grass","desert")]` (50.2%) +
  `STRIPS[("desert","dunes")]` (13.3%), all byte-identical at 5dp to the shipped constants.
  **topo-16 owns zero bespoke atlas territory — it is a SEAM-DRESSED ground**, and its strip
  choice tracks its real neighbour geographically: all 56 desert|dunes-strip tris are confined
  to exactly the 4 of its 6 blocks that actually contain dunes. Do NOT add it to `GROUNDS` or
  `STRIPS`. (The 57%→50.2% shift is cell-index share vs tri-count share, not a disagreement.)
- **The "secondary mains rect"** — the control lane's own harness printed
  `>=1 required control FAILED` (grass wall ≠ (0,0)) while its headline claimed all controls
  passed; desert and brush print nonzero cross-specimen spread. Behind that is a real
  unexplained phenomenon: a minority of desert/canyon/brush specimen blocks lock onto a
  *second* translated region (desert's reads exactly du=0.85058/dv=-0.11425 on 3/8 blocks).
  Given the topo-16 precedent, this may well be another already-catalogued region. Undecoded.
  → **★ ROUND 2: DECODED — it is genuinely NEW.** A previously uncatalogued second desert
  ground rect at `du=0.85058, dv=-0.11425`, proven-5dp on a 5-block cluster, matching none of
  the 21 catalogued regions. It is **not** the generic edge decal, despite near-identical
  u-origins (0.85058 vs 0.85059) — a >0.2 v-gap separates them, and that coincidence cost a
  round to rule out. Shipped as data-only `grassland.DESERT_MAINS_SECONDARY`. ⚠ The lane's
  "geographically isolated" claim was **struck** — two reviewers independently showed block
  (13,4) fits the PRIMARY exactly while directly bordering the secondary cluster at (12,4),
  so the two rects interleave and there is no territory to key authoring on.
  **The lesson worth keeping: this surfaced as an apparent control FAILURE. Read a control
  failure before you explain it away.**
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
  visual claim here is byte-derived only. → **★ ROUND 2 ran it** (`offline_eye_disputed_assets.py`,
  first visual pass in this arc's ground-family work) and it immediately paid: it is what
  established that grass|desert needs no careful placement while desert|dunes does. ⚠ One
  material correction from review: the decal's "mainstream, ~47%" framing conflated
  *block-incidence* (57/120 blocks touch it) with *area share* (~13% of desert's tri area) —
  roughly 4× smaller than the wording implied. Incidence is not extent.
