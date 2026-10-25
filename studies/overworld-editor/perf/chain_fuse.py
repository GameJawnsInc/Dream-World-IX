"""Lane chain: the world-fuse job the recipe bar runs per row (RecipeBar._fuse_argv: a put-back re-run, an opened
recipe's row), on the draft state that row composes onto.

    py studies/overworld-editor/perf/chain_fuse.py cold [runs]   # subprocess wall per row (fresh copy each run),
                                                                 # its result vs the card's Accept (the gold step)
    py studies/overworld-editor/perf/chain_fuse.py prof           # one cProfile'd subprocess per row (shares)
    py studies/overworld-editor/perf/chain_fuse.py warm           # B3 prototype: cli.main in ONE process, each row
                                                                 # twice (cold-in-process, then warm), world files
                                                                 # and ledger rows == the subprocess's

The state for row k: a fresh copy of the gold draft undone to cursor k (the recipe's first k rows applied), the very
ground an opened recipe composes row k onto.
"""
from __future__ import annotations

import hashlib
import io
import json
import pstats
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402

from ff9mapkit.world import draft as D                                # noqa: E402
from ff9mapkit.world import recipe as RC                              # noqa: E402

GOLD_STEPS = D.history(D.draft_path(CC.SOURCE, root=CC.GOLD))["steps"]
KEYS = ["H", "H2", "I", "T", "S"]


def state_before(k, name, warm=False):
    """``warm``: every file of the copy read once after it is made (chain_av: the first open of a file just written
    costs ~5 ms, later ones ~0.1 ms; a draft long in use has had most of its files read)."""
    root = CC.fresh_copy(name)
    d = D.draft_path(CC.SOURCE, root=root)
    while D.history(d)["cursor"] > k:
        D.undo(d)
    if warm:
        for p in Path(root).rglob("*"):
            if p.is_file():
                p.read_bytes()
    return d


def row_toml(k):
    tmp = Path(tempfile.mkdtemp(prefix="chain_fuse_", dir=str(CC.OUT))) / "row.toml"
    tmp.write_text(RC.dumps_one(dict(GOLD_STEPS[k]["row"])), encoding="utf-8")
    return tmp


def argv(recipe, d):
    from ff9mapkit.workspace.worldrecipe import RecipeBar
    return RecipeBar._fuse_argv(SimpleNamespace(_game_fn=lambda: CC.GAME), recipe, d)   # the bar's own argv


def world(d) -> dict:
    return {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(d) / "FF9_Data" / "WorldMap").rglob("Block*")
            if ".bak-" not in p.name and p.suffix in (".ff9mesh", ".txt")}


def ledger_rows(d, since):
    out = []
    for e in __import__("ff9mapkit.world.mesh", fromlist=["read_ledger"]).read_ledger(d)[since:]:
        out.append({k: v for k, v in e.items() if k not in ("utc", "argv")})
    return out


def vs_gold(k, d):
    """The composed row's files at the gold step's cells against the card's Accept (the gold step's after side)."""
    s = GOLD_STEPS[k]
    now = {rel: D._sha(p) for rel, p in D._cell_files(d, [tuple(c) for c in s["cells"]]).items()}
    return now == s["after"]


def cold(runs=3, warm=False):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "runs": runs, "warm": warm, "rows": {}}
    for k, key in enumerate(KEYS):
        ts, same, logs = [], [], []
        for r in range(runs):
            d = state_before(k, f"fuse{key}{r}", warm=warm)
            a = argv(row_toml(k), d)
            t = time.perf_counter()
            p = subprocess.run(a, cwd=str(CC.KIT), capture_output=True, text=True, timeout=3600)
            ts.append(time.perf_counter() - t)
            assert p.returncode == 0, (key, p.stdout[-800:], p.stderr[-800:])
            same.append(vs_gold(k, d))
            logs.append(p.stdout[-400:])
        out["rows"][key] = {"label": GOLD_STEPS[k]["label"], "wall": CC.stats(ts), "equals_card_accept": same,
                            "tail": logs[0]}
        print(f"{key:3s} {GOLD_STEPS[k]['label']:40s} min {min(ts):.2f} median {sorted(ts)[len(ts) // 2]:.2f} "
              f"== card accept {same}")
    # the import tax: a world-fuse that refuses at once (a missing layout file) and --help
    tax = []
    for _ in range(runs):
        t = time.perf_counter()
        subprocess.run([sys.executable, "-m", "ff9mapkit", "--game", str(CC.GAME), "world-fuse",
                        str(CC.OUT / "no-such.toml"), "--mod-folder", str(CC.OUT / "nowhere")],
                       cwd=str(CC.KIT), capture_output=True, text=True, timeout=600)
        tax.append(time.perf_counter() - t)
    out["start_tax (world-fuse on a missing file)"] = CC.stats(tax)
    print("start tax", out["start_tax (world-fuse on a missing file)"])
    CC.save("fuse_cold_warm.json" if warm else "fuse_cold.json", out)


