"""Lane jobs: PROTOTYPE (a monkeypatch in this script; the package is not edited) of two compute kernels the card
Checks spend most of their own time in, each compared against the unpatched code in the same script.

  P1 "census": placement.census with a per-census PER-TRIANGLE PRECOMPUTE. place()/all_sheets() recompute, for every
     candidate triangle at every one of the 576 samples, things that depend only on the triangle: int(round(idall)),
     the IDALL_SKIP test, the walkable-normal test (ny/L <= 0.1) and the barycentric denominator d. The patch computes
     each once per triangle per census (same expressions, same float operands, so the same IEEE results) and memoises
     decode_id's topograph per idall; the sample loop does only the barycentric part. Same scan order, same
     first-hit break, same dedup -- the census dict must come out ==.
  P2 "foot": interior.forest_footprint_lawful with an exact bounding-box prefilter before pip()/near_poly(): a point
     whose z is outside the rim polygon's [zmin, zmax] has no ray crossing (pip False, exactly), and a point more than
     SCAN_BAND + 1e-6 outside the polygon's box is farther than SCAN_BAND from every edge (near_poly False, exactly).
     Disabled (falls back to the original) if the polygon has an edge with 0 < |dz| < 1e-6, the one case where pip's
     1e-12 guard could move a crossing far along x.

    py jobs_census_proto.py verify <verb> [P1] [P2]   # in-process: every patched call computed BOTH ways, asserted ==,
                                                       # and the run's verdict JSON == the unpatched run's
    py jobs_census_proto.py time N <verb> [P1] [P2]    # alternating fresh children, unpatched vs patched
    (child) py jobs_census_proto.py child <verb> <out.json> [P1] [P2]
"""
import contextlib
import io
import json
import math
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402

STATS = {"census_calls": 0, "census_equal": 0, "foot_calls": 0, "foot_equal": 0, "foot_fallback": 0,
         "census_s": 0.0, "foot_s": 0.0}


