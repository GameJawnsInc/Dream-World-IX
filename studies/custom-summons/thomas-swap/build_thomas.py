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
     ``HideMeshes=<HIDE_RANGE>`` clause to that same line (default ``HIDE_RANGE=(0,31)`` -- round 1 of
     bisecting Bahamut's native mesh-index space into a BODY half (hidden) vs an EFFECT half (kept) --
     see README.md's "HideMeshes bisection protocol"; ``--hide-range A,B`` overrides the range for one
     deploy, ``--calibrate`` omits the clause entirely (Bahamut's real mesh renders unsuppressed, for a
     clean composition-reference video)).
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

    py studies/custom-summons/thomas-swap/build_thomas.py                    # deploy w/ default HIDE_RANGE
    py studies/custom-summons/thomas-swap/build_thomas.py --hide-range 32,63 # deploy w/ the OTHER half
    py studies/custom-summons/thomas-swap/build_thomas.py --calibrate        # no HideMeshes at all
    py studies/custom-summons/thomas-swap/build_thomas.py --restore   # back to rung 7's resting state
                                                                        # + Thomas's mint fully removed

See README.md for the full test procedure, the failure-mode table, the HideMeshes bisection protocol,
and the local-only provenance note.
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

# --------------------------------------------------------------------------- HIDEMESHES BISECTION
# The original blanket HideMeshes=0..63 (first shipped 2026-07-21) suppressed Bahamut's body but ALSO
# blanked his summon-swirl/beam/fire-column EFFECT meshes -- the 2026-07-22 calibration-cast video
# showed the user wants those effect meshes KEPT (the fire column engulfing Thomas reads as
# "SPECTACULAR"). HIDE_RANGE is round 1 of bisecting the native creature's mesh-index space into a
# BODY half (assumed low indices -- hide) vs an EFFECT half (assumed high indices -- keep); see
# README.md's "HideMeshes bisection protocol" table for what each round's video should show and which
# half to split next. ``BattleActionCode.cs:394-419`` (``TryGetArgMeshList``) parses each bare decimal
# token in the comma list as a plain index into ``SFXData.RunningInstance.preventedMeshIndices``
# (``SFXData.cs:1377``); unmatched indices are inert (no error), so a narrower range is exactly as safe
# as the original 0-63 blanket, just with less total coverage.
HIDE_RANGE = (0, 31)          # round 1: hide only the first half (0..31 inclusive) of the index space


def _hide_meshes_arg(hide_range: "tuple[int, int] | None") -> str:
    """``hide_range=None`` = CALIBRATE mode: no ``HideMeshes`` argument at all -- the patched line is
    then byte-identical to the stock donor's own ``PlaySFX`` line, i.e. Bahamut's real mesh renders
    completely unsuppressed. Otherwise a generated (not hand-typed) ``"lo,lo+1,...,hi"`` decimal list,
    inclusive both ends."""
    if hide_range is None:
        return ""
    lo, hi = hide_range
    indices = ",".join(str(i) for i in range(lo, hi + 1))
    return f" ; HideMeshes={indices}"


def patched_line(hide_range: "tuple[int, int] | None") -> str:
    return f"{ANCHOR_BASE}{_hide_meshes_arg(hide_range)}\r\n"

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

