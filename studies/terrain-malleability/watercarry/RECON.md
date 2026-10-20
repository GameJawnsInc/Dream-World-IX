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
| `still_session.py` | R0: read-only in-game stills of the stock river and falls (the renderer's calibration) |
| `ensemble.py` | R1: cluster C's river ensemble (parts + welded banks) and its boundary classed LAWN / SEA / ROCK (-> out/ensemble.json) |
| `seat_dryrun.py` | R1: the ensemble seated verbatim into a minted grass bench -- hole, the ported apron (`--no-apron` to compare), DP zip, gates, failures localized (-> out/seat.json, out/seat_plan.png) |
| `mouth.py` | R1: the stock mouth -- what its sea edge welds to, the bands round it, the beach arcs it splits (-> out/mouth.json) |
| `lips.py` | R1: the bay's two rocky lips against the kit island's lip, in the coast laws' terms (-> out/lips.json) |
| `closure.py` | R1: candidate fragment boundaries, THE COMPONENT CLOSURE and THE MINIMAL FRAGMENT, each boundary classed (-> out/closure.json) |
| `fragment_run.py` | PLAN rung 0: the kit's `world/river.py` fragment for cluster C, its F1/F2 gates and a plan (-> out/fragment.json, out/fragment_plan.png) |
| `outline_run.py` | PLAN rung 1: cluster C's kit outline, its custom-outline mint and the J1-J4 join gates, with plans (-> out/outline.json, out/outline_plan.png, out/outline_join_{E,W}.png) |
| `compose_run.py` | PLAN rung 2: cluster C composed onto open ocean, every gate and the binding plan, with plans (-> out/compose.json, out/compose_plan.png, out/compose_{E,W,NE,mouth}.png) |
| `write_run.py` | PLAN rung 3: cluster C written to a scratch folder (out/river_mod), the knit, W1 + B1 on the bytes, then `world-render --stock` and four seam views (-> out/write.json, out/river_render/) |

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

**R0 status: DONE (2026-10-19).**
- **The eye.** `render.PARTS` has the four water parts, with their engine textures: River and RiverJoint flipbook frame
  0, Falls and Stream materials at scroll offset 0. `world-render --stock` draws what the engine binds where no override
  exists (`render.effective_prefab`: own prefab / Donor.txt divert / SeaBlockPrefab).
  - Offline it shows the (19,11) twin falls and cluster C's river to its sea mouth.
  - In game, read-only stills of both places show the same channels, banks, falls and forests (`still_session.py`,
    runs `20261019-210537-water-stills` and `-d`; `out/r0_calibration_panel.png`). The game adds mist and lighting,
    which are in the renderer's blind-spot list.
- **The gate.**
  - `interior._strip_dispatch` keeps any IDALL in `placement.IDALL_SKIP`.
  - `placement.skip_parity_gate` refuses a carry that changes a tri's ground-query visibility; `carve_mountain` runs it
    and reports `skip_parity`.
  - On cluster C's real banks, the old strip flips 177 of 188 tris and the new one 0, as predicted. A hermetic break-it
    restores the old strip and is refused by name.
  - No existing donor changed a byte: the Uaho identity nets are green.

**R1 -- the coastal river (cluster C).** The region framing below was CLOSED by the offline round (2026-10-19); the
ensemble framing replaces it.

*The region carry: closed by THE FUSE LAW.*
- Cluster C sits on a 97-block landmass: the east Mist Continent, blocks x 11-22, y 8-18 (a block flood-fill of its
  land).
- No rect closes on open water. Every candidate rect's perimeter crosses land:

  | rect | perimeter | land crossing |
  |---|---|---|
  | 2x2 | 512u | 370u (72%) |
  | 3x2 | 640u | 425u (66%) |
  | 4x3 | 896u | 690u (77%) |
  | 4x4 | 1024u | 788u (77%) |
  | 6x5 | 1408u | 1112u (79%) |

  That is how much coast each would have to MINT from nothing. The kit has no lawful verb for it: land never knits, and
  the ladder mint is falsified. `cut_census`'s lawful lines are open-water lines, and there are none round a continent
  cut. The 2x2 dry run is weld-clean and fails `land-fit` alone (§4).

*The ensemble carry (`ensemble.py`, `seat_dryrun.py`).*
- **The unit** is the river's own parts (Stream, RiverJoint) plus every topo-62 bank welded to them: 188 tris, none
  left out, 177 of them on skipped IDALLs. It is CLOSED (0 open edges). Its outer ring, classed by what it welds to at
  home:

  | boundary | length | what it is | machinery |
  |---|---|---|---|
  | LAWN | 373.3u | grass and forest | the canopy carry's |
  | SEA | 20.6u | the mouth, at about (1035-1050, -986..-994) | none yet |
  | ROCK | 5.7u | the source, welded to the escarpment's foot at (1128.6, -918) | rock contact |

- **The seat dry run** puts the unit, bytes verbatim, into a minted r90 grass bench. It is shifted, and levelled so the
  lawn-side rim median sits at the bench's 3.2. Then: the hole along the outer ring + 2.5u, the kit's DP zip on exact
  floats, and the gates. Plan in `out/seat_plan.png`.
  - **Pass:**
    - the hole drops 354 tris, all plain grass, in one ring;
    - max zip chord 8.25u (< 9);
    - skip parity holds on every bank;
    - 686 census points hit stream or joint water through the bank holes.
  - **Fail, localized to the nearest boundary class:**

    | failure | at the mouth (SEA) | on the lawn |
    |---|---|---|
    | zip rise past 2.34 or ny < 0.5 (rise max 3.03, ny min 0.033) | 16 | 9 |
    | new once-edges | -- | 3 |
    | introduced census misses (360 donor vs 368 seated) | -- | 8 |

  - **The rim heights explain the lawn ones.** The LAWN rim is level (p10-p90 2.32-3.63 against the bench's 3.2), but
    12 of 194 rim verts sit more than 1u off: the home lawn falling toward the sea beside the mouth (0.5-2.0), and one
    4.3 rise at the north bend.
  - **The mouth sits at sea level (0.17-0.71),** 3u under the lawn. The source's rock contact sits at lawn height
    (2.9-3.8) and zips cleanly.

*Round 2 (offline, 2026-10-19): the apron, the true unit, and the mouth.*
- **The registered prediction FAILED as stated.** With `world-mountain`'s apron ported onto the lawn ring (367
  positions lifted, max 0.86u, apron slope 4.4 deg), the lawn failures barely moved: steep zip tris 9 -> 7, cracks
  3 -> 3, introduced misses 8 -> 8. The rim heights were not the cause. Localizing every failure by distance to the
  mouth found two missing members of the ensemble:
  - **The source's own water tri.** The unit had a second ring, a 3-point hole (7.4u, 1.3u^2) at the source,
    (1127.4, -917.9). At home a single Terrain tri plugs it: IDALL 4044 (area 15, topo 51), one of the map's two
    "channel markers". Leaving it out caused all 3 cracks and 3 of the misses.
  - **The crossing.** Six ring edges at the bend weld to the Object, not to grass. The Object splits into a separate
    76-tri structure (x 1079-1097, y 7.95-15.85, never welded to the river) and a 40-tri BRIDGE at (1028-1035,
    -955..-960), welded to the channel by 24 verts. The bridge has a walkable topo-52 deck (IDALL 4050) on skipped 4078
    sides. Leaving it out made the rim dip to 2.12 there, giving 4 steep zip tris and 5 misses.
- **THE ENSEMBLE IS WIDER THAN THE PARTS.** A stock water feature's lawful unit is its parts, plus the carved banks,
  plus the Terrain's own water tris that close it, plus the Object that crosses it. With all four, the seat is clean
  on the lawn side:

  | gate | result |
  |---|---|
  | rings | 1 |
  | new once-edges | 0 |
  | introduced census misses | 0 (360 seated = 360 donor) |
  | skip parity | 0 flips (201 skipped IDALLs kept) |
  | steepest zip ny | 0.726 |
  | max chord | 8.25u |

  Every one of the 20 remaining zip failures (rise to 3.09) sits within 4.9u of the mouth.
- **The apron is not needed here.** The same full unit seated WITHOUT it (`--no-apron`) is equally clean on the
  lawn side: 0 cracks, 0 introduced misses, steepest zip ny 0.701 against 0.726 with it, 21 mouth failures against
  20. The lawn rim is level enough (p10-p90 2.32-3.63 on a 3.2 bench) that the lift buys nothing measurable. Leave
  it out: it is authored surface, and THE DEFECT FOLLOWS THE AUTHORSHIP. Keep it for a bench that is not level.
- **The mouth (`mouth.py`).**
  - The unit's 20.6u sea edge welds to mid water: sea3 4, sea1 1, sea2 1. Within 6u: sea3 12, sea1 4, sea2 2, beach1 6.
  - The river SPLITS a sandy shore (topo 31): two beach arcs each end about 2.4u from the mouth.
  - Their far ends, 65u (W, 37 tris) and 92u (E, 50 tris) from the mouth, both weld to the rocky lip (topo 58).
  - So the smallest CLOSED coastal assembly holding the mouth is the whole ~157u bay, lip to lip. Splicing it into a
    kit coast means a cliff-to-cliff join at each lip, which the coast law index calls the hard case: independently
    authored cliffs never meet cleanly. That is R1's one remaining problem, now scoped.

*Round 3 (offline): can the bay's lips meet the kit's lip? (`lips.py`)*

The coast law index says independently authored cliffs never meet cleanly. The kit's cliff, though, is not independently
authored: `island.py` mints it from the stock measurement. Measured per wall tri (topo 58) near each lip and round
the kit's r90 ring:

| measure | stock E lip (33 tris) | stock W lip (14) | kit ring (332) |
|---|---|---|---|
| crest height p10 / p50 / p90 | 1.72 / 2.79 / 3.55 | 2.42 / 3.42 / 3.75 | 3.2 flat |
| base height | 0 | 0 | 0 |
| run p50 (crest to foot) | 0.96u | 1.32u | 1.0u (`rim_run`) |
| slope p50 | 72.8 deg | 70.9 deg | 72.7 deg |
| crest v / base v | 0.893 / 0.923 | 0.893 / 0.923 | 0.893 / 0.923 |
| u per unit of shore, p50 | 0.015 | 0.014 | 0.013 |
| land on top | grass | grass | grass |
| water at the foot | sea4 32, sea3 18, sea5 7, sea1 5, beach1 4, sea2 3 | sea3 21, sea1 4, beach1 1 | the cut Sea4 sheet only |

- **The same wall language:** slope, the corner-role V rows, the U density, the base, the grass on top.
- **Three things a join must solve:**
  1. **Crest height.** The kit's crest is flat 3.2; the stock crest wanders. Join columns at the kit's height exist on
     both lips: E at 19.5u past the beach end (crest 3.11, u 0.824) or 23.0u (3.07, u 0.947); W at 29.8u (3.29,
     u 0.752) or 39.7u (3.01, u 0.762). Within 0.1 of 3.2, so a join there needs no crest blend beyond a snap.
  2. **U phase.** The kit's U is one global arc length round the ring. Both joins must land on the stock u at their
     columns (0.824 and 0.752, say), so the kit arc between them has to be resampled to that phase: THE COLUMN
     QUANTIZATION LAW, which the coast morphs' FREE EQUAL-ARC RESAMPLE already solves (total columns, mod 4).
  3. **The water.** The stock feet are fronted by the bay's ladder (sea3, sea1, beach); the kit's only by Sea4, and
     sea3 may never touch sea4 (THE LATTICE ADJACENCY LAW). Water knits (THE FUSE LAW): the rim-retile family re-bands
     a sea3 or sea5 crop seam. That is lawful machinery, not new.
- **So the bay assembly** is about 200u of stock coast: the 157u bay plus ~20u (E) and ~30u (W) of cliff to the join
  columns, both of which already match the kit's crest. It carries verbatim and joins the kit wall at two columns
  where the profiles agree.

*Round 4 (offline): is there a fragment that cuts no component? (`closure.py`, plan in `out/bay_plan.png`)*
- **The shape.** The river comes from the north-east, bends west and runs south to its mouth at the top-left of a
  large cove. The cove holds a small beached island and opens to deep sea at the south-east. E sits on a headland
  tip (its wall faces east); W is on the cove's south-west shore.
- **The landward boundary must cut only lattice ground** (grass, sand). A forest canopy, a rock massif and an Object
  carry whole or not at all. Convex hulls of the river + cove, grown 6u and 12u, cross 76 / 66u of forest and
  58 / 135u of rock.
- **THE COMPONENT CLOSURE** (add every whole forest and Object touching the set) still meets rock for 138u: the three
  forests here stand at the escarpment's foot.
- **THE MINIMAL FRAGMENT:** 1,397 tris. It is the river ensemble (parts, banks, source marker, bridge) plus the cove
  assembly: 879 water and beach tris on the bay side of the W-E chord, 158 lip, sand and beach tris closed along the
  coast, and the island (59). Forests and the tower are LEFT HOME, not cut: a component beside the fragment is not
  part of it.

  | boundary class | length | what it is |
  |---|---|---|
  | grass | 592.3u | the zip |
  | water | 143.0u | the knit, all along the chord |
  | forest | 48.6u | canopies beside the river bank, left home |
  | lip | 26.4u | 3 edges at the join columns, plus a few back rows mid-bay |
  | sand | 20.5u | back rows mid-bay |
  | beach | 9.1u | back rows mid-bay |
  | rock | 5.7u | the source contact, 110-190u from the joins |

  So the bay carry is lawful in TOPOLOGY, with one correction below.
- **CORRECTION: the straight chord cuts the island.** Sampled every 0.5u, the 115.3u W-E chord crosses:

  | from W | what it crosses |
  |---|---|
  | 0-40u | water: sea3, sea5, sea3 |
  | 40-74u | the ISLAND: lip, grass, sand, beach |
  | 74-78u | 4u of sea1, the island's shallows |
  | 78-107u | water: sea3, sea4, sea5, sea3 |
  | 107-115u | the E headland's tip: lip, grass, lip |

  The minimal fragment's island flood was clipped to the bay side, so it carried HALF the island. The "mid-bay back
  rows" (sand, beach, lip ~60u from both joins) are its other half: a component cut, not a tail. The fix is in the
  plan: the seaward boundary is a polyline through mid and deep water only (sea3/sea5/sea4), routed seaward of the
  island's whole shallow ring and reaching each join base from the water.

*What R1 still needs: the composition, which is a kit-feature build, not a study script.*
1. a mint that takes a custom outline: the kit arc from E round the land to W, closed by the chord;
2. the opening: drop the mint inside the fragment's footprint, insert the fragment verbatim;
3. an OPEN-chain zip between the kit lawn's hole arc and the fragment's land boundary, crest E to crest W
   (`interior._zip_dp` is cyclic);
4. the two join columns: snap the kit's outline and rim verts onto the stock base and crest, and set the U of the
   join-adjacent kit wall to the stock u (0.8242 at E, 0.752 at W), with the kit arc resampled to land both phases;
5. the water along the chord: the fragment's bands against the kit's Sea4, re-banded by the rim retile;
6. the source: a `world-mountain` massif seated so its foot meets the source tip;
7. every gate (crack, grain, weld audit, census, Wang carry, skip parity), then a scratch-folder deploy and the
   offline render (`world-render --stock`).

Each step is authored surface. Built inside a study script, it would be the feature itself, built without a plan.
It belongs in the kit as a verb (`world-river`?) with its own tests, after a plan the owner signs off. Then one
in-game round: the river animates, the banks and bridge walk as stock, the mouth reads as stock, and the owner's
eye passes it.

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
