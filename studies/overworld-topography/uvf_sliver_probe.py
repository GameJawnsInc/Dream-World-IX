"""RUNG F -- THE SLIVER-STEP PROBE (round 7 forensics, 2026-07-25).

Playtest 5 on FIXED6 (round 6's carried-spike shave): "they're mostly flattened but ONE sticks out in
particular and has a noticeably different texture than the sand".  The owner stood WNW of the crater
(centre (127.14,-1161.42)); the feature is a small raised patch just south of them wearing a mottled,
non-sand look.

THE HYPOTHESIS UNDER TEST (the orchestrator's diagnosis, verified here, not assumed): the round-6
textured render shows bright lens/leaf-shaped SLIVER FACES radiating around the crater.  These are STEP
faces where round-5's relaxed fill sheet meets PINNED carried high ground -- the class round 5 flagged
as "12 fully-pinned positions, unreachable by any fill-only relax", and round 6's local-maximum rule
deliberately skipped (a step EDGE is not a local MAX).  A steep face wearing plan-projected ground mains
also SMEARS its texture (UV keyed on x,z, so a near-vertical face stretches one tile over the whole
drop) = the owner's "noticeably different texture".

LANE 1 -- THE SLIVER CENSUS on FIXED6: every Terrain tri within r<=40u of the crater with internal
  y-span >= 1.0u, edge-clustered into faces; per face world position / span / dip / 3D area / top-vertex
  ownership (carried-pinned vs carried-moved vs fill) / texture family + class / anisotropic UV-stretch
  (max singular value of the uv->world Jacobian, vs the tree's own flat-ground baseline).  Cross-
  referenced against the round-6 mound render (a 92u-wide, sc=10 top-down centred on the crater) by
  luminance contrast, and each face gets a zoom crop for the eye.

LANE 2 -- THE STOCK STEEP-FACE LANGUAGE (read-only stock, the fundamentals): the same instrument over
  the REAL dunes mass (18,3)(18,4)(19,3)(19,4)(20,3) and the Cleyra grass|desert junction (13-15,11-12).
  Dip distribution of ground-family tris; what UVs the >=30/45/60deg faces actually wear (family mains?
  a wall/crest band row? free fractional windows?); the UV-stretch they carry vs flat neighbours; and
  whether stock's dunes interior even CONTAINS faces as steep/tall as our slivers.

READ-ONLY vs the game install and vs every artifact tree.  Writes only
out/rung_f/uvf_sliver_probe.json + out/rung_f/renders/sliver7/*.png.  No git, no deploy.

    py -X utf8 uvf_sliver_probe.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X            # noqa: E402
from ff9mapkit.world import mesh as M               # noqa: E402
from ff9mapkit.world import grassland as G          # noqa: E402
from ff9mapkit.world import island as ISL           # noqa: E402

import seam_null_recon as SNR                       # noqa: E402  (FAM_OF / RECTS / classify_tri)
import uvf_stock_census as SC                       # noqa: E402  (classify_tri_plus / WALL_RECTS)
import uvf_fix2 as F2                               # noqa: E402  (terr_path / uv_degenerate)
import uvf_fix3 as F3                               # noqa: E402  (load_blocks / classify_defective)
import uvf_relief_probe as RP                       # noqa: E402  (Hash2D / ref_at -- reused verbatim)

CH_POS, CH_UV, CH_TAN = X.CH_POS, X.CH_UV, X.CH_TAN

RUNG_F = HERE / "out" / "rung_f"
SPEC = RUNG_F / "FF9CustomMap-world"
FIXED5 = RUNG_F / "FF9CustomMap-world-FIXED5"
FIXED6 = RUNG_F / "FF9CustomMap-world-FIXED6"
BUILD_JSON = RUNG_F / "rung_f_build.json"
FORENSICS = RUNG_F / "uvf_forensics.json"
REPORT = RUNG_F / "uvf_sliver_probe.json"
RENDER_DIR = RUNG_F / "renders" / "sliver7"
MOUND_PNG = RUNG_F / "renders" / "uvfix6" / "fixed6_mound_textured_shaded.png"
SLOPE_PNG = RUNG_F / "renders" / "uvfix6" / "fixed6_mound_slope_mag.png"

BASIN_C = (127.14, -1161.42)
BASIN_R = 7.92
SCAN_R = 40.0
SPAN_T = 1.0                       # LANE 1 sliver threshold, per the work order
POS_DP = 3

# the round-6 mound render frame: crop_world(canvas, *BASIN_C, 46.0) at sc=10
REN_SC = 10.0
REN_R = 46.0
REN_WX0 = BASIN_C[0] - REN_R
REN_WZ1 = BASIN_C[1] + REN_R

STOCK_DUNES = [(18, 3), (18, 4), (19, 3), (19, 4), (20, 3)]
STOCK_JUNCTION = [(13, 11), (14, 11), (15, 11), (13, 12), (14, 12), (15, 12)]

GROUND_FAMS = {"grass", "desert", "dunes", "scrub", "brush", "snow", "canyon"}

STEEP_T = 25.0                     # LANE 1b: the dip a "sliver/step face" starts at
RES_T = 0.8                        # round 6's residual gate, reused verbatim
PROM_T = 0.4                       # round 6's mesh-prominence gate, reused verbatim
FIX6_REPORT = RUNG_F / "uvf_fix6_report.json"


def log(m):
    print(m, flush=True)


def pkey(p):
    return (round(float(p[0]), POS_DP), round(float(p[1]), POS_DP), round(float(p[2]), POS_DP))


def rc(x, z):
    return math.hypot(x - BASIN_C[0], z - BASIN_C[1])


def bearing(x, z):
    """compass bearing of (x,z) from the crater centre.  OVERWORLD CARDINALS: block index by grows
    SOUTHWARD and world z = -by*64, so NORTH = +z, EAST = +x (the rasterizer draws +z upward)."""
    dx, dz = x - BASIN_C[0], z - BASIN_C[1]
    ang = math.degrees(math.atan2(dx, dz)) % 360.0        # 0 = N(+z), 90 = E(+x)
    names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
             "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return names[int((ang + 11.25) // 22.5) % 16], round(ang, 1)


# =================================================================================================
#  per-tri geometry + the anisotropic UV Jacobian
# =================================================================================================
def area3d(w3):
    a, b, c = w3
    e1 = [b[k] - a[k] for k in range(3)]
    e2 = [c[k] - a[k] for k in range(3)]
    cx = e1[1] * e2[2] - e1[2] * e2[1]
    cy = e1[2] * e2[0] - e1[0] * e2[2]
    cz = e1[0] * e2[1] - e1[1] * e2[0]
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz), (cx, cy, cz)


def plan_area(w3):
    (x0, _a, z0), (x1, _b, z1), (x2, _c, z2) = w3
    return abs((x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)) / 2.0


def dip_deg(w3):
    a3, n = area3d(w3)
    if a3 < 1e-9:
        return None
    nl = math.sqrt(sum(c * c for c in n))
    return math.degrees(math.acos(min(1.0, abs(n[1]) / nl)))


def uv_area(uv3):
    (u0, v0), (u1, v1), (u2, v2) = uv3
    return abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) / 2.0


def uv_jacobian_sigmas(w3, uv3):
    """singular values (world units per UV unit) of the affine uv->world3D map.  sigma_max is the
    WORST-CASE texel smear direction; a plan-projected flat ground tri has sigma_max == sigma_min ==
    1/GRASS_DENSITY ~= 92.  Returns (sigma_max, sigma_min) or None when the UVs are degenerate."""
    q = np.array([[uv3[1][0] - uv3[0][0], uv3[2][0] - uv3[0][0]],
                  [uv3[1][1] - uv3[0][1], uv3[2][1] - uv3[0][1]]], dtype=float)
    if abs(np.linalg.det(q)) < 1e-12:
        return None
    e = np.array([[w3[1][k] - w3[0][k], w3[2][k] - w3[0][k]] for k in range(3)], dtype=float)
    a = e @ np.linalg.inv(q)
    s = np.linalg.svd(a, compute_uv=False)
    return float(s[0]), float(s[1])


# =================================================================================================
#  tri extraction, shared by both lanes
# =================================================================================================
def tris_of_blockmesh(bm, bx, by):
    ox, oz = X.block_world_origin(bx, by)
    verts = bm.chan_arrays[CH_POS]
    uvs = bm.chan_arrays[CH_UV]
    tans = bm.chan_arrays[CH_TAN]
    out = []
    for t, tri in enumerate(bm.tris):
        w = [(float(verts[j][0]) + ox, float(verts[j][1]), float(verts[j][2]) + oz) for j in tri]
        uv = [(float(uvs[j][0]), float(uvs[j][1])) for j in tri]
        topo = X.decode_id(int(round(tans[tri[0]][0])))["topograph"]
        out.append(dict(block=(bx, by), tri=t, w=w, uv=uv, topo=topo,
                        fam=SNR.FAM_OF.get(topo), keys=[pkey(p) for p in w]))
    return out


def enrich(rec):
    w, uv = rec["w"], rec["uv"]
    ys = [p[1] for p in w]
    a3, _n = area3d(w)
    pa = plan_area(w)
    rec["span"] = round(max(ys) - min(ys), 4)
    rec["area3d"] = round(a3, 5)
    rec["plan_area"] = round(pa, 5)
    rec["dip"] = None if a3 < 1e-9 else round(dip_deg(w), 2)
    rec["uv_area"] = uv_area(uv)
    rec["uv_degenerate"] = rec["uv_area"] < 1e-9
    sig = uv_jacobian_sigmas(w, uv)
    rec["sigma_max"] = None if sig is None else round(sig[0], 3)
    rec["sigma_min"] = None if sig is None else round(sig[1], 3)
    rec["geom_stretch"] = None if pa < 1e-9 else round(a3 / pa, 4)      # == 1/cos(dip)
    cx = sum(p[0] for p in w) / 3.0
    cy = sum(p[1] for p in w) / 3.0
    cz = sum(p[2] for p in w) / 3.0
    rec["centroid"] = (round(cx, 3), round(cy, 3), round(cz, 3))
    cls, det = SC.classify_tri_plus(rec["fam"], uv) if rec["fam"] else ("no_family", None)
    rec["uv_class"] = cls
    rec["uv_detail"] = det if isinstance(det, (str, int, float, type(None))) else str(det)
    return rec


def flat_baseline(recs):
    """median sigma_max over dip<5deg, non-degenerate, ground-family tris."""
    v = [r["sigma_max"] for r in recs
         if r["fam"] in GROUND_FAMS and r["dip"] is not None and r["dip"] < 5.0
         and r["sigma_max"] is not None]
    if not v:
        return None
    return float(np.median(v))


# =================================================================================================
#  edge-connected face clustering
# =================================================================================================
def cluster_faces(recs):
    """union-find over SHARED EDGES (unordered pkey pairs) -- a face is a connected run of steep
    tris welded along their edges, which is what a lens/leaf sliver actually is."""
    parent = list(range(len(recs)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    edge_owner = defaultdict(list)
    for i, r in enumerate(recs):
        ks = r["keys"]
        for a in range(3):
            e = tuple(sorted((ks[a], ks[(a + 1) % 3])))
            edge_owner[e].append(i)
    for e, owners in edge_owner.items():
        for j in owners[1:]:
            union(owners[0], j)
    groups = defaultdict(list)
    for i in range(len(recs)):
        groups[find(i)].append(i)
    return list(groups.values())


# =================================================================================================
#  LANE 1 -- the FIXED6 sliver census
# =================================================================================================
def lane1(report):
    build = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    assert len(touched) == 20, len(touched)

    # -- the synth (fill) classifier of record: the SPECIMEN's degenerate UVs, keyed by (block,tri).
    #    (block,tri) is index-stable across rounds 1-6 (UV-only + Y-only edits) -- asserted below.
    forensics = json.loads(FORENSICS.read_text(encoding="utf-8"))
    apron_keys = {(tuple(r["block"]), round(r["centroid"][0], 3), round(r["centroid"][2], 3))
                  for r in forensics["records"]
                  if r.get("uv_verdict") == "degenerate-zero-area" and r["provenance"] == "apron"}
    spec_meshes = F3.load_blocks(SPEC, touched)
    defective, _lawful = F3.classify_defective(spec_meshes, apron_keys, touched)
    synth_key = {(d["block"], d["tri"]) for d in defective}

    f6 = F3.load_blocks(FIXED6, touched)
    f5 = F3.load_blocks(FIXED5, touched)
    idx_diff = xz_diff = 0
    moved_pairs = []           # (fixed5 key, fixed6 key) for the 12 round-6 Y moves
    for b in touched:
        a6 = M.read_ff9mesh(F2.terr_path(FIXED6, *b))
        a5 = M.read_ff9mesh(F2.terr_path(FIXED5, *b))
        idx_diff += (a6["indices"] != a5["indices"]) + (a6["vcount"] != a5["vcount"])
        ox, oz = X.block_world_origin(*b)
        for j in range(min(a6["vcount"], a5["vcount"])):
            p, q = a6["verts"][j], a5["verts"][j]
            xz_diff += (p[0] != q[0] or p[2] != q[2])
            if p[1] != q[1]:
                moved_pairs.append((pkey((q[0] + ox, q[1], q[2] + oz)),
                                    pkey((p[0] + ox, p[1], p[2] + oz))))
    assert idx_diff == 0 and xz_diff == 0, (idx_diff, xz_diff)
    moved_now = {b for _a, b in moved_pairs}

    # -- the position ledger on FIXED6's OWN bytes ------------------------------------------------
    all_recs = []
    kept_ground, kept_rock, synth_pos = defaultdict(set), defaultdict(set), set()
    for b in touched:
        for r in tris_of_blockmesh(f6[b], *b):
            r["is_synth"] = (r["block"], r["tri"]) in synth_key
            all_recs.append(r)
            for k in r["keys"]:
                if r["is_synth"]:
                    synth_pos.add(k)
                elif G.TOPO_FAMILY.get(r["topo"]) is not None:
                    kept_ground[k].add(r["topo"])
                else:
                    kept_rock[k].add(r["topo"])
    fill = {k for k in synth_pos if k not in kept_ground and k not in kept_rock}
    for r in all_recs:
        enrich(r)

    base_sigma = flat_baseline(all_recs)
    log(f"[L1] {len(all_recs)} Terrain tris over 20 blocks; flat sigma_max baseline "
        f"{base_sigma:.3f} world-u per uv-u (1/GRASS_DENSITY = {1/G.GRASS_DENSITY:.3f})")

    def own(k):
        if k in kept_rock:
            return "carried-rock"
        if k in kept_ground:
            return "carried-moved-r6" if k in moved_now else "carried-pinned"
        if k in fill:
            return "fill"
        return "unknown"

    near = [r for r in all_recs
            if min(rc(p[0], p[2]) for p in r["w"]) <= SCAN_R]
    slivers = [r for r in near if r["span"] >= SPAN_T]
    log(f"[L1] near-crater(r<={SCAN_R}) tris {len(near)}; span>={SPAN_T}u -> {len(slivers)} tris")

    groups = cluster_faces(slivers)
    faces = []
    for gi, idxs in enumerate(sorted(groups, key=lambda g: -sum(slivers[i]["area3d"] for i in g))):
        rs = [slivers[i] for i in idxs]
        ymax = max(p[1] for r in rs for p in r["w"])
        ymin = min(p[1] for r in rs for p in r["w"])
        a3 = sum(r["area3d"] for r in rs)
        cx = sum(r["centroid"][0] * r["area3d"] for r in rs) / a3
        cz = sum(r["centroid"][2] * r["area3d"] for r in rs) / a3
        cy = sum(r["centroid"][1] * r["area3d"] for r in rs) / a3
        topk = [k for r in rs for k in r["keys"] if k[1] >= ymax - 0.05]
        botk = [k for r in rs for k in r["keys"] if k[1] <= ymin + 0.05]
        own_top = Counter(own(k) for k in set(topk))
        own_bot = Counter(own(k) for k in set(botk))
        sig = [r["sigma_max"] for r in rs if r["sigma_max"] is not None]
        stretch = [r["sigma_max"] / base_sigma for r in rs if r["sigma_max"] is not None]
        gs = [r["geom_stretch"] for r in rs if r["geom_stretch"] is not None]
        bname, bang = bearing(cx, cz)
        xs = [p[0] for r in rs for p in r["w"]]
        zs = [p[2] for r in rs for p in r["w"]]
        faces.append(dict(
            face_id=gi, n_tris=len(rs),
            centroid_world=[round(cx, 3), round(cy, 3), round(cz, 3)],
            bbox_world=[round(min(xs), 2), round(min(zs), 2), round(max(xs), 2), round(max(zs), 2)],
            plan_extent_u=[round(max(xs) - min(xs), 2), round(max(zs) - min(zs), 2)],
            r_crater=round(rc(cx, cz), 2), bearing=bname, bearing_deg=bang,
            y_top=round(ymax, 3), y_bottom=round(ymin, 3),
            max_span_u=round(max(r["span"] for r in rs), 3),
            face_drop_u=round(ymax - ymin, 3),
            max_dip_deg=round(max(r["dip"] for r in rs if r["dip"] is not None), 2),
            median_dip_deg=round(float(np.median([r["dip"] for r in rs if r["dip"] is not None])), 2),
            area3d_u2=round(a3, 3),
            plan_area_u2=round(sum(r["plan_area"] for r in rs), 3),
            geom_stretch_max=round(max(gs), 3) if gs else None,
            top_vertex_ownership=dict(own_top), bottom_vertex_ownership=dict(own_bot),
            all_pinned_top=(own_top.get("carried-pinned", 0) > 0
                            and own_top.get("fill", 0) == 0),
            topo=sorted({r["topo"] for r in rs}),
            family=sorted({r["fam"] for r in rs if r["fam"]}),
            uv_class=dict(Counter(r["uv_class"] for r in rs)),
            uv_detail=dict(Counter(str(r["uv_detail"]) for r in rs)),
            sigma_max_worldu_per_uvu=round(max(sig), 2) if sig else None,
            uv_stretch_x_flat=round(max(stretch), 3) if stretch else None,
            uv_stretch_median=round(float(np.median(stretch)), 3) if stretch else None,
            n_synth_tris=sum(1 for r in rs if r["is_synth"]),
            n_carried_tris=sum(1 for r in rs if not r["is_synth"]),
            tris=[f"{r['block']}#{r['tri']}" for r in rs],
        ))

    # ---- render cross-reference -----------------------------------------------------------------
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    ren = np.asarray(Image.open(MOUND_PNG).convert("RGB"), dtype=np.float32)
    lum = 0.2126 * ren[..., 0] + 0.7152 * ren[..., 1] + 0.0722 * ren[..., 2]
    H, W = lum.shape
    rows, cols = np.mgrid[0:H, 0:W]
    wx = REN_WX0 + (cols + 0.5) / REN_SC
    wz = REN_WZ1 - (rows + 0.5) / REN_SC
    log(f"[L1] mound render {W}x{H}px, world x[{REN_WX0:.2f},{REN_WX0+W/REN_SC:.2f}] "
        f"z[{REN_WZ1-H/REN_SC:.2f},{REN_WZ1:.2f}]")

    for f in faces:
        cx, _cy, cz = f["centroid_world"]
        rad = max(0.9, 0.5 * max(f["plan_extent_u"]))
        d2 = (wx - cx) ** 2 + (wz - cz) ** 2
        inn = d2 <= rad ** 2
        ring = (d2 > (rad + 1.5) ** 2) & (d2 <= (rad + 6.0) ** 2)
        f["render_px"] = [int(round((cx - REN_WX0) * REN_SC)), int(round((REN_WZ1 - cz) * REN_SC))]
        if inn.any() and ring.any():
            li, lr = float(lum[inn].mean()), float(lum[ring].mean())
            f["render_lum_face"] = round(li, 2)
            f["render_lum_ring"] = round(lr, 2)
            f["render_lum_contrast"] = round(li - lr, 2)
            f["render_bright_sliver"] = bool(li - lr >= 12.0)
        else:
            f["render_lum_face"] = f["render_lum_ring"] = f["render_lum_contrast"] = None
            f["render_bright_sliver"] = None
        # zoom crop, 16u wide, 6x nearest upscale
        c0 = int(round((cx - 8 - REN_WX0) * REN_SC)); c1 = c0 + int(16 * REN_SC)
        r0 = int(round((REN_WZ1 - (cz + 8)) * REN_SC)); r1 = r0 + int(16 * REN_SC)
        if 0 <= c0 and c1 <= W and 0 <= r0 and r1 <= H:
            crop = Image.open(MOUND_PNG).convert("RGB").crop((c0, r0, c1, r1)).resize(
                (int(16 * REN_SC * 3), int(16 * REN_SC * 3)), Image.NEAREST)
            p = RENDER_DIR / f"face{f['face_id']:02d}_{f['bearing']}_zoom.png"
            crop.save(p)
            f["zoom_png"] = p.name

    # ---- LANE 1b: the STEEP-tri sub-census (the actual lens/leaf slivers) ------------------------
    steep = [r for r in near if r["dip"] is not None and r["dip"] >= STEEP_T]
    sfaces = []
    for gi, idxs in enumerate(sorted(cluster_faces(steep),
                                     key=lambda g: -sum(steep[i]["area3d"] for i in g))):
        rs = [steep[i] for i in idxs]
        ymax = max(p[1] for r in rs for p in r["w"])
        ymin = min(p[1] for r in rs for p in r["w"])
        a3 = sum(r["area3d"] for r in rs)
        cx = sum(r["centroid"][0] * r["area3d"] for r in rs) / a3
        cz = sum(r["centroid"][2] * r["area3d"] for r in rs) / a3
        topk = {k for r in rs for k in r["keys"] if k[1] >= ymax - 0.05}
        sig = [r["sigma_max"] for r in rs if r["sigma_max"] is not None]
        bn, ba = bearing(cx, cz)
        xs = [p[0] for r in rs for p in r["w"]]
        zs = [p[2] for r in rs for p in r["w"]]
        sfaces.append(dict(
            sface_id=gi, n_tris=len(rs),
            centroid_world=[round(cx, 3), round(cz, 3)], r_crater=round(rc(cx, cz), 2),
            bearing=bn, bearing_deg=ba,
            plan_extent_u=[round(max(xs) - min(xs), 2), round(max(zs) - min(zs), 2)],
            drop_u=round(ymax - ymin, 3), y_top=round(ymax, 3),
            max_dip_deg=round(max(r["dip"] for r in rs), 2),
            median_dip_deg=round(float(np.median([r["dip"] for r in rs])), 2),
            area3d_u2=round(a3, 3),
            top_vertex_ownership=dict(Counter(own(k) for k in topk)),
            topo=sorted({r["topo"] for r in rs}),
            uv_class=dict(Counter(r["uv_class"] for r in rs)),
            uv_stretch_x_flat_max=round(max(sig) / base_sigma, 3) if sig else None,
            inside_basin_disc=bool(rc(cx, cz) <= BASIN_R),
            tris=[f"{r['block']}#{r['tri']}" for r in rs]))

    # ---- LANE 1c: THE TEXTURE CENSUS -- every near-crater tri NOT wearing its family mains -------
    odd = [r for r in near if r["uv_class"] not in ("mains_own",)]
    uncat = [r for r in near if r["uv_class"] == "other_uncatalogued"]
    uncat_rows = []
    for r in sorted(uncat, key=lambda r: rc(r["centroid"][0], r["centroid"][2])):
        us = [u for u, _v in r["uv"]]
        vs = [v for _u, v in r["uv"]]
        bn, ba = bearing(r["centroid"][0], r["centroid"][2])
        uncat_rows.append(dict(
            tri=f"{r['block']}#{r['tri']}", centroid=[r["centroid"][0], r["centroid"][2]],
            r_crater=round(rc(r["centroid"][0], r["centroid"][2]), 2), bearing=bn,
            dip=r["dip"], span=r["span"], area3d=r["area3d"], topo=r["topo"],
            uv_rect=[round(min(us), 5), round(min(vs), 5), round(max(us), 5), round(max(vs), 5)],
            sigma_max=r["sigma_max"],
            uv_stretch_x_flat=round(r["sigma_max"] / base_sigma, 3) if r["sigma_max"] else None,
            is_synth=r["is_synth"],
            verts=[[round(c, 3) for c in p] for p in r["w"]]))

    # ---- LANE 1d: render-side bright-blob detection (the "bright slivers" made objective) --------
    blobs = render_blobs(lum, wx, wz)

    # ---- LANE 1e: the residual / prominence RE-CENSUS on FIXED6's own bytes ----------------------
    ridge = ridge_census(kept_ground, kept_rock, fill, adj_of(all_recs), moved_now)

    # ---- LANE 1f: THE SMEAR LEDGER -- how far our UV stretch runs past stock's ceiling ------------
    smear = []
    for lo, hi in ((1.0, 1.2), (1.2, 1.5), (1.5, 2.0), (2.0, 99.0)):
        sel = [r for r in near if r["sigma_max"] and lo <= r["sigma_max"] / base_sigma < hi]
        smear.append(dict(bucket=f"{lo}-{hi if hi < 90 else 'inf'}x", n=len(sel),
                          area3d_u2=round(sum(r["area3d"] for r in sel), 2),
                          dip_p50=round(float(np.median([r["dip"] for r in sel
                                                         if r["dip"] is not None])), 1) if sel else None,
                          uv_class=dict(Counter(r["uv_class"] for r in sel)),
                          synth_frac=round(sum(1 for r in sel if r["is_synth"]) / len(sel), 3)
                          if sel else None))

    # ---- LANE 1g: THE DONOR IDENTITY -- is THE ONE our geometry or a verbatim stock carry? -------
    donor = donor_identity(kept_ground, fill, adj_of(all_recs))

    # ---- THE ONE --------------------------------------------------------------------------------
    the_one = pick_the_one(uncat_rows, ridge, blobs, sfaces)

    report["lane1_sliver_census"] = dict(
        tree=str(FIXED6),
        scan=dict(crater_center=list(BASIN_C), scan_radius_u=SCAN_R, span_threshold_u=SPAN_T,
                  n_terrain_tris_all=len(all_recs), n_tris_within_scan=len(near),
                  n_sliver_tris=len(slivers), n_faces=len(faces)),
        flat_uv_baseline=dict(
            sigma_max_worldu_per_uvu=round(base_sigma, 4),
            theoretical_1_over_grass_density=round(1.0 / G.GRASS_DENSITY, 4),
            note=("sigma_max = largest singular value of the affine uv->world3D map = world units "
                  "spanned by one UV unit in the worst direction.  A plan-projected FLAT ground tri "
                  "sits at the baseline; a dipping tri wearing the same plan-projected mains carries "
                  "sigma_max = baseline/cos(dip), i.e. its texels are physically longer = SMEAR.")),
        round6_moves=dict(n_positions_moved=len(moved_now),
                          moved_positions=[list(k) for k in sorted(moved_now)]),
        position_ledger=dict(carried_ground=len(kept_ground), carried_rock=len(kept_rock),
                             fill=len(fill)),
        faces=faces,
        steep_faces=dict(threshold_dip_deg=STEEP_T, n_tris=len(steep), n_faces=len(sfaces),
                         faces=sfaces),
        texture_census=dict(
            n_near_tris=len(near),
            uv_class_hist=dict(Counter(r["uv_class"] for r in near)),
            n_not_own_mains=len(odd),
            n_uncatalogued=len(uncat),
            uncatalogued_tris=uncat_rows,
            note=("'other_uncatalogued' = the tri's UVs land in NO rect this study has catalogued "
                  "(family mains, the two STRIPS decal columns, or a family's translated rock/wall "
                  "band).  Every near-crater instance is a CARRIED topo-41 dunes tri, and all 10 wear "
                  "ONE rect -- see lane2: the same rect is what STOCK's own steep dunes faces wear at "
                  "the Cleyra junction, so this is real carried vocabulary, not a defect.")),
        render_blobs=blobs,
        ridge_census=ridge,
        smear_ledger=smear,
        donor_identity=donor,
        THE_ONE=the_one,
    )
    return dict(faces=faces, sfaces=sfaces, base_sigma=base_sigma, all_recs=all_recs,
                uncat=uncat_rows, ridge=ridge, the_one=the_one, donor=donor, smear=smear)


# =================================================================================================
#  LANE 1g -- THE DONOR IDENTITY
#  The mound's terrain is a MESH CARRY off the Cleyra-junction dunes donor, translated by
#  shift_world and lifted by DY (both read from uvf_fix6_report.json's stage4_donor_overlay -- a
#  transform, not a verdict).  Everything measured here is this script's own.
# =================================================================================================
def donor_identity(kept_ground, fill, adj):
    fix6 = json.loads(FIX6_REPORT.read_text(encoding="utf-8"))
    ov = fix6["stage4_donor_overlay"]
    sx, sz = float(ov["shift_world"][0]), float(ov["shift_world"][1])
    dy = float(ov["DY"])

    stock, _miss = read_stock(STOCK_JUNCTION)
    sy = defaultdict(set)
    for r in stock:
        for k in r["keys"]:
            sy[(round(k[0], 3), round(k[2], 3))].add(k[1])

    def dy_at(k):
        c = sy.get((round(k[0] - sx, 3), round(k[2] - sz, 3)))
        return None if not c else [y + dy for y in c]

    # (a) how faithful is the CARRIED half?  (the control that makes (b) readable)
    carried_delta, exact = [], set()
    for k in kept_ground:
        if rc(k[0], k[2]) > SCAN_R or rc(k[0], k[2]) <= BASIN_R:
            continue
        c = dy_at(k)
        if not c:
            continue
        d = k[1] - min(c, key=lambda y: abs(y - k[1]))
        carried_delta.append(d)
        if abs(d) < 0.01:
            exact.add(k)

    # (b) FILL positions sitting INSIDE intact carried donor terrain = holes in the carry that
    #     round 5's relax then pulled DOWN.  ">=4 donor-exact carried neighbours" is what makes the
    #     donor height at that XZ trustworthy (a fringe fill vertex coincidentally sharing XZ with
    #     some far-away donor hilltop has ~0).
    holes = []
    for k in fill:
        if rc(k[0], k[2]) > SCAN_R or rc(k[0], k[2]) <= BASIN_R:
            continue
        c = dy_at(k)
        if not c:
            continue
        nb_ok = sum(1 for n in adj[k] if n in exact)
        if nb_ok < 4:
            continue
        best = min(c, key=lambda y: abs(y - k[1]))
        holes.append(dict(pos=[k[0], k[1], k[2]], donor_y=round(best, 3),
                          delta_u=round(k[1] - best, 3), donor_exact_neighbours=nb_ok,
                          degree=len(adj[k]), r_crater=round(rc(k[0], k[2]), 2),
                          bearing=bearing(k[0], k[2])[0]))
    holes.sort(key=lambda h: h["delta_u"])

    # (c) THE ONE's own knob, side by side with its donor original
    apex = (116.0, 6.341, -1164.0)
    donor_apex = (round(apex[0] - sx, 3), round(apex[2] - sz, 3))
    pairs = []
    for n in sorted(adj[apex], key=lambda k: -k[1]):
        c = dy_at(n)
        pairs.append(dict(pos=[n[0], n[1], n[2]],
                          dist_u=round(math.hypot(n[0] - apex[0], n[2] - apex[2]), 2),
                          drop_from_apex_u=round(apex[1] - n[1], 3),
                          donor_y=None if not c else round(min(c, key=lambda y: abs(y - n[1])), 3),
                          kind=("carried" if n in kept_ground else "fill")))
    live_drop = max(p["drop_from_apex_u"] for p in pairs)
    stock_drop = max((apex[1] - p["donor_y"]) for p in pairs if p["donor_y"] is not None)

    return dict(
        transform=dict(shift_world=[sx, sz], DY=dy,
                       source="uvf_fix6_report.json stage4_donor_overlay (a transform, not a verdict)"),
        donor_region="Cleyra grass|desert|dunes junction (13-15,11-12), stock disc 1, read-only",
        carried_fidelity=dict(
            n_carried_positions_matched=len(carried_delta),
            n_exact_within_0p01u=len(exact),
            pct_exact=round(100.0 * len(exact) / max(1, len(carried_delta)), 2),
            delta_stats=RP.stats(carried_delta)),
        fill_holes_below_donor=dict(
            rule=("FILL position, inside the 40u mound, outside the sacred basin disc, with a donor "
                  "vertex at its exact shifted XZ and >=4 welded neighbours that are carried positions "
                  "matching the donor to <0.01u."),
            n=len(holes), rows=holes),
        THE_ONE_knob=dict(
            live_apex=list(apex), donor_apex_xz=list(donor_apex),
            neighbour_ring=pairs,
            max_welded_drop_live_u=round(live_drop, 3),
            max_welded_drop_if_donor_heights_u=round(stock_drop, 3),
            over_steepening_u=round(live_drop - stock_drop, 3)))


# =================================================================================================
#  helpers for lane 1b-1e
# =================================================================================================
def adj_of(all_recs):
    adj = defaultdict(set)
    for r in all_recs:
        ks = r["keys"]
        for a in range(3):
            for c in range(3):
                if a != c and ks[a] != ks[c]:
                    adj[ks[a]].add(ks[c])
    return adj


def render_blobs(lum, wx, wz, thresh=20.0, min_px=50):
    """connected bright components of (luminance - local background) in the round-6 mound render.
    Background = max(31px median, 30px box blur) -- so a broad lit slope is background and only a
    LOCAL bright lens survives.  Pure PIL/numpy (no scipy in this env)."""
    from collections import deque
    from PIL import ImageFilter
    li = Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8))
    med = np.asarray(li.filter(ImageFilter.MedianFilter(size=31)), dtype=np.float32)
    box = np.asarray(li.filter(ImageFilter.BoxBlur(30)), dtype=np.float32)
    th = lum - np.maximum(med, box)
    m = th > thresh
    H, W = m.shape
    lab = np.zeros((H, W), np.int32)
    cur = 0
    ys, xs = np.where(m)
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0]:
            continue
        cur += 1
        q = deque([(y0, x0)])
        lab[y0, x0] = cur
        while q:
            y, x = q.popleft()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and m[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = cur
                        q.append((yy, xx))
    out = []
    for i in range(1, cur + 1):
        yy, xx = np.where(lab == i)
        if len(yy) < min_px:
            continue
        cx, cz = float(wx[yy, xx].mean()), float(wz[yy, xx].mean())
        bn, ba = bearing(cx, cz)
        out.append(dict(n_px=int(len(yy)), world=[round(cx, 2), round(cz, 2)],
                        r_crater=round(rc(cx, cz), 2), bearing=bn,
                        size_u=[round((xx.max() - xx.min()) / REN_SC, 2),
                                round((yy.max() - yy.min()) / REN_SC, 2)],
                        mean_excess_lum=round(float(th[yy, xx].mean()), 1)))
    out.sort(key=lambda b: -b["n_px"])
    return out[:24]


def ridge_census(kept_ground, kept_rock, fill, adj, moved_now):
    """Round 6's stage-2 reference re-derived on FIXED6's OWN bytes (same recipe: basin-EXCLUDED
    samples, leave-one-out, two passes), then EVERY carried-ground position scored on both of round
    6's axes plus the two step-shaped statistics a shoulder/ridge needs (max welded drop, mean
    neighbour deficit).  This is the table a round-7 census rule must be built on."""
    sample_keys = sorted(set(kept_ground) | set(fill))
    samples = np.array([[k[0], k[1], k[2]] for k in sample_keys], dtype=float)
    idx_of = {k: i for i, k in enumerate(sample_keys)}
    base = RP.Hash2D(samples, cell=8.0)
    basin_idx = frozenset(idx_of[k] for k in sample_keys if rc(k[0], k[2]) <= BASIN_R)

    class Excl:
        def __init__(self, b, drop):
            self.base, self.drop, self.cell, self.pts = b, drop, b.cell, b.pts

        def query(self, x, z, r):
            return [(i, d2) for i, d2 in self.base.query(x, z, r) if i not in self.drop]

    def census(extra):
        out = {}
        for k in sample_keys:
            y, _d = RP.ref_at(Excl(base, basin_idx | {idx_of[k]} | extra), samples, k[0], k[2])
            out[k] = None if y is None else k[1] - y
        return out

    res_a = census(frozenset())
    cand_a = {k for k, v in res_a.items() if v is not None and v >= RES_T}
    res = census(frozenset(idx_of[k] for k in cand_a))

    def stepstats(k):
        nb = [n for n in adj[k]]
        if not nb:
            return None
        drops = [(k[1] - n[1], math.hypot(k[0] - n[0], k[2] - n[2]), n) for n in nb]
        prom = min(d for d, _dist, _n in drops)
        maxdrop = max(d for d, _dist, _n in drops)
        slopes = [d / dist for d, dist, _n in drops if dist > 1e-6]
        return dict(deg=len(nb), prominence=round(prom, 3), max_welded_drop=round(maxdrop, 3),
                    mean_deficit=round(float(np.mean([d for d, _dd, _n in drops])), 3),
                    max_welded_slope_deg=round(math.degrees(math.atan(max(slopes))), 1)
                    if slopes else None,
                    neighbour_y=[round(n[1], 3) for _d, _dd, n in
                                 sorted(drops, key=lambda t: -t[2][1])])

    rows = []
    for k in sorted(kept_ground, key=lambda k: -(res.get(k) or -9)):
        v = res.get(k)
        if v is None or v < 0.6:
            continue
        s = stepstats(k)
        bn, _ba = bearing(k[0], k[2])
        rows.append(dict(
            pos=[k[0], k[1], k[2]], r_crater=round(rc(k[0], k[2]), 2), bearing=bn,
            residual_u=round(v, 3), topo=sorted(kept_ground[k]),
            moved_by_round6=bool(k in moved_now), **(s or {}),
            round6_verdict=("SPIKE" if (v >= RES_T and s and s["prominence"] >= PROM_T)
                            else ("flush-with-a-neighbour(not-a-spike)" if v >= RES_T
                                  else "below-residual-threshold"))))

    rim_ring = sorted([k for k in kept_ground if abs(k[1] - 6.208) < 1e-3 and rc(k[0], k[2]) <= 15.0],
                      key=lambda k: -(res.get(k) or -9))
    return dict(
        method=("uvf_relief_probe.ref_at VERBATIM on FIXED6's own Terrain bytes; samples = carried "
                "ground + fill, MINUS the sacred basin disc (THE BASIN REFERENCE TRAP), leave-one-out, "
                "two passes (pass B also drops every pass-A candidate).  Rock never votes."),
        n_samples=len(sample_keys), n_basin_excluded=len(basin_idx),
        n_pass_a_candidates=len(cand_a),
        residual_all=RP.stats([v for v in res.values() if v is not None]),
        rim_ring_n=len(rim_ring),
        rim_ring_residual=RP.stats([res[k] for k in rim_ring if res[k] is not None]),
        rim_ring_max_residual=round(max((res[k] for k in rim_ring if res[k] is not None),
                                        default=0.0), 3),
        rows_residual_ge_0p6=rows,
        n_rows=len(rows))


def pick_the_one(uncat_rows, ridge, blobs, sfaces):
    """THE ONE = the owner's sighting.  Scored, not asserted: a candidate must (a) be a RAISED,
    still-unshaved feature, (b) wear a texture that is NOT the sand mains, (c) sit in the W..NW
    sector (the owner stood WNW; the patch was just SOUTH of them, so its own bearing from the
    crater reads W/WSW/WNW), and (d) coincide with a bright local blob in the round-6 render."""
    still_raised = [r for r in ridge["rows_residual_ge_0p6"]
                    if r["residual_u"] >= RES_T and not r["moved_by_round6"]]
    cands = []
    for r in uncat_rows:
        cx, cz = r["centroid"]
        # the nearest still-raised carried position
        best, bd = None, 1e9
        for q in still_raised:
            d = math.hypot(q["pos"][0] - cx, q["pos"][2] - cz)
            if d < bd:
                best, bd = q, d
        nb, nbd = None, 1e9
        for b in blobs:
            d = math.hypot(b["world"][0] - cx, b["world"][1] - cz)
            if d < nbd:
                nb, nbd = b, d
        sector = r["bearing"] in ("WSW", "W", "WNW", "NW")
        score = (2.0 * (r["dip"] or 0) / 45.0
                 + 3.0 * (1.0 if best is not None and bd <= 2.5 else 0.0)
                 + 2.0 * (1.0 if sector else 0.0)
                 + 1.5 * (1.0 if nb is not None and nbd <= 2.0 else 0.0))
        cands.append(dict(tri=r["tri"], centroid=r["centroid"], r_crater=r["r_crater"],
                          bearing=r["bearing"], dip=r["dip"], span=r["span"],
                          uv_rect=r["uv_rect"], sigma_max=r["sigma_max"],
                          nearest_still_raised_position=(best["pos"] if best and bd <= 2.5 else None),
                          nearest_still_raised_residual=(best["residual_u"] if best and bd <= 2.5
                                                         else None),
                          nearest_render_blob=(nb if nb and nbd <= 2.0 else None),
                          in_W_to_NW_sector=sector, score=round(score, 2)))
    cands.sort(key=lambda c: -c["score"])
    return dict(
        ranked_candidates=cands[:6],
        verdict=cands[0] if cands else None,
        criteria=("(a) still raised after round 6, (b) NOT wearing sand mains, (c) in the W..NW "
                  "sector, (d) coincident with a bright local blob in the round-6 render."))


# =================================================================================================
#  LANE 2 -- the stock steep-face language
# =================================================================================================
def read_stock(blocks):
    recs = []
    misses = []
    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except (ValueError, FileNotFoundError, KeyError) as exc:
            misses.append([bx, by, str(exc)[:80]])
            continue
        recs.extend(tris_of_blockmesh(bm, bx, by))
    for r in recs:
        enrich(r)
    return recs, misses


DIP_BINS = [(0, 5), (5, 15), (15, 30), (30, 45), (45, 60), (60, 75), (75, 90.1)]


def dip_hist(recs):
    out = {}
    for lo, hi in DIP_BINS:
        n = sum(1 for r in recs if r["dip"] is not None and lo <= r["dip"] < hi)
        out[f"{lo}-{hi if hi <= 90 else 90}"] = n
    return out


def uv_rect_of(recs):
    if not recs:
        return None
    us = [u for r in recs for (u, _v) in r["uv"]]
    vs = [v for r in recs for (_u, v) in r["uv"]]
    return [round(min(us), 5), round(min(vs), 5), round(max(us), 5), round(max(vs), 5)]


def region_report(name, blocks, base_sigma_hint=None):
    recs, misses = read_stock(blocks)
    ground = [r for r in recs if r["fam"] in GROUND_FAMS]
    rock = [r for r in recs if r["fam"] == "rock"]
    base = flat_baseline(recs) or base_sigma_hint
    log(f"[L2:{name}] {len(recs)} tris ({len(ground)} ground, {len(rock)} rock); "
        f"flat baseline sigma_max {base:.3f}")

    def bundle(sel, tag):
        if not sel:
            return dict(n=0)
        sig = [r["sigma_max"] for r in sel if r["sigma_max"] is not None]
        st = [r["sigma_max"] / base for r in sel if r["sigma_max"] is not None]
        return dict(
            n=len(sel),
            fam_hist=dict(Counter(r["fam"] for r in sel)),
            topo_hist=dict(Counter(r["topo"] for r in sel)),
            uv_class_hist=dict(Counter(r["uv_class"] for r in sel)),
            uv_detail_hist=dict(Counter(f"{r['uv_class']}:{r['uv_detail']}" for r in sel)),
            uv_bounding_rect=uv_rect_of(sel),
            uv_rect_by_class={c: uv_rect_of([r for r in sel if r["uv_class"] == c])
                              for c in sorted({r["uv_class"] for r in sel})},
            span_u=dict(max=round(max(r["span"] for r in sel), 3),
                        p50=round(float(np.median([r["span"] for r in sel])), 3),
                        p90=round(float(np.percentile([r["span"] for r in sel], 90)), 3)),
            dip_deg=dict(max=round(max(r["dip"] for r in sel if r["dip"] is not None), 2),
                         p50=round(float(np.median([r["dip"] for r in sel
                                                    if r["dip"] is not None])), 2)),
            area3d_total=round(sum(r["area3d"] for r in sel), 2),
            sigma_max=dict(p50=round(float(np.median(sig)), 2), max=round(max(sig), 2)) if sig else None,
            uv_stretch_x_flat=dict(p50=round(float(np.median(st)), 3),
                                   p90=round(float(np.percentile(st, 90)), 3),
                                   max=round(max(st), 3)) if st else None,
            tag=tag)

    steep = {}
    for thr in (30, 45, 60):
        steep[f"ground_dip_ge_{thr}"] = bundle(
            [r for r in ground if r["dip"] is not None and r["dip"] >= thr], f"ground dip>={thr}")
        steep[f"rock_dip_ge_{thr}"] = bundle(
            [r for r in rock if r["dip"] is not None and r["dip"] >= thr], f"rock dip>={thr}")

    # stock steep FACES, same rule as lane 1
    sl = [r for r in recs if r["span"] >= SPAN_T]
    sl_ground = [r for r in sl if r["fam"] in GROUND_FAMS]
    faces = []
    for idxs in cluster_faces(sl):
        rs = [sl[i] for i in idxs]
        ymax = max(p[1] for r in rs for p in r["w"])
        ymin = min(p[1] for r in rs for p in r["w"])
        a3 = sum(r["area3d"] for r in rs)
        sig = [r["sigma_max"] for r in rs if r["sigma_max"] is not None]
        faces.append(dict(
            n_tris=len(rs), fam=sorted({r["fam"] for r in rs if r["fam"]}),
            topo=sorted({r["topo"] for r in rs}),
            centroid=[round(sum(r["centroid"][0] for r in rs) / len(rs), 2),
                      round(sum(r["centroid"][2] for r in rs) / len(rs), 2)],
            drop_u=round(ymax - ymin, 3),
            max_span_u=round(max(r["span"] for r in rs), 3),
            max_dip=round(max(r["dip"] for r in rs if r["dip"] is not None), 2),
            area3d=round(a3, 2),
            uv_class=dict(Counter(r["uv_class"] for r in rs)),
            uv_stretch_max=round(max(sig) / base, 3) if sig else None))
    faces.sort(key=lambda f: -f["drop_u"])

    ground_faces = [f for f in faces if set(f["fam"]) & GROUND_FAMS]
    # THE HEADLINE TEST: a >=2u tall, >=45deg ground face wearing plain family mains
    violations = [f for f in ground_faces
                  if f["drop_u"] >= 2.0 and f["max_dip"] >= 45.0
                  and f["uv_class"].get("mains_own", 0) + f["uv_class"].get("mains_foreign", 0)
                  == f["n_tris"]]
    any_steep_tall_ground = [f for f in ground_faces if f["drop_u"] >= 2.0 and f["max_dip"] >= 45.0]

    # per-FAMILY dip/span profile (the aggregate hides that "dunes ground" and "brush riser" and
    # "topo-58 rock wall" are three different vocabularies living in the same blocks)
    per_fam = {}
    for fam in sorted({r["fam"] for r in recs if r["fam"]}):
        sel = [r for r in recs if r["fam"] == fam and r["dip"] is not None]
        if not sel:
            continue
        per_fam[fam] = dict(
            n=len(sel),
            dip=dict(p50=round(float(np.median([r["dip"] for r in sel])), 2),
                     p90=round(float(np.percentile([r["dip"] for r in sel], 90)), 2),
                     max=round(max(r["dip"] for r in sel), 2)),
            span=dict(p50=round(float(np.median([r["span"] for r in sel])), 3),
                      p90=round(float(np.percentile([r["span"] for r in sel], 90)), 3),
                      max=round(max(r["span"] for r in sel), 3)),
            n_dip_ge_30=sum(1 for r in sel if r["dip"] >= 30),
            n_dip_ge_45=sum(1 for r in sel if r["dip"] >= 45),
            uv_class_hist=dict(Counter(r["uv_class"] for r in sel)))

    # the DUNES STEEP DECAL -- the rect our carried slivers wear.  Where does STOCK put it?
    DECAL = (0.13867, 0.83594, 0.19922, 0.86621)
    dec = [r for r in recs
           if all(DECAL[0] - 1e-3 <= u <= DECAL[2] + 1e-3 and DECAL[1] - 1e-3 <= v <= DECAL[3] + 1e-3
                  for (u, v) in r["uv"])]
    decal = dict(
        rect=list(DECAL), n_tris=len(dec),
        topo_hist=dict(Counter(r["topo"] for r in dec)),
        dip=dict(p50=round(float(np.median([r["dip"] for r in dec])), 2),
                 max=round(max(r["dip"] for r in dec), 2)) if dec else None,
        span=dict(p50=round(float(np.median([r["span"] for r in dec])), 3),
                  max=round(max(r["span"] for r in dec), 3)) if dec else None,
        sigma_max=dict(p50=round(float(np.median([r["sigma_max"] for r in dec
                                                  if r["sigma_max"]])), 2)) if dec else None,
        n_clusters=len(cluster_faces(dec)) if dec else 0,
        cluster_sizes=sorted((len(g) for g in cluster_faces(dec)), reverse=True) if dec else [],
        knobs=[dict(topo=[dec[i]["topo"] for i in g],
                    centroid=[round(dec[g[0]]["centroid"][0], 2), round(dec[g[0]]["centroid"][2], 2)],
                    n_tris=len(g),
                    drop_u=round(max(p[1] for i in g for p in dec[i]["w"])
                                 - min(p[1] for i in g for p in dec[i]["w"]), 3),
                    dips=[round(dec[i]["dip"], 1) for i in g],
                    sigma_max=[round(dec[i]["sigma_max"], 1) for i in g if dec[i]["sigma_max"]])
               for g in cluster_faces(dec)] if dec else [],
        note=("THE STOCK KNOB FORM: this decal is never a lone tri and never a field -- it comes as a "
              "2-tri KNOB.  Its atlas art is sand at low v and a mottled rock/lichen outcrop at high v, "
              "and the tris put the high-v end at the knob's TOP: a rock poking out of a dune."))

    return dict(
        blocks=[list(b) for b in blocks], misses=misses,
        n_tris=len(recs), n_ground=len(ground), n_rock=len(rock),
        per_family=per_fam, dunes_steep_decal=decal,
        flat_baseline_sigma=round(base, 4),
        dip_hist_ground=dip_hist(ground), dip_hist_rock=dip_hist(rock),
        dip_pct_ground=dict(p50=round(float(np.median([r["dip"] for r in ground
                                                       if r["dip"] is not None])), 2),
                            p90=round(float(np.percentile([r["dip"] for r in ground
                                                           if r["dip"] is not None], 90)), 2),
                            p99=round(float(np.percentile([r["dip"] for r in ground
                                                           if r["dip"] is not None], 99)), 2),
                            max=round(max(r["dip"] for r in ground if r["dip"] is not None), 2)),
        span_pct_ground=dict(p50=round(float(np.median([r["span"] for r in ground])), 3),
                             p90=round(float(np.percentile([r["span"] for r in ground], 90)), 3),
                             p99=round(float(np.percentile([r["span"] for r in ground], 99)), 3),
                             max=round(max(r["span"] for r in ground), 3)),
        n_ground_sliver_tris=len(sl_ground),
        pct_ground_tris_span_ge_1u=round(100.0 * len(sl_ground) / max(1, len(ground)), 3),
        steep=steep,
        n_faces_span_ge_1u=len(faces),
        n_ground_faces=len(ground_faces),
        top_ground_faces=ground_faces[:12],
        top_faces_any=faces[:8],
        tall_steep_ground_faces=any_steep_tall_ground,
        tall_steep_ground_faces_wearing_plain_mains=violations,
    )


def lane2(report, base_hint):
    r = {}
    r["dunes_mass"] = region_report("dunes", STOCK_DUNES, base_hint)
    r["cleyra_junction"] = region_report("junction", STOCK_JUNCTION, base_hint)
    report["lane2_stock_steep_language"] = r
    return r


# =================================================================================================
def main():
    report = dict(meta=dict(
        script="uvf_sliver_probe.py",
        round="RUNG F round 7 -- the sliver-step probe",
        read_only_vs_game=True, writes=[str(REPORT), str(RENDER_DIR)],
        subject=str(FIXED6),
        playtest5="mostly flattened but ONE sticks out and has a noticeably different texture than the sand",
        owner_position="WNW of the crater; the feature a small raised patch just south of them"))

    L1 = lane1(report)
    lane2(report, L1["base_sigma"])

    # ---- comparison + recommendation ------------------------------------------------------------
    f = report["lane1_sliver_census"]["faces"]
    st = report["lane2_stock_steep_language"]
    ours_max_drop = max((x["face_drop_u"] for x in f), default=0.0)
    ours_max_dip = max((x["max_dip_deg"] for x in f), default=0.0)
    ours_max_stretch = max((x["uv_stretch_x_flat"] or 0 for x in f), default=0.0)
    report["comparison"] = dict(
        ours=dict(n_faces=len(f), max_face_drop_u=ours_max_drop, max_dip_deg=ours_max_dip,
                  max_uv_stretch_x_flat=ours_max_stretch,
                  pct_near_tris_span_ge_1u=round(
                      100.0 * report["lane1_sliver_census"]["scan"]["n_sliver_tris"]
                      / max(1, report["lane1_sliver_census"]["scan"]["n_tris_within_scan"]), 3)),
        stock_dunes=dict(max_ground_dip=st["dunes_mass"]["dip_pct_ground"]["max"],
                         p99_ground_dip=st["dunes_mass"]["dip_pct_ground"]["p99"],
                         max_ground_span=st["dunes_mass"]["span_pct_ground"]["max"],
                         pct_ground_tris_span_ge_1u=st["dunes_mass"]["pct_ground_tris_span_ge_1u"],
                         n_tall_steep_ground_faces=len(st["dunes_mass"]["tall_steep_ground_faces"])),
        stock_junction=dict(max_ground_dip=st["cleyra_junction"]["dip_pct_ground"]["max"],
                            p99_ground_dip=st["cleyra_junction"]["dip_pct_ground"]["p99"],
                            max_ground_span=st["cleyra_junction"]["span_pct_ground"]["max"],
                            pct_ground_tris_span_ge_1u=st["cleyra_junction"]["pct_ground_tris_span_ge_1u"],
                            n_tall_steep_ground_faces=len(
                                st["cleyra_junction"]["tall_steep_ground_faces"])))

    # ---- THE LEVER ------------------------------------------------------------------------------
    L1 = report["lane1_sliver_census"]
    ridge_rows = L1["ridge_census"]["rows_residual_ge_0p6"]
    qual = [r for r in ridge_rows
            if r["residual_u"] >= RES_T and r["prominence"] >= 0.0
            and r["max_welded_drop"] >= 1.5 and r["r_crater"] <= 40.0]
    rejects = [r for r in ridge_rows if r["residual_u"] >= RES_T and r not in qual]
    report["recommendation"] = dict(
        headline=("GEOMETRY, not texture.  THE ONE's texture is a BYTE-VERBATIM stock carry (its atlas "
                  "rect, its 2-tri knob form, its 46.0/35.6-deg dips and its 0.84u drop are all "
                  "identical to the stock donor knob at Cleyra-junction (884.7,-780.0)); stock puts "
                  "plain mains on 0 of 57 ground tris at dip>=45 across both reference regions, so "
                  "re-clothing it would be the only genuinely off-language move on the table."),
        refuted_lever=dict(
            name="texture-dress THE ONE in dunes mains",
            why=("stock's steep-sand vocabulary IS this decal: 10/10 topo-41 tris at the junction with "
                 "dip 34.3-55.4 (p50 44.5) wear rect [0.13867,0.83594,0.19922,0.86621], 0 wear mains; "
                 "in the dunes mass 52/52 ground tris at dip>=45 wear the brush edge column "
                 "[0.72070,0.53516,0.78125,0.59668], 0 wear mains.  Dressing a 46-deg sand face in "
                 "plan-projected mains would also ADD a 1.44x smear where the carried decal currently "
                 "sits at 0.55x (denser than flat).")),
        primary=dict(
            name="ROUND-7 SPIKE-SHAVE, the round-6 census with a STEP arm",
            rule=("SPIKE := carried ground position, outside the sacred basin disc, inside r<=40u, all "
                  "vertex entries in Terrain, rock (58/31) exempt, residual >= 0.8u AND "
                  "[ mesh-prominence >= 0.4u  OR  (mesh-prominence >= 0.0u AND max welded drop >= 1.5u) ].  "
                  "The new arm is the STEP arm: a shoulder/ridge crest is not a strict local max, which "
                  "is exactly why round 6's predicate (3) skipped it."),
            selects=qual, n_selected=len(qual),
            rejected_at_residual_gate=rejects,
            margins=dict(
                rim_crest_max_residual=L1["ridge_census"]["rim_ring_max_residual"],
                residual_gate=RES_T,
                note=("the sacred rim crest tops out at %.3fu -- %.3fu of clearance under the 0.8 gate, "
                      "so THE BASIN REFERENCE TRAP stays shut."
                      % (L1["ridge_census"]["rim_ring_max_residual"],
                         RES_T - L1["ridge_census"]["rim_ring_max_residual"]))),
            target=("shave the selected apex to within 0.15u of the local rim reference (residual "
                    "+0.863u -> ~0), with round 6's own harmonic solve: unknowns = the apex + fill "
                    "within HOPS=2, data term dY = -residual (W_SPIKE swept, smallest value that lands "
                    "the apex within 0.15u and moves no fill more than 0.60u), smoothness on every "
                    "interior edge, Dirichlet dY=0 on every edge leaving the patch.  Expected: 1 carried "
                    "position + ~2-4 welded fill, Y-only, basin byte-frozen."),
            precedent="round 6 did exactly this to the 4 sibling knobs; playtest 5 approved all 4."),
        companion_optional=dict(
            name="FILL-RESTORE (the ROOT CAUSE, higher variance)",
            finding=("THE ONE is not over-tall -- its WEST SHOULDER is over-DEEP.  Two fill vertices "
                     "inside intact carried donor terrain sit BELOW their donor height: "
                     "(114.0,-1164.609) at -1.040u (6 of 7 welded neighbours are donor-exact carried) "
                     "and (112.0,-1165.219) at -0.912u (4 of 5).  That turns the donor's 1.219u / 30.2-deg "
                     "west shoulder into a 2.259u / 47.2-deg step -- the knob itself is byte-identical."),
            spec=("raise those fill positions to their donor height (harmonic, same solver, fill-only -- "
                  "no carried-move contract needed at all, this is round 5's own lever class)."),
            risk=("it ADDS relief back where round 5's approved relax removed it ('the crevices are "
                  "sealed up ... seal looks good').  Untested look; the shave has 4 approved precedents."),
            full_hole_census=L1["donor_identity"]["fill_holes_below_donor"]),
        secondary_finding=dict(
            name="THE SMEAR LEDGER -- a real but UNREPORTED defect, do not ship blind",
            finding=("near-crater tris run to %.3fx the flat UV baseline, against a stock ground ceiling "
                     "of 1.414x (dunes mass, dip>=45) / 0.762x (junction, dip>=45).  Every over-1.5x tri "
                     "is synthesized fill wearing plan-projected mains on a dipping face."
                     % max((x["uv_stretch_x_flat"] or 0) for x in L1["faces"])),
            ledger=L1["smear_ledger"],
            judgement=("these sit E/NE/inside the crater bowl -- the sectors playtest 5 called good.  "
                       "Log it; do not bundle it into the same in-game test as the shave (ONE CHANGE "
                       "PER TEST).")))

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    log(f"\n-> {REPORT}")
    log(f"-> {RENDER_DIR}")

    log("\n== DONOR IDENTITY ==")
    di = report["lane1_sliver_census"]["donor_identity"]
    log(f"  carried fidelity: {di['carried_fidelity']['n_exact_within_0p01u']}/"
        f"{di['carried_fidelity']['n_carried_positions_matched']} exact "
        f"({di['carried_fidelity']['pct_exact']}%)")
    log(f"  THE ONE knob: live max welded drop {di['THE_ONE_knob']['max_welded_drop_live_u']}u vs "
        f"donor {di['THE_ONE_knob']['max_welded_drop_if_donor_heights_u']}u "
        f"(over-steepened by {di['THE_ONE_knob']['over_steepening_u']}u)")
    for p in di["THE_ONE_knob"]["neighbour_ring"]:
        log(f"    {p['pos']} {p['kind']:7s} d={p['dist_u']:.2f} drop={p['drop_from_apex_u']:+.3f} "
            f"donor_y={p['donor_y']}")
    log(f"  fill holes below donor: n={di['fill_holes_below_donor']['n']}")
    for h in di["fill_holes_below_donor"]["rows"]:
        log(f"    {h['pos']} donor={h['donor_y']} delta={h['delta_u']:+.3f} "
            f"nb={h['donor_exact_neighbours']}/{h['degree']} r={h['r_crater']} {h['bearing']}")
    log("\n== SMEAR LEDGER ==")
    for b in report["lane1_sliver_census"]["smear_ledger"]:
        log(f"  {b['bucket']:>10}: n={b['n']:4d} A3d={b['area3d_u2']:8.2f} dip_p50={b['dip_p50']} "
            f"synth={b['synth_frac']} uv={b['uv_class']}")
    log("\n== THE ONE ==")
    log(json.dumps(report["lane1_sliver_census"]["THE_ONE"]["verdict"], indent=1))
    log("\n== ridge census (residual >= 0.6, carried ground) ==")
    for r in report["lane1_sliver_census"]["ridge_census"]["rows_residual_ge_0p6"]:
        log(f"  {r['pos']} r={r['r_crater']:5.1f} {r['bearing']:>3} res={r['residual_u']:+.3f} "
            f"prom={r['prominence']:+.3f} maxdrop={r['max_welded_drop']:.3f} "
            f"slope={r['max_welded_slope_deg']} deg={r['deg']} topo={r['topo']} "
            f"moved6={r['moved_by_round6']} -> {r['round6_verdict']}")
    log("\n== near-crater UNCATALOGUED-UV tris ==")
    for r in report["lane1_sliver_census"]["texture_census"]["uncatalogued_tris"]:
        log(f"  {r['tri']:>12} c={r['centroid']} r={r['r_crater']:5.1f} {r['bearing']:>3} "
            f"dip={r['dip']:5.1f} span={r['span']:.2f} rect={r['uv_rect']} sig={r['sigma_max']}")
    log("\n== render bright blobs ==")
    for b in report["lane1_sliver_census"]["render_blobs"][:12]:
        log(f"  {b['world']} r={b['r_crater']:5.1f} {b['bearing']:>3} {b['size_u']}u "
            f"{b['n_px']}px excess={b['mean_excess_lum']}")
    log("\n== LANE 1b steep faces (dip>=%.0f) ==" % STEEP_T)
    for x in report["lane1_sliver_census"]["steep_faces"]["faces"][:14]:
        log(f"  s#{x['sface_id']:2d} {x['bearing']:>3} r={x['r_crater']:5.1f} "
            f"c={x['centroid_world']} drop={x['drop_u']:5.2f} dip={x['max_dip_deg']:5.1f} "
            f"A={x['area3d_u2']:7.2f} n={x['n_tris']:2d} basin={x['inside_basin_disc']} "
            f"uv={x['uv_class']} stretch={x['uv_stretch_x_flat_max']}")

    # console digest
    log("\n== LANE 1 faces (by 3D area) ==")
    for x in f[:20]:
        log(f"  #{x['face_id']:2d} {x['bearing']:>3} r={x['r_crater']:5.1f} "
            f"c=({x['centroid_world'][0]:7.2f},{x['centroid_world'][2]:9.2f}) "
            f"span={x['max_span_u']:5.2f} drop={x['face_drop_u']:5.2f} dip={x['max_dip_deg']:5.1f} "
            f"A3d={x['area3d_u2']:7.2f} n={x['n_tris']:2d} "
            f"top={dict(x['top_vertex_ownership'])} fam={x['family']} "
            f"uv={x['uv_class']} stretch={x['uv_stretch_x_flat']} "
            f"lum+{x.get('render_lum_contrast')}")
    log("\n== LANE 2 ==")
    for k, v in st.items():
        log(f"  {k}: ground dip p50/p90/p99/max = "
            f"{v['dip_pct_ground']['p50']}/{v['dip_pct_ground']['p90']}/"
            f"{v['dip_pct_ground']['p99']}/{v['dip_pct_ground']['max']}  "
            f"span max {v['span_pct_ground']['max']}  "
            f"span>=1u {v['pct_ground_tris_span_ge_1u']}%  "
            f"tall+steep ground faces {len(v['tall_steep_ground_faces'])} "
            f"(plain-mains {len(v['tall_steep_ground_faces_wearing_plain_mains'])})")
        for thr in (30, 45, 60):
            b = v["steep"][f"ground_dip_ge_{thr}"]
            log(f"    ground dip>={thr}: n={b.get('n',0)} uv={b.get('uv_class_hist')} "
                f"stretch={b.get('uv_stretch_x_flat')}")
            b2 = v["steep"][f"rock_dip_ge_{thr}"]
            log(f"    rock   dip>={thr}: n={b2.get('n',0)} uv={b2.get('uv_class_hist')} "
                f"stretch={b2.get('uv_stretch_x_flat')}")


if __name__ == "__main__":
    main()
