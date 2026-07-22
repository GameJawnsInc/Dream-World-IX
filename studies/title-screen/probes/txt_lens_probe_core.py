"""TXT LENS: scan the CORE (non-fieldmap) FF9 bundles for title/localization UI."""
import os, time, glob
import UnityPy

SA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\StreamingAssets"
NEEDLES = ["title", "localiz", "menu", "system.txt", "/text/"]
# core bundles: the small-index ones (2,3,4,5,7) + any not matching fieldmap pattern
core = [os.path.join(SA, f) for f in
        ("p0data2.bin","p0data3.bin","p0data4.bin","p0data5.bin","p0data7.bin",
         "p0data6.bin","p0data61.bin","p0data62.bin","p0data63.bin")]
core = [c for c in core if os.path.exists(c)]
DEADLINE = time.time() + 110
for b in core:
    if time.time() > DEADLINE:
        print("TIME BUDGET HIT"); break
    try:
        env = UnityPy.load(b)
        cont = env.container
    except Exception as e:
        print(f"  !{os.path.basename(b)}: {e}"); continue
    keys = list(cont.keys())
    print(f"--- {os.path.basename(b)}: {len(keys)} containers; sample: {keys[:3]}")
    for path, obj in cont.items():
        pl = path.lower()
        if any(nd in pl for nd in NEEDLES):
            try: t = obj.type.name
            except Exception: t = "?"
            extra = ""
            if t in ("Texture2D","Sprite"):
                try:
                    d = obj.read()
                    w = getattr(d,"m_Width",getattr(d,"width","?")); h = getattr(d,"m_Height",getattr(d,"height","?"))
                    extra = f" {getattr(d,'m_Name',getattr(d,'name','?'))} {w}x{h}"
                except Exception as e: extra = f"(err {e})"
            print(f"   [{os.path.basename(b)}] {t}  {path}{extra}")
print("done")
