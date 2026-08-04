# THE TILED-MAINS FILL — capability 1, registered 2026-08-04 before building
# ★ BUILT + SCORED same session — results at the bottom; offline-complete, no deploy yet

MORPH-ENVELOPE.md proved the dominant deep-morph blocker (~15 window-verbs on comma,
isthmus, crescent) is a MISCLASSIFICATION: the "painted-mural" refusal fires on *not
grass* (`CliffWindow.grass = topo == 0`, coastmorph.py:150), while 5 of 6 refused tops
are heavily TILED (8–34 uv-rects, 62–98% reuse) — a real fill language, more repetitive
than the grass reference that works.

## The design (CARRY THE TILES — the fill repeats measured tiles, never synthesizes)

1. `CliffWindow` collects ALL non-cliff terrain (`topo != 58`) as the window's mains,
   not just topo-0 grass. Drop selection stays geometric (unchanged).
2. Lane pick by MEASUREMENT, not topo list: if every dropped mains tri is topo-0 →
   the existing parametric grass fill, untouched. Else measure the local top's tile
   language (uv-rect reuse); TILED → the translate-clone fill; genuinely uv-unique →
   the honest mural refusal (now measured, not assumed).
3. The tiled fill is the PROVEN water vocabulary applied to land: per fill tri, the
   nearest source tile's affine map, evaluated translate-shifted into the source tile's
   own 4u cell (exactly `tile_for` at coastmorph.py:6425, in the same function). Source
   idall per tri (carries the real topo). Same lattice + Delaunay + CRACK + GRAIN gates.

## Predictions (falsifiable, scored after the build)

* **D-1 THE FLIP** — ≥1 previously mural-refused window on EACH of comma, crescent,
  isthmus passes the real `transplant_region --dry-run` gates CLEAN at headland depth
  ≥6 (candidates with passing bumps: comma (9,6) L=47.8 / (10,5) L=97.7, crescent
  (15,1) L=65.7 / (16,1) L=68.7, isthmus (7,7) L=45.4). FALSIFIED IF any of the three
  masses ends with zero CLEAN deep windows.
* **D-2 NO REGRESSION** — the (7,17) grass headland-8 / bay-6 tweak plans are
  byte-identical before vs after (repr comparison), and the coast domain test files
  stay green.
* **D-3 FAIL-CLOSED** — a genuinely uv-unique top still refuses via the measured
  discriminant: isthmus (6,6)'s topo-19 window (9% reuse — the one real mural in the
  refused set) keeps its mural refusal. Mutation: inverting/zeroing the reuse threshold
  must be caught by a test.
* **D-4 CARRIED VOCABULARY** — the tiled fill mints NO new tile language: every fill
  tri's uv map is a translate-clone of a real source tri (asserted by construction),
  and the fill's uv singular values sit inside the source envelope ×[0.7, 1.3] (the
  water-density-gate form, applied to land).
* **D-5 THE WALL RISK** (measured before building the fill) — the wall rebuild's CYC
  U-cycle (0.8242, 0.7617, 0.6992, 0.8867) was measured on grass islands; predicted:
  desert/brush cliff walls carry the SAME 4-phase ramp structure with possibly
  different U constants, so the phase harvest generalizes by reading the window's own
  clean gaps. FALSIFIED IF the walls do not quantize into 4 phases at all — that
  becomes capability 3's territory and caps this build at bays/headlands on windows
  whose walls do quantize.

## Expected residuals (NOT failures of this build)

Windows whose bump already refused sea3 — isthmus (6,6)/(7,6), crescent (16,1)
L=51.2 / (16,2) — will re-refuse at the sea3 gate once mural clears: that is
capability 2's lane, and surfacing it here is the honest ordering.

---

## SCORES (built + swept the same session; MORPH-ENVELOPE.tsv regenerated)

* **D-1 — 2 of 3 CONFIRMED, the third is a TRUE NEGATIVE.** Comma ★: (9,6)
  headland 8 + 12 CLEAN / bay 6 CLEAN; (10,5) headland 8 CLEAN / bay 4 CLEAN.
  Crescent ★ (through excise composition): (17,1) headland 8 + bay 6 CLEAN;
  (16,1) headland 8 + bay 4 CLEAN. Isthmus: NOT flipped — and rightly: at region
  scope its deep windows' crease drop consumes topo-49 at **5% reuse (78/57)**, a
  genuine painted mural. The refusal is the discriminant working. Deep shape
  control is now **3 of 8 masses** (chain, comma, crescent), up from 1.
