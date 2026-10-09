"""THE SWITCHABLE CELLS (terrain study defect 19).

26 overworld cells swap block form with nine story places (ff9.cs w_worldChangeBlockSet). There ``Terrain``/
``Object`` (and the Fire Shrine volcano, and the Water Shrine cell's seas) are form-1 parts, so a kit override of
one vanishes when the place switches and the stock ``Terrain2``/``Object2`` comes back. The forms lane found no kit
check that knew the set (F14). Now every writer's post-step (``discmirror.auto_mirror``) names such an edit, and
``world-forms`` checks a mod folder. The table was checked against the study's prefab census
(``studies/terrain-malleability/forms/out/prefab_census.json``): the same 26 cells on both discs, and all 297 part
slots of the switchable prefabs in the form this module gives them.
"""
from __future__ import annotations

import argparse

from ff9mapkit import cli, config
from ff9mapkit.world import discmirror as DM, environment as ENV, forms as F


def _override(root, disc, x, y, part):
    p = root / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{y}" / f"Block[{x}][{y}] {part}.ff9mesh"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")
    return p


def test_the_table_is_the_engines():
    assert len(F.SWITCHABLE) == 26 and sum(len(c) for c in F.PLACE_CELLS.values()) == 26    # no cell in two places
    assert set(F.PLACE_CELLS) == set(F.DEFAULT_CONDITION) and ENV.FORM_PLACES == tuple(F.PLACE_CELLS)
    assert F.SWITCHABLE[(20, 10)] == "Alexandria" and F.SWITCHABLE[(3, 9)] == "WaterShrine"


def test_part_form_follows_loadblock():
    assert F.part_form(20, 10, "Terrain") == 1 and F.part_form(20, 10, "object") == 1
    assert F.part_form(20, 10, "Terrain2") == 2 and F.part_form(20, 10, "Object2") == 2
    assert F.part_form(20, 10, "Sea4") is None and F.part_form(20, 10, "River") is None    # both forms
    assert F.part_form(3, 9, "Sea4") == 1 and F.part_form(3, 9, "Sea4_2") == 2              # block 219's seas
    assert F.part_form(7, 1, "VolcanoCrater1") == 1 and F.part_form(7, 1, "VolcanoLava2") == 2
    assert F.part_form(21, 9, "Terrain") is None                                           # not switchable


def test_dormant_on_disc_4_and_path_d():
    assert not F.dormant("Alexandria", 1) and F.dormant("Alexandria", 4)                     # w_frameDisc == 1 gate
    assert not F.dormant("MognetCentral", 4) and not F.dormant("ChocoboParadise", 4)         # flag places switch
    assert F.dormant("Cleyra", 9) and F.dormant("ChocoboParadise", 9)                        # BLANK mode default


def test_form_hits_and_their_receipt(tmp_path):
    t = _override(tmp_path, 1, 20, 10, "Terrain")
    hits = F.form_hits([t, "not-a-path.ff9mesh", object(), tmp_path / "missing.ff9mesh"])
    assert [(h["cell"], h["part"], h["form"], h["covered"]) for h in hits] == [((20, 10), "Terrain", 1, False)]
    (line,) = F.note_lines(hits)
    assert "!! WARNING: Block[20][10] Terrain (Disc1) replaces FORM 1 ONLY" in line and "Alexandria" in line
    assert "run the same edit again with --form 2" in line and "ScenarioCounter >= 8800" in line
    _override(tmp_path, 1, 20, 10, "Terrain2")
    (h,) = F.form_hits([t])
    assert h["covered"] and F.note_lines([h])[0].startswith("  note:")
    crater = F.form_hits([_override(tmp_path, 1, 7, 1, "VolcanoCrater1")])
    assert "form 2 has no VolcanoCrater1 here" in F.note_lines(crater)[0]
    assert F.form_hits([_override(tmp_path, 4, 20, 10, "Terrain")]) == []                    # dormant: dropped
    assert F.form_hits([_override(tmp_path, 4, 16, 1, "Terrain")])[0]["place"] == "MognetCentral"
    assert F.form_hits([_override(tmp_path, 1, 20, 10, "Sea4")]) == []                       # a shared part


def test_every_writers_post_step_names_the_edit(tmp_path):
    """auto_mirror is the one post-step every world writer runs; it names a form-1 edit even under --skip-mirror,
    and the replayed call (REPLAY) stays silent."""
    t = _override(tmp_path, 1, 13, 12, "Object")                                             # a bare Object: form 1
    log = []
    DM.auto_mirror([t], mod_folder="MOD", skip_mirror=True, log=log.append)
    assert any("Block[13][12] Object (Disc1) replaces FORM 1 ONLY" in ln and "Cleyra" in ln for ln in log)
    assert log[-1].endswith("skipped (--skip-mirror)")
    quiet = []
    DM.auto_mirror([t], mod_folder="MOD", skip_mirror=DM.REPLAY, log=quiet.append)
    assert quiet == []
    m = _override(tmp_path / "MOD", 1, 13, 12, "Object")
    gen = []
    DM.auto_mirror((p for p in [m]), mod_folder="MOD", log=gen.append)       # a generator: read once, used twice
    assert "FORM 1 ONLY" in gen[0] and gen[1].startswith("disc-4 mirror: NOT RUN for Disc1")   # (no p0data here)


def test_world_forms_fires_on_a_synthetic_edit_at_20_10(tmp_path, monkeypatch, capsys):
    """The study's registered check O5: the live stack reads 0 disc-1/4 hits and one dormant Path D hit at (14,12);
    a synthetic edit at (20,10) must fire."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    mod = tmp_path / "MOD"
    _override(mod, 9, 14, 12, "Terrain")
    ns = argparse.Namespace(mod_folder="MOD", stack=False, game=None, arm=None, disarm=None, when=None, disc=1)
    assert cli._cmd_world_forms(ns) == 0
    out = capsys.readouterr().out
    assert "1 override(s) on a switchable cell, 0 where the place switches" in out and "dormant: Block[14][12]" in out
    _override(mod, 1, 20, 10, "Terrain")
    assert cli._cmd_world_forms(ns) == 1
    assert "!! WARNING: Block[20][10] Terrain (Disc1) replaces FORM 1 ONLY" in capsys.readouterr().out
    _override(mod, 1, 20, 10, "Terrain2")
    assert cli._cmd_world_forms(ns) == 0
    (tmp_path / "Memoria.ini").write_text('[Mod]\nFolderNames = "MOD", "OTHER"\n', encoding="utf-8")
    assert cli._cmd_world_forms(argparse.Namespace(mod_folder=None, stack=True, game=None, arm=None, disarm=None, when=None, disc=1)) == 0
    out = capsys.readouterr().out
    assert "\nMOD: 3 override(s)" in out and "\nOTHER: 0 override(s)" in out
