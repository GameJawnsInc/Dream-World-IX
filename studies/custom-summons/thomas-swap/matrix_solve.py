"""matrix_solve.py -- THE FINAL SOLVE (2026-07-22): reconstruct Bahamut's REAL per-frame SCREEN
trajectory from the s50 probe's logged per-frame render matrices, so Thomas can *track* it -- be
wherever Bahamut was, INCLUDING the deliberate off-screen swoop-ins and camera-follows-blast beats.

=== WHY THIS SUPERSEDES viewspace_place.py / THE FLIGHT v4 ===

FLIGHT v4 (``viewspace_place.py``) was built on the premise that the render camera is STATIC: the s48
CAM hook logged ``Camera`` ``transform.position``/``.eulerAngles`` as identical across a whole cast, and
the module concluded the per-frame render matrix was an unrecoverable native scratch buffer. **The s50
probe overturns that.** It logs, per frame, the actual ``camera.worldToCameraMatrix`` (VIEW rows) and
``camera.projectionMatrix`` (PROJ rows) -- the very matrices ``SFX.UpdateCamera()`` assigns directly at
``SFX.cs:1603-1604`` -- and they are anything but static:

  * The logged ``CAM`` Transform IS static (``-2200,2900,4600`` / euler ``25,155,0`` all-frames) -- but
    it is NOT the render camera. It's the Battle Camera's own Transform, which nothing ever writes
    per-frame; the render matrix is overridden wholesale instead. viewspace_place.py's own
    ``render_camera_confirmed`` docstring flagged exactly this ambiguity ("the log cannot distinguish
    'the camera never moves' from 'nothing ever updates a Transform that was never the eye'") -- the s50
    VIEW rows RESOLVE it: it's the second one. The Transform is a decoy; the VIEW matrix is the eye.
  * VIEW moves dramatically frame to frame (frame 82 vs 200 vs 400 are entirely different orientations --
    the camera pans/orbits the whole cast).
  * PROJ *zooms*: its ``[1][1]`` entry (vertical focal term) ranges ~2.33..4.65 across the cast, i.e. the
    real vertical FOV sweeps ~47deg..24deg. There is no single "assumed FOV"; the cinematic zooms.

CONSEQUENCE -- the placement problem collapses. Thomas is rendered by that SAME per-frame camera
(``ef227``'s baked native camera track replays byte-identically every cast). So we do NOT need to model
the camera at all to place him: **put Thomas at Bahamut's actual measured world position each frame, and
the real per-frame VIEW+PROJ reproduces Bahamut's exact screen position -- pan, zoom, off-screen swoop
and all -- for free.** "Faithful = Thomas is wherever Bahamut was" is thus *literal*, not stylized. The
projection math below exists to (a) COMPUTE and VERIFY that screen trajectory (prove the swoops/off-frame
beats are real, not guesses), and (b) provide the general forward/inverse tools the mission specified.

=== BAHAMUT'S WORLD POSITION FROM POOL-POLLUTED BOUNDS ===

His 7 body-mesh keys draw at ``Matrix4x4.identity`` (object space == world space), but each key's logged
``mesh.bounds`` is POOL-POLLUTED: the SFX vertex pool holds unused verts at/near world origin, so the AABB
is stretched from the real body toward ``(0,0,0)``. The established heuristic (PROBE.md round 1,
independently re-validated there):

  * X, Y  = bounds CENTER (``cx``/``cy``) -- the body sits near origin on these axes (|X|,|Y| < ~512,
    comparable to the pool's own spread), so the midpoint is the better estimate; the far corner would
    chase silhouette extremities.
  * Z     = the FAR CORNER (``cz +/- ez``, whichever side is farther from 0) -- the body sits FAR from
    origin in Z (thousands of units), the pool sits at Z=0, so the AABB spans [Z_body, 0], center=Z_body/2
    and far-corner=Z_body recovers true depth. (Empirically ``ez ~= |cz|`` on every body row, confirming
    the pool-at-origin model: far-corner == ``2*cz``.)
  * MEDIAN across the (up to) 7 keys present that frame, for robustness against any single key's pooling.

A light temporal windowed-median (``body_world_smoothed``) further suppresses single-frame pooling spikes
(e.g. the frame where the AABB momentarily balloons symmetric around origin and drags ``cy`` to ~0).

DEPTH IS THE ONE GENUINELY-AMBIGUOUS AXIS (recorded finding, retune knob). Far-corner Z is the
mission-specified / PROBE-established choice and is what this module and the deployed build use; it reads
the body's *deepest* vert (== ``2*cz`` under the pool-at-origin model), which for a compact body cluster is
close to its center. The shallower alternative is the raw AABB CENTER ``cz`` (== half that depth). They
differ by ~2x, which materially changes apparent size and screen position under the moving camera. As a
diagnostic: projecting Bahamut's own body positions back through the real per-frame camera lands only
~8/324 frames strictly on-screen with far-corner Z (~50/324 with center Z), and only ~half the cast has
the body in FRONT of the camera at all -- i.e. his body is genuinely off-screen/behind for most of the
cast because the camera follows the blast/effect, not the creature (exactly the deliberate off-screen
behavior; NOT a reason to force him on-screen). If a playtest video shows the tracked Thomas reading as
too deep / too small, switch the Z estimate from far-corner to center in ``body_world`` -- a one-line
retune -- and rebuild.

=== THE MATRICES (verified against Unity conventions + PsxCamera.cs this round) ===

VIEW = ``worldToCameraMatrix`` (world -> camera/view space; camera looks down -Z; last row 0,0,0,1).
PROJ = ``camera.projectionMatrix`` raw (GL convention as logged; maps view -> clip). Both logged row-major
(m00,m01,m02,m03, m10,...). Per frame the log carries several near-identical copies (the native plugin
sub-steps within one ``SFX.frameIndex``); we mean them per frame.

  clip = PROJ @ VIEW @ [world, 1]
  ndc  = clip.xyz / clip.w                    (w == -view.z for this PROJ: its row3 is (0,0,-1,0))
  on-screen iff |ndc.x| < 1 and |ndc.y| < 1 and view.z < 0 (in front)

PROJ is an OFF-CENTER frustum: ``[0][2]==0`` (horizontal centered) but ``[1][2]==0.0909`` (vertical
off-center, == (top+bottom)/(top-bottom) for the cited top=120/bottom=-100 frustum). ``world_from_ndc``
inverts it generally (solves the 2x2 view-XY system from the exact PROJ entries + inverts VIEW), so the
off-center term is handled, not assumed away.

Everything here is a standalone, importable, unit-testable library; ``py matrix_solve.py`` runs a
self-test (round-trip + the full trajectory + screen-path analysis + a pasteable keyframe table).
"""
from __future__ import annotations

