"""Tier 3 re-measure + identity: the Check kernels as shipped against the code before them (PERF.md 5).

    py studies/overworld-editor/perf/t3_kernels.py stock [step]          the census on every stock block stack
    py studies/overworld-editor/perf/t3_kernels.py check N verb...       real Checks: old vs new, verdicts + walls
    (child) py studies/overworld-editor/perf/t3_kernels.py child <old|new> <out.json> <argv...>

stock: every stock block with a prefab on disc 1 and disc 4, its whole stock part stack (build_meshlist order,
       frame block_local), census with the precompute (new) and with placement._prepare -> None (the per-sample
       code); == block by block, raising alike.
check: the card's own Check argv (jobs_common.check_argv, the lane's lawful spots, into the jobs lane's draft) in
       fresh children, alternating OLD (every tier-3 change switched off by monkeypatch in the child: see OLD_OFF)
       and NEW; each child runs cli.main in-process and records its wall and the verdict JSON; the verdicts of all
       runs must be equal.
Evidence: out/perf/t3/t3_<mode>.json
"""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jobs_common as J                                               # noqa: E402  (pins the worktree package)
from jobs_wall import job_env                                         # noqa: E402

OUT = HERE.parent / "out" / "perf" / "t3"


def old_off():
    """Switch the tier-3 changes off in this process (the arm the verdicts are held to)."""
    from ff9mapkit.world import placement as P
    P._prepare = lambda meshlist: None
    try:
        from ff9mapkit.world import interior as IN
        if hasattr(IN, "_poly_box"):
            IN._poly_box = lambda poly: None
    except ImportError:
        pass


def stock(step):
    from ff9mapkit.world import extract as X
    from ff9mapkit.world import placement as P
    real = P._prepare
    rec = {"by_disc": {}}
    t_old = t_new = 0.0
    for disc in (1, 4):
        parts = X.block_parts(disc=disc, game=J.GAME)
        n = same = raised = 0
        for k, (bx, by) in enumerate(sorted(parts)[::step]):
            pb = {}
            for p in sorted(parts[(bx, by)]):
                cp = P.canonical_part(p)
                if cp is None:
                    continue
                try:
                    pb[cp] = X.read_block(bx, by, disc=disc, part=p, game=J.GAME)
                except Exception:                        # noqa: BLE001 -- a part read_block cannot decode: skip it
                    continue
            if "Terrain" not in pb:
                continue
            ml = P.build_meshlist(pb)
            out = {}
            for arm in (("old", "new") if k % 2 == 0 else ("new", "old")):
                P._prepare = real if arm == "new" else (lambda meshlist: None)
                t = time.perf_counter()
                try:
                    out[arm] = ("ok", P.census(ml, frame="block_local"))
                except ValueError as e:
                    out[arm] = ("raise", str(e))
                dt = time.perf_counter() - t
                if arm == "old":
                    t_old += dt
                else:
                    t_new += dt
            P._prepare = real
            n += 1
            raised += out["old"][0] == "raise"
            same += out["old"] == out["new"]
        rec["by_disc"][disc] = {"blocks": n, "identical": same, "both_raised": raised}
        print(disc, rec["by_disc"][disc], flush=True)
    rec.update(old_s=round(t_old, 3), new_s=round(t_new, 3), speedup=round(t_old / t_new, 2) if t_new else None)
    print(json.dumps(rec))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t3_stock.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")


def child(arm, out, argv):
    if arm == "old":
        old_off()
    from ff9mapkit import cli
    t = time.perf_counter()
    try:
        code = cli.main(argv)
    except SystemExit as e:
        code = e.code
    rep = Path(argv[argv.index("--report-json") + 1])
    Path(out).write_text(json.dumps({"cli_main_s": time.perf_counter() - t, "code": code,
                                     "verdict": json.loads(rep.read_text(encoding="utf-8"))}), encoding="utf-8")


def check(n, verbs):
    res = {}
    for verb in verbs:
        walls = {"old": [], "new": []}
        mains = {"old": [], "new": []}
        verdicts = []
        for i in range(n):
            for arm in (("old", "new") if i % 2 == 0 else ("new", "old")):
                tmp = Path(tempfile.mkdtemp(prefix="t3k_"))
                argv = [str(a) for a in J.check_argv(verb, J.draft(), tmp / "verdict.json")]
                cli_argv = argv[argv.index("ff9mapkit") + 1:]
                t = time.perf_counter()
                subprocess.run([sys.executable, str(Path(__file__).resolve()), "child", arm, str(tmp / "o.json")]
                               + cli_argv, cwd=str(J.kit_cwd()), env=job_env(), capture_output=True, check=False)
                walls[arm].append(round(time.perf_counter() - t, 3))
                r = json.loads((tmp / "o.json").read_text(encoding="utf-8"))
                mains[arm].append(round(r["cli_main_s"], 3))
                verdicts.append(json.dumps(r["verdict"], sort_keys=True))
        res[verb] = {"wall_min": {a: min(v) for a, v in walls.items()},
                     "cli_main_min": {a: min(v) for a, v in mains.items()},
                     "cli_main_median": {a: statistics.median(v) for a, v in mains.items()},
                     "verdicts_identical": len(set(verdicts)) == 1, "runs": n}
        print(verb, json.dumps(res[verb]), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t3_check.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "stock":
        stock(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    elif mode == "check":
        check(int(sys.argv[2]), sys.argv[3:])
    elif mode == "child":
        child(sys.argv[2], sys.argv[3], sys.argv[4:])
