"""Overlay the 24x20 block grid + object-block marks on the stock world-map art."""
import sys
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/gui-workspace-improvements-277c74/ff9mapkit")
from PIL import Image, ImageDraw
from ff9mapkit.world import extract as X
from ff9mapkit.world import navimap as NM
from ff9mapkit import config
SP = Path(__file__).resolve().parent
gp = Path(config.find_game_path(None))
cands = [gp / NM.MAP_SPRITE_REL, gp / NM.MAP_SPRITE_REL.replace("ui/sprites","UI/Sprites")]
src = None
for c in cands:
    if c.is_file(): src = c; break
if src is None:
    # try the extracted embedded asset elsewhere
    hits = list(gp.rglob("world_map_full_all.png"))
    print("rglob hits:", hits[:5])
    src = hits[0] if hits else None
print("map art:", src)
im = Image.open(src).convert("RGBA")
print("size", im.size)
fx,fy,fw,fh = NM.WORLD_MAP_ART_FRAME
X0,Y0 = fx*im.width, fy*im.height
W,H = fw*im.width, fh*im.height
sc = 2
im = im.resize((im.width*sc, im.height*sc), Image.LANCZOS)
X0,Y0,W,H = X0*sc, Y0*sc, W*sc, H*sc
d = ImageDraw.Draw(im)
objb = set(X.list_object_blocks(disc=1))
land = set(X.list_blocks(disc=1))
for bx in range(24):
    for by in range(20):
        x0 = X0 + W*bx/24.0; x1 = X0 + W*(bx+1)/24.0
        y0 = Y0 + H*by/20.0; y1 = Y0 + H*(by+1)/20.0
        col = (60,60,60,120)
        d.rectangle([x0,y0,x1,y1], outline=col)
        if (bx,by) in objb:
            d.rectangle([x0+1,y0+1,x1-1,y1-1], outline=(255,60,60,255), width=3)
            d.text((x0+3,y0+2), f"{bx},{by}", fill=(255,255,0,255))
        elif (bx,by) in land:
            d.text((x0+3,y0+2), f"{bx},{by}", fill=(120,200,255,200))
im.convert("RGB").save(SP/"mapgrid.png")
print("wrote", SP/"mapgrid.png", im.size)
im.crop((int(X0),int(Y0),int(X0+W),int(Y0+H))).convert("RGB").save(SP/"mapgrid_crop.png")
