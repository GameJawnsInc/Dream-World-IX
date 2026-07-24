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

    donor_raw = block.get("donor", DEFAULT_DONOR)
    if isinstance(donor_raw, str) and not donor_raw.strip().isdigit():
        raise SummonDeployError(
            f"[[summon]] donor {donor_raw!r} is a name -- the deploy engine takes the NUMERIC effect id "
            "(e.g. 227 for Bahamut). Resolve a SpecialEffect name to its id in the block-schema layer "
            "first, or pass the numeric id.")
    donor = _as_int(donor_raw, "[[summon]] donor")
    if donor <= 0:
        raise SummonDeployError(f"[[summon]] donor id {donor} must be positive")

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
    staging = str(block.get("staging", "donor")).lower()
    if staging not in ("donor", "curves"):
        raise SummonDeployError(f"[[summon]] staging must be 'donor' or 'curves', got {staging!r}")

    textures = block.get("textures")
    if textures is not None:
        textures = [str(t) for t in textures]

    return {
        "lane": lane, "donor": donor, "model": block.get("model"), "textures": textures,
        "id": new_id, "name": name, "group": group, "form": form,
        "private_ef": private_ef,
        "hide_native": bool(block.get("hide_native", True)),
        "hide_mask": hide_mask, "node_count": node_count,
        "apply_column_scale": bool(block.get("apply_column_scale", False)),
        "hide_meshes": hide_meshes,
        "clips": clips, "staging": staging,
    }


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
    """Row 2: the drift-guarded donor ``.seq`` copy spliced into ``ef{private_ef:D3}/PlayerSequence.seq``.
    The donor is READ (never written); its unified diff is captured for the deploy receipt."""
    donor_text = fetch_donor_seq(game, spec["donor"])
    out_text = splice_host_seq(donor_text, spec.get("hide_meshes"), private_ef=spec["private_ef"],
                               overlay=overlay)
    seq_dest = _sfx_dir(mod_root, spec["private_ef"]) / HOST_SEQ_NAME
    seq_sha = ledger.write_bytes(seq_dest, out_text.encode("utf-8"))
    diff = "".join(difflib.unified_diff(
        donor_text.splitlines(keepends=True), out_text.splitlines(keepends=True),
        fromfile=f"stock/ef{spec['donor']:03d}/{HOST_SEQ_NAME}",
        tofile=f"ef{spec['private_ef']:03d}/{HOST_SEQ_NAME}"))
    return {"seq_dest": str(seq_dest), "seq_sha256": seq_sha, "seq_diff": diff}


# --------------------------------------------------------------------------- overlay extras (rows 4/5/6)

def _sfxmodel_manifest(spec: dict, clip_names: list) -> dict:
    """The ``.sfxmodel`` JSON manifest (overlay lane, DESIGN row 5): one FBX entry naming the bare minted
    GEO name (Hop 4/5 discards the ef folder), plus one ``Animations[]`` entry per baked clip referenced by
    its literal ``Animations/{id}/{clip}`` path (Hop 8; verbatim, unprefixed). Sane world-origin
    Movement/Rotation/Scaling anchors so a mis-wired overlay degrades to "visible but static" not
    "invisible at the origin" (FBX-PATHS section 4)."""
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


def _decode_donor_clips(spec: dict, game) -> list:
    """Decode the donor creature's motion clips offline for the overlay ``.anim`` set (DESIGN 3.3), reusing
    the proven ``summons.build.adapt_all_clips`` decoder. Reads a LOCAL ``ef{donor}.bytes`` under
    ``C:/gd/SCRATCH/summon-transplant/`` (stock-derived -- never committed). Honors ``spec['clips']``
    ('all'|'none'|index list). Returns ``[(clip_name, clip_dict), ...]`` in file order."""
    clips_sel = spec.get("clips", "all")
    if clips_sel in (None, "none", "off", []):
        return []
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
    ``FileList.txt`` -- all under the PRIVATE ``ef{private_ef}/`` folder (never the donor's)."""
    from . import container as _container
    # decode + write the clips
    clips = _decode_donor_clips(spec, game)
    # bone-number -> parent map from the donor rig (for the hierarchy-path re-key)
    parent_of = {}
    src = _local_ef_bytes(spec["donor"])
    if clips:
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

    manifest = _sfxmodel_manifest(spec, clip_names)
    manifest_name = "creature_manifest.sfxmodel"
    man_dest = _sfx_dir(mod_root, spec["private_ef"]) / manifest_name
    ledger.write_bytes(man_dest, (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))

    fl_dest = _sfx_dir(mod_root, spec["private_ef"]) / "FileList.txt"
    ledger.write_bytes(fl_dest, f"Model {manifest_name}\n".encode("utf-8"))
    return {"manifest_dest": str(man_dest), "filelist_dest": str(fl_dest), "clips": clip_names}


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
    ledger = _Ledger(_backup_root(mod_root, work_dir))
    mint = _stage_model(spec, mod_root, ledger)
    seq = _stage_host_seq(spec, mod_root, game, ledger, overlay=False)
    ini_backup = arm_sfxhybrid(game, spec, log=True, out=out, ledger=ledger) if arm else None
    revert = ledger.write_revert_script(_revert_root(mod_root, work_dir), f"{spec['id']}")
    result = {"lane": "hybrid", "spec": spec, "mint": mint, "seq": seq,
              "arm_manifest": render_sfxhybrid_block(spec, log=True),
              "sfxhybrid_updates": sfxhybrid_updates(spec, log=True),
              "revert_script": str(revert), "artifacts": _artifact_paths(ledger),
              "armed": bool(arm)}
    if ini_backup is not None:
        result["ini_backup"] = str(ini_backup)
    return result


def emit_overlay(spec: dict, mod_root, game, *, work_dir=None) -> dict:
    """The OVERLAY lane deploy (DESIGN rows 1, 1b, 2, 4, 5, 6) -- DLL-free, works on stock Memoria. Emits
    the mint + the host ``.seq`` (with the StartThread self-load) + the ``.anim`` clips + the ``.sfxmodel``
    + ``FileList.txt``. No ini. Writes a revert script. Returns a manifest dict.

    ``spec`` may be a raw ``[[summon]]`` block OR an already-:func:`normalize_spec`-ed spec (idempotent)."""
    spec = _resolve_ids(normalize_spec(spec), mod_root, game)
    ledger = _Ledger(_backup_root(mod_root, work_dir))
    mint = _stage_model(spec, mod_root, ledger)
    seq = _stage_host_seq(spec, mod_root, game, ledger, overlay=True)
    extras = _stage_overlay_extras(spec, mod_root, game, ledger)
    revert = ledger.write_revert_script(_revert_root(mod_root, work_dir), f"{spec['id']}")
    return {"lane": "overlay", "spec": spec, "mint": mint, "seq": seq, "overlay": extras,
            "revert_script": str(revert), "artifacts": _artifact_paths(ledger)}


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
        result = emit_overlay(spec, mod_root, game, work_dir=work_dir)
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
