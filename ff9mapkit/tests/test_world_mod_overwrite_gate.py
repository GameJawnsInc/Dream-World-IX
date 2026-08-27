"""THE MOD-OVERWRITE GATE across the world lane -- one gate, one occupancy reader, every writer.

The defect, twice: a STOCK-tree probe ("does the REAL game ship assets here") standing in for an
OCCUPANCY question ("is this target free"). Fixed in ``transplant`` on 2026-07-15 (the dunes-islet
incident), back-ported to ``island.landmass`` on 2026-08-27 (``c39ea162``, after a `world-island` at
the recorded Aldermarch centre read all 19 footprint blocks as free while six held the owner-confirmed
R4 bench), and extended here to the rest of the lane. This file lives across modules on purpose: the
invariant IS cross-module, and the way the hole survived was each verb owning its own copy.

Hermetic throughout (a tmp game root; occupancy is a filesystem question -- no install, no extracted
templates). Two classes of writer, and the split is measured, not stylistic:

  * SYNTHESIZE-or-CARRY writers read NOTHING from the mod tree, so a target another deploy owns is
    silently replaced -> a REFUSAL with an ``allow_overwrite`` / ``--allow-overwrite`` hatch:
    ``terrain.reclaim``, ``terrain.coast``, ``water.water`` / ``deploy_verbatim`` / ``reproduce``,
    ``water.deploy_island_sea``, and (already) ``island.landmass``.
  * IN-PLACE editors READ the deployed override and write it back, so occupancy is the normal case and
    a refusal would be a wall, not a guard rail -> a WARN ROW: ``interior.deploy_mountain_parts``,
    ``entrance.author_entrance --fresh``. (``interior.deploy_changed`` gets neither: every block it
    writes came from ``read_deployed_blocks``, so even a warn would be 100% vacuous.)
"""
from __future__ import annotations

import pytest

from ff9mapkit import config
from ff9mapkit.world import (entrance as EN, extract as X, interior as IN, island as I,
                             mesh as M, palette as PAL, terrain as T, water as W)

MOD = "MOD"


class _Reached(Exception):
    """Raised by a stubbed gate to prove the call site reached it."""


# ---- fixtures ---------------------------------------------------------------------------------

def _deployed(tmp_path, *, cell=(3, 1), disc=1, names=("Terrain.ff9mesh",), mod=MOD):
    """Park override files at ``cell`` in a tmp game root, as a PRIOR deploy would have left them."""
    bx, by = cell
    d = tmp_path / mod / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
    d.mkdir(parents=True, exist_ok=True)
    for n in names:
        (d / f"Block[{bx}][{by}] {n}").write_bytes(b"PRIOR-DEPLOY")
    return d


def _block(x, y, part="Terrain", tris=4):
    from ff9mapkit.world.extract import BlockMesh, CH_POS, CH_NRM, CH_UV, CH_TAN
    n = tris * 3
    chan = {CH_POS: [[0.0, 0.0, 0.0]] * n, CH_NRM: [[0.0, 1.0, 0.0]] * n,
            CH_UV: [[0.5, 0.5]] * n, CH_TAN: [[236.0, 0.0, 0.0, 1.0]] * n}
    return BlockMesh(name=f"Block[{x}][{y}] {part}", disc=1, x=x, y=y, lod="0_1", vcount=n, stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays=chan, flat_index=list(range(n)),
                     tris=[[i, i + 1, i + 2] for i in range(0, n, 3)], raw_vbuf=b"", raw_ibuf=b"",
                     use32=True, submeshes=[])


@pytest.fixture
def wrote(monkeypatch):
    """Capture every write seam so a refusal can be proven to happen BEFORE the first one."""
    seen = []
    monkeypatch.setattr(M, "deploy_override", lambda bm, **k: seen.append((bm.x, bm.y, k.get("part"))))
    monkeypatch.setattr(M, "deploy_donor_sidecar", lambda dx, dy, **k: seen.append(("donor", k["x"], k["y"])))
    return seen


# ---- the shared reader + the shared gate ------------------------------------------------------

