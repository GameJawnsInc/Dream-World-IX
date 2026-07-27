r"""A stock FF9 summon's CAMERA, made readable -- the extractor, the adapter and the read-out.

A summon's camera is not reachable from the effect program: it is played by the container's SEQUENCE
stream (opcode ``0x29 PLAY_CAMERA``, and far more often ``0x23 SETUP_CAMERA``), which names a camera
sub-file inside the chunk's id-2 archive. The block those ops name is, byte for byte, the SAME format
:mod:`ff9mapkit.battle.camera_codec` already round-trips for battle raw17 cameras -- verified against
every statically-resolvable camera block in the 372-container stock set, all byte-exact.

So this module deliberately owns **no camera grammar of its own**. It contributes the three things the
battle path does not have:

1. **THE EXTRACTOR** -- walk the sequence, resolve each shot's sub-file, hand the codec a block
   (:func:`walk_camera_ops` + :func:`id2_directory` + :func:`extract_shots`).
2. **THE ADAPTER** -- an SFX camera block IS one battle camera without raw17's set-offset-table
   wrapper, so :func:`parse_camera_block` / :func:`serialize_camera_block` are two-line calls into
   ``camera_codec``'s per-camera functions. Nothing in ``camera_codec`` is re-implemented here.
3. **THE READ-OUT + THE MERGED TIMELINE** -- shots decoded to human terms
   (:func:`read_out`), then placed on ONE clock (:func:`merged_timeline`), which is what a rescore
   author actually reads before choosing a keyframe.

THREE CORRECTIONS THIS MODULE CARRIES (each one changes what you decode, not merely how)
----------------------------------------------------------------------------------------
* **THE ID-2 EXTRA-SECTOR CORRECTION.** :func:`~ff9mapkit.summons.container.parse_header` records an
  id-2 resource's payload at ``res.offset`` and its ``extra_sectors`` (the ``info != 0`` conditional
  field) as following it. The directory actually sits AFTER that extra region:
  ``base = res.offset + extra_sectors * 0x800``. Both readings consume identical total bytes, so the
  container walk is unaffected either way -- only the DIRECTORY BASE moves. On 371 of 372 stock
  containers ``extra_sectors == 0`` and the two coincide; on the one where it does not, parsing at
  ``res.offset`` yields a plausible-looking short table whose entries then read out of range, while
  the corrected base yields a monotone, in-bounds directory whose blocks round-trip.
  :func:`id2_directory` applies the correction.
* **THE FRAME WORD CARRIES FLAGS.** A Code's ``frame`` u16 is not a bare frame number: keyframes
  across the corpus set bits in ``0xE000``, almost always on the FIRST keyframe of a sequence. Read as
  a plain number those look like a shot that starts at frame 16385 and then runs backwards.
  :func:`frame_number` / :func:`frame_marks` split the word. The codec stores the word verbatim, so a
  round-trip is unaffected -- but anything that WRITES a frame must preserve the high bits.
* **``0x23 SETUP_CAMERA`` IS A CAMERA-BLOCK OP TOO.** It resolves through the same directory, and it
  reaches roughly NINE TENTHS of the corpus's statically-resolvable camera blocks. A tool that walks
  only ``0x29`` sees about a tenth of the camera data that is there.

WHAT IS NOT STATICALLY RESOLVABLE -- say it out loud
-----------------------------------------------------
``0x29``'s ``arg2`` selects the shot: ``0`` literal, ``1`` last-used, ``2`` LCG-random, ``3`` table
lookup keyed on a battle field. Roughly a fifth of the corpus's camera-naming ops are that last class,
and their table is not merely undecoded -- it is ABSENT from the container, so nothing offline can name
the block they play. :func:`walk_camera_ops` marks them ``dynamic`` rather than guessing, and they land
in :attr:`Extract.skipped` where a caller must deal with them explicitly.

PROVENANCE: this module reads a caller-supplied blob (a stock ``ef###`` the user extracted from, or
this kit read out of, their OWN install) and returns offsets, counts, frame numbers and decoded angles.
It embeds no game bytes and writes nothing.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from ..battle import camera_codec
from . import container

SECTOR = container.SECTOR

#: sequence opcodes this module cares about
OP_END = 0x00
OP_WAIT = 0x01
OP_LOAD_CHUNK = 0x05
OP_SETUP_CAMERA = 0x23
OP_PLAY_CAMERA = 0x29
OP_RUN_PROGRAM = 0x80          # 0x80 + N runs the chunk's program-table entry N

#: ``0x23``'s "no camera" sentinel and ``0x29``'s arg2 dispatch arms
SETUP_NONE = 0xFF
ARG2_LITERAL, ARG2_LAST, ARG2_RANDOM, ARG2_TABLE = 0, 1, 2, 3
ARG2_NAMES = {0: "literal", 1: "last-used", 2: "random", 3: "table-lookup"}

#: the Code ``frame`` word: low 13 bits are the frame, the top 3 are undecoded marks (see module head)
FRAME_MASK = 0x1FFF
FRAME_MARK_MASK = 0xE000

#: outer Flags groups, in the order the offset table lists them
OUTER_GROUPS = ((0x01, "sequence0"), (0x02, "sequence1"), (0x04, "sequence2"),
                (0x08, "selector"), (0xF0, "anchors"))

#: Movement ``type``. 0/1/2 are ``camera_codec``'s battle-side easing names; every other value is a
#: real corpus value with no read handler yet -- named ``type-N`` on purpose rather than guessed at.
EASE_NAMES = {0: "linear", 1: "ease-in", 2: "ease-out"}

#: shot labels, in resolution order -- the handle a human (and a rescore spec) names a shot by
_SHOT_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

__all__ = [
    "SummonCameraError", "SECTOR",
    "OP_END", "OP_WAIT", "OP_LOAD_CHUNK", "OP_SETUP_CAMERA", "OP_PLAY_CAMERA", "OP_RUN_PROGRAM",
    "SETUP_NONE", "ARG2_LITERAL", "ARG2_LAST", "ARG2_RANDOM", "ARG2_TABLE", "ARG2_NAMES",
    "FRAME_MASK", "FRAME_MARK_MASK", "OUTER_GROUPS", "EASE_NAMES",
    "frame_number", "frame_marks",
    "CameraOp", "SeqWalk", "walk_camera_ops", "Id2Archive", "id2_directory",
    "Shot", "Extract", "extract_shots",
    "parse_camera_block", "serialize_camera_block", "outer_groups", "block_layout",
    "Keyframe", "keyframes", "shot_span",
    "TimelineRow", "Timeline", "merged_timeline", "read_out", "timeline_lines",
]


class SummonCameraError(RuntimeError):
    """Raised when a camera op names a sub-file that cannot be resolved, or a block that is not one."""


def _u16(b, o) -> int:
    return struct.unpack_from("<H", b, o)[0]


# ============================================================ the frame word
def frame_number(word: int) -> int:
    """The Code's frame number -- the low 13 bits (see THE FRAME WORD CARRIES FLAGS, module head)."""
    return word & FRAME_MASK


