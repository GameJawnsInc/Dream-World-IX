"""Phase-3 validation: generalized content injectors.

The headline oracle is byte-exact: rebuilding the in-game-verified Vivi-hut interior from the
blank field via npc + set_player + gateway must reproduce it exactly (checked against the
manifest SHA-256, since the result embeds the game-derived blank). The other transforms
(encounter / reinit / music) are validated structurally —
applied to the blank field, the result must re-parse cleanly and contain the expected opcodes
with the rest of the script intact.
"""

from __future__ import annotations

from pathlib import Path

from ff9mapkit import data
from ff9mapkit.content import (camera, choice, conductor, cutscene, encounter, event, gateway, music,
                               npc, prop, region, reinit, text)
from ff9mapkit.eb import EbScript, opcodes
from ff9mapkit.eb.disasm import iter_code

FIX = Path(__file__).parent / "fixtures"
CLEAN = data.blank_field_bytes("us")


def _ops(eb: EbScript, entry_index: int, func_tag: int) -> list:
    f = eb.entry(entry_index).func_by_tag(func_tag)
    return [ins.op for ins in iter_code(eb.data, f.abs_start, f.abs_end)]


def test_hut_interior_reproduced_byte_exact():
    # Reproduces the in-game-verified hut interior from the blank via npc+spawn+gateway. The result
    # embeds the (game-derived) blank, so the golden is the manifest SHA-256, not shipped bytes.
    from ff9mapkit import provision
    EXIT_ZONE = [(-1100, -2400), (1100, -2400), (1100, -1750), (-1100, -1750), (-1100, -1750)]
    out = npc.inject_npc(CLEAN, 0, -700, preset="vivi", talk_text_id=500)
    out = npc.set_player_spawn(out, 0, -1350)
    out = gateway.inject_gateway(out, 4000, entrance=0, slot=3, zone=EXIT_ZONE)
    out = npc.neutralize_player_audio_cruft(out)   # build_script's final player-cleanup step (kills the 912 lag)
    assert provision.sha256(out) == provision.load_manifest()["goldens"]["EVT_HUT_INT.eb.bytes/us"]


def _build_zone_choice(tmp_path, build, extra=""):
    p = tmp_path / "z.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "Z"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        '[[choice]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nprompt = "Pull?"\n' + extra +
        '[[choice.options]]\ntext = "Yes"\nset_flag = [8001, 1]\n'
        '[[choice.options]]\ntext = "No"\n', encoding="utf-8")
    proj = build.FieldProject.load(p)
    _, _, _, _, ctx, _, _, _, _gw9 = build.collect_text(proj)
    eb = build.build_script(proj, "us", {}, choice_txids=ctx)
    return EbScript.from_bytes(eb), eb


def test_zone_choice_action_is_a_press_interact_region(tmp_path):
    # default trigger="action": a tag-3 (press-action) region with NO tread (tag 2) and NO gate flag
    # -> edge-triggered by the button, can't loop, re-usable, "decline" non-destructive.
    from ff9mapkit import build
    s, eb = _build_zone_choice(tmp_path, build)             # no trigger -> action
    reg = next(e for e in s.entries if not e.empty and e.type == 1 and e.func_by_tag(3)
               and bytes([0x7A, 0x09]) in eb[e.func_by_tag(3).abs_start:e.func_by_tag(3).abs_end])
    assert reg.func_by_tag(2) is None                       # no tread trigger -> no level-trigger loop
    ops = _ops(s, reg.index, 3)
    assert ops[0] == 0x2D and 0x1F in ops and 0x2E in ops   # body starts at DisableMove (no gate prologue)


def test_zone_choice_action_one_shot_terminates_and_gates_init(tmp_path):
    # a one-shot lever (requires_flag_clear + a consuming option that sets that flag): the consuming
    # option TerminateEntry's the region (no leftover prompt this visit) and the Init gates SetRegion
    # on the flag (no prompt on later visits when spent).
    from ff9mapkit import build
    s, eb = _build_zone_choice(tmp_path, build, extra="requires_flag_clear = 8001\n")
    reg = next(e for e in s.entries if not e.empty and e.type == 1 and e.func_by_tag(3)
               and bytes([0x7A, 0x09]) in eb[e.func_by_tag(3).abs_start:e.func_by_tag(3).abs_end])
    ops3 = _ops(s, reg.index, 3)
    assert 0x1C in ops3                                    # TerminateEntry when the flag is set (consumed)
    assert ops3.index(0x2E) < ops3.index(0x1C)            # EnableMove BEFORE terminate -> control restored
    t0 = _ops(s, reg.index, 0)
    assert t0[0] == 0x05 and 0x29 in t0                    # Init: gate (0x05) before SetRegion (0x29)


def test_zone_choice_walk_is_loop_safe_gated(tmp_path):
    # trigger="walk": a tag-2 tread region, GLOB flag-gated (loop-safe), once=false resets in Init.
    from ff9mapkit import build
    s, eb = _build_zone_choice(tmp_path, build, extra='trigger = "walk"\nonce = false\n')
    reg = next(e for e in s.entries if not e.empty and e.type == 1 and e.func_by_tag(2)
               and bytes([0x7A, 0x09]) in eb[e.func_by_tag(2).abs_start:e.func_by_tag(2).abs_end])
    ops = _ops(s, reg.index, 2)
    assert 0x2D in ops and 0x2E in ops and 0x1F in ops
    # the gate flag must be GLOB, not MAP: the 80-byte MAP array can't hold flag 8200 (out-of-bounds
    # crash). 8200 > 0xFF -> long index: GLOB_BOOL token 0xE4, MAP_BOOL token 0xE5.
    t2 = eb[reg.func_by_tag(2).abs_start:reg.func_by_tag(2).abs_end]
    assert bytes([0xE4]) in t2 and bytes([0xE5]) not in t2  # GLOB gate flag, never MAP
    assert 0x05 in _ops(s, reg.index, 0)                   # once=false -> Init resets the flag each visit


def test_zone_choice_pre_choose_default_cancel_emits_pchc(tmp_path):
    # default/cancel only (no disable): the .mes choice text carries [PCHC=count,cancel] and the body
    # runs EnableDialogChoices (0x7C) before the WindowSync (0x1F) to set the default highlighted row.
    from ff9mapkit import build
    s, eb = _build_zone_choice(tmp_path, build, extra="default = 1\ncancel = 0\n")
    mes = build.collect_text(build.FieldProject.load(tmp_path / "z.field.toml"))[0]
    assert "[PCHC=2,0]" in mes                                   # 2 rows, cancel row 0
    reg = next(e for e in s.entries if not e.empty and e.type == 1 and e.func_by_tag(3)
               and bytes([0x7A, 0x09]) in eb[e.func_by_tag(3).abs_start:e.func_by_tag(3).abs_end])
    ops3 = _ops(s, reg.index, 3)
    assert 0x7C in ops3 and ops3.index(0x7C) < ops3.index(0x1F)  # set choice params before the window


def test_zone_choice_pre_choose_disabled_emits_pchm_and_mask(tmp_path):
    # a statically-disabled option: [PCHM=count,cancel] in the text + EnableDialogChoices with the bit
    # cleared. 3 options, option 1 disabled -> mask 0b101 = 5; cancel defaults to last row (2).
    from ff9mapkit import build
    p = tmp_path / "z.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "Z"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        '[[choice]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nprompt = "Pick"\n'
        '[[choice.options]]\ntext = "A"\n'
        '[[choice.options]]\ntext = "B"\ndisabled = true\n'
        '[[choice.options]]\ntext = "C"\n', encoding="utf-8")
    proj = build.FieldProject.load(p)
    mes, _, _, _, ctx, _, _, _, _gw9 = build.collect_text(proj)
    assert "[PCHM=3,2]" in mes
    eb = build.build_script(proj, "us", {}, choice_txids=ctx)
    assert opcodes.enable_dialog_choices(0b101, 0) in eb        # row 1 masked off, default 0


