"""THE FORK WALKMESH-LITERAL LINT (walkmesh-sensor rung 1, L5) -- donor code keys on walkmesh TRIANGLE ids / FLOOR
indices as literals, and a fork that ships a rebuilt walkmesh must be told when it moved them.

Three layers under test:
  * ``disasm.walkmesh_reads`` -- the DECODED scanner (never a byte regex): B_BGIID/B_BGIFLOOR reads classified
    compare/switch/store/other + EnablePathTriangle 0x9A / EnablePath 0xCB immediates.
  * ``build._donor_code_sites`` over ``build.DONOR_CODE_LANES`` -- the scan set, closed against the build's readers.
  * ``build._lint_fork_walkmesh_ids`` -- early-outs, tri/floor STABILITY, emission, cap.
Mutation targets are named in brackets ([M10], [M11], ...) at the test that bites them.
"""
from __future__ import annotations

import ast
import re
import struct
from pathlib import Path

import pytest

from ff9mapkit import build
from ff9mapkit import walkmesh_hotfixes as whf
from ff9mapkit.content import object as _object
from ff9mapkit.eb import cmdasm, disasm
from ff9mapkit.eb.model import pack_entry
from ff9mapkit.scene import bgi


def _asm(text: str) -> bytes:
    return cmdasm.assemble_block(text)


def _reads(text: str) -> list:
    b = _asm(text)
    return disasm.walkmesh_reads(b, 0, len(b))


