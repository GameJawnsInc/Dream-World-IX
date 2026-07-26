"""The worldmap-exit gateway + the direct entrance trigger (the continent-entrance pair).

Game-gated like the transplant proofs: the cascade is extracted from the real install.
"""
import pytest


def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")


def test_cascade_extraction():
    """The shared exit cascade: the instruction-aligned common block of the two
    byte-verified carriers (300 e2/tag2, 2800 e21/tag2) -- 19 WorldMap arms, opens
    with the ScenarioCounter-read expression, parses cleanly end to end."""
    from ff9mapkit.content.worldexit import cascade_bytes
    from ff9mapkit.eb.disasm import read_code
    c = cascade_bytes()
    assert len(c) > 500
    assert c[:3] == bytes([0x05, 0xDC, 0x00])        # the first SC-band gate
    pos, wm = 0, 0
    while pos < len(c):
        ins, pos = read_code(c, pos)
        wm += ins.op == 0xB6
    assert pos == len(c) and wm == 19                # every WorldMap arm, clean parse


def test_worldmap_exit_body_shape():
    """[usercontrol guard] -> [D8:2 = 62: the generic-return key -- its arm runs
    D8:2=0 + WorldMap(9009) in every band = the persisted-position arrival;
    0/un-cased keys hit the switch default, a bare RETURN that never warps
    (playtest-proven dead door)] -> [the verbatim cascade]. (fade=False here to
    check the core structure; the fade prefix is asserted separately.)"""
    from ff9mapkit.content import region as R
    from ff9mapkit.content.worldexit import cascade_bytes, worldmap_exit_body
    b = worldmap_exit_body(fade=False)
    assert b.startswith(R.MOVEMENT_GATE)
    key_write = bytes([0x05, 0xD8, 0x02, 0x7D, 62, 0x00, 0x2C, 0x7F])
    assert b[len(R.MOVEMENT_GATE):len(R.MOVEMENT_GATE) + 8] == key_write
    assert b.endswith(cascade_bytes())
    # on-exit story writes slot between the guard and the key write
    b2 = worldmap_exit_body(on_exit_body=b"\xaa\xbb", fade=False)
    assert b2[len(R.MOVEMENT_GATE):len(R.MOVEMENT_GATE) + 2] == b"\xaa\xbb"


def test_worldmap_exit_fades_out_by_default():
    """Leaving a field DIMS before the WorldMap transition (the real exit head fades;
    the carried cascade suffix does not, so a synth exit re-adds it). The fade is
    DisableMove + FadeFilter(6,24,white) + Wait(25), inserted after the guard/on-exit
    writes and before the position/key writes. Default on; fade=False omits it."""
    from ff9mapkit.content import region as R
    from ff9mapkit.content.worldexit import exit_fade, worldmap_exit_body
    faded = worldmap_exit_body()
    plain = worldmap_exit_body(fade=False)
    assert exit_fade() in faded and exit_fade() not in plain
    assert len(faded) == len(plain) + len(exit_fade())
    # the fade sits right after the usercontrol guard (DisableMove is the first byte)
    assert faded[len(R.MOVEMENT_GATE):len(R.MOVEMENT_GATE) + len(exit_fade())] == exit_fade()
    # a FadeFilter (0xEC, SUB toward white) is present; the arrive variant fades too
    assert bytes([0xEC]) in exit_fade()
    assert exit_fade() in worldmap_exit_body(arrive=(228.0, -1187.0))