def test_zone_choice_flag_gated_builds_dynamic_mask_expression(tmp_path):
    # an option hidden until a flag is set -> the body builds a scratch mask (set_var base + if(flag)
    # or_var) and passes it to EnableDialogChoices as an EXPRESSION arg (real-field pattern, Dali 407).
    from ff9mapkit import build
    from ff9mapkit.content import region
    p = tmp_path / "z.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "Z"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        '[[choice]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nprompt = "P"\n'
        '[[choice.options]]\ntext = "Buy"\n'
        '[[choice.options]]\ntext = "Use key"\nrequires_flag = 8001\n'
        '[[choice.options]]\ntext = "Leave"\n', encoding="utf-8")
    proj = build.FieldProject.load(p)
    mes, _, _, _, ctx, _, _, _, _gw9 = build.collect_text(proj)
    assert "[PCHM=3,2]" in mes
    eb = build.build_script(proj, "us", {}, choice_txids=ctx)
    sc = region.MASK_SCRATCH_IDX
    assert region.set_var(region.GLOB_UINT16, sc, 0b101) in eb                          # base rows 0,2
    assert region.or_var(region.GLOB_UINT16, sc, 0b010) in eb                           # row 1's bit
    assert opcodes.enable_dialog_choices_var(region.var_expr(region.GLOB_UINT16, sc), 0) in eb


def test_npc_speak_body_choice_branch():
    # a dialogue choice replaces the plain talk: WindowSync(prompt) + a GetChoose() branch per option
    opt_bodies = [choice.option_body({"set_flag": [8000, 1]}, reply_txid=501),
                  choice.option_body({}, reply_txid=502)]
    sb = choice.speak_body(500, opt_bodies)
    out = npc.inject_npc(CLEAN, 100, -500, preset="vivi", speak_body=sb)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out                        # structurally valid round-trip
    e = next(x for x in eb.entries if not x.empty and x.func_by_tag(3) and x.index != 0)
    speak = _ops(eb, e.index, 3)
    assert 0x1F in speak and 0x05 in speak             # WindowSync + an expression (the branch)
    f = e.func_by_tag(3)
    assert bytes([0x7A, 0x09]) in eb.data[f.abs_start:f.abs_end]   # the GetChoose() sysvar token


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


def test_reinit_with_prologue():
    """A prologue (the [deathrules] on_defeat wipe-warp check) runs FIRST in tag-10: cond-expr,
    jump-if-false, clear-expr, the proven warp fade + sound + Field -- then the normal fade-in/
    EnableMove/return tail."""
    from ff9mapkit.battle import deathrules
    pro = deathrules.field_prologue(deathrules.DeathRulesSpec(warp_to=1055))
    out = reinit.add_reinit(CLEAN, with_fade=True, prologue=pro)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out
    ops = _ops(eb, 0, 10)
    assert ops[0] == 0x05                            # the wipe-flag condition expr comes first
    assert 0x2B in ops                               # Field(warp_to) present
    assert ops.index(0x2B) < ops.index(0x2E)         # the warp branch sits before the normal EnableMove tail
    assert ops[-2:] == [0x2E, 0x04]                  # ...which is unchanged (fade-in pinned by the sibling test)
    assert deathrules.field_prologue(None) == b""    # no on_defeat -> byte-identical reinit (sibling test)
    assert deathrules.field_prologue(deathrules.DeathRulesSpec(second_wind=True)) == b""


def test_outpost_registration_in_main_init(tmp_path):
    """`[field] outpost = true` -> an unconditional Main_Init word write of the field's own id into the
    kit-reserved outpost var (rides the [startup] machinery: every entry, last-write-wins)."""
    from ff9mapkit.battle import deathrules
    from ff9mapkit.build import FieldProject, _apply_startup
    p = tmp_path / "f.field.toml"
    p.write_text("[field]\nid = 4003\nname = 'CAMP'\narea = 11\ntext_block = 1073\noutpost = true\n"
                 "\n[camera]\npitch = 45\n"
                 "\n[walkmesh]\nquad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]\n"
                 "\n[player]\nspawn = [0, -300]\n", encoding="utf-8")
    proj = FieldProject.load(p)
    out = _apply_startup(proj, CLEAN)
    assert region.set_var(region.GLOB_UINT16, deathrules.OUTPOST_BYTE, 4003) in out
    ops = _ops(EbScript.from_bytes(out), 0, 0)
    assert ops[0] == 0x05                            # the write runs FIRST in Main_Init (startup-style)
    proj.field["outpost"] = False
    assert _apply_startup(proj, CLEAN) == CLEAN      # no outpost, no [startup] -> byte-identical


def test_apply_wipe_warp_into_existing_reinit():
    """The verbatim twin of the add_reinit prologue: [deathrules] on_defeat prepends the wipe-warp check
    into an EXISTING tag-10 (offset 0 -- always safe); no tag-10 (no battles) or no block -> byte-identical."""
    from types import SimpleNamespace
    from ff9mapkit.build import _apply_wipe_warp
    dr = {"deathrules": {"on_defeat": {"warp_to": 407}}}
    with_reinit = reinit.add_reinit(CLEAN, with_fade=True)         # a stand-in for a donor's real tag-10
    out = _apply_wipe_warp(SimpleNamespace(raw=dr), with_reinit)
    eb = EbScript.from_bytes(out)
    ops = _ops(eb, 0, 10)
    assert ops[0] == 0x05 and 0x2B in ops                          # the check runs FIRST, warp present
    assert ops[-3:] == [0xEC, 0x2E, 0x04]                          # the donor's original tail is intact
    assert eb.entry(1).func_by_tag(0) is not None                  # later entries survived the relocation
    # no tag-10 (a battle-less donor) -> byte-identical; no [deathrules] -> byte-identical
    assert _apply_wipe_warp(SimpleNamespace(raw=dr), CLEAN) == CLEAN
    assert _apply_wipe_warp(SimpleNamespace(raw={}), with_reinit) == with_reinit


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


def test_music_replace_field_music():
    # REPLACE the field BGM in place (the verbatim-fork rescore): every immediate field-BGM RunSoundCode --
    # the PLAY (code 0) AND the LOAD (code 1792) of the donor's song -> new, length-preserved, intact.
    from ff9mapkit import eventscan
    from ff9mapkit.eb import edit as _edit
    base = music.add_field_music(CLEAN, 9)               # a field that PLAYs song 9
    out, n, old = music.replace_field_music(base, 42)    # old auto-detected via scan_music
    assert (old, n) == (9, 1) and len(out) == len(base)
    assert eventscan.scan_music(out) == 42               # the swap took; 9 -> 42
    assert EbScript.from_bytes(out).to_bytes() == out    # entry table / structure intact (length-preserving)
    # the LOAD must be rescored TOO -- PLAY alone leaves the OLD song loaded + audible (the Ice Cavern fork bug).
    # a field that LOADs (code 1792) + PLAYs song 9: BOTH calls rescore (n == 2) and no PLAY/LOAD of 9 survives.
    mi = EbScript.from_bytes(base).entry(0).func_by_tag(0)
    loaded = _edit.insert_bytes(base, mi.abs_start, opcodes.run_sound_code(music.SONG_LOAD, 9))
    out2, n2, _ = music.replace_field_music(loaded, 42)
    assert n2 == 2
    eb2 = EbScript.from_bytes(out2)
    assert not [i for e in eb2.entries if not e.empty for f in e.funcs for i in eb2.instrs(f)
                if i.op == 0xC5 and i.imm(0) in (music.SONG_PLAY, music.SONG_LOAD) and i.imm(1) == 9]
    # BOTH plays rescored (the Main_Init play AND the after-battle tag-10 resume) -> no silence after battle
    two = music.add_music_to_reinit(reinit.add_reinit(music.add_field_music(CLEAN, 9), with_fade=True), 9)
    out3, n3, _ = music.replace_field_music(two, 42)
    assert n3 == 2 and eventscan.scan_music(out3) == 42
    # idempotent no-op when old == new; empty result when the field has no immediate BGM to replace
    assert music.replace_field_music(base, 9) == (bytes(base), 0, 9)
    nope, n4, old4 = music.replace_field_music(CLEAN, 42)
    assert n4 == 0 and old4 is None and nope == bytes(CLEAN)


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
    # the once-flag is set BEFORE the body (FF9 chest convention: if(!opened){ opened=1; reward; msg })
    assert rng.index(region.set_var(region.GLOB_BOOL, 200, 1)) < rng.index(opcodes.add_item(232, 1))
    # armed via a shared init code entry (InitCode in Main_Init)
    assert 0x07 in _ops(eb, 0, 0)


