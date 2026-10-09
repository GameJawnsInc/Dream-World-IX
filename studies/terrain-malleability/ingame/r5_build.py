"""BUILD + REGISTERED PREDICTIONS for in-game round 5 (2026-10-08): defects 19 and 20 in game, on the Black Mage
Village cell (22,14), whose stock form switch changes nothing (forms lane F10: its form-2 terrain is byte-equal to
form 1), so every height change is ours. Writes ONLY into staging folders under ingame/out/r5_stage/ (gitignored),
through the scratch mod folder FF9CustomMap-lab (emptied around every build; not in FolderNames while this runs).

THE QUESTIONS.
  Defect 19 (the kit now warns on it): a form-1 `Terrain` override on a switchable cell is replaced by the stock
  form-2 mesh when the place switches, and a `Terrain2` override beside it keeps an edit in form 2. Round 1 proved a
  Terrain2 binds (RESULTS section 5); no round has had a form-1 edit on a cell while its place switched.
  Defect 20 (the kit now writes `Clear`): the engine parses the base file, then every FolderNames folder from the
  lowest priority to the highest, ORing conditions for one key; `Place X Clear` drops what was parsed before it, and
  Memoria's documented `Clean` does nothing. Two lab folders: FF9CustomMap-lab (first) and FF9CustomMap-lab2 (second,
  so parsed BEFORE the lab).

FILES (all from the kit, except the Clean line, which is Memoria's documented syntax, and the Terrain2, which no CLI
verb writes -- built the way round 1 built it, `forms_build.py`, and checked byte-equal to round 1's file):
  T27     world-deploy --center 1440 -928 --radius 12 --flatten --height 27   -> Block[22][14] Terrain.ff9mesh
  T2_26   stock form-2 terrain flattened to 26 (r12, same centre)             -> Block[22][14] Terrain2.ff9mesh
  env     world-environment --dry-run on {place BlackMageVillage on=...}: on_true / on_false (with Clear),
          combine_false (stack = "combine": no Clear), plus clean_false (hand: `Clean` + the false line)

THE STAGES (lab | lab2 -> the place's condition -> form -> the ground at the read points):
  stock        -                         | -       -> stock (scenario 0: false) -> 1 -> STOCK
  d19_t_f1     T27 + on_false            | -       -> false -> 1 -> T27   (the edit shows)
  d19_t_f2     T27 + on_true             | -       -> true  -> 2 -> STOCK (THE EDIT VANISHES: stock form 2)
  d19_t_t2_f2  T27 + T2_26 + on_true     | -       -> true  -> 2 -> T2_26 (a Terrain2 keeps an edit in form 2)
  d20_clear    T27 + T2_26 + on_false    | on_true -> Clear drops lab2's true: false -> 1 -> T27   (the fix)
  d20_lower    T27 + T2_26               | on_true -> lab2 alone: true -> 2 -> T2_26               (lab2 is read)
  d20_clear2   = d20_clear                                                         -> T27
  d20_or       T27 + T2_26 + comb_false  | on_true -> true OR false -> 2 -> T2_26  (the old kit output: lab2 wins)
  d20_clear3   = d20_clear                                                         -> T27
  d20_clean    T27 + T2_26 + clean_false | on_true -> Clean ignored: OR -> 2 -> T2_26  (Memoria's documented word)
The predictions alternate wherever they can, so a stale parse or a failed swap shows as a wrong height.
Read points: round 1's four off-lattice points m1-m4 (RESULTS section 5) plus a control 20u out that every stage
reads as stock.
Writes out/r5_build.json.
Run:  py studies/terrain-malleability/ingame/r5_build.py   (from the repo root or ff9mapkit/)
"""
from __future__ import annotations

import copy
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
import forms_build as FB                             # noqa: E402  (round 1's Terrain2 builder + ground_at)