def frame_marks(word: int) -> int:
    """The frame word's undecoded high bits. Preserve them verbatim when authoring."""
    return word & FRAME_MARK_MASK


# ============================================================ (A) THE EXTRACTOR
@dataclass
class CameraOp:
    """One sequence op that names a camera block."""
    at: int                     # file offset of the 3-byte record
    code: int                   # 0x23 SETUP_CAMERA | 0x29 PLAY_CAMERA
    arg1: int
    arg2: int
    chunk_slot: int             # the chunk the last LOAD_CHUNK selected (its TABLE ordinal)
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
    r"""Walk the sequence stream and collect every camera-naming op.

    THE CLOCK. ``WAIT`` (0x01) with ``arg1 == 0`` waits ``arg2`` ticks; with ``arg1 != 0`` it blocks
    until channel-flag[arg2] clears -- a duration nothing static can supply, so those are COUNTED, not
    summed. ``seq_tick`` is therefore the effect's own authored clock with every statically-unknown
    blocking wait treated as zero. It is not the engine's frame index: mapping to that would need one
    additive origin, and :func:`merged_timeline` derives and reports the offset rather than assuming it.

    Summing ``arg2`` for a BLOCKING wait -- an earlier decoder did -- adds a channel INDEX to a tick
    count. Every offset this module reports is a DIFFERENCE between two ticks on the same clock, so
    that choice largely cancels; the strict rule is nevertheless the correct one and is what runs here.
    """
    ops: List[CameraOp] = []
    starts: Dict[Tuple[int, int], int] = {}
    slot, tick, blocking, n = 0, 0, 0, 0
    for op in container.parse_op_stream(blob):
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
    entries: Tuple[int, ...]   # signed s32 offsets relative to ``base``
    extra_sectors: int

    def bounds(self, idx: int) -> Tuple[int, int]:
        """``(lo, hi)`` file offsets of sub-file ``idx``.

        The end is the next STRICTLY GREATER entry (equal entries are aliases of the same sub-file)
        or the region end. The corpus fact that makes this safe for cameras: no camera block is ever
        the last sub-file in its chunk, so a camera's end is always a real directory delta and never
        the region's sector padding.
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


def id2_directory(blob: bytes, cont: "container.Container", slot: int) -> Optional[Id2Archive]:
    r"""The chunk's sub-file archive, WITH THE EXTRA-SECTOR CORRECTION (module head).

    ``parse_header`` reads the ``id == 2 && info != 0`` conditional field into ``extra_sectors`` and
    advances the cursor by it AFTER the payload. The directory, however, sits after the extra region:
    ``base = res.offset + extra_sectors * 0x800``, and the region the directory's offsets index is then
    the resource's OWN declared ``nbytes`` starting there -- so the two readings consume identical
    total bytes and only the base moves. Returns ``None`` when the chunk carries no id-2 resource (or
    an empty one), which is a normal container shape, not an error.
    """
    if not 0 <= slot < len(cont.chunks):
        return None
    res = next((r for r in cont.chunks[slot].resources if r.id == 2), None)
    if res is None:
        return None
    extra = res.extra_sectors or 0
    base = res.offset + extra * SECTOR
    size = res.nbytes
    if size <= 0:
        return None
    try:
        entries = container.parse_directory(blob, base)
    except (struct.error, IndexError) as e:
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
        """``(is byte-exact, re-serialised bytes)`` -- the block re-emitted through the battle codec."""
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
        return sum(1 for _o, w in self.skipped if w == "dynamic")


def extract_shots(blob: bytes, source: str = "?") -> Extract:
    """Every camera block a container's sequence statically names, resolved to bytes and parsed."""
    cont = container.parse_header(blob)
    walk = walk_camera_ops(blob)
    archives: Dict[int, Optional[Id2Archive]] = {}
    shots: List[Shot] = []
    skipped: List[Tuple[CameraOp, str]] = []
    for op in walk.ops:
        if op.resolution != "literal":
            skipped.append((op, op.resolution))
            continue
        if op.chunk_slot not in archives:
            archives[op.chunk_slot] = id2_directory(blob, cont, op.chunk_slot)
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
        except (struct.error, IndexError, camera_codec.CameraCodecError, SummonCameraError) as e:
            skipped.append((op, "block did not parse: %s: %s" % (type(e).__name__, e)))
            continue
        shots.append(Shot(op, arc.base, lo, hi, block, cam))
    return Extract(source, walk, tuple(shots), tuple(skipped))


