"""FF9 field ``.sps`` (Special Particle System) effect authoring -- the particle-effect analogue of the
field / battle pillars. An ``.sps`` is a multi-frame cloud of 2D textured billboard quads ("prims") sampling
the shared per-scene ``spt.tcb`` texture; the field ``.eb`` fires ``RunSPSCode`` to load, place, and loop it
(~15 fps). This package owns the ``.sps`` GEOMETRY/ANIMATION bytes -- the half we fully control.

``codec`` is the lossless parse / serialize / build foundation (proven byte-exact vs the engine source --
``SPSEffect.LoadSPS`` / ``_GenerateSPSPrims`` -- and a 9-file Ice-Cavern corpus). The texture (``spt.tcb``,
a PSX-VRAM blit blob) is a SEPARATE format and the real authoring gate; see [[project-ff9-sps-authoring]]
for the tiered editor plan (catalog browser -> declarative re-skin -> from-scratch creator).

NOTE: the kit already CARRIES a fork's ``.sps`` + ``spt.tcb`` verbatim (``extract.py`` / ``build.py``) so a
forked field keeps its donor's effects ([[project-ff9-sps-fork]]). This package is the from-scratch AUTHORING
half that the verbatim byte-copy doesn't cover.
"""
from __future__ import annotations

from . import codec  # noqa: F401  (pure, no I/O -- safe to import always)
