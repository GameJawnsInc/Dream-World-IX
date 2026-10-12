# The map erase: land a folder removed comes off the painted world map

Status: **built, offline-proven** (2026-10-12). In game: pending (one relaunch, the map opened on the two charts).
Kit: `ff9mapkit/world/maperase.py`, wired into `world-minimap` (`navimap.render_world_maps`).
Tests: `ff9mapkit/tests/test_world_maperase.py` (hermetic: a synthetic chart painted off its geometry).

## 1. The gap

`world-sink` (land2sea, rounds 10-13) turns a real island into open water, but the in-game map still drew it.
`world-minimap` could only ADD land: it painted a folder's deployed Terrain triangles flat over the chart. Painting
can't take land away, and on a real cell edited in place it also repainted the cell's own stock land flat over the
painted art.

## 2. What the chart is (measured)

- **Two full-screen charts.** `world_map_full_all.png` (disc 2+, or disc 1 from scenario 5990) and
  `world_map_full_mistcontinent.png` (disc 1 below 5990). The Mist chart is **not a crop** of the other: it's a
  separately painted close-up of the Mist continent. Both are 1273x1080 (Moguri HD) and share the same drawn frame line
  (inner edge at x 52, y 42). The Mist chart also has a corner emblem (bottom left, x 0-240, y 880-1080).
