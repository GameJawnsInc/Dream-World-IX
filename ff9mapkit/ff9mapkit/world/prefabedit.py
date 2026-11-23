"""Placing a landmass PREFAB as the overworld editor drives it (rung P3, studies/overworld-editor/PREFABS.md): the
catalog's prefabs, a prefab's land as the ghost on its anchor block, the clear window as a preview, and the ONE place
the editor's ``world-prefab`` command is built.

THE CLI STAYS THE ORACLE: Check runs :func:`command` with ``--dry-run`` (the clear window, then the prefab staged
outside the install and judged against its catalog fingerprint -- the full one at a clean site, the nav-margin tier
beside stock land) and Accept without, and both read the verdict ``--report-json`` writes. The card never composes
in-process.

THE GHOST is the prefab's own land, cheap and before any job: a minted base is the coast ring the mint builds
(``islandedit.outline``, exact for its seed: the prefab frame keeps the ring the same at every anchor) filled at its
height; a carried base is its donor's land laid by the carry's own quarter-turn map (``transplantedit.placed``); a
carried mountain or forest on it is that donor's own ghost (``mountainedit`` / ``forestedit.placed``). A hill is pure
height and draws nothing of its own. :func:`ghost` builds it for anchor block (0, 0); :func:`at` moves it to an
anchor, by whole blocks.

THE ANCHOR follows the click: the anchor whose footprint's bounding rect is centred nearest the click, its column
wrapped (a prefab may stand across x = 0) and its rows kept on the map (rows do not wrap for writes).

THE LAWS the preview runs are ``world-prefab``'s own first ones (``prefab.place``): the footprint on the map, every
footprint block stock open ocean, no edit in the footprint or its ring in the target (the draft) or any other folder
of the stack, and none in a relief row's read window in the target. Identity, navigation and every verb's own gates
run on Check.

THE TURN (rung P5): the card hands every function here the prefab AS IT LANDS (``prefab.turned``: the turned footprint,
its ``turn``), so the anchor, the rim, the centre and the preview are the turned ones; :func:`turn` lays the turn-0
ghost down turned, by the very rigid map the files take (``prefab.turn_point``).

THE RECIPE ROW is ``world-fuse``'s ``[[prefab]]`` (``name``, ``cell``, ``turn`` when not 0), which runs this very
command's pipeline.
"""
from __future__ import annotations

import math

import numpy as np

from .forestedit import CENTRE_STEP, SoupIndex, fmt_num, read_verdict   # noqa: F401  (the tools' shared kit)
from .islandedit import stock_land                                       # noqa: F401  (the open-ocean law's read)

GRID = (24, 20)
BLOCK = 64.0
#: the height a base is filled at when its row names none (the mint's default)
BASE_HEIGHT = 3.2


def prefabs(catalog=None) -> list:
    """The catalog's prefabs the picker offers: the qualified first (walked in game), then the candidates."""
    from .prefab import load_catalog
    rows = load_catalog(catalog)
    return [p for st in ("qualified", "candidate") for p in rows if p["status"] == st]


def get(name: str, catalog=None) -> dict:
    from .prefab import get as _get
    return _get(name, catalog)


def bbox(prefab: dict) -> tuple:
    """The footprint's bounding rect as block offsets from the anchor: ``(dx0, dy0, dx1, dy1)`` (inclusive)."""
    foot = prefab.get("footprint") or [(0, 0)]
    return (min(int(b[0]) for b in foot), min(int(b[1]) for b in foot),
            max(int(b[0]) for b in foot), max(int(b[1]) for b in foot))


def anchor_for(x: float, z: float, prefab: dict) -> tuple:
    """The anchor block for a click at world ``(x, z)``: the one whose footprint rect is centred nearest it, its
    column wrapped and its rows kept on the map."""
    dx0, dy0, dx1, dy1 = bbox(prefab)
    bx = int(round(x / BLOCK - (dx0 + dx1 + 1) / 2.0))
    by = int(round(-z / BLOCK - (dy0 + dy1 + 1) / 2.0))
    by = max(-dy0, min(GRID[1] - 1 - dy1, by))
    return (bx % GRID[0], by)


