"""Phase-5 validation: field-id allocation, scaffolding, and packaging."""

from __future__ import annotations

import tomllib
import zipfile
from pathlib import Path

import pytest

from ff9mapkit import pack
from ff9mapkit.build import FieldProject, build_mod


def test_suggest_base_deterministic_and_in_range():
    a = pack.suggest_base("Vivi's Return")
    b = pack.suggest_base("Vivi's Return")
    assert a == b
    assert pack.CUSTOM_ID_MIN <= a <= pack.CUSTOM_ID_MAX
    assert a % pack.BLOCK_SIZE == pack.CUSTOM_ID_MIN % pack.BLOCK_SIZE  # block-aligned


def test_suggest_ids_range_check():
    assert pack.suggest_ids(4000, 3) == [4000, 4001, 4002]
    with pytest.raises(ValueError):
        pack.suggest_ids(3999, 1)
    with pytest.raises(ValueError):
        pack.suggest_ids(pack.CUSTOM_ID_MAX, 5)


def test_new_project_scaffold(tmp_path):
    proj = pack.new_project("MY_ROOM", tmp_path, area=11)
    toml = proj / "my_room.field.toml"
    assert toml.is_file()
    assert (proj / "art" / "README.txt").is_file()
    data = tomllib.loads(toml.read_text(encoding="utf-8"))
    assert data["field"]["name"] == "MY_ROOM"
    assert data["field"]["area"] == 11
    assert data["field"]["id"] == pack.suggest_base("MY_ROOM")


def test_pack_mod_zips_built_mod(tmp_path):
    example = Path(__file__).parents[1] / "examples" / "vivi-hut" / "hut_int.field.toml"
    mod_root = tmp_path / "FF9CustomMap"
    build_mod([FieldProject.load(example)], mod_root, mod_name="FF9CustomMap")
    zip_path = pack.pack_mod(mod_root, tmp_path / "mod.zip")
    assert zip_path.is_file()
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    # archive is rooted at the mod folder name and contains the key registration files
    assert any(n.endswith("DictionaryPatch.txt") for n in names)
    assert any(n.endswith("EVT_HUT_INT.eb.bytes") for n in names)
    assert all(n.startswith("FF9CustomMap/") for n in names)
