"""THE DESCENT STALL -- an offline simulator of the overworld ON-FOOT step loop over the real (7,17) walk meshes.

Question (ingame/RESULTS.md section 6): at a +3 Terrain-only reshape of (7,17) (world-terrain --at 480 -1120 --radius 16
--raise 3), the descent from the terrain to the beach crossed at x=476.28 but "stalled" at x=479.64 / 480.18 in steps
of ~0.06u at z ~ -1119.80. What does the engine do there, tick by tick?

ANSWER (calibrate reproduces every ring position of session 5, both legs, +3 and +1): THE ENGINE NEVER STALLED. The
full-speed probe crossed the tear, so the step collapsed to s^2/sqrt(s^2+dy^2) = 0.062u (the CREEP); the walk had
crept 3 of its 6 creep ticks when world_approach's one-burst stall test (progress < 0.35 x commanded) ended it.
Held on, the actor drops onto the beach at tick 13. Line 476.28 "passed" only because its last full step ended
0.029u from the edge (< one creep step): a PHASE accident, not a smaller drop. See stall_PLAN.md for the law.

The simulator is a line-for-line port of the stock Memoria code path (float32 throughout, like the engine):
  * w_movementUpdate sets last = pos before control                                ff9.cs:5159-5162
  * w_movementControl: sweep theta = 0, 11.25 .. 78.75 deg (+theta, then -theta only if +theta's FIRST probe fails);
    probe 1 at full speed; num8 = |probe1 - last| in 3D (planar only when the slice height is nonzero);
    num9 = speed^2 / num8; probe 2 at num9 along the same rotation; move to probe 2 if it passes   ff9.cs:5533-5603
  * w_movementRoundCheck: probe = pos + (rsin, rcos)(RotTrue + 180 + rot) * speed, y = the ACTOR's y; w_cellHit with
    the per-actor cache unless the actor stands on topo 49/52; pass iff pno >= 0 and the topograph is in the control
    row's limit mask (on foot: flg_gake = 0, no water/ground gate)                                  ff9.cs:5682-5718
  * w_cellHit -> w_nwpHit: ray from (x, y + 2.34375, z) straight down (sky: y + 400); WMBlock.Raycast IGNORES the
    distance argument                                                    ff9.cs:3304-3314, :7296-7324, :1327-1329
  * WMBlock.Raycast: the 10-slot triangle cache first (slot Number, then Number+1 .. +9 mod 10; NO up-facing or
    skip-id filter, accepts intersect != 0); else a full scan, mesh by mesh in registration order, FIRST passing
    tri in buffer order (skip ids 4078/4088/2040, geometric ny > 0.1); a 0x31EE first hit abandons the mesh; a
    full-scan hit is pushed into the cache                                                  WMBlock.cs:137-235
  * WMPhysics.intersect3D_RayTriangle, emulated in float32 (r < 0 -> 0: a tri ABOVE the ray origin is invisible)
                                                                                            WMPhysics.cs:6-120
  * the teleport (Ff9mkDebugMenu.cs:1837-1852): x/z truncated to 1/256, then w_movementChrInitSlice sky-casts with
    NO cache (ff9.cs:4596-4618); the published player.y is (Int32)(y*256) (WMActor.cs:37-47)

Meshes: the (7,17) walk list in registration order (consumption bind oracle via arealib: Terrain, Beach1, Sea1-5);
Terrain is REGENERATED offline with the kit's own reshape step (extract.read_block + mesh.deform_radial +
mesh.ff9mesh_bytes, the exact bytes `world-terrain` deploys) into the session scratchpad -- never a mod folder.
No game bytes are written into the repo: out/*.json carries derived numbers only.

Usage (from anywhere; ~1-4 min each, numpy only):
  py stall_sim.py calibrate          # C0-C6: regenerate, then replay sessions 5 (+3) and 5 (+1) against their rings
  py stall_sim.py map                # the seam map, the phase map, the drop sweep, the slit corollary
  py stall_sim.py predict            # stall_session.py's line starts + registered numbers -> out/stall_predict.json
  py stall_sim.py replay <run dir>   # score a stall_session run: re-simulate each line at the MEASURED heading
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np                                   # noqa: E402

HERE = Path(__file__).resolve().parent
TM = HERE.parent
REPO = TM.parent.parent
OUT = HERE / "out"
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(TM / "gap_area_layer"))
SCR = Path(os.environ.get("STALL_SCRATCH", r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                                           r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\stall"))
RUNS = REPO / ".harness-runs"
RUN_R3 = RUNS / "20261007-133805-terrain-session5-raise3"
RUN_R1 = RUNS / "20261007-134218-terrain-session5-raise1"

f32 = np.float32
CELL = (7, 17)
ORIGIN = (f32(448.0), f32(-1088.0))                  # extract.block_world_origin(7, 17)
RESHAPE_AT = (480.0, -1120.0)
RESHAPE_RADIUS = 16.0
SEAM_Z = -1120.0                                      # the Terrain|Beach1 weld, x 476..484 (verts at 476/480/484)

# --- engine constants (stock Memoria) -----------------------------------------------------------------------
RAY_START = f32(2.34375)                              # ff9.cs:1328 rayStartOffsetY
RAY_START_SKY = f32(400.0)                            # ff9.cs:1327 rayStartOffsetYFromSky
SPEED = f32(0.4375)                                   # S(112 * 4096 >> 12): ff9.cs:1473 + :6165 (TransportControls row 0)
SWEEP = [f32(k * 11.25) for k in range(8)]            # num3 < PsxRot(1024), += PsxRot(128): ff9.cs:5552
LIMIT_ON_FOOT = (0x0010667F, 0xD8FF3CFF)              # ff9.cs:1487-1491 == TransportControls.csv row 0
SKIP_IDS = (4078, 4088, 2040)                         # WMPhysics.cs:16-20
VETO = 0x31EE                                         # WMBlock.cs:210 / :233
VEC_EPS = f32(9.99999944e-11)                         # UnityEngine.Vector3 == (SqrMagnitude(a-b) < 9.99999944E-11f)
SINK_ROW_ON_FOOT = (400, 150, 250, 200, 450, 450, 300, 300, 0)   # w_movementSinkArray row 1 (ff9.cs:19-43; V3)
HARNESS_STALL_FRACTION = 0.35                         # tools/harness/session.py:2614
SWEEP_MIN_COS = math.cos(math.radians(78.75))         # the widest sweep probe's forward reach / s


def topo(idall: int) -> int:
    return (int(idall) & 0xFC) >> 2                   # ff9.cs:2345-2348


def limit_ok(idall: int, limit=LIMIT_ON_FOOT) -> bool:
    n = topo(idall)                                   # ff9.cs:5924-5940
    return bool((limit[0] >> (n - 32)) & 1) if n > 31 else bool((limit[1] >> n) & 1)


def slice_height(idall: int) -> float:
    """w_movementGetSliceHeight for the on-foot party (ff9.cs:5636-5680): nonzero only on the sink topographs."""
    n = topo(idall)
    col = {36: 0, 37: 0, 38: 0, 53: 1, 54: 2, 55: 3, 56: 4, 57: 5, 51: 6, 48: 7}.get(n, 8)
    v = SINK_ROW_ON_FOOT[col]
    if v:
        v -= 100
    return float(f32(-v) * f32(0.00390625))


def creep_step(dy: float, s: float = float(SPEED)) -> float:
    """THE CREEP LAW: the collapsed step when the full-speed probe lands dy away vertically (ff9.cs:5568-5590)."""
    return s * s / math.sqrt(s * s + dy * dy)


# --- meshes ---------------------------------------------------------------------------------------------------
def regen_terrain(amount: float) -> Path:
    """The exact Terrain bytes `world-terrain --at 480 -1120 --radius 16 --raise <amount>` deploys for (7,17)
    (terrain.reshape -> deform_radial -> deploy_override -> ff9mesh_bytes), written to the SCRATCHPAD."""
    from ff9mapkit.world import extract as X, mesh as M
    SCR.mkdir(parents=True, exist_ok=True)
    p = SCR / f"Block[7][17] Terrain.raise{amount:g}.ff9mesh"
    if p.is_file():
        return p
    bm = X.read_block(*CELL, disc=1, part="terrain")
    if amount:
        moved = M.deform_radial(bm, amount=amount, radius=RESHAPE_RADIUS, center=RESHAPE_AT, falloff="smooth",
                                world_origin=X.block_world_origin(*CELL))
        assert moved > 0
    p.write_bytes(M.ff9mesh_bytes(bm))
    return p


def _dot(a, b):
    return ((a[..., 0] * b[..., 0]) + (a[..., 1] * b[..., 1])) + (a[..., 2] * b[..., 2])


def _cross(a, b):
    return np.stack([a[..., 1] * b[..., 2] - a[..., 2] * b[..., 1],
                     a[..., 2] * b[..., 0] - a[..., 0] * b[..., 2],
                     a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]], axis=-1).astype(f32)


class Mesh:
    """One walk mesh in the engine's frame: float32 world-space tris, ids, and the AddWalkMesh normal y."""

    def __init__(self, name: str, V_local, ids):
        L = np.asarray(V_local, dtype=f32)                                     # [T,3,3] local
        self.name = name
        self.ids = np.asarray(ids, dtype=np.int64)
        W = L.copy()
        W[:, :, 0] = L[:, :, 0] + ORIGIN[0]                                    # TransformPoint: + block position
        W[:, :, 2] = L[:, :, 2] + ORIGIN[1]
        self.W = W
        self.P0, self.P1, self.P2 = W[:, 0], W[:, 1], W[:, 2]
        n = _cross(L[:, 1] - L[:, 0], L[:, 2] - L[:, 0])                       # WMBlock.cs:66-71 (LOCAL verts)
        mag = np.sqrt(_dot(n, n)).astype(f32)
        with np.errstate(divide="ignore", invalid="ignore"):
            self.ny = np.where(mag > f32(1e-5), n[:, 1] / mag, f32(0.0)).astype(f32)
        # plan AABB prefilter for the FULL scan only: a tri whose plan box misses the point cannot return code 1
        m = 1e-3
        self.bx0, self.bx1 = W[:, :, 0].min(1) - m, W[:, :, 0].max(1) + m
        self.bz0, self.bz1 = W[:, :, 2].min(1) - m, W[:, :, 2].max(1) + m
        self.scan_ok = ~np.isin(self.ids, SKIP_IDS) & (self.ny > f32(0.1))   # WMPhysics.cs:16-29


