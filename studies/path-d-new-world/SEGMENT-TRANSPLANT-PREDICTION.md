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

## THE COVE CARRY (round registration, post-playtest-9) — the whole cove, not its bottom

**THE TANGENT TRUTH (measured from baseline bytes, boundary-chain walk):**
the registration's joint tangents were NOT coast tangents — 159.6 was the
fillet-INNER direction, 202.5 the fan-quantized hug hold. Truth: kept entry
at v5 = **129.4 deg** (carried entry kink 7.8 — already stock-class); kept
exit at v11 = **231.0 deg** (carried exit kink **54.5** — THE disconnected
slab). The baseline corner was a pointed PROMONTORY (out 115, hairpin back
235), and its concave recovery (-30, -30 per-vertex) still follows v11 in
the kept coast: the live shoreline reads smooth arc -> hairpin kink ->
recovery. THE JOINT-KINK LAW verdict on census2: 0 of 5 windows can pass at
the OLD endpoints — structurally impossible (the bench chord 152.65 lies
outside the tangent range), so the JOINTS move, not the donor bending.

**The claim:** replace the span v5 -> baseline-v10 (374.964,-522.996) —
the promontory AND the recovery — with ONE stock cove-class window. A cove
inherently overshoots its chord then recovers, which is exactly what these
endpoints demand (chord 13.66u @ 185.6; entry tangent 129.4, exit 171.1).

**Census spec (cove class):** chord within 8% of 13.66u; seated entry kink
<= 12 vs 129.4; seated exit kink <= 12 vs 171.1; per-vertex |turn| <= 40
(walk fan law 67.5 stays hard); grass-lip family on all wall columns
(topo 58, v pins 0.8926/0.9229); hmed in [2.4,4.0]; coastal free base.
THE FLOW CONSTRAINT relaxes from >=135 to >=128 (the kept NW run itself
walks at 129.4 with the 202.5 hold — 135 was conservative); the hug gates
stay the oracle. Fallback exit joint: baseline-v12 (376.274,-528.455),
chord 19.06 @ 180.0, exit tangent 158.7.

**Build implications (registered before building):** the new crest crosses
the old boundary once — a CUT lobe (the promontory: old lawn/wall dropped,
pristine sea restored by the walkable-cover re-cut) and a FILL lobe (the
old bay: zip lawn, atlas-validated). Sea re-cut re-derives from PRISTINE
per the new cover; boat gate re-judges. u continuity at v5 scores softly
(no shift budget — both band margins are alpha-0 poison, measured).

**Predictions:** P-J (census): stock has >= 2 qualifying cove windows —
FALSIFIED IF zero, then the exit-side fix falls back to joint-slide-only
(exit at v10 with a shorter pure-arc window at the SAME spec minus the
overshoot demand, accepting kink up to ~20). P-K: the seated cove passes
every stage-1/2 gate. P-L: at cove_cam/owner_close/graze the band TAPERS at
both silhouettes — no full-height cut; the flow check stays 0-smear/0-
stretch. P-M (owner, playtest 10): the disconnected piece reads connected.

## THE V-CARRY — BUILT, ALL GATES GREEN, DEPLOYED (playtest 10 pending)

**Shape-language measurements that shaped the round (all committed probes):**
stock grass-lip coasts turn SHARP routinely (per-vertex p50 25.5, p90 90.0;
24.6% of vertices exceed our 54.5 junction) and put tall walls on sharp
corners freely (turn-height corr +0.05) — the magnitude was never the
defect; the JOINT KINKS at fixed wrong endpoints were. The band does NOT
tile (edge-pair diff = random-pair), and stock butt-seams its wall texture
freely (16 small mid-band jumps in one block) — the u-phase seam theory
died too. What remained was geometry: the census.

