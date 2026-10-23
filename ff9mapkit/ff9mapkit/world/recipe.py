"""The overworld editor's document (rung C3): a ``world-fuse`` recipe.

Every edit the World tab makes into a draft is one recipe ROW, the ``[[forest]]`` / ``[[mountain]]`` table that
``world-fuse`` composes with the same verb call (``fuse.compose_layout``'s relief runner). :func:`row_for` builds the
row from the very command the tool ran (parsed by the CLI's own parser, so the row cannot say anything the command
did not), the draft's history keeps the rows in the order they were made (``world.draft.history``), and
:func:`dumps` writes them as a TOML ``world-fuse`` reads back: each row carries ``step = N``, because TOML keeps one
array per table and would otherwise lose the order a forest and a mountain were placed in (``fuse.ordered_rows``).

THE ACCEPTANCE (C3): a recipe saved by the editor, composed through the CLI onto the folder the draft was made
from, writes the bytes the editor wrote (``tests/test_worldrecipe.py``).
"""
from __future__ import annotations

import math
import tomllib

#: The tables the editor writes (the rest of a recipe it composes and lists, but does not edit).
EDITOR_TABLES = ("forest", "mountain", "sink", "morph", "island")

HEADER = ("# Dream World IX overworld recipe, written by the World tab.\n"
          "# Compose it onto a mod folder with:  ff9mapkit world-fuse <this file> --mod-folder <folder>\n")


def row_for(argv) -> dict:
    """The recipe row (``{"table": ..., key: value}``) for an editor command (``world-forest`` / ``world-mountain``
    argv, after ``python -m ff9mapkit``, without ``--dry-run``). Defaults are left out, as the command leaves them."""
    from .. import cli
    a = cli.build_parser().parse_args([str(v) for v in argv])
    verb = argv[0]
    if verb == "world-island":
        if a.center is None:
            raise ValueError("an [[island]] row is placed by --center")
        if a.seed is None:
            raise ValueError("an [[island]] row names its --seed (the mint derives one from the centre otherwise)")
        if (a.disc != 1 or a.target_disc is not None or a.skip_mirror or a.beach or a.relief or a.flat
                or a.skip_coastnav or a.area is not None or a.allow_overwrite or a.all_sea_target):
            raise ValueError("an [[island]] row is the plain disc-1 mint the World tab makes")
        row = {"table": "island", "center": [float(v) for v in a.center.split(",")], "seed": float(a.seed)}
        for key, val, dflt in (("radius", a.radius, 24.0), ("lobes", a.lobes, 1), ("height", a.height, 3.2),
                               ("ground", a.ground, "grass")):
            if val != dflt:
                row[key] = val
        return row
    if verb == "world-sink":
        if a.at is None or a.list:
            raise ValueError("a [[sink]] row names its island: --at WX WZ")
        if a.disc != 1 or a.skip_mirror or a.fresh or a.allow_overwrite:
            raise ValueError("a [[sink]] row is the disc-1 sink with its own disc-4 step (no --disc, --skip-mirror, "
                             "--fresh, --allow-overwrite)")
        row = {"table": "sink", "at": [float(v) for v in a.at]}
        if a.cluster:
            row["cluster"] = True
        if a.allow_entrances:
            row["allow_entrances"] = True
        return row
    if verb == "world-transplant":
        from .coastedit import VERBS
        flags = [v for v in VERBS if getattr(a, v.replace("-", "_"), None)]
        if not a.in_place or len(flags) != 1 or a.cell != a.donor:
            raise ValueError("a [[morph]] row is one coast morph in place (--in-place, one verb, --cell = --donor)")
        if a.disc != 1 or a.skip_mirror or a.fresh:
            raise ValueError("a [[morph]] row is the disc-1 morph with its own disc-4 step (no --disc, "
                             "--skip-mirror, --fresh)")
        s0, s1, sd = getattr(a, flags[0].replace("-", "_")).split(":")
        row = {"table": "morph", "cell": [int(v) for v in a.cell.split(",")], "verb": flags[0],
               "window": [[float(v) for v in s0.split(",")], [float(v) for v in s1.split(",")]], "depth": float(sd)}
        if getattr(a, "allow_entrances", False):
            row["allow_entrances"] = True
        return row
    if verb not in ("world-forest", "world-mountain"):
        raise ValueError(f"{verb} has no recipe row")
    if a.near is not None or a.center is None:
        raise ValueError("a recipe row is an exact placement (--center)")
    table = verb.removeprefix("world-")
    row = {"table": table, "center": [float(v) for v in a.center.split(",")], "donor": str(a.donor)}
    if a.rot is not None:
        row["rot"] = float(a.rot)
    if a.spread != 1.0:
        row["spread"] = float(a.spread)
    if a.reach != 96.0:
        row["reach"] = float(a.reach)
    if table == "mountain":
        if a.rock_height != 1.0:
            row["rock_height"] = float(a.rock_height)
        if a.ground != "grass":
            row["ground"] = str(a.ground)
        if a.max_apron_lift is not None or a.foot_course or a.gblend is not None:
            raise ValueError("--max-apron-lift / --foot-course / --gblend have no [[mountain]] row key")
    if a.target_disc is not None or a.disc != 1:
        raise ValueError("a recipe row is a disc-1 edit")
    return row


