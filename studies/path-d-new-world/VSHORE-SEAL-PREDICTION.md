# THE CURTAIN SEAL — the V-shore round (registered BEFORE the build)

2026-08-01. The round CURTAIN-GRAMMAR.md's findings make registrable. The defect
(owner-confirmed across two playtests): the carried wall hovers over the descending
shore at the V-shaped coast crossings — you see a slit of sea/backdrop under the
mountain. The grammar study measured the patient (THREE sites, 27/27 hover edges
carried, the pristine bench has zero) and the donor language (stock seals every such
edge; hover-over-ground has ZERO stock instances in 2,928 free edges).

## Scope — what gets sealed (whole chains, never partial)

Seal every TRUE-open carried rim chain that contains a ≥1.5u drop, entire:
- **EAST**: the 4.0u chain in the x=448 plane, (448,3.149,−508)→(448,3.149,−504),
  drop 3.149u to open Sea4 — extends the existing 0.051u mapid-1940 mini-curtain
  downward. Bottom: FREE at the waterline y=0.
- **WEST rim**: the connected ~14.6u chain W1+E_a+E_b+W3 over the build's own
  lawn/4078 underlay (drops 0.65-2.32u; the sub-1.5 members ride along — a
  partially sealed chain would leave mid-chain slits). Bottom: ON the surface below.
- **W2**: the 3.27u carried-lawn rim at the sea inlet, 3.2u over Sea4. Bottom: FREE
  at y=0.
