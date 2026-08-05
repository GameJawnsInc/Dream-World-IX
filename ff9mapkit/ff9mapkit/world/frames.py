"""THE CANONICAL COORDINATE FRAMES (audit rec 12) -- additive; existing sites are NOT migrated.

One place that states, in names, the conventions the world modules re-derive locally:

* **World frame**: X east in ``[0, 1536)``, Z SOUTH-NEGATIVE in ``(-1280, 0]``, toroidal on
  both axes (:func:`wrap_world_xz` is the ONE fold).
* **Block frame**: the 24x20 grid of 64u blocks; block ``(bx, by)`` owns world
  ``[64bx, 64bx+64] x [-64(by+1), -64by]``; block-LOCAL coords are ``x in [0, 64]``,
  ``z in [-64, 0]`` (same Z sign as world).
* **The 4u lattice**: two live index conventions under DELIBERATELY DIFFERENT names --
  :func:`lattice_ij` (j >= 0, from negated z: the rimretile/water retile convention) versus
  :func:`lattice_raw_xz` (j <= 0, raw floor: the interior/coastmorph convention). A
  convention mismatch is now a NAME mismatch, not a silent sign bug.

Constants are RE-EXPORTED from their one owner (``extract.BLOCK_SIZE``,
``mesh.GRID_COLS/GRID_ROWS``), never re-declared; ``tests/test_world_frames.py`` pins every
module's local literal to them.

THE DIRECTIONAL RULE (the audit's refusal, recorded so it is not re-proposed): do NOT
migrate the existing inline world<->block arithmetic in coastmorph/transplant/interior to
this module -- none of it diverges today, it is playtest-load-bearing, and re-authoring it
is the defect factory (DEFECT-FOLLOWS-AUTHORSHIP, CLAUDE.md section 7). New code imports
from here; an old site converts only when a session is already editing that line anyway.
"""
from __future__ import annotations

import math

from .extract import BLOCK_SIZE, block_world_origin
from .mesh import GRID_COLS, GRID_ROWS

#: one 4u sub-tile of the 16x16 per-block retile/texture lattice
LATTICE = 4.0
#: the engine's wrapped world window: 24x20 blocks of 64u = (1536.0, 1280.0)
WORLD_EXTENT = (GRID_COLS * float(BLOCK_SIZE), GRID_ROWS * float(BLOCK_SIZE))


def block_to_world(bx: int, by: int) -> tuple:
    """Block ``(bx, by)`` -> its world-frame origin ``(64bx, -64by)`` (the engine's
    ``transform.position``; delegates to :func:`extract.block_world_origin`)."""
    return block_world_origin(bx, by)


def world_to_block(wx: float, wz: float) -> tuple:
    """World point -> the block ``(bx, by)`` whose footprint holds it (Z NEGATED:
    ``by = floor(-wz/64)``). No wrap -- fold with :func:`wrap_world_xz` first if the
    point may be outside the window."""
    return math.floor(wx / BLOCK_SIZE), math.floor(-wz / BLOCK_SIZE)


def world_to_block_local(wx: float, wz: float, bx: int, by: int) -> tuple:
    """World point -> block ``(bx, by)``'s LOCAL frame: ``(wx - 64bx, wz + 64by)``.
    Same Z sign as world -- local z runs ``[-64, 0]``."""
    return wx - BLOCK_SIZE * bx, wz + BLOCK_SIZE * by


def block_local_to_world(lx: float, lz: float, bx: int, by: int) -> tuple:
    """Block ``(bx, by)``-local point -> world: ``(lx + 64bx, lz - 64by)``."""
    return lx + BLOCK_SIZE * bx, lz - BLOCK_SIZE * by


def lattice_ij(lx: float, lz: float) -> tuple:
    """Block-local point -> 4u lattice cell with ``j >= 0`` counted SOUTHWARD from the
    block's top edge (``j = (-z)//4`` -- rimretile ``cell_of`` / water's grid convention)."""
    return int(lx // LATTICE), int((-lz) // LATTICE)


def lattice_raw_xz(x: float, z: float) -> tuple:
    """Point -> 4u lattice cell by RAW floor on both axes (``j = floor(z/4)``, so ``j <= 0``
    for the world's z <= 0 -- the interior/coastmorph zip-UV convention). Same input as
    :func:`lattice_ij`, DIFFERENT j: that difference is the bug class the two names retire."""
    return int(math.floor(x / LATTICE)), int(math.floor(z / LATTICE))


def wrap_world_xz(wx: float, wz: float) -> tuple:
    """Fold absolute world coords into the engine's mapped window: x -> ``[0, 1536)``,
    z -> ``(-1280, 0]`` (the overworld is toroidal on BOTH axes). Moved verbatim from
    ``navimap._wrap_world`` (audit rec 12) -- the one fold, so a module wrapping only X
    is a visible omission, not a private convention."""
    return wx % WORLD_EXTENT[0], -((-wz) % WORLD_EXTENT[1])
