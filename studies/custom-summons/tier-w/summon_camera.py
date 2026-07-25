r"""TIER W rung 1 -- THE READ-OUT: a stock FF9 summon's camera, made readable.

    py summon_camera.py read 227            # the human read-out + the merged timeline
    py summon_camera.py roundtrip           # the W1b gate over the whole corpus
    py summon_camera.py census              # the W1d corpus census
    py summon_camera.py dump 227            # decoded rows -> SCRATCH (never the repo)

WHAT TIER R HANDED US, and what this module does with it
--------------------------------------------------------
R2 §5 proved the summon camera is **unreachable from the effect program**: it is played by the
SEQUENCE stream, opcode ``0x29 PLAY_CAMERA``, reading a camera sub-file out of the chunk's id-2
archive.  D4 §2.2 then read the native block parser (fn ``0x13030``) and claimed the block is *the
same binary format* ``ff9mapkit/battle/camera_codec.py`` already round-trips for raw17 battle
cameras.  **That claim had never been executed against a summon camera.**  ``roundtrip`` executes it.

The verdict is in ``W1-READOUT.md``; the short form is that the claim holds byte-for-byte, so this
module deliberately owns **no** camera grammar of its own.  It contributes exactly three things the
battle path does not have:

1. **THE EXTRACTOR** -- walk the sequence, resolve each shot's sub-file, hand the battle codec a
   block.  (``walk_camera_ops`` + ``id2_directory`` + ``extract_shots``.)
2. **THE ADAPTER** -- an SFX camera block *is* one battle camera without raw17's set-offset table
   wrapper, so ``parse_camera_block``/``serialize_camera_block`` are two-line calls into
   ``camera_codec``'s per-camera functions.  **Nothing in ``camera_codec`` is modified**; the battle
   tests stay green by construction (W1a).
3. **THE READ-OUT + THE MERGED TIMELINE** -- shots decoded to human terms, then merged with R3's
   recovered program phases on ONE clock (``merged_timeline``), which is what a rescore author reads.

THE THREE CORRECTIONS THIS ROUND SUPPLIES (each falsifiable, each in the gates)
------------------------------------------------------------------------------
* **THE ID-2 EXTRA-SECTOR CORRECTION.**  ``ef_container.parse_header`` records an id-2 resource's
  payload at ``res.offset`` and its ``extra_sectors`` (the ``info != 0`` conditional field) as
  following it.  For the ONE corpus file where ``extra_sectors != 0`` (``ef251`` chunk 0, D3's own
  census) that ordering puts the sub-file directory in the wrong place: parsing at ``res.offset``
  yields a plausible-looking 2-entry table and the effect's own camera index (7) then reads
  out of range.  Skipping the extra region first -- ``base = res.offset + extra_sectors*0x800``,
  i.e. the ordering ``SFXBinaryFile.cs`` uses -- yields a 33-entry directory that is monotone,
  in-bounds, and whose entry 7 is a camera block that round-trips.  Both orderings consume the same
  total bytes, so the container walk is unaffected either way; only the DIRECTORY BASE moves.
  ``id2_directory`` applies the correction and ``w1_gates`` K2 re-proves it.
* **THE FRAME WORD CARRIES FLAGS.**  A Code's ``frame`` u16 is not a bare frame number: 97 keyframes
  across the corpus set bits in ``0xE000`` (0x4000, 0x2000, 0x6000), almost always on the FIRST
  keyframe of a sequence.  Read as a plain number those look like a shot that starts at frame 16385
  and then goes backwards.  ``frame_number()``/``frame_marks()`` split the word.  The codec stores
  the word verbatim, so the round-trip is unaffected -- but a rescore author who *writes* a frame
  must preserve the high bits.
* **``0x23 SETUP_CAMERA`` IS A CAMERA-BLOCK OP TOO.**  It resolves through the same directory: 713
  of the corpus's 798 statically-resolvable camera blocks are reached by ``0x23``, not ``0x29``.
  A tool that walks only ``0x29`` sees 11 % of the corpus's camera data.

WHAT IS NOT STATICALLY RESOLVABLE (say it out loud -- it is a third of the corpus's PLAY ops)
--------------------------------------------------------------------------------------------
``0x29``'s ``arg2`` selects the shot: ``0`` literal · ``1`` last-used · ``2`` LCG-random · ``3``
table lookup keyed on a battle field (D4 §2.1, handler ``0x3bbd0``).  **324 of the corpus's 411
``0x29`` ops use arg2 == 3** and their shot is a RUNTIME choice -- offline decoding cannot name it.
Every one of those 324 is immediately preceded, in the same file, by exactly one ``0x23 arg1=0xFF``
(324 files, 1:1), so the idiom is "clear the setup slot, then pick a camera from the table."
``walk_camera_ops`` marks them ``dynamic`` rather than guessing.

PROVENANCE
----------
Reads the corpus extracted from the user's own install at ``C:\gd\SCRATCH\summon-format`` and writes
decoded dumps only under ``C:\gd\SCRATCH\summon-format\camera-w1``.  This file, its tests and the
report contain **no stock bytes** -- only offsets, counts, sizes and frame numbers.  ``dump_shots``
refuses any destination inside the repo, the way ``ef_camera_decode.py`` already does.
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import os
import struct
import sys
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)                                  # studies/custom-summons
_REPO = os.path.dirname(os.path.dirname(_STUDY))                 # <repo>
sys.path.insert(0, os.path.join(_STUDY, "thomas-swap", "disasm"))
sys.path.insert(0, os.path.join(_STUDY, "tier-r"))
sys.path.insert(0, os.path.join(_REPO, "ff9mapkit"))

import ef_container as EC                                        # noqa: E402
from ff9mapkit.battle import camera_codec as CC                  # noqa: E402

#: same env override tier-r uses, so a run without the extraction skips instead of failing
SCRATCH_CORPUS = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
SCRATCH_OUT = os.path.join(SCRATCH_CORPUS, "camera-w1")

SECTOR = EC.SECTOR

#: sequence opcodes this module cares about (names + semantics from M2 §7.4 / D4 §2.1)
OP_END = 0x00
OP_WAIT = 0x01
OP_LOAD_CHUNK = 0x05
OP_SETUP_CAMERA = 0x23
OP_PLAY_CAMERA = 0x29
OP_RUN_PROGRAM = 0x80          # 0x80 + N runs the chunk's program table entry N (M2 §7.3)

#: 0x23's "no camera" sentinel and 0x29's arg2 dispatch arms (D4 §2.1, handler 0x3bbd0)
SETUP_NONE = 0xFF
ARG2_LITERAL, ARG2_LAST, ARG2_RANDOM, ARG2_TABLE = 0, 1, 2, 3
ARG2_NAMES = {0: "literal", 1: "last-used", 2: "random", 3: "table-lookup"}

#: the Code ``frame`` word: low 13 bits are the frame, the top 3 are undecoded marks (see docstring)
FRAME_MASK = 0x1FFF
FRAME_MARK_MASK = 0xE000

#: outer Flags groups -- names from camera_codec, meanings sharpened by D4 §2.2
OUTER_GROUPS = ((0x01, "sequence0"), (0x02, "sequence1"), (0x04, "sequence2"),
                (0x08, "selector"), (0xF0, "anchors"))

#: Movement ``type``.  0/1/2 are camera_codec's battle-side easing names; the rest are real corpus
#: values with no read handler yet -- named ``type-N`` on purpose rather than guessed at.
EASE_NAMES = {0: "linear", 1: "ease-in", 2: "ease-out"}


class SummonCameraError(RuntimeError):
    pass


def _u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


# ============================================================ the frame word
def frame_number(word: int) -> int:
    """The Code's frame number -- the low 13 bits (see THE FRAME WORD CARRIES FLAGS, module head)."""
    return word & FRAME_MASK


