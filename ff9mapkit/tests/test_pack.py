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


def test_check_custom_id_speaks_the_hand_copied_band_voice():
    """The shared validator the Workspace pickers collapsed onto -- so its out-of-band message must be
    BYTE-IDENTICAL to the strings they used to hand-copy, or the rewire silently changed what a user reads.
    Wave 2 completed the rewire, so the band voice now lives in ONE place (here); the fence flips to demand
    the call sites no longer hand-copy it."""
    assert pack.check_custom_id("4003") == 4003                 # a string parses
    assert pack.check_custom_id(4000) == pack.CUSTOM_ID_MIN     # so does an int; edges are inclusive
    assert pack.check_custom_id(pack.FIELD_ID_MAX) == pack.FIELD_ID_MAX

    with pytest.raises(ValueError) as under:
        pack.check_custom_id(3999)
    assert str(under.value) == "field id 3999 out of the custom band 4000–32767 (real ids are locked)"
    with pytest.raises(ValueError) as over:
        pack.check_custom_id(pack.FIELD_ID_MAX + 1, what="entry field id")
    assert str(over.value) == ("entry field id 32768 out of the custom band 4000–32767 "
                               "(real ids are locked)")
    with pytest.raises(ValueError):                             # a non-number is refused, not int()-crashed
        pack.check_custom_id("not-an-int")

    # THE REWIRE IS DONE: the New pickers must no longer hand-copy the band literal -- they validate through
    # this one validator now. If a call site re-hand-copies the string (the drift this dedupe existed to
    # kill), it reappears in shell.py and this goes red.
    shell = (Path(pack.__file__).parent / "workspace" / "shell.py").read_text(encoding="utf-8")
    assert "out of the custom band" not in shell, "the band voice is owned by check_custom_id, not hand-copied"
    assert "pack.check_custom_id" in shell, "the New pickers validate through the shared validator"


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


def test_pack_mod_name_overrides_zip_top_folder(tmp_path):
    """`--name` renames the folder INSIDE the zip — Memoria identifies a mod by its folder name, so a
    campaign staged at the default dist/ must not ship a zip that unpacks to a folder called 'dist'."""
    mod_root = tmp_path / "dist"                       # the awkward-but-common staged name
    (mod_root / "StreamingAssets").mkdir(parents=True)
    (mod_root / "DictionaryPatch.txt").write_text("FieldScene 4003 11 X TESTROOM 1073\n", encoding="utf-8")
    (mod_root / "StreamingAssets" / "x.bin").write_bytes(b"\x00")
    (mod_root / "stale.bak").write_text("skip me", encoding="utf-8")
    zip_path = pack.pack_mod(mod_root, tmp_path / "MyMod.zip", name="MyMod")
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert names and all(n.startswith("MyMod/") for n in names), names
    assert not any(n.endswith(".bak") for n in names)
    assert pack.pack_mod(mod_root, tmp_path / "plain.zip").name == "plain.zip"   # default keeps folder name


def test_new_project_writes_placeholder_art(tmp_path):
    """`new` scaffolds placeholder back.png + floor.png (valid PNGs, same canvas dims) and derives
    the walkmesh quad from the camera frame so it lines up with the placeholder floor."""
    from ff9mapkit.build import _png_size
    proj = pack.new_project("SMOKE", tmp_path, area=11)
    back, floor = proj / "art" / "back.png", proj / "art" / "floor.png"
    assert back.is_file() and floor.is_file()
    assert back.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert _png_size(back) == _png_size(floor)
    data = tomllib.loads((proj / "smoke.field.toml").read_text(encoding="utf-8"))
    assert data["walkmesh"]["quad"] != [[-1400, -2400], [1400, -2400], [1400, -800], [-1400, -800]]


def test_new_project_builds_clean(tmp_path):
    """A fresh scaffold (placeholder art) builds with no errors AND no warnings -- the from-scratch
    path is end-to-end out of the box."""
    proj = pack.new_project("SMOKE", tmp_path, area=11)
    info = build_mod([FieldProject.load(proj / "smoke.field.toml")], tmp_path / "mod")
    assert info["dictionary"][0].split()[2:4] == ["11", "SMOKE"]
    assert info["warnings"] == []