def label(row: dict) -> str:
    """A row in words, for the history list and the Undo button: ``mountain uaho at 190, -1228``."""
    table = row.get("table", "?")
    name = row.get("donor")
    if table == "island":
        c = row.get("center") or (0, 0)
        return f"island r{_num(row.get('radius', 24))} seed {_num(row.get('seed', 0))} at {_num(c[0])}, {_num(c[1])}"
    if table == "morph":
        c = row.get("cell") or (0, 0)
        return f"{row.get('verb', 'morph')} {_num(row.get('depth', 0))} at block ({c[0]}, {c[1]})"
    if table == "sink":
        at = row.get("at") or (0, 0)
        return f"sink the island at {_num(at[0])}, {_num(at[1])}" + (" (and its cluster)" if row.get("cluster") else "")
    if table in EDITOR_TABLES and name is not None:
        from .donors import load_donors, spec_blocks
        klass = "canopy" if table == "forest" else "massif"
        want = spec_blocks(str(name))
        for r in load_donors():
            if r.get("class") == klass and (want == spec_blocks(r["blocks"]) or want <= spec_blocks(r["blocks"])):
                name = r["name"]
                break
    where = row.get("center") or row.get("near") or row.get("at") or row.get("cell")
    at = f" at {_num(where[0])}, {_num(where[1])}" if where else ""
    return f"{table} {name}{at}" if name is not None else f"{table}{at}"


def _num(v) -> str:
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:g}"


def _value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if not math.isfinite(v):
            raise ValueError(f"a recipe value must be finite, not {v}")
        return repr(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_value(x) for x in v) + "]"
    raise ValueError(f"a recipe value cannot be {type(v).__name__}")


def dumps(rows, *, base: str | None = None) -> str:
    """The recipe as TOML: one ``[[table]]`` per row, in the order given, each with its ``step``. ``base`` names the
    folder it was made on (a comment: compose it onto that folder as the draft found it)."""
    out = [HEADER]
    if base:
        out.append(f"# Made on {base}, as the draft found it.\n")
    for n, row in enumerate(rows, 1):
        table = row["table"]
        out.append(f"\n[[{table}]]\nstep = {n}\n")
        for k, v in row.items():
            if k in ("table", "step"):
                continue
            out.append(f"{k} = {_value(v)}\n")
    return "".join(out)


def loads(text: str) -> list:
    """A recipe's rows in the order ``world-fuse`` composes them (``fuse.ordered_rows``), each with its ``table``.
    Refuses ``[[placement]]`` tables: a fused transplant layout is not an editor recipe."""
    from . import fuse as FU
    doc = tomllib.loads(text)
    if doc.get("placement"):
        raise ValueError("this recipe has [[placement]] tables (a fused transplant layout): compose it with "
                         "world-fuse, the editor does not open it")
    rows = [{"table": table, **{k: v for k, v in row.items() if k != "step"}}
            for table, _i, row in FU.ordered_rows(doc)]
    if not rows:
        raise ValueError("the recipe has no rows (" + ", ".join(f"[[{t}]]" for t in FU.COMPOSE_TABLES
                                                                  if t != "placement") + ")")
    return rows


def dumps_one(row: dict) -> str:
    """One row as a recipe of its own (what the editor composes, one step at a time, when it opens a recipe)."""
    return dumps([row])


def row_cells(row: dict) -> list:
    """The blocks a row can write, a superset (the history snapshots them before the row runs): a relief row's read
    window round its point (``read_deployed_blocks``' rect at the row's reach); any other row, the whole world."""
    from .draft import all_cells
    table = row["table"]
    pt = row.get("center") or row.get("near")
    if table in ("forest", "mountain", "hill") and pt:
        if table == "hill":
            reach = max(96.0, float(row.get("radius", 18.0)) + 10.0)
        else:
            reach = float(row.get("reach", 96.0))
        if "near" in row:
            reach += 24.0                                 # a scan moves the centre (search radius + band)
        wx, wz = (float(v) for v in pt)
        bx0, bx1 = math.floor((wx - reach) / 64.0), math.floor((wx + reach) / 64.0)
        by0, by1 = math.floor(-(wz + reach) / 64.0), math.floor(-(wz - reach) / 64.0)
        return [(bx % 24, by) for by in range(max(by0, 0), min(by1, 19) + 1) for bx in range(bx0, bx1 + 1)]
    return all_cells()
