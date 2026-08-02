# THE WALK-QUERY DECODE — study registration (BEFORE reading)

2026-08-01. The full-skirt round closed the VISUAL junction (two passing playtests) and
opened the walkability front: on the shingle build the owner reports *"some spots miss
hills, and you phase into the ground. couldn't track the pattern"* (~(434,−542)); on the
overlay build before it, *"Zidane appears to be at a fixed height in the world, able to
walk through hills and through the mountain itself."* Every prior statement this arc has
made about the ground query — ray origin, hit selection, cache invalidation, the meaning
of 2.34375 — was **inference from grep hits, never a decode**. The synthesis's honest
line stands: *a probe that cannot reproduce the lifecycle cannot falsify a lifecycle
bug.* This study reads the engine's walk query end to end from source before any fix is
designed.

## What this study is NOT

Not a fix round. No builder edit, no deploy, no bench mutation. The deliverable is a
**decoded algorithm** precise enough that study B (the bench walk simulator) can
implement it offline and reproduce the owner's spots from the deployed bytes.

## The questions — declared before reading

Source of truth: `C:\gd\FFIX\Memoria\` (Assembly-CSharp/Global). Sizes: `ff9.cs` 11,543
lines (the movement engine — the real target), `WMWorld.cs` 2,251, `WMActor.cs` 700,
`WMBlock.cs` 343, `WMPhysics.cs` 129, the rest of WM tiny.

- **Q1 — RAY GEOMETRY.** Where does the ground query's ray actually start and point?
  The scout already shows `ff9.cs:1328 rayStartOffsetY = 2.34375f` — the constant the
  arc has treated as a "climb allowance" is named a RAY-START OFFSET. Decode: origin
  formula, direction, `rayDistance`'s value, the finite vs `UseInfiniteRaycast` modes
  and which caller uses which.
- **Q2 — HIT SELECTION.** First hit, nearest hit, or iteration-order accident? With two
  walk sheets stacked at one plan point (the overlay's configuration, and the shingle
  strip's), which sheet wins, and how does the answer depend on the actor's current y?
- **Q3 — THE CACHE LIFECYCLE.** `ff9.s_moveCHRCache` (class at `ff9.cs:10746`,
  `w_moveCHRCache[11]`, `w_cameraHit[4]`): what is cached, keyed how, written when,
  invalidated when. The fast path `WMBlock.cs:155` retests ONLY the cached triangle —
  when does a stale cache pin the actor to the wrong sheet? The shingle round SHIPPED on
  the assumption "a hidden cut edge breaks the cache" — that assumption is under test
  here, not settled.
- **Q4 — FILTER CALL SITES.** Where the up-facing filter (`WMPhysics.Raycast`) and the
  topograph walkability tables (`w_movementCheckTopographID`) actually apply, and where
  they are absent (the cache path applies neither — confirm from source, not memory).
- **Q5 — THE 2.34375 SEMANTICS.** Derive the behavioral law from the decoded geometry:
  what step DOES it permit, what hill gradient makes the ray start below the surface,
  what an under-sheet within range does to the hit. The prediction to test: ray-start =
  actor y + 2.34375 casting down means (a) a surface more than 2.34375 above the actor
  is INVISIBLE to the query → missed hill; (b) any sheet below the origin within
  `rayDistance` catches the ray → walking the under-sheet; (c) a miss altogether →
  whatever the miss branch does (Q6).
- **Q6 — THE ACTOR Y UPDATE.** On hit: snap or interpolate? On MISS: keep last y (the
  "fixed height" symptom?), fall, or brick? Who moves the on-foot actor each frame, and
  through which of `w_nwpHit` / `w_nwpHitBool` / `w_cellHit`.
- **Q7 — BLOCK LOOKUP.** How (x,z) maps to a block and its `ActiveWalkMeshes`; what
  happens to triangles at block borders; whether a query ever tests a neighbor block.
- **Q8 — COLLISION BLOCKING.** What blocks movement INTO a wall on foot (the owner:
  "nor is he collision blocked") — topograph limit tables, a slope test, or the height
  step itself.
- **Q9 — THE SINGLE-SHEET INVARIANTS.** From the decoded algorithm, enumerate what
  stock geometry silently guarantees (one up-facing sheet per plan point in the ray
  window; steps bounded by the offset; …) — the contract our carried skirt must satisfy
  or the fix must restore.

## Banking rules — falsification semantics for a source study

- A claim is BANKED only with file:line quotes, and only after an adversarial verifier
  re-reads the cited code trying to refute it. Unverified readings stay flagged OPEN.
- **THE CALIBRATION LAW applies to the model, not just the simulator:** the decoded
  algorithm must mechanically explain all three observed regimes — (i) stock walking
  works on stock hills; (ii) THE OVERLAY: fixed-height walk through hills and mountain;
  (iii) THE SHINGLE: local sunken spots + missed hills, tri-pattern-dependent. A model
  that cannot produce all three from the same code path is incomplete, and says so.
- Prior beliefs are on the table as predictions, not facts: "2.34375 is a climb
  ceiling" (probably FALSE as stated), "the cut edge breaks the cache" (UNTESTED),
  "the cache path skips the up-facing filter" (from the synthesis — re-verify).
- Study B (the simulator) is registered separately AFTER this decode lands; its gate is
  reproducing the ~(434,−542) spots before it may gate any fix build.

Ultracode on: the decode fans out over the source via Workflow — five readers by
subsystem, a synthesis over the merged claims, adversarial verification of every
load-bearing claim. Scored on whether the banked model survives its verifiers and
explains the three regimes.

---

## FINDINGS (2026-08-01) — the model survived; all three regimes are one code path

Run record: 70 claims from 5/5 readers, 36 verdicts. **Every load-bearing claim was
independently CONFIRMED by two verifier lenses** (the dedicated cache lens died on an
API error, but both survivors covered its claims and agreed — including on the one
refinement below). Full machine record with every quote: `walk-decode-claims.md`.
The per-frame algorithm (14 steps, file:line-cited, offline-implementable) is in that
appendix under `# ALGORITHM`; what follows is the banked law set.

