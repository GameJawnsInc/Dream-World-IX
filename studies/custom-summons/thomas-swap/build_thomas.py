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
    py studies/custom-summons/thomas-swap/build_thomas.py --m1a      # M1a static-hold -- camera-inheritance
                                                                      # isolation test, see m0/M1A-PLAN.md sec 2
    py studies/custom-summons/thomas-swap/build_thomas.py --restore   # back to rung 7's resting state
                                                                        # + Thomas's mint fully removed
    py studies/custom-summons/thomas-swap/build_thomas.py --m1a --dry-run   # stage M1a's artifacts locally
                                                                             # (see DRY_RUN_ROOT) -- nothing
                                                                             # deployed, safe to inspect

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
# --- and fills the frame up close, capped [0.18,0.70]. v10.1 low-passes the WORLD path (WSMOOTH) so the fast
# --- swoops + hard camera cuts read as smooth glides, not jerks. Position/every-frame keyframes from v9.
# --- Generated -- re-run flight_v10_solve.py; see README FLIGHT v10. ---
KEYFRAMES_V10: "tuple[tuple[int, tuple[int, int, int], float], ...]" = (
    (   0, (    866,    2181,    -2853), +240.42),  # lead-in (flying down)
    (  82, (  -1473,    2122,     -620), +185.27),  # measured f82
    (  83, (  -1407,    2125,     -612), +185.27),  # measured f83
    (  84, (  -1323,    2129,     -614), +185.27),  # measured f84
    (  85, (  -1246,    2133,     -617), +185.27),  # measured f85
    (  86, (  -1123,    2139,     -597), +185.27),  # measured f86
    (  87, (   -990,    2145,     -595), +185.27),  # measured f87
    (  88, (   -845,    2152,     -581), +185.27),  # measured f88
    (  89, (   -690,    2159,     -556), +185.27),  # measured f89
    (  90, (   -577,    2164,     -537), +185.27),  # measured f90
    (  91, (   -493,    2168,     -508), +185.27),  # measured f91
    (  92, (   -421,    2172,     -471), +185.27),  # measured f92
    (  93, (   -375,    2174,     -445), +185.27),  # measured f93
    (  94, (   -334,    2176,     -414), +185.27),  # measured f94
    (  95, (   -300,    2177,     -383), +185.27),  # measured f95
    (  96, (   -278,    2178,     -356), +185.27),  # measured f96
    (  97, (   -260,    2179,     -332), +185.27),  # measured f97
    (  98, (   -247,    2179,     -303), +185.27),  # measured f98
    (  99, (   -238,    2180,     -280), +185.27),  # measured f99
    ( 100, (   -227,    2180,     -256), +185.27),  # measured f100
    ( 101, (   -220,    2180,     -233), +185.27),  # measured f101
    ( 102, (   -219,    2180,     -211), +185.27),  # measured f102
    ( 103, (   -217,    2180,     -186), +185.27),  # measured f103
    ( 104, (   -216,    2180,     -161), +185.27),  # measured f104
    ( 105, (   -215,    2180,     -139), +185.27),  # measured f105
    ( 106, (   -213,    2180,     -118), +185.27),  # measured f106
    ( 107, (   -212,    2180,      -97), +185.27),  # measured f107
    ( 108, (   -211,    2180,      -74), +185.27),  # measured f108
    ( 109, (   -208,    2180,      -54), +185.27),  # measured f109
    ( 110, (   -203,    2180,      -35), +185.27),  # measured f110
    ( 111, (   -197,    2181,      -17), +185.27),  # measured f111
    ( 112, (   -191,    2181,        2), +185.27),  # measured f112
    ( 113, (   -184,    2172,       19), +185.27),  # measured f113
    ( 114, (   -173,    2104,       33), +185.27),  # measured f114
    ( 115, (   -157,    1977,       44), +185.27),  # measured f115
    ( 116, (   -139,    1795,       55), +185.27),  # measured f116
    ( 117, (   -118,    1561,       63), +185.27),  # measured f117
    ( 118, (    -95,    1280,       67), +185.27),  # measured f118
    ( 119, (    -69,     957,       68), +185.27),  # measured f119
    ( 120, (    -45,     607,       66), +185.27),  # measured f120
    ( 121, (    -21,     289,       62), +185.27),  # measured f121
    ( 122, (      0,       9,       58), +185.27),  # measured f122
    ( 123, (     16,    -215,       54), +185.27),  # measured f123
    ( 124, (     31,    -388,       45), +185.27),  # measured f124
    ( 125, (     32,    -174,       78), +185.27),  # measured f125
    ( 126, (     31,      84,      108), +185.27),  # measured f126
    ( 127, (     23,     394,      133), +185.27),  # measured f127
    ( 128, (     10,     756,      142),  +90.00),  # measured f128
    ( 129, (     -2,    1161,      134),  +90.00),  # measured f129
    ( 130, (    -15,    1587,      108),  +90.45),  # measured f130
    ( 131, (    -31,    2032,       68),  +91.54),  # measured f131
    ( 132, (    -39,    2139,      -25),  +92.65),  # measured f132
    ( 133, (    -47,    2236,     -125),  +93.73),  # measured f133
    ( 134, (    -49,    2312,     -223),  +94.76),  # measured f134
    ( 135, (    -52,    2360,     -311),  +95.80),  # measured f135
    ( 136, (    -55,    2383,     -387),  +96.76),  # measured f136
    ( 137, (    -58,    2383,     -447),  +97.63),  # measured f137
    ( 138, (    -61,    2364,     -493),  +98.47),  # measured f138
    ( 139, (    -62,    2343,     -527),  +99.19),  # measured f139
    ( 140, (    -64,    2328,     -553),  +99.85),  # measured f140
    ( 141, (    -67,    2318,     -573), +100.42),  # measured f141
    ( 142, (    -69,    2305,     -584), +100.88),  # measured f142
    ( 143, (    -73,    2286,     -584), +101.23),  # measured f143
    ( 144, (    -76,    2260,     -577), +101.49),  # measured f144
    ( 145, (    -79,    2227,     -560), +101.63),  # measured f145
    ( 146, (    -84,    2185,     -533), +101.83),  # measured f146
    ( 147, (    -89,    2133,     -496), +102.21),  # measured f147
    ( 148, (    -95,    2070,     -448), +102.63),  # measured f148
    ( 149, (   -104,    2000,     -389), +103.06),  # measured f149
    ( 150, (   -166,    1916,      480), +103.53),  # measured f150
    ( 151, (   -229,    1941,     1348), +104.02),  # measured f151
    ( 152, (   -293,    1975,     2207), +104.57),  # measured f152
    ( 153, (   -355,    2019,     3056), +230.60),  # gap f153
    ( 154, (   -429,    2072,     3882), +230.60),  # gap f154
    ( 155, (   -739,    2059,     4497), +230.60),  # gap f155
    ( 156, (  -1154,    2022,     5002), +230.60),  # measured f156
    ( 157, (  -1540,    2009,     4514), +230.60),  # measured f157
    ( 158, (  -1942,    1898,     3834), +230.60),  # measured f158
    ( 159, (  -2361,    1792,     2969), +230.60),  # measured f159
    ( 160, (  -2799,    1689,     1917), +230.60),  # measured f160
    ( 161, (  -3241,    1590,      692), +230.60),  # measured f161
    ( 162, (  -3463,    1571,     -519), +230.60),  # measured f162
    ( 163, (  -3564,    1595,    -1799), +230.60),  # measured f163
    ( 164, (  -3630,    1621,    -3066), +230.60),  # measured f164
    ( 165, (  -3665,    1648,    -4305), +230.60),  # measured f165
    ( 166, (  -3682,    1670,    -5359), +230.60),  # measured f166
    ( 167, (  -3680,    1690,    -6227), +230.60),  # measured f167
    ( 168, (  -3661,    1704,    -6909), +230.60),  # measured f168
    ( 169, (  -3626,    1717,    -7406), +230.60),  # measured f169
    ( 170, (  -3602,    1725,    -7741), +230.60),  # measured f170
    ( 171, (  -3590,    1730,    -7915), +230.60),  # measured f171
    ( 172, (  -3591,    1730,    -7929), +230.60),  # measured f172
    ( 173, (  -3591,    1730,    -7941), +230.60),  # measured f173
    ( 174, (  -3591,    1729,    -7954), +230.60),  # measured f174
    ( 175, (  -3010,    2711,    -3944), +230.60),  # measured f175
    ( 176, (  -2436,    3709,       76), +230.60),  # measured f176
    ( 177, (  -1889,    4762,     4108), +230.60),  # measured f177
    ( 178, (  -1369,    5870,     8153), +235.78),  # measured f178
    ( 179, (   -877,    7032,    12210), +235.64),  # measured f179
    ( 180, (   -414,    8246,    16278), +235.32),  # measured f180
    ( 181, (     18,    9514,    20357), +235.02),  # measured f181
    ( 182, (   -161,    9847,    20424), +234.67),  # measured f182
    ( 183, (   -365,   10212,    20493), +234.34),  # measured f183
    ( 184, (   -573,   10568,    20559), +234.05),  # measured f184
    ( 185, (   -787,   10913,    20623), +233.71),  # measured f185
    ( 186, (  -1004,   11246,    20685), +233.36),  # measured f186
    ( 187, (  -1227,   11566,    20744), +233.04),  # measured f187
    ( 188, (  -1452,   11872,    20804), +232.74),  # measured f188
    ( 189, (  -1680,   12166,    20862), +232.39),  # measured f189
    ( 190, (  -1912,   12446,    20919), +232.08),  # measured f190
    ( 191, (  -2144,   12712,    20976), +231.78),  # measured f191
    ( 192, (  -2378,   12964,    21033), +231.43),  # measured f192
    ( 193, (  -2609,   13201,    21089), +231.11),  # measured f193
    ( 194, (  -2842,   13425,    21147), +230.80),  # measured f194
    ( 195, (  -3074,   13636,    21205), +230.46),  # measured f195
    ( 196, (  -3305,   13833,    21263), +230.15),  # measured f196
    ( 197, (  -3535,   14017,    21320), +229.83),  # measured f197
    ( 198, (  -3764,   14187,    21376), +229.49),  # measured f198
    ( 199, (  -3993,   14345,    21432), +229.14),  # measured f199
    ( 200, (  -4224,   14491,    21486), +228.83),  # measured f200
    ( 201, (  -4437,   14638,    21529), +228.54),  # measured f201
    ( 202, (  -3832,   15542,    20649), +228.18),  # measured f202
    ( 203, (  -3192,   16444,    19751), +227.89),  # measured f203
    ( 204, (  -2516,   17348,    18840), +227.79),  # measured f204
    ( 205, (  -1804,   18251,    17912), +231.68),  # measured f205
    ( 206, (  -1061,   19156,    16974), +232.87),  # measured f206
    ( 207, (   -285,   20067,    16024), +234.03),  # measured f207
    ( 208, (    507,   20969,    15074), +235.17),  # measured f208
    ( 209, (    512,   21111,    15038), +236.23),  # measured f209
    ( 210, (    513,   21254,    15009), +237.20),  # measured f210
    ( 211, (    509,   21397,    14985), +238.18),  # measured f211
    ( 212, (    500,   21542,    14969), +239.20),  # measured f212
    ( 213, (    490,   21691,    14958), +240.00),  # measured f213
    ( 214, (    477,   21838,    14951), +240.86),  # measured f214
    ( 215, (    464,   21985,    14947), +241.77),  # measured f215
    ( 216, (    451,   22118,    14945), +242.56),  # measured f216
    ( 217, (    437,   22250,    14947), +243.27),  # measured f217
    ( 218, (    422,   22378,    14952), +243.95),  # measured f218
    ( 219, (    407,   22502,    14959), +244.23),  # measured f219
    ( 220, (    393,   22621,    14968), +245.00),  # measured f220
    ( 221, (    379,   22735,    14978), +245.56),  # measured f221
    ( 222, (    365,   22844,    14990), +246.09),  # measured f222
    ( 223, (    351,   22958,    15002), +246.57),  # measured f223
    ( 224, (    337,   23064,    15015), +247.14),  # measured f224
    ( 225, (    324,   23164,    15029), +247.64),  # measured f225
    ( 226, (    311,   23256,    15043), +248.05),  # measured f226
    ( 227, (    300,   23342,    15056), +248.39),  # measured f227
    ( 228, (    288,   23417,    15068), +248.78),  # measured f228
    ( 229, (    278,   23485,    15080), +249.13),  # measured f229
    ( 230, (    268,   23543,    15091), +249.33),  # measured f230
    ( 231, (    262,   23591,    15100), +249.60),  # measured f231
    ( 232, (    256,   23629,    15108), +249.84),  # measured f232
    ( 233, (    252,   23657,    15115), +249.99),  # measured f233
    ( 234, (    311,   23525,    15544), +250.07),  # measured f234
    ( 235, (    372,   23385,    15972), +250.15),  # measured f235
    ( 236, (    434,   23240,    16399), +250.23),  # measured f236
    ( 237, (    498,   23100,    16826), +106.87),  # measured f237
    ( 238, (    560,   22968,    17253), +106.87),  # measured f238
    ( 239, (    624,   22835,    17678), +106.87),  # measured f239
    ( 240, (    685,   22709,    18104), +106.87),  # measured f240
    ( 241, (    668,   22757,    18110), +106.87),  # measured f241
    ( 242, (    632,   22838,    18115), +106.87),  # measured f242
    ( 243, (    570,   22954,    18110), +106.57),  # measured f243
    ( 244, (    484,   23095,    18084), +103.91),  # measured f244
    ( 245, (    376,   23255,    18023), +100.62),  # measured f245
    ( 246, (    254,   23432,    17920),  +96.66),  # measured f246
    ( 247, (    130,   23607,    17766),  +92.54),  # measured f247
    ( 248, (     23,   23753,    17552),  +88.61),  # measured f248
    ( 249, (    -61,   23869,    17314),  +84.92),  # measured f249
    ( 250, (   -108,   23928,    17024),  +81.74),  # measured f250
    ( 251, (   -116,   23924,    16690),  +79.00),  # measured f251
    ( 252, (    -89,   23867,    16345),  +78.17),  # measured f252
    ( 253, (    -43,   23788,    16033),  +75.98),  # measured f253
    ( 254, (     13,   23697,    15762),  +74.13),  # measured f254
    ( 255, (     74,   23609,    15538),  +72.41),  # measured f255
    ( 256, (    137,   23514,    15331),  +70.70),  # measured f256
    ( 257, (    194,   23435,    15178),  +69.21),  # measured f257
    ( 258, (    241,   23380,    15084),  +67.83),  # measured f258
    ( 259, (    279,   23345,    15030),  +66.48),  # measured f259
    ( 260, (    318,   23311,    14980),  +65.10),  # measured f260
    ( 261, (    357,   23278,    14933),  +63.97),  # measured f261
    ( 262, (    398,   23245,    14890),  +62.84),  # measured f262
    ( 263, (    433,   23214,    14846),  +61.82),  # measured f263
    ( 264, (    476,   23183,    14806),  +60.86),  # measured f264
    ( 265, (    511,   23152,    14764),  +60.04),  # measured f265
    ( 266, (    554,   23121,    14724),  +59.27),  # measured f266
    ( 267, (    590,   23090,    14683),  +58.58),  # measured f267
    ( 268, (    629,   23060,    14643),  +57.93),  # measured f268
    ( 269, (    663,   23029,    14601),  +57.43),  # measured f269
    ( 270, (    704,   22999,    14562),  +57.02),  # measured f270
    ( 271, (    735,   22968,    14520),  +56.68),  # measured f271
    ( 272, (    773,   22938,    14481),  +56.38),  # measured f272
    ( 273, (    805,   22912,    14440),  +56.21),  # measured f273
    ( 274, (    845,   22888,    14404),  +56.12),  # measured f274
    ( 275, (    882,   22866,    14368),  +55.86),  # measured f275
    ( 276, (    923,   22846,    14336),  +55.17),  # measured f276
    ( 277, (    965,   22831,    14304),  +54.55),  # measured f277
    ( 278, (   1009,   22817,    14276),  +53.93),  # measured f278
    ( 279, (   1054,   22805,    14249),  +53.33),  # measured f279
    ( 280, (   1098,   22792,    14223),  +52.74),  # measured f280
    ( 281, (   1141,   22781,    14196),  +52.23),  # measured f281
    ( 282, (   1185,   22770,    14170),  +51.70),  # measured f282
    ( 283, (   1227,   22759,    14144),  +51.27),  # measured f283
    ( 284, (   1270,   22746,    14120),  +50.83),  # measured f284
    ( 285, (   1312,   22734,    14095),  +50.38),  # measured f285
    ( 286, (   1353,   22723,    14072),  +49.98),  # measured f286
    ( 287, (   1395,   22711,    14049),  +49.65),  # measured f287
    ( 288, (   1435,   22698,    14027),  +49.32),  # measured f288
    ( 289, (   1475,   22685,    14005),  +49.05),  # measured f289
    ( 290, (   1514,   22671,    13984),  +48.79),  # measured f290
    ( 291, (   1553,   22659,    13963),  +48.53),  # measured f291
    ( 292, (   1591,   22646,    13942),  +48.29),  # measured f292
    ( 293, (   1628,   22631,    13921),  +48.11),  # measured f293
    ( 294, (   1664,   22616,    13900),  +47.97),  # measured f294
    ( 295, (   1700,   22601,    13879),  +47.88),  # measured f295
    ( 296, (   1732,   22586,    13858),  +47.80),  # measured f296
    ( 297, (   1759,   22572,    13842),  +47.71),  # measured f297
    ( 298, (   1882,   22744,    13820),  +47.68),  # measured f298
    ( 299, (   1777,   20684,    11211),  +47.74),  # measured f299
    ( 300, (   1736,   18640,     8599),  +47.74),  # measured f300
    ( 301, (   1760,   16633,     5977),  +47.74),  # gap f301
    ( 302, (   1850,   14663,     3344),  +90.59),  # gap f302
    ( 303, (   1749,   12732,      708),  +90.81),  # gap f303
    ( 304, (   1605,   10835,    -1938),  +91.41),  # gap f304
    ( 305, (   1339,    8790,    -4583),  +92.03),  # measured f305
    ( 306, (   1288,    9013,    -4647),  +92.68),  # measured f306
    ( 307, (   1162,    9259,    -4715),  +93.35),  # measured f307
    ( 308, (    961,    9505,    -4778),  +93.96),  # measured f308
    ( 309, (    687,    9740,    -4849),  +94.57),  # measured f309
    ( 310, (    595,    9951,    -4961),  +95.23),  # measured f310
    ( 311, (    537,   10141,    -5102),  +95.90),  # measured f311
    ( 312, (    495,   10317,    -5266),  +96.52),  # measured f312
    ( 313, (    455,   10479,    -5448),  +97.14),  # measured f313
    ( 314, (    418,   10627,    -5644),  +97.73),  # measured f314
    ( 315, (    379,   10768,    -5852),  +98.42),  # measured f315
    ( 316, (    339,   10910,    -6053),  +99.07),  # measured f316
    ( 317, (    301,   11065,    -6224),  +99.66),  # measured f317
    ( 318, (    266,   11234,    -6372), +100.31),  # measured f318
    ( 319, (    230,   11407,    -6500), +100.95),  # measured f319
    ( 320, (    196,   11586,    -6613), +101.60),  # measured f320
    ( 321, (    161,   11768,    -6713), +102.26),  # measured f321
    ( 322, (    128,   11947,    -6802), +102.85),  # measured f322
    ( 323, (     95,   12130,    -6882), +103.46),  # measured f323
    ( 324, (     63,   12312,    -6955), +104.10),  # measured f324
    ( 325, (     31,   12491,    -7019), +104.74),  # measured f325
    ( 326, (      2,   12671,    -7077), +105.42),  # measured f326
    ( 327, (    -28,   12848,    -7129), +106.00),  # measured f327
    ( 328, (    -54,   13021,    -7175), +106.63),  # measured f328
    ( 329, (    -80,   13193,    -7217), +107.35),  # measured f329
    ( 330, (   -105,   13352,    -7253), +107.98),  # measured f330
    ( 331, (   -125,   13491,    -7283), +108.55),  # measured f331
    ( 332, (   -142,   13611,    -7306), +109.20),  # measured f332
    ( 333, (   -155,   13708,    -7323), +109.66),  # measured f333
    ( 334, (   -164,   13782,    -7333), +109.66),  # measured f334
    ( 335, (   -132,   13630,    -7258), +109.66),  # measured f335
    ( 336, (   -107,   13452,    -7187), +109.66),  # measured f336
    ( 337, (    -87,   13253,    -7138), +109.66),  # measured f337
    ( 338, (    -73,   13046,    -7110), +285.52),  # measured f338
    ( 339, (    -60,   12832,    -7103), +283.97),  # measured f339
    ( 340, (    -47,   12614,    -7112), +279.57),  # measured f340
    ( 341, (    -31,   12396,    -7137), +275.11),  # measured f341
    ( 342, (    -51,   12380,    -7254), +270.74),  # measured f342
    ( 343, (    -55,   12368,    -7374), +266.37),  # measured f343
    ( 344, (    -46,   12362,    -7475), +262.22),  # measured f344
    ( 345, (    -28,   12360,    -7558), +258.31),  # measured f345
    ( 346, (     -3,   12363,    -7624), +254.79),  # measured f346
    ( 347, (     25,   12367,    -7674), +251.63),  # measured f347
    ( 348, (     52,   12370,    -7709), +248.93),  # measured f348
    ( 349, (     79,   12376,    -7733), +246.62),  # measured f349
    ( 350, (    100,   12383,    -7747), +244.78),  # measured f350
    ( 351, (    118,   12389,    -7753), +243.38),  # measured f351
    ( 352, (    131,   12393,    -7758), +242.46),  # measured f352
    ( 353, (    142,   12397,    -7765), +241.98),  # measured f353
    ( 354, (    153,   12400,    -7776), +241.85),  # measured f354
    ( 355, (    162,   12405,    -7791), +241.84),  # measured f355
    ( 356, (    171,   12407,    -7813), +241.82),  # measured f356
    ( 357, (    184,   12410,    -7839), +241.82),  # measured f357
    ( 358, (    195,   12414,    -7872), +241.82),  # measured f358
    ( 359, (    210,   12419,    -7907), +241.82),  # measured f359
    ( 360, (    226,   12424,    -7942), +241.82),  # measured f360
    ( 361, (    241,   12430,    -7976), +241.82),  # measured f361
    ( 362, (    257,   12434,    -8011), +241.82),  # measured f362
    ( 363, (    273,   12440,    -8045), +241.83),  # measured f363
    ( 364, (    290,   12446,    -8080), +241.82),  # measured f364
    ( 365, (    307,   12452,    -8114), +241.81),  # measured f365
    ( 366, (    324,   12456,    -8150), +241.80),  # measured f366
    ( 367, (    340,   12460,    -8187), +241.81),  # measured f367
    ( 368, (    355,   12463,    -8226), +241.81),  # measured f368
    ( 369, (    369,   12467,    -8266), +241.82),  # measured f369
    ( 370, (    380,   12470,    -8308), +241.81),  # measured f370
    ( 371, (    390,   12472,    -8351), +241.81),  # measured f371
    ( 372, (    397,   12473,    -8395), +241.82),  # measured f372
    ( 373, (    403,   12473,    -8440), +241.82),  # measured f373
    ( 374, (    407,   12471,    -8488), +241.81),  # measured f374
    ( 375, (    412,   12468,    -8537), +241.81),  # measured f375
    ( 376, (    416,   12463,    -8589), +241.82),  # measured f376
    ( 377, (    423,   12460,    -8642), +241.81),  # measured f377
    ( 378, (    431,   12456,    -8696), +241.80),  # measured f378
    ( 379, (    444,   12444,    -8748), +241.79),  # measured f379
    ( 380, (    386,   12597,    -8621), +241.79),  # measured f380
    ( 381, (    328,   12751,    -8485), +241.81),  # measured f381
    ( 382, (    269,   12907,    -8341), +241.84),  # measured f382
    ( 383, (    208,   13063,    -8189), +258.76),  # measured f383
    ( 384, (    153,   13241,    -7985), +258.76),  # measured f384
    ( 385, (    100,   13441,    -7779), +258.76),  # measured f385
    ( 386, (     41,   13666,    -7593), +258.76),  # measured f386
    ( 387, (     53,   13745,    -7581), +258.76),  # measured f387
    ( 388, (     65,   13839,    -7577), +258.76),  # measured f388
    ( 389, (     79,   13940,    -7572), +258.76),  # measured f389
    ( 390, (     92,   14039,    -7571), +258.76),  # measured f390
    ( 391, (     99,   14108,    -7612), +258.76),  # measured f391
    ( 392, (    103,   14143,    -7647), +258.64),  # measured f392
    ( 393, (    109,   14146,    -7653), +258.25),  # measured f393
    ( 394, (    114,   14107,    -7653), +257.62),  # measured f394
    ( 395, (    117,   14030,    -7636), +256.66),  # measured f395
    ( 396, (    117,   13916,    -7608), +255.60),  # measured f396
    ( 397, (    112,   13773,    -7560), +254.53),  # measured f397
    ( 398, (    101,   13601,    -7489), +253.45),  # measured f398
    ( 399, (     91,   13435,    -7420), +252.44),  # measured f399
    ( 400, (     95,   13297,    -7369), +251.53),  # measured f400
    ( 401, (    120,   13191,    -7332), +250.72),  # measured f401
    ( 402, (      9,   12927,    -7222), +238.77),  # measured f402
    ( 403, (    -89,   12697,    -7157), +227.35),  # measured f403
    ( 404, (   -102,   12473,    -7167), +215.92),  # measured f404
    ( 405, (     -1,   12219,    -7156), +204.42),  # measured f405
    ( 406, (    201,   11922,    -7067), +192.98),  # measured f406
    ( 407, (    478,   11562,    -6863), +181.53),  # measured f407
    ( 408, (    800,   11156,    -6533), +170.08),  # measured f408
    ( 409, (   1298,   10876,    -6148), +158.65),  # measured f409
    ( 410, (   1610,   10715,    -6006), +147.21),  # measured f410
    ( 411, (   1937,   10526,    -5726), +135.79),  # measured f411
    ( 412, (   2236,   10356,    -5384), +124.27),  # measured f412
    ( 470, (   2236,   10356,    -5384),  +96.38),  # fire column (camera off him, f470)
    ( 520, (   2236,   10356,    -5384), +119.60),  # fire column (camera off him, f520)
)

