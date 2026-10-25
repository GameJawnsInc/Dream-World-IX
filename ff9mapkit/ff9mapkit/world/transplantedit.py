"""Carrying a real coastal block -- or a multi-block carry unit -- as the overworld editor drives it (rung C5): the coast
donors, a donor's land as the ghost on the target (turned by the carry's own quarter-turn map), the target's laws as
a preview, and the ONE place the editor's ``world-transplant`` command is built.

THE CLI STAYS THE ORACLE: Check runs :func:`command` with ``--dry-run`` and Accept without, and both read the verdict
``--report-json`` writes. A single block runs with ``--shift auto`` (the carried land centred in its cell; the ghost
stands unshifted until a check reports the shift it chose, then moves by it). A MULTI-BLOCK unit (``--size``) runs
with ``--shift 0,0``: auto-shift on a rect holding empty ocean destroyed a 4x4 test (the coast study's DESIGN-MENU).

THE DONORS are ``donors.toml``'s coast rows: the qualified single blocks, and the multi-block carry units -- the only
disc-1 rects that hold every landmass they touch whole -- with the quarter turns each allows (``rots``). A candidate
(not yet walked in game) is listed and says so.

THE RECIPE ROW is ``world-fuse``'s ``[[transplant]]``, which runs this very command -- not ``[[placement]]``, whose
fused path refuses carries the single-cell command makes (measured: the beach island at (3,5) turned 90, land-fit).

THE LAWS the preview runs: every target block is TRUE open ocean on the stock disc and on the grid's rows (columns wrap:
a rect may carry across x = 0, rung C23), and no folder of the stack nor the draft already holds one. The
carry's own gates (land fit, census, welds, the texture gates) run on Check. The disc-4 step is the mirror's copy,
which Promote runs in the live folder.
"""
from __future__ import annotations

import math

import numpy as np

from .forestedit import CENTRE_STEP, SoupIndex, fmt_num, read_verdict   # noqa: F401  (the tools' shared kit)
from .islandedit import stock_land                                       # noqa: F401  (the open-ocean law's read)

ROTS = (0, 90, 180, 270)
LAND_PARTS = ("terrain", "beach1")
GRID = (24, 20)


def donors() -> list:
    """The coast rows of ``donors.toml`` the picker offers (qualified, then candidates), each with ``donor`` (the
    rect's min block: ``--donor``'s anchor), ``size`` ``(nx, ny)`` and ``rots``."""
    from .donors import load_donors, spec_blocks
    out = []
    for status in ("qualified", "candidate"):
        for r in load_donors():
            if r.get("class") == "coast" and r.get("status") == status:
                bs = spec_blocks(r["blocks"])
                x0, y0 = min(b[0] for b in bs), min(b[1] for b in bs)
                size = (max(b[0] for b in bs) - x0 + 1, max(b[1] for b in bs) - y0 + 1)
                out.append({**r, "donor": (x0, y0), "size": size, "rots": tuple(r.get("rots", ROTS))})
    return out


