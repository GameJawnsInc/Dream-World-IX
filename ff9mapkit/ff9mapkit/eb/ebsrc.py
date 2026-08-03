"""The ``.ebs`` SOURCE form — whole-file, byte-exact `.eb` round-trip (eb-roundtrip Rungs 2-3).

:func:`write_source` decompiles a complete field event binary to re-assemblable text;
:func:`assemble_source` is its exact inverse. Function bodies ride the proven
:mod:`ff9mapkit.eb.cmdasm` labeled source (jump/switch targets as ``L<n>`` labels); this module
adds the FILE ENVELOPE: header, the per-language name block, the entry table, and func tables.

Grammar v1 — frozen by the Rung-1 census (``studies/eb-roundtrip/FINDINGS.md``; measured over
all 818 field EVTs x 7 languages), hardened by the adversarial review (see git log):

    .ebs 1                                 format version (required, first directive)
    .byte2 N                               header byte [2] (only when != 2; census: always 2)
    .name <248 hex chars>                  the 124-byte name block [0x04..0x80), STORED VERBATIM
                                           (per-language; jp carries a 2nd name + binary blob)
    .entry I EMPTY [off=N]                 an empty entry-table slot
    .entry I type=T loc=L flags=F [pad=P] [off=N]     a non-empty slot
    .entry I loc=L flags=F [pad=P] [off=N] raw=<hex>  ESCAPE HATCH: the whole entry blob
                                           (type byte + func table + bodies) verbatim, for an
                                           entry whose func table cannot be represented
                                           structurally (e.g. the kit's blank-template entry 0)
    .gap off=N raw=<hex>                   ESCAPE HATCH: file bytes covered by NO entry's
                                           declared span, verbatim. The kit's blank-template
                                           lineage declares entry 0 SMALLER than its func
                                           table's reach, so its Main_Loop body physically
                                           lives between entries -- the engine reads funcs by
                                           fpos and never consults the size, so those orphan
                                           bytes are live code and must survive the round trip
    .func TAG                              a function of the current (non-raw) entry
    <cmdasm source lines>                  the function body (may be absent = zero-length func)

``#`` starts a comment anywhere; a leading UTF-8 BOM is tolerated. Every slot index
``0..slots-1`` must appear exactly once (max index 254 — the header slot count is a u8).
Everything not stored is DERIVED, per the census: entry bodies contiguous in slot order from
the table end; func tables canonical (``fpos[0] == funcCount*4``, ascending); an EMPTY slot's
``off`` = the next non-empty entry's off, trailing empties park at the LAST non-empty entry's
off (proven 38325/38325). The ``off=`` overrides exist because KIT-BUILT/EDITED files deviate
(stale parked offs after length-changing edits; append_entry places a middle slot's body at
EOF): the writer emits an override exactly where a file deviates from the derived layout, so
the toolkit's own output round-trips too — stock files emit none.

Safety stance: :func:`write_source` always SELF-VERIFIES — it reassembles its own output and
raises :class:`EbSrcError` on any byte difference — and every failure on either side
(unparseable input bytes, hand-authored source errors) is an :class:`EbSrcError` naming where,
never a raw traceback.
"""
from __future__ import annotations

from struct import error as struct_error

from . import cmdasm, exprasm
from .model import EbScript, ENTRY_TABLE_OFF

NAME_END = ENTRY_TABLE_OFF                  # the name block is [0x04..0x80)
NAME_LO = 4
NAME_LEN = NAME_END - NAME_LO               # 124 bytes
FORMAT_VERSION = 1
MAX_SLOT = 254                              # slot count lives in a u8: 255 slots -> max index 254

# error classes the per-function assembler can raise on hand-authored bodies; all are converted
# to EbSrcError with entry/tag context (exprasm.AssembleError is a ValueError but NOT a
# CmdAsmError; a non-numeric immediate raises int()'s ValueError; a malformed operand list can
# IndexError inside the encoder)
_BODY_ERRORS = (cmdasm.CmdAsmError, exprasm.AssembleError, ValueError, IndexError)


class EbSrcError(ValueError):
    pass


# --------------------------------------------------------------------------- writer (decompile)