def frame_marks(word: int) -> int:
    """The frame word's undecoded high bits.  Preserve them verbatim when authoring."""
    return word & FRAME_MARK_MASK


# ============================================================ (A) THE EXTRACTOR
@dataclass
class CameraOp:
    """One sequence op that names a camera block."""
    at: int                     # file offset of the 3-byte record
    code: int                   # 0x23 SETUP_CAMERA | 0x29 PLAY_CAMERA
    arg1: int
    arg2: int
    chunk_slot: int             # the chunk the last LOAD_CHUNK selected (its TABLE ORDINAL, M2 §7.3)
    seq_tick: int               # accumulated WAIT ticks at this op (see THE CLOCK below)
    resolution: str             # 'literal' | 'dynamic' | 'none'

    @property
    def kind(self) -> str:
        return "SETUP_CAMERA" if self.code == OP_SETUP_CAMERA else "PLAY_CAMERA"


@dataclass
class SeqWalk:
    ops: Tuple[CameraOp, ...]
    program_starts: Dict[Tuple[int, int], int]   # (chunk slot, program index) -> seq tick
    total_ticks: int
    blocking_waits: int                          # WAIT arg1!=0 -- duration NOT statically known
    n_ops: int


def walk_camera_ops(blob: bytes) -> SeqWalk:
    r"""Walk the sequence stream at file 0x400 and collect every camera-naming op.

    THE CLOCK.  ``WAIT`` (0x01) with ``arg1 == 0`` waits ``arg2`` ticks; with ``arg1 != 0`` it
    blocks until channel-flag[arg2] clears (M2 §7.4) -- a duration nothing static can supply, so
    those are COUNTED, not summed.  ``seq_tick`` is therefore the effect's own authored clock with
    every statically-unknown blocking wait treated as zero.  It is not ``SFX.frameIndex``: mapping
    to that needs ONE additive origin (``merged_timeline`` derives and reports it).

    ``ef_camera_decode.py``'s older walk added ``arg2`` for blocking waits too, which adds a channel
    INDEX to a tick count; on ef227 that inflates every camera tick by exactly 3.  Every offset this
    module reports is a DIFFERENCE between two ticks on the same clock, so the choice cancels -- but
    the strict rule is the correct one and is what the gates use.
    """
    ops: List[CameraOp] = []
    starts: Dict[Tuple[int, int], int] = {}
    slot, tick, blocking, n = 0, 0, 0, 0
    for op in EC.parse_sequence(blob):
        n += 1
        if op.code == OP_LOAD_CHUNK:
            slot = op.arg1
        elif op.code >= OP_RUN_PROGRAM:
            starts.setdefault((slot, op.code - OP_RUN_PROGRAM), tick)
        elif op.code == OP_SETUP_CAMERA:
            res = "none" if op.arg1 == SETUP_NONE else "literal"
            ops.append(CameraOp(op.at, op.code, op.arg1, op.arg2, slot, tick, res))
        elif op.code == OP_PLAY_CAMERA:
            res = "literal" if op.arg2 == ARG2_LITERAL else "dynamic"
            ops.append(CameraOp(op.at, op.code, op.arg1, op.arg2, slot, tick, res))
        if op.code == OP_WAIT:
            if op.arg1 == 0:
                tick += op.arg2
            else:
                blocking += 1
        if op.code == OP_END:
            break
    return SeqWalk(tuple(ops), starts, tick, blocking, n)