import argparse
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# --------------------------------------------------------------------------- constants
# The 7 confirmed CREATURE/BODY mesh keys (PROBE.md round 1; hex, no 0x -- the MESH keyHex column form).
BODY_KEYS: Tuple[str, ...] = (
    "0033B990", "0033B9D0", "0035BAD0", "0035BA90", "0034BA10", "0034BA50", "0097BD02",
)

DEFAULT_LOG = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\sfxmeshprobe.log"
)

BAHAMUT_EFFECT_ID = 227


# --------------------------------------------------------------------------- parsing
class ProbeLog:
    """Parsed s50 probe log: per-frame mean VIEW / mean PROJ 4x4, and per-frame per-key mesh bounds."""

    def __init__(self) -> None:
        # frame -> list of 4x4 (row-major) arrays, later meaned
        self._view_rows: Dict[int, List[np.ndarray]] = {}
        self._proj_rows: Dict[int, List[np.ndarray]] = {}
        # frame -> key -> list of (cx,cy,cz,ex,ey,ez)
        self._body: Dict[int, Dict[str, List[Tuple[float, ...]]]] = {}
        self._view_cache: Dict[int, np.ndarray] = {}
        self._proj_cache: Dict[int, np.ndarray] = {}
        self._view_frames_sorted: Optional[np.ndarray] = None
        self._proj_frames_sorted: Optional[np.ndarray] = None

    @classmethod
    def parse(cls, path: Path = DEFAULT_LOG) -> "ProbeLog":
        if not Path(path).is_file():
            raise FileNotFoundError(
                f"probe log not found: {path}\n"
                "Arm the s50 probe ([SfxProbe] Enabled=1 in Memoria.ini), relaunch, run "
                "build_thomas.py --calibrate, cast Iviv -> Spark -> Bahamut Cinema, let it play through."
            )
        self = cls()
        body_key_set = set(BODY_KEYS)
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line or line[0] == "#":
                    continue
                parts = line.rstrip("\n").split(",")
                tag = parts[0]
                if tag == "VIEW":
                    # VIEW,frame,m00..m33 (16 floats)
                    frame = int(parts[1])
                    vals = np.array([float(x) for x in parts[2:18]], dtype=np.float64)
                    self._view_rows.setdefault(frame, []).append(vals.reshape(4, 4))
                elif tag == "PROJ":
                    frame = int(parts[1])
                    vals = np.array([float(x) for x in parts[2:18]], dtype=np.float64)
                    self._proj_rows.setdefault(frame, []).append(vals.reshape(4, 4))
                elif tag == "MESH":
                    # MESH,effectId,frame,index,keyHex,vertCount,triCount,cx,cy,cz,ex,ey,ez
                    key = parts[4]
                    if key not in body_key_set:
                        continue
                    frame = int(parts[2])
                    cx, cy, cz, ex, ey, ez = (float(x) for x in parts[7:13])
                    self._body.setdefault(frame, {}).setdefault(key, []).append((cx, cy, cz, ex, ey, ez))
        return self

    # ---- camera matrices -------------------------------------------------
    def _nearest(self, frames_sorted: np.ndarray, frame: int) -> int:
        i = int(np.searchsorted(frames_sorted, frame))
        if i <= 0:
            return int(frames_sorted[0])
        if i >= len(frames_sorted):
            return int(frames_sorted[-1])
        lo, hi = frames_sorted[i - 1], frames_sorted[i]
        return int(lo if (frame - lo) <= (hi - frame) else hi)

    def view(self, frame: int) -> np.ndarray:
        """Mean VIEW (worldToCameraMatrix) 4x4 for ``frame`` (nearest logged frame if exact absent)."""
        if self._view_frames_sorted is None:
            self._view_frames_sorted = np.array(sorted(self._view_rows.keys()))
        if frame not in self._view_rows:
            frame = self._nearest(self._view_frames_sorted, frame)
        if frame not in self._view_cache:
            self._view_cache[frame] = np.mean(np.stack(self._view_rows[frame]), axis=0)
        return self._view_cache[frame]

    def proj(self, frame: int) -> np.ndarray:
        """Mean PROJ (projectionMatrix) 4x4 for ``frame`` (nearest logged frame if exact absent)."""
        if self._proj_frames_sorted is None:
            self._proj_frames_sorted = np.array(sorted(self._proj_rows.keys()))
        if frame not in self._proj_rows:
            frame = self._nearest(self._proj_frames_sorted, frame)
        if frame not in self._proj_cache:
            self._proj_cache[frame] = np.mean(np.stack(self._proj_rows[frame]), axis=0)
        return self._proj_cache[frame]

    def has_camera(self, frame: int) -> bool:
        return frame in self._view_rows and frame in self._proj_rows

    # ---- Bahamut body position ------------------------------------------
    @staticmethod
    def _far_corner_z(cz: float, ez: float) -> float:
        a, b = cz + ez, cz - ez
        return a if abs(a) >= abs(b) else b

    # THE DEGENERATE-POOL-ROW SIGNATURE (found adversarially, 2026-07-22): a body key with genuinely NO
    # active geometry that frame doesn't drop out of the log -- it reports the SFX vertex pool's own
    # fixed-size unused-slot bounding box, which lands at this EXACT (cx,cy,ex,ey) every single time
    # (verified across every one of the 39 distinct keys in the whole cast, not just the 7 body keys):
    # cx=34.5, cy=-0.5, ex=1023.5, ey=1023.5 (a symmetric ~2047x2047 box centered near the origin -- the
    # pool's own fixed capacity, unrelated to Bahamut's silhouette). It is NOT rare: 323/324 (99.7%) of
    # this cast's logged body frames have >=1 of the 7 keys in this exact state, several frames have
    # multiple simultaneously (e.g. f150, f152 sub-steps). The prior body_world() folded these rows into
    # the per-frame median unfiltered -- harmless for X/Y when <4 of 7 keys are degenerate (median is
    # 3-outlier-robust), but the row's OWN far-corner Z is *also* included in the Z median even though it
    # reflects the pool box's depth, not the creature's -- a real, measurable contamination source (see
    # matrix_solve.py's adversarial-review notes / the thomas-swap README "known caveats").
    _POOL_CX = 34.5
    _POOL_CY = -0.5
    _POOL_EX = 1023.5
    _POOL_EY = 1023.5
    _POOL_EPS = 0.6

    @classmethod
    def _is_pool_row(cls, cx: float, cy: float, ex: float, ey: float) -> bool:
        return (
            abs(cx - cls._POOL_CX) < cls._POOL_EPS
            and abs(cy - cls._POOL_CY) < cls._POOL_EPS
            and abs(ex - cls._POOL_EX) < cls._POOL_EPS
            and abs(ey - cls._POOL_EY) < cls._POOL_EPS
        )

    def body_world(self, frame: int) -> Optional[Tuple[float, float, float]]:
        """Bahamut's heuristic world position at ``frame``: median across the body keys present that
        frame of (X=cx, Y=cy, Z=far-corner), EXCLUDING any key whose sub-step rows are all the degenerate
        pool-default box (``_is_pool_row`` -- see its docstring). ``None`` if no body key has real content
        that frame (either none logged, or every logged key that frame is pool-degenerate)."""
        keys = self._body.get(frame)
        if not keys:
            return None
        xs: List[float] = []
        ys: List[float] = []
        zs: List[float] = []
        for key, rows in keys.items():
            real_rows = [r for r in rows if not self._is_pool_row(r[0], r[1], r[3], r[4])]
            if not real_rows:
                continue  # this key contributed nothing but the pool box this frame -- skip it entirely
            # reduce this key's sub-step rows to one representative (median of each component)
            cx = statistics.median(r[0] for r in real_rows)
            cy = statistics.median(r[1] for r in real_rows)
            # far-corner z uses the row with the largest |far corner|, but median of per-row far corners
            # is steadier against a single spurious sub-step
            zf = statistics.median(self._far_corner_z(r[2], r[5]) for r in real_rows)
            xs.append(cx)
            ys.append(cy)
            zs.append(zf)
        if not xs:
            return None
        return (statistics.median(xs), statistics.median(ys), statistics.median(zs))

    def body_frames(self) -> List[int]:
        return sorted(self._body.keys())

    # ---- frame-based projection API (the mission's requested signatures) --
    def project_world_to_ndc(
        self, frame: int, world_pt: Tuple[float, float, float]
    ) -> Tuple[float, float, float, float]:
        """Frame-based forward projection -- ``(ndc_x, ndc_y, ndc_z, view_z)`` for ``world_pt`` under this
        frame's real VIEW+PROJ. Thin wrapper over the module-level :func:`project_world_to_ndc`."""
        return project_world_to_ndc(self.view(frame), self.proj(frame), world_pt)

    def world_from_ndc(
        self, frame: int, ndc_x: float, ndc_y: float, view_z: float
    ) -> Tuple[float, float, float]:
        """Frame-based inverse -- the world point that projects to ``(ndc_x, ndc_y)`` at camera-space depth
        ``view_z`` (negative in front) under this frame's real VIEW+PROJ. Thin wrapper over the module-
        level :func:`world_from_ndc`."""
        return world_from_ndc(self.view(frame), self.proj(frame), ndc_x, ndc_y, view_z)

    def body_world_smoothed(
        self, frame: int, window: int = 6, max_window: int = 60
    ) -> Optional[Tuple[float, float, float]]:
        """Windowed component-wise median of ``body_world`` over ``[frame-window, frame+window]`` --
        suppresses single-frame pooling spikes. Now that ``body_world`` (post pool-row filter, see
        ``_is_pool_row``) can legitimately return ``None`` for a frame where EVERY one of the 7 body keys
        was pool-degenerate that frame -- a real, adversarially-found condition, not hypothetical: frames
        166, 177, and the entire 411-417 tail (the deployed manifest's own LAST tracked point) have ZERO
        real body-key content once the pool rows are excluded -- a tight ``window`` can come up completely
        empty. Rather than silently return a stale/contaminated estimate (the pre-fix behavior) or None
        (which would leave a keyframe-table generator with a hole), progressively DOUBLE the window up to
        ``max_window`` until at least one real sample is found; ``None`` only if the whole ``+/-max_window``
        span around ``frame`` has no real body-key content at all."""
        w = window
        while True:
            xs: List[float] = []
            ys: List[float] = []
            zs: List[float] = []
            for g in range(frame - w, frame + w + 1):
                p = self.body_world(g)
                if p is not None:
                    xs.append(p[0])
                    ys.append(p[1])
                    zs.append(p[2])
            if xs:
                return (statistics.median(xs), statistics.median(ys), statistics.median(zs))
            if w >= max_window:
                return None
            w = min(w * 2, max_window)


