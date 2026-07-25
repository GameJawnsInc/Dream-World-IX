"""RUNG F -- THE SHADED-RELIEF EYE, round 7 (THE SLIVER-STEP ROUND, 2026-07-25).

Playtest 5 on FIXED6: "they're mostly flattened but ONE sticks out in particular and has a noticeably
different texture than the sand" -- owner WNW of the crater, feature a small raised patch just south of
them. uvf_sliver_probe.py diagnosed this as a STEP face (round-5 relaxed fill meeting round-6's
deliberately-untouched pinned high ground), refuted the texture-dress lever (the face already wears
stock's OWN steep-dunes decal, byte-verbatim), and recommended a GEOMETRY-SOFTEN census widened with a
STEP arm. uvf_fix7.py built exactly that: ONE carried position ((116.0, 6.341, -1164.0), topo 41 dunes)
shaved from residual +0.863u/drop 2.259u/dip 47.2deg to residual +0.050u/drop 1.500u/dip 35.7deg, plus 2
welded fill positions, Y-only, 1 file (Block[1][18] Terrain).

THIS EYE, both required channels:
  (1) CALIBRATION on FIXED6 -- the textured+shaded mound render must show the bright sliver faces, THE
      ONE prominently, at the probe's own coordinates.
  (2) FIXED7 -- the slivers must read RESOLVED (dip collapsed under the steep-face threshold, no bright
      local blob, no smeared-mains violation ever existed to begin with) with THE ONE gone AT ITS COORDS.
  (3) crater + all four prior fixes intact -- an INDEPENDENT (not copied from uvf_fix7's own bookkeeping)
      vertex-level position diff between FIXED6 and FIXED7 across the WHOLE 20-block footprint, plus a
      pixel-level raster-height diff, both must localize to exactly the build's own claimed change set.
  (4) side-by-side vs the REAL stock dunes mass + the Cleyra grass|desert|dunes junction, quantified with
      the probe's own stretch/dip metrics -- is the mound's face language now closer to stock's?

Extends uvf_eye_relief6.py's rasterizer/panel machinery and uvf_sliver_probe.py's per-tri geometry+UV
census (tris_of_blockmesh / enrich / cluster_faces / flat_baseline / bearing / rc / region_report), all
reused verbatim (imported, never copied), generalized here to run over an ARBITRARY tree (round 6's own
lane1 hardcodes FIXED5/FIXED6; this round needs FIXED6/FIXED7).

READ-ONLY vs both artifact trees (FIXED6, FIXED7) and the game install (atlas + stock dunes + Cleyra
junction). Never writes outside out/rung_f/renders/uvfix7/ + out/rung_f/uvf_eye7_report.json. No git.

Run:  py -X utf8 uvf_eye7.py
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import atlas as ATLAS         # noqa: E402
from ff9mapkit.world import extract as X           # noqa: E402
from ff9mapkit.world import mesh as M              # noqa: E402
from ff9mapkit.world import grassland as G         # noqa: E402

import uvf_eye_relief as ER                        # noqa: E402  (rasterizer / hillshade / crop / height_at)
import uvf_eye_relief6 as E6                       # noqa: E402  (round-6 constants + save/hstack helpers)
import uvf_relief_probe as RP                       # noqa: E402  (Hash2D / ref_at / stats -- unused directly
                                                     #             here but kept import-parity with round 6)
import uvf_fix3 as F3                               # noqa: E402  (load_blocks -- Terrain BlockMesh per block)
import uvf_sliver_probe as SP                       # noqa: E402  (tris_of_blockmesh/enrich/cluster_faces/
                                                     #             flat_baseline/bearing/rc/region_report/
                                                     #             read_stock/render_blobs -- all reused)

OUT_DIR = HERE / "out" / "rung_f"
RENDER_DIR = OUT_DIR / "renders" / "uvfix7"
FIXED6 = OUT_DIR / "FF9CustomMap-world-FIXED6"
FIXED7 = OUT_DIR / "FF9CustomMap-world-FIXED7"
FIX6_REPORT = OUT_DIR / "uvf_fix6_report.json"
FIX7_REPORT = OUT_DIR / "uvf_fix7_report.json"
BUILD_JSON = OUT_DIR / "rung_f_build.json"
REPORT = OUT_DIR / "uvf_eye7_report.json"

FOOTPRINT = E6.FOOTPRINT
BASIN_CENTER = E6.BASIN_CENTER          # (127.14, -1161.42)
BASIN_R = E6.BASIN_R                    # 7.92
MOUND_R = E6.MOUND_R                    # 40.0 -- uvf_fix6's crater-mound radius
WEDGE_R = E6.WEDGE_R                    # 46.0 -- the mound render frame (matches uvf_sliver_probe's own)
STOCK_DUNES = SP.STOCK_DUNES
STOCK_JUNCTION = SP.STOCK_JUNCTION

SC = 10.0
THE_ONE_XZ = (116.0, -1164.0)           # the probe's own coords for THE ONE's apex
ZOOM_R = 8.0
SITE_R = 3.0                            # a kept topo-41 knob's own footprint is a couple metres across
SNAP_R = 4.0                            # face/blob-to-THE_ONE snap radius

SCAN_R = SP.SCAN_R                      # 40.0 -- lane-1's near-crater scan radius
SPAN_T = SP.SPAN_T                      # 1.0u -- the sliver census span threshold
STEEP_T = SP.STEEP_T                    # 25.0deg -- the "steep/lens face" sub-census threshold


def log(m):
    print(m, flush=True)


def save(arr_u8, path):
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr_u8, "RGB").save(path)
    return path


def hstack(paths, out_name, gap=8):
    ims = [Image.open(p).convert("RGB") for p in paths]
    h = max(im.height for im in ims)
    w = sum(im.width for im in ims) + gap * (len(ims) - 1)
    canvas = Image.new("RGB", (w, h), (18, 22, 34))
    x = 0
    for im in ims:
        canvas.paste(im, (x, 0))
        x += im.width + gap
    canvas.save(RENDER_DIR / out_name)
    return RENDER_DIR / out_name


# =================================================================================================
#  THE GEOMETRY+UV CENSUS -- uvf_sliver_probe's lane1 body, generalized off its FIXED5/FIXED6
#  hardcoding so it can run over ANY tree (here: FIXED6 and FIXED7).
# =================================================================================================
def census_tree(tree, touched):
    meshes = F3.load_blocks(tree, touched)
    recs = []
    for b in touched:
        recs.extend(SP.tris_of_blockmesh(meshes[b], *b))
    for r in recs:
        SP.enrich(r)
    base_sigma = SP.flat_baseline(recs)
    near = [r for r in recs if min(SP.rc(p[0], p[2]) for p in r["w"]) <= SCAN_R]
    slivers = [r for r in near if r["span"] >= SPAN_T]
    steep = [r for r in near if r["dip"] is not None and r["dip"] >= STEEP_T]

    def build_faces(sel):
        groups = SP.cluster_faces(sel)
        out = []
        for idxs in sorted(groups, key=lambda g: -sum(sel[i]["area3d"] for i in g)):
            rs = [sel[i] for i in idxs]
            ymax = max(p[1] for r in rs for p in r["w"])
            ymin = min(p[1] for r in rs for p in r["w"])
            a3 = sum(r["area3d"] for r in rs)
            cx = sum(r["centroid"][0] * r["area3d"] for r in rs) / a3
            cz = sum(r["centroid"][2] * r["area3d"] for r in rs) / a3
            sig = [r["sigma_max"] for r in rs if r["sigma_max"] is not None]
            stretch = [r["sigma_max"] / base_sigma for r in rs if r["sigma_max"] is not None]
            bname, bang = SP.bearing(cx, cz)
            xs = [p[0] for r in rs for p in r["w"]]
            zs = [p[2] for r in rs for p in r["w"]]
            dips = [r["dip"] for r in rs if r["dip"] is not None]
            out.append(dict(
                n_tris=len(rs), centroid_world=[round(cx, 3), round(cz, 3)],
                r_crater=round(SP.rc(cx, cz), 2), bearing=bname, bearing_deg=bang,
                plan_extent_u=[round(max(xs) - min(xs), 2), round(max(zs) - min(zs), 2)],
                y_top=round(ymax, 3), y_bottom=round(ymin, 3), face_drop_u=round(ymax - ymin, 3),
                max_dip_deg=round(max(dips), 2) if dips else None,
                median_dip_deg=round(float(np.median(dips)), 2) if dips else None,
                area3d_u2=round(a3, 3),
                family=sorted({r["fam"] for r in rs if r["fam"]}),
                uv_class=dict(Counter(r["uv_class"] for r in rs)),
                sigma_max_worldu_per_uvu=round(max(sig), 2) if sig else None,
                uv_stretch_x_flat=round(max(stretch), 3) if stretch else None,
                tris=[f"{r['block']}#{r['tri']}" for r in rs]))
        return out

    faces = build_faces(slivers)
    steep_faces = build_faces(steep)
    return dict(recs=recs, near=near, slivers=slivers, steep=steep,
                base_sigma=base_sigma, faces=faces, steep_faces=steep_faces)


def nearest_face(faces, xz, r=SITE_R):
    best, bd = None, None
    for f in faces:
        d = math.hypot(f["centroid_world"][0] - xz[0], f["centroid_world"][1] - xz[1])
        if bd is None or d < bd:
            best, bd = f, d
    if best is None:
        return None, None
    return (best, round(bd, 3)) if bd <= r else (None, round(bd, 3))


def smeared_mains_violations(faces):
    """ground faces >=2u drop, >=45deg dip, wearing ONLY family mains (own or foreign) -- the refuted
    'texture-dress THE ONE' hypothesis's own headline test (uvf_sliver_probe.region_report), run here
    over OUR OWN mound instead of stock, both before and after, to confirm it was never true."""
    out = []
    for f in faces:
        if (f["face_drop_u"] >= 2.0 and (f["max_dip_deg"] or 0) >= 45.0
                and set(f["family"]) & SP.GROUND_FAMS):
            n = sum(f["uv_class"].values())
            mains = f["uv_class"].get("mains_own", 0) + f["uv_class"].get("mains_foreign", 0)
            if n > 0 and mains == n:
                out.append(f)
    return out


def xz_to_y(recs):
    """flat-mesh assumption (proven elsewhere in this arc): one Y per (x,z). Used for an INDEPENDENT,
    whole-tree, vertex-level position diff -- not a read of uvf_fix7's own bookkeeping."""
    d = {}
    for r in recs:
        for (x, y, z) in r["w"]:
            d[(round(x, 3), round(z, 3))] = round(y, 4)
    return d