def test_event_remove_item_and_trade():
    # remove_item is the symmetric take-item lever (RemoveItem 0x49); name-resolved like give_item.
    assert event.take_item(236, 2) == opcodes.remove_item(236, 2)
    assert event.take_item("Potion", 1) == opcodes.remove_item(236, 1)   # name -> id
    ZONE = [(200, -300), (600, -300), (600, -700), (200, -700)]
    body = event.take_item("Dagger", 1) + event.give_item("Potion", 1)   # a trade: Dagger -> Potion
    out = event.inject_events(CLEAN, [{"zone": ZONE, "body": body, "once_flag": 201}])
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out
    _, rng = _event_region(eb)
    assert opcodes.remove_item(1, 1) in rng and opcodes.add_item(236, 1) in rng   # both ops emitted


def test_event_sets_flag_before_message(tmp_path):
    # an event doesn't lock movement, so its flag must land on TRIGGER -- before the acknowledgement
    # message (not only when the player closes the window). Verify set_flag precedes the WindowSync.
    from ff9mapkit import build
    p = tmp_path / "z.field.toml"
    p.write_text(
        '[field]\nid=4003\nname="Z"\narea=11\ntext_block=1073\n\n'
        '[camera]\npitch=45\nfov=42.2\n\n'
        '[walkmesh]\nquad=[[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        '[[event]]\nname="key"\nzone=[[10,-10],[50,-10],[50,-50],[10,-50]]\n'
        'message="Found it!"\nset_flag=[8001,1]\n', encoding="utf-8")
    proj = build.FieldProject.load(p)
    _, _, et, _, _, _, _, _, _gw9 = build.collect_text(proj)
    eb = build.build_script(proj, "us", {}, event_txids=et)
    setflag = region.set_var(region.GLOB_BOOL, 8001, 1)
    msg = opcodes.window_sync(1, 128, et[0])
    assert setflag in eb and msg in eb
    assert eb.index(setflag) < eb.index(msg)        # flag set BEFORE the acknowledgement message


def test_chest_niceties_match_real_field_bytes():
    # GetItemCount(236)<99 guard + SetTextVariable(0,236) -- byte-exact vs Dali/Storage field 407
    assert region.cond_item_count_lt(236, 99) == bytes.fromhex("057dec00647d6300187f")
    assert opcodes.set_text_variable(0, 236) == bytes.fromhex("66000 0ec00".replace(" ", ""))


def test_event_received_window_and_space_check(tmp_path):
    # received -> SetTextVariable(0,item) + window-7 item-get box w/ "Received [ITEM=0]!" text;
    # require_space -> the whole reward wrapped in if(GetItemCount(item) < 99) (chest space guard).
    from ff9mapkit import build
    p = tmp_path / "z.field.toml"
    p.write_text(
        '[field]\nid=4003\nname="Z"\narea=11\ntext_block=1073\n\n'
        '[camera]\npitch=45\nfov=42.2\n\n'
        '[walkmesh]\nquad=[[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        '[[event]]\nname="chest"\nzone=[[10,-10],[50,-10],[50,-50],[10,-50]]\n'
        'give_item=[236,1]\nreceived=true\nrequire_space=true\n', encoding="utf-8")
    proj = build.FieldProject.load(p)
    mes, _, et, _, _, _, _, _, _gw9 = build.collect_text(proj)
    assert "Received [ITEM=0]!" in mes                              # canonical item-get text
    eb = build.build_script(proj, "us", {}, event_txids=et)
    assert opcodes.set_text_variable(0, 236) in eb                 # SetTextVariable(0, item)
    assert opcodes.window_sync(7, 0, et[0]) in eb                  # window-7 item-get box
    assert region.cond_item_count_lt(236, 99) in eb                # space guard present


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
    # a leading reorder Wait (so the lock outlives Main_Init's EnableMove), then the ungated sequence
    assert body == (cutscene.wait(cutscene.REORDER_WAIT) + opcodes.DISABLE_MOVE + cutscene.wait(5)
                    + opcodes.ENABLE_MOVE + opcodes.RETURN)


def test_cutscene_body_reorder_wait_precedes_disablemove():
    """The narration director yields briefly BEFORE DisableMove so Main_Init's EnableMove can't override
    the lock (the in-game 'control not locked' fix)."""
    body = cutscene.build_body([cutscene.say(500)], once_flag=None)
    assert body.startswith(cutscene.wait(cutscene.REORDER_WAIT))
    assert body.index(cutscene.wait(cutscene.REORDER_WAIT)) < body.index(opcodes.DISABLE_MOVE)


# --- the STORY-EVENT DIRECTOR (#13): beat-gated, story-advancing cutscenes -------------------------

def test_early_return_unless_matches_onentry_gate_shape():
    # the director's prologue gate re-emits onentry.scenario_gate's exact byte shape (onentry imports
    # cutscene, so it can't be imported back) -- pin the parity so the shapes never drift.
    from ff9mapkit.content import onentry
    cond = region.cond_eq(region.GLOB_UINT16, 0, 2600)
    assert cutscene.early_return_unless(cond) == onentry.scenario_gate(2600)


def test_cutscene_body_gate_and_end_writes():
    cond = region.cond_eq(region.GLOB_UINT16, 0, 2600)
    gate = cutscene.early_return_unless(cond)
    adv = region.set_var(region.GLOB_UINT16, 0, 2610)          # the set_scenario advance bytes
    body = cutscene.build_body([cutscene.say(500)], once_flag=230, gate=gate, end_writes=adv)
    assert body.startswith(gate)                                # the beat gate runs FIRST (early return)
    assert adv in body
    once_set = region.set_var(region.GLOB_BOOL, 230, 1)
    assert body.index(adv) < body.index(once_set)               # advance INSIDE the once-block, before its set
    # defaults are byte-identical to the pre-director shape
    assert cutscene.build_body([cutscene.say(500)], once_flag=230) == \
        cutscene.build_body([cutscene.say(500)], once_flag=230, gate=b"", end_writes=b"")


def test_actor_walk_sets_high_turn_speed_then_walks():
    """A walk cranks the walk-turn-speed first, then InitWalk + Walk -- so the Walk rotates tightly
    toward the target and goes straight (never arcs/orbits a point behind the actor), with no animated
    pre-turn that could hang at 180."""
    expected = (opcodes.set_walk_turn_speed(cutscene.WALK_TURN_SPEED) + opcodes.stop_animation()
                + opcodes.init_walk() + opcodes.walk(100, -200))
    assert cutscene.actor_walk(100, -200) == expected
    assert cutscene.actor_walk(100, -200, speed=15) == opcodes.set_walk_speed(15) + expected


def test_actor_teleport_moves_then_reenables_pathing():
    """A teleport instant-moves (MoveInstantXZY, Z-negated) then SetPathing(1) so a following walk
    paths normally."""
    assert cutscene.actor_teleport(-1150, -800) == (
        opcodes.move_instant_xzy(-1150, -800, 0) + opcodes.set_pathing(1))


