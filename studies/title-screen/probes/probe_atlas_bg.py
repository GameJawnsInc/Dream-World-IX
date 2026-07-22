"""Find logo_sqex/logo_sst atlas + the title background sprite.
Scan level1/level2/level6 (+ sharedassets1) MonoBehaviours for typetrees mentioning
logo_sqex / title_bg; dump level6 GameObjects; list all Sprite names per level.
READ-ONLY. Run: py probe_atlas_bg.py
"""
import os, json
import UnityPy

DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"
TARGETS = ["level1","level2","level6","sharedassets1.assets"]
MARKERS = ["logo_sqex","logo_sst","title_bg"]

for fn in TARGETS:
    p=os.path.join(DATA,fn)
    if not os.path.exists(p): print(f"-- {fn} missing"); continue
    e=UnityPy.load(p)
    print(f"\n############ {fn} ############")
    # all GameObject names for level6 (the Title scene)
    if fn=="level6":
        gos=[]
        for obj in e.objects:
            if obj.type.name=="GameObject":
                try: gos.append(obj.read().m_Name)
                except Exception: pass
        print(f"  GameObjects ({len(gos)}): {sorted(set(gos))}")
    # sprite names present
    sprites=set()
    for obj in e.objects:
        if obj.type.name=="Sprite":
            try: sprites.add(obj.read().m_Name)
            except Exception: pass
    if sprites: print(f"  Sprite objects: {sorted(s for s in sprites if s)}")
    # MonoBehaviours mentioning markers (atlas sprite lists, UITexture, UI2DSprite)
    for obj in e.objects:
        if obj.type.name!="MonoBehaviour": continue
        try:
            tt=obj.read_typetree()
        except Exception:
            continue
        blob=json.dumps(tt, default=str).lower()
        for m in MARKERS:
            if m in blob:
                nm=tt.get("m_Name","")
                # try to surface atlas sprite name list
                spr=tt.get("mSprites")
                spnames=[s.get("name") for s in spr] if isinstance(spr,list) else None
                print(f"  [MB match '{m}'] m_Name='{nm}' keys={list(tt.keys())[:10]}")
                if spnames: print(f"      atlas mSprites: {spnames}")
                # if UI2DSprite/UITexture, show the sprite ref name field
                for k in ("mSpriteName","spriteName","mSprite","m_Sprite"):
                    if k in tt: print(f"      {k}={tt[k]}")
                break
