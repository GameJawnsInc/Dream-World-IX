"""(a) level1 scene roots + any Title/UI-Root/Manager GameObject.
(b) locate MonoScript assets named TitleUI/UIManager across assets files. READ-ONLY."""
import UnityPy, os, time
DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"

# ---- (a) level1 roots ----
env = UnityPy.load(DATA + r"\level1")
go_name, tr = {}, {}
for obj in env.objects:
    if obj.type.name == "GameObject":
        try: go_name[obj.path_id] = obj.read().m_Name
        except: pass
    elif obj.type.name in ("Transform","RectTransform"):
        try:
            d = obj.read_typetree()
            tr[obj.path_id] = (d["m_GameObject"]["m_PathID"], d["m_Father"]["m_PathID"],
                               [c["m_PathID"] for c in d.get("m_Children",[])])
        except: pass
roots = [(tid,g) for tid,(g,f,k) in tr.items() if f == 0]
print("level1 scene-root GameObjects (transform.father==0):")
for tid,(g,f,k) in sorted([(t,tr[t]) for t,_ in roots]):
    print(f"   root transform {tid} GO='{go_name.get(g,'?')}' (go={g}) #children={len(k)}")

print("\nlevel1 GameObjects matching title/root/manager/ui root:")
for pid,nm in go_name.items():
    low=(nm or '').lower()
    if any(s in low for s in ["title","ui root","uiroot","manager","game object"]) and nm:
        print(f"   GO '{nm}' (go={pid})")

# ---- (b) MonoScript search ----
def scan_scripts(fn, wanted, budget=90):
    p = DATA + "\\" + fn
    t0=time.time(); hits=[]; n=0
    try: env = UnityPy.load(p)
    except Exception as e:
        return [("<loaderr>",str(e))]
    for obj in env.objects:
        if time.time()-t0>budget:
            hits.append(("<timeout after %ds, scanned %d objs>"%(budget,n),"")); break
        if obj.type.name!="MonoScript": continue
        n+=1
        try:
            d=obj.read_typetree()
            cn=d.get("m_ClassName")
            if cn in wanted:
                hits.append((cn, d.get("m_AssemblyName","?"), obj.path_id))
        except: pass
    return hits

for fn in ["sharedassets0.assets","sharedassets2.assets","resources.assets"]:
    print(f"\nMonoScript scan in {fn} for TitleUI/UIManager:")
    for h in scan_scripts(fn, {"TitleUI","UIManager"}):
        print("   ", h)