def test_npc_without_intro_is_byte_identical():
    """An NPC with no cutscene intro is byte-identical to before (the splice is purely additive)."""
    a = npc.inject_npc(CLEAN, 100, -500, preset="vivi", talk_text_id=500)
    b = npc.inject_npc(CLEAN, 100, -500, preset="vivi", talk_text_id=500, intro=None)
    assert a == b


def test_cutscene_injected_and_armed():
    out = cutscene.inject_cutscene(CLEAN, [cutscene.say(500), cutscene.set_flag(210)], once_flag=230)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out
    cs = next(e for e in eb.entries if not e.empty and e.type == 0 and e.index != 0
              and any(i.op == 0x2D for i in iter_code(eb.data, e.func_by_tag(0).abs_start,
                                                      e.func_by_tag(0).abs_end)))
    assert cs is not None
    assert 0x07 in _ops(eb, 0, 0)                                     # InitCode arms it from Main_Init


# --- multi-actor CONDUCTOR (the central-director model; memory project-ff9-cutscene-multiactor) ---

def test_conductor_ex_opcodes_roundtrip():
    """The targeted *Ex / RunScript helpers encode to bytes that disassemble back to the same opcode
    (arg layouts verified vs the engine optables); the conductor drives actors with these."""
    from ff9mapkit.eb.disasm import read_code
    cases = [
        (opcodes.window_sync_ex(11, 0, 128, 56), 0x95, 7),
        (opcodes.turn_instant_ex(12, 128), 0x87, 4),
        (opcodes.timed_turn_ex(12, 21, 16), 0xBB, 5),
        (opcodes.wait_turn_ex(12), 0xBC, 3),
        (opcodes.run_animation_ex(11, 2307), 0xBD, 5),
        (opcodes.wait_animation_ex(11), 0xBE, 3),
        (opcodes.run_script(2, 250, 16), 0x12, 5),
        (opcodes.run_script_async(2, 11, 24), 0x10, 5),
        (opcodes.run_shared_script(8), 0x43, 3),
        (opcodes.wait_shared_script(), 0x44, 1),
    ]
    for b, op, length in cases:
        ins, pos = read_code(b, 0)
        assert ins.op == op and ins.length == length and pos == len(b), f"{op:#x} {b.hex()}"
    # WindowSyncEx carries the TARGET object-id as operand 0 -- a conductor addressing an actor by id
    ins, _ = read_code(opcodes.window_sync_ex(11, 0, 128, 56), 0)
    assert ins.imm(0) == 11 and ins.imm(3) == 56


def test_conductor_drives_two_actors_by_id():
    """One conductor body drives TWO actors by uid (== their entry slots), gated once, control-locked."""
    uid_by_name = {"garnet": 11, "steiner": 12}
    steps = [{"actor": "garnet", "turn": 128}, {"actor": "garnet", "say": "Welcome home."},
             {"actor": "steiner", "animation": 2307}, {"actor": "steiner", "say": "Princess!"}, {"wait": 20}]
    body = conductor.build_body(steps, uid_by_name, [1000, 1001], once_flag=8100)
    assert body.startswith(region.cond_not(region.GLOB_BOOL, 8100))    # gated by the once flag
    # the reorder Wait (so the lock outlives Main_Init's EnableMove) sits inside the gate, before DisableMove
    assert body.index(cutscene.wait(cutscene.REORDER_WAIT)) < body.index(opcodes.DISABLE_MOVE)
    assert opcodes.turn_instant_ex(11, 128) in body                    # garnet turns, by id
    assert opcodes.window_sync_ex(11, 0, 128, 1000) in body            # garnet's line, by id
    assert opcodes.run_animation_ex(12, 2307) in body                  # steiner animates, by id
    assert opcodes.window_sync_ex(12, 0, 128, 1001) in body            # steiner's line, by id
    assert region.set_var(region.GLOB_BOOL, 8100, 1) in body           # once-guard set on completion
    ops = [i.op for i in iter_code(body, 0, len(body))]                # decode (single-byte index() is unsafe)
    assert 0x2D in ops and 0x2E in ops and ops.index(0x2D) < ops.index(0x2E)  # lock for the duration
    assert body.endswith(opcodes.RETURN)


def test_conductor_polls_for_control_grant_then_locks():
    """In-game finding (2026-06-28, two iterations): the field re-grants control as its entry camera settles,
    past any fixed warmup (the player could walk + dismiss the first window, THEN lost control). So the
    conductor DisableMoves, then SPINS until the engine re-grants control (IsMovementEnabled, sysvar 2), then
    re-locks -- the lock then lands AFTER the grant. The spin is bounded so it can't hang."""
    spin = conductor.wait_for_control_then_lock(cap=5)
    sops = [i.op for i in iter_code(spin, 0, len(spin))]
    assert 0x03 in sops                                           # JMP_IF -> exits early the moment control is granted
    assert sops.count(0x22) == 5                                  # one Wait per capped frame (bounded)
    assert sops[-1] == 0x2D                                       # ends by locking (DisableMove) after the grant
    # in build_body the spin sits after an early DisableMove; each beat still re-locks as a backstop
    body = conductor.build_body([{"actor": "player", "say": "a"}, {"actor": "player", "turn": 64}],
                                {}, [500], once_flag=None)
    bops = [i.op for i in iter_code(body, 0, len(body))]
    assert 0x03 in bops                                           # the control-grant poll is present
    for k, op in enumerate(bops):                                 # each say/turn beat is re-locked (DisableMove)
        if op in (0x95, 0x87):
            assert bops[k - 1] == 0x2D, f"beat op {op:#x} not re-locked"
    # owns_control = False -> no lock, no poll (the field keeps control)
    body2 = conductor.build_body([{"actor": "player", "say": "a"}], {}, [500], once_flag=None, owns_control=False)
    b2 = [i.op for i in iter_code(body2, 0, len(body2))]
    assert 0x2D not in b2 and 0x03 not in b2


def test_conductor_player_resolves_to_250():
    body = conductor.build_body([{"actor": "player", "say": "..."}], {}, [1000], once_flag=None)
    assert opcodes.window_sync_ex(250, 0, 128, 1000) in body           # "player" -> uid 250 (control char)


def test_conductor_avoids_blocking_waits_on_actors():
    """Softlock guard: anim/turn use the NON-blocking forms (RunAnimationEx+Wait, TurnInstantEx) -- never
    WaitAnimationEx/WaitTurnEx, which hang on a player-cloned actor whose clip doesn't drive the wait."""
    body = conductor.build_body([{"actor": "player", "animation": 1713}, {"actor": "player", "turn": 64}],
                                {}, [], once_flag=None)
    assert opcodes.run_animation_ex(250, 1713) in body and opcodes.turn_instant_ex(250, 64) in body
    assert opcodes.wait_animation_ex(250) not in body and opcodes.wait_turn_ex(250) not in body


def test_conductor_injected_and_armed():
    out = conductor.inject_conductor(CLEAN, [{"actor": "player", "say": "hi"}], {}, [500], once_flag=8100)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out                                        # structurally valid
    assert 0x07 in _ops(eb, 0, 0)                                      # InitCode arms it from Main_Init
    drv = next(e for e in eb.entries if not e.empty and e.index != 0 and e.func_by_tag(0)
               and any(i.op == 0x95 for i in iter_code(eb.data, e.func_by_tag(0).abs_start,
                                                        e.func_by_tag(0).abs_end)))
    assert drv is not None                                             # the conductor entry drives by WindowSyncEx


