# comp9 in game: a snow massif carried with its inlet floor (round 21)

**Status:** in game, 2026-10-22. 58/58 harness checks. The first run found a white sliver at the back of the inlet (the
owner saw it; an offline render reproduced it): the carried Object plate's plug painted across a pure-white atlas
gutter. FIXED (e04d2184, section "The fix" below) and re-run in game: 58/58 on the first launch, the sliver gone. The
owner's verdict on the look is pending.

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
- **The vanilla atlas** has no white line, but it changes paint at the same v 0.200 ((164,172,189) below, (222,230,222)
  above), so on a vanilla install the same plug would show a wrong-paint sliver. The fix therefore cannot key on Moguri.

## The fix (e04d2184, owner's go)

- **THE COLLAR-TILE CLAMP** (`carve_mountain`'s plug chart). A plug UV axis that leaves its collar group's UV box by
  MORE than the chart's own p90 fit residual on that axis is clamped into the box.
  - A plain clamp into the box was tried first and REFUSED by the identity check: Uaho's plug also overshoots its
    collar box (u 3.5 px, v 8 px) and its catalogued bytes moved. Uaho's overshoot sits inside its fit's noise
    (residual 15 / 10 px), so it is not an extrapolation and is kept. comp9's v overshoot is 27 px against a 9 px
    residual: clamped.
  - Two other lines were measured and rejected: no fixed tolerance works (the gutter is 0.002 above comp9's collar,
    the size of Uaho's harmless overshoot), and "inside the donor's own rock UV coverage" fails both donors (a plug sits
    in an Object hole in UV space too).
  - The plug log line names the raw plug UV range against the collar box.
- **THE GUTTER RULE** (`_atlas_gate_mountain`): a new tri may not sample a texel with every RGB >= 250
  (`ATLAS_GUTTER_WHITE`). `gutter_census.py` calibrates it: 0 of disc 1's ~84k stock Terrain tris sample one at the
  gate's sampler (the Object-part hits it prints are another atlas and do not count); the old lab plug samples 2 and 5.
- **Checks:** the 44 catalogued carve files byte-identical (uaho, crag, horseshoe, comp20, desert-peak); two new tests
  (a fake-atlas gate test with its break-it; an install-gated comp9 carve showing the raw overshoot and the clamp), both
  failing on the old `interior.py`; interior + donors + compose 126 passed; discmirror_auto, disc_split, mint_outline,
  placement_order, river, seam_wrap 190 passed. The rebuilt lab differs from the first only in 2 UV rows of block
  (21,1) (max 0.0066), and the offline top render shows no sliver.

## The rerun (`20261022-115102-snow-massif-fix`)

58/58 on the first launch, in 389 s. Every reading matches the first run (summits 19.7656 / 19.7344 / 19.7656, 36/36
ring, 6/6 walks, inlet floor 2.8320, walks in 18.35 / 18.72 / 18.79u). The near-white pixels in the upper half of each
inlet still, 86 / 90 / 88 before, are 0 / 0 / 0.

## Scripts

`site_probe.py`, `grid_probe.py`, `gutter_census.py`, `lab_build.py`, `lab_prep.py`, `lab_install.py`, `lab_session.py`, `lab_post.py`.
The install and restore are round 20's (ini restored sha efaebbf47c36e752; the lab moved into the run dir).
