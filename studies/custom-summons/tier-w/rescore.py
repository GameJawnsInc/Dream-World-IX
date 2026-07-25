r"""TIER W rung 2 -- THE CONTENT RESCORE: reframe a stock summon's shot, durations UNCHANGED.

    py rescore.py plan   bahamut_rescore.toml        # resolve + print the delta, write nothing
    py rescore.py build  bahamut_rescore.toml        # stage the override + emit the revert script
    py rescore.py verify bahamut_rescore.toml        # X1/X2 against a staged build

WHAT THIS IS
------------
W1 proved the summon camera decodes and re-encodes BYTE-IDENTICAL through the battle
``camera_codec``.  W2 spends that: it reads the target effect out of **the user's own install**,
applies a DECLARATIVE delta expressed in W1's own vocabulary (shot / chunk / sub-file / sequence /
local frame / camera pose / focal H), splices the re-serialised block back at the SAME LENGTH, and
stages the whole container as a mod-folder override.  Nothing stock is ever written into the repo,
and nothing is ever written into the install.

THE THREE HARD CONSTRAINTS, each enforced at the call site (a law in a docstring is a wish)
-------------------------------------------------------------------------------------------
1. **DURATIONS UNCHANGED.**  ``_apply_edit`` REFUSES any key that would move a clock -- a Movement
   ``duration``, a focal ``duration``, a Code ``frame``.  W1's two-clocks law says the camera and
   the program are two clocks the author kept aligned by construction; W2 moves neither.  Retiming
   is W3, and W3 must move the program's phase constants with it.
2. **BYTE LENGTH UNCHANGED.**  W1 section 6: a camera sub-file's length is defined by the NEXT id-2
   directory entry, and 187 of 798 blocks have 0-2 bytes of slack.  ``rescore_block`` asserts
   ``len(new) == len(old)`` before anything is spliced, so the id-2 directory never has to move and
   the native walker's sector sum (``cursor_end == size``) cannot break.
3. **THE FRAME WORD'S HIGH BITS SURVIVE.**  A Code's ``frame`` u16 carries undecoded marks in
   ``0xE000`` (W1 section 2.3).  This module never writes a frame word at all, which is the
   strongest form of preserving them.

THE THREE-SEQUENCE TRAP (W1 section 4.1 / section 6)
----------------------------------------------------
374 of 798 corpus blocks declare three sequences and 332 of those carry genuinely DIFFERENT
alternate takes, chosen at runtime by the bit-3 selector.  Editing one track of such a block
produces a cast that may look unchanged.  ``check_alternates`` reports the verdict for the target
block, and ``build`` REFUSES a single-sequence edit on a block whose alternates differ unless the
spec says ``all_sequences = true`` (which fans the same delta across every declared track).

THE SILENT-FAILURE RISK THIS BUILD IS SHAPED AROUND
---------------------------------------------------
``SFX.Play`` passes ``suppressMissingError = true``, so a wrong override path logs NOTHING and the
stock camera plays.  "Nothing changed" is therefore the symptom of EVERY misresolution -- a wrong
folder, a wrong name, a stray extension, a ModFileList that does not list the file, another mod
folder earlier in ``FolderNames`` shipping its own copy, or the selector picking a track we did not
edit.  That is why the first delta must be deliberately LARGE, and why the report's failure section
enumerates the misresolutions rather than saying "check the log".

PROVENANCE
----------
The stock container is read at RUN TIME from ``resources.assets`` in the user's install (never from
the repo, and never from a previously-written override -- always re-derived, so a Steam/Moguri patch
cannot be silently shadowed forever).  A sha256 DRIFT GUARD (hash only; no stock bytes) refuses a
donor whose install bytes differ from the ones this edit was derived against.  Staged output goes to
a mod root under ``C:\gd\SCRATCH\summon-format\rescore-w2`` by default; ``_refuse_repo_path`` refuses
any destination inside the repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)                                  # studies/custom-summons
_REPO = os.path.dirname(os.path.dirname(_STUDY))                 # <repo>
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_STUDY, "thomas-swap", "disasm"))
sys.path.insert(0, os.path.join(_REPO, "ff9mapkit"))

import ef_container as EC                                        # noqa: E402
import summon_camera as W                                        # noqa: E402
from ff9mapkit.battle import camera_codec as CC                  # noqa: E402

try:                                                             # py3.11+ stdlib, else the backport
    import tomllib as _toml
except ModuleNotFoundError:                                      # pragma: no cover
    import tomli as _toml                                        # type: ignore

#: default staging root -- SCRATCH, never the repo, never the live game folder (W2 stages only)
SCRATCH_ROOT = os.environ.get("FF9_RESCORE_SCRATCH",
                              r"C:\gd\SCRATCH\summon-format\rescore-w2")

#: the on-disc override path the engine's mod pass reads.  ``AssetManager.LoadBytes("SpecialEffects/
#: ef227")`` is NOT "Data/"-prefixed, so ``IsMemoriaAssets`` is false and ``GetBelongingBundleFilename``
#: is "" -- ``LoadBytesMultiple`` falls through to the disc pass, which probes
#: ``GetResourcesAssetsPath(true) + "/" + name`` under each mod folder = ``<mod>/FF9_Data/<name>``.
#: EXTENSIONLESS: ``LoadFromDisc`` reads the raw path, so ``ef227.bytes`` would never be found.
MOD_SUBPATH = "FF9_Data/SpecialEffects"

#: sha256 of the pristine stock container this edit was derived against.  HASH ONLY -- no stock byte
#: ever enters a committable file.  A donor whose install bytes drift is REFUSED, the
#: ``EXPECTED_DONOR_SEQ_SHA`` posture from ``ff9mapkit/summons/deploy.py``.
EXPECTED_STOCK_SHA = {
    227: "fe590d00a01d95c6dc473cee9fea9096b9ded63c3daae3aab693099c6d0ed167",  # Bahamut__Full
}

#: ONE Code's sub-blocks, in ``camera_codec._split_code``'s exact field order.  ``None`` marks a bit
#: that ABORTS the reader (the codec returns early), so nothing after it exists in the block.
_CODE_LAYOUT: Tuple[Tuple[int, Optional[str], int], ...] = (
    (0x0003, "campos", 6), (0x0002, "cammove", 4), (0x0004, None, 0),
    (0x0018, "tgtpos", 6), (0x0010, "tgtmove", 4), (0x0020, None, 0),
    (0x0040, "sign", 2), (0x0200, "unk3", 2), (0x0400, "unk4", 2),
    (0x0800, "focal", 4), (0x1000, "unk5", 4), (0x4000, "setting", 2), (0x8000, "unk6", 4),
)

#: a 6-byte pose, by W1's read-out names
POSE_FIELDS = {"code": 0, "flags": 1, "pitch": 2, "orientation": 3, "roll": 4, "distance": 5}
#: a 4-byte focal: the PROJECTION DISTANCE (H) is the u16 at +2 -- the one lever TIER R's capture
#: observed directly (``H -> 256 @f58`` and friends), so it is the calibrated half of a reframe.
FOCAL_FIELDS = {"duration": (0, 1), "flags": (1, 1), "distance": (2, 2)}
#: a 4-byte movement.  ``duration`` is a CLOCK and is refused at W2 (constraint 1).
MOVE_FIELDS = {"duration": (0, 2), "type": (2, 1), "unknown": (3, 1)}

#: keys this rung refuses outright, with the reason quoted at the call site
_REFUSED = {
    ("focal", "duration"): "a focal duration is a CLOCK -- W2 keeps every duration byte identical "
                           "so the two clocks stay aligned (W3 owns the timing rescore)",
    ("camera_move", "duration"): "a movement duration is a CLOCK -- see W1's two-clocks law; "
                                 "changing it drifts the cut off the program's phase beat",
    ("target_move", "duration"): "a movement duration is a CLOCK -- see W1's two-clocks law",
}

#: spec section -> the parsed Code sub-block it edits
_SECTIONS = {"camera": "campos", "target": "tgtpos", "focal": "focal",
             "camera_move": "cammove", "target_move": "tgtmove"}


class RescoreError(RuntimeError):
    pass


class StockDriftError(RescoreError):
    """The install's bytes are not the bytes this edit was derived against."""


