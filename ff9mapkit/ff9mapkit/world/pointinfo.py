"""What is at a world point: the facts the World tab's 3D pick shows (editor rung A1).

``studies/overworld-editor/PLAN.md`` rung A1. Everything here is an existing kit answer joined at one point, never a
new rule:

* **the coordinate triple** the kit speaks (the authoring-ff9-overworld skill): world ``(x, z)`` wrapped,
  block ``(floor(x/64), floor(-z/64))``, cell ``(floor(x/32), floor(-z/32))``;
* **the ground the engine gives you there** -- :func:`placement.place` (the sky ray the debug teleport and an
  arrival use) over the block's parts as :func:`render.cell_meshes` resolves them, so the ground query reads the
  very parts the view drew; its IDALL decoded (topograph, area, event), whether that topograph is walkable on foot,
  the canopy sink on a forest tile, and every walkable sheet on the vertical (:func:`placement.all_sheets`: more
  than one is the stacked-sheet defect class);
* **who owns the block's files in the game**: the engine resolves each part file through ``Memoria.ini``'s
  ``FolderNames`` on its own, highest priority first, so a higher folder can hide the shown folder's part, and a
  folder missing from ``FolderNames`` is not read at all. The view draws one folder over stock; this says when the
  game would draw something else;
* **the deploy ledger's last row** for the block (``.ff9world.jsonl``: which verb wrote it, when);
* **the nearest landmark** (:func:`locate.nearest_landmark`, a label with its distance, not an identity).

Read-only. Pure Python over the files; the World tab calls it on a worker thread.
"""

from __future__ import annotations

import math
from pathlib import Path

from . import frames as F
from . import mesh as M
from . import placement as P
from . import render as R

#: the party stands this far below the surface on a canopy tile (THE CANOPY STEP LAW; topographs 36-38)
CANOPY_SINK = 1.171875


def _walk_topographs():
    from .entrance import _WALK_TOPO
    return _WALK_TOPO


def stack_folders(game) -> list | None:
    """``Memoria.ini`` ``FolderNames``, highest priority first; ``None`` when the ini cannot be read (unknown, which
    is not the same as empty)."""
    from ..deploystack import parse_folder_names
    ini = Path(game) / "Memoria.ini"
    if not ini.is_file():
        return None
    return parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore"))


def _part_file(game, folder, disc, bx, by, part) -> Path:
    return (Path(game) / folder / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
            / f"Block[{bx}][{by}] {part}.ff9mesh")


def owners(site, bx, by, drawn, *, stack=None) -> dict:
    """Who supplies each part at block ``(bx, by)``: ``{"shown": folder, "in_stack": bool | None, "parts": {part:
    owner}, "hidden": [(part, owner)]}``. ``owner`` is the highest-priority ``FolderNames`` folder holding the part's
    file, else ``"stock"``. ``drawn`` = the parts the view drew (``{part: "folder" | "stock"}``); ``hidden`` lists each
    part the game takes from somewhere the view did not."""
    site = site.resolved()
    shown = Path(site.mod_root).name if site.mod_root is not None else site.mod_folder
    stack = stack_folders(site.game) if stack is None else stack
    out = {"shown": shown, "in_stack": None if stack is None else shown in stack, "parts": {}, "hidden": []}
    wbx = M.wrap_block_col(bx)
    for part in site.parts:
        # the engine's file for this part: the first FolderNames folder holding it (None: no folder does)
        owner = next((f for f in stack or () if _part_file(site.game, f, site.disc, wbx, by, part).is_file()), None)
        view_src = None if part not in drawn else (shown if drawn[part] == "folder" else "stock")
        if owner is None and view_src is None:
            continue
        out["parts"][part] = owner or view_src
        if owner is not None and owner != view_src:
            out["hidden"].append((part, owner))
    return out


def last_ledger_row(site, bx, by) -> dict | None:
    """The shown folder's last ledger row for block ``(bx, by)`` on the site's disc: ``{verb, utc, part}``, or None."""
    site = site.resolved()
    root = Path(site.mod_root) if site.mod_root is not None else site.game / site.mod_folder
    last = None
    for row in M.read_ledger(root):
        if row.get("cell") == [M.wrap_block_col(bx), by] and row.get("write_disc") == site.disc:
            last = row
    if last is None:
        return None
    tag = last.get("pipeline") or {}
    verb = tag.get("verb") or M.ledger_verb(last.get("argv"))
    return {"verb": verb, "utc": last.get("utc"), "part": last.get("part"), "removed": last.get("op") == "remove"}


