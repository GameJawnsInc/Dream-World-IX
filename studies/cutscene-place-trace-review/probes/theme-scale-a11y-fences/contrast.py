from PIL import Image
import sys
B="C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/tools/scroll_out/gui_snaps/review-ctp/"
def lum(c):
    def ch(v):
        v/=255; return v/12.92 if v<=0.03928 else ((v+0.055)/1.055)**2.4
    r,g,b=c[:3]; return 0.2126*ch(r)+0.7152*ch(g)+0.0722*ch(b)
def cr(a,b):
    la,lb=sorted([lum(a),lum(b)],reverse=True); return (la+0.05)/(lb+0.05)
def hx(s): s=s.lstrip('#'); return tuple(int(s[i:i+2],16) for i in (0,2,4))
im=Image.open(B+"light-100/trace-contacts-canvas_light_100.png").convert("RGB")
W,H=im.size; print(W,H)
# sample art grounds: tan floor, navy wall, sky, pillar
sc=W/2000
for name,(x,y) in {"tan":(900,550),"navy_floor":(650,500),"sky":(700,150),"pillar":(1080,500),"cube":(1080,270)}.items():
    print(name, im.getpixel((int(x*sc),int(y*sc))))
from ff9mapkit.editor import theme
grounds={"tan":(158,132,96),"navy":(38,42,58),"sky":(52,56,76),"cube":(148,150,160)}
for n in ('LIGHT','DARK','MIST','DRACULA'):
    p=theme.derive(dict(getattr(theme,n)))
    for tok in ('text','muted','accent','warn','error'):
        print(n,tok,p[tok]," ".join(f"{g}={cr(hx(p[tok]),c):.2f}" for g,c in grounds.items()))