def tsize(size, rot: int) -> tuple:
    """The target rect's size: a quarter turn swaps the donor rect's sides."""
    return tuple(size) if (int(rot) // 90) % 2 == 0 else (size[1], size[0])


def donor_land(donor, *, size=(1, 1), disc: int = 1, game=None) -> np.ndarray:
    """The donor rect's land (Terrain and its beach) as world triangles ``(n, 3, 3)``, from stock."""
    from . import transplant as TR
    tris = [[v[0] for v in t] for i in range(int(size[0])) for j in range(int(size[1])) for p in LAND_PARTS
            for t in TR.world_tris(int(donor[0]) + i, int(donor[1]) + j, p, disc=disc, game=game)]
    return np.asarray(tris, dtype=np.float64).reshape(-1, 3, 3)


def placed(land, donor, cell, *, rot: int = 0, shift=(0.0, 0.0), size=(1, 1)) -> np.ndarray:
    """The donor's land carried to ``cell``: region-local about the donor rect's corner, turned about the rect's centre
    by the carry's own quarter-turn map (``transplant._rot_region_xz``: ``(dx, dz) -> (-dz, dx)`` per step; a 1x1 rect
    is ``_rot_xz``), laid at the target rect's corner, shifted."""
    land = np.array(land, dtype=np.float64)
    ext = (64.0 * size[0], 64.0 * size[1])
    ts = tsize(size, rot)
    ext_r = (64.0 * ts[0], 64.0 * ts[1])
    dx = land[..., 0] - 64.0 * donor[0] - ext[0] / 2.0
    dz = land[..., 2] + 64.0 * donor[1] + ext[1] / 2.0
    for _ in range((int(rot) // 90) % 4):
        dx, dz = -dz, dx
    land[..., 0] = 64.0 * cell[0] + ext_r[0] / 2.0 + dx + float(shift[0])
    land[..., 2] = -64.0 * cell[1] - ext_r[1] / 2.0 + dz + float(shift[1])
    return land


def cells(cell, size=(1, 1), rot: int = 0) -> list:
    """The target blocks, by the engine's labels: columns wrap (a rect at column 23 two wide fills 23 and 0, rung
    C23, as ``transplant_region`` writes it); rows do not."""
    tw, th = tsize(size, rot)
    return [((int(cell[0]) + i) % GRID[0], int(cell[1]) + j) for j in range(th) for i in range(tw)]


def rim(cell, size=(1, 1), rot: int = 0) -> np.ndarray:
    """The target rect's frame at sea level: the ghost's rim (the carry fills exactly this rect)."""
    tw, th = tsize(size, rot)
    x0, z0 = 64.0 * cell[0], -64.0 * cell[1]
    x1, z1 = x0 + 64.0 * tw, z0 - 64.0 * th
    return np.array([(x0, 0.4, z0), (x1, 0.4, z0), (x1, 0.4, z1), (x0, 0.4, z1)])


def anchor_for(x: float, z: float, *, size=(1, 1), rot: int = 0) -> tuple:
    """The target rect's anchor (min block) for a click at ``(x, z)``: the rect whose middle is nearest it. Its column
    wraps -- a rect whose middle is near x = 0 anchors in column 23 and carries across the seam (rung C23); its row is
    kept on the grid. A single block keeps its own cell."""
    tw, th = tsize(size, rot)
    if (tw, th) == (1, 1):
        return cell_of(x, z)
    bx = int(round(x / 64.0 - tw / 2.0))
    by = int(round(-z / 64.0 - th / 2.0))
    return (bx % GRID[0], max(0, min(GRID[1] - th, by)))


#: the carry's land-fit margin (``transplant.transplant``'s ``land_margin``): its land keeps this much sea to the frame
LAND_MARGIN = 2.0


def too_wide(donor_tris, *, size=(1, 1), rot: int = 0, cell=(0, 0)):
    """None when the donor's land can fit its target rect, else ``{"why", "where"}``: THE LAND-FIT LAW, from the donor
    alone (rung C16). The carry's ``land-fit`` gate needs ``LAND_MARGIN`` of sea between its land (every Terrain and
    beach tri, the seabed included) and the rect's frame on all four sides, so land wider than the rect less twice the
    margin, along either axis, can never fit whatever the shift: a block cut from a continent's coast fills its frame.
    ``where`` = the middles of the two edges the land runs to, on the target rect at ``cell``."""
    t = np.asarray(donor_tris, dtype=np.float64).reshape(-1, 3)
    if not len(t):
        return None
    ext = [float(np.ptp(t[:, 0])), float(np.ptp(t[:, 2]))]          # in the donor's own frame
    if (int(rot) // 90) % 2:
        ext.reverse()
    tw, th = tsize(size, rot)
    x0, z0, x1, z1 = 64.0 * cell[0], -64.0 * cell[1], 64.0 * (cell[0] + tw), -64.0 * (cell[1] + th)
    where, sides = [], []
    if ext[0] > 64.0 * tw - 2 * LAND_MARGIN + 1e-6:
        where += [(x0, (z0 + z1) / 2.0), (x1, (z0 + z1) / 2.0)]
        sides.append(f"{ext[0]:.0f}u east to west")
    if ext[1] > 64.0 * th - 2 * LAND_MARGIN + 1e-6:
        where += [((x0 + x1) / 2.0, z0), ((x0 + x1) / 2.0, z1)]
        sides.append(f"{ext[1]:.0f}u north to south")
    if not where:
        return None
    return {"why": f"its land runs to its block's edge ({' and '.join(sides)}); a carry needs "
                   f"{LAND_MARGIN:g}u of sea all round it, so this block cannot be carried alone", "where": where}


def preview(cell, *, land: set, occupied, size=(1, 1), rot: int = 0, donor_tris=None) -> dict:
    """The target's laws: ``{"ok", "why", "where", "blocks"}``. ``donor_tris`` (the donor's land, :func:`donor_land`)
    adds THE LAND-FIT LAW (:func:`too_wide`), which no target can pass for a donor that fills its frame."""
    from . import mesh as M
    tw, th = tsize(size, rot)
    region = (tw, th) != (1, 1)
    cs = cells(cell, size, rot) if region else [(M.wrap_block_col(int(cell[0])), int(cell[1]))]

    def mid(c):
        return (64.0 * c[0] + 32.0, -(64.0 * c[1] + 32.0))
    off = [c for c in cs if not (0 <= c[1] < GRID[1] and 0 <= c[0] < GRID[0])]
    if off:
        return {"ok": False, "why": "the carry runs off the map", "where": [], "blocks": cs}
    wide = too_wide(donor_tris, size=size, rot=rot, cell=cell) if donor_tris is not None else None
    if wide:
        return {"ok": False, "why": wide["why"], "where": wide["where"], "blocks": cs, "donor": True}
    real = [c for c in cs if c in land]
    if real:
        what = f"block ({real[0][0]}, {real[0][1]}) is" if not region else \
            f"{len(real)} of its {len(cs)} blocks are"
        return {"ok": False, "why": f"{what} real land or coast (a carry goes onto open ocean)",
                "where": [mid(c) for c in real], "blocks": cs}
    taken = occupied(cs)
    if taken:
        what = f"block ({cs[0][0]}, {cs[0][1]})" if not region else f"{len(taken)} of its {len(cs)} blocks"
        return {"ok": False, "why": f"{what} already {'holds' if not region else 'hold'} an edit in "
                                    + ", ".join(sorted({f for fs in taken.values() for f in fs})),
                "where": [mid(c) for c in taken], "blocks": cs}
    return {"ok": True, "why": "", "where": [], "blocks": cs}


def cell_of(x: float, z: float) -> tuple:
    return (math.floor(x / 64.0), math.floor(-z / 64.0))


def command(mod_folder, cell, donor, *, rot: int = 0, size=(1, 1), dry_run: bool = True, report=None) -> list:
    """The ``world-transplant`` argv (after ``python -m ff9mapkit``): a single block with shift auto, or a multi-block
    unit (``--size``) with ``--shift 0,0`` (the module docstring)."""
    argv = ["world-transplant", "--mod-folder", str(mod_folder), "--cell", f"{int(cell[0])},{int(cell[1])}",
            "--donor", f"{int(donor[0])},{int(donor[1])}"]
    if tuple(size) != (1, 1):
        argv += ["--size", f"{int(size[0])}x{int(size[1])}", "--shift", "0,0"]
    if int(rot) % 360:
        argv += ["--rot", str(int(rot) % 360)]
    if dry_run:
        argv.append("--dry-run")
    if report is not None:
        argv += ["--report-json", str(report)]
    return argv
