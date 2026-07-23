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


WINDOW_SYNC_OP = 0x1F     # the announce/thanks arms' window op (WindowSync(3, 128, txid))


def find_letter_displays(eb_bytes) -> list:
    """Locate EVERY ``Byte[37]``-selected ``op_06`` whose case arms open with a window op -- the donor's
    letter machinery. Field 1865 (decoded 2026-07-22, the first playtest's finding) has FOUR: per stock
    letter a TRIPLET of txids (announce = letter-1 / letter / thanks = letter+1) across the READ-MAIL
    display, the DELIVERY announce, the DELIVERY display, and the DELIVERY thanks -- patching only one
    leaves the delivery path flashing empty. Each site: ``{entry, tag, func_start, switch_off, conv,
    arms, win_op, win_flags, role}`` with ``role`` in ``letter`` (the 0x20/16 full-screen display) /
    ``announce`` (0x1F arms whose txids sit one BELOW a letter site's) / ``thanks`` (one ABOVE) /
    ``unknown`` (left unpatched, warned by the caller)."""
    eb = EbScript.from_bytes(eb_bytes)
    selector = bytes([0x05, _region.GLOB_UINT8, VARIANT_BYTE, 0x7F])
    sites = []
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            prev = None
            for ins in eb.instrs(f):
                if (ins.op == 0x06 and prev is not None
                        and eb.data[prev.off:prev.end] == selector):
                    info = decode_switch(ins)
                    if info is not None:
                        arms, default_tgt, wops, wflags, ok = {}, None, set(), set(), True
                        for ed in info.edges:
                            if ed.value is None:
                                default_tgt = ed.target
                                continue
                            t, _ = read_code(eb.data, ed.target)
                            if t.op in (WINDOW_ASYNC_OP, WINDOW_SYNC_OP) and len(t.args) >= 3:
                                arms[ed.value] = t.args[2]
                                wops.add(t.op)
                                wflags.add(t.args[1])
                            else:
                                ok = False
                        if ok and arms and default_tgt is not None and len(wops) == 1:
                            sites.append({"entry": e.index, "tag": f.tag, "func_start": f.abs_start,
                                          "switch_off": ins.off, "conv": default_tgt, "arms": arms,
                                          "win_op": wops.pop(), "win_flags": wflags.pop()})
                prev = ins
    # classify: letter sites are the async full-screen displays; a sync site whose every shared
    # variant's txid sits exactly one below/above a letter site's is its announce/thanks sibling
    letter_arms = {}
    for s in sites:
        if s["win_op"] == WINDOW_ASYNC_OP and s["win_flags"] == _mognet.LETTER_FLAGS:
            s["role"] = "letter"
            letter_arms.update(s["arms"])
    for s in sites:
        if "role" in s:
            continue
        shared = [v for v in s["arms"] if v in letter_arms]
        if shared and all(s["arms"][v] == letter_arms[v] - 1 for v in shared):
            s["role"] = "announce"
        elif shared and all(s["arms"][v] == letter_arms[v] + 1 for v in shared):
            s["role"] = "thanks"
        else:
            s["role"] = "unknown"
    return sites


def find_letter_display(eb_bytes) -> dict | None:
    """The primary (first) letter-display site, or None -- the anchor the talk-tag prepend keys on."""
    for s in find_letter_displays(eb_bytes):
        if s["role"] == "letter":
            return s
    return None


def letter_content_guard(variant: int, txid: int, *, win_op: int = WINDOW_ASYNC_OP,
                         win_flags: int = _mognet.LETTER_FLAGS) -> bytes:
    """One spliced arm: ``if (Byte[37] == variant) Window*(3, flags, txid)`` -- the same window op +
    flags as the host site's own arms, gated so every stock path flows through untouched."""
    win = (opcodes.window_async(_mognet.LETTER_WINDOW, win_flags, int(txid))
           if win_op == WINDOW_ASYNC_OP
           else opcodes.window_sync(_mognet.LETTER_WINDOW, win_flags, int(txid)))
    return _region.if_block(
        _region.cond_cmp(_region.GLOB_UINT8, VARIANT_BYTE, int(variant), "=="), win)


