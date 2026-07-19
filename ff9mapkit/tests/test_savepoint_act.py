"""The save moogle's ACT -- content/savepoint.py's choreography synthesis, VM-executed + build-proven.

Grounding (the 4-agent decode + census, 2026-07-18): the interact-time act is ONE template across all
57 moogle save instances -- hop 6503 / book 133 + feather 134 appear / moogle-open 4645 / ``Menu(4,0)``
/ hide / hop back -- and it fires ONLY on the confirmed scripted Yes (the donor's decline law). These
tests EXECUTE the emitted bodies in test_mognet's mini-VM (recording choreography as events) and build
a whole field to prove the cluster wiring: the props exist hidden with the right models/clips, the
moogle seats at the slot its grafts reference, the player gains the pose/release tags, and the press
REGION stays actless (a type-1 region has no model to animate)."""
from __future__ import annotations

import pytest

from ff9mapkit.content import region as _region
from ff9mapkit.content import savepoint as _sp
from ff9mapkit.eb import EbScript, disasm, opcodes

from tests.test_mognet import act_async_contract, run

# --------------------------------------------------------------------------- byte pins vs the donor ---


def test_act_byte_pins_vs_the_donor():
    """The census's ground-truth hex, byte for byte (field 300 offsets quoted in the census report)."""
    assert opcodes.run_animation(_sp.ACT_HOP_CLIP) == bytes.fromhex("40006719")
    assert opcodes.run_animation(_sp.ACT_OPEN_CLIP) == bytes.fromhex("40002512")
    assert opcodes.menu(4, 0) == bytes.fromhex("75000400")
    assert _sp.act_sfx(_sp.SFX_HOP) == bytes.fromhex("c80000d05205000000807d")
    assert opcodes.set_jump_animation(_sp.ACT_HOP_CLIP, 26, 30) == bytes.fromhex("940067191a1e")
    # the clip-law corrections the census nailed down: the feather opens with 4652, NOT 4651
    assert _sp.ACT_FEATHER_OPEN_CLIP == 4652 and _sp.ACT_BOOK_OPEN_CLIP == 4641
    # the prop models resolve to the census's universal ids (book 57/57, feather 55/57)
    from ff9mapkit import catalog
    assert catalog.resolve_model(_sp.ACT_BOOK_MODEL) == 133
    assert catalog.resolve_model(_sp.ACT_FEATHER_MODEL) == 134


def test_obj_field_expression_matches_the_donor_snap():
    """The book's snap-to-moogle reads the moogle's LIVE position: ``a1 07 78 03 00 7f ...`` (field 300
    @10864, moogle uid 3). Reproduce that exact instruction for uid 3."""
    ins = opcodes.encode(0xA1, _sp._obj_field(3, 0), _sp._obj_field(3, 1), _sp._obj_field(3, 2),
                         arg_flags=0b111)
    assert ins == bytes.fromhex("a1077803007f7803017f7803027f")


def test_act_timing_bytes_are_the_donor_values():
    """The Wait counts are LOAD-BEARING (the donor calibrated them to real clip/SFX durations -- act
    decode item 9.4: 'copied verbatim alongside the opcodes'). Pin the emitted BYTE RUNS, so a mutated
    constant fails here, not in a playtest (the review's mutation probe sailed through the old suite):
    hop + chime + Wait(24) + landing thud, the pre-open Wait(12) + chime, and open + Wait(68) into the
    latch. Also the exact SetTurnSpeed(32) opener and the player funcs' TurnTowardObject speed 16."""
    body = _act_body()
    hop_out = (opcodes.run_animation(6503) + _sp.act_sfx(1362)
               + opcodes.wait(24) + _sp.act_sfx(2631))
    hop_back = (opcodes.run_animation(6503) + _sp.act_sfx(1362)
                + opcodes.wait(24) + _sp.act_sfx(682))
    pre_open = (opcodes.wait(12) + _sp.act_sfx(1362)
                + opcodes.run_script_async(4, 4, _sp.ACT_APPEAR_TAG))
    open_hold = opcodes.run_animation(4645) + opcodes.wait(68)
    for run_bytes in (hop_out, hop_back, pre_open, open_hold):
        assert run_bytes in body, run_bytes.hex()
    assert body.startswith(opcodes.encode(0x99, 32))            # SetTurnSpeed(32)
    assert (_sp.ACT_HOP_AIR_WAIT, _sp.ACT_PROP_WAIT, _sp.ACT_OPEN_WAIT) == (24, 12, 68)
    assert opcodes.wait(12) + opcodes.encode(0x93, 7) in _sp.act_prop_appear_body(3, 4641)
    assert _sp.player_pose_body(3).startswith(opcodes.turn_toward_object(3, 16))