def test_conductor_then_warp_replaces_enablemove():
    body = conductor.build_body([{"actor": "player", "say": "bye"}], {}, [500], once_flag=8100, then_warp=1153)
    assert opcodes.ENABLE_MOVE not in body                             # destination restores control
    assert any(i.op == 0x2B for i in iter_code(body, 0, len(body)))    # ends with Field(1153)


def test_conductor_two_actor_field_builds_end_to_end(tmp_path):
    """Full synth build: a field with two NPCs + a [cutscene] conductor injects one director entry that
    drives both NPCs (by their entry slots) and the player (250). The string-list `actor = [...]` form
    avoids the TOML array-of-tables ordering trap (steps must precede [[cutscene.actor]] otherwise)."""
    from ff9mapkit import build
    p = tmp_path / "c.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "C"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-200,-200],[200,-200],[200,200],[-200,200]]\n\n'
        '[player]\nspawn = [0, 150]\n\n'
        '[[npc]]\nname = "vivi1"\npreset = "vivi"\npos = [-80, 0]\ndialogue = "."\n\n'
        '[[npc]]\nname = "vivi2"\npreset = "vivi"\npos = [80, 0]\ndialogue = "."\n\n'
        '[cutscene]\nonce = true\nactors = ["vivi1", "vivi2", "player"]\n'
        'steps = [\n'
        '  { actor = "vivi1", turn = 128 },\n'
        '  { actor = "vivi1", say = "Hello there." },\n'
        '  { actor = "vivi2", animation = "glad" },\n'
        '  { actor = "vivi2", say = "Hi!" },\n'
        '  { actor = "player", say = "..." },\n'
        '  { wait = 20 },\n'
        ']\n', encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert build.lint_logic(proj) == [] or all("cutscene" not in m for m in build.lint_logic(proj))
    mes, npc_txids, _ev, cs_txids, _ch, _oe, _ate, _chest, _gw9 = build.collect_text(proj)
    assert len(cs_txids) == 3                                          # three say steps -> three txids
    eb = build.build_script(proj, "us", npc_txids, cutscene_txids=cs_txids)
    s = EbScript.from_bytes(eb)
    assert s.to_bytes() == eb                                          # re-parses cleanly
    # find the conductor entry (a code entry whose func 0 holds WindowSyncEx) and check it drives all three
    drv = next(e for e in s.entries if not e.empty and e.index != 0 and e.func_by_tag(0)
               and any(i.op == 0x95 for i in iter_code(s.data, e.func_by_tag(0).abs_start,
                                                       e.func_by_tag(0).abs_end)))
    body = s.data[drv.func_by_tag(0).abs_start:drv.func_by_tag(0).abs_end]
    speak_uids = {i.imm(0) for i in iter_code(body, 0, len(body)) if i.op == 0x95}
    assert 250 in speak_uids                                          # the player speaks, by uid 250
    assert len([u for u in speak_uids if u != 250]) >= 1              # at least one NPC speaks, by its slot
    assert opcodes.DISABLE_MOVE in body and opcodes.ENABLE_MOVE in body


def test_conductor_walk_tag_body_is_animated_walk():
    """A walk tag runs in the actor's own context (so base Walk animates it). Recipe: SetWalkTurnSpeed +
    StopAnimation + InitWalk + Walk + RETURN -- no WaitTurn/WaitAnimation (they hang on a player clone).
    Collision is handled by STAGING (clear paths), not a collision-off wrap (which can hang/drift off-mesh)."""
    body = conductor.walk_tag_body(100, -50)
    ops = [i.op for i in iter_code(body, 0, len(body))]
    assert ops == [0x55, 0x42, 0x25, 0x23, 0x04]                   # SetWalkTurnSpeed/StopAnim/InitWalk/Walk/RET


def test_conductor_walk_step_compiles_to_runscriptsync():
    """The conductor can't walk an actor inline (no targeted WalkEx), so a walk beat is a RunScriptSync into
    the actor's pre-generated walk tag (by uid) -- blocking, so it animates then the scene continues."""
    body = conductor.compile_steps([{"actor": "npc", "walk": [10, 20]}], {"npc": 5}, [], tag_calls={0: (5, 20)})
    assert opcodes.run_script_sync(conductor.WALK_LEVEL, 5, 20) in body
    # without the pre-generated tag, compiling a walk beat is a hard error (not a silent no-op)
    import pytest
    with pytest.raises(ValueError):
        conductor.compile_steps([{"actor": "npc", "walk": [10, 20]}], {"npc": 5}, [])


def test_conductor_walk_field_builds_end_to_end(tmp_path):
    """Full build: two NPCs each with a walk beat -> a walk tag (20) added to each NPC entry, and the
    conductor RunScriptSyncs into (uid, 20) for each."""
    from ff9mapkit import build
    p = tmp_path / "w.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "W"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-300,-300],[300,-300],[300,300],[-300,300]]\n\n'
        '[player]\nspawn = [0, 150]\n\n'
        '[[npc]]\nname = "lefty"\npreset = "vivi"\npos = [-100, 0]\ndialogue = "."\n\n'
        '[[npc]]\nname = "righty"\npreset = "vivi"\npos = [100, 0]\ndialogue = "."\n\n'
        '[cutscene]\nonce = true\nactors = ["lefty", "righty"]\n'
        'steps = [ { actor = "lefty", walk = [0, -150] }, { actor = "righty", walk = [150, 100] } ]\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert [m for m in build.lint_logic(proj) if "cutscene" in m] == []
    _mes, npc_txids, _e, cs_txids, _c, _o, _a, _ch, _gw = build.collect_text(proj)
    s = EbScript.from_bytes(build.build_script(proj, "us", npc_txids, cutscene_txids=cs_txids))
    walk_entries = [e.index for e in s.entries if not e.empty and e.func_by_tag(20)]
    assert len(walk_entries) == 2                                  # both NPC entries got a walk tag
    drv = next(e for e in s.entries if not e.empty and e.index != 0 and e.func_by_tag(0)
               and any(i.op == 0x14 for i in iter_code(s.data, e.func_by_tag(0).abs_start, e.func_by_tag(0).abs_end)))
    calls = [(i.imm(0), i.imm(1), i.imm(2)) for i in iter_code(s.data, drv.func_by_tag(0).abs_start,
                                                               drv.func_by_tag(0).abs_end) if i.op == 0x14]
    assert calls == [(2, walk_entries[0], 20), (2, walk_entries[1], 20)]  # RunScriptSync(level, uid, tag) per walk


def test_conductor_player_walk_supported(tmp_path):
    """walk on \"player\" runs in the PLAYER's OWN entry (DefinePlayerCharacter), addressed by the control
    sentinel uid 250: the walk tag lands on the player entry (NOT an NPC slot), and the conductor
    RunScriptSyncs into (250, tag). No longer rejected by validation."""
    from ff9mapkit import build
    from ff9mapkit.content import player as _player
    p = tmp_path / "pw.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "PW"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-300,-300],[300,-300],[300,300],[-300,300]]\n\n'
        '[player]\nspawn = [0, 150]\n\n'
        '[[npc]]\nname = "vivi1"\npreset = "vivi"\npos = [-100, 0]\ndialogue = "."\n\n'
        '[cutscene]\nactors = ["vivi1", "player"]\n'
        'steps = [ { actor = "vivi1", say = "Follow me." }, { actor = "player", walk = [0, 0] } ]\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert [m for m in build.validate(proj) if "walk" in m] == []  # player-walk is no longer flagged
    _mes, npc_txids, _e, cs_txids, _c, _o, _a, _ch, _gw = build.collect_text(proj)
    s = EbScript.from_bytes(build.build_script(proj, "us", npc_txids, cutscene_txids=cs_txids))
    pe = _player.find_player_entry(s)
    assert s.entry(pe).func_by_tag(20) is not None                # the walk tag landed on the PLAYER entry
    assert not any(e.func_by_tag(20) for e in s.entries if not e.empty and e.index != pe)  # only there
    drv = next(e for e in s.entries if not e.empty and e.index != 0 and e.func_by_tag(0)
               and any(i.op == 0x95 for i in iter_code(s.data, e.func_by_tag(0).abs_start, e.func_by_tag(0).abs_end)))
    calls = [(i.imm(0), i.imm(1), i.imm(2)) for i in iter_code(s.data, drv.func_by_tag(0).abs_start,
                                                               drv.func_by_tag(0).abs_end) if i.op == 0x14]
    assert (2, 250, 20) in calls                                  # RunScriptSync(level=2, uid=250 player, tag=20)


