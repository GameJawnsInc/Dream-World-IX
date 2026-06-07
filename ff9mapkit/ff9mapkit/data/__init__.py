"""Bundled binary data + accessors.

Contents
--------
blank_field/<lang>.eb.bytes
    The canonical *blank field* event script (956 bytes), one per language. This is the
    proven minimal playable field used as the starting point for every built field: a clean
    Main_Init (no stray popups, standard movement) plus a single player object. Content
    injectors clone/extend it; the builder writes it (with content) per language.

region_template.bin
    The 272-byte field-exit region body (a SetRegion polygon -> CalculateExitPosition /
    ExitField -> PreloadField -> set FieldEntrance -> Field(target)). The gateway injector
    patches its polygon / entrance / target and appends it as a new entry.

Provenance / distribution note
------------------------------
These blobs are DERIVED from Final Fantasy IX field data (the blank field is a cleaned clone of a
base field; the region template is a base field's exit region). To avoid redistributing Square Enix
game bytes, the public repo ships **none** of them -- they are regenerated from the user's own,
legally-owned FF9 install by ``ff9mapkit extract-templates`` (see :mod:`ff9mapkit.provision` and
docs/PROVENANCE.md) into a local, gitignored cache. The accessors below read that cache and raise a
clear "run extract-templates" message if it isn't present yet.
"""

from __future__ import annotations

from ..config import LANGS
from .. import provision


def blank_field_bytes(lang: str = "us") -> bytes:
    """Bytes of the blank field event script for *lang* (defaults to 'us'). Regenerated from the
    user's FF9 install by ``ff9mapkit extract-templates``; raises if that hasn't been run."""
    if lang not in LANGS:
        raise ValueError(f"unknown language {lang!r}; expected one of {LANGS}")
    p = provision.blank_dir() / f"{lang}.eb.bytes"
    if not p.is_file():
        raise FileNotFoundError(provision.MISSING_MSG)
    return p.read_bytes()


def region_template() -> bytes:
    """The 272-byte field-exit region template (regenerated from the user's install)."""
    p = provision.region_template_path()
    if not p.is_file():
        raise FileNotFoundError(provision.MISSING_MSG)
    return p.read_bytes()
