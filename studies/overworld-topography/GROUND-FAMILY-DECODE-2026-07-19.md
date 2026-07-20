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

> ## ⚠ CORRECTION (2026-07-19, after the round-3 section below was written and committed)
>
> **Round 3's FALSIFIED verdict is RETRACTED — it is not supported by its own evidence.** The
> user looked at the decisive render and observed that the *STOCK* panel also shows hard edges
> and bad connections. That is correct, and it was checked (`render_calibration.py`):
>
> * **The instrument was never calibrated.** Rendering 100% unmodified stock through the same
>   pipeline at the same settings (24×24u, unshaded, sc=32) shows *pure stock desert interior*
>   as a blatant repeating grid of squares — 2.3× edge-enrichment on the 4u lattice. FF9's
>   overworld ground **is** a 4u tile mosaic; at 32× with no shading the lattice is exposed
>   everywhere. Hard tile edges therefore cannot, by themselves, indict a synthesis.
> * **The missing control was STOCK vs STOCK.** Four *unmodified* desert|dunes seam windows
>   rendered side by side span the whole range from smooth-organic (block (18,3)) to distinctly
>   boxy and rectilinear (block (13,12)'s dune blobs). **Stock varies against itself as much as
>   the synth differed from the one stock window it was compared to.** Comparing a single stock
>   window to a single synth window had no resolving power.
> * Three agents (builder + two judges) and the orchestrator all read "stock curves, synth
>   staircases" into a panel where stock does no such thing. The description was motivated, and
>   the judges anchored on it rather than testing whether the view itself was trustworthy.
>
> **Correct status: INCONCLUSIVE, not falsified and not validated.** The render cannot tell.
>
> ### The re-run WITH the controls in the sheet (`dunes_strip_emitter_v2.py`)
>
> The comparison was then re-run properly, with a real NULL: instead of "does synth look like
> this one stock window", ask **"is synth distinguishable from a REAL FF9 row sequence borrowed
> from elsewhere on the map?"** The 195 strip cells sit in two clusters; a TRANSPLANT lays one
> cluster's genuine stock rows over the render window's cells (31 samples at varying offsets).
> Metric, since the eye is now known-unreliable here: mean |Δ mean-luminance| between
> lattice-adjacent strip cells (each row is a painted density tile with its own brightness).
>
> | assignment | jumpiness | |
> |---|---|---|
> | STOCK (this window's real rows) | 5.01 | reference |
> | **TRANSPLANT null** (31 real FF9 sequences) | **3.83 – 5.85** | the band |
> | SYNTH (emitter seed 0) | 5.33 | **inside** |
> | emitter, all 20 seeds | 4.62 – 5.62 | **20/20 inside** |
> | CONTROL iid-random | 4.49 | inside |
> | CONTROL all-row-0 | 0.00 | **the ONLY one outside** |
>
> * **The emitter sits inside stock's own range on every seed** — the original FALSIFIED verdict
>   is not merely unsupported, it is contradicted. Visually, the transplant panels show the same
>   blocky right-angled patchwork the synth panel was faulted for.
> * **Round 3's eye ranked the controls backwards.** It judged `all-row-0` "closest to stock";
>   that is the one assignment measurably out of family, outside the band by being perfectly
>   uniform. The uncalibrated eye picked the only detectably-wrong option as the best match.
> * **THE ROOT CAUSE OF THE WHOLE EPISODE: the 4 strip rows differ in mean brightness by only
>   ~5.9/255 ≈ 2.3%.** They are nearly the same tile. No row assignment can produce much visible
>   difference — which is why wide and medium zoom showed every variant identical, and why the
>   tight zoom became a Rorschach test.
> * **Effect on the dunes carry:** the blocker was "a placement policy must exist before a mint."
>   The calibrated answer is that it must merely be **non-degenerate** — the emitter qualifies,
>   and so does almost anything that is not all-one-row. A materially smaller obstacle than
>   "unsolved".
> * ⚠ Honest limits: this metric scores per-cell brightness jumps, so it does NOT separate the
>   emitter from iid-random — "not worse than stock" is established, "better than random" is not.
>   And the emitter's lag-1 autocorrelation miss (+0.073 vs −0.423) is a real structural
>   difference from stock that this metric does not capture.
>
> What still stands, independent of the render: the **coverage-density gradient discovery**
> (from the atlas crop, not the seam render), the 190-edge/195-cell/9-block census, the
> orientation law, and one *genuine measured* shortfall — the emitter does not reproduce stock's
> negative lag-1 autocorrelation (+0.073 vs −0.423), which is a real defect established by
> numbers rather than by looking. Also unaffected: at wide and medium zoom all variants are
> indistinguishable, so the practical stakes remain low.
>
> **THE LAW THIS MINTS — CALIBRATE THE INSTRUMENT BEFORE YOU JUDGE WITH IT.** Render known-good
> stock through the same pipeline first, and establish how much stock varies *against itself*,
> before declaring a synthesis different from it. This arc has now made the same class of
> mistake in the GUI study (*"an empty tempdir is not a clean room"*, *"a probe that cannot
> reproduce the lifecycle cannot falsify a lifecycle bug"*) and here. **An uncalibrated eye is
> not evidence.**

## Round 3 — the placement emitter: ~~★ FALSIFIED~~ INCONCLUSIVE (see the correction above)

`dunes_strip_emitter.py`. Built a real, deterministic, seeded desert|dunes row emitter grounded
in round 2's measured dither: per-touch-category empirical PMF × the measured |Δrow| transition
prior, assigned by BFS over lattice neighbours (so it generalises to branching 2D seams, not
just linear runs). Rendered it against the real stock seam over identical geometry, with two
controls. **Two of three judges reviewed substantively — both FALSIFIED. (The third returned a
degenerate empty response and was disregarded, not counted as agreement.)**

**The verdict is visual, and it is the right call.** At tight unshaded zoom, stock's boundary is
a smooth rounded coastline — one coherent bite out of the dune field. The emitter's, on the same
geometry, staircases into boxy right-angle notches. Damningly, **it is not visually
distinguishable from the iid-random control**, and the deliberately-wrong `all-row-0` floor looks
*closer* to stock than either. Numerically it also misses stock's negative lag-1 autocorrelation
(+0.073 vs −0.423), and its marginal χ² (mean 8.28) is often *worse* than the naive control's
(1.49). Measurably better ≠ visibly better — **THE FORM LESSON, a second time in this arc.**

**But the round produced a genuine discovery that explains the failure.** An atlas crop showed
for the first time that **the 4 strip rows are not abstract dither buckets — they are a literal
hand-painted 4-step dune COVERAGE-DENSITY gradient** (row0 ≈ 20% dune blobs on desert red →
row3 ≈ 80%+ dense mottling). That is *why* per-cell sampling fails: adjacent cells must have
their densities cohere into a spatially smooth gradient, and a per-cell draw — however well
conditioned on neighbours — sets each cell's density nearly independently, so density jitters
locally even when the long-run statistics look right.

**The named next design** (not attempted, correctly out of scope): sample one *continuous*
scalar coverage field along the seam, interpolate it spatially, then snap each cell to its
nearest row — replacing the per-cell stochastic draw with real spatial continuity. Re-run the
same tight-zoom render against the same specimen and controls before any shipped-code change.

**A finding that lowers the stakes:** at wide (200×160u) and medium shaded zoom, *all four*
variants — including both deliberately-wrong controls — are near-indistinguishable. The strip is
a one-cell trim; the silhouette a player sees is set by the mains geometry underneath. So whether
a full placement policy is even required for a shippable mint is now an open question in its own
right.

**Nothing shipped to `ff9mapkit/` from this round.** The emitter is a documented negative result,
not a recipe. Durable keeps: the row-as-density-gradient discovery, the 190-edge/195-cell/9-block
desert|dunes census (independently cross-checked against `biome_adjacency_census.py`), the
family-relative orientation law (row rises toward dunes in all 4 compass directions), and the
negative result itself.

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

---

## Round 4 (2026-07-19) — the coverage-field verdict · the donor screen · the first dunes MINT · the scrub recreate

Orchestrated as five adversarially-reviewed workflow rounds (Sonnet lanes; every headline
number independently re-run by a REPRODUCE lens, bit-for-bit deterministic throughout).

**1. The named coverage-field emitter design is REFUTED AS A MECHANISM**
(`dunes_strip_emitter_v3.py`). The round-3 correction's named next design (continuous coverage
field → snap/dither quantizer) was built and calibrated (133 configs × 2 quantizers): the
composite objective discarded the diffusion smoothing entirely (**iters=0 wins for BOTH
quantizers**), and the tested iid+non-negative-diffusion family is **structurally incapable of
anti-correlation** — every variant's same-row rate sits at the ~25% iid floor vs stock's 9.8%.
The snap variant's "improved" lag-1 is inherited touch-category alternation diluted by noise,
and its sign flips between 6-seed calibration (+0.0196) and 20-seed validation (−0.0677) —
unstable under resampling. **The mint keeps round 3's BFS emitter** (same-row 9.77% == stock's
9.77%, in-band 20/20). All variants clear the lawful non-degenerate+in-band bar; the choice is
statistical preference, not a gate.

**2. The donor-retile screen** (`donor_retile_screen.py`, closes the roadmap SOON item):
**47 beach-bearing blocks map-wide** (corrects the ~44 earmark) → 40 donor windows → **desert
6/40 qualified** (the proven (7,17) + 5 new: **(8,17)+2×2 auto [best, 3-block self-contained
island]**, (13,10) strips=none [the 1 STRIPS-PARITY window], (16,16), (17,9), (17,16));
**snow 0/40** — honestly split: 35/40 refuse via sand_fam (snow has no `SAND_BANDS` entry),
and **5 topo-33-ONLY frozen-shore windows ((6,3),(7,2),(7,3),(8,2),(8,3)) refuse via the
separate unclassified-content gap** — topo 33 is a distinct unmeasured family (parallel to the
topo-16 dirt gap), NOT the sand_fam mechanism. Canyon tallied-only (wall_coastal refusal).
New snow candidates must come from a non-beach rock/grass coastal population — a separate scan.

**3. The dunes MINT ladder** (`dunes_mint_design.md` → `dunes_patch_mint.py` +
`dunes_blob_shapes.py`): the decode's prize — the first minted dunes ecotone (a mint, not a
carry: THE NO-ENCLOSED-DUNES LAW forbids the verbatim window). Host = `world-island --ground
desert` at (672,−1248) r26 seed 2 (block (10,19)); dunes mains (topo 41, walk-legal) + the
desert|dunes STRIPS ring, rows from the frozen BFS emitter; **uv+tangent.x only, zero vertex
motion**; census MISS=0 regression-equal; the save-brick probes RUN, not argued. The ladder ran
under a calibrated-EYE deploy gate, each rung's defect distinct and structural:
- **v1**: 23/23 mechanical gates green — the EYE refused: ring perforation (6/28 theory ring
  cells dropped as irregular = bare-desert holes) + |Δrow|=2 cliffs across the shell seam.
  ⇒ the aggregate jumpiness scalar cannot see per-boundary cliffs; **a gate sheet without an
  eye is incomplete**.
