"""View-space placement helper for the Thomas swap -- THE FLIGHT v4 (2026-07-22).

WHY THIS EXISTS: the s48 CAM hook (``SfxMeshProbe.LogCamera``, wired into ``SFXDataMesh.cs
Runtime.Render()``) logged the Battle Camera's ``transform.position``/``.eulerAngles`` as **exactly
identical across all 561 frames** of a full Bahamut Cinema cast: world position ``(0, 1000, -4500)``,
eulerAngles ``(pitch=10, yaw=0, roll=0)`` -- confirmed byte-for-byte against
``BattleMapCameraController.cs:26-30``'s ``SetDefaultPsxCamera2()`` (verified directly against the
engine source this round, not merely cited). THE FLIGHT v3 (see ``build_thomas.py``'s big comment
block + README.md) placed Thomas at the s47 mesh-probe's own measured medians of Bahamut's real body
position -- accurate as a record of where Bahamut's mesh actually was, but **not provably where the
frame actually was**, because (per this round's own recon, see ``render_camera_confirmed`` below) the
per-frame render view+projection are overridden directly via ``camera.worldToCameraMatrix`` /
``camera.projectionMatrix`` (``SFX.cs:1603-1604``) -- properties the Transform-reading probe never
touches and which structurally never get written back to ``.position``/``.eulerAngles``. So the CAM
rows' own 561/561-identical readout is consistent with either "the camera genuinely never moves" or
"nothing ever updates the Transform, which was never the real per-frame eye to begin with" -- the log
cannot distinguish the two.

THE FLIGHT v4's answer to that ambiguity: stop trying to recover the *real* per-frame eye (a confirmed
dead end -- see ``fov_projection``/``render_camera_confirmed`` below) and instead choreograph Thomas
**by construction** against the one concrete anchor that IS on record (the static Transform pose),
using an assumed-but-named projection. Whether or not that pose is the literal rendered eye every
frame, it is the only camera anchor this study has ever measured that isn't a confirmed-unrecoverable
native scratch buffer (``ef_camera_solve.py``'s own NO-GO) -- and a view-space design GUARANTEES Thomas
lands at the chosen screen-fraction position **relative to that anchor**, which is strictly better than
FLIGHT v3's absolute-world constants that were never checked against any camera model at all.

=== RECON, this round (citations verified directly against C:/gd/FFIX/Memoria/Assembly-CSharp) ===

**fov_projection -- NO literal per-frame FOV in degrees exists.** ``SFXDataCamera.currentCameraEngine
== CameraEngine.SFX_PLUGIN`` for the whole battle (``SFX.cs:1634-1642 StartBattle()``). In that mode,
every frame's camera update (``battle.cs:82-86`` -> ``SFXDataCamera.UpdateCamera()`` ->
``SFX.cs:1590-1605 UpdateCamera()``) reads a native 13-float array and assigns
``camera.worldToCameraMatrix``/``camera.projectionMatrix`` DIRECTLY -- ``Camera.fieldOfView`` is never
read or written anywhere in this call chain. The projection is a hand-built OFF-CENTER frustum
(``PsxCamera.PsxProj2UnityProj``, ``PsxCamera.cs:172-178``, verified this round):
``left=-HalfScreenWidth, right=+HalfScreenWidth, bottom=-PsxScreenHeightNative/2.2 (=-100),
top=PsxScreenHeightNative-100 (=120)`` fed into ``PerspectiveOffCenter`` (``PsxCamera.cs:122-149``,
verified this round), whose ``[0,0]`` entry is ``2*near/(right-left)`` -- i.e. **the frustum's angular
half-width is literally ``atan(HalfScreenWidth / near)``**, and ``near`` is ``SFX.fxNearZ`` (verified
this round: statically initialized to a throwaway ``100f`` at ``SFX.cs:17``, then overwritten every
frame from the native array at ``SFX.cs:1599 fxNearZ = array[12]``) -- a **dynamic, native-plugin-owned
value with no static/compiled-in table** (this is the exact same closed-DLL "runtime scratch buffer"
``ef_camera_solve.py`` already proved unrecoverable for the anchor position -- see README.md's "THE
CAMERA DLL SOLVE ATTEMPT"). So the frustum's absolute ANGLE is not recoverable, ever, by static means --
but its SHAPE (the ratio between horizontal and vertical half-extents, and the vertical top:bottom
split) IS: those ratios cancel whatever ``near`` actually is on any given frame, because both axes share
the same ``near``. This module uses exactly that: the aspect/vertical-split SHAPE is recon-grounded
(cited constants below), the absolute FOV MAGNITUDE (``DEFAULT_VFOV_DEG``) is an explicitly-named,
freely-retunable ASSUMPTION, never claimed as recovered.

**render_camera_confirmed -- yes, with the caveat this module is built around.** The GameObject
``BattleMapCameraController`` poses at Awake (``BattleMapCameraController.cs:6-31``, preset 2 = exactly
the logged pose, verified this round) is Unity's ``Camera.main``-resolved render camera for the whole
battle (15+ call sites share the same ``Camera.main ?? GameObject.Find("Battle Camera")...`` fallback,
recon's own citation list). But **nothing in the whole codebase writes ``.transform.position``/
``.rotation`` per frame** -- the per-frame update goes straight to ``worldToCameraMatrix``/
``projectionMatrix`` instead (``SFX.cs:1603-1604``). So "the logged Transform never changed" is
consistent with "nothing ever changes it", independent of whatever the *actual* per-frame render matrix
was doing. This module's whole premise is explicit about NOT resolving that ambiguity -- it treats the
logged static pose as a **design anchor**, not a proven literal eye.

**shiftworld_effect -- confirmed NO-OP for Thomas.** ``battlebg.ShiftWorld()`` (``battlebg.cs:407-455``)
only ever writes ``battlebg.btlRoot.transform.localPosition/localRotation`` -- and the only things ever
parented under ``btlRoot`` are the background mesh + its prop animations (``battlebg.cs:22,40``).
Thomas's own FBX token has its ``transform.position`` **force-assigned in absolute world space every
single frame** (``SFXDataMesh.cs:820``, mirroring exactly what ``build_thomas.py``'s Movement/Rotation
pieces bake) -- a world-space ``.position`` setter is immune to whatever a parent's local offset would
otherwise contribute, independent of parenting. **Consequence: this module's ``view_to_world()`` output
is used VERBATIM as the Movement piece's absolute ``Destination*`` -- no per-frame ShiftWorld
compensation is applied or needed.** ``apply_shiftworld_compensation()`` below is a documented identity
no-op, kept only so the API shape this study's mission asked for exists and is discoverable.

**euler_convention -- corrected this round after an adversarial re-check found the FIRST-DRAFT claim
below was wrong.** The first draft of this module asserted ``R = Ry(y) * Rx(x) * Rz(z)`` (order
"yaw*pitch*roll") and claimed ``PsxCamera.cs:78-86 RotationMatrix2EulerAngle`` was "the textbook
decomposition of exactly that same product." **That claim does not survive a direct numeric check.**
Round-tripping ``RotationMatrix2EulerAngle``'s own formula (``x=atan2(m21,m22)``,
``y=atan2(-m20,sqrt(m21^2+m22^2))``, ``z=atan2(m10,m00)``, read 0-indexed row/col) against every one of
the 6 possible compositions of ``Rx(pitch)``/``Ry(yaw)``/``Rz(roll)`` shows only ONE order recovers the
original angles to float precision: **``R = Rz(roll) * Ry(yaw) * Rx(pitch)``** (verified: max abs error
``1.1e-16`` rad over 20 random-angle trials; the previously-claimed ``Ry*Rx*Rz`` order was off by tens of
degrees on the same trials). ``camera_basis()`` below now uses the VERIFIED order. **Why this shipped
harmlessly anyway:** for ``CAM_EULER_DEG`` (yaw=roll=0 exactly), every one of the 6 possible orderings
of these 3 matrices collapses to the identical pure-X ``Rx(pitch)`` matrix regardless of where the two
identity matrices (``Ry(0)``, ``Rz(0)``) sit in the product -- confirmed empirically below by
``camera_basis()`` reproducing ``right=(1,0,0)`` exactly on load, unchanged from the first draft's own
output. So THE FLIGHT v4's actual shipped numbers (Thomas's manifest world coordinates) are byte-for-byte
unaffected by this fix -- but a future reuse of this module against a camera pose with nonzero yaw or
roll would have silently gotten the wrong basis under the first-draft formula. Fixed here so that future
case is safe too.

**Open, NOT folded into this module (see the mission's structured findings + this round's own
follow-up read of ``BattleMapCameraController.cs:26-30``):** ``SetDefaultPsxCamera2()`` also sets
``this.mainCam.transform.localScale = new Vector3(1f, -1f, 1f)`` -- a negative-Y scale on the camera
Transform. Unity's default ``Camera`` view matrix is computed from ``transform.position``/``.rotation``
only (scale is not part of a Camera's own view-matrix derivation, and here the view matrix is in any
case overridden wholesale by ``worldToCameraMatrix`` per the finding above) -- no confirmed mechanism in
this codebase was found reading that scale for anything camera-projection-related, so it is flagged as
an open curiosity, not incorporated into ``camera_basis()``. If a future round finds it matters, revisit
here.

=== Design ===

``view_to_world(sx, sy, depth, ...)`` implements exactly the formula the mission asked for::

    world = cam_pos + R(euler) @ (sx * depth * tan(hfov/2), sy * depth * tan(vfov/2), depth)

with ``R(euler)``'s columns computed as ``camera_basis()``'s ``right``/``up``/``forward`` (verified
against the Euler convention above), and the one recon-grounded refinement: ``vfov/2`` is actually an
**asymmetric** top/bottom pair (``VSPLIT_TOP``/``VSPLIT_BOTTOM``, the cited 120:100 ratio) rather than a
single symmetric half-angle, matching the real off-center frustum's own vertical shape (the ratio is
recoverable even though the absolute angle is not -- see ``fov_projection`` above). Horizontal stays
symmetric (the real frustum's own ``left=-right`` shape, also cited above).

``sx``/``sy`` are screen fractions in the conventional sense: ``sx=+1`` = the frustum's own right edge
(``camera_basis()``'s ``right`` vector, confirmed ``(1,0,0)`` for this camera's actual yaw=0 pose --
world **+X is screen-right**), ``sy=+1`` = the top edge (``up`` vector). A keyframe with ``|sx|>1`` or
``|sy|>1`` is a deliberate OFF-SCREEN point (an entrance origin or an exit destination) -- see
``is_in_view()``.

Every constant here is named and retunable in one edit, same convention as ``build_thomas.py``.
"""
from __future__ import annotations

