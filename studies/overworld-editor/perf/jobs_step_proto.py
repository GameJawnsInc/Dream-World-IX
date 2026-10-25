"""Lane jobs: PROTOTYPE (monkeypatch here; the package is not edited) of a cheaper Accept bookkeeping for a step that
snapshots every cell (the sink: SinkTool._step_cells = draft.all_cells()), run on the GUI thread today.

  P3 _cell_files by DIRECTORY LISTING: one iterdir per (disc, lod, row) holding a wanted cell, the same name filter,
     instead of one glob per (disc, cell).
  P4 commit_step's AFTER side: hash the draft's files at the cells (read only), and write an "after" copy only for a
     file whose sha differs from its "before" (every other after copy is deleted again by commit_step itself).
     The before copies of the untouched cells are removed exactly as before.

The two arms run the SAME real sink Accept (both _accept_calls, as the card runs them) into two drafts made from the
same folder, then: arm U = draft.begin_step/commit_step unpatched, arm P = patched. Identity: the two drafts' whole
trees (world files, history/<n>/ before+after, history.json minus its "utc") must be byte-identical.
Every draft's files are read once before timing (so neither arm pays a fresh file's first-open cost).

    py studies/overworld-editor/perf/jobs_step_proto.py N     -> out/perf/jobs/step_proto.json
"""
import hashlib
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
from jobs_wall import job_env  # noqa: E402


def install(D):
    orig_cell_files = D._cell_files
    pat = re.compile(r"^Block\[(\d+)\]\[(\d+)\] ")

    def cell_files(folder, cells):
        want = {}
        for bx, by in cells:
            want.setdefault(by, set()).add(bx)
        out = {}
        folder = Path(folder)
        for d in D.DISCS:
            tree = folder / "FF9_Data" / "WorldMap" / f"Disc{d}"
            if not tree.is_dir():
                continue
            for lod in sorted(p for p in tree.iterdir() if p.is_dir()):
                for by, bxs in want.items():
                    row = lod / f"r{by}"
                    if not row.is_dir():
                        continue
                    for p in row.iterdir():
                        m = pat.match(p.name)
                        if not m or int(m.group(2)) != by or int(m.group(1)) not in bxs:
                            continue
                        if p.is_file() and ".bak-" not in p.name and not p.name.endswith(".promoting"):
                            out[p.relative_to(folder).as_posix()] = p
        return dict(sorted(out.items()))                 # (callers sort; keep a stable order anyway)

    def commit_step(draft, row, label):
        draft = Path(draft)
        pend = draft / D.HISTORY_DIR / D._PENDING
        step = json.loads((pend / "step.json").read_text(encoding="utf-8"))
        cells = [tuple(c) for c in step["cells"]]
        before = step["before"]
        now = {}
        for rel, p in sorted(cell_files(draft, cells).items()):
            now[rel] = (p, p.read_bytes())
        after = {rel: hashlib.sha256(data).hexdigest() for rel, (p, data) in now.items()}
        moved = {rel for rel in set(before) | set(after) if before.get(rel) != after.get(rel)}
        keep = sorted({D._parse_rel(rel)[1] for rel in moved if D._parse_rel(rel) is not None})
        keepset = set(keep)
        for rel, (p, data) in now.items():               # the after copies a kept cell needs (only those)
            pr = D._parse_rel(rel)
            if pr is not None and pr[1] in keepset:
                q = pend / "after" / rel
                q.parent.mkdir(parents=True, exist_ok=True)
                q.write_bytes(data)
        D._keep_ledger(draft, pend / "after")
        before = {rel: h for rel, h in before.items() if D._parse_rel(rel) and D._parse_rel(rel)[1] in keep}
        after = {rel: h for rel, h in after.items() if D._parse_rel(rel) and D._parse_rel(rel)[1] in keep}
        for rel in cell_files(pend / "before", [c for c in cells if c not in keepset]):
            (pend / "before" / rel).unlink()
        h = D.history(draft)
        for old in h["steps"][h["cursor"]:]:
            shutil.rmtree(draft / old["dir"], ignore_errors=True)
        n = h["cursor"]
        rel_dir = f"{D.HISTORY_DIR}/{n:04d}"
        shutil.rmtree(draft / rel_dir, ignore_errors=True)
        pend.rename(draft / rel_dir)
        rec = {"row": row, "label": label, "cells": [list(c) for c in keep], "before": before, "after": after,
               "dir": rel_dir, "utc": time.strftime("%Y-%m-%dT%H:%M:%S")}
        h["steps"] = h["steps"][:n] + [rec]
        h["cursor"] = n + 1
        D._write_history(draft, h)
        return rec
    return orig_cell_files, cell_files, D.commit_step, commit_step


