"""Should an ``[[npc]]`` follow ``_shadowparams.STOCK_CASTS`` the way a ``[[prop]]`` does? The census behind
the answer (NPC-STOCK-CASTS.md): every free-standing stock object that wears a NON-accessory model, sorted by
WHERE its Init puts it, with stock's cast verdict per placement.

The selection and the verdict are ``_regen_shadowparams``'s. An object counts when its Init ``SetModel``\\ s a
literal and it is not an ``AttachObject`` target. It is "disabled" when a ``DisableShadow`` block dominates
every exit of its Init (``eb.cfg.FuncFlow``). On top of that, each object gets ONE placement class:

  hidden      a ``HideObject`` dominates every exit of the Init (it appears later, in a scene)
  unbound     the Init's last ``SetPathing`` is 0 (walkmesh-unbound: the frog pond, a perch)
  elevated    ``MoveInstantXZY`` puts it more than TOL off the stock floor under it, or off the walkmesh
  stowed      no ``MoveInstantXZY``; its ``CreateObject`` point is shared by 2+ objects in the field (a pool
              spawn its loop moves out of)
  standing    on the walkmesh: ``MoveInstantXZY`` within TOL of the floor, else a ``CreateObject`` point on it
  unresolved  the position is computed (a local the const-propagation cannot see)

A kit ``[[npc]]`` has only ``pos = [x, z]``, no height and no pathing key, so it is always ``standing``.
Positions come from a const-propagation of the D9/DA/D2 locals through the Init (a union over branches).
The floor comes from ``BgiWalkmesh.height_at`` on the field's own walkmesh.

Reads the install (``$FF9_GAME_PATH`` or the default Steam path); ships no game bytes. Run from ff9mapkit/:

    py ../studies/actor-shadow/npc_standing_census.py [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))

from ff9mapkit import extract  # noqa: E402
from ff9mapkit._modeldb import MODELS  # noqa: E402
from ff9mapkit.eb import EbScript  # noqa: E402
from ff9mapkit.eb.cfg import CfgError, FuncFlow  # noqa: E402
from ff9mapkit.eb.disasm import jump_target  # noqa: E402
from ff9mapkit.scene.bgi import BgiWalkmesh  # noqa: E402

DISABLE, HIDE, ATTACH, INIT_OBJECT, SET_MODEL, DEFINE_PC = 0x80, 0x3A, 0x4C, 0x09, 0x2F, 0x2C
CREATE_OBJECT, MOVE_XZY, MOVE_XZY_EX, SET_PATHING, EXPR = 0x1D, 0xA1, 0xAD, 0xA8, 0x05
TOL = 60                                   # field units between the Init's Y and the floor that still stand
LOCALS = ("D9", "DA", "D2", "D8", "DB", "DC")
CLASSES = ("standing", "elevated", "unbound", "stowed", "hidden", "unresolved", "no-walkmesh")
_TOK = re.compile(r"op([0-9A-F]{2})\(([^)]*)\)|op([0-9A-F]{2})")


def _s16(v):
    return v - 0x10000 if v & 0x8000 else v


def _toks(expr: str) -> list:
    out = []
    for m in _TOK.finditer(expr):
        if m.group(1):
            out.append((m.group(1), [int(a) for a in m.group(2).split(",") if a.strip()]))
        else:
            out.append((m.group(3), []))
    return out


def _value(tk, env):
    """The possible values of a one-operand expression (a literal, or a local already assigned)."""
    if not tk:
        return None
    op, a = tk[0]
    if op == "7D":
        return {_s16(a[0] | (a[1] << 8))}
    if op == "7C":
        return {a[0] - 256 if a[0] >= 128 else a[0]}
    if op == "7E":
        v = a[0] | a[1] << 8 | a[2] << 16 | a[3] << 24
        return {v - (1 << 32) if v & 0x80000000 else v}
    if op in LOCALS:
        return env.get((op, a[0])) or None
    return None


def _arg(ins, k, env):
    if not ins.arg_is_expr[k]:
        return [_s16(ins.args[k])]
    v = _value(_toks(ins.args[k]), env)
    return sorted(v) if v else None


def _init_facts(eb, f0) -> dict:
    """The Init's placement facts: CreateObject (x, z) points, MoveInstantXZY (x, y, z) points, SetPathing
    values in order."""
    env, xz, xyz, path = defaultdict(set), [], [], []
    for i in eb.instrs(f0):
        if i.op == EXPR and i.args and i.arg_is_expr[0]:
            tk = _toks(i.args[0])
            if len(tk) >= 3 and tk[-1][0] == "7F" and tk[-2][0] == "2C" and tk[0][0] in LOCALS:
                v = _value(tk[1:2], env)
                if v:
                    env[(tk[0][0], tk[0][1][0])] |= v
        elif i.op == CREATE_OBJECT and len(i.args) >= 2:
            xs, zs = _arg(i, 0, env), _arg(i, 1, env)
            if xs and zs and len(xs) == len(zs):
                xz += list(zip(xs, zs))
        elif i.op in (MOVE_XZY, MOVE_XZY_EX) and len(i.args) >= 3:
            xs, ys, zs = _arg(i, 0, env), _arg(i, 1, env), _arg(i, 2, env)
            if xs and ys and zs and len(xs) == len(ys) == len(zs):
                xyz += list(zip(xs, ys, zs))
        elif i.op == SET_PATHING:
            path.append(i.imm(0))
    return {"xz": xz, "xyz": xyz, "pathing": path}


def _dominates(eb, f0, op) -> bool:
    """A block holding ``op`` dominates every exit of the Init -- ``_regen_shadowparams``'s test."""
    fl = FuncFlow.build(eb.data, f0.abs_start, f0.abs_end)
    offs = [b.index for b in fl.blocks if any(i.op == op for i in b.instrs)]
    if not offs:
        return False
    dom = fl._dom
    exits = [b.index for b in fl.blocks if dom[b.index]
             and (not b.succs or (b.instrs[-1].op in (0x01, 0x02, 0x03)
                                  and jump_target(b.instrs[-1]) == f0.abs_end))]
    return bool(exits) and any(all((dom[e] >> d) & 1 for e in exits) for d in offs)


