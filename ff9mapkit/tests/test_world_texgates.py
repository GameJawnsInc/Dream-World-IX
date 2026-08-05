"""THE TEXTURE + SEA GATES (``ff9mapkit.world.texgates``) -- the Rung-F UV/relief arc's acceptance
criteria (``studies/overworld-topography``, 8 in-game rounds, folded back through
``studies/overworld-topography/composite_gates.py`` 2026-07-25), productized as WARN-default gates on
the two kit mint/carry chokepoints.

Fully hermetic -- zero Square-Enix bytes, zero install reads. Every fixture is built from the repo's
own :mod:`ff9mapkit.world.grassland` constants or minted by :func:`~ff9mapkit.world.island.build_landmass`.

Coverage:
  * a LAWFUL mint passes all four gates, and THE ONE-WINDOW GATE actually JUDGES it (not vacuously
    skipped) -- the failure this file exists to prevent is a gate that is green because it looked at
    nothing
  * a synthetic CONSTANT-UV mutation (round 1's flat-sheet stain, the exact defect class) fails
    zero-uv-area, one-window AND family-rect
  * a synthetic OUT-OF-RECT UV mutation fails family-rect only (a transparent atlas gutter = white)
  * the sea gate's three predicates each fail on their own synthetic defect, including the DEGENERATE
    SEA4 STUB the L6 "uniform full plane on every block" law replaced
  * the WARN / ``enforce`` / ``allow`` composition matches ``wang_carry_gate``'s exactly
  * the one-window gate REFUSES to judge without a ``quad_ori`` field (the stock calibration: a blind
    lattice search reproduces only 3.2%-18.5% of REAL stock ground)
  * the wiring: ``transplant()``/``transplant_region()`` report the gates, the kwargs thread, the CLI
    flags parse and thread, and ``verify_landmass`` reports them + honours ``enforce_texgates``
"""
from __future__ import annotations

import copy

import pytest

from ff9mapkit.world import grassland as GL, island as I, mesh as M, texgates as TG, transplant as TR
from ff9mapkit.world.extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN

NRM = (0.0, 1.0, 0.0)


