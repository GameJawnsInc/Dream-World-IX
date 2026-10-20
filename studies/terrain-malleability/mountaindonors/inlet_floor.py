"""THE INLET FLOOR (INLET.md): carry comp9's inlet floor with its rock, closing the rim across the inlet mouth on low
snow, by the Uaho alcove-floor carry (`_mountain_blob`'s alcove box) with the floor's own topograph (snow, 27).
Offline only; writes nothing but out/inlet_*.json.

  anatomy        comp9's blob with and without the inlet: rim points, longest rim edge, steepest rim rise, rings,
                 Object apertures, and the floor tris the inlet adds (topographs, heights, event bits).
  hashes OUT     every catalogued donor carved at rot 0 on a bench of its home ground; sha256 of every written
                 block and part. Run once before the kit change and once after: the files must be equal.
  sweep          the control (Uaho, grass) and comp9 with the inlet (snow) at the six sweep angles; comp9 without
                 the inlet alongside, today's refusal.
RUN:  py studies/terrain-malleability/mountaindonors/inlet_floor.py anatomy|hashes OUT.json|sweep
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import sys
import tempfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sweep as S  # noqa: E402  (the lane's bench: CENTRE, ROTS, seeds, sizing radius + 28)

COMP9 = [(8, 0), (8, 1), (9, 0), (9, 1), (10, 0)]
# The inlet: snow between rim points 71 and 83 (comp9_diagnose.py), west of its 11.4u mouth at x ~589. The box is in
# the FIRST donor block's local frame, (8,0): world x 577-589.5 -> local 65-77.5; z unchanged (block row 0).
# y_min 3.0 sits under the inlet snow (3.3-4.1); the floor topograph is the massif's home ground, snow.
COMP9_INLET = ((65.0, 77.5), (-100.0, -79.5), 3.0, (27,))
CATALOGUED = {"uaho": ([(0, 0)], 20.0, "grass"), "crag": ([(10, 5), (10, 6)], 33.7, "desert"),
              "horseshoe": ([(5, 15), (6, 15), (5, 16), (6, 16)], 54.3, "grass"),
              "comp20": ([(12, 16), (12, 17)], 31.5, "grass"), "desert-peak": ([(19, 3)], 26.1, "desert")}
JOBS = {"uaho": ([(0, 0)], 20.0, "grass", "auto"), "comp9-inlet": (COMP9, 65.3, "snow", COMP9_INLET),
        "comp9-bare": (COMP9, 65.3, "snow", None)}


def _kit():
    return S._kit()


def anatomy():
    IN, _, _ = _kit()
    from ff9mapkit.world import extract as X
    rock = frozenset(IN.MOUNTAIN_ROCK_TOPOS)
    out = {}
    for name, box in (("bare", None), ("inlet", COMP9_INLET)):
        lines = []
        B = IN._mountain_blob(COMP9, rock_topos=rock, alcove_box=box, log=lines.append)
        rim = B["rim"]
        n = len(rim)
        el = [math.hypot(rim[k][0] - rim[(k + 1) % n][0], rim[k][2] - rim[(k + 1) % n][2]) for k in range(n)]
        dy = [abs(rim[k][1] - rim[(k + 1) % n][1]) for k in range(n)]
        floor = [t for t in B["blob"] if B["dtopo"][t] not in rock]
        ys = [B["dV"][i][1] for t in floor for i in B["dtri"][t]]
        ev = Counter(X.decode_id(int(round(B["dT"][B["dtri"][t][0]][0])))["event"] for t in floor)
        out[name] = {"blob_tris": len(B["blob"]), "non_rock_tris": len(floor),
                     "non_rock_topos": dict(Counter(B["dtopo"][t] for t in floor)),
                     "non_rock_y": [round(min(ys), 2), round(max(ys), 2)] if ys else None,
                     "non_rock_event_bits": {str(k): v for k, v in ev.items()},
                     "rim_pts": n, "rim_L0": round(max(el), 2), "rim_max_rise": round(max(dy), 2),
                     "apertures": [len(r) for r in B["apertures"]],
                     "aperture_pts": [[list(p) for p in r] for r in B["apertures"]],
                     "ensemble_apertures": len(B["ensemble_apertures"]), "sweep": len(B["sweep"]),
                     "r_rim": round(B["r_rim"], 1), "log": [str(x) for x in lines]}
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("log", "aperture_pts")} for k, v in out.items()},
                     indent=1))
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "inlet_anatomy.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")


def _bytes_of(M, bm):
    tmp = Path(tempfile.mkdtemp(prefix="ff9_inlet_hash_"))
    try:
        return M.write_ff9mesh(bm, tmp / "m.ff9mesh").read_bytes()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _hash_one(name):
    IN, M, _ = _kit()
    donor, r, ground = CATALOGUED[name]
    blocks, seed = S.bench(math.ceil(r + 28.0), ground)
    res = IN.carve_mountain(IN.soup_from_blocks(blocks), near=S.CENTRE, donor=donor, rot_deg=0, ground=ground,
                            log=lambda *a: None)
    h = {}
    for blk, bm in sorted(res["changed"].items()):
        h[f"terrain {blk}"] = hashlib.sha256(_bytes_of(M, bm)).hexdigest()
    for blk, parts in sorted((res.get("changed_parts") or {}).items()):
        for part, bm in sorted(parts.items()):
            h[f"{part} {blk}"] = hashlib.sha256(_bytes_of(M, bm)).hexdigest()
    return name, {"seed": seed, "center": list(res["center"]), "files": h}


def hashes(path):
    with ProcessPoolExecutor(max_workers=4) as ex:
        got = dict(ex.map(_hash_one, list(CATALOGUED)))
    p = Path(path)
    if p.exists():
        old = json.loads(p.read_text())
        same = {n: old[n] == got[n] for n in CATALOGUED}
        print("byte-identical to", p.name, same, "ALL" if all(same.values()) else "DIFFERS")
        return 0 if all(same.values()) else 1
    p.write_text(json.dumps(got, indent=1), encoding="utf-8")
    print("wrote", p, {n: len(v["files"]) for n, v in got.items()})
    return 0


def _sweep_one(job):
    name, rot = job
    IN, M, _ = _kit()
    donor, r, ground, alcove = JOBS[name]
    out = {"name": name, "rot": rot, "ground": ground, "bench_r": math.ceil(r + 28.0)}
    lines = []
    try:
        blocks, seed = S.bench(math.ceil(r + 28.0), ground)
        res = IN.carve_mountain(IN.soup_from_blocks(blocks), near=S.CENTRE, donor=donor, rot_deg=rot, ground=ground,
                                alcove=alcove, log=lines.append)
        IN.census_gate(res["changed"], disc=1, baseline=blocks, parts=IN.census_parts(res), log=lines.append)
        rep = res["report"]
        out.update(ok=True, center=res["center"], **{k: rep.get(k) for k in (
            "blob_tris", "plugs", "zip_rise", "rock_rigid", "apron_slope", "blocks")})
    except Exception as err:                                                    # noqa: BLE001
        out.update(ok=False, error=f"{type(err).__name__}: {err}"[:400])
    out["gates"] = next((str(x) for x in reversed(lines) if str(x).startswith("gates:")), None)
    out["log"] = [str(x)[:220] for x in lines[-40:]]
    return out


def sweep():
    jobs = [(n, r) for n in JOBS for r in S.ROTS]
    with ProcessPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(_sweep_one, jobs))
    for r in rows:
        print(f"{r['name']:12s} {r['rot']:>4} {'ok  ' if r['ok'] else 'FAIL'} "
              + (f"centre {r['center']} plugs {r.get('plugs')} zip-rise {r.get('zip_rise')} rigid {r.get('rock_rigid')}"
                 if r["ok"] else r["error"][:200]))
        if r.get("gates"):
            print(f"{'':18s}{r['gates'][:200]}")
    for n in JOBS:
        okr = [r["rot"] for r in rows if r["name"] == n and r["ok"]]
        print(f"{n}: {len(okr)}/{len(S.ROTS)} angles pass {okr}")
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "inlet_sweep.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "anatomy":
        anatomy()
    elif mode == "hashes":
        sys.exit(hashes(sys.argv[2]))
    elif mode == "sweep":
        sweep()
    else:
        raise SystemExit(__doc__)
