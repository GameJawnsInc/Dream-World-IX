"""SKEPTIC check for lane jobs, candidates P1 (census precompute) and P2 (footprint prefilter). The lane's prototypes
(jobs_census_proto.install_p1 / install_p2) are imported unchanged; what is new here:

  stock   P1 against the unpatched placement.census on STOCK blocks the lane's sweep never saw (it swept the draft's
          126 DEPLOYED blocks): every stock block with a prefab on disc 1 and disc 4, its whole stock part stack
          (every part the prefab carries, read_block, build_meshlist order), frame block_local; == block by block,
          and both must raise alike where the original raises.
  check   the lane's in-process both-ways verify during a real Check (every patched call computed both ways and
          asserted ==; the run's verdict == a fresh unpatched child's), re-run here with its output redirected to
          out/perf/jobs/verify/ (the lane's own evidence file is not touched).

    py studies/overworld-editor/perf/verify_jobs_kernels.py stock [step]        -> out/perf/jobs/verify/census_stock.json
    py studies/overworld-editor/perf/verify_jobs_kernels.py check <verb> P1 [P2] -> out/perf/jobs/verify/proto_verify.json
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs_common as J  # noqa: E402
import jobs_census_proto as CP  # noqa: E402

VOUT = J.OUT / "verify"
VOUT.mkdir(parents=True, exist_ok=True)


def stock(step):
    from ff9mapkit.world import extract as X
    from ff9mapkit.world import placement as P
    orig = P.census
    CP.install_p1()
    patched = P.census
    P.census = orig
    rec = {"by_disc": {}}
    t_o = t_p = 0.0
    for disc in (1, 4):
        parts = X.block_parts(disc=disc, game=J.GAME)
        keys = sorted(parts)[::step]
        n = same = raised = 0
        for k, (bx, by) in enumerate(keys):
            pb = {}
            for p in sorted(parts[(bx, by)]):
                cp = P.canonical_part(p)
                if cp is None:
                    continue
                try:
                    pb[cp] = X.read_block(bx, by, disc=disc, part=p, game=J.GAME)
                except Exception:                        # noqa: BLE001 -- a part read_block cannot decode: skip it
                    continue
            if "Terrain" not in pb:
                continue
            ml = P.build_meshlist(pb)
            out = {}
            arms = [("o", orig), ("p", patched)] if k % 2 == 0 else [("p", patched), ("o", orig)]
            for tag, fn in arms:
                t = time.perf_counter()
                try:
                    out[tag] = ("ok", fn(ml, frame="block_local"))
                except ValueError as e:
                    out[tag] = ("raise", str(e))
                dt = time.perf_counter() - t
                if tag == "o":
                    t_o += dt
                else:
                    t_p += dt
            n += 1
            raised += out["o"][0] == "raise"
            same += out["o"] == out["p"]
            assert out["o"] == out["p"], (disc, bx, by)
        rec["by_disc"][disc] = {"blocks": n, "identical": same, "both_raised": raised}
        print(disc, rec["by_disc"][disc], flush=True)
    rec.update(orig_s=t_o, patched_s=t_p, speedup=t_o / t_p if t_p else None)
    print(json.dumps(rec))
    (VOUT / "census_stock.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")


def main():
    mode = sys.argv[1]
    if mode == "stock":
        stock(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
        return
    if mode in ("check", "time"):                        # time: the lane's alternating-children timer, N verb P..
        import shutil
        shutil.copy2(J.OUT / "spots.json", VOUT / "spots.json")   # check_argv reads J.OUT/spots.json: same spots
        J.OUT = VOUT                                     # jobs_census_proto writes J.OUT/proto_*.json at call time
        sys.argv = [CP.__file__, "verify" if mode == "check" else "time"] + sys.argv[2:]
        CP.main()
        return
    raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
