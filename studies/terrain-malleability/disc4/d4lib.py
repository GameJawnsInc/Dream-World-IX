"""Shared instruments for the disc-1 vs disc-4 natural-experiment study (lane `disc4`).

Everything here is READ-ONLY on the install. Imported by census.py / calibrate.py / anatomy.py.

Instruments (each calibrated by calibrate.py before it is trusted):
  * raw_sig(obj)            -- the mesh asset's raw bytes (vertex buffer, index buffer, channel layout,
                               submeshes, name, local AABB). Two meshes are "byte-identical" iff the
                               vbuf/ibuf/channels/submeshes match.
  * compare(bm1, bm4)       -- classify a NON-identical pair: same topology (vcount + index buffer equal)
                               with per-channel deltas (pos / normal / uv / tangent.x=IDALL / tangent.yzw),
                               plus a GEOMETRIC triangle multiset match that survives re-ordering:
                               shared-exact tris, re-heighted tris (same XZ footprint, new Y),
                               d1-only / d4-only tris, attr changes (IDALL / UV / winding) on shared tris.
  * ground_grid(meshlist)   -- the kit's engine-faithful ground query (placement.place, sky ray) over a
                               1u lattice of a block -> (y, mesh, idall, topo) per sample.
  * edge_profile(bm, side)  -- the block-border vertex set on one side (for weld checks).
"""
from __future__ import annotations

import math
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit.world import placement as P        # noqa: E402

