"""A new island as the overworld editor drives it (rung C5): its coastline as the ghost (the mint's own outline call,
cheap and exact for a seed), the open-ocean and free-block laws as a preview, and the ONE place the editor's
``world-island`` command is built.

THE CLI STAYS THE ORACLE: Check runs :func:`command` with ``--dry-run`` and Accept without, and both read the verdict
``--report-json`` writes. The ghost is not a carve: :func:`outline` is the same pure call ``island.build_landmass``
makes for the coast ring (``mesh.blob_outline`` / ``multi_blob_outline``), so the ghost is the coast the mint will
build, before any job runs.

THE SEED is always explicit in the command: ``world-island`` derives one from the centre when none is given, so a
re-run elsewhere would not reproduce it, and the recipe row must.

THE LAWS the preview runs are ``island.landmass``' first two refusals: every block the island touches is TRUE open
ocean on the stock disc (a sea-only prefab has no Terrain transform to bind to), and no folder of the stack (nor the
draft) already overrides one (the mod-overwrite gate). The builder's geometry gates run on Check.

THE DISC-4 HALF needs nothing here: a mint's disc-4 step is the mirror's COPY (no replay), which a draft cannot run
and Promote runs in the live folder, as ``world-island`` itself would there.
"""
from __future__ import annotations

import math

import numpy as np

from .forestedit import CENTRE_STEP, SoupIndex, _pip, fmt_num, read_verdict   # noqa: F401  (the tools' shared kit)

RADIUS_RANGE = (12.0, 96.0)       # the radius handle's stops (the mint densifies its ring past 60)
LOBES_RANGE = (1, 3)
HEIGHT_RANGE = (2.0, 6.0)
SEED_MAX = 996                     # the centre-derived seed's own range (int(...) % 997)
DEFAULTS = {"radius": 24.0, "lobes": 1, "height": 3.2, "ground": "grass"}


def grounds() -> list:
    """The ground families an island can be minted in: those whose cliff wall stock dresses as a SEA cliff (THE
    WALL-CONTEXT LAW refuses the rest at the mint)."""
    from .grassland import GROUNDS
    return [name for name, g in GROUNDS.items() if g.get("cls") == "island" and g.get("wall_coastal")]


def outline(center, *, radius: float, seed: float, lobes: int = 1) -> np.ndarray:
    """The coast ring the mint builds, ``(n, 2)`` world ``(x, z)``: ``build_landmass``' own outline call."""
    from . import mesh as M
    cx, cz = float(center[0]), float(center[1])
    if lobes >= 2:
        pts, _r = M.multi_blob_outline(cx, cz, lobes=lobes, base_radius=radius, seed=seed, undulation=0.11)
    else:
        pts, _r = M.blob_outline(cx, cz, base_radius=radius, seed=seed, undulation=0.11,
                                 n=max(96, int(math.ceil(radius * 1.6))), n_corners=3, corner_strength=0.26)
    return np.asarray(pts, dtype=np.float64)


def footprint(ring) -> list:
    """The blocks the island touches: every block the coast passes through (each segment walked at 0.5u: a segment
    can cut a block's corner between two points that stand in others -- a one-tri sliver the mint still writes), and
    every block whose middle the coast encloses (an island wider than a block covers whole ones)."""
    ring = np.asarray(ring, dtype=np.float64)
    nxt = np.roll(ring, -1, axis=0)
    steps = np.maximum(1, np.ceil(np.hypot(*(nxt - ring).T) / 0.5)).astype(int)
    pts = np.concatenate([ring[k] + (nxt[k] - ring[k]) * (np.arange(steps[k])[:, None] / steps[k])
                          for k in range(len(ring))])
    out = {(math.floor(x / 64.0), math.floor(-z / 64.0)) for x, z in pts}
    bx0, bx1 = math.floor(ring[:, 0].min() / 64.0), math.floor(ring[:, 0].max() / 64.0)
    by0, by1 = math.floor(-ring[:, 1].max() / 64.0), math.floor(-ring[:, 1].min() / 64.0)
    for bx in range(bx0, bx1 + 1):
        for by in range(by0, by1 + 1):
            if _pip(np.array([[64.0 * bx + 32.0, -(64.0 * by + 32.0)]]), ring)[0]:
                out.add((bx, by))
    return sorted(out)


