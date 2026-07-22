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

from ff9mapkit import config, fsutil          # noqa: E402
from ff9mapkit.models import export as mexport  # noqa: E402
from ff9mapkit.models import mint as mmint      # noqa: E402

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

# --------------------------------------------------------------------------- THE FLIGHT v3 (2026-07-22, CAMERA-DECODE REWINDOWED)
# HISTORY (superseded, kept for the record): build 1 was a static hover; build 2 (the 6-phase "SKY ARC")
# eyeballed the beats from video; FLIGHT v2 (the 11-piece build) replaced the eyeball with the s47
# mesh-probe's real per-frame medians of Bahamut's own 7 body-mesh keys -- accurate gross position, but it
# had to GUESS where the camera cuts were (a big position delta between frames is a decent cut proxy, but
# can't tell a real cut from a fast in-shot reposition). It guessed cuts at frames 172-179 (P4->P5) and
# 204-207 (P6->P7) and modeled both Linear/un-eased.
#
# THE CAMERA DECODE (``ef_camera_decode.py``, this session) removed that guess. It parses the REAL native
# ``ef227.bytes`` container's baked camera track -- SFXBinaryFile.cs's chunk/opcode-stream spec (byte-exact
# validated: the resource table sums to the file's own 823,296-byte length with zero slack) +
# SFXDataCamera.cs's Code-stream reader (the SAME parser ``battle/camera_codec.py`` already round-trips for
# raw17 stock scenes) -- and finds Bahamut Cinema is exactly **3 real camera shots**, 2 real hard cuts, on
# Thomas's own PlaySFX-zeroed clock (offset 0, cross-checked 3 independent ways against the container's own
# internal tick math -- see ``ef_camera_decode.py``'s own docstring for the citations):
#   SHOT 0  ticks   0-258   ONE unbroken dolly (camera resource chunk0/arg6) -- P1 through P8 ALL fall
#                           inside this single shot; there is NO real cut at 172-179 or 204-207, just a
#                           fast in-shot reposition the mesh-position method mistook for a cut
#   CUT 1   tick    258     the REAL first hard cut (8 ticks into old FLIGHT v2's "P9" span)
#   SHOT 1  ticks 258-483   ONE unbroken shot (camera resource chunk1/arg16) -- the charge+blast+ground-
#                           reign; both EFFECT_POINT damage beats (abs 454, 466) fall inside it
#   CUT 2   tick    483     the REAL second hard cut, into the outro
#   SHOT 2  ticks 483-514   an almost-static outro/fade keyframe (camera resource chunk1/arg47)
#
# CONFIRMED GEOMETRIC GAP (see ``ef_camera_decode.py``'s own docstring): SFXDataCamera's spherical
# (pitch/orientation/roll/distance) Position format has NO open-code conversion to a Unity world-space eye
# or look-at point -- that conversion runs inside the closed native ``FF9SpecialEffectPlugin.dll``
# (``CameraEngine.SFX_PLUGIN``, a per-frame ``[DllImport]`` call). So this rewindow does NOT replace
# Thomas's measured XYZ waypoints with camera-derived ones -- it uses the SAME P1_DEST..P10_DEST as FLIGHT
# v2 (the mesh-probe medians below), only correcting WHERE the piece boundaries/easing fall relative to
# the REAL cuts. Net changes vs FLIGHT v2:
#   1. P5 (172-179) and P7 (204-207) re-eased Linear -> Sinus: both sit INSIDE shot 0's one continuous
#      dolly -- an un-eased snap here would read as Thomas teleporting mid-shot, since no real cut covers it.
#   2. P8's hold is extended 8 ticks (207-250 -> 207-258) to reach the REAL shot-0/shot-1 boundary exactly,
#      then ONE new short Linear piece (CUT1, 258-262) carries the P8->P9 position delta FAST -- converting
#      what FLIGHT v2 modeled as a slow 164-frame drift into the real hard cut, landing Thomas already
#      "in frame" for the reign the instant the camera cuts (matching how a real edit reads).
#   3. The post-cut hold (P9, now 262-414) + P10 (414-417, unchanged) + a new flat bridging hold (P10_HOLD,
#      417-483) keep shot 1 fully continuous through to tick 483 -- no invented position jump, since the
#      measured data shows none there; the REAL cut is honored by holding until the tick it actually lands,
#      not by faking a spatial snap the data doesn't support.
#   4. The unmeasured tail (P11) now starts its SinusIn climb-away AT tick 483 (was 417 in FLIGHT v2) --
#      "the cut gives cover for a position change/motion change at that instant" per the decode's own
#      placement recommendation; the climb-away now visibly BEGINS right as the outro shot cuts in, instead
#      of already being 66 frames underway.
#
# RECONSTRUCTION METHOD for the measured waypoints (UNCHANGED from FLIGHT v2 -- PROBE.md's round-1
# results): per frame, median across the 7 creature keys of -- **X, Y: bounds CENTER** (``cx``, ``cy``);
# **Z: the FAR CORNER** (``cz +/- ez``, whichever has the larger magnitude). Far-corner is essential for Z
# (recovers true depth) but chases silhouette extremities on X/Y (which stay close enough to origin that
# there's no stable "far side") -- cross-checked: raw CENTER cy stays in [-480.5, +511.5] across all 8,764
# creature-key rows, matching the probe's own independent "Y never exceeds ~512" cluster read.
#
# ABSOLUTE WORLD COORDINATES (unchanged from FLIGHT v2): every Movement Origin*/Destination* is a PLAIN
# NUMERIC NCalc constant, not a ``CasterPosition* + N`` expression -- ``SFXMesh.Render()`` draws via
# ``Graphics.DrawMeshNow(_mesh, Matrix4x4.identity)`` (no transform), so both the native donor's Raw mesh
# and Thomas's JSON mesh share one identity world space; an absolute coordinate puts Thomas exactly where
# Bahamut's own body was measured, independent of caster-lookup quirks or camera framing.
#
# YAW / BROADSIDE (open concern, honestly unresolved): the mission asked for a per-window yaw computed from
# each shot's eye->Thomas vector (yaw toward the enemies if the camera looks along his length axis, so the
# silhouette stays readable). This is NOT computable from the decode -- see the CONFIRMED GEOMETRIC GAP
# above; there is no eye/aim world position to take a vector from, for ANY of the 3 shots, not just some.
# Falling back to the qualitative shot descriptions instead: shot 0 is a single continuous dolly (distance
# push/pull, not a bearing change) -- a fixed viewing angle the whole shot, so if YAW_BROADSIDE=90 (length
# on world X, perpendicular to a Z-ish depth-dolly view axis) reads correctly at the start it should read
# correctly throughout; shot 1 is the charge+blast hero shot (broadside is the deliberately-designed framing
# the whole build has assumed since FLIGHT v1); shot 2 is a near-static outro during which the model ALREADY
# turns him back to forward-facing (yaw 90->0) as he climbs away -- exactly the departure framing a static
# outro camera would want. Net: NO per-window yaw deviation is introduced here (still 0->90 bank-in during
# P1, HOLD 90 through shots 0+1, 90->0 bank-out during the tail) -- the same scheme FLIGHT v2 used, now
# understood to already match what the decode's own qualitative shot descriptions imply, rather than an
# unexamined carryover. A future round that fixes the DLL-side gap (or gets a fresh camera log once the
# CAM-hook defect is fixed, PROBE.md's round-2 protocol item 5) could compute this for real.
#
# THE REWINDOWED FLIGHT (13 pieces: the same 10 measured + 1 unmeasured-tail waypoints as FLIGHT v2, plus 1
# new hard-cut piece and 1 new bridging hold), summing to THOMAS_END=580 unchanged:
#   P1  ENTRANCE          0-82     swoop in (pre-log; Origin unmeasured) -> the measured cave-shot settle    [SHOT 0]
#   P2  RISE-TO-FAR      82-144    climbs away in DEPTH -- the first sky/far shot                            [SHOT 0]
#   P3  FAR-DIP         144-157    a brief mid-act partial return                                            [SHOT 0]
#   P4  FAR-DEEP        157-172    the cast's single deepest point + a brief hold                            [SHOT 0]
#   P5  RETURN-DRIFT    172-179    re-eased Sinus (was Linear) -- NO real cut here, still shot 0             [SHOT 0]
#   P6  2ND-APPROACH    179-204    a second, shallower re-plunge                                              [SHOT 0]
#   P7  CHARGE-DRIFT    204-207    re-eased Sinus (was Linear) -- NO real cut here, still shot 0              [SHOT 0]
#   P8  CHARGE-HOLD     207-258    extended +8 ticks (was 207-250) to reach the REAL shot boundary exactly   [SHOT 0]
#   CUT1 (NEW)          258-262    THE real hard cut -- Linear, fast P8_DEST->P9_DEST snap                   [cut]
#   P9  GROUND-REIGN    262-414    post-cut hold at P9_DEST -- fire column + both damage beats               [SHOT 1]
#   P10 EXIT-EDGE       414-417    sharp final recess (unchanged from FLIGHT v2)                             [SHOT 1]
#   P10_HOLD (NEW)      417-483    flat bridging hold to the REAL 2nd cut tick (was silently absorbed into   [SHOT 1]
#                                  FLIGHT v2's tail SinusIn before)
#   P11 TAIL (tail)     483-580    unmeasured climb-away, now STARTS/accelerates right at the real cut       [SHOT 2]
#
# CAVEAT (carried forward from FLIGHT v2's round-1 analysis + the adversarial-verification correction --
# see PROBE.md "Sample-count correction"; NOT re-checked in-game against THIS rewindow):
#   (a) P5_DEST (179)/P7_DEST (207) are each backed by a full n=28 rows -- solid points; the actually
#       sparse/gappy region is frames ~153-177 (inside P3/P4), and P4_DEST itself (172, the single deepest/
#       most dramatic pose) is the real n=4 low-confidence measurement.
#   (b) P1's Origin (frame 0, pre-log) and the TAIL's Destination (P11_TAIL_DEST) have ZERO measured ground
#       truth -- both REASONED EXTRAPOLATIONS (see ENTRANCE_ORIGIN / P11_TAIL_DEST below), unconfirmed
#       against a fresh video/log of THIS build (this project's video-for-visual-bugs law).
#   (c) Clock alignment (probe/container tick ~= Thomas frame, offset 0) is a REASONED assumption, now
#       backed by the camera decode's own 3-way internal cross-check (container total ticks=514 and the
#       first camera's fire tick=14 both match the s47 probe's independently-logged cast bounds
#       frames~11-510/515 within 2-4 ticks) -- stronger than FLIGHT v2's bare assumption, still not a
#       literal re-measurement against THIS exact build. Treat +/-2-5 frames as realistic slop.
#   (d) The CUT1/CUT2 tick placements (258, 483) themselves carry the decode's own PARTIAL confidence --
#       SOLID on the container-parse + clock-alignment side, but the decode could not independently
#       re-verify against a fresh camera log (the s47 CAM-hook defect, PROBE.md, means no camera log exists
#       for THIS engine build to cross-check the container's baked ticks against real playback).
#   (e) Absolute-world Z DECREASES (more negative) as Bahamut flies "away" -- unrelated to any caster-
#       relative sign convention from earlier builds; nobody should reverse-engineer a caster position from
#       this sign.
#
#   Every number below is a named constant -- retune and rerun (recast-only, no relaunch) in one line.
VIDEO_TO_FRAME_OFFSET_S = 6      # Thomas's own PlaySFX/frame-0, video-seconds (per the mission's own t~=6+frame/15 map)
FRAMES_PER_VIDEO_SECOND = 15     # Thomas's own clock rate (same source)

