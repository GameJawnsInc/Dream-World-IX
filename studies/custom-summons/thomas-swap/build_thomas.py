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
     the named FLIGHT v5 constants below by ``build_manifest_json()`` -- Bahamut's OWN measured world
     flight, tracked frame-by-frame; the repo copy is kept in sync so it stays git-diffable) -> that same filename
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
section, and the local-only provenance note. See PROBE.md for the mesh-probe key classification and
matrix_solve.py for the FLIGHT v5 solve this build's placement is derived from.

THE FLIGHT v5 (2026-07-22, TRACK BAHAMUT -- THE FINAL SOLVE; supersedes v1-v4, see the FLIGHT v5 comment
block below the constants for the full case): the corrected target is that Bahamut's cinematic
DELIBERATELY swoops the creature off-screen while the camera follows his blast -- so faithful = "Thomas
is wherever Bahamut was", off-frame beats included, NOT "keep Thomas centered". The s50 probe logs the
actual per-frame render matrices (``camera.worldToCameraMatrix``/``.projectionMatrix``, ``SFX.cs:
1603-1604``) and they PAN + ZOOM (not static -- overturning FLIGHT v4's premise; the CAM-Transform v4
read was a decoy nothing writes per-frame). Since Thomas is rendered by that SAME baked camera, placement
is camera-independent: put him at Bahamut's OWN measured world position each frame (``matrix_solve.py``:
median of the 7 body-mesh keys, pool-pollution heuristic) and the real camera reproduces his exact screen
trajectory for free. No FOV assumption, no camera model -- ``viewspace_place.py`` (v4) and
``ef_camera_decode.py``/``ef_camera_solve.py`` (v3) are retained only as the superseded record.
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
# THE FLIGHT v5 (TRACK BAHAMUT) bakes the measured world trajectory below as constants; the tool that
# DERIVED them from the s50 probe log is matrix_solve.py (this dir). build-time needs no game log or
# viewspace_place.py (FLIGHT v4's now-superseded assumed-static-camera model -- see the FLIGHT v5 block).

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

