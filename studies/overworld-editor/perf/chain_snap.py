"""Lane chain: the whole-map step snapshot (draft.begin_step / commit_step over all_cells -- the sink card's Accept,
and the recipe bar's put-back re-run or opened-recipe row of any island/carry/sink/morph/river step, all on the GUI
thread), unpatched against prototypes, around a REAL world-fuse job of the sink row, on twin copies.

    py studies/overworld-editor/perf/chain_snap.py [runs] [debt|warm]

  debt -- each twin a fresh copy, its files never opened since written (the state a draft is in after
          ensure_draft wrote it, until something reads every file: chain_av measured ~10 s for that first read);
  warm -- the same, but every world file read once before the experiment (the floor).

Variants (each applied by swapping module functions for the twin's begin/commit only, restored after):
  base -- unpatched;
  P3   -- _cell_files by one listing per r-directory (chain_reads.cell_files_fast);
  S    -- P3 + S7 + S2:
          S7 begin_step: a file whose stat matches its manifest record on BOTH sides (the draft copy: column 3; the
             live folder: column 2) is the manifest's bytes on both (the law edits()/stale() already trust), so its
             snapshot copy is read from the LIVE folder (no first-open debt there) and its sha checked against the
             manifest (any mismatch falls back to reading the draft's file); every other file from the draft;
             begin_step also records each file's (size, mtime_ns) in the pending step.json;
          S2 commit_step: a file whose (size, mtime_ns) did not move since begin_step keeps its before-sha without
             a read; only moved, new or removed files are read, hashed and copied to the after side; the before
             copies of untouched cells are deleted as before.
IDENTITY: after the job and commit, the twins' history.json (utc out), every file under history/ (ledger copies
normalized: utc and argv out), every world file and the draft ledger (normalized) are compared; then both are undone,
compared, redone, compared.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402
import chain_fuse as CF                                               # noqa: E402
import chain_reads as CR                                              # noqa: E402

from ff9mapkit.world import draft as D                                # noqa: E402

K_SINK = 4


# ---------------------------------------------------------------- S7 + S2
def begin_step_s(draft, cells):
    draft = Path(draft)
    pend = draft / D.HISTORY_DIR / D._PENDING
    if pend.exists():
        shutil.rmtree(pend)
    cells = sorted({(int(bx) % 24, int(by)) for bx, by in cells})
    pend.mkdir(parents=True)
    meta = D.read_meta(draft) or {"manifest": {}, "source": str(draft)}
    man, source = meta["manifest"], Path(meta["source"])
    before, stat = {}, {}
    dest = pend / "before"
    made = set()
    for rel, p in sorted(D._cell_files(draft, cells).items()):
        s = os.stat(p)
        stat[rel] = [s.st_size, s.st_mtime_ns]
        rec = man.get(rel)
        data = None
        if rec is not None and s.st_size == rec[1] and s.st_mtime_ns == rec[3]:
            try:
                ls = os.stat(source / rel)
                if ls.st_size == rec[1] and ls.st_mtime_ns == rec[2]:
                    cand = (source / rel).read_bytes()
                    if hashlib.sha256(cand).hexdigest() == rec[0]:
                        data = cand
            except OSError:
                data = None
        if data is None:
            data = p.read_bytes()
        q = dest / rel
        if q.parent not in made:
            q.parent.mkdir(parents=True, exist_ok=True)
            made.add(q.parent)
        q.write_bytes(data)
        before[rel] = hashlib.sha256(data).hexdigest()
    D._keep_ledger(draft, pend / "before")
    (pend / "step.json").write_text(json.dumps({"cells": [list(c) for c in cells], "before": before,
                                                "stat": stat}), encoding="utf-8")


def commit_step_s(draft, row, label):
    draft = Path(draft)
    pend = draft / D.HISTORY_DIR / D._PENDING
    step = json.loads((pend / "step.json").read_text(encoding="utf-8"))
    cells = [tuple(c) for c in step["cells"]]
    before, stat0 = step["before"], step.get("stat", {})
    now = D._cell_files(draft, cells)
    after = {}
    moved_files = {}
    for rel, p in now.items():
        s = os.stat(p)
        if rel in before and stat0.get(rel) == [s.st_size, s.st_mtime_ns]:
            after[rel] = before[rel]
        else:
            moved_files[rel] = p
    for rel, p in moved_files.items():
        after[rel] = D._sha(p)
    moved = {rel for rel in set(before) | set(after) if before.get(rel) != after.get(rel)}
    keep = sorted({D._parse_rel(rel)[1] for rel in moved if D._parse_rel(rel) is not None})
    keep_set = set(keep)
    # the after side: every file at the kept cells (as the unpatched _snap would leave after its deletions)
    made = set()
    for rel, p in sorted(now.items()):
        pr = D._parse_rel(rel)
        if pr is None or pr[1] not in keep_set:
            continue
        data = p.read_bytes()
        q = pend / "after" / rel
        if q.parent not in made:
            q.parent.mkdir(parents=True, exist_ok=True)
            made.add(q.parent)
        q.write_bytes(data)
    (pend / "after").mkdir(parents=True, exist_ok=True)
    D._keep_ledger(draft, pend / "after")
    before = {rel: h for rel, h in before.items() if D._parse_rel(rel) and D._parse_rel(rel)[1] in keep_set}
    after = {rel: h for rel, h in after.items() if D._parse_rel(rel) and D._parse_rel(rel)[1] in keep_set}
    for rel in D._cell_files(pend / "before", [c for c in cells if c not in keep_set]):
        (pend / "before" / rel).unlink()
    h = D.history(draft)
    for old in h["steps"][h["cursor"]:]:
        shutil.rmtree(draft / old["dir"], ignore_errors=True)
    n = h["cursor"]
    rel_dir = f"{D.HISTORY_DIR}/{n:04d}"
    shutil.rmtree(draft / rel_dir, ignore_errors=True)
    (pend / "step.json").write_text(json.dumps({k: v for k, v in step.items() if k != "stat"}), encoding="utf-8")
    pend.rename(draft / rel_dir)
    rec = {"row": row, "label": label, "cells": [list(c) for c in keep], "before": before, "after": after,
           "dir": rel_dir, "utc": time.strftime("%Y-%m-%dT%H:%M:%S")}
    h["steps"] = h["steps"][:n] + [rec]
    h["cursor"] = n + 1
    D._write_history(draft, h)
    return rec


# ---------------------------------------------------------------- the comparison
def _norm_ledger(data: bytes, roots) -> str:
    out = []
    for line in data.decode("utf-8").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            out.append(line)
            continue
        e = {k: v for k, v in e.items() if k not in ("utc", "argv")}
        s = json.dumps(e, sort_keys=True)
        for r in roots:
            s = s.replace(json.dumps(str(r))[1:-1], "<root>")
        out.append(s)
    return "\n".join(out)


def tree(d: Path, roots) -> dict:
    out = {}
    for p in sorted(Path(d).rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(d).as_posix()
        if rel.endswith("world_manifest.json") or rel.startswith("FF9_Data/") and ".bak-" in p.name:
            continue                                                  # (the job's own stamps; parked backups)
        if rel == D.HISTORY:
            h = json.loads(p.read_text(encoding="utf-8"))
            for s in h.get("steps", []):
                s.pop("utc", None)
            out[rel] = json.dumps(h, sort_keys=True)
        elif rel.endswith(D.LEDGER):
            out[rel] = hashlib.sha256(_norm_ledger(p.read_bytes(), roots).encode()).hexdigest()
        elif rel.endswith("step.json"):
            out[rel] = json.dumps(json.loads(p.read_text(encoding="utf-8")), sort_keys=True)
        else:
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def warm_up(d):
    for p in Path(d).rglob("*"):
        if p.is_file():
            p.read_bytes()


VARIANTS = {"base": {}, "P3": {"_cell_files": CR.cell_files_fast},
            "S": {"_cell_files": CR.cell_files_fast, "begin_step": begin_step_s, "commit_step": commit_step_s}}


def run_variant(name, d, recipe, roots):
    patch = VARIANTS[name]
    saved = {k: getattr(D, k) for k in patch}
    rec = {}
    try:
        for k, f in patch.items():
            setattr(D, k, f)
        cells = D.all_cells()                                         # RC.row_cells of a sink row
        t = time.perf_counter()
        D.begin_step(d, cells)
        rec["begin_step_s"] = round(time.perf_counter() - t, 3)
        a = CF.argv(recipe, d)
        t = time.perf_counter()
        p = subprocess.run(a, cwd=str(CC.KIT), capture_output=True, text=True, timeout=3600)
        rec["job_s"] = round(time.perf_counter() - t, 2)
        assert p.returncode == 0, p.stdout[-1500:]
        t = time.perf_counter()
        D.commit_step(d, dict(CF.GOLD_STEPS[K_SINK]["row"]), CF.GOLD_STEPS[K_SINK]["label"])
        rec["commit_step_s"] = round(time.perf_counter() - t, 3)
    finally:
        for k, f in saved.items():
            setattr(D, k, f)
    return rec


def main(runs=2, mode="debt"):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "mode": mode, "rows": []}
    for r in range(runs):
        twins = {}
        for name in VARIANTS:
            d = CF.state_before(K_SINK, f"snap{mode}{name}{r}")
            if mode == "warm":
                warm_up(d)
            twins[name] = d
        recipe = CF.row_toml(K_SINK)
        res = {}
        for name, d in twins.items():
            res[name] = run_variant(name, d, recipe, [])
        roots = [Path(d).parent for d in twins.values()]
        trees = {n: tree(d, roots) for n, d in twins.items()}
        ident = {n: trees[n] == trees["base"] for n in twins if n != "base"}
        diff = {n: sorted(k for k in set(trees[n]) | set(trees["base"]) if trees[n].get(k) != trees["base"].get(k))[:8]
                for n in twins if n != "base"}
        for d in twins.values():
            D.undo(d)
        trees_u = {n: tree(d, roots) for n, d in twins.items()}
        ident_undo = {n: trees_u[n] == trees_u["base"] for n in twins if n != "base"}
        for d in twins.values():
            D.redo(d)
        trees_r = {n: tree(d, roots) for n, d in twins.items()}
        ident_redo = {n: trees_r[n] == trees_r["base"] for n in twins if n != "base"}
        row = {"run": r, "timings": res, "identical_after_commit": ident, "differ": diff,
               "identical_after_undo": ident_undo, "identical_after_redo": ident_redo,
               "kept_cells": D.history(twins["base"])["steps"][K_SINK]["cells"],
               "files_compared": len(trees["base"])}
        out["rows"].append(row)
        print(json.dumps(row))
    for name in VARIANTS:
        for k in ("begin_step_s", "commit_step_s", "job_s"):
            out[f"{name} {k}"] = CC.stats([row["timings"][name][k] for row in out["rows"]])
    CC.save(f"snap_{mode}.json", out)
    for name in VARIANTS:
        print(name, {k: out[f"{name} {k}"]["min"] for k in ("begin_step_s", "commit_step_s", "job_s")})


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2, sys.argv[2] if len(sys.argv) > 2 else "debt")