def _structured_funcs(data: bytes, e) -> "list[str] | None":
    """The ``.func`` source lines for a well-formed entry, or None when the entry's func table
    cannot be represented structurally (non-canonical fpos, a func range outside the entry, or
    a body the labeled disassembler refuses) — the caller then falls back to ``raw=``."""
    fp = [f.fpos for f in e.funcs]
    if not fp or fp[0] != e.func_count * 4 or any(b <= a for a, b in zip(fp, fp[1:])):
        return None
    if any(f.abs_start > f.abs_end or f.abs_end > e.abs_end for f in e.funcs):
        return None
    lines: list[str] = []
    for f in e.funcs:
        lines.append(f".func {f.tag}")
        if f.length:
            try:
                lines.append(cmdasm.disassemble_block(data, f.abs_start, f.abs_end))
            except cmdasm.CmdAsmError:
                return None
    return lines


def write_source(data: bytes, *, title: str = "") -> str:
    """Decompile a whole ``.eb`` to ``.ebs`` source. ``title`` becomes a leading comment line.
    ALWAYS self-verifies: the returned text reassembles (:func:`assemble_source`) to exactly
    ``data``, or this raises :class:`EbSrcError` (with the first differing offset)."""
    try:
        eb = EbScript.from_bytes(data)
    except (ValueError, IndexError, struct_error) as ex:
        raise EbSrcError(f"not a parseable .eb: {ex}") from ex
    lines: list[str] = []
    if title:
        lines.append(f"# {title}")
    lines.append(f".ebs {FORMAT_VERSION}")
    if data[2] != 2:
        lines.append(f".byte2 {data[2]}")
    lines.append(f".name {data[NAME_LO:NAME_END].hex()}")

    nonempty = [e for e in eb.entries if not e.empty]
    if not nonempty:
        raise EbSrcError("this .eb has no non-empty entries -- nothing to decompile")
    # the assembler's placement cursor, replayed on the ACTUAL offs: an entry (or empty slot)
    # matching the derived value emits no off=; a deviating one gets an explicit override
    pos = eb.entry_count * 8
    for e in eb.entries:
        slot = data[ENTRY_TABLE_OFF + e.index * 8: ENTRY_TABLE_OFF + (e.index + 1) * 8]
        pad = int.from_bytes(slot[6:8], "little")
        if e.empty:
            nxt = next((n for n in eb.entries[e.index + 1:] if not n.empty), None)
            want = nxt.off if nxt is not None else nonempty[-1].off
            head = f".entry {e.index} EMPTY"
            if e.off != want:
                head += f" off={e.off}"
            lines.append(head)
            continue
        head = f".entry {e.index} type={e.type} loc={e.loc} flags={e.flags}"
        if pad:
            head += f" pad={pad}"
        if e.off != pos:
            head += f" off={e.off}"
        pos = max(pos, e.off + e.size)
        funcs = _structured_funcs(data, e)
        if funcs is None:                    # the escape hatch: entry blob verbatim
            blob = data[e.abs_start:e.abs_end].hex()
            lines.append(head.replace(f" type={e.type}", "", 1) + f" raw={blob}")
        else:
            lines.append(head)
            lines.extend(funcs)

    # bytes covered by NO entry span (blank-template overhang code, EOF slack) -> .gap records
    covered = bytearray(len(data))
    covered[:ENTRY_TABLE_OFF + eb.entry_count * 8] = b"\x01" * (ENTRY_TABLE_OFF + eb.entry_count * 8)
    for e in nonempty:
        covered[e.abs_start:e.abs_end] = b"\x01" * (e.abs_end - e.abs_start)
    i = 0
    while i < len(data):
        if covered[i]:
            i += 1
            continue
        j = i
        while j < len(data) and not covered[j]:
            j += 1
        lines.append(f".gap off={i - ENTRY_TABLE_OFF} raw={data[i:j].hex()}")
        i = j
    src = "\n".join(lines) + "\n"

    out = assemble_source(src)
    if out != data:
        n = min(len(out), len(data))
        at = next((i for i in range(n) if out[i] != data[i]), n)
        raise EbSrcError(
            f"self-verify failed: reassembly differs at byte {at} "
            f"(source {len(data)}B, reassembled {len(out)}B) -- this file has a layout the "
            f".ebs grammar cannot yet express (uncovered gap bytes or EOF slack?); please "
            f"report it (studies/eb-roundtrip/FINDINGS.md)")
    return src


