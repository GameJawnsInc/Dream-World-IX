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

**§4 ADDENDUM 4 — ROUND 2 (2026-07-20): the merge fixed navigability but STREAKED the render; the
faithful fix is RESTORE PER-LAYER + ARM THE DIVERT, and it mints THE WANG-CARRY LAW.**

**Playtest verdict (user, with screenshot).** ADDENDUM 3's merge WORKED for navigability — *"able to
sail now and no more empty tiles"* — but introduced a VISUAL defect: at the light-blue/dark-blue ocean
boundary near the boat (world 755,−1216) a patch of **streaky, wrong-scale transition tiles** — *"the
old stretched/random transition tiles we had when first discovering wang tiles."*

**THE USER'S LAW, verbatim:** *"when we try to arbitrarily drop 2 water tiles next to each other, we need
to make sure any Wang patterns that extended outside the block we pulled from are either carried over or
recalculated."*

Minted as **THE WANG-CARRY LAW:** *water tiles are a cross-block Wang puzzle; a carry must carry over or
recalculate any pattern that extended outside the pulled window.* (The seam-coherence predicate that
makes a Wang region coherent — from `water.py`'s marching band: neighbours agree by construction because
both cells sampling a shared world-edge midpoint compute `deep(E) = depth(mid(E)) > threshold`
identically, so `deep_C(E) == deep_C′(E)` across cell AND block seams; a Sea3 never abuts a Sea4 without a
Sea5 bridge. A carry that crops a Wang region breaks this only at the cut edges.)

**Mechanism of the streaks — engine-source verified this round (`WMBlockPrefab.cs`, `WMWorld.cs`
LoadBlock, `WMBlock.cs`, `WMRenderTextureBank.cs`; offline `water_tile_eye_r2.py`).** A sea sub-mesh's
MATERIAL is bound **per GameObject/transform NAME**, and each `SeaN` name maps to a DIFFERENT caustic
texture: `Sea3`→`10_128_64` (light/shallow), `Sea4`→`10_128_128` (deep), `Sea5`→`11_64_0` (the
directional transition gradient, a 128×512 = four stacked quarter-v tongues). (`Sea1..Sea6` are commented
OUT of `WMBlock.ObjectNameToPaths`, so the material is NOT set by `SetupPreloadedMaterials`; it travels
with the INSTANTIATED donor transform and is scrolled by `WMRenderTextureBank` — the round-1 report's
"SetupPreloadedMaterials by name" premise was wrong on that detail, right on the conclusion.) Round-1's
merge put all 512 tris in ONE GameObject named `Sea4`, so the 32 former-`Sea5` tris (UVs = full-u ×
QUARTER-v strips, measured ~3.9:1 aspect) and 6 former-`Sea3` tris are sampled through the `Sea4` 256×256
atlas instead of their own → a 2-tile-wide, ¼-tall slab smeared across a 4u quad = the reported streaks.
The offline eye proves it: the merged Sea4 rendered all-through-Sea4 reproduces the exact streaky north
band; each pristine part through its own texture is coherent AND **pixel-identical (mean diff 0.000) to
the stock donor (8,18)**. So ADDENDUM 3's own productization prescription — *"auto-collapse to Sea4"* —
is exactly what streaks the render; **collapse-to-one-part is a navigability fix that DESTROYS the
per-part material namespace.**

**THE FIX — RESTORE PER-LAYER + ARM THE DIVERT** (the convergent recommendation of the site-vs-donor
audit AND the engine divert trace; the WANG-language report's pure-UV-reassign is inferior — it would
flatten the real shallow band to uniform deep and discard the faithful per-part structure). Three loose
files per disc, plus two:
1. **RESTORE** the pristine per-layer `Sea3`(6)/`Sea4`(474)/`Sea5`(32) `.ff9mesh` — byte-verbatim from
   donor (8,18) (`backups/waterfix-1119.20260720/`) — overwriting the merged 512-tri `Sea4`.
2. **RE-ADD** `Donor.txt` = `"8,18"`.
3. **ADD** `Terrain.ff9mesh` as a **SAFE DEGENERATE STUB** — one zero-area triangle (3 identical verts),
   `tangent.x = 4078` (`placement.IDALL_SKIP` → skipped before intersection), `flags=7`, `verts==idx==3`
   — whose ONLY job is to make `HasLandOverride` (a bare `File.Exists`) true and **arm the s34 divert.**

Now the divert loads the (8,18) donor prefab, whose part set is **EXACTLY {Sea3, Sea4, Sea5}** (measured,
both discs) — LoadBlock registers each as a Form-1 walkmesh (`if (prefab.SeaN) RegisterBlockComponent(…,
true, false)`), each `TryLoad`ing our per-layer override **with its own material** → Sea3 light / Sea4
deep / Sea5 gradient, exactly like the in-game-proven sibling cells (11,18)/(12,18)/(12,19). The streaks
are gone; the walkmesh UNION is the identical 512 tris round 1 proved MISS=0. Crucially, donor (8,18) has
**no `TerrainForm1`**, so LoadBlock's `if (prefab.TerrainForm1)` branch is false → **the stub Terrain is
NEVER bound as geometry** (never rendered, never walkmeshed); it is read only by `HasLandOverride`'s
`File.Exists`. That is why the stub is chosen over a flat submerged plane: it is provably harmless whether
or not it ever binds, so a future Donor.txt repoint to a block WITH a Terrain can't turn it into a phantom
sea-level floor.