def _minimal_eb(body: bytes) -> bytes:
    """A valid 1-entry / 1-func (tag 0) .eb wrapping ``body``."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1
    blob = pack_entry(0, [(0, body)])
    return bytes(head) + struct.pack("<HHBBH", 8, len(blob), 0, 0, 0) + blob


# ============================================================================ the decoded scanner

def test_compare_literal_after_the_read():
    (r,) = _reads("SET({B_PTR(250) B_BGIFLOOR const(2) B_EQ B_EXPR_END})\nRET()")
    assert (r.kind, r.subject, r.role, r.literals, r.op, r.off) == ("floor", "B_PTR(250)", "compare", (2,), 0x05, 0)


def test_compare_literal_before_the_read():
    (r,) = _reads("SET({const(220) B_PTR(21) B_BGIID B_NE B_EXPR_END})\nRET()")
    assert (r.kind, r.subject, r.role, r.literals) == ("tri", "B_PTR(21)", "compare", (220,))


def test_compare_every_compare_op_and_a_const_subject():
    for op in ("B_LT", "B_GT", "B_LE", "B_GE", "B_LT_E", "B_GT_E", "B_LE_E", "B_GE_E",
               "B_EQ", "B_NE", "B_EQ_E", "B_NE_E"):
        (r,) = _reads(f"SET({{const(3) B_BGIFLOOR const(1) {op} B_EXPR_END}})\nRET()")
        assert (r.subject, r.role, r.literals) == ("const(3)", "compare", (1,)), op


def test_compare_before_form_needs_a_single_token_subject():
    # `const(7) <x const(1) B_PLUS> B_BGIFLOOR B_EQ`: tok[j-2] is the B_PLUS operand, not the compared literal
    (r,) = _reads("SET({const(7) Global.Int16[2] const(1) B_PLUS B_BGIFLOOR B_EQ B_EXPR_END})\nRET()")
    assert (r.subject, r.role, r.literals) == ("expr", "other", ())


def test_switch_explicit_0x06_keys_on_its_case_values_not_the_default():
    (r,) = _reads("SET({B_PTR(250) B_BGIFLOOR B_EXPR_END})\nSWITCHEX(Ld, 1, La, 3, Lb)\n"
                  "La:\nRET()\nLb:\nRET()\nLd:\nRET()")
    assert (r.kind, r.role, r.literals) == ("floor", "switch", (1, 3))


def test_switch_contiguous_0x0b_keys_on_base_plus_n():
    (r,) = _reads("SET({B_PTR(255) B_BGIFLOOR B_EXPR_END})\nSWITCH(2, Ld, La, Lb)\n"
                  "La:\nRET()\nLb:\nRET()\nLd:\nRET()")
    assert (r.subject, r.role, r.literals) == ("B_PTR(255)", "switch", (2, 3))


def test_a_selector_not_followed_by_a_switch_is_other():
    (r,) = _reads("SET({B_PTR(250) B_BGIFLOOR B_EXPR_END})\nRET()")
    assert r.role == "other" and r.literals == ()


def test_store_and_other():
    rs = _reads("SET({Global.Int16[10] B_PTR(250) B_BGIFLOOR B_LET B_EXPR_END})\n"
                "SET({Global.Int16[12] B_PTR(250) B_BGIFLOOR B_PLUS_LET B_EXPR_END})\n"
                "SET({B_PTR(250) B_BGIID const(1) B_PLUS B_EXPR_END})\nRET()")
    assert [(r.kind, r.role) for r in rs] == [("floor", "store"), ("floor", "store"), ("tri", "other")]


def test_toggle_immediates_and_an_expression_toggle():
    rs = _reads("EnablePathTriangle(17, 0)\nEnablePath(2, 1)\n"
                "EnablePathTriangle({Global.Int16[3] B_EXPR_END}, 0)\nRET()")
    assert [(r.op, r.kind, r.subject, r.role, r.literals) for r in rs] == [
        (0x9A, "enable", "", "immediate", (17,)), (0xCB, "floor_enable", "", "immediate", (2,)),
        (0x9A, "enable", "", "other", ())]


def test_negative_literals_are_dropped():
    (r,) = _reads("SET({B_PTR(250) B_BGIFLOOR const(-1) B_EQ B_EXPR_END})\nRET()")
    assert r.role == "compare" and r.literals == ()


def test_literal_bytes_that_spell_a_read_are_not_reads():
    """[M10] The bytes ``5F 15 70`` (B_PTR(21) B_BGIID) inside a B_CONST4 literal and inside Walk()'s immediates
    are DATA. A raw byte scan would report two reads here; the decoded scan reports none."""
    b = _asm("SET({const4(7345503) B_EXPR_END})\nWalk(5471, 112)\nRET()")
    assert b.count(bytes([0x5F, 0x15, 0x70])) == 2               # the fixture really carries the byte pattern
    assert disasm.walkmesh_reads(b, 0, len(b)) == []


def test_instr_expr_tokens_self_verifies_against_read_code():
    b = _asm("SET({B_PTR(250) B_BGIFLOOR const(-2) B_EQ B_EXPR_END})\nRET()")
    ins = next(disasm.iter_code(b, 0, len(b)))
    assert disasm.instr_expr_tokens(b, ins) == [[(0x5F, 250), (0x71, None), (0x7D, -2), (0x20, None), (0x7F, None)]]
    shifted = disasm.Instr(ins.off, ins.op, ins.args, ins.arg_is_expr, ins.length + 1)
    with pytest.raises(ValueError, match="decode disagreement"):
        disasm.instr_expr_tokens(b, shifted)


# ============================================================================ content/object.py

def test_entry_blob_funcs_is_the_carry_bytes_parse():
    blob = pack_entry(0, [(0, b"\x04"), (1, b"\x04\x04"), (3, b"\x04\x04\x04")])
    assert _object.entry_blob_funcs(blob) == [(0, 14, 15), (1, 15, 17), (3, 17, 20)]
    assert _object.entry_blob_funcs(b"\x00") == []
    assert _object.carry_bytes(blob) == blob                                       # whole entry: byte-identical
    assert _object.carry_bytes(blob, [1]) == pack_entry(0, [(1, b"\x04\x04")])


def test_carried_object_entry_is_what_graft_objects_ships():
    warp = _asm("Field(100)\nRET()")
    director = pack_entry(0, [(0, b"\x04"), (1, warp)])
    assert _object.carried_object_entry({}, director) is None                      # #13b warp director: dropped
    assert _object.carried_object_entry({"carry_tags": [0]}, director) == pack_entry(0, [(0, b"\x04")])
    assert _object.carried_object_entry({"graft_safety": "refuse"}, pack_entry(0, [(0, b"\x04")])) is None


# ============================================================================ the lint -- a synthetic fork

# two floors STACKED over one XZ square: floor "lower" (y=0) and floor "upper" (y=-600)
_V = ["v -600 0 -200", "v 600 0 -200", "v 600 0 -1400", "v -600 0 -1400",
      "v -600 -600 -200", "v 600 -600 -200", "v 600 -600 -1400", "v -600 -600 -1400"]
_LOWER = ["f 1 2 3", "f 1 3 4"]
_UPPER = ["f 5 6 7", "f 5 7 8"]
_DONOR_OBJ = _V + ["o lower"] + _LOWER + ["o upper"] + _UPPER          # tris 0,1 = floor 0 (lower); 2,3 = floor 1
_SWAPPED_OBJ = _V + ["o upper"] + _UPPER + ["o lower"] + _LOWER        # same XZ per id -- only the LEVEL moved
_REASSIGNED_OBJ = _V + ["o lower", "f 1 2 3", "o upper", "f 1 3 4"] + _UPPER   # tri 1: same place, floor 0 -> 1
_MOVED_OBJ = [ln.replace("v 600 0 -1400", "v 650 0 -1450") for ln in _DONOR_OBJ]  # a pure vertex move

_PF_READS = ("SET({B_PTR(250) B_BGIID const(1) B_EQ B_EXPR_END})\n"
             "SET({B_PTR(250) B_BGIFLOOR const(0) B_EQ B_EXPR_END})\nRET()")

_TOML = """
[field]
id = 30999
name = "WLINT"
area = 11
{donor}
[camera]
pitch = 45

