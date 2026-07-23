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
     the ``KEYFRAMES_V9`` constant below by ``build_manifest_json()`` -- an IN-FRAME-BY-CONSTRUCTION
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
# THE FLIGHT v9 (MEASURED, 2026-07-23) bakes KEYFRAMES_V9 below as constants; the tool that DERIVED them is
# flight_v9_solve.py (this dir). The s53 probe + FORMAT round recovered the creature's REAL per-frame screen
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

# --- KEYFRAMES_V9: (frame, (world X, Y, Z), yaw_deg) -- flight_v9_solve.py's MEASURED path, 334 keyframes.
# --- THE FIRST MEASURED FLIGHT: the s53 probe + FORMAT round recovered the creature's REAL per-frame screen
# --- position (reproject its composed node-0 through the native GTE M+OFX/OFY/H). v9 places Thomas at that
# --- screen position, back-projected through the MANAGED camera (which renders Thomas) at HEIGHT_FRAC size.
# --- Entrance lead-in -> the measured every-frame path 82-412 (dead-centered float/charge) -> a fire-column
# --- exit hold (camera pans off him). One keyframe/frame in the measured window so cuts render as faithful
# --- 1-frame cuts, not swings. Generated -- do not hand-edit; re-run flight_v9_solve.py. See PROBE.md sec 11. ---
KEYFRAMES_V9: "tuple[tuple[int, tuple[int, int, int], float], ...]" = (
    (   0, (    866,    2181,    -2853), +240.42),  # lead-in (off-frame top, flying down)
    (  82, (  -1849,    1515,    -1030), +185.27),  # measured f82
    (  83, (  -1865,    1515,    -1017), +185.27),  # measured f83
    (  84, (  -1828,    1515,     -847), +185.27),  # measured f84
    (  85, (  -1735,    1521,     -768), +185.27),  # measured f85
    (  86, (  -1412,    1536,     -791), +185.27),  # measured f86
    (  87, (  -1067,    1551,     -754), +185.27),  # measured f87
    (  88, (   -935,    1558,     -823), +185.27),  # measured f88
    (  89, (   -727,    1566,     -717), +185.27),  # measured f89
    (  90, (   -613,    1571,     -667), +185.27),  # measured f90
    (  91, (   -496,    1577,     -673), +185.27),  # measured f91
    (  92, (   -467,    1579,     -634), +185.27),  # measured f92
    (  93, (   -378,    1582,     -549), +185.27),  # measured f93
    (  94, (   -332,    1585,     -550), +185.27),  # measured f94
    (  95, (   -321,    1586,     -504), +185.27),  # measured f95
    (  96, (   -306,    1587,     -441), +185.27),  # measured f96
    (  97, (   -265,    1588,     -404), +185.27),  # measured f97
    (  98, (   -239,    1588,     -418), +185.27),  # measured f98
    (  99, (   -234,    1589,     -353), +185.27),  # measured f99
    ( 100, (   -237,    1589,     -338), +185.27),  # measured f100
    ( 101, (   -212,    1589,     -290), +185.27),  # measured f101
    ( 102, (   -206,    1589,     -280), +185.27),  # measured f102
    ( 103, (   -222,    1590,     -232), +185.27),  # measured f103
    ( 104, (   -232,    1589,     -193), +185.27),  # measured f104
    ( 105, (   -221,    1589,     -174), +185.27),  # measured f105
    ( 106, (   -227,    1589,     -148), +185.27),  # measured f106
    ( 107, (   -217,    1589,     -110), +185.27),  # measured f107
    ( 108, (   -219,    1589,      -95), +185.27),  # measured f108
    ( 109, (   -209,    1590,      -71), +185.27),  # measured f109
    ( 110, (   -210,    1589,      -54), +185.27),  # measured f110
    ( 111, (   -201,    1589,       -6), +185.27),  # measured f111
    ( 112, (   -179,    1590,      -14), +185.27),  # measured f112
    ( 113, (   -177,    1590,       17), +185.27),  # measured f113
    ( 114, (   -164,    1590,       35), +185.27),  # measured f114
    ( 115, (   -150,    1591,       62), +185.27),  # measured f115
    ( 116, (   -139,    1592,       69), +185.27),  # measured f116
    ( 117, (   -132,    1593,       62), +185.27),  # measured f117
    ( 118, (   -107,    1594,       64), +185.27),  # measured f118
    ( 119, (   -100,    1594,       56), +185.27),  # measured f119
    ( 120, (    -89,    1594,       59), +185.27),  # measured f120
    ( 121, (    -73,    1595,       48), +185.27),  # measured f121
    ( 122, (    -73,    1595,       50), +185.27),  # measured f122
    ( 123, (    -68,    1595,       36), +185.27),  # measured f123
    ( 124, (    -68,    1595,       34), +185.27),  # measured f124
    ( 125, (    -69,    1595,       33), +185.27),  # measured f125
    ( 126, (    -66,    1595,       32), +185.27),  # measured f126
    ( 127, (    -57,    1595,       18), +185.27),  # measured f127
    ( 128, (      0,    2029,      925),  +90.00),  # measured f128
    ( 129, (      0,    2061,      909),  +90.00),  # measured f129
    ( 130, (    -57,    2200,      835),  +90.42),  # measured f130
    ( 131, (    -58,    2418,      698),  +91.52),  # measured f131
    ( 132, (    -51,    2624,      545),  +92.64),  # measured f132
    ( 133, (    -52,    2811,      384),  +93.72),  # measured f133
    ( 134, (    -60,    2977,      219),  +94.79),  # measured f134
    ( 135, (    -73,    2985,      100),  +95.78),  # measured f135
    ( 136, (    -72,    2922,       22),  +96.74),  # measured f136
    ( 137, (    -75,    2882,      -41),  +97.64),  # measured f137
    ( 138, (    -80,    2847,      -88),  +98.46),  # measured f138
    ( 139, (    -75,    2827,     -129),  +99.19),  # measured f139
    ( 140, (    -85,    2813,     -158),  +99.84),  # measured f140
    ( 141, (    -84,    2806,     -184), +100.42),  # measured f141
    ( 142, (    -86,    2796,     -199), +100.87),  # measured f142
    ( 143, (    -90,    2794,     -214), +101.23),  # measured f143
    ( 144, (    -97,    2789,     -221), +101.49),  # measured f144
    ( 145, (    -99,    2736,     -188), +101.63),  # measured f145
    ( 146, (   -108,    2654,     -132), +101.83),  # measured f146
    ( 147, (   -113,    2587,      -88), +102.21),  # measured f147
    ( 148, (   -114,    2506,      -32), +102.62),  # measured f148
    ( 149, (   -123,    2421,       37), +103.05),  # measured f149
    ( 150, (   -141,    2333,      115), +103.52),  # measured f150
    ( 151, (   -153,    2234,      209), +104.03),  # measured f151
    ( 152, (   -179,    2111,      338), +104.57),  # measured f152
    ( 153, (    610,    1857,     5240), +230.60),  # gap-interp f153
    ( 154, (    582,    2767,     5269), +230.60),  # gap-interp f154
    ( 155, (    582,    2767,     5252), +230.60),  # gap-interp f155
    ( 156, (    582,    2767,     5236), +230.60),  # measured f156
    ( 157, (    460,    2767,     5120), +230.60),  # measured f157
    ( 158, (  -1648,    2078,     3329), +230.60),  # measured f158
    ( 159, (  -2620,    1733,     2493), +230.60),  # measured f159
    ( 160, (  -3172,    1536,     2011), +230.60),  # measured f160
    ( 161, (  -3543,    1408,     1682), +230.60),  # measured f161
    ( 162, (  -3794,    1319,     1454), +230.60),  # measured f162
    ( 163, (  -3985,    1250,     1278), +230.60),  # measured f163
    ( 164, (  -4125,    1201,     1143), +230.60),  # measured f164
    ( 165, (  -4235,    1152,     1034), +230.60),  # measured f165
    ( 166, (  -4234,    1122,     1017), +230.60),  # measured f166
    ( 167, (  -4233,    1093,     1000), +230.60),  # measured f167
    ( 168, (  -4232,    1073,      983), +230.60),  # measured f168
    ( 169, (  -4233,    1073,      967), +230.60),  # measured f169
    ( 170, (  -4233,    1073,      951), +230.60),  # measured f170
    ( 171, (  -4232,    1073,      935), +230.60),  # measured f171
    ( 172, (  -4232,    1073,      919), +230.60),  # measured f172
    ( 173, (  -4232,    1073,      903), +230.60),  # measured f173
    ( 174, (  -4232,    1073,      887), +230.60),  # measured f174
    ( 175, (  -4233,    1073,      871), +230.60),  # measured f175
    ( 176, (  -4233,    1073,      855), +230.60),  # measured f176
    ( 177, (  -4232,    1073,      839), +230.60),  # measured f177
    ( 178, (    941,    8667,    19300), +235.78),  # measured f178
    ( 179, (    903,    8760,    19359), +235.65),  # measured f179
    ( 180, (    727,    9158,    19448), +235.33),  # measured f180
    ( 181, (    545,    9555,    19534), +235.02),  # measured f181
    ( 182, (    349,    9953,    19614), +234.66),  # measured f182
    ( 183, (    160,   10325,    19687), +234.35),  # measured f183
    ( 184, (    -48,   10703,    19752), +234.06),  # measured f184
    ( 185, (   -252,   11061,    19826), +233.71),  # measured f185
    ( 186, (   -470,   11415,    19893), +233.36),  # measured f186
    ( 187, (   -681,   11754,    19967), +233.04),  # measured f187
    ( 188, (   -901,   12073,    20032), +232.74),  # measured f188
    ( 189, (  -1125,   12379,    20097), +232.39),  # measured f189
    ( 190, (  -1359,   12679,    20155), +232.08),  # measured f190
    ( 191, (  -1587,   12960,    20222), +231.79),  # measured f191
    ( 192, (  -1819,   13232,    20286), +231.43),  # measured f192
    ( 193, (  -2059,   13484,    20343), +231.11),  # measured f193
    ( 194, (  -2276,   13719,    20417), +230.81),  # measured f194
    ( 195, (  -2508,   13945,    20480), +230.46),  # measured f195
    ( 196, (  -2727,   14154,    20553), +230.14),  # measured f196
    ( 197, (  -2958,   14355,    20621), +229.84),  # measured f197
    ( 198, (  -3189,   14550,    20687), +229.49),  # measured f198
    ( 199, (  -3407,   14719,    20757), +229.15),  # measured f199
    ( 200, (  -3645,   14877,    20814), +228.83),  # measured f200
    ( 201, (  -3866,   15023,    20879), +228.54),  # measured f201
    ( 202, (  -4095,   15152,    20931), +228.19),  # measured f202
    ( 203, (  -4326,   15279,    20996), +227.90),  # measured f203
    ( 204, (  -4449,   15493,    20993), +227.79),  # measured f204
    ( 205, (    726,   21410,    14888), +231.68),  # measured f205
    ( 206, (    775,   21530,    14784), +232.87),  # measured f206
    ( 207, (    810,   21651,    14693), +234.03),  # measured f207
    ( 208, (    852,   21743,    14585), +235.17),  # measured f208
    ( 209, (    862,   21843,    14520), +236.23),  # measured f209
    ( 210, (    871,   21961,    14458), +237.20),  # measured f210
    ( 211, (    873,   22074,    14404), +238.18),  # measured f211
    ( 212, (    870,   22184,    14354), +239.20),  # measured f212
    ( 213, (    866,   22301,    14310), +240.00),  # measured f213
    ( 214, (    858,   22412,    14272), +240.86),  # measured f214
    ( 215, (    844,   22524,    14239), +241.77),  # measured f215
    ( 216, (    828,   22638,    14217), +242.56),  # measured f216
    ( 217, (    813,   22748,    14199), +243.27),  # measured f217
    ( 218, (    797,   22855,    14183), +243.95),  # measured f218
    ( 219, (    790,   22891,    14179), +244.23),  # measured f219
    ( 220, (    769,   22998,    14172), +244.94),  # measured f220
    ( 221, (    750,   23091,    14166), +245.57),  # measured f221
    ( 222, (    730,   23187,    14168), +246.11),  # measured f222
    ( 223, (    713,   23274,    14168), +246.62),  # measured f223
    ( 224, (    694,   23357,    14170), +247.15),  # measured f224
    ( 225, (    677,   23423,    14173), +247.65),  # measured f225
    ( 226, (    661,   23487,    14177), +248.06),  # measured f226
    ( 227, (    645,   23558,    14188), +248.40),  # measured f227
    ( 228, (    630,   23609,    14195), +248.79),  # measured f228
    ( 229, (    616,   23668,    14203), +249.14),  # measured f229
    ( 230, (    607,   23705,    14210), +249.33),  # measured f230
    ( 231, (    584,   23737,    14212), +249.61),  # measured f231
    ( 232, (    576,   23762,    14217), +249.84),  # measured f232
    ( 233, (    570,   23779,    14222), +249.99),  # measured f233
    ( 234, (    579,   23781,    14229), +250.07),  # measured f234
    ( 235, (    575,   23775,    14231), +250.15),  # measured f235
    ( 236, (    572,   23781,    14232), +250.24),  # measured f236
    ( 237, (    951,   22234,    18999), +106.87),  # measured f237
    ( 238, (    951,   22223,    18999), +106.87),  # measured f238
    ( 239, (    951,   22241,    19001), +106.87),  # measured f239
    ( 240, (    953,   22328,    19006), +106.87),  # measured f240
    ( 241, (    955,   22425,    19011), +106.87),  # measured f241
    ( 242, (    967,   22433,    19006), +106.87),  # measured f242
    ( 243, (    938,   22501,    19017), +106.56),  # measured f243
    ( 244, (    790,   22720,    19069), +103.91),  # measured f244
    ( 245, (    608,   23014,    19089), +100.62),  # measured f245
    ( 246, (    355,   23368,    19041),  +96.66),  # measured f246
    ( 247, (    124,   23709,    18892),  +92.54),  # measured f247
    ( 248, (    -95,   24006,    18646),  +88.61),  # measured f248
    ( 249, (   -241,   24205,    18320),  +84.92),  # measured f249
    ( 250, (   -329,   24318,    17944),  +81.74),  # measured f250
    ( 251, (   -357,   24325,    17527),  +79.00),  # measured f251
    ( 252, (   -346,   24346,    17333),  +78.11),  # measured f252
    ( 253, (   -296,   24247,    16880),  +75.94),  # measured f253
    ( 254, (   -212,   24074,    16397),  +74.08),  # measured f254
    ( 255, (   -135,   23917,    16077),  +72.37),  # measured f255
    ( 256, (   -123,   23886,    16001),  +70.66),  # measured f256
    ( 257, (   -109,   23846,    15930),  +69.17),  # measured f257
    ( 258, (    -81,   23813,    15861),  +67.77),  # measured f258
    ( 259, (    -64,   23771,    15800),  +66.42),  # measured f259
    ( 260, (    -41,   23748,    15740),  +65.12),  # measured f260
    ( 261, (    -22,   23722,    15696),  +64.07),  # measured f261
    ( 262, (      5,   23685,    15641),  +62.82),  # measured f262
    ( 263, (     32,   23656,    15591),  +61.79),  # measured f263
    ( 264, (     60,   23628,    15541),  +60.87),  # measured f264
    ( 265, (    111,   23601,    15512),  +60.02),  # measured f265
    ( 266, (     87,   23564,    15434),  +59.25),  # measured f266
    ( 267, (    180,   23545,    15411),  +58.55),  # measured f267
    ( 268, (    148,   23510,    15342),  +57.92),  # measured f268
    ( 269, (    240,   23482,    15323),  +57.42),  # measured f269
    ( 270, (    224,   23448,    15260),  +57.01),  # measured f270
    ( 271, (    291,   23422,    15229),  +56.66),  # measured f271
    ( 272, (    300,   23395,    15177),  +56.38),  # measured f272
    ( 273, (    336,   23362,    15136),  +56.20),  # measured f273
    ( 274, (    368,   23336,    15090),  +56.13),  # measured f274
    ( 275, (    397,   23307,    15053),  +55.87),  # measured f275
    ( 276, (    433,   23294,    15017),  +55.14),  # measured f276
    ( 277, (    476,   23271,    14995),  +54.53),  # measured f277
    ( 278, (    511,   23257,    14962),  +53.92),  # measured f278
    ( 279, (    546,   23236,    14933),  +53.30),  # measured f279
    ( 280, (    584,   23226,    14901),  +52.72),  # measured f280
    ( 281, (    618,   23207,    14872),  +52.20),  # measured f281
    ( 282, (    653,   23188,    14843),  +51.70),  # measured f282
    ( 283, (    688,   23171,    14816),  +51.25),  # measured f283
    ( 284, (    726,   23163,    14785),  +50.81),  # measured f284
    ( 285, (    762,   23147,    14760),  +50.38),  # measured f285
    ( 286, (    798,   23129,    14735),  +49.97),  # measured f286
    ( 287, (    835,   23109,    14710),  +49.62),  # measured f287
    ( 288, (    872,   23101,    14684),  +49.31),  # measured f288
    ( 289, (    906,   23084,    14661),  +49.04),  # measured f289
    ( 290, (    941,   23068,    14638),  +48.78),  # measured f290
    ( 291, (    977,   23051,    14617),  +48.52),  # measured f291
    ( 292, (   1011,   23034,    14595),  +48.28),  # measured f292
    ( 293, (   1047,   23018,    14573),  +48.11),  # measured f293
    ( 294, (   1085,   23011,    14550),  +47.96),  # measured f294
    ( 295, (   1116,   22994,    14528),  +47.87),  # measured f295
    ( 296, (   1148,   22973,    14507),  +47.80),  # measured f296
    ( 297, (   1180,   22955,    14485),  +47.71),  # measured f297
    ( 298, (   1211,   22937,    14461),  +47.68),  # measured f298
    ( 299, (   1229,   22923,    14448),  +47.74),  # measured f299
    ( 300, (   1228,   22922,    14456),  +47.74),  # measured f300
    ( 301, (   2138,   24564,    14372),  +47.74),  # gap-interp f301
    ( 302, (   1238,    7471,    -3365),  +90.59),  # gap-interp f302
    ( 303, (   1857,    7562,    -3408),  +90.83),  # gap-interp f303
    ( 304, (   2490,    7799,    -3518),  +91.43),  # gap-interp f304
    ( 305, (   3123,    8035,    -3639),  +92.04),  # measured f305
    ( 306, (   1443,    8280,    -3664),  +92.70),  # measured f306
    ( 307, (   1074,    8526,    -3727),  +93.38),  # measured f307
    ( 308, (    909,    8763,    -3794),  +93.98),  # measured f308
    ( 309, (    835,    9003,    -3861),  +94.60),  # measured f309
    ( 310, (    787,    9239,    -3928),  +95.25),  # measured f310
    ( 311, (    754,    9481,    -3994),  +95.93),  # measured f311
    ( 312, (    740,    9626,    -4193),  +96.54),  # measured f312
    ( 313, (    680,    9649,    -4587),  +97.16),  # measured f313
    ( 314, (    622,    9716,    -4914),  +97.77),  # measured f314
    ( 315, (    593,    9817,    -5188),  +98.41),  # measured f315
    ( 316, (    550,    9941,    -5418),  +99.09),  # measured f316
    ( 317, (    519,   10079,    -5622),  +99.69),  # measured f317
    ( 318, (    477,   10238,    -5789), +100.31),  # measured f318
    ( 319, (    451,   10408,    -5933), +100.97),  # measured f319
    ( 320, (    410,   10574,    -6064), +101.63),  # measured f320
    ( 321, (    382,   10743,    -6187), +102.26),  # measured f321
    ( 322, (    342,   10915,    -6296), +102.88),  # measured f322
    ( 323, (    314,   11089,    -6397), +103.48),  # measured f323
    ( 324, (    274,   11263,    -6483), +104.13),  # measured f324
    ( 325, (    250,   11438,    -6559), +104.80),  # measured f325
    ( 326, (    225,   11611,    -6632), +105.41),  # measured f326
    ( 327, (    188,   11781,    -6698), +106.02),  # measured f327
    ( 328, (    165,   11950,    -6757), +106.67),  # measured f328
    ( 329, (    142,   12116,    -6814), +107.37),  # measured f329
    ( 330, (    108,   12275,    -6867), +107.97),  # measured f330
    ( 331, (     92,   12433,    -6914), +108.58),  # measured f331
    ( 332, (     68,   12587,    -6947), +109.22),  # measured f332
    ( 333, (     49,   12690,    -6972), +109.66),  # measured f333
    ( 334, (     40,   12721,    -6983), +109.66),  # measured f334
    ( 335, (     37,   12753,    -6978), +109.66),  # measured f335
    ( 336, (     34,   12766,    -6984), +109.66),  # measured f336
    ( 337, (     28,   12777,    -6972), +109.66),  # measured f337
    ( 338, (   -152,   12309,    -7920), +285.52),  # measured f338
    ( 339, (   -213,   12290,    -7979), +283.81),  # measured f339
    ( 340, (   -207,   12273,    -8163), +279.50),  # measured f340
    ( 341, (   -202,   12269,    -8308), +275.57),  # measured f341
    ( 342, (   -129,   12274,    -8475), +270.53),  # measured f342
    ( 343, (    -68,   12287,    -8594), +266.29),  # measured f343
    ( 344, (     16,   12311,    -8696), +262.09),  # measured f344
    ( 345, (     91,   12324,    -8776), +258.22),  # measured f345
    ( 346, (    179,   12340,    -8835), +254.71),  # measured f346
    ( 347, (    260,   12360,    -8875), +251.57),  # measured f347
    ( 348, (    330,   12385,    -8898), +248.85),  # measured f348
    ( 349, (    401,   12406,    -8906), +246.57),  # measured f349
    ( 350, (    449,   12422,    -8909), +244.74),  # measured f350
    ( 351, (    497,   12425,    -8900), +243.36),  # measured f351
    ( 352, (    522,   12442,    -8894), +242.45),  # measured f352
    ( 353, (    528,   12445,    -8892), +241.97),  # measured f353
    ( 354, (    553,   12446,    -8877), +241.85),  # measured f354
    ( 355, (    541,   12446,    -8897), +241.84),  # measured f355
    ( 356, (    557,   12446,    -8935), +241.82),  # measured f356
    ( 357, (    581,   12446,    -8967), +241.82),  # measured f357
    ( 358, (    592,   12462,    -9002), +241.82),  # measured f358
    ( 359, (    603,   12449,    -9040), +241.82),  # measured f359
    ( 360, (    624,   12458,    -9072), +241.82),  # measured f360
    ( 361, (    634,   12464,    -9110), +241.82),  # measured f361
    ( 362, (    654,   12478,    -9141), +241.82),  # measured f362
    ( 363, (    683,   12481,    -9170), +241.83),  # measured f363
    ( 364, (    699,   12486,    -9202), +241.82),  # measured f364
    ( 365, (    717,   12490,    -9235), +241.81),  # measured f365
    ( 366, (    736,   12494,    -9270), +241.80),  # measured f366
    ( 367, (    756,   12499,    -9306), +241.81),  # measured f367
    ( 368, (    779,   12505,    -9340), +241.81),  # measured f368
    ( 369, (    789,   12505,    -9383), +241.82),  # measured f369
    ( 370, (    804,   12505,    -9424), +241.81),  # measured f370
    ( 371, (    811,   12506,    -9470), +241.81),  # measured f371
    ( 372, (    820,   12509,    -9514), +241.82),  # measured f372
    ( 373, (    810,   12501,    -9567), +241.82),  # measured f373
    ( 374, (    805,   12495,    -9616), +241.81),  # measured f374
    ( 375, (    801,   12490,    -9668), +241.81),  # measured f375
    ( 376, (    806,   12484,    -9719), +241.82),  # measured f376
    ( 377, (    791,   12463,    -9784), +241.81),  # measured f377
    ( 378, (    801,   12448,    -9841), +241.80),  # measured f378
    ( 379, (    807,   12438,    -9903), +241.79),  # measured f379
    ( 380, (    812,   12438,    -9966), +241.79),  # measured f380
    ( 381, (    824,   12430,   -10020), +241.81),  # measured f381
    ( 382, (    865,   12359,   -10053), +241.84),  # measured f382
    ( 383, (     71,   14555,    -8356), +258.76),  # measured f383
    ( 384, (     71,   14555,    -8356), +258.76),  # measured f384
    ( 385, (     71,   14555,    -8356), +258.76),  # measured f385
    ( 386, (     69,   14558,    -8347), +258.76),  # measured f386
    ( 387, (    132,   14753,    -7941), +258.76),  # measured f387
    ( 388, (    175,   14934,    -7889), +258.76),  # measured f388
    ( 389, (    162,   15052,    -8068), +258.76),  # measured f389
    ( 390, (    180,   15189,    -8059), +258.76),  # measured f390
    ( 391, (    182,   15281,    -8114), +258.76),  # measured f391
    ( 392, (    190,   15339,    -8101), +258.63),  # measured f392
    ( 393, (    189,   15317,    -8130), +258.24),  # measured f393
    ( 394, (    206,   15261,    -8143), +257.60),  # measured f394
    ( 395, (    229,   15162,    -8162), +256.65),  # measured f395
    ( 396, (    250,   15034,    -8157), +255.59),  # measured f396
    ( 397, (    271,   14864,    -8150), +254.50),  # measured f397
    ( 398, (    282,   14671,    -8107), +253.43),  # measured f398
    ( 399, (    287,   14448,    -8052), +252.42),  # measured f399
    ( 400, (    265,   14205,    -7963), +251.50),  # measured f400
    ( 401, (    249,   13944,    -7830), +250.71),  # measured f401
    ( 402, (    444,   13807,    -7871), +238.77),  # measured f402
    ( 403, (    714,   13822,    -7940), +227.35),  # measured f403
    ( 404, (   1030,   13818,    -7934), +215.92),  # measured f404
    ( 405, (    -95,   12736,    -7401), +204.42),  # measured f405
    ( 406, (     65,   12836,    -7622), +192.98),  # measured f406
    ( 407, (    778,   12546,    -8000), +181.53),  # measured f407
    ( 408, (   1733,   12108,    -7565), +170.08),  # measured f408
    ( 409, (   2591,   11675,    -6801), +158.65),  # measured f409
    ( 410, (   3293,   11250,    -5824), +147.21),  # measured f410
    ( 411, (   3770,   10835,    -4698), +135.79),  # measured f411
    ( 412, (   3977,   10432,    -3483), +124.27),  # measured f412
    ( 470, (   3977,   10432,    -3483),  +96.36),  # fire column (camera off him -- hold, f470)
    ( 520, (   3977,   10432,    -3483), +119.60),  # fire column (camera off him -- hold, f520)
)

