"""Resolve the MonoBehaviour scripts attached to the Menu Panel / Menu Group Panel
GameObjects in level1 by loading level1's external files. READ-ONLY."""
import UnityPy, os
DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"

# 1) inspect externals of level1
env = UnityPy.load(DATA + r"\level1")
sf = list(env.files.values())[0]
print("level1 externals:")
for e in sf.externals:
    print("   ", getattr(e, "path", e))

# 2) load level1 together with the whole FF9_Data dir so PPtrs resolve
#    (lazy: UnityPy indexes object tables only). Time-box by loading level1 +
#    referenced external file names that exist.
ext_names = []
for e in sf.externals:
    nm = os.path.basename(getattr(e, "path", "") or "").strip()
    if nm and os.path.exists(os.path.join(DATA, nm)):
        ext_names.append(nm)
print("resolvable external files present:", ext_names)

paths = [DATA + r"\level1"] + [os.path.join(DATA, n) for n in ext_names]
env2 = UnityPy.load(*paths)

# Build gameobject name map + monobehaviours for level1 only
GO_MENU_PANEL = 3826
GO_MENU_GROUP = 2156
target_gos = {GO_MENU_PANEL: "Menu Panel", GO_MENU_GROUP: "Menu Group Panel"}
go_name = {}
mbs = []
for obj in env2.objects:
    src = obj.assets_file.name if hasattr(obj, "assets_file") else "?"
    if "level1" not in str(getattr(obj.assets_file, "name", "")):
        # still collect GO names from level1 only; skip others for names
        pass
    if obj.type.name == "GameObject":
        try: go_name[obj.path_id] = obj.read().m_Name
        except: pass
    elif obj.type.name == "MonoBehaviour":
        mbs.append(obj)

print("\nMonoBehaviours attached to target GameObjects (level1):")
for obj in mbs:
    try:
        d = obj.read_typetree()
        gpid = d.get("m_GameObject", {}).get("m_PathID", 0)
        if gpid in target_gos:
            cn = None
            try:
                s = obj.read().m_Script.read()
                cn = getattr(s, "m_ClassName", None)
            except Exception as ex:
                cn = f"<unresolved: {ex}>"
            print(f"  GO '{target_gos[gpid]}' (go={gpid}) <- MB path_id={obj.path_id} script={cn!r}")
    except Exception:
        pass

# Also: scan ALL level1 MBs for class TitleUI now that externals loaded
print("\nScanning all level1 MonoBehaviours for script 'TitleUI'...")
count = 0
for obj in mbs:
    try:
        s = obj.read().m_Script.read()
        if getattr(s, "m_ClassName", None) == "TitleUI":
            d = obj.read_typetree()
            gpid = d.get("m_GameObject", {}).get("m_PathID", 0)
            print(f"  TitleUI MB path_id={obj.path_id} on GO '{go_name.get(gpid,'?')}' (go={gpid})")
            count += 1
    except Exception:
        pass
print("TitleUI MBs found:", count)
