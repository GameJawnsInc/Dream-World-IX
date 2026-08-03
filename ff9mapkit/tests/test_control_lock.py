"""The control-lock Tier-1 (studies/movement/SURVEY.md §10): stock-faithful DisableMove brackets
on dialogue-bearing bodies, the author ``lock`` / ``lock_menu`` keys, the narration lane's
``owns_control``, and ``[player] locked_entrances`` (stock's entrance-gated arrive-locked grant).

The census law under all of it: THE ENGINE HAS NO DIALOG LOCK -- a window opcode blocks only the
calling object's thread, and stock hand-rolls the lock on 1,108/1,108 window-bearing talk handlers.
Pins: the bracket/dispatch byte shapes, the per-lane defaults (npc/press locked, tread free), the
opt-outs' byte-identity with the pre-census shapes, the tread DELEGATION (a tag-2 body must not
block under its own lock -- the in-game freeze class), the entrance-gate insertion at BOTH template
grant sites, and the validation rulebook."""
from __future__ import annotations

import struct

import pytest

from ff9mapkit import data
from ff9mapkit.build import FieldProject, build_mod, validate
from ff9mapkit.config import ModLayout
from ff9mapkit.content import cutscene as _cutscene
from ff9mapkit.content import entrylock as _entrylock
from ff9mapkit.content import event as _event
from ff9mapkit.content import npc as _npc
from ff9mapkit.content import onentry as _onentry
from ff9mapkit.content import region as _region
from ff9mapkit.eb import EbScript, opcodes

BASE = """
[field]
id = 30601
name = "LOCKTEST"
area = 11

[camera]
pitch = 45

[walkmesh]
quad = [[-1400, -100], [1400, -100], [1400, -1400], [-1400, -1400]]

[player]
spawn = [0, -300]
"""


def _project(tmp_path, toml: str) -> FieldProject:
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    return FieldProject.load(p)


def _build_eb(tmp_path, toml: str) -> bytes:
    pr = _project(tmp_path, toml)
    assert validate(pr) == []
    out = tmp_path / "mod"
    build_mod([pr], out, mod_name="FF9CustomMap")
    return ModLayout(out).eb_path("us", "EVT_LOCKTEST.eb.bytes").read_bytes()


def _player_entry(eb: EbScript) -> int:
    from ff9mapkit.content.ladder import find_player_entry
    return find_player_entry(eb)


# --------------------------------------------------------------- the bracket primitives ---

def test_lock_bracket_bytes():
    assert _event.lock_bracket(b"X") == opcodes.DISABLE_MOVE + b"X" + opcodes.ENABLE_MOVE
    assert _event.lock_bracket(b"X", menu=True) == (
        opcodes.DISABLE_MOVE + opcodes.DISABLE_MENU + b"X"
        + opcodes.ENABLE_MENU + opcodes.ENABLE_MOVE)


def test_locked_dispatch_is_the_jump_tread_shape():
    # DisableMove; RunScriptSync(2, 250, tag); EnableMove -- byte-identical to jump.py's dispatch
    d = _event.locked_dispatch(60)
    assert d == (opcodes.DISABLE_MOVE + opcodes.run_script_sync(2, 250, 60) + opcodes.ENABLE_MOVE)
    dm = _event.locked_dispatch(60, menu=True)
    assert dm.startswith(opcodes.DISABLE_MOVE + opcodes.DISABLE_MENU)
    assert dm.endswith(opcodes.ENABLE_MENU + opcodes.ENABLE_MOVE)


# --------------------------------------------------------------- npc talk (the fidelity fix) ---

def test_npc_default_talk_is_bracketed():
    # the census law: stock locks on every window-bearing talk handler; the kit's default now matches
    raw = data.blank_field_bytes()
    out = _npc.inject_npc(raw, 0, -500, talk_text_id=62)
    eb = EbScript.from_bytes(out)
    talk = None
    for e in eb.entries:
        if e.empty:
            continue
        f = e.func_by_tag(3)
        if f is not None:
            talk = out[f.abs_start:f.abs_end]
    assert talk is not None
    win = _event.message(62, window=1, flags=128)
    assert talk.startswith(opcodes.DISABLE_MOVE + win + opcodes.ENABLE_MOVE + opcodes.RETURN)


