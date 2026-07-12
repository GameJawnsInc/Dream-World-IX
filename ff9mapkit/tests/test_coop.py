"""Unit tests for the `ff9mapkit coop` setup logic (ini editing, codes, room detection).

Pure-logic tests: a fake game dir with a Memoria.ini + mod folders -- no game data,
no network, no engine.
"""

import re

import pytest

from ff9mapkit import coop

INI = (
    "[Mod]\n"
    'FolderNames = "FF9CustomMap", "MoguriMain"\n'
    'Priorities = "FF9CustomMap", "MoguriMain"\n'
    "\n"
    "[Graphics]\n"
    "Enabled = 1\n"
    "\n"
    "[Netsync]\n"
    "; co-op config\n"
    "Enabled = 0\n"
    "Role = host\n"
    "SessionCode =\n"
)


# ---------------------------------------------------------------- codes

def test_generate_code_shape():
    for _ in range(50):
        code = coop.generate_code()
        assert re.fullmatch(r"ff9-[A-Z0-9]{8}", code)


def test_generate_code_random():
    assert len({coop.generate_code() for _ in range(20)}) > 1


# ---------------------------------------------------------------- ini read

def test_read_ini_key():
    assert coop.read_ini_key(INI, "Netsync", "Role") == "host"
    assert coop.read_ini_key(INI, "netsync", "role") == "host"          # case-insensitive
    assert coop.read_ini_key(INI, "Netsync", "SessionCode") == ""
    assert coop.read_ini_key(INI, "Netsync", "Missing") is None
    assert coop.read_ini_key(INI, "Graphics", "Enabled") == "1"         # right section wins


def test_read_folder_names():
    assert coop.read_folder_names(INI) == ["FF9CustomMap", "MoguriMain"]


# ---------------------------------------------------------------- ini update

def test_update_existing_keys_in_place():
    out = coop.update_ini_section(INI, "Netsync", {"Enabled": "1", "SessionCode": "ff9-ABCD1234"})
    assert coop.read_ini_key(out, "Netsync", "Enabled") == "1"
    assert coop.read_ini_key(out, "Netsync", "SessionCode") == "ff9-ABCD1234"
    assert coop.read_ini_key(out, "Graphics", "Enabled") == "1"         # other sections untouched
    assert "; co-op config" in out                                       # comments preserved
    assert out.count("[Netsync]") == 1


def test_update_adds_missing_keys_inside_section():
    out = coop.update_ini_section(INI, "Netsync", {"RelayUrl": "ws://127.0.0.1:49201"})
    assert coop.read_ini_key(out, "Netsync", "RelayUrl") == "ws://127.0.0.1:49201"
    # the new key must land INSIDE [Netsync], i.e. Memoria's parser (section-scoped) can see it
    assert out.index("[Netsync]") < out.index("RelayUrl")


def test_update_key_added_before_next_section():
    ini = "[Netsync]\nEnabled = 0\n\n[Lang]\nEnabled = 0\n"
    out = coop.update_ini_section(ini, "Netsync", {"Role": "client"})
    assert out.index("Role = client") < out.index("[Lang]")
    assert coop.read_ini_key(out, "Lang", "Enabled") == "0"             # [Lang]'s key untouched


def test_update_creates_missing_section():
    ini = "[Mod]\nFolderNames = \"X\"\n"
    out = coop.update_ini_section(ini, "Netsync", {"Enabled": "1", "Role": "host"})
    assert coop.read_ini_key(out, "Netsync", "Enabled") == "1"
    assert coop.read_ini_key(out, "Netsync", "Role") == "host"


def test_update_preserves_crlf():
    ini = INI.replace("\n", "\r\n")
    out = coop.update_ini_section(ini, "Netsync", {"Enabled": "1"})
    assert "\r\n" in out
    assert "\n" not in out.replace("\r\n", "")                          # no bare-\n endings introduced
    assert coop.read_ini_key(out, "Netsync", "Enabled") == "1"


def test_update_can_blank_a_value():
    ini = "[Netsync]\nRelayUrl = ws://127.0.0.1:49201\n"
    out = coop.update_ini_section(ini, "Netsync", {"RelayUrl": ""})
    assert coop.read_ini_key(out, "Netsync", "RelayUrl") == ""


# ---------------------------------------------------------------- fake install fixtures

@pytest.fixture
def game(tmp_path):
    (tmp_path / "Memoria.ini").write_text(INI, encoding="utf-8")
    for folder in ("FF9CustomMap", "MoguriMain"):
        d = tmp_path / folder
        d.mkdir()
    (tmp_path / "FF9CustomMap" / "DictionaryPatch.txt").write_text(
        "FieldScene 30000 23 TESTROOM TESTROOM 1073\n", encoding="utf-8")
    return tmp_path


def test_find_registered_field(game):
    assert coop.find_registered_field(game, 30000) == "FF9CustomMap"
    assert coop.find_registered_field(game, 30003) is None
    # 3000 must not match the "FieldScene 30000 " line (space-delimited needle)
    assert coop.find_registered_field(game, 3000) is None


def test_find_registered_field_sees_coop_folder_even_unregistered(game):
    d = game / coop.COOP_MOD
    d.mkdir()
    (d / "DictionaryPatch.txt").write_text(
        f"FieldScene {coop.COOP_FIELD} 23 COOP COOP 1073\n", encoding="utf-8")
    assert coop.find_registered_field(game, coop.COOP_FIELD) == coop.COOP_MOD


def test_ensure_folder_registered(game):
    changed = coop.ensure_folder_registered(game, "FF9Coop", out=lambda *_: None)
    assert changed
    text = (game / "Memoria.ini").read_text(encoding="utf-8")
    assert coop.read_folder_names(text) == ["FF9CustomMap", "MoguriMain", "FF9Coop"]  # appended LAST
    prio = coop.read_ini_key(text, "Mod", "Priorities")
    assert "FF9Coop" in prio
    # idempotent
    assert not coop.ensure_folder_registered(game, "FF9Coop", out=lambda *_: None)
    assert not coop.ensure_folder_registered(game, "ff9coop", out=lambda *_: None)   # case-insensitive


def test_write_netsync_backs_up(game):
    backup = coop.write_netsync(game, {"Enabled": "1", "Role": "client"}, out=lambda *_: None)
    assert backup.is_file()
    assert backup.read_text(encoding="utf-8") == INI                    # backup = pre-edit content
    text = (game / "Memoria.ini").read_text(encoding="utf-8")
    assert coop.read_ini_key(text, "Netsync", "Enabled") == "1"
    assert coop.read_ini_key(text, "Netsync", "Role") == "client"


def test_write_netsync_requires_ini(tmp_path):
    with pytest.raises(FileNotFoundError):
        coop.write_netsync(tmp_path, {"Enabled": "1"}, out=lambda *_: None)
