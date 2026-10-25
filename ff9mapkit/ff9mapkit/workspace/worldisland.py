"""The World tab's island tool (overworld editor rung C5): mint a new island on open ocean where you click.

The carry cards' frame (:class:`worldforest.CarryTool`) with a mint's parts. The ghost is the island's own coastline
(``world.islandedit.outline``: the mint's outline call, exact for its seed) filled at its height; drag it to move it.
The handles are the mint's own: radius, lobes (one perturbed circle, or two or three lobes with waists), height,
the ground family, and the shape seed ("New shape" rolls one). The preview runs the mint's first laws (open ocean
under every block it touches, and no folder of the stack or the draft already holding one); ``world-island
--dry-run`` judges the rest, and Accept mints it into the draft.
"""
from __future__ import annotations

import random

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QHBoxLayout, QPushButton, QSpinBox

from . import widgets
from .worldforest import CarryTool

ISLAND = "island"                         # the one "donor": the stock land the open-ocean law reads


class IslandTool(CarryTool):
    """The island card (rung C5)."""

    TITLE, NOUN, PART, VERB = "Island", "island", "open ocean", "world-island"
    CHECK_TIME = "about six seconds"

    def __init__(self, pal, panel, *, game_fn, outline_fn=None, stack_fn=None, **kw):
        from ..world import islandedit as IE
        self._stack_fn = stack_fn
        super().__init__(pal, panel, game_fn=game_fn,
                         outline_fn=outline_fn or (lambda _d: IE.stock_land(game=game_fn())), **kw)

    def _edit_module(self):
        from ..world import islandedit
        return islandedit

    def _build_handles(self, row):
        IE = self.FE
        row.addWidget(widgets.role_label("Radius", "caption"))
        self.radius = QDoubleSpinBox()
        self.radius.setRange(*IE.RADIUS_RANGE)
        self.radius.setSingleStep(2.0)
        self.radius.setDecimals(0)
        self.radius.setSuffix(" u")
        self.radius.setValue(IE.DEFAULTS["radius"])
        self.radius.setAccessibleName("Island radius")
        self.radius.setToolTip("The coastline's base radius (world-island --radius): 24 is about one block.")
        self.radius.valueChanged.connect(lambda _v: self._handles_changed())
        row.addWidget(self.radius)
        row.addWidget(widgets.role_label("Lobes", "caption"))
        self.lobes = QSpinBox()
        self.lobes.setRange(*IE.LOBES_RANGE)
        self.lobes.setAccessibleName("Island lobes")
        self.lobes.setToolTip("1: one perturbed circle. 2-3: an asymmetric landmass with waists and corners "
                              "(world-island --lobes).")
        self.lobes.valueChanged.connect(lambda _v: self._handles_changed())
        row.addWidget(self.lobes)
        self.ground_box = QComboBox()
        self.ground_box.setAccessibleName("Island ground")
        self.ground_box.setToolTip("The island's ground family: only those whose cliff stock dresses as a sea cliff.")
        for g in IE.grounds():
            self.ground_box.addItem(g, g)
        self.ground_box.currentIndexChanged.connect(lambda _ix: self._handles_changed())
        row.addWidget(self.ground_box)
        row2 = QHBoxLayout()                             # the rest on a row of their own (the window's floor)
        row2.setSpacing(8)
        self._extra_rows = (row2,)
        row2.addWidget(widgets.role_label("Height", "caption"))
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(*IE.HEIGHT_RANGE)
        self.height_spin.setSingleStep(0.1)
        self.height_spin.setDecimals(1)
        self.height_spin.setSuffix(" u")
        self.height_spin.setValue(IE.DEFAULTS["height"])
        self.height_spin.setAccessibleName("Island height")
        self.height_spin.setToolTip("The interior's height (world-island --height; 3.2 is the stock coastal median).")
        self.height_spin.valueChanged.connect(lambda _v: self._handles_changed())
        row2.addWidget(self.height_spin)
        row2.addWidget(widgets.role_label("Shape", "caption"))
        self.seed = QSpinBox()
        self.seed.setRange(0, IE.SEED_MAX)
        self.seed.setValue(random.randint(0, IE.SEED_MAX))
        self.seed.setAccessibleName("Island shape seed")
        self.seed.setToolTip("The coastline's seed (world-island --seed): the same seed draws the same island.")
        self.seed.valueChanged.connect(lambda _v: self._handles_changed())
        row2.addWidget(self.seed)
        self.reroll_btn = QPushButton("New shape")
        self.reroll_btn.setProperty("role", "quiet")
        self.reroll_btn.setToolTip("Roll another coastline seed.")
        self.reroll_btn.clicked.connect(lambda: self.seed.setValue(random.randint(0, IE.SEED_MAX)))
        row2.addWidget(self.reroll_btn)
        row2.addStretch(1)

    def donor(self):
        return ISLAND

    def load_row(self, row):
        IE = self.FE
        ix = self.ground_box.findData(str(row.get("ground", "grass")))
        if ix < 0:
            raise ValueError(f"its ground {row.get('ground')} is not one the card offers")
        seed = float(row["seed"])
        if seed != int(seed) or not 0 <= seed <= IE.SEED_MAX:
            raise ValueError(f"its seed {row['seed']:g} is not one the card's shape spin can say")
        self.ground_box.setCurrentIndex(ix)
        self.radius.setValue(float(row.get("radius", IE.DEFAULTS["radius"])))
        self.lobes.setValue(int(row.get("lobes", 1)))
        self.height_spin.setValue(float(row.get("height", IE.DEFAULTS["height"])))
        self.seed.setValue(int(seed))
        self.place(*row["center"])

    # -- the shape and the laws --
    def _ring(self):
        return self.FE.outline(self.center, radius=self.radius.value(), seed=float(self.seed.value()),
                               lobes=self.lobes.value())

    def _cmd(self, target, *, dry_run, report=None):
        return self.FE.command(target, self.center, seed=float(self.seed.value()), radius=self.radius.value(),
                               lobes=self.lobes.value(), height=self.height_spin.value(),
                               ground=self.ground_box.currentData() or "grass", dry_run=dry_run, report=report)

    def _shape(self, ol, ground_y):
        return self.FE.ghost(self._ring(), height=self.height_spin.value())

    def _occupied(self, blocks):
        """``{block: [folders]}`` already overriding each block (the draft first, then the stack), cached per block
        until the draft moves: a drag asks for the same blocks every frame."""
        from pathlib import Path
        from ..world import mesh as M
        cache = self.__dict__.setdefault("_occ", {})
        stack = None
        for b in blocks:
            b = tuple(b)
            if b in cache:
                continue
            if stack is None:
                stack = self._stack_fn() if self._stack_fn else self._live_stack()
                folders = [self.target()] + [f for f in stack if Path(str(f)).name != self.source().name]
            cache[b] = sorted({Path(str(fo)).name for fo in folders for d in (1, 4)
                               if M.existing_overrides([b], str(fo), disc=d, game=self._game_fn())})
        return {tuple(b): cache[tuple(b)] for b in blocks if cache[tuple(b)]}

    def island_changed(self):
        self.__dict__.pop("_occ", None)
        super().island_changed()

    def _live_stack(self):
        from ..world import river as R
        return [str(self._game_fn() / f) for f in R.stack_folders(self._game_fn())]

    def _preview_at(self, ol, rim):
        return self.FE.preview(rim[:, [0, 2]], land=ol, occupied=self._occupied)

    def _show_point(self, v):
        return tuple(float(c) for c in v["center"]) if v.get("center") else None

    # -- the words --
    def _pass_text(self, v, where):
        n = len(v.get("blocks") or [])
        return (f"Passes every gate: an island of radius {self.radius.value():g} u {where}, seed {self.seed.value()}, "
                f"over {n} block{'s' if n != 1 else ''} of open ocean. Accept mints it into the draft.", "ok")

    def _preview_text(self, pv):
        return f"Not here: {pv['why']}. An island needs open ocean no edit holds yet under its whole coast.", "warn"