# --------------------------------------------------------------------------- the act body, executed ---


def _act_body(**kw):
    args = dict(book_uid=4, feather_uid=5, pose_tag=64, release_tag=65, act_txid=30,
                rest=(-100, 200), hop_to=None, latch=True)
    args.update(kw)
    return _sp.act_save_body(**args)


def _run_act(body, **kw):
    events, menus, windows = [], [], []
    M = bytearray(2048)
    G = run(body, events=events, menus=menus, windows=windows, M=M,
            on_async=act_async_contract(M), **kw)
    return G, events, menus, windows, M


def test_act_event_order_is_the_donor_sequence():
    """Execute the act and assert the donor's order: hop -> the pre-open beat -> props appear -> open
    -> save -> props hide -> hop back -> release -- the landing thuds direction-asymmetric (2631 out,
    682 back) and the accent chime x3 (hop out / pre-open / hop back; the review caught the pre-open
    beat dropped -- field 300 @4559-4572)."""
    G, events, menus, windows, M = _run_act(_act_body())
    assert menus == [(4, 0)]
    anims = [e for e in events if e[0] == "anim"]
    assert [a[1][0] for a in anims] == [_sp.ACT_HOP_CLIP, _sp.ACT_OPEN_CLIP, _sp.ACT_HOP_CLIP]
    sfx = [e[1][1] for e in events if e[0] == "sfx"]
    assert sfx == [_sp.SFX_HOP, _sp.SFX_LAND_OUT, _sp.SFX_HOP, _sp.SFX_HOP, _sp.SFX_LAND_BACK]
    reqs = [e for e in events if e[0] == "req"]
    assert [tuple(r[1]) for r in reqs] == [
        (4, 250, 64),                       # the player pose
        (4, 4, _sp.ACT_APPEAR_TAG), (4, 5, _sp.ACT_APPEAR_TAG),
        (4, 4, _sp.ACT_HIDE_TAG), (4, 5, _sp.ACT_HIDE_TAG),
        (4, 250, 65),                       # the player release (clears the handshake -- the contract)
    ]
    # ordering across kinds: appear before the open clip, open before the save, hide after it
    def at(kind, args_pred=None, n=0):
        hits = [i for i, e in enumerate(events)
                if e[0] == kind and (args_pred is None or args_pred(e[1]))]
        return hits[n]
    i_appear = at("req", lambda a: a[1] == 4 and a[2] == _sp.ACT_APPEAR_TAG)
    i_open = at("anim", lambda a: a[0] == _sp.ACT_OPEN_CLIP)
    i_hide = at("req", lambda a: a[1] == 4 and a[2] == _sp.ACT_HIDE_TAG)
    assert at("anim") < i_appear < i_open < i_hide
    assert windows == [(1, 128, 30)]        # the save line, async, during the act
    # the save latch closed and NOTHING else in gEventGlobal moved
    assert bytes(G) == bytes(bytearray(2048))
    # the handshake bit ended CLEAR (set by the close-out, cleared by the release contract)
    n = _sp.ACT_HANDSHAKE_BIT
    assert (M[n >> 3] >> (n & 7)) & 1 == 0


