"""OFFLINE PREP for the vehicle sessions (veh_session1-4). READ-ONLY on the install; writes only
studies/terrain-malleability/ingame/out/veh_prep.json and scratch meshes under the session scratchpad.

What it does, in order (every number a veh_session scenario asserts against comes from here):
  1. ROUTE EVIDENCE from the LIVE bytes the game will run (first FolderNames folder that serves each file, `us`):
     * the field-6603 (FARSHORE) exit trigger: the records it writes ([64..72] player, [83..91] chocobo), the
       region key, and the dispatcher its cascade picks per ScenarioCounter band (decode_switch on the real bytes);
     * per dispatcher 9003/9007/9008: Main_Init's InitObject gates (SC threshold for the vehicle actor, [191] for
       the chocobo) and each vehicle actor's Init: the `[190] == mode` arm that runs AttachObject +
       DefinePlayerCharacter (control binds to the vehicle AT LOAD), and the record it is placed from
       (Global.Int24[74]/Int16[77]/Int24[79]/Byte[82] for boat/airships, [83]/[86]/[88]/[91] for the chocobo).
  2. AIRSHIP points on disc 1 (veh_session1): SUMMIT (rank 5), HIGH (floor-raise instrument), LOW (spawn), SEA
     (V13 refuse), L1 (V13 land), L3 (V13 .eb-policy refuse) -- with an OFFLINE SIMULATION of
     ff9.w_movementGetGetoff (ff9.cs:5746-5917) for Hilda Garde III over 72 headings, so the registered landing
     prediction is heading-invariant.
  3. CHOCOBO points (veh_session2): the session-1b canopy pair (forest topo 37 / lawn topo 0) re-measured on the live
     mesh, and a SHORE->SHALLOW edge where the yellow chocobo (row 1 = the walking mask) must stop and the light-blue
     chocobo (row 2, flg_gake 1) must pass (shore topo 30-35 is neither ground nor water, ff9.cs:5703-5717).
  4. NO-FLY cell (veh_session3, rank 12): an isolated all-sea cell; the ring geometry veh_build.py emits.
  5. BOAT (veh_session4, rank 7): the (12,10) free-ride path through a sidecar-less reclaimed cell, simulated per
     deploy phase (flat 6.0 / flat 1.2 / island / cliff) with the engine's boat round check (window ray from the hull
     y + 2.34375, first registered mesh, first passing tri in buffer order, 10-slot cache, 8 slide angles each side,
     topo mask {53,54,57}); plus a STOCK-coast control (no deploy).

Rerun (from the repo root):  py studies/terrain-malleability/ingame/veh_prep.py
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TM = HERE.parent
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
sys.path.insert(0, str(TM / "gap_area_layer"))
sys.path.insert(0, str(HERE))
import numpy as np                                    # noqa: E402
import arealib as A                                   # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
SCRATCH = Path(os.environ.get("VEH_SCRATCH", r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                                             r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\veh"))
OUT = HERE / "out"

# --------------------------------------------------------------------------------------------- engine constants
SKIP = (4078, 4088, 2040)                 # WMPhysics.cs:16-20 (skipped unless IgnoreExceptions)
VETO = 0x31EE                             # WMBlock.cs:211 (abandons the mesh unless control type 1)
RAY_UP = 2.34375                          # ff9.cs:1328 rayStartOffsetY (non-sky ray origin above pos.y)
SLICE_BOAT = -180 / 256.0                 # ff9.cs:5489-5491 control 7 -> slice_height S(-180)
CEILING = 42.1875                         # ff9.cs:5518-5521
LAND_DY = 350 / 256.0                     # ff9.cs:5887 S(350)
HG3_R = 640 / 256.0                       # TransportControls row 8 radius 640 -> S(640) = 2.5u
BOAT_TERMINAL = (240 * 128 / 4) / 256.0 / 32.0   # ff9.cs:6235-6237: S(speed_move*128/p1)/p3 = 0.9375 u/tick


def _mask(l0, l1):
    return {t for t in range(64) if ((l0 >> (t - 32)) & 1 if t > 31 else (l1 >> t) & 1)}


def transport_rows():
    """The live TransportControls.csv rows (first folder that serves it) -> {row: (limit0, limit1, flg_gake)}."""
    for f in folder_names():
        p = GAME / f / "StreamingAssets" / "Data" / "World" / "TransportControls.csv"
        if p.is_file():
            rows = []
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                s = line.split("#")[0].strip()
                if not s:
                    continue
                c = [v for v in s.split(";") if v != ""]
                if len(c) >= 19 and c[0].lstrip("-").isdigit():
                    rows.append((int(c[17]), int(c[18]), int(c[1]), int(c[2]), int(c[13])))
            return {"source": f"{f}/StreamingAssets/Data/World/TransportControls.csv",
                    "rows": {i: {"limit0": r[0], "limit1": r[1], "flg_gake": r[2], "speed_move": r[3], "radius": r[4]}
                             for i, r in enumerate(rows)}}
    return {"source": "stock (no CSV)", "rows": {}}


WALK = _mask(1074815, 3640605951)                 # row 0 (identical to row 1, yellow chocobo)
LBLUE = _mask(553150079, 3640605951)              # row 2
AIR = _mask(2147444351, 3640605951)               # rows 8/9
BOAT = _mask(39845888, 0)                         # row 7 = {53, 54, 57}
GROUND_ST = _mask(0x5C126670, 0x18FF3CFF)         # ff9.cs:9971-9975 w_movementGroundStatus
WATER_ST = _mask(0x23ED0000, 0)                   # ff9.cs:18 w_movementWaterStatus


def topo(idall):
    return (int(idall) & 0xFC) >> 2


# --------------------------------------------------------------------------------------------- live files
def folder_names():
    ini = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', ini, re.M)
    return re.findall(r'"([^"]*)"', m.group(1)) if m else []


def served(rel):
    """(folder, path) of the first FolderNames folder serving `rel` (case-insensitive leaf), else (None, None)."""
    for f in folder_names():
        p = GAME / f / rel
        if p.is_file():
            return f, p
        d = p.parent
        if d.is_dir():
            for q in d.iterdir():
                if q.name.lower() == p.name.lower():
                    return f, q
    return None, None


EB_WORLD = "StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world/us/EVT_WORLD_WORLD{:02d}.eb.bytes"
EB_FARSHORE = "StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/us/EVT_FARSHORE.eb.bytes"


# --------------------------------------------------------------------------------------------- 1. route evidence
def _lines(eb, entry, tag):
    from ff9mapkit.eb import cmdasm
    f = next(f for f in eb.entry(entry).funcs if f.tag == tag)
    return cmdasm.disassemble_block(eb.data, f.abs_start, f.abs_end).splitlines()


def route_evidence():
    from ff9mapkit.eb.model import EbScript
    from ff9mapkit.eb import disasm as D
    out = {"folder_names": folder_names()}
    # --- 6603's exit trigger (entry 3 tag 2) ---
    fold, path = served(EB_FARSHORE)
    eb = EbScript(path.read_bytes())
    f = next(f for f in eb.entry(3).funcs if f.tag == 2)
    ins = list(D.iter_code(eb.data, f.abs_start, f.abs_end))
    idx = {i.off: k for k, i in enumerate(ins)}

    def first_worldmap(off):
        k = idx[off]
        while k < len(ins):
            i = ins[k]
            if i.name.startswith("WorldMap"):
                return i.args[0]
            if i.name == "JMP":
                k = idx[D.jump_target(i)]
                continue
            if i.name == "RET":
                return None
            k += 1
        return None

    sw = []
    for i in ins:
        if i.is_switch and i.name == "op_0B":
            si = D.decode_switch(i)
            m = {e.value: e.target for e in si.edges if not e.is_default}
            dflt = next(e.target for e in si.edges if e.is_default)
            sw.append({"off": i.off, "base": si.base, "key35": first_worldmap(m.get(35, dflt))})
    text = "\n".join(_lines(eb, 3, 2))
    out["field6603"] = {
        "served_by": fold,
        "writes": re.findall(r"SET\(\{Global\.(?:Int24|Int16|Byte)\[(\d+)\] (?:const4?)\((-?\d+)\) B_LET", text),
        "region_key": 35 if "Global.Int16[2] const(35) B_LET" in text else None,
        "worldmap_override_var": "Global.Int16[1062]" if "WorldMap({Global.Int16[1062]" in text else None,
        # the four op_0B switches in source order are the SC bands <5990 / 5990-10399 (not 9615-9790) / 10400-11089 / >=11090
        "cascade_key35": [s["key35"] for s in sw],
    }
    # --- dispatchers ---
    disp = {}
    for n, veh_entry, mode, rec in ((3, 6, 7, 74), (7, 6, 8, 74), (8, 6, 9, 74)):
        fold, path = served(EB_WORLD.format(n))
        eb = EbScript(path.read_bytes())
        mi = "\n".join(_lines(eb, 0, 0))
        gate = re.search(r"Global\.UInt16\[0\] const\((\d+)\) B_GE B_EXPR_END\}\)\nJMP_IFNOT\(L\d+\)\nInitObject\(6, 0\)", mi)
        cgate = bool(re.search(r"Global\.Byte\[191\] const\(0\) B_NE B_EXPR_END\}\)\nJMP_IFNOT\(L\d+\)\nInitObject\(5, 0\)", mi))
        vi = "\n".join(_lines(eb, veh_entry, 0))
        arm = re.search(r"Global\.Byte\[190\] const\((\d+)\) B_EQ B_EXPR_END\}\)\nJMP_IFNOT\(L\d+\)\nop_22\(1\)\n"
                        r"AttachObject\((\d+), (\d+), (\d+)\)", vi)
        binds = "DefinePlayerCharacter()" in vi.split("JMP(L")[0] if arm else False
        mv = re.search(r"MoveInstantXZY\(\{Global\.Int24\[(\d+)\] B_EXPR_END\}, \{Global\.Int16\[(\d+)\] B_EXPR_END\}, "
                       r"\{Global\.Int24\[(\d+)\] B_EXPR_END\}\)\nTurnInstant\(\{Global\.Byte\[(\d+)\]", vi)
        ci = "\n".join(_lines(eb, 5, 0))
        carm = re.search(r"Global\.Byte\[190\] const\(1\) B_GE Global\.Byte\[190\] const\(6\) B_LE B_ANDAND B_EXPR_END\}\)\n"
                         r"JMP_IFNOT\(L\d+\)\nop_22\(1\)\nAttachObject\((\d+), 5, 23\)\nDefinePlayerCharacter\(\)", ci)
        cmv = re.search(r"MoveInstantXZY\(\{Global\.Int24\[(\d+)\]", ci)
        disp[9000 + n] = {
            "served_by": fold,
            "vehicle_initobject_sc_gate": int(gate.group(1)) if gate else None,
            "chocobo_initobject_191_gate": cgate,
            "vehicle_mode_arm": int(arm.group(1)) if arm else None,
            "vehicle_attach": [int(arm.group(k)) for k in (2, 3, 4)] if arm else None,
            "vehicle_binds_control_at_load": binds,
            "vehicle_record": [int(mv.group(k)) for k in (1, 2, 3, 4)] if mv else None,
            "chocobo_arm_1_6_binds": bool(carm),
            "chocobo_record_x": int(cmv.group(1)) if cmv else None,
            "chocobo_hidden_unless_bit810": "Global.Bit[810] B_NOT" in ci,
            "expected_mode": mode,
        }
    out["dispatchers"] = disp
    out["transport"] = transport_rows()
    return out


# --------------------------------------------------------------------------------------------- geometry
_CELLS = None
_MESH = {}


def live_cells():
    global _CELLS
    if _CELLS is None:
        _CELLS = A.live_cells()
    return _CELLS


def cell_meshes(bx, by, disc=1, extra=None):
    """[(name, V, ids)] in registration order for a cell; `extra` = {part: ff9mesh path} hypothetical overrides
    (a lab deploy), routed through the same bind oracle the live scan uses."""
    key = (bx, by, disc, tuple(sorted((extra or {}).items())))
    if key in _MESH:
        return _MESH[key]
    cf = dict(live_cells().get((disc, bx, by), {}))
    for part, p in (extra or {}).items():
        cf[f"{part}.ff9mesh"] = [(0, "FF9CustomMap-lab", Path(p), 0.0)]
    if cf:
        pk, why, walk = A.live_walk_list(disc, bx, by, cf)
    else:
        pk, why = "stock", "stock"
        walk = [(n, k, "stock") for n, k in A.stock_walk_list(disc, bx, by)]
    arrs = A.load_walk_arrays(walk)
    res = {"prefab": pk, "why": why, "walk": [(n, k) for n, _s, k in walk], "meshes": arrs}
    _MESH[key] = res
    return res


def _prep_mesh(V):
    a, b, c = V[:, 0], V[:, 1], V[:, 2]
    u, v = b - a, c - a
    cx = u[:, 1] * v[:, 2] - u[:, 2] * v[:, 1]
    cy = u[:, 2] * v[:, 0] - u[:, 0] * v[:, 2]
    cz = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
    L = np.sqrt(cx * cx + cy * cy + cz * cz)
    L[L == 0] = 1.0
    d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
    return a, b, c, cy / L, d


def _hit_in_mesh(V, ids, lx, lz, origin_y, ignore_exc, veto, tri_filter=None):
    """First tri in BUFFER order hit by the vertical ray down from origin_y (None = from the sky), or None.
    Standard filters (skip ids, geometric ny > 0.1) unless ignore_exc. Returns (tri, y, id) or ('VETO', ...)."""
    if V.size == 0:
        return None
    a, b, c, ny, d = _prep_mesh(V)
    ok = np.abs(d) >= 1e-12
    if not ignore_exc:
        ok &= (ny > 0.1) & ~np.isin(ids, SKIP)
    if tri_filter is not None:
        ok &= tri_filter
    dd = np.where(ok, d, 1.0)
    w0 = ((b[:, 2] - c[:, 2]) * (lx - c[:, 0]) + (c[:, 0] - b[:, 0]) * (lz - c[:, 2])) / dd
    w1 = ((c[:, 2] - a[:, 2]) * (lx - c[:, 0]) + (a[:, 0] - c[:, 0]) * (lz - c[:, 2])) / dd
    w2 = 1 - w0 - w1
    hy = w0 * a[:, 1] + w1 * b[:, 1] + w2 * c[:, 1]
    inside = ok & (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
    if origin_y is not None:
        inside &= hy <= origin_y + 1e-9
    hits = np.nonzero(inside)[0]
    if hits.size == 0:
        return None
    t = int(hits[0])
    idv = int(ids[t])
    if veto and idv == VETO:
        return ("VETO", float(hy[t]), idv)
    return (t, float(hy[t]), idv)


def query(x, z, *, origin_y=None, ignore_exc=False, veto=True, disc=1, extra=None):
    """The engine ground query at world (x, z): first registered walk mesh with a passing hit (a veto first-hit
    abandons that mesh), first passing tri in buffer order. origin_y None = the sky cast."""
    bx, by = int(math.floor(x / 64.0)), int(math.floor(-z / 64.0))
    cm = cell_meshes(bx, by, disc, extra)
    lx, lz = x - bx * 64.0, z + by * 64.0
    for mi, (name, V, ids) in enumerate(cm["meshes"]):
        h = _hit_in_mesh(V, ids, lx, lz, origin_y, ignore_exc, veto)
        if h is None or h[0] == "VETO":
            continue
        return {"y": round(h[1], 4), "id": h[2], "topo": topo(h[2]), "part": name, "mesh": mi, "tri": h[0],
                "cell": [bx, by]}
    return None


def ground(x, z, **kw):
    q = query(x, z, **kw)
    return None if q is None else q["y"]


# --------------------------------------------------------------------------------------------- 2. airship
SPECIAL = [((191.875, -474.25), 3.75), ((189.2, -475.2), 10.12), ((1088.0, -952.4), 18.5), ((896.4, -350.0), 10.0)]


def getoff_hg3(ax, az, heading, *, policy=range(0, 14)):
    """ff9.w_movementGetGetoff case 8 (ff9.cs:5774-5807, 5839-5915) for Hilda Garde III at world (ax, az), hull yaw
    `heading` (deg), then the WORLD07 .eb Cancel arm (entry 3 func 1: y != 10000 -> topo under the airship in 0..13).
    Returns {"engine": accept|refuse:<why>, "eb": land|refuse, "point": [x, z] | None, "dist": u, "heading_index"}."""
    for (cx, cz), r in SPECIAL:
        if math.hypot(ax - cx, az - cz) < r:
            return {"engine": "refuse:special-zone", "eb": "refuse"}
    own = query(ax, az)                                   # pre-check ray (non-sky, standard filters) ~ the top surface
    if own is None or own["topo"] not in WALK:
        return {"engine": f"refuse:own-tile topo {None if own is None else own['topo']} not foot-legal", "eb": "refuse"}
    if own["topo"] in (45, 46, 52):
        return {"engine": f"refuse:own-tile topo {own['topo']}", "eb": "refuse"}
    under = query(ax, az, ignore_exc=True, veto=False)    # status ground_height (flight cast, IgnoreExceptions)
    g_air = under["y"]
    for k12 in range(8):
        n = k12 * 22.5
        for i in (0, 1):
            rot = (n + 270.0) % 360.0 if i == 0 else (-n + 270.0)
            ok = True
            last = None
            for j in range(1, 9):
                num13 = 8 if (i == 0 and k12 == 0 and j == 8) else 5
                dist = HG3_R * j / num13
                d = math.radians(heading + 180.0 + rot)
                px, pz = ax + math.sin(d) * dist, az + math.cos(d) * dist
                q = query(px, pz, ignore_exc=True, veto=False)
                if q is None or q["topo"] not in WALK:
                    ok = False
                last = (px, pz, q)
            if not ok:
                continue
            px, pz, q = last
            if abs(g_air - q["y"]) > LAND_DY:
                continue
            res = {"engine": "accept", "point": [round(px, 3), round(pz, 3)], "dist": round(math.hypot(px - ax, pz - az), 3),
                   "heading_index": [k12, i], "topo_under": under["topo"], "y_land": q["y"]}
            res["eb"] = "land" if under["topo"] in policy else "refuse"
            return res
    return {"engine": "refuse:no heading passes", "eb": "refuse", "topo_under": under["topo"]}


def getoff_all_headings(ax, az):
    rows = [getoff_hg3(ax, az, h) for h in range(0, 360, 5)]
    eng = {r["engine"] for r in rows}
    ebs = {r["eb"] for r in rows}
    dists = sorted({r.get("dist") for r in rows if r.get("dist") is not None})
    return {"engine": sorted(eng), "eb": sorted(ebs), "dists": dists, "topo_under": rows[0].get("topo_under")}


def flatness(x, z, r=4.6, step=0.5):
    ys, tps = [], set()
    for dx in np.arange(-r, r + 1e-6, step):
        for dz in np.arange(-r, r + 1e-6, step):
            if dx * dx + dz * dz > r * r:
                continue
            q = query(x + dx, z + dz)
            if q is None:
                return None
            ys.append(q["y"])
            tps.add(q["topo"])
    return {"dy": round(max(ys) - min(ys), 3), "topos": sorted(tps)}


SWITCHABLE = {(16, 14), (9, 1), (14, 17), (20, 10), (14, 15), (0, 0), (8, 1), (18, 14), (13, 17), (17, 12), (21, 10),
              (22, 14), (19, 11), (13, 4), (9, 17), (19, 10), (14, 5), (14, 12), (14, 6), (13, 16), (3, 9), (7, 1),
              (20, 11), (16, 1), (14, 16), (13, 12)}       # forms/out/scene_worlddisc.json level7 (disc 1)


def airship_points():
    out = {}
    # SUMMIT: the given point, nudged off any lattice, and the 0.25u-grid max within 3u
    sx, sz = 1225.53, -926.47
    best = None
    for dx in np.arange(-3, 3.01, 0.25):
        for dz in np.arange(-3, 3.01, 0.25):
            q = query(sx + dx, sz + dz)
            if q and (best is None or q["y"] > best[2]["y"]):
                best = (sx + dx, sz + dz, q)
    q0 = query(sx, sz)
    q0i = query(sx, sz, ignore_exc=True, veto=False)
    out["summit"] = {"world": [sx, sz], "ground": q0["y"], "topo": q0["topo"], "ground_ignore_exc": q0i["y"],
                     "air_legal": q0["topo"] in AIR, "grid_max": {"world": [round(best[0], 2), round(best[1], 2)],
                                                                  "ground": best[2]["y"]},
                     "cell": q0["cell"], "switchable": tuple(q0["cell"]) in SWITCHABLE}
    # HIGH / LOW / L1 / L3 / SEA: scan stock non-switchable land around the massif
    hi = lo = l1 = l3 = None
    cand = []
    for bx in range(16, 22):
        for by in range(12, 17):
            if (bx, by) in SWITCHABLE or (1, bx, by) in live_cells():
                continue
            for lx in np.arange(4.37, 60, 3.0):
                for lz in np.arange(-4.61, -60, -3.0):
                    x, z = bx * 64 + lx, -by * 64 + lz
                    q = query(x, z)
                    if q:
                        cand.append((x, z, q))
    for x, z, q in cand:
        if hi is None and 28.0 <= q["y"] <= 40.5 and q["topo"] in AIR and math.hypot(x - sx, z - sz) < 220:
            qi = query(x, z, ignore_exc=True, veto=False)        # the flight cast (IgnoreExceptions) must agree
            f = flatness(x, z, r=1.0)
            if f and f["dy"] < 3.0 and qi and abs(qi["y"] - q["y"]) < 1e-3:
                hi = {"world": [round(x, 2), round(z, 2)], "ground": q["y"], "topo": q["topo"], "flat": f}
    for x, z, q in sorted(cand, key=lambda c: math.hypot(c[0] - sx, c[1] - sz)):
        if lo is None and 2.0 <= q["y"] <= 9.0 and q["topo"] in AIR and q["topo"] in WALK:
            f = flatness(x, z, r=2.0)
            if f and f["dy"] < 0.6:
                lo = {"world": [round(x, 2), round(z, 2)], "ground": q["y"], "topo": q["topo"], "flat": f}
        if l1 is None and q["topo"] in range(0, 14) and q["topo"] in WALK:
            f = flatness(x, z)
            if f and f["dy"] < 0.5 and all(t in WALK for t in f["topos"]):
                g = getoff_all_headings(x, z)
                if g["engine"] == ["accept"] and g["eb"] == ["land"] and g["dists"] == [2.5]:
                    l1 = {"world": [round(x, 2), round(z, 2)], "ground": q["y"], "topo": q["topo"], "flat": f, "sim": g}
        if l3 is None and q["topo"] in WALK and q["topo"] >= 14 and q["topo"] not in (23, 45, 46, 52):
            f = flatness(x, z)
            if f and f["dy"] < 0.5 and all(t in WALK for t in f["topos"]):
                g = getoff_all_headings(x, z)
                if g["engine"] == ["accept"] and g["eb"] == ["refuse"]:
                    l3 = {"world": [round(x, 2), round(z, 2)], "ground": q["y"], "topo": q["topo"], "flat": f, "sim": g}
        if hi and lo and l1 and l3:
            break
    out.update({"high": hi, "low": lo, "l1": l1, "l3": l3})
    # SEA: nearest open-ocean sample (topo 57) to the summit
    sea = None
    for r in range(1, 12):
        for k in range(0, 360, 15):
            x = sx + r * 64 * math.cos(math.radians(k)) + 0.37
            z = sz + r * 64 * math.sin(math.radians(k)) + 0.61
            q = query(x, z)
            if q and q["topo"] == 57 and q["part"] in ("Sea4", "Sea5", "Sea6"):
                g = getoff_all_headings(x, z)
                sea = {"world": [round(x, 2), round(z, 2)], "ground": q["y"], "topo": 57, "sim": g}
                break
        if sea:
            break
    out["sea"] = sea
    return out


def record_bytes(x, y, z, face, base):
    """gEventGlobal bytes for a vehicle record at `base` (74 boat/airship, 83 chocobo, 64 player): X int24, Y int16,
    Z int24, facing byte -- the layout every dispatcher's MoveInstantXZY/TurnInstant reads (entry 6 func 0)."""
    def le(v, n):
        v = int(round(v)) & ((1 << (8 * n)) - 1)
        return [(v >> (8 * k)) & 0xFF for k in range(n)]
    b = le(x * 256, 3) + le(y * 256, 2) + le(z * 256, 3) + [int(face) & 0xFF]
    return {str(base + k): v for k, v in enumerate(b)}