# ============================================================ (0) provenance guards
def _refuse_repo_path(p) -> Path:
    """No stock-derived byte ever lands inside the repo -- ``summon_camera.dump_shots``'s guard,
    applied to the whole staging tree rather than one CSV."""
    ap = Path(p).resolve()
    repo = Path(_REPO).resolve()
    try:
        common = os.path.commonpath([str(ap), str(repo)])
    except ValueError:                                           # different drives -- fine
        return ap
    if common == str(repo):
        raise RescoreError("refusing to stage stock-derived bytes under the repo: %s" % ap)
    return ap


def _refuse_install_path(p, game_root) -> Path:
    """W2 STAGES.  It never writes into the game install -- not the install root, not a live mod
    folder under it.  The orchestrator runs the real deploy with the user present."""
    ap = Path(p).resolve()
    if game_root is None:
        return ap
    root = Path(game_root).resolve()
    try:
        common = os.path.commonpath([str(ap), str(root)])
    except ValueError:
        return ap
    if common == str(root):
        raise RescoreError("refusing to write inside the game install: %s (W2 stages only; the "
                           "orchestrator deploys)" % ap)
    return ap


# ============================================================ (1) read the user's OWN install
def read_stock_effect(ef_id: int, game=None) -> Tuple[bytes, str]:
    """The stock ``ef###`` container, re-derived from ``resources.assets`` in the user's install.

    ALWAYS from ``resources.assets``, never from a previously-written override: an override is a
    frozen whole-container copy, so re-reading one would compound our own edit and would hide the
    day a Steam/Moguri patch changes the stock effect.  Returns ``(bytes, source description)``.
    """
    from ff9mapkit import config
    try:
        import UnityPy
    except ImportError as e:                                     # pragma: no cover
        raise RescoreError("UnityPy is required to read the install's resources.assets: %s" % e)
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
    """sha256 of the install bytes, refused if it drifts from the registered constant.

    Hash only -- the constant is committable because it is not stock DATA.  An unregistered donor is
    ALLOWED but the caller is told there is no guard (``deploy.py``'s warn-not-refuse posture)."""
    got = hashlib.sha256(blob).hexdigest()
    want = expect or EXPECTED_STOCK_SHA.get(ef_id)
    if want and got != want:
        raise StockDriftError(
            "ef%03d in this install does not match the bytes this rescore was derived against.\n"
            "  expected sha256 %s\n  install  sha256 %s\n"
            "The install changed (a Steam/Moguri patch, or another mod wrote it). Re-derive the "
            "shot indices with `summon_camera.py read %d` before trusting this delta."
            % (ef_id, want, got, ef_id))
    return got