[walkmesh]
{walk}

[player]
spawn = [0, -800]
{extra}
"""
_PF_ROW = '\n[[player_func]]\nbin = "pf.bin"\ndonor_tag = 30\nsafety = "clean"\n'


def _write_obj(path: Path, lines) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _mesh(lines, tmp_path, name="m.obj"):
    p = tmp_path / name
    _write_obj(p, lines)
    v, f, fl = bgi.load_obj_floors(str(p))
    return bgi.build(v, f, floor_ids=fl)


def _fork(tmp_path, *, obj=_SWAPPED_OBJ, donor="source_field = 999", walk='obj = "walk.obj"',
          extra=_PF_ROW, sibling=True, pf=_PF_READS):
    """A synthetic fork: the donor mesh at the sibling walkmesh.bgi (what every import writes), a rebuilt
    ``[walkmesh] obj``, and donor code in a ``[[player_func]] bin`` sidecar."""
    if sibling:
        (tmp_path / "walkmesh.bgi").write_bytes(_mesh(_DONOR_OBJ, tmp_path, "donor.obj").to_bytes())
    _write_obj(tmp_path / "walk.obj", obj)
    (tmp_path / "pf.bin").write_bytes(_asm(pf))
    t = tmp_path / "wlint.field.toml"
    t.write_text(_TOML.format(donor=donor, walk=walk, extra=extra), encoding="utf-8")
    return build.FieldProject.load(t)


def _lint(project) -> list:
    return [w for w in build.verify_walkmesh(project)["warnings"] if w.startswith("fork of")]


def test_fixture_premise_the_stacked_swap_keeps_every_id_over_the_same_xz(tmp_path):
    """The swap's trap, measured: every tri id and every floor number sits over the SAME XZ in both meshes (so an
    XZ-only 'id still here' test calls it stable) -- only the level (height) says tri 1 went from y=0 to y=-600."""
    d, s = _mesh(_DONOR_OBJ, tmp_path, "d.obj"), _mesh(_SWAPPED_OBJ, tmp_path, "s.obj")
    dw, sw = d.world_verts(), s.world_verts()
    for t in range(4):
        dc = [sum(dw[v][k] for v in d.tris[t].vtx) / 3 for k in range(3)]
        sc = [sum(sw[v][k] for v in s.tris[t].vtx) / 3 for k in range(3)]
        assert (dc[0], dc[2]) == (sc[0], sc[2]) and d.tris[t].floor_ndx == s.tris[t].floor_ndx
        assert dc[1] != sc[1]


def test_stacked_swap_warns_naming_the_literals(tmp_path):
    """[M11] The rebuilt OBJ with its ``o`` blocks swapped: donor code keyed on tri 1 / floor 0 (the LOWER level)
    now fires on the upper one. An id-stable test that ignores the floor/level goes silent here."""
    ws = _lint(_fork(tmp_path))
    tri = [w for w in ws if "reads the walkmesh triangle (B_PTR(250)) and keys on [1]" in w]
    flr = [w for w in ws if "reads the walkmesh floor (B_PTR(250)) and keys on [0]" in w]
    assert len(tri) == 1 and len(flr) == 1, ws
    assert tri[0].startswith("fork of 999: [[player_func]] pf.bin ")
    assert "tri 1 is now the triangle at (-200,-1000) floor 0" in tri[0]
    assert "floor 0 is now elsewhere (2 of 2 of its donor triangles stand on floor [1])" in flr[0]
    assert 'Keep the donor mesh ([walkmesh] bgi = "walkmesh.bgi")' in tri[0]
    assert len(ws) == 2


def test_a_floor_reassignment_moves_the_tri_even_in_place(tmp_path):
    """[M11b] Tri 1 keeps its exact 3D place but joins the upper floor: B_BGIFLOOR at it now reads 1, so an id
    test that drops the floor-membership clause misses the tri literal (the floor literal is caught either way)."""
    ws = _lint(_fork(tmp_path, obj=_REASSIGNED_OBJ))
    tri = [w for w in ws if "keys on [1]" in w and "triangle" in w]
    assert len(tri) == 1 and "tri 1 is now the triangle at (-200,-1000) floor 1" in tri[0], ws
    assert any("floor 0 is now elsewhere (1 of 2" in w for w in ws), ws


@pytest.mark.parametrize("case", ["vertex_move", "bgi_is_donor", "no_donor", "unedited"])
def test_silent_cases(tmp_path, case):
    kw = {"vertex_move": dict(obj=_MOVED_OBJ),
          "bgi_is_donor": dict(walk='bgi = "walkmesh.bgi"'),
          "no_donor": dict(donor=""),
          "unedited": dict(obj=_DONOR_OBJ)}[case]
    assert _lint(_fork(tmp_path, **kw)) == []


def test_the_donor_mesh_itself_short_circuits_before_any_geometry(tmp_path, monkeypatch):
    """Early-out 4: the shipped mesh IS the donor mesh (byte-equal through the codec) -> every id holds by
    construction, so no stability geometry runs at all (exact, and free on every --verbatim/--native default)."""
    def boom(*_a, **_k):
        raise AssertionError("the stability geometry ran on the donor's own mesh")
    monkeypatch.setattr(build, "_WalkIndex", boom)
    assert _lint(_fork(tmp_path, walk='bgi = "walkmesh.bgi"')) == []
    assert _lint(_fork(tmp_path, obj=_DONOR_OBJ)) == []          # an OBJ rebuild of the same geometry: same bytes


def test_borrow_is_silent_even_on_a_moved_mesh(tmp_path):
    p = _fork(tmp_path)
    p.raw["field"]["borrow_bg"] = "fbg_n00_whatever"        # the engine runs the REAL mesh
    w: list = []
    build._lint_fork_walkmesh_ids(p, _mesh(_SWAPPED_OBJ, tmp_path, "s.obj"), w)
    assert w == []


def test_no_donor_code_no_warning(tmp_path):
    assert _lint(_fork(tmp_path, extra="")) == []                          # a moved mesh, but nothing keys on it
    assert _lint(_fork(tmp_path, pf="SET({Global.Int16[1] const(3) B_LET B_EXPR_END})\nRET()")) == []


def test_missing_donor_mesh_notes_it(tmp_path):
    a, b = tmp_path / "reads", tmp_path / "no_reads"
    a.mkdir()
    b.mkdir()
    ws = _lint(_fork(a, sibling=False))
    assert len(ws) == 1 and ws[0].startswith("fork of 999: the donor code reads walkmesh ids but no donor "
                                             "walkmesh.bgi sits next to the toml"), ws
    assert _lint(_fork(b, sibling=False, extra="")) == []                  # no reads -> nothing to verify


def test_store_reads_get_the_advisory_only_when_something_moved(tmp_path):
    store = "SET({Global.Int16[4] B_PTR(250) B_BGIFLOOR B_LET B_EXPR_END})\nRET()"
    ws = _lint(_fork(tmp_path, pf=store))
    assert ws == ["fork of 999: [[player_func]] pf.bin stores/derives the walkmesh floor -- its uses cannot be "
                  "traced; check them by hand"]
    assert _lint(_fork(tmp_path, pf=store, obj=_MOVED_OBJ)) == []


def test_walkmesh_tri_toggles_lane(tmp_path):
    ws = _lint(_fork(tmp_path, extra="", donor="source_field = 999\nwalkmesh_tri_toggles = [[1, 0], [3, 1]]"))
    assert len(ws) == 1 and ws[0].startswith("fork of 999: [field] walkmesh_tri_toggles toggles the walkmesh "
                                             "triangle and keys on [1, 3]"), ws


def test_engine_hotfix_lane_450_style(tmp_path, monkeypatch):
    """The custom engine's own C# tri literals (Dali 450's ``BGI_triSetActive(24U, 0u)``) fire on a fork through
    EffectiveFieldId, and no .eb carries them -- so the lint reads the hotfix catalog's ``fork_tris``."""
    monkeypatch.setitem(whf._HOTFIXES, 999, whf.Hotfix(999, "synthetic", "event_code", "n", "DoEventCode.cs:1",
                                                        tris=(1, 3), fork_tris=(1,)))
    ws = _lint(_fork(tmp_path, extra=""))
    assert len(ws) == 1 and ws[0].startswith("fork of 999: engine hotfix (Memoria C#, fires on forks) toggles the "
                                             "walkmesh triangle (DoEventCode.cs:1) and keys on [1];"), ws
    monkeypatch.setitem(whf._HOTFIXES, 999, whf.Hotfix(999, "raw gate", "dynamic", "n", "x", tris=(1,)))
    assert _lint(_fork(tmp_path, extra="")) == []                         # never fires on a fork -> not checked