# --------------------------------------------------------------------------- THE FLIGHT (2026-07-22)
# Playtest report on the first (static) build: "bahamut is invisible, but Thomas just spawns in front
# of Iviv and stays stationary instead of flying around like a dragon. there are also just periods of
# black screen." Re-derived from source (Memoria.Assembly-CSharp) rather than assumed:
#
#   ANCHOR TRUTH (verify-don't-assume result -- this REFUTES the mission's seed hypothesis that
#   Target*/TargetAveragePosition* resolve to the CASTER on this route):
#   Thomas's own quartet runs in a thread spawned by our spliced ``StartThread`` block. Text-DSL
#   ``StartThread`` compiles to a ``RunThread`` op (BattleActionThread.cs:183-193) executed by the
#   MAIN thread (thread 0, whose ``.targetId`` was set to the ability's REAL ``cmd.tar_id`` --
#   "AllEnemy" per rung3.field.toml:147 -- at cast start, UnifiedBattleSequencer.cs:159-160
#   ``threadList[0].targetId = cmd.tar_id``). Our ``StartThread`` line carries no ``Target=`` argument,
#   so at that ``RunThread`` (UnifiedBattleSequencer.cs:1155-1156) ``tmpChar = runningThread.targetId``
#   = the REAL AllEnemy bitmask, and the spawned child thread's OWN ``.targetId`` is set from that same
#   value (:1168 ``copy.targetId = ... tmpChar``) -- NOT reset to 0, NOT the caster. When that child
#   thread later runs ITS OWN ``LoadSFX: SFX=84 ; Char=Caster`` line, the same absent-``Target=``
#   fallback fires again (:326-327 ``tmpChar = runningThread.targetId``, now the CHILD thread's
#   inherited AllEnemy bitmask) feeding ``customRequest.SetupVfxRequest(cmd, sfxArg, caster, tmpChar)``
#   (:330) -- ``Char=Caster`` only ever re-resolves the CASTER argument (staying Iviv, no change), never
#   the target. In ``SetupVfxRequest`` (FF9/BTL_VFX_REQ.cs:57-69) that real bitmask populates ``trg[]``
#   and ``UpdateTargetAveragePosition()`` (:72-91) computes the REAL average of the actual enemies'
#   ``base_pos`` (Y forced to 0). So ``TargetAveragePositionX/Z`` on THIS exact route already resolved
#   to the real enemy formation, not Iviv -- the first manifest's anchor was not "at the caster" by
#   that mechanism. The actual defects were structural: (a) ``CasterPositionY + 20`` is GROUND level
#   (no loom at all for a dragon), (b) Origin==Destination was a deliberate static hold (zero motion),
#   and (c) Thomas's own ~10.1-unit (pre-scale) length -> ~2681 units at THOMAS_SCALE means a
#   ground-level placement's bounding volume alone can sprawl back over a modest early-game arena's
#   short caster<->enemy gap, which combined with (a) reads exactly as "spawns in front of Iviv".
#
#   DESIGN CHOICE: build the flight on full CASTER-RELATIVE offsets anyway (per the mission's
#   direction, rung 7's own in-game-proven pattern -- creature_manifest.sfxmodel:9's
#   "CasterPositionZ + 600" hover, README "toward the enemy side" -- and this session's own
#   composition-lens recon journal), rather than continuing to depend on TargetAveragePosition: it is
#   unambiguous (Iviv's own real position, no scene-specific enemy-formation guesswork), and it
#   directly targets the two REAL defects above (needs elevation + needs motion) regardless of root
#   cause. AXIS CONVENTION (independently confirmed twice): +Z (world, from a PLAYER caster) = toward
#   the enemies -- (1) rung7's own proven "CasterPositionZ + 600 ... toward the enemy side" hover, and
#   (2) Thomas's own axis-verification table (README.md) showing his normalized front (Blender -Y) maps
#   to +Z in the exported file, matching ``ef227/PlayerSequence.seq``'s stock
#   ``MoveToPosition: RelativePosition=(0,0,400) ; Anim=MP_STEP_FORWARD`` (the caster's own forward
#   step, toward the enemies, at positive Z).
#
#   2026-07-22 REDESIGN -- the orchestrator watched the calibration-cast video (both Bahamut and Thomas
#   visible) and derived an authoritative video-seconds timing map: Thomas's own PlaySFX/frame-0 lands
#   at video t~=5-6s, his clock runs FRAMES_PER_VIDEO_SECOND=15, total End=580 frames unchanged. The
#   3-phase build above left the ENTIRE SKY REALM window (t~=13-20 -- Bahamut's iconic hover pose, head
#   close-ups, the charge beginning) with no Thomas at all -- ~8s read as "tons of black screen" in the
#   HideMeshes cast, because Thomas never left ground level while Bahamut's own cinematic went to the
#   sky. THE REDESIGN adds a full ASCENT/SKY REIGN/DIVE arc so Thomas is on screen for that window too,
#   using frames = (t_video - VIDEO_TO_FRAME_OFFSET_S) * FRAMES_PER_VIDEO_SECOND with +/-15-frame
#   tolerance margins folded into each boundary below (not razor's-edge cuts):
#     P1 ENTRANCE     0 .. P1_ENTRANCE_DURATION                        -- t~=6-11, the proven cave shots
#                                                                          (unchanged path, just faster)
#     P2 ASCENT        .. + P2_ASCENT_DURATION                         -- t~=11-14, rocket up to the sky
#     P3 SKY REIGN      .. + P3_SKY_REIGN_DURATION                     -- t~=14-28, hover/close-ups/charge/
#                                                                          blast -- THE BLACK-SCREEN KILLER
#     P4 DIVE           .. + P4_DIVE_DURATION                          -- t~=28-31 BY THE ACTUAL DURATION
#                                                                          (45 frames/3s, not "~1s" -- see
#                                                                          CAVEAT below), touchdown ~2s
#                                                                          AFTER the flare hits (t~=29)
#     P5 GROUND REIGN   .. + P5_GROUND_REIGN_DURATION                  -- t~=31-42 BY THE ACTUAL DURATION
#                                                                          (165 frames/11s); fire column
#                                                                          engulfs him + both damage beats
#                                                                          + undercarriage shots (unchanged
#                                                                          from the original build's own
#                                                                          ground-hover piece)
#     P6 EXIT           .. + P6_EXIT_DURATION = THOMAS_END             -- t~=42-44.7 BY THE ACTUAL DURATION
#                                                                          (40 frames/2.7s) -- this is AFTER
#                                                                          the calibration video's own
#                                                                          observed "t~=38-40: resolution,
#                                                                          Thomas gone (End reached)," a
#                                                                          ~5-7s gap between the given
#                                                                          offset/rate constants and the
#                                                                          given End-reached observation
#                                                                          (see CAVEAT below -- NOT fixed
#                                                                          here, no footage of THIS build)
#
#   CAVEAT (adversarial verification, 2026-07-22, NOT yet in-game-checked -- the four t~= labels above
#   for P4/P5/P6 were originally hand-estimated and did NOT match frames=(t-6)*15 applied to this
#   build's own chosen Durations (P4=45f/P5=165f/P6=40f) -- corrected above to the values the formula
#   actually produces. Two consequences worth a look once there's footage of THIS specific build:
#     (a) P4's 45-frame (3s) dive means touchdown lands at t~=31, ~2s AFTER the flare hits the arena at
#         t~=29 per the video map -- for that first ~2s of the intended "backlit by the blast, engulfed
#         in the fire column" SPECTACULAR ground beat, Thomas would still read as mid-air/diving rather
#         than grounded. If confirmed, the fix is a P4-duration retune (not attempted blind here).
#     (b) P6 Exit (frames 540-580, t~=42-44.7) starts and ends entirely AFTER this same video's own
#         literal "t~=38-40: resolution, Thomas gone (End reached)" observation -- SFXDataMesh.cs:799
#         (`frame >= tok.endFrame` -> `SetActive(false)`) confirms "End reached" there literally means
#         frame=580 was hit, so that observation IS a real video-time data point for frame 580, and it
#         does not match 6 + 580/15 = 44.67s predicted by the given offset/rate constants -- a ~5-7s
#         internal inconsistency in the given numbers, not something this script's math got wrong. If
#         the real per-frame rate is faster than 15fps (needed to make End land at t~=38-40), P6 Exit
#         may play out well after the real cinematic and battle result have already resolved -- i.e. an
#         odd late coda -- rather than during it. Needs a fresh capture of THIS build before retuning
#         (this project's own video-for-visual-bugs law); not fixed here.
#
#   Every number below is a named constant -- retune and rerun (recast-only, no relaunch) in one line.
VIDEO_TO_FRAME_OFFSET_S = 6      # Thomas's own PlaySFX/frame-0, video-seconds (measured off the cast)
FRAMES_PER_VIDEO_SECOND = 15     # Thomas's own clock rate (measured off the cast)

