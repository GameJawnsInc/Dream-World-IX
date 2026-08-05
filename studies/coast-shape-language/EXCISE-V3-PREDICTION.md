# EXCISE v3 — THE STRUCTURE NOTCH (registered 2026-08-04, before implementation)

## What the 5 interior waterline verts actually are — measured, not assumed

The `(14,0)+4x3` crescent refusal: 5 waterline verts of the dropped assembly are neither
on the deep sheet nor on the rect frame. Probed one candidate explanation at a time:

* **Not near-misses** — nearest sea4 vertex is 20–23u away, five for five.
* **Not sea4-edge T-junctions** — nearest hole-boundary edge is the same 20–23u.
* **Not welded to the kept crescent** — nearest kept vertex is 95–102u away.
* **They are the y=0 base of block `(14,2)`'s `object` mesh, byte-exact, 5 of 5** — and
  that mesh's entire waterline base is exactly these 5 verts, no more.

The world sheet is CUT under baked structures the way sea4 is cut under land: block
`(14,2)` carries a harbor/structure on the dropped mass's south coast, its footprint is a
notch open to the rect frame, and the sheet welds to the structure's base along those 5
verts. `TR.PARTS` never collects `object`, so the notch reads as a genuine hole.

An instrument note for the record: `excise_v2_probe.py` initially reported the impossible
"95 free verts carrying no parts at all" — it was comparing `boundary_cycles`' exact
floats (the E-2 fix) against rounded keys. Fixed before believing anything it said.

## Why closing over is lawful, and the ONLY lawful option

**THE OBJECT ANCHOR** (transplant.py:2708) is standing law: the kit neither carries nor
transforms Object meshes, and target sidecars are chosen object-free so no structure
ghosts at the target. So in any carry the structure does not exist; leaving its footprint
un-filled ships a 12×8u VOID at the target. The dropped assembly's ring detours around
the structure base (ring verts 19→26: leave the frame, cross the 5 base verts, return to
the frame); deleting the whole detour closes the fill straight along the frame and covers
the notch with sea4 — the one part that cannot mint a walk trap.

## The discriminant, and why it is fail-closed

A detour run is deleted iff:
1. every vert in the run is neither sea4-shared nor on the rect frame (plan test), AND
2. the run contains ≥1 waterline vert, AND
3. **every waterline vert in the run matches the rect's own object-mesh y=0 base verts
   byte-exact** (rounded-4dp key, the codebase's standard).

(2) blocks the vacuous case — a pure-profile off-frame corner run with no waterline verts
is kept exactly as today, so no existing fill can change. (3) is the structure test; a
ladder that ends mid-sheet has no object partner and still refuses with the v1 reason.

**Measured scope:** sweeping every 2x2, 3x2 and 4x3 rect on disc 1, exactly ONE rect
reaches the exactness gate and fails it — the crescent — and 5/5 of its verts are
structure-base. The discriminant's live population is this one case; the negative
direction is therefore covered hermetically (synthetic non-structure interior vert must
still refuse) and by mutation (a discriminant forced always-true must go red).

## Predictions

* **V3-1** `(14,0)+4x3` reaches `weld_exact=True`, `structure_base=5`, refusal gone;
  the 330-tri mass drops and the fill covers the notch out to the frame.
* **V3-2** The full dry-run gates pass: `census miss=0 introduced=0`, `weld-audit
  pairs=0`. `inherited` is allowed to be non-zero: the kept crescent has its own 2-tri
  object at `(16,1)` (x 1073–1077, z −104…−108) whose footprint hole is stock's own — the
  census should class it inherited, not introduced. FALSIFIED IF it scores introduced.
* **V3-3** Zero regression: the palette rects' excise reports are unchanged (the sweep
  measured zero structure-base verts anywhere else, and rule (2) forbids vacuous
  deletion).
* **V3-4** Fail-closed: a synthetic interior waterline vert NOT in the object base still
  refuses with the v1 reason; mutation "discriminant always true" is caught red.