- **Hand-painted, and it drifts.** Shapes differ from the geometry (the lagoon island at (553, -1127) is painted
  longer), and the painted world drifts off the registered all-world frame (`WORLD_MAP_ART_FRAME`) **linearly**: the
  census's 46 local offsets fit a plane to ~1.3px rms, `dx = -0.87 - 0.0089x + 0.0002y`, `dy = 19.22 - 0.0014x -
  0.0401y` (px, 1273x1080). The painted world is ~4% short down and ~0.9% narrow across. The frame (an FFT
  translation fit, 2026-07-12) is right through the middle and up to ~24px off at the top and bottom edges: the far
  south is painted ~19px north of the geometry, the north ~10px south of it. Kit: `navimap.WORLD_MAP_DRIFT`.
- **Three looks.** Open sea is a stained, grainy parchment (std ~8 per channel; colour distance to a local
  parchment fit: p99 17, p99.9 25). Each coast wears a soft green **halo**: green over red +12..+40 against the
  parchment at nearly the same brightness. It covers about half the geometry's shallow water (sea1/2/3/5); the rest
  of the shallows is plain parchment. Islands also have a drop shadow to the south-east, a dark rim, and a pale beach
  stripe. Land is anything else, mostly far brighter or darker than the parchment.
- **The Mist frame** (`register_mist.py`): stock land rescaled and correlated against the Mist chart's land pixels
  over an x and y scale sweep: **1.300 px/u across, 1.3075 down, world (0, 0) at (-778, -586)**, Dice 0.909
  (0.934 with `register_mist.py`'s cleaner land mask, which lands on the same offset and sy 1.308), optimum interior
  to both sweeps. The chart shows world x ~598..1578, z ~-448..-1274. (A uniform-aspect sweep alone
  peaks at 1.29, Dice 0.899.)

## 3. The erase (what `maperase` does)

Geometry seeds it; the art decides it.

1. **Removed** = pixels whose class (deep 0 / shallow 1 / land 2) falls from stock to the folder's overrides over
   stock, on real cells the folder edits (`Donor.txt` cells add land; they are not edits). Hidden and zero-area stubs
   are not geometry. Removals under 12 px are coast tweaks. Removals outside the frame (a close-up chart's margin)
   are not drawn.
2. **Features**: a pixel off the local parchment fit by >15 (3x3-smoothed) or >30 (raw: a 1px rim or shadow line);
   isolated 1-2px specks dropped. **Halo** = a feature greener than the parchment (dG-dR > 10) at nearly its brightness
   (|dL| < 22), classified per pixel (a 3x3 smoothing smeared a pale beach stripe next to halo into halo), and at
   least 3px across (a thinner ring is a rim blending into halo).
3. **Alignment**: round each removal (48px context), the stock geometry (dilated 1px: a drawn feature reads 1px wide
   of its edge, which otherwise left a flat ±1px plateau of equal scores) slides up to 20px round the chart's
   predicted drift (all-world chart; the Mist chart needs none) to the best IoU with the features. An overlap under 0.35, or a best at the edge of the reach, means the chart does not draw this land:
   skipped and reported.
4. **What goes**: land-coloured pieces whose nearest land is removed land, grown through the island's adjacent
   pieces (the stripe drawn apart from its island); halo-coloured pixels on removed land (light grass reads as halo);
   a 1px anti-aliased fringe; halo whose nearest geometry is shallow water that became deep.
5. **The repaint**: parchment where the new water is deep; else the class of the kept chart beside it (halo or
   parchment), so no halo edge is invented. Colour = the local field of that class (halo fitted to the halo drawn
   nearby) plus the parchment's own grain, copied from clean parchment half a window away.

The paint pass (unchanged otherwise) now draws only land the folder ADDS on a real cell, and skips hidden stubs.

## 4. Results

**The lab** (`before_after.py FF9CustomMap-wmlab`; six islands sunk with `world-sink` into a folder not in
FolderNames, so the game never loads it; the base chart is the live `FF9CustomMap-world` composite):

| island | chart offset found (drift predicts), px | overlap before -> after | repainted | as halo |
|---|---|---|---|---|
| (679, -387), 4,813 u2, deep water | (-6, 4) ((-6, 4)) | 0.747 -> 0.931 | 3,336 | 0 |
| (553, -1127), the lagoon island | (-5, -19) ((-5, -19)) | 0.38 -> 0.782 | 1,603 | 1,476 |
| (425, -1020), Daguerreo, by footprint | (-4, -15) ((-4, -15)) | 0.627 -> 0.868 | 5,684 | 2,872 |
| (1325, -227), by footprint | (-10, 8) ((-10, 9)) | 0.647 -> 0.883 | 875 | 470 |
| (1446, -862), small | (-10, -11) ((-11, -11)) | 0.749 -> 0.906 | 142 | 0 |
| (10, -22), the corner island | best 0.12 | — | skipped: under the frame, not drawn | |
| Mist chart: (1446, -862) | (2, 0) (no drift) | 0.754 -> 0.769 | 405 | 0 (37 halo to sea) |

Every crop: the island and its shadow are gone. The deep-water island reads as open parchment. The lagoon island,
Daguerreo and the NE island read as halo continuing the band round them. Kept neighbours are byte-identical.

**The live folder** (`FF9CustomMap-world`, 82 donor cells, no real cell edited): the new render equals the deployed
map but for one pixel. That was the divert-arm stub of block (11, 19), whose zero-area triangle had painted a land dot
in open sea.

## 5. Census

`census.py`: every stock island (a land component of 15-7000 px inside the frame) removed alone in the raster, the
erase run on a fresh copy of the stock chart, one row and one before/after crop each (`out/`, gitignored: it is the
game's art).

| chart | islands | erased | skipped | to halo | overlap found (min / median; unshifted median) | offset off the expected (rms, max) |
|---|---|---|---|---|---|---|
| all-world | 47 (27-5,156 px) | 46 | 1: the corner island, under the frame | 30 | 0.771 / 0.865; 0.704 | dx 1.23 / 4, dy 1.37 / 4 px |
| Mist | 16 (88-899 px) | 16 | 0 | 11 | 0.769 / 0.849; 0.835 | dx 1.60 / 3, dy 3.20 / 7 px (no drift) |

Read off the crops: each island, its rim, shadow and beach stripe go; in a halo band the spot reads as the band; its
neighbours stay. The first run (`--no-drift`, reach 20 round no shift) erased the same 46. It found every
southern-band island at an offset of -16 to -19 px down, at the edge of its reach, and the trend fitted the drift
plane (section 2). A far-south island past the reach would have been skipped, so the drift is now the search's
centre. On the Mist chart, light rims blended into the halo first left faint arcs where an islet stood. They are
the TRACE rule now: a halo-coloured pixel within 3px of what goes and over 20 off the local halo (the halo's own
mottle: p90 11.6, p99 22.7). About 4 s a site (most of it the chart's colour fields).

## 6. Not done

- **In game**: one relaunch with the lab folder (or a real sink) stacked above `FF9CustomMap-world`, then the map
  opened on a disc-1 save past scenario 5990 (all-world) and one below it (Mist).
- New land is still drawn flat (islet fill + rim), with no halo or shadow, and only on the all-world chart.
- A synthetic namespace (Path D, `--target-disc 9`) is never erased.
