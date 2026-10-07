"""CAPACITY lane, step 6 -- FORM 1 (0_1) vs FORM 2 (0_2): is 0_2 a decimated far LOD (fewer, larger tris
everywhere) or a story-state ALTERNATE (same mesh, local edits)? Per switchable block, per part present in
both dirs: tri counts, the tri-soup symmetric difference (tris compared as sorted vertex triples rounded to
1/1024 u, plus their IDALL), and the XZ bbox of the changed tris. Also: IDALL (event/area/topograph) deltas.

Calibration: a far LOD would show tris_0_2 << tris_0_1 and ~0 shared tris; an alternate form shows most
tris shared verbatim. Block (12,10) has no 0_2 (not switchable) -> must be absent from the output.

Writes out/form_diff.json.   Run:  py studies/terrain-malleability/capacity/form_diff.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ff9mapkit.world import extract as X  # noqa: E402
from census import decode, PAT  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def soup(V, T, I):
    tri = I.reshape(-1, 3)
    keys = []
    for a, b, c in tri:
        pts = sorted(tuple(np.round(V[k] * 1024).astype(np.int64).tolist()) for k in (a, b, c))
        idall = int(round(T[a, 0])) if T is not None else -1
        keys.append((tuple(pts), idall))
    return keys


def main():
    env = X._worldmap_env(1)
    idx = X._mesh_index(env)
    meshes = {}
    for c, o in idx.items():
        m = PAT.search(c)
        if m:
            meshes[(int(m.group(1)), m.group(2), int(m.group(4)), int(m.group(3)), m.group(6))] = o
    res = []
    for (disc, d, x, y, part), o2 in sorted(meshes.items()):
        if d != "0_2":
            continue
        o1 = meshes.get((disc, "0_1", x, y, part))
        V2, U2, T2, I2, *_ = decode(o2.read())
        if o1 is None:
            res.append({"disc": disc, "x": x, "y": y, "part": part, "only_in_0_2": True, "tris2": len(I2) // 3})
            continue
        V1, U1, T1, I1, *_ = decode(o1.read())
        s1, s2 = Counter(soup(V1, T1, I1)), Counter(soup(V2, T2, I2))
        shared = sum((s1 & s2).values())
        only1, only2 = s1 - s2, s2 - s1
        ch = [p for (pts, _), n in (only1 + only2).items() for p in pts]
        bbox = None
        if ch:
            a = np.array(ch, dtype=float) / 1024.0
            bbox = [round(a[:, 0].min(), 2), round(a[:, 2].min(), 2), round(a[:, 0].max(), 2), round(a[:, 2].max(), 2)]
        geo1 = Counter(p for p, _ in s1.elements())
        geo2 = Counter(p for p, _ in s2.elements())
        res.append({"disc": disc, "x": x, "y": y, "part": part, "tris1": len(I1) // 3, "tris2": len(I2) // 3,
                    "shared": shared, "only1": sum(only1.values()), "only2": sum(only2.values()),
                    "geo_shared": sum((geo1 & geo2).values()), "changed_bbox_local_xz": bbox})
    (OUT / "form_diff.json").write_text(json.dumps(res, indent=0), encoding="utf-8")
    ter = [r for r in res if r["part"] == "terrain" and r["disc"] == 1]
    print("disc1 TERRAIN form1 vs form2 (x,y): tris1 tris2 shared only1 only2 geo_shared bbox")
    for r in ter:
        print(f"  ({r['x']:2d},{r['y']:2d}) {r['tris1']:4d} {r['tris2']:4d} shared={r['shared']:4d} "
              f"only1={r['only1']:3d} only2={r['only2']:3d} geo_shared={r['geo_shared']:4d} bbox={r['changed_bbox_local_xz']}")
    tot1 = sum(r["tris1"] for r in ter)
    sh = sum(r["shared"] for r in ter)
    print(f"disc1 terrain: {sh}/{tot1} form-1 tris shared VERBATIM (geometry+IDALL) with form 2 = {sh / tot1:.3f}")
    print("blocks with identical terrain in both forms:", [(r['x'], r['y']) for r in ter if r['only1'] == 0 and r['only2'] == 0])
    obj = [r for r in res if r["part"] == "object" and r["disc"] == 1 and "tris1" in r]
    print("disc1 OBJECT form1->form2 shared fraction:",
          round(sum(r['shared'] for r in obj) / max(1, sum(r['tris1'] for r in obj)), 3),
          "| objects only in 0_2:", [(r['x'], r['y']) for r in res if r.get('only_in_0_2') and r['disc'] == 1])


if __name__ == "__main__":
    main()
