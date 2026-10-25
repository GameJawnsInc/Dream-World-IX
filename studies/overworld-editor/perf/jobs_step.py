"""Lane jobs: the GUI-thread half of an Accept -- world.draft.begin_step (before the job) and commit_step (after it),
which CarryTool._run_job / _job_done call on the GUI thread. Times each on a scratch draft (out/perf/jobs/step/,
deleted after), for a forest's 12 cells and the sink's all_cells(), and splits begin_step into its parts:
_cell_files (the globs), the snapshot copy + sha256, and _keep_ledger (a copy of the ledger).

Also times a PROTOTYPE _cell_files (one directory listing per (disc, lod, row) instead of one glob per cell) and
proves it returns the same dict.

    py studies/overworld-editor/perf/jobs_step.py N       -> out/perf/jobs/step.json
"""
import json
import re
import shutil
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

FOREST_CELLS = [(21, 6), (21, 7), (21, 8), (22, 6), (22, 7), (22, 8), (23, 6), (23, 7), (23, 8), (20, 6), (20, 7),
                (20, 8)]


def cell_files_fast(D, folder, cells):
    """One listing per (disc, lod dir, row) holding any wanted cell; the same filter as draft._cell_files."""
    want = {}
    for bx, by in cells:
        want.setdefault(by, set()).add(bx)
    pat = re.compile(r"^Block\[(\d+)\]\[(\d+)\] ")
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
    return out


def timed(fn, *a, **k):
    t = time.perf_counter()
    r = fn(*a, **k)
    return time.perf_counter() - t, r


def main():
    from ff9mapkit.world import draft as D
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    root = J.OUT / "step"
    if root.exists():
        shutil.rmtree(root)
    d = D.ensure_draft(J.SOURCE, game=J.GAME, root=root)
    res = {}
    for name, cells in (("forest_12_cells", FOREST_CELLS), ("sink_all_cells", D.all_cells())):
        rows = []
        for _ in range(n):
            t_glob, files = timed(D._cell_files, d, cells)
            t_fast, files2 = timed(cell_files_fast, D, d, cells)
            assert {k: str(v) for k, v in files.items()} == {k: str(v) for k, v in files2.items()}, name
            t_begin, _ = timed(D.begin_step, d, cells)
            pend = d / D.HISTORY_DIR / D._PENDING
            t_ledger, _ = timed(D._keep_ledger, d, root / "ledger_probe")
            t_commit, _ = timed(D.commit_step, d, {"perf": name}, name)
            rows.append({"cell_files_glob_s": t_glob, "cell_files_fast_s": t_fast, "files": len(files),
                         "begin_step_s": t_begin, "keep_ledger_s": t_ledger, "commit_step_s": t_commit,
                         "bytes": sum(p.stat().st_size for p in files.values())})
            print(f"{name}: {len(files)} files {rows[-1]['bytes'] / 1e6:.1f} MB | _cell_files glob {t_glob:.3f}s "
                  f"(listing {t_fast:.3f}s, same dict) | GUI begin_step {t_begin:.3f}s | ledger copy {t_ledger:.3f}s "
                  f"| GUI commit_step {t_commit:.3f}s", flush=True)
            shutil.rmtree(pend, ignore_errors=True)
        res[name] = {"runs": rows, **{k: {"min": round(min(r[k] for r in rows), 4),
                                          "median": round(statistics.median(r[k] for r in rows), 4)}
                                      for k in ("cell_files_glob_s", "cell_files_fast_s", "begin_step_s",
                                                "keep_ledger_s", "commit_step_s")}}
    res["ledger_bytes"] = (d / D.LEDGER).stat().st_size if (d / D.LEDGER).is_file() else 0
    (J.OUT / "step.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
