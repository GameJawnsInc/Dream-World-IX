# Water-feature carry: recon

**Status:** recon only, nothing built (2026-10-19). The question: can the kit carry a stock stream, waterfall, river or
lake onto a kit island the way `world-forest` and `world-mountain` carry canopy and rock?

**The short answer:**
- **No "drop a stream on a lawn" verb is lawful.** The July census showed that stock has no standalone water
  feature. This recon confirms it and finds two more constraints.
- **Two lawful paths exist:**
  - A coastal river carried with its source and mouth, verbatim.
  - A falls inside a mountain ensemble, the way the horseshoe already rides.
- **Both need two cheap instruments first:** an offline eye that can see water, and a carry that keeps IDALLs
  verbatim. Today's kit sets area bits to 0 on every carried triangle, which this recon shows would change how the
  stream banks walk.

| file | what it does |
|---|---|
| `census.py` | Every disc-1 block's parts, every water-like part measured, and the Terrain's water topographs (-> out/census.json) |
| `anatomy.py` | For each water part, how it sits in its ground: hole, welds, height above the Terrain, bank topographs (-> out/anatomy.json) |

## 1. What was already settled (July)

From `../../overworld-topography/README.md` §"THE STANDALONE WATER-FEATURE CENSUS" and the KB
`project-ff9-overworld-interior-topography` ("THE STANDALONE-WATER CLOSURE"):
- **5 welded water systems** exist on disc 1, with **zero open tips**. Every river, stream or falls ends at the sea
  or at a massif. "Every stock river rises in a mountain."
- **The lawful carriable unit is the whole ensemble.** The horseshoe (Daguerreo) carries its falls, river and joint
  through `world-mountain`'s ensemble carry (in game, 2026-07-15).
- **Later unlocks named in July:**
  - Cluster D (18-20,10-13), the falls-to-sea system, as a massif ensemble.
  - Cluster C (16,14)-(17,14), the lowland river, as a coastal-river ensemble on a coast-aligned bench.

## 2. New measurements (census.py, anatomy.py)

**The inventory** (disc 1, blocks carrying each part):

| part | blocks |
|---|---|
| river | 10 |
| stream | 7 |
| riverjoint | 6 |
| falls | 3 |
| volcanocrater | 2 |
| volcanolava | 1 |

Each part carries one topograph on every triangle: river and riverjoint 48, falls 50, stream 51. The (16,15) and
(19,11) joints carry a few 51s. The Terrain itself carries only 2 water-topograph triangles map-wide.

**THE CHANNEL PLUG LAW.** Every stock water part plugs a hole in its Terrain:
- 100% of every part's plan footprint has no Terrain under it. The (14,17) river is 93%.
- Its boundary welds to Terrain vertices. Every stream is welded all round (53/53, 41/41, 35/35, ...).
- It is the building law (every stock building plugs a hole, `../forms/`) and the canopy's carve-and-seat, in water.

**Banks.** The Terrain ring a water part welds to is one topograph per system:
- 62 for every stream and the (19-20,10-11) river: the steep stream bank;
- 58 at the horseshoe;
- 49 (rock) for the (14,17) plateau river.

Cluster C's channel:
- 188 topo-62 bank triangles, 56-74 deg (p10-p90), dropping from lawn at y 3.16 to water at 0-1.
- The bank meets grass (143) and forest canopy (40).
- Kit islands mint lawn at 3.2, so the channel's depth matches our ground exactly.

**THE BANK SKIP LAW (new).**
- The engine's ground query skips three IDALLs outright (`WMPhysics.cs:15-29`): 4078 (area 15, topo 59), 4088
  (area 15, topo 62) and 2040 (area 7, topo 62). It also skips any triangle with up·normal <= 0.1.
- 177 of the map's 480 bank triangles carry 4088 or 2040, and 177 of cluster C's 188 do. Cluster D's banks use areas
  0, 22 and 23 and are not skipped.
- So the AREA bits on a bank are physics, not only dispatch context.
- `world-mountain` and `world-forest` strip the area to 0 on everything they carry (`strip_dispatch`, which exists
  so that a carried tri cannot fire an entrance or the camera bucket). Applied to these banks, it would turn every
  skipped bank into a ground-query hit. No gate today would notice.

**The parts' own IDALLs carry areas too.** The (14,17) river is all area 14, the (16,15) joint mixes areas 0, 5 and
16, and (19,11)'s falls and river carry area 22 on some triangles.