# --------------------------------------------------------------------------- parser + assembler

def _int_attr(lineno: int, k: str, v: str) -> int:
    try:
        return int(v, 0)
    except ValueError as ex:
        raise EbSrcError(f"line {lineno}: attribute {k}={v!r} is not an integer") from ex


def _parse_entry_attrs(lineno: int, idx: int, tokens) -> dict:
    """The key=value tail of a non-EMPTY .entry line -> {ints... , 'raw': bytes|None}."""
    out: dict = {"raw": None}
    seen: set = set()
    for t in tokens:
        if "=" not in t:
            raise EbSrcError(f"line {lineno}: malformed attribute {t!r} (want key=value)")
        k, _, v = t.partition("=")
        if k in seen:
            raise EbSrcError(f"line {lineno}: duplicate attribute {k!r}")
        seen.add(k)
        if k == "raw":
            try:
                out["raw"] = bytes.fromhex(v)
            except ValueError as ex:
                raise EbSrcError(f"line {lineno}: raw= is not valid hex") from ex
        elif k in ("type", "loc", "flags", "pad", "off"):
            out[k] = _int_attr(lineno, k, v)
        else:
            raise EbSrcError(f"line {lineno}: unknown attribute {k!r}")
    if out["raw"] is not None:
        if "type" in out:
            raise EbSrcError(f"line {lineno}: a raw= entry carries no type= "
                             f"(the type byte is inside the raw blob)")
        if len(out["raw"]) < 2:
            raise EbSrcError(f"line {lineno}: raw= blob must be at least 2 bytes (type + funcCount)")
    elif "type" not in out:
        raise EbSrcError(f"line {lineno}: .entry {idx} needs type= (or raw=/EMPTY)")
    return out


