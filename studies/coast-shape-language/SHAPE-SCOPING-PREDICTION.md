# The outline census — scoping round (registered 2026-08-02, before the design verdict)

## Why this lane exists

The V-shore corner closed rung 5: the coast is measured clean island-wide and the tuck
vocabulary is proven in playtest. The owner's next ask is not another defect hunt but a
capability question — *"what kinds of interesting island shapes can we do now that we
have more control over the coast?"*, keeping structures stock-plausible.

That is a **scoping** round, and its failure mode is different from a build round's.
A build round fails by shipping a defect. A scoping round fails by producing a
confident menu of shapes that stock does not actually contain, or that the toolkit
cannot actually build — i.e. by **not measuring the thing it claims to describe.**

So this round measures first, and every claim below is meant to be checkable against
`out/shapes_d1.json`.

## What was built

| file | what it does |
|---|---|
| `shape_census.py` | reads the user's install, emits per-4u-cell `land` / `foot` masks, height, topograph; connected landmasses with shape metrics |
| `shape_probe.py` | locates six outline classes — lagoon, bay, cape, isthmus, strait, chain — by morphology on the mask |
| `outline_render.py` | renders the mask, whole-world or cropped to one landmass |

Nothing here writes to the game or a mod folder; the whole study is read-only.

## THE TWO-MASK DISTINCTION (a modelling error caught in the first run)

The first cut built only the **foot** mask (foot-legal topographs) and reported 102
"landmasses" with circularity as low as 0.016. That is not a coastline measurement at
all: mountain rock (topo 49) is foot-illegal and covers 164 of disc 1's 260 blocks, so
the foot mask **fragments every continent along its mountain ranges**. It measures the
walkable partition, not the outline.

Corrected, the census carries both:

* `land` — any Terrain tri present. The outline; what reads as land from offshore.
* `foot` — foot-legal only. Where a player can stand.

**Measured: 28.6% of the world is land, 18.5% is standable — 35% of all land is
un-standable cliff and mountain.** The design consequence is direct and is the reason
both masks are kept: *a cape you cannot walk out onto is scenery, not a destination*,
and stock builds a great deal of exactly that.

## THREE DETECTOR FAULTS, FOUND AND FIXED BEFORE ANY CONCLUSION

Registered explicitly because the arc's most expensive recurring error is trusting an
uncalibrated instrument, and this round reproduced it three more times:

1. **Cape reach ran outside the cape's own landmass.** One global distance transform to
   the opened core meant an islet with no core of its own measured its distance to
   *another continent* — the top-left islet scored a 357u "cape", longer than any real
   headland in FF9. Fixed: reach is measured to the core of the same mass, and a mass
   the opening erases entirely is an islet, not a cape. 109 → 80 instances, max reach
   357u → 106u.
2. **The strait detector found coastal water, not straits.** "Sea within r of any land"
   is a band around every shore in the world; it returned three ~100k-u² "straits" that
   were one coastal ring, passing the separates-two-masses test trivially. Fixed:
   a strait is the *gap between two masses*, measured on the land-label Voronoi, and
   both shores must be substantial. 3 → 11 instances, narrowest 16u.
3. **The isthmus detector reported only each mass's thinnest neck** (it broke out of the
   width loop on the first hit), so every isthmus in the world came back as exactly 8.0u
   wide; and with no substantiality filter, "cuts" that merely shaved a pebble off a
   coast counted. Fixed: all widths, and both sides of the cut must survive.
   20 → 338 → **8** instances.

Every one of these would have produced a confident, wrong design menu.

## Measured vocabulary (disc 1)

| class | instances | range |
|---|---|---|
| bay / gulf / cove | 70 | depth to 27u |
| cape / peninsula / spit | 80 | reach to 106u, slenderness 2.3–3.3 |
| lagoon / enclosed water | 14 | all small, ≤ 528u² |
| strait / narrows | 11 | 16u to ~70u wide |
| **isthmus / land bridge** | **8** | 8–24u wide, several with `walkable_frac` 0.0 |
| archipelago chain | 4 | biggest 16 islands, block (5,15) |

Landmasses: 57 components, 31 of ≥16 cells, of which 4 are continent-scale.

## Predictions (registered before the design round returns)

* **S-1** The vocabulary is **lobe-and-inlet dominated**: bays and capes together
  outnumber every other class by an order of magnitude (150 of 187 instances), so
  "stock-plausible" mostly means *a ragged margin at the 16–40u scale*, not dramatic
  set-piece geography. FALSIFIED IF the characterization finds the striking instances
  are predominantly straits/isthmuses/lagoons.
* **S-2** The **isthmus is genuinely rare in stock FF9** (8 in the world, several not
  even walkable) — so a walkable land bridge is *off-language* however appealing it
  sounds, and proposing one is a deliberate departure, not a stock-plausible move.
  FALSIFIED IF the per-class dig finds many isthmuses the morphology missed.
* **S-3** The cheap striking designs will be **compositional, not novel**: combinations
  of carried stock coast (bay + cape + chain) will outrank anything needing new
  authored surface, because THE DEFECT FOLLOWS THE AUTHORSHIP. FALSIFIED IF the
  buildability pass finds a mint route that is both low-effort and low-risk.
* **S-4** At least one class comes back **`blocked` or `buildable-with-work`** — the
  toolkit is not uniformly capable across the vocabulary, and naming the weakest axis
  is more valuable than the menu itself.

## Stop rule

This round ends with a **ranked design menu and one recommendation**, not a build.
Nothing gets deployed until the owner picks. If the buildability pass says every class
is already `buildable-today`, the honest report is that the toolkit is ahead of the
design question and the next work is choosing a shape, not extending capability.

---

## FINDINGS

*(scored when the design round returns)*