# THOMAS_END = 520 (KEYFRAMES_V10[-1][0], the last tuple's own frame): the donor's WaitSFXDone-gated
# cast length. This comment used to read "580" -- stale documentation drift against the actual last
# KEYFRAMES_V10 tuple (frame 520); the code and the deployed artifact have always agreed at 520, only
# the inline comment disagreed with both. Fixed 2026-07-23 per m0/M1A-PLAN.md sec 2.2's flagged note.
THOMAS_END = KEYFRAMES_V10[-1][0]

# Third-party asset sources -- OUTSIDE the repo, never committed (CLAUDE.md provenance law; the repo's
# blanket *.fbx gitignore already makes an accidental commit structurally impossible, this is belt-
# and-suspenders: the paths themselves live only in this script, not the asset bytes).
SCRATCH_DIR = Path(r"C:\gd\SCRATCH\thomas")
THOMAS_FBX_SRC = SCRATCH_DIR / "blender_out" / "thomas_normalized.fbx"   # produced by blender_normalize.py
THOMAS_TEX_SRC = SCRATCH_DIR / "Thomas_d.png"                            # the original, untouched

# --dry-run staging root -- CLAUDE.md's provenance law applies here too: the spliced PlayerSequence.seq
# a dry run produces is a DERIVATIVE of stock ef227's real Square-Enix bytes (it's built by splicing our
# own delta into a verified-byte-identical copy of the donor's own file), so a staged/inspectable copy of
# it belongs under the same C:/gd/SCRATCH/ tree every other extracted-stock-content output in this study
# uses -- never under studies/.../out/ (that's still inside the repo; `studies/*/out/` is gitignored but
# only one path segment deep, and in any case "gitignored" isn't the bar here, "not in the repo tree at
# all" is). `--dry-run` mirrors the mod folder's own relative layout one level under here so paths stay
# directly comparable to a real deploy's own <mod_root>/... paths.
DRY_RUN_ROOT = Path(r"C:\gd\SCRATCH\summon-transplant") / "m1a_dry_run"


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


