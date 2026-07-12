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
    # Priorities is the launcher's MASTER order: it must list the actives in the SAME sequence
    prio = coop.read_ini_key(text, "Mod", "Priorities")
    assert prio == '"FF9CustomMap", "MoguriMain", "FF9Coop"'
    # idempotent
    assert not coop.ensure_folder_registered(game, "FF9Coop", out=lambda *_: None)
    assert not coop.ensure_folder_registered(game, "ff9coop", out=lambda *_: None)   # case-insensitive


# ------------------------------------------------- FolderNames <-> Priorities (THE LAUNCHER LAW)
#
# Root-caused 2026-07-12: the Memoria Launcher treats [Mod] Priorities as the MASTER mod order --
# LoadModSettings builds its list in Priorities order and UpdateModSettings rewrites FolderNames
# from it at every Play click (Memoria.Launcher/MainWindow_ModManager.cs). Every kit writer must
# therefore set BOTH keys in the same order (coop.mod_order_updates).

def _launcher_play_click(text: str) -> str:
    """Simulate the launcher's LoadModSettings + UpdateModSettings round-trip: build the mod list
    in Priorities order (FolderNames entries appended only if missing), then REWRITE FolderNames
    as the active mods in list order."""
    actives = coop.read_folder_names(text)
    active_lc = {a.lower() for a in actives}
    prio = coop.read_ini_key(text, "Mod", "Priorities") or ""
    plist = [p.strip().strip('"') for p in prio.split(",") if p.strip().strip('"')]
    mods = plist + [f for f in actives if f.lower() not in {p.lower() for p in plist}]
    new_actives = [m for m in mods if m.lower() in active_lc]
    return coop.update_ini_section(
        text, "Mod", {"FolderNames": ", ".join(f'"{n}"' for n in new_actives),
                      "Priorities": ", ".join(f'"{n}"' for n in mods)})


REQUIRED_ORDER = ["FF9CustomMap", "FF9CustomMap-hc", "FF9CustomMap-ow", "FF9CustomMap-world",
                  "MoguriMain", "MoguriVideo"]        # -world ABOVE MoguriMain (world-map override)


def test_mod_order_updates_reorders_priorities_in_step():
    ini = ('[Mod]\n'
           'FolderNames = "A", "B", "C"\n'
           'Priorities = "A", "Disabled", "B", "C"\n')
    up = coop.mod_order_updates(ini, ["C", "A", "B"])
    assert up["FolderNames"] == '"C", "A", "B"'
    # the active subsequence follows the new FolderNames order; the inactive mod keeps its slot
    assert up["Priorities"] == '"C", "Disabled", "A", "B"'


def test_mod_order_updates_new_folder_and_missing_priorities():
    up = coop.mod_order_updates('[Mod]\nFolderNames = "A"\nPriorities = "A", "Disabled"\n', ["A", "New"])
    assert up["Priorities"] == '"A", "Disabled", "New"'  # new active appended, inactive preserved
    up = coop.mod_order_updates('[Mod]\nFolderNames = "A"\n', ["A", "New"])
    assert "Priorities" not in up      # absent key stays absent: the launcher seeds it from FolderNames


def test_folder_names_only_edit_is_reverted_by_the_launcher():
    # the 2026-07-12 failure mode this whole rule guards against: Priorities wins over FolderNames
    ini = '[Mod]\nFolderNames = "A", "B"\nPriorities = "B", "A"\n'
    assert coop.read_folder_names(_launcher_play_click(ini)) == ["B", "A"]


def test_mod_order_round_trips_through_the_launcher():
    # a kit reorder written via mod_order_updates must SURVIVE the launcher's Play-click rewrite
    ini = ('[Mod]\n'
           'FolderNames = "FF9CustomMap", "MoguriMain", "MoguriVideo", "FF9CustomMap-world", '
           '"FF9CustomMap-hc", "FF9CustomMap-ow"\n'
           'Priorities = "FF9CustomMap", "MoguriMain", "SomeDisabledMod", "MoguriVideo", '
           '"FF9CustomMap-world", "FF9CustomMap-hc", "FF9CustomMap-ow"\n')
    text = coop.update_ini_section(ini, "Mod", coop.mod_order_updates(ini, REQUIRED_ORDER))
    after = _launcher_play_click(text)
    assert coop.read_folder_names(after) == REQUIRED_ORDER                      # order survived
    assert "SomeDisabledMod" in coop.read_ini_key(after, "Mod", "Priorities")   # inactive kept
    assert coop.read_folder_names(_launcher_play_click(after)) == REQUIRED_ORDER  # stable/idempotent


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
