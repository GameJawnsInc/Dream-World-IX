"""Inventory sharedassets2.assets (home of title_bg/title_logo + logo atlas).
List every Texture2D (with dims), Sprite, and MonoBehaviour (UIAtlas) m_Name.
READ-ONLY. Run: py probe_sa2.py
"""
import os
import UnityPy
DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"
e=UnityPy.load(os.path.join(DATA,"sharedassets2.assets"))
tex=[]; spr=[]; mb=[]; other={}
for obj in e.objects:
    tn=obj.type.name
    try: d=obj.read()
    except Exception:
        other[tn]=other.get(tn,0)+1; continue
    nm=getattr(d,"m_Name",getattr(d,"name","")) or ""
    if tn=="Texture2D":
        w=getattr(d,"m_Width","?"); h=getattr(d,"m_Height","?")
        tex.append(f"{nm} [{w}x{h}]")
    elif tn=="Sprite":
        spr.append(nm)
    elif tn=="MonoBehaviour":
        mb.append(nm)
    else:
        other[tn]=other.get(tn,0)+1
print(f"== Texture2D ({len(tex)}) ==")
for t in sorted(tex): print("  ",t)
print(f"== Sprite ({len(spr)}) ==")
for s in sorted(set(spr)): print("  ",s)
print(f"== MonoBehaviour m_Names ({len(mb)}) ==")
for m in sorted(set(x for x in mb if x)): print("  ",m)
print(f"== other type counts ==  {other}")
