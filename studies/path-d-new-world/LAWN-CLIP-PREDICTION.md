# THE RENDER-ONLY UNDERLAY — the walkability fix round (registered BEFORE building)

2026-08-01. Study A decoded the walk query (`WALK-QUERY-DECODE.md`); study B calibrated
the simulator and measured the defect (`BENCH-WALK-SIM.md`): 3,187 LAWN-UNDER points —
kept lawn, buffer-earlier, grounding the actor under the carried skirt even on a cold
scan. The owner's go-word covers register + build + deploy-at-green; the playtest
scores it. Branch `claude/path-d-level-host`; nothing merges to master.

## The claim under test

**The overlay was visually right and mechanically wrong for exactly ONE reason: the
under-lawn is walk-VISIBLE.** The engine itself ships the missing class: `WMPhysics.
Raycast` skips any triangle whose first-corner `tangent.x` is 4078, 4088, or 2040
(`WMPhysics.cs:15-20`, read firsthand this session, double-verified in the decode) —
a surface that renders but can never answer a ground query. And the terrain shader
binds only `vertex`+`texcoord` (the synthesis), so re-tagging a tangent changes ZERO
pixels. Therefore:

- **REVERT the shingle deletion entirely** — the lawn returns to the overlay's
  continuous sheet (the configuration that PASSED both visual playtests; every slit
  shows grass, no cut-edge voids, no new once-edge classes from deletion).
- **L-rule:** every lawn piece lying UNDER the carried walkable surface is re-tagged
  `mapid = 4078` (0xFEE). Lawn tris CROSSING the coverage boundary are split exactly
  there (slice by the carried plan-boundary segments, the run-1-proven chord
  machinery; both pieces kept, so every split edge is matched, not a once-edge).
  Walkable lawn must NEVER be tagged outside coverage — a render-only fringe on open
  lawn is an uncrossable dead band (miss → reject at every fan angle) and would brick
  the approach; the clip line IS the correctness boundary.
- **C-rule:** every carried tri wholly BELOW the kept walkable lawn (the 1,501
  DEAD-UNDER points — hidden apron the rim relaxation pushed under the sheet) is
  re-tagged 4078 too. Whole-tri, conservative; crossing carried tris stay walkable
  (their exposed part is the hem the player walks).

The engine result, by construction: **at every plan point exactly one walk-visible
walkable surface** — the single-sheet invariant restored without deleting a triangle,
minting a face, or moving a vertex.

## Why 4078 and not deletion or reordering

