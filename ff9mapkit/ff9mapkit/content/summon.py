"""``[[summon]]`` -- the field-build-facing block-schema layer for summon transplants (M2; design:
``studies/custom-summons/thomas-swap/m2/DESIGN.md``). It declares "wear stock donor D's cast with my
model M" and, unlike every other ``content/`` block, emits NO ``.eb`` bytecode -- it compiles to asset
artifacts + a ``[SfxHybrid]`` ARM manifest, all staged by the DEPLOY engine (``summons/deploy.py``).

DIVISION OF LABOUR (do NOT duplicate deploy logic -- DESIGN section 5.1/5.2):
  * ``summons/deploy.py`` OWNS normalization, structural validation (:func:`deploy.normalize_spec`), the
    two lane emitters (:func:`deploy.emit_hybrid` / :func:`deploy.emit_overlay`), the ``[SfxHybrid]`` arm,
    and the revert ledger. It takes a **numeric** ``donor``.
  * THIS module is the block-schema half the deploy engine explicitly defers to (deploy.py SCOPE NOTE:
    "a SpecialEffect-name -> id resolution belongs to the block-schema layer, not this deploy engine"):
      1. resolve a ``donor`` **name** ("Bahamut__Full") -> its numeric effect id (:func:`resolve_donor`);
      2. enforce the field-schema requirements the design pins (``donor`` + ``model`` REQUIRED) and the
         build-time model-path existence check the deploy engine only does at emit;
      3. register the block into :func:`ff9mapkit.build.validate` (errors) + ``lint_all`` (the ``vfx1``
         cast-trigger reminder + ignored cross-lane keys) exactly like every other content block;
      4. dispatch a compile to the deploy engine (:func:`emit`).

    Everything structural (lane enum, id band, private_ef absent-set, hide_mask/node_count, the
    ``[SfxHybrid]`` values) is DELEGATED to ``deploy.normalize_spec`` -- this module never re-implements it.

THE CAST TRIGGER is NOT authored here (DESIGN section 1.4): it fires through the existing ability -> effect
lane -- an ``Actions.csv`` row's ``vfx1`` (``battle/actiondelta.py``) points at ``private_ef``. The block
lint reminds the user to wire that; it MUST NOT edit ``Actions.csv``.

THE TWO LANES: ``hybrid`` (default, the s58 ``SfxHybridDrive`` engine feature -- REQUIRES the custom
Memoria engine, gated at the arm step) and ``overlay`` (the DLL-free rung-7 ``FileList``/``.sfxmodel``/
``.anim`` route -- works on stock). Provenance is the deploy engine's (DESIGN section 6): this file is
committable CODE, embeds zero game bytes.
"""
from __future__ import annotations

__all__ = [
    "SummonBlockError", "SUMMON_DONORS", "KNOWN_KEYS", "MIN_EFFECT_ID", "MAX_EFFECT_ID",
    "resolve_donor", "numeric_block", "resolve_spec",
    "validate_block", "validate_blocks", "lint_notes", "emit",
]

#: every key ``deploy.normalize_spec`` / ``deploy._stage_model`` read -- the block-schema surface. The
#: deploy engine reads keys with ``.get`` (ignoring extras); rejecting unknown keys is this schema
#: layer's hygiene job, so a typo'd key is caught at lint rather than silently ignored.
KNOWN_KEYS = frozenset({
    "donor", "model", "lane", "id", "name", "group", "form", "private_ef",
    "hide_native", "hide_mask", "node_count", "apply_column_scale", "hide_meshes",
    "textures", "clips", "staging",
})


class SummonBlockError(ValueError):
    """A block-schema problem this layer owns: a missing/unknown ``donor`` name, a missing ``model``, a
    bad model path. Structural problems (lane/id/private_ef/...) surface as ``deploy.SummonDeployError``.
    Both subclass the message-carrying base every other block raises."""


