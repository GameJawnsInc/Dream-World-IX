---
name: authoring-ff9-overworld
description: Gate-and-route skill for the FF9 overworld/world-map -- its FIRST job is to force reading the coast laws before any edit, because bad geometry under the spawn bricks the save with a silent black screen and no log. Use for ANY `world-*` command (`world-terrain`/`reclaim`/`coast`/`transplant`/`fuse`/`island`/`water`/`entrance`/`morphs`), the `--cliff-*`/`--beach-*`/`--band-convert` morph verbs, or any coast/beach/cliff/continent/vehicle work. Covers the canonical wrapped coordinate triple (world/block/cell), RESHAPE-stock-verts-never-OVERLAY, the s34 transform.name-GENERIC override and `--in-place`, reclaim's [NonSerialized] donor-cache mandate, RowInsert+spill-clip growth, the coast-morph and beach-mint rungs, the in-game-proven laws (RELIEF<=6, T-VERTEX gate, DEFORMED-TILE RECT), the `world-morphs` scanner, building collision, placement ground-query, vehicles, world-states, and actor-brick recovery. ALWAYS read memory project-ff9-overworld-coast-mosaic before coast work.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Authoring the FF9 Overworld

## WARNING -- READ-FIRST GATE

**Before ANY coast/beach/cliff/transplant/morph edit, open `references/coast-laws.md` AND memory `[[project-ff9-overworld-coast-mosaic]]`. Bad geometry under the spawn bricks the save (black screen, no log). Do not skip.**

- The coast/beach/cliff work is governed by ~115 in-game-proven laws. `references/coast-laws.md` is only the NAME index; the FULL statements live in memory `project-ff9-overworld-coast-mosaic` — read its `## LAW INDEX` section first, then search the quoted section phrase for the full statement + provenance.
- The save-brick hazard (why the gate exists), verbatim from memory `project-ff9-overworld-actor-brick`: "Editing overworld geometry under (or near) where the player stands can BRICK a save with a silent black screen." The brick is BAKED INTO THE SAVE; deleting the geometry override does NOT fix an already-parked save. Recovery: load a save that is in a FIELD/town, or New Game. Avoidance: keep a safe save on solid land far from the test cell; teleport in/out to inspect; NEVER save while parked on an edited cell. -> `[[project-ff9-overworld-actor-brick]]`.
- Every deploy is preceded by the offline gates the laws define (weld audit, placement census, crack/grain/ledger gates, `cut_census`) — never skip a gate finding ("never explain away a gate finding; MISS must be 0 EVERYWHERE in the cell").

## Coordinate triple + debug-menu readout

The canonical wrapped triple every kit tool speaks: `world (x,z)` · `block (floor(x/64), floor(-z/64))` · `cell (floor(x/32), floor(-z/32))`. The debug-menu Position readout leads with exactly this triple; raw `RealPosition` shows only when `[wrapped]` (it diverges once the overworld wraps — never feed it to kit tools); "Copy position" copies the canonical pair. -> `[[project-ff9-f6-overworld-debug]]`.

## RESHAPE-not-OVERLAY & the save-brick hazard

Verbatim (memory `project-ff9-overworld-terrain-authoring`): "THE LOAD-BEARING RULE: RESHAPE the stock terrain verts; do NOT OVERLAY a new mesh." Displacing existing verts leaves ONE walkmesh surface the player walks on; an overlay above intact ground never wins the down-raycast — it is non-walkable decoration (overlays = buildings/props only). If a save bricks anyway (black screen, the debug menu says "teleport: no controlled actor"): recovery -> `[[project-ff9-overworld-actor-brick]]` (field save / New Game).

## s34 override + `--in-place`

The s34 engine patch's override key is `transform.name`-GENERIC — per-part loose `.ff9mesh` files under `<mod>/FF9_Data/WorldMap/Disc{D}/<lod>/r{Y}/Block[X][Y] <Part>.ff9mesh` override ANY real block's parts (Terrain / Object / Sea1..6 / Beach1 ...). `--in-place` morphs touch ONLY the parts they change; revert = delete the loose files. Its two gates (index in `references/coast-laws.md`): IN-PLACE-FRAME (the block-frame vert set stays byte-unchanged, so it welds to real neighbours) + BOUNDS (nothing leaves the cell).

## Terrain reshape / reclaim

`world-terrain` reshapes stock land (radial/ridge/flatten, multi-block seam-safe); `world-reclaim` turns designated OCEAN cells into walkable land via the s34 divert onto a land-donor prefab; `world-coast` carries a REAL coastal block via a per-cell `Donor.txt` sidecar. Engine mandate, verbatim: the donor cache field on `WMWorld` "MUST be `[NonSerialized]`" — a serialized field shifts the baked MonoBehaviour's layout -> deserialize-corrupt -> overworld BLACKSCREEN. Detail + the 4 mesh bugs + the placement checklist -> `references/terrain-entrance.md`.

