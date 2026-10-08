"""SCORE an r3_session run's override loads: which lab files each world load bound (Memoria.log, archived in the run
dir). A world load logs one `[WorldMeshOverride] loaded '<key>' from <path>` line per bound override, all within a
second or two; loads are split on a gap of more than 4 s between such lines.

Run:  py studies/terrain-malleability/ingame/r3_post.py .harness-runs/<stamp>-r3-<phase>
Writes <run dir>/r3_post.json and prints, per load, the lab files it bound.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

LINE = re.compile(r"^(\d\d\.\d\d\.\d{4} \d\d:\d\d:\d\d) \|M\| \[WorldMeshOverride\] loaded '([^']+)' from (.+)$")


def loads(log: Path) -> list:
    out, last = [], None
    for raw in log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = LINE.match(raw.strip())
        if not m:
            continue
        t = datetime.strptime(m.group(1), "%d.%m.%Y %H:%M:%S")
        # a new load: a gap, or a key the current load already bound (two loads 6 s apart merged on gap alone)
        if last is None or (t - last).total_seconds() > 4 or m.group(2) in out[-1]["keys"]:
            out.append({"t": m.group(1), "lines": 0, "lab": [], "keys": set()})
        last = t
        out[-1]["keys"].add(m.group(2))
        out[-1]["lines"] += 1
        if "FF9CustomMap-lab" in m.group(3):
            out[-1]["lab"].append(m.group(2))
    for ld in out:
        del ld["keys"]
    return out


def main():
    run = Path(sys.argv[1])
    logs = sorted(run.glob("Memoria*.log"))
    if not logs:
        raise SystemExit(f"no Memoria.log in {run}")
    res = {"run": str(run), "loads": loads(logs[0])}
    for i, ld in enumerate(res["loads"]):
        print(f"load {i} at {ld['t']}: {ld['lines']} override lines, lab: {ld['lab'] or 'none'}")
    (run / "r3_post.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
