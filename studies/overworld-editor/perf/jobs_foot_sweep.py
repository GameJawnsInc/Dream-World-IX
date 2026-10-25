"""Lane jobs: identity sweep of the footprint prefilter prototype (jobs_census_proto P2) beyond the one call a Check
makes. A real forest Check runs in-process with interior.forest_footprint_lawful wrapped to capture its (soup, tri_c,
poly); the CLI's own rim polygon is then translated to N random centres over the island soup's extent (passes and
refusals both), and the unpatched law and the patched one are called on each: (return value, why list) must be ==.

    py studies/overworld-editor/perf/jobs_foot_sweep.py N [seed]     -> out/perf/jobs/foot_sweep.json
"""
import contextlib
import io
import json
import random
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402
import jobs_census_proto as CP  # noqa: E402


def main():
    n = int(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 11
    from ff9mapkit import cli
    from ff9mapkit.world import interior as IN
    orig = IN.forest_footprint_lawful
    cap = {}

    def capture(soup, tri_c, poly, why=None):
        cap.update(soup=soup, tri_c=tri_c, poly=list(poly))
        return orig(soup, tri_c, poly, why)
    IN.forest_footprint_lawful = capture
    rep = Path(tempfile.mkdtemp(prefix="jobs_fs_")) / "verdict.json"
    with contextlib.redirect_stdout(io.StringIO()):
        cli.main(J.check_argv("forest", J.draft(), rep)[3:])
    IN.forest_footprint_lawful = orig
    CP.install_p2()
    wrapper = IN.forest_footprint_lawful               # P2 + its timer (no verify)
    IN.forest_footprint_lawful = orig
    soup, tri_c, poly = cap["soup"], cap["tri_c"], cap["poly"]
    cx = sum(p[0] for p in poly) / len(poly)
    cz = sum(p[1] for p in poly) / len(poly)
    xs = [c[0] for c in tri_c]
    zs = [c[1] for c in tri_c]
    rng = random.Random(seed)
    t_o = t_p = 0.0
    passes = same = 0
    for k in range(n):
        tx, tz = rng.uniform(min(xs), max(xs)), rng.uniform(min(zs), max(zs))
        if k == 0:
            tx, tz = cx, cz                              # the Check's own placement first
        pl = [(x - cx + tx, z - cz + tz) for x, z in poly]
        w1, w2 = [], []
        t = time.perf_counter()
        r1 = orig(soup, tri_c, pl, w1)
        t_o += time.perf_counter() - t
        t = time.perf_counter()
        r2 = wrapper(soup, tri_c, pl, w2)
        t_p += time.perf_counter() - t
        assert r1 == r2 and w1 == w2, (k, r1, r2, w1, w2)
        same += 1
        passes += r1 is not None
    rec = {"calls": n, "identical": same, "lawful_results": passes, "orig_s": t_o, "patched_s": t_p,
           "speedup": t_o / t_p if t_p else None, "soup_tris": len(soup["tris"]), "poly_pts": len(poly),
           "fallbacks": CP.STATS["foot_fallback"]}
    print(json.dumps(rec))
    (J.OUT / "foot_sweep.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
