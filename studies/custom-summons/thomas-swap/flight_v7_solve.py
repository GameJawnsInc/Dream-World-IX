"""flight_v7_solve.py -- THE FLIGHT v7 (2026-07-22): IN-FRAME BY CONSTRUCTION.

Supersedes FLIGHT v5 (matrix_solve.py's "track Bahamut verbatim"). v5 was SOUND on its own premise
(Thomas is an ordinary GameObject whose world position is force-set every frame and rendered by the
real per-frame camera, so projecting a world point through the logged VIEW/PROJ correctly predicts
where it lands on screen -- this is empirically corroborated and NOT in question here) but the premise
itself -- "faithful = wherever Bahamut's own body was, off-screen swoops included" -- produces a promo
clip that is mostly EMPTY: matrix_solve.py's own self-test measures only ~4/323 (1.2%) of Bahamut's own
measured frames landing on-screen. The mission's goal is now explicit: THOMAS VISIBLE AND DRAMATIC
THROUGHOUT, a promo shot, not a fidelity exercise. The user accepted this trade.

THE ONE THING THAT STAYS SOUND (unchanged from v5): the captured per-frame VIEW/PROJ matrices ARE valid
for Thomas -- he is rendered by the real Unity pipeline under the real per-frame camera, so world points
project correctly through them (matrix_solve.py's round-trip self-test + PROBE.md's corroboration). Only
Bahamut's own native-pipeline position is the piece being abandoned as a placement source -- not the
projection math, which this module reuses verbatim (imports matrix_solve, no reimplementation).

=== THE METHOD -- construct in NDC, back-project to world ===

  1. Choose a target screen position (ndc_x, ndc_y) and apparent HEIGHT fraction of frame per authored
     "beat" (the story waypoints below), comfortably inside frame (|ndc| <= ~0.55).
  2. Solve the camera-space depth that makes Thomas's own (scaled) height actually fill that fraction,
     using THAT FRAME's real PROJ[1][1] (the vertical focal term -- PROJ zooms ~2.33..4.65 across the
     cast, so the same target height fraction needs a DIFFERENT depth at every frame):
         apparent_height_frac = (PROJ[1][1] * thomas_height_scaled / depth) / 2
         depth = PROJ[1][1] * thomas_height_scaled / (2 * height_frac)
  3. Back-project (ndc_x, ndc_y, view_z=-depth) through THAT FRAME's real VIEW+PROJ with
     matrix_solve.world_from_ndc (the general off-center-frustum inverse, round-trip verified exact).
  4. Derive per-keyframe YAW from the camera's own forward vector so Thomas presents broadside to THAT
     frame's actual camera, not a fixed world angle (closing the "known open item" both v4 and v5 left
     for a fixed-yaw camera that turned out to pan/orbit/cut).

=== WHY THE KEYFRAME COUNT ISN'T A FLAT 14-18 (an honest deviation, not an oversight) ===

The mission's own drift-margin language ("dense enough that between-keyframe drift cannot wander out of
frame") assumes a camera that pans/zooms *smoothly*. Measuring the real per-frame eye position
(`camera_eye_census` below) shows this cast's camera is CUT-HEAVY, not smooth: dozens of single-FRAME eye
jumps of 2000-22000 world units (real hard cuts, not interpolatable) are interleaved with a few
sustained fast continuous dolly/orbit shots (hundreds of units per frame for tens of frames). A hand-
picked ~16-beat story arc, tested directly against this real camera log, blows the |ndc|<=1 drift
envelope by 10-75x on more than half its segments (see the module's own dev history / git blame for the
first, naive attempt). Rather than ship that and call it "dense enough," this module ADAPTS: it treats
the ~16 hand-authored beats below as mandatory story waypoints (each still lands as a real keyframe, at
its own authored ndc/height), and RECURSIVELY BISECTS any segment between two waypoints whose real
camera drift would exceed the margin, inserting exactly as many extra in-between keyframes as the real
log demands (verified per-segment, not assumed) -- interpolating the *intended* screen position/size
linearly between the two flanking authored points for each inserted keyframe, then solving ITS world
position the same way. The result typically runs higher than 18 total keyframes (every insertion is a
real, measured necessity, printed and accounted for below) -- an honest trade of the raw headline count
for the thing the mission actually asked to guarantee: no segment drifts out of frame.

Run standalone: `py flight_v7_solve.py` parses the real probe log, builds the adaptive keyframe path,
verifies every final segment, and prints the exact pasteable table `build_thomas.py`'s `KEYFRAMES_V7`
constant was baked from.
"""
from __future__ import annotations

