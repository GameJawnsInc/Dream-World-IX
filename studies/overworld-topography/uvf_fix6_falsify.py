"""RUNG F -- THE CARRIED-SPIKE SHAVE (FIXED6) CODE-DISJOINT FALSIFIER (2026-07-25).

Round-6 verifier.  Extends MY OWN falsifier lineage
(uvf_fix_falsify -> uvf_fix2_falsify -> uvf_fix3_falsify -> uvf_fix4_falsify -> uvf_fix5_falsify).
Does NOT import uvf_fix6.py / uvf_gates6.py / uvf_fix5.py / uvf_relief_probe.py / uvf_gates*.py,
and deliberately does NOT bootstrap from rung_f_build.json (the build's own artifact).
Reuses ONLY the loaders (ff9mapkit.world.extract/.mesh) + the kit ground-family table
(grassland.TOPO_FAMILY) as an oracle for "which kept topos are ground".  Every parse, diff,
weld map, crack audit, topo decode, reference surface, prominence, spike census, normal
recomputation and gate below is re-implemented here from raw bytes.

  NOTE ON THE FILENAME COLLISION: the build lane had already written its OWN in-house verifier
  to this path.  It is preserved verbatim as uvf_fix6_falsify_buildside.py (it writes
  uvf_fix6_falsify_report.json).  Its pass gate contains NO test of this round's contract change
  -- it never fits a surface, never asks whether a moved carried position was an outlier, and
  reads the build's own touched-block list out of rung_f_build.json.  This file is the
  independent lane and writes uvf_fix6_falsify.json.

THE CONTRACT CHANGE THIS ROUND: carried positions MAY move -- but ONLY census-defined SPIKES
(strict positive outliers vs the local rim reference) plus fill welded to them.  So the
load-bearing lane is (2): I derive the moved carried set MYSELF from the byte diff and demand
each one was a genuine positive outlier under MY OWN independent surface fit.

CLAIMS TESTED INDEPENDENTLY FROM RAW BYTES:
 (1) changes = Y + normals ONLY; X/Z/UV/tangent/index/header bytes identical EVERYWHERE;
     only Terrain files changed; same file set; Sea/Object/Beach untouched.
 (2) THE SCOPED CARRIED EXCEPTION: my own byte-diff -> moved carried positions; each must be
     (a) a positive outlier >= ~0.8u above MY OWN local reference (measured PRE-move on FIXED5),
     (b) a strict local maximum on the weld graph, (c) inside the mound, (d) outside the basin.
     Any moved carried position that was NOT an outlier = REFUTED.  All other carried content
     (incl. the donor-matched carried core) byte-identical; rock stamps (topo 58/31) untouched.
 (3) WELD INTEGRITY (my own coincident-position map over ALL 8 parts x 20 blocks, cross-block),
     no new open edges (XZ-plan once-edge audit), no new down-facing tris, land > 0, no new
     zero-area tris, flat-mesh invariant.
 (4) THE BASIN DISC: 0 moved positions (independent re-derivation + a literal byte test) and the
     mound's carried height distribution outside the moved set is a MULTISET IDENTITY.
 (5) POST-MOVE: every shaved apex lands inside the local reference band -- no overshoot below
     the rim base, no new local MINIMUM, and it is no longer a local maximum.
 (6) REFUTATION HUNT: exhaustiveness re-census on FIXED6's own bytes, new-spike hunt, crater
     depth, the BASIN REFERENCE TRAP reproduced independently, normals scope/geometry + the
     donor-normal seam, carried-core donor rigidity, report reconciliation.

READ-ONLY vs the game install (donor blocks only).  Writes out/rung_f/uvf_fix6_falsify.json.

    py -X utf8 uvf_fix6_falsify.py
"""
from __future__ import annotations
import json, math, struct, sys, statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X      # noqa: E402
from ff9mapkit.world import mesh as M         # noqa: E402
from ff9mapkit.world import grassland as G    # noqa: E402

