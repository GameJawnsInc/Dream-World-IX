"""Mognet -- author a NEW moogle identity into FF9's real letter network.

FF9's Mognet is driven ENTIRELY by field bytecode + text: no C# letter logic exists (CaptionType.Mognet
is just a window skin), moogle identity is a plain byte indexing the 41-name roster in text entry 0, and
nothing anywhere bounds that byte against 41 -- every routing comparison in all 818 fields is equality
(B_EQ/B_NE, zero range checks). So a custom field's save Moogle can join the network as the 42nd identity
(id :data:`NEW_MOOGLE_ID`) by speaking the same byte protocol. This module emits that protocol.

THE MAILBOX (gEventGlobal; decoded from fields 300/407/1102 and LIVE-VERIFIED 2026-07-18 against a real
save -- delivering Kuppo's letter to Kupo zeroed slot 0's quad and ticked the counter 12->13):

    Byte[1024]        init/migration guard. Byte-one once the mailbox has ever been used. If 0 while any
                      slot is occupied, the next real save moogle ERASES all 12 slot bytes ("Old letter
                      data. Erasing..."). Every write path here sets it; never write any other value.
    Byte[1032]        lifetime letters-DELIVERED counter (the ACCEPT path post-increments it; Mognet
                      Central reads it for "Thanks for delivering [NUMB] letters!").
    Byte[1033]        Stiltzkin's sub-quest tally. The kit NEVER writes it.
    Byte[1034+4k]     slot k in {0,1,2}: +0 occupied, +1 variant, +2 FROM moogle id, +3 TO moogle id.
    bits 8376-8439    GIVE-side variant one-shot locks ("this letter was already handed out"),
    bits 8440-8503    READ-side locks -- bit(v) = anchor + 8*(v//8) - (v%8), anchors 8383/8447. The
                      inverse is pinned against live data (reading variants 19/22/33 set exactly bytes
                      1057 bit4 / 1057 bit1 / 1059 bit6). Inside the reserved 8376-8511 band; the kit's
                      custom flags start at 8712 (flags.FIRST_SAFE_FLAG), so no collision either way.
    Byte[1064+row]    the READ-MAIL menu payload: row VARIANT / row SENDER, rebuilt from the read-locks
    Byte[1079+row]    on every Mognet open (rows 0..9). SCRATCH semantically, but save-persisted --
                      which is why bits 8512-8711 are reserved (flags.READMAIL_PAYLOAD_LO/HI).

THE SAFETY DISCIPLINE (the one irreversible risk is a player's real letters; an adversarial review
marked "cannot corrupt" UNPROVEN precisely because it depended on unwritten code, so the invariants are
STRUCTURAL here, not documentation):

  * :func:`give_letter_body` prepends ``Byte[1024] = 1`` itself -- the wipe-guard precondition cannot be
    forgotten by a caller, and the write is idempotent (58 shipping fields only ever write literal 1).
  * A give NEVER overwrites an occupied slot: the body is a first-EMPTY-slot chain (slot checked empty
    immediately before its quad is written -- the same invariant as the donor's recount-then-switch,
    without the transient Map counter a naive port could forget to refresh).
  * A FULL mailbox refuses with ZERO mailbox writes (the donor's default arm does exactly nothing).
  * A delivery COMPACTS: higher quads shift down, the vacated tail quad is zeroed -- a hole would
    desynchronise every real moogle's slot count from the data permanently.
  * The tests EXECUTE these bodies in a mini-VM over a simulated gEventGlobal and assert the invariants
    on the resulting bytes -- not on the emitter's structure.

Letter VARIANT ids are the real ceiling (not the moogle id): the one-shot locks are 64-bit tables, so a
variant must be < 64, and shipped content uses ids up to ~48 -- custom letters take 49..63
(:data:`SAFE_VARIANTS`). The roster text itself (a 42nd NAME) ships via :func:`roster_extend` over the
install-derived entry-0 table -- see docs/PROVENANCE.md; the kit does not embed the 41 names.

READ-MAIL (decoded 2026-07-19, donors 115/300/418/1102 + a 58-field census, one invariant template):
the moogle re-reads its OWN received letters. Stock's machine, which this module now speaks verbatim:
each field hardcodes up to 10 rows, row k gated on ``read_lock_bit(variant_k)`` (the bit the ARRIVAL
paths set -- accept-delivery or a scenario auto-arrival; the accept path here has set it since rung 4);
an open rebuilds the payload (``Byte[1064+k]`` = variant, mask ``|= 1<<k``, ``Byte[1079+k]`` = sender,
in that donor order), masks a "which letter" choice window with it, and a pick re-displays that
variant's letter through the SAME :func:`letter_display` bracket. A read is PURE: no lock write, no
mailbox write -- a known letter is re-readable forever. The whole 3-row "What do you want to do"
submenu (Give <name> a letter / Read mail / Cancel) only appears when a delivery is pending OR a
letter is known -- the donor gates it on a computed bits word, and so do we.

What this module deliberately does NOT do yet: inbound mail from REAL moogles (their TO-recipient is a
per-field immediate constant -- reaching our moogle means verbatim-forking a donor field and repointing
that constant) and surfacing OUR letters in a REAL moogle's read-mail list (their row tables are
hand-authored per field; our delivered variant sets its lock bit harmlessly but no stock row reads it).
Both are the donor-fork class, a later opt-in rung.
"""
from __future__ import annotations

import re

from ..eb import opcodes
from . import choice as _choice
from . import region as _region

# --- identity ---------------------------------------------------------------------------------------
ROSTER_SIZE = 41          # the shipping [TBLE=] roster rows (ids 0..40)
NEW_MOOGLE_ID = 41        # the 42nd row -- the first free identity byte
# A save moogle does NOT speak under a literal name: stock loads its own roster id into text var 0
# (`SetTextVariable(0, <my id>)`) and every one of its windows uses `[TEXT=0,0]` as the speaker, which
# renders that row of the moogle-name table (field 300 txids 3/4/5/6 all do; its Init seeds the id and
# its loop refreshes the var). So the identity, not a hardcoded string, is what talks -- and the name
# tracks the roster. `[savepoint.mognet]` uses this by default; an explicit `speaker` overrides it.
VAR_SPEAKER = "[TEXT=0,0]"

