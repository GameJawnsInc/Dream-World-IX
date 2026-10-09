# Land to sea: removing a real island (2026-10-09)

The terrain-malleability matrix had one row with no operator: **remove land**. This lane measured how the stock game
does it, which islands the same recipe can take, and built `world-sink` (`ff9mapkit/world/transplant.py`
`sink_plan` / `sink_footprint_plan` / `sink_cluster_plan` / `sink` / `sink_candidates`). In-game proof:
`../ingame/RESULTS.md` sections 25 (deep water), 26 (shallow water) and 27 (clusters).

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

## 5. Islands in shallow water (`sh_q*.py`)

The bare-coast unit (land plus its welded shallows) cannot separate an island with shallows: the shallow bands are
continuous meshes, out to a continent. These islands are the common case: disc 1 has 57 land components (terrain and
beach1 joined by shared vertices), 53 within 9 blocks.

**What water they stand in** (`sh_q1_halos.py`, `sh_q2_plot.py`):
- Most stand in mid water (sea3), often on the edge of a shelf: mid water on one side, deep sea4 on the other, with
  the sea5 transition band between. Their land meets sea3 and sea4 directly, and sea5 only at a few tiles.
- Only true shallows (sea1, sea2) and the sand (beach1) are bound to a shore. Six small islands carry them.
- No water lies under other water: 0 of 20,582 shallow tris have sea4 under them. Every band is cut against the
  others, like sea4 is cut under land.
- All water bands sit flat at y 0, share the stock normal (-0.1211, 0.9785, 0.1665), wind negative and carry area 0.

**Their navigation classes** (`sh_q3_topo_reach.py`, `sh_q7_sea5_class.py`). The topograph is the engine's
navigation key, not the band:

| band | within 2u of land | past 4u |
|---|---|---|
| sea3 | 55, the standoff belt (2,480 of 2,488 tris) | 54 (sailable) |
| sea4 | 56, the keel | 57 |
| sea5 | 55/56 | one deep edge: 54 on both tris (890 of 890); a corner (two deep edges): the tile is split on the diagonal that cuts off its deep corner, 57 on that tri and 54 on the other (1,620 of 1,630); three deep edges: 57 (625 of 626) |

The Blue Narciss sails 53, 54 and 57, so mid water away from land is sailable. A party on foot sinks into water by
class (`w_movementSinkArray` row 1, `ff9.cs:19`): 54 reads 0.586 under the surface, 55 0.391, 56 and 57 1.367.