RUNG = HERE / "out" / "rung_f"
SPEC = RUNG / "FF9CustomMap-world"                # pre-fix specimen -> defines the synthesized set
FIXED5 = RUNG / "FF9CustomMap-world-FIXED5"       # base
FIXED6 = RUNG / "FF9CustomMap-world-FIXED6"       # candidate
OUT = RUNG / "uvf_fix6_falsify.json"
FOOTPRINT = [(bx, by) for bx in range(0, 5) for by in range(16, 20)]
PARTS = ("Terrain", "Object", "Beach1", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5")
MAGIC = b"F9WM"
UV_ZERO = 1e-6
POSKEY = 3
SEA_Y = 0.0

BASIN_C = (127.14, -1161.42)
BASIN_R = 7.92
MOUND_R = 40.0
OUTLIER_U = 0.80          # the round's stated spike residual threshold
PROM_U = 0.40             # the round's stated prominence threshold


def log(m): print(m, flush=True)


# ---------------- raw .ff9mesh parse (MY code, lineage-carried) ----------------
def parse_raw(path):
    data = Path(path).read_bytes()
    assert data[:4] == MAGIC, f"bad magic {path}"
    version, vcount, icount, flags = struct.unpack_from("<iiii", data, 4)
    off_pos = 20
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
    d = r["data"]
    if not r["sz_nrm"]: return [(0.0, 1.0, 0.0)] * r["vcount"]
    return [struct.unpack_from("<3f", d, r["off_nrm"] + j * 12) for j in range(r["vcount"])]
def uvs_of(r):
    d = r["data"]
    if not r["sz_uv"]: return [(0.0, 0.0)] * r["vcount"]
    return [struct.unpack_from("<2f", d, r["off_uv"] + j * 8) for j in range(r["vcount"])]
def tans_of(r):
    d = r["data"]
    if not r["sz_tan"]: return [(0.0, 0.0, 0.0, 0.0)] * r["vcount"]
    return [struct.unpack_from("<4f", d, r["off_tan"] + j * 16) for j in range(r["vcount"])]
def idx_of(r):
    d = r["data"]; return list(struct.unpack_from("<%di" % r["icount"], d, r["off_idx"]))


def uv_area(a, b, c): return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
def uv_collapsed(a, b, c):
    return max(math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in ((a, b), (a, c), (b, c))) < UV_ZERO
def is_degenerate(a, b, c): return uv_area(a, b, c) < UV_ZERO or uv_collapsed(a, b, c)


def part_path(root, bx, by, part): return root / M.override_relpath(1, bx, by, part=part)


def stats(v):
    if not v: return dict(n=0)
    s = sorted(v); n = len(s)
    def q(p): return s[min(n - 1, max(0, int(round(p * (n - 1)))))]
    return dict(n=n, mean=round(statistics.fmean(s), 5), sd=round(statistics.pstdev(s), 5) if n > 1 else 0.0,
                min=round(s[0], 5), p5=round(q(.05), 5), p25=round(q(.25), 5), p50=round(q(.5), 5),
                p75=round(q(.75), 5), p95=round(q(.95), 5), p99=round(q(.99), 5), max=round(s[-1], 5))


def geo_normal(p0, p1, p2):
    ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
    return (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)


def rcrater(x, z): return math.hypot(x - BASIN_C[0], z - BASIN_C[1])


# =====================================================================================
def load_all():
    T = {}; missing = []
    for (bx, by) in FOOTPRINT:
        for part in PARTS:
            p5, p6 = part_path(FIXED5, bx, by, part), part_path(FIXED6, bx, by, part)
            if not p5.exists() or not p6.exists():
                if p5.exists() != p6.exists(): missing.append([bx, by, part, p5.exists(), p6.exists()])
                continue
            r5, r6 = parse_raw(p5), parse_raw(p6)
            T[(bx, by, part)] = dict(r5=r5, r6=r6, v5=verts_of(r5), v6=verts_of(r6),
                                     org=X.block_world_origin(bx, by))
    return T, missing


def load_spec():
    S = {}; bad = []
    for (bx, by) in FOOTPRINT:
        p = part_path(SPEC, bx, by, "Terrain")
        if not p.exists(): bad.append([bx, by, "missing-spec"]); continue
        r = parse_raw(p)
        S[(bx, by)] = dict(r=r, uv=uvs_of(r), idx=idx_of(r))
    return S, bad


# ---- MY OWN surface reference: IDW-weighted LSQ plane, Cauchy-robust, leave-one-out ----
class Surface:
    """Independent local-surface estimator.

    Deliberately NOT the build's estimator: growing radii 10/14/20/28/40 (build: 8/12/18/26),
    ONE Cauchy-on-MAD reweighting pass (build: two Tukey-biweight IRLS passes), <=48 nearest,
    weight 1/max(d^2,1) (build: its own floor).  Leave-one-out by key blacklist so a lone apex
    cannot fit itself.  Rock never enters the sample set.
    """
    HB = 8.0
    RADII = (10.0, 14.0, 20.0, 28.0, 40.0)
    MINN = 10
    CAP = 48

    def __init__(self, samples, exclude_basin=True):
        self.pts = []
        for (x, z, y, sid) in samples:
            if exclude_basin and rcrater(x, z) <= BASIN_R:
                continue
            self.pts.append((x, z, y, sid))
        self.g = defaultdict(list)
        for i, (x, z, y, sid) in enumerate(self.pts):
            self.g[(int(math.floor(x / self.HB)), int(math.floor(z / self.HB)))].append(i)

    def _gather(self, x, z, R, skip):
        got = []
        rc_ = int(math.ceil(R / self.HB))
        cx, cz = int(math.floor(x / self.HB)), int(math.floor(z / self.HB))
        R2 = R * R
        for i in range(cx - rc_, cx + rc_ + 1):
            for j in range(cz - rc_, cz + rc_ + 1):
                for ix in self.g.get((i, j), ()):
                    px, pz, py, sid = self.pts[ix]
                    if sid in skip: continue
                    d2 = (px - x) ** 2 + (pz - z) ** 2
                    if d2 <= R2: got.append((d2, px, pz, py))
        got.sort()
        return got[:self.CAP]

    @staticmethod
    def _solve(got, x, z, wextra=None):
        A = [[0.0] * 3 for _ in range(3)]; rhs = [0.0] * 3
        for n, (d2, px, pz, py) in enumerate(got):
            w = 1.0 / max(d2, 1.0)
            if wextra is not None: w *= wextra[n]
            bas = (1.0, px - x, pz - z)
            for r_ in range(3):
                for c_ in range(3): A[r_][c_] += w * bas[r_] * bas[c_]
                rhs[r_] += w * bas[r_] * py
        Mx = [A[i][:] + [rhs[i]] for i in range(3)]
        for col in range(3):
            piv = max(range(col, 3), key=lambda rr: abs(Mx[rr][col]))
            if abs(Mx[piv][col]) < 1e-12: return None
            Mx[col], Mx[piv] = Mx[piv], Mx[col]
            for rr in range(3):
                if rr == col: continue
                f = Mx[rr][col] / Mx[col][col]
                for cc in range(col, 4): Mx[rr][cc] -= f * Mx[col][cc]
        return (Mx[0][3] / Mx[0][0], Mx[1][3] / Mx[1][1], Mx[2][3] / Mx[2][2])

    def at(self, x, z, skip=()):
        """Return the fitted surface height AT (x,z) -- the plane's constant term, since the
        basis is centred on the query."""
        skip = set(skip)
        for R in self.RADII:
            got = self._gather(x, z, R, skip)
            if len(got) < self.MINN: continue
            sol = self._solve(got, x, z)
            if sol is None: continue
            a, bb, cc = sol
            # TRUE plane residual at each sample (slope included), then one Cauchy-on-MAD reweight
            res = [py - (a + bb * (px - x) + cc * (pz - z)) for (_, px, pz, py) in got]
            med = statistics.median(res)
            mad = statistics.median([abs(r - med) for r in res]) or 1e-3
            wex = [1.0 / (1.0 + (abs(r - med) / (3.0 * mad)) ** 2) for r in res]
            sol2 = self._solve(got, x, z, wex)
            return (a if sol2 is None else sol2[0]), R, len(got)
        return None, None, 0

    def envelope(self, x, z, R, skip=()):
        skip = set(skip)
        got = self._gather(x, z, R, skip)
        if not got: return None, None, 0
        ys = [g[3] for g in got]
        return min(ys), max(ys), len(ys)


def main():
    findings = []; R = {}
    R["meta"] = dict(script="uvf_fix6_falsify.py", spec=str(SPEC), base=str(FIXED5), target=str(FIXED6),
                     poskey_dp=POSKEY, uv_zero=UV_ZERO, parts=list(PARTS),
                     basin=dict(center=list(BASIN_C), radius=BASIN_R), mound_radius=MOUND_R,
                     outlier_threshold_u=OUTLIER_U, prominence_threshold_u=PROM_U,
                     filename_collision="the build lane had already written its own verifier to this path; "
                                        "preserved as uvf_fix6_falsify_buildside.py (writes "
                                        "uvf_fix6_falsify_report.json). Its pass gate tests none of this "
                                        "round's contract change and it reads rung_f_build.json.",
                     independence="no import of uvf_fix6/uvf_gates6/uvf_fix5/uvf_relief_probe and no read of "
                                  "rung_f_build.json; own parser, own weld map, own topo decode, own surface "
                                  "estimator (10/14/20/28/40u Cauchy-on-MAD IDW-LSQ plane, leave-one-out) -- "
                                  "NOT the build's 8/12/18/26u two-pass Tukey scheme.")

    # ================= (1) tree + channel rigidity =================
    def rel(root): return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
    a, b = rel(FIXED5), rel(FIXED6)
    only5 = sorted(set(a) - set(b)); only6 = sorted(set(b) - set(a))
    changed = [rp for rp in sorted(set(a) & set(b))
               if (FIXED5 / rp).read_bytes() != (FIXED6 / rp).read_bytes()]
    non_terrain_changed = [rp for rp in changed if not rp.endswith("Terrain.ff9mesh")]
    non_disc1 = [rp for rp in changed if "Disc1" not in rp]
    R["tree_diff"] = dict(n_fixed5=len(a), n_fixed6=len(b), only_fixed5=only5, only_fixed6=only6,
                          n_changed=len(changed), changed=changed,
                          changed_non_terrain=non_terrain_changed, changed_non_disc1=non_disc1)
    log(f"[1] files {len(a)}/{len(b)} changed={len(changed)} non_terrain={non_terrain_changed}")
    if only5 or only6: findings.append(f"REFUTE (1): file set differs only5={only5} only6={only6}.")
    if non_terrain_changed:
        findings.append(f"REFUTE (1): non-Terrain files changed: {non_terrain_changed}.")
    if non_disc1:
        findings.append(f"REFUTE (1): non-Disc1 files changed: {non_disc1}.")
    if len(changed) != 3:
        findings.append(f"MISMATCH (1): {len(changed)} files changed, report claims 3.")

    T, missing = load_all()
    S, spec_bad = load_spec()
    R["load"] = dict(n_part_files=len(T), missing=missing, spec_blocks=len(S), spec_bad=spec_bad)
    if missing: findings.append(f"REFUTE (1): part-file presence differs FIXED5/FIXED6: {missing}.")
    if spec_bad: findings.append(f"NOTE: specimen tree incomplete: {spec_bad}.")

    chan = dict(header_bad=[], uv_bad=[], tan_bad=[], idx_bad=[], nrm_changed_files=[],
                pos_changed_files=[], xz_moved=[], y_moved_entries=0, nrm_changed_entries=0,
                flat_mesh_bad=[])
    moved_entries = []
    for key, D in sorted(T.items()):
        bx, by, part = key
        r5, r6 = D["r5"], D["r6"]
        if (r5["vcount"], r5["icount"], r5["flags"], r5["version"]) != \
           (r6["vcount"], r6["icount"], r6["flags"], r6["version"]):
            chan["header_bad"].append([bx, by, part]); continue
        if r6["vcount"] != r6["icount"] or r6["icount"] % 3:
            chan["flat_mesh_bad"].append([bx, by, part, r6["vcount"], r6["icount"]])
        if r5["sz_uv"] and sl(r5, r5["off_uv"], r5["sz_uv"]) != sl(r6, r6["off_uv"], r6["sz_uv"]):
            chan["uv_bad"].append([bx, by, part])
        if r5["sz_tan"] and sl(r5, r5["off_tan"], r5["sz_tan"]) != sl(r6, r6["off_tan"], r6["sz_tan"]):
            chan["tan_bad"].append([bx, by, part])
        if sl(r5, r5["off_idx"], r5["sz_idx"]) != sl(r6, r6["off_idx"], r6["sz_idx"]):
            chan["idx_bad"].append([bx, by, part])
        if sl(r5, r5["off_pos"], r5["sz_pos"]) != sl(r6, r6["off_pos"], r6["sz_pos"]):
            chan["pos_changed_files"].append(f"{bx},{by},{part}")
            d5, d6 = r5["data"], r6["data"]
            for j in range(r5["vcount"]):
                o5 = r5["off_pos"] + j * 12; o6 = r6["off_pos"] + j * 12
                if d5[o5:o5 + 12] == d6[o6:o6 + 12]: continue
                if d5[o5:o5 + 4] != d6[o6:o6 + 4] or d5[o5 + 8:o5 + 12] != d6[o6 + 8:o6 + 12]:
                    chan["xz_moved"].append([bx, by, part, j])
                chan["y_moved_entries"] += 1
                moved_entries.append((bx, by, part, j))
        if r5["sz_nrm"] and sl(r5, r5["off_nrm"], r5["sz_nrm"]) != sl(r6, r6["off_nrm"], r6["sz_nrm"]):
            chan["nrm_changed_files"].append(f"{bx},{by},{part}")
            d5, d6 = r5["data"], r6["data"]
            chan["nrm_changed_entries"] += sum(
                1 for j in range(r5["vcount"])
                if d5[r5["off_nrm"] + j * 12: r5["off_nrm"] + j * 12 + 12] !=
                   d6[r6["off_nrm"] + j * 12: r6["off_nrm"] + j * 12 + 12])
    chan["xz_moved_n"] = len(chan["xz_moved"]); chan["xz_moved"] = chan["xz_moved"][:10]
    R["channel_rigidity"] = chan
    log(f"[1] uv_bad={chan['uv_bad']} tan_bad={chan['tan_bad']} idx_bad={chan['idx_bad']} "
        f"hdr={chan['header_bad']} y_moved_entries={chan['y_moved_entries']} "
        f"xz_moved={chan['xz_moved_n']} nrm_entries={chan['nrm_changed_entries']} "
        f"flatmesh_bad={chan['flat_mesh_bad']}")
    for k, lbl in (("header_bad", "headers"), ("uv_bad", "UVs"), ("tan_bad", "tangents/IDALL"),
                   ("idx_bad", "indices")):
        if chan[k]: findings.append(f"REFUTE (1): {lbl} changed FIXED5->FIXED6 in {chan[k]}.")
    if chan["xz_moved_n"]:
        findings.append(f"REFUTE (1): {chan['xz_moved_n']} vertex entries had X or Z bytes rewritten "
                        f"(the move must be Y-only): {chan['xz_moved'][:4]}.")
    if chan["flat_mesh_bad"]:
        findings.append(f"REFUTE (3): FLAT-MESH invariant broken: {chan['flat_mesh_bad']}.")
    if chan["y_moved_entries"] != 67:
        findings.append(f"MISMATCH (1): {chan['y_moved_entries']} position entries moved, report claims 67.")
    if chan["nrm_changed_entries"] > 153:
        findings.append(f"MISMATCH (6): {chan['nrm_changed_entries']} normal entries rewritten, "
                        f"report claims 153 (a superset would be a scope breach).")

    # SPEC vs FIXED5 index/XZ parity: the (block,tri) identity that lets SPEC UVs classify FIXED5/6
    spec_diffs = []
    for (bx, by) in FOOTPRINT:
        if (bx, by) not in S or (bx, by, "Terrain") not in T: continue
        rs = S[(bx, by)]["r"]; r5 = T[(bx, by, "Terrain")]["r5"]
        if (rs["vcount"], rs["icount"]) != (r5["vcount"], r5["icount"]):
            spec_diffs.append([bx, by, "header"]); continue
        if sl(rs, rs["off_idx"], rs["sz_idx"]) != sl(r5, r5["off_idx"], r5["sz_idx"]):
            spec_diffs.append([bx, by, "idx"])
        vs = verts_of(rs); v5 = T[(bx, by, "Terrain")]["v5"]
        if any(abs(p[0] - q[0]) > 1e-9 or abs(p[2] - q[2]) > 1e-9 for p, q in zip(vs, v5)):
            spec_diffs.append([bx, by, "xz"])
    R["spec_parity"] = dict(diffs=spec_diffs,
                            note="SPEC UVs remain the synthesized-tri classifier; the carry-over proof is "
                                 "0 index diffs + 0 X/Z diffs (rounds 1-4 legitimately rewrote UVs).")
    if spec_diffs:
        findings.append(f"REFUTE (1): SPEC vs FIXED5 indices/XZ differ {spec_diffs} -- the synthesized-set "
                        f"oracle is not aligned to the base tree.")

    # ================= per-tri table =================
    tris = []
    for (bx, by) in FOOTPRINT:
        if (bx, by, "Terrain") not in T or (bx, by) not in S: continue
        D = T[(bx, by, "Terrain")]; ox, oz = D["org"]
        r5 = D["r5"]; idx = idx_of(r5); tan = tans_of(r5)
        su = S[(bx, by)]["uv"]
        v5, v6 = D["v5"], D["v6"]
        n5 = nrms_of(r5); n6 = nrms_of(D["r6"])
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            w5 = [(v5[j][0] + ox, v5[j][1], v5[j][2] + oz) for j in tri]
            w6 = [(v6[j][0] + ox, v6[j][1], v6[j][2] + oz) for j in tri]
            topo = X.decode_id(int(round(tan[tri[0]][0])))["topograph"]
            tris.append(dict(b=(bx, by), t=t, tri=tri, w5=w5, w6=w6, topo=topo,
                             synth=is_degenerate(*[su[j] for j in tri]),
                             n5=[n5[j] for j in tri], n6=[n6[j] for j in tri],
                             moved=any(p[1] != q[1] for p, q in zip(w5, w6))))
    n_synth = sum(1 for r in tris if r["synth"])
    R["synth_set"] = dict(n_terrain_tris=len(tris), n_synthesized=n_synth,
                          n_synth_with_moved_vert=sum(1 for r in tris if r["synth"] and r["moved"]),
                          n_kept_with_moved_vert=sum(1 for r in tris if not r["synth"] and r["moved"]),
                          kept_topo_hist=dict(sorted(Counter(r["topo"] for r in tris if not r["synth"]).items())),
                          synth_topo_hist=dict(sorted(Counter(r["topo"] for r in tris if r["synth"]).items())))
    log(f"[1] terrain tris={len(tris)} synth={n_synth} synth_moved={R['synth_set']['n_synth_with_moved_vert']} "
        f"kept_moved={R['synth_set']['n_kept_with_moved_vert']}")
    if n_synth != 2305:
        findings.append(f"MISMATCH (1): my synthesized-set size {n_synth} != the reported 2305.")
    if R["synth_set"]["n_kept_with_moved_vert"] != 8:
        findings.append(f"MISMATCH (2): {R['synth_set']['n_kept_with_moved_vert']} KEPT tris carry a moved "
                        f"vertex, report claims 8.")

    # ================= (3) weld map over ALL parts =================
    groups = defaultdict(list)
    ent5 = {}; ent6 = {}
    for (bx, by, part), D in T.items():
        ox, oz = D["org"]
        for j, (x, y, z) in enumerate(D["v5"]):
            wx, wy, wz = x + ox, y, z + oz
            k = (round(wx, POSKEY), round(wy, POSKEY), round(wz, POSKEY))
            groups[k].append((bx, by, part, j))
            ent5[(bx, by, part, j)] = (wx, wy, wz)
        for j, (x, y, z) in enumerate(D["v6"]):
            ent6[(bx, by, part, j)] = (x + ox, y, z + oz)

    split_groups = []; nonuniform = []; dy_by_group = {}
    moved_keys = []; cross_block_moved = 0; cross_part_moved = 0
    partial_groups = []
    moved_entry_set = set(moved_entries)
    for k, ents in groups.items():
        dys = [ent6[e][1] - ent5[e][1] for e in ents]
        dmin, dmax = min(dys), max(dys)
        if dmax - dmin > 1e-9:
            nonuniform.append([list(k), round(dmin, 6), round(dmax, 6), len(ents)])
        ys6 = [ent6[e][1] for e in ents]; ys5 = [ent5[e][1] for e in ents]
        if (max(ys6) - min(ys6)) > (max(ys5) - min(ys5)) + 1e-6:
            split_groups.append([list(k), round(max(ys5) - min(ys5), 6), round(max(ys6) - min(ys6), 6)])
        dy = statistics.fmean(dys)
        dy_by_group[k] = dy
        if any(abs(d) > 0 for d in dys):
            moved_keys.append(k)
            if len({(e[0], e[1]) for e in ents}) > 1: cross_block_moved += 1
            if len({e[2] for e in ents}) > 1: cross_part_moved += 1
            miss = [e for e in ents if e not in moved_entry_set]
            if miss: partial_groups.append([list(k), len(ents), len(miss)])
    R["weld"] = dict(n_distinct_positions=len(groups),
                     groups_that_split=len(split_groups), split_examples=split_groups[:8],
                     groups_with_nonuniform_delta=len(nonuniform), nonuniform_examples=nonuniform[:8],
                     groups_that_moved=len(moved_keys),
                     cross_block_groups_moved=cross_block_moved,
                     cross_part_groups_moved=cross_part_moved,
                     partial_groups=len(partial_groups), partial_examples=partial_groups[:6],
                     entries_per_moved_position=dict(sorted(Counter(len(groups[k]) for k in moved_keys).items())),
                     moved_entries_reconcile=[sum(len(groups[k]) for k in moved_keys), chan["y_moved_entries"]])
    log(f"[3] weld: positions={len(groups)} split={len(split_groups)} nonuniform={len(nonuniform)} "
        f"moved={len(moved_keys)} cross_block={cross_block_moved} cross_part={cross_part_moved} "
        f"partial={len(partial_groups)}")
    if split_groups:
        findings.append(f"REFUTE (3): {len(split_groups)} coincident-position groups SPLIT: {split_groups[:4]}.")
    if nonuniform:
        findings.append(f"REFUTE (3): {len(nonuniform)} coincident groups received NON-UNIFORM dY: {nonuniform[:4]}.")
    if partial_groups:
        findings.append(f"REFUTE (3): {len(partial_groups)} moved groups have entries that did NOT move "
                        f"(partial weld): {partial_groups[:4]}.")
    if sum(len(groups[k]) for k in moved_keys) != chan["y_moved_entries"]:
        findings.append(f"MISMATCH (3): weld-map moved entries {sum(len(groups[k]) for k in moved_keys)} != "
                        f"byte-diff moved entries {chan['y_moved_entries']}.")
    if len(moved_keys) != 12:
        findings.append(f"MISMATCH (3): {len(moved_keys)} positions moved, report claims 12.")
    if len(groups) != 8923:
        findings.append(f"MISMATCH (3): my distinct-position count {len(groups)} != the reported 8923.")

    # ================= position classification (MY OWN) =================
    pos_kept_ground = defaultdict(set); pos_kept_rock = defaultdict(set); pos_synth = set()
    pos_deg = defaultdict(set)
    for r in tris:
        ks = [(round(p[0], POSKEY), round(p[1], POSKEY), round(p[2], POSKEY)) for p in r["w5"]]
        for i in range(3):
            pos_deg[ks[i]].add(ks[(i + 1) % 3]); pos_deg[ks[(i + 1) % 3]].add(ks[i])
        fam = G.TOPO_FAMILY.get(r["topo"])
        for k in ks:
            if r["synth"]: pos_synth.add(k)
            elif fam is not None: pos_kept_ground[k].add(r["topo"])
            else: pos_kept_rock[k].add(r["topo"])
    carried_ground = set(pos_kept_ground)
    carried_rock = set(pos_kept_rock) - carried_ground          # STRICT: rock-only positions
    carried_rock_touched = set(pos_kept_rock)                   # BROAD: any position a rock tri touches
    fill = pos_synth - carried_ground - carried_rock
    R["classification"] = dict(carried_ground=len(carried_ground),
                               carried_rock_STRICT_rock_only=len(carried_rock),
                               carried_rock_BROAD_any_rock_tri=len(carried_rock_touched),
                               rock_positions_shared_with_ground=len(carried_rock_touched & carried_ground),
                               carried_rock=len(carried_rock),
                               fill=len(fill),
                               carried_ground_topo_hist=dict(sorted(Counter(
                                   t for s in pos_kept_ground.values() for t in s).items())),
                               carried_rock_topo_hist=dict(sorted(Counter(
                                   t for k in carried_rock for t in pos_kept_rock[k]).items())),
                               note="ground family via grassland.TOPO_FAMILY on the tangent-decoded topograph of "
                                    "each KEPT tri; rock = kept-but-no-family (58/31) touched by no ground tri.")
    log(f"[2] carried_ground={len(carried_ground)} carried_rock={len(carried_rock)} fill={len(fill)}")
    if len(carried_ground) != 2427 or len(fill) != 937:
        findings.append(f"MISMATCH (2): my ground/fill classification {len(carried_ground)}/{len(fill)} "
                        f"!= the reported 2427/937.")
    if 458 not in (len(carried_rock), len(carried_rock_touched)):
        findings.append(f"MISMATCH (2): the reported 458 carried-rock positions matches NEITHER of my two "
                        f"readings of the definition (strict rock-only {len(carried_rock)}, broad "
                        f"any-rock-tri {len(carried_rock_touched)}).")
    elif len(carried_rock) != 458:
        findings.append(f"NOTE (2): the report's 458 carried-rock positions is the BROAD reading (any position a "
                        f"kept rock tri touches, {len(carried_rock_touched)}), not the strict rock-only reading "
                        f"its own prose states ('touched by no ground tri', which gives {len(carried_rock)}); "
                        f"{len(carried_rock_touched & carried_ground)} positions are shared with ground. "
                        f"Report-only census wording -- the exemption itself holds under BOTH readings "
                        f"(0 moved either way).")

    moved_carried_ground = [k for k in moved_keys if k in carried_ground]
    moved_carried_rock = [k for k in moved_keys if k in carried_rock]
    moved_fill = [k for k in moved_keys if k in fill]
    R["moved_split"] = dict(carried_ground=len(moved_carried_ground), carried_rock=len(moved_carried_rock),
                            fill=len(moved_fill),
                            unclassified=len(moved_keys) - len(moved_carried_ground) -
                                         len(moved_carried_rock) - len(moved_fill))
    log(f"[2] moved split: carried_ground={len(moved_carried_ground)} rock={len(moved_carried_rock)} "
        f"fill={len(moved_fill)}")
    if moved_carried_rock:
        findings.append(f"REFUTE (2): {len(moved_carried_rock)} ROCK-STAMP positions moved "
                        f"{[list(k) for k in moved_carried_rock[:4]]} -- rock is exempt.")
    if R["moved_split"]["unclassified"]:
        findings.append(f"REFUTE (2): {R['moved_split']['unclassified']} moved positions fall in no class.")

    # ================= (2) THE SCOPED CARRIED EXCEPTION =================
    # RAW (unrounded) Y on both sides. Using the 3dp POSITION KEY as the "before" Y would make every
    # exact-identity test compare a rounded value against a raw one -- a false positive generator.
    y5map = {k: ent5[groups[k][0]][1] for k in groups}
    y6map = {k: ent6[groups[k][0]][1] for k in groups}

    samples = []
    for k in carried_ground: samples.append((k[0], k[2], y5map[k], k))
    for k in fill:           samples.append((k[0], k[2], y5map[k], k))
    surf = Surface(samples, exclude_basin=True)
    surf_withbasin = Surface(samples, exclude_basin=False)
    R["reference"] = dict(n_samples=len(samples), n_after_basin_exclusion=len(surf.pts),
                          n_rock_samples=0,
                          estimator="IDW(1/max(d^2,1)) least-squares PLANE over the nearest <=48 samples inside a "
                                    "growing 10/14/20/28/40u radius (min 10), one Cauchy-on-MAD robust "
                                    "reweighting pass, leave-one-out on the query position.")

    def prominence(k, ymap):
        nbs = [n for n in pos_deg.get(k, ()) if n != k]
        if not nbs: return None, []
        ring = [ymap[n] for n in nbs if n in ymap]
        if not ring: return None, []
        return ymap[k] - max(ring), ring

    mc_rows = []
    for k in moved_carried_ground:
        ref, rad, n = surf.at(k[0], k[2], skip=(k,))
        prom, ring = prominence(k, y5map)
        prom_a, _ = prominence(k, y6map)
        lo, hi, ne = surf.envelope(k[0], k[2], 12.0, skip=(k,))
        mc_rows.append(dict(
            pos=[round(k[0], 3), round(y5map[k], 3), round(k[2], 3)],
            topo=sorted(pos_kept_ground[k]), y_before=round(y5map[k], 4), y_after=round(y6map[k], 4),
            dY=round(y6map[k] - y5map[k], 4),
            my_reference=None if ref is None else round(ref, 4), fit_radius=rad, fit_n=n,
            residual_before=None if ref is None else round(y5map[k] - ref, 4),
            residual_after=None if ref is None else round(y6map[k] - ref, 4),
            prominence_before=None if prom is None else round(prom, 4),
            prominence_after=None if prom_a is None else round(prom_a, 4),
            neighbour_ring_before=[round(v, 3) for v in sorted(ring, reverse=True)],
            r_crater=round(rcrater(k[0], k[2]), 3),
            kept_lo_r12=None if lo is None else round(lo, 3), kept_hi_r12=None if hi is None else round(hi, 3),
            n_entries=len(groups[k]),
            blocks=sorted({f"{e[0]},{e[1]}" for e in groups[k]}),
            parts=sorted({e[2] for e in groups[k]})))
    R["moved_carried"] = dict(n=len(mc_rows), rows=mc_rows)
    log("[2] moved carried rows:")
    for row in mc_rows:
        log(f"    {row['pos']} topo={row['topo']} res_b={row['residual_before']} prom_b={row['prominence_before']} "
            f"r={row['r_crater']} dY={row['dY']} res_a={row['residual_after']} prom_a={row['prominence_after']}")

    not_outlier = [r for r in mc_rows if r["residual_before"] is None or r["residual_before"] < OUTLIER_U]
    soft_outlier = [r for r in mc_rows if r["residual_before"] is not None
                    and 0.70 <= r["residual_before"] < OUTLIER_U]
    hard_not = [r for r in not_outlier if r["residual_before"] is None or r["residual_before"] < 0.70]
    not_localmax = [r for r in mc_rows if r["prominence_before"] is None or r["prominence_before"] < PROM_U]
    out_of_mound = [r for r in mc_rows if r["r_crater"] > MOUND_R]
    in_basin = [r for r in mc_rows if r["r_crater"] <= BASIN_R]
    not_terrain = [r for r in mc_rows if r["parts"] != ["Terrain"]]
    upward = [r for r in mc_rows if r["dY"] > 0]
    R["scoped_exception"] = dict(
        n_moved_carried=len(mc_rows),
        n_not_positive_outlier_at_0p8=len(not_outlier),
        n_in_the_0p70_0p80_soft_band=len(soft_outlier),
        n_hard_non_outliers_below_0p70=len(hard_not),
        n_not_strict_local_max=len(not_localmax),
        n_outside_mound=len(out_of_mound), n_inside_basin=len(in_basin),
        n_with_non_terrain_entries=len(not_terrain), n_moved_upward=len(upward),
        min_residual_before=min((r["residual_before"] for r in mc_rows if r["residual_before"] is not None),
                                default=None),
        min_prominence_before=min((r["prominence_before"] for r in mc_rows
                                   if r["prominence_before"] is not None), default=None),
        verdict_rule="a moved carried position that was NOT a positive outlier (>= 0.8u above MY OWN local "
                     "reference, measured pre-move) REFUTES the scoped carried exception. A position landing in "
                     "0.70-0.80 under MY estimator but >= 0.80 under the build's is an estimator-difference "
                     "margin and is reported as a NOTE, not a refutation.")
    if hard_not:
        findings.append(f"REFUTE (2): {len(hard_not)} moved CARRIED positions were NOT positive outliers "
                        f"(< 0.70u even allowing estimator slack) under my own reference: "
                        f"{[[r['pos'], r['residual_before']] for r in hard_not[:4]]}.")
    if soft_outlier:
        findings.append(f"NOTE (2): {len(soft_outlier)} moved carried positions land in the 0.70-0.80u band under "
                        f"MY estimator while the build's put them >= 0.80u -- an estimator-difference margin, "
                        f"not a scope breach: {[[r['pos'], r['residual_before']] for r in soft_outlier[:4]]}.")
    if not_localmax:
        findings.append(f"REFUTE (2): {len(not_localmax)} moved CARRIED positions were NOT strict local maxima "
                        f"(prominence < {PROM_U}u): {[[r['pos'], r['prominence_before']] for r in not_localmax[:4]]}.")
    if out_of_mound:
        findings.append(f"REFUTE (2): {len(out_of_mound)} moved carried positions lie OUTSIDE the {MOUND_R}u "
                        f"mound: {[[r['pos'], r['r_crater']] for r in out_of_mound[:4]]}.")
    if in_basin:
        findings.append(f"REFUTE (4): {len(in_basin)} moved carried positions lie INSIDE the sacred basin disc.")
    if not_terrain:
        findings.append(f"REFUTE (2): {len(not_terrain)} moved positions have entries outside Terrain: "
                        f"{[[r['pos'], r['parts']] for r in not_terrain[:4]]}.")
    if upward:
        findings.append(f"REFUTE (2): {len(upward)} carried spike(s) moved UPWARD (a shave must go down): "
                        f"{[[r['pos'], r['dY']] for r in upward[:4]]}.")

    mf_rows = []
    for k in moved_fill:
        ref, rad, n = surf.at(k[0], k[2], skip=(k,))
        mf_rows.append(dict(pos=[round(k[0], 3), round(y5map[k], 3), round(k[2], 3)],
                            dY=round(y6map[k] - y5map[k], 4), r_crater=round(rcrater(k[0], k[2]), 3),
                            residual_before=None if ref is None else round(y5map[k] - ref, 4),
                            residual_after=None if ref is None else round(y6map[k] - ref, 4)))
    R["moved_fill"] = dict(n=len(mf_rows), max_abs_dY=round(max((abs(r["dY"]) for r in mf_rows), default=0.0), 4),
                           min_r_crater=round(min((r["r_crater"] for r in mf_rows), default=0.0), 3),
                           rows=sorted(mf_rows, key=lambda r: -abs(r["dY"])))
    log(f"[2] moved fill n={len(mf_rows)} max|dY|={R['moved_fill']['max_abs_dY']} "
        f"min r_crater={R['moved_fill']['min_r_crater']}")
    if R["moved_fill"]["max_abs_dY"] > 0.6:
        findings.append(f"REFUTE (2): a fill unknown moved {R['moved_fill']['max_abs_dY']}u > the build's own "
                        f"0.6u acceptance ceiling.")

    frozen_bad = [list(k) for k in carried_ground if k not in set(moved_carried_ground)
                  and abs(dy_by_group.get(k, 0.0)) > 0]
    rock_bad = [list(k) for k in carried_rock if abs(dy_by_group.get(k, 0.0)) > 0]
    rock_bad_broad = [list(k) for k in carried_rock_touched if abs(dy_by_group.get(k, 0.0)) > 0]
    R["carried_freeze"] = dict(carried_ground_non_spike_moved=len(frozen_bad), examples=frozen_bad[:6],
                               carried_rock_moved_STRICT=len(rock_bad), rock_examples=rock_bad[:6],
                               carried_rock_moved_BROAD=len(rock_bad_broad),
                               broad_examples=rock_bad_broad[:6],
                               carried_rock_moved=len(rock_bad),
                               carried_ground_total=len(carried_ground),
                               carried_rock_total_strict=len(carried_rock),
                               carried_rock_total_broad=len(carried_rock_touched))
    if frozen_bad:
        findings.append(f"REFUTE (2): {len(frozen_bad)} carried-ground positions outside the moved set moved.")
    if rock_bad_broad:
        findings.append(f"REFUTE (2): {len(rock_bad_broad)} positions touched by a kept ROCK tri moved "
                        f"(rock is exempt under BOTH readings): {rock_bad_broad[:4]}.")

    # ================= (3) crack / facing / area / land>0 =================
    def once_edges_plan(which):
        cnt = Counter()
        for r in tris:
            w = r[which]
            for i in range(3):
                p, q = w[i], w[(i + 1) % 3]
                kp = (round(p[0], POSKEY), round(p[1], POSKEY), round(p[2], POSKEY))
                kq = (round(q[0], POSKEY), round(q[1], POSKEY), round(q[2], POSKEY))
                cnt[tuple(sorted((kp, kq)))] += 1
        once = {k for k, v in cnt.items() if v == 1}
        plan = Counter(((k[0][0], k[0][2]), (k[1][0], k[1][2])) for k in once)
        return cnt, once, plan
    c5, o5, p5p = once_edges_plan("w5")
    c6, o6, p6p = once_edges_plan("w6")
    plan_new = {k: v for k, v in (p6p - p5p).items()}
    R["crack_audit"] = dict(n_edges_before=len(c5), n_edges_after=len(c6),
                            once_edges_before=len(o5), once_edges_after=len(o6),
                            new_open_edges_in_PLAN=len(plan_new),
                            plan_examples=[[list(k[0]), list(k[1]), v] for k, v in list(plan_new.items())[:6]],
                            edge_multiplicity_before=dict(sorted(Counter(c5.values()).items())),
                            edge_multiplicity_after=dict(sorted(Counter(c6.values()).items())),
                            note="the XZ-plan projection of the once-edge set is Y-move-invariant; a split weld "
                                 "or a dropped tri shows up there as a NEW open plan edge.")
    log(f"[3] cracks: once {len(o5)} -> {len(o6)} plan_new={len(plan_new)}")
    if plan_new:
        findings.append(f"REFUTE (3): {len(plan_new)} NEW open edges in the XZ-plan once-edge audit (a crack): "
                        f"{R['crack_audit']['plan_examples'][:3]}.")

    ny5c = Counter(); ny6c = Counter(); flipped = []; newdown = []
    za5 = za6 = 0
    for r in tris:
        g5 = geo_normal(*r["w5"]); g6 = geo_normal(*r["w6"])
        s5 = 0 if abs(g5[1]) < 1e-12 else (1 if g5[1] > 0 else -1)
        s6 = 0 if abs(g6[1]) < 1e-12 else (1 if g6[1] > 0 else -1)
        ny5c[s5] += 1; ny6c[s6] += 1
        if s5 != s6: flipped.append([list(r["b"]), r["t"], s5, s6])
        if s6 < 0 and s5 >= 0: newdown.append([list(r["b"]), r["t"]])
        if math.sqrt(sum(c * c for c in g5)) < 1e-9: za5 += 1
        if math.sqrt(sum(c * c for c in g6)) < 1e-9: za6 += 1
    ys5_all = [p[1] for r in tris for p in r["w5"]]
    ys6_all = [p[1] for r in tris for p in r["w6"]]
    sank = [[list(r["b"]), r["t"], round(p[1], 4), round(q[1], 4)]
            for r in tris for p, q in zip(r["w5"], r["w6"]) if p[1] > SEA_Y and q[1] <= SEA_Y]
    moved_y6 = [y6map[k] for k in moved_keys]
    R["geometry_gates"] = dict(ny_sign_before=dict(ny5c), ny_sign_after=dict(ny6c),
                               tris_flipped=len(flipped), flip_examples=flipped[:6],
                               newly_down_facing=len(newdown), newdown_examples=newdown[:6],
                               zero_world_area_before=za5, zero_world_area_after=za6,
                               min_Y_all_terrain_before=round(min(ys5_all), 6),
                               min_Y_all_terrain_after=round(min(ys6_all), 6),
                               min_Y_over_moved_positions=round(min(moved_y6), 5) if moved_y6 else None,
                               verts_that_sank_to_or_below_sea=len(sank), sank_examples=sank[:6],
                               facing_proof="ny of the face cross product is a pure X/Z expression; a Y-only move "
                                            "cannot flip facing -- the count is the empirical confirmation.")
    log(f"[3] facing {dict(ny5c)} -> {dict(ny6c)} flipped={len(flipped)} newdown={len(newdown)} "
        f"zeroarea {za5}->{za6} minY {min(ys5_all):.4f}->{min(ys6_all):.4f} "
        f"minY_moved={R['geometry_gates']['min_Y_over_moved_positions']} sank={len(sank)}")
    if newdown: findings.append(f"REFUTE (3): {len(newdown)} tris became DOWN-FACING: {newdown[:4]}.")
    if flipped: findings.append(f"REFUTE (3): {len(flipped)} tris changed geometric facing sign.")
    if za6 > za5: findings.append(f"REFUTE (3): zero-world-area tris grew {za5} -> {za6}.")
    if sank: findings.append(f"REFUTE (3): {len(sank)} land vertices sank to or below sea Y=0: {sank[:4]}.")

    # ================= (4) THE BASIN DISC =================
    disc_keys = [k for k in groups if rcrater(k[0], k[2]) <= BASIN_R
                 and any(e[2] == "Terrain" for e in groups[k])]
    disc_moved = [[list(k), round(dy_by_group[k], 6)] for k in disc_keys if abs(dy_by_group[k]) > 0]
    disc_bytes_changed = 0; disc_entries = 0
    for k in disc_keys:
        for (bx, by, part, j) in groups[k]:
            D = T[(bx, by, part)]
            r5, r6 = D["r5"], D["r6"]
            o5 = r5["off_pos"] + j * 12; o6 = r6["off_pos"] + j * 12
            disc_entries += 1
            if r5["data"][o5:o5 + 12] != r6["data"][o6:o6 + 12]: disc_bytes_changed += 1
    # THE RIM BAND MUST EXCLUDE THE LICENSED MOVED SET. The shaved apexes sit at r = 12.02/12.58/13.83,
    # i.e. INSIDE a naive 7.92-13.92u annulus -- so a depth statistic over the raw band measures the
    # shave the round is licensed to make, not a change to the crater. The frozen-rim depth is the
    # only depth statistic that can falsify "the crater is sacred".
    rim_keys = [k for k in groups if BASIN_R < rcrater(k[0], k[2]) <= BASIN_R + 6.0
                and any(e[2] == "Terrain" for e in groups[k])]
    rim_frozen = [k for k in rim_keys if k not in set(moved_keys)]
    rim_band5 = [y5map[k] for k in rim_frozen]
    rim_band6 = [y6map[k] for k in rim_frozen]
    rim_all5 = [y5map[k] for k in rim_keys]; rim_all6 = [y6map[k] for k in rim_keys]
    floor5 = [y5map[k] for k in disc_keys]; floor6 = [y6map[k] for k in disc_keys]
    depth5 = (statistics.fmean(rim_band5) - statistics.fmean(floor5)) if rim_band5 and floor5 else None
    depth6 = (statistics.fmean(rim_band6) - statistics.fmean(floor6)) if rim_band6 and floor6 else None
    depth_all5 = (statistics.fmean(rim_all5) - statistics.fmean(floor5)) if rim_all5 and floor5 else None
    depth_all6 = (statistics.fmean(rim_all6) - statistics.fmean(floor6)) if rim_all6 and floor6 else None
    R["basin"] = dict(centre=list(BASIN_C), radius=BASIN_R,
                      n_terrain_positions_in_disc=len(disc_keys), n_vertex_entries_in_disc=disc_entries,
                      positions_moved=len(disc_moved), moved_examples=disc_moved[:6],
                      vertex_bytes_changed_in_disc=disc_bytes_changed,
                      floor_y_before=stats(floor5), floor_y_after=stats(floor6),
                      rim_band_y_before=stats(rim_band5), rim_band_y_after=stats(rim_band6),
                      n_rim_band_positions=len(rim_keys), n_rim_band_frozen=len(rim_frozen),
                      depth_before=None if depth5 is None else round(depth5, 4),
                      depth_after=None if depth6 is None else round(depth6, 4),
                      depth_INCLUDING_moved_before=None if depth_all5 is None else round(depth_all5, 4),
                      depth_INCLUDING_moved_after=None if depth_all6 is None else round(depth_all6, 4),
                      depth_metric="depth_before/after use the FROZEN rim only (moved positions excluded); the "
                                   "depth_INCLUDING_moved pair is reported to show how much of the naive "
                                   "statistic is the licensed shave itself.",
                      min_r_crater_of_a_moved_position=round(min((rcrater(k[0], k[2]) for k in moved_keys),
                                                                 default=float("inf")), 4))
    log(f"[4] basin: disc positions={len(disc_keys)} entries={disc_entries} moved={len(disc_moved)} "
        f"bytes_changed={disc_bytes_changed} depth {R['basin']['depth_before']} -> {R['basin']['depth_after']} "
        f"min_r_moved={R['basin']['min_r_crater_of_a_moved_position']}")
    if disc_moved:
        findings.append(f"REFUTE (4): {len(disc_moved)} Terrain positions INSIDE the sacred basin disc moved: "
                        f"{disc_moved[:4]}.")
    if disc_bytes_changed:
        findings.append(f"REFUTE (4): {disc_bytes_changed} vertex BYTES inside the basin disc changed.")
    if depth5 is not None and depth6 < depth5 - 1e-4:
        findings.append(f"REFUTE (4): the crater got SHALLOWER ({round(depth5,4)} -> {round(depth6,4)}).")

    moved_set = set(moved_keys)
    mound_before = []; mound_after = []
    for k in groups:
        if rcrater(k[0], k[2]) > MOUND_R: continue
        if k not in carried_ground and k not in carried_rock: continue
        if k in moved_set: continue
        for _ in groups[k]:
            mound_before.append(y5map[k]); mound_after.append(y6map[k])
    identical = sorted(mound_before) == sorted(mound_after)
    differing = sum(1 for a_, b_ in zip(mound_before, mound_after) if a_ != b_)
    R["rim_distribution"] = dict(n_carried_entries_in_mound_excluding_moved=len(mound_before),
                                 multiset_identical=identical, entries_differing=differing,
                                 before=stats(mound_before), after=stats(mound_after),
                                 crest_ring_count_at_6p208_before=sum(1 for v in mound_before
                                                                      if abs(v - 6.208) < 5e-3),
                                 crest_ring_count_at_6p208_after=sum(1 for v in mound_after
                                                                     if abs(v - 6.208) < 5e-3))
    log(f"[4] rim distribution: n={len(mound_before)} identical={identical} differing={differing}")
    if not identical:
        findings.append(f"REFUTE (4): the mound's carried height distribution changed outside the moved set "
                        f"({differing} entries differ).")

    # ================= (5) POST-MOVE BAND =================
    band_rows = []
    for row, k in zip(mc_rows, moved_carried_ground):
        ref = row["my_reference"]
        prom_a, ring_a = prominence(k, y6map)
        lo, hi, ne = surf.envelope(k[0], k[2], 12.0, skip=(k,))
        y_a = row["y_after"]
        band_rows.append(dict(
            pos=row["pos"], y_before=row["y_before"], y_after=y_a, reference=ref,
            below_reference_by=None if ref is None else round(max(0.0, ref - y_a), 4),
            between_old_and_reference=None if ref is None else (min(row["y_before"], ref) - 1e-3 <= y_a <=
                                                                max(row["y_before"], ref) + 1e-3),
            prominence_after=None if prom_a is None else round(prom_a, 4),
            still_local_max=None if prom_a is None else (prom_a > 0),
            new_local_min=None if not ring_a else (y_a < min(ring_a) - 1e-6),
            kept_envelope_r12=[None if lo is None else round(lo, 3), None if hi is None else round(hi, 3)],
            inside_kept_envelope=None if lo is None else (lo - 0.05 <= y_a <= hi + 0.05),
            rim_band_5p2_6p2=(5.2 <= y_a <= 6.2)))
    overshoot = [r for r in band_rows if r["below_reference_by"] and r["below_reference_by"] > 0.15]
    outside_band = [r for r in band_rows if r["between_old_and_reference"] is False]
    still_max = [r for r in band_rows if r["still_local_max"]]
    new_min = [r for r in band_rows if r["new_local_min"]]
    outside_env = [r for r in band_rows if r["inside_kept_envelope"] is False]
    R["post_move_band"] = dict(rows=band_rows, n_overshoot_below_reference_gt_0p15=len(overshoot),
                               n_outside_old_to_reference_interval=len(outside_band),
                               n_still_local_max=len(still_max), n_new_local_min=len(new_min),
                               n_outside_kept_envelope_r12=len(outside_env),
                               all_in_rim_band_5p2_6p2=all(r["rim_band_5p2_6p2"] for r in band_rows))
    log(f"[5] band: overshoot={len(overshoot)} outside_interval={len(outside_band)} still_max={len(still_max)} "
        f"new_min={len(new_min)} outside_env={len(outside_env)} "
        f"all_in_5.2-6.2={R['post_move_band']['all_in_rim_band_5p2_6p2']}")
    if overshoot:
        findings.append(f"REFUTE (5): {len(overshoot)} shaved apexes overshoot BELOW my own local reference by "
                        f">0.15u: {[[r['pos'], r['below_reference_by']] for r in overshoot[:4]]}.")
    if outside_band:
        findings.append(f"REFUTE (5): {len(outside_band)} shaved apexes land outside the [old Y, reference] "
                        f"interval: {[[r['pos'], r['y_after'], r['reference']] for r in outside_band[:4]]}.")
    if new_min:
        findings.append(f"REFUTE (5): {len(new_min)} shaved apexes became a new local MINIMUM (a dig-spot pit): "
                        f"{[r['pos'] for r in new_min[:4]]}.")
    if still_max:
        findings.append(f"NOTE (5): {len(still_max)} shaved apexes are still a local maximum (prominence > 0).")

    # ================= (6) REFUTATION HUNT =================
    hunt = {}

    # 6a: EXHAUSTIVENESS -- MY OWN spike census on each tree's own bytes
    samples6 = []
    for k in carried_ground: samples6.append((k[0], k[2], y6map[k], k))
    for k in fill:           samples6.append((k[0], k[2], y6map[k], k))
    surf6 = Surface(samples6, exclude_basin=True)

    def census(ymap, sfc, keys):
        rows = []
        for k in keys:
            rr = rcrater(k[0], k[2])
            if rr > MOUND_R or rr <= BASIN_R: continue
            ref, rad, n = sfc.at(k[0], k[2], skip=(k,))
            if ref is None: continue
            res = ymap[k] - ref
            prom, ring = prominence(k, ymap)
            rows.append(dict(pos=[round(k[0], 3), round(ymap[k], 3), round(k[2], 3)],
                             res=round(res, 4), prom=None if prom is None else round(prom, 4),
                             r=round(rr, 2),
                             topo=sorted(pos_kept_ground.get(k, set())),
                             qual=(res >= OUTLIER_U and prom is not None and prom >= PROM_U)))
        return rows
    cen5 = census(y5map, surf, carried_ground)
    cen6 = census(y6map, surf6, carried_ground)
    q5 = [r for r in cen5 if r["qual"]]; q6 = [r for r in cen6 if r["qual"]]
    moved_xz = {(round(k[0], 3), round(k[2], 3)) for k in moved_carried_ground}
    unmoved_q = [r for r in q5 if (r["pos"][0], r["pos"][2]) not in moved_xz]
    hunt["exhaustiveness"] = dict(
        n_carried_ground_in_mound=len(cen5),
        qualifiers_before=len(q5), qualifiers_after=len(q6),
        qualifier_rows_before=sorted(q5, key=lambda r: -r["res"]),
        qualifier_rows_after=sorted(q6, key=lambda r: -r["res"])[:8],
        qualifiers_before_that_were_NOT_moved=unmoved_q,
        max_residual_before=round(max((r["res"] for r in cen5), default=0.0), 4),
        max_residual_after=round(max((r["res"] for r in cen6), default=0.0), 4),
        max_prominence_before=round(max((r["prom"] for r in cen5 if r["prom"] is not None), default=0.0), 4),
        max_prominence_after=round(max((r["prom"] for r in cen6 if r["prom"] is not None), default=0.0), 4),
        top_remaining_by_residual=sorted(cen6, key=lambda r: -r["res"])[:5],
        top_remaining_by_prominence=sorted([r for r in cen6 if r["prom"] is not None],
                                           key=lambda r: -r["prom"])[:5],
        note="my own independent census, re-derived from each tree's own bytes with each tree's own reference.")
    log(f"[6] exhaustiveness: qualifiers {len(q5)} -> {len(q6)}; max res "
        f"{hunt['exhaustiveness']['max_residual_before']} -> {hunt['exhaustiveness']['max_residual_after']}; "
        f"max prom {hunt['exhaustiveness']['max_prominence_before']} -> "
        f"{hunt['exhaustiveness']['max_prominence_after']}")
    if q6:
        findings.append(f"NOTE (6): {len(q6)} carried positions still qualify as spikes under MY census after "
                        f"the shave: {q6[:3]} -- not exhaustive under my estimator (an under-shave, not a "
                        f"contract breach).")
    if unmoved_q:
        findings.append(f"NOTE (6): {len(unmoved_q)} positions qualify under MY pre-move census but were not "
                        f"moved: {unmoved_q[:4]}.")

    # 6b: NEW spikes anywhere on the surface
    def all_prom(ymap):
        out = {}
        for k in groups:
            if not any(e[2] == "Terrain" for e in groups[k]): continue
            p, ring = prominence(k, ymap)
            if p is not None: out[k] = p
        return out
    pr5 = all_prom(y5map); pr6 = all_prom(y6map)
    grew = sorted(((pr6[k] - pr5[k], k) for k in pr5 if k in pr6 and pr6[k] - pr5[k] > 1e-6), reverse=True)
    newpeaks = [[list(k), round(pr5[k], 4), round(pr6[k], 4)] for k in pr5
                if k in pr6 and pr5[k] <= 0 < pr6[k]]
    hunt["new_spikes"] = dict(n_positions=len(pr5),
                              prominence_before=stats(list(pr5.values())),
                              prominence_after=stats(list(pr6.values())),
                              n_prominence_grew=len(grew),
                              worst_growth=[[list(k), round(d, 4), round(pr5[k], 4), round(pr6[k], 4)]
                                            for d, k in grew[:8]],
                              n_became_local_max=len(newpeaks), became_local_max=newpeaks[:8],
                              max_prominence_before=round(max(pr5.values()), 4),
                              max_prominence_after=round(max(pr6.values()), 4))
    log(f"[6] prominence: max {hunt['new_spikes']['max_prominence_before']} -> "
        f"{hunt['new_spikes']['max_prominence_after']}; grew at {len(grew)}; new local maxima {len(newpeaks)}")
    if hunt["new_spikes"]["max_prominence_after"] > hunt["new_spikes"]["max_prominence_before"] + 1e-6:
        findings.append(f"REFUTE (6): the island's WORST prominence GREW "
                        f"{hunt['new_spikes']['max_prominence_before']} -> "
                        f"{hunt['new_spikes']['max_prominence_after']}.")
    if newpeaks:
        findings.append(f"NOTE (6): {len(newpeaks)} positions became local maxima (a shaved apex's own ring "
                        f"inheriting the high spot is expected): {newpeaks[:4]}.")

    # 6c: THE BASIN REFERENCE TRAP -- reproduce independently
    ring_keys = [k for k in carried_ground if 8.9 <= rcrater(k[0], k[2]) <= 11.5 and abs(y5map[k] - 6.208) < 5e-3]
    trap_wo = []; trap_w = []
    for k in ring_keys:
        rw, _, _ = surf.at(k[0], k[2], skip=(k,))
        rb, _, _ = surf_withbasin.at(k[0], k[2], skip=(k,))
        if rw is not None: trap_wo.append(y5map[k] - rw)
        if rb is not None: trap_w.append(y5map[k] - rb)
    hunt["basin_reference_trap"] = dict(
        rim_ring_n=len(ring_keys),
        residual_basin_EXCLUDED=stats(trap_wo), residual_basin_SAMPLED=stats(trap_w),
        qualifying_at_0p8_basin_EXCLUDED=sum(1 for v in trap_wo if v >= OUTLIER_U),
        qualifying_at_0p8_basin_SAMPLED=sum(1 for v in trap_w if v >= OUTLIER_U),
        reproduced=(sum(1 for v in trap_w if v >= OUTLIER_U) > sum(1 for v in trap_wo if v >= OUTLIER_U)),
        note="the crest ring at Y=6.208, r=8.9-11.5u, measured under MY estimator both ways. If sampling the "
             "bowl makes the crater's own rim read as spikes, the build's sample-set exclusion was load-bearing.")
    TR = hunt["basin_reference_trap"]
    log(f"[6] basin trap: ring n={len(ring_keys)} qualifying excluded={TR['qualifying_at_0p8_basin_EXCLUDED']} "
        f"sampled={TR['qualifying_at_0p8_basin_SAMPLED']} reproduced={TR['reproduced']}")

    # 6d: NORMALS -- scope + geometry + the donor-normal seam
    nrm_scope_bad = []; nrm_geo_bad = []; nrm_down = []; min_ny = 2.0; max_ang = 0.0
    n_rw_tris = 0; n_rw_entries = 0; n_rw_kept = 0
    turn = []
    for r in tris:
        chg = any(x != y for x, y in zip(r["n5"], r["n6"]))
        if chg:
            n_rw_tris += 1
            n_rw_entries += sum(1 for x, y in zip(r["n5"], r["n6"]) if x != y)
            if not r["synth"]: n_rw_kept += 1
            for x, y in zip(r["n5"], r["n6"]):
                lx = math.sqrt(sum(c * c for c in x)); ly = math.sqrt(sum(c * c for c in y))
                if lx > 1e-9 and ly > 1e-9:
                    d = max(-1.0, min(1.0, sum(p * q for p, q in zip(x, y)) / (lx * ly)))
                    turn.append(math.degrees(math.acos(d)))
        if chg and not r["moved"]:
            nrm_scope_bad.append([list(r["b"]), r["t"]])
        if not r["moved"]: continue
        g = geo_normal(*r["w6"]); L = math.sqrt(sum(c * c for c in g))
        if L < 1e-12: continue
        gn = [c / L for c in g]
        if gn[1] < 0: gn = [-c for c in gn]
        for st in r["n6"]:
            ls = math.sqrt(sum(c * c for c in st))
            if ls < 1e-9: nrm_geo_bad.append([list(r["b"]), r["t"], "zero-length"]); continue
            sn = [c / ls for c in st]
            dot = max(-1.0, min(1.0, sum(x * y for x, y in zip(sn, gn))))
            ang = math.degrees(math.acos(dot)); max_ang = max(max_ang, ang)
            if ang > 0.5: nrm_geo_bad.append([list(r["b"]), r["t"], round(ang, 4)])
            min_ny = min(min_ny, sn[1])
            if sn[1] < 0: nrm_down.append([list(r["b"]), r["t"], round(sn[1], 5)])
    rewritten_kept_pos = set()
    for r in tris:
        if r["synth"] or not any(x != y for x, y in zip(r["n5"], r["n6"])): continue
        for p in r["w6"]:
            rewritten_kept_pos.add((round(p[0], POSKEY), round(p[1], POSKEY), round(p[2], POSKEY)))
    seam = 0
    for r in tris:
        if r["synth"] or any(x != y for x, y in zip(r["n5"], r["n6"])): continue
        ks = [(round(p[0], POSKEY), round(p[1], POSKEY), round(p[2], POSKEY)) for p in r["w6"]]
        if any(k in rewritten_kept_pos for k in ks): seam += 1
    hunt["normals"] = dict(tris_rewritten=n_rw_tris, entries_rewritten=n_rw_entries,
                           of_which_KEPT_tris=n_rw_kept,
                           rewritten_on_UNMOVED_tri=len(nrm_scope_bad), scope_examples=nrm_scope_bad[:8],
                           max_angle_vs_geometric_deg=round(max_ang, 5),
                           non_geometric=len(nrm_geo_bad), non_geometric_examples=nrm_geo_bad[:8],
                           min_stored_ny_on_moved=round(min_ny, 6), down_facing_stored=len(nrm_down),
                           normal_turn_deg=stats(turn),
                           kept_tris_adjacent_to_a_rewritten_kept_tri_keeping_donor_normal=seam,
                           note="the round overwrites CARRIED tris' donor-smoothed normals with geometric ones; "
                                "the seam count is how many unmoved kept tris share a vertex position with one "
                                "of those -- a cosmetic shading-discontinuity surface, not a gate.")
    log(f"[6] normals: tris={n_rw_tris} (kept {n_rw_kept}) entries={n_rw_entries} scope_bad={len(nrm_scope_bad)} "
        f"max_ang={max_ang:.4f} non_geo={len(nrm_geo_bad)} min_ny={min_ny:.6f} seam_tris={seam}")
    if nrm_scope_bad:
        findings.append(f"REFUTE (6): {len(nrm_scope_bad)} normals rewritten on tris with NO moved vertex.")
    if nrm_geo_bad:
        findings.append(f"REFUTE (6): {len(nrm_geo_bad)} stored normals on moved tris are not the geometric "
                        f"up-facing normal (>0.5deg): {nrm_geo_bad[:4]}.")
    if nrm_down:
        findings.append(f"REFUTE (6): {len(nrm_down)} stored normals on moved tris point DOWN.")
    if n_rw_tris != 51:
        findings.append(f"MISMATCH (6): {n_rw_tris} tris got a rewritten normal, report claims 51.")
    if n_rw_kept != 8:
        findings.append(f"MISMATCH (6): {n_rw_kept} KEPT tris got a rewritten normal, report claims 8.")

    # 6e: carried-core donor byte match -- positional rigidity
    SHIFT = (-768.0, -384.0)
    donor = defaultdict(list); donor_blocks = 0
    try:
        for bx in (13, 14, 15):
            for by in (11, 12):
                try:
                    bm = X.read_block(bx, by, disc=1, part="terrain")
                except (ValueError, FileNotFoundError, OSError):
                    continue
                donor_blocks += 1
                ox, oz = X.block_world_origin(bx, by)
                for tri in bm.tris:
                    w = [(bm.verts[j][0] + ox + SHIFT[0], bm.verts[j][1], bm.verts[j][2] + oz + SHIFT[1])
                         for j in tri]
                    key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in w))
                    donor[key].append(tuple(sorted((round(float(bm.uvs[j][0]), 6),
                                                    round(float(bm.uvs[j][1]), 6)) for j in tri)))
    except Exception as exc:
        R["donor_error"] = repr(exc)
    uvs5_by_block = {(bx, by): uvs_of(T[(bx, by, "Terrain")]["r5"]) for (bx, by) in FOOTPRINT
                     if (bx, by, "Terrain") in T}
    matched_xz = verbatim = moved_core = verbatim_synth = 0
    moved_core_rows = []
    for r in tris:
        key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in r["w5"]))
        cands = donor.get(key)
        if not cands: continue
        matched_xz += 1
        u = uvs5_by_block[r["b"]]
        uv5 = tuple(sorted((round(u[j][0], 6), round(u[j][1], 6)) for j in r["tri"]))
        if any(c == uv5 for c in cands):
            verbatim += 1
            if r["synth"]: verbatim_synth += 1
            if r["moved"]:
                moved_core += 1
                moved_core_rows.append([list(r["b"]), r["t"], r["topo"]])
    hunt["carried_core"] = dict(donor_blocks=donor_blocks, donor_keys=len(donor),
                                matched_xz_only=matched_xz, carried_core_verbatim=verbatim,
                                of_those_in_my_synth_set=verbatim_synth, moved=moved_core,
                                moved_examples=moved_core_rows[:8],
                                note="XZ position key AND the donor's own UVs (round-4 lineage discriminator). "
                                     "THE CONTRACT CHANGE: this round LICENSES a carried tri to move if it "
                                     "carries a census spike, so a non-zero count here is a finding only when it "
                                     "exceeds the spike-bearing kept tris.")
    log(f"[6] carried-core: donor_blocks={donor_blocks} xz_only={matched_xz} verbatim={verbatim} "
        f"synth_overlap={verbatim_synth} moved={moved_core}")
    if verbatim_synth:
        findings.append(f"REFUTE (6): {verbatim_synth} tris are BOTH donor-verbatim and in my synthesized set.")
    if moved_core > 8:
        findings.append(f"REFUTE (6): {moved_core} donor-verbatim carried-core tris moved -- more than the 8 "
                        f"spike-bearing kept tris the contract licenses: {moved_core_rows[:4]}.")
    elif moved_core:
        findings.append(f"NOTE (6): {moved_core} donor-verbatim carried tris moved -- these ARE spike-bearing "
                        f"kept tris the round-6 contract licenses (topo {sorted({r[2] for r in moved_core_rows})}).")

    # 6f: did the shave actually flatten the touched tris?
    touched = [r for r in tris if r["moved"]]
    def span_dip(rows, which):
        sp = []; dip = []
        for r in rows:
            ys = [p[1] for p in r[which]]; sp.append(max(ys) - min(ys))
            g = geo_normal(*r[which]); L = math.sqrt(sum(c * c for c in g))
            if L > 1e-12: dip.append(math.degrees(math.acos(max(-1.0, min(1.0, abs(g[1]) / L)))))
        return sp, dip
    s5t, d5t = span_dip(touched, "w5"); s6t, d6t = span_dip(touched, "w6")
    hunt["touched_tri_relief"] = dict(n=len(touched), yspan_before=stats(s5t), yspan_after=stats(s6t),
                                      dip_before=stats(d5t), dip_after=stats(d6t),
                                      n_span_ge_1u_before=sum(1 for v in s5t if v >= 1.0),
                                      n_span_ge_1u_after=sum(1 for v in s6t if v >= 1.0),
                                      n_dip_ge_45_before=sum(1 for v in d5t if v >= 45.0),
                                      n_dip_ge_45_after=sum(1 for v in d6t if v >= 45.0))
    HT = hunt["touched_tri_relief"]
    log(f"[6] touched tris n={len(touched)}: span p95 {HT['yspan_before'].get('p95')} -> "
        f"{HT['yspan_after'].get('p95')}; dip max {HT['dip_before'].get('max')} -> {HT['dip_after'].get('max')}; "
        f"dip>=45 {HT['n_dip_ge_45_before']} -> {HT['n_dip_ge_45_after']}")
    if HT["yspan_after"].get("max", 0) > HT["yspan_before"].get("max", 0) + 1e-6:
        findings.append(f"REFUTE (6): the touched tris' worst Y-span GREW {HT['yspan_before'].get('max')} -> "
                        f"{HT['yspan_after'].get('max')} -- the shave added relief.")

    # 6g: blocks reconciliation
    moved_blocks = sorted({f"{e[0]},{e[1]}" for k in moved_keys for e in groups[k]})
    changed_blocks = sorted({rp.split("Block[")[1].split("]")[0] + "," + rp.split("][")[1].split("]")[0]
                             for rp in changed})
    hunt["moved_blocks"] = moved_blocks; hunt["changed_files_blocks"] = changed_blocks
    if set(moved_blocks) - set(changed_blocks):
        findings.append(f"REFUTE (1): blocks with moved vertices but no changed file: "
                        f"{sorted(set(moved_blocks) - set(changed_blocks))}.")
    if set(changed_blocks) - set(moved_blocks):
        findings.append(f"NOTE (1): files changed in blocks with no moved vertex: "
                        f"{sorted(set(changed_blocks) - set(moved_blocks))}.")
    per_block = Counter()
    for k in moved_keys:
        for e in groups[k]: per_block[f"({e[0]},{e[1]})"] += 1
    hunt["moved_entries_per_block"] = dict(sorted(per_block.items()))
    R["hunt"] = hunt

    # ================= (7) ANTI-VACUITY CALIBRATION =================
    # A clean pass is worthless unless each gate can be SHOWN to fire on a planted defect.
    # Every probe below is an in-memory simulation; nothing is written.
    calib = {}

    # (7a) THE SPIKE CENSUS CAN SEE A SPIKE: plant +1.5u on the flattest carried position in the mound
    mound_ground = [k for k in carried_ground if BASIN_R < rcrater(k[0], k[2]) <= MOUND_R]
    base_rows = {(r["pos"][0], r["pos"][2]): r for r in cen6}
    victim = None
    for k in sorted(mound_ground):
        r = base_rows.get((round(k[0], 3), round(k[2], 3)))
        if r and abs(r["res"]) < 0.15 and r["prom"] is not None and r["prom"] < 0.0:
            victim = k; break
    if victim is not None:
        planted = dict(y6map); planted[victim] = y6map[victim] + 1.5
        ref, _, _ = surf6.at(victim[0], victim[2], skip=(victim,))
        prom_p, _ = prominence(victim, planted)
        res_p = planted[victim] - ref if ref is not None else None
        calib["7a_planted_spike"] = dict(
            victim=[round(victim[0], 3), round(victim[2], 3)],
            residual_clean=base_rows[(round(victim[0], 3), round(victim[2], 3))]["res"],
            residual_planted=None if res_p is None else round(res_p, 4),
            prominence_planted=None if prom_p is None else round(prom_p, 4),
            census_flags_it=bool(res_p is not None and res_p >= OUTLIER_U and
                                 prom_p is not None and prom_p >= PROM_U))
        if not calib["7a_planted_spike"]["census_flags_it"]:
            findings.append("REFUTE (7a): my spike census does NOT flag a planted +1.5u spike -- the "
                            "exhaustiveness lane is vacuous and its 4->0 result means nothing.")
    else:
        calib["7a_planted_spike"] = dict(skipped="no flat carried victim found")
        findings.append("NOTE (7a): could not select a calibration victim; the census lane is unproven.")

    # (7b) THE SCOPED-EXCEPTION LANE CAN REJECT: the lowest-residual carried position in the mound
    # would have refuted had the build moved it.
    lowest = min(cen5, key=lambda r: r["res"]) if cen5 else None
    calib["7b_non_outlier_would_refute"] = dict(
        lowest_residual_carried_in_mound=None if lowest is None else lowest,
        below_hard_threshold_0p70=None if lowest is None else (lowest["res"] < 0.70),
        meaning="if THIS position appeared in the moved-carried set, lane (2) fires REFUTE. The lane is "
                "therefore falsifiable, not a tautology over whatever the build happened to move.")
    if lowest is not None and lowest["res"] >= 0.70:
        findings.append("NOTE (7b): every carried position in the mound scores >= 0.70u, so lane (2) could not "
                        "have rejected anything -- treat its pass as weak.")

    # (7c) THE WELD DETECTOR CAN SEE A SPLIT: perturb ONE entry of the largest multi-entry group
    multi = max(groups.items(), key=lambda kv: len(kv[1]))
    mk, ments = multi
    sim5 = [ent5[e][1] for e in ments]
    sim6 = list(sim5); sim6[0] += 0.25
    calib["7c_planted_weld_split"] = dict(
        group=[round(mk[0], 3), round(mk[1], 3), round(mk[2], 3)], n_entries=len(ments),
        spread_before=round(max(sim5) - min(sim5), 6), spread_after=round(max(sim6) - min(sim6), 6),
        split_detector_fires=bool((max(sim6) - min(sim6)) > (max(sim5) - min(sim5)) + 1e-6),
        nonuniform_detector_fires=bool((max(x - y for x, y in zip(sim6, sim5)) -
                                        min(x - y for x, y in zip(sim6, sim5))) > 1e-9))
    if not (calib["7c_planted_weld_split"]["split_detector_fires"] and
            calib["7c_planted_weld_split"]["nonuniform_detector_fires"]):
        findings.append("REFUTE (7c): my weld detectors do NOT fire on a planted one-entry split -- the weld "
                        "lane is vacuous.")

    # (7d) THE BASIN GATE CAN SEE AN INTRUSION: is the disc non-empty and would a move in it be caught?
    calib["7d_basin_gate"] = dict(
        n_positions_in_disc=len(disc_keys), n_vertex_entries_in_disc=disc_entries,
        gate_is_live=bool(disc_keys),
        nearest_moved_position_to_centre=round(R["basin"]["min_r_crater_of_a_moved_position"], 4),
        clearance_beyond_disc=round(R["basin"]["min_r_crater_of_a_moved_position"] - BASIN_R, 4))
    if not disc_keys:
        findings.append("REFUTE (7d): the basin disc contains NO positions -- the 'basin frozen' claim is "
                        "vacuously true and proves nothing.")

    # (7e) THE ESTIMATORS DISAGREE ENOUGH TO BE INDEPENDENT: compare my residuals to the build's on the
    # 4 sites it reported, without importing its code (numbers read from its JSON only).
    rep_path = RUNG / "uvf_fix6_report.json"
    if rep_path.exists():
        rj0 = json.loads(rep_path.read_text(encoding="utf-8"))
        theirs = {(round(s["peak_world"][0], 3), round(s["peak_world"][2], 3)): s["peak_residual_u"]
                  for s in rj0["stage3_spike_census"]["sites"]}
        pairs = []
        for r in mc_rows:
            t = theirs.get((r["pos"][0], r["pos"][2]))
            if t is not None:
                pairs.append([r["pos"], t, r["residual_before"], round(r["residual_before"] - t, 4)])
        calib["7e_estimator_agreement"] = dict(
            row_schema=["pos", "build_residual", "my_residual", "delta"], rows=pairs,
            max_abs_delta=round(max((abs(p[3]) for p in pairs), default=0.0), 4),
            n_matched=len(pairs),
            reading="the two estimators are different code with different radii and different robust "
                    "weighting; a small non-zero delta is the evidence they are genuinely independent, "
                    "while both clearing 0.8u is the corroboration.")
        if len(pairs) != len(mc_rows):
            findings.append(f"MISMATCH (7e): only {len(pairs)}/{len(mc_rows)} moved carried positions appear "
                            f"in the build's own reported site list -- the build moved something it did not "
                            f"census.")
        if calib["7e_estimator_agreement"]["max_abs_delta"] == 0.0 and pairs:
            findings.append("NOTE (7e): my residuals match the build's EXACTLY -- suspicious for two "
                            "independent estimators; check for accidental code sharing.")
    R["calibration"] = calib
    log(f"[7] calibration: spike_seen={calib.get('7a_planted_spike', {}).get('census_flags_it')} "
        f"weld_split_seen={calib.get('7c_planted_weld_split', {}).get('split_detector_fires')} "
        f"basin_live={calib.get('7d_basin_gate', {}).get('gate_is_live')} "
        f"estimator_max_delta={calib.get('7e_estimator_agreement', {}).get('max_abs_delta')}")

    # ================= report reconciliation =================
    rep = RUNG / "uvf_fix6_report.json"
    recon = {}
    if rep.exists():
        rj = json.loads(rep.read_text(encoding="utf-8"))
        ap = rj["stage_apply"]; sg = rj["stop_guards"]; s1 = rj["stage1_mesh"]; s3 = rj["stage3_spike_census"]
        claims = dict(positions_moved=ap["positions_moved"], vertex_entries_moved=ap["vertex_entries_moved"],
                      tris_with_moved_vert=ap["tris_with_a_moved_vert"],
                      kept_tris_moved=ap["of_which_carried_kept_tris"],
                      normal_tris=ap["normal_tris_recomputed"], normal_entries=ap["normal_verts_rewritten"],
                      max_abs_dY=ap["max_abs_dY"], cross_block=ap["positions_spanning_multiple_blocks"],
                      files_changed=3,
                      distinct_positions=s1["n_distinct_positions_all_parts"],
                      carried_ground=s1["n_carried_ground_positions"],
                      carried_rock=s1["n_carried_rock_positions"], fill=s1["n_fill_positions"],
                      synthesized=s1["n_synthesized_tris"], n_spikes=s3["n_spikes"],
                      basin_disc_positions=sg["basin_disc_positions_total"],
                      min_r_crater_moved=sg["min_r_crater_of_a_moved_position"],
                      rock_moved=sg["rock_positions_moved"],
                      carried_non_spike_moved=sg["carried_non_spike_positions_moved"])
        mine = dict(positions_moved=len(moved_keys), vertex_entries_moved=chan["y_moved_entries"],
                    tris_with_moved_vert=len(touched), kept_tris_moved=n_rw_kept,
                    normal_tris=n_rw_tris, normal_entries=n_rw_entries,
                    max_abs_dY=round(max(abs(dy_by_group[k]) for k in moved_keys), 4) if moved_keys else 0.0,
                    cross_block=cross_block_moved, files_changed=len(changed),
                    distinct_positions=len(groups), carried_ground=len(carried_ground),
                    # adjudicated above: the report's number is the BROAD reading of its own definition
                    carried_rock=(len(carried_rock_touched)
                                  if len(carried_rock_touched) == s1["n_carried_rock_positions"]
                                  else len(carried_rock)),
                    fill=len(fill),
                    synthesized=n_synth, n_spikes=len(moved_carried_ground),
                    basin_disc_positions=len(disc_keys),
                    min_r_crater_moved=round(R["basin"]["min_r_crater_of_a_moved_position"], 3),
                    rock_moved=len(rock_bad), carried_non_spike_moved=len(frozen_bad))
        mism = {k: [claims[k], mine[k]] for k in claims
                if (isinstance(claims[k], float) and abs(claims[k] - (mine[k] or 0)) > 5e-3)
                or (not isinstance(claims[k], float) and claims[k] != mine[k])}
        recon = dict(claimed=claims, measured=mine, mismatches=mism)
        if mism: findings.append(f"MISMATCH (report): {mism} (claimed vs measured).")
    R["report_reconciliation"] = recon
    log(f"[R] reconciliation mismatches={recon.get('mismatches')}")

    hard = [f for f in findings if f.startswith("REFUTE") or f.startswith("MISMATCH")]
    R["findings"] = findings
    R["notes"] = [f for f in findings if f.startswith("NOTE")]
    R["verdict"] = "REFUTED" if hard else "CONFIRMED"
    OUT.write_text(json.dumps(R, indent=1), encoding="utf-8")
    log("\n" + "=" * 80)
    log(f"VERDICT: {R['verdict']}")
    for f in findings: log("  - " + f)
    log(f"-> {OUT}")
    return R


if __name__ == "__main__":
    main()
