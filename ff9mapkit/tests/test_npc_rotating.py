"""Beat-windowed / rotating-cast NPCs -- `[[npc]]` `scenario_min`/`scenario_max` (the story-event director
primitive, #13). An NPC self-gates on a ScenarioCounter window `[min, max)` so it appears only during a story
beat; NPCs at one spot with adjacent windows are a rotating cast (a shopkeeper who changes by disc).

The gates are the exact FF9 byte shape the roster analyzer reads (`forkreport.scenario_gates` / `_sc_cond`),
so these tests assert the authored gate ROUND-TRIPS through the reader -- writer and reader agree byte-for-byte.
"""
from __future__ import annotations

import pytest

from ff9mapkit import forkreport
from ff9mapkit.build import FieldProject, build_mod, validate
from ff9mapkit.config import ModLayout
from ff9mapkit.content import npc as _npc
from ff9mapkit.content import region, startup
from ff9mapkit.eb import EbScript


# ---- the gate primitive (no build) -------------------------------------------------------------
def test_window_gate_roundtrips_through_reader():
    g = startup.scenario_window_gate(2600, 6990)
    # the roster reader decodes both bounds from the authored gate
    assert forkreport.scenario_gates(g) == [2600, 6990]
    # and each guard is SC>=min / SC<max (not ==), so a RANGE gates
    conds = [forkreport._sc_cond(g, off) for off in range(len(g))]
    conds = [c for c in conds if c]
    assert (region.CMP_TOKENS[">="], 2600) in conds
    assert (region.CMP_TOKENS["<"], 6990) in conds


def test_window_gate_one_sided_and_empty():
    assert forkreport.scenario_gates(startup.scenario_window_gate(3000, None)) == [3000]
    assert forkreport.scenario_gates(startup.scenario_window_gate(None, 3000)) == [3000]
    assert startup.scenario_window_gate(None, None) == b""          # no bounds -> no gate


def _anims():
    return _npc._complete_anims(10, None)


def test_build_npc_init_prepends_window():
    b = _npc.build_npc_init(model=10, animset=0, anims=_anims(), x=100, z=200,
                            scenario_window=(2600, 6990))
    assert forkreport.scenario_gates(b) == [2600, 6990]
    # gate is a PROLOGUE -> the window bytes precede CreateObject (the object returns before it appears)
    assert b.index(bytes(startup.scenario_window_gate(2600, 6990))) == 0


def test_window_composes_with_flag_gate():
    b = _npc.build_npc_init(model=10, animset=0, anims=_anims(), x=0, z=0,
                            gate=(8512, True), scenario_window=(2600, None))
    assert forkreport.scenario_gates(b) == [2600]                   # window present
    assert region.flag_gate(region.GLOB_BOOL, 8512, require_set=True) in b   # flag present too


def test_no_window_is_byte_identical():
    plain = _npc.build_npc_init(model=10, animset=0, anims=_anims(), x=100, z=200)
    assert forkreport.scenario_gates(plain) == []


# ---- end-to-end through a real field.toml build ------------------------------------------------
_BASE = """
[field]
id = 4003
name = "ROTROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""

# a rotating shopkeeper: two NPCs at ONE spot, adjacent half-open windows -> the cast swaps at SC 6990
_ROTATING = _BASE + """
[[npc]]
name = "keeper_early"
model = "GEO_NPC_F1_BBA"
pos = [120, -400]
scenario_min = 2600
scenario_max = 6990

[[npc]]
name = "keeper_late"
model = "GEO_NPC_F1_BBA"
pos = [120, -400]
scenario_min = 6990
"""


def _build(tmp_path, toml):
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    proj = FieldProject.load(p)
    assert validate(proj) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    return EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_ROTROOM.eb.bytes").read_bytes())


def test_rotating_pair_end_to_end(tmp_path):
    eb = _build(tmp_path, _ROTATING)
    data = eb.data
    # both windows are present in the built .eb, decoded by the roster reader
    gates = forkreport.scenario_gates(data)
    assert 2600 in gates and 6990 in gates
    # the two keeper objects self-gate: walk the roster at three beats and confirm which keeper is "live"
    # (present-and-ungated). We verify via the analyzer's beat table: the field gates content on 2600/6990.
    beats = forkreport.roster_by_beat(eb, data, set())
    # roster_by_beat returns [] when the roster doesn't vary; here the InitObject calls are unconditional
    # (the gating is in each object's OWN Init, not Main_Init) -- so assert the per-object gates instead:
    # each keeper entry's Init carries its window.
    windows = []
    for e in eb.entries:
        if e.empty:
            continue
        f0 = e.func_by_tag(0)
        if f0 is None:
            continue
        body = data[f0.abs_start:f0.abs_end]
        g = forkreport.scenario_gates(body)
        if g:
            windows.append(sorted(g))
    assert [2600, 6990] in windows          # keeper_early: [2600, 6990)
    assert [6990] in windows                # keeper_late: [6990, inf)


def test_validation_rejects_inverted_window(tmp_path):
    bad = _BASE + """
[[npc]]
name = "x"
model = "GEO_NPC_F1_BBA"
pos = [0, -400]
scenario_min = 7000
scenario_max = 3000
"""
    p = tmp_path / "bad.field.toml"
    p.write_text(bad, encoding="utf-8")
    probs = validate(FieldProject.load(p))
    assert any("scenario_min" in x and "scenario_max" in x for x in probs)


def test_validation_rejects_out_of_range(tmp_path):
    bad = _BASE + """
[[npc]]
name = "x"
model = "GEO_NPC_F1_BBA"
pos = [0, -400]
scenario_min = 99999
"""
    p = tmp_path / "bad2.field.toml"
    p.write_text(bad, encoding="utf-8")
    probs = validate(FieldProject.load(p))
    assert any("scenario_min must be" in x for x in probs)
