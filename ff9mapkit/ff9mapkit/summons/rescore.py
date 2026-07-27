r"""THE CONTENT RESCORE: reframe a stock summon's camera shot, durations UNCHANGED.

The summon camera decodes and re-encodes BYTE-IDENTICAL through the battle
:mod:`~ff9mapkit.battle.camera_codec` (:mod:`ff9mapkit.summons.camera` proves and uses that). This
module spends it: it reads the target effect out of **the user's own install**, applies a DECLARATIVE
delta expressed in the read-out's own vocabulary (shot / chunk / sub-file / sequence / local frame /
camera pose / focal H), splices the re-serialised block back at the SAME LENGTH, and stages the whole
container as a mod-folder override. Nothing stock is ever written into the repo.

    from ff9mapkit.summons import rescore
    spec  = rescore.load_spec("phoenix_rescore.toml")
    build = rescore.build_patched(spec, "phoenix_rescore.toml")   # reads the install, splices, self-checks
    rescore.stage(build)                                          # writes the override + a revert script

THE THREE HARD CONSTRAINTS, each enforced at the call site (a law in a docstring is a wish)
-------------------------------------------------------------------------------------------
1. **DURATIONS UNCHANGED.** :func:`apply_edit` REFUSES any key that would move a clock -- a Movement
   ``duration``, a focal ``duration``, a Code ``frame``. The camera and the effect's program are two
   clocks the original author kept aligned by construction; a content rescore moves neither. Retiming
   is a separate lane, and it must move the program's phase constants with it.
2. **BYTE LENGTH UNCHANGED.** A camera sub-file's length is defined by the NEXT id-2 directory entry,
   and a large minority of stock blocks have only 0-2 bytes of slack. :func:`rescore_block` asserts
   ``len(new) == len(old)`` before anything is spliced, so the id-2 directory never has to move and the
   native walker's sector sum (``cursor_end == size``) cannot break.
3. **THE FRAME WORD'S HIGH BITS SURVIVE.** A Code's ``frame`` u16 carries undecoded marks in ``0xE000``.
   This module never writes a frame word at all, which is the strongest form of preserving them.

THE THREE-SEQUENCE TRAP
-----------------------
Roughly half of stock camera blocks declare three sequences, and most of those carry genuinely DIFFERENT
alternate takes chosen at runtime by the bit-3 selector. Editing one track of such a block produces a
cast that may look completely unchanged. :func:`check_alternates` reports the verdict for the target
block, and :func:`build_patched` REFUSES a single-sequence edit on a block whose alternates differ unless
the spec says ``all_sequences = true`` (which fans the same delta across every declared track).

THE DYNAMIC-OP DISCLOSURE
-------------------------
``PLAY_CAMERA`` with ``arg2 == 3`` picks its block from a **runtime table keyed by the battle field**;
that table is not merely undecoded, it is ABSENT from the container. So from these bytes alone nothing
can say whether the (chunk, sub-file) pair being edited is ALSO the target of a lookup under some other
battle condition, nor which other blocks that lookup may reach instead. :func:`build_patched` therefore
REFUSES any container carrying such an op unless the spec says ``acknowledge_dynamic_ops = true`` -- a
DISCLOSURE gate, not a hard block. The converse is refused too: an ``= true`` on a container with ZERO
dynamic ops is a stale acknowledgement copied from another effect, and a safety key that was never true
here must not be allowed to look satisfied.

THE SILENT-FAILURE RISK THIS IS ALL SHAPED AROUND
-------------------------------------------------
``SFX.Play`` passes ``suppressMissingError = true``, so a wrong override path logs NOTHING and the stock
camera plays. "Nothing changed" is the symptom of EVERY misresolution -- a wrong folder, a wrong name, a
stray extension, a ModFileList that does not list the file, another mod folder earlier in ``FolderNames``
shipping its own copy, or the selector picking a track that was not edited. That is why a first delta
should be deliberately LARGE, and why the reports here enumerate the misresolutions instead of saying
"check the log".

PROVENANCE
----------
The stock container is read at RUN TIME from ``resources.assets`` in the user's install -- never from the
repo, and never from a previously-written override, so a Steam/Moguri patch cannot be silently shadowed
forever. A sha256 DRIFT GUARD (hash only; no stock bytes) refuses a donor whose install bytes differ from
the ones an edit was derived against. Staged output defaults under :data:`STAGING_BASE`;
:func:`_refuse_repo_path` refuses any destination inside a checkout or a mod-asset tree.
"""
from __future__ import annotations

import hashlib
import os
import struct
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from ..battle import camera_codec
from . import camera as W
from . import container as EC
from . import export
from .ledger import Ledger

__all__ = [
    "RescoreError", "StockDriftError",
    "MOD_SUBPATH", "EXPECTED_STOCK_SHA", "SCAFFOLD_QUOTE_BUDGET",
    "STAGING_BASE", "LEGACY_STAGING", "staging_root", "default_mod_root",
    "POSE_FIELDS", "FOCAL_FIELDS", "MOVE_FIELDS",
    "read_stock_effect", "drift_guard",
    "dynamic_ops", "dynamic_disclosure",
    "code_field_offsets", "Target", "find_shot", "find_code", "resolve_targets", "apply_edit",
    "Splice", "rescore_block", "splice_container",
    "AlternatesVerdict", "alternates_signature", "check_alternates",
    "block_invariants", "SelfCheck", "self_check",
    "load_spec", "Build", "build_patched", "describe",
    "Ledger", "stage", "verify", "modfilelist_refusal",
    "PhaseRow", "ShotRow", "ScaffoldTarget", "Scaffold",
    "shot_rows", "choose_target", "scaffold", "scaffold_summary", "write_scaffold",
]

#: the on-disc override path the engine's mod pass reads. ``AssetManager.LoadBytes("SpecialEffects/
#: ef227")`` is NOT "Data/"-prefixed, so ``IsMemoriaAssets`` is false and ``GetBelongingBundleFilename``
#: is "" -- ``LoadBytesMultiple`` falls through to the disc pass, which probes
#: ``GetResourcesAssetsPath(true) + "/" + name`` under each mod folder = ``<mod>/FF9_Data/<name>``.
#: EXTENSIONLESS: ``LoadFromDisc`` reads the raw path, so ``ef227.bytes`` would never be found.
MOD_SUBPATH = "FF9_Data/SpecialEffects"

#: THE STAGING BASE -- a per-effect directory lands under it. Local-only by construction (the same root
#: the kit already documents as the home for stock-derived summon output) and re-checked through
#: :func:`ff9mapkit.summons.export.assert_local_only` every time it is used as a default, so the default
#: can never quietly become a committable or shippable location.
STAGING_BASE = export.DEFAULT_OUT_DIR / "rescore"

#: effect id -> a staging root PINNED to somewhere other than the per-effect default. Empty here on
#: purpose: a pin exists only for an effect whose staged revert chain is already DEPLOYED somewhere and
#: must not be relocated, which is per-installation history, not a property of the tool. A study or a
#: caller that carries such history re-pins this mapping on the module.
LEGACY_STAGING: Dict[int, str] = {}

#: sha256 of pristine stock containers a shipped edit was derived against. HASH ONLY -- no stock byte
#: ever enters a committable file. A donor whose install bytes drift is REFUSED (the
#: ``EXPECTED_DONOR_SEQ_SHA`` posture from :mod:`ff9mapkit.summons.deploy`). Effects absent from this
#: map are allowed but UNGUARDED unless their own spec pins ``expect_sha256`` -- which, on a tool that
#: takes any summon, is the normal case.
EXPECTED_STOCK_SHA = {
    227: "fe590d00a01d95c6dc473cee9fea9096b9ded63c3daae3aab693099c6d0ed167",  # Bahamut__Full
}

#: ONE Code's sub-blocks, in ``camera_codec.split_code``'s exact field order. ``None`` marks a bit that
#: ABORTS the reader (the codec returns early), so nothing after it exists in the block.
_CODE_LAYOUT: Tuple[Tuple[int, Optional[str], int], ...] = (
    (0x0003, "campos", 6), (0x0002, "cammove", 4), (0x0004, None, 0),
    (0x0018, "tgtpos", 6), (0x0010, "tgtmove", 4), (0x0020, None, 0),
    (0x0040, "sign", 2), (0x0200, "unk3", 2), (0x0400, "unk4", 2),
    (0x0800, "focal", 4), (0x1000, "unk5", 4), (0x4000, "setting", 2), (0x8000, "unk6", 4),
)

#: a 6-byte pose, by the read-out's names
POSE_FIELDS = {"code": 0, "flags": 1, "pitch": 2, "orientation": 3, "roll": 4, "distance": 5}
#: a 4-byte focal: the PROJECTION DISTANCE (H) is the u16 at +2 -- the one camera value an in-game
#: capture can observe directly, so it is the calibrated half of a reframe.
FOCAL_FIELDS = {"duration": (0, 1), "flags": (1, 1), "distance": (2, 2)}
#: a 4-byte movement. ``duration`` is a CLOCK and is refused (constraint 1).
MOVE_FIELDS = {"duration": (0, 2), "type": (2, 1), "unknown": (3, 1)}

