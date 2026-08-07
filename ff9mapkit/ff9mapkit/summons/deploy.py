"""``summons/deploy.py`` -- the DEPLOY engine for the ``[[summon]]`` transplant lane (M2 of
``studies/custom-summons/thomas-swap/disasm/TRANSPLANT.md`` section 2.4; binding design =
``studies/custom-summons/thomas-swap/m2/DESIGN.md``).

This productizes the hand-built, in-game-proven Thomas transplant (M1b, "it works, thomas flies with
the dragon's motion") -- the prototype is ``studies/custom-summons/thomas-swap/build_thomas.py`` +
``m1b/{skin_thomas.py,stage_mint.py}``. Two runtime lanes:

  * **hybrid** (DEFAULT) -- the s58 ``SfxHybridDrive`` engine feature poses the user's skinned model onto
    the native donor cast's live per-frame skeleton. Emits the mint (rows 1/1b) + the private-ef host
    ``.seq`` (row 2) and ARMS ``Memoria.ini [SfxHybrid]`` (row 3). REQUIRES the custom engine -- the arm
    step string-probes the deployed ``Assembly-CSharp.dll`` for ``SfxHybridDrive`` and REFUSES on stock.
  * **overlay** (DLL-free rung-7 route) -- the mint + the host ``.seq`` (with the StartThread self-load
    delta) + ``FileList.txt`` + a ``.sfxmodel`` manifest + the decoded donor ``.anim`` clips. Works on a
    STOCK engine; never touches ``Memoria.ini``.

THE DONOR-FILELIST REPLACEMENT LAW (``m0/FBX-PATHS.md`` section 3): a ``FileList.txt`` ``Model`` line in a
donor's OWN ``ef{donor:D3}/`` folder silently replaces the whole native cast (``if (mesh != null) return``
at ``SFXData.cs:349`` fires before the native ``Runtime`` enqueues) -- fatal to the hybrid, which needs
the native engine actually running so ``*(SummonData+0x38)`` has real bones. So the cast trigger always
routes through a **private, stock-ABSENT** effect id (``private_ef``) that hosts the ``.seq`` (and, overlay
lane, the JSON mesh); the donor's own folder is only ever READ.

PROVENANCE (DESIGN section 6, STRICT):
  * This module is committable CODE -- parsers/adapters/writers; it reads caller-supplied local blobs
    (the user's retargeted FBX, extracted stock ``.seq``/``ef###.bytes``) and embeds ZERO game bytes.
  * The user's retargeted model + the deployed ``.anim``/``.seq``/ini in the user's OWN mod folder =
    THEIRS (verbatim-fork precedent) -- we may write there.
  * The donor ``.seq`` copy is Square-Enix-derived: fetched fresh from the install at deploy,
    drift-guarded (:data:`EXPECTED_DONOR_SEQ_SHA`), NEVER committed; a staged/dry-run copy lives under
    ``C:/gd/SCRATCH/summon-transplant/``.

RELAUNCH vs RECAST (DESIGN section 2.3): a NEW ``3DModel`` mint id and the ``[SfxHybrid]`` section register
only at process start -> RELAUNCH. The host ``.seq`` + the loose model/clip files are zero-cache,
per-cast reparsed, mod-folder-shadowed -> RECAST.

SCOPE NOTE -- ``donor`` is NUMERIC here. ``[SfxHybrid] EffectId`` and the ``ef{id:D3}/`` folder both take
the numeric id, and the SFX NAME needed for the host ``.seq``'s ``PlaySFX`` anchor is DERIVED from the
donor's own ``.seq`` (its ``PlaySFX: SFX=<name> ; Reflect=True`` line), so no ``SpecialEffect`` enum table
is read here. A ``SpecialEffect``-name -> id resolution (DESIGN section 1.1) belongs to the block-schema
layer (``content/summon.py``), not this deploy engine. The native read/fork family is OUT (DESIGN 0).
"""
from __future__ import annotations

import difflib
import hashlib
import json
import math
import os
import re
import shutil
import time
from pathlib import Path

from .. import config, fsutil
from ..models import anim as _anim
from ..models import export as _mexport
from ..models import mint as _mint

# --------------------------------------------------------------------------- constants

#: the two runtime lanes (DESIGN section 1 / 2).
LANES = ("hybrid", "overlay")

DEFAULT_DONOR = 227                       # Bahamut__Full (the bench donor)
DEFAULT_PRIVATE_EF = 84                   # Unused_84 (the bench private host; rung 3/7's fresh id)
DEFAULT_GROUP = "MON"                     # MON -> ModelType.mon (3)
DEFAULT_FORM = "B0"                       # battle form token in the minted GEO name (bench: GEO_MON_B0_M201)
MINT_BAND_START = _mint.MINT_BAND_START   # 6000 -- clear of every real GEO id (real max 5511)

#: The 24 stock-ABSENT effect ids -- the private-ef allocation pool. Census: a folder listing of
#: ``Data/SpecialEffects/ef###`` (ids 0-510) is 487 present / 24 absent, and
#: ``SpecialEffect.cs:496-519`` hand-aliases those same 24 as ``Unused_N`` enum members
#: (``rung3-fresh-id/README.md`` lines 38-40; the bench uses 84 = ``Unused_84``). A private host must be
#: one of these -- an id with a real native creature would trip the donor-FileList replacement law.
ABSENT_EF_IDS = frozenset({
    18, 37, 39, 80, 84, 91, 263, 264, 379, 380, 426, 430, 442, 444,
    448, 449, 450, 451, 452, 453, 454, 455, 456, 488,
})

HOST_SEQ_NAME = "PlayerSequence.seq"      # the ``.seq`` a battle command actually authors against
DEFAULT_MANIFEST_NAME = "creature_manifest.sfxmodel"   # the FileList ``Model`` target (rung-7 proven)

#: ``staging.anchor`` -> the NCalc position-parameter prefix the emitted curve expressions are built on
#: (``ParametricMovement.cs:158-196``). ``world`` = no anchor, bare absolute numbers.
STAGING_ANCHORS = {
    "caster": "CasterPosition",
    "target_average": "TargetAveragePosition",
    "world": None,
}

#: THE MULTI-TARGET NULL. ``SFXData.PlaySFX`` passes ``sfxRequest.trgno == 1 ? trg[0] : null`` into
#: ``SetupPositions`` (``SFXData.cs:149``), so on a multi-target cast ``target`` is null and EVERY
#: ``TargetPosition*`` evaluates to 0 (``ParametricMovement.cs:176-178``) -- a creature staged on it would
#: render at the world origin, off-camera. ``TargetAveragePosition*`` (``BTL_VFX_REQ.trgcpos``) is always
#: valid; note its ``vy`` is hard-set to 0 (``BTL_VFX_REQ.cs:88``), so a ``target_average`` Y offset is an
#: ABSOLUTE ground-plane height, not a height above the targets.
_ANCHOR_TARGET_REFUSAL = (
    'staging anchor "target" is refused for a creature: SFXData.cs:149 passes a NULL target into '
    "SetupPositions whenever the cast has more than one target, and every TargetPosition* then evaluates "
    "to 0 -- the creature would stage at the world origin, off-camera (THE MOVEMENT TRAP by a second "
    'route). Use anchor = "target_average" (BTL_VFX_REQ.trgcpos, always valid; its Y is hard-zero, so a Y '
    'offset is an absolute ground-plane height) or "caster". NOTE the split: a CreateVisualEffect particle '
    "IS spawned per-unit and its own TargetPosition* is valid -- this refusal is about the FBX creature.")

#: the seven ``ParametricMovement.InterpolateType`` names; an unknown string silently becomes
#: ``Constant`` (``TryParseInterpolateType``, ``ParametricMovement.cs:273-285``).
_EASES = ("Constant", "Linear", "Sinus", "SinusIn", "SinusOut", "Turning1", "Turning2")

#: THE TURNING SPLIT -- the eases legal on an **FBX** curve, which is only FIVE of the seven.
#: ``ParametricMovement.GetPosition`` dereferences ``customParam`` WITHOUT a null guard on exactly the
#: ``Turning1``/``Turning2`` arms::
#:
#:     if (currentPiece.interpolate[i] == InterpolateType.Turning1 || ... == InterpolateType.Turning2)
#:     {
#:         Single baseAngle;
#:         customParam.TryGetValue(0, out baseAngle);      // ParametricMovement.cs:233-237
#:
#: and the FBX render path passes ``customParam = null`` on all three curves::
#:
#:     tok.unityObject.transform.position    = tok.movement.GetPosition(frame, null, ...);
#:     tok.unityObject.transform.eulerAngles = tok.rotation.GetPosition(frame, null, ...);
#:     tok.unityObject.transform.localScale  = tok.scaling .GetPosition(frame, null, ...);
#:                                                                 // SFXDataMesh.cs:843-845
#:
#: -> a NullReferenceException on EVERY render frame of the cast. Only the SPRITE path supplies a dict
#: (``p.param``, ``SFXDataMesh.cs:1285``), and even there it is null unless the emission carries a
#: ``ParameterMin``/``ParameterMax`` pair (``SFXDataMesh.cs:1386-1388``) -- which is why the study's own
#: ``MistFloor``/``MistWisps`` particles pair their ``Turning1``/``Turning2`` with ``Parameter0..2`` and
#: are safe. Turning on a creature curve never is.
_FBX_EASES = ("Constant", "Linear", "Sinus", "SinusIn", "SinusOut")

#: the two Sprite-only eases, refused on an FBX curve (see :data:`_FBX_EASES`).
_TURNING_EASES = ("Turning1", "Turning2")

#: the ``[summon.staging]`` table's own keys, and its two sub-table shapes -- a curve piece
#: (``[[summon.staging.move/turn/scale]]``) and a playlist row (``[[summon.staging.play]]``). Same
#: hygiene as :data:`content.summon.KNOWN_KEYS`: a typo'd key here is otherwise stored and silently
#: ignored (nothing in :func:`_validate_staging`/:func:`staging_curves_json` ever reads an unknown key),
#: so it is refused at validate time rather than let through to a cast that quietly does not do what the
#: author wrote.
_STAGING_TABLE_KEYS = frozenset({"anchor", "start", "end", "move", "turn", "scale", "play"})
_CURVE_PIECE_KEYS = frozenset({"duration", "from", "to", "ease"})
_PLAY_ROW_KEYS = frozenset({"clip", "speed", "repeat"})

#: THE OMITTED-CURVE SPLIT. ``staging_curves_json`` only emits a ``Movement``/``Rotation``/``Scaling``
#: key when its piece list is non-empty, and ``LoadFBX`` only calls ``LoadFromJSON`` for a node that
#: exists (``SFXDataMesh.cs:1007-1012``) -- so an omitted curve leaves that ``ParametricMovement`` with
#: ZERO pieces. ``GetPosition`` then takes ``currentPiece = null`` and returns the *seed* ``currentDest``
#: (``ParametricMovement.cs:209-212, 226-227``), and the seed is NOT the same for all three:
#:
#:   * ``movement`` / ``rotation`` -- ``new ParametricMovement()`` seeds ``Vector3.zero``
#:     (``ParametricMovement.cs:31-35``, ``SFXDataMesh.cs:1250-1251``). An omitted ``move`` therefore
#:     pins ``transform.position`` at the WORLD ORIGIN for the whole cast -- THE MOVEMENT TRAP, exactly
#:     the failure ``normalize_spec`` already refuses ``staging = "curves"``-with-no-table for. An
#:     omitted ``turn`` pins ``eulerAngles`` at ``(0,0,0)``, which is NOT the rung-7-proven
#:     ``(0,180,180)`` ROTATION BASELINE -- and the engine WRITES eulerAngles every frame
#:     (``SFXDataMesh.cs:844``), so it overrides whatever the FBX baked. Both are refused here.
#:   * ``scale`` -- ``new ParametricMovement(true)`` (``SFXDataMesh.cs:1252``) takes the ``isScaling``
#:     branch and seeds ``Vector3.one`` (``ParametricMovement.cs:26-30``), so an omitted ``scale`` is a
#:     benign IDENTITY scale ``(1,1,1)``: the creature renders at its authored size. It is therefore
#:     OPTIONAL, and deliberately not refused -- the "omitting scale makes the creature invisible"
#:     reading is wrong, it is the ``asScaling`` seed that saves it.
_REQUIRED_CURVES = {
    "move":
        "[summon.staging] has no [[summon.staging.move]] pieces. An omitted Movement curve is never "
        "loaded (SFXDataMesh.cs:1007-1012 only calls LoadFromJSON for a node that EXISTS), so "
        "ParametricMovement keeps zero pieces and GetPosition returns its Vector3.zero seed "
        "(ParametricMovement.cs:31-35, 226-227) -- the creature is pinned at the WORLD ORIGIN, "
        "off-camera, for the whole cast. That is THE MOVEMENT TRAP. Author at least one "
        "[[summon.staging.move]] piece (a single Duration = end - start piece with from == to is a "
        "legal way to say 'hold still here').",
    "turn":
        "[summon.staging] has no [[summon.staging.turn]] pieces. An omitted Rotation curve is never "
        "loaded (SFXDataMesh.cs:1007-1012), so GetPosition returns its Vector3.zero seed and the engine "
        "writes eulerAngles = (0,0,0) EVERY frame (SFXDataMesh.cs:844, raw, with no battle-actor base) "
        "-- overriding whatever orientation the FBX was exported at. That is not the rung-7-proven "
        "(0,180,180) ROTATION BASELINE, so the creature faces the wrong way with no error anywhere. "
        "Author at least one [[summon.staging.turn]] piece; the proven baseline is a single piece with "
        "from = to = [0, 180, 180].",
}

#: authored ``.anim`` clips get on-disc keys from the kit's mint band, clear of every stock clip key
#: (stock tops out at 14739) so a minted creature's clip file can never shadow a real one.
AUTHORED_CLIP_KEY_BASE = _anim._NEW_ANIM_KEY_BASE

#: donor id -> sha256 of the pristine stock ``ef{donor:D3}/PlayerSequence.seq`` we splice against. A donor
#: whose live ``.seq`` drifts from its registered hash is REFUSED (``build_thomas.py:141``). A donor with
#: no registered hash is allowed but WARNED (no drift guard is possible -- the caller vouches for it).
EXPECTED_DONOR_SEQ_SHA = {
    227: "4bc643bfb3ec478dcc1f5b51261f59637faac9d775cccd38c0055afee14ece63",  # Bahamut__Full
}

SFXHYBRID_SECTION = "SfxHybrid"
#: the UTF-8 type name that MUST be present in a deployed ``Assembly-CSharp.dll`` for the hybrid lane to
#: arm (the s58 feature class; ``m1b/RUNBOOK.md`` section 0 presence check).
_SFXHYBRID_ENGINE_MARK = b"SfxHybridDrive"

#: the host ``.seq`` line the transplant edits -- the native creature's spawn. Matched by pattern so no
#: ``SpecialEffect`` table is needed (the name is read straight off the donor's own line).
_ANCHOR_RE = re.compile(r"^PlaySFX: SFX=(?P<sfx>\S+) ; Reflect=True$")

# where the install keeps a summon effect's loose data files.
_SFX_REL = ("StreamingAssets", "Data", "SpecialEffects")


class SummonDeployError(RuntimeError):
    """A bad spec, a missing input, a refused engine/provenance gate, or a validation failure."""


class DonorDriftError(SummonDeployError):
    """A donor file this module READS (never owns) doesn't match the bytes it was derived against."""


# --------------------------------------------------------------------------- spec normalize / validate

def _as_int(v, who: str) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        raise SummonDeployError(f"{who} must be an integer, got {v!r}")


def _same_path(a: str, b: str) -> bool:
    """Lexical path equality, robust to `./b.seq` vs `b.seq` / backslash-vs-forward-slash / Windows case
    (review FOLD-B: raw string equality let a trivially-different spelling evade the short==sequence
    refusal). `normalize_spec` has no `base_dir` -- both sides are relative to whatever the TOML author
    wrote them relative to (the SAME field, in practice), so plain `normpath` is the right amount of
    normalization here; a true on-disk resolve happens later in `content.summon._path_problems`."""
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def derive_summon_name(new_id: int, group: str = DEFAULT_GROUP, form: str = DEFAULT_FORM) -> str:
    """The default minted GEO name for a summon model: ``GEO_<GROUP>_<FORM>_M<offset:03d>`` -- the same
    band-offset token scheme :func:`ff9mapkit.models.mint.derive_mint_name` uses, so id 6201 group MON
    reproduces the bench's ``GEO_MON_B0_M201`` exactly."""
    return f"GEO_{group.upper()}_{form.upper()}_M{new_id - MINT_BAND_START:03d}"