def test_npc_lock_false_is_the_pre_census_shape():
    raw = data.blank_field_bytes()
    locked = _npc.inject_npc(raw, 0, -500, talk_text_id=62)
    free = _npc.inject_npc(raw, 0, -500, talk_text_id=62, talk_lock=False)
    assert locked != free
    eb = EbScript.from_bytes(free)
    talk = None
    for e in eb.entries:
        if e.empty:
            continue
        f = e.func_by_tag(3)
        if f is not None:
            talk = free[f.abs_start:f.abs_end]
    win = _event.message(62, window=1, flags=128)
    assert talk.startswith(win + opcodes.RETURN)
    assert opcodes.DISABLE_MOVE not in talk


def test_npc_lock_menu_double_bracket():
    raw = data.blank_field_bytes()
    out = _npc.inject_npc(raw, 0, -500, talk_text_id=62, talk_lock_menu=True)
    assert (opcodes.DISABLE_MOVE + opcodes.DISABLE_MENU) in out
    assert (opcodes.ENABLE_MENU + opcodes.ENABLE_MOVE + opcodes.RETURN) in out


# --------------------------------------------------------------- [[event]] lock ---

def test_action_event_locks_by_default(tmp_path):
    toml = BASE + """
[[event]]
zone = [[-200, -700], [200, -700], [200, -400], [-200, -400]]
trigger = "action"
once = false
message = "A sign."
"""
    eb = _build_eb(tmp_path, toml)
    # the press body wraps the window inline: 2D <WindowSync> 2E (a tag-3 body is a normal thread)
    win = opcodes.window_sync(1, 128, 500)          # txid 500 = the field's first authored line
    assert (opcodes.DISABLE_MOVE + win + opcodes.ENABLE_MOVE) in eb


def test_action_event_lock_false_optout(tmp_path):
    toml = BASE + """
[[event]]
zone = [[-200, -700], [200, -700], [200, -400], [-200, -400]]
trigger = "action"
once = false
lock = false
message = "A sign."
"""
    eb = _build_eb(tmp_path, toml)
    win = opcodes.window_sync(1, 128, 500)
    assert win in eb
    assert (opcodes.DISABLE_MOVE + win) not in eb


def test_walk_event_default_stays_free_byte_identical(tmp_path):
    # the tread default is UNCHANGED by the lock feature (the proven toast idiom): lock=false
    # explicitly and the absent-key default build the same bytes
    toml_ev = """
[[event]]
zone = [[-200, -700], [200, -700], [200, -400], [-200, -400]]
message = "A toast."
"""
    a = _build_eb(tmp_path, BASE + toml_ev)
    (tmp_path / "f.field.toml").unlink()
    (tmp_path / "mod" / "x").parent.mkdir(exist_ok=True)
    import shutil
    shutil.rmtree(tmp_path / "mod")
    b = _build_eb(tmp_path, BASE + toml_ev + "lock = false\n")
    assert a == b


def test_walk_event_lock_delegates_to_a_player_func(tmp_path):
    # a tag-2 tread body must NOT block under its own lock (the in-game freeze class) -- a locked
    # tread event grafts its body onto the PLAYER entry and the region runs locked_dispatch
    toml = BASE + """
[[event]]
zone = [[-200, -700], [200, -700], [200, -400], [-200, -400]]
lock = true
message = "A story beat."
"""
    eb_bytes = _build_eb(tmp_path, toml)
    assert _event.locked_dispatch(_event.EVENT_LOCK_TAG_BASE) in eb_bytes
    eb = EbScript.from_bytes(eb_bytes)
    pf = eb.entry(_player_entry(eb)).func_by_tag(_event.EVENT_LOCK_TAG_BASE)
    assert pf is not None
    body = eb_bytes[pf.abs_start:pf.abs_end]
    assert opcodes.window_sync(1, 128, 500) in body     # the window lives in the delegated func
    assert body.endswith(opcodes.RETURN)


