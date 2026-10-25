"""Lane jobs: is the slow first snapshot of a fresh draft a FIRST-OPEN cost? Make a fresh draft (out/perf/jobs/fr/,
deleted after), then read every world file at all cells twice, timing each pass; then write the same files to a new
dir twice (fresh names each pass). Same bytes, same OS cache: a first-pass penalty is a per-new-file open cost.

    py studies/overworld-editor/perf/jobs_firstread.py      -> out/perf/jobs/firstread.json
"""
import json, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J
from ff9mapkit.world import draft as D
root = J.OUT / "fr"
if root.exists():
    shutil.rmtree(root)
t = time.perf_counter(); d = D.ensure_draft(J.SOURCE, game=J.GAME, root=root); t_make = time.perf_counter() - t
files = D._cell_files(d, D.all_cells())
res = {"files": len(files), "ensure_draft_s": t_make}
for k in (1, 2, 3):
    t = time.perf_counter()
    for p in files.values():
        p.read_bytes()
    res[f"read_pass{k}_s"] = time.perf_counter() - t
for k in (1, 2):
    dest = root / f"w{k}"
    t = time.perf_counter()
    for rel, p in files.items():
        q = dest / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_bytes(p.read_bytes())
    res[f"write_newnames_pass{k}_s"] = time.perf_counter() - t
    t = time.perf_counter()
    for rel in files:
        (dest / rel).unlink()
    res[f"unlink_pass{k}_s"] = time.perf_counter() - t
print(json.dumps(res))
(J.OUT / "firstread.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
shutil.rmtree(root, ignore_errors=True)
