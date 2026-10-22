# comp9 in game: a snow massif carried with its inlet floor (round 21)

**Status:** in game, 2026-10-22. 58/58 harness checks on the second launch. One visual defect found, by the owner and
by an offline render: a white sliver at the back of the inlet, the carried Object plate's plug painted across a
pure-white atlas gutter. Not fixed yet; the owner's verdict on the look is pending.

The lane follows `../mountaindonors/INLET.md` (offline, 4/6 angles). Round record: `../ingame/RESULTS.md` section 36.

## The site (the offline bench could not be deployed)

- The offline bench (`mountaindonors/sweep.py`) is an r94 one-lobe island at (1380, -100). It was never minted through
  `world-island`, and it cannot be:
  - no 4x4 window of disc 1 is open ocean that no live folder touches (`site_probe.py`'s docstring); the open window
    here is blocks (19-23, 0-2), 5x3;
  - r94 spills into real block (21,3), a sea-only prefab (THE OPEN-OCEAN TARGET LAW);
  - a one-lobe outline over about r80 fails world-island's shape gate: `med_turn` 7.3 < 8, too smooth for a stock coast.
- `site_probe.py`: `world-island --ground snow --center 1408,-96 --radius 88 --lobes 2 --patches 0 --seed 42` mints
  clean on blocks (20,0)-(22,2) (2 WARN rows: 3 zero-UV snow tris, Sea4 uniformity).
- `grid_probe.py`: comp9 with the inlet carves on it at every angle from some near= point on a 4u grid: rot 0 10/36,
  30 33/36, 200 5/36, 270 27/36. Most rot-0 refusals are INLET.md's ny-0.093 stock face (placement MISS).
- The carve span is a full 3x3 of blocks around near=, so a two-lobe island must cover all nine.

## The build (`lab_build.py`)

The CLI's own steps in-process, with `alcove=COMP9_INLET` handed in (the CLI has no flag for it yet). A rot 0 near
(1380, -88); B rot 200 near (1384, -96); C rot 270 near (1380, -96). Every gate green: 403 donor tris + 2 plugs, rock
rigid 0.3%, zip rise 1.13-1.16, apron 6.8-7.0 deg, peak 20.39. Seven Terrain files each; the plugs land in Terrain, so
no Object part and no Donor.txt.

## The prep (`lab_prep.py`)

- The inlet is located by fitting the donor's rock onto the carved rock. Two traps on the way:
  - the carve carries the DE-TILTED positions (`dV2`), not the raw `dV`;
  - the carved rock has more vertices than the donor's (tris split at block borders), so the centroid is a biased
    start, and one start settled in a wrong minimum at rot 0. A 1u grid of starts fixes it.
  - The fit is then exact on all three: plan and height residual 0, one lift of -0.7201.
- Views sit 28u from the nearest rock (the farthest-coast rule put a 130u ridge 60-85u away).

## The run

`20261022-112304-snow-massif`, 58/58 in 386 s. The first launch (`20261022-112149`) never reached the world: the blind
axis probe on bench 6603 measured right 30u / left 59u, at the 0.5 length-ratio edge, on a frame rate that wandered
52.7-70.7 fps. A rerun with no change passed. 6603 is a custom id, so `key_prior` has no stock script to predict from.

| # | prediction | measured | verdict |
|---|---|---|---|
| P1 | every stage reaches the world; the summit reads its peak | 19.7656 / 19.7344 / 19.7656 vs 19.7682 / 19.7329 / 19.7682 | holds |
| P2 | 12 ring points read the built ground | 36/36 | holds |
| P3 | walks keep to the built ground, never on rock | 6/6 walks, 0 samples off a built surface or on rock | holds |
| P4 | homes read their ground height | every view and inlet home | holds |
| P5 | the inlet floor reads the carried snow, and the walk in gets onto it | probe y 2.8320 vs 2.8338 in all three; walks 18.3-18.8u (need 12.5u), min y 2.61 | holds |

Stills settled (at most 0.12% of pixels changed, 60 frames apart).

## The defect: a white sliver at the inlet's back

- **Seen:** the owner ("a triangular shaped seam/sliver near the base") and the inlet panel, at the same place in all
  three variants. The offline `world-render --mod-root` top view reproduces it, so it is in the bytes.
- **Not a hole:** 0 open edges above y 1, 0 down-facing tris (the pre-carve island has none either), and the colour is
  (242,242,247), not the sky's (205,217,247).
- **What it is:** rasterising the pocket against the Moguri atlas names exactly the two plug tris (block (21,1), tris
  571 and 572: the 2-tri Object plate, carried as a plug). Their UVs span v 0.166-0.204. The atlas has a pure-white
  1-texel gutter line at v 0.200-0.202 across u 0-0.26; the collar round the plug stops at v 0.1973. The plug straddles
  the gutter.
- **Why the gates passed it:**
  - `_plug_chart_ok` (INLET.md round 2) accepts a plug inside the donor rock's min-max UV box, and comp9's box spans
    the gutter. The box is looser than any one tile.
  - `_atlas_gate_mountain` flags only texels that are transparent AND dark. A white gutter is opaque and bright.
- **Candidate fixes (not built):** keep a plug's UVs inside the tile its collar occupies (no crossing a gutter row or
  column); and/or let the atlas gate refuse pure-white gutter texels, calibrated against the catalogued carves (Uaho's
  plugs must still pass, and snow is near-white, so the line is 255).

## Scripts

`site_probe.py`, `grid_probe.py`, `lab_build.py`, `lab_prep.py`, `lab_install.py`, `lab_session.py`, `lab_post.py`.
The install and restore are round 20's (ini restored sha efaebbf47c36e752; the lab moved into the run dir).