def _parse(text: str):
    """Parse ``.ebs`` text -> (byte2, name_bytes, entries): a dense list over slots 0..N-1 of
    dicts — ``{'empty': True, 'off': int|None}`` or
    ``{'empty': False, type/loc/flags/pad/off, 'raw': bytes|None, 'funcs': [(tag, [lines])]}``."""
    text = text.lstrip(chr(0xFEFF))     # tolerate a UTF-8 BOM from Windows editors
    byte2 = 2
    name: bytes | None = None
    seen_version = False
    entries: dict[int, dict] = {}
    gaps: list[tuple[int, bytes]] = []      # (rel off, verbatim bytes) uncovered by any entry
    cur: dict | None = None                 # the open structured (non-raw) entry
    cur_func: list | None = None            # its open function's body-line list

    for lineno, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if not line.startswith("."):
            # a cmdasm body line (instruction or L<n>: label) of the open function
            if cur_func is None:
                raise EbSrcError(f"line {lineno}: instruction outside a .func block: {line!r}")
            cur_func.append(line)
            continue
        tok = line.split()
        d = tok[0]
        if not seen_version:
            if d != ".ebs":
                raise EbSrcError(f"line {lineno}: the first directive must be '.ebs {FORMAT_VERSION}'")
            if len(tok) != 2 or tok[1] != str(FORMAT_VERSION):
                raise EbSrcError(f"line {lineno}: unsupported .ebs version {tok[1:]!r} "
                                 f"(this tool reads version {FORMAT_VERSION})")
            seen_version = True
            continue
        if d == ".ebs":
            raise EbSrcError(f"line {lineno}: duplicate .ebs directive")
        if d == ".byte2":
            if len(tok) != 2:
                raise EbSrcError(f"line {lineno}: .byte2 takes one integer")
            byte2 = _int_attr(lineno, ".byte2", tok[1])
            if not 0 <= byte2 <= 255:
                raise EbSrcError(f"line {lineno}: .byte2 {byte2} out of u8 range")
        elif d == ".name":
            if name is not None:
                raise EbSrcError(f"line {lineno}: duplicate .name")
            if len(tok) != 2:
                raise EbSrcError(f"line {lineno}: .name takes one hex string")
            try:
                name = bytes.fromhex(tok[1])
            except ValueError as ex:
                raise EbSrcError(f"line {lineno}: .name is not valid hex") from ex
            if len(name) != NAME_LEN:
                raise EbSrcError(f"line {lineno}: .name must be {NAME_LEN} bytes ({NAME_LEN * 2} hex chars), "
                                 f"got {len(name)}")
        elif d == ".entry":
            if len(tok) < 3:
                raise EbSrcError(f"line {lineno}: .entry needs an index and EMPTY or attributes")
            idx = _int_attr(lineno, "entry index", tok[1])
            if idx < 0 or idx > MAX_SLOT:
                raise EbSrcError(f"line {lineno}: entry index {idx} out of range 0..{MAX_SLOT} "
                                 f"(the slot count is a u8, so {MAX_SLOT} is the highest index)")
            if idx in entries:
                raise EbSrcError(f"line {lineno}: duplicate .entry {idx}")
            if tok[2] == "EMPTY":
                off = None
                for t in tok[3:]:
                    k, _, v = t.partition("=")
                    if k != "off" or not v:
                        raise EbSrcError(f"line {lineno}: .entry EMPTY takes only an off= override")
                    if off is not None:
                        raise EbSrcError(f"line {lineno}: duplicate attribute 'off'")
                    off = _int_attr(lineno, "off", v)
                entries[idx] = {"empty": True, "off": off}
                cur, cur_func = None, None
            else:
                attrs = _parse_entry_attrs(lineno, idx, tok[2:])
                e = {"empty": False, "type": attrs.get("type"), "loc": attrs.get("loc", 0),
                     "flags": attrs.get("flags", 0), "pad": attrs.get("pad", 0),
                     "off": attrs.get("off"), "raw": attrs["raw"], "funcs": []}
                entries[idx] = e
                if e["raw"] is not None:
                    cur, cur_func = None, None    # a raw entry has no .func blocks
                else:
                    cur, cur_func = e, None
        elif d == ".gap":
            g_off, g_raw = None, None
            for t in tok[1:]:
                k, _, v = t.partition("=")
                if k == "off" and g_off is None and v:
                    g_off = _int_attr(lineno, "off", v)
                elif k == "raw" and g_raw is None and v:
                    try:
                        g_raw = bytes.fromhex(v)
                    except ValueError as ex:
                        raise EbSrcError(f"line {lineno}: .gap raw= is not valid hex") from ex
                else:
                    raise EbSrcError(f"line {lineno}: .gap takes exactly off= and raw=")
            if g_off is None or g_raw is None or not g_raw:
                raise EbSrcError(f"line {lineno}: .gap takes exactly off= and raw= (non-empty)")
            gaps.append((g_off, g_raw))
        elif d == ".func":
            if cur is None:
                raise EbSrcError(f"line {lineno}: .func outside a non-empty structured .entry "
                                 f"(EMPTY and raw= entries take no .func blocks)")
            if len(tok) != 2:
                raise EbSrcError(f"line {lineno}: .func takes one tag integer")
            tag = _int_attr(lineno, ".func tag", tok[1])
            if not 0 <= tag <= 0xFFFF:
                raise EbSrcError(f"line {lineno}: .func tag {tag} out of u16 range")
            cur_func = []
            cur["funcs"].append((tag, cur_func))
        else:
            raise EbSrcError(f"line {lineno}: unknown directive {d!r}")

    if not seen_version:
        raise EbSrcError("empty source (missing .ebs directive)")
    if name is None:
        raise EbSrcError("missing .name directive")
    if not entries:
        raise EbSrcError("no .entry directives")
    slots = max(entries) + 1
    missing = [i for i in range(slots) if i not in entries]
    if missing:
        raise EbSrcError(f"missing .entry for slot(s) {missing} (every slot 0..{slots - 1} must appear)")
    return byte2, name, [entries[i] for i in range(slots)], gaps


