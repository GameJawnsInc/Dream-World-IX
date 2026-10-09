"""THE SWITCHABLE CELLS (terrain study defect 19; the forms lane, studies/terrain-malleability/forms/).

The engine swaps 26 overworld cells between two block forms, nine places' worth, once per world load
(``ff9.w_worldChangeBlockSet``, ff9.cs:9153-9208). Each place's default condition is
``WorldConfiguration.UsePlaceAlternateForm`` (:165-193); a mod folder's ``Environment.txt`` can replace it
(``world-environment``). On those cells ``WMWorld.LoadBlock`` registers each part per form (WMWorld.cs:588-657):

* form 1 only: ``Terrain``, ``Object``, ``VolcanoCrater1``, ``VolcanoLava1``, and ``Sea3``/``Sea4``/``Sea5`` at the
  Water Shrine cell (3,9) (block 219);
* form 2 only: ``Terrain2``, ``Object2``, ``VolcanoCrater2``, ``VolcanoLava2``, ``Sea3_2``/``Sea4_2``/``Sea5_2``;
* both: every other part (beach, river, stream, falls, the other seas).

The s34 override key is the part's name (WMWorld.cs:823-825), so a kit ``Terrain`` override on such a cell replaces
form 1 only. When the place switches, the stock form-2 mesh comes back, render and walk, and the edit is gone; the
study found no kit check that knew this. The form-2 override is spelled ``Terrain2``/``Object2`` (a ``Terrain2``
override was walked in game: terrain study in-game round 1, story terrain).

Seven places are gated on ``w_frameDisc == 1``, so on disc 4 they never switch by default (forcing one there would
revert disc 4's ground to disc-1-era geometry: forms lane F11). Chocobo's Paradise and Mognet Central switch on a
story flag on every disc. A Path D namespace (``Disc9``) copies the switch flags only in CLONE mode
(``WorldDiscSpike.CloneStockWorld``, default off), so its cells are dormant by default.

ANY OTHER CELL (engine patch s92, terrain study P1). The custom engine arms a cell stock never switches when it has a
loose ``Terrain2`` override, and switches it to that ground once per world load when its ``Block[x][y] Form.txt``
sidecar holds an NCalc condition that evaluates true (like an Environment.txt ``[Condition=...]``). On such a cell
the form-1 Object stays in form 2 (unless a loose ``Object2`` replaces it), so only ``Terrain`` is form-1-only and
``Terrain2`` form-2-only. :func:`write_condition` arms one (``world-forms --arm``); stock Memoria ignores both files.
Engine patch s93 extends the ``Object2`` rule to a cell with no stock building (it appears in form 2 only, and a bare
kit ``Object`` beside it shows in form 1 only); :mod:`ff9mapkit.world.formobject` writes one (``--building2``).
"""
from __future__ import annotations

import re
from pathlib import Path