def tree(root):
    """Every file under the draft, normalised only where the two arms MUST differ: draft.json (made-time, copy
    mtimes), the ledger rows' utc and the draft's own path in their argv, a backup's timestamp suffix."""
    out = {}
    root = Path(root)
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            if rel == "draft.json":
                continue
            if rel.endswith(".ff9world.jsonl"):
                rows = []
                for ln in p.read_text(encoding="utf-8").splitlines():
                    if not ln.strip():
                        continue
                    e = json.loads(ln)
                    e.pop("utc", None)
                    row = json.dumps(e, sort_keys=True).replace(json.dumps(str(root))[1:-1], "<D>")
                    rows.append(re.sub(r"jobs_sp_[A-Za-z0-9_]+", "<T>", row))   # the job's temp --report-json
                out[rel] = "\n".join(rows).encode()
                continue
            if rel.endswith("history.json"):
                h = json.loads(p.read_text(encoding="utf-8"))
                for s in h.get("steps", []):
                    s.pop("utc", None)
                out[rel] = json.dumps(h, sort_keys=True).encode()
            elif ".bak-" in p.name:
                out[re.sub(r"\.bak-\d{8}-\d{6}.*$", ".bak-TS", rel)] = p.read_bytes()
            else:
                out[rel] = p.read_bytes()
    return out


def main():
    from ff9mapkit.world import draft as D
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    base = J.draft()
    o_cf, p_cf, o_commit, p_commit = install(D)
    res = {"runs": []}
    for i in range(n):
        drafts = {}
        for arm in ("U", "P"):
            root = J.OUT / "stepproto" / f"{arm}{i}"
            if root.exists():
                shutil.rmtree(root)
            d = D.ensure_draft(J.SOURCE, game=J.GAME, root=root)
            for p in D._cell_files(d, D.all_cells()).values():
                p.read_bytes()                           # pay every fresh file's first open before timing
            drafts[arm] = d
        rec = {}
        for arm in (("U", "P") if i % 2 == 0 else ("P", "U")):
            d = drafts[arm]
            D._cell_files = o_cf if arm == "U" else p_cf
            t = time.perf_counter()
            D.begin_step(d, D.all_cells())
            rec[f"{arm}_begin_s"] = time.perf_counter() - t
            tmp = Path(tempfile.mkdtemp(prefix="jobs_sp_"))
            for a in J.accept_argvs("sink", base, tmp / "verdict.json", tmp / "verdict4.json"):
                a = [str(x).replace(str(base), str(d)) for x in a]
                subprocess.run(a, cwd=str(J.kit_cwd()), env=job_env(), capture_output=True, check=False)
            t = time.perf_counter()
            (o_commit if arm == "U" else p_commit)(d, {"perf": "sink"}, "perf sink")
            rec[f"{arm}_commit_s"] = time.perf_counter() - t
        D._cell_files = o_cf
        tu, tp = tree(drafts["U"]), tree(drafts["P"])
        diff = sorted(k for k in set(tu) | set(tp) if tu.get(k) != tp.get(k))
        rec["identical"] = not diff
        rec["diff"] = diff[:10]
        rec["files_compared"] = len(tu)
        res["runs"].append(rec)
        print(json.dumps(rec), flush=True)
        for d in drafts.values():
            shutil.rmtree(d.parent, ignore_errors=True)
    for k in ("U_begin_s", "P_begin_s", "U_commit_s", "P_commit_s"):
        xs = [r[k] for r in res["runs"]]
        res[k] = {"min": round(min(xs), 3), "median": round(statistics.median(xs), 3)}
    res["all_identical"] = all(r["identical"] for r in res["runs"])
    (J.OUT / "step_proto.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "runs"}))


if __name__ == "__main__":
    main()
