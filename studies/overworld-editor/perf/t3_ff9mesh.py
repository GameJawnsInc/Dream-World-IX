"""c8 re-measure + identity: mesh.read_ff9mesh as shipped against the code before it, on every deployed .ff9mesh of
the live FF9CustomMap-world (read only) and of the jobs lane's draft (PERF.md 5).

    py studies/overworld-editor/perf/t3_ff9mesh.py

Every file: OLD read_ff9mesh (mesh.py of OLD_REV, exec'd beside the package) and NEW -> the same dict, every float's
bit pattern equal. Then the card's island read (interior.read_deployed_blocks over the draft) timed with each.
Evidence: out/perf/t3/t3_ff9mesh.json
"""
from __future__ import annotations

import json
import struct
import subprocess
import sys
import time
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jobs_common as J                                               # noqa: E402  (pins the worktree package)

OUT = HERE.parent / "out" / "perf" / "t3"
OLD_REV = "26b7eb7a"


def old_mesh():
    rel = "ff9mapkit/ff9mapkit/world/mesh.py"
    src = subprocess.run(["git", "show", f"{OLD_REV}:{rel}"], cwd=str(J.KIT.parent), capture_output=True, text=True,
                         encoding="utf-8", check=True).stdout
    mod = types.ModuleType("ff9mapkit.world._old_mesh")
    mod.__file__ = str(J.KIT.parent / rel)
    mod.__package__ = "ff9mapkit.world"
    sys.modules[mod.__name__] = mod
    exec(compile(src, mod.__file__, "exec"), mod.__dict__)
    return mod


def bits(rows):
    return None if rows is None else [[struct.pack("<d", v) for v in r] for r in rows]


def main():
    from ff9mapkit.world import interior as IN
    from ff9mapkit.world import mesh as NEW
    from ff9mapkit.workspace import worldforest as WF
    OLD = old_mesh()
    out = {}
    for label, root in (("live", J.SOURCE), ("draft", J.draft())):
        files = [p for p in (root / "FF9_Data" / "WorldMap").rglob("*.ff9mesh") if ".bak-" not in p.name]
        same = 0
        for p in files:
            a, b = OLD.read_ff9mesh(p), NEW.read_ff9mesh(p)
            same += all(bits(a[k]) == bits(b[k]) for k in ("verts", "normals", "uvs", "tangents")) and \
                all(a[k] == b[k] for k in ("version", "vcount", "indices"))
        out[label] = {"files": len(files), "identical": same}
        print(label, out[label], flush=True)
    near, reach = WF.WHOLE_MAP
    times = {"old": [], "new": []}
    real = NEW.read_ff9mesh
    for _ in range(3):
        for arm in ("old", "new"):
            NEW.read_ff9mesh = OLD.read_ff9mesh if arm == "old" else real
            t = time.perf_counter()
            IN.read_deployed_blocks(str(J.draft()), near=near, reach=reach, game=J.GAME)
            times[arm].append(round(time.perf_counter() - t, 3))
    NEW.read_ff9mesh = real
    out["read_deployed_blocks_s"] = times
    out["min"] = {a: min(v) for a, v in times.items()}
    print(json.dumps(out))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t3_ff9mesh.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