# ff9.cs:9153-9208, in the engine's order
PLACE_CELLS = {
    "SouthGate_Gate": ((18, 14), (17, 12)),
    "Alexandria": ((19, 10), (19, 11), (20, 10), (20, 11)),
    "FireShrine": ((7, 1), (8, 1), (14, 15)),
    "Lindblum": ((13, 16), (13, 17), (14, 16), (14, 17)),
    "Cleyra": ((13, 12), (14, 12)),
    "BlackMageVillage": ((14, 6), (21, 10), (22, 14)),
    "WaterShrine": ((3, 9), (9, 1)),
    "MognetCentral": ((16, 1), (13, 4), (14, 5)),
    "ChocoboParadise": ((0, 0), (16, 14), (9, 17)),
}
# WorldConfiguration.UsePlaceAlternateForm (:165-193), as NCalc an Environment.txt line could restate
DEFAULT_CONDITION = {
    "SouthGate_Gate": "WorldDisc == 1 && ScenarioCounter >= 2990 && ScenarioCounter < 6990",
    "Alexandria": "WorldDisc == 1 && ScenarioCounter >= 8800",
    "FireShrine": "WorldDisc == 1 && ScenarioCounter >= 10600 && ScenarioCounter < 10700",
    "Lindblum": "WorldDisc == 1 && ScenarioCounter >= 5598",
    "Cleyra": "WorldDisc == 1 && ScenarioCounter >= 4990",
    "BlackMageVillage": "WorldDisc == 1 && ScenarioCounter >= 6200",
    "WaterShrine": "WorldDisc == 1 && ScenarioCounter >= 10600 && ScenarioCounter < 10700",
    "MognetCentral": "(GetEventGlobalByte(101) & 128) != 0",
    "ChocoboParadise": "(GetEventGlobalByte(101) & 64) != 0",
}
FLAG_PLACES = ("MognetCentral", "ChocoboParadise")         # switch on every disc; the other seven on disc 1 only
SWITCHABLE = {cell: place for place, cells in PLACE_CELLS.items() for cell in cells}
WATER_SHRINE_CELL = (3, 9)
# a form-1-only part -> its form-2 counterpart (lower case, as the override file names compare on Windows); None =
# no switchable cell has one (form 2 drops the Fire Shrine crater: forms lane F10)
FORM2_OF = {"terrain": "Terrain2", "object": "Object2", "volcanocrater1": None, "volcanolava1": "VolcanoLava2"}
WATER_SHRINE_FORM2_OF = {"sea3": "Sea3_2", "sea4": "Sea4_2", "sea5": "Sea5_2"}
FORM2_PARTS = {"terrain2", "object2", "volcanocrater2", "volcanolava2", "sea3_2", "sea4_2", "sea5_2"}

#: the per-cell condition sidecar of a custom form cell (engine patch s92), beside its overrides
FORM_SIDECAR = "Form"

_OVERRIDE_RE = re.compile(r"Disc(\d+)[\\/]0_1[\\/]r(\d+)[\\/]Block\[(\d+)\]\[(\d+)\] ([^\\/]+)\.ff9mesh$", re.I)


def part_form(x: int, y: int, part: str) -> int | None:
    """1 or 2 when ``part`` on cell ``(x, y)`` renders in one form only; ``None`` when the cell never switches or the
    part renders in both forms."""
    if (x, y) not in SWITCHABLE:
        return None
    p = part.lower()
    if p in FORM2_OF or ((x, y) == WATER_SHRINE_CELL and p in WATER_SHRINE_FORM2_OF):
        return 1
    if p in FORM2_PARTS:
        return 2
    return None


def form_sidecar_relpath(disc: int, x: int, y: int) -> str:
    """The mod-folder-relative path of a cell's ``Form.txt`` (beside its ``.ff9mesh`` overrides, under ``0_1``)."""
    return f"FF9_Data/WorldMap/Disc{disc}/0_1/r{y}/Block[{x}][{y}] {FORM_SIDECAR}.txt"


def read_condition(path) -> str | None:
    """A ``Form.txt``'s condition: its first line that is neither blank nor a comment (``#`` or ``//``) -- the
    engine's rule -- or ``None`` (no file, or nothing in it)."""
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return None
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith("//"):
            return s
    return None


def custom_condition(mod_root, disc: int, x: int, y: int) -> str | None:
    """The condition ``mod_root`` arms cell ``(x, y)`` with in namespace ``Disc{disc}``, or ``None``."""
    return read_condition(Path(mod_root) / form_sidecar_relpath(disc, x, y))