- **SOUTH sea-chain**: 4.0u in the x=448 plane, 2.79-3.25u over Sea4 (one owner is
  the 4078 underlay's own rim). Bottom: FREE at y=0.
- **THE x=384 BORDER RIM**: the 3.46u edge at z −499..−496 with a 2.32u drop to the
  block-5 lawn (the skeptic's find — same class as the west rim, contiguous).
  Bottom: ON the lawn.

**Declared EXEMPT (measured, recorded, not sealed):** the SOUTH hem chain (12.93u,
0.51-0.75u over own lawn/underlay) and the 14 interior hem edges (0.57-0.95u, x
412-438 z −544..−556) — sub-1u drops over the build's own surface, 15-38u inland,
never owner-named; stock's curtain drop domain starts at 1.668u and a sub-1u
curtain has no shipped instance. The rounding-unstable 1.56u skirt edge NW of west
is exempt this round for the same reason (its gap re-measures 0.59 at 4dp). If the
owner names any of these, they become the next round's scope.

## The construction (stock's, from C2 — nothing invented)

Per rim segment a vertical quad (2 tris), top edge = the rim edge's own verts
(shared — the top seam gains a second owner and stops being a once-edge), bottom
verts at the SAME plan positions:
- over water: y = 0 exactly (C3's seal-bottom median 0.00; the pristine bench's own
  free edges sit at y = 0.0 min=med=max);
- over own ground: y = the surface height below at that plan position (the bottom
  edge LIES ON the sheet — we do not split the carried/bench sheet to host verts;
  stock welds INTO its ground sheet, but re-authoring the sheet below is the defect
  factory this arc measured, so the coincident-rest form is the declared deviation).
- topograph/raw mapid: CONTINUE the surface above (east 1940; west rim 1732; W2 0;
  south 1792/4078→its surface owner's id) — stock's 94% above-continuation rule.
  Walk safety is mechanism-proven: geometric ny=0 fails the engine's ny>0.1
  full-scan filter, so a curtain never enters a scan result nor (therefore) the
  movement cache; stock ships 2,703 foot-legal-topograph curtains this way.
- uv: THE PINNED STRIP — v_top=930/1024, v_bot=961/1024 (stretch over the drop, no
  rate law); u accumulates along the chain at 15 texels/u from station 115,
  wrapping 241→115 (within C2's statistical envelope: anchors {115,179,241}, true
  seams only ~53% continuous in stock). ONE strip for all sites this round.
- winding: outward — plan-normal away from the surface-above owner's centroid
  (the skeptic-validated method; 723/725 in stock).

## Predictions (falsifiable, scored at the playtest)

- **P1 (the defect):** at the V-shore the mountain no longer reads as floating —
  no visible slit under the wall at east/west/south. FALSIFIED if the owner still
  sees a gap at any sealed site.
- **P2 (no new defects):** no Z-fighting, no flicker, no dark banding at the sealed
  lines (the curtain is plan-degenerate — zero coplanar overlap with any surface).
  FALSIFIED by any new named artifact on the seals.
- **P3 (walk/camera unchanged):** movement and camera behave exactly as the owner
  confirmed them this arc. Gated offline before deploy; FALSIFIED in-game by any
  new stall/sink/climb/camera regression.
- **P4 (the strip reads lawful):** the seal reads as stock-like shadowed under-edge
  everywhere, INCLUDING under W1's rock rim (topo-49 above — stock has only 3-4
  such curtains and their strip was not decoded; if W1's seal reads wrong, the
  registered fallback is the 59-family rock-row variant, its own micro-round).
- **P5 (domain overhang, declared):** drops 2.86-3.25u exceed the forest strip's
  shipped domain (1.668-2.863u) by ≤0.39u; the pinned-stretch law says the strip
  stretches with no rate constant, so the extrapolation is mild. FALSIFIED if the
  tall seals read stretched/smeared relative to the short ones.

## Gates (all must be green BEFORE deploy; the bench restores pristine first)

1. **Differential identity:** the build's output equals the current deployed bytes
   PLUS added curtain tris only — zero moved verts, zero retagged tris, zero
   dropped tris (geometry-keyed diff, not rounded-vert equality — the skeptic's
   near-duplicate warning).
2. **The build suite** (full_skirt gates): watertight/TEAR/walkability/census, with
   the two lawful new once-edge classes declared to the watertight gate: a curtain
   bottom at y=0 over sea (free-base class) and a curtain bottom lying within
   0.05u ON a surface below (grounded-bottom class). No other new once-edge.
3. **walk_gate_fix 5/5** (gA stacked / gB sunken / gC deadband / gD climbers / gE
   camera) on the final bytes.
4. **gF — the seal gate (new):** the C4-skeptic-style GLOBAL hover census (union of
   blocks, render vocabulary, geometry-keyed once-edges) reads ZERO hover edges
   >0.5u within 12u of the three sites and the border rim; exempt classes report
   their unchanged counts by name.
5. **Curtain-specific:** every curtain tri has |geometric ny| ≤ 0.05; every top
   edge is 2-owned; every uv v ∈ {930,961}/1024 and u ∈ [115,241]/1024.

Deploy only at green; then the owner playtests the V-shore from both banks and the
sea approach. One round, one change class (additive seals), one playtest.

## AMENDMENT (2026-08-02, at the build gate — before any deploy)

gF's first run was RED and the findings amend the scope, recorded here:
1. **The west rim, the x=384 border edge, and the 1.56u skirt edge are ONE
   connected chain**, and it continues north of C4's W1 through two ~2u-drop edges
   ((382.109,5.376,−508)→(383.191,4.919,−504)→(384,5.454,−499.461)) that C4's
   scan-vocabulary hover test missed (they hover over the 4078 underlay in their
   own block — the exact under-detection its skeptic documented). Per the
   whole-chain rule the merged chain seals ENTIRE: 8 quads, drops 0.40-2.38u,
   ground bottoms. The skirt edge's singleton exemption is withdrawn — it is
   chain-connected with a 1.56u drop.
2. **The hem class formalized in gF**: a sub-1u drop over the build's OWN terrain
   (never over sea) is the declared exempt class — it covers the south hem chain
   (0.53-0.75u), the 14 interior hems, and a NW pair at (376-380,−500..−504)
   (0.85u) the gate surfaced. Vertical plan-degenerate once-edges (the curtain
   chain ends) are the second declared class.
3. **The uv-pin census reads 25, not 24**: the 25th is the donor's own 0.051u
   curtain sliver at east (C4's find, mapid 1940, carried stock bytes) — my east
   quad welds to its bottom edge, extending the stock curtain to the waterline.
Totals after amendment: 4 chains, 12 quads, 24 minted tris.

## BUILD LEDGER (2026-08-02 — DEPLOYED at all gates green)

The seal ships as `full_skirt.py`'s final pass (the one-command generator emits
it; the pass only READS upstream state and APPENDS — buffer order untouched,
curtains at cell-buffer tails, unhittable by the camera's down-ray). Sequence:
`restore_bench.py` (pristine, byte-verified) → `full_skirt.py` (gates green,
first run — every registered edge matched once-owned) → `walk_gate_fix.py` 5/5,
camera 100.0% median 0.00 → `probe_seal_gate.py` (gF; first run RED, produced
the amendment above; GREEN after: 0 site hovers, 0 site-external hovers >1u,
25/25 curtains on-strip, additive counts exact) → `--apply` → live-vs-built
byte compare 6/6 identical.

Numbers: 24 minted tris (east 1 quad drop 3.15 → sea; west-border-rim 8 quads
0.40-2.38 → ground; W2 1 quad 3.20 → sea; south-sea 2 quads 2.79-3.39 → sea);
watertight residuals FELL 3 → 2 (a curtain top-weld closed one); TEAR 0;
walkability 0/0; census MISS=0; blocks (7,7) 81→83, (7,8) 201→205. Two gate
adaptations shipped with the pass, both mechanism-grounded: the inline climb map
skips plan-degenerate tris (a vertical seal holds no floor; the engine's ny>0.1
filter keeps it out of every scan and therefore the cache — stock ships 2,703
foot-legal curtains so), and the watertight gate gained the declared
curtain-bottom/end classes. The south-sea chain's −536 end column passes ~0.19u
behind the rising lawn edge on its way to y=0 — hidden under the sheet, no
coplanar overlap, noted for the playtest.

## PLAYTEST 1 (2026-08-02) — P4 FALSIFIED; the GROUND-CURTAIN CLASS REJECTED

The owner, at the west rim (screenshot: a dark forest-textured fin standing on
open lawn under the mountain's skirt): *"covering the seal with a forest wall was
a .... creative choice."* Scores:
- **P4 FALSIFIED decisively** — the pinned strip is painted FOREST-WALL art; on
  an open lawn under a bare rock rim it reads as a wall-object, not an under-edge
  shadow. The study's own miss, named honestly: C2's "22/24 plain-ground curtains
  use the forest strip" measured CONSTRUCTION, not look-in-context — stock's
  plain-ground curtains sit in vegetation contexts; no stock curtain stands on
  open lawn under a rock rim. THE FORM LESSON recurring: a correct construction
  in an off-language placement fails at look. (P1's slit is geometrically closed
  in the frame, but superseded; P2/P3/P5 unscored — the wall-object dominates.)
- **The class verdict is broader than the skin**: no re-texture saves a wall
  standing on open lawn. The owner names the real solution classes (verbatim,
  "in no particular order, non-exhaustive"):
  A. weld smooth grass-tile transitions from the raised mountain base down to
     the existing ground;
  B. mountain versatility — adjustable base elevation on certain
     vertices/corners (manipulate the base to meet the ground);
  C. refuse placement this close to a shore wall; extend the landmass to
     compensate for large mountains.
- **Mapping onto the arc's measured laws** (for the next registration):
  A is bounded by S5 (stock's approach ground = short lip then LEVEL terrace,
  never a ramp) — a "smooth transition" must be a short tuck/terrace course, so
  A converges toward B at small drops. B at the CUT BOUNDARY dodges the
  carry-purity objection: the west rim's verts are OUR clip line (fits_bench),
  not donor-authored interior — pulling the cut edge down to the lawn is
  re-shaping our own cut, and the line-contact geometry is exactly the donor
  foot-weld class that has passed every playtest silently (contact at an EDGE,
  no area overlap → no z-fight). C is the synthesis's own "unexamined third
  move" (make the destination ground already have the donor's shape) — the
  structural answer; fits_bench stops clipping and the donor's natural taper
  ships.
- **The three OVER-SEA seals are a separate question**: they sample the same
  forest strip and will likely read wrong from the sea side too — but there
  stock's measured answer (C3) is the topo-58 COASTAL-CLIFF curtain to the
  waterline, the bench's own shore idiom (mapid-232 strip beside east). A
  re-skin in the cliff vocabulary is the already-measured candidate for them.
The lane choice is the owner's; the live bench still carries this build until
the next round deploys.

**THE OWNER'S DECODE (with the B pick)**: the curtain strip's art is the canopy
WALL of a stock forest that RESTS AGAINST the mountain — "a canopied, walkable
forest rests along the mountain... I think what you copied was that stock forest
resting against the mountain (probably an unstudied/unexpected stock shape)."
So the strip is not a generic under-rim seal; it is the forest assembly's own
wall, and the east sliver we carried is a fragment of that forest-against-
mountain shape. Explains C2's "22/24 plain-ground curtains use the forest
strip" — those sit in vegetation contexts. Banked as a first-class fact.

## ROUND 2 — THE TUCK + THE CLIFF RE-SKIN (registered before the rebuild, 2026-08-02)

Owner's lane: **B at the cut**. Two changes, per-site attributable:
1. **THE TUCK (the west-border-rim chain, 9 verts)**: the ground curtains are
   DELETED; instead the clipped cut-edge verts (OUR clip line, not donor
   interior) move straight DOWN to the surface below them (cluster-move within
   2e-3 so near-duplicate skirt verts stay welded; plan positions unchanged, so
   the 4078 tag boundary and the camera footprint are untouched). The wall
   sheet's last course bends to touch the lawn at an EDGE — the donor foot-weld
   contact class (line contact, no area overlap, no z-fight).
2. **THE CLIFF RE-SKIN (east / W2 / south-sea, 4 quads / 8 tris)**: the over-sea
   seals keep their geometry but drop the forest strip for the bench shore's own
   topo-58 cliff vocabulary, byte-sampled from the pristine shore beside east:
   tangent4 (232,0,0,1), v crest 0.893 / base 0.923 (THE WALL V CORNER-ROLE
   LAW), u sawtooth from 0.699 at 0.01264/u wrapping [0.699,0.947]. The pristine
   shore there is ALREADY a lawn-to-water curtain in this exact vocabulary — the
   re-skinned seals are the bench coast continuing across the crossings (C3's
   measured stock answer: the coast seal IS the topo-58 curtain).

Predictions: **P1r2** the lawn fins are gone and the mountain base meets the
grass, reading as the wall's own foot; **P2r2** the coast crossings read as the
bench's rock lip continuing, slits stay closed; **P3r2** no z-fighting at the
contact line; **P4r2** walk/camera unchanged. Gates: all three suites green; the
change-class gate replaces additive-only (diffs confined to tris containing the
9 moved cut verts, the 8 re-skinned quads, and the 16 deleted ground-curtain
tris); if the inline climb gate fires on tuck side edges, the treatment is
DECLARED here in an amendment before deploy, never silently.

## PLAYTEST 2 (2026-08-02) — ★ ROUND CLOSED, owner-confirmed

*"that did the trick, walk-colliding, camera-following, no seam mountain all the
way around. i gave the terrace a spot check as well."* P1r2-P4r2 ALL CONFIRMED
(the tuck reads as the wall's own foot; the cliff re-skin closed the crossings;
walk and camera clean; the terrace spot-checked good). The V-shore arc that
opened with the floating-wall screenshots is DONE: underlay → camera order →
curtain grammar → tuck + cliff re-skin, each rung owner-scored.

**ONE NEW ITEM, noted for investigation (not a regression of this round's
predictions — a walk TRAP):** at **~(376,−509)-(377,−510)**, near one of the
"vertex corners" of the V-shaped shore wall, the owner got STUCK — could only
TURN, not move, and could not escape without warping out. Context already in
hand for the next round: (a) the walk decode says a controlled walker on a
fully-failed deflection fan STALLS — a spot where every probe direction fails is
exactly this symptom; (b) walk_gate_fix's gC run showed a STALL cluster at
(377.2,−502.7) classified acceptable (open_lawn) — ~6u from the trap: **a gate
accepted what the player experienced as a trap; re-examine gC's classification**
(the regression-harness lesson, again); (c) the declared-exempt NW hem pair
(376-380, −500..−504, 0.85u drops over own terrain) and the tuck chain's west
vert (382.1,−508) both sit nearby; (d) the calibrated offline reproduction tool
EXISTS — walk_sim's deflection-fan walker at that spot, against the deployed
bytes (regenerable by full_skirt.py; backup terrace-strip-prewall.20260802-010535
is the pre-deploy pristine). Reproduce offline FIRST, then decode which surface
is answering the probes, then register the fix.

## THE V-CORNER TRAP REPRODUCTION (registered BEFORE running, 2026-08-02)

Instrument: `probe_vcorner_trap.py` over walk_sim's engine-exact query, against
the LIVE tuck-build bytes (verified: all six Terrain blocks hash-differ from the
pre-deploy pristine; live bytes archived to `backups/vcorner-trap-live.20260802-133500`).
The trap signature under test: stuck-only-turn = a grounded point where the
deflection fan fails for EVERY heading — turning re-aims the fan, so full trap =
all 32 headings (11.25° circle) reject at both commit probes.

- **P-A (static)**: the 0.25u fan map over x 368-388, z −516..−496 (covers the
  owner's pin, gC's stall, the NW hem pair, the tuck's west vert) contains a
  nonzero all-headings-stall set within ~2u of (376.5,−509.5).
- **P-B (dynamic)**: walkers driven at the corner enter that set and STALL; the
  escape test distinguishes ring class — all 32 headings fail with the walker's
  own ring AND a fresh ring → STATIC trap; fresh-ring escape → ring-poisoning.
- **P-C (decode)**: every failing probe names its answering surface (miss vs
  mask-reject; part, buffer tri, mapid, topo, ny). Suspects declared in advance:
  the tuck chain's bent wall course (steep ny ≤ 0.1 → filtered → MISS, or
  buffer-early non-walk sheet), the lawn-clip coverage hole (void MISS), the
  step-up reject (only sheet above y+2.34375), the NW hem pair.
- **P-D (attribution)**: the same map over the pre-deploy pristine
  (terrace-strip-prewall.20260802-010535 Terrain): clean → the trap is THIS
  round's authorship (the tuck, per THE DEFECT FOLLOWS THE AUTHORSHIP); trapped
  → older authorship, named from its decode.
- **P-E (gC re-exam)**: at gC's accepted stall (377.2,−502.7), the open_lawn
  classifier (8 static 1u probes) passes where the 32-heading commit test fails
  — the gate scored LOOK, not COMMIT. The repaired gate class is declared with
  the findings: a stall is acceptable only if some heading COMMITS from it.

Falsification: no all-stall point in the window, static and dynamic, either ring
state → the reproduction FAILED; the trap is not in the decoded walk query over
these bytes (re-suspect: TransportControls mask override, engine state the sim
lacks, wrong bytes) — STOP and re-diagnose, no fix design. Declared freedoms:
window extent, grid pitch, standing-sheet hypothesis (top walkable), step
counts. NOT a fix round: read-only, no deploy, no bench mutation.

## FINDINGS (2026-08-02) — REPRODUCED at the pin; the poisoner is ONE KEEL tri

Instruments: `probe_vcorner_trap.py` (fan map + driven walkers + gC re-exam),
`probe_vcorner_ringdump.py` (deterministic replay with ring introspection),
`probe_vcorner_latent.py` (bench-wide latent sweep). Committed logs:
`probe_vcorner_*_output.txt`.

**THE DECODED MECHANISM — a ring-poisoning trap, not geometry.** Deterministic
replay (spawn 8u north of the pin, walk south): the walker wall-slides into the
wedge at (376.86,−509.60); one deflection probe's plan point escapes every
Terrain tri at the lawn edge, so its full scan falls through to **`Sea4#430` —
the flat sea tri at y=0 spanning (376..380, −508..−512), mapid 224, topo 56 —
the boat seal's KEEL-BLOCK stamp, lying UNDER the land** — and writes it into
the ring's NEWEST slot. From then on the newest-first, filter-free,
no-invalidation cache answers EVERY fan candidate with topo 56 → mask-reject →
all 32 headings fail: stuck-only-turn, exactly the playtest. **The lock is
permanent by construction**: a cache answer prevents the very full scan that
could overwrite the slot — 100 turning ticks, ring FROZEN. Warping out works
only because the new position leaves the tri's plan footprint. This is the wild
instance of WALK-QUERY-DECODE's own banked invariant (MOVEMENT-CACHE SHADOW:
*no blocked mesh may extend under walkable ground*).

**Scoring the registration:**
- **P-A FAIL, and the failure is the finding**: the cold fan map shows ZERO
  all-stall points — at the wedge a cold query has 16 open headings. Every
  registered static suspect (tuck course, coverage hole, step-up, hem) was
  wrong. **A cold probe cannot falsify a cache bug** — the trap is invisible to
  every instrument that does not carry the ring.
- **P-B PASS (ring class)**: 7 driven walkers wedge at (376.6-376.9,
  −509.5..−509.7) with escape **own-ring 0/32, cold 16/32** — the registered
  escape test's ring-poisoning branch.
- **P-C PASS**: the answering surface is `Sea4#430` on all 32 headings (dump:
  32/32 cache slot answers, y=0.00 from origin 5.54). The wall tris
  (mapid-232/topo-58, ny 0.115-0.130) enter the ring during the approach but
  only shape the wedge; the sea tri alone covers the whole fan.
- **P-D — NOT the tuck.** The pre-tuck pristine replays IDENTICALLY (same
  wedge, same poisoner; its wall tris are the same verts renumbered). The
  probe's printed "CLEAN → this round authored it" verdict scored only the
  static+hard classes and is hereby CORRECTED. The authorship: the east
  extension grew land over a sea plane that was never cut (THE SEA4-UNDER-LAND
  LAW), and the coast-nav KEEL stamp (topo 56, `cliffs-refuse`) re-classed that
  under-land sea for the BOAT gate. **Stamp and cut are substitutes for the
  hull, NOT for the walker's cache**: the stamp leaves a BLOCK-class sheet
  under walkable approach land — the boat seal armed the walk trap.
- **P-E CONFIRMED, sharper**: gC's accepted stall (377.2,−502.7) re-examines as
  open_lawn=True AND cold-commit 32/32 — statically free lawn. Its stall was
  this same ring class; the open_lawn classifier tests LOOK (static sheets at
  1u), never COMMIT, and cannot see ring state. **The repaired gate: at any
  stall, re-run the fan with the walker's OWN ring; own=0 is a DEAD-BAND
  regardless of lawn look** (the own-vs-cold instrument now exists in
  `probe_vcorner_trap.drive_walkers`).

**Extent — the trap is UNIQUE on the bench.** The latent sweep (17,074
standable points, 0.5u; hard predicate: a blocked first-hit tri covering all 32
fan candidates): 0 hard at grid scale, 974 poisonable (partial cover — some
heading always escapes cold); the 0.1u refinement pass finds **exactly 2
hard-lock slivers, both this corner, both `Sea4#430`**. The basin is the sea
tri's footprint shrunk by the 0.4375u fan radius, intersected with standable
lawn — a sub-quarter-u sliver only a wall-slide funnels into, which is why one
playtest found it and no gate did.

**The fix implication (recorded, NOT designed here)**: cut the under-land sea
tri(s) per THE SEA4-UNDER-LAND LAW's own rule (the conservative all-3-corners
cut) — a MISS writes nothing to the ring, so the poisoning full-scan never
happens, and the cut is the STRONGER boat seal where it applies. Re-classing
cannot help: any non-walk topo poisons identically, and a walk topo would put
the player on the sea floor. The fix round registers separately, gated by: the
latent sweep's refined hard set = 0, driven walkers at the corner with own-ring
escape > 0, and the repaired gC (own-ring commit at every stall).

## THE SEA-CUT FIX ROUND (registered BEFORE building, 2026-08-02)

One change, per-site attributable: **Sea4 block (5,7), tri #430 only** —
`vcorner_sea_cut.py`, staged offline, gated, then deployed with backup.

**Why not the law's own conservative cut, and why not whole-tri deletion**: the
all-3-corners rule SPARES this tri (corner (376,−512) is open water), and
deleting it whole tears a ~4-5u² visible hole in the water beside the wall foot
— the arc just closed on "no seam all the way around". The fix class is
therefore **SUBDIVIDE + DELETE HIDDEN**: barycentric-subdivide #430 n=8 (64
congruent sub-tris, max edge 5.66/8 ≈ 0.71u; verts/UV interpolated linearly on
the flat y=0 plane — coplanar, so T-junctions against neighbor sea tris cannot
render; tangents asserted corner-equal and copied, mapid preserved), then
delete every sub-tri whose 3 shrunk corners + centroid all lie strictly inside
live Terrain plan coverage (lawn + wall faces = hidden from above). Kept
fragments preserve the visible waterline exactly.

**The dual kill mechanism, declared**: (1) the deletion makes the corner-gap
probe MISS — a miss writes nothing to the ring (the law's cut, applied at
triangle grain); (2) the subdivision is a structural de-arm independent of (1):
the fan's 32 candidates span a 0.875u circle and no kept sub-tri (max edge
0.71u) can contain it, so no single cached sea fragment can ever again answer
the whole fan, whichever probe writes it. The fix does not need to know which
exact candidate wrote the ring — both mechanisms close it.

