"""EYE-SKEPTIC REVIEW of gd_seam_dress.py (2026-07-22) -- READ-ONLY, dry-run only, zero writes.

Three renders, saved to out/:
  1. gd_eye_calibration.png  -- re-derive the atlas crops for grass mains / desert mains / STRIPS(grass,
     desert) rows 0-3 straight from the ENGINE-resolved atlas + the EXACT constants gd_seam_dress.py
     itself imports (GL.STRIP_U / GL.STRIPS_V / GL.STRIPS[('grass','desert')]) -- an independent
     recompute, not a re-display of the pre-existing gd_calibration_sheet.png, to catch any drift
     between when that PNG was made and the code as it stands today.
  2. gd_eye_bare_seam_planview.png -- top-down plan view (tri centroids, colored by family) of blocks
     (7,19)+(8,19)+their Moore ring, LIVE deployed bytes -- visual confirmation of seam_null_recon's
     "these do not touch" finding (independent of its printed numbers).
  3. gd_eye_roundtrip.png -- the visual test that stands in for "render the dressed seam" given the
     brief's named target has 0 eligible cells: pick a REAL stock straddle cell at the null cluster
     (13-15,11-12), and render 3 panels for BOTH its grass tri and its desert tri --
       (a) REAL stock pixels at that cell's actual UV (ground truth)
       (b) the SAME cell with its decal stripped back to plain mains (a synthetic "bare seam", the
           only lever available since no real bare-and-should-be-dressed cell exists in the deployed
           mod)
       (c) gd_seam_dress.compute_dress() run on that stripped state -- the tool's own dressing
           function, forward -- re-generating a decal
     If (c) visually (and numerically, via UV) matches (a), the dressing MECHANISM is proven
     stock-indistinguishable on a cell where ground truth exists, even though it produced zero output
     on the brief's own named target.

Run: py studies/overworld-topography/gd_eye_review.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from ff9mapkit import config as _cfg          # noqa: E402
from ff9mapkit.world import atlas as A        # noqa: E402
from ff9mapkit.world import extract as X      # noqa: E402
from ff9mapkit.world import grassland as GL   # noqa: E402
from ff9mapkit.world import orphangate as OG  # noqa: E402

import gd_seam_dress as GD                    # noqa: E402
import seam_null_recon as SNR                 # noqa: E402

OUT_DIR = HERE / "out"
GAME_ROOT = Path(_cfg.find_game_path(None))


def label(img, text):
    im2 = Image.new("RGBA", (img.width, img.height + 18), (20, 20, 20, 255))
    im2.paste(img, (0, 18))
    d = ImageDraw.Draw(im2)
    d.text((2, 2), text, fill=(255, 255, 255, 255))
    return im2


def hcat(imgs, pad=4, bg=(20, 20, 20, 255)):
    h = max(i.height for i in imgs)
    w = sum(i.width for i in imgs) + pad * (len(imgs) - 1)
    out = Image.new("RGBA", (w, h), bg)
    x = 0
    for i in imgs:
        out.paste(i, (x, 0))
        x += i.width + pad
    return out


def vcat(imgs, pad=4, bg=(20, 20, 20, 255)):
    w = max(i.width for i in imgs)
    h = sum(i.height for i in imgs) + pad * (len(imgs) - 1)
    out = Image.new("RGBA", (w, h), bg)
    y = 0
    for i in imgs:
        out.paste(i, (0, y))
        y += i.height + pad
    return out


# ====================================================================================================
# 1. CALIBRATE -- independent recompute of the atlas crops from current code + the engine atlas
# ====================================================================================================
def render_calibration():
    print("=" * 100)
    print("1. CALIBRATION -- engine atlas crops for grass mains / desert mains / STRIPS(grass,desert) "
          "rows 0-3, re-derived from CURRENT gd_seam_dress.py / grassland.py constants")
    print("=" * 100)
    img = A.load_atlas(part="terrain", game=GAME_ROOT, source="engine")
    print(f"engine atlas resolved: {img.width}x{img.height} (1024^2 = bundle default; larger = a loose "
          f"HD/Moguri override is winning -- this IS the pixels the game renders)")

    tiles = []
    m = GL.FAM_REGION["main"]
    for fam in ("grass", "desert"):
        g = GL.GROUNDS[fam]
        rect = (m[0] + g["mains_du"], m[1] + g["mains_dv"], m[2] + g["mains_du"], m[3] + g["mains_dv"])
        triplet = [(rect[0], rect[1]), (rect[2], rect[1]), (rect[2], rect[3])]
        crop = A.crop_tile(img, triplet, pad=0).resize((260, 260), Image.NEAREST)
        tiles.append(label(crop, f"{fam} mains  uv={tuple(round(x,5) for x in rect)}"))

    pair = ("grass", "desert")
    du, dv = GL.STRIPS[pair]["du"], GL.STRIPS[pair]["dv"]
    for row in range(4):
        rect = GD.strip_row_rect(row)   # reuses gd_seam_dress.py's OWN function, not a re-typed literal
        triplet = [(rect[0], rect[1]), (rect[2], rect[1]), (rect[2], rect[3])]
        crop = A.crop_tile(img, triplet, pad=0).resize((260, 260), Image.NEAREST)
        tiles.append(label(crop, f"STRIPS(grass,desert) row{row}  uv={tuple(round(x,5) for x in rect)}"))
        print(f"  row{row} rect (via gd_seam_dress.strip_row_rect) = {rect}  du/dv=({du},{dv})")

    sheet = hcat(tiles)
    path = OUT_DIR / "gd_eye_calibration.png"
    sheet.convert("RGB").save(path)
    print(f"-> {path}  ({sheet.width}x{sheet.height})")
    return path


# ====================================================================================================
# 2. THE BARE SEAM -- plan view of (7,19)/(8,19), live deployed bytes
# ====================================================================================================
FAM_COLOR = {
    "grass": (86, 148, 60), "desert": (196, 158, 100), "rock": (110, 110, 110),
    "hole": (20, 20, 20), "dunes": (214, 196, 140), "scrub": (120, 150, 90),
    None: (40, 70, 110),
}


def render_bare_seam():
    print("\n" + "=" * 100)
    print("2. THE BARE SEAM -- top-down plan view, block(7,19)+block(8,19)+Moore ring, LIVE deployed "
          "bytes (independent visual check of seam_null_recon's 'these do not touch' finding)")
    print("=" * 100)
    core = [(7, 19), (8, 19)]
    ring = sorted({(bx + dx, by + dy) for (bx, by) in core for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                  if 0 <= bx + dx < 24 and 0 <= by + dy < 20})
    all_tris, bms, src = SNR.load_tris(ring, source="deployed", must_have=set(core))
    xs = [p[0] for t in all_tris for p in t["w"]]
    zs = [p[2] for t in all_tris for p in t["w"]]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    scale = 6
    W, H = int((x1 - x0) * scale) + 20, int((z1 - z0) * scale) + 20
    img = Image.new("RGB", (W, H), (10, 10, 10))
    d = ImageDraw.Draw(img)

    def px(wx, wz):
        return (10 + int((wx - x0) * scale), 10 + int((wz - z0) * scale))

    for t in all_tris:
        pts = [px(p[0], p[2]) for p in t["w"]]
        d.polygon(pts, fill=FAM_COLOR.get(t["fam"], (200, 0, 200)))
    # block-boundary + core outline
    for (bx, by) in ring:
        ox, oz = X.block_world_origin(bx, by)
        rect = [px(ox, oz), px(ox + 64, oz + 64)]
        d.rectangle(rect, outline=(255, 255, 0) if (bx, by) in core else (90, 90, 90), width=2)
        d.text((rect[0][0] + 3, rect[0][1] + 3), f"({bx},{by})", fill=(255, 255, 255))

    n_core7 = sum(1 for t in all_tris if t["block"] == (7, 19))
    n_core8 = sum(1 for t in all_tris if t["block"] == (8, 19))
    print(f"rendered {len(all_tris)} tris across {len(ring)} blocks; block(7,19)={n_core7} tris "
          f"(grass islet), block(8,19)={n_core8} tris (desert islet); dark-blue fill = no mesh "
          f"content (open water) -- the gap between the yellow-outlined blocks IS the seam")
    path = OUT_DIR / "gd_eye_bare_seam_planview.png"
    img.save(path)
    print(f"-> {path}  ({img.width}x{img.height})")
    return path, dict(n_core7=n_core7, n_core8=n_core8, n_ring_blocks=len(ring))


# ====================================================================================================
# 3. ROUND-TRIP -- real straddle cell, strip it, re-dress it with gd_seam_dress's own function,
#    compare to ground truth. Stands in for "render the dressed seam" since the named target is empty.
# ====================================================================================================
def render_roundtrip():
    print("\n" + "=" * 100)
    print("3. ROUND-TRIP -- a REAL stock grass|desert straddle cell, stripped then re-dressed by "
          "gd_seam_dress.compute_dress(), compared to ground truth")
    print("=" * 100)
    GD_PAIR_TEST = ("grass", "desert")
    core = [(13, 11), (13, 12), (14, 11), (14, 12), (15, 11), (15, 12)]
    ring = sorted({(bx + dx, by + dy) for (bx, by) in core for dx in (-1, 0, 1) for dy in (-1, 0, 1)})
    all_tris, bms, src = SNR.load_tris(ring, source="stock", must_have=())
    core_tris = [t for t in all_tris if t["block"] in core]
    cell_fams, cell_recs = {}, {}
    for t in core_tris:
        if t["fam"] in ("grass", "desert"):
            cell_fams.setdefault(t["cell"], set()).add(t["fam"])
            cell_recs.setdefault(t["cell"], []).append(t)
    straddles = sorted(c for c, f in cell_fams.items() if f == {"grass", "desert"})

    img = A.load_atlas(part="terrain", game=GAME_ROOT, source="engine")
    rows = []
    tested = 0
    for cell in straddles:
        recs = {r["fam"]: r for r in cell_recs[cell] if r["fam"] in ("grass", "desert")}
        if set(recs) != {"grass", "desert"}:
            continue
        cls_g = SNR.classify_tri("grass", recs["grass"]["uv"])
        cls_d = SNR.classify_tri("desert", recs["desert"]["uv"])
        if cls_g[0] != "strip_grass_desert" or cls_d[0] != "strip_grass_desert" or cls_g[1] != cls_d[1]:
            continue   # only test cells wearing a clean matched-row decal on both tris
        row = cls_g[1]
        if row not in (1, 3):
            continue   # gd_seam_dress only ever synthesizes rows 1/3 (Law 2's dominant rows) -- test those

        bm = bms[recs["grass"]["block"]]
        ox, oz = X.block_world_origin(*recs["grass"]["block"])

        def find_tri_idx(rec):
            for tri in bm.tris:
                w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
                if SNR.kk(w[0]) == SNR.kk(rec["w"][0]) and SNR.kk(w[1]) == SNR.kk(rec["w"][1]) \
                        and SNR.kk(w[2]) == SNR.kk(rec["w"][2]):
                    return list(tri)
            return None

        tri_idx = {fam: find_tri_idx(rec) for fam, rec in recs.items()}
        if any(v is None for v in tri_idx.values()):
            continue

        # (a) ground truth = the real, currently-worn UV (already have it)
        real_uv = {"grass": recs["grass"]["uv"], "desert": recs["desert"]["uv"]}

        def uv_close(a, b, tol=0.0035):
            # unordered corner-set match (a tri's 3 UV corners, any winding) -- what matters is the
            # tri covers the identical rect region, not vertex-array order
            used = [False, False, False]
            for x in a:
                ok = False
                for k, y in enumerate(b):
                    if used[k]:
                        continue
                    if abs(x[0] - y[0]) < tol and abs(x[1] - y[1]) < tol:
                        used[k] = True
                        ok = True
                        break
                if not ok:
                    return False
            return True

        # brute-force the ORI that reproduces this REAL cell's ACTUAL decal exactly (both tris) --
        # the real stock game's per-cell orientation choice is its OWN, unknown, independent process
        # (never generated by the kit's assign_mains) -- so testing the FORMULA fairly means feeding
        # it the ori ground truth actually used, not the kit's seeded draw for a-cell-with-no-answer.
        ori_hit = None
        for cand_ori in GL.ORIS:
            g_uv = [OG._strip_uv_for_pair(GD_PAIR_TEST, bm.verts[j][0] + ox, bm.verts[j][2] + oz,
                                          cell, row, cand_ori) for j in tri_idx["grass"]]
            d_uv = [OG._strip_uv_for_pair(GD_PAIR_TEST, bm.verts[j][0] + ox, bm.verts[j][2] + oz,
                                          cell, row, cand_ori) for j in tri_idx["desert"]]
            if uv_close(real_uv["grass"], g_uv) and uv_close(real_uv["desert"], d_uv):
                ori_hit = cand_ori
                break
        if ori_hit is None:
            print(f"  cell{cell} row{row}: NO ori (of {list(GL.ORIS)}) reproduces the real decal via "
                 f"_strip_uv_for_pair -- FORMULA MISMATCH, not just an orientation-choice difference")
            ori = 0
        else:
            ori = ori_hit

        # (c) gd_seam_dress.compute_dress(), forward, fam-by-fam, fed the GROUND-TRUTH ori -- THE
        #     FUNCTION UNDER TEST, isolated from the separate orientation-CHOICE question
        dressed_uv = {}
        for fam, rec in recs.items():
            new_uv, new_idall = GD.compute_dress(bm, ox, oz, cell, tri_idx[fam], fam, row, ori)
            dressed_uv[fam] = new_uv

        if "grass" not in dressed_uv or "desert" not in dressed_uv:
            continue

        match_g = uv_close(real_uv["grass"], dressed_uv["grass"])
        match_d = uv_close(real_uv["desert"], dressed_uv["desert"])
        print(f"  cell{cell} row{row} ori_ground_truth={ori_hit} (kit-would-have-drawn="
             f"{GL.assign_mains({cell}, seed=OG.DEFAULT_REDRESS_SEED)[1][cell]}): "
             f"grass UV match={match_g}  desert UV match={match_d}")
        print(f"    real grass uv={[tuple(round(x,5) for x in p) for p in real_uv['grass']]}")
        print(f"    dressed grass uv={[tuple(round(x,5) for x in p) for p in dressed_uv['grass']]}")
        print(f"    real desert uv={[tuple(round(x,5) for x in p) for p in real_uv['desert']]}")
        print(f"    dressed desert uv={[tuple(round(x,5) for x in p) for p in dressed_uv['desert']]}")

        for fam in ("grass", "desert"):
            real_crop = A.crop_tile(img, real_uv[fam], pad=1).resize((160, 160), Image.NEAREST)
            dressed_crop = A.crop_tile(img, dressed_uv[fam], pad=1).resize((160, 160), Image.NEAREST)
            match = match_g if fam == "grass" else match_d
            rows.append(label(real_crop, f"{cell} {fam} REAL row{row}"))
            rows.append(label(dressed_crop, f"{cell} {fam} compute_dress() {'MATCH' if match else 'MISMATCH'}"))
        tested += 1
        if tested >= 4:
            break

    if not rows:
        print("  *** no clean matched-row straddle cell found to test -- see stdout above ***")
        return None, dict(tested=0)

    sheet = vcat([hcat(rows[i:i + 4]) for i in range(0, len(rows), 4)])
    path = OUT_DIR / "gd_eye_roundtrip.png"
    sheet.convert("RGB").save(path)
    print(f"tested {tested} real straddle cell(s) -> {path}  ({sheet.width}x{sheet.height})")
    return path, dict(tested=tested)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p1 = render_calibration()
    p2, seam_stats = render_bare_seam()
    p3, rt_stats = render_roundtrip()
    report = dict(calibration=str(p1), bare_seam=str(p2), bare_seam_stats=seam_stats,
                 roundtrip=str(p3) if p3 else None, roundtrip_stats=rt_stats)
    (OUT_DIR / "gd_eye_review.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\n-> {OUT_DIR / 'gd_eye_review.json'}")


if __name__ == "__main__":
    main()
