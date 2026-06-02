"""Phase-3 validation: generalized content injectors.

The headline oracle is byte-exact: rebuilding the in-game-verified Vivi-hut interior
(``hut_int-us.eb.bytes``) from the blank field via npc + set_player + gateway must reproduce
it exactly. The other transforms (encounter / reinit / music) are validated structurally —
applied to the blank field, the result must re-parse cleanly and contain the expected opcodes
with the rest of the script intact.
"""

from __future__ import annotations

from pathlib import Path

from ff9mapkit import data
from ff9mapkit.content import encounter, gateway, music, npc, reinit, text
from ff9mapkit.eb import EbScript
from ff9mapkit.eb.disasm import iter_code

FIX = Path(__file__).parent / "fixtures"
CLEAN = data.blank_field_bytes("us")


def _ops(eb: EbScript, entry_index: int, func_tag: int) -> list:
    f = eb.entry(entry_index).func_by_tag(func_tag)
    return [ins.op for ins in iter_code(eb.data, f.abs_start, f.abs_end)]


def test_hut_interior_reproduced_byte_exact():
    EXIT_ZONE = [(-1100, -2400), (1100, -2400), (1100, -1750), (-1100, -1750), (-1100, -1750)]
    out = npc.inject_npc(CLEAN, 0, -700, preset="vivi", talk_text_id=500)
    out = npc.set_player_spawn(out, 0, -1350)
    out = gateway.inject_gateway(out, 4000, entrance=0, slot=3, zone=EXIT_ZONE)
    assert out == (FIX / "hut_int-us.eb.bytes").read_bytes()


def test_npc_is_appended_and_spawned():
    out = npc.inject_npc(CLEAN, 100, -500, preset="vivi", talk_text_id=500)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out                       # still structurally valid
    # a new entry exists with a _SpeakBTN (tag 3) and no DefinePlayerCharacter
    npc_entry = next(e for e in eb.entries if not e.empty and e.func_by_tag(3) and e.index != 0)
    assert npc_entry.func_by_tag(3) is not None
    speak = _ops(eb, npc_entry.index, 3)
    assert 0x1F in speak                              # WindowSync
    # Main_Init now spawns it via InitObject (0x09)
    assert 0x09 in _ops(eb, 0, 0)


def test_encounter_injected():
    out = encounter.inject_encounter(CLEAN, scene=67, freq=255)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out
    assert 0x07 in _ops(eb, 0, 0)                    # InitCode in Main_Init
    batt = next(e for e in eb.entries if not e.empty and e.type == 0 and e.index != 0)
    ops = _ops(eb, batt.index, 0)
    assert ops[0] == 0x3C and 0x57 in ops            # SetRandomBattles + SetRandomBattleFrequency


def test_reinit_with_and_without_fade():
    out = reinit.add_reinit(CLEAN, with_fade=True)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out
    assert eb.entry(0).func_by_tag(10) is not None
    assert _ops(eb, 0, 10) == [0xEC, 0x2E, 0x04]     # FadeFilter, EnableMove, return
    # the player object (entry 1) survived the entry-0 growth + relocation
    assert eb.entry(1).func_by_tag(0) is not None
    assert 0x2C in _ops(eb, 1, 0)                    # DefinePlayerCharacter still intact

    plain = reinit.add_reinit(CLEAN, with_fade=False)
    assert _ops(EbScript.from_bytes(plain), 0, 10) == [0x2E, 0x04]


def test_music_on_entry_and_reinit():
    out = music.add_field_music(CLEAN, 9)
    eb = EbScript.from_bytes(out)
    assert eb.to_bytes() == out
    assert 0x07 in _ops(eb, 0, 0)                    # InitCode activates the music entry
    me = next(e for e in eb.entries if not e.empty and e.type == 0 and e.index != 0)
    assert _ops(eb, me.index, 0)[0] == 0xC5          # RunSoundCode

    out2 = reinit.add_reinit(CLEAN, with_fade=True)
    out2 = music.add_music_to_reinit(out2, 9)
    eb2 = EbScript.from_bytes(out2)
    assert _ops(eb2, 0, 10)[0] == 0xC5               # RunSoundCode now first in tag-10


def test_text_mes_format_and_mapping():
    line = text.mes_entry("I miss you Zidane", 500)
    assert line == "_[TXID=500][STRT=10,1][TAIL=UPR]I miss you Zidane[ENDN]"
    body, mapping = text.build_mes(["hello", "world"], start_txid=500)
    assert mapping == {0: 500, 1: 501}
    assert "[TXID=501]" in body and body.endswith("\n")