# --------------------------------------------------------------------------------------------- 3. chocobo
SHORE_T = (30, 31, 32, 33, 34, 35)
LB_WATER = (51, 53, 54, 55, 61)
CHOCO_STEP = 200 / 256.0                  # TransportControls rows 1/2 speed_move 200: XZSpeed = S(200) (ff9.cs:6165)


def _first_off_shore(x0, z0, ux, uz, smax):
    for s in np.arange(0, smax + 1e-6, 0.25):
        q = query(x0 + ux * s, z0 + uz * s)
        t = None if q is None else q["topo"]
        if t not in SHORE_T:
            return float(s), t
    return None, None


def straight_shore(x0, z0, bearing, waterline, half=4, tol=0.3):
    """The waterline seen from lateral offsets -half..+half (1u steps) must sit within `tol` of the centre line's and be
    light-blue-legal water: a straight shore square to the bearing, so a refused chocobo's slides cannot creep along it.
    Returns {offset: waterline} or None."""
    ux, uz = math.cos(math.radians(bearing)), math.sin(math.radians(bearing))
    seen = {}
    for L in range(-half, half + 1):
        if L == 0:
            continue
        w, t = _first_off_shore(x0 - uz * L, z0 + ux * L, ux, uz, waterline + 0.75)
        if w is None or abs(w - waterline) > tol or t not in LB_WATER:
            return None
        seen[str(L)] = w
    return seen


