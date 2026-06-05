"""Phase-3 validation: generalized content injectors.

The headline oracle is byte-exact: rebuilding the in-game-verified Vivi-hut interior
(``hut_int-us.eb.bytes``) from the blank field via npc + set_player + gateway must reproduce
it exactly. The other transforms (encounter / reinit / music) are validated structurally —
applied to the blank field, the result must re-parse cleanly and contain the expected opcodes
with the rest of the script intact.
"""

from __future__ import annotations

from pathlib import Path

from ff9mapkit import data
from ff9mapkit.content import (camera, cutscene, encounter, event, gateway, music, npc, region,
                               reinit, text)
from ff9mapkit.eb import EbScript, opcodes
from ff9mapkit.eb.disasm import iter_code

FIX = Path(__file__).parent / "fixtures"
CLEAN = data.blank_field_bytes("us")


def _ops(eb: EbScript, entry_index: int, func_tag: int) -> list:
    f = eb.entry(entry_index).func_by_tag(func_tag)
    return [ins.op for ins in iter_code(eb.data, f.abs_start, f.abs_end)]


def test_hut_interior_reproduced_byte_exact():
    EXIT_ZONE = [(-1100, -2400), (1100, -2400), (1100, -1750), (-1100, -1750), (-1100, -1750)]
    out = npc.inject_npc(CLEAN, 0, -700, preset="vivi", talk_text_id=500)
    out = npc.set_player_spawn(out, 0, -1350)
    out = gateway.inject_gateway(out, 4000, entrance=0, slot=3, zone=EXIT_ZONE)
    assert out == (FIX / "hut_int-us.eb.bytes").read_bytes()


def test_npc_is_appended_and_spawned():
    out = npc.inject_npc(CLEAN, 100, -500, preset="vivi", talk_text_id=500)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out                       # still structurally valid
    # a new entry exists with a _SpeakBTN (tag 3) and no DefinePlayerCharacter
    npc_entry = next(e for e in eb.entries if not e.empty and e.func_by_tag(3) and e.index != 0)
    assert npc_entry.func_by_tag(3) is not None
    speak = _ops(eb, npc_entry.index, 3)
    assert 0x1F in speak                              # WindowSync
    # Main_Init now spawns it via InitObject (0x09)
    assert 0x09 in _ops(eb, 0, 0)


def test_encounter_injected():
    out = encounter.inject_encounter(CLEAN, scene=67, freq=255)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out
    assert 0x07 in _ops(eb, 0, 0)                    # InitCode in Main_Init
    batt = next(e for e in eb.entries if not e.empty and e.type == 0 and e.index != 0)
    ops = _ops(eb, batt.index, 0)
    assert ops[0] == 0x3C and 0x57 in ops            # SetRandomBattles + SetRandomBattleFrequency


def test_reinit_with_and_without_fade():
    out = reinit.add_reinit(CLEAN, with_fade=True)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out
    assert eb.entry(0).func_by_tag(10) is not None
    assert _ops(eb, 0, 10) == [0xEC, 0x2E, 0x04]     # FadeFilter, EnableMove, return
    # the player object (entry 1) survived the entry-0 growth + relocation
    assert eb.entry(1).func_by_tag(0) is not None
    assert 0x2C in _ops(eb, 1, 0)                    # DefinePlayerCharacter still intact

    plain = reinit.add_reinit(CLEAN, with_fade=False)
    assert _ops(EbScript.from_bytes(plain), 0, 10) == [0x2E, 0x04]


def test_music_on_entry_and_reinit():
    out = music.add_field_music(CLEAN, 9)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out
    assert 0x07 in _ops(eb, 0, 0)                    # InitCode activates the music entry
    me = next(e for e in eb.entries if not e.empty and e.type == 0 and e.index != 0)
    assert _ops(eb, me.index, 0)[0] == 0xC5          # RunSoundCode

    out2 = reinit.add_reinit(CLEAN, with_fade=True)
    out2 = music.add_music_to_reinit(out2, 9)
    eb2 = EbScript.from_bytes(out2)
    assert _ops(eb2, 0, 10)[0] == 0xC5               # RunSoundCode now first in tag-10