def prof(warm=False):
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "warm": warm, "rows": {}}
    for k, key in enumerate(KEYS):
        d = state_before(k, f"fuseprof{key}", warm=warm)
        a = argv(row_toml(k), d)
        pf = CC.OUT / f"fuse_{key}{'_warm' if warm else ''}.pstats"
        a = [a[0], "-m", "cProfile", "-o", str(pf)] + a[1:]
        t = time.perf_counter()
        p = subprocess.run(a, cwd=str(CC.KIT), capture_output=True, text=True, timeout=3600)
        wall = time.perf_counter() - t
        assert p.returncode == 0, (key, p.stdout[-800:], p.stderr[-800:])
        st = pstats.Stats(str(pf))
        total = st.total_tt
        imp = sum(v[3] for f, v in st.stats.items() if f[2] == "_find_and_load" and "importlib" in f[0])
        rows = sorted(((v[3], v[2], f) for f, v in st.stats.items()), key=lambda r: -r[0])
        s = io.StringIO()
        pstats.Stats(str(pf), stream=s).sort_stats("cumulative").print_stats(40)
        s2 = io.StringIO()
        pstats.Stats(str(pf), stream=s2).sort_stats("tottime").print_stats(25)
        out["rows"][key] = {"label": GOLD_STEPS[k]["label"], "wall_under_cprofile": round(wall, 2),
                            "profiled_total": round(total, 2), "pstats": str(pf),
                            "cumulative": s.getvalue(), "tottime": s2.getvalue()}
        print(f"{key}: wall {wall:.1f} s (profiled {total:.1f} s)")
    CC.save("fuse_prof_warm.json" if warm else "fuse_prof.json", out)


def warm_worker():
    """B3: run each row through cli.main twice in this one process (a warm worker would keep the imports, UnityPy
    and the loaded bundles resident), each on its own fresh copy at the row's state; compare the world files and the
    ledger rows (minus utc) with a cold subprocess run of the same row."""
    from ff9mapkit import cli
    from ff9mapkit.world import mesh as M
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "rows": {}}
    t_imp = time.perf_counter()
    import ff9mapkit.world.fuse  # noqa: F401  (the verb's own modules, as the first in-process call would)
    out["import_world_fuse_s"] = round(time.perf_counter() - t_imp, 3)
    for k, key in enumerate(KEYS):
        rec = {"label": GOLD_STEPS[k]["label"]}
        dc = state_before(k, f"warmC{key}", warm=True)
        nl = len(M.read_ledger(dc))
        a = argv(row_toml(k), dc)
        t = time.perf_counter()
        p = subprocess.run(a, cwd=str(CC.KIT), capture_output=True, text=True, timeout=3600)
        rec["subprocess_s"] = round(time.perf_counter() - t, 2)
        assert p.returncode == 0, (key, p.stdout[-800:])
        ref_w, ref_l = world(dc), ledger_rows(dc, nl)
        for n in ("in_process_1", "in_process_2"):
            dw = state_before(k, f"warm{n[-1]}{key}", warm=True)
            nl = len(M.read_ledger(dw))
            aa = argv(row_toml(k), dw)[3:]                           # after "py -m ff9mapkit"
            buf = io.StringIO()
            t = time.perf_counter()
            old = sys.stdout
            sys.stdout = buf
            try:
                code = cli.main([str(x) for x in aa])
            finally:
                sys.stdout = old
            rec[f"{n}_s"] = round(time.perf_counter() - t, 2)
            assert code == 0, (key, buf.getvalue()[-800:])
            w, led = world(dw), ledger_rows(dw, nl)
            # paths differ by the copy's name only through the drafts root: world() is draft-relative already
            rec[f"{n}_world_identical"] = w == ref_w
            rec[f"{n}_ledger_identical"] = led == ref_l
            if not rec[f"{n}_world_identical"]:
                rec[f"{n}_differ"] = sorted(x for x in set(w) | set(ref_w) if w.get(x) != ref_w.get(x))[:8]
        out["rows"][key] = rec
        print(key, rec)
    CC.save(f"fuse_warm{sys.argv[2] if len(sys.argv) > 2 else ''}.json", out)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "cold"
    w = "warm" in sys.argv[2:]
    if mode == "cold":
        cold(int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 3, warm=w)
    elif mode == "prof":
        prof(warm=w)
    else:
        warm_worker()