STAGE = HERE / "out" / "r5_stage"
KIT = RB.KIT
LAB = "FF9CustomMap-lab"
ROUND1_T2 = Path(r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                 r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\forms\Block[22][14] Terrain2.ff9mesh")
T_REL = "FF9_Data/WorldMap/Disc1/0_1/r14/Block[22][14] Terrain.ff9mesh"
T2_REL = "FF9_Data/WorldMap/Disc1/0_1/r14/Block[22][14] Terrain2.ff9mesh"
ENV_REL = "StreamingAssets/Data/World/Environment.txt"
POINTS = {k: tuple(v["world"]) for k, v in json.loads((HERE / "out" / "forms_midcell.json").read_text()).items()}
POINTS["ctl"] = (1421.37, -941.61)                   # 23u out: outside every edit, off the 4u lattice
STAGES = {   # name: (lab files, lab2 files, ground source)
    "stock": ((), (), "stock"),
    "d19_t_f1": (("T27", "on_false"), (), "T27"),
    "d19_t_f2": (("T27", "on_true"), (), "stock"),
    "d19_t_t2_f2": (("T27", "T2_26", "on_true"), (), "T2_26"),
    "d20_clear": (("T27", "T2_26", "on_false"), ("on_true",), "T27"),
    "d20_lower": (("T27", "T2_26"), ("on_true",), "T2_26"),
    "d20_clear2": (("T27", "T2_26", "on_false"), ("on_true",), "T27"),
    "d20_or": (("T27", "T2_26", "combine_false"), ("on_true",), "T2_26"),
    "d20_clear3": (("T27", "T2_26", "on_false"), ("on_true",), "T27"),
    "d20_clean": (("T27", "T2_26", "clean_false"), ("on_true",), "T2_26"),
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def kit(argv) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "ff9mapkit"] + argv, cwd=str(KIT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def env_text(name: str, on: bool, stack: str = "replace") -> tuple[str, str]:
    toml = STAGE / "env" / f"{name}.toml"
    toml.parent.mkdir(parents=True, exist_ok=True)
    toml.write_text(f'[world_environment]\nstack = "{stack}"\n[[world_environment.place]]\nname = "BlackMageVillage"\n'
                    f'on = {"true" if on else "false"}\n', encoding="utf-8")
    p = kit(["world-environment", str(toml), "--mod-folder", LAB, "--dry-run"])
    assert p.returncode == 0, p.stderr
    return p.stdout, " ".join(["world-environment", toml.name, "--dry-run"])


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    shutil.rmtree(STAGE, ignore_errors=True)
    (STAGE / "files").mkdir(parents=True)
    res = {"points": POINTS, "files": {}, "stages": {}, "predict": {}}

    # T27: the kit's own writer, into the empty lab; its receipt must carry the defect-19 warning
    RB._clear_lab()
    p = kit(["world-deploy", "--center", "1440", "-928", "--radius", "12", "--flatten", "--height", "27",
             "--mod-folder", LAB, "--skip-mirror"])
    src = RB.A.GAME / LAB / T_REL
    assert p.returncode == 0 and src.is_file(), (p.returncode, p.stdout[-2000:], p.stderr[-2000:])
    t27 = STAGE / "files" / "T27"
    (t27 / Path(T_REL).parent).mkdir(parents=True)
    shutil.copy2(src, t27 / T_REL)
    others = [q for q in (RB.A.GAME / LAB).rglob("*") if q.is_file() and q.name != src.name
              and not q.name.startswith(".ff9world")]
    RB._clear_lab()
    res["files"]["T27"] = {"rel": T_REL, "sha": sha(t27 / T_REL), "stdout": p.stdout[-3000:],
                           "warned": "replaces FORM 1 ONLY" in p.stdout, "other_files": [str(q) for q in others]}
    assert res["files"]["T27"]["warned"], "world-deploy did not print the defect-19 warning"
    assert not others, others

    # T2_26: round 1's builder, byte-equal to the file round 1 walked
    stock2 = FB.E.read_block(FB.BX, FB.BY, disc=1, lod="0_2", part="terrain")
    bm2 = copy.deepcopy(stock2)
    FB.M.flatten_region(bm2, radius=FB.RADIUS, center=FB.CENTER, height=FB.HEIGHT, world_origin=FB.ORIGIN)
    t2 = STAGE / "files" / "T2_26"
    (t2 / Path(T2_REL).parent).mkdir(parents=True)
    FB.M.write_ff9mesh(bm2, t2 / T2_REL)
    res["files"]["T2_26"] = {"rel": T2_REL, "sha": sha(t2 / T2_REL),
                             "round1_sha": sha(ROUND1_T2) if ROUND1_T2.is_file() else None}
    assert res["files"]["T2_26"]["sha"] == res["files"]["T2_26"]["round1_sha"], "Terrain2 differs from round 1's"

    # the Environment.txt variants
    for name, (on, stack) in {"on_true": (True, "replace"), "on_false": (False, "replace"),
                              "combine_false": (False, "combine")}.items():
        txt, how = env_text(name, on, stack)
        d = STAGE / "files" / name / Path(ENV_REL).parent
        d.mkdir(parents=True)
        (d / "Environment.txt").write_text(txt, encoding="utf-8")
        res["files"][name] = {"rel": ENV_REL, "text": txt, "via": how}
    clean = "Place BlackMageVillage Clean\nPlace BlackMageVillage [Condition=false]\n"
    d = STAGE / "files" / "clean_false" / Path(ENV_REL).parent
    d.mkdir(parents=True)
    (d / "Environment.txt").write_text(clean, encoding="utf-8")
    res["files"]["clean_false"] = {"rel": ENV_REL, "text": clean, "via": "hand: Memoria's documented Clean"}
    assert "Clear" in res["files"]["on_false"]["text"] and "Clear" not in res["files"]["combine_false"]["text"]
    for k, v in res["files"].items():
        if "sha" not in v:
            v["sha"] = sha(STAGE / "files" / k / v["rel"])

    # predictions: STOCK = the live stack (no lab); T27 = the staged form-1 override; T2_26 = round 1's ground_at
    # rule on the Terrain2 (form 2 = Object2 + Terrain2: round 1's readings matched the terrain alone)
    ground = {"stock": {k: RB.ground(None, 1, *pt)["y"] for k, pt in POINTS.items()},
              "T27": {k: RB.ground(t27, 1, *pt)["y"] for k, pt in POINTS.items()},
              "T2_26": {k: round(FB.ground_at(bm2, *pt)[0], 4) for k, pt in POINTS.items()}}
    stock2_y = {k: round(FB.ground_at(stock2, *pt)[0], 4) for k, pt in POINTS.items()}
    assert all(abs(stock2_y[k] - ground["stock"][k]) < 1e-3 for k in POINTS), (stock2_y, ground["stock"])
    res["ground"], res["stock_form2"] = ground, stock2_y
    for k in ("m1", "m2", "m3", "m4"):                   # every source must be told apart at each read point
        a, b, c = ground["stock"][k], ground["T27"][k], ground["T2_26"][k]
        assert min(abs(a - b), abs(a - c), abs(b - c)) > 0.3, (k, a, b, c)
    assert len({round(ground[s]["ctl"], 3) for s in ground}) == 1, ground
    for name, (lab, lab2, src_) in STAGES.items():
        res["stages"][name] = {"lab": list(lab), "lab2": list(lab2), "ground": src_}
        res["predict"][name] = ground[src_]
        print(f"{name:12s} lab {'+'.join(lab) or '-':28s} lab2 {'+'.join(lab2) or '-':8s} -> {src_:6s} "
              + " ".join(f"{k} {v}" for k, v in ground[src_].items()))
    out = HERE / "out" / "r5_build.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