def test_region_primitives_match_real_field_bytes():
    """The flag/expression/conditional builders reproduce the exact bytecode decoded from the real
    Gargan Roo/Passage camera-switch region (evt_gargan_gr_lef_0)."""
    assert region.set_var(region.GLOB_UINT8, 24, 1).hex() == "05d5187d01002c7f"  # set flag = 1
    assert region.cond_not(region.GLOB_UINT8, 24).hex() == "05d5180e7f"          # if (!flag)
    assert region.cond_truthy(region.GLOB_UINT8, 24).hex() == "05d5187f"         # if (flag)
    assert region.cond_eq(region.MAP_BOOL, 159, 1).hex() == "05c59f7d0100207f"   # if (V == 1) (dev's Map bool 0xC5)
    assert region.MOVEMENT_GATE.hex() == "057a027f03010004"                      # ifnot(IsMovementEnabled) ret
    assert opcodes.set_field_camera(1).hex() == "7e0001"
    assert opcodes.terminate_entry(255).hex() == "1c00ff"
    # if_block jump-if-false offset == body length (matches dev `02 0b 00` for an 11-byte body)
    body = opcodes.set_field_camera(1) + region.set_var(region.GLOB_UINT8, 24, 1)
    assert region.if_block(region.cond_truthy(region.GLOB_UINT8, 24), body).hex() \
        == "05d5187f" + "020b00" + body.hex()


def test_region_forward_body_reproduces_dev_byte_exact():
    """The generic switch-body builder, given the field's own ChestA RunScriptSync, reproduces the
    real Gargan forward zone (entry 5 Range) byte-for-byte -- proof the conditional-region primitive
    matches shipped game bytecode, not just a plausible encoding."""
    runscript = bytes.fromhex("1400020811")          # RunScriptSync(2, 8, 17): field-specific anim
    body = (runscript + opcodes.set_field_camera(1) + region.set_var(region.GLOB_UINT8, 24, 1)
            + opcodes.set_control_direction(-36, -32) + opcodes.init_region(6, 0)
            + opcodes.terminate_entry(255))
    mine = region.MOVEMENT_GATE + region.if_block(region.cond_not(region.GLOB_UINT8, 24), body) \
        + opcodes.RETURN
    dev = bytes.fromhex("057a027f030100" "04" "05d5180e7f" "021a00" "1400020811" "7e0001"
                        "05d5187d01002c7f" "6700dce0" "080600" "1c00ff" "04")
    assert mine == dev


def test_camera_zones_structure_and_bodies():
    """N-camera area model: 3 zones, each owning its camera's area, flag-guarded (no toggle)."""
    zones = [(0, [(-900, -100), (-300, -100), (-300, -700), (-900, -700)]),
             (1, [(-200, -100), (200, -100), (200, -700), (-200, -700)]),
             (2, [(300, -100), (900, -100), (900, -700), (300, -700)])]
    cvs = [-1, 20, 30]
    out = camera.inject_camera_zones(CLEAN, zones, cvs)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out                       # round-trip valid

    free0 = EbScript.from_bytes(CLEAN).free_slots()
    zone_slots = free0[:3]
    init_slot = free0[3]
    for slot, k in zip(zone_slots, (0, 1, 2)):
        e = eb.entry(slot)
        assert e.type == 1 and e.func_by_tag(0) and e.func_by_tag(2)
        assert _ops(eb, slot, 0)[0] == 0x29           # SetRegion in Init
        rb = eb.data[e.func_by_tag(2).abs_start:e.func_by_tag(2).abs_end]
        # body: movement gate, then `if (flag != k) { SetFieldCamera(k); flag=k; SetControlDirection }`
        assert rb.startswith(region.MOVEMENT_GATE + region.cond_eq(region.GLOB_UINT8, 24, k))
        assert opcodes.set_field_camera(k) in rb and region.set_var(region.GLOB_UINT8, 24, k) in rb
        assert opcodes.set_control_direction(cvs[k], cvs[k]) in rb
    # init/arm entry (type 0): reset flag=0 + InitRegion every zone; armed from Main_Init
    ie = eb.entry(init_slot)
    assert ie.type == 0
    ib = eb.data[ie.func_by_tag(0).abs_start:ie.func_by_tag(0).abs_end]
    assert region.set_var(region.GLOB_UINT8, 24, 0) in ib
    assert all(opcodes.init_region(s, 0) in ib for s in zone_slots)
    assert 0x07 in _ops(eb, 0, 0)                     # InitCode arms it from Main_Init


