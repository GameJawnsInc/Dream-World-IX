# Land to sea: removing a real island (2026-10-09)

The terrain-malleability matrix had one row with no operator: **remove land**. This lane measured how the stock game
does it, which islands the same recipe can take, and built `world-sink` (`ff9mapkit/world/transplant.py`
`sink_plan` / `sink` / `sink_candidates`). In-game proof: `../ingame/RESULTS.md` section 25.

## 1. How disc 4 removed Shimmering Island (`shim_*.py`)

Shimmering Island spans blocks (6,4) (7,4) (6,5) (7,5). Disc 4 does not sink it under the water. It deletes it:

| step | measured |
|---|---|
| Terrain deleted | 798 → 321 tris over the four blocks (530 out, 53 new); no disc-4 Terrain vertex below y 0 |
| coastal Sea4 deleted | 216 tris out, 145 of them topograph 56 (the near-shore band) |
| re-tiled as open sea | 405 Sea4 tris in, 375 of them topograph 57, all at y 0; 91 of 96 former-land 4u tiles are one clean tile (two tris, one texture quadrant), the stock normal and winding |
| the coast band | the 0-6u ring went from 3,127 samples of topograph 56 to 540 (those left ring the islets that remain) |
| shallow bands | Sea1 identical; Sea3 and Sea5 re-cut 3 tris each, same ids |
| entrance | moved onto the new sea: 56 Sea4 tris with event 2, about 1.8 times the old tile area |

The ground query over the old footprint: disc 1 100% Terrain (topograph 59); disc 4 Sea4 topograph 57 at y 0 (topograph
56 on 90 samples), and Terrain only on a y 0 skirt. Plan overlap of Sea4 and Terrain: 0 on both discs.

**Corrections to `../disc4/NOTES.md`:**
- Alexandria Harbour (21,10) is not a land-to-sea site. Its entrance tiles were already on Sea4 at y 0 on disc 1.
- Map-wide land-to-sea on disc 4 is 1,878 u² on a 1u grid (`shim_q7_mapwide.py`), not 1,401. 1,871 u² of it is
  Shimmering; the rest are 1-2 u² cliff-lip slivers.

## 2. Which islands are separable (`island_pool.py`)

The excise's unit, an island ASSEMBLY, is the land plus the shallow water welded to it (terrain, beach1, sea1/2/3/5,
joined by shared vertices). Traced over the whole of disc 1, across block borders:

- **23 land assemblies** in all. The four continents absorb every island that owns shallow water or a beach: the
  shallow bands are continuous meshes, so such an island is one assembly with its neighbours, out to a continent.
- **19 bare-coast islands** stand alone (their land meets deep sea directly). Shimmering Island is one.

So the lawful unit for a sink is the bare-coast island, the class stock itself removed.

## 3. The coastal-water reach (`keel_reach.py`)

Stock deep sea carries topograph 57 in open water and 53-56 near coasts (the Blue Narciss sails only on 53, 54 and 57).
Topograph 56 sits on 4,357 disc-1 Sea4 tris, all within 4.14u of land (centroid to nearest land, p99 2.95u). The sink
re-ids a coastal tile to 57 only when no remaining land lies within 4.5u of it (`SEA_COAST_REACH`); otherwise a ring of
water the boat cannot cross would wall off where the island stood.

## 4. The sink, and what it takes (`sink_census.py`; `world-sink --list`)

The recipe, after disc 4:
1. Trace the island's assembly across block borders; refuse an island that owns shallows.
2. The REGION is every 4u tile the island covers, closed over the coast-conforming Sea4 tris round it (they span
   tiles: every tile one reaches joins, within 12u of the island).
3. Each region tile must hold only the island and stock Sea4 (no building, other land, shallows, river, or entrance
   bits on the sea). It is re-tiled whole as open sea (`lattice_patch` on the tile square). A kept vertex lying
   part-way along a region edge joins that tile's outline, so the seam has no T-junction.
4. The near-shore band only the island explained becomes topograph 57.
5. Every island tri is dropped, the near-vertical ones on tile lines included (they touch no tile by area: round 10's
   second launch left two floating). A land piece welded to nothing that lies within the region sinks with it.
6. Gates: every island tri dropped; no kept land vertex inside the region (it would float); coverage (every region
   sample under exactly one fill tri); per block, the in-place frame gate across parts (a border two sunk blocks share
   is exempt), stitch, and the entrance guard.
7. One morph per block, all gated before any write; one disc-4 mirror pass with a replay where disc 4 differs.

A block whose whole Terrain was the island gets the hidden blanking stub, not an empty mesh (the writer refuses a
0-vert mesh, and the failure would come mid-deploy).

**Of the 19 bare-coast islands, 8 sink, and all 8 replay cleanly on disc 4** (45 to 4,813 u²; three span 2 to 5
blocks). The 11 refusals:

| reason | islands |
|---|---|
| a building (Object) shares its tiles | 2, both on (5,3) |
| its coastal sea runs on into another coast's | 5, among them Shimmering Island (its own islets share its sea) and (0,0) |
| other land, a shallow tile or a waterfall shares its tiles | 3 |
| no Sea4 part in its blocks | 1 |

The 4 continents are refused as larger than 9 blocks or owning shallows.

## 5. Not done

- **Islands with shallows or a beach.** Sinking one needs re-tiling the shallow ladder round what is left. The coast
  laws say shallows are copied, never synthesized, so this needs its own study.
- **Island clusters** (Shimmering and its islets), and islands with a building.
- **The big map** still draws a sunk island: `world-minimap` paints deployed land, it cannot erase stock land.
- **Moving an entrance onto the new sea,** as disc 4 did for Shimmering.