def intersect(P0, P1, P2, ox, oy, oz):
    """WMPhysics.intersect3D_RayTriangle for a straight-down ray, vectorised in float32. Returns (code[T], Iy[T])."""
    ox, oy, oz = f32(ox), f32(oy), f32(oz)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        u = (P1 - P0).astype(f32)
        v = (P2 - P0).astype(f32)
        n = _cross(u, v)
        degenerate = _dot(n, n) < VEC_EPS
        O = np.array([ox, oy, oz], dtype=f32)
        w0 = (O - P0).astype(f32)
        a = (-_dot(n, w0)).astype(f32)
        b = (((n[:, 0] * f32(0)) + (n[:, 1] * f32(-1))) + (n[:, 2] * f32(0))).astype(f32)
        parallel = np.abs(b) < f32(1e-8)
        r = (a / b).astype(f32)
        Iy = (oy + r * f32(-1)).astype(f32)
        I = np.stack([np.full_like(Iy, ox), Iy, np.full_like(Iy, oz)], axis=-1)
        uu, uv, vv = _dot(u, u), _dot(u, v), _dot(v, v)
        w = (I - P0).astype(f32)
        wu, wv = _dot(w, u), _dot(w, v)
        D = (uv * uv - uu * vv).astype(f32)
        s = ((uv * wv - vv * wu) / D).astype(f32)
        t = ((uv * wu - uu * wv) / D).astype(f32)
        inside = ~((s < 0) | (s > 1)) & ~((t < 0) | ((s + t) > 1))
        code = np.where(inside & ~(r < 0), 1, 0)
        code = np.where(parallel, np.where(a == 0, 2, 0), code)
        code = np.where(degenerate, -1, code)
        Iy = np.where(degenerate, f32(0.0), Iy)                                # I = Vector3.zero
    return code, Iy


class Block:
    """WMBlock.Raycast over the cell's ActiveWalkMeshes (registration order)."""

    def __init__(self, meshes: list[Mesh]):
        self.meshes = meshes

    def full_scan(self, ox, oy, oz):
        for mi, m in enumerate(self.meshes):                                   # WMBlock.cs:185-199
            cand = np.nonzero(m.scan_ok & (m.bx0 <= ox) & (ox <= m.bx1) & (m.bz0 <= oz) & (oz <= m.bz1))[0]
            if cand.size == 0:
                continue
            code, Iy = intersect(m.P0[cand], m.P1[cand], m.P2[cand], ox, oy, oz)
            hit = np.nonzero(code == 1)[0]
            if hit.size == 0:
                continue
            ti = int(cand[hit[0]])                                             # FIRST passing tri, buffer order
            if int(m.ids[ti]) == VETO:                                         # WMBlock.cs:210: abandon this mesh
                continue
            return mi, ti, float(Iy[hit[0]]), int(m.ids[ti])
        return None

    def one_tri(self, mi, ti, ox, oy, oz):
        m = self.meshes[mi]
        code, Iy = intersect(m.P0[ti:ti + 1], m.P1[ti:ti + 1], m.P2[ti:ti + 1], ox, oy, oz)
        return int(code[0]), float(Iy[0])


