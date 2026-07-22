"""Focused probe: locate Menu Group Panel + ordered children, MenuPanel bg/logo,
and resolve the TitleUI MonoBehaviour's host GameObject + file. READ-ONLY."""
import UnityPy
DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"

def build(path):
    env = UnityPy.load(path)
    go_name = {}          # gameobject path_id -> name
    tr_of_go = {}         # gameobject path_id -> transform path_id
    tr = {}               # transform path_id -> dict(go, father, children[])
    mbs = []              # (path_id, gameobject_pid, script_pptr)
    for obj in env.objects:
        tn = obj.type.name
        if tn == "GameObject":
            d = obj.read()
            go_name[obj.path_id] = getattr(d, "m_Name", "") or ""
        elif tn in ("Transform", "RectTransform"):
            try:
                d = obj.read_typetree()
                gpid = d["m_GameObject"]["m_PathID"]
                fpid = d["m_Father"]["m_PathID"]
                kids = [c["m_PathID"] for c in d.get("m_Children", [])]
                tr[obj.path_id] = {"go": gpid, "father": fpid, "kids": kids}
                tr_of_go[gpid] = obj.path_id
            except Exception as e:
                pass
        elif tn == "MonoBehaviour":
            try:
                d = obj.read_typetree()
                gpid = d.get("m_GameObject", {}).get("m_PathID", 0)
                scr = d.get("m_Script", {})
                mbs.append((obj.path_id, gpid, scr, obj))
            except Exception:
                pass
    return env, go_name, tr_of_go, tr, mbs

for lvl in ["level1", "level2"]:
    path = DATA + "\\" + lvl
    print("="*72, "\nFILE:", lvl)
    env, go_name, tr_of_go, tr, mbs = build(path)
    # find candidate panels by name
    def find_go(substrs):
        out = []
        for pid, nm in go_name.items():
            low = nm.lower()
            if any(s in low for s in substrs):
                out.append((pid, nm))
        return out
    for label, subs in [("Menu Group Panel", ["menu group"]),
                        ("Menu Panel(Object)", ["menu panel"]),
                        ("Continue", ["continue"]),
                        ("New Game", ["new game"]),
                        ("Load Game", ["load game"]),
                        ("Cloud", ["cloud"]),
                        ("Logo", ["logo"]),
                        ("Slide", ["slide"])]:
        hits = find_go(subs)
        print(f"  [{label}] -> {[(p,n) for p,n in hits][:8]}")
    # For each 'Menu Group Panel' GO, list ordered children names
    for pid, nm in find_go(["menu group"]):
        trid = tr_of_go.get(pid)
        if trid and trid in tr:
            kids = tr[trid]["kids"]
            print(f"  '{nm}' (go={pid}) children in order:")
            for i, kt in enumerate(kids):
                kgo = tr.get(kt, {}).get("go")
                print(f"      GetChild({i}) -> transform {kt} -> GO '{go_name.get(kgo,'?')}' (go={kgo})")
    # For 'Menu Panel' list children (expect [0]=bg [1]=logo)
    for pid, nm in find_go(["menu panel"]):
        trid = tr_of_go.get(pid)
        if trid and trid in tr:
            kids = tr[trid]["kids"]
            print(f"  '{nm}' (go={pid}) children in order:")
            for i, kt in enumerate(kids):
                kgo = tr.get(kt, {}).get("go")
                print(f"      GetChild({i}) -> GO '{go_name.get(kgo,'?')}' (go={kgo})")
    # Resolve TitleUI MonoBehaviour
    print("  -- resolving MonoBehaviour scripts named TitleUI --")
    found = 0
    for mpid, gpid, scr, obj in mbs:
        try:
            s = obj.read().m_Script.read()
            cn = getattr(s, "m_ClassName", None)
            if cn == "TitleUI":
                found += 1
                print(f"      TitleUI MB path_id={mpid} on GO '{go_name.get(gpid,'?')}' (go={gpid})")
        except Exception:
            pass
    print("  TitleUI MonoBehaviours found in", lvl, ":", found)

# level6 quick summary
print("="*72, "\nFILE: level6 (Title.unity)")
env6 = UnityPy.load(DATA + "\\level6")
names = []
tc = {}
for obj in env6.objects:
    tc[obj.type.name] = tc.get(obj.type.name, 0) + 1
    if obj.type.name == "GameObject":
        names.append(obj.read().m_Name)
print("  type counts:", tc)
print("  GameObject names:", names)
