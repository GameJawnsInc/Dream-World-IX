"""
TXT LENS probe: find title-menu button sprites + embedded Localization.txt
across FF9 p0data bundles. Container-path scan only (lazy) -- no bulk extract.

Usage: py txt_lens_probe_title_menu_assets.py [substr ...]
"""
import sys, os, time, glob
import UnityPy

SA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\StreamingAssets"
NEEDLES = [s.lower() for s in (sys.argv[1:] or [
    "title_menu", "manifest/text/localization",
    "menu_newgame", "menu_continue", "menu_load", "menu_cloud",
])]

bundles = sorted(glob.glob(os.path.join(SA, "p0data*.bin")))
print(f"scanning {len(bundles)} bundles for {NEEDLES}")
DEADLINE = time.time() + 110
hits = 0
for b in bundles:
    if time.time() > DEADLINE:
        print("TIME BUDGET HIT, stopping"); break
    try:
        env = UnityPy.load(b)
        cont = env.container
    except Exception as e:
        print(f"  !{os.path.basename(b)}: {e}"); continue
    for path, obj in cont.items():
        pl = path.lower()
        if any(n in pl for n in NEEDLES):
            hits += 1
            try: t = obj.type.name
            except Exception: t = "?"
            extra = ""
            if t in ("Texture2D", "Sprite", "TextAsset"):
                try:
                    d = obj.read()
                    if t == "TextAsset":
                        raw = d.m_Script if hasattr(d, "m_Script") else getattr(d, "text", "")
                        extra = f" len={len(raw)}"
                    else:
                        w = getattr(d, "m_Width", getattr(d, "width", "?"))
                        h = getattr(d, "m_Height", getattr(d, "height", "?"))
                        extra = f" name={getattr(d,'m_Name',getattr(d,'name','?'))} {w}x{h}"
                except Exception as e:
                    extra = f" (read err {e})"
            print(f"[{os.path.basename(b)}] {t}  {path}{extra}")
print(f"done, {hits} hits")
