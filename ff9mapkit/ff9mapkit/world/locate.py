"""Decode the FF9 OVERWORLD entrance dispatch: which world CELLS (and so blocks) lead to which field (the
``world-locate`` foundation, reverse-engineered from ``EVT_WORLD_WORLD00`` + the Memoria engine).

The mechanism (engine + byte verified): walking onto a terrain tile whose IDALL ``event`` bits are set
(``(v & 0xC000) >> 14 != 0``) fires ``ff9.WorldEvent(cellX, cellZ, id)``, which packs the CELL TAG
``0x8000 | (cellZ<<8 & 0x3F00) | (cellX<<2 & 0xFC) | (id&3)`` (ff9.cs ``WorldEvent``; the cell from
``w_worldPos2Cell`` = ``(int)(x/32), (int)(z/-32)``) and GetIP-matches it against object-0 (entry 0)'s function
TAGS in the loaded world dispatcher ``.eb``. The matched trigger func sets ``Map.Byte[39] = <case>`` (the
``D5 27 7D <lo> <hi>`` literal) and ``RunScriptAsync(6,1,11)`` -> the shared entry-1/tag-1 dispatcher, whose
base-2 switch reads THAT case, branches on the ScenarioCounter (``gEventGlobal`` word 0), then emits
``Field(dest)`` (MAPJUMP ``0x2B``). So: **cell -> trigger tag -> Byte[39] case -> [(scenario-condition, field)]**.

⚠ The dispatch key derives from the tile's CELL COORDINATES -- the tile's IDALL ``area`` bits are NOT part of it.
They are a coarse regional tag shared across whole neighbourhoods (Object-mesh census, 2026-07-25). This module's
pre-census revision joined geography by those area bits and misplaced real places (case numbers coincide with
unrelated area numbers: it filed Alexandria's tile cluster under ``Marsh/Entrance`` 650 and Qu's Marsh under
``Treno/Gate`` 908). Geography now comes from the object-0 cell tags themselves; naming from the engine's
``navipos`` landmark-marker table (:data:`NAVIPOS`, verified to land inside the census' structure bboxes to <2u).
Evidence + reproduction scripts: ``studies/overworld-topography/object-census/`` (``area_truth.py``, ``README.md``).
"""
from __future__ import annotations

import glob
import math
import re
from pathlib import Path

from .. import config
from . import extract as W

# disc-1 free-roam overworld dispatcher; entry-1/tag-1 holds the dispatch switch (op_0B base 2, cases = Byte[39]).
WORLD_EB_CONTAINER = "eventbinary/world/us/evt_world_world00.eb"
_AREA_SWITCH_BASE = 2
_OP_EXPR, _OP_FIELD = 0x05, 0x2B
_CMP = {"op18": "<", "op19": ">", "op1A": "<=", "op1B": ">="}

