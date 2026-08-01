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
