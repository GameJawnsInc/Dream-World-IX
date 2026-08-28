# The Shoulder Heuristics — how stock makes shallow rock read right (no rotation)

> 2026-08-28. Six-agent workflow over ALL 260 stock disc-1 land blocks (83,939 tris): five parallel
> census agents + one adversarial verifier that independently re-derived the 14 load-bearing claims
> from raw bytes (12 CONFIRMED, 2 REFUTED — both refutations recorded below; the refuted numbers are
> stricken from use). Full agent outputs: the session workflow journal (run wf_1056c3f6-aef).
> Question: the R4 horseshoe's SW arc shows a 16–24° topo-49 shoulder (chart rows 10-11 cols 6-9)
> rising bare from a flat lawn; six fix takes failed. What does STOCK do with this element class?

## The verified heuristics

**H1 — The paint was never wrong.** The shoulder's tiles (r10 c6-9) are stock's **#1
rock-foot-at-grass tile set: 44.8% of all 2,505 rock-foot-at-grass tris** (rank order (10,9)/(10,8)/
(10,6)/(10,7), then a gap). Reproduced to the decimal. The band is *not* steep-biased (the census's
5.49× steep-bias claim REFUTED: direct measure gives shallow 10.6% vs steep 8.3% — mildly the other
way). Every paint-side fix idea (re-chart to pale rows, "wall conversion") was aimed at a non-defect.

**H2 — The slope-in-isolation is the defect, precisely.** Rock-49 meeting grass runs
**p05 = 32.1°, p50 = 49.6°**; a 16–24° rock face at a grass contact is a **1-in-130 event** (0.68%).
The donor's own home blocks: min 35.9°, p50 52.8° at the grass contact — even at Daguerreo the
shallow band never *meets grass* at 16–24° (forest and bench structure intervene).

