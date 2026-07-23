"""flight_v9_solve.py -- THE FLIGHT v9 (2026-07-23): MEASURED. The first flight built from the creature's
REAL per-frame screen path, not a constructed or mis-projected one.

The s53 probe (PROBE.md sec 11) + the FORMAT round settled why v5/v7/v8 all failed: the creature projects
through the plugin's own native GTE (world->view matrix M @0x1C1DC8 + OFX=160/OFY=120/H), NOT the managed
Unity VIEW/PROJ. Reading out the cast (disasm/FORMAT.md sec 5.4):
  * the creature IS the single summon slot (hasMotion=1 on kind=S only, 0 eff slots) -- settled;
  * reprojecting its COMPOSED node-0 (*(DATA+0x38)) through the native M+GTE lands ON-SCREEN with ZERO
    false positives (every on-screen frame also has the body mesh drawn) and DEAD CENTER through the
    float/charge (f288 ndc (+0.00,-0.01), f300 (0,0)).

So we finally have the creature's measured screen NDC per frame. v9 places Thomas THERE: for each reliable
frame it takes the creature's measured native NDC (SX,SY -> ndc), and back-projects it through the MANAGED
VIEW/PROJ (the camera that actually renders Thomas, a managed Unity object) at a chosen apparent size. Thomas
lands where the real dragon was on screen, at a controlled size -- faithful position, promo-friendly size.

Windows (from the readout):
  * reliable creature window = frames 82-415 (drawn AND composed sane); after 415 the creature stops being
    drawn (bones32 goes stale -> garbage), which IS the user's phase 4 (the camera leaves for the fire
    column). v9 recedes Thomas there.
  * the measured path dips off-frame briefly during the swoop-by/fly-by (f132/f156/f168/f240/f312/f384) --
    KEPT (that is the real "swooping by"), but clamped to |ndc|<=CLAMP so a dip never flings him to infinity.

Run standalone: py flight_v9_solve.py -> prints the pasteable KEYFRAMES_V9 table build_thomas.py bakes.
THOMAS_SCALE must stay in sync with build_thomas.py (265).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from matrix_solve import ProbeLog, project_world_to_ndc, world_from_ndc, DEFAULT_LOG
from flight_v7_solve import (KeyframeNode, make_node, solve_path, check_segment, broadside_yaw_deg,
                             _unwrap_deg, solve_height_depth, THOMAS_HEIGHT_SCALED, THOMAS_SCALE, DRIFT_LIMIT)

BODY = {"0033B990", "0033B9D0", "0035BAD0", "0035BA90", "0034BA10", "0034BA50", "0097BD02"}
HEIGHT_FRAC = 0.55          # Thomas's apparent size (fraction of frame height) at his measured position
NDC_CLAMP = 1.50            # a brief off-frame dip is faithful; never fling him past this
# KEY_STEP=1 -- a keyframe at EVERY reliable frame. The creature's world position (back-projected from its
# measured screen NDC through the MANAGED camera) jumps at each of the ~15 camera hard-cuts; interpolating
# ACROSS a cut is what made the sparse version swing 111x off-frame. One keyframe per frame removes the
# interpolation entirely -- each frame lands at its own measured screen position, and a cut renders as a
# faithful 1-frame cut, not a multi-frame swing. The cost is a big (generated) constant, which is free.
KEY_STEP = 1
LEADIN_NDC = (0.10, 1.10, 0.34)   # off-frame top, descending into the first measured frame ("flying down")
EXIT_HOLD_FRAMES = (470, 520, 580)  # phase 4: creature undrawn, camera on the fire column -> Thomas recedes


def _sat16(v: int) -> int:
    return -32768 if v < -32768 else (32767 if v > 32767 else v)


def parse_native_path(path: Path) -> Tuple[Dict[int, Tuple[float, float]], set]:
    """frame -> (ndc_x, ndc_y) of the creature's measured NATIVE screen position, plus the body-mesh set.
    Reliable frames only (drawn + composed sane); native NDC from the M+GTE reprojection of composed node-0."""
    psxcam: Dict[int, Tuple[list, list, int]] = {}
    smodel: Dict[int, dict] = {}
    body: set = set()
    for line in open(path, encoding="utf-8", errors="replace"):
        if line[0] == "#":
            continue
        p = line.rstrip("\n").split(",")
        if p[0] == "PSXCAM":
            f = int(p[2]); psxcam[f] = ([int(x) for x in p[3:12]], [int(x) for x in p[12:15]], int(p[17]))
        elif p[0] == "MODEL" and p[3] == "S":
            f = int(p[2]); smodel[f] = dict(b=p[26], wx=int(p[14]), wy=int(p[15]), wz=int(p[16]),
                                            ax=int(p[11]), ay=int(p[12]), az=int(p[13]))
        elif p[0] == "MESH" and p[4] in BODY:
            body.add(int(p[2]))
    ndc: Dict[int, Tuple[float, float]] = {}
    for f in sorted(smodel):
        d = smodel[f]
        if d["b"] == "00000000" or f not in psxcam:
            continue
        if abs(d["wx"] - d["ax"]) > 5000 or abs(d["wy"] - d["ay"]) > 5000 or abs(d["wz"] - d["az"]) > 5000:
            continue   # stale-arena garbage after the creature stops drawing
        R, T, H = psxcam[f]
        v = (d["wx"], d["wy"], d["wz"])
        px = ((R[0] * v[0] + R[1] * v[1] + R[2] * v[2]) >> 12) + T[0]
        py = ((R[3] * v[0] + R[4] * v[1] + R[5] * v[2]) >> 12) + T[1]
        pz = ((R[6] * v[0] + R[7] * v[1] + R[8] * v[2]) >> 12) + T[2]
        if pz <= 0:
            continue    # behind the native camera -> genuinely not on this frame
        sz = min(65535, pz)
        sx = 160 + ((_sat16(px) * ((H << 16) // sz)) >> 16)
        sy = 120 + ((_sat16(py) * ((H << 16) // sz)) >> 16)
        ndc[f] = ((sx - 160) / 160.0, (120 - sy) / 120.0)   # native screen 320x240, center (160,120)
    return ndc, body


def _clamp_ndc(x: float, y: float) -> Tuple[float, float]:
    return (max(-NDC_CLAMP, min(NDC_CLAMP, x)), max(-NDC_CLAMP, min(NDC_CLAMP, y)))


def build_flight(log: ProbeLog, ndc: Dict[int, Tuple[float, float]]) -> List[KeyframeNode]:
    meas = sorted(f for f in ndc if log.has_camera(f))
    f0, f1 = meas[0], meas[-1]
    # DENSIFY: fill every frame in [f0,f1] by linear interpolation of the SCREEN NDC over the gaps (frames
    # where the creature was behind-camera / stale). This keeps Thomas's screen path CONTINUOUS through the
    # gaps instead of cutting straight across them, and -- with a keyframe at every frame -- leaves no
    # interpolation interval to swing. World-space jumps at the camera hard-cuts then render as faithful
    # 1-frame cuts (screen stays smooth because the NDC is interpolated).
    mx = np.array(meas, dtype=np.float64)
    nxs = np.array([ndc[f][0] for f in meas]); nys = np.array([ndc[f][1] for f in meas])
    nodes: List[KeyframeNode] = [make_node(log, 0, *LEADIN_NDC, "lead-in (off-frame top, flying down)")]
    for f in range(f0, f1 + 1):
        if not log.has_camera(f):
            continue
        nx = float(np.interp(f, mx, nxs)); ny = float(np.interp(f, mx, nys))
        nx, ny = _clamp_ndc(nx, ny)
        tag = f"measured f{f}" if f in ndc else f"gap-interp f{f}"
        nodes.append(make_node(log, f, nx, ny, HEIGHT_FRAC, tag))
    # phase 4: the creature is no longer drawn (camera on the fire column). Hold Thomas's last measured world
    # position; the moving managed camera carries him out of frame -- faithful "the camera moves off him".
    hold = nodes[-1].world
    for f in EXIT_HOLD_FRAMES:
        if f <= f1 or not log.has_camera(f):
            continue
        nx, ny, _, _ = project_world_to_ndc(log.view(f), log.proj(f), hold)
        nodes.append(KeyframeNode(f, nx, ny, HEIGHT_FRAC, hold, f"fire column (camera off him -- hold, f{f})"))
    yaws = _unwrap_deg([broadside_yaw_deg(log.view(n.frame)) for n in nodes])
    return [n._replace(yaw_deg=y) for n, y in zip(nodes, yaws)]


def _fmt(p) -> str:
    return f"({p[0]:8.1f}, {p[1]:8.1f}, {p[2]:9.1f})"


def print_report(log: ProbeLog, ndc: Dict[int, Tuple[float, float]], body: set) -> List[KeyframeNode]:
    nodes = build_flight(log, ndc)
    print(f"=== THE FLIGHT v9 -- MEASURED ({len(nodes)} keyframes, frames {nodes[0].frame}..{nodes[-1].frame}) ===")
    print(f"  measured creature window: {min(ndc)}..{max(ndc)} ({len(ndc)} reliable frames)")
    print(f"  HEIGHT_FRAC={HEIGHT_FRAC}  NDC_CLAMP={NDC_CLAMP}  THOMAS_SCALE={THOMAS_SCALE}")
    print(f"\n{'frame':>5} | {'ndc_x':>7} {'ndc_y':>7} | {'yaw':>7} | world (X,Y,Z)          | label")
    for n in nodes:
        print(f"{n.frame:5d} | {n.ndc_x:+7.2f} {n.ndc_y:+7.2f} | {n.yaw_deg:+7.1f} | {_fmt(n.world)} | {n.label}")
    # drift on the measured segments (informational -- the measured path itself can dip off-frame)
    print("\n=== drift between consecutive measured keyframes (informational) ===")
    worst = 0.0
    for i in range(len(nodes) - 1):
        _, w, _ = check_segment(log, nodes[i], nodes[i + 1])
        worst = max(worst, w)
    print(f"  worst |ndc| between keyframes: {worst:.2f} (measured path legitimately dips off-frame on the swoop-by)")
    print("\n=== KEYFRAMES_V9 -- paste into build_thomas.py ===")
    for n in nodes:
        x, y, z = round(n.world[0]), round(n.world[1]), round(n.world[2])
        print(f"    ({n.frame:4d}, ({x:7d}, {y:7d}, {z:8d}), {n.yaw_deg:+7.2f}),  # {n.label}")
    return nodes


def main() -> int:
    log = ProbeLog.parse(DEFAULT_LOG)
    ndc, body = parse_native_path(DEFAULT_LOG)
    print_report(log, ndc, body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
