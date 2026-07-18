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
    for off_ish in ("", "off", "none", "0"):
        assert coop.parse_ghost_as(off_ish) == ""
    with pytest.raises(ValueError):
        coop.parse_ghost_as("beatrix")                     # no proven rig row -> refuse up front


def test_playstyle_updates_only_what_was_given():
    assert coop.playstyle_updates() == {}                  # nothing given -> nothing clobbered
    assert coop.playstyle_updates(guest_wait=0) == {"GuestWaitMs": "0"}
    full = coop.playstyle_updates("2", 30, "auto", True, True)
    assert full == {"GuestSlots": "2", "GuestWaitMs": "30000",
                    "GhostAs": "auto", "FollowHost": "1", "Diorama": "1"}
    assert coop.playstyle_updates(follow_host=False) == {"FollowHost": "0"}
    assert coop.playstyle_updates(diorama=False) == {"Diorama": "0"}
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
    assert "diorama:     ON" in text        # key absent -> the engine default (s40: on)


def test_show_config_diorama_off(game):
    coop.write_netsync(game, {"Enabled": "1", "Role": "client",
                              **coop.playstyle_updates(diorama=False)}, out=lambda *_: None)
    lines = []
    assert coop.show_config(game, out=lines.append) == 0
    assert any("diorama:     off (text spectate panel)" in ln for ln in lines)


def test_coop_join_diorama_flag_writes_key(game):
    rc = coop.run(_cli_args(action="join", game=str(game), code="ff9-ABCD1234",
                            lan="192.168.1.50", no_room=True, diorama="off"), out=lambda *_: None)
    assert rc == 0
    text = (game / "Memoria.ini").read_text(encoding="utf-8")
    assert coop.read_ini_key(text, "Netsync", "Diorama") == "0"


def test_coop_join_diorama_untouched_when_not_given(game):
    rc = coop.run(_cli_args(action="join", game=str(game), code="ff9-ABCD1234",
                            lan="192.168.1.50", no_room=True), out=lambda *_: None)
    assert rc == 0
    text = (game / "Memoria.ini").read_text(encoding="utf-8")
    assert coop.read_ini_key(text, "Netsync", "Diorama") is None    # engine default rules


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


def test_coop_host_explicit_follow_host_overrides(game, monkeypatch):
    # --follow-host on stays honored: the explicit style write lands AFTER the role-branch force
    monkeypatch.setattr(coop, "_copy_clipboard", lambda _text: False)
    rc = coop.run(_cli_args(action="host", game=str(game), lan="", no_room=True, follow_host="on"),
                  out=lambda *_: None)
    assert rc == 0
    text = (game / "Memoria.ini").read_text(encoding="utf-8")
    assert coop.read_ini_key(text, "Netsync", "FollowHost") == "1"


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
    # the flip side: a good stored code still survives a re-run (the fence must not churn codes)
    monkeypatch.setattr(coop, "_copy_clipboard", lambda _text: False)
    ini = (game / "Memoria.ini")
    ini.write_text(INI.replace("SessionCode =\n", "SessionCode = ff9-KEEPME12\n"), encoding="utf-8")
    assert coop.run(_cli_args(action="host", game=str(game), lan="", no_room=True),
                    out=lambda *_: None) == 0
    assert coop.read_ini_key(ini.read_text(encoding="utf-8"), "Netsync", "SessionCode") == "ff9-KEEPME12"


def test_show_config_off_and_missing(game, tmp_path):
    lines = []
    assert coop.show_config(game, out=lines.append) == 0        # fixture ini has Enabled = 0
    assert any("co-op:       off" in ln for ln in lines)
    empty = tmp_path / "no-install-here"                         # the game fixture IS tmp_path
    empty.mkdir()
    assert coop.show_config(empty, out=lambda *_: None) == 2     # no Memoria.ini -> actionable exit