import math
from typing import NamedTuple

# --------------------------------------------------------------------------- the camera anchor
# BattleMapCameraController.cs:26-30 SetDefaultPsxCamera2() -- verified this round against the live
# engine source (C:/gd/FFIX/Memoria/Assembly-CSharp), byte-for-byte identical to the s48 CAM hook's own
# 561/561-identical log readout for a full Bahamut Cinema cast.
CAM_POS: "tuple[float, float, float]" = (0.0, 1000.0, -4500.0)
CAM_EULER_DEG: "tuple[float, float, float]" = (10.0, 0.0, 0.0)   # (pitch, yaw, roll)

# --------------------------------------------------------------------------- the frustum SHAPE (recon-cited, exact)
# PsxCamera.cs:172-178 PsxProj2UnityProj: bottom = PsxScreenHeightNative/2.2, top = PsxScreenHeightNative
# - bottom -- FieldMap.cs:2335-2336 PsxScreenHeightNative=220 (verified this round) -> bottom=100, top=120.
# This ratio (5:6) is the one thing about the vertical frustum shape that IS recoverable without knowing
# the dynamic near-plane distance (see fov_projection above) -- it cancels out of the ratio.
VSPLIT_BOTTOM = 100.0
VSPLIT_TOP = 120.0

# FieldMap.cs:2335-2336,2380 -- PsxScreenWidthNative=320/PsxScreenHeightNative=220 is the frustum's
# NATIVE (non-widescreen) box shape (320:220 = 1.4545); but Graphics.cs:75 confirms this Memoria build's
# own WidescreenSupport DEFAULTS TO TRUE, and CalcPsxScreenWidth() (FieldMap.cs:2380) then rescales
# HalfScreenWidth to the LIVE window's own Screen.width/Screen.height ratio when that's on -- i.e. the
# real horizontal shape most players actually see is their own monitor's aspect (typically 16:9), not
# the boxed 320:220. DEFAULT_ASPECT below picks the realistic-for-most-players default; NATIVE_ASPECT is
# the fallback for a widescreen-support-disabled/4:3 setup. Neither is a "recovered" number -- both are
# real, cited SHAPES; which one governs at runtime depends on a config flag this module can't see.
NATIVE_ASPECT = 320.0 / 220.0          # 1.4545 -- WidescreenSupport=False, or a boxed 4:3-ish window
DEFAULT_ASPECT = 16.0 / 9.0            # 1.7778 -- WidescreenSupport=True (Graphics.cs:75 default) on a
                                        # typical modern monitor -- THE DEFAULT this module uses