def choco_approach(x0, z0, bearing, mask, gake, ticks_per_burst, frac=0.35, dist=8.0, bursts=40):
    """Session.world_approach (6-frame bursts, 'blocked' when a burst's progress along the bearing is under
    WORLD_STALL_FRACTION of a free burst) over w_movementControl's ground branch (ff9.cs:5549-5603): each tick one step
    of S(speed_move) along the bearing, else the first legal slide -- ENGINE ORDER: rotation +k*11.25 first, which with
    x += rsin(RotTrue+180+rot), z += rcos(...) (ff9.cs:5688-5689) is bearing - k*11.25 -- then -k. Legal = the row's
    limit mask plus flg_gake's ground<->water refusal (ff9.cs:5703-5717). Probes are the non-sky window ray."""
    ux, uz = math.cos(math.radians(bearing)), math.sin(math.radians(bearing))
    x, z = x0, z0
    y = query(x, z)["y"]
    prog, lat, tops = 0.0, 0.0, set()
    for _b in range(bursts):
        px, pz = x, z
        for _t in range(ticks_per_burst):
            cur = query(x, z, origin_y=y + RAY_UP)
            cur_t = cur["topo"] if cur else -1
            moved = False
            for k in range(8):
                for sgn in ((0,) if k == 0 else (-1, 1)):
                    a = math.radians(bearing + sgn * k * 11.25)
                    tx, tz = x + math.cos(a) * CHOCO_STEP, z + math.sin(a) * CHOCO_STEP
                    q = query(tx, tz, origin_y=y + RAY_UP)
                    if q is None or q["topo"] not in mask:
                        continue
                    if gake and ((q["topo"] in GROUND_ST and cur_t in WATER_ST)
                                 or (cur_t in GROUND_ST and q["topo"] in WATER_ST)):
                        continue
                    x, z, y = tx, tz, q["y"]
                    tops.add(q["topo"])
                    moved = True
                    break
                if moved:
                    break
        step = (x - px) * ux + (z - pz) * uz
        prog += step
        lat = max(lat, abs(-(x - x0) * uz + (z - z0) * ux))
        if step < CHOCO_STEP * ticks_per_burst * frac:
            return {"outcome": "blocked", "progress": round(prog, 2), "topos": sorted(tops), "lateral_max": round(lat, 2)}
        if prog >= dist:
            return {"outcome": "reached", "progress": round(prog, 2), "topos": sorted(tops), "lateral_max": round(lat, 2)}
    return {"outcome": "max", "progress": round(prog, 2), "topos": sorted(tops), "lateral_max": round(lat, 2)}


