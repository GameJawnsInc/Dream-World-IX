"""The editor model: round-trip-safe TOML writer + FieldDoc (load/save/merge).

The serializer's contract is round-trip equality (``tomllib.loads(dumps(d)) == d``), proven here on a
representative doc exercising every value type AND on every bundled example field.toml. FieldDoc tests
prove it preserves the scene/field split (saves logic only) and that its merged view matches what
``ff9mapkit build`` compiles.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from ff9mapkit.build import FieldProject
from ff9mapkit.editor import model

EXAMPLES = sorted((Path(__file__).resolve().parents[1] / "examples").rglob("*.field.toml"))


def test_dumps_roundtrips_every_value_type():
    d = {
        "field": {"id": 4003, "name": "ROOM", "area": 11, "text_block": 1073,
                  "title": 'a "quoted"\nmulti-line\ttitle'},
        "camera": {"pitch": 48.0, "fov": 42.2, "distance": 4500, "yaw": 0,
                   "scroll": {"enabled": True}, "frame": {"back": 205, "front": 432}},
        "walkmesh": {"quad": [[-1400, -2400], [1400, -2400], [1400, -800], [-1400, -800]],
                     "frame": "world"},
        "layers": [{"image": "art/back.png", "z": 4000},
                   {"image": "art/glow.png", "z": 873, "shader": "PSX/FieldMap_Abr_1"}],
        "player": {"spawn": [0, -1350]},
        "npc": [{"name": "Vivi", "preset": "vivi", "pos": [0, -700], "dialogue": "I miss you"},
                {"name": "Guard", "model": 21, "animset": 0,
                 "anims": {"stand": 1, "walk": 2, "run": 3, "left": 4, "right": 5},
                 "pos": [400, -200], "requires_flag": 200}],
        "gateway": [{"name": "door", "to": 4000, "entrance": 0,
                     "zone": [[-1100, -2400], [1100, -2400], [1100, -1750], [-1100, -1750]]}],
        "event": [{"name": "chest", "zone": [[-700, -2400], [700, -2400], [700, -1900], [-700, -1900]],
                   "message": "You got a Potion!", "give_item": [232, 1], "gil": 1000,
                   "set_flag": [200, 1], "once": True}],
        "camera_zone": [{"to_camera": 1, "zone": [[0, 0], [100, 0], [100, 100], [0, 100]]}],
        "encounter": {"scene": 67, "freq": 200, "battle_music": 0},
        "music": {"song": 9},
        "cutscene": {"actor": "Vivi", "once": True, "warmup": 30,
                     "steps": [{"say": "hello"}, {"wait": 30}, {"walk": [0, -800]},
                               {"face_player": True}, {"animation": 7302}, {"set_flag": [201, 1]}]},
        "choice": [{"npc": "Vivi", "prompt": "What?",      # nested array-of-tables (options)
                    "options": [{"text": "Potion", "reply": "ok", "give_item": ["Potion", 1], "gil": -100},
                                {"text": "Nothing", "set_flag": [8001, 1]}]}],
    }
    assert tomllib.loads(model.dumps(d)) == d


def test_dumps_output_is_canonically_ordered():
    text = model.dumps({"cutscene": {"steps": [{"say": "x"}]}, "field": {"id": 1, "name": "Z", "area": 11}})
    assert text.index("[field]") < text.index("[cutscene]")     # field before cutscene


def test_dumps_inline_table_keys_and_root_order_override():
    # a battle.toml uses a DIFFERENT schema: 'scene' is a big FORMATION table, not the field.toml inline
    # Blender-ref, so it must emit as real [scene]/[[scene.enemy]] sections (a name collision with field.toml).
    bdata = {"battlemap": {"bbg": "BBG_B013"},
             "scene": {"monster_count": 2, "enemy": [{"slot": 0, "hp": 500}], "ai_phase": [{"entry": 1}]},
             "character": [{"character": "Zidane", "strength": 99}]}
    # the field.toml default WOULD inline 'scene' (it's in _INLINE_TABLE_KEYS) -> demonstrate the collision...
    assert "scene = {" in model.dumps(bdata)
    # ...and the battle override emits sections instead, leading with the map identity, and round-trips.
    text = model.dumps(bdata, inline_table_keys=frozenset(), root_order=("battlemap", "scene"))
    assert "scene = {" not in text
    assert "[scene]" in text and "[[scene.enemy]]" in text and "[[scene.ai_phase]]" in text
    assert "[[character]]" in text
    assert text.index("[battlemap]") < text.index("[scene]")    # map identity leads
    assert tomllib.loads(text) == bdata                         # lossless


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_dumps_roundtrips_bundled_examples(path):
    orig = tomllib.loads(path.read_text(encoding="utf-8"))
    assert tomllib.loads(model.dumps(orig)) == orig


def test_fielddoc_split_preserved_and_merged_matches_build(tmp_path):
    (tmp_path / "room.field.toml").write_text(
        '[field]\nid = 4003\nname = "ROOM"\narea = 11\ntext_block = 1073\n\n'
        '[[npc]]\nname = "Vivi"\npreset = "vivi"\ndialogue = "hi"\n', encoding="utf-8")
    (tmp_path / "room.scene.toml").write_text(
        '[camera]\nborrow = "camera.bgx"\n\n[walkmesh]\nobj = "walkmesh.obj"\n\n'
        '[player]\nspawn = [0, -900]\n\n[[npc]]\nname = "Vivi"\npos = [0, -700]\n', encoding="utf-8")
    doc = model.FieldDoc.load(tmp_path / "room.field.toml")
    assert doc.scene_data is not None and "camera" in doc.scene_data
    # merged view == exactly what the builder sees
    assert doc.merged() == FieldProject.load(tmp_path / "room.field.toml").raw
    assert doc.merged()["npc"][0]["pos"] == [0, -700]
    assert doc.merged()["npc"][0]["dialogue"] == "hi"
    # edit logic + save: field.toml stays logic-only; scene.toml untouched
    doc.list_section("npc")[0]["dialogue"] = "changed"
    doc.save()
    field_rt = tomllib.loads((tmp_path / "room.field.toml").read_text(encoding="utf-8"))
    assert "camera" not in field_rt and "walkmesh" not in field_rt
    assert field_rt["npc"][0]["dialogue"] == "changed" and "pos" not in field_rt["npc"][0]
    scene_rt = tomllib.loads((tmp_path / "room.scene.toml").read_text(encoding="utf-8"))
    assert scene_rt["npc"][0]["pos"] == [0, -700]   # scene file never written by the editor


def test_single_file_doc_preserves_spatial_sections(tmp_path):
    # no scene sibling -> the field.toml holds spatial too; the editor must keep it on save
    src = (Path(__file__).resolve().parents[1] / "examples" / "vivi-hut" / "hut_int.field.toml")
    p = tmp_path / "hut.field.toml"
    p.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    doc = model.FieldDoc.load(p)
    assert doc.scene_data is None                      # single-file project
    doc.field["title"] = "Edited Title"
    doc.save()
    rt = tomllib.loads(p.read_text(encoding="utf-8"))
    assert rt["field"]["title"] == "Edited Title"
    assert "walkmesh" in rt and "camera" in rt and rt["camera"]["frame"]["back"] == 205


def test_new_doc_and_section_helpers(tmp_path):
    doc = model.FieldDoc.new(tmp_path / "x.field.toml", field_id=4005, name="X", area=12)
    doc.section("encounter").update({"scene": 67, "freq": 200})
    doc.section("music")["song"] = 9
    doc.list_section("npc").append({"name": "A", "preset": "vivi", "pos": [0, 0], "dialogue": "hi"})
    doc.save()
    rt = tomllib.loads((tmp_path / "x.field.toml").read_text(encoding="utf-8"))
    assert rt["field"]["id"] == 4005 and rt["field"]["area"] == 12
    assert rt["encounter"]["scene"] == 67 and rt["music"]["song"] == 9
    assert rt["npc"][0]["name"] == "A"


def test_protected_reason_blocks_bundled_and_installed_paths(tmp_path):
    """The save-guard: refuse to overwrite a bundled example or an installed-package file
    (the footgun that clobbered the golden hut_int example), but allow a normal user folder."""
    import ff9mapkit
    examples = Path(__file__).resolve().parents[1] / "examples"
    pkg = Path(ff9mapkit.__file__).resolve().parent
    assert model.protected_reason(examples / "vivi-hut" / "hut_int.field.toml")   # bundled example
    assert model.protected_reason(pkg / "editor" / "sneaky.field.toml")           # inside the package
    assert model.protected_reason(tmp_path / "lib" / "site-packages" / "x.field.toml")  # installed copy
    assert model.protected_reason(tmp_path / "my_room" / "room.field.toml") is None     # user's own folder
