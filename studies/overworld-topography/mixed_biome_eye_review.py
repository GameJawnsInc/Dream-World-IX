"""EYE-SKEPTIC REVIEW of mixed_biome_mint.py's DRY-RUN output (2026-07-22) -- READ-ONLY, zero writes.

Loads the would-be-deployed file set from out/mixed_biome_mint/FF9CustomMap-world/... (never the game
install) + real stock ring/A-B-comparison blocks, and renders:

  1. mixed_eye_wide_planview.png   -- the whole 17-block mint, family-colored, anchors + partition
     line overlaid.
  2. mixed_eye_boundary_zoom.png   -- block (2,17) (the ONLY block the sector retile actually touched),
     grazing-close family-colored plan + a texture-crop strip of the actual dressed decals along the
     line.
  3. mixed_eye_anchor_feet.png     -- both anchor terminations (where the desert corridor is supposed
     to meet each carved-rock massif) at close range -- the graveyard's "anchor-foot seam" failure mode.
  4. mixed_eye_stock_AB.png        -- the real stock grass|desert cluster (13-15,11-12), same render
     recipe, for direct A/B.

Run: py studies/overworld-topography/mixed_biome_eye_review.py
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

OUT_DIR = HERE / "out" / "mixed_biome_mint" / "renders"
MINT_ROOT = HERE / "out" / "mixed_biome_mint" / "FF9CustomMap-world"
GAME_ROOT = Path(_cfg.find_game_path(None))
MOD = "FF9CustomMap-world"

REPORT = json.loads((HERE / "out" / "mixed_biome_mint.json").read_text(encoding="utf-8"))
FOOTPRINT = [tuple(b) for b in REPORT["footprint_blocks"]]
ANCHORS = REPORT["anchors"]
LINE_EP = REPORT["partition_line"]["endpoints"]
RETILE_TOUCHED = [tuple(b) for b in REPORT["sector_retile"]["touched_blocks"]]

FAM_COLOR = {
    "grass": (86, 148, 60), "desert": (196, 158, 100), "rock": (120, 110, 100),
    "hole": (20, 20, 20), "dunes": (214, 196, 140), "scrub": (120, 150, 90),
    "strip": (230, 60, 200),               # any STRIPS(grass,desert) decal tri -- always flagged bright
    None: (35, 60, 100),
}
ROCK_TOPOS = {49, 7, 62, 58}


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


# ====================================================================================================
# tri classification + loading (mint dry-run files for footprint, stock for everything else)
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


def load_tris_mixed(blocks, *, must_have_mint=()):
    """Like seam_null_recon.load_tris, but footprint blocks read from the MINT DRY-RUN file set
    (out/mixed_biome_mint/FF9CustomMap-world/...) instead of the game install; non-footprint (ring /
    comparison) blocks read real stock bytes. Zero reads/writes against the live game MOD folder."""
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
            src_by_block[(bx, by)] = "mint-dry-run"
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


# ====================================================================================================
# 1. WIDE PLAN VIEW -- the whole mint
# ====================================================================================================
def render_wide():
    print("=" * 100)
    print("1. WIDE PLAN VIEW -- the full 17-block mint (mint dry-run bytes) + 1-block ring (stock)")
    print("=" * 100)
    ring = sorted({(bx + dx, by + dy) for (bx, by) in FOOTPRINT for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  if 0 <= bx + dx < 24 and 0 <= by + dy < 20})
    tris, bms, src = load_tris_mixed(ring, must_have_mint=FOOTPRINT)
    xs = [p[0] for t in tris for p in t["w"]]
    zs = [p[2] for t in tris for p in t["w"]]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    scale = 3.2
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
        d.rectangle(rect, outline=(255, 255, 0) if (bx, by) in FOOTPRINT else (70, 70, 70), width=2)
        d.text((rect[0][0] + 3, rect[0][1] + 3), f"({bx},{by})", fill=(255, 255, 255))
        if (bx, by) in RETILE_TOUCHED:
            d.rectangle(rect, outline=(255, 40, 40), width=3)

    for a in ANCHORS:
        acx, acz = a["realized_center"]
        p = px(acx, acz)
        d.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], outline=(0, 200, 255), width=3)
        d.text((p[0] + 8, p[1] - 8), a["label"] + f" clr={a['clear_radius']}u", fill=(0, 200, 255))
        clr_px = int(a["clear_radius"] * scale)
        d.ellipse([p[0] - clr_px, p[1] - clr_px, p[0] + clr_px, p[1] + clr_px], outline=(0, 140, 180), width=1)

    line_pts = [px(x, z) for (x, z) in LINE_EP]
    d.line(line_pts, fill=(255, 255, 255), width=1)
    for (x, z) in LINE_EP:
        p = px(x, z)
        d.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], outline=(255, 255, 255), width=2)

    print(f"  {len(tris)} tris; family counts: {fam_counts}")
    print(f"  RED-outlined block(s) = where sector_retile actually landed desert tris: {RETILE_TOUCHED}")
    path = OUT_DIR / "mixed_eye_wide_planview.png"
    img.save(path)
    print(f"-> {path}  ({img.width}x{img.height})")
    return path, fam_counts


# ====================================================================================================
# 2. BOUNDARY ZOOM -- block (2,17), the only retiled block -- plan + a texture-crop strip
# ====================================================================================================
def render_boundary_zoom():
    print("\n" + "=" * 100)
    print("2. BOUNDARY ZOOM -- block(2,17) + its ring, close-range plan + decal texture strip")
    print("=" * 100)
    core = RETILE_TOUCHED
    ring = sorted({(bx + dx, by + dy) for (bx, by) in core for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  if 0 <= bx + dx < 24 and 0 <= by + dy < 20})
    tris, bms, src = load_tris_mixed(ring, must_have_mint=core)
    xs = [p[0] for t in tris for p in t["w"]]
    zs = [p[2] for t in tris for p in t["w"]]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    scale = 9
    W, H = int((x1 - x0) * scale) + 30, int((z1 - z0) * scale) + 30
    img = Image.new("RGB", (W, H), (10, 10, 10))
    d = ImageDraw.Draw(img)

    def px(wx, wz):
        return (15 + int((wx - x0) * scale), 15 + int((wz - z0) * scale))

    strip_tris = []
    for t in tris:
        pts = [px(p[0], p[2]) for p in t["w"]]
        d.polygon(pts, fill=FAM_COLOR.get(t["fam"], (200, 0, 200)))
        if t["fam"] == "strip" and t["block"] in core:
            strip_tris.append(t)
    for (bx, by) in ring:
        ox, oz = X.block_world_origin(bx, by)
        rect = [px(ox, oz - 64), px(ox + 64, oz)]
        d.rectangle(rect, outline=(255, 255, 0) if (bx, by) in core else (70, 70, 70), width=2)
        d.text((rect[0][0] + 3, rect[0][1] + 3), f"({bx},{by})", fill=(255, 255, 255))
    for cell in range(0, 65, 4):
        pass  # (grid lines skipped -- keep the sheet legible)
    line_pts = [px(x, z) for (x, z) in LINE_EP]
    d.line(line_pts, fill=(255, 255, 255), width=1)

    print(f"  {len(tris)} tris in ring; {len(strip_tris)} STRIPS(grass,desert) decal tri(s) landed in "
          f"core block {core}")
    plan_path = OUT_DIR / "mixed_eye_boundary_zoom_plan.png"
    img.save(plan_path)
    print(f"-> {plan_path}  ({img.width}x{img.height})")

    # texture-crop strip of every dressed decal tri in the core block, ordered by world-Z (walk the
    # seam top to bottom) -- the castellation/repetition hunt
    atlas = A.load_atlas(part="terrain", game=GAME_ROOT, source="engine")
    strip_tris.sort(key=lambda t: t["c"][1])
    crops = []
    for t in strip_tris:
        crop = A.crop_tile(atlas, t["uv"], pad=1).resize((96, 96), Image.NEAREST)
        crops.append(label(crop, f"z={t['c'][1]:.0f} topo{t['topo']}", h=14))
    if crops:
        rows = [hcat(crops[i:i + 10]) for i in range(0, len(crops), 10)]
        sheet = vcat(rows)
    else:
        sheet = Image.new("RGB", (400, 60), (60, 0, 0))
        d2 = ImageDraw.Draw(sheet)
        d2.text((5, 5), "NO STRIPS(grass,desert) decal tris found in core block", fill=(255, 255, 255))
    strip_path = OUT_DIR / "mixed_eye_boundary_zoom_decals.png"
    sheet.save(strip_path)
    print(f"-> {strip_path}  ({sheet.width}x{sheet.height})")
    return plan_path, strip_path, dict(n_strip_tris=len(strip_tris))


# ====================================================================================================
# 3. ANCHOR-FOOT SEAMS -- both terminations, close range
# ====================================================================================================
def render_anchor_feet():
    print("\n" + "=" * 100)
    print("3. ANCHOR-FOOT SEAMS -- both terminations at close range")
    print("=" * 100)
    paths = []
    for a in ANCHORS:
        acx, acz = a["realized_center"]
        changed = [tuple(b) for b in a["report"]["blocks"]]
        ring = sorted({(bx + dx, by + dy) for (bx, by) in changed for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                      if 0 <= bx + dx < 24 and 0 <= by + dy < 20})
        tris, bms, src = load_tris_mixed(ring, must_have_mint=[b for b in changed if b in FOOTPRINT])
        radius = a["clear_radius"] + 20
        near = [t for t in tris if abs(t["c"][0] - acx) < radius and abs(t["c"][1] - acz) < radius]
        if not near:
            print(f"  {a['label']}: NO tris found near realized center -- skipping")
            continue
        xs = [p[0] for t in near for p in t["w"]]
        zs = [p[2] for t in near for p in t["w"]]
        x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
        scale = 5
        W, H = int((x1 - x0) * scale) + 30, int((z1 - z0) * scale) + 30
        img = Image.new("RGB", (W, H), (10, 10, 10))
        d = ImageDraw.Draw(img)

        def px(wx, wz):
            return (15 + int((wx - x0) * scale), 15 + int((wz - z0) * scale))

        fam_here = {}
        for t in near:
            pts = [px(p[0], p[2]) for p in t["w"]]
            d.polygon(pts, fill=FAM_COLOR.get(t["fam"], (200, 0, 200)))
            fam_here[t["fam"]] = fam_here.get(t["fam"], 0) + 1
        p = px(acx, acz)
        d.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], outline=(0, 200, 255), width=3)
        line_pts = [px(x, z) for (x, z) in LINE_EP]
        d.line(line_pts, fill=(255, 255, 255), width=1)
        print(f"  {a['label']}: {len(near)} tris near center, family mix {fam_here}")
        path = OUT_DIR / f"mixed_eye_anchor_foot_{a['label'].split()[0]}.png"
        img.save(path)
        print(f"  -> {path}  ({img.width}x{img.height})")
        paths.append(str(path))
    return paths


# ====================================================================================================
# 4. STOCK A/B -- the real cluster (13-15,11-12), same recipe
# ====================================================================================================
def render_stock_ab():
    print("\n" + "=" * 100)
    print("4. STOCK A/B -- the real grass|desert cluster (13-15,11-12), same render recipe")
    print("=" * 100)
    core = [(13, 11), (13, 12), (14, 11), (14, 12), (15, 11), (15, 12)]
    ring = sorted({(bx + dx, by + dy) for (bx, by) in core for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  if 0 <= bx + dx < 24 and 0 <= by + dy < 20})
    tris, bms, src = load_tris_mixed(ring)  # all stock (none in FOOTPRINT)
    xs = [p[0] for t in tris for p in t["w"]]
    zs = [p[2] for t in tris for p in t["w"]]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    scale = 3.2
    W, H = int((x1 - x0) * scale) + 30, int((z1 - z0) * scale) + 30
    img = Image.new("RGB", (W, H), (10, 10, 10))
    d = ImageDraw.Draw(img)

    def px(wx, wz):
        return (15 + int((wx - x0) * scale), 15 + int((wz - z0) * scale))

    fam_counts = {}
    strip_n = 0
    for t in tris:
        pts = [px(p[0], p[2]) for p in t["w"]]
        d.polygon(pts, fill=FAM_COLOR.get(t["fam"], (200, 0, 200)))
        fam_counts[t["fam"]] = fam_counts.get(t["fam"], 0) + 1
        if t["fam"] == "strip":
            strip_n += 1
    for (bx, by) in ring:
        ox, oz = X.block_world_origin(bx, by)
        rect = [px(ox, oz - 64), px(ox + 64, oz)]
        d.rectangle(rect, outline=(255, 255, 0) if (bx, by) in core else (70, 70, 70), width=2)
        d.text((rect[0][0] + 3, rect[0][1] + 3), f"({bx},{by})", fill=(255, 255, 255))
    print(f"  {len(tris)} tris; family counts: {fam_counts}; {strip_n} STRIPS(grass,desert) decal tris")
    path = OUT_DIR / "mixed_eye_stock_AB.png"
    img.save(path)
    print(f"-> {path}  ({img.width}x{img.height})")
    return path, fam_counts


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not MINT_ROOT.is_dir():
        sys.exit(f"no dry-run file set at {MINT_ROOT} -- run mixed_biome_mint.py first")
    p1, fam1 = render_wide()
    p2a, p2b, boundary_stats = render_boundary_zoom()
    p3 = render_anchor_feet()
    p4, fam4 = render_stock_ab()
    report = dict(wide=str(p1), wide_fam_counts=fam1, boundary_plan=str(p2a), boundary_decals=str(p2b),
                 boundary_stats=boundary_stats, anchor_feet=p3, stock_ab=str(p4), stock_ab_fam_counts=fam4)
    (OUT_DIR / "mixed_eye_review.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\n-> {OUT_DIR / 'mixed_eye_review.json'}")


if __name__ == "__main__":
    main()
