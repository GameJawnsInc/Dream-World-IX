"""The World tab's mountain tool (overworld editor rung C2): carry a real stock rock massif onto a deployed island.

The forest's card (:class:`worldforest.CarryTool`) with the massif's handles: one of the seven qualified massifs,
its angle, its spread and its rock height, each stopping at the law's ceiling. A chip names the ground the massif
stands on at home beside the ground under the ghost (THE HOME-GROUND WARNING: a lawful carry onto another ground
puts its foot on a ground it never meets in stock, which no gate sees). ``world-mountain`` judges it, and its
``--ground`` is the island's own.
"""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QHBoxLayout, QSpinBox

from . import widgets
from .worldforest import GATE_WORDS, CarryTool

MOUNTAIN_GATES = {**GATE_WORDS, "blocks": "the deployed-blocks law", "span": "the span law",
                  "zip": "the zip envelope", "rigid": "the rock-rigid gate", "peak": "the peak cap",
                  "apron": "the apron slope", "probe": "the placement probes", "plug": "the plug chart",
                  "edge": "the zip's edge"}


class MountainTool(CarryTool):
    """The mountain card (rung C2)."""

    TITLE, NOUN, PART, VERB = "Mountain", "mountain", "massif", "world-mountain"
    GATES = MOUNTAIN_GATES
    CHECK_TIME = "about ten seconds"                     # a passing world-mountain dry run, measured (C2)
    HANDLE_TABLE = "mountain"
    HANDLES = {"center": "the click (and the drag)", "donor": "donor_box", "rot": "angle", "spread": "spread",
               "rock_height": "rock_height", "reach": "the placed massif's radius (mountainedit.reach_for)",
               "ground": "the island's ground under the ghost (mountainedit.island_ground)"}

    def _edit_module(self):
        from ..world import mountainedit
        return mountainedit

    def _build_handles(self, row):
        from ..world import interior as IN
        FE = self.FE
        self._rows = {r["donor"]: r for r in FE.massif_donors()}
        self.donor_box = QComboBox()
        self.donor_box.setAccessibleName("Massif donor")
        self.donor_box.setToolTip("Which stock rock massif to carry, whole: the seven the donor catalogue has "
                                  "qualified (world-donors --class massif).")
        for r in self._rows.values():
            self.donor_box.addItem(f"{r['name']} ({r['blocks']})", r["donor"])
            self.donor_box.setItemData(self.donor_box.count() - 1, r.get("note", ""), 3)   # Qt.ToolTipRole
        self.donor_box.currentIndexChanged.connect(lambda _ix: self._handles_changed())
        row.addWidget(self.donor_box)
        self.ground_chip = widgets.status_chip("", "info")
        row.addWidget(self.ground_chip)
        row = QHBoxLayout()                              # the sizes on a row of their own: one row of seven
        row.setSpacing(8)                                # controls set the window's floor (1218px at 100%)
        self._extra_rows = (row,)
        row.addWidget(widgets.role_label("Angle", "caption"))
        self.angle = QSpinBox()
        self._fit(self.angle, "rot")
        self.angle.setSingleStep(5)
        self.angle.setSuffix("°")
        self.angle.setAccessibleName("Mountain angle")
        self.angle.setToolTip("Turn the massif about its centre, clockwise seen from above (world-mountain --rot). "
                              "Its rock texture turns with it; the grass stays on its grid.")
        self.angle.valueChanged.connect(lambda _v: self._handles_changed())
        row.addWidget(self.angle)
        row.addWidget(widgets.role_label("Spread", "caption"))
        self.spread = QDoubleSpinBox()
        top = self._fit(self.spread, "spread")             # the law's ceiling is the handle's stop
        self.spread.setSingleStep(FE.SPREAD_STEP)
        self.spread.setDecimals(2)
        self.spread.setSuffix("×")
        self.spread.setAccessibleName("Mountain spread")
        self.spread.setToolTip(f"Widen the massif in plan, heights kept (world-mountain --spread). It stops at "
                               f"×{top:g}, the widest judged in game; the island must be bigger.")
        self.spread.valueChanged.connect(lambda _v: self._handles_changed())
        row.addWidget(self.spread)
        row.addWidget(widgets.role_label("Height", "caption"))
        self.rock_height = QDoubleSpinBox()
        top = self._fit(self.rock_height, "rock_height")
        self.rock_height.setSingleStep(FE.HEIGHT_STEP)
        self.rock_height.setDecimals(2)
        self.rock_height.setSuffix("×")
        self.rock_height.setAccessibleName("Mountain rock height")
        self._height_tip = (f"Stretch the rock taller about its rim, which never moves (world-mountain "
                            f"--rock-height). It stops at ×{top:g}, the tallest judged in game, "
                            f"and the peak may not pass stock's tallest terrain (y {IN.STOCK_TERRAIN_MAX_Y}).")
        self.rock_height.setToolTip(self._height_tip)
        self.rock_height.valueChanged.connect(lambda _v: self._handles_changed())
        row.addWidget(self.rock_height)
        row.addStretch(1)
        self._sync_chip()

    def donor(self):
        return str(self.donor_box.currentData())

    def _outline_loaded(self, donor, ol):
        """A massif with geometry on its face the stretch would leave behind (the horseshoe's falls) keeps its
        height: the handle is held at ×1 and says why."""
        if ol.height_ok:
            self.rock_height.setEnabled(True)
            self.rock_height.setToolTip(self._height_tip)
            return
        self.rock_height.blockSignals(True)
        self.rock_height.setValue(1.0)
        self.rock_height.blockSignals(False)
        self.rock_height.setEnabled(False)
        self.rock_height.setToolTip(f"The {self._rows.get(donor, {}).get('name', donor)} massif carries falls or a "
                               "river mouth on its face, which a height stretch would leave behind, so its height "
                               "is fixed (world-mountain refuses --rock-height for it).")
        self._try_seat()                                 # a held step's reach waited on this outline

    # -- the island's ground and the donor's home ground --
    def ground(self) -> str:
        """The ground family under the ghost (``--ground``), grass until the island is read."""
        if self._ix is None or self.center is None:
            return "grass"
        return self.FE.island_ground(self._ix, *self.fcenter())

    def _sync_chip(self):
        home = self._rows.get(self.donor(), {}).get("home_ground") or "grass"
        if self.center is None or self._ix is None:
            text, kind = f"{home} at home", "info"
        else:
            here = self.ground()
            text, kind = (f"{home} at home and here", "good") if here == home else \
                (f"{home} at home, {here} here", "warn")
        self.ground_chip.setText(text)
        self.ground_chip.setProperty("kind", kind)
        widgets.repolish(self.ground_chip)
        self.ground_chip.setAccessibleName(f"{kind}: {text}")
        self.ground_chip.setToolTip("The ground this massif's foot meets at home, and the ground under the ghost. "
                                    "Carried onto another ground, its foot meets a ground it never meets in "
                                    "stock: lawful, and no gate sees it, so it is your call.")

    def _redraw(self):
        if self._pending_row is not None:                # (the island's read lands here: a held step's ground)
            self._try_seat()
        self._sync_chip()
        super()._redraw()

    # -- the shape --
    def _r_placed(self):
        ol = self._outlines.get(self.donor())
        return None if ol is None else ol.r_rim * self.spread.value()

    def load_row(self, row):
        """The massif, its angle, spread and height (the ground and the reach follow the place, as on a click). The
        row is held until the island and the massif are read: its --ground is the island's under the centre and its
        --reach the outline's, so said back before they land it would read grass and the default reach (review of
        C12: every mountain placed off grass refused to open)."""
        ix = self.donor_box.findData(str(row["donor"]))
        if ix < 0:
            raise ValueError(f"its massif {row['donor']} is not one the card lists")
        self.donor_box.setCurrentIndex(ix)
        self.angle.setValue(int(round(float(row.get("rot", 0.0)))) % 360)
        self.spread.setValue(float(row.get("spread", 1.0)))
        self.rock_height.setValue(float(row.get("rock_height", 1.0)))
        self._pending_row = row
        self._try_seat()

    def _seat_row(self, row):
        self.place(*row["center"])
        return self._ix is not None and self.donor() in self._outlines

    def _cmd(self, target, *, dry_run, report=None):
        r = self._r_placed()
        return self.FE.command(target, self.center, self.donor(), spread=self.spread.value(),
                               rot_deg=self.angle.value(), rock_height=self.rock_height.value(), ground=self.ground(),
                               reach=self.FE.DEFAULT_REACH if r is None else self.FE.reach_for(r),
                               dry_run=dry_run, report=report)

    def _shape(self, ol, ground_y):
        return self.FE.placed(ol, self.fcenter(), spread=self.spread.value(), rot_deg=self.angle.value(),
                              rock_height=self.rock_height.value(), ground_y=ground_y)

    def _preview_at(self, ol, rim):
        from ..world import interior as IN
        pv = self.FE.footprint_preview(self._ix, self.fcenter(), rim[:, [0, 2]], ol.r_rim * self.spread.value(),
                                       ground=self.ground())
        if pv["ok"] and self.rock_height.value() > 1.0 and self._ghost is not None:
            t = self._ghost[0].reshape(-1, 3)
            top = t[t[:, 1].argmax()]
            if top[1] > IN.STOCK_TERRAIN_MAX_Y:          # THE PEAK CAP, at the ghost's own seat
                return {"ok": False, "gate": "peak", "where": [(float(top[0]), float(top[2]))],
                        "why": f"y {top[1]:.1f}", "span": pv["span"]}
        return pv

    def _show_point(self, v):
        """The carve's own teleport point: beside the massif, facing it (its centre is rock)."""
        t = (v.get("report") or {}).get("teleport")
        if t:
            from ..world.frames import wrap_world_xz
            return tuple(float(c) for c in wrap_world_xz(*t))
        return super()._show_point(v)

    # -- the words --
    def _pass_text(self, v, where):
        r = v.get("report") or {}
        rigid = r.get("rock_rigid")
        plugs = f" (+{r['plugs']} plugs)" if r.get("plugs") else ""
        text = (f"Passes every gate {where}: {r.get('blob_tris')} rock triangles{plugs}, "
                f"{r.get('dropped')} island triangles carved, {r.get('zip_tris')} in the zip; peak y "
                f"{r.get('peak_y')}, rock rigidity {rigid * 100:.1f}% (the ceiling is 3.5). Accept writes it to "
                "the draft." if rigid is not None else f"Passes every gate {where}. Accept writes it to the draft.")
        home = self._rows.get(self.donor(), {}).get("home_ground")
        if v.get("note") and home:
            return (text + f" Its home ground is {home}: on {v.get('ground', self.ground())} its foot meets a ground "
                    "it never meets in stock.", "warn")
        return text, "ok"

    def _preview_text(self, pv):
        gate, why = pv.get("gate"), pv["why"]
        if why == "no island here":
            return (f"Not on an island in {self.target().name}: the mountain carries onto deployed kit islands "
                    "only.", "warn")
        if gate == "blocks":
            return (f"Not here: the massif needs deployed island under its whole span ({why}). Move it inland or "
                    "pick a smaller massif.", "warn")
        if gate == "span":
            return ("Not here: the massif's rim comes too near the edge of the deployed blocks; the carve works "
                    "inside them.", "warn")
        if why == "no plain ground round its rim":
            return ("Not here: there is no island under the massif's rim (open sea inside the deployed blocks).",
                    "warn")
        if gate == "peak":
            return (f"Too tall: the peak would stand at {why}, above stock's tallest terrain. Lower the height.",
                    "warn")
        if gate in ("weld", "edge"):                     # the carve's hole ring, read from the island (rung C17)
            return (f"Not here: {why}. Move it a little, or turn it; the marks show where.", "warn")
        return (f"Not here: the footprint reaches {why}. A massif needs plain {self.ground()} under its whole rim "
                "and a band round it.", "warn")
