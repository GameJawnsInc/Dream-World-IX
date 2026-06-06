"""Coherence guard: the editor's hand-written form specs must not drift from the builder.

The editor (``editor/forms.py``) and the compiler (``build.py`` + ``content/*``) maintain their
field vocabularies independently, so a form could grow a key the builder silently ignores (or
rejects). These tests drive representative entities through the FORMS layer
(``entity_to_values`` -> ``build_entity``, asserting no key is dropped) and then through the REAL
builder, proving every form-produced key is something ``ff9mapkit build`` understands and acts on.
"""

from __future__ import annotations

from pathlib import Path

from ff9mapkit.build import FieldProject, build_mod, lint_logic, validate
from ff9mapkit.config import LANGS, ModLayout
from ff9mapkit.editor import forms


def _via_forms(spec, entity: dict) -> dict:
    """Round-trip an entity through the editor's form layer; assert it preserves every key.

    This is the drift guard: if a spec ever stops covering a key the builder needs, the
    ``== entity`` check fails here (before the entity even reaches the compiler)."""
    out = forms.build_entity(spec, forms.entity_to_values(spec, entity))
    assert out == entity, f"forms dropped/mangled keys: built {out!r} from {entity!r}"
    return out


def _build(tmp_path, doc: dict):
    p = tmp_path / f"{doc['field']['name'].lower()}.field.toml"
    from ff9mapkit.editor.model import dumps          # the editor's own serializer (round-trip-safe)
    p.write_text(dumps(doc), encoding="utf-8")
    proj = FieldProject.load(p)
    assert validate(proj) == [], validate(proj)        # form-produced keys are schema-valid
    assert lint_logic(proj) == [], lint_logic(proj)    # ...and logically consistent
    out = tmp_path / "mod"
    build_mod([proj], out, mod_name="FF9CustomMap")
    return ModLayout(out)


def test_form_entities_are_builder_valid(tmp_path):
    """NPC + gateway + event + encounter + music, every spec key set via the forms, build cleanly."""
    field = _via_forms(forms.FIELD_SPEC,
                       {"id": 4003, "name": "FORMROOM", "area": 11, "text_block": 1073})
    npc = _via_forms(forms.NPC_SPEC,
                     {"name": "Vivi", "preset": "vivi", "dialogue": "hello there",
                      "pos": [0, -400], "requires_flag": 8050})
    gateway = _via_forms(forms.GATEWAY_SPEC,
                         {"name": "door", "to": 100, "entrance": 204,
                          "zone": [[-200, -1200], [200, -1200], [200, -1350], [-200, -1350]]})
    event = _via_forms(forms.EVENT_SPEC,
                       {"name": "lever", "message": "click", "set_flag": [8050, 1],
                        "give_item": [232, 1], "gil": 50,
                        "zone": [[300, -400], [700, -400], [700, -800], [300, -800]], "once": False})
    encounter = _via_forms(forms.ENCOUNTER_SPEC, {"scene": 67, "freq": 200, "battle_music": 0})
    music = _via_forms(forms.MUSIC_SPEC, {"song": 9})

    L = _build(tmp_path, {
        "field": field,
        "camera": {"pitch": 45},
        "walkmesh": {"quad": [[-1200, -100], [1200, -100], [1200, -1400], [-1200, -1400]]},
        "player": {"spawn": [0, -300]},
        "npc": [npc], "gateway": [gateway], "event": [event],
        "encounter": encounter, "music": music,
    })

    from ff9mapkit.eb import EbScript
    from ff9mapkit.eb.disasm import iter_code
    eb = EbScript.from_bytes(L.eb_path("us", "EVT_FORMROOM.eb.bytes").read_bytes())
    assert eb.to_bytes() == eb.data                     # valid script
    ops = [i.op for e in eb.entries if not e.empty for f in e.funcs
           for i in iter_code(eb.data, f.abs_start, f.abs_end)]
    assert 0x48 in ops                                  # AddItem from give_item -> the event built
    mes = L.mes_path("us", 1073).read_text(encoding="utf-8")
    assert "hello there" in mes and "click" in mes      # npc dialogue + event message landed
    for lang in LANGS:
        assert L.eb_path(lang, "EVT_FORMROOM.eb.bytes").is_file()


def test_form_cutscene_is_builder_valid(tmp_path):
    """A narration cutscene authored via the form meta-spec + the step builder compiles + plays."""
    field = _via_forms(forms.FIELD_SPEC, {"id": 4003, "name": "CSFORM", "area": 11, "text_block": 1073})
    meta = _via_forms(forms.CUTSCENE_SPEC, {"once": False, "warmup": 30})   # actor-less = narration
    steps = [forms.make_step("say", "welcome"), forms.make_step("wait", "20"),
             forms.make_step("set_flag", "8060, 1")]
    L = _build(tmp_path, {
        "field": field,
        "camera": {"pitch": 45},
        "walkmesh": {"quad": [[-600, -100], [600, -100], [600, -700], [-600, -700]]},
        "player": {"spawn": [0, -300]},
        "cutscene": {**meta, "steps": steps},
    })
    assert "welcome" in L.mes_path("us", 1073).read_text(encoding="utf-8")