# --- effect-id range (the stock ef### folders span ef001..ef510) -------------------------------------
MIN_EFFECT_ID = 1
MAX_EFFECT_ID = 510                                # Phoenix__Short = 510 is the highest real effect id

# --- donor NAME -> id (the creature-summon casts; the ONE catalog the deploy engine defers here) ------
# Numeric is canonical (what [SfxHybrid] EffectId + the ef{id:D3}/ folder take); a name resolves through
# this. Only the summon casts (real creature packages -- the transplant donors) are encoded; an unknown
# name is refused with a pointer to the numeric id, never silently guessed. Source (verified name=value):
# C:/gd/FFIX/Memoria .../Memoria/Data/Battle/SpecialEffect.cs.
SUMMON_DONORS: dict[str, int] = {
    "Shiva__Short": 407, "Shiva__Full": 38,
    "Ifrit__Short": 445, "Ifrit__Full": 276,
    "Ramuh__Short": 415, "Ramuh__Full": 186,
    "Atomos__Short": 446, "Atomos__Full": 184,
    "Odin__Short": 424, "Odin__Full": 261,
    "Leviathan__Short": 406, "Leviathan__Full": 179,
    "Bahamut__Short": 405, "Bahamut__Full": 227,
    "Ark__Short": 447, "Ark__Full": 381,
    "Carbuncle_Ruby__Short": 504, "Carbuncle_Ruby__Full": 177,
    "Carbuncle_Pearl__Short": 505, "Carbuncle_Pearl__Full": 493,
    "Carbuncle_Emerald__Short": 506, "Carbuncle_Emerald__Full": 494,
    "Carbuncle_Diamond__Short": 507, "Carbuncle_Diamond__Full": 495,
    "Fenrir_Earth__Short": 508, "Fenrir_Earth__Full": 210,
    "Fenrir_Wind__Short": 509, "Fenrir_Wind__Full": 226,
    "Phoenix__Short": 510, "Phoenix__Full": 211,
    "Phoenix_Rebirth_Flame": 225,
    "Madeen__Short": 378, "Madeen__Full": 251,
}
# for backfilling a numeric donor's display name (the "Full" cast / single-form name, never a "Short")
_DONOR_ID_TO_NAME = {v: k for k, v in SUMMON_DONORS.items() if k.endswith("__Full") or "__" not in k}


def _deploy():
    """Lazy handle to the deploy engine -- imported on demand so a field WITHOUT any ``[[summon]]`` block
    never pays for it (and to keep ``build.py``'s top-level import of this module cheap)."""
    from ..summons import deploy
    return deploy


def resolve_donor(donor) -> tuple[int, str | None]:
    """A ``donor`` value (numeric id OR SpecialEffect name) -> ``(id, name_or_None)``. Numeric is
    canonical; a name resolves through :data:`SUMMON_DONORS`. Structural sanity only (positive, in the
    ef### range, and not a stock-ABSENT id) -- the "has a real creature package" check is install-aware and
    is the deploy engine's ``fetch_donor_seq`` (DESIGN section 1.1)."""
    dep = _deploy()
    if isinstance(donor, bool):
        raise SummonBlockError(f"`donor` must be an effect id or SpecialEffect name (got {donor!r})")
    if isinstance(donor, int):
        did, name = donor, _DONOR_ID_TO_NAME.get(donor)
    elif isinstance(donor, str):
        s = donor.strip()
        if s.isdigit():
            did, name = int(s), _DONOR_ID_TO_NAME.get(int(s))
        elif s in SUMMON_DONORS:
            did, name = SUMMON_DONORS[s], s
        else:
            raise SummonBlockError(
                f"`donor` name {donor!r} is not a known summon effect -- use the numeric effect id "
                f"(canonical, e.g. 227 = Bahamut__Full) or one of: {', '.join(sorted(SUMMON_DONORS))}")
    else:
        raise SummonBlockError(f"`donor` must be an effect id or SpecialEffect name (got {donor!r})")
    if not (MIN_EFFECT_ID <= did <= MAX_EFFECT_ID):
        raise SummonBlockError(
            f"`donor` effect id {did} is out of range {MIN_EFFECT_ID}..{MAX_EFFECT_ID} (the stock ef### "
            f"folders)")
    if did in dep.ABSENT_EF_IDS:
        raise SummonBlockError(
            f"`donor` effect id {did} is a stock-ABSENT id (no creature to inherit a cast from) -- pick a "
            f"real summon donor (e.g. 227 = Bahamut__Full, 261 = Odin__Full)")
    return did, name


