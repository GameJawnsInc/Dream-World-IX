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
