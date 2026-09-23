"""Reproduce a real field's LOAD-TIME engine walkmesh hotfix in a fork.

A few fields rely on a hardcoded Memoria hotfix (BGI_triSetActive keyed on the real fldMapNo) that toggles
walkmesh-triangle active-state at field load (e.g. Gulug/Room blocks the broken wall). A fork runs at a custom
id, so a RAW guard is false and the hotfix never fires; a guard the custom engine routes through EffectiveFieldId
(s29/s30/s65) fires for a fork that records its donor. content.walkmesh_hotfix reproduces the load-time class by
prepending EnablePathTriangle(tri,state) to Main_Init -- only where the engine won't; the catalog
(walkmesh_hotfixes) classifies all ~11 fields against the patch stack and fork-report flags the rest as
lost-on-mint.
"""
from __future__ import annotations

import tomllib

import pytest

from ff9mapkit import data, idgated, walkmesh_hotfixes as WH
from ff9mapkit import forkreport
from ff9mapkit.content import walkmesh_hotfix as WHX
from ff9mapkit.eb import EbScript, opcodes

from ._patchstack import WRAPPED, net_added as _net_added

ENABLE_PATH_TRIANGLE = 0x9A


def _tag0_ops(ebb):
    eb = EbScript.from_bytes(ebb)
    f0 = eb.entry(0).func_by_tag(0)
    return [(i.op, list(i.args or [])) for i in eb.instrs(f0)]


# --- catalog ---------------------------------------------------------------------------------------------
def test_catalog_load_time_is_auto_with_toggles():
    h = WH.info(2356)                                            # Gulug/Room (broken-wall block) -- a RAW gate
    assert h is not None and h.kind == "load_time" and h.auto
    assert h.toggles == ((78, 0), (79, 0), (80, 0))
    assert WH.load_time_toggles(2356) == [[78, 0], [79, 0], [80, 0]]
    assert WH.load_time_toggles(2356, donor_recorded=False) == [[78, 0], [79, 0], [80, 0]]
    # 2161's gate is remapped (s65): the engine reproduces it on a donor-recorded fork, so the kit prepends it
    # only where no ForkDonorPatch row exists (a fork whose donor id did not resolve)
    assert WH.load_time_toggles("2161") == []                   # accepts a numeric string
    assert WH.load_time_toggles("2161", donor_recorded=False) == [[69, 0]]


def test_catalog_dynamic_is_not_auto():
    h = WH.info(2803)                                            # Daguerreo librarian -- tracks a story var
    assert h is not None and h.kind == "dynamic" and not h.auto
    assert WH.load_time_toggles(2803) == []                    # nothing statically reproducible
    h2 = WH.info(1753)                                          # opcode-augment -- also not auto
    assert h2.kind == "opcode_augment" and not h2.auto


def test_catalog_unknown_field_is_none():
    assert WH.info(99999) is None
    assert WH.info(None) is None
    assert WH.load_time_toggles(99999) == []
    assert set(WH._HOTFIXES) >= {2356, 2161, 2507, 2803, 900, 450, 1421}


# --- injector --------------------------------------------------------------------------------------------
def test_apply_prepends_enable_path_triangle_per_toggle():
    src = data.blank_field_bytes("us")
    out = WHX.apply_tri_toggles(src, [(78, 0), (79, 0), (80, 0)])
    assert EbScript.from_bytes(out).to_bytes() == out          # still a valid .eb (entry/func tables fixed)
    one = len(opcodes.encode(ENABLE_PATH_TRIANGLE, 0, 0))
    assert len(out) == len(src) + 3 * one
    ops = _tag0_ops(out)
    assert ops[0] == (ENABLE_PATH_TRIANGLE, [78, 0])           # tris off from frame 1, like the engine at load
    assert ops[1] == (ENABLE_PATH_TRIANGLE, [79, 0])
    assert ops[2] == (ENABLE_PATH_TRIANGLE, [80, 0])


def test_apply_state_is_coerced_to_bit():
    out = WHX.apply_tri_toggles(data.blank_field_bytes("us"), [(105, 1)])
    assert _tag0_ops(out)[0] == (ENABLE_PATH_TRIANGLE, [105, 1])


