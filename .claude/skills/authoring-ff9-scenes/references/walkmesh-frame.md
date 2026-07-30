# Walkmesh frame — the universal rule, ship-verbatim, reshape via obj+links

**Canonical code:** `ff9mapkit/ff9mapkit/scene/bgi.py` — `BgiWalkmesh.world_verts()`, `build`,
`extract_seams`/`apply_seams`, `reachable_floors()`, `point_on_walkmesh`, `degenerate_tris()`.
**Canonical spec:** `ff9mapkit/docs/WALKMESH_EDITING.md` (the full obj+links design, failure modes,
game-wide seam research); `ff9mapkit/docs/TECHNICAL.md` §6; memory `[[project-ff9-import-frame]]`.

## THE frame rule (universal — no heuristic)

Quoted verbatim from memory `project-ff9-import-frame`:

> Placing an IMPORTED real field's walkmesh onto its painted art =
> `world_vert = vert + header.orgPos + floor.org` (per the vert's FLOOR). Universal. No per-field detection.

- A real `.bgi` stores each FLOOR's verts CORNER-ORIGIN (0-based) in the floor's OWN frame; floors use
  DISJOINT vertex sets. `floor.org` tiles the floors; header `orgPos` places the whole walkmesh.
- **Single-floor fields have `floor.org=(0,0,0)`**, so it reduces to `vert + orgPos`.
- Confirmed from engine source (`WalkMesh.cs`): `world_vertex = vertexList[i] + floor.org + bgi.orgPos`.
- DISPLAY caveat: the engine then does `vertexPos.y *= -1` (`WalkMesh.cs:54`) before the GTE. The kit
  ships `world_verts` pre-flip (the build frame); the flip lives ONLY in display paths (compose_background
  footprint, the Blender import/export boundary). Never flip the shipped mesh — that double-flips.
- The exporter inverse: `bgi.build(verts, faces, floor_ids=...)` writes world-coord geometry with
  `orgPos=0` and every `floor.org=0` (the engine just sums, so org=0 is valid) — for NEW geometry.

## Ship the real `.bgi` verbatim

The `.bgi` codec (`from_bytes`/`to_bytes`) is **lossless**; the `.obj` intermediate is NOT — it carries
geometry only, not the navmesh adjacency graph (`tri.nbr`/`edge`/`edgeClone`, flags, anims). Because
floors are disjoint vertex sets (674/674 fields game-wide), rebuilding neighbor links by shared vertex
INDEX can NEVER recover a cross-floor seam → floors strand → player trapped on one floor. Adjacency is
not a function of geometry (touching floors can be walled; separated floors can be ladder-joined) — FF9
stores it explicitly. So a faithful fork ships `[walkmesh] bgi = "walkmesh.bgi"` (bytes as-is).

## Reshape recipe — `obj + links` (position-keyed seam sidecar)

To EDIT a multi-floor fork's geometry (in-game proven, CLI and Blender):

1. `ff9mapkit import <field> --editable` writes `walkmesh.obj` (reshape reference) + `walkmesh.links.toml`
   (adjacency sidecar: cross-floor seams keyed by WORLD POSITION + header).
2. Edit the `.obj` (or reshape in Blender and Export Field).
3. Switch field.toml from `[walkmesh] bgi` to `obj = "walkmesh.obj"` + `links = "walkmesh.links.toml"` +
   `frame = "world"`. On build, `apply_seams` re-matches each seam to the edited geometry by 3D world
   position (covers coincident + vertical-bridge seams) and WARNS on a moved/deleted seam — never a
   silent mis-link.

Full sidecar format, failure modes, and the seam research → `ff9mapkit/docs/WALKMESH_EDITING.md`.

## Build-time guards (offline — the only legal lever, I can't see the game)

- `reachable_floors()` BFS over `tri.nbr` — build warns on stranded floors (skipped for verbatim `bgi`:
  the original is trusted; connectivity ≠ reachability, some floors are script-reached).
- `point_on_walkmesh(x,z)` — warns on content (NPC/spawn/gateway-zone centre) OFF the walkmesh.
- `degenerate_tris()` — warns on zero-area triangles (IsInQuad dead zones).
- CLI: `ff9mapkit lint <toml>` / `ff9mapkit walkmesh verify <path>`.

## Region-quad gotchas (why zones go dead)

`IsInQuad`/`TreadQuad` test a FAN of consecutive vertex-triplets, not the real polygon — 3 collinear
points = a zero-area triangle = a DEAD ZONE. Author a convex quad with the last vertex DOUBLED.
`COLLISION_RADIUS_W = 80` (`SetObjectLogicalSize(20,...)` → `radius = size*4`, in-game confirmed
2026-07-30 — NOT `bgiRad*4`, which is a battle-return-only field, 0 on a fresh load): the player
CENTRE can't reach a walkmesh edge — extend the walkmesh 80u past the painted floor if the player
should stand at the visual edge. Trigger mechanics
(tags 2/3/10, point order = walk direction) belong to the field-scripts skill / memory
`[[project-ff9-gateway-regions]]`.

## Detours that were WRONG (do not repeat)

- Uniform `orgPos/2` slide — a single translation can't fix x and z in opposite directions.
- An `f0`-vs-`+org` frame auto-detector — ties on simple fields, picked wrong on GLGV. Always `+org`.
