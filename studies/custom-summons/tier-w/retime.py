r"""TIER W rung 3 -- THE TIMING RESCORE: stretch ``ef227:c0`` state 0 and move all four clocks with it.

    py retime.py plan   bahamut_retime.toml     # resolve + print every edit, write nothing
    py retime.py build  bahamut_retime.toml     # stage BOTH artifacts + the deploy/revert scripts
    py retime.py verify bahamut_retime.toml     # re-run the whole self-check against what is staged
    py retime.py report 211                     # W5: the two-clocks alignment report for one effect
    py retime.py report --corpus                # ... for every clean-switch effect in the corpus

WHAT W5 ADDED (rung 5, THE GENERALISATION -- the reading half only)
-------------------------------------------------------------------
The *writing* half of this rung stays ef227-shaped by choice: :mod:`w3_program_edits` is the frozen,
cast-proven E1 record and is consumed verbatim.  What generalised is everything that READS:

* ``report`` -- the per-effect two-clocks table, with **pairing quality** published beside it
  (nearest-neighbour distances, duplicate-Code collisions, pairs-found over beats-total) and a
  per-boundary derivability row for all four clocks.  37 of the corpus's 85 clock-guarded boundaries
  have no lock pair at all, so a table that only printed leads would manufacture "locked" out of
  "loosely correlated";
* :mod:`retime_derive` -- E1's sites, found in any target's own bytes instead of tabulated, with the
  peer-``lui`` reaching-definition pass that makes the half-patch trap mechanical;
* **the alignment checker classifies machines by PROGRAM ORIGIN, not by chunk slot.**  The c0/c1
  asymmetry this rung demonstrates is a property of *where each machine's ``RUN_PROGRAM`` sits
  relative to the cut*, and ef227 merely happens to spell that as slot 0 versus slot 1;
* ``PlayerAudit.needs_retime`` is ENFORCED at the call site.  It was dead code: the docstring
  claimed a refusal that nothing raised, and ef227's own file (zero literal ``Wait`` lines) never
  exercised it.

WHAT THIS IS
------------
W2 reframed a stock summon's camera with **every duration byte identical**, because W1's two-clocks
law says the camera and the effect program are two clocks the author kept aligned by construction.
W3 spends that law: it moves the phase boundary and moves *everything locked to it* in the same
edit -- and it ships a deliberate MIS-RETIME twin that moves the presentation and not the program,
so the law is demonstrated rather than asserted.

FOUR CLOCKS, FOUR EDIT DOMAINS (the recon slices that own each one)
------------------------------------------------------------------
=====  ===================================  ==============================================  ======
 tag    what                                 where                                            recon
=====  ===================================  ==============================================  ======
 E1     the effect PROGRAM's own clock       7 in-place splices in chunk 0's id-3 image       B0
 E2     the SEQUENCE stream's delta clock    ONE ``WAIT.arg2`` byte in the header sector      A1
 E3     the CAMERA's per-block frame clock   TEN u16 frame words in shot A                    A3
 E4     the OUTER text ``Sequence.seq``      ONE ``Wait: Time=`` line, a separate file        A4
=====  ===================================  ==============================================  ======

**E1 is not authored here.**  It is consumed verbatim from :mod:`w3_program_edits`, whose derivation
and 137-check emulator (:mod:`w3_clock_emu`) are B0's deliverables.  This module derives E2/E3/E4
from the container and the install, never from a hard-coded table: the spec carries *guards* (the
stock values each site must hold) and the tool refuses if the bytes underneath disagree.

THE TWO ARTIFACTS
-----------------
* **ALIGNED** = E1 + E2 + E3 (+ E4).  Every clock moves by N together.
* **MIS-RETIME** = E2 + E3 (+ E4), E1 omitted entirely.  The presentation is retimed, the creature's
  own clock is not.  Its offline signature is exact and is asserted, not hoped for: **c0's
  camera-vs-phase leads drift by exactly N while c1's stay put**, because c1's program origin is a
  sequence op that moves with the presentation and c0's is not.  (B0 section 6.5: this build is a
  LOUD falsifier -- with E1 omitted the creature's arrival arithmetic inverts.  A3 section 7's
  ``E3-alt`` is the subtle one, and is not what this rung ships.)

THE MASKS -- the one place this module owns a correction
--------------------------------------------------------
A3 section 5.1 read the native stepper: the Code frame word's number is **10 bits** (``& 0x3FF``)
and bits 10-15 are a flags composite.  ``summon_camera.FRAME_MASK`` is ``0x1FFF`` -- indistinguishable
on stock data (0 of 7,307 Codes set bits 10-12) and therefore harmless to READ with, which is why W1's
gates pin it and this rung does not change it.  **A WRITER cannot be that loose**: a frame of 1024+
would be read by the engine as ``value & 0x3FF``, fire at the wrong time, and leak bits 10-12 into the
flags.  So ``retime.py`` owns :data:`FRAME_NUM_MASK` = ``0x3FF`` / :data:`FRAME_FLAG_MASK` = ``0xFC00``
for every write, clamps to ``1 <= f <= 1023``, and asserts the two readings agree on this container so
they can never silently diverge.

WHAT THIS REFUSES TO STAGE (a law in a docstring is a wish -- every one is a call-site check)
---------------------------------------------------------------------------------------------
1. any changed byte it cannot name down to the field (self-check 1);
2. any changed byte in a DURATION field -- durations parametrise an interpolation, they do not
   schedule it (A3 section 0), so a retime must not touch one;
3. a MIS-RETIME whose diff is not exactly the ALIGNED diff minus the program edit set;
4. a container that does not re-parse strict, or a camera block that does not round-trip byte-exact
   through the UNMODIFIED codec;
5. a lock table that does not match the prediction derived from the edit sets (self-check 3);
6. a WAIT outside the corpus-attested ``[1, 240]``, a frame word outside ``1..1023``, a frame word
   whose ``0xFC00`` bits moved, or a text file with anything but the one anchored ``Wait`` changed.

PROVENANCE
----------
The container is read at RUN TIME from ``resources.assets`` in the user's own install (never the repo,
never a prior override) under the registered sha256 drift guard; the two text ``.seq`` files are read
from the user's own ``StreamingAssets`` under the drift guards ``build_rung2.py`` / ``build_rung4.py``
already registered.  Every staged byte -- both containers and the edited text -- is SE-derived and
lands under SCRATCH; ``_refuse_repo_path`` refuses the repo and ``_refuse_install_path`` refuses the
install unless ``--live`` is passed.  This file and its spec carry offsets, counts and small scalar
guards only: no run of stock bytes, and no stock frame list (the frame words are read from the
container and the new ones are computed).
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import struct
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import rescore as R                                          # noqa: E402  (sets up sys.path)
import summon_camera as W                                    # noqa: E402
import ef_container as EC                                    # noqa: E402
import w3_program_edits as PE                                # noqa: E402
import w3_clock_emu as EMU                                   # noqa: E402
from ff9mapkit.battle import camera_codec as CC              # noqa: E402

try:                                                         # py3.11+ stdlib, else the backport
    import tomllib as _toml
except ModuleNotFoundError:                                  # pragma: no cover
    import tomli as _toml                                    # type: ignore

_STUDY = os.path.dirname(_HERE)                              # studies/custom-summons
_REPO = os.path.dirname(os.path.dirname(_STUDY))             # <repo>

#: default staging root -- SCRATCH, never the repo, never the live game folder (build stages only)
SCRATCH_ROOT = os.environ.get("FF9_RETIME_SCRATCH",
                              r"C:\gd\SCRATCH\summon-format\retime-w3")

#: the binary container's override lane (rescore.MOD_SUBPATH: extensionless, LoadFromDisc reads it raw)
MOD_SUBPATH = R.MOD_SUBPATH                                  # "FF9_Data/SpecialEffects"
#: the loose-TEXT lane the rung-2/rung-4 overrides used (AssetManager.LoadString, re-read every cast)
TEXT_SUBPATH = "StreamingAssets/Data/SpecialEffects"

#: THE WRITE MASKS (module docstring).  The engine's stepper masks the frame number with 0x3FF and
#: folds bits 10-15 into a flags composite; the per-block frame counter saturates at 1023, and the
#: fire test is an EQUALITY compare, so an unmatchable frame parks the cursor and kills every later
#: keyframe in the block -- silently.
FRAME_NUM_MASK = 0x3FF
FRAME_FLAG_MASK = 0xFC00
FRAME_MIN, FRAME_MAX = 1, 1023
#: the frame-word bit that FREEZES the camera clock (A3 section 5.2).  A Code carrying it makes every
#: later Code in the track unreachable, so shifting them would be a silent no-op.
FRAME_PAUSE_BIT = 0x4000

#: WAIT ``arg2`` is a u8 (mechanical ceiling 255).  The corpus envelope over 1,931 non-blocking WAITs
#: in 372 files is [1, 240] and ``arg2 == 0`` occurs ZERO times -- treat 0 as unattested and unsafe.
WAIT_MIN, WAIT_MAX = 1, 240

#: sequence opcodes this module needs by name (summon_camera owns the rest)
OP_END, OP_WAIT, OP_RUN_PROGRAM = W.OP_END, W.OP_WAIT, W.OP_RUN_PROGRAM

#: a Code sub-block field whose name matches this is a CLOCK the retime must not touch
_DURATION_RE = re.compile(r"duration", re.I)


class RetimeError(RuntimeError):
    pass


# ============================================================ (0) small helpers
def _u16(b: bytes, off: int) -> int:
    return struct.unpack_from("<H", b, off)[0]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def frame_num(word: int) -> int:
    """The Code frame word's NUMBER, with the engine's own 10-bit mask (module docstring)."""
    return word & FRAME_NUM_MASK


def frame_flags(word: int) -> int:
    """The frame word's flags composite -- preserved verbatim through every write."""
    return word & FRAME_FLAG_MASK


def apply_writes(blob: bytes, writes: Sequence[Tuple[int, bytes, str]]) -> bytes:
    """Splice a set of same-length in-place writes into a COPY.  Overlaps and length changes raise."""
    out = bytearray(blob)
    seen: Dict[int, str] = {}
    for off, raw, why in writes:
        if off < 0 or off + len(raw) > len(out):
            raise RetimeError("write at %#x (%d B) is outside the container" % (off, len(raw)))
        for i in range(len(raw)):
            if off + i in seen:
                raise RetimeError("two edits write byte %#x (%s / %s)" % (off + i, seen[off + i], why))
            seen[off + i] = why
        out[off:off + len(raw)] = raw
    if len(out) != len(blob):                                # pragma: no cover - belt and braces
        raise RetimeError("container length changed: %d -> %d" % (len(blob), len(out)))
    return bytes(out)


# ============================================================ (1) E2 -- the sequence stream
@dataclass(frozen=True)
class SeqOp:
    at: int
    code: int
    arg1: int
    arg2: int
    tick: int


def seq_ops(blob: bytes) -> List[SeqOp]:
    """The whole 3-byte op stream with its accumulated DELTA clock.

    ``summon_camera.walk_camera_ops``'s strict clock, kept op-for-op instead of camera-ops-only:
    ``WAIT arg1 == 0`` adds ``arg2`` ticks, a BLOCKING wait (``arg1 != 0``) has no statically known
    duration and is counted as zero (ef227 has exactly one, at tick 0, before everything).
    """
    out: List[SeqOp] = []
    tick = 0
    for op in EC.parse_sequence(blob):
        out.append(SeqOp(op.at, op.code, op.arg1, op.arg2, tick))
        if op.code == OP_WAIT and op.arg1 == 0:
            tick += op.arg2
        if op.code == OP_END:
            break
    return out


@dataclass(frozen=True)
class SeqAnchor:
    """The ONE ``WAIT.arg2`` byte whose value shifts every op at ``cut_tick`` and later."""
    op_at: int                  # file offset of the 3-byte WAIT record
    arg_at: int                 # file offset of its arg2 -- the single byte this rung writes
    old: int
    new: int
    from_tick: int
    to_tick: int                # == cut_tick

    @property
    def write(self) -> Tuple[int, bytes, str]:
        return (self.arg_at, bytes([self.new]),
                "E2 SEQUENCE: WAIT @%#x arg2 %d -> %d (spans tick %d -> %d); every op at tick >= %d "
                "fires %+d later, and NOT ONE of their own bytes changes"
                % (self.op_at, self.old, self.new, self.from_tick, self.to_tick,
                   self.to_tick, self.new - self.old))


def find_seq_anchor(blob: bytes, cut_tick: int, n: int) -> SeqAnchor:
    """Derive the anchor WAIT from the stream: the one whose span ENDS on the cut tick.

    A1 section 4 calls this anchor **B**.  It is the lead-preserving choice: the tick-81 pair (the
    ``0x2A`` background-intensity op and shot A's f71 keyframe) is authored *to* the end of the
    entrance phase, so it must ride the phase's end rather than stay parked N ticks before it.
    Deriving it rather than trusting an offset is the point -- the spec's ``expect_wait_offset`` /
    ``expect_wait_time`` are then GUARDS on a derivation, not the derivation itself.
    """
    ops = seq_ops(blob)
    waits = [o for o in ops if o.code == OP_WAIT and o.arg1 == 0]
    hits = [o for o in waits if o.tick + o.arg2 == cut_tick]
    if len(hits) != 1:
        raise RetimeError(
            "expected exactly one non-blocking WAIT whose span ends on tick %d; found %d. The "
            "stream is not the stream this retime was derived against." % (cut_tick, len(hits)))
    w = hits[0]
    # it must be the LAST op before the first op at >= cut_tick, or the shift set is not "tick >= cut"
    after = [o for o in ops if o.at > w.at]
    if not after or after[0].tick != cut_tick:
        raise RetimeError("the WAIT at %#x is not immediately followed by the first op at tick %d"
                          % (w.at, cut_tick))
    new = w.arg2 + n
    if not WAIT_MIN <= new <= WAIT_MAX:
        raise RetimeError(
            "WAIT arg2 would become %d; the field is a u8 and the stock corpus envelope over 1,931 "
            "non-blocking WAITs is [%d, %d] (arg2 == 0 occurs ZERO times in 372 files, so 0 is the "
            "shrink floor, not 'no wait')" % (new, WAIT_MIN, WAIT_MAX))
    return SeqAnchor(w.at, w.at + 2, w.arg2, new, w.tick, w.tick + w.arg2)


