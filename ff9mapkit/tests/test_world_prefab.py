"""Landmass PREFABS (rungs P1/P1b, studies/overworld-editor/PREFABS.md): the catalog, the placement, the identity.

``world-prefab NAME --cell BX,BY --mod-folder F`` stamps a frozen composition (a minted island or a walked stock carry
unit, plus carried relief) on an anchor block. It refuses -- before writing anything -- unless the window is clear
(the target and the FolderNames stack, footprint and ring) and the prefab staged there is the catalog's land: the full
fingerprint at a clean site, or, beside stock land (THE NAV MARGIN), a reference copy at the catalog's clean site that
is the catalog's land and that the target equals outside the margin, with the margin's sea settled by the coast-nav
stamp. Hermetic tests cover the catalog rules, the frame arithmetic, the fingerprint's own invariances and every
refusal; the install-gated ones re-take the shipped fingerprints, place for real, and prove the identity CAN fail (a
coast-nav regression is refused).
"""
from __future__ import annotations

import warnings

import pytest

from ff9mapkit.world import mesh as M, prefab as PF
from ff9mapkit.world.extract import BlockMesh, CH_NRM, CH_POS, CH_TAN, CH_UV

ISLAND = {"table": "island", "center": [32.0, 32.0], "radius": 60.0, "seed": 5.0}


def _catalog(tmp_path, body: str):
    p = tmp_path / "prefabs.toml"
    p.write_text(body, encoding="utf-8")
    return p


def _entry(rows: str, **extra) -> str:
    head = "\n".join(f"{k} = {v!r}".replace("'", '"') for k, v in
                     {"name": "x", "status": "candidate", **extra}.items())
    return f"[[prefab]]\n{head}\n{rows}"


_ISL = '[[prefab.rows]]\ntable = "island"\ncenter = [32.0, 32.0]\nseed = 5.0\n'
_TP = '[[prefab.rows]]\ntable = "transplant"\ncell = [1, 0]\ndonor = [9, 5]\nsize = [2, 3]\nrot = 90\n'
_FOREST = '[[prefab.rows]]\ntable = "forest"\ncenter = [52.0, 20.0]\n'


# ---------------------------------------------------------------- the catalog
def test_the_shipped_catalog_is_well_formed_and_fingerprinted():
    cat = PF.load_catalog()
    assert {p["name"] for p in cat} >= {"desert-peak-isle", "meadow-grove-isle", "comma-isle", "beach-chain"}
    for p in cat:
        assert p["status"] in PF.STATUSES
        assert len(p["fingerprint"]) == 64 and p["footprint"], p["name"]
        assert all(r["table"] in PF.PREFAB_TABLES for r in p["rows"])
        assert p["rows"][0]["table"] in PF.BASE_TABLES
        if PF.stamped_nav(p):
            assert len(p["fingerprint_cell"]) == 2, p["name"]


@pytest.mark.parametrize("rows, why", [
    ('[[prefab.rows]]\ntable = "island"\ncenter = [32.0, 32.0]\n', "needs its seed"),
    ('[[prefab.rows]]\ntable = "forest"\ncenter = [1.0, 1.0]\n', "first row is the"),
    (_ISL + '[[prefab.rows]]\ntable = "river"\ncenter = [1.0, 1.0]\n', "not been measured"),
    (_ISL + '[[prefab.rows]]\ntable = "forest"\ncenter = [1.0, 1.0]\nprefab_frame = true\n', "set by placement"),
    (_ISL + '[[prefab.rows]]\ntable = "forest"\nnear = [1.0, 1.0]\ncenter = [1.0, 1.0]\n', "set by placement"),
    (_ISL + '[[prefab.rows]]\ntable = "hill"\n', "exact placement"),
    (_ISL + _ISL, "one base"),
    (_TP + _ISL, "one base"),
    ('[[prefab.rows]]\ntable = "transplant"\ndonor = [9, 5]\n', "names cell"),
])
def test_the_catalog_refuses_what_a_prefab_cannot_hold(tmp_path, rows, why):
    with pytest.raises(ValueError, match=why):
        PF.load_catalog(_catalog(tmp_path, _entry(rows)))


