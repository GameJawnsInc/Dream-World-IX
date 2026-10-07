"""BUILD the four refinement arms for in-game experiment rank 10 (THE IN-GAME COST BUDGET; capacity CAP-10/CAP-12).

One walkable cell, four Terrain overrides that differ ONLY in triangle count:

  cell      Disc1 (21,1) -- an isolated IsSea cell (all 8 neighbours sea, no live file on it or them). Its Terrain
            file arms the s34 sea divert onto Block[12][10] (WMWorld.cs:516-544, WorldMeshOverride.HasLandOverride),
            whose walk list is [Terrain, Sea1, Sea3, Sea4, Sea5] -- NO Object, so our Terrain is the FIRST walk mesh
            every scan iterates (WMBlock.cs:185-200). Session 7 proved this cell renders and walks up to 65,535 verts.
  base      a 13 x 13 quad grid over the whole 64u cell, pitch 64/13 = 4.923u, 338 tris (the stock Terrain median is
            314 tris, median 3D edge 4.38u: capacity CAP-6/CAP-7). Row-major emit (z rows outer, x inner).
  arms      in-place MIDPOINT subdivision r = 0/1/2/3 times: x1 338 / x4 1,352 / x16 5,408 / x64 21,632 tris
            (64,896 verts -- inside the 65,535 loader bound and the kit validator; written by the KIT's own
            ff9mesh_bytes, no hand packing). Children are emitted in place of their parent [A,ab,ca],[ab,B,bc],
            [ca,bc,C],[ab,bc,ca], so a point's scan depth FRACTION is the same in every arm (the same model as
            capacity/walk_cost_sim.py). Midpoint subdivision of a planar tri is EXACT: same surface, same texture
            mapping, only the count differs.
  height    a flat plane, one numeric ARM TAG per arm: x1 6.000 / x4 6.125 / x16 6.250 / x64 6.375 (1/8u apart, on the
            1/256 grid). The published state.world_y on the plane names the arm the engine actually loaded -- the
            per-load proof that the swap bound (session 1b read world_y to +-0.0035).
  IDALL     encode_id(area=14, topograph=0) = 3584 on every corner (tangent [3584, 0, 0, 0], stock tangent y/z/w = 0).
            Area 14 = the R4b safe road: zone 6, camera place 0 (as the surrounding area-0 sea), no area-12 lock, no
            spawn weather, no beach arm; (zone 6, topo 0) has NO encounter record at fog 0 or 1 in the LIVE table, so
            under s60 a roll there finds a hole (gap_area_layer GA1/C, ff9.cs:9237/9264). CHECKED below, not assumed.
  UV        the stock grass MAINS language (world/grassland.py): each base quad maps one full grass quadrant, linear
            in position, quadrant checkerboard (i%2, j%2), ori 0 -- every corner inside the main grass rect (no white
            gutter). Children interpolate, so all four arms texture identically. Normals (0,1,0).

Self-checks (exit non-zero on any failure): unindexed contract and bounds; every tri geometrically UP; the engine
SKY query (gap_area_layer/arealib.raster, calibrated against world/placement.place) over an off-lattice 1u grid
reads the arm tag at EVERY sample, zero misses; plan area exactly 4096 u^2; IDALL decodes to area 14 / topo 0 /
event 0 and is none of the 10 special full values; area 14 is an encounter hole at fog 0 and 1 in the live table;
the bind oracle (consumption/bind_oracle.py, 254/254 disc-1 receipts) predicts the lab file binds as the cell's
FIRST walk mesh; no live mod folder carries a file for (21,1).

Writes to $COST_SCRATCH (default: this session's scratchpad \\cost) -- NEVER the repo, never a mod folder:
    arms/cost_x{1,4,16,64}.ff9mesh   arms/cost_manifest.json
Rerun:  py studies/terrain-malleability/ingame/cost_build.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
sys.path.insert(0, str(HERE.parent / "gap_area_layer"))
from ff9mapkit.world import mesh as M                              # noqa: E402
from ff9mapkit.world.extract import encode_id, decode_id           # noqa: E402
from ff9mapkit.world import grassland as GL                        # noqa: E402

SCRATCH = Path(os.environ.get("COST_SCRATCH", r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                                              r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\cost"))
ARMS_DIR = SCRATCH / "arms"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")

DISC, BX, BY = 1, 21, 1
G = 13                                   # base quads per side
PITCH = 64.0 / G
REFINE = {1: 0, 4: 1, 16: 2, 64: 3}      # arm -> midpoint subdivision passes
TAG = {1: 6.0, 4: 6.125, 16: 6.25, 64: 6.375}
AREA, TOPO = 14, 0
IDALL = encode_id(event=0, area=AREA, topograph=TOPO, flags=0)
SPECIAL_FULL = {4078, 4088, 2040, 0x31EE, 0x18EE, 0x7EE, 0x1BEE, 0x2CEE, 56, 57}   # README §2 consumer table
REL = M.override_relpath(DISC, BX, BY)   # FF9_Data/WorldMap/Disc1/0_1/r1/Block[21][1] Terrain.ff9mesh


def base_tris(h: float) -> list:
    """338 tris [(pos, uv)] x3, row-major, each quad one full grass quadrant (checkerboard), up-wound."""
    tris = []
    for j in range(G):
        for i in range(G):
            x0, x1 = i * PITCH, (i + 1) * PITCH
            z0, z1 = -j * PITCH, -(j + 1) * PITCH
            uh, vh = i % 2, j % 2
            u0, u1 = GL.GRASS_U_HALF[uh]
            v0, v1 = GL.GRASS_V_HALF[vh]

            def corner(x, z):
                a = (x - x0) / PITCH
                b = (z0 - z) / PITCH
                return ((x, h, z), (u0 + a * (u1 - u0), v0 + b * (v1 - v0)))
            A, B, C, D = corner(x0, z0), corner(x1, z0), corner(x1, z1), corner(x0, z1)
            tris.append([A, B, C])           # cross(B-A, C-A).y = +PITCH^2 : up
            tris.append([A, C, D])           # cross(C-A, D-A).y = +PITCH^2 : up
    return tris


def _mid(p, q):
    (pa, ua), (pb, ub) = p, q
    return (((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2, (pa[2] + pb[2]) / 2), ((ua[0] + ub[0]) / 2, (ua[1] + ub[1]) / 2))


def subdivide(tris: list) -> list:
    """Each tri -> 4 by edge midpoints, children IN PLACE of the parent (scan-depth fraction preserved)."""
    out = []
    for A, B, C in tris:
        ab, bc, ca = _mid(A, B), _mid(B, C), _mid(C, A)
        out += [[A, ab, ca], [ab, B, bc], [ca, bc, C], [ab, bc, ca]]
    return out


def build_arm(arm: int):
    tris = base_tris(TAG[arm])
    for _ in range(REFINE[arm]):
        tris = subdivide(tris)
    bm = M.tri_soup_block_mesh(tris, name=f"Block[{BX}][{BY}] Terrain", disc=DISC, x=BX, y=BY)
    for t in bm.tangents:
        t[0], t[1], t[2], t[3] = float(IDALL), 0.0, 0.0, 0.0
    return bm, len(tris)


# ---------------------------------------------------------------------------------------------------- checks
def check_arm(arm: int, path: Path, ntris: int) -> dict:
    import numpy as np
    import arealib as A
    V, ids = A.read_ff9mesh_arrays(path)
    out = {"tris": int(V.shape[0])}
    assert V.shape[0] == ntris, f"x{arm}: read back {V.shape[0]} tris, built {ntris}"
    assert np.all(ids == IDALL), f"x{arm}: an IDALL other than {IDALL}"
    a, b, c = V[:, 0], V[:, 1], V[:, 2]
    u, v = b - a, c - a
    cy = u[:, 2] * v[:, 0] - u[:, 0] * v[:, 2]
    L = np.linalg.norm(np.cross(u, v), axis=1)
    assert np.all(cy / L > 0.999), f"x{arm}: a tri is not up-facing (the walk filter is ny > 0.1, WMPhysics.cs:22-23)"
    plan = 0.5 * np.abs(cy)
    out["plan_area"] = float(plan.sum())
    assert abs(out["plan_area"] - 4096.0) < 1e-3, f"x{arm}: plan area {out['plan_area']} != 4096 (gap/overlap)"
    out["edge_xz"] = float(np.median(np.linalg.norm((b - a)[:, [0, 2]], axis=1)))
    idv, pi, y = A.raster([("Terrain", V, ids)], pitch=1.0)
    miss = int((idv < 0).sum())
    out["raster_samples"], out["raster_miss"] = int(idv.size), miss
    out["raster_y_err"] = float(np.max(np.abs(y[idv >= 0] - TAG[arm]))) if miss < idv.size else None
    assert miss == 0, f"x{arm}: the sky query missed {miss} samples (a hole is a wall)"
    assert out["raster_y_err"] < 1e-4, f"x{arm}: ground != arm tag by {out['raster_y_err']}"
    return out


def check_uv(bm) -> None:
    lo_u, lo_v, hi_u, hi_v = GL.FAM_REGION["main"]
    for uu, vv in bm.uvs:
        assert lo_u - 1e-6 <= uu <= hi_u + 1e-6 and lo_v - 1e-6 <= vv <= hi_v + 1e-6, f"UV {uu},{vv} outside grass"


def check_area() -> dict:
    import arealib as A
    d = decode_id(IDALL)
    assert d == {"event": 0, "area": AREA, "topograph": TOPO, "flags": 0}, d
    assert IDALL not in SPECIAL_FULL, f"IDALL {IDALL} is a special full value"
    con = A.consequence(AREA)
    recs, src = A.record_set(DISC, live=True)
    holes = {fog: (con["zone"], TOPO, fog) not in recs for fog in (0, 1)}
    out = {"idall": IDALL, "consequence": con, "record_source": src, "encounter_hole": holes}
    assert con["camera_place"] == 0 and not con["area12_lock"] and not con["spawn_weather"] and not con["beach_arm"], con
    assert all(holes.values()), f"(zone {con['zone']}, topo {TOPO}) HAS a record at some fog: {holes} -- pick another area"
    return out


def check_live_and_bind(arm_path: Path) -> dict:
    import arealib as A
    cells = A.live_cells()
    on_cell = sorted(str(p[0][2]) for p in cells.get((DISC, BX, BY), {}).values())
    near = sorted(f"{x},{y}" for (ns, x, y) in cells if ns == DISC and abs(x - BX) <= 1 and abs(y - BY) <= 1)
    assert not on_cell, f"a live mod folder already carries files for ({BX},{BY}): {on_cell}"
    cf = {"Terrain.ff9mesh": [(0, "FF9CustomMap-lab", arm_path, 0.0)]}
    pk, why, walk = A.live_walk_list(DISC, BX, BY, cf)
    names = [(n, k) for (n, _s, k) in walk]
    assert pk == "d1/12,10", f"effective prefab {pk} ({why}), expected the Block[12][10] divert"
    assert names[0] == ("Terrain", "override"), f"walk list {names}: the lab Terrain is not the FIRST walk mesh"
    return {"live_files_on_cell": on_cell, "live_cells_within_1": near, "effective_prefab": pk, "why": why,
            "walk_list": names}


def main() -> int:
    ARMS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"cell": {"disc": DISC, "x": BX, "y": BY}, "rel_path": REL, "base_quads": G, "pitch": PITCH,
                "idall": IDALL, "arms": {}}
    for arm in (1, 4, 16, 64):
        bm, n = build_arm(arm)
        check_uv(bm)
        data = M.ff9mesh_bytes(bm)                       # the kit's validator runs here
        path = ARMS_DIR / f"cost_x{arm}.ff9mesh"
        path.write_bytes(data)
        row = {"file": path.name, "refine": REFINE[arm], "tris": n, "verts": bm.vcount, "bytes": len(data),
               "sha256": hashlib.sha256(data).hexdigest(), "height_tag": TAG[arm]}
        row.update(check_arm(arm, path, n))
        manifest["arms"][str(arm)] = row
        print(f"x{arm:<2} tris {n:>6}  verts {bm.vcount:>6}  {len(data):>9,} B  tag y {TAG[arm]}  "
              f"edge_xz {row['edge_xz']:.3f}  raster {row['raster_samples']} samples, 0 miss  sha {row['sha256'][:12]}")
    manifest["area"] = check_area()
    print(f"area {AREA}: {manifest['area']['consequence']}  encounter hole (fog0, fog1) = "
          f"{manifest['area']['encounter_hole']}  [{manifest['area']['record_source']}]")
    manifest["bind"] = check_live_and_bind(ARMS_DIR / "cost_x1.ff9mesh")
    print(f"bind: {manifest['bind']['effective_prefab']} ({manifest['bind']['why']}); walk {manifest['bind']['walk_list']}")
    print(f"live files on ({BX},{BY}): {manifest['bind']['live_files_on_cell'] or 'none'}; live cells within 1: "
          f"{manifest['bind']['live_cells_within_1'] or 'none'}")
    (ARMS_DIR / "cost_manifest.json").write_text(json.dumps(manifest, indent=1, default=str), encoding="utf-8")
    print(f"wrote {ARMS_DIR}  (deploy target inside the lab folder: {REL})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
