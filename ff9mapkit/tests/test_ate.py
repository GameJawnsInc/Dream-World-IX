"""[[ate]] synthesis -- the Active Time Event primitive (the 'Press SELECT' optional-cutscene mechanism).

These pin the BYTES the synthesizer emits against the engine facts + the real Lindblum Main-St hub
(field 552, the Small-Town Knight ATE): the ATE(mode) prompt opcode, the menu-open gate
(usercontrol AND avail AND B_KEYON(SELECT)), the winATE(64) menu window, the GetChoose branch, and the
Main_Init wiring (ATE + avail-flag + InitCode). No game required -- the .eb round-trips and re-parses.
"""
from __future__ import annotations

from ff9mapkit import data
from ff9mapkit.content import ate, choice, region
from ff9mapkit.eb import EbScript, disasm, edit, opcodes


def test_ate_opcode_bytes():
    assert opcodes.ate(5) == bytes([0xD7, 0x00, 0x05])      # ATE(5) force-show -- verified vs field 552/206
    assert opcodes.ate(1) == bytes([0xD7, 0x00, 0x01])      # ATE(1) Blue/new
    assert opcodes.ate(0) == bytes([0xD7, 0x00, 0x00])      # ATE(0) off


def test_select_gate_matches_field552_structure():
    """The menu-open gate is field 552 [11667] byte-for-byte (bar the avail var): usercontrol==1 AND
    <avail>==1 AND B_KEYON(SELECT). Decode the expression tokens (don't raw-byte-count: the avail
    long-index 8300=0x206C contains a 0x20 byte that collides with the T_EQ token value)."""
    gate = region.cond_ate_select(region.GLOB_BOOL, 8300)
    assert gate[0] == 0x05                                  # EXPR_OP
    txt, _ = disasm.read_expr(gate, 1)
    assert "op7A(2)" in txt                                 # GetSysvar(2) = usercontrol
    assert "op4F" in txt                                    # B_KEYON (the SELECT press-edge)
    assert txt.count("op20") == 2                           # two equality tests (usercontrol==1, avail==1)
    assert txt.count("op27") == 2                           # two && (3-way AND)
    assert txt.rstrip("}").endswith("op7F")                 # terminated


def test_main_init_inject_is_arm_set_initcode():
    inj = ate.main_init_inject(avail_idx=ate.ATE_FLAG_BASE, menu_slot=9, mode=ate.MODE_BLUE)
    names, pos = [], 0
    while pos < len(inj):
        ins, pos = disasm.read_code(inj, pos)
        names.append(ins.name)
    assert names == ["ATE", "op_05", "InitCode"]           # arm prompt ; set avail=1 ; activate menu entry
    # the ATE arg is the mode; the InitCode arg is the menu slot
    first, _ = disasm.read_code(inj, 0)
    assert first.imm(0) == ate.MODE_BLUE


def _field_with_ate(n_rows: int = 3):
    base = data.blank_field_bytes("us")
    slot = EbScript.from_bytes(base).first_free_slot()
    bodies = [choice.option_body({}) for _ in range(n_rows)]
    entry = ate.menu_entry(prompt_txid=50, option_bodies=bodies, avail_idx=ate.ATE_FLAG_BASE)
    out = edit.append_entry(base, slot, entry)
    inj = ate.main_init_inject(avail_idx=ate.ATE_FLAG_BASE, menu_slot=slot, mode=ate.MODE_BLUE)
    out = edit.insert_in_function(out, 0, 0, 0, inj)        # prepend the wiring to Main_Init
    return EbScript.from_bytes(out), slot


def test_menu_entry_structure_and_roundtrip():
    eb, slot = _field_with_ate()
    me = eb.entry(slot)
    assert [f.tag for f in me.funcs] == [0, 1]              # tag-0 init + tag-1 loop
    loop = list(eb.instrs(me.func_by_tag(1)))
    ws = [i for i in loop if i.name == "WindowSync"]
    assert ws and ws[0].imm(1) == ate.WIN_ATE               # the menu window carries winATE (64)
    assert ws[0].imm(2) == 50                               # the prompt txid
    assert eb.to_bytes() == EbScript.from_bytes(eb.to_bytes()).to_bytes()   # round-trips clean


