"""Independent probe: are the 17 cropped-Wang seams on the NEIGHBOR cells (out of scope) or on (11,19)?
Reuses the study module's own coherence predicate on the DEPLOYED bytes. No writes."""
import sys
from pathlib import Path
STUDY = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/overworld-work-continue-0d139c/studies/overworld-topography")
sys.path.insert(0, str(STUDY))
import importlib.util
spec = importlib.util.spec_from_file_location("wf", STUDY / "waterfix_1119_r2.py")
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)

G = wf.G

def cell_frame_incoherence(rdir, x, y, edges):
    """Count outer-frame (facing generic deep) incoherent edge cells for a neighbour cell."""
    parts = wf._load_deployed_parts(rdir, x, y)
    grid = wf.parts_shade_grid(parts)
    s5 = wf.parts_sea5_tiles(parts.get("sea5"))
    total_bad = 0
    detail = []
    for e in edges:
        res = wf.frame_edge_verdicts(grid, s5, e)
        bad = [r for r in res if not r[2]]
        total_bad += len(bad)
        detail.append((e, len(bad), [(ij, sh, det) for ij, sh, _ok, det in bad]))
    return total_bad, detail

# The 2x2 carried island: (11,18)=(11,r18) (12,18)=(12,r18) top row; (11,19) (12,19) bottom row.
# Outer edges facing generic-deep ocean:
#   (11,18): N (top) + W (left)   -- top-left corner of island
#   (12,18): N (top) + E (right)  -- top-right corner
#   (11,19): W (left) + S (bottom) -- bottom-left  [THE REDEPLOYED CELL]
#   (12,19): E (right) + S (bottom) -- bottom-right
SPECS = [
    (wf._rdir(1, 18), 11, 18, ("N", "W"), "(11,18) neighbour"),
    (wf._rdir(1, 18), 12, 18, ("N", "E"), "(12,18) neighbour"),
    (wf._rdir(1, 19), 12, 19, ("E", "S"), "(12,19) neighbour"),
]
grand = 0
for rdir, x, y, edges, label in SPECS:
    n, det = cell_frame_incoherence(rdir, x, y, edges)
    grand += n
    print(f"{label}: {n} incoherent outer-frame edge cells  (edges {edges})")
    for e, cnt, cells in det:
        if cnt:
            print(f"    .{e}: {cnt}  e.g. {cells[:3]}")
print(f"\nNEIGHBOUR total (out-of-scope cells): {grand} incoherent outer-frame edge cells")

# And re-confirm (11,19) itself is CLEAN on ITS outer frame edges (W,S):
n19, det19 = cell_frame_incoherence(wf._rdir(1, 19), 11, 19, ("W", "S"))
print(f"(11,19) [THE REDEPLOYED CELL] outer-frame W+S: {n19} incoherent  <- must be 0")