def test_conductor_group_parallel_by_with_prev():
    """A step with with_prev joins the PRECEDING group; any other step starts a new one. with_prev on step 0
    (no preceding group) falls back to a standalone leader (validation flags it)."""
    steps = [{"walk": 1}, {"walk": 2, "with_prev": True}, {"say": "x"}, {"turn": 1}, {"turn": 2, "with_prev": True}]
    assert [[i for i, _ in g] for g in conductor.group_parallel(steps)] == [[0, 1], [2], [3, 4]]
    assert [[i for i, _ in g] for g in conductor.group_parallel([{"turn": 1, "with_prev": True}])] == [[0]]


def test_conductor_parallel_walks_fork_async_then_drain():
    """Two walks in one parallel group (the 2nd with_prev) FORK via RunScriptAsync (0x10, no level gate), then
    the conductor DRAINS each actor's busy script level with RunScriptSync (0x14) into a bare-RETURN join tag
    -- the engine's only async barrier (requestAcceptable = lv < obj.level). Order: both forks, THEN both
    drains (so the walks run together, then the scene waits for both)."""
    steps = [{"actor": "a", "walk": [0, 0]}, {"actor": "b", "walk": [1, 1], "with_prev": True}]
    body = conductor.compile_steps(steps, {"a": 5, "b": 6}, [],
                                   tag_calls={0: (5, 20), 1: (6, 20)}, join_tags={5: 19, 6: 19})
    ops = [(i.op, i.imm(0), i.imm(1), i.imm(2)) for i in iter_code(body, 0, len(body))]
    assert ops == [(0x10, 2, 5, 20), (0x10, 2, 6, 20), (0x14, 2, 5, 19), (0x14, 2, 6, 19)]
    # a SINGLETON walk still compiles to a blocking RunScriptSync into the walk tag (unchanged, no async)
    solo = conductor.compile_steps([{"actor": "a", "walk": [0, 0]}], {"a": 5}, [], tag_calls={0: (5, 20)})
    assert [i.op for i in iter_code(solo, 0, len(solo))] == [0x14]


def test_conductor_parallel_anim_absorbs_hold_into_join():
    """A parallel anim FIRES (RunAnimationEx, no inline Wait) and its hold is absorbed into ONE join Wait, so
    the anim plays while the walk runs async; then the walk's sync-drain blocks for the rest."""
    steps = [{"actor": "a", "walk": [0, 0]}, {"actor": "b", "animation": 1713, "with_prev": True}]
    body = conductor.compile_steps(steps, {"a": 5, "b": 6}, [], tag_calls={0: (5, 20)}, join_tags={5: 19})
    ops = [i.op for i in iter_code(body, 0, len(body))]
    assert ops == [0x10, 0xBD, 0x22, 0x14]                         # async walk, RunAnimationEx, Wait(hold), drain
    assert ops.count(0x22) == 1                                    # the hold is the join Wait, not a per-anim Wait
    assert opcodes.wait(cutscene.ANIM_HOLD) in body


def test_conductor_parallel_walk_field_builds_end_to_end(tmp_path):
    """Full synth build: two NPCs walk SIMULTANEOUSLY (the 2nd beat with_prev). Each NPC entry gets a walk tag
    (20) AND the bare-RETURN join tag (19); the conductor forks both async then drains both (into tag 19)."""
    from ff9mapkit import build
    p = tmp_path / "par.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "PAR"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-300,-300],[300,-300],[300,300],[-300,300]]\n\n'
        '[player]\nspawn = [0, 150]\n\n'
        '[[npc]]\nname = "lefty"\npreset = "vivi"\npos = [-100, 0]\ndialogue = "."\n\n'
        '[[npc]]\nname = "righty"\npreset = "vivi"\npos = [100, 0]\ndialogue = "."\n\n'
        '[cutscene]\nonce = true\nactors = ["lefty", "righty"]\n'
        'steps = [ { actor = "lefty", walk = [0, -150] }, { actor = "righty", walk = [150, 100], with_prev = true } ]\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert [m for m in build.lint_logic(proj) if "cutscene" in m] == []
    assert [m for m in build.validate(proj) if "with_prev" in m or "parallel" in m.lower()] == []
    _mes, npc_txids, _e, cs_txids, _c, _o, _a, _ch, _gw = build.collect_text(proj)
    s = EbScript.from_bytes(build.build_script(proj, "us", npc_txids, cutscene_txids=cs_txids))
    parallel_entries = [e.index for e in s.entries if not e.empty and e.func_by_tag(20) and e.func_by_tag(19)]
    assert len(parallel_entries) == 2                              # both NPC entries got a walk tag AND a join tag
    drv = next(e for e in s.entries if not e.empty and e.index != 0 and e.func_by_tag(0)
               and any(i.op == 0x10 for i in iter_code(s.data, e.func_by_tag(0).abs_start, e.func_by_tag(0).abs_end)))
    cops = [(i.op, i.imm(0), i.imm(1), i.imm(2)) for i
            in iter_code(s.data, drv.func_by_tag(0).abs_start, drv.func_by_tag(0).abs_end) if i.op in (0x10, 0x14)]
    forks = [c for c in cops if c[0] == 0x10]
    drains = [c for c in cops if c[0] == 0x14]
    assert len(forks) == 2 and len(drains) == 2                    # two async forks, two sync-drains
    assert all(d[3] == 19 for d in drains)                        # drains target the bare-RETURN join tag (imm2)
    assert {f[2] for f in forks} == set(parallel_entries)         # forks target both NPC slots (imm1 = uid)
    assert cops.index(forks[-1]) < cops.index(drains[0])          # fork BOTH, then join BOTH


def test_conductor_parallel_validation(tmp_path):
    """with_prev guards: not on step 0; only walk/anim/turn (say/wait/set_flag is a sequential barrier, as a
    leader OR a follower); an actor can't act twice in one parallel group. A valid parallel scene is clean."""
    from ff9mapkit import build
    def probs(steps_toml):
        p = tmp_path / "v.field.toml"
        p.write_text(
            '[field]\nid = 4003\nname = "V"\narea = 11\ntext_block = 1073\n\n'
            '[camera]\npitch = 45\nfov = 42.2\n\n'
            '[walkmesh]\nquad = [[-300,-300],[300,-300],[300,300],[-300,300]]\n\n'
            '[player]\nspawn = [0, 150]\n\n'
            '[[npc]]\nname = "a"\npreset = "vivi"\npos = [-100, 0]\ndialogue = "."\n\n'
            '[[npc]]\nname = "b"\npreset = "vivi"\npos = [100, 0]\ndialogue = "."\n\n'
            '[cutscene]\nactors = ["a", "b"]\nsteps = ' + steps_toml + '\n', encoding="utf-8")
        return build.validate(build.FieldProject.load(p))
    assert any("step 0" in m and "with_prev" in m for m
               in probs('[ { actor = "a", turn = 0, with_prev = true } ]'))
    assert any("with_prev" in m and "sequential" in m.lower() for m
               in probs('[ { actor = "a", turn = 0 }, { actor = "b", say = "hi", with_prev = true } ]'))
    assert any("parallel" in m.lower() for m
               in probs('[ { actor = "a", say = "hi" }, { actor = "b", turn = 0, with_prev = true } ]'))
    assert any("already acts" in m for m
               in probs('[ { actor = "a", turn = 0 }, { actor = "a", animation = "glad", with_prev = true } ]'))
    assert [m for m in probs('[ { actor = "a", turn = 0 }, { actor = "b", turn = 64, with_prev = true } ]')
            if "with_prev" in m or "parallel" in m.lower() or "barrier" in m.lower()] == []


