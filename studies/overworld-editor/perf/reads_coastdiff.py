"""reads_coastdiff: why a cold coast window scan differs from the shared cache's json for the same block (read only).
    py studies/overworld-editor/perf/reads_coastdiff.py 14 1"""
import json, sys, threading, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import GAME, OUT, dump  # noqa: E402
from ff9mapkit.world import coastedit as CE, coastscan as CS  # noqa: E402

cell = (int(sys.argv[1]), int(sys.argv[2]))
p = CE._cache_file(GAME, 1, cell)
ref = json.loads(p.read_text(encoding="utf-8"))
now = CE._jsonable(CS.scan_block(*cell, disc=1, game=GAME))
now = json.loads(json.dumps(now))
diff = []
def walk(a, b, path):
    if type(a) != type(b):
        diff.append((path, repr(a)[:120], repr(b)[:120])); return
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            walk(a.get(k), b.get(k), path + "/" + str(k))
    elif isinstance(a, list):
        if len(a) != len(b):
            diff.append((path, f"len {len(a)}", f"len {len(b)}"))
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]")
    elif a != b:
        diff.append((path, repr(a)[:120], repr(b)[:120]))
walk(ref["windows"], now, "")
print("cache file", p, "mtime", p.stat().st_mtime)
print("diffs", len(diff))
for d in diff[:20]: print(d)
# does the scan run on a worker thread at all?
err = []
def run():
    try:
        CS.scan_block(*cell, disc=1, game=GAME)
    except Exception:
        err.append(traceback.format_exc())
t = threading.Thread(target=run); t.start(); t.join()
print("thread error:", err[0][-800:] if err else None)
dump(f"reads_coastdiff_{cell[0]}_{cell[1]}.json", {"cell": cell, "diffs": diff[:200], "n": len(diff),
     "thread_error": err[0][-2000:] if err else None})