def test_no_toggles_is_a_noop():
    src = data.blank_field_bytes("us")
    assert WHX.apply_tri_toggles(src, []) == src               # byte-identical when there's nothing to do
    assert WHX.apply_tri_toggles(src, None) == src


# --- build wiring ----------------------------------------------------------------------------------------
def test_build_wires_walkmesh_tri_toggles_from_field_block(tmp_path):
    from ff9mapkit import build
    base = ('[field]\nid=4700\nname="F"\nborrow_bg="MGNT_MAP810_MN_MOG_0"\narea=56\ntext_block=8\n'
            '{flag}[camera]\npitch=30\ndistance=900\nfov=40\n[player]\nspawn=[0,0]\n')
    p = tmp_path / "f.field.toml"
    p.write_text(base.format(flag="walkmesh_tri_toggles=[[78,0],[79,0],[80,0]]\n"), encoding="utf-8")
    ops = _tag0_ops(build.build_script(build.FieldProject.load(p), "us", {}))
    assert ops[0] == (ENABLE_PATH_TRIANGLE, [78, 0])
    assert ops[1] == (ENABLE_PATH_TRIANGLE, [79, 0])
    assert ops[2] == (ENABLE_PATH_TRIANGLE, [80, 0])
    # absent -> unchanged (no EnablePathTriangle prepend)
    p.write_text(base.format(flag=""), encoding="utf-8")
    ops2 = _tag0_ops(build.build_script(build.FieldProject.load(p), "us", {}))
    assert ops2[0] != (ENABLE_PATH_TRIANGLE, [78, 0])


def test_build_validate_rejects_malformed_toggles(tmp_path):
    from ff9mapkit import build
    base = ('[field]\nid=4700\nname="F"\nborrow_bg="MGNT_MAP810_MN_MOG_0"\narea=56\ntext_block=8\n'
            'walkmesh_tri_toggles=[[78,2]]\n[camera]\npitch=30\ndistance=900\nfov=40\n[player]\nspawn=[0,0]\n')
    p = tmp_path / "f.field.toml"
    p.write_text(base, encoding="utf-8")
    problems = build.validate(build.FieldProject.load(p))
    assert any("walkmesh_tri_toggles" in x for x in problems)   # state 2 is not 0|1


# --- fork-report (lost-on-mint, of which the walkmesh hotfix is one entry) -------------------------------
def _lost_labels(eb, fid):
    return [lbl for lbl, _ in forkreport.analyze_eb(eb, field_id=fid).lost_on_mint]


def test_fork_report_lost_on_mint_includes_walkmesh():
    eb = data.blank_field_bytes("us")
    assert "walkmesh hotfix" in _lost_labels(eb, 2356)     # load-time, auto-reproduced
    assert "walkmesh hotfix" in _lost_labels(eb, 2803)     # dynamic, fork-in-place
    assert forkreport.analyze_eb(eb, field_id=0).lost_on_mint == []   # fixture id -> nothing
    txt = forkreport.format_report(forkreport.analyze_eb(eb, field_id=2803))
    assert "Lost on mint" in txt and "walkmesh hotfix" in txt


# --- engine-remapped (2507 Ipsen): a DELAYED hotfix the s29 engine reproduces; the kit must NOT also prepend a
#     toggle, which fires at LOAD -- before the field's treasure chests settle onto those tris -- dropping them a
#     floor (caught in-game 2026-06-23). delayed -> never prependable, but still catalogued/reported.
def test_catalog_engine_remapped_2507_not_auto():
    h = WH.info(2507)
    assert h is not None and h.kind == "load_time" and h.engine_remapped and h.delayed
    assert h.toggles == ((174, 0), (175, 0), (177, 0), (178, 0))  # catalogued for reporting ...
    assert not h.auto and WH.load_time_toggles(2507) == []        # ... but NOT auto-emitted (engine reproduces it)
    assert not h.prependable                                      # ... and never, even with no donor row:
    assert WH.load_time_toggles(2507, donor_recorded=False) == [] # an at-load prepend mis-times the chests
    assert WH.info(2356).auto                                     # the RAW at-load hotfix stays kit-reproduced
    h61 = WH.info(2161)                                           # remapped by s65, not delayed:
    assert h61.engine_remapped and not h61.delayed and h61.prependable
    assert not h61.auto and h61.needs_prepend(donor_recorded=False)


