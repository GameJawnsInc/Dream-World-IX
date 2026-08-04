# THE MORPH ENVELOPE — what shape dials each palette mass actually has (2026-08-04)

> **★ CAPABILITY 1 BUILT (same day): the misclassification below is FIXED.** The
> tiled-mains fill (`DESERT-FILL-PREDICTION.md`, scored) flipped comma + crescent to
> deep-bendable — **3 of 8 masses** now admit headland/bay (chain, comma, crescent).
> The isthmus's refusal survived measurement honestly: its deep windows consume topo-49
> at 5% reuse, a REAL mural. `MORPH-ENVELOPE.tsv` is regenerated post-fix; the table
> below documents the pre-fix state that motivated the build.

Sweep: `morph_envelope.py` — `coastscan.scan_block` over every block of every palette
rect, scanner-passing deep windows then verified by real `transplant_region --dry-run`
ladders. Raw table: `MORPH-ENVELOPE.tsv`. Registered in `SHAPE-CONTROL-PREDICTION.md`.

## The headline

**Deep shape control (headland / bay) exists on exactly ONE of the 8 palette masses** —
the chain's (7,17) window, the same one the pre-#17 menu found. Region-capability (#17)
widened the *reach* of the verbs but not the *envelope*: the single-cell guard was never
the binding constraint.

Verified ceilings on the one live window (real gates, not the scanner):
* `cliff-headland` — **8 CLEAN, 12 CLEAN, 16 → land-fit FAIL**. True ceiling 12–15u.
* `cliff-bay` — **6 CLEAN, 10 → drop-set escape**.

The shallow dial is broad: `cliff-bump` (≤2.5u) passes on 14 windows across comma,
isthmus, corner, chain, small, crescent. Reef and reef-fragment have no windows at all
(unlandable by design, consistent).

## Prediction scores

* **M-1 partially confirmed** — 6 of 8 masses have windows; the reef family has none.
* **M-2 confirmed** — ceilings genuinely vary (bump 1.0–2.5 by window; headland 12–15
  where it exists at all).
* **M-3 FALSIFIED decisively** — 1 of 8 masses admits a deep morph, not ≥6.

## The blocker census (why each deep window refuses)

| blocker (scanner's words) | windows × verbs | masses hit |
|---|---|---|
| "no grass mains — painted-mural family" | **~15** | comma, isthmus, crescent |
| "not a clean one-quad wall nor a refined fan" | ~10 | comma, crescent, chain dots, small |
| "waterline touches sea3" | ~9 | isthmus, chain, small, crescent |
| "needs ≥2 base-outline gaps" (too short) | ~6 | dots |
| "outline vert escapes the drop sets" | 2 | corner (0,0)'s long window |

## THE MISCLASSIFICATION — the dominant blocker is not what it says it is

The top blocker claims the window tops are *painted murals* (THE BAKED-TERRAIN LAW: no
fill language). Measured the law's own discriminant — UV-rect reuse — on the dominant
topo of each refused window:

| window | topo | tris | distinct uv-rects | in rects used ≥3x | verdict |
|---|---|---|---|---|---|
| comma (10,5) | 17 | 83 | **8** | **98%** | TILED |
| comma (9,6) | 38 | 48 | 11 | 81% | TILED |
| crescent (15,1) | 17 | 77 | 13 | 92% | TILED |
| crescent (16,1) | 49 | 195 | 28 | 89% | TILED |
| isthmus (7,6) | 19 | 87 | 34 | 62% | TILED |
| isthmus (6,6) | 19 | 34 | 28 | 9% | uv-unique (real mural class) |
| chain (7,17) **the working grass ref** | 0 | 62 | 34 | 37% | — |

**Five of six refused tops are more tiled than the grass coast that works.** The
scanner's "painted-mural family" branch fires on *not grass*, not on *mural* — coastal
topo-17/38/49 here is a small, heavily-reused tile vocabulary (8–13 rects!), nothing
like the 92–100%-unique highland murals the law was measured on. (Instrument note: the
grass ref scores low because grass anti-tiles across many rects; per-block ≥3x reuse
underestimates it. The 81–98% verdicts are safely above any calibration quibble.)

## What this ranks (the capability list, in measured order)

1. **A desert/brush mains vocabulary for the deep-morph fill.** Flips ~15 refusals
   across the three biggest palette masses (comma, crescent, isthmus) from carry-only to
   bendable. The vocabulary half already exists — the ground-translation census measured
   desert's tile language (`LAYOUT_SUPPORT` desert 0.708) and the family machinery ships
   in `GroundRetile`. The fill would repeat measured tiles, not synthesize (CARRY THE
   TILES applies to fills too — proven twice this arc).
2. **Sea3-adjacent windows** (~9 refusals): the cliff verbs refuse a waterline touching
   sea3; the rim-retile vocabulary (verbatim sea5 terminations) is the existing lane for
   re-zipping shallow-adjacent edits.
3. **More wall forms** (~10 refusals): the wall builder accepts exactly two gap shapes
   (one-quad wall, refined fan).
4. Studies 2 (cluster shift) and 3 (strait fuse) from `SHAPE-CONTROL-PREDICTION.md` are
   orthogonal to all of the above (composition, not bending) and remain as registered.

Supporting measurement for Study 2, taken this session: dot clearances are 5.9–19u with
strip-data neighbours on 1–2 sides each; the corner (0,0) has NO neighbour data on any
side, so its shift refill would need the lattice-fill vacancy lane, not strips.