# ============================================================ (2) the Code field map
def code_field_offsets(flags: int) -> Dict[str, Tuple[int, int]]:
    """``{name: (offset, size)}`` within a Code's ``block``, mirroring ``camera_codec._split_code``.

    The codec SLICES; a rescore must SPLICE, so it needs the offsets the slicer walks past.  The
    two are pinned to agree by ``test_field_offsets_agree_with_the_codec`` over every flag word in
    the corpus plus an exhaustive synthetic sweep -- if the codec's field order ever changes, that
    test fails rather than this module writing into the wrong four bytes.
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
    shot: W.Shot
    shot_letter: str
    seq_index: int
    code_index: int
    local_frame: int
    flags: int


def find_shot(ex: W.Extract, spec: dict) -> Tuple[int, W.Shot]:
    """The spec's shot, by LETTER (W1's read-out label) and cross-checked against chunk/sub-file.

    Both are required when both are given: the letter is what a human reads in the read-out, the
    (chunk, sub-file) pair is what actually addresses the block.  A mismatch means the read-out the
    spec was written against is not the read-out of the bytes in front of us -- refuse, loudly.
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


def find_code(shot: W.Shot, seq_index: int, local_frame: int) -> int:
    """Index into ``cam['sequences'][seq_index]`` of the Code at ``local_frame``.

    Refuses an ambiguous frame.  ef227's shot A has TWO Codes at f121 and two at f148 (a placement
    and the move it starts) -- naming a frame with more than one Code without saying which is a
    coin-flip, so the spec must add ``occurrence``."""
    seqs = shot.camera["sequences"]
    if seq_index >= len(seqs):
        raise RescoreError("this block declares %d sequence(s); no sequence%d"
                           % (len(seqs), seq_index))
    hits = [i for i, c in enumerate(seqs[seq_index])
            if c.get("frame") and W.frame_number(c["frame"]) == local_frame]
    if not hits:
        raise RescoreError("no keyframe at local frame %d in sequence%d" % (local_frame, seq_index))
    return hits[0] if len(hits) == 1 else -len(hits)             # negative => ambiguous, see caller