def test_existing_overrides_part_scope(tmp_path):
    """``parts`` narrows the ONE reader instead of minting a second one at the call site that needs
    it. Default (None) still answers the whole cell -- the shape island/fuse were built against."""
    _deployed(tmp_path, names=("Terrain.ff9mesh", "Sea4.ff9mesh", "Donor.txt"))
    kw = dict(disc=1, lod="0_1", game=tmp_path)
    assert len(M.existing_overrides([(3, 1)], MOD, **kw)) == 3
    assert [p.endswith("Sea4.ff9mesh") for p in M.existing_overrides([(3, 1)], MOD, parts=("Sea4",), **kw)] == [True]
    assert M.existing_overrides([(3, 1)], MOD, parts=("Object",), **kw) == []
    # the sidecar is addressed by its part name too ("Donor"), not by extension
    assert len(M.existing_overrides([(3, 1)], MOD, parts=("Donor", "Terrain"), **kw)) == 2


def test_existing_overrides_part_scope_ignores_parked_backups(tmp_path):
    """REGRESSION PIN, carried to the scoped path: ``deploy_override`` parks ``<name>.bak-<ts>``
    beside a file it overwrites. A part scope must not resurrect the bare-``startswith`` bug that
    would count a backup as occupancy and refuse forever after the first legitimate re-deploy."""
    _deployed(tmp_path, names=("Terrain.ff9mesh.bak-20260101-000000",))
    kw = dict(disc=1, lod="0_1", game=tmp_path)
    assert M.existing_overrides([(3, 1)], MOD, **kw) == []
    assert M.existing_overrides([(3, 1)], MOD, parts=("Terrain",), **kw) == []


def test_mod_overwrite_gate_refuses_waives_and_survives_no_install(tmp_path):
    _deployed(tmp_path, names=("Terrain.ff9mesh", "Sea4.ff9mesh"))
    kw = dict(disc=1, lod="0_1", game=tmp_path)
    with pytest.raises(ValueError, match=r"already holds 2 deployed override file"):
        M.mod_overwrite_gate([(3, 1)], MOD, what="test footprint", **kw)
    assert len(M.mod_overwrite_gate([(3, 1)], MOD, allow_overwrite=True, **kw)) == 2   # hatch
    assert M.mod_overwrite_gate([(9, 9)], MOD, **kw) == []                             # clear target
    # an unresolvable install is not an occupancy claim -- it is nothing to hit
    assert M.mod_overwrite_gate([(3, 1)], MOD, disc=1, lod="0_1", game=tmp_path / "nope") == []


def test_one_gate_and_one_reader_in_the_kit():
    """``fuse``/``island`` shared the reader after ``c39ea162``; every writer now also shares the
    GATE. Two copies of one idea, one of which got fixed, IS the defect this whole file is about."""
    from ff9mapkit.world import fuse as F
    assert F._existing_overrides is M.existing_overrides


# ---- terrain.reclaim --------------------------------------------------------------------------

def _reclaim_offline(monkeypatch):
    monkeypatch.setattr(PAL, "apply_palette_uvs", lambda bm, **k: bm)      # no install needed


def test_reclaim_refuses_a_cell_another_deploy_owns(tmp_path, monkeypatch, wrote):
    """THE DEFECT THIS CLOSES for the reclaim lane: ``reclaim`` SYNTHESIZES its mesh and consults the
    mod tree nowhere, so a designated 'ocean' cell that already carries a prior deploy's land was
    replaced without a word."""
    _reclaim_offline(monkeypatch)
    _deployed(tmp_path, names=("Terrain.ff9mesh", "Donor.txt"))
    with pytest.raises(ValueError, match=r"reclaim target cell\(s\) already holds 2 deployed override file"):
        T.reclaim(MOD, cells=[(3, 1)], profile="flat", game=tmp_path)
    assert not wrote                                          # refused BEFORE the first write


def test_reclaim_allow_overwrite_waives_the_gate(tmp_path, monkeypatch, wrote):
    _reclaim_offline(monkeypatch)
    _deployed(tmp_path)
    s = T.reclaim(MOD, cells=[(3, 1)], profile="flat", game=tmp_path, allow_overwrite=True, skip_mirror=True)
    assert len(s["cells"]) == 1 and wrote == [(3, 1, "Terrain")]


def test_reclaim_refuses_the_whole_run_not_the_occupied_cell(tmp_path, monkeypatch, wrote):
    """The gate reads the WHOLE cell list before the loop. Refusing at cell 2 of 3 would leave a
    half-deploy -- the state hardest to diagnose and hardest to undo."""
    _reclaim_offline(monkeypatch)
    _deployed(tmp_path, cell=(5, 1))                          # only the LAST cell is occupied
    with pytest.raises(ValueError, match="already holds"):
        T.reclaim(MOD, cells=[(3, 1), (4, 1), (5, 1)], profile="flat", game=tmp_path)
    assert not wrote


