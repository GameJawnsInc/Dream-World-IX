"""Rung 6 live-gate bench: what `floorplan.compose` actually costs, per room and per room SIZE.

The Floorplan tab re-runs the whole of `compose` on a worker thread 140ms after every gesture, so
this number IS the tab's responsiveness. RUNG6-TESTPLAN.md step 5 records the pre-fix measurement
(1.02s for one 2400x1800 room, 16.45s for eight) and calls it a stall rather than a live gate.

Run it from anywhere:

    py studies/click-authoring/gate_bench.py                # the table
    py studies/click-authoring/gate_bench.py --profile 5    # cProfile a 5-room plan
    py studies/click-authoring/gate_bench.py --counts 3     # who calls the grid samplers, how often

Rooms are laid out as a west->east row of abutting rectangles with a 1200u door on every shared
wall -- the shape a corridor dungeon actually has, and the one that maximises door count per room.
"""
import argparse
import contextlib
import cProfile
import io
import math
import pstats
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "ff9mapkit"))

from ff9mapkit import floorplan as FP            # noqa: E402

SMALL = (1200, 1600)
FULL = (2400, 1800)
SIZES = {"small": SMALL, "full": FULL}
COUNTS = (1, 2, 3, 5, 8)


def make_plan(n, size=FULL, *, door_span=1200.0):
    """``n`` abutting rooms in a row, every shared wall carrying one centred door."""
    w, h = float(size[0]), float(size[1])
    span = min(door_span, h - 2 * FP.R_WALK)     # a door can never be wider than the wall
    rooms, doors = [], []
    for i in range(n):
        x0 = i * w
        rooms.append({"name": f"ROOM{i + 1}",
                      "poly": [[x0, 0.0], [x0 + w, 0.0], [x0 + w, h], [x0, h]]})
        if i:
            x = x0
            doors.append({"a": f"ROOM{i}", "b": f"ROOM{i + 1}",
                          "seg": [[x, (h - span) / 2.0], [x, (h + span) / 2.0]]})
    return {"name": "BENCH", "mod_folder": "FF9CustomMap", "id_base": 30000,
            "rooms": rooms, "doors": doors, "entry": "ROOM1"}


def time_compose(plan, *, best_of=3):
    """Seconds for the fastest of ``best_of`` composes. Raises if the plan does not compose --
    a bench that silently measures the error path is worse than no bench."""
    out = []
    for _ in range(best_of):
        t = time.perf_counter()
        FP.compose(plan)
        out.append(time.perf_counter() - t)
    return min(out)


def table(best_of=3):
    print(f"{'rooms':>6}  " + "  ".join(f"{k} {v[0]}x{v[1]}".rjust(18) for k, v in SIZES.items()))
    rows = {}
    for n in COUNTS:
        cells = []
        for key, size in SIZES.items():
            dt = time_compose(make_plan(n, size), best_of=best_of)
            rows[(n, key)] = dt
            cells.append(f"{dt:.2f}s".rjust(18))
        print(f"{n:>6}  " + "  ".join(cells))
    return rows


def counts(n=3, size=FULL):
    """How many times each grid sampler runs, and how much of it is the SAME argument twice."""
    seen = {}
    orig_standable = FP.standable
    orig_pip, orig_dtb = FP.point_in_poly, FP.dist_to_boundary
    orig_strip = FP.strip_standable_fraction
    tally = {"standable": 0, "point_in_poly": 0, "dist_to_boundary": 0, "strip": 0}

    def key_of(poly, R, step):
        return (tuple((round(x, 6), round(z, 6)) for x, z in poly), R, step)

    def standable(poly, *, R=FP.R_WALK, step=FP.GRID_STEP):
        tally["standable"] += 1
        k = key_of(poly, R, step)
        seen[k] = seen.get(k, 0) + 1
        return orig_standable(poly, R=R, step=step)

    def pip(x, z, poly):
        tally["point_in_poly"] += 1
        return orig_pip(x, z, poly)

    def dtb(x, z, poly):
        tally["dist_to_boundary"] += 1
        return orig_dtb(x, z, poly)

    def strip(poly, quad, **kw):
        tally["strip"] += 1
        return orig_strip(poly, quad, **kw)

    FP.standable, FP.point_in_poly, FP.dist_to_boundary = standable, pip, dtb
    FP.strip_standable_fraction = strip
    try:
        FP.compose(make_plan(n, size))
    finally:
        FP.standable, FP.point_in_poly, FP.dist_to_boundary = orig_standable, orig_pip, orig_dtb
        FP.strip_standable_fraction = orig_strip

    print(f"{n} rooms of {size[0]}x{size[1]}:")
    for k, v in tally.items():
        print(f"  {k:22} {v:>10,}")
    dup = sum(v - 1 for v in seen.values())
    print(f"  standable DISTINCT args {len(seen):>10,}   redundant repeats {dup:,}"
          f"   ({dup / max(tally['standable'], 1) * 100:.0f}% of calls)")

    poly = make_plan(1, size)["rooms"][0]["poly"]
    poly = [(float(x), float(z)) for x, z in poly]
    x0, z0, x1, z1 = FP.bbox(poly)
    visited = (math.floor((x1 - x0) / FP.GRID_STEP) + 2) * (math.floor((z1 - z0) / FP.GRID_STEP) + 2)
    kept = len(orig_standable(poly))
    print(f"  one room: ~{visited:,} cells visited, {kept:,} kept ({kept / visited * 100:.0f}%)")
    return tally