# Measured piece destinations -- (X, Y, Z) absolute world coords, PROBE.md's round-1 per-frame medians
# (X/Y = bounds center, Z = far corner) at each piece boundary frame, rounded to the nearest whole unit.
P1_DEST = (132, 512, -1568)          # frame 82  -- cave-shot entrance settle (PROBE.md's own table: -1568, not
                                      # -1600 -- a transcription slip caught + fixed during adversarial verification,
                                      # 2026-07-22 round 2; the raw log's own median is unambiguous, see verify below)
P2_DEST = (129, 128, -17860)         # frame 144 -- rise-to-far, first sky/far shot
P3_DEST = (6, -20, -8590)            # frame 157 -- the mid-act partial-return dip
P4_DEST = (-266, -425, -34368)       # frame 172 -- the cast's single deepest point + brief hold (n=4 rows,
                                      # the real low-confidence point in this reconstruction -- see CAVEAT a)
P5_DEST = (144, 47, -4864)           # frame 179 -- THE hard return-cut (n=28 rows, solid -- see CAVEAT a)
P6_DEST = (143, 124, -12336)         # frame 204 -- the second, shallower re-plunge
P7_DEST = (152, 202, -4720)          # frame 207 -- the second hard cut back to near-stage (n=28 rows, solid -- see CAVEAT a)
P8_DEST = (120, 118, -3968)          # frame 250 -- Mega-Flare charge+blast, held NEAR-STAGE
P9_DEST = (35, -1, -3832)            # frame 414 -- long ground-reign drift settle
P10_DEST = (35, -1, -9616)           # frame 417 -- body's last logged position, sharp final recess