MESH_RE = re.compile(r"worldmap/disc(\d)/([0-9_]+)/r(\d+)/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
R = 3          # position rounding (decimals) for geometric tri keys -- 1e-3u, far below the 4u lattice
RU = 5         # uv rounding


def mesh_objects():
    """{(disc, lod, x, y, part_lower): ObjectReader} for every worldmap block sub-mesh, both discs."""
    env = X._worldmap_env(1)
    out = {}
    for c, o in X._mesh_index(env).items():
        m = MESH_RE.search(c)
        if m:
            d, lod, _r, x, y, part = m.groups()
            out[(int(d), lod, int(x), int(y), part)] = o
    return out


def raw_sig(o) -> dict:
    md = o.read()
    vd = md.m_VertexData
    ch = tuple((int(getattr(c, "stream", 0)), int(c.offset), int(getattr(c, "format", 0)), int(c.dimension))
               for c in vd.m_Channels)
    sm = tuple((int(s.firstByte), int(s.indexCount), int(getattr(s, "topology", 0))) for s in md.m_SubMeshes)
    aabb = md.m_LocalAABB
    try:
        ab = (round(aabb.m_Center.x, 4), round(aabb.m_Center.y, 4), round(aabb.m_Center.z, 4),
              round(aabb.m_Extent.x, 4), round(aabb.m_Extent.y, 4), round(aabb.m_Extent.z, 4))
    except AttributeError:
        ab = None
    return {"vbuf": bytes(vd.m_DataSize), "ibuf": bytes(md.m_IndexBuffer), "ch": ch, "sm": sm,
            "vcount": int(vd.m_VertexCount), "name": md.m_Name, "aabb": ab}


def sig_identical(a: dict, b: dict) -> bool:
    return a["vbuf"] == b["vbuf"] and a["ibuf"] == b["ibuf"] and a["ch"] == b["ch"] and a["sm"] == b["sm"]


def decode(o, disc, x, y, lod):
    from ff9mapkit.extract import env_lock
    with env_lock:
        return X._decode_world_mesh(o, disc=disc, x=x, y=y, lod=lod)


def _geom_ny(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return ny / L


def tri_records(bm):
    """Per triangle: full-position key, XZ key, IDALL, uv tuple aligned to the sorted corners, winding ny."""
    V, U, T, N, fi = bm.verts, bm.uvs, bm.tangents, bm.normals, bm.flat_index
    recs = []
    for t in range(len(fi) // 3):
        idx = fi[3 * t:3 * t + 3]
        cs = [V[i] for i in idx]
        order = sorted(range(3), key=lambda k: (round(cs[k][0], R), round(cs[k][1], R), round(cs[k][2], R)))
        kfull = tuple((round(cs[k][0], R), round(cs[k][1], R), round(cs[k][2], R)) for k in order)
        kxz = tuple(sorted((round(c[0], R), round(c[2], R)) for c in cs))
        uv = tuple((round(U[idx[k]][0], RU), round(U[idx[k]][1], RU)) for k in order) if U else None
        nr = tuple(tuple(round(c, 3) for c in N[idx[k]]) for k in order) if N else None
        idall = int(round(T[idx[0]][0])) if T else None
        area = abs((cs[1][0] - cs[0][0]) * (cs[2][2] - cs[0][2]) - (cs[2][0] - cs[0][0]) * (cs[1][2] - cs[0][2])) / 2
        recs.append({"t": t, "kfull": kfull, "kxz": kxz, "uv": uv, "nrm": nr, "id": idall,
                     "ny": _geom_ny(*cs), "cs": cs, "area": area})
    return recs


def _pair(keys_a, keys_b):
    """Multiset pairing in buffer order: returns (pairs [(ia, ib)], unmatched_a, unmatched_b)."""
    pool = defaultdict(list)
    for i, k in enumerate(keys_b):
        pool[k].append(i)
    for k in pool:
        pool[k].reverse()
    pairs, ua = [], []
    for i, k in enumerate(keys_a):
        if pool.get(k):
            pairs.append((i, pool[k].pop()))
        else:
            ua.append(i)
    used = {j for _, j in pairs}
    ub = [j for j in range(len(keys_b)) if j not in used]
    return pairs, ua, ub


def compare(bm1, bm4) -> dict:
    """Classify a pair that is NOT byte-identical. See module docstring."""
    out = {"v1": bm1.vcount, "v4": bm4.vcount, "t1": len(bm1.tris), "t4": len(bm4.tris)}
    same_topo = bm1.vcount == bm4.vcount and bm1.flat_index == bm4.flat_index
    out["same_topology"] = same_topo
    chans = {}
    if same_topo:
        for ci in sorted(set(bm1.chan_arrays) | set(bm4.chan_arrays)):
            a, b = bm1.chan_arrays.get(ci), bm4.chan_arrays.get(ci)
            if a is None or b is None:
                chans[str(ci)] = "channel-missing"
                continue
            if ci == X.CH_TAN:
                n0 = sum(1 for p, q in zip(a, b) if p[0] != q[0])
                n1 = sum(1 for p, q in zip(a, b) if p[1:] != q[1:])
                chans["tan.x"] = n0
                chans["tan.yzw"] = n1
            else:
                nm = {X.CH_POS: "pos", X.CH_NRM: "nrm", X.CH_UV: "uv"}.get(ci, f"ch{ci}")
                chans[nm] = sum(1 for p, q in zip(a, b) if p != q)
        if bm1.verts and bm4.verts:
            d = [(q[0] - p[0], q[1] - p[1], q[2] - p[2]) for p, q in zip(bm1.verts, bm4.verts)]
            moved = [v for v in d if v != (0.0, 0.0, 0.0)]
            out["pos_moved_verts"] = len(moved)
            if moved:
                out["pos_max_abs"] = [round(max(abs(v[k]) for v in moved), 4) for k in range(3)]
                out["pos_dy_range"] = [round(min(v[1] for v in moved), 4), round(max(v[1] for v in moved), 4)]
                out["pos_xz_moved"] = sum(1 for v in moved if v[0] != 0.0 or v[2] != 0.0)
    out["chan_diff"] = chans

    r1, r4 = tri_records(bm1), tri_records(bm4)
    pairs, u1, u4 = _pair([r["kfull"] for r in r1], [r["kfull"] for r in r4])
    # among exact-geometry pairs: attribute changes
    id_ch, uv_ch, nrm_ch, wind_ch, reorder = [], [], [], 0, 0
    for i, j in pairs:
        a, b = r1[i], r4[j]
        if a["id"] != b["id"]:
            id_ch.append((i, j))
        if a["uv"] != b["uv"]:
            uv_ch.append((i, j))
        if a["nrm"] != b["nrm"]:
            nrm_ch.append((i, j))
        if (a["ny"] > 0) != (b["ny"] > 0):
            wind_ch += 1
        if i != j:
            reorder += 1
    # re-heighted: same XZ footprint among the unmatched
    xpairs, x1, x4 = _pair([r1[i]["kxz"] for i in u1], [r4[j]["kxz"] for j in u4])
    rh = [(u1[a], u4[b]) for a, b in xpairs]
    only1 = [u1[a] for a in x1]
    only4 = [u4[b] for b in x4]
    dys = []
    for i, j in rh:
        c1 = sorted(r1[i]["cs"], key=lambda c: (round(c[0], R), round(c[2], R)))
        c4 = sorted(r4[j]["cs"], key=lambda c: (round(c[0], R), round(c[2], R)))
        dys.extend(q[1] - p[1] for p, q in zip(c1, c4))
    out.update({
        "tri_shared_exact": len(pairs), "tri_reheighted": len(rh), "tri_only1": len(only1),
        "tri_only4": len(only4), "tri_reordered_in_shared": reorder,
        "shared_id_changed": len(id_ch), "shared_uv_changed": len(uv_ch), "shared_nrm_changed": len(nrm_ch),
        "shared_winding_flipped": wind_ch,
        "area1": round(sum(r["area"] for r in r1), 2), "area4": round(sum(r["area"] for r in r4), 2),
        "area_only1": round(sum(r1[i]["area"] for i in only1), 2),
        "area_only4": round(sum(r4[j]["area"] for j in only4), 2),
        "area_reheighted": round(sum(r1[i]["area"] for i, _ in rh), 2),
    })
    if dys:
        out["reheight_dy"] = {"min": round(min(dys), 4), "max": round(max(dys), 4),
                              "mean": round(sum(dys) / len(dys), 4),
                              "nonzero": sum(1 for d in dys if abs(d) > 1e-4)}
    # topograph / area / event transitions on shared-geometry tris whose id changed
    tr = Counter()
    for i, j in id_ch:
        a, b = X.decode_id(r1[i]["id"]), X.decode_id(r4[j]["id"])
        tr[(a["event"], a["area"], a["topograph"], b["event"], b["area"], b["topograph"])] += 1
    out["id_transitions"] = [[*k, v] for k, v in tr.most_common()]
    # changed region (block-local), split by kind
    def _bbox(cs):
        if not cs:
            return None
        xs, ys, zs = [c[0] for c in cs], [c[1] for c in cs], [c[2] for c in cs]
        return [round(min(xs), 3), round(max(xs), 3), round(min(ys), 3), round(max(ys), 3),
                round(min(zs), 3), round(max(zs), 3)]
    ch_cs = []
    for i in only1:
        ch_cs += r1[i]["cs"]
    for j in only4:
        ch_cs += r4[j]["cs"]
    for i, j in rh:
        ch_cs += r1[i]["cs"] + r4[j]["cs"]
    attr_cs = []
    for i, j in set(id_ch) | set(uv_ch):
        attr_cs += r1[i]["cs"]
    out["bbox_geom_change_local"] = _bbox(ch_cs)        # [x0,x1,y0,y1,z0,z1]
    out["bbox_attr_change_local"] = _bbox(attr_cs)
    # topograph histogram of each side's unique tris (what was cut out / what was put in)
    out["only1_topo"] = dict(Counter(X.decode_id(r1[i]["id"])["topograph"] for i in only1 if r1[i]["id"] is not None))
    out["only4_topo"] = dict(Counter(X.decode_id(r4[j]["id"])["topograph"] for j in only4 if r4[j]["id"] is not None))
    # does the geometric change touch the block border? (weld relevance)
    def _on_border(c):
        return abs(c[0]) < 1e-3 or abs(c[0] - 64) < 1e-3 or abs(c[2]) < 1e-3 or abs(c[2] + 64) < 1e-3
    out["geom_change_touches_border"] = any(_on_border(c) for c in ch_cs)
    out["n_border_verts_in_change"] = sum(1 for c in ch_cs if _on_border(c))
    return out


def edge_profile(bm, side: str) -> set:
    """Rounded (along, y) of every vertex on one block border. side in E/W/N/S.
    Local frame: x in [0,64] (W=0, E=64), z in [-64,0] (N edge z=0 = smaller row y; S edge z=-64)."""
    out = set()
    for v in bm.verts:
        if side == "E" and abs(v[0] - 64) < 1e-3:
            out.add((round(v[2], R), round(v[1], R)))
        elif side == "W" and abs(v[0]) < 1e-3:
            out.add((round(v[2], R), round(v[1], R)))
        elif side == "N" and abs(v[2]) < 1e-3:
            out.add((round(v[0], R), round(v[1], R)))
        elif side == "S" and abs(v[2] + 64) < 1e-3:
            out.add((round(v[0], R), round(v[1], R)))
    return out


WALK_PARTS = {p.lower() for p in P.REGISTRATION_ORDER}


def meshlist_for(parts: dict):
    """{part_lower: BlockMesh} -> placement meshlist (engine registration order), dropping parts the
    engine never registers as walkmesh. Returns (meshlist, dropped_parts)."""
    keep = {k: v for k, v in parts.items() if k in WALK_PARTS}
    return P.build_meshlist(keep), sorted(set(parts) - set(keep))


def ground_grid(meshlist, pitch: float = 1.0):
    """Sky-cast ground query on a pitch lattice over the block (local frame, cell centres)."""
    idx = [P.build_index(bm) for _, bm in meshlist]
    n = int(round(64 / pitch))
    res = {}
    for i in range(n):
        for j in range(n):
            x = (i + 0.5) * pitch
            z = -(j + 0.5) * pitch
            res[(i, j)] = P.place(meshlist, x, z, 0.0, sky=True, index=idx)
    return res