**Instrument change, declared**: `walk_sim.load_world` gains an additive
`part_src` override (any part, not just Terrain) so the gates run against the
STAGED Sea4 before any deploy; the live replay is re-run first unchanged as the
calibration check.

Predictions:
- **P-F (offline gates, staged bytes)**: the ringdump replay no longer freezes
  — after any wall stall the turning ticks ESCAPE; drive_walkers records 0
  own-ring-0 events; the refined latent sweep finds 0 hard-lock slivers
  bench-wide; the cold fan map over the window is IDENTICAL to live (the fix
  changes no cold-visible walk behavior on land).
- **P-G (seal + look gates, staged bytes)**: boat legality over block (5,7) is
  unchanged — every sea-level column that answered topo-56 either still
  answers 56 (kept) or MISSES (deleted, the stronger seal); no boat-legal topo
  appears anywhere. Every deleted-region sample at 0.1u lies strictly inside
  Terrain plan coverage (nothing visible was removed); kept sub-tri count and
  area ≈ footprint minus covered area.
- **P-H (in-game, owner)**: walking into the V-corner wedges against the wall
  and walks back out — no stuck-only-turn, no warp needed; the waterline at
  the wall foot looks unchanged from the boat and from the shore; the boat
  still cannot pass or land there.

Falsification: any gate red on staged bytes → no deploy, re-diagnose (the
likeliest miss: the writing probe reaches a DIFFERENT under-land sheet — the
gates name it and the round amends here before any bench mutation). P-H
failing after green gates = a sim-vs-engine divergence — re-open the walk
decode, revert the deploy (`revert_vcorner_seacut.py`, backup
`backups/Block[5][7] Sea4.ff9mesh.<ts>` + the archived
`vcorner-trap-live.20260802-133500`). Declared freedoms: subdivision n (≥8),
shrink margin, sample pitches. The bench-wide law application (re-clip ALL
under-land sea, revisit the 974 poisonable) is OUT of this round —
productization, separately registered.