def test_act_without_text_skips_the_window_only():
    _G, events, menus, windows, _M = _run_act(_act_body(act_txid=None))
    assert menus == [(4, 0)] and windows == []
    assert [e[1][0] for e in events if e[0] == "anim"] == [
        _sp.ACT_HOP_CLIP, _sp.ACT_OPEN_CLIP, _sp.ACT_HOP_CLIP]


def test_act_in_place_has_no_traversal_and_no_spin():
    """Without ``hop_to`` the moogle hops in place: zero MoveInstantXZY frames, zero TurnInstant
    (the landing 180° spin corrects the donor's fly-away facing -- pointless in place)."""
    _G, events, _m, _w, _M = _run_act(_act_body())
    assert not [e for e in events if e[0] == "pos"]
    assert not [e for e in events if e[0] == "turn"]


def _enc3(x, z, y=0):
    """A MoveInstantXZY event's recorded raw operands: (x, -y, z), unsigned u16 (the encoder's own
    arg convention -- opcodes.move_instant_xzy negates the height into arg2)."""
    return (x & 0xFFFF, (-y) & 0xFFFF, z & 0xFFFF)


def test_act_hop_to_emits_the_donor_lerp():
    """With a landing spot: 15 position frames out + 15 back (the donor's k=0..14 loop, unrolled),
    first frame = rest, last = the landing spot, and the 180° spin on both landings."""
    body = _act_body(hop_to=(-347, 7514))
    _G, events, menus, _w, _M = _run_act(body)
    assert menus == [(4, 0)]
    pos = [e for e in events if e[0] == "pos"]
    assert len(pos) == 30
    assert pos[0][1] == _enc3(-100, 200) and pos[14][1] == _enc3(-347, 7514)    # out: rest -> landing
    assert pos[15][1] == _enc3(-347, 7514) and pos[29][1] == _enc3(-100, 200)   # back: landing -> rest
    spins = [e for e in events if e[0] == "turn"]
    assert len(spins) == 2                   # one per landing, expression-arg (self.angle + 128)


def test_trunc_div_is_c_style():
    assert _sp._trunc_div(7, 2) == 3 and _sp._trunc_div(-7, 2) == -3
    assert _sp._trunc_div(13 * -50, 14) == -46      # the donor's own return-leg X delta at k=13


# --------------------------------------------------------------------------- the decline law ---


def _prompted(save_body):
    return _sp.save_dispatch_prompted(10, 11, save_body=save_body)


def test_decline_at_the_menu_skips_the_whole_act():
    events, menus = [], []
    run(_prompted(_act_body()), choices=[1], events=events, menus=menus)
    assert menus == [] and events == []


def test_decline_at_the_confirm_skips_the_whole_act():
    events, menus = [], []
    run(_prompted(_act_body()), choices=[0, 1], events=events, menus=menus)
    assert menus == [] and events == []


def test_confirmed_yes_runs_act_and_save_through_the_prompted_flow():
    events, menus = [], []
    M = bytearray(2048)
    run(_prompted(_act_body()), choices=[0, 0], events=events, menus=menus, M=M,
        on_async=act_async_contract(M))
    assert menus == [(4, 0)]
    assert [e[1][0] for e in events if e[0] == "anim"] == [
        _sp.ACT_HOP_CLIP, _sp.ACT_OPEN_CLIP, _sp.ACT_HOP_CLIP]


def test_handshake_poll_is_a_real_join():
    """Remove the release contract and the close-out's poll must spin into the VM's step guard --
    proof the join blocks on the player release rather than decorating it."""
    with pytest.raises(AssertionError, match="steps"):
        run(_act_body(), menus=[], max_steps=2000)


