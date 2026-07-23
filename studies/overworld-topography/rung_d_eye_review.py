"""EYE-SKEPTIC REVIEW of rung_d_build.py's DRY-RUN output -- READ-ONLY, zero writes to the game install.

Adapted from mixed_biome_eye_review.py (the Rung-C reviewer) for Rung D's ONE-MASSIF-TWO-TERMINI design:
loads the would-be-deployed file set from out/rung_d/FF9CustomMap-world/... (never the game install) +
real stock ring/coast/comparison blocks, and renders:

  1. rung_d_eye_wide_planview.png    -- the whole 10-block bench + 1-block ring (stock), family-colored,
     the single carried massif, both termini, the partition line, the OPEN OCEAN to the west.
  2. rung_d_eye_boundary_zoom.png    -- the retiled desert-body blocks, close-range plan.
  3. rung_d_eye_termini_feet.png     -- both terminations at close range (the anchor-foot seam hunt).
  4. rung_d_eye_stock_horseshoe_AB.png -- the REAL stock Daguerreo horseshoe donor (5-6,15-16), same
     render recipe, for direct A/B against the carried copy.
  5. rung_d_eye_stock_gd_AB.png      -- the real stock grass|desert cluster (13-15,11-12), same recipe,
     for the dressing-density A/B (same comparator Rung C used).

Run: py studies/overworld-topography/rung_d_eye_review.py
"""
from __future__ import annotations

import json
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

OUT_DIR = HERE / "out" / "rung_d" / "renders"
MINT_ROOT = HERE / "out" / "rung_d" / "FF9CustomMap-world"
GAME_ROOT = Path(_cfg.find_game_path(None))

BUILD = json.loads((HERE / "out" / "rung_d" / "rung_d_build.json").read_text(encoding="utf-8"))
LAYOUT = json.loads((HERE / "out" / "rung_d" / "rung_d_layout.json").read_text(encoding="utf-8"))
FOOTPRINT = [tuple(b) for b in BUILD["file_set_manifest"]["footprint"]]
TERM_A = tuple(LAYOUT["stage2_rim_termini"]["term_a"])
TERM_B = tuple(LAYOUT["stage2_rim_termini"]["term_b"])
REALIZED_CENTER = tuple(LAYOUT["stage1_anchor"]["realized_center"])
CLEAR_RADIUS = LAYOUT["stage1_anchor"]["clear_radius"]
R_RIM = LAYOUT["stage1_anchor"]["r_rim"]
MASSIF_BLOCKS = [tuple(b) for b in LAYOUT["stage1_anchor"]["changed_blocks"]]
RETILE_TOUCHED = [tuple(b) for b in LAYOUT["stage3_line_and_retile"]["retile_touched"]]
DONOR_BLOCKS = [tuple(b) for b in LAYOUT["site"]["donor"]]

FAM_COLOR = {
    "grass": (86, 148, 60), "desert": (196, 158, 100), "rock": (120, 110, 100),
    "hole": (20, 20, 20), "dunes": (214, 196, 140), "scrub": (120, 150, 90),
    "strip": (230, 60, 200),               # any STRIPS(grass,desert)-style decal tri -- flag bright
    None: (35, 60, 100),                   # sea / unresolved -> ocean-blue placeholder
}
ROCK_TOPOS = {49, 7, 62, 58}


def label(img, text, h=18):
    im2 = Image.new("RGB", (img.width, img.height + h), (18, 18, 18))
    im2.paste(img, (0, h))
    d = ImageDraw.Draw(im2)
    d.text((2, 2), text, fill=(255, 255, 255))
    return im2


def classify_fam_or_strip(topo, uv3):
    if topo in ROCK_TOPOS:
        return "rock"
    if topo == 59:
        return "hole"
    cls, detail = SNR.classify_tri(SNR.FAM_OF.get(topo), uv3) if topo in SNR.FAM_OF else ("other", None)
    if cls == "strip_grass_desert":
        return "strip"
    return SNR.FAM_OF.get(topo)