import math
from typing import List, NamedTuple, Tuple

import numpy as np

from matrix_solve import ProbeLog, project_world_to_ndc, world_from_ndc, DEFAULT_LOG

# --------------------------------------------------------------------------- Thomas's own geometry
# Must match build_thomas.py's THOMAS_SCALE (README.md "Scale reasoning": raw normalized bbox height
# 4.913, engine-verbatim no unit conversion). Independent literal here (this solver has no dependency on
# the ff9mapkit package / game-path resolution build_thomas.py needs) -- this comment is the sync point.
THOMAS_RAW_HEIGHT = 4.913
THOMAS_SCALE = 265
THOMAS_HEIGHT_SCALED = THOMAS_RAW_HEIGHT * THOMAS_SCALE   # ~1301.9

IN_FRAME_MARGIN = 0.55       # target range for every AUTHORED beat's own (ndc_x, ndc_y)
DRIFT_LIMIT = 0.85           # hard cap for every INTERMEDIATE (non-keyframe) sampled frame
ENTRANCE_NDC = (-0.90, +0.05, 0.35)   # the one named exception -- "start near ndc -0.9 and come in"
MAX_BISECT_DEPTH = 10


class Waypoint(NamedTuple):
    frame: int
    ndc_x: float
    ndc_y: float
    height_frac: float
    label: str


class KeyframeNode(NamedTuple):
    frame: int
    ndc_x: float
    ndc_y: float
    height_frac: float
    world: Tuple[float, float, float]
    label: str
    yaw_deg: float = 0.0   # filled in after the path is built (needs cross-node unwrap)


# --------------------------------------------------------------------------- THE AUTHORED BEATS (story arc)
# swooping ENTRANCE (edge -> center) -> CENTER-STAGE reign w/ gentle bob+charge -> a slow LATERAL PASS ->
# BIG AND PRESENT through the fire-column/aftermath window (430-540, the beats the user liked) -> a short
# EXIT at the very end. Every beat's own ndc sits within +/-IN_FRAME_MARGIN (the frame-0 entrance origin
# is the one named exception, handled separately -- see ENTRANCE_NDC above).
BEATS: Tuple[Waypoint, ...] = (
    Waypoint( 30, -0.55,  0.00, 0.48, "swoop continues"),
    Waypoint( 55, -0.20,  0.05, 0.55, "arriving"),
    Waypoint( 80,  0.00,  0.10, 0.60, "center-stage begin"),
    Waypoint(115,  0.10,  0.20, 0.62, "reign bob (up)"),
    Waypoint(150, -0.08, -0.05, 0.58, "reign bob (down)"),
    Waypoint(185,  0.10,  0.15, 0.63, "charge windup"),
    Waypoint(215,  0.00,  0.25, 0.65, "charge peak"),
    Waypoint(250, -0.45,  0.05, 0.55, "lateral pass (left)"),
    Waypoint(290,  0.45,  0.05, 0.55, "lateral pass (right)"),
    Waypoint(330,  0.05,  0.00, 0.58, "return toward center"),
    Waypoint(400,  0.00,  0.15, 0.62, "settle, approach fire column"),
    Waypoint(430,  0.05,  0.20, 0.65, "fire column ignition -- BIG"),
    Waypoint(470, -0.05,  0.15, 0.65, "fire column continues -- stay BIG"),
    Waypoint(510,  0.00,  0.10, 0.62, "aftermath -- still present"),
    Waypoint(540,  0.00,  0.05, 0.55, "aftermath settle"),
    Waypoint(560,  0.25, -0.15, 0.45, "exit begin"),
    Waypoint(580,  0.50, -0.30, 0.35, "exit end"),
)


# --------------------------------------------------------------------------- camera helpers
def camera_forward(view: np.ndarray) -> np.ndarray:
    """World-space forward (look) direction of the camera whose worldToCameraMatrix is ``view``. Camera
    space looks down -Z (view_z < 0 == in front, matching matrix_solve's own convention), so the forward
    direction in view space is (0,0,-1); transforming a DIRECTION (not a point) back to world drops the
    translation: world_dir = R^T @ view_dir = -R^T[:,2] = -R[2,:] (R = the rotation block of VIEW -- the
    same block ProbeLog's own cam_pos() helper uses for the eye position, c = -R.T @ t)."""
    R = view[:3, :3]
    fwd = -R[2, :3]
    n = np.linalg.norm(fwd)
    return fwd / n if n > 1e-9 else fwd


