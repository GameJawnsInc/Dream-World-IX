"""The story-write trace, KIT side -- read what the engine recorded, join it to the script, compare runs.

The engine half (memoria-patch s88, ``Memoria/Harness/StoryTrace.cs``) hooks ``EBin.SetVariableValueInternal``
and writes one JSON row per ``gEventGlobal`` store to ``<game>/x64/ff9harness/story.jsonl``. This module is
everything after that file exists: parse + validate the rows against THE ROW CONTRACT (proto 1,
``studies/story-trace/PLAN.md``), split the file into its traced runs (one per ``arm``; a run with no ``off``
is INCOMPLETE, never read as whole), segment them by epoch, fold the suppression counts back onto their sites,
drop the story-noise bits (``flags.story_noise_bits`` -- the one mask), JOIN each script row to the
instruction that wrote it, and diff N stock runs against N fork runs as sets.

THE CONTRACT IS ENFORCED HERE, not described: an unknown kind, a missing or extra field, a string where a
number belongs, a width the engine does not have -- each is a :class:`TraceError` naming the line. A reader
that skipped what it did not understand would turn an engine/kit skew into "the game wrote less", which is
the exact false negative this instrument exists to remove.

THE JOIN (:class:`ScriptIndex`). ``allObjsEBData[sid]`` is the kit's ``Entry`` (``EventEngine.cs:602-613``
copies each entry's bytes out of the file), so an ``eb`` row's ``ip`` is entry-relative and
``entry.abs_start + ip`` is a byte offset in the ``.eb``. The function is the one the engine's own
``StoryTrace.TagAt`` picks (the LARGEST start at or below ``ip``); the row's ``tag`` must agree with it; the
offset must be an instruction boundary; and that instruction must STORE to the row's byte -- the store
targets come from walking its expression operands the way the engine's CalcStack does (``exprsem``'s
arities). Anything else is a JOIN FAILURE, reported with the reason, never guessed onto a nearby
instruction.

THE ALIGNMENT. Rows key on ``(donor, sid, tag, offset within the function)``. A fork's ``[startup]`` (and
``[party]``, and the ``[deathrules]`` wipe-warp) PREPENDS to a function (``build._apply_startup``), which
shifts every offset in it and every later function in the file -- so fork offsets are aligned per function:
the donor's body is the fork body's SUFFIX, compared instruction by instruction (opcode + length), so a
same-length operand remap (a verbatim fork's ``Field()`` targets) still aligns. A row inside the prefix keys
at a NEGATIVE offset: the kit's own prepend, which stock can never match.

THE SITE KEY CARRIES THE FIELD. The engine collapses repeated stores per ``(fld, m, src, sid, tag, ip, byte, w,
bit)`` per epoch (:attr:`Row.site`): a field change opens no epoch, and sibling fields run byte-identical code at
one (sid, tag, ip) -- Dali's ``Bit[2102]`` store in 350/352/.../358 and in 450 -- so each field's first store
there is its own row, and a ``c`` row carries its SITE's ``fld``/``don``/``m`` (the flush's ``f``/``p``/``sc``).
A count therefore folds onto exactly one field's site.

THE MEMBERS AND THE SEAM. A chain fork is a SET of fork fields (``members``, ``{fork id: donor id}``); a member
whose exit was left pointing at a real field walks the run into the real game, where every row is the real
game's own and keys exactly like stock's (the key carries no ``fld``). Merged, a chain that misses a field would
match stock by leaving itself. So with a member set, a fork run's rows in a REAL field that is not a member,
after the run first stood in a member, are SEAM rows: kept in their own keys, reported as the crossing that
led there (the member, the real field, the first frame, the member's last write), and a stock key the fork
side wrote only there is REACHED ONLY ACROSS A SEAM -- never matched, never folded into STOCK ONLY.

WRITERS and CLOBBERS. The stock runs say who writes what: :func:`writers` indexes every stock ``(variable,
value)`` by the donors that wrote it (``Global.Bit[2102] := 1 <- {450}``). And they say how wide each variable
is: a fork's multi-byte write whose old/new show a byte changing OUTSIDE the variable stock writes at its start
(a 16-bit ``[startup]`` word at 296, where stock stores ``SByte[296]`` and ``UInt16[297]``) is a
NEIGHBOUR-BYTE CLOBBER -- the trace records no reads, so this is the only place a clobbered gate shows.

PRE-EMPTED. A fork's prepend that stamps a value every stock run writes ITSELF, at its own site (round 4's seed
set latch 2064 := 1, which stock's 351 lobby exit sets on the way out), does the story's work before the story
does: whatever the stock writer's guard does with the value it finds is decided by the seed. The prepend key is
FORK ONLY by construction (a negative offset stock can never match); PRE-EMPTED names the stock writer beside it.

Provenance: reads the user's own install and build output; ships no SE bytes.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field as dfield
from pathlib import Path

from . import flags as flagsmod
from .eb import EbScript, disasm
from .eb._exprtable import EXPR_OP_NAMES, VAR_TYPE
from .eb.exprsem import OP_SEMANTICS, WRITE

# ================================================================== THE ROW CONTRACT (proto 1)
PROTO = 1

#: every row carries these (PLAN.md "Every row carries")
COMMON_FIELDS = ("k", "f", "p", "m", "fld", "don", "sc")
#: and exactly these per kind -- a key outside the union is as much a contract break as a missing one
KIND_FIELDS = {
    "w": ("src", "sid", "uid", "lvl", "ip", "tag", "add", "byte", "w", "bit", "old", "new", "same"),
    "r": ("byte", "old", "new", "why"),
    "c": ("src", "sid", "tag", "ip", "byte", "w", "bit", "n", "last"),
    "e": ("why",),
}
_STRING_FIELDS = frozenset({"k", "src", "w", "why"})

SOURCES = ("eb", "cs", "harness")
#: `w`: the engine's own EBin.VariableType names (StoryTrace.WidthName = eb/_exprtable.VAR_TYPE) -> the
#: bytes a store of that width touches, and the value range the engine reads it back as (UInt24's read
#: sign-extends, EBin.GetVariableValueInternal -- so its range is Int24's)
WIDTH_BYTES = {"SBit": 1, "Bit": 1, "SByte": 1, "Byte": 1, "Int16": 2, "UInt16": 2, "Int24": 3, "UInt24": 3}
BIT_WIDTHS = ("SBit", "Bit")
_WIDTH_RANGE = {"SBit": (0, 1), "Bit": (0, 1), "SByte": (-128, 127), "Byte": (0, 255),
                "Int16": (-0x8000, 0x7FFF), "UInt16": (0, 0xFFFF),
                "Int24": (-0x800000, 0x7FFFFF), "UInt24": (-0x800000, 0x7FFFFF)}
RESIDUE_WHY = ("frame", "prestore")
EPOCH_WHY = ("arm", "swap", "debug-restore", "debug-clear", "netsync", "off")
STORY_LEN = 2048                    # gEventGlobal is Byte[2048]
FIELD_MODE = 1                      # `m`: gMode 1 = field; only a field row joins a field .eb


class TraceError(ValueError):
    """A story.jsonl that breaks the row contract -- the line and the broken rule, never a skipped row."""


@dataclass(frozen=True)
class Row:
    """One validated contract row. ``width`` is the contract's ``w`` (renamed: ``row.w`` would read as the
    kind); fields a kind does not carry are None."""

    k: str
    f: int
    p: int
    m: int
    fld: int
    don: int
    sc: int
    line: int = 0                   # 1-based line in its file (0 = not read from a file)
    src: str | None = None
    sid: int | None = None
    uid: int | None = None
    lvl: int | None = None
    ip: int | None = None
    tag: int | None = None
    add: int | None = None
    byte: int | None = None
    width: str | None = None
    bit: int | None = None
    old: int | None = None
    new: int | None = None
    same: int | None = None
    why: str | None = None
    n: int | None = None
    last: int | None = None

    @property
    def is_bit(self) -> bool:
        return self.width in BIT_WIDTHS

    @property
    def span(self) -> range:
        """The bytes this row touches."""
        return range(self.byte, self.byte + (WIDTH_BYTES[self.width] if self.width else 1))

    @property
    def site(self) -> tuple:
        """The engine's suppression key (``StoryTrace.Site``): ``(fld, m, src, sid, tag, ip, byte, w, bit)`` --
        a ``c`` row's ``fld``/``m`` are its site's, so it matches the ``w`` rows it counted."""
        return (self.fld, self.m, self.src, self.sid, self.tag, self.ip, self.byte, self.width, self.bit)

    @property
    def target(self) -> str:
        """The written variable as eb-src spells it: ``Global.Bit[2345]`` / ``Global.UInt16[236]``."""
        return f"Global.{self.width}[{self.bit if self.is_bit else self.byte}]"

    def byte_changes(self) -> dict:
        """``{byte: (old, new)}`` for each byte a multi-byte ``w`` row changed, read off its old/new the way
        the engine lays the value down (two's complement, little-endian: SC 3115 is bytes 43, 12). A bit or
        byte store touches only its own byte: ``{}``."""
        n = WIDTH_BYTES[self.width]
        if n == 1:
            return {}
        mask = (1 << 8 * n) - 1
        old, new = self.old & mask, self.new & mask
        return {self.byte + i: ((old >> 8 * i) & 0xFF, (new >> 8 * i) & 0xFF) for i in range(n)
                if (old >> 8 * i) & 0xFF != (new >> 8 * i) & 0xFF}


def _fail(line: int, msg: str):
    raise TraceError(f"story.jsonl line {line}: {msg}" if line else f"story row: {msg}")


def parse_row(obj, *, line: int = 0) -> Row:
    """Validate ONE decoded JSON object against proto 1 and return it as a :class:`Row`."""
    if not isinstance(obj, dict):
        _fail(line, f"a row is a JSON object, got {type(obj).__name__}")
    k = obj.get("k")
    if k not in KIND_FIELDS:
        _fail(line, f"unknown row kind {k!r} (proto {PROTO} has {', '.join(KIND_FIELDS)})")
    want = COMMON_FIELDS + KIND_FIELDS[k]
    missing = [x for x in want if x not in obj]
    extra = sorted(set(obj) - set(want))
    if missing:
        _fail(line, f"a {k!r} row is missing {', '.join(missing)}")
    if extra:
        _fail(line, f"a {k!r} row carries {', '.join(extra)}, which proto {PROTO} does not define -- "
                    f"an engine newer than this reader, or a renamed field")
    for key in want:
        v = obj[key]
        if key in _STRING_FIELDS:
            if not isinstance(v, str):
                _fail(line, f"{key} must be a string, got {v!r}")
        elif isinstance(v, bool) or not isinstance(v, int):
            _fail(line, f"{key} must be a JSON integer (numbers are never strings), got {v!r}")
    kw = {("width" if key == "w" else key): obj[key] for key in want}
    row = Row(line=line, **kw)
    _check_row(row, line)
    return row


def _check_row(r: Row, line: int) -> None:
    """The value rules each kind's fields obey -- the engine's own invariants, so a break is a real defect."""
    if r.byte is not None and not 0 <= r.byte < STORY_LEN:
        _fail(line, f"byte {r.byte} is outside gEventGlobal (0..{STORY_LEN - 1})")
    if r.k in ("w", "c"):
        if r.src not in SOURCES:
            _fail(line, f"src {r.src!r} is not one of {', '.join(SOURCES)}")
        if r.width not in WIDTH_BYTES:
            _fail(line, f"w {r.width!r} is not an engine variable width ({', '.join(WIDTH_BYTES)})")
        if r.byte + WIDTH_BYTES[r.width] > STORY_LEN:
            _fail(line, f"a {r.width} store at byte {r.byte} runs past gEventGlobal")
        if r.is_bit:
            if r.bit < 0 or r.bit >> 3 != r.byte:
                _fail(line, f"bit {r.bit} is not a bit of byte {r.byte}")
        elif r.bit != -1:
            _fail(line, f"a {r.width} store carries bit {r.bit}; only a bit store has one (-1 otherwise)")
        lo, hi = _WIDTH_RANGE[r.width]
        for key in ("old", "new") if r.k == "w" else ("last",):
            v = getattr(r, key)
            if not lo <= v <= hi:
                _fail(line, f"{key} {v} is outside what a {r.width} reads as ({lo}..{hi})")
    if r.k == "w":
        if r.same not in (0, 1) or r.same != int(r.old == r.new):
            _fail(line, f"same {r.same} disagrees with old {r.old} / new {r.new}")
        if r.add not in (0, 1):
            _fail(line, f"add must be 0 or 1, got {r.add}")
        if r.src != "eb" and (r.sid, r.uid, r.lvl, r.ip, r.tag, r.add) != (-1, -1, -1, -1, -1, 0):
            # StoryTrace.AfterStore: at a cs/harness store s1 is whatever object last ran, so the engine
            # names no writer -- attribution on such a row would be a stale object's, not the store's
            _fail(line, f"a {r.src!r} row names a writer (sid/uid/lvl/ip/tag must be -1, add 0)")
        if r.add == 1 and r.tag != -1:
            _fail(line, "an addition-buffer row carries a tag; the buffer's ip has none")
    elif r.k == "r":
        if r.why not in RESIDUE_WHY:
            _fail(line, f"residue why {r.why!r} is not one of {', '.join(RESIDUE_WHY)}")
        if not (0 <= r.old <= 255 and 0 <= r.new <= 255) or r.old == r.new:
            _fail(line, f"residue old {r.old} / new {r.new} is not a byte that changed")
    elif r.k == "c":
        if r.n < 1:
            _fail(line, f"a count row suppressing {r.n} rows")
    elif r.k == "e" and r.why not in EPOCH_WHY:
        _fail(line, f"epoch why {r.why!r} is not one of {', '.join(EPOCH_WHY)}")


def parse_text(text: str, *, live: bool = False) -> list:
    """Every row of a story.jsonl body. ``live`` = the file is still being appended: an UNTERMINATED last
    line is an append in flight (``StoryTrace.Flush`` writes whole rows, but a reader can land mid-write)
    and is held back for the next read. A collected trace is complete, so there it is parsed like any
    line -- and a torn one is an error."""
    lines = text.split("\n")
    tail = lines.pop()                                  # "" when the text ends with a newline
    if tail and not live:
        lines.append(tail)
    out = []
    for i, ln in enumerate(lines, 1):
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
        except ValueError as ex:
            raise TraceError(f"story.jsonl line {i}: not JSON ({ex})") from ex
        out.append(parse_row(obj, line=i))
    return out


def read_trace(path) -> list:
    """Every row of a COLLECTED story.jsonl (utf-8, BOM tolerated like state.json)."""
    return parse_text(Path(path).read_text(encoding="utf-8-sig"))


# ================================================================== epochs + suppressed counts
@dataclass
class Site:
    """One suppression site within one epoch: the rows the engine emitted there, plus what it counted."""

    key: tuple
    rows: list = dfield(default_factory=list)
    suppressed: int = 0
    last: int | None = None
    counted_at: int = 0             # the line of the `c` row that carried `last` (the epoch's close)


@dataclass
class Epoch:
    """The rows between two ``e`` rows: the shadow equalled live at its start (PLAN.md, kind ``e``)."""

    index: int
    why: str                        # the `e` row that opened it
    closed_by: str | None = None    # the `e` row that closed it; None = the file ended inside it
    writes: list = dfield(default_factory=list)
    residue: list = dfield(default_factory=list)
    counts: list = dfield(default_factory=list)
    sites: dict = dfield(default_factory=dict)


def epochs(rows) -> list:
    """Segment rows by epoch and fold every ``c`` row onto its site.

    The engine's shape, enforced: a trace OPENS with an epoch (``StoryTrace.Start`` writes ``arm`` first);
    every ``e`` but ``off`` opens the next epoch; nothing but another epoch follows ``off``; ``c`` rows
    arrive only at an epoch's close (``EmitCounts`` runs just before its ``e`` row); and a count names a
    site where the epoch EMITTED a row -- the first store at a site is always emitted, so a count with no
    row is rows lost between the engine and this reader."""
    out: list = []
    cur: Epoch | None = None
    closing = False                                     # a `c` row was read: only `c`/`e` may follow
    for r in rows:
        if r.k == "e":
            if cur is not None:
                cur.closed_by = r.why
                _fold_counts(cur)
                cur = None
            if r.why != "off":
                cur = Epoch(len(out), r.why)
                out.append(cur)
            closing = False
            continue
        if cur is None:
            _fail(r.line, f"a {r.k!r} row outside any epoch -- a trace opens with an `e` row and "
                          f"records nothing between `off` and the next `arm`")
        if r.k == "c":
            cur.counts.append(r)
            closing = True
            continue
        if closing:
            _fail(r.line, f"a {r.k!r} row after the epoch's counts -- counts only close an epoch")
        if r.k == "w":
            cur.writes.append(r)
            cur.sites.setdefault(r.site, Site(r.site)).rows.append(r)
        else:
            cur.residue.append(r)
    if cur is not None:
        _fold_counts(cur)
    return out


def _fold_counts(ep: Epoch) -> None:
    for c in ep.counts:
        site = ep.sites.get(c.site)
        if site is None:
            _fail(c.line, f"counts {c.n} suppressed rows at a site this epoch never emitted "
                          f"({c.target} src {c.src} field {c.fld} mode {c.m} sid {c.sid} tag {c.tag} ip {c.ip})")
        site.suppressed += c.n
        site.last = c.last
        site.counted_at = c.line


def split_runs(rows) -> list:
    """One row list per traced RUN. The engine only appends and a harness ``reset`` is a Stop, not a new
    file, so one story.jsonl holds every ``storytrace 1`` of a launch -- each one an ``arm`` epoch. Read as
    one run, their union would count a key reached in 1 of 3 runs as reached in 1 of 1.

    A run OPENS with ``arm`` (``StoryTrace.Start`` writes it first). A row before the first one is another
    arm's tail -- a leaked run's ``storytrace 0`` landing after this run cleared the file -- and is an error,
    never silently dropped."""
    runs: list = []
    for r in rows:
        if r.k == "e" and r.why == "arm":
            runs.append([r])
        elif not runs:
            _fail(r.line, f"a {r.k!r} row before the first `arm` epoch -- a trace opens with `arm`; this is "
                          f"another arm's tail (a leaked run's `storytrace 0` landing after the reset)")
        else:
            runs[-1].append(r)
    return runs


# ================================================================== masking (flags.story_noise_bits)
def noise_regions(row: Row) -> tuple:
    """The story-noise region names a row falls in, or ``()`` when it is story. A bit store masks by its
    bit; a wider store (and a residue byte) only when EVERY bit of every byte it touches is noise -- a word
    straddling one noise byte and one story byte is still a story write."""
    noise = flagsmod.story_noise_bits()
    bits = [row.bit] if row.is_bit else [b * 8 + i for b in row.span for i in range(8)]
    if not all(b in noise for b in bits):
        return ()
    return tuple(sorted({flagsmod.bit_region(b).name for b in bits}))


# ================================================================== THE JOIN
#: lane-(a) stores (EBin.cs, the op_binary switch): how deep below the CalcStack top the LVALUE sits when the
#: operator runs. ++/-- Eval the top, ``advanceTopOfStack`` back onto it, SetVariableValue it; B_LET and the
#: compound *_LET Eval the rhs off the top, then store through the var code beneath it.
_LVALUE_DEPTH = {
    "B_POST_PLUS": 1, "B_POST_MINUS": 1, "B_PRE_PLUS": 1, "B_PRE_MINUS": 1,
    "B_LET": 2, "B_MULT_LET": 2, "B_DIV_LET": 2, "B_REM_LET": 2, "B_PLUS_LET": 2, "B_MINUS_LET": 2,
    "B_SHIFT_LEFT_LET": 2, "B_SHIFT_RIGHT_LET": 2, "B_AND_LET": 2, "B_XOR_LET": 2, "B_OR_LET": 2,
}
#: exprsem WRITE operators that never reach SetVariableValue (partyadd recruits a member). Every OTHER write
#: operator -- the member-list _A/_E forms, which store through ``putv`` behind the member-list stack walk --
#: is recorded as a store whose target the kit does not resolve statically.
_NOT_A_VARIABLE_STORE = frozenset({"B_PARTYADD"})
_OPERAND_PUSHES = frozenset({0x29, 0x5F, 0x78, 0x79, 0x7A, 0x7D, 0x7E})   # member/ptr/obj/sys + consts
_EXPR_END, _FLEX = 0x7F, 0xD3
_GLOBAL = 0

#: Engine writes INSIDE a non-store opcode, by the engine's own code: ``(donor field, opcode, tag operand,
#: bits written, why)``. The one known in-script bypass of the store path's callers -- it still passes
#: SetVariableValueInternal, so it is traced as an `eb` row at the RunScriptSync that triggers it.
ENGINE_OPCODE_WRITES = (
    (2209, 0x14, 74, range(3536, 3543),
     "the engine's Oeilvert party hotfix (EventEngine.DoEventCode.cs REQEW: field 2209, Kuja_74) clears "
     "a missing member's bit inside this RunScriptSync"),
)


def instruction_stores(raw: bytes, ins) -> list:
    """Every variable store ``ins`` performs, from walking each expression operand's tokens with the
    engine's CalcStack arities: ``("global", vtype, index)`` for a gEventGlobal var-token lvalue,
    ``("other", source)`` for a Map/Instance/... one, ``("unknown", why)`` for a store whose target is not a
    literal var token (a member-list form, a computed lvalue, an operator the table cannot size)."""
    out: list = []
    for toks in disasm.instr_expr_tokens(raw, ins):
        if toks is None:
            continue
        stack: list = []
        for o, v in toks:
            if o == _EXPR_END:
                break
            if o == _FLEX:                              # u16 id + u8 argc: pops argc, pushes one
                del stack[max(0, len(stack) - v[1]):]
                stack.append(None)
                continue
            if o >= 0xC0:                               # a var token pushes its own var code
                stack.append((o & 3, (o >> 2) & 7, v))
                continue
            if o in _OPERAND_PUSHES:
                stack.append(None)
                continue
            name = EXPR_OP_NAMES.get(o)
            sem = OP_SEMANTICS.get(name)
            if sem is None:
                out.append(("unknown", f"operator 0x{o:02X} has no known arity -- the walk stops there"))
                break
            arity, effect = sem
            if effect == WRITE and name not in _NOT_A_VARIABLE_STORE:
                depth = _LVALUE_DEPTH.get(name)
                lv = stack[-depth] if depth is not None and len(stack) >= depth else None
                if depth is None:
                    out.append(("unknown", f"{name} stores through the member-list walk (putv)"))
                elif lv is None:
                    out.append(("unknown", f"{name}'s lvalue is not a literal variable"))
                elif lv[0] == _GLOBAL:
                    out.append(("global", lv[1], lv[2]))
                else:
                    out.append(("other", lv[0]))
            del stack[max(0, len(stack) - arity):]
            stack.append(None)
    return out


def _matches(store: tuple, row: Row) -> bool:
    return (store[0] == "global" and VAR_TYPE.get(store[1]) == row.width
            and store[2] == (row.bit if row.is_bit else row.byte))


@dataclass(frozen=True)
class Join:
    """Where an ``eb`` row's store is in the script.

    ``status``: ``store`` -- the instruction stores to exactly the row's variable (verified); ``unverified``
    -- it stores, but through a target the kit cannot resolve (see ``reason``); ``engine`` -- a named engine
    write inside a non-store opcode (:data:`ENGINE_OPCODE_WRITES`); ``fail`` -- none of those (``reason``
    says which check broke). ``rel`` is the offset within the function -- the row's key."""

    status: str
    reason: str = ""
    entry: int = -1
    tag: int = -1
    func: int = -1
    rel: int = -1
    text: str = ""
    name: str = ""
    census: bool = False

    @property
    def ok(self) -> bool:
        return self.status != "fail"


class ScriptIndex:
    """One field ``.eb`` indexed for joining trace rows: the engine's function-table rule, per-function
    decodes, eb-src instruction text, logic-map routine names and the census's own write-site population
    -- each built lazily, once."""

    def __init__(self, data: bytes, *, field_id: int | None = None, label: str = ""):
        self.data = bytes(data)
        self.eb = EbScript.from_bytes(self.data)
        self.field_id = field_id
        self.label = label or (f"field {field_id}" if field_id is not None else "script")
        self._decoded: dict = {}
        self._texts: dict = {}
        self._census: dict = {}
        self._names: dict | None = None
        self._joins: dict = {}

    # -- the function table ------------------------------------------------------------------
    def function_at(self, sid: int, ip: int):
        """``(entry, func, start, end)`` holding entry-relative ``ip`` by the engine's rule
        (``StoryTrace.TagAt``: the LARGEST function start at or below ip, first in table order on a tie;
        a start is ``2 + fpos``), or a string saying why there is none."""
        if not 0 <= sid < len(self.eb.entries):
            return f"sid {sid} is not an entry of this script ({len(self.eb.entries)} slots)"
        e = self.eb.entries[sid]
        if e.empty:
            return f"entry {sid} is an empty slot in this script"
        if not 0 <= ip < e.size:
            return f"ip {ip} is outside entry {sid} ({e.size} bytes)"
        best = None
        for f in e.funcs:
            if f.abs_start - e.abs_start <= ip and (best is None or f.abs_start > best.abs_start):
                best = f
        if best is None:
            return f"ip {ip} precedes every function of entry {sid} (the function table)"
        return (e, best, best.abs_start, self._end(e, best))

    def _end(self, e, f) -> int:
        later = [g.abs_start for g in e.funcs if g.abs_start > f.abs_start]
        return min(later + [e.abs_end, len(self.data)])

    def function(self, sid: int, tag: int):
        """``(entry, func, start, end)`` of entry ``sid``'s function ``tag`` (first in table order), or None."""
        if not 0 <= sid < len(self.eb.entries) or self.eb.entries[sid].empty:
            return None
        e = self.eb.entries[sid]
        f = e.func_by_tag(tag)
        return None if f is None else (e, f, f.abs_start, self._end(e, f))

    def instrs(self, start: int, end: int) -> list:
        """The decoded instructions of ``[start, end)``; raises ValueError when they do not decode."""
        if (start, end) not in self._decoded:
            try:
                self._decoded[(start, end)] = list(disasm.iter_code(self.data, start, end))
            except IndexError as ex:
                raise ValueError(f"bytes {start}..{end} do not decode ({ex})") from ex
        return self._decoded[(start, end)]

    def text_at(self, start: int, end: int, rel: int) -> str:
        """The instruction at function offset ``rel`` exactly as eb-src prints it (jumps as ``L<n>``)."""
        if (start, end) not in self._texts:
            from .eb import cmdasm
            try:
                texts = {o: t for o, t in cmdasm.disassemble_items(self.data, start, end) if o is not None}
            except Exception:                                # noqa: BLE001 -- text is presentation only
                texts = {}
            self._texts[(start, end)] = texts
        return self._texts[(start, end)].get(rel, "")

    def name_of(self, sid: int, func_index: int, tag: int) -> str:
        """The routine's name as eb-src's comments and logic-map give it (``Field startup``, ``Talk
        handler`` ...), with the raw tag that ``[[logic_edit]]`` keys on."""
        if self._names is None:
            from . import logic_map
            self._names = {}
            try:
                lm = logic_map.build_logic_map(self.data)
                per: dict = {}
                for n in lm.nodes:                           # one Node per func, entry-then-func order:
                    per.setdefault(n.entry, []).append(n)    # a POSITIONAL join (ebsrc._Enrichment's rule)
                for ei, ns in per.items():
                    for fi, n in enumerate(ns):
                        self._names[(ei, fi)] = logic_map.kind_label(n.kind)
            except Exception:                                # noqa: BLE001 -- names are presentation only
                pass
        label = self._names.get((sid, func_index))
        return f"{label} (tag {tag})" if label else f"tag {tag}"

    def census_sites(self, sid: int, func_index: int) -> set:
        """``{(abs_off, vtype, index)}``: the function's gEventGlobal write sites exactly as the rung-0
        census counts them (``research/dominance_census.py``: ``FuncFlow.iter_sets`` over reachable blocks,
        a ``SET`` assignment's lead variable, source Global). A degraded function contributes none."""
        key = (sid, func_index)
        if key not in self._census:
            from .eb.cfg import CfgError, FuncFlow
            f = self.eb.entries[sid].funcs[func_index]
            sites: set = set()
            try:
                fl = FuncFlow.build(self.data, f.abs_start, f.abs_end)
                for st, _blk in fl.iter_sets(self.data):
                    if st.kind == "assign" and st.source == _GLOBAL:
                        sites.add((st.off, st.vtype, st.index))
            except (CfgError, IndexError, ValueError):
                pass
            self._census[key] = sites
        return self._census[key]

    # -- the join ------------------------------------------------------------------------------
    def join(self, row: Row, *, donor: int | None = None) -> Join:
        """Join one ``eb``/``add 0`` ``w`` row (or ``c`` row) to its store. ``donor`` = the row's donor id,
        for the named engine writes. Cached per site and target."""
        ck = (row.sid, row.ip, row.tag, row.width, row.byte, row.bit, donor)
        if ck not in self._joins:
            self._joins[ck] = self._join(row, donor)
        return self._joins[ck]

    def _join(self, row: Row, donor) -> Join:
        if row.src != "eb" or row.add:
            raise ValueError("only a script row outside an addition buffer joins a script position")
        if row.ip < 0:
            return Join("fail", "no opcode latch: the store ran outside an opcode this object started")
        at = self.function_at(row.sid, row.ip)
        if isinstance(at, str):
            return Join("fail", at)
        e, f, start, end = at
        if f.tag != row.tag:
            return Join("fail", f"the function table puts ip {row.ip} in tag {f.tag}, the row says tag "
                                f"{row.tag} -- the engine ran different bytes", e.index, f.tag, f.index)
        off = e.abs_start + row.ip
        rel = off - start
        try:
            ins = next((i for i in self.instrs(start, end) if i.off == off), None)
        except ValueError as ex:
            return Join("fail", f"tag {f.tag} does not decode: {ex}", e.index, f.tag, f.index, rel)
        base = dict(entry=e.index, tag=f.tag, func=f.index, rel=rel,
                    name=self.name_of(e.index, f.index, f.tag))
        if ins is None:
            return Join("fail", f"+{rel} is not an instruction boundary of tag {f.tag}", **base)
        base["text"] = self.text_at(start, end, rel) or str(ins)
        try:
            stores = instruction_stores(self.data, ins)
        except ValueError as ex:
            return Join("fail", f"the operands do not decode: {ex}", **base)
        hit = next((s for s in stores if _matches(s, row)), None)
        if hit is not None:
            return Join("store", **base,
                        census=(off, hit[1], hit[2]) in self.census_sites(e.index, f.index))
        unknown = [s[1] for s in stores if s[0] == "unknown"]
        if unknown:
            return Join("unverified", unknown[0], **base)
        for fld, op, tag, bits, why in ENGINE_OPCODE_WRITES:
            if donor == fld and ins.op == op and ins.imm(2) == tag and row.is_bit and row.bit in bits:
                return Join("engine", why, **base)
        if stores:
            said = ", ".join(f"Global.{VAR_TYPE[s[1]]}[{s[2]}]" if s[0] == "global" else "a non-Global var"
                             for s in stores)
            return Join("fail", f"this instruction stores to {said}, not {row.target}", **base)
        return Join("fail", "this instruction is not a store", **base)

    # -- fork alignment --------------------------------------------------------------------------
    def skeleton(self, start: int, end: int) -> list:
        """``[(opcode, length), ...]`` of a byte range -- the shape an operand remap cannot change."""
        return [(i.op, i.length) for i in self.instrs(start, end)]


def align_function(fork: ScriptIndex, donor: ScriptIndex, sid: int, tag: int):
    """How many bytes the fork PREPENDED to entry ``sid``'s function ``tag``: the ``delta`` with the donor's
    body the fork body's suffix, instruction for instruction (opcode + length -- a same-length operand
    remap like a verbatim fork's ``Field()`` targets still aligns). None when the donor has no such
    function or the suffix does not match (the fork rewrote it: its rows are the fork's own)."""
    fa, da = fork.function(sid, tag), donor.function(sid, tag)
    if fa is None or da is None:
        return None
    _fe, _ff, fs, fend = fa
    _de, _df, ds, dend = da
    delta = (fend - fs) - (dend - ds)
    if delta < 0:
        return None
    if fork.data[fs + delta:fend] == donor.data[ds:dend]:
        return delta
    try:
        return delta if fork.skeleton(fs + delta, fend) == donor.skeleton(ds, dend) else None
    except ValueError:
        return None


# ================================================================== one run, digested
@dataclass(frozen=True)
class WriteKey:
    """What a run is compared on: ``(donor, mode, src, sid, tag, offset within the donor's function,
    variable, value)``. ``off`` < 0 is inside a fork's prepend; ``aligned`` False = a fork function no donor
    function aligns with (both can only ever be FORK ONLY). Battle/world rows keep the engine's own
    ``ip`` as ``off`` (no field join); addition-buffer rows ``tag`` -1; ``cs`` rows no position at all."""

    donor: int
    m: int
    src: str
    sid: int
    tag: int
    off: int
    target: str
    value: int
    aligned: bool = True

    def sort_key(self) -> tuple:
        return (self.donor, self.m, self.src, self.sid, self.tag, not self.aligned, self.off,
                self.target, self.value)


@dataclass
class Seam:
    """One crossing out of the fork's members into the real game: the run stood in ``frm`` (a member; its
    donor ``donor``) and its next row was in real field ``to``. ``frame``/``line`` are that first seam row's;
    ``exit`` is the last row the run wrote in ``frm`` before it (normally the exit's own ``Int16[2] :=
    entrance``), ``exit_where`` that row's place in the script. ``fields``: every real field the trace saw across
    it, in order, until the run stood in a member again."""

    frm: int
    donor: int | None
    to: int
    frame: int
    line: int
    exit: Row | None = None
    exit_where: str = ""
    fields: list = dfield(default_factory=list)

    @property
    def source(self) -> str:
        """``member(350)`` -- the member by its donor; the plain field when the run crossed from a non-member."""
        return f"member({self.donor})" if self.donor is not None else f"field {self.frm}"

    @property
    def origin(self) -> str:
        """``member(350) [fork 30838]``."""
        return self.source + (f" [fork {self.frm}]" if self.donor is not None else "")


@dataclass
class Observed:
    """A key as first seen in a run: its join (None off the field join) and why the census cannot see it.
    ``at`` is the line that first evidenced it -- the row's own, or for a site's last SUPPRESSED value
    (``counted``) the `c` row's at the epoch's close: the file's line order is the engine's emission order.
    ``changed``: ``{byte: (old, new, line)}``, the first change each byte of a multi-byte store showed over
    EVERY emitted row of the key (a suppressed value has no old). ``seam``: the crossing a seam key was
    written across."""

    key: WriteKey
    row: Row
    join: Join | None = None
    gap: str = ""
    where: str = ""
    at: int = 0
    counted: bool = False
    changed: dict = dfield(default_factory=dict)
    seam: Seam | None = None


@dataclass
class RunDigest:
    """One run, reduced: its story writes as keys, plus everything that is NOT a key, counted and kept."""

    label: str
    epochs: list
    keys: dict = dfield(default_factory=dict)             # WriteKey -> Observed
    masked: Counter = dfield(default_factory=Counter)     # story-noise region name -> rows
    harness: int = 0                                      # the driver's own pokes (the seed)
    failures: list = dfield(default_factory=list)         # (Row, reason) -- JOIN FAILURES
    residue: dict = dfield(default_factory=dict)          # byte -> [Row, ...] (unmasked)
    residue_masked: int = 0
    notes: list = dfield(default_factory=list)
    incomplete: str = ""                                  # why the run has no `off`; "" = it closed
    members: dict = dfield(default_factory=dict)          # {fork id: donor id} -- the fork side's chain
    mismatched: dict = dfield(default_factory=dict)       # {member: the donor its rows name}, when not the set's
    seams: list = dfield(default_factory=list)            # [Seam] in the order the run crossed
    seam_keys: dict = dfield(default_factory=dict)        # WriteKey -> Observed, written across a seam
    stores: dict = dfield(default_factory=dict)           # (byte, width) -> {target} every store site's


def digest(label: str, rows, *, scripts, donor_scripts=None, donors=None, members=None) -> RunDigest:
    """Reduce ONE run's rows (:func:`split_runs`) to its comparable story writes.

    ``scripts(field_id)`` -> the :class:`ScriptIndex` this side's game RAN for that field (the install's
    bytes on the stock side; the mod folder's on the fork side), or None. ``donor_scripts(donor_id)`` -> the
    donor's stock script, to align a fork's function offsets (default: ``scripts``). ``donors`` overrides
    ``{fork field: donor}`` for an engine with no ForkDonorPatch row (every row then says ``don == fld``).

    ``members`` = ``{fork id: donor id}``, the FORK side's chain: its rows in a real non-member field after
    the run first stood in a member go to :attr:`RunDigest.seam_keys` (never :attr:`RunDigest.keys`), each
    under the :class:`Seam` that led there. A member's donor also keys its rows when ``donors`` does not name
    it; a member whose rows carry another donor (or none) is noted.

    A run that never reached its ``off`` is still digested, and says so in :attr:`RunDigest.incomplete`: a
    tracer that faulted writes no ``off`` (``StoryTrace.Fail``), and every key after the cut would otherwise
    read as "never written" -- the false STOCK ONLY / empty STOCK ONLY this instrument must not give."""
    runs = split_runs(rows)
    if len(runs) != 1:
        raise TraceError(f"{label}: {len(runs)} traced runs where one was given -- split_runs() them"
                         if runs else f"{label}: no traced run (no `arm` epoch)")
    members = dict(members or {})
    d = RunDigest(label, epochs(runs[0]), members=members)
    if d.epochs[-1].closed_by is None:
        d.incomplete = (f"the trace ends inside its {d.epochs[-1].why!r} epoch with no `off` -- the tracer "
                        f"faulted (state.json storytrace.error), the game died, a second `storytrace 1` "
                        f"restarted it, or the file was taken before `storytrace 0` landed. Every write "
                        f"after the cut reads as absent")
    ctx = _Ctx(scripts, donor_scripts or scripts, {**members, **(donors or {})})
    across = _walk_seams(d, runs[0]) if members else {}
    for ep in d.epochs:
        for r in ep.residue:
            if noise_regions(r):
                d.residue_masked += 1
            else:
                d.residue.setdefault(r.byte, []).append(r)
        for site in ep.sites.values():
            first = site.rows[0]
            if first.src == "harness":
                d.harness += len(site.rows) + site.suppressed
                continue
            d.stores.setdefault((first.byte, first.width), set()).add(first.target)
            regions = noise_regions(first)
            if regions:
                for name in regions:
                    d.masked[name] += len(site.rows) + site.suppressed
                continue
            for r in site.rows:
                _observe(d, ctx, r, r.new, seam=across.get(id(r)))
            if site.suppressed:
                # the counted stores ran after the site's first row: they sit where its LAST emitted one did
                _observe(d, ctx, first, site.last, counted_at=site.counted_at, seam=across.get(id(site.rows[-1])))
    for s in d.seams:
        if s.exit is not None:
            got = _locate(d, ctx, s.exit, s.exit.new, record=False)
            s.exit_where = got[3] if got else f"e{s.exit.sid} tag {s.exit.tag} ip {s.exit.ip}"
    return d


def real_field(fid: int) -> bool:
    """A field of the game's own table (``extract.ID_TO_EVT``) -- where a fork run is in the real game."""
    from .extract import ID_TO_EVT
    return fid in ID_TO_EVT


def _walk_seams(d: RunDigest, run) -> dict:
    """Walk ONE run in the engine's order and mark its seam rows: ``{id(w row): Seam}``. Places come from
    every row but ``c`` (a count row carries its SITE's field, at the epoch's close). A row in a real field
    that is not a member, once the run has stood in a member, is across a seam; the run is back when it
    stands in a member again. Also notes each member whose rows name a donor other than the member set's."""
    members = d.members
    out: dict = {}
    inside = False                  # the run has stood in a member
    here = None                     # the field of the last placed row
    last_w = None                   # the last `w` row of the current field visit
    cur: Seam | None = None         # the crossing the run is across
    said: set = set()
    for r in run:
        if r.k == "c":
            continue
        if r.fld != here:
            if r.fld in members:
                inside, cur = True, None
            elif inside and real_field(r.fld):
                if cur is None:
                    exit_row = last_w if here in members else None
                    cur = Seam(here, members.get(here), r.fld, r.f, r.line, exit_row)
                    d.seams.append(cur)
                if r.fld not in cur.fields:
                    cur.fields.append(r.fld)
            else:
                cur = None          # a custom non-member (a hub) is the fork's own ground, not a seam
            here, last_w = r.fld, None
        if r.k != "w":
            continue
        last_w = r
        if cur is not None:
            out[id(r)] = cur
        elif r.fld in members and r.don != members[r.fld] and r.fld not in said:
            said.add(r.fld)
            d.mismatched[r.fld] = r.don
            d.notes.append(f"member {r.fld}: its rows name donor {r.don}"
                           + (" (no ForkDonorPatch row)" if r.don == r.fld else "")
                           + f", the member set says {members[r.fld]}")
    return out


class _Ctx:
    """A digest's script resolvers plus its per-function alignment memo."""

    def __init__(self, scripts, donor_scripts, donors):
        self.scripts, self.donor_scripts, self.donors = scripts, donor_scripts, donors
        self._delta: dict = {}

    def delta(self, ran: ScriptIndex, fld: int, donor: int, sid: int, tag: int):
        """The prefix the side's script adds to (sid, tag) over the donor's stock script: 0 when the bytes
        are the donor's own, None when nothing aligns (or there is no donor script) -- memoized."""
        k = (fld, donor, sid, tag)
        if k not in self._delta:
            base = self.donor_scripts(donor)
            if base is None:
                self._delta[k] = None
            elif base is ran or base.data == ran.data:
                self._delta[k] = 0
            else:
                self._delta[k] = align_function(ran, base, sid, tag)
        return self._delta[k]


def _locate(d: RunDigest, ctx: _Ctx, r: Row, value: int, *, record: bool = True):
    """``(key, join, gap, where)`` for one store and the value it left -- or None when a field row does not
    join (recorded once in :attr:`RunDigest.failures`, with the run's notes, unless ``record`` is False: a
    place asked only to NAME a row)."""
    donor = ctx.donors.get(r.fld, r.don)
    if r.src == "cs":
        return (WriteKey(donor, r.m, "cs", -1, -1, -1, r.target, value), None,
                "a C# writer through setVarManually -- no script position", "C#")
    if r.m != FIELD_MODE:
        return (WriteKey(donor, r.m, "eb", r.sid, r.tag, r.ip, r.target, value), None,
                f"a mode-{r.m} (battle/world) script -- the census reads field scripts only",
                f"mode {r.m} sid {r.sid} tag {r.tag} ip {r.ip}")
    if r.add:
        return (WriteKey(donor, r.m, "eb", r.sid, -1, r.ip, r.target, value), None,
                "an addition buffer (movQData/neckTurnData): ip indexes the buffer",
                f"e{r.sid} addition buffer ip {r.ip}")
    ran = ctx.scripts(r.fld)
    j = ran.join(r, donor=donor) if ran is not None else Join("fail", f"no .eb for field {r.fld} on this side")
    if not j.ok:
        if record and not any(fr is r for fr, _why in d.failures):  # a site's `last` re-joins its first row
            d.failures.append((r, j.reason))
        return None
    delta = ctx.delta(ran, r.fld, donor, r.sid, r.tag)
    ok = delta is not None
    off = j.rel - delta if ok else j.rel
    note = f"no stock .eb for donor {donor}: field {r.fld}'s rows stay unaligned"
    if record and ctx.donor_scripts(donor) is None and note not in d.notes:
        d.notes.append(note)
    key = WriteKey(donor, r.m, "eb", r.sid, r.tag, off, r.target, value, ok)
    if j.status == "store":
        gap = "" if j.census else "a store the census does not count (unreachable per the CFG, not the " \
                                  "statement's lead variable, or not a SET)"
    else:
        gap = j.reason
    where = f"e{r.sid} {j.name} {off:+d}" + ("" if ok else f" [fork {r.fld} +{j.rel}, no donor function aligns]")
    if ok and off < 0:
        where += " [the fork's prepend]"
    return key, j, gap, where


def _observe(d: RunDigest, ctx: _Ctx, r: Row, value: int, *, counted_at: int = 0, seam: Seam | None = None) -> None:
    """Key one store (a seam row into :attr:`RunDigest.seam_keys`, never :attr:`RunDigest.keys`)."""
    got = _locate(d, ctx, r, value)
    if got is None:
        return
    key, j, gap, where = got
    keys = d.seam_keys if seam is not None else d.keys
    o = keys.get(key)
    if o is None:
        o = keys[key] = Observed(key, r, j, gap, where, at=counted_at or r.line, counted=bool(counted_at),
                                 seam=seam)
    if not counted_at:                                   # a suppressed value has no old: no byte to compare
        for b, (old, new) in r.byte_changes().items():
            o.changed.setdefault(b, (old, new, r.line))


# ================================================================== N stock runs vs N fork runs
@dataclass
class Clobber:
    """A fork store that changed ``byte`` -- a byte of its span OUTSIDE the variable stock writes at its start
    -- from ``old`` to ``new`` (the first run that showed it: ``label`` line ``line``), in ``runs`` fork runs.
    ``why`` is the stock evidence (what the stock runs store at the start byte, and at the clobbered one)."""

    key: WriteKey
    seen: Observed
    byte: int
    old: int
    new: int
    runs: int
    label: str
    line: int
    why: str


@dataclass
class PreEmpted:
    """A value the fork's PREPEND stamps (``stamps``: its FORK ONLY keys at a negative offset, one per member
    donor that runs the prepend) that every stock run writes itself: ``stock`` = ``{stock key: stock runs}``,
    each store of the same (variable, value) at its own site -- one key in every run, or (the controller's
    flip, in whichever room its count ran out) a different one per run."""

    target: str
    value: int
    stamps: list
    stock: Counter


def writers(runs) -> dict:
    """``{(target, value): Counter({donor: runs})}``: every donor that wrote each (variable, value) in the
    runs, counted once per run -- ``("Global.Bit[2102]", 1): {450: 3}`` says, with no script read, that only
    field 450 ever sets the Dali ping."""
    out: dict = {}
    for d in runs:
        for target, value, donor in {(k.target, k.value, k.donor) for k in d.keys}:
            out.setdefault((target, value), Counter())[donor] += 1
    return out


def stock_layout(runs) -> dict:
    """``{(start byte, width): {target}}`` -- every variable the runs stored through (masked sites included,
    the driver's pokes not): how wide the real game writes each byte."""
    out: dict = {}
    for d in runs:
        for site, targets in d.stores.items():
            out.setdefault(site, set()).update(targets)
    return out


def _names(layout: dict, sites) -> str:
    names = sorted({t for s in sites for t in layout[s]})
    return ", ".join(names[:3]) + (f" (+{len(names) - 3} more)" if len(names) > 3 else "")


def outside_target(layout: dict, start: int, byte: int) -> str:
    """Why ``byte`` lies outside the variable a store at ``start`` is meant to write, by the stock evidence
    in ``layout`` (:func:`stock_layout`) -- or "" when the evidence does not say so (no claim without it).
    Outside = stock stores ``start`` only through variables that end before ``byte``, or stores ``byte`` only
    through variables that do not start at ``start`` (it is another variable's)."""
    here = [(s, w) for s, w in layout if s <= byte < s + WIDTH_BYTES[w]]
    at = [(s, w) for s, w in layout if s == start]
    parts = []
    if here and all(s != start for s, _w in here):
        parts.append(f"byte {byte} as {_names(layout, here)}")
    if at and byte >= start + max(WIDTH_BYTES[w] for _s, w in at):
        parts.append(f"byte {start} only as {_names(layout, at)}")
    return "the stock runs store " + ", and ".join(parts) if parts else ""


def find_clobbers(stock, fork) -> list:
    """Every NEIGHBOUR-BYTE CLOBBER on the fork side (never across a seam: that is the real game's own
    store) -- a multi-byte store's changed byte, other than its start, that :func:`outside_target` places
    outside its variable. One per (key, byte), counted over the fork runs that showed it."""
    layout = stock_layout(stock)
    found: dict = {}
    for d in fork:
        for k, o in d.keys.items():
            for b, (old, new, line) in sorted(o.changed.items()):
                if b == o.row.byte:
                    continue
                why = outside_target(layout, o.row.byte, b)
                if not why:
                    continue
                got = found.get((k, b))
                if got is None:
                    found[(k, b)] = Clobber(k, o, b, old, new, 1, d.label, line, why)
                else:
                    got.runs += 1
    return sorted(found.values(), key=lambda c: (c.key.sort_key(), c.byte))


@dataclass
class Comparison:
    """The set difference (PLAN.md "The deliverable"): per key, in how many runs of each side it appears.
    With a member set, the fork side's counts are its MEMBER keys; its seam keys count apart
    (``seam_counts``), so a key the fork reached only by leaving its members never matches."""

    stock: list
    fork: list
    counts: dict = dfield(default_factory=dict)           # WriteKey -> (stock runs, fork runs)
    seen: dict = dfield(default_factory=dict)             # WriteKey -> Observed (either side)
    members: dict = dfield(default_factory=dict)          # the fork side's {fork id: donor id}
    seam_counts: dict = dfield(default_factory=dict)      # WriteKey -> fork runs that wrote it across a seam
    seam_seen: dict = dfield(default_factory=dict)        # WriteKey -> Observed (the first fork seam run's)
    clobbers: list = dfield(default_factory=list)         # [Clobber]

    def _cat(self, pred) -> list:
        """The keys whose ``(stock runs, fork runs, stock N, fork N)`` satisfy ``pred``, in report order."""
        ns, nf = len(self.stock), len(self.fork)
        return sorted((k for k, (s, f) in self.counts.items() if pred(s, f, ns, nf)), key=WriteKey.sort_key)

    @property
    def stock_only(self) -> list:
        """In EVERY stock run and no fork run -- what the fork never reaches (rung 2: must be empty). With a
        member set: reached by no member AND not across any seam either (those are :attr:`across_seam`)."""
        return [k for k in self._cat(lambda s, f, ns, nf: s == ns and f == 0) if not self.seam_counts.get(k)]

    @property
    def across_seam(self) -> list:
        """In EVERY stock run, written by no fork member, and written across a seam in some fork run: the
        stock key the fork side reached only by leaving its members (Dali's ping, when 450 is no member)."""
        return [k for k in self._cat(lambda s, f, ns, nf: s == ns and f == 0) if self.seam_counts.get(k)]

    @property
    def seam_only(self) -> list:
        """Written across a seam and nowhere else -- by no stock run and no fork member: the real game's own
        writes in a state no stock run reached."""
        return sorted((k for k in self.seam_counts if k not in self.counts), key=WriteKey.sort_key)

    @property
    def seams(self) -> list:
        """``[(Seam, [run label, ...])]``: each crossing (member -> real field) once, with the fork runs that
        made it, in the order first made."""
        out: dict = {}
        for d in self.fork:
            for s in d.seams:
                out.setdefault((s.frm, s.to), (s, []))[1].append(d.label)
        return list(out.values())

    @property
    def writers(self) -> dict:
        """:func:`writers` over the stock runs."""
        return writers(self.stock)

    @property
    def fork_only(self) -> list:
        return self._cat(lambda s, f, ns, nf: f == nf and s == 0)

    @property
    def pre_empted(self) -> list:
        """``[PreEmpted]``: each (variable, value) a FORK ONLY prepend key stamps (``off`` < 0, aligned) that
        EVERY stock run writes itself at a site of its own -- the seed doing the story's work before the story
        does. In variable order."""
        stamps: dict = {}
        for k in self.fork_only:
            if k.off < 0 and k.aligned:
                stamps.setdefault((k.target, k.value), []).append(k)
        out = []
        for (target, value), ks in sorted(stamps.items(), key=lambda tv: (_target_order(tv[0][0]), tv[0])):
            own = [{k for k in d.keys if (k.target, k.value, k.src) == (target, value, "eb") and k.off >= 0}
                   for d in self.stock]
            if self.stock and all(own):
                out.append(PreEmpted(target, value, ks, Counter(k for keys in own for k in keys)))
        return out

    @property
    def unstable(self) -> list:
        """In some but not all runs of a side -- run-to-run drift, not a stock/fork difference."""
        return self._cat(lambda s, f, ns, nf: 0 < s < ns or 0 < f < nf)

    @property
    def matched(self) -> list:
        return self._cat(lambda s, f, ns, nf: s == ns and f == nf)

    @property
    def census_gaps(self) -> list:
        return sorted((k for k, o in self.seen.items() if o.gap), key=WriteKey.sort_key)

    @property
    def incomplete(self) -> list:
        """The runs (either side) that never reached their ``off``: while any is listed, a key it did not
        reach may simply lie past its cut -- STOCK ONLY / FORK ONLY / UNSTABLE are not evidence."""
        return [d for d in self.stock + self.fork if d.incomplete]

    @property
    def residue(self) -> dict:
        """``{byte: (stock runs, fork runs)}`` for every byte with unmasked residue on either side."""
        out: dict = {}
        for side, runs in ((0, self.stock), (1, self.fork)):
            for d in runs:
                for b in d.residue:
                    c = out.setdefault(b, [0, 0])
                    c[side] += 1
        return {b: tuple(c) for b, c in sorted(out.items())}


def compare(stock, fork, *, members=None) -> Comparison:
    """Compare digested runs as SETS: logic ticks per frame vary and randomness is unseeded, so an ordered
    diff would report noise -- a key present in every run of one side and none of the other is the signal.

    ``members`` = the fork side's ``{fork id: donor id}``. The seam is cut where the rows are in the engine's
    order, in :func:`digest` -- so every fork run must have been digested with this same member set, and no
    stock run with any: a comparison that claims a member set over runs digested without one would merge
    the seam rows it exists to keep apart."""
    members = dict(members or {})
    for d in stock:
        if d.members:
            raise TraceError(f"{d.label}: a stock run digested with a member set -- the members are the "
                             f"fork side's chain; the stock side is the real game")
    for d in fork:
        if d.members != members:
            raise TraceError(f"{d.label}: digested with member set {d.members or 'none'}, compared with "
                             f"{members or 'none'} -- digest every fork run with the member set compare() gets")
    c = Comparison(list(stock), list(fork), members=members)
    for side, runs in ((0, c.stock), (1, c.fork)):
        for d in runs:
            for k, o in d.keys.items():
                n = c.counts.setdefault(k, [0, 0])
                n[side] += 1
                c.seen.setdefault(k, o)
    c.counts = {k: tuple(v) for k, v in c.counts.items()}
    for d in c.fork:
        for k, o in d.seam_keys.items():
            c.seam_counts[k] = c.seam_counts.get(k, 0) + 1
            c.seam_seen.setdefault(k, o)
    c.clobbers = find_clobbers(c.stock, c.fork)
    return c


# ================================================================== the plain-text report
def _key_line(k: WriteKey, o: Observed, tail: str = "", lead: str = "") -> str:
    text = f"   {o.join.text}" if o.join is not None and o.join.text else ""
    return f"  {lead}{k.donor} {o.where}  {k.target} = {k.value}{text}{tail}"


def _incomplete_banner(runs, consequence: str) -> list:
    """The one line a reader cannot miss, then each cut run and why -- empty when every run closed."""
    cut = [d for d in runs if d.incomplete]
    if not cut:
        return []
    return ([f"!! {len(cut)} run(s) INCOMPLETE -- {consequence}"]
            + [f"  {d.label}: {d.incomplete}" for d in cut])


def _run_header(d: RunDigest) -> list:
    whys = ", ".join(ep.why + ("" if ep.closed_by else " (open)") for ep in d.epochs) or "none"
    rows = sum(len(ep.writes) for ep in d.epochs)
    supp = sum(s.suppressed for ep in d.epochs for s in ep.sites.values())
    seam = (f", {len(d.seam_keys)} across {len(d.seams)} seam crossing(s)" if d.members else "")
    return [f"  {d.label}: {len(d.epochs)} epoch(s) [{whys}], {rows} write rows (+{supp} suppressed), "
            f"{len(d.keys)} story keys{seam}"]


def _target_order(target: str) -> tuple:
    """``Global.Bit[2102]`` -> (262, 2102): the byte a variable starts at, then its own index."""
    idx = int(target[target.index("[") + 1:-1])
    return ((idx >> 3) if target[len("Global."):target.index("[")] in BIT_WIDTHS else idx, idx)


def _writers_section(runs, pairs, note: str, donors=None) -> list:
    """``Global.Bit[2102] := 1 <- {450}`` per (target, value); a donor in fewer than all the runs says in
    how many. ``donors`` = the member set's donors: a value none of them writes is listed FIRST and says so
    -- the stock field the chain would need, named with no script read."""
    pairs = list(dict.fromkeys(pairs))
    index, ns = writers(runs), len(runs)
    outside = [] if donors is None else [tv for tv in pairs if not set(index.get(tv, ())) & set(donors)]
    head = f"WRITERS ({len(pairs)}" + (f"; {len(outside)} written only outside the members" if outside else "")
    out = ["", f"{head}) -- {note}"]
    for tv in outside + [tv for tv in pairs if tv not in outside]:
        who = index.get(tv, Counter())
        names = ", ".join(f"{don}" + ("" if n == ns else f" ({n}/{ns})") for don, n in sorted(who.items()))
        out.append(f"  {tv[0]} := {tv[1]} <- {{{names}}}" + ("   -- no member's donor writes it"
                                                              if tv in outside else ""))
    return out


def _reached(o: Observed) -> str:
    """The plain words for a seam key: ``450 reached only across a seam from member(350)`` (``the real 350
    ... into 450`` for a field beyond the crossing)."""
    s = o.seam
    if o.row.fld == s.to:
        return f"{s.to} reached only across a seam from {s.source}"
    return f"the real {o.row.fld} reached only across a seam from {s.source} into {s.to}"


def _side_notes(runs, side: str) -> list:
    out = []
    masked = Counter()
    for d in runs:
        masked.update(d.masked)
    if masked:
        out.append(f"  {side} masked (story noise, flags.story_noise_bits): "
                   + ", ".join(f"{n} {c}" for n, c in sorted(masked.items())))
    res_masked = sum(d.residue_masked for d in runs)
    if res_masked:
        out.append(f"  {side} masked residue (whole noise bytes): {res_masked} rows")
    harness = sum(d.harness for d in runs)
    if harness:
        out.append(f"  {side} harness pokes (the seed, never compared): {harness} rows")
    for d in runs:
        out += [f"  {d.label}: {note}" for note in d.notes]
    return out


def _failures(runs) -> list:
    out = []
    for d in runs:
        for r, why in d.failures:
            out.append(f"  {d.label} line {r.line}: field {r.fld} e{r.sid} tag {r.tag} ip {r.ip} "
                       f"{r.target} = {r.new} -- {why}")
    return out


def report(c: Comparison, *, title: str = "", writers: bool = False) -> str:
    """The comparison as plain text: STOCK ONLY, FORK ONLY, UNSTABLE, RESIDUE, CENSUS GAPS, JOIN FAILURES.

    With a member set, also SEAMS (each crossing into the real game), REACHED ONLY ACROSS A SEAM, SEAM ONLY,
    and the WRITERS of every stock value the fork's members never wrote. NEIGHBOUR-BYTE CLOBBERS whenever
    one is found (FORK ONLY flags its own), and PRE-EMPTED whenever the prepend stamps a value stock writes
    itself. ``writers`` = the WRITERS of EVERY stock value (with a member set, a value no member's donor writes
    still first and marked). With none of these, the report is the one rung 2 read."""
    ns, nf = len(c.stock), len(c.fork)
    lines = [title or f"story trace: stock x{ns} vs fork x{nf}"]
    lines += _incomplete_banner(c.stock + c.fork, "a key such a run never reached may lie past its cut, so "
                                                  "STOCK ONLY / FORK ONLY / UNSTABLE below are not evidence")
    for d in c.stock:
        lines += _run_header(d)
    for d in c.fork:
        lines += _run_header(d)
    lines += _side_notes(c.stock, "stock") + _side_notes(c.fork, "fork")
    lines.append(f"  matched in every run of both sides: {len(c.matched)} key(s)"
                 + (" (fork MEMBERS only: a row across a seam never matches)" if c.members else ""))
    clobbered: dict = {}
    for cl in c.clobbers:
        clobbered.setdefault(cl.key, []).append(cl)

    def section(name, keys, tail=lambda k: "", note="", seen=None):
        lines.append("")
        lines.append(f"{name} ({len(keys)})" + (f" -- {note}" if note else ""))
        for k in keys:
            lines.append(_key_line(k, (c.seen if seen is None else seen)[k], tail(k)))

    section("STOCK ONLY", c.stock_only, note=f"in {ns}/{ns} stock runs, 0/{nf} fork runs")
    section("FORK ONLY", c.fork_only, note=f"in 0/{ns} stock runs, {nf}/{nf} fork runs",
            tail=lambda k: "".join(f"   !! NEIGHBOUR-BYTE CLOBBER: byte {cl.byte} {cl.old} -> {cl.new}"
                                   for cl in clobbered.get(k, ())))
    section("UNSTABLE", c.unstable, lambda k: f"   stock {c.counts[k][0]}/{ns} fork {c.counts[k][1]}/{nf}")
    if c.members:
        seams = c.seams
        lines.append("")
        lines.append(f"SEAMS ({len(seams)}) -- a fork run left its members into the real game; every row from "
                     f"there is the real game's own, kept apart from the keys above")
        for s, labels in seams:
            after = (f"; the member's last write before it: {s.exit_where}  {s.exit.target} = {s.exit.new}"
                     if s.exit is not None else "")
            lines.append(f"  {s.origin} -> real {s.to}: {len(labels)}/{nf} fork runs; first seam row at frame "
                         f"{s.frame} ({labels[0]} line {s.line}){after}")
            lines.append(f"    real fields seen across it: {', '.join(map(str, s.fields))}")
        section("REACHED ONLY ACROSS A SEAM", c.across_seam,
                lambda k: f"   -- {_reached(c.seam_seen[k])}, fork {c.seam_counts[k]}/{nf}",
                note=f"in {ns}/{ns} stock runs, written by no fork member: the fork side wrote them only in a "
                     f"real field it reached across a seam")
        section("SEAM ONLY", c.seam_only,
                lambda k: f"   -- {_reached(c.seam_seen[k])}, fork {c.seam_counts[k]}/{nf}",
                note="the real game's writes across a seam that no stock run and no fork member made",
                seen=c.seam_seen)
    if c.clobbers:
        lines.append("")
        lines.append(f"NEIGHBOUR-BYTE CLOBBERS ({len(c.clobbers)}) -- a fork store changed a byte outside the "
                     f"variable the stock runs write at its start")
        for cl in c.clobbers:
            lines.append(_key_line(cl.key, cl.seen,
                                   f"   changes byte {cl.byte}: {cl.old} -> {cl.new} in {cl.runs}/{nf} fork runs "
                                   f"(first {cl.label} line {cl.line}) -- {cl.why}"))
    pre = c.pre_empted
    if pre:
        lines.append("")
        lines.append(f"PRE-EMPTED ({len(pre)}) -- the fork's prepend stamps a value every stock run writes itself, "
                     f"at its own site: the seed does the story's work before the story does")
        for p in pre:
            donors = sorted({k.donor for k in p.stamps})
            where = ", ".join(f"{k.donor} {c.seen[k].where} ({n}/{ns})"
                              for k, n in sorted(p.stock.items(), key=lambda kn: kn[0].sort_key()))
            lines.append(f"  {p.target} := {p.value}  stamped by the prepend in {len(donors)} donor(s) "
                         f"({', '.join(map(str, donors))}); stock writes it at {where}")
    if writers:
        lines += _writers_section(c.stock, sorted({(k.target, k.value) for d in c.stock for k in d.keys},
                                                  key=lambda tv: (_target_order(tv[0]), tv)),
                                  "every donor that wrote each value in the stock runs",
                                  donors=c.members.values() if c.members else None)
    elif c.members:
        lines += _writers_section(c.stock, [(k.target, k.value) for k in c.stock_only + c.across_seam],
                                  "who wrote each STOCK ONLY / across-seam value in the stock runs",
                                  donors=c.members.values())
    res = c.residue
    lines.append("")
    lines.append(f"RESIDUE ({len(res)} byte(s) changed with no hooked store)")
    for b, (s, f) in res.items():
        word = flagsmod.named_word_at(b * 8)
        lines.append(f"  byte {b}{f' ({word.name})' if word else ''}: stock {s}/{ns} fork {f}/{nf}")
    section("CENSUS GAPS", c.census_gaps,
            lambda k: f"   stock {c.counts[k][0]}/{ns} fork {c.counts[k][1]}/{nf} -- {c.seen[k].gap}")
    fails = _failures(c.stock) + _failures(c.fork)
    lines.append("")
    lines.append(f"JOIN FAILURES ({len(fails)})")
    lines += fails
    return "\n".join(lines) + "\n"


def report_runs(runs, *, title: str = "", writers: bool = False) -> str:
    """One side alone (the rung-0 check): every story key with the instruction it joined to, then the
    census gaps, residue and join failures -- and with ``writers``, every donor that wrote each value.

    WRITES are listed in the ENGINE'S order (the line that first evidenced each key), never re-sorted by
    offset: rung 0 asks whether Main_Init's writes arrive in the script's order, and a list sorted by
    offset would show script order whatever the engine emitted -- a check that cannot fail."""
    lines = [title or f"story trace: {len(runs)} run(s)"]
    lines += _incomplete_banner(runs, "the writes after each cut are missing, not absent")
    for d in runs:
        lines += _run_header(d)
    lines += _side_notes(runs, "runs")
    for d in runs:
        lines.append("")
        lines.append(f"WRITES -- {d.label} ({len(d.keys)}, in the order the engine wrote them)")
        for k, o in sorted(d.keys.items(), key=lambda ko: (ko[1].at, ko[0].sort_key())):
            tail = "   [the site's last suppressed value, counted at the epoch's close]" if o.counted else ""
            lines.append(_key_line(k, o, tail + (f"   -- census gap: {o.gap}" if o.gap else ""),
                                   lead=f"line {o.at}  "))
        lines.append(f"RESIDUE -- {d.label} ({len(d.residue)} byte(s))")
        for b, rs in sorted(d.residue.items()):
            lines.append(f"  byte {b}: {len(rs)} row(s) ({', '.join(sorted({r.why for r in rs}))}), "
                         f"last {rs[-1].old} -> {rs[-1].new}")
    if writers:
        lines += _writers_section(runs, sorted({(k.target, k.value) for d in runs for k in d.keys},
                                               key=lambda tv: (_target_order(tv[0]), tv)),
                                  "every donor that wrote each value in these runs")
    fails = _failures(runs)
    lines.append("")
    lines.append(f"JOIN FAILURES ({len(fails)})")
    lines += fails
    return "\n".join(lines) + "\n"


# ================================================================== where the scripts come from
def stock_script_source(game=None, *, lang: str = "us", explicit=None):
    """``field id -> ScriptIndex | None`` over the install's field event bundle (US by default: the census
    is US bytes and JP differs in 71% of fields -- trace the US build). ``explicit`` = ``{field id: .eb
    bytes}`` answered first; the bundle is opened only for an id it lacks, then cached per id."""
    cache = {fid: ScriptIndex(data, field_id=fid, label=f"stock {fid}") for fid, data in (explicit or {}).items()}
    bundle = None

    def get(fid: int):
        nonlocal bundle
        if fid not in cache:
            if bundle is None:
                from .extract import EventBundle
                bundle = EventBundle(game, lang=lang)
            data = bundle.eb_for_id(fid)
            cache[fid] = ScriptIndex(data, field_id=fid, label=f"stock {fid}") if data else None
        return cache[fid]
    return get


def mod_registrations(root) -> dict:
    """``{field id: EVT name}`` a mod root's DictionaryPatch.txt registers (``FieldScene <id> <area> <mapid>
    <NAME> <block>``, build.py's emitter; the script is ``EVT_<NAME>.eb.bytes``)."""
    try:
        text = (Path(root) / "DictionaryPatch.txt").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    out = {}
    for ln in text.splitlines():
        p = ln.split()
        if len(p) >= 5 and p[0] == "FieldScene" and p[1].isdigit():
            out[int(p[1])] = p[4]
    return out


def mod_script_source(roots, *, fallback=None, lang: str = "us", explicit=None):
    """``field id -> ScriptIndex | None`` for a FORK run: ``explicit`` (``{field id: .eb bytes}``) first,
    then the ``.eb`` a mod root registers for the id, then a root's override of that STOCK field's script
    (:func:`stock_overrides` -- the field-70 New Game hook is one: the fork run RAN it), else ``fallback(id)``
    (the fork run walked into an untouched stock field). Two roots registering one id is the global EventDB
    collision, and two roots overriding one stock script leaves the winner to Memoria.ini's folder order --
    both refused, never resolved by picking one."""
    from .config import ModLayout
    regs = [(Path(r), mod_registrations(r)) for r in roots]
    cache = {fid: ScriptIndex(data, field_id=fid, label=f"fork {fid}") for fid, data in (explicit or {}).items()}

    def get(fid: int):
        if fid not in cache:
            hits = [(root, reg[fid]) for root, reg in regs if fid in reg]
            if len(hits) > 1:
                raise TraceError(f"field {fid} is registered by {len(hits)} mod folders "
                                 f"({', '.join(str(h[0]) for h in hits)}) -- EventDB is global; "
                                 f"name the one that ran with --fork-root")
            over = [] if hits else stock_overrides(fid, [root for root, _reg in regs], lang=lang)
            if len(over) > 1:
                raise TraceError(f"stock field {fid}'s script is overridden by {len(over)} mod folders "
                                 f"({', '.join(map(str, over))}) -- Memoria.ini's folder order picks the one "
                                 f"that ran; name it with --fork-root")
            if hits or over:
                root = hits[0][0] if hits else over[0]
                path = (ModLayout(root).eb_path(lang, f"EVT_{hits[0][1]}.eb.bytes") if hits
                        else _override_path(root, fid, lang))
                try:
                    cache[fid] = ScriptIndex(path.read_bytes(), field_id=fid, label=f"fork {fid} ({path})")
                except OSError as ex:
                    raise TraceError(f"field {fid}: {root} {'registers' if hits else 'overrides'} it but its "
                                     f"script is unreadable ({ex})") from ex
            else:
                cache[fid] = fallback(fid) if fallback else None
        return cache[fid]
    return get


def _override_path(root, fid: int, lang: str):
    """Where mod root ``root`` would ship its own script for STOCK field ``fid`` (None: not a stock id)."""
    from .config import ModLayout
    from .extract import ID_TO_EVT
    evt = ID_TO_EVT.get(int(fid))
    return None if evt is None else ModLayout(Path(root)).eb_path(lang, f"{evt}.eb.bytes")


def stock_overrides(fid: int, roots, *, lang: str = "us") -> list:
    """The mod roots that ship their own ``EVT_<stock name>.eb.bytes`` for stock field ``fid`` -- the game
    then RAN that, not the install's bundle (the field-70 New Game override is exactly this), so a "stock"
    run through ``fid`` did not run stock bytes there."""
    out = []
    for r in roots:
        path = _override_path(r, fid, lang)
        if path is not None and path.is_file():
            out.append(Path(r))
    return out
