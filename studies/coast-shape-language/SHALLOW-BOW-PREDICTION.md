# THE SHALLOW BOW — capability 2, registered 2026-08-04 before building
# ★ BUILT + SCORED same session — results at the bottom; offline-complete, no deploy yet

The last blocker class standing after capability 1: ~9 windows across chain, small,
crescent, isthmus refuse EVERY cliff verb with "the morph window's waterline touches
sea3". The cause is `_assert_pure_sea4`: the morph tweaks are part-scoped, so a
waterline vert coincident in sea3/sea5 would stay behind = a weld crack. The refusal
is correct; the capability is to CARRY the coincident verts.

## The design (the proven bump vocabulary, per part)

`SeaBump` is already part-parameterized and its semantics are exactly right for
shallow sheets: move the keyed verts, re-evaluate uv through the tile's OWN affine
(the caustic stays pinned in world space; the waterline cuts it at a new place),
fold-gate per tile. `cliff_bump` therefore:

1. measures which water parts hold coincident instances of its moved verts;
2. refuses beach1 coincidence (a beach-fronted run is the beach verbs' domain) —
   and ONLY that;
3. emits one `SeaBump(part=p)` per coincident shallow part with its exact expected
   count, and extends the offline fold precheck over those parts' tris.

The structural morphs (headland/bay) keep `_assert_pure_sea4` unchanged — rebuilding
a shallow LADDER is the registered v2 job (shore-bound, copy-only water), not this
rung. The wang/deep-set families are untouched by a bump (a repartition concern only
if a deploy's rim gate flags — `world-rim-retile` is the standing remedy).

## Predictions

* **S2-1 THE FLIP** — cliff-bump builds (offline gates green) on ≥6 of the 9
  sea3-refused windows: chain (8,17) L=18.1/L=106.2 + (9,17) L=36.6/L=18.9, small
  (17,16) L=28.8 + (18,16) L=112.6, crescent (16,1) L=51.2 + (16,2) L=69.2, isthmus
  (6,6) L=79.8 + (7,6) L=117.3. (Some may re-refuse at the fold/clearance envelope —
  those are honest geometric ceilings, not this blocker.)
* **S2-2 NO REGRESSION** — a pure-sea4 window's bump plan is byte-identical (the
  proven (7,17) bump: expected 26 land / 9 sea, golden test green).
* **S2-3 FAIL-CLOSED** — a beach1-coincident window still refuses, naming beach1;
  headland/bay on a shallow window still refuse via `_assert_pure_sea4` (unchanged
  message).
* **S2-4 THE WELD** — per coincident part, the emitted SeaBump's expected equals the
  window's measured coincident instance count (a dropped part = a stay-behind crack;
  a mutation deleting one part's tweak must be caught).

---

## SCORES (built + probed the same session)

* **S2-1 EXCEEDED — 9 of 10 flipped, all at the FULL 2.5u envelope.** The one
  refusal, isthmus (6,6) L=79.8, folds a tile at even 1.0u — a genuine geometric
  ceiling, not the blocker class. Coincidence measured on the ten windows: sea3
  everywhere (2–78 instances), sea5 on four, zero sea1/sea2/beach1.
* **S2-2 CONFIRMED** — pure-sea4 windows emit exactly the old two tweaks (empty
  shallow dict); the proven (7,17) bump golden (26 land / 9 sea) green.
* **S2-3 CONFIRMED** — beach1 coincidence refuses (injected specimen — no palette
  cliff window fronts a beach); headland/bay on the shallow windows keep the
  unchanged `touches sea3` refusal (the ladder rebuild is the registered v2 rung).
* **S2-4 CONFIRMED** — per-part expected counts pinned in-test ((8,17) L=18.1:
  terrain 17 / sea4 2 / sea3 2 / sea5 3), all water tweaks carry one move set.

**Mutation pass: 3/3 killed** (carriage never populates, beach refusal dead,
anchor-only part reads).

**Bonus fix — THE ANCHOR-ONLY READ GAP**: `_assert_pure_sea4` and the structural
REACH gate read `world_tris(*win.donor, ...)` — the anchor cell only — so a REGION
window in a non-anchor cell dodged the purity gates entirely. All three readers now
go through rect-wide `CliffWindow.part_tris`, with a region-aware test pinning it.

## What this unlocks / what stays closed

The shallow dial (conforming bow, ≤2.5u) now reaches every palette mass with a
window: 9 new windows across chain, small, crescent, isthmus. DEEP morphs on
shallow-fronted windows remain refused — rebuilding a shore-bound copy-only ladder
is capability 2b (unregistered), distinct from wall forms (capability 3).
