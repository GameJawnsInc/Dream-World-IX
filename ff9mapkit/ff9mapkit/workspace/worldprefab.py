"""The World tab's prefab tool (overworld editor rung P3, studies/overworld-editor/PREFABS.md): place a whole landmass
-- an island and the relief carried onto it, or a walked stock carry unit -- in one step.

The carry cards' frame (:class:`worldforest.CarryTool`) with a prefab's parts. The picker offers the prefab catalog
(``world/data/prefabs.toml``): the walked (qualified) first, a candidate saying so. A click picks the anchor block:
the one whose footprint is centred nearest the click (a prefab places by whole blocks, so it is picked, not dragged).
The ghost is the prefab's own land there (``world.prefabedit.ghost``). The preview runs ``world-prefab``'s first laws
(the footprint on the map and on open ocean, nothing edited in or beside it); ``world-prefab --dry-run`` judges the
rest -- the prefab staged outside the install and held to the land its catalog fingerprint names -- and Accept places
it into the draft as ONE step (one Undo takes the whole landmass back).
"""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox

from . import widgets
from .worldforest import GATE_WORDS, CarryTool

PREFAB_GATES = {**GATE_WORDS, "catalog": "the catalog", "rows": "the map's rows", "window": "the clear window",
                "identity": "the identity check", "nav": "the navigation check", "written": "the written-land check",
                "disc4": "the disc-4 check", "compose": "a row of the prefab"}