# ============================================================ (B) THE DECODER / ADAPTER
def parse_camera_block(block: bytes) -> dict:
    """Parse ONE SFX camera sub-file with the BATTLE codec, unmodified.

    A raw17 battle camera block is a set-offset table followed by N cameras; an SFX camera sub-file IS
    one of those cameras, delimited by the id-2 directory instead of by the set-offset table. So the
    whole adapter is: hand ``camera_codec``'s per-camera parser the block's own bounds.
    """
    if len(block) < 4:
        raise SummonCameraError("camera block is %d bytes -- too short for Flags + one offset"
                                % len(block))
    return camera_codec.parse_camera(block, 0, len(block))


def serialize_camera_block(cam: dict) -> bytes:
    """Re-emit a parsed SFX camera block with the BATTLE codec, unmodified (the round-trip's other
    half)."""
    return camera_codec.serialize_camera(cam)


def outer_groups(flags: int) -> List[str]:
    """The groups an outer Flags word declares, in the order the offset table lists them."""
    out = [name for bit, name in OUTER_GROUPS[:4] if flags & bit]
    if flags & 0xF0:
        out.append("anchors x%d" % bin(flags & 0xF0).count("1"))
    return out


def block_layout(block: bytes) -> List[Tuple[str, int, int]]:
    """``[(group name, lo, hi)]`` within the block -- the offset table read literally.

    The corpus invariant behind it: the table's first entry equals the table's own end and the entries
    are STRICTLY increasing, i.e. the groups' physical order IS the canonical order the codec re-emits
    them in. Every stock camera block satisfies both, which is *why* the round-trip is byte-exact
    rather than merely structure-preserving.
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

    # ---- typed views over the verbatim sub-blocks (SFXDataCamera field order, codec ``split_code``)
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
    """One sequence's Codes as :class:`Keyframe`\\ s (the frame-0 terminator dropped)."""
    if seq_index >= len(cam["sequences"]):
        return []
    out = []
    for c in cam["sequences"][seq_index]:
        w = c.get("frame") or 0
        if not w:
            continue
        out.append(Keyframe(frame_number(w), frame_marks(w), c["flags"],
                            camera_codec.split_code(c["flags"], c["block"])))
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
    seq_tick: int                # THE shared clock (see walk_camera_ops)
    kind: str                    # 'camera' | 'phase'
    who: str                     # 'shot A (c0 idx6)' | 'ef227:c0 s1'
    what: str                    # what changes
    h: Optional[int] = None      # the projection distance this row writes, if any
    state: Optional[int] = None  # the phase this row begins, if any


