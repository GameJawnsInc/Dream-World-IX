"""INDEPENDENT FALSIFIER for Lane A (realized-boundary -> coast floors), CONTRACT MASS round.

READ-ONLY. Does NOT import or read contract_mass_boundary.py (the lane script). Re-derives the
gate-bound numbers from raw bytes + the shared proven detectors (seam_null_recon FAM_OF/classify_tri/
load_tris/edge_index) only. Cross-checks against the SURVIVING falsifier JSON
(out/rung_e/verify_rung_e_independent.json) and the prior contract JSON (out/contract_gd_composition.json).

Two stages:
  STOCK  -- the three convention floors at the map's ONE grass|desert ecotone (13-15,11-12):
            boundary-cell-centre / straddle-cell-centre / topo16-body-tri-centroid  ->  nearest
            sea/beach VERTEX (the 39.95u methodology's own coast reference: CORE Moore ring r1),
            + a radius-2 widen to test "no closer vertex missed".
  RUNG E -- the staged mint (out/rung_e/.../Terrain.ff9mesh, footprint bx0-3 by14-19): the same
            three conventions measured to (a) staged Sea4 VERTICES (the claimed-invalid convention,
            expect ~0.6u) and (b) the realized LAND-PERIMETER coast (terrain boundary edges near
            sea = the valid 'coastal-filtered mesh edge').

LABEL-BLIND: every desert/boundary tri classified BOTH by topo id (FAM_OF) and UV geometry
(classify_tri); disagreements reported.

Run:  py studies/overworld-topography/contract_mass_falsify_a.py
Artifact -> out/contract_mass/falsify_a.json
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/ff9-special-effect-plugin-dll-2fdd97/studies/overworld-topography")
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                       # noqa: E402  proven detectors
from ff9mapkit.world import extract as X             # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402

OUT = HERE / "out" / "contract_mass" / "falsify_a.json"
CELL = 4.0
CORE = [(bx, by) for bx in (13, 14, 15) for by in (11, 12)]
WIDE = sorted({(bx, by) for bx in range(10, 19) for by in range(7, 16) if M.block_in_grid(bx, by)})
SEA_PARTS = ("sea1", "sea2", "sea3", "sea4", "sea5", "beach1", "beach2")

RUNG_E_DIR = HERE / "out" / "rung_e" / "FF9CustomMap-world"


def cell_center(cell):
    return (cell[0] * CELL + CELL / 2.0, cell[1] * CELL + CELL / 2.0)


def read_sea_verts(blocks, disc=1, staged_dir=None):
    """Return list of (wx, wz, block, part) for every sea/beach vertex in `blocks`."""
    pts = []
    for (bx, by) in blocks:
        ox, oz = X.block_world_origin(bx, by)
        for part in SEA_PARTS:
            bm = None
            if staged_dir is not None:
                rel = M.override_relpath(disc, bx, by, part=part.capitalize().replace("Sea", "Sea").replace("Beach", "Beach"))
                # ff9mesh filenames use capitalized part: Sea4, Beach1
                part_file = {"sea1": "Sea1", "sea2": "Sea2", "sea3": "Sea3", "sea4": "Sea4",
                             "sea5": "Sea5", "beach1": "Beach1", "beach2": "Beach2"}[part]
                rel = M.override_relpath(disc, bx, by, part=part_file)
                path = staged_dir / rel
                if path.exists():
                    bm = M.blockmesh_from_ff9mesh(path, disc=disc, x=bx, y=by, part=part)
                else:
                    continue
            else:
                try:
                    bm = X.read_block(bx, by, disc=disc, part=part)
                except (ValueError, FileNotFoundError):
                    continue
            for v in bm.verts:
                pts.append((v[0] + ox, v[2] + oz, (bx, by), part))
    return pts


def min_dist_to_pts(wx, wz, pts):
    best = None
    for (sx, sz, _b, _p) in pts:
        d = math.hypot(wx - sx, wz - sz)
        if best is None or d < best[0]:
            best = (d, (sx, sz), _b, _p)
    return best


def build_boundary_and_straddle(all_tris):
    """boundary cells = own >=1 grass|desert shared edge; straddle cells = own both a grass AND a
    desert tri by centroid; topo16 body tris. Returns (boundary_cells, straddle_cells, body_tris,
    label_blind_report)."""
    edge_owner = SNR.edge_index(all_tris)
    boundary_cells = set()
    n_gd_edges = 0
    for e, owners in edge_owner.items():
        fams = {all_tris[g]["fam"] for g in owners}
        if fams == {"grass", "desert"}:
            n_gd_edges += 1
            for g in owners:
                boundary_cells.add(all_tris[g]["cell"])

    cell_fams = defaultdict(set)
    for t in all_tris:
        if t["fam"]:
            cell_fams[t["cell"]].add(t["fam"])
    straddle_cells = {c for c, fams in cell_fams.items() if "grass" in fams and "desert" in fams}

    body_tris = [t for t in all_tris if t["topo"] == 16]

    # LABEL-BLIND: for topo-16 (desert-family by id), what does UV say?
    lb = Counter()
    topo17 = 0
    for t in all_tris:
        if t["fam"] == "desert":
            if t["topo"] == 17:
                topo17 += 1
            cls, _d = SNR.classify_tri(t["fam"], t["uv"])
            lb[cls] += 1
    return dict(
        boundary_cells=boundary_cells, straddle_cells=straddle_cells, body_tris=body_tris,
        n_gd_edges=n_gd_edges, label_blind=dict(lb), n_desert_topo17=topo17,
    )


def three_floors(bs, sea_pts):
    """Compute the three convention floors against a sea/coast point set."""
    # boundary cell centre -> coast
    bc_best = None
    for c in bs["boundary_cells"]:
        wx, wz = cell_center(c)
        d = min_dist_to_pts(wx, wz, sea_pts)
        if bc_best is None or d[0] < bc_best[0]:
            bc_best = (d[0], c, d[1], d[2], d[3])
    # straddle cell centre -> coast
    st_best = None
    for c in bs["straddle_cells"]:
        wx, wz = cell_center(c)
        d = min_dist_to_pts(wx, wz, sea_pts)
        if st_best is None or d[0] < st_best[0]:
            st_best = (d[0], c, d[1], d[2], d[3])
    # topo16 body tri centroid -> coast
    bt_best = None
    for t in bs["body_tris"]:
        cx = sum(p[0] for p in t["w"]) / 3.0
        cz = sum(p[2] for p in t["w"]) / 3.0
        d = min_dist_to_pts(cx, cz, sea_pts)
        if bt_best is None or d[0] < bt_best[0]:
            bt_best = (d[0], t["cell"], d[1], d[2], d[3])
    return bc_best, st_best, bt_best


def fmt_best(b):
    if b is None:
        return None
    return dict(dist_u=round(b[0], 3), obj_cell=list(b[1]),
                nearest_vertex=[round(b[2][0], 2), round(b[2][1], 2)],
                nearest_block=list(b[3]), nearest_part=b[4])


def terrain_boundary_edges(all_tris):
    """Edges owned by exactly one terrain tri = the mesh's outer perimeter (land shoreline for an
    open-ocean mint). Returns list of (mx, mz) edge midpoints in world coords + the raw endpoints."""
    edge_owner = SNR.edge_index(all_tris)
    segs = []
    for e, owners in edge_owner.items():
        if len(owners) == 1:
            (a, b) = tuple(e)
            segs.append((a, b))
    return segs


def min_dist_to_segs(wx, wz, segs):
    """min distance (2D X/Z) from point to any segment endpoint OR midpoint (cheap proxy) -- but do
    real point-to-segment to be faithful."""
    best = None
    for (a, b) in segs:
        # a,b are (x,y,z) rounded tuples in world coords (from kk)
        ax, az = a[0], a[2]
        bx, bz = b[0], b[2]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        if L2 < 1e-12:
            d = math.hypot(wx - ax, wz - az)
        else:
            tt = max(0.0, min(1.0, ((wx - ax) * dx + (wz - az) * dz) / L2))
            px, pz = ax + tt * dx, az + tt * dz
            d = math.hypot(wx - px, wz - pz)
        if best is None or d < best:
            best = d
    return best


def main():
    t0 = time.time()
    report = {"meta": {}, "stock": {}, "rung_e": {}, "cross_check": {}, "findings": []}

    # ============================================================ STOCK
    print("=== STOCK: loading wide region", len(WIDE), "blocks ===")
    all_tris, bms, _src = SNR.load_tris(WIDE, source="stock")
    print(f"  land blocks present: {len(bms)}, tris {len(all_tris)}")
    bs = build_boundary_and_straddle(all_tris)
    print(f"  boundary cells={len(bs['boundary_cells'])}  straddle cells={len(bs['straddle_cells'])}"
          f"  topo16 body tris={len(bs['body_tris'])}  gd edges={bs['n_gd_edges']}")
    print(f"  label-blind desert UV classes: {bs['label_blind']}  desert-topo17={bs['n_desert_topo17']}")

    # coast reference: CORE Moore ring radius 1 (the 39.95 methodology), then radius 2 widen
    core_ring1 = sorted({(bx + dx, by + dy) for (bx, by) in CORE
                         for dx in (-1, 0, 1) for dy in (-1, 0, 1) if M.block_in_grid(bx + dx, by + dy)})
    core_ring2 = sorted({(bx + dx, by + dy) for (bx, by) in CORE
                         for dx in range(-2, 3) for dy in range(-2, 3) if M.block_in_grid(bx + dx, by + dy)})
    sea_r1 = read_sea_verts(core_ring1)
    sea_r2 = read_sea_verts(core_ring2)
    print(f"  sea/beach verts r1={len(sea_r1)}  r2={len(sea_r2)}")

    bc1, st1, bt1 = three_floors(bs, sea_r1)
    bc2, st2, bt2 = three_floors(bs, sea_r2)
    print(f"  R1 floors: boundary={bc1[0]:.3f}  straddle={st1[0]:.3f}  body={bt1[0]:.3f}")
    print(f"  R2 floors: boundary={bc2[0]:.3f}  straddle={st2[0]:.3f}  body={bt2[0]:.3f}")

    report["stock"] = dict(
        n_land_blocks=len(bms), n_tris=len(all_tris),
        n_boundary_cells=len(bs["boundary_cells"]),
        n_straddle_cells=len(bs["straddle_cells"]),
        n_topo16_body_tris=len(bs["body_tris"]),
        n_gd_edges=bs["n_gd_edges"],
        label_blind_desert_uv=bs["label_blind"], desert_topo17_count=bs["n_desert_topo17"],
        coast_ring1_blocks=[list(b) for b in core_ring1], n_sea_verts_r1=len(sea_r1),
        n_sea_verts_r2=len(sea_r2),
        floor_boundary_cell_r1=fmt_best(bc1), floor_straddle_cell_r1=fmt_best(st1),
        floor_body_tri_r1=fmt_best(bt1),
        floor_boundary_cell_r2=fmt_best(bc2), floor_straddle_cell_r2=fmt_best(st2),
        floor_body_tri_r2=fmt_best(bt2),
    )

    # ============================================================ RUNG E
    print("\n=== RUNG E: staged bytes ===")
    fp_blocks = sorted({(bx, by) for bx in range(0, 4) for by in range(14, 20) if M.block_in_grid(bx, by)})
    rung_tris = []
    bm_by_block = {}
    for (bx, by) in fp_blocks:
        rel = M.override_relpath(1, bx, by, part="Terrain")
        path = RUNG_E_DIR / rel
        if not path.exists():
            continue
        bm = M.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by, part="terrain")
        bm_by_block[(bx, by)] = bm
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            idall0 = int(round(bm.tangents[tri[0]][0]))
            topo = X.decode_id(idall0)["topograph"]
            fam = SNR.FAM_OF.get(topo)
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[2] for p in w) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            rung_tris.append(dict(block=(bx, by), topo=topo, idall=idall0, fam=fam, w=w, uv=uv, cell=cell))
    for i, t in enumerate(rung_tris):
        t["gid"] = i
    print(f"  staged terrain blocks={len(bm_by_block)}, tris={len(rung_tris)}")
    rbs = build_boundary_and_straddle(rung_tris)
    topo_hist = Counter(t["topo"] for t in rung_tris)
    print(f"  boundary cells={len(rbs['boundary_cells'])}  straddle cells={len(rbs['straddle_cells'])}"
          f"  topo16 body={len(rbs['body_tris'])}")
    print(f"  topo hist={dict(sorted(topo_hist.items()))}")

    # (a) sea-vertex convention on staged Sea4 (claimed invalid ~0.6u)
    staged_sea = read_sea_verts(fp_blocks, staged_dir=RUNG_E_DIR)
    sea4_only = [p for p in staged_sea if p[3] == "sea4"]
    print(f"  staged sea verts total={len(staged_sea)}  sea4={len(sea4_only)}")
    rbc_sv, rst_sv, rbt_sv = three_floors(rbs, staged_sea)
    print(f"  RUNG-E sea-vertex-convention floors: boundary={rbc_sv[0]:.3f} straddle={rst_sv[0]:.3f} body={rbt_sv[0]:.3f}")

    # Sea4 footprint diagnostic: is it a full-block plane?
    sea4_diag = {}
    for (bx, by), _ in bm_by_block.items():
        rel = M.override_relpath(1, bx, by, part="Sea4")
        p = RUNG_E_DIR / rel
        if p.exists():
            sbm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="sea4")
            xs = [v[0] for v in sbm.verts]; zs = [v[2] for v in sbm.verts]
            sea4_diag[f"{bx},{by}"] = dict(n_verts=len(sbm.verts),
                                           x_span=round(max(xs) - min(xs), 1) if xs else 0,
                                           z_span=round(max(zs) - min(zs), 1) if zs else 0)
    print(f"  Sea4 per-block footprint: {sea4_diag}")

    # (b) realized land-perimeter coast (terrain boundary edges) -- the valid convention
    segs = terrain_boundary_edges(rung_tris)
    print(f"  terrain perimeter (1-owner) edges={len(segs)}")
    # measure the three conventions to nearest perimeter edge
    rbc_pe = min(( (min_dist_to_segs(*cell_center(c), segs), c) for c in rbs["boundary_cells"] ), key=lambda x: x[0])
    rst_pe = min(( (min_dist_to_segs(*cell_center(c), segs), c) for c in rbs["straddle_cells"] ), key=lambda x: x[0])
    rbt_pe = min(( (min_dist_to_segs(sum(p[0] for p in t["w"]) / 3.0, sum(p[2] for p in t["w"]) / 3.0, segs), t["cell"]) for t in rbs["body_tris"] ), key=lambda x: x[0])
    print(f"  RUNG-E land-perimeter-edge floors: boundary={rbc_pe[0]:.3f} straddle={rst_pe[0]:.3f} body={rbt_pe[0]:.3f}")

    report["rung_e"] = dict(
        footprint_blocks=[list(b) for b in sorted(bm_by_block)], n_tris=len(rung_tris),
        topo_hist=dict(sorted(topo_hist.items())),
        n_boundary_cells=len(rbs["boundary_cells"]), n_straddle_cells=len(rbs["straddle_cells"]),
        n_topo16_body_tris=len(rbs["body_tris"]),
        sea_vertex_convention=dict(
            n_staged_sea_verts=len(staged_sea), n_sea4_verts=len(sea4_only),
            floor_boundary_cell=fmt_best(rbc_sv), floor_straddle_cell=fmt_best(rst_sv),
            floor_body_tri=fmt_best(rbt_sv), sea4_footprint=sea4_diag),
        land_perimeter_edge_convention=dict(
            n_perimeter_edges=len(segs),
            floor_boundary_cell_u=round(rbc_pe[0], 3), boundary_cell=list(rbc_pe[1]),
            floor_straddle_cell_u=round(rst_pe[0], 3), straddle_cell=list(rst_pe[1]),
            floor_body_tri_u=round(rbt_pe[0], 3), body_cell=list(rbt_pe[1])),
    )

    # ============================================================ CROSS-CHECK vs surviving JSON + lane
    surv = json.load(open(HERE / "out" / "rung_e" / "verify_rung_e_independent.json"))
    prior = json.load(open(HERE / "out" / "contract_gd_composition.json"))
    lane = json.load(open(HERE / "out" / "contract_mass" / "lane_a_boundary.json")) if (HERE / "out" / "contract_mass" / "lane_a_boundary.json").exists() else None

    report["cross_check"] = dict(
        surviving_falsifier=dict(
            body_min_raw=surv["body_min_raw"], boundary_min_straddle=surv["boundary_min_straddle"],
            my_rung_e_body_land_perim=round(rbt_pe[0], 3),
            my_rung_e_straddle_land_perim=round(rst_pe[0], 3)),
        prior_contract_39_95=prior["coast"]["precise_boundary_cell_to_sea_vertex"]["dist_u"],
        my_stock_boundary_r1=round(bc1[0], 3),
    )

    report["meta"] = dict(elapsed_s=round(time.time() - t0, 1),
                          note="independent falsifier, read-only, no lane-script import")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}   ({report['meta']['elapsed_s']}s)")


if __name__ == "__main__":
    main()
