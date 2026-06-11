"""[startup] story-state presets -- assert the story beat a forked field represents.

A fork boots with a zero gEventGlobal, so every story-gated NPC/door/event takes the not-yet-happened
branch. [startup] presets the ScenarioCounter + specific story bits at field load (prepended to Main_Init).
These tests pin the injected bytecode (set_var sequences), the name/area resolution, validation, the
reserved-region lint, and that the .eb stays parseable + byte-identical when [startup] is absent.
"""
from __future__ import annotations

import pytest

from ff9mapkit.build import FieldProject, build_mod, validate, lint_flag_bands
from ff9mapkit.config import ModLayout
from ff9mapkit.content import region
from ff9mapkit.eb import EbScript

BASE = """
[field]
id = 4003
name = "STARTROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""

STARTUP = BASE + """
[startup]
scenario = 7200
flags = [{flag = 8520, value = 1}, {flag = 8521, value = 0}]
"""


def _build_eb(tmp_path, toml: str):
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    return EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_STARTROOM.eb.bytes").read_bytes())


def _main_init_bytes(eb: EbScript) -> bytes:
    f0 = eb.entry(0).func_by_tag(0)
    return eb.data[f0.abs_start:f0.abs_end]


def test_startup_injects_scenario_and_flags(tmp_path):
    body = _main_init_bytes(_build_eb(tmp_path, STARTUP))
    assert region.set_var(region.GLOB_UINT16, 0, 7200) in body      # ScenarioCounter @ byte 0
    assert region.set_var(region.GLOB_BOOL, 8520, 1) in body         # a story bit set
    assert region.set_var(region.GLOB_BOOL, 8521, 0) in body         # a story bit cleared


def test_startup_runs_first_in_main_init(tmp_path):
    """The presets are prepended -> they are the first bytes of Main_Init, so later gates see them set."""
    body = _main_init_bytes(_build_eb(tmp_path, STARTUP))
    assert body.startswith(region.set_var(region.GLOB_UINT16, 0, 7200))


def test_startup_absent_does_not_inject(tmp_path):
    body = _main_init_bytes(_build_eb(tmp_path, BASE))
    assert region.set_var(region.GLOB_UINT16, 0, 7200) not in body
    # the GLOB_UINT16 scenario-write opcode pattern is absent entirely when [startup] is omitted
    assert bytes([0x05, region.GLOB_UINT16, 0x00]) not in body


def test_startup_eb_parses_clean_after_inject(tmp_path):
    """insert_in_function must keep the entry/func tables consistent -- the .eb round-trips + Main_Init
    disassembles without error (no fpos corruption)."""
    eb = _build_eb(tmp_path, STARTUP)
    f0 = eb.entry(0).func_by_tag(0)
    assert list(eb.instrs(f0))                                       # Main_Init still disassembles
    # the after-battle handler (entry-0 tag-10, the func AFTER tag-0) survived the insert intact
    reinit = eb.entry(0).func_by_tag(10)
    if reinit is not None:
        assert list(eb.instrs(reinit))


def test_startup_scenario_by_area_name(tmp_path):
    toml = BASE + '\n[startup]\nscenario = "Ice Cavern"\n'         # resolves to 2500 (a unique beat)
    body = _main_init_bytes(_build_eb(tmp_path, toml))
    assert region.set_var(region.GLOB_UINT16, 0, 2500) in body


def test_startup_flag_by_name(tmp_path):
    toml = (BASE + '\n[[flag]]\nname = "switch_on"\nindex = 8520\n'
            '\n[startup]\nflags = [{flag = "switch_on", value = 1}]\n')
    body = _main_init_bytes(_build_eb(tmp_path, toml))
    assert region.set_var(region.GLOB_BOOL, 8520, 1) in body


def _problems(tmp_path, toml: str):
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    return validate(FieldProject.load(p))


def test_startup_validate_catches_bad_shapes(tmp_path):
    # pin distinctive message fragments (not just "scenario"/"value") so a future wording drift in the
    # shared _validate_story_writes helper is caught -- it's reused by [[gateway]] set_scenario/set_flags too.
    assert any("scenario must be 0.." in m for m in _problems(tmp_path, BASE + "\n[startup]\nscenario = 40000\n"))
    assert any("unknown scenario area" in m for m in
               _problems(tmp_path, BASE + '\n[startup]\nscenario = "Nowheresville"\n'))
    assert any("value must be 0 or 1" in m for m in
               _problems(tmp_path, BASE + "\n[startup]\nflags = [{flag = 8520, value = 2}]\n"))
    assert any("needs a `flag`" in m for m in
               _problems(tmp_path, BASE + "\n[startup]\nflags = [{value = 1}]\n"))


def test_startup_shared_flag_name_resolves_at_load(tmp_path):
    """A campaign-shared flag name in [startup] flags (not in the member's own [[flag]] table) resolves via
    the campaign name map at load -- same fix as the gateway set_flags read/write-parity regression."""
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + '\n[startup]\nflags = [{flag = "rescued_dagger", value = 1}]\n', encoding="utf-8")
    proj = FieldProject.load(p, flag_names={"rescued_dagger": 8700})
    assert validate(proj) == []
    assert proj.raw["startup"]["flags"][0]["flag"] == 8700


def test_startup_lint_warns_only_on_reserved_band(tmp_path):
    # a preset into the treasure-chest bitfield (reserved) is flagged -- it corrupts real save state
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + "\n[startup]\nflags = [{flag = 8400, value = 1}]\n", encoding="utf-8")
    w = lint_flag_bands(FieldProject.load(p))
    assert any("8400" in m and "chest_opened" in m and "[startup]" in m for m in w)
    # presetting a REAL story bit (non-reserved) is the whole point -> no warning
    p.write_text(BASE + "\n[startup]\nflags = [{flag = 2600, value = 1}]\n", encoding="utf-8")
    assert lint_flag_bands(FieldProject.load(p)) == []