# --------------------------------------------------------------------------- M1a (2026-07-23, m0/M1A-PLAN.md sec 2) -- camera-inheritance isolation build
# M1a swaps the FLIGHT v10 KEYFRAMES_V10 flight (above) for ONE static Movement/Rotation piece spanning
# the whole cast, holding Thomas fixed in WORLD space while the real cinematic camera cuts/dollies/zooms
# around him -- isolating "does camera inheritance work at all" (TRANSPLANT.md sec 1.1's "for free" claim)
# from "does our own flight match the real one" (what KEYFRAMES_V10 is solved for). See M1A-PLAN.md sec 3
# for the full success/failure read.
#
# The point is not invented: it is PROBE.md's own "P1 dest (entrance settle)" row -- the median, across
# Bahamut's 7 real body-mesh keys (HIDE_KEYS above), of his own on-screen world position at frame 82, the
# exact instant the real creature first becomes visible and the camera settles on him after the
# cave-entrance swoop. M1A-PLAN.md sec 2.2 states the caveat plainly: Bahamut's own trajectory revisits
# roughly this neighborhood at several other beats and diverges wildly during the sky-charge excursion --
# a single static point reading near-frame at some beats and off-frame at others is the EXPECTED,
# informative M1a result, not a defect to fix.
M1A_STATIC_POINT: "tuple[float, float, float]" = (132.5, 511.5, -1568)


