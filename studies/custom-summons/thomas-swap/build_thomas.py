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
     immediately before the donor's own ``PlaySFX: SFX=Bahamut__Full`` line, and appends
     ``HideMeshes=0,1,...,63`` to that same line (generated here, not hand-typed, to avoid a miscount).
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

    py studies/custom-summons/thomas-swap/build_thomas.py             # deploy the Thomas swap
    py studies/custom-summons/thomas-swap/build_thomas.py --restore   # back to rung 7's resting state
                                                                        # + Thomas's mint fully removed

See README.md for the full test procedure, the failure-mode table, and the local-only provenance note.
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
ANCHOR_LINE = "PlaySFX: SFX=Bahamut__Full ; Reflect=True\r\n"
HIDE_MESHES = ",".join(str(i) for i in range(64))              # "0,1,2,...,63" -- generated, not hand-typed
PATCHED_LINE = f"PlaySFX: SFX=Bahamut__Full ; Reflect=True ; HideMeshes={HIDE_MESHES}\r\n"

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
#   THE 3 PHASES map onto rung-4's tick map (PLAN.md; Thomas's own clock zeroes at HIS OWN PlaySFX,
#   which fires within a tick or two of the donor's nested Sequence.seq's own frame-0 -- see README.md
#   "Timing" for the background-thread offset-uncertainty discussion; each phase below is given a
#   comfortable overlap margin against that uncertainty, not a razor's-edge cut):
#     P1 ENTRANCE  t=0   .. P1_ENTRANCE_DURATION            -- covers blackout ramp (t=0), flash1
#                                                               (t=116), flash2 (t=289); arrives just
#                                                               before the dim silhouette reveal (t=403)
#     P2 THE REIGN  ..   .. + P2_REIGN_DURATION              -- covers the dim reveal (t=403) through
#                                                               the ENTIRE Mega-Flare window (t=434-516)
#                                                               incl. BOTH EffectPoints (t=486, t=498)
#     P3 EXIT       ..   .. + P3_EXIT_DURATION = THOMAS_END  -- covers lights-restored (t=516) through
#                                                               the close (t~547) + the same ~33-tick
#                                                               tail margin the prior static build used
#
#   Every number below is a named constant -- retune and rerun (recast-only, no relaunch) in one line.

# CENTER-STAGE -- the settled hover point for P2 ("the reign"): comfortably past Thomas's own
# ~1340-unit half-length (10.116/2 * THOMAS_SCALE) onto the enemy side so his own bulk doesn't sprawl
# back over the caster, and elevated roughly half his own ~1302-unit height (mission's suggested
# 500-900 Y-band; 1200-2200 Z-band) -- a dragon looms, it doesn't stand.
#
# CAVEAT (found in adversarial review, 2026-07-22, NOT yet in-game-checked -- flag for the next video
# capture): this Z-clearance reasoning is computed against Thomas's LENGTH axis (~2681 units), which
# only runs along world Z while his yaw is near 0 (facing the enemies, true for roughly the first half
# of P1's approach). By the time he actually ARRIVES at CENTER-STAGE (end of P1, frame
# P1_ENTRANCE_DURATION) his yaw has already eased to YAW_BROADSIDE=90 -- the pose he then HOLDS for the
# entire P2 "reign" (the mega-flare window, the shot the player is actually watching). At yaw=90, a
# rotation about the vertical (Y) axis swaps which world axis his bounding box projects onto: his
# ~2681-unit LENGTH now sweeps world X (not Z), and only his ~926-unit WIDTH remains on Z. P2's own X
# range (STAGE_X=0 -> DRIFT_X=220) was never sized against a 2681-unit sweep -- if the next playtest
# reports Thomas reading as absurdly wide / clipped at the screen edges / only a sliver visible during
# the HOVER (as opposed to the swoop-in), this axis swap -- not a miscalibrated magnitude -- is the
# first thing to check from footage. Candidate fixes if confirmed: shrink THOMAS_SCALE for the P2 hold
# specifically (not straightforward -- Scaling is one constant piece, not per-phase), pick a
# YAW_BROADSIDE nearer 0/180 so the long axis stays on Z, or accept a wider camera crop as the "epic"
# read. Not fixed here -- no footage yet, and retuning without it would be a guess (this project's own
# video-for-visual-bugs law).
STAGE_X = 0            # CasterPositionX + 0   -- centered on the caster's own lane
STAGE_Y = 700          # CasterPositionY + 700 -- looming height
STAGE_Z = 1800         # CasterPositionZ + 1800 -- well onto the enemy side