# CAVE STAGE -- the settled hover point for P1's arrival AND P4's landing (unchanged numbers from the
# original build's STAGE_*): comfortably past Thomas's own ~1340-unit half-length (10.116/2 *
# THOMAS_SCALE) onto the enemy side so his own bulk doesn't sprawl back over the caster, elevated
# roughly half his own ~1302-unit height -- a dragon looms, it doesn't stand.
#
# CAVEAT (found in adversarial review, 2026-07-22, NOT yet in-game-checked -- flag for the next video
# capture): this Z-clearance reasoning is computed against Thomas's LENGTH axis (~2681 units), which
# only runs along world Z while his yaw is near 0 (facing the enemies, true only during P1's own
# approach and P6's own climb-away). Everywhere else -- P2 through P5 -- his yaw is held at
# YAW_BROADSIDE=90, where a rotation about the vertical (Y) axis swaps which world axis his bounding
# box projects onto: his ~2681-unit LENGTH sweeps world X (not Z), and only his ~926-unit WIDTH remains
# on Z. Neither P3's own X range (SKY_DRIFT_X=250) nor P5's (GROUND_DRIFT_X - CAVE_STAGE_X=220) was
# ever sized against a 2681-unit sweep -- if a playtest reports Thomas reading as absurdly wide /
# clipped at the screen edges / only a sliver visible during either REIGN (as opposed to the
# swoop/dive transitions), this axis swap -- not a miscalibrated magnitude -- is the first thing to
# check from footage. Candidate fixes if confirmed: shrink THOMAS_SCALE for the reign holds
# specifically (not straightforward -- Scaling is one constant piece, not per-phase), pick a
# YAW_BROADSIDE nearer 0/180 so the long axis stays on Z, or accept a wider camera crop as the "epic"
# read. Not fixed here -- no footage of THIS build yet, and retuning without it would be a guess (this
# project's own video-for-visual-bugs law).
CAVE_STAGE_X = 0            # CasterPositionX + 0   -- centered on the caster's own lane
CAVE_STAGE_Y = 700          # CasterPositionY + 700 -- looming height
CAVE_STAGE_Z = 1800         # CasterPositionZ + 1800 -- well onto the enemy side

