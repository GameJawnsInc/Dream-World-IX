"""The World tab's sink tool (overworld editor rung C5): sink a real island into open water, chosen by a click.

The carry cards' frame (:class:`worldforest.CarryTool`) with a sink's parts. The islands come from the cached island
list (``world.sinkedit.candidates``: three minutes once per install, then instant); a click picks the island under
it, its outline is the ghost (where the sea would close), and its precomputed verdict previews at once (a whole-tile
sink, its land only, or the cluster its water joins; entrances need a tick). ``world-sink --dry-run`` judges it, and
Accept runs ``world-sink`` into the draft twice: disc 1, then the same sink on disc 4 (``sinkedit.commands``: the
draft's own disc-4 step).

Edit (rung C12) opens the card on a placed sink's row: its island picked again from the list, and its two
checkboxes as the step set them; pick another island or retune them, and Accept.

Show in game is not offered for a sink: the island's own point is open sea afterwards, and a party teleported there
would stand in the water.
"""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox

from . import widgets
from .worldforest import GATE_WORDS, CarryTool

SINK_GATES = {**GATE_WORDS, "frame": "the frame gate", "stitch": "the stitch gate", "entrance": "the entrance gate",
              "coverage": "the coverage gate"}
ISLANDS = "islands"                       # the one "donor": the island list


class SinkTool(CarryTool):
    """The sink card (rung C5)."""

    TITLE, NOUN, PART, VERB = "Sink", "sink", "island list (a few minutes, once)", "world-sink"
    GATES = SINK_GATES
    CHECK_TIME = "a few seconds"

    def __init__(self, pal, panel, *, game_fn, outline_fn=None, **kw):
        from ..world import sinkedit as SE
        self._row_sel = None
        self._click_waits = False
        super().__init__(pal, panel, game_fn=game_fn,
                         outline_fn=outline_fn or (lambda _d: SE.candidates(game_fn())), **kw)

    def _edit_module(self):
        from ..world import sinkedit
        return sinkedit

    def _build_handles(self, row):
        self.island_lbl = widgets.role_label("Click an island.", "caption")
        self.island_lbl.setAccessibleName("Island")
        row.addWidget(self.island_lbl)
        self.cluster = QCheckBox("With its cluster")
        self.cluster.setToolTip("Sink the island and every island its water joins, together (world-sink --cluster): "
                                "for an island whose water runs on to another coast.")
        self.cluster.toggled.connect(lambda _on: self._handles_changed())
        row.addWidget(self.cluster)
        self.entrances = QCheckBox("Allow entrances")
        self.entrances.setToolTip("Sink an island with an entrance on it (world-sink --allow-entrances): the place "
                                  "there never opens again.")
        self.entrances.toggled.connect(lambda _on: self._handles_changed())
        row.addWidget(self.entrances)

    def donor(self):
        return ISLANDS

    # -- the island under the click --
    def place(self, x, z, y=0.0):
        rows = self._outlines.get(ISLANDS)
        self._click_waits = rows is None                 # picked once the list comes
        self._row_sel = self.FE.hit(rows, x, z) if rows is not None else None
        self.center = tuple(self._row_sel["at"]) if self._row_sel else (round(x, 3), round(z, 3))
        self._pick_y = float(y)
        self._say_island()
        self._handles_changed()

    def drag_to(self, x, z):
        pass                                             # an island is picked, not dragged

    def drop_at(self, x, z):
        self.place(x, z)

    def _outline_loaded(self, donor, ol):
        self._try_seat()
        if self._click_waits and self.center is not None:       # a click that came before the list (only that:
            self.place(*self.center)                            # a click on open sea asks for the list again)

    def open_tool(self):
        """A card opens on the defaults: a placed step's ticks (an edit's load_row sets them first, before it knows
        the row can be seated) never outlive it. A refused edit left Allow entrances ticked for the next fresh sink,
        which then passed the entrance law (review of C12)."""
        for box in (self.cluster, self.entrances):
            box.blockSignals(True)
            box.setChecked(False)
            box.blockSignals(False)
        super().open_tool()

    # -- a placed sink (rung C12) --
    def load_row(self, row):
        self.cluster.setChecked(bool(row.get("cluster", False)))
        self.entrances.setChecked(bool(row.get("allow_entrances", False)))
        self._pending_row = row
        self._try_seat()

    def _seat_row(self, row):
        x, z = (float(v) for v in row["at"])
        if self._outlines.get(ISLANDS) is None:          # the list is read on a worker (minutes, once per install)
            self.center, self._row_sel = (x, z), None
            self._say_island()
            return False
        self.place(x, z)
        if self._row_sel is None:
            raise ValueError(f"no island the sink takes lies at {x:g}, {z:g}")
        return True

    def _say_island(self):
        r = self._row_sel
        self.island_lbl.setText("Click an island." if r is None else
                                f"The island at {r['at'][0]:g}, {r['at'][1]:g}: {r['land_u2']:g} u², up to y "
                                f"{r['max_y']:g}, {len(r['blocks'])} block{'s' if len(r['blocks']) != 1 else ''}")

    # -- the shape and the laws --
    def _cmd(self, target, *, dry_run, report=None):
        return self.FE.command(target, self.center, cluster=self.cluster.isChecked(),
                               allow_entrances=self.entrances.isChecked(), dry_run=dry_run, report=report)

    def _shape(self, ol, ground_y):
        import numpy as np
        if self._row_sel is None:
            x, z = self.center
            ring = np.array([(x - 3, 0.3, z - 3), (x + 3, 0.3, z - 3), (x + 3, 0.3, z + 3), (x - 3, 0.3, z + 3)])
            return np.array([[ring[0], ring[1], ring[2]], [ring[0], ring[2], ring[3]]]), ring
        return self.FE.ghost(self._row_sel)

    def _preview_at(self, ol, rim):
        return self.FE.verdict(self._row_sel, cluster=self.cluster.isChecked(),
                               allow_entrances=self.entrances.isChecked())

    def _show_point(self, v):
        return None

    def _pass_text(self, v, where):
        r = v.get("report") or {}
        n = len(v.get("blocks") or [])
        return (f"Passes every gate: the island at {self.center[0]:g}, {self.center[1]:g} goes, {r.get('land_tris')} "
                f"land tris over {n} block{'s' if n != 1 else ''} ({self._preview.get('how')}). Accept writes it to "
                "the draft, on disc 1 and on disc 4.", "ok")

    def _preview_text(self, pv):
        if pv["why"] == "no sinkable island here":
            return ("Not an island a sink takes: click a real island (the list holds every island water meets).",
                    "warn")
        return f"Not here: {pv['why']}.", "warn"

    # -- Accept: disc 1, then disc 4 (the draft's own disc-4 step) --
    def _accept_calls(self, draft, report, report4):
        return self.FE.commands(draft, self.center, cluster=self.cluster.isChecked(),
                                allow_entrances=self.entrances.isChecked(), report=report, report4=report4)

    def _step_cells(self, verdict):
        from ..world import draft as D
        return D.all_cells()                             # the disc-4 island's blocks are not known in advance

    def _accepted(self, v):
        super()._accepted(v)
        self._row_sel = None
        self._say_island()