def resolve_targets(ex: W.Extract, edit: dict) -> List[Target]:
    """The Codes one ``[[edit]]`` names -- one per track it applies to (see the three-sequence trap)."""
    idx, shot = find_shot(ex, edit)
    letter = W._SHOT_LETTERS[idx % 26]
    frame = edit.get("frame")
    if frame is None:
        raise RescoreError("[[edit]] on shot %s has no `frame` (the keyframe's LOCAL frame number, "
                           "as printed by `summon_camera.py read`)" % letter)
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


def apply_edit(shot: W.Shot, tgt: Target, edit: dict) -> List[Tuple[str, str, int, int]]:
    """Write one ``[[edit]]``'s deltas into ``shot.camera`` IN PLACE.  Returns the change log
    ``[(section, field, old, new)]``.  Refuses every clock key (constraint 1) and every field the
    Code's flags say is not present (writing a field that is not there would silently corrupt the
    NEXT field, which is exactly the class of bug a same-length splice would not catch)."""
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
                "%#06x). Read `summon_camera.py read` and pick a keyframe that carries one."
                % (tgt.local_frame, tgt.shot_letter, tgt.seq_index, section, code["flags"]))
        base, size = fmap[sub]
        for k, v in vals.items():
            why = _REFUSED.get((section, k))
            if why:
                raise RescoreError("[[edit]].%s.%s is refused at W2: %s" % (section, k, why))
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
            block = _patch_bytes(block, off,
                                 iv.to_bytes(width, "little"))
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


def rescore_block(shot: W.Shot) -> Splice:
    """Re-serialise the edited camera and REFUSE anything that is not a same-length in-place splice.

    W1 section 6 is the reason this is an assertion and not a hope: a camera sub-file's length is the
    delta to the NEXT id-2 directory entry and the slack is 0-2 bytes, so a longer block would force
    an id-2 directory rewrite -- which shifts every later sub-file and can break the native walker's
    sector sum.  Same-size only until a container writer exists (that is W3 work)."""
    new = W.serialize_camera_block(shot.camera)
    if len(new) != len(shot.block):
        raise RescoreError(
            "the rescored block is %d B but the stock block is %d B. A camera sub-file's length is "
            "fixed by the next id-2 directory entry (slack is 0-2 B corpus-wide), so only a "
            "SAME-SIZE splice is legal at W2. Adding/removing a keyframe needs an id-2 directory "
            "writer -- W3." % (len(new), len(shot.block)))
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


# ============================================================ (5) the alternates check (X3)
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
        """A one-track edit is safe iff there is only one track, or the alternates are byte-identical
        to it, or every track was edited."""
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