def test_entrance_func_body_direct():
    """The direct trigger: the proven template's 12-byte vehicle/state gate verbatim,
    the conditional skip re-pointed over [the real zone-in choreography][record?]
    [Field(id)], return. The zone-in (fade-to-black + control lock + the D8:2=9999
    arrival sentinel + the ready poll) is byte-verified against the REAL dispatcher's
    own main-loop run -- the donor is the oracle."""
    from ff9mapkit.eb.model import EbScript
    from ff9mapkit.world.entrance import (TEMPLATE_TAG, entrance_func_body_direct,
                                          load_world_dispatchers, zone_in_body)
    disp = load_world_dispatchers()
    w00 = EbScript(disp["evt_world_world00"])
    f = next(f for e in w00.entries for f in e.funcs if f.tag == TEMPLATE_TAG)
    tpl = w00.data[f.abs_start:f.abs_end]
    zi = zone_in_body()
    # donor oracle: WORLD00's main loop (entry-1/tag-1) carries the SAME bytes as three
    # contiguous slices of its real pre-AREA-switch choreography (the control lock, the
    # window cleanup -- a guard expression sits between them in the loop -- and the whole
    # fade -> Wait -> D8:2=9999 -> ready-poll run)
    f1 = w00.entry(1).func_by_tag(1)
    loop = w00.data[f1.abs_start:f1.abs_end]
    assert zi[:2] in loop                            # DisableMove; DisableMenu
    assert zi[2:8] in loop                           # CloseWindow(6); CloseWindow(7)
    assert zi[8:] in loop                            # RunWorldCode x2; fade; wait; D8:2; poll
    b = entrance_func_body_direct(6500, dispatchers=disp)
    fld = bytes([0x2B, 0x00, 6500 & 0xFF, 6500 >> 8])
    assert b[:12] == tpl[:12]                        # the gate, verbatim
    assert b[12:15] == bytes([0x02, len(zi) + 4, 0x00])   # JZ re-pointed over zone-in + Field
    assert b[15:15 + len(zi)] == zi
    assert b[15 + len(zi):19 + len(zi)] == fld
    assert b[-1] == 0x04                             # return
    # with the per-dispatcher world-state record (9009 -> WORLD09's copy): the
    # GLOB[1062] = 9009 write feeds the arrive= exit's same-state return
    b2 = entrance_func_body_direct(6500, world_state=9009, dispatchers=disp)
    rec = bytes([0x05, 0xD8 | 0x20]) + (1062).to_bytes(2, "little") \
        + bytes([0x7D]) + (9009).to_bytes(2, "little") + bytes([0x2C, 0x7F])
    assert b2[:12] == tpl[:12]
    assert b2[12:15] == bytes([0x02, len(zi) + len(rec) + 4, 0x00])
    assert b2[15:15 + len(zi)] == zi
    assert b2[15 + len(zi):15 + len(zi) + len(rec)] == rec
    assert b2[15 + len(zi) + len(rec):19 + len(zi) + len(rec)] == fld
    assert b2[-1] == 0x04
    with pytest.raises(ValueError):
        entrance_func_body_direct(0x8000, dispatchers=disp)   # past Int16


def test_entrance_func_body_prompt():
    """The faithful "!" action-prompt trigger (prompt=True): shows the FICON "!" bubble every frame
    on the tile and warps only on a Confirm press (B_KEYON gate) -- NOT walk-on auto-warp. The Confirm
    test is byte-identical to the real dispatcher main-loop entrance gate (WORLD00 tag-1 @261)."""
    from ff9mapkit.eb import disasm as D
    from ff9mapkit.world.entrance import (CONFIRM_PRESSED, FICON_EXCLAM,
                                          entrance_func_body_direct, load_world_dispatchers)
    from ff9mapkit.eb.model import EbScript
    disp = load_world_dispatchers()
    auto = entrance_func_body_direct(6500, world_state=9009, dispatchers=disp)
    prompt = entrance_func_body_direct(6500, world_state=9009, prompt=True, dispatchers=disp)
    # prompt adds exactly the FICON (3B) + the Confirm-gate (CONFIRM_PRESSED + a 3B JMP_IFNOT)
    assert len(prompt) == len(auto) + len(FICON_EXCLAM) + len(CONFIRM_PRESSED) + 3
    assert FICON_EXCLAM in prompt and CONFIRM_PRESSED in prompt
    # the Confirm test is the REAL dispatcher's gate fragment, verbatim
    w00 = EbScript(disp["evt_world_world00"])
    f1 = w00.entry(1).func_by_tag(1)
    assert CONFIRM_PRESSED[1:-1] in w00.data[f1.abs_start:f1.abs_end]   # op7E(0,0,2,0) op4F, inside the real gate
    # structure: FICON before the B_KEYON gate before Field; both JMP_IFNOTs land on the final RETURN
    ops = [(i.op, i.off) for i in D.iter_code(prompt, 0, len(prompt))]
    off = {op: o for op, o in ops}
    assert off[0x68] < off[0x4F] if 0x4F in off else True   # FICON precedes the keyon expr (0x4F is inside an expr)
    i_ficon = next(o for op, o in ops if op == 0x68)
    i_field = next(o for op, o in ops if op == 0x2B)
    assert i_ficon < i_field                                # "!" raised before the warp
    assert prompt[-1] == 0x04                               # terminal RETURN
    # a NON-prompt direct body has NO bubble and warps unconditionally after the vehicle gate
    assert FICON_EXCLAM not in auto and CONFIRM_PRESSED not in auto