#: keys this lane refuses outright, with the reason quoted at the call site
_REFUSED = {
    ("focal", "duration"): "a focal duration is a CLOCK -- a content rescore keeps every duration byte "
                           "identical so the two clocks stay aligned (the retime lane owns timing)",
    ("camera_move", "duration"): "a movement duration is a CLOCK -- see the two-clocks law; changing "
                                 "it drifts the cut off the program's phase beat",
    ("target_move", "duration"): "a movement duration is a CLOCK -- see the two-clocks law",
}

#: spec section -> the parsed Code sub-block it edits
_SECTIONS = {"camera": "campos", "target": "tgtpos", "focal": "focal",
             "camera_move": "cammove", "target_move": "tgtmove"}

#: every key ``[rescore]`` understands. Unknown keys are REFUSED rather than ignored: a mistyped
#: ``expect_sha256`` would silently drop the drift guard, which fails OPEN -- the one direction a
#: provenance guard may never fail. (A mistyped acknowledge key fails CLOSED, which is fine, but the
#: author still deserves to be told the spec does not say what they think it says.)
_RESCORE_KEYS = frozenset(("effect", "label", "expect_sha256", "acknowledge_dynamic_ops"))
#: every key one ``[[edit]]`` understands: the addressing keys plus the five editable sections
_EDIT_KEYS = frozenset(("shot", "chunk", "subfile", "sequence", "all_sequences",
                        "frame", "occurrence")) | frozenset(_SECTIONS)
#: every top-level table a rescore spec may declare
_SPEC_KEYS = frozenset(("rescore", "edit"))

#: how many STOCK VALUES a generated scaffold may quote. The scaffold is a committable AUTHORED spec,
#: not a decoded stock listing: it may name the values its own declared edit writes and nothing else.
#: The full keyframe dump belongs on stdout (``camera.read_out``), where it stays.
SCAFFOLD_QUOTE_BUDGET = 4


class RescoreError(RuntimeError):
    pass


class StockDriftError(RescoreError):
    """The install's bytes are not the bytes this edit was derived against."""


# ============================================================ (0) provenance guards
def _refuse_repo_path(p) -> Path:
    """No stock-derived byte ever lands in a committable or shippable location.

    These are clauses 1 and 2 of :func:`ff9mapkit.summons.export.assert_local_only` -- a git checkout
    anywhere up the ancestry (which catches this repo, any worktree and any other clone without
    hardcoding a root) and any ``StreamingAssets`` segment (a Memoria mod-asset tree). There is no
    ``--force``: this is a provenance rule, not a safety prompt.

    Clause 3 -- the FF9 install -- is deliberately NOT folded in here. It lives in
    :func:`_refuse_install_path`, which takes the install root as an ARGUMENT, because (a) this lane's
    deploy path legitimately targets the install once the user asks for it, and a guard that made that
    impossible would simply be wrong, and (b) resolving the install ourselves would refuse a caller who
    passed a different one. Together the two functions are the same three clauses.

    (The predecessor of this function derived the repo root from ``__file__`` by counting directories
    up. That is only ACCIDENTALLY correct after a move and silently wrong in an installed wheel, where
    three levels above ``site-packages/ff9mapkit/summons/`` is arbitrary -- a provenance guard that
    fails OPEN, which is the one direction it may never fail.)
    """
    ap = Path(p).resolve()
    for anc in (ap, *ap.parents):
        if (anc / ".git").exists():
            raise RescoreError(
                "refusing to stage stock-derived bytes under the repo: %s\n"
                "  (a git checkout lives at %s, so anything written there is committable -- and a "
                "stock container never may be)" % (ap, anc))
    if any(seg.lower() == "streamingassets" for seg in ap.parts):
        raise RescoreError(
            "refusing to stage stock-derived bytes inside a Memoria mod-asset tree (a "
            "StreamingAssets path): %s" % ap)
    return ap


def _refuse_install_path(p, game_root) -> Path:
    """STAGE by default: never write into the game install unless a caller explicitly allows it.

    Clause 3 of :func:`~ff9mapkit.summons.export.assert_local_only`, against the install root the
    CALLER named rather than one resolved here. ``game_root=None`` means "no install is in play", which
    is a normal offline state and not a licence to skip a check that had a root to check against.
    """
    ap = Path(p).resolve()
    if game_root is None:
        return ap
    root = Path(game_root).resolve()
    try:
        common = os.path.commonpath([str(ap), str(root)])
    except ValueError:                                           # different drives -- fine
        return ap
    if common == str(root):
        raise RescoreError("refusing to write inside the game install: %s (this lane stages by "
                           "default; pass the explicit allow-install flag to deploy)" % ap)
    return ap


def staging_root(effect: int, root=None) -> str:
    """The per-effect staging WORK dir: ``<root or STAGING_BASE>/ef###``, unless :data:`LEGACY_STAGING`
    pins this effect somewhere else.

    PER EFFECT, not shared: with one root for every effect, building a second summon drops its container
    and its revert script INSIDE the first one's kit, and two effects staged in one session overwrite
    each other's backups. A correct ``--out`` is not enough to keep two effects apart if the WORK dir
    still comes from a module constant -- so :func:`default_mod_root` derives from this, and
    :func:`stage` derives the work dir from the resolved mod root.
    """
    pinned = LEGACY_STAGING.get(int(effect))
    if pinned:
        return str(pinned)
    return os.path.join(str(root or STAGING_BASE), "ef%03d" % int(effect))


def default_mod_root(effect: int, root=None) -> str:
    """The staging mod root for one effect -- ``<staging_root>/mod``, ALWAYS under the same per-effect
    directory the work dir resolves to, so the two can never point at different effects' kits."""
    return os.path.join(staging_root(effect, root), "mod")


# ============================================================ (1) read the user's OWN install
def read_stock_effect(ef_id: int, game=None) -> Tuple[bytes, str]:
    """The stock ``ef###`` container, re-derived from ``resources.assets`` in the user's install.

    ALWAYS from ``resources.assets``, never from a previously-written override: an override is a frozen
    whole-container copy, so re-reading one would compound our own edit and would hide the day a
    Steam/Moguri patch changes the stock effect. Returns ``(bytes, source description)``.
    """
    from .. import config
    try:
        import UnityPy
    except ImportError as e:
        raise RescoreError(
            "UnityPy is required to read the install's resources.assets, and it is not importable "
            "(%s).\n  Install the assets extra:  py -m pip install \"ff9mapkit[assets]\"" % e)
    root = Path(config.find_game_path(game))
    cands = [root / "x64" / "FF9_Data" / "resources.assets",
             root / "FF9_Data" / "resources.assets",
             root / "x86" / "FF9_Data" / "resources.assets"]
    want = "ef%03d" % ef_id
    for res in cands:
        if not res.exists():
            continue
        env = UnityPy.load(str(res))
        for obj in env.objects:
            if obj.type.name != "TextAsset":
                continue
            try:
                d = obj.read()
            except Exception:                                    # pragma: no cover
                continue
            name = str(getattr(d, "m_Name", None) or getattr(d, "name", ""))
            if name != want:
                continue
            raw = d.m_Script
            blob = (raw.encode("utf-8", "surrogateescape") if isinstance(raw, str)
                    else bytes(raw))
            return blob, str(res)
    raise RescoreError("no TextAsset %r in this install's resources.assets (looked in %s)"
                       % (want, ", ".join(str(c) for c in cands)))


def drift_guard(ef_id: int, blob: bytes, expect: Optional[str] = None) -> str:
    """sha256 of the install bytes, refused if it drifts from the registered or spec-pinned constant.

    Hash only -- the constant is committable because it is not stock DATA. An unregistered donor is
    ALLOWED but the caller is told there is no guard (``deploy.py``'s warn-not-refuse posture)."""
    got = hashlib.sha256(blob).hexdigest()
    want = expect or EXPECTED_STOCK_SHA.get(ef_id)
    if want and got != want:
        raise StockDriftError(
            "ef%03d in this install does not match the bytes this rescore was derived against.\n"
            "  expected sha256 %s\n  install  sha256 %s\n"
            "The install changed (a Steam/Moguri patch, or another mod wrote it). Re-derive the shot "
            "indices from a fresh read-out before trusting this delta." % (ef_id, want, got))
    return got


# ============================================================ (1b) THE DYNAMIC-OP DISCLOSURE
def dynamic_ops(ex: "W.Extract") -> List["W.CameraOp"]:
    """Every camera op this container resolves at RUNTIME (``PLAY_CAMERA arg2 = 3``).

    ``extract_shots`` never letter-enumerates these -- they land in ``ex.skipped`` -- so a spec can never
    name one by shot letter. That is exactly why the risk is invisible without this call: an edit
    addressed by (chunk, sub-file) reaches the physical block REGARDLESS of which op eventually resolves
    to that index, and the table these ops read is battle-field-keyed data that is not in the container
    at all.
    """
    return [o for o, why in ex.skipped if why == "dynamic"]


