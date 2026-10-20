# Lakes recon: which sea patches are joined to the open ocean

**Status:** registered before measuring (2026-10-20). Reads only: stock disc-1 bytes, nothing written but
`out/lakes_recon.json` and `out/lakes_plan.png`. No launch.

**The question** (RECON.md, "Lakes are a separate recon"): stock has no lake part, so a lake can only be sea water
(Sea1-6) at an inland margin. Is any stock sea patch cut off from the open ocean? If so, it is the one water feature
that closes on every side by itself. THE TERMINATION CENSUS found none among rivers, streams and falls. An enclosed
lake would be the first candidate for a carry the way `world-forest` carries a canopy.

**What is already known:**
- Disc 1 has 480 block slots, and 275 carry a prefab. The other 205 render the engine's SeaBlockPrefab, which is open
  ocean (`extract.block_parts`).
- Sea parts by block count: sea4 214, sea3 157, sea5 140, sea1 44, sea2 40, sea6 4, sea4f 1. Every sea part's lowest
  vertex is at y 0.
  - A few shallow parts lift a vertex to 0.14-0.8: sea1/sea2 at (3,12), (3,13), (4,13), (5,13), (5,14), (7,17),
    (9,17) and (9,18); sea2/sea3 at (14,4), (12,11) and (13,13).
  - (16,15)'s lifted 0.535 vertices are the river mouth's two shallow tris (`mouth_compare.py`).
  - This inventory was read before this registration.
- Coast-mosaic records beach waterlines at y 0.2 at (3,12), (4,13), (5,13), (7,17) and (9,17), as "elevated
  lake/marsh shores". Its coast-tile catalog classed 3 blocks as `lake`, but did not keep the list.
- `census.py`'s "inland sea" list (blocks with Sea3 and no Sea4) is mostly bays. RECON leaves (17,10), (14,4) and
  (4,8) unconfirmed.
- Stock Sea4 is cut under land (memory `project-ff9-sea4-under-land-law`), but a one-tri fringe survives at the
  waterline. Hidden water could therefore join two bodies under a thin strip of land.

## The instrument (`lakes_recon.py`)

- **A. The water graph.** Every sea tri (sea1-6, sea4f) on every prefab block is joined to every other by a shared
  plan vertex. The keys wrap at the world's edges (x mod 1536, z mod 1280), and overlapping layers on the 4u lattice
  share vertices. Each prefab-less block is one node of open ocean. It joins its prefab-less neighbours (4-neighbour,
  wrapped) and every sea tri with an edge on their common border.
- **B. The partition.** The component that holds the prefab-less blocks is THE OCEAN. Every component without one is
  an enclosed body. Each body is described by:
  - its water: tris, plan area, blocks, layers, topographs and y;
  - its shore ring: the terrain and beach tris that share a plan vertex with it, by topograph, with their y;
  - its plan distance to the ocean;
  - any river, stream or falls tri within 8u;
  - any entrance tile within 16u.
- **C. Hidden joins.** The same partition, rebuilt from EXPOSED sea tris only: a tri is hidden when terrain stands
  above the water (> y + 0.05) at its centroid. A body that splits off only in the exposed graph is joined to the
  ocean by water under land alone.
- **The control:** cluster C's mouth water at (16,15) is a bay that opens to the sea, so it must land in THE OCEAN.
  A component labelled THE OCEAN must also hold every prefab-less block, or the joins are broken.

## Registered predictions

| # | prediction | falsified if |
|---|---|---|
| P0 | THE OCEAN is one component: it holds all 205 prefab-less blocks, (16,15)'s mouth and over 95% of sea tris | the prefab-less blocks split, the mouth lands elsewhere, or it holds 95% or less |
| P1 | disc 1 holds at least 1 and at most 6 enclosed bodies | 0, or more than 6 |
| P2 | every enclosed body is small: less than one block (4096 u²) of water in plan | one is larger |
| P3 | the y-0.2 shores at (3,12), (4,13), (5,13), (7,17) and (9,17) lie on enclosed bodies, not the ocean | any of them is ocean |
| P4 | no river, stream or falls tri lies within 8u of an enclosed body: no stock river ends in a lake, by THE TERMINATION CENSUS's SEA/MASSIF tips | one does |
| P5 | the exposed-only partition finds the same enclosed bodies: no body joins the ocean only under land | it finds more, or different ones |

The three bays RECON left open, (17,10), (14,4) and (4,8), get no call. They are measured and reported.

**What follows:**
- **If P1 holds:** each body's shore ring and size say whether it could be carried. A carry needs a lowland ring
  that closes, no entrance tiles, and no river.
- **If P1 fails with 0:** the lakes recon closes the same way as THE STANDALONE WATER-FEATURE CENSUS: every stock
  water body is the ocean's.