def test_reclaim_gate_reads_the_WRITE_disc_not_the_read_disc(tmp_path, monkeypatch, wrote):
    """``target_disc`` (Path D's sentinel namespace, engine patch s74) is where the bytes LAND, so
    that is the tree the gate must scan. A gate reading the wrong disc looks populated and protects
    nothing; here the READ disc's occupancy must NOT refuse."""
    _reclaim_offline(monkeypatch)
    _deployed(tmp_path, disc=1)                               # occupied on the READ disc only
    s = T.reclaim(MOD, cells=[(3, 1)], profile="flat", game=tmp_path, target_disc=9, dry_run=True)
    assert len(s["cells"]) == 1

    _deployed(tmp_path, disc=9)                               # now occupy the WRITE disc
    with pytest.raises(ValueError, match="on disc 9"):
        T.reclaim(MOD, cells=[(3, 1)], profile="flat", game=tmp_path, target_disc=9)
    assert not wrote


# ---- terrain.coast ----------------------------------------------------------------------------

def _coast_offline(monkeypatch):
    monkeypatch.setattr(X, "read_block", lambda dx, dy, **k: _block(dx, dy))


def test_coast_refuses_a_cell_another_deploy_owns(tmp_path, monkeypatch, wrote):
    """A verbatim CARRY writes DONOR bytes; like reclaim it reads nothing from the mod tree."""
    _coast_offline(monkeypatch)
    _deployed(tmp_path, names=("Terrain.ff9mesh",))
    with pytest.raises(ValueError, match=r"coast target cell\(s\) already holds 1 deployed override file"):
        T.coast(MOD, cells=[(3, 1)], donor=(18, 15), game=tmp_path)
    assert not wrote


def test_coast_allow_overwrite_waives_and_gates_the_write_disc(tmp_path, monkeypatch, wrote):
    _coast_offline(monkeypatch)
    _deployed(tmp_path)
    assert T.coast(MOD, cells=[(3, 1)], donor=(18, 15), game=tmp_path,
                   allow_overwrite=True, skip_mirror=True)["cells"]
    assert wrote == [(3, 1, "Terrain"), ("donor", 3, 1)]
    wrote.clear()
    # occupancy on the READ disc alone must not refuse a write aimed at disc 9...
    assert T.coast(MOD, cells=[(3, 1)], donor=(18, 15), game=tmp_path,
                   target_disc=9, dry_run=True)["cells"]
    _deployed(tmp_path, disc=9)                               # ...but occupancy on the WRITE disc must
    with pytest.raises(ValueError, match="on disc 9"):
        T.coast(MOD, cells=[(3, 1)], donor=(18, 15), game=tmp_path, target_disc=9)
    assert not wrote


# ---- water: water / deploy_verbatim / reproduce ------------------------------------------------

def test_water_refuses_a_cell_another_deploy_owns(tmp_path, wrote):
    _deployed(tmp_path, cell=(3, 17))
    with pytest.raises(ValueError, match=r"water already holds 1 deployed override file"):
        W.water(MOD, cells=[(3, 17)], game=tmp_path)
    assert not wrote


def test_water_allow_overwrite_waives_the_gate(tmp_path, wrote):
    _deployed(tmp_path, cell=(3, 17))
    s = W.water(MOD, cells=[(3, 17)], game=tmp_path, allow_overwrite=True, skip_mirror=True)
    assert len(s["cells"]) == 1
    assert [t[2] for t in wrote if t[0] != "donor"] == ["Terrain", "Sea3", "Sea5", "Sea4", "Sea1", "Sea2"]
    assert ("donor", 3, 17) in wrote


def test_water_refuses_before_the_first_cell_is_written(tmp_path, wrote):
    """``_deploy_ocean_cell`` deploys ONE cell inside the caller's loop, which is exactly why the gate
    is NOT there: a per-cell refusal at cell 2 of 2 would leave cell 1 already overwritten."""
    _deployed(tmp_path, cell=(4, 17))                         # only the second cell is occupied
    with pytest.raises(ValueError, match="already holds"):
        W.water(MOD, cells=[(3, 17), (4, 17)], game=tmp_path)
    assert not wrote


