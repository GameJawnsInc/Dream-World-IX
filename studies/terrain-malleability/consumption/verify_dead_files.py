"""VERIFY C5's dead-file inventory: are all 939 unbound .ff9mesh files really 1-triangle blanks at y=-80, area ~0.005 u^2?

Reads out/bind_oracle.json (the lane's dead-file list per cell) and opens every dead .ff9mesh in the live mod stack
(read-only), decoding the F9WM header + positions + indices. Also re-derives, independently of bind_oracle.py, the
bound/dead split for every cell from the census prefab child names (a second implementation of the effective-prefab
rule), so a bug shared by the oracle's own counters cannot hide.

Rerun:  py studies/terrain-malleability/consumption/verify_dead_files.py
"""
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")


def read_ff9mesh(p):
    b = p.read_bytes()
    assert b[:4] == b"F9WM", p
    ver, vc, ic, fl = struct.unpack_from("<iiii", b, 4)
    off = 20
    pos = struct.unpack_from(f"<{vc * 3}f", b, off)
    off += vc * 12
    if fl & 1:
        off += vc * 12
    if fl & 2:
        off += vc * 8
    tan = None
    if fl & 4:
        tan = struct.unpack_from(f"<{vc * 4}f", b, off)
        off += vc * 16
    idx = struct.unpack_from(f"<{ic}i", b, off)
    P = [pos[i * 3:i * 3 + 3] for i in range(vc)]
    area = 0.0
    for t in range(ic // 3):
        a, c, d = P[idx[3 * t]], P[idx[3 * t + 1]], P[idx[3 * t + 2]]
        u = [c[k] - a[k] for k in range(3)]
        v = [d[k] - a[k] for k in range(3)]
        cr = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        area += 0.5 * (cr[0] ** 2 + cr[1] ** 2 + cr[2] ** 2) ** 0.5
    ys = sorted({round(p[1], 3) for p in P})
    return {"vc": vc, "ic": ic, "flags": fl, "tris": ic // 3, "area": round(area, 4), "ys": ys[:4]}


def main():
    O = json.loads((HERE / "out" / "bind_oracle.json").read_text(encoding="utf-8"))
    C = json.loads((HERE / "out" / "consumption_census.json").read_text(encoding="utf-8"))
    folders = O["folders"]
    shapes = Counter()
    n = 0
    indep_mismatch = []
    for key, cell in O["cells"].items():
        ns, xy = key.split(":")
        x, y = map(int, xy.split(","))
        # independent re-derivation of the bound set from the census child names
        eff = cell["effective"]
        children = {c["go"] for c in C["prefabs"][eff]["children"]}
        slots = C["prefabs"][eff].get("slots", {})
        for pe, why in cell["dead"].items():
            if not pe.endswith(".ff9mesh"):
                continue
            part = pe[:-len(".ff9mesh")]
            bare_obj = part == "Object" and "ObjectForm1" not in slots and "TerrainForm1" in slots
            if part in children or bare_obj:
                if not (part == "Terrain" and "TerrainForm1" not in slots):
                    indep_mismatch.append((key, pe, eff))
            for f in folders:
                p = GAME / f / "FF9_Data" / "WorldMap" / f"Disc{ns}" / "0_1" / f"r{y}" / f"Block[{x}][{y}] {part}.ff9mesh"
                if p.is_file():
                    s = read_ff9mesh(p)
                    shapes[(s["tris"], s["area"], tuple(s["ys"]), why.split(" (")[0][:40] if "arms" in why else "no-child")] += 1
                    n += 1
                    break
    print(f"dead .ff9mesh files opened: {n}")
    for k, v in shapes.most_common(20):
        print(f"  {v:5d}  tris={k[0]} area={k[1]} y={k[2]} class={k[3]}")
    print(f"independent child-name check disagreements: {len(indep_mismatch)} {indep_mismatch[:5]}")
    (HERE / "out" / "verify_dead_files.json").write_text(json.dumps(
        {"opened": n, "shapes": [[list(map(str, k)), v] for k, v in shapes.most_common()],
         "indep_mismatch": indep_mismatch}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