def test_while_truthy_shapes():
    """The poll helper: bit clear -> straight through; a body that clears the bit -> exactly one pass."""
    loop = _sp._while_truthy(_region.MAP_BOOL, _sp.ACT_HANDSHAKE_BIT, opcodes.wait(1))
    M = bytearray(2048)
    run(loop + opcodes.RETURN, M=M)                     # bit clear: zero iterations, clean exit
    body = opcodes.wait(1) + _region.set_var(_region.MAP_BOOL, _sp.ACT_HANDSHAKE_BIT, 0)
    loop2 = _sp._while_truthy(_region.MAP_BOOL, _sp.ACT_HANDSHAKE_BIT, body)
    n = _sp.ACT_HANDSHAKE_BIT
    M2 = bytearray(2048)
    M2[n >> 3] |= 1 << (n & 7)
    run(loop2 + opcodes.RETURN, M=M2, max_steps=200)    # one pass, then the cleared bit exits
    assert (M2[n >> 3] >> (n & 7)) & 1 == 0


# --------------------------------------------------------------------------- the prop + player funcs ---


def test_prop_appear_body_executes_and_shows():
    events = []
    run(_sp.act_prop_appear_body(6, _sp.ACT_BOOK_OPEN_CLIP, poof=True), events=events)
    kinds = [e[0] for e in events]
    assert kinds[0] == "sfx" and events[0][1][1] == _sp.SFX_POOF        # the book's poof, first
    assert "pos" in kinds and "turn" in kinds                            # snap + face the moogle
    i_anim = kinds.index("anim")
    assert events[i_anim][1][0] == _sp.ACT_BOOK_OPEN_CLIP
    i_show = next(i for i, e in enumerate(events) if e[0] == "flags")
    assert events[i_show][1][0] == 7 and i_anim < i_show                 # anim, THEN show (donor order)
    sizes = [e[1] for e in events if e[0] == "size"]
    assert sizes == [(255, s, s, s) for s in (16, 32, 48, 64)]           # the 4-step grow-in
    feather = []
    run(_sp.act_prop_appear_body(6, _sp.ACT_FEATHER_OPEN_CLIP), events=feather)
    assert [e[0] for e in feather].count("sfx") == 0                     # no poof on the feather


def test_prop_hide_body_is_the_instant_vanish():
    assert _sp.act_prop_hide_body() == bytes.fromhex("93000e") + opcodes.RETURN


def test_player_funcs_turn_toward_the_moogle():
    events = []
    run(_sp.player_pose_body(9), events=events)
    assert events == [("turnobj", (9, 16)), ("waitturn", ())]
    events2 = []
    M = bytearray(2048)
    n = _sp.ACT_HANDSHAKE_BIT
    M[n >> 3] |= 1 << (n & 7)
    run(_sp.player_release_body(9), events=events2, M=M)
    assert events2[0] == ("turnobj", (9, 16))
    assert (M[n >> 3] >> (n & 7)) & 1 == 0               # the release CLEARS the handshake


# --------------------------------------------------------------------------- the build wiring ---

_FIELD = (
    '[field]\nid = 4009\nname = "ACT"\narea = 11\ntext_block = 30111\nregister_text_block = true\n\n'
    '[camera]\npitch = 45\nfov = 42.2\n\n'
    '[walkmesh]\nquad = [[-400,-400],[400,-400],[400,400],[-400,400]]\n\n'
    '[[savepoint]]\nzone = [[-100,-100],[100,-100],[100,100],[-100,100]]\n')


def _built(tmp_path, toml=_FIELD):
    from ff9mapkit import build
    p = tmp_path / "act.field.toml"
    p.write_text(toml, encoding="utf-8")
    proj = build.FieldProject.load(p)
    probs = [x for x in build.validate(proj) if "savepoint" in x.lower()]
    assert not probs, probs
    ct = build.collect_text(proj)
    eb = build.build_script(proj, "us", {}, savepoint_txids=ct[-1])
    return proj, ct, eb


