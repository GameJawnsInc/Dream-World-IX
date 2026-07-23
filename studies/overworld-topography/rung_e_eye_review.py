"""EYE-SKEPTIC REVIEW of rung_e_build.py's DRY-RUN output -- THE CALIBRATED EYE, READ-ONLY, zero
writes to the game install.

Adapted from ``rung_d_eye_review.py`` (Rung D's single-lobe reviewer, itself adapted from
``mixed_biome_eye_review.py``) for Rung E's TWO-LOBE composition (the horseshoe massif, UNCHANGED
from Rung D, fused through the reserved (0-2,12-15) corridor arm to a new Uaho north anchor).
Loads the would-be-deployed file set from ``out/rung_e/FF9CustomMap-world/...`` (never the game
install) + real stock ring/comparison blocks, using ``ff9mapkit.world.atlas.load_atlas`` (the FIXED
atlas resolver every sibling eye-review script in this study relies on -- kept unchanged here too).

THE CALIBRATION DISCIPLINE (the Z-sign lesson this task brief names): a rendering instrument is not
trustworthy until it reproduces KNOWN-GOOD stock as good. Every render below is produced by the
SAME painter's-algorithm function (``render_shaded``, self-contained/duplicated in this file rather
than imported -- matching this study's own established convention of keeping each eye-review script
independently rerunnable, e.g. ``mixed_biome_eye_review.py``'s own docstring, and ``dunes_strip_
emitter.py``'s ``render_plan`` / ``render_calibration.py``'s explicit re-use-not-reimplement
pattern). STEP 1 runs that exact function against PURE STOCK ground truth FIRST (never a block this
build touched) and only proceeds to judge the new build once that control reads correctly. Two
inherited findings from this study's own prior calibration work are carried forward rather than
re-discovered blind:
  - ``render_calibration.py`` (round-3/desert|dunes arc): at very tight zoom (window <~30u, high px/u
    scale), STOCK ground ALSO exposes its 4u cell-lattice mosaic as hard rectangular seams -- that is
    the medium (individually-textured 4u quads), not a synthesis defect. A "castellated" look at
    extreme zoom is only evidence of a real problem if the STOCK control at the SAME zoom does not
    show it too.
  - ``render_plan``'s own painter's-algorithm convention (``dunes_strip_emitter.py``/``massif_face_
    render.py``): triangles are drawn back-to-front sorted by ascending world-Y (taller/higher terrain
    painted LAST, over lower terrain behind it) with a fixed directional light dotted against the
    interpolated vertex normal -- this is what gives a straight-down orthographic plan view its
    pseudo-relief ("elevation") legibility: a real massif reads as a brighter, occluding mass rising
    over the plain behind it; a flat mis-shaded or inverted-normal region reads as uniformly dark or
    inverted-contrast against its neighbours. This IS the "elevation render" instrument this task
    asks for -- there is no separate hillshade tool in this study, and building a second one when
    this one is already proven (calibrated in a prior round, cited above) would violate CALIBRATE-
    THE-INSTRUMENT-BEFORE-YOU-JUDGE-WITH-IT by introducing an UNcalibrated second instrument instead.

Renders (all under ``out/rung_e/renders/``):
  0. rung_e_eye_calibration.png       -- STEP 1: pure STOCK grass|desert cluster (13-15,11-12) +
     the two real STOCK donor massifs (horseshoe (5-6,15-16), Uaho (0,0)), same render_shaded()
     function, same settings later renders reuse. Confirms orientation/atlas-mapping/elevation
     shading are sane BEFORE any dry-run byte is judged.
  1. rung_e_eye_wide_family.png       -- STEP 2a: the full 16-block footprint + 1-block ring,
     FAMILY-colored + shaded (relief-legible silhouette of the whole 2-lobe landmass).
  2. rung_e_eye_wide_elevation.png    -- STEP 2a: the same footprint, HYPSOMETRIC-tinted + shaded
     (a height-only palette, family-independent -- the second, family-blind elevation view).
  3. rung_e_eye_corridor_wide.png     -- STEP 2b: atlas-textured ground render of the whole
     footprint, zoom level 1 (wide).
  4. rung_e_eye_corridor_medium.png   -- STEP 2b: atlas-textured ground render of the retiled
     desert-body blocks + ring, zoom level 2 (medium).
  5. rung_e_eye_corridor_tight.png    -- STEP 2b: atlas-textured ground render, zoom level 3
     (tight, 24x24u per panel -- the SAME window size ``render_calibration.py`` used, both SHADED
     and UNSHADED, directly comparable to that prior calibration's own stock panels).
  6. rung_e_eye_corridor_decals.png   -- texel-crop strip of every dressing decal tri actually
     landed in the retile-touched blocks, ordered by world-Z (the castellation/row-jump hunt).
  7. rung_e_eye_terminus_south.png / _north.png -- STEP 2c: both terminations at close range
     (desert body meeting rock -- GATE 3's own contamination-clear claim, visually).
  8. rung_e_eye_waist.png             -- STEP 2c: the lobe waist (the connector pinch near
     REF_CENTER -- where 3 circles' union used to show a visible kink before the FIX 1(a)/(b)
     restructure).

Run: py studies/overworld-topography/rung_e_eye_review.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from PIL import Image, ImageDraw  # noqa: E402

from ff9mapkit import config as _cfg          # noqa: E402
from ff9mapkit.world import atlas as A        # noqa: E402
from ff9mapkit.world import extract as X      # noqa: E402
from ff9mapkit.world import mesh as M         # noqa: E402

import seam_null_recon as SNR                 # noqa: E402

OUT_DIR = HERE / "out" / "rung_e" / "renders"
MINT_ROOT = HERE / "out" / "rung_e" / "FF9CustomMap-world"
GAME_ROOT = Path(_cfg.find_game_path(None))
BLOCK = 64.0

BUILD = json.loads((HERE / "out" / "rung_e" / "rung_e_build.json").read_text(encoding="utf-8"))
LAYOUT = json.loads((HERE / "out" / "rung_e" / "rung_e_layout.json").read_text(encoding="utf-8"))

FOOTPRINT = [tuple(b) for b in BUILD["file_set_manifest"]["footprint"]]
RETILE_TOUCHED = [tuple(b) for b in LAYOUT["stage3_termini_line_retile"]["retile_touched"]]
TERM_A = tuple(LAYOUT["stage3_termini_line_retile"]["term_a"])   # south terminus (massif side)
TERM_B = tuple(LAYOUT["stage3_termini_line_retile"]["term_b"])   # north terminus (Uaho side)
REF_CENTER = tuple(LAYOUT["site"]["ref_center"])                 # the connector hub / "the waist"
CONNECTOR_RADIUS = LAYOUT["site"]["connector_radius"]

MASSIF_CENTER = tuple(LAYOUT["stage2_massif_anchor"]["realized_center"])
MASSIF_CLEAR = LAYOUT["stage2_massif_anchor"]["clear_radius"]
MASSIF_RRIM = LAYOUT["stage2_massif_anchor"]["r_rim"]
MASSIF_BLOCKS = [tuple(b) for b in LAYOUT["stage2_massif_anchor"]["changed_blocks"]]

NORTH_CENTER = tuple(LAYOUT["stage2b_north_anchor"]["realized_center"])
NORTH_CLEAR = LAYOUT["stage2b_north_anchor"]["clear_radius"]
NORTH_RRIM = LAYOUT["stage2b_north_anchor"]["r_rim"]
NORTH_BLOCKS = [tuple(b) for b in LAYOUT["stage2b_north_anchor"]["changed_blocks"]]

HORSESHOE_DONOR = [tuple(b) for b in LAYOUT["site"]["horseshoe_donor"]]
UAHO_DONOR = tuple(LAYOUT["site"]["uaho_donor"])

GATE1 = BUILD["gate1_coast_standoff"]
GATE2 = BUILD["gate2_dressing_ratio"]
GATE3 = BUILD["gate3_termination_decal"]
GATE4 = BUILD["gate4_macro_silhouette"]

FAM_COLOR = {
    "grass": (86, 148, 60), "desert": (196, 158, 100), "rock": (120, 110, 100),
    "hole": (20, 20, 20), "dunes": (214, 196, 140), "scrub": (120, 150, 90),
    "strip": (230, 60, 200),               # any STRIPS(grass,desert)-style decal tri -- flag bright
    None: (35, 60, 100),                   # sea / unresolved -> ocean-blue placeholder
}
ROCK_TOPOS = {49, 7, 62, 58}

LDIR = (-0.45, 0.72, 0.45)                 # dunes_strip_emitter.py's own calibrated light direction
_l = math.sqrt(sum(q * q for q in LDIR))
LDIR = tuple(q / _l for q in LDIR)


def log(msg):
    print(msg)


def label(img, text, h=18):
    im2 = Image.new("RGB", (img.width, img.height + h), (18, 18, 18))
    im2.paste(img, (0, h))
    d = ImageDraw.Draw(im2)
    d.text((2, 2), text, fill=(255, 255, 255))
    return im2


def hcat(imgs, pad=4, bg=(18, 18, 18)):
    h = max(i.height for i in imgs)
    w = sum(i.width for i in imgs) + pad * (len(imgs) - 1)
    out = Image.new("RGB", (w, h), bg)
    x = 0
    for i in imgs:
        out.paste(i, (x, 0))
        x += i.width + pad
    return out


def vcat(imgs, pad=4, bg=(18, 18, 18)):
    w = max(i.width for i in imgs)
    h = sum(i.height for i in imgs) + pad * (len(imgs) - 1)
    out = Image.new("RGB", (w, h), bg)
    y = 0
    for i in imgs:
        out.paste(i, (0, y))
        y += i.height + pad
    return out


def sheet(panels, cols, cell_w, cell_h, label_h=22, path=None, title=""):
    rows = (len(panels) + cols - 1) // cols
    pad = 10
    W = cols * (cell_w + pad) + pad
    H = rows * (cell_h + label_h + pad) + pad + (40 if title else 0)
    im = Image.new("RGB", (W, H), (16, 16, 16))
    dr = ImageDraw.Draw(im)
    if title:
        for i, line in enumerate(title.split("\n")):
            dr.text((pad, 6 + 14 * i), line, fill=(255, 230, 140))
    for i, (lab, panel) in enumerate(panels):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = pad + (40 if title else 0) + r * (cell_h + label_h + pad)
        dr.text((x, y), lab, fill=(230, 230, 230))
        pw, ph = panel.size
        scale = min(cell_w / pw, cell_h / ph)
        rp = panel.resize((max(1, int(pw * scale)), max(1, int(ph * scale))), Image.NEAREST)
        im.paste(rp, (x, y + label_h))
    if path:
        im.save(path)
        log(f"-> {path}  ({im.width}x{im.height})")
    return im


# ====================================================================================================
# classification (verbatim method from rung_d_eye_review.py / mixed_biome_eye_review.py)
# ====================================================================================================
def classify_fam_or_strip(topo, uv3):
    if topo in ROCK_TOPOS:
        return "rock"
    if topo == 59:
        return "hole"
    cls, detail = SNR.classify_tri(SNR.FAM_OF.get(topo), uv3) if topo in SNR.FAM_OF else ("other", None)
    if cls == "strip_grass_desert":
        return "strip"
    return SNR.FAM_OF.get(topo)


# ====================================================================================================
# block loading -- footprint blocks read the RUNG-E DRY-RUN file set; everything else reads real
# stock bytes. A separate ``load_bm_stock`` bypasses the footprint check entirely (used ONLY by the
# calibration step, so calibration can never accidentally read a dry-run byte).
# ====================================================================================================
def load_bm(bx, by):
    if (bx, by) in FOOTPRINT:
        rel = M.override_relpath(1, bx, by, part="Terrain")
        path = MINT_ROOT / rel
        if not path.is_file():
            return None, None
        return M.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by, part="terrain"), "rung_e-dry-run"
    try:
        return X.read_block(bx, by, disc=1, part="terrain"), "stock"
    except (ValueError, FileNotFoundError):
        return None, None


def load_bm_stock(bx, by):
    try:
        return X.read_block(bx, by, disc=1, part="terrain"), "stock"
    except (ValueError, FileNotFoundError):
        return None, None


def _ring(core, radius=1):
    return sorted({(bx + dx, by + dy) for (bx, by) in core
                  for dx in range(-radius, radius + 1) for dy in range(-radius, radius + 1)
                  if 0 <= bx + dx < 24 and 0 <= by + dy < 20})


# ====================================================================================================
# THE SHADED PAINTER'S-ALGORITHM RENDERER -- the ONE instrument every render in this script uses
# (calibration included). Ported from dunes_strip_emitter.py's own ``render_plan``/``at_b``
# (duplicated, not imported -- per this study's own independent-rerunnability convention) and
# generalized: (a) a pluggable per-block loader (mint-aware vs pure-stock), (b) 3 color modes
# (atlas-textured / flat family / hypsometric elevation-tint), all sharing the SAME back-to-front
# Y-sort + normal-dot-light shading pass, so a "sane elevation shading" verdict reached in
# calibration transfers directly to every later panel.
# ====================================================================================================
def _bilinear(apx, aw, ah, u, v):
    fx = (u % 1.0) * aw - 0.5
    fy = (1.0 - v % 1.0) * ah - 0.5
    x0, y0 = int(math.floor(fx)), int(math.floor(fy))
    tx, ty = fx - x0, fy - y0
    acc = [0.0, 0.0, 0.0]
    aa = 0.0
    for (dx, dy, wg) in ((0, 0, (1 - tx) * (1 - ty)), (1, 0, tx * (1 - ty)),
                         (0, 1, (1 - tx) * ty), (1, 1, tx * ty)):
        px_, py_ = min(max(x0 + dx, 0), aw - 1), min(max(y0 + dy, 0), ah - 1)
        r, g, b, a = apx[px_, py_]
        acc[0] += r * wg; acc[1] += g * wg; acc[2] += b * wg; aa += a * wg
    return aa, (acc[0], acc[1], acc[2])


_ELEV_STOPS = [(0.0, (35, 85, 130)), (0.05, (60, 120, 80)), (0.35, (110, 160, 80)),
               (0.60, (185, 165, 100)), (0.82, (170, 120, 90)), (1.0, (240, 235, 225))]


def _elev_color(y, y0, y1):
    t = 0.0 if y1 <= y0 else max(0.0, min(1.0, (y - y0) / (y1 - y0)))
    for (t0, c0), (t1, c1) in zip(_ELEV_STOPS, _ELEV_STOPS[1:]):
        if t <= t1:
            f = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
            return tuple(int(c0[k] + f * (c1[k] - c0[k])) for k in range(3))
    return _ELEV_STOPS[-1][1]


def render_shaded(blocks, cx, cz, win_x, win_z, sc, *, mode="atlas", loader=load_bm,
                  atlas_img=None, elev_range=None, must_have=(), shade=True):
    """mode: 'atlas' (real ground texture) / 'family' (flat FAM_COLOR) / 'elevation' (hypsometric
    tint). shade=False skips the normal-dot-light multiply (raw albedo -- the render_calibration.py
    UNSHADED control, isolates texture-lattice artifacts from lighting artifacts). Returns
    (image, n_blocks_read, src_by_block, fam_counts, y_range_seen)."""
    x0, x1 = cx - win_x / 2, cx + win_x / 2
    z0, z1 = cz - win_z / 2, cz + win_z / 2
    RW, RH = max(1, int(win_x * sc)), max(1, int(win_z * sc))
    img = Image.new("RGB", (RW, RH), (18, 26, 46))
    pix = img.load()
    apx = aw = ah = None
    if mode == "atlas":
        assert atlas_img is not None, "atlas mode needs atlas_img"
        apx, (aw, ah) = atlas_img.load(), atlas_img.size

    tris = []
    n_read = 0
    src_by_block = {}
    fam_counts = {}
    ys_seen = []
    for (bx, by) in blocks:
        bm, src = loader(bx, by)
        if bm is None:
            if (bx, by) in must_have:
                raise FileNotFoundError(f"required block missing from loader: {(bx, by)}")
            continue
        n_read += 1
        src_by_block[(bx, by)] = src
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            if max(p[0] for p in w) < x0 or min(p[0] for p in w) > x1:
                continue
            if max(p[2] for p in w) < z0 or min(p[2] for p in w) > z1:
                continue
            uv = [tuple(bm.uvs[j][:2]) for j in tri]
            n3 = [tuple(bm.normals[j][:3]) for j in tri]
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            fam = classify_fam_or_strip(topo, uv)
            fam_counts[fam] = fam_counts.get(fam, 0) + 1
            ymax = max(p[1] for p in w)
            ys_seen.append(sum(p[1] for p in w) / 3.0)
            tris.append((ymax, w, uv, n3, fam))

    if mode == "elevation" and elev_range is None:
        elev_range = (min(ys_seen), max(ys_seen)) if ys_seen else (0.0, 1.0)

    for _, w, uv, n3, fam in sorted(tris, key=lambda t: t[0]):
        sx = [(p[0] - x0) * sc for p in w]
        sy = [(p[2] - z0) * sc for p in w]
        bx0, bx1 = int(min(sx)), int(max(sx)) + 1
        by0, by1 = int(min(sy)), int(max(sy)) + 1
        if bx1 < 0 or bx0 >= RW or by1 < 0 or by0 >= RH:
            continue
        d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(d) < 1e-9:
            continue
        flat_rgb = None
        if mode == "family":
            flat_rgb = FAM_COLOR.get(fam, (200, 0, 200))
        elif mode == "elevation":
            ycent = sum(p[1] for p in w) / 3.0
            flat_rgb = _elev_color(ycent, *elev_range)
        for pxx in range(max(0, bx0), min(RW, bx1)):
            for pyy in range(max(0, by0), min(RH, by1)):
                w0 = ((sy[1] - sy[2]) * (pxx - sx[2]) + (sx[2] - sx[1]) * (pyy - sy[2])) / d
                w1 = ((sy[2] - sy[0]) * (pxx - sx[2]) + (sx[0] - sx[2]) * (pyy - sy[2])) / d
                w2 = 1 - w0 - w1
                if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                    continue
                if flat_rgb is not None:
                    rgb = flat_rgb
                else:
                    aa, rgb = _bilinear(apx, aw, ah,
                                        w0 * uv[0][0] + w1 * uv[1][0] + w2 * uv[2][0],
                                        w0 * uv[0][1] + w1 * uv[1][1] + w2 * uv[2][1])
                    if aa < 24:
                        continue
                if shade:
                    nx = sum(ww * n3[k][0] for k, ww in enumerate((w0, w1, w2)))
                    ny = sum(ww * n3[k][1] for k, ww in enumerate((w0, w1, w2)))
                    nz = sum(ww * n3[k][2] for k, ww in enumerate((w0, w1, w2)))
                    nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                    f = 0.45 + 0.55 * max(0.0, (nx * LDIR[0] + ny * LDIR[1] + nz * LDIR[2]) / nl)
                else:
                    f = 1.0
                pix[pxx, pyy] = tuple(min(255, int(c * f)) for c in rgb)
    return img, n_read, src_by_block, fam_counts, elev_range


def _annotate_blocks(img, cx, cz, win_x, win_z, sc, blocks, *, highlight=()):
    """Overlay block-boundary rectangles + '(bx,by)' labels -- the orientation cross-check: every
    panel below can be visually verified against the JSON block coordinates (no compass words
    needed -- the labeled grid itself proves/disproves an axis flip)."""
    x0, z0 = cx - win_x / 2, cz - win_z / 2
    d = ImageDraw.Draw(img)

    def px(wx, wz):
        return (int((wx - x0) * sc), int((wz - z0) * sc))

    for (bx, by) in blocks:
        ox, oz = X.block_world_origin(bx, by)
        p0, p1 = px(ox, oz), px(ox + BLOCK, oz + BLOCK)
        col = (255, 60, 60) if (bx, by) in highlight else (255, 255, 0) if (bx, by) in FOOTPRINT \
            else (110, 110, 110)
        d.rectangle([p0, p1], outline=col, width=2)
        d.text((p0[0] + 3, p0[1] + 3), f"({bx},{by})", fill=(255, 255, 255))
    return img


def _mark(img, cx, cz, win_x, win_z, sc, wx, wz, *, color=(0, 220, 255), text=""):
    x0, z0 = cx - win_x / 2, cz - win_z / 2
    d = ImageDraw.Draw(img)
    p = (int((wx - x0) * sc), int((wz - z0) * sc))
    d.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], outline=color, width=3)
    if text:
        d.text((p[0] + 8, p[1] - 8), text, fill=color)
    return img


# ====================================================================================================
# STEP 1 -- CALIBRATE FIRST (mandatory). PURE STOCK ground truth only (load_bm_stock -- the
# footprint-aware loader is never used here), same render_shaded() every later step reuses.
# ====================================================================================================
def step1_calibration():
    log("=" * 100)
    log("STEP 1 -- CALIBRATION (mandatory, the Z-sign lesson): render KNOWN-GOOD STOCK first, "
        "confirm orientation / atlas-mapping / elevation shading are sane, BEFORE judging the build")
    log("=" * 100)
    atlas_img = A.load_atlas(part="terrain", game=GAME_ROOT, source="engine")
    log(f"engine atlas resolved: {atlas_img.width}x{atlas_img.height} (this IS the pixels the game "
        f"renders -- 1024^2 = bundle default, larger = a loose HD/Moguri override is winning)")

    panels = []

    # (a) the real stock grass|desert cluster the study's own contract is built from -- proves the
    #     atlas-textured SHADED mode reads as an ordinary organic ecotone, matching every other eye-
    #     review script's own "stock A/B" comparator (13-15,11-12).
    core = [(13, 11), (13, 12), (14, 11), (14, 12), (15, 11), (15, 12)]
    cx, cz = 14 * 64 + 32, -(11 * 64 + 64)
    img, nread, src, fam, _ = render_shaded(_ring(core), cx, cz, 220, 180, 3.0, mode="atlas",
                                            loader=load_bm_stock, atlas_img=atlas_img,
                                            must_have=set(core))
    _annotate_blocks(img, cx, cz, 220, 180, 3.0, _ring(core), highlight=core)
    log(f"  (a) STOCK grass|desert cluster (13-15,11-12): {nread} blocks read, family mix {fam}")
    panels.append((f"(a) STOCK grass|desert (13-15,11-12) -- ATLAS+SHADED -- fam={fam}", img))

    # (b) the real stock horseshoe donor (5-6,15-16) -- the SAME donor rung_e's massif carries --
    #     elevation shading sanity: a real massif should read as a bright, occluding relief mass.
    core_hs = HORSESHOE_DONOR
    cx_hs, cz_hs = 5.5 * 64 + 32, -(15.5 * 64 + 32)
    img_hs, nread_hs, _, fam_hs, _ = render_shaded(_ring(core_hs), cx_hs, cz_hs, 200, 200, 3.2,
                                                   mode="atlas", loader=load_bm_stock,
                                                   atlas_img=atlas_img, must_have=set(core_hs))
    _annotate_blocks(img_hs, cx_hs, cz_hs, 200, 200, 3.2, _ring(core_hs), highlight=core_hs)
    log(f"  (b) STOCK horseshoe donor (5-6,15-16): {nread_hs} blocks read, family mix {fam_hs}")
    panels.append((f"(b) STOCK horseshoe donor (5-6,15-16) -- ATLAS+SHADED", img_hs))

    # (c) the real stock Uaho donor (0,0) -- the SAME donor rung_e's north anchor carries.
    core_uh = [UAHO_DONOR]
    cx_uh, cz_uh = 32, -32
    img_uh, nread_uh, _, fam_uh, _ = render_shaded(_ring(core_uh), cx_uh, cz_uh, 180, 180, 3.2,
                                                   mode="atlas", loader=load_bm_stock,
                                                   atlas_img=atlas_img, must_have=set(core_uh))
    _annotate_blocks(img_uh, cx_uh, cz_uh, 180, 180, 3.2, _ring(core_uh), highlight=core_uh)
    log(f"  (c) STOCK Uaho donor (0,0): {nread_uh} blocks read, family mix {fam_uh}")
    panels.append((f"(c) STOCK Uaho donor (0,0) -- ATLAS+SHADED", img_uh))

    # (d) the render_calibration.py tight-zoom lattice-exposure control, re-run here (not imported --
    #     independent rerun) at the SAME 24x24u/unshaded settings that prior round used, on a pure
    #     stock desert interior block -- carries that prior finding forward into THIS instrument's
    #     own calibration record rather than citing it from memory only.
    tight_core = (14, 12)
    tcx, tcz = 14 * 64 + 46, -(12 * 64 + 18)
    img_tight_shaded, _, _, _, _ = render_shaded(_ring([tight_core]), tcx, tcz, 24, 24, 24,
                                                 mode="atlas", loader=load_bm_stock,
                                                 atlas_img=atlas_img)
    img_tight_unshaded, _, _, _, _ = render_shaded(_ring([tight_core]), tcx, tcz, 24, 24, 24,
                                                   mode="atlas", loader=load_bm_stock,
                                                   atlas_img=atlas_img, shade=False)
    log(f"  (d) render_calibration.py's OWN control re-run here: pure-stock 24x24u tight zoom -- "
        f"per that prior round's finding, stock ground shows a hard-edged 4u lattice at this zoom "
        f"TOO (the medium, not a defect) -- carried forward as the tight-zoom expectation below")
    panels.append(("(d) STOCK tight 24x24u SHADED (render_calibration.py control, rerun)", img_tight_shaded))
    panels.append(("(d) STOCK tight 24x24u UNSHADED (render_calibration.py control, rerun)", img_tight_unshaded))

    path = OUT_DIR / "rung_e_eye_calibration.png"
    sheet(panels, cols=3, cell_w=520, cell_h=460, path=path,
          title="STEP 1 CALIBRATION -- ALL PANELS ARE 100% STOCK, UNMODIFIED, read via the EXACT "
                "render_shaded() function every later render reuses\n"
                "check: (a)/(b)/(c) block labels match their own donor coordinates (no axis flip); "
                "(b)/(c) read as coherent lit relief, not flat/inverted; (d) matches the prior round's "
                "known lattice-exposure finding")
    return dict(path=str(path), gd_fam=fam, horseshoe_fam=fam_hs, uaho_fam=fam_uh,
               gd_blocks_read=nread, horseshoe_blocks_read=nread_hs, uaho_blocks_read=nread_uh)


# ====================================================================================================
# STEP 2a -- ELEVATION renders of the FULL 2-lobe landmass (family-tint + hypsometric-tint, both
# shaded via the SAME calibrated instrument).
# ====================================================================================================
def step2a_elevation(atlas_img):
    log("\n" + "=" * 100)
    log("STEP 2a -- ELEVATION renders of the full 2-lobe landmass (footprint + 1-block ring)")
    log("=" * 100)
    ring = _ring(FOOTPRINT)
    xs = [X.block_world_origin(bx, by)[0] for (bx, by) in ring]
    zs = [X.block_world_origin(bx, by)[1] for (bx, by) in ring]
    cx = (min(xs) + max(xs) + BLOCK) / 2.0
    cz = (min(zs) + max(zs) + BLOCK) / 2.0
    win_x = (max(xs) - min(xs) + BLOCK) + 8
    win_z = (max(zs) - min(zs) + BLOCK) + 8
    sc = 2.6

    img_fam, nread, src, fam_counts, _ = render_shaded(ring, cx, cz, win_x, win_z, sc, mode="family",
                                                        loader=load_bm, atlas_img=atlas_img,
                                                        must_have=set(FOOTPRINT))
    _annotate_blocks(img_fam, cx, cz, win_x, win_z, sc, ring, highlight=MASSIF_BLOCKS + NORTH_BLOCKS)
    _mark(img_fam, cx, cz, win_x, win_z, sc, *MASSIF_CENTER, text=f"massif r_rim={MASSIF_RRIM}")
    _mark(img_fam, cx, cz, win_x, win_z, sc, *NORTH_CENTER, text=f"Uaho r_rim={NORTH_RRIM}")
    _mark(img_fam, cx, cz, win_x, win_z, sc, *REF_CENTER, color=(255, 120, 0),
         text=f"waist (connector hub, R={CONNECTOR_RADIUS})")
    _mark(img_fam, cx, cz, win_x, win_z, sc, *TERM_A, color=(255, 255, 255), text="A (south term)")
    _mark(img_fam, cx, cz, win_x, win_z, sc, *TERM_B, color=(255, 255, 255), text="B (north term)")
    p1 = OUT_DIR / "rung_e_eye_wide_family.png"
    img_fam.save(p1)
    log(f"  FAMILY+shaded: {nread} blocks read ({len(FOOTPRINT)} dry-run + {nread - len(set(FOOTPRINT) & set(ring))} stock); "
        f"family counts: {fam_counts}")
    log(f"  -> {p1}  ({img_fam.width}x{img_fam.height})")

    img_elev, _, _, _, erange = render_shaded(ring, cx, cz, win_x, win_z, sc, mode="elevation",
                                              loader=load_bm, atlas_img=atlas_img,
                                              must_have=set(FOOTPRINT))
    _annotate_blocks(img_elev, cx, cz, win_x, win_z, sc, ring, highlight=MASSIF_BLOCKS + NORTH_BLOCKS)
    _mark(img_elev, cx, cz, win_x, win_z, sc, *MASSIF_CENTER, text="massif")
    _mark(img_elev, cx, cz, win_x, win_z, sc, *NORTH_CENTER, text="Uaho")
    _mark(img_elev, cx, cz, win_x, win_z, sc, *REF_CENTER, color=(255, 120, 0), text="waist")
    p2 = OUT_DIR / "rung_e_eye_wide_elevation.png"
    img_elev.save(p2)
    log(f"  HYPSOMETRIC+shaded: y-range seen {erange}")
    log(f"  -> {p2}  ({img_elev.width}x{img_elev.height})")
    return dict(family=str(p1), elevation=str(p2), fam_counts=fam_counts, y_range=erange,
               n_blocks_read=nread)


# ====================================================================================================
# STEP 2b -- ATLAS-TEXTURED ground render of the ecotone corridor, 3 zoom levels.
# ====================================================================================================
def step2b_corridor(atlas_img):
    log("\n" + "=" * 100)
    log("STEP 2b -- ATLAS ground render of the ecotone corridor, 3 zoom levels")
    log("=" * 100)

    # level 1: wide -- the whole footprint, atlas-textured (same window as step2a, atlas mode)
    ring = _ring(FOOTPRINT)
    xs = [X.block_world_origin(bx, by)[0] for (bx, by) in ring]
    zs = [X.block_world_origin(bx, by)[1] for (bx, by) in ring]
    cx = (min(xs) + max(xs) + BLOCK) / 2.0
    cz = (min(zs) + max(zs) + BLOCK) / 2.0
    win_x, win_z = (max(xs) - min(xs) + BLOCK) + 8, (max(zs) - min(zs) + BLOCK) + 8
    img_wide, nread_w, _, fam_w, _ = render_shaded(ring, cx, cz, win_x, win_z, 3.0, mode="atlas",
                                                    loader=load_bm, atlas_img=atlas_img,
                                                    must_have=set(FOOTPRINT))
    _annotate_blocks(img_wide, cx, cz, win_x, win_z, 3.0, ring, highlight=RETILE_TOUCHED)
    p1 = OUT_DIR / "rung_e_eye_corridor_wide.png"
    img_wide.save(p1)
    log(f"  LEVEL 1 (wide): {nread_w} blocks, family mix {fam_w} -> {p1}  ({img_wide.width}x{img_wide.height})")

    # level 2: medium -- the retile-touched blocks (the desert body) + Moore ring
    core = RETILE_TOUCHED
    ring2 = _ring(core)
    xs2 = [X.block_world_origin(bx, by)[0] for (bx, by) in ring2]
    zs2 = [X.block_world_origin(bx, by)[1] for (bx, by) in ring2]
    cx2 = (min(xs2) + max(xs2) + BLOCK) / 2.0
    cz2 = (min(zs2) + max(zs2) + BLOCK) / 2.0
    win2 = (max(xs2) - min(xs2) + BLOCK) + 8
    winz2 = (max(zs2) - min(zs2) + BLOCK) + 8
    img_med, nread_m, _, fam_m, _ = render_shaded(ring2, cx2, cz2, win2, winz2, 6.5, mode="atlas",
                                                   loader=load_bm, atlas_img=atlas_img,
                                                   must_have=set(core))
    _annotate_blocks(img_med, cx2, cz2, win2, winz2, 6.5, ring2, highlight=core)
    p2 = OUT_DIR / "rung_e_eye_corridor_medium.png"
    img_med.save(p2)
    n_strip = fam_m.get("strip", 0)
    log(f"  LEVEL 2 (medium, retile-touched {core}): {nread_m} blocks, family mix {fam_m} "
        f"({n_strip} STRIPS-style decal tris) -> {p2}  ({img_med.width}x{img_med.height})")

    # level 3: tight -- 24x24u panels (the SAME window render_calibration.py used) centred on the
    # densest straddle-cell cluster within the retile-touched core, SHADED + UNSHADED (per the
    # calibration lesson -- compare directly against step1's stock (d) panels, not in isolation)
    dense_tris = []
    for (bx, by) in core:
        bm, src = load_bm(bx, by)
        if bm is None:
            continue
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            uv = [tuple(bm.uvs[j][:2]) for j in tri]
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            if classify_fam_or_strip(topo, uv) == "strip":
                cx_ = sum(p[0] for p in w) / 3.0
                cz_ = sum(p[2] for p in w) / 3.0
                dense_tris.append((cx_, cz_))
    if dense_tris:
        tcx = sum(p[0] for p in dense_tris) / len(dense_tris)
        tcz = sum(p[1] for p in dense_tris) / len(dense_tris)
    else:
        tcx, tcz = cx2, cz2
    img_tight_sh, _, _, fam_t, _ = render_shaded(ring2, tcx, tcz, 24, 24, 24, mode="atlas",
                                                 loader=load_bm, atlas_img=atlas_img)
    img_tight_un, _, _, _, _ = render_shaded(ring2, tcx, tcz, 24, 24, 24, mode="atlas",
                                             loader=load_bm, atlas_img=atlas_img, shade=False)
    p3 = OUT_DIR / "rung_e_eye_corridor_tight.png"
    sheet([("SHADED (compare vs step1(d) stock-shaded)", img_tight_sh),
          ("UNSHADED (compare vs step1(d) stock-unshaded)", img_tight_un)],
         cols=2, cell_w=560, cell_h=560, path=p3,
         title=f"LEVEL 3 (tight, 24x24u @ {len(dense_tris)}-decal-tri centroid ({tcx:.0f},{tcz:.0f})) "
               f"-- fam mix {fam_t}")

    return dict(wide=str(p1), medium=str(p2), tight=str(p3), fam_wide=fam_w, fam_medium=fam_m,
               fam_tight=fam_t, n_dense_decal_tris=len(dense_tris), tight_center=[tcx, tcz])


def step2b_decal_strip(atlas_img):
    log("\n" + "=" * 100)
    log("STEP 2b (cont.) -- decal texel-crop strip: every dressing decal tri actually landed in "
        "the retile-touched blocks, ordered by world-Z (the castellation/row-jump hunt)")
    log("=" * 100)
    core = RETILE_TOUCHED
    strip_tris = []
    for (bx, by) in core:
        bm, src = load_bm(bx, by)
        if bm is None:
            continue
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            uv = [tuple(bm.uvs[j][:2]) for j in tri]
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            if classify_fam_or_strip(topo, uv) == "strip":
                cz_ = sum(p[2] for p in w) / 3.0
                strip_tris.append((cz_, uv, topo, (bx, by)))
    strip_tris.sort(key=lambda t: t[0])
    crops = []
    for cz_, uv, topo, blk in strip_tris:
        crop = A.crop_tile(atlas_img, uv, pad=1).resize((96, 96), Image.NEAREST)
        crops.append(label(crop, f"z={cz_:.0f} {blk} t{topo}", h=14))
    if crops:
        rows = [hcat(crops[i:i + 10]) for i in range(0, len(crops), 10)]
        strip_sheet = vcat(rows)
    else:
        strip_sheet = Image.new("RGB", (400, 60), (60, 0, 0))
        d2 = ImageDraw.Draw(strip_sheet)
        d2.text((5, 5), "NO decal tris found in retile-touched core", fill=(255, 255, 255))
    p = OUT_DIR / "rung_e_eye_corridor_decals.png"
    strip_sheet.save(p)
    log(f"  {len(strip_tris)} decal tri(s) across {core} -> {p}  ({strip_sheet.width}x{strip_sheet.height})")
    return dict(path=str(p), n_decal_tris=len(strip_tris))


# ====================================================================================================
# STEP 2c -- closeups: both terminations + the lobe waist.
# ====================================================================================================
def step2c_closeups(atlas_img):
    log("\n" + "=" * 100)
    log("STEP 2c -- closeups: both terminations + the lobe waist")
    log("=" * 100)
    out = {}

    for name, pt, blocks_here in (("south", TERM_A, MASSIF_BLOCKS), ("north", TERM_B, NORTH_BLOCKS)):
        core = _ring([(int(pt[0] // BLOCK), int(-pt[1] // BLOCK))], radius=1)
        win = 70.0
        img, nread, _, fam, _ = render_shaded(core, pt[0], pt[1], win, win, 8.0, mode="atlas",
                                              loader=load_bm, atlas_img=atlas_img)
        _annotate_blocks(img, pt[0], pt[1], win, win, 8.0, core, highlight=blocks_here)
        _mark(img, pt[0], pt[1], win, win, 8.0, *pt, text=f"terminus {name}")
        p = OUT_DIR / f"rung_e_eye_terminus_{name}.png"
        img.save(p)
        log(f"  terminus {name} @ {pt}: {nread} blocks, family mix {fam} -> {p}  ({img.width}x{img.height})")
        out[name] = dict(path=str(p), fam=fam)

    win = 90.0
    core_w = _ring([(int(REF_CENTER[0] // BLOCK), int(-REF_CENTER[1] // BLOCK))], radius=1)
    img_w, nread_w, _, fam_w, _ = render_shaded(core_w, REF_CENTER[0], REF_CENTER[1], win, win, 6.5,
                                                mode="atlas", loader=load_bm, atlas_img=atlas_img)
    _annotate_blocks(img_w, REF_CENTER[0], REF_CENTER[1], win, win, 6.5, core_w)
    _mark(img_w, REF_CENTER[0], REF_CENTER[1], win, win, 6.5, *REF_CENTER,
         color=(255, 120, 0), text=f"waist hub C, R={CONNECTOR_RADIUS}")
    p_w = OUT_DIR / "rung_e_eye_waist.png"
    img_w.save(p_w)
    log(f"  lobe waist @ {REF_CENTER}: {nread_w} blocks, family mix {fam_w} -> {p_w}  ({img_w.width}x{img_w.height})")
    out["waist"] = dict(path=str(p_w), fam=fam_w)
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not MINT_ROOT.is_dir():
        sys.exit(f"no dry-run file set at {MINT_ROOT} -- run rung_e_build.py first")

    log(f"BUILD summary: {json.dumps(BUILD['summary'], indent=1)}")
    log(f"FOOTPRINT ({len(FOOTPRINT)} blocks): {FOOTPRINT}")
    log(f"RETILE_TOUCHED (desert body): {RETILE_TOUCHED}")
    log(f"MASSIF center={MASSIF_CENTER} r_rim={MASSIF_RRIM} blocks={MASSIF_BLOCKS}")
    log(f"NORTH (Uaho) center={NORTH_CENTER} r_rim={NORTH_RRIM} blocks={NORTH_BLOCKS}")
    log(f"TERM_A (south)={TERM_A}  TERM_B (north)={TERM_B}  waist/REF_CENTER={REF_CENTER}\n")

    cal = step1_calibration()
    atlas_img = A.load_atlas(part="terrain", game=GAME_ROOT, source="engine")
    elev = step2a_elevation(atlas_img)
    corridor = step2b_corridor(atlas_img)
    decals = step2b_decal_strip(atlas_img)
    closeups = step2c_closeups(atlas_img)

    report = dict(build_summary=BUILD["summary"], gate1=GATE1, gate2=GATE2, gate3=GATE3, gate4=GATE4,
                 footprint=FOOTPRINT, retile_touched=RETILE_TOUCHED,
                 massif=dict(center=MASSIF_CENTER, r_rim=MASSIF_RRIM, blocks=MASSIF_BLOCKS),
                 north_anchor=dict(center=NORTH_CENTER, r_rim=NORTH_RRIM, blocks=NORTH_BLOCKS),
                 term_a=TERM_A, term_b=TERM_B, ref_center=REF_CENTER,
                 calibration=cal, elevation=elev, corridor=corridor, decals=decals, closeups=closeups)
    (OUT_DIR / "rung_e_eye_review.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"\n-> {OUT_DIR / 'rung_e_eye_review.json'}")


if __name__ == "__main__":
    main()