def dynamic_disclosure(ef_id: int, ex: "W.Extract") -> List[str]:
    """The human disclosure text for a container's runtime-chosen camera ops (empty if none)."""
    dyn = dynamic_ops(ex)
    if not dyn:
        return []
    L = ["ef%03d runs %d RUNTIME-CHOSEN camera op(s) (PLAY_CAMERA arg2 = %d, %s):"
         % (ef_id, len(dyn), W.ARG2_TABLE, W.ARG2_NAMES[W.ARG2_TABLE])]
    for o in dyn:
        L.append("  %s @file %#x, chunk %d, arg1 %d, seq tick %d"
                 % (o.kind, o.at, o.chunk_slot, o.arg1, o.seq_tick))
    L.append("Each picks its camera block from a table keyed by the BATTLE FIELD at run time. That "
             "table is not undecoded -- it is ABSENT from these bytes, so no offline analysis can "
             "say which sub-file indices it reaches, nor whether it also reaches the one being "
             "edited. The consequences an offline gate CANNOT rule out:")
    L.append("  * the edited block may also play under battle conditions this edit was not judged "
             "against (a different enemy count, a different party, a different arena);")
    L.append("  * a condition may pick a DIFFERENT block entirely, so the cast can look completely "
             "unchanged -- the same symptom as a mis-resolved override.")
    L.append("Only an in-game cast across VARIED battle conditions closes this. No offline gate can.")
    return L


# ============================================================ (2) the Code field map
def code_field_offsets(flags: int) -> Dict[str, Tuple[int, int]]:
    """``{name: (offset, size)}`` within a Code's ``block``, mirroring ``camera_codec.split_code``.

    The codec SLICES; a rescore must SPLICE, so it needs the offsets the slicer walks past. The two are
    pinned to agree by a test that sweeps every flag word -- if the codec's field order ever changes,
    that test fails rather than this module writing into the wrong four bytes.
    """
    out: Dict[str, Tuple[int, int]] = {}
    off = 0
    for bit, name, size in _CODE_LAYOUT:
        if not flags & bit:
            continue
        if name is None:                                         # an aborting bit: nothing follows
            break
        out[name] = (off, size)
        off += size
    return out


def _patch_bytes(block: bytes, at: int, raw: bytes) -> bytes:
    b = bytearray(block)
    b[at:at + len(raw)] = raw
    return bytes(b)


# ============================================================ (3) locate + edit
@dataclass
class Target:
    """One resolved keyframe: which shot, which track, which Code."""
    shot: "W.Shot"
    shot_letter: str
    seq_index: int
    code_index: int
    local_frame: int
    flags: int


def find_shot(ex: "W.Extract", spec: dict) -> Tuple[int, "W.Shot"]:
    """The spec's shot, by LETTER (the read-out label) and cross-checked against chunk/sub-file.

    Both are required when both are given: the letter is what a human reads in the read-out, the
    (chunk, sub-file) pair is what actually addresses the block. A mismatch means the read-out the spec
    was written against is not the read-out of the bytes in front of us -- refuse, loudly.
    """
    letter = str(spec.get("shot", "")).upper()
    chunk, sub = spec.get("chunk"), spec.get("subfile")
    idx = None
    if letter:
        i = W._SHOT_LETTERS.find(letter)
        if i < 0 or i >= len(ex.shots):
            raise RescoreError("no shot %r in this effect (%d shots resolved)"
                               % (letter, len(ex.shots)))
        idx = i
    if chunk is not None and sub is not None:
        hits = [i for i, s in enumerate(ex.shots) if s.slot == chunk and s.index == sub]
        if not hits:
            raise RescoreError("no shot at chunk %s sub-file %s" % (chunk, sub))
        if idx is not None and idx not in hits:
            raise RescoreError(
                "spec disagrees with the container: shot %s is chunk %d sub-file %d, but the spec "
                "names chunk %s sub-file %s. The read-out this spec was written against is not "
                "this effect." % (letter, ex.shots[idx].slot, ex.shots[idx].index, chunk, sub))
        idx = hits[0] if idx is None else idx
    if idx is None:
        raise RescoreError("an [[edit]] must name a shot (letter) or a chunk+subfile pair")
    return idx, ex.shots[idx]


def find_code(shot: "W.Shot", seq_index: int, local_frame: int) -> int:
    """Index into ``cam['sequences'][seq_index]`` of the Code at ``local_frame``.

    Refuses an ambiguous frame by returning ``-len(hits)``: a frame can carry TWO Codes (a placement and
    the move it starts), and naming such a frame without saying which is a coin-flip, so the spec must
    add ``occurrence``."""
    seqs = shot.camera["sequences"]
    if seq_index >= len(seqs):
        raise RescoreError("this block declares %d sequence(s); no sequence%d"
                           % (len(seqs), seq_index))
    hits = [i for i, c in enumerate(seqs[seq_index])
            if c.get("frame") and W.frame_number(c["frame"]) == local_frame]
    if not hits:
        raise RescoreError("no keyframe at local frame %d in sequence%d" % (local_frame, seq_index))
    return hits[0] if len(hits) == 1 else -len(hits)             # negative => ambiguous, see caller


def resolve_targets(ex: "W.Extract", edit: dict) -> List[Target]:
    """The Codes one ``[[edit]]`` names -- one per track it applies to (see the three-sequence trap)."""
    idx, shot = find_shot(ex, edit)
    letter = W._SHOT_LETTERS[idx % 26]
    frame = edit.get("frame")
    if frame is None:
        raise RescoreError("[[edit]] on shot %s has no `frame` (the keyframe's LOCAL frame number, "
                           "as printed by the read-out)" % letter)
    occ = int(edit.get("occurrence", 0))
    n_seq = len(shot.camera["sequences"])
    if edit.get("all_sequences"):
        seq_ids = list(range(n_seq))
    else:
        seq_ids = [int(edit.get("sequence", 0))]
    out = []
    for si in seq_ids:
        seqs = shot.camera["sequences"]
        if si >= len(seqs):
            raise RescoreError("this block declares %d sequence(s); no sequence%d" % (len(seqs), si))
        hits = [i for i, c in enumerate(seqs[si])
                if c.get("frame") and W.frame_number(c["frame"]) == int(frame)]
        if not hits:
            raise RescoreError("no keyframe at local frame %s in sequence%d of shot %s"
                               % (frame, si, letter))
        if len(hits) > 1 and "occurrence" not in edit:
            raise RescoreError(
                "local frame %s has %d Codes in sequence%d of shot %s (a placement and the move it "
                "starts, typically). Add `occurrence = 0` (or 1..%d) to say which one."
                % (frame, len(hits), si, letter, len(hits) - 1))
        if occ >= len(hits):
            raise RescoreError("occurrence %d out of range (frame %s has %d Codes)"
                               % (occ, frame, len(hits)))
        ci = hits[occ]
        out.append(Target(shot, letter, si, ci, int(frame), seqs[si][ci]["flags"]))
    return out


def apply_edit(shot: "W.Shot", tgt: Target, edit: dict) -> List[Tuple[str, str, int, int]]:
    """Write one ``[[edit]]``'s deltas into ``shot.camera`` IN PLACE. Returns the change log
    ``[(section, field, old, new)]``. Refuses every clock key (constraint 1) and every field the Code's
    flags say is not present (writing a field that is not there would silently corrupt the NEXT field,
    which is exactly the class of bug a same-length splice would not catch)."""
    code = shot.camera["sequences"][tgt.seq_index][tgt.code_index]
    block = code["block"]
    fmap = code_field_offsets(code["flags"])
    log: List[Tuple[str, str, int, int]] = []
    for section, sub in _SECTIONS.items():
        vals = edit.get(section)
        if vals is None:
            continue
        if not isinstance(vals, dict):
            raise RescoreError("[[edit]].%s must be a table of field = value" % section)
        if sub not in fmap:
            raise RescoreError(
                "the keyframe at frame %d of shot %s sequence%d has no %s sub-block (Code flags "
                "%#06x). Read the read-out and pick a keyframe that carries one."
                % (tgt.local_frame, tgt.shot_letter, tgt.seq_index, section, code["flags"]))
        base, size = fmap[sub]
        for k, v in vals.items():
            why = _REFUSED.get((section, k))
            if why:
                raise RescoreError("[[edit]].%s.%s is refused by the content rescore: %s"
                                   % (section, k, why))
            if section in ("camera", "target"):
                if k not in POSE_FIELDS:
                    raise RescoreError("unknown pose field %r (have %s)"
                                       % (k, ", ".join(sorted(POSE_FIELDS))))
                off, width = base + POSE_FIELDS[k], 1
            elif section == "focal":
                if k not in FOCAL_FIELDS:
                    raise RescoreError("unknown focal field %r (have %s)"
                                       % (k, ", ".join(sorted(FOCAL_FIELDS))))
                rel, width = FOCAL_FIELDS[k]
                off = base + rel
            else:
                if k not in MOVE_FIELDS:
                    raise RescoreError("unknown movement field %r (have %s)"
                                       % (k, ", ".join(sorted(MOVE_FIELDS))))
                rel, width = MOVE_FIELDS[k]
                off = base + rel
            iv = int(v)
            lim = 1 << (8 * width)
            if not 0 <= iv < lim:
                raise RescoreError("[[edit]].%s.%s = %d is out of range for a %d-byte field (0..%d)"
                                   % (section, k, iv, width, lim - 1))
            old = int.from_bytes(block[off:off + width], "little")
            block = _patch_bytes(block, off, iv.to_bytes(width, "little"))
            log.append((section, k, old, iv))
    code["block"] = block
    return log