@dataclass
class Timeline:
    source: str
    rows: Tuple[TimelineRow, ...]
    program_starts: Dict[Tuple[int, int], int]
    machines: Tuple[object, ...] = ()

    def cameras(self) -> List[TimelineRow]:
        return [r for r in self.rows if r.kind == "camera"]

    def phases(self) -> List[TimelineRow]:
        return [r for r in self.rows if r.kind == "phase"]

    def h_changes(self) -> List[TimelineRow]:
        """Every row that CHANGES the projection distance, in order -- the one camera observable an
        in-game probe can read without a pose readback."""
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
        """``(camera row, nearest phase row, camera_tick - phase_tick)`` for every camera row within
        ``window`` ticks of a phase boundary -- THE TWO CLOCKS, as a number instead of a note.

        Empty when no phases were supplied: a caller that passes no ``machines`` gets no phase rows,
        and pairing a camera against nothing is not something to fake a neighbour for.
        """
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


def _shot_label(i: int, s: Shot) -> str:
    return "shot %s (c%d idx%d)" % (_SHOT_LETTERS[i % 26], s.slot, s.index)


def _machine_slot(sm) -> int:
    """``ef227:c0`` -> 0. A recovered state machine names its image by chunk ordinal, which is
    ``LOAD_CHUNK``'s own key -- so the two clocks join on it without a lookup table."""
    tail = str(getattr(sm, "image", "")).rsplit(":c", 1)
    try:
        return int(tail[-1])
    except ValueError:
        return 0


