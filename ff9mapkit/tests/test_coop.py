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
BOM = bytes((0xEF, 0xBB, 0xBF))          # a UTF-8 byte-order mark (THE BOM LAW: coop.read_ini_text)
NL = chr(10)


# ---------------------------------------------------------------- codes

def test_generate_code_shape():
    for _ in range(50):
        code = coop.generate_code()
        assert re.fullmatch(r"ff9-[A-Z0-9]{8}", code)


def test_generate_code_random():
    assert len({coop.generate_code() for _ in range(20)}) > 1


# ---------------------------------------------------------------- code validation (ini injection)
#
# The session code is written as a whole ini line ("SessionCode = <code>"), and Memoria's parser is a
# sequential LINE reader, last-write-wins per (section, key), that re-enters a section on a repeated
# header. So an embedded newline in a pasted "invite" becomes REAL extra [Netsync] keys -- the sender
# can grant themselves every party slot (GuestSlots) or re-point RelayUrl at their own relay.
POISONED_CODE = "ff9-AAAA0000\nGuestSlots = 15\nRelayUrl = ws://attacker.example:1234\n;"


def test_validate_code_accepts_generated_codes():
    for _ in range(50):
        code = coop.generate_code()
        assert coop.validate_code(code) == code     # returns it UNCHANGED -- pairing is literal


def test_validate_code_accepts_hand_set_forms():
    # case-insensitive prefix (the docs promise case-insensitive pairing), prefix optional, and the
    # length is a band not exactly 8 -- `coop host <code>` is documented as an override
    for good in ("ff9-ABCD1234", "FF9-abcd1234", "Ff9-AbCd1234", "ABCD1234", "abcd1234",
                 "ff9-A", "x", "ff9-" + "A" * 32):
        assert coop.validate_code(good) == good     # no upper-casing, no prefix insertion


def test_validate_code_rejects_newlines():
    for bad in (POISONED_CODE, "ff9-ABCD1234\n", "ff9-ABCD1234\r\nEnabled = 1",
                "ff9-ABCD\rGuestSlots = 15", "ff9-AB\x0bCD", "ff9-AB\x85CD"):
        with pytest.raises(ValueError):
            coop.validate_code(bad)


def test_validate_code_rejects_ini_metacharacters():
    # nothing that could open a second key, a comment, or a section header on the written line
    for bad in ("ff9-ABCD=1234", "ff9-ABCD;x", "ff9-ABCD#x", "ff9-[Netsync]", "ff9-ABCD]",
                "ff9-ABCD 1234", "ff9-ABCD\t1234", "ff9 ABCD", 'ff9-"ABCD"', "ff9-ABCD\x00"):
        with pytest.raises(ValueError):
            coop.validate_code(bad)


def test_validate_code_rejects_empty_and_overlong():
    # empty means "no code given" -- a CALLER concept (host mints one, join refuses with its own
    # message), never a valid code, so the validator refuses it and call sites guard with `if code`
    for bad in ("", "ff9-", "ff9-" + "A" * 33, None, 12345678):
        with pytest.raises(ValueError):
            coop.validate_code(bad)


def test_validate_code_message_names_the_shape():
    with pytest.raises(ValueError, match="ff9-XXXXXXXX"):
        coop.validate_code("ff9-ABCD=1234")


# ---------------------------------------------------------------- play style (s37)

def test_parse_guest_slots():
    # party POSITIONS 1-4 (as the in-game menu shows them) -> the engine bitmask
    assert coop.parse_guest_slots("1") == 1
    assert coop.parse_guest_slots("2") == 2
    assert coop.parse_guest_slots("2,3") == 6
    assert coop.parse_guest_slots("1, 4") == 9
    assert coop.parse_guest_slots("all") == 15
    for none_ish in ("0", "none", "off", "", "NONE"):
        assert coop.parse_guest_slots(none_ish) == 0
    for bad in ("5", "x", "1-2", "-1"):
        with pytest.raises(ValueError):
            coop.parse_guest_slots(bad)


def test_format_guest_slots():
    assert coop.format_guest_slots(0) == "none (spectate)"
    assert coop.format_guest_slots(2) == "2"
    assert coop.format_guest_slots(6) == "2, 3"
    assert coop.format_guest_slots(15) == "1, 2, 3, 4"


def test_parse_ghost_as():
    assert coop.parse_ghost_as("auto") == "auto"
    assert coop.parse_ghost_as("Vivi") == "vivi"
    assert coop.parse_ghost_as("DAGGER") == "dagger"       # the engine's garnet alias
    assert coop.parse_ghost_as("Moogle") == "moogle"       # [ff9mapkit netsync s139] rig row 8 (an older engine: undressed)
    # [ff9mapkit netsync s140] the owner's 8-11 rows (rigs 9-12): "their own models" (an engine before s140: undressed)
    assert [coop.parse_ghost_as(n) for n in ("Cinna", "MARCUS", " blank ", "Beatrix")] == ["cinna", "marcus", "blank",
                                                                                           "beatrix"]
    for off_ish in ("", "off", "none", "0"):
        assert coop.parse_ghost_as(off_ish) == ""
    for no_rig in ("kuja", "garland", "mog"):
        with pytest.raises(ValueError):
            coop.parse_ghost_as(no_rig)                    # no rig row (not a NameToRig name) -> refuse up front


def test_playstyle_updates_only_what_was_given():
    assert coop.playstyle_updates() == {}                  # nothing given -> nothing clobbered
    assert coop.playstyle_updates(guest_wait=0) == {"GuestWaitMs": "0"}
    full = coop.playstyle_updates("2", 30, "auto", True)
    assert full == {"GuestSlots": "2", "GuestWaitMs": "30000",
                    "GhostAs": "auto", "FollowHost": "1"}
    assert "Diorama" not in full                           # the knob is GONE (s42) -- never written
    assert coop.playstyle_updates(follow_host=False) == {"FollowHost": "0"}
    with pytest.raises(ValueError):
        coop.playstyle_updates(guest_wait=-1)


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


# -------------------------------------------- ini update: the control-character fence (defense in depth)
#
# validate_code() fences the session code at the door; this fences the WRITER, so the injection bug
# class cannot come back through the next bare string someone wires into an ini key. update_ini_section
# renders each pair as f"{k} = {v}" and joins with newlines, so an embedded \n is not a funny value --
# it is extra [Netsync] keys, and Memoria's parser is last-write-wins so the spliced key WINS.
# REJECT, never strip: a stripped value writes a subtly wrong setting the user never asked for and
# cannot see, whereas a raise is loud and the caller can say something useful.