# The engine's navipos landmark-marker table (ff9.cs, ``navipos[2,64]`` dim 1 -- the full-world set; dim 0 is the
# Mist-continent minimap subset with identical world coords). ``(loc, name, tx, ty)``; world XZ = tx/256, ty/256.
# Interop constants transcribed from the decompiled engine (no SE binary bytes); names are game knowledge. The
# census verified each obj-marked entry lands inside its Object-mesh structure bbox to <2u.
NAVIPOS = (
    (0, "Alexandria Harbour", 345560, -173564),
    (1, "Alexandria", 328680, -178910),
    (2, "Evil Forest", 311680, -191323),
    (3, "Ice Cavern", 306501, -204700),
    (4, "Quan's Dwelling", 358057, -236117),
    (5, "Treno", 328239, -245345),
    (6, "South Gate", 300090, -230918),
    (7, "South Gate", 300090, -230918),
    (8, "South Gate", 300090, -230918),
    (9, "South Gate", 300090, -230918),
    (10, "South Gate", 300090, -230918),
    (11, "Ice Cavern", 297056, -215824),
    (12, "Observatory Mountain", 284585, -203240),
    (13, "Dali", 280253, -206433),
    (14, "North Gate", 265584, -193337),
    (15, "North Gate", 265584, -193337),
    (16, "Gizamaluke's Grotto", 254112, -205731),
    (17, "Burmecia", 246186, -182059),
    (18, "Cleyra", 229548, -198479),
    (19, "Chocobo's Forest", 278526, -243814),
    (20, "Gizamaluke's Grotto", 250721, -224068),
    (21, "Qu's Marsh", 239319, -241340),
    (22, "Pinnacle Rocks", 241248, -279572),
    (23, "Lindblum Dragon's Gate", 234496, -260825),
    (24, "Lindblum", 229342, -278220),
    (25, "Lindblum Harbour", 221494, -282188),
    (26, "Earth Shrine", 299041, -94130),
    (27, "Desert Palace", 303345, -71006),
    (28, "Mognet Central", 275329, -27154),
    (29, "Qu's Marsh", 262598, -79454),
    (30, "Black Mage Village", 244288, -100007),
    (31, "Fossil Roo", 235576, -102928),
    (32, "Conde Petie", 229037, -90135),
    (33, "Madain Sari", 233101, -48649),
    (34, "Conde Petie Mountain Path", 226757, -59696),
    (35, "Conde Petie Mountain Path", 217668, -70533),
    (36, "Iifa Tree", 200097, -82107),
    (37, "Chocobo's Lagoon", 151941, -289631),
    (38, "Wind Shrine", 131348, -231368),
    (39, "Daguerreo", 97345, -262526),
    (40, "Qu's Marsh", 78285, -239115),
    (41, "Oeilvert", 101014, -204347),
    (42, "Landing Site", 83497, -145686),
    (43, "Water Shrine", 57147, -155460),
    (44, "Ipsen's Castle", 49042, -121464),
    (45, "Qu's Marsh", 87500, -125280),
    (46, "Shimmering Island", 116381, -81633),
    (47, "Esto Gaza", 95358, -61173),
    (48, "Fire Shrine", 129014, -29732),
    (54, "Air Garden", 334274, -164988),
    (55, "Air Garden", 320846, -111720),
    (56, "Air Garden", 119880, -159015),
    (57, "Air Garden", 120775, -275601),
    (58, "Air Garden", 187061, -151788),
)