def test_text_mes_format_and_mapping():
    line = text.mes_entry("I miss you Zidane", 500)
    assert line == "_[TXID=500][STRT=10,1][TAIL=UPR]I miss you Zidane[ENDN]"
    body, mapping = text.build_mes(["hello", "world"], start_txid=500)
    assert mapping == {0: 500, 1: 501}
    assert "[TXID=501]" in body and body.endswith("\n")


# ----- prop attachment (held items) + the IsActuallyTalkable bounds fix -----

def test_npc_talk_func_is_at_least_9_bytes():
    """The engine's IsActuallyTalkable reads tag3[ip+7]/[ip+8]; the NPC talk func must be >= 9 bytes or
    that indexes past the entry buffer -> a per-frame IndexOutOfRange near the NPC (the latent bug)."""
    out = npc.inject_npc(CLEAN, 0, 0, preset="vivi", slot=EbScript.from_bytes(CLEAN).first_free_slot())
    e = next(en for en in EbScript.from_bytes(out).entries if not en.empty and en.func_by_tag(3))
    f3 = e.func_by_tag(3)
    assert f3.abs_end - f3.abs_start >= 9


def test_bare_prop_is_init_only():
    """A non-interactive prop is Init-only (1 func, no tag-3) -> IsActuallyTalkable short-circuits."""
    out = prop.inject_prop(CLEAN, 0, 0, model=75, pose=7339,
                           slot=EbScript.from_bytes(CLEAN).first_free_slot())
    chest = next(e for e in EbScript.from_bytes(out).entries if not e.empty and any(
        ins.op == 0x2F and int.from_bytes(out[ins.off + 2:ins.off + 4], "little") == 75
        for f in e.funcs for ins in iter_code(out, f.abs_start, f.abs_end)))
    assert [f.tag for f in chest.funcs] == [0]


def test_prop_attach_emits_attachobject():
    """attach_to binds the prop to the carrier's bone: AttachObject(prop_slot, carrier_slot, bone)."""
    cslot = EbScript.from_bytes(CLEAN).first_free_slot()
    out = npc.inject_npc(CLEAN, 0, 0, preset="vivi", slot=cslot)
    pslot = EbScript.from_bytes(out).first_free_slot()
    out = prop.inject_prop(out, 0, 0, model=234, pose=8238, slot=pslot, attach_to=cslot, bone=11)
    attaches = [(out[ins.off + 2], out[ins.off + 3], out[ins.off + 4])
                for e in EbScript.from_bytes(out).entries if not e.empty
                for f in e.funcs for ins in iter_code(out, f.abs_start, f.abs_end) if ins.op == 0x4C]
    assert (pslot, cslot, 11) in attaches


def test_held_poses_catalog_shape_and_beatrix():
    """HELD_POSES maps (carrier, prop) -> (bone, prop_pose, holder_pose); spot-check Beatrix + sword."""
    from ff9mapkit import archetypes as AR, prop_archetypes as PA
    from ff9mapkit._held_poses import HELD_POSES
    assert HELD_POSES[(AR.resolve("beatrix")[0], PA.resolve("save_the_queen")[0])] == (16, 1894, 2978)
    assert all(len(v) == 3 and all(isinstance(x, int) for x in v) for v in HELD_POSES.values())


# --------------------------------------------------------------------------- [[chest]] on the synth path
# The openable/savable treasure chest (proven on verbatim forks) on a FROM-SCRATCH field: collect_text gives
# its centered "Received X" box a txid in the field's own 500-block; build_script appends the chest object.
_CHEST_BASE = (
    '[field]\nid = 4003\nname = "Z"\narea = 11\ntext_block = 1073\n\n'
    '[camera]\npitch = 45\nfov = 42.2\n\n'
    '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
)


def _build_synth(tmp_path, body):
    """Build a from-scratch field (CHEST_BASE + body) through collect_text -> build_script (the synth path)."""
    from ff9mapkit import build
    p = tmp_path / "z.field.toml"
    p.write_text(_CHEST_BASE + body, encoding="utf-8")
    proj = build.FieldProject.load(p)
    mes, _n, _e, _c, _ch, _o, _a, chest_txids, _gw9 = build.collect_text(proj)
    eb = build.build_script(proj, "us", {}, chest_txids=chest_txids)
    return mes, chest_txids, eb


def _synth_baseline_errors(tmp_path):
    """eblint errors for a CONTENT-FREE synth field (the blank field's own baseline -- e.g. an empty Loop --
    which the synth path never lints at build time). A chest that adds NO error beyond this is structurally
    clean, the same before/after comparison the verbatim injectors use."""
    from ff9mapkit import build, eblint
    _m, _t, eb = _build_synth(tmp_path, "")
    return eblint.errors(eblint.lint_eb(eb))


def test_synth_item_chest_full_contraption(tmp_path):
    # the SAME contraption the verbatim path builds, now appended to a synthesized field: a flag-gated
    # open/closed pose Init + collision box + a press-to-open handler that gives the item and shows a box.
    from ff9mapkit import eblint
    mes, chest_txids, eb = _build_synth(tmp_path, '[[chest]]\npos = [0, 60]\nitem = ["Potion", 1]\nflag = 8520\n')
    txid = chest_txids[0]
    assert txid >= text.DEFAULT_BASE_TXID                          # a real id in the synth 500-block
    # the REAL FF9 item-get box (field 200/407 txid 51): [STRT=69,3] (width,lines) + DEFT tail AUTO-CENTER it;
    # mes_entry's dialogue default (10,1)/UPR would pin it to the top-right corner (the reported bug).
    assert "[STRT=69,3][TAIL=DEFT][WDTH=0,69,14,0,-1][IMME]" in mes and "Received [ITEM=0]!" in mes
    assert "[STRT=10,1]" not in mes.split("[ENDN]")[0]            # the chest line is NOT the dialogue default
    assert opcodes.set_stand_animation(7338) in eb and opcodes.set_stand_animation(7339) in eb  # open/closed poses
    assert opcodes.encode(0x4B, 1, 40, 45) in eb                  # SetObjectLogicalSize -> the collision box
    assert opcodes.run_animation(7336) in eb                      # lid-open clip (the tag-3 open handler)
    assert opcodes.window_sync(7, 0, txid) in eb                  # window-7 Received box -> the .mes line
    assert eblint.errors(eblint.lint_eb(eb)) == _synth_baseline_errors(tmp_path)   # adds no new error


def test_synth_gil_chest_uses_numb_box(tmp_path):
    from ff9mapkit import eblint
    mes, chest_txids, eb = _build_synth(tmp_path, '[[chest]]\npos = [0, 60]\ngil = 500\nflag = 8520\n')
    # the real gil box (field 200/407 txid 53): own STRT=86,3 geometry, WDTH height 64, gold-coloured number.
    assert "[STRT=86,3][TAIL=DEFT][WDTH=0,86,64,0,-1][IMME]" in mes
    assert "[NUMB=0] Gil" in mes
    assert event.give_gil(500) in eb                              # the payload is gil, not an item
    assert opcodes.window_sync(7, 0, chest_txids[0]) in eb
    assert eblint.errors(eblint.lint_eb(eb)) == _synth_baseline_errors(tmp_path)


