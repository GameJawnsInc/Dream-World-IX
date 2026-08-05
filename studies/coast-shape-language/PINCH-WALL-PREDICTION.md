# THE PINCH WALL — capability 3, registered 2026-08-04 before building
# ★ BUILT + SCORED same session — results at the bottom; offline-complete, no deploy yet

The last blocker class from the morph envelope: ~10 window-verbs refuse "window gap N
is neither a clean one-quad wall nor a refined fan". Byte-level decode of 6 specimens
(`wall_gap_probe.py`): **5 are THE PINCH** — `crease[i] == crease[i+1]` byte-exact,
the crease contracts to a point and the wall gap is ONE triangle (bl, br, shared c).
A real stock vocabulary (crescent ×4, chain, comma) the window decode never learned;
today it hard-fails `CliffWindow` CONSTRUCTION, so even the bump — which only
displaces and never rebuilds a wall — dies on any window containing one.

## The design

1. **The decode accepts the pinch**: `cl == cr` → the gap's wall is the single tri on
   the 3 roles; `quads[i] = [tri]`, `refined[i] = []`. Fail-closed: any other tri
   count at a pinch still refuses with the current message.
2. **`cliff_bump` needs nothing else** — displacement + the fold gate already govern a
   pinch tri. (The shared crease vert takes one column's amplitude — the fold gate
   judges the result per tile.)
3. **The structural morphs refuse pinch gaps POSITIONALLY** ("window gap K is a
   crease-pinch...") — the quad-based wall-rebuild vocabulary cannot re-emit a pinch,
   and the scanner's refusal-steered sub-window search already cuts windows at a named
   gap, so structural verbs get steered sub-windows instead of dead blocks.

## Predictions

* **P3-1 THE BUMP FLIP** — cliff-bump builds on ≥4 of the wall-refused windows:
  chain (9,17) L=42.2 / (9,18) L=45.7, small (17,16) L=15.4, crescent (17,2) L=100.2,
  comma (10,6) L=34.5. (Any residual refusal must be a DIFFERENT named gate — fold /
  clearance / no-crease-partner — not the gap-decode hard fail.)
* **P3-2 STEERING** — with the positional pinch refusal, the scanner finds ≥1 NEW
  structural (headland/bay) sub-window on the previously wall-refused blocks (the
  crescent's (17,1) L=101.1 run is 24 gaps long with ONE pinch at gap 10 — cutting
  there should leave a viable sub-run).
* **P3-3 NO REGRESSION** — every existing window decode is byte-identical (goldens +
  the D-2 dump), and windows with non-pinch defective gaps keep the current refusal.
* **P3-4 FAIL-CLOSED** — a pinch gap inside a STRUCTURAL window refuses with the
  positional message (mutation: acceptance leaking into the rebuild must be caught).

---

## SCORES (built + probed the same session)

* **P3-1 CONFIRMED — 4 of 5 bump flips**, and capabilities 2+3 COMPOUND: (9,17)
  L=42.2 (D=1.5) carries sea1+sea2+sea3+sea5 at once; (9,18) L=45.7 (D=2.5),
  (17,16) L=15.4 (D=2.0), (17,2) L=100.2 (D=2.5). The (10,6) L=34.5 residual is the
  genuine class-B shape ("2 tris, 1 refined" with cl != cr) — a different, honest
  decode gap, unregistered.
* **P3-2 EXCEEDED — SIX new structural sub-windows**, not one: (17,1)
  headland-8/bay-6, (14,2) headland-8/bay-6, (15,2) headland-8/bay-4 — all steered
  around their pinch gaps by the positional refusal, scanner-CLEAN.
* **P3-3 CONFIRMED** — non-pinch gaps take the identical decode path; goldens +
  56/56 domain tests green.
* **P3-4 CONFIRMED** — positional refusal pinned in-test; 2/2 mutations killed
  (acceptance dead, structural refusal dead).

## The capability-1+2+3 envelope (vs the pre-arc baseline)

Deep morphs: 1 → **3 masses** (chain, comma, crescent — 8+ windows CLEAN through
real region gates). Shallow bump: reaches **every palette mass with a window** (9
sea3-window flips + 4 pinch-window flips + the six steered structural sub-windows).
Remaining named blockers: the class-B wall shape (~2 windows), the shallow LADDER
rebuild for deep morphs on sea3 shores (capability 2b, unregistered), the
excise∩morph drop overlap (crescent deep rungs), the "needs ≥2 base-outline gaps"
short runs (geometric), and reef/reef-frag (unlandable by design).
