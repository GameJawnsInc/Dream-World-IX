"""The relief verbs' SEAM-WRAP rung, measured on the river island: does the forest at (36, -820) seat once the
read can cross the world's x seam? (RUNG5.md "5a and 5b result": with reach 40 the snap found (36, -820) and the
forest geometry gate failed with annulusOnce=1; the default reach 96 refused at the seam.)

Offline, into scratch folders OUTSIDE the install. Nothing in the game is written; the install is read for stock
donors only.
  1. `world-river --at 512,128 --skip-mirror` into scratch/river. The stack read is narrowed to the target folder, as
     in rung5b_identity.py, because the live FF9CustomMap-world holds the live river at 512,128.
  2. The forest on that island, in-process, keeping each gate's log line, for three cases:
       a. near (49,-824), reach 40: the 5b run, whose window stopped at x = 0
       b. near (49,-824), reach 96: the default, which refused at the seam before this rung
       c. center (36,-820), reach 96: the 5b snap, exact
     For each: the read window (unwrapped key -> wrapped file), the snap, the gate line, the census, and on a
     refusal which gate failed and where (the annulus-crack gate's once-edges, by midpoint). Then the same gates on
     the UNTOUCHED island (pristine_checks), to tell the forest's failures from the island's own state.
     Since the gate rung the census runs as the CLI does: on the block's DEPLOYED stack, subtracting what the
     pristine stack already misses (`census_gate(stack=)`), and the annulus gate subtracts the island's own
     open edges; pristine_checks keeps the OLD construction's verdict beside the new one.
  3. The recipe: `[[river]]` + `[[forest]] near = [49, -824]` at the default reach, through `world-fuse` into
     scratch/fuse. Lists the files the forest step wrote (wrapped labels only) and reads the canopy back.
RUN:  py studies/terrain-malleability/watercarry/seam_forest.py [SCRATCH_DIR]   (-> out/seam_forest.json)
"""
from __future__ import annotations

import io
import json
import re
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit import cli, config  # noqa: E402
from ff9mapkit.world import extract as X, interior as IN, mesh as M, river as R  # noqa: E402

AT = (512.0, 128.0)
NEAR = (49.0, -824.0)                    # the river island's roomiest open lawn (the rung-5 recon's r~28 disc)
SNAP_5B = (36.0, -820.0)                 # where the 5b run's reach-40 snap landed
CASES = (("a_near_reach40", dict(near=NEAR), 40.0),
         ("b_near_reach96", dict(near=NEAR), 96.0),
         ("c_center_reach96", dict(center=SNAP_5B), 96.0))
ONCE_BAND = IN.RING_BAND + 2.0           # the annulus-crack gate's capture band (carve_forest)


def forest_case(mod: str, loc: dict, reach: float) -> dict:
    """One carve_forest run on the deployed island, every log line kept, gates named on a refusal."""
    lines, once = [], []
    real_near_poly = IN.near_poly

    def near_poly(px, pz, poly, d):              # records the annulus-crack gate's hits: its band is unique
        hit = real_near_poly(px, pz, poly, d)
        if hit and d == ONCE_BAND:
            once.append((round(px, 3), round(pz, 3)))
        return hit

    pt = loc.get("center") or loc["near"]
    out = {"loc": {k: list(v) for k, v in loc.items()}, "reach": reach}
    IN.near_poly = near_poly
    try:
        blocks = IN.read_deployed_blocks(mod, near=pt, reach=reach)
        out["window"] = {f"{bx},{by}": f"Block[{M.wrap_block_col(bx)}][{by}]" for bx, by in sorted(blocks)}
        soup = IN.soup_from_blocks(blocks)
        res = IN.carve_forest(soup, donor=IN.FOREST_DONOR, log=lines.append, **loc)
        IN.census_gate(res["changed"], probe=(res["center"], 37), baseline=blocks, log=lines.append,
                       stack=IN.read_deployed_stack(mod, blocks))
        out.update(ok=True, center=list(res["center"]), report=res["report"],
                   changed=[f"{bx},{by} -> Block[{M.wrap_block_col(bx)}][{by}]" for bx, by in sorted(res["changed"])])
    except ValueError as e:
        out.update(ok=False, error=str(e), annulus_once_midpoints=once[-8:])
    finally:
        IN.near_poly = real_near_poly
    out["gate_lines"] = [s for s in lines if re.match(r"(placement|gates|perimeter|placement census|probe)", s)]
    return out


