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

## PLAYTEST 7 (2026-08-02) — flow CONFIRMED; "still seeing seams towards the sea"

P-E's FLOW half PASSES (owner: "walkability is good" — the first flow+trap
pass on this corner). The residual: pale slivers at the waterline where the
wall foot meets the water. **THE SEAM-FIX ROUND** (same day, all offline
iterations caught by the render gate + pixel forensics, 0 reached the
install):

1. **Root cause**: the live Sea4 carried the UNION of every historical cut
   footprint, and `terrain_cover` (ANY-terrain) had cut the sea under the
   wall band too. Stock's FREE-BASE runs water under the lip to the base;
   under the tuck's back-leaning walls the cut boundary was hidden, under the
   transplanted OVERHANGING stock lip it showed. Fix: **rebuild the corner
   Sea4 from the PRISTINE pre-cut bytes (`.020657` backups), cutting under
   WALKABLE cover only** (`treat_part` gained `src_path`/`cover` params).
2. **THE FRINGE FALSIFICATION**: "keep a 1.2u under-lip water fringe like
   stock" re-armed the trap in one gate run (hug CAUGHT, latent FAIL) — an
   exposed CROSS-mesh sheet gets ring-cached from its seaward portion and
   answers under-lawn probes filter-free. THE WALK MEMBRANE's safety decoded
   by contrast: a SAME-mesh sheet behind the lawn in buffer order can never
   enter the ring. **Sea under walkable plan is the trap, no fringe
   exception; look-closures must be Terrain-mesh geometry.**
3. **THE FOOT APRON + THE INNER CURTAIN** (the look closure): a submerged
   rock shelf from a thin +0.06 rim at the crest line sloping to −0.6 at
   1.4u inland — subdivided ≤0.6u (the sea-cut precedent: a sub-tile's
   inradius can never cover the 32-candidate fan; the un-subdivided apron
   tripped the latent sweep and was fixed BY it) — plus corner WEDGE fans
   (the per-segment offset rectangles leave a pie gap at a convex crest
   vertex; a pixel ray-cast found rays tunneling through it into the hollow
   interior) — plus a VERTICAL INNER CURTAIN floor→lawn at the apron's
   inland edge (grazing rays descend shallower than the apron dips and
   cleared its inner edge; plan-degenerate ⇒ the walk query cannot even scan
   it — walk-inert by construction; wound seaward, the first winding culled).
4. **The instrument chain that converged it**: render → sky-pixel forensic
   (100 px vs baseline 0) → exact pixel ray-cast against all staged tris →
   fix → re-render, three times, to **0 sky px** with ALL 8 gates green.

**DEPLOYED** backups `.20260802-045616` (or per revert script); revert:
`revert_vcorner_transplant.py` (regenerated). Post-deploy live re-gate green.
P-F (owner): the waterline at the corner reads solid — water meets rock, no
pale slivers from any angle; flow unchanged.

## PLAYTEST 8 (2026-08-02) — better, NOT passed: light seam + texture break

