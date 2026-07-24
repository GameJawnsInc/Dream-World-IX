"""content/mognet.py -- a NEW moogle identity on FF9's real letter network.

The adversarial review marked "cannot corrupt a real save's letters" UNPROVEN because it was a promise
about unwritten code: the naive give (constant writes into slot 0) silently destroys whatever letter the
player already holds there. So these tests do not inspect the emitter's structure -- they EXECUTE the
emitted bodies in a mini-VM over a simulated gEventGlobal and assert the invariants on the bytes that
come out: an occupied slot is never overwritten, a full mailbox refuses with zero mailbox writes, a
delivery compacts and never leaves a hole, and Byte[1033] (Stiltzkin's) is never touched.

Byte-level pins come from field 300 (offsets quoted per line) and from the LIVE probe of 2026-07-18
(delivering Kuppo's letter to Kupo on a real save): the guard's RPN, the compaction copy idiom, the
Byte[1032]++ shape, and the lock-bit formula's test vectors are all donor- or live-derived.
"""
from __future__ import annotations

import pytest

from ff9mapkit.content import mognet as _m
from ff9mapkit.content import region as _region
from ff9mapkit.eb import disasm

_PARTYCHK = 0x6B          # B_PARTYCHK -- see content.savepoint.PARTYCHK (the party-size clamp)


