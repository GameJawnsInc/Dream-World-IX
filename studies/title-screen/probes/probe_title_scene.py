"""Locate: title_bg, title_logo, logo_sqex, logo_sst, caution/warning, and the Title
scene level file. Scans resources.assets (deduped) + every level* + mainData.
READ-ONLY.  Run: py probe_title_scene.py
"""
import os, glob, time
import UnityPy

DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"
NEEDLES = ["title_bg", "title_logo", "logo_sqex", "logo_sst", "sqex", "silicon", "sst",
           "caution", "warning", "splash", "atlas"]

def hit(s):
    s = (s or "").lower()
    return any(n in s for n in NEEDLES)

# 1) full dedup scan of resources.assets for title/logo/atlas names
print("==== resources.assets FULL dedup (Texture2D/Sprite/Material/MonoBehaviour) ====")
env = UnityPy.load(os.path.join(DATA, "resources.assets"))
seen = {}
for obj in env.objects:
    try: tn = obj.type.name
    except Exception: continue
    if tn not in ("Texture2D","Sprite","Material","MonoBehaviour"): continue
    try: d = obj.read()
    except Exception: continue
    nm = getattr(d,"m_Name",getattr(d,"name","")) or ""
    if hit(nm):
        key=(tn,nm)
        seen[key]=seen.get(key,0)+1
for (tn,nm),c in sorted(seen.items()):
    print(f"  {tn:14} {nm}  x{c}")

# 2) find the Title scene level: which level file has a MonoBehaviour script 'TitleUI'
#    and any objects named title_bg/title_logo/logo_sqex/logo_sst
print("\n==== per-level scan for Title scene + title_bg/title_logo/logo_* ====")
levels = sorted(glob.glob(os.path.join(DATA,"level*")),
                key=lambda p:int(os.path.basename(p)[5:]) if os.path.basename(p)[5:].isdigit() else 999)
for lp in levels:
    t0=time.time()
    try: e = UnityPy.load(lp)
    except Exception as ex:
        print(f"  {os.path.basename(lp)}: load-fail {ex}"); continue
    names=set(); has_titleui=False; scripts=set()
    for obj in e.objects:
        try: tn=obj.type.name
        except Exception: continue
        if tn=="MonoBehaviour":
            try:
                d=obj.read()
                # script class name via m_Script pptr
                sc=getattr(d,"m_Script",None)
                if sc is not None:
                    try:
                        s=sc.read(); cn=getattr(s,"m_ClassName","")
                        if cn: scripts.add(cn)
                        if cn=="TitleUI": has_titleui=True
                    except Exception: pass
                nm=getattr(d,"m_Name","") or ""
                if any(k in nm.lower() for k in ("title_bg","title_logo","logo_sqex","logo_sst")):
                    names.add(("MB",nm))
            except Exception: pass
        elif tn in ("Texture2D","Sprite","GameObject"):
            try:
                d=obj.read(); nm=getattr(d,"m_Name","") or ""
                low=nm.lower()
                if any(k in low for k in ("title_bg","title_logo","logo_sqex","logo_sst","sqex","sst")):
                    names.add((tn,nm))
            except Exception: pass
    tag = "  <-- TitleUI SCENE" if has_titleui else ""
    if has_titleui or names:
        print(f"  {os.path.basename(lp):10} titleui={has_titleui}{tag}")
        for t,n in sorted(names): print(f"       {t}: {n}")
        # dump a few scripts to identify scene
        if has_titleui:
            print(f"       scripts sample: {sorted(list(scripts))[:12]}")
