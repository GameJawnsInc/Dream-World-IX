import sys; sys.path.insert(0,"<SCRATCH>/review/theme-scale-a11y-fences")
from PIL import Image
def lum(c):
    def ch(v):
        v/=255; return v/12.92 if v<=0.03928 else ((v+0.055)/1.055)**2.4
    r,g,b=c[:3]; return 0.2126*ch(r)+0.7152*ch(g)+0.0722*ch(b)
def cr(a,b):
    la,lb=sorted([lum(a),lum(b)],reverse=True); return (la+0.05)/(lb+0.05)
B="C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/tools/scroll_out/gui_snaps/review-ctp/"
def box(path,x0,y0,x1,y1):
    im=Image.open(B+path).convert("RGB")
    px=[im.getpixel((x,y)) for x in range(x0,x1) for y in range(y0,y1)]
    from collections import Counter
    cnt=Counter(px)
    bg=cnt.most_common(1)[0][0]
    # glyph = pixel with max contrast vs bg
    best=max(cnt,key=lambda c:cr(c,bg))
    print(path,(x0,y0,x1,y1),"bg",bg,"ink",best,f"max={cr(best,bg):.2f}")
for a in sys.argv[1:]:
    p,*xs=a.split(":"); box(p,*map(int,xs))