def numeric_block(block: dict) -> dict:
    """A copy of ``block`` with ``donor`` resolved to its numeric id (a name -> its id) and the field-schema
    requirements enforced: ``donor`` and ``model`` are REQUIRED (DESIGN section 1). Raises
    :class:`SummonBlockError`. The result is what the deploy engine's numeric-donor API consumes."""
    if not isinstance(block, dict):
        raise SummonBlockError(f"[[summon]] must be a table, got {type(block).__name__}")
    unknown = set(block) - KNOWN_KEYS
    if unknown:
        raise SummonBlockError(
            f"[[summon]] has unknown key(s) {sorted(unknown)} -- valid keys: {sorted(KNOWN_KEYS)}")
    if "donor" not in block:
        raise SummonBlockError("[[summon]] needs a `donor` (an effect id like 227, or a name like "
                               "\"Bahamut__Full\") -- the native cast whose bones/camera/staging to wear")
    if "model" not in block:
        raise SummonBlockError("[[summon]] needs a `model` (a path to your retargeted FBX on the "
                               "bone000..092 rig -- see `summon-rig-ref`)")
    donor_id, _name = resolve_donor(block["donor"])
    nb = dict(block)
    nb["donor"] = donor_id
    return nb


def resolve_spec(block: dict) -> dict:
    """The block -> the deploy engine's fully-resolved, defaults-filled spec (name donor resolved first).
    NO I/O; raises :class:`SummonBlockError` / ``deploy.SummonDeployError``. This is the delegating
    "resolve defaults" entry -- it never re-implements normalization."""
    return _deploy().normalize_spec(numeric_block(block))


def _model_path_problem(spec: dict, base_dir) -> str | None:
    """The build-time model-path existence check (the deploy engine only checks at emit). ``None`` = OK."""
    model = spec.get("model")
    if not model or base_dir is None:
        return None
    from pathlib import Path
    p = Path(model)
    if not p.is_absolute():
        p = Path(base_dir) / p
    if not p.is_file():
        return (f"[[summon]] `model` file not found: {p} "
                f"(a bare name resolves under the field's asset dir {base_dir})")
    return None


def _reprefix(msg: str, tag: str) -> str:
    """Normalize a message to ``<tag>: <body>`` -- strip any leading ``[[summon]]`` block tag the raised
    message already carries so the per-block index (``[[summon]] #2``) is never lost or doubled."""
    if msg.startswith("[[summon]]"):
        msg = msg[len("[[summon]]"):].lstrip(" :")
    return f"{tag}: {msg}"


def validate_block(block, *, base_dir=None, tag: str = "[[summon]]") -> list[str]:
    """One block's build-blocking problems as a message list (empty => OK). Resolves the donor name,
    delegates structure to ``deploy.normalize_spec``, and adds the model-path existence check. The
    advisory ``vfx1`` reminder is NOT here (it is a warning -- see :func:`lint_notes`)."""
    dep = _deploy()
    try:
        nb = numeric_block(block)
        spec = dep.normalize_spec(nb)
        _check_group(block, dep)              # deploy defers group->ModelType until a name is derived
    except (SummonBlockError, dep.SummonDeployError, ValueError) as e:
        return [_reprefix(str(e), tag)]
    problem = _model_path_problem(spec, base_dir)
    return [_reprefix(problem, tag)] if problem else []


