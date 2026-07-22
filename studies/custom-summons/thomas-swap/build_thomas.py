"""Thomas swap -- LOCAL-ONLY MEME BUILD. Replaces Bahamut's creature (mesh only) with the user's
Thomas the Tank Engine model inside the REAL Bahamut Cinema cinematic (real native camera, real
sounds, real EffectPoint/damage timing) -- while keeping stock Bahamut, and every other summon, 100%
untouched.

Builds on the whole ``studies/custom-summons/`` ladder (rungs 1-7, all ★ in-game proven -- see
``PLAN.md``) plus a fresh 3-lens recon (suppression / composition / asset -- journal cited in
README.md) that closed the three open questions this build depends on:

  1. SUPPRESSION -- ``PlaySFX``'s own ``HideMeshes=<indices>`` argument (BattleActionCode.cs:394-419)
     blanks the native creature's terminal ``Graphics.DrawMeshNow`` calls while the native per-frame
     tick (which the real camera track rides) keeps running untouched -- data-only, no engine patch.
  2. COEXISTENCE -- a second, independent ``LoadSFX`` (Route A: two ``SFXData`` entries can sit
     side-by-side in one ``BattleAction.sfxList`` with zero shared mutable state) lets a JSON-mesh
     (our FBX) load and play IN PARALLEL with the native donor's own Raw-mesh load, on a background
     thread that never blocks the main thread's own ``WaitSFXDone`` on the real Bahamut cinematic.
  3. THE ASSET -- Thomas's raw third-party FBX is fully rigid (no skeleton, so the engine's "otherwise
     used verbatim" rule means it ignores his source Model node's own baked axis-conversion rotation
     entirely) -- normalized offline via Blender (``blender_normalize.py``, run once, documented,
     never committed) so the deployed FBX's raw vertices are ALREADY upright/correctly-scaled/
     correctly-facing, needing zero runtime rotation compensation.

MECHANISM (see README.md for the full trace + citations): the bench ability's ``vfx1`` already points
at rung 3's private folder ``ef084`` (``Unused_84`` -- never a real FF9 effect). This script:

  1. Fetches the REAL stock ``ef227/PlayerSequence.seq`` fresh from the user's own install every run
     (sha256-drift-guarded against the exact hash rung 3/4 were built against -- never committed; the
     rung2/3/4 provenance law: verbatim Square-Enix .seq content never lands in the repo).
  2. Splices in ``thomas_player_sequence.seq``'s committed delta (a background ``StartThread`` that
     self-loads THIS SAME folder's id 84 as a JSON/FBX mesh -- rung 7's own proven mechanism, reused)
     immediately before the donor's own ``PlaySFX: SFX=Bahamut__Full`` line, and appends a generated
     ``HideMeshes=<HIDE_KEYS>`` clause to that same line -- the s47 mesh-stream probe's own hex ``_key``
     list (default: the 7 keys the round-1 calibration cast confirmed are Bahamut's own creature/body,
     out of 39 distinct keys logged across the whole cast -- see README.md's "HideMeshes: the s47
     surgical key list" + PROBE.md's round-1 results). This REPLACES the earlier index-range bisection
     guess (``HideMeshes=0,31``): a key is exact and stable for a mesh's whole lifetime, unlike an index
     which can shift position in the draw buffer between phases. ``--hide-keys KEY1,KEY2,...`` overrides
     the list for one deploy, ``--calibrate`` omits the clause entirely (Bahamut's real mesh renders
     unsuppressed, for a clean composition-reference video/log).
  3. Writes the result to ``ef084/PlayerSequence.seq`` -- ``ef227`` (real stock Bahamut, and every
     vanilla Garnet/Eiko cast through it) is NEVER touched.
  4. Deploys ``ef084/FileList.txt`` (reused byte-identical from ``rung7-creature/FileList.txt`` -- same
     ``Model creature_manifest.sfxmodel`` line) and a GENERATED ``thomas_manifest.sfxmodel`` (built from
     the named FLIGHT constants below by ``build_manifest_json()`` -- a 3-phase caster-relative flight,
     not a static hover; the repo copy is kept in sync so it stays git-diffable) -> that same filename
     (OVERWRITING rung 7's own Iviv-clone manifest at that path -- ``--restore`` puts rung 7's back).
  5. Mints Thomas's own additive GEO id (>= 6000, the kit's mint band -- ``ff9mapkit/docs/CUSTOM_MODELS.md``)
     via a BINARY-SAFE raw copy (``ff9mapkit.models.mint.stage_mint``'s own ``fbx=`` path text-decodes
     as ASCII and would corrupt a real binary FBX -- confirmed by the asset lens; this script mirrors
     ``deploy_mint``'s structure by hand instead) + appends the ``3DModel`` DictionaryPatch line.

RELAUNCH: step 5's ``3DModel`` registration is load-time-only (like every other custom GEO mint) --
the FIRST deploy of this id needs ONE relaunch. Steps 1-4 (the .seq/FileList.txt/.sfxmodel edits) are
all zero-cache, per-cast-reparsed, mod-folder-shadowed -- recast-only, same as rungs 2-7.

Reads the normalized FBX + the original texture from ``C:/gd/SCRATCH/thomas/`` (never this repo --
CLAUDE.md provenance law + the repo's blanket ``*.fbx``/``*.png``-adjacent-to-fbx gitignore posture);
refuses with a clear message if either is missing. Run ``blender_normalize.py`` first if
``thomas_normalized.fbx`` isn't there yet (see README.md "Regenerating the normalized model").

Usage (game may be CLOSED or OPEN for steps 1-4; step 5's id needs a relaunch to REGISTER, same as
every mint):

    py studies/custom-summons/thomas-swap/build_thomas.py                        # deploy w/ default HIDE_KEYS
    py studies/custom-summons/thomas-swap/build_thomas.py --hide-keys 0097BD01,0098BD0E  # round-2 candidate test
    py studies/custom-summons/thomas-swap/build_thomas.py --calibrate            # no HideMeshes at all
    py studies/custom-summons/thomas-swap/build_thomas.py --restore   # back to rung 7's resting state
                                                                        # + Thomas's mint fully removed

See README.md for the full test procedure, the failure-mode table, the HideMeshes surgical-key-list
section, and the local-only provenance note. See PROBE.md for the s47 probe's round-1 calibration-cast
results (the full 39-key classification + the trajectory reconstruction this build's FLIGHT is derived
from) and the round-2 refinement protocol.

FLIGHT v3 (2026-07-22, CAMERA-DECODE REWINDOWED): the mesh-probe reconstruction above is accurate for
gross position but can't tell a real camera cut from a fast in-shot reposition. ``ef_camera_decode.py``
(this dir) parses the REAL native ``ef227.bytes`` camera track (open managed code: SFXBinaryFile.cs's
container spec, byte-exact validated this session; SFXDataCamera.cs's Code-stream reader, the same
parser ``ff9mapkit/ff9mapkit/battle/camera_codec.py`` round-trips for raw17) and finds Bahamut Cinema
has exactly **3 real camera shots** with hard cuts at absolute tick 258 and 483 (Thomas's own
PlaySFX-zeroed clock, offset 0) -- NOT at frames 172-179/204-207 where the mesh-position method had
guessed. See ``THE FLIGHT v3`` comment block below for the full re-derivation; the measured waypoints
themselves (P1_DEST..P10_DEST) are UNCHANGED (the decode can't recover a literal eye/aim world position
-- SFXDataCamera's spherical Position->matrix conversion lives in the closed native plugin, a confirmed
gap, not guessed) -- only the piece BOUNDARIES/EASING were corrected to match the real cut timing.

THE CAMERA DLL SOLVE ATTEMPT (2026-07-22, ``ef_camera_solve.py``, this dir): a follow-up pass
re-disassembled the closed ``FF9SpecialEffectPlugin.dll`` (pefile+capstone) to try to recover a
literal per-frame eye/look-at and close the yaw gap above for real. Result: **NO-GO, confirmed, not
guessed** -- 22 of ef227's 27 keyframes key their anchor into a runtime-populated scratch buffer (a PE
section-table read this pass ran directly proves the target RVA has zero bytes backing it on disk), so
no further static disassembly recovers it. A proxy reconstruction (substituting the s47 probe's own
measured Bahamut position as the anchor) still validates only as a coin-flip on directional sanity
(9-below/14-above of 24). Thomas's placement/yaw below are UNCHANGED from FLIGHT v3 as a direct result
-- this is a confirmed dead end, not an unexplored one. See ``ef_camera_solve.py``'s own module
docstring and README.md's "THE CAMERA DLL SOLVE ATTEMPT" section for the full byte-cited case.

THE FLIGHT v4 (2026-07-22, VIEW-SPACE CHOREOGRAPHY -- SUPERSEDES FLIGHT v3): a still-later recon round
found the CAM-hook fix (s48) IS built + the probe DOES now log a camera, and it is **completely static**
across all 561 frames of a full cast: ``(0, 1000, -4500)`` / ``eulerAngles(10, 0, 0)`` -- byte-exact to
``BattleMapCameraController.cs:26-30``'s ``SetDefaultPsxCamera2()`` (verified directly against the
engine source). That re-frames FLIGHT v3's whole premise: Bahamut's apparent swoop was never camera
motion, so his own measured body position (what v3 placed Thomas at) was framed by *whatever the real
per-frame native projection actually was* -- which per this round's own recon is a confirmed
dead end to recover (``ef_camera_solve.py``'s NO-GO, restated below) and, worse, may not even be
represented by this static Transform pose at all (the per-frame render view+projection are overridden
directly via ``camera.worldToCameraMatrix``/``.projectionMatrix``, properties the Transform never
reflects -- see ``viewspace_place.py``'s own docstring, ``render_camera_confirmed`` section, for the
full trace). FLIGHT v3's absolute-world constants were therefore never actually checked against ANY
camera model. FLIGHT v4 fixes that by inverting the method: instead of measuring Bahamut and hoping it
was in frame, it CONSTRUCTS Thomas's placement directly from the one anchor that IS on record (the
static pose) plus an explicitly-assumed projection (``viewspace_place.py``, this dir -- FOV magnitude
is a confirmed-unrecoverable native scratch value, same dead end as the camera-solve NO-GO; the
frustum's SHAPE -- aspect + the asymmetric vertical split -- IS recon-cited and used). Thomas is placed
in SCREEN-FRACTION + depth coordinates (``VS_*`` keyframes below), converted to the same absolute-world
``Destination*`` NCalc constants the engine consumes via ``viewspace_place.view_to_world()`` -- so he
lands at the chosen framing *by construction*, honestly caveated as relative to an assumed camera model
rather than a proven-recovered one. See ``viewspace_place.py``'s module docstring for the full recon
trail (``fov_projection``/``render_camera_confirmed``/``shiftworld_effect``/``euler_convention``).
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]                      # studies/custom-summons/thomas-swap -> <repo>
KIT = REPO / "ff9mapkit"
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(HERE))

from ff9mapkit import config, fsutil          # noqa: E402
from ff9mapkit.models import export as mexport  # noqa: E402
from ff9mapkit.models import mint as mmint      # noqa: E402
import viewspace_place as vsp                   # noqa: E402 -- THE FLIGHT v4's camera/projection model

RUNG7_DIR = REPO / "studies" / "custom-summons" / "rung7-creature"


class DriftError(RuntimeError):
    """A file this script reads (but doesn't own) doesn't match the bytes it was derived against."""

# --------------------------------------------------------------------------- ids / paths
DONOR_EF_ID = 227                            # Bahamut__Full's real effect folder
FRESH_EF_ID = 84                             # rung 3/7's private fresh-id folder -- reused, not re-minted
FRESH_REL_DIR = f"StreamingAssets/Data/SpecialEffects/ef{FRESH_EF_ID:03d}"
DONOR_REL_DIR = f"StreamingAssets/Data/SpecialEffects/ef{DONOR_EF_ID:03d}"

PLAYER_SEQ_NAME = "PlayerSequence.seq"
PLAYER_SEQ_REL = f"{FRESH_REL_DIR}/{PLAYER_SEQ_NAME}"

# The exact sha256 of the stock donor file this script splices (re-verified live this session --
# identical to rung 3/4's own EXPECTED_SHA256, confirming ef227 is still byte-for-byte pristine).
EXPECTED_DONOR_SHA256 = "4bc643bfb3ec478dcc1f5b51261f59637faac9d775cccd38c0055afee14ece63"

# The one line this script edits -- verified byte-exact against the live install this session.
ANCHOR_BASE = "PlaySFX: SFX=Bahamut__Full ; Reflect=True"
ANCHOR_LINE = ANCHOR_BASE + "\r\n"

# --------------------------------------------------------------------------- s47 PROBE -- SURGICAL HIDEMESHES KEY LIST (round 1, 2026-07-22)
# The original blanket HideMeshes=0..63 (2026-07-21) and its index-range bisection successor
# (HideMeshes=0,31, 2026-07-22 morning -- README.md's now-superseded "HideMeshes bisection protocol")
# were both GUESSES against an unknown index space. The s47 mesh-stream probe
# (memoria-patches/s47-sfx-mesh-probe.patch; PROBE.md) removed the guesswork: one instrumented
# ``--calibrate`` cast (Memoria.ini [SfxProbe] Enabled=1) logged every native mesh-draw call across the
# whole ~40s cinematic -- 19,456 MESH rows, 0 CAM rows (the camera hook never fired this cast; a KNOWN
# probe defect, out of scope for this build -- see PROBE.md), tallying to exactly 39 distinct mesh
# ``_key``s. ``TryGetArgMeshList`` (BattleActionCode.cs:394-419) parses each ``0x``-prefixed token in a
# ``HideMeshes=`` list into an exact ``UInt32`` key (``SFXData.cs:1376-1392``'s ``preventedMeshIndices``
# check matches by key OR index) -- a mesh's own ``_key`` is stable for its whole lifetime, so this list
# is exact and immune to the index-form's "meshes shift position in the draw buffer between phases"
# fragility.
#
# Of the 39 keys, 7 are Bahamut's own CREATURE/BODY -- present together on 301/325 frames (92.6%),
# tracing one coherent, physically sensible rigid-body flight (see PROBE.md's round-1 results for the
# full per-key classification and the trajectory this build's FLIGHT constants are reconstructed from):
#   0033B990 / 0033B9D0   (paired, "0033B9_" prefix, frames 82-412)
#   0035BAD0 / 0035BA90   (paired, "0035BA_" prefix, frames 82-410/414)
#   0034BA10 / 0034BA50   (paired, "0034BA_" prefix, frames 82-411)
#   0097BD02              (standalone, frames 82-417)
# These 7 are HIDE_KEYS below -- Bahamut's body vanishes. His own swirl/beam/fire-column EFFECT meshes
# (23 keys, confirmed keep-visible -- incl. 00B7BD80, folded into the fire-column group this round) and
# 9 remaining keys of genuinely ambiguous classification all stay rendering unsuppressed this round (the
# safer default -- see PROBE.md's round-1 results for the full per-key reasoning). Two of those 9
# (00BDBE00, 0098BD0E) are live round-2 candidates for a future addition to HIDE_KEYS -- see PROBE.md's
# round-2 refinement protocol for the recast that would confirm or refute each.
HIDE_KEYS: "tuple[str, ...]" = (
    "0033B990", "0033B9D0",
    "0035BAD0", "0035BA90",
    "0034BA10", "0034BA50",
    "0097BD02",
)


def _hide_meshes_arg(hide_keys: "tuple[str, ...] | None") -> str:
    """``hide_keys=None`` = CALIBRATE mode: no ``HideMeshes`` argument at all -- the patched line is
    then byte-identical to the stock donor's own ``PlaySFX`` line, i.e. Bahamut's real mesh renders
    completely unsuppressed. Otherwise a generated (not hand-typed) ``"0xKEY1,0xKEY2,..."`` hex-key
    list -- the exact form ``TryGetArgMeshList`` parses into its ``keyList`` (as opposed to a bare
    decimal token, which parses into the separate index-based ``indexList``)."""
    if hide_keys is None:
        return ""
    tokens = ",".join(f"0x{key}" for key in hide_keys)
    return f" ; HideMeshes={tokens}"


def patched_line(hide_keys: "tuple[str, ...] | None") -> str:
    return f"{ANCHOR_BASE}{_hide_meshes_arg(hide_keys)}\r\n"

# --------------------------------------------------------------------------- our own committed sources
THOMAS_SEQ_DELTA_PATH = HERE / "thomas_player_sequence.seq"      # committed, 100% our text (the splice)
THOMAS_MANIFEST_REPO_PATH = HERE / "thomas_manifest.sfxmodel"    # committed, 100% our JSON

# rung 7's own committed files -- read directly from that sibling directory, never duplicated
# (matches the rung6/rung7 cross-reference convention). Used both to build the Thomas deploy's
# FileList.txt (identical content either way -- both name "creature_manifest.sfxmodel") and, on
# --restore, to put ef084 back to rung 7's own resting state WITHOUT going through
# rung7-creature/build_rung7.py's own build(). When this was written that function raised
# DriftError on every call; the 2026-07-22 diagnosis found its sha constant was CORRECT all
# along -- core.autocrlf had smudged the committed LF .seq to CRLF on checkout ("git status
# clean" hides exactly that, because autocrlf's clean filter reverses the smudge before
# comparing), which .gitattributes (*.seq/*.sfxmodel -text) now prevents. rung7_build() works
# again, but this self-contained path is deliberately kept: reading rung 7's three committed
# sources directly, with ITS OWN verification, remains the simpler dependency. See README.md
# "Failure modes" for the full story.
RUNG7_FILELIST_PATH = RUNG7_DIR / "FileList.txt"
RUNG7_MANIFEST_PATH = RUNG7_DIR / "creature_manifest.sfxmodel"
RUNG7_SEQ_PATH = RUNG7_DIR / "rung7_player_sequence.seq"

CREATURE_MANIFEST_NAME = "creature_manifest.sfxmodel"           # SAME name rung 7 used
FILELIST_NAME = "FileList.txt"
CREATURE_MANIFEST_REL = f"{FRESH_REL_DIR}/{CREATURE_MANIFEST_NAME}"
FILELIST_REL = f"{FRESH_REL_DIR}/{FILELIST_NAME}"

# --------------------------------------------------------------------------- the Thomas GEO mint
THOMAS_GEO_ID = 6200                          # clear of the bench's existing mint (Iviv's clone, 6100)
THOMAS_GEO_NAME = "GEO_MON_B0_M200"           # M200 = 6200 - MINT_BAND_START(6000), same token scheme as derive_mint_name
THOMAS_SCALE = 265                            # see README.md "Scale reasoning"

# --------------------------------------------------------------------------- THE FLIGHT v4 (2026-07-22, VIEW-SPACE CHOREOGRAPHY)
# HISTORY (superseded, kept for the record -- full detail in README.md): build 1 was a static hover;
# build 2 (the 6-phase "SKY ARC") eyeballed the beats from video; FLIGHT v2 (11 pieces) replaced the
# eyeball with the s47 mesh-probe's real per-frame medians of Bahamut's own 7 body-mesh keys, but had to
# GUESS where the camera cuts were; FLIGHT v3 (13 pieces) removed that guess by decoding the REAL native
# camera container (``ef_camera_decode.py``) -- 3 real shots, hard cuts at ticks 258/483 -- and rewindowed
# the SAME measured XYZ waypoints against the real cut timing. All three placed Thomas at coordinates
# derived from *Bahamut's own measured body position*, on the working assumption that wherever Bahamut's
# body was, the real camera must have been framing it.
#
# THE PREMISE THAT ASSUMPTION RESTED ON DIDN'T SURVIVE THIS ROUND'S OWN RECON. The s48 CAM-hook fix (coded
# alongside FLIGHT v3, not yet built at the time) is now built, and a fresh cast's CAM rows are
# **completely static across all 561 logged frames**: ``(0, 1000, -4500)`` / ``eulerAngles(10, 0, 0)`` --
# verified byte-exact against ``BattleMapCameraController.cs:26-30``'s ``SetDefaultPsxCamera2()`` directly
# in the engine source this round. Bahamut's apparent cinematic swoop was therefore never camera motion --
# it's his own creature moving through world space while a fixed viewpoint watches. That's actually GOOD
# news for placement (a known, fixed anchor to build from) but it retroactively undermines FLIGHT v1-v3's
# method: Bahamut's measured position was framed by whatever the REAL per-frame native projection was
# doing (``camera.worldToCameraMatrix``/``.projectionMatrix``, overridden directly every frame,
# ``SFX.cs:1603-1604`` -- properties this static Transform pose never reflects either way), which is a
# CONFIRMED dead end to recover (``ef_camera_solve.py``'s NO-GO). FLIGHT v3's absolute constants were
# therefore never actually verified in-frame against any camera model -- they just happened to be wherever
# Bahamut's mesh was, which is not the same claim.
#
# THE FLIGHT v4 FIX: stop inferring placement from Bahamut and instead CONSTRUCT it, directly, against the
# one camera anchor that IS on record. ``viewspace_place.py`` (this dir) implements
# ``world = cam_pos + R(cam_euler) @ (sx*depth*tan(hfov/2), sy*depth*tan(vfov/2), depth)`` -- the exact
# formula the mission specified -- using an EXPLICITLY NAMED, RETUNABLE assumed FOV (the absolute angle is
# the same confirmed-unrecoverable native scratch value ``ef_camera_solve.py`` already hit; see that
# module's own docstring for the full recon: ``fov_projection``/``render_camera_confirmed``/
# ``shiftworld_effect``/``euler_convention``, each independently re-verified against the live engine source
# this round). Placing Thomas in (screen-fraction, depth) space GUARANTEES he lands at the chosen framing
# *relative to that assumed model*, by construction -- strictly stronger than FLIGHT v3's un-checked
# absolute constants, honestly weaker than a claim to have recovered the true per-frame eye (which no
# static method can -- confirmed, not merely unresolved).
#
# SHIFTWORLD: confirmed a non-issue (``viewspace_place.py``'s ``shiftworld_effect`` docstring) -- Thomas's
# JSON-mesh token gets its ``transform.position`` force-assigned in absolute world space every frame
# (``SFXDataMesh.cs:820``) and is never parented under ``battlebg.btlRoot`` (the only thing ``ShiftWorld``
# ever moves) -- so ``view_to_world()``'s output is used VERBATIM, no per-frame compensation.
#
# ORIENTATION: the camera's ``forward`` vector at this pose is ``(0, -sin10, cos10)`` -- see
# ``viewspace_place.camera_basis()`` -- i.e. it looks mostly along world +Z (``cos10 ~= 0.985``), the SAME
# general direction Thomas's own normalized neutral yaw (0) points (README's axis-verification: his face
# is at local/world +Z at yaw=0). A camera looking the same direction an actor's nose points sees that
# actor's BACK, not its face -- so ``YAW_BROADSIDE`` (unchanged from FLIGHT v2/v3, now justified against
# THIS camera's own basis rather than assumed) turns him 90 deg to present his iconic side profile. No
# Z-roll in any piece (he is not PSX-inverted; established in README's axis-verification).
#
# THE VIEW-SPACE FLIGHT (8 pieces, replacing FLIGHT v3's 13 -- durations sum to THOMAS_END=580, unchanged,
# matching the .seq's own ``WaitSFXDone``-gated cast length): every ``VS_*`` keyframe below is
# ``(sx, sy, depth_factor)`` -- ``sx``/``sy`` are screen fractions (``+1``=right/top edge of the ASSUMED
# frustum), ``depth_factor`` multiplies ``REIGN_DEPTH`` (the camera-space distance at which Thomas's own
# measured HEIGHT -- not his length, which lies along world X once broadside, see the failure-mode table
# in README.md -- fills ``TARGET_REIGN_FILL`` of the frame's vertical extent). Converted to absolute world
# XYZ via ``viewspace_place.view_to_world()`` at manifest-build time -- the engine still consumes plain
# NCalc numeric constants, unchanged schema.
#   ENTRANCE_ORIGIN (Origin of P1 only) -- off the upper-left edge, far: the pre-swoop start point
#   P1  ENTRANCE           0-90    swoop in + descend from the edge to a near-center settle    SinusOut
#   P2  APPROACH-TO-REIGN 90-150   push in to full REIGN_DEPTH, near-center                    SinusIn
#   P3  REIGN BOB (up)   150-195   gentle breathing bob, closer/higher                         Sinus
#   P4  REIGN BOB (down) 195-240   gentle breathing bob, farther/lower                          Sinus
#   P5  LATERAL PASS     240-340   slow drift across the frame ("for life") -- optional flourish Sinus
#   P6  REIGN BOB (settle) 340-430 back toward center -- the ground-reign/fire-column/damage-beat window Sinus
#   P7  REIGN HOLD       430-490   a steady beat immediately before the exit transition          Sinus
#   P8  EXIT CLIMB       490-580   climb away toward a top corner, receding                      SinusIn
#
# CAVEAT: this is a DESIGN, not a measurement -- there is no ground truth to check it against (the
# donor's own real per-frame render state is the same confirmed-unrecoverable native scratch buffer
# throughout this whole study). It supersedes FLIGHT v1-v3's mesh-derived waypoints entirely (those
# described where Bahamut's body WAS, which is a different question from where Thomas should BE framed
# now that the camera model is understood to be this static assumed one) -- retune any ``VS_*``
# keyframe, ``TARGET_REIGN_FILL``, or ``vsp.DEFAULT_VFOV_DEG`` and rerun, recast-only, no relaunch. Per
# the project's own video-for-visual-bugs law, a fresh capture of an actual cast is the next real check.
THOMAS_HEIGHT_RAW = 4.913           # README.md "Scale reasoning": raw (pre-scale) bounding-box height
TARGET_REIGN_FILL = 0.72            # mission's own "fill 60-80% of frame height" -- picked the midpoint
REIGN_DEPTH = vsp.reign_depth_for_fill(THOMAS_HEIGHT_RAW * THOMAS_SCALE, TARGET_REIGN_FILL)

# Yaw justification, COMPUTED (not assumed) against THIS camera's own basis -- see the ORIENTATION
# paragraph above. A strongly positive dot product confirms the camera looks the same general direction
# Thomas's neutral (yaw=0) nose points, i.e. yaw=0 would show his back -- broadside (90) is the fix.
_CAM_FORWARD = vsp.camera_basis(*vsp.CAM_EULER_DEG).forward
YAW_FORWARD_DOT = _CAM_FORWARD[2]   # cos(10 deg) ~= 0.985 -- Thomas's neutral +Z axis vs. camera forward
YAW_BROADSIDE = 90                  # Rotation.Z stays 0 throughout every piece -- no roll (see above)

# View-space keyframes -- (sx, sy, depth_factor); depth_factor multiplies REIGN_DEPTH. Named per the
# piece table above.
VS_ENTRANCE_ORIGIN = (-1.35, 0.55, 2.40)   # off the upper-left edge, far -- the pre-swoop start (P1 Origin only)
VS_P1_DEST         = (-0.25, 0.10, 1.35)   # entrance settle -- still off-center/smaller, descending in
VS_P2_DEST         = ( 0.05,-0.05, 1.00)   # arrives at full REIGN_DEPTH, near-center
VS_P3_DEST         = ( 0.10, 0.10, 0.95)   # breathing bob up (slightly closer/bigger)
VS_P4_DEST         = (-0.02,-0.12, 1.05)   # breathing bob down (slightly farther/smaller)
VS_P5_DEST         = ( 0.55,-0.05, 1.00)   # the lateral pass -- slow drift across the frame
VS_P6_DEST         = ( 0.00, 0.02, 0.98)   # settle back toward center -- ground-reign/damage-beat window
VS_P7_DEST         = (-0.08,-0.06, 1.02)   # a steady hold immediately before the exit transition
VS_P8_DEST         = ( 1.15, 1.25, 3.20)   # exit -- climbs toward a top corner, receding into the distance

# Durations (frames, Thomas's own PlaySFX-zeroed clock) -- named, sum to THOMAS_END=580 (unchanged from
# every prior FLIGHT version, matching the donor's own WaitSFXDone-gated cast length).
P1_ENTRANCE_DURATION = 90           # swoop in + descend from the edge to a near-center settle
P2_APPROACH_DURATION = 60           # push in to full reign size/position
P3_BOB_UP_DURATION = 45             # gentle breathing bob, up
P4_BOB_DOWN_DURATION = 45           # gentle breathing bob, down
P5_LATERAL_PASS_DURATION = 100      # the slow drift across the frame ("for life")
P6_BOB_SETTLE_DURATION = 90         # settle back toward center -- ground-reign/fire-column/damage-beat window
P7_HOLD_DURATION = 60               # a steady beat immediately before the exit transition
P8_EXIT_CLIMB_DURATION = 90         # climb away toward a top corner, receding
THOMAS_END = (P1_ENTRANCE_DURATION + P2_APPROACH_DURATION + P3_BOB_UP_DURATION + P4_BOB_DOWN_DURATION
              + P5_LATERAL_PASS_DURATION + P6_BOB_SETTLE_DURATION + P7_HOLD_DURATION
              + P8_EXIT_CLIMB_DURATION)   # 580, unchanged from every prior FLIGHT version

# The absolute-world XYZ this manifest actually ships, computed ONCE from the view-space keyframes above
# via viewspace_place.view_to_world() -- ShiftWorld verbatim (no compensation, see the SHIFTWORLD note
# above), rounded to whole units to match every prior FLIGHT version's own NCalc-constant precision.
def _vs(kf: "tuple[float, float, float]") -> "tuple[int, int, int]":
    sx, sy, depth_factor = kf
    x, y, z = vsp.view_to_world(sx, sy, depth_factor * REIGN_DEPTH)
    return (round(x), round(y), round(z))


ENTRANCE_ORIGIN = _vs(VS_ENTRANCE_ORIGIN)
P1_DEST = _vs(VS_P1_DEST)
P2_DEST = _vs(VS_P2_DEST)
P3_DEST = _vs(VS_P3_DEST)
P4_DEST = _vs(VS_P4_DEST)
P5_DEST = _vs(VS_P5_DEST)
P6_DEST = _vs(VS_P6_DEST)
P7_DEST = _vs(VS_P7_DEST)
P8_DEST = _vs(VS_P8_DEST)

# Third-party asset sources -- OUTSIDE the repo, never committed (CLAUDE.md provenance law; the repo's
# blanket *.fbx gitignore already makes an accidental commit structurally impossible, this is belt-
# and-suspenders: the paths themselves live only in this script, not the asset bytes).
SCRATCH_DIR = Path(r"C:\gd\SCRATCH\thomas")
THOMAS_FBX_SRC = SCRATCH_DIR / "blender_out" / "thomas_normalized.fbx"   # produced by blender_normalize.py
THOMAS_TEX_SRC = SCRATCH_DIR / "Thomas_d.png"                            # the original, untouched


class ThomasAssetError(RuntimeError):
    """A required third-party source file is missing or doesn't look like what we expect."""


def _require_source_assets():
    if not THOMAS_FBX_SRC.is_file():
        raise ThomasAssetError(
            f"normalized FBX not found: {THOMAS_FBX_SRC}\n"
            f"Run blender_normalize.py first (see README.md 'Regenerating the normalized model'):\n"
            f'  "path/to/blender.exe" --background --python {HERE / "blender_normalize.py"} -- '
            f'"{SCRATCH_DIR / "Thomas the Tank Engine.fbx"}" "{SCRATCH_DIR / "blender_out"}"'
        )
    magic = THOMAS_FBX_SRC.open("rb").read(20)
    if magic != b"Kaydara FBX Binary  ":
        raise ThomasAssetError(f"{THOMAS_FBX_SRC} doesn't look like a binary FBX (bad magic: {magic!r})")
    if not THOMAS_TEX_SRC.is_file():
        raise ThomasAssetError(
            f"texture not found: {THOMAS_TEX_SRC}\n"
            f"Expected the original Thomas_d.png beside the source FBX in {SCRATCH_DIR}"
        )
    png_magic = THOMAS_TEX_SRC.open("rb").read(8)
    if png_magic != b"\x89PNG\r\n\x1a\n":
        raise ThomasAssetError(f"{THOMAS_TEX_SRC} doesn't look like a PNG (bad magic: {png_magic!r})")


def _read_verified(path: Path, expected_sha256: str, desc: str) -> tuple[bytes, str]:
    if not path.exists():
        raise FileNotFoundError(f"{desc} not found: {path}")
    raw = path.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != expected_sha256:
        raise DriftError(
            f"{path} sha256 {got} != expected {expected_sha256} -- {desc} has changed since this "
            "script was derived against it; refusing to splice against unverified content."
        )
    return raw, raw.decode("utf-8")


def _read_repo_file(path: Path, desc: str) -> bytes:
    if not path.exists():
        raise FileNotFoundError(f"{desc} not found in repo: {path}")
    return path.read_bytes()


def _write(dest: Path, data: bytes) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    fsutil.atomic_write_bytes(dest, data)
    readback = dest.read_bytes()
    if readback != data:
        raise RuntimeError(f"write verification failed at {dest} -- readback != what we wrote")
    return hashlib.sha256(data).hexdigest()


def _pt(xyz: "tuple[int, int, int]") -> dict:
    """Split an (X, Y, Z) absolute-world tuple into the 3 ``Destination*`` JSON keys as plain numeric
    NCalc constants (a bare literal like ``"-17860"`` parses via NCalc exactly as well as an expression
    -- no ``CasterPosition*`` anchor needed under the absolute-world-coordinate design; these XYZ values
    are themselves computed from view-space keyframes by ``_vs()``/``viewspace_place.view_to_world()``,
    see THE FLIGHT v4 comment block above)."""
    x, y, z = xyz
    return {"DestinationX": str(x), "DestinationY": str(y), "DestinationZ": str(z)}


def build_manifest_json() -> dict:
    """Generate ``thomas_manifest.sfxmodel``'s JSON from the named FLIGHT v4 constants above (schema
    verified against ``ParametricMovement.LoadFromJSON``, Memoria/Battle/SFX/ParametricMovement.cs:
    58-136 -- an array of pieces, ``Duration`` + per-axis ``Origin*``/``Destination*``/
    ``InterpolationType*``; an absent ``Origin*`` key on piece i>0 CHAINS from the prior piece's own
    ``Destination*`` expression -- used below for pieces 2-8 of both Movement and Rotation). 8 pieces,
    each one a view-space keyframe (``VS_*`` above) converted to absolute world XYZ via
    ``viewspace_place.view_to_world()`` -- entrance (off-edge, descending) -> approach-to-reign -> a
    2-piece breathing bob -> a slow lateral pass -> a settle back to center (the ground-reign/damage-beat
    window) -> a steady hold -> an exit climb toward a top corner. Every Destination is always given
    explicitly (never relied on the dest-defaults-to-origin fallback) so the JSON stays self-documenting.
    Scaling is unchanged (constant THOMAS_SCALE, one piece spanning the whole THOMAS_END, no motion
    needed)."""
    movement = [
        {   # P1 ENTRANCE: off the upper-left edge, far -> a near-center settle, descending in
            "Duration": str(P1_ENTRANCE_DURATION),
            "OriginX": str(ENTRANCE_ORIGIN[0]), "OriginY": str(ENTRANCE_ORIGIN[1]), "OriginZ": str(ENTRANCE_ORIGIN[2]),
            **_pt(P1_DEST),
            "InterpolationTypeX": "SinusOut", "InterpolationTypeY": "SinusOut", "InterpolationTypeZ": "SinusOut",
        },
        {   # P2 APPROACH-TO-REIGN: push in to full REIGN_DEPTH, near-center (Origin chained from P1's Destination)
            "Duration": str(P2_APPROACH_DURATION),
            **_pt(P2_DEST),
            "InterpolationTypeX": "SinusIn", "InterpolationTypeY": "SinusIn", "InterpolationTypeZ": "SinusIn",
        },
        {   # P3 REIGN BOB (up): gentle breathing bob, closer/higher
            "Duration": str(P3_BOB_UP_DURATION),
            **_pt(P3_DEST),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P4 REIGN BOB (down): gentle breathing bob, farther/lower
            "Duration": str(P4_BOB_DOWN_DURATION),
            **_pt(P4_DEST),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P5 LATERAL PASS: slow drift across the frame -- the mission's own "optional... for life" flourish
            "Duration": str(P5_LATERAL_PASS_DURATION),
            **_pt(P5_DEST),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P6 REIGN BOB (settle): back toward center -- the ground-reign/fire-column/damage-beat window
            "Duration": str(P6_BOB_SETTLE_DURATION),
            **_pt(P6_DEST),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P7 REIGN HOLD: a steady beat immediately before the exit transition
            "Duration": str(P7_HOLD_DURATION),
            **_pt(P7_DEST),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P8 EXIT CLIMB: climbs away toward a top corner, receding into the distance -- accelerating departure
            "Duration": str(P8_EXIT_CLIMB_DURATION),
            **_pt(P8_DEST),
            "InterpolationTypeX": "SinusIn", "InterpolationTypeY": "SinusIn", "InterpolationTypeZ": "SinusIn",
        },
    ]
    rotation = [
        {   # P1: bank from his normalized-forward (0, faces the same way the camera looks -- his BACK, see
            # the ORIENTATION note above) to broadside (90) on arrival
            "Duration": str(P1_ENTRANCE_DURATION),
            "OriginY": "0", "DestinationY": str(YAW_BROADSIDE),
            "OriginZ": "0", "DestinationZ": "0",
            "InterpolationTypeY": "Sinus",
        },
        {"Duration": str(P2_APPROACH_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P3_BOB_UP_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P4_BOB_DOWN_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P5_LATERAL_PASS_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P6_BOB_SETTLE_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {   # P7: HOLD broadside through the last steady beat, then turn back to forward-facing during the
            # exit climb (P8) -- see the ORIENTATION note above for why no per-shot camera-relative yaw was
            # computed (the DLL-side eye/aim gap, ef_camera_solve.py's own confirmed NO-GO)
            "Duration": str(P7_HOLD_DURATION),
            "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0",
        },
        {   # P8 EXIT CLIMB: turn back to forward-facing as he climbs away
            "Duration": str(P8_EXIT_CLIMB_DURATION),
            "DestinationY": "0",
            "DestinationZ": "0",
            "InterpolationTypeY": "Sinus",
        },
    ]
    scaling = {
        "Duration": str(THOMAS_END),
        "OriginX": str(THOMAS_SCALE), "OriginY": str(THOMAS_SCALE), "OriginZ": str(THOMAS_SCALE),
        "DestinationX": str(THOMAS_SCALE), "DestinationY": str(THOMAS_SCALE), "DestinationZ": str(THOMAS_SCALE),
    }
    return {
        "FBX": [
            {
                "Path": THOMAS_GEO_NAME,
                "Start": "0",
                "End": str(THOMAS_END),
                "Movement": movement,
                "Rotation": rotation,
                "Scaling": scaling,
            }
        ]
    }


def splice_sequence(donor_text: str, hide_keys: "tuple[str, ...] | None") -> str:
    """Insert the Thomas delta block immediately before ANCHOR_LINE, and replace ANCHOR_LINE itself
    with ``patched_line(hide_keys)`` (the HideMeshes-augmented form, or -- ``hide_keys=None`` -- the
    bare unmodified anchor text, i.e. CALIBRATE mode). Raises DriftError if ANCHOR_LINE isn't found
    (the donor's shape changed since this script's splice point was derived -- abort rather than
    guess)."""
    lines = donor_text.splitlines(keepends=True)
    try:
        idx = lines.index(ANCHOR_LINE)
    except ValueError:
        raise DriftError(
            f"expected line {ANCHOR_LINE!r} not found in the donor copy -- its shape has changed "
            "since this script's splice point was derived; abort rather than guess"
        ) from None
    delta_text = THOMAS_SEQ_DELTA_PATH.read_text(encoding="utf-8")
    # The committed delta file's own leading `//` comment block is documentation for a human reader --
    # only the actual StartThread...EndThread block (the last 6 non-comment, non-blank lines) is
    # spliced into the deployed sequence.
    delta_lines = [ln for ln in delta_text.splitlines(keepends=True)
                   if ln.strip() and not ln.lstrip().startswith("//")]
    if not delta_lines or delta_lines[0].strip() != "StartThread: Condition=1 == 1 ; Sync=False":
        raise RuntimeError(
            f"{THOMAS_SEQ_DELTA_PATH} doesn't start with the expected StartThread line after "
            "stripping comments/blanks -- refusing to splice unexpected content"
        )
    new_lines = lines[:idx] + delta_lines + [patched_line(hide_keys)] + lines[idx + 1:]
    return "".join(new_lines)


def mint_thomas(mod_root: Path) -> dict:
    """Mint Thomas's additive GEO id via a BINARY-SAFE raw copy (never ff9mapkit.models.mint.stage_mint's
    own fbx= path, which text-decodes as ASCII and would corrupt a real binary FBX -- the asset lens's
    own finding). Mirrors deploy_mint's structure by hand: geometry+texture to the loose-override path,
    the 3DModel directive appended to DictionaryPatch.txt (idempotent)."""
    _require_source_assets()
    man = mmint.resolve_mint({"id": THOMAS_GEO_ID, "fbx": str(THOMAS_FBX_SRC), "name": THOMAS_GEO_NAME})
    dest = mod_root.joinpath(*mexport._RES, *mexport.model_dir_parts(man["type_int"], man["id"]))
    dest.mkdir(parents=True, exist_ok=True)

    fbx_bytes = THOMAS_FBX_SRC.read_bytes()
    fbx_dest = dest / f"{man['id']}.fbx"
    fbx_sha256 = _write(fbx_dest, fbx_bytes)

    tex_bytes = THOMAS_TEX_SRC.read_bytes()
    tex_dest = dest / THOMAS_TEX_SRC.name
    tex_sha256 = _write(tex_dest, tex_bytes)

    dp = mod_root / "DictionaryPatch.txt"
    lines = dp.read_text(encoding="utf-8").splitlines() if dp.exists() else []
    directive_added = False
    if man["directive"] not in lines:
        lines.append(man["directive"])
        fsutil.atomic_write_text(dp, "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        directive_added = True

    man.update(
        fbx_dest=str(fbx_dest), fbx_sha256=fbx_sha256,
        tex_dest=str(tex_dest), tex_sha256=tex_sha256,
        dictionary_patch=str(dp), directive_added=directive_added,
    )
    return man


def unmint_thomas(mod_root: Path) -> dict:
    """Remove exactly what mint_thomas staged: the Models/<type>/<id>/ folder + the DictionaryPatch
    line. Idempotent -- safe to call even if nothing was ever minted."""
    type_int = mmint.type_int_of_name(THOMAS_GEO_NAME)
    dest = mod_root.joinpath(*mexport._RES, *mexport.model_dir_parts(type_int, THOMAS_GEO_ID))
    removed_dir = False
    if dest.exists():
        import shutil
        shutil.rmtree(dest)
        removed_dir = True
        # clean up now-empty parent chain up to Resources/Models, mirroring rung3's empty-dir cleanup law
        parent = dest.parent
        models_root = mod_root.joinpath(*mexport._RES, "Models")
        while parent != models_root and parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent

    directive = f"3DModel {THOMAS_GEO_ID} {THOMAS_GEO_NAME}"
    dp = mod_root / "DictionaryPatch.txt"
    directive_removed = False
    if dp.exists():
        lines = dp.read_text(encoding="utf-8").splitlines()
        if directive in lines:
            lines = [ln for ln in lines if ln != directive]
            fsutil.atomic_write_text(dp, "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")
            directive_removed = True

    return {"removed_dir": removed_dir, "dest": str(dest), "directive_removed": directive_removed,
            "directive": directive}


def build_thomas(mod_root: Path, game_path: Path, hide_keys: "tuple[str, ...] | None" = HIDE_KEYS) -> dict:
    donor_bytes, donor_text = _read_verified(
        game_path / DONOR_REL_DIR / PLAYER_SEQ_NAME, EXPECTED_DONOR_SHA256, "stock ef227/PlayerSequence.seq"
    )
    out_text = splice_sequence(donor_text, hide_keys)
    out_bytes = out_text.encode("utf-8")

    seq_dest = mod_root / FRESH_REL_DIR / PLAYER_SEQ_NAME
    seq_sha256 = _write(seq_dest, out_bytes)

    diff = "".join(difflib.unified_diff(
        donor_text.splitlines(keepends=True), out_text.splitlines(keepends=True),
        fromfile=f"stock/ef{DONOR_EF_ID:03d}/{PLAYER_SEQ_NAME}",
        tofile=f"FF9CustomMap/{PLAYER_SEQ_REL}",
    ))

    filelist_bytes = _read_repo_file(RUNG7_FILELIST_PATH, "rung 7's FileList.txt (reused verbatim)")
    filelist_dest = mod_root / FILELIST_REL
    filelist_sha256 = _write(filelist_dest, filelist_bytes)

    # Generated from the named FLIGHT constants above (not hand-typed JSON) -- the repo file stays the
    # committed, git-diffable source of truth, but the Python constants are the single point of edit.
    manifest_bytes = (json.dumps(build_manifest_json(), indent=2) + "\n").encode("utf-8")
    _write(THOMAS_MANIFEST_REPO_PATH, manifest_bytes)   # keep the committed copy in sync
    manifest_dest = mod_root / CREATURE_MANIFEST_REL
    manifest_sha256 = _write(manifest_dest, manifest_bytes)

    mint_info = mint_thomas(mod_root)

    return {
        "seq_dest": str(seq_dest), "seq_sha256": seq_sha256, "seq_diff": diff,
        "filelist_dest": str(filelist_dest), "filelist_sha256": filelist_sha256,
        "manifest_dest": str(manifest_dest), "manifest_sha256": manifest_sha256,
        "mint": mint_info, "hide_keys": hide_keys,
    }


def restore(mod_root: Path, game_path: Path) -> dict:
    """Back to rung 7's own proven resting state: ef084's FileList.txt/creature_manifest.sfxmodel/
    PlayerSequence.seq reset to rung 7's own three committed source files (read directly from
    rung7-creature/, deployed here rather than via that directory's own build_rung7.build() -- see
    the RUNG7_FILELIST_PATH comment above for why), PLUS Thomas's mint fully removed (unlike rung 7's
    Iviv-clone asset, which pre-existed the whole custom-summons study and is never this study's to
    manage, Thomas's GEO mint is wholly new content THIS script introduced -- a true --restore
    removes it too)."""
    filelist_bytes = _read_repo_file(RUNG7_FILELIST_PATH, "rung 7's FileList.txt")
    filelist_dest = mod_root / FILELIST_REL
    filelist_sha256 = _write(filelist_dest, filelist_bytes)

    manifest_bytes = _read_repo_file(RUNG7_MANIFEST_PATH, "rung 7's creature_manifest.sfxmodel")
    manifest_dest = mod_root / CREATURE_MANIFEST_REL
    manifest_sha256 = _write(manifest_dest, manifest_bytes)

    seq_bytes = _read_repo_file(RUNG7_SEQ_PATH, "rung 7's rung7_player_sequence.seq")
    seq_dest = mod_root / FRESH_REL_DIR / PLAYER_SEQ_NAME
    seq_sha256 = _write(seq_dest, seq_bytes)

    rung7_result = {
        "filelist_dest": str(filelist_dest), "filelist_sha256": filelist_sha256,
        "manifest_dest": str(manifest_dest), "manifest_sha256": manifest_sha256,
        "seq_dest": str(seq_dest), "seq_sha256": seq_sha256,
    }
    unmint_result = unmint_thomas(mod_root)
    return {"rung7": rung7_result, "unmint": unmint_result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--thomas", action="store_true",
                        help="deploy the Thomas swap (DEFAULT if no flag given)")
    group.add_argument("--restore", action="store_true",
                        help="undo the Thomas swap -- back to rung 7's own proven resting state, and "
                             "Thomas's GEO mint fully removed")
    hg_group = parser.add_mutually_exclusive_group()
    hg_group.add_argument("--hide-keys", metavar="KEY1,KEY2,...", default=None,
                           help="override HIDE_KEYS (default the s47-probe-confirmed creature keys: "
                                + ",".join(HIDE_KEYS) + ") for this deploy -- comma-separated hex mesh "
                                "keys, `0x` prefix optional, e.g. --hide-keys 0097BD01,0098BD0E to test a "
                                "round-2 candidate. Only meaningful with a Thomas-swap deploy (not "
                                "--restore). See README.md's HideMeshes: the s47 surgical key list + "
                                "PROBE.md's round-2 refinement protocol.")
    hg_group.add_argument("--calibrate", action="store_true",
                           help="deploy with NO HideMeshes argument at all -- the patched line is then "
                                "byte-identical to the stock donor's own PlaySFX line, so Bahamut's real "
                                "mesh renders completely unsuppressed. For recording a clean composition-"
                                "reference video/log. Mutually exclusive with --hide-keys.")
    args = parser.parse_args()
    mode = "restore" if args.restore else "thomas"

    if mode == "restore" and (args.hide_keys or args.calibrate):
        parser.error("--hide-keys/--calibrate only apply to a Thomas-swap deploy, not --restore")

    if args.calibrate:
        hide_keys = None
    elif args.hide_keys:
        raw_tokens = [t.strip() for t in args.hide_keys.split(",") if t.strip()]
        if not raw_tokens:
            parser.error(f"--hide-keys must be a non-empty comma-separated list, got {args.hide_keys!r}")
        normalized = []
        for tok in raw_tokens:
            bare = tok[2:] if tok.lower().startswith("0x") else tok
            try:
                int(bare, 16)
            except ValueError:
                parser.error(f"--hide-keys token {tok!r} isn't a valid hex key")
            normalized.append(bare.upper())
        hide_keys = tuple(normalized)
    else:
        hide_keys = HIDE_KEYS

    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print(f"private id   : ef{FRESH_EF_ID:03d} (rung 3/7's fresh-id folder -- reused, not re-minted)")
    print(f"mode         : {'THOMAS SWAP' if mode == 'thomas' else 'RESTORE (rung-7 resting state)'}")
    if mode == "thomas":
        if hide_keys is None:
            print("hide keys    : CALIBRATE -- no HideMeshes argument at all (Bahamut renders unsuppressed)")
        else:
            print(f"hide keys    : {len(hide_keys)} key(s) -- " + ",".join(f"0x{k}" for k in hide_keys))
    print()

    try:
        if mode == "thomas":
            result = build_thomas(mod_root, game_path, hide_keys)
        else:
            result = restore(mod_root, game_path)
    except (DriftError, ThomasAssetError) as e:
        print(f"REFUSING TO BUILD:\n  {e}", file=sys.stderr)
        return 1

    if mode == "thomas":
        print(f"=== {PLAYER_SEQ_REL} ===")
        print(f"written  : {result['seq_dest']}")
        print(f"  sha256 : {result['seq_sha256']}")
        print()
        print("--- unified diff vs stock ef227/PlayerSequence.seq ---")
        print(result["seq_diff"] if result["seq_diff"] else "(no diff -- unexpected)")
        print()
        print(f"=== {FILELIST_REL} (reused verbatim from rung7-creature/FileList.txt) ===")
        print(f"written  : {result['filelist_dest']}")
        print(f"  sha256 : {result['filelist_sha256']}")
        print()
        print(f"=== {CREATURE_MANIFEST_REL} (GENERATED thomas_manifest.sfxmodel -- overwrites rung 7's Iviv-clone one) ===")
        print(f"written  : {result['manifest_dest']}")
        print(f"  sha256 : {result['manifest_sha256']}")
        print(f"(repo copy kept in sync at {THOMAS_MANIFEST_REPO_PATH})")
        b1 = P1_ENTRANCE_DURATION
        b2 = b1 + P2_APPROACH_DURATION
        b3 = b2 + P3_BOB_UP_DURATION
        b4 = b3 + P4_BOB_DOWN_DURATION
        b5 = b4 + P5_LATERAL_PASS_DURATION
        b6 = b5 + P6_BOB_SETTLE_DURATION
        b7 = b6 + P7_HOLD_DURATION
        b8 = b7 + P8_EXIT_CLIMB_DURATION  # == THOMAS_END
        print("THE FLIGHT v4 (8 pieces, VIEW-SPACE CHOREOGRAPHY, 2026-07-22):")
        print(f"  camera anchor : pos={vsp.CAM_POS}  eulerAngles={vsp.CAM_EULER_DEG}  (static -- BattleMapCameraController.cs:26-30)")
        print(f"  assumed FOV   : vfov={vsp.DEFAULT_VFOV_DEG} deg  aspect={vsp.DEFAULT_ASPECT:.4f}  (SHAPE is recon-cited, MAGNITUDE is a named assumption -- see viewspace_place.py)")
        print(f"  reign depth   : {REIGN_DEPTH:.1f} units (fills {TARGET_REIGN_FILL:.0%} of frame height at scale {THOMAS_SCALE})")
        print(f"  yaw broadside : {YAW_BROADSIDE} deg (camera-forward . Thomas-neutral-+Z = {YAW_FORWARD_DOT:+.4f} -- strongly positive => yaw=0 would show his BACK)")
        print(f"  P1 entrance          0-{b1}    off the upper-left edge, far -> near-center settle, descending in   sx,sy,depth*={VS_ENTRANCE_ORIGIN}->{VS_P1_DEST}")
        print(f"  P2 approach-to-reign {b1}-{b2}   push in to full reign size/position                              ->{VS_P2_DEST}")
        print(f"  P3 reign bob (up)   {b2}-{b3}  gentle breathing bob, closer/higher                                ->{VS_P3_DEST}")
        print(f"  P4 reign bob (down) {b3}-{b4}  gentle breathing bob, farther/lower                                ->{VS_P4_DEST}")
        print(f"  P5 lateral pass     {b4}-{b5}  slow drift across the frame (\"for life\")                          ->{VS_P5_DEST}")
        print(f"  P6 reign bob (settle) {b5}-{b6}  back toward center -- ground-reign/fire-column/damage-beat window ->{VS_P6_DEST}")
        print(f"  P7 reign hold       {b6}-{b7}  a steady beat immediately before the exit transition               ->{VS_P7_DEST}")
        print(f"  P8 exit climb       {b7}-{b8}  climb toward a top corner, receding into the distance              ->{VS_P8_DEST}")
        print()
        print("  absolute world XYZ actually baked into the manifest (view_to_world() output, rounded):")
        for name, xyz in (("ENTRANCE_ORIGIN", ENTRANCE_ORIGIN), ("P1_DEST", P1_DEST), ("P2_DEST", P2_DEST),
                          ("P3_DEST", P3_DEST), ("P4_DEST", P4_DEST), ("P5_DEST", P5_DEST),
                          ("P6_DEST", P6_DEST), ("P7_DEST", P7_DEST), ("P8_DEST", P8_DEST)):
            print(f"    {name:16s} = {xyz}")
        print()
        m = result["mint"]
        print(f"=== Thomas GEO mint: id={m['id']} name={m['name']} type_int={m['type_int']} ===")
        print(f"fbx      : {m['fbx_dest']}")
        print(f"  sha256 : {m['fbx_sha256']}")
        print(f"texture  : {m['tex_dest']}")
        print(f"  sha256 : {m['tex_sha256']}")
        print(f"directive: {m['directive']}  ({'ADDED this run' if m['directive_added'] else 'already present'})")
        print(f"  -> {m['dictionary_patch']}")
        print()
        if m["directive_added"]:
            print("*** NEW GEO ID -- RELAUNCH FF9 to register it (3DModel is load-time-only). ***")
            print("*** After that ONE relaunch, ef084/*.seq / FileList.txt / .sfxmodel edits above are")
            print("*** already live -- no further relaunch or redeploy needed for those.")
        else:
            print("Thomas's GEO id was already registered (no new relaunch needed for the mint); the")
            print(".seq/FileList.txt/.sfxmodel edits above are zero-cache -- recast-only.")
        print()
        print("Reminder: ef227 (the shared Bahamut donor) and every other summon/effect are UNTOUCHED.")
        print("Re-enter a battle on bench field 30300 and cast Iviv -> Spark -> Bahamut Cinema.")
    else:
        r7 = result["rung7"]
        print(f"=== ef084/ restored to rung 7's resting state (read directly from rung7-creature/) ===")
        print(f"  FileList.txt              sha256 : {r7['filelist_sha256']}")
        print(f"  creature_manifest.sfxmodel sha256 : {r7['manifest_sha256']}")
        print(f"  PlayerSequence.seq         sha256 : {r7['seq_sha256']}")
        um = result["unmint"]
        print()
        print(f"=== Thomas GEO mint ({THOMAS_GEO_NAME}, id {THOMAS_GEO_ID}) ===")
        print(f"model dir removed : {um['removed_dir']}  ({um['dest']})")
        print(f"DictionaryPatch line removed : {um['directive_removed']}  ({um['directive']!r})")
        print()
        print("ef084/ is back to rung 7's own proven resting state (FileList.txt + creature_manifest.sfxmodel")
        print("= rung 7's Iviv-clone content, PlayerSequence.seq = rung 7's 29-line sequence). Thomas's mint")
        print("is fully removed. A relaunch clears the now-unregistered GEO id from FF9BattleDB.GEO's runtime")
        print("dict (harmless either way -- nothing references it once removed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
