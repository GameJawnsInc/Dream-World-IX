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
