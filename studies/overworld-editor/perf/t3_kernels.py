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
OLD_REV = "1dce6836"                     # the commit before tier 3: the OLD arm runs these modules as they were there
OLD_MODULES = ("extract", "mesh", "placement", "interior", "transplant", "fuse")   # (dependency order)


def load_old():
    """Put world/<m>.py of OLD_REV in sys.modules under its own name before anything imports it (no switch in the
    package: the old arm IS the old code). Registered before exec, as an import does, so cycles resolve."""
    import types
    import ff9mapkit.world as W
    for m in OLD_MODULES:
        rel = f"ff9mapkit/ff9mapkit/world/{m}.py"
        src = subprocess.run(["git", "show", f"{OLD_REV}:{rel}"], cwd=str(J.KIT.parent), capture_output=True,
                             text=True, encoding="utf-8", check=True).stdout
        name = f"ff9mapkit.world.{m}"
        mod = types.ModuleType(name)
        mod.__file__ = str(J.KIT.parent / rel)                         # data files resolve beside it, as before
        mod.__package__ = "ff9mapkit.world"
        sys.modules[name] = mod
        setattr(W, m, mod)
        exec(compile(src, mod.__file__, "exec"), mod.__dict__)


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
        load_old()
    import contextlib
    import io
    from ff9mapkit import cli
    buf = io.StringIO()
    t = time.perf_counter()
    with contextlib.redirect_stdout(buf):
        try:
            code = cli.main(argv)
        except SystemExit as e:
            code = e.code
    rep = Path(argv[argv.index("--report-json") + 1])
    Path(out).write_text(json.dumps({"cli_main_s": time.perf_counter() - t, "code": code,
                                     "verdict": json.loads(rep.read_text(encoding="utf-8")) if rep.is_file() else None,
                                     "stdout": buf.getvalue()}), encoding="utf-8")


