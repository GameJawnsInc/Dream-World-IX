"""Lane chain: the disc-4 mirror every world-* job attempts inside a DRAFT (an absolute --mod-folder outside the
install: auto_mirror derives the draft's parent as the game root) imports UnityPy (world.extract._worldmap_env calls
_unitypy() first) before it finds that root has no StreamingAssets bundles and logs NOT RUN. A relief row needs
UnityPy for nothing else. PROTOTYPE U1: _worldmap_env checks for StreamingAssets/p0data*.bin under the root FIRST and
raises the very ValueError (same text, memoized the same way) when there is none, else runs as before.

    py studies/overworld-editor/perf/chain_unity.py [runs]

Each run: two fresh WARM copies at the state before H2 (the hill row the Delete/Edit put-back re-runs); one child
process per variant runs cli.main(world-fuse ...). Compared: world files, ledger rows (utc/argv out), the
world_manifest.json entries ("at" out), and the job's printed lines (the copy's root path normalized).
"""
from __future__ import annotations

import glob
import io
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402
import chain_fuse as CF                                               # noqa: E402

K = 1


def child(variant, draft, recipe):
    from ff9mapkit import cli
    from ff9mapkit.world import extract as X
    if variant == "U1":
        real = X._worldmap_env

        def env(disc=1, game=None):
            sa = X._streaming_assets(game)
            key = (str(sa), int(disc))
            if key not in X._WM_ENV_MEMO and not glob.glob(str(sa / "p0data*.bin")):
                msg = (f"no worldmap terrain meshes (container {f'worldmap/disc{disc}/0_1/'!r}) found in "
                       f"StreamingAssets/p0data*.bin -- is this a full FF9 install?")
                X._WM_ENV_MEMO[key] = (None, msg)
                raise ValueError(msg)
            return real(disc, game=game)
        X._worldmap_env = env
    argv = CF.argv(Path(recipe), Path(draft))[3:]
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    t = time.perf_counter()
    try:
        code = cli.main([str(a) for a in argv])
    finally:
        sys.stdout = old
    print(json.dumps({"code": code, "main_s": round(time.perf_counter() - t, 3), "unitypy": "UnityPy" in sys.modules,
                      "out": buf.getvalue()}))


def _manifest(d):
    doc = json.loads((Path(d) / "FF9_Data" / "WorldMap" / "world_manifest.json").read_text(encoding="utf-8"))
    return [{k: v for k, v in e.items() if k != "at"} for e in doc.get("entries", [])]


def main(runs=3):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "rows": []}
    recipe = CF.row_toml(K)
    from ff9mapkit.world import mesh as M
    for r in range(runs):
        row, res = {}, {}
        for variant in ("base", "U1"):
            d = CF.state_before(K, f"unity{variant}{r}", warm=True)
            nl = len(M.read_ledger(d))
            t = time.perf_counter()
            p = subprocess.run([sys.executable, str(Path(__file__).resolve()), "child", variant, str(d), str(recipe)],
                               capture_output=True, text=True, timeout=3600)
            wall = time.perf_counter() - t
            assert p.returncode == 0, p.stderr[-2000:]
            rec = json.loads(p.stdout.strip().splitlines()[-1])
            assert rec["code"] == 0, rec
            text = rec.pop("out").replace(str(Path(d).parent), "<root>")
            rec["child_wall_s"] = round(wall, 2)
            row[variant] = rec
            res[variant] = (CF.world(d), CF.ledger_rows(d, nl), _manifest(d), text)
        row["world_identical"] = res["base"][0] == res["U1"][0]
        row["ledger_identical"] = res["base"][1] == res["U1"][1]
        row["manifest_identical"] = res["base"][2] == res["U1"][2]
        row["printed_identical"] = res["base"][3] == res["U1"][3]
        row["not_run_lines"] = [ln for ln in res["U1"][3].splitlines() if "NOT RUN" in ln][:3]
        out["rows"].append(row)
        print(json.dumps(row))
    for v in ("base", "U1"):
        out[f"{v} child_wall_s"] = CC.stats([row[v]["child_wall_s"] for row in out["rows"]])
        out[f"{v} main_s"] = CC.stats([row[v]["main_s"] for row in out["rows"]])
        print(v, out[f"{v} child_wall_s"], out[f"{v} main_s"])
    CC.save("unity.json", out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["child"]:
        child(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