@dataclass
class Id2Archive:
    """A chunk's id-2 sub-file archive: the directory and the region it indexes."""
    slot: int
    base: int                  # file offset of the directory == the region base
    size: int                  # bytes of the region the directory's offsets index
    entries: Tuple[int, ...]   # signed s32 offsets relative to ``base`` (M2 §5, fn 0x3d800@0x3da8a)
    extra_sectors: int

    def bounds(self, idx: int) -> Tuple[int, int]:
        """(lo, hi) file offsets of sub-file ``idx``.

        The end is the next STRICTLY GREATER entry (equal entries are aliases of the same sub-file,
        which is exactly what ``SFXBinaryFile.cs``'s ``sfOffset == previous`` arm encodes) or the
        region end.  Corpus fact that makes this safe for cameras: **no camera block is ever the
        last sub-file in its chunk** (798/798), so a camera's end is always a real directory delta,
        never the region's sector padding.
        """
        if not 0 <= idx < len(self.entries):
            raise SummonCameraError("sub-file index %d out of range (%d entries)"
                                    % (idx, len(self.entries)))
        lo = self.entries[idx]
        if lo < 0:
            raise SummonCameraError("sub-file %d is EXTERNAL (negative relative offset %d): it "
                                    "points backwards out of this region into earlier-loaded data"
                                    % (idx, lo))
        hi = next((v for v in self.entries[idx + 1:] if v > lo), self.size)
        return self.base + lo, self.base + hi


def id2_directory(blob: bytes, container: EC.Container, slot: int) -> Optional[Id2Archive]:
    r"""The chunk's sub-file archive, WITH THE EXTRA-SECTOR CORRECTION (module docstring).

    ``parse_header`` reads the ``id == 2 && info != 0`` conditional field into ``extra_sectors`` and
    advances the cursor by it AFTER the payload.  The directory, however, sits after the extra
    region: ``base = res.offset + extra_sectors * 0x800``, and the region the directory's offsets
    index is then the resource's OWN declared ``nbytes`` starting there -- so the two readings
    consume identical total bytes and only the base moves.  On 371 of 372 corpus files
    ``extra_sectors == 0`` and they coincide; on ``ef251`` chunk 0 they do not, and only this one
    resolves the effect's own camera index (and lands the region end exactly on the next resource).
    """
    if not 0 <= slot < len(container.chunks):
        return None
    res = next((r for r in container.chunks[slot].resources if r.id == 2), None)
    if res is None:
        return None
    extra = res.extra_sectors or 0
    base = res.offset + extra * SECTOR
    size = res.nbytes
    if size <= 0:
        return None
    try:
        entries = EC.parse_directory(blob, base)
    except (struct.error, IndexError) as e:                       # pragma: no cover - corpus is clean
        raise SummonCameraError("chunk %d id-2 directory unreadable at %#x: %s" % (slot, base, e))
    if not entries:
        return None
    return Id2Archive(slot, base, size, tuple(entries), extra)


@dataclass
class Shot:
    """One camera block, located and decoded."""
    op: CameraOp
    archive_base: int
    lo: int
    hi: int
    block: bytes = field(repr=False)
    camera: dict = field(repr=False)

    @property
    def size(self) -> int:
        return self.hi - self.lo

    @property
    def index(self) -> int:
        return self.op.arg1

    @property
    def slot(self) -> int:
        return self.op.chunk_slot

    @property
    def key(self) -> Tuple[int, int]:
        return (self.slot, self.index)

    def roundtrip(self) -> Tuple[bool, bytes]:
        out = serialize_camera_block(self.camera)
        return out == self.block, out


@dataclass
class Extract:
    source: str
    walk: SeqWalk
    shots: Tuple[Shot, ...]
    skipped: Tuple[Tuple[CameraOp, str], ...]     # (op, why) for every op that named no block

    @property
    def dynamic(self) -> int:
        return sum(1 for o, w in self.skipped if w == "dynamic")


def extract_shots(blob: bytes, source: str = "?") -> Extract:
    """Every camera block a container's sequence statically names, resolved to bytes and parsed."""
    container = EC.parse_header(blob)
    walk = walk_camera_ops(blob)
    archives: Dict[int, Optional[Id2Archive]] = {}
    shots: List[Shot] = []
    skipped: List[Tuple[CameraOp, str]] = []
    for op in walk.ops:
        if op.resolution != "literal":
            skipped.append((op, op.resolution))
            continue
        if op.chunk_slot not in archives:
            archives[op.chunk_slot] = id2_directory(blob, container, op.chunk_slot)
        arc = archives[op.chunk_slot]
        if arc is None:
            skipped.append((op, "no id-2 archive in chunk %d" % op.chunk_slot))
            continue
        try:
            lo, hi = arc.bounds(op.arg1)
        except SummonCameraError as e:
            skipped.append((op, str(e)))
            continue
        block = bytes(blob[lo:hi])
        try:
            cam = parse_camera_block(block)
        except (struct.error, IndexError, CC.CameraCodecError) as e:
            skipped.append((op, "block did not parse: %s: %s" % (type(e).__name__, e)))
            continue
        shots.append(Shot(op, arc.base, lo, hi, block, cam))
    return Extract(source, walk, tuple(shots), tuple(skipped))