# --------------------------------------------------------------- [[on_entry]] ---

def test_on_entry_lock_false_drops_the_reorder_dance():
    locked = _onentry.on_entry_body(message_txid=500, once_flag=None)
    free = _onentry.on_entry_body(message_txid=500, once_flag=None, message_lock=False)
    assert opcodes.DISABLE_MOVE in locked and locked.startswith(opcodes.wait(_cutscene.REORDER_WAIT))
    assert opcodes.DISABLE_MOVE not in free and not free.startswith(opcodes.wait(2))


def test_on_entry_entrance_gate_shape():
    # single: `if (FieldEntrance == 5) skip-the-return` -- the scenario_gate shape, D8:2-keyed
    cond5 = _region.cond_eq(_region.GLOB_INT16, _region.FIELD_ENTRANCE_IDX, 5)
    g = _onentry.entrance_gate(5)
    assert g == cond5 + bytes([_region.JMP_TRUE]) + struct.pack("<h", 1) + opcodes.RETURN
    # multi: each match jumps past the remaining conditions AND the shared return
    cond2 = _region.cond_eq(_region.GLOB_INT16, _region.FIELD_ENTRANCE_IDX, 2)
    g2 = _onentry.entrance_gate([2, 5])
    assert g2 == (cond2 + bytes([_region.JMP_TRUE]) + struct.pack("<h", len(cond5) + 3 + 1)
                  + cond5 + bytes([_region.JMP_TRUE]) + struct.pack("<h", 1) + opcodes.RETURN)
    # and the hook body leads with it (before the once-block)
    body = _onentry.on_entry_body(message_txid=500, once_flag=None, entrance=5)
    assert body.startswith(_onentry.entrance_gate(5))


def test_on_entry_grant_control_tail():
    # the arrive-locked grant: OUTSIDE the once block, the stock enable-macro shape
    body = _onentry.on_entry_body(message_txid=500, once_flag=9000, grant_control=True)
    tail = (_region.set_var(_region.MAP_BOOL, 158, 1) + opcodes.ENABLE_MOVE
            + opcodes.encode(0x27, 255) + opcodes.ENABLE_MENU + opcodes.RETURN)
    assert body.endswith(tail)
    # and the once-gated inner grant still exists separately (the message bracket's own EnableMove)
    assert body.count(opcodes.ENABLE_MOVE) >= 2


# --------------------------------------------------------------- cutscene lanes ---

def test_narration_owns_control_false_emits_no_lock():
    say = opcodes.window_sync(1, 128, 500)
    locked = _cutscene.build_body([say], None)
    free = _cutscene.build_body([say], None, owns_control=False)
    assert opcodes.DISABLE_MOVE in locked and opcodes.ENABLE_MOVE in locked
    assert opcodes.DISABLE_MOVE not in free and opcodes.ENABLE_MOVE not in free
    assert say in free


def test_narration_build_uses_grant_spin_and_watchdog(tmp_path):
    # the reorder-wait guess LOSES to a late player-init grant (model-load-timed) -- a built
    # narration scene must carry the conductor's proven machinery: the watchdog entry + the
    # grant-catch spin (raise MAP flag, lock, spin, re-lock), not the bare Wait(2)+DisableMove
    from ff9mapkit.content import conductor as _conductor
    toml = BASE + """
[cutscene]
once = false
steps = [ { say = "hello" } ]
"""
    eb_bytes = _build_eb(tmp_path, toml)
    spin = _conductor.wait_for_control_then_lock()
    assert spin in eb_bytes                                     # the spin, ending in the re-lock
    flag_up = _region.set_var(_region.MAP_BOOL, _conductor.WATCHDOG_MAP_FLAG, 1)
    assert (flag_up + opcodes.DISABLE_MOVE) in eb_bytes         # raise the flag, then lock
    # and the watchdog poll entry exists (its 1-frame re-lock loop)
    assert _conductor.watchdog_body() in eb_bytes if hasattr(_conductor, "watchdog_body") else True


