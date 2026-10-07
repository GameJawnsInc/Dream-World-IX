"""Shared instruments for the gap lane `gap_area_layer` (tile AREA bits as an authored layer). READ-ONLY everywhere.

  * consequence(area)          -- every engine/script consequence of an area value, from the PARSED engine tables
                                  (engine_consumers.parse_tables) + the eb scan's beach switch: zone, camera place,
                                  area-12 lock, spawn weather, beach arm, location-text present
  * record_set(disc, live)     -- the set of (zone, topograph, fog) that HAVE an encounter record (stock p0data
                                  discmr, or the live mod-folder override); anything else is a TABLE HOLE
  * stock_walk_list(d, x, y)   -- the cell's effective FORM-1 walk meshes in engine registration order, as
                                  (child_name, mesh_key); IsSea -> SeaBlockPrefab Block[12][0]f (sea4f, disc 1)
  * live_walk_list(ns, x, y)   -- same for a LIVE cell, via the consumption lane's bind-oracle Engine
                                  (effective prefab + which override files bind); unbound slots = stock free riders
  * mesh_arrays(...)           -- per-triangle numpy arrays (V[T,3,3], idall[T]) from an EXACT container match
                                  (disc4/d4lib.mesh_objects -- NOT extract.read_block, which has the sea4/sea4f and
                                  river/riverjoint substring-prefix bug) or from a .ff9mesh file (own parser)
  * raster(meshes, pitch)      -- the engine's SKY ground query vectorized: first mesh in registration order with a
                                  passing hit, first passing tri in buffer order (skip-ids out, geometric ny>0.1,
                                  0x31EE veto abandons the mesh). Calibrated against world/placement.place.

Stock decoded meshes are cached as numpy in the SESSION SCRATCHPAD (outside the repo -- provenance gate).
"""
from __future__ import annotations

import json
import os
import re
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np                                   # noqa: E402