# --------------------------------------------------------------------------- THE FLIGHT v5 (2026-07-22, TRACK BAHAMUT -- THE FINAL SOLVE)
# THE CORRECTED TARGET (user insight): the real Bahamut cinematic deliberately SWOOPS THE CREATURE
# OFF-SCREEN and PANS THE CAMERA to follow his blast -- the subject is intentionally entering/exiting
# frame at points. So faithfulness is NOT "keep Thomas centered/in-frame every frame" (that would be LESS
# faithful than the dragon he replaces). Faithfulness = **Thomas is wherever Bahamut was, every frame**,
# off-screen swoop-ins and camera-follows-blast beats included.
#
# WHY FLIGHT v1-v4 ARE ALL SUPERSEDED. v1 hovered; v2/v3 placed Thomas at Bahamut's mesh-derived body
# medians but had to GUESS the camera; v4 abandoned that for a VIEW-SPACE construction against a camera it
# believed was STATIC (the s48 CAM hook logged an unchanging Transform). **The s50 probe overturns v4's
# premise.** It logs the actual per-frame render matrices -- ``camera.worldToCameraMatrix`` (VIEW rows) and
# ``camera.projectionMatrix`` (PROJ rows), the very matrices ``SFX.UpdateCamera()`` assigns at
# ``SFX.cs:1603-1604`` -- and they are NOT static: the logged CAM Transform is a decoy (nothing writes it
# per-frame), while VIEW pans/orbits dramatically frame to frame and PROJ *zooms* (its [1][1] focal term
# sweeps ~2.33..4.65 => vertical FOV ~47deg..24deg). v4's whole "assumed fixed 40deg camera" was built on a
# premise the raw render matrices disprove. (matrix_solve.py's module docstring carries the full evidence.)
#
# THE FINAL SOLVE -- placement becomes camera-INDEPENDENT. Thomas is rendered by that SAME per-frame camera
# (ef227's native camera track replays byte-identically every cast). So we do NOT model the camera at all:
# **put Thomas at Bahamut's own measured world position each frame, and the real per-frame VIEW+PROJ
# reproduces Bahamut's exact screen position -- pan, zoom, off-screen swoop and all -- for free.** No FOV
# assumption, no projection guess. matrix_solve.py's own forward projection VERIFIES this: of Bahamut's 324
# on-cast body frames, only ~5 project strictly inside |ndc|<1 -- his body is genuinely off-screen /
# behind the camera for most of the cast (the camera follows the effect/blast, not the creature), which is
# exactly the deliberate off-screen behavior the user described and the reason an always-in-frame check is
# WRONG. We reproduce it by copying his world path verbatim.
#
# HOW THE NUMBERS BELOW WERE DERIVED (matrix_solve.py, from the s50 probe log; re-derive with
#   py matrix_solve.py --step 12 --window 6
# and paste TRACKED_KEYFRAMES / ENTRANCE_ORIGIN / EXIT_DEST). Per frame, Bahamut's world position is the
# MEDIAN across his 7 confirmed body-mesh keys of (X=bounds cx, Y=bounds cy, Z=the FAR CORNER cz-/+ez) --
# the pool-pollution heuristic from PROBE.md round 1 (the SFX vertex pool sits at world origin, so the
# AABB stretches from the real body toward 0; on Z the body is thousands of units out so the far corner
# recovers true depth, while on X/Y it sits near origin so the center is the better estimate). A windowed
# median (+/-6 frames) suppresses single-frame pooling spikes. The result is a coherent flight: he starts
# near (Z~=-1700), DIVES far away (Z~=-18000..-27000 around frames 120-165 -- the deep swoop, keys agree
# tightly there so it is real signal, independently corroborated by the older s47 cast's own -34000 dive),
# then returns to a moderate Z~=-4000..-7000 for the reign/charge/fire-column window through frame 417.
#
# SHIFTWORLD: still a non-issue -- Thomas's JSON-mesh token has its transform.position force-assigned in
# absolute world space every frame (SFXDataMesh.cs:820), never parented under battlebg.btlRoot -- so these
# world coords are used VERBATIM. ORIENTATION: held broadside (YAW_BROADSIDE=90) through the tracked window
# to present his iconic side profile, turning 0->90 on entrance and 90->0 on the exit climb; no Z-roll (he
# is not PSX-inverted -- README axis-verification). NOTE: with the camera now known to pan wildly, a fixed
# world yaw does not hold a constant facing to the lens; a per-frame camera-relative yaw is now COMPUTABLE
# from the VIEW rows (matrix_solve gives them) and is the obvious next refinement if his facing reads
# wrong on video -- left out of this pass to keep the FINAL SOLVE about POSITION, the headline.
#
# TIMING: body frames span 82..417 in the probe's SFX.frameIndex, which aligns with Thomas's own PlaySFX-
# zeroed clock at ~offset 0 (README "Timing math"). Movement: an entrance (0..82) from an off-screen
# origin into the first tracked point; the measured track (82..417) as dense Linear pieces; an exit
# (417..580) climbing away after the body vanishes. Durations sum to THOMAS_END=580 (the donor's own
# WaitSFXDone-gated cast length, unchanged from every prior FLIGHT version).
#
# CAVEAT: the TRACKED 82..417 window is a MEASUREMENT (Bahamut's own logged mesh bounds); the ENTRANCE_
# ORIGIN and EXIT_DEST are the only reasoned-without-ground-truth points (the body is absent outside its
# 82..417 window) -- documented as such, retunable. Per the project's video-for-visual-bugs law, a fresh
# capture of an actual cast is the real next check.
YAW_BROADSIDE = 90                  # Rotation.Y held broadside through the track; Rotation.Z stays 0 (no roll)