# --- the mailbox layout (all gEventGlobal byte indices) ---------------------------------------------
GUARD_IDX = 1024          # wipe-guard; must be 1 before any mailbox byte is touched
DELIVERED_IDX = 1032      # lifetime delivered counter -- POST-INCREMENT only
STILTZKIN_IDX = 1033      # Stiltzkin's tally -- named so nothing here writes it by accident
SLOT0 = 1034
NSLOTS = 3
SLOTSZ = 4                # +0 occupied  +1 variant  +2 FROM  +3 TO

# --- the variant one-shot lock tables ---------------------------------------------------------------
GIVE_LOCK_ANCHOR = 8383   # bits 8376-8439 (bytes 1047-1054)
READ_LOCK_ANCHOR = 8447   # bits 8440-8503 (bytes 1055-1062)
VARIANT_LIMIT = 64        # the lock tables are 64 bits -- a variant id must be < 64
SHIPPED_VARIANT_MAX = 48  # observed high-water across shipping content
SAFE_VARIANTS = range(SHIPPED_VARIANT_MAX + 1, VARIANT_LIMIT)   # 49..63 -- the custom band

# expression tokens beyond region's set (values from eb/_exprtable.py, donor-byte verified)
_T_NE = 0x21              # B_NE
_T_ANDAND = 0x27          # B_ANDAND
_T_OROR = 0x28            # B_OROR
_T_POST_PLUS = 0x04       # B_POST_PLUS -- the donor's Byte[1032]++ (field 300 @6387: 05 f4 08 04 04 7f)


def slot_addr(k: int, part: int = 0) -> int:
    """gEventGlobal index of slot ``k``'s byte: part 0 occupied / 1 variant / 2 FROM / 3 TO."""
    if not 0 <= k < NSLOTS:
        raise ValueError(f"mailbox slot must be 0..{NSLOTS - 1}, got {k}")
    return SLOT0 + k * SLOTSZ + part