def cells(cell, prefab: dict) -> list:
    """The footprint's blocks on anchor ``cell``, by the engine's labels (columns wrap)."""
    from .prefab import footprint_labels
    return footprint_labels(prefab, cell)


def rim(cell, prefab: dict) -> np.ndarray:
    """The footprint's bounding rect at sea level, unwrapped from the anchor (the ghost's frame on the view)."""
    dx0, dy0, dx1, dy1 = bbox(prefab)
    x0, z0 = BLOCK * (cell[0] + dx0), -BLOCK * (cell[1] + dy0)
    x1, z1 = BLOCK * (cell[0] + dx1 + 1), -BLOCK * (cell[1] + dy1 + 1)
    return np.array([(x0, 0.4, z0), (x1, 0.4, z0), (x1, 0.4, z1), (x0, 0.4, z1)])


def center(cell, prefab: dict) -> tuple:
    """The footprint rect's middle, unwrapped from the anchor (the ghost's centre; the verdict folds it)."""
    dx0, dy0, dx1, dy1 = bbox(prefab)
    return (BLOCK * (cell[0] + (dx0 + dx1 + 1) / 2.0), -BLOCK * (cell[1] + (dy0 + dy1 + 1) / 2.0))


def ghost(prefab: dict, *, game=None) -> np.ndarray:
    """The prefab's land as world triangles ``(n, 3, 3)`` for anchor block (0, 0) (frame origin (0, -64)): its base,
    then each carried mountain and forest (module docstring). Reads stock for a carried base or relief (a second or
    two each): the card reads it once per prefab, off the window's thread."""
    from . import islandedit as IE
    from .prefab import origin
    ox, oz = origin((0, 0))
    base = prefab["rows"][0]
    height = float(base.get("height", BASE_HEIGHT))
    parts = []
    if base["table"] == "island":
        c = (ox + float(base["center"][0]), oz + float(base["center"][1]))
        ring = IE.outline(c, radius=float(base.get("radius", 24.0)), seed=float(base["seed"]),
                          lobes=int(base.get("lobes", 1)))
        parts.append(IE.ghost(ring, height=height)[0])
    else:
        from . import transplantedit as TE
        size = tuple(int(v) for v in base.get("size") or (1, 1))
        donor = tuple(int(v) for v in base["donor"])
        land = TE.donor_land(donor, size=size, game=game)
        parts.append(TE.placed(land, donor, tuple(int(v) for v in base["cell"]), rot=int(base.get("rot", 0)),
                               size=size))
    for r in prefab["rows"][1:]:
        c = (ox + float(r["center"][0]), oz + float(r["center"][1]))
        if r["table"] == "mountain":
            from . import mountainedit as ME
            from .interior import MOUNTAIN_DONOR
            ol = ME.outline(str(r.get("donor", "{},{}".format(*MOUNTAIN_DONOR))), game=game)
            parts.append(ME.placed(ol, c, spread=float(r.get("spread", 1.0)), rot_deg=float(r.get("rot", 0.0)),
                                   rock_height=float(r.get("rock_height", 1.0)), ground_y=height)[0])
        elif r["table"] == "forest":
            from . import forestedit as FO
            from .interior import FOREST_DONOR
            d = r.get("donor", FOREST_DONOR)
            d = tuple(int(v) for v in (d.split(",") if isinstance(d, str) else d))
            parts.append(FO.placed(FO.outline(d, game=game), c, spread=float(r.get("spread", 1.0)),
                                   rot_deg=float(r.get("rot", 0.0)), ground_y=height)[0])
    parts = [np.asarray(p, dtype=np.float64).reshape(-1, 3, 3) for p in parts if len(p)]
    return np.concatenate(parts) if parts else np.zeros((0, 3, 3))


