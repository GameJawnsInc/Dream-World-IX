# More mountain shapes: every disc-1 rock massif as a `world-mountain` donor, on its own ground

`world-mountain --donor` carries any real massif the gates accept, and four are catalogued as qualified (Uaho, the
crag, the horseshoe, comp20). The July census (`studies/overworld-topography/donor_qualify_scan.py`) found seven
more structurally qualified and promoted one (comp20); the rest were left as "rescue follow-ups". This lane re-runs
that census against today's kit, carves every candidate offline, and takes the clean one in game.

| file | what it does |
|---|---|
| `census.py` | July's scan, unchanged in its gates, qualifying EVERY shortlisted component (July: the 8 largest) |
| `sweep.py` | Offline: each candidate on a bench of its OWN ground family, 6 angles, every kit gate; Uaho the control |
| `home_render.py` | A massif at home, rendered from the stock bytes through the kit's renderer (`world-render` reads only deployed overrides) |
| `lab_build.py`, `lab_prep.py`, `lab_session.py`, `lab_post.py` | The in-game round (round 16's mountain instrument, on a desert island) |

## 1. The census: each massif has a home ground

13 lattice-sheet components are shortlisted; with today's kit, 9 qualify structurally. Their FEET (the topograph
across each rim edge at home) split them by ground family, and the catalogued donors measure the same way:

| donor | blocks | tris | radius | home ground (feet) | offline (sweep) |
|---|---|---|---|---|---|
| uaho (control) | 0,0 | 144 | 20.0 | grass (+ coastal rock) | 6/6 |
| crag (catalogued) | 10,5-6 | 294 | 33.7 | **desert** (17 only) | -- |
| comp20 (catalogued) | 12,16-17 | 178 | 31.5 | grass | -- |
| horseshoe (catalogued) | 5-6,15-16 | 713 | 54.3 | grass | -- |
| **comp23** | 19,3 | 139 | 26.1 | **desert** (17 only) | **6/6** |
| comp26 | 14-15,3 | 77 | 19.3 | desert, brush, coastal rock | 0/6 |
| comp10 | 14-15,14 | 373 | 37.4 | grass, forest | 0/6 |
| comp19 | 6-7,2-3 | 256 | 35.4 | snow | 0/6 |
| comp9 | 8-10,0-1 | 388 | 65.3 | snow | 0/6 |
| comp20 (this run) | 13-14,16 | 457 | 71.6 | (foot uneven by 15.1u) | not carved |
| comp3 / comp2 / comp4 | | 857-1288 | 83-98 | (object apertures) | not carved: a bench of r111+ |

Not qualified: comp0 (the continental rock network) and comp5 (an extra ring no part owns), comp27 (its blob
floods past the rock through an unsealed pocket, as Uaho's would without its alcove box).

The crag, carried onto grass in July, is a desert massif; its bench was later retiled to desert and the owner
passed THAT ground. comp20(July) appears here as comp21: component numbers are this run's.

## 2. The sweep, and the bench the control needed

Each candidate is carved onto a `build_landmass` bench minted in its own ground (`--ground`), 6 angles (0, 90, 180,
270, 30, 200), with `carve_mountain(near=...)` + `census_gate(parts=...)`.

**The first run's control FAILED** (Uaho 2/6): July's bench sizing, radius + 16.5u, put Uaho's apron on the
island's block borders near the coast, and its outer-border taper opened 5 once-edges along z = -128 (the gate
refused, as it should). At radius + 28u (Uaho: r48, its in-game bench) the control passes 6/6. Calibrate the
bench before reading a candidate: July's scan dry-carved three candidates on the tight bench and recorded their
refusals as the donors'.

The refusals that remain are each traced to a donor trait:
- **comp26, comp10: a vertical step in the rim.** Each rim has an edge of plan length 0.0 (comp26, twice) or 0.017u
  (comp10) rising 1.95u: at home the rock meets ground standing one step higher (comp10's is forest canopy, THE
  CANOPY-FOOT LAW: the rock meets the canopy). On a flat bench the zip can only close that edge with a vertical
  tri; the envelope gate refuses it (`zipNyMin 0.00`). Carrying them needs their raised neighbour (an ensemble),
  not a better zip.
- **comp19: a hillside.** Its rim spans y 2.8-20.4 (de-tilt 15.1 deg, residual 8.7u): there is no level foot.
- **comp9: a coarse rim.** Zip chords to 15.5u (the gate's ceiling is 9u) and a 3.55u zip rise.

## 3. comp23 at home, and on a desert island

At home (`home_render.py`): a brown rock peak 12.5u over its rim on the Outer Continent's red desert coast. The
kit's desert ground (THE DESERT TRANSLATION LAW) is the same red sand.

The lab (`lab_build.py`, out/lab/, gitignored): `world-island --center 1380,-100 --radius 55 --lobes 1 --patches 0
--seed 42 --ground desert` (blocks (20,0)-(22,2); 3 WARN rows, texture and sea-plan, of the island, none of the
mountain), carved by `world-mountain --donor 19,3 --ground desert --near 1380,-100`:

| variant | | placed at | peak y | gates |
|---|---|---|---|---|
| A | --rot 0 | (1382, -106) | 14.48 | clean (rigidity 1.0%, apron 3.5 deg) |
| B | --rot 200 | (1386, -102) | 14.48 | clean (1.0%, 3.2 deg) |
| C | --rot 30 --rock-height 1.5 | (1382, -106) | 20.11 | clean (1.0%, 3.8 deg) |

## 4. In game (round 19, `ingame/RESULTS.md` section 34)

Run `20261013-113037-mountain-donors`, **34/37**:
- P1: every stage reached the world; every summit read its variant (14.0625 / 14.0703 / 19.5117 vs 14.0588 /
  14.0663 / 19.5075).
- P2: 36/36 foot points read the built ground.
- P4: every home read 3.199.
- **P3 FAILED as registered on 3 of 6 walks** (A west, A east, B west): the walk "reached" its target distance
  instead of being blocked. Post-run, from the three failure state dumps (300 samples each): he never stood on rock,
  he followed the built surface to within 0.036u, and his lowest point (2.40) is the apron's own height at the rim
  (the ring reads 2.49-3.45). comp23 is a narrow peak: a walk aimed at its centre with a few degrees of facing
  error (A west: 5.4 deg) passes beside an arm of the rock and keeps gaining distance along the bearing. An aim
  instrument against a narrow massif, not a crack: round 16's walks met Uaho's broad face.

The owner judged labelled panels (`mountain_panel_*.png`). **Verdict: "yes"**: the desert peak reads as a stock
desert mountain at 0 deg, 200 deg and x1.5. It is qualified as `desert-peak` (`19,3`, home ground desert).

## Open

- comp26 and comp10 carry only with the raised ground their rim steps onto at home: an ensemble carry, like the
  horseshoe's falls mouth.
- The snow massifs (comp9, comp19) need a coarse-rim split (the forest's RIM GRAIN, for the mountain zip) and a
  level foot respectively; the big three (comp2/3/4) need an island past r111 and their own aperture anatomy.

## 5. The kit: THE HOME-GROUND WARNING

`world/data/donors.toml` rows now carry `home_ground` for every massif, and `world-mountain` and `world-fuse`'s
`[[mountain]]` table print a warning when `--ground` differs (`world/donors.home_ground_note`): the carry is
lawful, but the foot meets a ground it never meets in stock, which no gate can see. A warning, not a refusal (the
owner's call). The geometry modules still parse no catalog (the Uaho identity must not acquire a file-parse
dependency). The desert peak enters the catalog as `desert-peak` (`19,3`).
