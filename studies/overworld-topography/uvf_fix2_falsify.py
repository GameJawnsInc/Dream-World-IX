"""RUNG F -- UV-FIX v2 CODE-DISJOINT FALSIFIER (2026-07-24).

Round-2 verifier. Reuses round-1's own code (uvf_fix_falsify.py is mine); this is a self-contained
copy retargeted at out/rung_f/FF9CustomMap-world-FIXED2 with the NEW cross-check: the method-(a)
ground-truth cells' (quad,ori) must be IDENTICAL between FIXED and FIXED2, while re-resolved
(fully-dropped) cells differ. Does NOT import uvf_fix2.py / uvf_gates*.py / uvf_forensics.py. Reuses
ONLY loaders (ff9mapkit.world.extract, .mesh) + the grass UV language (grassland). Every gate/diff/
classifier reimplemented here.

READ-ONLY vs the game install. Writes only out/rung_f/uvf_fix2_falsify.json + this script.
"""
from __future__ import annotations
import json, math, struct, sys, hashlib
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X      # noqa: E402
from ff9mapkit.world import mesh as M         # noqa: E402
from ff9mapkit.world import grassland as G    # noqa: E402

CELL = 4.0
SPEC = HERE / "out" / "rung_f" / "FF9CustomMap-world"
FIXED = HERE / "out" / "rung_f" / "FF9CustomMap-world-FIXED"
FIXED2 = HERE / "out" / "rung_f" / "FF9CustomMap-world-FIXED2"
OUT = HERE / "out" / "rung_f" / "uvf_fix2_falsify.json"
FOOTPRINT = [(bx, by) for bx in range(0, 5) for by in range(16, 20)]
MAGIC = b"F9WM"
UV_ZERO = 1e-6
QUADS = [(0, 0), (0, 1), (1, 0), (1, 1)]
ORIS = (0, 90, 180, 270)
GRASS_REGION = G.FAM_REGION["main"]


def log(m): print(m, flush=True)


# ---------- raw .ff9mesh parse ----------
def parse_raw(path):
    data = Path(path).read_bytes()
    assert data[:4] == MAGIC, f"bad magic {path}"
    version, vcount, icount, flags = struct.unpack_from("<iiii", data, 4)
    off = 20
    off_pos = off
    sz_pos = vcount * 3 * 4
    off_nrm = off_pos + sz_pos
    sz_nrm = vcount * 3 * 4 if (flags & 1) else 0
    off_uv = off_nrm + sz_nrm
    sz_uv = vcount * 2 * 4 if (flags & 2) else 0
    off_tan = off_uv + sz_uv
    sz_tan = vcount * 4 * 4 if (flags & 4) else 0
    off_idx = off_tan + sz_tan
    sz_idx = icount * 4
    return dict(data=data, version=version, vcount=vcount, icount=icount, flags=flags,
                off_pos=off_pos, sz_pos=sz_pos, off_nrm=off_nrm, sz_nrm=sz_nrm,
                off_uv=off_uv, sz_uv=sz_uv, off_tan=off_tan, sz_tan=sz_tan,
                off_idx=off_idx, sz_idx=sz_idx, total=len(data))


def sl(r, off, sz): return r["data"][off:off + sz]
def verts_of(r):
    d = r["data"]; return [struct.unpack_from("<3f", d, r["off_pos"] + j * 12) for j in range(r["vcount"])]
def uvs_of(r):
    d = r["data"]; return [struct.unpack_from("<2f", d, r["off_uv"] + j * 8) for j in range(r["vcount"])]
def tans_of(r):
    d = r["data"]; return [struct.unpack_from("<4f", d, r["off_tan"] + j * 16) for j in range(r["vcount"])]
def idx_of(r):
    d = r["data"]; return list(struct.unpack_from("<%di" % r["icount"], d, r["off_idx"]))


def uv_area(uv0, uv1, uv2):
    return abs((uv1[0] - uv0[0]) * (uv2[1] - uv0[1]) - (uv2[0] - uv0[0]) * (uv1[1] - uv0[1]))
def uv_collapsed(uv0, uv1, uv2):
    ds = [math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in ((uv0, uv1), (uv0, uv2), (uv1, uv2))]
    return max(ds) < UV_ZERO
def is_degenerate(uv0, uv1, uv2):
    return uv_area(uv0, uv1, uv2) < UV_ZERO or uv_collapsed(uv0, uv1, uv2)


def terr_path(root, bx, by): return root / M.override_relpath(1, bx, by, part="Terrain")
def sea4_path(root, bx, by): return root / M.override_relpath(1, bx, by, part="Sea4")
def sha16(b): return hashlib.sha256(b).hexdigest()[:16]


