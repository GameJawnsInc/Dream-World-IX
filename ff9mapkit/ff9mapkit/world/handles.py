"""THE HANDLE TABLE (overworld editor rung B2): each carry verb's handles, declared once.

A handle is one of a verb's own parameters a person turns: a carry's centre, donor, angle and sizes. Each is declared
here ONCE -- its flag, type, default and help; its range and the interior constant that is its ceiling; the catalogue
class its picker lists; and which surfaces carry it -- and every surface reads this table:

- ``cli``: argparse. The verbs' parsers add their handles with :func:`add_arguments` (the plumbing flags -- the mod
  folder, the disc, ``--dry-run``, ``--report-json`` -- are not handles and stay in ``cli.py``).
- ``row``: ``world-fuse``'s ``[[table]]`` row. The keys it allows are :func:`row_keys`.
- ``gui``: the World tab's cards. Their spins stop at :meth:`Handle.range`, their donor pickers list
  :attr:`Handle.catalogue`, and each card's ``HANDLES`` names the widget (or the rule) that sets each one.

A law in a docstring is a wish: ``tests/test_world_handles.py`` fails when a handle exists in one surface only, and
when a card's range or catalogue strays from the table's.

The verbs still enforce their own ceilings (``interior.carve_*``): a row and the command refuse past one in the verb's
own words, and a handle's ``ceiling`` names the constant they enforce, read when asked (never copied here).

The help texts are the verbs' own, carried over verbatim from the parsers they replaced.
"""
from __future__ import annotations

from dataclasses import dataclass

#: the surfaces a handle can be on
SURFACES = ("cli", "row", "gui")


def _grounds():
    from .grassland import GROUNDS
    return tuple(GROUNDS)


@dataclass(frozen=True)
class Handle:
    name: str                     # the row key, and the argparse dest
    flag: str                     # the CLI flag
    type: type | None = None
    default: object = None
    metavar: str | None = None
    choices: object = None        # a tuple, or a callable that returns one (called when the parser is built)
    action: str | None = None     # an argparse action ("append"); else a plain store
    group: str | None = None      # "where": the required, mutually exclusive --center / --near
    lo: float | None = None
    hi: float | None = None
    ceiling: str | None = None    # the interior constant that is the handle's top (read when asked, never copied)
    wraps: bool = False           # an angle: hi is lo again
    catalogue: str | None = None  # the donors.toml class the picker lists (its qualified rows)
    surfaces: str = "cli row"
    help: str = ""

    def on(self, surface: str) -> bool:
        return surface in self.surfaces.split()

    def top(self):
        """The handle's top: its ceiling constant's value (read now, from the verb that enforces it), else ``hi``."""
        if self.ceiling:
            from . import interior as IN
            return float(getattr(IN, self.ceiling))
        return self.hi

    def range(self) -> tuple:
        """``(lo, top)``: where a card's spin stops."""
        return self.lo, self.top()


H = Handle