# P1 ENTRANCE origin -- swoop in from high off-side, descending + advancing into CAVE_STAGE (unchanged
# numbers from the original build's ENTRANCE_*; only the phase's OWN duration got faster, 75 not 420).
ENTRANCE_X = -2000     # off to one side (mission's own example number)
ENTRANCE_Y = 1500      # higher than CAVE_STAGE_Y -- descends INTO the loom height as he arrives
ENTRANCE_Z = 300       # barely onto the enemy side yet -- advances to CAVE_STAGE_Z over the swoop

# P2 ASCENT destination -- SKY STAGE: straight up off CAVE_STAGE's own X/Z lane (per the mission spec:
# "SKY_Y = CasterPositionY + 4500, Z stays ~+1800, X ~0").
SKY_Y_OFFSET = 4500              # CasterPositionY + 4500 -- "SKY_Y" per the mission's redesign spec
SKY_STAGE_X = CAVE_STAGE_X       # ~0, unchanged lane
SKY_STAGE_Z = CAVE_STAGE_Z       # ~1800, unchanged lane -- "Z stays ~+1800" per spec

# P3 SKY REIGN destination -- a gentle broadside sway/rise off SKY STAGE (mirrors the original ground
# REIGN's own "alive, not frozen" drift mechanic, relocated to the sky + rescaled per the mission's own
# amplitude: "drift amplitude ~250 X / ~100 Y"). Held via Sinus easing (floaty, no harsh start/stop),
# so the piece-chain (Origin inherited from the PRIOR piece's own Destination, verified against
# ParametricMovement.cs:88-105) lands P4's own Origin exactly where P3 visually stopped.
SKY_DRIFT_X = 250        # a modest lateral sway among the clouds
SKY_DRIFT_Y = 100        # a modest additional rise -- "breathing" through the hover pose/charge/blast

# P5 GROUND REIGN destination -- the proven floaty ground hover (unchanged numbers from the original
# build's own DRIFT_*): the fire column engulfs him here, both damage beats fire here.
GROUND_DRIFT_X = CAVE_STAGE_X + 220     # a modest lateral sway
GROUND_DRIFT_Y = CAVE_STAGE_Y + 80      # a modest additional rise -- "breathing" while he hovers
GROUND_DRIFT_Z = CAVE_STAGE_Z           # Z held (no drift on the caster<->enemy axis during the reign)

# P6 EXIT destination -- climb away up-forward, past the sequence's own close (unchanged numbers from
# the original build's own EXIT_*).
EXIT_X = GROUND_DRIFT_X + 380
EXIT_Y = 1600
EXIT_Z = 2600

