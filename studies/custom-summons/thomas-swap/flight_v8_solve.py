"""flight_v8_solve.py -- THE FLIGHT v8 (2026-07-23): HYBRID -- real entrance + constructed reign.

v7 (flight_v7_solve.py) was PURE construction (in-frame by NDC back-projection); the user found it
"in frame, doesn't really look good, some parts missing." The s52 ROOT probe (PROBE.md sec 10) then
captured Bahamut's REAL per-frame world transform, and analysis (root_reproject.py + the camera-aim
diagnostic) established:

  - The creature is actively posed (LIVE ROOT, changing every frame) for frames 82-301 -- ~43% of the
    cast -- then PARKS for the fire column. That ~43% matches the user's own recollection almost exactly
    ("~40%", a clean 4-phase structure they described from watching it: fly-down, swoop-by, float+charge
    with the camera ON him, then the camera moves OFF to follow the fire column into the enemies).
  - BUT only the SWOOP-IN (82-107) has a clean, camera-VALIDATED ROOT->screen mapping: at those frames
    the camera is aimed straight at the creature (fwd.dir ~ +0.97) and it projects on-screen coherently.
    From frame 108 on, the summon-model ROOT diverges hard from where the visible creature is drawn (at
    the charge it sits ~40,000 units below/behind the camera) -- the FINDINGS sec 4 puzzle: during the
    reign the visible creature is on a different draw path (or carries a large draw-time world offset the
    probe can't see). So the ROOT is NOT a trustworthy placement source past ~107.

v8 therefore:
  * ENTRANCE (82-107): uses the REAL ROOT world positions -- Thomas traces Bahamut's actual descent,
    growing naturally as he swoops close (measured, camera-validated). A constructed lead-in brings him
    in from off-frame ("flying down" from above).
  * SWOOP-BY + FLOAT/CHARGE (~120-300): CONSTRUCTED via v7's proven NDC back-projection to the user's
    4-phase spec -- a visible swoop-by pass, then a BIG center-stage float held through the charge (the
    beat the user wants Thomas present for). Drift-guaranteed in-frame.
  * FIRE COLUMN (~310-580): the camera moves OFF him to the enemies, so Thomas HOLDS his world position
    and drifts out of frame naturally as the camera pans away (faithful "camera leaves him"; deliberately
    NOT drift-guaranteed -- he is meant to exit).

Same projection math as v7 (imports matrix_solve + flight_v7_solve helpers -- no reimplementation).

Run standalone: py flight_v8_solve.py -> prints the pasteable KEYFRAMES_V8 table build_thomas.py bakes.
THOMAS_SCALE must stay in sync with build_thomas.py + flight_v7_solve.py (all 265).
"""
from __future__ import annotations

from typing import List

from matrix_solve import ProbeLog, project_world_to_ndc, DEFAULT_LOG
import flight_v7_solve as v7
from flight_v7_solve import (
    KeyframeNode, make_node, solve_path, check_segment, broadside_yaw_deg,
    _unwrap_deg, solve_height_depth, THOMAS_HEIGHT_SCALED, THOMAS_SCALE, DRIFT_LIMIT,
)
from root_reproject import RootTrack

# The camera-validated real swoop-in window (root_reproject.py: on-screen, camera aimed at the creature).
# Trimmed to end at 100, not the full 107: the real creature swoops so CLOSE by 107 that Thomas's own
# height fills 167% of frame (a wall of train). 82-100 is the clean "descend + approach, growing 18%->65%"
# arc; the constructed swoop-by picks up from there before the overflow (push this back toward 107 for a
# deliberately overwhelming close pass).
ENTRANCE_REAL = (82, 100)
ENTRANCE_STEP = 3                      # sample the real ROOT every 3 frames -> dense, low inter-key drift
LEADIN_NDC = (0.12, 1.15, 0.34)        # start just above frame, descending in ("flying down" from above)