def _num(v: float) -> str:
    """Render a coordinate the same way ``KEYFRAMES_V10``'s literal tuples do when passed through
    ``str()``: a whole number renders bare (``"-1568"``, not ``"-1568.0"``), a fractional value keeps
    its decimal (``"132.5"``)."""
    return str(int(v)) if float(v).is_integer() else str(v)


def build_manifest_json_m1a() -> dict:
    """Generate the M1a static-hold manifest (schema per ``ParametricMovement.LoadFromJSON``, same as
    ``build_manifest_json()`` above -- see M1A-PLAN.md sec 2.2 for the literal JSON this reproduces and
    the reasoning behind every value):

    - ONE ``Movement`` piece and ONE ``Rotation`` piece, each spanning ``[0, THOMAS_END)`` -- Origin ==
      Destination on every axis (a zero-length move: Thomas never travels in world space).
    - Held at ``M1A_STATIC_POINT`` -- genuine Unity world space (PROBE.md's own measurement, not a guess
      -- see the module comment above).
    - Rotation ``OriginY=DestinationY=0`` -- an explicit non-claim, not a measured facing (nothing in
      this study has measured Bahamut's own body facing at frame 82; ``0`` matches
      ``blender_normalize.py``'s own normalized-facing convention). ``*Z`` stays ``"0"`` -- no roll,
      same as every ``KEYFRAMES_V10`` piece.
    - No ``"Animations"`` key -- Thomas's raw FBX is fully rigid (no skeleton, no clips), same reason
      ``build_manifest_json()`` above never emits one.
    - ``Scaling`` unchanged at ``THOMAS_SCALE`` -- keeps the same physical scale v10.1 already uses, so a
      before/after against the currently-deployed FLIGHT v10.1 build isolates exactly one variable
      (motion vs. no motion), not two (motion and size)."""
    x, y, z = M1A_STATIC_POINT
    movement = [{
        "Duration": str(THOMAS_END),
        "OriginX": _num(x), "OriginY": _num(y), "OriginZ": _num(z),
        "DestinationX": _num(x), "DestinationY": _num(y), "DestinationZ": _num(z),
    }]
    rotation = [{
        "Duration": str(THOMAS_END),
        "OriginY": "0", "DestinationY": "0",
        "OriginZ": "0", "DestinationZ": "0",
    }]
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


