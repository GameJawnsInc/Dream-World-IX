"""flight_v10_solve.py -- THE FLIGHT v10 (2026-07-23): MEASURED POSITION + MEASURED SIZE.

v9 placed Thomas at the creature's real per-frame SCREEN POSITION but at a CONSTANT apparent size. Playtest
(the user): "much better coverage ... he doesn't scale down during the swoop ... tweens around into place."
Both symptoms are the missing depth cue: a constant-size Thomas translating reads as a flat 2D tween, not a
creature moving through 3D. v10 adds the creature's real per-frame SIZE.

The s53 BONES row gives the creature's node-cloud AABB per frame. Its apparent on-screen height is
`WORLD_H * native_H / depth` (apparent size prop 1/depth) -- robust, unlike projecting the AABB's 8 corners
(near-camera corners explode; the raw AABB height spiked to 750x). `WORLD_H` = the median AABB Y-extent
(~5749 units); `depth` = the creature node-0 depth from the native reprojection (same math as v9's position).
Measured: the dragon shrinks to ~0.21x frame height during the far swoop (f176) and swells to 5-9x up close
during the charge. v10 sets Thomas's per-frame apparent height to that (smoothed, and clamped to
[FRAC_MIN, FRAC_MAX] so the 9x charge frames FILL the frame instead of overflowing), which:
  * makes him scale DOWN during the swoop (the headline fix), and
  * varies his placement DEPTH per frame -> real 3D motion, not a flat tween.

Position is unchanged from v9 (the creature's measured native screen NDC, back-projected through the MANAGED
camera that renders Thomas); one keyframe per frame so camera cuts render as faithful 1-frame cuts.

Run standalone: py flight_v10_solve.py -> prints the pasteable KEYFRAMES_V10 table build_thomas.py bakes.
"""
from __future__ import annotations

import statistics
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from matrix_solve import ProbeLog, project_world_to_ndc, DEFAULT_LOG
from flight_v7_solve import (KeyframeNode, make_node, check_segment, broadside_yaw_deg, _unwrap_deg,
                             THOMAS_SCALE)

NDC_CLAMP = 1.50
FRAC_MIN = 0.18            # Thomas never shrinks below this (still visible during the far swoop)
FRAC_MAX = 0.70            # cap the giant charge frames (dragon hits 9x) near v9's proven ~0.55 charge size
                          # -- the goal is the SWOOP SHRINK (0.21), not a frame-overflowing wall-of-train
SMOOTH_WIN = 2            # +/- frames median-smoothing of the size (depth is noisy frame-to-frame)
LEADIN_NDC = (0.10, 1.10)  # off-frame top, descending in ("flying down")
LEADIN_FRAC = 0.34
EXIT_HOLD_FRAMES = (470, 520)


def _sat16(v: int) -> int:
    return -32768 if v < -32768 else (32767 if v > 32767 else v)


