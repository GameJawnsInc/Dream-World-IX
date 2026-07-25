"""RUNG F -- THE ROOTS RELIEF PROBE (round 5, 2026-07-24).  READ-ONLY.

Playtest 3 on FIXED4: the family re-clothe WORKED ("they almost look gone") but the GEOMETRY still
carries the dropped Cleyra roots -- the owner reports elongated channel/cleft depressions radiating
out of the crater rim, a raised face/nub at each channel's crater end, and local "dig spot" pits.

THIS SCRIPT MEASURES, IT DOES NOT MOVE ANYTHING.  It answers five questions with numbers:

  1. WHICH GEOMETRY IS MOVABLE.  Re-derive the 2305 synthesized tris (the SPECIMEN's UV-degenerate
     classifier of record, uvf_fix2/3) inside the DEPLOYED FIXED4 tree, then build the coincident-
     POSITION graph over EVERY vertex of EVERY part of all 20 touched blocks (Terrain + Object +
     Beach1 + Sea1..Sea5).  A position is MOVABLE only if every vertex entry at it belongs to a
     synthesized tri; one kept-content entry PINS it (Dirichlet).  Key = full 3D position at 3dp --
     same XZ + different Y is a wall, not a weld.

  2. THE REFERENCE SURFACE.  A robust local ground field fit from KEPT terrain only: kept tris whose
     topograph has a ground family (grassland.TOPO_FAMILY -> grass/desert/dunes) vote their vertex
     positions as samples; kept ROCK/wall stamps (the non-ground topos: 58 wall_rock, 31) ABSTAIN,
     because their near-vertical faces would tilt any local plane.  The fit is an IDW-weighted least-
     squares plane with two Tukey-biweight IRLS passes over a growing radius (8 -> 12 -> 18 -> 26u).
     The crater bowl IS kept content, so the reference FOLLOWS the crater by construction -- which is
     exactly why "residual vs the kept surface" is the right anomaly statistic: it is blind to the
     crater and sensitive to the root relief.

  3. THE RESIDUALS.  Per movable position, Y - reference(x,z).  Split by zone (the dunes/desert donut
     vs the grass lobe, from uvf_fix4's own per-cell family field) and by provenance (hole-fill /
     apron / stitch, from uvf_forensics' per-tri records).  Coherent anomalies are clustered
     (proximity graph on the anomalous positions) and each cluster is reported with world coords,
     PCA elongation, peak magnitude and sign.

  4. THE MECHANISM.  rung_f_layout.carry() gives the fill its Y by ONE of two branches: a fill vertex
     whose donor XZ is SHARED with a kept ecotone vertex keeps the donor's own Y (+DY); every other
     fill vertex is FLATTENED to land_height (3.0).  Both branches are tested per movable position by
     exact float match against a re-read of the donor window (load_donor_window + SHIFT_CELLS), so the
     relief's source is proven, not assumed.  The dropped topo-49 root strips are overlaid on the
     clusters.

  5. CRATER SAFETY + SCOPE.  Who owns the crater rim/bowl relief (pinned carried terrain vs fill), and
     the exact moved-vert set / blend ring / pin set / solve a fix round would use, with a predicted
     max |dY|.

    py -X utf8 uvf_relief_probe.py          # -> out/rung_f/uvf_relief_probe.json
"""
from __future__ import annotations
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X                       # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import grassland as G                     # noqa: E402

import uvf_fix2 as F2                                           # noqa: E402
import uvf_fix3 as F3                                           # noqa: E402
import rung_f_layout as L                                       # noqa: E402

CH_POS, CH_NRM, CH_UV, CH_TAN = X.CH_POS, X.CH_NRM, X.CH_UV, X.CH_TAN
CELL = 4.0
BLOCK = 64.0
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX"

RUNG_F = HERE / "out" / "rung_f"
SPEC = RUNG_F / "FF9CustomMap-world"
FIXED4 = RUNG_F / "FF9CustomMap-world-FIXED4"
BUILD_JSON = RUNG_F / "rung_f_build.json"
FORENSICS = RUNG_F / "uvf_forensics.json"
FIX4_REPORT = RUNG_F / "uvf_fix4_report.json"
REPORT = RUNG_F / "uvf_relief_probe.json"

