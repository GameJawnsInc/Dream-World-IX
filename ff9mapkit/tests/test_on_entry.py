"""[[on_entry]] -- gated, once field-load beats (FORK_FIDELITY.md #10).

A real field's entry cutscene fires from the engine's C# NarrowMapList table, not the .eb, so a fork
loses it. [[on_entry]] is the declarative re-authoring hook: fire a narration message and/or story-state
writes the moment the player ENTERS, once, but ONLY when requires_flag / requires_scenario match -- the
gating neither [startup] (unconditional) nor [cutscene] (ungated) can express. These tests pin the
injected bytes (gates, once-block, the message lock), name/area resolution, validation, the reserved-band
lint, the flag-setter accounting, and byte-identity when the block is absent.
"""
from __future__ import annotations

from ff9mapkit.build import (FieldProject, build_mod, validate, lint_flag_bands, lint_logic,
                             build_script, collect_text)
from ff9mapkit.config import ModLayout
from ff9mapkit.content import region, onentry, startup
from ff9mapkit.eb import EbScript

BASE = """
[field]
id = 4003
name = "ENTRYROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""


def _build_eb(tmp_path, toml: str) -> EbScript:
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    return EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_ENTRYROOM.eb.bytes").read_bytes())


def _eb_parses(eb: EbScript) -> bool:
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            list(eb.instrs(f))          # raises on a corrupt func boundary
    return True


# --------------------------------------------------------------- body builder (pure) ---

def test_on_entry_body_state_only_has_no_movement_gate():
    # a state-only beat: set scenario + a flag, gated once. NO MOVEMENT_GATE (it runs before usercontrol).
    body = onentry.on_entry_body(scenario=2700, set_flag_pairs=[(8520, 1)], once_flag=8300)
    assert region.MOVEMENT_GATE not in body
    assert region.set_var(region.GLOB_UINT16, 0, 2700) in body
    assert region.set_var(region.GLOB_BOOL, 8520, 1) in body
    assert region.set_var(region.GLOB_BOOL, 8300, 1) in body          # the once-flag is set
    # once-gate: if (!8300) { 8300 = 1; ... }
    assert region.cond_not(region.GLOB_BOOL, 8300) in body


def test_on_entry_body_message_uses_control_lock():
    from ff9mapkit.eb import opcodes
    from ff9mapkit.content import cutscene
    body = onentry.on_entry_body(message_txid=540, once_flag=8300)
    assert opcodes.DISABLE_MOVE in body and opcodes.ENABLE_MOVE in body
    assert opcodes.window_sync(1, 128, 540) in body
    # the lock-stick reorder Wait precedes DisableMove (so the lock outlives Main_Init's EnableMove)
    assert body.index(opcodes.wait(cutscene.REORDER_WAIT)) < body.index(opcodes.DISABLE_MOVE)


def test_on_entry_body_gate_precedes_once_block():
    body = onentry.on_entry_body(set_flag_pairs=[(8520, 1)], once_flag=8300, requires_scenario=2700)
    gate = onentry.scenario_gate(2700)
    assert gate in body
    assert body.index(gate) < body.index(region.cond_not(region.GLOB_BOOL, 8300))   # gate OUTSIDE once
    # a requires_flag gate is a flag_gate prologue
    body2 = onentry.on_entry_body(set_flag_pairs=[(8520, 1)], once_flag=8300, requires_flag=8513)
    assert region.flag_gate(region.GLOB_BOOL, 8513, require_set=True) in body2


def test_on_entry_no_once_flag_omits_once_block():
    body = onentry.on_entry_body(set_flag_pairs=[(8520, 1)], once_flag=None)
    assert region.cond_not(region.GLOB_BOOL, 8520) not in body        # no if(!once) wrapper
    assert region.set_var(region.GLOB_BOOL, 8520, 1) in body


# --------------------------------------------------------------- end-to-end build ---

ONE = BASE + '\n[[on_entry]]\nmessage = "The town lies in ruins."\nset_scenario = 2700\n'


def test_build_injects_armed_on_entry(tmp_path):
    eb = _build_eb(tmp_path, ONE)
    # the scenario write + the message landed in the eb, and it still fully parses
    assert region.set_var(region.GLOB_UINT16, 0, 2700) in eb.data
    assert _eb_parses(eb)
    # Main_Init runs an InitCode that schedules the hook entry (armed on load)
    main_init = eb.entry(0).func_by_tag(0)
    assert any(ins.name == "InitCode" for ins in eb.instrs(main_init))


def test_absent_on_entry_adds_exactly_one_entry(tmp_path):
    """The injection is strictly guarded by the block's presence (no [[on_entry]] -> no change), and one
    hook adds exactly one code entry. (Whole-field byte-identity for non-on_entry fields is covered by the
    existing goldens; here we pin the per-hook delta on the same build_script path.)"""
    p1 = tmp_path / "a.field.toml"; p1.write_text(BASE, encoding="utf-8")
    eb_plain = EbScript.from_bytes(build_script(FieldProject.load(p1), "us", {}))
    p2 = tmp_path / "b.field.toml"; p2.write_text(ONE, encoding="utf-8")
    proj2 = FieldProject.load(p2)
    _b, _n, _e, _c, _ch, oe = collect_text(proj2)
    eb_hooked = EbScript.from_bytes(build_script(proj2, "us", {}, on_entry_txids=oe))
    n_plain = sum(1 for e in eb_plain.entries if not e.empty)
    n_hooked = sum(1 for e in eb_hooked.entries if not e.empty)
    assert n_hooked == n_plain + 1          # exactly one new code entry for the single hook
    assert _eb_parses(eb_hooked)


def test_on_entry_message_text_shares_the_mes_block(tmp_path):
    p = tmp_path / "f.field.toml"; p.write_text(ONE, encoding="utf-8")
    body, _n, _e, _c, _ch, oe = collect_text(FieldProject.load(p))
    assert "The town lies in ruins." in body
    assert oe == {0: 500}                                  # first (only) line -> base txid


def test_on_entry_scenario_and_flags_by_name(tmp_path):
    toml = (BASE + '\n[[flag]]\nname = "saw_intro"\nindex = 8520\n'
            + '\n[[on_entry]]\nset_scenario = "Dali (underground)"\n'
            + 'set_flags = [{flag = "saw_intro", value = 1}]\nrequires_scenario = "Dali (underground)"\n')
    eb = _build_eb(tmp_path, toml)
    assert region.set_var(region.GLOB_UINT16, 0, 2700) in eb.data      # area name -> scenario
    assert region.set_var(region.GLOB_BOOL, 8520, 1) in eb.data        # flag name -> index


def test_on_entry_shared_flag_name_resolves_at_load(tmp_path):
    """A campaign-shared flag name (not in the member's own [[flag]] table) must resolve in set_flags AND
    requires_flag -- read/write parity, same as gateway/startup."""
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + '\n[[on_entry]]\nrequires_flag = "rescued"\nset_flags = [{flag = "rescued", value = 1}]\n',
                 encoding="utf-8")
    proj = FieldProject.load(p, flag_names={"rescued": 8700})
    assert validate(proj) == []
    assert proj.raw["on_entry"][0]["requires_flag"] == 8700
    assert proj.raw["on_entry"][0]["set_flags"][0]["flag"] == 8700


# --------------------------------------------------------------- validation ---

def _problems(tmp_path, toml: str):
    p = tmp_path / "f.field.toml"; p.write_text(toml, encoding="utf-8")
    return validate(FieldProject.load(p))


def test_on_entry_validate_catches_bad_shapes(tmp_path):
    assert any("[[on_entry]] #0 does nothing" in m for m in
               _problems(tmp_path, BASE + "\n[[on_entry]]\nonce = true\n"))
    assert any("[[on_entry]] #0 set_scenario must be" in m for m in
               _problems(tmp_path, BASE + "\n[[on_entry]]\nset_scenario = 40000\n"))
    assert any("[[on_entry]] #0 requires_scenario must be" in m for m in
               _problems(tmp_path, BASE + "\n[[on_entry]]\nmessage = \"x\"\nrequires_scenario = 99999\n"))
    assert any("value must be 0 or 1" in m for m in
               _problems(tmp_path, BASE + "\n[[on_entry]]\nset_flags = [{flag = 8520, value = 2}]\n"))


def test_on_entry_unknown_flag_name_raises_at_load(tmp_path):
    # an unknown requires_flag / set_flags name is rejected at load (resolve_project_flags), like every
    # other section -- read/write parity with the rest of the kit.
    import pytest
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + "\n[[on_entry]]\nmessage = \"x\"\nrequires_flag = \"nope\"\n", encoding="utf-8")
    with pytest.raises(ValueError):
        FieldProject.load(p)


# --------------------------------------------------------------- lint ---

def test_on_entry_set_flags_in_reserved_band_warns(tmp_path):
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + "\n[[on_entry]]\nset_flags = [{flag = 8400, value = 1}]\n", encoding="utf-8")
    w = lint_flag_bands(FieldProject.load(p))
    assert any("8400" in m and "on_entry" in m for m in w)
    # a real story bit (non-reserved) is the point -> no warning
    p.write_text(BASE + "\n[[on_entry]]\nset_flags = [{flag = 2600, value = 1}]\n", encoding="utf-8")
    assert lint_flag_bands(FieldProject.load(p)) == []


def test_on_entry_set_flags_counts_as_a_setter(tmp_path):
    """An on_entry beat that sets a flag a later NPC gates on must NOT lint-warn 'no event sets it'."""
    toml = (BASE + "\n[[on_entry]]\nset_flags = [{flag = 8800, value = 1}]\n"
            + '\n[[npc]]\nname = "Revealed"\narchetype = "moogle"\npos = [0, -300]\n'
            + 'requires_flag = 8800\ndialogue = "The way is open."\n')
    p = tmp_path / "f.field.toml"; p.write_text(toml, encoding="utf-8")
    warns = lint_logic(FieldProject.load(p))
    assert not any("8800" in w and "no event sets it" in w for w in warns)


def test_campaign_member_on_entry_needs_explicit_flag(tmp_path):
    """A campaign member's flag block is fully reserved -> an auto once-flag would alias a sibling, so a
    once on_entry hook there must carry an explicit flag = N (build raises a clear error otherwise)."""
    import pytest
    from ff9mapkit.build import BuildError
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + '\n[[on_entry]]\nmessage = "hi"\n', encoding="utf-8")
    proj = FieldProject.load(p)
    proj.flag_base = 9000                              # mimic a campaign member with a per-member block
    with pytest.raises(BuildError):
        build_script(proj, "us", {}, on_entry_txids={0: 500})


def test_on_entry_auto_flag_overflow_into_chest_band_is_blocked(tmp_path):
    """The single-field auto once-flag band is 8300+k; at k=76 it would reach FF9's reserved chest bitfield
    (8376+) -> save corruption. The build must REFUSE rather than silently corrupt (the band is unguarded by
    lint_flag_bands, which only checks explicit indices). 77 once-hooks with no explicit flag -> BuildError."""
    import pytest
    from ff9mapkit.build import BuildError
    from ff9mapkit.content import onentry
    from ff9mapkit import flags
    assert onentry.ONENTRY_FLAG_BASE + 76 == flags.CHEST_FLAG_LO          # the exact overflow point
    hooks = "".join('\n[[on_entry]]\nset_flags = [{flag = 2600, value = 1}]\n' for _ in range(77))
    p = tmp_path / "f.field.toml"; p.write_text(BASE + hooks, encoding="utf-8")
    proj = FieldProject.load(p)
    assert validate(proj) == []                                          # individually all valid
    with pytest.raises(BuildError):
        build_script(proj, "us", {})
    # 76 hooks (k max = 75 -> 8375, still below the chest band) builds fine
    p.write_text(BASE + "".join('\n[[on_entry]]\nset_flags = [{flag = 2600, value = 1}]\n' for _ in range(76)),
                 encoding="utf-8")
    build_script(FieldProject.load(p), "us", {})                         # no raise


def test_on_entry_in_verbatim_fork_has_no_lint_warning(tmp_path):
    """message-in-verbatim landed: a --verbatim fork now fires BOTH the gated state-advance AND the narration
    message (the message is appended to the donor .mes above its txids), so lint_logic no longer warns about
    [[on_entry]] in a verbatim fork -- neither a message hook nor a state-only one."""
    for hook in ('\n[[on_entry]]\nmessage = "hi"\n',
                 '\n[[on_entry]]\nset_scenario = 2700\nset_flags = [{flag = 8800, value = 1}]\n'):
        p = tmp_path / "f.field.toml"
        p.write_text(BASE + '\n[verbatim_eb]\nbin = "donor.eb.bin"\n' + hook, encoding="utf-8")
        assert not any("verbatim" in w.lower() for w in lint_logic(FieldProject.load(p)))


def _verbatim_fork(tmp_path, donor_us_mes: str, hooks: str):
    """A minimal verbatim-fork project: a [verbatim_eb] block with a donor .mes text sidecar + on_entry
    hooks. The .eb bin isn't read by _verbatim_on_entry_messages (only the text sidecar is)."""
    import json
    (tmp_path / "donor_text.json").write_text(json.dumps({"us": donor_us_mes}), encoding="utf-8")
    (tmp_path / "donor.eb.bin").write_bytes(b"\x00")
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + '\n[verbatim_eb]\nbin = "donor.eb.bin"\ntext = "donor_text.json"\n' + hooks,
                 encoding="utf-8")
    return FieldProject.load(p)