## Stop rule

Offline: implement + hermetic tests + mutations + the crescent dry-run scored against
V3-1..V3-3. Deploy is a separate, owner-confirmed step — one deploy, one playtest, with
explicit pass criteria stated first.

---

## FINDINGS — the notch closes, and the rect was never the right rect

**V3-1 CONFIRMED.** `(14,0)+4x3`: refusal gone, `weld_exact=True`, `structure_base=5`,
`frame_waterline=5`, the 330-tri mass drops, and the fill (41 tris) covers the notch
pocket **12/12 samples**. One design deepening forced by geometry: deleting only the 5
base verts leaves the detour's off-frame *profile* vert `(903.9, 0.70, -189.5)` re-routing
the boundary, which cuts a ~12u×2.5u void sliver along the frame — so the deletion takes
the **whole detour** between its frame departures, not just the y=0 verts.

**V3-2 CONFIRMED — after discovering the palette's rect was wrong.** At 4x3 the dry-run
failed wholesale (`census introduced=2051`): donor row 0 is DATA-LESS prefab ocean, and
strip slivers turned three should-be-skipped target cells into sparse deploys, each ~576
introduced misses. The crescent's land spans z −188.6…−67.4 — rows 1–2. **The right rect
is `(14,1)+4x2`**, where the full dry-run is `gates CLEAN`: `census miss=1 inherited=1
introduced=0` (the single inherited miss is the kept crescent's own 2-tri object
footprint at `(16,1)`, stock's own hole, exactly as predicted), `weld-audit 0`,
`border-census holes=0`. The palette quoted a rect that had never been gate-verified
because the excise refusal blocked everything downstream of itself.

**THE GHOST TONGUE — the second real defect, not predicted.** At `(14,1)+4x2` three
gates still failed (`land-fit`, `object-anchor moved=True`, `census introduced=26`), and
`--strips none` cleared all three: the island-tongue rule was judged on **pre-tweak**
land, so the *excised* mass's frame contact opened the S/W windows and the strips carried
its own continuation — the ghost of the thing just dropped — back in, steering the
auto-shift (+4,+8) under the donor objects. Fixed at the law level: **the tongue is
judged on the land that survives the tweaks** (a read-only key probe over `DropTris`;
`apply()` mutates its scope-gate counter and must not be called there). Stash-diff over
the four palette donors: comma/corner/chain byte-identical; the isthmus — whose redeploy
at a fresh target was failing pre-fix with `terrain:669` and land-fit FAIL — now carries
exactly its published 578, CLEAN.

**A third change was attempted and REMOVED as dead code.** "Non-windowed strips gather
water only" sounded principled, but the shift window opens only for *windowed* strips
(`avail = strips_with_data & windowed`), so non-windowed strip land can never lawfully
enter the rect — the partition clips it. The guard changed nothing reachable **and broke
two proven ground-retile carries** whose strips it starved. A guard that cannot fire on
any reachable path is not defense-in-depth; it is a claim the tests cannot check.

**V3-3 CONFIRMED.** Palette reports unchanged (`sb=0` everywhere); guard refusals return
before the notch pass computes. Domain suites: 230 passed.

**V3-4 CONFIRMED.** Three mutations, three caught, each by the test written for its law:
discriminant always-true → the not-the-structures-base test; vacuous-run guard removed →
the profile-corner test; tongue probe disabled → the region tongue test.

### The scoreboard

`(14,1)+4x2` carries **terrain 1386 + beach1 46** (= the mass's full 1432 land tris),
8624u², 78% walkable — the largest carry in the palette by a wide margin (the comma is
917). Deploy blockers: none offline. The 23-seam wang advisory on the cropped rim is the
standard post-carry `world-rim-retile` job. Valid stock-empty, deploy-free 4x2 targets
today: none inside the Path D cluster; nearest are the SE corner (17–20, 17–18) and the
NW (0–2, 0–4) — placement is the owner's composition call.