### The laws

- **THE RAY LAW.** The ground query is a single vertical ray: origin
  `(new_x, current_y + 2.34375, new_z)`, straight down, **UNBOUNDED** — the distance
  parameter is passed into `WMBlock.Raycast` and never read (dead), so
  `UseInfiniteRaycast` is a functional NO-OP everywhere. `2.34375` IS `rayStartOffsetY`
  (`ff9.cs:1328`), not a climb cap: the "climb allowance" is a reachability consequence
  (a surface above the origin intersects at t<0 and is rejected), evaluated per
  ~0.4375u step on foot. Ascent is capped at 2.34375 per step; **descent of any depth
  is accepted in one snap.** The candidate samples the NEW (x,z) at the OLD y.
- **THE FIRST-HIT LAW.** Hit selection is never nearest/topmost: first mesh in
  registration order (Object, Terrain, volcano, Beach1/2, Stream, River, RiverJoint,
  Falls, Sea1-6 — block 219 excepted, s74 flattens it on Path-D discs), then first
  triangle in flat-array order. Where sheets stack, the winner is order + history, not
  height. A kit Terrain override inherits the Terrain slot's position; its triangle
  order is OUR emit order.
- **THE CACHE LAW.** Per-actor-class 10-slot ring; probe order = newest slot, then
  OLDEST→second-newest (the study's one refuted detail — both verifiers found it). A
  cached triangle that still geometrically intersects the ray **wins outright** —
  before the scan, with NO mapid skip, NO up-facing filter (degenerate/coplanar codes
  even count as height-0 hits), only the 0x31EE veto; a cache hit writes nothing back.
  **NO INVALIDATION EXISTS ANYWHERE** — process-lifetime caches survive teleports,
  Form flips, and block stream reloads (which REPLACE the mesh lists in place, leaving
  stale indices to re-bind to new content). The get-off probe even POLLUTES the ring:
  it runs with `IgnoreExceptions=true` on the real movement ring, so cached entries
  were never guaranteed filter-passing. **The shingle round's shipped assumption "the
  hidden cut edge breaks the ground-query cache" is DEAD** — nothing breaks the cache;
  a cached triangle stops answering only when the ray stops intersecting it.
- **THE WALL LAW (FC-8).** Blocking has exactly two mechanisms, both destination-probe
  tests: a hit whose topograph is outside the on-foot mask, or a total miss. **No
  lateral collision exists anywhere in the walk loop.** Any walkable-class sheet at ANY
  depth below a plan point converts the miss into a lawful accept and dissolves the
  wall — the source-level proof of THE SEA4-UNDER-LAND LAW and of the placement study's
  rule (f).
- **THE MISS LAW.** The controlled walker NEVER floats over a miss: a miss rejects the
  candidate, the ±78.75° deflection fan (11.25° steps, +then− per magnitude) hunts an
  accepted heading, and a fully failed fan stalls in place (wall-slide feel = deflected
  accepts). The float/pop-to-zero class belongs to the NPC branch (null cache, no mask,
  miss → ground 0). So the overlay's "fixed height" was NOT miss-float — it was the
  lawn lawfully re-accepted every frame.
- **THE SNAP LAW.** Commit is a two-probe slope-corrected snap: first accepted probe
  measures the 3D step, speed is rescaled to `speed²/step`, RoundCheck re-runs from the
  ORIGINAL pos, and only that second success commits `pos` + `ground_height` — no
  interpolation (`slice_height` rate-limiting applies only to water-class sink).
- **THE BLOCK LAW.** Exactly one block answers: `col=x/64, row=|z|/64` on the 24×20
  grid, no neighbor fallback, no clipping — a triangle answers only inside its owner
  block's footprint. Null/!IsReady → height 0 with pno=−1 (the stranding class; DWIX
  `ForceLoadBlockReadyAt` patches the teleport case).
