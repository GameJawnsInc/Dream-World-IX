"""The editor app's pure glue (no Tk window needed): ``_apply`` writes a form's entity back into the
doc while clearing this spec's now-absent keys but preserving non-spec keys (single-file spatial data
and unknown future keys survive an edit)."""

from __future__ import annotations

import pytest

pytest.importorskip("tkinter")          # the app module imports tkinter (no display needed to import)

from ff9mapkit.editor import app, forms   # noqa: E402


def test_apply_clears_absent_spec_keys_keeps_others():
    target = {"name": "Vivi", "pos": [0, -700], "dialogue": "old", "custom_x": 5}
    app._apply(target, forms.NPC_SPEC, {"name": "Vivi", "dialogue": "new"})
    assert target["dialogue"] == "new"      # updated
    assert "pos" not in target              # a spec key absent in the new entity -> cleared
    assert target["custom_x"] == 5          # a non-spec key -> preserved


def test_apply_keeps_explicit_spatial_when_present():
    target = {"name": "Vivi", "pos": [0, -700]}
    app._apply(target, forms.NPC_SPEC, {"name": "Vivi", "pos": [10, 20], "dialogue": "hi"})
    assert target["pos"] == [10, 20] and target["dialogue"] == "hi"


class _FakeListbox:
    """Just enough of tk.Listbox for ``_step_add``/``_reload_steps`` to drive."""

    def __init__(self):
        self._sel = ()
        self._items = []

    def curselection(self):
        return self._sel

    def delete(self, start, end):
        self._items = []

    def insert(self, index, text):
        self._items.append(text)

    def selection_set(self, index):
        self._sel = (index,)

    def size(self):                     # both step verbs re-select the row they wrote
        return len(self._items)


def _fake_step_editor(steps, kind, val, sel=(0,)):
    fake = app.EditorApp.__new__(app.EditorApp)
    fake.doc = type("Doc", (), {"data": {"cutscene": {"steps": steps}}})()
    lb = _FakeListbox()
    lb._sel = sel
    fake.step_widgets = {
        "listbox": lb,
        "kind": type("V", (), {"get": lambda self: kind})(),
        "val": type("V", (), {"get": lambda self: val})(),
    }
    return fake


def test_step_update_preserves_actor_and_with_prev():
    """Editing an existing step's Value must not drop its actor tag or with_prev flag -- those
    aren't editable via this form, so a full-dict replacement silently corrupts multi-actor
    choreography (build.py resolves the actor from ``step['actor']``)."""
    steps = [{"animation": "sad", "actor": "vivi", "with_prev": True}]
    app.EditorApp._step_update(_fake_step_editor(steps, "animation", "glad"))
    assert steps[0] == {"animation": "glad", "actor": "vivi", "with_prev": True}


def test_step_update_can_change_a_steps_KIND_in_place():
    """One overloaded button could not: a kind mismatch took the append branch, leaving the
    original untouched and dropping a stray step at the end."""
    steps = [{"wait": 30, "actor": "vivi"}]
    app.EditorApp._step_update(_fake_step_editor(steps, "say", "converted"))
    assert steps == [{"actor": "vivi", "say": "converted"}]


def test_step_add_always_appends_after_the_selection():
    """Two consecutive steps of the SAME kind must both survive."""
    steps = [{"say": "one"}]
    app.EditorApp._step_add(_fake_step_editor(steps, "say", "two"))
    assert steps == [{"say": "one"}, {"say": "two"}]


def test_step_add_with_no_selection_appends_at_the_end():
    steps = [{"say": "one"}]
    app.EditorApp._step_add(_fake_step_editor(steps, "say", "two", sel=()))
    assert steps == [{"say": "one"}, {"say": "two"}]


# --- the [[cutscene]] DISPATCH: this editor used to raise AttributeError on every shipped example ---
def _fake_with(data):
    fake = app.EditorApp.__new__(app.EditorApp)
    fake.doc = type("Doc", (), {"data": data})()
    return fake


def test_steps_reads_block_zero_of_a_dispatch():
    """`_steps` ran `list.setdefault` on a [[cutscene]] array -> AttributeError."""
    data = {"cutscene": [{"steps": [{"say": "one"}]}, {"steps": [{"say": "two"}]}]}
    assert app.EditorApp._steps(_fake_with(data)) == [{"say": "one"}]


def test_steps_materializes_into_the_list_not_beside_it():
    data = {"cutscene": [{"actors": ["Cid"]}]}
    app.EditorApp._steps(_fake_with(data)).append({"say": "hi"})
    assert data["cutscene"] == [{"actors": ["Cid"], "steps": [{"say": "hi"}]}]


def test_apply_folds_a_dispatch_form_into_block_zero_and_keeps_scene_two():
    """The form's fold must not replace the whole array with one table."""
    data = {"cutscene": [{"requires_scenario": 100, "steps": [{"say": "one"}]},
                         {"requires_scenario": 300, "steps": [{"say": "two"}]}]}
    # the exact branch _commit_active takes for a cutscene (app.py, `elif a["type"] == "cutscene"`)
    cs = forms.single_block(data, "cutscene", create=True)
    steps = cs.get("steps", [])
    app._apply(cs, forms.CUTSCENE_SPEC, {"requires_scenario": 150})
    cs["steps"] = steps
    assert isinstance(data["cutscene"], list) and len(data["cutscene"]) == 2
    assert data["cutscene"][0]["requires_scenario"] == 150
    assert data["cutscene"][0]["steps"] == [{"say": "one"}]
    assert data["cutscene"][1]["requires_scenario"] == 300, "scene #2 must survive"