# ============================================================ (4) the same-length splice
@dataclass
class Splice:
    lo: int
    hi: int
    old: bytes
    new: bytes

    @property
    def diff_offsets(self) -> List[int]:
        return [i for i in range(len(self.old)) if self.old[i] != self.new[i]]


def rescore_block(shot: "W.Shot") -> Splice:
    """Re-serialise the edited camera and REFUSE anything that is not a same-length in-place splice.

    This is an assertion and not a hope because a camera sub-file's length is the delta to the NEXT id-2
    directory entry and the slack is 0-2 bytes: a longer block would force an id-2 directory rewrite,
    which shifts every later sub-file and can break the native walker's sector sum."""
    new = W.serialize_camera_block(shot.camera)
    if len(new) != len(shot.block):
        raise RescoreError(
            "the rescored block is %d B but the stock block is %d B. A camera sub-file's length is "
            "fixed by the next id-2 directory entry (slack is 0-2 B corpus-wide), so only a "
            "SAME-SIZE splice is legal here. Adding or removing a keyframe needs an id-2 directory "
            "writer, which this lane does not have." % (len(new), len(shot.block)))
    return Splice(shot.lo, shot.hi, shot.block, new)


def splice_container(blob: bytes, splices: Sequence[Splice]) -> bytes:
    out = bytearray(blob)
    for sp in splices:
        if bytes(out[sp.lo:sp.hi]) != sp.old:
            raise RescoreError("splice at %#x no longer matches the bytes it was derived from "
                               "(overlapping edits?)" % sp.lo)
        out[sp.lo:sp.hi] = sp.new
    if len(out) != len(blob):                                    # belt and braces
        raise RescoreError("container length changed: %d -> %d" % (len(blob), len(out)))
    return bytes(out)


# ============================================================ (5) the alternates check
@dataclass
class AlternatesVerdict:
    n_sequences: int
    identical_to_first: List[bool]
    edited: List[int]

    @property
    def has_alternates(self) -> bool:
        return self.n_sequences > 1

    @property
    def alternates_differ(self) -> bool:
        return any(not same for same in self.identical_to_first[1:])

    @property
    def safe(self) -> bool:
        """A one-track edit is safe iff there is only one track, or the alternates are byte-identical to
        it, or every track was edited."""
        if not self.has_alternates or not self.alternates_differ:
            return True
        return len(set(self.edited)) == self.n_sequences

    def line(self) -> str:
        if not self.has_alternates:
            return ("1 sequence declared -- no alternate takes, so the bit-3 selector has nothing to "
                    "choose between and the edited track is the only track that can play")
        if not self.alternates_differ:
            return ("%d sequences declared but every alternate is BYTE-IDENTICAL to sequence0 -- "
                    "whichever the selector picks is the same camera move" % self.n_sequences)
        return ("%d sequences declared with GENUINELY DIFFERENT alternates; edited %s"
                % (self.n_sequences, sorted(set(self.edited)) or "none"))


def alternates_signature(shot: "W.Shot") -> List[bool]:
    """``[True] + [track i is byte-identical to track 0]`` -- MUST be taken BEFORE any edit.

    Taken afterwards it is a lie in the most dangerous direction: editing track 0 of a block whose
    alternates really WERE identical makes them look "genuinely different", and the trap check would then
    wave through exactly the one-track edit it exists to refuse."""
    seqs = shot.camera["sequences"]
    return [True] + [camera_codec.serialize_sequence(seqs[i]) ==
                     camera_codec.serialize_sequence(seqs[0])
                     for i in range(1, len(seqs))]


def check_alternates(signature: Sequence[bool], edited_seq_ids: Sequence[int]) -> AlternatesVerdict:
    return AlternatesVerdict(len(signature), list(signature), list(edited_seq_ids))


# ============================================================ (6) the self-check
def block_invariants(blob: bytes, arc: "W.Id2Archive", idx: int, block: bytes) -> Dict[str, bool]:
    """The four camera-block invariants, re-asserted on a block we WROTE."""
    flags = struct.unpack_from("<H", block, 0)[0]
    names = [n for b, n in W.OUTER_GROUPS[:4] if flags & b]
    if flags & 0xF0:
        names.append("anchors")
    n = len(names)
    offs = [struct.unpack_from("<H", block, 2 + 2 * i)[0] for i in range(n)]
    lo, hi = arc.bounds(idx)
    last_entry = max((v for v in arc.entries if 0 <= v < arc.size), default=0)
    return {
        "i1_first_offset_is_table_end": bool(offs) and offs[0] == 2 + 2 * n,
        "i2_offsets_strictly_increasing": all(b > a for a, b in zip(offs, offs[1:])),
        "i3_last_group_is_not_a_sequence": bool(names) and names[-1] in ("selector", "anchors"),
        "i4_block_is_not_the_last_subfile": (hi - arc.base) < arc.size and
                                            (lo - arc.base) < last_entry,
    }


@dataclass
class SelfCheck:
    header_ok: bool
    cursor_end: int
    size: int
    roundtrip_ok: int
    roundtrip_total: int
    invariants: Dict[str, bool]
    directory_identical: bool
    changed_offsets: List[int]

    @property
    def ok(self) -> bool:
        return (self.header_ok and self.roundtrip_ok == self.roundtrip_total
                and all(self.invariants.values()) and self.directory_identical)


def self_check(orig: bytes, patched: bytes, source: str,
               targets: Sequence[Target]) -> SelfCheck:
    """Re-parse the container we just wrote and re-run the whole read path over it.

    Not "it built" -- the extractor's own gate, on our bytes: the native walker's sector sum still lands
    (``cursor_end == size``), every camera block in the container still round-trips byte-exact through
    the unmodified codec, the four invariants still hold on the block we edited, and the id-2 directory
    is untouched."""
    header_ok, cursor_end = True, 0
    try:
        c = EC.parse_header(patched, strict=True)
        cursor_end = c.cursor_end
    except EC.ContainerError:                                    # pragma: no cover
        header_ok, c = False, EC.parse_header(patched, strict=False)
        cursor_end = c.cursor_end
    ex2 = W.extract_shots(patched, source)
    ok = sum(1 for s in ex2.shots if s.roundtrip()[0])
    inv: Dict[str, bool] = {}
    for t in targets:
        arc = W.id2_directory(patched, c, t.shot.slot)
        blk = bytes(patched[t.shot.lo:t.shot.hi])
        for k, v in block_invariants(patched, arc, t.shot.index, blk).items():
            inv[k] = inv.get(k, True) and v
    co = EC.parse_header(orig, strict=False)
    dir_same = True
    for slot in sorted({t.shot.slot for t in targets}):
        a = W.id2_directory(orig, co, slot)
        b = W.id2_directory(patched, c, slot)
        dir_same = dir_same and a is not None and b is not None and \
            a.entries == b.entries and a.base == b.base and a.size == b.size
    changed = [i for i in range(len(orig)) if orig[i] != patched[i]]
    return SelfCheck(header_ok, cursor_end, len(patched), ok, len(ex2.shots), inv,
                     dir_same, changed)


# ============================================================ (7) the spec
def _unknown(where: str, got, known) -> None:
    """Refuse an unrecognised key. A spec key the reader ignores is a spec that does not say what its
    author thinks it says -- and for ``expect_sha256`` specifically, a typo would fail OPEN."""
    bad = sorted(k for k in got if k not in known)
    if bad:
        raise RescoreError("%s: unknown key(s) %s. Known keys: %s. (A key this reader ignores is a "
                           "line of the spec that does nothing -- most dangerously a mistyped "
                           "`expect_sha256`, which would silently drop the drift guard.)"
                           % (where, ", ".join(repr(b) for b in bad), ", ".join(sorted(known))))


def load_spec(path) -> dict:
    """Parse and VALIDATE a rescore spec toml. Every table and key is checked; unknown keys refuse."""
    with open(path, "rb") as fh:
        spec = tomllib.load(fh)
    _unknown("%s top level" % path, spec, _SPEC_KEYS)
    r = spec.get("rescore")
    if not isinstance(r, dict):
        raise RescoreError("%s has no [rescore] table" % path)
    _unknown("%s [rescore]" % path, r, _RESCORE_KEYS)
    if "effect" not in r:
        raise RescoreError("[rescore] needs `effect` (the stock ef### number)")
    ack = r.get("acknowledge_dynamic_ops", False)
    if not isinstance(ack, bool):
        raise RescoreError("[rescore].acknowledge_dynamic_ops must be a BOOLEAN (true/false), not "
                           "%r. A safety acknowledgement must be stated, never inferred from a "
                           "truthy string." % (ack,))
    edits = spec.get("edit")
    if not edits:
        raise RescoreError("%s declares no [[edit]] -- nothing to rescore" % path)
    if not isinstance(edits, list):
        raise RescoreError("[[edit]] must be an array of tables")
    for i, e in enumerate(edits):
        if not isinstance(e, dict):
            raise RescoreError("[[edit]] #%d is not a table" % i)
        _unknown("%s [[edit]] #%d" % (path, i), e, _EDIT_KEYS)
    return spec


