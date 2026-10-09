"""A CUSTOM FORM CELL'S ENTRANCE IN FORM 2 (engine patch s92; ``world-forms --entrance2``).

An overworld entrance is a set of ground tiles whose IDALL carries event bits (14-15): walking onto one fires
``WorldEvent`` with the cell's tag, and the world script's trigger for that tag picks the destination. The form switch
swaps the walked ground whole, IDALL included (forms lane F1), and the stock game uses exactly that to close Cleyra's
entrance and open the Water Shrine's with the story (F10: 96 -> 0 and 0 -> 257 event samples). An armed custom cell's
form-2 ground is its ``Terrain2``, which the kit starts as a copy of the form-1 ground -- event tiles included -- so its
entrance stays open in both forms until this module says otherwise:

* ``off``  -- the entrance closes when the cell switches: ``Terrain2``'s tiles lose their event bits.
* ``only`` -- the entrance opens only when it switches: the form-1 ``Terrain`` loses them (a form-1-only override,
  which is the point), ``Terrain2`` keeps (or regains) them.
* ``both`` -- undo either: each form's ground regains the event bits the other form's ground has at the same spot.

Only the event bits change: positions, uvs, topograph and area stay, so nothing else about the ground moves. The world
script's trigger is untouched (it stays in every dispatcher; with no tile it never fires).
"""
from __future__ import annotations

import dataclasses

EVENT_MASK = 0xC000
MODES = ("off", "only", "both")


class NoEntrance(ValueError):
    """The cell has no entrance tiles in either form on that disc."""


def _idall(bm, tri) -> int:
    return int(round(bm.tangents[tri[0]][0]))


def _set_event(bm, tri, event: int) -> None:
    for i in tri:
        t = list(bm.tangents[i])
        t[0] = float((int(round(t[0])) & ~EVENT_MASK & 0xFFFF) | ((event & 3) << 14))
        bm.tangents[i] = t


def _copy(bm, name):
    """A deep enough copy to edit tangents without touching ``bm``."""
    from .extract import CH_TAN
    arrays = dict(bm.chan_arrays)
    arrays[CH_TAN] = [list(t) for t in bm.chan_arrays[CH_TAN]]
    return dataclasses.replace(bm, name=name, chan_arrays=arrays)


def event_tris(bm) -> list:
    """The triangles of ``bm`` that carry event bits: ``[(tri, event)]``."""
    out = []
    for t in bm.tris:
        ev = (_idall(bm, t) & EVENT_MASK) >> 14
        if ev:
            out.append((t, ev))
    return out


def _centroid(bm, tri):
    return (sum(bm.verts[i][0] for i in tri) / 3.0, sum(bm.verts[i][2] for i in tri) / 3.0)


def _inside(bm, tri, p) -> bool:
    (a, b, c) = [bm.verts[i] for i in tri]
    d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
    if abs(d) < 1e-12:
        return False
    w0 = ((b[2] - c[2]) * (p[0] - c[0]) + (c[0] - b[0]) * (p[1] - c[2])) / d
    w1 = ((c[2] - a[2]) * (p[0] - c[0]) + (a[0] - c[0]) * (p[1] - c[2])) / d
    return w0 >= -1e-9 and w1 >= -1e-9 and 1 - w0 - w1 >= -1e-9


def clear_events(bm) -> int:
    """Clear every event bit in ``bm`` (in place); returns how many triangles changed."""
    n = 0
    for t, _ev in event_tris(bm):
        _set_event(bm, t, 0)
        n += 1
    return n


def copy_events(dst, src) -> int:
    """Give each ``dst`` triangle with no event bits the event of the ``src`` event triangle under its centroid (plan
    match: both meshes share a frame, and the kit's form-2 ground starts as a copy of the form-1 one). In place; returns
    how many triangles changed."""
    srcs = event_tris(src)
    if not srcs:
        return 0
    boxes = []
    for t, ev in srcs:
        xs = [src.verts[i][0] for i in t]
        zs = [src.verts[i][2] for i in t]
        boxes.append((min(xs), max(xs), min(zs), max(zs), t, ev))
    n = 0
    for t in dst.tris:
        if (_idall(dst, t) & EVENT_MASK) >> 14:
            continue
        cx, cz = _centroid(dst, t)
        for x0, x1, z0, z1, st, ev in boxes:
            if x0 - 1e-6 <= cx <= x1 + 1e-6 and z0 - 1e-6 <= cz <= z1 + 1e-6 and _inside(src, st, (cx, cz)):
                _set_event(dst, t, ev)
                n += 1
                break
    return n