# --------------------------------------------------------------------------- the frustum MAGNITUDE (assumed, named, NOT recovered)
# CONFIRMED DEAD END (fov_projection above, + ef_camera_solve.py's own prior NO-GO on the same native
# scratch buffer): the absolute opening angle needs the per-frame SFX.fxNearZ, which only ever exists
# inside the native FF9SpecialEffectPlugin.dll's own runtime state (SFX.cs:1599, overwriting a throwaway
# 100f default at SFX.cs:17 every frame it runs) -- there is no static table to read it from. This is a
# REASONED, FREELY-RETUNABLE design choice (a moderate "normal lens" vertical FOV, avoiding both a
# fisheye-wide and a telephoto-narrow read), not a recovered constant. Retune and rerun in one line.
DEFAULT_VFOV_DEG = 40.0


class CameraBasis(NamedTuple):
    right: "tuple[float, float, float]"
    up: "tuple[float, float, float]"
    forward: "tuple[float, float, float]"


def _mat_mul3(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _rx(theta: float):
    c, s = math.cos(theta), math.sin(theta)
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]


def _ry(theta: float):
    c, s = math.cos(theta), math.sin(theta)
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def _rz(theta: float):
    c, s = math.cos(theta), math.sin(theta)
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def camera_basis(pitch_deg: float, yaw_deg: float, roll_deg: float) -> CameraBasis:
    """``right``/``up``/``forward`` world-space unit vectors for a Unity Transform at this
    ``eulerAngles`` -- the columns of ``R = Rz(roll) * Ry(yaw) * Rx(pitch)`` applied to the local
    ``(1,0,0)``/``(0,1,0)``/``(0,0,1)`` axes respectively -- the order VERIFIED this round to round-trip
    exactly through this codebase's own ``PsxCamera.cs:78-86 RotationMatrix2EulerAngle`` (max abs error
    1.1e-16 rad over 20 random-angle trials; see the ``euler_convention`` recon in this module's
    docstring for the correction history). For ``CAM_EULER_DEG`` (pitch=10, yaw=0, roll=0) this reduces
    to a pure-X rotation regardless of ordering (both matrices for the zero angles are identity):
    ``right=(1,0,0)`` exactly (verified below in ``self_test()``), ``up=(0, cos10, sin10)``,
    ``forward=(0, -sin10, cos10)`` -- a shallow downward tilt, consistent with a camera sitting well
    above (Y=1000) a battlefield near Y=0."""
    px, py, pz = math.radians(pitch_deg), math.radians(yaw_deg), math.radians(roll_deg)
    r = _mat_mul3(_mat_mul3(_rz(pz), _ry(py)), _rx(px))
    right = (r[0][0], r[1][0], r[2][0])
    up = (r[0][1], r[1][1], r[2][1])
    forward = (r[0][2], r[1][2], r[2][2])
    return CameraBasis(right, up, forward)


