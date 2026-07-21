"""Regenerate the PRE(pre-fix)/POST(deployed) fringe witness renders after the fix is deployed:
PRE reads the pre-fix bytes from backups/dunes-fringe-fix.20260721, POST reads the live deployed
mod. (The in-line render in dunes_true_carry reads the LIVE deploy for PRE, so once the fix ships it
can no longer witness the 'before' -- this restores the witness from the preserved backup.)"""
import sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit")); sys.path.insert(0, str(HERE))
from ff9mapkit import config as _cfg
from ff9mapkit.world import mesh as MESH
import dunes_grazing_eye as GE
import dunes_true_carry as TC
from PIL import Image, ImageDraw

GP = Path(_cfg.find_game_path(None)); MOD = "FF9CustomMap-world"
BK = HERE.parents[1] / "backups" / "dunes-fringe-fix.20260721"
OUTD = HERE / "out"
BLOCK = 64.0


def tris_from(root, blocks):
    out = []
    for (bx, by) in blocks:
        p = Path(root) / MESH.override_relpath(1, bx, by, part="Terrain")
        if not p.exists():
            continue
        bm = MESH.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        out += GE._tris_of(bm, bx, by)
    return out


TOUCHED = [(18, 18), (19, 17), (19, 18), (19, 19), (20, 18)]
NEIGH = [b for b in GE.MINT_BLOCKS if b not in TOUCHED]
# PRE = pre-fix touched bytes (backup) + unchanged neighbours (live, byte-identical pre/post)
pre = tris_from(BK, TOUCHED) + tris_from(GP / MOD, NEIGH)
# POST = the live deployed full region (fixed)
post = tris_from(GP / MOD, GE.MINT_BLOCKS)

W, H = 900, 560
paths = []
for view in TC._fringe_cameras():
    cam, look, fov = view["cam"], view["look"], view["fov"]
    pre_img = GE.render_grazing(pre, cam, look, fov, W, H, shade=True)
    post_img = GE.render_grazing(post, cam, look, fov, W, H, shade=True)
    pad, lh = 8, 20
    sheet = Image.new("RGB", (W * 2 + pad * 3, H + lh + pad * 2 + 24), (16, 16, 16))
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 6), f"FRINGE WITNESS -- {view['cap']}. LEFT pre-fix (backup) / RIGHT deployed fix. "
                      f"Sky-blue through the terrain = a HOLE; bright green = a grass-ecotone shard "
                      f"(grass decal OR relocated desert-strip tile).",
            fill=(255, 230, 140))
    dr.text((pad, 24 + pad), "PRE -- pre-fix bytes (blue slivers + green shards)", fill=(220, 220, 220))
    dr.text((pad + W + pad, 24 + pad), "POST -- the deployed fix (seams closed, all green shards re-dressed)", fill=(220, 220, 220))
    sheet.paste(pre_img, (pad, 24 + pad + lh))
    sheet.paste(post_img, (pad + W + pad, 24 + pad + lh))
    p = OUTD / f"dunes_fringe_witness_{view['tag']}.png"
    sheet.save(p)
    paths.append(str(p))
    print(f"  -> {p}")
