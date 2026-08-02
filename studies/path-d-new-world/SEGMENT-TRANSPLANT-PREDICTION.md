# THE VERBATIM COAST-SEGMENT TRANSPLANT (study angle 2) — the V-corner by carry

> Registered BEFORE building, 2026-08-02. Parent: VSHORE-SEAL-PREDICTION.md
> "STUDY ANGLES" §2. The first construction round gated by THE RENDER GATE
> (RENDER-GATE.md — calibrated same day). The read-first gates honored:
> `authoring-ff9-overworld` + the coast-mosaic LAW INDEX.

## The claim

Every look SUCCESS on this bench was a carry; both fairing rounds FAILED at
look because they synthesized surface from vocabulary constants. The fix
class: cut a REAL rocky-lip shore segment (crest+wall+foot, geometry AND uv,
by original vertex index) from a stock coast whose along-shore turn matches
the proven 138° fairing arc, and weld it between the kept columns at v5/v11.
The carried segment supplies the look; the bench supplies the frame.

## The target (banked from the fillet rounds)

Kept-boundary joints: **v5 (376.29,−509.40)** entry tangent 159.6° and
**v11 (380.08,−516.73)** exit tangent 202.5° (the proven exact-fan heading).
Concave turn ≈ +43°, chord ≈ 8.25u, arc ≈ 9–11u. Bench wall at the joints:
crest y ≈ 3.2, base ≈ 0 (coastal free base), v pins 0.8926/0.9229, u band
[0.699, 0.947] — STOCK'S OWN vocabulary, so a stock segment is native here.

## The operators (the laws each obeys)

1. **SEGMENT CENSUS** — walkable-boundary chains over a stock donor pool
   (the proven coastal donors + neighbours), per-vertex tangents; a window
   qualifies iff: cumulative turn ∈ [35°, 52°] same-signed (no counter-turn
   > 10°), no single-vertex turn > 67.5° (THE QUANTIZED-FAN LAW — the carried
   boundary must itself be hug-clean), chord ∈ [7.5, 11]u, wall height
   ∈ [2.4, 4.0]u (small |Δh| keeps the height adaptation lawful), coastal
   free base (min wall y ≤ 0.5).
2. **SEGMENT CUT** — whole wall faces between the two END crest verts (cuts
   land ON column boundaries by construction — nothing is split); carried by
   ORIGINAL INDEX (never position-merged); degenerate filter by TRUE 3D area
   (THE WALL LAW).
3. **RIGID SEAT** — rotation+translation only (det=+1, winding preserved);
   endpoint crest verts SNAP to v5/v11 exactly; per-column crest-y conform to
   the bench lip line + THE PER-COLUMN LIP ANCHOR v-crop where the base
   height differs. u-TRANSLATE the whole wall band (mod the sawtooth wrap) so
   the entry column CONTINUES the kept v5 face's u — one wrap-class jump max,
   at the v11 joint (stock wraps are in-language).
4. **THE NOTCH DROP + LAWN ZIP** — the old notch wall faces (v5..v11) DROP
   (no buried blocked sheet — the ring-trap class dies at the root, not by
   sweep); the cavity caps with the v2-proven world-frame edge-donor lawn zip
   (per PRE-CLIP tri, donors across the inner edge from the kept lawn).
5. **SEA CONFORM** — the corner Sea4 stays the (already playtest-proven) cut;
   re-run the hidden-cut predicate over the NEW footprint and extend the cut
   only if the segment's foot demands it.

## Predictions

- **P-A (census)**: the stock coast HAS this segment — ≥3 qualifying windows
  across the pool. FALSIFIED IF zero: then the 43°/8u concave arc at ~3.2u
  height is off stock's shore grammar and the transplant reduces to angle 6
  (offset-loop) — record and stop, don't force.
- **P-B (mechanics preserved)**: the carried boundary passes the hug gates
  0-stall both directions (its turn profile already satisfies the fan law by
  census construction).
- **P-C (the look)**: THE RENDER GATE shows the segment's wall in coherent
  rock with a continuous LIP through both joints, no fins/voids/off-band
  texels/white slivers, and the diff-vs-baseline confined to the footprint —
  the four committed cameras all clean. This is the claim the two synthesis
  rounds failed; if a carried segment ALSO fails here, the defect is in the
  weld/zip operators, not the surface, and the render localizes which.
- **P-D (gates)**: weld audit 0 near-miss pairs; contract clean; latent sweep
  0 bench-wide; coverage lost=0; statics identical outside the bbox; boat
  coast-nav unchanged.
- **P-E (owner)**: in-game — the corner reads as ordinary rocky coast
  (no seam-line, no wrong tile, no void), Zidane slides through the corner
  both directions without catching, the boat behaves as before.

