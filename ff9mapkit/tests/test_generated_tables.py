"""Every generated / baked table carries a provenance stamp on the line after its docstring -- what it was
read from and which generator wrote it (scout F47) -- and every in-package generator emits that stamp.
The stamp's shape and the table registry are owned by ``ff9mapkit._regen_stamp``."""

from __future__ import annotations

import ast
import importlib
import inspect
import shutil
from pathlib import Path

import pytest

import ff9mapkit
from ff9mapkit import _regen_stamp as S

PKG = Path(ff9mapkit.__file__).resolve().parent


def _line_after_docstring(text: str) -> str:
    end = ast.parse(text).body[0].end_lineno          # the module docstring's closing line (1-based)
    return text.split("\n")[end]


@pytest.mark.parametrize("table", sorted(S.TABLES))
def test_every_table_is_stamped_by_its_registered_generator(table):
    line = _line_after_docstring((PKG / table).read_text(encoding="utf-8"))
    got = S.read_stamp(line)
    assert got is not None, (table, line)
    source, generator = got
    exp_generator, kind = S.TABLES[table]
    assert generator == exp_generator, (table, generator)
    if kind == "Memoria":
        assert source.startswith("Memoria@") and len(source) > len("Memoria@"), (table, source)
    else:
        assert source == kind, (table, source)


def test_the_registry_covers_every_table_in_the_package():
    """A new ``_*.py`` table lands in the registry (and so under the stamp check) or this fails."""
    found = set()
    for d, prefix in ((PKG, ""), (PKG / "eb", "eb/")):
        for p in d.glob("_*.py"):
            if p.name.startswith("_regen_") or p.name in ("__init__.py", "__main__.py"):
                continue
            found.add(prefix + p.name)
    assert found == set(S.TABLES), found ^ set(S.TABLES)


_STAMP = S.stamp_line("Memoria@abc123def456", "x.py")
_NPC = {1: {"animset": 1, "head_focus": 2, "logical_size": 3,
            "anims": {"stand": 1, "walk": 2, "run": 3, "left": 4, "right": 5}}}
_ALIAS = {"UPSCALE": {"A": "B"}, "REVERT_UPSCALE": {"B": "A"}, "DBALL_SWITCH": {}, "GEOID_SPECIALS": {"X": 1},
          "SUB_TYPE_GEO_IDS": frozenset({7})}
_GENERATORS = {
    "_regen_animdb": lambda m: m.render({1: "ANH_MAIN_F0_ZDN_IDLE"}, stamp=_STAMP),
    "_regen_animdb_all": lambda m: m.render({1: "ANH_MON_B0_X_IDLE"}, stamp=_STAMP),
    "_regen_fieldtable": lambda m: m.render({"fbg_n01_a": [1, "EVT_A"]}, {1: ["fbg_n01_a", "EVT_A"]}, stamp=_STAMP),
    "_regen_fieldtext": lambda m: m.render({1: 2}, stamp=_STAMP),
    "_regen_modelalias": lambda m: m.render(_ALIAS, stamp=_STAMP),
    "_regen_modeldb": lambda m: m.render({1: "GEO_MON_B0_001"}, stamp=_STAMP),
    "_regen_scenedb": lambda m: m.render({"BSC_A_0": 1}, stamp=_STAMP),
    "eb._regen_optables": lambda m: m.render([0, 1], [None, 1], {0: "Nop"}, stamp=_STAMP),
    "_regen_npcparams": lambda m: m._render(_NPC, stamp=_STAMP),
    "_regen_fieldschema": lambda m: m._emit({"": {"field"}}, set(), stamp=_STAMP),
}


@pytest.mark.parametrize("modname", sorted(_GENERATORS))
def test_every_in_package_generator_emits_the_stamp_after_its_docstring(modname):
    mod = importlib.import_module(f"ff9mapkit.{modname}")
    text = _GENERATORS[modname](mod)
    assert _line_after_docstring(text) == _STAMP, text[:400]
    ast.parse(text)                                                  # still a module
    main_src = inspect.getsource(mod.main)                           # and main really hands one in
    assert "memoria_stamp(" in main_src or "stamp_line(" in main_src, modname


def test_memoria_rev_reads_a_checkout_and_degrades_to_unknown(tmp_path):
    if shutil.which("git") is None:
        pytest.skip("no git on PATH")
    assert S.memoria_rev(tmp_path) == "unknown"                      # a plain dir (a source zip) -> unknown
    rev = S.memoria_rev(PKG)                                         # any path INSIDE a checkout works
    assert rev != "unknown" and 7 <= len(rev) <= 40 and all(c in "0123456789abcdef" for c in rev)
    assert S.read_stamp(S.memoria_stamp(PKG, "_regen_x.py")) == (f"Memoria@{rev}", "_regen_x.py")
    assert S.read_stamp("# not a stamp") is None