PARTS = ("Terrain", "Object", "Beach1", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5")

CRATER_CELL = (33, -292)
CRATER_WORLD = (CRATER_CELL[0] * CELL + CELL / 2.0, CRATER_CELL[1] * CELL + CELL / 2.0)  # (134,-1166)
LAND_HEIGHT = L.LAND_HEIGHT                                    # 3.0
SHIFT_WORLD = L.SHIFT_WORLD                                    # (-768,-384)

ANOM_T = 0.60          # |residual| (u) that counts as a coherent anomaly (sensitivity swept in-report)
CLUSTER_R = 4.5        # proximity-graph radius (u) for grouping anomalous positions
MIN_CLUSTER = 2        # smallest reported cluster (the "dig spots" are 2-4 verts)
ENCLOSE_R = 20.0       # ray length (u) for the basin-enclosure test
ENCLOSE_DY = 1.5       # a ray "closes" when kept ground rises this far above the sample
POS_DP = 3


def log(m):
    print(m, flush=True)


def pkey(p):
    return (round(float(p[0]), POS_DP), round(float(p[1]), POS_DP), round(float(p[2]), POS_DP))


def stats(a, extra_pctl=()):
    a = np.asarray(a, dtype=float)
    if a.size == 0:
        return dict(n=0)
    d = dict(n=int(a.size), mean=round(float(a.mean()), 4), sd=round(float(a.std()), 4),
             min=round(float(a.min()), 4), max=round(float(a.max()), 4))
    for q in (1, 5, 25, 50, 75, 95, 99) + tuple(extra_pctl):
        d[f"p{q}"] = round(float(np.percentile(a, q)), 4)
    d["mad"] = round(float(np.median(np.abs(a - np.median(a)))), 4)
    return d


# =================================================================================================
#  GRID HASH (neighbour queries without scipy)
# =================================================================================================
class Hash2D:
    def __init__(self, pts, cell=8.0):
        self.cell = cell
        self.pts = np.asarray(pts, dtype=float)
        self.buckets = defaultdict(list)
        for i, p in enumerate(self.pts):
            self.buckets[(math.floor(p[0] / cell), math.floor(p[2] / cell))].append(i)

    def query(self, x, z, r):
        c = self.cell
        i0, i1 = math.floor((x - r) / c), math.floor((x + r) / c)
        j0, j1 = math.floor((z - r) / c), math.floor((z + r) / c)
        out = []
        r2 = r * r
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                for k in self.buckets.get((i, j), ()):
                    p = self.pts[k]
                    d2 = (p[0] - x) ** 2 + (p[2] - z) ** 2
                    if d2 <= r2:
                        out.append((k, d2))
        return out


# =================================================================================================
#  STAGE 1 -- the movable set + the coincident-position graph
# =================================================================================================
def stage1(report):
    build = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    assert len(touched) == 20

    forensics = json.loads(FORENSICS.read_text(encoding="utf-8"))
    apron_keys = set()
    prov_by_key = {}
    for rec in forensics["records"]:
        cx, _cy, cz = rec["centroid"]
        k = (tuple(rec["block"]), round(cx, 3), round(cz, 3))
        prov_by_key[k] = rec["provenance"]
        if rec.get("uv_verdict") == "degenerate-zero-area" and rec["provenance"] == "apron":
            apron_keys.add(k)

    spec_meshes = F3.load_blocks(SPEC, touched)
    f4_meshes = F3.load_blocks(FIXED4, touched)

    # --- position identity between SPEC and the deployed FIXED4 (all uv rounds were UV-only) --------
    n_pos_diff = 0
    for b in touched:
        s = spec_meshes[b].chan_arrays[CH_POS]
        f = f4_meshes[b].chan_arrays[CH_POS]
        for j in range(len(s)):
            if s[j] != f[j]:
                n_pos_diff += 1
    assert n_pos_diff == 0, f"FIXED4 moved {n_pos_diff} vertex positions vs SPEC -- classifier invalid"

    defective, _lawful = F3.classify_defective(spec_meshes, apron_keys, touched)
    assert len(defective) == 2305, len(defective)
    synth_key = {(d["block"], d["tri"]) for d in defective}

    # --- provenance per synthesized tri (forensics centroid key) ----------------------------------
    prov_of = {}
    prov_hist = Counter()
    for d in defective:
        cx = sum(v[0] for v in d["vw"]) / 3.0
        cz = sum(v[2] for v in d["vw"]) / 3.0
        p = prov_by_key.get((d["block"], round(cx, 3), round(cz, 3)), "unmatched")
        prov_of[(d["block"], d["tri"])] = p
        prov_hist[p] += 1

    # --- the coincident-position graph over EVERY part ---------------------------------------------
    pos_entries = defaultdict(list)       # poskey -> [(block, part, tri_index_or_None)]
    pinned = set()
    synth_pos = set()
    part_files = Counter()
    for b in touched:
        for part in PARTS:
            p = Path(FIXED4) / M.override_relpath(1, b[0], b[1], part=part)
            if not p.exists():
                continue
            part_files[part] += 1
            bm = M.blockmesh_from_ff9mesh(p, disc=1, x=b[0], y=b[1], part=part.lower())
            ox, oz = X.block_world_origin(*b)
            verts = bm.chan_arrays[CH_POS]
            for t, tri in enumerate(bm.tris):
                is_synth = (part == "Terrain") and ((b, t) in synth_key)
                for j in tri:
                    v = verts[j]
                    k = pkey((v[0] + ox, v[1], v[2] + oz))
                    pos_entries[k].append((b, part, t if is_synth else None))
                    if is_synth:
                        synth_pos.add(k)
                    else:
                        pinned.add(k)
    movable = synth_pos - pinned

    # cross-block / cross-part multiplicity of the movable positions (the weld law's cost)
    mult = Counter(len(pos_entries[k]) for k in movable)
    cross_block = sum(1 for k in movable if len({e[0] for e in pos_entries[k]}) > 1)

    report["stage1_movable_set"] = dict(
        touched_blocks=len(touched), part_files=dict(part_files),
        n_synthesized_tris=len(defective), provenance_hist=dict(prov_hist),
        spec_vs_fixed4_position_diffs=n_pos_diff,
        n_distinct_positions_all_parts=len(pos_entries),
        n_positions_touched_by_synth=len(synth_pos),
        n_pinned_of_those=len(synth_pos & pinned),
        n_movable=len(movable),
        movable_entry_multiplicity=dict(sorted(mult.items())),
        movable_spanning_multiple_blocks=cross_block,
        note=("PINNED = any position with >=1 vertex entry owned by non-synthesized geometry "
              "(kept Terrain tri OR any Object/Beach/Sea part). Key = 3D position @3dp: same XZ + "
              "different Y is a wall, not a weld."))
    log(f"[s1] synth tris 2305  positions: synth-touched {len(synth_pos)}  pinned-of-those "
        f"{len(synth_pos & pinned)}  MOVABLE {len(movable)}  (cross-block {cross_block})")
    return touched, f4_meshes, defective, synth_key, prov_of, pos_entries, pinned, movable


# =================================================================================================
#  STAGE 2 -- the reference surface from KEPT terrain only
# =================================================================================================
GROUND_FAM = G.TOPO_FAMILY


def stage2(report, touched, f4_meshes, synth_key):
    ground_pos, rock_pos = {}, {}
    kept_topo = Counter()
    ground_topo = Counter()
    rock_topo = Counter()
    for b in touched:
        bm = f4_meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[CH_POS]
        tans = bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            if (b, t) in synth_key:
                continue
            topo = X.decode_id(int(round(tans[tri[0]][0])))["topograph"]
            kept_topo[topo] += 1
            fam = GROUND_FAM.get(topo)
            for j in tri:
                v = verts[j]
                k = pkey((v[0] + ox, v[1], v[2] + oz))
                if fam is not None:
                    ground_pos[k] = fam
                else:
                    rock_pos.setdefault(k, topo)
            (ground_topo if fam is not None else rock_topo)[topo] += 1

    # a position owned by BOTH a ground tri and a rock tri counts as ground (it is on the ground seam)
    rock_only = {k: v for k, v in rock_pos.items() if k not in ground_pos}

    gy = np.array([k[1] for k in ground_pos])
    ry = np.array([k[1] for k in rock_only])
    samples = np.array([[k[0], k[1], k[2]] for k in ground_pos], dtype=float)
    ghash = Hash2D(samples, cell=8.0)

    report["stage2_reference_surface"] = dict(
        kept_tris=int(sum(kept_topo.values())), kept_topo_hist=dict(sorted(kept_topo.items())),
        ground_tris=int(sum(ground_topo.values())), ground_topo_hist=dict(sorted(ground_topo.items())),
        abstaining_tris=int(sum(rock_topo.values())), abstaining_topo_hist=dict(sorted(rock_topo.items())),
        n_ground_sample_positions=len(ground_pos),
        n_rock_only_positions=len(rock_only),
        ground_sample_y=stats(gy), rock_only_y=stats(ry),
        rock_handling=("kept tris whose topograph has NO ground family (58 wall_rock, 31) ABSTAIN as "
                       "reference samples -- their near-vertical faces would tilt the local plane. A "
                       "position shared by a ground tri AND a rock tri is KEPT as a ground sample (it "
                       "lies on the ground seam, so it is the correct height there)."),
        method=("IDW-weighted least-squares plane y=a+bx+cz over kept ground sample positions inside a "
                "growing radius (8/12/18/26u, >=8 samples and a non-degenerate XZ spread required), "
                "w=1/(d^2+1); two Tukey-biweight IRLS passes (c=4.685*1.4826*MAD, floor 0.05u); "
                "weighted-median fallback if the normal matrix stays rank-deficient."))
    log(f"[s2] reference samples: {len(ground_pos)} ground positions "
        f"(y {gy.min():.2f}..{gy.max():.2f}), {len(rock_only)} rock-only positions EXCLUDED "
        f"(y {ry.min():.2f}..{ry.max():.2f})" if len(ry) else f"[s2] reference samples {len(ground_pos)}")
    return ground_pos, ghash, samples


def ref_at(ghash, samples, x, z):
    """Robust local ground height + diagnostics."""
    for R in (8.0, 12.0, 18.0, 26.0):
        hits = ghash.query(x, z, R)
        if len(hits) < 8:
            continue
        idx = np.array([h[0] for h in hits])
        d2 = np.array([h[1] for h in hits])
        P = samples[idx]
        dx, dz, y = P[:, 0] - x, P[:, 2] - z, P[:, 1]
        A = np.column_stack([np.ones_like(dx), dx, dz])
        w = 1.0 / (d2 + 1.0)
        beta = None
        for _ in range(3):
            W = np.sqrt(w)
            try:
                beta, *_ = np.linalg.lstsq(A * W[:, None], y * W, rcond=None)
            except np.linalg.LinAlgError:
                beta = None
                break
            r = y - A @ beta
            mad = float(np.median(np.abs(r - np.median(r))))
            s = max(1.4826 * mad, 0.05)
            u = np.clip(np.abs(r) / (4.685 * s), 0, 1)
            w = (1.0 / (d2 + 1.0)) * (1 - u ** 2) ** 2
            if w.sum() <= 1e-9:
                w = 1.0 / (d2 + 1.0)
                break
        if beta is None:
            continue
        yhat = float(beta[0])
        r = y - A @ beta
        return yhat, dict(R=R, n=len(hits), rms=float(np.sqrt(np.mean(r ** 2))),
                          d_near=float(np.sqrt(d2.min())), slope=float(math.hypot(beta[1], beta[2])))
    # fallback: weighted median of the nearest samples in a wide ring
    hits = ghash.query(x, z, 40.0)
    if not hits:
        return None, dict(R=None, n=0, rms=None, d_near=None, slope=None)
    hits.sort(key=lambda h: h[1])
    idx = [h[0] for h in hits[:12]]
    return float(np.median(samples[idx][:, 1])), dict(R=40.0, n=len(idx), rms=None,
                                                      d_near=float(math.sqrt(hits[0][1])), slope=None,
                                                      fallback="weighted-median")


# =================================================================================================
#  STAGE 3 -- residuals
# =================================================================================================
def stage3(report, movable, pos_entries, prov_of, ghash, samples, fill_fam_of_cell):
    rows = []
    for k in sorted(movable):
        x, y, z = k
        yhat, diag = ref_at(ghash, samples, x, z)
        if yhat is None:
            continue
        provs = Counter(prov_of[(e[0], e[2])] for e in pos_entries[k] if e[2] is not None)
        cell = (math.floor(x / CELL), math.floor(z / CELL))
        rows.append(dict(k=k, x=x, y=y, z=z, ref=yhat, res=y - yhat,
                         prov=provs.most_common(1)[0][0], provs=dict(provs),
                         fam=fill_fam_of_cell.get(cell, "unknown"), cell=cell,
                         r_crater=math.hypot(x - CRATER_WORLD[0], z - CRATER_WORLD[1]),
                         d_near=diag["d_near"], fit_R=diag["R"], fit_n=diag["n"], fit_rms=diag["rms"]))
    res = np.array([r["res"] for r in rows])

    by_fam, by_prov = {}, {}
    for fam in ("grass", "dunes", "desert", "unknown"):
        a = [r["res"] for r in rows if r["fam"] == fam]
        if a:
            by_fam[fam] = stats(a)
    for p in ("hole-fill", "apron", "stitch", "frame-mint", "unmatched"):
        a = [r["res"] for r in rows if r["prov"] == p]
        if a:
            by_prov[p] = stats(a)

    sens = {}
    for t in (0.4, 0.6, 0.8, 1.2, 2.0):
        sens[str(t)] = dict(n=int(np.sum(np.abs(res) >= t)),
                            n_pos=int(np.sum(res >= t)), n_neg=int(np.sum(res <= -t)))

    report["stage3_residuals"] = dict(
        n_movable_scored=len(rows), overall=stats(res),
        by_zone_family=by_fam, by_provenance=by_prov,
        threshold_sensitivity=sens,
        nearest_kept_ground_distance=stats([r["d_near"] for r in rows]),
        fit_rms=stats([r["fit_rms"] for r in rows if r["fit_rms"] is not None]),
        sign_convention="residual = fill Y minus the local kept-ground reference (positive = sits ABOVE)")
    log(f"[s3] residuals n={len(rows)} mean={res.mean():+.3f} p1={np.percentile(res,1):+.3f} "
        f"p99={np.percentile(res,99):+.3f} min={res.min():+.3f} max={res.max():+.3f}  "
        f"|res|>={ANOM_T}: {int(np.sum(np.abs(res)>=ANOM_T))}")
    return rows


# =================================================================================================
#  STAGE 4 -- clusters + the donor overlay (the mechanism proof)
# =================================================================================================
def load_donor(report):
    donor = L.load_donor_window(GAME)
    build = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    DY = build["compose_diag"]["DY"]
    Tx, Tz = SHIFT_WORLD

    kept_xz_y = defaultdict(set)          # deploy (x,z)@3dp -> {deploy Y of a KEPT donor vertex}
    kept_xz = set()
    for c, tris in donor["by_cell"].items():
        for tri in tris:
            for (p, _n, _u, _t) in tri:
                kx, kz = round(p[0] + Tx, 3), round(p[2] + Tz, 3)
                kept_xz.add((kx, kz))
                kept_xz_y[(kx, kz)].add(round(p[1] + DY, 3))

    dropped_cells_deploy = {}             # deploy cell -> Counter(topo)
    drop49_xz = set()
    for c, tris in donor["dropped_by_cell"].items():
        dc = (c[0] + L.SHIFT_CELLS[0], c[1] + L.SHIFT_CELLS[1])
        cnt = dropped_cells_deploy.setdefault(dc, Counter())
        for tri in tris:
            topo = X.decode_id(int(round(tri[0][3][0])))["topograph"]
            cnt[topo] += 1
            if topo == 49:
                for (p, _n, _u, _t) in tri:
                    drop49_xz.add((round(p[0] + Tx, 3), round(p[2] + Tz, 3)))
    cells49 = {c for c, cnt in dropped_cells_deploy.items() if cnt.get(49, 0) > 0}

    report["stage4_donor_overlay"] = dict(
        DY=DY, land_height=LAND_HEIGHT, shift_world=list(SHIFT_WORLD), shift_cells=list(L.SHIFT_CELLS),
        donor_kept_cells=donor["n_cells_kept"], donor_dropped_tris=donor["n_dropped"],
        dropped_cells=len(dropped_cells_deploy), dropped_cells_with_topo49=len(cells49),
        n_kept_donor_xz=len(kept_xz), n_topo49_vertex_xz=len(drop49_xz))
    return dict(DY=DY, kept_xz=kept_xz, kept_xz_y=kept_xz_y, cells49=cells49, drop49_xz=drop49_xz,
                dropped_cells=dropped_cells_deploy)


def enclosure(ghash, samples, x, y, z, n_rays=16):
    """Fraction of azimuths on which KEPT ground rises >= ENCLOSE_DY above y within ENCLOSE_R.
    A BASIN (the crater) closes on nearly every ray; a CHANNEL closes on its two flanks only."""
    hits = ghash.query(x, z, ENCLOSE_R)
    if not hits:
        return 0.0, 0.0
    best = [-1e9] * n_rays
    for k, d2 in hits:
        p = samples[k]
        a = math.atan2(p[2] - z, p[0] - x)
        s = int(((a + math.pi) / (2 * math.pi)) * n_rays) % n_rays
        if p[1] > best[s]:
            best[s] = p[1]
    live = [b for b in best if b > -1e8]
    if not live:
        return 0.0, 0.0
    closed = sum(1 for b in live if b - y >= ENCLOSE_DY)
    return closed / n_rays, float(np.median(live) - y)


def stage4b(report, touched, f4_meshes, synth_key, movable, pinned, prov_of):
    """THE JUTTING-FACE CENSUS. A synthesized tri spanning the flat land_height sheet and a PINNED
    donor-height rim is a near-vertical triangle -- the 'face/nub' the owner sees. Measured per tri:
    Y range, dip angle of the geometric normal, and how many of its 3 positions are movable."""
    faces = []
    dip_all = []
    for b in touched:
        bm = f4_meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[CH_POS]
        for t, tri in enumerate(bm.tris):
            if (b, t) not in synth_key:
                continue
            P3 = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in tri]
            ys = [p[1] for p in P3]
            yr = max(ys) - min(ys)
            u = np.subtract(P3[1], P3[0])
            v = np.subtract(P3[2], P3[0])
            nrm = np.cross(u, v)
            ln = float(np.linalg.norm(nrm))
            dip = 90.0 if ln < 1e-9 else math.degrees(math.acos(min(1.0, abs(float(nrm[1])) / ln)))
            dip_all.append(dip)
            keys = [pkey(p) for p in P3]
            nmov = sum(1 for k in keys if k in movable)
            if yr >= 1.0:
                cx = sum(p[0] for p in P3) / 3.0
                cz = sum(p[2] for p in P3) / 3.0
                faces.append(dict(world=[round(cx, 2), round(sum(ys) / 3.0, 2), round(cz, 2)],
                                  y_lo=round(min(ys), 3), y_hi=round(max(ys), 3), y_range=round(yr, 3),
                                  dip_deg=round(dip, 1), n_movable_of_3=nmov,
                                  prov=prov_of[(b, t)],
                                  r_crater=round(math.hypot(cx - CRATER_WORLD[0], cz - CRATER_WORLD[1]), 1),
                                  block=f"{b[0]},{b[1]}"))
    faces.sort(key=lambda f: -f["y_range"])
    bands = Counter()
    for f in faces:
        bands[f"{int(f['y_range'])}-{int(f['y_range'])+1}u"] += 1
    report["stage4b_jutting_faces"] = dict(
        n_synth_tris=len(dip_all), dip_deg=stats(dip_all),
        n_tris_yrange_ge_1u=len(faces),
        n_tris_yrange_ge_2u=sum(1 for f in faces if f["y_range"] >= 2.0),
        n_tris_yrange_ge_3u=sum(1 for f in faces if f["y_range"] >= 3.0),
        n_tris_dip_ge_45=sum(1 for d in dip_all if d >= 45.0),
        n_tris_dip_ge_60=sum(1 for d in dip_all if d >= 60.0),
        y_range_bands=dict(sorted(bands.items())),
        fixable_share=dict(
            all_three_movable=sum(1 for f in faces if f["n_movable_of_3"] == 3),
            two_movable=sum(1 for f in faces if f["n_movable_of_3"] == 2),
            one_movable=sum(1 for f in faces if f["n_movable_of_3"] == 1),
            none_movable=sum(1 for f in faces if f["n_movable_of_3"] == 0)),
        fixable_share_yrange_ge_2u=dict(
            two_movable=sum(1 for f in faces if f["y_range"] >= 2 and f["n_movable_of_3"] == 2),
            one_movable=sum(1 for f in faces if f["y_range"] >= 2 and f["n_movable_of_3"] == 1),
            none_movable=sum(1 for f in faces if f["y_range"] >= 2 and f["n_movable_of_3"] == 0)),
        fully_pinned_steep_faces=[f for f in faces if f["y_range"] >= 2 and f["n_movable_of_3"] == 0],
        steepest_40=faces[:40],
        note=("y_range = the vertical span of a single synthesized triangle. A tri with a movable vertex "
              "at the flat land_height sheet (Y=3.000) and a PINNED vertex at the carried donor rim IS "
              "the terminal face; raising the movable vertex to the reference collapses it. A face whose "
              "3 positions are ALL pinned is carried relief and cannot be touched."))
    log(f"[s4b] synth tris with >=1u internal Y span: {len(faces)} (>=2u {sum(1 for f in faces if f['y_range']>=2)}, "
        f">=3u {sum(1 for f in faces if f['y_range']>=3)}); dip>=45 {sum(1 for d in dip_all if d>=45)}")