def op_tick_map(blob: bytes) -> Dict[int, int]:
    """``{op file offset: seq tick}`` -- the whole stream, for the before/after shift proof."""
    return {o.at: o.tick for o in seq_ops(blob)}


# ============================================================ (2) E3 -- the camera frame words
@dataclass(frozen=True)
class CodeSite:
    """One Code, located inside its block with the byte offsets a WRITER needs."""
    seq_index: int
    code_index: int
    blk_off: int                # the frame word's block-relative offset
    file_off: int
    word: int
    flags: int
    body_len: int

    @property
    def local(self) -> int:
        return frame_num(self.word)


def code_sites(shot: W.Shot) -> List[CodeSite]:
    """Walk every declared track's Code stream and record each Code's own offsets.

    ``camera_codec`` SLICES (it hands back verbatim sub-block bytes); a retime must SPLICE, so it
    needs the offsets the slicer walked past.  The walk mirrors ``serialize_sequence`` exactly --
    ``frame u16``, ``flags u16``, then the body -- and every recovered offset is cross-checked
    against the block's own bytes, so a codec change breaks this loudly instead of writing into the
    wrong two bytes.
    """
    out: List[CodeSite] = []
    groups = {name: (lo, hi) for name, lo, hi in W.block_layout(shot.block)}
    for si, seq in enumerate(shot.camera["sequences"]):
        key = "sequence%d" % si
        if key not in groups:                                # pragma: no cover - codec/layout drift
            raise RetimeError("block layout has no %s group" % key)
        off, hi = groups[key]
        for ci, c in enumerate(seq):
            word = c.get("frame") or 0
            if not word:
                break                                        # the frame-0 terminator
            if off + 4 > hi:                                 # pragma: no cover
                raise RetimeError("Code %d of %s runs past its group" % (ci, key))
            if _u16(shot.block, off) != word or _u16(shot.block, off + 2) != c["flags"]:
                raise RetimeError(
                    "Code %d of %s does not sit at block+%d -- the codec's stream walk and this "
                    "module's offset walk disagree, so no write is safe" % (ci, key, off))
            body = len(c.get("block", b""))
            out.append(CodeSite(si, ci, off, shot.lo + off, word, c["flags"], body))
            off += 4 + body
    return out


@dataclass(frozen=True)
class FrameEdit:
    site: CodeSite
    new_word: int
    n: int

    @property
    def new_local(self) -> int:
        return frame_num(self.new_word)

    @property
    def write(self) -> Tuple[int, bytes, str]:
        return (self.site.file_off, struct.pack("<H", self.new_word),
                "E3 CAMERA: shot A seq%d Code %d frame word: local %d -> %d (flags %#06x preserved)"
                % (self.site.seq_index, self.site.code_index, self.site.local, self.new_local,
                   frame_flags(self.site.word)))


def _sub_field_name(sub: str, k: int) -> str:
    """Name the k-th byte of a Code sub-block, using ``rescore``'s own field maps.

    Imported rather than re-tabulated on purpose: if the two modules ever disagreed about where a
    duration lives, the duration guard below would be checking the wrong bytes.
    """
    if sub in ("campos", "tgtpos"):
        inv = {v: name for name, v in R.POSE_FIELDS.items()}
        return "%s.%s" % (sub, inv.get(k, "+%d" % k))
    if sub == "focal":
        for name, (rel, width) in R.FOCAL_FIELDS.items():
            if rel <= k < rel + width:
                return "focal.%s" % name
    if sub in ("cammove", "tgtmove"):
        for name, (rel, width) in R.MOVE_FIELDS.items():
            if rel <= k < rel + width:
                return "%s.%s" % (sub, name)
    return "%s+%d" % (sub, k)


def block_field_map(shot: W.Shot) -> Dict[int, str]:
    """``{block-relative offset: a field name a human can check}`` for every byte of every Code.

    This is what turns "3 bytes differ" into "3 bytes differ, and each one is a frame word".  Bytes
    NOT covered here (the outer flags word, the offset table, the selector group, the terminator)
    are deliberately absent, so a stray write into one of them shows up as UNEXPLAINED.
    """
    out: Dict[int, str] = {}
    for s in code_sites(shot):
        out[s.blk_off] = "seq%d Code%d frame.lo" % (s.seq_index, s.code_index)
        out[s.blk_off + 1] = "seq%d Code%d frame.hi" % (s.seq_index, s.code_index)
        out[s.blk_off + 2] = "seq%d Code%d CodeFlags.lo" % (s.seq_index, s.code_index)
        out[s.blk_off + 3] = "seq%d Code%d CodeFlags.hi" % (s.seq_index, s.code_index)
        body = s.blk_off + 4
        for sub, (fo, fsz) in R.code_field_offsets(s.flags).items():
            for k in range(fsz):
                out[body + fo + k] = "seq%d Code%d %s" % (s.seq_index, s.code_index,
                                                          _sub_field_name(sub, k))
    return out


def _straddle_ok(site: CodeSite, body: bytes, cut_local: int) -> Optional[str]:
    """A3 guard 4: a pre-cut Code's interpolation must have COMPLETED by the cut.

    If a movement/focal/unk5 countdown started before the cut and is still running when the timeline
    stretches underneath it, the interpolation is silently re-scoped.  Nothing in shot A does this
    (it starts no movement at all before local frame 121, and the only pre-cut duration is Code 0's
    ``focal.duration`` = 1, giving 1 + 1 = 2 <= 71), but the check is at the call site so a different
    shot cannot slip past.  ``focal``/``unk5`` durations are BYTES; a movement's is a u16 field whose
    runtime read is byte 0 only (A3 section 5.3), and the wider read is the conservative one here.
    """
    if site.local >= cut_local:
        return None
    fields = R.code_field_offsets(site.flags)
    for sub in ("cammove", "tgtmove", "focal", "unk5"):
        if sub not in fields:
            continue
        base, _size = fields[sub]
        dur = _u16(body, base) if sub in ("cammove", "tgtmove") else \
            (body[base] if sub == "focal" else body[base + 2])
        if site.local + dur > cut_local:
            return ("Code at local frame %d starts a %s countdown of %d frames, which straddles the "
                    "cut at local %d" % (site.local, sub, dur, cut_local))
    return None


def find_frame_edits(shot: W.Shot, cut_local: int, n: int) -> List[FrameEdit]:
    """Every frame word at or after the cut, with all six of A3 section 8's guards enforced here."""
    sites = code_sites(shot)
    bodies = {(si, ci): c.get("block", b"")
              for si, seq in enumerate(shot.camera["sequences"])
              for ci, c in enumerate(seq) if c.get("frame")}

    # guard: the loose read-side mask and the engine's own mask must agree on THIS container, or the
    # read-out a human checked and the bytes we write are describing different frames.
    for s in sites:
        if W.frame_number(s.word) != frame_num(s.word):
            raise RetimeError(
                "Code seq%d/%d frame word %#06x reads as %d under summon_camera's 0x1FFF mask and %d "
                "under the engine's 0x3FF mask. Bits 10-12 are set: this container is outside the "
                "corpus envelope W1's gates pin, and a write here would fire at the wrong time."
                % (s.seq_index, s.code_index, s.word, W.frame_number(s.word), frame_num(s.word)))

    out: List[FrameEdit] = []
    by_track: Dict[int, List[CodeSite]] = {}
    for s in sites:
        by_track.setdefault(s.seq_index, []).append(s)

    for si, track in sorted(by_track.items()):
        moved: Dict[int, int] = {}
        # guard 3: a pause bit before the cut makes everything after it unreachable
        for s in track:
            if s.local < cut_local and frame_flags(s.word) & FRAME_PAUSE_BIT:
                raise RetimeError(
                    "seq%d Code %d (local frame %d) carries the FREEZE bit %#06x: it stops the "
                    "block's frame counter, so every later keyframe is unreachable and shifting "
                    "them would be a silent no-op" % (si, s.code_index, s.local, FRAME_PAUSE_BIT))
            why = _straddle_ok(s, bodies[(s.seq_index, s.code_index)], cut_local)
            if why:
                raise RetimeError("THE STRADDLE TEST FAILED: %s" % why)
        for s in track:
            if s.local < cut_local:
                continue
            new_local = s.local + n
            if not FRAME_MIN <= new_local <= FRAME_MAX:
                raise RetimeError(
                    "frame %d + %d = %d is outside 1..1023: the frame field is 10 bits and the "
                    "block's own counter saturates at 1023, and the fire test is an EQUALITY "
                    "compare -- an unmatchable frame parks the cursor and kills every later "
                    "keyframe in the block, silently" % (s.local, n, new_local))
            new_word = frame_flags(s.word) | (new_local & FRAME_NUM_MASK)
            if frame_flags(new_word) != frame_flags(s.word):     # pragma: no cover - by construction
                raise RetimeError("the frame word's 0xFC00 flags did not survive the write")
            moved[s.code_index] = new_local
            out.append(FrameEdit(s, new_word, n))
        # guard 6: frames stay non-decreasing within a track
        after = [moved.get(s.code_index, s.local) for s in track]
        if any(y < x for x, y in zip(after, after[1:])):
            raise RetimeError("seq%d's frame words would stop being non-decreasing after the shift"
                              % si)
    if not out:
        raise RetimeError("no keyframe at or after local frame %d -- nothing to retime" % cut_local)
    return out


def find_shot(ex: W.Extract, spec: dict) -> Tuple[int, str, W.Shot]:
    """``rescore.find_shot``'s posture: the letter AND the (chunk, sub-file) pair must both agree."""
    idx, shot = R.find_shot(ex, spec)
    return idx, W._SHOT_LETTERS[idx % 26], shot


# ============================================================ (3) the build
@dataclass
class Domain:
    """One named edit domain: its writes, and the byte offsets they own."""
    tag: str
    what: str
    writes: List[Tuple[int, bytes, str]]

    @property
    def offsets(self) -> List[int]:
        return sorted(o + i for o, raw, _w in self.writes for i in range(len(raw)))


@dataclass
class Build:
    spec_path: str
    effect: int
    label: str
    n: int
    source: str
    sha_in: str
    cut_tick: int
    cut_local: int
    anchor: SeqAnchor
    frame_edits: List[FrameEdit]
    shot_letter: str
    shot: W.Shot = field(repr=False)
    orig: bytes = field(repr=False)
    aligned: bytes = field(repr=False)
    misretime: bytes = field(repr=False)
    domains: List[Domain] = field(default_factory=list, repr=False)
    #: ``(machine image, state)`` whose threshold E1 moves -- ``[retime.program] machine`` / ``state``.
    #: ``None`` means the historical default, this effect's ``c0`` state 0, which is ef227's shape.
    stretched: Optional[Tuple[str, int]] = None
    text: Optional["TextEdit"] = None
    player: Optional["PlayerAudit"] = None
    check: Optional["SelfCheck"] = None

    @property
    def sha_aligned(self) -> str:
        return _sha(self.aligned)

    @property
    def sha_mis(self) -> str:
        return _sha(self.misretime)


