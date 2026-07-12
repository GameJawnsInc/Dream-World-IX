# Overworld interior topography — the census study

The regenerable survey behind the **interior landmass** knowledge base (how FF9 builds
mountains, plateaus, forests, deserts, snowfields, and rivers — everything inland of the
shore vocabulary). It reads your own FF9 install; **no game bytes live in this repo** —
the `out/` artifacts regenerate in ~2 minutes:

```
py studies/overworld-topography/census.py        # artifacts -> studies/overworld-topography/out/
```

## Headline findings (disc 1, all 260 land blocks — 2026-07-12)

- **THE TERRACE LAW.** Walkable land lives in TWO altitude worlds: the lowlands (2–8u,
  peak 3–4u) and the plateaus (26–32u), with a near-empty gap at 18–26u — the gap is
  topo-49 rock. Mid heights (10–17u) are sparse terrace steps (the Forgotten Continent's
  canyon tiers, topo 45/46, and topo-13 shelves at ~17u).
- **LOOK FAMILIES ≪ TOPO IDS.** ~37 in-use topograph ids collapse into ~9 tile families:
  grass (0/1/2/3/10–13/42/59), dirt-desert (16–23/41), scrub (4/5/6), forest (36/37),
  canyon red-rock (45/46), snow (27/28), rock (49, 7, 62), shore sand (31/32/33), lip (58).
  Ids within a family are GAMEPLAY variants (encounter regions/events), not looks — e.g.
  plateau grass 10/11/12 renders with the same tiles as lowland grass 0.
- **FORESTS ARE GEOMETRY + TILES, fully lattice-native**: topo 36 (high, 20–32u) / 37
  (lowland), dark canopy tiles, the standard ~4.2u grid with ~1.9–2.3u per-tri height
  jitter (the "puffy" canopy), slopes to 90° yet FOOT-LEGAL — you walk into them.
- **RIVERS/FALLS/STREAMS ARE PARTS, like beaches**: tiny animated water-surface sub-meshes
  (`river`/`riverjoint` topo 48, `falls` topo 50, `stream` topo 51; 1–51 tris each) laid
  over a channel carved in the Terrain part. A falls sheet at block (5,15) spans y 15.2→26
  — it is the seam between the two altitude worlds. Also present: `volcanocrater`/
  `volcanolava` at (7,1)/(8,1) — Gulug.
- Dominant class map-wide: **topo 49 mountain rock** (27.8k tris, 164 of 260 blocks,
  median slope 51°, foot-illegal) — mountains are the walls that partition the walkable
  world. Top adjacencies: 0|49 (grass meets rock) and 10|49 (plateau meets rock).
- `topo_map_true.png` colors every 4u cell by its topograph's real mean atlas color —
  it reproduces the painted world map's reading at a glance (good sanity check that the
  census semantics are right).

## The forest arc (★ in-game proven 2026-07-12)

Two synthesis attempts were falsified in-game (per-tri tile picks, then dome+jitter+tiles —
"a sloppy triangular mess"); the UV studies (`forest_uv_language.py`, `forest_uv_components.py`)
showed canopy texture is hand-authored (28–35 non-affine UV patches, seams everywhere yet
invisible) ⇒ **THE CANOPY CARRY LAW: carry a real canopy blob whole, never synthesize it.**
`forest_blob_inventory.py` lists the carryable blobs ((15,15)'s 132-tri grass-bounded blob =
the clean donor); `forest_carry.py` is the proven build: lattice hole + chain-ordered rings +
greedy-bridge zip annulus + exact-float welds + **THE CANOPY STEP LAW** (wall faces are vertical
curtains; every rise gated ≤ 2.2u under the engine's 2.34375u step ceiling — stock forests
genuinely block at their own 2.4u+ segments). Proven on the reclaimed bench pad at cell (3,14)
(`world-reclaim --profile island --seg 16`).

Full statements + provenance: memory `project-ff9-overworld-interior-topography`.
Shore-side laws: memory `project-ff9-overworld-coast-mosaic` (the LAW INDEX).