# ============================================================ (B) THE DECODER / ADAPTER
def parse_camera_block(block: bytes) -> dict:
    """Parse ONE SFX camera sub-file with the BATTLE codec, unmodified.

    A raw17 battle camera block is a set-offset table followed by N cameras; an SFX camera sub-file
    IS one of those cameras, delimited by the id-2 directory instead of the set-offset table.  So
    the whole adapter is: hand ``camera_codec``'s per-camera parser the block's own bounds.
    """
    if len(block) < 4:
        raise SummonCameraError("camera block is %d bytes -- too short for Flags + one offset"
                                % len(block))
    return CC._parse_camera(block, 0, len(block))


def serialize_camera_block(cam: dict) -> bytes:
    """Re-emit a parsed SFX camera block with the BATTLE codec, unmodified (the W1b gate's other half)."""
    return CC._serialize_camera(cam)


def outer_groups(flags: int) -> List[str]:
    """The groups an outer Flags word declares, in the order the offset table lists them."""
    out = [name for bit, name in OUTER_GROUPS[:4] if flags & bit]
    if flags & 0xF0:
        out.append("anchors x%d" % bin(flags & 0xF0).count("1"))
    return out


def block_layout(block: bytes) -> List[Tuple[str, int, int]]:
    """[(group name, lo, hi)] within the block -- the offset table read literally.

    Corpus invariant this asserts on: the table's first entry equals the table's own end and the
    entries are STRICTLY increasing, i.e. the groups' physical order is the canonical order the
    codec re-emits them in.  798/798 stock camera blocks satisfy both, which is *why* the round-trip
    is byte-exact rather than merely structure-preserving.
    """
    flags = _u16(block, 0)
    names = [n for b, n in OUTER_GROUPS[:4] if flags & b]
    if flags & 0xF0:
        names.append("anchors")
    n = len(names)
    offs = [_u16(block, 2 + 2 * i) for i in range(n)]
    bounds = offs + [len(block)]
    return [(names[i], bounds[i], bounds[i + 1]) for i in range(n)]


@dataclass
class Keyframe:
    """One Code, decoded to human terms."""
    local_frame: int
    marks: int
    flags: int
    fields: Dict[str, bytes]

    # ---- typed views over the verbatim sub-blocks (SFXDataCamera field order, camera_codec._split_code)
    def pose(self, which: str = "campos") -> Optional[Dict[str, int]]:
        b = self.fields.get(which)
        if not b:
            return None
        return {"code": b[0], "flags": b[1], "pitch": b[2], "orientation": b[3],
                "roll": b[4], "distance": b[5]}

    def movement(self, which: str = "cammove") -> Optional[Dict[str, object]]:
        b = self.fields.get(which)
        if not b:
            return None
        return {"duration": _u16(b, 0), "type": b[2],
                "ease": EASE_NAMES.get(b[2], "type-%d" % b[2]), "unknown": b[3]}

    def focal(self) -> Optional[Dict[str, int]]:
        b = self.fields.get("focal")
        if not b:
            return None
        return {"duration": b[0], "flags": b[1], "distance": _u16(b, 2)}

    @property
    def is_cut(self) -> bool:
        """A pose with no movement = an instantaneous placement, i.e. a CUT rather than a move."""
        return "campos" in self.fields and "cammove" not in self.fields


def keyframes(cam: dict, seq_index: int = 0) -> List[Keyframe]:
    """One sequence's Codes as ``Keyframe``s (the frame-0 terminator dropped)."""
    if seq_index >= len(cam["sequences"]):
        return []
    out = []
    for c in cam["sequences"][seq_index]:
        w = c.get("frame") or 0
        if not w:
            continue
        out.append(Keyframe(frame_number(w), frame_marks(w), c["flags"],
                            CC._split_code(c["flags"], c["block"])))
    return out


def shot_span(cam: dict) -> int:
    """The shot's own length in local frames: the last keyframe, plus any move it starts."""
    best = 0
    for si in range(len(cam["sequences"])):
        for k in keyframes(cam, si):
            end = k.local_frame
            mv = k.movement("cammove") or k.movement("tgtmove")
            if mv:
                end += int(mv["duration"])
            best = max(best, end)
    return best


# ============================================================ (C) THE MERGED TIMELINE
@dataclass
class TimelineRow:
    seq_tick: int              # THE shared clock (see walk_camera_ops)
    kind: str                  # 'camera' | 'phase'
    who: str                   # 'shot A (c0 idx6)' | 'ef227:c0 s1'
    what: str                  # what changes
    h: Optional[int] = None    # the projection distance this row writes, if any
    state: Optional[int] = None  # the phase this row begins, if any