def point_info(site, wx: float, wz: float, *, stack=None, landmark: bool = True) -> dict:
    """Every fact the 3D pick shows for world ``(wx, wz)`` (see the module docstring). ``site`` is the
    :class:`render.RenderSite` the view drew; ``stack`` overrides ``FolderNames`` (the test seam)."""
    from .extract import decode_id
    site = site.resolved()
    wx, wz = F.wrap_world_xz(wx, wz)
    bx, by = F.world_to_block(wx, wz)
    by = min(by, M.GRID_ROWS - 1)
    lx, lz = F.world_to_block_local(wx, wz, bx, by)
    info = {"world": (wx, wz), "block": (bx, by), "cell": (math.floor(wx / 32.0), math.floor(-wz / 32.0)),
            "local": (lx, lz)}
    meshes = R.cell_meshes(site, bx, by, stock=True)
    drawn = {part: ("folder" if R.live_path(site, bx, by, part).is_file() else "stock") for part, _ in meshes}
    ground = {"modelled": True, "note": ""}
    if not meshes:
        ground.update(y=0.0, part="MISS", idall=0, topograph=None)
    else:
        meshlist = P.build_meshlist(dict(meshes))
        try:
            P.check_order_exceptions(meshlist)
        except ValueError as e:
            ground.update(modelled=False, note=str(e))
        if ground["modelled"]:
            gy, gpart, idall, topo = P.place(meshlist, lx, lz, 0.0, sky=True)
            ground.update(y=gy, part=gpart, idall=idall, topograph=topo)
            sheets = P.all_sheets(meshlist, lx, lz, strict=True)
            ground["sheets"] = [(round(y, 3), name, t) for (y, name, _i, t) in sheets]
            # placement.census's stacked-sheet rule, at this one point: >= 2 WALKABLE sheets whose top two stand
            # STACK_GAP_MIN apart; "shadowed" = the engine grounds you below the top one (an inversion)
            walk = sorted((y for (y, _n, _i, t) in sheets if t in P.WALK_OK), reverse=True)
            stacked = len(walk) >= 2 and walk[0] - walk[1] >= P.STACK_GAP_MIN
            ground["stacked"] = stacked
            ground["shadowed"] = bool(stacked and gpart != "MISS" and walk[0] - gy > P.SHEET_DEDUP_EPS)
    if ground.get("part") not in (None, "MISS"):
        d = decode_id(ground["idall"])
        ground.update(area=d["area"], event=d["event"],
                      walkable=ground["topograph"] in _walk_topographs(),
                      canopy=ground["topograph"] in M.CANOPY_TOPOGRAPHS)
        ground["stand_y"] = ground["y"] - (CANOPY_SINK if ground["canopy"] else 0.0)
    info["ground"] = ground
    info["owners"] = owners(site, bx, by, drawn, stack=stack)
    info["ledger"] = last_ledger_row(site, bx, by)
    if landmark:
        from .locate import nearest_landmark
        lm = nearest_landmark(wx, wz)
        info["landmark"] = {"name": lm["name"], "dist": lm["dist"]}
    return info


def describe(info: dict) -> list:
    """``info`` as the strip's lines: the triple, the ground, the owners, the ledger. Plain words; no markup."""
    wx, wz = info["world"]
    bx, by = info["block"]
    cx, cz = info["cell"]
    lines = [f"x {wx:.2f}, z {wz:.2f} · block {bx},{by} · cell {cx},{cz}"]
    g = info["ground"]
    if not g["modelled"]:
        lines.append("Ground query not modelled here: " + g["note"])
    elif g["part"] == "MISS":
        lines.append("No ground: the engine's ray misses here and drops you to y 0 (a hole, or open sea's edge)")
    else:
        walk = "walkable on foot" if g["walkable"] else "not walkable on foot"
        stand = f", you stand at y {g['stand_y']:.2f} (canopy)" if g["canopy"] else ""
        lines.append(f"Ground y {g['y']:.2f} on {g['part']} · topograph {g['topograph']} ({walk}) · "
                     f"area {g['area']}" + (f" · entrance event {g['event']}" if g["event"] else "") + stand)
        others = [(y, name) for y, name, _t in g.get("sheets", ()) if abs(y - g["y"]) > 1e-3 or name != g["part"]]
        if g.get("shadowed"):
            lines.append("⚠ Walkable sheets stacked here and the engine grounds you on the LOWER one "
                         "(the lawn-under-hill class): " + ", ".join(f"y {y:g} {n}" for y, n, _t in g["sheets"]))
        elif g.get("stacked"):
            lines.append("⚠ Walkable sheets stacked here (the census's stacked-sheet defect): " +
                         ", ".join(f"y {y:g} {n}" for y, n, _t in g["sheets"]))
        elif others:
            lines.append("Also on this vertical: " + ", ".join(f"{n} at y {y:g}" for y, n in others))
    o = info["owners"]
    if o["in_stack"] is False:
        lines.append(f"⚠ {o['shown']} is not in Memoria.ini's FolderNames: the game does not read it")
    if o["hidden"]:
        lines.append("⚠ In game " + ", ".join(f"{part} comes from {who}" for part, who in o["hidden"]) +
                     f", not what this view drew")
    parts = sorted({who for who in o["parts"].values()})
    if parts:
        lines.append("Files from " + ", ".join(parts))
    if info.get("ledger"):
        led = info["ledger"]
        when = (led.get("utc") or "")[:10]
        lines.append(f"Last written by {led['verb'] or 'a writer the ledger does not name'}" + (f" on {when}" if when else ""))
    if info.get("landmark"):
        lm = info["landmark"]
        lines.append(f"Nearest landmark {lm['name']}, {lm['dist']:.0f}u away")
    return lines
