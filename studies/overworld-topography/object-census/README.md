# Stock world-map Object-mesh census (2026-07-25)

The first per-block AND per-structure catalog of every stock disc-1 `Object.ff9mesh` — the substrate
that renders the world map's visible landmarks (towns, castles, harbours, cave mouths). Produced during
the Lantern Quay marker round; no such census existed before (confirmed by repo-wide grep;
`mesh_parts_census.py` only counted parts).

**Provenance:** every file here is MEASUREMENTS (tri/vert counts, bboxes, IDALL/topograph histograms,
distances) plus the scripts that regenerate them from the user's own install via
`ff9mapkit.world.extract`. No Square-Enix bytes: no vertex arrays, no OBJ exports, no atlas-textured
renders (those stayed in the session scratchpad and are regenerable by the scripts).

## Headline results (full numbers in the JSON/CSV)

- 63 Object blocks · 3693 tris · 11 079 verts · **48 welded world-space structures**. Uniform byte
  layout everywhere (stride 48, POS/NRM/UV/TAN, 16-bit indices, flat/unindexed with `flat_index` a
  PERMUTATION — slice by triangle through `flat_index`, never assume `3t..3t+2`).
- **Topograph 59 = the stock structure type** (93.7% of all Object tris); every distinct stock IDALL
  carries `flags == 2`.
- **IDALL 4078 (0x0FEE) is the stock render-only idiom** — `WMPhysics.Raycast` skips 4078/4088/2040
  outright; stock uses 4078 on Chocobo's Forest (100 tris). The Lantern Quay marker is stamped with it.
- **Structure naming is via the engine's `navipos` table** (`ff9.cs:421+`), which lands inside the
  object bboxes to <2u. **`world/locate.py`'s area→place join is WRONG** — the engine packs CELL
  coordinates into the world dispatch key (`ff9.cs:2233`), not the IDALL area bits; and the Object
  IDALL `area` field is only a coarse regional tag, not identity. (`area_truth.py` reproduces the
  refutation; a kit fix is tracked separately.)
- Override traps: block (5,16) Daguerreo's Object renderer is unconditionally replaced by a local
  prefab (`WMWorld.cs:666-678`) — s34 Object overrides there are invisible; same for (14,6) on disc 4
  only; block 219 early-returns.
- Best small-structure carry donors, ranked: **Alexandria Harbour (21,10)** (104 tris, ONE IDALL, whole
  block = the one structure, base at local y=0 — the Lantern Quay marker donor) · Lindblum Dragon's
  Gate (14,15) · the unnamed gatehouse (22,14) · Quan's Dwelling cave mouth (21,14) · Chocobo's Lagoon
  (9,17, carries a LIVE event-1 trigger IDALL — re-stamp if carried).

## Files

- `object_census.csv/.json` + `object_census.py` — per-block census (the .json variant here is the
  IDALL-focused census from the mechanism round; the .csv is the full per-block table).
- `structures.csv/.json` + `structures.py` — per-structure catalog (the primary artifact).
- `object_rank.json` + `obj_rank.py`, `object_coast.json` + `object_coast.py` — ranked/coastal views.
- `donor_spec.py` — exact carry-donor spec dumps.
- `area_truth.py`, `area_names.py`, `navipos.txt` — the locate()-refutation evidence.
- `quay_marker_census.py/.json`, `quay_marker_shapes.py` — the earlier (locate()-named, superseded)
  marker-candidate census; kept for provenance of the donor correction.
- `quay_probe.py`, `reverify.py`, `obj_bytes.py`, `obj_render.py`, `obj_context.py`, `obj_persp.py`,
  `mapgrid.py` — probes and (PNG-emitting, run-locally) render/context scripts.

Related: `../WORLD-SCRIPTED-OBJECT-LANE-2026-07-25.md` (the OTHER world-object lane — scripted actors),
`../southern-ring/` (the marker deployment this census served).