@dataclass
class Timeline:
    source: str
    rows: Tuple[TimelineRow, ...]
    program_starts: Dict[Tuple[int, int], int]
    machines: Tuple[object, ...] = ()

    def cameras(self):
        return [r for r in self.rows if r.kind == "camera"]

    def phases(self):
        return [r for r in self.rows if r.kind == "phase"]

    def h_changes(self) -> List[TimelineRow]:
        """Every row that writes the projection distance, in order -- the observable TIER R's
        capture recorded (``H -> 256 @f58`` and friends)."""
        out, last = [], None
        for r in self.rows:
            if r.h is None:
                continue
            if r.h != last:
                out.append(r)
                last = r.h
        return out

    def pairs(self, rows: Optional[Sequence[TimelineRow]] = None, window: int = 4
              ) -> List[Tuple[TimelineRow, TimelineRow, int]]:
        """(camera row, nearest phase row, camera_tick - phase_tick) for every camera row within
        ``window`` ticks of a phase boundary.  THE TWO CLOCKS, as a number instead of a note."""
        ph = self.phases()
        out = []
        for c in (self.cameras() if rows is None else rows):
            if not ph:
                break
            near = min(ph, key=lambda p: (abs(c.seq_tick - p.seq_tick), p.seq_tick))
            d = c.seq_tick - near.seq_tick
            if abs(d) <= window:
                out.append((c, near, d))
        return out


_SHOT_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _shot_label(i: int, s: Shot) -> str:
    return "shot %s (c%d idx%d)" % (_SHOT_LETTERS[i % 26], s.slot, s.index)


def merged_timeline(blob: bytes, source: str = "?", machines: Optional[Sequence[object]] = None
                    ) -> Timeline:
    r"""ONE table: camera events and R3's program phases on the SEQUENCE CLOCK.

    Both clocks are derived, neither is fitted:

    * a camera event is at ``op.seq_tick + local_frame - 1`` (``ef_camera_decode``'s three-way
      validated rule, mechanically explained by D4 §2.1: the stepper advances once per
      ``SFX_UpdateCamera``, i.e. once per host frame, from the moment ``0x12df0`` installs the block);
    * a phase boundary is at ``program_start_tick + phase.start_tick``, where the program start is
      the ``0x80+N`` op's own tick in the SAME sequence walk.

    So the OFFSET between a cut and a beat is a pure data+code quantity -- no capture, no fitted
    origin, nothing that could be tuned to match an observation.
    """
    ex = extract_shots(blob, source)
    rows: List[TimelineRow] = []
    for i, s in enumerate(ex.shots):
        label = _shot_label(i, s)
        base = s.op.seq_tick
        rows.append(TimelineRow(base, "camera", label, "%s installs (%d B, %d keyframes)"
                                % (s.op.kind, s.size, len(keyframes(s.camera)))))
        for si in range(len(s.camera["sequences"])):
            if si and s.camera["sequences"][si] == s.camera["sequences"][0]:
                continue                      # an identical alternate track -- report it once
            for k in keyframes(s.camera, si):
                t = base + k.local_frame - 1
                bits = []
                f = k.focal()
                if f:
                    bits.append("H -> %d" % f["distance"])
                p = k.pose("campos")
                if p:
                    mv = k.movement("cammove")
                    bits.append("pose (p%d o%d r%d d%d)%s"
                                % (p["pitch"], p["orientation"], p["roll"], p["distance"],
                                   "" if mv else " INSTANT"))
                    if mv:
                        bits.append("move %df %s" % (mv["duration"], mv["ease"]))
                if k.pose("tgtpos"):
                    bits.append("retarget")
                if not bits:
                    bits.append("flags %#06x" % k.flags)
                suffix = "" if si == 0 else " [alt seq%d]" % si
                rows.append(TimelineRow(t, "camera", label + suffix, ", ".join(bits),
                                        h=(f["distance"] if f else None)))

    for sm in (machines or ()):
        slot = _machine_slot(sm)
        start = ex.walk.program_starts.get((slot, 0))
        if start is None:
            continue
        for ph in sm.phases:
            rows.append(TimelineRow(start + ph.start_tick, "phase",
                                    "%s s%d" % (sm.image, ph.state),
                                    "phase s%d begins (%s ticks)"
                                    % (ph.state, "term" if ph.ticks is None else ph.ticks),
                                    state=ph.state))
    rows.sort(key=lambda r: (r.seq_tick, r.kind != "phase"))
    return Timeline(source, tuple(rows), dict(ex.walk.program_starts), tuple(machines or ()))


def _machine_slot(sm) -> int:
    """``ef227:c0`` -> 0.  R3 names an image by its chunk ordinal, which is LOAD_CHUNK's own key."""
    tail = str(getattr(sm, "image", "")).rsplit(":c", 1)
    try:
        return int(tail[-1])
    except ValueError:                                            # pragma: no cover
        return 0


def recover_machines(blob: bytes, source: str):
    """R3's state machines for this container, or () if R3's inspector is unavailable/defeated."""
    try:
        import summon_inspect as S
    except Exception:                                             # pragma: no cover
        return ()
    out = []
    for rec in S.recover_container(blob, source, _hle_ops()):
        if rec.machine is not None and rec.verdict == "clean":
            out.append(rec.machine)
    return tuple(out)


_OPS_CACHE: Optional[dict] = None