def broadside_yaw_deg(view: np.ndarray) -> float:
    """Yaw (degrees, world-space Ry) making Thomas's nose (world +Z at yaw=0, README axis-verification)
    perpendicular to the camera's own horizontal look direction -- his SIDE profile faces the lens. Two
    solutions exist (+90/-90 from the forward's own horizontal angle); this picks +90 consistently -- the
    full sequence is unwrapped afterward (see _unwrap_deg) so it never snaps the long way around."""
    fwd = camera_forward(view)
    phi_f = math.degrees(math.atan2(fwd[0], fwd[2]))
    return phi_f + 90.0


def _unwrap_deg(seq: List[float]) -> List[float]:
    if not seq:
        return seq
    out = [seq[0]]
    for v in seq[1:]:
        d = ((v - out[-1] + 180.0) % 360.0) - 180.0
        out.append(out[-1] + d)
    return out


def solve_height_depth(proj: np.ndarray, height_frac: float) -> float:
    return proj[1, 1] * THOMAS_HEIGHT_SCALED / (2.0 * height_frac)


# --------------------------------------------------------------------------- adaptive keyframe construction
def make_node(log: ProbeLog, frame: int, ndc_x: float, ndc_y: float, height_frac: float, label: str) -> KeyframeNode:
    view, proj = log.view(frame), log.proj(frame)
    depth = solve_height_depth(proj, height_frac)
    world = world_from_ndc(view, proj, ndc_x, ndc_y, -depth)
    return KeyframeNode(frame, ndc_x, ndc_y, height_frac, world, label)


def _interp_intent(a: KeyframeNode, b: KeyframeNode, frame: int) -> Tuple[float, float, float]:
    t = (frame - a.frame) / (b.frame - a.frame)
    return (
        a.ndc_x + (b.ndc_x - a.ndc_x) * t,
        a.ndc_y + (b.ndc_y - a.ndc_y) * t,
        a.height_frac + (b.height_frac - a.height_frac) * t,
    )


def check_segment(log: ProbeLog, a: KeyframeNode, b: KeyframeNode, limit: float = DRIFT_LIMIT) -> Tuple[bool, float, int]:
    """Sample every intermediate integer frame strictly between a and b, linearly interpolate the WORLD
    position by frame-fraction, and project through THAT frame's own real camera. Returns
    (all_within_limit, worst_abs_ndc_component, worst_frame)."""
    worst = 0.0
    worst_f = a.frame
    for f in range(a.frame + 1, b.frame):
        t = (f - a.frame) / (b.frame - a.frame)
        wp = tuple(a.world[i] + (b.world[i] - a.world[i]) * t for i in range(3))
        nx, ny, _, _ = project_world_to_ndc(log.view(f), log.proj(f), wp)
        m = max(abs(nx), abs(ny))
        if m > worst:
            worst, worst_f = m, f
    return worst <= limit, worst, worst_f


def solve_path(log: ProbeLog, a: KeyframeNode, b: KeyframeNode, depth: int = 0) -> List[KeyframeNode]:
    """Recursively bisect [a, b] until every resulting sub-segment's real-camera drift stays within
    DRIFT_LIMIT (or the bisection bottoms out at adjacent frames / MAX_BISECT_DEPTH). Returns the list of
    KeyframeNodes strictly needed AFTER a, ending with b itself."""
    ok, worst, _ = check_segment(log, a, b)
    if ok or depth >= MAX_BISECT_DEPTH or b.frame - a.frame <= 1:
        return [b]
    mid_f = (a.frame + b.frame) // 2
    ndc_x, ndc_y, hf = _interp_intent(a, b, mid_f)
    mid = make_node(log, mid_f, ndc_x, ndc_y, hf, "(auto -- drift insert)")
    left = solve_path(log, a, mid, depth + 1)
    right = solve_path(log, left[-1] if left else a, b, depth + 1)
    return left + right


