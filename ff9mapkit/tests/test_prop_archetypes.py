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
