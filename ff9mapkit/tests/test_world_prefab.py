"""Landmass PREFABS (rung P1, studies/overworld-editor/PREFABS.md): the catalog, the placement, the identity.

``world-prefab NAME --cell BX,BY --mod-folder F`` stamps a frozen island + relief composition on an anchor block. It
refuses -- before writing anything -- unless the window is clear (the target and the FolderNames stack) and the
prefab composed in a staging folder is the land its catalog fingerprint names. Hermetic tests cover the catalog
rules, the frame arithmetic, the fingerprint's own invariances and every refusal; the install-gated ones re-take the
shipped fingerprints and place a prefab for real (the fingerprint IS the regression oracle for the verbs it rides).
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


# ---------------------------------------------------------------- the catalog
def test_the_shipped_catalog_is_well_formed_and_fingerprinted():
    cat = PF.load_catalog()
    assert {p["name"] for p in cat} >= {"desert-peak-isle", "meadow-grove-isle"}
    for p in cat:
        assert p["status"] in PF.STATUSES
        assert len(p["fingerprint"]) == 64 and p["footprint"], p["name"]
        assert all(r["table"] in PF.PREFAB_TABLES for r in p["rows"])
        assert p["rows"][0]["table"] in PF.BASE_TABLES


@pytest.mark.parametrize("rows, why", [
    ('[[prefab.rows]]\ntable = "island"\ncenter = [32.0, 32.0]\n', "needs its seed"),
    ('[[prefab.rows]]\ntable = "forest"\ncenter = [1.0, 1.0]\n', "first row is the"),
    (_ISL + '[[prefab.rows]]\ntable = "river"\ncenter = [1.0, 1.0]\n', "not been measured"),
    (_ISL + '[[prefab.rows]]\ntable = "forest"\ncenter = [1.0, 1.0]\nprefab_frame = true\n', "set by placement"),
    (_ISL + '[[prefab.rows]]\ntable = "forest"\nnear = [1.0, 1.0]\ncenter = [1.0, 1.0]\n', "set by placement"),
    (_ISL + '[[prefab.rows]]\ntable = "hill"\n', "exact placement"),
    (_ISL + _ISL, "one base"),
])
def test_the_catalog_refuses_what_a_prefab_cannot_hold(tmp_path, rows, why):
    with pytest.raises(ValueError, match=why):
        PF.load_catalog(_catalog(tmp_path, _entry(rows)))


def test_the_catalog_refuses_a_bad_status_and_a_duplicate_name(tmp_path):
    with pytest.raises(ValueError, match="status"):
        PF.load_catalog(_catalog(tmp_path, _entry(_ISL, status="walked")))
    with pytest.raises(ValueError, match="unique name"):
        PF.load_catalog(_catalog(tmp_path, _entry(_ISL) + "\n" + _entry(_ISL)))


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


_TP = '[[prefab.rows]]\ntable = "transplant"\ncell = [1, 0]\ndonor = [9, 5]\nsize = [2, 3]\nrot = 90\n'
_FOREST = '[[prefab.rows]]\ntable = "forest"\ncenter = [52.0, 20.0]\n'


def test_a_transplant_base_is_placed_by_cell_and_carries_its_navigation(tmp_path):
    p = PF.load_catalog(_catalog(tmp_path, _entry(_TP + _FOREST)))[0]
    rows = PF.expand(p, (23, 4))
    assert rows[0]["cell"] == [0, 4] and "prefab_frame" not in rows[0]          # the anchor's +1 column wraps
    assert rows[1]["center"] == [64.0 * 23 + 52.0, -64.0 * 5 + 20.0]
    assert not PF.stamped_nav(p) and PF.stamped_nav({"rows": [dict(ISLAND)]})
    assert not PF.stamped_nav({"rows": [dict(ISLAND, coastnav=False)]})
    with pytest.raises(ValueError, match="names cell"):
        PF.load_catalog(_catalog(tmp_path, _entry('[[prefab.rows]]\ntable = "transplant"\ndonor = [9, 5]\n')))
    with pytest.raises(ValueError, match="one base"):
        PF.load_catalog(_catalog(tmp_path, _entry(_TP + _ISL)))


def test_block_offsets_fold_across_the_x_seam():
    assert PF.rel_block((0, 5), (23, 4)) == (1, 1)
    assert PF.rel_block((23, 5), (0, 4)) == (-1, 1)
    assert PF.label_of((1, 1), (23, 4)) == (0, 5)
    assert PF.label_of((-1, 0), (0, 4)) == (23, 4)


def test_read_windows_follow_each_verb_s_reach():
    rows = PF.expand({"name": "x", "rows": [dict(ISLAND), {"table": "hill", "center": [32.0, 32.0], "radius": 100.0},
                                            {"table": "forest", "center": [32.0, 32.0], "reach": 10.0}]}, (10, 9))
    win = PF.read_windows(rows)
    assert {(10, 9)} <= win and (8, 9) in win and (12, 11) in win      # the hill: max(96, 110) = 110u
    assert (7, 9) not in win
    assert PF.read_windows(PF.expand({"name": "x", "rows": [dict(ISLAND), {"table": "forest",
                                      "center": [32.0, 32.0]}]}, (5, 0))) >= {(5, 0), (4, 1)}
    assert all(0 <= by < M.GRID_ROWS for _bx, by in win)


# ---------------------------------------------------------------- the fingerprint
def _mesh(path, tris, *, nrm=(0.0, 1.0, 0.0), uv=(0.25, 0.5), tan_x=12.0, mask_nav=False):
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
    return PF.mesh_digest(path, mask_nav=mask_nav)


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


def test_the_nav_mask_blanks_only_the_water_class(tmp_path):
    """THE NAV MARGIN: a water vertex's class (topograph 53-57 in tangent.x bits 2-7) depends on the site, so the
    masked digest ignores it -- and nothing else: the unmasked digest sees it, and a non-water class still counts."""
    def sea(n, t, **kw):
        return _mesh(tmp_path / f"{n}.ff9mesh", [T1, T2], tan_x=t, **kw)
    assert sea("a", 57 << 2, mask_nav=True) == sea("b", 53 << 2, mask_nav=True)
    assert sea("c", 57 << 2) != sea("d", 53 << 2)
    assert sea("e", (57 << 2) | 1, mask_nav=True) != sea("f", (57 << 2) | 2, mask_nav=True)   # other bits kept
    assert sea("g", 17 << 2, mask_nav=True) != sea("h", 16 << 2, mask_nav=True)               # ground classes kept


def _put(root, label, part="Terrain.ff9mesh", data=b"x"):
    d = root / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / f"r{label[1]}"
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


@pytest.fixture
def fake(tmp_path, monkeypatch):
    """A one-prefab catalog, a tmp 'install' and a recorder in place of the compose."""
    from ff9mapkit import config
    game = tmp_path / "game"
    game.mkdir()
    monkeypatch.setattr(config, "find_game_path", lambda g=None: game)
    cat = _catalog(tmp_path, _entry(_ISL + '[[prefab.rows]]\ntable = "forest"\ncenter = [52.0, 20.0]\n',
                                    fingerprint="f" * 64, footprint=FOOT))
    composed = []
    monkeypatch.setattr(PF, "_compose", lambda folder, rows, **kw: composed.append((str(folder), rows)))
    monkeypatch.setattr(PF, "stage", lambda prefab, cell, game=None: {
        "fingerprint": "f" * 64, "footprint": sorted(tuple(b) for b in FOOT),
        "blocks": sorted(PF.label_of(b, cell) for b in FOOT), "nav": {}})
    monkeypatch.setattr(PF, "nav_settled", lambda *a, **k: {})
    monkeypatch.setattr(PF, "stock_land_near", lambda *a, **k: set())
    return {"game": game, "cat": cat, "composed": composed}


def _place(fake, cell=(10, 9), **kw):
    kw.setdefault("stack", ())
    return PF.place("x", cell, "Target", catalog=fake["cat"], log=lambda *a: None, **kw)


def test_a_clear_window_places_and_fingerprints_what_it_wrote(fake, monkeypatch):
    monkeypatch.setattr(PF, "fingerprint", lambda root, cell, blocks, **kw: "f" * 64)
    rep = _place(fake)
    assert rep["written"] == "f" * 64 and len(fake["composed"]) == 1
    assert fake["composed"][0][1][0]["center"] == [64.0 * 10 + 32.0, -64.0 * 10 + 32.0]


def test_a_dry_run_writes_nothing(fake):
    assert _place(fake, dry_run=True)["written"] is None and not fake["composed"]


def test_a_busy_target_window_refuses(fake):
    _put(fake["game"] / "Target", (12, 9))                          # in the forest's read window, off the footprint
    with pytest.raises(PF.PrefabRefused, match="already holds land") as e:
        _place(fake)
    assert e.value.where == [(12, 9)] and not fake["composed"]


def test_another_folder_in_the_stack_refuses_only_on_the_footprint(fake):
    other = fake["game"] / "Other"
    _put(other, (12, 9))                                            # read window only: another folder is not read
    _place(fake, stack=(other,), dry_run=True)
    _put(other, (11, 10))
    with pytest.raises(PF.PrefabRefused, match="Other") as e:
        _place(fake, stack=(other,))
    assert e.value.where == [(11, 10)] and not fake["composed"]


def test_a_broken_identity_refuses_before_the_write(fake, monkeypatch):
    monkeypatch.setattr(PF, "stage", lambda prefab, cell, game=None: {
        "fingerprint": "0" * 64, "footprint": sorted(tuple(b) for b in FOOT), "blocks": [], "nav": {}})
    with pytest.raises(PF.PrefabRefused, match="regression to find"):
        _place(fake)
    assert not fake["composed"]


def test_a_staged_mismatch_beside_stock_land_names_the_nav_margin(fake, monkeypatch):
    monkeypatch.setattr(PF, "stage", lambda prefab, cell, game=None: {
        "fingerprint": "0" * 64, "footprint": sorted(tuple(b) for b in FOOT), "blocks": [], "nav": {}})
    monkeypatch.setattr(PF, "stock_land_near", lambda *a, **k: {(8, 10)})
    with pytest.raises(PF.PrefabRefused, match="NAV MARGIN") as e:
        _place(fake)
    assert e.value.where == [(8, 10)] and not fake["composed"]


def test_unsettled_navigation_refuses_before_and_after_the_write(fake, monkeypatch):
    monkeypatch.setattr(PF, "stage", lambda prefab, cell, game=None: {
        "fingerprint": "f" * 64, "footprint": sorted(tuple(b) for b in FOOT),
        "blocks": sorted(PF.label_of(b, cell) for b in FOOT), "nav": {53: 27}})
    with pytest.raises(PF.PrefabRefused, match="not settled"):
        _place(fake)
    assert not fake["composed"]
    monkeypatch.setattr(PF, "stage", lambda prefab, cell, game=None: {
        "fingerprint": "f" * 64, "footprint": sorted(tuple(b) for b in FOOT),
        "blocks": sorted(PF.label_of(b, cell) for b in FOOT), "nav": {}})
    monkeypatch.setattr(PF, "fingerprint", lambda root, cell, blocks, **kw: "f" * 64)
    monkeypatch.setattr(PF, "nav_settled", lambda *a, **k: {53: 3})
    with pytest.raises(PF.PrefabRefused, match="re-class its sea there"):
        _place(fake)


def test_the_disc_4_copy_must_name_the_same_land(fake, monkeypatch):
    """Deep dive C14: placement writes disc 4 too (the auto-mirror), so its copy is fingerprinted as well."""
    seen = []

    def fp(root, cell, blocks, *, disc=1, **kw):
        seen.append(disc)
        return "f" * 64 if disc == 1 else "4" * 64
    monkeypatch.setattr(PF, "fingerprint", fp)
    with pytest.raises(PF.PrefabRefused, match="DISC-4 copy"):
        _place(fake)
    assert seen == [1, 4]
    seen.clear()
    assert _place(fake, skip_mirror=True)["written"] == "f" * 64 and seen == [1]   # no mirror, nothing to check


def test_kit_land_in_the_footprint_ring_refuses(fake, tmp_path):
    """The nav stamp classes the prefab's sea against ground 16u past its footprint, so the target's own land in the
    ring blocks is in the way even when no relief row reads there (an island-only prefab)."""
    bare = _catalog(tmp_path, _entry(_ISL, name="isle", fingerprint="f" * 64, footprint=FOOT))
    _put(fake["game"] / "Target", (12, 11))
    with pytest.raises(PF.PrefabRefused, match="already holds land") as e:
        PF.place("isle", (10, 9), "Target", catalog=bare, stack=(), log=lambda *a: None)
    assert e.value.where == [(12, 11)]


def test_a_broken_identity_after_the_write_is_reported_loudly(fake, monkeypatch):
    monkeypatch.setattr(PF, "fingerprint", lambda root, cell, blocks, **kw: "0" * 64)
    with pytest.raises(PF.PrefabRefused, match="after the write"):
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


def test_the_nav_margin_diagnosis_sees_the_stock_land_that_changed_the_sea():
    """Measured 2026-11-08: anchored at (0,12) the desert-peak isle's corner sea re-classed beside (22,13)/(22,14);
    at the seam anchor (23,5) nothing is near and the staged land matched the catalog."""
    _install()
    p = PF.get("desert-peak-isle")
    assert PF.stock_land_near(p, (0, 12)) == {(22, 13), (22, 14)}
    assert PF.stock_land_near(p, (23, 5)) == set()


def test_a_carry_unit_prefab_stages_to_its_catalog_fingerprint():
    _install()
    p = PF.get("terminus-pair")
    st = PF.stage(p, (1, 2))
    assert st["fingerprint"] == p["fingerprint"] and st["nav"] == {}


def test_the_meadow_prefab_stages_to_its_catalog_fingerprint():
    _install()
    p = PF.get("meadow-grove-isle")
    st = PF.stage(p, (0, 16))                     # across the x seam AND beside stock land (the nav margin)
    assert st["fingerprint"] == p["fingerprint"] and st["footprint"] == sorted(tuple(b) for b in p["footprint"])
    assert st["nav"] == {}


def test_the_desert_peak_prefab_places_for_real_far_from_where_it_was_fingerprinted(tmp_path):
    """Fingerprinted at (1,14); placed on (21,1), the other side of the map and the top row band: the staged and the
    written land are the catalog's, and a second placement on the same block refuses over the first."""
    _install()
    rep = PF.place("desert-peak-isle", (21, 1), str(tmp_path / "Target"), stack=(), skip_mirror=True,
                   log=lambda *a: None)
    assert rep["staged"] == rep["written"] == PF.get("desert-peak-isle")["fingerprint"]
    with pytest.raises(PF.PrefabRefused, match="already holds land"):
        PF.place("desert-peak-isle", (21, 1), str(tmp_path / "Target"), stack=(), dry_run=True, log=lambda *a: None)


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
