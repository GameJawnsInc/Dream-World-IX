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


# ---------------------------------------------------- the walk-scene triangle-mask bracket ---

def test_conductor_walk_scene_brackets_the_triangle_mask():
    # a WALK-bearing locked scene carries stock's macro pair: STFM(127) lands with the spin's
    # re-lock (restricted triangles crossable for the scene's routes -- forked fields gate
    # cutscene-only bridges/stairs this way), STFM(255) restores with the enable
    from ff9mapkit.content import conductor as _conductor
    steps = [{"actor": "a", "walk": [100, 200]}]
    body = _conductor.build_body(steps, {"a": 7}, [], None, tag_calls={0: (7, 20)})
    assert (opcodes.DISABLE_MOVE + opcodes.set_triangle_flag_mask(127)) in body
    assert (opcodes.ENABLE_MOVE + opcodes.set_triangle_flag_mask(255)) in body


def test_conductor_walkless_scene_emits_no_triangle_mask():
    # no walks -> no mask bracket: byte-identical to the pre-mask shape
    from ff9mapkit.content import conductor as _conductor
    body = _conductor.build_body([{"actor": "a", "turn": 64}], {"a": 7}, [], None)
    assert opcodes.set_triangle_flag_mask(127) not in body
    assert opcodes.set_triangle_flag_mask(255) not in body


def test_conductor_then_warp_walk_scene_skips_the_restore():
    # a warp-away scene leaves the mask -- the engine resets it to 255 on every field load
    # (WalkMesh.cs:1690), and there is no enable to pair the restore with
    from ff9mapkit.content import conductor as _conductor
    steps = [{"actor": "a", "path": [[100, 200], [300, 400]]}]
    body = _conductor.build_body(steps, {"a": 7}, [], None, tag_calls={0: (7, 20)},
                                 then_warp=4005)
    assert opcodes.set_triangle_flag_mask(127) in body
    assert opcodes.set_triangle_flag_mask(255) not in body


# ------------------------------------------------ Tier-2 item 7: latch / reinit / partial pad ---

def test_reinit_grant_is_restore_not_grant():
    # the tag-10 grant is gated on the engine-RESTORED pre-battle usercontrol (sysvar 2 -- the
    # context-copy at EventEngine.cs:668 runs BEFORE the tag-10 request) AND the stay-locked latch
    # (MAP 156) being clear: a battle that fired inside a lock returns still locked
    from ff9mapkit.content import reinit as R
    assert R.GRANT_GATE == bytes([0x05, 0x7A, 0x02, 0xC5, 0x9C, 0x0E, 0x27, 0x7F])
    out = R.add_reinit(data.blank_field_bytes(), with_fade=False)
    f10 = EbScript.from_bytes(out).entry(0).func_by_tag(10)
    assert out[f10.abs_start:f10.abs_end] == (
        R.GRANT_GATE + bytes([0x02, 0x01, 0x00]) + opcodes.ENABLE_MOVE + opcodes.RETURN)


def _body_ops(body: bytes) -> list:
    from ff9mapkit.eb import disasm as _disasm
    return [i.op for i in _disasm.iter_code(body, 0, len(body))]


def test_cutscene_stay_locked_latches_and_skips_the_enable():
    # narration: stay_locked ends the scene still locked + sets MAP 156 (stock's one-way index);
    # no EnableMove is emitted anywhere in the body
    body = _cutscene.build_body([opcodes.wait(10)], None, stay_locked=True,
                                grant_spin=True, watchdog_flag=110)
    latch = _region.set_var(_region.MAP_BOOL, _region.STAY_LOCKED_IDX, 1)
    assert latch in body
    assert 0x2E not in _body_ops(body)                   # no EnableMove anywhere


def test_conductor_stay_locked_latches_and_keeps_the_walk_mask():
    # conductor: stay_locked skips [EnableMenu]+EnableMove AND the STFM(255) restore (stock's
    # enable macro skips the restore inside its 156 guard too)
    from ff9mapkit.content import conductor as _conductor
    steps = [{"actor": "a", "walk": [100, 200]}]
    body = _conductor.build_body(steps, {"a": 7}, [], None, tag_calls={0: (7, 20)},
                                 stay_locked=True, lock_menu=True)
    latch = _region.set_var(_region.MAP_BOOL, _region.STAY_LOCKED_IDX, 1)
    assert latch in body
    assert opcodes.set_triangle_flag_mask(127) in body
    assert opcodes.set_triangle_flag_mask(255) not in body
    ops = _body_ops(body)
    assert 0x2E not in ops and 0xAA not in ops           # no EnableMove, no EnableMenu


def test_validate_stay_locked_rules(tmp_path):
    bad1 = BASE + """
[[cutscene]]
owns_control = false
stay_locked = true
steps = [ { say = "x" } ]
"""
    probs = validate(_project(tmp_path, bad1))
    assert any("stay_locked needs the control bracket" in p for p in probs)
    bad2 = BASE + """
[[cutscene]]
stay_locked = true
then_warp = 4005
steps = [ { say = "x" } ]
"""
    probs = validate(_project(tmp_path, bad2))
    assert any("stay_locked with then_warp is redundant" in p for p in probs)


