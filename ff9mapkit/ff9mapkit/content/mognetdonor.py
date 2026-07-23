"""The Mognet DONOR-FORK lane -- patching a REAL moogle field in place so the 42nd identity is a full
network citizen there. The three faces of the class (project memory `project-ff9-mognet-protocol`):

  * **letter CONTENT at a stock recipient** -- the donor's letter-display ``op_06`` switch (selector =
    ``MAP.Byte[37]``, arms = ``WindowAsync(3, 16, <txid>)``) has no arm for a custom variant, so a
    delivered custom letter shows the graceful empty flash. Fix: splice guarded arms at the switch's
    CONVERGENCE point (``if (Byte[37] == v) WindowAsync(3, 16, txid)``) -- the jump-table-aware
    ``edit.insert_in_function`` fixes every crossing displacement (built for exactly this).
  * **the blank NAME on the stock roster** -- the donor's text entry 0 is a ``[TBLE=]`` + 41 name rows;
    row 41 (our id) reads as blank. Fix: an additive ``.mes`` override re-emitting ``[TXID=0]`` with a
    42nd row appended (the TBLE tag params are PROVEN inert -- the engine splits on ``\\n``).
  * **INBOUND mail addressed to us** -- a stock moogle's gives are per-field constants; none targets
    id 41. Fix: PREPEND a gated give-offer to the donor moogle's own talk tag (a ``rel_off == 0``
    prepend is always jump-safe): ``if give_available(v): [offer] -> Yes -> give_letter_body(from =
    the donor's own id, to = 41)`` -- the letter then rides the REAL mailbox to our moogle's proven
    accept path.

⚠ PROVENANCE: everything here READS the stock ``.eb``/``.mes`` and emits DERIVED bytes. The patched
files are generated from the USER'S OWN INSTALL at deploy time (``tools/mognet_donor_patch.py``) and
land in the mod folder -- never in the repo (the extract-templates precedent). The additive ``.mes``
carries stock text ONLY in the re-emitted entry 0 (the roster), which is why it too is deploy-time.
"""
from __future__ import annotations

from ..eb import EbScript, edit, opcodes
from ..eb.disasm import decode_switch, read_code
from . import region as _region
from . import mognet as _mognet
from . import choice as _choice

VARIANT_BYTE = 37         # MAP.Byte[37] -- the letter-display selector the donor's op_06 switches on
WINDOW_ASYNC_OP = 0x20    # the arms' window op (WindowAsync(LETTER_WINDOW, LETTER_FLAGS, txid))


def find_letter_display(eb_bytes) -> dict | None:
    """Locate the donor's letter-content switch structurally: an ``op_06`` whose selector statement is
    exactly ``05 D5 25 7F`` (push ``Byte[37]``) and whose every case arm OPENS with
    ``WindowAsync(3, 16, <txid>)``. Returns ``{entry, tag, func_start, switch_off, conv, arms}`` where
    ``conv`` = the default target (the arms' convergence -- where a guarded custom arm splices in) and
    ``arms`` = ``{variant: txid}``; or None (not a Mognet recipient field)."""
    eb = EbScript.from_bytes(eb_bytes)
    selector = bytes([0x05, _region.GLOB_UINT8, VARIANT_BYTE, 0x7F])
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            prev = None
            for ins in eb.instrs(f):
                if (ins.op == 0x06 and prev is not None
                        and eb.data[prev.off:prev.end] == selector):
                    info = decode_switch(ins)
                    if info is None:
                        prev = ins
                        continue
                    arms, default_tgt, ok = {}, None, True
                    for ed in info.edges:
                        if ed.value is None:
                            default_tgt = ed.target
                            continue
                        t, _ = read_code(eb.data, ed.target)
                        if (t.op == WINDOW_ASYNC_OP and len(t.args) >= 3
                                and t.args[0] == _mognet.LETTER_WINDOW
                                and t.args[1] == _mognet.LETTER_FLAGS):
                            arms[ed.value] = t.args[2]
                        else:
                            ok = False
                    if ok and arms and default_tgt is not None:
                        return {"entry": e.index, "tag": f.tag, "func_start": f.abs_start,
                                "switch_off": ins.off, "conv": default_tgt, "arms": arms}
                prev = ins
    return None


