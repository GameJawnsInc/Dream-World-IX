"""Completeness-critic independent re-derivation (READ-ONLY).

Two label-blind, mesh-level checks that the contract round's cell-quantized census did NOT do
directly:
  (1) Does any plain topo-17 desert tri share a real MESH EDGE (2 shared verts) with a grass tri,
      anywhere in stock?  (verdict C says "topo-17 plain desert never meets grass" -- test it at
      the triangle level, not the 4u-cell level.)
  (2) Recount grass|desert straddle CELLS map-wide at the tri level (both-families-in-one-cell) to
      confirm the "exactly ONE ecotone site" claim, and report every block that has any.

Nothing is written to the game install; this only reads stock disc-1 bytes and prints/dumps JSON to
out/contract_mass/critic.json.
"""
from __future__ import annotations
import json, sys, time
from collections import defaultdict, Counter
from pathlib import Path

HERE = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/ff9-special-effect-plugin-dll-2fdd97/studies/overworld-topography")
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit")); sys.path.insert(0, str(HERE))
from ff9mapkit.world import extract as X  # noqa
import seam_null_recon as SNR  # noqa  (FAM_OF)

GRASS_TOPOS = {t for t, f in SNR.FAM_OF.items() if f == "grass"}
DESERT_TOPOS = {t for t, f in SNR.FAM_OF.items() if f == "desert"}  # 16,17,19,20
PLAIN17 = {17}
CELL = 32.0

t0 = time.time()

def block_tris(bx, by):
    """Yield (topo, (i0,i1,i2), verts) for terrain tris of a block, or [] if absent."""
    try:
        bm = X.read_block(bx, by, disc=1, part="terrain")
    except Exception:
        return None
    if bm is None:
        return None
    out = []
    for tri in bm.tris:
        topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
        out.append((topo, tuple(tri), bm.verts))
    return out

def vkey(v):
    return (round(float(v[0]), 3), round(float(v[1]), 3), round(float(v[2]), 3))

# ---- scan whole land-block rect (0..23, 0..19) --------------------------------------------------
edge_owner = {}          # within-block edge -> set of families touching it
straddle_cells = set()   # (world cellx, cellz) carrying BOTH grass and desert tris
cell_fam = defaultdict(set)
topo17_grass_edge_hits = []   # (bx,by, edge) where a plain-17 tri and a grass tri share an edge
desert_grass_edge_blocks = Counter()  # any desert-topo meets grass edge, per block
n_blocks = 0
n_tris = 0

for bx in range(24):
    for by in range(20):
        tris = block_tris(bx, by)
        if not tris:
            continue
        n_blocks += 1
        # per-block edge map: edge(vkey pair) -> list of (topo)
        emap = defaultdict(list)
        for topo, tri, verts in tris:
            n_tris += 1
            vk = [vkey(verts[i]) for i in tri]
            # centroid cell for straddle detection
            cx = sum(verts[i][0] for i in tri) / 3.0
            cz = sum(verts[i][2] for i in tri) / 3.0
            cell = (int(cx // CELL), int((-cz) // CELL))
            fam = SNR.FAM_OF.get(topo)
            if fam in ("grass", "desert"):
                cell_fam[cell].add(fam)
            for a in range(3):
                e = tuple(sorted((vk[a], vk[(a + 1) % 3])))
                emap[e].append(topo)
        for e, topos in emap.items():
            fams = {SNR.FAM_OF.get(t) for t in topos}
            if "grass" in fams and "desert" in fams:
                desert_grass_edge_blocks[(bx, by)] += 1
                # is the desert side plain topo-17 (not the 16 ecotone skin)?
                if any(t in PLAIN17 for t in topos) and any(t in GRASS_TOPOS for t in topos):
                    topo17_grass_edge_hits.append((bx, by, list(topos)))

for cell, fams in cell_fam.items():
    if "grass" in fams and "desert" in fams:
        straddle_cells.add(cell)

# group straddle cells into blocks
straddle_by_block = Counter()
for (cx, cz) in straddle_cells:
    straddle_by_block[(cx * 32 // 64, cz * 32 // 64)] += 1

# group topo17-grass hits by block
t17_by_block = Counter()
for (bx, by, _t) in topo17_grass_edge_hits:
    t17_by_block[(bx, by)] += 1

result = dict(
    elapsed_s=round(time.time() - t0, 1),
    n_blocks=n_blocks, n_tris=n_tris,
    n_grass_desert_edges_total=int(sum(desert_grass_edge_blocks.values())),
    grass_desert_edge_blocks={f"{k[0]},{k[1]}": v for k, v in sorted(desert_grass_edge_blocks.items())},
    n_topo17_grass_shared_edges=len(topo17_grass_edge_hits),
    topo17_grass_edge_blocks={f"{k[0]},{k[1]}": v for k, v in sorted(t17_by_block.items())},
    topo17_grass_edge_samples=topo17_grass_edge_hits[:20],
    n_straddle_cells_mapwide=len(straddle_cells),
    straddle_cells_by_block={f"{k[0]},{k[1]}": v for k, v in sorted(straddle_by_block.items())},
)
outdir = HERE / "out" / "contract_mass"
outdir.mkdir(parents=True, exist_ok=True)
(outdir / "critic.json").write_text(json.dumps(result, indent=1))
print(json.dumps({k: v for k, v in result.items() if k not in ("topo17_grass_edge_samples",)}, indent=1))
