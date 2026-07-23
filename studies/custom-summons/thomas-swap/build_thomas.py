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
     the ``KEYFRAMES_V10`` constant below by ``build_manifest_json()`` -- an IN-FRAME-BY-CONSTRUCTION
     flight solved against the real per-frame camera, see THE FLIGHT v7 below; the repo copy is kept in
     sync so it stays git-diffable) -> that same filename (OVERWRITING rung 7's own Iviv-clone manifest
     at that path -- ``--restore`` puts rung 7's back).
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
section, and the local-only provenance note. See PROBE.md for the mesh-probe key classification and
flight_v7_solve.py for THE FLIGHT v7 solve this build's placement is derived from (matrix_solve.py
supplies the projection primitives both v5 and v7 share).

THE FLIGHT v7 (2026-07-22, IN-FRAME BY CONSTRUCTION -- THE FINAL PRAGMATIC ROUND; supersedes v1-v5, see
THE FLIGHT v7 comment block below the constants for the full case). The goal changed: tracking Bahamut's
own real position (v5) is technically sound but reads as mostly EMPTY (his body is off-screen ~97-99% of
the real cast -- the camera follows the blast, not the creature), and separately, tracking him via the
native primitive stream directly was tried and FALSIFIED this round (no stable discriminator isolates his
creature in the raw primitives). The mission is now explicit: THOMAS VISIBLE AND DRAMATIC THROUGHOUT, a
promo shot, not a fidelity exercise -- the user accepted this trade. What stays sound (unchanged from v5):
Thomas's world position projects correctly through the s50 probe's real per-frame VIEW/PROJ (he's an
ordinary GameObject on the real render pipeline) -- only "where do I put him" changes. THE FLIGHT v7
instead CONSTRUCTS a target on-screen position + apparent size per story beat, solves the real-camera
depth that hits it, back-projects to world, and recursively densifies with extra keyframes wherever the
real camera log's own drift would carry him out of frame between beats -- verified, not assumed (61/61
final segments in-margin). ``viewspace_place.py`` (v4) and ``ef_camera_decode.py``/``ef_camera_solve.py``
(v3) remain retained only as the superseded record; matrix_solve.py (v5's own solver) is still imported
by flight_v7_solve.py for its projection primitives, not for Bahamut-tracking.
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
# THE FLIGHT v10 (MEASURED POSITION + SIZE, 2026-07-23) bakes KEYFRAMES_V10 below; the tool that DERIVED them
# is flight_v10_solve.py (this dir). v9 gave the creature's real per-frame screen POSITION; v10 adds its real
# per-frame SIZE (apparent height WORLD_H*native_H/depth from the s53 BONES AABB -> Thomas scales down during
# the swoop). The s53 probe + FORMAT round recovered the creature's REAL per-frame screen
# position (reproject its composed node-0 through the NATIVE GTE M+OFX/OFY/H); v9 places Thomas at that screen
# position, back-projected through the MANAGED camera (one keyframe/frame). -- see the README's FLIGHT v9
# section + PROBE.md sec 10). flight_v7_solve.py remains the reused machinery (imports matrix_solve.py for the shared
# projection primitives). build-time needs no game log or either superseded v3/v4 module.

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

# --------------------------------------------------------------------------- THE FLIGHT v7 (2026-07-22, IN-FRAME BY CONSTRUCTION -- THE FINAL PRAGMATIC ROUND)
# THE PIVOT (user-accepted trade). FLIGHT v5 (TRACK BAHAMUT -- see matrix_solve.py, kept for the record)
# was internally sound -- Thomas is an ordinary GameObject whose world position is force-set every frame
# and rendered by the real per-frame camera (SFXDataMesh.cs:820), so projecting his world position through
# the logged VIEW/PROJ correctly predicts where he lands on screen -- but its PREMISE ("faithful = wherever
# Bahamut's own body was, off-screen swoops included") produces a promo clip that is mostly EMPTY:
# matrix_solve.py's own self-test measures only ~4/323 (1.2%) of Bahamut's own measured frames landing
# on-screen; the deployed v5 build scored ~2.7% (9/336) on-screen coverage end to end. Separately, TRACKING
# Bahamut himself via the native PS1-primitive stream (rather than the mesh-bounds proxy) was tried and
# FALSIFIED this round -- no stable discriminator isolates his creature in the raw primitive stream, and
# the two video-confirmed beats (swirl entrance, fire column) contain ZERO body-key primitives. The goal is
# now explicit and different: THOMAS VISIBLE AND DRAMATIC THROUGHOUT -- a promo shot, not a fidelity
# exercise.
#
# WHAT STAYS SOUND (unchanged from v5, re-used verbatim, not re-derived): the captured per-frame
# camera.worldToCameraMatrix (VIEW)/camera.projectionMatrix (PROJ) pair from the s50 probe IS the real
# render camera for THIS cast, and a world point projects through it correctly (matrix_solve.py's
# round-trip self-test, empirically corroborated against the user's own video). Only "where do I put
# Thomas" changes -- not the projection math.
#
# THE METHOD -- construct in NDC, back-project to world (studies/custom-summons/thomas-swap/
# flight_v7_solve.py -- full derivation + module docstring; re-run it to reproduce every number below):
#   1. author a target on-screen position (ndc_x, ndc_y, comfortably inside frame) and an apparent HEIGHT
#      fraction of the frame (~45-65%) at each of 18 story "beats" spanning frames 0..580 (a swooping
#      entrance from a frame edge -> center-stage reign w/ gentle bob+charge -> a slow lateral pass -> BIG
#      AND PRESENT through the fire-column/aftermath window 430-540 (the beats the user liked -- no
#      receding/climbing away there, unlike v5's exit piece) -> a short exit);
#   2. solve the camera-space depth that makes Thomas's own scaled height actually fill that fraction
#      under THAT FRAME's real PROJ[1][1] (the vertical focal term sweeps ~2.33..4.65 across the cast --
#      zoom means the SAME height fraction needs a DIFFERENT depth at every beat, the main thing to get
#      right per the mission);
#   3. back-project (ndc_x, ndc_y, view_z=-depth) through THAT FRAME's real VIEW+PROJ
#      (matrix_solve.world_from_ndc, the general off-center-frustum inverse, round-trip exact);
#   4. derive YAW per keyframe from the camera's own forward vector (broadside presentation to THAT
#      frame's actual camera -- closes the "fixed yaw drifts as the camera pans" open item both v4 and v5
#      left unresolved).
#
# WHY 62 KEYFRAMES, NOT ~14-18 (an honest, MEASURED deviation, not scope creep). The 18 authored beats
# above are still all present below (their own labels survive verbatim) as the mandatory story waypoints.
# But directly checking a hand-picked ~16-beat arc against the REAL camera log found this cast's camera is
# CUT-HEAVY, not smoothly panning as the mission's own drift-margin language assumes: dozens of single-
# FRAME eye jumps of 2000-22000 world units (real hard cuts -- flight_v7_solve.camera_eye_census finds 15
# jumps over 2000 units alone) interleaved with a few sustained fast continuous dolly/orbit shots. A
# straight Linear-in-world interpolation between two in-frame beats, sampled at the REAL intermediate-frame
# cameras, blew the |ndc|<1 envelope by 10-75x on more than half of the first attempt's segments -- not a
# rounding error, a wrong premise (linear-in-world only tracks linear-in-camera). flight_v7_solve.py fixes
# this by treating each beat as mandatory and RECURSIVELY BISECTING any segment whose real-camera drift
# would exceed DRIFT_LIMIT=0.85, inserting exactly as many extra keyframes as the log demands (each
# insertion computed as intended-screen-position lerp -> its own real depth/back-projection, same method as
# every authored beat) -- verified, not assumed: the final build is 61/61 segments within the 0.85 |ndc|
# margin, worst point anywhere 0.83. 44 of the 62 keyframes are these adaptive drift-inserts (labeled
# "(auto -- drift insert)" in the table); every one is a measured necessity against the real log, not a
# guess. Re-derive with `py flight_v7_solve.py`.
#
# INTERPOLATION: every Movement/Rotation piece below is Linear (no Sinus/SinusIn/SinusOut anywhere) --
# deliberately, because the drift verification above was performed assuming Linear interpolation between
# consecutive keyframes; introducing easing would make the DEPLOYED runtime path diverge from the path
# that was actually checked, silently invalidating the in-frame guarantee. The entrance/exit already read
# as smooth swoops because the adaptive bisection naturally packs keyframes densely right where the
# camera moves fastest (see frames 0-30 and 400-430 below).
#
# SHIFTWORLD: still a non-issue (SFXDataMesh.cs:820 force-assigns absolute world position every frame,
# Thomas is never parented under battlebg.btlRoot) -- these world coords are used VERBATIM.
#
# CAVEAT: per this project's own video-for-visual-bugs law, a fresh capture of an actual cast is the real
# next check -- this is a DESIGN verified against the real camera log's OWN geometry (matrix_solve.py's
# projection math + flight_v7_solve.py's drift check), not a claim to have watched it play.

# --- KEYFRAMES_V10: (frame,(worldX,Y,Z),yaw) -- flight_v10_solve.py's MEASURED POSITION + SIZE, 334 keyframes.
# --- v9 nailed the creature's real per-frame SCREEN POSITION; v10 adds its real per-frame SIZE (apparent
# --- height = WORLD_H*native_H/depth from the s53 BONES AABB): Thomas shrinks to ~0.2x during the far swoop
# --- and fills the frame up close, capped [0.18,0.70]. The varying placement DEPTH also gives real 3D motion
# --- (v9's constant size read as a flat 2D tween). Position + every-frame keyframes unchanged from v9.
# --- Generated -- re-run flight_v10_solve.py; see README FLIGHT v10 + PROBE.md sec 11. ---
KEYFRAMES_V10: "tuple[tuple[int, tuple[int, int, int], float], ...]" = (
    (   0, (    866,    2181,    -2853), +240.42),  # lead-in (flying down)
    (  82, (  -1509,    2122,     -971), +185.27),  # measured f82
    (  83, (  -1504,    2122,     -832), +185.27),  # measured f83
    (  84, (  -1468,    2122,     -548), +185.27),  # measured f84
    (  85, (  -1481,    2122,     -691), +185.27),  # measured f85
    (  86, (  -1140,    2138,     -672), +185.27),  # measured f86
    (  87, (   -895,    2150,     -613), +185.27),  # measured f87
    (  88, (   -736,    2158,     -612), +185.27),  # measured f88
    (  89, (   -605,    2163,     -564), +185.27),  # measured f89
    (  90, (   -545,    2166,     -567), +185.27),  # measured f90
    (  91, (   -448,    2170,     -487), +185.27),  # measured f91
    (  92, (   -410,    2173,     -464), +185.27),  # measured f92
    (  93, (   -337,    2176,     -442), +185.27),  # measured f93
    (  94, (   -311,    2177,     -441), +185.27),  # measured f94
    (  95, (   -295,    2178,     -376), +185.27),  # measured f95
    (  96, (   -269,    2179,     -350), +185.27),  # measured f96
    (  97, (   -265,    2179,     -335), +185.27),  # measured f97
    (  98, (   -233,    2179,     -301), +185.27),  # measured f98
    (  99, (   -228,    2180,     -271), +185.27),  # measured f99
    ( 100, (   -224,    2180,     -247), +185.27),  # measured f100
    ( 101, (   -224,    2181,     -248), +185.27),  # measured f101
    ( 102, (   -228,    2180,     -206), +185.27),  # measured f102
    ( 103, (   -221,    2180,     -175), +185.27),  # measured f103
    ( 104, (   -216,    2180,     -158), +185.27),  # measured f104
    ( 105, (   -215,    2180,     -135), +185.27),  # measured f105
    ( 106, (   -215,    2180,     -117), +185.27),  # measured f106
    ( 107, (   -209,    2180,      -86), +185.27),  # measured f107
    ( 108, (   -222,    2180,      -74), +185.27),  # measured f108
    ( 109, (   -208,    2180,      -49), +185.27),  # measured f109
    ( 110, (   -201,    2181,      -41), +185.27),  # measured f110
    ( 111, (   -200,    2181,      -13), +185.27),  # measured f111
    ( 112, (   -192,    2181,        0), +185.27),  # measured f112
    ( 113, (   -180,    2181,       19), +185.27),  # measured f113
    ( 114, (   -171,    2182,       33), +185.27),  # measured f114
    ( 115, (   -173,    2182,       48), +185.27),  # measured f115
    ( 116, (   -159,    2120,       57), +185.27),  # measured f116
    ( 117, (   -123,    1703,       61), +185.27),  # measured f117
    ( 118, (    -94,    1296,       70), +185.27),  # measured f118
    ( 119, (    -66,     906,       72), +185.27),  # measured f119
    ( 120, (    -40,     542,       76), +185.27),  # measured f120
    ( 121, (     -9,     212,       61), +185.27),  # measured f121
    ( 122, (      6,     -80,       64), +185.27),  # measured f122
    ( 123, (     18,    -326,       67), +185.27),  # measured f123
    ( 124, (     41,    -522,       45), +185.27),  # measured f124
    ( 125, (     46,    -665,       44), +185.27),  # measured f125
    ( 126, (     48,    -666,       42), +185.27),  # measured f126
    ( 127, (     65,    -665,       18), +185.27),  # measured f127
    ( 128, (      0,    1704,      288),  +90.00),  # measured f128
    ( 129, (      0,    1728,      276),  +90.00),  # measured f129
    ( 130, (    -44,    1843,      214),  +90.46),  # measured f130
    ( 131, (    -45,    2011,      108),  +91.54),  # measured f131
    ( 132, (    -40,    2172,      -12),  +92.64),  # measured f132
    ( 133, (    -40,    2319,     -138),  +93.73),  # measured f133
    ( 134, (    -48,    2445,     -263),  +94.75),  # measured f134
    ( 135, (    -57,    2456,     -362),  +95.79),  # measured f135
    ( 136, (    -57,    2407,     -424),  +96.76),  # measured f136
    ( 137, (    -59,    2373,     -470),  +97.62),  # measured f137
    ( 138, (    -63,    2348,     -509),  +98.47),  # measured f138
    ( 139, (    -59,    2331,     -540),  +99.19),  # measured f139
    ( 140, (    -67,    2320,     -563),  +99.85),  # measured f140
    ( 141, (    -66,    2314,     -583), +100.42),  # measured f141
    ( 142, (    -67,    2307,     -596), +100.88),  # measured f142
    ( 143, (    -71,    2305,     -607), +101.23),  # measured f143
    ( 144, (    -77,    2301,     -613), +101.49),  # measured f144
    ( 145, (    -78,    2259,     -587), +101.63),  # measured f145
    ( 146, (    -85,    2195,     -543), +101.83),  # measured f146
    ( 147, (    -89,    2142,     -508), +102.21),  # measured f147
    ( 148, (    -89,    2079,     -464), +102.63),  # measured f148
    ( 149, (    -97,    2012,     -410), +103.06),  # measured f149
    ( 150, (   -111,    1943,     -349), +103.53),  # measured f150
    ( 151, (   -120,    1864,     -275), +104.02),  # measured f151
    ( 152, (   -141,    1768,     -174), +104.57),  # measured f152
    ( 153, (   -512,    1603,     5543), +230.60),  # gap f153
    ( 154, (   -534,    2318,     5564), +230.60),  # gap f154
    ( 155, (   -534,    2318,     5548), +230.60),  # gap f155
    ( 156, (   -534,    2317,     5531), +230.60),  # measured f156
    ( 157, (   -630,    2317,     5437), +230.60),  # measured f157
    ( 158, (  -2286,    1776,     4026), +230.60),  # measured f158
    ( 159, (  -3050,    1505,     3365), +230.60),  # measured f159
    ( 160, (  -3209,    1514,     2128), +230.60),  # measured f160
    ( 161, (  -3347,    1542,      803), +230.60),  # measured f161
    ( 162, (  -3471,    1571,     -511), +230.60),  # measured f162
    ( 163, (  -3602,    1596,    -1831), +230.60),  # measured f163
    ( 164, (  -3722,    1628,    -3141), +230.60),  # measured f164
    ( 165, (  -3839,    1639,    -4450), +230.60),  # measured f165
    ( 166, (  -3756,    1673,    -5593), +230.60),  # measured f166
    ( 167, (  -3672,    1695,    -6737), +230.60),  # measured f167
    ( 168, (  -3590,    1731,    -7873), +230.60),  # measured f168
    ( 169, (  -3590,    1730,    -7889), +230.60),  # measured f169
    ( 170, (  -3590,    1731,    -7905), +230.60),  # measured f170
    ( 171, (  -3590,    1730,    -7917), +230.60),  # measured f171
    ( 172, (  -3591,    1730,    -7929), +230.60),  # measured f172
    ( 173, (  -3591,    1730,    -7941), +230.60),  # measured f173
    ( 174, (  -3591,    1729,    -7954), +230.60),  # measured f174
    ( 175, (  -3592,    1729,    -7966), +230.60),  # measured f175
    ( 176, (  -3592,    1729,    -7978), +230.60),  # measured f176
    ( 177, (  -3592,    1728,    -7991), +230.60),  # measured f177
    ( 178, (    479,    8603,    20154), +235.78),  # measured f178
    ( 179, (    427,    8714,    20205), +235.64),  # measured f179
    ( 180, (    241,    9101,    20285), +235.32),  # measured f180
    ( 181, (     49,    9490,    20363), +235.02),  # measured f181
    ( 182, (   -148,    9859,    20432), +234.67),  # measured f182
    ( 183, (   -352,   10230,    20500), +234.34),  # measured f183
    ( 184, (   -570,   10600,    20560), +234.05),  # measured f184
    ( 185, (   -778,   10938,    20625), +233.71),  # measured f185
    ( 186, (   -997,   11268,    20684), +233.36),  # measured f186
    ( 187, (  -1218,   11594,    20750), +233.04),  # measured f187
    ( 188, (  -1443,   11899,    20808), +232.74),  # measured f188
    ( 189, (  -1672,   12190,    20866), +232.39),  # measured f189
    ( 190, (  -1911,   12474,    20919), +232.08),  # measured f190
    ( 191, (  -2146,   12743,    20978), +231.78),  # measured f191
    ( 192, (  -2376,   12995,    21033), +231.43),  # measured f192
    ( 193, (  -2617,   13230,    21083), +231.11),  # measured f193
    ( 194, (  -2847,   13457,    21149), +230.80),  # measured f194
    ( 195, (  -3076,   13661,    21202), +230.46),  # measured f195
    ( 196, (  -3290,   13846,    21262), +230.15),  # measured f196
    ( 197, (  -3542,   14047,    21325), +229.83),  # measured f197
    ( 198, (  -3768,   14219,    21379), +229.49),  # measured f198
    ( 199, (  -3992,   14375,    21438), +229.14),  # measured f199
    ( 200, (  -4227,   14515,    21486), +228.83),  # measured f200
    ( 201, (  -4451,   14647,    21542), +228.54),  # measured f201
    ( 202, (  -4683,   14763,    21587), +228.18),  # measured f202
    ( 203, (  -4910,   14871,    21642), +227.89),  # measured f203
    ( 204, (  -5028,   15075,    21630), +227.79),  # measured f204
    ( 205, (    465,   20546,    15213), +231.68),  # measured f205
    ( 206, (    490,   20693,    15156), +232.87),  # measured f206
    ( 207, (    506,   20840,    15107), +234.03),  # measured f207
    ( 208, (    527,   20967,    15046), +235.17),  # measured f208
    ( 209, (    524,   21098,    15021), +236.23),  # measured f209
    ( 210, (    521,   21247,    14996), +237.20),  # measured f210
    ( 211, (    513,   21395,    14978), +238.18),  # measured f211
    ( 212, (    503,   21539,    14962), +239.20),  # measured f212
    ( 213, (    493,   21692,    14950), +240.00),  # measured f213
    ( 214, (    481,   21840,    14943), +240.86),  # measured f214
    ( 215, (    466,   21987,    14937), +241.77),  # measured f215
    ( 216, (    449,   22134,    14940), +242.56),  # measured f216
    ( 217, (    434,   22279,    14944), +243.27),  # measured f217
    ( 218, (    419,   22421,    14950), +243.95),  # measured f218
    ( 219, (    412,   22471,    14953), +244.23),  # measured f219
    ( 220, (    393,   22624,    14965), +245.01),  # measured f220
    ( 221, (    380,   22728,    14974), +245.55),  # measured f221
    ( 222, (    364,   22855,    14990), +246.09),  # measured f222
    ( 223, (    351,   22960,    15000), +246.55),  # measured f223
    ( 224, (    335,   23082,    15016), +247.13),  # measured f224
    ( 225, (    322,   23178,    15028), +247.64),  # measured f225
    ( 226, (    310,   23269,    15041), +248.05),  # measured f226
    ( 227, (    298,   23358,    15057), +248.39),  # measured f227
    ( 228, (    287,   23430,    15070), +248.78),  # measured f228
    ( 229, (    278,   23505,    15083), +249.13),  # measured f229
    ( 230, (    270,   23563,    15095), +249.33),  # measured f230
    ( 231, (    254,   23612,    15101), +249.60),  # measured f231
    ( 232, (    249,   23650,    15109), +249.84),  # measured f232
    ( 233, (    244,   23680,    15117), +249.99),  # measured f233
    ( 234, (    251,   23693,    15124), +250.07),  # measured f234
    ( 235, (    248,   23695,    15127), +250.15),  # measured f235
    ( 236, (    247,   23704,    15129), +250.23),  # measured f236
    ( 237, (    684,   22640,    18099), +106.87),  # measured f237
    ( 238, (    684,   22630,    18099), +106.87),  # measured f238
    ( 239, (    684,   22638,    18101), +106.87),  # measured f239
    ( 240, (    685,   22699,    18105), +106.87),  # measured f240
    ( 241, (    687,   22769,    18108), +106.87),  # measured f241
    ( 242, (    697,   22769,    18104), +106.87),  # measured f242
    ( 243, (    675,   22819,    18111), +106.58),  # measured f243
    ( 244, (    565,   22978,    18139), +103.91),  # measured f244
    ( 245, (    432,   23193,    18135), +100.62),  # measured f245
    ( 246, (    247,   23449,    18070),  +96.66),  # measured f246
    ( 247, (     83,   23689,    17920),  +92.54),  # measured f247
    ( 248, (    -67,   23888,    17686),  +88.61),  # measured f248
    ( 249, (   -155,   24005,    17381),  +84.92),  # measured f249
    ( 250, (   -194,   24047,    17031),  +81.74),  # measured f250
    ( 251, (   -183,   24001,    16640),  +79.00),  # measured f251
    ( 252, (   -161,   24002,    16475),  +78.20),  # measured f252
    ( 253, (    -83,   23865,    16045),  +76.00),  # measured f253
    ( 254, (     23,   23668,    15592),  +74.16),  # measured f254
    ( 255, (    128,   23487,    15267),  +72.44),  # measured f255
    ( 256, (    163,   23455,    15200),  +70.74),  # measured f256
    ( 257, (    199,   23415,    15136),  +69.23),  # measured f257
    ( 258, (    242,   23381,    15075),  +67.85),  # measured f258
    ( 259, (    277,   23340,    15022),  +66.52),  # measured f259
    ( 260, (    320,   23309,    14968),  +65.09),  # measured f260
    ( 261, (    355,   23278,    14930),  +63.99),  # measured f261
    ( 262, (    394,   23244,    14888),  +62.85),  # measured f262
    ( 263, (    433,   23213,    14846),  +61.83),  # measured f263
    ( 264, (    475,   23182,    14802),  +60.86),  # measured f264
    ( 265, (    528,   23154,    14776),  +60.04),  # measured f265
    ( 266, (    523,   23118,    14712),  +59.28),  # measured f266
    ( 267, (    619,   23095,    14691),  +58.58),  # measured f267
    ( 268, (    602,   23059,    14632),  +57.93),  # measured f268
    ( 269, (    692,   23030,    14612),  +57.44),  # measured f269
    ( 270, (    685,   22995,    14556),  +57.02),  # measured f270
    ( 271, (    754,   22969,    14527),  +56.68),  # measured f271
    ( 272, (    766,   22939,    14479),  +56.38),  # measured f272
    ( 273, (    805,   22906,    14441),  +56.21),  # measured f273
    ( 274, (    836,   22880,    14398),  +56.12),  # measured f274
    ( 275, (    872,   22850,    14357),  +55.86),  # measured f275
    ( 276, (    915,   22844,    14327),  +55.18),  # measured f276
    ( 277, (    967,   22827,    14305),  +54.56),  # measured f277
    ( 278, (   1011,   22816,    14275),  +53.93),  # measured f278
    ( 279, (   1053,   22801,    14250),  +53.33),  # measured f279
    ( 280, (   1100,   22796,    14221),  +52.75),  # measured f280
    ( 281, (   1140,   22782,    14196),  +52.25),  # measured f281
    ( 282, (   1186,   22767,    14168),  +51.70),  # measured f282
    ( 283, (   1226,   22755,    14144),  +51.27),  # measured f283
    ( 284, (   1269,   22750,    14117),  +50.84),  # measured f284
    ( 285, (   1314,   22738,    14092),  +50.38),  # measured f285
    ( 286, (   1354,   22724,    14072),  +49.99),  # measured f286
    ( 287, (   1393,   22708,    14050),  +49.66),  # measured f287
    ( 288, (   1437,   22700,    14025),  +49.32),  # measured f288
    ( 289, (   1476,   22687,    14004),  +49.05),  # measured f289
    ( 290, (   1514,   22673,    13983),  +48.79),  # measured f290
    ( 291, (   1553,   22658,    13963),  +48.53),  # measured f291
    ( 292, (   1590,   22643,    13943),  +48.29),  # measured f292
    ( 293, (   1629,   22630,    13922),  +48.12),  # measured f293
    ( 294, (   1669,   22623,    13900),  +47.97),  # measured f294
    ( 295, (   1702,   22607,    13879),  +47.88),  # measured f295
    ( 296, (   1735,   22586,    13858),  +47.80),  # measured f296
    ( 297, (   1768,   22568,    13838),  +47.71),  # measured f297
    ( 298, (   1800,   22551,    13814),  +47.68),  # measured f298
    ( 299, (   1817,   22536,    13799),  +47.74),  # measured f299
    ( 300, (   1817,   22535,    13807),  +47.74),  # measured f300
    ( 301, (   2532,   23824,    13743),  +47.74),  # gap f301
    ( 302, (    965,    8188,    -4384),  +90.59),  # gap f302
    ( 303, (   1449,    8271,    -4419),  +90.80),  # gap f303
    ( 304, (   1939,    8516,    -4515),  +91.40),  # gap f304
    ( 305, (   2432,    8764,    -4622),  +92.02),  # measured f305
    ( 306, (   1105,    9011,    -4652),  +92.68),  # measured f306
    ( 307, (    809,    9257,    -4710),  +93.34),  # measured f307
    ( 308, (    674,    9505,    -4773),  +93.95),  # measured f308
    ( 309, (    609,    9747,    -4833),  +94.56),  # measured f309
    ( 310, (    565,    9995,    -4896),  +95.22),  # measured f310
    ( 311, (    532,   10236,    -4954),  +95.89),  # measured f311
    ( 312, (    514,   10412,    -5119),  +96.51),  # measured f312
    ( 313, (    460,   10485,    -5435),  +97.13),  # measured f313
    ( 314, (    407,   10594,    -5700),  +97.74),  # measured f314
    ( 315, (    376,   10728,    -5921),  +98.38),  # measured f315
    ( 316, (    335,   10878,    -6105),  +99.06),  # measured f316
    ( 317, (    303,   11041,    -6271),  +99.67),  # measured f317
    ( 318, (    262,   11215,    -6407), +100.28),  # measured f318
    ( 319, (    233,   11401,    -6525), +100.94),  # measured f319
    ( 320, (    193,   11582,    -6632), +101.61),  # measured f320
    ( 321, (    164,   11762,    -6731), +102.22),  # measured f321
    ( 322, (    124,   11944,    -6820), +102.85),  # measured f322
    ( 323, (     95,   12131,    -6901), +103.45),  # measured f323
    ( 324, (     56,   12310,    -6969), +104.09),  # measured f324
    ( 325, (     30,   12486,    -7029), +104.75),  # measured f325
    ( 326, (      3,   12673,    -7087), +105.38),  # measured f326
    ( 327, (    -32,   12852,    -7139), +105.99),  # measured f327
    ( 328, (    -56,   13028,    -7182), +106.65),  # measured f328
    ( 329, (    -80,   13200,    -7225), +107.34),  # measured f329
    ( 330, (   -112,   13363,    -7264), +107.94),  # measured f330
    ( 331, (   -129,   13528,    -7298), +108.56),  # measured f331
    ( 332, (   -153,   13685,    -7322), +109.19),  # measured f332
    ( 333, (   -170,   13795,    -7342), +109.66),  # measured f333
    ( 334, (   -174,   13830,    -7348), +109.66),  # measured f334
    ( 335, (   -174,   13863,    -7342), +109.66),  # measured f335
    ( 336, (   -173,   13879,    -7345), +109.66),  # measured f336
    ( 337, (   -175,   13890,    -7335), +109.66),  # measured f337
    ( 338, (     96,   12463,    -6774), +285.52),  # measured f338
    ( 339, (     21,   12440,    -6819), +284.04),  # measured f339
    ( 340, (    -34,   12403,    -6995), +279.63),  # measured f340
    ( 341, (    -73,   12383,    -7152), +275.18),  # measured f341
    ( 342, (    -88,   12364,    -7288), +270.82),  # measured f342
    ( 343, (    -85,   12358,    -7408), +266.45),  # measured f343
    ( 344, (    -63,   12359,    -7510), +262.28),  # measured f344
    ( 345, (    -42,   12355,    -7594), +258.35),  # measured f345
    ( 346, (     -7,   12355,    -7657), +254.85),  # measured f346
    ( 347, (     27,   12360,    -7705), +251.68),  # measured f347
    ( 348, (     54,   12370,    -7735), +248.98),  # measured f348
    ( 349, (     88,   12379,    -7752), +246.66),  # measured f349
    ( 350, (    108,   12386,    -7762), +244.80),  # measured f350
    ( 351, (    131,   12385,    -7761), +243.42),  # measured f351
    ( 352, (    141,   12398,    -7759), +242.47),  # measured f352
    ( 353, (    141,   12399,    -7759), +241.98),  # measured f353
    ( 354, (    157,   12401,    -7747), +241.85),  # measured f354
    ( 355, (    148,   12403,    -7764), +241.84),  # measured f355
    ( 356, (    164,   12405,    -7802), +241.82),  # measured f356
    ( 357, (    185,   12406,    -7835), +241.82),  # measured f357
    ( 358, (    196,   12420,    -7870), +241.82),  # measured f358
    ( 359, (    207,   12412,    -7908), +241.82),  # measured f359
    ( 360, (    226,   12421,    -7941), +241.82),  # measured f360
    ( 361, (    235,   12427,    -7980), +241.82),  # measured f361
    ( 362, (    253,   12439,    -8012), +241.82),  # measured f362
    ( 363, (    278,   12442,    -8043), +241.83),  # measured f363
    ( 364, (    291,   12447,    -8077), +241.82),  # measured f364
    ( 365, (    306,   12452,    -8111), +241.81),  # measured f365
    ( 366, (    323,   12455,    -8147), +241.80),  # measured f366
    ( 367, (    340,   12460,    -8184), +241.81),  # measured f367
    ( 368, (    361,   12466,    -8220), +241.81),  # measured f368
    ( 369, (    371,   12468,    -8263), +241.82),  # measured f369
    ( 370, (    386,   12470,    -8304), +241.81),  # measured f370
    ( 371, (    394,   12473,    -8348), +241.81),  # measured f371
    ( 372, (    406,   12478,    -8391), +241.82),  # measured f372
    ( 373, (    404,   12474,    -8440), +241.82),  # measured f373
    ( 374, (    405,   12473,    -8484), +241.81),  # measured f374
    ( 375, (    408,   12472,    -8531), +241.81),  # measured f375
    ( 376, (    418,   12470,    -8579), +241.82),  # measured f376
    ( 377, (    413,   12457,    -8639), +241.81),  # measured f377
    ( 378, (    427,   12451,    -8692), +241.80),  # measured f378
    ( 379, (    437,   12447,    -8750), +241.80),  # measured f379
    ( 380, (    447,   12450,    -8811), +241.79),  # measured f380
    ( 381, (    462,   12444,    -8863), +241.81),  # measured f381
    ( 382, (    499,   12390,    -8898), +241.84),  # measured f382
    ( 383, (     12,   13539,    -7688), +258.76),  # measured f383
    ( 384, (     12,   13539,    -7688), +258.76),  # measured f384
    ( 385, (     12,   13539,    -7688), +258.76),  # measured f385
    ( 386, (     10,   13541,    -7681), +258.76),  # measured f386
    ( 387, (     60,   13695,    -7378), +258.76),  # measured f387
    ( 388, (     94,   13845,    -7418), +258.76),  # measured f388
    ( 389, (     84,   13959,    -7601), +258.76),  # measured f389
    ( 390, (     98,   14096,    -7602), +258.76),  # measured f390
    ( 391, (    100,   14192,    -7658), +258.76),  # measured f391
    ( 392, (    106,   14248,    -7652), +258.64),  # measured f392
    ( 393, (    102,   14230,    -7673), +258.26),  # measured f393
    ( 394, (    111,   14183,    -7672), +257.63),  # measured f394
    ( 395, (    121,   14096,    -7669), +256.69),  # measured f395
    ( 396, (    126,   13980,    -7642), +255.62),  # measured f396
    ( 397, (    130,   13830,    -7608), +254.55),  # measured f397
    ( 398, (    123,   13654,    -7539), +253.47),  # measured f398
    ( 399, (    108,   13452,    -7455), +252.46),  # measured f399
    ( 400, (     70,   13233,    -7340), +251.54),  # measured f400
    ( 401, (     32,   12985,    -7178), +250.72),  # measured f401
    ( 402, (     52,   12927,    -7184), +238.77),  # measured f402
    ( 403, (    153,   13013,    -7283), +227.35),  # measured f403
    ( 404, (    304,   13085,    -7354), +215.92),  # measured f404
    ( 405, (   -655,   11803,    -6767), +204.42),  # measured f405
    ( 406, (   -575,   11843,    -6998), +192.98),  # measured f406
    ( 407, (    -27,   11695,    -7426), +181.53),  # measured f407
    ( 408, (    742,   11207,    -7096), +170.08),  # measured f408
    ( 409, (   1466,   10843,    -6564), +158.65),  # measured f409
    ( 410, (   2092,   10495,    -5852), +147.21),  # measured f410
    ( 411, (   2560,   10277,    -5068), +135.79),  # measured f411
    ( 412, (   2827,    9843,    -4069), +124.27),  # measured f412
    ( 470, (   2827,    9843,    -4069),  +96.39),  # fire column (camera off him, f470)
    ( 520, (   2827,    9843,    -4069), +119.60),  # fire column (camera off him, f520)
)

THOMAS_END = KEYFRAMES_V10[-1][0]          # 580 -- donor's WaitSFXDone-gated cast length, unchanged

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
    are ``KEYFRAMES_V10``'s own back-projected world positions, solved to hit an authored on-screen target
    under each frame's real camera -- see THE FLIGHT v7 comment block above)."""
    x, y, z = xyz
    return {"DestinationX": str(x), "DestinationY": str(y), "DestinationZ": str(z)}


def build_manifest_json() -> dict:
    """Generate ``thomas_manifest.sfxmodel``'s JSON from the FLIGHT v10 (MEASURED position + size -- the creature's real path)
    ``KEYFRAMES_V10`` constant above (schema verified against ``ParametricMovement.LoadFromJSON``,
    Memoria/Battle/SFX/ParametricMovement.cs:58-136 -- an array of pieces, ``Duration`` + per-axis
    ``Origin*``/``Destination*``/``InterpolationType*``; an absent ``Origin*`` on piece i>0 CHAINS from
    the prior piece's own ``Destination*``; an absent ``InterpolationType*`` defaults to ``Linear``,
    l.254).

    Movement is one Linear piece per consecutive ``KEYFRAMES_V10`` transition (61 pieces for 62
    keyframes) -- deliberately ALL Linear, no Sinus/SinusIn/SinusOut anywhere: the drift verification in
    ``flight_v7_solve.py`` (every segment's real-camera projection stays within margin) was performed
    assuming Linear interpolation between consecutive keyframes, so using anything else here would let
    the DEPLOYED runtime path diverge from the path that was actually checked. Rotation mirrors the same
    piece/duration structure, holding ``DestinationY`` = each keyframe's own per-frame broadside yaw
    (``DestinationZ`` always ``"0"`` -- no roll, per the README axis-verification). Scaling is one
    constant piece (``THOMAS_SCALE`` -- must match ``flight_v10_solve.THOMAS_SCALE``, both currently 265).
    All piece durations sum to ``THOMAS_END`` on every axis (asserted below)."""
    movement = [
        {   # first piece needs an explicit Origin -- every later piece chains from the prior Destination
            "Duration": str(KEYFRAMES_V10[1][0] - KEYFRAMES_V10[0][0]),
            "OriginX": str(KEYFRAMES_V10[0][1][0]), "OriginY": str(KEYFRAMES_V10[0][1][1]), "OriginZ": str(KEYFRAMES_V10[0][1][2]),
            **_pt(KEYFRAMES_V10[1][1]),
        },
    ]
    prev_frame = KEYFRAMES_V10[1][0]
    for frame, xyz, _yaw in KEYFRAMES_V10[2:]:
        movement.append({"Duration": str(frame - prev_frame), **_pt(xyz)})   # Linear default
        prev_frame = frame

    rotation = [
        {
            "Duration": str(KEYFRAMES_V10[1][0] - KEYFRAMES_V10[0][0]),
            "OriginY": f"{KEYFRAMES_V10[0][2]:.2f}", "DestinationY": f"{KEYFRAMES_V10[1][2]:.2f}",
            "OriginZ": "0", "DestinationZ": "0",
        },
    ]
    prev_frame = KEYFRAMES_V10[1][0]
    for frame, _xyz, yaw in KEYFRAMES_V10[2:]:
        rotation.append({
            "Duration": str(frame - prev_frame),
            "DestinationY": f"{yaw:.2f}", "DestinationZ": "0",
        })
        prev_frame = frame

    # invariant: every axis's piece durations sum to THOMAS_END (the cast length)
    assert sum(int(p["Duration"]) for p in movement) == THOMAS_END, "movement durations != THOMAS_END"
    assert sum(int(p["Duration"]) for p in rotation) == THOMAS_END, "rotation durations != THOMAS_END"
    assert len(movement) == len(KEYFRAMES_V10) - 1 == len(rotation), "piece count != KEYFRAMES_V10 transitions"
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
        print("THE FLIGHT v7 (IN-FRAME BY CONSTRUCTION, 2026-07-22):")
        print(f"  method        : each of 18 authored story beats gets a target on-screen (ndc_x,ndc_y) + apparent")
        print(f"                  height%, solved to a real-camera depth and back-projected to world via that")
        print(f"                  frame's real VIEW+PROJ (flight_v7_solve.py); segments whose real-camera drift")
        print(f"                  would leave the frame are recursively bisected with extra keyframes until every")
        print(f"                  segment verifies in-frame. All {len(KEYFRAMES_V10)} keyframes, {len(KEYFRAMES_V10)-1} Linear")
        print(f"                  pieces (no easing -- keeps the deployed path == the verified path).")
        print(f"  yaw           : per-keyframe, derived from that frame's own camera forward vector (broadside")
        print(f"                  presentation to the ACTUAL camera at that moment, not a fixed world angle).")
        print()
        print(f"  keyframes baked into the manifest (frame, world XYZ, yaw deg) -- {len(KEYFRAMES_V10)} total,")
        print(f"  {sum(1 for _f, _p, _y in KEYFRAMES_V10)} incl. 18 authored beats + adaptive drift-inserts:")
        for frame, xyz, yaw in KEYFRAMES_V10:
            print(f"    f{frame:<4d} = {xyz}  yaw={yaw:+.1f}")
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
