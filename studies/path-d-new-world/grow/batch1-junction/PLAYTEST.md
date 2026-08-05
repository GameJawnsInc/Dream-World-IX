# Grow-9013 Batch 1 — the JUNCTION landmass gateway

> **★ PASS (owner, 2026-08-05, with screenshot): "that worked"** — entry landed on the grass
> plain, the dune crossing walked, the "!" raised at the seam, Confirm warped back. The
> screenshot shows the two-ground front reading correctly at ground level, the V-shore
> island on the horizon, and the minimap live. **ONE DEFECT FILED: "some random desert
> triangle"** — an isolated sharp desert-textured triangle on the grass at ~the trigger
> seam's south edge, disconnected from the ecotone's organic boundary. Forensics + fix
> below/in TRIANGLE.md; the arming write is ruled out by construction (IDALL bits only,
> UVs byte-identical) pending byte re-verification.

**What's live:** bench field **30951 (PATHDGATE2)** warps into 9013 landing on the
**junction-compose two-ground landmass** (the SW island you verdicted "looks identical to the
disc-1 island" — never yet walked in-world), and a Confirm-gated exit at the grass↔dune seam
warps back. Zero new geometry was minted — this batch is pure parameterization of the Rung-6
scripts: same trigger form (object-0 tag 0xA311, 103 armed tiles on `Block[2][17]`), same
injection form (landing written by the entering field). Backups under
`C:\gd\Dream-World-IX\backups\rung6-worldside-20260805-1112*` + `rung6-pathdgate\`.

**RELAUNCH FIRST** — 30951 (FieldScene + MessageFile) registers at launch. The 30950 bench
from Rung 6 is untouched and still works.

## Stage 1 — ENTRY

1. `~ → Go → Warp to field → 30951` (same checkerboard bench shape as 30950).
2. Walk forward onto the landmarked pad → fade → **World Map: 9013**, standing at
   ~**(157, −1230)** on the junction island's southern grass plain, facing **north up the
   island's long axis** — the grass→dune ecotone front should fill most of the view ahead.
3. Confirm control + walkability; the coast is ~40u behind and to the sides.

**Report:** did you land on the grass plain; does the two-ground front read right from
ground level (this is the first time this landmass is seen from the ground, not renders)?

## Stage 2 — EXIT

4. Walk **straight ahead** (the landing facing aims exactly at the exit): ~95u north,
   crossing the dune field — checkpoints (155,−1219) → (152,−1197) → (149,−1176) →
   (147,−1154) → (144,−1138). The offline walker did this with zero
   deflections; ~65% of the route is on the desert/dunes — the crossing IS the tour.
5. At the grass↔dune seam near **(144, −1136)** the **"!"** appears → press **Confirm** →
   fade → bench 30951, near the back of the room.
6. `~ → Flags`: ScenarioCounter/gil unchanged.

**Report:** the "!" + warp-back, and anything odd underfoot on the dune crossing.

## Expected oddities

- Encounters may fire on the island (its topos are in WORLD11's stock tables) — normal.
- The trigger disc straddles the seam deliberately (51% grass / 49% dune) so the exit reads
  as a landmark; there is NO visible prop on it yet — the "!" itself is the sign. If it
  needs a visible marker, say so and batch 2 can seat one.
- Other sessions' clusters remain visible elsewhere on 9013 (unchanged).

## Escapes

Stuck anywhere: `~ → Go → Warp to field → 30951` (or 30950). Reverts:
`tools/scroll_out/revert_deploy_30951.py` (bench) + the `rung6-worldside-20260805-1112*`
backup manifests (WORLD13 `.eb` ×7 + `Block[2][17] Terrain`).
