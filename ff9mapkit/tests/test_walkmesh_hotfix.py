"""Reproduce a real field's LOAD-TIME engine walkmesh hotfix in a fork.

A few fields rely on a hardcoded Memoria hotfix (BGI_triSetActive keyed on the real fldMapNo) that toggles
walkmesh-triangle active-state at field load (e.g. Gulug/Room blocks the broken wall). A fork runs at a custom
id, so that guard is false and the hotfix never fires. content.walkmesh_hotfix reproduces the AUTO (load-time)
class by prepending EnablePathTriangle(tri,state) to Main_Init; the catalog (walkmesh_hotfixes) classifies all
~11 fields and fork-report flags the non-reproducible ones as lost-on-mint.
"""
from __future__ import annotations

from ff9mapkit import data, walkmesh_hotfixes as WH
from ff9mapkit import forkreport
from ff9mapkit.content import walkmesh_hotfix as WHX
from ff9mapkit.eb import EbScript, opcodes

ENABLE_PATH_TRIANGLE = 0x9A


def _tag0_ops(ebb):
    eb = EbScript.from_bytes(ebb)
    f0 = eb.entry(0).func_by_tag(0)
    return [(i.op, list(i.args or [])) for i in eb.instrs(f0)]


# --- catalog ---------------------------------------------------------------------------------------------
def test_catalog_load_time_is_auto_with_toggles():
    h = WH.info(2356)                                            # Gulug/Room (broken-wall block)
    assert h is not None and h.kind == "load_time" and h.auto
    assert h.toggles == ((78, 0), (79, 0), (80, 0))
    assert WH.load_time_toggles(2356) == [[78, 0], [79, 0], [80, 0]]
    assert WH.load_time_toggles("2161") == [[69, 0]]            # accepts a numeric string


def test_catalog_dynamic_is_not_auto():
    h = WH.info(2803)                                            # Daguerreo librarian -- tracks a story var
    assert h is not None and h.kind == "dynamic" and not h.auto
    assert WH.load_time_toggles(2803) == []                    # nothing statically reproducible
    h2 = WH.info(1753)                                          # opcode-augment -- also not auto
    assert h2.kind == "opcode_augment" and not h2.auto


def test_catalog_unknown_field_is_none():
    assert WH.info(99999) is None
    assert WH.info(None) is None
    assert WH.load_time_toggles(99999) == []
    assert set(WH.all_ids()) >= {2356, 2161, 2507, 2803, 900, 450, 1421}


# --- injector --------------------------------------------------------------------------------------------
def test_apply_prepends_enable_path_triangle_per_toggle():
    src = data.blank_field_bytes("us")
    out = WHX.apply_tri_toggles(src, [(78, 0), (79, 0), (80, 0)])
    assert EbScript.from_bytes(out).to_bytes() == out          # still a valid .eb (entry/func tables fixed)
    one = len(opcodes.encode(ENABLE_PATH_TRIANGLE, 0, 0))
    assert len(out) == len(src) + 3 * one
    ops = _tag0_ops(out)
    assert ops[0] == (ENABLE_PATH_TRIANGLE, [78, 0])           # tris off from frame 1, like the engine at load
    assert ops[1] == (ENABLE_PATH_TRIANGLE, [79, 0])
    assert ops[2] == (ENABLE_PATH_TRIANGLE, [80, 0])


def test_apply_state_is_coerced_to_bit():
    out = WHX.apply_tri_toggles(data.blank_field_bytes("us"), [(105, 1)])
    assert _tag0_ops(out)[0] == (ENABLE_PATH_TRIANGLE, [105, 1])


def test_no_toggles_is_a_noop():
    src = data.blank_field_bytes("us")
    assert WHX.apply_tri_toggles(src, []) == src               # byte-identical when there's nothing to do
    assert WHX.apply_tri_toggles(src, None) == src


# --- build wiring ----------------------------------------------------------------------------------------
def test_build_wires_walkmesh_tri_toggles_from_field_block(tmp_path):
    from ff9mapkit import build
    base = ('[field]\nid=4700\nname="F"\nborrow_bg="MGNT_MAP810_MN_MOG_0"\narea=56\ntext_block=8\n'
            '{flag}[camera]\npitch=30\ndistance=900\nfov=40\n[player]\nspawn=[0,0]\n')
    p = tmp_path / "f.field.toml"
    p.write_text(base.format(flag="walkmesh_tri_toggles=[[78,0],[79,0],[80,0]]\n"), encoding="utf-8")
    ops = _tag0_ops(build.build_script(build.FieldProject.load(p), "us", {}))
    assert ops[0] == (ENABLE_PATH_TRIANGLE, [78, 0])
    assert ops[1] == (ENABLE_PATH_TRIANGLE, [79, 0])
    assert ops[2] == (ENABLE_PATH_TRIANGLE, [80, 0])
    # absent -> unchanged (no EnablePathTriangle prepend)
    p.write_text(base.format(flag=""), encoding="utf-8")
    ops2 = _tag0_ops(build.build_script(build.FieldProject.load(p), "us", {}))
    assert ops2[0] != (ENABLE_PATH_TRIANGLE, [78, 0])


def test_build_validate_rejects_malformed_toggles(tmp_path):
    from ff9mapkit import build
    base = ('[field]\nid=4700\nname="F"\nborrow_bg="MGNT_MAP810_MN_MOG_0"\narea=56\ntext_block=8\n'
            'walkmesh_tri_toggles=[[78,2]]\n[camera]\npitch=30\ndistance=900\nfov=40\n[player]\nspawn=[0,0]\n')
    p = tmp_path / "f.field.toml"
    p.write_text(base, encoding="utf-8")
    problems = build.validate(build.FieldProject.load(p))
    assert any("walkmesh_tri_toggles" in x for x in problems)   # state 2 is not 0|1


# --- fork-report -----------------------------------------------------------------------------------------
def test_fork_report_flags_walkmesh_hotfix():
    eb = data.blank_field_bytes("us")
    assert forkreport.analyze_eb(eb, field_id=2356).walkmesh_hotfix == "auto"     # load-time, reproduced
    assert forkreport.analyze_eb(eb, field_id=2803).walkmesh_hotfix == "lost"     # dynamic, fork-in-place
    assert forkreport.analyze_eb(eb, field_id=0).walkmesh_hotfix == ""            # no hotfix (fixture)
    txt = forkreport.format_report(forkreport.analyze_eb(eb, field_id=2803))
    assert "Walkmesh fix" in txt and "LOST on a mint" in txt
