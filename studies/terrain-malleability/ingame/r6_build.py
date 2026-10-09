"""BUILD + REGISTERED PREDICTIONS for in-game round 6 (2026-10-09): story terrain on a cell stock never switches (terrain
study P1; engine patch s92, `world-forms --arm` + `world-terrain --form 2`). Writes ONLY into staging folders under
ingame/out/r6_stage/ (gitignored), through the scratch mod folder FF9CustomMap-lab (emptied around every build; not in
FolderNames while this runs).

THE CELL: (6,12), not one of the 26. Its Object has a walkable tile at O = (395.47, -799.35) that the sky query answers
with the Object (2.962), and plain walkable ground beside it (find_r6_cell: the only such cell on disc 1).
THE FILES (all from the kit's CLI, as a user would run it):
  T2      world-forms --arm 6 12 --when true, then world-terrain --form 2 --at 402.68 -799.52 --radius 16 --raise 6
          -> Block[6][12] Terrain2.ff9mesh (its form-1 ground + 6; the Object tile's welded rim held)
  F_true / F_false / F_flag    world-forms --arm 6 12 --when "true" / "false" / "(GetEventGlobalByte(1089) & 1) != 0"
          -> Block[6][12] Form.txt  (flag 8712 = byte 1089 bit 0, FIRST_SAFE_FLAG; off in a new game)
THE STAGES (lab files -> the engine's verdict -> the ground):
  stock        -               -> nothing armed            -> STOCK at every point
  armed_false  T2 + F_false    -> armed, condition false    -> STOCK
  armed_true   T2 + F_true     -> armed, switched           -> FORM2: T/T2 on the raised ground, O on the Object (carried)
  flag_off     T2 + F_flag     -> armed, flag 8712 off      -> STOCK
  flag_on      T2 + F_flag, flag 8712 set in the field      -> FORM2 (story-driven: the same files, a save bit)
  no_form      T2 only         -> armed, no condition       -> STOCK ("never")
Read points: O (the Object tile), T (the plain ground 7u east, the hill's centre), T2 (5.3u further east, on the
slope), ctl (outside the cell's edit). FORM2's O = the stock Object height: had the engine not carried the form-1
Object into form 2, O would read the raised Terrain2 there (or nothing).
Writes out/r6_build.json.
Run:  py studies/terrain-malleability/ingame/r6_build.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import r3_build as RB                                # noqa: E402  (the sky ground query, the lab)
import forms_build as FB                             # noqa: E402  (ground_at: the within-mesh rule)

STAGE = HERE / "out" / "r6_stage"
KIT = RB.KIT
LAB = "FF9CustomMap-lab"
CELL = (6, 12)
T2_REL = "FF9_Data/WorldMap/Disc1/0_1/r12/Block[6][12] Terrain2.ff9mesh"
FORM_REL = "FF9_Data/WorldMap/Disc1/0_1/r12/Block[6][12] Form.txt"
FLAG_COND = "(GetEventGlobalByte(1089) & 1) != 0"
POINTS = {"O": (395.47, -799.35), "T": (402.68, -799.52), "T2": (407.98, -799.61), "ctl": (431.37, -823.61)}
STAGES = {   # name: (lab files, ground source, flag 8712)
    "stock": ((), "stock", False),
    "armed_false": (("T2", "F_false"), "stock", False),
    "armed_true": (("T2", "F_true"), "form2", False),
    "flag_off": (("T2", "F_flag"), "stock", False),
    "flag_on": (("T2", "F_flag"), "form2", True),
    "no_form": (("T2",), "stock", False),
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def kit(argv) -> subprocess.CompletedProcess:
    p = subprocess.run([sys.executable, "-m", "ff9mapkit"] + argv, cwd=str(KIT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, (argv, p.stdout[-1500:], p.stderr[-1500:])
    return p


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    shutil.rmtree(STAGE, ignore_errors=True)
    files = STAGE / "files"
    res = {"cell": CELL, "points": POINTS, "flag_condition": FLAG_COND, "files": {}, "stages": {}, "predict": {}}
    lab = RB.A.GAME / LAB

    # T2: arm the cell, then the kit's own form-2 reshape
    RB._clear_lab()
    a = kit(["world-forms", "--mod-folder", LAB, "--arm", "6", "12", "--when", "true"])
    t = kit(["world-terrain", "--mod-folder", LAB, "--form", "2", "--at", "402.68", "-799.52", "--radius", "16",
             "--raise", "6"])
    src = lab / T2_REL
    assert src.is_file(), t.stdout
    (files / "T2" / Path(T2_REL).parent).mkdir(parents=True)
    shutil.copy2(src, files / "T2" / T2_REL)
    extra = sorted(str(q.relative_to(lab)) for q in lab.rglob("*") if q.is_file()
                   and q.name not in (src.name, "Block[6][12] Form.txt") and not q.name.startswith(".ff9world"))
    res["files"]["T2"] = {"rel": T2_REL, "sha": sha(files / "T2" / T2_REL), "arm": a.stdout[-600:],
                          "receipt": t.stdout[-2500:], "other_files": extra}
    assert "custom cell(s) [(6, 12)]" in t.stdout and "FORM-2 ground" in t.stdout, t.stdout
    assert not extra, extra                           # nothing else written (no Terrain, no disc-4 copy)
    # the Form.txt variants, each written by the kit
    for name, cond in {"F_true": "true", "F_false": "false", "F_flag": FLAG_COND}.items():
        RB._clear_lab()
        kit(["world-forms", "--mod-folder", LAB, "--arm", "6", "12", "--when", cond])
        (files / name / Path(FORM_REL).parent).mkdir(parents=True)
        shutil.copy2(lab / FORM_REL, files / name / FORM_REL)
        res["files"][name] = {"rel": FORM_REL, "sha": sha(files / name / FORM_REL),
                              "text": (files / name / FORM_REL).read_text(encoding="utf-8")}
    RB._clear_lab()

    # predictions: STOCK = the live stack's sky query; FORM2 = the Object where it answers (carried: registered
    # before the Terrain2 copy), else the Terrain2 (forms_build.ground_at: the within-mesh rule)
    from ff9mapkit.world import mesh as M
    t2 = M.blockmesh_from_ff9mesh(files / "T2" / T2_REL, disc=1, x=CELL[0], y=CELL[1], lod="0_1", part="Terrain2")
    stock = {k: RB.ground(None, 1, *p) for k, p in POINTS.items()}
    assert stock["O"]["part"] == "Object" and stock["T"]["part"] == "Terrain" and stock["T2"]["part"] == "Terrain"
    sunk = {k: (1.171875 if stock[k]["topo"] in (36, 37, 38) else 0.0) for k in POINTS}
    FB.ORIGIN = (CELL[0] * 64.0, -CELL[1] * 64.0)
    form2 = {}
    for k, p in POINTS.items():
        if stock[k]["part"] == "Object" or not (CELL[0] * 64 <= p[0] < CELL[0] * 64 + 64
                                                and -CELL[1] * 64 - 64 < p[1] <= -CELL[1] * 64):
            form2[k] = stock[k]["y"]                   # the Object answers first; or another cell
        else:
            form2[k] = round(FB.ground_at(t2, *p)[0], 4)
    ground = {"stock": {k: round(stock[k]["y"] - sunk[k], 4) for k in POINTS},
              "form2": {k: round(form2[k] - sunk[k], 4) for k in POINTS}}
    bug_O = round(FB.ground_at(t2, *POINTS["O"])[0], 4) if FB.ground_at(t2, *POINTS["O"])[0] is not None else None
    res["ground"], res["stock_query"], res["bug_O_if_object_not_carried"] = ground, stock, bug_O
    for k in ("T", "T2"):
        assert ground["form2"][k] - ground["stock"][k] > 1.0, (k, ground)
    assert abs(ground["form2"]["ctl"] - ground["stock"]["ctl"]) < 1e-6
    for name, (labf, src_, flag) in STAGES.items():
        res["stages"][name] = {"lab": list(labf), "ground": src_, "flag": flag}
        res["predict"][name] = ground[src_]
        print(f"{name:12s} lab {'+'.join(labf) or '-':12s} flag {int(flag)} -> {src_:5s} "
              + " ".join(f"{k} {v}" for k, v in ground[src_].items()))
    print("O if the Object were NOT carried into form 2:", bug_O)
    out = HERE / "out" / "r6_build.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