**A recorded claim the bytes contradict.**
- The horseshoe write-up (`../../overworld-topography/README.md:381, 413-418`) says stock aux parts carry
  "leftover REAL tangents whose x garbage-decodes to topo 0". That is why the ensemble carry stamps them topo 49
  (THE SCENERY SEAL).
- The census decodes every stock water triangle cleanly (48 / 50 / 51, and the horseshoe's too), matching the KB's
  own "water features are PARTS" table.
- The seal may still be right for the horseshoe: its parts are blocked in stock too, because 48 and 50 are closed to
  walkers. But it is not "garbage", and sealing a STREAM (51) as 49 would change which chocobos can cross it (below).
  Re-check before reusing the seal.

## 3. Engine facts (read in `C:\gd\FFIX\Memoria\Assembly-CSharp\`, verified in code)

- **Parts and registration order.** The prefab fields are Terrain, Object, Terrain2/Object2, Beach1/2, Stream, River,
  RiverJoint, Falls, Sea1-6 and Volcano* (`WMBlockPrefab.cs:6-50`). `LoadBlock` registers Object, Terrain, form-2,
  Volcano, Beach, Stream, River, RiverJoint, Falls, Sea (`WMWorld.cs:600-828`).
- **Every registered part is a walk mesh** (`WMWorld.cs:873-882`). The ground query casts only into the block under
  the actor:
  - it tries the 10 most recent triangles first;
  - it then returns the first MESH in registration order with any hit, and the first triangle in it
    (`WMBlock.cs:145-200`, `WMPhysics.cs:13-41`).
  - So a water part reports its own topograph only through a Terrain hole, exactly as stock builds it.
- **The topograph** is `(int)tangent.x` of the triangle's first vertex (`WMBlock.cs:210`). Overrides must be unwelded
  (vcount == icount) and must carry tangents (`WMBlock.cs:56-73`, `WMPhysics.cs:22`).
- **Who may enter water** (`ff9.cs:1467-1754`, check at `:5924-5939`):

  | mover | water topographs it may enter |
  |---|---|
  | foot, yellow chocobo | none |
  | light-blue chocobo | 51 (streams) |
  | red chocobo | 49-55 |
  | deep-blue, gold chocobo | 48-57 |
  | boat | 53, 54, 57 only (never a river) |

  Chocobos cannot step directly between ground and water topographs (`:5703-5716`). Standing on 51 or 48 sinks the
  party (sink indices 6 and 7).
- **Animation is per material, driven by `WMRenderTextureBank`:**
  - Falls and Stream: a shader `_Offset` scroll.
  - River and RiverJoint: a 6-frame flipbook.

  A carried part animates as long as it binds the prefab's own material. A per-part PNG clones the material and
  freezes it (`WMWorld.cs:857-871`).
- **Effects.** No sound or SPS is attached to a water mesh. The `AlexandriaWaterfall` SPS spawns at fixed world
  coordinates (`ff9.cs:3571-3587`). Movement splashes key off the topograph under the actor (`ff9.cs:6184`,
  `:6396-6427`), so they come with the part's topograph for free.
- **Binding.** A Stream/River/Falls override binds only if the cell's EFFECTIVE prefab has that child. On a kit
  (IsSea) cell, that means the `Donor.txt` divert must name a block that has it (`WMWorld.cs:525-573`,
  `:848-850`).
  - Every donor part without an override renders the donor's stock mesh at its block-local pose, and walks.
  - A blank needs at least one (zero-area) triangle: 0 indices crash `AddWalkMesh`.
  - No block has every water part. A coastal stream must divert to (16,15) (stream, joint, sea, beach); a falls
    plus stream to (19,11) (no sea).

## 4. What the kit can already do with water

- **`world-mountain`'s ensemble carry** (Object, Falls, River, RiverJoint) is in game on the horseshoe.
  - Stream is not in `ENSEMBLE_PARTS`.
  - A widened falls that straddles a block border refuses (the census MISS; `../mountainspread/NOTES.md`).
- **`world-transplant` at rot 0 / shift 0 carries a river verbatim already.** The parts it does not take render from
  the donor prefab at their stock pose. A dry run of cluster C's rect, donor (16,14) 2x2 onto (20,0):
  - every weld gate passes: stitch 1,388 welds, 0 torn; census 0 introduced, its 179 misses inherited (the channel
    holes the stream fills); T-junctions 0;
  - **only `land-fit` fails: the rect is a cut of a continent.** Land crosses its W, N and E edges, and the channel
    comes within 3.0u of the W edge (the source lies just beyond it, at the rock). It is 10u from N, 23u from E and
    30u from S, the sea side.
- **`world-sink`** drops or blanks Stream with its island (in place only).
- **The offline renderer draws none of them.** `render.PARTS` is Terrain, Object, Beach1, Sea1-5: the offline eye is
  blind to rivers, falls and streams.

## 5. The paths, ranked

**R0 -- the two instruments every path needs (offline, no game).**
1. **The offline eye sees water.** Add Stream / River / RiverJoint / Falls to `render.py` with their real
   materials' textures (frame 0, as the sea). Accept: the stock (16,14) and (19,11) render as in a game still.
2. **A faithful-IDALL carry mode, and a gate that proves it.** Keep the donor's IDALL on every carried triangle that
   the ground query treats specially (the skip set, the water topographs and their areas). Gate: each carried
   triangle's ground-query VISIBILITY (skipped or hit) equals the donor's. Break-it: `strip_dispatch` on cluster C's
   banks must fail it on 177 triangles. The existing dispatch strip stays for event bits (entrances) and for any
   triangle the ground query reads normally.

**R1 -- the coastal river, verbatim (cluster C), on a bench of its own coast.**
- **What:** the rect that holds the WHOLE system: the source's rock to the west, the channel, the sea mouth at (16,15).
  That is about 3x2 blocks. It is carried by the region transplant at rot 0 / shift 0, so the river, joint, banks and
  mouth are stock bytes, already weld-clean.
- **The only authored surface is the coast on the three land cuts.** Use `cut_census` to place the cut lines as far
  from the channel as possible; the coast morph verbs close them. The river is never touched.
- **Accept:**
  - offline: every gate, and R0's visibility gate holding on every bank;
  - in game: the stream animates, its banks walk as stock (the probe: a walk at the bank stops as at home, a light-blue
    chocobo crosses, a yellow one does not), the mouth reads as stock, and the owner's eye passes it.
- **Cost:** medium-large. The coast closure is the risk, as THE DEFECT FOLLOWS THE AUTHORSHIP predicts.

**R2 -- a falls in its mountain (cluster D, or a new massif donor).**
- **What:** `world-mountain`'s ensemble carry with Stream added to `ENSEMBLE_PARTS` and `Donor.txt` -> (19,11).
- **But:** cluster D's falls drops from a plateau at 26 to the lowland, and the plateau is not a qualified massif. It
  needs its own anatomy study first (as comp26/comp10 do, `../mountaindonors/NOTES.md`). Parked behind R1.

**Not recommended:**
- **A stream drawn or minted by the kit:** THE FORM LESSON; stock has none to copy the shape from.
- **A channel segment cut from a river and capped at both ends by kit mountains:** every cap is an authored join,
  and stock never shows a stream ending at a foot it was not born at.

**Lakes are a separate recon.**
- There is no lake part; a lake is Sea1-5 at an inland margin.
- `census.py`'s "inland sea" list is mostly bays (Sea3 at y 0 in blocks without Sea4); (17,10), (14,4) and (4,8) are
  unconfirmed.
- The recorded lake shores are at y 0.2 at (3,12), (4,13), (5,13), (7,17) and (9,17) (coast-mosaic).
- Start with a connectivity census: is each Sea component joined to open ocean?

## 6. Open (unmeasured)

- Whether a SKIPPED bank behaves differently in game from an area-0 one. Inferred from the code only; an in-game A/B
  on a transplanted bank would settle it, and R0's gate assumes it matters.
- How much coast R1's three cuts mint, at the best `cut_census` lines.
- Disc 4: `discmirror` pins the horseshoe's water parts because they differ there (`disc4/NOTES.md`). Cluster C's
  disc-4 bytes are not checked.
- The horseshoe's SCENERY SEAL against its parts' real topographs (§2): blocked either way on foot. But the red
  chocobo may enter 49 and not 48, so the seal opens a carried RIVER to it. Sealing a STREAM (51) as 49 would shut out
  the light-blue chocobo, which stock lets in. Falls (50) are unchanged for every mover.