def test_chest_received_box_matches_real_field_geometry():
    # byte-grounded on real fields 200/407: item txid 51 [STRT=69,3] WDTH=0,69,14,0,-1; gil txid 53 [STRT=86,3]
    # WDTH=0,86,64,0,-1; both TAIL=DEFT (the geometry auto-centers the system window). A `message` defaults to
    # the item geometry, overridable with box = [width, lines].
    from ff9mapkit.build import _chest_received_box
    it_text, it_strt, it_tail = _chest_received_box({"item": "Potion"})
    assert it_strt == (69, 3) and it_tail == "DEFT" and it_text.startswith("[WDTH=0,69,14,0,-1][IMME]")
    gi_text, gi_strt, gi_tail = _chest_received_box({"gil": 500})
    assert gi_strt == (86, 3) and gi_tail == "DEFT" and "[WDTH=0,86,64,0,-1]" in gi_text and "[NUMB=0] Gil" in gi_text
    m_text, m_strt, m_tail = _chest_received_box({"message": "[WDTH=0,40,14,0,-1][IMME]\n Hi \n", "box": [40, 3]})
    assert m_strt == (40, 3) and m_tail == "DEFT" and m_text.startswith("[WDTH=0,40,14")


def test_synth_chestless_field_has_no_chest(tmp_path):
    # the chest code path is inert when no [[chest]] -> no txid allocated, no chest opcodes leak in
    _mes, chest_txids, eb = _build_synth(tmp_path, '[[npc]]\nname = "V"\npos = [0, 0]\npreset = "vivi"\n')
    assert chest_txids == {}
    assert opcodes.encode(0x4B, 1, 40, 45) not in eb              # no chest collision box -> no chest injected


def test_synth_chest_validation(tmp_path):
    from ff9mapkit import build
    def _cp(body):                                  # the [[chest]]-specific problems only
        p = tmp_path / "z.field.toml"
        p.write_text(_CHEST_BASE + body, encoding="utf-8")
        return [s for s in build.validate(build.FieldProject.load(p)) if "[[chest]]" in s]
    assert any("exactly one" in s for s in _cp('[[chest]]\npos = [0, 0]\nflag = 8520\n'))                  # no payload
    assert any("exactly one" in s for s in _cp('[[chest]]\npos = [0, 0]\nitem = "Potion"\ngil = 5\nflag = 8520\n'))
    assert any("pos" in s for s in _cp('[[chest]]\nitem = "Potion"\nflag = 8520\n'))                       # no pos


def test_chest_requires_defined_safe_band_flag(tmp_path):
    # the opened-flag is REQUIRED (no positional auto bit) and must be in the safe band (not FF9's real chest
    # bitfield) -- resilient to reordering + a player's save. A named [[flag]] or a safe index both pass.
    from ff9mapkit import build
    def _cp(body):
        p = tmp_path / "z.field.toml"
        p.write_text(_CHEST_BASE + body, encoding="utf-8")
        return [s for s in build.validate(build.FieldProject.load(p)) if "[[chest]]" in s]
    base = '[[chest]]\npos = [0, 60]\nitem = ["Potion", 1]\n'
    assert any("needs a flag" in s for s in _cp(base))                     # no flag -> rejected
    assert any("safe" in s for s in _cp(base + "flag = 8400\n"))           # FF9 chest-bitfield index -> rejected
    assert not _cp(base + "flag = 8520\n")                                 # a safe-band index -> clean
    assert not _cp(base + 'flag = "t"\n\n[[flag]]\nname = "t"\nindex = 8520\n')   # a named [[flag]] -> clean


def test_synth_chest_flag_by_name_resolves(tmp_path):
    # a [[chest]] flag = "<name>" resolves to the [[flag]] index at load (the ergonomic, campaign-unique
    # choice); an unknown name raises at load (flags.resolve), never silently falling back.
    from ff9mapkit import build
    p = tmp_path / "z.field.toml"
    p.write_text(_CHEST_BASE + '[[chest]]\npos = [0, 60]\nitem = ["Potion", 1]\nflag = "treasure_a"\n\n'
                 '[[flag]]\nname = "treasure_a"\nindex = 8520\n', encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert proj.raw["chest"][0]["flag"] == 8520                            # named opened-flag resolved at load
    assert not [s for s in build.validate(proj) if "[[chest]]" in s]       # a named safe-band flag validates clean


def test_synth_gated_chest_has_appearance_gate(tmp_path):
    # requires_flag gates the chest's APPEARANCE (distinct from the opened-flag): its Init starts with a
    # flag_gate (early-return), so the chest is absent until that story flag is set -- a quest-reward chest.
    from ff9mapkit.content import region
    _mes, _txids, eb = _build_synth(tmp_path, '[[chest]]\npos = [0, 60]\nitem = ["Potion", 1]\n'
                                    'flag = 8520\nrequires_flag = 8521\n')
    assert region.flag_gate(region.GLOB_BOOL, 8521, require_set=True) in eb


def test_synth_chest_face_passes_through(tmp_path):
    # face rotates the chest model -- the Init's facing const carries the value (128 is distinctive; a
    # default face=0 chest wouldn't emit it).
    from ff9mapkit.content.npc import _d9_const
    _mes, _txids, eb128 = _build_synth(tmp_path, '[[chest]]\npos = [0, 60]\ngil = 100\nface = 128\nflag = 8520\n')
    _mes, _txids, eb0 = _build_synth(tmp_path, '[[chest]]\npos = [0, 60]\ngil = 100\nflag = 8520\n')
    assert _d9_const(6, 128) in eb128 and _d9_const(6, 128) not in eb0    # the facing value reaches the Init


def test_chest_variant_table_and_resolver():
    # the 4 TBX chest variants, decoded byte-for-byte from real fields (workflow-verified): F0/F2 share the 73xx
    # clips, F1/F3 share the low ids. resolve_chest_variant -> (model, neutral, open, closed, lid).
    import pytest as _pt
    from ff9mapkit.content import chest as C
    assert C.resolve_chest_variant() == (75, 7340, 7338, 7339, 7336)        # default = F0 (the proven wooden chest)
    assert C.resolve_chest_variant("F1") == (91, 4, 1, 3, 22)
    assert C.resolve_chest_variant("f2") == (701, 7340, 7338, 7339, 7336)   # case-insensitive; F2 shares F0's clips
    assert C.resolve_chest_variant(702) == (702, 4, 1, 3, 22)               # by raw id (F3)
    with _pt.raises(ValueError): C.resolve_chest_variant("F9")              # unknown variant name
    with _pt.raises(ValueError): C.resolve_chest_variant(999)               # an id with no known animations


def test_synth_chest_model_variant_uses_its_animations(tmp_path):
    # model = "F1" emits SetModel(91) + the F1 poses (neutral 4 / open 1 / closed 3) + lid 22 -- NOT F0's 73xx.
    from ff9mapkit.eb import EbScript
    _mes, _txids, eb = _build_synth(tmp_path,
        '[[chest]]\npos = [0, 60]\nitem = ["Potion", 1]\nflag = 8520\nmodel = "F1"\n')
    s = EbScript.from_bytes(eb)
    ent = next(e for e in s.entries if not e.empty and e.func_by_tag(0)
               and any(i.op == 0x2F and i.imm(0) == 91 for i in s.instrs(e.func_by_tag(0))))
    assert {i.imm(0) for i in s.instrs(ent.func_by_tag(0)) if i.op == 0x33} == {4, 1, 3}   # F1 poses, not F0's
    assert any(i.op == 0x40 and i.imm(0) == 22 for i in s.instrs(ent.func_by_tag(3))), "F1 lid animation"


def test_chest_unknown_model_rejected(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "z.field.toml"
    p.write_text(_CHEST_BASE + '[[chest]]\npos = [0, 0]\nitem = "Potion"\nflag = 8520\nmodel = "F9"\n', encoding="utf-8")
    assert any("[[chest]]" in s and "model" in s for s in build.validate(build.FieldProject.load(p)))