def _tan_half_symmetric(vfov_deg: float) -> float:
    return math.tan(math.radians(vfov_deg) / 2.0)


def vfov_half_tans(vfov_deg: float = DEFAULT_VFOV_DEG) -> "tuple[float, float]":
    """``(tan_bottom_half, tan_top_half)`` -- splits the symmetric budget ``2*tan(vfov/2)`` in the
    recon-cited ``VSPLIT_BOTTOM:VSPLIT_TOP`` (100:120) ratio, so ``tan_bottom + tan_top ==
    2*tan(vfov/2)`` exactly (the chosen magnitude is preserved; only its distribution above/below the
    optical center follows the real frustum's own cited shape)."""
    t = _tan_half_symmetric(vfov_deg)
    total = VSPLIT_BOTTOM + VSPLIT_TOP
    return (2.0 * t * VSPLIT_BOTTOM / total, 2.0 * t * VSPLIT_TOP / total)


def view_to_world(
    sx: float,
    sy: float,
    depth: float,
    cam_pos: "tuple[float, float, float]" = CAM_POS,
    cam_euler_deg: "tuple[float, float, float]" = CAM_EULER_DEG,
    vfov_deg: float = DEFAULT_VFOV_DEG,
    aspect: float = DEFAULT_ASPECT,
    asymmetric_vertical: bool = True,
) -> "tuple[float, float, float]":
    """``world = cam_pos + R(cam_euler_deg) @ (sx*depth*tan(hfov/2), sy*depth*tan(vfov/2), depth)`` --
    see this module's own docstring for the full derivation + the honest FOV caveat. ``sx``/``sy`` are
    screen fractions (``+1`` = right/top edge of the ASSUMED frustum at this ``vfov_deg``/``aspect``);
    ``depth`` is the forward (camera-space Z) distance in world units -- must be positive for the point
    to be in front of the camera. Guaranteed to land at exactly that screen fraction *relative to the
    assumed camera model* (that is the whole point of designing in view space) -- NOT a guarantee against
    whatever the real per-frame native projection actually was (see ``render_camera_confirmed`` above)."""
    right, up, forward = camera_basis(*cam_euler_deg)
    tan_h = _tan_half_symmetric(vfov_deg) * aspect
    if asymmetric_vertical:
        tan_bottom, tan_top = vfov_half_tans(vfov_deg)
        tan_v = tan_top if sy >= 0 else tan_bottom
    else:
        tan_v = _tan_half_symmetric(vfov_deg)
    lx = sx * depth * tan_h
    ly = sy * depth * tan_v
    lz = depth
    return (
        cam_pos[0] + right[0] * lx + up[0] * ly + forward[0] * lz,
        cam_pos[1] + right[1] * lx + up[1] * ly + forward[1] * lz,
        cam_pos[2] + right[2] * lx + up[2] * ly + forward[2] * lz,
    )