def choco_edge_sim(x0, z0, bearing, waterline):
    """Register C2/C3 from the slide simulator over burst lengths 2/3/5/6 ticks (6 frames at 60 or 31 fps) and a +-3 deg
    facing error (world_face tolerance): the YELLOW must be blocked inside [waterline - 1.1, waterline + 0.3] on shore
    topographs only, the LIGHT BLUE must reach >= waterline + 2 through light-blue-only water."""
    rows, ok = [], True
    for db in (-3.0, 0.0, 3.0):
        for tpb in (2, 3, 5, 6):
            yl = choco_approach(x0, z0, bearing + db, WALK, 0, tpb)
            lb = choco_approach(x0, z0, bearing + db, LBLUE, 1, tpb)
            good = (yl["outcome"] == "blocked" and waterline - 1.1 <= yl["progress"] <= waterline + 0.3
                    and not set(yl["topos"]) & set(LB_WATER)
                    and lb["progress"] >= waterline + 2.0 and bool(set(lb["topos"]) & set(LB_WATER)))
            ok = ok and good
            rows.append({"bearing_err": db, "ticks_per_burst": tpb, "yellow": yl, "lightblue": lb, "ok": good})
    ys = [r["yellow"]["progress"] for r in rows]
    return {"ok": ok, "yellow_progress": [min(ys), max(ys)], "rows": rows}


