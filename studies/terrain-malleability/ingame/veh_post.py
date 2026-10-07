"""Score a veh_session run's recorded samples against the LIVE mesh (and the lab meshes the phase deployed), offline.

    py studies/terrain-malleability/ingame/veh_post.py <.harness-runs/... run dir> [--phase-mesh <ff9mesh>]

Reads whichever veh_session<N>.json the run wrote (the scenario dir under the run dir, or the run dir itself) and
prints, per sample set:
  session1  S5: every sample's y against the ground under it (sky cast, IgnoreExceptions = the flight cast): the
            registered claim is y <= 42.1875 + 0.004 everywhere and y == 42.1875 wherever ground > 42.1875.
  session2  V3 rows: y - ground at each sample's exact x/z (prediction -1.171875 on topo 36/37/38, else 0); edge
            traces: the topograph under every sample (yellow must never stand on 51/53-55; light blue must).
  session3  N1/N3: the stall position's radius and the topograph one step further out (must be 15).
  session4  lane samples inside the cell: y against (the window-ray water y - 0.703) on the phase mesh.
"""
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import veh_prep as P                                  # noqa: E402


def _find(run: Path):
    for p in [run] + [d for d in run.iterdir() if d.is_dir()]:
        for n in (1, 2, 3, 4):
            f = p / f"veh_session{n}.json"
            if f.is_file():
                return n, json.loads(f.read_text(encoding="utf-8"))
    raise SystemExit(f"no veh_session*.json under {run}")


def s1(rec):
    rows = rec.get("S5", {}).get("samples", [])
    bad, over = [], 0
    for r in rows:
        if r["x"] is None:
            continue
        q = P.query(r["x"], r["z"], ignore_exc=True, veto=False)
        gy = None if q is None else q["y"]
        if r["y"] is not None and r["y"] > P.CEILING + 0.004:
            bad.append(("above ceiling", r))
        if gy is not None and gy > P.CEILING:
            over += 1
            if abs(r["y"] - P.CEILING) > 0.004:
                bad.append(("not at ceiling over tall ground", r, gy))
    print(f"S5: {len(rows)} samples, {over} over ground > 42.1875, violations {len(bad)}")
    for b in bad[:10]:
        print("  ", b)


def s2(rec):
    for who in ("yellow", "lightblue"):
        r = rec.get(who, {})
        for k in ("forest", "lawn"):
            for row in r.get(k, []):
                if row.get("x") is None:
                    continue
                q = P.query(row["x"], row["z"])
                print(f"{who} {k} {row['after']:>12}: y {row['y']:.4f} ground {q['y']:.4f} topo {q['topo']} "
                      f"dy {row['y'] - q['y']:+.4f}")
        tr = r.get("edge", {}).get("trace", [])
        tps = []
        for row in tr:
            if row.get("x") is None:
                continue
            q = P.query(row["x"], row["z"])
            tps.append((round(row.get("progress", 0), 2), None if q is None else q["topo"], row.get("y")))
        print(f"{who} edge: outcome {r.get('edge', {}).get('outcome')} topos {tps}")


def s3(rec):
    from veh_build import BX, BY                       # noqa: F401  (the cell)
    b = json.loads((HERE / "out" / "veh_build.json").read_text(encoding="utf-8"))
    ex = {"Terrain": b["mesh"]}
    cx, cz = b["centres"]["A"]["world"]
    for k in ("N1", "N3"):
        e = rec.get(k, {}).get("end")
        if not e or e.get("x") is None:
            continue
        r = math.hypot(e["x"] - cx, e["z"] - cz)
        ux, uz = (e["x"] - cx) / r, (e["z"] - cz) / r
        q = P.query(e["x"] + ux * 1.0, e["z"] + uz * 1.0, ignore_exc=True, veto=False, extra=ex)
        print(f"{k}: stalled at r {r:.3f}, 1u further out topo {None if q is None else q['topo']}")


def s4(rec, mesh):
    ex = {"Terrain": mesh} if mesh else None
    for lane in ("open", "rim"):
        rows = [r for r in rec.get(lane + "_samples", []) if r.get("x") is not None and r["x"] > P.BOAT_CELL[0] * 64]
        dev = []
        for r in rows:
            q = P.query(r["x"], r["z"], origin_y=(r["y"] or 0) + P.RAY_UP, extra=ex)
            if q is not None and r["y"] is not None:
                dev.append(round(r["y"] - (q["y"] + P.SLICE_BOAT), 4))
        print(f"{lane}: {len(rows)} in-cell samples, y - (water - 0.703) range "
              f"{(min(dev), max(dev)) if dev else None}; end {rec.get(lane, {}).get('end')}")
        # [review] where the hull was first slid, against its measured heading (veh_lib.first_deflection)
        hd = rec.get("hull_heading")
        start = rec.get(lane + "_samples", [{}])[0] if rec.get(lane + "_samples") else None
        if hd is not None and start and start.get("x") is not None:
            from veh_lib import first_deflection
            d = first_deflection(rec.get(lane + "_samples", []), start["x"], start["z"], hd, P.BOAT_CELL[0] * 64)
            print(f"   {lane}: outcome {rec.get(lane, {}).get('outcome')} into {rec.get(lane, {}).get('into')}, "
                  f"first slide {d}, recorded contact {rec.get(lane, {}).get('contact')}")


def main(argv):
    run = Path(argv[1])
    mesh = argv[argv.index("--phase-mesh") + 1] if "--phase-mesh" in argv else None
    n, rec = _find(run)
    print(f"veh_session{n} ({rec.get('phase', '')})")
    {1: s1, 2: s2, 3: s3}.get(n, lambda r: s4(r, mesh))(rec)


if __name__ == "__main__":
    main(sys.argv)
