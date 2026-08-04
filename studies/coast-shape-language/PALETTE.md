# THE PALETTE — what we can carry, verified (2026-08-02)

Every row below was run through a real `--dry-run` against the live install. The offline
shortlist is not quotable on its own: 16 rects were predicted, **10 verified**.

## Verified carryable — 10 masses

| donor | size | area | relief | walk | how |
|---|---|---|---|---|---|
| `(9,5)` | 2x3 | 5312u² | 19.1 | 0.67 | clean — **deployed as the Fraying Tail anchor** |
| `(6,6)` | 2x2 | 3616u² | 8.2 | 0.79 | excise 43 cells — **the waisted isthmus** |
| `(3,11)` | 2x4 | 3584u² | 5.9 | **0.87** | excise 180 cells — **the sinuous S-curve** |
| `(6,4)` | 2x2 | 2592u² | 6.9 | **0.00** | clean — the crystal reef, *unlandable by design* |
| `(7,17)` | 4x2 | 2080u² | 5.0 | 0.76 | clean — the island chain |
| `(7,16)` | 2x2 | 1120u² | 6.9 | 0.84 | excise 50 cells |
| `(7,17)` | 2x1 | 864u² | 3.4 | 0.85 | excise 44 cells |
| `(17,16)` | 2x1 | 736u² | 3.3 | 0.70 | excise 26 cells |
| `(16,16)` | 2x1 | 544u² | 3.1 | 0.74 | excise 53 cells |
| `(6,4)` | 1x2 | 544u² | 8.0 | 0.00 | excise 61 cells |

**Plus Daguerreo** — see the census bug below — so the real figure is **11**, against 7
before excise.

## What failed, and why each failure is different

* **`(5,14)` 3x4 Daguerreo — `weld-audit` FAIL (1 pair).** But **`(5,15)` 3x2 carries the
  same mass and gates fully CLEAN** (verified). So Daguerreo *is* in the palette; the
  census simply picked the wrong rect for it.
  **THE CENSUS BUG: one rect is chosen per mass, by least excise, and never re-tried.**
  A mass whose best-by-excise rect fails is reported as unavailable even when another rect
  carries it. The verified count is therefore a FLOOR, not a total.
* **`(14,0)` 4x3 — excise refused, 5 interior waterline verts.** The genuinely-interior
  case the frame fix deliberately does not cover. This one hurts: 8624u², 78% walkable,
  and the most distinctive silhouette in the pool (a swept crescent — a long tapering west
  arm opening into a broad east body). **The single highest-value target for excise v3.**
* **`(4,13)`, `(3,15)`, `(2,10)`, `(5,14)` 2x2 — "every assembly crosses the frame".**
  The offline clearance test works on the 4u cell bbox; the real one works on mesh vertices
  and is stricter. Over-prediction in the census, not a capability gap.

## Reading the palette

Relief is what carries the horizon at the game camera (the outline census measured this;
plan shape does not read). On that axis the pool is thin: **only `(9,5)` at 19.1 has real
vertical presence**, and it is already deployed. Everything else is 3–8u — low, flat land.
Daguerreo (23.5) is the one untapped high-relief mass, which is a second reason to prefer
its `(5,15)` rect.

`(6,4)`'s **walk 0.00** is not a defect: the crystal reef is unlandable in stock too. It is
the pool's only pure-scenery object — useful precisely because you sail past it.