def check(n, verbs):
    res = {}
    for verb in verbs:
        walls = {"old": [], "new": []}
        mains = {"old": [], "new": []}
        verdicts = []
        for i in range(n):
            for arm in (("old", "new") if i % 2 == 0 else ("new", "old")):
                tmp = Path(tempfile.mkdtemp(prefix="t3k_"))
                if verb == "near":                                # the CLI's own search: the law in a loop
                    argv = [str(a) for a in J.prefix()] + ["world-forest", "--mod-folder", str(J.draft()), "--near",
                                                         "1400,-460", "--donor", "13,15", "--dry-run",
                                                         "--report-json", str(tmp / "verdict.json")]
                else:
                    argv = [str(a) for a in J.check_argv(verb, J.draft(), tmp / "verdict.json")]
                cli_argv = argv[argv.index("ff9mapkit") + 1:]
                t = time.perf_counter()
                subprocess.run([sys.executable, str(Path(__file__).resolve()), "child", arm, str(tmp / "o.json")]
                               + cli_argv, cwd=str(J.kit_cwd()), env=job_env(), capture_output=True, check=False)
                walls[arm].append(round(time.perf_counter() - t, 3))
                r = json.loads((tmp / "o.json").read_text(encoding="utf-8"))
                mains[arm].append(round(r["cli_main_s"], 3))
                verdicts.append(json.dumps([r["verdict"], r["stdout"]], sort_keys=True))
        res[verb] = {"wall_min": {a: min(v) for a, v in walls.items()},
                     "cli_main_min": {a: min(v) for a, v in mains.items()},
                     "cli_main_median": {a: statistics.median(v) for a, v in mains.items()},
                     "verdicts_identical": len(set(verdicts)) == 1, "runs": n}
        print(verb, json.dumps(res[verb]), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t3_check.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


def accept(n, verbs):
    """The card's real Accept call(s) into twin drafts, OLD and NEW children per call; the whole trees (and each
    call's printed output, the draft path normalized) must match."""
    import os
    import shutil
    import jobs_step_proto as SP
    from ff9mapkit.world import draft as D
    base, res = J.draft(), {}
    for verb in verbs:
        walls = {"old": [], "new": []}
        same = []
        for i in range(n):
            drafts, outs = {}, {}
            for arm in ("old", "new"):
                root = OUT / f"acc_{verb}_{arm}{i}"
                if root.exists():
                    shutil.rmtree(root)
                drafts[arm] = D.ensure_draft(J.SOURCE, game=J.GAME, root=root)
            for arm in (("old", "new") if i % 2 == 0 else ("new", "old")):
                d, total, printed = drafts[arm], 0.0, []
                tmp = Path(tempfile.mkdtemp(prefix="t3acc_"))
                for a in J.accept_argvs(verb, base, tmp / "verdict.json", tmp / "verdict4.json"):
                    argv = [str(x).replace(str(base), str(d)) for x in a]
                    cli_argv = argv[argv.index("ff9mapkit") + 1:]
                    t = time.perf_counter()
                    subprocess.run([sys.executable, str(Path(__file__).resolve()), "child", arm, str(tmp / "o.json")]
                                   + cli_argv, cwd=str(J.kit_cwd()), env=job_env(), capture_output=True, check=False)
                    total += time.perf_counter() - t
                    printed.append(json.loads((tmp / "o.json").read_text(encoding="utf-8"))["stdout"]
                                   .replace(str(d), "<D>"))
                walls[arm].append(round(total, 3))
                outs[arm] = printed
            import re

            def norm(tr):                                 # each arm's temp --report-json path is its own
                return {k: re.sub(rb"t3acc_[A-Za-z0-9_]+", b"<T>", v) for k, v in tr.items()}
            to, tn = norm(SP.tree(drafts["old"])), norm(SP.tree(drafts["new"]))
            diff = sorted(k for k in set(to) | set(tn) if to.get(k) != tn.get(k))
            for k in diff[:1]:                            # say what differs
                ro, rn = to.get(k, b"").splitlines(), tn.get(k, b"").splitlines()
                bad = [(x, y) for x, y in zip(ro, rn) if x != y][:1]
                print("  first differing row:", bad, len(ro), len(rn), flush=True)
            same.append(not diff and outs["old"] == outs["new"])
            print(verb, i, walls["old"][-1], walls["new"][-1], "identical", same[-1], diff[:3], flush=True)
            for d in drafts.values():
                shutil.rmtree(d.parent, ignore_errors=True)
        res[verb] = {"wall_min": {a: min(v) for a, v in walls.items()},
                     "wall_median": {a: statistics.median(v) for a, v in walls.items()}, "identical": all(same)}
        print(verb, json.dumps(res[verb]), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t3_accept.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


def fuse(n, ks):
    """The recipe bar's world-fuse row (the chain lane's gold draft, the state before step k: K=1 the hill row H2,
    K=4 the sink row) in OLD and NEW children; world files, ledger rows (utc/argv out) and world_manifest.json entries
    ('at' out) compared, and each equal to the card's own Accept of that step."""
    import chain_fuse as CF
    from chain_md5 import _manifest
    from ff9mapkit.world import mesh as M
    res = {}
    for k in ks:
        walls, same = {"old": [], "new": []}, []
        recipe = CF.row_toml(k)
        for i in range(n):
            got = {}
            for arm in (("old", "new") if i % 2 == 0 else ("new", "old")):
                d = CF.state_before(k, f"t3fuse_{arm}{i}", warm=True)
                nl = len(M.read_ledger(d))
                cli_argv = [str(a) for a in CF.argv(Path(recipe), Path(d))[3:]]
                tmp = Path(tempfile.mkdtemp(prefix="t3fuse_"))
                t = time.perf_counter()
                subprocess.run([sys.executable, str(Path(__file__).resolve()), "child-noreport", arm,
                                str(tmp / "o.json")] + cli_argv, cwd=str(J.kit_cwd()), env=job_env(),
                               capture_output=True, check=False)
                walls[arm].append(round(time.perf_counter() - t, 3))
                got[arm] = (CF.world(d), CF.ledger_rows(d, nl), _manifest(d), CF.vs_gold(k, d))
            same.append(got["old"][:3] == got["new"][:3] and got["old"][3] and got["new"][3])
            print(k, i, walls["old"][-1], walls["new"][-1], "identical and == the card's Accept", same[-1], flush=True)
        res[str(k)] = {"wall_min": {a: min(v) for a, v in walls.items()},
                       "wall_median": {a: statistics.median(v) for a, v in walls.items()}, "identical": all(same)}
        print(k, json.dumps(res[str(k)]), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t3_fuse.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


def child_noreport(arm, out, argv):
    if arm == "old":
        load_old()
    from ff9mapkit import cli
    t = time.perf_counter()
    try:
        code = cli.main(argv)
    except SystemExit as e:
        code = e.code
    Path(out).write_text(json.dumps({"cli_main_s": time.perf_counter() - t, "code": code}), encoding="utf-8")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "stock":
        stock(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    elif mode == "check":
        check(int(sys.argv[2]), sys.argv[3:])
    elif mode == "accept":
        accept(int(sys.argv[2]), sys.argv[3:])
    elif mode == "fuse":
        fuse(int(sys.argv[2]), [int(k) for k in sys.argv[3:]])
    elif mode == "child-noreport":
        child_noreport(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif mode == "child":
        child(sys.argv[2], sys.argv[3], sys.argv[4:])
