"""Defect-18 re-drive: register the boat prediction for world-reclaim's FIXED deploy shape with round 2's simulator.

    py studies/terrain-malleability/ingame/d18_predict.py

CALIBRATION FIRST: fed the PRE-fix shape (Terrain only), `veh_prep.boat_drive` must reproduce what round 2 registered
in out/veh_prep.json (flat6 open 123.81 / rim 19.75, which the in-game session 4 then matched at 19.81). Then the
FIXED shape -- whatever terrain.reclaim writes TODAY for (21,1), run for real into a throwaway mod root (an absolute
mod_folder, so the install is read and nothing is written to it) -- is driven over the same two lanes and the same
+-2 deg hull band. Writes out/d18_predict.json; exit 0 only when the calibration reproduces.

The session phases this registers (veh_session4.py PRED): `flat6-fixed` and `cliff-fixed`.
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(HERE))
import veh_prep as VP                                               # noqa: E402
from ff9mapkit.world import terrain as T                            # noqa: E402

assert Path(T.__file__).resolve().is_relative_to(REPO / "ff9mapkit"), T.__file__   # this tree's kit, not master's
REG = json.loads((VP.OUT / "veh_prep.json").read_text(encoding="utf-8"))["boat"]
BX, BY = VP.BOAT_CELL
XB = BX * 64.0
PHASES = {"flat6": dict(profile="flat", height=6.0), "flat1.2": dict(profile="flat", height=1.2),
          "island": dict(profile="island"), "cliff": dict(profile="cliff")}


def deploy_shape(phase):
    """{part: path} of what terrain.reclaim writes for the cell, deployed into a throwaway root."""
    VP.SCRATCH.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=f"d18_{phase}_", dir=VP.SCRATCH))
    T.reclaim(str(root / "LAB"), cells=[(BX, BY)], skip_mirror=True, **PHASES[phase])   # find_game_path / abs == abs
    d = root / "LAB" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / f"r{BY}"
    return {p.name.split("] ", 1)[1].rsplit(".", 1)[0]: str(p) for p in sorted(d.glob("*.ff9mesh"))}


def main():
    res = {"cell": [BX, BY], "lanes": REG["lanes"], "calibration": {}, "fixed": {}}
    ok = True
    for phase in PHASES:
        files = deploy_shape(phase)
        res["fixed"][phase] = {"parts": sorted(files)}
        for label, extra in (("pre-fix", {"Terrain": files["Terrain"]}), ("fixed", files)):
            ex = dict(extra, _cell=(BX, BY))
            row = {}
            for ln, v in REG["lanes"].items():
                x0, z0 = v["start"]
                lane = VP._lane(VP.boat_drive(x0, z0, 0.0, 160, extra=ex), XB)
                scan = VP.heading_scan(x0, z0, XB, ex)
                row[ln] = {"into_cell": lane["into_cell"], "stalled": lane["stalled"], "slides": lane["slides"],
                           "scan_into": [r["into_cell"] for r in scan["rows"]], "scan_all_stalled": scan["all_stalled"]}
            if label == "pre-fix":
                reg = REG["phases"][phase]
                match = all(abs(row[ln]["into_cell"] - reg[ln]["into_cell"]) < 0.05
                            and row[ln]["stalled"] == reg[ln]["stalled"] for ln in ("open", "rim"))
                res["calibration"][phase] = {"sim": row, "registered": {ln: reg[ln]["into_cell"] for ln in ("open", "rim")},
                                             "reproduces": match}
                ok &= match
            else:
                res["fixed"][phase].update(row)
            print(f"{phase:8} {label:8} open into={row['open']['into_cell']:8} stalled={row['open']['stalled']} | "
                  f"rim into={row['rim']['into_cell']:8} stalled={row['rim']['stalled']} | 9-heading all-stalled "
                  f"open={row['open']['scan_all_stalled']} rim={row['rim']['scan_all_stalled']}")
    res["calibration_ok"] = ok
    (VP.OUT / "d18_predict.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("calibration reproduces round 2:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