def test_update_refuses_a_newline_in_a_replaced_value():
    # the in-place branch: SessionCode already exists in INI, so its line is REWRITTEN
    with pytest.raises(ValueError):
        coop.update_ini_section(INI, "Netsync", {"SessionCode": "ff9-AAAA0000\nGuestSlots = 15"})


def test_update_refuses_a_newline_in_an_appended_value():
    # the append branch builds its line in flush_pending(), a DIFFERENT code path from the rewrite
    # above (PeerAddress is absent from INI). Both are pinned, so the contract holds wherever the
    # check happens to live.
    with pytest.raises(ValueError):
        coop.update_ini_section(INI, "Netsync", {"PeerAddress": "192.168.1.50\nGuestSlots = 15"})


def test_update_refuses_a_carriage_return_in_a_value():
    # \r alone is what .NET's StreamReader.ReadLine breaks on -- Python's splitlines() hides that
    for updates in ({"Enabled": "1\rRole = client"},                     # replace
                    {"PeerAddress": "192.168.1.50\rGuestSlots = 15"}):   # append
        with pytest.raises(ValueError):
            coop.update_ini_section(INI, "Netsync", updates)


def test_update_refuses_every_control_character_in_a_value():
    # THE INVARIANT, stated literally: there is no value carrying a control character for which this
    # function produces output at all -- so no line it emits can ever carry a raw break. The set is
    # the UNION of what .NET's ReadLine and Python's str.splitlines() call a line break, plus the rest
    # of C0 and DEL (both parsers trim around '=', so a tab is silently not the value you wrote).
    for ch in [chr(c) for c in range(0x20)] + ["\x7f", "\x85", chr(0x2028), chr(0x2029)]:
        for updates in ({"SessionCode": "ff9-ABCD" + ch + "1234"},   # replace an existing key
                        {"PeerAddress": "192.168.1.50" + ch},        # append inside the section
                        {"Enabled": ch}):
            with pytest.raises(ValueError):
                coop.update_ini_section(INI, "Netsync", updates)
            with pytest.raises(ValueError):                          # + the append-the-section branch
                coop.update_ini_section('[Mod]\nFolderNames = "X"\n', "Netsync", updates)


def test_update_refuses_a_newline_in_a_key():
    # the same bug through the other door -- the key half builds the same line
    with pytest.raises(ValueError):
        coop.update_ini_section(INI, "Netsync", {"Enabled = 1\nGuestSlots": "15"})


def test_update_refuses_a_structurally_broken_key():
    # '=' lands a DIFFERENT (shorter) key in the file than the caller asked for; a leading ';'/'#'
    # comments the whole setting out; brackets can open a section header. All silent, which is
    # exactly what reject-over-strip exists for.
    for bad_key in ("Enabled=x", "[Netsync]", "Enabled]", ";Enabled", "#Enabled", "", "   ", None):
        with pytest.raises(ValueError):
            coop.update_ini_section(INI, "Netsync", {bad_key: "1"})


def test_update_refusal_names_the_key_and_escapes_the_payload():
    with pytest.raises(ValueError) as exc:
        coop.update_ini_section(INI, "Netsync", {"SessionCode": "ff9-A\nGuestSlots = 15"})
    msg = str(exc.value)
    assert "SessionCode" in msg      # which key -- the caller has to be able to say something useful
    assert "\\n" in msg              # repr()'d, so the escape is what the user reads...
    assert "\n" not in msg           # ...and the payload cannot fake extra lines in the terminal


def test_update_still_round_trips_a_legitimate_update():
    # the positive control: the fence must be invisible to every real caller. Same assertions as
    # test_update_existing_keys_in_place, plus the values _setup() actually writes -- and an int,
    # since a non-str value is rendered with str() and vetted AFTER (callers pass str(int) already).
    out = coop.update_ini_section(INI, "Netsync", {
        "Enabled": "1", "SessionCode": "ff9-ABCD1234", "RelayUrl": "ws://127.0.0.1:49201",
        "PeerAddress": "192.168.1.50", "GhostAs": "auto", "TargetField": 30003})
    assert coop.read_ini_key(out, "Netsync", "Enabled") == "1"
    assert coop.read_ini_key(out, "Netsync", "SessionCode") == "ff9-ABCD1234"
    assert coop.read_ini_key(out, "Netsync", "RelayUrl") == "ws://127.0.0.1:49201"
    assert coop.read_ini_key(out, "Netsync", "TargetField") == "30003"      # int -> "30003"
    assert coop.read_ini_key(out, "Netsync", "GhostAs") == "auto"
    assert coop.read_ini_key(out, "Graphics", "Enabled") == "1"             # other sections untouched
    assert "; co-op config" in out                                          # comments preserved
    assert out.count("[Netsync]") == 1


def test_update_still_writes_quoted_mod_lists():
    # the fence is control-characters-only, NOT a charset allowlist: [Mod] values legitimately carry
    # quotes, commas and spaces, and THE LAUNCHER LAW's round-trip depends on them surviving verbatim
    out = coop.update_ini_section(INI, "Mod", coop.mod_order_updates(INI, ["FF9CustomMap", "FF9Coop"]))
    assert coop.read_ini_key(out, "Mod", "FolderNames") == '"FF9CustomMap", "FF9Coop"'


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