def turn(land, prefab: dict) -> np.ndarray:
    """:func:`ghost`'s land (anchor (0, 0), turn 0) laid down as ``prefab`` lands -- turned by its ``turn`` with the
    rigid map the files take, still on anchor (0, 0). Turn 0 is the land as it is."""
    from .prefab import turn_of, turn_point
    out = np.array(land, dtype=np.float64)
    t = turn_of(prefab)
    if not t or not out.size:
        return out
    flat = out.reshape(-1, 3)
    for v in flat:
        v[0], v[2] = turn_point(float(v[0]), float(v[2]), prefab, (0, 0), t)
    return flat.reshape(out.shape)


def at(land, cell) -> np.ndarray:
    """:func:`ghost`'s land moved from anchor (0, 0) to anchor ``cell`` (whole blocks)."""
    out = np.array(land, dtype=np.float64)
    out[..., 0] += BLOCK * int(cell[0])
    out[..., 2] -= BLOCK * int(cell[1])
    return out


def preview(cell, prefab: dict, *, land: set, occupied, occupied_target) -> dict:
    """``world-prefab``'s first laws for anchor ``cell``: ``{"ok", "why", "where", "blocks"}``. ``land`` is the stock
    land set (:func:`stock_land`); ``occupied(blocks)`` -> ``{block: [folder]}`` over the target and the stack;
    ``occupied_target(blocks)`` over the target alone (the relief rows read only it)."""
    from .prefab import _ring, reads

    def mid(b):
        return (BLOCK * b[0] + 32.0, -(BLOCK * b[1] + 32.0))
    dx0, dy0, dx1, dy1 = bbox(prefab)
    if not (0 <= cell[1] + dy0 and cell[1] + dy1 < GRID[1]):
        return {"ok": False, "why": "it runs off the top or bottom of the map", "where": [], "blocks": []}
    foot = cells(cell, prefab)
    real = [b for b in foot if b in land]
    if real:
        return {"ok": False, "why": f"{len(real)} of its {len(foot)} blocks are real land or coast (a prefab goes "
                                    f"onto open ocean)", "where": [mid(b) for b in real], "blocks": foot}
    near = sorted(set(foot) | _ring(set(foot)))
    taken = occupied(near)
    if taken:
        names = sorted({f for fs in taken.values() for f in fs})
        return {"ok": False, "why": f"{len(taken)} block{'s' if len(taken) > 1 else ''} in or beside its footprint "
                                    f"already hold{'s' if len(taken) == 1 else ''} an edit in {', '.join(names)}",
                "where": [mid(b) for b in sorted(taken)], "blocks": foot}
    win = sorted(reads(prefab, cell) - set(near))
    taken = occupied_target(win) if win else {}
    if taken:
        return {"ok": False, "why": f"its carries read {len(taken)} block{'s' if len(taken) > 1 else ''} the draft "
                                    f"already edits", "where": [mid(b) for b in sorted(taken)], "blocks": foot}
    return {"ok": True, "why": "", "where": [], "blocks": foot}


def command(mod_folder, name: str, cell, *, dry_run: bool = True, report=None, turn: int = 0) -> list:
    """The ``world-prefab`` argv (after ``python -m ff9mapkit``); ``--turn`` only when the prefab turns."""
    argv = ["world-prefab", str(name), "--cell", f"{int(cell[0])},{int(cell[1])}", "--mod-folder", str(mod_folder)]
    if int(turn or 0):
        argv += ["--turn", str(int(turn))]
    if dry_run:
        argv.append("--dry-run")
    if report is not None:
        argv += ["--report-json", str(report)]
    return argv


def cell_of(x: float, z: float) -> tuple:
    return (math.floor(x / BLOCK), math.floor(-z / BLOCK))