def build_containers(spec: dict, spec_path: str = "?", game=None,
                     blob: Optional[bytes] = None) -> Build:
    """Read the install, derive E2/E3, consume E1 verbatim, and splice BOTH artifacts."""
    r = spec["retime"]
    ef_id = int(r["effect"])
    n = int(r["ticks"])
    label = str(r.get("label") or ("ef%03d" % ef_id))
    if blob is None:
        blob, source = R.read_stock_effect(ef_id, game)
    else:
        source = "(caller-supplied bytes)"
    sha_in = R.drift_guard(ef_id, blob, r.get("expect_sha256"))
    src_name = "ef%03d" % ef_id

    # ---- E1: consumed verbatim, and its guards run BEFORE a single byte moves anywhere
    prog = r.get("program", {})
    PE.verify_stock(blob)
    if PE.N_TICKS != n:
        raise RetimeError("the spec says N = %+d but w3_program_edits is locked at N = %+d -- the "
                          "program edit set is derived for its own N and the two must agree"
                          % (n, PE.N_TICKS))
    if int(prog.get("expect_threshold", PE.STOCK_THRESHOLD)) != PE.STOCK_THRESHOLD:
        raise RetimeError("spec expect_threshold %s != w3_program_edits' %d"
                          % (prog.get("expect_threshold"), PE.STOCK_THRESHOLD))
    if int(prog.get("new_threshold", PE.NEW_THRESHOLD)) != PE.NEW_THRESHOLD:
        raise RetimeError("spec new_threshold %s != w3_program_edits' %d"
                          % (prog.get("new_threshold"), PE.NEW_THRESHOLD))
    if int(prog.get("sites", len(PE.PROGRAM_EDITS))) != len(PE.PROGRAM_EDITS):
        raise RetimeError("spec program.sites %s != the %d sites w3_program_edits emits at this N"
                          % (prog.get("sites"), len(PE.PROGRAM_EDITS)))

    # ---- E2: the sequence anchor, derived then guarded
    sq = r["sequence"]
    cut_tick = int(sq["cut_tick"])
    anchor = find_seq_anchor(blob, cut_tick, n)
    if "expect_wait_offset" in sq and int(sq["expect_wait_offset"]) != anchor.arg_at:
        raise RetimeError("the derived WAIT arg2 sits at %#x, the spec guards %#x"
                          % (anchor.arg_at, int(sq["expect_wait_offset"])))
    if "expect_wait_time" in sq and int(sq["expect_wait_time"]) != anchor.old:
        raise RetimeError("the WAIT at %#x holds %d, the spec guards %d"
                          % (anchor.op_at, anchor.old, int(sq["expect_wait_time"])))

    # ---- E3: shot A's frame words
    cam = r["camera"]
    ex = W.extract_shots(blob, src_name)
    idx, letter, shot = find_shot(ex, cam)
    if "install_tick" in cam and int(cam["install_tick"]) != shot.op.seq_tick:
        raise RetimeError("shot %s installs at seq tick %d, the spec guards %d"
                          % (letter, shot.op.seq_tick, int(cam["install_tick"])))
    cut_local = cut_tick - shot.op.seq_tick + 1              # A3: abs = install + local - 1
    if "expect_first_local_frame" in cam and int(cam["expect_first_local_frame"]) != cut_local:
        raise RetimeError(
            "the cut lands on local frame %d of shot %s (install tick %d, cut tick %d) but the spec "
            "guards %d" % (cut_local, letter, shot.op.seq_tick, cut_tick,
                           int(cam["expect_first_local_frame"])))
    frame_edits = find_frame_edits(shot, cut_local, n)
    if "expect_frame_words" in cam and int(cam["expect_frame_words"]) != len(frame_edits):
        raise RetimeError("%d frame words move, the spec guards %d"
                          % (len(frame_edits), int(cam["expect_frame_words"])))

    d_seq = Domain("E2", "the sequence stream's delta clock", [anchor.write])
    d_cam = Domain("E3", "shot %s's frame words" % letter, [e.write for e in frame_edits])
    d_prog = Domain("E1", "the effect program's own clock",
                    [(off, nb, why) for off, _ln, nb, why in PE.PROGRAM_EDITS])

    # the three domains must be disjoint, or "aligned minus E1 == misretime" is not a set difference
    seen: Dict[int, str] = {}
    for d in (d_prog, d_seq, d_cam):
        for o in d.offsets:
            if o in seen:
                raise RetimeError("domains %s and %s both write byte %#x" % (seen[o], d.tag, o))
            seen[o] = d.tag

    misretime = apply_writes(blob, d_seq.writes + d_cam.writes)
    aligned = PE.apply_edits(misretime)                       # re-runs verify_stock on the E1 sites

    stretched = ("ef%03d:%s" % (ef_id, str(prog.get("machine", "c0"))),
                 int(prog.get("state", 0)))
    return Build(spec_path=spec_path, effect=ef_id, label=label, n=n, source=source, sha_in=sha_in,
                 cut_tick=cut_tick, cut_local=cut_local, anchor=anchor, frame_edits=frame_edits,
                 shot_letter=letter, shot=shot, orig=blob, aligned=aligned,
                 misretime=misretime, domains=[d_prog, d_seq, d_cam], stretched=stretched)


# ============================================================ (4) E4 -- the OUTER text clock
@dataclass(frozen=True)
class WaitLine:
    index: int                  # ordinal among the file's ``Wait: Time=`` lines
    line_no: int                # 0-based line index in the file
    time: int
    start: int                  # cumulative tick BEFORE this wait
    end: int                    # cumulative tick after it


_WAIT_RE = re.compile(r"^\s*Wait\s*:\s*Time\s*=\s*(\d+)\s*$")
_TIME_RE = re.compile(r"(Time\s*=\s*)(\d+)")


def parse_seq_text(text: str) -> Tuple[List[str], List[WaitLine]]:
    """Split a text ``.seq`` into lines and reconstruct its cumulative-tick clock.

    The DSL's only literal tick advance is ``Wait: Time=N`` on the main thread; every other ``Time=``
    is a tween/hold DURATION internal to its own op, and every other wait (``WaitAnimation``,
    ``WaitSFXDone``, ...) is signal-driven and has no static length.  So the file's schedule IS the
    running sum of the ``Wait`` lines -- which is exactly why a single one of them can move every
    beat downstream of it.
    """
    lines = text.splitlines(keepends=True)
    waits: List[WaitLine] = []
    cum = 0
    for i, ln in enumerate(lines):
        m = _WAIT_RE.match(ln.rstrip("\r\n"))
        if not m:
            continue
        t = int(m.group(1))
        waits.append(WaitLine(len(waits), i, t, cum, cum + t))
        cum += t
    return lines, waits


@dataclass
class TextEdit:
    path: str
    dest_rel: str
    stock_sha: str
    new_sha: str
    anchor: WaitLine
    new_time: int
    delta: int
    boundary: int
    stock_total: int
    new_total: int
    moved_beats: int
    diff: str
    data: bytes = field(repr=False)


@dataclass
class PlayerAudit:
    path: str
    sha: str
    n_wait_lines: int
    max_tick: int
    boundary: int
    timed_lines: List[Tuple[int, int, str]]      # (line no, cumulative tick, keyword)
    verdict: str
    #: set only when the spec explicitly states the drift is intended
    acknowledged: bool = False

    @property
    def needs_retime(self) -> bool:
        return self.max_tick > self.boundary

    @property
    def ok(self) -> bool:
        """The self-check's view: clean, or drifting and explicitly acknowledged in the spec."""
        return (not self.needs_retime) or self.acknowledged


def _game_text_path(game_root, ef_id: int, name: str) -> Path:
    return Path(game_root) / TEXT_SUBPATH / ("ef%03d" % ef_id) / name


def build_text_edit(spec: dict, game_root) -> TextEdit:
    """E4: the ONE ``Wait`` line whose span straddles the boundary, +N.

    A4 section 4.4: every later tick in the file is a running sum that includes this line's value, so
    changing it alone shifts every downstream beat -- both ``EffectPoint`` calls, the flare ramp, all
    the remaining sound clusters and the closing fade -- uniformly by N, and leaves everything before
    the boundary exactly where it was.  The anchor is found by its SPAN, not by its text: the stock
    file has two ``Wait: Time=56`` lines and only one of them covers the boundary.
    """
    r = spec["retime"]
    t = r["text"]
    ef_id = int(r["effect"])
    delta = int(t.get("delta", r["ticks"]))
    boundary = int(t["boundary_outer_tick"])
    name = str(t.get("seq_file", "Sequence.seq"))
    src = _game_text_path(game_root, ef_id, name)
    if not src.exists():
        raise RetimeError("no stock text sequence at %s" % src)
    raw = src.read_bytes()
    got = _sha(raw)
    want = str(t["expect_sha256"])
    if got != want:
        raise RetimeError(
            "%s sha256 %s != the registered %s. That constant is build_rung4.py's own drift guard "
            "for this exact file; a mismatch means the install's text changed and the anchor line "
            "this edit names may no longer be the line that covers the boundary." % (src, got, want))
    text = raw.decode("utf-8")
    if text.encode("utf-8") != raw:                          # pragma: no cover - utf-8 round-trip
        raise RetimeError("%s does not round-trip through utf-8" % src)
    lines, waits = parse_seq_text(text)
    if "".join(lines) != text:                               # pragma: no cover
        raise RetimeError("line split did not round-trip")

    hits = [w for w in waits if w.start <= boundary < w.end]
    if len(hits) != 1:
        raise RetimeError("expected exactly one Wait spanning outer tick %d; found %d"
                          % (boundary, len(hits)))
    anchor = hits[0]
    if "anchor_wait_index" in t and int(t["anchor_wait_index"]) != anchor.index:
        raise RetimeError("the Wait covering tick %d is #%d, the spec guards #%d"
                          % (boundary, anchor.index, int(t["anchor_wait_index"])))
    if "expect_wait_time" in t and int(t["expect_wait_time"]) != anchor.time:
        raise RetimeError("the anchor Wait holds Time=%d, the spec guards %d"
                          % (anchor.time, int(t["expect_wait_time"])))
    if "expect_wait_span" in t and list(t["expect_wait_span"]) != [anchor.start, anchor.end]:
        raise RetimeError("the anchor Wait spans %d -> %d, the spec guards %s"
                          % (anchor.start, anchor.end, list(t["expect_wait_span"])))

    new_time = anchor.time + delta
    if new_time < 1:
        raise RetimeError("the anchor Wait would become Time=%d" % new_time)
    old_line = lines[anchor.line_no]
    new_line, n_sub = _TIME_RE.subn(lambda m: m.group(1) + str(new_time), old_line, count=1)
    if n_sub != 1 or new_line == old_line:                   # pragma: no cover
        raise RetimeError("could not rewrite the anchor Wait line")
    out = list(lines)
    out[anchor.line_no] = new_line
    new_text = "".join(out)

    # -- the edit's own proof: exactly one line differs, it is the anchor, and the clock moved the
    #    way the mechanism says it must (upstream identical, downstream uniformly +delta).
    changed = [i for i, (a, b) in enumerate(zip(lines, out)) if a != b]
    if changed != [anchor.line_no] or len(out) != len(lines):
        raise RetimeError("the text edit touched lines %s; exactly one was allowed" % changed)
    _new_lines, new_waits = parse_seq_text(new_text)
    if len(new_waits) != len(waits):                         # pragma: no cover
        raise RetimeError("the Wait count changed")
    moved = 0
    for a, b in zip(waits, new_waits):
        want_start = a.start + (delta if a.start >= anchor.end else 0)
        if b.start != want_start:
            raise RetimeError("Wait #%d now starts at tick %d, expected %d" % (a.index, b.start,
                                                                               want_start))
        if a.index != anchor.index and b.time != a.time:
            raise RetimeError("Wait #%d's Time changed and it is not the anchor" % a.index)
        if b.start >= anchor.end:
            moved += 1
    if new_waits[anchor.index].time != new_time:             # pragma: no cover
        raise RetimeError("the anchor's new Time did not land")

    diff = "".join(difflib.unified_diff(
        lines, out, fromfile="stock/%s/ef%03d/%s" % (TEXT_SUBPATH, ef_id, name),
        tofile="FF9CustomMap/%s/ef%03d/%s" % (TEXT_SUBPATH, ef_id, name), n=0))
    data = new_text.encode("utf-8")
    return TextEdit(path=str(src), dest_rel="%s/ef%03d/%s" % (TEXT_SUBPATH, ef_id, name),
                    stock_sha=got, new_sha=_sha(data), anchor=anchor, new_time=new_time,
                    delta=delta, boundary=boundary,
                    stock_total=waits[-1].end if waits else 0,
                    new_total=new_waits[-1].end if new_waits else 0,
                    moved_beats=moved, diff=diff, data=data)


def audit_player_sequence(spec: dict, game_root) -> PlayerAudit:
    """Does the OUTER-OUTER script have any beat after the boundary?  Checked, not assumed.

    ``PlayerSequence.seq`` is the caster's own choreography.  If any of its literal tick-scheduled
    beats landed after the boundary it would need the same one-line co-retime; the answer here is
    that its main-thread clock never advances at all (it has zero ``Wait: Time=`` lines -- every wait
    it uses is animation- or signal-gated), so nothing in it can drift.  Recorded as a fact with the
    numbers behind it, and the file ships untouched.
    """
    r = spec["retime"]
    pa = r["text"].get("player_audit", {})
    ef_id = int(r["effect"])
    boundary = int(r["text"]["boundary_outer_tick"])
    _ack_raw = pa.get("acknowledge_uncoretimed", False)
    if not isinstance(_ack_raw, bool):
        # rescore.py's R3 rule, applied here too (V2's cross-lane finding): a TOML author writing
        # `acknowledge_uncoretimed = "false"` must not silently ARM the acknowledgement.
        raise RetimeError(
            "[retime.text.player_audit] acknowledge_uncoretimed must be a BOOLEAN (true/false), "
            "not %r. A safety acknowledgement must be stated, never inferred from a truthy string."
            % (_ack_raw,))
    _ack = _ack_raw
    name = str(pa.get("file", "PlayerSequence.seq"))
    src = _game_text_path(game_root, ef_id, name)
    if not src.exists():
        raise RetimeError("no stock %s at %s" % (name, src))
    raw = src.read_bytes()
    got = _sha(raw)
    want = pa.get("expect_sha256")
    if want and got != str(want):
        raise RetimeError("%s sha256 %s != the registered %s (build_rung2.py's own drift guard)"
                          % (src, got, want))
    lines, waits = parse_seq_text(raw.decode("utf-8"))
    timed: List[Tuple[int, int, str]] = []
    cum = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        m = _WAIT_RE.match(s)
        if m:
            cum += int(m.group(1))
            timed.append((i, cum, "Wait"))
        elif "Time" in s and "=" in s:
            timed.append((i, cum, s.split(":", 1)[0].strip()))
    max_tick = waits[-1].end if waits else 0
    if max_tick > boundary:
        verdict = ("%d Wait line(s), clock reaches tick %d > the boundary %d -- this file DOES carry "
                   "beats after the cut and needs the same one-line co-retime"
                   % (len(waits), max_tick, boundary))
        # ENFORCED HERE, at the only place the verdict is produced.  Until W5 ``needs_retime`` was
        # a property nothing ever read: the docstring claimed the tool "would refuse to leave it
        # alone", and on ef227 (zero literal Wait lines) the claim was never exercised.  It is not
        # hypothetical -- ef418's PlayerSequence.seq clock reaches tick 130, and ef125/151/251/381
        # each carry a Wait line, so a generalised retime would silently ship an un-co-retimed
        # outer-outer script whose failure mode looks exactly like a mistimed sound cue.
        if not _ack:
            raise RetimeError(
                "%s CARRIES BEATS AFTER THE BOUNDARY: %s. This rung edits one Wait line in "
                "Sequence.seq and leaves PlayerSequence.seq untouched, so those beats would keep "
                "their stock schedule and drift by the retime's delta. Co-retime it, move the "
                "boundary, or set `[retime.text.player_audit] acknowledge_uncoretimed = true` to "
                "state in the spec that the drift is intended." % (name, verdict))
    else:
        verdict = ("%d literal `Wait: Time=` line(s); the main-thread clock never advances past tick "
                   "%d, so NO beat lands after the boundary %d. Its %d other `Time=` value(s) are "
                   "tween/hold DURATIONS internal to their own op, not schedule positions. SHIPPED "
                   "UNTOUCHED -- a checked fact, not an assumption."
                   % (len(waits), max_tick, boundary, len(timed) - len(waits)))
    return PlayerAudit(str(src), got, len(waits), max_tick, boundary, timed, verdict,
                       acknowledged=_ack)