def test_entrance_func_body_nameplate():
    """The nameplate HUD (prompt=True, nameplate=True) SUMMONS the native machinery (Byte[39]=1 +
    RunScriptAsync(6,1,11) -> func-0xB) on the APPROACH frames -- the only spam-free way to show it, since the idle
    loop closes windows 6/7 every frame while Byte[24]<=100 and func-0xB keeps Byte[24]>100. The trigger gate is
    ON-FOOT ONLY (not the template's Byte[24]==100), so our Confirm warp still fires while func-0xB holds Byte[24]
    off 100 -- that Byte[24] coupling was the 3x blackscreen. The WARP branch writes Byte[24]=100 first (suppresses
    the native main loop's own confirm gate = single fade), then the proven zone_in + Field(6500)."""
    from ff9mapkit.eb import disasm as D
    from ff9mapkit.world.entrance import (CONFIRM_PRESSED, FICON_EXCLAM, NAMEPLATE_CASE, ONFOOT_GATE,
                                          dispatcher_cases, entrance_func_body_direct, load_world_dispatchers,
                                          nameplate_summon)
    disp = load_world_dispatchers()
    named = entrance_func_body_direct(6500, world_state=9009, prompt=True, nameplate=True, dispatchers=disp)
    summon = nameplate_summon()
    settle = bytes([0x05, 0xD5, 0x18, 0x7D, 100, 0x00, 0x2C, 0x7F])    # Byte[24] = 100 (warp branch only)
    field = bytes([0x2B, 0x00, 6500 & 0xFF, 6500 >> 8])
    # the gate is ON-FOOT ONLY (no Byte[24]==100 term); it is the template gate's !var190 term
    assert named.startswith(ONFOOT_GATE + bytes([0x02]))
    assert ONFOOT_GATE == bytes([0x05, 0xD4, 0xBE, 0x0E, 0x7F])
    # Confirm gate FIRST; on !Confirm -> APPROACH (summon + "!"); on Confirm -> WARP (settle + zone_in + Field)
    assert named.index(CONFIRM_PRESSED) < named.index(settle) < named.index(field) < named.index(summon)
    assert named.index(summon) < named.index(FICON_EXCLAM)             # the "!" follows the summon
    # the summon is the native handshake (Byte[39]=1 + RunScriptAsync(6,1,11)), only on the approach branch
    assert summon == bytes([0x05, 0xD5, 0x27, 0x7D, NAMEPLATE_CASE, 0x00, 0x2C, 0x7F]) + bytes([0x10, 0x00, 0x06, 0x01, 0x0B])
    assert summon not in named[:named.index(field)]                   # summon is NOT on the warp path
    # the summon is GATED on Byte[24]==100 (func-0xB's clean-entry precondition) right before it
    eq100 = bytes([0x05, 0xD5, 0x18, 0x7D, 100, 0x00, 0x20, 0x7F])     # EXPR: Byte[24] == 100
    assert eq100 in named and named.index(eq100) < named.index(summon)
    # the warp branch writes Byte[24]=100 BEFORE the fade (single-fade guard) and reaches Field(6500)
    assert named.index(settle) < named.index(bytes([0xEC])) < named.index(field)   # settle < FadeFilter(0xEC) < Field
    # NAMEPLATE_CASE must be UNMAPPED in every free-roam dispatcher (native confirm -> switch default, no mis-warp)
    for name, b in disp.items():
        cs = dispatcher_cases(b)
        if cs is not None:
            assert NAMEPLATE_CASE not in cs, f"{name} maps case {NAMEPLATE_CASE}"
    # body parses clean end to end, terminal RETURN
    tail = list(D.iter_code(named, 0, len(named)))
    assert tail[-1].off + tail[-1].length == len(named) and named[-1] == 0x04
    # nameplate requires prompt
    with pytest.raises(ValueError):
        entrance_func_body_direct(6500, nameplate=True, dispatchers=disp)