HERE = Path(__file__).resolve().parent
TM = HERE.parent
OUT = HERE / "out"
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
sys.path.insert(0, str(TM / "disc4"))
sys.path.insert(0, str(TM / "consumption"))
sys.path.insert(0, str(HERE))
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
SCRATCH = Path(os.environ.get("AREA_LANE_SCRATCH", r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                                                   r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\area_lane"))

IDALL_SKIP = (4078, 4088, 2040)
VETO = 0x31EE
FORM1_WALK_SLOTS = {"ObjectForm1", "TerrainForm1", "VolcanoCrater1", "VolcanoLava1", "Beach1", "Beach2", "Stream",
                    "River", "RiverJoint", "Falls", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6"}
LAND_PARTS = {"Object", "Terrain", "VolcanoCrater1", "VolcanoLava1"}
SPAWN_WEATHER_AREAS = (9, 12, 13)           # ff9.cs:8510-8519 (w_weatherDeside, one-shot)
LOCK_AREA = 12                              # ff9.cs:2771 / :3199 (scenario < 4990)

_CENSUS = None
_TABLES = None


def census():
    global _CENSUS
    if _CENSUS is None:
        _CENSUS = json.loads((TM / "consumption/out/consumption_census.json").read_text(encoding="utf-8"))
    return _CENSUS


def tables():
    global _TABLES
    if _TABLES is None:
        import engine_consumers as EC
        _TABLES = EC.parse_tables()
    return _TABLES


def decode(idall):
    idall = int(idall)
    return {"event": (idall & 0xC000) >> 14, "area": (idall & 0x3F00) >> 8, "topo": (idall & 0xFC) >> 2,
            "flags": idall & 3}


def consequence(area: int) -> dict:
    t = tables()
    place = t["w_cameraArea2Place"][area]
    return {"area": area, "zone": t["w_worldAreaZone"][area], "camera_place": place,
            "area12_lock": area == LOCK_AREA, "spawn_weather": area in SPAWN_WEATHER_AREAS,
            "beach_arm": area in t["BeachData"]}


# ------------------------------------------------------------------------------------------- encounter records
_RECS = {}


def record_set(disc: int, live: bool = False):
    """{(zone, topo, fog)} with a record in the disc's table. live=True reads the stacked mod-folder override when
    one exists (FolderNames order), else falls back to stock. Returns (set, source_label)."""
    key = (disc, live)
    if key in _RECS:
        return _RECS[key]
    from ff9mapkit.world import worldpack as WP
    src = "stock p0data"
    dm = None
    if live:
        for fo in ("FF9CustomMap", "FF9CustomMap-world", "MoguriMain", "MoguriVideo", "FF9CustomMap-schema",
                   "FF9CustomMap-msgs"):
            p = GAME / fo / f"StreamingAssets/assets/resources/worldmap/wmap/disc{disc}/discmr.img.bytes"
            if p.is_file():
                dm = WP.Discmr.from_bytes(p.read_bytes(), disc=disc)
                src = str(p)
                break
    if dm is None:
        dm = WP.load_discmr(disc)
    info = WP.zone_info()
    out = set()
    for z in range(WP.ZONE_COUNT):
        for i in range(info[z], info[z + 1]):
            r = dm.encounters[i]
            out.add((z, r.topograph, r.fog))
    _RECS[key] = (out, src)
    return _RECS[key]


# ------------------------------------------------------------------------------------------- location text
_NAMES = None


def location_names(lang="us"):
    """{area: name} from embeddedasset/text/<lang>/etc/worldloc.mes ([ENDN]-split, index = area;
    EtcImporter -> FF9TextTool.SetWorldLocationText). Resolved at runtime; never written to the repo whole."""
    global _NAMES
    if _NAMES is None:
        from ff9mapkit.battle import extract as BE
        from ff9mapkit.extract import _unitypy, _raw_bytes
        U = _unitypy()
        d = BE._ff9_data_dir(None)
        env = U.load(str(d / "mainData"), str(d / "resources.assets"))
        rm = next(o.read() for o in env.objects if getattr(getattr(o, "type", None), "name", "") == "ResourceManager")
        idx = {str(p).lower(): ptr for p, ptr in rm.m_Container}
        b = _raw_bytes(idx[f"embeddedasset/text/{lang}/etc/worldloc.mes"].read())
        _NAMES = {i: s for i, s in enumerate(b.decode("utf-8", "replace").split("[ENDN]"))}
    return _NAMES


# ------------------------------------------------------------------------------------------- meshes
_OBJS = None
_MEM = {}


def _objs():
    global _OBJS
    if _OBJS is None:
        import d4lib
        _OBJS = d4lib.mesh_objects()
    return _OBJS


def arrays_from_bm(verts, tangents, flat_index):
    fi = np.asarray(flat_index, dtype=np.int64)
    V = np.asarray(verts, dtype=np.float64)[fi].reshape(-1, 3, 3)
    T = np.asarray(tangents, dtype=np.float64)
    ids = np.rint(T[fi[0::3], 0]).astype(np.int64)
    return V, ids


def stock_mesh(mesh_key: str):
    """mesh_key 'd1/0_1/12,0/sea4f' -> (V, idall) via the EXACT container; cached in the scratchpad."""
    if mesh_key in _MEM:
        return _MEM[mesh_key]
    SCRATCH.mkdir(parents=True, exist_ok=True)
    cp = SCRATCH / ("m_" + re.sub(r"[^A-Za-z0-9_]+", "_", mesh_key) + ".npz")
    if cp.is_file():
        z = np.load(cp)
        _MEM[mesh_key] = (z["V"], z["ids"])
        return _MEM[mesh_key]
    m = re.match(r"d(\d)/([0-9_]+)/(\d+),(\d+)/(.+)$", mesh_key)
    d, lod, x, y, part = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4)), m.group(5)
    o = _objs()[(d, lod, x, y, part)]
    import d4lib
    bm = d4lib.decode(o, d, x, y, lod)
    V, ids = arrays_from_bm(bm.verts, bm.tangents, bm.flat_index)
    np.savez_compressed(cp, V=V, ids=ids)
    _MEM[mesh_key] = (V, ids)
    return V, ids


def stock_bm(mesh_key: str):
    m = re.match(r"d(\d)/([0-9_]+)/(\d+),(\d+)/(.+)$", mesh_key)
    d, lod, x, y, part = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4)), m.group(5)
    import d4lib
    return d4lib.decode(_objs()[(d, lod, x, y, part)], d, x, y, lod)


