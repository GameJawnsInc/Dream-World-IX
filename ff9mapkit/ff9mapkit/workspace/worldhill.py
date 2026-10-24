"""The World tab's hill tool (overworld editor rung 6): raise a grass hill on a deployed island.

The carry cards' frame (:class:`worldforest.CarryTool`) with a hill's parts: a click places the centre (drag it), and
the height and radius spins stop where the handle table says (``world/handles.py``). The ghost is the island's own
triangles lifted by the hill's raised cosine, the very displacement ``world-hill`` writes (``world.hilledit``); the
preview runs the verb's footprint, flank and peak laws live, and ``world-hill --dry-run`` judges the rest (the crack
gate, the placement census). Accept raises it in the draft.
"""
from __future__ import annotations

from PySide6.QtWidgets import QDoubleSpinBox

from . import widgets
from .worldforest import GATE_WORDS, CarryTool

HILL_GATES = {**GATE_WORDS, "flank": "the flank law", "peak": "the peak cap", "crack": "the crack gate"}


class HillTool(CarryTool):
    """The hill card (rung 6)."""

    TITLE, NOUN, PART, VERB = "Hill", "hill", "hill", "world-hill"
    GATES = HILL_GATES
    CHECK_TIME = "a few seconds"
    HANDLE_TABLE = "hill"
    HANDLES = {"center": "the click (and the drag)", "height": "height_spin", "radius": "radius_spin"}

    def __init__(self, pal, panel, **kw):
        kw.setdefault("outline_fn", lambda _key: self.FE.DONOR)      # a hill carries nothing: no read
        super().__init__(pal, panel, **kw)

    def _edit_module(self):
        from ..world import hilledit
        return hilledit

    def _build_handles(self, row):
        row.addWidget(widgets.role_label("Height", "caption"))
        self.height_spin = QDoubleSpinBox()
        top = self._fit(self.height_spin, "height")
        self.height_spin.setValue(self._handle("height").default)
        self.height_spin.setSingleStep(0.1)
        self.height_spin.setDecimals(1)
        self.height_spin.setAccessibleName("Hill height")
        self.height_spin.setToolTip(f"How far the hill rises above the lawn, in units (world-hill --height). Stock's "
                                    f"lowland hills rise 3.5 to 5.2; it stops at {top:g}, and the flank law and the "
                                    "peak cap judge every height.")
        self.height_spin.valueChanged.connect(lambda _v: self._handles_changed())
        row.addWidget(self.height_spin)
        row.addWidget(widgets.role_label("Radius", "caption"))
        self.radius_spin = QDoubleSpinBox()
        top = self._fit(self.radius_spin, "radius")
        self.radius_spin.setValue(self._handle("radius").default)
        self.radius_spin.setSingleStep(1.0)
        self.radius_spin.setDecimals(1)
        self.radius_spin.setAccessibleName("Hill radius")
        self.radius_spin.setToolTip(f"How far out the hill's slope runs from its top, in units (world-hill --radius). "
                                    f"A wider hill is gentler; it stops at {top:g}, and the footprint must stay on "
                                    "level grass, clear of forest, meadow stamps and the coast.")
        self.radius_spin.valueChanged.connect(lambda _v: self._handles_changed())
        row.addWidget(self.radius_spin)
        row.addStretch(1)

    def donor(self):
        return self.FE.DONOR

    # -- the shape and the laws --
    def _cmd(self, target, *, dry_run, report=None):
        return self.FE.command(target, self.center, height=self.height_spin.value(), radius=self.radius_spin.value(),
                               dry_run=dry_run, report=report)

    def _shape(self, _ol, ground_y):
        tris, _touched = self.FE.lifted(self._ix, self.center, self.height_spin.value(), self.radius_spin.value())
        return tris, self.FE.rim(self._ix, self.center, self.radius_spin.value(), ground_y)

    def _preview_at(self, _ol, _rim):
        return self.FE.preview(self._ix, self.center, self.height_spin.value(), self.radius_spin.value())

    # -- the words --
    def _pass_text(self, v, where):
        r = v.get("report") or {}
        return (f"Passes every gate {where}: {r.get('displaced_tris')} triangles lifted, the steepest flank "
                f"{r.get('worst_flank')}° (the limit is 28.6), the top at y {r.get('peak_y')}. Accept writes it to "
                "the draft.", "ok")

    def _preview_text(self, pv):
        if pv["why"] == "no island here":
            return (f"Not on an island in {self.target().name}: a hill rises on deployed kit islands only.", "warn")
        return f"Not here: {pv['why']}.", "warn"
