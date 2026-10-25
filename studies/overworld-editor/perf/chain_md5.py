"""Lane chain: world-fuse's two whole-tree md5 walks (fuse._world_tree_md5, before and after each row: the manifest
drift gate and the per-step attribution in world_manifest.json) inside the bar's world-fuse job, unpatched against a
prototype; and the cost of the UnityPy import the doomed disc-4 mirror attempt pays in a draft.

    py studies/overworld-editor/perf/chain_md5.py [runs]

PROTOTYPE F1: the walk by os.scandir (no Path.rglob), the files ordered exactly as sorted(rglob) orders them (Path
order), and a per-process (size, mtime_ns) -> md5 memo: the AFTER walk re-reads only files whose stat moved since the
BEFORE walk (the stat law draft.edits() already trusts).
Each run: two fresh WARM copies at the state before H2 (a hill row, the row the Delete/Edit put-back re-runs), one
child process per variant running cli.main(world-fuse ...); world files, ledger rows (utc/argv out) and the
world_manifest.json entries ("at" out) compared. Each md5 walk is timed inside the child.
Also: `import UnityPy` in a fresh process (bytecode cached), the price of mirror() reaching _unitypy() before finding
the draft's root has no bundles.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402
import chain_fuse as CF                                               # noqa: E402

K = 1                                                                 # H2


def child(variant, draft, recipe):
    from ff9mapkit import cli
    from ff9mapkit.world import fuse as FU
    from ff9mapkit.world.mesh import LEDGER_NAME
    real = FU._world_tree_md5
    walks = []
    memo = {}

    def fast(mod_root):
        root = Path(mod_root) / "FF9_Data" / "WorldMap"
        out = {}
        if not root.is_dir():
            return out
        found = []
        stack = [str(root)]
        while stack:
            p = stack.pop()
            with os.scandir(p) as it:
                for e in it:
                    if e.is_dir(follow_symlinks=False):
                        stack.append(e.path)
                    elif e.is_file():
                        found.append((Path(e.path), e))
        found.sort(key=lambda pe: pe[0])                               # the order sorted(rglob("*")) gives
        for p, e in found:
            if p.name in (FU._MANIFEST_NAME, LEDGER_NAME) or any(m in p.name for m in FU._SKIP_MARKERS):
                continue
            st = e.stat()
            key = (str(p), st.st_size, st.st_mtime_ns)
            h = memo.get(key)
            if h is None:
                h = memo[key] = hashlib.md5(p.read_bytes()).hexdigest()
            out[p.relative_to(mod_root).as_posix()] = h
        return out

    fn = fast if variant == "F1" else real

    def timed(mod_root):
        t = time.perf_counter()
        try:
            return fn(mod_root)
        finally:
            walks.append(round(time.perf_counter() - t, 3))
    FU._world_tree_md5 = timed
    argv = CF.argv(Path(recipe), Path(draft))[3:]
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    t = time.perf_counter()
    try:
        code = cli.main([str(a) for a in argv])
    finally:
        sys.stdout = old
    print(json.dumps({"code": code, "main_s": round(time.perf_counter() - t, 2), "walks_s": walks,
                      "unitypy_loaded": "UnityPy" in sys.modules}))


def _manifest(d):
    doc = json.loads((Path(d) / "FF9_Data" / "WorldMap" / "world_manifest.json").read_text(encoding="utf-8"))
    return [{k: v for k, v in e.items() if k != "at"} for e in doc.get("entries", [])]


def unitypy_import(runs):
    ts = []
    for _ in range(runs):
        p = subprocess.run([sys.executable, "-c", "import time; t=time.perf_counter(); import UnityPy; "
                            "print(time.perf_counter()-t)"], capture_output=True, text=True, timeout=300)
        ts.append(float(p.stdout.strip().splitlines()[-1]))
    return CC.stats(ts)


def main(runs=3):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "rows": []}
    recipe = CF.row_toml(K)
    from ff9mapkit.world import mesh as M
    for r in range(runs):
        row, res = {}, {}
        for variant in ("base", "F1"):
            d = CF.state_before(K, f"md5{variant}{r}", warm=True)
            nl = len(M.read_ledger(d))
            t = time.perf_counter()
            p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "child", variant, str(d), str(recipe)],
                               capture_output=True, text=True, timeout=3600)
            wall = time.perf_counter() - t
            assert p.returncode == 0, p.stderr[-2000:]
            rec = json.loads(p.stdout.strip().splitlines()[-1])
            assert rec["code"] == 0, rec
            rec["child_wall_s"] = round(wall, 2)
            row[variant] = rec
            res[variant] = (CF.world(d), CF.ledger_rows(d, nl), _manifest(d), CF.vs_gold(K, d))
        row["world_identical"] = res["base"][0] == res["F1"][0]
        row["ledger_identical"] = res["base"][1] == res["F1"][1]
        row["manifest_identical"] = res["base"][2] == res["F1"][2]
        row["equal_card_accept"] = (res["base"][3], res["F1"][3])
        out["rows"].append(row)
        print(json.dumps(row))
    for v in ("base", "F1"):
        out[f"{v} child_wall_s"] = CC.stats([row[v]["child_wall_s"] for row in out["rows"]])
        out[f"{v} walks_total_s"] = CC.stats([sum(row[v]["walks_s"]) for row in out["rows"]])
        print(v, out[f"{v} child_wall_s"], out[f"{v} walks_total_s"])
    out["import UnityPy (fresh process)"] = unitypy_import(runs)
    print("import UnityPy", out["import UnityPy (fresh process)"])
    CC.save("md5.json", out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["child"]:
        child(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