class Cache:
    """s_moveCHRCache (ff9.cs:10749-10760) for ONE block: None = a slot that holds another block (ignored)."""

    def __init__(self):
        self.number = 0
        self.slots: list = [None] * 10

    def push(self, mi, ti):
        self.number = (self.number + 1) % 10                                   # WMBlock.cs:171-178
        self.slots[self.number] = (mi, ti)

    def flush(self):
        """Walking on OTHER blocks overwrites the slots with foreign entries (WMBlock.cs:150: Blocks[k] != this)."""
        self.slots = [None] * 10


class Walker:
    """The controlled on-foot actor on one cell."""

    def __init__(self, block: Block, heading_phi: float, cache: Cache | None = None):
        self.block = block
        self.phi = f32(heading_phi)                  # RotTrue + PsxRot(2048), degrees
        self.cache = cache if cache is not None else Cache()
        self.x = self.y = self.z = f32(0)
        self.id = 0
        self.part = None
        self.log: list = []

    def raycast(self, x, z, origin_y, use_cache=True):
        """w_nwpHit through WMBlock.Raycast: (pno, y, id, (src, (mesh, tri))). pno -1 = miss."""
        ox, oz = f32(x), f32(z)
        if use_cache:
            for i in range(10):                                                # WMBlock.cs:145-162
                k = (self.cache.number + i) % 10
                slot = self.cache.slots[k]
                if slot is None:
                    continue
                code, Iy = self.block.one_tri(slot[0], slot[1], ox, origin_y, oz)
                if code != 0:                                                  # WMPhysics.cs:63 (!= 0)
                    idv = int(self.block.meshes[slot[0]].ids[slot[1]])
                    if idv != VETO:
                        return 1000, f32(Iy), idv, ("cache", slot)
        h = self.block.full_scan(ox, origin_y, oz)
        if h is None:
            return -1, f32(0.0), 0, None
        mi, ti, y, idv = h
        if use_cache:
            self.cache.push(mi, ti)
        return 1000, f32(y), idv, ("scan", (mi, ti))

    def teleport(self, x: float, z: float, y_before: float = 5.0):
        """Ff9mkDebugMenu.WorldTeleportTo (:1837-1852) + w_movementChrInitSlice (ff9.cs:4596-4618: null cache, sky cast,
        filters on)."""
        self.x = f32(math.trunc(x * 256.0) / 256.0)
        self.z = f32(math.trunc(z * 256.0) / 256.0)
        self.y = f32(math.trunc(y_before * 256.0) / 256.0)
        pno, gy, idv, src = self.raycast(self.x, self.z, f32(self.y + RAY_START_SKY), use_cache=False)
        if pno < 0:
            raise RuntimeError(f"teleport ({x}, {z}): the sky cast missed")
        self.id = idv
        self.part = self.block.meshes[src[1][0]].name
        self.y = f32(gy + f32(slice_height(idv)))
        return self.state()

    def round_check(self, rot, speed):
        a = f32(f32(self.phi + rot) * f32(0.0174532924))
        px = f32(self.x + f32(math.sin(float(a))) * f32(speed))
        pz = f32(self.z + f32(math.cos(float(a))) * f32(speed))
        cache_ok = topo(self.id) not in (49, 52)                               # ff9.cs:5690-5699
        pno, gy, idv, src = self.raycast(px, pz, f32(self.y + RAY_START), use_cache=cache_ok)
        ok = pno >= 0 and limit_ok(idv)
        part = self.block.meshes[src[1][0]].name if src else None
        return ok, (px, gy, pz), idv, part, pno

    def tick(self):
        last = (self.x, self.y, self.z)
        part0 = self.part
        tried = []
        for th in SWEEP:
            rot = th
            ok, p, idv, part1, pno = self.round_check(rot, SPEED)
            tried.append((float(rot), "p1", ok, part1))
            if not ok:
                rot = f32(-th)
                ok, p, idv, part1, pno = self.round_check(rot, SPEED)
                tried.append((float(rot), "p1", ok, part1))
            if not ok:
                continue
            dx, dy, dz = f32(p[0] - last[0]), f32(p[1] - last[1]), f32(p[2] - last[2])
            if slice_height(idv) != 0.0:
                num8 = f32(math.sqrt(float(f32(dx * dx + dz * dz))))
            else:
                num8 = f32(math.sqrt(float(f32(f32(dx * dx + dy * dy) + dz * dz))))
            num9 = f32(f32(SPEED * SPEED) / num8) if int(num8 * 256.0) != 0 else f32(0)
            ok2, p2, idv2, part2, pno2 = self.round_check(rot, num9)
            tried.append((float(rot), "p2", ok2, part2))
            if ok2:
                self.x, self.z = p2[0], p2[2]
                self.y = f32(p2[1] + f32(slice_height(idv2)))
                self.id = idv2
                self.part = part2
                row = dict(self.state(), rot=float(rot), num9=float(num9), dy_probe=float(dy), probe_part=part1,
                           from_part=part0, collapsed=bool(part1 != part0 and float(num9) < 0.9 * float(SPEED)))
                self.log.append(row)
                return row
        row = dict(self.state(), rot=None, stalled=True, num9=0.0, collapsed=False, tried=tried)
        self.log.append(row)
        return row

    def state(self):
        return {"x": float(self.x), "z": float(self.z), "y": float(self.y), "part": self.part,
                "y_pub": math.trunc(float(self.y) * 256.0) / 256.0, "topo": topo(self.id)}


# --- cell assembly --------------------------------------------------------------------------------------------
_BLOCKS: dict = {}


def cell_block(amount: float, slit: float = 0.0) -> Block:
    """Terrain regenerated at +amount, then the stock Beach1/Sea1-5 in the bind oracle's registration order.
    ``slit`` > 0 (SYNTHETIC, the corollary only): pull the Terrain's three seam verts (476/480/484, -1120) north by
    that much, opening a plan slit between Terrain and Beach1 that no reshape here makes."""
    key = (amount, slit)
    if key in _BLOCKS:
        return _BLOCKS[key]
    import arealib as A
    walk = A.stock_walk_list(1, *CELL)
    assert [n for n, _ in walk][0] == "Terrain", walk
    meshes = []
    for name, mkey in walk:
        if name == "Terrain":
            V, ids = A.read_ff9mesh_arrays(regen_terrain(amount))
            if slit:
                V = V.copy()
                lx = V[:, :, 0] + 448.0
                lz = V[:, :, 2] - 1088.0
                on = (np.abs(lz - SEAM_Z) < 1e-4) & (lx > 475.99) & (lx < 484.01)
                V[:, :, 2] = np.where(on, V[:, :, 2] + slit, V[:, :, 2])
        else:
            V, ids = A.stock_mesh(mkey)
        meshes.append(Mesh(name, V, ids))
    _BLOCKS[key] = Block(meshes)
    return _BLOCKS[key]