def chocobo_points():
    vp = json.loads((OUT / "vertical_prep.json").read_text(encoding="utf-8"))["canopy"]
    out = {}
    for k in ("forest", "lawn"):
        x, z = vp[k]["world"]
        q = query(x, z)
        out[k] = {"world": [x, z], "ground": q["y"], "topo": q["topo"], "sink_pred": -1.171875 if q["topo"] in (36, 37, 38) else 0.0}
    # SHORE -> SHALLOW edge: walk +/- axis lines from shore (30-35) into light-blue-legal water (51/53/54/55/61)
    best = None
    for bx, by in [(7, 17), (6, 17), (8, 17), (5, 16), (9, 16), (2, 6), (3, 6), (15, 16), (16, 16), (18, 15)]:
        if (1, bx, by) in live_cells() or (bx, by) in SWITCHABLE:
            continue
        for lx in np.arange(2.37, 62, 1.0):
            for lz in np.arange(-2.61, -62, -1.0):
                x0, z0 = bx * 64 + lx, -by * 64 + lz
                q0 = query(x0, z0)
                if not q0 or q0["topo"] not in (30, 31, 32, 33, 34, 35):
                    continue
                for bearing in (0, 90, 180, 270):
                    ux, uz = math.cos(math.radians(bearing)), math.sin(math.radians(bearing))
                    prof = []
                    for s in np.arange(0, 14.01, 0.25):
                        q = query(x0 + ux * s, z0 + uz * s)
                        prof.append((round(float(s), 2), None if q is None else q["topo"], None if q is None else q["y"]))
                    # shore run, then water: first non-shore sample must be light-blue-legal water, then >= 5u of it
                    k = next((i for i, p in enumerate(prof) if p[1] not in (30, 31, 32, 33, 34, 35)), None)
                    if k is None or k < 12:                     # want >= 3u of shore before the water
                        continue
                    wt = prof[k][1]
                    if wt not in (51, 53, 54, 55, 61):
                        continue
                    run = 0
                    for p in prof[k:]:
                        if p[1] in (51, 53, 54, 55, 61):
                            run += 1
                        else:
                            break
                    if run < 22:                               # >= 5.5u of light-blue-legal water
                        continue
                    ys = [p[2] for p in prof[:k + run] if p[2] is not None]
                    steps = max(abs(ys[i + 1] - ys[i]) for i in range(len(ys) - 1))
                    if steps > 0.5:
                        continue
                    cand = {"start": [round(x0, 2), round(z0, 2)], "bearing": bearing, "waterline": prof[k][0],
                            "water_topo": wt, "water_run": round(run * 0.25, 2), "max_sample_step": round(steps, 3),
                            "cell": [bx, by], "profile": prof[:k + run + 1]}
                    if best is not None and cand["waterline"] >= best["waterline"]:
                        continue
                    # [review] THE SHORE MUST BE STRAIGHT AND SQUARE TO THE BEARING. A blocked chocobo does not stop
                    # at an oblique waterline: w_movementControl tries 7 slide angles each side (ff9.cs:5549-5603)
                    # and the first legal one keeps it creeping ALONG the sand. The first pick here, (485.37,
                    # -1121.61) bearing 270, sits on a ~28 deg shoreline: the slide simulator below walks the YELLOW
                    # chocobo to progress 7.2-7.5 (never touching water) before world_approach calls it blocked --
                    # outside [1.9, 3.3], and past C3's 5.0 bar, so C2 failed and C3 could not tell the two apart.
                    straight = straight_shore(x0, z0, bearing, prof[k][0])
                    if straight is None:
                        continue
                    sim = choco_edge_sim(x0, z0, bearing, prof[k][0])
                    if not sim["ok"]:
                        continue
                    cand["straight"] = straight
                    cand["sim"] = sim
                    best = cand
        if best:
            break
    out["edge"] = best
    # the landing lawn's clear run along the edge bearing (the speed probes and world_face probes walk it)
    lx, lz = 68.0, -444.0
    clear = {}
    for brg in (0, 90, 180, 270, best["bearing"] if best else 270):
        ux, uz = math.cos(math.radians(brg)), math.sin(math.radians(brg))
        prev = query(lx, lz)["y"]
        d = 0.0
        for s_ in np.arange(0.25, 40.01, 0.25):
            q = query(lx + ux * s_, lz + uz * s_)
            if q is None or q["topo"] not in WALK or abs(q["y"] - prev) > 2.34375:
                break
            prev, d = q["y"], float(s_)
        clear[str(brg)] = d
    out["landing_clear_u"] = clear
    return out