# Yaw (Rotation.Y): P1 banks 0 (his normalized-forward, facing the enemies) -> 90 (broadside) as he
# arrives at CAVE_STAGE, then HOLDS broadside from P2's entry all the way through the end of P5 (the
# mission's own instruction -- also his iconic "number 1" side panel, per README's axis-verification
# renders), then 90 -> 0 only in P6 as he turns forward again to climb away. Rotation.Z stays 0 in
# every piece -- NO roll (he is not PSX-inverted; README's own axis-verification already established
# his normalized Rotation=(0,0) needs no runtime compensation).
YAW_BROADSIDE = 90

# Tick-map phase lengths (frames, on Thomas's own PlaySFX-zeroed clock) -- boundaries match the
# mission's video-derived timing map exactly (0-75 / 75-120 / 120-330 / 330-375 / 375-540 / 540-580);
# sum = THOMAS_END = the FBX entry's own End, unchanged at 580 from the original 3-phase build. The
# t~= labels below are frames=(t-6)*15 solved FORWARD from each Duration (adversarial-verification
# correction, 2026-07-22 -- P4/P5/P6 were previously mislabeled ~2-5s early; see the CAVEAT above the
# FLIGHT constants for what this means for the flare-hit/End-reached alignment, not fixed blind here).
P1_ENTRANCE_DURATION = 75          # t~=6-11: the proven cave shots (was 420 -- now faster, same path)
P2_ASCENT_DURATION = 45            # t~=11-14: rocket up to the sky stage
P3_SKY_REIGN_DURATION = 210        # t~=14-28: hover pose/close-ups/charge/blast -- the black-screen killer
P4_DIVE_DURATION = 45              # t~=28-31 (3s): plunge back down -- touchdown ~2s AFTER the flare
                                    #   hits (t~=29 per the video map); see CAVEAT above
P5_GROUND_REIGN_DURATION = 165     # t~=31-42 (11s): fire column + both damage beats + undercarriage shots
P6_EXIT_DURATION = 40              # t~=42-44.7: climb away -- AFTER the calibration video's own observed
                                    #   "End reached" at t~=38-40; see CAVEAT above
THOMAS_END = (P1_ENTRANCE_DURATION + P2_ASCENT_DURATION + P3_SKY_REIGN_DURATION
              + P4_DIVE_DURATION + P5_GROUND_REIGN_DURATION + P6_EXIT_DURATION)   # 580, unchanged

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


def _rel(base: str, offset) -> str:
    """An NCalc anchor expression: ``base`` plus/minus an integer caster-relative offset. offset==0
    collapses to the bare base expression (both parse identically via NCalc -- purely for a
    cleaner-reading generated manifest, exactly the ``_hide_meshes_arg``-style "generated, not
    hand-typed" convention already used above for the .seq splice)."""
    offset = int(offset)
    if offset == 0:
        return base
    return f"{base} + {offset}" if offset > 0 else f"{base} - {-offset}"