def test_hotfix_catalog_fork_tris_follow_the_engine_gates():
    """fork_tris = the tris whose C# gate reads EffectiveFieldId (the s29/s30/s65 fork-gate patches); a gate still
    on the raw fldMapNo (FieldMap 2356, all of turnOffTriManually) never fires on a fork."""
    want = {2356: (), 2161: (69,), 2507: (174, 175, 177, 178), 450: (24,), 1753: (207, 208), 1606: (107,),
            2803: (105, 106), 900: (62,), 1421: (109, 110), 1900: (), 1455: ()}
    assert {k: h.fork_tris for k, h in whf._HOTFIXES.items()} == want
    assert all(set(h.fork_tris) <= set(h.tris) for h in whf._HOTFIXES.values())


def test_output_is_capped_at_twelve_lines(tmp_path):
    body = "\n".join(f"SET({{B_PTR({i}) B_BGIID const(1) B_EQ B_EXPR_END}})" for i in range(15)) + "\nRET()"
    ws = _lint(_fork(tmp_path, pf=body))
    assert len(ws) == 13 and ws[-1] == "fork of 999: ... and 3 more walkmesh-id warning(s)", ws


# ============================================================================ the scan set (critic #2)

_LANE_LABELS = {                                    # every registered lane -> the label its sites carry
    ("verbatim_eb", "bin"): "[verbatim_eb] v.eb.bin entry 0 tag 0",
    ("object", "bin"): "[[object]] o.bin tag 0",
    ("object", "seqs"): "[[object]] o.seq9.bin tag 0",
    ("player_func", "bin"): "[[player_func]] pf.bin",
    ("ladder", "climb"): "[[ladder]] l.climb.bin",
    ("ladder", "climb.seq"): "[[ladder]] l.seq7.bin tag 0",
    ("jump", "jump"): "[[jump]] j.bin",
    ("gateway_carry", "bin"): "[[gateway_carry]] g.bin tag 0",
    ("save_moogle", "director"): "[[save_moogle]] d.bin",
}
_ALL_LANES = """
[verbatim_eb]
bin = "v.eb.bin"

[[object]]
bin = "o.bin"
kind = "prop"
donor_idx = 5
instances = [{ arg = 0 }]
seqs = [{ entry = 9, bin = "o.seq9.bin" }]

[[player_func]]
bin = "pf.bin"
donor_tag = 30

[[player_func]]
bin = "refused.bin"
donor_tag = 31
safety = "text"

[[ladder]]
zone = [[0, -500], [100, -500], [100, -600], [0, -600]]
climb = "l.climb.bin"

[[ladder]]
navigable = true
bottom = [0, -500, 0]
top = [0, -500, -600]

[[jump]]
zone = [[0, -500], [100, -500], [100, -600], [0, -600]]
jump = "j.bin"

[[gateway_carry]]
bin = "g.bin"

[[save_moogle]]
director = "d.bin"
carried = true
"""