def alternates_signature(shot: W.Shot) -> List[bool]:
    """``[True] + [track i is byte-identical to track 0]`` -- MUST be taken BEFORE any edit.

    Taken afterwards it is a lie in the most dangerous direction: editing track 0 of a block whose
    alternates really WERE identical makes them look "genuinely different", and the trap check
    would then wave through exactly the one-track edit it exists to refuse."""
    seqs = shot.camera["sequences"]
    return [True] + [CC.serialize_sequence(seqs[i]) == CC.serialize_sequence(seqs[0])
                     for i in range(1, len(seqs))]


def check_alternates(signature: Sequence[bool], edited_seq_ids: Sequence[int]) -> AlternatesVerdict:
    return AlternatesVerdict(len(signature), list(signature), list(edited_seq_ids))


# ============================================================ (6) the self-check (X2)
def block_invariants(blob: bytes, arc: W.Id2Archive, idx: int, block: bytes) -> Dict[str, bool]:
    """W1 section 0's four invariants, re-asserted on a block we WROTE."""
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
    """Re-parse the container we just wrote and re-run W1's whole path over it.

    Not "it built" -- W1's own gate, on our bytes: the native walker's sector sum still lands
    (``cursor_end == size``), every camera block in the container still round-trips byte-exact
    through the unmodified codec, the four invariants still hold on the block we edited, and the
    id-2 directory is untouched."""
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


