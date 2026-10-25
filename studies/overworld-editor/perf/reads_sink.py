"""reads_sink: the sink card's island list cold (sinkedit.candidates -> transplant.sink_candidates, "three minutes once
per install"), measured in fresh processes, its read_block decode memo hit rate, and its cost shares (cProfile).

    py studies/overworld-editor/perf/reads_sink.py wall      # one fresh-process wall run (append to reads_sink_wall.jsonl)
    py studies/overworld-editor/perf/reads_sink.py profile   # one cProfile run -> reads_sink.pstats + shares

The scan is called directly (TR.sink_candidates): nothing is written to the shared cache. Identity: the rows are
compared (json-normalised) with the shared cache's rows, read only."""
from __future__ import annotations

import cProfile
import io
import json
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import GAME, OUT  # noqa: E402

from ff9mapkit.world import extract as X  # noqa: E402
from ff9mapkit.world import sinkedit as SE  # noqa: E402
from ff9mapkit.world import transplant as TR  # noqa: E402

calls = {"read_block": 0, "decode": 0}
_rb, _dec = X.read_block, X._decode_world_mesh


def _count_rb(*a, **k):
    calls["read_block"] += 1
    return _rb(*a, **k)


def _count_dec(*a, **k):
    calls["decode"] += 1
    return _dec(*a, **k)


X.read_block = _count_rb
X._decode_world_mesh = _count_dec


def norm(rows):
    return json.loads(json.dumps(rows, default=lambda o: list(o) if isinstance(o, tuple) else str(o)))


def cached_rows():
    p = SE._cache_file(GAME, 1)
    try:
        return json.loads(p.read_text(encoding="utf-8"))["rows"]
    except (OSError, ValueError, KeyError):
        return None


def main(mode):
    t_imp = time.perf_counter()
    X._worldmap_env(1, GAME)
    t_env = time.perf_counter() - t_imp
    t0 = time.perf_counter()
    if mode == "profile":
        pr = cProfile.Profile()
        pr.enable()
        rows = TR.sink_candidates(disc=1, game=GAME)
        pr.disable()
        pr.dump_stats(str(OUT / "reads_sink.pstats"))
    else:
        rows = TR.sink_candidates(disc=1, game=GAME)
    dt = time.perf_counter() - t0
    ref = cached_rows()
    rec = {"mode": mode, "env_load_s": round(t_env, 3), "scan_s": round(dt, 2), "rows": len(rows),
           "identical_to_shared_cache": (norm(rows) == ref) if ref is not None else "no cache",
           "read_block_calls": calls["read_block"], "decodes": calls["decode"],
           "memo_max": X._BLOCK_MEMO_MAX}
    if mode == "profile":
        st = pstats.Stats(str(OUT / "reads_sink.pstats"))
        buf = io.StringIO()
        st.stream = buf
        st.sort_stats("cumulative").print_stats(30)
        rec["pstats_top"] = buf.getvalue().splitlines()[:60]
        (OUT / "reads_sink_profile.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    else:
        with open(OUT / "reads_sink_wall.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    print(json.dumps({k: v for k, v in rec.items() if k != "pstats_top"}))
    if "pstats_top" in rec:
        print("\n".join(rec["pstats_top"]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "wall")
