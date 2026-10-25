"""Lane chain: the sink row's world-fuse (the costliest row the recipe bar re-runs or composes) -- how much of it is
the sink PLAN, and a prototype that plans once per disc instead of twice.

    py studies/overworld-editor/perf/chain_sinkplan.py [runs]

transplant.sink() calls its planned() twice (the gates' dry-run morphs, then "fresh tweaks: each counts what it
applied"), and the row runs sink() on disc 1 and again on disc 4 (the replay): four sink_auto_plan calls. The plan
reads STOCK only (at, disc, lod, game: no mod-folder argument), and nothing is written between the two calls.
PROTOTYPE (memo): sink_auto_plan memoized per (at, disc, lod, game, cluster), each caller handed a copy.deepcopy of the
result taken BEFORE any caller used it (so the second caller's tweaks are as fresh as a re-plan's).
Each run: a fresh warm copy at the state before the sink step, one child process per variant running cli.main
(world-fuse <row> --mod-folder <copy> --allow-overwrite, the bar's argv); world files, ledger rows (utc/argv out) and
the world_manifest.json entries (their "at" out) compared across the variants.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402
import chain_fuse as CF                                               # noqa: E402

K = 4


def child(variant, draft, recipe):
    from ff9mapkit import cli
    from ff9mapkit.world import transplant as TR
    real = TR.sink_auto_plan
    calls = []
    memo = {}

    def timed(at, *, disc=1, lod="0_1", game=None, cluster=False):
        t = time.perf_counter()
        try:
            if variant == "memo":
                key = (tuple(float(v) for v in at), int(disc), str(lod), str(game), bool(cluster))
                if key not in memo:
                    memo[key] = copy.deepcopy(real(at, disc=disc, lod=lod, game=game, cluster=cluster))
                return copy.deepcopy(memo[key])
            return real(at, disc=disc, lod=lod, game=game, cluster=cluster)
        finally:
            calls.append(round(time.perf_counter() - t, 3))
    TR.sink_auto_plan = timed
    argv = CF.argv(Path(recipe), Path(draft))[3:]
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    t = time.perf_counter()
    try:
        code = cli.main([str(a) for a in argv])
    finally:
        sys.stdout = old
    wall = time.perf_counter() - t
    print(json.dumps({"code": code, "main_s": round(wall, 2), "plan_calls_s": calls, "tail": buf.getvalue()[-300:]}))


def _manifest(d):
    p = Path(d) / "FF9_Data" / "WorldMap" / "world_manifest.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    return [{k: v for k, v in e.items() if k != "at"} for e in doc.get("entries", [])]


def main(runs=3):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "rows": []}
    recipe = CF.row_toml(K)
    for r in range(runs):
        row = {}
        res = {}
        for variant in ("base", "memo"):
            d = CF.state_before(K, f"sinkplan{variant}{r}", warm=True)
            from ff9mapkit.world import mesh as M
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
        row["world_identical"] = res["base"][0] == res["memo"][0]
        row["ledger_identical"] = res["base"][1] == res["memo"][1]
        row["manifest_identical"] = res["base"][2] == res["memo"][2]
        row["both_equal_card_accept"] = (res["base"][3], res["memo"][3])
        out["rows"].append(row)
        print(json.dumps(row))
    for v in ("base", "memo"):
        out[f"{v} child_wall_s"] = CC.stats([row[v]["child_wall_s"] for row in out["rows"]])
        out[f"{v} main_s"] = CC.stats([row[v]["main_s"] for row in out["rows"]])
        out[f"{v} plan_total_s"] = CC.stats([sum(row[v]["plan_calls_s"]) for row in out["rows"]])
        print(v, out[f"{v} child_wall_s"], out[f"{v} main_s"], out[f"{v} plan_total_s"])
    CC.save("sinkplan.json", out)


if __name__ == "__main__":
    if sys.argv[1:2] == ["child"]:
        child(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
