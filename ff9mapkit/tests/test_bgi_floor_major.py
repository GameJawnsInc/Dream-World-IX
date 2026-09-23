"""THE FLOOR-MAJOR TRIANGLE LAW (walkmesh-sensor rung 1; studies/walkmesh-sensor/PLAN.md).

The engine builds its walkmesh triangle list floor by floor (WalkMesh.cs:46-65) but indexes it by
triangle ID (:573, :618, :1050, and the edge hysteresis in FieldMapActorController.cs:1376-1417). So
floor 0 must list triangles 0..k, floor 1 the next run, and every triangle's ``floor_ndx`` must equal the
floor that lists it. Every stock ``.bgi`` obeys it (674/674, the install-gated census below).

Before this law the kit could break it silently: an OBJ that REOPENS a floor (``o A / o B / o A``) kept
face order, so floor A listed ``[0..3, 12..15]``. Four layers now guard it, each pinned here:
  (a) ``bgi.build`` regroups floor by floor (a stable sort -- the identity on floor-contiguous input);
  (b) ``bgi.build`` checks its own output with ``floor_order_problems``;
  (c) ``resolve_walkmesh`` refuses a shipped ``[walkmesh] bgi`` that is not floor-major;
  (d) ``walkmesh verify`` prints the floor table and ``floor-major: yes|NO``.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ff9mapkit import build as B
from ff9mapkit.scene import bgi

BENCH = Path(__file__).resolve().parents[2] / "studies" / "walkmesh-sensor" / "bench"
BGI0_TOML = BENCH / "bgi0.field.toml"
BGI0_OBJ = BENCH / "bgi0.walkmesh.obj"
# resolve_walkmesh(bgi0.field.toml) on the BASE commit (1b9d5536), BEFORE the regroup existed -- the
# mesh rung 0 proved in-game 43/43. The regroup must leave it byte-identical.
BGI0_SHA256 = "681c0a00639883af97063e96cb89acfa7965805b0aebe4f8060e26e7e8dd1ea8"

_BGI0_VERTS = BGI0_OBJ.read_text(encoding="utf-8").split("o floorA")[0]   # the header comment + 18 `v` lines
_GROUND = ["f 1 2 3 4", "f 2 5 6 3", "f 4 3 7 8", "f 3 6 9 7"]            # bgi0 floor 0 (8 tris)
_TERRACE = ["f 10 11 12 13", "f 11 14 15 12", "f 13 12 16 17", "f 12 15 18 16"]   # bgi0 floor 1 (8 tris)
# the SAME 16 triangles with floor 0 REOPENED: ground's first two quads, the terrace, ground's last two
_REOPENED = "\n".join(["o ground", *_GROUND[:2], "o terrace", *_TERRACE, "o ground", *_GROUND[2:]]) + "\n"


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def _reopened_obj(tmp_path):
    return _write(tmp_path, "wm.obj", _BGI0_VERTS + _REOPENED)


def _project(tmp_path, walkmesh_block):
    toml = _write(tmp_path, "f.field.toml",
                  '[field]\nid = 30999\nname = "FM"\narea = 11\n\n' + walkmesh_block)
    return B.FieldProject.load(toml)


def _floor_lists(m):
    return [list(fl.tri_ndx_list) for fl in m.floors]


# ------------------------------------------------------------------ (a) the regroup
def test_a_reopened_floor_is_regrouped_floor_by_floor(tmp_path):
    """`o ground / o terrace / o ground` -> ground = tris 0..7, terrace = 8..15: first-appearance floor
    indices unchanged (ground 0, terrace 1), floor_ndx == membership, and source_face records the move.
    [M1: drop the sort -> the lists interleave and the build's own check raises]"""
    p = _reopened_obj(tmp_path)
    v, f, fid = bgi.load_obj_floors(str(p))
    assert fid == [0] * 4 + [1] * 8 + [0] * 4                      # the input really is interleaved
    m = bgi.build(v, f, floor_ids=fid)
    assert _floor_lists(m) == [list(range(8)), list(range(8, 16))]
    assert all(m.tris[t].floor_ndx == fi for fi, fl in enumerate(m.floors) for t in fl.tri_ndx_list)
    assert m.source_face == [0, 1, 2, 3, 12, 13, 14, 15, 4, 5, 6, 7, 8, 9, 10, 11]
    assert m.regrouped is True
    assert [tuple(m.tris[t].vtx) for t in range(16)] == [f[s] for s in m.source_face]
    assert bgi.obj_floor_names(str(p)) == ["ground", "terrace"]
    assert bgi.floor_order_problems(m) == []


def test_a_regrouped_mesh_is_byte_identical_to_the_proven_bgi0(tmp_path):
    """The regroup is proven against known-good bytes OFFLINE: the reopened OBJ, regrouped, builds the
    exact .bgi of the floor-contiguous bgi0 OBJ (the mesh rung 0 read back in-game 43/43) -- the only
    difference between them is face ORDER, which the regroup removes."""
    rv, rf, rfid = bgi.load_obj_floors(str(_reopened_obj(tmp_path)))
    v, f, fid = bgi.load_obj_floors(str(BGI0_OBJ))
    assert rv == v and sorted(rf) == sorted(f) and rf != f               # same geometry, other face order
    assert bgi.build(rv, rf, floor_ids=rfid).to_bytes() == bgi.build(v, f, floor_ids=fid).to_bytes()


def test_a_floor_contiguous_input_is_the_identity(tmp_path):
    """Byte identity: every floor-contiguous mesh (a quad, a flat list, the bgi0 bench) is NOT regrouped
    and its source_face is the identity -- so no existing mesh changes."""
    q = bgi.quad([(-500, -500), (500, -500), (500, 500), (-500, 500)])
    assert q.regrouped is False and q.source_face == [0, 1]
    v, f, fid = bgi.load_obj_floors(str(BGI0_OBJ))
    m = bgi.build(v, f, floor_ids=fid)
    assert m.regrouped is False and m.source_face == list(range(16))
    flat = bgi.build(v, f)                                           # floor_ids=None: one floor
    assert flat.regrouped is False and flat.source_face == list(range(16))
    # floor ids need not start at 0 or ascend: first appearance numbers them, contiguity is what counts
    two = bgi.build(v, f, floor_ids=[9] * 8 + [5] * 8)
    assert two.regrouped is False and _floor_lists(two) == [list(range(8)), list(range(8, 16))]


def test_a_bgi0_bench_bytes_are_pinned():
    """The bench's shipped .bgi (obj + links through resolve_walkmesh) is byte-identical to the BASE
    commit's -- the regroup and the new checks moved nothing."""
    proj = B.FieldProject.load(BGI0_TOML)
    warns: list = []
    data = B.resolve_walkmesh(proj, None, warns)
    assert hashlib.sha256(data).hexdigest() == BGI0_SHA256
    assert warns == []                                               # contiguous: no regroup note


# ------------------------------------------------------------------ (b) build checks its own output
def test_b_build_refuses_its_own_non_floor_major_output(monkeypatch):
    """A law in a docstring is a wish: build() runs floor_order_problems on what it made and raises an
    `internal:` ValueError (never a bare assert, which -O strips). [M: delete the check -> green build]"""
    monkeypatch.setattr(bgi, "floor_order_problems", lambda m: ["floor 0 lists triangle 1 at list position 0"])
    with pytest.raises(ValueError, match=r"^internal: bgi\.build produced a non-floor-major mesh: floor 0"):
        bgi.quad([(-500, -500), (500, -500), (500, 500), (-500, 500)])


# ------------------------------------------------------------------ floor_order_problems itself
def _bgi0_mesh():
    v, f, fid = bgi.load_obj_floors(str(BGI0_OBJ))
    return bgi.BgiWalkmesh.from_bytes(bgi.build(v, f, floor_ids=fid).to_bytes())


def _corrupt(edit):
    """A codec-level corrupted bgi0: edit the parsed mesh, then round-trip it through the bytes, so the
    check sees exactly what a shipped file would carry."""
    m = _bgi0_mesh()
    edit(m)
    return bgi.BgiWalkmesh.from_bytes(m.to_bytes())


def test_floor_order_problems_clean_on_the_bench():
    assert bgi.floor_order_problems(_bgi0_mesh()) == []


def test_floor_order_problems_names_a_non_contiguous_list():
    def swap(m):                                                     # floor 0 lists tri 8, floor 1 lists tri 7
        m.floors[0].tri_ndx_list[7], m.floors[1].tri_ndx_list[0] = 8, 7
    probs = bgi.floor_order_problems(_corrupt(swap))
    assert probs[0] == "floor 0 lists triangle 8 at list position 7 (floor-major needs triangle 7 there)"
    assert "triangle 8 is listed on floor 0 but its floor_ndx is 1" in probs
    assert "triangle 7 is listed on floor 1 but its floor_ndx is 0" in probs


def test_floor_order_problems_names_an_in_floor_reorder():
    def rev(m):
        m.floors[0].tri_ndx_list[:2] = [1, 0]
    assert bgi.floor_order_problems(_corrupt(rev)) == [
        "floor 0 lists triangle 1 at list position 0 (floor-major needs triangle 0 there)"]


def test_floor_order_problems_names_a_floor_ndx_mismatch():
    def relabel(m):
        m.tris[3].floor_ndx = 1
    assert bgi.floor_order_problems(_corrupt(relabel)) == [
        "triangle 3 is listed on floor 0 but its floor_ndx is 1"]


def test_floor_order_problems_names_duplicated_missing_and_out_of_range_tris():
    def dup(m):
        m.floors[1].tri_ndx_list.append(3)
    probs = bgi.floor_order_problems(_corrupt(dup))
    assert probs[0] == "triangle(s) [3] listed more than once"
    assert "triangle 3 is listed on floor 1 but its floor_ndx is 0" in probs

    def drop(m):
        m.floors[1].tri_ndx_list.pop()
    assert bgi.floor_order_problems(_corrupt(drop)) == ["triangle(s) [15] on no floor's list"]

    def oob(m):
        m.floors[1].tri_ndx_list.append(99)
    assert bgi.floor_order_problems(_corrupt(oob)) == ["floor 1 lists triangle 99, out of range 0..15"]


# ------------------------------------------------------------------ (c) resolve_walkmesh
def test_c_resolve_walkmesh_refuses_a_shipped_non_floor_major_bgi(tmp_path):
    """A shipped [walkmesh] bgi is checked, never repaired: a floor-major file ships byte-unchanged, a
    non-floor-major one is a BuildError naming the first problem. [M: drop the check -> it ships]"""
    good = _bgi0_mesh().to_bytes()
    (tmp_path / "wm.bgi").write_bytes(good)
    proj = _project(tmp_path, '[walkmesh]\nbgi = "wm.bgi"\n')
    assert B.resolve_walkmesh(proj, None) == good

    def swap(m):
        m.floors[0].tri_ndx_list[7], m.floors[1].tri_ndx_list[0] = 8, 7
    (tmp_path / "wm.bgi").write_bytes(_corrupt(swap).to_bytes())
    with pytest.raises(B.BuildError) as ei:
        B.resolve_walkmesh(proj, None)
    msg = str(ei.value)
    assert msg.startswith("[walkmesh] bgi wm.bgi: triangles are not listed floor by floor (floor 0 lists "
                          "triangle 8 at list position 7")
    assert "674/674" in msg and "[walkmesh] obj" in msg


def test_c_resolve_walkmesh_warns_naming_the_reopened_floor(tmp_path):
    """The obj branch regroups and SAYS so: the note names the reopened floor ('ground', not 'terrace')
    and how many triangle ids moved -- a hand-written tri id is now a different triangle."""
    _reopened_obj(tmp_path)
    proj = _project(tmp_path, '[walkmesh]\nobj = "wm.obj"\n')
    warns: list = []
    data = B.resolve_walkmesh(proj, None, warns)
    assert len(warns) == 1
    w = warns[0]
    assert w.startswith("walkmesh: wm.obj reopens floor(s) 'ground' (floor 0) (their faces are not contiguous)")
    assert "terrace" not in w and "(12 of 16 moved)" in w and "walkmesh_tri_toggles" in w
    m = bgi.BgiWalkmesh.from_bytes(data)
    assert _floor_lists(m) == [list(range(8)), list(range(8, 16))]
    assert B.resolve_walkmesh(proj, None) == data                    # warnings=None: same bytes, no note


def test_c_links_active_tri_follows_its_face_through_the_regroup(tmp_path):
    """A links sidecar's `[header] active_tri` names an OBJ FACE (the export writes one face per donor
    triangle); after a regroup it must still name that face's triangle. Input face 12 (ground's third
    quad) becomes built triangle 4. [M: drop the remap -> activeTri 12 = a terrace triangle]"""
    _reopened_obj(tmp_path)
    _write(tmp_path, "wm.links.toml", "[header]\nactive_floor = 0\nactive_tri = 12\n")
    proj = _project(tmp_path, '[walkmesh]\nobj = "wm.obj"\nlinks = "wm.links.toml"\n')
    m = bgi.BgiWalkmesh.from_bytes(B.resolve_walkmesh(proj, None, []))
    assert m.activeTri == 4 and m.tris[4].floor_ndx == 0


# ------------------------------------------------------------------ (d) walkmesh verify
def test_d_walkmesh_stats_floor_table():
    """verify's floor table: (floor, name, first tri, last tri, count) + floor_major, names from the obj."""
    rep = B.verify_walkmesh(B.FieldProject.load(BGI0_TOML))
    assert rep["floor_table"] == [(0, "floorA", 0, 7, 8), (1, "floorB", 8, 15, 8)]
    assert rep["floor_major"] is True
    q = B._walkmesh_stats(bgi.quad([(-500, -500), (500, -500), (500, 500), (-500, 500)]))
    assert q["floor_table"] == [(0, None, 0, 1, 2)] and q["floor_major"] is True


def test_d_cli_verify_prints_the_floor_table(capsys, tmp_path):
    from ff9mapkit.cli import _walkmesh_verify
    assert _walkmesh_verify(str(BGI0_TOML)) == 0
    out = capsys.readouterr().out
    assert "  floors: 0 'floorA' tris 0-7 | 1 'floorB' tris 8-15   floor-major: yes\n" in out

    def swap(m):
        m.floors[0].tri_ndx_list[7], m.floors[1].tri_ndx_list[0] = 8, 7
    raw = tmp_path / "bad.bgi"
    raw.write_bytes(_corrupt(swap).to_bytes())
    assert _walkmesh_verify(str(raw)) == 1                             # a raw .bgi: warns, exit 1
    out = capsys.readouterr().out
    assert "floor-major: NO" in out and "NOT contiguous" in out
    assert "! not floor-major: floor 0 lists triangle 8 at list position 7" in out


def test_d_cli_obj_conversion_says_when_it_regrouped(capsys, tmp_path):
    """`walkmesh obj` (the standalone converter) regroups too -- and says so; a contiguous obj is quiet."""
    import argparse

    from ff9mapkit.cli import _cmd_walkmesh
    out = tmp_path / "o.bgi"
    _cmd_walkmesh(argparse.Namespace(action="obj", input=str(_reopened_obj(tmp_path)), output=str(out)))
    said = capsys.readouterr().out
    assert "note: the obj reopens a floor" in said and "12 of 16 triangle ids moved" in said
    assert bgi.floor_order_problems(bgi.BgiWalkmesh.from_file(out)) == []
    _cmd_walkmesh(argparse.Namespace(action="obj", input=str(BGI0_OBJ), output=str(out)))
    assert "note:" not in capsys.readouterr().out


# ------------------------------------------------------------------ floor NAMES
@pytest.mark.parametrize("text, names, fids", [
    # an `o` with no faces takes no index
    ("o empty\no A\nf 1 2 3\no B\nf 1 3 4\n", ["A", "B"], [1, 2]),
    # faces before the first `o` join the FIRST-DECLARED object's floor
    ("f 1 2 3\no A\nf 1 3 4\no B\nf 2 3 4\n", ["A", "B"], [0, 0, 1]),
    # a reopened name rejoins its floor (built floors follow first appearance among FACES)
    ("o B\nf 1 2 3\no A\nf 1 3 4\no B\nf 2 3 4\n", ["B", "A"], [0, 1, 0]),
    # ... among FACES, not among declarations: A is declared first but B has the first face
    ("o A\no B\nf 1 2 3\no A\nf 1 3 4\n", ["B", "A"], [1, 0]),
    # `g` is a synonym for `o`
    ("g A\nf 1 2 3\ng B\nf 1 3 4\n", ["A", "B"], [0, 1]),
    # no objects at all: one unnamed floor
    ("f 1 2 3\nf 1 3 4\n", [None], [0, 0]),
    # a bare `o` names nothing
    ("o\nf 1 2 3\no A\nf 1 3 4\n", [None, "A"], [0, 1]),
])
def test_obj_floor_names(tmp_path, text, names, fids):
    p = _write(tmp_path, "n.obj", "v 0 0 0\nv 100 0 0\nv 100 0 100\nv 0 0 100\n" + text)
    assert bgi.obj_floor_names(str(p)) == names
    v, f, fid = bgi.load_obj_floors(str(p))                          # load_obj_floors keeps its shape
    assert fid == fids
    assert len(bgi.build(v, f, floor_ids=fid).floors) == len(names)  # one name per BUILT floor


@pytest.mark.parametrize("line", ["o upper deck", "g upper\tdeck", "g ground terrace"])
def test_a_floor_name_with_whitespace_is_refused(tmp_path, line):
    """`o upper deck` used to become floor 'upper' and silently merge with `o upper ledge`; a `g` with
    several words is OBJ's multi-group form. Both are refused, naming the line and a fix."""
    p = _write(tmp_path, "w.obj", f"v 0 0 0\nv 100 0 0\nv 100 0 100\n{line}\nf 1 2 3\n")
    with pytest.raises(ValueError, match=r"line 4: [og] name .* contains whitespace .* Rename it, e\.g\. "):
        bgi.load_obj_floors(str(p))
    with pytest.raises(ValueError, match="contains whitespace"):
        bgi.obj_floor_names(str(p))


# ------------------------------------------------------------------ tris_at
def test_tris_at_returns_every_containing_triangle():
    """Ascending ids, edges inclusive: a centroid is one triangle, a shared diagonal two, and the x = 0
    seam (each floor has its OWN vertices there) one per floor."""
    m = _bgi0_mesh()
    assert m.tris_at(-407, -472) == [3]                              # tri 3's centroid (floor 0)
    assert m.tris_at(407, -1202) == [12]                             # tri 12's centroid (floor 1)
    assert m.tris_at(-915, -290) == [0, 1]                           # on quad 1's diagonal
    two = m.tris_at(0, -290)                                         # on the seam: one tri per floor
    assert len(two) == 2 and sorted(m.tris[t].floor_ndx for t in two) == [0, 1]
    assert m.tris_at(5000, 5000) == []                               # off-mesh


# ------------------------------------------------------------------ INSTALL-GATED: the stock census
def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_every_stock_bgi_is_floor_major_and_the_obj_round_trip_keeps_every_id(tmp_path):
    """The law's premise, measured: every stock .bgi is floor-major (so `[walkmesh] bgi` refuses none of
    them), and the editable fork's OBJ re-export rebuilds with every triangle id, vertex and floor in
    place and NO regroup -- the regroup is the identity on everything the importer writes."""
    import collections

    from ff9mapkit import extract
    by_bundle = collections.defaultdict(list)
    for folder, bn in extract.build_field_index(verbose=False).items():
        by_bundle[bn].append(folder)
    sa = extract._streaming_assets(None)
    n, bad, moved = 0, [], []
    obj = tmp_path / "w.obj"
    for bn, folders in sorted(by_bundle.items()):
        env = extract._load_env(sa / bn)
        wanted = {f"fieldmaps/{f}/": f for f in folders}
        for k in env.container:
            kl = k.lower()
            if not kl.endswith(".bgi.bytes"):
                continue
            folder = next((f for pre, f in wanted.items() if pre in kl), None)
            if folder is None:
                continue
            m = bgi.BgiWalkmesh.from_bytes(extract._raw_bytes(env.container[k].read()))
            n += 1
            if bgi.floor_order_problems(m):
                bad.append((folder, bgi.floor_order_problems(m)[0]))
            obj.write_text(extract._world_walkmesh_obj_text(m), encoding="utf-8", newline="\n")
            v, f, fid = bgi.load_obj_floors(str(obj))
            r = bgi.build(v, f, floor_ids=fid)
            if (r.regrouped or [t.vtx for t in r.tris] != [t.vtx for t in m.tris]
                    or [t.floor_ndx for t in r.tris] != [t.floor_ndx for t in m.tris]):
                moved.append(folder)
    assert n >= 674, n
    assert bad == []
    assert moved == []