def test_the_catalog_refuses_a_bad_status_a_duplicate_name_and_an_unsited_island_fingerprint(tmp_path):
    with pytest.raises(ValueError, match="status"):
        PF.load_catalog(_catalog(tmp_path, _entry(_ISL, status="walked")))
    with pytest.raises(ValueError, match="unique name"):
        PF.load_catalog(_catalog(tmp_path, _entry(_ISL) + "\n" + _entry(_ISL)))
    with pytest.raises(ValueError, match="fingerprint_cell"):
        PF.load_catalog(_catalog(tmp_path, _entry(_ISL, fingerprint="f" * 64)))
    PF.load_catalog(_catalog(tmp_path, _entry(_TP, fingerprint="f" * 64)))      # a carried sea needs no clean site


# ---------------------------------------------------------------- the frame arithmetic
def test_expand_shifts_by_whole_blocks_and_frames_only_the_tables_that_take_it():
    prefab = {"name": "x", "rows": [dict(ISLAND), {"table": "mountain", "center": [24.0, 36.0], "rot": 90.0},
                                    {"table": "forest", "center": [52.0, 20.0]}]}
    a, b = PF.expand(prefab, (1, 14)), PF.expand(prefab, (3, 16))
    assert a[0]["center"] == [96.0, -928.0]                     # the measured A/B site
    assert [r["step"] for r in a] == [1, 2, 3]
    assert [r.get("prefab_frame") for r in a] == [True, True, None]
    for ra, rb in zip(a, b):
        assert rb["center"] == [ra["center"][0] + 128.0, ra["center"][1] - 128.0]
    assert prefab["rows"][0]["center"] == [32.0, 32.0]          # the catalog row is not mutated
    doc = PF.doc_for(a)
    assert set(doc) == {"island", "mountain", "forest"} and "table" not in doc["island"][0]


def test_a_transplant_base_is_placed_by_cell_and_carries_its_navigation(tmp_path):
    p = PF.load_catalog(_catalog(tmp_path, _entry(_TP + _FOREST)))[0]
    rows = PF.expand(p, (23, 4))
    assert rows[0]["cell"] == [0, 4] and "prefab_frame" not in rows[0]          # the anchor's +1 column wraps
    assert rows[1]["center"] == [64.0 * 23 + 52.0, -64.0 * 5 + 20.0]
    assert not PF.stamped_nav(p) and PF.stamped_nav({"rows": [dict(ISLAND)]})
    assert not PF.stamped_nav({"rows": [dict(ISLAND, coastnav=False)]})


def test_block_offsets_and_points_fold_across_the_x_seam():
    assert PF.rel_block((0, 5), (23, 4)) == (1, 1)
    assert PF.rel_block((23, 5), (0, 4)) == (-1, 1)
    assert PF.label_of((1, 1), (23, 4)) == (0, 5)
    assert PF.label_of((-1, 0), (0, 4)) == (23, 4)
    assert PF.rel_point(2.0, -300.0, (23, 4)) == (66.0, 20.0)   # just past x = 0 is 66u past the anchor's corner
    assert PF.rel_point(1530.0, -300.0, (0, 4)) == (-6.0, 20.0)


def test_read_windows_follow_each_verb_s_reach():
    rows = PF.expand({"name": "x", "rows": [dict(ISLAND), {"table": "hill", "center": [32.0, 32.0], "radius": 100.0},
                                            {"table": "forest", "center": [32.0, 32.0], "reach": 10.0}]}, (10, 9))
    win = PF.read_windows(rows)
    assert {(10, 9)} <= win and (8, 9) in win and (12, 11) in win      # the hill: max(96, 110) = 110u
    assert (7, 9) not in win
    assert PF.read_windows(PF.expand({"name": "x", "rows": [dict(ISLAND), {"table": "forest",
                                      "center": [32.0, 32.0]}]}, (5, 0))) >= {(5, 0), (4, 1)}
    assert all(0 <= by < M.GRID_ROWS for _bx, by in win)


def test_the_margin_mask_is_the_same_triangles_wherever_the_reference_stands():
    """The mask is built from the TARGET's stock ground but judged on frame-relative centroids, so the reference copy
    staged at another anchor masks exactly the same triangles."""
    near = PF.margin_mask([(10 * 64 + 70.0, -10 * 64 + 5.0)], (10, 9))      # 6u east of the footprint's x = 64 line
    assert near(64.0 - 9.0, 5.0) and not near(64.0 - 11.0, 5.0)          # 15u and 17u from the point
    seam = PF.margin_mask([(1.0, -300.0)], (23, 4))                       # ground just past x = 0
    assert seam(64.0 - 2.0, 20.0)                                          # the anchor block's east edge, 3u away