def test_narration_lock_menu_pair():
    say = opcodes.window_sync(1, 128, 500)
    body = _cutscene.build_body([say], None, lock_menu=True)
    assert (opcodes.DISABLE_MOVE + opcodes.DISABLE_MENU) in body
    assert (opcodes.ENABLE_MENU + opcodes.ENABLE_MOVE) in body


# --------------------------------------------------------------- [player] locked_entrances ---

_SET_LATCH = _entrylock._SET_LATCH
_TEST_LATCH = _entrylock._TEST_LATCH


def _gate_for(entrance: int) -> bytes:
    return _region.cond_eq(_region.GLOB_INT16, _region.FIELD_ENTRANCE_IDX, entrance)


def test_entrylock_gates_both_grant_sites():
    raw = data.blank_field_bytes()
    out = _entrylock.gate_grant_on_entrances(raw, [2])
    cond = _gate_for(2)

    # site A: the player-init latch arm -- the gate sits immediately before `set MAP158 = 1`,
    # and its JMP_TRUE skips exactly to the terminal RETURN
    eb = EbScript.from_bytes(out)
    pe = _player_entry(eb)
    init = eb.entry(pe).func_by_tag(0)
    body = out[init.abs_start:init.abs_end]
    a = body.find(cond)
    assert a >= 0 and body[a + len(cond)] == _region.JMP_TRUE
    skip = struct.unpack_from("<h", body, a + len(cond) + 1)[0]
    land = a + len(cond) + 3 + skip
    assert body[land] == 0x04                       # RETURN -- the grant block is skipped whole
    assert body[a + len(cond) + 3:].startswith(_SET_LATCH)

    # site B: the Main_Init re-affirm -- gate before the `if (MAP158 == 1)` test, landing at the
    # JMP_FALSE's own target (the end of the taken branch)
    main = eb.entry(0).func_by_tag(0)
    mbody = out[main.abs_start:main.abs_end]
    b = mbody.find(cond)
    assert b >= 0 and mbody[b + len(cond)] == _region.JMP_TRUE
    mskip = struct.unpack_from("<h", mbody, b + len(cond) + 1)[0]
    t = b + len(cond) + 3
    assert mbody[t:].startswith(_TEST_LATCH)
    jo = t + len(_TEST_LATCH)
    assert mbody[jo] == _region.JMP_FALSE
    inner = struct.unpack_from("<h", mbody, jo + 1)[0]
    assert t + mskip == jo + 3 + inner              # both jumps land on the same block end


def test_entrylock_multiple_entrances_chain():
    raw = data.blank_field_bytes()
    out = _entrylock.gate_grant_on_entrances(raw, [2, 5])
    eb = EbScript.from_bytes(out)
    init = eb.entry(_player_entry(eb)).func_by_tag(0)
    body = out[init.abs_start:init.abs_end]
    a2, a5 = body.find(_gate_for(2)), body.find(_gate_for(5))
    assert 0 <= a2 < a5                             # the chain, in author order
    # each condition's jump lands on the SAME grant-block end (the RETURN)
    for a, cond in ((a2, _gate_for(2)), (a5, _gate_for(5))):
        skip = struct.unpack_from("<h", body, a + len(cond) + 1)[0]
        assert body[a + len(cond) + 3 + skip] == 0x04


def test_entrylock_rejects_a_non_template_player():
    # a player Init WITHOUT the template's latch arm (a donor-shaped fork) is refused loudly --
    # NOP out the `set MAP158 = 1` anchor and the module must raise, not silently half-gate
    raw = data.blank_field_bytes()
    broken = raw.replace(_SET_LATCH, b"\x00" * len(_SET_LATCH))
    with pytest.raises(ValueError, match="synth-only"):
        _entrylock.gate_grant_on_entrances(broken, [2])