def build_flight(log: ProbeLog) -> List[KeyframeNode]:
    entrance = make_node(log, 0, *ENTRANCE_NDC, "entrance origin (off-frame edge, swooping in)")
    nodes: List[KeyframeNode] = [entrance]
    cur = entrance
    for wp in BEATS:
        target = make_node(log, wp.frame, wp.ndc_x, wp.ndc_y, wp.height_frac, wp.label)
        path = solve_path(log, cur, target)
        nodes.extend(path)
        cur = path[-1]
    # yaw: compute per node from that node's own camera, then unwrap the whole sequence for continuity
    raw_yaws = [broadside_yaw_deg(log.view(n.frame)) for n in nodes]
    yaws = _unwrap_deg(raw_yaws)
    return [n._replace(yaw_deg=y) for n, y in zip(nodes, yaws)]


# --------------------------------------------------------------------------- camera census (module docstring evidence)
def camera_eye_census(log: ProbeLog, jump_threshold: float = 2000.0) -> List[Tuple[int, int, float]]:
    frames = sorted(log._view_rows.keys())
    prev = None
    prev_f = None
    cuts = []
    for f in frames:
        V = log.view(f)
        R, t = V[:3, :3], V[:3, 3]
        c = -R.T @ t
        if prev is not None:
            j = float(np.linalg.norm(c - prev))
            if j > jump_threshold:
                cuts.append((prev_f, f, j))
        prev, prev_f = c, f
    return cuts


# --------------------------------------------------------------------------- reporting
def _fmt_world(p) -> str:
    return f"({p[0]:8.1f}, {p[1]:8.1f}, {p[2]:9.1f})"


def print_report(log: ProbeLog) -> List[KeyframeNode]:
    cuts = camera_eye_census(log)
    print(f"=== camera hard-cut census (single-frame eye jump > 2000 units): {len(cuts)} cuts ===")
    for pf, f, j in cuts[:15]:
        print(f"  f{pf} -> f{f}  jump={j:.0f}")
    if len(cuts) > 15:
        print(f"  ... ({len(cuts) - 15} more)")
    print()

    nodes = build_flight(log)
    print(f"=== THE FLIGHT v7 -- IN-FRAME BY CONSTRUCTION ({len(nodes)} keyframes, frames "
          f"{nodes[0].frame}..{nodes[-1].frame}; {len(BEATS) + 1} authored beats + "
          f"{len(nodes) - len(BEATS) - 1} adaptive drift-inserts) ===")
    print(f"THOMAS_HEIGHT_SCALED = {THOMAS_HEIGHT_SCALED:.1f} (raw {THOMAS_RAW_HEIGHT} x scale {THOMAS_SCALE})")
    print()
    print(f"{'frame':>5} | {'ndc_x':>7} {'ndc_y':>7} | {'h%':>5} | {'depth':>9} | {'yaw':>7} | world (X,Y,Z)     | label")
    for n in nodes:
        depth = -1  # recompute for display
        view, proj = log.view(n.frame), log.proj(n.frame)
        depth = solve_height_depth(proj, n.height_frac)
        print(f"{n.frame:5d} | {n.ndc_x:+7.2f} {n.ndc_y:+7.2f} | {n.height_frac*100:4.0f}% | "
              f"{depth:9.1f} | {n.yaw_deg:+7.1f} | {_fmt_world(n.world)} | {n.label}")
    print()

    print("=== FINAL DRIFT VERIFICATION (every consecutive pair, should be 100% within DRIFT_LIMIT) ===")
    n_ok = 0
    worst_overall = 0.0
    for i in range(len(nodes) - 1):
        a, b = nodes[i], nodes[i + 1]
        ok, worst, wf = check_segment(log, a, b)
        n_ok += int(ok)
        worst_overall = max(worst_overall, worst)
        flag = "OK" if ok else "FAIL"
        if not ok:
            print(f"  seg f{a.frame:<4d}->f{b.frame:<4d}  worst@f{wf:<4d} |ndc|={worst:.2f}  {flag}")
    print(f"  {n_ok}/{len(nodes)-1} segments within DRIFT_LIMIT={DRIFT_LIMIT}; worst |ndc| anywhere = {worst_overall:.3f}")
    print()

    print("=== KEYFRAMES_V7 -- paste into build_thomas.py ===")
    for n in nodes:
        x, y, z = round(n.world[0]), round(n.world[1]), round(n.world[2])
        print(f"    ({n.frame:4d}, ({x:6d}, {y:6d}, {z:7d}), {n.yaw_deg:+7.2f}),  # {n.label}")
    return nodes


def main() -> int:
    log = ProbeLog.parse(DEFAULT_LOG)
    print_report(log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
