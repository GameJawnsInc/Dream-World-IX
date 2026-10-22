"""THE RAISED STEP (STEP.md): carry comp26's and comp10's walled canopy with their rock, as the alcove floor.
Offline only; writes nothing but out/step_*.json.

  spec       each donor's alcove spec by the registered rule: the canopy component behind the rim's step (topo 36-38,
             flooded whole from the canopy tris on the bare rim), a box round its plan extent +0.5u in the first donor
             block's local frame, y_min 0.5u under its lowest vertex, the floor = its own topograph
  anatomy    T2: with the spec, the carried non-rock tris, the step edges left on the rim, the steepest rim edge
  sweep      T1, T3-T6: the control (Uaho, grass) and each donor with and without its canopy, six angles, every gate
RUN:  py studies/terrain-malleability/mountaindonors/step_carry.py anatomy|sweep
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sweep as S  # noqa: E402  (the lane's bench: CENTRE, ROTS, seeds)

CANOPY = frozenset({36, 37, 38})
DONORS = {"comp26": ([(14, 3), (15, 3)], "desert"), "comp10": ([(14, 14), (15, 14), (16, 14)], "grass")}
STEP_PLAN, STEP_RISE, CLIMB = 0.1, 1.0, 2.34375


def canopy_spec(blocks):
    """The registered rule -> ``((x0, x1), (z0, z1), y_min, (topo,))`` and the component's size."""
    IN, _, _ = S._kit()
    kk3 = IN.kk3
    B = IN._mountain_blob(blocks, rock_topos=frozenset(IN.MOUNTAIN_ROCK_TOPOS), alcove_box=None, log=lambda *a: None)
    dV, dtri, dtopo, d_edge, blob = B["dV"], B["dtri"], B["dtopo"], B["d_edge"], B["blob"]
    rimk = {kk3(p) for p in B["rim"]}
    seeds = [t for t in range(len(dtri)) if t not in blob and dtopo[t] in CANOPY
             and any(kk3(dV[i]) in rimk for i in dtri[t])]
    comp, st = set(), list(seeds)
    while st:
        t = st.pop()
        if t in comp or t in blob or dtopo[t] not in CANOPY:
            continue
        comp.add(t)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            for t2 in d_edge[tuple(sorted((kk3(dV[dtri[t][a]]), kk3(dV[dtri[t][b]]))))]:
                if t2 not in comp:
                    st.append(t2)
    topos = sorted({dtopo[t] for t in comp})
    if len(topos) != 1:
        raise SystemExit(f"{blocks}: canopy behind the step mixes topographs {topos}")
    P = np.array([dV[i] for t in comp for i in dtri[t]])
    doff = np.array([64.0 * blocks[0][0], 0.0, -64.0 * blocks[0][1]])
    L = P - doff
    spec = ((round(float(L[:, 0].min()) - 0.5, 3), round(float(L[:, 0].max()) + 0.5, 3)),
            (round(float(L[:, 2].min()) - 0.5, 3), round(float(L[:, 2].max()) + 0.5, 3)),
            round(float(P[:, 1].min()) - 0.5, 3), (topos[0],))
    return spec, len(comp)


def specs():
    return {name: canopy_spec(blocks) for name, (blocks, _) in DONORS.items()}