**The pick:** (4,14) chain1 v3..v8 seated E'→baseline-v12 — kinks 1.3/2.4
at the TRUE kept tangents, interior V-turn +45 (the corner drawn in stock's
own hand), every seated heading in [156.3, 201.3] (flow-clean), scales
0.965/0.914, du 0.0200. The (20,15) candidate (entry 130.9) was hug-CAUGHT
at the joint — **THE FLOW CONSTRAINT stands at 135; the 125 relaxation is
FALSIFIED** (the gate caught it in one offline run; zero playtests spent).

**Machinery minted (all in vcorner_transplant.py):**
- the figure-8 strip: the crest crosses the old chain once (CUT lobe = the
  promontory razed, FILL lobe = the bay filled); even-odd covers both.
- the mixed inland chain: drop-scar (north) + the old bay shore (south),
  corridor-restricted walk joint-to-joint.
- ear SUBDIVISION (≤2.2u): a big ear's uv footprint ALWAYS hits ground-field
  poison (5-10% interior, atlas_map.json) — subdivide until each sub-tri
  validates; global proximity weld of minted verts (cousin midpoints land
  within audit range; T-junctions are benign on the flat coplanar lawn).
- **THE TONE LAW**: footprint validation must check TONE, not just poison —
  mean-RGB within ΔRGB 30 of the donor face's OWN paint, and uv outside
  [0,1] is forbidden outright (the brown-patch + cyan-wrap classes both
  passed the white-only test).

**Verdicts:** stage-1 all green (hug BOTH directions 56-67 steps 0 stalls
across the whole new coast), latent 0, flow 0-smear/0-stretch, renders at
all six cameras + cove_cam: the disconnected slab is GONE — the coast is
one continuous sweep; the wall shows as a tapering rock nose where it faces
the camera (stock behavior) and a continuous band at graze. DEPLOYED
(backups .20260802-131811, revert_vcorner_transplant.py regenerated).
**P-M (playtest 10): the corner reads connected at the owner's vantages.**

## PLAYTEST 10 (2026-08-02) — FAILED: "more segmented and fractured; the
## cliff is at a less than 90 degree angle to the ground"

The owner's read is the measured fact: the carried wall's seaward ny is
[-0.396,-0.144] — the face tilts 8-23 deg PAST vertical (THE LEAN FACT).
**THE OVERHANG-CONTEXT LAW (minted): the stock overhang class is unusable
over a CUT sea.** In stock the overhang stands IN water to its base
(FREE-BASE) so the base context is never seen; over our walkable-cover cut
it hangs over dry void and reads as a sloped skirt — and each auxiliary the
overhang forces (coplanar walk membrane, fold-back apron, inner curtain,
weld shears, 2-tri giant facets) adds authored surface that reads as
"segmented and fractured". THE DEFECT FOLLOWS THE AUTHORSHIP, round 3.

**The round now executes STUDY ANGLE 6 in full — THE TUCK REBUILD:**
keep the V-carry's gate-proven skeleton (the crest polyline, ears, sea cut,
joint welds — walk axis owner-approved since playtest 9) and replace ONLY
the wall construction with the bench's OWN tuck vocabulary (the coast class
on every shore the owner has approved): at-or-past-vertical, walk-visible
(ny>0, no membrane), foot tucked under the lawn lip (no apron, no curtain —
the face itself closes the under-lip slot). The joints become seamless BY
CLASS (same vocabulary on both sides of each weld).

**Predictions:** P-N: the baseline kept-coast walls at both joints are
tuck-class (harvest confirms profile + uv pattern). P-O: the tuck rebuild
needs ZERO auxiliary constructions and passes all 8 gates unchanged. P-P:
at cove_cam/owner_close the corner reads like the rest of the island
(green lip from above, rock only at low vantages); at graze the band is
continuous. P-Q (playtest 11): no "segmented/fractured" read; the cliff
angle reads >= 90 deg.

## THE TUCK REBUILD — BUILT, ALL GATES GREEN + THE PEER GATE, DEPLOYED