# ============================================================ (5) THE ALIGNMENT CHECKER (self-check 3)
@dataclass(frozen=True)
class LockId:
    """A lock pair's IDENTITY -- what it is, not where it is.

    The pairing is taken ONCE, on the stock container, and then the same identities are re-timed in
    the patched ones.  Re-running a nearest-neighbour match on a drifted container would silently
    re-pair each cut with whatever beat happens to be closest now, which is precisely how a broken
    lock table can look healthy.
    """
    machine: str
    state: int
    slot: int
    subfile: int
    seq_index: int
    code_index: int


@dataclass(frozen=True)
class LockRow:
    ident: LockId
    beat: int
    cam: int
    local: int
    install: int

    @property
    def lead(self) -> int:
        """cut minus beat: NEGATIVE means the camera event ANTICIPATES the phase boundary."""
        return self.cam - self.beat


#: R3's state-machine recovery costs ~1 s a container and the checker needs three of them several
#: times over.  Keyed by content hash, so a patched container can never be served a stock answer.
_RECOVERY_MEMO: Dict[str, Tuple[W.Extract, List[Tuple[str, int, int, int]], Dict[str, int]]] = {}


def _machines_and_beats(blob: bytes, source: str) -> Tuple[W.Extract, List[Tuple[str, int, int, int]],
                                                           Dict[str, int]]:
    """``(extract, [(image, slot, state, beat tick)], {image: program origin})``, all from the bytes.

    Both columns are derived: the beat from R3's recovered thresholds (re-read out of the PATCHED
    image, so a moved threshold moves the beat) placed at the ``RUN_PROGRAM`` op's own sequence tick,
    which comes from re-walking the PATCHED stream.  Nothing here consults the edit lists.
    """
    key = _sha(blob) + "|" + source
    if key in _RECOVERY_MEMO:
        return _RECOVERY_MEMO[key]
    ex = W.extract_shots(blob, source)
    machines = W.recover_machines(blob, source)
    beats: List[Tuple[str, int, int, int]] = []
    origins: Dict[str, int] = {}
    for m in machines:
        slot = W._machine_slot(m)
        origin = ex.walk.program_starts.get((slot, 0))
        if origin is None:                                   # pragma: no cover
            continue
        origins[m.image] = origin
        for ph in m.phases:
            beats.append((m.image, slot, ph.state, origin + ph.start_tick))
    _RECOVERY_MEMO[key] = (ex, beats, origins)
    return _RECOVERY_MEMO[key]


def _camera_events(ex: W.Extract) -> Dict[Tuple[int, int, int, int], Tuple[int, int, int]]:
    """``{(slot, subfile, seq, code): (local frame, abs tick, install tick)}``."""
    out: Dict[Tuple[int, int, int, int], Tuple[int, int, int]] = {}
    for s in ex.shots:
        for si, seq in enumerate(s.camera["sequences"]):
            for ci, c in enumerate(seq):
                word = c.get("frame") or 0
                if not word:
                    break
                local = frame_num(word)
                out[(s.slot, s.index, si, ci)] = (local, s.op.seq_tick + local - 1, s.op.seq_tick)
    return out


def lock_table(blob: bytes, source: str = "ef227", window: int = 6) -> List[LockRow]:
    """The camera-vs-phase lock pairs this container carries -- W1's two-clocks law as a table."""
    ex, beats, _origins = _machines_and_beats(blob, source)
    cams = _camera_events(ex)
    rows: List[LockRow] = []
    for image, slot, state, beat in beats:
        cand = [(k, v) for k, v in cams.items() if k[0] == slot]
        if not cand:
            continue
        (k, v) = min(cand, key=lambda kv: (abs(kv[1][1] - beat), kv[1][1]))
        if abs(v[1] - beat) > window:
            continue
        rows.append(LockRow(LockId(image, state, k[0], k[1], k[2], k[3]), beat, v[1], v[0], v[2]))
    rows.sort(key=lambda r: (r.ident.machine, r.beat))
    return rows


def relock(blob: bytes, source: str, idents: Sequence[LockId]) -> Dict[LockId, LockRow]:
    """Re-time a FIXED set of lock identities against another container's bytes."""
    ex, beats, _origins = _machines_and_beats(blob, source)
    bmap = {(image, state): beat for image, _slot, state, beat in beats}
    cams = _camera_events(ex)
    out: Dict[LockId, LockRow] = {}
    for idt in idents:
        beat = bmap.get((idt.machine, idt.state))
        cam = cams.get((idt.slot, idt.subfile, idt.seq_index, idt.code_index))
        if beat is None or cam is None:
            raise RetimeError("lock identity %r vanished from the patched container -- a retime must "
                              "MOVE a pair, never delete one" % (idt,))
        out[idt] = LockRow(idt, beat, cam[1], cam[0], cam[2])
    return out