def edge_drop(block: Block, x: float, z: float = SEAM_Z, eps: float = 2e-3) -> float:
    """Terrain y just north of the seam minus Beach1 y just south of it, at x (sky casts, full scan)."""
    t = block.full_scan(f32(x), f32(400.0), f32(z + eps))
    b = block.full_scan(f32(x), f32(400.0), f32(z - eps))
    return (t[2] - b[2]) if (t and b) else float("nan")


# --- ring reading ---------------------------------------------------------------------------------------------
def ring_positions(run_dir: Path, *, files=None, window=None):
    """Distinct player positions (frame, x, z, y_pub, key_up, status) in frame order from the run's state rings."""
    run_dir = Path(run_dir)
    files = files or sorted(p.name for p in run_dir.glob("states-*.jsonl"))
    rows, seen = [], set()
    for fn in files:
        p = run_dir / fn
        if not p.is_file():
            continue
        for ln in p.read_text(encoding="utf-8").splitlines():
            s = json.loads(ln)["state"]
            pl = s.get("player") or {}
            if pl.get("x") is None or pl.get("z") is None or s.get("ui_state") != "WorldHUD":
                continue
            fr = s["frame"]
            if fr in seen:
                continue
            seen.add(fr)
            x, z, y = pl["x"] / 256.0, pl["z"] / 256.0, pl["y"] / 256.0
            if window and not (window[0] <= x <= window[1] and window[2] <= z <= window[3]):
                continue
            rows.append((fr, x, z, y, s["input"].get("key_up"), s.get("debug_status") or ""))
    rows.sort()
    out = []
    for r in rows:
        if out and abs(out[-1][1] - r[1]) < 1e-6 and abs(out[-1][2] - r[2]) < 1e-6 and out[-1][3] == r[3]:
            continue
        out.append(r)
    return out


def segments(rows, starts=None):
    """Split ring positions into walks: a new segment at every teleport (a jump > 1.5u) and, given ``starts`` (the
    1/256-quantised line starts), at every arrival on a start. REVIEW FIX: L4's start (479.64, -1119.105) is only ~1.4u
    from where L2 ends on the beach, so the jump test alone glued L4's whole walk onto L2's segment and replay scored
    L4 as "0 ring rows"."""
    segs, cur = [], []
    for r in rows:
        at_start = bool(starts) and any(abs(r[1] - sx) < 1e-3 and abs(r[2] - sz) < 1e-3 for sx, sz in starts)
        if cur and at_start and abs(r[1] - cur[-1][1]) < 1e-6 and abs(r[2] - cur[-1][2]) < 1e-6:
            at_start = False                          # still standing on that start (a y re-publish): same walk
        if cur and (math.hypot(r[1] - cur[-1][1], r[2] - cur[-1][2]) > 1.5 or at_start):
            segs.append(cur)
            cur = []
        cur.append(r)
    if cur:
        segs.append(cur)
    return segs


def full_tick_heading(segs):
    """phi (RotTrue + 180, deg): the mean atan2(dx, dz) over consecutive ring positions that are ONE full tick apart."""
    phis = [math.degrees(math.atan2(b[1] - a[1], b[2] - a[2])) % 360.0
            for seg in segs for a, b in zip(seg, seg[1:]) if 0.40 < math.hypot(b[1] - a[1], b[2] - a[2]) < 0.44]
    if not phis:
        return None
    ref = phis[0]
    return (ref + sum(((p - ref + 180.0) % 360.0) - 180.0 for p in phis) / len(phis)) % 360.0


def match_ring(sim_rows, seg, tol=2e-3):
    """Every ring position after the start must equal SOME simulated tick position (ring samples can skip ticks)."""
    res = []
    for r in seg[1:]:
        k = min(range(len(sim_rows)), key=lambda i: math.hypot(sim_rows[i]["x"] - r[1], sim_rows[i]["z"] - r[2]))
        d = math.hypot(sim_rows[k]["x"] - r[1], sim_rows[k]["z"] - r[2])
        yerr = sim_rows[k]["y_pub"] - r[3]
        res.append({"ring": [round(r[1], 4), round(r[2], 4), round(r[3], 4)], "tick": k + 1,
                    "dxz": round(d, 5), "dy_pub": round(yerr, 5), "ok": d <= tol and abs(yerr) <= 1 / 256 + 1e-9})
    return res


def harness_verdict(st0, rows, *, bearing_vec, ticks_per_burst=3, distance=4.0, schedule=None,
                    commanded_ticks=None):
    """world_approach's verdict on a simulated walk (session.py:2851-2882): bursts of `ticks_per_burst` ticks,
    commanded = a free burst's reach; 'blocked' when a burst's progress along the bearing < 0.35 x commanded.

    ``schedule`` (REVIEW FIX): the ticks each burst actually held, in order. The world runs at WorldTPS 28 (Memoria.ini)
    against a 60 fps render, so a 6-frame hold holds 2 OR 3 ticks (2.8 on average) -- the session-5 +1 ring has 2-tick
    bursts at seqs 45 and 50 -- not a fixed B. ``commanded_ticks``: the ticks the stall test's `commanded` stands for
    (world_face's measured speed x burst frames: ~2.8 at 28 TPS / 60 fps); default = ``ticks_per_burst``."""
    commanded = (ticks_per_burst if commanded_ticks is None else commanded_ticks) * float(SPEED)
    sizes = list(schedule) if schedule is not None else []
    prog, prev, i, nb = 0.0, (st0["x"], st0["z"]), 0, 0
    while i < len(rows):
        n = sizes[nb] if nb < len(sizes) else ticks_per_burst
        nb += 1
        i = min(i + n, len(rows))
        end = rows[i - 1]
        step = (end["x"] - prev[0]) * bearing_vec[0] + (end["z"] - prev[1]) * bearing_vec[1]
        prog += step
        prev = (end["x"], end["z"])
        out = {"progress": round(prog, 2), "end": [round(end["x"], 4), round(end["z"], 4)], "end_tick": i,
               "bursts": nb}
        if step < commanded * HARNESS_STALL_FRACTION:
            return dict(out, outcome="blocked")
        if prog >= distance:
            return dict(out, outcome="reached")
    return {"outcome": "max", "progress": round(prog, 2)}


WORLD_TPS = 28.0                                      # Memoria.ini [Graphics] WorldTPS (FieldTPS is 30)


