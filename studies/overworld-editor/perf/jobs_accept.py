"""Lane jobs: an Accept, as the card runs it, timed by part and by THREAD (CarryTool._start / _run_job / _job_done):

  worker    D.ensure_draft (the first Check/Accept on a folder: "Making a draft ... (once)")
  GUI       D.begin_step(draft, cells)         (_run_job, before the job starts; the sink snapshots ALL cells)
  subprocess  each of _accept_calls (one; two for the sink and the coast morph: disc 1, then the disc-4 replay)
  GUI       D.commit_step(draft, row, label)   (_job_done, on the runner's done callback)
  worker    the draft label's read: D.edited_blocks + D.stale + D.last_promote (_refresh_draft_label)

Each run uses its OWN fresh draft under out/perf/jobs/acc/ (deleted after), so every Accept starts from the same
bytes. Nothing touches the install: the drafts are copies, every argv targets the draft.

    py studies/overworld-editor/perf/jobs_accept.py N verb [verb ...]     -> out/perf/jobs/accept.json
"""
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402
from jobs_wall import job_env  # noqa: E402


def step_cells(verb, verdict, argv):
    from ff9mapkit.world import draft as D
    if verb == "sink":
        return D.all_cells()
    if verb == "coast":
        i = argv.index("--cell")
        return [tuple(int(v) for v in argv[i + 1].split(","))]
    return [tuple(b) for b in (verdict or {}).get("blocks") or []]


def retarget(argv, d0, d1):
    return [str(a).replace(str(d0), str(d1)) for a in argv]


def main():
    from ff9mapkit.world import draft as D
    n = int(sys.argv[1])
    verbs = sys.argv[2:]
    base = J.draft()                                     # the lane draft: the argv recorded against it
    res = {}
    for verb in verbs:
        runs = []
        for i in range(n):
            root = J.OUT / "acc" / f"{verb}_{i}"
            if root.exists():
                shutil.rmtree(root)
            rec = {}
            t = time.perf_counter()
            d = D.ensure_draft(J.SOURCE, game=J.GAME, root=root)
            rec["ensure_draft_s"] = time.perf_counter() - t
            tmp = Path(tempfile.mkdtemp(prefix=f"jobs_acc_{verb}_"))
            chk = retarget(J.check_argv(verb, base, tmp / "check.json"), base, d)
            t = time.perf_counter()
            subprocess.run(chk, cwd=str(J.kit_cwd()), env=job_env(), capture_output=True)
            rec["check_s"] = time.perf_counter() - t
            v = json.loads((tmp / "check.json").read_text(encoding="utf-8"))
            assert v.get("ok"), (verb, v.get("refused"))
            cells = step_cells(verb, v, chk)
            t = time.perf_counter()
            D.begin_step(d, cells)
            rec["begin_step_s"] = time.perf_counter() - t
            rec["cells"] = len(cells)
            calls = [retarget(a, base, d) for a in J.accept_argvs(verb, base, tmp / "verdict.json",
                                                                  tmp / "verdict4.json")]
            rec["calls_s"] = []
            for k, a in enumerate(calls):
                t = time.perf_counter()
                r = subprocess.run(a, cwd=str(J.kit_cwd()), env=job_env(), capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
                rec["calls_s"].append(time.perf_counter() - t)
                if k == 0:
                    v1 = json.loads((tmp / "verdict.json").read_text(encoding="utf-8"))
                    rec["ok"] = v1.get("ok")
                    rec["written"] = len(v1.get("written") or [])
                    if not v1.get("ok"):
                        break
            t = time.perf_counter()
            D.commit_step(d, {"perf": verb}, f"perf {verb}")
            rec["commit_step_s"] = time.perf_counter() - t
            t = time.perf_counter()
            blocks = D.edited_blocks(d)
            st = D.stale(d)
            D.last_promote(d)
            rec["draft_label_read_s"] = time.perf_counter() - t
            rec["edited_blocks"] = len(blocks)
            rec["stale"] = len(st)
            rec["accept_wall_s"] = sum(rec["calls_s"])
            runs.append(rec)
            print(f"{verb:9s} {i}: draft {rec['ensure_draft_s']:5.2f} | check {rec['check_s']:5.2f} | GUI begin_step "
                  f"{rec['begin_step_s']:5.2f} ({rec['cells']} cells) | calls "
                  + " + ".join(f"{s:5.2f}" for s in rec["calls_s"])
                  + f" | GUI commit_step {rec['commit_step_s']:5.2f} | worker label {rec['draft_label_read_s']:5.2f}"
                    f" | ok={rec['ok']} written={rec['written']}", flush=True)
            shutil.rmtree(root, ignore_errors=True)
        keys = ["ensure_draft_s", "check_s", "begin_step_s", "accept_wall_s", "commit_step_s", "draft_label_read_s"]
        res[verb] = {"runs": runs, **{k: {"min": round(min(r[k] for r in runs), 3),
                                          "median": round(statistics.median(r[k] for r in runs), 3)}
                                      for k in keys}}
        for j in range(max(len(r["calls_s"]) for r in runs)):
            xs = [r["calls_s"][j] for r in runs if len(r["calls_s"]) > j]
            res[verb][f"call{j + 1}_s"] = {"min": round(min(xs), 3), "median": round(statistics.median(xs), 3)}
    p = J.OUT / "accept.json"
    allr = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    allr.update(res)
    p.write_text(json.dumps(allr, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
