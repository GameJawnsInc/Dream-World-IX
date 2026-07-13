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


# ---- rung 5: the ATTRIBUTED decoder + arrival-aware import ---------------------------------------
def test_scan_arrival_table_attributes_alexandria():
    # the real switch form: Alexandria Main Street (fixture) -- entrance -> placement, byte-grounded
    from pathlib import Path
    raw = (Path(__file__).parent / "fixtures" / "alex100-us.eb.bytes").read_bytes()
    t = eventscan.scan_arrival_table(raw)
    assert t["reads_entrance"] and t["unattributed"] == 0
    by_ent = {r["entrance"]: r for r in t["table"]}
    assert by_ent[201]["pos"] == [0, 6092] and by_ent[201]["face"] == 0
    assert by_ent[231]["pos"] == [654, 1073] and by_ent[231]["face"] == 64
    assert by_ent[204]["pos"] == [0, 332] and by_ent[204]["face"] == 128
    assert t["default"]["pos"] == [0, 100] and t["default"]["face"] == 128


def test_scan_arrival_table_round_trips_the_kit_form():
    # the if-chain form the kit compiles: author -> build -> the SAME attributed table comes back
    src = data.blank_field_bytes("us")
    out = N.set_player_spawn(src, 5, -600)
    out = N.set_player_facing(out, 64)
    out = N.inject_player_arrivals(out, [{"entrance": 201, "pos": [400, -900], "face": 128},
                                         {"entrance": 2, "pos": [-350, -1500]}])
    t = eventscan.scan_arrival_table(out)
    by_ent = {r["entrance"]: r for r in t["table"]}
    assert by_ent[201]["pos"] == [400, -900] and by_ent[201]["face"] == 128
    assert by_ent[2]["pos"] == [-350, -1500] and by_ent[2]["face"] is None
    assert t["default"]["pos"] == [5, -600] and t["default"]["face"] == 64


def test_player_block_renders_the_donor_table():
    from ff9mapkit.extract import _player_block
    meta = {"player_start": [10, -20], "player_arrivals": [
        {"entrance": 204, "pos": [0, 332], "face": 128, "y": None},
        {"entrance": 201, "pos": [0, 6092], "face": 0, "y": None},
        {"entrance": 201, "pos": [7, 7], "face": 300, "y": None},     # dup: LAST wins; face out of compass
        {"entrance": -3, "pos": [1, 1], "face": None, "y": None},     # negative: dropped (build would reject)
    ]}
    s = _player_block(meta)
    assert s.startswith("[player]\nspawn = [10, -20]\n")
    assert s.count("[[player.arrival]]") == 2                          # 201 (deduped) + 204; -3 dropped
    assert "entrance = 201\npos = [7, 7]\n" in s                       # last block won...
    assert "face = 300" not in s                                       # ...its bad facing omitted
    assert "entrance = 204\npos = [0, 332]\nface = 128\n" in s


def test_player_block_without_rows_is_byte_identical_to_before():
    from ff9mapkit.extract import _player_block
    assert _player_block({"player_start": [0, -500]}) == "[player]\nspawn = [0, -500]\n\n"
    assert _player_block({"player_start": [0, -500], "player_arrivals": []}) == "[player]\nspawn = [0, -500]\n\n"


def test_emitted_rows_build_and_scan_back(tmp_path):
    # end-to-end offline: a rendered [player] block builds, and the built .eb decodes to the donor table
    from ff9mapkit import build
    from ff9mapkit.extract import _player_block
    meta = {"player_start": [0, -500], "player_arrivals": [
        {"entrance": 201, "pos": [400, -900], "face": 128, "y": None},
        {"entrance": 231, "pos": [-350, -1500], "face": None, "y": -49},
    ]}
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=4700\nname="F"\nborrow_bg="X"\narea=21\ntext_block=8\n'
                 '[camera]\npitch=30\ndistance=900\nfov=40\n' + _player_block(meta), encoding="utf-8")
    t = eventscan.scan_arrival_table(build.build_script(build.FieldProject.load(p), "us", {}))
    by_ent = {r["entrance"]: r for r in t["table"]}
    assert by_ent[201]["pos"] == [400, -900] and by_ent[201]["face"] == 128
    assert by_ent[231]["pos"] == [-350, -1500]
    assert t["default"]["pos"] == [0, -500]


# ---- rung 3: the campaign-graph entrance audit (campaign.lint_campaign (g2)) --------------------
def _campaign_plan(tmp_path, *, edges, member_content=None, verbatim=False, entry_entrance=0):
    from ff9mapkit import campaign
    members = [campaign.Member(300, 6000, "A", "borrow", 11, "", "A/A.field.toml", False),
               campaign.Member(301, 6001, "B", "borrow", 11, "", "B/B.field.toml", False)]
    plan = campaign.CampaignPlan(name="C", mod_folder="M", id_base=6000,
                                 flag_base=campaign.FIRST_SAFE_FLAG, flags_per_field=64,
                                 entry_name="A", entry_entrance=entry_entrance,
                                 members=members, edges=edges)
    plan.verbatim = verbatim
    for m in members:
        d = tmp_path / m.name
        d.mkdir(parents=True, exist_ok=True)
        extra = (member_content or {}).get(m.name, "")
        (d / f"{m.name}.field.toml").write_text(
            f'[field]\nid = {m.new_id}\nname = "{m.name}"\narea = 11\n{extra}', encoding="utf-8")
    return plan


