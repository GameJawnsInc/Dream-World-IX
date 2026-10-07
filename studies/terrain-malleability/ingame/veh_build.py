"""BUILD the scratch-folder deployables for the vehicle sessions, and register the exact predictions they carry.

veh_session3 (README rank 12, the NO-FLY topograph, vertical V12):
  Disc1 `Block[1][13] Terrain.ff9mesh` for the isolated open-ocean cell (1,13) (IsSea, all 8 neighbours stock sea, no
  live override on disc 1 or 4 -- veh_prep.isolated_sea_cells). Its existence arms the s34 sea divert onto
  Block[12][10] (consumption C6), whose Sea parts free-ride UNDER it; the sky cast meets this Terrain first because
  Terrain registers before Sea1-6 (WMWorld.cs:582-810).
  A flat slab at y 2.0 of 1u quads (8192 tris, fresh verts per tri -- the unindexed contract), topograph per triangle
  by its centroid's distance r from two ring centres:
      ring A  centre local (14.37, -14.61)  8 <= r <= 12  -> topograph 15 (flight-blocked AND foot-blocked: V12's
              14 unused topographs; TransportControls rows 8/9 limit1 0xD8FF3CFF has bit 15 clear)
      ring B  centre local (49.63, -49.39)  8 <= r <= 12  -> topograph 41 (desert: legal for the airship and on foot)
      elsewhere                                            -> topograph 0
  UVs: per-tri palette by own topograph (grass / desert); ring A has no stock donor (topo 15 is unused), so it is
  stamped with the rock (49) look -- render only, UV is read by nothing but the renderer (uvclass UV-01).

veh_session4 (README rank 7, H1): NOT built here -- the deploy IS the kit verb (veh_PLAN.md section 5 lists the exact
commands). veh_prep.build_phase_meshes() builds the identical walk geometry with the same builders and CLI defaults
for the simulation.

Outputs: ingame/out/veh_deploy/nofly/<the mod-folder tree>, ingame/out/veh_build.json (ring geometry + the flight
simulation's registered stop windows). Nothing is written into the game install.

Rerun:  py studies/terrain-malleability/ingame/veh_build.py
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
sys.path.insert(0, str(HERE))
import veh_prep as P                                  # noqa: E402

BX, BY = 1, 13
SLAB_Y = 2.0
RING_IN, RING_OUT = 8.0, 12.0
CENTRES = {"A": ((14.37, -14.61), 15), "B": ((49.63, -49.39), 41)}
OUT_TREE = HERE / "out" / "veh_deploy" / "nofly"
HG3_TARGET = (500 * 128 / 4) / 256.0                  # ff9.cs:6313: S(speed_move * rightStick / p1), rightStick 128


def ring_mesh():
    from ff9mapkit.world.extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN
    pos, nrm, uv, tan, flat, tris = [], [], [], [], [], []
    vi = 0
    for i in range(64):
        for j in range(64):
            x0, x1, z0, z1 = float(i), float(i + 1), -float(j), -float(j + 1)
            c00, c10, c11, c01 = (x0, z0), (x1, z0), (x1, z1), (x0, z1)
            for (a, b, c) in ((c00, c11, c01), (c00, c10, c11)):          # both +Y geometric normal (mesh.flat_block_mesh)
                cx = (a[0] + b[0] + c[0]) / 3.0
                cz = (a[1] + b[1] + c[1]) / 3.0
                t = 0
                for (rx, rz), tp in CENTRES.values():
                    if RING_IN <= math.hypot(cx - rx, cz - rz) <= RING_OUT:
                        t = tp
                idall = float(encode_id(event=0, area=0, topograph=t))
                base = vi
                for (px, pz) in (a, b, c):
                    pos.append([px, SLAB_Y, pz]); nrm.append([0.0, 1.0, 0.0]); uv.append([0.0, 0.0])
                    tan.append([idall, 0.0, 0.0, 1.0]); flat.append(vi); vi += 1
                tris.append([base, base + 1, base + 2])
    chan = {CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan}
    channels = {CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)}
    return BlockMesh(name=f"Block[{BX}][{BY}] Terrain", disc=1, x=BX, y=BY, lod="0_1", vcount=vi, stride=48,
                     channels=channels, chan_arrays=chan, flat_index=flat, tris=tris,
                     raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def fly(cx, cz, bearing, mesh_path, ticks=60):
    """ff9.w_movementControl's flying branch (ff9.cs:5605-5633) at full throttle from rest: one round check per tick
    at the full step (no slide), sky cast with IgnoreExceptions, mask = rows 8/9. Returns (stop distance, stalled)."""
    ex = {"Terrain": mesh_path}
    x, z, alpha = cx, cz, 0.0
    for t in range(ticks):
        alpha += (HG3_TARGET - alpha) / 8.0
        sp = alpha / 32.0
        nx, nz = x + math.cos(math.radians(bearing)) * sp, z + math.sin(math.radians(bearing)) * sp
        q = P.query(nx, nz, ignore_exc=True, veto=False, extra=ex)
        if q is None or q["topo"] not in P.AIR:
            return round(math.hypot(x - cx, z - cz), 3), True, t
        x, z = nx, nz
    return round(math.hypot(x - cx, z - cz), 3), False, ticks


def main():
    from ff9mapkit.world import mesh as M
    from ff9mapkit.world import palette as PAL
    bm = ring_mesh()
    M.validate_blockmesh(bm)
    bm = PAL.apply_palette_uvs(bm, topograph=None, disc=1, part="terrain")      # grass (0), desert (41)
    bm = PAL.apply_palette_uvs(bm, topograph=49, disc=1, part="terrain")        # ring A (15: no donor) -> rock look
    rel = M.override_relpath(1, BX, BY, part="Terrain")
    path = M.write_ff9mesh(bm, OUT_TREE / rel)
    counts = {}
    for t in bm.tangents[::3]:
        k = (int(round(t[0])) & 0xFC) >> 2
        counts[k] = counts.get(k, 0) + 1
    res = {"cell": [BX, BY], "slab_y": SLAB_Y, "ring_in": RING_IN, "ring_out": RING_OUT, "tris": len(bm.tris),
           "verts": bm.vcount, "topo_tris": counts, "mesh": str(path), "relpath": rel,
           "isolated": (BX, BY) in P.isolated_sea_cells(), "centres": {}}
    for k, ((lx, lz), tp) in CENTRES.items():
        wx, wz = BX * 64 + lx, -BY * 64 + lz
        stops = [fly(wx, wz, b, str(path)) for b in range(0, 360, 10)]
        d = [s[0] for s in stops]
        res["centres"][k] = {"local": [lx, lz], "world": [round(wx, 2), round(wz, 2)], "topo": tp,
                             "ground_centre": P.query(wx, wz, extra={"Terrain": str(path)})["y"],
                             "sim_stalled_all": all(s[1] for s in stops), "sim_stalled_any": any(s[1] for s in stops),
                             "sim_stop_min": min(d), "sim_stop_max": max(d),
                             "sim_ticks_to_stop": [min(s[2] for s in stops), max(s[2] for s in stops)]}
    res["spawn_record"] = P.record_bytes(res["centres"]["A"]["world"][0], SLAB_Y, res["centres"]["A"]["world"][1], 192, 74)
    (HERE / "out" / "veh_build.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("spawn_record",)}, indent=1, default=str))


if __name__ == "__main__":
    main()
