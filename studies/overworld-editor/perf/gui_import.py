"""gui lane, probe 1: what the World tab's modules cost to import, and WHEN (Workspace start vs a first click).

    py studies/overworld-editor/perf/gui_import.py [runs]

Each scenario is a FRESH interpreter (`py -X importtime -c ...`) so nothing is warm in sys.modules; the disk cache is
warm after the first run (the min is the headline). Scenarios:
  shell      -- `import ff9mapkit.workspace.shell` (Workspace start): the worlddoc node's cumulative is what the World
                tab adds to start at that point of the shell's import order (modules imported earlier are not its).
  lazy_3d    -- after the shell: the imports the first "3D view" click runs ON THE GUI THREAD (worldview3d, worldrecipe,
                and what they pull: OpenGL wrappers, numpy, world.render ...).
  lazy_<card>-- after the shell + the 3D imports: a card's first open (its module + its world/*edit module).
Evidence: out/perf/gui/gui_import.json.
"""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gui_common as C                                                # noqa: E402

PIN = (f"import sys; sys.path.insert(0, r'{C.KIT}'); import ff9mapkit, pathlib; "
       f"assert pathlib.Path(ff9mapkit.__file__).resolve().is_relative_to(pathlib.Path(r'{C.KIT}').resolve()); ")
SHELL = "import ff9mapkit.workspace.shell; "
LAZY3D = ("from ff9mapkit.workspace.worldview3d import WorldView3DPanel; "
          "from ff9mapkit.workspace.worldrecipe import RecipeBar; ")
CARDS = {
    "forest": "from ff9mapkit.workspace.worldforest import ForestTool; import ff9mapkit.world.forestedit",
    "mountain": "from ff9mapkit.workspace.worldmountain import MountainTool; import ff9mapkit.world.mountainedit",
    "coast": "from ff9mapkit.workspace.worldcoast import CoastTool; import ff9mapkit.world.coastedit",
    "sink": "from ff9mapkit.workspace.worldsink import SinkTool; import ff9mapkit.world.sinkedit",
    "island": "from ff9mapkit.workspace.worldisland import IslandTool; import ff9mapkit.world.islandedit",
}


# THIS AGENT SHELL SETS PYTHONDONTWRITEBYTECODE=1 (not the user's env: User/Machine scope is unset), so every stale
# .pyc in the worktree is recompiled on EVERY import (interior.py: 117 ms of compile). The user's Workspace writes its
# .pyc once. Measure the user's steady state: bytecode on, but cached under OUR out dir (PYTHONPYCACHEPREFIX), never
# into the package's __pycache__; one untimed warm-up run per scenario fills it.
import os                                                             # noqa: E402
ENV = dict(os.environ)
ENV.pop("PYTHONDONTWRITEBYTECODE", None)
ENV["PYTHONPYCACHEPREFIX"] = str(C.OUT / "pycache")


def run(code):
    """(wall seconds of the timed statement measured in-process, {module: (self_us, cum_us)} for it)."""
    pre, timed = code
    src = (PIN + pre + "import time as _t; _a=_t.perf_counter(); " + timed +
           "; print('WALL', _t.perf_counter()-_a)")
    # importtime prints every import; a sentinel import just before the timed statement splits the pre-imports'
    # lines from the timed statement's.
    src = src.replace("import time as _t;", "import time as _t; import tabnanny as _gui_sentinel;", 1)
    r = subprocess.run([sys.executable, "-X", "importtime", "-c", src], capture_output=True, text=True,
                       cwd=str(C.KIT), env=ENV)
    if r.returncode != 0:
        raise SystemExit(r.stderr[-3000:])
    wall = float(re.search(r"WALL ([0-9.e-]+)", r.stdout).group(1))
    lines = r.stderr.splitlines()
    # keep the lines after the sentinel's own line (tabnanny: never imported by the kit; if it were, the marker is
    # absent and we keep all lines -- reported as marker_found False)
    mark = next((i for i, ln in enumerate(lines) if ln.rstrip().endswith("| tabnanny")), None)
    keep = lines[mark + 1:] if mark is not None else lines
    mods = {}
    for ln in keep:
        m = re.match(r"import time:\s+(\d+) \|\s+(\d+) \| (\s*)(\S+)", ln)
        if m:
            mods[m.group(4)] = (int(m.group(1)), int(m.group(2)), len(m.group(3)) // 2)
    return wall, mods, mark is not None


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    scen = {"shell": ("", "import ff9mapkit.workspace.shell"),
            "lazy_3d": (SHELL, LAZY3D.rstrip("; "))}
    for k, v in CARDS.items():
        scen[f"lazy_{k}"] = (SHELL + LAZY3D, v)
    out = {"python": sys.version, "runs": runs, "pycache_prefix": ENV["PYTHONPYCACHEPREFIX"],
           "note": "bytecode cached (user steady state); one warm-up run per scenario discarded", "scenarios": {}}
    for name, code in scen.items():
        walls, last = [], None
        run(code)                                                     # warm-up: fills the pyc prefix, untimed
        for _ in range(runs):
            w, mods, marked = run(code)
            walls.append(w)
            last = (mods, marked)
        mods, marked = last
        top_level = sorted(((n, s, c) for n, (s, c, d) in mods.items() if d == 0), key=lambda t: -t[2])
        by_cum = sorted(((n, s, c) for n, (s, c, d) in mods.items()), key=lambda t: -t[2])[:25]
        by_self = sorted(((n, s, c) for n, (s, c, d) in mods.items()), key=lambda t: -t[1])[:25]
        rec = {"wall": C.stats(walls), "marker_found": marked, "n_new_modules": len(mods),
               "top_level_cum_us": top_level[:15], "top_cum_us": by_cum, "top_self_us": by_self}
        if name == "shell":
            for key in ("ff9mapkit.workspace.worlddoc", "ff9mapkit.workspace.worldscan", "ff9mapkit.world.discmirror",
                        "ff9mapkit.world.mesh", "numpy", "PySide6.QtOpenGL"):
                rec.setdefault("nodes_us", {})[key] = mods.get(key)
        out["scenarios"][name] = rec
        print(f"{name:16s} min {min(walls):.3f}s median {statistics.median(walls):.3f}s  new modules {len(mods)}")
        for n, s, c in top_level[:6]:
            print(f"      {c / 1e6:7.3f}s cum  {n}")
    C.dump("gui_import.json", out)


if __name__ == "__main__":
    main()