**H3 — The shape law: shallow rock is a BENCH or a TOE, never a free ramp.** 14 of 15 stock shallow
stretches are benched, 1 convex, **0 ramps**. Every 16–24°-at-grass instance in stock (the verifier
found 3, on the mod's exact tiles) is the **bottom toe course of a 24–37u massif at p50 45–53°** —
one course of shallow, steep body directly above. An 11u-tall shallow run is off-language regardless
of paint.

**H4 — The flat lawn was never the problem.** Stock parks rock on billiard-flat ground routinely:
**52% of foot chains have a ≥20u run under 1.0u relief spread** (75% under 1.5u); the flattest is
Alexandria's plaza, block (20,10) — 23u at **exactly 0.000u** spread, y = 26.07 constant, cliffs
rising straight out of it. Stock's idiom is *flat lawn → abrupt steep rock*. Every apron/rolling-
ground take was solving a non-problem (median foot relief is LOWER than open-grass median).

**H5 — At scale, the mossy band is never bare.** All stock patches of the band taller than one
course are steep (41–50°), forest-touching (0–2.8u), and occluded. The one-course use (n=159,
median rise 0.25u) is the ground-fringe idiom; 94.6% of band tris orient fringe-down (high-v edge at
the lower vert).

**H6 — Wall companions: bare is the default, forest is the dressing, and forests WELD.**
81.8% of stock wall-foot stations have no companion; forest is the top dressing (~10%, 2× scrub);
shallow feet are dressed ~2× more often than steep. **30 of 44 disc-1 forest blobs sit at gap 0.0 —
literally sharing verts with the rock** — not planted in front. The Daguerreo islet: 89 tris,
31×32u, welded. 73% of stock blobs are ≥25u diagonal — our ~28u arc is a normal blob size.

**H7 — The topo-38/scrub re-class is dead.** Topo-38 touches grass **0 times in 3,119 tris**
(attacked three ways: edge, shared-vertex, nearest-centroid min 21u — unbreakable). It is a desert
hillside with brown paint (rows 17-19 c7-8); scrub never fronts walls (0.2% of boundary edges).

**H8 — At 16–24° beside grass, stock's material is GRASS ITSELF.** Material share adjacent to grass:
15–20° → grass 94.2%; 20–25° → grass 89.8%; 25–30° → grass 72.3% / rock 24.3%; 30–40° → rock 83.2%.
Stock has 449 contiguous grass runs ≥15°; the largest — blocks (16,15)/(17,15), n=69, **p50 18.5°
rising 5.28u — is geometrically the mod's exact case**, shipped as walkable grass.

## The fix space these heuristics license (no rotation)

Ranked by precedent strength; all keep the massif's placement and presentation.

1. **THE GRASS SHOULDER (H8+H2+H3+H1)** — re-class the arc's shallow band (16–24°, ~y 4–12) as
   walkable GRASS (positional mains paint + topo 0), moving the fringe + dark foot-course contact
   line UP to where the face first sustains ~36° (stock's p05 at a grass contact). Grammar becomes:
   flat lawn → rolling grass shoulder (real, walkable, stock-instanced) → fringe → dark toe course →
   steep mossy/pale wall. Geometry untouched (UV+idall re-tile of carried tris only — the paint-class
   change lane, offline-eye-provable); the H1 tiles stay exactly where stock uses them (the ≥36°
   contact). Consequences: the shoulder becomes climbable (stock-normal for grass), area stamp covers
   the new grass (area 14).
2. **THE WELDED FOREST (H5+H6)** — carry a forest blob welded (gap 0.0, the stock idiom) over/against
   the shoulder — the donor's own home solution, the Daguerreo islet's size class matches the arc,
   and R6 already budgets three forests. Composable with 1 (Daguerreo composes both).
3. **Nothing else.** Steepening (take 6) is refuted by H4+form; paint conversion by H1; topo-38 by
   H7; ground-shaping (all apron takes) by H4.

## Falsification ledger for this arc (takes 0–6, all owner-rejected)

apron bulge (t0/t1) and broad bank (t4): solved the non-problem H4 · conform shelf (t3): created a
walkable flat rock shelf (H3 violation) · UV strip: paint on flat ground (H3) · foot course alone
(t5): one course can't fix an 11u shallow run (H3) · face steepen (t6): form destruction, the
rock-rigid law's own domain. The heuristics above explain every verdict after the fact.

## ADDENDUM — THE ARC WAS NEVER SHALLOW (the instrument correction, same day)

Per-tri measurement of the deployed arc window (all families, 2u height bands): grass lawn (3 deg)
-> rock49 at p50 45-59 deg CONTINUOUSLY from y 3 to 14 -> the flat bowl terrace at 15. Zero rock
tris under 33 deg. Every "16-24 deg shoulder" figure in this file's framing (and takes 4-6's
premises) came from ONE instrument error: rise over RADIAL run across a curving arc — a steep wall
meandering +-5u in radius reads as a shallow chord. The census's per-tri STOCK numbers (H1, H2, the
verifier's re-derivations) are unaffected and stand; the census's own "stretch" slopes are composite
chords of BENCHED profiles and must never be read as face angles. THE LAW: measure a face's angle
from its triangles, never from ring-radius chords.

## ADDENDUM 2 — THE PROFILE LAW (the owner's take-7 correction, measured)

The owner, closing the arc: the offline render matches in-game — the instrument gap was judging a
3D shape from one view, and authoring the base from the GROUND side ("you made the flat ground into
rock walls") instead of continuing the mountain's own slope. Stock mountains climb in a specific
range; the takes did not. `envelope_profile.py` (study dir) measures it: from each rock-grass
contact march horizontally uphill; **A1** = envelope angle over 0–8u, **A2** over 8–16u, **kink**
= A1−A2. **STOCK (n=926 feet): A1 p25–p75 = 42.3–52.7°, floor p05 = 33.1°, kink centered +1.5°**
— the base course continues (or slightly steepens, convex-toe) the face above; a splayed skirt or
a wall-over-flat are both extreme-tail events. The R4 massif's owner-passed faces measure
IDENTICAL to Daguerreo home (A1 p50 49.0 vs 49.5); the failed SW window was the massif's only
out-of-law zone, in both tails at once (mid-arc 21–36° skirts under a 38–42° face, kink −20..−11;
window-edge 52–56° walls over 13° flat body, kink +36..+43). THE LAW: author a foot by EXTENDING
the local face plane to the lawn (A1 in the face's own band, |kink| within stock's −6..+18); where
the body above is flat, build no wall — retreat the contact. Per-tri angles cannot see any of
this: the window's triangles individually matched stock's distribution in every take.

What is actually off on the arc vs the owner-passed north face: (a) the apron's 1.1-1.9u grass
bulge at the foot (the original knoll verdict's subject; H4+H6 say stock stands steep rock BARE on
flat lawn); (b) THE DOUBLED FRINGE — the arc's chart carries foot/fringe rows (10-11) at the lawn
contact AND again mid-face (the owner's "mid-cliff ground-to-cliff transition tile"), where the
north face runs one fringe course then the pale ascending ladder. The heuristics-licensed build:
kill the apron in the window (the take-5 flat-window mechanism, without the ground rock course) +
re-align the chart so fringe rows appear only at real contacts (the ladder law), pale courses
between. Takes 4-6 are falsified at the premise level; the steepen lever carries a falsification
note in its own right.