## Gates (all green BEFORE any deploy; deploy is one reversible change)

g1 weld audit · g2 unindexed contract (write_ff9mesh asserts) · g3 winding
(zero down-facing lawn, wall normals seaward — plus the game-eye render)
· g4 hug 0-stall both directions · g5 latent 0 · g6 coverage/statics · g7
boat nav · **g8 THE RENDER GATE (4 cameras + footprint-confined diff)**.

## BUILD LEDGER (2026-08-02) — ALL 8 GATES GREEN, DEPLOYED

**Census** (`vcorner_transplant.py census`, 260 real disc-1 blocks): P-A holds
at every tightening. Three laws were MINTED by failed seats along the way:

1. **THE FLOW CONSTRAINT** (seat 1, (4,13)): matching cum-turn+chord is not
   enough — after chord-seating, EVERY segment heading must be ≥135° or a hug
   hold exceeds the 67.5° fan bound. A symmetric arc centered on the chord
   can never satisfy the bench's asymmetric tangent placement; the fairing's
   138° chord was exactly this constraint + 3° margin. Census-enforced.
2. **THE GRASS-FAMILY DISCRIMINANT** (seat 2, (5,13)): "topo-58 + v≈0.87-0.93"
   admits the HIGHLAND-DIRT strip (v 0.872/0.902, u 0.428-0.676). The lip-row
   vocabulary discriminates: grass-top = v pins 0.8926/0.9229 + u [0.699,
   0.947]. Census-enforced; 5 grass windows survive map-wide.
3. **THE LEAN FACT + THE WALK MEMBRANE** (seats on all 5 candidates): stock's
   grass-family lip walls ALL overhang (seaward-wound ny ∈ [-0.37,-0.15] —
   the rock lip curls over the water; the bench generator's back-lean was OUR
   deviation). Seaward winding alone goes walk-invisible, and over the CUT
   sea the fan total-MISSes → the hug catches. Resolution BY THE SEPARABILITY
   LAW (navigation ≠ render): emit the verbatim seaward render face + a
   coplanar reversed WALK MEMBRANE (ny > 0.1, topo 58, occluded in-game).

**Seated donor**: **(5,14) chain1 v0..v2** — turn +39.3, chord 8.08 (plan
scale 1.0218), h med 3.31 (y 0.967), u/v verbatim (the window carries its own
column-boundary sawtooth wrap; joint phase jumps ~0.013 read as nothing).

**Build lessons banked** (each caught by a gate, none reached the install):
- **Exact-bytes INNER**: the hand-copied 2-decimal INNER seeded 0.004u
  near-miss cracks at every joint — re-captured from the baseline bytes
  (THE NEVER-HAND-TYPE-GEOMETRY law, enforced by the weld audit).
- **The width filter**: crest-key-subset selection — a face sharing only an
  END crest vert belongs to the NEIGHBOUR column, not the window.
- **Strict-interior drop**: with exact coords, vertex-inclusive strip tests
  fire on kept faces whose corner IS a joint vertex (v5's kept wall face was
  dropped → a wall hole → a hug catch 1u before the joint).
- **Ear-clip strip cover**: the two-chain zip overlaps/holes against the
  folded INNER (the notch turnaround); ear-clipping the simple strip polygon
  covers exactly.
- **THE PAINTED-BAND END + THE ATLAS-VALIDATED TRANSLATE-CLONE**: the local
  lawn map is phase-consistent but its painted atlas band ENDS at the old
  boundary — five kept tiles unanimously extrapolate the strip point to
  (0.13,0.80) = WHITE paint. No distance-based donor pick can fix it (three
  identical renders proved it). The lawful op: shift the evaluation point by
  whole 4u lattice steps (mains periodicity) and validate the candidate's
  FULL TEXEL FOOTPRINT against the atlas (point samples miss sliver whites);
  3 of 6 ears took a (0,-1) shift. This is study angle 4 working as a build
  primitive.

**Gates**: g1 weld 0 · g2 contract · g3 winding unanimous · g4 hug 0-stall
both directions + control · g5 latent 0 bench-wide · g6 coverage lost=0 /
statics 0 outside bbox · g7 boat 0 new-legal · **g8 THE RENDER GATE: all four
committed cameras CLEAN (continuous rock through both joints, lip unbroken,
zero fins/voids/off-band/white), diffs footprint-confined.** The instrument
caught FIVE broken intermediate builds this round (sky-wall, zip holes, the
white sliver twice, the over-drop) — every one before the install was touched.

**DEPLOYED** backups `.20260802-042455`; revert:
`revert_vcorner_transplant.py`. Post-deploy live re-gate green (hug PASS,
own-ring-0 = 0, 0 hard-trapped). P-E (owner): the corner reads as ordinary
rocky coast; slide-through both directions; then the standing P-H checks.