def stage4(report, rows, donor, ghash, samples):
    DY = donor["DY"]
    # --- per-vertex BRANCH attribution: flatten-to-land_height vs kept-donor-Y --------------------
    branch = Counter()
    for r in rows:
        xz = (round(r["x"], 3), round(r["z"], 3))
        y = round(r["y"], 3)
        shared = xz in donor["kept_xz"]
        if abs(r["y"] - LAND_HEIGHT) < 1e-3:
            b = "flattened_to_land_height"
        elif shared and y in donor["kept_xz_y"][xz]:
            b = "kept_donor_Y(+DY)"
        elif shared:
            b = "shared_xz_other_Y"
        else:
            b = "other(stitch/apron/tiling-interpolated)"
        r["branch"] = b
        r["donor_shared_xz"] = shared
        r["in_topo49_cell"] = r["cell"] in donor["cells49"]
        dc = donor["dropped_cells"].get(r["cell"])
        r["drop_topo"] = ("none" if not dc else
                          ("49-mural" if dc.most_common(1)[0][0] == 49 else
                           ("59-decal" if dc.most_common(1)[0][0] == 59 else
                            f"other-{dc.most_common(1)[0][0]}")))
        branch[b] += 1

    bstats = {}
    for b in branch:
        a = [r["res"] for r in rows if r["branch"] == b]
        bstats[b] = dict(n=len(a), residual=stats(a))

    # --- clusters over anomalous positions ---------------------------------------------------------
    anom = [r for r in rows if abs(r["res"]) >= ANOM_T]
    for r in anom:
        r["enclose"], r["rise"] = enclosure(ghash, samples, r["x"], r["y"], r["z"])
    pts = np.array([[r["x"], r["y"], r["z"]] for r in anom]) if anom else np.zeros((0, 3))
    clusters = []
    if anom:
        h = Hash2D(pts, cell=CLUSTER_R)
        parent = list(range(len(anom)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i, j):
            a, b = find(i), find(j)
            if a != b:
                parent[b] = a

        for i, r in enumerate(anom):
            for j, _d2 in h.query(r["x"], r["z"], CLUSTER_R):
                if j != i and (anom[j]["res"] > 0) == (r["res"] > 0):
                    union(i, j)
        groups = defaultdict(list)
        for i in range(len(anom)):
            groups[find(i)].append(i)
        for _g, idxs in groups.items():
            if len(idxs) < MIN_CLUSTER:
                continue
            P = pts[idxs]
            rs = np.array([anom[i]["res"] for i in idxs])
            xz = P[:, [0, 2]]
            c = xz.mean(axis=0)
            cov = np.cov((xz - c).T)
            ev, evec = np.linalg.eigh(cov)
            L1, L2 = math.sqrt(max(ev[1], 0)), math.sqrt(max(ev[0], 0))
            ax = evec[:, 1]
            peak_i = idxs[int(np.argmax(np.abs(rs)))]
            pk = anom[peak_i]
            near = min(anom[i]["r_crater"] for i in idxs)
            clusters.append(dict(
                n_verts=len(idxs), sign=("bump" if rs.mean() > 0 else "pit"),
                centroid_world=[round(float(c[0]), 2), round(float(c[1]), 2)],
                peak_world=[round(pk["x"], 2), round(pk["y"], 3), round(pk["z"], 2)],
                peak_residual=round(float(rs[np.argmax(np.abs(rs))]), 3),
                mean_residual=round(float(rs.mean()), 3),
                extent_major_u=round(2.0 * L1, 2), extent_minor_u=round(2.0 * L2, 2),
                elongation=round(float(L1 / L2) if L2 > 1e-6 else 999.0, 2),
                axis_xz=[round(float(ax[0]), 3), round(float(ax[1]), 3)],
                bearing_deg_from_crater=round(math.degrees(math.atan2(
                    c[1] - CRATER_WORLD[1], c[0] - CRATER_WORLD[0])), 1),
                r_crater_min=round(float(near), 2),
                r_crater_max=round(float(max(anom[i]["r_crater"] for i in idxs)), 2),
                families=dict(Counter(anom[i]["fam"] for i in idxs)),
                provenance=dict(Counter(anom[i]["prov"] for i in idxs)),
                branches=dict(Counter(anom[i]["branch"] for i in idxs)),
                frac_in_topo49_cells=round(float(np.mean([anom[i]["in_topo49_cell"] for i in idxs])), 3),
                dropped_donor_topo=dict(sum((donor["dropped_cells"].get(anom[i]["cell"], Counter())
                                             for i in idxs), Counter())),
                enclosure_frac=round(float(np.mean([anom[i]["enclose"] for i in idxs])), 3),
                enclosure_rise_u=round(float(np.median([anom[i]["rise"] for i in idxs])), 2),
                blocks=sorted({f"{math.floor(anom[i]['x']/BLOCK)},{math.floor(-anom[i]['z']/BLOCK)}"
                               for i in idxs}),
                _keys=[anom[i]["k"] for i in idxs]))
        for c in clusters:
            c["verdict"] = ("BASIN(keep)" if (c["enclosure_frac"] >= 0.70 and c["elongation"] <= 1.6
                                              and c["frac_in_topo49_cells"] < 0.20)
                            else ("channel" if c["elongation"] >= 2.0 else "pit/dig-spot"))
        clusters.sort(key=lambda c: -abs(c["peak_residual"]))

    # --- the topo-49 coincidence test over ALL anomalous verts (not just clusters) -----------------
    n_anom = len(anom)
    in49 = sum(1 for r in anom if r["in_topo49_cell"])
    base49 = sum(1 for r in rows if r["in_topo49_cell"])
    report["stage4_mechanism"] = dict(
        branch_hist=dict(branch), branch_residuals=bstats,
        anomaly_threshold_u=ANOM_T, n_anomalous_positions=n_anom,
        anomalous_in_dropped_topo49_cells=in49,
        anomalous_in_topo49_frac=round(in49 / n_anom, 3) if n_anom else None,
        all_movable_in_topo49_frac=round(base49 / len(rows), 3),
        enrichment_vs_base=round((in49 / n_anom) / (base49 / len(rows)), 2) if n_anom and base49 else None,
        r_crater_hist_of_anomalies={f"{i}-{i+10}u": sum(1 for r in anom if i <= r["r_crater"] < i + 10)
                                    for i in range(0, 130, 10)},
        n_clusters=len(clusters), clusters=clusters,
        cluster_rule=(f"proximity graph radius {CLUSTER_R}u, same-sign only, >={MIN_CLUSTER} verts; "
                      f"verdict = BASIN(keep) when enclosure>=0.70 AND elongation<=1.6 AND "
                      f"topo49-cell fraction<0.20, else channel (elongation>=2) / pit-dig-spot"))
    log(f"[s4] branches {dict(branch)}")
    log(f"[s4] anomalous positions {n_anom} -> {len(clusters)} clusters; topo49-cell frac "
        f"{in49/n_anom if n_anom else 0:.3f} vs base {base49/len(rows):.3f}")

    # --- the DROPPED-PROVENANCE split (the load-bearing discriminator) -----------------------------
    dsplit = {}
    for lab in sorted({r["drop_topo"] for r in rows}):
        a = [r["res"] for r in rows if r["drop_topo"] == lab]
        dsplit[lab] = dict(n_movable=len(a), residual=stats(a),
                           n_anomalous=sum(1 for r in anom if r["drop_topo"] == lab))
    report["stage4c_dropped_provenance"] = dict(
        by_dropped_donor_topo=dsplit,
        note=("each movable position is labelled by the MAJORITY topograph the donor DROPPED in its own "
              "4u cell (DROP_SET filter in rung_f_layout.load_donor_window). 49 = the Cleyra mural/root "
              "strips, 59 = decals. This is the clean binary that separates the root wedges from the "
              "basin the owner wants kept."))

    # --- does the anomaly extend beyond the 102 re-clothed tris? -----------------------------------
    fam_hist = Counter(r["fam"] for r in anom)
    report["stage4_beyond_the_102"] = dict(
        anomalous_positions_by_fill_family=dict(fam_hist),
        note=("fill family = uvf_fix4's per-cell family field (fill_cell_detail), the same field that "
              "chose the 102 re-clothed tris (101 dunes + 1 desert). 'grass' here = grass-resolved "
              "fill that was NOT re-clothed."),
        re_clothed_tri_count=102)
    return anom, clusters


# =================================================================================================
#  STAGE 5 -- crater safety
# =================================================================================================
def stage5(report, touched, f4_meshes, synth_key, movable, pinned, rows, ghash, samples):
    cx0, cz0 = CRATER_WORLD
    rings = defaultdict(lambda: dict(kept=[], fill=[]))
    kept_pos, fill_pos = [], []
    for b in touched:
        bm = f4_meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[CH_POS]
        tans = bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            is_synth = (b, t) in synth_key
            topo = X.decode_id(int(round(tans[tri[0]][0])))["topograph"]
            for j in tri:
                v = verts[j]
                x, y, z = v[0] + ox, v[1], v[2] + oz
                r = math.hypot(x - cx0, z - cz0)
                if r > 40.0:
                    continue
                ring = int(r // 2.0) * 2
                if is_synth:
                    rings[ring]["fill"].append(y)
                    fill_pos.append((x, y, z, r))
                else:
                    rings[ring]["kept"].append((y, topo))
                    kept_pos.append((x, y, z, r, topo))

    profile = []
    for ring in sorted(rings):
        kk = [y for y, _t in rings[ring]["kept"]]
        ff = rings[ring]["fill"]
        profile.append(dict(r_lo=ring, r_hi=ring + 2,
                            kept_n=len(kk), kept_y_p50=round(float(np.median(kk)), 3) if kk else None,
                            kept_y_p95=round(float(np.percentile(kk, 95)), 3) if kk else None,
                            kept_y_max=round(float(max(kk)), 3) if kk else None,
                            fill_n=len(ff), fill_y_p50=round(float(np.median(ff)), 3) if ff else None,
                            fill_y_max=round(float(max(ff)), 3) if ff else None,
                            fill_frac=round(len(ff) / max(1, len(ff) + len(kk)), 3)))

    # rim = the ring band with the highest kept p95; bowl = the low interior
    with_kept = [p for p in profile if p["kept_n"] >= 20]
    rim = max(with_kept, key=lambda p: p["kept_y_p95"]) if with_kept else None
    bowl = min(with_kept, key=lambda p: p["kept_y_p50"]) if with_kept else None

    # who owns the rim relief: positions inside the rim band, movable vs pinned
    rim_lo, rim_hi = (rim["r_lo"], rim["r_hi"]) if rim else (0, 0)
    band = [p for p in kept_pos if rim_lo <= p[3] < rim_hi]
    bandf = [p for p in fill_pos if rim_lo <= p[3] < rim_hi]
    inner = 0.0
    if rim:
        inner = rim["r_hi"]
    mov_inside = [r for r in rows if r["r_crater"] <= inner]
    mov_inside_anom = [r for r in mov_inside if abs(r["res"]) >= ANOM_T]

    report["stage5_crater_safety"] = dict(
        crater_center_world=[CRATER_WORLD[0], CRATER_WORLD[1]], crater_cell=list(CRATER_CELL),
        radial_profile_2u=profile,
        rim_band=rim, bowl_band=bowl,
        kept_vertex_entries_within_40u=len(kept_pos),
        fill_vertex_entries_within_40u=len(fill_pos),
        fill_share_within_40u=round(len(fill_pos) / max(1, len(fill_pos) + len(kept_pos)), 4),
        rim_band_kept_entries=len(band), rim_band_fill_entries=len(bandf),
        movable_positions_within_rim_radius=len(mov_inside),
        movable_anomalous_within_rim_radius=len(mov_inside_anom),
        movable_within_rim_residual=stats([r["res"] for r in mov_inside]) if mov_inside else dict(n=0))
    log(f"[s5] crater: kept entries<=40u {len(kept_pos)} fill {len(fill_pos)}; rim band {rim_lo}-{rim_hi}u")
    return profile, rim, bowl, mov_inside, mov_inside_anom


def stage5b(report, rows, clusters, ghash, samples):
    """THE BASIN (the feature the owner calls 'the crater') -- located, owner-split, and turned into an
    explicit EXCLUSION disc that the scope stage pins."""
    basins = [c for c in clusters if c["verdict"] == "BASIN(keep)"]
    excl = []
    basin_keys = set()
    for c in basins:
        cx, cz = c["centroid_world"]
        R = max(c["extent_major_u"], c["extent_minor_u"]) / 2.0 + 3.0
        excl.append(dict(center=[cx, cz], radius_u=round(R, 2), cluster_peak=c["peak_residual"],
                         n_anom_verts=c["n_verts"]))
        basin_keys |= set(c["_keys"])

    NEAR = 25.0     # how far the 59-decal footprint rule reaches around a basin centroid

    def in_excl(r):
        if r["k"] in basin_keys:
            return True                                     # exact cluster membership
        for e in excl:
            d = math.hypot(r["x"] - e["center"][0], r["z"] - e["center"][1])
            if d <= e["radius_u"]:
                return True                                 # the disc
            if d <= NEAR and r["drop_topo"] == "59-decal":
                return True                                 # the basin's own donor footprint
        return False

    inside = [r for r in rows if in_excl(r)]
    for r in rows:
        r["crater_excluded"] = in_excl(r)
    by_rule = Counter()
    for r in inside:
        by_rule["cluster_member" if r["k"] in basin_keys else
                ("disc" if any(math.hypot(r["x"] - e["center"][0], r["z"] - e["center"][1])
                               <= e["radius_u"] for e in excl) else "59-decal_footprint")] += 1

    # WHO OWNS THE BASIN RELIEF: the depth is the drop from the surrounding kept rim to the fill floor.
    depth = None
    if inside:
        depth = dict(fill_floor_y=stats([r["y"] for r in inside]),
                     local_kept_reference_y=stats([r["ref"] for r in inside]),
                     depth_u=stats([-r["res"] for r in inside]))
    report["stage5b_basin_exclusion"] = dict(
        n_basin_clusters=len(basins), exclusion_discs=excl,
        exclusion_rule=(f"basin-cluster membership (exact) OR inside the disc OR (within {NEAR}u of the "
                        f"basin centroid AND the cell's dropped donor topo is 59-decal)"),
        excluded_by_rule=dict(by_rule),
        n_movable_inside_exclusion=len(inside),
        n_anomalous_inside_exclusion=sum(1 for r in inside if abs(r["res"]) >= ANOM_T),
        basin_relief_ownership=depth,
        finding=("the basin FLOOR is synthesized fill sitting at exactly land_height 3.000 while its "
                 "rim is CARRIED (pinned) donor terrain -- so fill DOES participate in the feature, and "
                 "relaxing it to the local kept reference would FILL THE CRATER IN. It is therefore "
                 "excluded by construction: every movable position inside the exclusion disc is pinned "
                 "at its current Y, exactly like kept content."),
        discriminators=("(1) enclosure: the basin closes on >=70% of 16 azimuths, a root channel closes "
                        "only on its two flanks; (2) plan shape: the basin is round (elongation ~1.3), "
                        "the wedges are 2.0-16x elongated; (3) PROVENANCE: the basin's donor cells "
                        "dropped topo-59 decals, every wedge cluster's dropped topo-49 murals -- a clean "
                        "binary split, see each cluster's dropped_donor_topo."))
    log(f"[s5b] basin exclusion: {len(excl)} disc(s), {len(inside)} movable positions pinned inside")
    return excl, inside


# =================================================================================================
#  STAGE 6 -- the scope proposal
# =================================================================================================
def _basin_dem(touched, f4_meshes, synth_key, moved, centre, R=24.0, STEP=1.5, lo=2.5, hi=7.2):
    """Top-surface DEM of the basin, BEFORE (on-disk FIXED4) and AFTER the dry-run solve, as two
    glyph grids ('0'..'9' = Y lo..hi). The crater-safety proof an eye can read."""
    cx0, cz0 = centre
    n = int(2 * R / STEP) + 1

    def build(apply_dy):
        Yg = [[None] * n for _ in range(n)]
        for b in touched:
            bm = f4_meshes[b]
            ox, oz = X.block_world_origin(*b)
            verts = bm.chan_arrays[CH_POS]
            for t, tri in enumerate(bm.tris):
                pts = []
                for j in tri:
                    x, y, z = verts[j][0] + ox, verts[j][1], verts[j][2] + oz
                    if apply_dy:
                        y += moved.get(pkey((x, y, z)), 0.0)
                    pts.append((x, y, z))
                xs = [p[0] for p in pts]
                zs = [p[2] for p in pts]
                if min(xs) > cx0 + R or max(xs) < cx0 - R or min(zs) > cz0 + R or max(zs) < cz0 - R:
                    continue
                (ax, ay, az), (bx, by, bz), (cx, cy, cz) = pts
                den = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
                if abs(den) < 1e-9:
                    continue
                i0 = max(0, int((min(xs) - (cx0 - R)) / STEP))
                i1 = min(n - 1, int((max(xs) - (cx0 - R)) / STEP) + 1)
                j0 = max(0, int((min(zs) - (cz0 - R)) / STEP))
                j1 = min(n - 1, int((max(zs) - (cz0 - R)) / STEP) + 1)
                for i in range(i0, i1 + 1):
                    px = cx0 - R + i * STEP
                    for j in range(j0, j1 + 1):
                        pz = cz0 - R + j * STEP
                        l1 = ((bz - cz) * (px - cx) + (cx - bx) * (pz - cz)) / den
                        l2 = ((cz - az) * (px - cx) + (ax - cx) * (pz - cz)) / den
                        if l1 < -1e-6 or l2 < -1e-6 or 1 - l1 - l2 < -1e-6:
                            continue
                        y = l1 * ay + l2 * by + (1 - l1 - l2) * cy
                        if Yg[j][i] is None or y > Yg[j][i]:
                            Yg[j][i] = y
        return ["".join(" " if v is None else
                        "0123456789"[max(0, min(9, int((v - lo) / (hi - lo) * 10)))]
                        for v in row) for row in Yg]

    return dict(centre=[round(cx0, 2), round(cz0, 2)], half_width_u=R, step_u=STEP,
                glyph_scale=f"'0'..'9' = Y {lo}..{hi}u, ' ' = no surface",
                row_z_from=round(cz0 - R, 1), col_x_from=round(cx0 - R, 1),
                before=build(False), after_dryrun=build(True))


def _basin_check(rows, moved, excl, R=20.0):
    """After the dry-run solve: how much does anything inside/near the basin actually move, and is the
    basin still as deep as it was?"""
    out = []
    for e in excl:
        cx, cz = e["center"]
        near = [r for r in rows if math.hypot(r["x"] - cx, r["z"] - cz) <= R]
        dys = [moved.get(r["k"], 0.0) for r in near]
        floor = [r for r in near if r["crater_excluded"]]
        out.append(dict(
            center=[cx, cz], radius_checked_u=R,
            n_movable_within=len(near),
            n_excluded_within=len(floor),
            max_abs_dY_within=round(max((abs(v) for v in dys), default=0.0), 4),
            max_abs_dY_on_excluded=round(max((abs(moved.get(r["k"], 0.0)) for r in floor), default=0.0), 4),
            basin_depth_before_u=round(float(np.mean([-r["res"] for r in floor])), 3) if floor else None,
            basin_depth_after_u=round(float(np.mean([-(r["res"] + moved.get(r["k"], 0.0))
                                                     for r in floor])), 3) if floor else None))
    return out


def stage6(report, rows, anom, movable, pinned, pos_entries, touched, f4_meshes, synth_key, excl):
    """THE SCOPE PROPOSAL -- and a DRY-RUN of the proposed solve so the predicted dY is measured, not
    guessed. Nothing is written; only the linear system is built and solved in memory."""
    by_key = {r["k"]: r for r in rows}
    core = [r for r in anom if not r["crater_excluded"]]
    coreset = {r["k"] for r in core}
    unknown_keys = [r["k"] for r in rows if not r["crater_excluded"]]
    uidx = {k: i for i, k in enumerate(unknown_keys)}
    n = len(unknown_keys)

    # --- mesh edges of the synthesized patch (position-keyed) --------------------------------------
    edges = set()
    for b in touched:
        bm = f4_meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[CH_POS]
        for t, tri in enumerate(bm.tris):
            if (b, t) not in synth_key:
                continue
            ks = [pkey((verts[j][0] + ox, verts[j][1], verts[j][2] + oz)) for j in tri]
            for a in range(3):
                p, q = ks[a], ks[(a + 1) % 3]
                if p != q:
                    edges.add((min(p, q), max(p, q)))
    e_uu = [(uidx[p], uidx[q]) for p, q in edges if p in uidx and q in uidx]
    e_ub = [uidx[p] for p, q in edges if p in uidx and q not in uidx] + \
           [uidx[q] for p, q in edges if q in uidx and p not in uidx]

    # --- least squares:  W_DATA*(dY_i + res_i) on the core ; (dY_i - dY_j) on every patch edge ;
    #     (dY_i - 0) on every edge to a PINNED position (kept content or the excluded basin) ;
    #     EPS*dY_i everywhere (keeps isolated unknowns at 0)
    W_DATA, W_HOLD, W_EDGE, EPS = 4.0, 1.0, 1.0, 1e-3
    A = np.zeros((n + len(e_uu) + len(e_ub) + n, n))
    rhs = np.zeros(A.shape[0])
    r0 = 0
    for k in unknown_keys:                       # data term on EVERY unknown: strong on the anomalous
        r = by_key[k]                            # core, weak ("hold your ground") everywhere else --
        w = W_DATA if k in coreset else W_HOLD   # without the weak term the smoothness alone lifts the
        A[r0, uidx[k]] = w                       # far outer sheet off a reference it already matches.
        rhs[r0] = -w * r["res"]
        r0 += 1
    for i, j in e_uu:
        A[r0, i] = W_EDGE
        A[r0, j] = -W_EDGE
        r0 += 1
    for i in e_ub:
        A[r0, i] = W_EDGE
        r0 += 1
    for i in range(n):
        A[r0, i] = EPS
        r0 += 1
    dY, *_ = np.linalg.lstsq(A, rhs, rcond=None)

    moved = {unknown_keys[i]: float(dY[i]) for i in range(n) if abs(dY[i]) > 1e-4}
    post = np.array([by_key[k]["res"] + moved.get(k, 0.0) for k in coreset])
    newY = np.array([by_key[k]["y"] + v for k, v in moved.items()])
    report["stage6_solve_dryrun"] = dict(
        n_unknowns=n, n_core_data_rows=len(core), n_patch_edges=len(e_uu),
        n_edges_to_pinned=len(e_ub),
        weights=dict(data_core=W_DATA, data_hold_noncore=W_HOLD, edge=W_EDGE, eps=EPS),
        residual_all_unknowns_before=stats([by_key[k]["res"] for k in unknown_keys]),
        residual_all_unknowns_after=stats([by_key[k]["res"] + moved.get(k, 0.0) for k in unknown_keys]),
        n_positions_moved_gt_0p01=int(sum(1 for v in moved.values() if abs(v) > 0.01)),
        n_positions_moved_gt_0p1=int(sum(1 for v in moved.values() if abs(v) > 0.1)),
        dY=stats(list(moved.values())),
        predicted_max_abs_dY=round(float(max(abs(v) for v in moved.values())), 3) if moved else 0.0,
        core_residual_before=stats([r["res"] for r in core]),
        core_residual_after=stats(post),
        min_Y_after=round(float(newY.min()), 3) if newY.size else None,
        sea_clearance_ok=bool(newY.size == 0 or newY.min() > 0.5),
        crater_safety_under_the_solve=_basin_check(rows, moved, excl),
        largest_moves_top25=[dict(world=[round(by_key[k]["x"], 2), round(by_key[k]["y"], 3),
                                         round(by_key[k]["z"], 2)],
                                  dY=round(v, 3), res_before=round(by_key[k]["res"], 3),
                                  res_after=round(by_key[k]["res"] + v, 3),
                                  drop=by_key[k]["drop_topo"], fam=by_key[k]["fam"],
                                  prov=by_key[k]["prov"],
                                  r_crater=round(by_key[k]["r_crater"], 1))
                             for k, v in sorted(moved.items(), key=lambda kv: -abs(kv[1]))[:25]],
        unfixable_residual=dict(
            n_after_abs_gt_0p6=int(np.sum(np.abs([by_key[k]["res"] + moved.get(k, 0.0)
                                                  for k in unknown_keys]) > 0.6)),
            note=("what survives the solve is geometry the fill cannot reach: a movable position whose "
                  "whole 1-ring is PINNED kept content is held at dY~0 by the smoothness term, so its "
                  "step is carried relief, not fill relief.")),
        note="dry run only -- no bytes written; this is the exact system a fix round would solve.")
    log(f"[s6] solve dry-run: {n} unknowns, {len(core)} data rows, {len(e_uu)} patch edges, "
        f"{len(e_ub)} pin edges -> moved {len(moved)} positions, max|dY| "
        f"{max(abs(v) for v in moved.values()) if moved else 0:.3f}, core |res| p95 "
        f"{np.percentile(np.abs(post),95):.3f} (was {np.percentile([abs(r['res']) for r in core],95):.3f})")

    # --- FACE CHECK: what happens to every steep synthesized tri under the solve ------------------
    face_rows = []
    for b in touched:
        bm = f4_meshes[b]
        ox, oz = X.block_world_origin(*b)
        verts = bm.chan_arrays[CH_POS]
        for t, tri in enumerate(bm.tris):
            if (b, t) not in synth_key:
                continue
            P3 = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in tri]
            ys0 = [p[1] for p in P3]
            if max(ys0) - min(ys0) < 1.0:
                continue
            ys1 = [p[1] + moved.get(pkey(p), 0.0) for p in P3]
            cx = sum(p[0] for p in P3) / 3.0
            cz = sum(p[2] for p in P3) / 3.0
            dbasin = min((math.hypot(cx - e["center"][0], cz - e["center"][1]) for e in excl),
                         default=1e9)
            face_rows.append(dict(before=max(ys0) - min(ys0), after=max(ys1) - min(ys1),
                                  d_basin=dbasin,
                                  world=[round(cx, 2), round(cz, 2)]))
    near_basin = [f for f in face_rows if f["d_basin"] <= 12.0]
    far = [f for f in face_rows if f["d_basin"] > 12.0]
    report["stage6_face_collapse_check"] = dict(
        n_steep_faces_ge_1u=len(face_rows),
        all_faces_before=stats([f["before"] for f in face_rows]),
        all_faces_after=stats([f["after"] for f in face_rows]),
        n_still_ge_2u_after=sum(1 for f in face_rows if f["after"] >= 2.0),
        crater_wall_faces_within_12u_of_basin=dict(
            n=len(near_basin),
            y_range_before=stats([f["before"] for f in near_basin]) if near_basin else dict(n=0),
            y_range_after=stats([f["after"] for f in near_basin]) if near_basin else dict(n=0),
            max_shrink_u=round(max((f["before"] - f["after"] for f in near_basin), default=0.0), 3)),
        wedge_faces_beyond_12u=dict(
            n=len(far),
            y_range_before=stats([f["before"] for f in far]) if far else dict(n=0),
            y_range_after=stats([f["after"] for f in far]) if far else dict(n=0),
            max_shrink_u=round(max((f["before"] - f["after"] for f in far), default=0.0), 3)),
        reading=("the crater-wall faces must NOT collapse (their movable vertex is the basin floor, "
                 "pinned by the exclusion) while the wedge faces must. Compare the two max_shrink_u."))

    # --- a compact DEM of the basin, before and under the dry-run solve ---------------------------
    if excl:
        report["stage6_basin_dem"] = _basin_dem(touched, f4_meshes, synth_key, moved, excl[0]["center"])

    # the blend ring = the unknowns that are NOT core but do move (>1cm) under the solve
    blend = {k for k, v in moved.items() if k not in coreset and abs(v) > 0.01}
    report["stage6_scope_proposal"] = dict(
        anomaly_threshold_u=ANOM_T,
        moved_vert_set=dict(
            core_anomalous_movable_positions=len(coreset),
            blend_ring_positions_that_actually_move=len(blend),
            total_positions_moved_gt_1cm=int(sum(1 for v in moved.values() if abs(v) > 0.01)),
            movable_universe=len(movable)),
        pin_set=dict(
            kept_coincident_positions=len(pinned),
            fill_positions_inside_the_basin_exclusion=sum(1 for r in rows if r["crater_excluded"]),
            out_of_scope_fill_positions=n - len(coreset) - len(blend),
            note=("every position with >=1 kept vertex entry is Dirichlet at its current Y; so is every "
                  "movable position inside the basin exclusion disc -- that is what keeps the crater.")),
        blend_falloff=("NOT a distance falloff -- the blend is the SOLUTION of the Laplacian on the "
                       "synthesized patch's own edge graph, so the fall-off follows the mesh and reaches "
                       "zero exactly at the pins. Measured reach: the moved set is "
                       f"{int(sum(1 for v in moved.values() if abs(v) > 0.01))} positions, of which "
                       f"{len(blend)} are ring (non-core)."),
        method_recommended="harmonic / Laplacian least-squares on the synthesized patch (dry-run above)",
        method_argument=(
            "Two candidates. (A) DIRECT relax-to-reference with a distance falloff: cheap, but the "
            "falloff is a distance function, not a mesh function -- a ring vertex sitting BETWEEN a moved "
            "vertex and a PINNED kept vertex gets pulled without knowing the pin, so the step is merely "
            "RELOCATED onto the pin. That is precisely the terminal-face artifact being reported, so (A) "
            "risks reproducing the defect one vertex over. (B) HARMONIC: unknowns = every non-excluded "
            "movable position, Dirichlet dY=0 at every pinned position (kept-coincident + basin), data "
            "term dY = -residual on the anomalous core, smoothness (dY_i - dY_j) on every synthesized-"
            "patch edge. It is C0 into the pins BY CONSTRUCTION -- no new step can be minted at the "
            f"boundary -- and it is tiny here ({n} unknowns / {len(e_uu)} edges, one dense lstsq in "
            "well under a second). RECOMMEND (B); keep (A) as an A/B sanity check on the patch interior."),
        weld_law=("the solve is keyed on the ROUNDED 3D WORLD POSITION, so every vertex entry at a moved "
                  "position (across parts of a block AND across block borders -- "
                  f"{sum(1 for k in moved if len({e[0] for e in pos_entries[k]}) > 1)} of the moved "
                  "positions are multi-block) receives the identical dY; a position with any kept entry "
                  "is never an unknown."),
        invariants=("Y-only (X/Z fixed); UVs/tangents/indices untouched; per-tri geometric up-facing "
                    "normals recomputed for every tri with a moved vert; verts==idx preserved (no tri "
                    "added or removed); every moved Y stays above Sea Y=0 (measured min "
                    f"{round(float(newY.min()), 3) if newY.size else None}u)."))
    log(f"[s6] scope: core {len(coreset)} + ring {len(blend)}; basin-excluded "
        f"{sum(1 for r in rows if r['crater_excluded'])}")
    return coreset, blend, moved


# =================================================================================================
def main():
    report = {"meta": dict(script="uvf_relief_probe.py", read_only=True, tree=str(FIXED4),
                           crater_world=list(CRATER_WORLD), anomaly_threshold_u=ANOM_T)}
    touched, f4_meshes, defective, synth_key, prov_of, pos_entries, pinned, movable = stage1(report)

    fix4 = json.loads(FIX4_REPORT.read_text(encoding="utf-8"))
    fill_fam_of_cell = {}
    for k, v in fix4["fill_cell_detail"].items():
        a, b = k.split(",")
        fill_fam_of_cell[(int(a), int(b))] = v["fam"]

    ground_pos, ghash, samples = stage2(report, touched, f4_meshes, synth_key)
    rows = stage3(report, movable, pos_entries, prov_of, ghash, samples, fill_fam_of_cell)
    donor = load_donor(report)
    stage4b(report, touched, f4_meshes, synth_key, movable, pinned, prov_of)
    anom, clusters = stage4(report, rows, donor, ghash, samples)
    stage5(report, touched, f4_meshes, synth_key, movable, pinned, rows, ghash, samples)
    excl, _inside = stage5b(report, rows, clusters, ghash, samples)
    stage6(report, rows, anom, movable, pinned, pos_entries, touched, f4_meshes, synth_key, excl)

    for c in report["stage4_mechanism"]["clusters"]:
        c.pop("_keys", None)
    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
