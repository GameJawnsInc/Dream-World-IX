# X3: a carried forest, wider and turned (`world-forest --spread` / `--rot`)

The uvclass study's X3 (`../uvclass/NOTES.md`, "Open items"): carry the (15,15) canopy with a plan stretch of x1.1
and x1.25. Its prediction, from the canopy's UV class (L.free: tile-scale charts of shared art): x1.1 faithful
(93.9% inside the envelope), x1.25 showing on some charts (78.9%). The same table says a turn about the vertical is
lawful for the canopy, and the canopy curtain has no light painted into one side (b = 0.13).

Why it matters: `world-forest` has ONE clean donor, so every forest the kit makes is the same 29 x 41u blob facing
the same way. A spread and an angle make each forest its own.

| file | what it does |
|---|---|
| `sweep.py` | Offline: the real canopy on the lab island at 4 spreads x 10 angles, every kit gate (S1-S3) |
| `lab_build.py` | The four in-game variants, carved by the kit's own `world-forest` command |
| `lab_prep.py` | The run's registered predictions from the built files (canopy, ring, views, walk lines) |
| `lab_session.py` | The in-game run (P1-P4 and the owner's stills) |
| `lab_post.py` | The owner's blind panels |

`out/` (gitignored) holds the lab island and the variants.

## 1. The map

`interior._forest_plan`: each donor vertex moves to c + s R(theta) (p - c) in plan, about the donor blob's centre c,
its height kept. A curtain's top and base share a plan point, so every curtain stays vertical. Normals take the
inverse transpose, (nx/s, ny, nz/s) turned the same way, at their original length. A whole number of quarter turns
is the exact coordinate swap (as `world-mountain --rot`); any other angle cos/sin; positive turns east to south.
`spread = 1` with no turn skips the map entirely: the verbatim carry, byte for byte (the island E identity net
stays green).

Everything downstream runs unchanged on the mapped blob: placement, the hole, the exact-weld zip, the per-station
rim lift (the canopy step law), the perimeter walk-in simulation and the placement census. The 9u max-edge gate
measures a canopy edge against its declared length (edge / s); zip edges keep the plain 9u.

The first sweep refused 3 of 40 carves, each at a different gate, and each traced to something the map exposes:

- **THE HAIRLINE CURTAIN** (x1.5 at 45 deg, census MISS). Two of the (15,15) blob's 48 curtain tris stand too
  steep for the engine's ground query (ny <= 0.1) yet keep a plan footprint 0.010-0.015u wide: both share one top
  corner set 0.0195u off the base corner below it. No down-ray grounds in that strip; the census refuses a carve
  when one of its 24 x 24 samples lands there. Stock ships it; the map widens it by s. A mapped carve sets that
  top corner on its base in plan (`CURTAIN_HAIRLINE` 0.05u x s); the verbatim carry keeps the donor's bytes.
- **THE RIM GRAIN** (x1.5 at 30 deg, a 9.1u zip chord). A spread rim edge is s times its donor length and the zip
  bridging it grows with it. A spread carve splits each rim edge longer than the donor's longest into equal
  pieces by splitting its curtain tri (a planar split, UV and normal lerped along the edge: renders the same).
  The split pieces are vertical to float noise (ny ~1e-13), so the forest's `down` gate now counts a tri only
  past a relative -1e-6.
- **THE ZIP SLIVER** (x1.25 at 200 deg, zip ny 0.07). Two hole nodes and a rim node almost collinear in plan: the
  greedy walk (and the mountain's minimal-chord DP, tried next) took the sliver. A mapped carve now zips with the
  mountain's DP (`_zip_dp`, shared), given a floor: a candidate tri steeper than ny 0.5 costs 1e6 more, so the
  strip routes round it. The mountain passes no floor -- its foot course is deliberately steep -- so its strips
  are byte-identical (the Uaho identity nets stay green).

The lab island: `world-island --center 1372,-84 --radius 58 --lobes 1 --patches 0 --seed 42` into
`out/lab/island/FF9CustomMap-lab` (blocks (20,0)-(22,2), open ocean, no live folder there). The placement needs the
blob plus ~11.5u of plain grass round it (the 6.5u scan band and the 5u coast margin): a x1.5 canopy is 44 x 62u,
75u across its diagonal. A first try at radius 48 had no lawful pocket for x1.5 at any angle, nor for x1.25 at most
odd angles. The r58 mint WARNs (2, no FAIL): grass windows at the island's block corners, and the sea-plan gate's
adjacent-block Sea4 ratio, which is infinite because the land covers block (21,1) whole (no deep-sea underlay there
to see).