def test_camera_restore_after_battle():
    """add_camera_restore puts `if (flag==K) { SetFieldCamera(K); SetControlDirection }` in tag-10."""
    out = reinit.add_reinit(CLEAN, with_fade=False)
    out = camera.add_camera_restore(out, {0, 1, 2}, [-1, 20, 30])
    eb = EbScript.from_bytes(out)
    t10 = eb.entry(0).func_by_tag(10)
    body = eb.data[t10.abs_start:t10.abs_end]
    # cameras 1 and 2 restored (0 is the default, skipped); EnableMove/return still present
    assert region.cond_eq(region.GLOB_UINT8, 24, 1) in body and opcodes.set_field_camera(1) in body
    assert region.cond_eq(region.GLOB_UINT8, 24, 2) in body and opcodes.set_field_camera(2) in body
    assert opcodes.set_field_camera(0) not in body
    assert 0x2E in _ops(eb, 0, 10)                    # EnableMove (the reinit) survived


def test_camera_zones_player_object_survives():
    """The injection must not disturb the player object (entry 1) or its DefinePlayerCharacter."""
    out = camera.inject_camera_zones(CLEAN, [(0, [(0, 0), (100, 0), (100, 100), (0, 100)]),
                                             (1, [(0, 200), (100, 200), (100, 300), (0, 300)])],
                                     [-1, 20])
    eb = EbScript.from_bytes(out)
    assert 0x2C in _ops(eb, 1, 0)                     # DefinePlayerCharacter intact


def _event_region(eb):
    """The injected event region (type-1 with a Range tag 2), and its Range bytes."""
    e = next(x for x in eb.entries if not x.empty and x.type == 1 and x.func_by_tag(2))
    f = e.func_by_tag(2)
    return e, eb.data[f.abs_start:f.abs_end]


def test_event_give_item_once_structure():
    ZONE = [(200, -300), (600, -300), (600, -700), (200, -700)]
    body = event.give_item(232, 1) + event.message(500)
    out = event.inject_events(CLEAN, [{"zone": ZONE, "body": body, "once_flag": 200}])
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out
    _, rng = _event_region(eb)
    assert opcodes.add_item(232, 1) in rng                       # AddItem(232,1)
    assert opcodes.window_sync(1, 128, 500) in rng              # got-item message
    assert region.cond_not(region.GLOB_BOOL, 200) in rng        # if (!flag)
    assert region.set_var(region.GLOB_BOOL, 200, 1) in rng      # flag = 1 (fires once)
    # armed via a shared init code entry (InitCode in Main_Init)
    assert 0x07 in _ops(eb, 0, 0)


def test_event_repeatable_has_no_flag():
    ZONE = [(0, 0), (100, 0), (100, 100), (0, 100)]
    out = event.inject_events(CLEAN, [{"zone": ZONE, "body": event.give_gil(500), "once_flag": None}])
    eb = EbScript.from_bytes(out)
    _, rng = _event_region(eb)
    assert opcodes.add_gil(500) in rng
    assert region.cond_not(region.GLOB_BOOL, 200) not in rng    # no once-guard
    # range body = movement gate + body + return (no flag machinery)
    assert rng == region.MOVEMENT_GATE + event.give_gil(500) + opcodes.RETURN


def test_event_batch_shares_one_wait():
    """Two events must consume only ONE Main_Init Wait filler (shared arming entry)."""
    evs = [{"zone": [(i * 100, 0), (i * 100 + 50, 0), (i * 100 + 50, 50), (i * 100, 50)],
            "body": event.message(500 + i), "once_flag": 200 + i} for i in range(2)]
    before = len(edit_waits(CLEAN))
    out = event.inject_events(CLEAN, evs)
    after = len(edit_waits(out))
    assert before - after == 1                                   # only one Wait consumed for 2 events
    eb = EbScript.from_bytes(out)
    assert sum(1 for e in eb.entries if not e.empty and e.type == 1 and e.func_by_tag(2)) == 2


def edit_waits(data):
    eb = EbScript.from_bytes(data)
    f = eb.entry(0).func_by_tag(0)
    return [i for i in iter_code(eb.data, f.abs_start, f.abs_end) if i.op == 0x22 and i.imm(0) == 2]


def test_flag_gate_bytes():
    # require_set: 'ifnot(flag) return' = push flag (Global bool 0xC4), jump-if-TRUE past return, return
    assert region.flag_gate(region.GLOB_BOOL, 200, require_set=True).hex() == "05c4c87f03010004"
    # require_clear: 'if(flag) return' = push flag, jump-if-FALSE past return, return
    assert region.flag_gate(region.GLOB_BOOL, 200, require_set=False).hex() == "05c4c87f02010004"
    # high index (> 0xFF) uses the long-index encoding: class|0x20 (0xE4) + 2-byte LE index
    assert region.flag_gate(region.GLOB_BOOL, 8000, require_set=True).hex() == "05e4401f7f03010004"