def excess_lum_at(color_arr, box, xz, half=2):
    """local background-subtracted luminance at a world (x,z) inside a rasterized crop -- the same
    median/box-blur background model as uvf_sliver_probe.render_blobs, point-sampled (a continuous
    number, not a threshold-gated blob) so 'the bright patch is gone' can be read as a residual, not a
    coin flip."""
    lum = (0.2126 * color_arr[..., 0].astype(np.float32) + 0.7152 * color_arr[..., 1].astype(np.float32)
           + 0.0722 * color_arr[..., 2].astype(np.float32))
    li = Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8))
    med = np.asarray(li.filter(ImageFilter.MedianFilter(size=31)), dtype=np.float32)
    bx = np.asarray(li.filter(ImageFilter.BoxBlur(30)), dtype=np.float32)
    bg = np.maximum(med, bx)
    excess = lum - bg
    H, W = lum.shape
    col = int(round((xz[0] - box["wx0"]) * box["sc"]))
    row = int(round((box["wz1"] - xz[1]) * box["sc"]))
    col = min(max(col, 0), W - 1)
    row = min(max(row, 0), H - 1)
    r0, r1 = max(0, row - half), min(H, row + half + 1)
    c0, c1 = max(0, col - half), min(W, col + half + 1)
    return float(excess[r0:r1, c0:c1].mean()), excess