def assemble_source(text: str) -> bytes:
    """Assemble ``.ebs`` source -> the complete ``.eb`` bytes (the exact inverse of
    :func:`write_source`). Entry offs/sizes, func-table fpos, and empty-slot offs are derived
    per the census-proven layout rules; explicit ``off=`` / ``raw=`` overrides win where given."""
    byte2, name, entries, gaps = _parse(text)

    # -- per-entry blobs --
    blobs: list[bytes | None] = []
    for idx, e in enumerate(entries):
        if e["empty"]:
            blobs.append(None)
            continue
        if e["raw"] is not None:
            blobs.append(e["raw"])
            continue
        if not 0 <= e["type"] <= 255:
            raise EbSrcError(f"entry {idx}: type {e['type']} out of u8 range")
        fc = len(e["funcs"])
        if not 1 <= fc <= 255:
            raise EbSrcError(f"entry {idx}: needs 1..255 .func blocks, has {fc}")
        table = bytearray()
        bodies = bytearray()
        fpos = fc * 4
        for tag, body_lines in e["funcs"]:
            body = b""
            if body_lines:
                try:
                    body = cmdasm.assemble_block("\n".join(body_lines))
                except _BODY_ERRORS as ex:
                    raise EbSrcError(f"entry {idx} tag {tag}: {ex}") from ex
            if fpos > 0xFFFF:
                raise EbSrcError(f"entry {idx}: func table overflows u16 fpos at tag {tag}")
            table += tag.to_bytes(2, "little") + fpos.to_bytes(2, "little")
            bodies += body
            fpos += len(body)
        blobs.append(bytes([e["type"], fc]) + bytes(table) + bytes(bodies))

    if all(b is None for b in blobs):
        raise EbSrcError("a .eb needs at least one non-empty entry (the empty-slot off rule "
                         "is undefined with none)")

    # -- placement: derived cursor in slot order; an explicit off= wins and the cursor tracks
    #    the furthest end, so out-of-order physical layouts (append_entry) are representable --
    slots = len(blobs)
    offs: list[int | None] = [None] * slots
    pos = slots * 8                                       # rel to ENTRY_TABLE_OFF
    for i, b in enumerate(blobs):
        if b is None:
            continue
        off = entries[i]["off"]
        offs[i] = off if off is not None else pos
        if not 0 <= offs[i] <= 0xFFFF:
            raise EbSrcError(f"entry {i}: off {offs[i]} out of the u16 offset space")
        if offs[i] < slots * 8:
            raise EbSrcError(f"entry {i}: off {offs[i]} overlaps the entry table")
        pos = max(pos, offs[i] + len(b))
    nonempty = [i for i, b in enumerate(blobs) if b is not None]
    last_off = offs[nonempty[-1]]
    empty_offs: list[int | None] = [None] * slots
    for i in range(slots):
        if offs[i] is not None:
            continue
        explicit = entries[i]["off"]
        if explicit is not None:
            empty_offs[i] = explicit
        else:
            nxt = next((offs[j] for j in range(i + 1, slots) if offs[j] is not None), None)
            empty_offs[i] = nxt if nxt is not None else last_off
        if not 0 <= empty_offs[i] <= 0xFFFF:
            raise EbSrcError(f"entry {i}: empty-slot off {empty_offs[i]} out of u16 range")

    # -- header + name + table + bodies (placed at their offs; derived layouts are contiguous) --
    for g_off, g_raw in gaps:
        if g_off < slots * 8:
            raise EbSrcError(f".gap off={g_off} overlaps the entry table")
        pos = max(pos, g_off + len(g_raw))
    total = ENTRY_TABLE_OFF + max(pos, slots * 8)
    out = bytearray(total)
    out[0:2] = b"EV"
    out[2] = byte2
    out[3] = slots
    out[NAME_LO:NAME_END] = name
    for i, b in enumerate(blobs):
        e = entries[i]
        off = offs[i] if b is not None else empty_offs[i]
        sz = len(b) if b is not None else 0
        loc = e.get("loc", 0) or 0
        flags = e.get("flags", 0) or 0
        pad = e.get("pad", 0) or 0
        for v, nm in ((sz, "size"), (loc, "loc"), (flags, "flags"), (pad, "pad")):
            hi = 0xFFFF if nm in ("size", "pad") else 0xFF
            if not 0 <= v <= hi:
                raise EbSrcError(f"entry {i}: {nm} {v} out of range")
        base = ENTRY_TABLE_OFF + i * 8
        out[base:base + 2] = off.to_bytes(2, "little")
        out[base + 2:base + 4] = sz.to_bytes(2, "little")
        out[base + 4] = loc
        out[base + 5] = flags
        out[base + 6:base + 8] = pad.to_bytes(2, "little")
        if b is not None:
            out[ENTRY_TABLE_OFF + off: ENTRY_TABLE_OFF + off + len(b)] = b
    for g_off, g_raw in gaps:
        out[ENTRY_TABLE_OFF + g_off: ENTRY_TABLE_OFF + g_off + len(g_raw)] = g_raw
    return bytes(out)
