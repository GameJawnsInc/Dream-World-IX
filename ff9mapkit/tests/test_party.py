"""[party] party-membership authoring -- add/remove existing playable characters at field load.

The authoring complement to `import --swap-player` (which changes who you WALK as): [party] mutates
party.member[] (who's in the MENU + BATTLE). The add is FF9's real B_PARTYADD (op 0x6D) JOIN form, proven
in-game (inject partyadd(Steiner) -> the party menu shows the new member). These tests pin the emitted
bytecode against the proven probe, the name/alias resolution, the build injection (prepended to Main_Init),
byte-identity when absent, validation, and the SetPartyReserve wipe-warning scan.
"""
from __future__ import annotations

import pytest

from ff9mapkit.build import FieldProject, build_mod, validate, BuildError, _field_load_inject
from ff9mapkit.config import ModLayout
from ff9mapkit.content import party
from ff9mapkit.eb import EbScript, edit
import ff9mapkit.forkreport as forkreport


def _raise(exc):
    raise exc

BASE = """
[field]
id = 4003
name = "PARTYROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""


# ---- the bytecode emitters (grounded in the in-game-proven probe) -----------------------------
def test_add_member_matches_proven_probe():
    # the in-game-proven probe bytes (2026-06-11): inject partyadd(Steiner=3) into Main_Init
    assert party.add_member(3) == bytes.fromhex("05 c5 93 7d 03 00 6d 2c 7f".replace(" ", ""))
    # real field 60 JOIN form (add Vivi=1)
    assert party.add_member(1) == bytes.fromhex("05 c5 93 7d 01 00 6d 2c 7f".replace(" ", ""))


def test_remove_member_is_removeparty_op():
    assert party.remove_member(0) == bytes([0xDD, 0x00, 0x00])    # RemoveParty(Zidane), literal arg
    assert party.remove_member(7) == bytes([0xDD, 0x00, 0x07])


def test_party_body_removes_then_adds_else_empty():
    assert party.party_body() == b""                              # nothing -> byte-identical caller
    assert party.party_body(adds=[3], removes=[0]) == party.remove_member(0) + party.add_member(3)


# ---- name resolution --------------------------------------------------------------------------
def test_resolve_member_names_aliases_ints():
    assert party.resolve_member("steiner") == 3
    assert party.resolve_member("STEINER") == 3
    assert party.resolve_member("dagger") == 2                    # alias -> Garnet
    assert party.resolve_member("salamander") == 7               # alias -> Amarant
    assert party.resolve_member(5) == 5                          # bare CharacterOldIndex passes through
    with pytest.raises(ValueError):
        party.resolve_member("zorn")
    with pytest.raises(ValueError):
        party.resolve_member(99)
    with pytest.raises(ValueError):
        party.resolve_member(True)                              # bools are not members


def test_char_table_pinned_to_forkreport():
    """Single source of truth: the local table must stay in lockstep with forkreport's (the scanner side)."""
    assert party.CHAR_OLD_INDEX == forkreport.CHAR_OLD_INDEX


# ---- build integration ------------------------------------------------------------------------
def _build_eb(tmp_path, toml: str) -> EbScript:
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    return EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_PARTYROOM.eb.bytes").read_bytes())


def _main_init_bytes(eb: EbScript) -> bytes:
    f0 = eb.entry(0).func_by_tag(0)
    return eb.data[f0.abs_start:f0.abs_end]


def test_party_add_injected_at_start_of_main_init(tmp_path):
    body = _main_init_bytes(_build_eb(tmp_path, BASE + '\n[party]\nadd = ["steiner"]\n'))
    assert party.add_member(3) in body
    assert body.startswith(party.add_member(3))                  # prepended -> runs at field load


def test_party_add_and_remove(tmp_path):
    body = _main_init_bytes(_build_eb(tmp_path, BASE + '\n[party]\nremove = ["zidane"]\nadd = ["vivi"]\n'))
    assert party.remove_member(0) in body and party.add_member(1) in body


def test_party_absent_is_byte_identical(tmp_path):
    body = _main_init_bytes(_build_eb(tmp_path, BASE))
    assert party.add_member(3) not in body
    # the partyadd opcode signature (expr + MAP scratch) is absent entirely when [party] is omitted
    assert bytes([0x05, party._region.MAP_BOOL, party.PARTY_SCRATCH]) not in body


def test_party_eb_parses_clean_after_inject(tmp_path):
    eb = _build_eb(tmp_path, BASE + '\n[party]\nadd = ["steiner", "vivi"]\n')
    f0 = eb.entry(0).func_by_tag(0)
    assert list(eb.instrs(f0))                                    # Main_Init still disassembles (no fpos corruption)
    reinit = eb.entry(0).func_by_tag(10)
    if reinit is not None:
        assert list(eb.instrs(reinit))                           # the after-battle handler survived intact


# ---- validation -------------------------------------------------------------------------------
def _problems(tmp_path, toml: str):
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    return validate(FieldProject.load(p))


def test_party_validate_catches_bad_shapes(tmp_path):
    assert any("unknown party member" in m for m in _problems(tmp_path, BASE + '\n[party]\nadd = ["zorn"]\n'))
    assert any("must be a list" in m for m in _problems(tmp_path, BASE + '\n[party]\nadd = "steiner"\n'))
    assert any("unknown key" in m for m in _problems(tmp_path, BASE + '\n[party]\nfoo = ["vivi"]\n'))
    assert any("no add or remove" in m for m in _problems(tmp_path, BASE + "\n[party]\n"))


# ---- the SetPartyReserve wipe-scan ------------------------------------------------------------
def test_field_resets_party_scan(tmp_path):
    eb = _build_eb(tmp_path, BASE + '\n[party]\nadd = ["steiner"]\n')
    assert party.field_resets_party(eb) is False                 # a synthesized field never rebuilds the roster
    reserve = bytes([party.SET_PARTY_RESERVE, 0x00, 0x00, 0x00])
    # 0xB4 in Main_Init (entry 0 tag 0) -> flagged
    assert party.field_resets_party(EbScript.from_bytes(
        edit.insert_in_function(eb.data, 0, 0, 0, reserve))) is True
    # ★ the broadened scan: 0xB4 in an OBJECT Init (entry 1 tag 0), NOT Main_Init, is also flagged -- this is
    # the real-field case (Cargo Ship has SetPartyReserve in an object Init; the old entry-0/tag-0-only scan
    # missed 109 of 111 reset fields).
    assert party.field_resets_party(EbScript.from_bytes(
        edit.insert_in_function(eb.data, 1, 0, 0, reserve))) is True


# ---- the jump-table fail-closed guard (adversarial-review finding) ----------------------------
def test_field_load_inject_converts_jump_table_valueerror():
    """Defensive net: if a field-load injector ever raises a 0x06 jump-table ValueError (a MID-function insert),
    _field_load_inject must convert it to a clear BuildError, not leak an opaque ValueError. The levers all
    PREPEND (rel_off=0), which is always safe past a jump table since the rel_off==0 fix, so this no longer
    fires for them -- but the conversion stays as insurance for a future mid-insert lever."""
    jt = ValueError("func 0 has a jump table (0x06); insert unsupported")
    with pytest.raises(BuildError, match="jump table"):
        _field_load_inject("[party]", "FIELD100", lambda: _raise(jt))
    # an UNRELATED ValueError is re-raised as-is (not swallowed/masked)
    with pytest.raises(ValueError, match="something else"):
        _field_load_inject("[party]", "X", lambda: _raise(ValueError("something else")))
    # a clean injection passes its result straight through
    assert _field_load_inject("[party]", "X", lambda: b"ok") == b"ok"
