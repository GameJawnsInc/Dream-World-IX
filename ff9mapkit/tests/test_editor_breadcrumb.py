"""The tk-FREE half of editor/breadcrumb.py: the Crumb/trail builder. No display, no tkinter (like
the other editor headless tests). The Breadcrumb widget is verified by the human in the running app."""

from __future__ import annotations

from ff9mapkit.editor import breadcrumb as bc


def test_empty_trail():
    assert bc.trail() == []


def test_full_four_level_trail():
    t = bc.trail(journey="Dali Arc", campaign="Dali chain", field="DALI_INN",
                 obj_label="NPC: Innkeeper", obj_key="npc:2")
    assert [c.level for c in t] == [bc.JOURNEY, bc.CAMPAIGN, bc.FIELD, bc.OBJECT]
    assert [c.label for c in t] == ["Dali Arc", "Dali chain", "DALI_INN", "NPC: Innkeeper"]
    # the keys a click handler navigates with: roots are sentinels, field = member name, object = iid.
    assert [c.key for c in t] == ["@journey", "@campaign", "DALI_INN", "npc:2"]


def test_partial_trail_omits_unopened_levels():
    t = bc.trail(journey="Arc", campaign="C")          # no field/object opened yet
    assert [c.level for c in t] == [bc.JOURNEY, bc.CAMPAIGN]
    t2 = bc.trail(journey="Arc", campaign="C", field="F")
    assert [c.level for c in t2] == [bc.JOURNEY, bc.CAMPAIGN, bc.FIELD]


def test_object_needs_a_label_to_appear():
    # an empty object label is dropped (an object key alone is not a crumb)
    t = bc.trail(journey="A", campaign="C", field="F", obj_label="", obj_key="npc:0")
    assert [c.level for c in t] == [bc.JOURNEY, bc.CAMPAIGN, bc.FIELD]


def test_every_level_has_a_glyph():
    for lvl in (bc.JOURNEY, bc.CAMPAIGN, bc.FIELD, bc.OBJECT):
        assert lvl in bc.GLYPH and bc.GLYPH[lvl]


def test_crumb_is_frozen():
    import dataclasses

    c = bc.Crumb(bc.FIELD, "F", "F")
    try:
        c.label = "x"  # type: ignore[misc]
    except (dataclasses.FrozenInstanceError, AttributeError):
        return
    raise AssertionError("expected a frozen dataclass")
