"""Find the Title scene level + the title_bg sprite name + logo atlas.
(a) read build-settings scene list from mainData/globalgamemanagers.
(b) per level: match GameObject names menupanel/logo/slideshow/title; dump Sprite/Tex names.
READ-ONLY. Run: py probe_title_level.py
"""
import os, glob
import UnityPy

DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"

# (a) build settings scene list
for cand in ("globalgamemanagers","mainData"):
    p=os.path.join(DATA,cand)
    if not os.path.exists(p): continue
    try:
        e=UnityPy.load(p)
        for obj in e.objects:
            if obj.type.name=="BuildSettings":
                d=obj.read_typetree()
                sc=d.get("scenes") or d.get("m_Scenes")
                print(f"==== BuildSettings in {cand}: scenes ====")
                for i,s in enumerate(sc or []): print(f"  level{i}: {s}")
    except Exception as ex:
        print(f"{cand}: {ex}")

# (b) per-level GameObject / sprite scan
GO_KEYS=("menupanel","logosprite","slideshow","titleimage","title")
levels=sorted(glob.glob(os.path.join(DATA,"level*")),
              key=lambda p:int(os.path.basename(p)[5:]) if os.path.basename(p)[5:].isdigit() else 999)
for lp in levels:
    try: e=UnityPy.load(lp)
    except Exception: continue
    gohits=[]; sprites=set(); texs=set()
    for obj in e.objects:
        tn=obj.type.name
        if tn=="GameObject":
            try:
                d=obj.read(); nm=getattr(d,"m_Name","") or ""
                if any(k in nm.lower() for k in GO_KEYS): gohits.append(nm)
            except Exception: pass
        elif tn=="Sprite":
            try:
                d=obj.read(); sprites.add(getattr(d,"m_Name","") or "")
            except Exception: pass
        elif tn=="Texture2D":
            try:
                d=obj.read(); texs.add(getattr(d,"m_Name","") or "")
            except Exception: pass
    if gohits:
        base=os.path.basename(lp)
        print(f"\n#### {base}: GameObject title-hits ({len(gohits)}): {sorted(set(gohits))[:25]}")
        if sprites: print(f"     Sprites in level: {sorted(s for s in sprites if s)[:40]}")
        if texs: print(f"     Texture2D in level: {sorted(t for t in texs if t)[:40]}")