def write_condition(mod_root, disc: int, x: int, y: int, condition: str | None) -> Path:
    """Arm (or, with ``condition=None``, disarm) cell ``(x, y)``: write or delete its ``Form.txt``. Refuses one of the
    26 stock cells (a place's Environment.txt condition rules those: ``world-environment``), a cell off the grid, and a
    condition that is empty or spans lines. Returns the path."""
    from .mesh import GRID_COLS, GRID_ROWS
    if not (0 <= x < GRID_COLS and 0 <= y < GRID_ROWS):
        raise ValueError(f"cell ({x},{y}) is off the {GRID_COLS}x{GRID_ROWS} grid")
    if (x, y) in SWITCHABLE:
        raise ValueError(f"cell ({x},{y}) already switches with {SWITCHABLE[(x, y)]}: its condition is that place's "
                         f"(world-environment [[place]]), and its form 2 is edited with --form 2 directly")
    dest = Path(mod_root) / form_sidecar_relpath(disc, x, y)
    if condition is None:
        if dest.is_file():
            dest.unlink()
        return dest
    cond = str(condition).strip()
    if not cond or "\n" in cond or "\r" in cond:
        raise ValueError("give the condition as one NCalc expression on one line, e.g. "
                         "\"(GetEventGlobalByte(1089) & 1) != 0\"")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f"# ff9mapkit: Block[{x}][{y}] switches to its loose Terrain2 when this holds (engine patch s92)\n"
                    f"{cond}\n", encoding="utf-8")
    return dest


def dormant(place: str, disc_tag: int) -> bool:
    """True when ``place`` never switches by default in override namespace ``Disc{disc_tag}``: a disc-gated place on
    disc 4, or any place on a Path D namespace (not 1 or 4) in its default BLANK mode."""
    if disc_tag == 1:
        return False
    if disc_tag == 4:
        return place not in FLAG_PLACES
    return True


def form_hits(paths, *, include_dormant: bool = False) -> list:
    """The overrides among ``paths`` (existing ``.ff9mesh`` files under ``WorldMap/Disc{n}/0_1``) that reach ONE form
    of a switchable cell: ``[{"path", "disc", "cell", "part", "place", "form", "dormant", "counterpart",
    "covered"}]``. ``counterpart`` = the form-2 part a form-1 edit would need too (``None`` for a form-2 part);
    ``covered`` = that counterpart's override exists beside it. Anything else (a MagicMock, a missing file, another
    lod) is skipped. Dormant hits are dropped unless ``include_dormant``."""
    out = []
    for p in paths:
        if not isinstance(p, (str, Path)):
            continue
        m = _OVERRIDE_RE.search(str(p))
        if not m:
            continue
        pp = Path(p)
        try:
            if not pp.is_file():
                continue
        except OSError:
            continue
        disc, y, x, part = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(5)
        if (x, y) in SWITCHABLE:
            form = part_form(x, y, part)
            if form is None:
                continue
            place = SWITCHABLE[(x, y)]
            when, quiet = DEFAULT_CONDITION[place], dormant(place, disc)
            cp = (FORM2_OF.get(part.lower()) or WATER_SHRINE_FORM2_OF.get(part.lower())) if form == 1 else None
        else:                                   # a custom form cell (engine s92): armed by the Form.txt beside it
            when = read_condition(pp.with_name(f"Block[{x}][{y}] {FORM_SIDECAR}.txt"))
            form = {"terrain": 1, "terrain2": 2, "object2": 2}.get(part.lower()) if when else None
            if when and part.lower() == "object" and pp.with_name(f"Block[{x}][{y}] Object2.ff9mesh").is_file():
                form = 1                        # an Object2 replaces the form-1 building in form 2 (s92 + s93)
            if form is None:
                continue                        # not armed, or a part that renders in both forms there
            place, quiet, cp = None, False, (FORM2_OF[part.lower()] if form == 1 else None)
        if quiet and not include_dormant:
            continue
        covered = bool(cp) and pp.with_name(f"Block[{x}][{y}] {cp}.ff9mesh").is_file()
        out.append({"path": str(pp), "disc": disc, "cell": (x, y), "part": part, "place": place, "form": form,
                    "dormant": quiet, "counterpart": cp, "covered": covered, "when": when})
    return out


