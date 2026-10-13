# More forest shapes: every disc-1 canopy as a `world-forest` donor (`--donor`)

`world-forest` carried one canopy, the (15,15) blob the July study found grass-bounded, so every kit forest had the
same outline (`--spread` / `--rot`, X3, only scale and turn it). This lane asks which stock forests can be carried
whole the same way, and teaches the kit to carry them.

| file | what it does |
|---|---|
| `census.py` | Every disc-1 forest blob (topo 36/37, >= 20 tris, the welded soup): size, rings, what its rim meets, walls, level, Object |
| `sweep.py` | Offline: the qualified donors on canopyspread's lab island, x1.0/x1.5 x 0/30/90/200 deg, every kit gate |
| `lab_build.py`, `lab_prep.py`, `lab_session.py`, `lab_post.py` | The in-game round (canopyspread's instrument, five donors) |

## 1. The census

44 blobs. QUALIFIED = one ring, >= 95% of rim length against grass, >= 90% of that walled (ny <= 0.1), rim spread
<= 1.5u, no Object in its bbox, topo 37 only. (15,15), the positive control, qualifies; so do four more:

| donor | tris | extent (u) | blocks | rim spread | wall rise |
|---|---|---|---|---|---|
| 15,15 (control) | 132 | 28.9 x 40.9 | (15,15) | 0.85 | 1.93 |
| 3,12 long | 85 | 16.8 x 32.0 | (3,12)-(3,13) | 0.64 | 1.91 |
| 19,8 round | 75 | 23.2 x 20.0 | (19,8)-(19,9) | 1.00 | 1.89 |
| 18,15 small | 59 | 18.9 x 15.6 | (18,15) | 0.09 | 1.95 |
| 13,15 grove | 41 | 12.1 x 17.3 | (13,15)-(13,16) | 0.62 | 1.90 |

The other 39: all 19 other lowland blobs meet rock (the rock stands on their canopy: THE CANOPY-FOOT LAW), and 20 are
plateau forest (topo 36, bounded by other ground at 26-28u). The 3 with an Object in their bbox fail on one of those
too.

## 2. The kit: `interior._forest_donor`

Reads the 3x3 blocks round `--donor`, the named block first (so a one-block blob keeps its tri order: (15,15)'s
bytes are unchanged, island E's identity net green), and takes the largest topo-37 blob with tris in that block
whose rim meets only grass. A rim edge across which lies rock or other ground refuses. (18,15)'s block also holds
part of a 116-tri blob that meets rock; the reader skips it for the 59-tri one. `chain_ring` takes a `min_len`: the
grove's rim is 11 points, under the July floor of 12 (a sanity guard); a forest rim's floor is 8.

## 3. Offline (`sweep.py`)

40/40 carves pass every gate (5 donors x {x1.0, x1.5} x {0, 30, 90, 200 deg}); texel density is exactly the donor's
/ s^2 per donor, anisotropy unchanged. The grove's worst single step at the rim is the highest, 2.10-2.19 (its
walls are tallest after seating, 2.05), under the 2.30 gate.

## 4. In game (`../ingame/RESULTS.md` section 33)

66/66 on one launch: each donor carved verbatim at one centre on the lab island, three walks each on, across and
off the canopy, every canopy point at its surface minus the sink, every grass point round it at its built height.
Pinholes 0-2 a frame. The owner, on labelled panels: "they read well to me". All four enter `donors.toml` as
qualified.

Untested: topo-36 plateau forests (they need a plateau host), a forest carried with the rock that stands on it.
