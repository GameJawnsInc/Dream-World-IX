"""Carrying a real coastal block as the overworld editor drives it (rung C5): the qualified coast donors, a donor's land
as the ghost on the target cell (turned by the carry's own quarter-turn map), the target's laws as a preview, and the
ONE place the editor's ``world-transplant`` command is built.

THE CLI STAYS THE ORACLE: Check runs :func:`command` with ``--dry-run`` and Accept without, and both read the verdict
``--report-json`` writes. ``world-transplant``'s ``--shift auto`` centres the carried land inside the cell; the
ghost stands unshifted until a check reports the shift it chose, then moves by it.

THE RECIPE ROW is ``world-fuse``'s ``[[transplant]]``, which runs this very command -- not ``[[placement]]``, whose
fused path refuses carries the single-cell command makes (measured: the beach island at (3,5) turned 90, land-fit).

THE LAWS the preview runs: the target cell is TRUE open ocean on the stock disc, and no folder of the stack nor the
draft already holds it. The carry's own gates (land fit, census, welds, the texture gates) run on Check. The disc-4
step is the mirror's copy, which Promote runs in the live folder.
"""
from __future__ import annotations

import math

import numpy as np

from .forestedit import CENTRE_STEP, SoupIndex, fmt_num, read_verdict   # noqa: F401  (the tools' shared kit)
from .islandedit import stock_land                                       # noqa: F401  (the open-ocean law's read)

ROTS = (0, 90, 180, 270)
LAND_PARTS = ("terrain", "beach1")


def donors() -> list:
    """The qualified coast donors of ``donors.toml`` (single blocks), the picker's whole list."""
    from .donors import load_donors, spec_blocks
    out = []
    for r in load_donors():
        if r.get("class") == "coast" and r.get("status") == "qualified":
            (blk,) = spec_blocks(r["blocks"])
            out.append({**r, "donor": blk})
    return out


def donor_land(donor, *, disc: int = 1, game=None) -> np.ndarray:
    """The donor block's land (Terrain and its beach) as world triangles ``(n, 3, 3)``, from stock."""
    from . import transplant as TR
    tris = [[v[0] for v in t] for p in LAND_PARTS for t in TR.world_tris(int(donor[0]), int(donor[1]), p, disc=disc,
                                                                         game=game)]
    return np.asarray(tris, dtype=np.float64).reshape(-1, 3, 3)


def placed(land, donor, cell, *, rot: int = 0, shift=(0.0, 0.0)) -> np.ndarray:
    """The donor's land carried to ``cell``: turned ``rot`` about the donor cell's centre by the carry's own
    quarter-turn map (``transplant._rot_xz``: ``(dx, dz) -> (-dz, dx)`` per step), moved to the target cell, shifted."""
    land = np.array(land, dtype=np.float64)
    dcx, dcz = 64.0 * donor[0] + 32.0, -(64.0 * donor[1] + 32.0)
    tcx, tcz = 64.0 * cell[0] + 32.0, -(64.0 * cell[1] + 32.0)
    dx, dz = land[..., 0] - dcx, land[..., 2] - dcz
    for _ in range((int(rot) // 90) % 4):
        dx, dz = -dz, dx
    land[..., 0] = tcx + dx + float(shift[0])
    land[..., 2] = tcz + dz + float(shift[1])
    return land


def rim(cell) -> np.ndarray:
    """The target cell's frame at sea level: the ghost's rim (the carry fills exactly this cell)."""
    x0, z0 = 64.0 * cell[0], -64.0 * cell[1]
    return np.array([(x0, 0.4, z0), (x0 + 64.0, 0.4, z0), (x0 + 64.0, 0.4, z0 - 64.0), (x0, 0.4, z0 - 64.0)])


def preview(cell, *, land: set, occupied) -> dict:
    """The target's laws: ``{"ok", "why", "where", "blocks"}``."""
    from . import mesh as M
    c = (M.wrap_block_col(int(cell[0])), int(cell[1]))
    mid = (64.0 * c[0] + 32.0, -(64.0 * c[1] + 32.0))
    if not 0 <= c[1] < 20:
        return {"ok": False, "why": "the cell is off the map", "where": [], "blocks": [c]}
    if c in land:
        return {"ok": False, "why": f"block ({c[0]}, {c[1]}) is real land or coast (a carry goes onto open ocean)",
                "where": [mid], "blocks": [c]}
    taken = occupied([c])
    if taken:
        return {"ok": False, "why": f"block ({c[0]}, {c[1]}) already holds an edit in "
                                    + ", ".join(sorted({f for fs in taken.values() for f in fs})),
                "where": [mid], "blocks": [c]}
    return {"ok": True, "why": "", "where": [], "blocks": [c]}


def cell_of(x: float, z: float) -> tuple:
    return (math.floor(x / 64.0), math.floor(-z / 64.0))


def command(mod_folder, cell, donor, *, rot: int = 0, dry_run: bool = True, report=None) -> list:
    """The ``world-transplant`` argv (after ``python -m ff9mapkit``): the plain single-cell carry, shift auto."""
    argv = ["world-transplant", "--mod-folder", str(mod_folder), "--cell", f"{int(cell[0])},{int(cell[1])}",
            "--donor", f"{int(donor[0])},{int(donor[1])}"]
    if int(rot) % 360:
        argv += ["--rot", str(int(rot) % 360)]
    if dry_run:
        argv.append("--dry-run")
    if report is not None:
        argv += ["--report-json", str(report)]
    return argv
