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

## FINDINGS (2026-08-02) — predictions scored, menu in `DESIGN-MENU.md`

**S-1 CONFIRMED, and sharpened.** Capes + bays are 150 of 187 instances; stock-plausible
means a ragged margin at the 16–40u scale. But the per-class dig found the striking unit
is often the *arrangement* rather than any instance — the archipelago's anchor-plus-
fraying-tail is a composition, not an object.

**S-2 CONFIRMED and strengthened.** One neck per 3,678u of coastline against one cape per
368u; the whole class is 0.22% of the world's land area. A walkable land bridge is a
deliberate departure from stock language.

**S-3 CONFIRMED.** The top two designs author zero triangles; the only design that mints
surface ranks third and is explicitly the capability demo, not the opener.

**S-4 CONFIRMED.** Four of six classes came back `buildable-with-work`; the strait is
effectively blocked by six lines in `fuse.py`.

### A FOURTH DETECTOR FAULT — the lagoon class does not exist in stock FF9

The three faults fixed above were mine. This one survived into the published counts and
was caught by the per-class dig: of 6,384u² of fully sealed "water" in disc 1, **46% is a
dedicated river/stream/falls mesh, 39% is a town or dungeon object model plugging a hole
in the terrain, 11% is the Fire Shrine's lava crater, and exactly 32u² — one 4u cell — is
actual enclosed sea.**

Independently corroborated here: the probe's second-largest "lagoon" (448u², block (7,1))
is **Gulug's volcano crater**, which `studies/overworld-topography/`'s own part inventory
records as `volcanocrater`/`volcanolava` at (7,1)/(8,1).

The lagoon detector was measuring *holes in the terrain mask*, not enclosed water. The
mask cannot tell sealed sea from a crater or a building footprint, because Terrain is
absent under all three. **Stock FF9 has no lagoons; a Path D lagoon would be the first
one in the game.** That is a legitimate design choice but it is not a stock-plausible one,
and the census as first published implied the opposite.

### The structural finding that outranks the menu

**There is no post-deploy coast editing on Path D**, verified in source rather than taken
on report:

* `cli.py:3773` — `cliff morphs are single-cell v1 -- drop --size`, so no morph verb
  reaches a multi-block carry at all.
* `transplant.morph_in_place` → `world_tris` → `extract.read_block(disc=…)`, which reads
  the **stock install bundles**, and only discs 1 and 4 exist. It cannot see deployed
  disc-9 overrides.

So a multi-block carry into Path D is **frozen verbatim forever**, and the coast-control
verbs reach exactly one carryable block. "More control over the coast" is, today, control
over a single 800u² block.

### The carryable pool is 7 mass-sets out of 57 landmasses

The disqualifier is almost always a *neighbouring* mass crossing the donor rect frame,
not the target island — Daguerreo, the waisted isthmus island and the sinuous island are
all unliftable for that reason alone. Hence the named top capability gap: a **donor-rect
excise** (drop a cropped foreign mass and re-zip sea4 over its footprint), whose patch
lands on sea4 — the one surface in this arc that cannot mint a walk trap.

### Verified independently before relaying

The recommended carry — `(9,5)+2x3 → cell (10,12)` — was re-run here from scratch:
`wang-carry incoherent=0`, `sea-plan A/B/C all ok, C_overlap=0`, `census miss=2
inherited=2 introduced=0`, **gates CLEAN**. It is the cleanest carry measured, cleaner
than the owner-accepted bench donor (which warns 16 seams and 0.22 sea overlap).

### Stop rule honoured

The round ends with a ranked menu and one recommendation. **Nothing has been deployed.**
