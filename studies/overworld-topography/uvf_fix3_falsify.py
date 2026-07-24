"""RUNG F -- UV-FIX v3 (FIXED3A) CODE-DISJOINT FALSIFIER (2026-07-24).

Round-3 verifier for the ONE-WINDOW-PER-TRI fix. Extends MY OWN falsifier lineage
(uvf_fix_falsify.py -> uvf_fix2_falsify.py). Does NOT import uvf_fix3.py / uvf_fix2.py /
uvf_gates*.py / uvf_forensics.py. Reuses ONLY the loaders (ff9mapkit.world.extract, .mesh) +
the grass UV language (grassland.ground_uv). Every gate/diff/classifier reimplemented here.

Central NEW claim tested independently from raw bytes: every rewritten (formerly-degenerate) tri's
3 UVs reconstruct from a SINGLE (cell,quad,ori) grass window -- the cross-window barycentric sweep
that produced the eye's streaking in FIXED2 is gone. My window derivation is my own: search a generous
candidate-cell set (3 per-vertex cells + centroid cell + centroid Moore ring) x 4 quads x 4 oris and
demand ONE (cell,q,o) reproducing all three verts via G.ground_uv (which itself carries the inward
bleed clamp). A genuinely cross-window tri cannot pass for ANY candidate, so candidate generosity is
safe -- it only helps find a legit single window.

READ-ONLY vs the game install. Writes only out/rung_f/uvf_fix3_falsify.json + this script.
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
RUNG = HERE / "out" / "rung_f"
SPEC = RUNG / "FF9CustomMap-world"
FIXED = RUNG / "FF9CustomMap-world-FIXED"
FIXED2 = RUNG / "FF9CustomMap-world-FIXED2"
FIXED3A = RUNG / "FF9CustomMap-world-FIXED3A"
OUT = RUNG / "uvf_fix3_falsify.json"
FOOTPRINT = [(bx, by) for bx in range(0, 5) for by in range(16, 20)]
MAGIC = b"F9WM"
UV_ZERO = 1e-6
QUADS = [(0, 0), (0, 1), (1, 0), (1, 1)]
ORIS = (0, 90, 180, 270)
GRASS_REGION = G.FAM_REGION["main"]
WIN_TOL = 2e-5          # grass window reconstruction tolerance (float32 storage ~6e-9 quant)


def log(m): print(m, flush=True)


# ---------- raw .ff9mesh parse (MY code) ----------
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
def nrms_of(r):
    d = r["data"]; return [struct.unpack_from("<3f", d, r["off_nrm"] + j * 12) for j in range(r["vcount"])]
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
# (1) degenerate count -- own classifier
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
# (2)+(4) channel byte-diff vs SPEC (Terrain only)
def channel_diff(target):
    res = dict(files=0, pos_diff_files=[], tan_diff_files=[], idx_diff_files=[], nrm_diff_files=[],
               uv_changed_verts=0, nrm_changed_verts=0, uv_changed_tris=0, nrm_changed_tris=0,
               nrm_changed_tris_not_uv=0, header_mismatch=[], uv_changed_tri_ids=[], per_block={})
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
        idx = idx_of(rs); uvt = nrt = nrt_not_uv = 0; tri_ids = []
        for t in range(len(idx) // 3):
            tv = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            uv_hit = any(v in uv_changed for v in tv)
            nrm_hit = any(v in nrm_changed for v in tv)
            if uv_hit: uvt += 1; tri_ids.append(t)
            if nrm_hit:
                nrt += 1
                if not uv_hit: nrt_not_uv += 1
        res["uv_changed_verts"] += len(uv_changed); res["nrm_changed_verts"] += len(nrm_changed)
        res["uv_changed_tris"] += uvt; res["nrm_changed_tris"] += nrt
        res["nrm_changed_tris_not_uv"] += nrt_not_uv
        res["per_block"][f"{bx},{by}"] = dict(uv_verts=len(uv_changed), nrm_verts=len(nrm_changed),
                                              uv_tris=uvt, nrm_tris=nrt, nrm_not_uv=nrt_not_uv)
    return res


# =====================================================================================================
# (2) carried-core identity via donor byte-match (MY re-identification)
def carried_core_identity(target):
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
        ns, nf = nrms_of(rs), nrms_of(rf); ts, tf = tans_of(rs), tans_of(rf)
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
# (3) ONE-WINDOW coherence -- MY OWN derivation from grassland.ground_uv
def _candidate_cells(w):
    """Generous candidate-cell set: 3 per-vertex floor cells + centroid + centroid Moore ring."""
    cells = set()
    for i in range(3):
        cells.add((math.floor(w[i][0] / CELL), math.floor(w[i][2] / CELL)))
    cx = sum(p[0] for p in w) / 3.0; cz = sum(p[2] for p in w) / 3.0
    cc = (math.floor(cx / CELL), math.floor(cz / CELL))
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            cells.add((cc[0] + di, cc[1] + dj))
    return cells


def _single_window(w, obs, tol=WIN_TOL):
    """Return (cell,quad,ori,max_resid) if ONE grass window reproduces all 3 UVs; else None."""
    best = None
    for cell in _candidate_cells(w):
        for (q, o) in product(QUADS, ORIS):
            resid = 0.0; ok = True
            for i in range(3):
                cu, cv = G.ground_uv(w[i][0], w[i][2], cell, q, o, "grass")
                d = max(abs(cu - obs[i][0]), abs(cv - obs[i][1]))
                if d >= tol:
                    ok = False; break
                resid = max(resid, d)
            if ok:
                if best is None or resid < best[3]:
                    best = (cell, q, o, resid)
    return best


def _rewritten_tris(target):
    """List of (bx,by,t,w[3],obs[3]) for tris whose UV differs SPEC->target."""
    out = []
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
                out.append((bx, by, t, w, obs))
    return out


def window_coherence(target):
    rw = _rewritten_tris(target)
    n = len(rw); single = 0; multi = []
    excursions = []; resids = []
    lo_u, lo_v, hi_u, hi_v = GRASS_REGION
    out_region = 0; collapsed = 0
    for (bx, by, t, w, obs) in rw:
        # excursion = max pairwise UV distance (barycentric sweep length)
        exc = max(math.hypot(obs[a][0] - obs[b][0], obs[a][1] - obs[b][1])
                  for a, b in ((0, 1), (0, 2), (1, 2)))
        excursions.append(exc)
        if uv_collapsed(*obs): collapsed += 1
        if not all(lo_u - 0.02 <= u <= hi_u + 0.02 and lo_v - 0.02 <= v <= hi_v + 0.02 for (u, v) in obs):
            out_region += 1
        win = _single_window(w, obs)
        if win is not None:
            single += 1; resids.append(win[3])
        else:
            multi.append([bx, by, t, [[round(u, 6) for u in o] for o in obs]])
    excursions.sort()
    def pct(a, p): return round(a[min(len(a) - 1, int(p * len(a)))], 6) if a else None
    return dict(n_rewritten=n, single_window=single, multi_window=len(multi),
                pct_single=round(100.0 * single / n, 3) if n else None,
                excursion_p50=pct(excursions, 0.50), excursion_p90=pct(excursions, 0.90),
                excursion_max=round(excursions[-1], 6) if excursions else None,
                match_resid_max=round(max(resids), 8) if resids else None,
                collapsed_uv=collapsed, out_of_grass_region=out_region,
                multi_window_examples=multi[:10])


def window_sample_lawful(target, n_sample=30):
    """(3) sample 30 rewritten tris; each must reproduce from a lawful grass (quad,ori) window."""
    rw = _rewritten_tris(target)
    if not rw: return dict(sampled=0, matched=0)
    step = max(1, len(rw) // n_sample)
    sample = rw[::step][:n_sample]
    matched = 0; qo_hist = Counter(); fails = []; resid_max = 0.0
    for (bx, by, t, w, obs) in sample:
        win = _single_window(w, obs)
        if win is not None:
            matched += 1; qo_hist[str((win[1], win[2]))] += 1; resid_max = max(resid_max, win[3])
        else:
            fails.append([bx, by, t])
    return dict(sampled=len(sample), matched=matched, resid_max=round(resid_max, 8),
                quad_ori_hist=dict(qo_hist), fails=fails)


# =====================================================================================================
# (4)+(6) diff FIXED2 -> FIXED3A: UV-ONLY, confined to the rewritten 2305
def fixed2_vs_fixed3a():
    res = dict(terr_pos_bad=0, terr_tan_bad=0, terr_idx_bad=0, terr_nrm_bad=0,
               uv_diff_verts=0, uv_diff_in_rewritten=0, uv_diff_outside_rewritten=0,
               terr_files_diff=[], sea4_diff_files=[], missing=[])
    for (bx, by) in FOOTPRINT:
        ps = terr_path(SPEC, bx, by)
        pa, pb = terr_path(FIXED2, bx, by), terr_path(FIXED3A, bx, by)
        if not (ps.exists() and pa.exists() and pb.exists()):
            res["missing"].append([bx, by, "terr"]); continue
        rs, ra, rb = parse_raw(ps), parse_raw(pa), parse_raw(pb)
        if sl(ra, ra["off_pos"], ra["sz_pos"]) != sl(rb, rb["off_pos"], rb["sz_pos"]): res["terr_pos_bad"] += 1
        if sl(ra, ra["off_tan"], ra["sz_tan"]) != sl(rb, rb["off_tan"], rb["sz_tan"]): res["terr_tan_bad"] += 1
        if sl(ra, ra["off_idx"], ra["sz_idx"]) != sl(rb, rb["off_idx"], rb["sz_idx"]): res["terr_idx_bad"] += 1
        if sl(ra, ra["off_nrm"], ra["sz_nrm"]) != sl(rb, rb["off_nrm"], rb["sz_nrm"]): res["terr_nrm_bad"] += 1
        # rewritten verts = those whose UV differs SPEC vs FIXED3A (the 2305-tri vert set)
        ds, db = rs["data"], rb["data"]; da = ra["data"]; idx = idx_of(rs)
        spec_diff_verts = {j for j in range(rs["vcount"])
                           if ds[rs["off_uv"] + j * 8: rs["off_uv"] + j * 8 + 8]
                           != db[rb["off_uv"] + j * 8: rb["off_uv"] + j * 8 + 8]}
        rewritten_vids = set()
        us, ub = uvs_of(rs), uvs_of(rb)
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            if any(us[j] != ub[j] for j in tri):
                rewritten_vids.update(tri)
        for j in range(ra["vcount"]):
            if da[ra["off_uv"] + j * 8: ra["off_uv"] + j * 8 + 8] != db[rb["off_uv"] + j * 8: rb["off_uv"] + j * 8 + 8]:
                res["uv_diff_verts"] += 1
                if j in rewritten_vids: res["uv_diff_in_rewritten"] += 1
                else: res["uv_diff_outside_rewritten"] += 1
        if ra["data"] != rb["data"]: res["terr_files_diff"].append([bx, by])
    for (bx, by) in FOOTPRINT:
        pa, pb = sea4_path(FIXED2, bx, by), sea4_path(FIXED3A, bx, by)
        if not (pa.exists() and pb.exists()): continue
        if pa.read_bytes() != pb.read_bytes(): res["sea4_diff_files"].append([bx, by])
    return res


# =====================================================================================================
# (5) Sea4 uniform + flat mesh
def sea4_check(target):
    shas = Counter(); y_nonzero = 0; flat_bad = []; n = 0
    for (bx, by) in FOOTPRINT:
        p = sea4_path(target, bx, by)
        if not p.exists(): continue
        n += 1; r = parse_raw(p); shas[sha16(r["data"])] += 1
        for v in verts_of(r):
            if abs(v[1]) > 1e-4: y_nonzero += 1
        ntri = r["icount"] // 3
        if not (r["vcount"] == r["icount"] == 3 * ntri): flat_bad.append([bx, by, r["vcount"], r["icount"]])
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


# =====================================================================================================
# (6) refutation hunt: collapsed/pinned, position drift, file-set drift
def collapsed_pinned_scan(target):
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
        if (SPEC / rp).read_bytes() != (target / rp).read_bytes():
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
    T = FIXED3A

    # (1) degenerate = 0
    cls = classify_tree(T); cls_spec = classify_tree(SPEC)
    R["degenerate"] = dict(fixed3a=cls, spec_total=cls_spec["total"], spec_per_block=cls_spec["per_block"])
    log(f"[1] degenerate FIXED3A={cls['total']} SPEC={cls_spec['total']}")
    if cls["total"] != 0:
        findings.append(f"REFUTE (1): FIXED3A still has {cls['total']} degenerate tris.")

    # (2) rigidity vs SPEC + carried-core donor byte-match
    ch = channel_diff(T); R["channel_diff"] = {k: v for k, v in ch.items() if k != "uv_changed_tri_ids"}
    log(f"[2/4] pos_diff={ch['pos_diff_files']} tan_diff={ch['tan_diff_files']} idx_diff={ch['idx_diff_files']} "
        f"nrm_diff_files={ch['nrm_diff_files']} uv_verts={ch['uv_changed_verts']} uv_tris={ch['uv_changed_tris']} "
        f"nrm_verts={ch['nrm_changed_verts']} nrm_not_uv={ch['nrm_changed_tris_not_uv']}")
    if ch["pos_diff_files"]: findings.append(f"REFUTE (2): positions changed vs SPEC {ch['pos_diff_files']}.")
    if ch["tan_diff_files"]: findings.append(f"REFUTE (2): tangents changed vs SPEC {ch['tan_diff_files']}.")
    if ch["idx_diff_files"]: findings.append(f"REFUTE (2): indices changed vs SPEC {ch['idx_diff_files']}.")
    if ch["header_mismatch"]: findings.append(f"REFUTE (2): header mismatch {ch['header_mismatch']}.")

    core = carried_core_identity(T); R["carried_core"] = core
    log(f"[2] carried-core verbatim={core['carried_core_verbatim']} matched_xz={core['matched_xz']} "
        f"fixed_vs_spec_bad={core['fixed_vs_spec_bad']}")
    if core["fixed_vs_spec_bad"]:
        findings.append(f"REFUTE (2): {core['fixed_vs_spec_bad']} carried-core tris differ FIXED3A vs SPEC.")
    if core["carried_core_verbatim"] == 0:
        findings.append("NOTE (2): 0 carried-core verbatim tris matched (donor re-identification empty).")

    # (2/4) UV changes confined to the degenerate (2305) tris
    R["uv_confinement"] = dict(uv_changed_tris=ch["uv_changed_tris"], spec_degenerate=cls_spec["total"],
                               uv_changed_verts=ch["uv_changed_verts"],
                               nrm_changed_verts=ch["nrm_changed_verts"])
    if ch["uv_changed_tris"] != cls_spec["total"]:
        findings.append(f"REFUTE (4): UV-changed tris {ch['uv_changed_tris']} != degenerate {cls_spec['total']} "
                        f"(UV not confined to the 2305).")
    if ch["nrm_changed_verts"] != 162:
        findings.append(f"NOTE (2): normal-changed verts vs SPEC {ch['nrm_changed_verts']} != report 162 (apron).")
    if ch["nrm_changed_tris_not_uv"] > 0:
        findings.append(f"NOTE (2): {ch['nrm_changed_tris_not_uv']} apron-normal tris with no UV change "
                        f"(nrm changed outside the rewritten set -- allowed by 'apron normals' clause, flagged).")

    # (3) ONE-WINDOW coherence (the central new claim) -- FIXED3A vs FIXED2
    wc3 = window_coherence(T); R["window_coherence_fixed3a"] = wc3
    log(f"[3] FIXED3A window coherence: n={wc3['n_rewritten']} single={wc3['single_window']} "
        f"multi={wc3['multi_window']} pct_single={wc3['pct_single']} resid_max={wc3['match_resid_max']} "
        f"exc(p50/p90/max)={wc3['excursion_p50']}/{wc3['excursion_p90']}/{wc3['excursion_max']} "
        f"collapsed={wc3['collapsed_uv']} out_region={wc3['out_of_grass_region']}")
    wc2 = window_coherence(FIXED2); R["window_coherence_fixed2"] = wc2
    log(f"[3] FIXED2 window coherence (control): n={wc2['n_rewritten']} single={wc2['single_window']} "
        f"multi={wc2['multi_window']} pct_single={wc2['pct_single']} "
        f"exc(p50/p90/max)={wc2['excursion_p50']}/{wc2['excursion_p90']}/{wc2['excursion_max']}")
    smp = window_sample_lawful(T, 30); R["window_sample_30"] = smp
    log(f"[3] 30-sample lawful: sampled={smp['sampled']} matched={smp['matched']} resid_max={smp.get('resid_max')} "
        f"qo_hist={smp.get('quad_ori_hist')} fails={smp.get('fails')}")
    # verdict tests
    if wc3["n_rewritten"] != cls_spec["total"]:
        findings.append(f"NOTE (3): rewritten count {wc3['n_rewritten']} != degenerate {cls_spec['total']}.")
    if wc3["multi_window"] > 1:
        findings.append(f"REFUTE (3): {wc3['multi_window']} rewritten tris are CROSS-WINDOW (>1 documented "
                        f"per-vertex last-resort sliver): {wc3['multi_window_examples'][:5]}.")
    if wc3["collapsed_uv"] > 0:
        findings.append(f"REFUTE (3): {wc3['collapsed_uv']} rewritten tris have collapsed/pinned UV.")
    if wc3["out_of_grass_region"] > 0:
        findings.append(f"REFUTE (3): {wc3['out_of_grass_region']} rewritten tris fall outside the grass mains region.")
    if wc3["excursion_max"] is not None and wc3["excursion_max"] > 0.10:
        findings.append(f"REFUTE (3): max UV excursion {wc3['excursion_max']} > 0.10 (a lawful tri stays ~<=0.089, "
                        f"one window scale 0.06769) -- cross-window sweep persists.")
    if smp["sampled"] and smp["matched"] != smp["sampled"]:
        findings.append(f"REFUTE (3): only {smp['matched']}/{smp['sampled']} sampled tris reproduce a lawful "
                        f"grass (quad,ori); fails={smp['fails']}.")
    # improvement sanity: FIXED3A must be strictly better than FIXED2
    if wc2["n_rewritten"] and wc3["single_window"] <= wc2["single_window"]:
        findings.append(f"REFUTE (3): FIXED3A single-window {wc3['single_window']} not > FIXED2 "
                        f"{wc2['single_window']} -- the fix did not improve coherence.")

    # (4) diff FIXED2 -> FIXED3A: UV-only, confined to the 2305
    fvf = fixed2_vs_fixed3a(); R["fixed2_vs_fixed3a"] = fvf
    log(f"[4] FIXED2->FIXED3A: pos_bad={fvf['terr_pos_bad']} tan_bad={fvf['terr_tan_bad']} idx_bad={fvf['terr_idx_bad']} "
        f"nrm_bad={fvf['terr_nrm_bad']} uv_diff_verts={fvf['uv_diff_verts']} in_rewritten={fvf['uv_diff_in_rewritten']} "
        f"outside={fvf['uv_diff_outside_rewritten']} terr_files_diff={len(fvf['terr_files_diff'])} "
        f"sea4_diff={fvf['sea4_diff_files']}")
    if fvf["terr_pos_bad"] or fvf["terr_tan_bad"] or fvf["terr_idx_bad"] or fvf["terr_nrm_bad"]:
        findings.append(f"REFUTE (4): FIXED2->FIXED3A changed a non-UV channel "
                        f"(pos={fvf['terr_pos_bad']} tan={fvf['terr_tan_bad']} idx={fvf['terr_idx_bad']} nrm={fvf['terr_nrm_bad']}).")
    if fvf["uv_diff_outside_rewritten"] > 0:
        findings.append(f"REFUTE (4): {fvf['uv_diff_outside_rewritten']} FIXED2->FIXED3A UV changes fall OUTSIDE "
                        f"the rewritten 2305-tri vert set.")
    if fvf["sea4_diff_files"]:
        findings.append(f"REFUTE (4): FIXED2->FIXED3A Sea4 files differ {fvf['sea4_diff_files']}.")
    if fvf["uv_diff_verts"] != 4437:
        findings.append(f"NOTE (4): FIXED2->FIXED3A uv_diff_verts {fvf['uv_diff_verts']} != report 4437.")

    # (5) Sea4 uniform + flat mesh
    sea = sea4_check(T); R["sea4"] = sea
    log(f"[5] sea4 n={sea['n_sea4']} uniform={sea['uniform']} hist={sea['fixed_sha_hist']} y_nz={sea['y_nonzero']} "
        f"flat_bad={sea['flat_invariant_bad']}")
    if not sea["uniform"]: findings.append(f"REFUTE (5): Sea4 not uniform: {sea['fixed_sha_hist']}.")
    if sea["y_nonzero"]: findings.append(f"REFUTE (5): {sea['y_nonzero']} Sea4 verts Y!=0.")
    if sea["flat_invariant_bad"]: findings.append(f"REFUTE (5): Sea4 flat-mesh bad {sea['flat_invariant_bad']}.")
    flat = flat_mesh_check(T); R["flat_mesh_terrain"] = flat
    if flat["bad"]: findings.append(f"REFUTE (5): Terrain flat-mesh bad {flat['bad']}.")

    # (6) refutation hunt
    cp = collapsed_pinned_scan(T); R["collapsed_pinned"] = cp
    log(f"[6] collapsed_uv_tris={cp['collapsed_uv_tris']} pos_drift={cp['pos_drift_files']}")
    if cp["collapsed_uv_tris"]:
        findings.append(f"REFUTE (6): {cp['collapsed_uv_tris']} collapsed/pinned UV tris remain.")
    if cp["pos_drift_files"]:
        findings.append(f"REFUTE (6): position drift vs SPEC in {cp['pos_drift_files']}.")

    parity = file_set_parity(T); R["file_parity"] = parity
    log(f"[6] files spec={parity['n_spec']} fixed3a={parity['n_fixed']} only_spec={parity['only_spec']} "
        f"only_fixed3a={parity['only_fixed']} changed_terr={parity['n_changed_terrain']} "
        f"changed_sea4={parity['n_changed_sea4']} changed_other={parity['changed_non_terrain_sea4']} "
        f"n_changed={parity['n_changed_files']}")
    if parity["only_spec"] or parity["only_fixed"]:
        findings.append(f"REFUTE (6): file-set differs only_spec={parity['only_spec']} only_fixed3a={parity['only_fixed']}.")
    if parity["changed_non_terrain_sea4"]:
        findings.append(f"REFUTE (6): non-Terrain/Sea4 files changed: {parity['changed_non_terrain_sea4']}.")
    if parity["n_changed_files"] != 22 or parity["n_changed_terrain"] != 16 or parity["n_changed_sea4"] != 6:
        findings.append(f"MISMATCH (6): changed-file profile {parity['n_changed_files']} "
                        f"(terr {parity['n_changed_terrain']}, sea4 {parity['n_changed_sea4']}) != 22 (16+6).")

    # verdict
    hard = [f for f in findings if f.startswith("REFUTE") or f.startswith("MISMATCH")]
    notes = [f for f in findings if f.startswith("NOTE")]
    verdict = "REFUTED" if hard else "CONFIRMED"
    R["findings"] = findings
    R["notes"] = notes
    R["verdict"] = verdict
    R["meta"] = dict(script="uvf_fix3_falsify.py", spec=str(SPEC), fixed2=str(FIXED2), fixed3a=str(FIXED3A),
                     win_tol=WIN_TOL)
    OUT.write_text(json.dumps(R, indent=1), encoding="utf-8")
    log("\n" + "=" * 80)
    log(f"VERDICT: {verdict}")
    for f in findings: log("  - " + f)
    log(f"-> {OUT}")
    return R


if __name__ == "__main__":
    main()
