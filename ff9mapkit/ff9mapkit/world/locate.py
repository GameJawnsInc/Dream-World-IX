"""Decode the FF9 OVERWORLD entrance dispatch: which world blocks/tiles lead to which field (the reliable
``world-locate`` foundation, reverse-engineered from ``EVT_WORLD_WORLD00`` + the Memoria engine).

The mechanism (engine + byte verified): walking onto an event tile (its mesh ``tangent.x`` IDALL has the event
bits set, ``(v & 0xC000) >> 14 != 0``) fires ``ff9.WorldEvent`` → the world ``.eb`` entry(1)/tag-1 dispatcher.
That dispatcher is TWO levels: a top switch on the **vehicle** (``gEventGlobal[190]`` = ControlNo; on-foot is
case 0), then, on foot, an **AREA switch** keyed on the entered tile's IDALL **area** (bits 8-13) ==
:func:`~ff9mapkit.world.extract.decode_id`'s ``area`` == the switch case (the engine copies ``m_GetIDArea`` into
the dispatch key with NO remap). Each area case then branches on the **ScenarioCounter** (``gEventGlobal`` word 0)
before emitting ``Field(dest)`` (MAPJUMP ``0x2B``). So: **tile → area → [(scenario-condition, field)]**, and
separately **area → blocks** (the entrance tiles carried by each world block mesh).

So a place's real overworld location is its entrance AREA's blocks (authoritative, from the meshes), and its
destination is that area's ``Field`` (base game; a deployed journey may ``field_remap`` it). This module never
guessed the wrong blocks the way the old "first Field literal" heuristic did — the area IS the switch key.
"""
from __future__ import annotations

import glob
import re
from pathlib import Path

from .. import config
from . import extract as W

# disc 1 on-foot overworld dispatcher; the AREA switch is an op_0B with this base (cases = IDALL area ids).
WORLD_EB_CONTAINER = "eventbinary/world/us/evt_world_world00.eb"
_AREA_SWITCH_BASE = 2
_OP_EXPR, _OP_FIELD = 0x05, 0x2B
_CMP = {"op18": "<", "op19": ">", "op1A": "<=", "op1B": ">="}


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


def area_to_fields(game=None) -> dict:
    """``{area: [(condition, field_id), ...]}`` -- the on-foot overworld entrance destinations, decoded from the
    world ``.eb`` AREA switch with its ScenarioCounter branches. ``condition`` is ``"default"`` or e.g. ``"SC < 8800"``;
    a field of ``None`` means the area's case emits no ``Field`` (a walkable, non-entrance/spacer area)."""
    from ..eb.model import EbScript
    from ..eb import disasm as D
    s = EbScript(_world_eb_bytes(game))
    fn = next(f for f in s.entry(1).funcs if f.tag == 1)
    ins = list(D.iter_code(s.data, fn.abs_start, fn.abs_end))

    area_sw = next(((i, si) for i in ins if i.is_switch
                    for si in (D.decode_switch(i) or i.switch(),) if si and si.base == _AREA_SWITCH_BASE), None)
    if area_sw is None:
        raise ValueError("could not find the on-foot AREA switch (op_0B base 2) in the world dispatcher")
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


def area_to_blocks(disc: int = 1, game=None) -> dict:
    """``{area: [(x, y), ...]}`` -- every world block whose mesh carries an entrance tile of that IDALL area
    (the AUTHORITATIVE geography: the area is the dispatch switch key, so these blocks are exactly where the
    place's overworld entrance sits). Reads all disc blocks; a bit slow (~260 meshes)."""
    out: dict = {}
    for (x, y) in W.list_blocks(disc=disc, game=game):
        for pe in W.block_summary(W.read_block(x, y, disc=disc, game=game))["place_entrances"]:
            out.setdefault(pe["area"], set()).add((x, y))
    return {a: sorted(bs) for a, bs in out.items()}


def field_names() -> dict:
    """``{field_id: name}`` from the dev field manifest if present (``reference/field-manifest.tsv``); ``{}`` on a
    shipped/clean install (names are a dev convenience -- the field IDs + block clusters are the authoritative output)."""
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


def locate(disc: int = 1, game=None) -> list:
    """The full overworld entrance table: a list of ``{area, blocks, destinations}`` sorted by area, where
    ``destinations`` is ``[{condition, field, name}]``. Joins :func:`area_to_blocks` (geography) with
    :func:`area_to_fields` (dispatch) + optional :func:`field_names`."""
    blocks = area_to_blocks(disc=disc, game=game)
    fields = area_to_fields(game=game)
    names = field_names()
    rows = []
    for area in sorted(set(blocks) | set(fields)):
        dests = [{"condition": c, "field": f, "name": names.get(f)} for (c, f) in fields.get(area, [])]
        rows.append({"area": area, "blocks": blocks.get(area, []), "destinations": dests})
    return rows
