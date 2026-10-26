"""Tier 2 re-measure + identity: the shipped draft.begin_step / commit_step / abort_step against the code before them
(PERF.md 3: one listing per row, commit reads only what moved, abort writes back only what moved).

    py studies/overworld-editor/perf/t2_step.py [n] [verbs...]      (default: 2 forest sink)

OLD is world/draft.py as committed before the change (`git show <rev>:...`, default 30a33d48), exec'd as its own module,
so every helper it calls is the old one. NEW is the package. Per run and verb: twin drafts of FF9CustomMap-world under
out/perf/t2/, their files aged 60 s (a draft in use was not written this instant: the racy-clean window is 2 s) and
read once (neither arm pays a fresh file's first open); then begin_step -> the card's real Accept call(s) as
subprocesses -> commit_step, the whole trees compared (jobs_step_proto.tree's normalisation); an undo through each,
compared again; then an ABORT leg: begin_step, one file of the step's cells rewritten as a job would, abort_step,
compared (bytes; the old abort also rewrote every other file, so times differ by design).
Evidence: out/perf/t2/t2_step.json
"""
from __future__ import annotations

import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jobs_common as J                                               # noqa: E402  (pins the worktree package)
import jobs_step_proto as SP                                          # noqa: E402
from jobs_wall import job_env                                         # noqa: E402

OUT = HERE.parent / "out" / "perf" / "t2"
REV = os.environ.get("T2_OLD_REV", "30a33d48")


def old_draft():
    src = subprocess.run(["git", "show", f"{REV}:ff9mapkit/ff9mapkit/world/draft.py"], cwd=str(J.KIT.parent),
                         capture_output=True, text=True, check=True).stdout
    mod = types.ModuleType("ff9mapkit.world._draft_old")
    mod.__file__ = "draft_old.py"
    mod.__package__ = "ff9mapkit.world"
    exec(compile(src, "draft_old.py", "exec"), mod.__dict__)
    return mod


def tree(root):
    out = SP.tree(root)
    return {k: re.sub(rb"t2step_[A-Za-z0-9_]+", b"<T>", v) for k, v in out.items()}


def aged(d, seconds=60):
    then = time.time_ns() - seconds * 10 ** 9
    for p in (Path(d) / "FF9_Data").rglob("*"):
        if p.is_file():
            os.utime(p, ns=(then, then))
            p.read_bytes()


def forest_cells(d):
    tmp = Path(tempfile.mkdtemp(prefix="t2step_fc_"))
    a = [str(x).replace(str(J.draft()), str(d)) for x in J.check_argv("forest", J.draft(), tmp / "verdict.json")]
    subprocess.run(a, cwd=str(J.kit_cwd()), env=job_env(), capture_output=True, check=False)
    v = json.loads((tmp / "verdict.json").read_text(encoding="utf-8"))
    assert v.get("ok"), v
    return [tuple(b) for b in v["blocks"]]


def diff(a, b):
    ta, tb = tree(a), tree(b)
    return sorted(k for k in set(ta) | set(tb) if ta.get(k) != tb.get(k)), len(ta)


def main():
    from ff9mapkit.world import draft as NEW
    OLD = old_draft()
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    verbs = sys.argv[2:] or ["forest", "sink"]
    base = J.draft()
    res = {"old_rev": REV, "runs": []}
    for verb in verbs:
        for i in range(n):
            drafts = {}
            for arm in ("OLD", "NEW"):
                root = OUT / f"{verb}_{arm}{i}"
                if root.exists():
                    shutil.rmtree(root)
                drafts[arm] = NEW.ensure_draft(J.SOURCE, game=J.GAME, root=root)
                aged(drafts[arm])
            cells = NEW.all_cells() if verb == "sink" else forest_cells(drafts["OLD"])
            rec = {"verb": verb, "run": i, "cells": len(cells)}
            for arm in (("OLD", "NEW") if i % 2 == 0 else ("NEW", "OLD")):
                D, d = (OLD if arm == "OLD" else NEW), drafts[arm]
                t = time.perf_counter()
                D.begin_step(d, cells)
                rec[f"{arm}_begin_s"] = round(time.perf_counter() - t, 3)
                tmp = Path(tempfile.mkdtemp(prefix="t2step_"))
                for a in J.accept_argvs(verb, base, tmp / "verdict.json", tmp / "verdict4.json"):
                    subprocess.run([str(x).replace(str(base), str(d)) for x in a], cwd=str(J.kit_cwd()),
                                   env=job_env(), capture_output=True, check=False)
                rec[f"{arm}_ok"] = json.loads((tmp / "verdict.json").read_text(encoding="utf-8")).get("ok")
                t = time.perf_counter()
                st = D.commit_step(d, {"perf": verb}, f"perf {verb}")
                rec[f"{arm}_commit_s"] = round(time.perf_counter() - t, 3)
                rec[f"{arm}_kept_cells"] = len(st["cells"])
            rec["diff"], rec["files_compared"] = diff(drafts["OLD"], drafts["NEW"])
            for arm in ("OLD", "NEW"):
                (OLD if arm == "OLD" else NEW).undo(drafts[arm])
            rec["diff_after_undo"] = diff(drafts["OLD"], drafts["NEW"])[0]
            for arm in ("OLD", "NEW"):                                # the abort leg
                D, d = (OLD if arm == "OLD" else NEW), drafts[arm]
                aged(d)
                D.begin_step(d, cells)
                victim = sorted(D._cell_files(d, cells))[0]
                (d / victim).write_bytes(b"half a write")
                t = time.perf_counter()
                D.abort_step(d)
                rec[f"{arm}_abort_s"] = round(time.perf_counter() - t, 3)
            rec["diff_after_abort"] = diff(drafts["OLD"], drafts["NEW"])[0]
            rec["identical"] = not (rec["diff"] or rec["diff_after_undo"] or rec["diff_after_abort"])
            print(json.dumps({k: v for k, v in rec.items() if k not in ("diff",)}), flush=True)
            res["runs"].append(rec)
            for d in drafts.values():
                shutil.rmtree(d.parent, ignore_errors=True)
    summ = {}
    for verb in verbs:
        rs = [r for r in res["runs"] if r["verb"] == verb]
        summ[verb] = {k: {"min": min(r[k] for r in rs), "median": statistics.median(r[k] for r in rs)}
                      for k in ("OLD_begin_s", "NEW_begin_s", "OLD_commit_s", "NEW_commit_s", "OLD_abort_s",
                                "NEW_abort_s")}
        summ[verb]["all_identical"] = all(r["identical"] for r in rs)
    res["summary"] = summ
    print(json.dumps(summ, indent=1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "t2_step.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