def burst_schedules(n: int, *, frames: int = 6, fps: float = 60.0, tps: float = WORLD_TPS, seed: int = 7):
    """``n`` random burst schedules: each burst holds the world ticks a ``frames``-frame window at a random phase of a
    ``tps`` clock catches (floor or ceil of frames*tps/fps) -- the irregularity a real run has and a 2-frame-tick
    stand-in does not."""
    import random
    rng = random.Random(seed)
    mean = frames * tps / fps
    lo = math.floor(mean)
    return [[lo + (1 if rng.random() < mean - lo else 0) for _ in range(60)] for _ in range(n)]


def descent_profile(st0, rows, seam_z=SEAM_Z):
    """The creep anatomy of one descent: d0 (edge distance when the first full probe crossed), the collapsed
    ticks (on-terrain creep + the crossing tick), the crossing tick, the creep step, the drop."""
    prev = st0
    out = {"cross_tick": None, "collapsed": [], "d0": None, "creep_step": None, "stalled_at": None, "drop": None}
    for i, r in enumerate(rows):
        if r.get("stalled"):
            out["stalled_at"] = i + 1
            break
        if r["collapsed"]:
            if out["d0"] is None:
                out["d0"] = round(prev["z"] - seam_z, 4)
                out["creep_step"] = round(r["num9"], 4)
                out["drop"] = round(-r["dy_probe"], 4)
            out["collapsed"].append(i + 1)
        if r["part"] != st0["part"]:
            out["cross_tick"] = i + 1
            out["landed"] = [round(r["x"], 4), round(r["z"], 4), r["y_pub"], r["part"]]
            break
        prev = r
    out["n_collapsed"] = len(out["collapsed"])
    return out


def run_line(block, start, phi, ticks, cache=None, y_before=5.0):
    w = Walker(block, phi, cache)
    st0 = w.teleport(start[0], start[1], y_before)
    return st0, [w.tick() for _ in range(ticks)]


SOUTH_LINES = {476.28: -1117.0, 479.64: -1117.0, 480.18: -1117.0}
NORTH_LINES = {476.28: -1120.28, 479.64: -1120.18, 480.18: -1120.36}
SOUTH_VEC = (0.0, -1.0)
NORTH_VEC = (0.0, 1.0)
PHI_S5_SOUTH = 181.388                                # session 5 (+3) south leg, measured (calibrate C2)
PHI_S5_NORTH = 358.55                                 # session 5 (+3) north leg, fitted (calibrate C4)


def bearing_to_phi(bearing_deg: float) -> float:
    """Harness bearing (atan2(dz, dx), 0 = +x, 90 = +z) -> the engine's RotTrue + 180 (atan2(dx, dz))."""
    return (90.0 - bearing_deg) % 360.0


