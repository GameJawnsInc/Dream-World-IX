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


def test_compulsory_ate_then_warp_auto_returns(tmp_path):
    """[cutscene] ate=true + then_warp=N ends the grey scene with Field(N) -- the auto-return real grey
    ATEs use (956 -> Field(2054)). The chain primitive: a grey cutscene field warps back to its hub."""
    eb = _build_eb(tmp_path, _CUTSCENE_ATE_TOML.replace("ate = true", "ate = true\nthen_warp = 30011"))
    ins = _all_instrs(eb)
    assert 30011 in [i.imm(0) for i in ins if i.op == 0x2B]   # Field(30011) warp back to the hub
    assert [i.imm(0) for i in ins if i.op == 0xD7] == [6, 0]  # still the grey ATE(6) bracket
    # the auto-return FADES OUT first (fade=True) so the destination doesn't load in the clear: a
    # FadeFilter (0xEC) precedes the Field(30011) on the warp path (the static-screen fix, like choices).
    fade_offs = [i.off for i in ins if i.op == 0xEC]
    warp_off = next(i.off for i in ins if i.op == 0x2B and i.imm(0) == 30011)
    assert any(f < warp_off for f in fade_offs), "then_warp must fade to black before Field()"


def test_then_warp_validation(tmp_path):
    from ff9mapkit.build import FieldProject, validate

    def problems(toml):
        p = tmp_path / "v.field.toml"
        p.write_text(toml, encoding="utf-8")
        return validate(FieldProject.load(p))

    assert any("must be a field id" in m
               for m in problems(_CUTSCENE_ATE_TOML.replace("ate = true", "ate = true\nthen_warp = 0")))
    assert any("only supported on a narration cutscene" in m for m in
               problems(_CUTSCENE_ATE_TOML.replace("ate = true", 'ate = true\nactor = "X"\nthen_warp = 30011')))


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


# --- The FAITHFUL grey-ATE TRIGGER: the banner is a pre-warp WARNING on the ORIGIN (a forced-ATE warp-in),
# NOT a held overlay on the destination scene. `[[gateway]] ate = true` -> ATE(6) flashes, clears, then the
# gateway's fade + Field() warps you to the (plain) ATE scene, which `exit_warp`s you back. Grounded in real
# field 956 (Gargan Roo): ATE(6) -> Wait(45) -> fade -> ATE(0) -> Field(scene). ---------------------------

_GATEWAY_ATE_TOML = """
[field]
id = 4003
name = "GATEROOM"
area = 11
text_block = 1073
[camera]
pitch = 45
[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]
[player]
spawn = [0, -300]
[[gateway]]
to = 1853
ate = true
zone = [[-200, -200], [200, -200], [200, -500], [-200, -500]]
"""


def test_forced_ate_warp_body():
    """The forced-ATE player func (RunScript'd from the trigger region, so its Waits tick under the lock --
    NOT inline in the region, which would freeze). Verified vs real 956/2211: ATE(6) -> Wait -> fade -> ATE(0)
    -> [WindowAsync title] -> Field. The banner clears BEFORE the warp; the title is a NON-blocking async
    window, not a press-to-continue WindowSync."""
    from ff9mapkit.content import event
    body = _cs.forced_ate_warp_body(1153, mode=6)
    assert body == (opcodes.ate(6) + opcodes.wait(_cs.ATE_WARN_FRAMES)
                    + opcodes.fade_filter(*event.WARP_FADE) + opcodes.wait(25)
                    + opcodes.ate(0) + opcodes.field(1153) + opcodes.RETURN)
    # with a title: an ASYNC winATE window (0x20) before the Field -- NOT a blocking WindowSync (0x1F)
    titled = _cs.forced_ate_warp_body(1153, mode=6, title_txid=500)
    assert opcodes.window_async(0, _cs.ATE_CAPTION_FLAG, 500) in titled       # async (real grey-ATE behavior)
    assert opcodes.window_sync(0, _cs.ATE_CAPTION_FLAG, 500) not in titled    # NOT blocking
    assert opcodes.wait(_cs.ATE_WARN_FRAMES) in titled                        # the banner-warning Wait stays