# --- the catalog follows the PATCH STACK (memoria-patches/, the engine's source of truth). A gate is REMAPPED when
#     the live stack writes it in its EffectiveFieldId form; engine_remapped means EVERY gate of the hotfix is, and
#     fork_tris is non-empty when ANY is. This is the check whose absence let s65 wrap 2161 while the catalog
#     still called it lost -- so forks of 2161 got the engine toggle AND the kit's prepend.
_FM = WRAPPED.format("==", "{}")
_DOE, _TOT = "EventEngine.DoEventCode.cs", "EventEngine.turnOffTriManually.cs"
# field -> [(patched file, the gate in its WRAPPED form, how many such sites the hotfix needs)]
_GATES = {
    2356: [("FieldMap.cs", _FM.format(2356), 1)],
    2161: [("FieldMap.cs", _FM.format(2161), 1)],
    2507: [("FieldMap.cs", _FM.format(2507), 2)],       # HonoAwake's StartCoroutine + DelayedActiveTri's re-check
    450: [(_DOE, r"effMapNo == 450 && po\.sid == 3 && posX == 363", 1)],
    1421: [(_DOE, r"effMapNo == 1421 && po\.sid == 5\b", 1)],
    1753: [(_DOE, r"effMapNo == 1753 && triangleID == 207", 1)],
    1606: [(_DOE, r"effMapNo == 1606 && triangleID == 107", 1)],
    900: [(_DOE, r"effMapNo == 900 && obj1 != null && scriptLevel == 2 && tagNumber == 11", 1),
          (_TOT, r"EffectiveFieldId", 1)],
    2803: [(_DOE, r"effMapNo == 2803 && obj1 != null && tagNumber == 18", 1), (_TOT, r"EffectiveFieldId", 1)],
    1900: [(_TOT, r"EffectiveFieldId", 1)],
    1455: [(_TOT, r"EffectiveFieldId", 1)],
    406: [("FieldMapActorController.cs", _FM.format(406), 1)],        # s65 wraps the collision rule
    1752: [("FieldMapActorController.cs", _FM.format(1752), 1)],      # raw -- no patch wraps it
}


def test_net_added_counts_the_stack_net_of_removals():
    raw, wrapped = b"        if (fldMapNo == 7)", b"        if (EffectiveFieldId(FF9StateSystem.Common.FF9.fldMapNo) == 7)"

    def patch(path, body):
        return b"--- a/%s\n+++ b/%s\n@@ -1,1 +1,1 @@\n%s\n" % (path, path, body)
    wrap = patch(b"A/FieldMap.cs", b"-" + raw + b"\n+" + wrapped)
    unwrap = patch(b"A/FieldMap.cs", b"-" + wrapped + b"\n+" + raw)
    context = patch(b"A/FieldMap.cs", b" " + wrapped + b"\n+        x();")
    elsewhere = patch(b"A/WMFieldMap.cs", b"-" + raw + b"\n+" + wrapped)
    pat = _FM.format(7)
    assert _net_added("FieldMap.cs", pat, [wrap]) == 1
    assert _net_added("FieldMap.cs", pat, [wrap, unwrap]) == 0      # a later patch that unwraps it wins
    assert _net_added("FieldMap.cs", pat, [wrap, context]) == 1     # a context line is not a new site
    assert _net_added("FieldMap.cs", pat, [elsewhere]) == 0         # another file's gate never counts