# --- commands -----------------------------------------------------------------------------------------------------
def cmd_calibrate():
    import arealib as A
    report = {}
    # C0 -- regeneration: +0 must equal stock exactly
    V0, i0 = A.read_ff9mesh_arrays(regen_terrain(0))
    Vs, is_ = A.stock_mesh("d1/0_1/7,17/terrain")
    report["C0_regen_equals_stock"] = bool(np.array_equal(V0.astype(f32), Vs.astype(f32)) and np.array_equal(i0, is_))
    B = {a: cell_block(a) for a in (0.0, 1.0, 3.0)}
    report["C0_seam_drop_+3"] = {str(x): round(edge_drop(B[3.0], x), 4) for x in (476.28, 479.64, 480.18)}
    # C1 -- the teleport grounds (published y at the 6 starts of the +3 run)
    rec3 = json.loads((RUN_R3 / "terrain_session5.json").read_text(encoding="utf-8"))
    c1 = []
    for leg, lines in (("north", NORTH_LINES), ("south", SOUTH_LINES)):
        for r in rec3[leg]:
            st = Walker(B[3.0], 0.0).teleport(r["x"], lines[r["x"]], 5.0)
            c1.append({"leg": leg, "x": r["x"], "sim_y_pub": st["y_pub"], "ring_y": r["start"]["y"],
                       "ok": abs(st["y_pub"] - r["start"]["y"]) < 1e-6})
    report["C1_teleport_heights"] = c1
    # C2/C3 -- the +3 SOUTH walks, tick by tick against the ring; one heading for the leg, measured from full ticks
    rows = ring_positions(RUN_R3, window=(470, 486, -1126, -1114))
    segs = [s for s in segments(rows) if abs(s[0][2] + 1117.0) < 1e-3]
    phi = full_tick_heading(segs)
    south, cache = {}, Cache()                            # the three lines ran back to back on one cache
    for seg in segs:
        x0 = round(seg[0][1], 2)
        st0, sim = run_line(B[3.0], (x0, SOUTH_LINES[x0]), phi, 16, cache)
        m = match_ring(sim, seg)
        south[str(x0)] = {"phi": round(phi, 4), "matched": sum(r["ok"] for r in m), "of": len(m), "rows": m,
                          "profile": descent_profile(st0, sim),
                          "harness_3tick_bursts": harness_verdict(st0, sim, bearing_vec=SOUTH_VEC, distance=4.0),
                          "sim_ticks": [[i + 1, round(r["x"], 4), round(r["z"], 4), r["y_pub"], round(r["num9"], 4),
                                         r["part"]] for i, r in enumerate(sim[:14])]}
    report["C2_C3_south_+3"] = south
    # C4 -- the +3 NORTH walks (no ring rows: start/end in terrain_session5.json): fit ONE heading for all three
    best = None
    for k in range(-160, 161):
        ph = (k * 0.025) % 360.0
        cache, err, ends = Cache(), 0.0, []
        for r in rec3["north"]:
            st0, sim = run_line(B[3.0], (r["x"], NORTH_LINES[r["x"]]), ph, 8, cache)
            e = sim[-1]
            ends.append((e["x"], e["z"], e["y_pub"], [i + 1 for i, q in enumerate(sim) if q.get("stalled")][:1]))
            err = max(err, math.hypot(e["x"] - r["end"]["x"], e["z"] - r["end"]["z"]))
        if best is None or err < best[0]:
            best = (err, ph, ends)
    report["C4_north_+3_refusal"] = {
        "phi_fit": round(best[1], 3), "max_end_error": round(best[0], 4),
        "ends": [{"x": r["x"], "sim": [round(e[0], 4), round(e[1], 4), e[2]], "first_stalled_tick": e[3],
                  "seam_gap": round(SEAM_Z - e[1], 4), "ring": [r["end"]["x"], r["end"]["z"], r["end"]["y"]]}
                 for e, r in zip(best[2], rec3["north"])]}
    # C5 -- the +1 control NORTH climbs, tick by tick against the ring (one heading, from the full ticks)
    rows1 = ring_positions(RUN_R1, files=["states-final.jsonl"], window=(470, 486, -1126, -1114))
    segs1 = [s for s in segments(rows1) if s[0][2] < -1120.0 and len(s) > 2]
    phi1 = full_tick_heading(segs1)
    north1, cache = {}, Cache()
    for seg in segs1:
        x0 = round(seg[0][1], 2)
        st0, sim = run_line(B[1.0], (x0, NORTH_LINES[x0]), phi1, 12, cache, y_before=0.5)
        m = match_ring(sim, seg)
        north1[str(x0)] = {"phi": round(phi1, 4), "matched": sum(r["ok"] for r in m), "of": len(m), "rows": m,
                           "first_ticks": [[round(r["z"], 4), r["y_pub"], round(r["num9"], 4), r["part"]]
                                           for r in sim[:4]]}
    report["C5_north_+1_climb"] = north1
    # C6 -- stock: both directions legal at all three lines, no collapse, no stall (no ring: a sim-only control)
    c6 = {}
    for leg, lines, ph in (("south", SOUTH_LINES, PHI_S5_SOUTH), ("north", NORTH_LINES, PHI_S5_NORTH)):
        for x, z in lines.items():
            st0, sim = run_line(B[0.0], (x, z), ph, 16)
            c6[f"{leg} {x}"] = {"crossed": any(r["part"] != st0["part"] for r in sim),
                                "stalls": sum(1 for r in sim if r.get("stalled")),
                                "collapsed": sum(1 for r in sim if r["collapsed"]),
                                "min_step": round(min(r["num9"] for r in sim), 4)}
    report["C6_stock_legal"] = c6
    OUT.mkdir(exist_ok=True)
    (OUT / "stall_calibrate.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"C0 regenerated +0 == stock: {report['C0_regen_equals_stock']}; seam drop at +3: {report['C0_seam_drop_+3']}")
    print(f"C1 teleport grounds: {sum(c['ok'] for c in c1)}/{len(c1)} equal the published y")
    for k, v in south.items():
        print(f"C2/C3 south {k}: phi {v['phi']}  ring rows matched {v['matched']}/{v['of']}  profile {v['profile']}")
        print(f"      harness 3-tick bursts: {v['harness_3tick_bursts']}")
        for row in v["rows"]:
            if not row["ok"]:
                print("      MISS", row)
    c4 = report["C4_north_+3_refusal"]
    print(f"C4 north +3, ONE fitted heading phi {c4['phi_fit']}: max end error {c4['max_end_error']}")
    for e in c4["ends"]:
        print(f"      x {e['x']}: sim end {e['sim']} (stalled from tick {e['first_stalled_tick']}, "
              f"{e['seam_gap']}u short of the seam)  ring end {e['ring']}")
    for k, v in north1.items():
        print(f"C5 north +1 {k}: phi {v['phi']}  ring rows matched {v['matched']}/{v['of']}  first ticks "
              f"{v['first_ticks']}")
        for row in v["rows"]:
            if not row["ok"]:
                print("      MISS", row)
    print("C6 stock:", json.dumps(c6))
    return report


def seam_lines():
    """Descent lines across the welded Terrain|Beach1 seam: x 476.1 .. 483.9 (the straight z = -1120 stretch)."""
    return [round(476.1 + 0.2 * k, 2) for k in range(40)]


def cmd_map():
    B3 = cell_block(3.0)
    res = {}
    # (a) the seam map: every line starts 3u north of the seam (the session-5 protocol), session-5 heading
    rows_a = []
    for x in seam_lines():
        st0, sim = run_line(B3, (x, -1117.0), PHI_S5_SOUTH, 30)
        p = descent_profile(st0, sim)
        hv = harness_verdict(st0, sim, bearing_vec=SOUTH_VEC, distance=4.0)
        rows_a.append({"x": x, "drop": round(edge_drop(B3, x), 3), "creep_law": round(creep_step(edge_drop(B3, x)), 4),
                       **{k: p[k] for k in ("d0", "creep_step", "n_collapsed", "cross_tick", "stalled_at")},
                       "harness": hv["outcome"], "harness_end_z": hv.get("end", [None, None])[1]})
    res["seam_map"] = rows_a
    # (b) the phase map: one line (479.64, then 476.28), start z swept over one full step
    res["phase_map"] = {}
    for x in (479.64, 476.28):
        rows_b = []
        for k in range(0, 112, 2):
            z0 = -1117.0 - k / 256.0
            st0, sim = run_line(B3, (x, z0), PHI_S5_SOUTH, 30)
            p = descent_profile(st0, sim)
            rows_b.append({"z0": round(st0["z"], 5), "d0": p["d0"], "n_collapsed": p["n_collapsed"],
                           "cross_tick": p["cross_tick"],
                           "harness_B3": harness_verdict(st0, sim, bearing_vec=SOUTH_VEC)["outcome"],
                           "harness_B4": harness_verdict(st0, sim, bearing_vec=SOUTH_VEC, ticks_per_burst=4)["outcome"]})
        res["phase_map"][str(x)] = rows_b
    # (c) the drop sweep: the same reshape at other amounts, line 479.64 (creep law vs sim; climb refusal threshold)
    rows_c = []
    for amount in (0.5, 1.0, 1.5, 2.0, 2.25, 2.4, 2.5, 3.0, 4.0, 6.0, 10.0):
        B = cell_block(amount)
        drop = edge_drop(B, 479.64)
        st0, sim = run_line(B, (479.64, -1117.0), PHI_S5_SOUTH, 80)
        p = descent_profile(st0, sim)
        st1, simn = run_line(B, (479.64, NORTH_LINES[479.64]), PHI_S5_NORTH, 10, y_before=0.5)
        climbed = any(r["part"] != st1["part"] for r in simn)
        rows_c.append({"raise": amount, "drop": round(drop, 3), "creep_law": round(creep_step(drop), 4),
                       "creep_sim": p["creep_step"], "n_collapsed": p["n_collapsed"], "cross_tick": p["cross_tick"],
                       "descent_stalled": p["stalled_at"], "climb": "legal" if climbed else "REFUSED"})
    res["drop_sweep"] = rows_c
    # (d) the SLIT corollary (synthetic geometry, not the deployed mesh): a plan gap of width w between the
    # Terrain edge and Beach1 at +3 -- a full probe clears it, a collapsed step cannot
    rows_d = []
    for w in (0.0, 0.02, 0.04, 0.05, 0.07, 0.1, 0.2, 0.3, 0.42):
        B = cell_block(3.0, slit=w)
        st0, sim = run_line(B, (479.64, -1117.0), PHI_S5_SOUTH, 40)
        p = descent_profile(st0, sim)
        lateral = round(sim[-1]["x"] - st0["x"], 3)
        rows_d.append({"slit": w, "cross_tick": p["cross_tick"], "stalled_at": p["stalled_at"],
                       "n_collapsed": p["n_collapsed"], "end": [round(sim[-1]["x"], 4), round(sim[-1]["z"], 4)],
                       "lateral": lateral})
    res["slit_corollary"] = rows_d
    OUT.mkdir(exist_ok=True)
    (OUT / "stall_map.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("(a) SEAM MAP, +3, start z -1117, session-5 heading (engine: every line crosses; harness = the old reader)")
    print("    x       drop   v_c    d0      n_coll cross  harness")
    for r in rows_a:
        print(f"    {r['x']:<7} {r['drop']:<6} {r['creep_law']:<6} {str(r['d0']):<7} {r['n_collapsed']:<6} "
              f"{str(r['cross_tick']):<6} {r['harness']}")
    for x, rows_b in res["phase_map"].items():
        print(f"(b) PHASE MAP x={x}: start z -> d0 / collapsed ticks / harness(B=3, B=4)")
        print("    " + "  ".join(f"{r['z0']:.3f}:{r['n_collapsed']}{r['harness_B3'][0]}{r['harness_B4'][0]}"
                                  for r in rows_b))
    print("(c) DROP SWEEP at x 479.64")
    for r in rows_c:
        print(f"    {r}")
    print("(d) SLIT COROLLARY (synthetic plan gap at the +3 seam, x 479.64)")
    for r in rows_d:
        print(f"    {r}")
    return res


# --- the confirmation session's lines ---------------------------------------------------------------------------
def _start_for_d0(block, x, target_d0, phi, z_hi=-1118.9, z_lo=-1119.3):
    """The 1/256-quantised start z whose descent first collapses at d0 closest to target (scan, deterministic)."""
    best = None
    for k in range(int(round((z_hi - z_lo) * 256)) + 1):
        z0 = math.trunc((z_hi - k / 256.0) * 256.0) / 256.0
        st0, sim = run_line(block, (x, z0), phi, 6)
        p = descent_profile(st0, sim)
        if p["d0"] is None:
            continue
        if best is None or abs(p["d0"] - target_d0) < abs(best[1] - target_d0):
            best = (z0, p["d0"])
    return best


def session_plan(phi_s: float, phi_n: float, *, ticks_per_burst: int = 3, starts=None):
    """Simulate stall_session.py's lines in scenario order with one carried cache (flushed by each world_face).
    Returns {line: {...}}."""
    B3 = cell_block(3.0)
    starts = starts or STARTS
    out = {}
    cache = Cache()
    # C: the +3 CLIMB control (face 90 first): a TRUE stall the instrument must be able to see
    st0, sim = run_line(B3, starts["C"], phi_n, 12, cache, y_before=3.2)
    stalled_from = next((i + 1 for i, r in enumerate(sim) if r.get("stalled")), None)
    out["C"] = {"start": starts["C"], "phi": phi_n, "end": [round(sim[-1]["x"], 4), round(sim[-1]["z"], 4),
                                                            sim[-1]["y_pub"]],
                "moving_ticks": sum(1 for r in sim if not r.get("stalled")), "stalled_from_tick": stalled_from,
                "seam_gap": round(SEAM_Z - sim[-1]["z"], 4), "crossed": any(r["part"] != st0["part"] for r in sim)}
    cache.flush()                                          # world_face(270) walks the landing lawn
    for name, dist in (("L2", 4.0), ("L4", 1.5), ("L5", 1.5)):
        st0, sim = run_line(B3, starts[name], phi_s, 24, cache)
        p = descent_profile(st0, sim)
        hv = harness_verdict(st0, sim, bearing_vec=SOUTH_VEC, ticks_per_burst=ticks_per_burst, distance=dist)
        out[name] = {"start": starts[name], "start_q": [round(st0["x"], 5), round(st0["z"], 5)],
                     "start_y_pub": st0["y_pub"], "phi": phi_s, "profile": p, "approach": hv,
                     "drop": round(edge_drop(B3, starts[name][0]), 3),
                     "ticks": [[i + 1, round(r["x"], 4), round(r["z"], 4), r["y_pub"], round(r["num9"], 4), r["part"]]
                               for i, r in enumerate(sim)]}
    return out


STARTS = {"C": (479.64, -1120.18), "L2": (479.64, -1117.0), "L4": (479.64, -1119.105), "L5": (476.28, -1118.78)}


def cmd_predict():
    B3 = cell_block(3.0)
    # how the two phase-shifted starts were chosen (target d0: half a creep step for L4, ~5 creep steps for L5)
    pick = {"L4": _start_for_d0(B3, 479.64, 0.5 * creep_step(edge_drop(B3, 479.64)), PHI_S5_SOUTH),
            "L5": _start_for_d0(B3, 476.28, 0.37, PHI_S5_SOUTH, z_hi=-1118.6, z_lo=-1119.0)}
    nominal = session_plan(PHI_S5_SOUTH, PHI_S5_NORTH)
    band = {}
    creep_z: dict = {"L2": {}, "L5": {}}                # tick -> every z it takes across the heading band
    for dphi in (-2.0, -1.0, 0.0, 1.0, 2.0):           # world_face(tolerance=2.0) leaves up to 2 deg either way
        for B in (2, 3, 4):
            sp = session_plan((180.0 + dphi) % 360.0, (0.0 + dphi) % 360.0, ticks_per_burst=B)
            band[f"dphi{dphi:+g}/B{B}"] = {k: {"approach": v.get("approach", {}).get("outcome"),
                                               "n_collapsed": v.get("profile", {}).get("n_collapsed"),
                                               "cross_tick": v.get("profile", {}).get("cross_tick"),
                                               "d0": v.get("profile", {}).get("d0"),
                                               "C_end": v.get("end"), "C_stalled_from": v.get("stalled_from_tick")}
                                           for k, v in sp.items()}
            if B == 3:                                 # the ticks do not depend on B
                for name in ("L2", "L5"):
                    for t in sp[name]["profile"]["collapsed"]:
                        creep_z[name].setdefault(t, []).append(sp[name]["ticks"][t - 1][2])
    # REVIEW FIX: the K2/K5 acceptance tables. world_approach's "blocked" end is SOME creep tick of the line (or, for
    # L5, its crossing tick); which one depends on how the 2-or-3-tick bursts fall, so the scenario accepts any of
    # them -- each tick's z band across the heading tolerance is far narrower than the 0.06u between ticks.
    creep_table = {name: {str(t): {"mid": round((min(zs) + max(zs)) / 2, 4), "half_range": round((max(zs) - min(zs)) / 2, 4)}
                          for t, zs in sorted(tbl.items())} for name, tbl in creep_z.items()}
    # REVIEW FIX: the verdicts under REAL (irregular) bursts -- 6 frames at 60 fps against WorldTPS 28
    B3 = cell_block(3.0)
    mc = {}
    scheds = burst_schedules(4000)
    for name, dist in (("L2", 4.0), ("L4", 1.5), ("L5", 1.5)):
        st0, sim = run_line(B3, STARTS[name], PHI_S5_SOUTH, 30)
        hist: dict = {}
        for sc in scheds:
            hv = harness_verdict(st0, sim, bearing_vec=SOUTH_VEC, distance=dist, schedule=sc,
                                 commanded_ticks=6 * WORLD_TPS / 60.0)
            key = f"{hv['outcome']}@tick{hv.get('end_tick')}"
            hist[key] = hist.get(key, 0) + 1
        mc[name] = dict(sorted(hist.items()))
    res = {"starts": STARTS, "start_search": pick, "nominal_session5_headings": nominal, "heading_burst_band": band,
           "creep_tick_table": creep_table, "irregular_burst_mc": {"runs": len(scheds), "p_two_tick_burst": 0.2,
                                                                  "verdicts": mc}}
    OUT.mkdir(exist_ok=True)
    (OUT / "stall_predict.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("start search (z0, d0):", pick)
    for k, v in nominal.items():
        print(f"{k}: {json.dumps({kk: vv for kk, vv in v.items() if kk != 'ticks'})}")
        for t in v.get("ticks", [])[:(v.get("profile", {}).get("cross_tick") or 12) + 2]:
            print("      ", t)
    print("heading x burst band:")
    for k, v in band.items():
        print(f"  {k}: " + "; ".join(f"{n} {d['approach']} coll {d['n_collapsed']} cross {d['cross_tick']} d0 {d['d0']}"
                                     if n != "C" else f"C end {d['C_end']} stall@{d['C_stalled_from']}"
                                     for n, d in v.items()))
    print("creep-tick acceptance tables (tick: mid z +- half range over the +-2 deg band):")
    for name, tbl in creep_table.items():
        print(f"  {name}: " + "  ".join(f"{t}: {d['mid']} +-{d['half_range']}" for t, d in tbl.items()))
    print(f"irregular bursts ({len(scheds)} schedules, 6 frames at 60 fps vs WorldTPS {WORLD_TPS:g}):")
    for name, hist in mc.items():
        print(f"  {name}: {hist}")
    return res


def cmd_replay(run_dir):
    """Score a stall_session run against the simulator at the run's OWN measured headings."""
    run_dir = Path(run_dir)
    rec = json.loads((run_dir / "stall_session.json").read_text(encoding="utf-8"))
    rows = ring_positions(run_dir, window=(470, 486, -1126, -1114))
    starts_q = [(math.trunc(ln["start"][0] * 256) / 256, math.trunc(ln["start"][1] * 256) / 256) for ln in rec["lines"]]
    segs = segments(rows, starts_q)
    south_segs = [s for s in segs if s[0][2] > SEAM_Z + 0.5]
    phi_s = full_tick_heading(south_segs)
    if phi_s is None and rec.get("face_s"):
        phi_s = bearing_to_phi(rec["face_s"]["heading"])
    # the climb control has no full tick to measure: fit its heading to its end (as calibrate C4 did)
    c = next((ln for ln in rec["lines"] if ln["name"] == "C"), None)
    B3 = cell_block(3.0)
    phi_n = bearing_to_phi(rec["face_n"]["heading"]) if rec.get("face_n") else PHI_S5_NORTH
    if c and c.get("end"):
        best = None
        for k in range(-200, 201):
            ph = (phi_n + k * 0.02) % 360.0
            st0, sim = run_line(B3, tuple(c["start"]), ph, 12, y_before=3.2)
            err = math.hypot(sim[-1]["x"] - c["end"]["px"], sim[-1]["z"] - c["end"]["pz"])
            if best is None or err < best[0]:
                best = (err, ph)
        phi_n_fit, c_err = best[1], best[0]
    else:
        phi_n_fit, c_err = phi_n, None
    starts = {ln["name"]: tuple(ln["start"]) for ln in rec["lines"]}
    plan = session_plan(phi_s, phi_n_fit, starts={**STARTS, **starts})
    report = {"phi_south_measured": phi_s, "phi_north_face": phi_n, "phi_north_fit": phi_n_fit, "C_fit_error": c_err,
              "lines": {}}
    for ln in rec["lines"]:
        name = ln["name"]
        seg = [s for s in segs if math.hypot(s[0][1] - math.trunc(ln["start"][0] * 256) / 256,
                                             s[0][2] - math.trunc(ln["start"][1] * 256) / 256) < 0.01]
        sim_ticks = [{"x": t[1], "z": t[2], "y_pub": t[3]} for t in plan[name].get("ticks", [])]
        if name == "C":
            sim_ticks = [{"x": plan["C"]["end"][0], "z": plan["C"]["end"][1], "y_pub": plan["C"]["end"][2]}]
        m = match_ring(sim_ticks, seg[0]) if seg and sim_ticks else []
        # REVIEW FIX: "every ring row equals a simulated tick" is a FIDELITY check, not a discriminator -- a walk that
        # stalled at the edge (H_SEAM) or at the last full step (H_DROP) publishes a PREFIX of the simulated path and
        # matches it row for row (dry run: all three engines match). What separates them is how FAR the ring got:
        # whether it holds the predicted crossing tick (the drop onto the beach).
        cross = (plan[name].get("profile") or {}).get("cross_tick")
        last_ok = max((r["tick"] for r in m if r["ok"]), default=None)
        report["lines"][name] = {"ring_rows": len(seg[0]) - 1 if seg else 0, "matched": sum(r["ok"] for r in m),
                                 "misses": [r for r in m if not r["ok"]][:8], "last_matched_tick": last_ok,
                                 "predicted_cross_tick": cross,
                                 "ring_reaches_crossing": None if cross is None or last_ok is None else last_ok >= cross,
                                 "sim": {k: v for k, v in plan[name].items() if k != "ticks"},
                                 "recorded": {k: ln.get(k) for k in ("approach", "creep", "end")}}
    (run_dir / "stall_replay.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "lines"}, indent=1))
    for k, v in report["lines"].items():
        print(f"{k}: ring rows {v['ring_rows']}, matched by a sim tick {v['matched']} (last tick {v['last_matched_tick']}"
              f", crossing tick {v['predicted_cross_tick']} in the ring: {v['ring_reaches_crossing']}); "
              f"misses {v['misses'][:3]}")
    return report


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "calibrate"
    if cmd == "calibrate":
        cmd_calibrate()
    elif cmd == "map":
        cmd_map()
    elif cmd == "predict":
        cmd_predict()
    elif cmd == "replay":
        cmd_replay(sys.argv[2])
    else:
        raise SystemExit(f"unknown command {cmd!r}")