def read_ff9mesh_arrays(path):
    """Own .ff9mesh parser (header F9WM, <iiii version,vcount,icount,flags; pos, [nrm], [uv], [tan], int32 idx)."""
    b = Path(path).read_bytes()
    if b[:4] != b"F9WM":
        raise ValueError(f"not a .ff9mesh: {path}")
    ver, vc, ic, fl = struct.unpack_from("<iiii", b, 4)
    off = 20
    pos = np.frombuffer(b, dtype="<f4", count=vc * 3, offset=off).reshape(vc, 3).astype(np.float64)
    off += vc * 12
    if fl & 1:
        off += vc * 12
    if fl & 2:
        off += vc * 8
    if not fl & 4:
        raise ValueError(f"{path}: no tangent channel (flag bit 4) -- the walk query would index an empty array")
    tan = np.frombuffer(b, dtype="<f4", count=vc * 4, offset=off).reshape(vc, 4).astype(np.float64)
    off += vc * 16
    idx = np.frombuffer(b, dtype="<i4", count=ic, offset=off).astype(np.int64)
    V = pos[idx].reshape(-1, 3, 3)
    ids = np.rint(tan[idx[0::3], 0]).astype(np.int64)
    return V, ids


# ------------------------------------------------------------------------------------------- walk lists
def _engine():
    import bind_oracle as BO
    return BO.Engine(census())


def _children(prefab_key):
    return {c["go"]: c["mesh_key"] for c in census()["prefabs"][prefab_key]["children"]}


def stock_walk_list(d: int, x: int, y: int):
    """[(child_name, mesh_key)] -- form-1 walk meshes of a STOCK cell in registration order."""
    E = _engine()
    if E.is_sea(d, x, y):
        return [("Sea4", "d1/0_1/12,0/sea4f")]          # SeaBlockPrefab from disc 1 even on disc 4 (WMWorld.cs:1198)
    pk = f"d{d}/{x},{y}"
    order, _ = E.bind_list(d, x, y, pk, {})
    ch = _children(pk)
    return [(n, ch[n]) for (n, s) in order if s in FORM1_WALK_SLOTS and n in ch]


def live_cells():
    """{(ns, x, y): cell_files} for every cell with a loose override in the live FolderNames stack."""
    import bind_oracle as BO
    return BO.scan_overrides(GAME, BO.folder_names(GAME))


def live_walk_list(ns: int, x: int, y: int, cell_files):
    """(prefab_key, why, [(child_name, source, kind)]) where kind = 'override' (source = file path) or
    'stock' (source = mesh_key, a free rider of the effective prefab)."""
    E = _engine()
    pk, why, _dt = E.effective(ns, x, y, cell_files)
    order, bound = E.bind_list(ns, x, y, pk, cell_files)
    ch = _children(pk)
    out = []
    for (n, s) in order:
        if s not in FORM1_WALK_SLOTS:
            continue
        f = cell_files.get(f"{n}.ff9mesh")
        if f:
            out.append((n, str(f[0][2]), "override"))
        elif n in ch:
            out.append((n, ch[n], "stock"))
    return pk, why, out


def load_walk_arrays(walk):
    """walk = [(name, source, kind)] -> [(name, V, ids)]"""
    res = []
    for name, src, kind in walk:
        V, ids = read_ff9mesh_arrays(src) if kind == "override" else stock_mesh(src)
        res.append((name, V, ids))
    return res


# ------------------------------------------------------------------------------------------- the raster
def sample_grid(pitch=1.0, ox=0.37, oz=0.61):
    n = int(round(64 / pitch))
    xs = (np.arange(n) + ox) * pitch
    zs = -(np.arange(n) + oz) * pitch
    X, Z = np.meshgrid(xs, zs, indexing="ij")           # [i (x), j (z-row)]
    return X.ravel(), Z.ravel(), n