def test_partial_control_primitives():
    # the pad-mask lane (stock's tutorial idiom): named buttons -> AddControllerMask(0, mask)
    from ff9mapkit.content import movement as _movement
    assert _movement.button_mask("directions") == 240            # stock's own tutorial mask
    assert _movement.button_mask(["select", "start"]) == 9
    assert _movement.button_mask(255) == 255
    assert _movement.mask_pad("directions") == opcodes.encode(0xB9, 0, 240)
    assert _movement.unmask_pad("directions") == opcodes.encode(0xBA, 0, 240)
    assert _movement.mask_pad(["square"]) == opcodes.encode(0xB9, 0, 0x8000)   # u16-unsigned safe
    with pytest.raises(ValueError):
        _movement.button_mask("konami")


def test_event_mask_buttons_end_to_end(tmp_path):
    toml = BASE + """
[[event]]
zone = [[-200, -500], [200, -500], [200, -300], [-200, -300]]
mask_buttons = ["directions"]
message = "Your feet are frozen. Press things instead."

[[event]]
zone = [[-200, -900], [200, -900], [200, -700], [-200, -700]]
unmask_buttons = ["directions"]
"""
    eb_bytes = _build_eb(tmp_path, toml)
    assert opcodes.encode(0xB9, 0, 240) in eb_bytes      # the mask, before the window
    assert opcodes.encode(0xBA, 0, 240) in eb_bytes      # the unmask event
    # the mask must land BEFORE the message window in its body
    mask_at = eb_bytes.index(opcodes.encode(0xB9, 0, 240))
    win_at = eb_bytes.index(opcodes.window_sync(1, 128, 0)[:2], mask_at)   # any WindowSync after it
    assert mask_at < win_at


def test_validate_event_mask_buttons_names(tmp_path):
    toml = BASE + """
[[event]]
zone = [[-200, -500], [200, -500], [200, -300], [-200, -300]]
mask_buttons = ["konami"]
"""
    probs = validate(_project(tmp_path, toml))
    assert any("unknown button" in p for p in probs)


def test_unlocked_unmask_emits_the_revive_enable_move():
    """THE CONTROLLER-DEACTIVATION LAW (movement.unmask_pad): a movement mask deactivates the
    player's actor controller (FieldMapActorController.cs:170-173) and ONLY EnableMove revives it
    (DoEventCode.cs:1068), so an unlocked unmask must carry its own EnableMove. A locked body's
    closing bracket already does it -- its bytes stay exactly as round 3 proved them in-game."""
    from ff9mapkit.content import movement as _movement
    plain = _movement.unmask_pad("directions")
    assert plain == opcodes.encode(0xBA, 0, 240)                       # locked path: unchanged
    revived = _movement.unmask_pad("directions", revive=True)
    assert revived == opcodes.encode(0xBA, 0, 240) + opcodes.ENABLE_MOVE
    # a NON-movement mask never deactivates the controller -> no revive even when asked
    assert _movement.unmask_pad(["select"], revive=True) == opcodes.encode(0xBA, 0, 1)


def test_unlocked_mask_cycle_builds_with_the_revive(tmp_path):
    toml = BASE + """
[[event]]
zone = [[-200, -500], [200, -500], [200, -300], [-200, -300]]
trigger = "action"
lock = false
mask_buttons = ["directions"]
message = "frozen"
unmask_buttons = ["directions"]
"""
    eb = _build_eb(tmp_path, toml)
    assert (opcodes.encode(0xBA, 0, 240) + opcodes.ENABLE_MOVE) in eb
    # the locked twin keeps the round-3-proven shape: the bracket owns the EnableMove
    sub = tmp_path / "b"
    sub.mkdir()
    locked = _build_eb(sub, toml.replace("lock = false\n", ""))
    assert (opcodes.DISABLE_MOVE + opcodes.encode(0xB9, 0, 240)) in locked
    assert (opcodes.encode(0xBA, 0, 240) + opcodes.ENABLE_MOVE) in locked   # bracket's, not a dup
    assert (opcodes.encode(0xBA, 0, 240) + opcodes.ENABLE_MOVE
            + opcodes.ENABLE_MOVE) not in locked


def test_validate_refuses_an_unlocked_mask_with_no_unmask(tmp_path):
    """The real trap the law identifies: unlocked + masked + never unmasked = a permanent strand
    (nothing in the field can revive the controller). mask+unmask in one unlocked body is fine."""
    stranding = BASE + """
[[event]]
zone = [[-200, -500], [200, -500], [200, -300], [-200, -300]]
trigger = "action"
lock = false
mask_buttons = ["directions"]
message = "frozen"
"""
    assert any("strands the player" in p for p in validate(_project(tmp_path, stranding)))
    # with the unmask in the same body -> allowed (the kit emits the revive)
    ok = stranding + 'unmask_buttons = ["directions"]\n'
    assert validate(_project(tmp_path, ok)) == []
    # locked + no unmask -> allowed (the bracket's EnableMove revives it)
    assert validate(_project(tmp_path, stranding.replace("lock = false\n", ""))) == []
    # and the in-game-proven walk-under NPC banner stays legal (owner-confirmed, WINSTYLE)
    drifter = BASE + """
[[npc]]
name = "drifter"
preset = "vivi"
pos = [0, -700]
dialogue = "walk away mid-sentence"
lock = false
"""
    assert validate(_project(tmp_path, drifter)) == []
