"""Enumerate distinct MonoBehaviour script class names per level (with externals
loaded), to locate TitleUI / UIManager / other UIScene controllers. READ-ONLY."""
import UnityPy, os
DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"
WANT = ["TitleUI","UIManager","FieldMap","BattleHUD","MainMenuUI","WorldMap",
        "MenuUI","ShopUI","SaveLoadUI","CloudUI","EndGameUI","QuadMist","DialogManager"]

def externals_of(path):
    env = UnityPy.load(path)
    sf = list(env.files.values())[0]
    names = []
    for e in sf.externals:
        nm = os.path.basename(getattr(e, "path", "") or "").strip()
        if nm and os.path.exists(os.path.join(DATA, nm)):
            names.append(nm)
    return names

for lvl in ["level1", "level2", "level6"]:
    p = DATA + "\\" + lvl
    exts = externals_of(p)
    env = UnityPy.load(*([p] + [os.path.join(DATA, n) for n in exts]))
    # restrict to MBs whose source file is this level
    counts = {}
    total = 0
    errs = 0
    go_name = {}
    interesting = []
    for obj in env.objects:
        fn = str(getattr(obj.assets_file, "name", ""))
        if obj.type.name == "GameObject" and lvl in fn:
            try: go_name[obj.path_id] = obj.read().m_Name
            except: pass
    for obj in env.objects:
        fn = str(getattr(obj.assets_file, "name", ""))
        if obj.type.name != "MonoBehaviour" or lvl not in fn:
            continue
        total += 1
        try:
            mb = obj.read()
            s = mb.m_Script.read()
            cn = getattr(s, "m_ClassName", None)
            asm = getattr(s, "m_AssemblyName", "?")
            counts[cn] = counts.get(cn, 0) + 1
            if cn in WANT:
                gpid = obj.read_typetree().get("m_GameObject",{}).get("m_PathID",0)
                interesting.append((cn, asm, obj.path_id, gpid, go_name.get(gpid,"?")))
        except Exception:
            errs += 1
    print("="*66)
    print(f"{lvl}: total MBs={total}, resolved distinct scripts={len(counts)}, unresolved={errs}")
    print("  WANT hits:")
    for cn, asm, mpid, gpid, gnm in interesting:
        print(f"     {cn} [{asm}] MB={mpid} on GO='{gnm}' (go={gpid})")
    # show whether each WANT class appears
    for w in WANT:
        if w in counts:
            print(f"     present: {w} x{counts[w]}")