class PrefabTool(CarryTool):
    """The prefab card (rung P3)."""

    TITLE, NOUN, PART, VERB = "Add a prefab", "prefab", "prefab's land", "world-prefab"
    GATES = PREFAB_GATES
    # measured on a real draft: a check 31 s, an accept 57 s (the prefab is built outside the install, then written)
    CHECK_TIME = "about half a minute: the prefab is built outside the install and held to its catalog"

    def __init__(self, pal, panel, *, game_fn, ghost_fn=None, ocean_fn=None, stack_fn=None, catalog=None, **kw):
        from ..world import prefabedit as PE
        self._stack_fn = stack_fn
        self._catalog = catalog
        self._ghost_fn = ghost_fn or (lambda prefab: PE.ghost(prefab, game=game_fn()))
        self._ocean_fn = ocean_fn or (lambda: PE.stock_land(game=game_fn()))
        self._anchor = None                              # the anchor block the click picked
        super().__init__(pal, panel, game_fn=game_fn, outline_fn=self._read_prefab, **kw)

    def _read_prefab(self, name):
        """One read per prefab: its ghost land, plus the stock land set the open-ocean law reads (once)."""
        if not hasattr(self, "_ocean"):
            self._ocean = self._ocean_fn()
        return self._ghost_fn(self._rows[name])

    def _edit_module(self):
        from ..world import prefabedit
        return prefabedit

    def _build_handles(self, row):
        self.prefab_box = QComboBox()
        self.prefab_box.setAccessibleName("Prefab")
        self.prefab_box.setToolTip("Which landmass to place, whole: the prefab catalog (world/data/prefabs.toml). A "
                                   "walked one has been checked in game; a new one has not.")
        self._rows = {}
        for p in self.FE.prefabs(self._catalog):
            self._rows[p["name"]] = p
            self.prefab_box.addItem(self.prefab_label(p), p["name"])
            tip = (p.get("note", "") + " " + (f"Walked: {p['walked']}." if p.get("walked") else
                                             "Not yet walked in game.")).strip()
            self.prefab_box.setItemData(self.prefab_box.count() - 1, tip, 3)
        # a long name never sets the card's width (the window's floor): the combo shows ~16 characters
        self.prefab_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.prefab_box.setMinimumContentsLength(16)
        self.prefab_box.currentIndexChanged.connect(lambda _ix: self._prefab_changed())
        row.addWidget(self.prefab_box)
        self.cell_lbl = widgets.role_label("Click open ocean.", "caption")
        self.cell_lbl.setAccessibleName("Anchor block")
        row.addWidget(self.cell_lbl)

    @staticmethod
    def prefab_label(p) -> str:
        """``desert-peak-isle 3x3``, ``meadow-grove-isle 3x3 · new`` (a candidate: not yet walked in game)."""
        foot = p.get("footprint") or [(0, 0)]
        w = max(b[0] for b in foot) - min(b[0] for b in foot) + 1
        h = max(b[1] for b in foot) - min(b[1] for b in foot) + 1
        return f"{p['name']} {w}x{h}" + ("" if p["status"] == "qualified" else " · new")

    def donor(self):
        return str(self.prefab_box.currentData())

    def prefab(self) -> dict:
        return self._rows[self.donor()]

    def _prefab_changed(self):
        if self._click is not None:
            self.place(*self._click, self._pick_y)       # a different footprint: fit the anchor to the click again
        else:
            self._handles_changed()

    _click = None                                        # the click the anchor follows (a new prefab re-fits it)

    def load_row(self, row):
        """The prefab and its anchor (rung C9): placed by its footprint's middle, which picks the same anchor."""
        ix = self.prefab_box.findData(str(row["name"]))
        if ix < 0:
            raise ValueError(f"its prefab {row['name']} is not one the catalog lists")
        self.prefab_box.setCurrentIndex(ix)
        self.place(*self.FE.center(tuple(int(v) for v in row["cell"]), self.prefab()))

    def cell(self):
        return self._anchor

    def blocks(self):
        return [] if self._anchor is None else self.FE.cells(self._anchor, self.prefab())

    # -- the anchor under the click --
    def place(self, x, z, y=0.0):
        self._click = (float(x), float(z))
        self._pick_y = float(y)
        p = self.prefab()
        self._anchor = self.FE.anchor_for(*self._click, p)
        cx, cz = self.FE.center(self._anchor, p)
        self.center = (cx % 1536.0, cz)                  # the command names the anchor; the centre is for the words
        dx0, dy0, dx1, dy1 = self.FE.bbox(p)
        self.cell_lbl.setText(f"Anchor ({self._anchor[0]}, {self._anchor[1]}), {dx1 - dx0 + 1}x{dy1 - dy0 + 1} blocks")
        self._handles_changed()

    def drag_to(self, x, z):
        pass                                             # an anchor is picked, not dragged

    def drop_at(self, x, z):
        self.place(x, z)

    # -- the shape and the laws --
    def _cmd(self, target, *, dry_run, report=None):
        return self.FE.command(target, self.donor(), self._anchor or (0, 0), dry_run=dry_run, report=report)

    def _shape(self, ol, ground_y):
        return self.FE.at(ol, self._anchor), self.FE.rim(self._anchor, self.prefab())

    def _folders(self, *, stack):
        from pathlib import Path
        out = [self.target()]
        if stack:
            st = self._stack_fn() if self._stack_fn else self._live_stack()
            out += [f for f in st if Path(str(f)).name != self.source().name]   # the draft stands in for its source
        return out

    def _occupied_in(self, blocks, *, stack):
        from pathlib import Path
        from ..world import mesh as M
        cache = self.__dict__.setdefault("_occ", {})
        out = {}
        for b in blocks:
            key = (tuple(b), stack)
            if key not in cache:
                cache[key] = sorted({Path(str(fo)).name for fo in self._folders(stack=stack) for d in (1, 4)
                                     if M.existing_overrides([tuple(b)], str(fo), disc=d, game=self._game_fn())})
            if cache[key]:
                out[tuple(b)] = cache[key]
        return out

    def island_changed(self):
        self.__dict__.pop("_occ", None)
        super().island_changed()

    def _live_stack(self):
        from ..world import river as R
        return [str(self._game_fn() / f) for f in R.stack_folders(self._game_fn())]

    def _preview_at(self, ol, rim):
        return self.FE.preview(self._anchor, self.prefab(), land=getattr(self, "_ocean", set()),
                               occupied=lambda bs: self._occupied_in(bs, stack=True),
                               occupied_target=lambda bs: self._occupied_in(bs, stack=False))

    def _step_cells(self, verdict):
        """The prefab's footprint (the history snapshots every block before an Accept writes it): the check's own
        blocks, else the catalog's."""
        return [tuple(b) for b in (verdict or {}).get("blocks") or []] or self.blocks()

    def _show_point(self, v):
        return tuple(float(c) for c in v["center"]) if v.get("center") else self.center

    # -- the words --
    def _pass_text(self, v, where):
        p = self.prefab()
        a = self._anchor
        walked = "walked in game" if p["status"] == "qualified" else "NOT yet walked in game"
        tier = v.get("identity") or "the catalog's land"
        n = len(v.get("blocks") or [])
        return (f"Passes: {p['name']} on anchor ({a[0]}, {a[1]}), {n} block{'s' if n != 1 else ''}, {walked}. "
                f"Identity: {tier}. Accept places it into the draft as one step.", "ok")

    def _preview_text(self, pv):
        return f"Not here: {pv['why']}.", "warn"