@dataclass
class Alignment:
    stock: List[LockRow]
    aligned: Dict[LockId, LockRow]
    misretime: Dict[LockId, LockRow]
    n: int
    cut_tick: int
    cut_local: int
    edited_shot: Tuple[int, int]
    stretched: Tuple[str, int]
    origins: Dict[str, Dict[str, int]]
    findings: List[Tuple[bool, str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(f[0] for f in self.findings)

    @property
    def drifted(self) -> List[LockId]:
        return [i for i, r in self.misretime.items() if r.lead != self.stock_lead(i)]

    def stock_lead(self, ident: LockId) -> int:
        return next(r.lead for r in self.stock if r.ident == ident)


def check_alignment(stock: bytes, aligned: bytes, misretime: bytes, n: int, cut_tick: int,
                    cut_local: int, edited_shot: Tuple[int, int], source: str = "ef227",
                    stretched: Tuple[str, int] = ("ef227:c0", 0)) -> Alignment:
    """THE RUNG'S OWN GATE, offline: re-derive BOTH clocks from the patched bytes and compare.

    Nothing here reads the edit lists to find the answer -- the beats come back out of the program
    image through R3's recovery, the cuts come back out of the camera blocks through the codec, and
    the sequence clock is re-walked from the stream.  The edit lists are used only to state the
    PREDICTION each artifact must satisfy:

    * a camera event moves iff its own install op moved (its tick >= the cut) or its local frame was
      rewritten (>= the cut's local frame, in the edited shot);
    * a phase beat moves iff its program's ``RUN_PROGRAM`` op moved -- **plus, on ALIGNED only, N
      more if it belongs to the STRETCHED machine and sits after the stretched phase, because that
      machine's own threshold moved underneath it.**

    So ALIGNED must keep every lead, and MIS-RETIME must break exactly c0's post-cut leads by N and
    leave c1's alone.  That asymmetry is the whole demonstration: c1's program origin is a sequence
    op, so its clock rides the presentation; c0's is upstream of the cut, so it does not.
    """
    rows = lock_table(stock, source)
    idents = [r.ident for r in rows]
    a = relock(aligned, source, idents)
    m = relock(misretime, source, idents)
    _exa, _ba, oa = _machines_and_beats(aligned, source)
    _exm, _bm, om = _machines_and_beats(misretime, source)
    _exs, _bs, os_ = _machines_and_beats(stock, source)

    res = Alignment(rows, a, m, n, cut_tick, cut_local, edited_shot, stretched,
                    {"stock": os_, "aligned": oa, "misretime": om})

    def add(ok: bool, tag: str, detail: str):
        res.findings.append((bool(ok), tag, detail))

    if not rows:                                             # pragma: no cover
        add(False, "lock table is empty", "no camera event lands within the window of any beat")
        return res

    # ---- ALIGNED: every lead preserved, and the pairs that should have MOVED did move
    bad = [r for r in rows if a[r.ident].lead != r.lead]
    add(not bad, "ALIGNED: every lock pair keeps its lead",
        "%d pairs, %d drifted%s" % (len(rows), len(bad),
                                    "" if not bad else " -- " + ", ".join(
                                        "%s s%d %+d -> %+d" % (x.ident.machine, x.ident.state,
                                                               x.lead, a[x.ident].lead)
                                        for x in bad)))
    moved = [r for r in rows if a[r.ident].cam != r.cam]
    add(len(moved) > 0, "ALIGNED: the post-cut pairs actually moved",
        "%d of %d pairs shifted by %+d on both clocks (a table that did not move would keep its "
        "leads trivially)" % (len(moved), len(rows), n))
    for r in moved:
        if a[r.ident].cam - r.cam != n or a[r.ident].beat - r.beat != n:
            add(False, "ALIGNED: pair %s s%d moved by N on both clocks" % (r.ident.machine,
                                                                           r.ident.state),
                "camera %+d, beat %+d (expected %+d / %+d)"
                % (a[r.ident].cam - r.cam, a[r.ident].beat - r.beat, n, n))

    # ---- the PREDICTION, per artifact, per pair
    stretch_image, stretch_state = stretched
    for tag, key, table, prog_moves in (("ALIGNED", "aligned", a, True),
                                        ("MIS-RETIME", "misretime", m, False)):
        bad_rows = []
        for r in rows:
            origin_s = res.origins["stock"][r.ident.machine]
            origin_new = res.origins[key][r.ident.machine]
            cam_moves = (r.install >= cut_tick) or \
                        ((r.ident.slot, r.ident.subfile) == edited_shot and r.local >= cut_local)
            want_cam = r.cam + (n if cam_moves else 0)
            # a beat moves with its own program origin ALWAYS (the RUN_PROGRAM op rides the
            # sequence); it moves N more only when E1 shipped, only in the machine whose threshold
            # moved, and only for phases that start after the stretched one.
            beat_shift = origin_new - origin_s
            if prog_moves and r.ident.machine == stretch_image and r.ident.state != stretch_state \
                    and (r.beat - origin_s) > 0:
                beat_shift += n
            want_beat = r.beat + beat_shift
            got = table[r.ident]
            if (got.cam, got.beat) != (want_cam, want_beat):
                bad_rows.append("%s s%d: cam %d (want %d) beat %d (want %d)"
                                % (r.ident.machine, r.ident.state, got.cam, want_cam,
                                   got.beat, want_beat))
        add(not bad_rows, "%s: every pair lands where the edit sets predict" % tag,
            "%d pairs checked%s" % (len(rows), "" if not bad_rows else " -- " + "; ".join(bad_rows)))

    # ---- MIS-RETIME: the asymmetry, stated as the falsifiable claim it is.
    #
    # THE CLASSIFIER IS THE PROGRAM ORIGIN, NOT THE CHUNK SLOT.  Until W5 this split was written as
    # ``slot == 0`` vs ``slot != 0``, which is ef227's topology spelled as a rule: its c0 is started
    # by a RUN_PROGRAM at sequence tick 0 and its c1 by one at tick 255.  The property that actually
    # produces the asymmetry is WHERE THAT OP SITS RELATIVE TO THE CUT -- a machine whose
    # RUN_PROGRAM fires at or after the cut rides the E2 shift wholesale, so its beats and its
    # camera events move together and its leads survive a program-less retime; a machine started
    # upstream of the cut does not move at all, so its post-cut leads drift by exactly N.  On ef227
    # the two readings agree; on any other effect only this one is true.
    origin_of = res.origins["stock"]
    upstream = [r for r in rows if origin_of.get(r.ident.machine, 0) < cut_tick]
    downstream = [r for r in rows if origin_of.get(r.ident.machine, 0) >= cut_tick]
    up_post = [r for r in upstream if r.cam >= cut_tick]
    up_pre = [r for r in upstream if r.cam < cut_tick]
    off = [r for r in up_post if m[r.ident].lead - r.lead != n]
    add(bool(up_post) and not off,
        "MIS-RETIME: the UPSTREAM machines' post-cut leads drift by %+d" % n,
        "%d post-cut pairs in machine(s) whose RUN_PROGRAM is before tick %d, %d off%s"
        % (len(up_post), cut_tick, len(off),
           "" if not off else " -- " + ", ".join(
               "%s s%d %+d -> %+d" % (x.ident.machine, x.ident.state, x.lead, m[x.ident].lead)
               for x in off)))
    still = [r for r in up_pre if m[r.ident].lead != r.lead]
    add(not still, "MIS-RETIME: the UPSTREAM machines' pre-cut leads are untouched",
        "%d pre-cut pair(s), %d drifted" % (len(up_pre), len(still)))
    dbad = [r for r in downstream if m[r.ident].lead != r.lead]
    add(bool(downstream) and not dbad, "MIS-RETIME: the DOWNSTREAM machines' leads are UNCHANGED",
        "%d pairs in machine(s) started at or after the cut (%s), %d drifted -- their program "
        "origin IS a sequence op, so their clock rides the presentation and their locks survive a "
        "program-less retime"
        % (len(downstream), ", ".join("%s@%d" % (k, v) for k, v in sorted(origin_of.items())
                                      if v >= cut_tick) or "none", len(dbad)))
    return res


def lock_lines(al: Alignment) -> List[str]:
    """The lock tables, printed.  Three columns of leads: stock, ALIGNED, MIS-RETIME."""
    L = ["  %-11s %-5s %-8s %-8s %-6s | %-8s %-8s %-6s | %-8s %-8s %-6s"
         % ("machine", "state", "beat", "cut", "lead", "beat", "cut", "lead", "beat", "cut", "lead"),
         "  %-11s %-5s %-26s | %-26s | %s" % ("", "", "-- stock --", "-- ALIGNED --",
                                              "-- MIS-RETIME --")]
    for r in al.stock:
        a, m = al.aligned[r.ident], al.misretime[r.ident]
        flag = "" if m.lead == r.lead else "   <<< DRIFTED %+d" % (m.lead - r.lead)
        L.append("  %-11s %-5d %-8d %-8d %-+6d | %-8d %-8d %-+6d | %-8d %-8d %-+6d%s"
                 % (r.ident.machine, r.ident.state, r.beat, r.cam, r.lead,
                    a.beat, a.cam, a.lead, m.beat, m.cam, m.lead, flag))
    return L


# ============================================================ (6) the self-check
@dataclass
class ByteReport:
    tag: str
    changed: List[int]
    by_domain: Dict[str, List[int]]
    meaning: Dict[int, str]
    unexplained: List[int]
    duration_hits: List[int]

    @property
    def ok(self) -> bool:
        return not self.unexplained and not self.duration_hits


@dataclass
class SelfCheck:
    bytes_aligned: ByteReport
    bytes_mis: ByteReport
    difference_ok: bool
    difference_detail: str
    roundtrip: Dict[str, Tuple[bool, int, int, int, Dict[str, bool]]]
    alignment: Alignment
    emu: List[EMU.Finding]
    bounds: List[Tuple[bool, str, str]]

    @property
    def ok(self) -> bool:
        return (self.bytes_aligned.ok and self.bytes_mis.ok and self.difference_ok
                and all(v[0] for v in self.roundtrip.values())
                and self.alignment.ok and all(f.ok for f in self.emu)
                and all(b[0] for b in self.bounds))


def account_bytes(b: Build, patched: bytes, tag: str, domains: Sequence[Domain]) -> ByteReport:
    """SELF-CHECK 1 -- every differing byte, named, in FOUR domains (three in-container + the text).

    W2's X1 posture, widened: the program bytes are named from the spec module's own edit list and
    guard values, the sequence byte is named by re-walking the stream, and the camera bytes are named
    by walking the CODEC's field order -- so a byte that landed in a duration, in an unknown field,
    or outside all three sets is reported as such and refuses the stage.
    """
    changed = [i for i in range(len(b.orig)) if b.orig[i] != patched[i]]
    owner: Dict[int, Tuple[str, str]] = {}
    for d in domains:
        for off, raw, why in d.writes:
            for i in range(len(raw)):
                owner[off + i] = (d.tag, why)

    field_map = block_field_map(b.shot)
    meaning: Dict[int, str] = {}
    by_domain: Dict[str, List[int]] = {d.tag: [] for d in domains}
    unexplained: List[int] = []
    duration_hits: List[int] = []
    for o in changed:
        if o not in owner:
            unexplained.append(o)
            meaning[o] = "UNEXPLAINED -- not inside any declared edit domain"
            continue
        tagd, why = owner[o]
        by_domain[tagd].append(o)
        if tagd == "E1":
            img = o - PE.IMAGE_BASE
            guard = PE.EXPECT_OLD.get(o & ~1)
            meaning[o] = ("program image 0x%04X (%s); stock u16 guard %s"
                          % (img, why.split(":")[0],
                             "0x%04X" % guard if guard is not None else "n/a"))
        elif tagd == "E2":
            meaning[o] = "sequence stream: the WAIT at %#x, arg2" % b.anchor.op_at
        else:
            rel = o - b.shot.lo
            name = field_map.get(rel)
            if name is None:
                unexplained.append(o)
                meaning[o] = ("UNEXPLAINED -- block+%d is not inside any Code sub-block (the outer "
                              "flags, the offset table, the selector group or the terminator)" % rel)
                continue
            meaning[o] = "shot %s block+%d = %s" % (b.shot_letter, rel, name)
            if not name.endswith(("frame.lo", "frame.hi")):
                unexplained.append(o)
                meaning[o] += "  <<< NOT A FRAME WORD"
            if _DURATION_RE.search(name):
                duration_hits.append(o)
                meaning[o] += "  <<< A DURATION FIELD -- forbidden"
    return ByteReport(tag, changed, by_domain, meaning, unexplained, duration_hits)


def roundtrip_check(b: Build, patched: bytes, tag: str):
    """SELF-CHECK 2 -- strict re-parse, all camera blocks byte-exact, W1's four invariants."""
    header_ok, cursor_end = True, 0
    try:
        c = EC.parse_header(patched, strict=True)
        cursor_end = c.cursor_end
    except EC.ContainerError:                                # pragma: no cover
        header_ok = False
        c = EC.parse_header(patched, strict=False)
        cursor_end = c.cursor_end
    ex = W.extract_shots(patched, "ef%03d" % b.effect)
    ok = sum(1 for s in ex.shots if s.roundtrip()[0])
    arc = W.id2_directory(patched, c, b.shot.slot)
    blk = bytes(patched[b.shot.lo:b.shot.hi])
    inv = R.block_invariants(patched, arc, b.shot.index, blk)
    again = W.serialize_camera_block(W.parse_camera_block(blk))
    inv["i5_edited_block_reserialises_byte_exact"] = (again == blk)
    inv["i6_block_length_unchanged"] = (len(blk) == b.shot.size)
    good = (header_ok and cursor_end == len(patched) and ok == len(ex.shots)
            and all(inv.values()))
    return (good, cursor_end, ok, len(ex.shots), inv)


def emulator_gate(b: Build) -> List[EMU.Finding]:
    """SELF-CHECK 4 -- w3_clock_emu's own checks, run against BOTH staged containers.

    The aligned container must satisfy the PATCHED invariants (both ramps land on 4096 at the new
    last tick, every beat unmoved, nothing inverts); the mis-retime container must satisfy the STOCK
    ones, because its program is byte-identical stock -- that is the machine-checked statement of
    what the two artifacts differ by.
    """
    sc = EMU.read_consts(b.orig)
    ac = EMU.read_consts(b.aligned)
    mc = EMU.read_consts(b.misretime)
    ref = EMU.read_consts(PE.apply_edits(b.orig))
    f: List[EMU.Finding] = [
        EMU.Finding(ac == ref, "ALIGNED program == the spec module's own patch",
                    "threshold %d, /%d progress (shift %d), /%d arrival (shift %d)"
                    % (ac.threshold, ac.prog_divisor, ac.prog_shift, ac.arr_divisor, ac.arr_shift)),
        EMU.Finding(mc == sc, "MIS-RETIME program is byte-identical STOCK",
                    "threshold %d, /%d progress, /%d arrival -- E1 omitted entirely"
                    % (mc.threshold, mc.prog_divisor, mc.arr_divisor)),
        # the reciprocal census, re-probed out of BOTH containers: exactly two reciprocals are
        # coupled to the phase length, and the other three encode their own gate or domain.  This is
        # the machine-checked form of "do not retune the /12 or the /46 for symmetry".
        EMU.Finding(sc.prog_divisor == sc.threshold
                    and sc.arr_divisor == sc.threshold - sc.g_creature,
                    "STOCK: the two phase-coupled reciprocals divide by the phase",
                    "/%d == the threshold, /%d == threshold-%d"
                    % (sc.prog_divisor, sc.arr_divisor, sc.g_creature)),
        EMU.Finding(sc.beam_divisor == sc.g_beam and sc.intro_divisor == sc.g_intro,
                    "STOCK: the other reciprocals encode GATES, not the phase length",
                    "light column /%d == its own clock<%d gate; intro /%d == clock<%d; the vertical "
                    "curve's /%d is Q-domain -- none is retuned"
                    % (sc.beam_divisor, sc.g_beam, sc.intro_divisor, sc.g_intro, sc.ycurve_divisor)),
        EMU.Finding(ac.prog_divisor == ac.threshold
                    and ac.arr_divisor == ac.threshold - ac.g_creature
                    and ac.beam_divisor == sc.beam_divisor and ac.intro_divisor == sc.intro_divisor,
                    "ALIGNED: both phase reciprocals re-divide by the NEW phase",
                    "/%d and /%d; the gate-coupled /%d and /%d are untouched"
                    % (ac.prog_divisor, ac.arr_divisor, ac.beam_divisor, ac.intro_divisor)),
        EMU.Finding(sum(1 for x, y in zip(b.orig, PE.apply_edits(b.orig, PE.build_edits(0)))
                        if x != y) == 0,
                    "N = 0 reproduces the stock bytes",
                    "the derivation that picked /117 and /93 is a no-op at zero stretch, so its /69 "
                    "and /45 ARE the shipping constants -- it reads the compiler's idiom rather "
                    "than rationalising a fit"),
    ]
    f += EMU.check_stock_endpoints(sc)
    f += EMU.check_stock_endpoints(mc)                       # the mis-retime's program, on stock terms
    f += EMU.check_retime(sc, ac, b.n)
    f += EMU.check_half_patch(b.orig)
    f += EMU.check_mis_retime(sc, b.n)
    f += EMU.check_same_length(b.orig, PE.apply_edits(b.orig))
    f.append(EMU.Finding(PE.changed_byte_count(b.orig) == 12, "E1 changes 12 bytes",
                         "%d bytes differ across %d sites"
                         % (PE.changed_byte_count(b.orig), len(PE.PROGRAM_EDITS))))
    return f


def bounds_check(b: Build, patched_aligned: bytes) -> List[Tuple[bool, str, str]]:
    """SELF-CHECK 5 -- the field-level bounds, re-read out of the bytes we are about to stage."""
    out: List[Tuple[bool, str, str]] = []
    got = patched_aligned[b.anchor.arg_at]
    out.append((got == b.anchor.new and WAIT_MIN <= got <= WAIT_MAX,
                "WAIT arg2 in the attested envelope",
                "%d -> %d, envelope [%d, %d] (u8 ceiling 255; arg2 == 0 unattested corpus-wide)"
                % (b.anchor.old, got, WAIT_MIN, WAIT_MAX)))
    ok_words, detail = True, []
    for e in b.frame_edits:
        w = _u16(patched_aligned, e.site.file_off)
        num = frame_num(w)
        if w != e.new_word or not FRAME_MIN <= num <= FRAME_MAX \
                or frame_flags(w) != frame_flags(e.site.word):
            ok_words = False
            detail.append("block+%d word %#06x" % (e.site.blk_off, w))
    out.append((ok_words, "every frame word in 1..1023 with 0xFC00 preserved",
                "%d words rewritten, %d..%d -> %d..%d%s"
                % (len(b.frame_edits), min(e.site.local for e in b.frame_edits),
                   max(e.site.local for e in b.frame_edits),
                   min(e.new_local for e in b.frame_edits), max(e.new_local for e in b.frame_edits),
                   "" if ok_words else " -- BAD: " + ", ".join(detail))))
    # the whole stream's tick map moved exactly the way one WAIT byte says it must
    a, c = op_tick_map(b.orig), op_tick_map(patched_aligned)
    bad = [at for at in a if c.get(at) != a[at] + (b.n if a[at] >= b.cut_tick else 0)]
    n_moved = sum(1 for at in a if a[at] >= b.cut_tick)
    out.append((not bad and set(a) == set(c),
                "the sequence tick map shifted exactly at the cut",
                "%d of %d ops move %+d, %d stay; %d op offsets changed"
                % (n_moved, len(a), b.n, len(a) - n_moved, len(bad))))
    if b.text is not None:
        t = b.text
        out.append((t.moved_beats > 0 and t.new_total - t.stock_total == t.delta,
                    "the text .seq clock moved by exactly the delta",
                    "one Wait line Time=%d -> %d; %d downstream Wait beats shift %+d; the file's "
                    "own end moves %d -> %d"
                    % (t.anchor.time, t.new_time, t.moved_beats, t.delta, t.stock_total,
                       t.new_total)))
    if b.player is not None:
        p = b.player
        out.append((p.ok,
                    "the OUTER-OUTER script carries no beat after the boundary",
                    "%s: %d literal Wait line(s), clock reaches %d, boundary %d%s"
                    % (os.path.basename(p.path), p.n_wait_lines, p.max_tick, p.boundary,
                       "" if not p.needs_retime else
                       "  <<< ACKNOWLEDGED DRIFT (acknowledge_uncoretimed = true)")))
    return out


def self_check(b: Build) -> SelfCheck:
    d_prog, d_seq, d_cam = b.domains
    ba = account_bytes(b, b.aligned, "ALIGNED", b.domains)
    bm = account_bytes(b, b.misretime, "MIS-RETIME", [d_seq, d_cam])
    sa, sm = set(ba.changed), set(bm.changed)
    prog_changed = {o for o in d_prog.offsets if b.orig[o] != b.aligned[o]}
    diff_ok = (sm <= sa and (sa - sm) == prog_changed
               and all(b.aligned[o] == b.misretime[o] for o in sm))
    detail = ("aligned %d bytes, mis-retime %d bytes, difference %d == the %d program bytes that "
              "actually differ (of %d written across %d sites); every shared byte identical"
              % (len(sa), len(sm), len(sa - sm), len(prog_changed),
                 sum(len(raw) for _o, raw, _w in d_prog.writes), len(d_prog.writes)))
    rt = {"ALIGNED": roundtrip_check(b, b.aligned, "ALIGNED"),
          "MIS-RETIME": roundtrip_check(b, b.misretime, "MIS-RETIME")}
    al = check_alignment(b.orig, b.aligned, b.misretime, b.n, b.cut_tick, b.cut_local,
                         (b.shot.slot, b.shot.index), "ef%03d" % b.effect,
                         stretched=b.stretched or ("ef%03d:c0" % b.effect, 0))
    emu = emulator_gate(b)
    bnd = bounds_check(b, b.aligned)
    return SelfCheck(ba, bm, diff_ok, detail, rt, al, emu, bnd)


# ============================================================ (7) staging + the deploy ledger
def _mod_paths(mod_root, ef_id: int) -> Dict[str, Path]:
    return {
        "container": Path(mod_root).joinpath(*MOD_SUBPATH.split("/"), "ef%03d" % ef_id),
        "text": Path(mod_root).joinpath(*TEXT_SUBPATH.split("/"), "ef%03d" % ef_id, "Sequence.seq"),
    }


def stage(b: Build, root=None, game_root=None, allow_install: bool = False) -> dict:
    """Write both artifacts, the text override, and the three live-deploy scripts.

    STAGE by default, exactly as W2: ``_refuse_repo_path`` always, ``_refuse_install_path`` unless
    ``--live``.  The scripts this emits are what actually touch the install, and they are stdlib-only
    so the person running them needs nothing from the kit.
    """
    root = Path(R._refuse_repo_path(root or SCRATCH_ROOT))
    if not allow_install:
        R._refuse_install_path(root, game_root)
    mod_root = root / "mod"
    mis_dir = root / "misretime"
    ledger = R._Ledger(root / "backups")

    paths = _mod_paths(mod_root, b.effect)
    if paths["container"].suffix:                            # pragma: no cover
        raise RetimeError("the container override must be EXTENSIONLESS (LoadFromDisc reads the raw "
                          "path, so ef227.bytes would never be found)")
    sha_c = ledger.write_bytes(paths["container"], b.aligned)
    sha_m = ledger.write_bytes(mis_dir / ("ef%03d" % b.effect), b.misretime)
    sha_t = ledger.write_bytes(paths["text"], b.text.data) if b.text else None

    live_mod = Path(game_root) / "FF9CustomMap" if game_root else None
    scripts = {}
    if live_mod is not None:
        live = _mod_paths(live_mod, b.effect)
        common = {
            "effect": b.effect,
            "mod_root": str(live_mod),
            "snapshot_dir": str(root / "live-snapshot"),
            "revert_script": str(root / ("revert_summon_retime_%d.py" % b.effect)),
            "manifest_roots": [str(Path(live_mod).joinpath(*MOD_SUBPATH.split("/"))),
                               str(Path(live_mod).joinpath(*TEXT_SUBPATH.split("/"),
                                                           "ef%03d" % b.effect))],
            "prune_stop": str(live_mod),
        }
        text_entry = ([{"src": str(paths["text"]), "dest": str(live["text"]), "sha256": sha_t}]
                      if b.text else [])
        for name, container, sha in (("aligned", paths["container"], sha_c),
                                     ("misretime", mis_dir / ("ef%03d" % b.effect), sha_m)):
            plan = dict(common)
            plan["variant"] = name
            plan["targets"] = [{"src": str(container), "dest": str(live["container"]),
                                "sha256": sha}] + text_entry
            p = _write_script(root / ("deploy_%s.py" % name), _DEPLOY_TEMPLATE, plan)
            scripts["deploy_%s" % name] = str(p)
        p = _write_script(root / ("revert_summon_retime_%d.py" % b.effect), _REVERT_TEMPLATE, common)
        scripts["revert"] = str(p)

    manifest = {
        "spec": b.spec_path, "effect": b.effect, "label": b.label, "n": b.n,
        "stock_sha256": b.sha_in, "aligned_sha256": sha_c, "misretime_sha256": sha_m,
        "text_sha256": sha_t, "cut_tick": b.cut_tick, "cut_local": b.cut_local,
        "aligned": str(paths["container"]), "misretime": str(mis_dir / ("ef%03d" % b.effect)),
        "text": str(paths["text"]) if b.text else None,
        "scripts": scripts,
    }
    from ff9mapkit import fsutil
    fsutil.atomic_write_text(root / "build_manifest.json",
                             json.dumps(manifest, indent=2), encoding="utf-8", newline="\n")
    manifest["staged_files"] = len(ledger.files)
    return manifest


def _write_script(path: Path, template: str, plan: dict) -> Path:
    from ff9mapkit import fsutil
    body = template.replace("__PLAN__", repr(json.dumps(plan, indent=2)))
    fsutil.atomic_write_text(path, body, encoding="utf-8", newline="\n")
    return path


_LEDGER_PREAMBLE = '''
def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(roots):
    """A tree hash of every file under each root -- the before/after evidence."""
    out = {}
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                p = Path(dirpath) / f
                out[str(p)] = _sha(p)
    return out


def manifest_hash(m):
    return hashlib.sha256("\\n".join("%s %s" % (k, m[k]) for k in sorted(m)).encode()).hexdigest()
'''


_DEPLOY_TEMPLATE = '''#!/usr/bin/env python3
"""Auto-generated LIVE deploy for a TIER W3 summon retime -- stdlib only, no ff9mapkit import.

Copies one staged artifact (and the shared text .seq co-retime) into the live FF9CustomMap, taking a
FIRST-DEPLOY SNAPSHOT of whatever the mod folder held beforehand.  The snapshot is written once and
never overwritten, so deploying the other variant on top of this one still reverts all the way back
to the pre-W3 state (which currently holds W2's 4-byte camera override, and NO text override).

Idempotent: re-running copies the same bytes and leaves the snapshot alone.
"""
import hashlib, json, os, shutil, sys
from pathlib import Path

PLAN = json.loads(__PLAN__)
''' + _LEDGER_PREAMBLE + '''

def main():
    mod_root = Path(PLAN["mod_root"])
    if not mod_root.is_dir():
        print("FAIL: mod folder not found: %s" % mod_root); return 1
    if (mod_root / "ModFileList.txt").exists():
        print("REFUSING: %s has a ModFileList.txt. TryFindAssetInModOnDisc TRUSTS that list and "
              "never calls File.Exists, so an unlisted override is INVISIBLE -- and the listing "
              "format for the StreamingAssets lane is unverified. Handle the list by hand, then "
              "re-run." % mod_root)
        return 1
    for t in PLAN["targets"]:
        if not Path(t["src"]).is_file():
            print("FAIL: staged artifact missing: %s" % t["src"]); return 1
        got = _sha(t["src"])
        if got != t["sha256"]:
            print("FAIL: %s sha256 %s != the build's %s -- the staged artifact changed after the "
                  "build; re-run `retime.py build`." % (t["src"], got, t["sha256"]))
            return 1

    before = manifest(PLAN["manifest_roots"])
    snap_dir = Path(PLAN["snapshot_dir"])
    snap_file = snap_dir / "snapshot.json"
    if snap_file.exists():
        snap = json.loads(snap_file.read_text(encoding="utf-8"))
        print("snapshot: reusing the FIRST-DEPLOY snapshot at %s (%s)"
              % (snap_file, snap.get("taken")))
    else:
        snap_dir.mkdir(parents=True, exist_ok=True)
        entries = []
        for t in PLAN["targets"]:
            dest = Path(t["dest"])
            if dest.exists():
                backup = snap_dir / ("%s__%s.pre-w3" % (dest.parent.name, dest.name))
                shutil.copyfile(dest, backup)
                entries.append({"dest": str(dest), "existed": True,
                                "sha256": _sha(dest), "backup": str(backup)})
            else:
                entries.append({"dest": str(dest), "existed": False, "sha256": None,
                                "backup": None})
        snap = {"taken": "first deploy (%s)" % PLAN["variant"], "entries": entries,
                "pre_manifest": before, "pre_manifest_hash": manifest_hash(before),
                "manifest_roots": PLAN["manifest_roots"], "prune_stop": PLAN["prune_stop"]}
        tmp = snap_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(snap, indent=2), encoding="utf-8")
        os.replace(tmp, snap_file)
        print("snapshot: TAKEN -> %s" % snap_file)
        for e in entries:
            print("   %-6s %s%s" % ("saved" if e["existed"] else "absent", e["dest"],
                                    "  (sha %s)" % e["sha256"][:16] if e["existed"] else ""))

    for t in PLAN["targets"]:
        dest = Path(t["dest"])
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(t["src"], dest)
        if _sha(dest) != t["sha256"]:
            print("FAIL: write verification at %s -- readback != what we wrote" % dest); return 1
        print("deployed %s  (%d B, sha %s)" % (dest, dest.stat().st_size, t["sha256"][:16]))

    after = manifest(PLAN["manifest_roots"])
    print()
    print("tree manifest before : %s  (%d files)" % (manifest_hash(before), len(before)))
    print("tree manifest after  : %s  (%d files)" % (manifest_hash(after), len(after)))
    print("variant deployed     : %s" % PLAN["variant"].upper())
    print("revert with          : py %s" % PLAN["revert_script"])
    print()
    print("NOTE: the container override is re-read when the effect is next LOADED and the text .seq")
    print("      is re-read on EVERY cast -- no relaunch, no field reload. Recast to see it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


_REVERT_TEMPLATE = '''#!/usr/bin/env python3
"""Auto-generated revert for the TIER W3 summon retime -- stdlib only, no ff9mapkit import.

Restores whatever the live mod folder held before the FIRST W3 deploy: the W2 camera override goes
back byte-for-byte, and any file W3 newly created (the text .seq override and its ef### folder) is
deleted.  Idempotent -- running it twice restores the same bytes twice and reports the same verdict.
"""
import hashlib, json, os, shutil, sys
from pathlib import Path

PLAN = json.loads(__PLAN__)
''' + _LEDGER_PREAMBLE + '''

def main():
    snap_file = Path(PLAN["snapshot_dir"]) / "snapshot.json"
    if not snap_file.exists():
        print("nothing to revert: no snapshot at %s (was the deploy ever run?)" % snap_file)
        return 0
    snap = json.loads(snap_file.read_text(encoding="utf-8"))
    stop = Path(snap.get("prune_stop") or PLAN["prune_stop"]).resolve()
    for e in snap["entries"]:
        dest = Path(e["dest"])
        if e["existed"]:
            backup = Path(e["backup"])
            if not backup.exists():
                print("FAIL: snapshot copy missing: %s" % backup); return 1
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(backup, dest)
            ok = _sha(dest) == e["sha256"]
            print("restored %s <- %s  %s" % (dest, backup.name, "OK" if ok else "SHA MISMATCH"))
            if not ok:
                return 1
        else:
            if dest.exists():
                dest.unlink()
                print("deleted  %s" % dest)
            parent = dest.parent
            while parent.resolve() != stop and parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
                print("pruned   %s" % parent)
                parent = parent.parent

    after = manifest(snap.get("manifest_roots") or PLAN["manifest_roots"])
    same = manifest_hash(after) == snap["pre_manifest_hash"]
    print()
    print("tree manifest pre-W3 : %s  (%d files)" % (snap["pre_manifest_hash"],
                                                     len(snap["pre_manifest"])))
    print("tree manifest now    : %s  (%d files)" % (manifest_hash(after), len(after)))
    print("verdict              : %s" % ("EXACT RESTORE" if same else "DRIFT -- see the two hashes"))
    print()
    print("the snapshot is KEPT so a re-deploy still reverts to the true pre-W3 state; delete")
    print("%s by hand only if you want to re-baseline." % snap_file)
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


# ============================================================ (8) reporting
def describe(b: Build) -> List[str]:
    L = ["ef%03d  %s    N = %+d ticks" % (b.effect, b.label, b.n),
         "  stock source   : %s" % b.source,
         "  stock sha256   : %s  (drift guard %s)"
         % (b.sha_in, "REGISTERED" if b.effect in R.EXPECTED_STOCK_SHA else "none -- unguarded"),
         "  aligned sha    : %s" % b.sha_aligned,
         "  misretime sha  : %s" % b.sha_mis,
         "  container      : %d B in, %d B out (same length, both artifacts)"
         % (len(b.orig), len(b.aligned)),
         "  the cut        : seq tick %d (the LAST tick of c0 s0; the boundary is %d) = shot %s "
         "local frame %d" % (b.cut_tick, b.cut_tick + 1, b.shot_letter, b.cut_local),
         ""]
    L.append("  E1  THE PROGRAM CLOCK -- %d sites, %d bytes written, %d actually differ"
             % (len(PE.PROGRAM_EDITS), sum(e.old_len for e in PE.PROGRAM_EDITS),
                PE.changed_byte_count(b.orig)))
    for off, ln, nb, why in PE.PROGRAM_EDITS:
        L.append("      file %#08x (image 0x%04X)  old 0x%04X -> new 0x%s   %s"
                 % (off, off - PE.IMAGE_BASE, PE.EXPECT_OLD[off], nb[::-1].hex().upper(),
                    why.split(":")[0]))
    L.append("")
    L.append("  E2  THE SEQUENCE CLOCK -- one byte")
    L.append("      file %#08x  WAIT arg2 %d -> %d   (spans tick %d -> %d)"
             % (b.anchor.arg_at, b.anchor.old, b.anchor.new, b.anchor.from_tick, b.anchor.to_tick))
    a, c = op_tick_map(b.orig), op_tick_map(b.aligned)
    L.append("      %d of %d sequence ops move %+d; none of THEIR bytes change"
             % (sum(1 for at in a if a[at] >= b.cut_tick), len(a), b.n))
    L.append("")
    L.append("  E3  THE CAMERA CLOCK -- %d frame words in shot %s (chunk %d sub-file %d, %d B)"
             % (len(b.frame_edits), b.shot_letter, b.shot.slot, b.shot.index, b.shot.size))
    for e in b.frame_edits:
        L.append("      file %#08x (block+%-3d) seq%d Code%-2d  local %3d -> %-3d  abs %3d -> %-3d"
                 % (e.site.file_off, e.site.blk_off, e.site.seq_index, e.site.code_index,
                    e.site.local, e.new_local, b.shot.op.seq_tick + e.site.local - 1,
                    b.shot.op.seq_tick + e.new_local - 1))
    L.append("      durations changed: 0 (the schedule is the frame word; a duration parametrises "
             "the motion a keyframe STARTS -- A3 section 0)")
    if b.text:
        t = b.text
        L.append("")
        L.append("  E4  THE OUTER TEXT CLOCK -- one Wait line in %s" % os.path.basename(t.path))
        L.append("      Wait #%d (file line %d): Time=%d -> %d   (spans outer tick %d -> %d, which "
                 "is the span containing the boundary %d)"
                 % (t.anchor.index, t.anchor.line_no + 1, t.anchor.time, t.new_time,
                    t.anchor.start, t.anchor.end, t.boundary))
        L.append("      %d downstream Wait beats shift %+d; the script's own end moves %d -> %d"
                 % (t.moved_beats, t.delta, t.stock_total, t.new_total))
        L.append("      stock sha %s -> edited sha %s" % (t.stock_sha[:16], t.new_sha[:16]))
    if b.player:
        L.append("")
        L.append("  E4 audit -- %s" % os.path.basename(b.player.path))
        L.append("      %s" % b.player.verdict)
    return L


def check_lines(b: Build) -> List[str]:
    c = b.check
    L = ["", "=" * 96, "THE SELF-CHECK -- the tool refuses to stage if any of these fails", ""]
    for rep in (c.bytes_aligned, c.bytes_mis):
        L.append("  1. BYTE ACCOUNTING (%s): %d byte(s) differ from stock in the whole %d B container"
                 % (rep.tag, len(rep.changed), len(b.orig)))
        for tag, offs in sorted(rep.by_domain.items()):
            if offs:
                L.append("       %s: %d byte(s)" % (tag, len(offs)))
        for o in rep.changed:
            L.append("       %#08x  %s" % (o, rep.meaning[o]))
        L.append("       unexplained: %d   in a duration field: %d"
                 % (len(rep.unexplained), len(rep.duration_hits)))
    L.append("     ALIGNED minus MIS-RETIME == the program edit set: %s" % c.difference_ok)
    L.append("       %s" % c.difference_detail)
    L.append("")
    L.append("  2. ROUND-TRIP")
    for tag, (good, cur, ok, tot, inv) in sorted(c.roundtrip.items()):
        L.append("     %-11s strict re-parse cursor_end %#x == size %#x : %s"
                 % (tag, cur, len(b.aligned), cur == len(b.aligned)))
        L.append("     %-11s camera blocks byte-exact through the UNMODIFIED codec: %d/%d"
                 % ("", ok, tot))
        for k, v in sorted(inv.items()):
            L.append("     %-11s %-42s %s" % ("", k, v))
    L.append("")
    L.append("  3. THE ALIGNMENT CHECKER (the rung's own gate, offline)")
    for ok, tag, detail in c.alignment.findings:
        L.append("     [%s] %-52s %s" % ("PASS" if ok else "FAIL", tag, detail))
    L.append("")
    L += lock_lines(c.alignment)
    L.append("")
    L.append("  4. THE EMULATOR GATE (w3_clock_emu, on BOTH containers)")
    fails = [f for f in c.emu if not f.ok]
    L.append("     %d checks, %d failures" % (len(c.emu), len(fails)))
    for f in fails:
        L.append("     %s" % f)
    for f in c.emu[:2]:
        L.append("     %s" % f)
    L.append("")
    L.append("  5. BOUNDS")
    for ok, tag, detail in c.bounds:
        L.append("     [%s] %-52s %s" % ("PASS" if ok else "FAIL", tag, detail))
    L.append("")
    L.append("  SELF-CHECK: %s" % ("PASS -- staging allowed" if c.ok else "FAIL -- refusing to stage"))
    return L


def residual_lines(b: Build) -> List[str]:
    sc, ac = EMU.read_consts(b.orig), EMU.read_consts(b.aligned)
    L = ["", "  RESIDUALS (deliberate consequences of the locked policy, re-derived from the bytes):"]
    for i, r in enumerate(EMU.residuals(sc, ac), 1):
        L.append("   %d. %s" % (i, r))
    return L


# ============================================================ (8b) THE TWO-CLOCKS ALIGNMENT REPORT
#
# The reading half of this lane was always corpus-general -- ``lock_table``, ``relock``,
# ``_machines_and_beats`` and ``_camera_events`` run unmodified on every clean-switch effect.  What
# was missing is the thing that makes such a table trustworthy: its PAIRING QUALITY.  A
# nearest-neighbour match inside a 6-tick window will happily return a "lock pair" for two events
# that merely happen to be near each other, and 37 of the corpus's 85 clock-guarded boundaries have
# no pair at all.  This report therefore publishes, per boundary, how good the pairing is and what
# each of the four clocks could actually derive -- and never calls a loose correlation a lock.

#: the pairing window ``lock_table`` uses.  Corpus-measured lead distribution over the 48 boundaries
#: that DO pair: |lead| <= 1 on 35 of them, but the tail runs -6..+5.  ef227's uniform -1 is the
#: tightest case in the corpus, not the norm -- so a cut is taken from the boundary's OWN lead.
LOCK_WINDOW = 6

#: the nominal stretch the report probes E2/E3 with.  Small on purpose: the point is whether an
#: anchor and a frame-edit set EXIST at this boundary, not whether some particular N fits.
PROBE_N = 1


@dataclass
class PairQuality:
    """How well this effect's two clocks actually pair -- published, never assumed."""
    beats_total: int
    pairs_found: int
    nn_distances: List[int]                      # |cam - beat| for the nearest camera event, per beat
    duplicate_codes: Dict[Tuple[int, int, int, int], List[str]]
    window: int = LOCK_WINDOW

    @property
    def collisions(self) -> int:
        return sum(1 for v in self.duplicate_codes.values() if len(v) > 1)

    @property
    def verdict(self) -> str:
        if not self.beats_total:
            return "no beats"
        if not self.pairs_found:
            return "NO LOCK -- not one camera event lands within %d ticks of any beat" % self.window
        frac = self.pairs_found / self.beats_total
        tag = "LOCKED" if frac >= 0.75 and not self.collisions else "LOOSELY CORRELATED"
        return ("%s -- %d of %d beats pair (%.0f%%), %d Code collision(s)"
                % (tag, self.pairs_found, self.beats_total, 100 * frac, self.collisions))


@dataclass
class BoundaryFlags:
    """What each of the four clocks could derive at ONE phase boundary.

    A row is the boundary at the END of ``state`` -- the tick its successor begins on.  That is the
    tick every clock in this rung is measured against: the threshold that moves belongs to ``state``,
    but the lock pair, the sequence anchor, the camera cut and the outer text's ``Wait`` are all
    anchored to where the NEXT phase starts.
    """
    machine: str
    state: int
    next_state: Optional[int]
    beat: int                                    # the successor's start tick == the boundary
    cut: Optional[int]                           # the paired camera event's tick, or None
    lead: Optional[int]
    origin: int
    #: if THIS boundary were the cut: the machines whose RUN_PROGRAM fires before it (their clocks
    #: do NOT ride the sequence shift, so an E1-less retime drifts their post-cut leads by N) and
    #: the machines started at or after it (they ride the presentation and their leads survive).
    #: This is the classification ``check_alignment`` now makes -- program origin, never chunk slot.
    upstream_machines: Tuple[str, ...] = ()
    downstream_machines: Tuple[str, ...] = ()
    e1_threshold: str = ""                       # the slti site, or why not
    e1_recips: str = ""                          # reciprocals found / peers / disposition, or refusal
    e2: str = ""                                 # exact | containing (slack k) | none
    e3: str = ""                                 # pass (k words) | straddle | no-shot | ...
    e4: str = ""                                 # anchor + PlayerSequence verdict, or "(no install)"


@dataclass
class EffectReport:
    effect: int
    source: str
    machines: List[Tuple[str, int, int, Optional[int]]]   # (image, phases, total ticks, origin)
    quality: PairQuality
    locks: List[LockRow]
    boundaries: List[BoundaryFlags]
    notes: List[str] = field(default_factory=list)


def _nearest(cams: Dict, slot: int, beat: int) -> Optional[Tuple[Tuple, Tuple]]:
    cand = [(k, v) for k, v in cams.items() if k[0] == slot]
    if not cand:
        return None
    return min(cand, key=lambda kv: (abs(kv[1][1] - beat), kv[1][1]))


def _e2_flag(blob: bytes, cut: int) -> str:
    """Exact / containing / none, and the containing WAIT's slack when there is no exact anchor."""
    try:
        a = find_seq_anchor(blob, cut, PROBE_N)
        return "exact (WAIT @%#x, %d -> %d)" % (a.op_at, a.from_tick, a.to_tick)
    except RetimeError:
        pass
    waits = [o for o in seq_ops(blob) if o.code == OP_WAIT and o.arg1 == 0]
    holding = [w for w in waits if w.tick < cut < w.tick + w.arg2]
    if len(holding) == 1:
        w = holding[0]
        return ("containing (WAIT @%#x spans %d -> %d, slack %d) -- an exact anchor needs the "
                "record SPLIT, a byte insert never cast" % (w.at, w.tick, w.tick + w.arg2,
                                                            w.tick + w.arg2 - cut))
    ending = [w for w in waits if w.tick + w.arg2 == cut]
    if len(ending) > 1:
        return "AMBIGUOUS (%d WAITs end on tick %d)" % (len(ending), cut)
    return "none (no WAIT ends on or contains tick %d)" % cut


def _e3_flag(ex: W.Extract, slot: int, subfile: int, cut: int) -> str:
    shot = next((s for s in ex.shots if s.slot == slot and s.index == subfile), None)
    if shot is None:
        return "no-shot (chunk %d sub-file %d resolves to no camera block)" % (slot, subfile)
    cut_local = cut - shot.op.seq_tick + 1
    try:
        edits = find_frame_edits(shot, cut_local, PROBE_N)
        return "pass (%d frame word(s) at or after local %d)" % (len(edits), cut_local)
    except RetimeError as exc:
        head = str(exc).split(":")[0].split("--")[0].strip()
        if "STRADDLE" in str(exc):
            return "straddle (a pre-cut interpolation is still running at local %d)" % cut_local
        return "refused (%s)" % head[:70]


def _e4_flag(game_root, effect: int, boundary: int) -> str:
    if game_root is None:
        return "(no install -- not probed)"
    src = _game_text_path(game_root, effect, "Sequence.seq")
    if not src.exists():
        return "no Sequence.seq"
    try:
        _lines, waits = parse_seq_text(src.read_bytes().decode("utf-8"))
    except Exception as exc:                                 # pragma: no cover
        return "Sequence.seq unreadable (%s)" % type(exc).__name__
    hits = [w for w in waits if w.start <= boundary < w.end]
    anchor = ("anchor Wait #%d (%d -> %d)" % (hits[0].index, hits[0].start, hits[0].end)
              if len(hits) == 1 else "NO unique Wait spans outer tick %d (%d hits, %d Wait lines)"
              % (boundary, len(hits), len(waits)))
    ps = _game_text_path(game_root, effect, "PlayerSequence.seq")
    if not ps.exists():
        return "%s; no PlayerSequence.seq" % anchor
    try:
        _l2, pw = parse_seq_text(ps.read_bytes().decode("utf-8"))
    except Exception:                                        # pragma: no cover
        return "%s; PlayerSequence.seq unreadable" % anchor
    pmax = pw[-1].end if pw else 0
    return ("%s; PlayerSequence %d Wait line(s) reaching tick %d -- %s"
            % (anchor, len(pw), pmax,
               "CO-RETIME NEEDED" if pmax > boundary else "no beat after the boundary"))


def effect_report(blob: bytes, effect: int, game_root=None, window: int = LOCK_WINDOW,
                  derive: bool = True) -> EffectReport:
    """The per-effect two-clocks alignment report: pairing quality + per-boundary derivability."""
    source = "ef%03d" % effect
    ex, beats, origins = _machines_and_beats(blob, source)
    cams = _camera_events(ex)
    rows = lock_table(blob, source, window)
    machines = W.recover_machines(blob, source)
    mach_rows = [(m.image, len(m.phases),
                  (m.phases[-1].start_tick if m.phases else 0), origins.get(m.image))
                 for m in machines]

    nn: List[int] = []
    dup: Dict[Tuple[int, int, int, int], List[str]] = {}
    for image, slot, state, beat in beats:
        hit = _nearest(cams, slot, beat)
        if hit is None:
            continue
        k, v = hit
        nn.append(abs(v[1] - beat))
        if abs(v[1] - beat) <= window:
            dup.setdefault(k, []).append("%s s%d" % (image, state))
    quality = PairQuality(len(beats), len(rows), nn, dup, window)

    by_ident = {(r.ident.machine, r.ident.state): r for r in rows}
    beat_of = {(image, state): tick for image, _slot, state, tick in beats}
    bounds: List[BoundaryFlags] = []
    for m in machines:
        origin = origins.get(m.image, 0)
        for ph in m.phases:
            # a terminal phase has no boundary to move -- it ends when something else ends it, and
            # a self-transition is a per-tick loop, not a boundary between two phases
            if ph.next_state is None or ph.next_state == ph.state \
                    or (m.image, ph.next_state) not in beat_of:
                continue
            beat = beat_of[(m.image, ph.next_state)]
            row = by_ident.get((m.image, ph.next_state))
            cut = row.cam if row else None
            lead = row.lead if row else None
            e1_thr, e1_rec = _e1_flags(blob, effect, m.image, ph.state, derive)
            e2 = _e2_flag(blob, cut) if cut is not None else "(no lock pair -- no cut to anchor)"
            e3 = (_e3_flag(ex, row.ident.slot, row.ident.subfile, cut) if row is not None
                  else "(no lock pair -- no shot named)")
            e4 = _e4_flag(game_root, effect, beat)
            ref = cut if cut is not None else beat
            ups = tuple(sorted(k for k, v in origins.items() if v < ref))
            downs = tuple(sorted(k for k, v in origins.items() if v >= ref))
            bounds.append(BoundaryFlags(
                machine=m.image, state=ph.state, next_state=ph.next_state, beat=beat,
                cut=cut, lead=lead, origin=origin,
                upstream_machines=ups, downstream_machines=downs,
                e1_threshold=e1_thr, e1_recips=e1_rec, e2=e2, e3=e3, e4=e4))
    notes = []
    if ex.dynamic:
        notes.append("%d camera op(s) resolve DYNAMICALLY -- their blocks are not statically named, "
                     "so any boundary they carry is invisible to this table" % ex.dynamic)
    if not rows:
        notes.append("NO lock pair anywhere in this effect: the two clocks are not demonstrably "
                     "locked here, and W1's law must not be quoted at it")
    return EffectReport(effect, source, mach_rows, quality, rows, bounds, notes)


def _e1_flags(blob: bytes, effect: int, image: str, state: int, derive: bool) -> Tuple[str, str]:
    """``(threshold site, reciprocal census)`` from :mod:`retime_derive`, or the refusal that stopped it."""
    if not derive:
        return "(not probed)", "(not probed)"
    try:
        import retime_derive as RD
    except Exception as exc:                                 # pragma: no cover
        return "(unavailable: %s)" % exc, "(unavailable)"
    try:
        t = RD.analyse_target(blob, effect, image, state)
    except RD.DeriveRefusal as exc:
        return "x", "REFUSED: %s" % str(exc).splitlines()[0][:100]
    except Exception as exc:            # one odd phase must not take down a whole effect's report
        return "x", "ERROR in the E1 probe: %s: %s" % (type(exc).__name__, str(exc)[:80])
    thr = "OK  slti imm %d at image %#06x = file %#08x" % (t.threshold, t.guard_off,
                                                           t.guard_file_off)
    if t.derivable:
        # V2's finding: `t.derivable` is the ANALYSIS flag; the WRITER can still refuse (ef381:c4 s4,
        # two retuned ramps wanting the same byte).  The label -- and therefore the --corpus footer,
        # which counts this substring -- must be end-to-end, so run the mandatory N=0 identity gate
        # before calling anything DERIVABLE.
        try:
            RD.assert_identity(t, blob)
        except RD.DeriveRefusal as exc:
            return thr, ("%d reciprocal(s), %d peer copy(ies); WRITER-REFUSED: %s"
                         % (len(t.reciprocals), t.peer_count, str(exc).splitlines()[0][:100]))
        rec = ("%d reciprocal(s), %d peer copy(ies); %d RETUNE, %d KEEP -- DERIVABLE"
               % (len(t.reciprocals), t.peer_count, len(t.retuned),
                  len(t.reciprocals) - len(t.retuned)))
    else:
        rec = ("%d reciprocal(s), %d peer copy(ies); REFUSED: %s"
               % (len(t.reciprocals), t.peer_count, t.refusals[0][:100]))
    return thr, rec


def report_lines(rep: EffectReport) -> List[str]:
    L = ["=" * 110,
         "ef%03d -- THE TWO-CLOCKS ALIGNMENT REPORT" % rep.effect,
         "=" * 110,
         "  machines (clean-switch class only):"]
    for image, nph, last, origin in rep.machines:
        L.append("     %-12s %2d phases, last starts at program tick %-4d  RUN_PROGRAM origin = %s"
                 % (image, nph, last, origin))
    q = rep.quality
    L.append("")
    L.append("  PAIRING QUALITY (window %d): %s" % (q.window, q.verdict))
    if q.nn_distances:
        srt = sorted(q.nn_distances)
        L.append("     nearest-neighbour |cam - beat| over %d beats: min %d, median %d, max %d"
                 % (len(srt), srt[0], srt[len(srt) // 2], srt[-1]))
    for k, v in sorted(q.duplicate_codes.items()):
        if len(v) > 1:
            L.append("     COLLISION: camera Code (slot %d sub %d seq %d code %d) is the nearest "
                     "neighbour of %s -- one Code cannot be the lock of two beats"
                     % (k[0], k[1], k[2], k[3], " and ".join(v)))
    L.append("")
    L.append("  PER-BOUNDARY DERIVABILITY")
    for b in rep.boundaries:
        L.append("   %-12s s%-3d -> %-5s beat %-5d cut %-6s lead %-5s  origin %d"
                 % (b.machine, b.state, b.next_state if b.next_state is not None else "term",
                    b.beat, b.cut if b.cut is not None else "--",
                    ("%+d" % b.lead) if b.lead is not None else "--", b.origin))
        L.append("       if this were the cut: %s do NOT ride the sequence shift; %s do"
                 % (", ".join(b.upstream_machines) or "(none)",
                    ", ".join(b.downstream_machines) or "(none)"))
        L.append("       E1 threshold : %s" % b.e1_threshold)
        L.append("       E1 program   : %s" % b.e1_recips)
        L.append("       E2 sequence  : %s" % b.e2)
        L.append("       E3 camera    : %s" % b.e3)
        L.append("       E4 outer text: %s" % b.e4)
    for n in rep.notes:
        L.append("  NOTE: %s" % n)
    return L


def corpus_report(root: Optional[str] = None, game_root=None, derive: bool = True,
                  window: int = LOCK_WINDOW) -> List[Tuple[int, Optional[EffectReport], str]]:
    """``[(effect, report or None, error)]`` for every corpus container with a clean-switch image."""
    import glob
    root = root or W.SCRATCH_CORPUS
    out = []
    for p in sorted(glob.glob(os.path.join(root, "ef*.bytes"))):
        name = os.path.splitext(os.path.basename(p))[0]
        try:
            ef = int(name[2:])
        except ValueError:                                   # pragma: no cover
            continue
        with open(p, "rb") as fh:
            blob = fh.read()
        try:
            if not W.recover_machines(blob, name):
                continue
            out.append((ef, effect_report(blob, ef, game_root, window, derive), ""))
        except Exception as exc:                             # the sweep must never stop on one file
            out.append((ef, None, "%s: %s" % (type(exc).__name__, exc)))
    return out


# ============================================================ (9) the spec
def load_spec(path) -> dict:
    with open(path, "rb") as fh:
        spec = _toml.load(fh)
    r = spec.get("retime")
    if not isinstance(r, dict):
        raise RetimeError("%s has no [retime] table" % path)
    for key in ("effect", "ticks"):
        if key not in r:
            raise RetimeError("[retime] needs `%s`" % key)
    for sub in ("sequence", "camera"):
        if not isinstance(r.get(sub), dict):
            raise RetimeError("[retime.%s] is missing" % sub)
    if "cut_tick" not in r["sequence"]:
        raise RetimeError("[retime.sequence] needs `cut_tick`")
    return spec


# ============================================================ CLI
def _read_effect_blob(effect: int, corpus_root: Optional[str], game=None) -> Tuple[bytes, str]:
    """Prefer the corpus copy (offline, provenance-gated); fall back to the user's own install."""
    root = corpus_root or W.SCRATCH_CORPUS
    p = os.path.join(root, "ef%03d.bytes" % effect)
    if os.path.isfile(p):
        with open(p, "rb") as fh:
            return fh.read(), p
    return R.read_stock_effect(effect, game)


def _report_main(a, game_root) -> int:                        # pragma: no cover - CLI wiring
    if a.corpus:
        rows = corpus_report(a.corpus_root, game_root, not a.no_derive, a.window)
        ok = bad = 0
        print("%-8s %-10s %-6s %-9s %s" % ("effect", "machines", "beats", "pairs", "verdict"))
        for ef, rep, err in rows:
            if rep is None:
                bad += 1
                print("ef%03d    ERROR      %s" % (ef, err[:90]))
                continue
            ok += 1
            print("ef%03d    %-10s %-6d %-9d %s"
                  % (ef, ",".join(m[0].split(":")[-1] for m in rep.machines),
                     rep.quality.beats_total, rep.quality.pairs_found, rep.quality.verdict))
        derivable = sum(1 for _e, rp, _x in rows if rp
                        for b in rp.boundaries if "DERIVABLE" in b.e1_recips)
        total_b = sum(len(rp.boundaries) for _e, rp, _x in rows if rp)
        print("\n%d effect(s) reported, %d errored; %d of %d boundaries are E1-DERIVABLE"
              % (ok, bad, derivable, total_b))
        return 0 if not bad else 1
    try:
        effect = int(str(a.spec).lstrip("eEfF"))
    except ValueError:
        print("`report` takes an EFFECT ID (e.g. `retime.py report 211`), not %r" % a.spec)
        return 2
    blob, src = _read_effect_blob(effect, a.corpus_root, a.game)
    rep = effect_report(blob, effect, game_root, a.window, not a.no_derive)
    print("source: %s" % src)
    print("\n".join(report_lines(rep)))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("verb", choices=("plan", "build", "verify", "report"))
    ap.add_argument("spec", nargs="?", default=os.path.join(_HERE, "bahamut_retime.toml"),
                    help="a retime spec for plan/build/verify; an EFFECT ID for `report`")
    ap.add_argument("--root", default=SCRATCH_ROOT,
                    help="staging root (default: SCRATCH; the repo and the install are refused)")
    ap.add_argument("--game", default=None)
    ap.add_argument("--no-text", action="store_true",
                    help="skip E4 (the outer text co-retime) -- for a container-only bisect")
    ap.add_argument("--live", action="store_true",
                    help="allow a --root INSIDE the game install. Off by default: W3 stages, and the "
                         "generated deploy scripts are what touch the install, with the user present.")
    ap.add_argument("--corpus", action="store_true",
                    help="`report` only: sweep every clean-switch effect in the corpus")
    ap.add_argument("--corpus-root", default=None, help="`report` only: where the ef*.bytes live")
    ap.add_argument("--no-derive", action="store_true",
                    help="`report` only: skip the E1 program probe (much faster, far less useful)")
    ap.add_argument("--window", type=int, default=LOCK_WINDOW, help="`report` only: pairing window")
    a = ap.parse_args(argv)

    try:
        from ff9mapkit import config
        game_root = config.find_game_path(a.game)
    except Exception:                                        # pragma: no cover
        game_root = None

    if a.verb == "report":
        return _report_main(a, game_root)

    spec = load_spec(a.spec)

    b = build_containers(spec, a.spec, a.game)
    if not a.no_text and game_root is not None:
        b.text = build_text_edit(spec, game_root)
        b.player = audit_player_sequence(spec, game_root)
    b.check = self_check(b)

    print("\n".join(describe(b)))
    print("\n".join(check_lines(b)))
    print("\n".join(residual_lines(b)))
    if b.text:
        print("\n  E4 UNIFIED DIFF (the only record of the text edit -- SE-derived content is never "
              "committed)")
        for ln in b.text.diff.splitlines():
            print("    " + ln)

    if a.verb == "plan":
        print("\nplan only -- nothing written.")
        return 0 if b.check.ok else 1
    if not b.check.ok:
        print("\nREFUSING TO STAGE -- the self-check failed (see above).")
        return 1

    if a.verb == "build":
        out = stage(b, a.root, game_root, allow_install=a.live)
        print("\n  %s" % ("DEPLOYED (--live)" if a.live else "STAGED"))
        for k, v in out.items():
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    print("    %-22s %s" % (k2, v2))
            else:
                print("    %-22s %s" % (k, v))
        return 0

    # verify: the staged bytes, re-checked as bytes (not as a rebuild)
    root = Path(a.root)
    mf = root / "build_manifest.json"
    if not mf.exists():
        print("\nVERIFY FAILED: no build manifest at %s" % mf)
        return 1
    man = json.loads(mf.read_text(encoding="utf-8"))
    ok = True
    for key, want in (("aligned", b.aligned), ("misretime", b.misretime)):
        p = Path(man[key])
        if not p.exists():
            print("  VERIFY %-11s MISSING at %s" % (key, p)); ok = False; continue
        got = p.read_bytes()
        same = got == want
        ok = ok and same
        print("  VERIFY %-11s %d B sha %s -> %s"
              % (key, len(got), _sha(got)[:16], "MATCHES the rebuild" if same else "DIVERGES"))
    if man.get("text") and b.text:
        p = Path(man["text"])
        same = p.exists() and p.read_bytes() == b.text.data
        ok = ok and same
        print("  VERIFY %-11s %s -> %s" % ("text", p,
                                           "MATCHES the rebuild" if same else "DIVERGES/MISSING"))
    for name, p in sorted((man.get("scripts") or {}).items()):
        exists = Path(p).exists()
        ok = ok and exists
        print("  VERIFY %-11s %s" % (name, p if exists else "MISSING: %s" % p))
    print("\n  VERIFY: %s" % ("PASS" if ok and b.check.ok else "FAIL"))
    return 0 if ok and b.check.ok else 1


if __name__ == "__main__":                                   # pragma: no cover
    raise SystemExit(main())