def anatomy():
    IN, _, _ = S._kit()
    rock = frozenset(IN.MOUNTAIN_ROCK_TOPOS)
    out = {}
    for name, (blocks, ground) in DONORS.items():
        spec, ncomp = canopy_spec(blocks)
        B = IN._mountain_blob(blocks, rock_topos=rock, alcove_box=spec, log=lambda *a: None)
        rim = B["rim"]
        n = len(rim)
        steps = [k for k in range(n) if math.hypot(rim[k][0] - rim[(k + 1) % n][0], rim[k][2] - rim[(k + 1) % n][2])
                 < STEP_PLAN and abs(rim[k][1] - rim[(k + 1) % n][1]) > STEP_RISE]
        rises = [abs(rim[k][1] - rim[(k + 1) % n][1]) for k in range(n)]
        nonrock = Counter(B["dtopo"][t] for t in B["blob"] if B["dtopo"][t] not in rock)
        out[name] = {"spec": spec, "canopy_component": ncomp, "blob_tris": len(B["blob"]),
                     "carried_non_rock": dict(nonrock), "rim_pts": n, "steps_left": steps,
                     "max_rim_rise": round(max(rises), 3), "r_rim": round(B["r_rim"], 1),
                     "rim_y": [round(min(p[1] for p in rim), 2), round(max(p[1] for p in rim), 2)],
                     "apertures": [len(r) for r in B["apertures"]], "sweep": len(B["sweep"])}
        r = out[name]
        t2 = (sum(nonrock.values()) == ncomp and len(nonrock) == 1 and not steps and r["max_rim_rise"] <= CLIMB)
        print(f"{name}: spec {spec}; canopy component {ncomp}; carried non-rock {dict(nonrock)}; rim {n} pts y "
              f"{r['rim_y']}; steps left {steps}; max rim rise {r['max_rim_rise']}; r_rim {r['r_rim']}; T2 "
              f"{'holds' if t2 else 'FALSIFIED'}")
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "step_anatomy_spec.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    return out


def _job(job):
    name, rot, mode = job
    IN, _, _ = S._kit()
    if name == "uaho":
        donor, ground, alcove, rr = [(0, 0)], "grass", "auto", 20.0
    else:
        donor, ground = DONORS[name]
        spec, _ = canopy_spec(donor)
        alcove = spec if mode == "canopy" else None
        B = IN._mountain_blob(donor, rock_topos=frozenset(IN.MOUNTAIN_ROCK_TOPOS), alcove_box=spec,
                              log=lambda *a: None)
        rr = B["r_rim"]                                  # the bench sizes to the CARRIED blob (canopy included)
    radius = math.ceil(rr + 28.0)
    out = {"name": name, "mode": mode, "rot": rot, "ground": ground, "bench_r": radius}
    lines = []
    try:
        blocks, seed = S.bench(radius, ground)
        out["seed"] = seed
        res = IN.carve_mountain(IN.soup_from_blocks(blocks), near=S.CENTRE, donor=donor, rot_deg=rot, ground=ground,
                                alcove=alcove, log=lines.append)
        IN.census_gate(res["changed"], disc=1, baseline=blocks, parts=IN.census_parts(res), log=lines.append)
        rep = res["report"]
        out.update(ok=True, center=res["center"], **{k: rep.get(k) for k in (
            "blob_tris", "plugs", "zip_rise", "rock_rigid", "apron_slope", "peak_y")})
    except Exception as err:                                                    # noqa: BLE001
        out.update(ok=False, error=f"{type(err).__name__}: {err}"[:400])
    out["gates"] = next((str(x) for x in reversed(lines) if str(x).startswith("gates:")), None)
    out["zip_line"] = next((str(x) for x in reversed(lines) if "zipNyMin" in str(x)), None)
    out["log"] = [str(x)[:220] for x in lines[-40:]]
    return out


def sweep():
    jobs = [("uaho", r, "auto") for r in S.ROTS]
    for name in DONORS:
        jobs += [(name, r, m) for m in ("canopy", "bare") for r in S.ROTS]
    with ProcessPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(_job, jobs))
    for r in rows:
        print(f"{r['name']:7s} {r['mode']:6s} {r['rot']:>4} r{r['bench_r']} "
              + (f"ok   centre {r['center']} zip-rise {r.get('zip_rise')} rigid {r.get('rock_rigid')} apron "
                 f"{r.get('apron_slope')}" if r["ok"] else f"FAIL {r['error'][:170]}"))
    for name, mode in [("uaho", "auto")] + [(n, m) for n in DONORS for m in ("canopy", "bare")]:
        okr = [r["rot"] for r in rows if r["name"] == name and r["mode"] == mode and r["ok"]]
        print(f"{name} {mode}: {len(okr)}/{len(S.ROTS)} {okr}")
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "step_sweep.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    {"anatomy": anatomy, "sweep": sweep}[sys.argv[1]]()