# ---------------------------------------------------------------- the fingerprint
def _mesh(path, tris, *, nrm=(0.0, 1.0, 0.0), uv=(0.25, 0.5), tan_x=12.0, mask=False):
    pos, nr, uvs, tan, flat, t_out = [], [], [], [], [], []
    for tri in tris:
        base = len(pos)
        for c in tri:
            pos.append(list(c))
            nr.append(list(nrm))
            uvs.append([uv[0] + c[0] / 64.0, uv[1]])
            tan.append([float(tan_x), 0.0, 0.0, 1.0])
            flat.append(len(pos) - 1)
        t_out.append([base, base + 1, base + 2])
    bm = BlockMesh(name="Block[0][0] Terrain", disc=1, x=0, y=0, lod="0_1", vcount=len(pos), stride=48,
                   channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                   chan_arrays={CH_POS: pos, CH_NRM: nr, CH_UV: uvs, CH_TAN: tan},
                   flat_index=flat, tris=t_out, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])
    M.write_ff9mesh(bm, path)
    if mask is False:
        return PF.mesh_digest(path)
    return PF.mesh_digest(path, mask_tri=mask, label=(0, 0), cell=(0, 0))


T1 = [(0.0, 3.0, 0.0), (8.0, 3.0, 0.0), (0.0, 3.0, -8.0)]
T2 = [(8.0, 3.0, 0.0), (8.0, 3.0, -8.0), (0.0, 3.0, -8.0)]


def test_the_digest_ignores_vertex_order_and_normal_noise_but_keeps_winding_and_uvs(tmp_path):
    base = _mesh(tmp_path / "a.ff9mesh", [T1, T2])
    assert _mesh(tmp_path / "b.ff9mesh", [T2, T1]) == base                          # triangle order
    assert _mesh(tmp_path / "c.ff9mesh", [T1[1:] + T1[:1], T2]) == base             # rotated corners, same winding
    assert _mesh(tmp_path / "d.ff9mesh", [T1, T2], nrm=(1e-9, 1.0, 0.0)) == base    # the mint's normal noise
    assert _mesh(tmp_path / "e.ff9mesh", [T1[::-1], T2]) != base                    # flipped winding = other land
    assert _mesh(tmp_path / "f.ff9mesh", [T1, T2], uv=(0.25, 0.75)) != base          # other tiles
    assert _mesh(tmp_path / "g.ff9mesh", [T1, [(8.0, 3.5, 0.0)] + T2[1:]]) != base   # a moved vertex


def test_the_margin_mask_blanks_only_the_water_class_of_the_triangles_it_names(tmp_path):
    """The review's finding: masking every water class hid any change in the sea's navigation. The mask now blanks
    the class only on the triangles the predicate names; every other class stays in the hash."""
    def sea(n, t, mask=False):
        return _mesh(tmp_path / f"{n}.ff9mesh", [T1, T2], tan_x=t, mask=mask)
    everywhere = lambda rx, rz: True                                                       # noqa: E731
    nowhere = lambda rx, rz: False                                                         # noqa: E731
    assert sea("a", 57 << 2, everywhere) == sea("b", 53 << 2, everywhere)       # a masked class is free
    assert sea("c", 57 << 2, nowhere) != sea("d", 53 << 2, nowhere)             # an unmasked class is identity
    assert sea("c2", 57 << 2) != sea("d2", 53 << 2)                             # ... and so is every class by default
    assert sea("e", (57 << 2) | 1, everywhere) != sea("f", (57 << 2) | 2, everywhere)   # other bits kept
    assert sea("g", 17 << 2, everywhere) != sea("h", 16 << 2, everywhere)               # ground classes kept
    near_t1 = lambda rx, rz: rx < 3.0 and rz > -3.0                             # T1's centroid only  # noqa: E731
    assert _mesh(tmp_path / "i.ff9mesh", [T1], tan_x=57 << 2, mask=near_t1) == \
        _mesh(tmp_path / "j.ff9mesh", [T1], tan_x=53 << 2, mask=near_t1)
    assert _mesh(tmp_path / "k.ff9mesh", [T2], tan_x=57 << 2, mask=near_t1) != \
        _mesh(tmp_path / "l.ff9mesh", [T2], tan_x=53 << 2, mask=near_t1)


