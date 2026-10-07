"""STEP 12 -- ENTRANCE EDITS: story removal, or a root laid over an entrance footprint?

For every block whose entrance tiles changed (anatomy.json event_transitions): count entrance samples (event
bits != 0, engine-faithful sky-cast, 1u lattice) on each disc, and the disc-4 topograph + rise at the samples
that LOST their entrance. A place that keeps most of its entrance and loses only samples now under raised
topo-49 rock = footprint trimmed by a ridge; a place that loses ALL of it = the place closed.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/entrance_check.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402
from d4lib import X                                  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
ana = json.loads((OUT / "anatomy.json").read_text(encoding="utf-8"))
objs = L.mesh_objects()
out = []
for k, r in sorted(ana["blocks"].items(), key=lambda kv: -sum(v for *_, v in kv[1]["event_transitions"])):
    if not r["event_transitions"]:
        continue
    b = tuple(r["block"])
    g = {}
    for d in (1, 4):
        parts = {p: L.decode(o, d, x, y, lod) for (dd, lod, x, y, p), o in objs.items()
                 if dd == d and lod == "0_1" and (x, y) == b}
        ml, _ = L.meshlist_for(parts)
        g[d] = L.ground_grid(ml, 1.0)
    e1 = {s for s, v in g[1].items() if v[1] != "MISS" and X.decode_id(v[2])["event"]}
    e4 = {s for s, v in g[4].items() if v[1] != "MISS" and X.decode_id(v[2])["event"]}
    lost = e1 - e4
    lt = Counter(g[4][s][3] for s in lost)
    rise = [g[4][s][0] - g[1][s][0] for s in lost if g[4][s][1] != "MISS"]
    rec = {"block": list(b), "landmark": r.get("landmark"), "entr_d1": len(e1), "entr_d4": len(e4),
           "kept": len(e1 & e4), "lost": len(lost), "gained": len(e4 - e1),
           "lost_d4_topo": dict(lt.most_common(4)),
           "lost_rise_mean": round(sum(rise) / len(rise), 2) if rise else None,
           "event_ids_d1": dict(Counter(X.decode_id(g[1][s][2])["event"] for s in e1)),
           "event_ids_d4": dict(Counter(X.decode_id(g[4][s][2])["event"] for s in e4))}
    v = ("CLOSED (all entrance tiles gone)" if e1 and not e4 else
         "NEW entrance" if e4 and not e1 else
         "TRIMMED by raised rock" if lost and lt.get(49, 0) >= 0.6 * len(lost) else
         "GROWN (footprint enlarged)" if (e4 - e1) and not lost else
         "RE-ID'd" if not lost and set(rec["event_ids_d1"]) != set(rec["event_ids_d4"]) else
         "reshaped" if lost or (e4 - e1) else "same")
    rec["verdict"] = v
    out.append(rec)
    print(f"  {str(b):9s} ~{r.get('landmark')}: d1 {len(e1):4d} d4 {len(e4):4d} kept {len(e1 & e4):4d} "
          f"lost {len(lost):3d} gained {len(e4 - e1):4d} lost->topo {dict(lt.most_common(3))} rise "
          f"{rec['lost_rise_mean']}  ids {rec['event_ids_d1']}->{rec['event_ids_d4']}  => {v}")
print("verdicts:", dict(Counter(r["verdict"] for r in out)))
(OUT / "entrance_check.json").write_text(json.dumps(out, indent=0, default=str), encoding="utf-8")
print("->", OUT / "entrance_check.json")