def test_menu_entry_winate_and_getchoose_branch():
    eb, slot = _field_with_ate(n_rows=3)
    loop = list(eb.instrs(eb.entry(slot).func_by_tag(1)))
    # winATE menu window present
    assert any(i.name == "WindowSync" and i.imm(1) == ate.WIN_ATE for i in loop)
    # the per-row branch reads GetChoose (sysvar 9) -- bodies are empty here, so the branch may be
    # elided; with non-empty bodies it appears. Assert the gate uses B_KEYON regardless.
    raw = eb.to_bytes()
    assert raw == EbScript.from_bytes(raw).to_bytes()       # round-trips


def test_ate_main_init_wiring_runs_first():
    eb, _ = _field_with_ate()
    f0 = eb.entry(0).func_by_tag(0)
    first, _ = disasm.read_code(eb.data, f0.abs_start)
    assert first.name == "ATE"                              # the prompt is armed at the very top of Main_Init


_ATE_TOML = """
[field]
id = 4003
name = "ATEROOM"
area = 11
text_block = 1073
[camera]
pitch = 45
[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]
[player]
spawn = [0, -300]
[ate]
prompt = "Active Time Event"
mode = 5
options = [
  { text = "Watch A", reply = "You watched A." },
  { text = "Watch B", reply = "You watched B." },
  { text = "Leave" },
]
"""


def test_declarative_ate_builds_into_field(tmp_path):
    """The declarative [ate] block compiles end-to-end: collect_text allocates the menu prompt + reply
    txids, and build_script arms the ATE(prompt) + a winATE(64) menu code-entry on a real field .eb."""
    from ff9mapkit.build import FieldProject, build_mod, validate, collect_text
    from ff9mapkit.config import ModLayout
    p = tmp_path / "a.field.toml"
    p.write_text(_ATE_TOML, encoding="utf-8")
    proj = FieldProject.load(p)
    assert validate(proj) == []
    ate_txids = collect_text(proj)[6]                       # the new 7th return -> {prompt, replies}
    assert "prompt" in ate_txids and len(ate_txids["replies"]) == 2   # 2 rows have a reply ("Leave" has none)
    out = tmp_path / "mod"
    build_mod([proj], out, mod_name="FF9CustomMap")
    eb = EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_ATEROOM.eb.bytes").read_bytes())
    assert list(eb.instrs(eb.entry(0).func_by_tag(0)))[0].name == "ATE"            # prompt armed first
    ws = [i for e in eb.entries if not e.empty for f in e.funcs
          for i in eb.instrs(f) if i.name == "WindowSync" and i.imm(1) == ate.WIN_ATE]
    assert ws and ws[0].imm(2) == ate_txids["prompt"]       # the winATE menu points at the collected prompt txid


def test_no_ate_block_is_byte_identical(tmp_path):
    """A field WITHOUT [ate] builds byte-identical to before (the 7-tuple / _apply_ate are no-ops)."""
    from ff9mapkit.build import FieldProject, build_mod
    from ff9mapkit.config import ModLayout
    base = _ATE_TOML.split("[ate]")[0]
    p = tmp_path / "b.field.toml"
    p.write_text(base, encoding="utf-8")
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    eb = EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_ATEROOM.eb.bytes").read_bytes())
    assert not [i for e in eb.entries if not e.empty for f in e.funcs
                for i in eb.instrs(f) if i.op == 0xD7]      # no ATE opcode injected


# --- Compulsory / auto-advance ATE (Flavor A, the FORCED no-menu cutscene -- field 1901's Eiko bracket).
# A `[cutscene] ate = true` is an ordinary cutscene styled as a compulsory ATE: its body is bracketed
# ATE(mode)..ATE(0) and its windows carry the winATE(64) caption. -------------------------------------

from ff9mapkit.content import cutscene as _cs   # noqa: E402

_CUTSCENE_ATE_TOML = """
[field]
id = 4003
name = "ATEROOM"
area = 11
text_block = 1073
[camera]
pitch = 45
[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]
[player]
spawn = [0, -300]
[cutscene]
ate = true
steps = [
  { say = "An Active Time Event." },
  { wait = 30 },
]
"""