def normalize_spec(block: dict) -> dict:
    """A ``[[summon]]`` block dict -> a validated, defaults-filled spec (NO I/O). Raises
    :class:`SummonDeployError` on the first structural problem (DESIGN section 1). ``id`` / ``private_ef``
    may be left as ``None`` to defer to :func:`alloc_mint_id` / :func:`alloc_private_ef` at emit time.

    A ``model`` is required for a real emit but NOT for a pure schema check -- pass
    ``require_model=False`` semantics by simply omitting it and reading the returned ``model=None``.
    """
    if not isinstance(block, dict):
        raise SummonDeployError(f"[[summon]] block must be a table, got {type(block).__name__}")
    lane = str(block.get("lane", "hybrid")).lower()
    if lane not in LANES:
        raise SummonDeployError(f"[[summon]] lane must be one of {list(LANES)}, got {block.get('lane')!r}")

    donor_raw = block.get("donor")
    if donor_raw is None and block.get("sequence"):
        # An authored (`sequence=`) block has no donor at all -- do NOT silently fall back to
        # DEFAULT_DONOR (Bahamut). A pure-authored cast reads no stock content, so a donor id here would
        # be a LIE: it would claim a relationship to a creature/skeleton this block never touches, and on
        # the hybrid lane it would arm `[SfxHybrid] EffectId = 227` -- posing the model on BAHAMUT's live
        # bones for a creature that was never rigged to them. `donor` stays ``None``; donor-dependent
        # features (the hybrid lane; a donor-decode `clips` selector) refuse it explicitly below / in
        # :func:`_decode_donor_clips` rather than crashing or silently defaulting.
        donor = None
    else:
        if donor_raw is None:
            donor_raw = DEFAULT_DONOR
        if isinstance(donor_raw, str) and not donor_raw.strip().isdigit():
            raise SummonDeployError(
                f"[[summon]] donor {donor_raw!r} is a name -- the deploy engine takes the NUMERIC effect "
                "id (e.g. 227 for Bahamut). Resolve a SpecialEffect name to its id in the block-schema "
                "layer first, or pass the numeric id.")
        donor = _as_int(donor_raw, "[[summon]] donor")
        if donor <= 0:
            raise SummonDeployError(f"[[summon]] donor id {donor} must be positive")

    if lane == "hybrid" and donor is None:
        raise SummonDeployError(
            '[[summon]] lane = "hybrid" needs a `donor` -- the s58 SfxHybridDrive engine feature poses '
            "the model on a REAL donor's live skeleton (`[SfxHybrid] EffectId` = donor); an authored "
            "(`sequence=`) block with no donor has no skeleton to pose on. Use lane = \"overlay\" (the "
            "default a donor-less block should reach for) or add a `donor`.")

    group = str(block.get("group", DEFAULT_GROUP)).upper()
    # validate the group early (bad group -> unknown ModelType) via the mint helper's table
    form = str(block.get("form", DEFAULT_FORM)).upper()

    new_id = block.get("id")
    if new_id is not None:
        new_id = _as_int(new_id, "[[summon]] id")
        if new_id < MINT_BAND_START:
            raise SummonDeployError(
                f"[[summon]] id {new_id} is below the mint band {MINT_BAND_START} (real GEO ids 0..5511)")
    name = block.get("name")
    if name is None and new_id is not None:
        name = derive_summon_name(new_id, group, form)
    if name is not None:
        _mint.validate_mint_name(name)                  # raises ValueError -> surfaced below
    # else: name derives at emit once id is allocated.

    private_ef = block.get("private_ef")
    if private_ef is not None:
        private_ef = _as_int(private_ef, "[[summon]] private_ef")
        _check_private_ef_static(private_ef, donor)

    hide_meshes = block.get("hide_meshes")
    if hide_meshes is not None:
        hide_meshes = [_norm_mesh_key(k) for k in hide_meshes]

    hide_mask = _norm_hide_mask(block.get("hide_mask", "0x3"))
    node_count = _as_int(block.get("node_count", 93), "[[summon]] node_count")
    clips = block.get("clips", "all")
    staging, staging_curves = _norm_staging(block.get("staging", "donor"))
    if staging_curves is None and block.get("staging_curves") is not None:
        # RE-NORMALIZING AN ALREADY-NORMALIZED SPEC. This function's contract (and ``emit_overlay`` /
        # ``emit_hybrid``'s docstrings) is that it is IDEMPOTENT -- ``deploy()`` normalizes, then the lane
        # emitter normalizes again. A curve table breaks that naively: the first pass SPLITS
        # ``staging = <table>`` into ``staging = "curves"`` + a separate ``staging_curves`` key, so the
        # second pass saw a bare ``"curves"`` string with no table and refused a block that emits fine when
        # the emitter is called directly. (That is exactly the split between ``emit_overlay(block, ...)``,
        # which the study's build scripts use, and the real ``summon-deploy`` CLI, which goes through
        # ``deploy()`` -- so it only bit the actual deploy command.) Adopt the already-split table.
        staging_curves = dict(block["staging_curves"])

    textures = block.get("textures")
    if textures is not None:
        textures = [str(t) for t in textures]
    particles = block.get("particles")
    if particles is not None:
        particles = [str(p) for p in particles]
    sequence = block.get("sequence")
    if sequence is not None:
        sequence = str(sequence)
    manifest = str(block.get("manifest", DEFAULT_MANIFEST_NAME))
    if "/" in manifest or "\\" in manifest:
        raise SummonDeployError(
            f"[[summon]] manifest {manifest!r} must be a BARE file name -- FileList.txt's grammar splits on "
            "single spaces and AssetManager resolves the name relative to the ef folder itself "
            "(SFXData.cs:253-254)")

    # ------------------------------------------------------------------- the SHORT/FULL pair (K6)
    short_sequence = block.get("short_sequence")
    if short_sequence is not None:
        short_sequence = str(short_sequence)
        if sequence is not None and _same_path(sequence, short_sequence):
            raise SummonDeployError(
                "[[summon]] short_sequence is the same file as `sequence` (after path normalization) -- a "
                "short/full pair needs two DIFFERENT casts (the engine plays Vfx2 verbatim when "
                "cmd.info.short_summon != 0, btl_vfx.cs:99); pointing both vfx slots at one .seq is a "
                "pointless pair.")

    short_private_ef = block.get("short_private_ef")
    if short_private_ef is not None:
        short_private_ef = _as_int(short_private_ef, "[[summon]] short_private_ef")
        _check_private_ef_static(short_private_ef, donor)
        if private_ef is not None and short_private_ef == private_ef:
            raise SummonDeployError(
                f"[[summon]] short_private_ef {short_private_ef} equals private_ef {private_ef} -- the "
                "short cast needs its OWN private host id (a distinct ef### folder); a FileList.txt in the "
                "same folder as the full cast's .seq would collide with it.")

    roll_mp, roll_command, roll_ability = (block.get("roll_mp"), block.get("roll_command"),
                                           block.get("roll_ability"))
    # `short_staging` -- THE SHORT CAST'S OWN TIMELINE (review 2026-07-24 addendum). It must NOT default to
    # or copy the primary's `staging`/`staging_curves`: the two casts have independently-authored lengths
    # (the bench case: primary ~23.0s/260 frames, short ~9.3s/110 frames), so a short folder wearing the
    # full's Movement/Rotation/Scaling envelope would render at the wrong pace/position for its own
    # shorter window. Grammar mirrors `staging`/`[summon.staging]` exactly, minus the "donor" mode (there
    # is no donor splice for a short cast at all -- it is always fully authored, K1's self-load shape).
    short_staging_curves = _norm_short_staging(block.get("short_staging"))
    if short_staging_curves is None and block.get("short_staging_curves") is not None:
        # idempotent re-normalize (mirrors the `staging`/`staging_curves` split below)
        short_staging_curves = dict(block["short_staging_curves"])
    # `short_manifest` -- the SHORT folder's OWN bare .sfxmodel file name (review 2026-07-24, item 2): the
    # two ef folders are otherwise both named from `manifest`, so a pair block could never give them
    # distinct manifest file names (the bench needs exactly this: the deployed short folder keeps
    # `nimbra_manifest.sfxmodel` while the full's own spec renames to `nimbra_full_manifest.sfxmodel`).
    # Defaults to `manifest` (today's behaviour) when short_sequence is set and short_manifest is omitted.
    short_manifest = block.get("short_manifest")
    if short_manifest is not None:
        short_manifest = str(short_manifest)
        if "/" in short_manifest or "\\" in short_manifest:
            raise SummonDeployError(
                f"[[summon]] short_manifest {short_manifest!r} must be a BARE file name -- FileList.txt's "
                "grammar splits on single spaces and AssetManager resolves the name relative to the ef "
                "folder itself (SFXData.cs:253-254)")

    if short_sequence is not None:
        if roll_mp is None or roll_command is None or roll_ability is None:
            raise SummonDeployError(
                "[[summon]] short_sequence needs `roll_mp` (the hosting ability's own MP cost), "
                "`roll_command` (its BattleCommandId, name or 0-47 id), AND `roll_ability` (its "
                "BattleAbilityId, an int) -- ALL THREE. The short/full pick is a per-command-AND-"
                "per-ability AbilityFeatures roll standing in for DecideSummonType, which never reaches a "
                "custom command (btl_cmd.cs:1025-1028 gates on cmd_no in {SummonGarnet, SummonEiko, "
                "Phantom}). The deploy engine refuses to guess the wiring rather than silently never "
                "rolling.")
        roll_mp = _as_int(roll_mp, "[[summon]] roll_mp")
        if roll_mp < 0:
            raise SummonDeployError(f"[[summon]] roll_mp {roll_mp} must be >= 0")
        from ..battle import characterdelta as _cd
        try:
            roll_command = _cd._resolve_command(roll_command, ctx="[[summon]] roll_command")
        except _cd.CharacterDeltaError as e:
            raise SummonDeployError(str(e)) from e
        if roll_command == 0:
            raise SummonDeployError(
                "[[summon]] roll_command 0 ('None') is not a real command -- the roll's Condition gates on "
                "CommandId == roll_command, and no cast is ever dispatched under command 0")
        # THE ABILITY-DISCRIMINATION LAW (review 2026-07-24, item 1): a minted command can host SEVERAL
        # abilities (the rung-8 bench's command 46 hosts four). CommandId alone does not discriminate --
        # every ability sharing that command would roll IsShortSummon, flipping the OTHERS onto their own
        # Vfx2 (btl_vfx.cs:99) and taking a 2/3 damage cut wherever their own formula reads IsShortSummon
        # (e.g. BattleCalculator.cs:515). `AbilityId` is bound right alongside `CommandId`
        # (NCalcUtility.cs:631-632, InitializeExpressionCommand) in the SAME Condition context
        # TriggerOnCommand evaluates (CharacterAbilityGems.cs:774) -- int only: `AbilityCastingName` is
        # explicitly flagged "Language dependent" in the engine's own source comment (NCalcUtility.cs:634),
        # so a name-based `roll_ability` would silently break on a non-English install.
        if isinstance(roll_ability, bool):
            raise SummonDeployError(f"[[summon]] roll_ability must be an int, got {roll_ability!r}")
        try:
            roll_ability = _as_int(roll_ability, "[[summon]] roll_ability")
        except SummonDeployError:
            raise SummonDeployError(
                f"[[summon]] roll_ability must be an int (the hosting ability's BattleAbilityId) -- an "
                f"ability NAME is refused: AbilityCastingName is explicitly flagged 'Language dependent' "
                f"in the engine's own source (NCalcUtility.cs:634), got {roll_ability!r}")
        from ..battle import abilityfeatures as _af
        if not (0 <= roll_ability <= _af._AA_MAX):
            raise SummonDeployError(
                f"[[summon]] roll_ability {roll_ability} out of range (0-{_af._AA_MAX})")
        if roll_ability == 0:
            raise SummonDeployError(
                "[[summon]] roll_ability 0 (Void) is not a real ability -- the roll's Condition gates on "
                "AbilityId == roll_ability, and Void never actually casts")
        if short_staging_curves is None:
            raise SummonDeployError(
                "[[summon]] short_sequence needs a [summon.short_staging] curve table -- the short cast "
                "hosts its OWN FBX creature self-load (K1's LoadSFX-on-itself shape) with its OWN timeline; "
                "an omitted Movement/Rotation curve pins the model at the world origin / zero rotation for "
                "the WHOLE short cast (THE MOVEMENT TRAP -- the same law the primary's staging=\"curves\" "
                "mode already enforces). It must NOT silently default to the primary's own `staging` -- the "
                "two casts have independent lengths. A single hold-still piece (from == to) is a legal, "
                "minimal short_staging.")
        _validate_staging(short_staging_curves, clips)
        if short_manifest is None:
            short_manifest = manifest                  # default: the SAME bare name as the primary's
    else:
        if roll_mp is not None or roll_command is not None or roll_ability is not None:
            raise SummonDeployError(
                "[[summon]] roll_mp/roll_command/roll_ability are only meaningful together with "
                "`short_sequence` (there is nothing to roll between without a second cast) -- add "
                "short_sequence, or remove them.")
        if short_staging_curves is not None:
            raise SummonDeployError(
                "[[summon]] short_staging is only meaningful together with `short_sequence` -- remove it, "
                "or add short_sequence.")
        if short_manifest is not None:
            raise SummonDeployError(
                "[[summon]] short_manifest is only meaningful together with `short_sequence` -- remove it, "
                "or add short_sequence.")

    if staging == "curves" and staging_curves is None:
        raise SummonDeployError(
            '[[summon]] staging = "curves" needs an authored [summon.staging] table (anchor/start/end + '
            "[[summon.staging.move]]/[[summon.staging.turn]]/[[summon.staging.scale]]/[[summon.staging.play]]"
            ") -- otherwise there are no curves to emit and the creature would stage at the world origin "
            "(THE MOVEMENT TRAP).")
    if staging_curves is not None:
        _validate_staging(staging_curves, clips)

    return {
        "lane": lane, "donor": donor, "model": block.get("model"), "textures": textures,
        "id": new_id, "name": name, "group": group, "form": form,
        "private_ef": private_ef,
        "hide_native": bool(block.get("hide_native", True)),
        "hide_mask": hide_mask, "node_count": node_count,
        "apply_column_scale": bool(block.get("apply_column_scale", False)),
        "hide_meshes": hide_meshes,
        "clips": clips, "staging": staging, "staging_curves": staging_curves,
        "sequence": sequence, "particles": particles, "manifest": manifest,
        "short_sequence": short_sequence, "short_private_ef": short_private_ef,
        "roll_mp": roll_mp, "roll_command": roll_command, "roll_ability": roll_ability,
        "short_staging_curves": short_staging_curves, "short_manifest": short_manifest,
    }


def _norm_staging(raw) -> tuple:
    """``staging`` -> ``(mode, curves_table_or_None)``.

    Two accepted forms, because the storyboard's own example (``staging = "curves"`` **and** a
    ``[summon.staging]`` table) is not expressible in TOML -- one key cannot be a string and a table at
    once. The TABLE form is canonical:

      * ``[summon.staging]`` (a table)  -> mode ``"curves"``, the table IS the curve spec;
      * ``staging = "donor"``           -> mode ``"donor"`` (the default: decode the donor's own staging);
      * ``staging = "curves"``          -> mode ``"curves"`` with NO table, which
        :func:`normalize_spec` then refuses with the fix spelled out.
    """
    if isinstance(raw, dict):
        return "curves", dict(raw)
    mode = str(raw).lower()
    if mode not in ("donor", "curves"):
        raise SummonDeployError(
            f"[[summon]] staging must be 'donor', 'curves', or a [summon.staging] curve table, got {raw!r}")
    return mode, None