def build_thomas(mod_root: Path, game_path: Path, hide_keys: "tuple[str, ...] | None" = HIDE_KEYS,
                  manifest_fn=build_manifest_json, dry_run: bool = False) -> dict:
    """``manifest_fn`` (default ``build_manifest_json``, the FLIGHT v10.1 flight) is the single knob
    M1a adds -- pass ``build_manifest_json_m1a`` for the static-hold build instead; every other step
    (the .seq splice, FileList.txt, the mint) is reused verbatim regardless of which manifest is built,
    per M1A-PLAN.md sec 2.3 ("reuse rung-7 verbatim, ZERO new engine code"). The committed
    ``thomas_manifest.sfxmodel`` repo copy is synced ONLY for the FLIGHT build (``manifest_fn is
    build_manifest_json``) and never on ``dry_run`` -- an ``--m1a`` / custom-``manifest_fn`` build leaves the
    committed v10.1 flight source-of-truth intact (see that write's own comment for why)."""
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
    manifest_bytes = (json.dumps(manifest_fn(), indent=2) + "\n").encode("utf-8")
    # Sync the committed repo copy ONLY on a FLIGHT (--thomas) build. THOMAS_MANIFEST_REPO_PATH is the git
    # source-of-truth for the DEPLOYED v10.1 flight; an --m1a run builds the 791-byte static-hold JSON, which
    # must NOT overwrite it (a later commit would silently drop v10.1 from HEAD). Gating on the FLIGHT
    # manifest_fn makes this match main()'s printed guarantee ("only a --thomas build syncs it") and the
    # --m1a runbook's "the repo's thomas_manifest.sfxmodel is left untouched". --dry-run never touches it
    # either (a dry run's whole point is generate-and-inspect, nothing written outside its own staging area).
    if not dry_run and manifest_fn is build_manifest_json:
        _write(THOMAS_MANIFEST_REPO_PATH, manifest_bytes)   # keep the committed FLIGHT copy in sync
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
                        help="deploy the Thomas swap, FLIGHT v10.1 (DEFAULT if no flag given)")
    group.add_argument("--m1a", action="store_true",
                        help="deploy the M1a static-hold manifest instead of the FLIGHT v10 KEYFRAMES_V10 "
                             "flight -- one fixed Movement/Rotation piece spanning the whole cast, no "
                             "Animations array (Thomas has no clips). Same .seq splice, same HIDE_KEYS, "
                             "same mint as --thomas. Isolates camera-inheritance from flight-matching. "
                             "See m0/M1A-PLAN.md sec 2.")
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
    parser.add_argument("--dry-run", action="store_true",
                         help="stage every artifact under a local folder "
                              f"({DRY_RUN_ROOT}\\<mod folder>\\...) instead of writing into the real game "
                              "install's mod folder, and skip the thomas_manifest.sfxmodel repo-copy sync "
                              "-- generate + inspect only, nothing is deployed. The real stock "
                              "ef227/PlayerSequence.seq is still READ (never written) to build the "
                              "spliced output. Works with --thomas, --m1a, and --restore alike.")
    args = parser.parse_args()
    if args.restore:
        mode = "restore"
    elif args.m1a:
        mode = "m1a"
    else:
        mode = "thomas"

    if mode == "restore" and (args.hide_keys or args.calibrate):
        parser.error("--hide-keys/--calibrate only apply to a Thomas-swap or --m1a deploy, not --restore")

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
    if args.dry_run:
        import shutil
        mod_root = DRY_RUN_ROOT / mod_root.name
        if mod_root.exists():
            shutil.rmtree(mod_root)

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}" + ("  *** DRY RUN -- staged locally, real mod folder NOT touched ***"
                                           if args.dry_run else ""))
    print(f"private id   : ef{FRESH_EF_ID:03d} (rung 3/7's fresh-id folder -- reused, not re-minted)")
    mode_label = {
        "thomas": "THOMAS SWAP (FLIGHT v10.1)",
        "m1a": "M1A STATIC HOLD (camera-inheritance isolation test, m0/M1A-PLAN.md sec 2)",
        "restore": "RESTORE (rung-7 resting state)",
    }[mode]
    print(f"mode         : {mode_label}")
    if mode in ("thomas", "m1a"):
        if hide_keys is None:
            print("hide keys    : CALIBRATE -- no HideMeshes argument at all (Bahamut renders unsuppressed)")
        else:
            print(f"hide keys    : {len(hide_keys)} key(s) -- " + ",".join(f"0x{k}" for k in hide_keys))
    print()

    try:
        if mode in ("thomas", "m1a"):
            manifest_fn = build_manifest_json_m1a if mode == "m1a" else build_manifest_json
            result = build_thomas(mod_root, game_path, hide_keys, manifest_fn=manifest_fn, dry_run=args.dry_run)
        else:
            result = restore(mod_root, game_path)
    except (DriftError, ThomasAssetError) as e:
        print(f"REFUSING TO BUILD:\n  {e}", file=sys.stderr)
        return 1

    if mode in ("thomas", "m1a"):
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
        manifest_label = ("GENERATED thomas_manifest.sfxmodel (FLIGHT v10.1)" if mode == "thomas"
                           else "GENERATED M1a static-hold manifest, m0/M1A-PLAN.md sec 2.2")
        print(f"=== {CREATURE_MANIFEST_REL} ({manifest_label} -- overwrites rung 7's Iviv-clone one) ===")
        print(f"written  : {result['manifest_dest']}")
        print(f"  sha256 : {result['manifest_sha256']}")
        if mode == "thomas":
            if not args.dry_run:
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
        else:
            print("M1a STATIC HOLD -- NOT a flight (see m0/M1A-PLAN.md sec 2 for the full design + sec 3 for")
            print("the success/failure read); the repo's thomas_manifest.sfxmodel is left untouched (only a")
            print("--thomas build syncs it):")
            print(f"  ONE Movement/Rotation piece, Start=0 / End={THOMAS_END}, held fixed at world point")
            print(f"  {M1A_STATIC_POINT} -- PROBE.md's P1 dest ('entrance settle'), the median across")
            print("  Bahamut's 7 real body-mesh keys of his own screen position at frame 82. No Animations")
            print("  array (Thomas has no skeleton/clips). Thomas never moves -- any apparent on-screen")
            print("  motion is the real cinematic camera cutting/dollying/zooming around him.")
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
        if args.dry_run:
            print("*** DRY RUN -- nothing above was written into the real game install or the repo's own")
            print(f"*** {THOMAS_MANIFEST_REPO_PATH.name}. Inspect the staged files under {mod_root}, then")
            print("*** re-run without --dry-run to actually deploy (see the '## M1a' runbook in M1A-PLAN.md).")
        elif m["directive_added"]:
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
        if args.dry_run:
            print(f"is fully removed under the staged {mod_root} -- *** DRY RUN, the real game install was")
            print("*** never touched. ***")
        else:
            print("is fully removed. A relaunch clears the now-unregistered GEO id from FF9BattleDB.GEO's runtime")
            print("dict (harmless either way -- nothing references it once removed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