@dataclass
class Build:
    spec_path: str
    effect: int
    label: str
    source: str
    sha_in: str
    sha_out: str
    orig: bytes = field(repr=False)
    patched: bytes = field(repr=False)
    splices: List[Splice] = field(repr=False)
    changes: List[Tuple[str, str, str, int, int]] = field(default_factory=list)
    verdicts: List[Tuple[str, AlternatesVerdict]] = field(default_factory=list)
    check: Optional[SelfCheck] = None
    #: the container's runtime-chosen camera ops, and whether the spec acknowledged them
    dynamic: Tuple["W.CameraOp", ...] = ()
    acknowledged: bool = False
    #: which drift guard actually applied. Reported honestly: an effect with no entry in
    #: ``EXPECTED_STOCK_SHA`` is still GUARDED when its own spec pins ``expect_sha256`` -- and on a
    #: generalised tool that is the normal case, so "unguarded" must not be printed for it.
    guard: str = "none -- UNGUARDED"


def _ack_flag(r: dict) -> bool:
    """``acknowledge_dynamic_ops``, refusing anything that is not literally ``true``/``false``.

    Enforced HERE and not only in :func:`load_spec` because :func:`build_patched` also takes in-memory
    specs (a gate runner's synthetic containers, the tests) -- a law checked on only one of two entry
    paths is a law with a hole in it."""
    ack = r.get("acknowledge_dynamic_ops", False)
    if not isinstance(ack, bool):
        raise RescoreError("[rescore].acknowledge_dynamic_ops must be a BOOLEAN (true/false), not "
                           "%r. A safety acknowledgement must be stated, never inferred from a "
                           "truthy string." % (ack,))
    return ack


def build_patched(spec: dict, spec_path: str = "?", game=None,
                  blob: Optional[bytes] = None) -> Build:
    """The whole offline half: read the install, apply every ``[[edit]]``, splice, self-check.

    ``blob`` supplies the container directly and skips the install read -- the entry point tests and
    gate runners use with a synthetic container. The drift guard, the disclosure and the self-check all
    still run, because a law that only holds on one of two entry paths is not a law.
    """
    r = spec["rescore"]
    ef_id = int(r["effect"])
    label = str(r.get("label") or ("ef%03d" % ef_id))
    if blob is None:
        blob, source = read_stock_effect(ef_id, game)
    else:
        source = "(caller-supplied bytes)"
    sha_in = drift_guard(ef_id, blob, r.get("expect_sha256"))
    guard = ("the spec's own expect_sha256 -- MATCHES" if r.get("expect_sha256") else
             ("REGISTERED in EXPECTED_STOCK_SHA -- MATCHES" if ef_id in EXPECTED_STOCK_SHA
              else "none -- UNGUARDED (this spec pins no expect_sha256)"))
    src_name = "ef%03d" % ef_id
    ex = W.extract_shots(blob, src_name)

    # THE DYNAMIC-OP DISCLOSURE. Before a single byte is resolved: a container whose camera ops are
    # chosen from a runtime table cannot have its edit's reachability proven offline, so the author must
    # SAY SO in the spec. Refused in BOTH directions -- an unacknowledged risk, and an acknowledgement
    # of a risk this container does not carry (a spec copied from another effect).
    dyn = dynamic_ops(ex)
    ack = _ack_flag(r)
    if dyn and not ack:
        raise RescoreError(
            "THE DYNAMIC-OP DISCLOSURE: %s\nAdd `acknowledge_dynamic_ops = true` to [rescore] to "
            "state you have read this and will prove the reframe by an in-game cast across varied "
            "battle conditions. The effect this tool was first proven on has ZERO such ops, so that "
            "proof's offline completeness claim does NOT carry to this container."
            % "\n".join(dynamic_disclosure(ef_id, ex)))
    if ack and not dyn:
        raise RescoreError(
            "[rescore].acknowledge_dynamic_ops = true, but ef%03d runs NO runtime-chosen camera op "
            "(%d camera op(s), all statically resolved). A safety acknowledgement that was never "
            "true for this container is a spec copied from another effect -- remove the key, or "
            "you are re-reading a disclosure that does not describe these bytes."
            % (ef_id, len(ex.walk.ops)))

    splices: List[Splice] = []
    changes: List[Tuple[str, str, str, int, int]] = []
    verdicts: List[Tuple[str, AlternatesVerdict]] = []
    targets: List[Target] = []
    by_shot: Dict[Tuple[int, int], List[int]] = {}
    touched: Dict[Tuple[int, int], "W.Shot"] = {}
    signatures: Dict[Tuple[int, int], List[bool]] = {}

    # PASS 1 -- resolve every edit and snapshot each target block's alternates signature BEFORE a single
    # byte moves (see ``alternates_signature``: taken after, the check inverts).
    plan: List[Tuple[dict, List[Target]]] = []
    for edit in spec["edit"]:
        tg = resolve_targets(ex, edit)
        for t in tg:
            signatures.setdefault(t.shot.key, alternates_signature(t.shot))
        plan.append((edit, tg))

    # PASS 2 -- apply.
    for edit, tg in plan:
        for t in tg:
            log = apply_edit(t.shot, t, edit)
            if not log:
                raise RescoreError("[[edit]] on shot %s frame %s changes nothing -- name at least "
                                   "one of %s" % (t.shot_letter, t.local_frame,
                                                  ", ".join(sorted(_SECTIONS))))
            for section, k, old, new in log:
                changes.append(("%s f%d seq%d" % (t.shot_letter, t.local_frame, t.seq_index),
                                section, k, old, new))
            by_shot.setdefault(t.shot.key, []).append(t.seq_index)
            touched[t.shot.key] = t.shot
        targets.extend(tg)

    for key, shot in touched.items():
        v = check_alternates(signatures[key], by_shot[key])
        letter = next(t.shot_letter for t in targets if t.shot.key == key)
        verdicts.append((letter, v))
        if not v.safe:
            raise RescoreError(
                "THE THREE-SEQUENCE TRAP: shot %s %s. Edit every track (`all_sequences = true`) or "
                "prove which one the bit-3 selector picks -- a one-track edit here produces a cast "
                "that may look completely unchanged." % (letter, v.line()))
        splices.append(rescore_block(shot))

    patched = splice_container(blob, splices)
    chk = self_check(blob, patched, src_name, targets)
    if not chk.ok:
        raise RescoreError("SELF-CHECK FAILED: header_ok=%s roundtrip=%d/%d invariants=%s dir=%s"
                           % (chk.header_ok, chk.roundtrip_ok, chk.roundtrip_total,
                              chk.invariants, chk.directory_identical))
    return Build(spec_path, ef_id, label, source, sha_in,
                 hashlib.sha256(patched).hexdigest(), blob, patched, splices,
                 changes, verdicts, chk, tuple(dyn), ack, guard)


# ============================================================ (8) staging
def modfilelist_refusal(mod_root) -> Optional[str]:
    """The refusal text if ``mod_root`` carries a ``ModFileList.txt``, else ``None``.

    THE SILENT-FALLBACK LAW: when a mod folder has a ModFileList.txt, ``TryFindAssetInModOnDisc`` TRUSTS
    that list and never calls ``File.Exists``, so any file the list omits is INVISIBLE -- and because
    ``SFX.Play`` suppresses its missing-asset error, the cast simply plays the stock camera with nothing
    logged anywhere. "Nothing changed" would be the only symptom.

    Appending our line to the list would work, but it edits a file whose format this lane does not own,
    in a folder somebody else's tooling maintains. So the DEPLOY path refuses and says what to do,
    rather than half-owning a registry. (Creating one is never an option in any path -- that would make
    every OTHER file in the folder invisible at a stroke.)
    """
    lp = Path(mod_root) / "ModFileList.txt"
    if not lp.exists():
        return None
    return ("REFUSING to deploy into %s: it has a ModFileList.txt.\n"
            "  When that file exists the engine TRUSTS it and never probes the folder, so an "
            "unlisted override is invisible -- and SFX.Play suppresses the missing-asset error, so "
            "the stock camera would simply play with nothing logged. 'Nothing changed' would be the "
            "only symptom you ever saw.\n"
            "  Deploy into a mod folder that has no list, or add this line to %s yourself:\n"
            "    %s" % (mod_root, lp, "specialeffects/<the effect id>"))


