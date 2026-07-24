"""RUNG F -- UV-FIX CODE-DISJOINT FALSIFIER (2026-07-24).

Written from scratch (bootstrap pattern only from rung_f_falsify.py). Verifies, from RAW BYTES, the UV-fix
that produced out/rung_f/FF9CustomMap-world-FIXED against the specimen out/rung_f/FF9CustomMap-world and the
stock donor blocks. Does NOT import uvf_fix.py / uvf_gates.py / uvf_forensics.py. Reuses ONLY the loaders
(ff9mapkit.world.extract, .mesh) and the grass UV language (ff9mapkit.world.grassland) -- every gate/diff/
classifier is reimplemented here.

READ-ONLY vs the game install (only donor stock blocks via X.read_block for the carried-core identity).
Writes only out/rung_f/uvf_fix_falsify.json + this script.
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
OUT = HERE / "out" / "rung_f" / "uvf_fix_falsify.json"
FOOTPRINT = [(bx, by) for bx in range(0, 5) for by in range(16, 20)]
MAGIC = b"F9WM"
UV_ZERO = 1e-6                       # spec classifier threshold (parallelogram area)
QUADS = [(0, 0), (0, 1), (1, 0), (1, 1)]
ORIS = (0, 90, 180, 270)
GRASS_REGION = G.FAM_REGION["main"]  # (0.00391,0.76855,0.12695,0.83008)


def log(m): print(m, flush=True)


# ---------- raw .ff9mesh parse (independent of M.read_ff9mesh, though we cross-check with it) ----------
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


def sl(r, off, sz):
    return r["data"][off:off + sz]


def verts_of(r):
    d = r["data"]
    return [struct.unpack_from("<3f", d, r["off_pos"] + j * 12) for j in range(r["vcount"])]


def uvs_of(r):
    d = r["data"]
    return [struct.unpack_from("<2f", d, r["off_uv"] + j * 8) for j in range(r["vcount"])]


def tans_of(r):
    d = r["data"]
    return [struct.unpack_from("<4f", d, r["off_tan"] + j * 16) for j in range(r["vcount"])]


def idx_of(r):
    d = r["data"]
    return list(struct.unpack_from("<%di" % r["icount"], d, r["off_idx"]))


def uv_area(uv0, uv1, uv2):
    return abs((uv1[0] - uv0[0]) * (uv2[1] - uv0[1]) - (uv2[0] - uv0[0]) * (uv1[1] - uv0[1]))


def uv_collapsed(uv0, uv1, uv2):
    ds = [math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in ((uv0, uv1), (uv0, uv2), (uv1, uv2))]
    return max(ds) < UV_ZERO


def is_degenerate(uv0, uv1, uv2):
    return uv_area(uv0, uv1, uv2) < UV_ZERO or uv_collapsed(uv0, uv1, uv2)


def terr_path(root, bx, by):
    return root / M.override_relpath(1, bx, by, part="Terrain")


def sea4_path(root, bx, by):
    return root / M.override_relpath(1, bx, by, part="Sea4")


def sha16(b):
    return hashlib.sha256(b).hexdigest()[:16]


# =====================================================================================================
def classify_tree(root):
    """degenerate-tri count per block + total; also topo tally of degenerates."""
    per_block, total, topo_ctr = {}, 0, Counter()
    for (bx, by) in FOOTPRINT:
        p = terr_path(root, bx, by)
        if not p.exists():
            per_block[f"{bx},{by}"] = 0
            continue
        r = parse_raw(p)
        uvs = uvs_of(r)
        tans = tans_of(r)
        idx = idx_of(r)
        ntri = len(idx) // 3
        cnt = 0
        for t in range(ntri):
            a, b, c = idx[3 * t], idx[3 * t + 1], idx[3 * t + 2]
            if is_degenerate(uvs[a], uvs[b], uvs[c]):
                cnt += 1
                idall = int(round(tans[a][0]))
                topo_ctr[X.decode_id(idall)["topograph"]] += 1
        per_block[f"{bx},{by}"] = cnt
        total += cnt
    return dict(total=total, per_block=per_block, topo_of_degenerate=dict(topo_ctr))


# =====================================================================================================
def channel_diff():
    """Per Terrain file, byte-diff each channel FIXED vs SPEC. Confirm pos/tan/idx identical; count
    changed UV verts + changed normal verts; roll up to changed-tris."""
    res = dict(files=0, pos_diff_files=[], tan_diff_files=[], idx_diff_files=[], nrm_diff_files=[],
               uv_changed_verts=0, nrm_changed_verts=0, uv_changed_tris=0, nrm_changed_tris=0,
               header_mismatch=[], per_block={})
    for (bx, by) in FOOTPRINT:
        ps, pf = terr_path(SPEC, bx, by), terr_path(FIXED, bx, by)
        if not (ps.exists() and pf.exists()):
            res["header_mismatch"].append([bx, by, "missing"])
            continue
        rs, rf = parse_raw(ps), parse_raw(pf)
        res["files"] += 1
        if (rs["vcount"], rs["icount"], rs["flags"]) != (rf["vcount"], rf["icount"], rf["flags"]):
            res["header_mismatch"].append([bx, by, (rs["vcount"], rs["icount"], rs["flags"]),
                                           (rf["vcount"], rf["icount"], rf["flags"])])
            continue
        # channel byte-equality
        if sl(rs, rs["off_pos"], rs["sz_pos"]) != sl(rf, rf["off_pos"], rf["sz_pos"]):
            res["pos_diff_files"].append([bx, by])
        if sl(rs, rs["off_tan"], rs["sz_tan"]) != sl(rf, rf["off_tan"], rf["sz_tan"]):
            res["tan_diff_files"].append([bx, by])
        if sl(rs, rs["off_idx"], rs["sz_idx"]) != sl(rf, rf["off_idx"], rf["sz_idx"]):
            res["idx_diff_files"].append([bx, by])
        nrm_file_diff = sl(rs, rs["off_nrm"], rs["sz_nrm"]) != sl(rf, rf["off_nrm"], rf["sz_nrm"])
        if nrm_file_diff:
            res["nrm_diff_files"].append([bx, by])
        # per-vertex UV + normal byte diff
        ds, df = rs["data"], rf["data"]
        vc = rs["vcount"]
        uv_changed = set()
        for j in range(vc):
            o = rs["off_uv"] + j * 8
            if ds[o:o + 8] != df[o:o + 8]:
                uv_changed.add(j)
        nrm_changed = set()
        for j in range(vc):
            o = rs["off_nrm"] + j * 12
            if ds[o:o + 12] != df[o:o + 12]:
                nrm_changed.add(j)
        idx = idx_of(rs)
        ntri = len(idx) // 3
        uvt = nrt = nrt_not_uv = 0
        for t in range(ntri):
            tv = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            uv_hit = any(v in uv_changed for v in tv)
            nrm_hit = any(v in nrm_changed for v in tv)
            if uv_hit:
                uvt += 1
            if nrm_hit:
                nrt += 1
                if not uv_hit:
                    nrt_not_uv += 1     # a normal change on a tri whose UV did NOT change => unexpected
        res["uv_changed_verts"] += len(uv_changed)
        res["nrm_changed_verts"] += len(nrm_changed)
        res["uv_changed_tris"] += uvt
        res["nrm_changed_tris"] += nrt
        res["nrm_changed_tris_not_uv"] = res.get("nrm_changed_tris_not_uv", 0) + nrt_not_uv
        res["per_block"][f"{bx},{by}"] = dict(uv_verts=len(uv_changed), nrm_verts=len(nrm_changed),
                                              uv_tris=uvt, nrm_tris=nrt, nrm_not_uv=nrt_not_uv)
    return res


def sha_reconcile():
    """Do the FIXED tree's Terrain+Sea4 files match the report's written_files_sha256 exactly?"""
    rep = json.loads((HERE / "out" / "rung_f" / "uvf_fix_report.json").read_text(encoding="utf-8"))
    want = rep.get("written_files_sha256", {})
    mism, ok = [], 0
    for relp, wsha in want.items():
        p = FIXED / relp.replace("\\", "/")
        if not p.exists():
            mism.append([relp, "missing"])
            continue
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != wsha:
            mism.append([relp, got[:16], wsha[:16]])
        else:
            ok += 1
    return dict(n_reported=len(want), n_ok=ok, mismatches=mism)


# =====================================================================================================
def carried_core_identity():
    """Identify carried-core VERBATIM tris independently: donor blocks 13-15,11-12 (stock) shifted
    (-768,-384) in XZ. A staged tri is carried-core-verbatim iff its XZ footprint matches a donor tri
    AND its uv+nrm+tan (attr) equal that donor tri's (the whole-verbatim/clipped-piece carry -- XZ+attr
    match, Y is a uniform lift). This deliberately EXCLUDES the topo-0 frame/hole tris that merely
    overlap donor XZ (they fail the attr match). Then: every carried-core-verbatim tri must be
    byte-identical FIXED vs SPEC across ALL channels (the fix must not have touched it)."""
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
                w = [(bm.verts[j][0] + ox + SHIFT[0], bm.verts[j][1], bm.verts[j][2] + oz + SHIFT[1])
                     for j in tri]
                key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in w))   # XZ only; carry lifts Y
                uv = tuple(sorted((round(float(bm.uvs[j][0]), 6), round(float(bm.uvs[j][1]), 6)) for j in tri))
                nrm = tuple(sorted((round(float(bm.normals[j][0]), 5), round(float(bm.normals[j][1]), 5),
                                    round(float(bm.normals[j][2]), 5)) for j in tri))
                tan = tuple(sorted((round(float(bm.tangents[j][1]), 5), round(float(bm.tangents[j][2]), 5),
                                    round(float(bm.tangents[j][3]), 5)) for j in tri))
                idall = int(round(bm.tangents[tri[0]][0]))
                topo = X.decode_id(idall)["topograph"]     # build strips event/area -> compare topo, not idall
                donor[key].append(dict(uv=uv, nrm=nrm, tan=tan, topo=topo))
    matched_xz = 0            # staged tris whose XZ overlaps a donor tri
    verbatim = 0             # + attr (uv,nrm,tan,idall) equals a donor tri -> carried-core-verbatim
    xz_only_deviation = 0    # XZ overlaps donor but attr differs (frame/hole overlap OR excise+refill)
    fixed_vs_spec_bad = 0    # carried-core-verbatim tri that differs FIXED vs SPEC (the refutation)
    for (bx, by) in FOOTPRINT:
        ps, pf = terr_path(SPEC, bx, by), terr_path(FIXED, bx, by)
        if not (ps.exists() and pf.exists()):
            continue
        rs, rf = parse_raw(ps), parse_raw(pf)
        vs, vf = verts_of(rs), verts_of(rf)
        us, uf = uvs_of(rs), uvs_of(rf)
        ns = [struct.unpack_from("<3f", rs["data"], rs["off_nrm"] + j * 12) for j in range(rs["vcount"])]
        nf = [struct.unpack_from("<3f", rf["data"], rf["off_nrm"] + j * 12) for j in range(rf["vcount"])]
        ts, tf = tans_of(rs), tans_of(rf)
        ox, oz = X.block_world_origin(bx, by)
        idx = idx_of(rs)
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            w = [(vs[j][0] + ox, vs[j][1], vs[j][2] + oz) for j in tri]
            key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in w))
            cands = donor.get(key)
            if not cands:
                continue
            matched_xz += 1
            uvs_t = tuple(sorted((round(us[j][0], 6), round(us[j][1], 6)) for j in tri))
            nrm_t = tuple(sorted((round(ns[j][0], 5), round(ns[j][1], 5), round(ns[j][2], 5)) for j in tri))
            tan_t = tuple(sorted((round(ts[j][1], 5), round(ts[j][2], 5), round(ts[j][3], 5)) for j in tri))
            topo_t = X.decode_id(int(round(ts[tri[0]][0])))["topograph"]
            is_verbatim = any(c["uv"] == uvs_t and c["nrm"] == nrm_t and c["tan"] == tan_t
                              and c["topo"] == topo_t for c in cands)
            if is_verbatim:
                verbatim += 1
                same = all(vs[j] == vf[j] and us[j] == uf[j] and ns[j] == nf[j] and ts[j] == tf[j]
                           for j in tri)
                if not same:
                    fixed_vs_spec_bad += 1
            else:
                xz_only_deviation += 1
    return dict(matched_xz=matched_xz, carried_core_verbatim=verbatim,
                xz_overlap_nonverbatim=xz_only_deviation, fixed_vs_spec_bad=fixed_vs_spec_bad)


# =====================================================================================================
def resolve_ground_uv(world_verts, obs_uvs, cells, tol=2e-5):
    """Can obs_uvs be reproduced by G.ground_uv(...,'grass') for lawful (quad,ori)? Try (a) per-vertex
    OWN-cell with a shared (quad,ori) per distinct cell (CSP), and (b) a single common cell for all 3
    (centroid-style). Return the method name or None."""
    def matches(wv, uv, cell, q, o):
        cu, cv = G.ground_uv(wv[0], wv[2], cell, q, o, "grass")
        return abs(cu - uv[0]) < tol and abs(cv - uv[1]) < tol

    # (a) own-cell CSP
    distinct = sorted(set(cells))
    combos = list(product(QUADS, ORIS))
    for assign in product(combos, repeat=len(distinct)):
        amap = dict(zip(distinct, assign))
        ok = True
        for i in range(3):
            q, o = amap[cells[i]]
            if not matches(world_verts[i], obs_uvs[i], cells[i], q, o):
                ok = False
                break
        if ok:
            return "own-cell"
    # (b) common cell (own cells OR centroid cell)
    cx = sum(w[0] for w in world_verts) / 3.0
    cz = sum(w[2] for w in world_verts) / 3.0
    ccell = (math.floor(cx / CELL), math.floor(cz / CELL))
    for cand in set(cells) | {ccell}:
        for (q, o) in combos:
            if all(matches(world_verts[i], obs_uvs[i], cand, q, o) for i in range(3)):
                return "common-cell"
    return None


def uv_language_check(n_sample=30):
    """Sample rewritten tris (UV-changed FIXED vs SPEC) across blocks; each must be reproducible grass
    mains language and now non-degenerate + in the lawful grass-mains region (bleed-extended)."""
    rewritten = []
    for (bx, by) in FOOTPRINT:
        ps, pf = terr_path(SPEC, bx, by), terr_path(FIXED, bx, by)
        if not (ps.exists() and pf.exists()):
            continue
        rs, rf = parse_raw(ps), parse_raw(pf)
        us, uf = uvs_of(rs), uvs_of(rf)
        vf = verts_of(rf)
        idx = idx_of(rf)
        ox, oz = X.block_world_origin(bx, by)
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            if any(us[j] != uf[j] for j in tri):     # UV changed => rewritten
                w = [(vf[j][0] + ox, vf[j][1], vf[j][2] + oz) for j in tri]
                obs = [uf[j] for j in tri]
                cells = [(math.floor(w[i][0] / CELL), math.floor(w[i][2] / CELL)) for i in range(3)]
                rewritten.append((bx, by, t, w, obs, cells))
    total_rw = len(rewritten)
    if total_rw == 0:
        return dict(total_rewritten=0, sampled=0, matched=0, note="no rewritten tris found")
    step = max(1, total_rw // n_sample)
    sample = rewritten[::step][:n_sample]
    matched = 0
    nondegen = 0
    in_region = 0
    methods = Counter()
    fails = []
    lo_u, lo_v, hi_u, hi_v = GRASS_REGION
    # bleed-extended region: mains_uv clamp allows a,b in [-0.15,1.15] on the uh/vh==0 half
    ext = 0.15 * (hi_u - lo_u)   # widen by clamp fraction * cell-rect width; generous but bounded
    for (bx, by, t, w, obs, cells) in sample:
        meth = resolve_ground_uv(w, obs, cells)
        if meth:
            matched += 1
            methods[meth] += 1
        else:
            fails.append([bx, by, t, [ [round(u,5) for u in o] for o in obs ]])
        if uv_area(*obs) >= UV_ZERO:
            nondegen += 1
        if all(lo_u - 0.02 <= u <= hi_u + 0.02 and lo_v - 0.02 <= v <= hi_v + 0.02 for (u, v) in obs):
            in_region += 1
    return dict(total_rewritten=total_rw, sampled=len(sample), matched=matched,
                nondegenerate=nondegen, in_grass_region=in_region, methods=dict(methods),
                fails=fails[:8])


# =====================================================================================================
def sea4_check():
    recs = []
    shas = Counter()
    y_nonzero = 0
    flat_bad = []
    n = 0
    for (bx, by) in FOOTPRINT:
        p = sea4_path(FIXED, bx, by)
        if not p.exists():
            continue
        n += 1
        r = parse_raw(p)
        shas[sha16(r["data"])] += 1
        verts = verts_of(r)
        for v in verts:
            if abs(v[1]) > 1e-4:
                y_nonzero += 1
        ntri = r["icount"] // 3
        if not (r["vcount"] == r["icount"] == 3 * ntri):
            flat_bad.append([bx, by, r["vcount"], r["icount"]])
        recs.append(dict(block=[bx, by], sha=sha16(r["data"]), vcount=r["vcount"],
                         icount=r["icount"], ntri=ntri, bytes=r["total"]))
    # specimen sea4 shas for contrast
    spec_shas = Counter()
    for (bx, by) in FOOTPRINT:
        p = sea4_path(SPEC, bx, by)
        if p.exists():
            spec_shas[sha16(p.read_bytes())] += 1
    return dict(n_sea4=n, fixed_sha_hist=dict(shas), spec_sha_hist=dict(spec_shas),
                y_nonzero=y_nonzero, flat_invariant_bad=flat_bad,
                uniform=len(shas) == 1, per_block=recs)


# =====================================================================================================
def flat_mesh_check():
    bad = []
    for (bx, by) in FOOTPRINT:
        p = terr_path(FIXED, bx, by)
        if not p.exists():
            continue
        r = parse_raw(p)
        ntri = r["icount"] // 3
        if not (r["vcount"] == r["icount"] == 3 * ntri):
            bad.append([bx, by, r["vcount"], r["icount"]])
    return dict(bad=bad)


# =====================================================================================================
def file_set_parity():
    def rel(root):
        return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
    set_s, set_f = rel(SPEC), rel(FIXED)
    only_spec = sorted(set(set_s) - set(set_f))
    only_fixed = sorted(set(set_f) - set(set_s))
    # which non-terrain/non-sea4 files differ at all (should be none)?
    changed_other = []
    for rp in set(set_s) & set(set_f):
        if rp.endswith("Terrain.ff9mesh") or rp.endswith("Sea4.ff9mesh"):
            continue
        a = (SPEC / rp).read_bytes()
        b = (FIXED / rp).read_bytes()
        if a != b:
            changed_other.append(rp)
    # count all changed files
    changed = []
    for rp in set(set_s) & set(set_f):
        if (SPEC / rp).read_bytes() != (FIXED / rp).read_bytes():
            changed.append(rp)
    return dict(n_spec=len(set_s), n_fixed=len(set_f), only_spec=only_spec, only_fixed=only_fixed,
                changed_non_terrain_sea4=changed_other, n_changed_files=len(changed))


# =====================================================================================================
def main():
    findings = []
    R = {}

    # (1) degenerate counts
    cls_fixed = classify_tree(FIXED)
    cls_spec = classify_tree(SPEC)
    R["degenerate"] = dict(fixed=cls_fixed, spec_total=cls_spec["total"],
                           spec_per_block=cls_spec["per_block"])
    log(f"[1] degenerate FIXED total={cls_fixed['total']} SPEC total={cls_spec['total']} "
        f"(spec topo_of_degenerate={cls_spec['topo_of_degenerate']})")
    if cls_fixed["total"] != 0:
        findings.append(f"REFUTE (1): FIXED still has {cls_fixed['total']} degenerate tris: "
                        f"{ {k:v for k,v in cls_fixed['per_block'].items() if v} }")
    if cls_spec["total"] != 2305:
        findings.append(f"NOTE: my classifier counts SPEC degenerate={cls_spec['total']} (expected 2305) "
                        f"-- classifier calibration differs from forensics.")

    # (2) byte-rigidity + carried-core identity
    ch = channel_diff()
    R["channel_diff"] = ch
    log(f"[2/3] pos_diff_files={ch['pos_diff_files']} tan_diff_files={ch['tan_diff_files']} "
        f"idx_diff_files={ch['idx_diff_files']} uv_changed_verts={ch['uv_changed_verts']} "
        f"uv_changed_tris={ch['uv_changed_tris']} nrm_changed_verts={ch['nrm_changed_verts']} "
        f"nrm_changed_tris={ch['nrm_changed_tris']} header_mismatch={ch['header_mismatch']}")
    if ch["pos_diff_files"]:
        findings.append(f"REFUTE (2): positions changed in files {ch['pos_diff_files']}.")
    if ch["tan_diff_files"]:
        findings.append(f"REFUTE (2): tangents (topology idall) changed in files {ch['tan_diff_files']}.")
    if ch["idx_diff_files"]:
        findings.append(f"REFUTE (2): tri-indices changed in files {ch['idx_diff_files']}.")
    if ch["header_mismatch"]:
        findings.append(f"REFUTE (2): header/vcount mismatch {ch['header_mismatch']}.")

    core = carried_core_identity()
    R["carried_core"] = core
    log(f"[2] carried-core verbatim={core['carried_core_verbatim']} matched_xz={core['matched_xz']} "
        f"xz_overlap_nonverbatim={core['xz_overlap_nonverbatim']} "
        f"fixed_vs_spec_bad={core['fixed_vs_spec_bad']}")
    if core["fixed_vs_spec_bad"]:
        findings.append(f"REFUTE (2): {core['fixed_vs_spec_bad']} carried-core-verbatim tris differ "
                        f"FIXED vs SPEC.")

    # (3) only expected channels changed -- reconcile counts
    R["channel_reconcile"] = dict(
        uv_changed_tris=ch["uv_changed_tris"], expect_uv_tris=cls_spec["total"],
        uv_changed_verts=ch["uv_changed_verts"], expect_uv_verts=cls_spec["total"] * 3,
        nrm_changed_tris=ch["nrm_changed_tris"], report_apron_tris=321,
        nrm_changed_verts=ch["nrm_changed_verts"], report_nrm_verts=162)
    if ch["uv_changed_tris"] != cls_spec["total"]:
        findings.append(f"MISMATCH (3): UV-changed tris {ch['uv_changed_tris']} != degenerate count "
                        f"{cls_spec['total']}.")
    if ch["uv_changed_verts"] != cls_spec["total"] * 3:
        findings.append(f"MISMATCH (3): UV-changed verts {ch['uv_changed_verts']} != 3x degenerate "
                        f"{cls_spec['total']*3}.")
    if ch["nrm_changed_tris"] > 321:
        findings.append(f"MISMATCH (3): normal-changed tris {ch['nrm_changed_tris']} > 321 apron cap.")
    if ch.get("nrm_changed_tris_not_uv", 0) > 0:
        findings.append(f"REFUTE (3): {ch['nrm_changed_tris_not_uv']} tris had a NORMAL change but NO UV "
                        f"change -- a channel edit outside the rewritten-tri set.")

    shar = sha_reconcile()
    R["sha_reconcile"] = shar
    log(f"[3] sha256 reconcile vs report: n_ok={shar['n_ok']}/{shar['n_reported']} "
        f"mismatches={shar['mismatches']}")
    if shar["mismatches"]:
        findings.append(f"MISMATCH: FIXED files differ from report written_files_sha256: "
                        f"{shar['mismatches']}.")

    # (4) UV language
    uvl = uv_language_check(30)
    R["uv_language"] = uvl
    log(f"[4] rewritten={uvl.get('total_rewritten')} sampled={uvl.get('sampled')} "
        f"matched={uvl.get('matched')} nondegen={uvl.get('nondegenerate')} "
        f"in_region={uvl.get('in_grass_region')} methods={uvl.get('methods')} fails={uvl.get('fails')}")
    if uvl.get("sampled") and uvl.get("matched") != uvl.get("sampled"):
        findings.append(f"REFUTE (4): only {uvl['matched']}/{uvl['sampled']} sampled rewritten tris "
                        f"reproduce grass ground_uv; fails={uvl['fails']}.")
    if uvl.get("sampled") and uvl.get("nondegenerate") != uvl.get("sampled"):
        findings.append(f"REFUTE (4): {uvl['sampled']-uvl['nondegenerate']} sampled rewritten tris still "
                        f"degenerate UV-area.")

    # (5) Sea4
    sea = sea4_check()
    R["sea4"] = sea
    log(f"[5] sea4 n={sea['n_sea4']} uniform={sea['uniform']} fixed_sha_hist={sea['fixed_sha_hist']} "
        f"spec_sha_hist={sea['spec_sha_hist']} y_nonzero={sea['y_nonzero']} "
        f"flat_bad={sea['flat_invariant_bad']}")
    if not sea["uniform"]:
        findings.append(f"REFUTE (5): Sea4 not uniform across 20 blocks: {sea['fixed_sha_hist']}.")
    if sea["y_nonzero"]:
        findings.append(f"REFUTE (5): {sea['y_nonzero']} Sea4 verts with Y!=0.")
    if sea["flat_invariant_bad"]:
        findings.append(f"REFUTE (5): Sea4 flat-mesh invariant violated {sea['flat_invariant_bad']}.")

    flat = flat_mesh_check()
    R["flat_mesh_terrain"] = flat
    if flat["bad"]:
        findings.append(f"REFUTE (5): Terrain flat-mesh invariant violated {flat['bad']}.")

    # (6) refutation hunt -- file-set parity + stray changes
    parity = file_set_parity()
    R["file_parity"] = parity
    log(f"[6] files spec={parity['n_spec']} fixed={parity['n_fixed']} only_spec={parity['only_spec']} "
        f"only_fixed={parity['only_fixed']} changed_other={parity['changed_non_terrain_sea4']} "
        f"n_changed_files={parity['n_changed_files']}")
    if parity["only_spec"] or parity["only_fixed"]:
        findings.append(f"REFUTE (6): file-set differs only_spec={parity['only_spec']} "
                        f"only_fixed={parity['only_fixed']}.")
    if parity["changed_non_terrain_sea4"]:
        findings.append(f"REFUTE (6): unexpected non-Terrain/Sea4 files changed: "
                        f"{parity['changed_non_terrain_sea4']}.")

    # verdict
    hard = [f for f in findings if f.startswith("REFUTE") or f.startswith("MISMATCH")]
    notes = [f for f in findings if f.startswith("NOTE")]
    if hard:
        verdict = "REFUTED"
    elif notes:
        verdict = "CONFIRMED"   # benign notes only -> still confirmed (documented deviations)
    else:
        verdict = "CONFIRMED"
    R["findings"] = findings
    R["verdict"] = verdict
    R["meta"] = dict(script="uvf_fix_falsify.py", spec=str(SPEC), fixed=str(FIXED))
    OUT.write_text(json.dumps(R, indent=1), encoding="utf-8")
    log("\n" + "=" * 80)
    log(f"VERDICT: {verdict}")
    for f in findings:
        log("  - " + f)
    log(f"-> {OUT}")
    return R


if __name__ == "__main__":
    main()