# --------------------------------------------------------------------------------------------- 4. no-fly cell
def isolated_sea_cells(exclude=()):
    E = A._engine()
    res = []
    for by in range(0, 20):
        for bx in range(0, 24):
            if (bx, by) in exclude:
                continue
            ok = True
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    cx, cy = bx + dx, by + dy
                    if not (0 <= cx < 24 and 0 <= cy < 20):
                        ok = False
                        continue
                    if not E.is_sea(1, cx, cy) or (1, cx, cy) in live_cells() or (4, cx, cy) in live_cells():
                        ok = False
            if ok:
                res.append((bx, by))
    return res


# --------------------------------------------------------------------------------------------- 5. boat
class Cache:
    """ff9.s_moveCHRCache semantics (WMBlock.cs:145-183): 10 slots of (block, mesh, tri), tested first."""

    def __init__(self):
        self.slots = []

    def test(self, cell, meshes, lx, lz, origin_y):
        for (c, mi, t) in reversed(self.slots):
            if c != cell:
                continue
            name, V, ids = meshes[mi]
            sel = np.zeros(len(ids), bool)
            sel[t] = True
            h = _hit_in_mesh(V, ids, lx, lz, origin_y, True, False, tri_filter=sel)   # no filters on a cached tri
            if h is not None:
                if h[2] == VETO:
                    continue
                return {"y": h[1], "id": h[2], "topo": topo(h[2]), "mesh": mi, "tri": t, "cached": True}
        return None

    def push(self, cell, mi, t):
        self.slots.append((cell, mi, t))
        self.slots = self.slots[-10:]


def boat_query(x, z, origin_y, cache, extra):
    bx, by = int(math.floor(x / 64.0)), int(math.floor(-z / 64.0))
    parts = {k: v for k, v in (extra or {}).items() if k != "_cell"}
    cm = cell_meshes(bx, by, 1, parts if parts and (bx, by) == tuple(extra.get("_cell", ())) else None)
    lx, lz = x - bx * 64.0, z + by * 64.0
    h = cache.test((bx, by), cm["meshes"], lx, lz, origin_y)
    if h:
        return h
    for mi, (name, V, ids) in enumerate(cm["meshes"]):
        r = _hit_in_mesh(V, ids, lx, lz, origin_y, False, True)
        if r is None or r[0] == "VETO":
            continue
        cache.push((bx, by), mi, r[0])
        return {"y": r[1], "id": r[2], "topo": topo(r[2]), "mesh": mi, "tri": r[0], "part": name, "cached": False}
    return None