**The vocabulary, measured off the baseline bytes (probe_bench_wall_xsec.py),
not invented:** the island's own coast wall is a ruled strip — crest FLUSH
with the lawn edge at y=3.2, foot at y=0.0 offset 0.88-0.99u SEAWARD,
mitered; seaward ny +0.26..+0.30. uv: `v = 0.8930 + (3.2-y)/3.2 * 0.0300`
(confirmed exactly against the y=2.65 -> v=0.8982 sample); `u` advances with
arc at 0.012643/u — the registered URATE, re-derived over five independent
spans — wrapping modulo the band, and a foot vert inherits its crest vert's
u. The offset formula reproduces both measured joints to 3 decimals.

**Why this kills the whole auxiliary stack — a proof, not a hope.** With the
foot SEAWARD at sea level, a ray arriving from seaward is above the wall
surface at the foot line (below it is opaque sea at y=0) and the surface
rises monotonically to the lawn: every such ray must hit wall or lawn. The
under-lip slot is sealed BY THE FACE. So: no walk membrane (ny>0.1 already —
walk-visible), no foot apron, no wedge fans, no inner curtain. **332 tris of
authored corner became 14.** THE DEFECT FOLLOWS THE AUTHORSHIP — so the
cheapest defect fix was deleting the authorship.

**One real defect found and gated, not shipped.** The first tuck build
rendered a picket-fence of vertical streaks at graze. The render gate's id
buffer named the two faces: the CUT rung was the one branch where I had
skipped the band-wrap split, so wrap() sent its ends to opposite band edges —
0.198u of atlas compressed into 3.9 world units, 4x the bench density,
reversed. Fixed by unifying the split across all quads, and **THE TEXEL-
DENSITY GATE** now asserts every face carries < 2x URATE, so the class cannot
silently return.

**THE PEER GATE (new instrument, probe_peer_compare.py).** Every gate in this
arc scored an element against stock's marginals; none asked "does this read
like what the owner already accepted?" (GROUND-JUNCTION-SYNTHESIS: 0/13).
This one renders the corner and four owner-passed shore stations from cameras
placed identically relative to the local coast tangent and compares rock-band
screen thickness + variation. Corner 211px vs peers' 60-374 (median 283);
**variation 0.32 vs the peer median 0.35 — the corner is now LESS irregular
than shore the owner has already approved.** PASS.