def stage(b: Build, mod_root=None, work_dir=None, game_root=None,
          allow_install: bool = False, refuse_modfilelist: bool = False) -> dict:
    """Write the override + the revert script. Returns a dict describing what landed.

    ``mod_root=None`` resolves :func:`default_mod_root` FOR THIS BUILD'S EFFECT, so two effects staged
    in one session can never share a kit.

    STAGE by default: a repo / mod-asset tree is refused ALWAYS, and a destination inside the game
    install is refused unless ``allow_install`` is passed. That flag is the live deploy -- deliberately
    not the default, because a build agent writing into a shared install by accident is exactly the
    class of thing several concurrent worktrees must not do.

    ``refuse_modfilelist`` turns :func:`modfilelist_refusal` into a hard refusal BEFORE any write. It is
    off for staging (a scratch folder's list, if any, is the caller's own) and ON for the deploy path,
    where a list belongs to somebody else's tooling.
    """
    if mod_root is None:
        # The DEFAULT is the one destination this module chooses rather than accepts, so it gets the
        # full local-only guard (repo + mod-asset tree + the resolved install), not just the two
        # clauses an explicit caller-supplied path is held to.
        mod_root = export.assert_local_only(default_mod_root(b.effect))
    mod_root = _refuse_repo_path(mod_root)
    if not allow_install:
        mod_root = _refuse_install_path(mod_root, game_root)
    if refuse_modfilelist:
        why = modfilelist_refusal(mod_root)
        if why:
            raise RescoreError(why)
    # COUPLED, deliberately: an explicit ``work_dir`` still wins, but its DEFAULT is derived from the
    # resolved mod root rather than from a module constant. A module-constant default means pointing
    # the mod root at effect B still writes effect B's revert script into effect A's kit -- a correct
    # flag was not enough to keep two effects apart.
    work_dir = Path(work_dir or Path(mod_root).parent)
    _refuse_repo_path(work_dir)
    dest = Path(mod_root).joinpath(*MOD_SUBPATH.split("/"), "ef%03d" % b.effect)
    if dest.suffix:                                              # pragma: no cover
        raise RescoreError("the override must be EXTENSIONLESS (LoadFromDisc reads the raw path)")
    ledger = Ledger(Path(work_dir) / "backups", mod_root=mod_root)
    sha = ledger.write_bytes(dest, b.patched)
    listed = ledger.add_list_line(Path(mod_root) / "ModFileList.txt",
                                  "%s/ef%03d" % (MOD_SUBPATH.split("/", 1)[1].lower(), b.effect))
    revert = ledger.write_revert_script(Path(work_dir), "%d" % b.effect)
    return {"dest": str(dest), "sha256": sha, "bytes": len(b.patched),
            "mod_root": str(mod_root), "revert_script": str(revert),
            "modfilelist_updated": listed,
            "modfilelist_present": (Path(mod_root) / "ModFileList.txt").exists()}


def verify(b: Build, mod_root=None) -> dict:
    """Compare what is ON DISC against a fresh rebuild of the same spec.

    The point is not "did the file get written" but "are the bytes at the override path the bytes this
    spec produces from THIS install today" -- so it re-derives rather than trusting a recorded hash. A
    missing destination and a divergent one are different verdicts and are reported as such.
    """
    dest = Path(mod_root or default_mod_root(b.effect)).joinpath(*MOD_SUBPATH.split("/"),
                                                                "ef%03d" % b.effect)
    if not dest.exists():
        return {"ok": False, "reason": "nothing staged at %s" % dest, "dest": str(dest),
                "bytes": 0, "sha256": None, "expected_sha256": b.sha_out}
    on_disc = dest.read_bytes()
    got = hashlib.sha256(on_disc).hexdigest()
    same = on_disc == b.patched
    return {"ok": same,
            "reason": ("matches the rebuild" if same else
                       "DIVERGES from the rebuild -- the staged file is not what this spec builds "
                       "from this install now (a stale build, a hand edit, or another tool wrote it)"),
            "dest": str(dest), "bytes": len(on_disc), "sha256": got,
            "expected_sha256": b.sha_out}


# ============================================================ (9) reporting
def describe(b: Build) -> List[str]:
    """The plan/build report -- the delta, the splice, and every gate's verdict, in one screen."""
    L = ["ef%03d  %s" % (b.effect, b.label),
         "  stock source : %s" % b.source,
         "  stock sha256 : %s  (drift guard %s)" % (b.sha_in, b.guard),
         "  rescored sha : %s" % b.sha_out,
         "  container    : %d B in, %d B out (same length required)" % (len(b.orig), len(b.patched)),
         ""]
    L.append("  THE DELTA")
    for who, section, k, old, new in b.changes:
        L.append("    %-14s %-12s %-12s %6d -> %-6d  (%+d)" % (who, section, k, old, new, new - old))
    L.append("")
    L.append("  THE SPLICE")
    for sp in b.splices:
        offs = sp.diff_offsets
        L.append("    block @file %#x..%#x (%d B): %d byte(s) differ, at block-relative %s"
                 % (sp.lo, sp.hi, len(sp.old), len(offs), offs))
    L.append("")
    L.append("  THE THREE-SEQUENCE CHECK")
    for letter, v in b.verdicts:
        L.append("    shot %s: %s" % (letter, v.line()))
    L.append("")
    L.append("  THE DYNAMIC-OP DISCLOSURE")
    if not b.dynamic:
        L.append("    0 runtime-chosen camera ops -- every camera this container plays resolves to "
                 "a literal sub-file offline, so the edited block's reachability IS enumerable")
    else:
        L.append("    ACKNOWLEDGED by the spec -- %d runtime-chosen op(s); reachability is NOT "
                 "enumerable offline and only an in-game cast across varied battle conditions "
                 "closes it:" % len(b.dynamic))
        for o in b.dynamic:
            L.append("      %s @file %#x chunk %d arg1 %d seq tick %d"
                     % (o.kind, o.at, o.chunk_slot, o.arg1, o.seq_tick))
    if b.check:
        c = b.check
        L.append("")
        L.append("  SELF-CHECK")
        L.append("    container header re-parses strict : %s (cursor_end %#x == size %#x)"
                 % (c.header_ok, c.cursor_end, c.size))
        L.append("    every camera block round-trips     : %d/%d byte-exact"
                 % (c.roundtrip_ok, c.roundtrip_total))
        L.append("    id-2 directory untouched           : %s" % c.directory_identical)
        for k, v in sorted(c.invariants.items()):
            L.append("    %-34s : %s" % (k, v))
        L.append("    container bytes changed            : %d (at %s)"
                 % (len(c.changed_offsets),
                    ", ".join("%#x" % o for o in c.changed_offsets[:16])
                    + (" ..." if len(c.changed_offsets) > 16 else "")))
    return L


# ============================================================ (10) THE SCAFFOLD
#: the levers the scaffold may pre-declare, in preference order. H FIRST, deliberately: THE
#: EFFECT-OWNED SCENERY LAW -- focal distance is the safest lever, because it reframes without moving
#: the eye, so it exposes less of the effect's own authored set than a pose change does.
_LEVERS: Tuple[Tuple[str, str, Tuple[str, ...]], ...] = (
    ("focal", "focal", ("distance",)),
    ("campos", "camera", ("orientation", "roll")),
)


@dataclass
class PhaseRow:
    """One recovered program phase placed on the SEQUENCE clock, so it can be read against a shot's
    tick span. Only ever present when a caller supplied recovered machines (see :func:`shot_rows`)."""
    image: str
    state: int
    start: int
    end: Optional[int]
    roles: Tuple[str, ...]

    @property
    def draws_set(self) -> bool:
        """The reframe-budget test: a phase that draws effect models has the effect's OWN scenery on
        screen, so a reframe can walk the camera off the edge of the authored set."""
        return "draws effect models" in self.roles

    def overlaps(self, lo: int, hi: int) -> bool:
        return (self.end is None or self.end >= lo) and self.start <= hi


@dataclass
class ShotRow:
    letter: str
    slot: int
    subfile: int
    kind: str
    seq_tick: int
    span: int
    n_sequences: int
    signature: Tuple[bool, ...]
    n_keyframes: int
    frames: Tuple[Tuple[int, int], ...]      # (local frame, how many Codes sit on it) in sequence0
    focal_frames: Tuple[int, ...]
    phases: Tuple[PhaseRow, ...]

    @property
    def alternates_differ(self) -> bool:
        return any(not s for s in self.signature[1:])

    @property
    def draws_set(self) -> bool:
        return any(p.draws_set for p in self.phases)


@dataclass
class ScaffoldTarget:
    """The one ``[[edit]]`` the scaffold pre-declares, and whether it is an IDENTITY."""
    letter: str
    slot: int
    subfile: int
    frame: int
    occurrence: int
    ambiguous: bool
    section: str
    all_sequences: bool
    values: Dict[str, int]                   # sequence0's own values -- the identity, if there is one
    per_track: Dict[int, Dict[str, int]]     # every target track's values (== ``values`` if identity)
    identity: bool
    why_not: str = ""


@dataclass
class Scaffold:
    effect: int
    source: str
    sha256: str
    shots: Tuple[ShotRow, ...]
    dynamic: Tuple["W.CameraOp", ...]
    disclosure: Tuple[str, ...]
    target: ScaffoldTarget
    quoted: Tuple[Tuple[str, int], ...]      # every STOCK VALUE the emitted toml names
    text: str = ""


def _phase_rows(ex: "W.Extract", machines=()) -> List[PhaseRow]:
    """Recovered phases on the sequence clock -- :func:`~ff9mapkit.summons.camera.merged_timeline`'s own
    derivation, reused. A phase boundary is ``program_start_tick + phase.start_tick``, where the program
    start is the ``0x80+N`` op's own tick in the SAME sequence walk. Like that function this keys on
    program 0 of the machine's chunk; a machine whose chunk never ran a program 0 contributes nothing
    rather than being placed at a guessed origin.

    ``machines`` defaults to none, and none is the kit's normal state: recovering them needs a MIPS
    disassembler this package does not ship. The cost is one ADVISORY column (the reframe budget), and
    it is reported as UNKNOWN rather than as loose -- an absent judgement, not a favourable one.
    """
    out: List[PhaseRow] = []
    for sm in (machines or ()):
        slot = W._machine_slot(sm)
        start = ex.walk.program_starts.get((slot, 0))
        if start is None:
            continue
        for ph in sm.phases:
            end = None if ph.ticks is None else start + ph.start_tick + ph.ticks - 1
            out.append(PhaseRow(str(sm.image), int(ph.state), start + ph.start_tick, end,
                                tuple(ph.case.roles())))
    out.sort(key=lambda p: (p.start, p.image, p.state))
    return out