# P1 ENTRANCE origin -- swoop in from high off-side, descending + advancing into CENTER-STAGE.
ENTRANCE_X = -2000     # off to one side (mission's own example number)
ENTRANCE_Y = 1500      # higher than STAGE_Y -- descends INTO the loom height as he arrives
ENTRANCE_Z = 300       # barely onto the enemy side yet -- advances to STAGE_Z over the swoop

# P2 THE REIGN destination -- a gentle sway/rise off CENTER-STAGE, NOT a static hold ("alive, not
# frozen"); held via Sinus easing (floaty, no harsh start/stop) rather than a Turning oscillator, so
# the piece-chain (Origin inherited from the PRIOR piece's own Destination, verified against
# ParametricMovement.cs:88-105) lands P3's own Origin exactly where P2 visually stopped.
DRIFT_X = STAGE_X + 220     # a modest lateral sway
DRIFT_Y = STAGE_Y + 80      # a modest additional rise -- "breathing" while he hovers
DRIFT_Z = STAGE_Z           # Z held (no drift on the caster<->enemy axis during the reign)

# P3 EXIT destination -- climb away up-forward, past the sequence's own close.
EXIT_X = DRIFT_X + 380
EXIT_Y = 1600
EXIT_Z = 2600

# Yaw (Rotation.Y): P1 banks 0 (his normalized-forward, facing the enemies) -> 90 (broadside) as he
# arrives, holds broadside through P2 (the mission's "safe comedic read" -- also his iconic "number 1"
# side panel, per README's axis-verification renders), then 90 -> 0 in P3 as he turns forward again to
# climb away. Rotation.Z stays 0 in every piece -- NO roll (he is not PSX-inverted; README's own
# axis-verification already established his normalized Rotation=(0,0) needs no runtime compensation).
YAW_BROADSIDE = 90