def patch_recipient_letters(eb_bytes, triplets: dict) -> bytes:
    """Splice content arms for ``triplets`` = ``{variant: {"letter": txid, "announce": txid,
    "thanks": txid}}`` at EVERY classified letter-machinery site's convergence (read-mail display,
    delivery announce/display/thanks -- the first playtest proved patching one site is not enough:
    the delivery path has its own switches). Sites are patched in DESCENDING convergence order so
    earlier sites' recorded offsets stay valid. Every stock arm's jump targets its convergence (==
    the insert point), so it flows INTO the guards and falls through for stock variants."""
    sites = find_letter_displays(eb_bytes)
    if not any(s["role"] == "letter" for s in sites):
        raise ValueError("no Mognet letter-display switch found -- not a recipient moogle field?")
    for v in triplets:
        _mognet.check_variant(v)
        for s in sites:
            if v in s["arms"]:
                raise ValueError(f"variant {v} already has a stock arm (txid {s['arms'][v]})")
    out = eb_bytes
    for site in sorted(sites, key=lambda s: s["conv"], reverse=True):
        if site["role"] == "unknown":
            continue
        frag = b"".join(
            letter_content_guard(v, t[site["role"]], win_op=site["win_op"], win_flags=site["win_flags"])
            for v, t in sorted(triplets.items()) if t.get(site["role"]) is not None)
        if frag:
            out = edit.insert_in_function(out, site["entry"], site["tag"],
                                          site["conv"] - site["func_start"], frag)
    return out


def inbound_give_offer(variant: int, *, from_id: int, prompt_txid: int,
                       give_txid: int | None = None, to_id: int = _mognet.NEW_MOOGLE_ID) -> bytes:
    """The gated give-offer -- the donor becomes a SENDER of a letter to our moogle. One-shot +
    free-slot gated (``give_available_cond``); the offer is a two-row choice window whose Yes runs
    :func:`mognet.give_letter_body` (from = the DONOR's own roster id, to = ours). Declining
    re-offers on the next Mognet open; accepting sets the variant's give lock. No RETURN: control
    falls through into the donor's real Mognet flow either way."""
    offer = (opcodes.window_sync(_mognet.CHOICE_WINDOW, _mognet.CHOICE_FLAGS, int(prompt_txid))
             + _choice.switch_on_choice([
                 _mognet.give_letter_body(int(variant), int(to_id), from_id=int(from_id),
                                          give_txid=give_txid),
                 b""]))
    return _region.if_block(_mognet.give_available_cond(int(variant)), offer)


# the migration guard's own `Byte[1024] := 1` -- `05 F4 <1024 LE> 7D 01 00 2C 7F`. Every donor's
# Mognet section writes exactly this (the wipe-guard invariant: 58 shipping fields, only ever
# literal 1), making its FIRST occurrence a universal "the player chose Mognet and the guard has
# run" anchor -- INSIDE the player-chosen Mognet branch, before the mail business.
_GUARD_SET_STMT = (bytes([0x05, 0xF4]) + _mognet.GUARD_IDX.to_bytes(2, "little")
                   + bytes([0x7D, 0x01, 0x00, 0x2C, 0x7F]))


def patch_inbound_give(eb_bytes, *, variant: int, from_id: int, prompt_txid: int,
                       give_txid: int | None = None) -> bytes:
    """Splice the inbound give-offer INSIDE the donor's Mognet section -- right after the migration
    guard's ``Byte[1024] := 1`` write. The first playtest proved the talk-tag PREPEND wrong: the offer
    fired on every talk, before the moogle's own menu ("don't open directly to Mognet -- the player
    has to choose to enter"). Anchored after the guard write, the offer runs only when the player
    picked the Mognet row, and the donor's own exit cycle (back to the choice menu, the "I want mail,
    kupo!" nothing-hint) is untouched."""
    site = find_letter_display(eb_bytes)
    if site is None:
        raise ValueError("no Mognet letter-display switch found -- not a recipient moogle field?")
    eb = EbScript.from_bytes(eb_bytes)
    f = eb.entry(site["entry"]).func_by_tag(site["tag"])
    at = eb_bytes.find(_GUARD_SET_STMT, f.abs_start, f.abs_end)
    if at < 0:
        raise ValueError("no migration-guard write (Byte[1024] := 1) found in the Mognet function -- "
                         "cannot anchor the inbound offer")
    frag = inbound_give_offer(variant, from_id=from_id, prompt_txid=prompt_txid, give_txid=give_txid)
    return edit.insert_in_function(eb_bytes, site["entry"], site["tag"],
                                   at + len(_GUARD_SET_STMT) - f.abs_start, frag)


def _re_emit_entry(entry, text: str) -> str:
    """Re-emit one parsed MesEntry with new ``text``, preserving its exact STRT/TAIL."""
    tail = f"[TAIL={entry.tail}]" if entry.tail else ""
    return f"_[TXID={entry.txid}][STRT={entry.strt}]{tail}{text}[ENDN]"


