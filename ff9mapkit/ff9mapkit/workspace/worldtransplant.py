"""The World tab's transplant tool (overworld editor rung C5): carry a real coastal block -- or a multi-block carry unit
-- whole, onto open ocean.

The carry cards' frame (:class:`worldforest.CarryTool`) with a carry's parts. The donor picker offers the catalogue's
coast donors: the qualified single blocks and the multi-block carry units (a candidate, not yet walked in game, says
so). The turn combo offers the quarter turns the donor allows. A click picks the target: one block's own cell, or the
rect (turned with the carry) whose middle is nearest the click. The ghost is the donor's own land, turned by the
carry's quarter-turn map and laid there (``world.transplantedit.placed``); once a check reports the shift ``--shift
auto`` chose for a single block, it moves by that too (a unit runs ``--shift 0,0``). The preview runs the target's
laws (open ocean, on the grid, no edit there yet); ``world-transplant --dry-run`` judges the rest, and Accept carries
it into the draft.
"""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox

from . import widgets
from .worldforest import GATE_WORDS, CarryTool

TRANSPLANT_GATES = {**GATE_WORDS, "land-fit": "the land-fit gate", "frame": "the frame gate",
                    "census": "the placement census", "weld": "the weld audit"}


class TransplantTool(CarryTool):
    """The transplant card (rung C5)."""

    TITLE, NOUN, PART, VERB = "Carry a coast", "carry", "donor's land", "world-transplant"
    GATES = TRANSPLANT_GATES
    CHECK_TIME = "about five seconds"

    def __init__(self, pal, panel, *, game_fn, land_fn=None, ocean_fn=None, stack_fn=None, **kw):
        from ..world import transplantedit as TE
        self._stack_fn = stack_fn
        self._land_fn = land_fn or (lambda donor, size=(1, 1): TE.donor_land(donor, size=size, game=game_fn()))
        self._ocean_fn = ocean_fn or (lambda: TE.stock_land(game=game_fn()))
        self._click = None                               # the click the target follows (a turn re-fits the rect)
        super().__init__(pal, panel, game_fn=game_fn, outline_fn=self._read_donor, **kw)

    def _read_donor(self, key):
        """One read per donor: its land, plus the stock land set the open-ocean law reads (once)."""
        if not hasattr(self, "_ocean"):
            self._ocean = self._ocean_fn()
        donor, size = self._parse(key)
        return self._land_fn(donor) if size == (1, 1) else self._land_fn(donor, size=size)

    @staticmethod
    def _parse(key):
        """``"BX,BY"`` or ``"BX,BY@NXxNY"`` -> ``((bx, by), (nx, ny))``."""
        blk, _, size = str(key).partition("@")
        return (tuple(int(v) for v in blk.split(",")),
                tuple(int(v) for v in size.lower().split("x")) if size else (1, 1))

    def _edit_module(self):
        from ..world import transplantedit
        return transplantedit

    def _build_handles(self, row):
        self.donor_box = QComboBox()
        self.donor_box.setAccessibleName("Coast donor")
        self.donor_box.setToolTip("Which real coast to carry, whole (land, beach and its whole tiled ocean): the "
                                  "catalogue's coast donors -- single blocks, and the multi-block carry units, the "
                                  "only rects that hold every island they touch whole.")
        self._rows = {}
        for r in self.FE.donors():
            key = "{},{}".format(*r["donor"]) + ("" if r["size"] == (1, 1) else "@{}x{}".format(*r["size"]))
            self._rows[key] = r
            self.donor_box.addItem(self.donor_label(r), key)
            tip = r.get("note", "") + ("" if r["status"] == "qualified" else " Not yet walked in game.")
            self.donor_box.setItemData(self.donor_box.count() - 1, tip.strip(), 3)
        # a long name never sets the card's width (the window's floor): the combo shows ~16 characters, and the
        # list opens as wide as its items
        self.donor_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.donor_box.setMinimumContentsLength(16)
        self.donor_box.currentIndexChanged.connect(lambda _ix: self._donor_changed())
        row.addWidget(self.donor_box)
        row.addWidget(widgets.role_label("Turn", "caption"))
        self.rot_box = QComboBox()
        self.rot_box.setAccessibleName("Carry turn")
        self.rot_box.setToolTip("Turn the carried coast about its centre by a quarter turn (world-transplant --rot): "
                                "the 4u tile lattice and its ocean stay verbatim. A unit carrying an object allows "
                                "only the turns its object does.")
        self.rot_box.currentIndexChanged.connect(lambda _ix: self._turn_changed())
        row.addWidget(self.rot_box)
        self.cell_lbl = widgets.role_label("Click open ocean.", "caption")
        self.cell_lbl.setAccessibleName("Target cell")
        row.addWidget(self.cell_lbl)
        self._fill_rots()

    @staticmethod
    def donor_label(r) -> str:
        """``beach-island (7,17)``, ``the-comma 2x3 · new`` (a candidate: not yet walked in game)."""
        what = f"{r['name']} ({r['blocks']})" if tuple(r["size"]) == (1, 1) else "{} {}x{}".format(r["name"],
                                                                                                  *r["size"])
        return what + ("" if r["status"] == "qualified" else " · new")

    def _fill_rots(self):
        keep = self.rot_box.currentData()
        rots = self._rows.get(self.donor(), {}).get("rots") or self.FE.ROTS
        self.rot_box.blockSignals(True)
        self.rot_box.clear()
        for r in rots:
            self.rot_box.addItem(f"{r}°", r)
        ix = self.rot_box.findData(keep)
        self.rot_box.setCurrentIndex(ix if ix >= 0 else 0)
        self.rot_box.blockSignals(False)

    def _donor_changed(self):
        self._fill_rots()
        self._turn_changed()

    def _turn_changed(self):
        if self._click is not None:
            self.place(*self._click, self._pick_y)       # the rect turns with the carry: fit it to the click again
        else:
            self._handles_changed()

    def donor(self):
        return str(self.donor_box.currentData())

    def load_row(self, row):
        """The donor (a block or a unit), the turn, and the target rect: placed by its middle, which fits it again."""
        size = tuple(row.get("size") or (1, 1))
        key = "{},{}".format(*row["donor"]) + ("" if size == (1, 1) else "@{}x{}".format(*size))
        ix = self.donor_box.findData(key)
        if ix < 0:
            raise ValueError(f"its donor {key} is not one the card lists")
        self.donor_box.setCurrentIndex(ix)
        jx = self.rot_box.findData(int(row.get("rot") or 0))
        if jx < 0:
            raise ValueError(f"the turn {row.get('rot')} is not one its donor allows")
        self.rot_box.setCurrentIndex(jx)
        c = row["cell"]
        tw, th = self.FE.tsize(size, self.rot())
        self.place(64.0 * c[0] + 32.0 * tw, -(64.0 * c[1] + 32.0 * th))

    def _donor_blk(self):
        return self._parse(self.donor())[0]

    def size(self):
        return self._parse(self.donor())[1]

    def rot(self):
        return int(self.rot_box.currentData() or 0)

    def cell(self):
        if self._click is None:
            return None
        return self.FE.anchor_for(*self._click, size=self.size(), rot=self.rot())

    def blocks(self):
        c = self.cell()
        return [] if c is None else self.FE.cells(c, self.size(), self.rot())

    # -- the target under the click --
    def place(self, x, z, y=0.0):
        self._click = (float(x), float(z))
        self._pick_y = float(y)
        c = self.cell()
        tw, th = self.FE.tsize(self.size(), self.rot())
        self.center = (64.0 * c[0] + 32.0 * tw, -(64.0 * c[1] + 32.0 * th))   # the command names the cell(s)
        self.cell_lbl.setText(f"Onto block ({c[0]}, {c[1]})" if (tw, th) == (1, 1) else
                              f"Onto ({c[0]}, {c[1]}), {tw}x{th}")
        self._handles_changed()

    def drag_to(self, x, z):
        pass                                             # a cell is picked, not dragged

    def drop_at(self, x, z):
        self.place(x, z)

    # -- the shape and the laws --
    def _cmd(self, target, *, dry_run, report=None):
        return self.FE.command(target, self.cell() or (0, 0), self._donor_blk(), rot=self.rot(), size=self.size(),
                               dry_run=dry_run, report=report)

    def _shape(self, ol, ground_y):
        v = self._current_verdict() or {}
        shift = v.get("shift") or (0.0, 0.0)
        tris = self.FE.placed(ol, self._donor_blk(), self.cell(), rot=self.rot(), shift=shift, size=self.size())
        return tris, self.FE.rim(self.cell(), self.size(), self.rot())

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
        return self.FE.preview(self.cell(), land=getattr(self, "_ocean", set()), occupied=self._occupied,
                               size=self.size(), rot=self.rot())

    def _step_cells(self, verdict):
        """The carry's whole target rect (the history snapshots every block before an Accept writes it)."""
        return [tuple(b) for b in (verdict or {}).get("blocks") or []] or self.blocks()

    def _show_point(self, v):
        return self.center

    # -- the words --
    def _pass_text(self, v, where):
        n = sum(1 for g in v.get("gates") or [] if g.get("ok"))
        sh = v.get("shift") or (0, 0)
        c = self.cell()
        what = f"block {self.donor()}" if self.size() == (1, 1) else \
            "{} ({}x{} blocks)".format(self._rows.get(self.donor(), {}).get("name", self.donor()), *self.size())
        return (f"Passes every gate ({n}): {what} carried onto ({c[0]}, {c[1]}), turned {self.rot()}°, shifted "
                f"{sh[0]:+g}, {sh[1]:+g}. Accept carries it into the draft.", "ok")

    def _preview_text(self, pv):
        return f"Not here: {pv['why']}.", "warn"