- **v2**: ring completeness 12/12+16/16 via all-regular window SELECTION (6 candidate windows;
  the classifier untouched) + cross-shell |Δrow|≤1 — the gate refused: the square-core+shells
  plan renders a rectilinear SQUARE FRAME. Quantified post-hoc by the shape census: v2
  convexity 0.9024 vs the real envelope 0.464–0.754; bimodal {1,3} run-lengths vs real decay.
- **THE SHAPE CENSUS** (`dunes_blob_shapes.py`): stock has exactly **TWO dunes components
  map-wide** (273 cells over (18-20,3-4); 130 over (13-14,11-12) — the latter with a real
  ~20-cell enclosed topo-59 hole), **ZERO freckle satellites**, borders essentially all-desert;
  neither fits an 80-regular-cell host whole. Extracted the **31-cell lobe of comp[0]**
  (16/19 outline cells verbatim-real) as the stampable template.
- **v3**: STAMPS the real lobe (8 dihedral transforms × translation over regular cells; winner
  rot270 at origin (166,−317), same block) + a SHAPE-FIDELITY gate (placed outline byte-matches
  the template). **The macro silhouette is FIXED — two independent eyes agree the coastline now
  reads organic** (convexity 0.721, inside the real envelope). The gate refused a third time:
  the INTERIOR reads as a dune/desert checker QUILT at gameplay scale. Root cause is
  arithmetic: 19 of 31 footprint cells are boundary wearing gradient strip tiles over a 12-cell
  core — **61% boundary vs stock's 32–45%; the transition band IS the blob.**
