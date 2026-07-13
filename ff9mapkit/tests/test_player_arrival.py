"""[player] face + [[player.arrival]] -- the destination-side arrival dispatch (field-entry rungs 1+2).

The oracle is the kit's own real-field decoder: ``eventscan.scan_player_arrivals`` reads the exact
byte pattern real fields use (a D8:2 read + D9(0)/D9(4)/D9(6) const blocks), so an authored table
must round-trip through it (author -> build -> scan -> the same table)."""
from __future__ import annotations

import pytest

from ff9mapkit import data, eventscan
from ff9mapkit.content import npc as N
from ff9mapkit.eb import EbScript

SET_MODEL = 0x2F


def _player_init(ebb):
    eb = EbScript.from_bytes(ebb)
    pe = N._find_player_entry(eb)
    return eb, eb.entry(pe).func_by_tag(0)


def test_facing_is_a_pure_const_patch():
    src = data.blank_field_bytes("us")
    out = N.set_player_facing(src, 64)
    assert len(out) == len(src)                       # a const patch, not an insert
    before = eventscan.scan_player_arrivals(src)["arrivals"][0]
    after = eventscan.scan_player_arrivals(out)["arrivals"][0]
    assert after == (before[0], before[1], 64)        # face changed, spawn x/z untouched


def test_arrival_table_round_trips_through_the_decoder():
    src = data.blank_field_bytes("us")
    out = N.inject_player_arrivals(src, [
        {"entrance": 1, "pos": [400, -900], "face": 128},
        {"entrance": 2, "pos": [-350, -1500]},
    ])
    assert EbScript.from_bytes(out).to_bytes() == out  # still a valid .eb
    t = eventscan.scan_player_arrivals(out)
    assert t["reads_entrance"]
    assert (400, -900, 128) in t["arrivals"]
    assert (-350, -1500, None) in t["arrivals"]
    assert t["distinct"] == 3                          # the default spawn + the 2 doors


def test_dispatch_sits_before_object_creation():
    # the if-chain must land before SetModel/CreateObject so the overridden consts are what the
    # engine creates the player FROM (pre-creation placement: frame 0, no base-spawn flash)
    src = data.blank_field_bytes("us")
    out = N.inject_player_arrivals(src, [{"entrance": 7, "pos": [111, -222]}])
    eb, f0 = _player_init(out)
    body = out[f0.abs_start:f0.abs_end]
    cond = bytes([0x05, 0xD8, 0x02, 0x7D, 7, 0, 0x20, 0x7F])   # if (D8:2 == 7)
    set_model = next(i.off - f0.abs_start for i in eb.instrs(f0) if i.op == SET_MODEL)
    assert body.find(cond) != -1 and body.find(cond) < set_model


def test_default_spawn_still_patchable_after_arrivals():
    # set_player_spawn anchors on the FIRST D9(0) const = the default block, not an arrival row
    src = data.blank_field_bytes("us")
    out = N.inject_player_arrivals(src, [{"entrance": 1, "pos": [400, -900]}])
    out = N.set_player_spawn(out, 55, -655)
    t = eventscan.scan_player_arrivals(out)
    assert t["arrivals"][0][:2] == (55, -655)          # the default block
    assert (400, -900, None) in t["arrivals"]          # the arrival row intact


def _build(tmp_path, player_block):
    from ff9mapkit import build
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=4700\nname="F"\nborrow_bg="X"\narea=21\ntext_block=8\n'
                 '[camera]\npitch=30\ndistance=900\nfov=40\n' + player_block, encoding="utf-8")
    return build.build_script(build.FieldProject.load(p), "us", {})


def test_build_wires_face_and_arrivals(tmp_path):
    ebb = _build(tmp_path, '[player]\nspawn=[0,-500]\nface=192\n'
                           '[[player.arrival]]\nentrance=1\npos=[300,-800]\nface=64\n'
                           '[[player.arrival]]\nentrance=2\npos=[-300,-800]\n')
    t = eventscan.scan_player_arrivals(ebb)
    assert t["arrivals"][0] == (0, -500, 192)          # [player] spawn + face = the default block
    assert (300, -800, 64) in t["arrivals"]
    assert (-300, -800, None) in t["arrivals"]
    assert t["distinct"] == 3


def test_build_without_new_keys_is_unchanged(tmp_path):
    # the feature is strictly opt-in: a spawn-only [player] builds byte-identically to before
    a = _build(tmp_path, '[player]\nspawn=[0,-500]\n')
    t = eventscan.scan_player_arrivals(a)
    assert t["arrivals"] == [(0, -500, 0)] and t["distinct"] == 1


@pytest.mark.parametrize("block,msg", [
    ('[player]\nspawn=[0,0]\nface=999\n', "face must be 0-255"),
    ('[[player.arrival]]\nentrance=1\npos=[0,0]\n[[player.arrival]]\nentrance=1\npos=[9,9]\n', "duplicated"),
    ('[[player.arrival]]\nentrance=-1\npos=[0,0]\n', "negative"),
    ('[[player.arrival]]\nentrance=1\n', "pos"),
    ('[[player.arrival]]\nentrance=1\npos=[0,0]\nface=300\n', "face must be 0-255"),
])
def test_build_rejects_malformed_rows(tmp_path, block, msg):
    with pytest.raises(ValueError, match=msg):
        _build(tmp_path, block)


def test_lint_flags_an_off_mesh_arrival(tmp_path):
    # arrival rows get the same placement advisory the spawn has -- an off-walkmesh pos warns
    from pathlib import Path

    from ff9mapkit.build import FieldProject, build_mod
    fix = Path(__file__).parent / "fixtures"
    (tmp_path / "camera.bgx").write_bytes((fix / "grgr.bgx").read_bytes())
    (tmp_path / "f.field.toml").write_text(
        '[field]\nid = 4003\nname = "X"\narea = 21\n\n[camera]\nborrow = "camera.bgx"\n\n'
        '[walkmesh]\nquad = [[-500, -500], [500, -500], [500, 500], [-500, 500]]\nframe = "world"\n\n'
        '[player]\nspawn = [0, 0]\n\n'
        '[[player.arrival]]\nentrance = 1\npos = [9000, 9000]\n\n'      # off the +-500 quad -> warn
        '[[player.arrival]]\nentrance = 2\npos = [0, 100]\n',           # on it -> silent
        encoding="utf-8")
    info = build_mod([FieldProject.load(tmp_path / "f.field.toml")], tmp_path / "mod")
    assert any("player.arrival" in w and "entrance 1" in w and "off the walkmesh" in w
               for w in info["warnings"])
    assert not any("entrance 2" in w for w in info["warnings"])
