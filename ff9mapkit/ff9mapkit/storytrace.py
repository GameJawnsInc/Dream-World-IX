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
class Observed:
    """A key as first seen in a run: its join (None off the field join) and why the census cannot see it.
    ``at`` is the line that first evidenced it -- the row's own, or for a site's last SUPPRESSED value
    (``counted``) the `c` row's at the epoch's close: the file's line order is the engine's emission order."""

    key: WriteKey
    row: Row
    join: Join | None = None
    gap: str = ""
    where: str = ""
    at: int = 0
    counted: bool = False


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


def digest(label: str, rows, *, scripts, donor_scripts=None, donors=None) -> RunDigest:
    """Reduce ONE run's rows (:func:`split_runs`) to its comparable story writes.

    ``scripts(field_id)`` -> the :class:`ScriptIndex` this side's game RAN for that field (the install's
    bytes on the stock side; the mod folder's on the fork side), or None. ``donor_scripts(donor_id)`` -> the
    donor's stock script, to align a fork's function offsets (default: ``scripts``). ``donors`` overrides
    ``{fork field: donor}`` for an engine with no ForkDonorPatch row (every row then says ``don == fld``).

    A run that never reached its ``off`` is still digested, and says so in :attr:`RunDigest.incomplete`: a
    tracer that faulted writes no ``off`` (``StoryTrace.Fail``), and every key after the cut would otherwise
    read as "never written" -- the false STOCK ONLY / empty STOCK ONLY this instrument must not give."""
    runs = split_runs(rows)
    if len(runs) != 1:
        raise TraceError(f"{label}: {len(runs)} traced runs where one was given -- split_runs() them"
                         if runs else f"{label}: no traced run (no `arm` epoch)")
    d = RunDigest(label, epochs(runs[0]))
    if d.epochs[-1].closed_by is None:
        d.incomplete = (f"the trace ends inside its {d.epochs[-1].why!r} epoch with no `off` -- the tracer "
                        f"faulted (state.json storytrace.error), the game died, a second `storytrace 1` "
                        f"restarted it, or the file was taken before `storytrace 0` landed. Every write "
                        f"after the cut reads as absent")
    ctx = _Ctx(scripts, donor_scripts or scripts, donors or {})
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
            regions = noise_regions(first)
            if regions:
                for name in regions:
                    d.masked[name] += len(site.rows) + site.suppressed
                continue
            for r in site.rows:
                _observe(d, ctx, r, r.new)
            if site.suppressed:
                _observe(d, ctx, first, site.last, counted_at=site.counted_at)
    return d


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


def _observe(d: RunDigest, ctx: _Ctx, r: Row, value: int, *, counted_at: int = 0) -> None:
    donor = ctx.donors.get(r.fld, r.don)
    if r.src == "cs":
        key = WriteKey(donor, r.m, "cs", -1, -1, -1, r.target, value)
        _keep(d, key, r, None, "a C# writer through setVarManually -- no script position", "C#", counted_at)
        return
    if r.m != FIELD_MODE:
        key = WriteKey(donor, r.m, "eb", r.sid, r.tag, r.ip, r.target, value)
        _keep(d, key, r, None, f"a mode-{r.m} (battle/world) script -- the census reads field scripts only",
              f"mode {r.m} sid {r.sid} tag {r.tag} ip {r.ip}", counted_at)
        return
    if r.add:
        key = WriteKey(donor, r.m, "eb", r.sid, -1, r.ip, r.target, value)
        _keep(d, key, r, None, "an addition buffer (movQData/neckTurnData): ip indexes the buffer",
              f"e{r.sid} addition buffer ip {r.ip}", counted_at)
        return
    ran = ctx.scripts(r.fld)
    j = ran.join(r, donor=donor) if ran is not None else Join("fail", f"no .eb for field {r.fld} on this side")
    if not j.ok:
        if not any(fr is r for fr, _why in d.failures):  # a site's `last` re-joins its first row
            d.failures.append((r, j.reason))
        return
    delta = ctx.delta(ran, r.fld, donor, r.sid, r.tag)
    ok = delta is not None
    off = j.rel - delta if ok else j.rel
    note = f"no stock .eb for donor {donor}: field {r.fld}'s rows stay unaligned"
    if ctx.donor_scripts(donor) is None and note not in d.notes:
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
    _keep(d, key, r, j, gap, where, counted_at)


