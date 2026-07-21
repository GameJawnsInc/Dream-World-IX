"""wang_seam_census.py -- THE DECISIVE CENSUS behind the wang-carry gate's report-only default.

Question (2026-07-20, round: the wang-carry-default review): does shipping FF9 ever put a sea3 (light
shallow) tile DIRECTLY against a sea4 (deep) tile across a block border with NO sea5 transition ring --
i.e. is the wang-carry gate's "sea3 abuts deep = incoherent" predicate a REAL shipping invariant, or does
it over-flag legitimate coast?

Answer (run below): ZERO.  Across every block border in the stock world map, a sea3 tile's cross-border
neighbour is NEVER sea4.  Every shallow->deep transition is sea5-mediated (~194) or stays shallow->shallow
(~1461).  So:
  * the gate's predicate is SOUND -- a flagged sea3-abuts-deep frame edge is a genuine seam;
  * a carried coastal ISLAND standalone crops the neighbour blocks that hosted its sea5 transition rings,
    so it legitimately PRODUCES such seams (e.g. donor (7,17) alone shows 16 flagged frame edges) -- fixed
    by a post-carry RE-TILE (wang_rim_retile.py), a human-reviewed step;
  * a DONOR-BASELINE subtraction does NOT enable a safe hard-fail-by-default: with zero pre-existing
    sea3-abuts-deep edges anywhere, there is nothing to subtract -- every flagged sea3 frame edge is
    crop-introduced, so the subtraction reduces to the raw count and would refuse every coastal carry.
    (Empirically confirmed: the donor-outward-deep baseline calls 15/16 of the proven (7,17) carry's
    frame edges "introduced".)  Hence the gate WARNS by default and refuses only on --enforce-wang-carry.

Run:  py studies/overworld-topography/wang_seam_census.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit.world import transplant as TR                    # noqa: E402
from ff9mapkit.world.terrain import GRID_X, GRID_Y              # noqa: E402

G, CELL = 16, 4.0
_STEP = {"E": (1, 0), "W": (-1, 0), "N": (0, -1), "S": (0, 1)}


def shade_grid(bx, by):
    """(16x16 shade grid 'sea3'/'sea4'/'sea5'/'none', has_any_water) for a stock block."""
    g = [["none"] * G for _ in range(G)]
    any_w = False
    for part in ("sea3", "sea4", "sea5"):
        for tri in TR.world_tris(bx, by, part, disc=1, lod="0_1", game=None):
            any_w = True
            i = int((sum(v[0][0] for v in tri) / 3 - 64.0 * bx) // CELL)
            j = int((-(sum(v[0][2] for v in tri) / 3) - 64.0 * by) // CELL)
            if 0 <= i < G and 0 <= j < G:
                g[i][j] = part
    return g, any_w


def census(cells=None):
    """Cross-block-border tile pairs where a sea3 tile faces a real neighbour.  ``cells`` limits the
    scan (a coastal subset for a fast regression test); None = the whole map."""
    scan = cells if cells is not None else [(bx, by) for bx in range(GRID_X) for by in range(GRID_Y)]
    S = {c: shade_grid(*c) for c in scan}
    seam = mediated = shallow = 0
    for (bx, by), (g, any_w) in S.items():
        if not any_w:
            continue
        for i in range(G):
            for j in range(G):
                if g[i][j] != "sea3":
                    continue
                for d, (di, dj) in _STEP.items():
                    if not (i + di < 0 or i + di > 15 or j + dj < 0 or j + dj > 15):
                        continue                                # only cross-BLOCK-border edges
                    ni, nj, nbx, nby = i + di, j + dj, bx, by
                    if ni < 0: nbx, ni = bx - 1, 15
                    elif ni > 15: nbx, ni = bx + 1, 0
                    if nj < 0: nby, nj = by - 1, 15
                    elif nj > 15: nby, nj = by + 1, 0
                    ng = S.get((nbx, nby))
                    if ng is None:
                        ng = shade_grid(nbx, nby) if 0 <= nbx < GRID_X and 0 <= nby < GRID_Y else None
                        if ng is not None:
                            S[(nbx, nby)] = ng
                    if ng is None:
                        continue                                # off-map neighbour (open-ocean ring)
                    ns = ng[0][ni][nj]
                    if ns == "sea4":
                        seam += 1
                    elif ns == "sea5":
                        mediated += 1
                    elif ns == "sea3":
                        shallow += 1
    return {"sea3_abuts_sea4": seam, "sea3_via_sea5": mediated, "sea3_meets_sea3": shallow}


if __name__ == "__main__":
    r = census()
    print("STOCK WORLD MAP -- cross-block-border edges from a sea3 (shallow) tile:")
    print(f"  sea3 -> neighbour sea4 (HARD shallow|deep seam): {r['sea3_abuts_sea4']}")
    print(f"  sea3 -> neighbour sea5 (mediated transition):     {r['sea3_via_sea5']}")
    print(f"  sea3 -> neighbour sea3 (shallow|shallow):          {r['sea3_meets_sea3']}")
    assert r["sea3_abuts_sea4"] == 0, "INVARIANT BROKEN: shipping FF9 has a sea3-abuts-deep border!"
    print("\nINVARIANT HOLDS: shipping FF9 never abuts sea3 to sea4 -- the wang-carry predicate is sound.")
