"""Named PROP archetypes: a friendly name -> a prop model + its canonical resting pose. Pure (no game
install needed) -- resolution is a model identifier + a number."""
import pytest

from ff9mapkit import catalog as C
from ff9mapkit import prop_archetypes as PA


def test_every_prop_archetype_resolves_to_a_real_model_and_pose():
    for name in PA.names():
        mid, pose = PA.resolve(name)
        assert isinstance(mid, int) and mid > 0, name
        assert isinstance(pose, int) and pose > 0, name
        assert C.model(mid) is not None, name            # the model exists in the catalog


def test_resolve_is_case_insensitive():
    assert PA.resolve("Chest") == PA.resolve("chest")


def test_resolve_unknown_raises():
    with pytest.raises(ValueError):
        PA.resolve("not_a_prop_at_all")


def test_names_and_is_prop_archetype():
    ns = PA.names()
    for expect in ("chest", "tent", "save_book", "feather"):
        assert expect in ns
    assert PA.is_prop_archetype("Tent") and not PA.is_prop_archetype("nope")


def test_composites_resolve_to_real_multi_part_sets():
    assert PA.is_composite("save_point") and not PA.is_composite("chest")
    for name in PA.PROP_COMPOSITES:
        parts = PA.resolve_composite(name)
        assert len(parts) >= 2, name                      # a composite is multi-part
        for mid, pose, dx, dz in parts:
            assert isinstance(mid, int) and mid > 0, (name, mid)
            assert isinstance(pose, int) and pose > 0, (name, pose)
            assert isinstance(dx, int) and isinstance(dz, int), (name, dx, dz)
            assert C.model(mid) is not None, (name, mid)  # every part is a real model
    # the scale set piece offsets its side weight from the anchor; the save point co-locates everything
    assert any(dx or dz for _, _, dx, dz in PA.resolve_composite("scale_set"))
    assert all(dx == 0 and dz == 0 for _, _, dx, dz in PA.resolve_composite("save_point"))