# P1 ENTRANCE origin (frame 0, PRE-LOG -- unmeasured, see CAVEAT b): a REASONED EXTRAPOLATION, not a
# measurement. Preserves build 2's own "high, off-side" entrance SHAPE by re-applying that build's own
# caster-relative delta (its ENTRANCE offset minus its CAVE_STAGE offset = (-2000, +800, -1500)) to the
# NEWLY MEASURED P1_DEST, rather than re-guessing a fresh shape from nothing.
ENTRANCE_ORIGIN = (P1_DEST[0] - 2000, P1_DEST[1] + 800, P1_DEST[2] - 1500)

# TAIL destination (piece runs ticks 483-580 under FLIGHT v3 -- starts at the real 2nd camera cut, was
# 417-580 in FLIGHT v2; UNMEASURED either way, see CAVEAT b): no creature-key rows exist past frame 417,
# so there's no ground truth for this piece regardless of where it starts. A REASONED continuation of
# P10's own recess (still climbing away / receding further), carrying forward build 2's own EXIT_Y=1600
# magnitude and its SinusIn "accelerating departure" intent -- X holds near the trend's own converged
# value (~35, matching frames 400-417), Z recedes further into the distance (shallower than P4's own
# measured -34368 record, so this reads as "leaving" rather than "returning to the same deep point").
# Flagged for round 2 -- a fresh log/video of frames 417-580 specifically (PROBE.md's round-2 protocol)
# should replace this with real data.
P11_TAIL_DEST = (35, 1600, -30000)