def boat_drive(x0, z0, heading_deg, ticks, extra=None):
    """Simulate w_movementControl (ff9.cs:5543-5603) for the Blue Narciss driving forward at full throttle along
    world bearing `heading_deg` (atan2(dz, dx)); returns the per-tick trace and where progress stalled."""
    ex = dict(extra or {})
    cache = Cache()
    q = boat_query(x0, z0, None, cache, ex) if ex else query(x0, z0)
    y = (q["y"] if q else 0.0) + SLICE_BOAT
    x, z = x0, z0
    alpha = 0.0
    trace = []
    stall = 0
    for t in range(ticks):
        alpha += (30.0 - alpha) / 8.0
        speed = alpha / 32.0
        moved = False
        for k in range(8):
            # [review] ENGINE ORDER: w_movementControl tries rotation +k*11.25 first (ff9.cs:5557-5561), and the probe
            # is x += rsin(RotTrue+180+rot), z += rcos(...) (ff9.cs:5688-5689), so +rot is bearing - k*11.25 (toward
            # -z when heading +x). This loop used to try bearing + k*11.25 first -- the mirror image.
            for sgn in ((1,) if k == 0 else (-1, 1)):
                ang = math.radians(heading_deg + sgn * k * 11.25)
                tx, tz = x + math.cos(ang) * speed, z + math.sin(ang) * speed
                h = boat_query(tx, tz, y + RAY_UP, cache, ex)
                if h is None or h["topo"] not in BOAT:
                    continue
                # step length = speed^2 / |first probe| (2D on water: sink classes 53-57 are non-zero, ff9.cs:5571-5578)
                x, z, y = tx, tz, h["y"] + SLICE_BOAT
                moved = True
                trace.append({"t": t, "x": round(x, 3), "z": round(z, 3), "y": round(y, 3), "topo": h["topo"],
                              "slide": sgn * k, "cached": h.get("cached")})
                break
            if moved:
                break
        if not moved:
            stall += 1
            if stall >= 3:
                break
        else:
            stall = 0
    return trace


def build_phase_meshes():
    """The lab Terrain overrides world-reclaim would write for (21,1), built with the SAME kit builders and the CLI
    defaults (seg 10), written to the scratchpad for the simulation only (veh_build.py documents the deploy)."""
    from ff9mapkit.world import mesh as M
    SCRATCH.mkdir(parents=True, exist_ok=True)
    bx, by = BOAT_CELL
    water = [(-1, 0), (1, 0), (0, 1), (0, -1)]
    phases = {
        "flat6": M.flat_block_mesh(disc=1, x=bx, y=by, seg=10, topograph=0, height=6.0),
        "flat1.2": M.flat_block_mesh(disc=1, x=bx, y=by, seg=10, topograph=0, height=1.2),
        "island": M.island_block_mesh(disc=1, x=bx, y=by, water_dirs=water, seg=10, height=6.0, beach=22.0,
                                      grass_topo=0, shore_topo=20, shore_frac=0.3),
        "cliff": M.cliff_block_mesh(disc=1, x=bx, y=by, cliff_dirs=water, seg=10, land_height=3.2, rim_run=1.0,
                                    land_topo=0),
    }
    paths = {}
    for k, bm in phases.items():
        p = SCRATCH / f"phase_{k}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        M.write_ff9mesh(bm, p)
        paths[k] = str(p)
    return paths


BOAT_CELL = (21, 1)


def _lane(trace, x_border):
    xs = [r["x"] for r in trace]
    ins = [r for r in trace if r["x"] > x_border]
    return {"ticks": len(trace), "max_x": round(max(xs), 2) if xs else None,
            "into_cell": round(max(xs) - x_border, 2) if xs else None,
            "stalled": len(trace) > 0 and trace[-1]["t"] < 150,
            "y_in_cell": [min(r["y"] for r in ins), max(r["y"] for r in ins)] if ins else [],
            "topos_in_cell": sorted({r["topo"] for r in ins}), "slides": sum(1 for r in trace if r["slide"]),
            "last": trace[-1] if trace else None}


from veh_lib import first_deflection        # noqa: E402 -- ONE definition: the session judges with the same function


RIM_HEADINGS = (-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0)


def heading_scan(x0, z0, x_border, extra, ticks=110):
    """[review] The lane predictions are taken at heading 0 exactly, but the session accepts a hull within +-2 deg
    (veh_lib.hull_steer tol, veh_session4 B1). Re-drive each lane over that band and record what the in-game judge can
    rely on. For flat6 RIM this is decisive: the hidden islet rim is a ~4u-wide wall the boat meets at into ~19.5, and
    whether it STALLS there (residual distance under the 78.75-deg slide's 0.18u reach) or SLIDES round the islet and
    passes is a step-phase knife edge -- heading 0 stalls, -0.5 and +0.5 pass. Both are contact with the rim."""
    rows = []
    for h in RIM_HEADINGS:
        tr = boat_drive(x0, z0, h, ticks, extra=extra)
        ln = _lane(tr, x_border)
        stalled = bool(tr) and tr[-1]["t"] < ticks - 10
        d = first_deflection(tr, x0, z0, h, x_border)
        rows.append({"heading": h, "stalled": stalled, "into_cell": ln["into_cell"], "slides": ln["slides"],
                     "deflection": d, "contact_into": ln["into_cell"] if stalled else (None if d is None else d["into"])})
    contact = [r["contact_into"] for r in rows if r["contact_into"] is not None]
    return {"rows": rows, "all_stalled": all(r["stalled"] for r in rows),
            "any_stalled": any(r["stalled"] for r in rows),
            "all_contact": len(contact) == len(rows),
            "contact_into": [min(contact), max(contact)] if contact else None,
            "max_slides": max(r["slides"] for r in rows),
            "any_deflection": any(r["deflection"] for r in rows)}