# ------------------------------------------------------------------ P1: the census precompute
def install_p1(verify=False):
    from ff9mapkit.world import placement as P
    orig_census = P.census
    IDALL_SKIP, VETO, INDEX_GRID = P.IDALL_SKIP, P.VETO, P.INDEX_GRID
    SKY, WALK = P.SKY_RAY_START, P.WALK_RAY_START
    DEDUP, GAPMIN, WALK_OK = P.SHEET_DEDUP_EPS, P.STACK_GAP_MIN, P.WALK_OK
    topo_memo = {}

    def topo_of(idall):
        t = topo_memo.get(idall, topo_memo)
        if t is topo_memo:
            t = topo_memo[idall] = P._decode_topo(idall)
        return t

    def pre(bm):
        V, T, fi = bm.verts, bm.tangents, bm.flat_index
        out = []
        for t in range(len(fi) // 3):
            idx = fi[3 * t:3 * t + 3]
            idall = int(round(T[idx[0]][0]))
            if idall in IDALL_SKIP:
                out.append(None)
                continue
            a, b, c = V[idx[0]], V[idx[1]], V[idx[2]]
            ux, uy, uz = b[0]-a[0], b[1]-a[1], b[2]-a[2]
            vx, vy, vz = c[0]-a[0], c[1]-a[1], c[2]-a[2]
            ny = uz * vx - ux * vz
            L = math.sqrt((uy*vz-uz*vy)**2 + ny*ny + (ux*vy-uy*vx)**2) or 1.0
            if ny / L <= 0.1:
                out.append(None)
                continue
            d = (b[2]-c[2])*(a[0]-c[0]) + (c[0]-b[0])*(a[2]-c[2])
            if abs(d) < 1e-12:
                out.append(None)
                continue
            out.append((idall, a[1], b[1], c[1], c[0], c[2], b[2]-c[2], c[0]-b[0], c[2]-a[2], a[0]-c[0], d))
        return out

    def place_p(meshlist, pres, x, z, y, index):
        origin_y = y + SKY
        gx, gz = math.floor(x / INDEX_GRID), math.floor(z / INDEX_GRID)
        for mi, (name, _bm) in enumerate(meshlist):
            pr = pres[mi]
            hit = None
            for t in index[mi].get((gx, gz), ()):
                r = pr[t]
                if r is None:
                    continue
                idall, ay, by_, cy, cx_, cz_, bzc, cxb, cza, axc, d = r
                w0 = (bzc*(x-cx_) + cxb*(z-cz_)) / d
                w1 = (cza*(x-cx_) + axc*(z-cz_)) / d
                w2 = 1 - w0 - w1
                if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                    continue
                hy = w0*ay + w1*by_ + w2*cy
                if hy > origin_y:
                    continue
                hit = (hy, idall)
                break
            if hit is not None:
                if hit[1] == VETO:
                    continue
                return hit[0], name, hit[1], topo_of(hit[1])
        return 0.0, "MISS", 0, None

    def sheets_p(meshlist, pres, x, z, index):
        eps = 1e-5
        out = []
        gx, gz = math.floor(x / INDEX_GRID), math.floor(z / INDEX_GRID)
        for mi, (name, _bm) in enumerate(meshlist):
            pr = pres[mi]
            for t in index[mi].get((gx, gz), ()):
                r = pr[t]
                if r is None:
                    continue
                idall, ay, by_, cy, cx_, cz_, bzc, cxb, cza, axc, d = r
                if idall == VETO:
                    continue
                w0 = (bzc*(x-cx_) + cxb*(z-cz_)) / d
                w1 = (cza*(x-cx_) + axc*(z-cz_)) / d
                w2 = 1 - w0 - w1
                if w0 < eps or w1 < eps or w2 < eps:
                    continue
                hy = w0*ay + w1*by_ + w2*cy
                if any(abs(hy - y0) <= DEDUP for (y0, _, _, _) in out):
                    continue
                out.append((hy, name, idall, topo_of(idall)))
        return out

    def census_p(meshlist, *, span=(2.0, 62.0, -62.0, -2.0), samples=24, y=0.0, frame=None):
        x0, x1, z0, z1 = span
        if frame == "block_local":                 # placement.census's own frame assert, verbatim
            blks = {(bm.x, bm.y) for _, bm in meshlist
                    if getattr(bm, "x", None) is not None and getattr(bm, "y", None) is not None}
            if len(blks) > 1:
                raise ValueError(f"block_local census: meshes span blocks {sorted(blks)} -- "
                                 "one block-local stack per census")
            if not (0.0 <= min(x0, x1) and max(x0, x1) <= 64.0
                    and -64.0 <= min(z0, z1) and max(z0, z1) <= 0.0):
                raise ValueError(f"block_local census: span {span} outside the block frame "
                                 "[0,64] x [-64,0]")
        elif frame not in (None, "world"):
            raise ValueError(f"unknown census frame {frame!r} (block_local or world)")
        counts = P.collections.Counter()
        miss, points, stacked, inversions = [], [], [], []
        P.check_registration_order(meshlist)
        index = P.build_meshlist_index(meshlist)
        pres = [pre(bm) for _, bm in meshlist]
        for i in range(samples):
            for j in range(samples):
                px = x0 + (x1 - x0) * i / (samples - 1)
                pz = z0 + (z1 - z0) * j / (samples - 1)
                gy, name, idall, topo = place_p(meshlist, pres, px, pz, y, index)
                counts[(name, topo)] += 1
                points.append((px, pz, gy, name, topo))
                if name == "MISS":
                    miss.append((px, pz))
                walk = [s for s in sheets_p(meshlist, pres, px, pz, index) if s[3] in WALK_OK]
                if len(walk) >= 2:
                    ys = sorted((s[0] for s in walk), reverse=True)
                    if ys[0] - ys[1] < GAPMIN:
                        continue
                    rec = {"at": (px, pz), "gap": round(ys[0] - ys[1], 3),
                           "sheets": [(round(s[0], 3), s[1], s[3]) for s in walk],
                           "shadowed": name != "MISS" and ys[0] - gy > DEDUP}
                    stacked.append(rec)
                    if rec["shadowed"]:
                        inversions.append(rec)
        return {"counts": dict(counts), "miss": miss, "points": points, "stacked": stacked,
                "inversions": inversions}

    def census(meshlist, **kw):
        STATS["census_calls"] += 1
        t = time.perf_counter()
        out = census_p(meshlist, **kw)
        STATS["census_s"] += time.perf_counter() - t
        if verify:
            ref = orig_census(meshlist, **kw)
            assert ref == out, "census differs"
            STATS["census_equal"] += 1
        return out
    P.census = census


def install_timer_only():
    """The unpatched run, with the same timers (so both arms carry the same wrapper)."""
    from ff9mapkit.world import interior as IN
    from ff9mapkit.world import placement as P
    oc, of = P.census, IN.forest_footprint_lawful

    def census(meshlist, **kw):
        STATS["census_calls"] += 1
        t = time.perf_counter()
        try:
            return oc(meshlist, **kw)
        finally:
            STATS["census_s"] += time.perf_counter() - t

    def foot(*a, **k):
        STATS["foot_calls"] += 1
        t = time.perf_counter()
        try:
            return of(*a, **k)
        finally:
            STATS["foot_s"] += time.perf_counter() - t
    P.census = census
    IN.forest_footprint_lawful = foot


# ------------------------------------------------------------------ P2: the footprint prefilter
def install_p2(verify=False):
    from ff9mapkit.world import interior as IN
    orig = IN.forest_footprint_lawful
    pip, near_poly, X = IN.pip, IN.near_poly, IN.X

    def patched(soup, tri_c, poly, why=None):
        zs = [p[1] for p in poly]
        xs = [p[0] for p in poly]
        n = len(poly)
        if any(0.0 < abs(poly[(i + 1) % n][1] - poly[i][1]) < 1e-6 for i in range(n)):
            STATS["foot_fallback"] += 1
            return orig(soup, tri_c, poly, why)
        band = IN.SCAN_BAND
        m = band + 1e-6
        zmin, zmax, xmin, xmax = min(zs), max(zs), min(xs), max(xs)
        bx0, bx1, bz0, bz1 = xmin - m, xmax + m, zmin - m, zmax + m

        def hit_at(x, z):
            if x < bx0 or x > bx1 or z < bz0 or z > bz1:
                return False                       # outside the band box: pip and near_poly are both False
            return pip(x, z, poly) or near_poly(x, z, poly, band)
        gpos, gtris, gmeta = soup["pos"], soup["tris"], soup["meta"]
        seen = 0
        for tidx, tri in enumerate(gtris):
            cx, cz = tri_c[tidx]
            hit = hit_at(cx, cz)
            if not hit:
                hit = any(hit_at(gpos[i][0], gpos[i][2]) for i in tri)
            if not hit:
                continue
            seen += 1
            _, idall, fam, _ = gmeta[tidx]
            topo = X.decode_id(int(round(idall)))["topograph"]
            if fam != "main" or topo != 0:
                if why is not None:
                    why.append(((cx, cz), IN.ground_words(fam, topo)))
                return None
            for i in tri:
                if IN._coast_d2(soup, gpos[i][0], gpos[i][2]) < IN.RIM_MARGIN ** 2:
                    if why is not None:
                        why.append(((gpos[i][0], gpos[i][2]), "the coast rim"))
                    return None
        return seen

    def wrapper(soup, tri_c, poly, why=None):
        STATS["foot_calls"] += 1
        w2 = [] if why is not None else None
        t = time.perf_counter()
        out = patched(soup, tri_c, poly, w2)
        STATS["foot_s"] += time.perf_counter() - t
        if verify:
            w1 = [] if why is not None else None
            ref = orig(soup, tri_c, poly, w1)
            assert ref == out and w1 == w2, ("footprint differs", ref, out, w1, w2)
            STATS["foot_equal"] += 1
        if why is not None:
            why.extend(w2)
        return out
    IN.forest_footprint_lawful = wrapper
    # carve_forest calls it through footprint_lawful in the same module (a module-global name lookup)


def run_check(verb):
    from ff9mapkit import cli
    d = J.draft()
    rep = Path(tempfile.mkdtemp(prefix=f"jobs_cp_{verb}_")) / "verdict.json"
    argv = J.check_argv(verb, d, rep)[3:]
    t = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            code = cli.main(argv)
        except SystemExit as e:
            code = e.code
    return time.perf_counter() - t, code, json.loads(rep.read_text(encoding="utf-8"))


def child(verb, out, patches):
    if patches:
        if "P1" in patches:
            install_p1()
        if "P2" in patches:
            install_p2()
        if "P1" not in patches or "P2" not in patches:  # the other arm's timer
            from ff9mapkit.world import interior as IN
            from ff9mapkit.world import placement as P
            if "P1" not in patches:
                oc = P.census

                def census(meshlist, **kw):
                    STATS["census_calls"] += 1
                    t = time.perf_counter()
                    try:
                        return oc(meshlist, **kw)
                    finally:
                        STATS["census_s"] += time.perf_counter() - t
                P.census = census
            if "P2" not in patches:
                of = IN.forest_footprint_lawful

                def foot(*a, **k):
                    STATS["foot_calls"] += 1
                    t = time.perf_counter()
                    try:
                        return of(*a, **k)
                    finally:
                        STATS["foot_s"] += time.perf_counter() - t
                IN.forest_footprint_lawful = foot
    else:
        install_timer_only()
    s, code, v = run_check(verb)
    Path(out).write_text(json.dumps({"cli_main_s": s, "code": code, "verdict": v, **STATS}), encoding="utf-8")


def main():
    mode = sys.argv[1]
    if mode == "child":
        child(sys.argv[2], sys.argv[3], [a for a in sys.argv[4:] if a in ("P1", "P2")])
        return
    if mode == "verify":
        verb = sys.argv[2]
        patches = [a for a in sys.argv[3:] if a in ("P1", "P2")] or ["P1", "P2"]
        # the unpatched verdict first, in a fresh child (no patch at all)
        tmp = Path(tempfile.mkdtemp(prefix="jobs_cpv_"))
        subprocess.run([sys.executable, __file__, "child", verb, str(tmp / "ref.json")], cwd=str(J.kit_cwd()),
                       check=True)
        ref = json.loads((tmp / "ref.json").read_text(encoding="utf-8"))["verdict"]
        if "P1" in patches:
            install_p1(verify=True)
        if "P2" in patches:
            install_p2(verify=True)
        s, code, v = run_check(verb)
        same = json.dumps(v, sort_keys=True) == json.dumps(ref, sort_keys=True)
        rec = {"verb": verb, "patches": patches, "verdict_identical": same, "ok": v.get("ok"), **STATS}
        print(json.dumps(rec))
        p = J.OUT / "proto_verify.json"
        allv = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        allv[f"{verb}:{'+'.join(patches)}"] = rec
        p.write_text(json.dumps(allv, indent=1), encoding="utf-8")
        assert same
        return
    if mode == "time":
        from jobs_wall import job_env
        n, verb = int(sys.argv[2]), sys.argv[3]
        patches = [a for a in sys.argv[4:] if a in ("P1", "P2")] or ["P1", "P2"]
        arms = {"unpatched": [], "patched": []}
        verdicts = {}
        for i in range(n):
            for arm in ("unpatched", "patched") if i % 2 == 0 else ("patched", "unpatched"):
                out = Path(tempfile.mkdtemp(prefix="jobs_cpt_")) / "r.json"
                extra = patches if arm == "patched" else []
                t = time.perf_counter()
                subprocess.run([sys.executable, __file__, "child", verb, str(out)] + extra, cwd=str(J.kit_cwd()),
                               env=job_env(), check=True)
                wall = time.perf_counter() - t
                r = json.loads(out.read_text(encoding="utf-8"))
                r["wall"] = wall
                verdicts.setdefault(arm, set()).add(json.dumps(r.pop("verdict"), sort_keys=True))
                arms[arm].append(r)
                print(f"{verb} {arm:9s} wall {wall:5.2f} cli.main {r['cli_main_s']:5.2f} census {r['census_s']:5.2f} "
                      f"({r['census_calls']}) foot {r['foot_s']:5.2f} ({r['foot_calls']})", flush=True)
        summ = {}
        for arm, rs in arms.items():
            summ[arm] = {k: {"min": round(min(r[k] for r in rs), 3),
                             "median": round(statistics.median(r[k] for r in rs), 3)}
                         for k in ("wall", "cli_main_s", "census_s", "foot_s")}
        summ["verdicts_identical_across_arms"] = verdicts["unpatched"] == verdicts["patched"] and \
            len(verdicts["unpatched"]) == 1
        print(json.dumps(summ, indent=1))
        p = J.OUT / "proto_time.json"
        allt = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        allt[f"{verb}:{'+'.join(patches)}"] = {"summary": summ, "runs": arms}
        p.write_text(json.dumps(allt, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