# --------------------------------------------------------------------------- the mini-VM ---
def _eval_expr(tokens: bytes, G: bytearray, sysread=None, party=None, M=None, in_party=None) -> int:
    """Evaluate one 0x05 expression's token stream (sans the leading 05) against gEventGlobal ``G``.
    ``sysread(code)`` services GetSysvar tokens (0x7A) -- the tests script dialog choices through it.
    ``M`` is the transient MAP array (the engine's per-field twin of G) -- the act's handshake bit
    lives there (MAP.Bit[322], class 0xC5/0xE5)."""
    stack: list = []

    def deref(x):
        kind, v = x
        if kind == "c":
            return v
        if kind == "by":
            return G[v]
        if kind == "w":
            return G[v] | (G[v + 1] << 8)              # GLOB_UINT16 -- LE word, engine-unsigned
        if kind == "mbi":
            return (M[v >> 3] >> (v & 7)) & 1          # MAP bit
        return (G[v >> 3] >> (v & 7)) & 1              # "bi"

    p = 0
    while p < len(tokens):
        t = tokens[p]; p += 1
        if t == _region.T_END:
            break
        elif t == _region.T_CONST:
            stack.append(("c", int.from_bytes(tokens[p:p + 2], "little"))); p += 2
        elif t == _region.GLOB_BYTE:                                   # 0xD4 short index
            stack.append(("by", tokens[p])); p += 1
        elif t == (_region.GLOB_BYTE | 0x20):                          # 0xF4 long index
            stack.append(("by", int.from_bytes(tokens[p:p + 2], "little"))); p += 2
        elif t == _region.GLOB_BOOL:                                   # 0xC4 short index
            stack.append(("bi", tokens[p])); p += 1
        elif t == (_region.GLOB_BOOL | 0x20):                          # 0xE4 long index
            stack.append(("bi", int.from_bytes(tokens[p:p + 2], "little"))); p += 2
        elif t == _region.GLOB_UINT16:                                 # 0xDC short index (LE word)
            stack.append(("w", tokens[p])); p += 1
        elif t == (_region.GLOB_UINT16 | 0x20):                        # 0xFC long index
            stack.append(("w", int.from_bytes(tokens[p:p + 2], "little"))); p += 2
        elif t == _region.MAP_BOOL and M is not None:                  # 0xC5 short index (MAP bit)
            stack.append(("mbi", tokens[p])); p += 1
        elif t == (_region.MAP_BOOL | 0x20) and M is not None:         # 0xE5 long index (MAP bit)
            stack.append(("mbi", int.from_bytes(tokens[p:p + 2], "little"))); p += 2
        elif t == _region.T_SYSVAR:                                    # 0x7A GetSysvar(code)
            code = tokens[p]; p += 1
            if sysread is None:
                raise AssertionError(f"mini-VM: unscripted GetSysvar({code})")
            stack.append(("c", int(sysread(code))))
        elif t in (_region.T_CURHP, _region.T_MAXHP, _region.T_CURMP, _region.T_MAXMP):
            slot = deref(stack.pop())                  # a slot the party doesn't hold reads 0
            idx = {_region.T_CURHP: 0, _region.T_MAXHP: 1, _region.T_CURMP: 2, _region.T_MAXMP: 3}[t]
            stack.append(("c", (party or {}).get(slot, (0, 0, 0, 0))[idx]))
        elif t == _region.T_ITEMCOUNT:
            item = deref(stack.pop())
            stack.append(("c", (party or {}).get(("item", item), 0)))
        elif t == _PARTYCHK:                           # 0x6B B_PARTYCHK: is this character in the party?
            cid = deref(stack.pop())
            stack.append(("c", 1 if cid in (in_party or ()) else 0))
        elif t in (_region.T_PLUS, _region.T_DIV, _region.T_MULT, _region.T_MINUS):
            b, a = deref(stack.pop()), deref(stack.pop())
            stack.append(("c", {_region.T_PLUS: a + b, _region.T_MINUS: a - b,
                                _region.T_MULT: a * b, _region.T_DIV: a // b if b else 0}[t]))
        elif t == _region.T_NOT:
            stack.append(("c", 0 if deref(stack.pop()) else 1))
        elif t in (_region.T_LT, _region.T_GE, _region.T_EQ, _m._T_NE, _m._T_ANDAND, _m._T_OROR):
            b, a = deref(stack.pop()), deref(stack.pop())
            r = {_region.T_LT: a < b, _region.T_GE: a >= b, _region.T_EQ: a == b, _m._T_NE: a != b,
                 _m._T_ANDAND: bool(a) and bool(b), _m._T_OROR: bool(a) or bool(b)}[t]
            stack.append(("c", 1 if r else 0))
        elif t == _region.T_OR_ASSIGN:                 # |= -- the mask-scratch build idiom (or_var)
            val = deref(stack.pop())
            kind, idx = stack.pop()
            assert kind == "w", "mini-VM: |= modelled for the GLOB_UINT16 mask scratch only"
            cur = (G[idx] | (G[idx + 1] << 8)) | val
            G[idx], G[idx + 1] = cur & 0xFF, (cur >> 8) & 0xFF
            stack.append(("c", cur))
        elif t == _region.T_ASSIGN:
            val = deref(stack.pop())
            kind, idx = stack.pop()
            if kind == "by":
                G[idx] = val & 0xFF
            elif kind == "w":
                G[idx], G[idx + 1] = val & 0xFF, (val >> 8) & 0xFF
            elif kind == "bi":
                if val:
                    G[idx >> 3] |= 1 << (idx & 7)
                else:
                    G[idx >> 3] &= ~(1 << (idx & 7)) & 0xFF
            elif kind == "mbi":
                if val:
                    M[idx >> 3] |= 1 << (idx & 7)
                else:
                    M[idx >> 3] &= ~(1 << (idx & 7)) & 0xFF
            else:
                raise AssertionError("assignment to a non-lvalue")
            stack.append(("c", val))
        elif t == _m._T_POST_PLUS:
            kind, idx = stack.pop()
            assert kind == "by"
            stack.append(("c", G[idx]))
            G[idx] = (G[idx] + 1) & 0xFF
        else:
            raise AssertionError(f"mini-VM: unhandled expression token 0x{t:02X}")
    return deref(stack[-1]) if stack else 0


def _expr_operand(raw: bytes, i) -> bytes:
    """The expression-operand token stream of an instruction whose arg1 is an expression (SetHP/SetMP:
    opcode, argflag, slot byte, then the tokens)."""
    return raw[i.off + 3:i.off + i.length]


# The act's opcode set -- movement / animation / staging ops that never touch gEventGlobal. The VM
# RECORDS them (into ``events``, as (name, args) in execution order) rather than modelling them; the
# RunScript trio additionally fires ``on_async`` so a test can apply the callee's CONTRACT (e.g. the
# release tag clearing the handshake MAP bit) without the VM needing a multi-entry model.
_ACT_OPS = {0x40: "anim", 0x41: "waitanim", 0x42: "stopanim", 0x36: "turn", 0x51: "turnobj",
            0x50: "waitturn", 0x99: "turnspeed", 0x47: "headfocus", 0x93: "flags", 0x9F: "size",
            0x94: "jumpanim", 0xA1: "pos", 0xA8: "pathing", 0x7F: "shadow_on", 0x80: "shadow_off",
            0xC8: "sfx", 0x22: "wait"}    # Wait recorded too -- the donor calls its counts load-bearing
_REQ_OPS = {0x10: "req", 0x12: "reqsw", 0x14: "reqew"}


def run(body: bytes, G: bytearray | None = None, choices=None, menus=None, windows=None,
        stats=None, items=None, party_menu=None, party=None, events=None, on_async=None,
        M: bytearray | None = None, in_party=(), masks=None, max_steps: int = 200_000) -> bytearray:
    """Execute an emitted body over a (simulated) 2048-byte gEventGlobal; windows/text ops are no-ops.

    ``choices`` scripts the player's dialog picks: each read of GetSysvar(9) consumes the next entry
    (the engine's own contract -- every menu re-reads the choice register after its window). ``menus``,
    if a list, collects every Menu(id, sub) call so a test can assert the save fired (or didn't).
    ``events`` collects the act's choreography ops (see ``_ACT_OPS``); ``on_async(level, uid, tag)``
    runs on every RunScript dispatch (apply the callee's contract there); ``M`` is the transient MAP
    array (pass a bytearray to seed/inspect it -- mutated in place); ``in_party`` is the set of
    CharacterOldIndexes currently in the party, which ``B_PARTYCHK`` reads (the party-row size clamp).
    ``max_steps`` guards a loop whose exit contract was never applied (the handshake poll) from
    spinning the suite forever."""
    G = bytearray(2048) if G is None else bytearray(G)
    M = bytearray(2048) if M is None else M
    raw = bytes(body)
    queue = list(choices or [])

    party = dict(party or {})                      # {slot: (curhp, maxhp, curmp, maxmp)}; absent = 0s

    def sysread(code):
        if code != 9:
            raise AssertionError(f"mini-VM: unexpected GetSysvar({code})")
        if not queue:
            raise AssertionError("mini-VM: the body read a choice the test did not script")
        return queue.pop(0)

    pos, last, steps = 0, 0, 0
    while pos < len(raw):
        steps += 1
        if steps > max_steps:
            raise AssertionError(f"mini-VM: over {max_steps} steps -- a loop's exit contract "
                                 f"(on_async?) was never applied")
        i, nxt = disasm.read_code(raw, pos)
        if i.op == 0x05:
            last = _eval_expr(raw[i.off + 1:i.off + i.length], G, sysread, party, M, in_party)
        elif i.op in (0x01, 0x03):                     # JMP / JMP_IF -- SIGNED int16, the engine's own
            d = i.args[0]                              #   read (EBin bra/bne; disasm.jump_target agrees;
            d = d - 0x10000 if d >= 0x8000 else d      #   the donor's handshake poll is an 0x03 back-jump)
            if i.op == 0x01 or last:
                nxt += d
        elif i.op == 0x02:                             # JMP_IFNOT -- the engine reads this one UNSIGNED
            nxt += 0 if last else i.args[0]
        elif i.op == 0x0B:                             # the op_0B switch -- dispatch on the last expr
            info = disasm.decode_switch(i)
            edge = next((e for e in info.edges if e.value == last),
                        next(e for e in info.edges if e.is_default))
            pos = edge.target
            continue
        elif i.op == 0x75:                             # Menu -- record, never "open"
            if menus is not None:
                menus.append((i.args[0], i.args[1]))
        elif i.op in (0x1F, 0x20) and windows is not None:   # Window{Sync,Async} -- record (win, flags, txid)
            windows.append((i.args[0], i.args[1], i.args[2]))
        elif i.op == 0x04:                             # RETURN -- halt
            break
        elif i.op in (0xF1, 0xF2):                     # SetHP / SetMP -- record (slot, value)
            if stats is not None:
                stats.append((("hp" if i.op == 0xF1 else "mp"), i.args[0],
                              _eval_expr(_expr_operand(raw, i), G, sysread, party)))
        elif i.op == 0x49:                             # RemoveItem
            if items is not None:
                items.append((i.args[0], i.args[1]))
        elif i.op == 0x7C:                             # EnableDialogChoices(mask, default) -- record the
            if masks is not None:                      #   mask the engine would receive (expr or literal)
                mv = (_eval_expr(raw[i.off + 2:i.off + i.length - 1], G, sysread, party, M, in_party)
                      if i.arg_is_expr[0] else i.args[0])
                masks.append(mv)
        elif i.op == 0xB2:                             # Party(min_size, locked_mask)
            if party_menu is not None:
                # min_size is an EXPRESSION on the default path (the softlock clamp) -- evaluate it,
                # so the recorded value is the size the engine would actually receive. Layout:
                # op, argflag, <tokens...>, locked(1 byte).
                mn = (_eval_expr(raw[i.off + 2:i.off + i.length - 1], G, sysread, party, M, in_party)
                      if i.arg_is_expr[0] else i.args[0])
                party_menu.append((mn, i.args[1]))
        elif i.op in _REQ_OPS:                         # RunScript{Async,,Sync} -- record + apply contract
            if events is not None:
                events.append((_REQ_OPS[i.op], tuple(i.args)))
            if on_async is not None:
                on_async(i.args[0], i.args[1], i.args[2])
        elif i.op in _ACT_OPS:                         # choreography -- record only (never touches G)
            if events is not None:
                events.append((_ACT_OPS[i.op], tuple(i.args)))
        elif i.op in (0x1F, 0x20, 0x66,                # WindowSync / WindowAsync / SetTextVariable
                      0x22,                            # Wait
                      0x2D, 0x2E, 0xAB, 0xAA,          # Disable/EnableMove, Disable/EnableMenu
                      0xA9, 0xEC, 0x8E, 0x54, 0x21,    # the letter display: CalcScreenPos / FadeFilter
                      0xE9,                            #   / RaiseWindows / WaitWindow / CloseWindow
                      0xD5):                           # HideAllObjects -- the tent's rest bracket
            pass                                       # + UpdatePartyUID
        else:
            raise AssertionError(f"mini-VM: unhandled opcode 0x{i.op:02X} at {i.off}")
        pos = nxt
    assert not queue, f"mini-VM: {len(queue)} scripted choice(s) were never consumed"
    return G


def _mailbox(G):
    return [(G[_m.slot_addr(k)], G[_m.slot_addr(k, 1)], G[_m.slot_addr(k, 2)], G[_m.slot_addr(k, 3)])
            for k in range(3)]


def _set_slot(G, k, variant, from_id, to_id):
    G[_m.slot_addr(k)] = 1
    G[_m.slot_addr(k, 1)] = variant
    G[_m.slot_addr(k, 2)] = from_id
    G[_m.slot_addr(k, 3)] = to_id


def _bit(G, n):
    return (G[n >> 3] >> (n & 7)) & 1


def act_async_contract(M):
    """The act's async-release CONTRACT for the VM: the real release tag (a grafted player function)
    clears MAP.Bit[322] when it finishes; the VM records RunScript dispatches without executing them,
    so this hook applies that effect -- any player-targeted dispatch clears the handshake bit (the pose
    tag never sets it, so over-applying is harmless). Without it the close-out's poll would rightly
    spin into the step guard -- which is itself the proof the join is real, not decorative."""
    from ff9mapkit.content import savepoint as _sp

    def hook(level, uid, tag):
        if uid == _sp.PLAYER_UID:
            n = _sp.ACT_HANDSHAKE_BIT
            M[n >> 3] &= ~(1 << (n & 7)) & 0xFF
    return hook


# --------------------------------------------------------------------------- byte pins vs the donor ---
def test_lock_bit_formula_matches_the_live_probe():
    """Reading variants 19/22/33 on the real save set exactly bytes 1057 bit4 / 1057 bit1 / 1059 bit6."""
    assert _m.read_lock_bit(19) == 8460 and (8460 >> 3, 8460 & 7) == (1057, 4)
    assert _m.read_lock_bit(22) == 8457 and (8457 >> 3, 8457 & 7) == (1057, 1)
    assert _m.read_lock_bit(33) == 8478 and (8478 >> 3, 8478 & 7) == (1059, 6)
    assert _m.give_lock_bit(0) == 8383 and _m.give_lock_bit(7) == 8376   # anchor + descending in-byte


def test_guard_condition_is_donor_byte_identical():
    """field 300 @5638 -- the wipe-guard RPN, token for token."""
    donor = "05f400047d010018f40a047d000021f40e047d00002128f412047d00002128277f"
    assert _m.migration_guard().hex().startswith(donor)


def test_compaction_copy_and_counter_idioms_match_the_donor():
    assert _m._copy_byte(1034, 1038).hex() == "05f40a04f40e042c7f"      # field 300 @7019
    assert _m._post_inc_byte(1032).hex() == "05f40804047f"              # field 300 @6387


def test_variant_validation():
    with pytest.raises(ValueError):
        _m.check_variant(19)                           # shipped band -- collides with a real letter
    with pytest.raises(ValueError):
        _m.check_variant(64)                           # past the 64-bit lock tables
    assert _m.check_variant(55) == 55
    assert _m.check_variant(19, allow_shipped=True) == 19
    with pytest.raises(ValueError):
        _m.give_letter_body(55, to_id=300)             # a moogle id is a byte


# --------------------------------------------------------------------------- executed invariants ---
def test_give_lands_in_the_first_empty_slot():
    G = run(_m.give_letter_body(55, to_id=8))
    assert _mailbox(G) == [(1, 55, 41, 8), (0, 0, 0, 0), (0, 0, 0, 0)]
    assert G[_m.GUARD_IDX] == 1
    assert _bit(G, _m.give_lock_bit(55)) == 1          # the one-shot fired


def test_give_never_overwrites_an_occupied_slot():
    """THE invariant the review called unproven: slot 0 holds the player's real letter (Kuppo->Kupo,
    variant 19, as on the live save); our give must land in slot 1 and leave slot 0 byte-identical."""
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    _set_slot(G0, 0, 19, 23, 1)
    G = run(_m.give_letter_body(55, to_id=8), G0)
    assert _mailbox(G) == [(1, 19, 23, 1), (1, 55, 41, 8), (0, 0, 0, 0)]


def test_give_on_a_full_mailbox_writes_nothing():
    """Full = graceful refusal: every mailbox byte identical, and the one-shot lock does NOT fire
    (the letter was not handed out -- locking it would silently destroy the offer forever)."""
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    _set_slot(G0, 0, 19, 23, 1)
    _set_slot(G0, 1, 20, 5, 9)
    _set_slot(G0, 2, 21, 7, 2)
    G = run(_m.give_letter_body(55, to_id=8, full_txid=501), G0)
    assert bytes(G[_m.SLOT0:_m.SLOT0 + 12]) == bytes(G0[_m.SLOT0:_m.SLOT0 + 12])
    assert _bit(G, _m.give_lock_bit(55)) == 0
    assert bytes(G) == bytes(G0)                       # in fact NOTHING changed (guard was already 1)


def test_accept_consumes_and_compacts_never_leaving_a_hole():
    """Deliver to our moogle while a stranger's letter sits ABOVE ours: consuming slot 0 must shift
    slot 1 down into slot 0 and zero the tail -- the donor's compaction (field 300 @6990-7126)."""
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    G0[_m.DELIVERED_IDX] = 12
    _set_slot(G0, 0, 55, 8, 41)                        # ours: variant 55 FROM Kumop TO us
    _set_slot(G0, 1, 19, 23, 1)                        # a stranger's (Kuppo -> Kupo)
    G = run(_m.accept_letter_body([55]), G0)
    assert _mailbox(G) == [(1, 19, 23, 1), (0, 0, 0, 0), (0, 0, 0, 0)]   # shifted down, tail zeroed
    assert G[_m.DELIVERED_IDX] == 13                   # the live probe's 12 -> 13
    assert _bit(G, _m.read_lock_bit(55)) == 1
    assert G[_m.STILTZKIN_IDX] == G0[_m.STILTZKIN_IDX]  # never ours to touch


def test_accept_matches_the_addressee_not_the_position():
    """Ours in slot 1 behind a stranger's in slot 0: slot 0 must survive byte-identically."""
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    _set_slot(G0, 0, 19, 23, 1)
    _set_slot(G0, 1, 55, 8, 41)
    G = run(_m.accept_letter_body([55]), G0)
    assert _mailbox(G) == [(1, 19, 23, 1), (0, 0, 0, 0), (0, 0, 0, 0)]
    assert G[_m.DELIVERED_IDX] == 1


def test_accept_with_no_matching_letter_changes_nothing():
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    _set_slot(G0, 0, 19, 23, 1)                        # addressed to Kupo, not to us
    G = run(_m.accept_letter_body([55], nothing_txid=502), G0)
    assert bytes(G) == bytes(G0)


def test_migration_guard_erases_only_when_it_should():
    # guard 0 + a letter present -> the erase fires, then guard = 1 (the donor's exact behaviour)
    G0 = bytearray(2048)
    _set_slot(G0, 0, 19, 23, 1)
    G = run(_m.migration_guard(), G0)
    assert _mailbox(G) == [(0, 0, 0, 0)] * 3 and G[_m.GUARD_IDX] == 1
    # guard already 1 -> letters SURVIVE (this is why every write path must set the guard)
    G1 = bytearray(2048)
    G1[_m.GUARD_IDX] = 1
    _set_slot(G1, 0, 19, 23, 1)
    G = run(_m.migration_guard(), G1)
    assert _mailbox(G)[0] == (1, 19, 23, 1)
    # guard 0 + empty mailbox -> nothing to erase, guard becomes 1
    G = run(_m.migration_guard())
    assert G[_m.GUARD_IDX] == 1 and _mailbox(G) == [(0, 0, 0, 0)] * 3


def test_availability_conds_evaluate_correctly():
    """The menu-row gates, executed: give offered only while unlocked + a slot free; accept row only
    while a letter addressed to us is held."""
    def cond(body, G):
        # a bare cond expr is one 05-expression; evaluate it directly
        return _eval_expr(bytes(body)[1:], G)

    G = bytearray(2048)
    assert cond(_m.give_available_cond(55), G) == 1
    G[_m.slot_addr(0)] = G[_m.slot_addr(1)] = G[_m.slot_addr(2)] = 1
    assert cond(_m.give_available_cond(55), G) == 0    # mailbox full -> no offer
    G2 = bytearray(2048)
    G2[_m.give_lock_bit(55) >> 3] |= 1 << (_m.give_lock_bit(55) & 7)
    assert cond(_m.give_available_cond(55), G2) == 0   # already handed out -> one-shot
    G3 = bytearray(2048)
    assert cond(_m.accept_available_cond(41), G3) == 0
    _set_slot(G3, 2, 55, 8, 41)
    assert cond(_m.accept_available_cond(41), G3) == 1
    _set_slot(G3, 2, 55, 8, 40)                        # addressed to Artemicion, not us
    assert cond(_m.accept_available_cond(41), G3) == 0


# --------------------------------------------------------------------------- the roster text ---
_FAKE = "[TBLE=41,82,88,]" + " " + "\n".join(f"M{i:02}" for i in range(41))


def test_roster_extend_appends_the_42nd_row_preserving_the_rest():
    out = _m.roster_extend(_FAKE, "Mogwai")
    rows = out.split("] ", 1)[1].split("\n")
    assert len(rows) == 42 and rows[41] == "Mogwai" and rows[:41] == [f"M{i:02}" for i in range(41)]
    assert out.startswith("[TBLE=41,82,88,] ")         # the tag (inert params) byte-preserved
    assert _m.NEW_MOOGLE_ID == 41                      # the appended row's index IS the new identity


def test_roster_extend_rejects_bad_input():
    with pytest.raises(ValueError):
        _m.roster_extend("no table here", "X")
    with pytest.raises(ValueError):
        _m.roster_extend("[TBLE=3,] a\nb\nc", "X")     # too few rows -- wrong text entry
    for bad in ("", "a\nb", "[CHOO]x"):
        with pytest.raises(ValueError):
            _m.roster_extend(_FAKE, bad)


# --------------------------------------------------------------------------- install-gated ---
def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_roster_from_install_matches_the_live_identities():
    """The extracted roster must resolve the identities OBSERVED in-game: the barrel moogle's nameplate
    read Kumop (Init sets id 8), and the live save's letter is FROM Kuppo (23) TO Kupo (1)."""
    text = _m.roster_from_install()
    assert text.startswith("[TBLE=")
    names = _m._TBLE_RE.match(text).group(3).split("\n")
    assert len(names) == _m.ROSTER_SIZE
    assert names[8] == "Kumop" and names[23] == "Kuppo" and names[1] == "Kupo"
    out = _m.roster_extend(text, "Mogwai")
    assert _m._TBLE_RE.match(out).group(3).split("\n")[_m.NEW_MOOGLE_ID] == "Mogwai"


# --------------------------------------------------------------------------- the full moogle, executed ---
from ff9mapkit.content import savepoint as _sp  # noqa: E402  (the rung-4 menu assembly)


def _moogle(give=None, accepts=(55,)):
    """The composed network moogle exactly as the build will wire it: the 3-row top menu around the
    mognet a/b/c interaction."""
    mog = _m.mognet_interaction_body(accept_variants=accepts, give=give,
                                     accept_prompt_txid=520, thanks_txid=521,
                                     give_prompt_txid=522, give_txid=523,
                                     nothing_txid=524, erase_txid=525)
    return _sp.save_dispatch_mognet(510, 511, mog)


def test_menu_save_yes_fires_the_latched_save():
    menus = []
    G = run(_moogle(), choices=[0, 0], menus=menus)
    assert menus == [(4, 0)]
    assert G[184 >> 3] & (1 << (184 & 7)) == 0         # the GLOB(184) latch set then cleared


def test_menu_save_no_does_nothing():
    menus = []
    G = run(_moogle(), choices=[0, 1], menus=menus)
    assert menus == [] and bytes(G) == bytes(bytearray(2048))


def test_menu_cancel_does_nothing():
    menus = []
    G = run(_moogle(), choices=[2], menus=menus)
    assert menus == [] and bytes(G) == bytes(bytearray(2048))


def test_menu_mognet_accept_path():
    """(a) the player brought a letter addressed to us: Mognet -> confirm Yes -> delivery."""
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    G0[_m.DELIVERED_IDX] = 12
    _set_slot(G0, 0, 55, 8, 41)
    menus = []
    G = run(_moogle(), G0, choices=[1, 0], menus=menus)
    assert menus == []                                 # mognet never opens the save menu
    assert _mailbox(G) == [(0, 0, 0, 0)] * 3
    assert G[_m.DELIVERED_IDX] == 13 and _bit(G, _m.read_lock_bit(55)) == 1


def test_menu_mognet_accept_declined_is_a_no_op():
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    _set_slot(G0, 0, 55, 8, 41)
    G = run(_moogle(), G0, choices=[1, 1])
    assert bytes(G) == bytes(G0)


def test_menu_mognet_give_path():
    """(b) our moogle's letter is unhanded and a slot is free: Mognet -> offer Yes -> handed over."""
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    G = run(_moogle(give=(56, 1)), G0, choices=[1, 0])
    assert _mailbox(G)[0] == (1, 56, 41, 1)            # FROM us TO Kupo
    assert _bit(G, _m.give_lock_bit(56)) == 1


def test_menu_mognet_give_declined_keeps_the_offer():
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    G = run(_moogle(give=(56, 1)), G0, choices=[1, 1])
    assert bytes(G) == bytes(G0)                       # nothing written, the one-shot NOT burnt


def test_menu_mognet_give_already_handed_is_case_c():
    """The one-shot: once given, the offer never re-fires -- the nothing line shows instead."""
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    G0[_m.give_lock_bit(56) >> 3] |= 1 << (_m.give_lock_bit(56) & 7)
    G = run(_moogle(give=(56, 1)), G0, choices=[1])    # no confirm opens -- straight to the nothing line
    assert bytes(G) == bytes(G0)


def test_menu_mognet_nothing_pending_is_case_c():
    G = run(_moogle(), choices=[1])
    ref = bytearray(2048)
    ref[_m.GUARD_IDX] = 1                              # only the migration guard's init write
    assert bytes(G) == bytes(ref)


def test_menu_mognet_accept_takes_priority_over_give():
    """Both pending: delivering the player's letter beats re-offering ours (donor order)."""
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    _set_slot(G0, 0, 55, 8, 41)
    G = run(_moogle(give=(56, 1)), G0, choices=[1, 0])
    assert _mailbox(G) == [(0, 0, 0, 0)] * 3           # the accept consumed; the give did NOT fire
    assert _bit(G, _m.give_lock_bit(56)) == 0


def test_menu_mognet_runs_the_migration_guard():
    """Old un-migrated data + our moogle first: the erase fires HERE, exactly as at a real moogle."""
    G0 = bytearray(2048)                               # guard 0
    _set_slot(G0, 0, 19, 23, 1)
    G = run(_moogle(), G0, choices=[1])
    assert _mailbox(G) == [(0, 0, 0, 0)] * 3 and G[_m.GUARD_IDX] == 1


def test_menu_save_path_skips_the_guard_and_mailbox_entirely():
    """Picking Save must not touch a single mognet byte -- even with old data present."""
    G0 = bytearray(2048)
    _set_slot(G0, 0, 19, 23, 1)                        # guard 0 + occupied: the erase WOULD fire in mognet
    menus = []
    G = run(_moogle(), G0, choices=[0, 0], menus=menus)
    assert menus == [(4, 0)]
    assert bytes(G[_m.GUARD_IDX:1091]) == bytes(G0[_m.GUARD_IDX:1091])


# --------------------------------------------------------------------------- rung 5: the build wiring ---
_FIELD = (
    '[field]\nid = 4005\nname = "S"\narea = 11\ntext_block = 30110\nregister_text_block = true\n\n'
    '[camera]\npitch = 45\nfov = 42.2\n\n'
    '[walkmesh]\nquad = [[-400,-400],[400,-400],[400,400],[-400,400]]\n\n'
    '[[savepoint]]\nzone = [[-100,-100],[100,-100],[100,100],[-100,100]]\n'
    '[savepoint.mognet]\nname = "Mogwai"\naccept = [55]\ngive = { variant = 56, to = "Kupo" }\n')


@pytest.fixture()
def fake_roster(monkeypatch):
    """41 fake rows with the two live-verified identities at their real indices, so `to = "Kupo"`
    resolves to id 1 without the install."""
    rows = [f"M{i:02}" for i in range(41)]
    rows[1], rows[23], rows[8] = "Kupo", "Kuppo", "Kumop"
    monkeypatch.setattr(_m, "roster_from_install", lambda **kw: "[TBLE=41,82,] " + "\n".join(rows))


def _built(tmp_path, toml=_FIELD):
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(toml, encoding="utf-8")
    proj = build.FieldProject.load(p)
    probs = [x for x in build.validate(proj) if "mognet" in x.lower() or "savepoint" in x.lower()]
    assert not probs, probs
    ct = build.collect_text(proj)
    eb = build.build_script(proj, "us", {}, savepoint_txids=ct[10])
    return proj, ct, eb


def test_build_ships_the_roster_and_the_three_row_menu(tmp_path, fake_roster):
    _proj, ct, _eb = _built(tmp_path)
    mes, sp_txids = ct[0], ct[10]
    assert mes.startswith("_[TXID=0][STRT=10,1][TBLE=")            # the roster IS entry 0
    roster_line = mes.split("\n\n")[0] if "\n\n" in mes else mes
    assert mes.count("Mogwai") >= 1
    names = _m.roster_names(mes.split("[TBLE=", 1)[1].split("[ENDN]")[0].replace("41,82,]", "", 1)
                            .lstrip() if False else "[TBLE=41,82,] " + mes.split("[TBLE=41,82,] ", 1)[1].split("[ENDN]")[0])
    assert names[_m.NEW_MOOGLE_ID] == "Mogwai" and names[1] == "Kupo"
    assert "[PCHC=3,2]" in mes and "Mognet" in mes                 # the 3-row top menu
    t = sp_txids[0]
    assert {"prompt", "confirm", "accept_prompt", "thanks", "nothing", "erase",
            "give_prompt", "give_line", "give_to_id"} <= set(t)
    assert t["give_to_id"] == 1                                    # "Kupo" resolved against the roster


def _moogle_talk_body(eb_bytes):
    """The BUILT moogle NPC's talk func -- entry with SetModel(220) in tag 0, body of tag 3."""
    s = EbScript_from(eb_bytes)
    for e in s.entries:
        if e is None or e.empty:
            continue
        f0 = e.func_by_tag(0)
        if f0 is None:
            continue
        if any(i.op == 0x2F and i.args and i.args[0] == 220
               for i in disasm.iter_code(eb_bytes, f0.abs_start, f0.abs_end)):
            f3 = e.func_by_tag(3)
            if f3 is not None:
                return eb_bytes[f3.abs_start:f3.abs_end]
    raise AssertionError("no moogle talk func in the built field")


def EbScript_from(b):
    from ff9mapkit.eb import EbScript
    return EbScript.from_bytes(b)


def test_built_field_moogle_runs_the_whole_network_act(tmp_path, fake_roster):
    """The crown test: the .eb the BUILD emits, executed. Save works, the letter act works, and the
    player's held letter survives -- straight from the shipped bytes, not from the emitters."""
    _proj, _ct, eb = _built(tmp_path)
    body = _moogle_talk_body(eb)
    # Save -> Yes: the latched Menu(4,0). The built talk body now carries THE ACT around it, whose
    # close-out joins the async player release -- apply that contract or the poll (correctly) spins.
    menus = []
    M = bytearray(2048)
    run(body, choices=[0, 0], menus=menus, M=M, on_async=act_async_contract(M))
    assert menus == [(4, 0)]
    # Mognet with the player's real letter (Kuppo->Kupo) held + ours pending delivery TO us:
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    G0[_m.DELIVERED_IDX] = 12
    _set_slot(G0, 0, 19, 23, 1)                        # the live save's actual letter
    _set_slot(G0, 1, 55, 8, 41)                        # a letter addressed to Mogwai
    # Mognet is a SUBMENU (the donor cycle, 2026-07-22): completing it reopens the moogle's menu, so
    # every mognet visit scripts a trailing Cancel (row 2) to leave the reopened menu.
    G = run(body, G0, choices=[1, 0, 2])
    assert _mailbox(G) == [(1, 19, 23, 1), (0, 0, 0, 0), (0, 0, 0, 0)]   # ours consumed, theirs SURVIVES
    assert G[_m.DELIVERED_IDX] == 13 and _bit(G, _m.read_lock_bit(55)) == 1
    # Mognet again, nothing addressed to us now -> the give offer -> accept it
    G2 = run(body, G, choices=[1, 0, 2])
    assert _mailbox(G2)[1] == (1, 56, 41, 1)           # FROM Mogwai (41) TO Kupo (1), first free slot
    assert _bit(G2, _m.give_lock_bit(56)) == 1
    # Mognet a third time: letter handed out, nothing held -> case (c), a pure no-op
    G3 = run(body, G2, choices=[1, 2])
    assert bytes(G3) == bytes(G2)


def test_zone_region_carries_the_same_mognet_dispatch(tmp_path, fake_roster):
    _proj, ct, eb = _built(tmp_path)
    # both interact points (zone action + moogle talk) open the 3-row prompt: count its WindowSync
    t = ct[10][0]
    pat = bytes([0x1F, 0x00, 0x02, 0x08]) + int(t["prompt"]).to_bytes(2, "little")
    assert eb.count(pat) == 2


def test_mognet_validation_gates(tmp_path, fake_roster):
    from ff9mapkit import build

    def probs(toml):
        p = tmp_path / "v.field.toml"
        p.write_text(toml, encoding="utf-8")
        return build.validate(build.FieldProject.load(p))

    base = _FIELD
    # no minted text block -> refused (the roster would shadow a shared base block's entry 0)
    bad = base.replace("text_block = 30110\nregister_text_block = true", "text_block = 1073")
    assert any("MINTED text block" in x for x in probs(bad))
    # a base-game mesID, even registered -> refused
    bad = base.replace("text_block = 30110", "text_block = 8")
    assert any("BASE-GAME mes block" in x for x in probs(bad))
    # dialogue = false + mognet -> refused
    bad = base.replace("[savepoint.mognet]", "dialogue = false\n[savepoint.mognet]")
    assert any("requires the dialogue flow" in x for x in probs(bad))
    # a shipped variant -> refused
    bad = base.replace("variant = 56", "variant = 19")
    assert any("SHIPPED band" in x for x in probs(bad))
    # give.to = the moogle itself -> refused
    bad = base.replace('to = "Kupo"', 'to = "Mogwai"')
    assert any("cannot mail itself" in x for x in probs(bad))
    # a variant both given and accepted -> refused
    bad = base.replace("accept = [55]", "accept = [56]")
    assert any("both FROM and TO" in x for x in probs(bad))
    # unknown key -> refused
    bad = base.replace('name = "Mogwai"', 'name = "Mogwai"\nkupo = 1')
    assert any("unknown key 'kupo'" in x for x in probs(bad))
    # a second network moogle -> refused
    bad = base + ('\n[[savepoint]]\nzone = [[-300,-300],[-200,-300],[-200,-200],[-300,-200]]\n'
                  '[savepoint.mognet]\nname = "Kupomi"\n')
    assert any("only ONE network moogle" in x for x in probs(bad))
    # the happy path stays clean
    assert not [x for x in probs(base) if "mognet" in x.lower()]


# --------------------------------------------------------------------------- the LETTER (rung 6) ---
def test_letter_display_decodes_to_the_donor_shape():
    """field 1865 @6191-6310: parchment fade in (2,24 / 220,220,250), the frameless letter
    (window 3, flags 16), RaiseWindows + WaitWindow, restore fade (7,16)."""
    body = _m.letter_display(510)
    ins = list(disasm.iter_code(body, 0, len(body)))
    ops = [(disasm.op_name(i.op), list(i.args)) for i in ins]
    assert ("FadeFilter", [2, 24, 255, 220, 220, 250]) in ops
    assert ("WindowAsync", [3, 16, 510]) in ops
    assert ("RaiseWindows", []) in ops and ("WaitWindow", [3]) in ops
    assert ("FadeFilter", [7, 16, 255, 0, 0, 0]) in ops
    assert [o for o, _ in ops].count("CalculateScreenPosition") == 2


def test_letter_entry_text_is_the_stock_template_plus_body():
    t = _m.letter_entry_text("Dear Kupo,\nHello!  Kupo!")
    assert t.startswith(_m.LETTER_HEADER + "\n\n")
    assert "From [TEXT=0,1] to [TEXT=0,0]" in t          # sender/recipient through the roster
    assert "[ICON=27]" in t and "[ICON=29]" in t          # the moogle portrait pieces
    assert t.endswith("Hello!  Kupo!")


def test_normalize_accept_mixes_ints_and_tables():
    vs, letters = _m.normalize_accept([55, {"variant": 57, "letter": "Hi, kupo!"}, {"variant": 58}])
    assert vs == [55, 57, 58] and letters == {57: "Hi, kupo!"}
    assert _m.normalize_accept(None) == ([], {})


def test_accept_with_letter_still_holds_every_invariant():
    """The letter display is presentation only -- consuming with a letter must leave the mailbox
    mechanics byte-identical to consuming without one."""
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    _set_slot(G0, 0, 55, 8, 41)
    _set_slot(G0, 1, 19, 23, 1)
    plain = run(_m.accept_letter_body([55]), G0)
    lettered = run(_m.accept_letter_body([55], letter_txids={55: 900}), G0)
    assert bytes(plain) == bytes(lettered)
    assert _mailbox(lettered) == [(1, 19, 23, 1), (0, 0, 0, 0), (0, 0, 0, 0)]


_LETTER_FIELD = _FIELD.replace(
    "accept = [55]",
    'accept = [{ variant = 55, letter = "Dear Mogwai,\\nThe hills are lovely.  Kupo!" }]')


def test_build_ships_the_letter_and_the_display(tmp_path, fake_roster):
    _proj, ct, eb = _built(tmp_path, _LETTER_FIELD)
    mes, sp_txids = ct[0], ct[10]
    t = sp_txids[0]
    assert "letter55" in t
    entry = [ln for ln in mes.split("_[TXID=") if ln.startswith(str(t["letter55"]))][0]
    assert _m.LETTER_HEADER in entry and "The hills are lovely.  Kupo!" in entry
    # the built moogle still runs every path; the letter ops ride along as no-ops in the VM
    body = _moogle_talk_body(eb)
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    _set_slot(G0, 0, 55, 8, 41)
    G = run(body, G0, choices=[1, 0, 2])   # trailing Cancel: the reopened menu (donor cycle)
    assert _mailbox(G) == [(0, 0, 0, 0)] * 3 and _bit(G, _m.read_lock_bit(55)) == 1
    # and the letter window itself is in the emitted bytes: WindowAsync(3, 16, letter_txid) --
    # once per slot-consume arm (3) at each interact point (zone + moogle talk = 2)
    pat = bytes([0x20, 0x00, 0x03, 0x10]) + int(t["letter55"]).to_bytes(2, "little")
    assert eb.count(pat) == 6


def test_letter_validation(tmp_path, fake_roster):
    from ff9mapkit import build

    def probs(toml):
        p = tmp_path / "v.field.toml"
        p.write_text(toml, encoding="utf-8")
        return build.validate(build.FieldProject.load(p))

    bad = _FIELD.replace("accept = [55]", 'accept = [{ variant = 55, letter = 7 }]')
    assert any("letter must be a string" in x for x in probs(bad))
    bad = _FIELD.replace("accept = [55]", 'accept = [{ letter = "x" }]')
    assert any("accept entry must be" in x for x in probs(bad))
    bad = _FIELD.replace("accept = [55]", 'accept = [{ variant = 55, kupo = 1 }]')
    assert any("accept entry must be" in x for x in probs(bad))
    # the table form passes clean, and give-vs-accept collision still detects THROUGH the table form
    assert not [x for x in probs(_LETTER_FIELD) if "mognet" in x.lower()]
    bad = _FIELD.replace("accept = [55]", 'accept = [{ variant = 56 }]')
    assert any("both FROM and TO" in x for x in probs(bad))


# --------------------------------------------------------------------------- the mail-STATUS box ---
def test_status_entry_texts_reference_the_loaded_value_slots():
    e = _m.status_entry_texts()
    assert len(e) == 4
    texts = [t for t, _s, _t in e]
    assert "You have no mail" in texts[0] and "[TIME=-1]" in texts[0]
    assert "[TEXT=0,2]" in texts[1] and "[TEXT=0,3]" in texts[1]   # letter 1 = vars 2/3 (the donor's slots)
    assert "[TEXT=0,4]" in texts[2] and "[TEXT=0,5]" in texts[2]
    assert "[TEXT=0,6]" in texts[3] and "[TEXT=0,7]" in texts[3]
    assert texts[1].startswith("[WDTH=0,160,6,2,6,3,-1]")          # the stock width table, per line count
    assert _m.status_entry_texts("Empty bag, kupo")[0][0].count("Empty bag, kupo") == 1
    # THE GEOMETRY IS PART OF THE ENTRY: the stock [STRT] + the LOL (lower-left) tail ship with each
    # text -- the dialogue defaults ((10,1), UPR) mis-place the box (chest/ATE-title, third instance).
    assert [s for _t, s, _tl in e] == [(100, 1), (160, 1), (160, 2), (160, 3)]
    assert all(tl == "LOL" for _t, _s, tl in e)


def test_built_status_entries_carry_the_stock_geometry(tmp_path, fake_roster):
    """The .mes must ship [STRT=<stock>][TAIL=LOL] on every status entry -- the text alone centers."""
    _proj, ct, _eb = _built(tmp_path)
    mes, t = ct[0], ct[10][0]
    for si, strt in enumerate(((100, 1), (160, 1), (160, 2), (160, 3))):
        entry = [ln for ln in mes.split("_[TXID=") if ln.startswith(str(t[f"status{si}"]))][0]
        assert f"[STRT={strt[0]},{strt[1]}]" in entry, f"status{si} lost its STRT"
        assert "[TAIL=LOL]" in entry, f"status{si} lost its lower-left tail"


def test_status_window_picks_the_entry_by_occupancy():
    """The nested pick rides the compaction invariant: slots fill from 0."""
    for occupied, want in ((0, 100), (1, 101), (2, 102), (3, 103)):
        G0 = bytearray(2048)
        for k in range(occupied):
            _set_slot(G0, k, 60 + k, 2, 3)
        wins = []
        run(_m.mail_status_window([100, 101, 102, 103]), G0, windows=wins)
        assert wins == [(5, 8, want)], f"{occupied} letters -> {wins}"


def test_interaction_opens_status_then_closes_it():
    mog = _m.mognet_interaction_body(accept_variants=[55], nothing_txid=524,
                                     status_txids=[100, 101, 102, 103])
    ins = list(disasm.iter_code(mog, 0, len(mog)))
    closes = [i for i in ins if i.op == 0x21 and i.args == [5]]
    assert len(closes) >= 1 and closes[-1].off > max(i.off for i in ins if i.op == 0x20)
    # executed: empty mailbox -> the "no mail" status entry + the nothing line, nothing else
    wins = []
    G = run(mog, choices=[], windows=wins)
    assert (5, 8, 100) in wins and (1, 128, 524) in wins
    ref = bytearray(2048); ref[_m.GUARD_IDX] = 1
    assert bytes(G) == bytes(ref)


def test_letter_display_yields_the_status_box_first():
    ins = list(disasm.iter_code(_m.letter_display(900), 0, len(_m.letter_display(900))))
    assert ins[0].op == 0x21 and ins[0].args == [5]          # CloseWindow(5) leads (1865 @6177)


def test_built_field_shows_the_status_box(tmp_path, fake_roster):
    _proj, ct, eb = _built(tmp_path)
    t = ct[10][0]
    assert {"status0", "status1", "status2", "status3"} <= set(t)
    body = _moogle_talk_body(eb)
    # one held letter addressed elsewhere: the 1-letter status entry shows under the menus. This field
    # authors a give and the mailbox has room, so the offer opens -- decline it (second choice).
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    _set_slot(G0, 0, 19, 23, 1)
    wins = []
    run(body, G0, choices=[1, 1, 2], windows=wins)   # trailing Cancel: the reopened menu (donor cycle)
    assert (5, 8, t["status1"]) in wins
    assert (5, 8, t["status2"]) not in wins


# --------------------------------------------------------------------------- the three menu rows ---
from ff9mapkit.content import savepoint as _spm  # noqa: E402

_ALIVE = {0: (10, 100, 5, 50), 1: (200, 200, 0, 20), 2: (0, 80, 0, 30)}   # hurt / full / KO'd
_HAS_TENT = dict(_ALIVE); _HAS_TENT[("item", _spm.TENT_ITEM)] = 3


def test_tent_heals_half_of_max_and_never_revives():
    """The donor's formula (field 300 @5029): CUR + (MAX+1)/2 per slot, guarded by CURHP != 0 -- so a
    KO'd member is skipped entirely and an unheld slot (all zeros) likewise."""
    stats, items = [], []
    run(_spm.tent_rest_body(), party=_HAS_TENT, stats=stats, items=items)
    got = {(kind, slot): val for kind, slot, val in stats}
    assert got[("hp", 0)] == 10 + (100 + 1) // 2         # hurt -> half of max, rounded up
    assert got[("mp", 0)] == 5 + (50 + 1) // 2
    assert got[("hp", 1)] == 200 + (200 + 1) // 2        # already full -> SetHP clamps in-engine
    assert ("hp", 2) not in got and ("mp", 2) not in got  # KO'd: not revived
    assert all(slot in (0, 1) for _k, slot, _v in stats)  # unheld slots 3..7 skipped by the same guard
    assert items == [(_spm.TENT_ITEM, 1)]                 # exactly one tent consumed


def test_tent_dispatch_refuses_without_a_tent():
    stats, items, wins = [], [], []
    run(_spm.tent_dispatch(600, 601), party=_ALIVE, stats=stats, items=items, windows=wins)
    assert stats == [] and items == []                    # no heal, no consume
    assert wins == [(1, 128, 601)]                        # just the "no tents" line


def test_tent_dispatch_rests_on_yes_and_not_on_no():
    for pick, healed in ((0, True), (1, False)):
        stats, items, wins = [], [], []
        run(_spm.tent_dispatch(600, 601), party=_HAS_TENT, choices=[pick],
            stats=stats, items=items, windows=wins)
        assert wins == [(_spm.CHOICE_WINDOW, _spm.CHOICE_FLAGS, 600)]
        assert bool(stats) is healed and bool(items) is healed


def test_shop_and_party_rows_are_the_donor_pair():
    menus = []
    run(_spm.shop_dispatch(7), menus=menus)
    assert menus == [(2, 7)]                              # Menu(2, shopId)
    # an explicit min_size is the donor literal, verbatim -- field 300 @10675 is Party(4, 1)
    pm = []
    run(_spm.party_dispatch(min_size=4), party_menu=pm)
    assert pm == [(4, 1)]
    pm = []
    run(_spm.party_dispatch(min_size=0, locked=0), party_menu=pm)
    assert pm == [(0, 0)]


def test_party_row_min_size_clamps_to_the_live_party():
    """THE SOFTLOCK FIX (playtest 2026-07-18): the party screen's ONLY exit is
    `charCnt >= party_ct`, so a literal 4 with fewer than four characters is unescapable. The default
    now emits the runtime count instead -- equal to charCnt on entry, so the check always passes."""
    for members in ([0], [0, 1], [0, 1, 2], [0, 1, 2, 3]):
        pm = []
        run(_spm.party_dispatch(), party_menu=pm, in_party=set(members))
        assert pm == [(len(members), 1)], members         # never above the live size -> never locks
    # a FULL party reproduces the donor's literal exactly
    pm = []
    run(_spm.party_dispatch(), party_menu=pm, in_party={0, 2, 5, 7})
    assert pm == [(4, 1)]
    # characters outside the party never count (the expression reads party.member[] only)
    pm = []
    run(_spm.party_dispatch(), party_menu=pm, in_party={11})
    assert pm == [(1, 1)]


def test_menu_rows_follow_the_donor_order():
    assert _spm.menu_rows({}) == ["save", "cancel"]
    assert _spm.menu_rows({"tent": True, "party": True, "shop": 3}) == \
        ["save", "tent", "shop", "party", "cancel"]
    full = {"tent": True, "shop": 3, "party": True, "mognet": {"name": "Mogwai"}}
    assert _spm.menu_rows(full) == ["save", "tent", "mognet", "shop", "party", "cancel"]
    assert _spm.menu_rows({"mognet": {}}) == ["save", "cancel"]      # a nameless mognet is not a row


_ROWS_FIELD = _FIELD.replace(
    "[savepoint.mognet]",
    'tent = true\nparty = true\nshop = 80\n\n[[shop]]\nid = 80\nsells = ["Potion"]\n\n[savepoint.mognet]')


def test_built_six_row_menu_dispatches_every_row(tmp_path, fake_roster):
    _proj, ct, eb = _built(tmp_path, _ROWS_FIELD)
    mes, t = ct[0], ct[10][0]
    assert "[PCHC=6,5]" in mes                            # 6 rows, cancel last
    for label in ("Save", "Tent", "Mognet", "Mogshop", "Switch party members", "Cancel"):
        assert label in mes
    assert "(Tent(s) Remaining=[NUMB=7])" in mes and "tent_prompt" in t
    body = _moogle_talk_body(eb)
    # row 0 Save -> Yes (the built talk body carries the act -- apply its async-release contract)
    menus = []
    M = bytearray(2048)
    run(body, choices=[0, 0], menus=menus, M=M, on_async=act_async_contract(M))
    assert menus == [(4, 0)]
    # row 1 Tent -> Rest (with tents held)
    stats, items = [], []
    run(body, choices=[1, 0], party=_HAS_TENT, stats=stats, items=items)
    assert items == [(_spm.TENT_ITEM, 1)] and stats
    # row 3 Mogshop, row 4 party (the built default clamps the party min to the live party size)
    menus, pm = [], []
    run(body, choices=[3], menus=menus); assert menus == [(2, 80)]
    run(body, choices=[4], party_menu=pm, in_party={0, 1, 2, 3}); assert pm == [(4, 1)]
    pm = []
    run(body, choices=[4], party_menu=pm, in_party={0, 1}); assert pm == [(2, 1)]
    # row 5 Cancel -- nothing at all
    G = run(body, choices=[5]); assert bytes(G) == bytes(bytearray(2048))


def test_row_validation(tmp_path, fake_roster):
    from ff9mapkit import build

    def probs(toml):
        p = tmp_path / "v.field.toml"
        p.write_text(toml, encoding="utf-8")
        return build.validate(build.FieldProject.load(p))

    bad = _ROWS_FIELD.replace("shop = 80", "shop = 81")          # no [[shop]] with that id
    assert any("has no [[shop]] with that id" in x for x in probs(bad))
    bad = _ROWS_FIELD.replace("tent = true", 'tent = "yes"')
    assert any("tent must be true or false" in x for x in probs(bad))
    bad = _ROWS_FIELD.replace("party = true", "party = true\nparty_min = 9")
    assert any("party_min must be 0..4" in x for x in probs(bad))
    assert not [x for x in probs(_ROWS_FIELD) if "savepoint" in x.lower()]


# --------------------------------------------------------------------------- READ-MAIL ---
# The moogle re-reads its OWN received letters -- stock's third mechanic, decoded 2026-07-19 (donors
# 115/300/418/1102 + a 58-field census): rows gated on read_lock_bit, the payload rebuild into
# Byte[1064+k]/[1079+k], the masked "which letter" window, and the PURE re-display. Arrival (accept or
# a story-gated auto-arrival), not reading, sets the lock.

def test_read_row_population_is_the_donor_shape():
    """The per-row payload rebuild, byte- and behavior-pinned: mask seeds with the CANCEL bit, each row
    writes variant -> mask -> sender in the donor's order, gated on that variant's READ lock."""
    rows = [(55, 8), (57, 23)]
    body = _m.read_row_population(rows)
    # byte pin: row 0's write triplet, in the donor's exact order (field 115 @1246-1248 shape)
    triplet = (_m._set_byte(_m.PAYLOAD_VARIANT_BASE, 55)
               + _region.or_var(_region.GLOB_UINT16, _region.MASK_SCRATCH_IDX, 1)
               + _m._set_byte(_m.PAYLOAD_SENDER_BASE, 8))
    assert triplet in body
    # behavior: only the LOCKED row populates; the mask always carries the cancel bit (1 << 2 here)
    G0 = bytearray(2048)
    G0[_m.read_lock_bit(57) >> 3] |= 1 << (_m.read_lock_bit(57) & 7)
    G = run(body, G0)
    assert G[_m.PAYLOAD_VARIANT_BASE] == 0 and G[_m.PAYLOAD_SENDER_BASE] == 0      # row 0 unknown
    assert G[_m.PAYLOAD_VARIANT_BASE + 1] == 57 and G[_m.PAYLOAD_SENDER_BASE + 1] == 23
    assert G[_region.MASK_SCRATCH_IDX] | (G[_region.MASK_SCRATCH_IDX + 1] << 8) == 0x8000 | 2
    # the payload lands inside the band flags.py reserves for exactly this
    from ff9mapkit import flags as _flags
    for k in range(len(rows)):
        assert _flags.READMAIL_PAYLOAD_LO <= (_m.PAYLOAD_VARIANT_BASE + k) * 8 <= _flags.READMAIL_PAYLOAD_HI
        assert _flags.READMAIL_PAYLOAD_LO <= (_m.PAYLOAD_SENDER_BASE + k) * 8 <= _flags.READMAIL_PAYLOAD_HI
    with pytest.raises(ValueError, match="at most"):
        _m.read_row_population([(49 + i, 0) for i in range(11)])


def test_read_available_cond_is_an_or_over_the_locks():
    cond = _m.read_available_cond([55, 57])
    assert _eval_expr(cond[1:], bytearray(2048)) == 0
    G = bytearray(2048)
    G[_m.read_lock_bit(57) >> 3] |= 1 << (_m.read_lock_bit(57) & 7)
    assert _eval_expr(cond[1:], G) == 1
    with pytest.raises(ValueError, match="at least one"):
        _m.read_available_cond([])


def test_read_mail_body_is_a_pure_read():
    """Selecting a known letter re-displays it and touches NOTHING: no lock write, no mailbox write,
    no counter -- the donor's re-read law (the letter never leaves the list). The sender text var is
    re-seeded FROM THE PAYLOAD BYTE, the donor's own read-back idiom."""
    rows = [(55, 8), (57, 23)]
    body = _m.read_mail_body(rows, 90, {55: 91, 57: 92})
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    G0[_m.DELIVERED_IDX] = 12
    _set_slot(G0, 0, 19, 23, 1)                                    # a held letter must survive a read
    for v in (55, 57):
        G0[_m.read_lock_bit(v) >> 3] |= 1 << (_m.read_lock_bit(v) & 7)
    wins, masks = [], []
    G = run(body, G0, choices=[1], windows=wins, masks=masks)
    assert masks == [0x8000 | 1 | 2]                               # both rows + Cancel at bit 15
    assert (2, 8, 90) in wins and (3, 16, 92) in wins              # the list, then row 1's letter
    assert (3, 16, 91) not in wins
    # pure: everything outside the payload/scratch bytes is untouched
    diff = {i for i in range(2048) if G[i] != G0[i]}
    allowed = ({_m.PAYLOAD_VARIANT_BASE + k for k in range(2)}
               | {_m.PAYLOAD_SENDER_BASE + k for k in range(2)}
               | {_region.MASK_SCRATCH_IDX, _region.MASK_SCRATCH_IDX + 1})
    assert diff <= allowed, sorted(diff - allowed)
    assert G[_m.DELIVERED_IDX] == 12 and _mailbox(G)[0] == (1, 19, 23, 1)
    # re-reading is idempotent: a second identical run changes nothing further
    G2 = run(body, bytearray(G), choices=[1], windows=[], masks=[])
    assert bytes(G2) == bytes(G)
    # cancel is bodiless
    wins2 = []
    run(body, G0, choices=[2], windows=wins2)
    assert not any(w[0] == 3 for w in wins2)


def test_arrival_fires_once_gated_and_sets_the_lock():
    """A `received` letter auto-arrives when its story condition holds: announce + letter + READ lock
    (arrival sets the lock, the donor law) -- and never again (the lock is the once-guard)."""
    entries = [(57, 23, 8720, None)]                               # requires_flag 8720
    body = _m.arrival_body(entries, arrive_txid=80, letter_txids={57: 81})
    # gate closed -> nothing at all
    wins = []
    G = run(body, windows=wins)
    assert wins == [] and _bit(G, _m.read_lock_bit(57)) == 0
    # gate open -> the full arrival, lock set
    G0 = bytearray(2048)
    G0[8720 >> 3] |= 1 << (8720 & 7)
    wins = []
    G = run(body, G0, windows=wins)
    assert (1, 128, 80) in wins and (3, 16, 81) in wins
    assert _bit(G, _m.read_lock_bit(57)) == 1
    # second visit: arrived already -> silent
    wins = []
    G2 = run(body, G, windows=wins)
    assert wins == [] and bytes(G2) == bytes(G)


def test_arrival_scenario_gate():
    entries = [(58, 1, None, 2500)]                                # requires_scenario 2500
    body = _m.arrival_body(entries, letter_txids={58: 81})
    G0 = bytearray(2048)
    G0[0:2] = (2400).to_bytes(2, "little")
    G = run(body, G0, windows=[])
    assert _bit(G, _m.read_lock_bit(58)) == 0                      # before the beat
    G0[0:2] = (2500).to_bytes(2, "little")
    wins = []
    G = run(body, G0, windows=wins)
    assert _bit(G, _m.read_lock_bit(58)) == 1 and (3, 16, 81) in wins


# --------------------------------------------------- READ-MAIL: the built field, end to end ---
_RM_FIELD = (
    '[field]\nid = 4005\nname = "S"\narea = 11\ntext_block = 30110\nregister_text_block = true\n\n'
    '[camera]\npitch = 45\nfov = 42.2\n\n'
    '[walkmesh]\nquad = [[-400,-400],[400,-400],[400,400],[-400,400]]\n\n'
    '[[savepoint]]\nzone = [[-100,-100],[100,-100],[100,100],[-100,100]]\n'
    '[savepoint.mognet]\nname = "Mogwai"\n'
    'accept = [{ variant = 55, letter = "So good to hear from you, kupo!", from = "Kumop", '
    'title = "A Warm Hello" }]\n'
    'give = { variant = 56, to = "Kupo" }\n'
    'received = [{ variant = 57, from = "Kuppo", title = "News From The Mines", '
    'letter = "The mines are quiet again, kupo.", requires_flag = 8720 }]\n')


def test_built_read_mail_text_ships_the_two_menus(tmp_path, fake_roster):
    _proj, ct, _eb = _built(tmp_path, _RM_FIELD)
    mes, t = ct[0], ct[10][0]
    assert {"menu_prompt", "read_prompt", "arrive", "letter55", "letter57",
            "read_rows_meta", "received_meta"} <= set(t)
    assert "[PCHM=3,2]" in mes and "Give Mogwai a letter" in mes and "Read mail" in mes
    assert "[PCHM=16,15]" in mes and "A Warm Hello" in mes and "News From The Mines" in mes
    assert t["read_rows_meta"] == [(55, 8), (57, 23)]              # Kumop=8, Kuppo=23, authored order
    assert t["received_meta"] == [(57, 23, 8720, None)]


def test_built_read_mail_full_lifecycle(tmp_path, fake_roster):
    """The crown test's read-mail sibling, straight from the shipped bytes: the arrival fires once on
    its story flag, the accept feeds the same list, reads are pure and repeatable, and the give offer
    is STILL reachable in the same talk (cancel out of the submenu -> the offer -- the flow bug the
    naive accept>read priority chain would have had)."""
    _proj, ct, eb = _built(tmp_path, _RM_FIELD)
    t = ct[10][0]
    body = _moogle_talk_body(eb)
    # ---- visit 1: nothing known, flag clear -> the v1 give-offer path (decline it) ----
    wins = []
    G = run(body, choices=[1, 1, 2], windows=wins)                 # Mognet -> give offer -> "Not now" -> Cancel the reopened menu
    assert (2, 8, t["give_prompt"]) in wins and not any(w[0] == 3 for w in wins)
    # ---- visit 2: the story flag is set -> the ARRIVAL, then the submenu exists; cancel out ->
    #      the give offer fires in the SAME talk (decline) ----
    G[8720 >> 3] |= 1 << (8720 & 7)
    wins, masks = [], []
    G = run(body, G, choices=[1, 2, 1, 2], windows=wins, masks=masks)
    assert (1, 128, t["arrive"]) in wins and (3, 16, t["letter57"]) in wins
    assert _bit(G, _m.read_lock_bit(57)) == 1
    assert masks[0] == 4 | 2                                       # submenu: read known, no delivery
    assert (2, 8, t["menu_prompt"]) in wins and (2, 8, t["give_prompt"]) in wins
    # ---- visit 3: re-read via the submenu; pure + repeatable ----
    wins, masks = [], []
    G3 = run(body, bytearray(G), choices=[1, 1, 1, 1, 2], windows=wins, masks=masks)
    # Mognet -> Read mail -> row 1 (News From The Mines) -> then the give offer, declined
    assert masks == [4 | 2, 0x8000 | 2]                            # submenu, then the which-letter list
    assert (2, 8, t["read_prompt"]) in wins and (3, 16, t["letter57"]) in wins
    assert (1, 128, t["arrive"]) not in wins                       # the arrival never re-fires
    G4 = run(body, bytearray(G3), choices=[1, 1, 1, 1, 2], windows=[], masks=[])
    assert bytes(G4) == bytes(G3)                                  # byte-stable across repeat reads
    # ---- visit 4: a delivery TO Mogwai pending -> submenu row 0 = the accept; then read lists BOTH ----
    _set_slot(G4, 0, 55, 8, 41)
    G4[_m.GUARD_IDX] = 1
    wins, masks = [], []
    G5 = run(body, bytearray(G4), choices=[1, 0, 0, 1, 2], windows=wins, masks=masks)
    # Mognet -> submenu accept -> confirm Yes -> (letter displays) -> give offer declined
    assert masks[0] == 4 | 1 | 2                                   # delivery pending + letters known
    assert (3, 16, t["letter55"]) in wins and _bit(G5, _m.read_lock_bit(55)) == 1
    assert _mailbox(G5)[0] == (0, 0, 0, 0) and G5[_m.DELIVERED_IDX] == 1
    wins, masks = [], []
    run(body, bytearray(G5), choices=[1, 1, 0, 1, 2], windows=wins, masks=masks)
    assert masks == [4 | 2, 0x8000 | 1 | 2]                        # read list now carries BOTH rows
    assert (3, 16, t["letter55"]) in wins                          # row 0 re-displays the accept letter
    # ---- and the mailbox-status + save rows never regressed: Save -> Yes still fires Menu(4,0) ----
    menus = []
    M = bytearray(2048)
    run(body, choices=[0, 0], menus=menus, M=M, on_async=act_async_contract(M))
    assert menus == [(4, 0)]


def test_read_mail_validation_gates(tmp_path, fake_roster):
    from ff9mapkit import build

    def probs(toml):
        p = tmp_path / "v.field.toml"
        p.write_text(toml, encoding="utf-8")
        return build.validate(build.FieldProject.load(p))

    # from without title (and vice versa) on an accept entry -> half a row, refused
    bad = _RM_FIELD.replace(', title = "A Warm Hello"', "")
    assert any("come together" in x for x in probs(bad))
    # a titled accept row without a letter body -> nothing to re-display, refused
    bad = _RM_FIELD.replace('letter = "So good to hear from you, kupo!", ', "")
    assert any("needs the `letter` body" in x for x in probs(bad))
    # a received entry missing a required key -> refused
    bad = _RM_FIELD.replace('letter = "The mines are quiet again, kupo.", ', "")
    assert any("received entry must be" in x for x in probs(bad))
    # the same variant authored twice (accept + received) -> the locks are save-global, refused
    bad = _RM_FIELD.replace("variant = 57", "variant = 55")
    assert any("authored twice" in x for x in probs(bad))
    # give colliding with received -> refused
    bad = _RM_FIELD.replace("variant = 57", "variant = 56")
    assert any("also in received" in x for x in probs(bad))
    # a shipped variant in received -> refused
    bad = _RM_FIELD.replace("variant = 57", "variant = 19")
    assert any("SHIPPED band" in x for x in probs(bad))
    # the clean field validates clean
    assert not [x for x in probs(_RM_FIELD) if "mognet" in x.lower()]


# --------------------------------------------- READ-MAIL: the adversarial-review escape probes ---
def test_read_menu_is_the_stock_fixed_16_row_shape(tmp_path, fake_roster):
    """The donor's which-letter window is a FIXED 16-line entry (authored titles, then 'Letter NN'
    dead filler, Cancel at row 15 / mask bit 0x8000) -- 100% uniform across all 58 stock moogle
    fields. The review caught our first cut sizing it dynamically; this pins the stock shape."""
    _proj, ct, _eb = _built(tmp_path, _RM_FIELD)
    seg = ct[0].split("[PCHM=16,15]", 1)[1]
    assert "A Warm Hello" in seg and "News From The Mines" in seg
    for i in range(2, 15):                                         # rows 2..14 = dead filler
        assert f"Letter {i:02d}" in seg
    G = run(_m.read_row_population([(55, 8), (57, 23)]))           # nothing known yet
    assert G[_region.MASK_SCRATCH_IDX] | (G[_region.MASK_SCRATCH_IDX + 1] << 8) == 0x8000


def test_read_mail_pure_even_with_lock_clear():
    """The review's escaped mutation: a lock write smuggled into a row's re-display arm passed every
    test, because the lifecycle only reads rows whose lock is ALREADY set. Force the pick with the
    lock CLEAR: a pure read must leave it clear."""
    body = _m.read_mail_body([(55, 8)], 90, {55: 91})
    G = run(body, choices=[0], windows=[])
    assert _bit(G, _m.read_lock_bit(55)) == 0


def test_arrival_combined_flag_and_scenario_gate():
    """BOTH gates on one entry -- the RPN path a review probe proved untested (dropping the ANDAND
    between the scenario compare and the flag escaped the whole suite). Neither gate alone opens it."""
    entries = [(59, 1, 8720, 2500)]
    body = _m.arrival_body(entries, letter_txids={59: 81})
    G0 = bytearray(2048)
    G0[0:2] = (2500).to_bytes(2, "little")                         # scenario only
    assert _bit(run(body, G0), _m.read_lock_bit(59)) == 0
    G1 = bytearray(2048)
    G1[8720 >> 3] |= 1 << (8720 & 7)                               # flag only
    assert _bit(run(body, G1), _m.read_lock_bit(59)) == 0
    G1[0:2] = (2500).to_bytes(2, "little")                         # both -> arrives
    assert _bit(run(body, G1), _m.read_lock_bit(59)) == 1


def test_give_offer_is_one_shot_through_the_submenu(tmp_path, fake_roster):
    """The review proved give_available_cond was removable from the submenu's trailing offer without
    a failure. Accept the give once; the offer must never come back."""
    _proj, ct, eb = _built(tmp_path, _RM_FIELD)
    t = ct[10][0]
    body = _moogle_talk_body(eb)
    G = bytearray(2048)
    G[8720 >> 3] |= 1 << (8720 & 7)                                # the arrival -> the submenu exists
    wins = []
    G = run(body, G, choices=[1, 2, 0, 2], windows=wins)           # arrival; cancel submenu; TAKE the give; Cancel the reopened menu
    assert (2, 8, t["give_prompt"]) in wins
    assert _bit(G, _m.give_lock_bit(56)) == 1 and _mailbox(G)[0][1] == 56
    wins = []
    run(body, bytearray(G), choices=[1, 2, 2], windows=wins)       # reopen; cancel -> NO offer window; Cancel the reopened menu
    assert (2, 8, t["give_prompt"]) not in wins


def test_built_ungated_and_scenario_arrivals_with_bespoke_announce(tmp_path, fake_roster):
    """The two arrival lanes the built-field tests missed: an UNGATED letter (arrives on the first
    Mognet open) and a requires_scenario letter carrying its OWN announce line (stock announces each
    letter with bespoke text; the shared arrive_line is only the fallback)."""
    toml = _RM_FIELD.replace(
        'received = [{ variant = 57, from = "Kuppo", title = "News From The Mines", '
        'letter = "The mines are quiet again, kupo.", requires_flag = 8720 }]',
        'received = [{ variant = 57, from = "Kuppo", title = "News From The Mines", '
        'letter = "The mines are quiet again, kupo." }, '
        '{ variant = 58, from = "Kupo", title = "Steeple Bells", '
        'letter = "The bells rang twice today, kupo.", requires_scenario = 2500, '
        'announce = "A bell-stamped letter, kupo!" }]')
    _proj, ct, eb = _built(tmp_path, toml)
    t = ct[10][0]
    body = _moogle_talk_body(eb)
    wins = []
    G = run(body, choices=[1, 2, 1, 2], windows=wins)              # first open: 57 arrives, 58 waits
    assert _bit(G, _m.read_lock_bit(57)) == 1 and _bit(G, _m.read_lock_bit(58)) == 0
    assert (1, 128, t["arrive"]) in wins and (3, 16, t["letter57"]) in wins
    G[0:2] = (2500).to_bytes(2, "little")                          # cross the beat
    wins = []
    G = run(body, G, choices=[1, 2, 1, 2], windows=wins)
    assert _bit(G, _m.read_lock_bit(58)) == 1
    assert (1, 128, t["announce58"]) in wins and (3, 16, t["letter58"]) in wins
    assert (1, 128, t["arrive"]) not in wins                       # bespoke replaces the shared line


def test_read_mail_validation_hardening(tmp_path, fake_roster):
    from ff9mapkit import build

    def probs(toml):
        p = tmp_path / "v.field.toml"
        p.write_text(toml, encoding="utf-8")
        return build.validate(build.FieldProject.load(p))

    bad = _RM_FIELD.replace("requires_flag = 8720", "requires_flag = true")
    assert any("requires_flag must be an int" in x for x in probs(bad))
    bad = _RM_FIELD.replace("requires_flag = 8720", "requires_scenario = -5")
    assert any("0..32767" in x for x in probs(bad))
    bad = _RM_FIELD.replace("requires_flag = 8720", "requires_flag = 8400")     # the Mognet lock band
    assert any("reserved" in x for x in probs(bad))
    bad = _RM_FIELD.replace('title = "A Warm Hello"', 'title = "  "')
    assert any("non-blank" in x for x in probs(bad))
    bad = _RM_FIELD.replace("requires_flag = 8720", 'requires_flag = 8720, announce = ""')
    assert any("announce must be" in x for x in probs(bad))
    # the 10-row payload cap: 1 titled accept + 10 received = 11 rows -> refused at validate time
    rows = ", ".join(f'{{ variant = {v}, from = "Kupo", title = "L{v}", letter = "x, kupo." }}'
                     for v in (49, 50, 51, 52, 53, 54, 57, 58, 59, 60))   # 10, clear of 55/56
    bad = _RM_FIELD.replace(
        'received = [{ variant = 57, from = "Kuppo", title = "News From The Mines", '
        'letter = "The mines are quiet again, kupo.", requires_flag = 8720 }]',
        f"received = [{rows}]")
    assert any("payload budget" in x for x in probs(bad))
    # error attribution: a bad received.from names ITS OWN key, not give.to
    from ff9mapkit.content import mognet as _mg
    with pytest.raises(ValueError, match="received.from"):
        _mg.resolve_moogle_id("NoSuchMoogle", ["Kupo"], field_label="received.from")


def test_stolen_ember_example_lints_clean_in_the_new_band():
    """The review's CRITICAL find: the shipped flagship campaign still allocated flags at 8600-8625 --
    inside the newly-reserved read-mail payload band -- and nothing in CI would have caught it. This
    lints the real example so the next band change fails here instead of on a user's machine."""
    from pathlib import Path
    from ff9mapkit import campaign
    ember = Path(__file__).resolve().parents[2] / "examples" / "stolen-ember"
    if not (ember / "campaign.toml").is_file():
        pytest.skip("stolen-ember example not present")
    plan = campaign.load_campaign(ember / "campaign.toml")
    assert plan.flag_base >= campaign.FIRST_SAFE_FLAG
    errors, _warnings = campaign.lint_campaign(plan, ember)
    band_errors = [e for e in errors if "flag" in e.lower()]
    assert not band_errors, band_errors