def _all_lanes_fork(tmp_path):
    read_src = "SET({B_PTR(250) B_BGIID const(1) B_EQ B_EXPR_END})\nRET()"
    read = _asm(read_src)
    seq = pack_entry(1, [(0, read)])                    # a type-1 helper/region entry blob
    for name, data in {"v.eb.bin": _minimal_eb(read), "o.bin": pack_entry(0, [(0, read)]), "o.seq9.bin": seq,
                       "refused.bin": read, "l.climb.bin": _asm("RunSharedScript(7)\n" + read_src),
                       "l.seq7.bin": seq, "j.bin": read, "g.bin": seq, "d.bin": read}.items():
        (tmp_path / name).write_bytes(data)
    return _fork(tmp_path, extra=_ALL_LANES)


def test_every_registered_lane_is_scanned(tmp_path):
    """The lint's scan set covers EVERY lane in build.DONOR_CODE_LANES (and this table must name each one, so a
    new lane cannot be registered without a scan test). Only what ships is scanned: the refused "text" player func
    (no text carry) and the navigable ladder (no climb bytes) contribute nothing."""
    assert set(_LANE_LABELS) == {(ln.block, ln.key) for ln in build.DONOR_CODE_LANES}
    p = _all_lanes_fork(tmp_path)
    labels = [s[0] for s in build._donor_code_sites(p)]
    assert sorted(labels) == sorted(_LANE_LABELS.values()), labels
    ws = _lint(p)
    for lbl in _LANE_LABELS.values():
        assert any(w.startswith(f"fork of 999: {lbl} reads the walkmesh triangle") and "keys on [1]" in w
                   for w in ws), (lbl, ws)