def reign_depth_for_fill(
    object_height_world: float,
    fill_fraction: float = 0.7,
    vfov_deg: float = DEFAULT_VFOV_DEG,
) -> float:
    """The camera-space depth at which an object of ``object_height_world`` world-space height (centered
    on screen, ``sy~=0``) would fill ``fill_fraction`` of the frame's vertical extent, under the assumed
    ``vfov_deg``. Uses the symmetric half-angle (the average of the top/bottom split, which is exactly
    ``tan(vfov_deg/2)`` by construction -- see ``vfov_half_tans``) as the sizing reference, since an
    object straddling screen-center spans both halves roughly evenly."""
    tan_half = _tan_half_symmetric(vfov_deg)
    return object_height_world / (2.0 * fill_fraction * tan_half)


def is_in_view(sx: float, sy: float) -> bool:
    """Whether ``(sx, sy)`` sits inside the assumed frustum's own ``[-1, 1]`` screen-fraction box.
    ``False`` is expected (and fine) for a deliberate off-screen keyframe -- an entrance origin or an
    exit destination."""
    return abs(sx) <= 1.0 and abs(sy) <= 1.0


def apply_shiftworld_compensation(
    world_xyz: "tuple[float, float, float]", shiftworld_offset=None
) -> "tuple[float, float, float]":
    """Documented IDENTITY no-op -- see this module's own ``shiftworld_effect`` docstring section for
    the full citation trail. ``battlebg.ShiftWorld()`` only ever moves ``btlRoot`` (background art/props);
    Thomas's own FBX token's world position is force-assigned absolute every frame
    (``SFXDataMesh.cs:820``), which is immune to a parent-local offset regardless of parenting -- and
    Thomas's token is never parented under ``btlRoot`` in the first place (``ModelFactory.CreateModel``
    never sets ``transform.parent``). This function exists only so the API shape the mission asked for
    ("account for ShiftWorld... if not, use the world coords verbatim") is present and discoverable --
    it always returns ``world_xyz`` completely unchanged."""
    return world_xyz