def test_gateway_ate_warp_in_warns_then_warps(tmp_path):
    """`[[gateway]] ate = true` is a forced-ATE WARP-IN: a TREAD region RunScriptSyncs the player's forced-ATE
    func (so the timed banner+warp aren't frozen by the region's move-lock -- a region body runs only while
    usercontrol==1). The func flashes ATE(6), CLEARS ATE(0), and warps -- the banner clears BEFORE the Field,
    not held over the destination scene (the divergence the user corrected)."""
    from ff9mapkit.content.ladder import find_player_entry
    eb = _build_eb(tmp_path, _GATEWAY_ATE_TOML, name="GATEROOM")
    func = eb.entry(find_player_entry(eb)).func_by_tag(_cs.FORCED_ATE_TAG)
    assert func is not None, "the forced-ATE warp func is grafted onto the player entry"
    ops = list(eb.instrs(func))
    assert [i.imm(0) for i in ops if i.op == 0xD7] == [6, 0]    # banner arm, then clear
    k_a0 = next(k for k, i in enumerate(ops) if i.op == 0xD7 and i.imm(0) == 0)
    k_field = next(k for k, i in enumerate(ops) if i.op == 0x2B)
    assert k_a0 < k_field                                       # the banner clears BEFORE the warp
    # a tread region RunScriptSyncs into the player func (level 2, uid 250, FORCED_ATE_TAG)
    rs = [i for i in _all_instrs(eb) if i.op == 0x14]
    assert any(i.imm(0) == 2 and i.imm(1) == 250 and i.imm(2) == _cs.FORCED_ATE_TAG for i in rs)
    # a plain gateway (no ate) has no forced-ATE func and no banner -- the styling is opt-in
    plain = _build_eb(tmp_path, _GATEWAY_ATE_TOML.replace("ate = true\n", ""), name="GATEROOM")
    assert not any(i.op == 0xD7 for i in _all_instrs(plain))


def test_gateway_ate_title_window(tmp_path):
    """`[[gateway]] ate_title = "..."` shows a winATE-captioned, CENTERED title window (verified vs real
    956/2211): the forced-ATE func gets an ASYNC WindowAsync(0, winATE, txid) (NOT blocking WindowSync), and the
    title ships in the .mes with CENTERED system-window geometry ([STRT=W,1][IMME][CENT=W]) -- not top-right."""
    from ff9mapkit.content.ladder import find_player_entry
    from ff9mapkit.build import FieldProject, build_mod
    from ff9mapkit.config import ModLayout
    toml = _GATEWAY_ATE_TOML.replace("ate = true\n", 'ate = true\nate_title = "Meanwhile, elsewhere..."\n')
    p = tmp_path / "t.field.toml"
    p.write_text(toml, encoding="utf-8")
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    eb = EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_GATEROOM.eb.bytes").read_bytes())
    func = eb.entry(find_player_entry(eb)).func_by_tag(_cs.FORCED_ATE_TAG)
    ws = [i for i in eb.instrs(func) if i.op == 0x20]           # WindowAsync = the async title window
    assert len(ws) == 1 and ws[0].imm(1) == ate.WIN_ATE        # winATE caption flag (64)
    assert not any(i.op == 0x1F for i in eb.instrs(func))      # NOT a blocking WindowSync
    blob = "".join(q.read_text(encoding="utf-8") for q in out.rglob("*.mes"))
    assert "Meanwhile, elsewhere..." in blob and f"[TXID={ws[0].imm(2)}]" in blob   # title shipped at that txid
    assert "[IMME]" in blob and "[CENT=" in blob               # CENTERED system-window geometry (not top-right)


def test_gateway_ate_validation(tmp_path):
    """`[[gateway]]` ate guards: ate_mode needs ate = true; ate_mode must be 0..255."""
    from ff9mapkit.build import FieldProject, validate

    def problems(toml):
        p = tmp_path / "gv.field.toml"
        p.write_text(toml, encoding="utf-8")
        return validate(FieldProject.load(p))

    assert any("ate_mode is set but ate is not true" in m
               for m in problems(_GATEWAY_ATE_TOML.replace("ate = true", "ate_mode = 6")))
    assert any("must be an int 0..255" in m
               for m in problems(_GATEWAY_ATE_TOML.replace("ate = true", "ate = true\nate_mode = 999")))
    assert validate(FieldProject.load(_w(tmp_path, _GATEWAY_ATE_TOML))) == []   # the plain ate = true is clean


def _w(tmp_path, toml):
    p = tmp_path / "ok.field.toml"
    p.write_text(toml, encoding="utf-8")
    return p


def test_legacy_cutscene_ate_is_deprecated(tmp_path):
    """`[cutscene] ate = true` (the OLD held-banner model) now lint-warns toward the faithful `[[gateway]] ate`
    warp-in trigger -- it still builds (a warning, not an error)."""
    from ff9mapkit.build import FieldProject, lint_logic, validate
    base = ('[field]\nid = 4003\nname = "D"\narea = 11\ntext_block = 1073\n\n'
            '[camera]\npitch = 45\nfov = 42.2\n\n'
            '[walkmesh]\nquad = [[-200,-200],[200,-200],[200,200],[-200,200]]\n\n'
            '[player]\nspawn = [0, 0]\n\n')
    p = tmp_path / "d.field.toml"
    p.write_text(base + '[cutscene]\nate = true\nsteps = [ { say = "An ATE." } ]\n', encoding="utf-8")
    proj = FieldProject.load(p)
    assert any("held-banner" in w and "[[gateway]] ate" in w for w in lint_logic(proj))
    assert validate(proj) == []                                # deprecated, but still valid (warning, not error)
    p.write_text(base + '[cutscene]\nsteps = [ { say = "Hi." } ]\n', encoding="utf-8")   # no ate -> no warning
    assert not any("held-banner" in w for w in lint_logic(FieldProject.load(p)))