**Verdicts:** all 8 gates green (hug both directions 55/65, latent 0, weld 0,
coverage/sea/boat/statics PASS); flow check 0 smear / 0 stretch / **0
mirrored faces (was 176 — every one of them a membrane copy)** / 2 rotated
edges (was 27); peer gate PASS. Deployed (backups .20260802-145104).
**P-Q (playtest 11): no segmented/fractured read; the cliff no longer reads
as a sloped skirt.** If it still reads segmented, the next variable is the
CREST polyline itself (a -45 deg interior turn vs the bench's own ~30 max) —
deliberately held constant this round: one change per test.

## PLAYTEST 11 — cliff ACCEPTED; two lawn defects found, fixed, gated

Owner: "the cliff looks good now, but there's this weird meadowy texture
forming 2 triangles, and if you look close you can see a couple whitish
pixels seaming through." **THE TUCK VOCABULARY IS RATIFIED** — the wall
axis is closed. Both residuals were on the EAR LAWN, and both were visible
in my own instrument before I deployed; I shipped past them.

**Defect 1 — the meadow triangles: THE WRONG REFERENCE.** The tone gate
scored each ear against its DONOR face's paint. A donor can be perfectly
lawful and still sit in a lighter part of the ground field than the grass
the ear lands in. Measured in-render: dRGB 19-24 above the surrounding lawn.
Fix: score against THE NEIGHBOURHOOD — the mean paint of the nearest
retained lawn faces — and take the tone-NEAREST clean lattice shift instead
of the first acceptable one. Worst ear now 9.6 (gate 12).

**Defect 2 — the whitish pixels: TWO holes in one check.** (a) `_bad_uv`
tested FULL white (>235 per channel); blank paint's neighbours are merely
near-white. Now min-channel > 205. (b) the exact uv footprint was validated,
but render-time NEAREST sampling lands texels just outside it — now a
1.6-texel DILATED footprint. And the sting: the dilation was added to
`_footprint_bad`, which THE EAR LOOP DOES NOT CALL — a fix that was never on
the path it was written for, caught only because the new gate measured
pixels instead of trusting the code. Blank-paint 0 at all ten cameras.

**THE T-JUNCTION GATE (new, `probe_tjunction.py`).** A vertex in the
interior of another face's edge is watertight in exact arithmetic and cracks
under float32 — invisible to the render gate at most cameras and to the weld
audit (which only looks for near-MISS duplicates). Measured 38 vs baseline's
12 = 26 minted. Root cause: the band-wrap rungs put crest vertices on the
wall that the lawn did not share, plus ear subdivision splitting shared ring
edges. Fix: DENSIFY THE CREST FIRST and build BOTH meshes on that chain,
never split a ring edge, and repair ear-vs-ear splits. Now 2 new, both
sub-0.0014u (baseline carries 12 of its own at that scale).

**A REGRESSION I CAUGHT BY MEASURING, NOT BY REASONING:** raising the repair
tolerance to 2.5e-3 to close those last two opened **26 px of visible
background** — splitting an edge at a point merely NEAR it leaves a sliver
gap the width of the offset, which is strictly worse than the T-junction it
closes. Reverted to near-exact (1e-4). **A repair that is not exact is a
hole.**

**Final:** all 8 gates + latent + peer + blank-paint green; flow 0 smear /
0 stretch / 0 mirrored / 8 rotated; 0 background px. Deployed (backups
.20260802-152923). **P-R (playtest 12): uniform grass, no tone patches, no
white specks.**

## ★ PLAYTEST 12 (2026-08-02) — PASSED. THE V-SHORE CORNER IS CLOSED.

Owner: "yep, that worked. that's the culmination of all this work."
P-R confirmed: uniform grass, no tone patches, no white specks; the cliff
ratified at playtest 11. **The corner is owner-accepted on BOTH axes —
flow (playtest 9: "walkability is good") and look (12).** Twelve playtests,
one corner.

### What actually closed it (the short version worth carrying forward)

Three failures in a row were the same shape, and none of them was a
measurement error: **the element was lawful and the CONTEXT was wrong.**
- The stock coast lip is lawful — over cut sea it is an overhang above dry
  void (THE OVERHANG-CONTEXT LAW), and every auxiliary it forced was new
  authored surface that then carried the next defect.
- A translate-clone donor is lawful — scored against ITSELF instead of the
  grass it lands in, it is a meadow patch (THE WRONG REFERENCE).
- A wrap-split rung is lawful on the wall — not shared with the lawn, it is
  a crack (the T-junction class).
The fix in all three cases was the same move: **stop scoring the element in
isolation and score it against the thing it must live next to** — which is
what THE PEER GATE does structurally, and it is the one instrument this arc
was missing from the start.

### The gate record, honestly

GROUND-JUNCTION-SYNTHESIS measured 0 of 13 playtest verdicts predicted by a
gate. This round: **4 defects caught offline before deploy** (the picket-
fence streak, the brown/cyan tone breaks, a blank texel, and a 26-px hole I
inflicted myself while fixing something else), and **2 the owner found that
no gate yet existed for** — each of which is now a gate. The change is not
that the gates got stricter; it is that they started **measuring pixels and
comparing against approved peers** instead of scoring against stock's
marginals. Cf. `probe_peer_compare.py`, `probe_blank_paint.py`,
`probe_tjunction.py`, and THE TEXEL-DENSITY GATE in `vcorner_transplant.py`.

### Standing debt (READ BEFORE ANY FURTHER BENCH WORK)

The whole corner lives in **study scripts operating on two live blocks**.
A `full_skirt` regeneration overwrites Blocks [5][7]/[5][8] and silently
reverts all of it, and no kit verb knows any of these laws. That debt is
now P0 → `NEXT-STUDIES.md`.