### AMENDMENT 1 (declared before the re-build, 2026-08-02) — g2 fired: the trap RELOCATED

The registered falsification did its job on the first staged run: with #430
alone treated, the original wedge is FIXED (its walkers escape 17/32) and the
hidden-cut/boat/calibration gates all passed — but **g2 named a relocation**:
walkers now hard-lock 4.3u along the wall at (380.4,−511.3), own-ring 0 / cold
16, armed by the NEIGHBOR under-land sea tri. The ground-junction lesson,
verbatim: a per-SITE treatment relocates the defect; the walker wall-slides to
wherever the next armed tri waits, and the wall runs the whole V-shore.

**Scope amended, per-CLASS**: the "tri #430 only" clause and the "bench-wide
application is OUT of this round" clause are both SUPERSEDED by the gate's own
evidence. The re-build treats **every sea-part tri (Beach1/Sea1-5) on the six
bench cells that intersects Terrain plan coverage**: subdivide with per-tri
adaptive N (sub-edge < 0.875u always), delete sub-tris whose 7 samples are all
Terrain-covered, keep everything visible verbatim. Degenerate/placeholder tris
(area ≈ 0) and tris with zero coverage overlap are untouched. The dual kill
mechanism, the deletion predicate, and every gate are unchanged — the
hidden-cut verifier generalizes to per-treated-tri fine sampling and the boat
legality map to all six blocks. Same falsification: all gates green or no
deploy.

