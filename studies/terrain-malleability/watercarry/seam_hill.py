"""The hill's crack gate on the river island: does `world-hill` seat beside the carried bank once its crack gate judges
only the edges the lift opens? (RUNG5.md "The gates measure the carve": the forest's annulus gate and the census were
made to subtract the island's own state; `world-hill`'s crack gate -- once-edges within radius + 4 -- stayed absolute.)

Offline, into scratch folders OUTSIDE the install. Nothing in the game is written; the install is read for stock
donors only.
  1. `world-river --at 512,128 --skip-mirror` into scratch/river, the stack read narrowed as in seam_forest.py.
  2. The hill on that island, in-process as the CLI runs it (read at reach max(96, r + 10), build_hill, census_gate
     with the deployed stack), every log line kept, for:
       a. center (31,-826): 20.5u from the island's own open edge at (10.84,-829.54), the grass crest over the
          carried stock bank (topo 62) -- inside the gate's radius + 4 = 22u, outside the 18u lift
       b. center (30,-824): the lawful centre nearest that edge (13 open edges in the window)
       c. near (49,-824): the default scan, for reference (its snap is clear of the bank)
     For each, beside the gate's verdict, the OLD construction's (every once-edge within r + 4 after the lift,
     absolute) and the inherited edges' midpoints.
  3. `world-hill --center 31,-826 --dry-run` through the CLI on scratch/river.
  4. The recipe `[[river]]` + `[[hill]] center = [31, -826]` through `world-fuse` into scratch/fuse: the files the
     hill step wrote.
RUN:  py studies/terrain-malleability/watercarry/seam_hill.py [SCRATCH_DIR]   (-> out/seam_hill.json)
"""
from __future__ import annotations

import io
import json
import math
import shutil
import sys
import tempfile
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit import cli, config  # noqa: E402
from ff9mapkit.world import interior as IN, mesh as M, river as R  # noqa: E402

AT = (512.0, 128.0)
EDGE = (10.84, -829.54)                  # the island's own open edge (seam_forest.py, RUNG5.md)
CASES = (("a_center_31_-826", dict(center=(31.0, -826.0))),
         ("b_center_30_-824", dict(center=(30.0, -824.0))),
         ("c_near_49_-824", dict(near=(49.0, -824.0))))


def old_gate(soup, res, radius=IN.HILL_R, height=IN.HILL_H) -> list:
    """The pre-fix crack gate's hits: every once-edge within radius + 4 of the centre after the lift, absolute
    (midpoints). Each one the gate now passes is also open on the pristine island at the same place."""
    CX, CZ = res["center"]
    gpos, gtris = soup["pos"], soup["tris"]
    lift = [IN.raised_cosine(math.hypot(p[0] - CX, p[2] - CZ), height, radius) for p in gpos]
    P = [[p[0], p[1] + lift[i], p[2]] if lift[i] > 0 else p for i, p in enumerate(gpos)]
    eu = Counter()
    for t in gtris:
        cx, cz = sum(gpos[i][0] for i in t) / 3, sum(gpos[i][2] for i in t) / 3
        if math.hypot(cx - CX, cz - CZ) > radius + 8:
            continue
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu[tuple(sorted((IN.kk3(P[t[a]]), IN.kk3(P[t[b]]))))] += 1
    mids = [((e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2) for e, n in eu.items() if n == 1]
    return sorted((round(x, 2), round(z, 2)) for x, z in mids if math.hypot(x - CX, z - CZ) < radius + 4)


def hill_case(mod: str, loc: dict) -> dict:
    lines = []
    pt = loc.get("center") or loc["near"]
    out = {"loc": {k: list(v) for k, v in loc.items()}}
    blocks = IN.read_deployed_blocks(mod, near=pt, reach=max(96.0, IN.HILL_R + 10.0))
    soup = IN.soup_from_blocks(blocks)
    try:
        res = IN.build_hill(soup, log=lines.append, **{k: loc.get(k) for k in ("center", "near")})
        out.update(center=list(res["center"]), report=res["report"],
                   edge_dist=round(math.hypot(res["center"][0] - EDGE[0], res["center"][1] - EDGE[1]), 2),
                   old_gate_once=old_gate(soup, res))
        out["edge_in_old_hits"] = list(EDGE) in [list(m) for m in out["old_gate_once"]]
        IN.census_gate(res["changed"], baseline=blocks, log=lines.append, stack=IN.read_deployed_stack(mod, blocks))
        out.update(ok=True, changed=[f"{bx},{by} -> Block[{M.wrap_block_col(bx)}][{by}]"
                                     for bx, by in sorted(res["changed"])])
    except ValueError as e:
        out.update(ok=False, error=str(e))
    out["log"] = lines
    return out


def main():
    scratch = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="ff9-seam-hill-"))
    game = config.find_game_path(None)
    assert not scratch.resolve().is_relative_to(game.resolve()), "scratch must sit outside the install"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    A, C = scratch / "river", scratch / "fuse"
    R.stack_folders = lambda game=None: []                       # the stack gate narrowed (docstring)
    rep = {"scratch": str(scratch), "at": AT}

    buf = io.StringIO()
    with redirect_stdout(buf):
        rep["river_rc"] = cli.main(["world-river", "--mod-folder", str(A), "--at", f"{AT[0]:g},{AT[1]:g}",
                                    "--skip-mirror"])
    if rep["river_rc"] != 0:
        rep["river_out"] = buf.getvalue()[-2000:]
    rep["hill"] = {name: hill_case(str(A), loc) for name, loc in CASES}

    buf, err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf), redirect_stderr(err):
        rep["cli_rc"] = cli.main(["world-hill", "--mod-folder", str(A), "--center", "31,-826", "--dry-run",
                                  "--skip-mirror"])
    rep["cli_out"] = (buf.getvalue() + err.getvalue())[-1500:]

    recipe = scratch / "river_hill.toml"
    recipe.write_text(f"[[river]]\nat = [{AT[0]:g}, {AT[1]:g}]\n\n[[hill]]\ncenter = [31, -826]\n", encoding="utf-8")
    buf = io.StringIO()
    with redirect_stdout(buf):
        rep["fuse_rc"] = cli.main(["world-fuse", str(recipe), "--mod-folder", str(C), "--skip-mirror"])
    man = C / "FF9_Data" / "WorldMap" / "world_manifest.json"
    entries = json.loads(man.read_text(encoding="utf-8"))["entries"] if man.is_file() else []
    rep["fuse"] = {"steps": [(e["table"], len(e["files"])) for e in entries],
                   "hill_files": sorted(Path(f).as_posix().split("WorldMap/")[-1] for e in entries
                                        if e["table"].startswith("hill") for f in e["files"])}
    rep["fuse_out"] = buf.getvalue()[-3000:]

    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "seam_hill.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main()