HANDLES = {
    "forest": (
        H("center", "--center", metavar="WX,WZ", group="where", surfaces="cli row gui",
          help="EXACT blob centre in world coords (gated, no scan)"),
        H("near", "--near", metavar="WX,WZ", group="where", surfaces="cli row",
          help="scan a ~80u window around this point for the best lawful plain-grass placement"),
        H("donor", "--donor", default="15,15", metavar="BX,BY", catalogue="canopy", surfaces="cli row gui",
          help="real block whose canopy to carry: the largest topo-37 blob touching it whose rim meets only grass,"
               " gathered whole across block borders (default 15,15, the July donor; `world-donors --class canopy`"
               " lists the census-qualified ones). A blob that meets rock or other ground refuses: carried alone "
               "it would leave an open, unwalled edge."),
        H("spread", "--spread", type=float, default=1.0, metavar="S", lo=1.0, ceiling="FOREST_SPREAD_MAX",
          surfaces="cli row gui",
          help="scale the canopy S times wider in plan (1.0-1.5) about its centre, heights, UVs and topographs "
               "carried: a bigger forest from the same donor, its curtains still vertical. The step law and the "
               "walk-in gate judge the result as usual. In-game kept to x1.5 (terrain study X3). Default 1.0 = the"
               " verbatim carry."),
        H("rot", "--rot", type=float, metavar="DEG", lo=0.0, hi=360.0, wraps=True, surfaces="cli row gui",
          help="turn the canopy to ANY angle about its centre (degrees, clockwise seen from above, as "
               "world-mountain --rot); its texture turns with it, the grass stays on its grid and the zip round "
               "the rim is minted fresh and gated. Default 0."),
        H("reach", "--reach", type=float, default=96.0, surfaces="cli row",
          help="deployed-block load window around the point in units (default 96)"),
    ),
    "mountain": (
        H("center", "--center", metavar="WX,WZ", group="where", surfaces="cli row gui",
          help="EXACT massif centre in world coords, rotation 0 (gated, no scan)"),
        H("near", "--near", metavar="WX,WZ", group="where", surfaces="cli row",
          help="scan a ~20u window around this point for the best lawful plain-grass placement (exact 90-deg "
               "rotations as fallbacks)"),
        H("donor", "--donor", default="0,0", metavar="BX[,-BX1],BY[-BY1]", catalogue="massif",
          surfaces="cli row gui",
          help="real block(s) whose rock massif to carry: one block (default 0,0 = Uaho) or a rect for a massif "
               "that straddles a border (the target sizes itself to a multi-block span automatically). The "
               "qualified-donor catalog is `ff9mapkit world-donors --class massif`; a NEW donor needs its own "
               "anatomy pass first (studies/overworld-topography/README.md)."),
        H("max_apron_lift", "--max-apron-lift", type=float, metavar="U", surfaces="cli",
          help="cap the grass apron's rise toward a high donor foot at U units; outer-rim columns still higher "
               "CONFORM DOWN (the carried bottom wall row stretches, uv kept -- THE WALL V CORNER-ROLE LAW) so "
               "flat host ground meets the wall at the crease instead of minting a grass knoll against mid-wall "
               "(the R4 west-seam defect). DOWN-only; aperture/ensemble columns exempt. Default: no cap (the "
               "frozen identity baselines' behavior)."),
        H("foot_course", "--foot-course", metavar="X0,Z0,X1,Z1[,PULL[,TOP]]", action="append", surfaces="cli",
          help="world rect (repeatable) where the massif gets a synthetic ROCK FOOT COURSE instead of a grass "
               "apron: rim nodes inside the rect leave the apron field (the lawn stays flat), the hole hugs the "
               "rim (THE PROFILE LAW: the toe CONTINUES the face's own slope instead of skirting), and the zip "
               "annulus there emits as blocked topo-49 r10-tile rock, fringe pinned at the lawn line -- except "
               "where the rim sits at lawn height (the mountain has ended: grass, never rock paint on flat "
               "ground). Optional PULL steepens the carried flank inside the rect: horizontal pull toward the "
               "massif centre in units, full at lawn height fading to zero at TOP (default lawn+12) -- for a donor"
               " face that is low-angle because its home context hides it."),
        H("rot", "--rot", type=float, metavar="DEG", lo=0.0, hi=360.0, wraps=True, surfaces="cli row gui",
          help="turn the massif to ANY angle about its centre (degrees, clockwise seen from above): exact with "
               "--center, the only angle --near scans. The rock's texture turns with it unchanged; the grass stays"
               " on its grid and the foot seam is minted fresh and gated. Default: --near tries the four quarter "
               "turns, --center uses 0."),
        H("rock_height", "--rock-height", type=float, default=1.0, metavar="S", lo=1.0,
          ceiling="MTN_ROCK_HEIGHT_MAX", surfaces="cli row gui",
          help="stretch the carried rock S times taller (1.0-2.0) about its rim, UV carried: the rim, the welds to"
               " any floor or ledge and the aperture plugs stay put, so the apron and zip are unchanged. In-game "
               "passed to x2.0 on Uaho (terrain study X1). Refused for a massif with loose geometry on its face "
               "(the horseshoe's falls/river mouth) and for a peak above stock's tallest terrain (42.68). Default "
               "1.0 = the rigid carry."),
        H("spread", "--spread", type=float, default=1.0, metavar="S", lo=1.0, ceiling="MTN_SPREAD_MAX",
          surfaces="cli row gui",
          help="carry the massif S times wider in plan (1.0-1.5) about its centre, heights kept: the rock, its "
               "rim, plugs and any falls/river parts move alike, UVs carried, and every gate judges the result. "
               "With --rock-height S as well it scales uniformly. Needs a bigger island: the footprint grows S "
               "squared. In-game passed to x1.5 on Uaho, alone and scaled whole (terrain study round 20). Default "
               "1.0 = the rigid carry."),
        H("gblend", "--gblend", type=float, metavar="U", surfaces="cli",
          help="ground-apron blend reach in units (default 12.0, the proven hill-at-scale value): how far out from"
               " the rigid rim the grass apron spreads its rise. Wider = a broader, gentler bank into the foot (a "
               "high donor foot over flat host lawn wants ~20-26 so the rise reads as a foothill, not a knoll)."),
        H("reach", "--reach", type=float, default=96.0, surfaces="cli row gui",
          help="deployed-block load window around the point in units (default 96)"),
        H("ground", "--ground", default="grass", choices=_grounds, surfaces="cli row gui",
          help="the bench island's ground family: the zip annulus + plain-ground checks speak it (match the "
               "island's world-island --ground)"),
    ),
    "hill": (
        H("center", "--center", metavar="WX,WZ", group="where", surfaces="cli row",
          help="EXACT hill centre in world coords (gated, no scan)"),
        H("near", "--near", metavar="WX,WZ", group="where", surfaces="cli row",
          help="scan a ~112u window around this point for the best lawful pure-mains placement"),
        H("height", "--height", type=float, default=4.2, surfaces="cli row",
          help="prominence in units (default 4.2; the real language is 3.5-5.2)"),
        H("radius", "--radius", type=float, default=18.0, surfaces="cli row",
          help="footprint radius in units (default 18; the real language is 20-26u diameter runs)"),
    ),
}


