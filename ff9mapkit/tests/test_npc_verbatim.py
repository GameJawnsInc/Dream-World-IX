"""Add a NEW self-contained kit NPC to a VERBATIM fork (party-band-aware insertion).

dead-end #14 was about GRAFTING an existing donor handler (semantic, still dead); ADDING a fresh
self-contained `[[npc]]` to a verbatim fork is a different, tractable problem. The load-bearing constraint
is the engine's reserved party-character band (the LAST 9 entry slots, addressed positionally), so the NPC
must be seated BELOW it with every band reference remapped +1. These tests prove that on a real donor
(`alex100`, Alexandria Main Street) the 9 character bodies survive byte-identical, the references remap,
the result is structurally clean (eblint), and the NPC spawns + is talkable.
"""
from pathlib import Path

import pytest

from ff9mapkit import eblint
from ff9mapkit.content import npc as _npc
from ff9mapkit.content import object as _object
from ff9mapkit.eb import EbScript

FIX = Path(__file__).parent / "fixtures"
BAND = _object.PARTY_BAND_SIZE


def _alex100() -> bytes:
    p = FIX / "alex100-us.eb.bytes"
    if not p.exists():
        pytest.skip("alex100 fixture not extracted (ff9mapkit extract-templates)")
    return p.read_bytes()


def _entry_body(eb: EbScript, idx: int) -> bytes:
    e = eb.entry(idx)
    return eb.data[e.abs_start:e.abs_end]


def _main_init_object_targets(eb: EbScript) -> list:
    """The slot args of every InitObject (0x09) in Main_Init (entry 0, tag 0), in order."""
    f0 = eb.entry(0).func_by_tag(0)
    return [int(ins.imm(0)) for ins in eb.instrs(f0) if ins.op == 0x09 and ins.imm(0) is not None]


def test_insert_before_band_is_purely_structural():
    """insert_entry_before_band = remap-band-refs THEN relocate. Proven by isolating the two: after the
    remap alone (shift_slot_refs), the structural insert must only RELOCATE bodies (band chars +1 slot,
    others in place), never alter body CONTENT. So every body in the output equals its body in the
    remapped-but-not-inserted script."""
    data = _alex100()
    n = EbScript.from_bytes(data).entry_count
    band_lo = n - BAND
    fake_npc = bytes([2, 1]) + (0).to_bytes(2, "little") + (4).to_bytes(2, "little") + bytes([0x04])

    shifted = _object.shift_slot_refs(data, band_lo, n - 1, 1)     # the remap, in isolation (no relocate)
    out, slot = _object.insert_entry_before_band(data, fake_npc)
    eb_sh = EbScript.from_bytes(shifted)
    eb_out = EbScript.from_bytes(out)

    assert slot == band_lo
    assert eb_out.entry_count == n + 1
    assert eb_out.to_bytes() == out                               # round-trip identity
    assert _entry_body(eb_out, band_lo) == fake_npc               # the inserted body, verbatim

    # below the band: same slot index, body == the remapped body (relocate touched nothing)
    for k in range(band_lo):
        if not eb_sh.entry(k).empty:
            assert _entry_body(eb_out, k) == _entry_body(eb_sh, k), f"below-band entry {k} content changed"
    # the band characters: relocated +1 slot, body == the remapped body (no content change from the insert)
    for k in range(band_lo, n):
        assert _entry_body(eb_out, k + 1) == _entry_body(eb_sh, k), f"character {k}->{k+1} content changed"


def test_character_bodies_change_only_by_band_remap():
    """End-to-end (inject_npc): a band character's body in the fork differs from the donor's ONLY by the
    +1 band-reference remap -- i.e. shifting the fork body's band refs back -1 recovers the donor body."""
    data = _alex100()
    eb0 = EbScript.from_bytes(data)
    n = eb0.entry_count
    band_lo = n - BAND
    shifted = _object.shift_slot_refs(data, band_lo, n - 1, 1)
    eb_sh = EbScript.from_bytes(shifted)

    out = _npc.inject_npc(data, 100, 200, model=None, reserve_party_band=True)
    eb1 = EbScript.from_bytes(out)
    for k in range(band_lo, n):                                   # donor char k -> fork char k+1
        assert _entry_body(eb1, k + 1) == _entry_body(eb_sh, k)


def test_inserted_npc_is_below_band_and_talkable():
    data = _alex100()
    n = EbScript.from_bytes(data).entry_count
    band_lo = n - BAND

    out = _npc.inject_npc(data, 120, 240, model=None, talk_text_id=77, reserve_party_band=True)
    eb1 = EbScript.from_bytes(out)
    new_band_lo = (n + 1) - BAND                      # the band shifted up one

    npc = eb1.entry(band_lo)
    assert not npc.empty
    assert band_lo < new_band_lo                      # the NPC sits BELOW the (now shifted) party band
    assert npc.func_by_tag(0) is not None             # Init
    assert npc.func_by_tag(3) is not None             # talk (_SpeakBTN)