DEFAULT_ANNOUNCE = "A letter for me?  Kupo!"
DEFAULT_THANKS_AT_DONOR = "What a nice letter, kupo!"
SPEAKER_DRESS = "[WDTH=0,0,6,0,-1][IMME][TEXT=0,0]"   # the stock announce/thanks dress: the moogle's
                                                       # own roster name + instant pop (field 1865 @45/47)
QUOTE_OPEN, QUOTE_CLOSE = "“", "”"


def _speaker_line(text: str) -> str:
    """The stock announce/thanks form: the speaker dress, then the curly-quoted line (the kit-wide
    SPEAKER FORM law -- name line + curly quotes, never 'Name:')."""
    return f"{SPEAKER_DRESS}\n{QUOTE_OPEN}{text}{QUOTE_CLOSE}"


def choice_prompt_text(prompt: str, yes: str = "Sure, kupo!", no: str = "Not now") -> str:
    """A REAL two-row choice window text -- ``[PCHC=2,1]`` + the prompt + the ``[CHOO]`` rows. The
    first playtest proved a bare prompt line auto-resolves (switch_on_choice reads a stale selection
    -> the offer 'accepts itself'); the choice rows are load-bearing, not dressing."""
    from .text import CHOICE_OPEN, CHOICE_INDENT
    return ("[PCHC=2,1][IMME]" + str(prompt) + CHOICE_OPEN
            + ("\n" + CHOICE_INDENT).join((str(yes), str(no))))


def donor_mes_additions(stock_mes_body: str, *, roster_name: str | None = None,
                        letters: dict | None = None, prompts: list | None = None) -> tuple:
    """Build the ADDITIVE ``.mes`` override for a donor field's block: re-emitted ``[TXID=0]`` with the
    42nd roster row appended (when ``roster_name``), plus -- per ``letters`` entry ``{variant: {"letter":
    body, "announce": line?, "thanks": line?}}`` (a bare string = the letter body with default
    announce/thanks) -- a TRIPLET of new entries above the stock max txid: the announce and thanks in
    the stock speaker form (STRT/TAIL copied from the donor's own announce/thanks windows -- the
    window-geometry law) and the letter through the stock letter template. ``prompts`` = extra window
    texts (the inbound offer, already choice-formatted by the caller). Returns
    ``(mes_text, {variant: {"announce": txid, "letter": txid, "thanks": txid}}, [prompt_txids])``.

    The override merges per-txid over the stock block (FF9TextTool is cumulative), so ONLY the touched
    txids ship -- nothing else is redefined. Stock text appears ONLY in the re-emitted entry 0, which
    is why this runs at deploy time from the user's own install (provenance)."""
    from .. import dialogue as _dialogue
    from .text import mes_entry
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
    letter_txids, prompt_txids = {}, []
    if letters:
        # per-field window geometry, copied from the donor's own entries (the window-geometry law):
        # the letter STRT from a [WDTH=0,55-opening full-screen letter; announce/thanks STRT+TAIL
        # from a speaker-dressed window
        l_strt, at_strt, at_tail = None, None, "UPR"
        for e in entries.values():
            if l_strt is None and e.text.startswith("[WDTH=0,55") and e.strt:
                l_strt = tuple(int(v) for v in e.strt.split(","))
            if at_strt is None and e.text.startswith(SPEAKER_DRESS) and e.strt:
                at_strt = tuple(int(v) for v in e.strt.split(","))
                at_tail = e.tail or "UPR"
        for v in sorted(letters):
            spec = letters[v] if isinstance(letters[v], dict) else {"letter": letters[v]}
            tri = {}
            parts.append(mes_entry(_speaker_line(spec.get("announce", DEFAULT_ANNOUNCE)),
                                   next_txid, strt=at_strt or (240, 3), tail=at_tail))
            tri["announce"] = next_txid
            next_txid += 1
            parts.append(mes_entry(_mognet.letter_entry_text(spec["letter"]), next_txid,
                                   strt=l_strt or (10, 1), tail=""))
            tri["letter"] = next_txid
            next_txid += 1
            parts.append(mes_entry(_speaker_line(spec.get("thanks", DEFAULT_THANKS_AT_DONOR)),
                                   next_txid, strt=at_strt or (136, 3), tail=at_tail))
            tri["thanks"] = next_txid
            next_txid += 1
            letter_txids[v] = tri
    for p in (prompts or []):
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
        prompts.append(choice_prompt_text(inbound["prompt"],
                                          inbound.get("yes", "Sure, kupo!"),
                                          inbound.get("no", "Not now")))
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