def handles(table: str, surface: str | None = None) -> tuple:
    """The table's handles (only those on ``surface``, when given)."""
    return tuple(h for h in HANDLES[table] if surface is None or h.on(surface))


def handle(table: str, name: str) -> Handle:
    for h in HANDLES[table]:
        if h.name == name:
            return h
    raise KeyError(f"{table} has no handle {name!r}")


def row_keys(table: str) -> set:
    """The keys ``world-fuse``'s ``[[table]]`` row allows: every handle on the row surface."""
    return {h.name for h in handles(table, "row")}


def add_arguments(parser, table: str) -> None:
    """Add the table's CLI handles to a verb's ``parser``, with the types, defaults, metavars, choices and help
    declared here (the ``where`` pair as one required, mutually exclusive group)."""
    groups = {}
    for h in handles(table, "cli"):
        target = parser
        if h.group:
            if h.group not in groups:
                groups[h.group] = parser.add_mutually_exclusive_group(required=True)
            target = groups[h.group]
        kw = {"help": h.help}
        if h.action:
            kw["action"] = h.action
        if h.type is not None:
            kw["type"] = h.type
        if h.default is not None:
            kw["default"] = h.default
        if h.metavar:
            kw["metavar"] = h.metavar
        if h.choices is not None:
            kw["choices"] = h.choices() if callable(h.choices) else h.choices
        target.add_argument(h.flag, **kw)
