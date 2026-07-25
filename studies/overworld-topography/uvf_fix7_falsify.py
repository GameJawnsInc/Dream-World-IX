"""RUNG F -- THE SLIVER-STEP ROUND (FIXED7) CODE-DISJOINT FALSIFIER (2026-07-25).

Round-7 verifier.  Extends MY OWN falsifier lineage
(uvf_fix_falsify -> uvf_fix2 -> uvf_fix3 -> uvf_fix4 -> uvf_fix5 -> uvf_fix6 -> THIS).
Does NOT import uvf_fix7 / uvf_gates7 / uvf_sliver_probe / uvf_fix6 / uvf_relief_probe / uvf_eye*,
and does not bootstrap ANY set, threshold or site list out of the build's own JSON except for the
final report-reconciliation table and one estimator-agreement calibration (both explicitly labelled).
Reuses ONLY the loaders (ff9mapkit.world.extract/.mesh) and the kit ground-family table
(grassland.TOPO_FAMILY) as an oracle for "which kept topos are ground".  Every parse, byte diff,
weld map, topo decode, reference surface, prominence, DROP, census arm, hop graph, normal check,
UV rect and gate below is re-implemented here from raw bytes.

THE CONTRACT CHANGE THIS ROUND: predicate (3) of round 6's five-predicate carried-move census gains
a STEP ARM -- prominence >= 0.40u (CONE) OR (prominence >= 0.00u AND max welded drop >= 1.50u) (STEP).
That widening removes the shape protection that used to keep the crater's own rim crest out of the
census, so the load-bearing lanes here are (2) re-justifying the single moved carried position under
MY OWN surface fit and MY OWN arm arithmetic, and (6) measuring how close the widened rule comes to
eating the sacred rim under an estimator that is NOT the build's.

CLAIMS TESTED INDEPENDENTLY FROM RAW BYTES:
 (1) changes = Y + normals ONLY, in ONE file; X/Z/UV/tangent/index/header bytes identical EVERYWHERE;
     normals rewritten only on tris that actually carry a moved vertex.
 (2) my own byte-diff -> moved positions -> classification -> every moved CARRIED position must pass
     the build's STATED five-predicate rule under MY OWN basin-excluded surface fit, MY OWN mesh
     prominence and MY OWN welded-drop/slope arithmetic.  Any unjustified carried move = REFUTED.
     Fill moves must be welded, Terrain-only, <= 2 mesh hops from a spike and <= 0.6u.
 (3) UV lane: UV/tangent bytes must be byte-identical (the round declares a geometry-only lever); the
     lane is kept NON-VACUOUS by re-deriving the stock UV-window rect vocabulary from REAL stock bytes
     (the dunes mass (18,3)(18,4)(19,3)(19,4)(20,3) + the Cleyra junction (13-15,11-12)) and testing
     that the faces this round re-poses still wear a genuine stock window, plus a texel-stretch
     measurement of the smear the diagnosis blamed.
 (4) PRIOR-FIX REGRESSION, all re-derived from the older TREES, never from a report: the round-6 spike
     sites = MY byte diff FIXED5->FIXED6; the round-5 relax set = MY byte diff FIXED4->FIXED5;
     degenerate UV = 0 on FIXED7's own bytes; the basin disc byte-frozen; crack/facing/land>0.
 (5) POST-MOVE: the shaved crest lands in the reference band, is no longer a local max, is not a new
     local min, and its step actually collapsed.
 (6) REFUTATION HUNT: self-termination re-census on each tree's own bytes, THE STEP-ARM BLAST RADIUS
     (how many carried positions pass an arm and how close the crest ring comes to the residual gate
     under MY estimator), the BASIN REFERENCE TRAP reproduced, new-spike hunt, normals, the
     donor-verbatim "fifth fidelity payment", report reconciliation.
 (7) ANTI-VACUITY CALIBRATION: every gate shown to fire on a planted defect.

READ-ONLY vs the game install (stock donor/dunes block reads only).  Writes
out/rung_f/uvf_fix7_falsify.json.

    PYTHONIOENCODING=utf-8 py -X utf8 uvf_fix7_falsify.py
"""
from __future__ import annotations
import json, math, struct, sys, statistics
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X      # noqa: E402
from ff9mapkit.world import mesh as M         # noqa: E402
from ff9mapkit.world import grassland as G    # noqa: E402

RUNG = HERE / "out" / "rung_f"
SPEC = RUNG / "FF9CustomMap-world"                # pre-fix specimen -> the synthesized-set classifier
FIXED4 = RUNG / "FF9CustomMap-world-FIXED4"       # round-5's base   (for the round-5 regression set)
FIXED5 = RUNG / "FF9CustomMap-world-FIXED5"       # round-6's base   (for the round-6 regression set)
BASE = RUNG / "FF9CustomMap-world-FIXED6"         # this round's base
TGT = RUNG / "FF9CustomMap-world-FIXED7"          # candidate
OUT = RUNG / "uvf_fix7_falsify.json"