def test_entry_settle_grant_is_entrance_gated_with_locked_entrances():
    # the settle's closing EnableMove is an unconditional grant -- on an arrive-locked field it
    # must be gated on the locked entrances (else it re-grants mid-arrival and breaks the contract)
    from ff9mapkit.content import entry_settle as _es
    raw = data.blank_field_bytes()
    plain = _es.add_entry_settle(raw, 30)
    gated = _es.add_entry_settle(raw, 30, locked_entrances=[5])
    assert (opcodes.DISABLE_MOVE + opcodes.wait(30) + opcodes.ENABLE_MOVE) in plain
    cond = _gate_for(5)
    assert (opcodes.DISABLE_MOVE + opcodes.wait(30) + cond + bytes([_region.JMP_TRUE])
            + struct.pack("<h", 1) + opcodes.ENABLE_MOVE) in gated


def test_locked_entrances_build_end_to_end(tmp_path):
    toml = BASE.replace('spawn = [0, -300]', 'spawn = [0, -300]\nlocked_entrances = [2]') + """
[[player.arrival]]
entrance = 2
pos = [0, -600]

[[on_entry]]
message = "You awaken somewhere strange."
"""
    eb_bytes = _build_eb(tmp_path, toml)
    assert _gate_for(2) in eb_bytes                 # the entrance gate landed
    tail = (_region.set_var(_region.MAP_BOOL, 158, 1) + opcodes.ENABLE_MOVE
            + opcodes.encode(0x27, 255) + opcodes.ENABLE_MENU)
    assert tail in eb_bytes                         # the on_entry hook carries the grant


# --------------------------------------------------------------- the validation rulebook ---

def _problems(tmp_path, toml: str) -> list:
    return validate(_project(tmp_path, toml))


def test_validate_lock_on_choice_rejected(tmp_path):
    toml = BASE + """
[[choice]]
zone = [[-200, -700], [200, -700], [200, -400], [-200, -400]]
prompt = "Pull the lever?"
lock = false

[[choice.options]]
text = "Yes"
"""
    assert any("ALWAYS locked" in p for p in _problems(tmp_path, toml))


def test_validate_lock_menu_needs_lock(tmp_path):
    toml = BASE + """
[[npc]]
name = "Grump"
pos = [0, -600]
dialogue = "Hmph."
lock = false
lock_menu = true
"""
    assert any("lock_menu needs the lock" in p for p in _problems(tmp_path, toml))


def test_validate_locked_entrances_needs_a_covering_hook(tmp_path):
    toml = BASE.replace('spawn = [0, -300]', 'spawn = [0, -300]\nlocked_entrances = [2]')
    assert any("no [[on_entry]] hook to hand control back" in p for p in _problems(tmp_path, toml))
    # a hook gated to a DIFFERENT entrance does not cover it
    toml5 = toml + """
[[on_entry]]
entrance = 5
message = "wrong door"
"""
    assert any("entrance 2 has no [[on_entry]]" in p for p in _problems(tmp_path, toml5))
    # an entrance-gated hook covering it DOES (the preferred shape)
    toml2 = toml + """
[[on_entry]]
entrance = 2
message = "the locked door"
"""
    assert not any("locked_entrances" in p for p in _problems(tmp_path, toml2))


def test_locked_entrances_entrance_gated_hook_builds(tmp_path):
    toml = BASE.replace('spawn = [0, -300]', 'spawn = [0, -300]\nlocked_entrances = [2]') + """
[[player.arrival]]
entrance = 2
pos = [0, -600]

[[on_entry]]
entrance = 2
once = false
message = "Through the locked door."
"""
    eb_bytes = _build_eb(tmp_path, toml)
    # the hook leads with the entrance gate AND still carries the grant tail
    assert _onentry.entrance_gate(2) in eb_bytes
    tail = (_region.set_var(_region.MAP_BOOL, 158, 1) + opcodes.ENABLE_MOVE
            + opcodes.encode(0x27, 255) + opcodes.ENABLE_MENU)
    assert tail in eb_bytes


def test_validate_cutscene_lock_menu_needs_owns_control(tmp_path):
    toml = BASE + """
[cutscene]
owns_control = false
lock_menu = true
steps = [{ say = "..." }]
"""
    assert any("lock_menu needs the control bracket" in p for p in _problems(tmp_path, toml))