def test_catalog_engine_remap_follows_the_patch_stack():
    assert set(_GATES) == set(WH._HOTFIXES)                   # every catalogued hotfix names its engine gates
    # the effMapNo gates only mean "remapped" while s30's alias is still EffectiveFieldId(mapNo)
    assert _net_added(_DOE, r"Int32 effMapNo = Memoria\.DataPatchers\.EffectiveFieldId\(mapNo\)") == 1
    for fid, gates in _GATES.items():
        wrapped = [_net_added(f, pat) >= need for f, pat, need in gates]
        h = WH.info(fid)
        assert h.engine_remapped == all(wrapped), (fid, wrapped)
        assert bool(h.fork_tris) == any(wrapped), (fid, wrapped)
        assert set(h.fork_tris) <= set(h.tris), fid
        if h.engine_remapped:                                  # every gate fires on a fork -> every tri does
            assert set(h.fork_tris) == set(h.tris), fid
    assert {f for f, h in WH._HOTFIXES.items() if h.delayed} == {2507}


def test_no_donor_recorded_fork_gets_both_the_engine_and_the_prepend():
    """The 2161 double write, as an invariant: on a fork with a donor row, a tri the engine still toggles is never
    also prepended by the kit; with no row, the kit prepends exactly the prependable hotfixes."""
    for fid, h in WH._HOTFIXES.items():
        prepended = {t for t, _ in WH.load_time_toggles(fid)}
        assert not prepended & set(h.fork_tris), fid
        assert bool(WH.load_time_toggles(fid, donor_recorded=False)) == h.prependable, fid
    assert {f for f, h in WH._HOTFIXES.items() if h.auto} == {2356}
    assert {f for f in WH._HOTFIXES if WH.load_time_toggles(f, donor_recorded=False)} == {2356, 2161}


def test_extract_no_toggle_line_for_engine_remapped():
    from ff9mapkit.extract import _walkmesh_hotfix_line
    line = _walkmesh_hotfix_line(2507)
    assert "walkmesh_tri_toggles = [" not in line                 # no ACTIVE directive (a prepend would mis-time chests)
    assert all(ln.lstrip().startswith("#") for ln in line.splitlines() if ln.strip())  # only comments
    assert "engine fork-donor remap" in line                      # documented as engine-reproduced
    assert "walkmesh_tri_toggles = [[78, 0]" in _walkmesh_hotfix_line(2356)   # a normal auto hotfix still authors it


def _toggles_of(line):
    """What the emitted line AUTHORS -- parsed as TOML under [field], never grepped (a comment is not a key)."""
    return tomllib.loads("[field]\n" + line)["field"].get("walkmesh_tri_toggles")


def test_extract_line_for_2161_follows_the_donor_row():
    from ff9mapkit.extract import _walkmesh_hotfix_line as line
    # --native / --verbatim: the donor is recorded -> ForkDonorPatch -> the s65 engine gate fires; no prepend
    rec = line(2161, fork_id=30999, donor_recorded=True)
    assert _toggles_of(rec) is None and "engine fork-donor remap" in rec and "only repeat it" in rec
    assert line(2161) == rec                                      # the default is a donor-recorded fork
    # a fork that records no donor -> no row -> the engine gate stays false: the kit prepends
    ed = line(2161, fork_id=30999, donor_recorded=False)
    assert _toggles_of(ed) == [[69, 0]] and "records no donor" in ed
    # forked IN PLACE on 2161: the engine's own gate fires as on the real field -- nothing to author
    assert _toggles_of(line(2161, fork_id=2161, donor_recorded=False)) is None
    assert _toggles_of(line(2356, fork_id=2356)) is None          # even the RAW gate fires at the real id
    assert _toggles_of(line(2356, fork_id=30999, donor_recorded=False)) == [[78, 0], [79, 0], [80, 0]]
    assert "raw fldMapNo 2356" in line(2356)


def test_extract_line_for_a_delayed_hotfix_without_a_donor_row_says_lost():
    from ff9mapkit.extract import _walkmesh_hotfix_line as line
    lost = line(2507, fork_id=30999, donor_recorded=False)
    assert _toggles_of(lost) is None and "LOST on this fork" in lost    # no prepend can time it, no engine row
    assert "mis-time prop placement" in line(2507)


