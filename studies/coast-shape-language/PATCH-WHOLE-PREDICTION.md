# THE PATCH-WHOLE LAW — study registered 2026-08-04, BEFORE building

The bent-crescent rounds 4-6 falsified per-tile grass handling three ways: uv escapes
(fixed — THE TILE-RECT CONTAINMENT LAW), interior-tile patch extension (fixed — THE
WEDGE GROUND LAW), and finally the owner's round-6 verdict on the residue: "you're
trying to seam the unseamable. i count 5 different 1-edge grass tiles aligned to each
other, and still seaming." A cut patch's KEPT edge tiles face the fill across a line
their tiles were never coded for — no reproduction fixes that.

## The census (grass_patch_census.py, map-wide disc 1)

* 19 blocks carry topo-4; **90 distinct uv rects**: 3 interior workhorses (217/203/203
  uses), ~10 edge-family tiles (16-57 uses), ~60 one-off coast/feature-cut rects.
* **Neighbour-context is SOFT, not coded**: per-rect directional consistency runs
  40-90%, never deterministic. This is NOT a Wang system like the sea strips (whose
  EDGESET2STRIP decode is ~100% consistent) — it is artist-placed form with habits.
  Decoding it as a tile language would repeat the terrace-wall dead end (correct
  tiles on invented arrangement still fail at form).
* **The unit is the PATCH**: 20 connected components, sizes 210, 115, 31, 26, 21, 20,
  19, 18, 17, 13, 12, 11, 11, 10, 10, 9, 6, 6, 5, 1 cells. Authored shapes.

## The law under test

**THE PATCH-WHOLE LAW** — a structural morph's drop may not CUT a patch-system
family (topo-4 grass; presumptively also topo-38 brush, topo-42): it either consumes
a whole component (refilling pure modal ground — the patch honestly disappears) or
does not touch it (the window steers away). The fill never emits patch tiles at all;
patch form enters new terrain only by the carry lane (world-mountain's precedent),
never by tile reproduction.

## Predictions (falsifiable, scored before any deploy)

* **P1 — THE CUT MEASUREMENT**: the deployed (17,1) window's drop cuts a patch
  component; measure its size and whether whole-component extension stays within the
  morph's reach gates (wedge/crease footprint + outline-vert containment). Expected:
  the component is the mid-size southern patch and extension is OUT of reach (the
  patch runs ~40u south of the crease) → the (17,1) window as-deployed is UNLAWFUL
  under the law and would refuse.
* **P2 — THE AVOIDING WINDOW**: the crescent's north coast holds >= 1 steered window
  with headland >= 6 whose drop touches ZERO patch cells (candidate: the west half of
  the current run, donor x 1088-1104). FALSIFIED IF the scanner finds none on the
  crescent at any depth >= 6.
* **P3 — THE SEAM VERDICT**: a redeploy under the law (avoiding window, or whole-
  consumption if P1 surprises) shows the owner zero grass seams — every visible grass
  tile is verbatim stock in its stock context. This is the study's in-game gate.
* **P4 — NO REGRESSION**: grass-lane (topo-0) morphs and the golden builds stay
  byte-identical; the wobbly-boundary and containment refusals keep firing (the law
  composes with, never replaces, rounds 4-5's gates).

## SCORES (built + deployed the same session)

* **P1 — SURPRISE, in our favor.** The cut component is NOT the big southern patch:
  it is a separate **6-cell** component (x 1104-1120, z -88..-80) reaching just 4u
  past the crease — whole consumption is IN reach. The (17,1) window stays lawful.
  One addendum the extension exposed: the enlarged hole boundary landed on WOBBLY
  stock rows (1.26u past z=-88) — solved by **THE WOBBLE-ESCAPE LADDER**: the
  wobbly refusal now carries its offending edge, and the fill loop consumes the
  OWNER tile and retries (patch-whole re-runs each hop; measured convergence: 5
  hops / 6 extra tris). Bounded at 16 hops, refusal past that.
* **P2 — NOT NEEDED** (P1's lane landed); unscored.
* **P3 — DEPLOYED, awaiting the owner.** The rebuilt crescent fill emits ZERO
  patch-family tris (111 novel tris live, audited); no kept patch tri shares an
  edge with the fill (THE SEAM INVARIANT, now a test). The 6-cell north component
  is honestly gone; the big southern patch is untouched stock.
* **P4 — CONFIRMED**: 61 coastmorph + 215 world domain tests green; grass lane and
  goldens byte-identical; the comma still refuses honestly (now via PATCH-WHOLE:
  its brush component reaches the rect frame at every probed anchor/scope —
  registered residual). Mutations: 3/3 killed (families emptied / ladder disabled /
  extension removed), on top of rounds 4-5's 8.

## ROUND 7 RESCORE — CONSUMPTION OWNER-REFUSED, THE LAW IS AVOIDANCE

The whole-consumption build survived exactly one deploy: the wobble-escape ladder
bit the rim of the crescent's VISIBLE authored meadow (the "6-cell component" WAS
the green feature filling the owner's screenshots), patch-whole legally consumed
it, and the island degraded to scattered 1-edge singles ("now it's just 1-edged
grass Wang all around"). **THE PATCH-AVOIDANCE LAW** replaces it: a structural
drop touching ANY patch-family tri refuses; the ladder consumes modal-family
tiles only. Consumption of authored features is form damage — the same reason
the plug was refused; eating is not seaming.

Consequence, measured (full scanner sweep of the 4x2 region, every window x
depths 8/6): **the bent crescent has ZERO lawful deep windows** under the full
law stack — every run hits the meadow, its wobbly flank, wall-harvest scarcity,
or deep wobble. The deployed instance is REVERTED to the pure excise carry
(meadow restored byte-exact). The capability's honest state: deep tiled-mains
morphs are open on masses whose coasts are patch-free and near-grid; the
WOBBLY-CELL FILL is the registered reopener for the rest.

## Non-goals (recorded so they stay dead)

* Decoding the patch edge tiles into a generative coding — killed by the census
  (soft context) + the terrace-wall precedent.
* Translating/reshaping a patch to fit new terrain — real content through a
  synthetic frame is still synthesis (the v3 bend-carry lesson).