- **v4 (the decisive round)**: measure stock's per-side/coverage/contiguity arrangement, then
  one calibrated sheet of three dressings — measured side-conditional · **transplanted-REAL
  arrangement** (stock comp[0]'s actual boundary sequence laid on our geometry — the control
  that separates "arrangement fixable" from "blob too small for the band") · solid-core with
  outer-halo-only. Outcome recorded below.

**4. The scrub rung-1 recreate is DEPLOYED** (2026-07-19, post-reset). `dunes_patch_carry.py
--deploy` re-ran byte-deterministic vs the pre-reset record (same donor (13,3) window, same
seed 2, all gates green at deploy); the save-brick point probe on the WRITTEN files grounds
walkable (scrub topo 4 at centre, desert 17 around, zero MISS); the standalone `world-mirror`
synced Disc4 (Terrain byte-identical Disc1==Disc4); the install diff shows exactly 18 files,
all Block[8][19], comp20 untouched. ⚠ Two honest framings: this content was **never playtested
pre-reset** — its deploy is a FIRST playtest, not a restore; and the known amputation-stump
cosmetic is reproduced by design (the round-3 TRUE-isolation fix remains an open LATER item).
Teleport (544,−1248); A/B donor at (1158,−388). ⚠ Mechanism note for future carries: the
carry's final `deploy_override` write BYPASSES auto-mirror (only `landmass()`'s own writes
mirror) — the standalone verb is REQUIRED after it, which is exactly how it was run.