def test_worldmap_exit_arrive_shape():
    """The deterministic return: [gate][arrive var writes -- BOTH player-object
    blocks, in the Init's own 32-bit idiom][D8:2 = the position-preset key, which
    must NOT be a key whose cascade arm re-zeroes D8:2][if GLOB[1062]:
    WorldMap(<var>) computed][the cascade fallback for debug-warped-in visits]."""
    from ff9mapkit.content import region as R
    from ff9mapkit.content.worldexit import (_POS_ONFOOT, _POS_VEHICLE, POSITION_PRESET_KEY,
                                             WORLD_STATE_VAR, arrive_writes, cascade_bytes,
                                             worldmap_exit_body, worldmap_to_var)
    b = worldmap_exit_body(arrive=(228.0, -1179.0), fade=False)   # fade tested separately
    aw = arrive_writes(228.0, -1179.0, face=0)
    # the ON-FOOT avatar's block first (C8:0x40 -- the object that takes control when
    # D4:190 == 0, and the block the save mirrors at WORLD_POS_X_OFF = 64), then the
    # model-308 vehicle-composite block (C8:0x53); the non-driving one is inert.
    assert _POS_ONFOOT[0] == (0xC8, 0x40) and _POS_VEHICLE[0] == (0xC8, 0x53)
    onfoot = bytes([0x05, 0xC8, 0x40, 0x7E]) + (228 * 256).to_bytes(4, "little")
    vehicle = bytes([0x05, 0xC8, 0x53, 0x7E]) + (228 * 256).to_bytes(4, "little")
    assert aw[:8] == onfoot
    assert vehicle in aw and aw.index(onfoot) < aw.index(vehicle)
    for cls, idx in (_POS_ONFOOT[2], _POS_VEHICLE[2]):          # both Z writes present
        assert bytes([0x05, cls, idx, 0x7E]) + (-1179 * 256).to_bytes(4, "little", signed=True) in aw
    assert len(aw) == 2 * (10 + 8 + 10 + 8)                     # two full blocks, no more
    assert b.startswith(R.MOVEMENT_GATE + aw)
    # the preset key must NOT be 62: 62 is the one cascade key whose arm runs
    # `D8:2 = 0; WorldMap(9009)` in all four SC bands, which discards the preset on
    # the fall-through path. 35 is a real disc-1 key with BARE WorldMap arms.
    assert POSITION_PRESET_KEY == 35 and POSITION_PRESET_KEY != 62
    p = len(R.MOVEMENT_GATE) + len(aw)
    key = R.set_var(R.GLOB_INT16, R.FIELD_ENTRANCE_IDX, POSITION_PRESET_KEY)
    assert b[p:p + len(key)] == key
    p += len(key)
    cond = R.cond_truthy(0xD8, WORLD_STATE_VAR)
    assert b[p:p + len(cond)] == cond
    p += len(cond)
    wm = worldmap_to_var()
    assert b[p:p + 3] == bytes([0x02, len(wm), 0x00])         # skip the computed op
    assert b[p + 3:p + 3 + len(wm)] == wm                     # WorldMap(<GLOB 1062>)
    assert b.endswith(cascade_bytes())
