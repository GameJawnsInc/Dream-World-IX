"""The FF9 Map Kit field-logic editor.

A friendly front-end for the *logic* half of a field (dialogue, events, flags, encounters, music,
cutscenes) so authors never hand-write TOML. Spatial placement (camera / walkmesh / positions /
zones) stays in Blender; this editor owns the ``<field>.field.toml`` logic file, leaving any sibling
``<field>.scene.toml`` (Blender-owned) untouched.

- ``model``  - bpy/tk-FREE: load/edit/serialize a field.toml (round-trip-safe TOML writer +
               a ``FieldDoc`` that preserves the scene/field split). Fully unit-testable.
- ``app``    - the Tkinter UI over the model (imported lazily so the package stays importable
               on a headless machine without a display).

Launch with ``ff9mapkit edit [field.toml]``.
"""

from __future__ import annotations

from . import model  # noqa: F401  (re-export the bpy/tk-free core)

__all__ = ["model"]