def letter_content_guard(variant: int, txid: int) -> bytes:
    """One spliced arm: ``if (Byte[37] == variant) WindowAsync(3, 16, txid)`` -- the same window shape
    as the donor's own arms, gated so every stock path flows through untouched."""
    return _region.if_block(
        _region.cond_cmp(_region.GLOB_UINT8, VARIANT_BYTE, int(variant), "=="),
        opcodes.window_async(_mognet.LETTER_WINDOW, _mognet.LETTER_FLAGS, int(txid)))


def patch_recipient_letters(eb_bytes, letters: dict) -> bytes:
    """Splice content arms for ``letters`` = ``{variant: txid}`` at the donor's letter-display
    convergence. Every stock arm's jump targets the convergence (== the insert point), so it flows
    INTO the guards and falls through for stock variants -- the ``tgt == abs_ins`` insert semantics."""
    site = find_letter_display(eb_bytes)
    if site is None:
        raise ValueError("no Mognet letter-display switch found -- not a recipient moogle field?")
    for v in letters:
        _mognet.check_variant(v)
        if v in site["arms"]:
            raise ValueError(f"variant {v} already has a stock arm (txid {site['arms'][v]})")
    frag = b"".join(letter_content_guard(v, t) for v, t in sorted(letters.items()))
    return edit.insert_in_function(eb_bytes, site["entry"], site["tag"],
                                   site["conv"] - site["func_start"], frag)


def inbound_give_prepend(variant: int, *, from_id: int, prompt_txid: int,
                         give_txid: int | None = None, to_id: int = _mognet.NEW_MOOGLE_ID) -> bytes:
    """The gated give-offer PREPENDED to the donor moogle's talk tag -- the donor becomes a SENDER of
    a letter to our moogle. One-shot + free-slot gated (``give_available_cond``); the offer is a
    confirm window whose Yes runs :func:`mognet.give_letter_body` (from = the DONOR's own roster id,
    to = ours). Declining re-offers next talk; accepting sets the variant's give lock -- the stock
    gives' own shape. No RETURN: control falls through into the donor's real talk flow either way."""
    offer = (opcodes.window_sync(_mognet.CHOICE_WINDOW, _mognet.CHOICE_FLAGS, int(prompt_txid))
             + _choice.switch_on_choice([
                 _mognet.give_letter_body(int(variant), int(to_id), from_id=int(from_id),
                                          give_txid=give_txid),
                 b""]))
    return _region.if_block(_mognet.give_available_cond(int(variant)), offer)


def patch_inbound_give(eb_bytes, *, variant: int, from_id: int, prompt_txid: int,
                       give_txid: int | None = None) -> bytes:
    """Prepend the inbound give-offer onto the donor moogle's talk tag (located via the letter-display
    scan -- the same function hosts the whole Mognet flow). A prepend is always jump-safe."""
    site = find_letter_display(eb_bytes)
    if site is None:
        raise ValueError("no Mognet letter-display switch found -- not a recipient moogle field?")
    frag = inbound_give_prepend(variant, from_id=from_id, prompt_txid=prompt_txid, give_txid=give_txid)
    return edit.insert_in_function(eb_bytes, site["entry"], site["tag"], 0, frag)


def _re_emit_entry(entry, text: str) -> str:
    """Re-emit one parsed MesEntry with new ``text``, preserving its exact STRT/TAIL."""
    tail = f"[TAIL={entry.tail}]" if entry.tail else ""
    return f"_[TXID={entry.txid}][STRT={entry.strt}]{tail}{text}[ENDN]"


