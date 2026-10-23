"""The World tab's transplant tool (overworld editor rung C5): carry a real coastal block, whole, onto an open-ocean cell.

The carry cards' frame (:class:`worldforest.CarryTool`) with a carry's parts. The donor picker offers the catalogue's
qualified coast donors; a click picks the target CELL (whole blocks only: the carry fills one cell); the ghost is the
donor's own land, turned by the carry's quarter-turn map and moved there (``world.transplantedit.placed``), and once a
check reports the shift ``--shift auto`` chose, it moves by that too. The preview runs the target's laws (open ocean,
no edit there yet); ``world-transplant --dry-run`` judges the rest, and Accept carries it into the draft.
"""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox

from . import widgets
from .worldforest import GATE_WORDS, CarryTool

TRANSPLANT_GATES = {**GATE_WORDS, "land-fit": "the land-fit gate", "frame": "the frame gate",
                    "census": "the placement census", "weld": "the weld audit"}
OCEAN = "ocean"                           # the open-ocean law's read (the stock land set), shared by every donor


class TransplantTool(CarryTool):
    """The transplant card (rung C5)."""

    TITLE, NOUN, PART, VERB = "Carry a coast", "carry", "donor's land", "world-transplant"
    GATES = TRANSPLANT_GATES
    CHECK_TIME = "about five seconds"

    def __init__(self, pal, panel, *, game_fn, land_fn=None, ocean_fn=None, stack_fn=None, **kw):
        from ..world import transplantedit as TE
        self._stack_fn = stack_fn
        self._land_fn = land_fn or (lambda donor: TE.donor_land(donor, game=game_fn()))
        self._ocean_fn = ocean_fn or (lambda: TE.stock_land(game=game_fn()))
        super().__init__(pal, panel, game_fn=game_fn, outline_fn=self._read_donor, **kw)

    def _read_donor(self, key):
        """One read per donor: its land, plus the stock land set the open-ocean law reads (once)."""
        if not hasattr(self, "_ocean"):
            self._ocean = self._ocean_fn()
        return self._land_fn(tuple(int(v) for v in key.split(",")))

    def _edit_module(self):
        from ..world import transplantedit
        return transplantedit

    def _build_handles(self, row):
        self.donor_box = QComboBox()
        self.donor_box.setAccessibleName("Coast donor")
        self.donor_box.setToolTip("Which real coastal block to carry, whole (land, beach and its whole tiled ocean): "
                                  "the catalogue's qualified coast donors.")
        for r in self.FE.donors():
            self.donor_box.addItem(f"{r['name']} ({r['blocks']})", "{},{}".format(*r["donor"]))
            self.donor_box.setItemData(self.donor_box.count() - 1, r.get("note", ""), 3)
        self.donor_box.currentIndexChanged.connect(lambda _ix: self._handles_changed())
        row.addWidget(self.donor_box)
        row.addWidget(widgets.role_label("Turn", "caption"))
        self.rot_box = QComboBox()
        self.rot_box.setAccessibleName("Carry turn")
        self.rot_box.setToolTip("Turn the carried block about its centre by a quarter turn (world-transplant --rot): "
                                "the 4u tile lattice and its ocean stay verbatim.")
        for r in self.FE.ROTS:
            self.rot_box.addItem(f"{r}°", r)
        self.rot_box.currentIndexChanged.connect(lambda _ix: self._handles_changed())
        row.addWidget(self.rot_box)
        self.cell_lbl = widgets.role_label("Click an open-ocean cell.", "caption")
        self.cell_lbl.setAccessibleName("Target cell")
        row.addWidget(self.cell_lbl)

    def donor(self):
        return str(self.donor_box.currentData())

    def _donor_blk(self):
        return tuple(int(v) for v in self.donor().split(","))

    def rot(self):
        return int(self.rot_box.currentData() or 0)

    def cell(self):
        return self.FE.cell_of(*self.center) if self.center is not None else None

    # -- the cell under the click --
    def place(self, x, z, y=0.0):
        c = self.FE.cell_of(x, z)
        self.center = (64.0 * c[0] + 32.0, -(64.0 * c[1] + 32.0))      # whole cells: the command names the cell
        self._pick_y = float(y)
        self.cell_lbl.setText(f"Onto block ({c[0]}, {c[1]})")
        self._handles_changed()

    def drag_to(self, x, z):
        pass                                             # a cell is picked, not dragged

    def drop_at(self, x, z):
        self.place(x, z)

    # -- the shape and the laws --
    def _cmd(self, target, *, dry_run, report=None):
        return self.FE.command(target, self.cell() or (0, 0), self._donor_blk(), rot=self.rot(), dry_run=dry_run,
                               report=report)

    def _shape(self, ol, ground_y):
        v = self._current_verdict() or {}
        shift = v.get("shift") or (0.0, 0.0)
        tris = self.FE.placed(ol, self._donor_blk(), self.cell(), rot=self.rot(), shift=shift)
        return tris, self.FE.rim(self.cell())

    def _occupied(self, blocks):
        from pathlib import Path
        from ..world import mesh as M
        stack = self._stack_fn() if self._stack_fn else self._live_stack()
        folders = [self.target()] + [f for f in stack if Path(str(f)).name != self.source().name]
        out = {}
        for b in blocks:
            hits = sorted({Path(str(fo)).name for fo in folders for d in (1, 4)
                           if M.existing_overrides([tuple(b)], str(fo), disc=d, game=self._game_fn())})
            if hits:
                out[tuple(b)] = hits
        return out

    def _live_stack(self):
        from ..world import river as R
        return [str(self._game_fn() / f) for f in R.stack_folders(self._game_fn())]

    def _preview_at(self, ol, rim):
        return self.FE.preview(self.cell(), land=getattr(self, "_ocean", set()), occupied=self._occupied)

    def _show_point(self, v):
        c = v.get("cell") or self.cell()
        return (64.0 * c[0] + 32.0, -(64.0 * c[1] + 32.0)) if c else None

    # -- the words --
    def _pass_text(self, v, where):
        n = sum(1 for g in v.get("gates") or [] if g.get("ok"))
        sh = v.get("shift") or (0, 0)
        return (f"Passes every gate ({n}): block {self.donor()} carried onto ({self.cell()[0]}, {self.cell()[1]}), "
                f"turned {self.rot()}°, shifted {sh[0]:+g}, {sh[1]:+g}. Accept carries it into the draft.", "ok")

    def _preview_text(self, pv):
        return f"Not here: {pv['why']}.", "warn"
