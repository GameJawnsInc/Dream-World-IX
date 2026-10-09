"""THE WELD DIFFERENTIAL (terrain study defect 13).

Transplant's weld gate refused any near-miss vertex pair (0 < d < 0.05u), on the claim that verbatim donor blocks
have none. Disc 4's (18,4) Terrain+Sea3 has 3 (S17; disc 1 and every other disc-4 block have 0), so a disc-4 carry
of it failed the gate on unmodified bytes, in every pose. The gate now subtracts the donor's own pairs, mapped
through the carry's census inverse -- the T-junction differential's law: stock may, the carry may not mint one.
"""
from __future__ import annotations

import warnings

import pytest

from ff9mapkit import config
from ff9mapkit.world import mesh as M, transplant as T

P, Q = (10.0, 3.0, -20.0), (10.0, 3.02, -20.0)                  # a stock pair, 0.02u apart (donor world)
PRISTINE = {"terrain": [[(P, None), ((11.0, 3.0, -20.0), None), (Q, None)]]}


def _shifted_back(dx, dz):
    return lambda x, z: (x - dx, z - dz)


def test_near_miss_pairs_is_the_weld_audits_core():
    assert M.near_miss_pairs([P, Q, (40.0, 0.0, 0.0)]) == [(P, Q)]
    assert M.near_miss_pairs([P, P]) == []                                      # identical = a weld, not a miss


def test_a_carried_stock_pair_is_inherited_and_anything_else_is_minted():
    back = _shifted_back(4.0, -8.0)                                            # the carry shifted the donor (+4, -8)
    carried = ((14.0, 3.0, -28.0), (14.0, 3.02, -28.0))
    swapped = (carried[1], carried[0])
    elsewhere = ((30.0, 3.0, -28.0), (30.0, 3.02, -28.0))                      # the same shape, somewhere else
    one_end = ((14.0, 3.0, -28.0), (14.03, 3.0, -28.0))                        # shares one end with the stock pair
    lifted = ((14.0, 3.5, -28.0), (14.0, 3.52, -28.0))                         # a tweak moved its height
    minted, inh = T._inherited_weld_pairs([carried, swapped, elsewhere, one_end, lifted], PRISTINE, back)
    assert inh == [carried, swapped] and minted == [elsewhere, one_end, lifted]
    assert T._inherited_weld_pairs([], PRISTINE, back) == ([], [])
    clean = {"terrain": [[(P, None), ((11.0, 3.0, -20.0), None), ((10.0, 3.0, -21.0), None)]]}
    assert T._inherited_weld_pairs([carried], clean, back) == ([carried], [])  # a donor with no stock pair


def _need_install() -> None:
    """Skip LOUDLY (the worktree skip trap): a silent skip prints green with the real-data law unchecked."""
    try:
        import UnityPy  # noqa: F401
        ok = (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        ok = False
    if not ok:
        warnings.warn("THE WELD DIFFERENTIAL went unchecked on real data in this run: no FF9 install + UnityPy. "
                      "Re-run in the MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy (see the warnings summary)")


@pytest.mark.parametrize("shift,rot", [((0, 0), 0), ((0, 0), 90), ((4, -4), 0)])
def test_a_disc4_carry_of_18_4_inherits_its_three_stock_pairs(shift, rot):
    _need_install()
    s = T.transplant("FF9CustomMap_test_nonexistent", cell=(2, 0), donor=(18, 4), disc=4, shift=shift, rot=rot,
                     dry_run=True)
    (g,) = [g for g in s["gates"] if g["gate"] == "weld-audit"]
    assert g["pairs"] == 0 and g["inherited"] == 3 and g["ok"]


def test_the_region_carry_and_disc_1_controls():
    _need_install()
    s = T.transplant_region("FF9CustomMap_test_nonexistent", cell=(2, 0), donor=(17, 4), size=(2, 1), disc=4,
                            shift=(0, 0), dry_run=True)
    (g,) = [g for g in s["gates"] if g["gate"] == "weld-audit"]
    assert g["pairs"] == 0 and g["inherited"] == 3
    s = T.transplant("FF9CustomMap_test_nonexistent", cell=(2, 0), donor=(18, 4), disc=1, shift=(0, 0), dry_run=True)
    (g,) = [g for g in s["gates"] if g["gate"] == "weld-audit"]
    assert g["pairs"] == 0 and g["inherited"] == 0                             # disc 1's (18,4) has none
