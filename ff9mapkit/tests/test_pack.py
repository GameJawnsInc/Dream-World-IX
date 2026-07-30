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


@pytest.mark.parametrize("pitch", [15.0, 20.0, 48.0])
def test_new_project_quad_matches_its_own_camera(tmp_path, pitch):
    """THE USER-VISIBLE CONSEQUENCE: the scaffold's walkmesh must land on the canvas rows its OWN
    toml declares. `new --pitch 15` used to swallow the frame_floor failure and fall back to a
    hard-coded quad, so the room looked fine and shipped a mesh that did not match its camera."""
    from ff9mapkit.scene import cam as C, guide as G
    proj = pack.new_project("LOWCAM", tmp_path, pitch=pitch, area=11)
    data = tomllib.loads((proj / "lowcam.field.toml").read_text(encoding="utf-8"))
    cfg, quad = data["camera"], data["walkmesh"]["quad"]
    assert quad != [[-1400, -2400], [1400, -2400], [1400, -800], [-1400, -800]]   # the old fallback
    cam = G.make_camera(cfg["pitch"], cfg["distance"], fov_x_deg=cfg["fov"])
    rows = [C.to_canvas((x, 0, z), cam)[1] for x, z in quad]                      # BL, BR, FR, FL
    assert max(abs(r - cfg["frame"]["back"]) for r in rows[:2]) < 1.0
    assert max(abs(r - cfg["frame"]["front"]) for r in rows[2:]) < 1.0
    assert quad[2][1] < data["player"]["spawn"][1] < quad[0][1]                   # spawn is inside


def test_new_project_refuses_an_unframeable_camera(tmp_path):
    """An unframeable pitch must REFUSE, not scaffold a plausible-looking guess -- and must leave no
    half-made project behind. At pitch 2 the horizon (Y~208) really is below the template back row
    205, so no floor quad exists; the message has to say which knob to turn."""
    with pytest.raises(ValueError, match="cannot frame"):
        pack.new_project("LEVELCAM", tmp_path, pitch=2.0, area=11)
    assert not (tmp_path / "LEVELCAM").exists()
    pack.new_project("LEVELCAM", tmp_path, pitch=15.0, area=11)      # the named fix works
    assert (tmp_path / "LEVELCAM" / "levelcam.field.toml").is_file()


def test_new_project_builds_clean(tmp_path):
    """A fresh scaffold (placeholder art) builds with no errors AND no problem warnings -- the
    from-scratch path is end-to-end out of the box. The scaffold's entry_settle = "auto" surfaces
    its computed hold as ONE informational line (by design); anything else is a regression."""
    proj = pack.new_project("SMOKE", tmp_path, area=11)
    info = build_mod([FieldProject.load(proj / "smoke.field.toml")], tmp_path / "mod")
    assert info["dictionary"][0].split()[2:4] == ["11", "SMOKE"]
    settle, rest = [], []
    for w in info["warnings"]:
        (settle if 'entry_settle = "auto" ->' in w else rest).append(w)
    assert len(settle) == 1 and "frames" in settle[0]   # the auto hold resolved (not the fallback path)
    assert rest == []
