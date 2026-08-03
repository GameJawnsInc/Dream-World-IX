"""The ``.ebs`` SOURCE form — whole-file, byte-exact `.eb` round-trip (eb-roundtrip Rungs 2-3).

:func:`write_source` decompiles a complete field event binary to re-assemblable text;
:func:`assemble_source` is its exact inverse. Function bodies ride the proven
:mod:`ff9mapkit.eb.cmdasm` labeled source (jump/switch targets as ``L<n>`` labels); this module
adds the FILE ENVELOPE: header, the per-language name block, the entry table, and func tables.

Grammar v1 — frozen by the Rung-1 census (``studies/eb-roundtrip/FINDINGS.md``; every claim
below was measured over all 818 field EVTs x 7 languages):

    .ebs 1                                 format version (required, first directive)
    .byte2 N                               header byte [2] (only when != 2; census: always 2)
    .name <248 hex chars>                  the 124-byte name block [0x04..0x80), VERBATIM
                                           (per-language; jp carries a 2nd name + binary blob)
    .entry I EMPTY                         an empty entry-table slot
    .entry I type=T loc=L flags=F [pad=P]  a non-empty slot (pad only when != 0)
    .func TAG                              a function of the current entry
    <cmdasm source lines>                  the function body (may be absent = zero-length func)

``#`` starts a comment anywhere. Every slot index ``0..slots-1`` must appear exactly once
(the slot count is implied by the highest index). EVERYTHING ELSE IS DERIVED, per the census:
entry bodies are contiguous in table order starting at the table end (no gaps, no EOF slack);
func tables are canonical (``fpos[0] == funcCount*4``, ascending); an EMPTY slot's ``off``
equals the next non-empty entry's off, and a TRAILING empty parks at the LAST non-empty
entry's off (proven 38325/38325 empty slots, all languages).

Safety stance: :func:`write_source` always SELF-VERIFIES — it reassembles its own output and
raises :class:`EbSrcError` on any byte difference, so emitted source is round-trip-proven at
birth (a file violating a census invariant is refused loudly, never silently mangled).
"""
from __future__ import annotations

from . import cmdasm
from .model import EbScript, ENTRY_TABLE_OFF

NAME_END = ENTRY_TABLE_OFF                  # the name block is [0x04..0x80)
NAME_LO = 4
NAME_LEN = NAME_END - NAME_LO               # 124 bytes
FORMAT_VERSION = 1


class EbSrcError(ValueError):
    pass


# --------------------------------------------------------------------------- writer (decompile)

def write_source(data: bytes, *, title: str = "") -> str:
    """Decompile a whole ``.eb`` to ``.ebs`` source. ``title`` becomes a leading comment line.
    ALWAYS self-verifies: the returned text reassembles (:func:`assemble_source`) to exactly
    ``data``, or this raises :class:`EbSrcError` (with the first differing offset)."""
    eb = EbScript.from_bytes(data)
    lines: list[str] = []
    if title:
        lines.append(f"# {title}")
    lines.append(f".ebs {FORMAT_VERSION}")
    if data[2] != 2:
        lines.append(f".byte2 {data[2]}")
    lines.append(f".name {data[NAME_LO:NAME_END].hex()}")
    for e in eb.entries:
        if e.empty:
            lines.append(f".entry {e.index} EMPTY")
            continue
        slot = data[ENTRY_TABLE_OFF + e.index * 8: ENTRY_TABLE_OFF + (e.index + 1) * 8]
        pad = int.from_bytes(slot[6:8], "little")
        head = f".entry {e.index} type={e.type} loc={e.loc} flags={e.flags}"
        if pad:
            head += f" pad={pad}"
        lines.append(head)
        for f in e.funcs:
            lines.append(f".func {f.tag}")
            if f.length:
                try:
                    lines.append(cmdasm.disassemble_block(data, f.abs_start, f.abs_end))
                except cmdasm.CmdAsmError as ex:
                    raise EbSrcError(f"entry {e.index} tag {f.tag}: {ex}") from ex
    src = "\n".join(lines) + "\n"

    out = assemble_source(src)
    if out != data:
        n = min(len(out), len(data))
        at = next((i for i in range(n) if out[i] != data[i]), n)
        raise EbSrcError(
            f"self-verify failed: reassembly differs at byte {at} "
            f"(source {len(data)}B, reassembled {len(out)}B) -- this file violates a layout "
            f"invariant the .ebs grammar derives (see studies/eb-roundtrip/FINDINGS.md)")
    return src


# --------------------------------------------------------------------------- parser + assembler