# ---- fixtures ------------------------------------------------------------------------------------
def _mesh(tris, *, name="Block[0][0] Terrain", x=0, y=0, disc=1):
    """A BlockMesh from ``[(corners[(x,y,z,u,v)]x3, idall), ...]`` in BLOCK-LOCAL coords."""
    pos, nrm, uv, tan, flat, t_out = [], [], [], [], [], []
    for corners, idall in tris:
        base = len(pos)
        for c in corners:
            pos.append([float(c[0]), float(c[1]), float(c[2])])
            nrm.append(list(NRM))
            uv.append([float(c[3]), float(c[4])])
            tan.append([float(idall), 0.0, 0.0, 1.0])
            flat.append(len(pos) - 1)
        t_out.append([base, base + 1, base + 2])
    return BlockMesh(name=name, disc=disc, x=x, y=y, lod="0_1", vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=t_out, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


def _lawful_cell(cell, *, fam="grass", quad=(0, 0), ori=0, y=3.2):
    """Two UP-FACING tris covering the 4u ``cell``, UV'd through the family's OWN
    :func:`~ff9mapkit.world.grassland.ground_uv` window -- lawful by construction, in block (0,0)
    (world == local there, so block-local coords ARE the world coords the gates read)."""
    i, j = cell
    x0, z0 = 4.0 * i, 4.0 * j
    idall = float(encode_id(topograph=GL.GROUNDS[fam]["topo"]))
    pts = {(x0, z0), (x0 + 4.0, z0), (x0 + 4.0, z0 + 4.0), (x0, z0 + 4.0)}

    def c(px, pz):
        u, v = GL.ground_uv(px, pz, cell, quad, ori, fam)
        return (px, y, pz, u, v)

    assert len(pts) == 4
    a, b = c(x0, z0 + 4.0), c(x0 + 4.0, z0 + 4.0)
    d, e = c(x0 + 4.0, z0), c(x0, z0)
    return [((a, b, e), idall), ((b, d, e), idall)]


def _lawful_block(*, fam="grass", n=4):
    """An ``n`` x ``n`` patch of lawful cells at block (0,0) + its own ``{cell: (quad, ori)}``
    field, exactly as a generator would hand it over."""
    cells = [(i, -1 - j) for i in range(n) for j in range(n)]
    quad_ori = {c: (((c[0] + c[1]) % 2, (c[0] * 3 + c[1]) % 2), GL.ORIS[(c[0] + 2 * c[1]) % 4])
                for c in cells}
    tris = []
    for c in cells:
        q, o = quad_ori[c]
        tris += _lawful_cell(c, fam=fam, quad=q, ori=o)
    return {(0, 0): [("Terrain", _mesh(tris))]}, {(0, 0)}, quad_ori


def _mutate_uv(cell_meshes, fn):
    """Deep-copy ``cell_meshes`` and rewrite every Terrain UV through ``fn(u, v) -> (u, v)``."""
    out = copy.deepcopy(cell_meshes)
    for parts in out.values():
        for pn, bm in parts:
            if pn.lower() == "terrain":
                for k in range(len(bm.chan_arrays[CH_UV])):
                    u, v = bm.chan_arrays[CH_UV][k]
                    bm.chan_arrays[CH_UV][k] = list(fn(u, v))
    return out


def _sea_plane_mesh(blk, *, seg=4, y=0.0, part="Sea4"):
    """A full-block water plane at ``blk`` -- ``seg``x``seg`` quads, block-local."""
    bx, by = blk
    step = 64.0 / seg
    idall = float(encode_id(topograph=57))
    tris = []
    for i in range(seg):
        for j in range(seg):
            x0, x1 = i * step, (i + 1) * step
            z0, z1 = -(j + 1) * step, -j * step
            a = (x0, y, z1, 0.5, 0.5)
            b = (x1, y, z1, 0.5, 0.5)
            c = (x1, y, z0, 0.5, 0.5)
            d = (x0, y, z0, 0.5, 0.5)
            tris += [((a, b, d), idall), ((b, c, d), idall)]
    return _mesh(tris, name=f"Block[{bx}][{by}] {part}", x=bx, y=by)


def _grid_sea_plane():
    """The 4u-lattice full-block Sea4 plane ``verify_landmass``'s placement census expects (the same
    shape as ``test_world_island._grid_plane``, minted locally so this file stays standalone)."""
    return _sea_plane_mesh((12, 0), seg=16)


def _stub_sea_mesh(blk, *, part="Sea4"):
    """The DEGENERATE one-blob Sea4 stub the L6 law replaced: a single tiny tri."""
    bx, by = blk
    idall = float(encode_id(topograph=57))
    return _mesh([(((0.0, 0.0, 0.0, 0.5, 0.5), (1.0, 0.0, 0.0, 0.5, 0.5),
                    (0.0, 0.0, -1.0, 0.5, 0.5)), idall)],
                 name=f"Block[{bx}][{by}] {part}", x=bx, y=by)


# ================================================================================================ the lawful baseline
def test_lawful_synthetic_patch_passes_every_gate_and_one_window_actually_judges():
    cm, region, quad_ori = _lawful_block()
    gates = {g["gate"]: g for g in TG.texture_sea_gates(cm, region, quad_ori=quad_ori, sea=False)}
    assert set(gates) == {"tex-zero-uv", "tex-one-window", "tex-family-rect"}
    assert all(g["ok"] and not g["warn"] for g in gates.values())
    ow = gates["tex-one-window"]
    assert ow["skipped"] is False and ow["checked"] == 32 and ow["n_multi_window"] == 0
    assert gates["tex-family-rect"]["checked_by_family"] == {"grass": 32}


@pytest.mark.parametrize("fam", ["grass", "desert", "dunes"])
def test_every_ground_family_is_lawful_in_its_own_translated_rect(fam):
    """THE TRANSLATION LAW: each family's mains live in their OWN rect, and the gates judge each tri
    against ITS family -- not against grass."""
    cm, region, quad_ori = _lawful_block(fam=fam, n=3)
    gates = {g["gate"]: g for g in TG.texture_sea_gates(cm, region, quad_ori=quad_ori, sea=False)}
    assert all(g["ok"] for g in gates.values())
    assert gates["tex-family-rect"]["checked_by_family"] == {fam: 18}
    assert gates["tex-one-window"]["checked"] == 18


def test_a_real_build_landmass_mint_passes_all_four_gates_through_verify_landmass():
    """The kit's own generator, end to end through the wired chokepoint."""
    built = I.build_landmass(center=(224.0, -96.0), base_radius=20.0, seed=5.0)
    rep = I.verify_landmass(built, sea_plane=_grid_sea_plane())
    assert rep["clean"] is True
    gates = {g["gate"]: g for g in rep["texgates"]}
    assert set(gates) == {"tex-zero-uv", "tex-one-window", "tex-family-rect", "sea-plan"}
    assert all(g["ok"] and not g["warn"] for g in gates.values())
    # NON-VACUOUS: the mint hands over its own minted field, so the law is really judged
    assert gates["tex-one-window"]["skipped"] is False and gates["tex-one-window"]["checked"] > 100
    assert gates["tex-one-window"]["n_multi_window"] == 0


# ================================================================================================ the defect classes
def _MAINS_MID(fam="grass"):
    lo_u, lo_v, hi_u, hi_v = GL.ground_main_region(fam)
    return ((lo_u + hi_u) / 2.0, (lo_v + hi_v) / 2.0)


def test_the_constant_uv_stamp_fails_all_three_texture_gates():
    """ROUND 1's DEFECT, faithfully: ONE constant (uv, topo) for every synthesized vertex -- and the
    constant that shipped was a REAL grass mains uv, so it sits INSIDE the family rect. All three
    gates independently refuse it: the UV triangle has no area, it comes from no window, and the
    zero-area arm of rect membership fires."""
    cm, region, quad_ori = _lawful_block()
    bad = _mutate_uv(cm, lambda u, v: _MAINS_MID())
    gates = {g["gate"]: g for g in TG.texture_sea_gates(bad, region, quad_ori=quad_ori,
                                                        enforce=True, sea=False)}
    z = gates["tex-zero-uv"]
    assert z["ok"] is False and z["n_zero_uv_area"] == 32 and z["n_bit_identical"] == 32
    assert z["zero_uv_area_frac"] == 1.0
    ow = gates["tex-one-window"]
    assert ow["ok"] is False and ow["checked"] == 32 and ow["multi_window_frac"] == 1.0
    fr = gates["tex-family-rect"]
    assert fr["ok"] is False and fr["zero_area_by_family"] == {"grass": 32}
    assert fr["out_of_region_by_family"] == {}         # membership alone would have been blind


def test_a_constant_uv_OFF_every_rect_is_caught_by_zero_uv_and_reported_as_escaped():
    """THE SELECTOR'S DOCUMENTED BLIND SPOT: a stamp that lands off every mains rect also leaves the
    UV-based mains selector, so gates 2/3 stop seeing it. Gate 1 is topo-agnostic and still refuses,
    and the escape is reported. (Selecting by topograph alone was measured and REJECTED: 6.2% of real
    stock ground wears an uncatalogued rect -- see mains_records' docstring.)"""
    cm, region, quad_ori = _lawful_block()
    bad = _mutate_uv(cm, lambda u, v: (0.5, 0.5))
    gates = {g["gate"]: g for g in TG.texture_sea_gates(bad, region, quad_ori=quad_ori,
                                                        enforce=True, sea=False)}
    assert gates["tex-zero-uv"]["ok"] is False and gates["tex-zero-uv"]["n_bit_identical"] == 32
    fr = gates["tex-family-rect"]
    assert fr["checked_by_family"] == {} and fr["escaped_every_mains_rect_ADVISORY"] == 32
    assert gates["tex-one-window"]["checked"] == 0
    assert len(TG.escaped_records(TG.terrain_records(bad, region))) == 32


def test_out_of_rect_uvs_fail_family_rect_but_not_zero_uv():
    """A mis-BASED window on ONE corner: the tri still claims the rect (so the selector keeps it) but
    a corner has walked into a transparent atlas gutter -- white in game."""
    cm, region, quad_ori = _lawful_block()
    bad = copy.deepcopy(cm)
    for parts in bad.values():
        for pn, bm in parts:
            if pn.lower() == "terrain":
                for k in range(0, len(bm.chan_arrays[CH_UV]), 3):     # one corner of every tri
                    bm.chan_arrays[CH_UV][k][0] += 0.30
    gates = {g["gate"]: g for g in TG.texture_sea_gates(bad, region, quad_ori=quad_ori,
                                                        enforce=True, sea=False)}
    assert gates["tex-zero-uv"]["ok"] is True          # areas stay non-zero
    fr = gates["tex-family-rect"]
    assert fr["ok"] is False and fr["out_of_region_by_family"]["grass"] == 32
    assert fr["checked_by_family"] == {"grass": 32}


def test_mis_scaled_window_fails_one_window_while_staying_in_the_rect():
    """A window scaled about the rect centre stays inside the rect and keeps a non-zero area, so only
    THE ONE-WINDOW LAW sees it -- the positive form of the law earning its place."""
    lo_u, lo_v, hi_u, hi_v = GL.ground_main_region("grass")
    cu, cv = (lo_u + hi_u) / 2.0, (lo_v + hi_v) / 2.0
    cm, region, quad_ori = _lawful_block()
    bad = _mutate_uv(cm, lambda u, v: (cu + (u - cu) * 0.5, cv + (v - cv) * 0.5))
    gates = {g["gate"]: g for g in TG.texture_sea_gates(bad, region, quad_ori=quad_ori,
                                                        enforce=True, sea=False)}
    assert gates["tex-zero-uv"]["ok"] is True and gates["tex-family-rect"]["ok"] is True
    assert gates["tex-one-window"]["ok"] is False and gates["tex-one-window"]["multi_window_frac"] == 1.0


# ================================================================================================ the one-window scoping law
def test_one_window_refuses_to_judge_without_a_quad_ori_field():
    """THE CALIBRATION (texgates docstring): a blind lattice search reproduces only 3.2%-18.5% of REAL
    stock ground, because lawful stock slides free fractional windows. So with no field supplied the
    gate reports ``skipped`` and passes -- even on content it would otherwise flunk."""
    cm, region, _qo = _lawful_block()
    bad = _mutate_uv(cm, lambda u, v: _MAINS_MID())
    g = TG.one_window_gate(bad, region, enforce=True)          # no quad_ori
    assert g["skipped"] is True and g["ok"] is True and g["warn"] is False
    assert g["checked"] == 0 and g["mains_tris"] == 32


def test_one_window_reports_cells_outside_the_supplied_field_without_gating_them():
    cm, region, quad_ori = _lawful_block()
    partial = {c: qo for c, qo in list(quad_ori.items())[:4]}
    g = TG.one_window_gate(cm, region, quad_ori=partial, enforce=True)
    assert g["ok"] is True and g["checked"] == 8 and g["out_of_field"] == 24


def test_the_mains_selector_ignores_non_ground_vocabulary():
    """Rock/cliff, the meadow (D) stamp set and the STRIPS transition band live in other atlas rects
    and belong to the ORPHAN-DECAL gate, not this module -- they must not be judged (or counted)
    here."""
    idall = float(encode_id(topograph=GL.GROUNDS["grass"]["topo"]))
    rock_uv = (I.ROCK_U[0] + 0.01, min(I.ROCK_V) + 0.005)
    strip_uv = (GL.STRIP_U[0] + 0.01, GL.STRIPS_V[0][0] + 0.005)
    tris = []
    for k, uvv in enumerate((rock_uv, strip_uv)):
        x0 = 40.0 + 4.0 * k
        tris.append((((x0, 3.0, -4.0, *uvv), (x0 + 4.0, 3.0, -4.0, *uvv),
                      (x0, 3.0, -8.0, *uvv)), idall))
    cm = {(0, 0): [("Terrain", _mesh(tris))]}
    recs = TG.terrain_records(cm, {(0, 0)})
    assert len(recs) == 2 and TG.mains_records(recs) == []
    fr = TG.family_rect_gate(cm, {(0, 0)}, enforce=True)
    assert fr["ok"] is True and fr["checked_by_family"] == {}


# ================================================================================================ the sea gate's 3 predicates
def test_sea_A_fully_submerged_land_tri_fails_but_shoreline_taper_to_zero_does_not():
    """THE CALIBRATION TRAP the arc named: real shorelines lawfully taper to EXACTLY y=0, so the
    per-vertex reading is a diagnostic only; the gating predicate is all-three-verts-submerged."""
    cm, region, _qo = _lawful_block()
    taper = copy.deepcopy(cm)
    bm = taper[(0, 0)][0][1]
    for k in range(0, len(bm.chan_arrays[CH_POS]), 3):        # one vert of every tri down to 0
        bm.chan_arrays[CH_POS][k][1] = 0.0
    g = TG.sea_plan_gate(taper, region, enforce=True)
    assert g["A_ok"] is True and g["ok"] is True
    assert g["A_per_vertex_at_or_below_0_DIAGNOSTIC"] == 32 and g["A_submerged_tris"] == 0

    sunk = copy.deepcopy(cm)
    bm = sunk[(0, 0)][0][1]
    for k in range(len(bm.chan_arrays[CH_POS])):
        bm.chan_arrays[CH_POS][k][1] = -1.0
    g = TG.sea_plan_gate(sunk, region, enforce=True)
    assert g["A_ok"] is False and g["ok"] is False and g["A_submerged_tris"] == 32


def test_sea_B_degenerate_sea4_stub_beside_a_full_plane_fails_uniformity():
    """L6: a uniform FULL Sea4 plane on EVERY block. The old degenerate one-blob stub reads as an
    infinite adjacent-block plan-area ratio."""
    lawful = {(0, 0): [("Sea4", _sea_plane_mesh((0, 0)))],
              (1, 0): [("Sea4", _sea_plane_mesh((1, 0)))]}
    g = TG.sea_plan_gate(lawful, {(0, 0), (1, 0)}, enforce=True)
    assert g["B_ok"] is True and g["B_pairs"] == 1 and g["B_max_ratio"] == 1.0

    stubbed = {(0, 0): [("Sea4", _sea_plane_mesh((0, 0)))],
               (1, 0): [("Sea4", _stub_sea_mesh((1, 0)))]}
    g = TG.sea_plan_gate(stubbed, {(0, 0), (1, 0)}, enforce=True)
    assert g["B_ok"] is False and g["ok"] is False and g["B_violations"] == 1


def test_sea_C_real_water_over_land_fails_but_the_sea4_underlay_and_placeholders_do_not():
    """Sea4 is the DEEP UNDERLAY -- it lawfully lies under land, so it is excluded; a <=1-tri hidden
    convention placeholder is not water either. Real Sea1 laid over the land cells is a defect."""
    cm, region, _qo = _lawful_block()
    under = copy.deepcopy(cm)
    under[(0, 0)].append(("Sea4", _sea_plane_mesh((0, 0))))
    under[(0, 0)].append(("Sea1", _stub_sea_mesh((0, 0), part="Sea1")))
    g = TG.sea_plan_gate(under, region, enforce=True)
    assert g["C_ok"] is True and g["C_overlap_cells"] == 0 and g["C_placeholders_excluded"] == 1

    over = copy.deepcopy(cm)
    over[(0, 0)].append(("Sea1", _sea_plane_mesh((0, 0), seg=16, part="Sea1")))
    g = TG.sea_plan_gate(over, region, enforce=True)
    assert g["C_ok"] is False and g["ok"] is False and g["C_overlap_frac"] > TG.SEA_OVERLAP_CEILING


# ================================================================================================ WARN / enforce / allow
@pytest.mark.parametrize("gatefn,name", [
    (lambda cm, r, **k: TG.zero_uv_area_gate(cm, r, **k), "tex-zero-uv"),
    (lambda cm, r, **k: TG.family_rect_gate(cm, r, **k), "tex-family-rect"),
])
def test_warn_enforce_allow_composition_matches_wang_carry_gate(gatefn, name):
    cm, region, _qo = _lawful_block()
    bad = _mutate_uv(cm, lambda u, v: _MAINS_MID())
    warn = gatefn(bad, region)
    assert warn["gate"] == name and warn["ok"] is True and warn["warn"] is True
    assert warn["enforced"] is False and warn["detail"] != 0
    enf = gatefn(bad, region, enforce=True)
    assert enf["ok"] is False and enf["warn"] is False and enf["enforced"] is True
    waived = gatefn(bad, region, enforce=True, allow=True)
    assert waived["ok"] is True and waived["warn"] is False
    clean = gatefn(cm, region, enforce=True)
    assert clean["ok"] is True and clean["warn"] is False and clean["detail"] == 0


def test_gates_are_purely_read_only():
    """WARN mode must change ZERO output bytes -- that is what makes wiring it into a shipping carry
    path safe."""
    cm, region, quad_ori = _lawful_block()
    before = copy.deepcopy(cm)
    TG.texture_sea_gates(cm, region, quad_ori=quad_ori, sea=False)
    for blk in cm:
        for (pn, bm), (_pn0, bm0) in zip(cm[blk], before[blk]):
            assert bm.chan_arrays[CH_UV] == bm0.chan_arrays[CH_UV]
            assert bm.chan_arrays[CH_POS] == bm0.chan_arrays[CH_POS]
            assert bm.chan_arrays[CH_TAN] == bm0.chan_arrays[CH_TAN]


def test_only_reported_blocks_are_judged():
    cm, _region, _qo = _lawful_block()
    cm[(1, 0)] = [("Terrain", _mesh(_lawful_cell((16, -1)), name="Block[1][0] Terrain", x=1, y=0))]
    g = TG.zero_uv_area_gate(cm, {(0, 0)})
    assert g["checked"] == 32                      # block (1,0) is context, not ours to report


def test_blanking_stub_tris_below_the_floor_are_not_content():
    idall = float(encode_id(topograph=GL.GROUNDS["grass"]["topo"]))
    y = TG.STUB_Y_FLOOR - 30.0
    stub = [(((0.0, y, 0.0, 0.5, 0.5), (4.0, y, 0.0, 0.5, 0.5), (0.0, y, -4.0, 0.5, 0.5)), idall)]
    cm = {(0, 0): [("Terrain", _mesh(stub))]}
    assert TG.terrain_records(cm, {(0, 0)}) == []
    assert TG.zero_uv_area_gate(cm, {(0, 0)}, enforce=True)["ok"] is True


# ================================================================================================ transplant() wiring (offline)
def _fake_world(blocks):
    def fake(bx, by, part, **_k):
        return [list(t) for t in blocks.get((bx, by, part), [])]
    return fake


def _v(x, y, z, uv=(0.5, 0.5), idall=12800.0):
    return ((float(x), float(y), float(z)), NRM, tuple(uv), (float(idall), 0.0, 0.0, 1.0))


def _quad_tris(x0, x1, z0, z1, *, y=0.0, idall=12800.0, uv=(0.5, 0.5)):
    a, b = _v(x0, y, z1, uv, idall), _v(x1, y, z1, uv, idall)
    c, d = _v(x1, y, z0, uv, idall), _v(x0, y, z0, uv, idall)
    return [[a, b, d], [b, c, d]]


def _lawful_donor_terrain(x0, x1, z0, z1):
    """A LAWFUL donor island patch: per-4u-cell grass mains quads UV'd through ``ground_uv``, in the
    WORLD frame ``world_tris`` returns. (test_world_orphangate's donor fixture uses a flat (0.5,0.5)
    uv -- itself a zero-area constant stamp, exactly what these gates exist to refuse -- so this file
    mints a clean one instead of reusing it.)"""
    idall = float(encode_id(topograph=GL.GROUNDS["grass"]["topo"]))
    out = []
    for i in range(int(x0 // 4), int(x1 // 4)):
        for j in range(int(z0 // 4), int(z1 // 4)):
            cell = (i, j)
            quad, ori = ((i + j) % 2, (i * 3 + j) % 2), GL.ORIS[(i + 2 * j) % 4]
            cx0, cz0 = 4.0 * i, 4.0 * j

            def c(px, pz, _cell=cell, _q=quad, _o=ori):
                # y = 3.2 (the kit's default land height): at y=0 the whole patch would be FULLY
                # SUBMERGED under the sea plane and sea predicate A would refuse it -- which it did,
                # on the first run of this fixture.
                return _v(px, 3.2, pz, GL.ground_uv(px, pz, _cell, _q, _o, "grass"), idall)

            a, b = c(cx0, cz0 + 4.0), c(cx0 + 4.0, cz0 + 4.0)
            d, e = c(cx0 + 4.0, cz0), c(cx0, cz0)
            out += [[a, b, e], [b, d, e]]
    return out


def _island_donor():
    """Donor (1,1): a LAWFUL small terrain island + a full-cell sea4 (world frame x 64..128,
    z -128..-64)."""
    return {(1, 1, "terrain"): _lawful_donor_terrain(88.0, 104.0, -104.0, -88.0),
            (1, 1, "sea4"): _quad_tris(64.0, 128.0, -128.0, -64.0, idall=232.0)}


def test_transplant_reports_the_texture_and_sea_gates_and_stays_clean(monkeypatch):
    """The byte-identity contract in WARN mode: the new gates report present + clean, and an existing
    clean carry stays clean."""
    monkeypatch.setattr(TR, "world_tris", _fake_world(_island_donor()))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True, census_samples=8)
    got = {g["gate"] for g in s["gates"]}
    assert {"tex-zero-uv", "tex-one-window", "tex-family-rect", "sea-plan"} <= got
    for g in s["gates"]:
        if g["gate"].startswith("tex-") or g["gate"] == "sea-plan":
            assert g["ok"] is True and g["warn"] is False, g
    assert s["clean"] is True


def test_transplant_one_window_is_skipped_on_a_carry(monkeypatch):
    """A carry (GroundRetile included) TRANSLATES the donor's own free fractional windows rather than
    minting on the quadrant lattice, so the ONE-WINDOW law is undefined there -- by design."""
    monkeypatch.setattr(TR, "world_tris", _fake_world(_island_donor()))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True, census_samples=8)
    ow = next(g for g in s["gates"] if g["gate"] == "tex-one-window")
    assert ow["skipped"] is True and ow["ok"] is True


def test_transplant_kwargs_thread_to_the_texture_gates(monkeypatch):
    monkeypatch.setattr(TR, "world_tris", _fake_world(_island_donor()))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True, census_samples=8,
                      enforce_texture_gates=True)
    for g in s["gates"]:
        if g["gate"].startswith("tex-") or g["gate"] == "sea-plan":
            assert g["enforced"] is True, g


def test_transplant_region_reports_the_texture_and_sea_gates(monkeypatch):
    donor = {(1, 1, "terrain"): _lawful_donor_terrain(88.0, 104.0, -104.0, -88.0),
             (1, 1, "sea4"): _quad_tris(64.0, 128.0, -128.0, -64.0, idall=232.0),
             (2, 1, "terrain"): _lawful_donor_terrain(152.0, 168.0, -104.0, -88.0),
             (2, 1, "sea4"): _quad_tris(128.0, 192.0, -128.0, -64.0, idall=232.0)}
    monkeypatch.setattr(TR, "world_tris", _fake_world(donor))
    s = TR.transplant_region("MOD", cell=(4, 2), donor=(1, 1), size=(2, 1), dry_run=True,
                             census_samples=8)
    got = {g["gate"] for g in s["gates"]}
    assert {"tex-zero-uv", "tex-one-window", "tex-family-rect", "sea-plan"} <= got
    sea = next(g for g in s["gates"] if g["gate"] == "sea-plan")
    assert sea["B_pairs"] == 1 and sea["ok"] is True       # region-wide: predicate B has a real pair


# ================================================================================================ CLI flag threading
def _fake_summary():
    return dict(op="transplant", donor=[7, 17], cell=[4, 19], rot=0, shift=[0.0, 0.0],
                window={"x": [0.0, 0.0], "z": [0.0, 0.0]}, strips=[], coverage_strips=[],
                carried={}, clipped_out={}, blanked=[], gates=[], clean=True, dry_run=True,
                deployed=[])


@pytest.mark.parametrize("argv,expect", [
    (["--enforce-texture-gates", "--allow-texture-gates"], (True, True)),
    ([], (False, False)),
])
def test_cli_texture_gate_flags_thread_to_transplant(monkeypatch, argv, expect):
    from ff9mapkit import cli
    from ff9mapkit.world import transplant as TRmod
    captured = {}

    def fake_transplant(mod_folder, **kw):
        captured.update(kw)
        return _fake_summary()

    monkeypatch.setattr(TRmod, "transplant", fake_transplant)
    rc = cli.main(["world-transplant", "--mod-folder", "MOD", "--cell", "4,19", "--donor", "7,17",
                   "--dry-run"] + argv)
    assert rc == 0
    assert (captured["enforce_texture_gates"], captured["allow_texture_gates"]) == expect


# ================================================================================================ verify_landmass wiring
def test_verify_landmass_reports_texgates_and_can_be_disabled():
    built = I.build_landmass(center=(224.0, -96.0), base_radius=20.0, seed=5.0)
    assert "mains_field" in built and built["mains_field"]
    rep = I.verify_landmass(built)
    assert [g["gate"] for g in rep["texgates"]] == ["tex-zero-uv", "tex-one-window",
                                                    "tex-family-rect"]      # no sea_plane -> no sea gate
    assert I.verify_landmass(built, texgates=False).get("texgates") is None


def test_verify_landmass_enforce_texgates_folds_a_defect_into_clean():
    """The gate is REAL at the chokepoint: stamp one constant UV over the mint and ``clean`` flips --
    but only under ``enforce_texgates`` (WARN default never changes an existing verdict)."""
    built = I.build_landmass(center=(224.0, -96.0), base_radius=20.0, seed=5.0)
    assert I.verify_landmass(built)["clean"] is True
    for bm in built["blocks"].values():
        for k in range(len(bm.chan_arrays[CH_UV])):
            bm.chan_arrays[CH_UV][k] = [0.5, 0.5]
    warn_rep = I.verify_landmass(built)
    assert any(g["warn"] for g in warn_rep["texgates"])
    assert all(g["ok"] for g in warn_rep["texgates"])
    enf_rep = I.verify_landmass(built, enforce_texgates=True)
    assert enf_rep["clean"] is False
    assert not enf_rep["texgates"][0]["ok"]
    assert I.verify_landmass(built, enforce_texgates=True, allow_texgates=True)["clean"] is True


def test_gate_status_key_tells_the_reporting_truth():
    """Audit rec 9's surviving payload: `ok` is the deploy verdict (True under WARN-default
    even when dirty), so a headline derived from `ok` alone printed "gates CLEAN" over a
    live warn row. `status` is the reporting truth."""
    from ff9mapkit.world.texgates import _gate
    assert _gate("g", enforce=False, allow=False, dirty=False, detail=0)["status"] == "pass"
    warn = _gate("g", enforce=False, allow=False, dirty=True, detail=1)
    assert warn["ok"] is True and warn["status"] == "warn"
    fail = _gate("g", enforce=True, allow=False, dirty=True, detail=1)
    assert fail["ok"] is False and fail["status"] == "fail"
    assert _gate("g", enforce=True, allow=True, dirty=True, detail=1)["status"] == "pass"


def test_the_cli_headline_never_says_clean_over_a_warn():
    """[[feedback-a-check-that-cannot-fail]]: the exact defect was `clean = all(g["ok"])`
    printing CLEAN three lines under a warning. The helper is the one voice now."""
    from ff9mapkit.cli import _world_gate_headline
    clean = _world_gate_headline([{"status": "pass"}, {"status": "pass"}], "gates CLEAN")
    assert clean == "gates CLEAN"
    honest = _world_gate_headline([{"status": "pass"}, {"status": "warn"}], "gates CLEAN")
    assert "CLEAN" not in honest and "WARN" in honest
    legacy = _world_gate_headline([{"ok": True, "warn": True}], "gates CLEAN")
    assert "CLEAN" not in legacy                          # rows without `status` still count