def test_extract_line_is_empty_for_non_load_time_hotfixes():
    from ff9mapkit.extract import _walkmesh_hotfix_line as line
    for fid in (450, 1421, 1753, 1606, 2803, 900, 1900, 1455):   # remapped or not, import emits nothing for them
        assert line(fid) == "" and line(fid, donor_recorded=False) == "", fid


def test_fork_report_engine_remapped_wording():
    eb = data.blank_field_bytes("us")
    rep = forkreport.analyze_eb(eb, field_id=2507)
    det = dict(rep.lost_on_mint).get("walkmesh hotfix")
    assert det is not None and "reproduced by the engine fork-donor remap" in det
    assert "auto-reproduced" not in det and "fork-in-place" not in det
    assert "reproduced by the engine fork-donor remap" in forkreport.format_report(rep)


def test_fork_report_counts_only_the_unreproduced_hotfixes_as_lost():
    """fork-report's verdict steers to fork-in-place unless the walkmesh detail says ``reproduced``: every
    remapped hotfix (2161 included -- no longer 'lost on a mint') drops out; a partly-remapped one (900, 2803:
    turnOffTriManually is raw) and a raw one (1900) stay losses."""
    def loses(fid):
        v = forkreport._verdict_line(forkreport.ForkReport(field_id=fid, lost_on_mint=idgated.lost_on_mint(fid)))
        return "Loses walkmesh hotfix" in v
    for fid in (2161, 2507, 450, 1421, 1753, 1606, 2356):
        assert not loses(fid), fid
    for fid in (900, 2803, 1900, 1455):
        assert loses(fid), fid
    det = dict(idgated.lost_on_mint(2161))["walkmesh hotfix"]
    assert "reproduced by the engine fork-donor remap on a fork that records its donor" in det
    assert "(--verbatim)" in dict(idgated.lost_on_mint(450))["walkmesh hotfix"]
    part = dict(idgated.lost_on_mint(900))["walkmesh hotfix"]
    assert "fork-in-place" in part and "tri 62" in part and "reproduced" not in part


# --- the real import (install-gated): the toml a fork of 2161 gets matches whether its donor is recorded.
def _game_ready():
    try:
        import UnityPy  # noqa: F401,PLC0415
        from ff9mapkit import config  # noqa: PLC0415
        return config.find_game_path(None) is not None
    except Exception:
        return False


def _raw(p):
    return tomllib.loads(p.read_text(encoding="utf-8"))


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_2161_records_the_donor_on_every_fork_kind(tmp_path):
    from ff9mapkit import build, extract
    donor = "2161"          # L. Castle/Guest Room (disc 3); by id -- its FBG is shared with 611/1361 (ambiguous)
    for kw in ({}, {"verbatim": True}):                           # --native / --verbatim record the donor
        _, p = extract.write_native_project(donor, tmp_path / f"n{len(kw)}", name="LB", field_id=30999, **kw)
        raw = _raw(p)
        assert build.donor_field_id(raw) == 2161, kw              # -> the build emits `30999 2161`
        assert "walkmesh_tri_toggles" not in raw["field"], kw    # -> the s65 engine gate covers tri 69
    # --editable records it too (it used to record none, so its only copy was the kit's prepend)
    _, p = extract.write_editable_project(donor, tmp_path / "ed", name="LB", field_id=30999)
    raw = _raw(p)
    assert raw["field"]["source_field"] == 2161 and build.donor_field_id(raw) == 2161
    assert "walkmesh_tri_toggles" not in raw["field"]
    # forked IN PLACE on 2161: no self-mapping, and the engine's own gate fires as on the real field
    _, p = extract.write_editable_project(donor, tmp_path / "ip", name="LB", field_id=2161)
    raw = _raw(p)
    assert "source_field" not in raw["field"] and "walkmesh_tri_toggles" not in raw["field"]


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_editable_import_of_2507_keeps_its_delayed_hotfix_through_the_engine(tmp_path):
    """2507's hotfix fires 0.5s AFTER load, so no Main_Init prepend can reproduce it -- only the engine remap can,
    and only on a fork with a ForkDonorPatch row. An --editable fork used to record no donor and lost it."""
    from ff9mapkit import build, extract
    _, p = extract.write_editable_project("2507", tmp_path, name="IPSN_EDIT", field_id=30999)
    raw = _raw(p)
    assert build.donor_field_id(raw) == 2507                      # -> the build/deploy emit `30999 2507`
    assert "walkmesh_tri_toggles" not in raw["field"]             # an at-load prepend would drop the chests a floor
    text = p.read_text(encoding="utf-8")
    assert "reproduced by the engine fork-donor remap" in text and "LOST" not in text


