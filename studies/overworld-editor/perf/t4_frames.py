"""Tier 4 re-measure + identity: the GUI-thread frames as shipped against the code before them (PERF.md 6).

    py studies/overworld-editor/perf/t4_frames.py preview [reps]     the forest drag's footprint_preview
    py studies/overworld-editor/perf/t4_frames.py ground [reps]      the game camera's ground probe

OLD is the module as it was at OLD_REV (git show), exec'd as its own module object beside the package (it imports the
package's other modules); NEW is the package.
preview: the gui lane's 247 placements (a lattice round the forest spot + every island block's centre) on the lane's
         draft of FF9CustomMap-world, old == new for every one; per-call time.
ground:  the whole map as the 3D view draws it (the game's stack), 1,868 probe points (random, a walk, the 16u
         grid lines), old ground_y == new for every one; per-call time, the grid build.
Evidence: out/perf/t4/t4_<mode>.json
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402  (pins the worktree package)

OUT = HERE.parent / "out" / "perf" / "t4"
OLD_REV = "1dce6836"
FOREST_SPOT, FOREST_DONOR = (1400.0, -460.0), (13, 15)


def old_module(rel, package):
    src = subprocess.run(["git", "show", f"{OLD_REV}:ff9mapkit/ff9mapkit/{rel}"], cwd=str(C.WT), capture_output=True,
                         text=True, encoding="utf-8", check=True).stdout
    mod = types.ModuleType(f"{package}._old_{Path(rel).stem}")
    mod.__file__ = str(C.KIT / "ff9mapkit" / rel)
    mod.__package__ = package
    sys.modules[mod.__name__] = mod                                   # (dataclasses look their module up there)
    exec(compile(src, mod.__file__, "exec"), mod.__dict__)
    return mod


def preview(reps):
    from ff9mapkit.world import forestedit as FE
    from ff9mapkit.world import interior as IN
    from ff9mapkit.world import draft as D
    from ff9mapkit.workspace import worldforest as WF
    OLD = old_module("world/forestedit.py", "ff9mapkit.world")
    draft = D.draft_path(C.SOURCE, root=C.OUT / "drafts")
    assert D.read_meta(draft) is not None, draft
    near, reach = WF.WHOLE_MAP
    ix = FE.SoupIndex(IN.soup_from_blocks(IN.read_deployed_blocks(str(draft), near=near, reach=reach, game=C.GAME)))
    ol = FE.outline(FOREST_DONOR, game=C.GAME)
    pts = [(FOREST_SPOT[0] + dx, FOREST_SPOT[1] + dz) for dx in range(-40, 41, 8) for dz in range(-40, 41, 8)]
    pts += [((bx + 0.5) * 64.0, -(by + 0.5) * 64.0) for bx, by in sorted(ix.blocks)]
    rims = [FE.placed(ol, p, ground_y=0.0)[1][:, [0, 2]] for p in pts]
    same, kinds = 0, {}
    for rim in rims:
        a, b = OLD.footprint_preview(ix, rim), FE.footprint_preview(ix, rim)
        same += a == b
        k = a["why"] or ("ok" if a["ok"] else "?")
        kinds[k] = kinds.get(k, 0) + 1
    times = {"old": [], "new": []}
    for _ in range(reps):
        for arm, fn in (("old", OLD.footprint_preview), ("new", FE.footprint_preview)):
            t = time.perf_counter()
            for rim in rims:
                fn(ix, rim)
            times[arm].append((time.perf_counter() - t) / len(rims) * 1e3)
    out = {"placements": len(rims), "identical": same, "kinds": kinds,
           "per_call_ms_min": {a: round(min(v), 3) for a, v in times.items()}}
    print(json.dumps(out))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t4_preview.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


def ground(reps):
    import numpy as np
    from ff9mapkit.workspace import worldview3d as V
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import render as R
    OLD = old_module("workspace/worldview3d.py", "ff9mapkit.workspace")
    cells = tuple((bx, by) for by in range(M.GRID_ROWS) for bx in range(M.GRID_COLS))
    packed, _tex = V.load_scene(R.RenderSite(cells=cells, disc=1, game=C.GAME, stack=R.game_stack(C.GAME)))
    rng = np.random.default_rng(9)
    probe = [(float(x), float(z)) for x, z in zip(rng.uniform(-150, 1700, 1500), rng.uniform(-1300, 20, 1500))]
    probe += [(FOREST_SPOT[0] + 0.37 * k, FOREST_SPOT[1] - 0.29 * k) for k in range(200)]
    probe += [(16.0 * i, -16.0 * j) for i in range(0, 96, 7) for j in range(0, 80, 7)]
    t = time.perf_counter()
    packed.build_ground_grid()                                        # (the panel builds it on a worker)
    build = time.perf_counter() - t
    a = [OLD.ground_y(packed, x, z) for x, z in probe]
    b = [V.ground_y(packed, x, z) for x, z in probe]
    times = {"old": [], "new": []}
    sub = probe[:200]
    for _ in range(reps):
        for arm, fn in (("old", OLD.ground_y), ("new", V.ground_y)):
            t = time.perf_counter()
            for x, z in sub:
                fn(packed, x, z)
            times[arm].append((time.perf_counter() - t) / len(sub) * 1e3)
    out = {"points": len(probe), "with_ground": sum(v is not None for v in a), "identical": a == b,
           "first_call_with_build_s": round(build, 3),
           "per_call_ms_min": {k: round(min(v), 4) for k, v in times.items()}}
    print(json.dumps(out))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t4_ground.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    mode = sys.argv[1]
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    {"preview": preview, "ground": ground}[mode](reps)