**THE v4 VERDICT — the mint arc CLOSES: THE DUNES SIZE-CLASS LAW.** The measurement landed
first (`dunes_boundary_composition.py`): dune-side boundary strip coverage is **61.0%**, NOT
100% (desert-side 53.8%); rows are hard side-conditional (dune-side {1,2,3} mean 1.96, row 0
never; desert-side {0,1,3} mean 1.08, row 2 never); strip runs are CLUMPED (dune-side mean
3.12 including two real 15-cell runs); interiors beyond depth 1 are 99.6% plain mains. All
three dressings built on those numbers (measured side-conditional / a TRANSPLANT of comp[0]'s
real ordered boundary walk / solid-core+outer-halo) fixed v3's interior quilt — the core is
solid, tagging is contiguous — and **all three were REFUTED by the fresh eye + the gate's own
look**: a castellated grid-aligned boundary with detached single-cell fragments, at gameplay
scale, in every variant. **The transplant control is the closure proof: zero-synthesis,
genuine stock arrangement quilts identically at this size** — the defect is footprint SCALE,
not dressing choice. Stock's ecotone vocabulary is painted for its two real components
(273/130 cells, boundary populations 164/171) and the shape census found ZERO smaller
components or freckles map-wide: **small dune blobs do not exist in FF9, and the dressing
mechanism is why — the family has a minimum size class.** A lawful dunes mint needs a
≥~130-cell footprint (a multi-block host stamping a REAL component whole — comp[1] + ring
needs ~185 regular cells) or a sub-cell blend mechanism outside the decoded per-cell
vocabulary. NOT deployed; block (10,19) stays empty. What the arc KEEPS: the shape-stamp
mechanism (v3, proven organic by two eyes twice), the boundary-composition dataset, the
donor screen, and four rounds of falsification record — the FORM LESSON's dunes instance,
caught offline by the calibrated eye with zero playtests spent.

