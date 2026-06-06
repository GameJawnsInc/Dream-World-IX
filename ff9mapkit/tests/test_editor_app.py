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