# Yaw (Rotation.Y): P1 banks 0 (his normalized-forward, facing the enemies) -> 90 (broadside) as he
# arrives at P1_DEST, then HOLDS broadside from P2 all the way through P10_HOLD (the mission's own
# instruction -- also his iconic "number 1" side panel, per README's axis-verification renders), then
# 90 -> 0 only in the TAIL as he turns forward again to climb away. Rotation.Z stays 0 in every piece --
# NO roll (he is not PSX-inverted; README's own axis-verification already established his normalized
# Rotation=(0,0) needs no runtime compensation).
YAW_BROADSIDE = 90

# Tick-map phase lengths (frames, on Thomas's own PlaySFX-zeroed clock) -- boundaries are now the REAL
# camera-shot structure (ef_camera_decode.py): shot 0 spans 0-258 (P1..P8, ONE continuous dolly), CUT1 is
# the real hard cut at 258, shot 1 spans 258-483 (P9/P10/the bridging hold), CUT2's "cut" is realized as
# the tail's motion BEGINNING exactly at 483 (no invented spatial jump -- the measured data shows none),
# shot 2 (the outro) runs 483-580. Sum = THOMAS_END = the FBX entry's own End, unchanged at 580.
P1_ENTRANCE_DURATION = 82           # frames 0-82:     swoop in (pre-log entrance -> the measured settle)          [SHOT 0]
P2_RISE_TO_FAR_DURATION = 62        # frames 82-144:   climbs away in depth to the first sky/far shot               [SHOT 0]
P3_FAR_DIP_DURATION = 13            # frames 144-157:  the mid-act partial-return dip                               [SHOT 0]
P4_FAR_DEEP_DURATION = 15           # frames 157-172:  the deepest point + brief hold (iconic close-up)             [SHOT 0]
P5_RETURN_DRIFT_DURATION = 7        # frames 172-179:  re-eased Sinus (was "RETURN_CUT"/Linear -- NO real cut here) [SHOT 0]
P6_SECOND_APPROACH_DURATION = 25    # frames 179-204:  the second, shallower re-plunge                              [SHOT 0]
P7_CHARGE_DRIFT_DURATION = 3        # frames 204-207:  re-eased Sinus (was "CHARGE_CUT"/Linear -- NO real cut here) [SHOT 0]
P8_CHARGE_HOLD_DURATION = 51        # frames 207-258:  EXTENDED +8 (was 43/207-250) to reach the REAL cut exactly   [SHOT 0]
CUT1_DURATION = 4                   # frames 258-262:  NEW -- THE real hard cut, fast Linear P8_DEST->P9_DEST snap  [cut]
P9_GROUND_REIGN_DURATION = 152      # frames 262-414:  post-cut hold at P9_DEST (was 164/250-414 -- CUT1 now owns   [SHOT 1]
                                     #                  the P8->P9 delta, so this piece is a flat post-cut hold)
