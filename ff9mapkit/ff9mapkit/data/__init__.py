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
These blobs are derived from Final Fantasy IX field data (the blank field originated as a
cleaned clone of a base field). They are bundled here so the kit is functional out of the
box for *development*. For a clean public release, prefer extracting the blank from the
user's own game install (a documented step) rather than redistributing game-derived bytes.
"""

from __future__ import annotations

from importlib import resources

from ..config import LANGS

_PKG = "ff9mapkit.data"


def blank_field_bytes(lang: str = "us") -> bytes:
    """Bytes of the blank field event script for *lang* (defaults to 'us')."""
    if lang not in LANGS:
        raise ValueError(f"unknown language {lang!r}; expected one of {LANGS}")
    return (resources.files(_PKG) / "blank_field" / f"{lang}.eb.bytes").read_bytes()


def region_template() -> bytes:
    """The 272-byte field-exit region template."""
    return (resources.files(_PKG) / "region_template.bin").read_bytes()
