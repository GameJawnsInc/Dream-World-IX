"""READ-ONLY: frame counts + engine-path presence of every JUMP/LADDER-named clip on each dress rig's own folder
(the plain family AND the named variants), so the s157 twin table's fallback can pick 'nearest in frame count'.
Needs the game install (p0data5) and the Memoria clone; writes variants.json beside this file."""
import json, sys
from pathlib import Path
WT = Path(__file__).resolve().parents[3]          # the checkout this census lives in (its own ff9mapkit package)
sys.path.insert(0, str(WT / "ff9mapkit"))
sys.path.insert(0, str(WT / "studies" / "battle-coop" / "dress-census"))
import ff9mapkit  # noqa
assert Path(ff9mapkit.__file__).resolve().is_relative_to((WT / "ff9mapkit").resolve()), ff9mapkit.__file__
import rigs_8_11 as R  # noqa
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
tables = R.load_tables(Path(r"C:\gd\FFIX\Memoria"))
inst = R.Install(GAME)
RIGS = [(0, "Zidane", 98, "ANH_MAIN_F0_ZDN_"), (1, "Vivi", 8, "ANH_MAIN_F0_VIV_"), (2, "Garnet", 185, "ANH_MAIN_F0_GRN_"),
    (3, "Steiner", 5489, "ANH_MAIN_F0_STN_"), (4, "Freya", 192, "ANH_MAIN_F0_FRJ_"), (5, "Quina", 273, "ANH_MAIN_F0_KUI_"),
    (6, "Eiko", 443, "ANH_MAIN_F0_EIK_"), (7, "Amarant", 509, "ANH_MAIN_F0_SLM_"), (8, "moogle", 220, "ANH_NPC_F0_MOG_"),
    (9, "Cinna", 107, "ANH_SUB_F0_CNA_"), (10, "Marcus", 109, "ANH_SUB_F0_MRC_"), (11, "Blank", 5467, "ANH_SUB_F0_BLN_"),
    (12, "Beatrix", 204, "ANH_SUB_F0_BTX_")]
out = {}
for rig, who, model, pre in RIGS:
    rows = []
    for name, ids in sorted(tables["anim_ids"].items()):
        if not name.startswith(pre):
            continue
        suf = name[len(pre):]
        if "JUMP" not in suf and "LADDER" not in suf:
            continue
        aid = tables["anim_first"][name]
        fr = inst.frames(model, aid)
        ep = inst.engine_path(tables, aid)
        rows.append({"suffix": suf, "ids": ids, "first": aid, "frames": fr.get("frames"), "engine_on_disc": ep["on_disc"]})
    out[who] = rows
    print(rig, who)
    for r in rows:
        print("   %-18s ids=%-16s frames=%s on_disc=%s" % (r["suffix"], r["ids"], r["frames"], r["engine_on_disc"]))
(Path(__file__).parent / "variants.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