Owner (close-range top-down shot at the corner): "still have some light
seaming, what looks like some texture breaking or maybe flipped/rotated
faces." Suspects, NOT yet diagnosed: (a) the +0.06 apron RIM — a thin
constant-v (0.916) band stretched along the waterline = a smeared light line
exactly where the seam shows; (b) close-range texture-flow discontinuity at
the joints/strip (the carried faces + translate-clone lawn read fine at my
mid-range cameras but not at the owner's close oblique vantage). **The
instrument gap is the vantage**: the render gate's four committed cameras
are mid-range; every residual defect now lives below their threshold.
PARKED HERE for the study decision (recorded in the session close-out):
angle 4 (THE ATLAS MAP) + angle 6 (offset-loop curtains from the bench's OWN
tuck vocabulary — no overhang, no membrane/apron/curtain cascade) are the
recommended next arcs, plus a close-range owner-vantage camera + texture-flow
check added to the render gate BEFORE the next visual round.

## THE SEAM-FORENSICS ROUND (2026-08-02, post-playtest-8) — the carrier found

Instrument first (the playtest-8 recommendation, executed): owner_close +
graze cameras + the analytic flow check added and CALIBRATED — both
playtest-8 classes reproduce offline (RENDER-GATE.md, close-range upgrade).

**1. The measured smears are real but were NOT the visible carrier.** The
apron/fan/curtain stack scored 16 constant-uv smears + 62 stretched (6.3×) +
mirrored faces — fixed by BAND CONTINUATION: u follows each wall column's
own crest u; v folds back up the band from the foot row (below v_foot=0.9229
the atlas is white/34% alpha-0 — measured poison; the fold shows the wall's
own waterline row at the rim). All 8 gates green, deployed
(`.20260802-121757` backups). Flow: 16/62 → **0/0**. But the staged-vs-live
pixel diff was ≤220 px at every camera — the stack is nearly invisible from
the failing vantages. The defect had to live elsewhere.

**2. THE ID-BUFFER FORENSICS** (probe_seam_owner.py — the raster now emits a
per-pixel owner-triangle buffer): the light waterline pixels belong to the
**lip WALL faces themselves** (v 0.893–0.923 — the pale rock band), and the
largest owners are the bench's OWN run walls beyond the transplant
(z −517…−524, z −504…−508), not the carried window.

**3. THE FAR-COAST REFERENCE** (farcoast_nw / farcoast_nw_graze): the
island's owner-passed coast language is **rock visible ONLY from sea level;
pure green lawn-to-water from above** (convex shore tucks the wall behind
the lawn edge). The corner is the island's only CONCAVE shoreline — from
the lawn you look ACROSS the inlet at the opposite wall face frontally. No
lean class can hide a wall you view across water: the corner shows
above-water rock where the island's language never does. The baseline notch
had the same exposure (thinner); the transplant widened it.

**4. The corner walls are IN STOCK DISTRIBUTION on every texture metric**
(u-density p50 0.0151 vs stock 0.0154, p99 inside stock's; fewer uv-cut
edges than stock's own 40%). The rock is lawful; the residual is a
**PRESENTATION-CLASS mismatch**, not a texture defect. The gates could
never have caught this: they score elements against STOCK's marginals, and
the corner IS stock-lawful — the mismatch is against the ISLAND's own
established look (the ground-junction lesson restated on the look axis).

**THE OWNER FORK (playtest 9 question):**
- **(i) island language** — green-to-water at the corner too: rebuild the
  inlet walls in the bench's own tuck vocabulary / beach-class slope so no
  above-water rock shows (study angle 6 becomes the build).
- **(ii) rocky cove** — keep the stock lip and read the corner as a
  deliberate rocky inlet ("the cove exposes what the tide hides" — at graze
  the whole island already shows this rock band). Nothing further to build;
  metrics are already stock.
The instrument can render candidate (i) before any deploy; (ii) is live now.

## ANGLE-6 PRE-BUILD MEASUREMENT (probe_tuck_vocab.py) — the offset-loop premise falsified for purpose

The bench tuck vocabulary, measured at 11 stations: wall crest verts are
FLUSH-WELDED to the lawn edge everywhere (tuck offset 0.00 by construction);
bench walls back-lean (seaward ny +0.14…+0.30, crest 3.2 → foot 0.0) vs
stock's overhang (THE LEAN FACT). The island hides its walls from above NOT
by lean but by **backface culling + lawn occlusion**: from any land-side
vantage a convex shore's seaward faces point away (culled) and the lawn
occludes the down-look. Across a CONCAVE inlet the far wall's seaward face
points TOWARD the viewer — **no lean class can hide it**. Study angle 6 as
registered (offset-loop re-lean of the corner in tuck vocabulary) therefore
cannot cure the corner exposure; killed before a build round was spent.
Fork (i)'s real construction is a **beach-class ramp at the inlet mouth**
(no tall wall — e.g. the proven (7,17) ground-retile carry class), a real
design round. Fork (ii) is live now. The owner picks at playtest 9.

## PLAYTEST 9 (2026-08-02) — THE FORK IS DECIDED: rocky cove stays

Owner (in-game shot, Zidane on the north lawn looking into the inlet):
"still seeing that weird disconnected cliff piece near the water. keep the
rocky cove for this island, beaches will complicate things and require more
study. let's just master the cliff shape language + walking stuff." And:
"this was an improvement but we've still got things to learn."

DECISIONS BANKED: fork (ii) CHOSEN — the rocky cove is this island's corner
language; fork (i)/beach-class is OUT OF SCOPE for this island. The
remaining axis: make the cliff band read CONNECTED around the inlet.
Visible in the shot: the lip band runs the near shore, then breaks at a
vertical seam; the far-side rock reads as a separate slab; thin white
dashes in the water along the wall foot near the seam. Suspects (to be
id-buffered at the reproduced game-cam vantage, NOT guessed): the v11
joint (carried->kept u-phase reset + possible crest/foot line step), and
the white dashes (sea-cut edge gap / rim edge-on sliver / blank texels).