Deletion re-opens the see-through-void class that cost playtest 1 (the margin strip
existed for slits, and the strip is itself LAWN-UNDER — the sim flags it). Buffer
reordering (carried first) flips the 1,501 DEAD-UNDER points into new defects and is
defeated by the cache anyway (a cached boundary-spanning lawn tri beats mesh order —
the decode's CL-5). The skip-id is the engine's own mechanism, checked before any
filter, immune to cache pollution in the walk loop (ring entries come only from full
scans, which never return a skipped tri). Sole exposures, recorded: the NPC re-ground
branch runs `IgnoreExceptions=true` and CAN hit a 4078 tri — for which 0xFEE is the
engine's own graceful freeze sentinel (`ff9.cs:5209`); and a vehicle get-off probe
could cache one (no vehicles dismount on the bench interior). A source sweep found no
other reader of these ids in any walk-relevant system.

## Gates (deploy only when ALL green)

1. The full_skirt suite verbatim (pristine guard, watertight declared-class cascade —
   expect the SHINGLE cut-edge class to go EMPTY since nothing is deleted — TEAR = 0,
   FRINGE ≥95%, band, census MISS = 0, culled game-eye renders unchanged vs the
   overlay build).
2. **walk_sim.py on the BUILT files (pre-deploy, via `terrain_src`):**
   0 stacked-WALKABLE points (tagged pieces are topo-59, auto-excluded — the census
   needs no special-casing); 0 SUNKEN events on the full trajectory set (the pin +
   every prior cluster); STALL events at each non-wall target ≤ the pristine control's
   (no new invisible walls on open lawn — the dead-band check); the pristine control
   itself unchanged.
3. Post-deploy: walk_sim against the live folder confirms identity with the built
   files.

## REGISTERED PREDICTION

Gates green; in-game the eye sees THE OVERLAY (already twice-passed): connection,
fringe, blob, slits-show-grass all unchanged. The feet get stock semantics: Zidane
climbs the low rim onto the skirt, walks the mountain surface, is properly
wall-blocked where the surface climbs beyond 2.34375 per step, descends any cliff,
and NEVER sinks below a visible surface. The sunken spots at (434,−542) and the
missed hills are gone.

## Falsification semantics — declared in advance

- **Sinking recurs in-game where the sim says single-sheet** → the sim's mesh-order
  or cache model diverges from the engine on THIS data; instrument before any edit
  (the calibration law cuts both ways).
- **Walking onto the skirt stalls on open lawn** (the dead-band class) → the clip
  leaked render-only outside coverage; the clip machinery, not the design, is at
  fault — locate the leaked pieces offline.
- **A 4078 surprise** (actor grounds on a tagged piece, or an unrelated system reacts
  to the id) → a decode falsifier worth more than the round; capture coordinates +
  video, then micro-probe the id on a scratch block before abandoning the class.
- **Any visual regression** → the underlay changed no pixel by design; forensics
  before fixes (suspect the split's uv lerp first — pieces must inherit the parent's
  plan-barycentric uv exactly).
- **SUNKEN via a crossing carried tri under lawn** (the C-rule's declared residue) →
  split carried tris at the lawn boundary too; registered iteration freedom, measured
  by the sim before any deploy.
- **PLUMBING** → fix or stop, no verdict.

One round, one mechanism (the walk-visibility tag). Scored on the owner's verdict.

---

## BUILD (2026-08-01): GATES GREEN on both suites after nine measured iterations

Terminal form: 376 whole lawn tris + 330 pieces of 210 boundary-sliced tris tagged
4078 (L-rule); C-rule empty — **THE HEM LIFT** (200 carried walkable verts below the
lawn raised to exactly 3.2, rock/bench-weld verts locked) dissolved the DEAD-UNDER
class into coincidence instead. The T-sweep converges 333→37→5→1; watertight 2
residual of 4,823 (0.0415% vs stock's own 2.8-6.8%), TEAR 0, inline walkability 0/0,
census MISS=0. **Walk gates 4/4**: 0 stacked-walkable beyond the 0.3 visibility
threshold (strict-interior census — a shared boundary LINE is not a stack; declared
freedoms resolved), 0 SUNKEN on trajectories through the pin + every measured cluster
+ the curtain locus, 0 dead-band stalls, walkers climb the rim.

The iteration ladder — every step forced by a measured artifact, none by conjecture:
1. **Lip-pair line dedup** — the carried boundary carries BOTH lips of donor-border
   pairs; two near-identical slice lines minted 0.006u sliver tears.
2. **THE ISO LINES** — the coverage silhouette is not only mesh once-edges: where a
   carried tri plunges through the lawn plane, the boundary is the iso-curve
   `carried_y = lawn + 0.05` inside that tri (the first gate run's missed class).
3. **Edge-bucket canonicalization** — crossing points grouped PER ORIGINAL EDGE
   (keyed by corner pair) so every owner applies the identical map; polygon-local
   merging was inconsistent across neighbors, and free-radius snapping dragged
   points off their host edges and fed the sweep a cascade.
4. **Sweep-fan max-min apex** — the T-sweep's corner-apex fan minted zero-area flaps
   when a tri carried insertions on two edges (230 degenerate facets; the lawn was
   never heavily swept before). 3D area keeps steep wall tris first-class.
5. **THE HEM LIFT** (above) + iso-hug suppression (post-lift, each hem tri's iso
   hugs its own base edge within centimeters — near-coincident line pairs the sweep
   can neither merge nor conform).
6. **THE LOCAL-ARRANGEMENT CLOSURE** — the forest blob's rim is closed by vertical
   CURTAIN faces (3 plan-owners, never once-edges), invisible to boundary
   extraction; mixed-coverage recs are re-sliced by their local covering tris' own
   edge lines (the boundary is a subset of those by construction).
7. **Exact-overlap eligibility** — point sampling cannot decide closure eligibility:
   a covered SLIVER 0.05u wide at 1.56u depth hid from pulled samples while
   boundary-conformal pieces false-fired vert tests (the 140-rec sweep flood). The
   predicate clips each covering tri against the rec and tests deep cover over the
   actual overlap polygon.
8. **Float-scale closure radii** — the closure's genuine features are hair-thin (the
   blob rim runs ~0.05 off a lawn edge, a true walkable-under hair the walkers hit);
   a 0.06 corner capture collapsed exactly the piece that must survive and be
   tagged. Its lip-pair scale went to the line set instead.
9. **THE KNOT WELD** — hair-tip fragments knot where the hair tapers into the blob
   corner (one 5-edge micro-knot in a 0.1u disc = all 10 "tear pairs"); sub-0.15u
   once-edge endpoint clusters weld to their carried anchor. No healthy edge class
   is that short.

Deployed to the bench at gates-green; the pre-deploy backup is stamped by the deploy
tail. Post-deploy identity vs the built dump verified. **Now awaiting the owner's
playtest** — the prediction stands as registered: the eye sees THE OVERLAY
(twice-passed), the feet get stock semantics.

## PLAYTEST 1 (2026-08-01): walk not re-flagged; TWO RENDER DEFECTS, ONE CAUSE — THE HEM LIFT

Owner: *"still have a seam near that V-shaped shore section... the mountain is lifted
off the grass here. there's a gap in between the ground and mountain. the mountain
still blocks movement in"* + *"Z-fighting near some of the grass hills now... any type
of camera movement causes Z-fighting... you can see the banding."*

Diagnosis — both are THE HEM LIFT, the one pass that moved vertices, and both are
render classes the walk gates are structurally blind to:
- **Z-fighting**: lifting 200 hem verts to exactly LOWLAND made the carried hem
  COPLANAR-COINCIDENT with the lawn — two renderable sheets at identical depth.
  "Dissolves into coincidence" was the walk-side win and the render-side crime.
- **The V-shore gap**: at the coast notch the donor hem lawfully descends BELOW the
  lawn toward the water; the lift pulled those verts up to 3.2, lifting the mountain
  base off the descending shore. (The lock set keyed on exact weld keys — the overlay
  lies ON the shore, unwelded, so nothing was locked there.)
- Movement blocking correct throughout (the walk model holds); the registered
  "visual regression → forensics first, suspect the machinery that moved something"
  branch fired exactly as declared.

**The fix — THE C-SLICE replaces the lift**: the hem ships as DONOR BYTES again (the
exact geometry both overlay playtests passed; zero vertex moves restored as the
round's invariant). Carried walkable tris crossing the lawn plane split at their own
y = LOWLAND−0.1 iso — a coplanar, render-identical split — and the wholly-below
pieces become walk-invisible via the downstream C-rule tag, symmetric with the lawn's
own underlay. Curtains (plan-degenerate) stay whole. The residual untagged crossing
band (±0.1 of the lawn plane) is sub-eps by construction and non-coincident
(separated except along the crossing line itself).

## PLAYTEST 2 (2026-08-01): Z-FIGHTING GONE ("grass looks good now"); TWO OPEN ITEMS

1. **The V-shore floating wall persists** — so the hem-lift attribution for THE GAP
   was WRONG (the Z-fighting attribution was right; one cause, one effect each). The
   gap is in the base full-skirt geometry: the wall crossing the coast at the
   V-notch hovers above the descending shore (the apron was clipped at the bench
   grass edge — `fits_bench` — so no carried ground continues under the wall bottom
   there). Needs a measured probe + its own registered fix.
2. **NEW CLASS — THE CAMERA RIDE-UP**: on stock mountains the camera slides UP the
   mountain to a bird's-eye when it would clip; on ours it passes through and shows
   the far side (the ground beneath). Engine behavior our data isn't triggering —
   mechanism unknown; decode BEFORE designing (WMPsxCamera + the w_cameraHit cache
   sites from the walk decode). Recorded, not guessed.

**THE CAMERA DECODE (same day)** — `WMPsxCamera.cs` is dead code; the mechanism is
`ff9.cs:2926-3001`: each frame the camera SKY-CASTS at the eye's plan position
(4 fuzzy probes ±5.5 taking the max; brackets `UseInfiniteRaycast + CastRayFromSky +
IgnoreExceptions`) and RAISES the eye to `cameraCorrect + hit height` (fast-rise
branch keyed on topograph 49 — rock). **`IgnoreExceptions` bypasses the 4078 skip and
the up-facing filter — the camera is a third consumer of the single-sheet invariant
and it is TAG-PROOF.** With the lawn first in the buffer, the probe read 3.2 under
the whole mountain → no ride → see-through. Fix (data-only): **THE CAMERA ORDER** —
carried tris emit BEFORE the bench sheet; the probe hits the mountain surface, the
walk stays correct because every under-sheet is 4078-tagged (walk scans skip them;
the camera deliberately does not). New gate gE: an engine-exact camera-probe census
over the mountain footprint (probe within 2u of the true top for ≥90%, median
deficit ≤1).

**THE V-SHORE GAP, measured** (`probe_vshore_gap.py`): 66 hover once-edges (edge
>0.5u above a surface below); prime coast-crossing clusters at (448.8,−507.8) east
(11 edges, 22u, wall edges y 1.6-5.1 over shore ~1.9) and (382.4,−511.6) west — the
apron was clipped at the bench grass edge (`fits_bench`), so the skirt ends mid-air
where the shore descends. The fix class is a MINT (the donor's own curtain idiom,
measured on the blob's rim: vertical faces sealing rim to ground, uv = the bottom
course's v-continuation) — registered as its own design round, NOT built here (the
authorship law: no mint without its study).

**REBUILT + REDEPLOYED same day, both suites green again**: C-slice 59 tris, C-rule
113 (its reference now includes TAGGED lawn — a dip spanning under an L-tagged zone
was the only walk-visible surface there, measured at (419.5,−489) gaps 0.31-0.44);
closure eligibility aligned to the gate threshold (0.25 < 0.3 — three stacks had
lived in the 0.31-0.37 crack between the two numbers); THE WINDING RESTORE (a weld
move inverted a small lawn piece to ny −1; bench ground re-oriented by vert swap,
carried never touched); and the facet gate gained a 1e-3 plan-area floor (a 2e-6
hair's winding sign is catastrophic-cancellation noise — measured +1e-5 vs −1e-5
between two evaluations of the same cross product — and can neither hold ground nor
mis-answer). Walk gates 4/4 on the final bytes; watertight 3 residual (0.06%),
TEAR 0. Awaiting the owner's re-check of the V-shore and the Z-fighting spots.