def _arrival_warnings(tmp_path, **kw):
    from ff9mapkit import campaign
    _errors, warnings = campaign.lint_campaign(_campaign_plan(tmp_path, **kw), tmp_path)
    return [w for w in warnings if "arrival" in w or "entrance" in w]


_TWO_DOORS = [{"frm": "A", "to": "B", "entrance": 1}, {"frm": "A", "to": "B", "entrance": 2}]


def test_campaign_lint_flags_the_arrival_collapse(tmp_path):
    # two doors with distinct entrances, no rows -> "every door lands on the one spawn"
    w = _arrival_warnings(tmp_path, edges=_TWO_DOORS)
    assert any("B" in x and "no [[player.arrival]] rows" in x and "2 doors" in x for x in w)


def test_campaign_lint_full_coverage_is_silent(tmp_path):
    rows = ('[[player.arrival]]\nentrance = 1\npos = [0, 0]\n'
            '[[player.arrival]]\nentrance = 2\npos = [9, 9]\n')
    assert _arrival_warnings(tmp_path, edges=_TWO_DOORS, member_content={"B": rows}) == []


def test_campaign_lint_partial_coverage_and_dead_row(tmp_path):
    rows = ('[[player.arrival]]\nentrance = 1\npos = [0, 0]\n'
            '[[player.arrival]]\nentrance = 7\npos = [9, 9]\n')
    w = _arrival_warnings(tmp_path, edges=_TWO_DOORS, member_content={"B": rows})
    assert any("inbound entrance 2" in x and "falls through" in x for x in w)   # door 2 uncovered
    assert any("entrance 7 is not routed" in x for x in w)                      # row 7 unreachable


def test_campaign_lint_same_entrance_doors_cant_dispatch(tmp_path):
    # two sources both writing entrance 0 -> the destination can't tell them apart
    w = _arrival_warnings(tmp_path, edges=[{"frm": "A", "to": "B", "entrance": 0},
                                           {"frm": "B", "to": "B", "entrance": 0}])
    assert any("can't tell them apart" in x and "distinct entrance=" in x for x in w)


def test_campaign_lint_entry_entrance_counts_as_inbound(tmp_path):
    # the entry member is entered from OUTSIDE with entry_entrance -- a row for it is NOT a dead row
    rows = '[[player.arrival]]\nentrance = 5\npos = [0, 0]\n'
    w = _arrival_warnings(tmp_path, edges=[], member_content={"A": rows}, entry_entrance=5)
    assert not any("not routed" in x for x in w)


def test_campaign_lint_verbatim_members_exempt_and_rows_flagged(tmp_path):
    # a verbatim member carries the donor table: no collapse warning without rows, IGNORED warning with
    assert _arrival_warnings(tmp_path, edges=_TWO_DOORS, verbatim=True) == []
    rows = '[[player.arrival]]\nentrance = 1\npos = [0, 0]\n'
    w = _arrival_warnings(tmp_path, edges=_TWO_DOORS, member_content={"B": rows}, verbatim=True)
    assert any("IGNORED on a verbatim member" in x for x in w)


# ---- rung 3: the field-local checks (build.lint_player_arrivals) --------------------------------
def test_field_lint_verbatim_dead_keys(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid = 6100\nname = "V"\narea = 11\n[verbatim_eb]\nbin = "x.bin"\n'
                 '[player]\nface = 64\n[[player.arrival]]\nentrance = 1\npos = [0, 0]\n', encoding="utf-8")
    out = build.lint_player_arrivals(build.FieldProject.load(p))
    assert any("IGNORED on a verbatim fork" in x and "[[player.arrival]]" in x and "[player] face" in x
               for x in out)


def test_field_lint_self_loop_coverage(tmp_path):
    from ff9mapkit import build
    base = ('[field]\nid = 4003\nname = "S"\narea = 11\n[player]\nspawn = [0, 0]\n'
            '[[player.arrival]]\nentrance = 1\npos = [5, 5]\n'
            '[[gateway]]\nto = 4003\nentrance = 1\nzone = [[0,0],[1,0],[1,1],[0,1]]\n')
    p = tmp_path / "f.field.toml"
    p.write_text(base, encoding="utf-8")
    assert build.lint_player_arrivals(build.FieldProject.load(p)) == []          # covered -> silent
    p.write_text(base + '[[gateway]]\nto = 4003\nentrance = 9\nzone = [[2,2],[3,2],[3,3],[2,3]]\n',
                 encoding="utf-8")
    out = build.lint_player_arrivals(build.FieldProject.load(p))
    assert any("self-loop" in x and "entrance 9" in x for x in out)


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