# --- the tracked flight: Bahamut's own measured world position, sampled every ~12 frames (matrix_solve.py
# --- --step 12 --window 6, windowed-median of the 7 body keys). (frame, (X, Y, Z)) absolute world. ---
#
# 2026-07-22 ADVERSARIAL-REVIEW CORRECTION: the prior table below was built from matrix_solve.py's
# body_world() BEFORE it filtered THE DEGENERATE-POOL-ROW SIGNATURE (see ProbeLog._is_pool_row's
# docstring) -- a body key with no active geometry that frame doesn't drop out of the log, it reports the
# SFX vertex pool's own fixed unused-slot bounding box (cx=34.5,cy=-0.5,ex=ey=1023.5, IDENTICAL every
# time, verified across all 39 keys in the cast, not just the 7 body keys). 323/324 (99.7%) of this cast's
# body frames had >=1 of the 7 keys in that exact state, folded unfiltered into the per-frame median. Two
# of the OLD table's own headline points turned out to be built from ZERO real content once filtered out:
# frame 166 ("the single deepest point... corroborated by the s47 cast's ~-34000", Z=-30864 old vs -28548
# now -- the old number happened to land close, but had no real data behind it) and frame 417 ("last frame
# his body is logged", (34,0,-4288) old vs (80,229,-5032) now -- a real, material change, since body_world
# _smoothed's fixed +/-6 window was ALSO entirely pool-degenerate for the whole 411-417 tail; the function
# now widens its search window until it finds real content, see its docstring). Regenerated with:
#   py matrix_solve.py --step 12 --window 6
TRACKED_KEYFRAMES: "tuple[tuple[int, tuple[int, int, int]], ...]" = (
    (  82, (   156,    444,   -2344)),
    (  94, (   142,    206,   -5936)),
    ( 106, (   131,    118,   -8976)),
    ( 118, (   145,    118,  -13424)),
    ( 130, (   164,    118,  -20208)),   # into the deep dive (keys agree tightly here -- real)
    ( 142, (   164,    118,  -18800)),
    ( 154, (    35,   -129,   -7832)),
    ( 166, (    44,   -128,  -28548)),   # the single deepest point (re-derived post pool-row filter)
    ( 178, (    96,    -53,   -6704)),
    ( 190, (   132,    102,   -7648)),
    ( 202, (   132,    116,  -10336)),
    ( 214, (   152,    176,   -6192)),
    ( 226, (   152,    151,   -3328)),
    ( 238, (   156,    200,   -3296)),
    ( 250, (   127,    172,   -3136)),   # reign/charge window -- moderate depth, near-center-ish
    ( 262, (   149,     93,   -5232)),
    ( 274, (   167,     90,   -5904)),
    ( 286, (   159,     90,   -6448)),
    ( 298, (   125,     90,   -6768)),
    ( 310, (   180,   -254,   -6128)),
    ( 322, (   134,     18,   -6128)),
    ( 334, (   126,     54,   -7248)),
    ( 346, (   154,    170,   -4288)),
    ( 358, (   170,    187,   -4192)),
    ( 370, (   170,    191,   -4032)),
    ( 382, (   188,    176,   -4032)),
    ( 394, (   112,    130,   -3696)),
    ( 406, (    86,    180,   -4848)),
    ( 417, (    80,    229,   -5032)),   # last frame his body is logged -- then he vanishes (fire column)
)

# The ONLY two reasoned-without-ground-truth points (body absent outside 82..417); re-extrapolated from
# the corrected table above (py matrix_solve.py):
#  ENTRANCE_ORIGIN -- his earliest measured velocity (f82->f94) extended back to frame 0, so the entrance
#                     is a smooth continuation of his real motion into the first tracked point.
#  EXIT_DEST       -- a reasoned dramatic climb-and-recede after his body vanishes at 417 (matrix_solve's
#                     own velocity extrapolation from the new f406->f417 segment drifts only mildly, unlike
#                     the old table's extrapolation which needed an override; kept as a manual dramatic
#                     climb-away rather than the raw extrapolation, since the body is unmeasured past 417
#                     either way and "climb up and recede" reads better than a shallow drift).
ENTRANCE_ORIGIN: "tuple[int, int, int]" = (255, 2068, 22201)
EXIT_DEST: "tuple[int, int, int]" = (34, 4000, -14000)