# ============================================================ (7) the write ledger + revert
class _Ledger:
    """Every write this build performs, plus the revert that undoes exactly those writes.

    The ``ff9mapkit/summons/deploy.py`` ``_Ledger`` posture, verbatim in spirit: a pre-existing file
    is backed up before overwrite and the backup path is recorded; a newly created file records
    ``None`` so revert DELETES it; a ModFileList line is recorded so revert drops exactly that line.
    Every write is read back and compared -- a write that did not land is a silent failure and this
    whole rung's failure mode is silence."""

    def __init__(self, backup_dir):
        self.backup_dir = Path(backup_dir)
        self.stamp = time.strftime("%Y%m%d-%H%M%S")
        self.files: List[Tuple[str, Optional[str]]] = []
        self.list_line: Optional[str] = None
        self.list_path: Optional[str] = None

    def write_bytes(self, dest, data: bytes) -> str:
        from ff9mapkit import fsutil
        dest = Path(dest)
        backup = None
        if dest.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup = self.backup_dir / ("%s.pre-%s" % (dest.name, self.stamp))
            shutil.copyfile(dest, backup)
        dest.parent.mkdir(parents=True, exist_ok=True)
        fsutil.atomic_write_bytes(dest, data)
        if dest.read_bytes() != data:                            # pragma: no cover
            raise RescoreError("write verification failed at %s -- readback != what we wrote" % dest)
        self.files.append((str(dest), str(backup) if backup else None))
        return hashlib.sha256(data).hexdigest()

    def add_list_line(self, list_path, line: str) -> bool:
        """Append to an EXISTING ``ModFileList.txt``.  Never create one: if a mod folder has a list,
        ``TryFindAssetInModOnDisc`` TRUSTS it and never calls ``File.Exists``, so creating a list
        would make every other file in that folder invisible."""
        from ff9mapkit import fsutil
        lp = Path(list_path)
        if not lp.exists():
            return False
        lines = lp.read_text(encoding="utf-8").splitlines()
        if any(l.strip().lower() == line for l in lines):
            return False
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup = self.backup_dir / ("%s.pre-%s" % (lp.name, self.stamp))
        shutil.copyfile(lp, backup)
        lines.append(line)
        fsutil.atomic_write_text(lp, "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        self.list_line, self.list_path = line, str(lp)
        self.files.append((str(lp), str(backup)))
        return True

    def revert_plan(self) -> dict:
        return {"files": self.files, "list_line": self.list_line, "list_path": self.list_path}

    def write_revert_script(self, out_dir, name: str) -> Path:
        from ff9mapkit import fsutil
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        plan = json.dumps(self.revert_plan(), indent=2)
        script = _REVERT_TEMPLATE.replace("__PLAN__", repr(plan))
        p = out_dir / ("revert_summon_camera_%s.py" % name)
        fsutil.atomic_write_text(p, script, encoding="utf-8", newline="\n")
        return p


_REVERT_TEMPLATE = '''#!/usr/bin/env python3
"""Auto-generated revert for a TIER W camera rescore -- stdlib only, no ff9mapkit import.

Restores each backed-up file, deletes each file the rescore newly created, and drops the
ModFileList line it added. Idempotent: safe to run more than once."""
import json, shutil
from pathlib import Path

PLAN = json.loads(__PLAN__)

if PLAN.get("list_line") and PLAN.get("list_path"):
    lp = Path(PLAN["list_path"])
    if lp.exists():
        kept = [ln for ln in lp.read_text(encoding="utf-8").splitlines()
                if ln.strip().lower() != PLAN["list_line"]]
        lp.write_text("\\n".join(kept) + ("\\n" if kept else ""), encoding="utf-8", newline="\\n")
        print(f"dropped ModFileList line: {PLAN['list_line']}")

for dest, backup in PLAN["files"]:
    dest = Path(dest)
    if backup and Path(backup).exists():
        shutil.copyfile(backup, dest)
        print(f"restored {dest} <- {Path(backup).name}")
    elif dest.exists():
        dest.unlink()
        print(f"deleted  {dest}")
        parent = dest.parent
        while parent.exists() and parent.name and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
print("camera rescore revert complete.")
'''


# ============================================================ (8) the spec
def load_spec(path) -> dict:
    with open(path, "rb") as fh:
        spec = _toml.load(fh)
    r = spec.get("rescore")
    if not isinstance(r, dict):
        raise RescoreError("%s has no [rescore] table" % path)
    if "effect" not in r:
        raise RescoreError("[rescore] needs `effect` (the stock ef### number)")
    edits = spec.get("edit")
    if not edits:
        raise RescoreError("%s declares no [[edit]] -- nothing to rescore" % path)
    if not isinstance(edits, list):
        raise RescoreError("[[edit]] must be an array of tables")
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


def build_patched(spec: dict, spec_path: str = "?", game=None,
                  blob: Optional[bytes] = None) -> Build:
    """The whole offline half: read the install, apply every ``[[edit]]``, splice, self-check."""
    r = spec["rescore"]
    ef_id = int(r["effect"])
    label = str(r.get("label") or ("ef%03d" % ef_id))
    if blob is None:
        blob, source = read_stock_effect(ef_id, game)
    else:
        source = "(caller-supplied bytes)"
    sha_in = drift_guard(ef_id, blob, r.get("expect_sha256"))
    src_name = "ef%03d" % ef_id
    ex = W.extract_shots(blob, src_name)

    splices: List[Splice] = []
    changes: List[Tuple[str, str, str, int, int]] = []
    verdicts: List[Tuple[str, AlternatesVerdict]] = []
    targets: List[Target] = []
    by_shot: Dict[Tuple[int, int], List[int]] = {}
    touched: Dict[Tuple[int, int], W.Shot] = {}
    signatures: Dict[Tuple[int, int], List[bool]] = {}

    # PASS 1 -- resolve every edit and snapshot each target block's alternates signature BEFORE a
    # single byte moves (see ``alternates_signature``: taken after, the check inverts).
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
                 changes, verdicts, chk)


