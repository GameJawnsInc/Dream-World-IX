"""forms lane CENSUS 2 -- the RUNTIME tier. SetForm gates on the SCENE WMBlock's IsSwitchable (WMBlock.cs:99),
not the prefab's. WMWorld.WorldDisc is a baked scene reference (RESEARCH.md R2); the scene files carrying a
'WorldDisc' GameObject are FF9_Data/level7 and level19 (byte grep + GameObject census). Scene MonoBehaviours are
TYPETREE-STRIPPED, so we borrow the WMBlock typetree from the same class serialized in p0data3's
'worlddisc-incasethatitneedstocreateagain.prefab' and parse each scene MB with it, with check_read=True (the
parse must consume EXACTLY the object's bytes) -- that, plus "480 rows covering the 24x20 grid once each", is the
calibration that the borrowed layout is right.  Rerun:  py probe_scene_worlddisc.py"""
import sys, collections, json
from pathlib import Path
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import UnityPy
from ff9mapkit.world import extract as X
G = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data")

env3 = X._worldmap_env(1)
nodes = None
for o in env3.objects:
    if (getattr(o, "container", "") or "").lower().endswith("worlddisc-incasethatitneedstocreateagain.prefab"):
        root = o.read()
        tr = [pp for cid, pp in root.m_Component if cid == 4][0].deref().read()
        g = tr.m_Children[0].deref().read().m_GameObject.deref().read()
        mb = [pp for cid, pp in g.m_Component if cid == 114][0].deref()
        nodes = mb.serialized_type.nodes
        break
assert nodes, "no WMBlock typetree donor"
backup = json.loads((Path(__file__).parent / "out" / "prefab_census.json").read_text())   # for cross-check
out = {}
for lv in ("level7", "level19"):
    env = UnityPy.load(str(G / lv))
    rows, fails = [], 0
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            tt = o.read_typetree(nodes=nodes, check_read=True)
        except Exception:
            fails += 1
            continue
        rows.append({"x": tt["InitialX"], "y": tt["InitialY"], "IsSwitchable": int(tt["IsSwitchable"]),
                     "IsSea": int(tt["IsSea"]), "Number": tt["Number"],
                     "nF1": len(tt["Form1Transforms"]), "nF2": len(tt["Form2Transforms"])})
    cells = collections.Counter((r["x"], r["y"]) for r in rows)
    full = len(cells) == 480 and all(v == 1 for v in cells.values()) and all(0 <= x < 24 and 0 <= y < 20 for x, y in cells)
    sw = sorted((r["x"], r["y"]) for r in rows if r["IsSwitchable"])
    numok = all(r["Number"] == r["y"] * 24 + r["x"] for r in rows)
    print(f"{lv}: parsed WMBlock={len(rows)} (other MBs not matching layout={fails}) grid-complete={full} "
          f"Number==row-major={numok} switchable={len(sw)} sea={sum(r['IsSea'] for r in rows)} "
          f"nonempty Form lists={sum(1 for r in rows if r['nF1'] or r['nF2'])}")
    pref_sw = sorted((r['x'], r['y']) for r in backup['1'] if r['IsSwitchable'])
    print("   switchable set == prefab IsSwitchable set (disc1):", sw == pref_sw)
    pref_sea = sorted((r['x'], r['y']) for r in backup['1'] if r['IsSea'])
    print("   sea set == prefab IsSea set (disc1):", sorted((r['x'], r['y']) for r in rows if r['IsSea']) == pref_sea)
    out[lv] = rows
(Path(__file__).parent / "out" / "scene_worlddisc.json").write_text(json.dumps(out), encoding="utf-8")