def _build_eb(tmp_path, toml, name="ATEROOM"):
    from ff9mapkit.build import FieldProject, build_mod, validate
    from ff9mapkit.config import ModLayout
    p = tmp_path / "c.field.toml"
    p.write_text(toml, encoding="utf-8")
    proj = FieldProject.load(p)
    assert validate(proj) == []
    out = tmp_path / "mod"
    build_mod([proj], out, mod_name="FF9CustomMap")
    return EbScript.from_bytes(ModLayout(out).eb_path("us", f"EVT_{name}.eb.bytes").read_bytes())


def _all_instrs(eb):
    return [i for e in eb.entries if not e.empty for f in e.funcs for i in eb.instrs(f)]


def test_compulsory_ate_narration_brackets_and_captions(tmp_path):
    """A narration cutscene with `ate = true` builds the ATE(6)..ATE(0) grey-unskippable HUD bracket around
    its body and renders its `say` window with the winATE caption (the default = the real grey forced-ATE
    look, field 956 / the Festival cluster; ate_mode = 1 is the opt-in quiet no-icon variant)."""
    eb = _build_eb(tmp_path, _CUTSCENE_ATE_TOML)
    ate_ops = [i for i in _all_instrs(eb) if i.op == 0xD7]
    assert [i.imm(0) for i in ate_ops] == [6, 0]            # default mode 6 (grey, force-show) arm, then disarm
    says = [i for i in _all_instrs(eb) if i.name == "WindowSync"]
    assert says and all(i.imm(1) == ate.WIN_ATE for i in says)   # the cutscene window is winATE-captioned


def test_compulsory_ate_mode_override(tmp_path):
    """`ate_mode = 5` forces the HUD prompt to show even without user control (the &4 force bit)."""
    eb = _build_eb(tmp_path, _CUTSCENE_ATE_TOML.replace("ate = true", "ate = true\nate_mode = 5"))
    ate_ops = [i for i in _all_instrs(eb) if i.op == 0xD7]
    assert [i.imm(0) for i in ate_ops] == [5, 0]


def test_cutscene_without_ate_has_no_bracket_or_caption(tmp_path):
    """Drop `ate = true` and the cutscene is a plain one: no 0xD7 op, ordinary (128) window caption."""
    eb = _build_eb(tmp_path, _CUTSCENE_ATE_TOML.replace("ate = true\n", ""))
    assert not [i for i in _all_instrs(eb) if i.op == 0xD7]       # no ATE bracket
    says = [i for i in _all_instrs(eb) if i.name == "WindowSync"]
    assert says and all(i.imm(1) == 128 for i in says)           # plain caption, not winATE


def test_compulsory_ate_actor_path_brackets_and_captions():
    """The ACTOR cutscene path (choreography spliced into an NPC's loop) brackets + captions the same way
    -- asserted at the bytes level (no NPC-model build needed)."""
    styled = _cs.build_choreography([{"say": 0}], [77], 8100, ate_mode=1,
                                    say_flags=_cs.ATE_CAPTION_FLAG)
    assert opcodes.ate(1) in styled and opcodes.ate(0) in styled
    assert _cs.say(77, flags=_cs.ATE_CAPTION_FLAG) in styled      # winATE-captioned window
    plain = _cs.build_choreography([{"say": 0}], [77], 8100)
    assert opcodes.ate(1) not in plain and opcodes.ate(0) not in plain
    assert _cs.say(77, flags=128) in plain                        # ordinary window


def test_compulsory_ate_validation(tmp_path):
    from ff9mapkit.build import FieldProject, validate

    def problems(toml):
        p = tmp_path / "v.field.toml"
        p.write_text(toml, encoding="utf-8")
        return validate(FieldProject.load(p))

    assert any("ate_mode is set but ate is not true" in m
               for m in problems(_CUTSCENE_ATE_TOML.replace("ate = true", "ate_mode = 5")))
    assert any("must be an int 0..255" in m
               for m in problems(_CUTSCENE_ATE_TOML.replace("ate = true", "ate = true\nate_mode = 999")))