**Wang-carry finding: (11,19) needs ZERO recalculation.** The audit proved — and the deployed-byte gate
re-proves — that every edge touching (11,19) is coherent by pure verbatim carry: the frame **W/S** edges
face all-deep generic ocean (donor (8,18).W/.S = 16/16 Sea4), and the internal **N→(11,18) / E→(12,19)**
edges reproduce stock adjacency. The island's genuinely cropped-Wang seams (the real instance of THE
WANG-CARRY LAW) live on the **top-row** cells — (11,18).N/.W, (12,18).E, (12,19).E — where the 2×2 window
cut the shallow coast against deep ocean with no transition ring; those are **pre-existing since the
(8,17) carry, away from the boat, and OUT OF SCOPE** for this one-cell redeploy (a marching-band re-run
against a deep exterior cascades, so it can't be a single-cell edit).

**Gates all green** (`waterfix_1119_r2.py`, idempotent; pristine from the round-1 backup, merged-Sea4
fallback preserved in `backups/waterfix-1119-r2.20260720/`): (3a) NON-REGRESSION via the DIVERT
effective-prefab oracle (all three sea overrides bind) — PRE (Sea4-only, un-armed) = 304/4096 misses,
POST (divert, 3 layers) = **0/4096** cell + 0 window, topos {57:3926, 54:170} ⊆ {54,57} boat-legal; the
stub-only census = 4096/4096 MISS (zero hittable area); (3b) FLAT-MESH `verts==idx` on all four written
meshes + ReadMesh range; (3c) free-ride — donor exposes exactly {Sea3,Sea4,Sea5}, all ours, Terrain not
exposed; (3d) **WANG EDGE-COHERENCE** — all four (11,19) edges CLEAN, 0 incoherent; (3e) byte-diff — the
restored parts are byte-identical to the pristine carry (0 quads recalculated); (3f) Disc1==Disc4 for all
5 files, neighbours (11,18)/(12,18)/(12,19) byte-untouched (41 files hashed pre==post); (3g) the offline
eye. En route it caught its OWN gate defect and fixed it: `pathlib.glob("Block[11][19] *")` reads `[11]`
as a **glob CHARACTER CLASS** → matches nothing → the neighbour-untouched and leftover-file checks ran
VACUOUSLY (0 files); replaced with a literal-prefix `iterdir` filter (`_cell_files`) and re-verified
genuinely (41 files). **A GLOB WITH `[` IN THE LITERAL IS A VACUOUS GATE.**

**Productization (paper only, per the one-change rule) — supersedes ADDENDUM 3's "collapse to Sea4".**
Any sea carry/transplant that relocates `Sea` sub-meshes must satisfy TWO gates, both computed exactly as
the engine will:
- **The effective-prefab gate.** A Terrain-less target binds ONLY the transforms its effective prefab
  exposes (SeaBlockPrefab = {Sea4}; a divert donor = the donor prefab's set). For a data-bearing water
  cell with >1 sea layer, DO NOT collapse to Sea4 (that streaks) — instead **arm the divert**: emit a
  degenerate `Terrain.ff9mesh` stub + a live `Donor.txt` naming a donor prefab whose transform set ⊇ the
  layers you ship, so each layer binds its own material. Belongs in `transplant.transplant_region` /
  `GroundRetile.for_donor` (with the disc-4 mirror pinning the stub + sidecar verbatim, NOT free-riding
  the donor's own Sea parts back in).
- **The Wang-carry gate.** Re-run `water.build_arrangement` over the destination's NEW world-space
  neighbourhood; any transition tile whose implied deep-set no longer matches its new neighbour must be
  recalculated (or the window chosen so the cut falls on all-deep edges, as (11,19)'s did). This is THE
  WANG-CARRY LAW mechanized: carry-over when the window preserves the pattern, recalculate when it crops.

**§4 ADDENDUM 5 — ROUND 2 REVIEW (2026-07-20b): the panel finding re-derived, gates re-run green,
disposition = OUT-OF-SCOPE (no byte change).** The round-2 fix (ADDENDUM 4, commit `fe3f28d`) shipped;
the adversarial panel returned ONE *major* finding — *"the user's Wang-carry law is unsatisfied for the
island rim: 17 cropped-Wang seams remain on the neighbour cells."* Re-verified this round against the
**deployed** bytes, not the report:
- **The deliverable (11,19) is correct.** All 7 study gates PASS on the on-disk files (both discs
  byte-identical to the pristine per-layer donor carry, md5 `fb96b321`/`c8244b04`/`8fb7afa2`; the divert
  effective-prefab oracle censuses MISS **0/4096** cell + **0/2706** window, topos `{57:3926, 54:170}` ⊆
  boat-legal `{54,57}`; the stub Terrain is engine-verified never-bound — donor (8,18) has no
  `TerrainForm1`, WMWorld.cs:558). The engine divert path was re-read end-to-end: WMWorld.cs:503-507
  (`HasLandOverride` File.Exists arm) → `ResolveReclaimDonor` (Donor.txt="8,18") → :581-593 each
  `if (prefab.SeaN) RegisterBlockComponent` binds our override by `transform.name` with its **own**
  material. The user's reported streak (the (11,19) NE sea5 band rendering through the Sea4 atlas) IS
  fixed by this restore.
- **The finding is factually accurate but OUT OF SCOPE.** An independent probe (`neighbor_seam_probe.py`,
  reusing the study's own `frame_edge_verdicts` predicate on the deployed bytes) reproduces the count
  EXACTLY: **17** incoherent outer-frame edge cells — 11 on (11,18).N/.W, 5 on (12,18).E, 1 on
  (12,19).E — and **0** on (11,19)'s own W+S frame. Every one of the 17 is on a cell the deliverable
  is FORBIDDEN to touch (*"Block[11][19] only, both discs; nothing else changes on disk in the mod
  tree"*). They are **pre-existing** since the (8,17)→(11,18) carry (neighbour mtimes 09:25/13:53 predate
  the 16:18 (11,19) deploy; round-2 gate 3f verified them hash-identical before==after), a *different
  defect class* than the streak (a hard shallow|deep boundary, no transition ring — not stretched tiles),
  and unreported by the user. Refuted, therefore, on scope not merit: fixing them means re-tiling three
  other cells' outer edges = the island-wide **Wang-carry gate** productization the task defers (above),
  not this one-cell redeploy. **No bytes changed; the final deliverable state is `fe3f28d`.**

**§4 ADDENDUM 6 — ROUND-2 PLAYTEST: CONFIRMED (2026-07-20c). THE (11,19) ARC IS CLOSED.** The user
sailed the boundary: *"it looks good."* Navigability held (the non-regression gate's promise) and the
streaks are gone — the per-layer restore + divert-arm is **★ IN-GAME PROVEN**, closing the
(755,−1216)/(11,19) defect over 3 in-game rounds (hole → merge → per-layer+arm). Laws promoted to the
coast memory (`project-ff9-overworld-coast-mosaic`): **THE DIVERT-ARM LAW**, **THE EFFECTIVE-PREFAB
ORACLE LAW**, **THE PER-NAME MATERIAL LAW**, **THE WANG-CARRY LAW** (user-authored). Successor work,
now the active round: the **17 cropped-Wang rim seams** on the island's other three cells
(`neighbor_seam_probe.py`; requires re-tiling (11,18)/(12,18)/(12,19)'s outer sea edges per the
marching-band language) + **productizing the two kit gates** in `transplant.py` (effective-prefab +
Wang-carry), with the auto-arm emit (stub + Donor.txt) as the proven water-only-cell pattern.

**§4 ADDENDUM 7 — THE 17 CROPPED-WANG RIM SEAMS RE-TILED + BOTH KIT GATES PRODUCTIZED (2026-07-20d).**
The successor round above, built and DEPLOYED (both discs); awaits the sail-around playtest.

**Target 1 — the rim re-tile (`wang_rim_retile.py`, idempotent, deployed both discs).** The 17 seams
reproduce EXACTLY (`neighbor_seam_probe.py`): 11 on (11,18).N/.W, 5 on (12,18).E, 1 on (12,19).E;
(11,19)'s own frame clean (0), byte-identical, untouched. The fix is a SURGICAL per-quad re-tile: for
each flagged rim quad, a LAND-AWARE marching-band re-derivation of the tile's deep-set (a frame edge
faces the generic deep ring; an interior edge is deep iff its neighbour is sea4-WITH-WATER — a
sea4-shaded cell with NO water triangle is LAND/coast, not deep) gives 17 assignments: **12 sea3→sea5**
(a shallow rim cell → an outward-pointing transition tip), **4 sea5→sea5** (a mis-oriented tile
re-derived), **1 sea5→sea4** ((2,0), deep-surrounded, the lone shallow poke absorbed). The derivation
reproduces the design's plan bit-for-bit (cross-check gate). Each moved quad keeps its EXACT verts (Y=0)
+ normals + `tangent.x` TOPO — only the UV rect and the containing Sea file change (THE PER-NAME MATERIAL
LAW). So the {Sea3,Sea4,Sea5} triangle union is a pure REPARTITION (geometry+topo IDENTICAL) → the
walkmesh raycast/coverage/boat-legality is byte-for-byte preserved (non-regression airtight by
construction). **VERBATIM-FIRST (THE FORM LESSON):** the new sea5 UVs are HARVESTED byte-exact from the
donor island's OWN real sea5 termination tiles (donors (8,17)/(9,17)/(8,18)/(9,18) via
`water.read_sea5_tiles` + `_fit_tile` — every needed deep-set variant present, intra-variant UV spread
**0.0**; the donor's real contiguous v-bands 0.244/0.496/0.748 differ from the synthesized
`water.VSTRIP`, so a harvest — not `VSTRIP` synthesis — is the faithful source); the one sea4 tile copies
a deep neighbour's own mains UV. Gates (all green): (a) NON-REGRESSION — the (verts+topo) triangle
multiset is IDENTICAL before==after per cell, sea-union MISS unchanged, moved-quad topos ⊆ boat-legal
{54,55,57} (the whole topo distribution — incl. pre-existing carried-donor topo-56 deep tiles — is
unchanged); (b) FLAT-MESH + SEA-LAYER (union vertex-Y set unchanged, ~0.07u donor micro-relief carried
verbatim); (c) SEAM CENSUS (land-aware) — frame-vs-generic-deep **17 → 0** on all four cells, island-wide
water-aware directed edges **96 → 79 (removed 17, INTRODUCED 0)**, (11,19) clean before AND after,
interior water|water residual **79 pre-existing, delta 0** (the real donor beach-island's own near-shore
lagoon water — sea3 abutting sea4 in complex coast geometry — on interior cells the deliverable is
FORBIDDEN to touch; NOT the fix's fault and NOT a Wang-cropped rim seam); (d) BYTE-DIFF SCOPED — only the
12 declared files changed ((11,18) Sea3/Sea4/Sea5, (12,18) Sea3/Sea5, (12,19) Sea5, both discs);
Terrain/Object/Beach1/Sea1/Sea2/Donor + (11,19) + all other cells byte-identical; (e) DISC PARITY
Disc1==Disc4; POST render `wang_rim_post.png` — 0 red at the real-neighbour level (was 17). **TRANSPARENCY
(never explained away):** the STRICT 4-corner `frame_edge_verdicts` reports ONE residual = the (0,9)
**1-TRIANGLE shore sliver**, which carries the verbatim W-tip gradient UVs (proven byte-exact) but a
4-corner-only fit can't classify a 3-corner tile — a predicate limitation, NOT a seam; the land-aware
lenient census (the calibrated instrument, per the site-prep) = 0. Idempotent: re-deploy is
BYTE-IDENTICAL (0 files changed). Backups → `backups/wang-rim-retile.20260720/`.

**Target 2 — the two kit gates SHIPPED in `transplant.py` (+ `mesh.stub_terrain_mesh`, 10 new tests,
195 world tests green).** (a) **THE EFFECTIVE-PREFAB GATE + AUTO-ARM** (`effective_prefab_arm`, wired into
`transplant()` + `transplant_region()`, ENFORCED): the engine binds a cell's overrides only for the
transforms its EFFECTIVE prefab exposes — armed (a Terrain override present → the s34 divert loads the
`Donor.txt` prefab) binds the sidecar's set; unarmed loads `SeaBlockPrefab`={Sea4} and SILENTLY DROPS
every other sea layer (the (11,19) black-screen class). A water-only carry (donor + sidecar both
Terrain-less) that emits >1 sea layer now AUTO-ARMS with a degenerate `mesh.stub_terrain_mesh`
(tangent.x=4078 skip-sentinel, never bound as geometry — BYTE-IDENTICAL to the proven (11,19) study
stub) so each layer binds its own material. Byte-identity-safe: a cell that already ships a Terrain
override → arm None, unchanged. (b) **THE WANG-CARRY GATE** (`wang_carry_gate`, land-aware frame census
productizing the study predicate, REPORT-ONLY by default): surfaces a carried region's OUTER-FRAME sea3 /
mis-oriented-sea5 tiles facing the open-ocean deep ring. Enforcement is OPT-IN (`enforce_wang_carry`)
because the raw frame census cannot yet separate a carry-INTRODUCED seam from a PRE-EXISTING donor coast
tile without the DONOR-BASELINE subtraction (the proven (7,17) carry shows 16 frame-incoherent edges —
all its verbatim beach-island shelf, NONE carry-introduced; "the donor-site baseline is 4, not 0"); the
rim-retile round IS the end-to-end baseline-aware application. So a cropping carry is VISIBLE
(report-only) without false-positiving proven carries; full hard-enforcement lands once the donor
baseline does.

**Target 3 — the Disc4-only `Block[12][18] Object.ff9mesh` (4076B) = BY DESIGN, load-bearing, no fix.**
The TWO-TREE mirror FREE-RIDE PIN of donor (9,17)'s Object (which free-rides un-overridden on Disc1): its
geometry == the stock disc1 donor Object but != the disc4 donor Object (the stock Object differs across
disc trees), so `discmirror` pins the disc1-source bytes as a Disc4 override to force cross-disc parity of
the free-riding scenery. Verified preserved byte-identical (4076B/64e2abdc) — the re-tile touched only
Sea3/4/5, never the Object.

**§4 ADDENDUM 8 — THE WANG-CARRY DEFAULT REVIEW: the finding CONFIRMED, its remedy REFUTED-with-evidence,
the gate made VISIBLE (2026-07-20e).** A review flagged (major): "the wang-carry gate is report-only by
DEFAULT — the money protection only exists behind `--enforce-wang-carry`; a normal `world-transplant` run
reports `-> ok` on the original broken (8,17) carry." The FACT is confirmed (the default does not refuse).
Its recommended REMEDY — "productize the donor-baseline subtraction so it can safely hard-fail by default"
(ADDENDUM 7's Target-2 rationale, and the gate/CHANGELOG's own words) — is **refuted by a decisive
census.**

- **THE DECISIVE CENSUS (`wang_seam_census.py`, whole stock map):** across EVERY block border in shipping
  FF9, a sea3 (shallow) tile's cross-border neighbour is **NEVER** sea4 (deep) — **0** map-wide. Every
  shallow→deep transition is sea5-mediated (194) or stays shallow→shallow (~1300+). So the gate's predicate
  ("sea3 abuts deep ring = incoherent") encodes a REAL shipping invariant — it does NOT over-flag
  legitimate coast.
- **∴ THE FINDING'S PREMISE IS FALSE.** ADDENDUM 7 (and the finding) asserted the proven (7,17) carry's 16
  frame edges are "all verbatim donor shelf, NONE carry-introduced" — a legitimate pre-existing coast the
  baseline would exempt. But real FF9 has ZERO sea3-abuts-deep: (7,17)'s shelf never faces bare deep in the
  real map (its sea5 transition rings live on the NEIGHBOUR blocks (6,17)/(7,16)/…). Carrying (7,17)
  standalone CROPS those neighbours → its 16 frame edges are all crop-introduced seams, not pre-existing
  coast. (7,17) was proven for walk/render, its shallow RIM never scrutinized at this level.
- **∴ A DONOR-BASELINE SUBTRACTION CANNOT ENABLE A SAFE HARD-FAIL DEFAULT.** With zero pre-existing
  sea3-abuts-deep edges anywhere, there is nothing to subtract — every flagged sea3 frame edge is
  crop-introduced. The subtraction collapses to the raw count and would refuse EVERY coastal-island carry
  (empirically the donor-outward-deep baseline calls **15/16** of the proven (7,17) carry "introduced").
  Flipping the default to hard-fail would therefore refuse the whole coastal-carry workflow — a regression;
  and the shallow-rim look at the exact carry is the human's visual call (Hard-Constraint S2: carry →
  review → re-tile-or-accept). The prior round's report-only default is CORRECT, not a gap.
- **THE FIX SHIPPED (this round, code+docs+tests, no mod-tree change):** the gate now sets a `warn` flag by
  default and `world-transplant` prints a loud **`!! WARNING wang-carry: N cropped-Wang frame seam(s) …`**
  line (was a bare `-> ok`) pointing to the re-tile / `--enforce-wang-carry` / `--allow-wang-seams` — the
  protection is VISIBLE and actionable without refusing. The unsound "false-positives (7,17)" /
  "baseline-subtraction next round" rationale is corrected in the gate docstring, CHANGELOG, and skill. Two
  game-gated tests lock it in: the shipping invariant (0 sea3-abuts-deep in the (7,17) neighbourhood) and
  the real (7,17) carry (warns→ok by default, refuses under enforce, waived under allow). 362 world tests
  green; the deployed island still censuses 0 (no false-warn), enforced-OK, effective-prefab idempotent.

**§4 ADDENDUM 9 — RIM-RETILE PLAYTEST: CONFIRMED; the user names the SIBLING CLASS (2026-07-20e).**
The user sailed the re-tiled shore: *"good"* — the 17-seam rim re-tile is **★ IN-GAME PROVEN** (the
Sea3/Sea5→Sea4 shore termination reads clean). The screenshot's remaining hiccup, in the user's own
analysis (verbatim intent): *there are 3 levels of deepness and 2 transition tile types; the round handled
the 2nd-deepest→deepest transition (Sea3/4/5); where the 3rd-deepest [the shallowest coastal water,
sea1/sea2] meets the deepest in the implant, a HARD EDGE forms — expected, since no transition tiles exist
between these two types. **Don't force it: assess the options, or accept for now.*** This is the crop's
sibling class the retile deliberately did not touch (sea1/sea2/beach1 rode verbatim). Assessment round
launched (no build): the deployed-site adjacency census (crop-created vs donor-verbatim, incl. whether
stock EVER shows sea1/sea2-abuts-sea4) + the lawful-options study (accept / {sea1,sea5} mediation ring /
full ring-ladder termination / shelf extension) — disposition is the user's call on its results.

**§4 ADDENDUM 10 — THE {sea1,sea5} LADDER AT THE SAND-SPIT CORNER: OPTION B BUILT + DEPLOYED
(2026-07-20f).** The user chose **option B** (the {sea1,sea5} mediation ladder) from the assessment
round's options. Built as `studies/overworld-topography/sea1_ladder_corner.py` (idempotent, both discs;
backups `backups/sea1-ladder.20260720/`), a **~4-quad PURE REPARTITION inside cell (12,18) ONLY**.

**The quad plan (verified against the deployed bytes — NO delta from the options sketch):** convert the
two crop-created hard tiles `(15,14)`/`(15,15)` **Sea1 → Sea5** (an E-pointing tip, deepset {E} → deep
to the E), and the two inboard `(14,14)`/`(14,15)` **Sea2 → Sea1** (so the row reads sea2 → sea1 → sea5
→ deep, every adjacency lawful: {sea2,sea1} 499, {sea1,sea5} 79, {sea5,deep} the transition's job — and
NOT the off-language {sea2,sea5}=1). The S-neighbour (12,19) j0 is i14=sea2 / i15=sea5, so both cross-block
edges are lawful with NO 3rd inboard quad. Both E-tip UVs are **harvested byte-exact from the donor
island's OWN real Sea5 and Sea1 strip0/r0 tiles** (donors (8,17)/(9,17)/(8,18)/(9,18); the Sea5 tip is the
SAME UV the rim-retile's (15,9..13) E-tips already use, so the i15 column now reads as one continuous Sea5
E-wall (j8..15); the Sea1 tip is the donor's own (11,10) sea1) — verbatim-first, not `water.VSTRIP`.

**The GEOMETRY delta from the sketch (declared, not a plan change).** The options study assumed clean
flat sea quads; the bytes show the four SE-corner cells are **irregular shore geometry** — 2-3 tris each,
**mixed topos within a cell** (53/54/55), vertices **spilling past the cell** (local z 4.66/5.887, one
tile spans the j14/j15 boundary), and **non-zero beach Y** (0.20–0.39u, the shore relief — NOT flat
Y=0). This is still a pure repartition: every vertex position + `tangent.x` topo is carried **byte-exact**;
only UVs + Sea-file membership move (the walkmesh raycast/coverage/boat-legality is byte-preserved by
construction). Two re-UV methods are used, by DST part: **Sea5 = corner-snap** (rounds each vertex to its
nearest cell corner → a clean strip0/r0 rect that `water._fit_tile` classifies as deepset {E}, REQUIRED
so the new tiles pass the Wang frame gate; both Sea5 target cells have all 4 distinct corners = no
degenerate tri), **Sea1 = bilinear-from-local** (position-accurate, so the boundary-spanning shore sliver
`(14,15)` tri0 — whose two x=0 verts would collapse under corner-snap — keeps distinct UVs). The Sea1
tiles are never Wang-classified by any gate, so bilinear is free there.

**Gates (all green; `sea1_ladder_corner.py --deploy`):** (a) LAWFUL-ADJACENCY — all 16 changed-quad
edges lawful ladder pairs; sea1→sea4 direct island edges **2 → 0**; sea2 introduces **0** forbidden
(sea3/sea5/sea4/deep) edges; the s12 shallow census (12,18)+E+S neighbourhood **2 → 0, INTRODUCED 0**
(incl. N/S of the changed quads); independently re-confirmed by `s12_deep_census_opus.py` on the DEPLOYED
bytes (HARD EDGES 2 → 0). En route the gate caught + resolved a real discrepancy (never explained away):
a bare water-only shade grid mislabels shore LAND cells as deep sea4 → a spurious `sea2(9,10)|sea3` flag;
the fix is to include **terrain** (priority `land`) exactly as s12 does, so `(9,9)` (terrain+sea3) reads as
the coast it is. (b) SEA3/4/5 UNHARMED — `transplant.wang_carry_gate(enforce)` frame incoherent **0**,
`wang_rim_retile.census` FRAME **0** (the rim-retile arc's 17→0 stays 0; the new Sea5 E-tips are coherent
frame edges). (c) PURE REPARTITION — the (verts+`tangent.x`) triangle multiset over all 6 water parts is
**IDENTICAL** before==after (687 tris); FLAT-MESH `vcount==idx` per written file; union vertex-Y unchanged
(max|Y|=0.391u shore relief, carried verbatim — honestly NOT Y=0, and NOT flattened). (d) BYTE-DIFF SCOPED
— only (12,18) Sea1/Sea2/Sea5 change (sizes +156/−780/+624 B = +1/−5/+4 tris, arithmetic checks). (e) DISC
PARITY — Disc1==Disc4 by explicit byte-copy; a 2nd `--deploy` is byte-identical (idempotent); 45
out-of-scope files (the other 3 cells + (12,18) Terrain/Beach1/Sea3/Sea4/Object/Donor, both discs) hashed
byte-unchanged. (f) OFFLINE EYE — `whole_island_eye.py` (`sea1_ladder_{pre,post}.png`), the REAL-ATLAS
corner zoom (`sea1_ladder_zoom_{pre,post}.png`), and the FLAT SHADE-PLAN PRE|POST
(`sea1_ladder_shadeplan.png`, adapts `s12_zoom_render_opus.py`): the shade plan shows **only the 4
red-boxed cells change colour, the rest pixel-identical**; the atlas zoom shows the corner grades
sea2→sea1→sea5→deep with **no hard shallow|deep cut** — and, as the options study predicted (sea1's deep
shade == sea5's shallow shade), the change is **cosmetically near-invisible** at play scale (the material
diff localises to world x 824–832 = the i14/i15 columns; the faint background elsewhere is draw-order edge
noise from the file rebuild, content byte-proven unchanged by gate c/d).

**LEFT ALONE (as the task mandated):** the interior sea2|sea4 tile at `(12,19)` cell `(14,0).S` — byte-
verbatim donor (9,18) geometry and the ONLY sea2|sea4 edge in the entire stock map (lawful-by-precedent).
(12,19)/(11,18)/(11,19) are byte-untouched.

**LOGGED-LATER (unchanged this round):** the shipped `wang_carry_gate` / `_sea_shade_grid` bin only
Sea3/4/5, so a Sea1/Sea2 frame tile reads as deep and is never flagged — the gate could not have SEEN
this corner. Extending the gate alphabet to the coastal shades is the productization gap; deferred (the
one-change rule), NOT this round's job.

**Status: deployed both discs, AWAITING the sail-around playtest** at the SE cove (world ~832,−1212). If
the user confirms, the island's last off-language shore edge is closed and the (8,17)+2×2 desert-beach
carry's water is fully in-language (rim Sea3/5 rung + this shallow Sea1/2 rung both done).

**★ PLAYTEST CONFIRMED (2026-07-20f): "that looks correct now, the transition is clean."** The corner
ladder is IN-GAME PROVEN; the island's water is **FULLY IN-LANGUAGE** — all three defect classes of the
(8,17)+2×2 carry's water are closed in-game (the (11,19) water-only cell over 3 rounds, the 17 Sea3/5
rim seams, and this shallow Sea1/2 corner). THE SHALLOW-LADDER REMEDY is minted to the coast memory:
when a crop leaves shallowest-abuts-deep, the lawful fix is the {sea1,sea5} ladder repartition — never
an invented transition tile (stock authored none; THE SEA5-MEDIATION census). The one open successor:
extend `wang_carry_gate`'s shade alphabet to the coastal shades (sea1/sea2) so this class warns at
carry time — **LANDED same day (`c666ba8`)**: additive `incoherent_deep`+`incoherent_shallow`, deep
verdicts byte-identical, the pre-ladder backup reports exactly the 2 sand-spit tiles, and a fresh
(8,17)+2×2 region carry warns deep==12 + shallow==5 at carry time. **The water-carry arc has NO open
items.**

---

## Round 5 (2026-07-21) — THE CALIBRATED EYE for the ≥130-cell WHOLE-STAMP dunes mint (built + FROZEN, no build judged yet)

THE DUNES SIZE-CLASS LAW (§Round 4) left exactly one lawful path open: a **≥~130-cell
multi-block dunes field that STAMPS A REAL COMPONENT WHOLE** — comp[1] (130 cells, one enclosed
topo-59 hole) on a DESERT host. Per the arc's own hardest law — **CALIBRATE THE INSTRUMENT
BEFORE YOU JUDGE WITH IT** — the eye that will judge that build is built and frozen HERE, against
100% stock, *before any synthesis exists*. Deliverable: `dunes_mint_eye.py` (idempotent,
byte-deterministic — the `out/` renders + JSON regenerate identically; the frozen bands live in
the script's `CRITERIA` dict and `judge()`).

**The three frozen zooms** (this arc's own): WIDE 200×160u sc=6 (frames a whole component +
margin, texture+shaded) · MEDIUM 56×56u sc=16 shaded (play-scale) · TIGHT 24×24u sc=32 UNSHADED
(the row/Rorschach zoom — the only scale where row choice is legible). Stock NULLS rendered side
by side: **both real components in situ** (comp[0] 273-cell @ world (1224,−264); comp[1] 130-cell
@ (902,−780) — THE MINT TWIN), 4 desert|dunes seam windows spanning the known variance
(smooth-organic (18,3) → boxy (13,12)), a pure-desert control, a pure-dunes-interior control.

**THE CRITICAL CALIBRATION LESSON, caught by the instrument's own self-test.** A first cut set the
same-row band from the **map-wide** stock rate (9.8%). The self-test — *judging stock comp[1]
itself, which a faithful whole-stamp equals byte-for-byte* — then **FAILED M2** (comp[1]'s own ring
same-row is **36.4%**, comp[0]'s **15.0%** — both far above the pooled 9.8%). The map-wide pool is
the WRONG null: the judge measures over the mint's ~30-cell ring, not 195 pooled cells, and a small
clustered ring runs much higher same-row. **Gating on the map-wide figure would false-reject a
verbatim comp[1] stamp** — the exact "an uncalibrated instrument is not evidence" failure this arc
keeps re-learning. FIX: the M1/M2 nulls are re-derived at the **mint's own ring scale** — lay
comp[0]'s genuine rows over comp[1]'s real ring geometry at every phase (v2's cross-cluster
transplant method) + comp[1]'s verbatim anchor. The self-test now PASSES; an anti-test (v2-square
footprint + all-row-0 ring) FAILS on M1/M2/M3, as it must.

**THE FROZEN BANDS + PASS/FAIL (calibrated once, then frozen for the round):**

| gate | metric | stock band (ring scale) | wrong-control (out) | stock-vs-stock (not separated) |
|---|---|---|---|---|
| **M1** | luminance jumpiness over the ring | **1.62 .. 7.71** (verbatim comp[1] 5.08) | all-row-0 = 0.00 | comp[0]-rows-on-comp[1]-ring + verbatim all in-band |
| **M2** | same-row adjacency % over the ring | **0.0 .. 0.686** (verbatim 36.4%) | all-row-0 = 100% | comp[0] ring 15.0% / comp[1] 36.4% both in |
| **M3** | silhouette convexity | **0.45 .. 0.78** | v2-square 0.9024 | comp[0] 0.464 / comp[1] 0.754 both in |
| **M3** | max boundary run | **≥ 4** | v2-square = 3 | comp[0] 4 / comp[1] 5 |
| **M3** | enclosed hole present | **required** (comp[1] has one) | v2-square = 0 holes | both real comps have their real holes |
| **M4** | interior-strip-coverage | **≤ 0.02** (both comps ~0.0%) | quilt control 64.5% | both interiors ~all plain mains |

Non-gating diagnostic (reported, never a gate — the arc's explicit ruling): lag-1 row
autocorrelation, STOCK −0.423 vs the BFS emitter's +0.073 (it under-alternates); the jumpiness
metric cannot see this, so it is documented, not enforced. Boundary-strip coverage is a DESIGN
TARGET for the ring (comp[0] 58.5% / comp[1] 52.7%), reported not hard-gated.

**Two honest limits, stated up front.** (1) M2's ring-scale band is WIDE (0–0.686): at ~30 cells
its only real discriminating power is against the DEGENERATE all-one-row — which is precisely the
arc's own conclusion that the blocker shrunk to *"any non-degenerate placement."* (2) The
strongest structural gate is not any single number but **an outline byte-match of the placed
footprint to the comp[1] template** (the v3 shape-fidelity gate): a faithful whole-stamp makes M3
pass by construction, and the eye's real job then reduces to the WIDE-panel twin comparison — the
mint's comp[1]-stamp beside stock comp[1]-in-situ must be indistinguishable. The renders confirm
this is a fair test: comp[1] in situ genuinely carries a **boxy, quilt-like east ecotone** (real
stock), so a calibrated eye must NOT fault the mint for reproducing it — the very false-reject the
uncalibrated rounds 1–3 kept making.

**Status: instrument FROZEN, zero builds judged. `judge(ring_rows, footprint_cells)` is the entry
point the builder calls before deploy; ALL gates must pass, then the WIDE/MEDIUM/TIGHT stock panels
are the reference its renders sit beside. Consistent with the arc's record: 4 dunes rounds spent
zero playtests — this one spends zero too, the eye gates first.**

---

## Round 5 (cont., 2026-07-21) — THE REAL-SCALE comp[1] WHOLE-STAMP DUNES MINT ★ BUILT + DEPLOYED (18/18 gates + frozen eye PASS; awaits playtest)

> **⚠ SITE CORRECTED 2026-07-21 — see §Round 5 (correction) below.** The site named in this section,
> centre **(608,−1376) ≈ block (9,21)**, is **OFF the engine's 24x20 grid** (block rows 20–22 don't
> exist; world z only reaches −1279). It deployed 81 dead files/disc the engine never streamed. The
> mint was re-sited to the IN-GRID stamp site **(1248,−1184) = block (19,18), r56 s2, k=0, blocks
> (18–20,17–19)**; the frozen-eye numbers below are UNCHANGED (a verbatim k=0 stamp is
> site-independent). Read the recipe/gates here; read the *live* coordinates in the correction.

THE DUNES SIZE-CLASS LAW's one prescribed unit — **a ≥130-cell multi-block dunes field that STAMPS
A REAL COMPONENT WHOLE** — is built and deployed. `dunes_field_mint.py` stamps **comp[1]** (130
dunes cells + its 14-cell topo-59 enclosed hole) **VERBATIM** (bijective rigid transform, **k=0
IDENTITY** — comp[1] exactly *relocated*) onto a fresh multi-block `--ground desert` host, the
ecotone rows CARRIED verbatim. Deployed to `FF9CustomMap-world`, both discs (72/72 mesh parts
byte-identical Disc1↔Disc4), MOD-OVERWRITE clear.

**The two design reports RECONCILED empirically** (`dunes_host_probe.py`). The host census owned
SITING (its own centre **(608,−1376)**, the coherent little desert archipelago south of the (8,19)
islet); the stamp design owned the RECIPE — the strict `footprint+ring+2-cell-margin =
dilate3(footprint) ⊆ regular`, which the census's bbox proxy had missed (**r48 FAILS the margin,
exactly as the stamp design found**; the census's int2=270 < the 288-cell dilate3). The winner
satisfies BOTH: **census centre (608,−1376), radius 56, seed 2, dihedral k=0** — 9 blocks
(8–10, 20–22), 490 regular cells, 17 candidate placements. r56 = the stamp design's own
identity-headroom radius; it yields the k=0 identity placement AND the census's desired desert
apron. **A hairline-crack scan drove the seed**: `island.build_landmass`'s big-mint edge refinement
leaves `mesh.weld_audit` near-miss vertex pairs for SOME seeds (the census's own s11 has 9, though
`verify_landmass`'s coarser once-edge/crack gates pass) — the verbatim stamp is seed-independent,
so a **zero-weld seed (s2)** was chosen. (`weld_audit` reads a block's LOCAL-frame verts — audit
PER BLOCK, never the concatenated multi-block list, which would mix 9 local frames.)

**THE STAMP UNLOCKED A ZERO-SYNTHESIS DRESSING** (the stamp design's core insight, realized): at
full-component scale the entire boundary is real comp[1] boundary, so the bijective k=0 transform
CARRIES the ecotone rows verbatim — the dune-side strip (**30 cells**) and desert-side strip (**26
cells**) wear comp[1]'s OWN measured rows. The round-3 BFS emitter is retained only as a residual
fallback — **never invoked** (every ring cell has a verbatim source). The judge therefore lands
**BYTE-IDENTICAL to the eye's self-test**: M1 jumpiness **5.076**, M2 same-row **0.3636**, M3
convexity **0.7536** / max-run **5** / hole present, M4 interior-coverage **0.0** — ALL PASS, exactly
comp[1]'s own values (the verbatim guarantee: k=0 is a pure translation, so adjacency + silhouette
are invariant).

**THE ONE DELIBERATE DEVIATION** — the 14-cell topo-59 enclosed hole (undecoded, non-walkable) is
FILLED with plain dunes mains: the only in-vocabulary faithful option (leaving it desert would
demand a dunes|rock inner ring stock does not paint), it is fully interior (invisible to
silhouette/ecotone), and it makes the interior seamless *walkable* dunes.

**Retile** — 114 dunes-mains + 30 dune-side-strip + 26 desert-side-strip cells; 20 outer-ring cells
untouched (already-correct desert mains). Geometry byte-identical to the plain host (uv + tangent.x
only; zero vertex motion proven).

**GATES — 18/18 PASS**: comp[1]-template match (LAW 5, 130 cells byte-normalized vs the committed
`real_component_1_verbatim`), baseline `verify_landmass` clean, OPEN-OCEAN TARGET, zero vertex
motion (verts + normals), zero-residual classification (mains 268 / strip 112 / **other 0**),
boundary invariance, weld audit **0** (per-block), frame bounds, IDALL_SKIP structurally impossible
(area 0 everywhere), MISS census regression + **MISS==0** every touched block, save-brick probes
(core dunes topo-41, filled-hole topo-41, inner/outer ring walkable), **SHAPE-FIDELITY** (placed
silhouette byte-identical to comp[1]'s template — convexity 0.7536 / max_run 5 / 1 hole), ROW-0
GUARD (rows {0,1,2,3}), and **THE FROZEN EYE** (`dunes_mint_eye.judge`, all M1–M4). effective-prefab
/ wang-carry are N/A by construction (an island mint writes a full `Terrain` override — the s34
divert is armed — + a full-cell `Sea4` + blanked hidden sea parts; there are no cropped-Wang seams).

**THE ONE HONEST LIMIT (measured precisely, flagged for the playtest).** comp[1]'s 279 dune terrain
tiles = **209 mains-rect + 60 strip + 10 OFF-rect "dune-crest" tiles** (a DISTINCT atlas region
u≈0.14–0.20, v≈0.83–0.87 — the elongated ridge streaks visible in the MEDIUM render's stock panel).
The mint reproduces **269/279 (96.4%)** — all mains + all strip verbatim — but NOT the 10 crest
tiles (**3.6%**): the generic grass-derived `assign_mains` only samples the mains rect. This is the
CONCRETE instance of the design's explicitly-DEFERRED dunes-interior-detail gap ("reuse
`assign_mains` unchanged — the same gap every shipped `--ground` family mint carries; none has read
as wrong in-game"). It is **not a frozen-eye axis** (it does not touch silhouette, ecotone, or
quilt), which is why the eye passes. **Follow-up rung, now precisely scoped**: carry the interior
verbatim INCLUDING the crest tiles (k=0 makes it a per-cell-corner UV copy of comp[1]'s exact tiles)
OR decode + place them — either needs the zero-residual classifier extended to admit the crest
atlas region.

**Site / renders** — centre (608,−1376) ≈ block (9,21); the dunes footprint centres near world cell
(152,−344). `out/dunes_field_mint_{wide,medium,tight}.png` place the mint beside comp[1]-in-situ at
the eye's three frozen zooms (WIDE = whole blob, MEDIUM/TIGHT = the ecotone). The WIDE twin reads as
comp[1] relocated; the ecotone-centred MEDIUM shows the verbatim strip mottling matching stock.

**THE PLACEMENT BLOCKER IS CONSUMED.** The arc's remaining blocker (lifted at "any non-degenerate
placement") is *spent*: the verbatim carry needs no synthesized placement at all. **THE DUNES
SIZE-CLASS LAW is satisfied** — a ≥130-cell dunes field that does NOT quilt, reading as comp[1]
relocated. Zero playtests spent to here (the eye gated first, per the arc's record — 5 dunes rounds,
zero playtests). Artifacts: `dunes_field_mint.py`, `dunes_host_probe.py`,
`out/dunes_field_mint.json`.

## Round 5 (correction, 2026-07-21) — THE GRID-BOUNDS INCIDENT: the vacuous open-ocean check off the map edge ★ GATE PRODUCTIZED + MINT RE-SITED

**The catcher was the user's own debug menu.** The whole-stamp mint above deployed to centre
**(608,−1376)** — the host census's own siting, "the coherent little desert archipelago south of
the (8,19) islet." On the first playtest the debug-menu overworld teleport refused it:

> `teleport: (608, -1376) is outside the 24x20 grid (x 0..1535, z 0..-1279)`

**The engine's world is a FIXED 24×20 block grid.** `WMWorld.BuildBlockArray` mints `new
WMBlock[24, 20]` (`Assembly-CSharp/Global/WM/WMWorld/WMWorld.cs:1675`); block cols run 0..23, rows
0..19; world x spans [0, 1535], z spans [−1279, 0]. Centre z = **−1376 is block row 21.5** — rows
**20/21/22 do not exist**. The mint's 9 blocks (8–10, 20–22) were **all off-grid**: the engine never
streams those cells, so the 81 files/disc were **dead on disk**. Every one of the census's alternate
sites ((10,22)/(13,21)/(15,20)/(8,22)/(16,20)) is off-grid too.

**ROOT CAUSE — the session's vacuous-gate class, now in a shipped path.** The one gate that should
have caught it — `landmass()`'s **OPEN-OCEAN TARGET** check (`_real_block_parts` must be empty) — was
**VACUOUSLY TRUE off the map edge**: there are no per-block mesh assets in rows 20–22 *because there
is no map there*, so "empty ⇒ open ocean" passed. No chokepoint in `island.py` validated grid bounds
(`transplant`/`transplant_region` already did, via `GRID_X/GRID_Y`; `build_landmass` never did), and
the mint's own `deploy()` wrote through `mesh.deploy_override` with no bounds check. **A check that is
trivially satisfied outside its own domain is not a gate.**

**THE GATE, PRODUCTIZED (kit).** One authoritative constant, three chokepoints:
- `mesh.GRID_COLS, GRID_ROWS = 24, 20` (+ `GRID_WORLD_X_MAX 1535`, `GRID_WORLD_Z_MIN −1279`),
  `mesh.block_in_grid(x,y)` and `mesh.require_block_in_grid(x,y)` — cited to `WMWorld.cs:1675` and the
  debug-menu bounds `Ff9mkDebugMenu.cs:1595`. `terrain.py`/`water.py` (and thus `transplant.py`)
  **re-export** `GRID_X/GRID_Y` from here, so there is now **ONE literal `24, 20`** in the kit.
- **`build_landmass`** (world-island) refuses off-grid *before building a single `BlockMesh`*, naming
  every offending block and the centre/radius to shift.
- **`deploy_override` / `deploy_donor_sidecar`** (the lowest write layer) refuse off-grid *before
  touching the filesystem* — belt-and-braces catching any direct-deploy path, including the study's own.
- Tests: `tests/test_world_grid_bounds.py` (18) — the exact (9,21) repro refused, corners/last-row-col
  (23,19) accepted, col 24 / row 20 / negatives refused, single-source assertion, both write funcs.

**THE MINT, RE-SITED (measured, not guessed).** `dunes_host_probe.py` re-ran restricted to IN-GRID
candidates, seeded with the stamp design's verified (1248,−1184). The winner by measurement:

| | centre | block | radius | seed | dihedral | blocks | regular | placements | weld |
|---|---|---|---|---|---|---|---|---|---|
| **winner** | **(1248,−1184)** | **(19,18)** | **56** | **2** | **k=0 identity** | **(18–20,17–19)** | 490 | 17 | **0** |

On-grid, STOCK open ocean, clear of every live cluster (comp20 (6–7,18–19), desert islet (8,19), the
(8,17)-beach island (11–12,18–19), water-only (11,19)), MOD-OVERWRITE clean, 2-cell placement margin
satisfied (dilate3 = 288 ⊆ 490 regular). **k=0 = a pure translation, so the frozen eye is
byte-identical to the off-grid build**: M1 5.076 · M2 0.3636 · M3 conv 0.7536 / max_run 5 / hole 1 ·
M4 0.0 — the verbatim stamp is **site-independent** (all 18 gates + the eye re-passed at the new
site). Deployed both discs (81 files/disc + Disc4 mirror, 0 free-ride pins). The 162 off-grid dead
files (r20/r21/r22 × 2 discs) were backed up to `backups/dunes-mint-gridfix.20260721/` and deleted;
the live tree now holds exactly the pre-existing content + the mint (r17 (18–20,17); r18/r19 = live
cols 6–12 **+** mint cols 18–20; no r20–22).

**THE LAW.** *A gate that is vacuously satisfied outside its domain is not a gate.* The open-ocean
check answers "is this a real world block?" — off the map that question is meaningless, so it must be
**preceded** by "is this a block the engine has at all?" The debug menu already knew the answer
(`bx >= 24 || bz >= 20`); the authoring side now speaks the same 24×20 grid. Artifacts:
`dunes_host_probe.py` (re-sited), `dunes_field_mint.py` (parameterized centre/radius/seed, defensive
`build_host`, in-grid ladder), `ff9mapkit/world/mesh.py` (+ `terrain.py`/`water.py`/`island.py`),
`tests/test_world_grid_bounds.py`.

## Round 5 (forensics + eye upgrade, 2026-07-21) — THE CASTELLATION VERDICT + THE GRAZING MESH EYE ★ INSTRUMENT FROZEN (Phase 1; no carry built yet)

**The verdict (user, in-game A/B).** The re-sited whole-stamp mint at centre **(1248,−1184)** (blocks
(18–20,17–19), r56 host, commit `0b0e768`) is **REJECTED**: the dune/desert ecotone reads as an
**unaligned castellated grid of tiles**; stock comp[1] in situ *"reads great"* — smooth and organic.
A grazing-angle A/B render (same camera both) separates them the same way the eye did (below).

**ROOT CAUSE — two factors, one root: the label-stamp pipeline painted ROW LABELS onto a synthetic
plain island instead of carrying the donor MESH.** Read-only byte A/B of the DEPLOYED `.ff9mesh`
overrides vs stock comp[1] (`byte_compare.py`/`dunes_ab.py`), 143/143 dune cells paired under the k=0
translation **T=(87,−101)**:

- **Factor 1 (dominant) — zero sub-cell vertex motion.** The mint enforced zero vertex motion, so its
  dune|desert boundary is **100 % on the 4u grid** (`frac_on_grid 1.0`, `mean_offcell 0.0`, n=136 seam
  endpoints). Stock comp[1] has **14.6 % off-grid conforming seam verts** (`mean_offcell 0.0219`,
  `p90 0.103`, n=260). A staircase *by construction*.
- **Factor 2 — every ecotone tile at orientation 0, and the UVs regenerated not carried.** Stock
  distributes the pale→red ramp tiles across all four **{0,90,180,270}** boundary-awarely; the mint is
  monolithically ori-0. Paired same-orientation **15.8 %**, class-agreement **60 %**, and the mint's
  per-corner UVs **byte-derive from the donor for only 2.1 % of cells** — proof they were
  *regenerated*, not *copied*.
- The interior mains are generative (uncorrelated with stock), and the 14-cell **topo-59 butte hole
  was filled FLAT** (mint footprint 144 = 130 comp1 + 14 filled), losing the butte stock renders behind
  the seam.

**Why the old eye passed it (the blind axis).** `dunes_mint_eye.py` judged ROW LABELS at a top-down
zoom. On the DEPLOYED bytes its **M1 jumpiness = 5.076 and M2 same-row = 0.3636 are IN-BAND —
byte-identical to stock's own self-test** — because the pipeline *nailed the row-label axis it was
optimizing*. The row eye caught only the shape defects (M3 convexity 0.835 + the hole-fill); the
**castellation is invisible to it**. *A row-label eye cannot see mesh geometry.*

**THE FIX (build phase, NOT this round): a TRUE MESH CARRY** — rigidly relocate stock comp[1]'s ACTUAL
Terrain content (verts incl. the sub-cell conforms + the butte relief, per-corner UVs incl.
orientations, tangents/topo) onto the deployed desert host, THE CARRY LAW applying (carried content
rigid; conform goes to the host ground at the ring). Deferred to Phase 2.

**THIS ROUND (Phase 1) — THE GRAZING MESH EYE, `dunes_grazing_eye.py`, promoted from the forensics +
FROZEN.** A mesh-level judge with three new numeric gates, each **calibrated on stock first** (comp[1]
must clear every gate before any mint is judged) and each with a **donor-derived band**:

| gate | what it measures | donor (stock comp[1]) | band | deployed mint | verdict |
|---|---|---|---|---|---|
| **A** sub-cell boundary-conformance | off-4u-grid seam-vert fraction + mean off-cell | 0.146 / 0.0219 (n=260) | off_grid ≥ **0.0731** AND mean ≥ **0.01096** (½ donor) | **0.0 / 0.0** | **FAIL** |
| **B** orientation fidelity + byte-derivation | paired same-ori vs donor; carried-UV byte match | 1.0 / 1.0 (identity, n=95) | both ≥ **0.90** | **0.158 / 0.021** | **FAIL** |
| **C** boundary-framed render | grazing render (painter-sorted, per-corner UV, 2 pitches) framing-ASSERTED to contain the boundary, then frontier-profile organicity (slope reversals /100col) | 46.7 / 56.25 | min-pitch ≥ **23.33** (½ donor worst) | **1.354 / 3.125** | **FAIL** |

- **GATE A** is the direct sub-cell measure; a rigid carry reproduces the donor exactly (pass), a
  grid-locked stamp is 0.0 (hard fail). **Zero vertex motion on a real-geometry donor is a RED FLAG,
  not a pass.**
- **GATE B** brute-forces each tile's identity over all four orientations (so the recovered ori is
  real), and the **byte-derivation assert** demands the carried cells' UVs *equal the donor's bytes*
  — a carry copies verbatim (1.0), a regenerate does not (0.021).
- **GATE C** is the render the arc never had: a low-pitch GAME-CAMERA perspective through the real
  atlas, **painter-sorted**, per-corner UV. Its framing is **asserted programmatically** to contain
  the dune|desert boundary — *the TIGHT top-down mis-framing was a real miss* — and an interior-zoom
  camera is **correctly blocked** (0 desert px, "cannot judge"). The organicity metric is the
  render-space read of Factor 1: stock's off-grid verts make the rendered frontier WIGGLE (~46–56
  reversals/100col); the grid-locked mint is a monotone staircase (~1–3). A ~25× separation, measured
  on both before freezing (the gradient-peakedness and tortuosity candidates were tried and **do not
  separate** — discarded).

**INSTRUMENT INVARIANTS (all hold; the eye is frozen).** SELF-TEST: stock comp[1] vs itself **PASSES
all three**. ANTI-TEST: the deployed bytes **FAIL all three** (the perfect anti-fixture). MIS-FRAMING
guard blocks an interior zoom. Re-runs are byte-deterministic (stock bytes + deployed bytes). The
calibration witness `out/dunes_grazing_eye_calib_pitch{22,34}.png` shows stock smooth / mint
castellated in the same frame.

**INTEGRATION.** `dunes_mint_eye.judge(mesh=…)` now delegates the three mesh gates to
`dunes_grazing_eye.judge_mesh` and requires them for the overall verdict (non-breaking — `mesh=None`
preserves the frozen row self-test byte-for-byte). The combined self-test PASSES; the combined
anti-test on the deployed bytes FAILS with **3/3 mesh gates failing** while M1/M2 stay in-band —
*the row flow now spends the mesh axis it was blind to.*

**THE LAW (extended).** *Calibrate the instrument on stock before you judge with it* now covers the
RENDER axis: stock must render smooth through the grazing eye before any mint is judged, and every
band is the donor's own value with a stated margin. And: **a row-label eye is blind to mesh geometry —
judge the BYTES the engine renders, not the design intent.** Artifacts (all committed): the instrument
`dunes_grazing_eye.py` + `out/dunes_grazing_eye.json` + `out/dunes_grazing_eye_calib_pitch{22,34}.png`
+ `out/dunes_grazing_eye_judge_*.png`; the forensic provenance `dunes_grazing_forensics.py` (the raw
A/B render) and `dunes_byte_ab.py` (the per-tile byte A/B that recovered the orientation histogram);
integration in `dunes_mint_eye.py` (`judge(mesh=…)` + the direct-run demo).

## Round 6 (2026-07-21) — THE TRUE MESH CARRY ★ BUILT + DEPLOYED (10/10 gates + the frozen eye PASS to the donor values; awaits playtest)

**The correction of Round 5's LABEL-STAMP FALLACY, built and deployed.** `dunes_true_carry.py` rigidly
relocates stock comp[1]'s **actual Terrain mesh** — verts (incl. the 14.6 % sub-cell conform seam
verts + the topo-59 butte relief), per-corner UVs (orientations, crest tiles, real interior mains),
tangents/topo/normals — onto the deployed r56 desert host at centre **(1248,−1184)**, *replacing* the
label-stamp cells. It passes the frozen grazing eye **to the donor's own values by construction**, which
is the acceptance target a faithful carry must hit.

**THE CARRY (measured).** Placement **T=(87,−101)** (donor→deployed, topo-41 bbox-min; lands exactly on
the label-stamp cells). Carried region **R = 225 cells** = dunes **119** + desert ecotone/weld margin
(2 rings) **81** + topo-59 butte-hole **17** + enclosed topo-49 **8** — comp[1]'s content verbatim,
**zero grass carried** (the green patches in the render are comp[1]'s own carried topo-49 tiles through
the atlas, present in stock too). Donor is **RIGID**: a whole-cell xz shift (`Tw = CELL·T`) preserves
every vert's fractional-in-cell coord → the UV decode is **byte-identical** (that is *why* GATE B is
1.0), plus a uniform **DY = +0.4656** seats the desert weld ring at the host's flat Y (3.20). All
seating deformation goes to the HOST: 193 kept-host weld-ring verts **snap** to the carried donor verts
(0 near-miss pairs). Touched blocks: **(18,18),(19,17),(19,18),(19,19),(20,18)** — 5 of the 9 mint
blocks; the other 4 (and all coast/sea/apron) are left exactly as deployed.

**THE GATES (all 10 PASS).** Containment (no built block escapes the deployed footprint) · FLAT-MESH
(vcount==idx) · grid bounds · **weld audit 0** · **frame bounds clean** · **MISS census 0** (full ground
coverage; the butte grounds as topo-59 — a raised mesa with mesh, non-walkable by the engine's topo
mask exactly as stock, not by absent ground) · no IDALL_SKIP · and the frozen eye to the donor values:
**GATE A 0.146 / 0.0219** (= stock, n=260, vs the stamp's 0.0/0.0) · **GATE B paired-ori 1.0 /
byte-derivation 1.0** (identity, vs the stamp's 0.158/0.021) · **GATE C organicity 54.1/55.6** (band ≥
23.3, vs the stamp's 1.35/3.13). The grazing A/B `out/dunes_true_carry_ab_pitch{22,34}.png` shows the
carry reading as comp[1] relocated — the organic red ecotone ramp, the tan dunes, and the carried rock
butte all faithful; the desert host + ocean beyond correctly replace stock's grass continent.

**What the carry brings that the stamp lacked (measured).** The **topo-59 BUTTE** — 38 cells of real
relief, Y **1.37 → 8.20** (median 4.91) — where the stamp filled it FLAT; **79 distinct dune per-corner
UVs** carried verbatim where the stamp regenerated ori-0 tiles; and the **sub-cell conform seam verts**
that make the boundary read organic. Deployed Disc1 `Block[19][18] Terrain` grew **81452 → 95804 bytes**
(butte relief + conform verts + border splits) — the mesh the flat stamp never had.

**TWO MECHANICAL LAWS minted by the build (a rigid cell-translation carry is not a per-block copy).**

1. **THE PHASE-SHIFTED PARTITION law.** A cell translation with **T mod 16 ≠ 0** (here (7,11)) puts the
   HOST block boundaries at *different* 4u lines than the donor's. Stock terrain keeps **every one of
   112 170 verts strictly inside its block frame** (0 pokes, measured) — a per-block partition — so a
   whole-tri carry whose sub-cell conform verts land just past a phase-shifted border is **new geometry
   the engine has never been shown**. The fix is the kit's own multi-block law: **re-partition every
   carried tri at the host block borders** (`transplant.clip_poly`, the `_split_at_borders` cut — pos/
   nrm/uv lerped on the cut, tangent/IDALL kept verbatim, the cut `t` bit-identical on both sides →
   watertight; a tri fully inside a block passes byte-identical, so GATE B stays 1.0). Every built block
   is then strictly in-frame like stock (`max_poke 0.0`).
2. **THE BLOCK-LOCAL WELD-SNAP law.** A weld-ring corner **on** a host block border is shared by two
   blocks; the carried conform vert is in-frame in ONE of them (a sub-cell wiggle interior to it) and
   appears as the exact `z=border` cut vert in the other. Snapping a kept-host vert to a *single* world
   value pokes it (a vert in-frame for (19,17) pokes +0.57 when applied to (19,18)'s copy). Key the snap
   **(blk,gi,gj)** — snap every host vert to the carried donor vert of ITS OWN block → exact in-block
   weld, strictly in-frame.

**THE LABEL-STAMP FALLACY (the law).** *A verbatim stamp must carry the MESH — verts + per-corner UVs +
tangents — not row LABELS through a synthetic frame.* Round 5's pipeline built a flat synthetic island
and stamped a `{cell: row}` map onto it, **regenerating** every ecotone UV at ori-0; the result was
byte-faithful on the row axis it optimized and **castellated everywhere the mesh actually lives** (the
boundary 100 % on-grid, 2.1 % of UVs byte-deriving, the butte filled flat). This is **THE FORM LESSON's
dunes-pipeline instance** — *real content (the row language) through a synthetic frame (a flat stamp) is
still synthesis.* The only faithful path was the one the eye's self-test always pointed to: **carry the
donor's bytes.** A true carry passes the eye because it *is* the donor, relocated.

**Roadmap ledger.** The DUNES family's *"minimum size class / no small-blob mint"* blocker (§Round 4,
THE DUNES SIZE-CLASS LAW) is now **closed the lawful way**: not a synthetic ≥130-cell island but a
**verbatim mesh carry of stock's 130-cell comp[1] + its butte** onto our host — the first proven
synthetic-site dunes ensemble. Deployed both discs (auto-mirror 45 files, Disc4 byte-identical), backups
→ `backups/dunes-true-carry.20260721/` (10 Terrain files, both discs). **Awaits the in-game A/B playtest
at the same site (1248,−1184)** vs stock comp[1] (902,−780). Artifacts: `dunes_true_carry.py` +
`out/dunes_true_carry.json` + `out/dunes_true_carry_ab_pitch{22,34}.png`; the frozen eye
`dunes_grazing_eye.py` was **not touched** (Phase-1 freeze honored). Revert: restore the 10 backed-up
Terrain files (both discs).

## Round 7 (2026-07-21) — THE FRINGE CENSUS ★ the two playtest fringe defects decoded to the vertex (census + fix designed + gates frozen; NOT yet built)

**The playtest verdict on the TRUE MESH CARRY (Round 6):** *"The ecotone is nice now"* — the dunes|desert
seam LANDED. Two NEW fringe defects, with two ground-level screenshots: (1) *"lifted or shrunken seams in
the ground"* — long thin BLUE SLIVERS (sea/void through the terrain), one *"around (1220,−1152)"*, exactly
on the block border z=−1152; (2) *"hard-edged grass ecotone tiles"* — carried green fragments reading as
triangular green shards with dead-straight edges against the red desert.

**The instrument the arc never had — `dunes_fringe_census.py`, the CROSS-BLOCK coincident-edge test.** The
recorded blind spot (coast memory): *"the adjacency test only sees WITHIN-block edges, never a coincident
edge across a block boundary."* `weld_audit` is per-block LOCAL-frame — two verts on a shared border read
z=0 (top of the by−1 block) vs z=−64 (bottom of the by block): same WORLD line, different local values, so
a cross-block crack is **structurally invisible** to it (and to the MISS census, which samples per-cell
coverage inside a block). The new census lifts BOTH sides of every shared border into the WORLD frame and
compares the border cross-sections by **border-edge interval coverage + Y-profile** (a vertex-match test
alone misses the notch — both endpoint verts can coincide while one side lacks the border edge between
them). **Calibration law honored: the STOCK donor region (blocks 12–15,10–13) censuses 0 steps / 0 holes**
across all 24 internal borders — the instrument raises zero phantom seams on shipping data.

**THE CRACK/STEP CENSUS — 4 defects, ALL on carried|carried borders, ALL cross-block-reconciliation
failures, mechanism proven to the vertex** (drilled the actual tris):

| # | kind | border | site | measure | mechanism |
|---|------|--------|------|---------|-----------|
| 1 | HOLE | [19][17] and [19][18], z=−1152 | x in [1216,1220] w≈4u | void | phase-shifted NOTCH |
| 2 | HOLE | [19][17] and [19][18], z=−1152 | x in [1248,1256] w≈7.7u | void | phase-shifted NOTCH |
| 3 | STEP | [18][18] and [19][18], x=1216 | z in [−1171,−1165] | dY=0.12 | block-local WELD-SNAP miss |
| 4 | STEP | [19][18] and [20][18], x=1280 | z in [−1172,−1165] | dY=0.33 | block-local WELD-SNAP miss |

- **THE PHASE-SHIFTED NOTCH (holes).** A sub-cell CONFORM vertex from the donor lands just *off* a
  phase-shifted block border (e.g. world z=−1151.43, 0.57u inside block [19][17]'s frame). In the block
  where it is interior it survives verbatim, pulling that block's boundary into a notch off the border
  line; in the neighbour the *same* donor geometry is clipped exactly at z=−1152 (straight). The two
  boundaries no longer coincide → a thin triangular void where sea/void shows through = the BLUE SLIVER.
  The user's *"(1220,−1152)"* sighting is the right edge of defect #1. **This is the Round-6 phase-shifted
  partition's failure mode the `clip_poly` watertightness argument missed: the argument holds for a tri
  the two blocks BOTH clip, but a conform vert interior to one block is never clipped there — only in the
  neighbour — so the two boundaries diverge by the vert's off-border distance.**
- **THE BLOCK-LOCAL WELD-SNAP MISS (steps).** Round 6's conform-snap (which seats the flat host up to the
  carried donor margin) is keyed **(blk,gi,gj)** — deliberately, so a border-corner vert in-frame for one
  block does not poke the neighbour. But a carried donor vert that lands ON a block border is registered
  only in the block that owns the cell; the neighbour host block's flat vert (Y=3.20) finds no snap target
  and stays flat while the carried side is elevated (donor+DY, 3.32/3.54) → a vertical step = the
  *lifted/shrunken seam*. **The block-local key that fixed one poke opened the reciprocal gap: a border
  corner needs the carried target registered in BOTH blocks.**

**THE GREEN-SHARD CENSUS refutes the "62+7" grouping — only 7 tris render green.** Atlas-sampled greenness
(G − max(R,B)) over the 5 deployed blocks: **topo-0 grass = +9.9 (the ONLY green-positive topo,** RGB
97,107,57, olive**)**; topo-49 mural = −26.3 (RGB 139,113,78, **brown rock**, mean 8.9u from the topo-59
butte). So the *"green shards"* are the **7 topo-0 grass tris only**; the **62 topo-49 murals are the
mesa's brown mural faces — genuine dunes-ensemble content, KEEP.** Donor-context classification: the 7
grass tris sit in desert-dominant cells that in stock comp[1] lay on the grass|desert ecotone with the
grass continent behind; the carry amputated the grass side (our island is all-desert) leaving lone green
tiles against red desert = **orphan-grass-stumps, THE ENSEMBLE LAW's amputation-stump class.** They rode
along despite grass not in CARRY_FAMS because CARRY_FAMS only gates the *margin* cells — a dunes/desert
dominant BLOB cell carries **all** its centroid tris, including a stray grass one. (The Round-6 note *"zero
grass carried"* was true at the cell level, false at the tri level; the census caught it.) **The fix
vocabulary** is stock's own dune-ensemble desert margin: **86 desert / 19 t49-mural / 24 hole-butte / 4
grass** — i.e. re-dress the orphan grass to plain desert.

**THE FIX (designed + mechanism PROVEN offline, NOT yet built).** `simulate_fix()` applies three fixes to
in-memory world soups and re-censuses → **cross-block steps=0, holes=0, green=0** (all fringe defects
closed):
- **FIX-H (holes):** snap every carried vert within (1e-4, 1.0u) of a block-border plane ONTO it — the
  notch vert stretches its tri down to the border, filling the gap; both sides become the same straight
  border edge.
- **FIX-S (steps):** the cross-block form of Round 6's conform-snap — register a carried border-corner
  target in BOTH adjacent blocks (or, post-hoc, raise the matched-t border verts to the per-t MAX Y so the
  flat-host side welds UP to the carried margin).
- **FIX-G (green):** re-dress each of the 7 topo-0 grass tris to desert (topo-17 + desert-mains UV).
- **EYE PRESERVED (empirically substantiated):** the fix touches **17 distinct world positions**, every one
  **≥8.9u from any dune-footprint cell** (median 23.5u), topos {0,16,17,58} — **zero topo-41 dunes, zero
  within 8u of the dune|desert boundary the frozen eye judges.** So GATE A/B/C stay at their stock-exact
  values by construction (the fix lives entirely in the flat desert margin + mesa base + the amputation
  stumps). **The best home for the fix is the CARRY level (`dunes_true_carry.py`): pre-quantize near-border
  donor verts onto the phase-shifted borders before re-partition (closes holes) + register the weld-snap
  target for both border blocks (closes steps) + strip/re-dress topo-0 tris inside carried cells (closes
  shards) — then re-run, which re-asserts all 10 gates + the frozen eye, and the census on the rebuilt
  blocks must read 0/0/0.**

**PERMANENT GATES (frozen into `dunes_fringe_census.py`).** (1) *cross-block seam NULL* — stock donor
region 0 steps/0 holes (calibration); (2) *deployed cross-block seam integrity == 0* — the fix target,
frozen at the known 4-defect set so a regression that ADDS a seam is caught even before the fix lands;
(3) *no orphan grass shard* — 0 topo-0 tiles with an all-desert deployed 8-neighbourhood. **KIT-PRODUCTIZATION
candidate:** promote the cross-block interval-coverage census into `world/mesh.py` as a
`cross_block_seam_audit(blocks)` companion to `weld_audit` — every multi-block carry (Uaho / crag /
horseshoe / comp20, the coast ladders) has the same blind spot, and this is the general instrument for it.
**NOTHING WAS DEPLOYED THIS ROUND** — census is read-only, the fix is simulated in-memory; the 5 carried
Terrain blocks are byte-untouched on both discs. Artifacts: `dunes_fringe_census.py` +
`out/dunes_fringe_census.json`.
