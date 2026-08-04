# RECON DOSSIER — ff9mapkit overworld 3D interface

---

## R1: Architecture & code inventory
# World Subpackage Architecture & Code Inventory

Scope: `ff9mapkit/ff9mapkit/world/` (29 modules, 25,577 LOC total, confirmed via `wc -l`).

## 1. Module-by-module role summary

| Module | LOC | Role |
|---|---|---|
| `__init__.py` | 7 | Package marker only; docstring: "World-map (overworld) tooling — the geometry-edit / custom-overworld pillar (Path C/D)." (`__init__.py:1`) |
| `extract.py` | 479 | Reads FF9 world-map block meshes out of the install's `p0data` AssetBundles offline via UnityPy; defines `BlockMesh` (`extract.py:183`), the canonical in-memory mesh type, plus `read_block`/`decode_id`/`encode_id`/`to_obj`. Foundation layer — imports only `config`. |
| `mesh.py` | 1270 | The `.ff9mesh` loose-override codec (custom engine's `WorldMeshOverride` loader): `write_ff9mesh`/`read_ff9mesh`/`deploy_override`/`deploy_donor_sidecar`, plus synthetic-mesh builders (`island_block_mesh`, `blob_cliff_block_mesh`, `stub_terrain_mesh`) and mesh-editing primitives (`deform_radial`, `flatten_region`, `retarget_tiles`, `weld_audit`). Owns the authoritative `GRID_COLS/GRID_ROWS = 24, 20` grid constant, re-exported by `terrain.py`/`water.py` (`mesh.py:32`, `terrain.py:22`, `water.py:46`). Foundation layer. |
| `meshedit.py` | 1028 | "the coast-edit primitives, promoted out of study scripts" (`meshedit.py:1`) — generic polygon/wall geometry toolkit: `earclip`, `sweep_wall`/`WallSweep`, `find_tjunctions`/`repair_tjunctions`, `flat_patch`, `lattice_patch`, `retag_flat`. Zero intra-package imports (pure primitives layer). Consumed only by `transplant.py` (lazy imports, `transplant.py:3368,3827,4148`). |
| `terrain.py` | 337 | "Author walkable overworld TERRAIN — raise/lower/flatten/ridge the ground by RESHAPING the stock mesh" (`terrain.py:1`): `reshape`, `coast`, `reclaim`. Backs `world-terrain`/`world-reclaim`/`world-coast`. |
| `water.py` | 609 | "Synthesize custom GRADED OCEAN WATER... from a depth field" (`water.py:1-3`), the from-scratch counterpart to `terrain.coast`'s verbatim carry. `build_arrangement`, `build_cell`, `water`, `deploy_island_sea`, `reproduce`. |
| `island.py` | 1056 | "Fully-SYNTHETIC overworld islands/landmasses" (`island.py:1`): Delaunay-based `build_landmass`/`landmass`, `verify_landmass`. Imports `grassland`, `placement`, and lazily `islandbeach`/`texgates`. |
| `islandbeach.py` | 546 | "THE LADDER MINT — a beach arc on a `world-island` mint" (`islandbeach.py:1`): `plan_arc`/`build_beach`. Has no dedicated CLI verb; wired only as a lazy import inside `island.py` (`island.py:294,542`) and `transplant.py` (`transplant.py:359,665`) behind `--beach`/`--beach-*` flags. |
| `interior.py` | 2552 | "INTERIOR topography on a DEPLOYED kit island" (`interior.py:1-8`): backs `world-forest`/`world-hill`/`world-mountain` — `carve_forest`, `build_hill`, `carve_mountain`, `deploy_mountain_parts`. Imports `extract`, `grassland`, `mesh`, and lazily `placement`. |
| `transplant.py` | 4169 | The god-module of donor-carry: "VERBATIM overworld TRANSPLANT: carry a complete real block... to a custom ocean cell" (`transplant.py:1-3`). Core `transplant`/`morph_in_place`/`transplant_region`, plus a large family of "tweak" classes (`TileRetexture`, `GroundRetile`, `PatchRecover`, `VertexDisplace`, `RowInsert`/`RowInsertZ`, `SpillClip`/`SpillClipZ`, `DropTris`, `EmitTris`, `SeaBump`) and gates (`wang_carry_gate`, `sea_adjacent_lawful`). Backs `world-transplant`, `world-morphs`. |
| `coastmorph.py` | 6880 | The largest module: "CLIFF-COAST MORPHS on verbatim transplants" (`coastmorph.py:1`). Beach/cliff/sand/foam rebuild families: `beach_bump`, `beach_rebuild`, `beach_reshape`, `beach_mint`, `band_convert`, `sand_rebuild`, `cliff_bump`, `cliff_headland`, `cliff_bay`, `cliff_lobes`, `cap_rebuild`. Backs the `world-transplant --beach-*`/`--cliff-*`/`--band-convert` flag family (`cli.py:4255,4332,5073`). |
| `fuse.py` | 223 | "Cross-donor FUSE: compose several verbatim transplants into ONE contiguous custom region" (`fuse.py:1`): `fuse_layout`. Sits directly on `transplant.py` (`fuse.py:30-31`). Backs `world-fuse`. |
| `rimretile.py` | 361 | "terminate a carried island's CROPPED SHALLOW RING" (`rimretile.py:1`): `plan_rim`/`apply_rim`/`rim_retile`. Imports `water.py`. Backs `world-rim-retile`. |
| `grassland.py` | 701 | "The REAL overworld GRASS tile language — byte-measured" (`grassland.py:1`): `ground_uv`, `assign_mains`, `mains_uv`, `relief`, `smooth_normals`. Zero intra-package imports — a pure data/algorithm library. Widely consumed (by `island`, `interior`, `coastmorph`, `orphangate`, `texgates`, `transplant`). No dedicated CLI verb; not directly imported by `cli.py`. |
| `palette.py` | 216 | "Texture NEW overworld geometry by reusing the shared atlas — a UV palette learned from real blocks" (`palette.py:1`): `build_palette`, `apply_palette_uvs`. Backs `world-texture-palette`. |
| `atlas.py` | 433 | "Extract + preview the overworld texture ATLAS" (`atlas.py:1`): `extract_atlas`, `tile_catalog`, `deploy_atlas`, `add_tile`. Backs `world-atlas-extract`/`-catalog`/`-reskin`/`-add-tile`. |
| `placement.py` | 99 | "OFFLINE ENGINE-PLACEMENT SIMULATOR — the overworld ground-query, byte-exact to Memoria source" (`placement.py:1`): `place`, `census`. No CLI verb of its own; consumed internally by `island.py`, `interior.py`, `transplant.py`. |
| `texgates.py` | 451 | "THE TEXTURE + SEA GATES — the Rung-F UV/relief arc's acceptance criteria, productized as carry-time/mint-time gates" (`texgates.py:1-3`): `zero_uv_area_gate`, `one_window_gate`, `sea_plan_gate`, `texture_sea_gates`. No CLI verb; surfaced only via `summary["report"]["texgates"]` inside `world-transplant`'s output (`cli.py:4595`). Consumed by `island.py`, `transplant.py`. |
| `orphangate.py` | 541 | "THE ORPHAN-DECAL GATE — a carry-time productization of the comp[1] fringe-arc's proven rule set" (`orphangate.py:1-6`): `orphan_decal_census`, `orphan_decal_gate`. No CLI verb; consumed only by `texgates.py` and `transplant.py`. |
| `meshedit.py` | (see above) | |
| `coastnav.py` | 413 | "THE COAST NAVIGATION STAMP — vehicle legality classes on a synthetic coast" (`coastnav.py:1`): `stamp`. Backs `world-coastnav`. |
| `coastscan.py` | 348 | "The COAST WINDOW SCANNER — the coast-morph pillar's catalog builder" (`coastscan.py:1`): `beach_windows`, `cliff_windows`, `scan_block`. Imports `transplant` and `coastmorph` (reaches into `coastmorph._pk`, `coastscan.py:30`). No standalone `world-coast-scan` verb found in the `set_defaults` list — likely invoked as a sub-mode of `world-coast`/reporting rather than its own top-level command. |
| `locate.py` | 267 | "Decode the FF9 OVERWORLD entrance dispatch: which world CELLS lead to which field" (`locate.py:1-2`): `case_to_fields`, `case_to_cells`, `locate`. Backs `world-locate`. |
| `entrance.py` | 1038 | "Author a complete custom OVERWORLD ENTRANCE end-to-end (model → place → seat → trigger)" (`entrance.py:1-2`): `author_entrance`, `cell_to_block`, `dispatcher_cases`, `patch_byte39`. Backs `world-entrance`. Imports `extract`, `mesh`; reaches into `locate.cell_to_block` from `cli.py` (`cli.py:3896`). |
| `discmirror.py` | 285 | "Mirror a mod folder's WorldMap overrides across DISC TREES" (`discmirror.py:1`): `auto_mirror`, `mirror`. Backs `world-mirror`. Imports `extract`, `mesh`. |
| `navimap.py` | 409 | "Overworld minimap MARKER registry + the reveal helper" (`navimap.py:1`): `marker_bit`, `resolve_markers`, `composite_world_map`. Backs `world-minimap`/`world-rename-markers`. Lazily imports `mesh` (`navimap.py:359`). |
| `environment.py` | 144 | "Overworld WEATHER/environment authoring — emit Memoria's `Environment.txt`" (`environment.py:1`): `build_environment_txt`, `write_environment`. Backs `world-environment`. Zero intra-package imports. |
| `encounter.py` | 160 | "Overworld ENCOUNTER-RATE authoring — retune the random-battle frequency in the world `.eb`" (`encounter.py:1`): `apply_encounter_rate`, `deploy_encounter_rate`. Backs `world-encounter-rate`. Zero intra-package imports. |
| `worldpack.py` | 290 | "Codec for the overworld `discmr.img` — the baked binary that holds the random-encounter TABLE" (`worldpack.py:1`): `Discmr`, `load_discmr`, `deploy_discmr`. Backs `world-encounters`. This is a *separate pillar* from mesh geometry — it never touches `BlockMesh`. |
| `blendio.py` | 265 | "Blender round-trip for overworld block meshes — the 'mesh surgery' path" (`blendio.py:1`): `export_obj`/`read_obj`/`build_from_obj`. Backs `world-mesh-export`/`world-mesh-build`. Imports `extract`, `mesh`. |

## 2. Main data flow

**Ingress — asset bundle → Python object.** `extract.py` reads the game's `p0data*.bin` UnityRaw bundles offline via UnityPy (`extract.py` docstring, `_unitypy`, `_bundles`, `_worldmap_env`) and decodes a block's interleaved vertex buffer + index buffer into the package's one canonical in-memory type: the frozen dataclass `BlockMesh` (`extract.py:183-207`), holding `chan_arrays` (per-channel float arrays keyed by `CH_POS`/`CH_NRM`/`CH_UV`/`CH_TAN`), `flat_index`/`tris`, and the original `raw_vbuf`/`raw_ibuf` for lossless re-encode. `read_block`/`list_blocks`/`extract_block` are the entry points (`extract.py`).

**Transform — the core builders.** `BlockMesh` is the lingua franca every geometry module consumes and produces: `transplant.py`, `island.py`, `interior.py`, `mesh.py`, `orphangate.py`, `palette.py`, `placement.py`, `rimretile.py`, `texgates.py`, `water.py`, and `blendio.py` all `import BlockMesh` (or its `CH_*` channel constants) directly from `extract.py` (confirmed via `grep -l "BlockMesh" *.py`). Three main producers:
- `transplant.py:transplant`/`morph_in_place`/`transplant_region` — carries a *real* donor block's `BlockMesh` verbatim into a custom cell, then applies a chain of "tweak" objects (`TileRetexture`, `GroundRetile`, `VertexDisplace`, `RowInsert`, `SeaBump`, etc., all defined in `transplant.py`) that mutate copies of it.
- `island.py:build_landmass`/`landmass` — synthesizes a wholly new `BlockMesh` per block via Delaunay triangulation (`_delaunay`, `island.py:158`) plus `grassland.py`-sourced UV/relief data, gated through `placement.py`.
- `mesh.py` — the lowest-level synthetic-mesh factory (`island_block_mesh`, `blob_cliff_block_mesh`, `stub_terrain_mesh`, `flat_block_mesh`) and the generic mutator toolkit (`deform_radial`, `flatten_region`, `retarget_tiles`) that `interior.py`/`island.py`/`entrance.py` build on.
- `coastmorph.py` — takes a *transplanted* `BlockMesh` (via `transplant.py`'s tweak-list contract, `coastmorph.py:31`) and rebuilds coastal sub-regions (cliff walls, beach arcs, sand bands) in place, returning more tweaks for `transplant.transplant` to apply — it never touches `extract.py` mesh reads directly except for `decode_id`/`encode_id`.

**Verification (a parallel gate layer, not a data-flow stage).** `placement.py` (ground-query simulator), `texgates.py` (UV/area gates), and `orphangate.py` (fringe-triangle classification) all consume a built `BlockMesh`'s tris/UVs and raise `ValueError` or return census dicts; none write anything. They are invoked from *inside* `island.py`/`interior.py`/`transplant.py` build functions, not as separate pipeline stages.

**Egress — Python object → deployable mod.** The terminal write is `mesh.py:write_ff9mesh` (raw bytes) and `mesh.py:deploy_override`/`deploy_donor_sidecar` (`mesh.py:176-193`), which places a `.ff9mesh` file at `<game>/<mod_folder>/<override_relpath(disc,x,y,lod,part)>` for the custom engine's `WorldMeshOverride` loader to pick up loose, bypassing the AssetBundle pipeline entirely (`mesh.py:16-19` docstring). Every builder ultimately funnels its finished `BlockMesh` through this one write seam; `cli.py:_cmd_world_deploy` (`cli.py:3693`) is the CLI entry that calls it directly, while `world-transplant`/`world-island`/etc. call it via their own deploy helpers (e.g. `interior.py:deploy_mountain_parts`, `interior.py:deploy_changed`).

**A second, disjoint pipeline** exists for random encounters: `worldpack.py`'s `Discmr` codec reads/writes `discmr.img` (a baked binary encounter table), entirely independent of `BlockMesh`/geometry — it is reachable only via `world-encounters` (`cli.py:5252`, `from .world import worldpack as WP`).

## 3. CLI verb → module map

Derived from `cli.py` `set_defaults(func=...)` (`cli.py:7923-8966`) cross-referenced with each handler's `from .world import ...` line:

| Verb | Handler | Primary module(s) |
|---|---|---|
| `world-extract` | `_cmd_world_extract` (`cli.py:3662`) | `extract` (`cli.py:3664`) |
| `world-deploy` | `_cmd_world_deploy` (`cli.py:3693`) | `extract`, `mesh` (`cli.py:3697`) |
| `world-locate` | `_cmd_world_locate` (`cli.py:3814`) | `locate` (`cli.py:3818`) |
| `world-retarget` | `_cmd_world_retarget` (`cli.py:3866`) | `extract`, `mesh`, `discmirror`, `locate`, `entrance.cell_to_block` (`cli.py:3870,3886,3895,3896`) |
| `world-mesh-export` | `_cmd_world_mesh_export` (`cli.py:3919`) | `blendio` (`cli.py:3921`) |
| `world-mesh-build` | `_cmd_world_mesh_build` (`cli.py:3955`) | `blendio`, `extract.decode_id` (`cli.py:3957,3972`) |
| `world-texture-palette` | `_cmd_world_texture_palette` (`cli.py:3992`) | `palette` (`cli.py:3994`) |
| `world-atlas-extract` / `-catalog` / `-reskin` / `-add-tile` | (`cli.py:4011,4031,4835,4848`) | `atlas` |
| `world-terrain` | `_cmd_world_terrain` (`cli.py:4045`) | `terrain` (`cli.py:4048`) |
| `world-reclaim` | `_cmd_world_reclaim` (`cli.py:4103`) | `terrain`, `extract` (`cli.py:4106,4136`) |
| `world-coast` | `_cmd_world_coast` (`cli.py:4132`) | `terrain` (`cli.py:4135`) |
| `world-rim-retile` | `_cmd_world_rim_retile` (`cli.py:4178`) | `rimretile` (`cli.py:4180`) |
| `world-transplant` / `world-morphs` | `_cmd_world_transplant` (`cli.py:4206`), `_cmd_world_morphs` (`cli.py:4467`) | `transplant` (`cli.py:4210`), plus lazily `coastmorph` for `--beach-*`/`--cliff-*` flags (`cli.py:4255,4332`) |
| `world-coastnav` | `_cmd_world_coastnav` (`cli.py:4501`) | `coastnav` (`cli.py:4504`) |
| `world-island` | `_cmd_world_island` (`cli.py:4537`) | `island`, `grassland.GROUNDS` (`cli.py:4542-4543`) |
| `world-forest` / `world-hill` / `world-mountain` | `_cmd_world_forest/hill/mountain` (`cli.py:4623,4657,4708`) | `interior` (`cli.py:4627,4661,4712`) |
| `world-mirror` | `_cmd_world_mirror` (`cli.py:4755`) | `discmirror` (`cli.py:4760`) |
| `world-water` | `_cmd_world_water` (`cli.py:4776`) | `water` (`cli.py:4779`) |
| `world-mesh-trim` | `_cmd_world_mesh_trim` (`cli.py:4867`) | (uses `blendio` machinery, `cli.py:4870`) |
| `world-entrance` | `_cmd_world_entrance` (`cli.py:4888`) | `entrance` (`cli.py:4893`) |
| `world-fuse` | `_cmd_world_fuse` (`cli.py:5026`) | `fuse`, `transplant`, lazily `coastmorph` (`cli.py:5031,5073`) |
| `world-environment` | `_cmd_world_environment` (`cli.py:5125`) | `environment` (`cli.py:5130`) |
| `world-minimap` / `world-rename-markers` | `_cmd_world_minimap`/`_cmd_world_rename_markers` (`cli.py:5157,5178`) | `navimap` (`cli.py:5159,5182`) |
| `world-encounter-rate` | `_cmd_world_encounter_rate` (`cli.py:5216`) | `encounter` (`cli.py:5221`) |
| `world-encounters` | `_cmd_world_encounters` (`cli.py:5248`) | `worldpack` (`cli.py:5252`) |

`islandbeach`, `placement`, `texgates`, `orphangate`, `meshedit`, `grassland`, and `coastscan` have **no dedicated CLI verb** — they're reachable only as libraries other builders call into (see §1/§4).

## 4. Architectural observations (facts, not recommendations)

- **God modules, by size and by internal fan-out.** `coastmorph.py` (6880 LOC) has 69 top-level `def`/`class` symbols, 47 of them (68%) leading-underscore private helpers never exported (counted via `grep -c "^def \|^class "` + docstring-name pattern). `transplant.py` (4169 LOC) has 55 top-level symbols including 9 nested "tweak" classes (`TileRetexture`, `GroundRetile`, `PatchRecover`, `VertexDisplace`, `RowInsert`, `RowInsertZ`, `SpillClip`, `SpillClipZ`, `DropTris`, `EmitTris`, `SeaBump`). Both single files each encode what their own docstrings describe as multiple distinct "rungs"/pillars (cliff-bump, cliff-headland, beach-mint, band-convert, sand-rebuild, cap-rebuild inside `coastmorph.py:1-33`).
- **Duplicated point-in-polygon primitives.** Point-in-polygon is independently reimplemented at least 6 times across the package rather than sharing one function: `coastmorph.py:58` (`_pip_xz`) and `coastmorph.py:68` (`_in_poly`), `interior.py:265` (`pip`), `island.py:158` (`_pip`), `islandbeach.py:537` (`_pip`), `mesh.py:1039` (`_point_in_polygon`), `transplant.py:3783` (`_point_in_poly`).
- **Duplicated ear-clipping.** `meshedit.py:355` defines a general-purpose `earclip`, but `coastmorph.py:1182` independently defines its own `_ear_clip` rather than importing `meshedit`'s — `coastmorph.py` has no import of `meshedit` at all (confirmed against its full import block, `coastmorph.py:34-42`), even though it is the module most likely to need generic polygon-fill primitives.
- **Duplicated `_sea5_deepsets`.** Two independent same-named functions exist: `rimretile.py:269` and `transplant.py:2468`, with no shared import between the two files for this symbol.
- **A cross-module circular dependency, mitigated by deferred imports.** `coastmorph.py` imports `transplant` at module top level (`coastmorph.py:40`, `from . import transplant as TR`), while `transplant.py` imports `coastmorph` only lazily, function-local (`transplant.py:358,585`, `from . import coastmorph as CM`) — the reverse edge is deferred specifically to avoid an import cycle at module-load time.
- **`coastmorph.py` reaches into another module's private helper.** `coastmorph.py:42` does `from .island import _delaunay` — a leading-underscore (private-by-convention) symbol imported across a module boundary.
- **`meshedit.py` sits under `transplant.py` only, not under `coastmorph.py`.** Despite `meshedit.py`'s docstring calling itself "the coast-edit primitives" (`meshedit.py:1`), its only intra-package consumer is `transplant.py` (three lazy imports: `transplant.py:3368,3827,4148`); `coastmorph.py` — the module that does the actual coast editing — never imports it.
- **A parallel "gate" layer with no CLI surface.** `placement.py`, `texgates.py`, and `orphangate.py` have zero entries in `cli.py`'s `set_defaults` table; they are pure internal libraries invoked from inside `island.py`/`interior.py`/`transplant.py` build functions (e.g. `transplant.py:2935,3593` import `placement`; `texgates.py`/`orphangate.py` results surface only as a nested `summary["report"]["texgates"]` dict printed by `world-transplant`, `cli.py:4595`). This is a genuine layering split between the 31 CLI-addressable authoring verbs and an unaddressable internal verification layer.
- **`islandbeach.py` (546 LOC) has zero direct test coverage.** No `tests/` file imports it or calls `plan_arc`/`build_beach` directly (`grep -rl "plan_arc\|build_beach" tests/` returns nothing), and no test exercises the `--beach`/`--beach-pins` CLI flags on `world-island`/`world-transplant` (`grep -rn '"--beach"' tests/` returns nothing). It is reached only transitively, if at all, through `island.py:294,542` and `transplant.py:359,665`'s conditional lazy imports.
- **Foundation vs. consumer layering is otherwise clean at the module-import level.** `extract.py` and `mesh.py` import only `config` (the package root) — no other `world/*` sibling — making them the package's true leaf/foundation layer; `grassland.py`, `meshedit.py`, `placement.py`, `environment.py`, `encounter.py`, `navimap.py` (module scope), `atlas.py` (module scope), and `palette.py` (module scope) likewise have zero *module-level* intra-package imports (several do lazy function-local imports of `extract`/`mesh`, confirmed above).
- **Test organization mirrors most, not all, CLI verbs.** `ff9mapkit/tests/` has one file per verb-family for the majority of modules (`test_world_terrain.py`, `test_world_coastnav.py`, `test_world_island.py`, `test_world_interior.py`, `test_world_transplant.py`, `test_coastmorph.py`, `test_world_water.py`, `test_world_fuse.py`, `test_world_rimretile.py`, `test_world_orphangate.py`, `test_world_texgates.py`, `test_world_palette.py`, `test_world_atlas.py`, `test_world_environment.py`, `test_world_encounter_rate.py`, `test_discmirror.py`/`test_discmirror_auto.py`, `test_navimap_worldmap.py`/`test_navimap_rename.py`, `test_worldpack.py`), but `blendio.py`, `coastscan.py`, `entrance.py`, `grassland.py`, `locate.py`, and `placement.py` have no dedicated test file and are exercised only incidentally through other modules' tests (e.g. `test_world.py`, `test_world_mesh_deploy.py`, `test_nameplate_band.py`, `test_worldexit.py`, `test_sea4_under_land.py` — confirmed via targeted `grep -rl` against each module name across `ff9mapkit/tests/`).

---

## R2: 3D data model & geometry contracts
# Scout R2 — 3D Data Model & Geometry Contracts

## 1. In-memory representation (`world/extract.py`, `world/mesh.py`)

Geometry is **plain Python lists of lists**, not numpy, not a dataclass-per-vertex. The single container is `BlockMesh` (`world/extract.py:182-219`), a `@dataclass` holding:

- `chan_arrays: dict` — `{channel_id: [[float,...], ...]}`, one list-of-floats per vertex per channel. Channel ids are Unity-5 vertex-stream indices: `CH_POS, CH_NRM, CH_UV, CH_TAN = 0, 1, 3, 7` (`extract.py:29`).
- `channels: dict` — `{channel_id: (byte_offset, dimension)}`, the interleaved-vertex layout (only used for round-trip against `raw_vbuf`).
- `flat_index: list[int]` — the raw index buffer.
- `tris: list[list[int,int,int]]` — the index buffer regrouped in 3s.
- `verts/normals/uvs/tangents` are `@property` accessors (`extract.py:205-219`) that just return `chan_arrays.get(CH_*)` — no separate storage, no caching, so any in-place mutation of `bm.verts` (e.g. `mesh.lift_block`, `mesh.deform_radial`) mutates `chan_arrays[CH_POS]` directly.
- `raw_vbuf`/`raw_ibuf: bytes` — the original Unity bytes (kept for provenance, unused by synth builders which pass `b""`).
- `use32: bool`, `submeshes: list`.

**Winding** is not a stored field — it is a derived property of vertex order, tested by the geometric cross product `(b-a)×(c-a)` in XZ (e.g. `mesh.py:693`, `placement.py:60-64`, `meshedit.py` throughout). The engine reads the same convention, so every builder computes it live rather than storing an orientation flag.

**IDALL** (per-triangle event/area/topograph/flags) is *not* a separate channel — it is packed into `tangent.x` as a float-encoded int (`encode_id`/`decode_id`, `extract.py:65-87`), one value per corner vertex, read at the triangle's first index (`retarget_tiles`, `mesh.py:1109-1110`; `placement.place`, `placement.py:56`). This is an engine convention (`WMBlock.cs:231`, `tangent.x` = `mapid`), not a kit invention.

## 2. The `.ff9mesh` on-disk format

Defined and documented at `world/mesh.py:1-13`: a raw dump of `BlockMesh` channels, little-endian:

```
b"F9WM" | version i32 | vertexCount i32 | indexCount i32 | flags i32
vertices v*3 f32 ; normals v*3 f32 (flags&1) ; uv v*2 f32 (flags&2) ; tangents v*4 f32 (flags&4) ; indices i*i32
```

`write_ff9mesh` (`mesh.py:60-95`) and its inverse `read_ff9mesh` (`mesh.py:98-119`) are the only codec. Deployment target path: `override_relpath` (`mesh.py:148-154`) → `<mod>/FF9_Data/WorldMap/Disc{D}/{lod}/r{Y}/Block[{X}][{Y}] {part}.ff9mesh`, loaded loose by the custom engine's `WorldMeshOverride` (bypasses the AssetBundle pipeline entirely — this is the s34 fork-gate/patch mechanism, not stock Memoria).

## 3. Write-time assertions (enforced in code, not just documented)

- **THE UNINDEXED CONTRACT** — `write_ff9mesh`, `mesh.py:71-74`:
  ```python
  assert bm.vcount == len(bm.flat_index), (...)
  ```
  This is a hard Python `assert` at the actual write call site — it fires on `write_ff9mesh`/`deploy_override`, not merely documented. Memory file `project-ff9-worldmesh-unindexed-contract.md` states the same law and correctly attributes enforcement to this line; **reconciled, current, and matches code exactly** (line numbers 71-74 confirmed live). Note: this assert only checks `vcount == icount`, i.e. it detects the *symptom* (a mismatched buffer), not the specific failure mode (shared verts appended) — a caller could still emit `vcount == icount` verts that are non-unique-per-triangle and pass this assert while being wrong in a different way; the assert is a necessary, not sufficient, guard.
- **Off-grid write refusal** — `require_block_in_grid` (`mesh.py:43-57`), called from both `deploy_override` (`mesh.py:193`) and `deploy_donor_sidecar` (`mesh.py:169`): raises `ValueError` before any bytes are written if `(x,y)` falls outside the fixed `24×20` block grid (`GRID_COLS, GRID_ROWS = 24, 20`, `mesh.py:32`). This is enforced at the *lowest* write layer deliberately (per the docstring, so a per-call-site retag can't skip it).
- **`obj_to_blockmesh`/`build_from_obj` OBJ-import guard** — `blendio.py:209`: `if not V: raise ValueError("OBJ has no vertices")`.
- **`atlas._part_name`** (`atlas.py:36-38`) and multiple `world-` verb entry points (`water.py:353-359, 422-437, 588-595`) raise `ValueError` on out-of-grid cell/donor coordinates before any mesh work happens — same `GRID_X/GRID_Y` bound reused from `mesh.py`.
- **`meshedit.py` construction-time guards** are real `raise ValueError`s inside the geometry primitives themselves (not gates run afterward): `flow_ok`/degenerate-segment checks in `seaward` (`meshedit.py:80-81`), `seat_transform`'s degenerate-chord check (`meshedit.py:156-157`), `miter_offset`'s length-mismatch check (`meshedit.py:123-124`), `sweep_wall`'s walk-visibility (`min_ny`) and texel-density checks (`meshedit.py:319-328`) which actively refuse to return a `WallSweep` if the geometry would be non-walkable or badly UV-streaked, `flat_patch`/`lattice_patch`'s "ear-clip introduced a vertex off the ring" weld-exactness check (`meshedit.py:726-728`), `retag_flat`'s winding-flip refusal (`meshedit.py:1006-1010`), and `boundary_cycles`'s edge-budget non-termination guard (`meshedit.py:654-656`). These are load-bearing, not decorative — several docstrings explicitly narrate the playtest/measurement that motivated each one.

## 4. Reconciling the memory files against current code

- **`project-ff9-worldmesh-unindexed-contract.md`**: accurate. `write_ff9mesh` line numbers (71-74 for the assert, 60 for the def) match; the described failure modes (vcount>icount overruns the index buffer at `WMBlock.AddWalkMesh`, vcount<icount builds `TriangleNormals` short) are stated as engine-source facts the kit assert protects against, and the kit-side enforcement claim is verified correct.
- **`project-ff9-sea-sheet-laws.md`**: the WINDING LAW and "normals are a byte constant" claim are reflected in code as defaults, not universal enforcement. `flat_patch(..., winding: float = -1.0)` (`meshedit.py:677`) defaults to stock's `-1` and actively **flips** a triangle whose cross sign disagrees (`meshedit.py:721-722`) — so for this specific builder the law is self-correcting, not merely asserted. `retag_flat`, by contrast, **raises** rather than auto-fixing when a winding mismatch is detected (`meshedit.py:1006-1010`) — the docstring explains why: a re-shade should never silently flip a face. Neither function *validates the caller's supplied normal* against the byte-constant claim — normals are passed straight through (`meshedit.py:734`, `meshedit.py:885-887`); getting the normal right is the caller's discipline, not a code-enforced gate. This matches the memory's framing ("take both from the neighbouring sheet") but confirms it is convention, not an assert.
- **`project-ff9-sea4-under-land-law.md`**: this file documents an *engine* mechanism (ray-origin ceiling, `WALK_RAY_START`/`SKY_RAY_START`) that is faithfully reproduced in `placement.py` (`WALK_RAY_START = 2.34375`, `SKY_RAY_START = 400.0`, `placement.py:34-36`, applied at `placement.py:49`). The described fix (cutting Sea4 under land, not adding a beach) lives in `meshedit.py`'s excise/patch primitives (`flat_patch`, `boundary_cycles`, `vertex_components`) but is explicitly **not yet promoted into `mesh.py`/`meshedit.py`'s public surface** — the module docstring says so directly: *"Deliberately NOT here yet: the sea cut (`cut_sea_under`), which is entangled with per-part world mesh semantics… see `studies/path-d-new-world/vcorner_sea_cut.py`"* (`meshedit.py:43-45`). So the sea4-under-land fix as of this reading is a **study script, not a kit-owned reusable function** — the memory file's own 2026-08-02 update (a per-CLASS cut, not per-site) is consistent with this: it's still framed as a bespoke bench operation, not a general library entry point.

## 5. Coordinate systems (`world/locate.py`, `world/placement.py`, `world/extract.py`)

Three nested frames, confirmed in code:

1. **World XZ** (global, floats) — the frame every geometry function (`meshedit`, `mesh.deform_*`, `texgates`) operates in. `+Y` is up.
2. **Block** — a fixed `24×20` grid of `64u` cells (`extract.py:37`, `mesh.py:32`). `block_world_origin(x, y) -> (x*64, -y*64)` (`extract.py:40-44`) — **Z is negated**: block row `y` advances toward `-Z`. A block's local verts span `x∈[0,64], z∈[-64,0]`. This is stated as engine-verified (`WMWorld.cs`) plus empirically corroborated, not inferred.
3. **World-map "cell"** — a *coarser, independent* `32u` unit used only by the entrance/event dispatcher, not by mesh geometry: `w_worldPos2Cell = (int)(x/32), (int)(z/-32)` (`locate.py:7`). Two blocks = one cell-row conceptually is *not* a fixed ratio the kit hardcodes as a constant; it is derived directly from the packed cell tag `0x8000|(cellZ<<8)|(cellX<<2)|event` (`locate.py:6`), decoded by `unpack_cell_tag`/`cell_to_block` in `entrance.py` (referenced but not fully read in this pass — `locate.py:197-228` calls `cell_to_block`/`cell_world_center` from that module).

**Wrapping**: block indices are never modular in code — they are hard-bounded (`0..23`, `0..19`) by `block_in_grid`/`require_block_in_grid` (`mesh.py:37-57`), i.e. off-grid is a *refusal*, not a wrap. The memory file `project-ff9-overworld-placement-rules.md` documents a *different* wrap hazard entirely: the **lattice-edge teleport trap** (a float barycentric rejection at exactly-4u-aligned XZ, §2) — that's a numerical-precision edge case in `WMPhysics.intersect3D_RayTriangle`, reproduced by `placement.place`'s own barycentric test (`placement.py:69-73`, `w0/w1/w2` with a `-1e-9` slack), not a coordinate-wrap bug.

**Scale**: `BLOCK_SIZE = 64` (`extract.py:37`) is the single defined unit constant; the memory file corroborates it and adds the derived facts `speed_move=112 → ~0.44u/frame` and the `4u` lattice used by Sea4/ground-UV tiling (`CELL = 4.0`, `texgates.py:75`) — those two "4u" and "64u" grids are distinct and both real (mesh-block grid vs. UV/texture-tiling grid).

**Ray origins / ground-query** (`placement.py:34-36, 44-78`) are a byte-exact reproduction of the engine's `w_nwpHit`, cross-checked against the memory file's numbered rule list — confirmed matching: infinite-descent walk rays (`ff9.rayDistance` dead-code, `placement.py:9-10`), sky-cast at `y+400`, mesh-registration-order-wins-not-nearest (`placement.py` reads `meshlist` in caller-supplied order and returns on first hit — `place`, lines 52-77), first-triangle-in-buffer-order wins, `ny > 0.1` geometric-winding filter, `IDALL_SKIP = {4078, 4088, 2040}` (`placement.py:33`).

## 6. Texture/UV → atlas binding (`atlas.py`, `palette.py`, `texgates.py`)

- Two **shared, global** `1024×1024` atlases (`terrain`, `object`), `ATLAS_NAMES`/`ATLAS_SIZE` (`atlas.py:25-26`). A face's UV alone selects its tile; topograph does **not** select texture — it's a movement/encounter tag only (`palette.py:5-6`).
- `palette.py` builds a **learned** `topograph -> [(uv_triplet, count)]` map by sampling real donor blocks (`sample_donor_faces`, `palette.py:37-59`; `build_palette`, `palette.py:62-97`), cached to `.ff9palette_<part>_disc<N>.json`. New/synthetic geometry gets `[0,0]` UVs by default; `apply_palette_uvs` (`palette.py:121-156`) stamps a real donor triplet onto any all-zero-UV triangle, `stamp_uv_rect` (`palette.py:159-207`) stamps an explicit custom rect with planar (`box`) or crude (`corner`) projection.
- **UV validity gates live in `texgates.py`** and are the clearest example of "documented-and-partially-enforced but not asserted": every gate function (`zero_uv_area_gate`, `one_window_gate`, `family_rect_gate`, `sea_plan_gate`, `texgates.py:218-451`) returns a dict shaped `{ok, warn, enforced, detail, ...}` via the shared `_gate()` helper (`texgates.py:202-212`):
  ```python
  d["ok"] = bool(allow or (not enforce) or not dirty)
  ```
  **Default is `enforce=False`**, meaning a dirty result still reports `ok=True` (`warn=True`) unless the caller explicitly passes `enforce=True`. These are **not** write-blocking asserts by default — they are opt-in checks a caller must wire in and turn on. `one_window_gate` additionally self-disables (`skipped=True`, passes) unless the caller supplies the exact `(quad, ori)` field it minted with (`texgates.py:258-262`) — it explicitly refuses to "judge blind" per the calibration measurements documented in its own module docstring (3.2%-18.5% false-positive rate on real stock ground if judged without that context).

## 7. Validation enumerated: enforced-in-code vs. documented-only

| Check | Enforced (assert/raise at call site) | File:line | Merely documented (law/memory) |
|---|---|---|---|
| vcount == index count (unindexed contract) | ✅ hard `assert` | `mesh.py:71-74` | — |
| Block coords inside 24×20 grid | ✅ `raise ValueError` | `mesh.py:37-57`, called `mesh.py:169,193` | — |
| OBJ import has vertices | ✅ `raise ValueError` | `blendio.py:209` | — |
| `sweep_wall` walk-visibility (min_ny) / texel density | ✅ `raise ValueError` | `meshedit.py:319-328` | — |
| `flat_patch`/`lattice_patch` weld-exactness (no off-ring vertex) | ✅ `raise ValueError` | `meshedit.py:726-728` | — |
| `retag_flat` winding must match target | ✅ `raise ValueError` | `meshedit.py:1006-1010` | — |
| Sea4/geometry winding sign | ⚠️ auto-corrected (silent flip), not asserted | `meshedit.py:721-722` (flat_patch), `mesh.py:691-694` (blob_cliff auto-orient) | Stated as a hard law in `project-ff9-sea-sheet-laws.md` |
| Sea normals = donor byte constant, not (0,1,0) | ❌ no check — caller must pass the right value | n/a | `project-ff9-sea-sheet-laws.md` only |
| Zero-UV-area / bit-identical UV stamp | ⚠️ gate exists, **WARN by default** | `texgates.py:218-236`, `_gate` at `202-212` | Requires caller `enforce=True` to hard-fail |
| One-window-per-tri UV coherence | ⚠️ gate exists, **skips entirely** without caller-supplied `(quad,ori)` field | `texgates.py:242-293` | — |
| Family mains-rect UV membership | ⚠️ gate exists, WARN by default | `texgates.py:299-329` | — |
| Sea plan-disjoint (Y-order / Sea4 uniformity / real-sea overlap) | ⚠️ gate exists, WARN by default | `texgates.py:335-432` | — |
| Sea4-under-land cut (the actual fix) | ❌ not a library function yet | — | `meshedit.py:43-45` docstring explicitly defers it to a study script; `project-ff9-sea4-under-land-law.md` |
| Ground-query ray semantics (placement) | N/A — this is a simulator, not a write gate; used offline only | `placement.py` whole file | `project-ff9-overworld-placement-rules.md` |
| Weld/hairline-crack audit (`weld_audit`) | ⚠️ reusable function, returns offending pairs; caller must `assert == []` | `mesh.py:1244-1271` | — |

The load-bearing distinction the codebase itself draws (per `texgates.py`'s docstring and `_gate()` shape) is: **every geometry-shape check that would reject bad output is opt-in and warn-by-default** — nothing in `write_ff9mesh`/`deploy_override` calls `texgates` or `weld_audit` automatically. The only checks that are *unconditionally* enforced at the actual byte-write boundary are the unindexed-contract assert and the off-grid-block raise; everything about UV/texture/sea-shape correctness is a separately-invoked, separately-enabled gate that a generator (`island.py`, `transplant.py`, etc.) must choose to call and choose to set `enforce=True` on.

---

## R3: Authoring workflow & feedback loop
# Scout R3 — Authoring Workflow & Feedback Loop (Overworld)

## 1. The skill's prescribed workflow and guard rails

`.claude/skills/authoring-ff9-overworld/SKILL.md` is a **thin router**, explicitly not a recipe book (`SKILL.md:6`: "do NOT recopy opcode tables, TOML schemas, or coast laws"). Its structure:

- **Read-first gate (mandatory, before ANY coast/beach/cliff/transplant/morph edit)**: open `references/coast-laws.md` AND memory `project-ff9-overworld-coast-mosaic` (`SKILL.md:10-16`). Rationale stated verbatim: "Bad geometry under the spawn bricks the save (black screen, no log)." The memory file's `## LAW INDEX` (lines 13-164, ~134 named laws) is called "AUTHORITATIVE"; the skill's own `references/coast-laws.md` is flagged as a **stale 2026-07-11 snapshot** that undercounts current laws — "When the two disagree, the memory wins" (`SKILL.md:14`).
- **The save-brick hazard** is called out as a hard safety rule, quoted from `project-ff9-overworld-actor-brick`: editing geometry under/near the player can brick a save with a silent black screen, baked into the save itself — deleting the override afterward does not fix it. Recovery = load a field/town save or New Game; avoidance = never save on an edited cell (`SKILL.md:15`).
- **RESHAPE-not-OVERLAY law** (`SKILL.md:22-24`): "RESHAPE the stock terrain verts; do NOT OVERLAY a new mesh" — an overlay above intact ground never wins the down-raycast and becomes non-walkable decoration.
- **s34 override mechanism**: loose `.ff9mesh` files per block-part override real bytes; `--in-place` touches only the changed parts; revert = delete the loose files; two build gates (IN-PLACE-FRAME, BOUNDS) (`SKILL.md:26-28`).
- **Disc-4 mirror is automatic**, not a remembered step, since 2026-07-19 — every world-override writer runs `discmirror.auto_mirror` as a post-step, cell-scoped to just-written paths; `--skip-mirror` opts out (`SKILL.md:30-32`).
- Sections walk through each productized capability in turn: terrain reshape/reclaim/coast-carry (`SKILL.md:34-36`), transplant/fuse/grow plus the **two automatic water-carry gates** (effective-prefab gate, Wang-carry gate) (`SKILL.md:38-42`), coast-morph/beach-mint ladders (`SKILL.md:44-46`), the three interior-relief verbs mountain/forest/hill (`SKILL.md:48-56`), `world-minimap` (`SKILL.md:58`), and entrances/buildings/vehicles/world-states (`SKILL.md:60-62`).
- Closes with a Layer-3/Layer-2 pointer list rather than inlining content (`SKILL.md:64-67`).

Companion files under the skill dir: `references/coast-laws.md`, `references/overworld-engine.md`, `references/terrain-entrance.md` (glob confirmed, not opened in full — the skill explicitly discourages treating them as current).

## 2. The iteration loop

**No CLI verb takes a `field.toml`.** Unlike field authoring, the overworld lane is driven entirely by ~32 `world-*` subcommands defined in `ff9mapkit/ff9mapkit/cli.py` (`_cmd_world_*` handlers at lines 3662-5248, e.g. `world-deploy:3693`, `world-terrain:4045`, `world-transplant:4206`, `world-island:4537`, `world-forest:4623`, `world-hill:4657`, `world-mountain:4708`, `world-mirror:4755`, `world-entrance:4888`, `world-fuse:5026`, `world-minimap:5157`). Each verb reads live game bytes (or an already-deployed mod folder) and writes loose `.ff9mesh`/override files directly into `<mod-folder>/FF9_Data/WorldMap/...` — **there is no `tools/deploy_field.py`-equivalent wrapper for world content**; the CLI verb *is* the deploy step, gated by a required `--mod-folder` flag on nearly every writer (e.g. `cli.py:7944`, `8164`, `8495`, `8573`).

A concrete, real, shipped example is `ff9mapkit/examples/continent-v1/README.md:15-25` — a **four-command deploy sequence** for composing an archipelago:
```
world-fuse continent_v1.toml --mod-folder FF9CustomMap-world --dry-run   # validate
world-fuse continent_v1.toml --mod-folder FF9CustomMap-world             # deploy
world-island --mod-folder FF9CustomMap-world --center 344,-1152 --radius 46 --lobes 3 --seed 55
world-minimap --mod-folder FF9CustomMap-world                            # refresh the big map
```
followed by: "Relaunch the game (or exit + re-enter the overworld) to apply — loose world assets aren't hot-reloaded." A typical "add a mountain to an island" job composes further: `world-island` (or an already-deployed island) → `world-mountain --near WX,WZ` or `world-forest --near WX,WZ` (both mentioned at `OVERWORLD_ENGINE.md:787,801`) → `world-coastnav` to restamp vehicle-legality after any coastal edit (`cli.py:8569-8583`) → `world-minimap` to refresh the pause-map composite (`cli.py:8899-8918`).

**Dedicated mod folder rationale** (README.md:27-30): overworld content is kept in its own stacked `FolderNames` entry (`FF9CustomMap-world`) specifically because campaign/journey deploys wholesale-replace their target folder — this isolates world state from field-content churn (also documented in the repo-root CLAUDE.md §3).

**Relaunch vs hot reload — this is the single biggest behavioral difference from field authoring.** Field content supports `~ → Reload field` hot reload (repo CLAUDE.md §4). Overworld content essentially never does. A `grep` for "RELAUNCH"/"re-enter the world" across `cli.py` turns up dozens of per-verb print statements, all variants of the same fact:
- `cli.py:3808`: "RELAUNCH the game (a new loose asset isn't hot-reloaded), reach the disc-%d overworld, walk to the edit."
- `cli.py:3988`: "RELAUNCH or re-enter the overworld."
- `cli.py:4127`, `4405`, `4463`, `4830`: "Needs the CUSTOM engine (...). RELAUNCH (or exit+re-enter the overworld)."
- `cli.py:5172`: `world-minimap` needs a full relaunch AND (if MoguriMain also ships a map PNG) manual edits to **both** `FolderNames` and `Priorities` in `Memoria.ini`, "game+launcher closed."

So the practical loop is: edit → run one or more `world-*` verbs against a mod folder → **exit to the overworld (minimum) or fully relaunch FF9 (for anything registering a new asset/id)** → visually/behaviorally check in-game → `tools/game_snap.ps1` to capture a PNG for the agent to read (`tools/game_snap.ps1:1-8`, "The agent cannot see the running game directly; this closes most of that gap with static frames... run it while FF9 is up (windowed/borderless) and Read the PNG") → human confirms.

## 3. Visualization inventory

No live viewport exists anywhere in this pipeline. Everything is a static raster generated from mesh bytes, at three tiers of "first-class-ness":

| Tool | Scope | First-class or study-local | What it shows |
|---|---|---|---|
| `world-minimap` (`cli.py:8899`, `world/navimap.py`) | Whole-map | **First-class CLI verb** | Composites the mod folder's deployed land onto the real in-game `world_map_full_all.png` pause-map projection (1536×1280, engine-derived); the only visualization output that ships INTO the game itself. |
| `ff9mapkit/ff9mapkit/world/placement.py: census()` (`placement.py:81`) | Per-cell | **First-class kit function**, used as a build gate not a picture | Offline down-raycast ground-query simulator; not an image, but the numeric oracle ("MISS must be 0 everywhere," `placement.py:24`) every world writer runs before deploy. |
| `studies/overworld-topography/canvas_render.py` | Whole 24×20 block grid | Study-local | Renders `out/world-design/canvas.json` to a PNG: stock land (grey), each live cluster in its own color, reserved-but-empty study benches (hatched), free ocean (pale blue), best free-radius circle overlaid — a design/allocation map, not a render of geometry (`canvas_render.py:1-6,55-59`). |
| `studies/overworld-topography/artifact_bucket_render.py` | One artifact window | Study-local | Same triangles as its zoom sibling, solid-colored by GroundRetile classification bucket (mains=tan, wall=gray, sand=yellow, recovered=magenta, foam=cyan) — a debugging aid to attribute a visual defect to a code path (`artifact_bucket_render.py:1-4`). |
| `studies/overworld-topography/artifact_zoom_render.py` | One 2×2-block window | Study-local | Textured re-render at a specific site (19,17) using the shipped atlas texture recipe, plus a bucket-colored overlay — same debugging genre, single-incident script (`artifact_zoom_render.py:1-4`). |
| `studies/path-d-new-world/render_gate.py` | Bench block set | Study-local, but **the most game-faithful renderer that exists** | An offline **textured software renderer** over bench meshes, explicitly engine-faithful: UNLIT (Memoria trace: "WorldMap/Terrain binds no normal"), plain 0..1 UV over the real 1024² atlas, opaque geometric sea layers, NEAREST sampling, alpha-0 texels rendered white per the blank-tile law, back-face culling via a game-eye convention (`render_gate.py:1-14`). Modes: `render <baseline\|v1\|v2\|live>`, `calibrate` (fixed-camera corpus diff), `flow` (UV-gradient orientation/handedness check) (`render_gate.py:18-27`). |
| `studies/overworld-topography/bench_audit.py` | Deployed bytes | Study-local | Gate T (tessellation, scoped to the grass class) + walkability pass reading engine constants directly from Memoria source (step-height ceiling 2.34375u, WMPhysics raycast skip rule) (`bench_audit.py:1-19`). |
| `studies/path-d-new-world/coast_lint.py` (+ `walk_sim.py`) | Whole boundary | Study-local | Scores the entire walkable boundary for "catch risk" under a quantised player-heading fan, then **hug-tests** flagged sites with an offline movement simulator — explicitly because "a static score is a hypothesis and the simulator is the oracle" (`coast_lint.py:1-8`). |
| `tools/game_snap.ps1` | Live game window | First-class, cross-pillar | The only tool that shows the *actual rendered game* — PrintWindow capture of the live FF9 process to PNG, with a black-frame detector for exclusive-fullscreen false negatives (`game_snap.ps1:1-57`). |

The pattern: **exactly one visualization ships as a CLI verb** (`world-minimap`); everything else that shows geometry as pixels is a bespoke, single-purpose script written inside a `studies/` arc to chase one specific defect, then left in place. None of the study renderers are wired into `ff9mapkit/ff9mapkit/`.

## 4. The bench + gates

`studies/path-d-new-world/bench_pipeline.py` (`bench_pipeline.py:1-31`) exists to fix a stated **P0 problem**: the accepted Path D bench was built by "a chain of study scripts, each reading the LIVE install and each anchored to a TIMESTAMPED BACKUP in a gitignored folder shared by every concurrent session" — so re-running the generator silently reverted a hand-tuned corner while every gate stayed green, because the gates score whatever bytes are currently sitting there. Twelve playtests of work sat on that regression before it was caught. Four subcommands: `verify` (anchors exist/self-consistent/hash-match, `bench_pipeline.py:65-95`), `regen` (rebuild OFFLINE from the anchor, never touching the game, `:98-118`), `corner` (build the accepted corner ON the regenerated base via `vcorner_transplant.py stage1`/`stage2`, `:121-137`), `check` (md5-diff the regenerated build against the live owner-accepted bytes and write `bench_manifest.json`, `:140-169`); `all` chains all four (`:182-183`).

`studies/path-d-new-world/terrain_gate.py` is "one command over any terrain change" (`terrain_gate.py:1`), created because the eight gates that finally closed the V-shore corner were previously run by hand in an order held in one person's head — "three of the last four playtest failures happened" because a fix's gate either didn't exist yet or existed but was never wired into the call path it was written for (`terrain_gate.py:3-9`). It runs **10 named gates** across two axes: flow axis = `walk`, `latent`; build axis = `weld`, `cover`, `sea`; look axis = `flow-uv`, `blank`, `holes`, `tjunc`, `peer` (`terrain_gate.py:11-21`, confirmed by the `add(...)` call sites at `:69-106`). Two encoded rules: (1) compare against the **neighbour, not the marginal** — `peer` and `tjunc` are differential by construction because isolated-element scoring already passed defects the owner later caught; (2) **calibrate before judging** — `blank` counts exact blank-paint texels because a looser threshold flagged the owner's own accepted island as defective (`terrain_gate.py:22-28`). Invoked as `py terrain_gate.py [staged|live] [--quick]` (`:29-31`).

`studies/overworld-topography/composite_gates.py` implements the "THE FINAL-COMPOSITE RULE" — consolidates eight generator acceptance predicates previously scattered across earlier per-round scripts, so a generator can run its own final composite and **refuse to emit on any red** (`composite_gates.py:1-9`): `gate_zero_uv_area` (`:140`), `gate_one_window_family_aware` (`:152`), `gate_family_rect_membership` (`:211`), `gate_sea_3predicate` (`:241`), `gate_stage4_plumbing` (`:255`), `gate_stock_envelope` (`:381`), `gate_spike_step_census_empty` (`:482`), `gate_orphan_census_empty` (`:492`). Its envelope-calibration table is measured, not guessed, and documents its own trap: a hard `<=1.41x` UV-stretch ceiling map-wide "would REFUSE the very build the owner accepted after 8 rounds" (`composite_gates.py:34-51`) — hence the split into hard CARRIED-ground / hard SYNTH-density / advisory SYNTH-tail bands.

Lint-adjacent verbs in the shipped CLI: `world-morphs` (the "COAST WINDOW SCANNER" — probes real builders down a depth ladder and prints only lawful morph windows with per-verb ceilings, certified by an in-place dry run, `cli.py:8469-8486`) and `world-coastnav` (vehicle-legality stamping with a `--dry-run` report mode, `cli.py:8569-8583`) are the closest things to first-class "lint" verbs; `coast_lint.py`'s boundary-wide catch-risk scan remains study-local, unexposed via CLI.

## 5. Honest friction inventory (facts, not narrative)

- **The mesh/geometry authoring step itself is scriptable and fast** — one `world-*` command per edit, offline, with no game running required.
- **Every deploy requires leaving the running game state**: at minimum "exit + re-enter the overworld," and for anything registering a new asset/id, a **full relaunch** (`cli.py:3808` and the ~40 other RELAUNCH print sites enumerated in §2). This is categorically worse than field authoring's `~ → Reload field` hot path — there is no hot-reload path for overworld geometry at all.
- **Minimum step count from "I want a hill here" to a verified change, counting only what a human/agent must actually do**:
  1. Read the coast-laws gate (mandatory per skill) if the edit touches shore.
  2. Run the `world-*` verb(s) (often 2+, e.g. island → relief verb → coastnav restamp → minimap refresh, per the continent-v1 example).
  3. Exit/relaunch the game.
  4. Walk to the site in-game (human).
  5. `tools/game_snap.ps1` to capture a PNG (agent-visible check).
  6. Read the PNG.
  7. Ask the human to actually play/walk the terrain, since a screenshot cannot show walkability, catch points, or save-brick risk.
  8. Only the human's playtest verdict closes the loop — the toolkit's own docs state this as policy, not preference (repo CLAUDE.md §2: "I cannot PLAY the game... Behavior and feel still need the human... Never assume it worked because it built.").
  So the floor is **on the order of 6-8 discrete steps**, and it is never fewer than "one relaunch + one human playtest" — there is no offline-only path to a verified answer.
- **The human playtest is the ONLY oracle for**: whether a save bricks (silent black screen, no log, per `SKILL.md:15`); whether a boundary vertex actually catches a moving character (the reason `coast_lint.py` had to build a movement simulator and treat it, not a static score, as ground truth, `coast_lint.py:1-8`); whether the minimap composite actually shows up correctly once `Memoria.ini` `FolderNames`/`Priorities` are hand-edited (`cli.py:5172-5174`); and whether the disc-4 mirror actually took effect on that disc.
- **State invisible until playtest, quantified by the project's own retrospective**: `terrain_gate.py:3-9` records that 3 of the last 4 playtest failures on the V-shore corner arc traced to a gate that either didn't exist or wasn't wired into the path that needed it, and CLAUDE.md §7 separately states a harder number for the same arc — "0 of 13 playtest verdicts were predicted by a gate" (repo CLAUDE.md, Path-D wall arc). `bench_pipeline.py:1-9` separately documents 12 playtests' worth of work sitting invisibly on a regenerate-and-silently-revert bug because every gate scored the bytes present, not the bytes intended.
- **No live viewport exists at any layer** — not in the CLI, not in Blender for this pillar (the skill note confirms Blender integration is for FIELD scenes/models; overworld authoring is CLI-verb driven, per the scout brief and confirmed by the absence of any `world-*` Blender bridge in the skill file). The closest thing to "seeing" a change before relaunch is a study-local offline software renderer (`render_gate.py`) built specifically because no in-engine preview exists, and even that renderer had to reverse-engineer basic facts about the shader model (unlit, no normals) from the Memoria source rather than from any documented spec.
- **The visualization tooling is fragmented, not consolidated**: of the ~10 render/probe scripts inventoried in §3, only one (`world-minimap`) is a shipped CLI verb; the rest are one-off scripts inside `studies/` written to chase a single specific defect and never generalized or wired into the kit, meaning a new defect class typically requires writing a *new* bespoke renderer rather than reusing one.

---

## R4: Constraint landscape (laws + dead ends)
# Scout R4 — Constraint Landscape & Institutional Knowledge Brief

## 1. Overworld-related dead ends (CLAUDE.md §8, lines 236-249)

| Dead end | One-line reason | Superseded by |
|---|---|---|
| **From-scratch massif SYNTHESIS** (`CLAUDE.md:236-237`) | Falsified over 8 rounds — statistics reproduce measured *properties*, never the *look* (THE FORM LESSON) | Carry the real mesh (`world-mountain`) |
| **Terrace wall from the decoded tile LANGUAGE** (`CLAUDE.md:238-240`) | Refuted twice: correct tiles on INVENTED MASSING still fail at form — silhouette, not tile-correctness, is the look's carrier | `studies/path-d-new-world/TERRACE-WALL-PREDICTION.md` |
| **Real content through a synthetic frame** (`CLAUDE.md:241-242`) | Killed both the v3 bend-carry and the dunes label-stamp — a verbatim stamp must carry the MESH (verts+uvs+tangents), not row labels | N/A — carry mesh whole |
| **The beach-mint ladder** (`world-island --beach`, `CLAUDE.md:243-244`) | Falsified over 4 playtests | `(7,17)` ground-retile carry (`world-transplant --ground desert`) |
| **The dunes MINT at small scale** (`CLAUDE.md:245-246`) | Dunes have a size class (≥~130-cell footprint); even genuine stock arrangement quilts on a ~31-cell blob | True mesh carry at real scale |
| **A canyon ISLAND** (`CLAUDE.md:247-248`) | Off-language by THE WALL-CONTEXT LAW — canyon's red band is never open-sea coastal | Guarded at both chokepoints |
| **Mixed-biome as a thin desert ribbon along a line** (`CLAUDE.md:249`) | THE RIBBON FALLACY — stock's ecotone is the margin of a desert *mass*, not a line | Two-ground landmass unit |
| **The self-summon `--action-prompt`/`--nameplate` overworld entrance** | Too timing-fragile | AREA-SWITCH SURGERY (repoint a dead area-switch case) |
| **A no-art camera REFRAME on import** (general, not overworld-only) | Broke faithful pose on every artless fork | Removed entirely |

Two adjacent items worth flagging to reviewers even though not literally in §8: the **v3 bend-carry** (two-level island F, `project-ff9-overworld-interior-topography.md:333-341`) — "tons of jank still... spiky, faces stacked" after 3 rounds, explicitly named **THE FORM LESSON's fourth firing** — and the earlier **crag mini-mesa** on island F ("sharp-peaked mountain... the crag is UGLY," removed). Both read as candidate "just synthesize a mountain procedurally" proposals that a fresh reviewer might re-propose; both are closed.

## 2. Coast law index (compact digest of `project-ff9-overworld-coast-mosaic.md:13-169`)

The file's own LAW INDEX groups ~90 named laws into 7 clusters. Load-bearing ones for a reviewer:

- **THE LAW (line 18):** a per-cell tiler/WFC over arbitrary tiles cannot make continuous LAND — independently-authored 3D cliffs never meet cleanly. Only WATER seams blend freely.
- **THE RING LADDER** (line 20): bands ring an island Sea4→Sea5→Sea3→Sea1→Sea2→beach1→land, width tracks bathymetry not a uniform offset; {sea1,sea5} is a real lawful adjacency that can skip sea3.
- **COMPONENTS ARE GEOMETRY+TEXTURE+TOPO UNITS** (line 37): texture substitution across component classes fails — you can't texture-swap your way to a different coast type.
- **CARRY, DON'T SYNTHESIZE, recurring 3×** (lines 42, 82, 137): island-tongue rule, beach-mint mesh law, canopy-carry law — each domain independently re-derived "carry the real mesh whole" after synthesis attempts failed.
- **THE STRICT SHORE LAW / GROWTH CEILING** (lines 75, 169): a cut may never cross sea1/sea2; single-donor single-axis growth caps at 2 cuts / +8u — set by component laws (relief/beach/wash/conforming), not the shallow-crossing law.
- **THE LATTICE LAW / MEASURED MURAL GATE / TILED-MAINS FILL** (lines 56, 60-61, 2026-08-04 dated): sea fills must be stock-shaped 4u tiles, no tri spanning a tile; cliff-fill admission is measured by uv-rect reuse fraction (threshold 0.40), never decided by topo id alone (topo-49 alone was 90% tiled on one crescent, 5% mural on an isthmus — same id, opposite verdict).
- **THE OVERHANG-CONTEXT / TUCK VOCABULARY items (lines 65-66)** point out to the dedicated law file (§3 below).
- **Map-wide census verdicts (Section G, lines 166-169):** the multi-block landmass screen found NO verbatim-clean 2-block island except one; ~56 donors have ≥2 clean growth x-lines but the ceiling is component-law-bound, not census-bound.

Net for reviewers: this file is the single largest law surface in the KB (~90 named laws across component/transplant/growth/cliff-morph/beach-morph/strip-language/census clusters) and is the **mandatory read-before-coast-work gate** (`CLAUDE.md:§9` read-first list). Any proposal touching coastline geometry should be checked against this index before design, not after.

## 3. The arc's meta-lessons (why gates and green tests are not proof)

**THE OVERHANG-CONTEXT LAW** (`project-ff9-overhang-context-law.md:29-44`) — a verbatim stock element can be *wrong* purely because of the context it's torn from, not because the carry was inexact. FF9's grass-family coast lips all overhang (5/5 census, ny −0.37..−0.15) because in stock they stand in water to their base (FREE-BASE) — the overhang's underside is never seen. Carried onto Path D's bench, where the sea is *cut* under walkable cover, the identical faces hang over dry void: visually a fractured skirt, and every attempted fix (coplanar walk membrane, foot apron, inner curtain) added *more* authored surface, which then absorbed the next round's defect (see below). Corollary tools: **THE PEER GATE** (`:64-70`) — score a new element against peers the owner *already accepted* on the same island, not against stock's marginals, because "no gate asks does this read like the thing already approved." **THE T-JUNCTION GATE** (`:72-82`) — a vertex sitting in the interior of another face's edge is watertight in exact math but cracks under float32, invisible to render gates and weld audits; a "near enough" repair is *worse* than the crack (measured: 2.5e-3 tolerance opened 26px of visible background).

**THE DEFECT FOLLOWS THE AUTHORSHIP** (`project-ff9-ground-junction-synthesis.md:16-19`, echoed `CLAUDE.md:207-210`) — measured over the Path-D wall arc: **12 of 13 playtest verdicts and 32 of 37 named defects landed on whatever that round had most recently authored** — never on carried stock geometry sitting in its own context. Corollary: the cheapest way to stop minting defects is to stop minting surface. Practical reading for a reviewer: a proposal that adds a new authored patch to fix a previous authored patch is very likely restarting this cycle, not closing it.

**A GREEN GATE SUITE IS A REGRESSION HARNESS, NOT AN ORACLE — 0 of 13** (`project-ff9-ground-junction-synthesis.md:21-26`, `CLAUDE.md:203-206`). No gate in this arc ever fired *before* the owner's eye did. Every gate asks "is this value inside stock's distribution for this element," never "does stock ever build this *shape*." Concretely: a wall end with 42 stock counterexamples and 0 real instances *passed* every gate, and a round shipped a 10.94u weld displacement inside a 12u cap that the owner then personally flagged as wrong — "a gate can be green and wrong in the same number." Every gate in the suite was written *after* a verdict had already named its defect class, i.e. gates in this domain are retrospective regression nets, not predictive oracles.

**THE REAL OFF-LANGUAGE NUMBER — TESSELLATION** (`project-ff9-ground-junction-synthesis.md:40-45`). Three plausible mechanisms were measured OUT entirely: UV continuity is not the seam (the bench was *more* uv-continuous than stock, 83.9% vs 52.4%); ground normals are render-inert (`WorldMap/Terrain` binds no light position, `WMMesh.Normals` read at zero non-debug sites — a normal fix literally cannot change a pixel); the plan-vs-surface UV convention debate is near-vacuous below 20°. The actual carrier was **tessellation density**: a per-vertex weld of a flat host to a non-level donor weld line shattered the ground into 4,181 grass tris at median 0.32u² (79% under 1u², up to 82 per 4u cell) versus the pristine bench's 858 tris at 8.00u² (max 5) and stock's map-wide max of 4-5 tris/cell. **Nobody had rendered the defect across 8 rounds — zero images taken** until a still was requested. A follow-up A/B refined the carrier further to **THE LIFT FIELD** (`:47-53`): the strongest owner-named defect class (raised-grass bank) survives coarsening to one quad per 4u cell — its carrier is the minted height field's *shape* itself, not the tessellation. Prescription: **any next build is a DELETION — no per-point vertex moves, no ground partition, no stitch passes.**

**THE APPROACH-GROUND LAW** (`:64-69`, the one law that *survived* the arc): stock's ground at a wall foot is a short lip then a LEVEL TERRACE at ~1.0-1.5u offset over local lowland — never a ramp, and 0 of 176 sampled components are pedestals. A calm (flat-ish) host is a real ~10% stock subpopulation and not disqualified; a monotone lift/ramp is off-language regardless.

## 4. Interior-topography, terrain-authoring, actor-brick, audit-roadmap

**THE TERRACE LAW** (`project-ff9-overworld-interior-topography.md:22-29`): walkable land lives in exactly two altitude worlds — lowland 2-8u and plateau 26-32u, with a near-empty 18-26u gap that IS rock (topo-49). A faithful landmass is built from discrete levels joined by walls/rare passes, never a continuous ramp; coastal land stays 0-2.7u. **NO-FOOT-PASS finding**: the two altitude worlds are not overworld-walk-connected on foot by design (2.34375u step ceiling) — connection is fields/vehicles.

**LOOK FAMILIES ≪ TOPO IDS** (`:31-48`): ~37 in-use topo ids collapse to ~9 look families (grass/dirt-desert/scrub/forest/canyon-red-rock/snow/rock/shore-sand/coastal-lip) plus 2 unassigned (38, 51). Ids *within* a family are gameplay/encounter variants, not looks — so authoring a look needs only the family's tile set; picking the specific topo id is a separate encounter/region decision.

**RESHAPE, NEVER OVERLAY** (`project-ff9-overworld-terrain-authoring.md:15-23`): the load-bearing rule for `world-terrain`. Displacing existing verts leaves one walkmesh surface the player walks on; overlaying a new mesh on intact ground is non-walkable decoration — mechanism is *non-registration*, not raycast precedence (`RegisterBareObjectOverride` never calls `AddWalkMeshForm1`). Exception: on a TOWN block with a real stock `ObjectForm1`, an Object override *does* register as real collision — the two paths are chosen by whether the stock prefab already carries an Object.

**Overworld actor-brick** (`project-ff9-overworld-actor-brick.md:13-23`): editing overworld geometry under or near where the player stands can BRICK a save — silent black screen, no exception logged, hard-freeze, debug menu still opens but reports "no controlled actor." It is baked into the save; continuing re-blacks every time, and deleting the bad geometry does not fix an already-parked save. Root cause: invalid ground under the saved spawn → no `wmActor` binds → camera follows a permanent dummy. An engine self-heal (`w_worldSelfHealControl`, s61-gated to worlds with an actual player actor to avoid hijacking scripted scene worlds) now recovers this live, plus a ~ "Rebuild player actor" button — but the discipline (safe save off the edited cell, teleport-in/look/teleport-out, never save parked on an edited cell) still stands as the primary defense.

**Audit-roadmap** (`project-ff9-overworld-audit-roadmap.md:11-20`): a 2026-07-18 adversarial pass over 260 falsifiable claims across 5 doc layers found ~205 held, 20 confirmed defects, 19 split, 13 rejected — mechanisms/gates/constants overwhelmingly held. The recurring defect class was **numbers that don't reproduce from their cited scripts** ("a number without a rerunnable script is a wish" — the study-arc's own corollary of the harness-verification law). One real code bug was found and fixed (`pack_cell_tag` 7-bit vs engine 6-bit z-mask). The do-next tier from that audit is fully closed (world-mirror auto-run, donor census, discmr full-pack decode).

## 5. Proven-and-working vs. falsified

**PROVEN-AND-WORKING (in-game confirmed, safe to build on):**
- `world-terrain` reshape (seamless multi-block hill), `world-reclaim` (ocean→walkable land, s34 engine patch)
- `world-coast` faithful coastal-donor carry (terrain+sea+beach1+foam, real donor block)
- `world-water` marching-band synthetic open ocean (3-shade grammar sea3/sea5/sea4, 4-rotation quadrant UVs) — 100% shape/adjacency match vs verbatim
- `world-transplant --ground` (ground-retile carry, e.g. (7,17)→desert) — "looks verbatim," geometry/water byte-verbatim
- `world-transplant` whole-block coastal/two-level carries (the v4 Daguerreo transplant — falls/river/bridge free-ride mechanism proven, disc-4 mirror proven)
- The FOREST canopy carry (`world-forest` pipeline) — "walked the whole rim aggressively, no more sticking"
- THE HILL AT SCALE (pure-Y cosine-dome displacement of deployed island mesh) — "looks natural, walkable from all sides"
- THE SPUR (first in-game-proven *synthetic* mountain material, one course grafted onto a real massif foot) — "looks good, i compared to verbatim"
- THE SOUTHERN RING (composed world, R1-R5 all playtest-confirmed per CLAUDE.md §10)
- Path D V-shore corner (owner-accepted on flow and look after 12 playtests, using the tuck vocabulary derived from measurement, not invention)
- The overworld self-heal engine patch (s61-gated) recovering actor-brick without a relaunch

**FALSIFIED (do not re-propose without new evidence):**
- From-scratch procedural massif/mountain synthesis by statistics (8 rounds)
- Terrace wall built from decoded tile language alone, without carrying real massing (2 rounds)
- Any "carry the ingredients through a synthetic frame" approach — ribbon-bending, label-stamping, parameterized bend-carries (v3 two-level island, 3 rounds, "stacked interpenetrating shards")
- `world-island --beach` procedural beach-mint ladder (4 rounds)
- Small-footprint dunes mint (<~130-cell) — a real size-class law, not a tuning problem
- Canyon-family walls placed on an island/open-sea coastal context
- Thin desert ribbons as a mixed-biome transition (must be a landmass-scale unit)
- Uniform coast-lip carries into a cut-sea (no free water beneath) context — THE OVERHANG-CONTEXT LAW
- Any fix strategy that adds authored geometry to patch a previous authored defect, without first re-measuring against real stock bytes (THE DEFECT FOLLOWS THE AUTHORSHIP predicts this repeats)
- Treating a green offline gate suite as proof of in-game correctness for any novel ground-junction/wall/coast shape (0/13 predictive record in this specific arc)
- HW-based field/model authoring generally (out of scope for overworld too — atlas-clone UV bug)