def _put(root, label, part="Terrain.ff9mesh", data=b"x", disc=1):
    d = root / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{label[1]}"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"Block[{label[0]}][{label[1]}] {part}").write_bytes(data)


def test_the_fingerprint_is_keyed_by_offset_and_skips_backups(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for root, cell in ((a, (3, 5)), (b, (23, 9))):
        _put(root, PF.label_of((0, 0), cell), "Donor.txt", b"Block[7][17]")
        _put(root, PF.label_of((1, 0), cell), "Donor.txt", b"Block[7][17]")
    _put(b, PF.label_of((1, 0), (23, 9)), "Donor.txt.bak-20261108-1", b"old")
    blocks_a = {PF.label_of(r, (3, 5)) for r in ((0, 0), (1, 0))}
    blocks_b = {PF.label_of(r, (23, 9)) for r in ((0, 0), (1, 0))}
    assert blocks_b == {(23, 9), (0, 9)}                                             # across the seam
    assert PF.fingerprint(a, (3, 5), blocks_a) == PF.fingerprint(b, (23, 9), blocks_b)
    _put(b, (0, 9), "Donor.txt", b"Block[20][5]")
    assert PF.fingerprint(a, (3, 5), blocks_a) != PF.fingerprint(b, (23, 9), blocks_b)


# ---------------------------------------------------------------- the refusals (nothing is written)
FOOT = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 0], [0, 1], [1, -1], [1, 0], [1, 1]]
GOOD = "f" * 64


@pytest.fixture
def fake(tmp_path, monkeypatch):
    """A one-prefab catalog, a tmp 'install', a recorder in place of the compose, a clean site, a staged copy that is
    the catalog's land, and a settled stamp. Each test breaks one of them."""
    from ff9mapkit import config
    game = tmp_path / "game"
    game.mkdir()
    monkeypatch.setattr(config, "find_game_path", lambda g=None: game)
    cat = _catalog(tmp_path, _entry(_ISL + _FOREST, fingerprint=GOOD, footprint=FOOT, fingerprint_cell=[1, 14]))
    composed, staged = [], []

    def stage(prefab, cell, game=None, keep=False):
        staged.append(tuple(cell))
        root = tmp_path / f"stage{len(staged)}"
        root.mkdir()
        return {"fingerprint": GOOD, "footprint": sorted(tuple(b) for b in FOOT),
                "blocks": sorted(PF.label_of(b, cell) for b in FOOT), "nav": {}, "root": root if keep else None}
    monkeypatch.setattr(PF, "_compose", lambda folder, rows, **kw: composed.append((str(folder), rows)))
    monkeypatch.setattr(PF, "stage", stage)
    monkeypatch.setattr(PF, "nav_settled", lambda *a, **k: {})
    monkeypatch.setattr(PF, "stock_ground", lambda *a, **k: {})
    monkeypatch.setattr(PF, "fingerprint", lambda root, cell, blocks, **kw: GOOD)
    return {"game": game, "cat": cat, "composed": composed, "staged": staged, "tmp": tmp_path}


def _place(fake, cell=(10, 9), **kw):
    kw.setdefault("stack", ())
    return PF.place("x", cell, "Target", catalog=fake["cat"], log=lambda *a: None, **kw)


def test_a_clear_window_at_a_clean_site_places_with_the_full_fingerprint(fake):
    rep = _place(fake)
    assert rep["written"] == GOOD and rep["identity"].startswith("clean site") and len(fake["composed"]) == 1
    assert fake["composed"][0][1][0]["center"] == [64.0 * 10 + 32.0, -64.0 * 10 + 32.0]
    assert fake["staged"] == [(10, 9)]                                   # no reference copy needed
    assert not any((fake["tmp"] / "stage1").exists() for _ in [0])       # the staging folder is removed


def test_a_dry_run_writes_nothing(fake):
    assert _place(fake, dry_run=True)["written"] is None and not fake["composed"]