- **Full-scan filters** (absent on the cache path): mapid skip {4078, 4088, 2040};
  geometric-winding-normal up-facing test `ny > 0.1` (faces steeper than ~84.3°
  invisible; authored normals unused); 0x31EE flight-veto that abandons the WHOLE mesh.
  On-foot walkable topographs: {0-7, 10-13, 16-23, 27, 28, 30, 31} ∪ {32-38, 41, 42,
  45, 46, 52} (masks 0x0010667F/0xD8FF3CFF, bit-decoded twice by hand).

### The three regimes — CONFIRMED as one code path (the calibration law held)

- **STOCK** works because the data guarantees one reachable up-facing sheet per plan
  point; every accident of the algorithm (first-hit, unbounded drop, filter-free cache)
  is invisible under that contract. A wall blocks by mask-hit or by miss — both depend
  on NOTHING walkable lying beneath.
- **THE OVERLAY**: with a lawn under everything, the ray from `lawn_y+2.34375` cannot
  reach hills more than 2.34375 up (t<0) but always reaches the lawn → lawful re-accept
  every frame = fixed height; the wall's miss-reject is converted to an accept = no
  collision; near margins both sheets sit within 2.34375 so either winner looks right =
  "appears on the actual ground near cliffs". The transition contour is exactly
  `carried_surface − lawn_y = 2.34375`, modulated by ring history.
- **THE SHINGLE**: single-sheet almost everywhere = "mostly correct"; at the kept
  boundary-crossing strips the lawn wins by reachability (hill >2.34375 up), by ring
  history, or by array order → phase-into-ground; past the strip the deleted-lawn
  region offers only unreachable hill → miss → the fan decides stall/slide/re-ground by
  entry angle, speed, and ring contents — **the untrackability is real state, not
  noise.** (434,−542) → block (6,8) is a data locus; no code special case. The engine
  reads NO margin: any strip penetration > 0 with a >2.34375 hill-lawn gap reproduces
  the defect class.

### The single-sheet invariants (the contract our geometry must satisfy)

The appendix `# INVARIANTS` section holds the full set; the operative ones: at any plan
point, ALL up-facing walk triangles on the vertical line must lie on ONE surface (the
unbounded cast makes a second sheet at ANY depth eligible); an impassable boundary
exists only where the first reachable hit is mask-blocked or nothing reachable exists;
ascent needs a chain of ≤2.34375 steps; where sheets must overlap, the intended winner
must precede in mesh/triangle order AND the ring makes even that unreliable.

### Prior art reconciled

`project-ff9-overworld-placement-rules` (the 2026-07-07 placement study,
`scratch/synth-island/sim_place.py`) had already RE'd the core spec — down-ray, dead
distance, mesh order, first-tri-wins, winding normals — and **rule (f), THE
MOVEMENT-CACHE SHADOW: no blocked mesh may extend under walkable ground.** This decode
adversarially confirms all of it and extends it: exact ring probe order,
no-invalidation-ever + dangling re-bind, filter-free cached retest, ring pollution,
the deflection fan, the two-probe commit, controlled-vs-NPC miss semantics, the mask
bit-decode. The honest ledger: rule (f) AND the SEA4 law were both on record before
the overlay shipped — the walkability playtest was the price of not re-reading them.

### Gaps that gate study B (from the synthesis, all recorded in the appendix)

The simulator is uncalibrated until it replicates the DEPLOYED byte order (mesh
registration + triangle emit — read from the live block files, not from this source);
TransportControls.csv can wholesale-replace the on-foot mask at runtime (read the live
CSV if present); per-spot reproduction REQUIRES simulating the ring (class-level locus
prediction — strip footprints — is the honest gate, per the regime-shingle caveat);
cross-block overhang and Form1/Form2 list-length parity are byte-level data questions
on our minted blocks.

**Study B is registered in `BENCH-WALK-SIM.md`.** Fix design waits for its calibration.