# --- the delayed pass also detaches a kit-built PLAYER: the build re-attaches it ----------------------------
WAIT, SET_PATHING = 0x22, 0xA8


def _player_loop_ops(ebb):
    from ff9mapkit.content.npc import _find_player_entry
    eb = EbScript.from_bytes(ebb)
    return [(i.op, list(i.args or [])) for i in eb.instrs(eb.entry(_find_player_entry(eb)).func_by_tag(1))]


def test_catalog_2507_detaches_actors():
    assert WH.detaching_ids() == (2507,)                     # FieldMap.DelayedActiveTri, the only such pass
    assert WH.info(2507).detaches_actors and WH.info(2507).delayed


def test_reattach_turns_the_idle_player_loop_into_a_guard():
    """A fixed one-shot (Wait 30, SetPathing 1) raced the engine's pass in-game and lost: when the pass lands
    relative to the script varies with the load. So the player's idle Loop becomes a guard: every frame, when
    the player has control (B_SYSVAR[2]) but no triangle (B_BGIID -1), SetPathing(1)."""
    src = data.blank_field_bytes("us")
    out = WHX.reattach_player(src)
    assert EbScript.from_bytes(out).to_bytes() == out        # still a valid .eb
    assert _player_loop_ops(src) == [(WAIT, [1]), (0x01, [0x10000 - 6])]   # the template's idle loop
    ops = _player_loop_ops(out)
    assert [op for op, _ in ops] == [0x05, 0x02, SET_PATHING, WAIT, 0x01]
    assert ops[2][1] == [1] and ops[3][1] == [1]              # SetPathing(1), then Wait(1) -- every frame
    assert ops[4][1] == [0x10000 - len(WHX.reattach_loop_body())]   # the jump closes the whole body
    from ff9mapkit.eb import exprasm
    assert exprasm.assemble(WHX.REATTACH_COND + " B_EXPR_END") in out
    assert _tag0_ops(out) == _tag0_ops(src)                   # Main_Init untouched
    with pytest.raises(ValueError, match="idle loop"):        # a Loop someone already changed is not replaced
        WHX.reattach_player(out)


def test_build_reattaches_the_player_only_where_the_pass_detaches_it(tmp_path):
    from ff9mapkit import build
    base = ('[field]\nid={fid}\nname="F"\narea=43\ntext_block=739\n{extra}'
            '[camera]\npitch=30\ndistance=900\nfov=40\n[player]\nspawn=[0,0]\n')
    head = [0x05, 0x02, SET_PATHING, WAIT, 0x01]
    cases = {"donor": (30999, "source_field = 2507\n", True),               # --native / --editable
             "in_place": (2507, "", True),                                  # EffectiveFieldId(2507) == 2507
             "borrow": (30999, 'borrow_bg = "IPSN_MAP745A_IP_HL2_0"\n', True),   # a campaign BG-borrow member
             "other_donor": (30999, "source_field = 600\n", False),
             "other_borrow": (30999, 'borrow_bg = "MGNT_MAP810_MN_MOG_0"\n', False),
             "novel": (30999, "", False)}
    for name, (fid, extra, want) in cases.items():
        p = tmp_path / f"{name}.field.toml"
        p.write_text(base.format(fid=fid, extra=extra), encoding="utf-8")
        proj = build.FieldProject.load(p)
        assert (build.detaching_donor(proj) == 2507) is want, name
        assert ([op for op, _ in _player_loop_ops(build.build_script(proj, "us", {}))] == head) is want, name