def test_only_the_bytes_that_ship_are_scanned(tmp_path):
    """An object's dropped funcs (outside ``carry_tags``), a warp-director object graft_objects skips (#13b), and
    ladder rows the build never reads a climb for (navigable / top+bottom) are not donor code on this fork."""
    read = _asm("SET({B_PTR(250) B_BGIID const(1) B_EQ B_EXPR_END})\nRET()")
    (tmp_path / "keep.bin").write_bytes(pack_entry(0, [(0, b"\x04"), (3, read)]))
    (tmp_path / "warp.bin").write_bytes(pack_entry(0, [(0, read), (1, _asm("Field(100)\nRET()"))]))
    (tmp_path / "stale.climb.bin").write_bytes(read)
    (tmp_path / "warp.seq9.bin").write_bytes(pack_entry(0, [(0, read)]))    # ships only WITH its object
    extra = ('\n[[object]]\nbin = "keep.bin"\nkind = "prop"\ndonor_idx = 4\ncarry_tags = [0]\n'
             '\n[[object]]\nbin = "warp.bin"\nkind = "npc"\ndonor_idx = 6\n'
             'seqs = [{ entry = 9, bin = "warp.seq9.bin" }]\n'
             '\n[[ladder]]\nnavigable = true\nbottom = [0, -500, 0]\ntop = [0, -500, -600]\nclimb = "stale.climb.bin"\n'
             '\n[[ladder]]\ntop = [0, -500, -600]\nbottom = [0, -900, 0]\nclimb = "stale.climb.bin"\n')
    p = _fork(tmp_path, extra=extra)
    assert [s[0] for s in build._donor_code_sites(p)] == ["[[object]] keep.bin tag 0"]
    assert _lint(p) == []