TRACK_START = TRACKED_KEYFRAMES[0][0]    # 82
TRACK_END = TRACKED_KEYFRAMES[-1][0]     # 417
THOMAS_END = 580                          # donor's WaitSFXDone-gated cast length, unchanged
ENTRANCE_DURATION = TRACK_START           # 0..82
EXIT_DURATION = THOMAS_END - TRACK_END    # 417..580 == 163

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
    are Bahamut's own measured world positions (TRACKED_KEYFRAMES) or the reasoned entrance/exit points,
    see THE FLIGHT v5 comment block above)."""
    x, y, z = xyz
    return {"DestinationX": str(x), "DestinationY": str(y), "DestinationZ": str(z)}


def build_manifest_json() -> dict:
    """Generate ``thomas_manifest.sfxmodel``'s JSON from the FLIGHT v5 (TRACK BAHAMUT) constants above
    (schema verified against ``ParametricMovement.LoadFromJSON``, Memoria/Battle/SFX/ParametricMovement.cs:
    58-136 -- an array of pieces, ``Duration`` + per-axis ``Origin*``/``Destination*``/
    ``InterpolationType*``; an absent ``Origin*`` on piece i>0 CHAINS from the prior piece's own
    ``Destination*``; an absent ``InterpolationType*`` defaults to ``Linear``, l.254).

    Movement is 1 entrance piece + one Linear piece per tracked keyframe transition + 1 exit piece:
      * ENTRANCE (0..TRACK_START, SinusOut): off-screen ENTRANCE_ORIGIN -> the first tracked point,
        easing into Bahamut's real f82 position.
      * TRACK (TRACK_START..TRACK_END): Bahamut's own measured world path, one Linear segment between
        consecutive TRACKED_KEYFRAMES (Origin chained). Linear (not eased) because these are dense
        samples of a continuously-moving body -- the body moves smoothly in WORLD space; the apparent
        on-screen cuts/swoops come from the camera, which is baked into ef227 and replays for free.
      * EXIT (TRACK_END..THOMAS_END, SinusIn): last tracked point -> the reasoned EXIT_DEST climb-away.
    Rotation is a simple 3-piece scheme (independent piece list): turn 0->broadside over the entrance,
    hold broadside through the whole track, turn broadside->0 over the exit. Scaling is one constant
    piece (THOMAS_SCALE, no motion -- apparent size tracks depth via the flight's own Z, faithfully). All
    piece durations sum to THOMAS_END=580 on every axis (asserted below)."""
    movement = [
        {   # ENTRANCE: off-screen origin -> Bahamut's first measured position (smooth arrival)
            "Duration": str(ENTRANCE_DURATION),
            "OriginX": str(ENTRANCE_ORIGIN[0]), "OriginY": str(ENTRANCE_ORIGIN[1]), "OriginZ": str(ENTRANCE_ORIGIN[2]),
            **_pt(TRACKED_KEYFRAMES[0][1]),
            "InterpolationTypeX": "SinusOut", "InterpolationTypeY": "SinusOut", "InterpolationTypeZ": "SinusOut",
        },
    ]
    # TRACK: one Linear segment per keyframe transition (Origin chains from the prior Destination)
    prev_frame = TRACKED_KEYFRAMES[0][0]
    for frame, xyz in TRACKED_KEYFRAMES[1:]:
        movement.append({"Duration": str(frame - prev_frame), **_pt(xyz)})   # Linear default
        prev_frame = frame
    movement.append(
        {   # EXIT: climb away + recede after the body vanishes (reasoned, no ground truth past 417)
            "Duration": str(EXIT_DURATION),
            **_pt(EXIT_DEST),
            "InterpolationTypeX": "SinusIn", "InterpolationTypeY": "SinusIn", "InterpolationTypeZ": "SinusIn",
        }
    )
    rotation = [
        {   # turn from normalized-forward (0) to broadside (90) as he enters
            "Duration": str(ENTRANCE_DURATION),
            "OriginY": "0", "DestinationY": str(YAW_BROADSIDE),
            "OriginZ": "0", "DestinationZ": "0",
            "InterpolationTypeY": "Sinus",
        },
        {   # HOLD broadside through the entire tracked window (present his iconic side profile)
            "Duration": str(TRACK_END - TRACK_START),
            "DestinationY": str(YAW_BROADSIDE), "DestinationZ": "0",
        },
        {   # EXIT: turn back to forward-facing as he climbs away
            "Duration": str(EXIT_DURATION),
            "DestinationY": "0", "DestinationZ": "0",
            "InterpolationTypeY": "Sinus",
        },
    ]
    # invariant: every axis's piece durations sum to THOMAS_END (the cast length)
    assert sum(int(p["Duration"]) for p in movement) == THOMAS_END, "movement durations != THOMAS_END"
    assert sum(int(p["Duration"]) for p in rotation) == THOMAS_END, "rotation durations != THOMAS_END"
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
        print("THE FLIGHT v5 (TRACK BAHAMUT -- THE FINAL SOLVE, 2026-07-22):")
        print(f"  method        : Thomas placed at Bahamut's OWN measured world position each frame; the real")
        print(f"                  per-frame camera (VIEW+PROJ, s50 probe -- pans + zooms, NOT static) reproduces")
        print(f"                  his exact screen path (off-screen swoops included) for free. See matrix_solve.py.")
        print(f"  entrance      : frames 0-{TRACK_START}   off-screen ENTRANCE_ORIGIN={ENTRANCE_ORIGIN} -> first tracked point (SinusOut)")
        print(f"  TRACK         : frames {TRACK_START}-{TRACK_END}  {len(TRACKED_KEYFRAMES)} measured keyframes, Linear between (Bahamut's real world flight)")
        print(f"  exit          : frames {TRACK_END}-{THOMAS_END} last tracked point -> EXIT_DEST={EXIT_DEST} climb-away (SinusIn)")
        print(f"  yaw broadside : {YAW_BROADSIDE} deg held through the track (side profile); 0->90 in, 90->0 out; no roll")
        print()
        print("  tracked world XYZ baked into the manifest (Bahamut's own bounds, windowed-median of 7 body keys):")
        for frame, xyz in TRACKED_KEYFRAMES:
            print(f"    f{frame:<4d} = {xyz}")
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