def test_a_busy_target_window_refuses_footprint_ring_and_read_window(fake, tmp_path):
    (tmp_path / "far").mkdir()
    far = _catalog(tmp_path / "far", _entry(_ISL + _FOREST + "reach = 200.0\n", name="far", fingerprint=GOOD, footprint=FOOT,
                                    fingerprint_cell=[1, 14]))
    _put(fake["game"] / "Target", (13, 9))                          # in the forest's 200u read window, past the ring
    PF.place("x", (10, 9), "Target", catalog=fake["cat"], stack=(), dry_run=True, log=lambda *a: None)  # 96u: clear
    with pytest.raises(PF.PrefabRefused, match="already holds land") as e:
        PF.place("far", (10, 9), "Target", catalog=far, stack=(), log=lambda *a: None)
    assert e.value.where == [(13, 9)] and not fake["composed"]


def test_kit_land_in_the_footprint_ring_refuses(fake, tmp_path):
    """The nav stamp classes the prefab's sea against ground 16u past its footprint (and a neighbour's own sea would go
    stale beside new land), so the target's land in the ring is in the way even with no relief row (an island-only
    prefab), on disc 4 as on disc 1."""
    (tmp_path / "isle").mkdir()
    bare = _catalog(tmp_path / "isle", _entry(_ISL, name="isle", fingerprint=GOOD, footprint=FOOT,
                                              fingerprint_cell=[1, 14]))
    _put(fake["game"] / "Target", (12, 11), disc=4)
    with pytest.raises(PF.PrefabRefused, match="already holds land") as e:
        PF.place("isle", (10, 9), "Target", catalog=bare, stack=(), log=lambda *a: None)
    assert e.value.where == [(12, 11)]


def test_another_folder_in_the_stack_refuses_on_the_footprint_and_its_ring_only(fake):
    """The stamp's loader reads only the target folder and stock, so another folder's land beside the footprint would
    be invisible to it (the review's finding): the ring counts; a block past the ring does not."""
    other = fake["game"] / "Other"
    _put(other, (13, 9))                                            # past the ring: not this folder's business
    _place(fake, stack=(other,), dry_run=True)
    _put(other, (12, 10))                                           # the ring
    with pytest.raises(PF.PrefabRefused, match="Other") as e:
        _place(fake, stack=(other,))
    assert e.value.where == [(12, 10)] and not fake["composed"]


def test_a_broken_identity_at_a_clean_site_is_a_regression_and_writes_nothing(fake, monkeypatch):
    real = PF.stage

    def stage(prefab, cell, game=None, keep=False):
        out = real(prefab, cell, game=game, keep=keep)
        return dict(out, fingerprint="0" * 64)
    monkeypatch.setattr(PF, "stage", stage)
    with pytest.raises(PF.PrefabRefused, match="regression to find"):
        _place(fake)
    assert not fake["composed"]


def test_unsettled_navigation_at_a_clean_site_refuses(fake, monkeypatch):
    real = PF.stage
    monkeypatch.setattr(PF, "stage", lambda prefab, cell, game=None, keep=False:
                        dict(real(prefab, cell, game=game, keep=keep), nav={53: 27}))
    with pytest.raises(PF.PrefabRefused, match="regression in the stamp"):
        _place(fake)
    assert not fake["composed"]


# ---- the nav margin: a reference copy at the catalog's clean site, the target against it outside the margin
GROUND = {(8, 10): [(10 * 64 - 70.0, -10 * 64 - 30.0)]}


def test_a_site_beside_stock_land_is_judged_against_a_reference_at_the_clean_site(fake, monkeypatch):
    monkeypatch.setattr(PF, "stock_ground", lambda *a, **k: GROUND)
    real = PF.stage
    monkeypatch.setattr(PF, "stage", lambda prefab, cell, game=None, keep=False:
                        dict(real(prefab, cell, game=game, keep=keep), fingerprint="9" * 64))   # classes differ
    masks = []

    def fp(root, cell, blocks, *, disc=1, mask_tri=None):
        masks.append(mask_tri)
        return GOOD if mask_tri is not None else "9" * 64           # equal once the margin is masked
    monkeypatch.setattr(PF, "fingerprint", fp)
    with pytest.raises(PF.PrefabRefused, match="reference copy"):    # the reference's full hash must be the catalog's
        _place(fake)
    monkeypatch.setattr(PF, "stage", lambda prefab, cell, game=None, keep=False:
                        dict(real(prefab, cell, game=game, keep=keep),
                             fingerprint=GOOD if tuple(cell) == (1, 14) else "9" * 64))
    fake["staged"].clear()
    rep = _place(fake, dry_run=True)
    assert rep["identity"].startswith("nav margin") and fake["staged"] == [(10, 9), (1, 14)]
    assert sum(m is not None for m in masks) >= 2                   # target and reference, the same mask