def load_tris_mixed(blocks, *, must_have_mint=()):
    """Footprint blocks read from the RUNG-D DRY-RUN file set; everything else reads real stock bytes."""
    bm_by_block = {}
    src_by_block = {}
    for (bx, by) in blocks:
        if (bx, by) in FOOTPRINT:
            rel = M.override_relpath(1, bx, by, part="Terrain")
            path = MINT_ROOT / rel
            if not path.is_file():
                if (bx, by) in must_have_mint:
                    raise FileNotFoundError(f"expected mint dry-run file missing: {path}")
                continue
            bm = M.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by, part="terrain")
            src_by_block[(bx, by)] = "rung_d-dry-run"
        else:
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain")
            except (ValueError, FileNotFoundError):
                continue
            src_by_block[(bx, by)] = "stock"
        bm_by_block[(bx, by)] = bm

    tris = []
    for (bx, by), bm in bm_by_block.items():
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            uv = [tuple(bm.uvs[j]) for j in tri]
            fam = classify_fam_or_strip(topo, uv)
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[2] for p in w) / 3.0
            tris.append(dict(block=(bx, by), tri=tri, w=w, uv=uv, topo=topo, fam=fam, c=(cx, cz),
                             src=src_by_block[(bx, by)]))
    return tris, bm_by_block, src_by_block


def _plan(tris, ring, core_outline, extra_draw=None, scale=3.2):
    xs = [p[0] for t in tris for p in t["w"]]
    zs = [p[2] for t in tris for p in t["w"]]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    W, H = int((x1 - x0) * scale) + 30, int((z1 - z0) * scale) + 30
    img = Image.new("RGB", (W, H), (10, 10, 10))
    d = ImageDraw.Draw(img)

    def px(wx, wz):
        return (15 + int((wx - x0) * scale), 15 + int((wz - z0) * scale))

    fam_counts = {}
    for t in tris:
        pts = [px(p[0], p[2]) for p in t["w"]]
        col = FAM_COLOR.get(t["fam"], (200, 0, 200))
        d.polygon(pts, fill=col)
        fam_counts[t["fam"]] = fam_counts.get(t["fam"], 0) + 1
    for (bx, by) in ring:
        ox, oz = X.block_world_origin(bx, by)
        rect = [px(ox, oz - 64), px(ox + 64, oz)]
        outline = (255, 40, 40) if (bx, by) in RETILE_TOUCHED else \
                  ((255, 255, 0) if (bx, by) in core_outline else (70, 70, 70))
        d.rectangle(rect, outline=outline, width=3 if (bx, by) in RETILE_TOUCHED else 2)
        d.text((rect[0][0] + 3, rect[0][1] + 3), f"({bx},{by})", fill=(255, 255, 255))
    if extra_draw:
        extra_draw(d, px)
    return img, fam_counts, px


def render_wide():
    print("=" * 100)
    print("1. WIDE PLAN VIEW -- the full 10-block Rung D bench (dry-run bytes) + 1-block ring (stock)")
    print("=" * 100)
    ring = sorted({(bx + dx, by + dy) for (bx, by) in FOOTPRINT for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  if 0 <= bx + dx < 24 and 0 <= by + dy < 20})
    tris, bms, src = load_tris_mixed(ring, must_have_mint=FOOTPRINT)

    def extra(d, px):
        p = px(*REALIZED_CENTER)
        d.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], outline=(0, 200, 255), width=3)
        d.text((p[0] + 8, p[1] - 8), f"massif center clr={CLEAR_RADIUS}u r_rim={R_RIM}u", fill=(0, 200, 255))
        clr_px = int(CLEAR_RADIUS * 3.2)
        d.ellipse([p[0] - clr_px, p[1] - clr_px, p[0] + clr_px, p[1] + clr_px], outline=(0, 140, 180), width=1)
        pa, pb = px(*TERM_A), px(*TERM_B)
        d.line([pa, pb], fill=(255, 255, 255), width=1)
        for p2, lbl in ((pa, "A"), (pb, "B")):
            d.ellipse([p2[0] - 4, p2[1] - 4, p2[0] + 4, p2[1] + 4], outline=(255, 255, 255), width=2)
            d.text((p2[0] + 6, p2[1] + 6), lbl, fill=(255, 255, 255))

    img, fam_counts, px = _plan(tris, ring, FOOTPRINT, extra_draw=extra)
    print(f"  {len(tris)} tris; family counts: {fam_counts}")
    print(f"  RED-outlined block(s) = sector_retile-touched (the desert BODY): {RETILE_TOUCHED}")
    path = OUT_DIR / "rung_d_eye_wide_planview.png"
    img.save(path)
    print(f"-> {path}  ({img.width}x{img.height})")
    return path, fam_counts


