"""HOLES.md H2 + H4: a sweep of world-island mints, each scanned for sea holes and hashed file by file.

Every config mints through the CLI (all of world-island's gates) into a temp folder at the open window round 23 used
(blocks (19-23, 0-2)); a mint its own gates refuse is recorded as such and skipped. Per mint: hole_scan's uncovered
points, and the sha256 of every written file, so a run before the fix and one after can be compared: holes must fall
to 0 (H2), and only Sea4 files may differ (H4).
RUN:  py studies/terrain-malleability/canopystep/hole_census.py OUT.json        (then again after; compare with --vs)
      py studies/terrain-malleability/canopystep/hole_census.py OUT.json --vs BEFORE.json
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import hole_scan as H  # noqa: E402

CONFIGS = [(g, c, r, l, s) for g in ("grass", "desert") for (c, r) in (("1380,-96", 40), ("1380,-96", 55),
                                                                         ("1380,-96", 66), ("1408,-96", 84))
           for l in (1, 2) for s in (42, 7)]


def one(cfg):
    g, c, r, l, s = cfg
    tmp = Path(tempfile.mkdtemp(prefix="ff9_holecensus_"))
    key = f"{g} c{c} r{r} L{l} s{s}"
    try:
        p = subprocess.run([sys.executable, "-m", "ff9mapkit", "world-island", "--mod-folder", str(tmp / "m"),
                            "--ground", g, "--center", c, "--radius", str(r), "--lobes", str(l), "--patches", "0",
                            "--seed", str(s), "--skip-mirror"], cwd=ROOT / "ff9mapkit", capture_output=True, text=True)
        if p.returncode:
            return key, {"refused": (p.stdout + p.stderr).strip().splitlines()[-1][:120]}
        rep = H.scan(tmp / "m")
        root = tmp / "m" / "FF9_Data"
        files = {f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
                 for f in root.rglob("*") if f.is_file()}
        return key, {"holes": rep["holes"], "clusters": len(rep["clusters"]), "files": files}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    out_path = Path(sys.argv[1])
    with ProcessPoolExecutor(max_workers=6) as ex:
        rows = dict(ex.map(one, CONFIGS))
    out_path.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    minted = {k: v for k, v in rows.items() if "holes" in v}
    print(f"{len(minted)}/{len(rows)} mints; with holes: "
          f"{ {k: v['holes'] for k, v in minted.items() if v['holes']} }")
    if "--vs" in sys.argv:
        before = json.loads(Path(sys.argv[sys.argv.index("--vs") + 1]).read_text(encoding="utf-8"))
        changed_kinds, bad = {}, []
        for k, v in minted.items():
            b = before.get(k, {})
            if "files" not in b:
                bad.append(f"{k}: not minted before")
                continue
            diff = sorted(f for f in set(v["files"]) | set(b["files"]) if v["files"].get(f) != b["files"].get(f))
            for f in diff:
                part = f.rsplit(" ", 1)[-1] if " " in f else f
                changed_kinds[part] = changed_kinds.get(part, 0) + 1
            print(f"   {k}: holes {b['holes']} -> {v['holes']}; {len(diff)} file(s) differ "
                  f"{[d.rsplit('/', 1)[-1] for d in diff][:4]}")
        print("changed files by part:", changed_kinds, "| problems:", bad)


if __name__ == "__main__":
    main()
