# A carried mountain, wider (`world-mountain --spread`)

`world-forest --spread` widens a carried canopy in plan (in game to x1.5, terrain study X3), and
`world-mountain --rock-height` stretches a carried massif upward (to x2.0, X1). Nothing yet widens a massif, so
every carried mountain keeps its donor's footprint: Uaho is always 40u across. This lane adds the massif twin of
the forest's spread. With a matching rock height, it gives a uniform scale.

| file | what it does |
|---|---|
| `sweep.py` | Offline: the five qualified massifs on benches of their home ground at x1.0 / 1.25 / 1.5 and four angles, plus the uniform scale (S1-S4) |
| `lab_build.py` | The four in-game variants (Uaho, rigid / x1.25 / x1.5 / x1.5 scaled whole), carved by the kit's own `world-mountain` |
| `lab_prep.py` | The run's registered predictions from the built files (summit, ring, views, walk lines) |
| `lab_install.py` | Puts the lab first in FolderNames for one session and takes it out again (ini restored byte-exact) |
| `lab_session.py` | The in-game run (P1-P4 and the owner's stills) |
| `lab_post.py` | The owner's labelled panels |

`out/` (gitignored) holds the sweep's rows.

## 1. The map

`carve_mountain` already sends every donor position through one map, `rot_pt`: the carried rock, the rim nodes,
the hole polygon, the aperture plugs and the ensemble parts (falls, river, Object). `spread` scales the plan
offset from the blob centre inside that map before the turn: `c + R(theta) s (p - c)`, height kept. Because every
site uses the same function on the same input floats, welds stay exact. Normals take the inverse transpose,
`(nx/s, ny, nz/s)`, at their original length. UVs, topographs and the plug chart are the donor's.

What else had to know:
- **Sizing.** The span is chosen from `r_rim` before any placement (the single-block route needs
  `2 (r_rim + band) <= 64`), so it uses the widened radius. Uaho at x1.25 (r 25) therefore leaves the byte-frozen
  single-block pipeline for the multi-block span the crag, comp20 and the horseshoe already use.
- **The rock-rigid gate** measures the carry against `dVref`, the declared shape. At spread s that shape is the
  donor widened s times in plan about the same centre, so any deformation the map does not declare still trips
  `MTN_ROCK_RIGID`.
- **Unchanged and still right:** the plug chart (fitted in the donor frame), the 9u zip-edge gate (zip edges
  only; carried rock edges are stock-given), the apron (world frame), the peak cap (heights are kept).

`spread = 1` skips the multiply, and the Uaho July identity nets stay green.

## 2. Registered before the sweep

- **S1:** the x1.0 rows reproduce round 19's verdicts.
- **S2:** every angle that passes at x1.0 passes at x1.25 and x1.5.
- **S3:** the rigidity drift at x1.25 / x1.5 equals the x1.0 drift at the same angle (within 0.2 points). The
  only undeclared deformation is the de-tilt, and the map scales it with everything else.
- **S4:** every zip chord stays under the 9u gate. **The risk:** rim edges grow s times, as the forest's did
  (THE RIM GRAIN, `../canopyspread/NOTES.md`). A coarse rim at x1.5 may need the same split.

## 3. Offline (`sweep.py`)

The first run (the map alone) refused 8 of 48 widened carves at one gate: comp20 and the desert peak at x1.5,
every angle, on the 9u edge (chords 10.2u and 9.2u; rise, envelope, rigidity and apron all clean). That is S4's
risk, and the forest's answer applies.

**THE RIM GRAIN, for the mountain** (`interior._mountain_rim_grain`). Split every outer rim edge whose widened
plan length passes the donor's longest rim edge, by fanning the blob tri that owns it from its opposite corner:
position, UV and normal lerped along the edge, a planar split that renders the same. It runs on the donor blob
AFTER the de-tilt fit and AFTER any `--rock-height` map, so neither changes. Two leaks were found and closed on the
way:
- the midpoints first fed the seat's median rim height, and the carry sat 0.04u higher (Uaho 12.09 against
  12.05). The seat now reads the donor's own rim;
- they also first joined the rock-height pins (42 against X1's 30), which moved the height map (rise +4.24u
  against X1's 4.139u). The map now runs first, on the donor's own rim, and the split lerps what it made: the
  uniform scale's rise is +4.14u, X1's to the millimetre.

The second run, against the registered rows:
- **S1 holds:** every x1.0 row passes, except the horseshoe at 200 deg (the zip envelope, 3 banks). That is
  today's kit with no spread, and round 19 did not sweep the horseshoe.
- **S2: 46 of 48 widened carves pass**, the uniform scale included (8/8). Uaho, the crag, comp20 and the desert
  peak pass every spread at every angle. The two refusals are the horseshoe at x1.25 / 30 deg and x1.5 / 200 deg:
  a census MISS beside its falls mouth. Ensemble components are assigned whole to the block holding their
  centroid, so a widened one that straddles a block border leaves a sample there with no ground. The census
  refuses those placements, as it should. Not built: splitting ensemble parts at block borders.
- **S3 fails, in the safe direction:** the drift FALLS with spread (Uaho 3.15% -> 2.51% -> 2.06%, the others alike).
  The prediction was wrong: the de-tilt's height shear is not widened, the edges it is measured against are.
- **S4 holds:** the largest zip chord over every clean carve is 8.6u (8.9u before the rim grain).

| donor | x1.0 | x1.25 | x1.5 | x1.5 + height x1.5 | rigidity (x1.0 -> x1.5) | peak |
|---|---|---|---|---|---|---|
| uaho | 4/4 | 4/4 | 4/4 | 2/2 | 3.1 -> 2.1% | 12.05 / 16.13 tall |
| crag | 4/4 | 4/4 | 4/4 | 2/2 | 0.7 -> 0.4% | 22.4 / 32.01 tall |
| comp20 | 4/4 | 4/4 | 4/4 | 2/2 | 0.6 -> 0.4% | 21.76 / 31.0 tall |
| desert-peak | 4/4 | 4/4 | 4/4 | 2/2 | 1.0 -> 0.7% | 14.48 / 20.11 tall |
| horseshoe | 3/4 | 3/4 | 3/4 | (refused: --rock-height) | 0.8 -> 0.6% | 30.9 |

Re-run after both leak fixes: the same verdicts, and every widened carve now seats exactly where the rigid one
does (Uaho 12.05 and the desert peak 14.48 at every spread). The desert peak scaled whole reads 20.11, round 19's
x1.5-tall variant C to the hundredth: the split adds nothing to the height map.

**Offline renders** (`world-render --around 1386,-104 --ground-y 3.2` over each lab variant, out/lab/render/):
the overview reads as built (B and C wider and lower, D the same mountain scaled whole), no stray geometry, 0
sky-coloured pixels in any close or top view. One white pixel at the rock foot in C and D: an alpha-0 texel
(the renderer's blank-tile rule) inside an ORIGINAL Uaho rock tri's UV window (2 of its 9,761 texels; the rigid
carry has the same one tri). The x1.5 camera lands on it, the rigid one misses it. Donor content, not the map.