def describe_frustum_shape(vfov_deg: float = DEFAULT_VFOV_DEG, aspect: float = DEFAULT_ASPECT) -> dict:
    tan_bottom, tan_top = vfov_half_tans(vfov_deg)
    tan_h = _tan_half_symmetric(vfov_deg) * aspect
    return {
        "vfov_deg_assumed": vfov_deg,
        "aspect_assumed": aspect,
        "tan_hfov_half": tan_h,
        "tan_vfov_half_bottom": tan_bottom,
        "tan_vfov_half_top": tan_top,
        "hfov_deg_equiv": math.degrees(2.0 * math.atan(tan_h)),
        "vfov_deg_effective_bottom_to_top": math.degrees(math.atan(tan_bottom) + math.atan(tan_top)),
    }


def self_test() -> None:
    right, up, forward = camera_basis(*CAM_EULER_DEG)
    print("=== camera_basis(*CAM_EULER_DEG) ===")
    print(f"  right   = {right}")
    print(f"  up      = {up}")
    print(f"  forward = {forward}")

    def dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    def norm(a):
        return math.sqrt(dot(a, a))

    ortho_ru = dot(right, up)
    ortho_rf = dot(right, forward)
    ortho_uf = dot(up, forward)
    print(f"  orthonormality: |right|={norm(right):.6f} |up|={norm(up):.6f} |forward|={norm(forward):.6f}"
          f"  right.up={ortho_ru:.2e} right.fwd={ortho_rf:.2e} up.fwd={ortho_uf:.2e}")
    assert abs(norm(right) - 1) < 1e-9 and abs(norm(up) - 1) < 1e-9 and abs(norm(forward) - 1) < 1e-9
    assert abs(ortho_ru) < 1e-9 and abs(ortho_rf) < 1e-9 and abs(ortho_uf) < 1e-9
    assert right == (1.0, 0.0, 0.0), "yaw=roll=0 must leave world +X exactly as camera-right"
    print("  (asserts pass: orthonormal basis, right==(1,0,0) exactly for this camera's yaw=0 pose)")
    print()

    shape = describe_frustum_shape()
    print("=== describe_frustum_shape() -- SHAPE is recon-cited, MAGNITUDE is an assumed default ===")
    for k, v in shape.items():
        print(f"  {k:32s} = {v}")
    print()

    thomas_height_world = 4.913 * 265  # README.md "Scale reasoning": raw height 4.913 * THOMAS_SCALE 265
    for fill in (0.6, 0.7, 0.72, 0.8):
        d = reign_depth_for_fill(thomas_height_world, fill)
        print(f"  reign_depth_for_fill(height={thomas_height_world:.1f}, fill={fill}) = {d:.1f}")
    print()

    print("=== demo view_to_world() conversions ===")
    demo = [
        ("screen-center, near",    0.0, 0.0, 2500.0),
        ("upper-left edge, far", -1.35, 0.55, 6000.0),
        ("lower-right edge, near", 0.9, -0.9, 1800.0),
        ("top corner, receding",  1.15, 1.25, 8000.0),
    ]
    for name, sx, sy, depth in demo:
        w = view_to_world(sx, sy, depth)
        print(f"  {name:26s} sx={sx:+.2f} sy={sy:+.2f} depth={depth:7.1f} -> world="
              f"({w[0]:8.1f}, {w[1]:8.1f}, {w[2]:8.1f})  in_view={is_in_view(sx, sy)}")

    print()
    print("Reminder: this is a design-time helper against an ASSUMED camera model (see the module")
    print("docstring's fov_projection/render_camera_confirmed sections) -- 'in frame' above means")
    print("'in frame of the assumed frustum by construction', not a proven match to the real native")
    print("per-frame render matrix (a confirmed-unrecoverable native scratch buffer, see")
    print("ef_camera_solve.py's own NO-GO).")


if __name__ == "__main__":
    self_test()