FOOTPRINT = [(bx, by) for bx in range(0, 5) for by in range(16, 20)]
PARTS = ("Terrain", "Object", "Beach1", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5")
MAGIC = b"F9WM"
UV_ZERO = 1e-6
POSKEY = 3
SEA_Y = 0.0

BASIN_C = (127.14, -1161.42)
BASIN_R = 7.92
GUARD_R = 9.92
MOUND_R = 40.0

# the round's OWN stated rule (transcribed from its prose, re-implemented here)
OUTLIER_U = 0.80          # predicate (2) residual gate
CONE_PROM = 0.40          # predicate (3) CONE arm
STEP_PROM = 0.00          # predicate (3) STEP arm, prominence floor
STEP_DROP = 1.50          # predicate (3) STEP arm, welded-drop floor
HOPS = 2                  # fill unknowns within 2 mesh hops of a spike
FILL_CEIL = 0.6           # the build's own fill acceptance ceiling

# stock reference regions (READ-ONLY) for the UV-rect vocabulary
DUNES_BLOCKS = [(18, 3), (18, 4), (19, 3), (19, 4), (20, 3)]
CLEYRA_BLOCKS = [(bx, by) for bx in (13, 14, 15) for by in (11, 12)]
SHIFT = (-768.0, -384.0)  # the carry's world shift, used only to test the fidelity-cost claim


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


def dip_of(pts):
    g = geo_normal(*pts); L = math.sqrt(sum(c * c for c in g))
    return None if L < 1e-12 else round(math.degrees(math.acos(max(-1.0, min(1.0, abs(g[1]) / L)))), 2)


def tri_area3(p0, p1, p2):
    g = geo_normal(p0, p1, p2)
    return 0.5 * math.sqrt(sum(c * c for c in g))


def rcrater(x, z): return math.hypot(x - BASIN_C[0], z - BASIN_C[1])


# ---- MY OWN surface reference: IDW-weighted LSQ plane, Cauchy-robust, leave-one-out ----
class Surface:
    """Independent local-surface estimator -- NOT the build's.

    Growing radii 10/14/20/28/40u (build: 8/12/18/26), ONE Cauchy-on-MAD reweighting pass
    (build: two Tukey-biweight IRLS passes), <=48 nearest, weight 1/max(d^2,1).  Leave-one-out
    by key blacklist so a lone crest cannot fit itself.  Rock never enters the sample set.
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
        skip = set(skip)
        for R in self.RADII:
            got = self._gather(x, z, R, skip)
            if len(got) < self.MINN: continue
            sol = self._solve(got, x, z)
            if sol is None: continue
            a, bb, cc = sol
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


# =====================================================================================
def main():
    findings = []; R = {}
    R["meta"] = dict(
        script="uvf_fix7_falsify.py", round=7, spec=str(SPEC), base=str(BASE), target=str(TGT),
        regression_trees=[str(FIXED4), str(FIXED5)],
        poskey_dp=POSKEY, uv_zero=UV_ZERO, parts=list(PARTS),
        basin=dict(center=list(BASIN_C), radius=BASIN_R, guard_radius=GUARD_R), mound_radius=MOUND_R,
        rule=dict(residual_gate_u=OUTLIER_U, cone_prominence_u=CONE_PROM,
                  step_prominence_u=STEP_PROM, step_drop_u=STEP_DROP, hops=HOPS,
                  fill_ceiling_u=FILL_CEIL,
                  statement="a SPIKE is a CARRIED position with a ground-family topograph (rock exempt) "
                            "that sits >= 0.80u above the local basin-excluded rim reference AND passes "
                            "an arm -- CONE: prominence >= 0.40u, or STEP: prominence >= 0.00u and max "
                            "welded drop >= 1.50u -- inside the 40u mound and outside the basin disc."),
        independence="no import of uvf_fix7/uvf_gates7/uvf_sliver_probe/uvf_fix6/uvf_relief_probe; own "
                     "parser, own weld map, own topo decode, own hop graph, own drop/slope arithmetic and "
                     "own surface estimator (10/14/20/28/40u Cauchy-on-MAD IDW-LSQ plane, leave-one-out) "
                     "-- NOT the build's 8/12/18/26u two-pass Tukey scheme.  The round-6 and round-5 "
                     "regression sets are re-derived from the FIXED5->FIXED6 and FIXED4->FIXED5 byte "
                     "diffs, not from any report.")

    # ================= (1) tree + channel rigidity =================
    def rel(root): return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
    a, b = rel(BASE), rel(TGT)
    only_b = sorted(set(a) - set(b)); only_t = sorted(set(b) - set(a))
    changed = [rp for rp in sorted(set(a) & set(b)) if (BASE / rp).read_bytes() != (TGT / rp).read_bytes()]
    non_terrain_changed = [rp for rp in changed if not rp.endswith("Terrain.ff9mesh")]
    non_disc1 = [rp for rp in changed if "Disc1" not in rp]
    R["tree_diff"] = dict(n_base=len(a), n_target=len(b), only_base=only_b, only_target=only_t,
                          n_changed=len(changed), changed=changed,
                          changed_non_terrain=non_terrain_changed, changed_non_disc1=non_disc1)
    log(f"[1] files {len(a)}/{len(b)} changed={len(changed)} -> {changed}")
    if only_b or only_t: findings.append(f"REFUTE (1): file set differs only_base={only_b} only_target={only_t}.")
    if non_terrain_changed: findings.append(f"REFUTE (1): non-Terrain files changed: {non_terrain_changed}.")
    if non_disc1: findings.append(f"REFUTE (1): non-Disc1 files changed: {non_disc1}.")
    if len(changed) != 1: findings.append(f"MISMATCH (1): {len(changed)} files changed, report claims 1.")
    if changed and "Block[1][18]" not in changed[0]:
        findings.append(f"MISMATCH (1): the changed file is {changed[0]}, report declares Block[1][18] Terrain.")

    # ---- load every part of every footprint block, all four trees ----
    T = {}; missing = []; older_ok = True; older_bad = []
    for (bx, by) in FOOTPRINT:
        for part in PARTS:
            pb, pt = part_path(BASE, bx, by, part), part_path(TGT, bx, by, part)
            if not pb.exists() or not pt.exists():
                if pb.exists() != pt.exists(): missing.append([bx, by, part, pb.exists(), pt.exists()])
                continue
            rb, rt = parse_raw(pb), parse_raw(pt)
            ent = dict(rb=rb, rt=rt, vb=verts_of(rb), vt=verts_of(rt), org=X.block_world_origin(bx, by))
            for tag, root in (("v5", FIXED5), ("v4", FIXED4)):
                p = part_path(root, bx, by, part)
                if p.exists():
                    ro = parse_raw(p)
                    if (ro["vcount"], ro["icount"]) != (rb["vcount"], rb["icount"]):
                        older_ok = False; older_bad.append([bx, by, part, tag, "header"])
                        ent[tag] = None
                    else:
                        vo = verts_of(ro)
                        if any(abs(p_[0] - q[0]) > 1e-9 or abs(p_[2] - q[2]) > 1e-9 for p_, q in zip(vo, ent["vb"])):
                            older_ok = False; older_bad.append([bx, by, part, tag, "xz"])
                        ent[tag] = vo
                else:
                    ent[tag] = None; older_ok = False; older_bad.append([bx, by, part, tag, "missing"])
            T[(bx, by, part)] = ent
    S = {}; spec_bad = []
    for (bx, by) in FOOTPRINT:
        p = part_path(SPEC, bx, by, "Terrain")
        if not p.exists(): spec_bad.append([bx, by, "missing-spec"]); continue
        r = parse_raw(p); S[(bx, by)] = dict(r=r, uv=uvs_of(r), idx=idx_of(r))
    R["load"] = dict(n_part_files=len(T), missing=missing, spec_blocks=len(S), spec_bad=spec_bad,
                     older_trees_aligned=older_ok, older_tree_problems=older_bad[:8])
    if missing: findings.append(f"REFUTE (1): part-file presence differs base/target: {missing}.")
    if spec_bad: findings.append(f"NOTE: specimen tree incomplete: {spec_bad}.")
    if not older_ok:
        findings.append(f"NOTE (4): FIXED4/FIXED5 are not index/XZ aligned with FIXED6 ({older_bad[:3]}) -- "
                        f"the prior-round regression sets fall back to whatever aligned parts exist.")

    chan = dict(header_bad=[], uv_bad=[], tan_bad=[], idx_bad=[], nrm_changed_files=[],
                pos_changed_files=[], xz_moved=[], y_moved_entries=0, nrm_changed_entries=0,
                flat_mesh_bad=[])
    moved_entries = []
    for key, D in sorted(T.items()):
        bx, by, part = key
        rb, rt = D["rb"], D["rt"]
        if (rb["vcount"], rb["icount"], rb["flags"], rb["version"]) != \
           (rt["vcount"], rt["icount"], rt["flags"], rt["version"]):
            chan["header_bad"].append([bx, by, part]); continue
        if rt["vcount"] != rt["icount"] or rt["icount"] % 3:
            chan["flat_mesh_bad"].append([bx, by, part, rt["vcount"], rt["icount"]])
        if rb["sz_uv"] and sl(rb, rb["off_uv"], rb["sz_uv"]) != sl(rt, rt["off_uv"], rt["sz_uv"]):
            chan["uv_bad"].append([bx, by, part])
        if rb["sz_tan"] and sl(rb, rb["off_tan"], rb["sz_tan"]) != sl(rt, rt["off_tan"], rt["sz_tan"]):
            chan["tan_bad"].append([bx, by, part])
        if sl(rb, rb["off_idx"], rb["sz_idx"]) != sl(rt, rt["off_idx"], rt["sz_idx"]):
            chan["idx_bad"].append([bx, by, part])
        if sl(rb, rb["off_pos"], rb["sz_pos"]) != sl(rt, rt["off_pos"], rt["sz_pos"]):
            chan["pos_changed_files"].append(f"{bx},{by},{part}")
            db, dt = rb["data"], rt["data"]
            for j in range(rb["vcount"]):
                ob = rb["off_pos"] + j * 12; ot = rt["off_pos"] + j * 12
                if db[ob:ob + 12] == dt[ot:ot + 12]: continue
                if db[ob:ob + 4] != dt[ot:ot + 4] or db[ob + 8:ob + 12] != dt[ot + 8:ot + 12]:
                    chan["xz_moved"].append([bx, by, part, j])
                chan["y_moved_entries"] += 1
                moved_entries.append((bx, by, part, j))
        if rb["sz_nrm"] and sl(rb, rb["off_nrm"], rb["sz_nrm"]) != sl(rt, rt["off_nrm"], rt["sz_nrm"]):
            chan["nrm_changed_files"].append(f"{bx},{by},{part}")
            db, dt = rb["data"], rt["data"]
            chan["nrm_changed_entries"] += sum(
                1 for j in range(rb["vcount"])
                if db[rb["off_nrm"] + j * 12: rb["off_nrm"] + j * 12 + 12] !=
                   dt[rt["off_nrm"] + j * 12: rt["off_nrm"] + j * 12 + 12])
    chan["xz_moved_n"] = len(chan["xz_moved"]); chan["xz_moved"] = chan["xz_moved"][:10]
    R["channel_rigidity"] = chan
    log(f"[1] uv_bad={chan['uv_bad']} tan_bad={chan['tan_bad']} idx_bad={chan['idx_bad']} "
        f"hdr={chan['header_bad']} y_entries={chan['y_moved_entries']} xz={chan['xz_moved_n']} "
        f"nrm_entries={chan['nrm_changed_entries']} flat_bad={chan['flat_mesh_bad']}")
    for k, lbl in (("header_bad", "headers"), ("uv_bad", "UVs"), ("tan_bad", "tangents/IDALL"),
                   ("idx_bad", "indices")):
        if chan[k]: findings.append(f"REFUTE (1): {lbl} changed BASE->TARGET in {chan[k]}.")
    if chan["xz_moved_n"]:
        findings.append(f"REFUTE (1): {chan['xz_moved_n']} vertex entries had X or Z bytes rewritten "
                        f"(the move must be Y-only): {chan['xz_moved'][:4]}.")
    if chan["flat_mesh_bad"]:
        findings.append(f"REFUTE (3): FLAT-MESH invariant broken: {chan['flat_mesh_bad']}.")
    if chan["y_moved_entries"] != 16:
        findings.append(f"MISMATCH (1): {chan['y_moved_entries']} position entries moved, report claims 16.")
    if chan["nrm_changed_entries"] != 36:
        findings.append(f"MISMATCH (1): {chan['nrm_changed_entries']} normal entries rewritten, report "
                        f"claims 36.")

    # SPEC vs BASE index/XZ parity: the identity that lets SPEC UVs classify the synthesized set
    spec_diffs = []
    for (bx, by) in FOOTPRINT:
        if (bx, by) not in S or (bx, by, "Terrain") not in T: continue
        rs = S[(bx, by)]["r"]; rb = T[(bx, by, "Terrain")]["rb"]
        if (rs["vcount"], rs["icount"]) != (rb["vcount"], rb["icount"]):
            spec_diffs.append([bx, by, "header"]); continue
        if sl(rs, rs["off_idx"], rs["sz_idx"]) != sl(rb, rb["off_idx"], rb["sz_idx"]):
            spec_diffs.append([bx, by, "idx"])
        vs = verts_of(rs); vb = T[(bx, by, "Terrain")]["vb"]
        if any(abs(p[0] - q[0]) > 1e-9 or abs(p[2] - q[2]) > 1e-9 for p, q in zip(vs, vb)):
            spec_diffs.append([bx, by, "xz"])
    R["spec_parity"] = dict(diffs=spec_diffs,
                            note="SPEC's degenerate UVs remain the synthesized-tri classifier; the carry-over "
                                 "proof is 0 index diffs + 0 X/Z diffs.")
    if spec_diffs:
        findings.append(f"REFUTE (1): SPEC vs BASE indices/XZ differ {spec_diffs}.")

    # ================= per-tri table =================
    tris = []
    for (bx, by) in FOOTPRINT:
        if (bx, by, "Terrain") not in T or (bx, by) not in S: continue
        D = T[(bx, by, "Terrain")]; ox, oz = D["org"]
        rb = D["rb"]; idx = idx_of(rb); tan = tans_of(rb)
        su = S[(bx, by)]["uv"]; ub = uvs_of(rb)
        vb, vt = D["vb"], D["vt"]
        nb = nrms_of(rb); nt = nrms_of(D["rt"])
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            wb = [(vb[j][0] + ox, vb[j][1], vb[j][2] + oz) for j in tri]
            wt = [(vt[j][0] + ox, vt[j][1], vt[j][2] + oz) for j in tri]
            topo = X.decode_id(int(round(tan[tri[0]][0])))["topograph"]
            tris.append(dict(b=(bx, by), t=t, tri=tri, wb=wb, wt=wt, topo=topo,
                             synth=is_degenerate(*[su[j] for j in tri]),
                             uv=[ub[j] for j in tri],
                             nb=[nb[j] for j in tri], nt=[nt[j] for j in tri],
                             moved=any(p[1] != q[1] for p, q in zip(wb, wt))))
    n_synth = sum(1 for r in tris if r["synth"])
    R["synth_set"] = dict(n_terrain_tris=len(tris), n_synthesized=n_synth,
                          n_synth_with_moved_vert=sum(1 for r in tris if r["synth"] and r["moved"]),
                          n_kept_with_moved_vert=sum(1 for r in tris if not r["synth"] and r["moved"]),
                          kept_topo_hist=dict(sorted(Counter(r["topo"] for r in tris if not r["synth"]).items())),
                          synth_topo_hist=dict(sorted(Counter(r["topo"] for r in tris if r["synth"]).items())))
    log(f"[1] tris={len(tris)} synth={n_synth} synth_moved={R['synth_set']['n_synth_with_moved_vert']} "
        f"kept_moved={R['synth_set']['n_kept_with_moved_vert']}")
    if n_synth != 2305:
        findings.append(f"MISMATCH (1): my synthesized-set size {n_synth} != the reported 2305.")
    if R["synth_set"]["n_kept_with_moved_vert"] != 2:
        findings.append(f"MISMATCH (2): {R['synth_set']['n_kept_with_moved_vert']} KEPT tris carry a moved "
                        f"vertex, report claims 2.")
    n_moved_tris = sum(1 for r in tris if r["moved"])
    if n_moved_tris != 12:
        findings.append(f"MISMATCH (1): {n_moved_tris} tris carry a moved vertex, report claims 12.")

    # ================= (3-weld) weld map over ALL parts =================
    groups = defaultdict(list); entb = {}; entt = {}; ent5 = {}; ent4 = {}
    for (bx, by, part), D in T.items():
        ox, oz = D["org"]
        for j, (x, y, z) in enumerate(D["vb"]):
            wx, wy, wz = x + ox, y, z + oz
            k = (round(wx, POSKEY), round(wy, POSKEY), round(wz, POSKEY))
            groups[k].append((bx, by, part, j))
            entb[(bx, by, part, j)] = (wx, wy, wz)
        for j, (x, y, z) in enumerate(D["vt"]):
            entt[(bx, by, part, j)] = (x + ox, y, z + oz)
        if D.get("v5") is not None:
            for j, (x, y, z) in enumerate(D["v5"]): ent5[(bx, by, part, j)] = y
        if D.get("v4") is not None:
            for j, (x, y, z) in enumerate(D["v4"]): ent4[(bx, by, part, j)] = y

    split_groups = []; nonuniform = []; dy_by_group = {}
    moved_keys = []; cross_block_moved = 0; cross_part_moved = 0; partial_groups = []
    moved_entry_set = set(moved_entries)
    for k, ents in groups.items():
        dys = [entt[e][1] - entb[e][1] for e in ents]
        dmin, dmax = min(dys), max(dys)
        if dmax - dmin > 1e-9:
            nonuniform.append([list(k), round(dmin, 6), round(dmax, 6), len(ents)])
        yst = [entt[e][1] for e in ents]; ysb = [entb[e][1] for e in ents]
        if (max(yst) - min(yst)) > (max(ysb) - min(ysb)) + 1e-6:
            split_groups.append([list(k), round(max(ysb) - min(ysb), 6), round(max(yst) - min(yst), 6)])
        dy_by_group[k] = statistics.fmean(dys)
        if any(abs(d) > 0 for d in dys):
            moved_keys.append(k)
            if len({(e[0], e[1]) for e in ents}) > 1: cross_block_moved += 1
            if len({e[2] for e in ents}) > 1: cross_part_moved += 1
            miss = [e for e in ents if e not in moved_entry_set]
            if miss: partial_groups.append([list(k), len(ents), len(miss)])
    R["weld"] = dict(n_distinct_positions=len(groups), groups_that_split=len(split_groups),
                     split_examples=split_groups[:8], groups_with_nonuniform_delta=len(nonuniform),
                     nonuniform_examples=nonuniform[:8], groups_that_moved=len(moved_keys),
                     cross_block_groups_moved=cross_block_moved, cross_part_groups_moved=cross_part_moved,
                     partial_groups=len(partial_groups), partial_examples=partial_groups[:6],
                     entries_per_moved_position=dict(sorted(Counter(len(groups[k]) for k in moved_keys).items())),
                     moved_entries_reconcile=[sum(len(groups[k]) for k in moved_keys), chan["y_moved_entries"]])
    log(f"[3] weld: positions={len(groups)} split={len(split_groups)} nonuniform={len(nonuniform)} "
        f"moved={len(moved_keys)} cross_block={cross_block_moved} cross_part={cross_part_moved} "
        f"partial={len(partial_groups)}")
    if split_groups:
        findings.append(f"REFUTE (3): {len(split_groups)} coincident-position groups SPLIT: {split_groups[:4]}.")
    if nonuniform:
        findings.append(f"REFUTE (3): {len(nonuniform)} coincident groups got NON-UNIFORM dY: {nonuniform[:4]}.")
    if partial_groups:
        findings.append(f"REFUTE (3): {len(partial_groups)} moved groups have entries that did NOT move: "
                        f"{partial_groups[:4]}.")
    if sum(len(groups[k]) for k in moved_keys) != chan["y_moved_entries"]:
        findings.append(f"MISMATCH (3): weld-map moved entries {sum(len(groups[k]) for k in moved_keys)} != "
                        f"byte-diff moved entries {chan['y_moved_entries']}.")
    if len(moved_keys) != 3:
        findings.append(f"MISMATCH (3): {len(moved_keys)} positions moved, report claims 3.")
    if len(groups) != 8923:
        findings.append(f"MISMATCH (3): my distinct-position count {len(groups)} != the reported 8923.")

    # ================= position classification (MY OWN) =================
    pos_kept_ground = defaultdict(set); pos_kept_rock = defaultdict(set); pos_synth = set()
    pos_deg = defaultdict(set)
    for r in tris:
        ks = [(round(p[0], POSKEY), round(p[1], POSKEY), round(p[2], POSKEY)) for p in r["wb"]]
        for i in range(3):
            pos_deg[ks[i]].add(ks[(i + 1) % 3]); pos_deg[ks[(i + 1) % 3]].add(ks[i])
        fam = G.TOPO_FAMILY.get(r["topo"])
        for k in ks:
            if r["synth"]: pos_synth.add(k)
            elif fam is not None: pos_kept_ground[k].add(r["topo"])
            else: pos_kept_rock[k].add(r["topo"])
    carried_ground = set(pos_kept_ground)
    carried_rock = set(pos_kept_rock) - carried_ground
    carried_rock_touched = set(pos_kept_rock)
    fill = pos_synth - carried_ground - carried_rock
    R["classification"] = dict(carried_ground=len(carried_ground),
                               carried_rock_STRICT=len(carried_rock),
                               carried_rock_BROAD=len(carried_rock_touched),
                               rock_shared_with_ground=len(carried_rock_touched & carried_ground),
                               fill=len(fill),
                               carried_ground_topo_hist=dict(sorted(Counter(
                                   t for s in pos_kept_ground.values() for t in s).items())),
                               carried_rock_topo_hist=dict(sorted(Counter(
                                   t for k in carried_rock for t in pos_kept_rock[k]).items())))
    log(f"[2] carried_ground={len(carried_ground)} rock={len(carried_rock)}/{len(carried_rock_touched)} "
        f"fill={len(fill)}")
    if len(carried_ground) != 2427 or len(fill) != 937:
        findings.append(f"MISMATCH (2): my ground/fill classification {len(carried_ground)}/{len(fill)} "
                        f"!= the reported 2427/937.")
    if 458 not in (len(carried_rock), len(carried_rock_touched)):
        findings.append(f"MISMATCH (2): the reported 458 carried-rock positions matches neither of my two "
                        f"readings (strict {len(carried_rock)}, broad {len(carried_rock_touched)}).")

    moved_carried_ground = [k for k in moved_keys if k in carried_ground]
    moved_rock = [k for k in moved_keys if k in carried_rock_touched]
    moved_fill = [k for k in moved_keys if k in fill]
    R["moved_split"] = dict(carried_ground=len(moved_carried_ground), carried_rock=len(moved_rock),
                            fill=len(moved_fill),
                            unclassified=len(moved_keys) - len(moved_carried_ground) - len(moved_fill)
                                         - len([k for k in moved_rock if k not in carried_ground]))
    if [k for k in moved_rock if k not in carried_ground]:
        findings.append(f"REFUTE (2): rock-stamp positions moved -- rock is exempt at all three levels.")
    if R["moved_split"]["unclassified"]:
        findings.append(f"REFUTE (2): {R['moved_split']['unclassified']} moved positions fall in no class.")

    # ================= (2) THE SCOPED CARRIED EXCEPTION, round-7 rule =================
    yb = {k: entb[groups[k][0]][1] for k in groups}
    yt = {k: entt[groups[k][0]][1] for k in groups}

    samples = [(k[0], k[2], yb[k], k) for k in carried_ground] + [(k[0], k[2], yb[k], k) for k in fill]
    surf = Surface(samples, exclude_basin=True)
    surf_withbasin = Surface(samples, exclude_basin=False)
    R["reference"] = dict(n_samples=len(samples), n_after_basin_exclusion=len(surf.pts), n_rock_samples=0,
                          estimator="IDW(1/max(d^2,1)) LSQ PLANE over the nearest <=48 samples inside a growing "
                                    "10/14/20/28/40u radius (min 10), one Cauchy-on-MAD robust reweight, "
                                    "leave-one-out on the query position.")

    def shape(k, ymap):
        """MY OWN prominence / max welded drop / max welded slope on the mesh-edge graph."""
        nbs = [n for n in pos_deg.get(k, ()) if n != k and n in ymap]
        if not nbs: return None, None, None, []
        ring = [ymap[n] for n in nbs]
        prom = ymap[k] - max(ring)
        drop = ymap[k] - min(ring)
        slope = 0.0
        for n in nbs:
            d = math.hypot(k[0] - n[0], k[2] - n[2])
            if d > 1e-9:
                slope = max(slope, math.degrees(math.atan2(ymap[k] - ymap[n], d)))
        return prom, drop, slope, sorted(ring, reverse=True)

    def arm_of(prom, drop):
        if prom is None: return None
        if prom >= CONE_PROM: return "CONE"
        if prom >= STEP_PROM and drop is not None and drop >= STEP_DROP: return "STEP"
        return None

    mc_rows = []
    for k in moved_carried_ground:
        ref, rad, n = surf.at(k[0], k[2], skip=(k,))
        prom, drop, slope, ring = shape(k, yb)
        prom_a, drop_a, slope_a, ring_a = shape(k, yt)
        lo, hi, ne = surf.envelope(k[0], k[2], 12.0, skip=(k,))
        mc_rows.append(dict(
            pos=[round(k[0], 3), round(yb[k], 3), round(k[2], 3)],
            topo=sorted(pos_kept_ground[k]),
            topo_families=sorted({G.TOPO_FAMILY.get(t) for t in pos_kept_ground[k]}),
            y_before=round(yb[k], 4), y_after=round(yt[k], 4), dY=round(yt[k] - yb[k], 4),
            my_reference=None if ref is None else round(ref, 4), fit_radius=rad, fit_n=n,
            residual_before=None if ref is None else round(yb[k] - ref, 4),
            residual_after=None if ref is None else round(yt[k] - ref, 4),
            prominence_before=None if prom is None else round(prom, 4),
            prominence_after=None if prom_a is None else round(prom_a, 4),
            drop_before=None if drop is None else round(drop, 4),
            drop_after=None if drop_a is None else round(drop_a, 4),
            slope_before_deg=None if slope is None else round(slope, 3),
            slope_after_deg=None if slope_a is None else round(slope_a, 3),
            arm=arm_of(prom, drop), arm_after=arm_of(prom_a, drop_a),
            neighbour_ring_before=[round(v, 3) for v in ring],
            degree=len(pos_deg.get(k, ())),
            r_crater=round(rcrater(k[0], k[2]), 3),
            kept_lo_r12=None if lo is None else round(lo, 3), kept_hi_r12=None if hi is None else round(hi, 3),
            n_entries=len(groups[k]), blocks=sorted({f"{e[0]},{e[1]}" for e in groups[k]}),
            parts=sorted({e[2] for e in groups[k]})))
    R["moved_carried"] = dict(n=len(mc_rows), rows=mc_rows)
    log("[2] moved carried rows:")
    for row in mc_rows:
        log(f"    {row['pos']} topo={row['topo']} res={row['residual_before']} prom={row['prominence_before']} "
            f"drop={row['drop_before']} slope={row['slope_before_deg']} arm={row['arm']} r={row['r_crater']} "
            f"dY={row['dY']} -> res_a={row['residual_after']} prom_a={row['prominence_after']}")

    hard_not = [r for r in mc_rows if r["residual_before"] is None or r["residual_before"] < 0.70]
    soft_band = [r for r in mc_rows if r["residual_before"] is not None
                 and 0.70 <= r["residual_before"] < OUTLIER_U]
    no_arm = [r for r in mc_rows if r["arm"] is None]
    out_of_mound = [r for r in mc_rows if r["r_crater"] > MOUND_R]
    in_basin = [r for r in mc_rows if r["r_crater"] <= BASIN_R]
    in_guard = [r for r in mc_rows if r["r_crater"] <= GUARD_R]
    not_terrain = [r for r in mc_rows if r["parts"] != ["Terrain"]]
    upward = [r for r in mc_rows if r["dY"] > 0]
    no_family = [r for r in mc_rows if None in r["topo_families"] or not r["topo_families"]]
    R["scoped_exception"] = dict(
        n_moved_carried=len(mc_rows), n_hard_non_outliers_below_0p70=len(hard_not),
        n_in_0p70_0p80_soft_band=len(soft_band), n_failing_both_arms=len(no_arm),
        n_outside_mound=len(out_of_mound), n_inside_basin=len(in_basin), n_inside_guard_annulus=len(in_guard),
        n_with_non_terrain_entries=len(not_terrain), n_moved_upward=len(upward),
        n_without_a_ground_family=len(no_family),
        min_residual_before=min((r["residual_before"] for r in mc_rows if r["residual_before"] is not None),
                                default=None),
        arms=dict(Counter(r["arm"] for r in mc_rows)),
        verdict_rule="a moved carried position that was NOT a positive outlier (>= 0.8u above MY OWN "
                     "basin-excluded reference) or that passes NEITHER arm under MY OWN prominence/drop "
                     "arithmetic REFUTES the scoped carried exception.  0.70-0.80 under my estimator is an "
                     "estimator-difference margin (NOTE), not a refutation.")
    if hard_not:
        findings.append(f"REFUTE (2): {len(hard_not)} moved CARRIED positions were not positive outliers "
                        f"(<0.70u even with estimator slack): {[[r['pos'], r['residual_before']] for r in hard_not]}.")
    if soft_band:
        findings.append(f"NOTE (2): {len(soft_band)} moved carried positions land in the 0.70-0.80u band under MY "
                        f"estimator: {[[r['pos'], r['residual_before']] for r in soft_band]}.")
    if no_arm:
        findings.append(f"REFUTE (2): {len(no_arm)} moved CARRIED positions pass NEITHER census arm under my own "
                        f"shape arithmetic: {[[r['pos'], r['prominence_before'], r['drop_before']] for r in no_arm]}.")
    if out_of_mound:
        findings.append(f"REFUTE (2): {len(out_of_mound)} moved carried positions lie outside the {MOUND_R}u mound.")
    if in_basin:
        findings.append(f"REFUTE (4): {len(in_basin)} moved carried positions lie INSIDE the sacred basin disc.")
    if in_guard:
        findings.append(f"REFUTE (4): {len(in_guard)} moved positions lie inside the {GUARD_R}u guard annulus.")
    if not_terrain:
        findings.append(f"REFUTE (2): {len(not_terrain)} moved positions have entries outside Terrain.")
    if upward:
        findings.append(f"REFUTE (2): {len(upward)} carried spike(s) moved UPWARD: "
                        f"{[[r['pos'], r['dY']] for r in upward]}.")
    if no_family:
        findings.append(f"REFUTE (2): {len(no_family)} moved carried positions have no ground family (rock).")

    # --- fill moves: welded, Terrain-only, <=HOPS from a spike, <=FILL_CEIL ---
    spike_keys = set(moved_carried_ground)
    hop = {k: 0 for k in spike_keys}
    dq = deque(spike_keys)
    while dq:
        k = dq.popleft()
        if hop[k] >= HOPS: continue
        for n in pos_deg.get(k, ()):
            if n not in hop:
                hop[n] = hop[k] + 1; dq.append(n)
    mf_rows = []
    for k in moved_fill:
        ref, rad, n = surf.at(k[0], k[2], skip=(k,))
        mf_rows.append(dict(pos=[round(k[0], 3), round(yb[k], 3), round(k[2], 3)],
                            dY=round(yt[k] - yb[k], 4), r_crater=round(rcrater(k[0], k[2]), 3),
                            hops_from_a_spike=hop.get(k),
                            residual_before=None if ref is None else round(yb[k] - ref, 4),
                            residual_after=None if ref is None else round(yt[k] - ref, 4),
                            parts=sorted({e[2] for e in groups[k]})))
    far_fill = [r for r in mf_rows if r["hops_from_a_spike"] is None or r["hops_from_a_spike"] > HOPS]
    big_fill = [r for r in mf_rows if abs(r["dY"]) > FILL_CEIL]
    nonterr_fill = [r for r in mf_rows if r["parts"] != ["Terrain"]]
    R["moved_fill"] = dict(n=len(mf_rows), rows=sorted(mf_rows, key=lambda r: -abs(r["dY"])),
                           max_abs_dY=round(max((abs(r["dY"]) for r in mf_rows), default=0.0), 4),
                           min_r_crater=round(min((r["r_crater"] for r in mf_rows), default=0.0), 3),
                           n_beyond_2_hops=len(far_fill), n_over_ceiling=len(big_fill),
                           n_non_terrain=len(nonterr_fill))
    log(f"[2] moved fill n={len(mf_rows)} max|dY|={R['moved_fill']['max_abs_dY']} "
        f"hops={[r['hops_from_a_spike'] for r in mf_rows]}")
    if far_fill:
        findings.append(f"REFUTE (2): {len(far_fill)} moved fill positions are further than {HOPS} mesh hops "
                        f"from any spike: {far_fill[:4]}.")
    if big_fill:
        findings.append(f"REFUTE (2): {len(big_fill)} fill positions moved beyond the build's own {FILL_CEIL}u "
                        f"acceptance ceiling: {big_fill[:4]}.")
    if nonterr_fill:
        findings.append(f"REFUTE (2): {len(nonterr_fill)} moved fill positions have non-Terrain entries.")

    frozen_bad = [list(k) for k in carried_ground if k not in spike_keys and abs(dy_by_group.get(k, 0.0)) > 0]
    rock_bad_broad = [list(k) for k in carried_rock_touched if abs(dy_by_group.get(k, 0.0)) > 0]
    R["carried_freeze"] = dict(carried_ground_non_spike_moved=len(frozen_bad), examples=frozen_bad[:6],
                               carried_rock_moved_BROAD=len(rock_bad_broad), rock_examples=rock_bad_broad[:6],
                               carried_ground_total=len(carried_ground),
                               carried_rock_total_broad=len(carried_rock_touched))
    if frozen_bad:
        findings.append(f"REFUTE (2): {len(frozen_bad)} carried-ground positions outside the spike set moved.")
    if rock_bad_broad:
        findings.append(f"REFUTE (2): {len(rock_bad_broad)} rock-touched positions moved: {rock_bad_broad[:4]}.")

    # ================= (3) UV LANE =================
    uvlane = dict(uv_bytes_identical=(not chan["uv_bad"]), tangent_bytes_identical=(not chan["tan_bad"]))
    # (3a) degenerate UVs measured on the TARGET's own bytes
    deg_target = 0; deg_rows = []
    for (bx, by) in FOOTPRINT:
        if (bx, by, "Terrain") not in T: continue
        rt = T[(bx, by, "Terrain")]["rt"]; u = uvs_of(rt); idx = idx_of(rt)
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            if is_degenerate(*[u[j] for j in tri]):
                deg_target += 1
                if len(deg_rows) < 8: deg_rows.append([bx, by, t])
    uvlane["degenerate_uv_tris_on_target"] = deg_target
    uvlane["degenerate_examples"] = deg_rows
    if deg_target:
        findings.append(f"REFUTE (3/4): {deg_target} Terrain tris have DEGENERATE UVs on FIXED7's own bytes "
                        f"(the ONE-WINDOW-PER-TRI invariant): {deg_rows[:4]}.")

    # (3b) STOCK UV-WINDOW VOCABULARY re-derived from real stock bytes (NOT from any probe JSON)
    stock_rects = defaultdict(Counter); stock_err = None; stock_blocks_read = 0
    donor_tris = {}
    try:
        for (bx, by) in DUNES_BLOCKS + CLEYRA_BLOCKS:
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain")
            except (ValueError, FileNotFoundError, OSError) as exc:
                stock_err = repr(exc); continue
            stock_blocks_read += 1
            ox, oz = X.block_world_origin(bx, by)
            for ti, tri in enumerate(bm.tris):
                topo = X.decode_id(int(round(float(bm.tangents[tri[0]][0]))))["topograph"]
                us = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
                rect = (round(min(p[0] for p in us), 5), round(min(p[1] for p in us), 5),
                        round(max(p[0] for p in us), 5), round(max(p[1] for p in us), 5))
                stock_rects[topo][rect] += 1
                if (bx, by) in CLEYRA_BLOCKS:
                    w = [(bm.verts[j][0] + ox + SHIFT[0], float(bm.verts[j][1]),
                          bm.verts[j][2] + oz + SHIFT[1]) for j in tri]
                    key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in w))
                    donor_tris.setdefault(key, []).append(dict(block=[bx, by], tri=ti, topo=topo, rect=rect,
                                                               ys=[round(p[1], 4) for p in w], pts=w))
    except Exception as exc:  # noqa: BLE001
        stock_err = repr(exc)
    all_stock_rects = set()
    for topo, c in stock_rects.items(): all_stock_rects |= set(c)
    uvlane["stock_vocabulary"] = dict(blocks_read=stock_blocks_read, error=stock_err,
                                      n_distinct_rects=len(all_stock_rects),
                                      n_rects_by_topo={str(t): len(c) for t, c in sorted(stock_rects.items())},
                                      source_blocks=dict(dunes=DUNES_BLOCKS, cleyra=CLEYRA_BLOCKS))

    def rect_of(uv):
        return (round(min(p[0] for p in uv), 5), round(min(p[1] for p in uv), 5),
                round(max(p[0] for p in uv), 5), round(max(p[1] for p in uv), 5))

    # every RE-POSED face (the 12 tris with a moved vertex) is sampled against the stock vocabulary
    reposed = []
    for r in tris:
        if not r["moved"]: continue
        rc = rect_of(r["uv"])
        reposed.append(dict(block=list(r["b"]), tri=r["t"], synth=r["synth"], topo=r["topo"],
                            rect=list(rc), in_stock_vocabulary=rc in all_stock_rects,
                            in_same_topo_vocabulary=rc in stock_rects.get(r["topo"], {}),
                            stock_occurrences_same_topo=int(stock_rects.get(r["topo"], {}).get(rc, 0)),
                            stock_rank_within_topo=(
                                [k for k, _ in stock_rects[r["topo"]].most_common()].index(rc) + 1
                                if rc in stock_rects.get(r["topo"], {}) else None),
                            n_windows_for_topo=len(stock_rects.get(r["topo"], {})),
                            uv_area=round(uv_area(*r["uv"]), 8)))
    kept_reposed = [r for r in reposed if not r["synth"]]
    kept_off_vocab = [r for r in kept_reposed if not r["in_stock_vocabulary"]]
    uvlane["reposed_faces"] = dict(n=len(reposed), n_kept=len(kept_reposed), rows=reposed,
                                   n_kept_off_stock_vocabulary=len(kept_off_vocab),
                                   note="no UV byte changed this round, so this lane cannot fail on a re-dress; "
                                        "it instead certifies that the faces the round RE-POSES still wear a "
                                        "genuine stock UV window re-derived from stock bytes.")
    if chan["uv_bad"]:
        findings.append("REFUTE (3): UV bytes changed although the round declares a geometry-only lever -- "
                        "every re-dressed face would need stock-rect justification.")
    if kept_off_vocab:
        findings.append(f"NOTE (3): {len(kept_off_vocab)} re-posed CARRIED face(s) wear a UV window not present "
                        f"in my stock sample (dunes mass + Cleyra junction): "
                        f"{[[r['block'], r['tri'], r['rect']] for r in kept_off_vocab[:4]]} -- carried bytes are "
                        f"unchanged, so this is a vocabulary-coverage note, not a breach.")

    # (3c) TEXEL STRETCH -- the smear the diagnosis blamed, measured before and after
    stretch_rows = []
    for r in tris:
        if not r["moved"]: continue
        ua = uv_area(*r["uv"])
        ab = tri_area3(*r["wb"]); at = tri_area3(*r["wt"])
        planb = abs((r["wb"][1][0] - r["wb"][0][0]) * (r["wb"][2][2] - r["wb"][0][2]) -
                    (r["wb"][2][0] - r["wb"][0][0]) * (r["wb"][1][2] - r["wb"][0][2])) / 2.0
        stretch_rows.append(dict(block=list(r["b"]), tri=r["t"], synth=r["synth"],
                                 uv_area=round(ua, 8),
                                 area3d_before=round(ab, 5), area3d_after=round(at, 5),
                                 plan_area=round(planb, 5),
                                 stretch_before=round(ab / planb, 4) if planb > 1e-9 else None,
                                 stretch_after=round(at / planb, 4) if planb > 1e-9 else None))
    sb = [r["stretch_before"] for r in stretch_rows if r["stretch_before"]]
    sa = [r["stretch_after"] for r in stretch_rows if r["stretch_after"]]
    uvlane["texel_stretch_on_reposed_faces"] = dict(
        rows=sorted(stretch_rows, key=lambda r: -(r["stretch_before"] or 0)),
        stretch_before=stats(sb), stretch_after=stats(sa),
        definition="stretch = 3D face area / its XZ-plan area.  UVs are plan-projected, so this ratio IS the "
                   "texture magnification of the face; 1.0 = no smear.  A geometry-only fix reduces it without "
                   "touching a UV byte.")
    if sa and sb and max(sa) > max(sb) + 1e-6:
        findings.append(f"REFUTE (3): the worst texel stretch on the re-posed faces GREW {max(sb)} -> {max(sa)} "
                        f"-- the geometry lever made the smear worse.")
    R["uv_lane"] = uvlane
    log(f"[3] uv identical={uvlane['uv_bytes_identical']} degenerate_on_target={deg_target} "
        f"stock_rects={len(all_stock_rects)} kept_off_vocab={len(kept_off_vocab)} "
        f"stretch max {max(sb) if sb else None} -> {max(sa) if sa else None}")

    # ================= (4) crack / facing / area / land>0 =================
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
    cb, ob, pb_ = once_edges_plan("wb")
    ct, ot, pt_ = once_edges_plan("wt")
    plan_new = {k: v for k, v in (pt_ - pb_).items()}
    R["crack_audit"] = dict(n_edges_before=len(cb), n_edges_after=len(ct),
                            once_edges_before=len(ob), once_edges_after=len(ot),
                            new_open_edges_in_PLAN=len(plan_new),
                            plan_examples=[[list(k[0]), list(k[1]), v] for k, v in list(plan_new.items())[:6]],
                            note="the XZ-plan projection of the once-edge set is Y-move-invariant; a split weld "
                                 "or a dropped tri appears there as a NEW open plan edge.")
    if plan_new:
        findings.append(f"REFUTE (4): {len(plan_new)} NEW open edges in the XZ-plan once-edge audit (a crack).")

    nyb = Counter(); nyt = Counter(); flipped = []; newdown = []; zab = zat = 0
    for r in tris:
        gb = geo_normal(*r["wb"]); gt = geo_normal(*r["wt"])
        s1 = 0 if abs(gb[1]) < 1e-12 else (1 if gb[1] > 0 else -1)
        s2 = 0 if abs(gt[1]) < 1e-12 else (1 if gt[1] > 0 else -1)
        nyb[s1] += 1; nyt[s2] += 1
        if s1 != s2: flipped.append([list(r["b"]), r["t"], s1, s2])
        if s2 < 0 and s1 >= 0: newdown.append([list(r["b"]), r["t"]])
        if math.sqrt(sum(c * c for c in gb)) < 1e-9: zab += 1
        if math.sqrt(sum(c * c for c in gt)) < 1e-9: zat += 1
    ysb_all = [p[1] for r in tris for p in r["wb"]]
    yst_all = [p[1] for r in tris for p in r["wt"]]
    sank = [[list(r["b"]), r["t"], round(p[1], 4), round(q[1], 4)]
            for r in tris for p, q in zip(r["wb"], r["wt"]) if p[1] > SEA_Y and q[1] <= SEA_Y]
    moved_yt = [yt[k] for k in moved_keys]
    R["geometry_gates"] = dict(ny_sign_before=dict(nyb), ny_sign_after=dict(nyt), tris_flipped=len(flipped),
                               newly_down_facing=len(newdown), zero_world_area_before=zab,
                               zero_world_area_after=zat, min_Y_all_terrain_before=round(min(ysb_all), 6),
                               min_Y_all_terrain_after=round(min(yst_all), 6),
                               min_Y_over_moved_positions=round(min(moved_yt), 5) if moved_yt else None,
                               verts_that_sank_to_or_below_sea=len(sank))
    log(f"[4] facing {dict(nyb)}->{dict(nyt)} flipped={len(flipped)} newdown={len(newdown)} "
        f"zeroarea {zab}->{zat} minY_moved={R['geometry_gates']['min_Y_over_moved_positions']} sank={len(sank)}")
    if newdown: findings.append(f"REFUTE (4): {len(newdown)} tris became DOWN-FACING.")
    if flipped: findings.append(f"REFUTE (4): {len(flipped)} tris changed geometric facing sign.")
    if zat > zab: findings.append(f"REFUTE (4): zero-world-area tris grew {zab} -> {zat}.")
    if sank: findings.append(f"REFUTE (4): {len(sank)} land vertices sank to or below sea Y=0.")

    # ================= (4) THE BASIN DISC =================
    disc_keys = [k for k in groups if rcrater(k[0], k[2]) <= BASIN_R and any(e[2] == "Terrain" for e in groups[k])]
    disc_moved = [[list(k), round(dy_by_group[k], 6)] for k in disc_keys if abs(dy_by_group[k]) > 0]
    disc_bytes_changed = 0; disc_entries = 0
    for k in disc_keys:
        for (bx, by, part, j) in groups[k]:
            D = T[(bx, by, part)]; rb, rt = D["rb"], D["rt"]
            ob = rb["off_pos"] + j * 12; ot = rt["off_pos"] + j * 12
            disc_entries += 1
            if rb["data"][ob:ob + 12] != rt["data"][ot:ot + 12]: disc_bytes_changed += 1
    guard_moved = [list(k) for k in moved_keys if rcrater(k[0], k[2]) <= GUARD_R]
    rim_keys = [k for k in groups if BASIN_R < rcrater(k[0], k[2]) <= BASIN_R + 6.0
                and any(e[2] == "Terrain" for e in groups[k])]
    rim_frozen = [k for k in rim_keys if k not in set(moved_keys)]
    floorb = [yb[k] for k in disc_keys]; floort = [yt[k] for k in disc_keys]
    rimb = [yb[k] for k in rim_frozen]; rimt = [yt[k] for k in rim_frozen]
    depth_b = (statistics.fmean(rimb) - statistics.fmean(floorb)) if rimb and floorb else None
    depth_t = (statistics.fmean(rimt) - statistics.fmean(floort)) if rimt and floort else None
    R["basin"] = dict(centre=list(BASIN_C), radius=BASIN_R, guard_radius=GUARD_R,
                      n_terrain_positions_in_disc=len(disc_keys), n_vertex_entries_in_disc=disc_entries,
                      positions_moved=len(disc_moved), vertex_bytes_changed_in_disc=disc_bytes_changed,
                      guard_annulus_positions_moved=len(guard_moved),
                      floor_y_before=stats(floorb), floor_y_after=stats(floort),
                      n_rim_band_positions=len(rim_keys), n_rim_band_frozen=len(rim_frozen),
                      depth_before=None if depth_b is None else round(depth_b, 4),
                      depth_after=None if depth_t is None else round(depth_t, 4),
                      min_r_crater_of_a_moved_position=round(min((rcrater(k[0], k[2]) for k in moved_keys),
                                                                 default=float("inf")), 4))
    log(f"[4] basin: positions={len(disc_keys)} entries={disc_entries} moved={len(disc_moved)} "
        f"bytes_changed={disc_bytes_changed} guard_moved={len(guard_moved)} "
        f"min_r_moved={R['basin']['min_r_crater_of_a_moved_position']}")
    if disc_moved: findings.append(f"REFUTE (4): {len(disc_moved)} positions inside the sacred basin disc moved.")
    if disc_bytes_changed:
        findings.append(f"REFUTE (4): {disc_bytes_changed} vertex BYTES inside the basin disc changed.")
    if guard_moved:
        findings.append(f"REFUTE (4): {len(guard_moved)} positions inside the {GUARD_R}u guard annulus moved.")
    if depth_b is not None and depth_t < depth_b - 1e-4:
        findings.append(f"REFUTE (4): the crater got SHALLOWER ({round(depth_b,4)} -> {round(depth_t,4)}).")

    # the mound's carried height multiset outside the moved set
    mset = set(moved_keys); mound_before = []; mound_after = []
    for k in groups:
        if rcrater(k[0], k[2]) > MOUND_R: continue
        if k not in carried_ground and k not in carried_rock_touched: continue
        if k in mset: continue
        for _ in groups[k]:
            mound_before.append(yb[k]); mound_after.append(yt[k])
    identical = sorted(mound_before) == sorted(mound_after)
    R["rim_distribution"] = dict(n_carried_entries_in_mound_excluding_moved=len(mound_before),
                                 multiset_identical=identical,
                                 entries_differing=sum(1 for x, y_ in zip(mound_before, mound_after) if x != y_),
                                 before=stats(mound_before), after=stats(mound_after))
    if not identical:
        findings.append("REFUTE (4): the mound's carried height distribution changed outside the moved set.")

    # ================= (4) PRIOR-FIX REGRESSION, sets re-derived from the OLD TREES =================
    prior = {}
    r6_keys = []; r5_keys = []
    if ent5:
        for k, ents in groups.items():
            if any(e in ent5 and abs(ent5[e] - entb[e][1]) > 0 for e in ents): r6_keys.append(k)
    if ent4 and ent5:
        r5_moved_entries = set()
        for k, ents in groups.items():
            if any(e in ent4 and e in ent5 and abs(ent4[e] - ent5[e]) > 0 for e in ents): r5_keys.append(k)
            for e in ents:
                if e in ent4 and e in ent5 and abs(ent4[e] - ent5[e]) > 0: r5_moved_entries.add(e)
    r6_carried = [k for k in r6_keys if k in carried_ground]
    r6_fill = [k for k in r6_keys if k in fill]
    r6_rows = []
    for k in r6_carried:
        prom_t, drop_t, slope_t, ring_t = shape(k, yt)
        by_ = all(T[(e[0], e[1], e[2])]["rb"]["data"][T[(e[0], e[1], e[2])]["rb"]["off_pos"] + e[3] * 12:
                                                      T[(e[0], e[1], e[2])]["rb"]["off_pos"] + e[3] * 12 + 12] ==
                  T[(e[0], e[1], e[2])]["rt"]["data"][T[(e[0], e[1], e[2])]["rt"]["off_pos"] + e[3] * 12:
                                                      T[(e[0], e[1], e[2])]["rt"]["off_pos"] + e[3] * 12 + 12]
                  for e in groups[k])
        ref6, _, _ = surf.at(k[0], k[2], skip=(k,))
        r6_rows.append(dict(pos=[round(k[0], 3), round(yb[k], 3), round(k[2], 3)],
                            y_in_base=round(yb[k], 6), y_in_target=round(yt[k], 6),
                            byte_identical=bool(by_), moved_this_round=bool(abs(dy_by_group[k]) > 0),
                            prominence_now=None if prom_t is None else round(prom_t, 4),
                            below_its_ring=None if prom_t is None else bool(prom_t <= 0.0),
                            residual_now=None if ref6 is None else round(yt[k] - ref6, 4),
                            arm_now=arm_of(prom_t, drop_t),
                            r_crater=round(rcrater(k[0], k[2]), 3)))
    bad6 = [r for r in r6_rows if not r["byte_identical"]]
    above6 = [r for r in r6_rows if r["below_its_ring"] is False]
    prior["round6"] = dict(derivation="MY byte diff FIXED5 -> FIXED6 (no report read)",
                           n_positions_moved_by_round6=len(r6_keys), n_carried=len(r6_carried),
                           n_fill=len(r6_fill), rows=r6_rows,
                           n_not_byte_identical_now=len(bad6), n_still_above_their_ring=len(above6))
    if len(r6_carried) != 4:
        findings.append(f"MISMATCH (4): my FIXED5->FIXED6 diff yields {len(r6_carried)} moved carried positions, "
                        f"round 6 claimed 4 apexes.")
    if bad6:
        findings.append(f"REFUTE (4): {len(bad6)} of round 6's shaved apexes were re-written this round: "
                        f"{[r['pos'] for r in bad6]}.")
    if above6:
        findings.append(f"REFUTE (4): {len(above6)} of round 6's shaved apexes are ABOVE their ring again: "
                        f"{[[r['pos'], r['prominence_now']] for r in above6]}.")

    r5_rows = []
    r5_changed_now = []
    for k in r5_keys:
        if abs(dy_by_group.get(k, 0.0)) > 0: r5_changed_now.append([list(k), round(dy_by_group[k], 5)])
    resb5 = []; rest5 = []
    for k in r5_keys:
        ref, _, _ = surf.at(k[0], k[2], skip=(k,))
        if ref is None: continue
        resb5.append(yb[k] - ref); rest5.append(yt[k] - ref)
    fill_resb = []; fill_rest = []
    for k in fill:
        ref, _, _ = surf.at(k[0], k[2], skip=(k,))
        if ref is None: continue
        fill_resb.append(yb[k] - ref); fill_rest.append(yt[k] - ref)
    mound_tris_dip_b = []; mound_tris_dip_t = []
    for r in tris:
        cx = statistics.fmean([p[0] for p in r["wb"]]); cz = statistics.fmean([p[2] for p in r["wb"]])
        if rcrater(cx, cz) > MOUND_R: continue
        for which, acc in (("wb", mound_tris_dip_b), ("wt", mound_tris_dip_t)):
            g = geo_normal(*r[which]); L = math.sqrt(sum(c * c for c in g))
            if L > 1e-12: acc.append(math.degrees(math.acos(max(-1.0, min(1.0, abs(g[1]) / L)))))
    prior["round5"] = dict(derivation="MY byte diff FIXED4 -> FIXED5 (no report read)",
                           n_positions_moved_by_round5=len(r5_keys),
                           n_of_them_changed_again_this_round=len(r5_changed_now),
                           changed_again=r5_changed_now[:8],
                           residuals_over_the_round5_set_before=stats(resb5),
                           residuals_over_the_round5_set_after=stats(rest5),
                           fill_residuals_before=stats(fill_resb), fill_residuals_after=stats(fill_rest),
                           fill_residual_distribution_unchanged=(stats(fill_resb) == stats(fill_rest)),
                           mound_tris_dip_ge45_before=sum(1 for v in mound_tris_dip_b if v >= 45.0),
                           mound_tris_dip_ge45_after=sum(1 for v in mound_tris_dip_t if v >= 45.0),
                           mound_tris_yspan_ge1_before=sum(
                               1 for r in tris
                               if rcrater(statistics.fmean([p[0] for p in r["wb"]]),
                                          statistics.fmean([p[2] for p in r["wb"]])) <= MOUND_R
                               and (max(p[1] for p in r["wb"]) - min(p[1] for p in r["wb"])) >= 1.0),
                           mound_tris_yspan_ge1_after=sum(
                               1 for r in tris
                               if rcrater(statistics.fmean([p[0] for p in r["wt"]]),
                                          statistics.fmean([p[2] for p in r["wt"]])) <= MOUND_R
                               and (max(p[1] for p in r["wt"]) - min(p[1] for p in r["wt"])) >= 1.0))
    P5 = prior["round5"]
    if P5["mound_tris_dip_ge45_after"] > P5["mound_tris_dip_ge45_before"]:
        findings.append(f"REFUTE (4): steep mound faces (dip>=45) GREW {P5['mound_tris_dip_ge45_before']} -> "
                        f"{P5['mound_tris_dip_ge45_after']} -- round 5's crevice seal re-opened.")
    if len(r5_changed_now) > len(moved_keys):
        findings.append(f"REFUTE (4): {len(r5_changed_now)} of round 5's relaxed positions changed again, more "
                        f"than this round's entire moved set.")
    R["prior_fixes"] = prior
    log(f"[4] prior: round6 carried={len(r6_carried)} byte_bad={len(bad6)} above_ring={len(above6)}; "
        f"round5 set={len(r5_keys)} changed_again={len(r5_changed_now)} dip>=45 "
        f"{P5['mound_tris_dip_ge45_before']}->{P5['mound_tris_dip_ge45_after']}")

    # ================= (5) POST-MOVE BAND =================
    band_rows = []
    for row, k in zip(mc_rows, moved_carried_ground):
        ref = row["my_reference"]
        prom_a, drop_a, slope_a, ring_a = shape(k, yt)
        lo, hi, ne = surf.envelope(k[0], k[2], 12.0, skip=(k,))
        y_a = row["y_after"]
        band_rows.append(dict(
            pos=row["pos"], y_before=row["y_before"], y_after=y_a, reference=ref,
            below_reference_by=None if ref is None else round(max(0.0, ref - y_a), 4),
            between_old_and_reference=None if ref is None else (min(row["y_before"], ref) - 1e-3 <= y_a <=
                                                                max(row["y_before"], ref) + 1e-3),
            prominence_after=None if prom_a is None else round(prom_a, 4),
            still_local_max=None if prom_a is None else bool(prom_a > 0),
            new_local_min=None if not ring_a else bool(y_a < min(ring_a) - 1e-6),
            drop_after=None if drop_a is None else round(drop_a, 4),
            slope_after_deg=None if slope_a is None else round(slope_a, 3),
            step_collapsed=None if drop_a is None else bool(drop_a < row["drop_before"]),
            arm_after=arm_of(prom_a, drop_a),
            kept_envelope_r12=[None if lo is None else round(lo, 3), None if hi is None else round(hi, 3)],
            inside_kept_envelope=None if lo is None else bool(lo - 0.05 <= y_a <= hi + 0.05)))
    overshoot = [r for r in band_rows if r["below_reference_by"] and r["below_reference_by"] > 0.15]
    outside_band = [r for r in band_rows if r["between_old_and_reference"] is False]
    still_max = [r for r in band_rows if r["still_local_max"]]
    new_min = [r for r in band_rows if r["new_local_min"]]
    R["post_move_band"] = dict(rows=band_rows, n_overshoot_gt_0p15=len(overshoot),
                               n_outside_old_to_reference=len(outside_band), n_still_local_max=len(still_max),
                               n_new_local_min=len(new_min))
    log(f"[5] band: overshoot={len(overshoot)} outside={len(outside_band)} still_max={len(still_max)} "
        f"new_min={len(new_min)}")
    if overshoot:
        findings.append(f"REFUTE (5): {len(overshoot)} shaved crests overshoot BELOW my own reference by >0.15u: "
                        f"{[[r['pos'], r['below_reference_by']] for r in overshoot]}.")
    if outside_band:
        findings.append(f"REFUTE (5): {len(outside_band)} shaved crests land outside the [old Y, reference] "
                        f"interval.")
    if new_min:
        findings.append(f"REFUTE (5): {len(new_min)} shaved crests became a new local MINIMUM (a pit).")
    if still_max:
        findings.append(f"NOTE (5): {len(still_max)} shaved crests are still a local maximum.")

    # ================= (6) REFUTATION HUNT =================
    hunt = {}
    samplest = [(k[0], k[2], yt[k], k) for k in carried_ground] + [(k[0], k[2], yt[k], k) for k in fill]
    surft = Surface(samplest, exclude_basin=True)

    def census(ymap, sfc, keys, mound_only=True):
        rows = []
        for k in keys:
            rr = rcrater(k[0], k[2])
            if rr <= BASIN_R: continue
            if mound_only and rr > MOUND_R: continue
            ref, rad, n = sfc.at(k[0], k[2], skip=(k,))
            if ref is None: continue
            res = ymap[k] - ref
            prom, drop, slope, ring = shape(k, ymap)
            arm = arm_of(prom, drop)
            rows.append(dict(pos=[round(k[0], 3), round(ymap[k], 3), round(k[2], 3)],
                             res=round(res, 4), prom=None if prom is None else round(prom, 4),
                             drop=None if drop is None else round(drop, 4),
                             slope=None if slope is None else round(slope, 2),
                             arm=arm, r=round(rr, 2), topo=sorted(pos_kept_ground.get(k, set())),
                             qual=bool(res >= OUTLIER_U and arm is not None)))
        return rows
    cen_b = census(yb, surf, carried_ground)
    cen_t = census(yt, surft, carried_ground)
    qb = [r for r in cen_b if r["qual"]]; qt = [r for r in cen_t if r["qual"]]
    moved_xz = {(round(k[0], 3), round(k[2], 3)) for k in moved_carried_ground}
    unmoved_q = [r for r in qb if (r["pos"][0], r["pos"][2]) not in moved_xz]
    hunt["self_termination"] = dict(
        n_carried_ground_in_mound=len(cen_b), qualifiers_on_base=len(qb), qualifiers_on_target=len(qt),
        qualifier_rows_base=sorted(qb, key=lambda r: -r["res"]),
        qualifier_rows_target=sorted(qt, key=lambda r: -r["res"])[:8],
        qualifiers_on_base_not_moved=unmoved_q,
        max_residual_base=round(max((r["res"] for r in cen_b), default=0.0), 4),
        max_residual_target=round(max((r["res"] for r in cen_t), default=0.0), 4),
        top_remaining_by_residual=sorted(cen_t, key=lambda r: -r["res"])[:5],
        top_remaining_by_drop=sorted([r for r in cen_t if r["drop"] is not None],
                                     key=lambda r: -r["drop"])[:5],
        note="MY OWN round-7 rule, re-derived from each tree's own bytes with each tree's own reference.")
    log(f"[6] self-termination: qualifiers {len(qb)} -> {len(qt)}; max res "
        f"{hunt['self_termination']['max_residual_base']} -> {hunt['self_termination']['max_residual_target']}")
    if qt:
        findings.append(f"NOTE (6): {len(qt)} carried positions still qualify under MY census after the shave: "
                        f"{qt[:3]} -- an under-shave under my estimator, not a contract breach.")
    if unmoved_q:
        findings.append(f"NOTE (6): {len(unmoved_q)} positions qualify under MY pre-move census but were not "
                        f"moved: {unmoved_q[:4]}.")

    # 6b: THE STEP-ARM BLAST RADIUS -- how close the widened rule comes to the sacred rim
    arm_pass = [r for r in cen_b if r["arm"] is not None]
    crest = [k for k in carried_ground if abs(yb[k] - 6.208) < 5e-3 and rcrater(k[0], k[2]) <= 12.0]
    crest_rows = []
    for k in crest:
        ref, _, _ = surf.at(k[0], k[2], skip=(k,))
        refb, _, _ = surf_withbasin.at(k[0], k[2], skip=(k,))
        prom, drop, slope, ring = shape(k, yb)
        crest_rows.append(dict(pos=[round(k[0], 3), round(yb[k], 3), round(k[2], 3)],
                               r=round(rcrater(k[0], k[2]), 2),
                               res_basin_excluded=None if ref is None else round(yb[k] - ref, 4),
                               res_basin_sampled=None if refb is None else round(yb[k] - refb, 4),
                               prom=None if prom is None else round(prom, 4),
                               drop=None if drop is None else round(drop, 4),
                               arm=arm_of(prom, drop),
                               qualifies_excluded=bool(ref is not None and yb[k] - ref >= OUTLIER_U
                                                       and arm_of(prom, drop) is not None),
                               qualifies_sampled=bool(refb is not None and yb[k] - refb >= OUTLIER_U
                                                      and arm_of(prom, drop) is not None)))
    crest_res = [r["res_basin_excluded"] for r in crest_rows if r["res_basin_excluded"] is not None]
    crest_arm = [r for r in crest_rows if r["arm"] is not None]
    crest_qual = [r for r in crest_rows if r["qualifies_excluded"]]
    crest_qual_sampled = [r for r in crest_rows if r["qualifies_sampled"]]
    hunt["step_arm_blast_radius"] = dict(
        n_carried_in_mound=len(cen_b), n_passing_an_arm=len(arm_pass),
        arm_hist=dict(Counter(r["arm"] for r in arm_pass)),
        n_passing_an_arm_but_stopped_by_the_residual_gate=len([r for r in arm_pass if not r["qual"]]),
        max_residual_among_arm_passers_that_did_not_qualify=round(
            max((r["res"] for r in arm_pass if not r["qual"]), default=0.0), 4),
        crest_ring=dict(n=len(crest_rows), rows=sorted(crest_rows, key=lambda r: -(r["res_basin_excluded"] or -9)),
                        residual_basin_excluded=stats(crest_res),
                        n_passing_an_arm=len(crest_arm), n_qualifying_basin_excluded=len(crest_qual),
                        n_qualifying_if_basin_were_SAMPLED=len(crest_qual_sampled),
                        max_residual=round(max(crest_res), 4) if crest_res else None,
                        clearance_under_the_gate=round(OUTLIER_U - max(crest_res), 4) if crest_res else None),
        reading="the widened predicate (3) no longer protects the crater's own rim crest by SHAPE; only the "
                "0.80u residual gate does, and that gate only holds because the basin is excluded from the "
                "reference SAMPLES.  This lane measures the surviving clearance under an estimator that is not "
                "the build's.")
    BR = hunt["step_arm_blast_radius"]
    log(f"[6] blast radius: arm passers={len(arm_pass)} crest n={len(crest_rows)} arm={len(crest_arm)} "
        f"qual_excluded={len(crest_qual)} qual_if_sampled={len(crest_qual_sampled)} "
        f"clearance={BR['crest_ring']['clearance_under_the_gate']}")
    if crest_qual:
        findings.append(f"REFUTE (6): under MY estimator {len(crest_qual)} CRATER-RIM CREST vertices qualify "
                        f"under the round's own widened rule -- the rule as stated would shave the sacred "
                        f"feature: {[r['pos'] for r in crest_qual[:4]]}.")
    if crest_res and (OUTLIER_U - max(crest_res)) < 0.05:
        findings.append(f"NOTE (6): the rim crest clears the residual gate by only "
                        f"{round(OUTLIER_U - max(crest_res), 4)}u under MY estimator -- thinner than the "
                        f"build's own 0.1426u margin.")

    # 6b2: WHICH PREDICATE IS ACTUALLY DOING THE WORK on the post-shave tree.  A rule that terminates
    # because of ONE predicate with a thin margin is a different safety story from one that terminates
    # on several.  For every carried position in the mound on FIXED7 I record which predicates fail and
    # by how much, and list those excluded by exactly ONE.
    one_away = []
    for r in cen_t:
        f_res = r["res"] < OUTLIER_U
        f_arm = r["arm"] is None
        if f_res == f_arm:      # both fail (comfortable) or neither (it qualifies)
            continue
        row = dict(pos=r["pos"], r=r["r"], topo=r["topo"], res=r["res"], prom=r["prom"], drop=r["drop"],
                   excluded_by="residual-gate-only" if f_res else "arm-only")
        if f_res:
            row["residual_short_by"] = round(OUTLIER_U - r["res"], 4)
        else:
            row["prominence_short_by"] = None if r["prom"] is None else round(max(0.0, STEP_PROM - r["prom"]), 4)
            row["drop_short_by"] = None if r["drop"] is None else round(max(0.0, STEP_DROP - r["drop"]), 4)
            row["cone_short_by"] = None if r["prom"] is None else round(max(0.0, CONE_PROM - r["prom"]), 4)
        one_away.append(row)
    one_away.sort(key=lambda r: (r["excluded_by"], r.get("residual_short_by", 0) or 0))
    hunt["single_predicate_margins"] = dict(
        n_one_predicate_away=len(one_away), rows=one_away,
        thinnest_arm_only=min((r for r in one_away if r["excluded_by"] == "arm-only"),
                              key=lambda r: min(x for x in (r.get("drop_short_by"), r.get("prominence_short_by"))
                                                if x is not None), default=None),
        thinnest_residual_only=min((r for r in one_away if r["excluded_by"] == "residual-gate-only"),
                                   key=lambda r: r["residual_short_by"], default=None),
        reading="rows excluded by the RESIDUAL GATE ALONE would enter the census if the reference moved; rows "
                "excluded by the ARM ALONE would enter if a future round loosened predicate (3) again.  These "
                "are the doors round 7's widening leaves ajar, measured under MY estimator on FIXED7.")
    SPM = hunt["single_predicate_margins"]
    log(f"[6] single-predicate margins: {len(one_away)} one-predicate-away "
        f"(arm-only {sum(1 for r in one_away if r['excluded_by']=='arm-only')}, "
        f"residual-only {sum(1 for r in one_away if r['excluded_by']=='residual-gate-only')})")
    if SPM["thinnest_residual_only"]:
        findings.append(f"NOTE (6): {sum(1 for r in one_away if r['excluded_by']=='residual-gate-only')} carried "
                        f"position(s) on FIXED7 pass an ARM and are held out by the residual gate alone, the "
                        f"thinnest by {SPM['thinnest_residual_only']['residual_short_by']}u "
                        f"({SPM['thinnest_residual_only']['pos']}).")
    if SPM["thinnest_arm_only"]:
        ta = SPM["thinnest_arm_only"]
        findings.append(f"NOTE (6): {sum(1 for r in one_away if r['excluded_by']=='arm-only')} carried "
                        f"position(s) on FIXED7 clear the 0.80u residual gate under MY estimator and are held "
                        f"out by predicate (3) ALONE -- thinnest {ta['pos']} res {ta['res']}, prominence short "
                        f"by {ta.get('prominence_short_by')}u / drop short by {ta.get('drop_short_by')}u.")

    # 6c: THE BASIN REFERENCE TRAP -- reproduce independently
    trap_wo = [r["res_basin_excluded"] for r in crest_rows if r["res_basin_excluded"] is not None]
    trap_w = [r["res_basin_sampled"] for r in crest_rows if r["res_basin_sampled"] is not None]
    hunt["basin_reference_trap"] = dict(
        rim_ring_n=len(crest_rows), residual_basin_EXCLUDED=stats(trap_wo), residual_basin_SAMPLED=stats(trap_w),
        qualifying_at_0p8_basin_EXCLUDED=sum(1 for v in trap_wo if v >= OUTLIER_U),
        qualifying_at_0p8_basin_SAMPLED=sum(1 for v in trap_w if v >= OUTLIER_U),
        reproduced=bool(sum(1 for v in trap_w if v >= OUTLIER_U) > sum(1 for v in trap_wo if v >= OUTLIER_U)))

    # 6d: new spikes anywhere
    def all_shape(ymap):
        out = {}
        for k in groups:
            if not any(e[2] == "Terrain" for e in groups[k]): continue
            p, d, s, ring = shape(k, ymap)
            if p is not None: out[k] = p
        return out
    prb = all_shape(yb); prt = all_shape(yt)
    grew = sorted(((prt[k] - prb[k], k) for k in prb if k in prt and prt[k] - prb[k] > 1e-6), reverse=True)
    newpeaks = [[list(k), round(prb[k], 4), round(prt[k], 4)] for k in prb if k in prt and prb[k] <= 0 < prt[k]]
    hunt["new_spikes"] = dict(n_positions=len(prb), prominence_before=stats(list(prb.values())),
                              prominence_after=stats(list(prt.values())), n_prominence_grew=len(grew),
                              worst_growth=[[list(k), round(d, 4), round(prb[k], 4), round(prt[k], 4)]
                                            for d, k in grew[:8]],
                              n_became_local_max=len(newpeaks), became_local_max=newpeaks[:8],
                              max_prominence_before=round(max(prb.values()), 4),
                              max_prominence_after=round(max(prt.values()), 4))
    if hunt["new_spikes"]["max_prominence_after"] > hunt["new_spikes"]["max_prominence_before"] + 1e-6:
        findings.append(f"REFUTE (6): the island's WORST prominence GREW "
                        f"{hunt['new_spikes']['max_prominence_before']} -> "
                        f"{hunt['new_spikes']['max_prominence_after']}.")
    if newpeaks:
        findings.append(f"NOTE (6): {len(newpeaks)} positions became local maxima (a shaved crest's own ring "
                        f"inheriting the high spot is expected): {newpeaks[:4]}.")

    # 6e: normals -- scope + geometry
    nrm_scope_bad = []; nrm_geo_bad = []; nrm_down = []; min_ny = 2.0; max_ang = 0.0
    n_rw_tris = 0; n_rw_entries = 0; n_rw_kept = 0; turn = []
    for r in tris:
        chg = any(x != y_ for x, y_ in zip(r["nb"], r["nt"]))
        if chg:
            n_rw_tris += 1
            n_rw_entries += sum(1 for x, y_ in zip(r["nb"], r["nt"]) if x != y_)
            if not r["synth"]: n_rw_kept += 1
            for x, y_ in zip(r["nb"], r["nt"]):
                lx = math.sqrt(sum(c * c for c in x)); ly = math.sqrt(sum(c * c for c in y_))
                if lx > 1e-9 and ly > 1e-9:
                    d = max(-1.0, min(1.0, sum(p * q for p, q in zip(x, y_)) / (lx * ly)))
                    turn.append(math.degrees(math.acos(d)))
        if chg and not r["moved"]: nrm_scope_bad.append([list(r["b"]), r["t"]])
        if not r["moved"]: continue
        g = geo_normal(*r["wt"]); L = math.sqrt(sum(c * c for c in g))
        if L < 1e-12: continue
        gn = [c / L for c in g]
        if gn[1] < 0: gn = [-c for c in gn]
        for st in r["nt"]:
            ls = math.sqrt(sum(c * c for c in st))
            if ls < 1e-9: nrm_geo_bad.append([list(r["b"]), r["t"], "zero-length"]); continue
            sn = [c / ls for c in st]
            dot = max(-1.0, min(1.0, sum(x * y_ for x, y_ in zip(sn, gn))))
            ang = math.degrees(math.acos(dot)); max_ang = max(max_ang, ang)
            if ang > 0.5: nrm_geo_bad.append([list(r["b"]), r["t"], round(ang, 4)])
            min_ny = min(min_ny, sn[1])
            if sn[1] < 0: nrm_down.append([list(r["b"]), r["t"], round(sn[1], 5)])
    hunt["normals"] = dict(tris_rewritten=n_rw_tris, entries_rewritten=n_rw_entries, of_which_KEPT=n_rw_kept,
                           rewritten_on_UNMOVED_tri=len(nrm_scope_bad), scope_examples=nrm_scope_bad[:8],
                           max_angle_vs_geometric_deg=round(max_ang, 5), non_geometric=len(nrm_geo_bad),
                           non_geometric_examples=nrm_geo_bad[:8], min_stored_ny_on_moved=round(min_ny, 6),
                           down_facing_stored=len(nrm_down), normal_turn_deg=stats(turn))
    log(f"[6] normals: tris={n_rw_tris} (kept {n_rw_kept}) entries={n_rw_entries} scope_bad={len(nrm_scope_bad)} "
        f"max_ang={max_ang:.4f} non_geo={len(nrm_geo_bad)} min_ny={min_ny:.6f}")
    if nrm_scope_bad:
        findings.append(f"REFUTE (6): {len(nrm_scope_bad)} normals rewritten on tris with NO moved vertex.")
    if nrm_geo_bad:
        findings.append(f"REFUTE (6): {len(nrm_geo_bad)} stored normals on moved tris are not the geometric "
                        f"up-facing normal (>0.5deg): {nrm_geo_bad[:4]}.")
    if nrm_down:
        findings.append(f"REFUTE (6): {len(nrm_down)} stored normals on moved tris point DOWN.")
    if n_rw_tris != 12:
        findings.append(f"MISMATCH (6): {n_rw_tris} tris got a rewritten normal, report claims 12.")
    if n_rw_kept != 2:
        findings.append(f"MISMATCH (6): {n_rw_kept} KEPT tris got a rewritten normal, report claims 2.")

    # 6f: THE FIDELITY COST -- is the shaved crest genuine carried stock geometry?
    fid = dict(donor_keys=len(donor_tris), shift=list(SHIFT))
    fid_rows = []
    for r in tris:
        if not r["moved"] or r["synth"]: continue
        key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in r["wb"]))
        cands = donor_tris.get(key, [])
        rc = rect_of(r["uv"])
        match = [c for c in cands if c["rect"] == rc]
        dys = sorted({round(min(p[1] for p in r["wb"]) - min(c["ys"]), 4) for c in cands}) if cands else []
        def dip(which):
            g = geo_normal(*r[which]); L = math.sqrt(sum(c * c for c in g))
            return None if L < 1e-12 else round(math.degrees(math.acos(max(-1.0, min(1.0, abs(g[1]) / L)))), 2)
        fid_rows.append(dict(block=list(r["b"]), tri=r["t"], topo=r["topo"], rect=list(rc),
                             donor_xz_match=bool(cands),
                             donor_candidates=[[c["block"], c["tri"], c["topo"], list(c["rect"])] for c in cands],
                             donor_uv_match=bool(match), implied_DY=dys,
                             dip_before_deg=dip("wb"), dip_after_deg=dip("wt"),
                             donor_dip_deg=[dip_of(c["pts"]) for c in cands]))
    fid["reposed_carried_faces"] = fid_rows
    fid["n_donor_verbatim"] = sum(1 for r in fid_rows if r["donor_uv_match"])
    # is the decal rect a ground main, or a distinct atlas window?
    decal_rects = {tuple(r["rect"]) for r in fid_rows}
    ground_rect_hist = {}
    for topo in (41, 16, 0):
        c = stock_rects.get(topo)
        if c: ground_rect_hist[str(topo)] = [[list(k), v] for k, v in c.most_common(4)]
    fid["stock_topo_rect_top4"] = ground_rect_hist
    fid["reposed_rects_are_the_topo_majority_window"] = {
        str(list(rr)): bool(stock_rects.get(41) and stock_rects[41].most_common(1)[0][0] == rr)
        for rr in decal_rects}
    hunt["fidelity_cost"] = fid
    log(f"[6] fidelity: donor keys={len(donor_tris)} reposed carried faces={len(fid_rows)} "
        f"donor_verbatim={fid['n_donor_verbatim']}")
    if fid_rows and fid["n_donor_verbatim"] == len(fid_rows):
        findings.append(f"NOTE (6): all {len(fid_rows)} re-posed CARRIED faces are donor-verbatim stock geometry "
                        f"(Cleyra junction under shift {list(SHIFT)}) -- the round's own 'fifth fidelity "
                        f"payment' independently confirmed: real stock relief was flattened.")

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
    R["hunt"] = hunt

    # ================= (7) ANTI-VACUITY CALIBRATION =================
    calib = {}
    mound_ground = [k for k in carried_ground if BASIN_R < rcrater(k[0], k[2]) <= MOUND_R]
    base_rows = {(r["pos"][0], r["pos"][2]): r for r in cen_t}
    victim = None
    for k in sorted(mound_ground):
        r = base_rows.get((round(k[0], 3), round(k[2], 3)))
        if r and abs(r["res"]) < 0.15 and r["prom"] is not None and r["prom"] < 0.0:
            victim = k; break
    if victim is not None:
        planted = dict(yt); planted[victim] = yt[victim] + 1.5
        ref, _, _ = surft.at(victim[0], victim[2], skip=(victim,))
        prom_p, drop_p, slope_p, _ = shape(victim, planted)
        res_p = planted[victim] - ref if ref is not None else None
        calib["7a_planted_spike"] = dict(
            victim=[round(victim[0], 3), round(victim[2], 3)],
            residual_clean=base_rows[(round(victim[0], 3), round(victim[2], 3))]["res"],
            residual_planted=None if res_p is None else round(res_p, 4),
            prominence_planted=None if prom_p is None else round(prom_p, 4),
            drop_planted=None if drop_p is None else round(drop_p, 4),
            arm_planted=arm_of(prom_p, drop_p),
            census_flags_it=bool(res_p is not None and res_p >= OUTLIER_U and arm_of(prom_p, drop_p)))
        if not calib["7a_planted_spike"]["census_flags_it"]:
            findings.append("REFUTE (7a): my round-7 census does NOT flag a planted +1.5u spike -- the "
                            "self-termination lane is vacuous.")
    else:
        calib["7a_planted_spike"] = dict(skipped="no flat carried victim found")
        findings.append("NOTE (7a): no calibration victim; the census lane is unproven.")

    # 7a2: THE STEP ARM specifically -- plant a pure step (prominence 0, deep drop) and confirm the arm sees it
    step_victim = None
    for r in cen_t:
        if r["arm"] == "STEP": step_victim = r; break
    calib["7a2_step_arm_is_live"] = dict(
        n_step_arm_passers_on_target=sum(1 for r in cen_t if r["arm"] == "STEP"),
        n_cone_arm_passers_on_target=sum(1 for r in cen_t if r["arm"] == "CONE"),
        example=step_victim,
        synthetic_check=dict(prom=0.0, drop=STEP_DROP + 0.01, arm=arm_of(0.0, STEP_DROP + 0.01),
                             prom_neg=arm_of(-0.01, 9.0), drop_short=arm_of(0.0, STEP_DROP - 0.01)))
    if calib["7a2_step_arm_is_live"]["synthetic_check"]["arm"] != "STEP" or \
       calib["7a2_step_arm_is_live"]["synthetic_check"]["prom_neg"] is not None or \
       calib["7a2_step_arm_is_live"]["synthetic_check"]["drop_short"] is not None:
        findings.append("REFUTE (7a2): my STEP-arm implementation does not behave as the round states.")

    lowest = min(cen_b, key=lambda r: r["res"]) if cen_b else None
    calib["7b_non_outlier_would_refute"] = dict(
        lowest_residual_carried_in_mound=lowest,
        below_hard_threshold_0p70=None if lowest is None else bool(lowest["res"] < 0.70),
        n_carried_in_mound_failing_the_gate=sum(1 for r in cen_b if r["res"] < 0.70),
        meaning="if any of these appeared in the moved-carried set, lane (2) fires REFUTE.")
    if lowest is not None and lowest["res"] >= 0.70:
        findings.append("NOTE (7b): every carried position in the mound scores >= 0.70u, so lane (2) could not "
                        "have rejected anything -- treat its pass as weak.")

    multi = max(groups.items(), key=lambda kv: len(kv[1]))
    mk, ments = multi
    simb = [entb[e][1] for e in ments]; simt = list(simb); simt[0] += 0.25
    calib["7c_planted_weld_split"] = dict(
        group=[round(mk[0], 3), round(mk[1], 3), round(mk[2], 3)], n_entries=len(ments),
        spread_before=round(max(simb) - min(simb), 6), spread_after=round(max(simt) - min(simt), 6),
        split_detector_fires=bool((max(simt) - min(simt)) > (max(simb) - min(simb)) + 1e-6),
        nonuniform_detector_fires=bool((max(x - y_ for x, y_ in zip(simt, simb)) -
                                        min(x - y_ for x, y_ in zip(simt, simb))) > 1e-9))
    if not (calib["7c_planted_weld_split"]["split_detector_fires"] and
            calib["7c_planted_weld_split"]["nonuniform_detector_fires"]):
        findings.append("REFUTE (7c): my weld detectors do NOT fire on a planted one-entry split.")

    calib["7d_basin_gate"] = dict(n_positions_in_disc=len(disc_keys), n_vertex_entries_in_disc=disc_entries,
                                  gate_is_live=bool(disc_keys),
                                  nearest_moved_position_to_centre=R["basin"]["min_r_crater_of_a_moved_position"],
                                  clearance_beyond_guard=round(
                                      R["basin"]["min_r_crater_of_a_moved_position"] - GUARD_R, 4))
    if not disc_keys:
        findings.append("REFUTE (7d): the basin disc contains NO positions -- 'basin frozen' is vacuous.")

    rep_path = RUNG / "uvf_fix7_report.json"
    if rep_path.exists():
        rj0 = json.loads(rep_path.read_text(encoding="utf-8"))
        theirs = {(round(s["peak_world"][0], 3), round(s["peak_world"][2], 3)):
                  (s["peak_residual_u"], s.get("peak_prominence_u"), s.get("peak_drop_u"))
                  for s in rj0["stage3_spike_census"]["sites"]}
        pairs = []
        for r in mc_rows:
            t = theirs.get((r["pos"][0], r["pos"][2]))
            if t is not None:
                pairs.append([r["pos"], t[0], r["residual_before"], round(r["residual_before"] - t[0], 4),
                              t[1], r["prominence_before"], t[2], r["drop_before"]])
        calib["7e_estimator_agreement"] = dict(
            row_schema=["pos", "build_res", "my_res", "delta", "build_prom", "my_prom", "build_drop", "my_drop"],
            rows=pairs, n_matched=len(pairs),
            max_abs_residual_delta=round(max((abs(p[3]) for p in pairs), default=0.0), 4),
            reading="different radii + different robust weighting; a small non-zero residual delta with "
                    "IDENTICAL prominence/drop (pure mesh arithmetic, no estimator) is exactly what two "
                    "independent implementations should produce.")
        if len(pairs) != len(mc_rows):
            findings.append(f"MISMATCH (7e): only {len(pairs)}/{len(mc_rows)} moved carried positions appear in "
                            f"the build's own site list -- it moved something it did not census.")
    R["calibration"] = calib
    log(f"[7] calibration: spike_seen={calib.get('7a_planted_spike', {}).get('census_flags_it')} "
        f"weld_split={calib.get('7c_planted_weld_split', {}).get('split_detector_fires')} "
        f"basin_live={calib.get('7d_basin_gate', {}).get('gate_is_live')} "
        f"est_delta={calib.get('7e_estimator_agreement', {}).get('max_abs_residual_delta')}")

    # ================= report reconciliation =================
    recon = {}
    if rep_path.exists():
        rj = json.loads(rep_path.read_text(encoding="utf-8"))
        ap = rj["stage_apply"]; sg = rj["stop_guards"]; s1 = rj["stage1_mesh"]; s3 = rj["stage3_spike_census"]
        cs = rj["stage_verify"]["crater_sacred"]["basin"]
        claims = dict(positions_moved=ap["positions_moved"], vertex_entries_moved=ap["vertex_entries_moved"],
                      tris_with_moved_vert=ap["tris_with_a_moved_vert"],
                      kept_tris_moved=ap["of_which_carried_kept_tris"],
                      normal_tris=ap["normal_tris_recomputed"], normal_entries=ap["normal_verts_rewritten"],
                      max_abs_dY=ap["max_abs_dY"], cross_block=ap["positions_spanning_multiple_blocks"],
                      files_changed=1, distinct_positions=s1["n_distinct_positions_all_parts"],
                      carried_ground=s1["n_carried_ground_positions"], fill=s1["n_fill_positions"],
                      synthesized=s1["n_synthesized_tris"], n_spikes=s3["n_spikes"],
                      basin_disc_positions=cs["n_position_groups_inside"],
                      basin_disc_entries=cs["n_vertex_entries_inside"],
                      basin_bytes_changed=cs["vertex_bytes_changed"],
                      min_r_crater_moved=sg["min_r_crater_of_a_moved_position"],
                      rock_moved=sg["rock_positions_moved"],
                      carried_non_spike_moved=sg["carried_non_spike_positions_moved"])
        mine = dict(positions_moved=len(moved_keys), vertex_entries_moved=chan["y_moved_entries"],
                    tris_with_moved_vert=n_moved_tris, kept_tris_moved=n_rw_kept, normal_tris=n_rw_tris,
                    normal_entries=n_rw_entries,
                    max_abs_dY=round(max(abs(dy_by_group[k]) for k in moved_keys), 4) if moved_keys else 0.0,
                    cross_block=cross_block_moved, files_changed=len(changed), distinct_positions=len(groups),
                    carried_ground=len(carried_ground), fill=len(fill), synthesized=n_synth,
                    n_spikes=len(moved_carried_ground), basin_disc_positions=len(disc_keys),
                    basin_disc_entries=disc_entries, basin_bytes_changed=disc_bytes_changed,
                    min_r_crater_moved=round(R["basin"]["min_r_crater_of_a_moved_position"], 3),
                    rock_moved=len(rock_bad_broad), carried_non_spike_moved=len(frozen_bad))
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