**The band model** (`world/water.py`'s open-ocean marching band, in-game proven 2026-07-05). Every tile edge is deep
or not; a tile with no deep edge is sea3, four sea4, one to three a sea5 transition tile drawn for its deep-edge-set
(transplant.py's learned Wang table). Stock agrees: on 827 edges shared by two decodable sea5 tiles, both decode the
edge the same way, every time (312 deep, 515 not). A corner tile's two variants (v-strips 1 and 3) split about 50/50
whatever its diagonal neighbour holds (`sh_q4_corner_variants.py`): a free variation choice.

**The sink, generalized** (`transplant.sink_plan`):
1. The unit is the island's land component, traced across block borders, plus its own shore: sea1 and sea2 nearer to
   it than to any other land. Shore water joined to another coast's is refused.
2. The region is every tile they touch, closed over the coast-conforming water (sea3, sea5, sea4) round them, within
   12u.
3. The bands: an edge on the region's rim takes its state from the kept water across it (sea4 deep, sea3 not, a sea5
   tile what its own decoded deep-edge-set says, another coast's sea1 not). Another coast's wash (sea2) refuses. An
   interior edge takes the inverse-distance-weighted state of the rim's. A channel (two opposite deep edges, which no
   tile draws) flips its weakest free edge. Every kept transition tile keeps its deep-edge-set, so nothing outside the
   region changes look. An island in deep water re-bands to sea4 throughout: the bare-coast sink exactly (7 of round
   10's 8 islands plan byte for byte the same; see below for the eighth).
4. Each tile is filled whole in its band: sea4 as before, sea3 in its learned quadrant language, sea5 as the learned
   transition tile. A corner tile is split as stock splits it.
5. Navigation classes as stock (the table above), the shore classes within 2u of land that stays. A kept tri with a
   coastal class that only the island explained takes its band's open class, in the 3x3 blocks round the region. The
   old sink looked only in the region's own blocks: at the (7,4) island this missed 4 keel tris of its ring in (7,5).
6. New gates: the absent-part gate (a block whose prefab lacks the band a tile needs), the band gate (every pair of
   neighbours is one stock lays side by side), the decode gate (every drawn transition tile decodes as the edges it
   was drawn for).

**What it takes** (`sh_q5_census.py`; `world-sink --list`): 25 of the 53 islands, all 25 replayed on disc 4 (up from
8). 17 of them stand in shallow water; one takes its own beach water (32 sea1/sea2 tris). No band field needed a
channel flip. The 28 refusals: 14 run their coastal water on into another coast's, 5 share their beach water with
another coast, 8 have a building, other land or a waterfall in their tiles, 1 has a kept land vertex on a re-tiled
tile's edge.

**The look, offline** (`sh_q6_render.py`): top-down renders with the game's own textures (unlit, no wave animation)
of five sinks show the lagoon healed as plain mid water, and on a shelf island the mid-water edge running on across
where it stood. No seam is visible.

**In game** (`../ingame/RESULTS.md` section 26, 48/48 on the first launch): a lagoon island with a beach and a
shelf-edge island sank on both discs. A party where they stood reads each new class's walk sink to the last bit (mid
water 0.586 under the surface, open water 1.367, both tris of a split corner tile as stock classes them), the Blue
Narciss crossed where each stood (on stock it stops at their standoff belt), and the frames show continuous water.

## 6. Island clusters (`sh_c*.py`)

An island whose coastal water also hugs a neighbour's coast is part of a CLUSTER. The whole-tile sink re-tiles every
tile the island touches, closed over the coast-hugging water round it, so here it runs on into the neighbour's coast
and refuses. 19 of the 28 islands refused in section 5 were refused at another coast or its beach water.

**How disc 4 removed Shimmering Island and kept its islets** (`sh_c1_shimmering.py`). Shimmering's main island and
seven islets share their coastal water. Disc 4 removed the main island (489 land tris), and kept all seven islets.
Three kept their land and coast byte for byte, one changed 4 of its 113 land tris and 2 of its water tris, and three,
where the strait water touched the main island too, had their coast water rebuilt: the new water tris span 2 to 4
tiles and run from the islet's coast vertices to lattice points, and the islets' land got 53 new tris, some at new
heights. That is hand work: the bytes cannot be copied.

**Two operators:**

| | what goes | what stays | how |
|---|---|---|---|
| THE FOOTPRINT SINK (the default for a joined island) | the island's land and its own beach water | every water tri round it, every neighbour | its plan footprint becomes water, cell by cell |
| THE CLUSTER SINK (`--cluster`) | the island and every island its water joins | the water past them | the whole-tile sink on the union |

**The footprint fill** (`sh_c2_hole.py` to `sh_c4_footprint.py`; `transplant.sink_footprint_plan`):
- `sh_c2`: filling the hole's outline with `lattice_patch` fails twice. Shimmering's outline encloses a kept islet (a
  loop inside the loop), and an irregular outline clipped to a cell leaves a piece the ear-clipper cannot take.
- `sh_c3`: cutting each dropped tri against each 4u cell instead (one convex piece, its crossings computed from the
  original edge in one canonical order) and merging a cell's pieces by edge cancellation fills both exactly. But
  where the hole's outline crosses a 4u line it adds a vertex part-way along a kept tri's edge: a T-junction.
- `sh_c4`: so keep all the water and replace only the land. The footprint is the island's land; a cell it covers
  whole becomes a stock tile in the band the marching band gives it; a part-cell continues the kept water beside it
  (that water's band, affine uv map, normal and area), so the water runs on over the old coastline with no seam;
  where a 4u line crosses the old coastline, the kept water tri on it is split there (same plane, same uv map).
  Stock puts zero-area water slivers along coasts, with a vertex part-way along the land's edge: the fill takes
  those vertices too. On all four sites the fill equals the footprint to 0.01 u2, with no kept water under it.
- Shimmering by footprint (`out/sh_q6_441_311.png`): the main island goes, all seven islets stay, as on disc 4.

**THE SPLIT WELD** (`sh_c6_welds.py`, an independent check of the finished mesh: open edges, T-junctions, near
misses). It found that the whole-tile sink of rounds 10-11 left T-junctions on 20 of its 25 islands (122 edges): a
re-tiled tile's corner part-way along a kept coastal tri that runs past it. The whole-tile sink now splits that kept
tri there too; its fills are byte-identical to before on all 25 islands and both discs, only the split pieces are
added. After it, all 40 sinkable islands are watertight (0 open edges, 0 T-junctions). The near misses left (1 to 5 on
7 islands) are welded short edges: a stock coast vertex within 0.05u of a 4u line.

**What it takes** (`sh_c5_census.py`; `world-sink --list`): 40 of disc 1's 53 islands, up from 25: 25 by the
whole-tile sink and 15 by the footprint sink. All 40 replay on disc 4 except Shimmering, which disc 4 already
removed (no land there: the replay refuses and disc 4 keeps its own ground). With `--cluster`, 4 clusters sink
together (Shimmering's main island with two islets, and three pairs), all but Shimmering's on disc 4 too.
The 13 refused: 7 have a building on them, 5 share their beach water with another coast, 1 needs a band its
block's prefab has no part for.

**In game** (`../ingame/RESULTS.md` section 27, 60/60 on the first launch): Shimmering's main island sank alone on
disc 1 by its footprint, its islets read their stock heights to the last bit, and the frames match disc 4's own
Shimmering; the (8,16) pair sank together with `--cluster` on both discs; the Blue Narciss crossed where each stood;
round 11's island, re-deployed with the split weld, read as before.

## 7. Not done

- **Islands with a building,** and islands whose beach water another coast shares.
- **The big map** still draws a sunk island: `world-minimap` paints deployed land, it cannot erase stock land.
- **Moving an entrance onto the new sea,** as disc 4 did for Shimmering (`--allow-entrances` drops it).
