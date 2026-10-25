"""The FolderNames-stack rule in game: two lab folders FIRST in FolderNames, the 3D view's rule predicting each height.

    py studies/overworld-editor/stack_lab.py build      # out/stack_lab/ + out/stack_prep.json (the predictions)
    py studies/overworld-editor/stack_lab.py run        # install, reach the world, teleport, quit, uninstall, judge

THE RULE UNDER TEST (Memoria/World/WorldMeshOverride.cs, now render.resolve_file / cell_meshes / effective_prefab):
the engine walks FolderNames highest first and takes each file from the first folder holding it; a file it refuses
means STOCK there, not the next folder's file.

THE LAB (built outside the install; copied in for one session, moved out after: the launcher activates any folder
left there, memory project-ff9-launcher-activates-new-folders):
  FF9CustomMap-lab-hi, FF9CustomMap-lab-lo, then the game's own FolderNames.
  A  a stock land block (its own prefab, no Object, no override anywhere): lab-lo Terrain = stock + 1.5,
     lab-hi Terrain = stock + 3.0                                   -> the game stands at stock + 3.0
  B  another such block: lab-lo Terrain = stock + 1.5, lab-hi Terrain = the same bytes stamped version 2 (refused)
                                                                   -> the game stands on STOCK, not + 1.5
  C  an FF9CustomMap-world island cell (a diverted sea cell): lab-hi Terrain = that island's Terrain + 1.5
                                                                   -> the game stands at the island + 1.5
  K  control: the Landing Site pick from rung A1, untouched        -> 4.285 as before

REGISTERED PREDICTIONS (stack_prep.json, written by `build` before the game opens; tolerance 0.15):
  S1 each of A, B, C, K reads back the stand height point_info predicts on the STACKED site (lab-hi, lab-lo, then
     the game's FolderNames) -- and at A, B, C that height differs by >= 1.0 from the wrong rule's (A: lab-lo only;
     B: falling through to lab-lo; C: FF9CustomMap-world only), so the read-back can tell the rules apart;
  S2 Memoria.log: "[WorldMeshOverride] loaded" from lab-hi for A's and C's Terrain, and "failed to read" for B's.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))
import ff9mapkit                                                      # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(KIT), ff9mapkit.__file__

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MAIN_BACKUPS = Path(r"C:\gd\Dream-World-IX\backups")
INI = GAME / "Memoria.ini"
HI, LO = "FF9CustomMap-lab-hi", "FF9CustomMap-lab-lo"
OUT = HERE / "out" / "stack_lab"
PREP = HERE / "out" / "stack_prep.json"
STATE = HERE / "out" / "stack_install.json"
RESULT = HERE / "out" / "stack_result.json"
ARRIVAL = (68.0, -444.0)                                              # the 6603 route's world arrival (rung A1)
CONTROL = ("Landing Site", 326.16, -569.09)
TOL = 0.15


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _cell_file(root, bx, by, part="Terrain"):
    return root / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"


def _raised(bm, dy):
    from ff9mapkit.world import extract as X
    import copy
    out = copy.deepcopy(bm)
    out.chan_arrays[X.CH_POS] = [[x, y + dy, z] for x, y, z in bm.chan_arrays[X.CH_POS]]
    return out


def _ground(site, x, z, stack):
    from ff9mapkit.world import pointinfo as PI
    g = PI.point_info(site, x, z, stack=stack, landmark=False)["ground"]
    return g


def build():
    from ff9mapkit import config
    from ff9mapkit.world import extract as X, forms, mesh as M, render as R
    game = Path(config.find_game_path(None))
    stack_names = [p.name for p in R.game_stack(game)]
    own = X.block_parts(disc=1, game=game)
    world = game / "FF9CustomMap-world"
    overridden = {(int(a), int(b)) for f in game.glob("*/FF9_Data/WorldMap/Disc1/0_1/r*/Block*")
                  for a, b in [re.findall(r"\[(\d+)\]", f.name)[:2]]}
    switchable = set(forms.SWITCHABLE)
    bare = R.RenderSite(cells=(), disc=1, game=game, stack=())
    picks = []
    for (bx, by), parts in sorted(own.items()):
        if "object" in parts or (bx, by) in overridden or (bx, by) in switchable:
            continue
        if any(math.dist((bx, by), (px, py)) < 3 for px, py, *_ in picks):
            continue
        cx, cz = bx * 64 + 32.37, -(by * 64 + 32.41)
        if math.dist((cx, cz), ARRIVAL) < 320:
            continue
        g = _ground(bare, cx, cz, [])
        if g["part"] == "Terrain" and g.get("walkable") and not g.get("canopy") and not g.get("stacked"):
            picks.append((bx, by, cx, cz))
        if len(picks) == 2:
            break
    # C: an FF9CustomMap-world island cell with a walkable Terrain point
    one_world = R.RenderSite(cells=(), disc=1, game=game, mod_root=world)
    c_pick = None
    for f in sorted((world / "FF9_Data/WorldMap/Disc1/0_1").rglob("Block*Terrain.ff9mesh")):
        bx, by = map(int, re.findall(r"\[(\d+)\]", f.name)[:2])
        if math.dist((bx * 64 + 32, -(by * 64 + 32)), ARRIVAL) < 320:
            continue
        for i, j in ((4, 4), (3, 4), (4, 3), (5, 4), (4, 5)):
            x, z = bx * 64 + i * 8 + 0.37, -(by * 64 + j * 8 + 0.41)
            g = _ground(one_world, x, z, [])
            if g["part"] == "Terrain" and g.get("walkable") and not g.get("canopy") and not g.get("stacked"):
                c_pick = (bx, by, x, z)
                break
        if c_pick:
            break
    assert len(picks) == 2 and c_pick, (picks, c_pick)
    if OUT.exists():
        shutil.rmtree(OUT)
    hi, lo = OUT / HI, OUT / LO
    (ax, ay, _, _), (bx_, by_, _, _) = picks
    stock_a = X.read_block(ax, ay, disc=1, part="terrain", game=game)
    stock_b = X.read_block(bx_, by_, disc=1, part="terrain", game=game)
    for root, (x, y), bm in ((lo, (ax, ay), _raised(stock_a, 1.5)), (hi, (ax, ay), _raised(stock_a, 3.0)),
                             (lo, (bx_, by_), _raised(stock_b, 1.5))):
        p = _cell_file(root, x, y)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(M.ff9mesh_bytes(bm))
    refused = bytearray(M.ff9mesh_bytes(_raised(stock_b, 1.5)))
    refused[4:8] = (2).to_bytes(4, "little")                         # version 2: ReadMesh throws -> stock
    p = _cell_file(hi, bx_, by_)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(bytes(refused))
    cbx, cby, cx, cz = c_pick
    c_mesh = M.blockmesh_from_ff9mesh(_cell_file(world, cbx, cby), disc=1, x=cbx, y=cby, part="terrain")
    p = _cell_file(hi, cbx, cby)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(M.ff9mesh_bytes(_raised(c_mesh, 1.5)))
    for root in (hi, lo):                                            # never mod-shaped beyond what the test needs
        assert not (root / "ModDescription.xml").exists()

    # the predictions: the stacked site resolves exactly as the installed labs will (same files, same order)
    stacked_roots = (hi, lo) + tuple(game / n for n in stack_names)
    names = [HI, LO] + stack_names
    stacked = R.RenderSite(cells=(), disc=1, game=game, stack=stacked_roots)
    wrong = {"A": R.RenderSite(cells=(), disc=1, game=game, stack=(lo,) + tuple(game / n for n in stack_names)),
             "B": R.RenderSite(cells=(), disc=1, game=game, stack=(lo,) + tuple(game / n for n in stack_names)),
             "C": one_world}
    targets = []
    for key, (x, z) in (("A", picks[0][2:]), ("B", picks[1][2:]), ("C", (cx, cz)), ("K", CONTROL[1:])):
        g = _ground(stacked, x, z, names)
        row = {"key": key, "x": round(x, 2), "z": round(z, 2), "predict_y": g["stand_y"], "part": g["part"],
               "block": (math.floor(x / 64), math.floor(-z / 64))}
        if key in wrong:
            w = _ground(wrong[key], x, z, names)
            row["wrong_rule_y"] = w["stand_y"]
            row["separation"] = abs(g["stand_y"] - w["stand_y"])
        targets.append(row)
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "stack": names, "tolerance": TOL, "targets": targets,
           "files": {str(p.relative_to(OUT)): sha(p)[:16] for p in sorted(OUT.rglob("*.ff9mesh"))}}
    PREP.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for t in targets:
        print(f"  {t['key']} block {t['block']} at {t['x']}, {t['z']}: predict y {t['predict_y']:.3f}"
              + (f"  (wrong rule {t['wrong_rule_y']:.3f}, separation {t['separation']:.2f})" if "separation" in t else ""))
    bad = [t["key"] for t in targets if t.get("separation", 9) < 1.0]
    assert not bad, f"predictions cannot tell the rules apart at {bad}"
    print(f"-> {PREP}")


def _game_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq FF9.exe"], capture_output=True, text=True).stdout
    return "FF9.exe" in out


def install():
    if _game_running():
        raise SystemExit("FF9 is running: close it first (the ini is read at launch)")
    for n in (HI, LO):
        if (GAME / n).exists():
            raise SystemExit(f"{GAME / n} already exists: not touching it")
    raw = INI.read_bytes()
    m = re.search(rb'^(\s*FolderNames\s*=\s*)(.+)$', raw, re.M)
    if not m or HI.encode() in m.group(2) or LO.encode() in m.group(2):
        raise SystemExit(f"FolderNames missing or already holds a lab: {m and m.group(2)!r}")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    MAIN_BACKUPS.mkdir(parents=True, exist_ok=True)
    bak = MAIN_BACKUPS / f"Memoria.ini.{stamp}.stack-lab"
    shutil.copyfile(INI, bak)
    assert sha(bak) == sha(INI)
    for n in (HI, LO):
        shutil.copytree(OUT / n, GAME / n)
    INI.write_bytes(raw[:m.start(2)] + f'"{HI}", "{LO}", '.encode() + raw[m.start(2):])
    STATE.write_text(json.dumps({"backup": str(bak), "ini_sha": sha(bak), "installed_at": stamp}, indent=1),
                     encoding="utf-8")
    print(f"installed {HI}, {LO} first in FolderNames; ini backed up to {bak}")


def uninstall(run_dir: Path):
    if _game_running():
        raise SystemExit("FF9 is running: close it first")
    st = json.loads(STATE.read_text(encoding="utf-8"))
    shutil.copyfile(st["backup"], INI)
    if sha(INI) != st["ini_sha"]:
        raise SystemExit(f"Memoria.ini restore MISMATCH: {sha(INI)} vs {st['ini_sha']}")
    run_dir.mkdir(parents=True, exist_ok=True)
    for n in (HI, LO):
        if (GAME / n).exists():
            shutil.move(str(GAME / n), str(run_dir / f"{n}.moved"))
    STATE.unlink()
    print(f"uninstalled: Memoria.ini restored byte-exact (sha {st['ini_sha'][:16]}); labs moved into {run_dir}")


def _sh(argv, timeout):
    print("$", " ".join(str(a) for a in argv), flush=True)
    r = subprocess.run([str(a) for a in argv], cwd=REPO, capture_output=True, text=True, timeout=timeout)
    print(r.stdout[-2000:], flush=True)
    if r.returncode:
        print(r.stderr[-2000:], flush=True)
    return r


def run():
    prep = json.loads(PREP.read_text(encoding="utf-8"))
    py = sys.executable
    log = GAME / "Memoria.log"
    run_dir = REPO / ".harness-runs" / f"{time.strftime('%Y%m%d-%H%M%S')}-stack-lab"
    rec = {"prep_t": prep["t"], "targets": []}
    install()
    try:
        r = _sh([py, "tools/play.py", HERE / "a1_reach.py", "--keep-open", "--label", "stack-reach"], 900)
        rec["reach_rc"] = r.returncode
        if r.returncode == 0:
            for t in prep["targets"]:
                r = _sh([py, "tools/world_teleport.py", f"{t['x']:.2f}", f"{t['z']:.2f}", "--shot",
                         f"stack-{t['key']}"], 300)
                back = json.loads(r.stdout.strip().splitlines()[-1])
                row = dict(t, back=back)
                if back["ok"] and back["world_y"] is not None:
                    row["dy"] = back["world_y"] - t["predict_y"]
                    row["S1"] = abs(row["dy"]) <= TOL
                else:
                    row["S1"] = False
                rec["targets"].append(row)
        _sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "stack-quit"], 300)
        for _ in range(30):
            if not _game_running():
                break
            time.sleep(1)
        text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
        rec["log"] = {}
        for t in prep["targets"]:
            if t["key"] == "K":
                continue
            bx, by = t["block"]
            key = f"Block[{bx}][{by}] Terrain"
            lines = [ln.strip() for ln in text.splitlines() if key in ln and "WorldMeshOverride" in ln]
            rec["log"][t["key"]] = lines[-4:]
        rec["S2"] = {
            "A": any("loaded" in ln and HI in ln for ln in rec["log"].get("A", ())),
            "C": any("loaded" in ln and HI in ln for ln in rec["log"].get("C", ())),
            "B": any("failed to read" in ln and HI in ln for ln in rec["log"].get("B", ())),
        }
    finally:
        uninstall(run_dir)
        RESULT.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for row in rec["targets"]:
        b = row["back"]
        print(f"{row['key']}: S1 {row['S1']}  y {b.get('world_y')} vs predicted {row['predict_y']:.3f}"
              + (f" (wrong rule {row['wrong_rule_y']:.3f})" if "wrong_rule_y" in row else ""))
    print("S2", rec.get("S2"))
    print(f"-> {RESULT}")


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["build"]:
        build()
    elif cmd == ["run"]:
        run()
    elif cmd == ["uninstall"] and len(sys.argv) == 3:
        uninstall(Path(sys.argv[2]))
    else:
        raise SystemExit(__doc__)