def _codes_at(shot: "W.Shot", seq: int, frame: int) -> List[int]:
    seqs = shot.camera["sequences"]
    if seq >= len(seqs):
        return []
    return [i for i, c in enumerate(seqs[seq])
            if c.get("frame") and W.frame_number(c["frame"]) == frame]


def shot_rows(ex: "W.Extract", machines=()) -> List[ShotRow]:
    """The shot table a scaffold prints -- STRUCTURE ONLY (letters, addresses, ticks, counts, frames).

    Deliberately not a keyframe dump: a decoded stock listing is not a committable artefact, and
    :func:`~ff9mapkit.summons.camera.read_out` already prints one, to stdout. The only stock VALUES that
    reach a generated file are the ones its own declared edit writes (:data:`SCAFFOLD_QUOTE_BUDGET`).
    """
    phases = _phase_rows(ex, machines)
    rows: List[ShotRow] = []
    for i, s in enumerate(ex.shots):
        ks = W.keyframes(s.camera, 0)
        span = W.shot_span(s.camera)
        lo = s.op.seq_tick
        hi = lo + max(0, span - 1)
        seen: Dict[int, int] = {}
        for k in ks:
            seen[k.local_frame] = seen.get(k.local_frame, 0) + 1
        rows.append(ShotRow(
            letter=W._SHOT_LETTERS[i % 26], slot=s.slot, subfile=s.index, kind=s.op.kind,
            seq_tick=lo, span=span, n_sequences=len(s.camera["sequences"]),
            signature=tuple(alternates_signature(s)), n_keyframes=len(ks),
            frames=tuple(sorted(seen.items())),
            focal_frames=tuple(sorted({k.local_frame for k in ks if "focal" in k.fields})),
            phases=tuple(p for p in phases if p.overlaps(lo, hi))))
    return rows


def choose_target(ex: "W.Extract") -> ScaffoldTarget:
    """Pick the ONE keyframe the scaffold pre-declares, and decide whether it is an identity.

    Preference order is the law's, not convenience: the first shot carrying a **focal** wins, because H
    is the lever THE EFFECT-OWNED SCENERY LAW names as safest and the only camera value an in-game
    capture observes directly. Only if NO shot in the container carries a focal does the scaffold fall
    back to a pose pair.

    An IDENTITY target writes back the value already there, so the generated spec builds a container
    BYTE-IDENTICAL to stock -- the whole resolution path proven before the author changes a thing. That
    claim is only sound when every track this edit fans across holds the SAME value, so when the tracks
    disagree the scaffold says so and leaves the lever commented out rather than shipping an "identity"
    that silently rewrites two of three alternate takes.
    """
    if not ex.shots:
        raise RescoreError(
            "no statically-resolved camera shot in this container (%d camera op(s), %d dynamic). "
            "There is nothing for a rescore spec to address: an edit is placed by (chunk, sub-file) "
            "and this container names none literally."
            % (len(ex.walk.ops), len(dynamic_ops(ex))))
    rows = shot_rows(ex)
    pick = None
    for sub, section, keys in _LEVERS:
        for i, s in enumerate(ex.shots):
            for k in W.keyframes(s.camera, 0):
                if sub in k.fields:
                    pick = (i, s, rows[i], k, sub, section, keys)
                    break
            if pick:
                break
        if pick:
            break
    if pick is None:
        have = sorted({f for s in ex.shots for k in W.keyframes(s.camera, 0) for f in k.fields})
        raise RescoreError(
            "no keyframe in this container carries a focal or a camera pose, so there is no lever "
            "for a rescore to pull. %d shot(s) resolve; between them their Codes carry only %s. "
            "(A minority of stock containers are of this class -- a camera block whose only Code is "
            "the trailing `unk6` marker. There is nothing to reframe; this is a refusal, not a "
            "failure.)" % (len(ex.shots), ", ".join(have) or "(no sub-block at all)"))
    i, shot, row, kf, sub, section, keys = pick

    hits = _codes_at(shot, 0, kf.local_frame)
    seq0 = shot.camera["sequences"][0]
    occ = next(j for j, ci in enumerate(hits)
               if sub in camera_codec.split_code(seq0[ci]["flags"], seq0[ci]["block"]))
    fan = row.alternates_differ
    seq_ids = list(range(row.n_sequences)) if fan else [0]

    per: Dict[int, Dict[str, int]] = {}
    why = ""
    for si in seq_ids:
        h = _codes_at(shot, si, kf.local_frame)
        if occ >= len(h):
            why = ("sequence%d has only %d Code(s) at local frame %d, so occurrence %d does not "
                   "exist there" % (si, len(h), kf.local_frame, occ))
            break
        c = shot.camera["sequences"][si][h[occ]]
        fields = camera_codec.split_code(c["flags"], c["block"])
        if sub not in fields:
            why = ("sequence%d's Code at local frame %d occurrence %d carries no %s sub-block"
                   % (si, kf.local_frame, occ, sub))
            break
        k2 = W.Keyframe(kf.local_frame, 0, c["flags"], fields)
        got = k2.focal() if sub == "focal" else k2.pose(sub)
        per[si] = {name: int(got[name]) for name in keys}
    vals = per.get(0, {})
    identity = bool(per) and not why and all(v == vals for v in per.values())
    if not why and not identity:
        why = ("the %d target tracks do not hold the same %s value(s), so no single number written "
               "here is an identity on all of them" % (len(per), section))
    return ScaffoldTarget(letter=row.letter, slot=shot.slot, subfile=shot.index,
                          frame=kf.local_frame, occurrence=occ, ambiguous=len(hits) > 1,
                          section=section, all_sequences=fan, values=vals, per_track=per,
                          identity=identity, why_not=why)


def _quote_check(quoted: Sequence[Tuple[str, int]]) -> None:
    """The provenance ceiling, enforced at the write site rather than promised in a docstring."""
    if len(quoted) > SCAFFOLD_QUOTE_BUDGET:
        raise RescoreError(
            "the scaffold would quote %d stock values (%s) but the budget is %d. A generated spec is "
            "an AUTHORED file -- it may name the values its own declared edit writes and nothing "
            "more; a decoded stock listing belongs on stdout, not in a repo."
            % (len(quoted), ", ".join(n for n, _v in quoted), SCAFFOLD_QUOTE_BUDGET))


def scaffold(ef_id: int, blob: bytes, source: str, machines=()) -> Scaffold:
    """Derive a complete, guarded starter spec for ANY stock effect -- zero hand-typed offsets."""
    src_name = "ef%03d" % ef_id
    ex = W.extract_shots(blob, src_name)
    rows = shot_rows(ex, machines)
    tgt = choose_target(ex)
    dyn = dynamic_ops(ex)
    sha = hashlib.sha256(blob).hexdigest()

    quoted: List[Tuple[str, int]] = []
    if tgt.identity:
        quoted = [(k, tgt.values[k]) for k in sorted(tgt.values)]
    elif tgt.per_track and len(tgt.per_track) * max(1, len(tgt.values)) <= SCAFFOLD_QUOTE_BUDGET:
        quoted = [("seq%d.%s" % (si, k), v)
                  for si in sorted(tgt.per_track) for k, v in sorted(tgt.per_track[si].items())]
    _quote_check(quoted)

    sc = Scaffold(ef_id, source, sha, tuple(rows), tuple(dyn),
                  tuple(dynamic_disclosure(ef_id, ex)), tgt, tuple(quoted))
    sc.text = _scaffold_text(sc)
    return sc