def test_verbatim_on_entry_message_appends_above_donor_txids(tmp_path):
    """A verbatim fork's [[on_entry]] narration message is APPENDED to the donor .mes above its txids (so it
    can't collide) and the hook gets that txid -> the message SHOWS, not dropped. A state-only hook gets no
    message txid. Floor is CARRY_BASE_TXID (1000); a donor reaching it pushes the base higher."""
    from ff9mapkit.build import _verbatim_on_entry_messages
    proj = _verbatim_fork(
        tmp_path, "_[TXID=12][STRT=10,1][TAIL=UPR]donor line[ENDN]\n",
        '\n[[on_entry]]\nmessage = "A real entry line."\nset_flags = [{flag = 8800, value = 1}]\n'
        '\n[[on_entry]]\nset_scenario = 2700\n')            # 2nd hook is state-only -> no message
    txids, suffix = _verbatim_on_entry_messages(proj, ["us"])
    assert txids == {0: 1000}                                # only the message hook; floored at 1000 (> donor 12)
    assert 1 not in txids                                    # the state-only hook gets no message txid
    assert "[TXID=1000]" in suffix["us"] and "A real entry line." in suffix["us"]
    assert "donor line" not in suffix["us"]                  # the donor's verbatim text is untouched (appended-to)

    # no message hooks at all -> nothing to append (state-only verbatim fork stays unchanged)
    proj2 = _verbatim_fork(tmp_path, "_[TXID=12][STRT=10,1][TAIL=UPR]x[ENDN]\n",
                           '\n[[on_entry]]\nset_scenario = 2700\n')
    assert _verbatim_on_entry_messages(proj2, ["us"]) == ({}, {})

    # a donor whose text reaches the safe floor pushes the base up (no collision with donor txids)
    proj3 = _verbatim_fork(tmp_path, "_[TXID=1500][STRT=10,1][TAIL=UPR]x[ENDN]\n",
                           '\n[[on_entry]]\nmessage = "hi"\n')
    txids3, _ = _verbatim_on_entry_messages(proj3, ["us"])
    assert txids3 == {0: 1501}
