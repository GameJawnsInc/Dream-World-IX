"""The World tab's sink tool (overworld editor rung C5): sink a real island into open water, chosen by a click.

The carry cards' frame (:class:`worldforest.CarryTool`) with a sink's parts. The islands come from the cached island
list (``world.sinkedit.candidates``: three minutes once per install, then instant); a click picks the island under
it, its outline is the ghost (where the sea would close), and its precomputed verdict previews at once (a whole-tile
sink, its land only, or the cluster its water joins; entrances need a tick). ``world-sink --dry-run`` judges it, and
Accept runs ``world-sink`` into the draft twice: disc 1, then the same sink on disc 4 (``sinkedit.commands``: the
draft's own disc-4 step).

Show in game is not offered for a sink: the island's own point is open sea afterwards, and a party teleported there
would stand in the water.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QCheckBox

from . import widgets
from .worldforest import GATE_WORDS, CarryTool, kit_cwd

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
        if self.center is not None and self._row_sel is None:   # a click that came before the list
            self.place(*self.center)

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
    def _run_job(self, kind, draft):
        if kind != "accept":
            return super()._run_job(kind, draft)
        from ..world import draft as D
        key = self.handles()
        if key is None:
            self._job = None
            return
        D.begin_step(draft, D.all_cells())               # the disc-4 island's blocks are not known in advance
        tmp = Path(tempfile.mkdtemp(prefix="ff9_sink_"))
        report, report4 = tmp / "verdict.json", tmp / "verdict4.json"
        one, four = self.FE.commands(draft, self.center, cluster=self.cluster.isChecked(),
                                     allow_entrances=self.entrances.isChecked(), report=report, report4=report4)
        game = self._game_fn()
        pre = [sys.executable, "-m", "ff9mapkit", "--game", str(game)]
        self._job = (kind, key)
        self._say(f"Sinking the island in the draft of {self.source().name}, disc 1 then disc 4…", "")
        self._sync_buttons()

        def disc4_done(code, text):
            v4 = self.FE.read_verdict(report4) or {}
            self._disc4 = bool(v4.get("ok"))
            self._job_done(kind, key, report, 0, text)

        def disc1_done(code, text):
            if self._job != (kind, key):
                return
            v = self.FE.read_verdict(report)
            if v is None or not v.get("ok"):
                self._job_done(kind, key, report, code, text)
                return
            self._runner.start(pre + four, kit_cwd(), disc4_done)
        self._disc4 = None
        self._runner.start(pre + one, kit_cwd(), disc1_done)

    def _accepted(self, v):
        disc4 = getattr(self, "_disc4", None)
        super()._accepted(v)
        self._row_sel = None
        self._say_island()
        if disc4 is False:
            self._say(self.verdict_lbl.text() + " Disc 4 refused the same sink, so disc 4 keeps its island (as "
                      "world-sink's replay would).", "warn")