@contextlib.contextmanager
def before_module():
    """The PRE-CHANGE composer, loaded from git, as an oracle module.

    ★ WITHOUT THIS THERE IS NO HONEST "BEFORE". The obvious shortcut -- run the CURRENT module with
    ``cache=None`` and call that the old cost -- is what produced a published "6.6s per gesture
    before" that no version of this code ever took: `compose` mints a private `GeomCache` when it is
    handed none, and the scanline samplers are in either way. The real before-number is bigger, and
    it equals the COLD number, because at HEAD a gesture WAS a cold compose -- there was no cache to
    carry. Any pair of before-numbers where the gesture is cheaper than the cold judge is wrong on
    its face.

    HEAD's `floorplan.py` uses package-relative imports, so it has to be materialised inside the
    package to import at all. Removed again on the way out, always."""
    import importlib
    import subprocess

    repo = _REPO
    pkg = repo / "ff9mapkit" / "ff9mapkit"
    dst = pkg / "_floorplan_before.py"
    src = subprocess.run(["git", "-C", str(repo), "show", "HEAD:ff9mapkit/ff9mapkit/floorplan.py"],
                         capture_output=True, text=True, check=True).stdout
    dst.write_text(src, encoding="utf-8", newline="\n")
    try:
        yield importlib.import_module("ff9mapkit._floorplan_before")
    finally:
        dst.unlink(missing_ok=True)


def _nudge(plan, which, k):
    """Move one corner of one room, which is what a drag feeds the gate.

    In Z, not X: the rooms in this bench abut along x, so nudging a middle room's corner outward in
    x drives it into its neighbour and the plan is refused for overlap before it does any of the
    work being measured. Z grows the room away from both shared walls and keeps them intact."""
    r = plan["rooms"][which]
    r["poly"] = [[x, z] for x, z in r["poly"]]
    r["poly"][2][1] += k * 3.0
    return plan


def drag(n=8, size=FULL, gestures=5):
    """THE NUMBER THAT DECIDES "LIVE": what ONE gesture costs on an ``n``-room plan.

    Reported for the END room (one door) AND a MIDDLE room (two doors, so two door strips to
    re-derive). The middle room is the honest one to quote -- it is the worse case and the common
    one -- and quoting only the end room is how two different "after" numbers ended up in the docs.
    """
    mid = n // 2

    def secs(fn):
        t = time.perf_counter()
        fn()
        return time.perf_counter() - t

    with before_module() as OLD:
        old_cold = min(secs(lambda: OLD.compose(make_plan(n, size))) for _ in range(2))
        old_drag = secs(lambda: OLD.compose(_nudge(make_plan(n, size), mid, 1)))
    print(f"{n} rooms of {size[0]}x{size[1]}")
    print(f"  BEFORE (HEAD)   cold {old_cold:5.2f}s   gesture {old_drag:5.2f}s"
          f"   <- equal, because HEAD had no cache to carry")

    print(f"  AFTER           cold {time_compose(make_plan(n, size), best_of=2):5.2f}s")
    for label, which in (("gesture, middle room (2 doors)", mid),
                         ("gesture, end room (1 door)", n - 1)):
        cache = FP.GeomCache()
        FP.compose(make_plan(n, size), cache=cache)      # the plan is already on screen
        times = []
        for g in range(gestures):
            t = time.perf_counter()
            FP.compose(_nudge(make_plan(n, size), which, g + 1), cache=cache)
            times.append(time.perf_counter() - t)
        print(f"    {label:34} {sum(times) / len(times):5.2f}s "
              f"(min {min(times):.2f} max {max(times):.2f})")
    cache = FP.GeomCache()
    plan = make_plan(n, size)
    FP.compose(plan, cache=cache)
    h0, m0 = cache.hits, cache.misses
    t = time.perf_counter()
    FP.compose(plan, cache=cache)
    print(f"    {'re-judge, nothing changed':34} {(time.perf_counter() - t) * 1000:5.1f}ms "
          f"(cache {cache.hits - h0}/{cache.hits - h0 + cache.misses - m0} hits)")


def profile(n=5, size=FULL, top=15):
    plan = make_plan(n, size)
    FP.compose(plan)                                   # warm any import-time work
    pr = cProfile.Profile()
    pr.enable()
    FP.compose(plan)
    pr.disable()
    for sort in ("cumulative", "tottime"):
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats(sort).print_stats(top)
        print(f"\n===== {n} rooms {size[0]}x{size[1]} -- by {sort} =====")
        print(s.getvalue())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", type=int, metavar="N", help="cProfile an N-room plan")
    ap.add_argument("--counts", type=int, metavar="N", help="sampler call counts for an N-room plan")
    ap.add_argument("--drag", type=int, metavar="N", help="cost of ONE gesture on an N-room plan")
    ap.add_argument("--best-of", type=int, default=3)
    ap.add_argument("--size", choices=sorted(SIZES), default="full")
    a = ap.parse_args(argv)
    if a.profile:
        profile(a.profile, SIZES[a.size])
    elif a.drag:
        drag(a.drag, SIZES[a.size])
    elif a.counts:
        counts(a.counts, SIZES[a.size])
    else:
        table(best_of=a.best_of)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
