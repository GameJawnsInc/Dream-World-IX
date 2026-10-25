"""reads_sink_par: a prototype of the sink card's cold island list (transplant.sink_candidates) with its per-island
plans spread over worker PROCESSES. The parent runs the serial part verbatim (the land components, the not-an-island
filter, each row's at/outline/land/max_y), and a spawn pool runs the per-island part verbatim (sink_plan, then the
footprint and cluster fallbacks) on just ``at``. Identity: the rows (json-normalised) == the shared cache's rows
(read only) AND == an unpatched TR.sink_candidates run's rows (reads_sink.py's identity, which matched the cache).

    py studies/overworld-editor/perf/reads_sink_par.py [workers=6] [runs=3]

Nothing is written to the shared cache; the pool's workers load their own UnityPy env (counted in the wall)."""
from __future__ import annotations

import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import GAME, dump, stat  # noqa: E402


def _plan_row(args):
    """The per-island body of sink_candidates, verbatim, from ``at`` on."""
    at, row, disc, lod, max_blocks = args
    from ff9mapkit.world import transplant as TR
    from ff9mapkit.world.transplant import SinkCrowded, SinkJoined, sink_cluster_plan, sink_footprint_plan, sink_plan
    game = GAME
    try:
        _plan, rep = sink_plan(at, disc=disc, lod=lod, game=game, max_blocks=max_blocks)
        row.update(ok=True, why=None, bands=rep["bands"], shore_tris=rep["shore_tris"], blocks=rep["blocks"],
                   building=rep["building"] or None, entrance_tris=rep["entrance_tris"])
    except (SinkJoined, SinkCrowded) as e:
        row.update(ok=False, why=str(e).split(":")[0][:160])
        try:
            _plan, rep = sink_footprint_plan(at, disc=disc, lod=lod, game=game, max_blocks=max_blocks)
            row.update(ok=True, fill="footprint", joined=row["why"], why=None, bands=rep["bands"],
                       shore_tris=rep["shore_tris"], blocks=rep["blocks"], building=rep["building"] or None,
                       entrance_tris=rep["entrance_tris"])
        except ValueError as e3:
            row["why"] = str(e3).split(":")[0][:160]
        if not isinstance(e, SinkJoined):
            return row
        try:
            _plan, rep = sink_cluster_plan(at, disc=disc, lod=lod, game=game, max_blocks=max_blocks)
            row["cluster"] = {"ok": True, "members": rep["members"], "blocks": rep["blocks"],
                              "bands": rep["bands"], "why": None}
        except ValueError as e2:
            row["cluster"] = {"ok": False, "members": None, "blocks": None, "bands": None,
                              "why": str(e2).split(":")[0][:160]}
    except ValueError as e:
        row.update(ok=False, why=str(e).split(":")[0][:160])
    del TR
    return row


def _warm(_):
    from ff9mapkit.world import extract as X
    X._worldmap_env(1, GAME)
    return True


def sink_candidates_par(pool, *, disc=1, lod="0_1", max_blocks=9):
    """sink_candidates' serial head, verbatim; the per-island tail through ``pool``."""
    from ff9mapkit.world import discmirror as DM, meshedit as ME
    from ff9mapkit.world.transplant import SINK_LAND_PARTS, SINK_WATER_PARTS, _plan_centroid, _plan_hull, world_tris
    game = GAME
    real = DM._real_parts(disc, lod, game=game)
    tagged = []
    for b in sorted(real):
        for p in SINK_LAND_PARTS:
            if p in real[b]:
                tagged += [(p, b, t) for t in world_tris(b[0], b[1], p, disc=disc, lod=lod, game=game)]
    own = {id(t): (p, b) for p, b, t in tagged}
    wkeys: dict = {}

    def water_keys(b):
        if b not in wkeys:
            wkeys[b] = {(round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4)) for p in SINK_WATER_PARTS
                        if p in real.get(b, ()) for t in world_tris(b[0], b[1], p, disc=disc, lod=lod, game=game)
                        for v in t}
        return wkeys[b]
    jobs = []
    for c in ME.vertex_components([t for _, _, t in tagged]):
        blocks = sorted({own[id(t)][1] for t in c})
        if len(blocks) > max_blocks:
            continue
        ck = {(round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4)) for t in c for v in t}
        if not any(ck & water_keys((b[0] + dx, b[1] + dy)) for b in blocks for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            continue

        def flat(t):
            return abs((t[1][0][0] - t[0][0][0]) * (t[2][0][2] - t[0][0][2])
                       - (t[2][0][0] - t[0][0][0]) * (t[1][0][2] - t[0][0][2]))
        at = tuple(round(v, 3) for v in _plan_centroid(max(c, key=flat)))
        row = {"at": list(at), "outline": _plan_hull([(v[0][0], v[0][2]) for t in c for v in t]),
               "land_u2": round(sum(flat(t) for t in c) / 2.0, 1),
               "max_y": round(max(v[0][1] for t in c for v in t), 2), "blocks": blocks, "bands": None,
               "shore_tris": 0, "cluster": None, "fill": "tiles", "joined": None, "building": None,
               "entrance_tris": 0}
        jobs.append((at, row, disc, lod, max_blocks))
    t_head = time.perf_counter()
    rows = pool.map(_plan_row, jobs, chunksize=1)
    return sorted(rows, key=lambda r: -r["land_u2"]), t_head, len(jobs)


def norm(rows):
    return json.loads(json.dumps(rows, default=lambda o: list(o) if isinstance(o, tuple) else str(o)))


def main():
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    from ff9mapkit.world import extract as X
    from ff9mapkit.world import sinkedit as SE
    ref = json.loads(SE._cache_file(GAME, 1).read_text(encoding="utf-8"))["rows"]
    res = {"cmd": f"py studies/overworld-editor/perf/reads_sink_par.py {workers} {runs}", "workers": workers,
           "runs": []}
    ctx = mp.get_context("spawn")
    for i in range(runs):
        t0 = time.perf_counter()                         # the pool's start + its workers' env loads are in the wall
        with ctx.Pool(workers) as pool:
            pool.map(_warm, range(workers), chunksize=1)
            t_pool = time.perf_counter() - t0
            X._worldmap_env(1, GAME)
            rows, t_head, n = sink_candidates_par(pool)
        wall = time.perf_counter() - t0
        rec = {"wall_s": round(wall, 2), "pool_start_and_env_s": round(t_pool, 2),
               "serial_head_s": round(t_head - t0 - t_pool, 2), "islands_planned": n,
               "identical_to_shared_cache": norm(rows) == ref}
        res["runs"].append(rec)
        print(i, rec, flush=True)
    res["wall"] = stat([r["wall_s"] for r in res["runs"]])
    dump(f"reads_sink_par_{workers}.json", res)


if __name__ == "__main__":
    main()
