"""SKEPTIC check for lane jobs, candidate A2 (P3 _cell_files by directory listing + P4 commit_step writes only the kept
cells' after copies). The lane's prototype (jobs_step_proto.install) and its tree normaliser (jobs_step_proto.tree) are
imported UNCHANGED; the loop is mine and adds the case the lane flagged as missing: a FOREST-sized step (the cells the
card snapshots for a forest: the dry run's own "blocks", 12 cells), next to the sink (all 480 cells).

Per run and verb: two drafts from the same live folder (U unpatched, P patched; out/perf/jobs/verify/a2/), every
snapshot file read once first (neither arm pays a fresh file's first open), then begin_step -> the card's real Accept
call(s) as subprocesses -> commit_step; the two whole draft trees must be byte-identical (history before/after,
history.json minus utc, ledger rows minus utc/paths -- jobs_step_proto.tree's normalisation, plus this probe's own
temp prefix). Then an UNDO through each draft (draft.undo) and the trees compared again (the history must replay alike).

    py studies/overworld-editor/perf/verify_jobs_a2.py N     -> out/perf/jobs/verify/a2.json
"""
import json
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402
import jobs_step_proto as SP  # noqa: E402
from jobs_wall import job_env  # noqa: E402

VOUT = J.OUT / "verify"


def tree(root):
    out = SP.tree(root)
    return {k: re.sub(rb"vjobs_a2_[A-Za-z0-9_]+", b"<T>", v) for k, v in out.items()}


def run_calls(argvs):
    oks = []
    for a in argvs:
        subprocess.run(a, cwd=str(J.kit_cwd()), env=job_env(), capture_output=True, check=False)
    return oks


def forest_cells(d):
    tmp = Path(tempfile.mkdtemp(prefix="vjobs_a2_fc_"))
    a = [str(x) for x in J.check_argv("forest", J.draft(), tmp / "verdict.json")]
    a = [x.replace(str(J.draft()), str(d)) for x in a]
    subprocess.run(a, cwd=str(J.kit_cwd()), env=job_env(), capture_output=True, check=False)
    v = json.loads((tmp / "verdict.json").read_text(encoding="utf-8"))
    assert v.get("ok"), v
    return [tuple(b) for b in v["blocks"]]


def main():
    from ff9mapkit.world import draft as D
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    verbs = sys.argv[2:] or ["forest", "sink"]
    base = J.draft()
    o_cf, p_cf, o_commit, p_commit = SP.install(D)
    res = {"runs": []}
    for verb in verbs:
        for i in range(n):
            drafts = {}
            for arm in ("U", "P"):
                root = VOUT / "a2" / f"{verb}_{arm}{i}"
                if root.exists():
                    shutil.rmtree(root)
                d = D.ensure_draft(J.SOURCE, game=J.GAME, root=root)
                for p in D._cell_files(d, D.all_cells()).values():
                    p.read_bytes()
                drafts[arm] = d
            cells = D.all_cells() if verb == "sink" else forest_cells(drafts["U"])
            rec = {"verb": verb, "run": i, "cells": len(cells)}
            for arm in (("U", "P") if i % 2 == 0 else ("P", "U")):
                d = drafts[arm]
                D._cell_files = o_cf if arm == "U" else p_cf
                t = time.perf_counter()
                D.begin_step(d, cells)
                rec[f"{arm}_begin_s"] = time.perf_counter() - t
                tmp = Path(tempfile.mkdtemp(prefix="vjobs_a2_"))
                argvs = [[str(x).replace(str(base), str(d)) for x in a]
                         for a in J.accept_argvs(verb, base, tmp / "verdict.json", tmp / "verdict4.json")]
                run_calls(argvs)
                v = json.loads((tmp / "verdict.json").read_text(encoding="utf-8"))
                rec[f"{arm}_ok"] = v.get("ok")
                t = time.perf_counter()
                st = (o_commit if arm == "U" else p_commit)(d, {"perf": verb}, f"perf {verb}")
                rec[f"{arm}_commit_s"] = time.perf_counter() - t
                rec[f"{arm}_kept_cells"] = len(st["cells"])
            D._cell_files = o_cf
            tu, tp = tree(drafts["U"]), tree(drafts["P"])
            diff = sorted(k for k in set(tu) | set(tp) if tu.get(k) != tp.get(k))
            rec.update(identical=not diff, diff=diff[:10], files_compared=len(tu))
            for arm in ("U", "P"):                       # the recorded step must undo alike
                D.undo(drafts[arm])
            tu, tp = tree(drafts["U"]), tree(drafts["P"])
            diff2 = sorted(k for k in set(tu) | set(tp) if tu.get(k) != tp.get(k))
            rec.update(identical_after_undo=not diff2, diff_after_undo=diff2[:10],
                       undo_restored_edits=[len(D.edits(drafts[a])) for a in ("U", "P")])
            print(json.dumps(rec), flush=True)
            res["runs"].append(rec)
            for d in drafts.values():
                shutil.rmtree(d.parent, ignore_errors=True)
    summ = {}
    for verb in verbs:
        rs = [r for r in res["runs"] if r["verb"] == verb]
        summ[verb] = {k: {"min": round(min(r[k] for r in rs), 3), "median": round(statistics.median(r[k] for r in rs), 3)}
                      for k in ("U_begin_s", "P_begin_s", "U_commit_s", "P_commit_s")}
        summ[verb]["all_identical"] = all(r["identical"] and r["identical_after_undo"] for r in rs)
    res["summary"] = summ
    print(json.dumps(summ, indent=1))
    (VOUT / "a2.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
