"""
Probe FF9 level files for Title-screen GameObjects + MonoBehaviours.
READ-ONLY on the game install. Dumps GameObject names and MonoBehaviour
script names (best-effort resolution) from level1, level2, level6.
"""
import sys, time
import UnityPy

DATA = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data"
TARGETS = ["level1", "level2", "level6"]
# keyword filter for interesting names
KW = ["title", "menu", "logo", "slide", "button", "panel", "movie", "staff",
      "license", "language", "splash", "continue", "newgame", "new game",
      "loadgame", "load game", "cloud", "bg"]

def interesting(name):
    n = (name or "").lower()
    return any(k in n for k in KW)

for lvl in TARGETS:
    path = DATA + "\\" + lvl
    print("="*70)
    print("FILE:", path)
    t0 = time.time()
    try:
        env = UnityPy.load(path)
    except Exception as e:
        print("  LOAD ERROR:", e)
        continue
    go_names = []
    mb_list = []
    type_counts = {}
    for obj in env.objects:
        tn = obj.type.name
        type_counts[tn] = type_counts.get(tn, 0) + 1
        try:
            if tn == "GameObject":
                d = obj.read()
                nm = getattr(d, "m_Name", "") or getattr(d, "name", "")
                go_names.append((obj.path_id, nm))
            elif tn == "MonoBehaviour":
                mb_list.append(obj)
        except Exception as e:
            pass
    print("  object type counts:", type_counts)
    print("  total GameObjects:", len(go_names))
    print("  -- GameObjects (interesting by keyword) --")
    for pid, nm in go_names:
        if interesting(nm):
            print(f"     GO pathid={pid} name={nm!r}")
    # dump ALL GameObject names if few
    if len(go_names) <= 60:
        print("  -- ALL GameObject names --")
        for pid, nm in go_names:
            print(f"     GO pathid={pid} name={nm!r}")
    # MonoBehaviour script resolution (best effort)
    print("  total MonoBehaviours:", len(mb_list))
    script_names = {}
    resolved = 0
    for obj in mb_list:
        try:
            mb = obj.read()
            sname = None
            # try typetree-less path: m_Script PPtr
            scr = getattr(mb, "m_Script", None)
            if scr is not None:
                try:
                    s = scr.read()
                    sname = getattr(s, "m_ClassName", None) or getattr(s, "m_Name", None)
                    resolved += 1
                except Exception:
                    sname = None
            if sname:
                script_names[sname] = script_names.get(sname, 0) + 1
        except Exception:
            pass
    print("  MonoBehaviour scripts resolved:", resolved, "of", len(mb_list))
    for k in sorted(script_names):
        print(f"     script {k!r} x{script_names[k]}")
    print("  elapsed %.1fs" % (time.time()-t0))