def test_main_init_initobjects_remapped_and_npc_armed():
    data = _alex100()
    eb0 = EbScript.from_bytes(data)
    n = eb0.entry_count
    band_lo = n - BAND
    old = _main_init_object_targets(eb0)

    out = _npc.inject_npc(data, 90, 180, model=None, reserve_party_band=True)
    eb1 = EbScript.from_bytes(out)
    new = _main_init_object_targets(eb1)

    # every donor InitObject target is shifted +1 iff it was a band slot; the NPC slot (band_lo) is armed
    expect = sorted([t + 1 if t >= band_lo else t for t in old] + [band_lo])
    assert sorted(new) == expect


def test_result_is_structurally_clean():
    data = _alex100()
    base_errors = [i for i in eblint.lint_eb(data) if i.level == "error"]
    out = _npc.inject_npc(data, 64, 128, model=None, reserve_party_band=True)
    errors = [i for i in eblint.lint_eb(out) if i.level == "error"]
    assert errors == base_errors, f"insertion introduced eblint errors: {errors}"


def test_two_npcs_stack_below_band():
    data = _alex100()
    n = EbScript.from_bytes(data).entry_count
    out = _npc.inject_npc(data, 100, 200, model=None, reserve_party_band=True)
    out = _npc.inject_npc(out, 140, 220, model=None, reserve_party_band=True)
    eb = EbScript.from_bytes(out)
    assert eb.entry_count == n + 2
    assert [i for i in eblint.lint_eb(out) if i.level == "error"] == \
           [i for i in eblint.lint_eb(data) if i.level == "error"]


def test_synth_path_unchanged_by_new_param():
    """reserve_party_band defaults False -> the synthesize path is byte-identical to before."""
    data = _alex100()
    a = _npc.inject_npc(data, 100, 200, model=None)
    b = _npc.inject_npc(data, 100, 200, model=None, reserve_party_band=False)
    assert a == b


# ----------------------------------------------- regions: a NEW [[gateway]] / [[event]] below the band

def _errors(b):
    return [i for i in eblint.lint_eb(b) if i.level == "error"]


def _quad(x0, z0, x1, z1):
    from ff9mapkit.content import gateway as _gw
    return _gw.quad_zone([(x0, z0), (x1, z0), (x1, z1), (x0, z1)])


def test_gateway_seated_below_band():
    from ff9mapkit.content import gateway as _gw
    data = _alex100()
    n = EbScript.from_bytes(data).entry_count
    band_lo = n - BAND
    out = _gw.inject_gateway(data, 4100, zone=_quad(0, 0, 100, 100), reserve_party_band=True)
    eb = EbScript.from_bytes(out)
    assert eb.entry_count == n + 1
    reg = eb.entry(band_lo)
    assert not reg.empty and reg.type == 1                     # a region entry, below the (shifted) band
    assert any(i.op == 0x2B and i.imm(0) == 4100 for f in reg.funcs for i in eb.instrs(f)), "warps to 4100"
    assert _errors(out) == _errors(data)


def test_events_seated_below_band():
    from ff9mapkit.content import event as _event
    data = _alex100()
    n = EbScript.from_bytes(data).entry_count
    specs = [{"zone": [(0, 0), (100, 0), (100, 100), (0, 100)], "body": _event.give_gil(100), "once_flag": 8000},
             {"zone": [(200, 0), (300, 0), (300, 100), (200, 100)], "body": _event.give_item(1, 1),
              "once_flag": 8001}]
    out = _event.inject_events(data, specs, reserve_party_band=True)
    eb = EbScript.from_bytes(out)
    assert eb.entry_count == n + 3                             # 2 event regions + 1 shared arm entry
    assert _errors(out) == _errors(data)


def test_mixed_content_stacks_below_band_and_lints_clean():
    """NPC + gateway + events all seated below the band compose: the count grows by the total, the donor's
    character bodies are still recoverable (only +k band-ref remap), and the whole .eb lints clean."""
    from ff9mapkit.content import gateway as _gw
    from ff9mapkit.content import event as _event
    data = _alex100()
    eb0 = EbScript.from_bytes(data)
    n = eb0.entry_count
    band_lo = n - BAND
    band_bodies = {k: _entry_body(eb0, k) for k in range(band_lo, n)}

    out = _npc.inject_npc(data, 0, 2600, model=None, reserve_party_band=True)
    out = _gw.inject_gateway(out, 4100, zone=_quad(0, 0, 100, 100), reserve_party_band=True)
    out = _event.inject_events(out, [{"zone": [(0, 0), (100, 0), (100, 100), (0, 100)],
                                      "body": _event.give_gil(50), "once_flag": 8000}], reserve_party_band=True)
    eb = EbScript.from_bytes(out)
    assert eb.entry_count == n + 4                             # npc + gateway + (1 event region + 1 arm)
    assert _errors(out) == _errors(data)
    assert eb.to_bytes() == out                                # round-trip identity
    # every donor character body survived (shifted up by the 4 inserts, content == donor + band-ref remap)
    shifted = data
    for d in range(4):
        cur = EbScript.from_bytes(shifted).entry_count
        shifted = _object.shift_slot_refs(shifted, cur - BAND, cur - 1, 1)
    eb_sh = EbScript.from_bytes(shifted)
    for k in range(band_lo, n):
        assert _entry_body(eb, k + 4) == _entry_body(eb_sh, k), f"character {k}->{k+4} content drifted"