## Coast transplant / fuse / grow

`world-transplant` carries a verbatim donor island/region (position / shift / rotation knobs, `--size NXxNY` regions, tweak classes) onto open ocean; `world-fuse <layout.toml>` composes several donors into a continent (land never knits — coastlines are components; the WATER knits). Growth = `RowInsert` cuts at `cut_census`-clean lines + spill-clip budgets (`--grow-cut` / `--grow-cut-z`). Law index -> `references/coast-laws.md`; the full recipes, ceilings, and census verdicts -> memory `[[project-ff9-overworld-coast-mosaic]]`.

Two water-carry gates run automatically on every transplant. **The effective-prefab gate** auto-arms a water-only target cell (a carry emitting >1 sea layer with no Terrain) with a degenerate never-bound `Terrain` stub + `Donor.txt`, so the s34 divert fires and each sea layer binds its own material instead of collapsing to the generic `SeaBlockPrefab`'s only transform (`Sea4`) — the (11,19) black-screen fix; it fails only if the armed donor prefab can't bind an emitted layer. **The Wang-carry gate** censuses the carried outer frame for cropped seams in TWO systems (additive report keys `incoherent_deep` + `incoherent_shallow`): a **mid** Sea3 / mis-oriented Sea5 tile, OR a **shallow** Sea1/Sea2 coastal tile, abutting the deep ring with no transition ring. The predicate is sound — shipping FF9 abuts **neither** mid **nor** shallow water to deep sea4 map-wide: zero sea3-abuts-deep (`wang_seam_census.py`) and zero sea1/sea2-abuts-sea4 (`s12_stock_map_census_opus.py`, land-aware — a sea1 tile's deepest lawful neighbour is sea5, a sea2 tile's is sea3; `transplant.SEA_ADJ_LAWFUL`). It stays **report-only + a visible `!! WARNING …` line** rather than hard-failing, because carrying any coastal island standalone crops the neighbour blocks' transition rings, so real coastal donors (e.g. (7,17) → 16 seams) legitimately warrant a human-reviewed re-tile (`wang_rim_retile` for sea3/sea5, the `{sea1,sea5}` ladder for sea1/sea2), not a refusal. A donor-baseline subtraction can't make it safe-hard-fail (there are no pre-existing such edges to subtract). `--enforce-wang-carry` hard-fails, `--allow-wang-seams` waives. Both gates are byte-neutral over already-deployed carries.

## Coast-morph & beach-mint ladders

Cliff morphs: `--cliff-bump` / `--cliff-headland` / `--cliff-bay` / `--cliff-lobes`. Beach morphs: `--beach-bump` / `--beach-reshape` / `--beach-slide` / `--beach-mint WIDTH|auto[:LAND]`. Band/strip verbs: `--band-convert CX,CZ:PART`, `--strips-rebuild`, `--sand-rebuild`, `--cap-rebuild`. All run on verbatim transplants or `--in-place` on the real map. The `world-morphs` scanner (`--block BX,BY | --all`) enumerates the lawful windows with probed per-verb ceilings and ready-to-run deploy lines — the builders are the oracle. Laws -> `references/coast-laws.md`.

## Entrances / buildings / vehicles / world-states

`world-entrance --cell X Z --field N [--building m.obj]` authors a new overworld entrance in one command: per-language trigger func into every dispatcher carrying the case + tile event bits + an optional seated building (render-only Object; collision = terrain-59 under the building's convex hull, exact via `split_retarget_by_polygon`; entrance tiles excluded from the footprint). Placement obeys the engine ground-query spec (down-ray, first-mesh/first-tri wins, geometric-winding up-facing filter, movement-cache shadow). The 13 world-state dispatchers + the exit cascade and the vehicle system (`.eb` owns policy, C# owns mechanism) gate what loads where. Detail -> `references/terrain-entrance.md` + `references/overworld-engine.md`.

## Additional resources

- Canonical doc (Layer 3): `ff9mapkit/docs/OVERWORLD_ENGINE.md` — tick/actor model, the 13 dispatchers + exit cascade, minimap/place-names, environment, encounters + the world-pack binary, `world-water`, the entrance flow.
- Memory recipes (Layer 2, read on demand): `[[project-ff9-overworld-coast-mosaic]]` (PRIMARY — always before coast work), `[[project-ff9-worldmap-feasibility]]`, `[[project-ff9-overworld-terrain-authoring]]`, `[[project-ff9-overworld-placement-rules]]`, `[[project-ff9-overworld-vehicles]]`, `[[project-ff9-overworld-worlds]]`, `[[project-ff9-f6-overworld-debug]]`, `[[project-ff9-overworld-actor-brick]]`, `[[project-ff9-first-continent-proposal]]`.
