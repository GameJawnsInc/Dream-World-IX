"""An editable fork's cross-floor seams follow their floors through a reshape that renumbers them.

``import --editable`` writes a multi-floor walkmesh as ``walkmesh.obj`` (one ``o floor_<donor index>`` block
per floor) plus the ``walkmesh.links.toml`` sidecar: the cross-floor seams geometry can't carry, keyed by the
DONOR's floor numbers. ``bgi.build`` numbers floors in first-seen face order, so an edit that deletes or
reorders a block renumbers the floors after it -- and a seam looked up by its donor number on the rebuilt mesh
misses, stranding floors (studies/actor-shadow rung 1: a 1607 fork written in floor order 3,1,2,0,... dropped
2 of 14 seams and stranded floors [1,3,4]). The build now re-keys the seams through the floor NAMES, the same
map (``build._donor_floor_map``) that re-keys the MapConfigData lights (tests/test_fork_mapconfig.py).

THE INVARIANT pinned here: every seam whose two floors are still in the .obj links, whatever order they are
written in; a seam whose floor is gone (deleted, renamed) counts as missing, and the warning names that floor.
The unedited round-trip is untouched, byte for byte. All bytes here are authored except the gitignored
multi-floor fixture ``ff9mapkit extract-templates`` regenerates.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit import build, extract
from ff9mapkit.scene import bgi

FIX = Path(__file__).parent / "fixtures"


def _seam(fa, a, fb, b):
    return (fa, tuple(sorted(a)), fb, tuple(sorted(b)))


# floors 0-3: a 2x2 grid at y 0 joined by coincident seams; floor 4: a ledge at y 400 bridged to floor 1
_FLOORS = [(0, 0, 0), (100, 0, 0), (0, 0, 100), (100, 0, 100), (200, 400, 0)]
_SEAMS = [_seam(0, ((100, 0, 0), (100, 0, 100)), 1, ((100, 0, 0), (100, 0, 100))),
          _seam(0, ((0, 0, 100), (100, 0, 100)), 2, ((0, 0, 100), (100, 0, 100))),
          _seam(1, ((100, 0, 100), (200, 0, 100)), 3, ((100, 0, 100), (200, 0, 100))),
          _seam(2, ((100, 0, 100), (100, 0, 200)), 3, ((100, 0, 100), (100, 0, 200))),
          _seam(1, ((200, 0, 0), (200, 0, 100)), 4, ((200, 400, 0), (200, 400, 100)))]


def _donor() -> bgi.BgiWalkmesh:
    """An authored 5-floor walkmesh in the multi-floor .bgi convention: one quad per floor on its own
    (disjoint) vertex set, the cross-floor links only its seams make."""
    verts, faces, fids = [], [], []
    for f, (x, y, z) in enumerate(_FLOORS):
        v = len(verts)
        verts += [(x, y, z), (x + 100, y, z), (x + 100, y, z + 100), (x, y, z + 100)]
        faces += [(v, v + 1, v + 2), (v, v + 2, v + 3)]
        fids += [f, f]
    wm = bgi.build(verts, faces, floor_ids=fids)
    assert wm.apply_seams(_SEAMS)[:2] == (len(_SEAMS), 0)
    assert wm.reachable_floors() == wm.all_floors()
    return bgi.BgiWalkmesh.from_bytes(wm.to_bytes())


def _reshape(obj_text: str, order, rename=None) -> str:
    """The author's edit on the re-exported .obj: its ``o floor_N`` blocks kept in ``order`` (donor numbers;
    one left out is deleted), some optionally renamed. The vertex list is untouched."""
    head, blocks, cur = [], {}, None
    for line in obj_text.splitlines():
        if line.startswith("o floor_"):
            cur = int(line[len("o floor_"):])
            blocks[cur] = [line]
        elif cur is None:
            head.append(line)
        else:
            blocks[cur].append(line)
    rename = rename or {}
    out = list(head)
    for d in order:
        out += [f"o {rename[d]}"] + blocks[d][1:] if d in rename else blocks[d]
    return "\n".join(out) + "\n"


def _fork(tmp_path, donor, obj_text=None):
    """What ``import --editable`` writes for a multi-floor donor -- the world-frame .obj and the links
    sidecar -- with the .obj optionally replaced by an edit of it."""
    (tmp_path / "walkmesh.obj").write_text(obj_text or extract._world_walkmesh_obj_text(donor), encoding="utf-8")
    extract._write_links_toml(donor, tmp_path / "walkmesh.links.toml")
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=30990\nname="EDM"\narea=21\ntext_block=30990\n'
                 '[camera]\npitch=30\ndistance=900\nfov=40\n'
                 '[walkmesh]\nobj = "walkmesh.obj"\nlinks = "walkmesh.links.toml"\n', encoding="utf-8")
    return build.FieldProject.load(p)


def _resolve(proj, warnings):
    return build.resolve_walkmesh(proj, build.resolve_camera(proj), warnings)


def _prefix_reconcile(tmp_path):
    """The reconcile as it was before seams were re-keyed -- the rebuilt mesh, the sidecar's seams looked
    up by their DONOR floor numbers as-is, its header restored -- and how many seams it missed."""
    v, f, fid = bgi.load_obj_floors(str(tmp_path / "walkmesh.obj"))
    mesh = bgi.build(v, f, floor_ids=fid)
    seams, header = build._read_links(tmp_path / "walkmesh.links.toml")
    _linked, missing, _ = mesh.apply_seams(seams)
    mesh.activeFloor, mesh.activeTri = int(header["active_floor"]), int(header["active_tri"])
    mesh.charPos = bgi.Vec3(*(int(c) for c in header["char_pos"]))
    return mesh, missing


def _seam_links(wm, to_donor):
    """The cross-floor links as unordered pairs of (DONOR floor, edge) halves -- renumber-proof."""
    return {frozenset({(to_donor[fa], a), (to_donor[fb], b)}) for (fa, a, fb, b) in wm.extract_seams()}


def _seam_warnings(warnings):
    return [w for w in warnings if "seam" in w]


# ---- the unedited round-trip: untouched ------------------------------------------------------------------

def test_the_unedited_round_trip_is_byte_identical(tmp_path):
    donor = _donor()
    proj = _fork(tmp_path, donor)
    assert build._donor_floor_map(tmp_path / "walkmesh.obj") is None     # no renumbering: no re-keying
    w = []
    out = _resolve(proj, w)
    assert out == donor.to_bytes()                                       # the donor, byte for byte
    pre, missing = _prefix_reconcile(tmp_path)
    assert out == pre.to_bytes() and missing == 0                        # = the pre-re-keying reconcile
    assert _seam_warnings(w) == []


@pytest.mark.skipif(not (FIX / "multifloor.bgi.bytes").is_file(),
                    reason="gitignored fixture: run `ff9mapkit extract-templates`")
def test_a_real_multifloor_walkmesh_unedited_is_the_prefix_reconcile(tmp_path):
    # GRGR's 7 floors: the unedited re-export resolves to exactly what the pre-re-keying reconcile built
    donor = bgi.BgiWalkmesh.from_bytes((FIX / "multifloor.bgi.bytes").read_bytes())
    proj = _fork(tmp_path, donor)
    assert build._donor_floor_map(tmp_path / "walkmesh.obj") is None
    pre, missing = _prefix_reconcile(tmp_path)
    w = []
    out = _resolve(proj, w)
    assert out == pre.to_bytes() and missing == 0
    built = bgi.BgiWalkmesh.from_bytes(out)
    assert _seam_warnings(w) == [] and built.reachable_floors() == built.all_floors()


# ---- a reordering reshape: every seam still links --------------------------------------------------------

@pytest.mark.parametrize("order", [[3, 1, 2, 0, 4],                  # the rung-1 1607 fork's written order
                                   [4, 3, 2, 1, 0],
                                   [1, 0, 2, 3, 4]])                 # a swap renumbers its neighbours' seams too
def test_a_reordered_reshape_links_every_seam(tmp_path, order):
    donor = _donor()
    proj = _fork(tmp_path, donor, _reshape(extract._world_walkmesh_obj_text(donor), order))
    pre, missing = _prefix_reconcile(tmp_path)                       # the check can fail: un-keyed, it strands
    assert missing and pre.reachable_floors() != pre.all_floors()
    w = []
    built = bgi.BgiWalkmesh.from_bytes(_resolve(proj, w))
    assert _seam_warnings(w) == []
    assert _seam_links(built, order) == _seam_links(donor, range(len(_FLOORS)))
    assert built.reachable_floors() == built.all_floors()
    assert build.verify_walkmesh(proj)["stranded"] == []


@pytest.mark.skipif(not (FIX / "multifloor.bgi.bytes").is_file(),
                    reason="gitignored fixture: run `ff9mapkit extract-templates`")
def test_a_real_multifloor_walkmesh_reversed_links_every_seam(tmp_path):
    donor = bgi.BgiWalkmesh.from_bytes((FIX / "multifloor.bgi.bytes").read_bytes())
    order = sorted(donor.all_floors(), reverse=True)
    proj = _fork(tmp_path, donor, _reshape(extract._world_walkmesh_obj_text(donor), order))
    assert _prefix_reconcile(tmp_path)[1]                            # un-keyed, the reversal drops seams
    w = []
    built = bgi.BgiWalkmesh.from_bytes(_resolve(proj, w))
    assert _seam_warnings(w) == []
    assert _seam_links(built, order) == _seam_links(donor, sorted(donor.all_floors()))
    assert built.reachable_floors() == built.all_floors()


# ---- a floor gone from the .obj: its seams miss, loudly --------------------------------------------------

@pytest.mark.parametrize("order, rename, gone, stranded", [
    ([0, 1, 3, 4], None, 2, []),                                     # floor_2 deleted: 3 and 4 renumber
    ([0, 1, 2, 3, 4], {2: "balcony"}, 2, [2]),                       # floor_2 renamed: an island of its own
    ([0, 1, 2, 3], None, 4, []),                                     # the last floor deleted: nothing renumbers
])
def test_a_floor_gone_from_the_obj_misses_only_its_seams_and_says_which(tmp_path, order, rename, gone,
                                                                        stranded):
    donor = _donor()
    proj = _fork(tmp_path, donor, _reshape(extract._world_walkmesh_obj_text(donor), order, rename))
    w = []
    built = bgi.BgiWalkmesh.from_bytes(_resolve(proj, w))
    [msg] = _seam_warnings(w)
    lost = [s for s in _SEAMS if gone in (s[0], s[2])]
    assert f"{len(lost)} of 5 cross-floor seam(s)" in msg and f"donor floor(s) [{gone}]" in msg
    kept = {frozenset({(fa, a), (fb, b)}) for (fa, a, fb, b) in _SEAMS if gone not in (fa, fb)}
    to_donor = [None if rename and d in rename else d for d in order]
    assert _seam_links(built, to_donor) == kept
    assert sorted(built.all_floors() - built.reachable_floors()) == stranded


def test_apply_seams_misses_come_back_in_the_seams_own_numbering():
    donor = _donor()
    wv = donor.world_verts()
    faces = [tuple(t.vtx) for t in donor.tris if t.floor_ndx != 2]
    fids = [t.floor_ndx for t in donor.tris if t.floor_ndx != 2]
    mesh = bgi.build(wv, faces, floor_ids=fids)                        # floor 2 dropped: 3 -> 2, 4 -> 3
    linked, missing, misses = mesh.apply_seams(_SEAMS, {0: 0, 1: 1, 3: 2, 4: 3})
    assert (linked, missing) == (3, 2)
    assert misses == [s for s in _SEAMS if 2 in (s[0], s[2])]


# ---- an AUTHORED multi-floor mesh: its sidecar is in its own numbering ------------------------------------

def test_an_authored_mesh_with_no_floor_n_names_keeps_its_own_seams(tmp_path):
    # o ground / o terrace (no exporter's floor_<N> names): the sidecar a from-scratch author writes is numbered
    # by the mesh's own BUILT floors, so there is nothing to re-key. An empty map used to drop EVERY seam (and
    # every per-floor light) -- the actor-shadow and walkmesh-sensor benches all lost their links.
    donor = _donor()
    names = {d: n for d, n in enumerate(["ground", "terrace", "yard", "court", "ledge"])}
    proj = _fork(tmp_path, donor, _reshape(extract._world_walkmesh_obj_text(donor), range(len(_FLOORS)), names))
    assert bgi.obj_built_floor_donors(str(tmp_path / "walkmesh.obj")) == [None] * len(_FLOORS)
    assert build._donor_floor_map(tmp_path / "walkmesh.obj") is None
    w = []
    built = bgi.BgiWalkmesh.from_bytes(_resolve(proj, w))
    assert _seam_warnings(w) == []
    assert _seam_links(built, range(len(_FLOORS))) == _seam_links(donor, range(len(_FLOORS)))
    assert built.reachable_floors() == built.all_floors()
