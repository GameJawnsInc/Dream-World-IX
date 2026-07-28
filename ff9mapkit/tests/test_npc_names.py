"""The default-name mint (:mod:`ff9mapkit.editor.names`) — playtest-asked: every new
[[npc]] used to be the literal "NPC", so a field grew TWINS of a load-bearing name
(behavior units and the field/scene merge bind by npc name). The default is now a
fresh FF9-flavoured ``flavor_role`` compound, deduped against the field's own cast."""

from __future__ import annotations

import random

from ff9mapkit.editor import names


def test_the_name_is_a_compound_of_the_two_lists():
    n = names.fresh_npc_name()
    flav, _, role = n.partition("_")
    assert flav in names.FLAVOR and role in names.ROLES


def test_taken_names_are_never_reissued():
    rng = random.Random(7)
    taken = set()
    for _ in range(80):                       # far past the collision-prone regime
        n = names.fresh_npc_name(taken, rng=rng)
        assert n not in taken
        taken.add(n)


def test_a_crowded_field_falls_back_to_a_numeric_suffix():
    every = {f"{f}_{r}" for f in names.FLAVOR for r in names.ROLES}
    n = names.fresh_npc_name(every, rng=random.Random(1))
    stem, _, suffix = n.rpartition("_")
    assert stem in every and suffix.isdigit()   # mist_porter_2 — still unique


def test_rng_makes_it_deterministic_for_tests():
    a = names.fresh_npc_name(rng=random.Random(42))
    b = names.fresh_npc_name(rng=random.Random(42))
    assert a == b


def test_every_candidate_is_a_legal_identifier():
    """Names reach the behavior compiler and the scene merge — keep them tame."""
    for f in names.FLAVOR:
        assert f == f.lower() and f.isidentifier(), f
    for r in names.ROLES:
        assert r == r.lower() and r.isidentifier(), r