# Constructed beats AFTER the real entrance (frame, ndc_x, ndc_y, height_frac, label) -- the user's 4-phase
# narrative. Phase 2 = a visible swoop-by pass; phase 3 = settle center + BIG float held through the charge.
BEATS_AFTER = (
    v7.Waypoint(130,  0.45, -0.08, 0.52, "swoop-by (sweep across, right)"),
    v7.Waypoint(160, -0.38,  0.02, 0.54, "swoop-by (sweep across, left)"),
    v7.Waypoint(190,  0.00,  0.05, 0.62, "settle center -- float begins"),
    v7.Waypoint(225,  0.06,  0.16, 0.66, "float + charge -- BIG"),
    v7.Waypoint(265, -0.05,  0.10, 0.66, "float + charge -- stay BIG"),
    v7.Waypoint(300,  0.00,  0.12, 0.64, "charge hold -- present, camera still on him"),
)
# Phase 4: the camera pans to the fire column. Thomas holds the phase-3 world position; the moving camera
# carries him out of frame. Keyframes are the SAME world point re-projected per frame (so the piece is a
# world-space HOLD, and he exits by camera motion alone). Deliberately not drift-checked -- he leaves frame.
PHASE4_FRAMES = (340, 430, 510, 580)


def real_node(log: ProbeLog, roots: RootTrack, frame: int) -> KeyframeNode:
    """A keyframe at the creature's MEASURED world position for `frame` (camera-validated entrance window).
    ndc/height are computed from the real position so the node is fully specified like a make_node output
    (lets solve_path/interp treat it uniformly if ever bisected)."""
    world = roots.pos[frame]
    view, proj = log.view(frame), log.proj(frame)
    nx, ny, _, vz = project_world_to_ndc(view, proj, world)
    height_frac = (proj[1, 1] * THOMAS_HEIGHT_SCALED / (2.0 * -vz)) if vz < 0 else 0.60
    return KeyframeNode(frame, nx, ny, height_frac, world, "real entrance (measured swoop-in)")


def build_flight(log: ProbeLog, roots: RootTrack) -> List[KeyframeNode]:
    lead = make_node(log, 0, *LEADIN_NDC, "lead-in (off-frame top, flying down)")
    nodes: List[KeyframeNode] = [lead]

    # --- ENTRANCE: real ROOT, dense (every ENTRANCE_STEP frames). The lead-in -> first-real segment is
    #     the off-frame entrance (no drift guarantee); the real nodes themselves are dense enough that
    #     linear world interpolation between them stays on the real path.
    rf = list(range(ENTRANCE_REAL[0], ENTRANCE_REAL[1] + 1, ENTRANCE_STEP))
    if rf[-1] != ENTRANCE_REAL[1]:
        rf.append(ENTRANCE_REAL[1])
    rf = [f for f in rf if f in roots.pos and log.has_camera(f)]
    for f in rf:
        nodes.append(real_node(log, roots, f))

    # --- SWOOP-BY + FLOAT/CHARGE: constructed, drift-guaranteed in-frame (v7 machinery).
    for wp in BEATS_AFTER:
        target = make_node(log, wp.frame, wp.ndc_x, wp.ndc_y, wp.height_frac, wp.label)
        nodes.extend(solve_path(log, nodes[-1], target))

    # --- FIRE COLUMN: hold the phase-3 world; the moving camera carries Thomas out of frame.
    hold_world = nodes[-1].world
    hold_hf = nodes[-1].height_frac
    for f in PHASE4_FRAMES:
        nx, ny, _, _ = project_world_to_ndc(log.view(f), log.proj(f), hold_world)
        nodes.append(KeyframeNode(f, nx, ny, hold_hf, hold_world,
                                  "fire column (camera off him -- world hold, exits by camera pan)"))

    # yaw: broadside to each node's own camera, unwrapped for continuity (Thomas presents his side/"1" panel)
    yaws = _unwrap_deg([broadside_yaw_deg(log.view(n.frame)) for n in nodes])
    return [n._replace(yaw_deg=y) for n, y in zip(nodes, yaws)]