* **D-2 CONFIRMED** — (7,17) headland-8/bay-6 tweak plans byte-identical
  (78,998-char content dump), all golden hashes green, 52/52 domain tests pass.
  The mains widening initially DEEPENED the grass bay envelope (10/14 CLEAN) via a
  mixed grass+topo-31 clone fill — an unproven look; THE ONE-LANE LAW (below)
  removed it and restored the old envelope exactly.
* **D-3 CONFIRMED** — isthmus (7,6) refuses naming topo-49 + its measured reuse;
  the corner (0,0)'s topo-49 (0%, 134/129) now refuses as mural too (same verdict
  as before, earlier and more honest gate). Same topo number, opposite verdicts on
  crescent (90%) vs isthmus (5%) — topo NEVER decides.
* **D-4 CONFIRMED** — translate-clone asserted by test (fill uvs inside expanded
  source rects; idall carriage; desert topo present in the fill) + the MAINS
  DENSITY GATE (source sv envelope ×[0.7,1.3]).
* **D-5 CONFIRMED as predicted** — comma/crescent walls carry their own 4-phase
  ramp (0.4277/0.4902/0.5527/0.6152, wrap seam +0.25; grass CYC matches ~0 gaps);
  the harvest reads it from the window's clean gaps, grass CYC stays the
  byte-identical fast path. The capped case landed exactly where predicted: the
  isthmus (7,7) wall does NOT harvest (no consistent 4-cycle) → capability 3.

**Mutation pass: 6/6 killed** (gate constant, discriminant, translate offset,
seam fold [synthetic specimen — no palette wall witnesses it], ramp-consistency
flag, one-lane law [decode_id-remap specimen]).

## New laws (memory + module docstring carry them)

1. **THE MEASURED MURAL GATE** — fill admission is uv-rect reuse (≥3x fraction,
   threshold 0.40 in the 5–9% vs 52–93% gap), censused over the WINDOW'S OWN
   rect. Region vs single-cell census can differ near the line (isthmus topo-19:
   37% single-cell / 52% region) — the build's rect is the truth.
2. **THE ONE-LANE LAW** — a drop mixing grass with a tiled family refuses; ring
   extensions admit only already-gated families (a new topo entering an extension
   would dodge the mural gate).
3. **THE HARVESTED WALL CYCLE** — grass CYC first (byte-identical), else the
   window's own clean gaps must yield ONE ramp-consistent 4-cycle (+0.25 seam
   fold); ambiguity refuses.
4. **Grain-aware clearance ladder (tiled lane only)** — the grain gate sits
   INSIDE the ladder with a denser 0.9 rung; grass ladder untouched.
5. **Scanner: outline-escape is depth-dependent** — removed from _STRUCTURAL, so
   ladders retry shallower and report honest ceilings (e.g. (10,5) bay 4 found
   where D=6 used to end the probe).

## ★ DEPLOYED for the in-game verdict 2026-08-04

A fresh crescent instance with the (17,1) steered-window **headland-8** (excise +
`cliff_headland`, the tiled-mains fill + harvested wall cycle) at Disc9 blocks
(0,4)+4x2 in `FF9CustomMap-world` — the owner-approved crescent at (18,17) is
untouched. Deploy CLEAN (52 files); rim-retiled with THE CROP-SEAM WIDENING +
THE CUT-VERT LAW live (107 quads, under 3→0, over 23→0). The promontory sits at
the rect's east end, world ≈ (192–228, −273..−276), block (3,4). ⏳ awaiting the
owner's verdict on the fill's tile language vs the native top.

## Registered residuals (next capabilities)

* **Capability 2 (sea3 windows)**: unchanged ~9 refusals across isthmus/chain/
  small/crescent — now the single biggest blocker class.
* **Capability 3 (wall forms)**: comma (10,6)/(9,7) region windows die on
  `window gap N` decode; isthmus (7,7) on the failed harvest.
* **Excise∩morph composition**: crescent (14,2)/(15,2) + deep (16,1)/(17,1)
  rungs fail `gate:drop[terrain]` — the morph's drop set overlaps the excise's
  dropped territory (double-drop scope mismatch). Not blocking (3 crescent
  windows CLEAN); worth one look before a crescent morph deploy.