def _keep(d: RunDigest, key: WriteKey, row: Row, join, gap: str, where: str, counted_at: int = 0) -> None:
    if key not in d.keys:
        d.keys[key] = Observed(key, row, join, gap, where, at=counted_at or row.line, counted=bool(counted_at))


# ================================================================== N stock runs vs N fork runs
@dataclass
class Comparison:
    """The set difference (PLAN.md "The deliverable"): per key, in how many runs of each side it appears."""

    stock: list
    fork: list
    counts: dict = dfield(default_factory=dict)           # WriteKey -> (stock runs, fork runs)
    seen: dict = dfield(default_factory=dict)             # WriteKey -> Observed (either side)

    def _cat(self, pred) -> list:
        """The keys whose ``(stock runs, fork runs, stock N, fork N)`` satisfy ``pred``, in report order."""
        ns, nf = len(self.stock), len(self.fork)
        return sorted((k for k, (s, f) in self.counts.items() if pred(s, f, ns, nf)), key=WriteKey.sort_key)

    @property
    def stock_only(self) -> list:
        """In EVERY stock run and no fork run -- what the fork never reaches (rung 2: must be empty)."""
        return self._cat(lambda s, f, ns, nf: s == ns and f == 0)

    @property
    def fork_only(self) -> list:
        return self._cat(lambda s, f, ns, nf: f == nf and s == 0)

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


def compare(stock, fork) -> Comparison:
    """Compare digested runs as SETS: logic ticks per frame vary and randomness is unseeded, so an ordered
    diff would report noise -- a key present in every run of one side and none of the other is the signal."""
    c = Comparison(list(stock), list(fork))
    for side, runs in ((0, c.stock), (1, c.fork)):
        for d in runs:
            for k, o in d.keys.items():
                n = c.counts.setdefault(k, [0, 0])
                n[side] += 1
                c.seen.setdefault(k, o)
    c.counts = {k: tuple(v) for k, v in c.counts.items()}
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
    return [f"  {d.label}: {len(d.epochs)} epoch(s) [{whys}], {rows} write rows (+{supp} suppressed), "
            f"{len(d.keys)} story keys"]


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


def report(c: Comparison, *, title: str = "") -> str:
    """The comparison as plain text: STOCK ONLY, FORK ONLY, UNSTABLE, RESIDUE, CENSUS GAPS, JOIN FAILURES."""
    ns, nf = len(c.stock), len(c.fork)
    lines = [title or f"story trace: stock x{ns} vs fork x{nf}"]
    lines += _incomplete_banner(c.stock + c.fork, "a key such a run never reached may lie past its cut, so "
                                                  "STOCK ONLY / FORK ONLY / UNSTABLE below are not evidence")
    for d in c.stock:
        lines += _run_header(d)
    for d in c.fork:
        lines += _run_header(d)
    lines += _side_notes(c.stock, "stock") + _side_notes(c.fork, "fork")
    lines.append(f"  matched in every run of both sides: {len(c.matched)} key(s)")

    def section(name, keys, tail=lambda k: "", note=""):
        lines.append("")
        lines.append(f"{name} ({len(keys)})" + (f" -- {note}" if note else ""))
        for k in keys:
            lines.append(_key_line(k, c.seen[k], tail(k)))

    section("STOCK ONLY", c.stock_only, note=f"in {ns}/{ns} stock runs, 0/{nf} fork runs")
    section("FORK ONLY", c.fork_only, note=f"in 0/{ns} stock runs, {nf}/{nf} fork runs")
    section("UNSTABLE", c.unstable, lambda k: f"   stock {c.counts[k][0]}/{ns} fork {c.counts[k][1]}/{nf}")
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


def report_runs(runs, *, title: str = "") -> str:
    """One side alone (the rung-0 check): every story key with the instruction it joined to, then the
    census gaps, residue and join failures.

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
