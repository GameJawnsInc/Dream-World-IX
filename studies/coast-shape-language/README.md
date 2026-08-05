# Coast shape language — what outlines does stock FF9 actually build?

The **outline** half of the overworld surveys. `studies/overworld-topography/` answered
*what is inland made of*; this answers the orthogonal question the coast arc reached
after the V-shore corner closed: **what is the stock world's coastline vocabulary**, and
which parts of it can our builders reproduce.

Reads your own FF9 install; **no game bytes live in this repo**, and nothing here writes
to the game or a mod folder. Regenerates in ~4 minutes:

```bash
py studies/coast-shape-language/shape_census.py --disc 1
```

```bash
py studies/coast-shape-language/shape_probe.py --disc 1
```

```bash
py studies/coast-shape-language/outline_render.py --disc 1 --px 3
```

| script | emits |
|---|---|
| `shape_census.py` | `out/landmask_d1.npz` (`land`, `foot`, `hgt`, `topo` on the 4u lattice), `out/outline_d1.json` (landmasses + shape metrics) |
| `shape_probe.py` | `out/shapes_d1.json` — located instances of six outline classes |
| `outline_render.py` | `out/outline_d1.png`, and `--mass N` crops to one landmass |

## The two masks are not the same question

* **`land`** — any Terrain tri in the cell. The outline; what reads as land from offshore.
* **`foot`** — foot-legal topographs only. Where a player can actually stand.

**28.6% of the world is land; 18.5% is standable — 35% of all land is un-standable cliff
and mountain.** Coast-shape work wants `land`, reachability work wants `foot`, and the
interesting design questions live in the difference: *a cape you cannot walk out onto is
scenery, not a destination*, and stock builds a great deal of exactly that.

The first cut of the census built only `foot` and reported 102 "landmasses" — mountain
rock (topo 49) is foot-illegal and covers 164 of disc 1's 260 blocks, so the foot mask
fragments every continent along its ranges. It was measuring the walkable partition, not
the coastline.

## The measured vocabulary (disc 1)

| class | what it is | instances | range |
|---|---|---|---|
| bay | concavity closed by a mouth narrower than itself | 70 | depth to 27u |
| cape | land an opening removes — a limb thinner than 2r | 80 | reach to 106u |
| lagoon | sea unreachable from the open ocean | 14 | all ≤ 528u² |
| strait | narrowest water between two substantial masses | 11 | 16–70u wide |
| isthmus | a neck whose cut would split its mass in two | **8** | 8–24u wide |
| chain | ≥3 small masses whose dilations merge | 4 | biggest 16 islands |

Landmasses: 57 components, 31 of ≥16 cells, 4 continent-scale.

## Calibration matters more than the counts

Three detectors were wrong on their first run and every one would have produced a
confident, wrong design menu. They are documented in the source docstrings so they are
not reintroduced:

1. **cape reach** ran outside the cape's own landmass — an islet with no core measured
   its distance to *another continent* and scored a 357u headland (real max: 106u).
2. **strait** found "sea near land", which is a band around every shore in the world —
   three ~100k-u² "straits" that were one coastal ring.
3. **isthmus** reported only each mass's thinnest neck and counted cuts that shaved a
   pebble off a coast — 20 → 338 → 8 once both sides had to survive.

The arc's standing law applies: *calibrate the instrument before you judge with it.*

## Where the conclusions live

`SHAPE-SCOPING-PREDICTION.md` — the registration (predictions S-1…S-4, the stop rule)
and the scored findings.
