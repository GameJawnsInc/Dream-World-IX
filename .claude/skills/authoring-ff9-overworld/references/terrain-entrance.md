# Terrain / reclaim / placement / entrances / buildings (reference)

> Index + verbatim load-bearing rules only. Full recipes: memory `project-ff9-overworld-terrain-authoring`
> (terrain/reclaim/coast/water foundation), `project-ff9-overworld-placement-rules` (the complete engine
> ground-query spec), `project-ff9-worldmap-feasibility` (entrance dispatch + engine-fork map + building saga);
> canonical doc `ff9mapkit/docs/OVERWORLD_ENGINE.md`. Never act from a gist here — read the source section.

## Contents

- [Walkable terrain — `world-terrain`](#walkable-terrain--world-terrain)
- [Reclaim ocean cells — `world-reclaim`](#reclaim-ocean-cells--world-reclaim)
- [Faithful coast — `world-coast`](#faithful-coast--world-coast)
- [Moguri HD atlas warning](#moguri-hd-atlas-warning)
- [Placement — the engine ground-query spec](#placement--the-engine-ground-query-spec)
- [Entrances — `world-entrance`](#entrances--world-entrance)
- [Buildings](#buildings)
- [Save-brick and F6 escape](#save-brick-and-f6-escape)

## Walkable terrain — `world-terrain`

- Verbatim (memory `project-ff9-overworld-terrain-authoring`): "**THE LOAD-BEARING RULE: RESHAPE the stock
  terrain verts; do NOT OVERLAY a new mesh.**" Reshape = walkable ground; overlay = non-walkable decoration.
- **The mechanism is NON-REGISTRATION, not raycast precedence** (source-verified 2026-07-19, `WMWorld.cs`) — an
  overlay does not "lose" the ground-raycast to the stock surface; it never enters the raycast at all.
  `WMBlock.ActiveWalkMeshes` returns only `Form1WalkMeshes`/`Form2WalkMeshes`, and the render-only override path
  `RegisterBareObjectOverride` (:831) calls `AddForm1Transform` **but deliberately never `AddWalkMeshForm1`**
  (:846) — so the mesh is renders-and-visibility only, and there is no contest to lose.
- ⚠ **The rule is not universal — an Object override on a TOWN block IS walkability-affecting.** The two paths
  are selected by whether the stock prefab carries a real `ObjectForm1`: bare block (`!ObjectForm1 &&
  TerrainForm1`, :563) → the render-only path above; block WITH a stock `ObjectForm1` (:556) →
  `RegisterBlockComponent(..., form1: true, ...)`, where a loose `.ff9mesh` override **replaces** `mesh` (:790)
  and **is** fed to `AddWalkMeshForm1` (:813). On those blocks an override becomes real collision — and a whole
  3D building mesh as a collider turns its back-face-culled walls + below-ground base into INVISIBLE collision,
  which is exactly why the bare path refuses it. Collision for authored buildings comes from the
  `world-entrance` TERRAIN footprint (topograph 59 under the hull) instead.
- The 4 mesh bugs baked into `world-terrain` (each hit + fixed in-game): (1) LOCAL frame — block verts are
  block-local; (2) Winding — tris must be UP-facing by the GEOMETRIC winding normal; (3) Index buffer — emit
  fresh verts per triangle (shared verts per cell desync `flat_index`); (4) Multi-block seam — apply the same
  world-space deform to EVERY touched block so shared edge verts move identically. Full statements in the memory.
- Movement is topograph-gated, NOT slope-gated. Walkability = the tile's `tangent.x` IDALL topograph vs the
  control's `limit` mask; a reshape leaves topograph untouched, so a raised slope stays walkable at any grade.
- Never reshape under a spawn/field-entry tile (the actor drops at the stale pre-raise Y, below the surface,
  and freezes) — see the save-brick section below.

## Reclaim ocean cells — `world-reclaim`

- Every ocean cell already exists as a `WMBlock` short-circuiting to a shared `SeaBlockPrefab`; the s34 divert
  routes a sea cell carrying a loose Terrain override onto a plain LAND donor prefab. Data-driven: a cell is
  land iff its override file exists.
- Verbatim engine mandate: "the donor cache field on `WMWorld` MUST be **`[NonSerialized]`**" — a serialized
  field on the baked MonoBehaviour deserialize-corrupts it -> overworld BLACKSCREEN (diagnosed in Unity's
  `output_log.txt`, NOT Memoria.log).
- `--height 0` z-fights the sea surface; raising height under a STANDING player embeds them (teleport away+back).
- A lone reclaimed cell is an ISLAND; ship on-foot reachability as a contiguous bridge of reclaimed cells.
- Boat-walkable ocean: the water Terrain walkmesh sits at `WATER_Y = -0.1` with topograph 57 (boat mask admits
  53/54/57; on-foot blocks them). Details + the sink-array facts in the memory.

## Faithful coast — `world-coast`

- Real foam/beach CANNOT come from terrain tiles — a real coastal block is THREE layered sub-meshes (terrain +
  sea bands + a dedicated animated `beach1`). The faithful path carries a REAL coastal block via a per-cell
  `Block[x][y] Donor.txt` sidecar (s34 `ResolveReclaimDonor`/`TryReadDonorPath`). `world-coast --list` = the
  44 real beach donors. Don't donor block 219 (Water Shrine — target-`Number`-gated sea).
- Open-ocean synthesis is `world-water` (marching-band Sea3/Sea5/Sea4; shallows are shore-bound COPY-ONLY —
  see coast-laws.md group A). Doc section: OVERWORLD_ENGINE.md "Custom graded OCEAN water — `world-water`".

## Moguri HD atlas warning

Verbatim (memory `project-ff9-overworld-terrain-authoring`): "**THE GAME RENDERS THE OVERWORLD WITH MOGURI'S
HD ATLAS, NOT STOCK.**" The UV layout is identical but tile CONTENT differs — all overworld texture authoring /
tile-selection MUST sample the ACTIVE atlas (Moguri override -> deployed override -> stock). This one mismatch
explained ~10 failed custom-coast texture iterations.

## Placement — the engine ground-query spec

Memory `project-ff9-overworld-placement-rules` holds the COMPLETE 7-rule spec + the offline simulator
(`sim_place.py`). The rule headlines (full statements there):

1. Ground query = a DOWN ray (walking origin y+2.34375, distance 2.8; sky mode y+400, infinite).
2. Every miss => ground = `defaultHeight = 0` (ocean level) — the stranding fallback.
3. Mesh order: first MESH with any passing hit wins (registration order Object, Terrain, Beach1, ... Sea1..6),
   NOT the closest across meshes.
4. Within a mesh: the FIRST TRIANGLE IN BUFFER ORDER wins — never stack walkable layers.
5. The up-facing filter is the GEOMETRIC WINDING normal (`ny > 0.1`), not stored vertex normals.
6. mapid = the hit tri's `tangent.x` IDALL.
7. F6 teleport = keep Y -> `SetActorPosition` -> `ForceLoadBlockReadyAt` -> sky re-ground -> `Skip = 2`.

The synth-terrain placement CHECKLIST (a)-(e) — up-wound tris, 0 MISS anywhere in the cell, no submerged
up-facing Terrain, no stacked layers, warp target grounds on walkable topo — plus rule (f), verbatim:
"**NO BLOCKED MESH MAY EXTEND UNDER WALKABLE GROUND**" (the movement-cache shadow). **2026-07-18 correction:**
the old prescription here — "synth water must be CLIPPED at the coast outline" — is dead; the mint's Sea4 is a
FULL-CELL plane under the whole island (THE FULL-CELL SEA REVELATION), so there is no outline to clip to. The
working fix is **THE VERGE RULE**: any walkable synth piece within 2u of the outline emits as blocked topo-49
(the superseded v2 was a ~4u-inland MOAT). Also verbatim: "never explain away a gate finding; MISS must be 0
EVERYWHERE in the cell (land AND water)" — a ground-query miss area is also an INVISIBLE VEHICLE WALL + void
render.

## Entrances — `world-entrance`

- One command folds the whole flow: `ff9mapkit world-entrance --cell X Z --field N [--case C]
  [--building m.obj] [--texture/--tile/--tile-uv] [--fresh] [--dry-run] --mod-folder <mod>`.
- Mechanism (memory `project-ff9-worldmap-feasibility`, byte-proven): TWO cooperating world-`.eb` objects —
  the TRIGGER (entry[0] func whose tag = the packed cell `num = 0x8000|(cellZ<<8)|(cellX<<2)|event`) and the
  DESTINATION dispatcher (entry[1] AREA switch -> ScenarioCounter gate -> `Field(dest)`). A tile edit alone
  can NOT make an entrance (no matching func => silent no-op).
- The 13-dispatcher gotcha: the overworld runs ONE of `EVT_WORLD_WORLD00..12` keyed by wldMapNo — the func
  must be added to every dispatcher carrying the case (`world-entrance` does this).
- Per-language: patch each language's OWN world `.eb` base (JP differs — cloning US clobbers Japanese dialogue).
- RELAUNCH (or exit + re-enter the overworld) to reload the world `.eb`.
- Entrance tiles are EXCLUDED from the building footprint (the player triggers from walkable land BESIDE the
  building, never inside); stacking composes but geometry COMPOUNDS on re-runs — use `--fresh` to re-iterate.

## Buildings

- Render-only Object override (s34): the building mesh is NEVER fed to the walkmesh — a hollow 3D model as a
  collider = invisible walls + a walk-in trap.
- Collision = terrain topograph-59 under the building's convex HULL, EXACT via
  `mesh.split_retarget_by_polygon` (Sutherland-Hodgman clip of straddling tris; in-game proven "watchtower
  collision is fixed"). A stale wrong stamp from an older run is NOT self-correcting — reset to a clean
  baseline (re-run the verbatim transplant) before re-authoring.
- Place by bbox-CENTRE, not vertex centroid (asymmetric models bulge off-centre).
- Pick a cell judged OPEN over the WHOLE BLOCK (not a 16u radius); solid footprints are SPAWN-FRAGILE —
  prefer `--hollow-building` for entrance buildings unless the arrival point is guaranteed outside.
- Seating alone is the right default; `--flatten-pad` can leave step-walls (auto-capped to the inscribed
  footprint). Real stock structures round-trip through Blender with real atlas UVs intact (no `--texture`).
- An Object `.ff9mesh` override REPLACES the whole block's Object mesh — use `--keep-block` to append.

## Save-brick and F6 escape

- Bad geometry under the spawn = the "no controlled actor" black-screen brick (silent, baked into the save).
  Recognition + recovery + the engine self-heal: memory `project-ff9-overworld-actor-brick`. Recover by
  loading a FIELD save or New Game; deleting the geometry does NOT un-brick a parked save.
- Live stuck-escape: F6 -> World -> Teleport (or "Warp to field" — fires even when frozen). The F6 cell
  readout is the in-game cell-targeting oracle (`w_worldPos2Cell` = `(int)(x/32), (int)(z/-32)`), and the
  Position section leads with the canonical wrapped world/block/cell triple -> memory
  `project-ff9-f6-overworld-debug`.