def _norm_short_staging(raw) -> "dict | None":
    """``short_staging`` -> the curve table, or ``None``. Unlike :func:`_norm_staging`, there is no
    "donor" mode here at all -- the short cast never splices a donor's own staging (it is always fully
    authored, K1's self-load shape), so a bare string is always a mistake worth refusing by name rather
    than silently coercing."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        return dict(raw)
    raise SummonDeployError(
        f"[[summon]] short_staging must be a [summon.short_staging] curve table (there is no 'donor' mode "
        f"for the short cast -- it is always fully authored, independent of the primary's own staging), "
        f"got {raw!r}")


# --------------------------------------------------------------------------- staging = "curves" (K4)

def authored_clip_paths(clips) -> "list | None":
    """``clips`` -> the AUTHORED file-path list, or ``None`` when it is the donor-decode selector.

    The two forms are told apart by CONTENT, not by a flag: a list whose every element is an int (or an
    all-digit string) is a donor CLIP-INDEX list; anything else is a list of authored ``.anim`` paths.
    A bare string (``"all"``/``"none"``/``"0 1 2"``) is always the donor selector."""
    if not isinstance(clips, (list, tuple)):
        return None
    if not clips:
        return []
    if all(isinstance(c, int) or (isinstance(c, str) and c.strip().isdigit()) for c in clips):
        return None
    return [str(c) for c in clips]


def clip_key_of(index: int, path=None) -> int:
    """The on-disc ``.anim`` key for the ``index``-th AUTHORED clip. ``anim_disc_path`` names clip files
    ``{key}.anim`` and the engine's playlist keys a clip by ``Path.GetFileNameWithoutExtension``
    (``SFXDataMesh.cs:789``), so the key doubles as the clip's runtime NAME -- it just has to be unique
    and stable, and the manifest's ``Animations[].Path`` must agree with it.

    Two forms, so an upstream clip author can pin a key OR stay out of the way:

      * a NUMERIC file stem (``0.anim``) is taken AT ITS WORD -- the author has chosen the key;
      * anything else (``emerge.anim``) gets ``AUTHORED_CLIP_KEY_BASE + index``, which reads back in the
        deployed tree as an unmistakably minted key and can never collide with a stock clip (stock keys
        top out at 14739).

    Either way the kit writes both the file and the manifest entry from THIS function, so they cannot
    disagree."""
    if path is not None:
        stem = Path(str(path)).stem
        if stem.isdigit():
            return int(stem)
    return AUTHORED_CLIP_KEY_BASE + int(index)


def clip_name_map(clips) -> dict:
    """Authored clips -> ``{stem: key}`` (plus ``{str(key): key}`` so a ``play.clip`` may name either).
    Empty for the donor-decode selector.

    Refuses two ALIASING collisions, neither of which the engine would ever surface as an error -- it
    would just silently do the wrong thing:

      * **same key, different clip** -- an explicit numeric stem (``60001.anim``) landing on the same
        key an auto-derived stem resolves to (``AUTHORED_CLIP_KEY_BASE + index``), or two explicit
        numeric stems repeating a key. ``_stage_authored_clips`` and this map are BOTH keyed by the
        number, and both write to ``anim_disc_path(mod_root, id, key)`` -- the second clip's write
        silently OVERWRITES the first clip's ``.anim`` file on disc, with no error at deploy or in-game
        (the symptom is "my emerge clip plays drift's motion").
      * **same stem, different key** -- two authored clips sharing a file NAME (``a/emerge.anim`` and
        ``b/emerge.anim``) but different (auto-derived, positional) keys. ``out[stem] = key`` is a plain
        dict assignment, so the second entry SILENTLY REPLACES the first in the name map -- a
        ``play.clip = "emerge"`` row can then only ever reach the second clip; the first is staged to
        disc under its own key but becomes unreachable by name."""
    paths = authored_clip_paths(clips)
    if not paths:
        return {}
    out: dict = {}
    key_owner: dict = {}          # key -> (index, stem) of the clip that first claimed it
    for i, p in enumerate(paths):
        stem = Path(p).stem
        key = clip_key_of(i, p)
        if key in key_owner and key_owner[key][1] != stem:
            other_i, other_stem = key_owner[key]
            raise SummonDeployError(
                f"[[summon]] clips[{i}] ({stem!r}) and clips[{other_i}] ({other_stem!r}) both resolve to "
                f".anim key {key} -- the on-disc file AND the manifest's playlist entry are keyed by this "
                "number, so the second clip's write would silently overwrite the first's .anim file with "
                "no error. Rename one clip file, or renumber the numeric stem that collided.")
        key_owner[key] = (i, stem)
        if stem in out and out[stem] != key:
            raise SummonDeployError(
                f"[[summon]] clips has two authored clips both named {stem!r} (position {i} and an "
                f"earlier one) with DIFFERENT keys ({key} vs {out[stem]}) -- the name map can only hold "
                f"one key per stem, so `play.clip = {stem!r}` would silently reach only the later clip. "
                "Rename one of the files.")
        out[stem] = key
        out[str(key)] = key
    return out


def _num(v) -> str:
    """A curve number -> its expression text. Ints stay int-shaped (``190`` not ``190.0``) so the emitted
    JSON reads like the hand-authored stock manifests."""
    f = float(v)
    return str(int(f)) if f == int(f) else repr(round(f, 6))


def _axis_expr(prefix, axis: str, offset) -> str:
    """One axis of a curve endpoint: ``TargetAveragePositionY - 900`` / ``190`` (anchor ``world``)."""
    if prefix is None:
        return _num(offset)
    f = float(offset)
    if f == 0:
        return f"{prefix}{axis}"
    return f"{prefix}{axis} {'+' if f > 0 else '-'} {_num(abs(f))}"


def _triple(v, who: str) -> list:
    """A curve endpoint: a 3-list, or a scalar meaning "uniform on all three axes" (Scaling's usual form)."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return [float(v)] * 3
    if isinstance(v, (list, tuple)) and len(v) == 3 and all(
            isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
        return [float(x) for x in v]
    raise SummonDeployError(f"{who} must be a 3-number list [x, y, z] or a single number, got {v!r}")


def _validate_staging(st: dict, clips) -> None:
    """Structural validation of a ``[summon.staging]`` table (no I/O). The duration invariants come
    straight from the engine: every curve is evaluated against the SAME frame counter, so all three must
    span the whole ``end - start`` window or the tail of the shortest one freezes on its last piece."""
    if not isinstance(st, dict):
        raise SummonDeployError("[summon.staging] must be a table")
    unknown = set(st) - _STAGING_TABLE_KEYS
    if unknown:
        raise SummonDeployError(
            f"[summon.staging] has unknown key(s) {sorted(unknown)} -- valid keys: "
            f"{sorted(_STAGING_TABLE_KEYS)}")
    anchor = str(st.get("anchor", "target_average")).lower()
    if anchor == "target":
        raise SummonDeployError(f"[summon.staging] {_ANCHOR_TARGET_REFUSAL}")
    if anchor not in STAGING_ANCHORS:
        raise SummonDeployError(
            f"[summon.staging] anchor must be one of {sorted(STAGING_ANCHORS)}, got {anchor!r}")
    start = _as_int(st.get("start", 0), "[summon.staging] start")
    if "end" not in st:
        # `start`/`end` both silently default to 0 in staging_curves_json (STORYBOARD 6.4's own emit
        # rule: Start==End==0 tells the ENGINE to auto-derive the window, SFXDataMesh.cs:803-808). But
        # THIS validator's duration-sum invariant (below) is gated on `if span and ...` -- a span of 0
        # (the same default) makes that gate falsy and SILENTLY SKIPS the invariant, indistinguishable
        # from "the author explicitly wants auto-derive". Require `end` explicitly so an omission (a
        # typo, not a choice) is caught here instead of disabling the check it was meant to run.
        raise SummonDeployError(
            "[summon.staging] needs an explicit `end` -- even `end = 0` if you want the engine's own "
            "auto-derive route (Start==End, SFXDataMesh.cs:803-808). An OMITTED `end` defaults to 0 too, "
            "which makes `span = end - start` also 0 and SILENTLY DISABLES the duration-sum invariant "
            "below (`if span and total != span` -- a falsy span never runs the check), so a genuine typo "
            "and a deliberate auto-derive become indistinguishable. Pin `end` explicitly.")
    end = _as_int(st.get("end", 0), "[summon.staging] end")
    if end < start:
        raise SummonDeployError(f"[summon.staging] end {end} is before start {start}")
    span = end - start

    for key in ("move", "turn", "scale"):
        pieces = st.get(key) or []
        if not isinstance(pieces, (list, tuple)):
            raise SummonDeployError(f"[[summon.staging.{key}]] must be an array of tables")
        if not pieces:
            if key in _REQUIRED_CURVES:
                raise SummonDeployError(_REQUIRED_CURVES[key])
            continue                      # `scale` only -- see _REQUIRED_CURVES' note on the identity seed
        total = 0
        for i, p in enumerate(pieces):
            where = f"[[summon.staging.{key}]] #{i}"
            if not isinstance(p, dict):
                raise SummonDeployError(f"{where} must be a table")
            unknown = set(p) - _CURVE_PIECE_KEYS
            if unknown:
                raise SummonDeployError(
                    f"{where} has unknown key(s) {sorted(unknown)} -- valid keys: {sorted(_CURVE_PIECE_KEYS)}")
            total += _as_int(p.get("duration", 0), f"{where} duration")
            if "to" not in p:
                raise SummonDeployError(f"{where} needs a `to` destination")
            _triple(p["to"], f"{where} to")
            if "from" in p:
                _triple(p["from"], f"{where} from")
            elif i == 0:
                raise SummonDeployError(
                    f"{where} is the FIRST piece and has no `from` -- there is no previous destination to "
                    "inherit (ParametricMovement.cs:88-105), so its origin expression would stay null")
            for e in (p.get("ease") or []):
                if str(e) in _TURNING_EASES:
                    raise SummonDeployError(
                        f"{where} ease {e!r} is SPRITE-ONLY and would CRASH this creature. "
                        f"ParametricMovement.cs:233-237 calls customParam.TryGetValue(0, out baseAngle) "
                        f"with no null guard on exactly the Turning1/Turning2 arms, and the FBX render "
                        f"path passes customParam = null on all three curves (SFXDataMesh.cs:843-845) -- "
                        f"a NullReferenceException on every render frame of the cast. Only the sprite "
                        f"path supplies a dict (p.param, SFXDataMesh.cs:1285), which is why a PARTICLE "
                        f".sfxmodel may use them. On an FBX curve use one of {list(_FBX_EASES)}.")
                if str(e) not in _EASES:
                    raise SummonDeployError(
                        f"{where} ease {e!r} is not one of {list(_EASES)} -- TryParseInterpolateType "
                        "(ParametricMovement.cs:273-285) silently falls back to Constant, so a typo here "
                        "freezes that axis at its origin with no log")
        if span and total != span:
            raise SummonDeployError(
                f"[[summon.staging.{key}]] durations sum to {total} but end - start = {span}. Every curve "
                "is sampled against the same frame counter -- a short one freezes on its last piece while "
                "the others keep moving.")

    names = clip_name_map(clips)
    for i, p in enumerate(st.get("play") or []):
        where = f"[[summon.staging.play]] #{i}"
        if not isinstance(p, dict):
            raise SummonDeployError(f"{where} must be a table")
        unknown = set(p) - _PLAY_ROW_KEYS
        if unknown:
            raise SummonDeployError(
                f"{where} has unknown key(s) {sorted(unknown)} -- valid keys: {sorted(_PLAY_ROW_KEYS)}")
        clip = p.get("clip")
        if clip is None:
            raise SummonDeployError(f"{where} needs a `clip`")
        if names and str(clip) not in names:
            raise SummonDeployError(
                f"{where} clip {clip!r} is not one of the block's authored clips {sorted(k for k in names if not k.isdigit())}")
        speed = float(p.get("speed", 1))
        if speed <= 0:
            raise SummonDeployError(
                f"{where} speed must be > 0 (animMaxFrame = ceil(numFrames / speed), SFXDataMesh.cs:852)")
        if _as_int(p.get("repeat", 1), f"{where} repeat") < 1:
            raise SummonDeployError(f"{where} repeat must be >= 1")


def staging_curves_json(spec: dict, staging_curves: "dict | None" = None) -> dict:
    """The authored ``[summon.staging]`` table -> the ``.sfxmodel`` FBX entry's
    ``Start``/``End``/``Movement``/``Rotation``/``Scaling``/``Animations`` keys (K4).

    ``Movement`` is ANCHORED (offsets are added to the anchor's NCalc position parameters); ``Rotation``
    and ``Scaling`` are ABSOLUTE -- rotation is applied raw to ``eulerAngles`` with no battle-actor base
    (``SFXDataMesh.cs:844``, THE ROTATION BASELINE LAW) and scaling is a plain factor. A piece that omits
    ``from`` emits NO ``Origin*`` keys at all, so the engine's own by-reference inheritance
    (``ParametricMovement.cs:88-105``) does the chaining -- re-emitting the previous destination would
    double-evaluate the NCalc expression.

    A curve with no pieces emits NO key at all, which leaves the engine's ``ParametricMovement`` empty
    and pins that transform channel at its constructor seed for the whole cast (see
    :data:`_REQUIRED_CURVES`). ``move`` and ``turn`` are therefore REQUIRED by :func:`_validate_staging`
    (their seed is ``Vector3.zero`` = the world origin / a wrong facing); ``scale`` is optional because
    its ``ParametricMovement(true)`` seed is ``Vector3.one``, a benign identity scale.

    ``staging_curves`` -- an explicit override (the SHORT cast's OWN ``short_staging_curves`` table,
    review 2026-07-24 addendum: the short/full pair each renders from its OWN curve table, never a shared
    one). Defaults to ``spec["staging_curves"]`` (the primary) for every pre-existing caller."""
    st = staging_curves if staging_curves is not None else spec["staging_curves"]
    anchor = str(st.get("anchor", "target_average")).lower()
    prefix = STAGING_ANCHORS[anchor]
    out: dict = {"Start": str(_as_int(st.get("start", 0), "start")),
                 "End": str(_as_int(st.get("end", 0), "end"))}
    for key, json_key, pfx in (("move", "Movement", prefix), ("turn", "Rotation", None),
                               ("scale", "Scaling", None)):
        pieces = st.get(key) or []
        if not pieces:
            continue
        out[json_key] = [_curve_piece(p, pfx) for p in pieces]
    names = clip_name_map(spec.get("clips"))
    playlist = []
    for p in (st.get("play") or []):
        key = names.get(str(p["clip"]), p["clip"])
        entry = {"Path": f"Animations/{spec['id']}/{key}"}
        speed = float(p.get("speed", 1))
        if speed != 1:
            entry["Speed"] = _num(speed)
        playlist += [dict(entry) for _ in range(int(p.get("repeat", 1)))]
    if playlist:
        out["Animations"] = playlist
    return out


def _curve_piece(p: dict, prefix) -> dict:
    d = {"Duration": str(_as_int(p.get("duration", 0), "duration"))}
    if "from" in p:
        for ax, v in zip("XYZ", _triple(p["from"], "from")):
            d[f"Origin{ax}"] = _axis_expr(prefix, ax, v)
    for ax, v in zip("XYZ", _triple(p["to"], "to")):
        d[f"Destination{ax}"] = _axis_expr(prefix, ax, v)
    for ax, e in zip("XYZ", (p.get("ease") or [])):
        d[f"InterpolationType{ax}"] = str(e)
    return d


def _norm_mesh_key(k) -> str:
    """A HideMeshes mesh KEY -> the bare uppercase hex form ``build_thomas.py`` splices as ``0x{key}``.
    Strips a leading ``0x``/``0X`` and validates the remainder is hex (else the ``.seq`` line is garbage
    the engine's ``TryGetArgMeshList`` silently drops)."""
    s = str(k).strip()
    bare = s[2:] if s[:2].lower() == "0x" else s
    if not bare or any(c not in "0123456789abcdefABCDEF" for c in bare):
        raise SummonDeployError(f"[[summon]] hide_meshes key {k!r} is not a hex mesh key")
    return bare


def _norm_hide_mask(v) -> str:
    """``hide_mask`` -> the ``"0x..."`` hex-string form ``[SfxHybrid] HideMask`` needs. The engine's
    ``LoadHex`` (``s58-sfx-hybrid-drive.patch``) strips an optional ``0x``/``0X`` prefix and then parses
    the remainder with ``NumberStyles.HexNumber`` -- so a BARE decimal-looking string is silently parsed
    AS HEX (``hide_mask = 12`` naively ``str()``'d to ``"12"`` would arm ``HideMask = 12``, which the
    engine reads as ``0x12`` = 18, not the 12 the TOML author meant). Accepts:

      * a TOML **int** -- the actual mask VALUE; rendered to its hex string (``12 -> "0xc"``, matching
        the engine's own parse so the value round-trips correctly);
      * a **``"0x..."``/``"0X..."`` string** -- kept as given (already the form the engine expects), just
        hex-validated;
      * anything else raises -- a bare non-prefixed string (``"12"``, ``"0011"``) is exactly the shape
        that silently corrupts the mask, so it is refused rather than guessed at."""
    if isinstance(v, bool):
        raise SummonDeployError(f"[[summon]] hide_mask must be an int or a '0x...' hex string, got {v!r}")
    if isinstance(v, int):
        return f"0x{v:x}"
    if isinstance(v, str):
        s = v.strip()
        bare = s[2:] if s[:2].lower() == "0x" else None
        if bare and all(c in "0123456789abcdefABCDEF" for c in bare):
            return s
        raise SummonDeployError(
            f"[[summon]] hide_mask {v!r} must be an int (e.g. 3) or a '0x...' hex string (e.g. \"0x3\") -- "
            "the engine's HideMask parser reads a bare string AS HEX, so a plain decimal-looking string "
            "would silently arm the wrong mask")
    raise SummonDeployError(f"[[summon]] hide_mask must be an int or a '0x...' hex string, got {v!r}")


def _check_private_ef_static(private_ef: int, donor: int) -> None:
    """The install-INDEPENDENT half of the private-ef validator (DESIGN section 1.3): must be in the absent
    set and must not equal the donor. (The install-content check is :func:`validate_private_ef`.)"""
    if private_ef == donor:
        raise SummonDeployError(
            f"[[summon]] private_ef {private_ef} equals donor {donor} -- the private host must be a "
            "DIFFERENT, stock-absent id (a FileList in the donor's own folder kills the native cast)")
    if private_ef not in ABSENT_EF_IDS:
        raise SummonDeployError(
            f"[[summon]] private_ef {private_ef} is not a stock-absent effect id -- pick one of "
            f"{sorted(ABSENT_EF_IDS)} (an id with a real native creature would trip the "
            "donor-FileList replacement law). Default = auto-alloc.")


def lint_spec(block: dict) -> list:
    """Return every install-independent problem with a ``[[summon]]`` block as a list of strings (empty =
    clean). Never raises -- for a build-time lint pass. Also emits the ``vfx1`` cast-trigger REMINDER
    (DESIGN section 1.4: the block does NOT wire the ability; point an ability's ``vfx1`` at
    ``private_ef``)."""
    problems: list = []
    try:
        spec = normalize_spec(block)
    except (SummonDeployError, ValueError) as e:
        return [str(e)]
    if not spec.get("model"):
        problems.append("[[summon]] needs a `model` (the user's retargeted FBX on the donor's rig)")
    pe = spec["private_ef"] if spec["private_ef"] is not None else "<auto>"
    problems.append(
        f"[[summon]] reminder: the block emits assets + an ARM manifest, NOT the ability -- point a summon "
        f"ability's `vfx1` at private_ef={pe} (see authoring-ff9-battles / battle/actiondelta.py); "
        "this lint never edits Actions.csv.")
    return problems


# --------------------------------------------------------------------------- the host .seq splice

def _hide_meshes_arg(hide_meshes) -> str:
    """``hide_meshes`` -> the ``" ; HideMeshes=0xK1,0xK2,..."`` clause spliced onto the anchor line, byte-
    identical to ``build_thomas.py:_hide_meshes_arg``. ``None``/empty = ``""`` (CALIBRATE: the anchor line
    is then the stock donor's own, unsuppressed)."""
    if not hide_meshes:
        return ""
    tokens = ",".join(f"0x{_norm_mesh_key(k)}" for k in hide_meshes)
    return f" ; HideMeshes={tokens}"


def find_anchor(donor_text: str, sfx_name: "str | None" = None) -> tuple:
    """Locate the native-creature spawn line in a donor ``.seq``. Returns ``(index, sfx_name, newline)``
    where ``index`` is the 0-based line index (in ``splitlines(keepends=True)`` order), ``sfx_name`` is the
    matched ``SFX=`` token, and ``newline`` is that line's own terminator (preserved for byte-fidelity).

    Matches ``^PlaySFX: SFX=<X> ; Reflect=True$`` (per line, terminator stripped). If ``sfx_name`` is
    given, only that SFX matches. Raises :class:`DonorDriftError` if there is no match (the donor's shape
    changed) or an ambiguous multi-match with no ``sfx_name`` to disambiguate."""
    lines = donor_text.splitlines(keepends=True)
    hits = []
    for i, raw in enumerate(lines):
        body = raw.rstrip("\r\n")
        nl = raw[len(body):]
        m = _ANCHOR_RE.match(body)
        if m and (sfx_name is None or m.group("sfx") == sfx_name):
            hits.append((i, m.group("sfx"), nl))
    if not hits:
        want = "" if sfx_name is None else f" for SFX={sfx_name}"
        raise DonorDriftError(
            f"no 'PlaySFX: SFX=<name> ; Reflect=True' anchor line{want} in the donor .seq -- its shape "
            "changed since this splice was derived; abort rather than guess")
    if len(hits) > 1:
        names = ", ".join(sorted({h[1] for h in hits}))
        raise DonorDriftError(
            f"the donor .seq has {len(hits)} candidate anchor lines ({names}) -- pass sfx_name to pick one")
    return hits[0]


def _overlay_delta(private_ef: int, newline: str) -> list:
    """The overlay-lane StartThread self-load block (parameterized ``thomas_player_sequence.seq``): a
    background ``Sync=False`` thread that LoadSFX/PlaySFXes THIS folder's own ``private_ef`` as a second,
    JSON-mesh ``SFXData`` (Route A) so the user's FBX renders in parallel with the untouched native cast.
    Generated (not read from a committed Thomas-specific file), with the donor's own newline for a clean
    single-EOL-style output."""
    return [ln + newline for ln in (
        "StartThread: Condition=1 == 1 ; Sync=False",
        f"\tLoadSFX: SFX={private_ef} ; Char=Caster ; UseCamera=False",
        f"\tWaitSFXLoaded: SFX={private_ef}",
        f"\tPlaySFX: SFX={private_ef} ; SkipSequence=True",
        f"\tWaitSFXDone: SFX={private_ef}",
        "EndThread",
    )]


def splice_host_seq(donor_text: str, hide_meshes, *, private_ef: "int | None" = None,
                    overlay: bool = False, sfx_name: "str | None" = None) -> str:
    """The generalized ``build_thomas.py:splice_sequence``. Replace the donor's native-creature anchor
    line with the same line plus the ``HideMeshes`` clause; for ``overlay=True`` also insert the
    :func:`_overlay_delta` StartThread block immediately before it. ``overlay=False`` (the m1b-bench /
    hybrid shape) applies ONLY the anchor replacement -- byte-identical to the proven live host ``.seq``.

    Raises :class:`DonorDriftError` if the anchor isn't found (:func:`find_anchor`)."""
    idx, sfx, newline = find_anchor(donor_text, sfx_name)
    lines = donor_text.splitlines(keepends=True)
    patched = f"PlaySFX: SFX={sfx} ; Reflect=True{_hide_meshes_arg(hide_meshes)}{newline}"
    if not overlay:
        return "".join(lines[:idx] + [patched] + lines[idx + 1:])
    if private_ef is None:
        raise SummonDeployError("overlay splice needs a private_ef (the self-load StartThread target)")
    delta = _overlay_delta(private_ef, newline)
    return "".join(lines[:idx] + delta + [patched] + lines[idx + 1:])


# --------------------------------------------------------------------------- donor read (drift-guarded)

def donor_seq_path(game, donor: int) -> Path:
    """``<install>/StreamingAssets/Data/SpecialEffects/ef{donor:D3}/PlayerSequence.seq`` -- read-only."""
    return Path(game).joinpath(*_SFX_REL, f"ef{int(donor):03d}", HOST_SEQ_NAME)


def fetch_donor_seq(game, donor: int) -> str:
    """Read + drift-guard the pristine stock donor ``.seq``. Returns its text; NEVER writes it. Raises
    :class:`SummonDeployError` if absent (not a real donor) and :class:`DonorDriftError` if it doesn't
    match its registered :data:`EXPECTED_DONOR_SEQ_SHA` (an unregistered donor is allowed, unguarded)."""
    p = donor_seq_path(game, donor)
    if not p.is_file():
        raise SummonDeployError(
            f"donor ef{int(donor):03d}/{HOST_SEQ_NAME} not found at {p} -- effect {donor} is not a real "
            "cast in this install (or its .seq isn't loose on disc)")
    raw = p.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    exp = EXPECTED_DONOR_SEQ_SHA.get(int(donor))
    if exp is not None and got != exp:
        raise DonorDriftError(
            f"{p} sha256 {got} != expected {exp} -- the donor .seq changed since this splice was derived; "
            "refusing to splice against unverified stock content")
    return raw.decode("utf-8")


# --------------------------------------------------------------------------- private-ef allocation

def _sfx_dir(root, ef_id: int) -> Path:
    return Path(root).joinpath(*_SFX_REL, f"ef{int(ef_id):03d}")


def _install_has_native_ef(game, ef_id: int) -> bool:
    """True if the BASE install carries a real native effect at ``ef{id:D3}`` (an ``ef{id:D3}.bytes``
    payload or a populated ``ef{id:D3}/`` loose folder). Used to defend the absent-set claim against the
    actual install."""
    if game is None:
        return False
    game = Path(game)
    if (game / "StreamingAssets" / "Data" / "SpecialEffects" / f"ef{int(ef_id):03d}.bytes").is_file():
        return True
    d = _sfx_dir(game, ef_id)
    return d.is_dir() and any(d.iterdir())


def validate_private_ef(private_ef: int, donor: int, *, game=None, mod_root=None,
                        for_alloc: bool = False) -> None:
    """The full private-ef validator (DESIGN section 1.3). Always checks the static half (in the absent
    set, != donor). With ``game`` it also refuses an id that carries a real native effect in the install.
    With ``for_alloc=True`` it additionally refuses an id whose ``ef{id:D3}/`` folder already exists in
    ``mod_root`` (so auto-alloc never lands on an occupied slot); an EXPLICIT private_ef is allowed to
    re-use its own folder (the bench pins 84 across redeploys)."""
    _check_private_ef_static(private_ef, donor)
    if _install_has_native_ef(game, private_ef):
        raise SummonDeployError(
            f"[[summon]] private_ef {private_ef} carries a real native effect in the install -- it is not "
            "an empty private host (the absent-set census disagrees with this install; pick another)")
    if for_alloc and mod_root is not None:
        d = _sfx_dir(mod_root, private_ef)
        if d.is_dir() and any(d.iterdir()):
            raise SummonDeployError(f"ef{private_ef:03d}/ already populated in {mod_root}")


def alloc_private_ef(game, mod_root, donor: int) -> int:
    """The first stock-absent id (ascending) that has no native effect in the install AND no populated
    ``ef{id:D3}/`` folder in ``mod_root`` (DESIGN section 1.3). Raises if the whole pool is occupied."""
    for ef_id in sorted(ABSENT_EF_IDS):
        if ef_id == donor:
            continue
        try:
            validate_private_ef(ef_id, donor, game=game, mod_root=mod_root, for_alloc=True)
        except SummonDeployError:
            continue
        return ef_id
    raise SummonDeployError("no free private effect id -- every stock-absent slot is occupied")


def _next_absent_ef(private_ef: int) -> int:
    """The next stock-absent id AFTER ``private_ef`` in ascending order -- ``short_private_ef``'s default
    ("primary private_ef + 1" read as +1 POSITION in :data:`ABSENT_EF_IDS`'s ordered sequence, not literal
    arithmetic -- see the SHORT/FULL ROLL module comment above :func:`_stage_short_seq`)."""
    higher = sorted(a for a in ABSENT_EF_IDS if a > private_ef)
    if not higher:
        raise SummonDeployError(
            f"[[summon]] private_ef {private_ef} is the LAST stock-absent id in ascending order -- there "
            "is no default short_private_ef after it; set short_private_ef explicitly to one of "
            f"{sorted(ABSENT_EF_IDS)}")
    return higher[0]


def alloc_mint_id(mod_root) -> int:
    """The next free mint GEO id >= 6000 not already present as a ``Models/*/{id}/`` folder in
    ``mod_root`` (a deterministic default when the block omits ``id``)."""
    used = set()
    models = Path(mod_root).joinpath(*_mexport._RES, "Models")
    if models.is_dir():
        for type_dir in models.iterdir():
            if not type_dir.is_dir():
                continue
            for id_dir in type_dir.iterdir():
                if id_dir.is_dir() and id_dir.name.isdigit():
                    used.add(int(id_dir.name))
    i = MINT_BAND_START
    while i in used:
        i += 1
    return i


# --------------------------------------------------------------------------- the write ledger / revert

class _Ledger:
    """Accumulates every file write + backup + DictionaryPatch/ini change one emit performs, and renders a
    self-contained (stdlib-only) revert script -- the ``tools/deploy_field.py`` revert convention, scoped
    to a summon deploy. Backups snapshot a pre-existing file before overwrite; a newly-created file records
    ``None`` (revert deletes it)."""

    def __init__(self, backup_dir: Path):
        self.backup_dir = Path(backup_dir)
        self.stamp = time.strftime("%Y%m%d-%H%M%S")
        self.files: list = []          # (dest, backup|None)
        self.dict_line: "str | None" = None
        self.dict_path: "str | None" = None
        self.ini_backup: "str | None" = None
        self.ini_path: "str | None" = None

    def write_bytes(self, dest: Path, data: bytes) -> str:
        dest = Path(dest)
        backup = None
        if dest.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup = self.backup_dir / f"{dest.name}.pre-{self.stamp}"
            shutil.copyfile(dest, backup)
        dest.parent.mkdir(parents=True, exist_ok=True)
        fsutil.atomic_write_bytes(dest, data)
        if dest.read_bytes() != data:
            raise SummonDeployError(f"write verification failed at {dest} -- readback != what we wrote")
        self.files.append((str(dest), str(backup) if backup else None))
        return hashlib.sha256(data).hexdigest()

    def append_dict_line(self, dp: Path, directive: str) -> bool:
        dp = Path(dp)
        lines = dp.read_text(encoding="utf-8").splitlines() if dp.exists() else []
        if directive in lines:
            return False
        lines.append(directive)
        fsutil.atomic_write_text(dp, "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        self.dict_line, self.dict_path = directive, str(dp)
        return True

    def record_ini(self, ini_path: Path, backup: "Path | None") -> None:
        self.ini_path = str(ini_path)
        self.ini_backup = str(backup) if backup else None

    def revert_plan(self) -> dict:
        return {"files": self.files, "dict_line": self.dict_line, "dict_path": self.dict_path,
                "ini_path": self.ini_path, "ini_backup": self.ini_backup,
                "sfxhybrid_section": SFXHYBRID_SECTION}

    def write_revert_script(self, out_dir: Path, name: str) -> Path:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        # repr()-inject the plan (the reverttmpl hardening class, 44fcf794): repr of a str is always
        # a valid, fully-escaped Python literal, so no plan value can break out of the generated code
        # (a raw triple-quoted splice dies on any value containing three quotes).
        plan = json.dumps(self.revert_plan(), indent=2)
        script = _REVERT_TEMPLATE.replace("__PLAN__", repr(plan))
        specific = out_dir / f"revert_summon_{name}.py"
        fsutil.atomic_write_text(specific, script, encoding="utf-8", newline="\n")
        fsutil.atomic_write_text(out_dir / "revert_summon.py", script, encoding="utf-8", newline="\n")
        return specific


_REVERT_TEMPLATE = '''#!/usr/bin/env python3
"""Auto-generated revert for a [[summon]] deploy -- stdlib only (no ff9mapkit import).

Restores each backed-up file, deletes each file this deploy newly created, drops the DictionaryPatch
line this deploy added, and (hybrid lane) restores the Memoria.ini backup OR neutralizes [SfxHybrid].
Idempotent: safe to run more than once."""
import json, shutil
from pathlib import Path

PLAN = json.loads(__PLAN__)

for dest, backup in PLAN["files"]:
    dest = Path(dest)
    if backup:
        shutil.copyfile(backup, dest)
        print(f"restored {dest} <- {Path(backup).name}")
    elif dest.exists():
        dest.unlink()
        print(f"deleted  {dest}")
        # tidy now-empty parent chain (Models/<type>/<id>/, ef###/)
        parent = dest.parent
        while parent.exists() and parent.name and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent

if PLAN.get("dict_line") and PLAN.get("dict_path"):
    dp = Path(PLAN["dict_path"])
    if dp.exists():
        kept = [ln for ln in dp.read_text(encoding="utf-8").splitlines() if ln != PLAN["dict_line"]]
        dp.write_text("\\n".join(kept) + ("\\n" if kept else ""), encoding="utf-8", newline="\\n")
        print(f"dropped DictionaryPatch line: {PLAN['dict_line']}")

if PLAN.get("ini_path"):
    ini = Path(PLAN["ini_path"])
    if PLAN.get("ini_backup") and Path(PLAN["ini_backup"]).exists():
        shutil.copyfile(PLAN["ini_backup"], ini)
        print(f"restored Memoria.ini <- {Path(PLAN['ini_backup']).name}")
    elif ini.exists():
        # no pre-existing backup (the section was freshly added) -> neutralize it in place
        import re as _re
        text = ini.read_text(encoding="utf-8", errors="replace")
        sec = PLAN["sfxhybrid_section"]
        out, in_sec = [], False
        for line in text.splitlines():
            t = line.strip()
            if t.startswith("[") and not (t.startswith(";") or t.startswith("#")):
                in_sec = t.lower().startswith("[" + sec.lower() + "]")
            elif in_sec and "=" in line and line.split("=", 1)[0].strip().lower() == "enabled":
                line = "Enabled = 0"
            out.append(line)
        nl = "\\r\\n" if "\\r\\n" in text else "\\n"
        ini.write_text(nl.join(out), encoding="utf-8")
        print(f"neutralized [{sec}] Enabled = 0 in {ini}")
print("summon revert complete.")
'''


# --------------------------------------------------------------------------- model mint (rows 1 / 1b)

def _stage_model(spec: dict, mod_root: Path, ledger: _Ledger) -> dict:
    """Rows 1 + 1b (DESIGN section 2.1): the user's retargeted FBX (+ textures) to
    ``Models/{typeInt}/{id}/{id}.fbx`` and the idempotent ``3DModel`` DictionaryPatch line. Reuses
    :func:`ff9mapkit.models.mint.resolve_mint` for the id/name/type + directive; the FBX/PNG copies are
    BINARY-SAFE ``write_bytes`` (never ``stage_mint``'s ascii path, which corrupts a Kaydara binary FBX)."""
    model = spec["model"]
    if not model:
        raise SummonDeployError("[[summon]] needs a `model` (the user's retargeted FBX)")
    src_fbx = Path(model)
    if not src_fbx.is_file():
        raise SummonDeployError(f"[[summon]] model FBX not found: {src_fbx}")
    man = _mint.resolve_mint({"id": spec["id"], "name": spec["name"], "fbx": str(src_fbx)})
    dest_dir = Path(mod_root).joinpath(*_mexport._RES, *_mexport.model_dir_parts(man["type_int"], man["id"]))
    fbx_dest = dest_dir / f"{man['id']}.fbx"
    fbx_sha = ledger.write_bytes(fbx_dest, src_fbx.read_bytes())

    tex_specs = spec.get("textures")
    tex_srcs = [Path(t) for t in tex_specs] if tex_specs else sorted(src_fbx.parent.glob("*.png"))
    textures = []
    for t in tex_srcs:
        if not t.is_file():
            raise SummonDeployError(f"[[summon]] texture not found: {t}")
        ledger.write_bytes(dest_dir / t.name, t.read_bytes())
        textures.append(str(dest_dir / t.name))

    dp = Path(mod_root) / "DictionaryPatch.txt"
    added = ledger.append_dict_line(dp, man["directive"])
    man.update(fbx_dest=str(fbx_dest), fbx_sha256=fbx_sha, textures=textures,
               dictionary_patch=str(dp), directive_added=added)
    return man


# --------------------------------------------------------------------------- host .seq (row 2)

def _stage_host_seq(spec: dict, mod_root: Path, game, ledger: _Ledger, *, overlay: bool) -> dict:
    """Row 2: the host ``ef{private_ef:D3}/PlayerSequence.seq``.

    Two sources, and the second one is the rung-8 delta (K1):

      * ``sequence = "<file>.seq"`` -- an AUTHORED cast, copied VERBATIM. No donor is read, no splice is
        performed, no drift guard applies (there is no stock content in the chain at all), and the file is
        run through :mod:`ff9mapkit.summons.seqlint` first -- the engine drops an unknown op or arg key
        without a log, so an unlinted hand-authored cast is a silent-failure machine.
      * no ``sequence`` -- the historical transplant path: the drift-guarded donor ``.seq``, spliced. The
        donor is READ (never written); its unified diff is captured for the deploy receipt."""
    authored = spec.get("sequence")
    if authored:
        src = Path(authored)
        if not src.is_file():
            raise SummonDeployError(f"[[summon]] sequence file not found: {src}")
        problems = _lint_authored_sequence(spec, src)
        if problems:
            raise SummonDeployError(
                f"the authored sequence {src} does not lint -- refusing to deploy a cast the engine would "
                "silently drop pieces of:\n  " + "\n  ".join(problems))
        seq_dest = _sfx_dir(mod_root, spec["private_ef"]) / HOST_SEQ_NAME
        seq_sha = ledger.write_bytes(seq_dest, src.read_bytes())
        authored_text = src.read_text(encoding="utf-8-sig")
        return {"seq_dest": str(seq_dest), "seq_sha256": seq_sha, "seq_diff": "",
                "seq_source": str(src), "seq_authored": True, "text": authored_text}
    donor_text = fetch_donor_seq(game, spec["donor"])
    out_text = splice_host_seq(donor_text, spec.get("hide_meshes"), private_ef=spec["private_ef"],
                               overlay=overlay)
    seq_dest = _sfx_dir(mod_root, spec["private_ef"]) / HOST_SEQ_NAME
    seq_sha = ledger.write_bytes(seq_dest, out_text.encode("utf-8"))
    diff = "".join(difflib.unified_diff(
        donor_text.splitlines(keepends=True), out_text.splitlines(keepends=True),
        fromfile=f"stock/ef{spec['donor']:03d}/{HOST_SEQ_NAME}",
        tofile=f"ef{spec['private_ef']:03d}/{HOST_SEQ_NAME}"))
    return {"seq_dest": str(seq_dest), "seq_sha256": seq_sha, "seq_diff": diff, "text": out_text}


# --------------------------------------------------------------------------- the SHORT/FULL pair (K6)
"""
THE SHORT/FULL ROLL -- how `short_sequence` picks between two casts.

The engine's own summon roll (``DecideSummonType``, ``btl_cmd.cs:1583-1615``) sets ``cmd.info.short_summon``,
and ``btl_vfx.SelectCommandVfx``/``GetPlayerCommandSFX`` (``btl_vfx.cs:41-103``, the ``short_summon`` branch
at ``:99``) plays ``cmd.aa.Vfx2`` whenever ``cmd.info.short_summon != 0``, else ``VfxIndex`` (vfx1) -- so
vfx1 = FULL, vfx2 = SHORT. But ``DecideSummonType`` only RUNS for ``cmd.cmd_no`` in ``{SummonGarnet,
SummonEiko, Phantom}`` (``btl_cmd.cs:1025-1028``, inside ``CheckCommandCondition``'s ``switch``) -- a custom
command never reaches it, so a custom short/full pair needs its own roll. Memoria's ``AbilityFeatures``
NCalc system already has the write it needs: a ``>SA`` ``Command``-type feature may set
``command.IsShortSummon`` (``CharacterAbilityGems.cs:821``), and stock ships exactly one precedent -- ``>SA
59 Boost``: ``Command EvenImmobilized`` / ``[code=Condition] IsTheCaster [/code]`` / ``[code=IsShortSummon]
false [/code]`` (``AbilityFeatures.txt:842-845``) -- Boost forces every summon its wearer casts to the FULL
form.

QUESTION 3a -- is the caster's MP already deducted by the time our formula reads it? YES.
    The stock roll runs inside ``CheckCommandCondition`` (called from ``CMD_MODE_INSPECTION``,
    ``btl_cmd.cs:564``), comparing PRE-deduction MP: ``cmd.regist.cur.mp > cmd.aa.MP * 2``
    (``btl_cmd.cs:1605``). The ACTUAL deduction (``ConsumeMp``, ``btl_cmd.cs:1641-1652``) happens inside
    ``CheckMpCondition`` -- the THIRD operand of the SAME ``||`` chain at ``btl_cmd.cs:564``
    (``!CheckCommandCondition(...) || !CheckTargetCondition(...) || !CheckMpCondition(...)``), so it runs
    AFTER ``CheckCommandCondition`` within that one ``CMD_MODE_INSPECTION`` tick.
    Our own write happens in ``SupportingAbilityFeature.TriggerOnCommand``
    (``CharacterAbilityGems.cs:755``), called from the loop at ``btl_cmd.cs:594-595`` -- which only runs
    inside ``case command_mode_index.CMD_MODE_SELECT_VFX`` (``btl_cmd.cs:579-617``), a mode
    ``CMD_MODE_INSPECTION`` merely SETS and ``break``s out of (``btl_cmd.cs:577-578``) -- so
    ``CMD_MODE_SELECT_VFX`` runs on a LATER ``CommandEngine`` tick, after ``ConsumeMp`` has already run.
    NCalc's ``MP`` parameter reads the LIVE current MP (``NCalcUtility.cs:411``,
    ``expr.Parameters[prefix + "MP"] = unit.CurrentMp``) -- so by the time our formula evaluates, MP is
    POST-deduction: ``MP == pre_deduction_mp - mp_cost``.
    COMPENSATION: stock compares ``pre_deduction_mp > 2*mp_cost``. Substituting
    ``pre_deduction_mp = MP + mp_cost`` gives ``MP + mp_cost > 2*mp_cost  <=>  MP > mp_cost`` -- so the
    formula below thresholds on ``mp_cost`` (``roll_mp``), NOT ``2*mp_cost``. Using ``2*mp_cost`` against an
    already-deducted MP would silently demand ``pre_deduction_mp > 3*mp_cost``, biasing every cast whose
    true cost sits in ``(2x, 3x]`` toward the LOW branch (170/255) that stock would have rolled HIGH (230/255).
    CAVEAT (review FOLD-F): under dev cheats the deduction never runs at all -- ``ConsumeMp``'s guard is
    ``if (!FF9StateSystem.Battle.isDebug && (btl.bi.player == 0 || !FF9StateSystem.Settings.IsHpMpFull))``
    (``btl_cmd.cs:1651-1652``) -- so a debug/``IsHpMpFull`` session reads PRE-deduction MP through our
    POST-deduction-calibrated threshold, biasing every roll toward the HIGH branch (more shorts than a
    clean save would produce). This is a cheat-session artifact, not a bug in the formula.

QUESTION 3b -- if the caster ALSO has stock SA 59 Boost equipped, who wins? BOOST, BY CONSTRUCTION.
    ``TriggerOnCommand`` writes are a plain overwrite -- ``command.IsShortSummon =
    EvaluateNCalcCondition(e.Evaluate(), command.IsShortSummon)`` (``CharacterAbilityGems.cs:821``) -- so
    whichever SA feature runs LAST for the caster wins; there is no "leave untouched" expressible from our
    side (the current-value fallback only matters if OUR OWN formula fails to evaluate to a bool, which
    would be a bug, not a coexistence strategy). But the ORDER is fixed, not the HashSet-iteration order of
    equipped abilities: ``ff9abil.GetEnabledSA(BTL_DATA btl)`` (``ff9abil.cs:70-84``, the exact overload
    ``btl_cmd.cs:594`` calls) returns ``[Global, ...saMonster, ...saExtended (equipped SAs, Boost among
    them), GlobalLast]`` -- Global is ALWAYS first, GlobalLast ALWAYS last, regardless of what is equipped.
    Boost lives in ``saExtended`` (an ordinary equipped SA), so registering our own roll under ``>SA
    Global`` guarantees Boost's unconditional ``false`` (its own Condition is just ``IsTheCaster``, no
    CommandId check) runs STRICTLY AFTER ours and overwrites it -- Boost's "always full summon" promise is
    preserved for OUR command too, exactly as it already is for the stock ones. (The alternative,
    registering under ``GlobalLast``, would run AFTER Boost and silently break that promise -- refused by
    construction: this module only ever emits ``>SA Global``.)

THE HYBRID-LANE SHORT MECHANISM (MUST-FIX 1, review 2026-07-24). ``[SfxHybrid] EffectId`` always names the
PRIMARY's ``donor`` -- the s58 drive poses the primary's model on THAT donor's live skeleton, full stop.
A ``short_sequence`` is a fully-authored cast under its OWN ``short_private_ef``, wholly disconnected from
the hybrid drive (a donor is never read to build it, per :func:`_stage_short_seq`'s own doc). So regardless
of whether the BLOCK's ``lane`` is ``"hybrid"`` or ``"overlay"``, the short folder is ALWAYS staged the
OVERLAY/K1 way -- a self-contained ``FileList.txt`` + ``.sfxmodel`` manifest + verbatim particle copies
beside its own ``PlayerSequence.seq`` (:func:`_stage_short_overlay_folder`) -- because that manifest's own
``LoadSFX: SFX=<short_private_ef>`` self-load (K1's shape: the ``.seq`` loads ITSELF) is the only mechanism
that can render an FBX creature with no live donor skeleton driving it. A ``[[summon]]`` block with
``lane = "hybrid"`` therefore ends up running BOTH mechanisms side by side: the s58 drive for its own
(full) cast, and a private JSON-mesh ``SFXData`` instance for the short -- exactly the rung-7 overlay route,
just reached from a hybrid-lane block.

THE SHORT CAST'S OWN TIMELINE (addendum, review 2026-07-24). A short cast is NOT the primary re-timed --
each has an independently-authored length (the bench: primary ~23.0s/260 frames, short ~9.3s/110 frames).
``short_staging`` (a ``[summon.short_staging]`` curve table, REQUIRED whenever ``short_sequence`` is set)
is therefore a SEPARATE table from the primary's ``staging``/``[summon.staging]`` -- never copied, never
defaulted from it. Only the ASSETS are shared verbatim: the model (`spec["name"]`, referenced by both
manifests) and any authored ``.anim`` clips (one shared ``Animations/{id}/`` location, keyed by the model
id, which is identical for both casts). Particles ARE duplicated into the short's own folder (self-
containment: the short folder must not depend on the primary folder still existing) via
:func:`_stage_particles`'s new ``ef_id`` parameter.
"""

#: the SHORT/FULL roll's Command-feature body template (`{cond}` = the Condition formula, `{formula}` =
#: the IsShortSummon formula) -- see the module comment above for 3a (the `roll_mp` threshold) and 3b (why
#: `Global`, not `GlobalLast`). `EvenImmobilized` mirrors stock SA 59 Boost's own choice (DecideSummonType
#: itself has no immobilized guard either).
_SHORT_ROLL_BODY = "Command EvenImmobilized\n[code=Condition] {cond} [/code]\n[code=IsShortSummon] {formula} [/code]"


def short_summon_feature_block(spec: dict) -> "dict | None":
    """The ``[[ability_feature]]``-shaped dict (``battle/abilityfeatures.py``'s own schema) that emits the
    short/full roll as DATA. ``None`` when the block has no ``short_sequence`` (nothing to roll between).
    Registered under the ``Global`` special SA id (3b) with `cumulate=True` (`+`) so multiple ``[[summon]]``
    blocks -- each gated on their OWN `roll_command`/`roll_ability` pair -- coexist in one file without
    wiping each other (``ff9abil.cs:538``: a header WITHOUT `+` replaces the whole prior entry for that id).

    THE ABILITY-DISCRIMINATION LAW (review 2026-07-24, item 1): the Condition gates on BOTH `CommandId`
    AND `AbilityId` -- a minted command can host SEVERAL abilities (the rung-8 bench's command 46 hosts
    four: Voltflare, Soul Leech, Bahamut Cinema, Nimbra), and `CommandId` alone cannot tell them apart.
    Gating on `CommandId` only would roll `IsShortSummon` for every one of them, flipping the OTHER
    abilities' Vfx2 too (btl_vfx.cs:99) and biasing whatever else reads `IsShortSummon` in their own
    formulas (e.g. SA 60 Odin's Sword's HPDamage -- ``AbilityFeatures.txt:852`` -- takes a 2/3 cut when
    it's true). Both parameters are bound in the SAME Condition context TriggerOnCommand evaluates
    (`InitializeExpressionCommand`, `NCalcUtility.cs:631-632`, called from `CharacterAbilityGems.cs:774`)."""
    if not spec.get("short_sequence"):
        return None
    mp_cost, cmd_id, abil_id = spec["roll_mp"], spec["roll_command"], spec["roll_ability"]
    cond = f"IsTheCaster && CommandId == {cmd_id} && AbilityId == {abil_id}"
    formula = f"GetRandom() < (MP > {mp_cost} ? 230 : 170)"
    return {
        "kind": "SA", "ability": "Global", "cumulate": True,
        "features": _SHORT_ROLL_BODY.format(cond=cond, formula=formula),
        "comment": f"ff9mapkit summon short/full roll -- command {cmd_id} ability {abil_id}",
    }


def short_summon_feature_lines(spec: dict) -> list:
    """:func:`short_summon_feature_block` rendered through ``battle.abilityfeatures.build_lines`` (reuse,
    never re-derive the header/`[code=]` grammar) -- just THIS block's own lines (the file preamble +
    leading blank line ``build_lines`` prepends are stripped). Empty when there is nothing to roll."""
    blk = short_summon_feature_block(spec)
    if blk is None:
        return []
    from ..battle import abilityfeatures as _af
    try:
        lines, _warnings = _af.build_lines([blk], strict=False)
    except _af.AbilityFeatureError as e:
        raise SummonDeployError(f"[[summon]] short/full roll feature failed to build: {e}") from e
    return lines[2:]                      # drop [_FILE_HEADER, ""]; keep this block's own trailing ""


def render_short_summon_feature(spec: dict) -> str:
    """The exact text :func:`_stage_short_summon_feature` merges into ``AbilityFeatures.txt`` -- for the
    printed manifest / offline inspection. ``""`` when there is nothing to roll."""
    lines = short_summon_feature_lines(spec)
    return "\n".join(lines) + ("\n" if lines else "")


def _preflight_short_sequence(spec: dict) -> None:
    """Every short-lane check that is cheap to run BEFORE the first byte of a deploy is written -- mirrors
    :func:`_preflight_inputs`'s early-check law for the primary. No-op when there is no `short_sequence`.

      * the K5 silent-skip lint on `short_sequence` itself;
      * THE ANIMATION-PLAYLIST LAW against the short's OWN ``short_staging_curves`` window (review
        addendum: this must NEVER be checked against the primary's ``staging_curves`` -- the two windows
        are independent)."""
    short = spec.get("short_sequence")
    if not short:
        return
    src = Path(short)
    if not src.is_file():
        raise SummonDeployError(f"[[summon]] short_sequence file not found: {src}")
    text = src.read_text(encoding="utf-8-sig")
    problems = _seqlint().lint_seq(
        text, private_ef=spec["short_private_ef"],
        particles=[Path(p).name for p in (spec.get("particles") or [])], path=str(src))
    if problems:
        raise SummonDeployError(
            f"the short_sequence {src} does not lint -- refusing to deploy a cast the engine would "
            "silently drop pieces of:\n  " + "\n  ".join(problems))
    _check_playlist_coverage(spec, spec.get("short_staging_curves"), label="[[summon.short_staging.play]]")


def _stage_short_seq(spec: dict, mod_root: Path, ledger: _Ledger, *, full_text: str) -> dict:
    """The short cast's host ``ef{short_private_ef:D3}/PlayerSequence.seq`` -- ALWAYS an authored, verbatim
    BYTE copy (review FOLD-A: the earlier draft re-encoded the decoded text as UTF-8-LF-only, silently
    corrupting a CRLF-authored file; the decoded ``text`` below is used ONLY for lint/tick analysis, never
    for the write -- exactly :func:`_stage_host_seq`'s own authored branch). There is no donor-splice route
    for a short: the short's whole POINT is a hand-timed abbreviation, never derived from a stock file.
    Refuses a short LONGER than the full cast (a "short" that outruns the full one is backwards) by
    comparing each cast's :func:`seqlint.analyze_seq` fixed-``Wait`` tick floor -- the same measure the
    phase-lock/figure-visibility laws are built on."""
    src = Path(spec["short_sequence"])
    raw = src.read_bytes()
    text = raw.decode("utf-8-sig")                   # decode ONLY for lint/tick analysis, see above
    seq = _seqlint()
    problems = seq.lint_seq(
        text, private_ef=spec["short_private_ef"],
        particles=[Path(p).name for p in (spec.get("particles") or [])], path=str(src))
    if problems:                          # safety net (already run in _preflight_short_sequence)
        raise SummonDeployError(
            f"the short_sequence {src} does not lint -- refusing to deploy a cast the engine would "
            "silently drop pieces of:\n  " + "\n  ".join(problems))
    full_ticks = seq.analyze_seq(full_text).total_ticks
    short_ticks = seq.analyze_seq(text).total_ticks
    if short_ticks > full_ticks:
        raise SummonDeployError(
            f"[[summon]] short_sequence ({short_ticks} fixed-Wait ticks) is LONGER than the full cast "
            f"({full_ticks} ticks) -- a 'short' cinematic that outruns the full one is backwards. Trim "
            "short_sequence, or check `sequence` (the census puts real shorts in a ~3.8-12.5s band).")
    seq_dest = _sfx_dir(mod_root, spec["short_private_ef"]) / HOST_SEQ_NAME
    seq_sha = ledger.write_bytes(seq_dest, raw)
    return {"seq_dest": str(seq_dest), "seq_sha256": seq_sha, "seq_source": str(src),
            "full_ticks": full_ticks, "short_ticks": short_ticks}


def _stage_short_overlay_folder(spec: dict, mod_root: Path, ledger: _Ledger) -> dict:
    """MUST-FIX 1 (review 2026-07-24): complete the short private ef folder to the SAME self-contained
    shape the primary's overlay staging gets -- ``FileList.txt`` + a ``.sfxmodel`` manifest + verbatim
    particle copies -- so the short cast's own ``LoadSFX: SFX=<short_private_ef>`` self-load (K1's shape,
    the ONLY route that can render an FBX creature with no live donor skeleton -- see THE HYBRID-LANE
    SHORT MECHANISM above :func:`short_summon_feature_block`) actually finds a Model line. Runs
    regardless of the block's own ``lane`` (hybrid or overlay) -- the short is always this shape.

    The manifest is built from ``short_staging_curves`` (never ``staging_curves`` -- the addendum: each
    cast renders from its OWN timeline). ``clip_names`` is passed empty because ``short_staging_curves``
    is REQUIRED whenever this runs (:func:`normalize_spec`), so :func:`_sfxmodel_manifest`'s curves branch
    is always taken -- the world-origin-stub fallback that reads ``clip_names`` is unreachable here; any
    shared clip a ``[[summon.short_staging.play]]`` entry names is still resolved via
    ``Animations/{id}/`` -- the SAME shared, model-id-keyed location the primary's own playlist reads (no
    duplication: :func:`_stage_particles`/authored-clip staging already wrote it once).

    ``manifest_name`` -- ``spec["short_manifest"]`` (review 2026-07-24, item 2), the short folder's OWN
    bare file name -- defaults to ``spec["manifest"]`` in :func:`normalize_spec`, but a pair block may
    give the two folders DISTINCT names (the bench: the short keeps the deployed ``nimbra_manifest
    .sfxmodel``, the full renames to ``nimbra_full_manifest.sfxmodel``)."""
    particles = _stage_particles(spec, mod_root, ledger, ef_id=spec["short_private_ef"])
    return _write_manifest(spec, mod_root, ledger, [], particles=particles,
                           ef_id=spec["short_private_ef"], staging_curves=spec["short_staging_curves"],
                           manifest_name=spec["short_manifest"])


def _decode_cp1252_strict(data: bytes, path) -> str:
    """cp1252 STRICT decode, failing LOUD (review FOLD-C). windows-1252 leaves 5 byte values undefined
    (0x81, 0x8D, 0x8F, 0x90, 0x9D) and Python's codec raises on them; the file's charset is invariant
    (``AbilityFeatures.txt`` is documented cp1252 kit-wide, ``battle/abilityfeatures.py``'s own docstring),
    so an undecodable byte means something ELSE already wrote non-cp1252 content into this file --
    ``errors="replace"`` would silently turn it into U+FFFD (re-encoded as ``?``), corrupting that other
    writer's bytes with no warning. Refuse clearly instead."""
    try:
        return data.decode("cp1252")
    except UnicodeDecodeError as e:
        raise SummonDeployError(
            f"{path} is not valid cp1252 ({e}) -- refusing to merge into it. A silent 'replace' decode "
            "would corrupt whatever produced that byte (a foreign encoding, a stray control byte) with no "
            "warning; fix the file's encoding first.") from e


def _modfilelist_warning(mod_root, rel_path: str) -> "str | None":
    """G (review FOLD-G): if the mod folder ships a ``ModFileList.txt``, a newly staged file is INVISIBLE
    to the engine unless it is also LISTED there (``AssetManager.cs:948-976`` resolves an asset only
    against the entries that manifest names). A WARNING, not a hard refusal -- this deploy engine does not
    own that file's format or the decision to auto-append to it; plenty of mod folders have none at all
    (an unlisted file just loads straight off disk in that case)."""
    mfl = Path(mod_root) / "ModFileList.txt"
    if not mfl.is_file():
        return None
    return (f"{mfl} exists -- a mod folder shipping ModFileList.txt only exposes LISTED assets "
            f"(AssetManager.cs:948-976); add {rel_path!r} to it or the engine will not see this file")


def _stage_short_summon_feature(spec: dict, mod_root: Path, ledger: _Ledger) -> dict:
    """Merge the roll (:func:`short_summon_feature_lines`) into this mod folder's ``AbilityFeatures.txt``,
    non-destructively (``battle.abilityfeatures.merge_ability_features``'s ``##`` marker splice -- keyed on
    this block's own mint `id`, so redeploying one ``[[summon]]`` block never disturbs another's roll or
    any hand-authored ``[[ability_feature]]`` content already in the file -- see MUST-FIX 3: the field-build
    writer, ``battle.abilityfeatures.write_ability_features``, is now ALSO marker-aware for the same reason,
    so whichever of the two runs SECOND updates only its OWN section). ``{}`` when there is nothing to
    roll. The file is seeded with the shared file header on a FRESH file (so either writer's first touch
    produces the same bytes, order-independent) and decoded STRICT (FOLD-C)."""
    lines = short_summon_feature_lines(spec)
    if not lines:
        return {}
    from ..battle import abilityfeatures as _af
    path = (Path(mod_root) / "StreamingAssets" / "Data" / "Characters" / "Abilities" / "AbilityFeatures.txt")
    live = _decode_cp1252_strict(path.read_bytes(), path) if path.is_file() else (_af._FILE_HEADER + "\n")
    merged = _af.merge_ability_features(live, lines, f"summon-short-roll-{spec['id']}")
    ledger.write_bytes(path, merged.encode("cp1252"))
    result = {"ability_features_path": str(path)}
    warn = _modfilelist_warning(mod_root, "StreamingAssets/Data/Characters/Abilities/AbilityFeatures.txt")
    if warn:
        result["warning"] = warn
    return result


# --------------------------------------------------------------------------- overlay extras (rows 4/5/6)

def _sfxmodel_manifest(spec: dict, clip_names: list, *, staging_curves: "dict | None | bool" = False) -> dict:
    """The ``.sfxmodel`` JSON manifest (overlay lane, DESIGN row 5): one FBX entry naming the bare minted
    GEO name (Hop 4/5 discards the ef folder), plus the ``Animations[]`` playlist.

    ``staging = "donor"`` (the default) emits sane world-origin Movement/Rotation/Scaling anchors so a
    mis-wired overlay degrades to "visible but static" rather than "invisible at the origin"
    (FBX-PATHS section 4), and chains each decoded clip once.

    A ``[summon.staging]`` curve table (``staging = "curves"``, K4) REPLACES all of that with the authored
    Start/End + the three curves + the authored playlist -- see :func:`staging_curves_json`.

    ``staging_curves`` -- explicit override for the SHORT cast's own ``short_staging_curves`` (the
    sentinel default ``False``, not ``None``, distinguishes "not passed -> use `spec['staging_curves']`"
    from "passed explicitly as `None` -> this manifest has NO curves table at all", which the short lane
    never does since `short_staging_curves` is a required field once `short_sequence` is set, but a caller
    passing the primary's `spec.get('staging_curves')` verbatim -- which CAN legitimately be ``None`` --
    must not be silently redirected back to `spec['staging_curves']`)."""
    st = spec.get("staging_curves") if staging_curves is False else staging_curves
    if st is not None:
        fbx = {"Path": spec["name"]}
        fbx.update(staging_curves_json(spec, st))
        return {"FBX": [fbx]}
    fbx = {"Path": spec["name"], "Start": "0", "End": "0",
           "Movement": [{"Duration": "0", "OriginX": "0", "OriginY": "0", "OriginZ": "0",
                         "DestinationX": "0", "DestinationY": "0", "DestinationZ": "0"}],
           "Rotation": [{"Duration": "0", "OriginY": "0", "DestinationY": "0",
                         "OriginZ": "0", "DestinationZ": "0"}],
           "Scaling": {"Duration": "0", "OriginX": "1", "OriginY": "1", "OriginZ": "1",
                       "DestinationX": "1", "DestinationY": "1", "DestinationZ": "1"}}
    if clip_names:
        fbx["Animations"] = [{"Path": f"Animations/{spec['id']}/{c}"} for c in clip_names]
    return {"FBX": [fbx]}


def _seqlint():
    """Lazy handle to the ``.seq``/``.sfxmodel`` linter (K5) -- only an authored cast pays for it."""
    from . import seqlint
    return seqlint


def _lint_authored_sequence(spec: dict, src: Path) -> list:
    """The authored ``.seq``'s silent-skip lint (K5), as a plain problem list (no I/O side effects beyond
    the read). Shared by :func:`_preflight_inputs` (a cheap, no-writes-yet check) and
    :func:`_stage_host_seq` (the actual write site -- kept as a safety net for any caller that reaches it
    without going through preflight, e.g. a test that calls it directly)."""
    text = src.read_text(encoding="utf-8-sig")
    return _seqlint().lint_seq(
        text, private_ef=spec["private_ef"],
        particles=[Path(p).name for p in (spec.get("particles") or [])], path=str(src))


def _check_playlist_coverage(spec: dict, staging_curves: "dict | None | bool" = False,
                             label: str = "[[summon.staging.play]]") -> None:
    """THE ANIMATION-PLAYLIST LAW as a raising check (a thin wrapper over :func:`playlist_coverage`, which
    is a pure read -- no writes). Shared by :func:`_preflight_inputs` (early, before the first byte of the
    mint is written) and :func:`_stage_overlay_extras_authored` (the actual write site -- kept as a safety
    net). ``None``/``short_by == 0`` from :func:`playlist_coverage` means nothing to check -- returns.

    ``staging_curves``/``label`` -- forwarded to :func:`playlist_coverage` + used in the error text so the
    SHORT cast's own check (``short_staging_curves`` / ``[[summon.short_staging.play]]``) names ITSELF,
    not the primary, when it fires."""
    coverage = playlist_coverage(spec, staging_curves)
    if coverage and coverage["short_by"] > 0:
        raise SummonDeployError(
            f"THE ANIMATION-PLAYLIST LAW: the {label} playlist covers "
            f"{coverage['playlist_ticks']} ticks but the FBX window (end - start) is {coverage['window']} "
            f"-- short by {coverage['short_by']}. SFXDataMesh.cs:860-863 has no loop flag: once the "
            f"playlist runs out the model FREEZES on the last clip's last frame for the remaining "
            f"{coverage['short_by']} ticks. Add a `repeat` (or shorten `end`).\n"
            f"  per clip (frames / speed = ticks): " + ", ".join(coverage["detail"]))


def _preflight_inputs(spec: dict) -> None:
    """Every caller-supplied input file must EXIST before the first byte is written -- AND, for the two
    checks that are cheap to run this early (pure reads, no derived manifest/clip-key state needed), must
    also pass the checks the engine would otherwise fail at SILENTLY:

      * the authored ``sequence=``'s silent-skip lint (K5, :func:`_lint_authored_sequence`);
      * THE ANIMATION-PLAYLIST LAW's coverage check (:func:`_check_playlist_coverage`).

    Without this an emit that dies half-way (a particle path typo, a lint failure, a short playlist)
    leaves the mint + the host ``.seq`` already in the mod folder and no revert script -- the ledger only
    renders one at the end. Both checks are pure reads against caller-supplied files already confirmed to
    exist above, so folding them in costs nothing extra in I/O and moves their failure point BEFORE
    :func:`_stage_model`'s first write (previously: the seq lint fired inside :func:`_stage_host_seq`,
    which runs after the mint is already on disc; the playlist check fired inside
    :func:`_stage_overlay_extras_authored`, after the mint AND the host ``.seq`` are already on disc).

    NOT folded in, and this is deliberate rather than an oversight: the ``.sfxmodel`` manifest lint
    (:func:`_write_manifest`) and the particle-file lint (:func:`_stage_particles`). Both need state this
    function has no cheap way to derive twice -- the manifest lint needs the ACTUAL clip-key list
    :func:`_stage_authored_clips`/:func:`_decode_donor_clips` compute while writing, and the particle
    lint is already itself the very first thing each particle file's write site does. Duplicating either
    here would mean re-deriving (not just re-reading) real staged state before the real staging runs, which
    is not "trivially callable" the way the seq lint and the playlist check are -- so they stay at their
    existing write sites, and this docstring is the honest record of the check order."""
    missing = []
    for label, raw in [("model", spec.get("model")), ("sequence", spec.get("sequence"))]:
        if raw and not Path(raw).is_file():
            missing.append(f"[[summon]] {label} file not found: {raw}")
    for label, seq in [("particle .sfxmodel", spec.get("particles")),
                       ("clip", authored_clip_paths(spec.get("clips")))]:
        for raw in (seq or []):
            if not Path(raw).is_file():
                missing.append(f"[[summon]] {label} not found: {raw}")
    if missing:
        raise SummonDeployError("\n".join(missing))

    sequence = spec.get("sequence")
    if sequence:
        problems = _lint_authored_sequence(spec, Path(sequence))
        if problems:
            raise SummonDeployError(
                f"the authored sequence {sequence} does not lint -- refusing to deploy a cast the engine "
                "would silently drop pieces of:\n  " + "\n  ".join(problems))
    _check_playlist_coverage(spec)


def _stage_particles(spec: dict, mod_root: Path, ledger: _Ledger, *, ef_id: "int | None" = None) -> list:
    """K3: the authored sprite ``.sfxmodel`` particle files, copied VERBATIM into the private
    ``ef{private_ef:D3}/`` folder beside the manifest.

    They live in the ef folder because that is where ``CreateVisualEffect``'s full ``Data/``-rooted
    ``SFXModel=`` path points, and because a ``.sfxmodel``'s own texture references resolve relative to its
    OWN folder (``SFXDataMesh.cs:1064-1068``). Each is linted first -- a ``.sfxmodel`` that does not parse
    makes ``ModelSequence.Load`` return null and the op ``break`` with no message at all
    (``UnifiedBattleSequencer.cs:406-408``).

    ``ef_id`` -- which private ef folder to copy into (default ``spec["private_ef"]``); the SHORT folder
    (MUST-FIX 1) passes its own ``short_private_ef`` so it carries its OWN verbatim copies -- a
    self-contained folder that does not depend on the primary's still existing."""
    ef_id = spec["private_ef"] if ef_id is None else ef_id
    out = []
    for raw in (spec.get("particles") or []):
        src = Path(raw)
        if not src.is_file():
            raise SummonDeployError(f"[[summon]] particle .sfxmodel not found: {src}")
        problems = _seqlint().lint_sfxmodel_file(src)
        if problems:
            raise SummonDeployError(
                "a particle .sfxmodel does not lint -- refusing to deploy an effect the engine would drop "
                "silently:\n  " + "\n  ".join(problems))
        dest = _sfx_dir(mod_root, ef_id) / src.name
        ledger.write_bytes(dest, src.read_bytes())
        out.append(str(dest))
    return out


def _stage_authored_clips(spec: dict, mod_root: Path, ledger: _Ledger) -> list:
    """K2: AUTHORED ``.anim`` clips (the ``models/anim.py:new_clip`` -> ``clip_to_anim_json`` output),
    copied verbatim to ``anim_disc_path(mod_root, id, key)``.

    NO ``3DModelAnimation`` DictionaryPatch line is written, exactly as on the donor-decode path: the SFX
    route resolves a clip by LITERAL PATH through ``AssetManager.Load<AnimationClip>``
    (``SFXDataMesh.cs:793``), not through the animation table -- so authored clips are RECAST-only, and
    only a new ``3DModel`` mint id needs the relaunch.

    The on-disc key is :func:`clip_key_of` (the mint band, positional), and the manifest's playlist maps a
    human ``play.clip = "emerge"`` name onto it via :func:`clip_name_map` -- so the TOML stays readable
    while the file name stays a key the engine is happy to treat as a clip NAME."""
    paths = authored_clip_paths(spec.get("clips")) or []
    out = []
    for i, raw in enumerate(paths):
        src = Path(raw)
        if not src.is_file():
            raise SummonDeployError(f"[[summon]] clip file not found: {src}")
        key = clip_key_of(i, src)
        dest = _anim.anim_disc_path(mod_root, spec["id"], key)
        ledger.write_bytes(dest, src.read_bytes())
        out.append({"name": src.stem, "key": key, "dest": str(dest), "source": str(src)})
    return out


def _decode_donor_clips(spec: dict, game) -> list:
    """Decode the donor creature's motion clips offline for the overlay ``.anim`` set (DESIGN 3.3), reusing
    the proven ``summons.build.adapt_all_clips`` decoder. Reads a LOCAL ``ef{donor}.bytes`` under
    ``C:/gd/SCRATCH/summon-transplant/`` (stock-derived -- never committed). Honors ``spec['clips']``
    ('all'|'none'|index list). Returns ``[(clip_name, clip_dict), ...]`` in file order."""
    clips_sel = spec.get("clips", "all")
    if clips_sel in (None, "none", "off", []):
        return []
    if spec.get("donor") is None:
        raise SummonDeployError(
            "[[summon]] has no `donor` -- an authored (`sequence=`) block with no donor cannot decode "
            "donor clips (there is no ef###.bytes to read them from). Pass `clips=[<authored .anim "
            'paths>]` (K2) or `clips="none"`, or add a `donor`.')
    from . import build as _sbuild
    from . import container as _container
    src = _local_ef_bytes(spec["donor"])
    if not src.is_file():
        raise SummonDeployError(
            f"overlay lane needs the donor's decoded clips: {src} not found. Extract ef{spec['donor']:03d}"
            ".bytes from your install into C:/gd/SCRATCH/summon-transplant/ first, or use lane='hybrid' "
            "(the drive supplies motion from the live donor bones -- no clips).")
    blob = src.read_bytes()
    mp = _container.creature_package(blob)
    if mp is None:
        raise SummonDeployError(f"{src} carries no creature package -- not a summon-creature effect")
    g = _container.creature_geom(blob, mp)
    decoded = _sbuild.adapt_all_clips(blob, mp, g.bone_count)
    if clips_sel in ("all", "auto", "", "default"):
        idxs = list(range(len(decoded)))
    else:
        idxs = []
        for tok in str(clips_sel).replace(",", " ").split():
            if not tok.isdigit() or not (0 <= int(tok) < len(decoded)):
                raise SummonDeployError(f"[[summon]] clips index {tok!r} out of range 0..{len(decoded)-1}")
            idxs.append(int(tok))
    return [(decoded[i]["name"], decoded[i]) for i in idxs]


def _local_ef_bytes(donor: int) -> Path:
    """Where a caller-extracted ``ef{donor:D3}.bytes`` lives for the offline clip decode (SCRATCH-only)."""
    from .export import DEFAULT_OUT_DIR
    return DEFAULT_OUT_DIR / f"ef{int(donor):03d}.bytes"


def _clip_bone_paths(clip: dict, parent_of: dict) -> dict:
    """Re-key ``clip['bones']`` from bone NUMBER (``bone000``) to the nested hierarchy PATH
    (``bone000/bone001/...``) ``clip_to_anim_json`` writes as the ``SetCurve`` relativePath (DESIGN 3.3,
    detail 1). ``parent_of`` maps ``boneNNN -> parentNNN|None``."""
    def path_of(name):
        # cycle-safe (belt-and-suspenders): stop if a parent repeats, so a malformed parent_of can never
        # loop forever (the root itself is parent_of[root] is None -- see _stage_overlay_extras).
        chain, seen = [name], {name}
        p = parent_of.get(name)
        while p is not None and p not in seen:
            chain.append(p)
            seen.add(p)
            p = parent_of.get(p)
        return "/".join(reversed(chain))
    return {"name": clip.get("name"), "sample_rate": clip.get("sample_rate"),
            "length": clip.get("length"),
            "bones": {path_of(bn): ch for bn, ch in clip.get("bones", {}).items()}}


def _stage_overlay_extras(spec: dict, mod_root: Path, game, ledger: _Ledger) -> dict:
    """Rows 4/5/6 (overlay lane): the ``.anim`` clips (via ``models/anim.py:clip_to_anim_json`` at
    ``anim_disc_path`` -- NO ``3DModelAnimation`` line), the ``.sfxmodel`` manifest, and the one-line
    ``FileList.txt`` -- all under the PRIVATE ``ef{private_ef}/`` folder (never the donor's). Plus, on the
    rung-8 authored path, the sprite particle ``.sfxmodel`` files (K3)."""
    from . import container as _container
    authored = authored_clip_paths(spec.get("clips"))
    if authored is not None:
        return _stage_overlay_extras_authored(spec, mod_root, ledger)
    # decode + write the clips
    clips = _decode_donor_clips(spec, game)
    # bone-number -> parent map from the donor rig (for the hierarchy-path re-key)
    parent_of = {}
    if clips:
        # `_decode_donor_clips` already refused a None `donor` before returning anything non-empty, so
        # `spec["donor"]` is safe to read here (deferred past the empty-clips/"none" case, which never
        # needs a donor at all -- see Finding 8: a donor-less authored block with `clips="none"` must not
        # crash trying to resolve a donor it was never given).
        src = _local_ef_bytes(spec["donor"])
        blob = src.read_bytes()
        mp = _container.creature_package(blob)
        g = _container.creature_geom(blob, mp)
        parents = g.parents()
        # The root is bone INDEX 0, NOT a negative parent: container.Geom.parents() reports the root's
        # own parent as 0 (a self-reference, "parents[0] is the implicit root, reported as 0") -- so the
        # proven summons/build.py:adapt_model keys the root off ``k == 0``. Using ``parents[k] < 0`` here
        # instead made parent_of['bone000'] = 'bone000', a self-cycle that hung _clip_bone_paths forever.
        parent_of = {f"bone{k:03d}": (None if k == 0 else f"bone{parents[k]:03d}")
                     for k in range(g.bone_count)}
    clip_names = []
    for name, clip in clips:
        anim_json = _anim.clip_to_anim_json(_clip_bone_paths(clip, parent_of))
        dest = _anim.anim_disc_path(mod_root, spec["id"], _anim_key_of(name))
        ledger.write_bytes(dest, anim_json.encode("utf-8"))
        clip_names.append(_anim_key_of(name))

    return _write_manifest(spec, mod_root, ledger, clip_names, particles=[])


def _stage_overlay_extras_authored(spec: dict, mod_root: Path, ledger: _Ledger) -> dict:
    """The rung-8 authored variant of :func:`_stage_overlay_extras`: no donor container is opened at all
    (K2's clips are files the caller wrote), the sprite particles ride along (K3), and the manifest picks
    up the ``[summon.staging]`` curves when they are present (K4)."""
    _check_playlist_coverage(spec)                     # already run in _preflight_inputs; kept as a
    coverage = playlist_coverage(spec)                  # safety net for a caller that skips preflight
    clips = _stage_authored_clips(spec, mod_root, ledger)
    particles = _stage_particles(spec, mod_root, ledger)
    res = _write_manifest(spec, mod_root, ledger, [c["key"] for c in clips], particles=particles)
    res["clip_files"] = clips
    if coverage:
        res["playlist_coverage"] = coverage
    return res


def anim_frame_count(path) -> "int | None":
    """Frames in an authored ``.anim`` JSON clip -- what ``GeoAnim.geoAnimGetNumFrames`` will report.

    Derived, not read: the ``.anim`` JSON carries per-key TIMES in seconds plus a ``frameRate``
    (``models/anim.py:clip_to_anim_json``), so frames = ``round(maxTime * frameRate) + 1``. Returns
    ``None`` for a file this shape does not fit (binary clips, a donor decode) -- the caller then skips
    the coverage check rather than guessing."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    if not isinstance(doc, dict) or "transform" not in doc:
        return None
    rate = float(doc.get("frameRate") or 30.0)
    tmax = 0.0
    for bone in doc.get("transform") or []:
        for chan in ("localRotation", "localPosition", "localScale"):
            for k in bone.get(chan) or []:
                tmax = max(tmax, float(k.get("time", 0.0)))
    return int(round(tmax * rate)) + 1


def playlist_coverage(spec: dict, staging_curves: "dict | None | bool" = False) -> "dict | None":
    """Does the authored ``[[summon.staging.play]]`` playlist cover the whole ``end - start`` window?

    ``staging_curves`` -- explicit override, checked against ITS OWN window (the SHORT cast passes its
    own ``short_staging_curves`` here -- its playlist must cover ITS OWN ``end - start``, never the
    primary's; sentinel default ``False`` means "use ``spec['staging_curves']``", distinct from an
    explicit ``None``).

    One playlist entry occupies ``ceil(frames / speed)`` SEQUENCE TICKS (``animMaxFrame``,
    ``SFXDataMesh.cs:852``) -- which is also why a 30 fps clip runs at half speed with ``speed = 1`` at
    ``BattleTPS = 15``. ``None`` when there is nothing to check (no curves, no playlist, or a clip whose
    frame count could not be derived).

    THE SPEED-DIVISOR DEFECT -- why the returned ``nonunit_speeds`` matters
    ----------------------------------------------------------------------
    ``speed`` sets how many TICKS an entry occupies, and it is honest about that. It does NOT slow the
    clip down. ``animFrame = floor(ticks * speed)`` (``:858``) is a CLIP-FRAME index while
    ``animMaxFrame`` is a TICK count, and ``SFXDataMesh.cs:869`` divides one by the other::

        clipState.time = clipState.length * animFrame / animMaxFrame[animIndex];

    The two are equal only at ``speed == 1``. (``:863``'s exhausted branch sets
    ``animFrame = animMaxFrame`` so that line yields ``time = length`` -- proof the divisor was meant to
    be ``animFrame``'s end-of-clip value, i.e. ~``numFrames``.) So at ``speed = s`` a clip advances
    ``s**2`` frames per tick: it finishes after ``1/s`` of its entry and the rig FREEZES for the rest.

    **Author every entry at ``speed = 1`` and size the CLIP to the beat.** ``speed = 1`` is the only
    self-consistent value and the one value at which both readings of ``:869`` agree. ``nonunit_speeds``
    lists ``(clip, speed)`` for every entry that is not 1 so callers can warn; this is reported, never
    raised, because ``speed`` remains a legal knob and existing content may rely on the tick footprint.
    Diagnosed on rung 8 -- ``studies/custom-summons/rung8-epic/`` STORYBOARD 11.9 + ``playlist_sim.py``.
    """
    st = spec.get("staging_curves") if staging_curves is False else staging_curves
    paths = authored_clip_paths(spec.get("clips"))
    if not st or not st.get("play") or not paths:
        return None
    frames = {}
    for i, p in enumerate(paths):
        n = anim_frame_count(p)
        if n is None:
            return None
        frames[Path(p).stem] = frames[str(clip_key_of(i, p))] = n
    window = _as_int(st.get("end", 0), "end") - _as_int(st.get("start", 0), "start")
    total, detail, nonunit = 0, [], []
    for p in st["play"]:
        name = str(p["clip"])
        speed = float(p.get("speed", 1))
        repeat = int(p.get("repeat", 1))
        n = frames.get(name)
        if n is None:
            return None
        ticks = int(math.ceil(n / speed)) * repeat
        total += ticks
        if speed != 1:                              # THE SPEED-DIVISOR DEFECT -- see the docstring
            nonunit.append((name, speed))
        detail.append(f"{name} {n}/{_num(speed)}"
                      + (f" x{repeat}" if repeat > 1 else "") + f" = {ticks}")
    return {"window": window, "playlist_ticks": total, "short_by": max(0, window - total),
            "detail": detail, "nonunit_speeds": nonunit}


def _write_manifest(spec: dict, mod_root: Path, ledger: _Ledger, clip_names: list, *,
                    particles: list, ef_id: "int | None" = None,
                    staging_curves: "dict | None | bool" = False,
                    manifest_name: "str | None" = None) -> dict:
    """Row 5 + 6: the ``.sfxmodel`` manifest and the one-line ``FileList.txt`` that reveals it.

    THE FILELIST GRAMMAR: tokens split on a SINGLE space (``SFXData.cs:253-254``) -- a tab or a double
    space breaks the line silently -- and the manifest name must stay bare so ``UsePathWithDefaultFolder``
    resolves it inside this same ef folder.

    ``ef_id`` -- which private ef folder to write into (default ``spec["private_ef"]``, the primary); the
    SHORT folder passes its own ``short_private_ef``. ``staging_curves`` -- forwarded to
    :func:`_sfxmodel_manifest` (the SHORT folder passes its own ``short_staging_curves`` so its manifest
    is built from its OWN timeline, never the primary's). ``manifest_name`` -- which BARE file name to
    write the manifest (and the ``FileList.txt`` ``Model`` line) as; default ``spec["manifest"]`` (the
    primary's). The SHORT folder passes its own ``short_manifest`` (review 2026-07-24, item 2) so a pair
    block can give the two folders DISTINCT manifest file names -- both are still bare-name-validated by
    :func:`normalize_spec` the same way ``manifest`` itself is."""
    ef_id = spec["private_ef"] if ef_id is None else ef_id
    manifest_name = manifest_name if manifest_name is not None else (spec.get("manifest") or DEFAULT_MANIFEST_NAME)
    manifest = _sfxmodel_manifest(spec, clip_names, staging_curves=staging_curves)
    body = json.dumps(manifest, indent=2) + "\n"
    problems = _seqlint().lint_sfxmodel_text(body, path=manifest_name)
    if problems:
        raise SummonDeployError(
            "the emitted .sfxmodel manifest does not lint (a kit bug or a bad [summon.staging]):\n  "
            + "\n  ".join(problems))
    man_dest = _sfx_dir(mod_root, ef_id) / manifest_name
    ledger.write_bytes(man_dest, body.encode("utf-8"))

    fl_dest = _sfx_dir(mod_root, ef_id) / "FileList.txt"
    ledger.write_bytes(fl_dest, f"Model {manifest_name}\n".encode("utf-8"))
    return {"manifest_dest": str(man_dest), "filelist_dest": str(fl_dest), "clips": clip_names,
            "particles": particles, "manifest_name": manifest_name}


def _anim_key_of(clip_name: str):
    """A clip's ``.anim`` file stem. ``anim_disc_path`` names files ``{key}.anim`` where key is numeric;
    a summon clip's own name is ``clip{i}`` -> use ``i`` so the ``.sfxmodel`` ``Animations[].Path`` and the
    on-disc file agree (both ``Animations/{id}/{i}``)."""
    m = re.search(r"(\d+)$", str(clip_name))
    return int(m.group(1)) if m else 0


# --------------------------------------------------------------------------- the [SfxHybrid] arm step

def probe_hybrid_engine(game) -> bool:
    """String-probe the deployed ``Assembly-CSharp.dll`` (x64, then x86) for the s58
    :data:`_SFXHYBRID_ENGINE_MARK` -- True only if the running engine carries ``SfxHybridDrive`` (DESIGN
    section 2.4, the engine-independence split made executable). A missing DLL -> False."""
    game = Path(game)
    for arch in ("x64", "x86"):
        dll = game / arch / "FF9_Data" / "Managed" / "Assembly-CSharp.dll"
        if dll.is_file() and _SFXHYBRID_ENGINE_MARK in dll.read_bytes():
            return True
    return False


def sfxhybrid_updates(spec: dict, *, log: bool = False) -> dict:
    """The ``[SfxHybrid]`` key/value dict for a spec (maps the hybrid knobs 1:1; DESIGN section 2.3/2.4).
    Insertion order matches the acceptance block (RUNBOOK section 5)."""
    return {
        "Enabled": "1",
        "EffectId": str(spec["donor"]),
        "ModelPath": spec["name"],
        "HideNative": "1" if spec["hide_native"] else "0",
        "HideMask": spec["hide_mask"],
        "NodeCount": str(spec["node_count"]),
        "ApplyColumnScale": "1" if spec["apply_column_scale"] else "0",
        "Log": "1" if log else "0",
    }


def render_sfxhybrid_block(spec: dict, *, log: bool = False) -> str:
    """The exact ``[SfxHybrid]`` INI text a deploy would write, for the printed ARM manifest (staged, not
    written -- confirm-first, DESIGN section 2.4)."""
    lines = [f"[{SFXHYBRID_SECTION}]"]
    lines += [f"{k} = {v}" for k, v in sfxhybrid_updates(spec, log=log).items()]
    return "\n".join(lines) + "\n"


def arm_sfxhybrid(game, spec: dict, *, log: bool = False, out=print,
                  ledger: "_Ledger | None" = None) -> Path:
    """Row 3: ARM ``Memoria.ini [SfxHybrid]`` -- the coop ``[Netsync]`` precedent EXACTLY (DESIGN section
    2.4). Refuses (a) a stock engine (:func:`probe_hybrid_engine`) and (b) a missing ini; backs the ini up
    first (``coop._backup_ini``), rewrites the section (``coop.update_ini_section``, every pair vetted by
    ``coop._check_ini_pair``), warns on duplicate keys, and prints the applied block. Returns the backup
    path. This MUTATES the user's live ``Memoria.ini`` -- it is the explicit ``summon-deploy`` arm step,
    never a silent build side effect.

    If ``ledger`` is given, the ini path + this arm's OWN backup are recorded into it
    (:meth:`_Ledger.record_ini`) -- the caller MUST do this BEFORE :meth:`_Ledger.write_revert_script` runs
    (see :func:`emit_hybrid`), or the emitted revert script never learns the ini needs undoing at all."""
    from .. import coop as _coop
    game = Path(game)
    if not probe_hybrid_engine(game):
        raise SummonDeployError(
            "the hybrid lane requires the s58 SfxHybridDrive engine, but the deployed Assembly-CSharp.dll "
            "has no 'SfxHybridDrive' string (stock Memoria). Deploy the custom Dream World IX engine "
            'bundle, or use lane = "overlay" (DLL-free).')
    ini = game / "Memoria.ini"
    if not ini.is_file():
        raise SummonDeployError(f"{ini} not found -- is this the FF9 install (and is Memoria set up)?")
    updates = sfxhybrid_updates(spec, log=log)
    text = ini.read_text(encoding="utf-8", errors="replace")
    new_text = _coop.update_ini_section(text, SFXHYBRID_SECTION, updates)   # vets every pair (raises pre-backup)
    dupes = _coop.duplicate_ini_keys(text, SFXHYBRID_SECTION)
    if dupes:
        out(f"  ! [{SFXHYBRID_SECTION}] had duplicate keys {dupes} -- rewritten to a single copy each")
    backup = _coop._backup_ini(ini)
    fsutil.atomic_write_text(ini, new_text, encoding="utf-8")
    if ledger is not None:
        ledger.record_ini(ini, backup)
    out(f"  Memoria.ini: [{SFXHYBRID_SECTION}] armed (backup: {backup.name})")
    for k, v in updates.items():
        out(f"      {k} = {v}")
    out("  RELAUNCH FF9 to apply (the section is read once at process start).")
    return backup


def _print_short_receipt(spec: dict, short: dict, *, out=print) -> None:
    """FOLD-D (review 2026-07-24): the deploy receipt was silent about the short half entirely -- print
    its host ``.seq`` destination, the RESOLVED ``short_private_ef`` (the lint note in
    ``content/summon.py`` already promises this number), and a `vfx2` wiring reminder, plus any
    ``ModFileList.txt`` visibility warning (FOLD-G)."""
    out(f"  short cast: ef{spec['short_private_ef']:03d}/PlayerSequence.seq ({short['short_ticks']} "
        f"ticks vs full's {short['full_ticks']})")
    out(f"      -> {short['seq_dest']}")
    out(f"  point that SAME ability's `vfx2` at short_private_ef={spec['short_private_ef']} to fire it")
    warn = (short.get("ability_features") or {}).get("warning")
    if warn:
        out(f"  ! {warn}")


# --------------------------------------------------------------------------- the lane emitters

def emit_hybrid(spec: dict, mod_root, game, *, work_dir=None, arm: bool = False, out=print) -> dict:
    """The HYBRID lane deploy (DESIGN rows 1, 1b, 2 + a staged ARM manifest). Emits the mint + the host
    ``.seq``; STAGES the ``[SfxHybrid]`` text (does NOT write the ini unless ``arm=True``). Writes a revert
    script LAST. Returns a manifest dict (+ ``armed``, and ``ini_backup`` when armed).

    ``arm=True`` performs the confirm-first :func:`arm_sfxhybrid` step BEFORE the revert script is
    rendered, so the ini backup it creates is recorded into the SAME ledger the revert script reads --
    without this ordering the revert script would drop newly-minted files but leave a live, un-undone
    ``[SfxHybrid]`` arm in the user's ``Memoria.ini`` (the ledger's ``ini_path`` would stay ``None`` and
    the revert template's ini-restore/neutralize branch would never run).

    ``spec`` may be a raw ``[[summon]]`` block OR an already-:func:`normalize_spec`-ed spec (normalize is
    idempotent), so ``content/summon.py`` can call this with either (it never passes ``arm``)."""
    spec = _resolve_ids(normalize_spec(spec), mod_root, game)
    _preflight_short_sequence(spec)
    ledger = _Ledger(_backup_root(mod_root, work_dir))
    mint = _stage_model(spec, mod_root, ledger)
    seq = _stage_host_seq(spec, mod_root, game, ledger, overlay=False)
    short = None
    if spec.get("short_sequence"):
        # THE HYBRID-LANE SHORT MECHANISM (module comment above short_summon_feature_block): the short is
        # ALWAYS the authored/overlay shape, never the s58 drive. The primary hybrid lane never stages
        # clips (the drive supplies all motion from the live donor bones) -- but the SHORT's own manifest
        # may reference authored clips via [[summon.short_staging.play]], so stage them here too (a no-op,
        # `[]`, when `clips` isn't an authored-path list -- see authored_clip_paths).
        _stage_authored_clips(spec, mod_root, ledger)
        short = _stage_short_seq(spec, mod_root, ledger, full_text=seq["text"])
        short["overlay_folder"] = _stage_short_overlay_folder(spec, mod_root, ledger)
        short["ability_features"] = _stage_short_summon_feature(spec, mod_root, ledger)
    ini_backup = arm_sfxhybrid(game, spec, log=True, out=out, ledger=ledger) if arm else None
    revert = ledger.write_revert_script(_revert_root(mod_root, work_dir), f"{spec['id']}")
    result = {"lane": "hybrid", "spec": spec, "mint": mint, "seq": seq,
              "arm_manifest": render_sfxhybrid_block(spec, log=True),
              "sfxhybrid_updates": sfxhybrid_updates(spec, log=True),
              "revert_script": str(revert), "artifacts": _artifact_paths(ledger),
              "armed": bool(arm)}
    if short is not None:
        result["short"] = short
        _print_short_receipt(spec, short, out=out)
    if ini_backup is not None:
        result["ini_backup"] = str(ini_backup)
    return result


def emit_overlay(spec: dict, mod_root, game, *, work_dir=None, out=print) -> dict:
    """The OVERLAY lane deploy (DESIGN rows 1, 1b, 2, 4, 5, 6) -- DLL-free, works on stock Memoria. Emits
    the mint + the host ``.seq`` (with the StartThread self-load) + the ``.anim`` clips + the ``.sfxmodel``
    + ``FileList.txt``. No ini. Writes a revert script. Returns a manifest dict.

    ``spec`` may be a raw ``[[summon]]`` block OR an already-:func:`normalize_spec`-ed spec (idempotent)."""
    spec = _resolve_ids(normalize_spec(spec), mod_root, game)
    _preflight_inputs(spec)
    _preflight_short_sequence(spec)
    ledger = _Ledger(_backup_root(mod_root, work_dir))
    mint = _stage_model(spec, mod_root, ledger)
    seq = _stage_host_seq(spec, mod_root, game, ledger, overlay=True)
    extras = _stage_overlay_extras(spec, mod_root, game, ledger)
    short = None
    if spec.get("short_sequence"):
        short = _stage_short_seq(spec, mod_root, ledger, full_text=seq["text"])
        short["overlay_folder"] = _stage_short_overlay_folder(spec, mod_root, ledger)
        short["ability_features"] = _stage_short_summon_feature(spec, mod_root, ledger)
    revert = ledger.write_revert_script(_revert_root(mod_root, work_dir), f"{spec['id']}")
    result = {"lane": "overlay", "spec": spec, "mint": mint, "seq": seq, "overlay": extras,
              "revert_script": str(revert), "artifacts": _artifact_paths(ledger)}
    if short is not None:
        result["short"] = short
        _print_short_receipt(spec, short, out=out)
    return result


def _resolve_ids(spec: dict, mod_root, game) -> dict:
    """Fill a deferred ``id`` / ``name`` / ``private_ef`` (DESIGN sections 1.2/1.3) + validate the private
    host against the install. Returns a NEW spec dict (the input is not mutated)."""
    spec = dict(spec)
    if spec.get("id") is None:
        spec["id"] = alloc_mint_id(mod_root)
    if spec.get("name") is None:
        spec["name"] = derive_summon_name(spec["id"], spec.get("group", DEFAULT_GROUP),
                                          spec.get("form", DEFAULT_FORM))
    _mint.validate_mint_name(spec["name"])
    if spec.get("private_ef") is None:
        spec["private_ef"] = alloc_private_ef(game, mod_root, spec["donor"])
    else:
        validate_private_ef(spec["private_ef"], spec["donor"], game=game, mod_root=mod_root)
    if spec.get("short_sequence"):
        if spec.get("short_private_ef") is None:
            # default = "primary private_ef + 1" -- but ABSENT_EF_IDS is NOT contiguous (18, 37, 39, 80,
            # 84, 91, ... gaps up to 19), so a LITERAL +1 lands outside the pool for 18 of the 24 ids. Read
            # "+1" as +1 POSITION in the ordered absent-id sequence instead (the next allocatable slot
            # after the primary) -- always a legal candidate barring pool exhaustion, and it reproduces the
            # bench precedent (84 -> 91, the rung-3/7 fresh id).
            #
            # MUST-FIX 2 (review 2026-07-24): unlike `alloc_private_ef`'s ascending SCAN (which picks a
            # genuinely different free id if its first pick is occupied -- appropriate for a search), this
            # default is a DETERMINISTIC function of `private_ef` alone -- redeploying the SAME block with
            # a PINNED `private_ef` recomputes the exact same `short_private_ef` every time. Validating it
            # `for_alloc=True` (the "refuse if `mod_root` already has this folder populated" branch) then
            # refused the block's own SECOND deploy on the very folder its FIRST deploy created. Mirror the
            # EXPLICIT-primary rule instead (`validate_private_ef`'s `for_alloc` default, False): a
            # computed-but-now-fixed id is checked exactly like a user-pinned one, so redeploying is
            # idempotent. (The same collision risk an explicit `private_ef` already accepts -- two
            # UNRELATED blocks landing on the same id -- applies here too; that is a pre-existing,
            # documented tradeoff of pinning, not something this default newly introduces.)
            spec["short_private_ef"] = _next_absent_ef(spec["private_ef"])
        validate_private_ef(spec["short_private_ef"], spec["donor"], game=game, mod_root=mod_root)
        if spec["short_private_ef"] == spec["private_ef"]:
            raise SummonDeployError(
                f"[[summon]] short_private_ef {spec['short_private_ef']} equals private_ef "
                f"{spec['private_ef']} -- the short cast needs its OWN private host id")
    return spec


def _backup_root(mod_root, work_dir) -> Path:
    base = Path(work_dir) if work_dir else Path(mod_root)
    return base / ".summon-backups"


def _revert_root(mod_root, work_dir) -> Path:
    base = Path(work_dir) if work_dir else Path(mod_root)
    return base / ".summon-revert"


def _artifact_paths(ledger: _Ledger) -> list:
    out = [dest for dest, _b in ledger.files]
    if ledger.dict_line:
        out.append(ledger.dict_path)
    return out


# --------------------------------------------------------------------------- top-level deploy

def deploy(block: dict, *, game=None, mod_root=None, arm=False, dry_run=False, out=print) -> dict:
    """The umbrella ``summon-deploy`` entry. Normalizes the block, resolves the install + mod folder,
    dispatches to the lane emitter, and (hybrid + ``arm`` + not ``dry_run``) performs the confirm-first
    ``[SfxHybrid]`` arm. ``dry_run`` stages every artifact under a SCRATCH mirror instead of the live mod
    folder (and never arms the ini). Returns the lane manifest (+ ``armed``/``dry_run``).

    The arm (hybrid lane only) happens INSIDE :func:`emit_hybrid`, before its revert script is written --
    so an armed deploy's revert script actually restores (or neutralizes) ``[SfxHybrid]`` too, not just the
    mint + host ``.seq``."""
    spec = normalize_spec(block)
    game = config.find_game_path(game)
    if mod_root is None:
        mod_root = config.find_mod_root(game)
    mod_root = Path(mod_root)
    work_dir = None
    if dry_run:
        from .export import DEFAULT_OUT_DIR
        work_dir = DEFAULT_OUT_DIR / "m2_stage"
        mod_root = work_dir / Path(mod_root).name
        if mod_root.exists():
            shutil.rmtree(mod_root)

    if spec["lane"] == "hybrid":
        result = emit_hybrid(spec, mod_root, game, work_dir=work_dir, arm=(arm and not dry_run), out=out)
    else:
        result = emit_overlay(spec, mod_root, game, work_dir=work_dir, out=out)
        result["armed"] = False
    result["dry_run"] = bool(dry_run)
    result["mod_root"] = str(mod_root)

    if spec["lane"] == "hybrid" and not result["armed"]:
        out("  (ini NOT armed -- pass arm=True / --arm to write [SfxHybrid]; here is the staged block:)")
        for line in result["arm_manifest"].splitlines():
            out(f"      {line}")
    return result


# --------------------------------------------------------------------------- summon-import (Blender return)

def validate_import_rig(model: dict) -> list:
    """The rig half of the import validation list (DESIGN section 3.1): bone names ``bone000..bone09N``,
    contiguous from 0, a single root (``bone000``, parent None), and every non-root parent present.
    Renaming/reparenting breaks Unity's by-path clip binding, so a mismatch is a hard problem. Smooth /
    multi-bone weights are NOT checked -- legal for a USER mesh (the rigidity is a property of the DONOR,
    not a constraint on the user's model). Returns a list of problems (empty = ok)."""
    bones = model.get("bones", [])
    if not bones:
        return ["no bones -- the model must be skinned to the summon-rig-ref armature (bone000..)"]
    nums, names = [], set()
    for b in bones:
        m = re.fullmatch(r"bone(\d+)", b.get("name", ""))
        if not m:
            return [f"bone {b.get('name')!r} isn't named boneNNN -- keep the summon-rig-ref bone names "
                    "(the FBX importer maps clips by the trailing bone id)"]
        nums.append(int(m.group(1)))
        names.add(b["name"])
    problems = []
    if sorted(nums) != list(range(len(nums))):
        problems.append(
            f"bones are not contiguous bone000..bone{len(nums) - 1:03d} -- Unity binds clips by a hierarchy "
            "path built from bone ids, so a gap/rename breaks the retarget")
    roots = [b for b in bones if b.get("parent") is None]
    if len(roots) != 1 or roots[0].get("name") != "bone000":
        problems.append("the rig must have exactly one root and it must be bone000 (the summon rig's shape)")
    for b in bones:
        p = b.get("parent")
        if p is not None and p not in names:
            problems.append(f"bone {b.get('name')} references a missing parent {p!r}")
    return problems


def validate_import_textures_fbx(fbx_bytes: bytes) -> list:
    """Texture half of the import validation for a ready FBX (DESIGN 3.1): the FBX must reference at least
    one texture by BARE filename (path_mode STRIP), so ``ModelImporter`` resolves it beside the deployed
    FBX. Mirrors ``m1b/stage_mint.py``'s ``b'Thomas_d.png' in fbx_bytes`` assert, generalized."""
    if b".png" not in fbx_bytes.lower() and b".tga" not in fbx_bytes.lower():
        return ["the FBX references no texture by name (STRIP path mode) -- the material/texture binding "
                "did not survive export; the creature would deploy untextured"]
    return []


def _glb_to_fbx(user_glb: Path, out_dir: Path, geo_id: int, *, scale: float) -> tuple:
    """Convert a Blender ``.glb`` (skinned to the summon rig) into the kit's ASCII FBX + PNG textures under
    ``out_dir`` (a scratch staging dir). Reuses ``models.gltf.import_gltf`` (glb -> Model struct, validates
    joints) + ``models.fbx_skin.emit_skinned_fbx`` (Model -> FBX). Returns ``(fbx_path, model, problems)``;
    the caller enforces ``problems``."""
    from ..models import fbx_skin as _fbxskin
    from ..models import gltf as _gltf2
    model = _gltf2.import_gltf(str(user_glb), scale=scale)
    problems = validate_import_rig(model)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    text, _meta = _fbxskin.emit_skinned_fbx(model)
    fbx_path = out_dir / f"{geo_id}.fbx"
    fbx_path.write_text(text, encoding="ascii", newline="\n")
    for stem, img in (model.get("textures") or {}).items():
        img.save(str(out_dir / f"{stem}.png"))
    return fbx_path, model, problems


def stage_import(user_model, block: dict, *, game=None, mod_root=None, dry_run=False,
                 scale: "float | None" = None, out=print) -> dict:
    """The ``summon-import`` packager (DESIGN section 3): validate the user's OWN retargeted model and
    deploy it via the lane emitter. This is the REVERSE of the export guard
    (``summons/export.py:assert_local_only``) -- export refuses to write STOCK content OUT of SCRATCH;
    ``stage_import`` accepts the user's OWN content INTO the user's OWN mod folder (verbatim-fork
    precedent). Accepts a Blender ``.glb`` (converted to FBX via the model pillar) OR a ready ``.fbx``
    (validated + deployed verbatim). ``dry_run`` stages under a SCRATCH mirror."""
    src = Path(user_model)
    if not src.is_file():
        raise SummonDeployError(f"summon-import model not found: {src}")
    if src.suffix.lower() not in (".glb", ".gltf", ".fbx"):
        # refuse the wrong file BEFORE resolving the install -- a user with a bad extension should get
        # this message even when their game path is unset/broken (and the check needs nothing else).
        raise SummonDeployError(f"summon-import takes a .glb/.gltf (Blender) or a .fbx, got {src.suffix!r}")
    spec = normalize_spec(block)
    game = config.find_game_path(game)
    if mod_root is None:
        mod_root = config.find_mod_root(game)
    mod_root = Path(mod_root)
    work_dir = None
    if dry_run:
        from .export import DEFAULT_OUT_DIR
        work_dir = DEFAULT_OUT_DIR / "m2_import_stage"
        mod_root = work_dir / mod_root.name
        if mod_root.exists():
            shutil.rmtree(mod_root)

    spec = _resolve_ids(spec, mod_root, game)      # need the id to name the FBX
    ext = src.suffix.lower()
    emit = emit_hybrid if spec["lane"] == "hybrid" else emit_overlay
    if ext in (".glb", ".gltf"):
        import tempfile
        from ..models import gltf as _gltf2
        sc = scale if scale is not None else _gltf2.DEFAULT_SCALE
        # the glb -> FBX intermediate stages in a throwaway temp dir (never the user's source dir);
        # _stage_model copies it INTO the mod folder before the temp dir is cleaned.
        tmp = Path(tempfile.mkdtemp(prefix="ff9mk-summon-import-"))
        try:
            try:
                fbx_path, _model, problems = _glb_to_fbx(src, tmp, spec["id"], scale=sc)
            except ValueError as e:
                # import_gltf validates the joint names itself (a renamed/non-boneNNN joint) BEFORE
                # validate_import_rig runs -- surface it as the same clean rig-validation refusal, not a
                # raw ValueError leaking through the library API (the CLI catches both; callers get one).
                raise SummonDeployError(f"summon-import rig validation failed:\n  {e}") from e
            if problems:
                raise SummonDeployError("summon-import rig validation failed:\n  " + "\n  ".join(problems))
            spec["model"] = str(fbx_path)
            result = emit(spec, mod_root, game, work_dir=work_dir)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    elif ext == ".fbx":
        raw = src.read_bytes()
        is_binary = raw[:20] == b"Kaydara FBX Binary  "
        problems = []
        if not is_binary:
            from ..models import fbx_validate as _fv
            try:
                problems += _fv.validate(raw.decode("utf-8", "replace"))
            except Exception as e:                 # a non-FBX text file
                raise SummonDeployError(f"{src} isn't a valid FBX: {e}") from e
        problems += validate_import_textures_fbx(raw)
        if problems:
            raise SummonDeployError("summon-import model validation failed:\n  " + "\n  ".join(problems))
        spec["model"] = str(src)
        result = emit(spec, mod_root, game, work_dir=work_dir)
    else:
        raise SummonDeployError(f"summon-import takes a .glb/.gltf (Blender) or a .fbx, got {src.suffix!r}")

    result["dry_run"] = bool(dry_run)
    result["mod_root"] = str(mod_root)
    result["imported_from"] = str(src)
    return result
