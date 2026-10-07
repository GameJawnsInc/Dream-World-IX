"""BUILD the two files in-game experiment 2 deploys mid-run, and register the exact predictions.

  1. Block[22][14] Terrain2.ff9mesh -- the Black Mage Village cell's stock FORM-2 terrain (0_2; byte-equal to form 1
     in stock, forms lane F10) with a flattened disc: radius 12 about (1440, -928), height 26.0 (stock ground there
     ~21.52, topo-49 rock). Named "Terrain2" and served under 0_1 -- the s34 loader hard-codes 0_1 and keys on the
     child name (WMWorld.cs:823-825), forms finding F13: never loaded in-game before this run.
  2. Environment.txt -- one flag (8712 = gEventGlobal byte 1089 bit 0, FIRST_SAFE_FLAG) drives BOTH places:
        Place WaterShrine      [Condition=WorldDisc == 1 && (GetEventGlobalByte(1089) & 1) != 0]
        Place BlackMageVillage [Condition=WorldDisc == 1 && (GetEventGlobalByte(1089) & 1) != 0]

The mesh is written to the SESSION SCRATCHPAD (it is derived from game bytes -- never into the repo); the scenario
copies it into the mod folder while the game is inside a field and deletes it again before the run ends.

Rerun:  py studies/terrain-malleability/ingame/forms_build.py   -> ingame/out/forms_build.json (+ the scratch mesh)
"""
import copy
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import numpy as np                                   # noqa: E402
from ff9mapkit.world import extract as E             # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402

BX, BY = 22, 14
ORIGIN = (BX * 64.0, -BY * 64.0)
CENTER = (1440.0, -928.0)
RADIUS = 12.0
HEIGHT = 26.0
SCRATCH = Path(os.environ.get("FORMS_SCRATCH", r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                                               r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\forms"))
FLAG = 8712
COND = f"WorldDisc == 1 && (GetEventGlobalByte({FLAG >> 3}) & {1 << (FLAG & 7)}) != 0"
ENV_TEXT = (f"Place WaterShrine [Condition={COND}]\n"
            f"Place BlackMageVillage [Condition={COND}]\n")


def ground_at(bm, wx, wz):
    """First up-facing tri in buffer order containing (wx, wz) -- the engine's within-mesh rule."""
    lx, lz = wx - ORIGIN[0], wz - ORIGIN[1]
    V = np.array(bm.verts, dtype=np.float64)
    T = np.array(bm.tangents, dtype=np.float64) if bm.tangents else None
    idx = np.array(bm.flat_index).reshape(-1, 3)
    for t, (i0, i1, i2) in enumerate(idx):
        a, b, c = V[i0], V[i1], V[i2]
        u, v = b - a, c - a
        n = np.cross(u, v)
        L = np.linalg.norm(n) or 1.0
        if n[1] / L <= 0.1:
            continue
        d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(d) < 1e-12:
            continue
        w0 = ((b[2] - c[2]) * (lx - c[0]) + (c[0] - b[0]) * (lz - c[2])) / d
        w1 = ((c[2] - a[2]) * (lx - c[0]) + (a[0] - c[0]) * (lz - c[2])) / d
        w2 = 1 - w0 - w1
        if min(w0, w1, w2) < -1e-9:
            continue
        idall = int(round(T[i0][0])) if T is not None else None
        return float(w0 * a[1] + w1 * b[1] + w2 * c[1]), idall
    return None, None


def main():
    stock = E.read_block(BX, BY, disc=1, lod="0_2", part="terrain")
    form1 = E.read_block(BX, BY, disc=1, lod="0_1", part="terrain")
    same = (stock.verts == form1.verts and stock.flat_index == form1.flat_index)
    bm = copy.deepcopy(stock)
    moved = M.flatten_region(bm, radius=RADIUS, center=CENTER, height=HEIGHT, world_origin=ORIGIN)
    M.validate_blockmesh(bm)
    y0, id0 = ground_at(stock, *CENTER)
    y1, id1 = ground_at(bm, *CENTER)
    probes = {}
    for name, (dx, dz) in {"center": (0, 0), "e4": (4, 0), "n4": (0, 4), "w8": (-8, 0)}.items():
        p = (CENTER[0] + dx, CENTER[1] + dz)
        probes[name] = {"world": p, "stock": ground_at(stock, *p)[0], "flattened": ground_at(bm, *p)[0]}
    SCRATCH.mkdir(parents=True, exist_ok=True)
    mesh_path = M.write_ff9mesh(bm, SCRATCH / f"Block[{BX}][{BY}] Terrain2.ff9mesh")
    (SCRATCH / "Environment.txt").write_text(ENV_TEXT, encoding="utf-8")
    res = {"cell": [BX, BY], "form2_stock_equals_form1": same, "verts_moved": moved, "vcount": bm.vcount,
           "center": CENTER, "radius": RADIUS, "height": HEIGHT,
           "predicted": {"stock_center_y": y0, "flattened_center_y": y1, "center_idall": id0,
                         "center_topo": (id0 & 0xFC) >> 2 if id0 is not None else None, "probes": probes},
           "mesh_relpath": M.override_relpath(1, BX, BY, part="Terrain2"),
           "mesh_scratch": str(mesh_path), "env_relpath": "StreamingAssets/Data/World/Environment.txt",
           "env_text": ENV_TEXT, "flag": FLAG}
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    (out / "forms_build.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