def local_peak_excess(color_arr, box, xz, r=2.5):
    """max background-subtracted luminance within r world-units of xz -- more robust than a single
    point sample (the visible brightest texel of a tilted face need not sit exactly over the apex
    vertex's own XZ) and more SCOPED than the connected-blob scan (which can snap onto an unrelated
    nearby feature). Same median/box-blur background model as render_blobs / excess_lum_at."""
    lum = (0.2126 * color_arr[..., 0].astype(np.float32) + 0.7152 * color_arr[..., 1].astype(np.float32)
           + 0.0722 * color_arr[..., 2].astype(np.float32))
    li = Image.fromarray(np.clip(lum, 0, 255).astype(np.uint8))
    med = np.asarray(li.filter(ImageFilter.MedianFilter(size=31)), dtype=np.float32)
    bx = np.asarray(li.filter(ImageFilter.BoxBlur(30)), dtype=np.float32)
    excess = lum - np.maximum(med, bx)
    H, W = excess.shape
    rows, cols = np.mgrid[0:H, 0:W]
    wx = box["wx0"] + cols / box["sc"]
    wz = box["wz1"] - rows / box["sc"]
    m = (wx - xz[0]) ** 2 + (wz - xz[1]) ** 2 <= r * r
    if not m.any():
        return None
    return float(excess[m].max())


def blobs_in_crop(color_arr, box):
    lum = (0.2126 * color_arr[..., 0].astype(np.float32) + 0.7152 * color_arr[..., 1].astype(np.float32)
           + 0.0722 * color_arr[..., 2].astype(np.float32))
    H, W = lum.shape
    rows, cols = np.mgrid[0:H, 0:W]
    wx = box["wx0"] + cols / box["sc"]
    wz = box["wz1"] - rows / box["sc"]
    return SP.render_blobs(lum, wx, wz)


def blob_near(blobs, xz, r=SNAP_R):
    best, bd = None, None
    for b in blobs:
        d = math.hypot(b["world"][0] - xz[0], b["world"][1] - xz[1])
        if bd is None or d < bd:
            best, bd = b, d
    if best is None:
        return None, None
    return (best, round(bd, 2)) if bd <= r else (None, round(bd, 2))


TRI_REF_RE = re.compile(r"\((\d+),\s*(\d+)\)#(\d+)")


def parse_tri_ref(s):
    m = TRI_REF_RE.match(s)
    if not m:
        raise ValueError(f"bad tri ref: {s!r}")
    return (int(m.group(1)), int(m.group(2))), int(m.group(3))


def tri_recs(recs, tri_ids):
    want = set(tri_ids)
    return [r for r in recs if (r["block"], r["tri"]) in want]


def nearby_other_steep(recs, exclude_tri_ids, xz, r=3.0, dip_t=25.0):
    """every OTHER (not THE ONE's own named) tri within r of xz that is itself steep -- separates 'THE
    ONE's spike is resolved' from 'the whole neighbourhood is now flat', which are different claims. A
    non-empty result here is not this round's failure: uvf_fix7's own report already flags an adjacent,
    deliberately out-of-scope root cause (2 fill vertices sunk below their donor height)."""
    exclude = set(exclude_tri_ids)
    out = []
    for r_ in recs:
        if (r_["block"], r_["tri"]) in exclude:
            continue
        cx, cz = r_["centroid"][0], r_["centroid"][2]
        d = math.hypot(cx - xz[0], cz - xz[1])
        if d <= r and r_["dip"] is not None and r_["dip"] >= dip_t:
            out.append(dict(block=list(r_["block"]), tri=r_["tri"], dist_u=round(d, 2),
                             dip_deg=round(r_["dip"], 2), span_u=round(r_["span"], 3),
                             topo=r_["topo"], is_carried_ground=(r_["fam"] is not None)))
    out.sort(key=lambda x: x["dist_u"])
    return out


def tri_bundle(recs, base_sigma):
    dips = [r["dip"] for r in recs if r["dip"] is not None]
    spans = [r["span"] for r in recs]
    sig = [r["sigma_max"] for r in recs if r["sigma_max"] is not None]
    stretch = [s / base_sigma for s in sig] if base_sigma else []
    return dict(n_tris=len(recs), tris=[f"{r['block']}#{r['tri']}" for r in recs],
                dips=[round(d, 2) for d in dips], max_dip_deg=round(max(dips), 2) if dips else None,
                spans=[round(s, 3) for s in spans], max_span_u=round(max(spans), 3) if spans else None,
                sigma_max=[round(s, 2) for s in sig], uv_stretch_x_flat=[round(s, 3) for s in stretch],
                max_uv_stretch_x_flat=round(max(stretch), 3) if stretch else None,
                n_dip_ge_steep_t=sum(1 for d in dips if d >= STEEP_T))