def pristine_checks(mod: str, once_at) -> dict:
    """The same gates on the UNTOUCHED river island, to tell the forest's failures from the island's own state:
    census_gate per window block (what every relief verb runs on every block it re-emits), the census of the block's
    whole DEPLOYED stack (Stream/RiverJoint/Beach1/Object/Sea*), and every pristine edge at the annulus gate's hits."""
    from collections import Counter
    from ff9mapkit.world import placement as P
    blocks = IN.read_deployed_blocks(mod, near=NEAR, reach=96.0)
    out = {"census_gate": {}, "census_gate_stack": {}, "deployed_stack_miss": {}, "edges_at_once_hits": {}}
    stack = IN.read_deployed_stack(mod, blocks)
    root = Path(mod) / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    for blk in sorted(blocks):
        key = f"{blk[0]},{blk[1]}"
        said = []
        IN.census_gate({blk: blocks[blk]}, baseline=blocks, stack=stack, log=said.append)
        out["census_gate_stack"][key] = said[-1]
        try:
            IN.census_gate({blk: blocks[blk]}, baseline=blocks, log=lambda *a: None)
            out["census_gate"][key] = "clean"
        except ValueError as e:
            out["census_gate"][key] = str(e)[:200]
            wbx, by = M.wrap_block_col(blk[0]), blk[1]
            parts = {f.name[len(f"Block[{wbx}][{by}] "):-len(".ff9mesh")]: f
                     for f in (root / f"r{by}").glob(f"Block[[]{wbx}[]][[]{by}[]] *.ff9mesh")}
            ml = P.build_meshlist({n: M.blockmesh_from_ff9mesh(f, disc=1, x=wbx, y=by, part=n.lower())
                                   for n, f in parts.items()})
            out["deployed_stack_miss"][key] = {"parts": sorted(parts),
                                               "miss": len(P.census(ml, frame="block_local")["miss"])}
    soup = IN.soup_from_blocks(blocks)
    eu, owner = Counter(), {}
    for ti, t in enumerate(soup["tris"]):
        ks = [IN.kk3(soup["pos"][i]) for i in t]
        topo = X.decode_id(int(round(soup["meta"][ti][1])))["topograph"]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e = tuple(sorted((ks[a], ks[b])))
            eu[e] += 1
            owner.setdefault(e, []).append(topo)
    for mx, mz in once_at:
        hits = [e for e in eu if abs((e[0][0] + e[1][0]) / 2 - mx) < 1e-2 and abs((e[0][2] + e[1][2]) / 2 - mz) < 1e-2]
        out["edges_at_once_hits"][f"{mx},{mz}"] = [{"edge": e, "uses": eu[e], "topos": owner[e]} for e in hits]
    return out


def canopy_cells(mod: Path) -> dict:
    """Topo-37 (canopy) tri count per deployed Terrain file."""
    out = {}
    for p in sorted((mod / "FF9_Data" / "WorldMap" / "Disc1" / "0_1").rglob("Block*Terrain.ff9mesh")):
        m = re.search(r"Block\[(\d+)\]\[(\d+)\]", p.name)
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=int(m[1]), y=int(m[2]))
        tan = bm.chan_arrays[X.CH_TAN]
        n = sum(1 for t in bm.tris if X.decode_id(int(round(tan[t[0]][0])))["topograph"] == 37)
        if n:
            out[p.name] = n
    return out


def main():
    scratch = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="ff9-seam-forest-"))
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
    rep["forest"] = {name: forest_case(str(A), loc, reach) for name, loc, reach in CASES}
    once_at = sorted({tuple(m) for c in rep["forest"].values() for m in c.get("annulus_once_midpoints", [])})
    rep["pristine"] = pristine_checks(str(A), once_at)

    recipe = scratch / "river_forest.toml"
    recipe.write_text(f"[[river]]\nat = [{AT[0]:g}, {AT[1]:g}]\n\n[[forest]]\nnear = [{NEAR[0]:g}, {NEAR[1]:g}]\n",
                      encoding="utf-8")
    buf = io.StringIO()
    with redirect_stdout(buf):
        rep["fuse_rc"] = cli.main(["world-fuse", str(recipe), "--mod-folder", str(C), "--skip-mirror"])
    man = C / "FF9_Data" / "WorldMap" / "world_manifest.json"
    entries = json.loads(man.read_text(encoding="utf-8"))["entries"] if man.is_file() else []
    rep["fuse"] = {"steps": [(e["table"], len(e["files"])) for e in entries],
                   "forest_files": sorted(Path(f).as_posix().split("WorldMap/")[-1] for e in entries
                                          if e["table"].startswith("forest") for f in e["files"]),
                   "dead_labels": sorted(p.name for p in C.rglob("Block[-*")) + sorted(
                       p.name for p in C.rglob("Block[24]*")),
                   "canopy": canopy_cells(C)}
    rep["fuse_out"] = buf.getvalue()[-3000:]

    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "seam_forest.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main()