def parse(path: Path) -> Tuple[Dict[int, Tuple[float, float]], Dict[int, float]]:
    """frame -> (ndc_x, ndc_y) measured native screen position; frame -> dragon apparent height fraction.
    Reliable frames only (drawn + composed sane)."""
    psx: Dict[int, Tuple[list, list, int]] = {}
    sm: Dict[int, dict] = {}
    wh: Dict[int, int] = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        if line[0] == "#":
            continue
        p = line.rstrip("\n").split(",")
        if p[0] == "PSXCAM":
            f = int(p[2]); psx[f] = ([int(x) for x in p[3:12]], [int(x) for x in p[12:15]], int(p[17]))
        elif p[0] == "MODEL" and p[3] == "S":
            f = int(p[2]); sm[f] = dict(b=p[26], wx=int(p[14]), wy=int(p[15]), wz=int(p[16]),
                                        ax=int(p[11]), ay=int(p[12]), az=int(p[13]))
        elif p[0] == "BONES":
            wh[int(p[2])] = int(p[11]) - int(p[8])   # maxY - minY = the creature's world height
    WORLD_H = statistics.median(wh.values()) if wh else 5749.0
    ndc: Dict[int, Tuple[float, float]] = {}
    raw_frac: Dict[int, float] = {}
    for f in sorted(sm):
        d = sm[f]
        if d["b"] == "00000000" or f not in psx:
            continue
        if abs(d["wx"] - d["ax"]) > 5000 or abs(d["wy"] - d["ay"]) > 5000 or abs(d["wz"] - d["az"]) > 5000:
            continue
        R, T, H = psx[f]
        v = (d["wx"], d["wy"], d["wz"])
        px = ((R[0] * v[0] + R[1] * v[1] + R[2] * v[2]) >> 12) + T[0]
        py = ((R[3] * v[0] + R[4] * v[1] + R[5] * v[2]) >> 12) + T[1]
        pz = ((R[6] * v[0] + R[7] * v[1] + R[8] * v[2]) >> 12) + T[2]
        if pz <= 0:
            continue
        sz = min(65535, pz)
        sx = 160 + ((_sat16(px) * ((H << 16) // sz)) >> 16)
        sy = 120 + ((_sat16(py) * ((H << 16) // sz)) >> 16)
        ndc[f] = ((sx - 160) / 160.0, (120 - sy) / 120.0)
        raw_frac[f] = WORLD_H * H / pz / 240.0    # dragon apparent height fraction (prop 1/depth)
    # smooth (median over a small window) then clamp
    fr_frames = sorted(raw_frac)
    frac: Dict[int, float] = {}
    for i, f in enumerate(fr_frames):
        lo = max(0, i - SMOOTH_WIN); hi = min(len(fr_frames), i + SMOOTH_WIN + 1)
        m = statistics.median(raw_frac[fr_frames[j]] for j in range(lo, hi))
        frac[f] = max(FRAC_MIN, min(FRAC_MAX, m))
    return ndc, frac


def _clamp(x: float, y: float) -> Tuple[float, float]:
    return (max(-NDC_CLAMP, min(NDC_CLAMP, x)), max(-NDC_CLAMP, min(NDC_CLAMP, y)))


def build_flight(log: ProbeLog, ndc: Dict[int, Tuple[float, float]], frac: Dict[int, float]) -> List[KeyframeNode]:
    meas = sorted(f for f in ndc if log.has_camera(f))
    f0, f1 = meas[0], meas[-1]
    mx = np.array(meas, dtype=np.float64)
    nxs = np.array([ndc[f][0] for f in meas]); nys = np.array([ndc[f][1] for f in meas])
    fmx = np.array([f for f in meas if f in frac], dtype=np.float64)
    fvs = np.array([frac[f] for f in meas if f in frac])
    nodes: List[KeyframeNode] = [make_node(log, 0, LEADIN_NDC[0], LEADIN_NDC[1], LEADIN_FRAC, "lead-in (flying down)")]
    for f in range(f0, f1 + 1):
        if not log.has_camera(f):
            continue
        nx, ny = _clamp(float(np.interp(f, mx, nxs)), float(np.interp(f, mx, nys)))
        hf = float(np.interp(f, fmx, fvs))                       # per-frame measured apparent size
        tag = f"measured f{f}" if f in ndc else f"gap f{f}"
        nodes.append(make_node(log, f, nx, ny, hf, tag))
    hold = nodes[-1].world
    hold_hf = nodes[-1].height_frac
    for f in EXIT_HOLD_FRAMES:
        if f <= f1 or not log.has_camera(f):
            continue
        nxp, nyp, _, _ = project_world_to_ndc(log.view(f), log.proj(f), hold)
        nodes.append(KeyframeNode(f, nxp, nyp, hold_hf, hold, f"fire column (camera off him, f{f})"))
    yaws = _unwrap_deg([broadside_yaw_deg(log.view(n.frame)) for n in nodes])
    return [n._replace(yaw_deg=y) for n, y in zip(nodes, yaws)]


def _fmt(p) -> str:
    return f"({p[0]:8.1f}, {p[1]:8.1f}, {p[2]:9.1f})"


def print_report(log: ProbeLog, ndc, frac) -> List[KeyframeNode]:
    nodes = build_flight(log, ndc, frac)
    print(f"=== THE FLIGHT v10 -- MEASURED POSITION + SIZE ({len(nodes)} keyframes, frames {nodes[0].frame}..{nodes[-1].frame}) ===")
    fr = [frac[f] for f in sorted(frac)]
    print(f"  measured window: {min(ndc)}..{max(ndc)}; apparent size frac min {min(fr):.2f} median {statistics.median(fr):.2f} max {max(fr):.2f} (clamped [{FRAC_MIN},{FRAC_MAX}])")
    print(f"\n{'frame':>5} | {'ndc_x':>6} {'ndc_y':>6} | {'size':>5} | {'yaw':>7} | world (X,Y,Z)")
    for n in nodes:
        if n.frame % 16 == 0 or n.label.startswith(("lead", "fire")):
            print(f"{n.frame:5d} | {n.ndc_x:+6.2f} {n.ndc_y:+6.2f} | {n.height_frac:5.2f} | {n.yaw_deg:+7.1f} | {_fmt(n.world)}")
    worst = max((check_segment(log, nodes[i], nodes[i + 1])[1] for i in range(len(nodes) - 1)), default=0.0)
    print(f"\n  worst |ndc| between keyframes: {worst:.2f} (phase-4 exit is intentionally off-frame)")
    print("\n=== KEYFRAMES_V10 -- paste into build_thomas.py ===")
    for n in nodes:
        x, y, z = round(n.world[0]), round(n.world[1]), round(n.world[2])
        print(f"    ({n.frame:4d}, ({x:7d}, {y:7d}, {z:8d}), {n.yaw_deg:+7.2f}),  # {n.label}")
    return nodes


def main() -> int:
    log = ProbeLog.parse(DEFAULT_LOG)
    ndc, frac = parse(DEFAULT_LOG)
    print_report(log, ndc, frac)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