def test_npc_gated_by_flag():
    """A gated NPC's Init starts with the flag gate, so it returns before CreateObject when absent."""
    plain = npc.inject_npc(CLEAN, 100, -500, preset="vivi", talk_text_id=500)
    gated = npc.inject_npc(CLEAN, 100, -500, preset="vivi", talk_text_id=500, gate_flag=205)
    assert gated != plain
    eb = EbScript.from_bytes(gated)
    e = next(x for x in eb.entries if not x.empty and x.func_by_tag(3) and x.index != 0)
    init = e.func_by_tag(0)
    assert eb.data[init.abs_start:init.abs_start + 8] == region.flag_gate(region.GLOB_BOOL, 205)
    # the model setup still follows the gate (CreateObject 0x1D present after it)
    assert 0x1D in _ops(eb, e.index, 0)


def test_gateway_gated_by_flag():
    ZONE = [(-1100, -2400), (1100, -2400), (1100, -1750), (-1100, -1750), (-1100, -1750)]
    gated = gateway.inject_gateway(CLEAN, 4000, entrance=0, slot=3, zone=ZONE, gate_flag=210)
    eb = EbScript.from_bytes(gated)
    assert eb.to_bytes() == gated
    rng = eb.entry(3).func_by_tag(2)
    assert eb.data[rng.abs_start:rng.abs_start + 8] == region.flag_gate(region.GLOB_BOOL, 210)
    assert 0x2B in _ops(eb, 3, 2)                                # Field() exit still present after the gate


def test_event_requires_flag():
    out = event.inject_events(CLEAN, [{"zone": [(0, 0), (100, 0), (100, 100), (0, 100)],
                                       "body": event.message(500), "once_flag": None,
                                       "requires_flag": 215, "requires_set": True}])
    eb = EbScript.from_bytes(out)
    _, rng = _event_region(eb)
    # movement gate, then the requires-flag gate, then the body
    assert rng.startswith(region.MOVEMENT_GATE + region.flag_gate(region.GLOB_BOOL, 215))


def test_cutscene_body_once_structure():
    steps = [cutscene.say(500), cutscene.wait(30), cutscene.set_flag(210)]
    body = cutscene.build_body(steps, once_flag=230)
    # `if (!once230) { DisableMove; <steps>; EnableMove; once230 = 1 }` then return
    assert body.startswith(region.cond_not(region.GLOB_BOOL, 230))     # the once guard
    assert opcodes.DISABLE_MOVE in body and opcodes.ENABLE_MOVE in body
    assert opcodes.window_sync(1, 128, 500) in body                   # say -> WindowSync
    assert opcodes.wait(30) in body
    assert region.set_var(region.GLOB_BOOL, 210, 1) in body           # the set_flag step
    assert region.set_var(region.GLOB_BOOL, 230, 1) in body           # once-guard set on completion
    assert body.endswith(opcodes.RETURN)
    # DisableMove precedes EnableMove (control locked for the duration)
    assert body.index(opcodes.DISABLE_MOVE) < body.index(opcodes.ENABLE_MOVE)


def test_cutscene_body_no_once_is_unguarded():
    body = cutscene.build_body([cutscene.wait(5)], once_flag=None)
    assert body == opcodes.DISABLE_MOVE + cutscene.wait(5) + opcodes.ENABLE_MOVE + opcodes.RETURN


def test_cutscene_injected_and_armed():
    out = cutscene.inject_cutscene(CLEAN, [cutscene.say(500), cutscene.set_flag(210)], once_flag=230)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out
    cs = next(e for e in eb.entries if not e.empty and e.type == 0 and e.index != 0
              and any(i.op == 0x2D for i in iter_code(eb.data, e.func_by_tag(0).abs_start,
                                                      e.func_by_tag(0).abs_end)))
    assert cs is not None
    assert 0x07 in _ops(eb, 0, 0)                                     # InitCode arms it from Main_Init


def test_text_mes_format_and_mapping():
    line = text.mes_entry("I miss you Zidane", 500)
    assert line == "_[TXID=500][STRT=10,1][TAIL=UPR]I miss you Zidane[ENDN]"
    body, mapping = text.build_mes(["hello", "world"], start_txid=500)
    assert mapping == {0: 500, 1: 501}
    assert "[TXID=501]" in body and body.endswith("\n")