def _entry_with_model(eb_bytes, model):
    s = EbScript.from_bytes(eb_bytes)
    out = []
    for e in s.entries:
        if e is None or e.empty:
            continue
        f0 = e.func_by_tag(0)
        if f0 is not None and any(i.op == 0x2F and i.args and i.args[0] == model
                                  for i in disasm.iter_code(eb_bytes, f0.abs_start, f0.abs_end)):
            out.append(e)
    return out


def test_build_injects_the_act_cluster(tmp_path):
    _proj, ct, eb = _built(tmp_path)
    t = ct[-1][0]
    assert "act" in t                                            # the save line was minted
    books, feathers = _entry_with_model(eb, 133), _entry_with_model(eb, 134)
    assert len(books) == 1 and len(feathers) == 1
    for e, open_clip in ((books[0], _sp.ACT_BOOK_OPEN_CLIP), (feathers[0], _sp.ACT_FEATHER_OPEN_CLIP)):
        tags = {f.tag for f in e.funcs}
        assert {0, _sp.ACT_APPEAR_TAG, _sp.ACT_HIDE_TAG} <= tags
        fa = e.func_by_tag(_sp.ACT_APPEAR_TAG)
        instrs = list(disasm.iter_code(eb, fa.abs_start, fa.abs_end))
        ops = [i.op for i in instrs]
        # the RIGHT open clip on the RIGHT prop -- the census's 4641-book / 4652-feather law (a clip
        # swap between the two injections sailed through the old op-presence-only assertion)
        assert any(i.op == 0x40 and i.args and i.args[0] == open_clip for i in instrs), open_clip
        assert 0x9F in ops                                       # the grow-in
        f0 = e.func_by_tag(0)
        init_ops = [i.op for i in disasm.iter_code(eb, f0.abs_start, f0.abs_end)]
        assert 0x93 in init_ops and 0x80 in init_ops             # spawns hidden, shadow off
    # the moogle: SetJumpAnimation preload in Init, the act in its talk body
    moogles = _entry_with_model(eb, 220)
    assert len(moogles) == 1
    m = moogles[0]
    f0 = m.func_by_tag(0)
    assert any(i.op == 0x94 and tuple(i.args) == (_sp.ACT_HOP_CLIP, 26, 30)
               for i in disasm.iter_code(eb, f0.abs_start, f0.abs_end))
    f3 = m.func_by_tag(3)
    talk_ops = [i.op for i in disasm.iter_code(eb, f3.abs_start, f3.abs_end)]
    assert 0x40 in talk_ops and 0xC8 in talk_ops and 0x75 in talk_ops
    # the moogle's grafts point at REAL entries: the reqs' uids are the props' actual slots
    req_uids = {i.args[1] for i in disasm.iter_code(eb, f3.abs_start, f3.abs_end) if i.op == 0x10}
    assert {books[0].index, feathers[0].index, 250} <= req_uids
    # the player gained the pose + release tags (the object band, 64+)
    from ff9mapkit.content.ladder import find_player_entry
    s = EbScript.from_bytes(eb)
    ptags = {f.tag for f in s.entry(find_player_entry(s)).funcs}
    assert len([t2 for t2 in ptags if t2 >= 64]) == 2


def test_build_region_dispatch_stays_actless(tmp_path):
    """The press REGION saves with zero clips -- the donor's moogle-less family, and ours."""
    _proj, _ct, eb = _built(tmp_path)
    s = EbScript.from_bytes(eb)
    for e in s.entries:
        if e is None or e.empty or e.type != 1:
            continue
        f3 = e.func_by_tag(3)
        if f3 is None:
            continue
        ops = [i.op for i in disasm.iter_code(eb, f3.abs_start, f3.abs_end)]
        if 0x75 in ops:                                          # the save region
            assert 0x40 not in ops and 0xC8 not in ops and 0x10 not in ops
            return
    raise AssertionError("no save region in the built field")


