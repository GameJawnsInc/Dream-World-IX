"""Offline READ layer for FF9's summon-cutscene ``ef###.bytes`` containers -- the last raw-PSX geometry
island in the shipped game.

This package is the committable, provenance-clean parser/decoder half of the summon-transplant study
(``studies/custom-summons/thomas-swap/``). Every module reads a caller-supplied stock blob (a stock
``ef###.bytes`` the user extracted from their OWN install, kept only under ``C:/gd/SCRATCH/...``) and
returns offsets, counts, typed structures and decoded angles. Nothing here embeds game bytes, and nothing
here writes -- the write / re-import lane is a separate, later concern with its own provenance rules.

Modules:
  * ``container`` -- the container / chunk / resource-table walk + the creature-package header + the
    model-address map that reaches the skeleton, the mesh table (POLY buckets + run-length rigid skinning)
    and the motion-clip payload offsets.
  * ``motion``    -- the motion-clip decoder (12-bit coarse+fine Euler) + the exact psyq rotation math
    (``build_rotation`` and its closed-form inverse ``decompose``), plus a self-validating entry point.
  * ``build``     -- the Model-struct adapter: turns a decoded ``Geom`` + motion clips into the exact dict
    shapes ``ff9mapkit.models.gltf``/``fbx_skin`` consume (rigid one-bone-per-vertex weights, bind-pose
    verts baked via forward kinematics, dense per-frame rotation/root-translation clip curves).

All three are pure (no I/O at import) and safe to import always.
"""
from __future__ import annotations

from . import build, container, motion  # noqa: F401