def render_boundary_zoom():
    print("\n" + "=" * 100)
    print("2. BOUNDARY ZOOM -- the retiled body blocks + ring, close-range plan + decal texture strip")
    print("=" * 100)
    core = RETILE_TOUCHED
    ring = sorted({(bx + dx, by + dy) for (bx, by) in core for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  if 0 <= bx + dx < 24 and 0 <= by + dy < 20})
    tris, bms, src = load_tris_mixed(ring, must_have_mint=core)

    def extra(d, px):
        pa, pb = px(*TERM_A), px(*TERM_B)
        d.line([pa, pb], fill=(255, 255, 255), width=1)

    img, fam_counts, px = _plan(tris, ring, core, extra_draw=extra, scale=9)
    strip_tris = [t for t in tris if t["fam"] == "strip" and t["block"] in core]
    print(f"  {len(tris)} tris in ring; {len(strip_tris)} STRIPS-style decal tri(s) in body blocks {core}")
    print(f"  body-block family counts: {fam_counts}")
    plan_path = OUT_DIR / "rung_d_eye_boundary_zoom_plan.png"
    img.save(plan_path)
    print(f"-> {plan_path}  ({img.width}x{img.height})")

    atlas = A.load_atlas(part="terrain", game=GAME_ROOT, source="engine")
    strip_tris.sort(key=lambda t: t["c"][1])
    crops = []
    for t in strip_tris:
        crop = A.crop_tile(atlas, t["uv"], pad=1).resize((96, 96), Image.NEAREST)
        crops.append(label(crop, f"z={t['c'][1]:.0f} topo{t['topo']}", h=14))
    if crops:
        def hcat(imgs, pad=4, bg=(18, 18, 18)):
            h = max(i.height for i in imgs)
            w = sum(i.width for i in imgs) + pad * (len(imgs) - 1)
            out = Image.new("RGB", (w, h), bg)
            x = 0
            for i in imgs:
                out.paste(i, (x, 0)); x += i.width + pad
            return out

        def vcat(imgs, pad=4, bg=(18, 18, 18)):
            w = max(i.width for i in imgs)
            h = sum(i.height for i in imgs) + pad * (len(imgs) - 1)
            out = Image.new("RGB", (w, h), bg)
            y = 0
            for i in imgs:
                out.paste(i, (0, y)); y += i.height + pad
            return out
        rows = [hcat(crops[i:i + 10]) for i in range(0, len(crops), 10)]
        sheet = vcat(rows)
    else:
        sheet = Image.new("RGB", (400, 60), (60, 0, 0))
        d2 = ImageDraw.Draw(sheet)
        d2.text((5, 5), "NO STRIPS-style decal tris found in body blocks", fill=(255, 255, 255))
    strip_path = OUT_DIR / "rung_d_eye_boundary_zoom_decals.png"
    sheet.save(strip_path)
    print(f"-> {strip_path}  ({sheet.width}x{sheet.height})")
    return plan_path, strip_path, dict(n_strip_tris=len(strip_tris))