def test_an_unregistered_lane_is_refused_at_the_reader(tmp_path):
    p = _fork(tmp_path)
    with pytest.raises(KeyError, match="not in DONOR_CODE_LANES"):
        build._read_donor_code(p, "newlane", "bin", "pf.bin")
    assert build._read_donor_code(p, "player_func", "bin", "pf.bin") == (tmp_path / "pf.bin").read_bytes()


def test_a_registered_lane_without_a_scan_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "DONOR_CODE_LANES", build.DONOR_CODE_LANES + (build._DonorLane("x", "bin", "body"),))
    with pytest.raises(KeyError, match="has no scan in _donor_code_sites"):
        build._donor_code_sites(_fork(tmp_path))


# every `.read_bytes()` in build.py outside _read_donor_code, by enclosing function, and why it is not a carry
_NON_CARRY_READERS = {
    "_validate_sps_edits": "SPS effect bins (dry-run validation)",
    "validate": "sidecar validation only (object non-empty, seq-helper safety, player-call tags)",
    "lint_logic": "window-txid scan for the text lints",
    "_borrow_walkmesh": "the donor walkmesh (validation only)",
    "resolve_walkmesh": "a shipped [walkmesh] bgi",
    "gauge_layout": "the native .bgs header",
    "behavior_walkmesh": "the routing walkmesh",
    "behavior_floor_table": "a shipped [walkmesh] bgi's floor count (the [behavior] floor sensor)",
    "verify_walkmesh": "a shipped [walkmesh] bgi the build refuses (verify still reports its table)",
    "build_field": "SPS effect bins ([[sps_edit]])",
    "build_mod": "the BUILT .eb read back from the output layout",
}


def test_no_donor_code_is_read_around_the_registry():
    """The drift tripwire: the build carries donor bytecode only through _read_donor_code. A new
    ``project.path(row["bin"]).read_bytes()`` in any other build.py function fails here -- route it through
    _read_donor_code + DONOR_CODE_LANES (so the fork walkmesh-literal lint scans it), or, if it is NOT carried
    bytecode, add its function to _NON_CARRY_READERS with the reason."""
    tree = ast.parse(Path(build.__file__).read_text(encoding="utf-8"))
    found = set()

    def walk(node, fn):
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(ch, fn or ch.name)
                continue
            if isinstance(ch, ast.Call) and isinstance(ch.func, ast.Attribute) and ch.func.attr == "read_bytes":
                found.add(fn)
            walk(ch, fn)

    walk(tree, None)
    assert found - {"_read_donor_code"} <= set(_NON_CARRY_READERS), found - set(_NON_CARRY_READERS)
    assert "_read_donor_code" in found


def test_the_lint_is_wired_after_every_geometry_validation():
    src = Path(build.__file__).read_text(encoding="utf-8")
    geo = re.findall(r"^\s*_validate_walkmesh_geometry\(project, wmesh, warnings\)\s*\n\s*(\S+)", src, re.M)
    assert len(geo) == 3 and all(n.startswith("_lint_fork_walkmesh_ids(") for n in geo), geo


# ============================================================================ install-gated: a real donor

def _game_ready():
    try:
        import UnityPy  # noqa: F401,PLC0415
        from ff9mapkit import config  # noqa: PLC0415
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:                                               # noqa: BLE001
        return False


