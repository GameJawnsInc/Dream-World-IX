"""The worldmap-exit gateway + the direct entrance trigger (the continent-entrance pair).

Game-gated like the transplant proofs: the cascade is extracted from the real install.
"""
import pytest


def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")


def test_cascade_extraction():
    """The shared exit cascade: the instruction-aligned common block of the two
    byte-verified carriers (300 e2/tag2, 2800 e21/tag2) -- 19 WorldMap arms, opens
    with the ScenarioCounter-read expression, parses cleanly end to end."""
    from ff9mapkit.content.worldexit import cascade_bytes
    from ff9mapkit.eb.disasm import read_code
    c = cascade_bytes()
    assert len(c) > 500
    assert c[:3] == bytes([0x05, 0xDC, 0x00])        # the first SC-band gate
    pos, wm = 0, 0
    while pos < len(c):
        ins, pos = read_code(c, pos)
        wm += ins.op == 0xB6
    assert pos == len(c) and wm == 19                # every WorldMap arm, clean parse


def test_worldmap_exit_body_shape():
    """[usercontrol guard] -> [D8:2 = 62: the generic-return key -- its arm runs
    D8:2=0 + WorldMap(9009) in every band = the persisted-position arrival;
    0/un-cased keys hit the switch default, a bare RETURN that never warps
    (playtest-proven dead door)] -> [the verbatim cascade]."""
    from ff9mapkit.content import region as R
    from ff9mapkit.content.worldexit import cascade_bytes, worldmap_exit_body
    b = worldmap_exit_body()
    assert b.startswith(R.MOVEMENT_GATE)
    key_write = bytes([0x05, 0xD8, 0x02, 0x7D, 62, 0x00, 0x2C, 0x7F])
    assert b[len(R.MOVEMENT_GATE):len(R.MOVEMENT_GATE) + 8] == key_write
    assert b.endswith(cascade_bytes())
    # on-exit story writes slot between the guard and the key write
    b2 = worldmap_exit_body(on_exit_body=b"\xaa\xbb")
    assert b2[len(R.MOVEMENT_GATE):len(R.MOVEMENT_GATE) + 2] == b"\xaa\xbb"


def test_entrance_func_body_direct():
    """The direct trigger: the proven template's 12-byte vehicle/state gate verbatim,
    the conditional skip re-pointed over a bare Field(id), return. 20 bytes; the gate
    bytes are byte-identical to the template's own."""
    from ff9mapkit.eb.model import EbScript
    from ff9mapkit.world.entrance import (TEMPLATE_TAG, entrance_func_body_direct,
                                          load_world_dispatchers)
    disp = load_world_dispatchers()
    w00 = EbScript(disp["evt_world_world00"])
    f = next(f for e in w00.entries for f in e.funcs if f.tag == TEMPLATE_TAG)
    tpl = w00.data[f.abs_start:f.abs_end]
    b = entrance_func_body_direct(6500, dispatchers=disp)
    assert len(b) == 20
    assert b[:12] == tpl[:12]                        # the gate, verbatim
    assert b[12:15] == bytes([0x02, 0x04, 0x00])     # JZ re-pointed over Field
    assert b[15:19] == bytes([0x2B, 0x00, 6500 & 0xFF, 6500 >> 8])
    assert b[19] == 0x04                             # return
    with pytest.raises(ValueError):
        entrance_func_body_direct(0x8000, dispatchers=disp)   # past Int16