def render_termini_feet():
    print("\n" + "=" * 100)
    print("3. TERMINI-FOOT SEAMS -- both line terminations at close range")
    print("=" * 100)
    paths = []
    for label_, (acx, acz) in (("A", TERM_A), ("B", TERM_B)):
        radius = 30
        ring = sorted({(bx + dx, by + dy) for (bx, by) in MASSIF_BLOCKS + RETILE_TOUCHED
                      for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                      if 0 <= bx + dx < 24 and 0 <= by + dy < 20})
        tris, bms, src = load_tris_mixed(ring)
        near = [t for t in tris if abs(t["c"][0] - acx) < radius and abs(t["c"][1] - acz) < radius]
        if not near:
            print(f"  {label_}: NO tris found near terminus -- skipping")
            continue

        def extra(d, px, acx=acx, acz=acz):
            p = px(acx, acz)
            d.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], outline=(0, 200, 255), width=3)
            pa, pb = px(*TERM_A), px(*TERM_B)
            d.line([pa, pb], fill=(255, 255, 255), width=1)

        img, fam_here, px = _plan(near, ring, FOOTPRINT, extra_draw=extra, scale=6)
        print(f"  terminus {label_}: {len(near)} tris near center, family mix {fam_here}")
        path = OUT_DIR / f"rung_d_eye_terminus_{label_}.png"
        img.save(path)
        print(f"  -> {path}  ({img.width}x{img.height})")
        paths.append(str(path))
    return paths


def render_stock_horseshoe_ab():
    print("\n" + "=" * 100)
    print("4. STOCK HORSESHOE A/B -- the real Daguerreo donor (5-6,15-16), same render recipe")
    print("=" * 100)
    core = DONOR_BLOCKS
    ring = sorted({(bx + dx, by + dy) for (bx, by) in core for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  if 0 <= bx + dx < 24 and 0 <= by + dy < 20})
    tris, bms, src = load_tris_mixed(ring)
    img, fam_counts, px = _plan(tris, ring, core)
    print(f"  {len(tris)} tris; family counts: {fam_counts}")
    path = OUT_DIR / "rung_d_eye_stock_horseshoe_AB.png"
    img.save(path)
    print(f"-> {path}  ({img.width}x{img.height})")
    return path, fam_counts


def render_stock_gd_ab():
    print("\n" + "=" * 100)
    print("5. STOCK GRASS|DESERT A/B -- the real cluster (13-15,11-12), same recipe as Rung C's comparator")
    print("=" * 100)
    core = [(13, 11), (13, 12), (14, 11), (14, 12), (15, 11), (15, 12)]
    ring = sorted({(bx + dx, by + dy) for (bx, by) in core for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  if 0 <= bx + dx < 24 and 0 <= by + dy < 20})
    tris, bms, src = load_tris_mixed(ring)
    img, fam_counts, px = _plan(tris, ring, core)
    strip_n = fam_counts.get("strip", 0)
    print(f"  {len(tris)} tris; family counts: {fam_counts}; {strip_n} STRIPS-style decal tris")
    path = OUT_DIR / "rung_d_eye_stock_gd_AB.png"
    img.save(path)
    print(f"-> {path}  ({img.width}x{img.height})")
    return path, fam_counts


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not MINT_ROOT.is_dir():
        sys.exit(f"no dry-run file set at {MINT_ROOT} -- run rung_d_build.py first")
    p1, fam1 = render_wide()
    p2a, p2b, boundary_stats = render_boundary_zoom()
    p3 = render_termini_feet()
    p4, fam4 = render_stock_horseshoe_ab()
    p5, fam5 = render_stock_gd_ab()
    report = dict(wide=str(p1), wide_fam_counts=fam1, boundary_plan=str(p2a), boundary_decals=str(p2b),
                 boundary_stats=boundary_stats, termini_feet=p3,
                 stock_horseshoe_ab=str(p4), stock_horseshoe_fam_counts=fam4,
                 stock_gd_ab=str(p5), stock_gd_fam_counts=fam5)
    (OUT_DIR / "rung_d_eye_review.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\n-> {OUT_DIR / 'rung_d_eye_review.json'}")


if __name__ == "__main__":
    main()
