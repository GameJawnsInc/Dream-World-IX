"""Region arming from Main_Init (eb.edit.activate): patch a Wait filler, or INSERT past the 2-filler budget.

The blank field template has only 2 Wait(2) fillers; a field with >2 regions exhausts them, so the 3rd+
region must INSERT its InitRegion into Main_Init. Regression (found in-game forking a Daguerreo chain): the
old fallback used raw insert_bytes at a stale Main_Init position, so the 2nd+ insert corrupted the bytecode
and that region SILENTLY never armed (a campaign member's on-entry events never fired). The fix routes the
fallback through insert_in_function (fpos-fixing). This pins: every region of a many-region field is armed,
and the .eb stays fully parseable.
"""
from __future__ import annotations

from ff9mapkit.build import FieldProject, build_mod
from ff9mapkit.config import ModLayout
from ff9mapkit.eb import EbScript

BASE = """
[field]
id = 4003
name = "ARMROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1200, -100], [1200, -100], [1200, -1000], [-1200, -1000]]

[player]
spawn = [0, -200]
"""


def _gateway(to: int, ztop: int) -> str:
    zbot = ztop - 100
    return (f"\n[[gateway]]\nto = {to}\nentrance = 0\n"
            f"zone = [[-200, {ztop}], [200, {ztop}], [200, {zbot}], [-200, {zbot}]]\n")


def _build(tmp_path, toml: str) -> EbScript:
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    return EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_ARMROOM.eb.bytes").read_bytes())


def _main_init(eb: EbScript):
    return eb.entry(0).func_by_tag(0)


def _eb_fully_parses(eb: EbScript) -> bool:
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            list(eb.instrs(f))           # raises on a corrupt func boundary
    return True


def test_two_regions_use_wait_fillers(tmp_path):
    # within budget: 2 gateways patch the 2 Wait fillers, both armed
    eb = _build(tmp_path, BASE + _gateway(30000, -300) + _gateway(30001, -450))
    inits = [ins for ins in eb.instrs(_main_init(eb)) if ins.name == "InitRegion"]
    assert len(inits) == 2
    assert _eb_fully_parses(eb)


def test_many_regions_all_arm_via_insert_fallback(tmp_path):
    """5 gateways: 2 patch the Wait fillers, 3 must INSERT -- all 5 must arm and the .eb must stay valid
    (the bug: the 2nd+ insert corrupted the bytecode so those regions never armed)."""
    toml = BASE + "".join(_gateway(30000 + i, -300 - i * 130) for i in range(5))
    eb = _build(tmp_path, toml)
    inits = [ins for ins in eb.instrs(_main_init(eb)) if ins.name == "InitRegion"]
    assert len(inits) == 5            # every region armed, not just the 2 that fit the fillers
    assert _eb_fully_parses(eb)       # no corruption from the sequential inserts