def test_water_verbatim_and_reproduce_share_the_gate(tmp_path, monkeypatch, wrote):
    """All three public water verbs funnel into ``_deploy_ocean_cell``, so all three must gate --
    the A/B reference lanes overwrite a neighbour's cell just as thoroughly as the synthesizer."""
    monkeypatch.setattr(X, "read_block", lambda sx, sy, **k: _block(sx, sy, part=k.get("part", "sea4")))
    _deployed(tmp_path, cell=(3, 17))
    with pytest.raises(ValueError, match=r"water-verbatim already holds 1 deployed override file"):
        W.deploy_verbatim(MOD, cells=[(3, 17)], source=(8, 4), game=tmp_path)
    with pytest.raises(ValueError, match=r"water-reproduce already holds 1 deployed override file"):
        W.reproduce(MOD, cells=[(3, 17)], source=(8, 4), game=tmp_path)
    assert not wrote


# ---- water.deploy_island_sea (the part-scoped gate) --------------------------------------------

def test_island_sea_gate_is_scoped_past_the_callers_own_land(tmp_path, wrote):
    """THE ONE PLACE WHOLE-CELL SCOPE WOULD BE WRONG. ``deploy_island_sea`` lays the sea around an
    island whose LAND ``Terrain`` the caller itself just wrote on these very cells, so an unscoped
    read would refuse on this deploy's own co-tenant and the gate would be unusable."""
    _deployed(tmp_path, cell=(3, 17), names=("Terrain.ff9mesh",))
    s = W.deploy_island_sea(MOD, cells=[(3, 17)], game=tmp_path)
    assert s["cells"] and [t[2] for t in wrote if t[0] != "donor"] == ["Sea3", "Sea5", "Sea4", "Sea1", "Sea2"]


def test_island_sea_refuses_another_deploys_water(tmp_path, wrote):
    _deployed(tmp_path, cell=(3, 17), names=("Terrain.ff9mesh", "Sea4.ff9mesh"))
    with pytest.raises(ValueError, match=r"island-sea target cell\(s\) already holds 1 deployed override file"):
        W.deploy_island_sea(MOD, cells=[(3, 17)], game=tmp_path)
    assert not wrote
    assert W.deploy_island_sea(MOD, cells=[(3, 17)], game=tmp_path, allow_overwrite=True)["cells"]


# ---- island.landmass routes through the SHARED gate -------------------------------------------

def test_landmass_routes_through_the_shared_gate(tmp_path, monkeypatch):
    """``island.landmass``'s inline copy of the gate was replaced by the shared one; pin that it is
    the SHARED one that runs, with the WRITE disc. (The refusal itself is owned by
    ``test_world_island.py``, whose five tests came in with ``c39ea162``.)"""
    seen = []

    def _record(cells, mod, **k):
        seen.append((sorted(cells), k["disc"], k["what"]))
        raise _Reached                                       # stop here: the rest of the mint is not the subject

    monkeypatch.setattr(I, "_real_block_parts", lambda blk, **k: {})     # stock says FREE: the blind spot
    monkeypatch.setattr(M, "mod_overwrite_gate", _record)
    with pytest.raises(_Reached):
        I.landmass(MOD, cell=(3, 1), base_radius=20.0, seed=5.0, flat=True,
                   game=tmp_path, target_disc=9)
    assert len(seen) == 1
    blocks, disc, what = seen[0]
    assert (3, 1) in blocks and disc == 9 and what == "landmass footprint"   # the WRITE disc, not --disc


# ---- interior: a WARN ROW, never a refusal ----------------------------------------------------

def _mountain_res(blocks=((3, 1),)):
    return {"changed_parts": {}, "donor_ref": (0, 0), "report": {"blocks": [list(b) for b in blocks]}}


def test_mountain_parts_warns_about_the_parts_it_blanks(tmp_path):
    """``deploy_mountain_parts`` writes carried content OR A HIDDEN BLANK for every ENSEMBLE_PART and
    never reads those parts back, so a prior deploy's ``Object`` (a ``world-entrance`` building, say)
    at a span block is erased silently. Name it -- but do NOT refuse: these verbs reshape an ALREADY
    DEPLOYED kit island (``read_deployed_blocks`` refuses when the mod tree is EMPTY), so a refusal
    would fire on every legitimate run. A wall, not a guard rail."""
    _deployed(tmp_path, cell=(3, 1), names=("Object.ff9mesh", "Terrain.ff9mesh"))
    lines = []
    out = IN.deploy_mountain_parts(_mountain_res(), mod_folder=MOD, game=tmp_path,
                                   skip_mirror=True, log=lines.append)
    warn = [l for l in lines if l.startswith("!! WARNING")]
    assert len(warn) == 1 and "Object.ff9mesh" in warn[0]
    assert "Terrain.ff9mesh" not in warn[0]        # Terrain is not an ENSEMBLE_PART -- it is not touched
    assert out                                     # WARNED, and then deployed: a warn is not a refusal