def object2_kind(path) -> str | None:
    """What a cell's loose ``Object2`` does in form 2: ``"blank"`` (a hidden one-triangle stub, the building is gone),
    ``"mesh"`` (another building), or ``None`` (no file: the form-1 building stays)."""
    import struct
    try:
        head = Path(path).read_bytes()[:20]
    except OSError:
        return None
    if head[:4] != b"F9WM" or len(head) < 20:
        return "mesh"
    return "blank" if struct.unpack_from("<i", head, 8)[0] <= 3 else "mesh"


def custom_cells(mod_root) -> list:
    """Every custom form cell ``mod_root`` defines (engine s92): ``[{"disc", "cell", "condition", "armed",
    "object2"}]``, one per ``Form.txt``. ``armed`` = its ``Terrain2`` is there too; without it the engine arms nothing
    and the cell never switches. ``object2`` = :func:`object2_kind`."""
    wm = Path(mod_root) / "FF9_Data" / "WorldMap"
    out = []
    pat = re.compile(r"Disc(\d+)[\\/]0_1[\\/]r\d+[\\/]Block\[(\d+)\]\[(\d+)\] " + FORM_SIDECAR + r"\.txt$", re.I)
    for p in sorted(wm.rglob(f"Block*{FORM_SIDECAR}.txt")) if wm.is_dir() else []:
        m = pat.search(str(p))
        if not m:
            continue
        disc, x, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        out.append({"disc": disc, "cell": (x, y), "condition": read_condition(p),
                    "armed": p.with_name(f"Block[{x}][{y}] Terrain2.ff9mesh").is_file(),
                    "object2": object2_kind(p.with_name(f"Block[{x}][{y}] Object2.ff9mesh"))})
    return out


def mod_folder_hits(mod_root, *, include_dormant: bool = True) -> list:
    """:func:`form_hits` over every ``.ff9mesh`` under ``<mod_root>/FF9_Data/WorldMap`` (``.bak`` parks excluded)."""
    wm = Path(mod_root) / "FF9_Data" / "WorldMap"
    paths = sorted(wm.rglob("*.ff9mesh")) if wm.is_dir() else []
    return form_hits(paths, include_dormant=include_dormant)


def note_lines(hits) -> list:
    """The writer receipt for :func:`form_hits`: a warning per uncovered form-1 edit, a note per form-2 edit."""
    lines = []
    for h in hits:
        (x, y), place = h["cell"], h["place"]
        where = f"Block[{x}][{y}] {h['part']} (Disc{h['disc']})"
        when = h.get("when") or DEFAULT_CONDITION[place]
        switches = (f"switches with {place} (by default: {when})" if place else
                    f"switches to its Terrain2 when its Form.txt holds ({when}; engine s92)")
        pin = ("pin the place's condition with world-environment" if place else
               "change or remove its Form.txt (world-forms --arm / --disarm)")
        if h["form"] == 2:
            lines.append(f"  note: {where} is the FORM-2 mesh of a cell that {switches}: it shows only while the "
                         f"cell has switched")
        elif h["covered"]:
            lines.append(f"  note: {where} replaces form 1 of a cell that {switches}; its form-2 override "
                         f"({h['counterpart']}) is there too")
        elif h["counterpart"] is None:
            lines.append(f"  !! WARNING: {where} replaces FORM 1 ONLY: this cell {switches}, and form 2 has no "
                         f"{h['part']} here, so the edit vanishes when it does. To keep it, {pin}.")
        else:
            how = ("run the same edit again with --form 2 (world-terrain / world-deploy) to make it in form 2 too"
                   if h["counterpart"] == "Terrain2" else
                   f"write a {h['counterpart']} override too (mesh.deploy_override(bm, part=\"{h['counterpart']}\"))")
            lines.append(f"  !! WARNING: {where} replaces FORM 1 ONLY: this cell {switches}, and when it does the "
                         f"{h['counterpart']} mesh replaces it and this edit vanishes, render and walk. To keep it, "
                         f"{how}, or {pin}.")
    return lines
