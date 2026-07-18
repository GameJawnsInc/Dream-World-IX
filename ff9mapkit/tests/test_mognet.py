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


# --------------------------------------------------------------------------- the mini-VM ---
def _eval_expr(tokens: bytes, G: bytearray, sysread=None) -> int:
    """Evaluate one 0x05 expression's token stream (sans the leading 05) against gEventGlobal ``G``.
    ``sysread(code)`` services GetSysvar tokens (0x7A) -- the tests script dialog choices through it."""
    stack: list = []

    def deref(x):
        kind, v = x
        if kind == "c":
            return v
        if kind == "by":
            return G[v]
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
        elif t == _region.T_SYSVAR:                                    # 0x7A GetSysvar(code)
            code = tokens[p]; p += 1
            if sysread is None:
                raise AssertionError(f"mini-VM: unscripted GetSysvar({code})")
            stack.append(("c", int(sysread(code))))
        elif t == _region.T_NOT:
            stack.append(("c", 0 if deref(stack.pop()) else 1))
        elif t in (_region.T_LT, _region.T_EQ, _m._T_NE, _m._T_ANDAND, _m._T_OROR):
            b, a = deref(stack.pop()), deref(stack.pop())
            r = {_region.T_LT: a < b, _region.T_EQ: a == b, _m._T_NE: a != b,
                 _m._T_ANDAND: bool(a) and bool(b), _m._T_OROR: bool(a) or bool(b)}[t]
            stack.append(("c", 1 if r else 0))
        elif t == _region.T_ASSIGN:
            val = deref(stack.pop())
            kind, idx = stack.pop()
            if kind == "by":
                G[idx] = val & 0xFF
            elif kind == "bi":
                if val:
                    G[idx >> 3] |= 1 << (idx & 7)
                else:
                    G[idx >> 3] &= ~(1 << (idx & 7)) & 0xFF
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


def run(body: bytes, G: bytearray | None = None, choices=None, menus=None) -> bytearray:
    """Execute an emitted body over a (simulated) 2048-byte gEventGlobal; windows/text ops are no-ops.

    ``choices`` scripts the player's dialog picks: each read of GetSysvar(9) consumes the next entry
    (the engine's own contract -- every menu re-reads the choice register after its window). ``menus``,
    if a list, collects every Menu(id, sub) call so a test can assert the save fired (or didn't)."""
    G = bytearray(2048) if G is None else bytearray(G)
    raw = bytes(body)
    queue = list(choices or [])

    def sysread(code):
        if code != 9:
            raise AssertionError(f"mini-VM: unexpected GetSysvar({code})")
        if not queue:
            raise AssertionError("mini-VM: the body read a choice the test did not script")
        return queue.pop(0)

    pos, last = 0, 0
    while pos < len(raw):
        i, nxt = disasm.read_code(raw, pos)
        if i.op == 0x05:
            last = _eval_expr(raw[i.off + 1:i.off + i.length], G, sysread)
        elif i.op == 0x01:                             # unconditional forward hop
            nxt += i.args[0]
        elif i.op == 0x02:                             # jump-if-false
            nxt += 0 if last else i.args[0]
        elif i.op == 0x03:                             # jump-if-true
            nxt += i.args[0] if last else 0
        elif i.op == 0x0B:                             # the op_0B switch -- dispatch on the last expr
            info = disasm.decode_switch(i)
            edge = next((e for e in info.edges if e.value == last),
                        next(e for e in info.edges if e.is_default))
            pos = edge.target
            continue
        elif i.op == 0x75:                             # Menu -- record, never "open"
            if menus is not None:
                menus.append((i.args[0], i.args[1]))
        elif i.op == 0x04:                             # RETURN -- halt
            break
        elif i.op in (0x1F, 0x20, 0x66,                # WindowSync / WindowAsync / SetTextVariable
                      0x22,                            # Wait
                      0x2D, 0x2E, 0xAB, 0xAA):         # Disable/EnableMove, Disable/EnableMenu
            pass
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
    eb = build.build_script(proj, "us", {}, savepoint_txids=ct[-1])
    return proj, ct, eb


def test_build_ships_the_roster_and_the_three_row_menu(tmp_path, fake_roster):
    _proj, ct, _eb = _built(tmp_path)
    mes, sp_txids = ct[0], ct[-1]
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
    # Save -> Yes: the latched Menu(4,0)
    menus = []
    run(body, choices=[0, 0], menus=menus)
    assert menus == [(4, 0)]
    # Mognet with the player's real letter (Kuppo->Kupo) held + ours pending delivery TO us:
    G0 = bytearray(2048)
    G0[_m.GUARD_IDX] = 1
    G0[_m.DELIVERED_IDX] = 12
    _set_slot(G0, 0, 19, 23, 1)                        # the live save's actual letter
    _set_slot(G0, 1, 55, 8, 41)                        # a letter addressed to Mogwai
    G = run(body, G0, choices=[1, 0])
    assert _mailbox(G) == [(1, 19, 23, 1), (0, 0, 0, 0), (0, 0, 0, 0)]   # ours consumed, theirs SURVIVES
    assert G[_m.DELIVERED_IDX] == 13 and _bit(G, _m.read_lock_bit(55)) == 1
    # Mognet again, nothing addressed to us now -> the give offer -> accept it
    G2 = run(body, G, choices=[1, 0])
    assert _mailbox(G2)[1] == (1, 56, 41, 1)           # FROM Mogwai (41) TO Kupo (1), first free slot
    assert _bit(G2, _m.give_lock_bit(56)) == 1
    # Mognet a third time: letter handed out, nothing held -> case (c), a pure no-op
    G3 = run(body, G2, choices=[1])
    assert bytes(G3) == bytes(G2)


def test_zone_region_carries_the_same_mognet_dispatch(tmp_path, fake_roster):
    _proj, ct, eb = _built(tmp_path)
    # both interact points (zone action + moogle talk) open the 3-row prompt: count its WindowSync
    t = ct[-1][0]
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