# --------------------------------------------------------------------------- projection
def project_world_to_ndc(
    view: np.ndarray, proj: np.ndarray, world_pt: Tuple[float, float, float]
) -> Tuple[float, float, float, float]:
    """Forward project a world point through this frame's VIEW then PROJ.

    Returns ``(ndc_x, ndc_y, ndc_z, view_z)`` where ndc is the clip-space point after perspective
    divide (Unity/GL convention, y-up, each axis in [-1,1] when on screen) and ``view_z`` is the
    camera-space Z coordinate (NEGATIVE for points in front of the camera). On-screen iff
    ``abs(ndc_x) < 1 and abs(ndc_y) < 1 and view_z < 0``."""
    w = np.array([world_pt[0], world_pt[1], world_pt[2], 1.0], dtype=np.float64)
    v = view @ w
    clip = proj @ v
    cw = clip[3]
    if cw == 0.0:
        cw = 1e-9
    return (clip[0] / cw, clip[1] / cw, clip[2] / cw, v[2])


def world_from_ndc(
    view: np.ndarray, proj: np.ndarray, ndc_x: float, ndc_y: float, view_z: float
) -> Tuple[float, float, float]:
    """Inverse of :func:`project_world_to_ndc`: given a target screen position ``(ndc_x, ndc_y)`` and a
    camera-space depth ``view_z`` (the same signed camera-space Z the forward call returns -- NEGATIVE in
    front; ``depth_in_front = -view_z``), recover the world point that projects there under this frame's
    VIEW+PROJ.

    Handles the off-center frustum generally: it solves the 2x2 linear system for the view-space X/Y from
    the exact PROJ entries (no assumption that the off-center terms are zero), using ``clip.w`` derived
    from PROJ's own row 3, then maps the view point back to world with ``inv(VIEW)``.

    Round-trips :func:`project_world_to_ndc` to float precision (asserted in ``self_test``)."""
    # clip.w = proj[3] . (vx, vy, view_z, 1); for this PROJ proj[3] = (0,0,-1,0) so w = -view_z, but
    # solve it generally: w depends on vx,vy only if proj[3,0]/[3,1] != 0 (not the case here -- guarded).
    if abs(proj[3, 0]) > 1e-12 or abs(proj[3, 1]) > 1e-12:
        raise NotImplementedError(
            "PROJ row 3 has nonzero X/Y terms; clip.w depends on the unknown view X/Y -- the simple "
            "depth-parameterized inverse does not apply to this (non-standard) projection."
        )
    w = proj[3, 2] * view_z + proj[3, 3]
    # clip.x = proj[0,0]*vx + proj[0,1]*vy + proj[0,2]*vz + proj[0,3] = ndc_x * w
    # clip.y = proj[1,0]*vx + proj[1,1]*vy + proj[1,2]*vz + proj[1,3] = ndc_y * w
    a = np.array([[proj[0, 0], proj[0, 1]], [proj[1, 0], proj[1, 1]]], dtype=np.float64)
    rhs = np.array(
        [
            ndc_x * w - proj[0, 2] * view_z - proj[0, 3],
            ndc_y * w - proj[1, 2] * view_z - proj[1, 3],
        ],
        dtype=np.float64,
    )
    vx, vy = np.linalg.solve(a, rhs)
    view_pt = np.array([vx, vy, view_z, 1.0], dtype=np.float64)
    world = np.linalg.inv(view) @ view_pt
    return (float(world[0]), float(world[1]), float(world[2]))