def test_a_difference_outside_the_margin_refuses_and_so_does_unsettled_margin_sea(fake, monkeypatch):
    monkeypatch.setattr(PF, "stock_ground", lambda *a, **k: GROUND)
    real = PF.stage
    monkeypatch.setattr(PF, "stage", lambda prefab, cell, game=None, keep=False:
                        dict(real(prefab, cell, game=game, keep=keep)))
    calls = []

    def fp(root, cell, blocks, *, disc=1, mask_tri=None):
        calls.append(tuple(cell))
        return GOOD if tuple(cell) == (1, 14) else "7" * 64          # the target differs even masked
    monkeypatch.setattr(PF, "fingerprint", fp)
    with pytest.raises(PF.PrefabRefused, match="OUTSIDE the nav margin"):
        _place(fake)
    monkeypatch.setattr(PF, "fingerprint", lambda root, cell, blocks, **kw: GOOD)
    monkeypatch.setattr(PF, "stage", lambda prefab, cell, game=None, keep=False:
                        dict(real(prefab, cell, game=game, keep=keep), nav={53: 2}))
    with pytest.raises(PF.PrefabRefused, match="would still re-class") as e:
        _place(fake)
    assert e.value.where == [(8, 10)] and not fake["composed"]


# ---- after the write
def test_a_broken_identity_after_the_write_is_reported_loudly(fake, monkeypatch):
    monkeypatch.setattr(PF, "fingerprint", lambda root, cell, blocks, **kw: "0" * 64 if "Target" in str(root) else GOOD)
    with pytest.raises(PF.PrefabRefused, match="after the write"):
        _place(fake)


def test_unsettled_navigation_after_the_write_refuses(fake, monkeypatch):
    monkeypatch.setattr(PF, "nav_settled", lambda folder, *a, **k: {53: 3} if "Target" in str(folder) else {})
    with pytest.raises(PF.PrefabRefused, match="re-class its sea there"):
        _place(fake)


def test_the_disc_4_copy_must_be_the_staged_land_and_settled(fake, monkeypatch):
    """Deep dive C14: placement writes disc 4 too (the auto-mirror), so its copy is fingerprinted and nav-checked."""
    seen = []

    def fp(root, cell, blocks, *, disc=1, **kw):
        seen.append(disc)
        return GOOD if disc == 1 else "4" * 64
    monkeypatch.setattr(PF, "fingerprint", fp)
    with pytest.raises(PF.PrefabRefused, match="DISC-4 copy"):
        _place(fake)
    seen.clear()
    assert _place(fake, skip_mirror=True)["written"] == GOOD and 4 not in seen     # no mirror, nothing to check
    monkeypatch.setattr(PF, "fingerprint", lambda root, cell, blocks, **kw: GOOD)
    monkeypatch.setattr(PF, "nav_settled", lambda folder, *a, disc=1, **k: {55: 1} if disc == 4 else {})
    with pytest.raises(PF.PrefabRefused, match="navigation unsettled"):
        _place(fake)


def test_off_the_map_rows_and_an_unfingerprinted_prefab_refuse(fake, tmp_path):
    with pytest.raises(PF.PrefabRefused, match="off the map"):
        _place(fake, cell=(10, 19))
    bare = _catalog(tmp_path, _entry(_ISL, name="bare"))
    with pytest.raises(PF.PrefabRefused, match="no fingerprint"):
        PF.place("bare", (10, 9), "Target", catalog=bare, stack=())
    assert not fake["composed"]


# ---------------------------------------------------------------- install-gated: the shipped fingerprints are true
def _install():
    from ff9mapkit import config
    try:
        game = config.find_game_path(None)
        if (game / "StreamingAssets").is_dir():
            return game
        why = "no StreamingAssets under the resolved FF9 install"
    except Exception as e:                                   # noqa: BLE001 -- any resolution failure is a skip
        why = f"the FF9 install did not resolve ({type(e).__name__}: {e})"
    warnings.warn("THE PREFAB CATALOG WENT UNVERIFIED in this run: " + why + ". This is the WORKTREE SKIP TRAP -- "
                  "re-run where the install resolves.", UserWarning)
    pytest.skip(why)