def landmarks() -> list:
    """The navipos landmark markers as ``[{loc, name, world: (x, z), block: (bx, by)}]`` -- the engine's own
    world-landmark naming table (offline; no install needed). ``block`` is the 64u world block under the marker."""
    out = []
    for loc, name, tx, ty in NAVIPOS:
        wx, wz = tx / 256.0, ty / 256.0
        out.append({"loc": loc, "name": name, "world": (wx, wz),
                    "block": (int(wx // W.BLOCK_SIZE), int(-wz // W.BLOCK_SIZE))})
    return out


def nearest_landmark(wx: float, wz: float) -> dict:
    """The navipos marker nearest to world ``(wx, wz)``, with ``dist`` added (world units). A LABEL with an honest
    error bar, not identity -- callers should surface the distance (entrances sit 5-50u from their marker)."""
    best, bd = None, None
    for lm in landmarks():
        d = math.hypot(lm["world"][0] - wx, lm["world"][1] - wz)
        if bd is None or d < bd:
            best, bd = lm, d
    return {**best, "dist": bd}


def _world_eb_bytes(game=None) -> bytes:
    """The disc-1 overworld dispatcher ``.eb`` bytes (``EVT_WORLD_WORLD00``) from the install's p0data (p0data7)."""
    from ..extract import _unitypy
    _unitypy()
    sa = config.find_game_path(game) / "StreamingAssets"
    for path in sorted(glob.glob(str(sa / "p0data*.bin")),
                       key=lambda p: (0 if "p0data7." in Path(p).name else 1, p)):
        try:
            import UnityPy
            env = UnityPy.load(path)
        except Exception:                                    # noqa: BLE001 -- non-bundle / odd file, keep scanning
            continue
        for o in env.objects:
            if o.type.name != "TextAsset" or WORLD_EB_CONTAINER not in (getattr(o, "container", None) or "").lower():
                continue
            d = o.read()
            m = d.m_Script
            return m.encode("utf-8", "surrogateescape") if isinstance(m, str) else bytes(m)
    raise ValueError(f"overworld dispatcher {WORLD_EB_CONTAINER!r} not found in StreamingAssets/p0data*.bin "
                     f"-- is this a full FF9 install?")


def _sc_condition(expr: str) -> str | None:
    """Parse a ScenarioCounter gate ``op_05{ opDC(0) op7D(lo,hi) <cmp> ... }`` into e.g. ``"SC < 8800"``; else None."""
    if "opDC(0)" not in expr:
        return None
    m = re.search(r"opDC\(0\)\s+op7D\((\d+),(\d+)\)\s+(op1[89AB])", expr)
    if not m:
        return "SC (gated)"
    lo, hi, op = int(m.group(1)), int(m.group(2)), m.group(3)
    return f"SC {_CMP.get(op, '?')} {lo + hi * 256}"


def case_to_fields(game=None) -> dict:
    """``{case: [(condition, field_id), ...]}`` -- the on-foot overworld entrance DESTINATIONS, decoded from the
    world ``.eb`` entry-1 dispatch switch (base 2; a case == the ``Map.Byte[39]`` value a cell's trigger func set,
    NOT a tile IDALL area) with its ScenarioCounter branches. ``condition`` is ``"default"`` or e.g. ``"SC < 8800"``;
    a field of ``None`` means the case's arm emits no ``Field`` (e.g. Chocobo's Forest hands off to its own
    handler, and high cases are dead/bare arms)."""
    from ..eb.model import EbScript
    from ..eb import disasm as D
    s = EbScript(_world_eb_bytes(game))
    fn = next(f for f in s.entry(1).funcs if f.tag == 1)
    ins = list(D.iter_code(s.data, fn.abs_start, fn.abs_end))

    area_sw = next(((i, si) for i in ins if i.is_switch
                    for si in (D.decode_switch(i) or i.switch(),) if si and si.base == _AREA_SWITCH_BASE), None)
    if area_sw is None:
        raise ValueError("could not find the dispatch switch (op_0B base 2) in the world dispatcher")
    _, si = area_sw

    edges = [ed for ed in si.edges if not ed.is_default]
    order = sorted({ed.target for ed in edges})              # case bodies span [target, next distinct target)
    idx_at = lambda off: next((k for k, i in enumerate(ins) if i.off >= off), len(ins))
    out: dict = {}
    for ed in edges:
        lo = idx_at(ed.target)
        nxt = next((t for t in order if t > ed.target), None)
        hi = idx_at(nxt) if nxt is not None else min(lo + 60, len(ins))
        branches, cond = [], None
        for k in range(lo, hi):
            i = ins[k]
            if i.op == _OP_EXPR and i.args and "opDC(0)" in str(i.args[0]):
                cond = _sc_condition(str(i.args[0]))
            elif i.op == _OP_FIELD:
                branches.append((cond or "default", i.imm(0)))
                cond = None
            elif i.op == 0x01:                               # unconditional JMP: the else branch follows
                cond = None
        out[ed.value] = branches or [("default", None)]
    return out


area_to_fields = case_to_fields    # pre-census name (the cases were never IDALL areas) -- kept for compatibility


def case_to_cells(game=None) -> dict:
    """``{case: [(cell_x, cell_z, event), ...]}`` -- the on-foot overworld entrance GEOGRAPHY, decoded from the
    world dispatcher's object-0 cell-tag trigger functions (the AUTHORITATIVE source: ``ff9.WorldEvent`` GetIP-
    matches the walked cell's packed tag against exactly these). ``case`` is the ``Byte[39]`` literal the trigger
    body sets; several tags may alias ONE body (a multi-cell entrance, e.g. Lindblum's four Hunter's-Gate cells)
    and resolve through the shared code offset. Triggers that set no ``Byte[39]`` at all (scripted world events)
    are grouped under key ``None``. Cases 57+ exist as triggers but have no dispatch-switch arm (no walk-on warp)."""
    from ..eb.model import EbScript
    from .entrance import unpack_cell_tag, _BYTE39_PAT
    s = EbScript(_world_eb_bytes(game))
    funcs = s.entry(0).funcs
    case_at = {}                                             # the non-empty func at each offset owns the body
    for f in funcs:
        body = s.data[f.abs_start:f.abs_end]
        j = body.find(_BYTE39_PAT)
        if j >= 0 and j + 5 <= len(body):
            case_at[f.abs_start] = body[j + 3] | (body[j + 4] << 8)
    out: dict = {}
    for f in funcs:
        cell = unpack_cell_tag(f.tag)
        if cell is None:
            continue
        out.setdefault(case_at.get(f.abs_start), []).append(cell)
    return {c: sorted(cs) for c, cs in out.items()}


def case_to_blocks(game=None) -> dict:
    """``{case: [(x, y), ...]}`` -- every world block containing an entrance cell of that dispatch case (derived
    from :func:`case_to_cells`; 32u cells, 64u blocks). The true place->blocks geography."""
    from .entrance import cell_to_block
    return {c: sorted({cell_to_block(cx, cz) for (cx, cz, _e) in cells})
            for c, cells in case_to_cells(game=game).items()}


def field_names() -> dict:
    """``{field_id: name}`` from the dev field manifest if present (``reference/field-manifest.tsv``); ``{}`` on a
    shipped/clean install (names are a dev convenience -- the field IDs + cell clusters are the authoritative output)."""
    for base in (Path(config.__file__).resolve().parents[2], Path.cwd()):
        mf = base / "reference" / "field-manifest.tsv"
        if mf.is_file():
            names = {}
            for ln in mf.read_text(encoding="utf-8", errors="replace").splitlines():
                p = ln.rstrip("\n").split("\t")
                if len(p) >= 3 and p[1].isdigit():
                    names[int(p[1])] = p[2]
            return names
    return {}


def locate(game=None) -> list:
    """The full overworld entrance table: a list of ``{case, cells, blocks, landmark, destinations}`` sorted by
    case, joining :func:`case_to_cells` (geography -- the object-0 cell tags) with :func:`case_to_fields`
    (dispatch) + optional :func:`field_names`. ``landmark`` is :func:`nearest_landmark` of the entrance-cell
    centroid (name + distance; None for a case with no cells). Rows with destinations but no cells are scripted/
    return destinations with no walk-on tile; the trailing ``case None`` row (if present) collects cell triggers
    that set no dispatch case (scripted world events, e.g. boat landings)."""
    from .entrance import cell_to_block, cell_world_center
    cells_by = case_to_cells(game=game)
    fields = case_to_fields(game=game)
    names = field_names()
    rows = []
    for case in sorted(set(cells_by) | set(fields), key=lambda c: (c is None, c if c is not None else 0)):
        cells = cells_by.get(case, [])
        blocks = sorted({cell_to_block(cx, cz) for (cx, cz, _e) in cells})
        lm = None
        if cells:
            ws = [cell_world_center(cx, cz) for (cx, cz, _e) in cells]
            lm = nearest_landmark(sum(w[0] for w in ws) / len(ws), sum(w[1] for w in ws) / len(ws))
        dests = [{"condition": c, "field": f, "name": names.get(f)} for (c, f) in fields.get(case, [])]
        rows.append({"case": case, "cells": cells, "blocks": blocks, "landmark": lm, "destinations": dests})
    return rows