def donor_mes_additions(stock_mes_body: str, *, roster_name: str | None = None,
                        letters: dict | None = None, prompts: list | None = None) -> tuple:
    """Build the ADDITIVE ``.mes`` override for a donor field's block: re-emitted ``[TXID=0]`` with the
    42nd roster row appended (when ``roster_name``), plus new entries above the stock max txid for
    ``letters`` = ``{variant: body_text}`` (rendered through the stock letter template -- the STRT of
    an existing stock letter entry is reused) and ``prompts`` = plain window texts (the inbound offer
    lines). Returns ``(mes_text, {variant: txid}, [prompt_txids])``.

    The override merges per-txid over the stock block (FF9TextTool is cumulative), so ONLY the touched
    txids ship -- nothing else is redefined. Stock text appears ONLY in the re-emitted entry 0, which
    is why this runs at deploy time from the user's own install (provenance)."""
    from .. import dialogue as _dialogue
    entries = _dialogue.parse_mes(stock_mes_body)
    if 0 not in entries:
        raise ValueError("stock block has no entry 0 (the roster) -- not a moogle field block?")
    parts = []
    if roster_name is not None:
        e0 = entries[0]
        rows = e0.text.split("\n")
        if len(rows) != _mognet.ROSTER_SIZE:
            raise ValueError(f"entry 0 has {len(rows)} roster rows, expected {_mognet.ROSTER_SIZE} -- "
                             f"refusing to patch an unrecognised roster")
        parts.append(_re_emit_entry(e0, e0.text + "\n" + str(roster_name)))
    next_txid = max(entries) + 1
    # the stock letter template's window geometry: reuse an existing letter arm's STRT (they are
    # per-field placement -- the window-geometry-is-part-of-the-entry law)
    letter_txids, prompt_txids = {}, []
    if letters:
        from .text import mes_entry
        strt = None
        for e in entries.values():          # any entry opening with the letter header's [WDTH tag
            if e.text.startswith("[WDTH") and e.strt:
                strt = tuple(int(v) for v in e.strt.split(","))
                break
        for v in sorted(letters):
            body = _mognet.letter_entry_text(letters[v])
            parts.append(mes_entry(body, next_txid, strt=strt or (10, 1), tail=""))
            letter_txids[v] = next_txid
            next_txid += 1
    for p in (prompts or []):
        from .text import mes_entry
        parts.append(mes_entry(str(p), next_txid))
        prompt_txids.append(next_txid)
        next_txid += 1
    return "".join(parts), letter_txids, prompt_txids


def patch_donor_field(eb_bytes, stock_mes_body: str, *, roster_name: str | None = None,
                      content_letters: dict | None = None, inbound: dict | None = None) -> tuple:
    """The one-call donor patch. ``content_letters`` = ``{variant: letter_body_text}`` (letters OUR
    moogle sends TO this donor -- face 2); ``roster_name`` = our moogle's name (face 3); ``inbound`` =
    ``{variant, prompt, line?}`` (a letter THIS donor sends to us -- face 1; ``prompt`` = the offer
    window text, ``line`` = the optional Yes-side send-off line). Returns
    ``(patched_eb, additive_mes_text)``."""
    inbound = dict(inbound) if inbound else None
    prompts = []
    if inbound:
        prompts.append(inbound["prompt"])
        if inbound.get("line"):
            prompts.append(inbound["line"])
    mes_text, letter_txids, prompt_txids = donor_mes_additions(
        stock_mes_body, roster_name=roster_name, letters=content_letters, prompts=prompts)
    out = eb_bytes
    if letter_txids:
        out = patch_recipient_letters(out, letter_txids)
    if inbound:
        from_id = inbound.get("from_id")
        if from_id is None:
            raise ValueError("inbound patch needs from_id = the donor moogle's own roster id")
        out = patch_inbound_give(out, variant=int(inbound["variant"]), from_id=int(from_id),
                                 prompt_txid=prompt_txids[0],
                                 give_txid=(prompt_txids[1] if len(prompt_txids) > 1 else None))
    return out, mes_text
