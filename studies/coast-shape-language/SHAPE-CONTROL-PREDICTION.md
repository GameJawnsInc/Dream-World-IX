# SHAPE CONTROL — three studies, registered 2026-08-04 before running

## Where the arc stands

The design menu's "cannot do yet" list (DESIGN-MENU.md §"What this vocabulary says we
cannot do") named four gaps. Since then: **excise is built** (v1–v3, isthmus + crescent
in game) and **the cliff verbs are region-capable** (#17 — verified at cli.py:4262: only
the beach verbs still refuse `--size`, by name). Two named blockers remain, plus one
measurement nobody has run now that the tools changed.

Shape control today = pick a palette silhouette (8 masses) × 4 rotations × excise. The
three studies below add: *bending* a silhouette (1), *composing* silhouettes at stock
spacing (2), and *the strait class* (3).

## Study 1 — THE MORPH ENVELOPE (measurement only, nothing deployed)

With region-capable cliff verbs, every palette mass has a morph surface for the first
time — the menu's scan predates #17 and found windows on exactly one block. Chart it:
for each palette mass, enumerate windows (`world-morphs`), then ladder each region verb
(bump / headland / bay / lobes) to its refusal depth, recording the failing gate.

* **M-1** Every palette mass admits ≥1 cliff window (the old scan's "one block only" was
  the single-cell guard, not geology). FALSIFIED IF a mass has none.
* **M-2** The refusal depth varies by mass and window (a real envelope, not a constant):
  the (7,17) ceiling measured headland-14 / lobes 8,-6,8; other masses will differ both
  ways. FALSIFIED IF every window tops out at the same figure.
* **M-3** ≥1 morph on ≥6 of 8 masses gates fully CLEAN at depth ≥6 — i.e. the palette is
  broadly bendable, not just carryable.

Deliverable: `MORPH-ENVELOPE.md` — the per-mass shape-dial table.

## Study 2 — THE CLUSTER SHIFT (the shift lock) — ★ BUILT + SCORED 2026-08-04

**S-1 CONFIRMED.** The dots (10,17) rot-180 shifted +20E and (10,18) shifted −24W
into adjacent Path D disc-9 cells both gate CLEAN through the full dry-run (census
introduced 0, weld pairs 0) at a composed land gap of **5.4u** — inside stock's
4–20u cluster regime, against the old ~49.8u floor. The trailing vacancy is minted
as stock-shaped sea4 (`lattice_patch`, THE LATTICE LAW) in PRE-shift coordinates,
welded to the sheet's own frame verts, so the standard shift+partition welds it
like any carried tri.

**S-2 CONFIRMED.** The widening applies ONLY to explicit shifts — the auto path
never cluster-widens (pinned hermetically) — and all 119 pre-existing transplant
tests including the region/transplant byte-identity law stay green.

**S-3 CONFIRMED, five named refusals:** land within the margin of the leading
frame; a data-backed trailing side (the ±8u strip window governs there — its clip
edge is not lattice-shaped, so minting behind it is a registered residual, not
v1); a tongued trailing side (tested live on the crescent's S tongue); a diagonal
shift (one axis at a time — the corner band has no fill lane); off-lattice
(mod-4, pre-existing). 4/4 mutations killed.

**Registered residuals:** the data-backed trailing side (fill beyond a gathered
strip needs a strip-edge-welded mint); the diagonal corner band; rot of the
minted band's quadrant hash keys on pre-shift region coords (lawful — the sea4
quadrant choice is measured-free — but a re-mint at the same world cell hashes
differently than an excise fill would).

**★ DEPLOYED for playtest 2026-08-04**: the pair live at Disc9 blocks
(19,0)/(20,0) in `FF9CustomMap-world` via `fuse_layout` (11 override files, fused
border 0 bad / 0 grade jumps, no wang advisories). A = (10,17) rot-180 shift
+20E, B = (10,18) shift −24W; the 5.4u channel runs along the shared frame
x=1280, z ≈ −10..−45. Revert = delete the Block[19][0]/Block[20][0] files.
⏳ awaiting the owner's verdict.

`transplant_region` pins shift to 0 when no tongue opens a window (`avail =
strips_with_data & windowed`), so two carried masses can never sit closer than their
rects allow — measured floor 49.8u against stock's cluster regime of **4–20u** gaps. The
menu's ask: on a donor whose land reaches no border, allow shift up to
`clearance − land_margin` — coverage is not at risk because the vacated band is open
water on both sides.

* **S-1** With the window widened, two palette dots can be placed at a measured mask gap
  inside 4–20u, and the composed pair gates CLEAN (census introduced=0, weld 0).
* **S-2** No regression: every existing carry's shift window is unchanged when a tongue
  exists (the widening applies only to tongue-less sides backed by open donor water).
* **S-3** Fail-closed: a shift that would push land within `land_margin` of the frame
  still refuses via land-fit.

## Study 3 — THE STRAIT UNLOCK (fuse off-lattice tolerance) — ★ BUILT + SCORED 2026-08-04

**F-1 FALSIFIED — and the falsification is the finding.** The predicate is built
exactly as scoped (`_side_row`: an off-lattice vert on a PURE open-water row →
`water-offlat`, lawful against water/prefab) and it clears the off-lattice sea3
rows — but the Iron Gate still refuses, 6 bad rows → 4. Measured on the reef's
channel frame: rows carrying `sea1` (3 off-lattice + 1 on-lattice) — the reef
brings its LIVE SHORE WASH to the frame, and the menu's "blocked by six lines of
fuse.py" had lumped that under "off-lattice". No fuse predicate can lawfully clear
it: sea1 is shore-bound copy-only — refusing it is the fuse law's founding case.
**The strait class at stock width needs a shore-ladder termination on the channel
frame (the rim-retile family lane), not a fuse predicate** — registered as the
follow-up.

**F-2 CONFIRMED** — all pre-existing fuse verdicts unchanged (6 tests green; the
predicate only turns off-lattice→water-offlat on pure-water rows, a strict
widening).

**F-3 CONFIRMED** — an off-lattice vert on a sea1 row keeps the hard refusal
(hermetic test + demonstrated live by the Iron Gate itself). 2/2 mutations killed
(predicate dead / predicate ignoring parts).

The Iron Gate (stock strait #7 rebuilt: comma + reef at 36.2u) fails ONE fuse row class:
`off-lattice` verts on the reef's original N frame. The menu scoped the fix as one
predicate in `fuse.py _side_row`: tolerate an off-lattice vert when **both** sides
classify as open water (a water vert off the lattice cannot tear land).

* **F-1** With the predicate, the Iron Gate layout (`layout_iron_gate.toml`) gates CLEAN
  at its 36.2u gap.
* **F-2** No regression: every fuse verdict on the existing Path D layouts is unchanged
  (the Southern Ring and Fraying Tail fuse planes carry no off-lattice water rows — if
  they do, the verdict may only change FAIL→ok, never ok→FAIL, since the predicate only
  widens acceptance).
* **F-3** Fail-closed: an off-lattice vert on a row where EITHER side has land/beach/
  shallow content still fails.

## Order and stop rule

1 first (pure measurement, calibrates 2 and 3's worth), then 2, then 3. Each study is
offline-complete: gates green + the registered predictions scored. Deploys are separate
owner-chosen builds — the deliverable is capability, not landmasses (the owner's own
framing: "improving our ability to choose/alter/implement all the different land
styles"). One deploy per playtest when we get there.