def stock_land(*, disc: int = 1, lod: str = "0_1", game=None) -> set:
    """Every block the stock disc ships its own prefab for (any land, beach or coast water): not open ocean."""
    from . import discmirror as DM
    return {tuple(b) for b, parts in DM._real_parts(disc, lod, game=game).items() if parts}


def preview(ring, *, land: set, occupied) -> dict:
    """The mint's first two laws for this ring: ``{"ok", "why", "where", "blocks"}``. ``land`` is
    :func:`stock_land`; ``occupied(blocks)`` returns the folders already overriding each (``{block: [folder]}``)."""
    from . import mesh as M
    blocks = footprint(ring)
    wrapped = sorted({(M.wrap_block_col(bx), by) for bx, by in blocks})
    if any(not 0 <= by < 20 for _bx, by in wrapped):
        return {"ok": False, "why": "it runs off the top or bottom of the map", "where": [], "blocks": wrapped}
    bad = [b for b in wrapped if b in land]
    if bad:
        return {"ok": False, "why": f"it reaches real land or coast at block{'s' if len(bad) > 1 else ''} "
                                    + ", ".join(f"({a}, {b})" for a, b in bad[:4]),
                "where": [_mid(b) for b in bad], "blocks": wrapped}
    taken = occupied(wrapped)
    if taken:
        names = sorted({f for fs in taken.values() for f in fs})
        return {"ok": False, "why": f"block{'s' if len(taken) > 1 else ''} "
                                    + ", ".join(f"({a}, {b})" for a, b in sorted(taken)[:4])
                                    + f" already hold{'s' if len(taken) == 1 else ''} an edit in {', '.join(names)}",
                "where": [_mid(b) for b in sorted(taken)], "blocks": wrapped}
    return {"ok": True, "why": "", "where": [], "blocks": wrapped}


def _mid(b):
    return (64.0 * b[0] + 32.0, -(64.0 * b[1] + 32.0))


def ghost(ring, *, height: float):
    """``(tris, rim)``: the island's land as a flat fan at its height, the coast as the rim."""
    ring = np.asarray(ring, dtype=np.float64)
    rim = np.c_[ring[:, 0], np.full(len(ring), float(height)), ring[:, 1]]
    c = np.array([ring[:, 0].mean(), float(height), ring[:, 1].mean()])
    tris = np.array([[c, rim[k], rim[(k + 1) % len(rim)]] for k in range(len(rim))], dtype=np.float64)
    return tris, rim


def command(mod_folder, center, *, seed: float, radius: float = 24.0, lobes: int = 1, height: float = 3.2,
            ground: str = "grass", dry_run: bool = True, report=None) -> list:
    """The ``world-island`` argv (after ``python -m ff9mapkit``). The seed is always given; other defaults omitted."""
    argv = ["world-island", "--mod-folder", str(mod_folder),
            "--center", f"{fmt_num(center[0], CENTRE_STEP)},{fmt_num(center[1], CENTRE_STEP)}",
            "--seed", fmt_num(seed, 1.0)]
    if abs(float(radius) - DEFAULTS["radius"]) > 1e-9:
        argv += ["--radius", fmt_num(radius, 1.0)]
    if int(lobes) != DEFAULTS["lobes"]:
        argv += ["--lobes", str(int(lobes))]
    if abs(float(height) - DEFAULTS["height"]) > 1e-9:
        argv += ["--height", fmt_num(height, 0.1)]
    if ground != DEFAULTS["ground"]:
        argv += ["--ground", ground]
    if dry_run:
        argv.append("--dry-run")
    if report is not None:
        argv += ["--report-json", str(report)]
    return argv
