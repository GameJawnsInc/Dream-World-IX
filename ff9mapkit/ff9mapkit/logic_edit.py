"""Phase-2: in-place, length-preserving, GUARDED value edits on a verbatim fork's ``.eb`` (+ ``.mes`` text).

The write-side sibling of :mod:`ff9mapkit.logic_map` (read) and :mod:`ff9mapkit.eblint` (validate): a verbatim
fork ships the donor's whole compiled ``.eb``, and this lets you EDIT it IN PLACE -- change an item reward, a gil
amount, a ``Field()`` warp destination, a story-flag index, a dialogue txid, or rewrite a dialogue STRING -- WITHOUT
regenerating or splicing the script (that's Phase 4). Every ``.eb`` edit is strictly LENGTH-PRESERVING (a same-width
operand overwrite), so the entry table / fpos never move; the composed ``.eb`` is re-validated by the Phase-3 linter
(:func:`ff9mapkit.eblint.lint_eb`) before the build ships it. Each edit is **old-guarded**: it locates its site by
``entry``/``tag``/``op`` AND the current value, and REFUSES (a clean ``LogicEditError`` -> build failure, never a
silent mis-patch) if the donor bytes drifted. Authored declaratively as ``[[logic_edit]]`` in the member field.toml;
applied in build's verbatim pass (CLAUDE.md / docs/FORK_FIDELITY.md). Empty list -> byte-identical no-op.

v1 kinds: ``field`` (0x2B dest) · ``item`` (0x48 id/count) · ``gil`` (0xCE amount) · ``txid`` (a Window op's text id)
· ``flag_index`` (the GLOB ``C4``/``E4`` index inside an 0x05 expression, width-class-preserving) · ``text`` (a
``.mes`` dialogue-string rewrite, the only non-length-preserving kind -- it targets the per-language ``.mes``, not the
``.eb``). Deferred: ``switch_case`` (a switch's case value) and cross-0xFF flag remaps (a length change = Phase 4).

The ``.eb`` bytecode is language-identical (only the 84-byte name differs), so one edit set patches all 7 langs.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field as _dc_field

from .eb import disasm
from .eb.model import EbScript
from .content.object import _arg_byte_offset

ITEM_OP = 0x48          # AddItem(item_id:u16, count:u8)
GIL_OP = 0xCE           # AddGil(amount:u24)
FIELD_OP = 0x2B         # Field(dest:u16)
EXPR_OP = 0x05          # an expression statement (a GLOB flag read/write rides here)
SETTEXTVAR_OP = 0x66    # SetTextVariable(slot:u8, value:u16) -- feeds the "Received <item>!" DISPLAY id
WINDOW_OPS = {0x1F: 2, 0x20: 2, 0x95: 3, 0x96: 3}   # Window op -> its txid operand index (dialogue.WINDOW_OPS)
_ITEM_OPERAND = {"id": 0, "count": 1}
_EB_KINDS = ("field", "item", "gil", "txid", "flag_index", "operand", "item_display")
_TAIL_RE = re.compile(r"\[TAIL=([^\]]*)\]")


class LogicEditError(ValueError):
    """A logic-edit that can't be applied safely (bad address, drifted donor, overflow, unsupported) -- it
    fails the BUILD, never silently mis-patches the shipped script."""


def _req(ed, key):
    if key not in ed:
        raise LogicEditError(f"logic_edit ({ed.get('kind', '?')}) missing required key '{key}'")
    return ed[key]


def _int(ed, key, *, optional=False):
    """Require ``key`` be a plain int (TOML floats/strings/bools are author mistakes -> a clean LogicEditError,
    not a raw TypeError). ``optional`` returns None when the key is absent."""
    if optional and key not in ed:
        return None
    v = _req(ed, key)
    if isinstance(v, bool) or not isinstance(v, int):
        raise LogicEditError(f"logic_edit ({ed.get('kind', '?')}) key '{key}' must be an integer, "
                             f"got {type(v).__name__} ({v!r})")
    return v


def _func(eb, ed):
    entry, tag = _int(ed, "entry"), _int(ed, "tag")
    if not (0 <= entry < eb.entry_count):
        raise LogicEditError(f"logic_edit entry {entry} out of range (0..{eb.entry_count - 1})")
    e = eb.entry(entry)
    if e.empty:
        raise LogicEditError(f"logic_edit entry {entry} is an empty slot")
    f = e.func_by_tag(tag)
    if f is None:
        raise LogicEditError(f"logic_edit entry {entry} has no function tag {tag}")
    return f


def _pick(hits, ed, what):
    """Choose among instrs already filtered to match the old value: exactly one, or ``nth`` to disambiguate."""
    if not hits:
        raise LogicEditError(f"logic_edit found no {what} (the donor drifted or the address is wrong)")
    if len(hits) == 1:
        return hits[0]
    nth = _int(ed, "nth", optional=True)
    if nth is None:
        raise LogicEditError(f"logic_edit is ambiguous: {len(hits)} {what} -- add `nth` (0..{len(hits) - 1})")
    if not (0 <= nth < len(hits)):
        raise LogicEditError(f"logic_edit nth={nth} out of range (0..{len(hits) - 1}) for {what}")
    return hits[nth]


def _guarded_write(buf, abs_off, w, old, new):
    """Overwrite ``w`` bytes at ``abs_off`` IN PLACE, asserting the current bytes encode ``old`` first (a real
    guard that also catches an offset miscalculation). ``new`` must fit ``w`` bytes."""
    if not (0 <= new < (1 << (8 * w))):
        raise LogicEditError(f"logic_edit new value {new} doesn't fit a {w}-byte operand")
    expect = old.to_bytes(w, "little")
    cur = bytes(buf[abs_off:abs_off + w])
    if cur != expect:
        raise LogicEditError(f"logic_edit guard @{abs_off}: expected {expect.hex()} got {cur.hex()} "
                             "(donor drift or a bad address)")
    buf[abs_off:abs_off + w] = new.to_bytes(w, "little")


def _operand_edit(eb, buf, ed, op, operand_index, *, extra=None, what=None):
    """Locate an instr (op, current operand == old, + an optional ``extra(ins)`` guard) in entry/tag and
    overwrite that operand same-width. ``extra`` lets a kind pin a SECOND operand (e.g. the item-display
    text slot) so the value-filtered nth matches discovery -- without it, an unrelated same-value instr
    could be mis-targeted."""
    f = _func(eb, ed)
    old, new = _int(ed, "old"), _int(ed, "new")
    hits = [i for i in eb.instrs(f) if i.op == op and i.imm(operand_index) == old and (extra is None or extra(i))]
    ins = _pick(hits, ed, what or (f"{disasm.op_name(op)} with operand[{operand_index}]=={old} in "
                                   f"entry{_req(ed, 'entry')}/tag{_req(ed, 'tag')}"))
    bo = _arg_byte_offset(ins, operand_index)
    if bo is None:
        raise LogicEditError(f"logic_edit cannot address {disasm.op_name(op)} operand {operand_index} "
                             "(a preceding operand is an expression)")
    _guarded_write(buf, ins.off + bo, disasm.argsize(op, operand_index), old, new)


def _flag_edit(eb, buf, ed):
    """Remap a GLOB story-flag index inside an 0x05 expression (the C4/E4 var token) -- width-class-preserving."""
    from .eventscan import _glob_var_token
    f = _func(eb, ed)
    old, new = _int(ed, "flag"), _int(ed, "new_flag")
    hits = []
    for i in eb.instrs(f):
        if i.op != EXPR_OP:
            continue
        tok = _glob_var_token(eb.data, i.off + 1)             # the var token sits right after the 0x05
        if tok is not None and tok[0] == old:
            hits.append((i, tok))
    pair = _pick(hits, ed, f"GLOB flag {old} read/write in entry{_req(ed, 'entry')}/tag{_req(ed, 'tag')}")
    ins, (idx, tok_len) = pair
    idx_w = tok_len - 1                                        # C4 -> 1-byte index, E4 -> 2-byte index
    new_w = 1 if new <= 0xFF else 2
    if new_w != idx_w:
        raise LogicEditError(f"logic_edit flag remap {old}->{new} crosses the 0xFF C4/E4 token boundary "
                             "(a length change) -- not supported in the in-place tier (Phase 4)")
    _guarded_write(buf, ins.off + 2, idx_w, old, new)         # 0x05 at off, token byte at off+1, index at off+2


def _apply_eb_edit(eb, buf, ed):
    kind = _req(ed, "kind")
    if kind == "field":
        _operand_edit(eb, buf, ed, FIELD_OP, 0)
    elif kind == "item":
        _operand_edit(eb, buf, ed, ITEM_OP, _ITEM_OPERAND.get(ed.get("operand", "id"), 0))
    elif kind == "gil":
        _operand_edit(eb, buf, ed, GIL_OP, 0)
    elif kind == "txid":
        op = _int(ed, "op")
        if op not in WINDOW_OPS:
            raise LogicEditError(f"logic_edit txid op {op:#x} is not a Window op {sorted(WINDOW_OPS)}")
        _operand_edit(eb, buf, ed, op, WINDOW_OPS[op])
    elif kind == "flag_index":
        _flag_edit(eb, buf, ed)
    elif kind == "operand":                                  # generic escape hatch: patch literal operand
        _operand_edit(eb, buf, ed, _int(ed, "op"), _int(ed, "operand"))   # `operand` of any op (caller owns
        #   the choice of op/operand/nth -- e.g. a hand-authored display patch; no slot guard)
    elif kind == "item_display":                             # the "Received <item>!" DISPLAY half of a reward:
        slot = _int(ed, "slot", optional=True)               #   SetTextVariable(slot, item_id). FF9's item-get
        slot = 0 if slot is None else slot                   #   display is slot 0; pin it so a same-value
        old = _int(ed, "old")                                #   SetTextVariable in another slot isn't corrupted.
        _operand_edit(eb, buf, ed, SETTEXTVAR_OP, 1, extra=lambda i: i.imm(0) == slot,
                      what=f"SetTextVariable(slot={slot}, id={old}) display in "
                           f"entry{_req(ed, 'entry')}/tag{_req(ed, 'tag')}")
    else:
        raise LogicEditError(f"logic_edit unknown .eb kind '{kind}' (kinds: {_EB_KINDS} + 'text')")


def apply_logic_edits(eb_bytes, edits) -> bytes:
    """Apply every NON-text ``[[logic_edit]]`` to ``eb_bytes`` in place (length-preserving, old-guarded) and
    return the patched bytes. Empty / text-only -> byte-identical. Raises :class:`LogicEditError` on any unsafe
    edit (bad address, drift, overflow, unsupported)."""
    eb_edits = [e for e in (edits or []) if e.get("kind") != "text"]
    if not eb_edits:
        return bytes(eb_bytes)
    eb = EbScript.from_bytes(eb_bytes)
    buf = bytearray(eb_bytes)
    for ed in eb_edits:
        _apply_eb_edit(eb, buf, ed)
    return bytes(buf)


# --- .mes dialogue-string rewrite (kind="text") -- a verified in-place splice, per language ----------
def _splice_block(part: str, new_text: str) -> str:
    """Replace the text payload of one ``[STRT=...]...[ENDN]`` block (a ``[STRT=``-split segment), preserving
    its STRT geometry, optional [TAIL], the [ENDN], and any trailing bytes before the next entry."""
    b = part.find("]")
    if b < 0:
        raise LogicEditError("malformed .mes entry (no STRT close)")
    rest = part[b + 1:]
    mt = _TAIL_RE.match(rest)
    tail_str = mt.group(0) if mt else ""
    endn = part.find("[ENDN]", b + 1 + len(tail_str))
    if endn < 0:
        raise LogicEditError("malformed .mes entry (no [ENDN])")
    return part[:b + 1] + tail_str + new_text + part[endn:]


def apply_logic_text_edits(body: str, edits, lang: str) -> str:
    """Apply every ``kind="text"`` edit whose ``lang`` is unset or == ``lang`` to a ``.mes`` body, returning the
    rewritten body. A VERIFIED in-place splice: it replaces one entry's text payload, then re-parses and asserts
    every OTHER entry is byte-identical (so a botched splice fails the build, not the player). v1 supports the
    index-implicit verbatim donor body (no ``[TXID=]`` re-index markers)."""
    text_edits = [e for e in (edits or []) if e.get("kind") == "text" and e.get("lang") in (None, lang)]
    if not text_edits or not body:
        return body
    from .dialogue import parse_mes, strip_tags
    if "[TXID=" in body:
        raise LogicEditError("logic_edit text rewrite on a [TXID=]-reindexed .mes is not supported (Phase 2b)")
    for ed in text_edits:
        txid, old, new = _int(ed, "txid"), _req(ed, "old"), _req(ed, "new")
        if not isinstance(old, str) or not isinstance(new, str):
            raise LogicEditError(f"logic_edit text txid {txid}: 'old' and 'new' must be strings")
        before = parse_mes(body)
        ent = before.get(txid)
        if ent is None:
            raise LogicEditError(f"logic_edit text: txid {txid} not found in the {lang} .mes")
        if old not in (ent.text, strip_tags(ent.text)):
            raise LogicEditError(f"logic_edit text txid {txid} ({lang}): current line != `old` (donor drifted)")
        parts = body.split("[STRT=")
        if not (0 <= txid + 1 < len(parts)):                  # index-implicit: txid == position == part index-1
            raise LogicEditError(f"logic_edit text: txid {txid} out of range in the {lang} .mes")
        parts[txid + 1] = _splice_block(parts[txid + 1], new)
        spliced = "[STRT=".join(parts)
        after = parse_mes(spliced)                            # VERIFY: only the target entry changed
        if len(after) != len(before):
            raise LogicEditError(f"logic_edit text splice changed the .mes entry count ({lang})")
        for t, e in before.items():
            got = after.get(t)
            if got is None:
                raise LogicEditError(f"logic_edit text splice dropped txid {t} ({lang})")
            if t == txid:
                if got.text != new:
                    raise LogicEditError(f"logic_edit text splice didn't take for txid {txid} ({lang})")
            elif (got.text, got.strt, got.tail) != (e.text, e.strt, e.tail):
                raise LogicEditError(f"logic_edit text splice corrupted txid {t} ({lang})")
        body = spliced
    return body


# --- discovery: the editable value-sites of one routine (the GUI authoring surface) -----------------
# The GUI (Workspace "Script (verbatim .eb)" subtree) can't ask the user to hand-write entry/tag/op/nth/old
# coordinates. So this walks ONE (entry, tag) routine the way the appliers' `_pick` filters do, and returns a
# legible EditSite per editable value, each carrying ready-to-fill [[logic_edit]] templates. Edit -> click ->
# pick a new value; :func:`synth_edits` splices it in; :func:`upsert_edits` merges into the field.toml list.
@dataclass
class EditSite:
    """One editable value in a routine -- a row + 'Edit…' affordance in the GUI. ``templates`` are the
    [[logic_edit]] dicts MINUS the new-value key (filled by :func:`synth_edits`). For an item reward the
    AddItem give and the matched ``SetTextVariable`` 'Received <item>!' display are paired in
    ``display_templates`` so ONE edit retargets both -- the give-vs-display decoupling: if only the give
    changes, the message lies (the chest-says-Potion-gives-Elixir bug)."""
    group: str                  # item | gil | field | flag | text  (what's being edited)
    value_kind: str             # item | int | flag | string  -> how the dialog renders/validates NEW
    label: str                  # the row label shown in the panel
    old: object                 # the donor's current value (int, or the us string for text)
    new_key: str = "new"        # the template key the NEW value goes under ("new", or "new_flag" for flag)
    templates: list = _dc_field(default_factory=list)          # the primary edits (the give / the value)
    display_templates: list = _dc_field(default_factory=list)  # item: the paired display edits
    note: str = ""              # an advisory (e.g. no display site found / count not shown)
    key: str = ""               # a stable id for this site within the routine (GUI row <-> its edits)


def _op_tmpl(kind, entry, tag, old, nth, total, *, op=None, operand=None):
    """One length-preserving operand template (the new value spliced in later). ``nth`` is included only
    when the value is ambiguous (``total`` > 1) -- mirroring what the appliers' ``_pick`` requires."""
    t = {"kind": kind, "entry": int(entry), "tag": int(tag), "old": old}
    if op is not None:
        t["op"] = op
    if operand is not None:
        t["operand"] = operand
    if total > 1:
        t["nth"] = nth
    return t


def _value_groups(instrs, op, operand_index):
    """``{value: [nth, ...]}`` for every immediate ``operand_index`` of ``op`` -- the value-filtered nth
    each occurrence gets (the exact index :func:`_pick` resolves), so an edit can target all or one."""
    groups: dict = {}
    for ins in instrs:
        if ins.op != op:
            continue
        v = ins.imm(operand_index)
        if v is None:
            continue
        groups.setdefault(v, []).append(len(groups.get(v, [])))
    return groups


def _line_old(entries, txid):
    """The donor's current line (tag-stripped) for ``txid``, or None (no ``.mes`` / not found)."""
    if not entries:
        return None
    from .dialogue import strip_tags
    ent = entries.get(int(txid))
    return strip_tags(ent.text) if ent is not None else None


def _short(s, width=44):
    s = " ".join(str(s).split())
    return (s[:width] + "…") if len(s) > width else s


def _text_templates(txid, lang_bodies, fallback_old):
    """A per-language ``text`` template (each guarded by THAT language's own current string) so a single
    new string is written to every localized copy consistently. Skips a ``[TXID=]``-reindexed body (Phase
    4) and a language missing the txid. Falls back to one lang-agnostic template when no bodies are given."""
    if not lang_bodies:
        return [{"kind": "text", "txid": int(txid), "old": fallback_old}] if fallback_old is not None else []
    from .dialogue import parse_mes, strip_tags
    out = []
    for lang, body in lang_bodies.items():
        if not body or "[TXID=" in body:
            continue
        ent = parse_mes(body).get(int(txid))
        if ent is None:
            continue
        out.append({"kind": "text", "lang": lang, "txid": int(txid), "old": strip_tags(ent.text)})
    return out


def editable_effects(eb_bytes, entry, tag, *, entries=None, lang_bodies=None):
    """Discover the editable value-sites of one ``(entry, tag)`` routine of a verbatim fork's ``.eb`` --
    item rewards (give + paired display), gil grants, ``Field()`` warps, GLOB story-flag indices, and
    dialogue lines -- each as an :class:`EditSite` the GUI authors a ``[[logic_edit]]`` from. Pure; never
    mutates. ``entries`` = parsed us ``.mes`` (``{txid: MesEntry}``) for line text; ``lang_bodies`` =
    ``{lang: raw .mes body}`` for per-language text-edit guards."""
    eb = EbScript.from_bytes(eb_bytes)
    if not (0 <= entry < eb.entry_count):
        return []
    e = eb.entry(entry)
    if e.empty:
        return []
    f = e.func_by_tag(tag)
    if f is None:
        return []
    from . import forkreport as FR
    instrs = list(eb.instrs(f))
    sites: list = []

    # items: group AddItem by id (skipping the engine no-op grants the read map also hides); pair each with
    # the same-id SetTextVariable in TEXT SLOT 0 (FF9's item-get display, build.set_text_variable(0, id)) so
    # the reward + its "Received <item>!" message change together. A same-value SetTextVariable in another
    # slot (e.g. a preview row) is NOT the item display and is left alone.
    disp_groups: dict = {}
    for ins in instrs:
        if ins.op == SETTEXTVAR_OP and ins.imm(0) == 0:
            v = ins.imm(1)
            if v is not None:
                disp_groups.setdefault(v, []).append(len(disp_groups.get(v, [])))
    item_groups: dict = {}
    for ins in instrs:
        if ins.op != ITEM_OP:
            continue
        iid = ins.imm(0)
        if iid is None or iid == FR.NO_ITEM or FR.item_inert(iid):
            continue
        item_groups.setdefault(iid, []).append(len(item_groups.get(iid, [])))
    for iid, nths in item_groups.items():
        give = [_op_tmpl("item", entry, tag, iid, n, len(nths), op=ITEM_OP, operand="id") for n in nths]
        dn = disp_groups.get(iid, [])
        disp = [{**_op_tmpl("item_display", entry, tag, iid, n, len(dn), op=SETTEXTVAR_OP, operand=1), "slot": 0}
                for n in dn]
        label = f"gives {FR.item_label(iid)}" + (f"  (×{len(nths)})" if len(nths) > 1 else "")
        note = "" if disp else "no 'Received <item>!' display message paired — only the give changes"
        sites.append(EditSite("item", "item", label, int(iid), "new", give, disp, note, f"item:{iid}"))

    # gil grants (skip the > party-cap sentinel amounts -- a scripted/computed AddGil, not a treasure reward)
    for amt, nths in _value_groups(instrs, GIL_OP, 0).items():
        if amt > FR.GIL_CAP:
            continue
        tmpls = [_op_tmpl("gil", entry, tag, amt, n, len(nths), op=GIL_OP) for n in nths]
        sites.append(EditSite("gil", "int", f"gives {amt} gil", int(amt), "new", tmpls, key=f"gil:{amt}"))

    # Field() warps (an alternative to the [verbatim_eb] retarget table -- per-site, not by global dest)
    for dest, nths in _value_groups(instrs, FIELD_OP, 0).items():
        tmpls = [_op_tmpl("field", entry, tag, dest, n, len(nths), op=FIELD_OP) for n in nths]
        sites.append(EditSite("field", "field", f"warps to field {dest}", int(dest), "new", tmpls,
                              key=f"field:{dest}"))

    # GLOB story-flag indices (read + write of one index remap together so they stay in sync)
    from .eventscan import _glob_var_token
    flag_groups: dict = {}
    for ins in instrs:
        if ins.op != EXPR_OP:
            continue
        tok = _glob_var_token(eb.data, ins.off + 1)
        if tok is not None:
            flag_groups.setdefault(tok[0], []).append(len(flag_groups.get(tok[0], [])))
    for idx, nths in flag_groups.items():
        tmpls = [{"kind": "flag_index", "entry": int(entry), "tag": int(tag), "flag": int(idx),
                  **({"nth": n} if len(nths) > 1 else {})} for n in nths]
        n = len(nths)
        sites.append(EditSite("flag", "flag", f"story flag {idx}" + (f"  (×{n})" if n > 1 else ""),
                              int(idx), "new_flag", tmpls, key=f"flag:{idx}"))

    # dialogue lines (one site per distinct Window-op txid that resolves to a line)
    seen_txid: set = set()
    for ins in instrs:
        if ins.op not in WINDOW_OPS:
            continue
        txid = ins.imm(WINDOW_OPS[ins.op])
        if txid is None or txid in seen_txid:
            continue
        seen_txid.add(txid)
        us_old = _line_old(entries, txid)
        tmpls = _text_templates(txid, lang_bodies, us_old)
        if not tmpls:
            continue                                          # no editable .mes for this line
        label = (f'line {txid}: "{_short(us_old)}"' if us_old else f"line {txid}")
        langs = [t["lang"] for t in tmpls if t.get("lang")]
        note = ("rewrites " + ", ".join(langs)) if langs else ""
        sites.append(EditSite("text", "string", label, us_old if us_old is not None else "",
                              "new", tmpls, note=note, key=f"text:{txid}"))
    return sites


# --- edit synthesis + merge (the GUI writes these into the field.toml's logic_edit list) -------------
_COORD_KEYS = ("kind", "entry", "tag", "op", "operand", "slot", "nth", "lang", "txid", "flag", "old")


def synth_edits(site: EditSite, new) -> list:
    """The ``[[logic_edit]]`` dicts that realize editing ``site`` to ``new`` -- the value edits PLUS, for an
    item, the paired display edits (so the 'Received <item>!' message always tracks the give)."""
    out = [{**t, site.new_key: new} for t in site.templates]
    out += [{**t, "new": new} for t in site.display_templates]
    return out


def edit_coord(ed: dict) -> tuple:
    """The identifying coordinates of a logic_edit (everything but the NEW value) -- for dedup/replace."""
    return tuple((k, ed.get(k)) for k in _COORD_KEYS)


def site_footprint(site: EditSite) -> set:
    """The coords of EVERY edit ``site`` can author (value + display) -- so re-editing or clearing a site
    removes all of its prior edits before adding new ones (handles a changed display set cleanly)."""
    return {edit_coord(t) for t in (site.templates + site.display_templates)}


def upsert_edits(existing, new_edits, *, drop=None) -> list:
    """Return ``existing`` with edits whose coords are in ``drop`` (default = the new edits' own coords)
    removed, then ``new_edits`` appended. Pure -- re-editing a site replaces its edits, never stacks them."""
    drop = set(drop) if drop is not None else {edit_coord(e) for e in new_edits}
    kept = [e for e in (existing or []) if edit_coord(e) not in drop]
    return kept + list(new_edits)