## FIX FINDINGS (2026-08-02) — run 2 per-CLASS: ALL GATES GREEN, DEPLOYED

The build (`vcorner_sea_cut.py`, logs `vcorner_sea_cut_output.txt` +
`_stage2_` + `_deploy_`): all six Sea4 files changed — **149 under-land tris
subdivided+cut** (22/35/19/17/36/20 per block 5,7→7,8); Beach1/Sea1-3/Sea5
untouched (no coverage overlap). Verification: **24,866 deleted-region fine
samples, 0 outside Terrain cover** (nothing visible removed); **97,536
sea-level columns, 0 newly boat-legal, 2,189 hit→MISS** (under-land sea now
misses = the cut-class seal, stronger than the KEEL stamp it replaces there).

Gates: **g0** the untouched live bytes still lock (instrument calibrated);
**g1** the staged replay escapes; **g2** zero own-ring-0 stalls — the pin
wedge AND run 1's (380.4,−511.3) relocation both gone, and the STAGED walkers
show **0 ring-poisoned stalls at all** (live had 7): the whole shore poisoning
class died, not just the hard locks; **g3** the cold fan map is point-for-point
identical (no on-land walk behavior changed); **g4** the bench-wide latent
sweep refined at 0.1u: **0 hard-lock slivers in 974 poisonable points**.

DEPLOYED to the live bench (per-file backups
`backups/Block[X][Y] Sea4.ff9mesh.rY.20260802-020657`, revert =
`revert_vcorner_seacut.py`); the post-deploy live re-gate is green (replay
escapes, 0 own-ring-0, 0 ring-poisoned). No registration change — content
hot-reloads; re-enter the world map / warp to re-stream the blocks.

**P-H — the owner's playtest, pending**: (1) walk into the V-corner at
~(376,−509) from the lawn, push into the wedge, then walk back out — no
stuck-only-turn, no warp needed; (2) eyeball the waterline along the whole
V-shore wall foot from the shore and from the sea — it should be unchanged;
(3) nose the boat against the same shore — still refused, still no landing.

## PLAYTEST 3 (2026-08-02) — the TRAP is dead; the residual is the CATCH

*"well, I don't get stuck anymore which is good."* The ring trap is CONFIRMED
FIXED in game — no stuck-only-turn, no warp needed. Two residuals at the same
spot, screenshotted:
1. **The run-freeze**: hitting the corner, Zidane freezes mid-run-animation
   instead of the normal reject-to-standing/idle a wall bump gives.
