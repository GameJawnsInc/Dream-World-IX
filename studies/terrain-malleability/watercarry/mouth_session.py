"""The owner's open observation (PLAN.md "The CLI verb"): the two shallow triangles at the river mouth's beach corners
"look a little weird" on the LIVE river (FF9CustomMap-world, 512,128). `mouth_compare.py` found every water, beach and
river tri round the mouth byte-identical to home bar decision 1's area stamp (5/16 -> 14, outside every area range the
engine renders by), and named the two: a Sea1 tri at the W corner and a Sea2 tri at the E corner, each with a vertex
lifted to y 0.535 (every other sea tri there is flat at 0).

This puts the two side by side in ONE launch, so both share one environment: for each pose, face on the open lawn,
then a still at the LIVE mouth and a still at HOME's mouth from the same relative spot (home = live + (1024, -128)).
Nothing is installed: the live river is already in FF9CustomMap-world, and home is stock (no live folder overrides
cluster C).
RUN:  py studies/terrain-malleability/watercarry/mouth_session.py          (prep: the poses -> out/mouth_poses.json)
      py tools/play.py studies/terrain-malleability/watercarry/mouth_session.py --label world-river-mouth
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
POSES = HERE / "out" / "mouth_poses.json"
HOME_SHIFT = (1024.0, -128.0)                          # live -> home (block offset (8,-2) undone, x wrapped)
SETTLE = 180
TOL_Y = 0.15


def prep():
    """Each pose's live and home spots, their ground heights (the engine's rules over the live bytes and over stock),
    and the bearing at the mouth. Home must read the same height as live: the carry is verbatim there."""
    import lab_prep as P                                   # the engine-rules simulator over the lab (= live) bytes
    comp = json.loads((HERE / "out" / "mouth_compare.json").read_text(encoding="utf-8"))
    mx, _, mz = comp["mouth_live"]
    spots = {"deck": (7.687, -829.258), "beach_E": (38.0, -861.0), "beach_W": (4.0, -875.0)}
    poses = []
    for name, (x, z) in spots.items():
        ql, qh = P.query(x, z), P.query(x + HOME_SHIFT[0], z + HOME_SHIFT[1])
        poses.append({"name": name, "live": [x, z], "home": [x + HOME_SHIFT[0], z + HOME_SHIFT[1]],
                      "y_live": None if ql is None else round(ql["y"], 3), "y_home": None if qh is None else round(qh["y"], 3),
                      "topo": None if ql is None else ql["topo"],
                      "bearing_deg": round(math.degrees(math.atan2(mz - z, mx - x)), 2)})
    POSES.write_text(json.dumps({"mouth_live": comp["mouth_live"], "poses": poses}, indent=1), encoding="utf-8")
    print(json.dumps(poses, indent=1))


def run(g):
    sys.path.insert(0, str(HERE))
    import lab_session as S                                # FACE_AT, face(), the 6603 route via veh_lib
    data = json.loads(POSES.read_text(encoding="utf-8"))
    rec = {"lane": "world-river mouth", "poses": data["poses"], "shots": {}}
    out = g.run_dir / "mouth_session.json"
    g.note("world-river: the river mouth's beach corners, live vs home, one launch")
    srec = {}
    S.V.reach_world_as(g, srec, scenario=0, pokes={}, expect_world=0, first=True)
    g.no_encounters()
    g.check(g.state.on_world, "on the world map", json.dumps(srec.get("arrival")))
    for p in data["poses"]:
        try:
            g.teleport(*S.FACE_AT)
            f = S.face(g, p["bearing_deg"], S.FACE_AT, srec, p["name"])
            r = {"heading": f["heading"], "error": f["error"]}
            for site in ("live", "home"):
                g.teleport(*p[site])
                g.wait_frames(SETTLE)
                shot = g.shot(f"mouth-{p['name']}-{site}")
                at = S.V.settle3(g)
                r[site] = {"at": at, "shot": shot.name}
                want = p[f"y_{site}"]
                g.check(at["y"] is not None and want is not None and abs(at["y"] - want) <= TOL_Y,
                        f"{p['name']} {site}: stands where the rules say", f"y={at['y']} want {want}")
            g.check(abs(f["error"]) <= S.TOL_FACE, f"{p['name']}: faced the mouth", f"heading {f['heading']:.1f}")
            rec["shots"][p["name"]] = r
        except Exception as err:                                        # noqa: BLE001  (one pose must not cost the rest)
            rec.setdefault("errors", {})[p["name"]] = str(err)[:400]
            g.check(False, f"{p['name']}: completed", str(err)[:200])
        out.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    prep()