def _check_group(block: dict, dep) -> None:
    """Validate a ``group`` -> ModelType early (a bad group only trips deploy once a name is derived from an
    ``id``; an id-less block would slip a typo through to emit). No-op unless ``group`` is set without an
    explicit ``name`` (an explicit name is validated by ``normalize_spec`` and makes group inert)."""
    if "group" not in block or "name" in block:
        return
    from ..models import mint as _mint
    name = dep.derive_summon_name(dep.MINT_BAND_START, str(block["group"]),
                                  str(block.get("form", dep.DEFAULT_FORM)))
    _mint.type_int_of_name(name)              # raises ValueError on an unknown group


def validate_blocks(blocks, *, base_dir=None) -> list[str]:
    """Every ``[[summon]]`` block's build-blocking problems (for ``lint`` + :func:`ff9mapkit.build.validate`).
    Empty => OK. Pure-logic except the optional model-path existence check when ``base_dir`` is given."""
    blocks = blocks or []
    problems: list[str] = []
    for i, block in enumerate(blocks):
        tag = f"[[summon]] #{i}" if len(blocks) > 1 else "[[summon]]"
        problems += validate_block(block, base_dir=base_dir, tag=tag)
    return problems


def lint_notes(blocks) -> list[str]:
    """Advisory (non-blocking) notes for ``lint_all``'s warning lane: (1) the cast-trigger reminder -- the
    block does NOT author the ability; the user must point an ``Actions.csv`` row's ``vfx1`` at
    ``private_ef`` (DESIGN section 1.4); (2) cross-lane keys that will be ignored. Never raises; skips
    blocks that don't even parse (their errors are already reported by :func:`validate_blocks`)."""
    blocks = blocks or []
    notes: list[str] = []
    for i, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue
        tag = f"[[summon]] #{i}" if len(blocks) > 1 else "[[summon]]"
        lane = str(block.get("lane", "hybrid")).lower()
        # An OMITTED private_ef is auto-allocated at deploy (the first free stock-absent id ascending,
        # NOT the bench constant DEFAULT_PRIVATE_EF=84) -- so mirror deploy.lint_spec's honest '<auto>'
        # placeholder rather than naming an id the user's ability must NOT be wired to.
        pef = block.get("private_ef")
        pef = pef if pef is not None else "<auto> (auto-allocated at deploy; summon-deploy prints it)"
        notes.append(f"{tag}: this block does NOT author the cast -- point an ability's `vfx1` at "
                     f"private_ef={pef} to fire it (see the authoring-ff9-battles skill / "
                     f"battle/actiondelta.py; the block MUST NOT edit Actions.csv).")
        if lane == "hybrid":
            stray = sorted(k for k in ("clips", "staging") if k in block)
            if stray:
                notes.append(f"{tag}: overlay-only key(s) {stray} are ignored on the hybrid lane.")
        elif lane == "overlay":
            stray = sorted(k for k in ("hide_mask", "node_count", "hide_native", "apply_column_scale")
                           if k in block)
            if stray:
                notes.append(f"{tag}: hybrid-only key(s) {stray} are ignored on the overlay (DLL-free) lane.")
    return notes


def emit(block: dict, mod_root, game, *, work_dir=None):
    """Compile one ``[[summon]]`` block by driving the deploy engine's lane emitter (DESIGN section 5.1:
    ``emit_hybrid`` / ``emit_overlay``). Resolves the donor name -> id, normalizes, and dispatches -- it
    does NOT duplicate staging. Returns the deploy engine's lane manifest.

    NOTE the ``[SfxHybrid]`` arm is deliberately NOT done here: ``emit_hybrid`` STAGES the arm block into
    the returned manifest, and the actual ini write is the explicit confirm-first ``summon-deploy`` arm
    step (``deploy.arm_sfxhybrid``, DESIGN section 2.4)."""
    dep = _deploy()
    spec = dep.normalize_spec(numeric_block(block))
    fn = dep.emit_hybrid if spec["lane"] == "hybrid" else dep.emit_overlay
    return fn(spec, mod_root, game, work_dir=work_dir)
