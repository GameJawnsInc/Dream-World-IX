"""[[gateway]] on-exit story advance -- set_scenario / set_flags.

A forked field chain needs to PROGRESS the story as the player leaves a screen: taking an exit can
advance the ScenarioCounter and/or set story bits so the NEXT field boots at the right beat (the write-
side complement to [startup]'s entry-side assert + the import's story-branch door gating). These tests
pin the injected set_var bytes in the gateway's Range trigger, the usercontrol guard + flag-gate ordering,
name/area resolution, validation, the reserved-band lint, and byte-identity when the keys are absent.
"""
from __future__ import annotations

from ff9mapkit.build import FieldProject, build_mod, validate, lint_flag_bands
from ff9mapkit.config import ModLayout
from ff9mapkit.content import region
from ff9mapkit.eb import EbScript

BASE = """
[field]
id = 4003
name = "EXITROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""

_GW = """
[[gateway]]
to = 30005
entrance = 0
zone = [[-200, -100], [200, -100], [200, -400], [-200, -400]]
"""

GW_PLAIN = BASE + _GW
GW_ADVANCE = BASE + _GW + "set_scenario = 2700\nset_flags = [{flag = 8520, value = 1}, {flag = 8521, value = 0}]\n"
GW_GATED = BASE + _GW + "requires_flag = 8512\nset_scenario = 2700\n"


def _build_eb(tmp_path, toml: str) -> EbScript:
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    return EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_EXITROOM.eb.bytes").read_bytes())


def _range_with(eb: EbScript, needle: bytes) -> bytes | None:
    """The tag-2 (Range) func bytes of the region entry whose trigger carries ``needle`` (the gateway)."""
    for e in eb.entries:
        if e.empty:
            continue
        f = e.func_by_tag(region.RANGE_TAG)
        if f is not None:
            b = eb.data[f.abs_start:f.abs_end]
            if needle in b:
                return b
    return None


def test_gateway_advance_emits_writes(tmp_path):
    eb = _build_eb(tmp_path, GW_ADVANCE)
    assert region.set_var(region.GLOB_UINT16, 0, 2700) in eb.data    # ScenarioCounter advance
    assert region.set_var(region.GLOB_BOOL, 8520, 1) in eb.data      # a story bit set on exit
    assert region.set_var(region.GLOB_BOOL, 8521, 0) in eb.data      # a story bit cleared on exit


def test_gateway_plain_has_no_writes(tmp_path):
    eb = _build_eb(tmp_path, GW_PLAIN)
    assert region.set_var(region.GLOB_UINT16, 0, 2700) not in eb.data
    assert bytes([0x05, region.GLOB_UINT16, 0x00]) not in eb.data    # no scenario-write opcode at all


def test_gateway_advance_guarded_by_usercontrol(tmp_path):
    """The writes sit behind a usercontrol guard so they fire on an actual walk-out, not a puppet pass."""
    eb = _build_eb(tmp_path, GW_ADVANCE)
    rng = _range_with(eb, region.set_var(region.GLOB_UINT16, 0, 2700))
    assert rng is not None
    assert rng.index(region.MOVEMENT_GATE) < rng.index(region.set_var(region.GLOB_UINT16, 0, 2700))


def test_gateway_advance_after_flag_gate(tmp_path):
    """A gated exit advances the story ONLY when the gate passes -> the flag gate precedes the writes."""
    eb = _build_eb(tmp_path, GW_GATED)
    rng = _range_with(eb, region.set_var(region.GLOB_UINT16, 0, 2700))
    assert rng is not None
    gate = region.flag_gate(region.GLOB_BOOL, 8512, require_set=True)
    assert rng.index(gate) < rng.index(region.MOVEMENT_GATE)         # gate first
    assert rng.index(region.MOVEMENT_GATE) < rng.index(region.set_var(region.GLOB_UINT16, 0, 2700))


def test_gateway_advance_scenario_by_name(tmp_path):
    toml = BASE + _GW + 'set_scenario = "Dali (underground)"\n'      # resolves to 2700
    eb = _build_eb(tmp_path, toml)
    assert region.set_var(region.GLOB_UINT16, 0, 2700) in eb.data


def test_gateway_advance_flag_by_name(tmp_path):
    toml = (BASE + '\n[[flag]]\nname = "left_room"\nindex = 8520\n' + _GW
            + 'set_flags = [{flag = "left_room", value = 1}]\n')
    eb = _build_eb(tmp_path, toml)
    assert region.set_var(region.GLOB_BOOL, 8520, 1) in eb.data


def test_gateway_advance_shared_flag_name_resolves_at_load(tmp_path):
    """A CAMPAIGN-shared flag name (not in the member's own [[flag]] table) in set_flags must resolve via
    the campaign name map at load — read/write parity with requires_flag, which already does. (Regression:
    set_flags name resolution previously saw only the member's own table, so a shared name failed to build.)"""
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + _GW + 'set_flags = [{flag = "rescued_dagger", value = 1}]\n', encoding="utf-8")
    proj = FieldProject.load(p, flag_names={"rescued_dagger": 8700})   # mimic build_campaign's shared map
    assert validate(proj) == []
    assert proj.raw["gateway"][0]["set_flags"][0]["flag"] == 8700      # resolved at load, not member-only
    out = tmp_path / "mod"
    build_mod([proj], out, mod_name="FF9CustomMap")
    eb = EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_EXITROOM.eb.bytes").read_bytes())
    assert region.set_var(region.GLOB_BOOL, 8700, 1) in eb.data        # emitted at the shared index


def _problems(tmp_path, toml: str):
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    return validate(FieldProject.load(p))


def test_gateway_advance_validate_catches_bad_shapes(tmp_path):
    assert any("[[gateway]]" in m and "set_scenario must be 0.." in m for m in
               _problems(tmp_path, BASE + _GW + "set_scenario = 40000\n"))
    assert any("[[gateway]]" in m and "unknown scenario area" in m for m in
               _problems(tmp_path, BASE + _GW + 'set_scenario = "Nowheresville"\n'))
    assert any("[[gateway]]" in m and "value must be 0 or 1" in m for m in
               _problems(tmp_path, BASE + _GW + "set_flags = [{flag = 8520, value = 2}]\n"))
    assert any("[[gateway]]" in m and "needs a `flag`" in m for m in
               _problems(tmp_path, BASE + _GW + "set_flags = [{value = 1}]\n"))


def test_gateway_set_flags_counts_as_a_flag_setter(tmp_path):
    """A same-field 'the door sets a flag -> reveals an NPC' pattern must NOT lint-warn 'no event sets it':
    a gateway's set_flags is a flag SETTER (regression: lint_logic only knew event/cutscene/choice set_flag)."""
    from ff9mapkit.build import lint_logic
    toml = (BASE + _GW + "set_flags = [{flag = 8800, value = 1}]\n"
            + '\n[[npc]]\nname = "Revealed"\narchetype = "moogle"\npos = [0, -300]\n'
            + 'requires_flag = 8800\ndialogue = "You opened the way."\n')
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    warns = lint_logic(FieldProject.load(p))
    assert not any("8800" in w and "no event sets it" in w for w in warns)


def test_gateway_advance_lint_warns_on_reserved_band(tmp_path):
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + _GW + "set_flags = [{flag = 8400, value = 1}]\n", encoding="utf-8")
    w = lint_flag_bands(FieldProject.load(p))
    assert any("8400" in m and "gateway" in m for m in w)
    # advancing a REAL story bit (non-reserved) is the point -> no warning
    p.write_text(BASE + _GW + "set_flags = [{flag = 2600, value = 1}]\n", encoding="utf-8")
    assert lint_flag_bands(FieldProject.load(p)) == []