# Tick-map phase lengths (frames, on Thomas's own PlaySFX-zeroed clock) -- sum = THOMAS_END = the FBX
# entry's own End (matches the prior static build's End=580, generous ~33-tick tail past the donor's
# own last beat at t~547; see PLAN.md's rung-4 tick-map annotation for every cited beat above).
P1_ENTRANCE_DURATION = 420
P2_REIGN_DURATION = 100
P3_EXIT_DURATION = 60
THOMAS_END = P1_ENTRANCE_DURATION + P2_REIGN_DURATION + P3_EXIT_DURATION   # 580, unchanged

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
    cleaner-reading generated manifest, exactly the ``HIDE_MESHES``-style "generated, not hand-typed"
    convention already used above for the .seq splice)."""
    offset = int(offset)
    if offset == 0:
        return base
    return f"{base} + {offset}" if offset > 0 else f"{base} - {-offset}"


def build_manifest_json() -> dict:
    """Generate ``thomas_manifest.sfxmodel``'s JSON from the named FLIGHT constants above (schema
    verified against ``ParametricMovement.LoadFromJSON``, Memoria/Battle/SFX/ParametricMovement.cs:
    58-136 -- an array of pieces, ``Duration`` + per-axis ``Origin*``/``Destination*``/
    ``InterpolationType*``; an absent ``Origin*`` key on piece i>0 CHAINS from the prior piece's own
    ``Destination*`` expression, :88-105/:104-105/:96-97 -- used below for pieces 2/3 of both Movement
    and Rotation). Movement uses SinusOut (decelerating arrival) -> Sinus (floaty hover, both ends
    eased) -> SinusIn (accelerating departure); every Destination is always given explicitly (never
    relied on the dest-defaults-to-origin fallback) so the JSON stays self-documenting. Scaling is
    unchanged from the prior static build (constant THOMAS_SCALE, one piece, no motion needed)."""
    movement = [
        {   # P1 ENTRANCE: swoop in high off-side -> descend+advance into CENTER-STAGE
            "Duration": str(P1_ENTRANCE_DURATION),
            "OriginX": _rel("CasterPositionX", ENTRANCE_X),
            "OriginY": _rel("CasterPositionY", ENTRANCE_Y),
            "OriginZ": _rel("CasterPositionZ", ENTRANCE_Z),
            "DestinationX": _rel("CasterPositionX", STAGE_X),
            "DestinationY": _rel("CasterPositionY", STAGE_Y),
            "DestinationZ": _rel("CasterPositionZ", STAGE_Z),
            "InterpolationTypeX": "SinusOut", "InterpolationTypeY": "SinusOut", "InterpolationTypeZ": "SinusOut",
        },
        {   # P2 THE REIGN: gentle sway/rise off CENTER-STAGE (Origin chained from P1's Destination)
            "Duration": str(P2_REIGN_DURATION),
            "DestinationX": _rel("CasterPositionX", DRIFT_X),
            "DestinationY": _rel("CasterPositionY", DRIFT_Y),
            "DestinationZ": _rel("CasterPositionZ", DRIFT_Z),
            "InterpolationTypeX": "Sinus", "InterpolationTypeY": "Sinus", "InterpolationTypeZ": "Sinus",
        },
        {   # P3 EXIT: climb away up-forward (Origin chained from P2's Destination)
            "Duration": str(P3_EXIT_DURATION),
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
        {   # P2: hold broadside (Origin chained from P1's Destination = YAW_BROADSIDE already)
            "Duration": str(P2_REIGN_DURATION),
            "DestinationY": str(YAW_BROADSIDE),
            "DestinationZ": "0",
        },
        {   # P3: turn back to forward-facing as he climbs away
            "Duration": str(P3_EXIT_DURATION),
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


def splice_sequence(donor_text: str) -> str:
    """Insert the Thomas delta block immediately before ANCHOR_LINE, and replace ANCHOR_LINE itself
    with PATCHED_LINE (the HideMeshes-augmented form). Raises DriftError if ANCHOR_LINE isn't found
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
    new_lines = lines[:idx] + delta_lines + [PATCHED_LINE] + lines[idx + 1:]
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


def build_thomas(mod_root: Path, game_path: Path) -> dict:
    donor_bytes, donor_text = _read_verified(
        game_path / DONOR_REL_DIR / PLAYER_SEQ_NAME, EXPECTED_DONOR_SHA256, "stock ef227/PlayerSequence.seq"
    )
    out_text = splice_sequence(donor_text)
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
        "mint": mint_info,
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
    args = parser.parse_args()
    mode = "restore" if args.restore else "thomas"

    game_path = config.find_game_path()
    mod_root = config.find_mod_root(game_path)

    print(f"game install : {game_path}")
    print(f"mod folder   : {mod_root}")
    print(f"private id   : ef{FRESH_EF_ID:03d} (rung 3/7's fresh-id folder -- reused, not re-minted)")
    print(f"mode         : {'THOMAS SWAP' if mode == 'thomas' else 'RESTORE (rung-7 resting state)'}")
    print()

    try:
        if mode == "thomas":
            result = build_thomas(mod_root, game_path)
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
        print(f"THE FLIGHT: P1 entrance 0-{P1_ENTRANCE_DURATION} (swoop in, high off-side -> center-stage), "
              f"P2 reign {P1_ENTRANCE_DURATION}-{P1_ENTRANCE_DURATION + P2_REIGN_DURATION} (broadside hover, "
              f"gentle sway -- covers the Mega-Flare + both EffectPoints), "
              f"P3 exit {P1_ENTRANCE_DURATION + P2_REIGN_DURATION}-{THOMAS_END} (climb away up-forward).")
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
