# Sea holes at a cove's inner corner: the "conservative" Sea4 cut is not conservative on a concave coast

**Status:** registered 2026-10-23, before the fix. Owner's go: "diagnose and fix the world-island sea holes at cove
corners, reading the coast laws first."

## The report and the measurement

Round 23 (`NOTES.md`): sky-coloured wedges in the sea at a cove's inner corner, below the coast wall. `hole_scan.py`
finds the plan uncovered by every one of the island's own parts there: round 23's grass island (r66 one-lobe at
(1380, -96)) a thin diagonal of 8 grid points in block (20,2) plus 1 in (21,0); round 22's desert island (r55 at
(1380, -100)) 3 points in (21,2); round 21's two-lobe snow island none. All are `world-island` mints, holed before any
carve.

## The mechanism (read from the bytes, block (20,2) of round 23's island)

The tile x 1340-1344, z -128 to -132 is split on its diagonal (1340,-128)-(1344,-132). Sea4 keeps only its south-west
half. The wall's foot (topo 58 at y 0) runs (1340.67, -129.89) -> (1344, -130.66), north of the diagonal for most of
its length, then turns south along x = 1344 (the cove's inner corner). The wedge between the foot and the diagonal is
neither land nor sea: at x 1342.62 the foot is at z -130.34, the diagonal at -130.62, the hole at -130.38.

**Why the cut dropped that half-tile.** `island._cut_plane` drops a Sea4 tri when ALL THREE CORNERS lie under land
(THE SEA4-UNDER-LAND LAW, "the cut must be CONSERVATIVE -- all three corners under land, not the centroid"). The half
tile's corners (1340,-128), (1344,-128), (1344,-132) are all under land -- the last sits on the wall-foot edge where
the wall turns south -- but its interior spans the cove's water between the two walls. "Every corner inside" implies
"inside" only for CONVEX land; at a concave corner it is not conservative, and the dropped tri tears exactly the hole
the law's own text warns of ("tears a query/render hole just outside the land").

## The fix (registered)

`_cut_plane` drops a Sea4 tri only when its WHOLE AREA lies under land: the tri minus every overlapping land tri
(exact convex clipping, pure Python -- the base install has no geometry library) leaves less than `SEA_CUT_EPS_AREA`
(0.001 u2). Where land is convex the result is unchanged (a covered tri has nothing left), so a convex coast cuts the
same tris. At a concave corner the half-tile reaching into the cove stays, as a waterline fringe the law already
accepts ("a one-triangle fringe at the waterline survives the conservative cut").

| # | prediction | falsified if |
|---|---|---|
| H1 | `hole_scan.py` on the three lab islands, re-minted with the fix: 0 uncovered points (round 23's 9, round 22's 3, round 21's 0) | any point remains |
| H2 | **the census:** over a sweep of `world-island` mints (grass and desert, radii 40-90, 1-2 lobes, several seeds), uncovered points fall to 0 in every mint that had any, and no mint that had none gains any | any mint keeps or gains holes |
| H3 | the kept-sea growth is the fringe only: every Sea4 tri the fix newly keeps touches the land's boundary (has a part outside land), and no Sea4 tri lies wholly under land after the fix | a newly kept tri is wholly covered, or a wholly covered tri survives |
| H4 | Terrain bytes never change: the identity nets (Uaho's mint pins, island E) stay byte-exact; only Sea4 files differ, and only in blocks with a concave coast | an identity pin moves, or a Terrain file changes |
| H5 | break-it, as a test: a concave (L-shaped) land cover with a tri whose three corners are inside and whose middle is not -- the old rule drops it, the new keeps it; a tri wholly under convex land is dropped by both | either fails |

**Known risk, no call made:** the kept fringe lies partly under the wall, so a boat may nose a little further into a
cove's corner before the wall stops it (the fringe the law accepts). The coast-nav stamp re-classes waterline tris for
vehicles; the harness boat drive is the in-game check, not this offline round.

## Result (offline, 2026-10-23)

| # | measured | verdict |
|---|---|---|
| H1 | the three lab islands re-minted: 0 / 0 / 0 uncovered points (were 9 / 3 / 0) -- `hole_fringe_check.py` | **holds** |
| H2 | `hole_census.py`, 20 lawful mints of 32 configs (grass and desert, r40/55/66 at (1380,-96) and r84 at (1408,-96), 1-2 lobes, seeds 42/7): **8 had holes before** (8, 8, 3, 18 points each on grass, the same on desert), **0 after**; none gained any | **holds** |
| H3 | on round 23's island the fix newly keeps 3 Sea4 tris, all 3 reaching past the land on an independent 231-point sample grid; 0 kept tris wholly under land | **holds** |
| H4 | only Sea4 files change: 14 of them, all in mints with a concave corner (one r84 mint changed with 0 -> 0 scanned holes: a sliver under the scan's 0.25u grid). No Terrain file changes; the identity nets pass | **holds** |
| H5 | `test_cut_keeps_a_tri_whose_corners_are_under_land_but_whose_middle_is_not`: an L-shaped land keeps the cove tri, the old rule (patched back in) tears the hole, a tri wholly under land is still cut | **holds** |

**A second finding on the way: the census's sea MODEL must keep the corner rule.** The first world-domain run went red
on two `census_gate` tests (`..._detects_holes_even_without_baseline`, `..._stack_passes_the_islands_own_misses...`).
`interior.census_gate` re-cuts the sea plane to model what lies under the land, and its job is to make a hole the
carve punched read MISS: under the area rule a hole enclosed by land keeps its sea and the hole hides. So `_cut_plane`
takes `rule=` -- `"area"` for every deployed Sea4 (the mint and its beach path), `"corners"` for the census model. The
census paths that read the DEPLOYED Sea4 (`stack=`, the mountain and forest CLIs) need neither: they read the bytes.
Rerun after the split: the mint bytes are identical to the first fix (`hole_census_after2.json` == `after.json`).

**What follows:** an in-game look at a re-minted island's cove corner (stills + `hole_scan`), when the harness is free.
Every kit island deployed before this fix keeps its holes until it is re-minted; `hole_scan.py <mod folder>` finds them.

## In game (2026-10-23, `20261023-101037-sea-holes-fix`)

Round 23's comp10 lab rebuilt with the fixed mint (its prep byte-identical to round 23's: the land did not move; 0
uncovered points in all four variants), then the same session in stills-only mode (`MTN_STILLS=1`): 53/53, the ini
restored byte-exact. Same cameras, same cove corners: sky-coloured pixels in the lower 58% of the 20 stills went from
**1557 to 6** (B-west 501 -> 0, C-south 444 -> 0, D-south 260 -> 0, B-south 237 -> 0, A-north 55 -> 2, B-north 53 -> 0;
the 6 left are single pixels, 1-2 a frame, none a wedge). The zoom on C-south's corner shows water meeting the wall
where the sky wedge was. The boat drive near a fixed cove (the registered risk) was not run.