2. **The broken wall-hug (the owner's "more importantly")**: wall-hugging flow
   that slides along every normal coast HARD-CATCHES on this mini-edge instead
   of sliding through. Escapable by turning — a catch, not a trap.

The catch was measurably present in the sim all along: post-fix driven walkers
still STALL at the wedge (own-ring escape 16-17/32 — free, but stopped). The
escape gates scored trap-ness, not through-flow; the residual needs its own
instrument. Diagnosis registered before any fix design: (a) per failing fan
candidate at the wedge, the reject CLASS (miss vs mask) and the answering
surface — the freeze suspect is the reject-class change (the cut turned sea
mask-hits into MISSES somewhere near the walk edge; a stall with held input
freezes the stride, a mask bump idles); (b) coast-hugging walkers driven
around the corner AND along a healthy control stretch (the east shore) — the
flow defect reproduced as net-progress-zero, the control sliding through;
(c) the engine source read on the miss-vs-mask reject paths (anim state).
Instrument: `probe_vcorner_flow.py`.

## FLOW DIAGNOSIS (2026-08-02) — THE FAN-TURN LAW; the reject-class suspect REFUTED

`probe_vcorner_flow_output.txt`. The measurement overturns the registered
suspect and names the real mechanism:

- **No MISS exists at the wedge.** All 15 failing headings are mask-rejects —
  13 on the wall (Terrain#44/#45, topo 58), 2 on KEPT boundary sea sub-tris
  (Sea4#1000/#1001, topo 56). The sea cut left the reject class at the walk
  edge identical to a stock coast; the freeze is NOT a miss-class artifact.
- **The catch reproduced**: hug walkers (along-coast heading biased 22.5-45°
  into the wall — the player's wall-hug) stall 383-394/400 ticks pinned at
  (376.4,−509.4). The CONTROL (east shore, same hug): PASSED, 0 stalls, pure
  deflect-slide. The sim shows the playtest verbatim.
- **THE FAN-TURN LAW (the minted mechanism)**: the wedge's failing arc is
  h11-h25 = [123.75°, 281.25°]. A hug heading of 202.5° has a fan of exactly
  ±78.75° = [123.75°, 281.25°] — the WHOLE fan inside the failing arc — while
  the walkable continuation around the corner sits at ~112.5-115°, ~9° beyond
  the fan's reach. Held input → the fan fails every tick → stall; heading
  EXACTLY south still slides (its fan bottom just reaches 112.5° — the
  razor-thin margin the replay walkers threaded). **A walkable boundary may
  not turn more than the fan half-span (78.75°) at one vertex, or the
  wall-slide dies there.** Stock coasts turn gradually; the V-corner's crest
  turns ~88° at the single vertex (376.29, 3.2, −509.40). The run-freeze is
  the fully-failed fan with input held (zero movement, the stride freezes);
  the deflect-slide never reaches an idle state on normal walls.

## THE CORNER FILLET (the fix round, registered — build pending)

Design: **round the crest turn at the apex** so no boundary vertex turns more
than ~45°: insert 1-2 crest verts at the corner, extending the lawn a small
fillet seaward (~1-1.5u radius, sub-2u² of new lawn) with the wall face + foot
following, in the wall's own vocabulary. The open arc at the wedge widens from
~112.5° to ≥150°, putting the continuation inside every hug heading's fan —
the slide survives the corner in both directions, which also removes the
freeze state (the fan never fully fails while hugging).

Implementation route: full_skirt.py owns Terrain — the fillet belongs IN the
generator (like THE TUCK), gated first by byte-exact reproduction of the live
Terrain from an unchanged run (worktree calibration); a standalone patch is
the fallback WITH a loud fold-back debt note. The fillet extends land over
kept sea sub-tris → re-run `vcorner_sea_cut.py` after the terrain change (the
per-class treatment re-cuts the newly-covered fragments).

Gates (all must pass before deploy): hug walkers PASS the corner in both
directions at 22.5° AND 45° bias (the new THROUGH-FLOW gate, control stretch
still passing); the wedge fan's open arc ≥ [112.5°, 315°]; the full prior
suite (latent hard = 0, hidden-cut, boat legality, cold-map delta confined to
the fillet zone); ringdump replay still escape-clean. In-game (owner): the
wall-hug slides around the corner without catching; no mid-run freeze; the
corner look unchanged from shore and sea.

### AMENDMENT 2 (before building) — the measurement REDESIGNED the fillet

The boundary extraction (`probe_vcorner_boundary.py`) refutes the fillet's
premise: **no single vertex is sharp** (turns −30.2°, −14.5°, +23.3° — all
under 45°). The coast rotates ~70° CUMULATIVELY (178.8°→114.9° over ~14u),
and the catch is the held heading lagging > the fan half-span behind the LOCAL
tangent: the 114.9° stretch (v5 (376.29,−509.40) → v8 (381.90,−512.00)) fails
any hold ≥ 193.65°. A due-south holder threads it today; a south-southwest hug
cannot. Vertex chamfers CANNOT fix a cumulative bend.

**The freeze decoded from the engine source (ff9.cs:5552-5603 + WMActor.cs:
182-198)**: the fan loop simply exits on full failure — nothing is zeroed —
and the world actor's animation is script-FRAME-driven (`animState.speed=0`,
`animState.time = animFrame/frameN`), frames advancing only with actual
movement. Input held + fan fully failed = run anim selected, frame frozen —
**engine-inherent to every full fan failure, stock included**; unfixable by
data except by keeping the slide alive. One law, one fix.

**THE 126° CREST CHORD (the amended design)**: straighten the crest from v5 to
the strip's turnaround tip v9 (383.79,−514.11) onto a single ~126° chord —
maximum seaward displacement ~0.9u, inside the ~1.1u wall-face room:
- r7 Terrain (5,7): v6 (380.00,−511.12) → (379.54,−511.76); v7
  (381.12,−511.64) AND v8's r7 instances → the seam-clamped chord crossing
  **(379.87,−512.00)** (v7/v8 merge; collapsed tris deleted). The chord is
  clamped to cross the block seam AT a crest vertex, so no r7 tri needs to own
  plan south of the seam.
- r8 Terrain (5,8): v8's r8 instances SLIDE ALONG THE SEAM to (379.87,−512.00)
  and v9 → (383.44,−514.60) — the boundary tris stretch to cover the new lawn
  sliver in their OWN block (self-sealing seam, no patch tris).
- Cluster-move within 2e-3 (the tuck's weld discipline); moved LAWN vert UVs
  re-derived from their tri's pre-move affine map (tile continuity); wall-face
  UVs kept; feet unchanged (faces narrow).
- The new lawn covers kept sea fragments → incremental
  `vcorner_sea_cut.treat_part` on (5,7)+(5,8) Sea4 with STAGED-terrain
  coverage.

Chord tangent ~126° protects held headings ≤ ~204.7° — past the natural hug
range. **Declared residual**: holds ≥ ~205° (hard-southwest into the wall)
still freeze-stall, as they would against any stock wall when the mismatch
exceeds the fan — stock-parity, not a defect of this shore. Gates as
registered, with the through-flow gate primary (22.5° hug PASS both
directions; 45° reported), plus: staged boundary re-extract shows the chord
(all turns ≤ ~10° from v3 to v9'), walkable coverage gained ⊆ the intended
sliver and nothing lost, no degenerate/flipped tris, cold-map identity outside
the zone. Instrument: `vcorner_crest.py`. full_skirt fold-back debt: a
full_skirt Terrain redeploy REVERTS this chord (the sea cut survives — Sea4
untouched by the generator); the chord spec must join TUCK_CHAIN in the next
terrace round.

### AMENDMENT 3 (during the build) — ADDITIVE fairing; THE QUANTIZED-FAN LAW

Two build-time discoveries, each caught by its own gate:

1. **The crest verts are HUB verts** (`probe_vcorner_boundary` local-fan dump):
   lawn lies on BOTH sides of v6-v9 (the walkable strip continues east of
   them), so MOVING crest verts drags interior lawn inside-out — the winding
   gate stopped build 1 with 3 flipped tris. And v5→v8 is already STRAIGHT at
   114.9°: no vertex motion can steepen a straight line between fixed ends.
   The design became **THE SHORE FAIRING, fully ADDITIVE**: a new lawn strip
   seaward of the old boundary (old boundary v5..v11 = inner edge, chord +
   fairing = outer edge), the old topo-58 faces under it DELETED (first-hit
   shadowing), a new near-vertical curtain (feet 0.45u seaward at y=0, cliff
   vocabulary: mapid 232, v 0.893/0.923, u sawtooth) along the new edge, every
   new tri seam-clipped to its owner block, per-tri lawn-UV donors (the lawn's
   u-phase flips between tile families — a global affine is measurably false).
   No vertex moves → no flip risk by construction.
2. **THE QUANTIZED-FAN LAW** (measured on the 126° staged run): the deflection
   fan probes in 11.25° steps, so a slide is robust only when
   |held − tangent| ≤ 78.75 − 11.25 = **67.5°**. At chord 126° a 202.5° hug's
   only landward probe (123.75°) has a 2.25° ≈ 0.017u margin — walkers pinned
   mid-chord at (382.7,−514.1). **The chord is 138°**: mismatch 64.5° for BOTH
   the 202.5° south hug and the 22.5° north hug, and the fairing to v11 runs
   at exactly 202.5°. Run 2 (138°): south+22.5 all PASS with ZERO stall
   ticks, north+22.5 PASS 0 stalls, control PASS; coverage lost=0 / gained
   368 samples all in-strip; hidden-cut 0; boat 0 new-legal; cold-map
   identical outside the zone; 0 own-ring-0, 0 ring-poisoned.
   **south+45 declared residual, stock-parity**: its catches are at
   (372.8,−506.5)/(374.0,−507.5) on the UNMODIFIED upper shore — byte-identical
   positions in the pre-fix run-1 evidence; a 225° hold against a 159.6° shore
   exceeds the quantized fan on any geometry of this direction.

## PLAYTEST 4 (2026-08-02) — THE DEPLOY BRICKED THE BLOCK; root-caused + reverted

*"a big tile of ground missing... cliff seams messed up with empty triangles...
approaching the island cliffs bricks the movement system, causes the game to
lag out and then you end up stuck in the ground, even on airship mode.
attempting to warp onto the island bricks the game as well."* REVERTED
immediately (`revert_vcorner_crest.py`, hashes verified byte-exact back to the
playtest-3 state).

**ROOT CAUSE — THE UNINDEXED CONTRACT (engine source, WMBlock.cs:60-73)**:
`AddWalkMesh` iterates `vertices.Length / 3` and indexes `triangles[i*3]`,
and warns "All vertices, triangles, tangents .Length must be equal" — the
engine expects FULLY UNINDEXED meshes (vcount == icount, 3 fresh verts per
tri; every stock and full_skirt mesh is laid out this way, e.g. 1434 = 478×3).
My builders were the first to append SHARED verts and delete tris while
keeping verts:
- the crest Terrain files: **vcount > icount** (708/696, 471/453) → the loop
  OVERRUNS the index buffer → exception during block registration → the block
  dies: the missing ground tile, the dead cliff faces, movement stranded
  (height-0), warp brick, exception lag. Every symptom, one line of engine.
- **all six sea-cut Sea4 files (which playtest 3 ran on): vcount < icount** →
  `TriangleNormals` built SHORT (e.g. 723 of 1452) — no load failure, but a
  LATENT query-time hazard on high-index sea tris. Playtest 3 passed on luck.

**The gate lesson, sharpened**: the sim parses meshes with ITS OWN reader —
it is loader-blind; a green sim suite says nothing about the engine's data
contract. New standing gate: **vcount == icount on every emitted mesh**
(`vcorner_repack.py check`), enforced before any deploy.

## THE RE-PACK ROUND (registered before deploy)

`vcorner_repack.py`: expand every touched mesh to the contract layout (per-tri
vertex expansion; orphans dropped) — the tri SOUP is asserted identical, so
the sim gates carry by construction (the sim's world model is a pure function
of the soup). Scope: the 4 crest staged files + the 4 other live Sea4 files
(all currently LATENT). Gates: per-file contract-OK + soup-identity asserts;
hug/drive sanity re-run on the packed set; live folder contract-checked after
deploy. P-I (owner, after a game RESTART): the island loads (tile + cliff ring
intact), approach/warp/airship normal, then the fairing checks (slide both
directions, no freeze, the look).

## PLAYTEST 5 (2026-08-02) — loads + FLOW CONFIRMED; two visual defects

*"the game renders now, the stopping and sliding is good, but the cliffs are
malformed, and there is a right-angle seam along the shore as well."* The
contract fix and the fairing BEHAVIOR are owner-confirmed; the geometry is
frozen — this is a texture/construction round. Screenshots: pale triangular
fins rising out of the cliff (one ABOVE the crest), one with a stepped edge;
a straight seam line in the grass meeting the shore at a right angle.

**Root causes, both in the v1 curtain/uv construction:**
1. **THE VERTICAL-FACE CLIP BUG (the fins)**: the v1 curtain quads were
   plan-space seam-clipped — but a near-vertical face's plan projection is a
   degenerate sliver, so the clip's barycentric weights EXPLODE, extrapolating
   both y (fins poking above the 3.2 crest — screenshot 1 exactly) and uv
   (wild coordinates wrapping the atlas = the pale color). One bug, both
   symptoms. A vertical face must never be plan-clipped.
2. **THE PER-BLOCK DONOR SPLIT (the right-angle seam)**: strip tris split by
   the block seam picked lawn-UV donors from their OWN block's affine list —
   the two halves of one quad got different tile-family affines → a grass
   phase jump exactly along the straight seam line z=−512.

**THE SHORE FAIRING v2** (`vcorner_crest.py`, rebuilt from the pre-fairing
Terrain baseline): the block-seam crossing (378.63,−512) is INSERTED into the
outer polyline so every curtain quad lies wholly in one block — vertical faces
are never clipped; curtain UVs use the LOCAL vocabulary (v pins 0.893/0.923
and u-rate ≈0.0126/u verified against the deleted faces; u seeded 0.8579 to
CONTINUE the kept face at v5, sawtooth-wrapped in the measured [0.699,0.947]
band, audited per-vert); lawn strip donors are WORLD-frame and chosen per
PRE-CLIP tri from the old lawn across its inner edge — the same donor for
both clipped halves (uv continuity across the seam AND exact continuity along
the inner boundary). All emitted meshes per-tri expanded (the contract assert
now lives in write_ff9mesh itself). Gates: all stage-1 PASS (hug 0-stall both
directions unchanged, coverage lost=0, hidden-cut 0, boat 0 new-legal +
0 hit→MISS — the sea was already correctly cut, statics identical outside the
bbox), latent 0 bench-wide, live post-deploy re-gate green. Backups
`.20260802-032654`. P-J (owner): the cliff face along the fairing renders in
the local rock texture — no fins, no pale; the grass shows no seam line at
the block boundary; flow still slides; then the standing P-H checks.

## PLAYTEST 6 (2026-08-02) — v2 STILL VISUALLY BROKEN; the arc PARKED

*"more broken, still seaming, random forest tile, random other tile, still
blank voids."* Third consecutive visual failure through fully-green gates.
Unverified suspects for the record: the forest tile = the u-sawtooth
"extend past U_HI" wrap hack sampling the atlas band BEYOND the cliff row;
the white sliver = the 0.26u seam-insert quad; the voids = fan() over
non-convex clip fragments and/or the unwelded joints at v5/v11 where the new
curtain meets the kept faces. NOT diagnosed further — the pattern is the
verdict: **the sim gates cannot see the LOOK axis at all** (no gate renders),
and every hand-rolled construction round mints a new visual defect class
(THE DEFECT FOLLOWS THE AUTHORSHIP, again, on the texture/render axis).

**THE PARKED STATE (live now)**: pre-fairing baseline Terrain
(.20260802-025232, the tuck build the arc closed on) + the MATCHING sea-cut
Sea4 for (5,7)/(5,8), contract-packed (soup-identical repack of the 025232
backups). Verified: trap DEAD (0 own-ring-0), contract-clean, the LOOK is the
owner-confirmed tuck state. **The wall-hug CATCH is back by design** — the
mechanically-proven fix (the 138° fairing surface: hug 0-stall both
directions) awaits a construction method that can pass the look axis.
Un-park: `unpark_vcorner.py` (restores the v2 fairing files, backups
*.park.20260802-033102). The v2 staged files remain in `out/vcorner_crest/`.

**What is PROVEN and carries forward regardless of construction method**: the
ring-trap kill (the sea cut, playtest-confirmed); THE UNINDEXED CONTRACT
(enforced in write_ff9mesh); THE QUANTIZED-FAN LAW (slide needs
|hold−tangent| ≤ 67.5°) and the 138° chord + exact-202.5° fairing GEOMETRY
(hug-gate-proven); the engine decodes (fan/anim/loader); the instruments
(walk_sim, hug gates, latent sweep, boundary extractor, repack/contract
checker).

## STUDY ANGLES — making the coast-edit system flexible (the next arcs)

1. **THE RENDER GATE** — the missing axis. An offline textured renderer of
   block meshes (verts+uvs + the donor prefabs' atlas textures via UnityPy;
   even painter's-algorithm quality) rendering sea-side/land-side/top shots,
   diffed against baseline renders. Every defect of playtests 4-6 (fins,
   voids, pale, forest tile, seams, flipped windings) is visible in such a
   render; none is visible to walk_sim. The calibration law applied to the
   look axis: no visual deploy until the instrument reproduces the LAST
   round's defect offline.
2. **VERBATIM COAST-SEGMENT TRANSPLANT** — the project's own carry law at
   sub-cell scale. Instead of synthesizing lawn/curtain from constants: cut a
   REAL shore segment (crest+faces+feet+uv, its sea edge) from a donor coast
   with the wanted tangent, and weld it between two cut points on the bench
   shore. Every successful look on this bench was a carry (mesa top, ground
   retile, cliff re-skin BESIDE a pristine donor); every synthesis failed at
   look. The study: the segment cut/weld operators + the seam laws.
3. **THE MESHEDIT SUBSTRATE** — promote the hard-won primitives out of study
   scripts into a tested kit module (`world/meshedit.py`): per-tri expansion
   (the contract), never-plan-clip-vertical, seam-vertex insertion, winding
   audits, degenerate cleanup, uv-donor continuation — with synthetic-mesh
   unit tests (worktree-safe) so the next edit composes primitives instead of
   re-rolling them.
4. **THE ATLAS MAP** — decode each donor block's terrain-atlas band layout
   (cliff/grass/forest/beach uv rectangles) into a queryable table, once, from
   the prefab textures. UV assignment becomes VALIDATABLE ("inside THIS
   block's cliff band") instead of trusting constants measured on another
   shore — the forest tile was exactly this blind spot.
5. **THE FAN-AWARE BOUNDARY LINTER** — productize the quantized-fan law: lint
   any walkable boundary polyline for catch-class stretches (mismatch > 67.5°
   for plausible hug holds) at build time, kit-wide; promote walk_sim + the
   hug gate from study scripts to a kit verification verb so every terrain
   deploy gets through-flow coverage automatically.
6. **CURTAIN GRAMMAR II — offset-loop curtains** — derive a new curtain by
   OFFSETTING the existing face loop (carrying its verts/uv/normals
   per-vertex, like the tuck's cluster-move) rather than re-authoring from
   vocabulary constants — re-shaping proven surface instead of minting it.