def raster(meshes, pitch=1.0, chunk=1024):
    """meshes = [(name, V[T,3,3], ids[T])] in registration order, block-local frame.
    Returns (idall[S] (-1 = MISS), part_index[S] (-1), y[S]) for the sample grid of sample_grid(pitch)."""
    px, pz, n = sample_grid(pitch)
    S = px.size
    out_id = np.full(S, -1, np.int64)
    out_pi = np.full(S, -1, np.int16)
    out_y = np.zeros(S)
    unresolved = np.ones(S, bool)
    for pi, (name, V, ids) in enumerate(meshes):
        if not unresolved.any():
            break
        if V.size == 0:
            continue
        a, b, c = V[:, 0], V[:, 1], V[:, 2]
        u, v = b - a, c - a
        cx = u[:, 1] * v[:, 2] - u[:, 2] * v[:, 1]
        cy = u[:, 2] * v[:, 0] - u[:, 0] * v[:, 2]
        cz = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
        L = np.sqrt(cx * cx + cy * cy + cz * cz)
        L[L == 0] = 1.0
        d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
        ok = (cy / L > 0.1) & ~np.isin(ids, IDALL_SKIP) & (np.abs(d) >= 1e-12)
        ti = np.nonzero(ok)[0]
        if ti.size == 0:
            continue
        A, B, C, D = a[ti], b[ti], c[ti], d[ti]
        # sample-axis AABB prefilter per chunk
        for s0 in range(0, S, chunk):
            sl = np.arange(s0, min(S, s0 + chunk))
            sl = sl[unresolved[sl]]
            if sl.size == 0:
                continue
            x = px[sl][None, :]
            z = pz[sl][None, :]
            w0 = ((B[:, 2:3] - C[:, 2:3]) * (x - C[:, 0:1]) + (C[:, 0:1] - B[:, 0:1]) * (z - C[:, 2:3])) / D[:, None]
            w1 = ((C[:, 2:3] - A[:, 2:3]) * (x - C[:, 0:1]) + (A[:, 0:1] - C[:, 0:1]) * (z - C[:, 2:3])) / D[:, None]
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
            hit = inside.any(axis=0)
            if not hit.any():
                continue
            first = inside.argmax(axis=0)
            hs = np.nonzero(hit)[0]
            tf = first[hs]
            tri = ti[tf]
            idv = ids[tri]
            keep = idv != VETO                          # a veto first-hit abandons THIS mesh for the sample
            hs, tf, tri, idv = hs[keep], tf[keep], tri[keep], idv[keep]
            ww0, ww1, ww2 = w0[tf, hs], w1[tf, hs], w2[tf, hs]
            hy = ww0 * A[tf, 1] + ww1 * B[tf, 1] + ww2 * C[tf, 1]
            g = sl[hs]
            out_id[g] = idv
            out_pi[g] = pi
            out_y[g] = hy
            unresolved[g] = False
    return out_id, out_pi, out_y


def tri_hist(V, ids):
    """Per-area histogram of a mesh: {area: [tris, up_tris, up_plan_area]} (skip-ids excluded from 'up')."""
    a, b, c = V[:, 0], V[:, 1], V[:, 2]
    u, v = b - a, c - a
    cx = u[:, 1] * v[:, 2] - u[:, 2] * v[:, 1]
    cy = u[:, 2] * v[:, 0] - u[:, 0] * v[:, 2]
    cz = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
    L = np.sqrt(cx * cx + cy * cy + cz * cz)
    L[L == 0] = 1.0
    up = (cy / L > 0.1) & ~np.isin(ids, IDALL_SKIP)
    plan = np.abs(cy) / 2
    area = (ids & 0x3F00) >> 8
    out = {}
    for ar in np.unique(area):
        m = area == ar
        out[int(ar)] = [int(m.sum()), int((m & up).sum()), round(float(plan[m & up].sum()), 2)]
    return out