def plan(mod_folder: str, x: int, y: int, mode: str, *, disc: int = 1, game=None) -> dict:
    """What :func:`apply` writes for one disc, nothing written: ``{"writes": {part: bm}, "tags": {...}}``."""
    from . import mesh as M, terrain as T
    from .entrance import read_block_stacked
    from .forms import SWITCHABLE, custom_condition
    if mode not in MODES:
        raise ValueError(f"--entrance2 takes one of {MODES}, not {mode!r}")
    if (x, y) in SWITCHABLE:
        raise ValueError(f"cell ({x},{y}) switches with {SWITCHABLE[(x, y)]}: its form-2 entrance is that place's own "
                         f"-- --entrance2 is for cells armed with world-forms --arm")
    root = T._mod_root(mod_folder, game)
    cond = custom_condition(root, disc, x, y) if root is not None else None
    if not cond:
        raise ValueError(f"Block[{x}][{y}] is not armed on disc {disc}: run world-forms --arm {x} {y} --when "
                         f"\"<condition>\"{'' if disc == 1 else f' --disc {disc}'} first (its form 2 needs a "
                         f"condition)")
    t1 = read_block_stacked(mod_folder, x, y, disc=disc, part="terrain", game=game, missing_ok=True)
    if t1 is None or not getattr(t1, "verts", None):
        raise ValueError(f"Block[{x}][{y}] has no ground (a sea cell): no entrance to switch")
    dep2 = M.deployed_override(mod_folder, x, y, disc=disc, part="Terrain2", game=game)
    t2 = (M.blockmesh_from_ff9mesh(dep2, disc=disc, x=x, y=y, part="Terrain2") if dep2 is not None
          else _copy(t1, f"Block[{x}][{y}] Terrain2"))
    tags1, tags2 = sorted(M.entrance_tags(t1)), sorted(M.entrance_tags(t2))
    if not tags1 and not tags2:
        raise NoEntrance(f"Block[{x}][{y}] has no entrance tiles in either form -- nothing to switch (world-entrance "
                         f"authors one)")
    n1 = n2 = 0
    new1 = _copy(t1, f"Block[{x}][{y}] Terrain")
    new2 = _copy(t2, f"Block[{x}][{y}] Terrain2")
    if mode == "off":
        n2 = clear_events(new2)
    elif mode == "only":
        n2 = copy_events(new2, t1)
        n1 = clear_events(new1)
    else:
        n1 = copy_events(new1, t2)
        n2 = copy_events(new2, t1)
    writes = {}
    if n1:
        writes["Terrain"] = new1
    if n2 or dep2 is None:
        writes["Terrain2"] = new2                          # a cell is armed only once its Terrain2 exists
    return {"disc": disc, "cell": [x, y], "condition": cond, "mode": mode, "writes": writes,
            "changed": {"Terrain": n1, "Terrain2": n2},
            "tags": {"form1": sorted(M.entrance_tags(new1)), "form2": sorted(M.entrance_tags(new2))},
            "tags_before": {"form1": tags1, "form2": tags2}}


def apply(mod_folder: str, x: int, y: int, mode: str, *, disc: int = 1, game=None, dry_run: bool = False,
          replay_disc4: bool = True) -> dict:
    """Plan (and unless ``dry_run`` write) the form-2 entrance of armed custom cell ``(x, y)``; on disc 1, replayed on
    disc 4's own ground when the cell is armed there too. Every disc is planned before the first write."""
    from . import mesh as M, terrain as T
    from .forms import custom_condition
    plans = [plan(mod_folder, x, y, mode, disc=disc, game=game)]
    if disc == 1 and replay_disc4:
        root = T._mod_root(mod_folder, game)
        if root is not None and custom_condition(root, 4, x, y):
            try:
                plans.append(plan(mod_folder, x, y, mode, disc=4, game=game))
            except NoEntrance:                      # disc 4's own ground can lack the entrance: nothing to replay
                plans[0]["disc4"] = "this cell has no entrance tiles on disc 4: nothing to replay there"
        else:
            plans[0]["disc4"] = "not armed on disc 4: disc 4 keeps this cell as it is (arm it there with --disc 4)"
    if not dry_run:
        for p in plans:
            p["written"] = [str(M.deploy_override(bm, mod_folder=mod_folder, game=game, part=part, disc=p["disc"]))
                            for part, bm in p["writes"].items()]
    return {"plans": plans, "dry_run": dry_run}


def receipt(res) -> list:
    lines = []
    head = {"off": "the entrance CLOSES when the cell switches",
            "only": "the entrance OPENS only when the cell switches",
            "both": "the entrance is open in both forms"}
    for p in res["plans"]:
        x, y = p["cell"]
        lines.append(f"Block[{x}][{y}] (Disc{p['disc']}): {head[p['mode']]} (when {p['condition']})")
        lines.append(f"  entrance tile tags: form 1 {p['tags']['form1'] or 'none'}; "
                     f"form 2 {p['tags']['form2'] or 'none'}")
        ch = ", ".join(f"{k} {v} tris" for k, v in p["changed"].items() if v) or "nothing to change"
        lines.append(f"  event bits changed: {ch}")
        if "Terrain" in p["writes"]:
            lines.append("  note: the form-1 Terrain override is FORM 1 ONLY on purpose: the form-2 ground has the "
                         "entrance")
        if p.get("disc4"):
            lines.append(f"  disc 4: {p['disc4']}")
        for w in p.get("written", []):
            lines.append(f"  wrote {w}")
    return lines


def entrance_centres(bm) -> list:
    """World ``(x, z)`` of each event triangle's centroid (a read point for a harness walk)."""
    from .extract import block_world_origin
    ox, oz = block_world_origin(bm.x, bm.y)
    return [(round(_centroid(bm, t)[0] + ox, 3), round(_centroid(bm, t)[1] + oz, 3), ev) for t, ev in event_tris(bm)]

