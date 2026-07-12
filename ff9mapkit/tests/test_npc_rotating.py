"""Beat-windowed / rotating-cast NPCs -- `[[npc]]` `scenario_min`/`scenario_max` (the story-event director
primitive, #13). An NPC gated on a ScenarioCounter window `[min, max)` appears only during a story beat;
NPCs at one spot with adjacent windows are a rotating cast (a shopkeeper who changes by disc).

THE OBJECT-INIT GATE LAW (in-game proven 2026-07-12, the invisible-innkeeper bisect): the window compiles
to a CALL-SITE guard around the ``InitObject`` in Main_Init -- the stock idiom (18688 real Init funcs, zero
early-return-before-SetModel; an init-prologue gate loads the object permanently HIDDEN when it passes).
The guards are the exact FF9 byte shape the roster analyzer reads (`forkreport.scenario_gates` / `_sc_cond`
/ `roster_by_beat`), so these tests assert the authored guard ROUND-TRIPS through the reader.
"""
from __future__ import annotations

import pytest

from ff9mapkit import forkreport
from ff9mapkit.build import FieldProject, build_mod, validate, lint_logic, _lint_rotating_cast
from ff9mapkit.config import ModLayout
from ff9mapkit.content import npc as _npc
from ff9mapkit.content import region, startup
from ff9mapkit.eb import EbScript

SET_MODEL_OP = 0x2F
RETURN_OP = 0x04


def _window_block(smin, smax, body=b"\x09\x02\x00"):
    """The call-site guard block for a window, wrapped around an InitObject(2,0)-shaped body."""
    return region.guarded_call(startup.scenario_window_conds(smin, smax), body)


# ---- the guard primitive (no build) -------------------------------------------------------------
def test_window_guard_roundtrips_through_reader():
    g = _window_block(2600, 6990)
    # the roster reader decodes both bounds from the authored call-site guard
    assert forkreport.scenario_gates(g) == [2600, 6990]
    # and each guard is SC>=min / SC<max (not ==), so a RANGE gates
    conds = [forkreport._sc_cond(g, off) for off in range(len(g))]
    conds = [c for c in conds if c]
    assert (region.CMP_TOKENS[">="], 2600) in conds
    assert (region.CMP_TOKENS["<"], 6990) in conds


def test_window_guard_one_sided_and_empty():
    assert forkreport.scenario_gates(_window_block(3000, None)) == [3000]
    assert forkreport.scenario_gates(_window_block(None, 3000)) == [3000]
    assert startup.scenario_window_conds(None, None) == []          # no bounds -> no guards
    assert _window_block(None, None) == b"\x09\x02\x00"             # ...and the body passes through bare


def _anims():
    return _npc._complete_anims(10, None)


def _ops_before_setmodel(code: bytes) -> list:
    from ff9mapkit.eb.disasm import iter_code
    ops = []
    for ins in iter_code(code, 0, len(code)):
        if ins.op == SET_MODEL_OP:
            return ops
        ops.append(ins.op)
    return ops


def test_npc_init_is_unconditional_by_law():
    # the Init NEVER gates: no ScenarioCounter conds, and no RETURN before SetModel (the OBJECT-INIT
    # GATE LAW -- an init-prologue gate loads the object permanently hidden when it passes)
    b = _npc.build_npc_init(model=10, animset=0, anims=_anims(), x=100, z=200)
    assert forkreport.scenario_gates(b) == []
    assert RETURN_OP not in _ops_before_setmodel(b)


def test_window_composes_with_flag_guard():
    conds = startup.scenario_window_conds(2600, None)
    conds.append((region.cond_truthy(region.GLOB_BOOL, 8512), True))
    g = region.guarded_call(conds, b"\x09\x02\x00")
    assert forkreport.scenario_gates(g) == [2600]                   # window present
    assert region.cond_truthy(region.GLOB_BOOL, 8512) in g          # flag cond present too
    assert g.endswith(b"\x09\x02\x00")                              # the InitObject is the guarded body


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
    # THE LAW: no object Init in the built field returns before SetModel (a gated init loads hidden)
    for e in eb.entries:
        if e.empty:
            continue
        f0 = e.func_by_tag(0)
        if f0 is None:
            continue
        ops = []
        for ins in eb.instrs(f0):
            if ins.op == SET_MODEL_OP:
                break
            ops.append(ins.op)
        assert RETURN_OP not in ops, f"entry {e.index}: Init returns before SetModel"
    # ...and no window bytes inside any object entry -- the gating lives at the Main_Init CALL SITE,
    # so roster_by_beat (which symbolically walks Main_Init) now sees the cast rotate for real:
    beats = {beat: {s for s, _, _ in entries}
             for beat, _, entries in forkreport.roster_by_beat(eb, data, set())}
    assert set(beats) >= {0, 2600, 6990}
    early = beats[2600] - beats[0]                  # keeper_early spawns only inside [2600, 6990)
    late = beats[6990] - beats[0]                   # keeper_late from 6990 on
    assert len(early) == 1 and len(late) == 1 and early != late


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


# ---- the rotating-cast lint (overlap / gap) ----------------------------------------------------
def _npcs(*windows):
    """NPCs at ONE spot with the given (min, max) windows."""
    return [{"name": f"n{i}", "pos": [100, -400], "scenario_min": w[0], "scenario_max": w[1]}
            for i, w in enumerate(windows)]


def test_lint_tiled_windows_clean():
    # adjacent half-open windows [_,6990) then [6990,_) tile perfectly -> no warning (the demo field's shape)
    assert _lint_rotating_cast(_npcs((None, 6990), (6990, None))) == []


def test_lint_overlap_warns():
    warns = _lint_rotating_cast(_npcs((0, 7000), (6990, None)))    # 6990..7000 covered by both
    assert any("OVERLAPPING" in w for w in warns)


def test_lint_gap_warns():
    warns = _lint_rotating_cast(_npcs((None, 3000), (5000, None)))  # 3000..5000 has nobody
    assert any("GAP" in w for w in warns)


def test_lint_lone_windowed_npc_is_clean():
    # a single gated NPC's "absence outside its beat" is intentional, not a gap
    assert _lint_rotating_cast(_npcs((2600, 6990))) == []


def test_lint_different_spots_dont_interact():
    a = {"name": "a", "pos": [100, -400], "scenario_max": 3000}
    b = {"name": "b", "pos": [900, -400], "scenario_min": 5000}    # far away -> not a shared spot
    assert _lint_rotating_cast([a, b]) == []


def test_lint_wired_into_lint_logic(tmp_path):
    overlapping = _BASE + """
[[npc]]
name = "a"
model = "GEO_NPC_F1_BBA"
pos = [120, -520]
scenario_max = 7000

[[npc]]
name = "b"
model = "GEO_NPC_F1_BBA"
pos = [120, -520]
scenario_min = 6990
"""
    p = tmp_path / "ov.field.toml"
    p.write_text(overlapping, encoding="utf-8")
    proj = FieldProject.load(p)
    assert validate(proj) == []                                    # a valid build -- overlap is a LINT, not an error
    assert any("OVERLAPPING" in w for w in lint_logic(proj))