# --------------------------------------------------------------------------- trajectory
def is_on_screen(ndc_x: float, ndc_y: float, view_z: float) -> bool:
    return abs(ndc_x) < 1.0 and abs(ndc_y) < 1.0 and view_z < 0.0


def screen_trajectory(log: ProbeLog, smoothed: bool = True, window: int = 6) -> Dict[int, dict]:
    """For every frame Bahamut's body is on screen: his heuristic world pos, its projection to
    ``(ndc_x, ndc_y)`` under that frame's real VIEW+PROJ, ``view_z``, and the on-screen flag."""
    out: Dict[int, dict] = {}
    for frame in log.body_frames():
        pos = log.body_world_smoothed(frame, window) if smoothed else log.body_world(frame)
        if pos is None or not log.has_camera(frame):
            continue
        ndc_x, ndc_y, ndc_z, view_z = project_world_to_ndc(log.view(frame), log.proj(frame), pos)
        out[frame] = {
            "world": pos,
            "ndc": (ndc_x, ndc_y),
            "view_z": view_z,
            "on_screen": is_on_screen(ndc_x, ndc_y, view_z),
        }
    return out


def sample_keyframes(
    log: ProbeLog, start: int, end: int, step: int, window: int = 6
) -> List[Tuple[int, Tuple[float, float, float]]]:
    """Windowed-median world position sampled every ``step`` frames over ``[start, end]`` (``end`` always
    included). The world trajectory Thomas's Movement pieces reproduce piecewise-linearly."""
    frames = list(range(start, end + 1, step))
    if frames[-1] != end:
        frames.append(end)
    out: List[Tuple[int, Tuple[float, float, float]]] = []
    for f in frames:
        p = log.body_world_smoothed(f, window)
        if p is None:
            p = log.body_world(f)
        if p is not None:
            out.append((f, p))
    return out