def _hle_ops() -> Optional[dict]:
    global _OPS_CACHE
    if _OPS_CACHE is None:
        try:
            import json
            with open(os.path.join(_STUDY, "tier-r", "hle_ops.json"), "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            _OPS_CACHE = {int(k): v for k, v in (raw.get("ops") or raw).items()}
        except Exception:                                         # pragma: no cover
            _OPS_CACHE = {}
    return _OPS_CACHE or None


# ============================================================ (D) THE CORPUS CENSUS
@dataclass
class CensusRow:
    source: str
    n_seq_ops: int
    n_camera_ops: int
    n_shots: int
    n_dynamic: int
    n_setup_none: int
    shot_sizes: Tuple[int, ...]
    keyframes: Tuple[int, ...]
    spans: Tuple[int, ...]
    n_sequences: Tuple[int, ...]
    roundtrip_ok: int
    roundtrip_bad: Tuple[str, ...]
    skipped: Tuple[str, ...]
    shot_shas: Tuple[str, ...]


def census_one(path: str) -> CensusRow:
    import hashlib
    source = os.path.splitext(os.path.basename(path))[0]
    with open(path, "rb") as fh:
        blob = fh.read()
    ex = extract_shots(blob, source)
    ok, bad, sizes, kfs, spans, nseq, shas = 0, [], [], [], [], [], []
    for s in ex.shots:
        good, out = s.roundtrip()
        if good:
            ok += 1
        else:
            bad.append("c%d idx%d: %d B in, %d B out" % (s.slot, s.index, s.size, len(out)))
        sizes.append(s.size)
        kfs.append(sum(len(keyframes(s.camera, i)) for i in range(len(s.camera["sequences"]))))
        spans.append(shot_span(s.camera))
        nseq.append(len(s.camera["sequences"]))
        shas.append(hashlib.sha256(s.block).hexdigest())
    return CensusRow(
        source=source, n_seq_ops=ex.walk.n_ops, n_camera_ops=len(ex.walk.ops),
        n_shots=len(ex.shots), n_dynamic=ex.dynamic,
        n_setup_none=sum(1 for o, w in ex.skipped if w == "none"),
        shot_sizes=tuple(sizes), keyframes=tuple(kfs), spans=tuple(spans),
        n_sequences=tuple(nseq), roundtrip_ok=ok, roundtrip_bad=tuple(bad),
        skipped=tuple("c%d %s idx%d: %s" % (o.chunk_slot, o.kind, o.arg1, w)
                      for o, w in ex.skipped if w not in ("none", "dynamic")),
        shot_shas=tuple(shas))


def corpus_paths(root: str = SCRATCH_CORPUS) -> List[str]:
    return sorted(glob.glob(os.path.join(root, "ef*.bytes")))


def census(root: str = SCRATCH_CORPUS, limit: Optional[int] = None) -> List[CensusRow]:
    paths = corpus_paths(root)
    if limit:
        paths = paths[:limit]
    return [census_one(p) for p in paths]


def census_summary(rows: Sequence[CensusRow]) -> dict:
    sizes = [n for r in rows for n in r.shot_sizes]
    kfs = [n for r in rows for n in r.keyframes]
    spans = [n for r in rows for n in r.spans]
    sha = collections.defaultdict(list)
    for r in rows:
        for i, h in enumerate(r.shot_shas):
            sha[h].append(r.source)
    dup = {h: v for h, v in sha.items() if len(v) > 1}
    return {
        "effects": len(rows),
        "effects_with_camera_ops": sum(1 for r in rows if r.n_camera_ops),
        "effects_with_shots": sum(1 for r in rows if r.n_shots),
        "camera_ops": sum(r.n_camera_ops for r in rows),
        "shots": sum(r.n_shots for r in rows),
        "dynamic": sum(r.n_dynamic for r in rows),
        "setup_none": sum(r.n_setup_none for r in rows),
        "roundtrip_ok": sum(r.roundtrip_ok for r in rows),
        "roundtrip_bad": [b for r in rows for b in r.roundtrip_bad],
        "skipped": [s for r in rows for s in r.skipped],
        "shots_per_effect": dict(sorted(collections.Counter(r.n_shots for r in rows).items())),
        "sequences_per_shot": dict(sorted(collections.Counter(
            n for r in rows for n in r.n_sequences).items())),
        "bytes_total": sum(sizes),
        "size_min": min(sizes) if sizes else 0,
        "size_max": max(sizes) if sizes else 0,
        "size_mean": (sum(sizes) / len(sizes)) if sizes else 0,
        "kf_min": min(kfs) if kfs else 0,
        "kf_max": max(kfs) if kfs else 0,
        "kf_mean": (sum(kfs) / len(kfs)) if kfs else 0,
        "kf_total": sum(kfs),
        "span_min": min(spans) if spans else 0,
        "span_max": max(spans) if spans else 0,
        "span_mean": (sum(spans) / len(spans)) if spans else 0,
        "identical_groups": len(dup),
        "identical_refs": sum(len(v) for v in dup.values()),
        "identical_cross_effect": sum(1 for v in dup.values() if len(set(v)) > 1),
    }


# ============================================================ the human read-out
def _pose_line(tag: str, p: Dict[str, int]) -> str:
    return ("%-7s code=%-3d flags=%#04x  pitch=%-4d orientation=%-4d roll=%-4d distance=%-4d"
            % (tag, p["code"], p["flags"], p["pitch"], p["orientation"], p["roll"], p["distance"]))


def read_out(blob: bytes, source: str, machines: Optional[Sequence[object]] = None) -> List[str]:
    """THE READ-OUT (C): every shot in human terms, then the merged timeline."""
    ex = extract_shots(blob, source)
    L: List[str] = []
    w = ex.walk
    L.append("%s -- %d sequence ops, %d authored ticks, %d blocking waits (duration not static)"
             % (source, w.n_ops, w.total_ticks, w.blocking_waits))
    L.append("  camera ops: %d  ->  %d resolved shots, %d dynamic (runtime-chosen), %d 'no camera'"
             % (len(w.ops), len(ex.shots), ex.dynamic,
                sum(1 for o, why in ex.skipped if why == "none")))
    if w.program_starts:
        L.append("  programs start at seq tick: "
                 + ", ".join("c%d prog%d @%d" % (c, p, t)
                             for (c, p), t in sorted(w.program_starts.items())))
    for o, why in ex.skipped:
        if why not in ("none",):
            L.append("  ! %s @%#x chunk %d arg1=%d arg2=%d (%s): %s"
                     % (o.kind, o.at, o.chunk_slot, o.arg1, o.arg2,
                        ARG2_NAMES.get(o.arg2, "?"), why))

    for i, s in enumerate(ex.shots):
        cam = s.camera
        good, out = s.roundtrip()
        L.append("")
        L.append("=" * 92)
        L.append("%s -- %s @file %#x, chunk %d sub-file %d, %d B, fires at seq tick %d"
                 % (_shot_label(i, s), s.op.kind, s.op.at, s.slot, s.index, s.size, s.op.seq_tick))
        L.append("  outer Flags %#06x = %s   |   round-trip %s (%d B -> %d B)"
                 % (cam["flags"], " + ".join(outer_groups(cam["flags"])) or "(none)",
                    "BYTE-EXACT" if good else "DIVERGES", s.size, len(out)))
        L.append("  layout: " + "  ".join("%s[%d..%d)" % (n, lo, hi)
                                          for n, lo, hi in block_layout(s.block)))
        if cam["unknown"]:
            L.append("  sequence selector: %d B (bit-3 group; its OUTPUT is an index 0..2 choosing "
                     "the live track -- D4 sec 2.2 correction 2)" % len(cam["unknown"]))
        if cam["position"] is not None:
            n = bin(cam["flags"] & 0xF0).count("1")
            L.append("  anchors: %d B = %d record(s) of 3x s16 (D4 sec 2.2 correction 1); these are "
                     "world-space camera/target anchor points" % (len(cam["position"]), n))
        L.append("  span: %d local frames  (absolute seq ticks %d..%d)"
                 % (shot_span(cam), s.op.seq_tick, s.op.seq_tick + max(0, shot_span(cam) - 1)))
        for si in range(len(cam["sequences"])):
            ks = keyframes(cam, si)
            same = si and cam["sequences"][si] == cam["sequences"][0]
            L.append("  -- sequence%d: %d keyframes%s"
                     % (si, len(ks), "  (BYTE-IDENTICAL to sequence0)" if same else ""))
            if same:
                continue
            for k in ks:
                mark = ""
                if k.marks:
                    mark = "  [frame-word marks %#06x -- undecoded, preserve verbatim]" % k.marks
                L.append("     f%-4d  abs %-4d  flags %#06x%s"
                         % (k.local_frame, s.op.seq_tick + k.local_frame - 1, k.flags, mark))
                p = k.pose("campos")
                if p:
                    L.append("        " + _pose_line("camera", p)
                             + ("   <- INSTANT (no movement block = a placement, not a glide)"
                                if k.is_cut else ""))
                mv = k.movement("cammove")
                if mv:
                    L.append("        move    duration=%-4d ease=%-9s unk=%d"
                             % (mv["duration"], mv["ease"], mv["unknown"]))
                t = k.pose("tgtpos")
                if t:
                    L.append("        " + _pose_line("target", t))
                tm = k.movement("tgtmove")
                if tm:
                    L.append("        tmove   duration=%-4d ease=%-9s unk=%d"
                             % (tm["duration"], tm["ease"], tm["unknown"]))
                f = k.focal()
                if f:
                    L.append("        focal   H=%-5d duration=%-4d flags=%d   "
                             "<- THE PROJECTION DISTANCE (zoom), an independent lever"
                             % (f["distance"], f["duration"], f["flags"]))
                for name in ("sign", "unk3", "unk4", "unk5", "setting", "unk6"):
                    if name in k.fields:
                        L.append("        %-7s %s (verbatim)" % (name, k.fields[name].hex()))
    return L


def timeline_lines(tl: Timeline) -> List[str]:
    L = ["", "=" * 92,
         "THE MERGED TIMELINE -- camera shots and R3's program phases on ONE clock (seq ticks)",
         "  seq tick = the sequence's own authored clock (WAIT arg1==0 sums).  Both columns are",
         "  DERIVED: a camera event at op.seq_tick + local_frame - 1, a phase boundary at the",
         "  0x80+N op's tick + R3's phase start.  No capture, no fitted origin.",
         "",
         "  %-8s %-7s %-22s %s" % ("seqtick", "kind", "who", "what")]
    for r in tl.rows:
        L.append("  %-8d %-7s %-22s %s" % (r.seq_tick, r.kind, r.who, r.what))
    hrows = tl.h_changes()
    if hrows and tl.phases():
        L.append("")
        L.append("  THE TWO CLOCKS -- the PROJECTION-DISTANCE changes against the phase spine.")
        L.append("  (H is the lever TIER R's capture recorded; ops 121/122/148 write gteH alone,")
        L.append("   so this is the camera column a probe can see without a pose readback.)")
        L.append("  %-8s %-34s %-8s %-18s %s" % ("cam@", "camera event", "phase@", "phase", "offset"))
        for c, p, d in tl.pairs(hrows, window=6):
            L.append("  %-8d %-34s %-8d %-18s %+d"
                     % (c.seq_tick, ("%s %s" % (c.who, c.what))[:34], p.seq_tick, p.who, d))
    prs = tl.pairs()
    if prs:
        L.append("")
        L.append("  ALL camera events within 4 ticks of a phase boundary:")
        L.append("  %-8s %-40s %-8s %-18s %s" % ("cam@", "camera event", "phase@", "phase", "offset"))
        for c, p, d in prs:
            L.append("  %-8d %-40s %-8d %-18s %+d"
                     % (c.seq_tick, ("%s %s" % (c.who, c.what))[:40], p.seq_tick, p.who, d))
    return L


# ============================================================ dumps (SCRATCH only)
DUMP_FIELDS = ["effect", "shot", "op", "op_at", "chunk", "subfile", "file_lo", "size",
               "outer_flags", "sequence", "local_frame", "frame_marks", "abs_seq_tick",
               "code_flags", "cam_code", "cam_flags", "cam_pitch", "cam_orientation", "cam_roll",
               "cam_distance", "move_duration", "move_type", "tgt_code", "tgt_flags", "tgt_pitch",
               "tgt_orientation", "tgt_roll", "tgt_distance", "tmove_duration", "tmove_type",
               "focal_H", "focal_duration", "focal_flags"]


def dump_rows(blob: bytes, source: str) -> List[dict]:
    ex = extract_shots(blob, source)
    rows = []
    for i, s in enumerate(ex.shots):
        for si in range(len(s.camera["sequences"])):
            for k in keyframes(s.camera, si):
                r = {"effect": source, "shot": _SHOT_LETTERS[i % 26], "op": s.op.kind,
                     "op_at": s.op.at, "chunk": s.slot, "subfile": s.index, "file_lo": s.lo,
                     "size": s.size, "outer_flags": s.camera["flags"], "sequence": si,
                     "local_frame": k.local_frame, "frame_marks": k.marks,
                     "abs_seq_tick": s.op.seq_tick + k.local_frame - 1, "code_flags": k.flags}
                p = k.pose("campos")
                if p:
                    r.update({"cam_" + a: p[b] for a, b in
                              (("code", "code"), ("flags", "flags"), ("pitch", "pitch"),
                               ("orientation", "orientation"), ("roll", "roll"),
                               ("distance", "distance"))})
                t = k.pose("tgtpos")
                if t:
                    r.update({"tgt_" + a: t[b] for a, b in
                              (("code", "code"), ("flags", "flags"), ("pitch", "pitch"),
                               ("orientation", "orientation"), ("roll", "roll"),
                               ("distance", "distance"))})
                mv = k.movement("cammove")
                if mv:
                    r.update(move_duration=mv["duration"], move_type=mv["type"])
                tm = k.movement("tgtmove")
                if tm:
                    r.update(tmove_duration=tm["duration"], tmove_type=tm["type"])
                f = k.focal()
                if f:
                    r.update(focal_H=f["distance"], focal_duration=f["duration"],
                             focal_flags=f["flags"])
                rows.append(r)
    return rows


def dump_shots(rows: Sequence[dict], out_path: str) -> int:
    """Write decoded rows to a CSV -- SCRATCH only.  Decoded stock data never enters the repo."""
    ap = os.path.abspath(out_path)
    if os.path.commonpath([ap, os.path.abspath(_REPO)]) == os.path.abspath(_REPO):
        raise SummonCameraError("refusing to write decoded stock-derived data under the repo: %s" % ap)
    os.makedirs(os.path.dirname(ap), exist_ok=True)
    with open(ap, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=DUMP_FIELDS, restval="", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows)


# ============================================================ CLI
def _load(effect, root: str = SCRATCH_CORPUS) -> Tuple[bytes, str]:
    path = effect if os.path.sep in str(effect) or str(effect).endswith(".bytes") else \
        os.path.join(root, "ef%03d.bytes" % int(effect))
    if not os.path.isfile(path):
        raise SummonCameraError("no such container: %s (extract the corpus first)" % path)
    with open(path, "rb") as fh:
        return fh.read(), os.path.splitext(os.path.basename(path))[0]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("verb", choices=("read", "roundtrip", "census", "dump", "timeline"))
    ap.add_argument("effect", nargs="?", default=227)
    ap.add_argument("--corpus-root", default=SCRATCH_CORPUS)
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-phases", action="store_true",
                    help="skip R3's state-machine recovery (faster; the timeline loses its phase rows)")
    a = ap.parse_args(argv)

    if a.verb in ("read", "timeline", "dump"):
        blob, src = _load(a.effect, a.corpus_root)
        machines = () if a.no_phases else recover_machines(blob, src)
        if a.verb == "dump":
            out = a.out or os.path.join(SCRATCH_OUT, "%s_camera.csv" % src)
            n = dump_shots(dump_rows(blob, src), out)
            print("wrote %d keyframe rows -> %s" % (n, out))
            return 0
        if a.verb == "read":
            print("\n".join(read_out(blob, src, machines)))
        print("\n".join(timeline_lines(merged_timeline(blob, src, machines))))
        return 0

    rows = census(a.corpus_root, a.limit)
    s = census_summary(rows)
    if a.verb == "roundtrip":
        print("ROUND-TRIP over %d containers: %d/%d camera blocks byte-exact"
              % (s["effects"], s["roundtrip_ok"], s["shots"]))
        for b in s["roundtrip_bad"]:
            print("  FAIL " + b)
        for k in s["skipped"]:
            print("  skipped " + k)
        return 0 if s["roundtrip_ok"] == s["shots"] and not s["roundtrip_bad"] else 1
    for k, v in s.items():
        print("%-24s %s" % (k, v if not isinstance(v, list) else "%d entries" % len(v)))
    return 0


if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