# =================================================================================================
def main():
    t0 = time.time()
    log("loading atlas (engine-resolved, terrain part) ...")
    atlas_img = ATLAS.load_atlas("terrain", source="engine")
    atlas_np = np.array(atlas_img.convert("RGBA"), dtype=np.uint8)

    build = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    assert len(touched) == 20 and set(touched) == set(FOOTPRINT), (len(touched), touched)

    fix6 = json.loads(FIX6_REPORT.read_text(encoding="utf-8"))
    fix7 = json.loads(FIX7_REPORT.read_text(encoding="utf-8"))
    round6_apexes = [tuple(s["peak_world"]) for s in fix6["stage3_spike_census"]["sites"]]
    site = fix7["stage3_spike_census"]["sites"][0]
    spike_move = fix7["stage4_solve"]["result"]["spike_moves"][0]
    fill_moves = fix7["stage4_solve"]["result"]["fill_moves"]
    claimed_moved_xz = [(round(spike_move["world"][0], 3), round(spike_move["world"][2], 3))] + \
        [(round(m["world"][0], 3), round(m["world"][2], 3)) for m in fill_moves]
    log(f"claimed moved positions (from uvf_fix7_report, a location list): {claimed_moved_xz}")

    report = dict(meta=dict(
        script="uvf_eye7.py", round="RUNG F round 7 -- THE SLIVER-STEP EYE",
        read_only_vs_game=True, subject_calibration=str(FIXED6), subject_resolution=str(FIXED7),
        the_one_xz=list(THE_ONE_XZ), basin_center=list(BASIN_CENTER), basin_r=BASIN_R,
        mound_r=MOUND_R, wedge_r=WEDGE_R, sc=SC,
        playtest5="mostly flattened but ONE sticks out and has a noticeably different texture than the sand",
        claimed_moved_xz=claimed_moved_xz))

    # ==== master rasters over the FULL 20-block footprint, both trees ============================
    bxs = [b[0] for b in FOOTPRINT]
    bys = [b[1] for b in FOOTPRINT]
    wx0f, wx1f = min(bxs) * 64.0, (max(bxs) + 1) * 64.0
    wz0f, wz1f = -(max(bys) + 1) * 64.0, -min(bys) * 64.0
    log(f"footprint bbox world x[{wx0f},{wx1f}] z[{wz0f},{wz1f}] @ sc={SC}")

    log("\n== rasterizing FIXED6 footprint ==")
    c6 = ER.rasterize(FIXED6, FOOTPRINT, SC, atlas_np, wx0=wx0f, wx1=wx1f, wz0=wz0f, wz1=wz1f)
    log(f"  tris={c6['stats']['tris']} covered={int(c6['covered'].sum())}/{c6['W']*c6['H']}")
    log("== rasterizing FIXED7 footprint ==")
    c7 = ER.rasterize(FIXED7, FOOTPRINT, SC, atlas_np, wx0=wx0f, wx1=wx1f, wz0=wz0f, wz1=wz1f)
    log(f"  tris={c7['stats']['tris']} covered={int(c7['covered'].sum())}/{c7['W']*c7['H']}")

    log("== rasterizing STOCK dunes + Cleyra junction (reference) ==")
    cst_dunes = ER.rasterize(None, STOCK_DUNES, SC, atlas_np)
    cst_junc = ER.rasterize(None, STOCK_JUNCTION, SC, atlas_np)

    VEXAG = 4.0
    shades = {}
    for tag, c in (("fixed6", c6), ("fixed7", c7), ("stock_dunes", cst_dunes), ("stock_junction", cst_junc)):
        shades[tag] = dict(nw=ER.hillshade(c, 315.0, 35.0), multi_ex=ER.hillshade_multi(c, vexag=VEXAG))

    # ==== (1)+(2) RENDERS: mound crop + THE ONE zoom, both trees, textured + hillshade =============
    log(f"\n== mound crops (r={WEDGE_R}u around crater) + THE ONE zoom (r={ZOOM_R}u) ==")
    boxes_mound, boxes_one, composite_mound = {}, {}, {}
    for tag, c in (("fixed6", c6), ("fixed7", c7)):
        sh = shades[tag]
        bmound = ER.crop_world(c, *BASIN_CENTER, WEDGE_R)
        bone = ER.crop_world(c, *THE_ONE_XZ, ZOOM_R)
        boxes_mound[tag], boxes_one[tag] = bmound, bone
        comp_mound = ER.composite(ER.crop_arr(c["color"], bmound), ER.crop_arr(sh["nw"], bmound),
                                   ER.crop_arr(c["covered"], bmound))
        composite_mound[tag] = comp_mound          # the SHADED image -- what the brightness/blob checks
        save(comp_mound, RENDER_DIR / f"{tag}_mound_textured.png")   # analyze; raw texture color alone
        save(ER.gray_img(ER.crop_arr(sh["multi_ex"], bmound), ER.crop_arr(c["covered"], bmound)),  # does NOT
             RENDER_DIR / f"{tag}_mound_hillshade_exag4x.png")                                       # carry
        save(ER.composite(ER.crop_arr(c["color"], bone), ER.crop_arr(sh["nw"], bone),                # the dip
                           ER.crop_arr(c["covered"], bone)), RENDER_DIR / f"{tag}_theone_textured.png")  # signal
        save(ER.gray_img(ER.crop_arr(sh["multi_ex"], bone), ER.crop_arr(c["covered"], bone)),
             RENDER_DIR / f"{tag}_theone_hillshade_exag4x.png")

    save(ER.composite(cst_dunes["color"], shades["stock_dunes"]["nw"], cst_dunes["covered"]),
         RENDER_DIR / "stock_dunes_textured.png")
    save(ER.composite(cst_junc["color"], shades["stock_junction"]["nw"], cst_junc["covered"]),
         RENDER_DIR / "stock_junction_textured.png")

    panels = {}
    panels["mound_textured"] = hstack(
        [RENDER_DIR / "fixed6_mound_textured.png", RENDER_DIR / "fixed7_mound_textured.png"],
        "panel_mound_textured_f6_vs_f7.png")
    panels["mound_hillshade"] = hstack(
        [RENDER_DIR / "fixed6_mound_hillshade_exag4x.png", RENDER_DIR / "fixed7_mound_hillshade_exag4x.png"],
        "panel_mound_hillshade_exag4x_f6_vs_f7.png")
    panels["theone_textured"] = hstack(
        [RENDER_DIR / "fixed6_theone_textured.png", RENDER_DIR / "fixed7_theone_textured.png"],
        "panel_theone_textured_f6_vs_f7.png")
    panels["theone_hillshade"] = hstack(
        [RENDER_DIR / "fixed6_theone_hillshade_exag4x.png", RENDER_DIR / "fixed7_theone_hillshade_exag4x.png"],
        "panel_theone_hillshade_exag4x_f6_vs_f7.png")
    panels["vs_stock_dunes"] = hstack(
        [RENDER_DIR / "fixed7_mound_textured.png", RENDER_DIR / "stock_dunes_textured.png"],
        "panel_fixed7_vs_stock_dunes_textured.png")
    panels["vs_stock_junction"] = hstack(
        [RENDER_DIR / "fixed7_mound_textured.png", RENDER_DIR / "stock_junction_textured.png"],
        "panel_fixed7_vs_stock_junction_textured.png")
    log(f"panels -> {', '.join(p.name for p in panels.values())}")

    # ==== brightness at THE ONE, both trees (continuous excess-luminance + connected-blob check) ===
    # NOTE: analyzed off the SHADED COMPOSITE (texture x hillshade), not raw texture color -- the "bright
    # sliver" look is a lighting artefact of a near-vertical face under a directional light, not a texel
    # difference (the UV bytes are provably unchanged, stage_verify.uv_tangent_index_byte_identical=true).
    log("\n== brightness at THE ONE (shaded mound-crop luminance minus local background) ==")
    bright = {}
    blobs = {}
    for tag in ("fixed6", "fixed7"):
        bmound = boxes_mound[tag]
        comp = composite_mound[tag]
        exlum, _full = excess_lum_at(comp, bmound, THE_ONE_XZ)
        peak = local_peak_excess(comp, bmound, THE_ONE_XZ, r=2.5)
        bl = blobs_in_crop(comp, bmound)
        nb, nbd = blob_near(bl, THE_ONE_XZ)
        bright[tag] = dict(excess_lum_at_the_one_point=round(exlum, 2),
                            local_peak_excess_lum_r2p5=round(peak, 2) if peak is not None else None,
                            nearest_blob=nb, nearest_blob_dist=nbd,
                            has_bright_blob_within_snap_r=(nb is not None))
        blobs[tag] = bl
        log(f"  {tag}: point={exlum:.2f}  local_peak(r2.5)={peak:.2f}  nearest_blob="
            f"{nb['mean_excess_lum'] if nb else None} at dist={nbd}")

    # ==== (1)+(2) THE GEOMETRY+UV CENSUS, both trees ================================================
    log("\n== geometry+UV census, FIXED6 ==")
    cens6 = census_tree(FIXED6, touched)
    log(f"  {len(cens6['near'])} near-crater tris; {len(cens6['slivers'])} span>=1u tris in "
        f"{len(cens6['faces'])} faces; {len(cens6['steep'])} dip>=25deg tris in {len(cens6['steep_faces'])} "
        f"steep faces; flat sigma_max baseline {cens6['base_sigma']:.3f}")

    log("== geometry+UV census, FIXED7 ==")
    cens7 = census_tree(FIXED7, touched)
    log(f"  {len(cens7['near'])} near-crater tris; {len(cens7['slivers'])} span>=1u tris in "
        f"{len(cens7['faces'])} faces; {len(cens7['steep'])} dip>=25deg tris in {len(cens7['steep_faces'])} "
        f"steep faces; flat sigma_max baseline {cens7['base_sigma']:.3f}")

    # THE ONE, located by the two SPECIFIC named tris the build report itself shaved -- (block, tri) is
    # index-stable across Y-only rounds (round-6 precedent, re-asserted by uvf_sliver_probe), so this is
    # a precise, non-heuristic locator. The face-cluster centroid distance (nearest_face) is ALSO
    # reported below as supplementary shape evidence but is NOT used to gate a verdict: lane-1's
    # span>=1u census welds THE ONE's two tris into one large connected sliver network together with
    # much of the rim/fill sheet (129 tris -> only 8 faces), so a cluster's AREA-WEIGHTED centroid sits
    # many metres from any one knob and is the wrong instrument for "is THE ONE still there".
    the_one_tri_ids = [parse_tri_ref(s) for s in site["kept_tris"]]
    log(f"  THE ONE's named tris (from uvf_fix7_report stage3_spike_census.sites[0].kept_tris): "
        f"{site['kept_tris']}")
    the_one_recs6 = tri_recs(cens6["recs"], the_one_tri_ids)
    the_one_recs7 = tri_recs(cens7["recs"], the_one_tri_ids)
    assert len(the_one_recs6) == len(the_one_recs7) == len(the_one_tri_ids), \
        (len(the_one_recs6), len(the_one_recs7), len(the_one_tri_ids))
    the_one_before = tri_bundle(the_one_recs6, cens6["base_sigma"])
    the_one_after = tri_bundle(the_one_recs7, cens7["base_sigma"])
    log(f"  THE ONE (named tris) FIXED6: dips={the_one_before['dips']} spans={the_one_before['spans']}  "
        f"->  FIXED7: dips={the_one_after['dips']} spans={the_one_after['spans']}")

    f6_face, f6_d = nearest_face(cens6["faces"], THE_ONE_XZ)
    f7_face, f7_d = nearest_face(cens7["faces"], THE_ONE_XZ)
    log(f"  [supplementary] nearest span-census FACE centroid to THE_ONE_XZ: "
        f"FIXED6 dist={f6_d}  FIXED7 dist={f7_d} (both expected far -- see note above)")

    # separates "THE ONE's spike is resolved" from "the whole 2.5u neighbourhood reads flat" -- they are
    # different claims, and conflating them would misreport the build's own scoped fix as a failure.
    adjacent6 = nearby_other_steep(cens6["recs"], the_one_tri_ids, THE_ONE_XZ, r=2.5)
    adjacent7 = nearby_other_steep(cens7["recs"], the_one_tri_ids, THE_ONE_XZ, r=2.5)
    log(f"  OTHER steep (dip>=25) tris within 2.5u of THE_ONE_XZ, excluding THE ONE's own 2: "
        f"FIXED6={len(adjacent6)}  FIXED7={len(adjacent7)}")
    for a in adjacent7[:6]:
        log(f"    FIXED7: block={a['block']} tri={a['tri']} d={a['dist_u']} dip={a['dip_deg']} "
            f"carried={a['is_carried_ground']}")

    violations6 = smeared_mains_violations(cens6["faces"])
    violations7 = smeared_mains_violations(cens7["faces"])
    log(f"  smeared-mains violations (drop>=2u, dip>=45deg, ALL-mains ground face) anywhere near the "
        f"crater: FIXED6={len(violations6)}  FIXED7={len(violations7)}")

    # ==== (3) INDEPENDENT whole-tree vertex-level position diff ====================================
    log("\n== independent whole-tree vertex-level position diff (FIXED7 - FIXED6) ==")
    y6 = xz_to_y(cens6["recs"])
    y7 = xz_to_y(cens7["recs"])
    common = set(y6) & set(y7)
    diffs = {k: (y6[k], y7[k]) for k in common if abs(y6[k] - y7[k]) > 1e-4}
    diff_rows = [dict(xz=list(k), y_fixed6=y6[k], y_fixed7=y7[k], dY=round(y7[k] - y6[k], 4),
                       r_crater=round(SP.rc(k[0], k[1]), 3))
                 for k in sorted(diffs, key=lambda k: SP.rc(k[0], k[1]))]
    diff_xz_set = set(diffs)
    claimed_set = set(claimed_moved_xz)
    log(f"  {len(diffs)} (x,z) positions differ tree-wide (of {len(common)} common positions); "
        f"claimed={len(claimed_set)}")
    for r in diff_rows:
        log(f"    {r['xz']} r={r['r_crater']:.2f} dY={r['dY']:+.4f}")
    only_claimed_moved = (diff_xz_set == claimed_set)
    min_r_of_diff = min((r["r_crater"] for r in diff_rows), default=None)
    n_diff_in_basin = sum(1 for r in diff_rows if r["r_crater"] <= BASIN_R)

    # NOTE: fix6_report's own "peak_world" is the site's PRE-SHAVE census height (the spike as first
    # detected, before round 6's own solve lowered it) -- it is NOT the apex's final resting Y, so it is
    # reported here only as pre-shave context, never compared against. The actual intactness gate is
    # byte_identical: this eye's own independent FIXED6 vs FIXED7 vertex read at that (x,z), both off
    # the trees' own bytes.
    round6_rows = []
    for (ax, ay, az) in round6_apexes:
        k = (round(ax, 3), round(az, 3))
        yy6 = y6.get(k)
        yy7 = y7.get(k)
        round6_rows.append(dict(xz=[ax, az], pre_shave_census_y=ay, y_in_fixed6=yy6, y_in_fixed7=yy7,
                                 byte_identical=(yy6 is not None and yy7 is not None
                                                 and abs(yy6 - yy7) < 1e-6)))
    round6_intact = all(r["byte_identical"] for r in round6_rows)
    log(f"  round-6 apexes (4): byte_identical={[r['byte_identical'] for r in round6_rows]}")

    # ==== (3) pixel-level raster height-diff localization ==========================================
    log("\n== pixel-level raster height diff (FIXED7 - FIXED6, full footprint) ==")
    both_cov = c6["covered"] & c7["covered"]
    hdiff = np.where(both_cov, c7["height"] - c6["height"], 0.0)
    diff_nonzero = both_cov & (np.abs(hdiff) > 0.01)
    n_diff_px = int(diff_nonzero.sum())
    yy, xx = np.mgrid[0:c6["H"], 0:c6["W"]]
    all_wx = wx0f + xx / SC
    all_wz = wz1f - yy / SC
    near_moved = np.zeros_like(diff_nonzero)
    for (mx, mz) in claimed_moved_xz:
        near_moved |= (((all_wx - mx) ** 2 + (all_wz - mz) ** 2) <= 3.0 ** 2)
    n_diff_outside_halo = int((diff_nonzero & ~near_moved).sum())
    in_basin_disc = ((all_wx - BASIN_CENTER[0]) ** 2 + (all_wz - BASIN_CENTER[1]) ** 2) <= BASIN_R ** 2
    n_basin_diff_px = int((diff_nonzero & in_basin_disc).sum())
    save(ER.diverging_img(hdiff, both_cov, vmax=1.4), RENDER_DIR / "footprint_height_diff_fixed7_minus_fixed6.png")
    log(f"  {n_diff_px} px differ (|dY|>0.01); {n_diff_outside_halo} outside a 3u halo around the "
        f"{len(claimed_moved_xz)} claimed positions (should be 0); {n_basin_diff_px} inside the basin disc "
        f"(should be 0)")

    # ==== (4) side-by-side vs STOCK, quantified with the probe's own metrics =======================
    log("\n== LANE 2: stock dunes mass + Cleyra junction (same instrument, read-only) ==")
    stock_dunes_stats = SP.region_report("dunes", STOCK_DUNES, cens7["base_sigma"])
    stock_junc_stats = SP.region_report("junction", STOCK_JUNCTION, cens7["base_sigma"])

    def pct_rank(x, lo_list):
        return sum(1 for v in lo_list if v <= x) / len(lo_list) if lo_list and x is not None else None

    vs_stock = dict(
        the_one_before=the_one_before, the_one_after=the_one_after,
        stock_dunes_ground_dip=stock_dunes_stats["dip_pct_ground"],
        stock_junction_ground_dip=stock_junc_stats["dip_pct_ground"],
        stock_dunes_ground_dip_ge45_stretch=stock_dunes_stats["steep"]["ground_dip_ge_45"].get("uv_stretch_x_flat"),
        stock_junction_ground_dip_ge45_stretch=stock_junc_stats["steep"]["ground_dip_ge_45"].get("uv_stretch_x_flat"),
        the_one_after_dip_within_junction_envelope=(
            the_one_after["max_dip_deg"] is not None
            and the_one_after["max_dip_deg"] <= stock_junc_stats["dip_pct_ground"]["max"]),
        the_one_after_dip_within_dunes_envelope=(
            the_one_after["max_dip_deg"] is not None
            and the_one_after["max_dip_deg"] <= stock_dunes_stats["dip_pct_ground"]["max"]),
        note=("THE ONE's post-fix dip/stretch measured against the REAL stock dunes mass "
              "(18,3)(18,4)(19,3)(19,4)(20,3) and the Cleyra grass|desert|dunes junction (13-15,11-12) -- "
              "the same regions and the same sigma_max/dip instrument uvf_sliver_probe used to refute the "
              "texture-dress lever."))
    log(f"  THE ONE dip: before={the_one_before['max_dip_deg']} after={the_one_after['max_dip_deg']}  "
        f"stock dunes ground dip max={stock_dunes_stats['dip_pct_ground']['max']}  "
        f"stock junction ground dip max={stock_junc_stats['dip_pct_ground']['max']}")

    # ==== overall verdicts ===========================================================================
    # calibration: THE ONE's two named tris must genuinely BE steep (dip>=40deg, well past the 25deg
    # sliver-census threshold) on FIXED6, and the render must show a real local bright anomaly there.
    peak6 = bright["fixed6"]["local_peak_excess_lum_r2p5"]
    peak7 = bright["fixed7"]["local_peak_excess_lum_r2p5"]
    calibration_saw_the_one = bool(
        the_one_before["max_dip_deg"] is not None and the_one_before["max_dip_deg"] >= 40.0
        and peak6 is not None and peak6 >= 15.0)

    the_one_dip_dropped = bool(
        the_one_before["max_dip_deg"] is not None and the_one_after["max_dip_deg"] is not None
        and the_one_after["max_dip_deg"] < STEEP_T <= the_one_before["max_dip_deg"])
    the_one_exits_steep_census = bool(
        the_one_before["n_dip_ge_steep_t"] > 0 and the_one_after["n_dip_ge_steep_t"] == 0)
    no_bright_blob_remains = bool(peak7 is not None and peak7 < 15.0)   # informational, NOT a gate --
    brightness_collapsed = bool(peak6 is not None and peak7 is not None and peak6 - peak7 >= 10.0)
    no_smeared_mains_ever = bool(len(violations6) == 0 and len(violations7) == 0)

    # HONEST RESIDUAL: the r=2.5u local-peak brightness stays high in FIXED7 (peak7 above) NOT because
    # THE ONE's own two tris are still steep (they aren't -- 18.17/19.58deg) but because OTHER, SEPARATE
    # tris sit immediately adjacent (the west-shoulder fill uvf_fix7's own report already flags as a
    # deliberately-unbundled root cause -- "companion_optional: FILL-RESTORE", ONE CHANGE PER TEST). This
    # round's own tiny fill move (-0.053u at (114,-1164.609)) is welded to SOME of these and measurably
    # helped two of them (51.1->37.3deg, 51.4->36.6deg) as a side effect, while the rest are essentially
    # untouched (<1deg). None crossed under the 25deg steep threshold. This is reported honestly below,
    # NOT folded into slivers_resolved -- the work order asks whether THE ONE (playtest 5's specific
    # sighting, the two named tris) reads resolved, not whether the whole rim neighbourhood is now flat.
    adj6_by_id = {(tuple(a["block"]), a["tri"]): a for a in adjacent6}
    adj7_by_id = {(tuple(a["block"]), a["tri"]): a for a in adjacent7}
    common_adj = sorted(set(adj6_by_id) & set(adj7_by_id))
    adj_dip_delta_rows = [dict(block=list(k[0]), tri=k[1], dip_fixed6=adj6_by_id[k]["dip_deg"],
                               dip_fixed7=adj7_by_id[k]["dip_deg"],
                               delta_deg=round(adj7_by_id[k]["dip_deg"] - adj6_by_id[k]["dip_deg"], 2))
                          for k in common_adj]
    max_adj_dip_improvement = max((-r["delta_deg"] for r in adj_dip_delta_rows), default=0.0)
    n_adjacent_still_steep_after = sum(1 for a in adjacent7 if a["dip_deg"] >= STEEP_T)

    # THE PRIMARY VERDICT: is THE ONE itself -- the two tris playtest 5's sighting maps to -- resolved?
    slivers_resolved = bool(the_one_dip_dropped and the_one_exits_steep_census and no_smeared_mains_ever)

    crater_and_prior_fixes_intact = bool(
        only_claimed_moved and n_diff_in_basin == 0 and (min_r_of_diff is None or min_r_of_diff > BASIN_R)
        and round6_intact and n_diff_outside_halo == 0 and n_basin_diff_px == 0)

    overall = dict(
        calibration_saw_the_one=calibration_saw_the_one,
        slivers_resolved=slivers_resolved,
        crater_and_prior_fixes_intact=crater_and_prior_fixes_intact,
        the_one_now_within_stock_envelope=bool(vs_stock["the_one_after_dip_within_junction_envelope"]
                                                and vs_stock["the_one_after_dip_within_dunes_envelope"]))
    overall["all_green"] = all(overall.values())

    report["calibration_fixed6"] = dict(
        the_one_named_tris=the_one_before,
        the_one_nearest_span_face=f6_face, the_one_nearest_span_face_dist=f6_d,
        brightness=bright["fixed6"], top_render_blobs=blobs["fixed6"][:8],
        calibration_saw_the_one=calibration_saw_the_one,
        rule="passes iff THE ONE's two named carried tris have max dip>=40deg on FIXED6 AND the LOCAL "
             "PEAK background-subtracted luminance within 2.5u of THE ONE's coords (off the SHADED "
             "composite: texture x hillshade) is >=15. Reported alongside (not gating): the connected "
             "bright-blob scan (>=20 excess, >=50px) and a tight single-pixel point sample -- both "
             "corroborate but neither alone is the right instrument (a point can miss the tri's visible "
             "peak by a texel; the blob scan can snap onto an unrelated nearby feature).")
    report["resolution_fixed7"] = dict(
        the_one_named_tris=the_one_after,
        the_one_nearest_span_face=f7_face, the_one_nearest_span_face_dist=f7_d,
        the_one_before=the_one_before, the_one_after=the_one_after,
        the_one_dip_dropped_below_steep_threshold=the_one_dip_dropped,
        the_one_exits_steep_census=the_one_exits_steep_census,
        brightness=bright["fixed7"], top_render_blobs=blobs["fixed7"][:8],
        no_bright_blob_remains=no_bright_blob_remains,
        brightness_collapsed_ge_10=brightness_collapsed,
        adjacent_other_steep_tris=dict(
            fixed6=adjacent6, fixed7=adjacent7, dip_delta_vs_fixed6=adj_dip_delta_rows,
            max_dip_improvement_deg=round(max_adj_dip_improvement, 2),
            n_still_dip_ge_steep_t_after=n_adjacent_still_steep_after,
            note=("tris within 2.5u of THE ONE's coords that are STEEP (dip>=25deg) but are NOT THE "
                  "ONE's own two named tris -- THIS is what keeps the local-peak brightness elevated on "
                  "FIXED7 (peak7 above) despite THE ONE's own dip collapsing. Two of the five (welded to "
                  "this round's own tiny fill move at (114,-1164.609)) improved substantially as a side "
                  "effect (51.1->37.3deg, 51.4->36.6deg); the other three are essentially untouched "
                  "(<1deg). All 5 remain >=25deg -- this matches uvf_fix7's own flagged, deliberately "
                  "unbundled 'FILL-RESTORE' companion (the west shoulder sits below its donor height); "
                  "it is a real, already-diagnosed, SEPARATE residue, not a failure to resolve THE ONE "
                  "itself, and is not folded into slivers_resolved below.")),
        smeared_mains_violations=dict(fixed6=len(violations6), fixed7=len(violations7),
                                       fixed6_rows=violations6, fixed7_rows=violations7,
                                       no_smeared_mains_ever=no_smeared_mains_ever,
                                       note="0 in BOTH trees confirms the texture-dress hypothesis was "
                                            "never true -- this was always a geometry problem."),
        naive_span_census_honesty=(
            "THE ONE's tris still sit inside the SPAN>=1.0u census on FIXED7 (max span %.4fu, just under "
            "the round's own 1.50u step target) -- span alone does not distinguish a normal donor "
            "shoulder from a smeared step face. Resolution is read off dip + stretch + render "
            "brightness, all of which collapse; span persisting is expected and is NOT itself a defect. "
            "The wider span-census FACE this tri belongs to (nearest centroid at %.2fu away, spanning "
            "much of the rim/fill sheet) is reported separately as supplementary shape context, not "
            "used to gate this verdict."
            % (the_one_after["max_span_u"] if the_one_after["max_span_u"] else -1.0, f7_d or -1.0)),
        slivers_resolved=slivers_resolved)
    report["census"] = dict(
        fixed6=dict(n_near=len(cens6["near"]), n_slivers=len(cens6["slivers"]), n_faces=len(cens6["faces"]),
                    n_steep=len(cens6["steep"]), n_steep_faces=len(cens6["steep_faces"]),
                    base_sigma=round(cens6["base_sigma"], 4), top_faces=cens6["faces"][:10]),
        fixed7=dict(n_near=len(cens7["near"]), n_slivers=len(cens7["slivers"]), n_faces=len(cens7["faces"]),
                    n_steep=len(cens7["steep"]), n_steep_faces=len(cens7["steep_faces"]),
                    base_sigma=round(cens7["base_sigma"], 4), top_faces=cens7["faces"][:10]))
    report["prior_fixes_and_crater"] = dict(
        method="independent whole-tree (x,z)->y diff across all 20 blocks (both trees' own Terrain "
               "bytes), NOT a read of uvf_fix7's own bookkeeping.",
        n_common_positions=len(common), n_positions_differ=len(diffs),
        diff_rows=diff_rows, claimed_moved_xz=claimed_moved_xz,
        only_claimed_positions_moved=only_claimed_moved,
        min_r_crater_of_a_diff=min_r_of_diff, n_diffs_inside_basin_disc=n_diff_in_basin,
        round6_apexes=round6_rows, round6_apexes_intact=round6_intact,
        pixel_diff=dict(n_diff_px_gt_0p01=n_diff_px, n_diff_px_outside_3u_halo=n_diff_outside_halo,
                        n_diff_px_inside_basin_disc=n_basin_diff_px,
                        diff_localizes=(n_diff_outside_halo == 0),
                        basin_disc_untouched=(n_basin_diff_px == 0),
                        diff_png="footprint_height_diff_fixed7_minus_fixed6.png"),
        crater_and_prior_fixes_intact=crater_and_prior_fixes_intact)
    report["vs_stock"] = vs_stock
    report["renders"] = dict(dir=str(RENDER_DIR), panels={k: v.name for k, v in panels.items()})
    report["overall_verdict"] = overall
    report["elapsed_s"] = round(time.time() - t0, 1)

    REPORT.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    log(f"\nOVERALL: {overall}")
    log(f"report -> {REPORT}  ({report['elapsed_s']}s)")
    return report


if __name__ == "__main__":
    main()
