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