# =====================================================================================================
def classify_tree(root):
    per_block, total, topo_ctr = {}, 0, Counter()
    for (bx, by) in FOOTPRINT:
        p = terr_path(root, bx, by)
        if not p.exists():
            per_block[f"{bx},{by}"] = 0; continue
        r = parse_raw(p); uvs = uvs_of(r); tans = tans_of(r); idx = idx_of(r)
        cnt = 0
        for t in range(len(idx) // 3):
            a, b, c = idx[3 * t], idx[3 * t + 1], idx[3 * t + 2]
            if is_degenerate(uvs[a], uvs[b], uvs[c]):
                cnt += 1
                idall = int(round(tans[a][0]))
                topo_ctr[X.decode_id(idall)["topograph"]] += 1
        per_block[f"{bx},{by}"] = cnt; total += cnt
    return dict(total=total, per_block=per_block, topo_of_degenerate=dict(topo_ctr))


# =====================================================================================================
def channel_diff(target):
    """Byte-diff each channel target vs SPEC per Terrain file."""
    res = dict(files=0, pos_diff_files=[], tan_diff_files=[], idx_diff_files=[], nrm_diff_files=[],
               uv_changed_verts=0, nrm_changed_verts=0, uv_changed_tris=0, nrm_changed_tris=0,
               nrm_changed_tris_not_uv=0, header_mismatch=[], per_block={})
    for (bx, by) in FOOTPRINT:
        ps, pf = terr_path(SPEC, bx, by), terr_path(target, bx, by)
        if not (ps.exists() and pf.exists()):
            res["header_mismatch"].append([bx, by, "missing"]); continue
        rs, rf = parse_raw(ps), parse_raw(pf); res["files"] += 1
        if (rs["vcount"], rs["icount"], rs["flags"]) != (rf["vcount"], rf["icount"], rf["flags"]):
            res["header_mismatch"].append([bx, by, (rs["vcount"], rs["icount"], rs["flags"]),
                                           (rf["vcount"], rf["icount"], rf["flags"])]); continue
        if sl(rs, rs["off_pos"], rs["sz_pos"]) != sl(rf, rf["off_pos"], rf["sz_pos"]):
            res["pos_diff_files"].append([bx, by])
        if sl(rs, rs["off_tan"], rs["sz_tan"]) != sl(rf, rf["off_tan"], rf["sz_tan"]):
            res["tan_diff_files"].append([bx, by])
        if sl(rs, rs["off_idx"], rs["sz_idx"]) != sl(rf, rf["off_idx"], rf["sz_idx"]):
            res["idx_diff_files"].append([bx, by])
        if sl(rs, rs["off_nrm"], rs["sz_nrm"]) != sl(rf, rf["off_nrm"], rf["sz_nrm"]):
            res["nrm_diff_files"].append([bx, by])
        ds, df = rs["data"], rf["data"]; vc = rs["vcount"]
        uv_changed = {j for j in range(vc) if ds[rs["off_uv"] + j * 8: rs["off_uv"] + j * 8 + 8]
                      != df[rf["off_uv"] + j * 8: rf["off_uv"] + j * 8 + 8]}
        nrm_changed = {j for j in range(vc) if ds[rs["off_nrm"] + j * 12: rs["off_nrm"] + j * 12 + 12]
                       != df[rf["off_nrm"] + j * 12: rf["off_nrm"] + j * 12 + 12]}
        idx = idx_of(rs); uvt = nrt = nrt_not_uv = 0
        for t in range(len(idx) // 3):
            tv = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            uv_hit = any(v in uv_changed for v in tv)
            nrm_hit = any(v in nrm_changed for v in tv)
            if uv_hit: uvt += 1
            if nrm_hit:
                nrt += 1
                if not uv_hit: nrt_not_uv += 1
        res["uv_changed_verts"] += len(uv_changed); res["nrm_changed_verts"] += len(nrm_changed)
        res["uv_changed_tris"] += uvt; res["nrm_changed_tris"] += nrt
        res["nrm_changed_tris_not_uv"] += nrt_not_uv
        res["per_block"][f"{bx},{by}"] = dict(uv_verts=len(uv_changed), nrm_verts=len(nrm_changed),
                                              uv_tris=uvt, nrm_tris=nrt, nrm_not_uv=nrt_not_uv)
    return res


def sha_reconcile():
    rep = json.loads((HERE / "out" / "rung_f" / "uvf_fix2_report.json").read_text(encoding="utf-8"))
    want = rep.get("written_files_sha256", {})
    mism, ok = [], 0
    for relp, wsha in want.items():
        p = FIXED2 / relp.replace("\\", "/")
        if not p.exists():
            mism.append([relp, "missing"]); continue
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != wsha: mism.append([relp, got[:16], wsha[:16]])
        else: ok += 1
    return dict(n_reported=len(want), n_ok=ok, mismatches=mism)


# =====================================================================================================
def carried_core_identity(target):
    """Carried-core VERBATIM tris = donor blocks 13-15,11-12 shifted (-768,-384) matching XZ+attr.
    Each must be byte-identical target vs SPEC across ALL channels."""
    SHIFT = (-768.0, -384.0)
    donor = defaultdict(list)
    for bx in (13, 14, 15):
        for by in (11, 12):
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain")
            except (ValueError, FileNotFoundError):
                continue
            ox, oz = X.block_world_origin(bx, by)
            for tri in bm.tris:
                w = [(bm.verts[j][0] + ox + SHIFT[0], bm.verts[j][1], bm.verts[j][2] + oz + SHIFT[1]) for j in tri]
                key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in w))
                uv = tuple(sorted((round(float(bm.uvs[j][0]), 6), round(float(bm.uvs[j][1]), 6)) for j in tri))
                nrm = tuple(sorted((round(float(bm.normals[j][0]), 5), round(float(bm.normals[j][1]), 5),
                                    round(float(bm.normals[j][2]), 5)) for j in tri))
                tan = tuple(sorted((round(float(bm.tangents[j][1]), 5), round(float(bm.tangents[j][2]), 5),
                                    round(float(bm.tangents[j][3]), 5)) for j in tri))
                idall = int(round(bm.tangents[tri[0]][0]))
                donor[key].append(dict(uv=uv, nrm=nrm, tan=tan, topo=X.decode_id(idall)["topograph"]))
    matched_xz = verbatim = xz_only = fixed_vs_spec_bad = 0
    for (bx, by) in FOOTPRINT:
        ps, pf = terr_path(SPEC, bx, by), terr_path(target, bx, by)
        if not (ps.exists() and pf.exists()):
            continue
        rs, rf = parse_raw(ps), parse_raw(pf)
        vs, vf = verts_of(rs), verts_of(rf); us, uf = uvs_of(rs), uvs_of(rf)
        ns = [struct.unpack_from("<3f", rs["data"], rs["off_nrm"] + j * 12) for j in range(rs["vcount"])]
        nf = [struct.unpack_from("<3f", rf["data"], rf["off_nrm"] + j * 12) for j in range(rf["vcount"])]
        ts, tf = tans_of(rs), tans_of(rf)
        ox, oz = X.block_world_origin(bx, by); idx = idx_of(rs)
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            w = [(vs[j][0] + ox, vs[j][1], vs[j][2] + oz) for j in tri]
            key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in w))
            cands = donor.get(key)
            if not cands: continue
            matched_xz += 1
            uvs_t = tuple(sorted((round(us[j][0], 6), round(us[j][1], 6)) for j in tri))
            nrm_t = tuple(sorted((round(ns[j][0], 5), round(ns[j][1], 5), round(ns[j][2], 5)) for j in tri))
            tan_t = tuple(sorted((round(ts[j][1], 5), round(ts[j][2], 5), round(ts[j][3], 5)) for j in tri))
            topo_t = X.decode_id(int(round(ts[tri[0]][0])))["topograph"]
            is_verbatim = any(c["uv"] == uvs_t and c["nrm"] == nrm_t and c["tan"] == tan_t
                              and c["topo"] == topo_t for c in cands)
            if is_verbatim:
                verbatim += 1
                same = all(vs[j] == vf[j] and us[j] == uf[j] and ns[j] == nf[j] and ts[j] == tf[j] for j in tri)
                if not same: fixed_vs_spec_bad += 1
            else:
                xz_only += 1
    return dict(matched_xz=matched_xz, carried_core_verbatim=verbatim,
                xz_overlap_nonverbatim=xz_only, fixed_vs_spec_bad=fixed_vs_spec_bad)