def merged_timeline(blob: bytes, source: str = "?",
                    machines: Optional[Sequence[object]] = None) -> Timeline:
    r"""ONE table: camera events and (optionally) program phases on the SEQUENCE CLOCK.

    Both clocks are derived, neither is fitted:

    * a camera event is at ``op.seq_tick + local_frame - 1`` -- the stepper advances once per
      ``SFX_UpdateCamera``, i.e. once per host frame, from the moment the block is installed;
    * a phase boundary is at ``program_start_tick + phase.start_tick``, where the program start is the
      ``0x80+N`` op's own tick in the SAME sequence walk.

    So the OFFSET between a cut and a beat is a pure data+code quantity -- no capture, no fitted
    origin, nothing that could be tuned to match an observation.

    ``machines`` is OPTIONAL and defaults to none. Recovering a container's program state machines
    needs a MIPS disassembler + annotator that this kit does not ship (it lives in the study), so the
    kit's timeline is the camera column alone: every camera row is identical either way, and what is
    missing is the phase spine and therefore :meth:`Timeline.pairs`. That is a REDUCED read-out, not a
    wrong one -- pass recovered machines in and the phase rows appear, with no other behaviour change.
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


# ============================================================ the human read-out
def _pose_line(tag: str, p: Dict[str, int]) -> str:
    return ("%-7s code=%-3d flags=%#04x  pitch=%-4d orientation=%-4d roll=%-4d distance=%-4d"
            % (tag, p["code"], p["flags"], p["pitch"], p["orientation"], p["roll"], p["distance"]))


def read_out(blob: bytes, source: str,
             machines: Optional[Sequence[object]] = None) -> List[str]:
    """THE READ-OUT: every shot in human terms -- the lines a rescore author picks a keyframe from.

    ``machines`` is accepted for signature parity with :func:`merged_timeline` and is unused here: the
    shot listing has never depended on program phases, and taking the parameter keeps a caller from
    having to know which of the two read-out halves does.
    """
    ex = extract_shots(blob, source)
    L: List[str] = []
    w = ex.walk
    L.append("%s -- %d sequence ops, %d authored ticks, %d blocking waits (duration not static)"
             % (source, w.n_ops, w.total_ticks, w.blocking_waits))
    L.append("  camera ops: %d  ->  %d resolved shots, %d dynamic (runtime-chosen), %d 'no camera'"
             % (len(w.ops), len(ex.shots), ex.dynamic,
                sum(1 for _o, why in ex.skipped if why == "none")))
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
                     "the live track)" % len(cam["unknown"]))
        if cam["position"] is not None:
            n = bin(cam["flags"] & 0xF0).count("1")
            L.append("  anchors: %d B = %d record(s) of 3x s16; these are world-space camera/target "
                     "anchor points" % (len(cam["position"]), n))
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
    """The merged timeline as printable lines. The phase-relative sections appear only when the
    timeline actually carries phase rows -- with no ``machines`` supplied this prints the camera
    column alone rather than empty headers for a comparison nobody made."""
    L = ["", "=" * 92,
         "THE MERGED TIMELINE -- camera shots%s on ONE clock (seq ticks)"
         % (" and program phases" if tl.phases() else ""),
         "  seq tick = the sequence's own authored clock (WAIT arg1==0 sums).  Both columns are",
         "  DERIVED: a camera event at op.seq_tick + local_frame - 1, a phase boundary at the",
         "  0x80+N op's tick + the phase start.  No capture, no fitted origin.",
         "",
         "  %-8s %-7s %-22s %s" % ("seqtick", "kind", "who", "what")]
    for r in tl.rows:
        L.append("  %-8d %-7s %-22s %s" % (r.seq_tick, r.kind, r.who, r.what))
    hrows = tl.h_changes()
    if hrows and tl.phases():
        L.append("")
        L.append("  THE TWO CLOCKS -- the PROJECTION-DISTANCE changes against the phase spine.")
        L.append("  (H is the one camera value an in-game probe can read without a pose readback.)")
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