**§4 ADDENDUM — the playtest verdict + disposition (2026-07-20).** The recreate's first
playtest re-confirmed the amputation stumps in-game (screenshot: the fully-carried centre
patch reads well; two hard-edged corner fragments). The OPEN-END TRIM (the round-3 design,
now BUILT: `full8()` unbounded 8-adjacency donor flood-fill + `trim_open_ends()` + the
ZERO-OPEN-ENDS gate + a donor-context render) returned the strongest form of the answer:
**DROP EVERYTHING** — all 8 scrub-bearing window cells (6 comp + 2 that had leaked into the
ring untagged) belong to ONE 232-cell donor shrub system, 224 cells outside the window; even
the good-looking centre patch is a lucky slice, not a terminating patch. THE ENSEMBLE LAW,
now in-game-confirmed. En route: the donor label bug — `cand['block']` was the mega-region's
`blocks[0]`; the true donor block is **(18,6)**, not "(13,3)" (the world teleport (1158,−388)
was always correct). **Disposition (the user's call, made 2026-07-20): REMOVE THE PATCH** —
Block[8][19] is redeployed as the PLAIN desert islet (same mint: (544,−1248) r26 seed 2,
all gates clean, MISS=0, auto-mirrored, Disc1==Disc4 byte-identical). The scrub-patch rung
is **CLOSED BY REMOVAL**: the lawful mixed-biome unit is the full interlocked ensemble
(ground + shrub + slope + rock) on a bigger bench — the ensemble-carry rung, unchanged in
the LATER tier.

**§4 ADDENDUM 2 — a CONFIRMED live-only defect at (755,−1216): the census oracle's first miss
(2026-07-20).** After the flat-mesh fix, the user reported a NEW class of tile near (755,−1216):
pale, flat-textured, and **genuinely unnavigable — boat and airship both blocked**. This is the
first defect all session where the offline census oracle (`placement.place()`-reconstructed from
the deployed bytes) DISAGREED with the live engine: a 40×40u window at 0.1u around the exact point,
straddling the block-frame boundary on both sides, reports **zero misses**, every probe grounding
on Sea4/Sea5 at topo 57/54 — both in `BOAT_TOPO`. The geometry, per the offline reconstruction, is
complete and legal. The live engine blocks it anyway.

**Location, precisely:** (755,−1216) sits exactly on the frame between block (11,18) [donor (8,17),
overridden parts `Terrain, Sea3, Sea4, Sea5`] and block (11,19) [donor (8,18), overridden parts
**`Sea3, Sea4, Sea5` only — NO Terrain override**]. Donor (8,18) carries no land (confirmed in the
original round-4 donor detail: "(8,18) carries no data"), so cell (11,19) is a **water-only carry**:
Sea mesh laid onto a cell whose stock prefab was — like all four target cells — genuinely blank
(zero parts, off the data grid; verified for all of (11,18)/(12,18)/(12,19)/(11,19) alike, so
blankness alone doesn't distinguish it).

**Two concrete hypotheses TESTED and REFUTED:**
1. *Sea1/Sea2 coast-tile free-ride mismatch* (stock coast-only shades bleeding into open water,
   per `water.py`'s own documented "misplaced river tile" look) — checked both the donor (8,18) and
   the pre-carry stock prefab at (11,19) directly via `transplant.world_tris`: **neither carries any
   Sea1/Sea2 geometry at all.** Refuted.
2. *A bad/non-boat topo carried in* — dumped the full topograph histogram of every tri in the
   deployed Block[11][19] Sea3/Sea4/Sea5: **100% topo ∈ {54, 57}**, both boat-legal. Refuted.

**The leading hypothesis (UNCONFIRMED, needs live access to close):** block (11,19) is architecturally
unique among every cell this arc has deployed — it is the FIRST per-block override this session
(possibly ever, in this kit) that carries water parts with **NO Terrain override at all**. Every
other successful carry (this island's own other 3 cells included) always ships at least a Terrain
component, even where it's a thin sliver. This matches the session's own established LOAD-BEARING
RULE correction (registration ≠ raycast — a render-only/bare override can exist geometrically and
still never enter `WMBlock.ActiveWalkMeshes`): the s34 divert / `WMWorld.LoadBlock` registration
path may specifically require a Terrain component to be present for a block to register its OTHER
parts (SeaX) as active walkmeshes at all. A Terrain-less water-only override may simply be an
untested, possibly-unsupported configuration.

**Secondary lead (the user's own hypothesis, worth checking in parallel, not yet confirmed or
refuted):** "a series of uncarried sea tiles that no longer make a coherent Wang puzzle" — the
`water.py` Wang-tile transition language (`DEEPSET2TILE`) assumes neighbour-consistent depth-edge
sampling; a carry that doesn't re-derive that language at the new site (this carry positions the
donor's UVs verbatim, it does not re-run the Wang assignment) could produce texture/tile
discontinuities. The topo dump above shows the COLLISION data is clean, so a pure Wang-UV mismatch
would explain the PALE/flat visual on its own but not obviously the navigability block by itself —
unless the two are separate, co-located symptoms (a texture defect AND a registration defect,
both stemming from the same "no-Terrain water-only cell" carry). Worth checking independently.

**NEXT SESSION, in order:**
1. Live forensics FIRST, not more offline census — sail/fly to (755,−1216) and grab `Memoria.log` /
   `output_log.txt` from that moment (the same technique that found the flat-mesh IndexOutOfRange).
   The offline oracle has now been shown NOT sufficient for this failure class.
2. Test the Terrain-registration hypothesis directly: deploy a degenerate/inert flat Terrain
   override at block (11,19) (zero visual/gameplay change, purely to test registration) and see if
   the water there becomes texturally correct + navigable.
3. If confirmed, this is a NEW GATE for `transplant.py`/`world-transplant`: a target cell whose
   donor carries water but no land must synthesize a minimal Terrain component (or the tool should
   refuse/flag such cells) — a real gap in the shipped machinery, not just this one carry.
4. Check whether any EXISTING stock or previously-carried water-only cell elsewhere already proves
   or disproves the Terrain-required theory (a fast falsification if one is found).

Not fixed this session — recorded for continuity across the account switch. The rest of the (8,17)
carry stays fully closed and in-game proven (cave inert, the (12,18) sea holes patched and
confirmed navigable, no z-fight).

**§4 ADDENDUM 3 — ROOT-CAUSED + FIXED (2026-07-20): the s34 `HasLandOverride` divert gate, not a
Terrain-registration requirement.** The live evidence ADDENDUM 2 asked for turned up in
`GAME/Memoria.log` (boot 02:18) — the smoking gun is line 55 next to its siblings:

```
55  [WorldMeshOverride] loaded '.../r19/Block[11][19] Sea4' ...            <- ONLY Sea4
35-38 [WorldMeshOverride] loaded '.../r18/Block[11][18] Terrain/Sea3/Sea4/Sea5'   <- all 4 (divert donor 8,17)
56-61 [WorldMeshOverride] loaded '.../r19/Block[12][19] Terrain/Beach1/Sea2/Sea3/Sea4/Sea5'  <- all (donor 9,18)
```

Block[11][19] loaded ONLY `Sea4`; its deployed `Sea3.ff9mesh` (956 B) and `Sea5.ff9mesh` (5012 B) sat
unread. Every working sibling ships a `Terrain.ff9mesh` and loaded ALL its parts.

**Confirmed mechanism (s34 source — `memoria-patches/s34-worldmap-mesh-override.patch`,
`Assembly-CSharp/Global/WM/WMWorld/WMWorld.cs`).** A sea cell diverts to a reclaim DONOR prefab only
`if (LandDonorPrefab != null && WorldMeshOverride.HasLandOverride(disc,x,y))`, and `HasLandOverride`
returns true **iff a `Block[x][y] Terrain.ff9mesh` override FILE exists** (patch :286-289). Block[11][19]
has no Terrain override (donor (8,18) is water-only, so the transplant emitted none) ⇒ `HasLandOverride`
= false ⇒ **the divert never fires** ⇒ the cell loads the generic **`SeaBlockPrefab`**, whose single
child transform is `Sea4`. `LoadBlock`→`RegisterBlockComponent` looks up an override **per
prefab-transform NAME** (`TryLoad("...Block[11][19] " + transform.name)`), so only `Block[11][19] Sea4`
binds; `Sea3`/`Sea5` have no matching transform and are silently skipped, and the `Donor.txt="8,18"`
sidecar is **DEAD** (read only inside the un-armed divert — the ADDENDUM-2 leading hypothesis named the
right symptom but the wrong prefab: the effective prefab is SeaBlockPrefab, never donor (8,18)). The
carried donor-(8,18) `Sea4` is a **PARTIAL 474-tri** interior band whose holes the (now-unloaded)
Sea3/Sea5 layers were meant to fill; carried here with only Sea4 binding, those holes are real
ground-query misses = an invisible VEHICLE WALL + a pale/void render (placement rule 2). Both symptoms,
one mechanism.

**THE ORACLE GAP, closed.** The prior census fed all three deployed files into `placement.census`; the
engine binds only the transforms the *effective prefab* exposes. The fix models it: an
`effective_meshlist` gate — no `Terrain.ff9mesh` ⇒ SeaBlockPrefab ⇒ keep only `{Sea4}`, drop
Sea3/Sea5. With that gate the oracle **finally reproduces the live defect offline**: pristine-Sea4-only
= **304/4096** cell misses (hole bbox world x[716,763] z[-1231,-1216], containing the reported point;
432/2706 in the 40×40u window at (755,-1216)); the merged Sea4 = **0**.

**THE FIX (Route 2 / option c — the convergent engine-source + oracle-gap recommendation; the
STOCK-PREFAB dissent was a concurrent-write race artifact: it measured the already-merged 512-tri file
at the exact point, which of course covers it, and read "coverage complete").** Merge the Sea3+Sea5
triangles into the single bindable `Sea4` part (512 tris; per-tri `tangent.x` topograph carried verbatim
⇒ boat-legality byte-preserved; the FLAT-MESH INVARIANT held via `merge_local_mesh`), then DELETE the
now-inert `Sea3`/`Sea5` and the dead `Donor.txt` so the on-disk state equals what the engine loads (a
Terrain-less water cell = exactly ONE file, the complete Sea4). Mirrored to Disc4 by **explicit
byte-copy** — NOT `discmirror.auto_mirror`, whose FREE-RIDE PIN (`discmirror.py:241-265`) would read the
inert `Donor.txt`, subtract the overridden `{Sea4}` from donor (8,18)'s `{sea3,sea4,sea5}`, and
**resurrect `Block[11][19] Sea3/Sea5` on Disc4** with donor bytes — re-creating the orphans and a
Disc1/Disc4 asymmetry (a real gotcha for any water-only cleanup near an inert sidecar).

Gates all green (`studies/overworld-topography/waterfix_1119.py`, idempotent, reads pristine from
`backups/waterfix-1119.20260720/`): (a) byte-diff — the merge only APPENDS Sea3+Sea5, the 474-tri Sea4
base is verbatim; (b) FLAT-MESH `vcount==idx` (1536), topos {57:489, 54:23} ⊆ {54,57}; (c) free-ride
audit — SeaBlockPrefab exposes only {Sea4}, nothing foreign rides in; (d) the money gate above; (e)
two-tree — Disc1 Sea4 == Disc4 Sea4 byte-identical (79892 B, md5 d0f1eabd…), (11,19) now one file per
disc. Neighbours (11,18)/(12,18)/(12,19) untouched. Deployed to both discs; awaiting the sail/fly
playtest at (755,-1216).

**Productization (deferred to post-playtest, per the one-change rule) — a real shipped gap.** The
`transplant`/`GroundRetile` path silently emits a water-only cell with >1 sea layer + no Terrain, which
the effective prefab can never bind. The gate belongs in `transplant.transplant_region` /
`GroundRetile.for_donor`: compute the effective prefab exactly as the engine will, and for any
data-bearing cell REFUSE (or auto-collapse to Sea4) any part the effective prefab cannot bind. The
cleaner long-term fix is engine-side (make override files authoritative regardless of the effective
prefab's transform set — a DANGEROUS DLL round, out of scope here).