def boat_plan():
    """Two lanes through the reclaimed cell, both starting at rest 19.63u west of its border on open stock sea, hull
    bearing 0 (+x): OPEN (the longest slide-free free-ride run -- crosses the cell under a flat-6 slab) and RIM (stops
    MID-CELL, under the slab, on Block[12][10]'s hidden topo-56 islet rim)."""
    bx, by = BOAT_CELL
    xb = bx * 64.0
    out = {"cell": [bx, by], "neighbours_all_stock_sea": BOAT_CELL in isolated_sea_cells()}
    paths = build_phase_meshes()
    x0 = round(xb - 19.63, 2)
    lanes = {}
    for lz in np.arange(-3.39, -61, -1.0):
        z = round(-by * 64 + lz, 2)
        tr = boat_drive(x0, z, 0.0, 160, extra={"Terrain": paths["flat6"], "_cell": (bx, by)})
        ln = _lane(tr, xb)
        if ln["slides"] == 0 and (lanes.get("open") is None or ln["into_cell"] > lanes["open"]["into_cell"]):
            lanes["open"] = dict(ln, z=z)
        if ln["slides"] == 0 and ln["stalled"] and 8.0 <= (ln["into_cell"] or 0) <= 40.0:
            if lanes.get("rim") is None or abs(lz + 25.39) < abs(lanes["rim"]["z"] + by * 64 + 25.39):
                lanes["rim"] = dict(ln, z=z)
    out["lanes"] = {k: {"start": [x0, v["z"]]} for k, v in lanes.items()}
    out["spawn"] = {"world": [x0, lanes["open"]["z"]], "face_byte": 192, "y": 0.0,
                    "record": record_bytes(x0, 0.0, lanes["open"]["z"], 192, 74)}
    phases = {}
    for k, p in paths.items():
        phases[k] = {"mesh": p}
        for ln, v in lanes.items():
            tr = boat_drive(x0, v["z"], 0.0, 160, extra={"Terrain": p, "_cell": (bx, by)})
            phases[k][ln] = _lane(tr, xb)
    out["phases"] = phases
    # [review] the +-2 deg hull band the session accepts: flat6 (H1) and the no-deploy baseline, both lanes
    out["heading_scan"] = {ln: {"flat6": heading_scan(x0, v["z"], xb, {"Terrain": paths["flat6"], "_cell": (bx, by)}),
                                "none": heading_scan(x0, v["z"], xb, None)}
                           for ln, v in lanes.items()}
    # STOCK-coast control (no deploy): a stock land cell whose WEST neighbour is stock open sea; at rest 14.37u out,
    # +x; the boat must STALL within 3-20u with at most one slide (the instrument's "blocked" calibration)
    E = A._engine()
    ctrl = None
    for (cx, cy) in sorted({(x, y) for y in range(20) for x in range(1, 24)},
                           key=lambda c: abs(c[0] - bx) + abs(c[1] - by)):
        if E.is_sea(1, cx, cy) or not E.is_sea(1, cx - 1, cy):
            continue
        if (1, cx, cy) in live_cells() or (1, cx - 1, cy) in live_cells() or (cx, cy) in SWITCHABLE:
            continue
        for lz in np.arange(-6.39, -60, -2.0):
            z = round(-cy * 64 + lz, 2)
            sx0 = round(cx * 64 - 14.37, 2)
            q = query(sx0, z)
            if not q or q["topo"] != 57:
                continue
            tr = boat_drive(sx0, z, 0.0, 120)
            if not tr or tr[-1]["t"] >= 119:
                continue
            ln = _lane(tr, cx * 64.0)
            prog = ln["max_x"] - sx0
            if not (3.0 <= prog <= 20.0) or ln["slides"] > 1:
                continue
            nxt = query(ln["max_x"] + 0.6, tr[-1]["z"], origin_y=tr[-1]["y"] + RAY_UP)
            ctrl = {"cell": [cx, cy], "start": [sx0, z], "stop_x": ln["max_x"], "progress": round(prog, 2),
                    "blocking_ahead": None if nxt is None else {k2: nxt[k2] for k2 in ("part", "topo", "y")},
                    "slides": ln["slides"], "y_at_stop": tr[-1]["y"]}
            break
        if ctrl:
            break
    if ctrl:                                              # [review] the same +-2 deg band for the instrument
        prog = []
        for h in RIM_HEADINGS:
            tr = boat_drive(ctrl["start"][0], ctrl["start"][1], h, 120)
            prog.append(round(max(r["x"] for r in tr) - ctrl["start"][0], 2) if tr and tr[-1]["t"] < 110 else None)
        ctrl["heading_scan"] = {"headings": list(RIM_HEADINGS), "progress": prog}
    out["stock_control"] = ctrl
    return out


# --------------------------------------------------------------------------------------------- main
def main():
    OUT.mkdir(exist_ok=True)
    res = {"route": route_evidence()}
    air = airship_points()
    lo = air["low"]
    air["spawn"] = {"world": lo["world"], "y": lo["ground"], "face_byte": 192,
                    "record": record_bytes(lo["world"][0], lo["ground"], lo["world"][1], 192, 74)}
    res["air"] = air
    res["choco"] = chocobo_points()
    nof = [c for c in isolated_sea_cells(exclude={BOAT_CELL}) if c[1] >= 1]
    res["nofly_candidates"] = nof[:12]
    res["boat"] = boat_plan()
    res["masks"] = {"walk_blocked": sorted(set(range(64)) - WALK), "air_blocked": sorted(set(range(64)) - AIR),
                    "lightblue_extra": sorted(LBLUE - WALK), "boat_legal": sorted(BOAT),
                    "ground_status": sorted(GROUND_ST), "water_status": sorted(WATER_ST)}
    (OUT / "veh_prep.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    r = res["route"]
    print("6603:", r["field6603"]["region_key"], r["field6603"]["cascade_key35"], r["field6603"]["worldmap_override_var"])
    for k, v in r["dispatchers"].items():
        print(k, {kk: v[kk] for kk in ("vehicle_initobject_sc_gate", "vehicle_mode_arm", "vehicle_binds_control_at_load",
                                        "vehicle_record", "chocobo_arm_1_6_binds", "chocobo_record_x")})
    for k in ("summit", "high", "low", "l1", "l3", "sea"):
        v = air.get(k)
        print(k, None if v is None else {kk: v.get(kk) for kk in ("world", "ground", "topo")},
              None if not v or "sim" not in v else v["sim"])
    print("choco:", {k: res["choco"][k] for k in ("forest", "lawn")})
    e = res["choco"]["edge"]
    print("edge:", None if e is None else {k: e[k] for k in ("start", "bearing", "waterline", "water_topo", "water_run", "cell")},
          None if e is None else {"yellow_progress": e["sim"]["yellow_progress"], "ok": e["sim"]["ok"]})
    print("nofly candidates:", res["nofly_candidates"][:6])
    b = res["boat"]
    print("boat lanes:", b["lanes"], "spawn", b["spawn"]["world"])
    for k, v in b["phases"].items():
        for ln in ("open", "rim"):
            if ln in v:
                print("  phase", k, ln, {kk: v[ln][kk] for kk in ("into_cell", "stalled", "y_in_cell", "topos_in_cell", "slides", "ticks")})
    print("  stock control:", b["stock_control"])
    for ln, v in b.get("heading_scan", {}).items():
        for ph, s in v.items():
            print("  heading scan", ln, ph, {kk: s[kk] for kk in ("all_stalled", "any_stalled", "all_contact",
                                                               "contact_into", "max_slides", "any_deflection")})


if __name__ == "__main__":
    main()