def _scaffold_text(sc: Scaffold) -> str:
    L: List[str] = []
    A = L.append
    A("# CONTENT RESCORE spec for ef%03d.  GENERATED by:" % sc.effect)
    A("#     ff9mapkit summon-rescore scaffold --ef %d" % sc.effect)
    A("#")
    A("# Every address below was DERIVED from the container, not typed: the shot letter, the")
    A("# (chunk, sub-file) pair, the local frame, the sequence count and the drift hash all come")
    A("# out of the container's own bytes.  What is NOT derived is the ART -- which keyframe to")
    A("# move and how far.  That is yours.")
    A("#")
    A("# WHAT THIS LANE MAY NOT TOUCH, refused at the call site rather than trusted to this comment:")
    A("#   * any DURATION (focal, camera_move, target_move) -- the two clocks stay aligned; a timing")
    A("#     move must carry the program's phase constants with it, which is a different lane;")
    A("#   * any FRAME word -- it carries undecoded marks in its top 3 bits;")
    A("#   * anything that changes the block's BYTE LENGTH -- a camera sub-file's length is the")
    A("#     delta to the next id-2 directory entry and the slack is 0-2 bytes corpus-wide.")
    A("#")
    A("# THE SHOT TABLE -- structure only.  For the full keyframe listing (poses, H, easing) run")
    A("#     ff9mapkit summon-rescore read --ef %d" % sc.effect)
    A("# and read it on stdout: a decoded stock listing is not a committable artefact.")
    A("#")
    for r in sc.shots:
        A("#   shot %s   chunk %d sub-file %-3d  %-12s installs at seq tick %d, span %d local frames"
          % (r.letter, r.slot, r.subfile, r.kind, r.seq_tick, r.span))
        A("#     tracks    : %d sequence(s); %s"
          % (r.n_sequences,
             "no alternate takes -- the bit-3 selector has nothing to choose between"
             if r.n_sequences == 1 else
             ("alternates DIFFER -- a one-track edit here may produce a cast that looks completely "
              "unchanged, so `all_sequences = true` is required" if r.alternates_differ else
              "every alternate is BYTE-IDENTICAL to sequence0 -- whichever the selector picks is "
              "the same move")))
        A("#     keyframes : %d in sequence0, at local frames %s"
          % (r.n_keyframes,
             ", ".join("f%d%s" % (f, " x%d" % n if n > 1 else "") for f, n in r.frames) or "(none)"))
        A("#     focal (H) : %s"
          % (", ".join("f%d" % f for f in r.focal_frames) if r.focal_frames
             else "NONE -- this shot has no projection-distance lever; only a pose edit reaches it"))
        if r.phases:
            A("#     phases live under this shot (recovered state machines on the SAME clock):")
            for p in r.phases:
                A("#       %-12s s%-2d ticks %4d..%-6s %s"
                  % (p.image, p.state, p.start, "term" if p.end is None else p.end,
                     ", ".join(p.roles) or "(no drawing role)"))
            A("#     reframe budget: %s"
              % ("TIGHT -- a phase under this shot DRAWS EFFECT MODELS, so the effect's own scenery "
                 "is on screen and the camera can be walked off the edge of the authored set. "
                 "Prefer H; treat a pose change as high-risk (THE EFFECT-OWNED SCENERY LAW)."
                 if r.draws_set else
                 "looser -- no phase under this shot draws effect models, so less of the effect's "
                 "own set is on screen here. H is still the safer lever."))
        else:
            A("#     phases    : none supplied for this shot. The reframe budget is then UNKNOWN,")
            A("#                 not loose -- judge it from an in-game cast.")
        A("#")
    A("# DYNAMIC (RUNTIME-CHOSEN) CAMERA OPS: %d" % len(sc.dynamic))
    if not sc.dynamic:
        A("#   Every camera op resolves to a literal sub-file index offline, so the set of blocks an")
        A("#   edit can reach IS enumerable from these bytes -- a property most of the corpus lacks.")
    else:
        for ln in sc.disclosure:
            A("#   " + ln)
        A("#   `acknowledge_dynamic_ops` below is pre-seeded FALSE.  The build REFUSES until you")
        A("#   flip it, on purpose: flipping it is the record that you read the paragraph above.")
    A("")
    A("[rescore]")
    A("effect = %d" % sc.effect)
    A('label  = "ef%03d-rescore"' % sc.effect)
    A("# The drift guard: sha256 of the pristine container in the user's OWN install.  A HASH, not")
    A("# data.  If the install is patched, the build refuses rather than splicing a delta into bytes")
    A("# it was never derived against.")
    A('expect_sha256 = "%s"' % sc.sha256)
    if sc.dynamic:
        A("# MUST become `true` to build -- see THE DYNAMIC-OP DISCLOSURE above.")
        A("acknowledge_dynamic_ops = false")
    A("")
    A("")
    t = sc.target
    A("# ---------------------------------------------------------------------------------------")
    A("# THE EDIT.  Pre-aimed at shot %s's %s keyframe -- %s."
      % (t.letter, "first focal-carrying" if t.section == "focal" else "first pose-carrying",
         "H, the safest lever (THE EFFECT-OWNED SCENERY LAW: it reframes without moving the eye)"
         if t.section == "focal" else
         "a pose pair, because no shot here carries a focal"))
    if t.identity:
        A("#")
        A("# THIS IS AN IDENTITY as generated: it writes back the value already there, so `plan`")
        A("# reports 0 changed bytes and `build` produces a container BYTE-IDENTICAL to stock.")
        A("# Run it FIRST -- it proves the whole path resolves (install read, drift guard, shot")
        A("# address, alternates, splice, self-check) before any judgement about art is involved.")
        A("# Then change the number.")
    else:
        A("#")
        A("# NOT AN IDENTITY: %s." % t.why_not)
        A("# The lever is left COMMENTED OUT rather than pre-filled -- a value that is an identity on")
        A("# one track is a real, unjudged change on the others.  Uncomment it and choose knowing")
        A("# that.  (As generated this spec builds nothing: an [[edit]] that names no field is")
        A("# refused, which is the correct outcome for a spec that has not been finished.)")
    A("[[edit]]")
    A('shot     = "%s"' % t.letter)
    A("chunk    = %d" % t.slot)
    A("subfile  = %d" % t.subfile)
    if t.all_sequences:
        A("# the alternate takes DIFFER, so the delta must fan across every track or the selector")
        A("# may play one this edit never touched")
        A("all_sequences = true")
    else:
        A("sequence = 0")
    A("frame    = %d" % t.frame)
    if t.ambiguous:
        A("# local frame %d carries more than one Code (a placement and the move it starts," % t.frame)
        A("# typically) -- `occurrence` says which, and the tool refuses the ambiguity without it.")
        A("occurrence = %d" % t.occurrence)
    body = ", ".join("%s = %d" % (k, t.values[k]) for k in sorted(t.values))
    if t.identity:
        A("%-8s = { %s }" % (t.section, body))
    else:
        pertrack = ("; ".join("seq%d %s" % (si, ", ".join("%s=%d" % kv for kv in
                                                          sorted(t.per_track[si].items())))
                              for si in sorted(t.per_track))
                    if sc.quoted else "read the read-out to see them")
        A("# stock here: %s" % pertrack)
        A("# %-6s = { %s }" % (t.section, body or "... = ..."))
    return "\n".join(L) + "\n"


def scaffold_summary(sc: Scaffold) -> List[str]:
    """What a scaffold prints to the terminal -- the same facts the file carries, in one screen."""
    t = sc.target
    L = ["ef%03d  scaffold" % sc.effect,
         "  read from    : %s" % sc.source,
         "  sha256       : %s" % sc.sha256,
         "  shots        : %d statically resolved, %d runtime-chosen (dynamic)"
         % (len(sc.shots), len(sc.dynamic)),
         ""]
    L.append("  %-5s %-14s %-13s %-7s %-6s %-9s %-9s %s"
             % ("shot", "chunk/subfile", "op", "tick", "span", "tracks", "keyframes", "focal at"))
    for r in sc.shots:
        L.append("  %-5s c%-2d idx%-9d %-13s %-7d %-6d %-9s %-9d %s"
                 % (r.letter, r.slot, r.subfile, r.kind, r.seq_tick, r.span,
                    "%d%s" % (r.n_sequences,
                              " DIFFER" if r.alternates_differ else
                              (" same" if r.n_sequences > 1 else "")),
                    r.n_keyframes,
                    ", ".join("f%d" % f for f in r.focal_frames) or "-"))
    for r in sc.shots:
        if r.phases:
            L.append("  shot %s spans %d phase(s); reframe budget %s"
                     % (r.letter, len(r.phases), "TIGHT (draws effect models)" if r.draws_set
                        else "looser (no effect-model draw)"))
        else:
            L.append("  shot %s spans no supplied phase -- reframe budget UNKNOWN" % r.letter)
    L.append("")
    if sc.dynamic:
        L.append("  THE DYNAMIC-OP DISCLOSURE")
        for ln in sc.disclosure:
            L.append("    " + ln)
        L.append("    -> the scaffold pre-seeds `acknowledge_dynamic_ops = false`; the build REFUSES "
                 "until it is flipped")
    else:
        L.append("  THE DYNAMIC-OP DISCLOSURE: none -- every camera op resolves literally offline")
    L.append("")
    L.append("  THE EDIT it pre-declares: shot %s (c%d idx%d) local frame %d%s, section `%s`%s"
             % (t.letter, t.slot, t.subfile, t.frame,
                " occurrence %d" % t.occurrence if t.ambiguous else "", t.section,
                ", fanned across every track (all_sequences)" if t.all_sequences else ""))
    L.append("    %s" % ("IDENTITY -- as generated it rebuilds the container BYTE-IDENTICAL to stock"
                         if t.identity else "NOT an identity, lever left commented: %s" % t.why_not))
    return L


def write_scaffold(sc: Scaffold, out_path, force: bool = False) -> Path:
    """Write the generated spec. Never over an existing file without being told to: a scaffold is a
    starting point, and silently replacing an author's finished spec with one is the single most
    destructive thing this verb could do."""
    p = Path(out_path)
    if p.exists() and not force:
        raise RescoreError("%s already exists. `scaffold` refuses to overwrite an authored spec -- "
                           "pass --force if you really mean to replace it." % p)
    from .. import fsutil
    p.parent.mkdir(parents=True, exist_ok=True)
    fsutil.atomic_write_text(p, sc.text, encoding="utf-8", newline="\n")
    return p