def linear_extrapolate(
    p_far: Tuple[float, float, float],
    f_far: int,
    p_near: Tuple[float, float, float],
    f_near: int,
    to_frame: int,
) -> Tuple[float, float, float]:
    """Extrapolate the line through (f_far -> p_far, f_near -> p_near) to ``to_frame`` -- used to build the
    off-screen ENTRANCE origin (extend the earliest measured velocity backward before the body appears)
    and the EXIT destination (extend the latest velocity forward after it vanishes). These two endpoints
    have NO ground truth (the body is absent outside its 82..417 window); they are honest reasoned
    extrapolations of the real measured velocity at the edges, not measurements."""
    span = f_near - f_far
    if span == 0:
        return p_near
    t = (to_frame - f_far) / span
    return tuple(p_far[i] + (p_near[i] - p_far[i]) * t for i in range(3))  # type: ignore[return-value]


# --------------------------------------------------------------------------- self-test / CLI
def _fmt_xyz(p) -> str:
    return f"({p[0]:9.1f}, {p[1]:9.1f}, {p[2]:10.1f})"


def self_test(log_path: Path = DEFAULT_LOG, step: int = 12, window: int = 6,
              track_start: int = 82, track_end: int = 417) -> None:
    log = ProbeLog.parse(log_path)
    bframes = log.body_frames()
    print(f"parsed: {log_path}")
    print(f"body frames: {bframes[0]}..{bframes[-1]}  ({len(bframes)} distinct)")
    print()

    # 1. round-trip: project a sample body pos, then invert -- must recover the world point exactly
    print("=== round-trip project_world_to_ndc -> world_from_ndc ===")
    ok = True
    for f in (bframes[0], bframes[len(bframes) // 2], bframes[-1]):
        pos = log.body_world_smoothed(f, window)
        V, P = log.view(f), log.proj(f)
        nx, ny, nz, vz = project_world_to_ndc(V, P, pos)
        back = world_from_ndc(V, P, nx, ny, vz)
        err = max(abs(back[i] - pos[i]) for i in range(3))
        flag = "OK" if err < 1e-4 else "FAIL"
        ok = ok and err < 1e-4
        print(f"  f{f:<4d} world={_fmt_xyz(pos)} ndc=({nx:+.3f},{ny:+.3f}) view_z={vz:9.1f}  "
              f"inv-err={err:.2e} {flag}")
    print(f"  round-trip: {'PASS' if ok else 'FAIL'}")
    print()

    # 2. PROJ zoom + VIEW motion span (the FLIGHT-v4-demolishing evidence)
    print("=== camera is NOT static (the s50 headline) ===")
    m11 = [log.proj(f)[1, 1] for f in bframes if log.has_camera(f)]
    import math as _m
    vfovs = [_m.degrees(2 * _m.atan(1.0 / v)) for v in m11]
    print(f"  PROJ[1][1] (vertical focal): {min(m11):.3f}..{max(m11):.3f}"
          f"  => vertical FOV ~{max(vfovs):.1f}deg..{min(vfovs):.1f}deg (the cinematic ZOOMS)")
    # camera world position derived from VIEW = -R^T t, sampled -- shows it pans
    def cam_pos(f):
        V = log.view(f)
        R, t = V[:3, :3], V[:3, 3]
        c = -R.T @ t
        return c
    for f in (bframes[0], bframes[len(bframes)//2], bframes[-1]):
        c = cam_pos(f)
        print(f"  eye@f{f:<4d} (from VIEW) = ({c[0]:8.0f},{c[1]:8.0f},{c[2]:8.0f})")
    print()

    # 3. the screen trajectory -- prove the off-screen swoops are REAL
    print("=== Bahamut's SCREEN trajectory (smoothed world -> ndc under real per-frame camera) ===")
    traj = screen_trajectory(log, smoothed=True, window=window)
    on = sum(1 for v in traj.values() if v["on_screen"])
    off = len(traj) - on
    print(f"  {len(traj)} body frames projected: {on} on-screen, {off} off-screen (deliberate swoop/pan)")
    # print a coarse walk so the off-screen windows are visible
    print("  frame |    ndc_x  ndc_y | view_z    | on? | world (X,Y,Z)")
    for f in range(bframes[0], bframes[-1] + 1, 15):
        v = traj.get(f)
        if not v:
            continue
        nx, ny = v["ndc"]
        mark = " " if v["on_screen"] else "OFF"
        print(f"  {f:5d} | {nx:+7.2f} {ny:+7.2f} | {v['view_z']:9.1f} | {mark:>3s} | {_fmt_xyz(v['world'])}")
    print()

    # 4. the pasteable keyframe table for build_thomas.py
    print(f"=== TRACKED keyframes (windowed median, step={step}, window={window}) -- paste into build_thomas.py ===")
    kfs = sample_keyframes(log, track_start, track_end, step, window)
    print(f"  # {len(kfs)} keyframes, frames {kfs[0][0]}..{kfs[-1][0]}")
    for f, p in kfs:
        print(f"    ({f:4d}, ({round(p[0]):6d}, {round(p[1]):6d}, {round(p[2]):7d})),")
    # entrance origin (extrapolate the earliest velocity backward to frame 0) + exit dest (latest fwd)
    ent = linear_extrapolate(kfs[1][1], kfs[1][0], kfs[0][1], kfs[0][0], 0)
    ext = linear_extrapolate(kfs[-2][1], kfs[-2][0], kfs[-1][1], kfs[-1][0], 580)
    print(f"  ENTRANCE_ORIGIN (extrapolated to f0)  = ({round(ent[0])}, {round(ent[1])}, {round(ent[2])})")
    print(f"  EXIT_DEST      (extrapolated to f580) = ({round(ext[0])}, {round(ext[1])}, {round(ext[2])})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG, help="path to sfxmeshprobe.log")
    ap.add_argument("--step", type=int, default=12, help="keyframe sampling step (frames)")
    ap.add_argument("--window", type=int, default=6, help="windowed-median half-width (frames)")
    ap.add_argument("--start", type=int, default=82, help="first tracked frame")
    ap.add_argument("--end", type=int, default=417, help="last tracked frame")
    args = ap.parse_args()
    self_test(args.log, step=args.step, window=args.window, track_start=args.start, track_end=args.end)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