def test_the_nav_margin_finds_the_stock_land_that_re_classes_the_sea():
    """Measured 2026-11-08: anchored at (0,12) the desert-peak isle's corner sea re-classed beside (22,13)/(22,14);
    at the seam anchor (23,5) nothing is near and the staged land matched the catalog in full."""
    _install()
    p = PF.get("desert-peak-isle")
    assert PF.stock_land_near(p, (0, 12)) == {(22, 13), (22, 14)}
    assert PF.stock_land_near(p, (23, 5)) == set()


def test_a_carry_unit_prefab_stages_to_its_catalog_fingerprint():
    _install()
    p = PF.get("terminus-pair")
    st = PF.stage(p, (1, 2))
    assert st["fingerprint"] == p["fingerprint"] and st["nav"] == {}


def test_the_meadow_prefab_places_across_the_seam_beside_stock_land(tmp_path):
    """Anchored at (0,16): across x = 0 AND beside the stock land of (22,14)/(22,15) -- the nav-margin tier."""
    _install()
    rep = PF.place("meadow-grove-isle", (0, 16), str(tmp_path / "T"), stack=(), dry_run=True, log=lambda *a: None)
    assert rep["identity"].startswith("nav margin")


def test_the_desert_peak_prefab_places_for_real_far_from_where_it_was_fingerprinted(tmp_path):
    """Fingerprinted at (1,14); placed on (21,1), the other side of the map, and its disc-1 bytes are the staged
    land; a second placement on the same block refuses over the first."""
    _install()
    rep = PF.place("desert-peak-isle", (21, 1), str(tmp_path / "Target"), stack=(), skip_mirror=True,
                   log=lambda *a: None)
    assert rep["staged"] == rep["written"]
    with pytest.raises(PF.PrefabRefused, match="already holds land"):
        PF.place("desert-peak-isle", (21, 1), str(tmp_path / "Target"), stack=(), dry_run=True, log=lambda *a: None)


def test_a_coast_nav_regression_is_refused_not_placed(tmp_path, monkeypatch):
    """THE CHECK CAN FAIL (the review's sabotage): widen the stamp's reach -- standing in for any regression in
    coastnav.py -- and a clean-site placement must refuse, because the sea's classes are part of the identity."""
    _install()
    from ff9mapkit.world import coastnav as CN
    monkeypatch.setattr(CN, "FRINGE_R", 30.0)
    monkeypatch.setattr(CN, "BELT_R", 9.0)
    with pytest.raises(PF.PrefabRefused, match="regression"):
        PF.place("desert-peak-isle", (0, 5), str(tmp_path / "T"), stack=(), dry_run=True, log=lambda *a: None)


# ---------------------------------------------------------------- the verb
def test_the_verb_lists_the_catalog_and_writes_a_placed_recipe(tmp_path, capsys):
    from ff9mapkit import cli
    from ff9mapkit.world import recipe as R
    assert cli.main(["world-prefab", "--list"]) == 0
    out = capsys.readouterr().out
    assert "desert-peak-isle" in out and "candidate" in out
    path = tmp_path / "placed.toml"
    assert cli.main(["world-prefab", "desert-peak-isle", "--cell", "21,1", "--recipe-out", str(path)]) == 0
    rows = R.loads(path.read_text(encoding="utf-8"))
    assert [r["table"] for r in rows] == ["island", "mountain"]
    assert rows[0]["center"] == [64.0 * 21 + 32.0, -64.0 * 2 + 32.0] and rows[0]["prefab_frame"] is True


def test_a_draft_defers_its_disc_4_copy_to_promote(fake, monkeypatch):
    """Measured on a real draft: a draft gets no disc-4 copy (the auto-mirror needs the install's bundles; Promote
    makes it in the live folder), so the disc-4 identity check refused every Accept from the World tab. A draft target
    defers it, and says so; a live target still checks it."""
    from ff9mapkit.world import draft as D
    monkeypatch.setattr(PF, "fingerprint", lambda root, cell, blocks, *, disc=1, **kw: GOOD if disc == 1 else "")
    with pytest.raises(PF.PrefabRefused, match="DISC-4 copy"):
        _place(fake)                                                  # a live folder: still checked
    monkeypatch.setattr(D, "stands_in_for", lambda folder: "FF9CustomMap-world")
    rep = _place(fake)
    assert rep["written"] == GOOD and rep["written_disc4"].startswith("deferred")