def test_build_act_false_opts_out(tmp_path):
    _proj, ct, eb = _built(tmp_path, _FIELD.replace(
        "[[savepoint]]\n", "[[savepoint]]\nact = false\n"))
    assert "act" not in (ct[-1][0] or {})
    assert not _entry_with_model(eb, 133) and not _entry_with_model(eb, 134)
    m = _entry_with_model(eb, 220)[0]
    f3 = m.func_by_tag(3)
    ops = [i.op for i in disasm.iter_code(eb, f3.abs_start, f3.abs_end)]
    assert 0x40 not in ops and 0x10 not in ops                   # a still moogle, as before


def test_built_act_executes_end_to_end(tmp_path):
    """The crown: the BUILT moogle talk body through the VM -- decline skips everything, the confirmed
    Yes plays the full act around exactly one Menu(4,0)."""
    _proj, _ct, eb = _built(tmp_path)
    m = _entry_with_model(eb, 220)[0]
    f3 = m.func_by_tag(3)
    body = eb[f3.abs_start:f3.abs_end]
    events, menus = [], []
    run(body, choices=[1], events=events, menus=menus)           # Cancel
    assert menus == [] and events == []
    events, menus = [], []
    M = bytearray(2048)
    run(body, choices=[0, 1], events=events, menus=menus, M=M)   # Save -> No
    assert menus == [] and events == []
    events, menus = [], []
    M = bytearray(2048)
    G = run(body, choices=[0, 0], events=events, menus=menus, M=M,
            on_async=act_async_contract(M))
    assert menus == [(4, 0)]
    assert [e[1][0] for e in events if e[0] == "anim"] == [
        _sp.ACT_HOP_CLIP, _sp.ACT_OPEN_CLIP, _sp.ACT_HOP_CLIP]
    assert bytes(G) == bytes(bytearray(2048))                    # the latch closed; nothing else moved


def test_act_validation_gates(tmp_path):
    from ff9mapkit import build

    def probs(toml):
        p = tmp_path / "v.field.toml"
        p.write_text(toml, encoding="utf-8")
        return build.validate(build.FieldProject.load(p))

    bad = _FIELD.replace("[[savepoint]]\n", "[[savepoint]]\nact = true\nmoogle = false\n")
    assert any("needs the moogle" in x for x in probs(bad))
    bad = _FIELD.replace("[[savepoint]]\n", "[[savepoint]]\nact = true\ndialogue = false\n")
    assert any("needs dialogue" in x for x in probs(bad))
    bad = _FIELD.replace("[[savepoint]]\n", "[[savepoint]]\nact_hop_to = [1]\n")
    assert any("act_hop_to" in x for x in probs(bad))
    bad = _FIELD.replace("[[savepoint]]\n", "[[savepoint]]\nact = 1\n")
    assert any("act must be true or false" in x for x in probs(bad))
    bad = _FIELD.replace("[[savepoint]]\n", "[[savepoint]]\nakt = true\n")
    assert any("unknown key 'akt'" in x for x in probs(bad))
    ok = _FIELD.replace("[[savepoint]]\n", "[[savepoint]]\nact_hop_to = [-347, 7514]\n"
                                           'act_text = "Kupo!"\n')
    assert not [x for x in probs(ok) if "savepoint" in x.lower()]


# --------------------------------------------------------------------------- the roster speaker + menu pos ---


