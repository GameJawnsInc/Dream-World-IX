# The stray desert triangle — forensics + fix (2026-08-05, FIXED all three trees)

Owner filed on the batch-1 playtest: an isolated sharp desert-textured triangle on the grass
at the exit seam (~(134, −1128)). Forensics ran offline against live bytes; fix applied.

## Diagnosis (byte-grounded)

- **`Block[2][17] Terrain.ff9mesh` tri 521** (verts 1563-1565), a 4.70u² wedge at world
  x 132-136, z −1127..−1130. Its **topograph says grass (0)** but its **uv sits in the desert
  mains rect** — visual family and topo family disagree. Connected-component census: the ONLY
  size-1 desert-visual component on the entire landmass, edge-embedded in the 433-tri grass
  component. NOT a lawful mixed-cell diagonal pair (no shared rect partner).
- **The rung-6/batch-1 arming is ruled out from bytes**: live vs the pre-arm backup differs
  in 675 bytes, 100% tangent.x event bits; uvs byte-identical. The stray predates us.
- **The ratified Disc1 AND Disc4 twins carry the same triangle** (identical geometry, same
  grass topo, desert-family uv — a different tile, since Disc9 is a re-generation with
  another seed). Root cause, measured: the uv is exactly
  `grassland.ground_uv(cell=(33,−283), quad=(1,1), ori=270, ground="desert")` — a lawful
  per-vert mains evaluation with the WRONG ground family: a deterministic **one-tri
  family-selector slip in the junction generator**, reproducing across seeds.
- **Why no gate saw it**: `orphangate.py` censuses STRIPS-vocabulary tris only; a mains-rect
  orphan (family-A rect on family-B topo) is outside its census. That predicate, run
  landmass-wide, finds exactly this tri and nothing else.

## Fix (applied 2026-08-05, all three trees)

`fix_triangle.py` (committed beside this file), mode **translate** — THE TRANSLATION LAW in
reverse: subtract the desert mains delta, recovering exactly the grass tile the generator
would have emitted for cell (33,−283) quad (1,1) at the tri's own rotation. Geometry,
normals, tangents/IDALL, indices untouched (the batch-1 event arming survives). Gated by
the cut-vert, tile-rect-containment, modal-family, and mixed-cell-pair laws (script refuses,
never warns). Dry-run proof: 21-byte delta, all inside the uv channel; `validate_blockmesh`
passes; the desert family drops to 7 components; tri 521 joins grass (434 tris).

Applied to: **Disc9** (the filed defect) + **Disc1 + Disc4 twins** (same defect, identical
delta shape, idall 3584/area-14 preserved) so the cross-world A/B stays honest. Backups:
`C:\gd\Dream-World-IX\backups\Block[2][17] Terrain.ff9mesh.20260805-12363*`.

In-game: loose-mesh hot reload — `~ → World → Reload overworld on state` (or re-enter 9013).

## Follow-up (kit, out of scope here)

Extend the orphan gate with the mains-rect-orphan predicate (tri wearing family A's mains
rect while its topo says family B) so this class is caught offline at generation time.