def _fmt_world(p) -> str:
    return f"({p[0]:8.1f}, {p[1]:8.1f}, {p[2]:9.1f})"


def print_report(log: ProbeLog, roots: RootTrack) -> List[KeyframeNode]:
    nodes = build_flight(log, roots)
    n_real = sum(1 for n in nodes if n.label.startswith("real entrance"))
    n_p4 = len(PHASE4_FRAMES)
    print(f"=== THE FLIGHT v8 -- HYBRID ({len(nodes)} keyframes, frames {nodes[0].frame}..{nodes[-1].frame}) ===")
    print(f"  entrance: 1 lead-in + {n_real} MEASURED real-ROOT nodes ({ENTRANCE_REAL[0]}-{ENTRANCE_REAL[1]})")
    print(f"  reign:    {len(BEATS_AFTER)} authored beats + adaptive drift-inserts (constructed, in-frame)")
    print(f"  fire col: {n_p4} world-hold nodes (camera pans away -- Thomas exits)")
    print(f"  THOMAS_HEIGHT_SCALED = {THOMAS_HEIGHT_SCALED:.1f} (scale {THOMAS_SCALE})")
    print()
    print(f"{'frame':>5} | {'ndc_x':>7} {'ndc_y':>7} | {'h%':>5} | {'yaw':>7} | world (X,Y,Z)          | label")
    for n in nodes:
        print(f"{n.frame:5d} | {n.ndc_x:+7.2f} {n.ndc_y:+7.2f} | {n.height_frac*100:4.0f}% | "
              f"{n.yaw_deg:+7.1f} | {_fmt_world(n.world)} | {n.label}")
    print()

    # drift verification -- report all, but the entrance lead-in and the phase-4 holds are EXPECTED off-frame
    print("=== DRIFT (constructed reign segments should be within DRIFT_LIMIT; entrance/fire-col exempt) ===")
    entrance_end = nodes[1 + n_real].frame if len(nodes) > 1 + n_real else nodes[-1].frame
    fire_start = PHASE4_FRAMES[0]
    worst_reign = 0.0
    n_reign = 0
    n_reign_ok = 0
    for i in range(len(nodes) - 1):
        a, b = nodes[i], nodes[i + 1]
        ok, worst, wf = check_segment(log, a, b)
        exempt = (a.frame < ENTRANCE_REAL[0]) or (b.frame >= fire_start)
        if not exempt:
            n_reign += 1
            n_reign_ok += int(ok)
            worst_reign = max(worst_reign, worst)
            if not ok:
                print(f"  reign seg f{a.frame:<4d}->f{b.frame:<4d}  worst@f{wf:<4d} |ndc|={worst:.2f}  FAIL")
    print(f"  reign: {n_reign_ok}/{n_reign} segments within DRIFT_LIMIT={DRIFT_LIMIT}; worst |ndc| = {worst_reign:.3f}")
    print("  (entrance lead-in and fire-column holds are intentionally allowed off-frame -- fly-in from")
    print("   off-frame, and the camera pans away from Thomas onto the fire column.)")
    print()

    print("=== KEYFRAMES_V8 -- paste into build_thomas.py (rename KEYFRAMES_V7 -> KEYFRAMES_V8) ===")
    for n in nodes:
        x, y, z = round(n.world[0]), round(n.world[1]), round(n.world[2])
        print(f"    ({n.frame:4d}, ({x:7d}, {y:7d}, {z:8d}), {n.yaw_deg:+7.2f}),  # {n.label}")
    return nodes


def main() -> int:
    log = ProbeLog.parse(DEFAULT_LOG)
    roots = RootTrack.parse(DEFAULT_LOG)
    print_report(log, roots)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
