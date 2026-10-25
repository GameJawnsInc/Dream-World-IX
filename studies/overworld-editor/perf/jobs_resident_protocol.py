"""Lane jobs: is a RESIDENT worker (B3) safe across a CHANGING draft? The same sequence of card jobs runs twice from
two fresh drafts of the live folder: arm C = a fresh subprocess per job (what the card does today), arm R = ONE
process calling cli.main for every job with nothing purged (modules, the p0data env cache, the block decode memo,
every module-global cache kept). Each job's verdict and, at the end, every file under the two drafts must match.

The sequence makes later jobs read what earlier ones wrote: a forest Check, its Accept, the SAME forest Check again
(the draft now holds that forest), a hill Check elsewhere, a sink Accept (both calls: disc 1, then the disc-4 replay),
a coast Check, the same sink's Check again (the island is gone), the forest Check a third time.

    py studies/overworld-editor/perf/jobs_resident_protocol.py     -> out/perf/jobs/resident_protocol.json
"""
import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

SEQ = [("forest", "check"), ("forest", "accept"), ("forest", "check"), ("hill", "check"), ("sink", "accept"),
       ("coast", "check"), ("sink", "check"), ("forest", "check")]


def argvs(verb, kind, base, draft, tmp):
    if kind == "check":
        calls = [J.check_argv(verb, base, tmp / "verdict.json")]
    else:
        calls = J.accept_argvs(verb, base, tmp / "verdict.json", tmp / "verdict4.json")
    return [[str(x).replace(str(base), str(draft)) for x in a] for a in calls]


def verdicts(tmp, draft):
    out = []
    for name in ("verdict.json", "verdict4.json"):
        if (tmp / name).is_file():
            s = (tmp / name).read_text(encoding="utf-8").replace(json.dumps(str(draft))[1:-1], "<D>")
            out.append(json.loads(s))
    return out


def resident(draft, out):
    from ff9mapkit import cli
    base = J.draft()
    rec = []
    for verb, kind in SEQ:
        tmp = Path(tempfile.mkdtemp(prefix="jobs_rp_"))
        t = time.perf_counter()
        for a in argvs(verb, kind, base, draft, tmp):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    cli.main(a[3:])
                except SystemExit:
                    pass
        rec.append({"job": f"{verb} {kind}", "s": time.perf_counter() - t, "verdicts": verdicts(tmp, draft)})
    Path(out).write_text(json.dumps(rec), encoding="utf-8")


def tree(root):
    out = {}
    root = Path(root)
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if rel == "draft.json":
            continue
        if rel.endswith(".ff9world.jsonl"):
            rows = []
            for ln in p.read_text(encoding="utf-8").splitlines():
                if ln.strip():
                    e = json.loads(ln)
                    e.pop("utc", None)
                    row = json.dumps(e, sort_keys=True).replace(json.dumps(str(root))[1:-1], "<D>")
                    rows.append(re.sub(r"jobs_rp_[A-Za-z0-9_]+", "<T>", row))
            out[rel] = "\n".join(rows).encode()
        elif ".bak-" in p.name:
            out[re.sub(r"\.bak-\d{8}-\d{6}.*$", ".bak-TS", rel)] = p.read_bytes()
        else:
            out[rel] = p.read_bytes()
    return out


def main():
    from ff9mapkit.world import draft as D
    from jobs_wall import job_env
    base = J.draft()
    drafts = {}
    for arm in ("C", "R"):
        root = J.OUT / "resident" / arm
        if root.exists():
            shutil.rmtree(root)
        drafts[arm] = D.ensure_draft(J.SOURCE, game=J.GAME, root=root)
    # arm C: a fresh subprocess per call, as the card runs them
    cold = []
    for verb, kind in SEQ:
        tmp = Path(tempfile.mkdtemp(prefix="jobs_rp_"))
        t = time.perf_counter()
        for a in argvs(verb, kind, base, drafts["C"], tmp):
            subprocess.run(a, cwd=str(J.kit_cwd()), env=job_env(), capture_output=True)
        cold.append({"job": f"{verb} {kind}", "s": time.perf_counter() - t, "verdicts": verdicts(tmp, drafts["C"])})
    # arm R: one process
    out = Path(tempfile.mkdtemp(prefix="jobs_rpx_")) / "r.json"
    subprocess.run([sys.executable, __file__, "child", str(drafts["R"]), str(out)], cwd=str(J.kit_cwd()),
                   env=job_env(), check=True)
    res = json.loads(out.read_text(encoding="utf-8"))
    steps = []
    for c, r in zip(cold, res):
        same = json.dumps(c["verdicts"], sort_keys=True) == json.dumps(r["verdicts"], sort_keys=True)
        oks = [v.get("ok") for v in c["verdicts"]]
        steps.append({"job": c["job"], "cold_s": round(c["s"], 2), "resident_s": round(r["s"], 2),
                      "verdicts_identical": same, "ok": oks,
                      "gate": [(v.get("refused") or {}).get("gate") for v in c["verdicts"]]})
        print(f"{c['job']:16s} cold {c['s']:6.2f}s  resident {r['s']:6.2f}s  ok={oks} gate={steps[-1]['gate']} "
              f"verdicts identical={same}", flush=True)
    tc, tr = tree(drafts["C"]), tree(drafts["R"])
    diff = sorted(k for k in set(tc) | set(tr) if tc.get(k) != tr.get(k))
    rec = {"steps": steps, "files_compared": len(tc), "files_differ": diff[:20], "trees_identical": not diff,
           "cold_total_s": sum(s["cold_s"] for s in steps), "resident_total_s": sum(s["resident_s"] for s in steps)}
    print(json.dumps({k: v for k, v in rec.items() if k != "steps"}))
    (J.OUT / "resident_protocol.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    for d in drafts.values():
        shutil.rmtree(d.parent, ignore_errors=True)


if __name__ == "__main__":
    if sys.argv[1:2] == ["child"]:
        resident(sys.argv[2], sys.argv[3])
    else:
        main()