def test_mognet_moogle_speaks_as_its_roster_identity(tmp_path):
    """A network moogle's windows use [TEXT=0,0] (stock's own idiom) and the dispatch seeds text var 0
    with the moogle's roster id -- so the name comes from the roster row, not a baked literal."""
    from ff9mapkit import build
    from ff9mapkit.content import mognet as _mg
    toml = (_FIELD.replace('text_block = 30111', 'text_block = 30111')
            + '\n[savepoint.mognet]\nname = "Mogwai"\naccept = [55]\n')
    p = tmp_path / "m.field.toml"
    p.write_text(toml, encoding="utf-8")
    proj = build.FieldProject.load(p)
    ct = build.collect_text(proj)
    mes = ct[0]
    # the roster speaker + stock's menu head, byte for byte (field 300 txid 3's own shape)
    assert ("[WDTH=0,2,6,0,-1][IMME][FEED=2][TEXT=0,0]\n[FEED=4]“What would you like to do?”") in mes
    assert "Mogwai\n“What would you like to do?”" not in mes      # NOT a baked literal name
    eb = build.build_script(proj, "us", {}, savepoint_txids=ct[-1])
    # SetTextVariable(0, 41) leads the talk body (0x66, slot 0, the new-moogle id)
    seed = opcodes.set_text_variable(0, _mg.NEW_MOOGLE_ID)
    assert seed in eb
    m = _entry_with_model(eb, 220)[0]
    f3 = m.func_by_tag(3)
    body = eb[f3.abs_start:f3.abs_end]
    assert body.index(seed) < body.index(opcodes.window_sync(2, 8, ct[-1][0]["prompt"]))


def test_explicit_speaker_overrides_the_roster_identity(tmp_path):
    from ff9mapkit import build
    toml = (_FIELD.replace("[[savepoint]]\n", '[[savepoint]]\nspeaker = "Mogwai"\n')
            + '\n[savepoint.mognet]\nname = "Mogwai"\naccept = [55]\n')
    p = tmp_path / "m2.field.toml"
    p.write_text(toml, encoding="utf-8")
    mes = build.collect_text(build.FieldProject.load(p))[0]
    assert "[IMME][FEED=2]Mogwai\n[FEED=4]“What would you like to do?”" in mes
    assert "[TEXT=0,0]\n[FEED=4]“What would you like to do?”" not in mes
    assert "[WDTH=" not in mes.split("[TXID=500]")[1].split("[ENDN]")[0]   # literal name: no hint


def test_menu_pos_is_opt_in(tmp_path):
    from ff9mapkit import build
    mes = build.collect_text(build.FieldProject.load(_write(tmp_path, "p0", _FIELD)))[0]
    assert "[MPOS=" not in mes                                    # default: the engine places it
    mes = build.collect_text(build.FieldProject.load(
        _write(tmp_path, "p1", _FIELD.replace("[[savepoint]]\n", '[[savepoint]]\nmenu_pos = "stock"\n'))))[0]
    assert "[MPOS=20,16][PCHC=" in mes                            # stock's main-menu pin, leading the entry
    assert "[MPOS=30,26][PCHC=2,1]" in mes                        # ...and the sub-window pin
    mes = build.collect_text(build.FieldProject.load(
        _write(tmp_path, "p2", _FIELD.replace("[[savepoint]]\n", "[[savepoint]]\nmenu_pos = [40, 50]\n"))))[0]
    assert mes.count("[MPOS=40,50]") >= 2                         # an explicit pair: everywhere


def _write(tmp_path, name, toml):
    p = tmp_path / f"{name}.field.toml"
    p.write_text(toml, encoding="utf-8")
    return p


def test_menu_pos_validation(tmp_path):
    from ff9mapkit import build

    def probs(toml):
        return build.validate(build.FieldProject.load(_write(tmp_path, "v", toml)))

    assert any("menu_pos" in x for x in probs(
        _FIELD.replace("[[savepoint]]\n", '[[savepoint]]\nmenu_pos = "middle"\n')))
    assert any("menu_pos" in x for x in probs(
        _FIELD.replace("[[savepoint]]\n", "[[savepoint]]\nmenu_pos = [1, 2, 3]\n")))
    assert not [x for x in probs(_FIELD.replace("[[savepoint]]\n", '[[savepoint]]\nmenu_pos = "stock"\n'))
                if "savepoint" in x.lower()]