def test_mountain_parts_is_quiet_on_a_clear_span(tmp_path):
    """A warn that fires on every run is noise, not a signal."""
    lines = []
    IN.deploy_mountain_parts(_mountain_res(), mod_folder=MOD, game=tmp_path,
                             skip_mirror=True, log=lines.append)
    assert not [l for l in lines if l.startswith("!! WARNING")]


# ---- entrance: --fresh names what it discards --------------------------------------------------

def test_fresh_discard_note_names_the_bytes_fresh_throws_away(tmp_path):
    """``--fresh`` re-reads PRISTINE p0data, so on a cell another deploy owns it silently reverts that
    deploy's terrain/building to stock. Not a refusal (re-doing your own block is what --fresh is FOR),
    but the operator must be told WHAT is being discarded."""
    _deployed(tmp_path, cell=(17, 12), names=("Terrain.ff9mesh", "Object.ff9mesh"))
    note = EN.fresh_discard_note(MOD, 17, 12, game=tmp_path)
    assert len(note["fresh_discards"]) == 2
    assert "DISCARDING the 2 deployed override(s)" in note["fresh_warning"]


def test_fresh_discard_note_is_scoped_to_what_fresh_actually_rereads(tmp_path):
    """A ``Donor.txt`` or a sea layer at the same cell survives ``--fresh`` untouched, so claiming it
    is discarded would be a false alarm -- and a false alarm is how a real one stops being read."""
    _deployed(tmp_path, cell=(17, 12), names=("Donor.txt", "Sea4.ff9mesh"))
    assert EN.fresh_discard_note(MOD, 17, 12, game=tmp_path) == {}
    _deployed(tmp_path, cell=(17, 12), names=("Terrain.ff9mesh.bak-20260101-000000",))
    assert EN.fresh_discard_note(MOD, 17, 12, game=tmp_path) == {}          # backups are not content
    assert EN.fresh_discard_note(MOD, 17, 12, game=tmp_path / "nope") == {}  # no install: nothing to say


def test_author_entrance_wires_the_fresh_note_into_its_summary(tmp_path, monkeypatch):
    """THE CALL SITE, not just the helper. The gate that survived six weeks of green suites was one
    whose owning test monkeypatched the very function it needed to observe; a helper proven alone and
    never proven CALLED is the same shape of nothing."""
    pytest.importorskip("UnityPy")
    try:
        config.find_game_path(None)
    except Exception:                                          # noqa: BLE001
        pytest.skip("needs the FF9 install (world dispatchers come from p0data)")
    seen = []

    def _note(mod_folder, bx, by, **k):
        seen.append((mod_folder, bx, by))
        return {"fresh_discards": ["<sentinel>"], "fresh_warning": "SENTINEL"}

    monkeypatch.setattr(EN, "fresh_discard_note", _note)
    info = EN.author_entrance(cell=(35, 25), mod_folder="FF9CustomMap_test_nonexistent", field=300,
                              fresh=True, dry_run=True)
    assert seen == [("FF9CustomMap_test_nonexistent", 17, 12)]
    assert info["fresh_warning"] == "SENTINEL"


def test_author_entrance_says_nothing_when_not_fresh(tmp_path, monkeypatch):
    """Without ``--fresh`` the writer STACKS on the deployed override, so there is nothing discarded
    and nothing to warn about -- the note must not fire on the ordinary loop."""
    pytest.importorskip("UnityPy")
    try:
        config.find_game_path(None)
    except Exception:                                          # noqa: BLE001
        pytest.skip("needs the FF9 install (world dispatchers come from p0data)")
    monkeypatch.setattr(EN, "fresh_discard_note",
                        lambda *a, **k: pytest.fail("fresh_discard_note ran without fresh=True"))
    info = EN.author_entrance(cell=(35, 25), mod_folder="FF9CustomMap_test_nonexistent", field=300,
                              dry_run=True)
    assert "fresh_warning" not in info