def _parse_kv(tokens, *, allowed) -> dict:
    out = {}
    for t in tokens:
        if "=" not in t:
            raise EbSrcError(f"malformed attribute {t!r} (want key=value)")
        k, _, v = t.partition("=")
        if k not in allowed:
            raise EbSrcError(f"unknown attribute {k!r} (allowed: {sorted(allowed)})")
        if k in out:
            raise EbSrcError(f"duplicate attribute {k!r}")
        try:
            out[k] = int(v, 0)
        except ValueError as ex:
            raise EbSrcError(f"attribute {k}={v!r} is not an integer") from ex
    return out


def _parse(text: str):
    """Parse ``.ebs`` text -> (byte2, name_bytes, entries) where entries is a dense list over
    slots 0..N-1: ``None`` for EMPTY, else ``dict(type, loc, flags, pad, funcs=[(tag, [lines])])``."""
    byte2 = 2
    name: bytes | None = None
    seen_version = False
    entries: dict[int, dict | None] = {}
    cur: dict | None = None                 # the open non-empty entry
    cur_func: list | None = None            # its open function's body-line list

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
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
            byte2 = int(tok[1], 0)
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
            try:
                idx = int(tok[1], 0)
            except ValueError as ex:
                raise EbSrcError(f"line {lineno}: bad entry index {tok[1]!r}") from ex
            if idx < 0 or idx > 255:
                raise EbSrcError(f"line {lineno}: entry index {idx} out of range (u8 slot count)")
            if idx in entries:
                raise EbSrcError(f"line {lineno}: duplicate .entry {idx}")
            if tok[2] == "EMPTY":
                if len(tok) != 3:
                    raise EbSrcError(f"line {lineno}: .entry EMPTY takes no attributes")
                entries[idx] = None
                cur, cur_func = None, None
            else:
                kv = _parse_kv(tok[2:], allowed={"type", "loc", "flags", "pad"})
                if "type" not in kv:
                    raise EbSrcError(f"line {lineno}: .entry {idx} needs type=")
                cur = {"type": kv["type"], "loc": kv.get("loc", 0), "flags": kv.get("flags", 0),
                       "pad": kv.get("pad", 0), "funcs": []}
                entries[idx] = cur
                cur_func = None
        elif d == ".func":
            if cur is None:
                raise EbSrcError(f"line {lineno}: .func outside a non-empty .entry")
            if len(tok) != 2:
                raise EbSrcError(f"line {lineno}: .func takes one tag integer")
            try:
                tag = int(tok[1], 0)
            except ValueError as ex:
                raise EbSrcError(f"line {lineno}: bad .func tag {tok[1]!r}") from ex
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
    return byte2, name, [entries[i] for i in range(slots)]


def assemble_source(text: str) -> bytes:
    """Assemble ``.ebs`` source -> the complete ``.eb`` bytes (the exact inverse of
    :func:`write_source`). Entry offs/sizes, func-table fpos, and empty-slot offs are derived
    per the census-proven layout rules."""
    byte2, name, entries = _parse(text)

    # -- per-entry bodies --
    blobs: list[bytes | None] = []
    for idx, e in enumerate(entries):
        if e is None:
            blobs.append(None)
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
                except cmdasm.CmdAsmError as ex:
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

    # -- layout: bodies contiguous in slot order from the table end; empty offs by the census rule --
    slots = len(blobs)
    offs: list[int | None] = [None] * slots
    pos = slots * 8                                       # rel to ENTRY_TABLE_OFF
    for i, b in enumerate(blobs):
        if b is None:
            continue
        offs[i] = pos
        pos += len(b)
        if offs[i] > 0xFFFF or pos > 0xFFFF:
            raise EbSrcError(f"entry {i}: file exceeds the u16 offset space at rel off {offs[i]}")
    nonempty = [i for i, b in enumerate(blobs) if b is not None]
    last_off = offs[nonempty[-1]]
    for i in range(slots):
        if offs[i] is not None:
            continue
        nxt = next((offs[j] for j in range(i + 1, slots) if offs[j] is not None), None)
        offs[i] = nxt if nxt is not None else last_off

    # -- header + name + table + bodies --
    out = bytearray(ENTRY_TABLE_OFF)
    out[0:2] = b"EV"
    out[2] = byte2
    out[3] = slots
    out[NAME_LO:NAME_END] = name
    for i, b in enumerate(blobs):
        e = entries[i]
        sz = len(b) if b is not None else 0
        loc = e["loc"] if e is not None else 0
        flags = e["flags"] if e is not None else 0
        pad = e["pad"] if e is not None else 0
        for v, nm in ((sz, "size"), (loc, "loc"), (flags, "flags"), (pad, "pad")):
            hi = 0xFFFF if nm in ("size", "pad") else 0xFF
            if not 0 <= v <= hi:
                raise EbSrcError(f"entry {i}: {nm} {v} out of range")
        out += offs[i].to_bytes(2, "little") + sz.to_bytes(2, "little")
        out += bytes([loc, flags]) + pad.to_bytes(2, "little")
    for b in blobs:
        if b is not None:
            out += b
    return bytes(out)