def _lock_bit(anchor: int, variant: int) -> int:
    if not 0 <= variant < VARIANT_LIMIT:
        raise ValueError(f"letter variant must be 0..{VARIANT_LIMIT - 1} (the lock tables are 64-bit), "
                         f"got {variant}")
    return anchor + 8 * (variant // 8) - (variant % 8)


def give_lock_bit(variant: int) -> int:
    """The GIVE-side one-shot lock bit for ``variant`` -- set when the letter is handed out."""
    return _lock_bit(GIVE_LOCK_ANCHOR, variant)


def read_lock_bit(variant: int) -> int:
    """The READ-side one-shot lock bit for ``variant`` -- set when the letter is read/completed."""
    return _lock_bit(READ_LOCK_ANCHOR, variant)


def check_variant(variant: int, *, allow_shipped: bool = False) -> int:
    """Validate a custom letter's variant id: < 64 always; and outside the shipped band unless
    ``allow_shipped`` (re-using a shipped id would collide with that letter's one-shot locks -- the
    give-lock says "already handed out", so a player who did that quest never sees ours)."""
    v = int(variant)
    _lock_bit(GIVE_LOCK_ANCHOR, v)                     # range check (raises)
    if v <= SHIPPED_VARIANT_MAX and not allow_shipped:
        raise ValueError(
            f"letter variant {v} is in the SHIPPED band (<= {SHIPPED_VARIANT_MAX}) -- its one-shot locks "
            f"collide with a real letter's. Pick one of {SAFE_VARIANTS.start}..{SAFE_VARIANTS.stop - 1}, "
            f"or pass allow_shipped=True if you really mean to alias shipped state.")
    return v


def _check_id(name: str, i: int) -> int:
    i = int(i)
    if not 0 <= i <= 255:
        raise ValueError(f"{name} must be a byte (0..255), got {i}")
    return i


# --------------------------------------------------------------------------- expression pieces ---
def _push_byte(idx: int) -> bytes:
    return _region._push_var(_region.GLOB_BYTE, idx)


def _const(v: int) -> bytes:
    return bytes([_region.T_CONST]) + int(v).to_bytes(2, "little")


def _set_byte(idx: int, value: int) -> bytes:
    return _region.set_var(_region.GLOB_BYTE, idx, value)


def _copy_byte(dst: int, src: int) -> bytes:
    """``Global.Byte[dst] = Global.Byte[src]`` -- the donor's compaction idiom, byte-for-byte
    (field 300 @7019: ``05 f4 0a 04 f4 0e 04 2c 7f`` = ``B[1034] <- B[1038]``)."""
    return (bytes([_region.EXPR_OP]) + _push_byte(dst) + _push_byte(src)
            + bytes([_region.T_ASSIGN, _region.T_END]))


def _post_inc_byte(idx: int) -> bytes:
    """``Global.Byte[idx]++`` (donor: field 300 @6387 -- the ONLY way shipping code touches 1032)."""
    return bytes([_region.EXPR_OP]) + _push_byte(idx) + bytes([_T_POST_PLUS, _region.T_END])


def _set_lock(bit: int) -> bytes:
    return _region.set_var(_region.GLOB_BOOL, bit, 1)


def slot_empty_cond(k: int) -> bytes:
    """``if (slot k unoccupied)`` -- ``05 <occ> const(0) EQ 7F``."""
    return (bytes([_region.EXPR_OP]) + _push_byte(slot_addr(k)) + _const(0)
            + bytes([_region.T_EQ, _region.T_END]))


def slot_addressed_to_cond(k: int, my_id: int) -> bytes:
    """``if (slot k occupied AND its TO == my_id)`` -- the accept condition, donor-shaped
    (occupied != 0, then TO == id, then ANDAND)."""
    return (bytes([_region.EXPR_OP])
            + _push_byte(slot_addr(k)) + _const(0) + bytes([_T_NE])
            + _push_byte(slot_addr(k, 3)) + _const(_check_id("my_id", my_id)) + bytes([_region.T_EQ])
            + bytes([_T_ANDAND, _region.T_END]))


def give_available_cond(variant: int) -> bytes:
    """``if (this letter not yet handed out AND a slot is free)`` -- gates the moogle's OFFER (the menu
    row / greet line). The lock read makes the offer one-shot save-persistently; the free-slot check
    mirrors the donor's ``count < 3`` offer gate."""
    v = check_variant(variant, allow_shipped=True)     # gate rows may reference any variant; writes stay strict
    return (bytes([_region.EXPR_OP])
            + _region._push_var(_region.GLOB_BOOL, give_lock_bit(v)) + bytes([_region.T_NOT])
            + _push_byte(slot_addr(0)) + _const(0) + bytes([_region.T_EQ])
            + _push_byte(slot_addr(1)) + _const(0) + bytes([_region.T_EQ, _T_OROR])
            + _push_byte(slot_addr(2)) + _const(0) + bytes([_region.T_EQ, _T_OROR])
            + bytes([_T_ANDAND, _region.T_END]))


def accept_available_cond(my_id: int = NEW_MOOGLE_ID) -> bytes:
    """``if (any slot holds a letter addressed to my_id)`` -- gates the "give <name> a letter" menu row,
    the donor's [PCHM] mask condition."""
    mid = _check_id("my_id", my_id)

    def pair(k):
        return (_push_byte(slot_addr(k)) + _const(0) + bytes([_T_NE])
                + _push_byte(slot_addr(k, 3)) + _const(mid) + bytes([_region.T_EQ, _T_ANDAND]))

    return (bytes([_region.EXPR_OP]) + pair(0) + pair(1) + bytes([_T_OROR])
            + pair(2) + bytes([_T_OROR, _region.T_END]))


# --------------------------------------------------------------------------- the write paths ---
def migration_guard(notice_txid: int | None = None, *, window: int = 0, flags: int = 0) -> bytes:
    """The donor's mailbox init/migration guard, byte-shaped on field 300 @5638-5796::

        if (Byte[1024] < 1  AND  (slot0 occ != 0 OR slot1 occ != 0 OR slot2 occ != 0)) {
            [Window(notice)]                  # "Old letter data. Erasing..." in the donor
            Byte[1034..1045] = 0              # all 12 slot bytes, ascending
        }
        Byte[1024] = 1                        # unconditional -- the only write shipping code makes

    Run this at the top of any Mognet interaction (the menu emitter does). If the player reaches OUR
    moogle first on a fresh save, our copy is the one that must migrate correctly. The condition's RPN
    is token-identical to the donor's (pinned by test)."""
    cond = (bytes([_region.EXPR_OP])
            + _push_byte(GUARD_IDX) + _const(1) + bytes([_region.T_LT])
            + _push_byte(slot_addr(0)) + _const(0) + bytes([_T_NE])
            + _push_byte(slot_addr(1)) + _const(0) + bytes([_T_NE, _T_OROR])
            + _push_byte(slot_addr(2)) + _const(0) + bytes([_T_NE, _T_OROR])
            + bytes([_T_ANDAND, _region.T_END]))
    erase = b"".join(_set_byte(SLOT0 + i, 0) for i in range(NSLOTS * SLOTSZ))   # 1034..1045 ascending
    body = (opcodes.window_sync(window, flags, notice_txid) if notice_txid is not None else b"") + erase
    return _region.if_block(cond, body) + _set_byte(GUARD_IDX, 1)


def _give_arm(k: int, variant: int, from_id: int, to_id: int, give_txid, window, flags) -> bytes:
    """Write slot ``k``'s quad -- donor order occupied / FROM / TO / variant (field 300 @9981-10013) --
    then the give-side one-shot lock, then the optional handover line."""
    return (_set_byte(slot_addr(k), 1)
            + _set_byte(slot_addr(k, 2), from_id)
            + _set_byte(slot_addr(k, 3), to_id)
            + _set_byte(slot_addr(k, 1), variant)
            + _set_lock(give_lock_bit(variant))
            + (opcodes.window_sync(window, flags, give_txid) if give_txid is not None else b""))


def give_letter_body(variant: int, to_id: int, *, from_id: int = NEW_MOOGLE_ID,
                     give_txid: int | None = None, full_txid: int | None = None,
                     window: int = 1, flags: int = 128, allow_shipped_variant: bool = False) -> bytes:
    """Our moogle hands the player a letter: FROM ``from_id`` (default: the new identity) TO ``to_id``
    (a real moogle delivers it with no engine change -- outbound is the proven direction).

    Emits::

        Byte[1024] = 1                                   # the wipe-guard invariant, locally guaranteed
        if slot0 empty:      write quad0 ; lock ; [line]
        elif slot1 empty:    write quad1 ; lock ; [line]
        elif slot2 empty:    write quad2 ; lock ; [line]
        else:                [full line]                 # mailbox full -> NO mailbox write at all

    The first-empty chain checks each slot immediately before writing it, so an occupied slot can never
    be overwritten -- the invariant behind the donor's recount-then-switch, made unconditional. The
    caller gates the OFFER on :func:`give_available_cond` (one-shot + free-slot); this body is the
    structural backstop if it ever runs anyway."""
    v = check_variant(variant, allow_shipped=allow_shipped_variant)
    fid, tid = _check_id("from_id", from_id), _check_id("to_id", to_id)
    full_arm = opcodes.window_sync(window, flags, full_txid) if full_txid is not None else b""
    chain = full_arm
    for k in reversed(range(NSLOTS)):                  # innermost else first: 2, then 1, then 0
        chain = _region.if_else(slot_empty_cond(k), _give_arm(k, v, fid, tid, give_txid, window, flags),
                                chain)
    return _set_byte(GUARD_IDX, 1) + chain


def _consume_arm(k: int, variants, thanks_txid, window, flags, my_id, letter_txids) -> bytes:
    """Consume slot ``k``: counter, the sender/recipient text vars, thanks line, then per-variant the
    LETTER display + read-lock, then the donor's compaction (field 300 @6990-7126): shift every higher
    quad DOWN one (order occupied/FROM/TO/variant per quad), then zero the top quad -- never a hole."""
    out = _post_inc_byte(DELIVERED_IDX)
    # the stock letter-header convention (field 1865 entry 49, "From [TEXT=0,1] to [TEXT=0,0]"):
    # text var 1 <- the slot's FROM byte (the sender), text var 0 <- our own id (the recipient). The
    # thanks line reads the same slots, so they are set whether or not a letter is authored.
    from_expr = _push_byte(slot_addr(k, 2)) + bytes([_region.T_END])
    out += opcodes.encode(0x66, 1, from_expr, arg_flags=0b10)         # SetTextVariable(1, {FROM})
    out += opcodes.set_text_variable(0, my_id)
    if thanks_txid is not None:
        out += opcodes.window_sync(window, flags, thanks_txid)
    letter_txids = letter_txids or {}
    for v in variants:
        cond = (bytes([_region.EXPR_OP]) + _push_byte(slot_addr(k, 1)) + _const(v)
                + bytes([_region.T_EQ, _region.T_END]))
        arm = (letter_display(letter_txids[v]) if v in letter_txids else b"")
        out += _region.if_block(cond, arm + _set_lock(read_lock_bit(v)))
    parts = (0, 2, 3, 1)                               # occupied, FROM, TO, variant -- donor copy order
    for dst in range(k, NSLOTS - 1):
        out += b"".join(_copy_byte(slot_addr(dst, p), slot_addr(dst + 1, p)) for p in parts)
    out += b"".join(_set_byte(slot_addr(NSLOTS - 1, p), 0) for p in parts)
    return out


def accept_letter_body(variants, *, my_id: int = NEW_MOOGLE_ID, thanks_txid: int | None = None,
                       nothing_txid: int | None = None, window: int = 1, flags: int = 128,
                       letter_txids: dict | None = None) -> bytes:
    """Our moogle takes delivery of a letter addressed TO it (the player picked "give <name> a letter").

    ``variants`` is the set of letter variant ids authored as deliverable to this moogle -- known at
    build time, so the read-side lock is set per-variant with literal bits (the donor's 64-arm switch
    collapses to an if per authored variant). For each slot in order: if occupied AND TO == my_id ->
    consume it (counter++, sender/recipient text vars, optional thanks line, the LETTER display when
    ``letter_txids`` carries that variant's content, read-lock, compaction). If no slot matches, the
    optional ``nothing_txid`` line shows. Byte[1033] (Stiltzkin) is never touched."""
    vs = [check_variant(v, allow_shipped=True) for v in variants]
    nothing = opcodes.window_sync(window, flags, nothing_txid) if nothing_txid is not None else b""
    chain = nothing
    for k in reversed(range(NSLOTS)):
        chain = _region.if_else(slot_addressed_to_cond(k, my_id),
                                _consume_arm(k, vs, thanks_txid, window, flags, my_id, letter_txids),
                                chain)
    return _set_byte(GUARD_IDX, 1) + chain


# --- the READ-MAIL payload (the stock scratch band our rows write, byte-faithfully) -----------------
# Byte[1064+k] = row k's VARIANT, Byte[1079+k] = row k's SENDER roster id, k = 0..9 -- rebuilt on every
# Mognet open from the read-locks (donor idiom: `if (lock) { 1064+k = v; mask |= 1<<k; 1079+k = s }`,
# field 115 @test2_37:1246-1265 / field 1102 @test2_300:681-690). Bits 8512-8711 are reserved for
# exactly this (flags.READMAIL_PAYLOAD_LO/HI) -- our writes land where stock's do.
PAYLOAD_VARIANT_BASE = 1064
PAYLOAD_SENDER_BASE = 1079
PAYLOAD_ROWS = 10         # the engine-side row budget (10 slots + the mask's cancel bit)

# Default wording -- original phrasing, not Square-Enix text (docs/PROVENANCE.md; "kupo" is a word,
# not a quoted line). Every one is overridable per [savepoint.mognet] key of the same lowercase name.
DEFAULT_MOGNET_ROW = "Mognet"
DEFAULT_MENU_PROMPT = "What can I do for you, kupo?"
DEFAULT_ACCEPT_ROW = "Give {name} a letter"     # submenu row 0 = the ACCEPT (hand a carried letter over)
DEFAULT_READ_ROW = "Read mail"                  # submenu row 1
DEFAULT_MENU_CANCEL = "Cancel"                  # submenu row 2 (B backs out here too)
DEFAULT_READ_PROMPT = "Which letter, kupo?"
DEFAULT_ARRIVE = "A letter came for me, kupo!"
DEFAULT_ACCEPT_PROMPT = "That letter is addressed to me, kupo! May I have it?"
DEFAULT_ACCEPT_YES, DEFAULT_ACCEPT_NO = "Hand it over", "Keep it"
DEFAULT_THANKS = "A letter from [TEXT=0,1], kupo! Thank you!"   # [TEXT=0,1] = roster[sender] -- see LETTER_HEADER
DEFAULT_GIVE_PROMPT = "Would you deliver my letter to {to}, kupo?"
DEFAULT_GIVE_YES, DEFAULT_GIVE_NO = "Take the letter", "Not now"
DEFAULT_GIVE_LINE = "Take good care of it, kupo!"
DEFAULT_NOTHING = "No mail today, kupo..."
DEFAULT_ERASE = "This old mail ledger is unreadable, kupo. Starting fresh!"


def resolve_moogle_id(to, roster_names, *, self_id: int = NEW_MOOGLE_ID, self_name: str | None = None):
    """Resolve a letter's ``to`` (a roster NAME or a numeric id) to the identity byte. ``roster_names``
    is the full row list -- the 41 install names plus any custom appendees -- so a custom moogle can
    address real and custom recipients alike. Self-mail is refused either way (a letter FROM us TO us
    would satisfy our own accept condition the moment it was given)."""
    if isinstance(to, bool):
        raise ValueError(f"mognet give.to must be a moogle name or id, got {to!r}")
    if isinstance(to, int):
        tid = _check_id("give.to", to)
        if tid == self_id:
            raise ValueError(f"mognet give.to = {tid} is this moogle itself -- a moogle cannot mail itself")
        return tid
    name = str(to)
    if self_name is not None and name == self_name:
        raise ValueError(f"mognet give.to = {name!r} is this moogle itself -- a moogle cannot mail itself")
    try:
        return list(roster_names).index(name)
    except ValueError:
        known = ", ".join(list(roster_names)[:8]) + ", ..."
        raise ValueError(f"mognet give.to = {name!r} is not a moogle on the roster ({known})") from None


def roster_names(entry0_text: str) -> list:
    """The row list out of a roster table text (see :func:`roster_extend` for the format)."""
    m = _TBLE_RE.match(entry0_text)
    if not m:
        raise ValueError("not a [TBLE=...] roster table")
    return m.group(3).split("\n")


# The moogle's CHOICE windows: slot 2, flags 8 -- flags bit "4: mognet format" is what paints the
# MOGNET caption on the frame (EventEngine.DoEventCode.cs:413; field 300 opens every moogle menu as
# WindowAsync(2, 8, ...)). Statement lines (thanks / handover / nothing) use the plain dialogue window
# (1, 128), which the give/accept bodies already default to.
CHOICE_WINDOW = 2
CHOICE_FLAGS = 8

# --- the MAIL-STATUS box (the persistent bottom-left "You have a letter from X to Y") -----------------
# Decoded from field 300 @5929-6153: on opening Mognet the moogle recounts the slots, loads text vars
# 2..7 with the three slots' FROM/TO bytes, and WindowAsync(5, 8, <entry>)s one of four entries (none /
# 1 / 2 / 3 letters) -- ASYNC with [TIME=-1], so the box sits under the menus until CloseWindow(5)
# (field 1865 closes it right before the letter display). The stock block carries two near-identical
# sets (11-14 / 15-18, toggled by a scratch bit); the [IMME] set is the visible one and the one we ship.
STATUS_WINDOW = 5           # the same slot every moogle field uses for the status box
_SENDER = "[68C0D8][HSHD][TEXT=0,{f}][C8C8C8][HSHD]"     # a name, in the mognet blue
_LINE = "You have a letter from " + _SENDER.format(f="{f}") + " to " + _SENDER.format(f="{t}")
DEFAULT_STATUS_NONE = "You have no mail"
# entry shapes: the stock [WDTH] width tables reference exactly the value slots each line renders
STATUS_TEMPLATES = (
    "[IMME][FEED=4]{none}[FEED=4][TIME=-1]",
    "[WDTH=0,160,6,2,6,3,-1][IMME][FEED=4]" + _LINE.format(f=2, t=3) + "[FEED=4][TIME=-1]",
    ("[WDTH=0,160,6,2,6,3,-1,0,160,6,4,6,5,-1][IMME][FEED=4]" + _LINE.format(f=2, t=3)
     + "[FEED=4]\n[FEED=4]" + _LINE.format(f=4, t=5) + "[FEED=4][TIME=-1]"),
    ("[WDTH=0,160,6,2,6,3,-1,0,160,6,4,6,5,-1,0,160,6,6,6,7,-1][IMME][FEED=4]" + _LINE.format(f=2, t=3)
     + "[FEED=4]\n[FEED=4]" + _LINE.format(f=4, t=5) + "[FEED=4]\n[FEED=4]" + _LINE.format(f=6, t=7)
     + "[FEED=4][TIME=-1]"),
)


# THE GEOMETRY IS PART OF THE ENTRY. The stock status entries carry their own [STRT] + [TAIL=LOL]
# (lower-left) -- that placement, not the window slot, is what pins the box bottom-left. Read from the
# real block (entries 11-14: strt 100,1 / 160,1 / 160,2 / 160,3, tail LOL). Shipping the text with the
# dialogue defaults ((10,1) / no tail) mis-places it -- the third instance of this exact mistake in the
# kit's history (the chest box and the ATE title both landed top-right the same way).
STATUS_STRT = ((100, 1), (160, 1), (160, 2), (160, 3))
STATUS_TAIL = "LOL"


def status_entry_texts(none_text: str = DEFAULT_STATUS_NONE) -> list:
    """The four status-box entries (0/1/2/3 letters held) as ``(text, strt, tail)`` -- text AND the
    stock geometry, which the caller must ship together. Only the no-mail wording is authorable; the
    list lines are structural templates whose [WDTH]/[TEXT] slots must match :func:`mail_status_window`'s
    text-var loads."""
    texts = [STATUS_TEMPLATES[0].format(none=str(none_text))] + list(STATUS_TEMPLATES[1:])
    return [(t, STATUS_STRT[i], STATUS_TAIL) for i, t in enumerate(texts)]


def mail_status_window(txids) -> bytes:
    """Open the mail-status box: text vars 2..7 <- the slots' FROM/TO bytes, then the right entry by
    occupancy. ``txids`` = the four entry ids in held-count order 0..3. Compaction keeps slots filled
    from 0, so the donor's count scratch collapses to a nested check: slot 2 occupied => 3 letters,
    else slot 1 => 2, else slot 0 => 1, else none."""
    if len(txids) != 4:
        raise ValueError(f"mail_status_window needs 4 txids (0..3 letters held), got {len(txids)}")
    out = b""
    for var, (k, part) in enumerate(((0, 2), (0, 3), (1, 2), (1, 3), (2, 2), (2, 3)), start=2):
        expr = _push_byte(slot_addr(k, part)) + bytes([_region.T_END])
        out += opcodes.encode(0x66, var, expr, arg_flags=0b10)        # SetTextVariable(var, {slot byte})
    def occ(k):
        return (bytes([_region.EXPR_OP]) + _push_byte(slot_addr(k)) + _const(0)
                + bytes([_T_NE, _region.T_END]))
    show = [opcodes.window_async(STATUS_WINDOW, CHOICE_FLAGS, t) for t in txids]
    return out + _region.if_else(occ(2), show[3],
                                 _region.if_else(occ(1), show[2],
                                                 _region.if_else(occ(0), show[1], show[0])))


# --- the LETTER itself (the full-screen frameless read) -----------------------------------------------
# Decoded from field 1865 (Alexandria/Steeple, Kupo) @6191-6310: letter content is ONE ordinary text
# entry in the RECIPIENT's field block, shown in window 3 with flags 16 (the "hide window" bit -- no
# frame, over the letter art), selected by an op_06 switch on the letter VARIANT with HARDCODED arms
# (19->46, 22->49, 33->52, 48->63 there) whose default skips the window -- but the fade bracket runs
# regardless, which is exactly the observed "faded in, no content, faded out" for our variant 56 at a
# stock recipient. So content at STOCK recipients needs their .eb patched (the inbound-fork class,
# deferred); content at OUR OWN moogle is fully authorable, and that is what ships here.
LETTER_WINDOW = 3
LETTER_FLAGS = 16
# The stock letter-entry template (field 1865 entry 49): the widths table, the moogle portrait built
# from icon pieces 27/28/29, then the colored "From <sender> to <recipient>" line -- sender = text var
# 1, recipient = text var 0, both rendered through roster table 0. Formatting tags, not prose.
LETTER_HEADER = ("[WDTH=0,55,6,1,6,0,-1][SPED=255][ICON=27][XTAB=0][YADD=16][ICON=28][YADD=8][XTAB=0]"
                 "[ICON=29][YSUB=8][FEED=4][SPED=3][68C0D8][HSHD]From [TEXT=0,1] to [TEXT=0,0]"
                 "[C8C8C8][HSHD]")


def letter_entry_text(body: str) -> str:
    """A complete letter text entry: the stock header template + a blank line + the authored body
    (author-controlled line breaks; the stock letters hand-break every line)."""
    return LETTER_HEADER + "\n\n" + str(body)


def letter_display(letter_txid: int) -> bytes:
    """The faithful letter presentation, byte-shaped on field 1865 @6191-6310::

        CalculateScreenPosition(250) ; FadeFilter(2, 24, 255, 220,220,250)   # the parchment glow, in
        Wait(16)
        WindowAsync(3, 16, letter)                                           # the frameless letter
        RaiseWindows ; WaitWindow(3)                                         # the player reads + closes
        CalculateScreenPosition(250) ; FadeFilter(7, 16, 255, 0,0,0)         # restore
        Wait(16)

    The donor passes the fade intensity through a Map scratch var holding 255; we pass the literal."""
    return (opcodes.encode(0x21, STATUS_WINDOW)             # the status box yields to the letter (1865 @6177)
            + opcodes.encode(0xA9, 250)                     # CalculateScreenPosition(player)
            + opcodes.encode(0xEC, 2, 24, 255, 220, 220, 250)
            + opcodes.wait(16)
            + opcodes.window_async(LETTER_WINDOW, LETTER_FLAGS, letter_txid)
            + opcodes.encode(0x8E)                          # RaiseWindows
            + opcodes.encode(0x54, LETTER_WINDOW)           # WaitWindow
            + opcodes.encode(0xA9, 250)
            + opcodes.encode(0xEC, 7, 16, 255, 0, 0, 0)
            + opcodes.wait(16))


# --------------------------------------------------------------------------- READ-MAIL ---
def read_available_cond(variants) -> bytes:
    """``if (any of these letters is known)`` -- an OR over the READ-lock bits, the same bits the
    row-population tests. Gates the whole Read-mail lane (and its submenu row's mask bit)."""
    vs = [check_variant(v, allow_shipped=True) for v in variants]
    if not vs:
        raise ValueError("read_available_cond needs at least one variant")
    t = _region._push_var(_region.GLOB_BOOL, read_lock_bit(vs[0]))
    for v in vs[1:]:
        t += _region._push_var(_region.GLOB_BOOL, read_lock_bit(v)) + bytes([_T_OROR])
    return bytes([_region.EXPR_OP]) + t + bytes([_region.T_END])


def read_row_population(rows) -> bytes:
    """The donor's per-row payload rebuild, byte-shaped (field 115 @1246-1265): the mask scratch seeds
    with the CANCEL row's bit (index ``len(rows)``, always available), then per row k, gated on that
    variant's READ lock: ``Byte[1064+k] = variant ; mask |= 1<<k ; Byte[1079+k] = sender`` -- variant
    first, sender last, exactly the donor's write order. ``rows`` = ``[(variant, sender_id), ...]`` in
    menu order (row index IS list position -- static, like every stock field's)."""
    if len(rows) > PAYLOAD_ROWS:
        raise ValueError(f"read-mail supports at most {PAYLOAD_ROWS} rows, got {len(rows)}")
    out = _region.set_var(_region.GLOB_UINT16, _region.MASK_SCRATCH_IDX, 1 << len(rows))
    for k, (v, sender) in enumerate(rows):
        vv = check_variant(v, allow_shipped=True)
        body = (_set_byte(PAYLOAD_VARIANT_BASE + k, vv)
                + _region.or_var(_region.GLOB_UINT16, _region.MASK_SCRATCH_IDX, 1 << k)
                + _set_byte(PAYLOAD_SENDER_BASE + k, _check_id("sender", sender)))
        out += _region.if_block(_region.cond_truthy(_region.GLOB_BOOL, read_lock_bit(vv)), body)
    return out


def read_mail_body(rows, prompt_txid: int, letter_txids, *, window: int = CHOICE_WINDOW,
                   flags: int = CHOICE_FLAGS) -> bytes:
    """The Read-mail pick: rebuild the payload + mask, open the masked "which letter" window (its text
    carries ``[PCHM=n+1,n]`` so hidden rows vanish from navigation, like stock), then dispatch the row.
    A row's arm re-seeds text var 1 FROM THE PAYLOAD BYTE (the donor reads ``Byte[1079+k]`` back rather
    than re-hardcoding the sender -- ``switch 10`` @test2_37:1298-1343) and re-displays the letter via
    :func:`letter_display`. NO lock write, NO mailbox write -- the read is pure, so the letter stays in
    the list forever (the donor's own re-read law). Cancel is the last arm, bodiless."""
    rows = list(rows)
    arms = []
    for k, (v, sender) in enumerate(rows):
        sender_expr = _push_byte(PAYLOAD_SENDER_BASE + k) + bytes([_region.T_END])
        arm = opcodes.encode(0x66, 1, sender_expr, arg_flags=0b10)    # SetTextVariable(1, {Byte[1079+k]})
        arm += letter_display(letter_txids[int(v)])
        arms.append(arm)
    arms.append(b"")                                                   # cancel
    mask_expr = _region.var_expr(_region.GLOB_UINT16, _region.MASK_SCRATCH_IDX)
    return (read_row_population(rows)
            + opcodes.enable_dialog_choices_var(mask_expr, 0)
            + opcodes.window_sync(window, flags, prompt_txid)
            + _choice.switch_on_choice(arms))


def _arrival_cond(variant: int, requires_flag=None, requires_scenario=None) -> bytes:
    """``if ([scenario >= N] [&& flag] && !read_lock(variant))`` -- the stock auto-arrival gate shape
    (a story condition crossed AND the letter not yet arrived; donor: the scenario-threshold checks
    feeding the arrival counter, field 115 @1444-1479)."""
    t, have = b"", False
    if requires_scenario is not None:
        t += (_region._push_var(_region.GLOB_UINT16, 0) + bytes([_region.T_CONST])
              + _region._const16(_region.GLOB_UINT16, int(requires_scenario)) + bytes([_region.T_GE]))
        have = True
    if requires_flag is not None:
        t += _region._push_var(_region.GLOB_BOOL, int(requires_flag))
        if have:
            t += bytes([_T_ANDAND])
        have = True
    t += _region._push_var(_region.GLOB_BOOL, read_lock_bit(variant)) + bytes([_region.T_NOT])
    if have:
        t += bytes([_T_ANDAND])
    return bytes([_region.EXPR_OP]) + t + bytes([_region.T_END])


def arrival_body(entries, *, arrive_txid: int | None = None, letter_txids=None,
                 window: int = 1, flags: int = 128) -> bytes:
    """Scenario/flag-gated AUTO-ARRIVALS: letters that reach our moogle by network, offscreen -- the
    stock second arrival source (the first is the player's own delivery, the accept path). Per entry,
    when its condition holds and the letter hasn't arrived yet: announce line, sender into text var 1,
    the letter display, then the READ lock -- arrival, not reading, is what sets the lock (the donor
    law), which is exactly what makes the letter appear in the read-mail list afterwards. One-shot by
    construction (the lock is the once-guard). ``entries`` = ``[(variant, sender_id, requires_flag,
    requires_scenario), ...]``."""
    letter_txids = letter_txids or {}
    out = b""
    for (v, sender, rf, rs) in entries:
        vv = check_variant(v, allow_shipped=True)
        body = opcodes.set_text_variable(1, _check_id("sender", sender))
        if arrive_txid is not None:
            body += opcodes.window_sync(window, flags, arrive_txid)
        if int(vv) in letter_txids:
            body += letter_display(letter_txids[int(vv)])
        body += _set_lock(read_lock_bit(vv))
        out += _region.if_block(_arrival_cond(vv, rf, rs), body)
    return out


def normalize_accept(acc) -> tuple:
    """``accept`` entries are bare variant ints OR ``{variant, letter, [from], [title]}`` tables.
    Returns ``(variants, {variant: letter_body})`` -- the single normalization used by validate,
    collect_text and the dispatch, so the three can never disagree. (``from``/``title`` make an accept
    letter ALSO re-readable via Read mail -- collect_text resolves them into the row list.)"""
    variants, letters = [], {}
    for it in (acc or []):
        if isinstance(it, dict):
            v = int(it["variant"])
            variants.append(v)
            if it.get("letter") is not None:
                letters[v] = str(it["letter"])
        else:
            variants.append(int(it))
    return variants, letters


def normalize_received(rec) -> list:
    """``received`` entries -- letters that auto-ARRIVE at this moogle when a story condition holds
    (``requires_flag`` / ``requires_scenario``; neither = arrives on the first Mognet open). Each is a
    dict ``{variant, from, title, letter, [requires_flag], [requires_scenario]}`` -- ``from``/``title``/
    ``letter`` are REQUIRED (an arrival without content or a row without a title cannot render).
    Returns the entries with ``variant`` and the gate values normalized to ints; ``from`` stays raw
    (a roster name or id, resolved against the install roster at text time)."""
    out = []
    for it in (rec or []):
        if not isinstance(it, dict):
            raise ValueError(f"[savepoint.mognet] received entries must be tables, got {it!r}")
        e = dict(it)
        e["variant"] = int(e["variant"])
        if e.get("requires_flag") is not None:
            e["requires_flag"] = int(e["requires_flag"])
        if e.get("requires_scenario") is not None:
            e["requires_scenario"] = int(e["requires_scenario"])
        out.append(e)
    return out


def mognet_interaction_body(*, my_id: int = NEW_MOOGLE_ID, accept_variants=(), give=None,
                            accept_prompt_txid: int | None = None, thanks_txid: int | None = None,
                            give_prompt_txid: int | None = None, give_txid: int | None = None,
                            nothing_txid: int | None = None, erase_txid: int | None = None,
                            letter_txids: dict | None = None, status_txids=None,
                            read_rows=(), received=(), menu_prompt_txid: int | None = None,
                            read_prompt_txid: int | None = None,
                            arrive_txid: int | None = None) -> bytes:
    """The whole Mognet interaction -- the body behind the moogle menu's "Mognet" row.

    WITHOUT read-mail rows (``read_rows`` empty) this is byte-identical to the proven v1 chain::

        migration guard                       # the wipe-guard runs before ANY mailbox read
        if a held letter is addressed to me:  # (a) ACCEPT -- confirm, then take delivery
            [confirm window] -> row 0 -> accept_letter_body   (thanks line, compaction, counter)
        elif my letter is unhanded + a slot free:             # (b) GIVE -- offer, then hand it over
            [offer window]   -> row 0 -> give_letter_body     (first-empty slot, one-shot lock)
        else:                                                 # (c) nothing to give or receive
            [nothing line]

    WITH read-mail rows the donor's real shape takes over: auto-ARRIVALS fire first (``received``
    entries whose story condition newly holds -- announce + letter + READ lock, the one-shot), then a
    computed availability word gates the 3-row "What can I do for you" submenu exactly like the donor's
    ``if (VAR_GlobInt16_39)`` (bit 0 = a delivery pending, bit 1 = any letter known, bit 2 = Cancel,
    always on -- so the gate is ``mask != cancel-only``)::

        arrivals
        mask = 4 | (accept pending ? 1) | (any letter known ? 2)
        if (mask != 4):
            [3-row submenu, masked]  row 0 -> the accept confirm+body (as v1)
                                     row 1 -> read_mail_body (payload rebuild + which-letter + display)
                                     row 2 -> Cancel (bodiless)
            if my give is offerable: [the give offer]         # still reachable in the same talk
        else:  (b)/(c) exactly as v1

    ``give`` is ``(variant, to_id)`` or None. ``accept_variants`` = variants deliverable TO this
    moogle; ``read_rows`` = ``[(variant, sender_id), ...]`` in menu order (the titled letters);
    ``received`` = ``[(variant, sender_id, requires_flag, requires_scenario), ...]`` auto-arrivals.
    Confirms dispatch via :func:`choice.switch_on_choice` (one sysvar-9 read; nesting-safe)."""
    def _confirmed(prompt_txid, body):
        if prompt_txid is None:
            return body
        return (opcodes.window_sync(CHOICE_WINDOW, CHOICE_FLAGS, prompt_txid)
                + _choice.switch_on_choice([body, b""]))

    nothing_arm = opcodes.window_sync(1, 128, nothing_txid) if nothing_txid is not None else b""
    accept_arm = _confirmed(accept_prompt_txid,
                            accept_letter_body(accept_variants, my_id=my_id, thanks_txid=thanks_txid,
                                               letter_txids=letter_txids))
    if give is not None:
        gv, gto = give
        give_arm = _confirmed(give_prompt_txid,
                              give_letter_body(gv, gto, from_id=my_id, give_txid=give_txid))
        els = _region.if_else(give_available_cond(gv), give_arm, nothing_arm)
    else:
        give_arm = b""
        els = nothing_arm
    # the mail-status box opens right after the guard (the donor's order: recount+status @5929-6153,
    # THEN the row gating) and closes when the act ends; the letter display closes it early itself.
    status = mail_status_window(status_txids) if status_txids else b""
    closer = opcodes.encode(0x21, STATUS_WINDOW) if status_txids else b""
    rows = list(read_rows)
    if rows and menu_prompt_txid is not None and read_prompt_txid is not None:
        arrivals = arrival_body(received, arrive_txid=arrive_txid, letter_txids=letter_txids)
        # the availability word, donor-shaped: base = the Cancel bit, then each live lane ORs its row in
        mask = _region.MASK_SCRATCH_IDX
        avail = (_region.set_var(_region.GLOB_UINT16, mask, 4)
                 + _region.if_block(accept_available_cond(my_id),
                                    _region.or_var(_region.GLOB_UINT16, mask, 1))
                 + _region.if_block(read_available_cond([v for v, _ in rows]),
                                    _region.or_var(_region.GLOB_UINT16, mask, 2)))
        gate = (bytes([_region.EXPR_OP]) + _region._push_var(_region.GLOB_UINT16, mask)
                + bytes([_region.T_CONST]) + _region._const16(_region.GLOB_UINT16, 4)
                + bytes([_T_NE, _region.T_END]))
        submenu = (opcodes.enable_dialog_choices_var(_region.var_expr(_region.GLOB_UINT16, mask), 0)
                   + opcodes.window_sync(CHOICE_WINDOW, CHOICE_FLAGS, menu_prompt_txid)
                   + _choice.switch_on_choice(
                       [accept_arm,
                        read_mail_body(rows, read_prompt_txid, letter_txids or {}),
                        b""])
                   + (_region.if_block(give_available_cond(give[0]), give_arm) if give is not None else b""))
        dispatch = arrivals + avail + _region.if_else(gate, submenu, els)
    else:
        dispatch = _region.if_else(accept_available_cond(my_id), accept_arm, els)
    # our own identity into text var 0 FIRST -- every window below speaks as `[TEXT=0,0]` (the stock
    # idiom, see VAR_SPEAKER). Nothing downstream clobbers var 0: the status box uses 2..7 and the
    # accept arm re-seeds this same value alongside var 1 (the sender).
    return (opcodes.set_text_variable(0, int(my_id)) + migration_guard(erase_txid) + status
            + dispatch + closer)


# --------------------------------------------------------------------------- the roster text ---
_TBLE_RE = re.compile(r"^(\[TBLE=[^\]]*\])( ?)(.*)$", re.S)


def roster_extend(entry0_text: str, new_names) -> str:
    """Append moogle name(s) to a roster table (a field text-entry-0 ``[TBLE=...]`` body), preserving
    the original tag and rows byte-for-byte. The tag's numeric parameters are PROVEN inert -- the engine
    splits the post-tag text on newlines and never reads them (DialogBoxSymbols.ParseTextSplitTags;
    independently exploited by ``world/navimap.py``) -- so they are deliberately NOT recomputed. Row
    index = moogle id: the first appended name becomes id ``len(existing)`` (41 on a stock roster =
    :data:`NEW_MOOGLE_ID`)."""
    m = _TBLE_RE.match(entry0_text)
    if not m:
        raise ValueError("entry-0 text does not start with a [TBLE=...] tag -- not a roster table")
    tag, sep, body = m.groups()
    names = body.split("\n")
    if len(names) < ROSTER_SIZE:
        raise ValueError(f"roster has {len(names)} rows, expected >= {ROSTER_SIZE} -- wrong text entry?")
    add = [str(n) for n in (new_names if isinstance(new_names, (list, tuple)) else [new_names])]
    for n in add:
        if not n or "\n" in n or "[" in n:
            raise ValueError(f"bad moogle name {n!r} (empty, newline, or a text tag)")
    return tag + sep + "\n".join(names + add)


def roster_from_install(*, lang: str = "us", field: int = 300, game=None) -> str:
    """The real roster table text (entry 0 of a save-moogle field's text block), read from the USER'S OWN
    install -- the kit ships no Square-Enix text (docs/PROVENANCE.md), so the 41 names enter a build only
    via this extraction, exactly like every other template. Needs the install + UnityPy."""
    from .. import dialogue as _dialogue
    from .._fieldtext import EVENT_ID_TO_MES
    got = _dialogue._load_field_text([0], lang, game=game, zone_id=EVENT_ID_TO_MES[int(field)])
    if 0 not in got:
        raise ValueError(f"field {field}'s text block has no entry 0 -- not a save-moogle block?")
    return got[0].text
