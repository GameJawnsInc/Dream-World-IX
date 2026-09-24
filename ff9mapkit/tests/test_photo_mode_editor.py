"""``[photo]`` on the two AUTHORING surfaces that are not the build (photo mode rung 1):

  * THE FORM EDITOR's Save regenerates the whole field.toml through ``editor.model.dumps`` -- a key it cannot write
    back is a key the author loses on the next Save. ``[photo]`` round-trips as its own section, ``grade = false`` and
    ``hide = []`` included.
  * THE HARVESTED LINT SCHEMA (``_fieldschema.py``, regenerated from a vivi-hut photo stub) enforces ``photo``: a typo'd
    key is a did-you-mean, and the vocabulary is exactly ``content.photo``'s own key table.

Pure: no templates, no build, never skips.
"""
from __future__ import annotations

import tomllib

from ff9mapkit import fieldschema
from ff9mapkit.content import photo
from ff9mapkit.editor import model

_DOC = {
    "field": {"id": 30992, "name": "PHOTE", "area": 11},
    "photo": {"open_button": "l2", "close_button": "l2", "hide_button": "r1", "grade_button": "l1",
              "hide": ["player", "all"], "grade": True},
}


def test_editor_round_trips_photo():
    for doc in (_DOC, {**_DOC, "photo": {"hide": [], "grade": False}}, {**_DOC, "photo": {}}):
        text = model.dumps(doc)
        assert tomllib.loads(text) == doc, text
        assert photo.parse(tomllib.loads(text)) == photo.parse(doc)


def test_fielddoc_save_keeps_photo(tmp_path):
    p = tmp_path / "phote.field.toml"
    p.write_text(model.dumps(_DOC), encoding="utf-8")
    doc = model.FieldDoc.load(p)
    doc.field["title"] = "Edited"
    doc.save()
    assert tomllib.loads(p.read_text(encoding="utf-8"))["photo"] == _DOC["photo"]


def test_schema_enforces_photo_with_did_you_mean():
    vocab, enforced = fieldschema.load_schema()
    assert "photo" in enforced and "photo" in vocab[""]
    assert set(vocab["photo"]) == set(photo._KEYS)
    out = fieldschema.check({"photo": {"hide_buton": "r1"}}, vocab=vocab, enforced=enforced)
    assert len(out) == 1 and "'hide_buton'" in out[0] and "hide_button" in out[0], out
    assert fieldschema.check(_DOC, vocab=vocab, enforced=enforced) == []