THOMAS_END = KEYFRAMES_V9[-1][0]          # 580 -- donor's WaitSFXDone-gated cast length, unchanged

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
    are ``KEYFRAMES_V9``'s own back-projected world positions, solved to hit an authored on-screen target
    under each frame's real camera -- see THE FLIGHT v7 comment block above)."""
    x, y, z = xyz
    return {"DestinationX": str(x), "DestinationY": str(y), "DestinationZ": str(z)}


def build_manifest_json() -> dict:
    """Generate ``thomas_manifest.sfxmodel``'s JSON from the FLIGHT v9 (MEASURED -- the creature's real screen path)
    ``KEYFRAMES_V9`` constant above (schema verified against ``ParametricMovement.LoadFromJSON``,
    Memoria/Battle/SFX/ParametricMovement.cs:58-136 -- an array of pieces, ``Duration`` + per-axis
    ``Origin*``/``Destination*``/``InterpolationType*``; an absent ``Origin*`` on piece i>0 CHAINS from
    the prior piece's own ``Destination*``; an absent ``InterpolationType*`` defaults to ``Linear``,
    l.254).

    Movement is one Linear piece per consecutive ``KEYFRAMES_V9`` transition (61 pieces for 62
    keyframes) -- deliberately ALL Linear, no Sinus/SinusIn/SinusOut anywhere: the drift verification in
    ``flight_v7_solve.py`` (every segment's real-camera projection stays within margin) was performed
    assuming Linear interpolation between consecutive keyframes, so using anything else here would let
    the DEPLOYED runtime path diverge from the path that was actually checked. Rotation mirrors the same
    piece/duration structure, holding ``DestinationY`` = each keyframe's own per-frame broadside yaw
    (``DestinationZ`` always ``"0"`` -- no roll, per the README axis-verification). Scaling is one
    constant piece (``THOMAS_SCALE`` -- must match ``flight_v9_solve.THOMAS_SCALE``, both currently 265).
    All piece durations sum to ``THOMAS_END`` on every axis (asserted below)."""
    movement = [
        {   # first piece needs an explicit Origin -- every later piece chains from the prior Destination
            "Duration": str(KEYFRAMES_V9[1][0] - KEYFRAMES_V9[0][0]),
            "OriginX": str(KEYFRAMES_V9[0][1][0]), "OriginY": str(KEYFRAMES_V9[0][1][1]), "OriginZ": str(KEYFRAMES_V9[0][1][2]),
            **_pt(KEYFRAMES_V9[1][1]),
        },
    ]
    prev_frame = KEYFRAMES_V9[1][0]
    for frame, xyz, _yaw in KEYFRAMES_V9[2:]:
        movement.append({"Duration": str(frame - prev_frame), **_pt(xyz)})   # Linear default
        prev_frame = frame

    rotation = [
        {
            "Duration": str(KEYFRAMES_V9[1][0] - KEYFRAMES_V9[0][0]),
            "OriginY": f"{KEYFRAMES_V9[0][2]:.2f}", "DestinationY": f"{KEYFRAMES_V9[1][2]:.2f}",
            "OriginZ": "0", "DestinationZ": "0",
        },
    ]
    prev_frame = KEYFRAMES_V9[1][0]
    for frame, _xyz, yaw in KEYFRAMES_V9[2:]:
        rotation.append({
            "Duration": str(frame - prev_frame),
            "DestinationY": f"{yaw:.2f}", "DestinationZ": "0",
        })
        prev_frame = frame

    # invariant: every axis's piece durations sum to THOMAS_END (the cast length)
    assert sum(int(p["Duration"]) for p in movement) == THOMAS_END, "movement durations != THOMAS_END"
    assert sum(int(p["Duration"]) for p in rotation) == THOMAS_END, "rotation durations != THOMAS_END"
    assert len(movement) == len(KEYFRAMES_V9) - 1 == len(rotation), "piece count != KEYFRAMES_V9 transitions"
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
        print(f"                  segment verifies in-frame. All {len(KEYFRAMES_V9)} keyframes, {len(KEYFRAMES_V9)-1} Linear")
        print(f"                  pieces (no easing -- keeps the deployed path == the verified path).")
        print(f"  yaw           : per-keyframe, derived from that frame's own camera forward vector (broadside")
        print(f"                  presentation to the ACTUAL camera at that moment, not a fixed world angle).")
        print()
        print(f"  keyframes baked into the manifest (frame, world XYZ, yaw deg) -- {len(KEYFRAMES_V9)} total,")
        print(f"  {sum(1 for _f, _p, _y in KEYFRAMES_V9)} incl. 18 authored beats + adaptive drift-inserts:")
        for frame, xyz, yaw in KEYFRAMES_V9:
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