def build_manifest_json() -> dict:
    """Generate ``thomas_manifest.sfxmodel``'s JSON from the named FLIGHT constants above (schema
    verified against ``ParametricMovement.LoadFromJSON``, Memoria/Battle/SFX/ParametricMovement.cs:
    58-136 -- an array of pieces, ``Duration`` + per-axis ``Origin*``/``Destination*``/
    ``InterpolationType*``; an absent ``Origin*`` key on piece i>0 CHAINS from the prior piece's own
    ``Destination*`` expression, :88-105/:104-105/:96-97 -- used below for pieces 2-6 of both Movement
    and Rotation). The 2026-07-22 redesign is 6 pieces (Entrance/Ascent/Sky Reign/Dive/Ground Reign/
    Exit): SinusOut (decelerating arrival, P1) -> SinusIn (accelerating launch, P2) -> Sinus (floaty
    sky hover, P3) -> SinusIn (the dive, P4, mirrors Bahamut's own dive per the mission spec) -> Sinus
    (floaty ground hover, P5) -> SinusIn (accelerating departure, P6); every Destination is always
    given explicitly (never relied on the dest-defaults-to-origin fallback) so the JSON stays
    self-documenting. Scaling is unchanged from the original build (constant THOMAS_SCALE, one piece,
    no motion needed)."""
    movement = [
        {   # P1 ENTRANCE: swoop in high off-side -> descend+advance into CAVE_STAGE (faster than the
            # original build, same path)
            "Duration": str(P1_ENTRANCE_DURATION),
            "OriginX": _rel("CasterPositionX", ENTRANCE_X),
            "OriginY": _rel("CasterPositionY", ENTRANCE_Y),
            "OriginZ": _rel("CasterPositionZ", ENTRANCE_Z),
            "DestinationX": _rel("CasterPositionX", CAVE_STAGE_X),
            "DestinationY": _rel("CasterPositionY", CAVE_STAGE_Y),
            "DestinationZ": _rel("CasterPositionZ", CAVE_STAGE_Z),
            "InterpolationTypeX": "SinusOut", "InterpolationTypeY": "SinusOut", "InterpolationTypeZ": "SinusOut",
        },
        {   # P2 ASCENT: rocket up off CAVE_STAGE's own X/Z lane to SKY STAGE (Origin chained from P1's
            # Destination)
            "Duration": str(P2_ASCENT_DURATION),
            "DestinationX": _rel("CasterPositionX", SKY_STAGE_X),
            "DestinationY": _rel("CasterPositionY", SKY_Y_OFFSET),
            "DestinationZ": _rel("CasterPositionZ", SKY_STAGE_Z),
            "InterpolationTypeX": "SinusIn", "InterpolationTypeY": "SinusIn", "InterpolationTypeZ": "SinusIn",
        },
        {   # P3 SKY REIGN: gentle broadside sway/rise among the clouds (Origin chained from P2's
            # Destination) -- the Mega-Flare + both EffectPoints play out under this piece
            "Duration": str(P3_SKY_REIGN_DURATION),
            "DestinationX": _rel("CasterPositionX", SKY_STAGE_X + SKY_DRIFT_X),
            "DestinationY": _rel("CasterPositionY", SKY_Y_OFFSET + SKY_DRIFT_Y),
            "DestinationZ": _rel("CasterPositionZ", SKY_STAGE_Z),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P4 DIVE: plunge back down to CAVE_STAGE (Origin chained from P3's Destination) -- mirrors
            # Bahamut's own dive per the mission spec, lands before the flare hits the ground
            "Duration": str(P4_DIVE_DURATION),
            "DestinationX": _rel("CasterPositionX", CAVE_STAGE_X),
            "DestinationY": _rel("CasterPositionY", CAVE_STAGE_Y),
            "DestinationZ": _rel("CasterPositionZ", CAVE_STAGE_Z),
            "InterpolationTypeX": "SinusIn", "InterpolationTypeY": "SinusIn", "InterpolationTypeZ": "SinusIn",
        },
        {   # P5 GROUND REIGN: the proven floaty ground hover (Origin chained from P4's Destination) --
            # unchanged from the original build's own ground-reign piece
            "Duration": str(P5_GROUND_REIGN_DURATION),
            "DestinationX": _rel("CasterPositionX", GROUND_DRIFT_X),
            "DestinationY": _rel("CasterPositionY", GROUND_DRIFT_Y),
            "DestinationZ": _rel("CasterPositionZ", GROUND_DRIFT_Z),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P6 EXIT: climb away up-forward (Origin chained from P5's Destination) -- unchanged path
            "Duration": str(P6_EXIT_DURATION),
            "DestinationX": _rel("CasterPositionX", EXIT_X),
            "DestinationY": _rel("CasterPositionY", EXIT_Y),
            "DestinationZ": _rel("CasterPositionZ", EXIT_Z),
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
        {   # P2: hold broadside through the ascent (Origin chained from P1's Destination = YAW_BROADSIDE)
            "Duration": str(P2_ASCENT_DURATION),
            "DestinationY": str(YAW_BROADSIDE),
            "DestinationZ": "0",
        },
        {   # P3: hold broadside through the sky reign (the mega-flare window)
            "Duration": str(P3_SKY_REIGN_DURATION),
            "DestinationY": str(YAW_BROADSIDE),
            "DestinationZ": "0",
        },
        {   # P4: hold broadside through the dive
            "Duration": str(P4_DIVE_DURATION),
            "DestinationY": str(YAW_BROADSIDE),
            "DestinationZ": "0",
        },
        {   # P5: hold broadside through the ground reign (fire column + damage beats)
            "Duration": str(P5_GROUND_REIGN_DURATION),
            "DestinationY": str(YAW_BROADSIDE),
            "DestinationZ": "0",
        },
        {   # P6: turn back to forward-facing as he climbs away
            "Duration": str(P6_EXIT_DURATION),
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


def splice_sequence(donor_text: str, hide_range: "tuple[int, int] | None") -> str:
    """Insert the Thomas delta block immediately before ANCHOR_LINE, and replace ANCHOR_LINE itself
    with ``patched_line(hide_range)`` (the HideMeshes-augmented form, or -- ``hide_range=None`` -- the
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
    new_lines = lines[:idx] + delta_lines + [patched_line(hide_range)] + lines[idx + 1:]
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


def build_thomas(mod_root: Path, game_path: Path, hide_range: "tuple[int, int] | None" = HIDE_RANGE) -> dict:
    donor_bytes, donor_text = _read_verified(
        game_path / DONOR_REL_DIR / PLAYER_SEQ_NAME, EXPECTED_DONOR_SHA256, "stock ef227/PlayerSequence.seq"
    )
    out_text = splice_sequence(donor_text, hide_range)
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
        "mint": mint_info, "hide_range": hide_range,
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
    hg_group.add_argument("--hide-range", metavar="A,B", default=None,
                           help=f"override HIDE_RANGE (default {HIDE_RANGE[0]},{HIDE_RANGE[1]}) for this "
                                "deploy -- two comma-separated inclusive integers, e.g. --hide-range 32,63 "
                                "for round 2's other half. Only meaningful with a Thomas-swap deploy (not "
                                "--restore). See README.md's HideMeshes bisection protocol.")
    hg_group.add_argument("--calibrate", action="store_true",
                           help="deploy with NO HideMeshes argument at all -- the patched line is then "
                                "byte-identical to the stock donor's own PlaySFX line, so Bahamut's real "
                                "mesh renders completely unsuppressed. For recording a clean composition-"
                                "reference video. Mutually exclusive with --hide-range.")
    args = parser.parse_args()
    mode = "restore" if args.restore else "thomas"

    if mode == "restore" and (args.hide_range or args.calibrate):
        parser.error("--hide-range/--calibrate only apply to a Thomas-swap deploy, not --restore")

    if args.calibrate:
        hide_range = None
    elif args.hide_range:
        parts = args.hide_range.split(",")
        if len(parts) != 2:
            parser.error(f"--hide-range must be 'A,B' (two comma-separated integers), got {args.hide_range!r}")
        try:
            hide_range = (int(parts[0]), int(parts[1]))
        except ValueError:
            parser.error(f"--hide-range must be 'A,B' (two comma-separated integers), got {args.hide_range!r}")
        if hide_range[0] > hide_range[1]:
            parser.error(f"--hide-range lo must be <= hi, got {hide_range}")
    else:
        hide_range = HIDE_RANGE

    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print(f"private id   : ef{FRESH_EF_ID:03d} (rung 3/7's fresh-id folder -- reused, not re-minted)")
    print(f"mode         : {'THOMAS SWAP' if mode == 'thomas' else 'RESTORE (rung-7 resting state)'}")
    if mode == "thomas":
        if hide_range is None:
            print("hide range   : CALIBRATE -- no HideMeshes argument at all (Bahamut renders unsuppressed)")
        else:
            print(f"hide range   : {hide_range[0]}..{hide_range[1]} inclusive "
                  f"({hide_range[1] - hide_range[0] + 1} indices)")
    print()

    try:
        if mode == "thomas":
            result = build_thomas(mod_root, game_path, hide_range)
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
        b2 = b1 + P2_ASCENT_DURATION
        b3 = b2 + P3_SKY_REIGN_DURATION
        b4 = b3 + P4_DIVE_DURATION
        b5 = b4 + P5_GROUND_REIGN_DURATION
        b6 = b5 + P6_EXIT_DURATION  # == THOMAS_END
        print("THE FLIGHT (6 phases, 2026-07-22 redesign):")
        print(f"  P1 entrance   0-{b1}   swoop in, high off-side -> cave stage")
        print(f"  P2 ascent   {b1}-{b2}   rocket up to the sky stage")
        print(f"  P3 sky reign  {b2}-{b3}  broadside hover among the clouds -- the black-screen killer")
        print(f"  P4 dive     {b3}-{b4}  plunge back down to the cave stage")
        print(f"  P5 ground reign {b4}-{b5}  fire column + both damage beats + undercarriage shots")
        print(f"  P6 exit     {b5}-{b6}  climb away up-forward")
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