def _walkmesh(fid):
    try:
        _bp, _folder, roles, env = extract.find_field(str(fid))
        return BgiWalkmesh.from_bytes(extract._raw_bytes(env.container[roles["bgi"]].read()))
    except Exception:                                   # noqa: BLE001 -- a field with no walkmesh: class it
        return None


def _classify(r, wm, stow) -> str:
    if wm is None:
        return "no-walkmesh"
    if r["hidden"]:
        return "hidden"
    if r["pathing"] and r["pathing"][-1] == 0:
        return "unbound"
    if r["xyz"]:
        ok = [(h := wm.height_at(x, z)) is not None and abs(y - h) <= TOL for x, y, z in r["xyz"]]
        return "standing" if all(ok) else "elevated"
    if r["xz"]:
        if any(tuple(p) in stow for p in r["xz"]):
            return "stowed"
        return "standing" if all(wm.height_at(x, z) is not None for x, z in r["xz"]) else "elevated"
    return "unresolved"


def scan() -> list:
    bundle = extract.EventBundle()
    index = extract.build_field_index(verbose=False)
    fids = sorted(extract.ID_TO_EVT, key=lambda f: (index.get(extract.ID_TO_FBG.get(f, ""), ""), f))
    rows = []
    for fid in fids:                                    # bundle order, so the env LRU loads each bundle once
        data = bundle.eb_for_id(fid)
        if not data:
            continue
        try:
            eb = EbScript.from_bytes(data)
        except Exception:                               # noqa: BLE001 -- a field we can't parse: skip
            continue
        uids, attached = defaultdict(set), set()
        for e in eb.entries:
            if e.empty:
                continue
            for f in e.funcs:
                for ins in eb.instrs(f):
                    if ins.op == INIT_OBJECT and ins.imm(0) is not None:
                        uids[ins.imm(0)].add(ins.imm(1) or ins.imm(0))
                    elif ins.op == ATTACH and ins.imm(0) is not None:
                        attached.add(ins.imm(0))
        here = []
        for e in eb.entries:
            f0 = None if e.empty else e.func_by_tag(0)
            if f0 is None:
                continue
            ins0 = list(eb.instrs(f0))
            sm = next((i for i in ins0 if i.op == SET_MODEL), None)
            if sm is None or sm.imm(0) is None or (uids.get(e.index, set()) | {e.index}) & attached:
                continue
            model = int(sm.imm(0))
            if MODELS.get(model, "").startswith("GEO_ACC_"):
                continue
            try:
                disabled, hidden = _dominates(eb, f0, DISABLE), _dominates(eb, f0, HIDE)
            except CfgError:                            # an Init the flow can't soundly read: no vote
                continue
            here.append({"fid": fid, "entry": e.index, "model": model, "name": MODELS.get(model, "?"),
                         "disabled": disabled, "hidden": hidden,
                         "player": any(i.op == DEFINE_PC for i in ins0), **_init_facts(eb, f0)})
        if not here:
            continue
        wm = _walkmesh(fid)
        pool = Counter(tuple(p) for r in here if not r["xyz"] for p in r["xz"])
        stow = {p for p, k in pool.items() if k >= 2}
        for r in here:
            r["placement"] = _classify(r, wm, stow)
        rows += here
    return rows


def _cd(c: Counter, k) -> str:
    cs, ds = c[(k, False)], c[(k, True)]
    return f"{cs:>4}c/{ds:<3}d" if cs or ds else f"{'.':>10}"


def report(rows: list) -> None:
    tot = Counter((r["placement"], r["disabled"]) for r in rows)
    print(f"{len(rows)} free-standing non-accessory stock objects")
    print("  placement   " + "  ".join(f"{k:>10}" for k in CLASSES))
    print("  all         " + "  ".join(_cd(tot, k) for k in CLASSES))
    by = defaultdict(Counter)
    for r in rows:
        by[r["model"]][r["disabled"]] += 1
    # the per-model verdict _regen_shadowparams bakes: majority, a tie goes to "disabled"
    off = sorted(m for m, c in by.items() if c[True] >= c[False])
    print(f"\n{len(off)} models whose objects mostly disable (the STOCK_CASTS False set), by placement:")
    print(f"  {'model':<18}" + "  ".join(f"{k:>10}" for k in CLASSES))
    for m in off:
        c = Counter((r["placement"], r["disabled"]) for r in rows if r["model"] == m)
        print(f"  {MODELS.get(m, '?')[4:]:<18}" + "  ".join(_cd(c, k) for k in CLASSES))
    never = [m for m in off if not any(r["model"] == m and r["placement"] == "standing" for r in rows)]
    print(f"  -> {len(never)} of {len(off)} never stand on the walkmesh in stock")
    pl = [r for r in rows if r["player"]]
    print(f"\nplayer objects: {len(pl)}, casting {sum(not r['disabled'] for r in pl)}; "
          f"STOCK_CASTS-False models worn by a player: "
          + (", ".join(f"{r['name']} f{r['fid']} {'disabled' if r['disabled'] else 'casts'}"
                       for r in pl if r["model"] in off) or "none"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", help="also write every classified object here")
    a = ap.parse_args()
    rows = scan()
    report(rows)
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