# ============================================================ (9) staging
def stage(b: Build, mod_root, work_dir=None, game_root=None, allow_install: bool = False) -> dict:
    """Write the override + the revert script.

    STAGE by default: the repo is refused always, and a destination inside the game install is
    refused unless ``allow_install`` is passed.  That flag is the LIVE deploy the orchestrator runs
    with the user present -- it is deliberately not the default, because a build agent writing into
    the shared install is exactly the kind of thing several concurrent worktrees must not do by
    accident."""
    mod_root = _refuse_repo_path(mod_root)
    if not allow_install:
        mod_root = _refuse_install_path(mod_root, game_root)
    work_dir = Path(work_dir or Path(mod_root).parent)
    _refuse_repo_path(work_dir)
    dest = Path(mod_root).joinpath(*MOD_SUBPATH.split("/"), "ef%03d" % b.effect)
    if dest.suffix:                                              # pragma: no cover
        raise RescoreError("the override must be EXTENSIONLESS (LoadFromDisc reads the raw path)")
    ledger = _Ledger(Path(work_dir) / "backups")
    sha = ledger.write_bytes(dest, b.patched)
    listed = ledger.add_list_line(Path(mod_root) / "ModFileList.txt",
                                  "%s/ef%03d" % (MOD_SUBPATH.split("/", 1)[1].lower(), b.effect))
    revert = ledger.write_revert_script(Path(work_dir), "%d" % b.effect)
    return {"dest": str(dest), "sha256": sha, "bytes": len(b.patched),
            "mod_root": str(mod_root), "revert_script": str(revert),
            "modfilelist_updated": listed,
            "modfilelist_present": (Path(mod_root) / "ModFileList.txt").exists()}


# ============================================================ (10) reporting
def describe(b: Build) -> List[str]:
    L = ["ef%03d  %s" % (b.effect, b.label),
         "  stock source : %s" % b.source,
         "  stock sha256 : %s  (drift guard %s)"
         % (b.sha_in, "REGISTERED" if b.effect in EXPECTED_STOCK_SHA else "none -- unguarded"),
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
    L.append("  THE THREE-SEQUENCE CHECK (X3)")
    for letter, v in b.verdicts:
        L.append("    shot %s: %s" % (letter, v.line()))
    if b.check:
        c = b.check
        L.append("")
        L.append("  SELF-CHECK (X2)")
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


# ============================================================ CLI
def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("verb", choices=("plan", "build", "verify"))
    ap.add_argument("spec", nargs="?", default=os.path.join(_HERE, "bahamut_rescore.toml"))
    ap.add_argument("--mod-root", default=os.path.join(SCRATCH_ROOT, "mod"),
                    help="staging mod root (default: SCRATCH; the repo and the install are refused)")
    ap.add_argument("--work-dir", default=SCRATCH_ROOT)
    ap.add_argument("--game", default=None)
    ap.add_argument("--live", action="store_true",
                    help="allow a --mod-root INSIDE the game install (the real deploy). Off by "
                         "default: W2 stages, the orchestrator deploys with the user present.")
    a = ap.parse_args(argv)

    spec = load_spec(a.spec)
    b = build_patched(spec, a.spec, a.game)
    print("\n".join(describe(b)))
    if a.verb == "plan":
        print("\nplan only -- nothing written.")
        return 0

    from ff9mapkit import config
    try:
        game_root = config.find_game_path(a.game)
    except Exception:                                            # pragma: no cover
        game_root = None
    if a.verb == "build":
        out = stage(b, a.mod_root, a.work_dir, game_root, allow_install=a.live)
        print("\n  %s" % ("DEPLOYED (--live)" if a.live else "STAGED"))
        for k, v in out.items():
            print("    %-22s %s" % (k, v))
        if not out["modfilelist_present"]:
            print("    (no ModFileList.txt in this mod folder -- correct: one must never be "
                  "CREATED, or every other file in the folder becomes invisible)")
        return 0

    dest = Path(a.mod_root).joinpath(*MOD_SUBPATH.split("/"), "ef%03d" % b.effect)
    if not dest.exists():
        print("\nVERIFY FAILED: nothing staged at %s" % dest)
        return 1
    on_disc = dest.read_bytes()
    same = on_disc == b.patched
    print("\n  VERIFY  staged %d B sha %s -> %s"
          % (len(on_disc), hashlib.sha256(on_disc).hexdigest()[:16],
             "MATCHES the rebuild" if same else "DIVERGES from the rebuild"))
    return 0 if same else 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
