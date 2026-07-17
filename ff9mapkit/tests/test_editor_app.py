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


def test_step_add_update_preserves_actor_and_with_prev():
    """Editing an existing step's Value through Add/Update must not drop its actor tag or
    with_prev flag -- those aren't editable via the form, so a full-dict replacement silently
    corrupts multi-actor choreography (build.py resolves the actor from ``step['actor']``)."""
    steps = [{"animation": "sad", "actor": "vivi", "with_prev": True}]
    fake = app.EditorApp.__new__(app.EditorApp)
    fake.doc = type("Doc", (), {"data": {"cutscene": {"steps": steps}}})()
    lb = _FakeListbox()
    lb._sel = (0,)
    fake.step_widgets = {
        "listbox": lb,
        "kind": type("V", (), {"get": lambda self: "animation"})(),
        "val": type("V", (), {"get": lambda self: "glad"})(),
    }
    app.EditorApp._step_add(fake)
    assert steps[0] == {"animation": "glad", "actor": "vivi", "with_prev": True}