def test_ensure_folder_registered_backs_up(game):
    # this is the FIRST ini mutation of a default `coop host`/`coop join` run -- must not
    # be the one write in the module with no recovery point (contrast write_netsync).
    before = (game / "Memoria.ini").read_text(encoding="utf-8")
    assert coop.ensure_folder_registered(game, "FF9Coop", out=lambda *_: None)
    backups = list(game.glob("Memoria.ini.coop-bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == before
    # a no-op call (already registered) makes no backup at all
    assert not coop.ensure_folder_registered(game, "FF9Coop", out=lambda *_: None)
    assert len(list(game.glob("Memoria.ini.coop-bak-*"))) == 1


def test_ensure_folder_registered_no_tmp_file_left_behind(game):
    coop.ensure_folder_registered(game, "FF9Coop", out=lambda *_: None)
    assert not (game / "Memoria.ini.tmp").exists()


def test_bom_ini_keeps_the_mod_list(game):
    # THE BOM LAW (studies/coop-review/REVIEW.md 1.3): a Notepad / Notepad++ BOM glued U+FEFF to the line-1 [Mod]
    # header, read_folder_names saw [], and the first co-op setup appended a SECOND [Mod] with FolderNames = "FF9Coop"
    # -- which the engine (last write wins) loaded alone. The existing folders must survive, in one [Mod] section.
    ini = game / "Memoria.ini"
    ini.write_bytes(b"\xef\xbb\xbf" + INI.encode("utf-8"))
    assert coop.read_folder_names(coop.read_ini_text(ini)) == ["FF9CustomMap", "MoguriMain"]
    assert coop.ensure_folder_registered(game, "FF9Coop", out=lambda *_: None)
    raw = ini.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "the file's BOM was not kept"
    assert raw.count(b"\xef\xbb\xbf") == 1
    text = raw[3:].decode("utf-8")
    assert text.count("[Mod]") == 1
    assert coop.read_folder_names(text) == ["FF9CustomMap", "MoguriMain", "FF9Coop"]
    assert coop.read_ini_key(text, "Mod", "Priorities") == '"FF9CustomMap", "MoguriMain", "FF9Coop"'


def test_bom_ini_netsync_write_keeps_bom_and_sections(game):
    ini = game / "Memoria.ini"
    ini.write_bytes(b"\xef\xbb\xbf" + INI.encode("utf-8"))
    coop.write_netsync(game, {"Enabled": "1"}, out=lambda *_: None)
    raw = ini.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") and raw.count(b"\xef\xbb\xbf") == 1
    text = raw[3:].decode("utf-8")
    assert text.count("[Mod]") == 1 and text.count("[Netsync]") == 1
    assert coop.read_ini_key(text, "Netsync", "Enabled") == "1"
    assert coop.read_folder_names(text) == ["FF9CustomMap", "MoguriMain"]


def test_no_bom_ini_stays_without_bom(game):
    coop.ensure_folder_registered(game, "FF9Coop", out=lambda *_: None)
    assert not (game / "Memoria.ini").read_bytes().startswith(b"\xef\xbb\xbf")


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
    assert not (game / "Memoria.ini.tmp").exists()   # staged through fsutil.atomic_write_text, not left behind


def test_write_netsync_requires_ini(tmp_path):
    with pytest.raises(FileNotFoundError):
        coop.write_netsync(tmp_path, {"Enabled": "1"}, out=lambda *_: None)


def test_write_netsync_refusal_touches_nothing(game):
    # the fence runs BEFORE the backup, so a rejected write leaves no trace at all -- not the edited
    # ini, not a stray snapshot, not a staged temp file
    with pytest.raises(ValueError):
        coop.write_netsync(game, {"SessionCode": "ff9-A\nGuestSlots = 15"}, out=lambda *_: None)
    assert (game / "Memoria.ini").read_text(encoding="utf-8") == INI
    assert not list(game.glob("Memoria.ini.coop-bak-*"))
    assert not (game / "Memoria.ini.tmp").exists()


def test_show_config_reads_playstyle_in_human_terms(game):
    coop.write_netsync(game, {"Enabled": "1", "Role": "host", "SessionCode": "ff9-TESTCODE",
                              "RelayUrl": "ws://127.0.0.1:49201", "TargetField": "0",
                              **coop.playstyle_updates("2,3", 30, "auto", True)},
                       out=lambda *_: None)
    lines = []
    assert coop.show_config(game, out=lines.append) == 0
    text = "\n".join(lines)
    assert "co-op:       ON" in text
    assert "slot(s) 2, 3" in text
    assert "30s per guest turn" in text
    assert "auto (the party member they command)" in text
    assert "follow-host: ON" in text
    assert "diorama" not in text            # the knob is GONE (s42): follow-host implies the diorama
    assert "self-dress" not in text         # [ff9mapkit netsync s140] SelfDress named only when switched off
    coop.write_netsync(game, {"SelfDress": "0"}, out=lambda *_: None)
    lines = []
    assert coop.show_config(game, out=lines.append) == 0
    assert any(ln.startswith("  self-dress:  OFF ([Netsync] SelfDress=0") for ln in lines), lines


def test_coop_join_never_writes_diorama_key(game):
    # The knob was removed with the s42 engine: no argv accepts it, and setup must never write it.
    rc = coop.run(_cli_args(action="join", game=str(game), code="ff9-ABCD1234",
                            lan="192.168.1.50", no_room=True), out=lambda *_: None)
    assert rc == 0
    text = (game / "Memoria.ini").read_text(encoding="utf-8")
    assert coop.read_ini_key(text, "Netsync", "Diorama") is None


# ------------------------------------------------- host/join end-to-end (run -> _setup)
#
# `coop host` must force FollowHost = 0 in the written ini (a host must never follow its guest --
# FollowHost fires regardless of role, so a stale selftest value would drag the host to the guest's
# field). playstyle_updates() alone can't prove this: the force lives in _setup's role branch.

def _cli_args(**kw):
    import types
    base = dict(game=None, code=None, port=49201)     # only the attrs run()/_setup() read directly
    base.update(kw)
    return types.SimpleNamespace(**base)


def test_coop_host_forces_follow_host_off(game, monkeypatch):
    monkeypatch.setattr(coop, "_copy_clipboard", lambda _text: False)
    rc = coop.run(_cli_args(action="host", game=str(game), lan="", no_room=True),
                  out=lambda *_: None)
    assert rc == 0
    text = (game / "Memoria.ini").read_text(encoding="utf-8")
    assert coop.read_ini_key(text, "Netsync", "FollowHost") == "0"
    assert coop.read_ini_key(text, "Netsync", "Role") == "host"
    assert coop.read_ini_key(text, "Netsync", "Enabled") == "1"


def test_coop_host_refuses_an_explicit_follow_host(game, monkeypatch):
    # --follow-host on a HOST is refused before anything is written. It used to be honored ("if ever
    # explicitly wanted"), but the engine's follow tick has no role check: in the b20 smoke test a host
    # ticked to follow and its following guest bounced between fields 250 and 350 every few seconds.
    monkeypatch.setattr(coop, "_copy_clipboard", lambda _text: False)
    before = (game / "Memoria.ini").read_text(encoding="utf-8")
    lines = []
    rc = coop.run(_cli_args(action="host", game=str(game), lan="", no_room=True, follow_host="on"),
                  out=lines.append)
    assert rc == 2
    assert any("joining side" in ln for ln in lines), lines
    assert (game / "Memoria.ini").read_text(encoding="utf-8") == before, "nothing may be written"
    with pytest.raises(ValueError):
        coop.playstyle_updates(follow_host=True, role="host")
    assert coop.playstyle_updates(follow_host=False, role="host") == {"FollowHost": "0"}
    assert coop.playstyle_updates(follow_host=True, role="client") == {"FollowHost": "1"}


def test_coop_join_with_a_ghost_pick_warns_the_guest_already_wears_the_hosts(game, monkeypatch):
    # [ff9mapkit netsync s140] the guest dresses itself from the HOST's GhostAs; a guest-side GhostAs only re-dresses the
    # guest's view of the host (the s138 client rule, kept byte for byte), so the same pick on both machines shows the
    # guest two of that character. A joiner that names one is told (and the value is still written: a warning, not a
    # refusal -- the Workspace's shared play-style panel passes the same argv to host and join); 'off' and hosting are not.
    monkeypatch.setattr(coop, "_copy_clipboard", lambda _text: False)

    def run(**kw):
        lines = []
        assert coop.run(_cli_args(game=str(game), no_room=True, **kw), out=lines.append) == 0
        return [ln for ln in lines if "visitor: NOTE" in ln]
    note = run(action="join", code="ff9-ABCD1234", lan="192.168.1.50", ghost_as="vivi")
    assert len(note) == 1 and "two of that character" in note[0] and "SelfDress=0" in note[0], note
    assert coop.read_ini_key((game / "Memoria.ini").read_text(encoding="utf-8"), "Netsync", "GhostAs") == "vivi"
    assert len(run(action="join", code="ff9-ABCD1234", lan="192.168.1.50", ghost_as="auto")) == 1
    assert run(action="join", code="ff9-ABCD1234", lan="192.168.1.50", ghost_as="off") == []
    assert run(action="join", code="ff9-ABCD1234", lan="192.168.1.50") == []
    assert run(action="host", lan="", ghost_as="vivi") == []


def test_coop_join_does_not_force_follow_host(game):
    rc = coop.run(_cli_args(action="join", game=str(game), code="ff9-ABCD1234",
                            lan="192.168.1.50", no_room=True), out=lambda *_: None)
    assert rc == 0
    text = (game / "Memoria.ini").read_text(encoding="utf-8")
    assert coop.read_ini_key(text, "Netsync", "FollowHost") is None     # join leaves it alone
    assert coop.read_ini_key(text, "Netsync", "Role") == "client"
    assert coop.read_ini_key(text, "Netsync", "PeerAddress") == "192.168.1.50"


# ------------------------------------------------- the ini-injection fence, end to end
#
# THE test of the fix: the documented `ff9mapkit coop join "<code your friend sent>"` must refuse a
# poisoned invite, and it must refuse it BEFORE ensure_room() and BEFORE write_netsync() -- so the
# ini is not merely correct afterwards, it is untouched (no backup, no atomic rewrite).

def test_coop_join_refuses_a_poisoned_code_and_leaves_the_ini_untouched(game):
    lines = []
    rc = coop.run(_cli_args(action="join", game=str(game), code=POISONED_CODE,
                            lan="192.168.1.50", no_room=True), out=lines.append)
    assert rc == 2
    assert any("bad session code" in ln for ln in lines)
    text = (game / "Memoria.ini").read_text(encoding="utf-8")
    assert text == INI                                   # byte-identical: we bailed before any write
    assert "GuestSlots" not in text                      # the injected key never landed
    assert "attacker.example" not in text                # the relay was never re-pointed
    assert text.count("[Netsync]") == 1                  # no re-opened section (engine = last-wins)
    assert not list(game.glob("Memoria.ini.coop-bak-*"))  # not even the backup ran


def test_coop_host_refuses_a_poisoned_override_code(game, monkeypatch):
    # the host's optional override rides the same code argument -- same fence, same exit
    monkeypatch.setattr(coop, "_copy_clipboard", lambda _text: False)
    lines = []
    rc = coop.run(_cli_args(action="host", game=str(game), code=POISONED_CODE, lan="",
                            no_room=True), out=lines.append)
    assert rc == 2
    assert (game / "Memoria.ini").read_text(encoding="utf-8") == INI


def test_coop_host_replaces_an_unusable_stored_code(game, monkeypatch):
    # `coop host` re-reads SessionCode to keep a session's code stable across re-runs. A stored value
    # that no longer validates (hand-edited, or the residue of a poisoned ini) is treated as ABSENT --
    # mint a fresh one rather than crash the setup or re-write someone else's value verbatim.
    monkeypatch.setattr(coop, "_copy_clipboard", lambda _text: False)
    ini = (game / "Memoria.ini")
    ini.write_text(INI.replace("SessionCode =\n", "SessionCode = not a code!\n"), encoding="utf-8")
    lines = []
    rc = coop.run(_cli_args(action="host", game=str(game), lan="", no_room=True), out=lines.append)
    assert rc == 0
    minted = coop.read_ini_key(ini.read_text(encoding="utf-8"), "Netsync", "SessionCode")
    assert re.fullmatch(r"ff9-[A-Z0-9]{8}", minted)
    assert any("ignoring the stored SessionCode" in ln for ln in lines)


def test_coop_host_keeps_a_valid_stored_code(game, monkeypatch):
    # the flip side: a good stored code still survives a re-run (the fence must not churn codes). INI's Role is host, so
    # this is also THE OWN-CODE LAW's migration row: a pre-s154 host's code is adopted as its own (HostSessionCode)
    monkeypatch.setattr(coop, "_copy_clipboard", lambda _text: False)
    ini = (game / "Memoria.ini")
    ini.write_text(INI.replace("SessionCode =\n", "SessionCode = ff9-KEEPME12\n"), encoding="utf-8")
    assert coop.run(_cli_args(action="host", game=str(game), lan="", no_room=True),
                    out=lambda *_: None) == 0
    assert coop.read_ini_key(ini.read_text(encoding="utf-8"), "Netsync", "SessionCode") == "ff9-KEEPME12"
    assert coop.read_ini_key(ini.read_text(encoding="utf-8"), "Netsync", "HostSessionCode") == "ff9-KEEPME12"


# ------------------------------------------------- THE OWN-CODE LAW (s154): a code this PC JOINED with is never its own
#
# One ini key used to carry two meanings: the engine DIALS [Netsync] SessionCode (a host's own code, a guest's friend's
# invite after `coop join`), and `coop host` re-read it as "this PC's own code". So a PC that joined a friend and later
# hosted re-published the friend's code: anyone holding that invite walked into its game, and two hosts on one code
# evicted each other (studies/coop-review/REVIEW.md appendix 25). The own code now lives in HostSessionCode.

def _ns(*lines):
    return "[Netsync]\n" + "".join(ln + "\n" for ln in lines)


# (the [Netsync] body, the expected (code, why, key), the failure the row names)
OWN_ROWS = [
    (_ns("HostSessionCode = ff9-MINE0001", "Role = client", "SessionCode = ff9-FRIEND01"),
     ("ff9-MINE0001", "own", "HostSessionCode"), "a former guest hosts on its friend's invite (THE bug)"),
    (_ns("Role = client", "SessionCode = ff9-FRIEND01"),
     (None, "joined", "SessionCode"), "a pre-s154 guest ini's invite is adopted as this PC's own code"),
    (_ns("Role = host", "SessionCode = ff9-MINE0001"),
     ("ff9-MINE0001", "migrated", "SessionCode"), "an existing host's code churns at the upgrade"),
    (_ns("Enabled = 0", "Role =  Host ", "SessionCode = ff9-MINE0001"),
     ("ff9-MINE0001", "migrated", "SessionCode"), "`coop off` or a hand-cased Role (the engine lowercases) forgets it"),
    (_ns("SessionCode = ff9-MINE0001"),
     (None, "unowned", "SessionCode"), "a code under no Role is adopted (the engine's default role is selftest)"),
    (_ns("Role = selftest", "SessionCode = ff9-BENCH001"),
     (None, "unowned", "SessionCode"), "a bench's code is re-published as a host's"),
    (_ns("Role = CLIENT", "SessionCode = ff9-FRIEND01"),
     (None, "joined", "SessionCode"), "a hand-cased client Role reads as a host's code"),
    (_ns("HostSessionCode = not a code!", "Role = client", "SessionCode = ff9-FRIEND01"),
     (None, "unusable", "HostSessionCode"), "a bad own key falls back to the invite"),
    (_ns("Role = host", "SessionCode = not a code!"),
     (None, "unusable", "SessionCode"), "a poisoned stored code is re-written verbatim"),
    (_ns("Role = host", "SessionCode = ff9-MINE0001", "HostSessionCode ="),
     ("ff9-MINE0001", "migrated", "SessionCode"), "an empty own key blocks the migration"),
    (_ns("Role = client", "SessionCode =", "HostSessionCode = ff9-MINE0001"),
     ("ff9-MINE0001", "own", "HostSessionCode"), "a LAN join (SessionCode blanked) loses the host's code"),
    (_ns("HostSessionCode = ff9-OLD00001", "Role = client", "HostSessionCode = ff9-NEW00001"),
     ("ff9-NEW00001", "own", "HostSessionCode"), "the kit vets a copy the file does not use (last key wins)"),
    (_ns("Role = host"),
     (None, "none", "SessionCode"), "an empty ini is treated as a code"),
    (_ns("; HostSessionCode = ff9-MINE0001", "Role = client", "SessionCode = ff9-FRIEND01"),
     (None, "joined", "SessionCode"), "a commented-out own key is read as live"),
    ("[Mod]\nHostSessionCode = ff9-MINE0001\n\n" + _ns("Role = client", "SessionCode = ff9-FRIEND01"),
     (None, "joined", "SessionCode"), "another section's HostSessionCode is read as this PC's"),
]


@pytest.mark.parametrize("text,want,failure", OWN_ROWS, ids=[r[2] for r in OWN_ROWS])
def test_own_host_code_rule(text, want, failure):
    assert coop.own_host_code(text) == want, failure


@pytest.fixture
def no_clip(monkeypatch):
    monkeypatch.setattr(coop, "_copy_clipboard", lambda _text: False)     # never the developer's clipboard


def _coop(game, action, code=None, **kw):
    """One `ff9mapkit coop <action>` against the fake install, relay mode unless ``lan`` is given; (rc, lines)."""
    lines = []
    rc = coop.run(_cli_args(action=action, game=str(game), code=code, no_room=True, no_bridge=True, **kw),
                  out=lines.append)
    return rc, lines


def _netsync(game, key):
    return coop.read_ini_key(coop.read_ini_text(game / "Memoria.ini"), "Netsync", key)


def test_a_former_guest_hosts_on_its_own_code(game, no_clip):
    assert _coop(game, "join", "ff9-FRIEND01")[0] == 0
    assert _netsync(game, "SessionCode") == "ff9-FRIEND01" and _netsync(game, "Role") == "client"
    rc, lines = _coop(game, "host")
    assert rc == 0
    code = _netsync(game, "SessionCode")
    assert code != "ff9-FRIEND01", "the PC re-published the code it JOINED with as its own session"
    assert re.fullmatch(r"ff9-[A-Z0-9]{8}", code) and _netsync(game, "HostSessionCode") == code
    assert any("not reusing 'ff9-FRIEND01'" in ln and "joined a session with it" in ln for ln in lines), lines


def test_a_hosts_own_code_survives_a_join(game, no_clip):
    assert _coop(game, "host")[0] == 0
    mine = _netsync(game, "SessionCode")
    assert _netsync(game, "HostSessionCode") == mine
    assert _coop(game, "join", "ff9-FRIEND01")[0] == 0
    assert _netsync(game, "SessionCode") == "ff9-FRIEND01" and _netsync(game, "HostSessionCode") == mine
    assert _coop(game, "off")[0] == 0
    assert _coop(game, "host")[0] == 0
    assert _netsync(game, "SessionCode") == mine, "a guest stint churned the host's code ('generated once, persisted')"


def test_a_pre_s154_host_ini_keeps_its_code_through_a_join(game, no_clip):
    (game / "Memoria.ini").write_text(INI.replace("SessionCode =\n", "SessionCode = ff9-MINE0001\n"), encoding="utf-8")
    rc, lines = _coop(game, "join", "ff9-FRIEND01")
    assert rc == 0
    assert _netsync(game, "HostSessionCode") == "ff9-MINE0001" and _netsync(game, "SessionCode") == "ff9-FRIEND01"
    # the one-time migration says what it kept AND that it cannot vouch for a pre-fix residue
    assert any("keeping your own session code ff9-MINE0001" in ln and "coop host --new-code --no-bridge" in ln
               for ln in lines), lines
    assert _coop(game, "host")[0] == 0
    assert _netsync(game, "SessionCode") == "ff9-MINE0001"


def test_a_lan_join_keeps_the_host_code(game, no_clip):
    assert _coop(game, "host")[0] == 0
    mine = _netsync(game, "SessionCode")
    assert _coop(game, "join", lan="192.168.1.50")[0] == 0
    assert _netsync(game, "SessionCode") == ""                   # a LAN join pairs by address and blanks the code
    assert _coop(game, "host")[0] == 0
    assert _netsync(game, "SessionCode") == mine


def test_explicit_and_new_codes_become_the_own_code(game, no_clip):
    assert _coop(game, "host", "ff9-CHOSEN01")[0] == 0
    assert _netsync(game, "SessionCode") == _netsync(game, "HostSessionCode") == "ff9-CHOSEN01"
    assert _coop(game, "join", "ff9-FRIEND01")[0] == 0
    assert _coop(game, "host")[0] == 0
    assert _netsync(game, "SessionCode") == "ff9-CHOSEN01"
    assert _coop(game, "host", new_code=True)[0] == 0
    fresh = _netsync(game, "SessionCode")
    assert fresh != "ff9-CHOSEN01" and re.fullmatch(r"ff9-[A-Z0-9]{8}", fresh)
    assert _netsync(game, "HostSessionCode") == fresh


def test_an_explicit_joined_code_is_honoured_and_named(game, no_clip):
    # `coop host <code>` stays a documented override, even on the code this PC joined with -- but never silently, and
    # never FOR GOOD: it dials the friend's code this run, and the own code stays this PC's, so the note's advice ("leave
    # the code off to host on your own") is true. The s154 first cut wrote the invite into HostSessionCode: every later
    # bare `coop host` re-published it, silently (Role read host by then, so the note never fired again).
    assert _coop(game, "host")[0] == 0
    mine = _netsync(game, "HostSessionCode")
    assert _coop(game, "join", "ff9-FRIEND01")[0] == 0
    rc, lines = _coop(game, "host", "FF9-friend01")
    assert rc == 0 and _netsync(game, "SessionCode") == "FF9-friend01"
    assert _netsync(game, "HostSessionCode") == mine, "the override recorded the friend's code as this PC's own"
    assert any("last JOINED with" in ln and f"your own code is {mine}" in ln for ln in lines), lines
    shown = []
    assert coop.show_config(game, out=shown.append) == 0
    assert any(ln.startswith(f"  your code:   {mine}") for ln in shown), shown   # says what a bare host goes back to
    # the same command again (shell history): the Role reads host now, and the override must still be caught
    rc, lines = _coop(game, "host", "ff9-FRIEND01")
    assert rc == 0 and _netsync(game, "SessionCode") == "ff9-FRIEND01"
    assert _netsync(game, "HostSessionCode") == mine, "a REPEATED override recorded the friend's code as this PC's own"
    assert any("is not this PC's own code" in ln and f"your own code is {mine}" in ln for ln in lines), lines
    assert _coop(game, "off")[0] == 0
    rc, lines = _coop(game, "host")                          # the note's advice: leave the code off
    assert rc == 0
    assert _netsync(game, "SessionCode") == _netsync(game, "HostSessionCode") == mine, (
        "a bare `coop host` after the override re-published the friend's invite")


def test_an_explicit_joined_code_on_a_never_hosted_pc_mints_its_own(game, no_clip):
    # no own code yet: the override mints one and records THAT, never published -- writing nothing would not do, a
    # Role=host ini with no HostSessionCode reads 'migrated' and the next bare host would adopt the invite
    assert _coop(game, "join", "ff9-FRIEND01")[0] == 0
    rc, lines = _coop(game, "host", "ff9-FRIEND01")
    assert rc == 0 and _netsync(game, "SessionCode") == "ff9-FRIEND01"
    own = _netsync(game, "HostSessionCode")
    assert own and re.fullmatch(r"ff9-[A-Z0-9]{8}", own) and own.upper() != "FF9-FRIEND01", own
    assert any(f"your own code is {own}" in ln for ln in lines), lines
    assert _coop(game, "host", "ff9-FRIEND01")[0] == 0       # a repeat keeps the one minted, mints no second
    assert _netsync(game, "HostSessionCode") == own
    assert _coop(game, "off")[0] == 0
    assert _coop(game, "host")[0] == 0
    assert _netsync(game, "SessionCode") == _netsync(game, "HostSessionCode") == own


# (the [Netsync] body, the explicit code, joined_override's verdict, the failure the row names)
OVERRIDE_ROWS = [
    (_ns("Role = client", "SessionCode = ff9-FRIEND01"), "ff9-FRIEND01", True,
     "the first override (a guest ini) records the invite as the own code"),
    (_ns("Role = CLIENT ", "SessionCode = ff9-FRIEND01", "HostSessionCode = ff9-MINE0001"), "FF9-friend01", True,
     "a hand-cased Role or a re-cased code slips the guard"),
    (_ns("Role = host", "SessionCode = ff9-FRIEND01", "HostSessionCode = ff9-MINE0001"), "ff9-FRIEND01", True,
     "a REPEATED override (Role reads host by then) records the invite"),
    (_ns("Role = host", "SessionCode = ff9-MINE0001", "HostSessionCode = ff9-MINE0001"), "ff9-MINE0001", False,
     "a host re-naming its own code is told it joined with it"),
    (_ns("Role = host", "SessionCode = ff9-MINE0001"), "ff9-MINE0001", False,
     "a pre-s154 host's migrated code is refused as its own"),
    (_ns("Role = client", "SessionCode = ff9-FRIEND01", "HostSessionCode = ff9-MINE0001"), "ff9-CHOSEN01", False,
     "a fresh explicit code is kept from becoming the own code"),
    (_ns("Role = host", "SessionCode = ff9-FRIEND01", "HostSessionCode = ff9-MINE0001"), None, False,
     "a bare `coop host` (no code) is taken for an override"),
    (_ns("Role = selftest", "SessionCode = ff9-BENCH001"), "ff9-BENCH001", False,
     "a bench's own code, named explicitly, is refused as a host code"),
    (_ns("Role = client", "SessionCode ="), "ff9-FRIEND01", False, "an empty SessionCode matches any code"),
]


@pytest.mark.parametrize("text,code,want,failure", OVERRIDE_ROWS, ids=[r[3] for r in OVERRIDE_ROWS])
def test_joined_override_rule(text, code, want, failure):
    assert coop.joined_override(code, text) is want, failure


def test_every_fresh_code_cure_names_the_bridge_safe_form(monkeypatch):
    # the cure is read in a place a bridge already runs (the Workspace's Connection log and Output panel, or beside a
    # terminal's `coop host`): a bare `coop host --new-code` runs a SECOND bridge on the same port, and SO_REUSEADDR lets
    # both bind on Windows. Every surface that names it names `--no-bridge`, and the Workspace's step after it.
    import threading
    from pathlib import Path
    from ff9mapkit import netsync_bridge as NB
    said = []
    monkeypatch.setattr(NB, "log", said.append)
    up = NB._Upstream(None, "ws://127.0.0.1:1", "/sess/ff9-T?role=host", False, threading.Event())
    t = 0.0
    for _ in range(NB.FLAP_WARN_AT):                         # the shipped two-hosts advice, driven, not read from source
        up.up_since = t
        t += 0.4
        up.flap_wait(t)
    tutorial = (Path(__file__).resolve().parents[1] / "docs" / "tutorials" / "17-coop.md").read_text(encoding="utf-8")
    for name, text in (("the bridge's two-hosts advice", " ".join(said)), ("the migration caveat", coop.MIGRATION_CAVEAT),
                       ("tutorial 17", tutorial)):
        cures = re.findall(r"ff9mapkit coop host --new-code(?: --[\w-]+)*", text)
        assert cures, f"{name} no longer names the cure: {text[:300]}"
        assert all("--no-bridge" in c for c in cures), (name, cures)
        assert "Start hosting again" in re.sub(r"\*\*|\s+", lambda m: "" if m.group() == "**" else " ", text), name


def test_a_fresh_code_from_the_bridge_safe_cure_is_kept_by_the_next_host(game, no_clip):
    # the cure's second half: Start hosting again (a bare `coop host`, which is all the Workspace's Start runs) must keep
    # the code `--new-code --no-bridge` just minted, not go back to the old one
    assert _coop(game, "host")[0] == 0
    old = _netsync(game, "SessionCode")
    assert _coop(game, "host", new_code=True)[0] == 0          # _coop always passes --no-bridge
    fresh = _netsync(game, "SessionCode")
    assert fresh != old and _netsync(game, "HostSessionCode") == fresh
    rc, lines = _coop(game, "host")
    assert rc == 0 and _netsync(game, "SessionCode") == _netsync(game, "HostSessionCode") == fresh
    assert any(ln.strip().startswith(f"session code:  {fresh}") for ln in lines), lines


@pytest.mark.parametrize("role_line,said", [("Role = selftest", "Role is 'selftest'"), (None, "Role is not set")])
def test_an_unowned_stored_code_is_declined_with_its_real_reason(game, no_clip, role_line, said):
    # a bench's (selftest) or a no-Role code was never a friend's invite: the decline must not claim this PC joined with
    # it -- every gate that declines says its REAL reason
    body = INI.replace("Role = host\n", (role_line + "\n") if role_line else "")
    (game / "Memoria.ini").write_text(body.replace("SessionCode =\n", "SessionCode = ff9-BENCH001\n"), encoding="utf-8")
    rc, lines = _coop(game, "host")
    assert rc == 0 and _netsync(game, "SessionCode") != "ff9-BENCH001"
    hit = [ln for ln in lines if "not reusing the stored SessionCode 'ff9-BENCH001'" in ln]
    assert len(hit) == 1 and said in hit[0] and "joined" not in hit[0], lines


def test_the_migration_caveat_is_said_once(game, no_clip):
    (game / "Memoria.ini").write_text(INI.replace("SessionCode =\n", "SessionCode = ff9-MINE0001\n"), encoding="utf-8")
    rc, lines = _coop(game, "host")
    assert rc == 0 and _netsync(game, "SessionCode") == "ff9-MINE0001"
    caveat = [ln for ln in lines if "adopting your stored session code ff9-MINE0001" in ln]
    assert len(caveat) == 1 and "coop host --new-code --no-bridge" in caveat[0], lines
    rc, lines = _coop(game, "host")
    assert rc == 0 and not any("adopting" in ln for ln in lines), "the caveat is one-time: HostSessionCode exists now"


def test_an_unusable_own_key_never_falls_back_to_the_invite(game, no_clip):
    (game / "Memoria.ini").write_text(
        INI.replace("Role = host\n", "Role = client\n").replace("SessionCode =\n", "SessionCode = ff9-FRIEND01\n")
        + "HostSessionCode = not a code!\n", encoding="utf-8")
    rc, lines = _coop(game, "host")
    assert rc == 0
    code = _netsync(game, "SessionCode")
    assert code != "ff9-FRIEND01" and _netsync(game, "HostSessionCode") == code
    assert any("ignoring the stored HostSessionCode 'not a code!'" in ln for ln in lines), lines


def test_show_config_names_the_own_code_on_a_guest(game, no_clip):
    assert _coop(game, "host", "ff9-MINE0001")[0] == 0
    assert _coop(game, "join", "ff9-FRIEND01")[0] == 0
    lines = []
    assert coop.show_config(game, out=lines.append) == 0
    assert any(ln.startswith("  session:     ff9-FRIEND01  (the host's code you joined with)") for ln in lines), lines
    assert any(ln.startswith("  your code:   ff9-MINE0001") for ln in lines), lines
    assert _coop(game, "host")[0] == 0                      # hosting on the own code: nothing to tell apart
    lines = []
    assert coop.show_config(game, out=lines.append) == 0
    assert not any("your code:" in ln for ln in lines), lines


def test_show_config_off_and_missing(game, tmp_path):
    lines = []
    assert coop.show_config(game, out=lines.append) == 0        # fixture ini has Enabled = 0
    assert any("co-op:       off" in ln for ln in lines)
    empty = tmp_path / "no-install-here"                         # the game fixture IS tmp_path
    empty.mkdir()
    assert coop.show_config(empty, out=lambda *_: None) == 2     # no Memoria.ini -> actionable exit


# ------------------------------------- the RESIDUE of a pre-fence splice: duplicate [Netsync] keys
#
# validate_code + the writer fence stop a NEW splice; an install poisoned BEFORE the fix still carries
# the spliced lines. Memoria's IniFile.Init ends every parsed line with `Options[Key(section,key)] =
# value` -- a plain dict assignment -- so on a duplicated key the LAST copy is the live one. Every
# reader and writer here has to agree with that, or the kit reports (and vets, and rewrites) a value
# the game is not using.

RESIDUE_INI = (
    "[Graphics]\n"
    "Enabled = 1\n"
    "\n"
    "[Netsync]\n"
    "Enabled = 1\n"
    "RelayUrl = ws://127.0.0.1:49201\n"
    "SessionCode = ff9-GOOD1234\n"
    "GuestSlots = 15\n"
    "RelayUrl = ws://attacker.example:1234\n"
    "SessionCode = not a code!\n"
)


def test_read_ini_key_returns_the_last_copy_like_the_engine():
    # first-match-wins read the reassuring line the victim can see; the engine reads the one below it
    assert coop.read_ini_key(RESIDUE_INI, "Netsync", "SessionCode") == "not a code!"
    assert coop.read_ini_key(RESIDUE_INI, "Netsync", "RelayUrl") == "ws://attacker.example:1234"
    assert coop.read_ini_key(RESIDUE_INI, "Netsync", "GuestSlots") == "15"
    assert coop.read_ini_key(RESIDUE_INI, "Graphics", "Enabled") == "1"      # unrelated section intact


def test_read_ini_key_sees_a_re_opened_section():
    # the payload's own shape: a second [Netsync] header re-enters the section in the engine's parser
    ini = "[Netsync]\nGuestSlots = 0\n\n[Mod]\nPriorities = \"X\"\n\n[Netsync]\nGuestSlots = 15\n"
    assert coop.read_ini_key(ini, "Netsync", "GuestSlots") == "15"


def test_duplicate_ini_keys_names_the_residue():
    assert coop.duplicate_ini_keys(RESIDUE_INI, "Netsync") == ["RelayUrl", "SessionCode"]
    assert coop.duplicate_ini_keys(INI, "Netsync") == []                     # a clean ini is silent
    assert coop.duplicate_ini_keys(RESIDUE_INI, "Graphics") == []            # section-scoped


def test_show_config_flags_a_duplicated_key(game):
    (game / "Memoria.ini").write_text(RESIDUE_INI, encoding="utf-8")
    lines = []
    assert coop.show_config(game, out=lines.append) == 0
    text = "\n".join(lines)
    assert "more than once" in text and "RelayUrl" in text and "SessionCode" in text
    # ...and the report itself must describe the LIVE lines, not the dead ones above them
    assert "session:     not a code!" in text
    assert "relay via ws://attacker.example:1234" in text
    assert "slot(s) 1, 2, 3, 4" in text


def test_update_ini_section_drops_a_stale_duplicate_of_a_key_it_writes():
    # writing only the FIRST copy left the engine obeying the second -- the rewrite meant to CORRECT
    # a poisoned value would have been a silent no-op
    out = coop.update_ini_section(RESIDUE_INI, "Netsync",
                                  {"SessionCode": "ff9-NEWCODE1", "RelayUrl": ""})
    assert out.count("SessionCode") == 1
    assert out.count("RelayUrl") == 1
    assert "attacker.example" not in out
    assert coop.read_ini_key(out, "Netsync", "SessionCode") == "ff9-NEWCODE1"
    assert coop.read_ini_key(out, "Netsync", "GuestSlots") == "15"   # not ours to touch: left alone


def test_update_ini_section_collapses_a_duplicate_across_a_re_opened_section():
    ini = "[Netsync]\nEnabled = 1\nSessionCode = ff9-GOOD1234\n\n[Netsync]\nSessionCode = not a code!\n"
    out = coop.update_ini_section(ini, "Netsync", {"SessionCode": "ff9-NEWCODE1"})
    assert coop.read_ini_key(out, "Netsync", "SessionCode") == "ff9-NEWCODE1"
    assert "not a code!" not in out


def test_coop_host_replaces_a_poisoned_second_stored_code(game, monkeypatch):
    # the stored-code guard has to vet the line the ENGINE obeys: with the first copy read instead,
    # the good-looking line validated, the unusable one below it survived the rewrite, and the fence
    # that exists for exactly this ini passed it straight through
    monkeypatch.setattr(coop, "_copy_clipboard", lambda _text: False)
    ini = game / "Memoria.ini"
    ini.write_text(INI + "SessionCode = ff9-GOOD1234\nSessionCode = not a code!\n", encoding="utf-8")
    lines = []
    assert coop.run(_cli_args(action="host", game=str(game), lan="", no_room=True),
                    out=lines.append) == 0
    text = ini.read_text(encoding="utf-8")
    assert any("ignoring the stored SessionCode" in ln for ln in lines)
    assert "not a code!" not in text
    # anchored on the KEY: [ff9mapkit s154] HostSessionCode now sits beside it and contains the substring
    assert sum(1 for ln in text.splitlines() if ln.split("=")[0].strip() == "SessionCode") == 1
    assert re.fullmatch(r"ff9-[A-Z0-9]{8}", coop.read_ini_key(text, "Netsync", "SessionCode"))


def test_bom_ini_find_registered_field_sees_the_real_folders(game):
    # red on the pre-fix reader: a BOM'd line-1 [Mod] read as no folders, so the 30000 in FF9CustomMap was invisible and the
    # co-op room could be built (and registered) a second time beside it -- the cross-folder EventDB collision
    ini = game / "Memoria.ini"
    ini.write_bytes(BOM + INI.encode("utf-8"))
    assert coop.find_registered_field(game, 30000) == "FF9CustomMap"


def test_split_mod_section_is_named_not_left_silent(game):
    # an ini the OLD bug already split: the engine obeys the last [Mod] (FF9Coop alone) -- the setup must say so, not report
    # "already registered" and leave every other mod off
    ini = game / "Memoria.ini"
    ini.write_text(INI + NL + "[Mod]" + NL + 'FolderNames = "FF9Coop"' + NL, encoding="utf-8")
    said = []
    assert not coop.ensure_folder_registered(game, "FF9Coop", out=said.append)
    assert any("FolderNames more than once" in line for line in said), said
    said.clear()
    assert not coop.warn_split_mod_section(INI, out=said.append) and not said