_PLANK_LITERALS = {203, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 218, 219, 220, 221, 222, 226, 227,
                   250, 251}


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_field116_plank_loop_literals(tmp_path):
    """Stock field 116 (Alexandria rooftop) loops while ``GetWalkpathTriangle(21)`` is one of its plank tris --
    the only stock B_BGIID compares. ``import --verbatim`` ships the donor mesh (silent); switching to the editable
    OBJ round trip keeps every id (silent); deleting ONE face below id 203 renumbers every plank tri (warns,
    listing the plank literals)."""
    from ff9mapkit import extract
    _meta, toml = extract.write_native_project("116", tmp_path, name="PLANK", verbatim=True)
    assert _lint(build.FieldProject.load(toml)) == []                      # [walkmesh] bgi = the donor
    wm = bgi.BgiWalkmesh.from_bytes((tmp_path / "walkmesh.bgi").read_bytes())
    obj = extract._world_walkmesh_obj_text(wm).splitlines()
    (tmp_path / "walkmesh.obj").write_text("\n".join(obj) + "\n", encoding="utf-8")
    body = toml.read_text(encoding="utf-8")
    assert 'bgi = "walkmesh.bgi"' in body
    toml.write_text(body.replace('bgi = "walkmesh.bgi"', 'obj = "walkmesh.obj"'), encoding="utf-8")
    assert _lint(build.FieldProject.load(toml)) == []                      # the round trip preserves every id
    faces = [i for i, ln in enumerate(obj) if ln.startswith("f ")]
    del obj[faces[100]]                                                     # face 100 < 203
    (tmp_path / "walkmesh.obj").write_text("\n".join(obj) + "\n", encoding="utf-8")
    ws = _lint(build.FieldProject.load(toml))
    plank = [w for w in ws if "reads the walkmesh triangle (B_PTR(21))" in w]
    keyed = {int(x) for w in plank for x in re.search(r"keys on \[([^\]]*)\]", w).group(1).split(",")}
    assert keyed == _PLANK_LITERALS, (keyed, ws)
    # ...and every one of them is judged MOVED, one by one (the 'keys on' set lists a group's literals whenever
    # any ONE moved, so it alone could not tell a lint that flagged a single plank from one that flagged all 20)
    judged = {int(t) for w in plank for t in re.findall(r"tri (\d+) (?:is now|no longer)", w)}
    assert judged == _PLANK_LITERALS, (sorted(_PLANK_LITERALS - judged), plank)
    assert all(w.startswith("fork of 116: [verbatim_eb] PLANK.verbatim_eb.bin entry ") for w in plank)


# ------------------------------------------------------------------ the review round: every stability branch
_DROPPED_UPPER_OBJ = _V + ["o lower"] + _LOWER                 # the upper floor (tris 2,3 = floor 1) is gone
_FAR_OBJ = [(f"v {int(ln.split()[1]) + 5000} {ln.split()[2]} {ln.split()[3]}" if ln.startswith("v ") else ln)
            for ln in _DONOR_OBJ]                              # both floors moved 5000u east: off the donor XZ


def test_a_tri_or_floor_that_no_longer_exists_warns(tmp_path):
    pf = ("SET({B_PTR(250) B_BGIID const(3) B_EQ B_EXPR_END})\n"
          "SET({B_PTR(250) B_BGIFLOOR const(1) B_EQ B_EXPR_END})\nRET()")
    ws = _lint(_fork(tmp_path, obj=_DROPPED_UPPER_OBJ, pf=pf))
    assert any("tri 3 no longer exists" in w for w in ws), ws
    assert any("floor 1 no longer exists" in w for w in ws), ws


def test_a_floor_whose_whole_donor_area_left_the_mesh_warns(tmp_path):
    """Floor 0 still EXISTS in the rebuilt mesh, but none of its donor triangles' centroids land on it (or on
    anything): moved == 0 is not enough -- the floor must still cover some of its donor area."""
    pf = "SET({B_PTR(250) B_BGIFLOOR const(0) B_EQ B_EXPR_END})\nRET()"
    ws = _lint(_fork(tmp_path, obj=_FAR_OBJ, pf=pf))
    assert any("floor 0 no longer covers any of its donor area" in w for w in ws), ws