P10_EXIT_EDGE_DURATION = 3          # frames 414-417:  the sharp final recess (last logged body frames, unchanged)  [SHOT 1]
P10_HOLD_DURATION = 66              # frames 417-483:  NEW -- flat bridging hold to the REAL 2nd cut tick (was      [SHOT 1]
                                     #                  silently absorbed into FLIGHT v2's tail SinusIn before)
P11_TAIL_DURATION = 97              # frames 483-580:  UNMEASURED climb-away, now STARTS at the real 2nd cut (was   [SHOT 2]
                                     #                  163/417-580 in FLIGHT v2 -- see CAVEAT b)
THOMAS_END = (P1_ENTRANCE_DURATION + P2_RISE_TO_FAR_DURATION + P3_FAR_DIP_DURATION + P4_FAR_DEEP_DURATION
              + P5_RETURN_DRIFT_DURATION + P6_SECOND_APPROACH_DURATION + P7_CHARGE_DRIFT_DURATION
              + P8_CHARGE_HOLD_DURATION + CUT1_DURATION + P9_GROUND_REIGN_DURATION + P10_EXIT_EDGE_DURATION
              + P10_HOLD_DURATION + P11_TAIL_DURATION)   # 580, unchanged

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
    -- no ``CasterPosition*`` anchor needed under the absolute-world-coordinate design, see THE FLIGHT v3
    comment above)."""
    x, y, z = xyz
    return {"DestinationX": str(x), "DestinationY": str(y), "DestinationZ": str(z)}


def build_manifest_json() -> dict:
    """Generate ``thomas_manifest.sfxmodel``'s JSON from the named FLIGHT v3 constants above (schema
    verified against ``ParametricMovement.LoadFromJSON``, Memoria/Battle/SFX/ParametricMovement.cs:
    58-136 -- an array of pieces, ``Duration`` + per-axis ``Origin*``/``Destination*``/
    ``InterpolationType*``; an absent ``Origin*`` key on piece i>0 CHAINS from the prior piece's own
    ``Destination*`` expression -- used below for pieces 2-13 of both Movement and Rotation). 13 pieces,
    one group per REAL camera shot (ef_camera_decode.py) with the 2 real hard cuts as their own explicit
    short Linear pieces: SHOT 0 (P1..P8, ticks 0-258, one continuous dolly -- SinusOut/SinusIn/Sinus
    throughout, NO Linear inside it) -> CUT1 (258-262, the one deliberate Linear snap, timed to the real
    cut) -> SHOT 1 (P9/P10/P10_HOLD, ticks 262-483, the charge+blast+ground-reign, gentle Sinus/SinusIn
    holds) -> SHOT 2 (P11 TAIL, ticks 483-580, the reasoned climb-away, starting right at the real 2nd
    cut). Every Destination is always given explicitly (never relied on the dest-defaults-to-origin
    fallback) so the JSON stays self-documenting. Scaling is unchanged (constant THOMAS_SCALE, one piece
    spanning the whole THOMAS_END, no motion needed)."""
    movement = [
        {   # P1 ENTRANCE [SHOT 0]: unmeasured origin (reasoned extrapolation, see CAVEAT b) -> the
            # measured frame-82 cave-shot settle
            "Duration": str(P1_ENTRANCE_DURATION),
            "OriginX": str(ENTRANCE_ORIGIN[0]), "OriginY": str(ENTRANCE_ORIGIN[1]), "OriginZ": str(ENTRANCE_ORIGIN[2]),
            **_pt(P1_DEST),
            "InterpolationTypeX": "SinusOut", "InterpolationTypeY": "SinusOut", "InterpolationTypeZ": "SinusOut",
        },
        {   # P2 RISE-TO-FAR [SHOT 0]: climbs away in depth to the first sky/far shot (Origin chained
            # from P1's Destination)
            "Duration": str(P2_RISE_TO_FAR_DURATION),
            **_pt(P2_DEST),
            "InterpolationTypeX": "SinusIn", "InterpolationTypeY": "SinusIn", "InterpolationTypeZ": "SinusIn",
        },
        {   # P3 FAR-DIP [SHOT 0]: a brief mid-act partial return -- still inside the one continuous dolly
            "Duration": str(P3_FAR_DIP_DURATION),
            **_pt(P3_DEST),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P4 FAR-DEEP [SHOT 0]: the cast's single deepest point + a brief hold -- the iconic hover/
            # close-up moment, still inside shot 0
            "Duration": str(P4_FAR_DEEP_DURATION),
            **_pt(P4_DEST),
            "InterpolationTypeX": "SinusIn", "InterpolationTypeY": "SinusIn", "InterpolationTypeZ": "SinusIn",
        },
        {   # P5 RETURN-DRIFT [SHOT 0]: re-eased Sinus (was Linear in FLIGHT v2) -- the camera decode found
            # NO real cut here, just a fast in-shot reposition inside the one continuous dolly; an un-eased
            # snap here (with no real cut to cover it) would read as Thomas teleporting mid-shot
            "Duration": str(P5_RETURN_DRIFT_DURATION),
            **_pt(P5_DEST),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P6 2ND-APPROACH [SHOT 0]: a second, shallower re-plunge during the charge windup
            "Duration": str(P6_SECOND_APPROACH_DURATION),
            **_pt(P6_DEST),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P7 CHARGE-DRIFT [SHOT 0]: re-eased Sinus (was Linear) -- same correction as P5, still shot 0
            "Duration": str(P7_CHARGE_DRIFT_DURATION),
            **_pt(P7_DEST),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P8 CHARGE-HOLD [SHOT 0]: Mega-Flare charge+blast, held NEAR-STAGE -- duration EXTENDED +8
            # ticks vs FLIGHT v2 so this piece's own end lands exactly on the REAL shot-0/shot-1 boundary
            "Duration": str(P8_CHARGE_HOLD_DURATION),
            **_pt(P8_DEST),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # CUT1 [the real hard cut]: NEW piece -- a fast Linear snap from P8_DEST to P9_DEST, landing
            # exactly on the camera decode's own real cut tick (258). This is the ONE deliberate un-eased
            # moment in the whole flight now, replacing FLIGHT v2's 164-frame slow drift between the same
            # two points with the snap the real edit actually performs.
            "Duration": str(CUT1_DURATION),
            **_pt(P9_DEST),
            "InterpolationTypeX": "Linear", "InterpolationTypeY": "Linear", "InterpolationTypeZ": "Linear",
        },
        {   # P9 GROUND-REIGN [SHOT 1]: post-cut hold at P9_DEST -- fire column + both damage beats land
            # inside this shot; gentle Sinus (a floaty near-stage hover, not a rigid freeze)
            "Duration": str(P9_GROUND_REIGN_DURATION),
            **_pt(P9_DEST),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P10 EXIT-EDGE [SHOT 1]: the body's last logged position -- a sharp final recess, unchanged
            # from FLIGHT v2, still well inside shot 1 (the real cut is still 66 ticks away)
            "Duration": str(P10_EXIT_EDGE_DURATION),
            **_pt(P10_DEST),
            "InterpolationTypeX": "SinusIn", "InterpolationTypeY": "SinusIn", "InterpolationTypeZ": "SinusIn",
        },
        {   # P10_HOLD [SHOT 1]: NEW bridging piece -- a gentle Sinus hold at the recessed P10_DEST,
            # filling shot 1 all the way to the REAL 2nd cut tick (483) instead of letting FLIGHT v2's tail
            # SinusIn silently absorb this span
            "Duration": str(P10_HOLD_DURATION),
            **_pt(P10_DEST),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P11 TAIL [SHOT 2, the outro]: UNMEASURED -- a reasoned climb-away continuation, now
            # STARTING/accelerating exactly at the real 2nd cut tick (483) rather than 66 ticks early
            # (see CAVEAT b)
            "Duration": str(P11_TAIL_DURATION),
            **_pt(P11_TAIL_DEST),
            "InterpolationTypeX": "SinusIn", "InterpolationTypeY": "SinusIn", "InterpolationTypeZ": "SinusIn",
        },
    ]
    rotation = [
        {   # P1: bank from his normalized-forward (0, faces the enemies) to broadside (90) on arrival
            "Duration": str(P1_ENTRANCE_DURATION),
            "OriginY": "0", "DestinationY": str(YAW_BROADSIDE),
            "OriginZ": "0", "DestinationZ": "0",
            "InterpolationTypeY": "Sinus",
        },
        {"Duration": str(P2_RISE_TO_FAR_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P3_FAR_DIP_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P4_FAR_DEEP_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P5_RETURN_DRIFT_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P6_SECOND_APPROACH_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P7_CHARGE_DRIFT_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P8_CHARGE_HOLD_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(CUT1_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P9_GROUND_REIGN_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P10_EXIT_EDGE_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {"Duration": str(P10_HOLD_DURATION), "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0"},
        {   # P11 TAIL: turn back to forward-facing as he climbs away -- see the YAW / BROADSIDE comment
            # above for why no per-shot yaw deviation was computed (the DLL-side eye/aim gap)
            "Duration": str(P11_TAIL_DURATION),
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
        b2 = b1 + P2_RISE_TO_FAR_DURATION
        b3 = b2 + P3_FAR_DIP_DURATION
        b4 = b3 + P4_FAR_DEEP_DURATION
        b5 = b4 + P5_RETURN_DRIFT_DURATION
        b6 = b5 + P6_SECOND_APPROACH_DURATION
        b7 = b6 + P7_CHARGE_DRIFT_DURATION
        b8 = b7 + P8_CHARGE_HOLD_DURATION
        bc1 = b8 + CUT1_DURATION
        b9 = bc1 + P9_GROUND_REIGN_DURATION
        b10 = b9 + P10_EXIT_EDGE_DURATION
        b10h = b10 + P10_HOLD_DURATION
        b11 = b10h + P11_TAIL_DURATION  # == THOMAS_END
        print("THE FLIGHT v3 (13 pieces, CAMERA-DECODE REWINDOWED, 2026-07-22):")
        print(f"  [SHOT 0: real camera ticks 0-258, ONE continuous dolly -- no real cut inside it]")
        print(f"  P1  entrance        0-{b1}    swoop in (unmeasured origin) -> the measured cave-shot settle")
        print(f"  P2  rise-to-far   {b1}-{b2}   climbs away in depth -- the first sky/far shot")
        print(f"  P3  far-dip       {b2}-{b3}  a brief mid-act partial-return dip")
        print(f"  P4  far-deep      {b3}-{b4}  the cast's single deepest point + a brief hold")
        print(f"  P5  return-drift  {b4}-{b5}  re-eased Sinus (was Linear) -- NO real cut here")
        print(f"  P6  2nd-approach  {b5}-{b6}  a second, shallower re-plunge")
        print(f"  P7  charge-drift  {b6}-{b7}  re-eased Sinus (was Linear) -- NO real cut here")
        print(f"  P8  charge-hold   {b7}-{b8}  Mega-Flare charge+blast -- extended +8 to reach the real cut")
        print(f"  [CUT 1: the REAL hard cut, camera tick {b8}]")
        print(f"  CUT1 (fast/Linear)  {b8}-{bc1}  the one deliberate snap, P8_DEST->P9_DEST")
        print(f"  [SHOT 1: real camera ticks {b8}-483, the charge+blast+ground-reign]")
        print(f"  P9  ground-reign  {bc1}-{b9}  post-cut hold -- fire column + both damage beats")
        print(f"  P10 exit-edge    {b9}-{b10}  sharp final recess (last logged body frames)")
        print(f"  P10_hold        {b10}-{b10h}  bridging hold to the real 2nd cut tick (483)")
        print(f"  [CUT 2 / SHOT 2: the REAL 2nd hard cut + outro, camera tick 483-514]")
        print(f"  P11 tail (UNMEASURED) {b10h}-{b11}  climb-away STARTS at the real cut -- see PROBE.md round-2 protocol")
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