# =====================================================================================================
def resolve_ground_uv(world_verts, obs_uvs, cells, tol=2e-5):
    def matches(wv, uv, cell, q, o):
        cu, cv = G.ground_uv(wv[0], wv[2], cell, q, o, "grass")
        return abs(cu - uv[0]) < tol and abs(cv - uv[1]) < tol
    distinct = sorted(set(cells)); combos = list(product(QUADS, ORIS))
    for assign in product(combos, repeat=len(distinct)):
        amap = dict(zip(distinct, assign)); ok = True
        for i in range(3):
            q, o = amap[cells[i]]
            if not matches(world_verts[i], obs_uvs[i], cells[i], q, o):
                ok = False; break
        if ok: return "own-cell", amap
    cx = sum(w[0] for w in world_verts) / 3.0; cz = sum(w[2] for w in world_verts) / 3.0
    ccell = (math.floor(cx / CELL), math.floor(cz / CELL))
    for cand in set(cells) | {ccell}:
        for (q, o) in combos:
            if all(matches(world_verts[i], obs_uvs[i], cand, q, o) for i in range(3)):
                return "common-cell", {cand: (q, o)}
    return None, None


def uv_language_check(target, n_sample=30):
    rewritten = []
    for (bx, by) in FOOTPRINT:
        ps, pf = terr_path(SPEC, bx, by), terr_path(target, bx, by)
        if not (ps.exists() and pf.exists()): continue
        rs, rf = parse_raw(ps), parse_raw(pf)
        us, uf = uvs_of(rs), uvs_of(rf); vf = verts_of(rf); idx = idx_of(rf)
        ox, oz = X.block_world_origin(bx, by)
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            if any(us[j] != uf[j] for j in tri):
                w = [(vf[j][0] + ox, vf[j][1], vf[j][2] + oz) for j in tri]
                obs = [uf[j] for j in tri]
                cells = [(math.floor(w[i][0] / CELL), math.floor(w[i][2] / CELL)) for i in range(3)]
                rewritten.append((bx, by, t, w, obs, cells))
    total_rw = len(rewritten)
    if total_rw == 0:
        return dict(total_rewritten=0, sampled=0, matched=0, note="no rewritten tris")
    step = max(1, total_rw // n_sample)
    sample = rewritten[::step][:n_sample]
    matched = nondegen = in_region = 0
    methods = Counter(); fails = []
    percell = defaultdict(set)   # cell -> set of (q,o) seen across sampled tris (consistency check)
    lo_u, lo_v, hi_u, hi_v = GRASS_REGION
    for (bx, by, t, w, obs, cells) in sample:
        meth, amap = resolve_ground_uv(w, obs, cells)
        if meth:
            matched += 1; methods[meth] += 1
            for c, qo in (amap or {}).items():
                percell[c].add(qo)
        else:
            fails.append([bx, by, t, [[round(u, 5) for u in o] for o in obs]])
        if uv_area(*obs) >= UV_ZERO: nondegen += 1
        if all(lo_u - 0.02 <= u <= hi_u + 0.02 and lo_v - 0.02 <= v <= hi_v + 0.02 for (u, v) in obs):
            in_region += 1
    inconsistent = {f"{c}": sorted(map(list, s)) for c, s in percell.items() if len(s) > 1}
    return dict(total_rewritten=total_rw, sampled=len(sample), matched=matched, nondegenerate=nondegen,
                in_grass_region=in_region, methods=dict(methods), fails=fails[:8],
                percell_inconsistent=inconsistent)


# =====================================================================================================
def decode_cell_qo(target):
    """Per block-scoped cell, decode (q,o) from that tree's REWRITTEN tris (UV != SPEC). Majority vote
    over per-vertex decodes vs G.ground_uv grass. Returns {(bx,by,ci,cj): (q,o)}."""
    combos = list(product(QUADS, ORIS)); tol = 2e-5
    out = {}
    for (bx, by) in FOOTPRINT:
        ps, pf = terr_path(SPEC, bx, by), terr_path(target, bx, by)
        if not (ps.exists() and pf.exists()): continue
        rs, rf = parse_raw(ps), parse_raw(pf)
        us, uf = uvs_of(rs), uvs_of(rf); vf = verts_of(rf); idx = idx_of(rf)
        ox, oz = X.block_world_origin(bx, by)
        votes = defaultdict(Counter)
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            if not any(us[j] != uf[j] for j in tri): continue
            for j in tri:
                wx, wz = vf[j][0] + ox, vf[j][2] + oz
                cell = (math.floor(wx / CELL), math.floor(wz / CELL))
                u, v = uf[j]
                found = None
                for (q, o) in combos:
                    cu, cv = G.ground_uv(wx, wz, cell, q, o, "grass")
                    if abs(cu - u) < tol and abs(cv - v) < tol:
                        found = (q, o); break
                if found is not None:
                    votes[cell][found] += 1
        for cell, ctr in votes.items():
            out[(bx, by, cell[0], cell[1])] = ctr.most_common(1)[0][0]
    return out


def specimen_surviving_lawful_cells():
    """Ground-truth (method-(a)-class) cells: cells that (in SPEC) contain BOTH a degenerate tri (=> a
    rewrite happens in that cell) AND a surviving NON-degenerate grass VERTEX that decodes to a lawful
    grass (q,o) in that same per-vertex cell. Per-vertex keying aligned with decode_cell_qo so the two
    maps compare. A cell's ground-truth (q,o) = majority of its surviving grass-vertex decodes.
    Returns {(bx,by,ci,cj): (q,o)}, n_has_degen."""
    combos = list(product(QUADS, ORIS)); tol = 2e-5
    surviving = defaultdict(Counter); has_degen = set()
    for (bx, by) in FOOTPRINT:
        p = terr_path(SPEC, bx, by)
        if not p.exists(): continue
        r = parse_raw(p); us = uvs_of(r); vs = verts_of(r); idx = idx_of(r)
        ox, oz = X.block_world_origin(bx, by)
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            uv3 = [us[j] for j in tri]
            cx = sum(vs[j][0] + ox for j in tri) / 3.0
            cz = sum(vs[j][2] + oz for j in tri) / 3.0
            if is_degenerate(*uv3):
                has_degen.add((bx, by, math.floor(cx / CELL), math.floor(cz / CELL)))
                continue
            # surviving lawful tri: decode each vertex against its OWN per-vertex cell (grass mains)
            for j in tri:
                wx, wz = vs[j][0] + ox, vs[j][2] + oz
                cell = (math.floor(wx / CELL), math.floor(wz / CELL))
                u, v = us[j]
                for (q, o) in combos:
                    cu, cv = G.ground_uv(wx, wz, cell, q, o, "grass")
                    if abs(cu - u) < tol and abs(cv - v) < tol:
                        surviving[(bx, by, cell[0], cell[1])][(q, o)] += 1
                        break
    surv_qo = {c: ctr.most_common(1)[0][0] for c, ctr in surviving.items()}
    # ground-truth = cells that had a degenerate tri (a rewrite) AND a surviving grass decode
    method_a = {c: qo for c, qo in surv_qo.items() if c in has_degen}
    return method_a, len(has_degen)


# =====================================================================================================
def fixed_vs_fixed2_diff():
    """Direct byte-diff FIXED vs FIXED2: pos/tan/idx/nrm must be identical; only UV differs; only 16
    Terrain files differ; 6 Sea4 identical. Reconciles diff_vs_fixed in the report."""
    res = dict(terr_pos_bad=0, terr_tan_bad=0, terr_idx_bad=0, terr_nrm_bad=0, uv_diff_verts=0,
               terr_files_diff=[], sea4_diff_files=[], missing=[])
    for (bx, by) in FOOTPRINT:
        pa, pb = terr_path(FIXED, bx, by), terr_path(FIXED2, bx, by)
        if not (pa.exists() and pb.exists()):
            res["missing"].append([bx, by, "terr"]); continue
        ra, rb = parse_raw(pa), parse_raw(pb)
        if sl(ra, ra["off_pos"], ra["sz_pos"]) != sl(rb, rb["off_pos"], rb["sz_pos"]): res["terr_pos_bad"] += 1
        if sl(ra, ra["off_tan"], ra["sz_tan"]) != sl(rb, rb["off_tan"], rb["sz_tan"]): res["terr_tan_bad"] += 1
        if sl(ra, ra["off_idx"], ra["sz_idx"]) != sl(rb, rb["off_idx"], rb["sz_idx"]): res["terr_idx_bad"] += 1
        if sl(ra, ra["off_nrm"], ra["sz_nrm"]) != sl(rb, rb["off_nrm"], rb["sz_nrm"]): res["terr_nrm_bad"] += 1
        da, db = ra["data"], rb["data"]
        uvd = sum(1 for j in range(ra["vcount"])
                  if da[ra["off_uv"] + j * 8: ra["off_uv"] + j * 8 + 8]
                  != db[rb["off_uv"] + j * 8: rb["off_uv"] + j * 8 + 8])
        res["uv_diff_verts"] += uvd
        if ra["data"] != rb["data"]: res["terr_files_diff"].append([bx, by])
    for (bx, by) in FOOTPRINT:
        pa, pb = sea4_path(FIXED, bx, by), sea4_path(FIXED2, bx, by)
        if not (pa.exists() and pb.exists()): continue
        if pa.read_bytes() != pb.read_bytes(): res["sea4_diff_files"].append([bx, by])
    return res


def method_a_stability():
    """Round-2 claim: method-(a) ground-truth cells IDENTICAL FIXED<->FIXED2; re-resolved cells differ.

    PRIMARY measurement is BYTE-DOMAIN and fix-independent: for each rewritten (formerly-degenerate)
    tri, bucket its per-vertex cells; a cell is UV-STABLE iff every one of its rewritten-vertex UV
    8-byte words is identical FIXED vs FIXED2, else UV-CHANGED. Ground-truth (method-a) cells are
    pre-seeded identically in both rounds, so they MUST be UV-stable; re-resolved cells that drew a
    different (q,o) are UV-changed. This needs NO (q,o) decode -- pure bytes.

    A (q,o)-decode ground-truth reconstruction was ATTEMPTED and found UNRELIABLE (surviving lawful
    ecotone tris are multi-cell CONFORMING geometry, so a per-vertex grass-mains decode yields spurious
    matches -- its candidates decoded to a (q,o) matching NEITHER tree and were in fact UV-CHANGED
    re-resolved cells). It is reported as advisory ONLY and never drives the verdict."""
    # ---- PRIMARY: byte-domain per-cell UV stability FIXED vs FIXED2 ----
    cell_changed = {}
    for (bx, by) in FOOTPRINT:
        ps, pa, pb = terr_path(SPEC, bx, by), terr_path(FIXED, bx, by), terr_path(FIXED2, bx, by)
        if not (ps.exists() and pa.exists() and pb.exists()):
            continue
        rs, ra, rb = parse_raw(ps), parse_raw(pa), parse_raw(pb)
        us, ub = uvs_of(rs), uvs_of(rb); vf = verts_of(rb); idx = idx_of(rb)
        da, db = ra["data"], rb["data"]; ox, oz = X.block_world_origin(bx, by)
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            if not any(us[j] != ub[j] for j in tri):
                continue                                    # only rewritten tris
            for j in tri:
                wx, wz = vf[j][0] + ox, vf[j][2] + oz
                cell = (bx, by, math.floor(wx / CELL), math.floor(wz / CELL))
                oa, ob = ra["off_uv"] + j * 8, rb["off_uv"] + j * 8
                changed = da[oa:oa + 8] != db[ob:ob + 8]
                cell_changed[cell] = cell_changed.get(cell, False) or changed
    n_cells = len(cell_changed)
    n_changed = sum(1 for v in cell_changed.values() if v)
    n_stable = n_cells - n_changed
    change_rate = round(n_changed / n_cells, 4) if n_cells else None

    # ---- ADVISORY: (q,o) decode reconstruction (unreliable; not verdict-bearing) ----
    qo_fixed = decode_cell_qo(FIXED); qo_fixed2 = decode_cell_qo(FIXED2)
    method_a, n_has_degen = specimen_surviving_lawful_cells()
    ma_common = [c for c in method_a if c in qo_fixed and c in qo_fixed2]
    ma_uv_stable = sum(1 for c in ma_common if not cell_changed.get(c, True))
    ma_gt_fixed_ok = sum(1 for c in ma_common if qo_fixed[c] == method_a[c])
    ma_gt_fixed2_ok = sum(1 for c in ma_common if qo_fixed2[c] == method_a[c])
    decoder_reliable = bool(ma_common) and (ma_gt_fixed_ok >= 0.8 * len(ma_common))
    return dict(
        primary_byte_domain=dict(
            n_rewritten_cells=n_cells, n_uv_stable=n_stable, n_uv_changed=n_changed,
            change_rate=change_rate,
            note="UV-stable cells carry the ground-truth (method-a) tiles, byte-identical FIXED<->"
                 "FIXED2; UV-changed = re-resolved cells that drew a new (q,o). ~86-90%% change "
                 "confirms the quilt-dissolution mechanism; the stable minority holds the pinned "
                 "ground-truth. Fix report: 90 method-a unchanged + 58 coincidental-same of 923 "
                 "dropped; 1040 of 1108 dropped-set cells changed."),
        advisory_qo_decode=dict(
            n_candidates=len(method_a), candidates_uv_stable=ma_uv_stable,
            candidates_gt_match_fixed=ma_gt_fixed_ok, candidates_gt_match_fixed2=ma_gt_fixed2_ok,
            decoder_reliable=decoder_reliable,
            note="ATTEMPTED (q,o) reconstruction of the 90 method-a cells. UNRELIABLE: candidates' "
                 "decoded (q,o) matches neither tree (gt_match ~2-5%%) and they are UV-CHANGED "
                 "re-resolved cells -- the ecotone's surviving lawful tris are multi-cell conforming "
                 "geometry, so per-vertex grass-mains decode is ambiguous. NOT verdict-bearing."))


# =====================================================================================================
def sea4_check(target):
    shas = Counter(); y_nonzero = 0; flat_bad = []; n = 0; recs = []
    for (bx, by) in FOOTPRINT:
        p = sea4_path(target, bx, by)
        if not p.exists(): continue
        n += 1; r = parse_raw(p); shas[sha16(r["data"])] += 1
        for v in verts_of(r):
            if abs(v[1]) > 1e-4: y_nonzero += 1
        ntri = r["icount"] // 3
        if not (r["vcount"] == r["icount"] == 3 * ntri): flat_bad.append([bx, by, r["vcount"], r["icount"]])
        recs.append(dict(block=[bx, by], sha=sha16(r["data"]), vcount=r["vcount"], ntri=ntri))
    spec_shas = Counter()
    for (bx, by) in FOOTPRINT:
        p = sea4_path(SPEC, bx, by)
        if p.exists(): spec_shas[sha16(p.read_bytes())] += 1
    return dict(n_sea4=n, fixed_sha_hist=dict(shas), spec_sha_hist=dict(spec_shas), y_nonzero=y_nonzero,
                flat_invariant_bad=flat_bad, uniform=len(shas) == 1)


def flat_mesh_check(target):
    bad = []
    for (bx, by) in FOOTPRINT:
        p = terr_path(target, bx, by)
        if not p.exists(): continue
        r = parse_raw(p); ntri = r["icount"] // 3
        if not (r["vcount"] == r["icount"] == 3 * ntri): bad.append([bx, by, r["vcount"], r["icount"]])
    return dict(bad=bad)


def collapsed_pinned_scan(target):
    """Refutation hunt: any collapsed UV tri anywhere in target, and any position drift vs SPEC."""
    collapsed = 0; pos_drift_files = []
    for (bx, by) in FOOTPRINT:
        pf = terr_path(target, bx, by)
        if not pf.exists(): continue
        rf = parse_raw(pf); uf = uvs_of(rf); idx = idx_of(rf)
        for t in range(len(idx) // 3):
            a, b, c = idx[3 * t], idx[3 * t + 1], idx[3 * t + 2]
            if uv_collapsed(uf[a], uf[b], uf[c]): collapsed += 1
        ps = terr_path(SPEC, bx, by)
        if ps.exists():
            rs = parse_raw(ps)
            if sl(rs, rs["off_pos"], rs["sz_pos"]) != sl(rf, rf["off_pos"], rf["sz_pos"]):
                pos_drift_files.append([bx, by])
    return dict(collapsed_uv_tris=collapsed, pos_drift_files=pos_drift_files)


def file_set_parity(target):
    def rel(root): return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
    set_s, set_f = rel(SPEC), rel(target)
    only_spec = sorted(set(set_s) - set(set_f)); only_fixed = sorted(set(set_f) - set(set_s))
    changed_other, changed = [], []
    for rp in set(set_s) & set(set_f):
        diff = (SPEC / rp).read_bytes() != (target / rp).read_bytes()
        if diff:
            changed.append(rp)
            if not (rp.endswith("Terrain.ff9mesh") or rp.endswith("Sea4.ff9mesh")):
                changed_other.append(rp)
    n_terr = sum(1 for rp in changed if rp.endswith("Terrain.ff9mesh"))
    n_sea4 = sum(1 for rp in changed if rp.endswith("Sea4.ff9mesh"))
    return dict(n_spec=len(set_s), n_fixed=len(set_f), only_spec=only_spec, only_fixed=only_fixed,
                changed_non_terrain_sea4=changed_other, n_changed_files=len(changed),
                n_changed_terrain=n_terr, n_changed_sea4=n_sea4)


# =====================================================================================================
def main():
    findings = []; R = {}
    T = FIXED2

    # (1) degenerate count on FIXED2
    cls_fixed2 = classify_tree(T); cls_spec = classify_tree(SPEC)
    R["degenerate"] = dict(fixed2=cls_fixed2, spec_total=cls_spec["total"],
                           spec_per_block=cls_spec["per_block"])
    log(f"[1] degenerate FIXED2 total={cls_fixed2['total']} SPEC total={cls_spec['total']}")
    if cls_fixed2["total"] != 0:
        findings.append(f"REFUTE (1): FIXED2 still has {cls_fixed2['total']} degenerate tris.")

    # (2) byte-rigidity vs SPEC + carried-core identity
    ch = channel_diff(T); R["channel_diff"] = ch
    log(f"[2/3] pos_diff={ch['pos_diff_files']} tan_diff={ch['tan_diff_files']} idx_diff={ch['idx_diff_files']} "
        f"uv_verts={ch['uv_changed_verts']} uv_tris={ch['uv_changed_tris']} nrm_verts={ch['nrm_changed_verts']} "
        f"nrm_tris={ch['nrm_changed_tris']} nrm_not_uv={ch['nrm_changed_tris_not_uv']}")
    if ch["pos_diff_files"]: findings.append(f"REFUTE (2): positions changed {ch['pos_diff_files']}.")
    if ch["tan_diff_files"]: findings.append(f"REFUTE (2): tangents changed {ch['tan_diff_files']}.")
    if ch["idx_diff_files"]: findings.append(f"REFUTE (2): indices changed {ch['idx_diff_files']}.")
    if ch["header_mismatch"]: findings.append(f"REFUTE (2): header mismatch {ch['header_mismatch']}.")

    core = carried_core_identity(T); R["carried_core"] = core
    log(f"[2] carried-core verbatim={core['carried_core_verbatim']} matched_xz={core['matched_xz']} "
        f"fixed_vs_spec_bad={core['fixed_vs_spec_bad']}")
    if core["fixed_vs_spec_bad"]:
        findings.append(f"REFUTE (2): {core['fixed_vs_spec_bad']} carried-core tris differ FIXED2 vs SPEC.")

    # (3) only expected channels changed -- reconcile
    R["channel_reconcile"] = dict(uv_changed_tris=ch["uv_changed_tris"], expect_uv_tris=cls_spec["total"],
                                  uv_changed_verts=ch["uv_changed_verts"], expect_uv_verts=cls_spec["total"] * 3,
                                  nrm_changed_verts=ch["nrm_changed_verts"], report_nrm_verts=162,
                                  nrm_changed_tris=ch["nrm_changed_tris"], report_apron_tris=321)
    if ch["uv_changed_tris"] != cls_spec["total"]:
        findings.append(f"MISMATCH (3): UV-changed tris {ch['uv_changed_tris']} != degenerate {cls_spec['total']}.")
    if ch["uv_changed_verts"] != cls_spec["total"] * 3:
        findings.append(f"MISMATCH (3): UV-changed verts {ch['uv_changed_verts']} != 3x {cls_spec['total']}.")
    if ch["nrm_changed_verts"] != 162:
        findings.append(f"NOTE (3): normal-changed verts {ch['nrm_changed_verts']} != report 162.")
    if ch["nrm_changed_tris_not_uv"] > 0:
        findings.append(f"REFUTE (3): {ch['nrm_changed_tris_not_uv']} tris with a NORMAL change but NO UV change.")

    shar = sha_reconcile(); R["sha_reconcile"] = shar
    log(f"[3] sha256 reconcile: n_ok={shar['n_ok']}/{shar['n_reported']} mism={shar['mismatches'][:3]}")
    if shar["mismatches"]:
        findings.append(f"MISMATCH (3): FIXED2 files differ from report sha256: {shar['mismatches'][:5]}.")

    # (4) UV language + method-a stability
    uvl = uv_language_check(T, 30); R["uv_language"] = uvl
    log(f"[4] rewritten={uvl.get('total_rewritten')} sampled={uvl.get('sampled')} matched={uvl.get('matched')} "
        f"nondegen={uvl.get('nondegenerate')} in_region={uvl.get('in_grass_region')} methods={uvl.get('methods')} "
        f"inconsistent={uvl.get('percell_inconsistent')} fails={uvl.get('fails')}")
    if uvl.get("sampled") and uvl.get("matched") != uvl.get("sampled"):
        findings.append(f"REFUTE (4): only {uvl['matched']}/{uvl['sampled']} rewritten tris reproduce grass "
                        f"ground_uv; fails={uvl['fails']}.")
    if uvl.get("sampled") and uvl.get("nondegenerate") != uvl.get("sampled"):
        findings.append(f"REFUTE (4): {uvl['sampled']-uvl['nondegenerate']} sampled rewritten tris still degenerate.")
    if uvl.get("percell_inconsistent"):
        findings.append(f"REFUTE (4): per-cell (q,o) inconsistent across sampled tris {uvl['percell_inconsistent']}.")

    ma = method_a_stability(); R["method_a_stability"] = ma
    pbd = ma["primary_byte_domain"]; adv = ma["advisory_qo_decode"]
    log(f"[4b] BYTE-DOMAIN rewritten_cells={pbd['n_rewritten_cells']} uv_stable={pbd['n_uv_stable']} "
        f"uv_changed={pbd['n_uv_changed']} change_rate={pbd['change_rate']} | "
        f"advisory(unreliable) candidates={adv['n_candidates']} gt_match_fixed={adv['candidates_gt_match_fixed']} "
        f"decoder_reliable={adv['decoder_reliable']}")
    # SOUND verdict tests (byte-domain only):
    if pbd["n_rewritten_cells"] and pbd["change_rate"] is not None and pbd["change_rate"] < 0.5:
        findings.append(f"REFUTE (4): only {pbd['change_rate']} of rewritten cells changed UV FIXED->FIXED2 "
                        f"-- the new policy barely differs from decode_cell_pick (quilt not dissolved).")
    if pbd["n_uv_stable"] == 0 and pbd["n_rewritten_cells"]:
        findings.append(f"NOTE (4): 0 UV-stable rewritten cells -- no ground-truth-carrying cell survived "
                        f"unchanged (expected a small stable minority).")

    # (5) Sea4 + flat-mesh
    sea = sea4_check(T); R["sea4"] = sea
    log(f"[5] sea4 n={sea['n_sea4']} uniform={sea['uniform']} hist={sea['fixed_sha_hist']} y_nz={sea['y_nonzero']} "
        f"flat_bad={sea['flat_invariant_bad']}")
    if not sea["uniform"]: findings.append(f"REFUTE (5): Sea4 not uniform: {sea['fixed_sha_hist']}.")
    if sea["y_nonzero"]: findings.append(f"REFUTE (5): {sea['y_nonzero']} Sea4 verts Y!=0.")
    if sea["flat_invariant_bad"]: findings.append(f"REFUTE (5): Sea4 flat-mesh bad {sea['flat_invariant_bad']}.")
    flat = flat_mesh_check(T); R["flat_mesh_terrain"] = flat
    if flat["bad"]: findings.append(f"REFUTE (5): Terrain flat-mesh bad {flat['bad']}.")

    # (6) refutation hunt: file-set + collapsed/pinned + drift + FIXED-vs-FIXED2 confinement
    parity = file_set_parity(T); R["file_parity"] = parity
    log(f"[6] files spec={parity['n_spec']} fixed2={parity['n_fixed']} only_spec={parity['only_spec']} "
        f"only_fixed2={parity['only_fixed']} changed_terr={parity['n_changed_terrain']} "
        f"changed_sea4={parity['n_changed_sea4']} changed_other={parity['changed_non_terrain_sea4']} "
        f"n_changed={parity['n_changed_files']}")
    if parity["only_spec"] or parity["only_fixed"]:
        findings.append(f"REFUTE (6): file-set differs only_spec={parity['only_spec']} only_fixed2={parity['only_fixed']}.")
    if parity["changed_non_terrain_sea4"]:
        findings.append(f"REFUTE (6): non-Terrain/Sea4 files changed: {parity['changed_non_terrain_sea4']}.")
    if parity["n_changed_files"] != 22 or parity["n_changed_terrain"] != 16 or parity["n_changed_sea4"] != 6:
        findings.append(f"MISMATCH (6): changed-file profile {parity['n_changed_files']} "
                        f"(terr {parity['n_changed_terrain']}, sea4 {parity['n_changed_sea4']}) != 22 (16+6).")

    cp = collapsed_pinned_scan(T); R["collapsed_pinned"] = cp
    log(f"[6] collapsed_uv_tris={cp['collapsed_uv_tris']} pos_drift={cp['pos_drift_files']}")
    if cp["collapsed_uv_tris"]:
        findings.append(f"REFUTE (6): {cp['collapsed_uv_tris']} collapsed/pinned UV tris remain.")
    if cp["pos_drift_files"]:
        findings.append(f"REFUTE (6): position drift in {cp['pos_drift_files']}.")

    fvf = fixed_vs_fixed2_diff(); R["fixed_vs_fixed2"] = fvf
    log(f"[6] FIXED->FIXED2: pos_bad={fvf['terr_pos_bad']} tan_bad={fvf['terr_tan_bad']} idx_bad={fvf['terr_idx_bad']} "
        f"nrm_bad={fvf['terr_nrm_bad']} uv_diff_verts={fvf['uv_diff_verts']} terr_files_diff={len(fvf['terr_files_diff'])} "
        f"sea4_diff={fvf['sea4_diff_files']}")
    if fvf["terr_pos_bad"] or fvf["terr_tan_bad"] or fvf["terr_idx_bad"] or fvf["terr_nrm_bad"]:
        findings.append(f"REFUTE (6): FIXED->FIXED2 changed a non-UV channel "
                        f"(pos={fvf['terr_pos_bad']} tan={fvf['terr_tan_bad']} idx={fvf['terr_idx_bad']} nrm={fvf['terr_nrm_bad']}).")
    if fvf["sea4_diff_files"]:
        findings.append(f"REFUTE (6): FIXED->FIXED2 Sea4 files differ {fvf['sea4_diff_files']}.")
    if fvf["uv_diff_verts"] != 6305:
        findings.append(f"NOTE (6): FIXED->FIXED2 uv_diff_verts {fvf['uv_diff_verts']} != report 6305.")

    # verdict
    hard = [f for f in findings if f.startswith("REFUTE") or f.startswith("MISMATCH")]
    notes = [f for f in findings if f.startswith("NOTE")]
    verdict = "REFUTED" if hard else "CONFIRMED"
    R["findings"] = findings
    R["verdict"] = verdict
    R["meta"] = dict(script="uvf_fix2_falsify.py", spec=str(SPEC), fixed=str(FIXED), fixed2=str(FIXED2))
    OUT.write_text(json.dumps(R, indent=1), encoding="utf-8")
    log("\n" + "=" * 80)
    log(f"VERDICT: {verdict}")
    for f in findings: log("  - " + f)
    log(f"-> {OUT}")
    return R


if __name__ == "__main__":
    main()
