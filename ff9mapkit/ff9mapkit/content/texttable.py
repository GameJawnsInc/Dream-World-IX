"""``[[text_table]]`` -- a field's own ``[TBLE]`` STRING BANKS, and the ``[TEXT=<name>,slot]`` tags
that read a row out of one.

WHAT THE ENGINE DOES, end to end (every step transcribed from the open-source Memoria C#):

  1. a dialogue line renders ``[TEXT=bank,slot]`` -> ``DialogBoxSymbols.ParseSingleConstantTextReplaceTag``
     -> ``ETb.GetStringFromTable(UIntParam(0), UIntParam(1))`` (ETb.cs:270-283);
  2. ``GetStringFromTable`` bounds the SLOT (``index < 8u``) and the ROW
     (``tableIndex < tableText.Length``) but has **no lower bound** -- a negative ``gMesValue[slot]``
     indexes ``tableText[-n]`` and throws, which is why every emitter that publishes into a
     ``[TEXT=]`` slot wraps :func:`content.behavior.hud_row_index_clamp` around the expression;
  3. the BANK is a **TXID in this field's own ``.mes``** -- ``FF9TextTool.GetTableText(index)`` looks
     ``index`` up in ``DisplayBatch.fieldText`` and hands the raw entry to
     ``DialogBoxSymbols.ParseTextSplitTags`` (FF9TextTool.cs:650-659);
  4. ``ParseTextSplitTags`` walks tags until it meets ``FFIXTextTagCode.Table`` (``[TBLE`` --
     ``NGUIText.TableStart``, NGUIText.cs:1536), strips a trailing ``[ENDN]``, and returns
     ``text.Substring(<after the tag>).Split('\\n')`` (DialogBoxSymbols.cs:35-38). So the rows are
     newline-separated and **the tag's own parameters are inert**.

⚠ THE BANK CANNOT BE AUTHORED, AND THAT IS THE WHOLE REASON THIS MODULE EXISTS.
:func:`build.collect_text` assigns txids **by position** (``content.text.txid_map``), so a
hand-written ``[TEXT=612,2]`` in a TOML bakes an id that moves the instant a line is added above it --
and the failure is silent: the wrong bank renders another table's row, and a bank with no entry
renders ``String.Empty``, i.e. a BLANK LINE, which a player reads as a bug. The lane therefore takes
a **name**, the build ALLOCATES the entry, and :func:`resolve` substitutes the assigned txid into
every reference. An unresolved name is refused at the substitution site, not merely documented.

    [[text_table]]
    name = "th_rank"
    rows = ["H", "G", "F", "E", "D", "C", "B", "A", "S"]

    # ...then anywhere a dialogue body is authored:
    #   Rank  [TEXT=th_rank,2]        <- slot 2 holds the row index, published by the .eb

A NUMERIC bank passes through untouched (``[TEXT=0,0]`` is the Mognet roster idiom,
``content.mognet.VAR_SPEAKER``) -- this lane adds a naming layer, it does not replace the raw form.

⚠ A BANK ABOVE 255 IS FINE HERE, and the standing "keep banks under 256" caveat is narrower than it
reads. ``NGUIText.GetDialogWidthFromSpecialOpcode`` (NGUIText.cs:60-84) carries a SECOND, packed
``[TEXT=]`` decode -- ``tableId > Byte.MaxValue`` reads a constant row from
``GetTableText(tableId - 256)``, while ``tableId <= 255`` is treated as the packed
``bank=(t>>4)&3, slot=t&7`` form -- and ``DialogBoxSymbols``' replacement path implements neither: it
is a plain ``ETb.GetStringFromTable(UIntParam(0), UIntParam(1))`` (DialogBoxSymbols.cs:59-60). The
divergent decoder is reachable ONLY from ``OnWidths``, i.e. the ``[WDTH]`` tag, which Memoria marks
``// Dummied`` (DialogBoxSymbols.cs:905). The kit emits no ``[WDTH=]``, so a bank of 509 renders and
measures through the same one function. Do not add ``[WDTH=]`` to an entry that carries a ``[TEXT=]``.

Provenance: derived from the open-source Memoria C# and this kit's own emitters. No SE bytes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: The engine's table-open tag (``NGUIText.TableStart``). Emitted in stock's own ``[TBLE=...]`` form:
#: the real Mognet roster is ``[TBLE=41,82,88,93,...]`` -- **41 rows, first parameter 41**, the rest
#: per-row byte offsets from the PSX text blob. ``ParseTextSplitTags`` ignores every parameter
#: (DialogBoxSymbols.cs:35-38), so we emit the row count alone; the ``=`` form is kept because it is
#: what every other TBLE consumer in this kit and in Memoria matches on (the dummied
#: ``FF9TextTool.ExtractTableText`` and ``battle/extract.py``'s field-vs-battle discriminator both
#: test the literal ``"[TBLE="``).
TABLE_OPEN = "[TBLE"

#: ``ETb.GetStringFromTable`` guards ``index < 8u`` against ``gMesValue = new Int32[8]`` -- a slot
#: outside 0..7 returns ``String.Empty`` and renders a blank line.
MAX_SLOT = 7

#: Every ``[TEXT=bank,slot]`` occurrence. The bank group is deliberately permissive (anything up to
#: the comma): a NAME resolves here, a NUMBER passes through, and anything else is refused loudly by
#: :func:`resolve` rather than being silently left in the shipped ``.mes``.
REF_RE = re.compile(r"\[TEXT=([^,\]\[]*),\s*(\d+)\]")

#: A table name: what a TOML author types and what a ``[TEXT=]`` tag carries. No comma (the tag's own
#: separator), no bracket, no whitespace, and never all-digits (that is the raw txid form).
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


class TextTableError(ValueError):
    """A ``[[text_table]]`` block, or a reference to one, that cannot be emitted."""


@dataclass(frozen=True)
class TextTable:
    name: str
    rows: tuple


def entry_text(rows) -> str:
    """The ``.mes`` entry BODY for one bank: the ``[TBLE=n,]`` tag then the rows, newline-separated.

    No space after the tag (stock's roster has one, and it lands inside row 0 -- harmless there
    because stock's row 0 is a real name, but here row 0 is a value a player reads)."""
    rows = tuple(str(r) for r in rows)
    return f"{TABLE_OPEN}={len(rows)},]" + "\n".join(rows)


def blocks(raw) -> list:
    """The project's ``[[text_table]]`` blocks as :class:`TextTable` records, validated.

    Raises :class:`TextTableError` on anything that would ship a broken bank. ``validate`` turns the
    same failures into build problems with file context; this is the emitter-side gate."""
    out, seen = [], set()
    blks = raw.get("text_table") if isinstance(raw, dict) else None
    if isinstance(blks, dict):                     # a single [text_table] table, not an array
        blks = [blks]
    for i, b in enumerate(blks or []):
        if not isinstance(b, dict):
            raise TextTableError(f"[[text_table]] #{i}: expected a table with `name` and `rows`")
        name = str(b.get("name", "")).strip()
        if not NAME_RE.match(name):
            raise TextTableError(
                f"[[text_table]] #{i}: name {name!r} is not usable inside a [TEXT=<name>,slot] tag. "
                f"Use letters/digits/._- starting with a letter or underscore -- no comma (the tag's "
                f"own separator), no brackets, no spaces, and not a bare number (that is the raw "
                f"txid form the build assigns).")
        if name in seen:
            raise TextTableError(f"[[text_table]] duplicate name {name!r} -- a bank name is the "
                                 f"reference, so two banks cannot share one")
        seen.add(name)
        rows = b.get("rows")
        if not isinstance(rows, (list, tuple)) or not rows:
            raise TextTableError(f"[[text_table]] {name!r}: `rows` must be a non-empty list of "
                                 f"strings (row i is what [TEXT={name},slot] renders when the "
                                 f"published slot value is i)")
        rows = tuple(str(r) for r in rows)
        for j, r in enumerate(rows):
            if "\n" in r:
                raise TextTableError(f"[[text_table]] {name!r} row {j}: rows are NEWLINE-SEPARATED in "
                                     f"the .mes entry (DialogBoxSymbols.cs:38 Split('\\n')), so a row "
                                     f"cannot contain one -- it would silently become two rows and "
                                     f"shift every row below it")
            if TABLE_OPEN in r or "[ENDN]" in r:
                raise TextTableError(f"[[text_table]] {name!r} row {j}: a row may not contain "
                                     f"{TABLE_OPEN}...] or [ENDN] -- both terminate the entry")
        out.append(TextTable(name, rows))
    return out


def refs(line: str) -> list:
    """``[(bank, slot)]`` for every ``[TEXT=bank,slot]`` in ``line`` whose bank is NOT a plain
    number -- i.e. every reference this lane has to resolve."""
    return [(m.group(1).strip(), int(m.group(2)))
            for m in REF_RE.finditer(str(line or "")) if not m.group(1).strip().isdigit()]


def resolve(line: str, banks: dict) -> str:
    """``line`` with every ``[TEXT=<name>,slot]`` rewritten to the txid ``banks[name]``.

    THE CALL-SITE LAW. An unresolved name raises here rather than shipping: an unknown bank id
    renders ``String.Empty`` (ETb.cs:283) -- a BLANK LINE with no error anywhere -- and a blank line
    in a readout is exactly what a player reports as a bug. A numeric bank is left byte-identical, so
    a field with no ``[[text_table]]`` and no named reference passes through untouched."""
    s = str(line)

    def _sub(m):
        bank, slot = m.group(1).strip(), int(m.group(2))
        if bank.isdigit():
            return m.group(0)                       # a raw txid (mognet's [TEXT=0,0]) -- untouched
        if bank not in banks:
            raise TextTableError(
                f"{m.group(0)!r}: no [[text_table]] named {bank!r} in this field. The bank operand of "
                f"a [TEXT=] tag must be a [[text_table]] name (the build allocates and substitutes "
                f"its txid) or a literal txid. An unknown bank renders a BLANK line in-game with no "
                f"error -- known banks here: {sorted(banks) or 'none'}")
        if not 0 <= slot <= MAX_SLOT:
            raise TextTableError(
                f"{m.group(0)!r}: slot {slot} is outside 0..{MAX_SLOT} -- ETb.GetStringFromTable "
                f"guards `index < 8u` against gMesValue's Int32[8] (ETb.cs:270-283) and returns "
                f"String.Empty, i.e. a blank line, for anything else")
        return f"[TEXT={int(banks[bank])},{slot}]"

    return REF_RE.sub(_sub, s)


def validate(raw) -> list:
    """Build problems for a project's ``[[text_table]]`` blocks and the references to them.

    Two failure classes, both silent in-game if they ship: a malformed bank (:func:`blocks`), and a
    ``[TEXT=<name>,slot]`` naming a bank this field does not declare -- which renders a blank line."""
    problems: list = []
    try:
        tables = blocks(raw)
    except TextTableError as e:
        return [str(e)]
    known = {t.name for t in tables}
    seen: set = set()
    for src, body in _authored_bodies(raw):
        for bank, slot in refs(body):
            if (bank, slot, src) in seen:
                continue
            seen.add((bank, slot, src))
            if bank not in known:
                problems.append(
                    f"{src}: [TEXT={bank},{slot}] names no [[text_table]] in this field. Declare "
                    f"`[[text_table]] name = \"{bank}\"` with its `rows`, or write a literal txid. An "
                    f"unknown bank renders a BLANK line in-game (ETb.cs:283 returns String.Empty) "
                    f"-- known banks: {sorted(known) or 'none'}")
            elif not 0 <= slot <= MAX_SLOT:
                problems.append(f"{src}: [TEXT={bank},{slot}] slot is outside 0..{MAX_SLOT} "
                                f"(ETb.GetStringFromTable guards `index < 8u`, ETb.cs:270)")
    return problems


def _authored_bodies(raw):
    """``(where, text)`` for every authored dialogue body a ``[TEXT=]`` tag can legally sit in.

    Deliberately walks the raw tree with plain iteration rather than ``.get`` probes on blocks that
    may not own the key: ``fieldschema``'s recording spy treats a ``get`` as a vocabulary claim, and
    probing ``reply`` on an ``[[npc]]`` would bless ``[[npc]] reply`` as a legal key
    (``content.text.body_text`` documents the same trap)."""
    if not isinstance(raw, dict):
        return
    from . import text as _text

    def _walk(node, where):
        if isinstance(node, dict):
            plain = dict(node)
            for k in _text.BODY_KEYS:
                v = plain.get(k)
                if isinstance(v, str):
                    yield f"{where}.{k}" if where else k, v
            for k, v in plain.items():
                if isinstance(v, (dict, list)):
                    yield from _walk(v, f"{where}.{k}" if where else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                if isinstance(v, (dict, list)):
                    yield from _walk(v, f"{where}[{i}]")

    yield from _walk(raw, "")
