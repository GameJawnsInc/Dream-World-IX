"""The World tab's coast tool (overworld editor rung C5): morph a real coast in place, at a lawful window, by a click.

The carry cards' frame (:class:`worldforest.CarryTool`) with a coast morph's parts. A click picks the block under it
and the lawful window nearest the click (``world.coastedit.windows``: the block's beach and cliff runs with each verb's
probed depth ceiling -- ``world-morphs``' catalog, a few seconds per block, cached); the verb picker offers only the
verbs that window can take, and the depth stops at its ceiling. The window's run is the ghost.
``world-transplant --in-place --dry-run`` judges it, and Accept runs the morph into the draft on disc 1 and then on
disc 4 (the draft's own disc-4 step). A block a folder of the stack, or the draft, already overrides offers no
window: the windows are stock's.

Edit (rung C12) opens the card on a placed morph's row: its block, the window its span names (matched exactly), the
verb and the depth; pick another window or verb, or retune the depth, and Accept.
"""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDoubleSpinBox

from . import widgets
from .worldforest import GATE_WORDS, CarryTool
from ..world.forestedit import disc4_words

COAST_GATES = {**GATE_WORDS, "frame": "the frame gate", "stitch": "the stitch gate", "entrance": "the entrance gate",
               "bounds": "the bounds gate", "census": "the placement census"}
VERB_WORDS = {"cliff-bump": "push the cliff out", "cliff-headland": "a headland", "cliff-bay": "a bay",
              "beach-bump": "move the beach", "beach-reshape": "reshape the beach", "beach-slide": "slide the beach"}


class CoastTool(CarryTool):
    """The coast card (rung C5)."""

    TITLE, NOUN, PART, VERB = "Coast", "coast morph", "coast windows (a few seconds a block)", "world-transplant"
    GATES = COAST_GATES
    CHECK_TIME = "a few seconds"

    def __init__(self, pal, panel, *, game_fn, outline_fn=None, stack_fn=None, **kw):
        from ..world import coastedit as CE
        self._cell = None
        self._window = None
        self._edited_by = []
        self._stack_fn = stack_fn
        super().__init__(pal, panel, game_fn=game_fn,
                         outline_fn=outline_fn or (lambda cell: [] if cell == "-" else
                                                   CE.windows(game_fn(), _cell_of(cell))), **kw)

    def _edit_module(self):
        from ..world import coastedit
        return coastedit

    def _build_handles(self, row):
        self.window_lbl = widgets.role_label("Click a coast.", "caption")
        self.window_lbl.setAccessibleName("Coast window")
        row.addWidget(self.window_lbl)
        self.verb_box = QComboBox()
        self.verb_box.setAccessibleName("Coast morph")
        self.verb_box.setToolTip("What to do at this window: only the morphs whose gates pass here at some depth are "
                                 "listed (world-morphs probes each down its depth ladder).")
        self.verb_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)   # "(to 2.5 u)" whole
        self.verb_box.currentIndexChanged.connect(lambda _ix: self._verb_changed())
        row.addWidget(self.verb_box)
        row.addWidget(widgets.role_label("Depth", "caption"))
        self.depth = QDoubleSpinBox()
        self.depth.setDecimals(1)
        self.depth.setSingleStep(self.FE.DEPTH_STEP)
        self.depth.setSuffix(" u")
        self.depth.setAccessibleName("Coast morph depth")
        self.depth.setToolTip("How far the morph moves the coast (units). It stops at the deepest depth this "
                              "window's gates pass (for a beach: negative moves it landward).")
        self.depth.valueChanged.connect(lambda _v: self._handles_changed())
        row.addWidget(self.depth)
        self._fill_verbs()

    def donor(self):
        return "{},{}".format(*self._cell) if self._cell is not None else "-"

    # -- the block, the window, the verb --
    def place(self, x, z, y=0.0):
        from ..world import frames
        cell = frames.world_to_block(*frames.wrap_world_xz(x, z))
        self.center = (round(x, 2), round(z, 2))
        self._pick_y = float(y)
        if cell != self._cell:
            self._cell, self._window = cell, None
            self._edited_by = self._edited(cell)
        self._pick_window()
        self._handles_changed()

    def drag_to(self, x, z):
        pass                                             # a window is picked, not dragged

    def drop_at(self, x, z):
        self.place(x, z)

    def _edited(self, cell):
        from ..world import coastedit as CE
        from pathlib import Path
        stack = self._stack_fn() if self._stack_fn else self._live_stack()
        folders = [self.target()] + [f for f in stack if Path(str(f)).name != self.source().name]
        return CE.edited(cell, folders, game=self._game_fn())

    def _live_stack(self):
        from ..world import river as R
        return [str(self._game_fn() / f) for f in R.stack_folders(self._game_fn())]

    def open_tool(self):
        """Who holds the card's block is read again: the folder may have changed while it was closed (a folder pick
        or a Rescan only closes the card), and place() re-reads only for a new block (review of C12)."""
        if self._cell is not None:
            self._edited_by = self._edited(self._cell)
        super().open_tool()

    def island_changed(self):
        """The draft moved under the card (an undo, an edit lifting steps out, an Accept): who holds the block it is
        on is read again (it was read once per block: an undone morph's block still read as edited)."""
        if self._cell is not None:
            self._edited_by = self._edited(self._cell)
        super().island_changed()

    def _outline_loaded(self, donor, ol):
        if donor == self.donor():
            if self._pending_row is not None:
                self._try_seat()
                return
            self._pick_window()
            self._redraw()

    # -- a placed morph (rung C12) --
    def load_row(self, row):
        if row.get("verb") not in self.FE.VERBS:
            raise ValueError(f"its morph {row.get('verb')} is not one the card offers")
        if row.get("allow_entrances"):
            raise ValueError("its allow_entrances is not a handle of the card")
        self._pending_row = row
        self._try_seat()

    def _seat_row(self, row):
        cell = tuple(int(v) for v in row["cell"])
        verb, depth = row["verb"], float(row["depth"])
        (x0, z0), (x1, z1) = row["window"]
        self.center = (round((x0 + x1) / 2.0, 2), round((z0 + z1) / 2.0, 2))
        if cell != self._cell:
            self._cell, self._window = cell, None
        self._edited_by = self._edited(cell)             # the draft before the step, read now (not the card's last)
        ws = self._outlines.get(self.donor())
        if ws is None:                                   # the block's windows: a few seconds, once (cached)
            self._say_window()
            self._load_outline(self.donor())
            ws = self._outlines.get(self.donor())        # (read inline in the synchronous lane)
            if ws is None:
                return False
        want = self.FE.row_spec(row)
        w = next((w for w in ws if verb in self.FE.lawful(w) and self.FE.spec(w, verb, depth) == want), None)
        if w is None:
            raise ValueError(f"its window is not one of block ({cell[0]}, {cell[1]})'s lawful {verb} windows")
        rng = self.FE.lawful(w)[verb]
        lo, hi = min(rng), max(rng)
        if not lo - 1e-9 <= depth <= hi + 1e-9:
            raise ValueError(f"its depth {depth:g} is outside the window's lawful {lo:g} to {hi:g}")
        self.center = tuple(round(v, 2) for v in self.FE.anchor(w, verb))
        self._window = w
        self._fill_verbs()
        self.verb_box.setCurrentIndex(self.verb_box.findData(verb))
        self.depth.setValue(depth)
        self._say_window()
        self._handles_changed()
        return True

    def _pick_window(self):
        ws = self._outlines.get(self.donor())
        w = self.FE.nearest(ws, *self.center, prefer=self._window) if ws is not None and self.center is not None \
            else None
        if w != self._window:                            # by value: a fresh read's equal window is the same one
            self._window = w
            self._fill_verbs()
        self._window = w                                 # (the read's own copy)
        self._say_window()

    def _fill_verbs(self):
        rng = self.FE.lawful(self._window) if self._window else {}
        keep = self.verb_box.currentData()
        self.verb_box.blockSignals(True)
        self.verb_box.clear()
        for verb in self.FE.VERBS:
            if verb in rng:
                lo, hi = rng[verb]
                self.verb_box.addItem(f"{verb} (to {hi:g} u)" if lo > 0 else f"{verb} ({lo:g} to {hi:g} u)", verb)
        ix = self.verb_box.findData(keep)
        self.verb_box.setCurrentIndex(ix if ix >= 0 else 0)
        self.verb_box.blockSignals(False)
        self._verb_changed(redraw=False)

    def _verb_changed(self, redraw=True):
        rng = self.FE.lawful(self._window).get(self.verb()) if self._window else None
        self.depth.blockSignals(True)
        if rng:
            lo, hi = min(rng), max(rng)
            self.depth.setRange(lo, hi)                  # the window's own ceiling is the handle's stop
            self.depth.setValue(hi if hi > 0 else lo)
        self.depth.setEnabled(bool(rng))
        self.depth.blockSignals(False)
        if redraw:
            self._handles_changed()

    def verb(self):
        return self.verb_box.currentData()

    def _say_window(self):
        w = self._window
        if self._cell is None:
            text = "Click a coast."
        elif self._edited_by:
            text = f"Block ({self._cell[0]}, {self._cell[1]}) is already edited in {', '.join(self._edited_by)}."
        elif w is None:
            text = (f"Reading block ({self._cell[0]}, {self._cell[1]})'s coast…" if self.donor() not in self._outlines
                    else f"No lawful window near the click in block ({self._cell[0]}, {self._cell[1]}).")
        else:
            text = f"A {w['kind']} run in block ({self._cell[0]}, {self._cell[1]}), {w['L']:.0f} u long"
        self.window_lbl.setText(text)

    # -- the shape and the laws --
    def _spec(self):
        if self._window is None or not self.verb():
            return "0,0:0,0:0"
        return self.FE.spec(self._window, self.verb(), self.depth.value())

    def _cmd(self, target, *, dry_run, report=None):
        return self.FE.command(target, self._cell or (0, 0), self.verb() or "cliff-bump", self._spec(),
                               dry_run=dry_run, report=report)

    def _shape(self, ol, ground_y):
        import numpy as np
        if self._window is None or not self.verb():
            x, z = self.center
            ring = np.array([(x - 2, 1.0, z - 2), (x + 2, 1.0, z - 2), (x + 2, 1.0, z + 2), (x - 2, 1.0, z + 2)])
            return np.array([[ring[0], ring[1], ring[2]], [ring[0], ring[2], ring[3]]]), ring
        return self.FE.ghost(self._window, self.verb())

    def _preview_at(self, ol, rim):
        return self.FE.verdict(self._window, self.verb(), self.depth.value(), edited_by=self._edited_by)

    def _accept_calls(self, draft, report, report4):
        return self.FE.commands(draft, self._cell, self.verb(), self._spec(), report=report, report4=report4)

    def _step_cells(self, verdict):
        return [tuple(self._cell)]

    def _show_point(self, v):
        if self._window is None:
            return None
        (x0, z0), (x1, z1) = self.FE.span(self._window, self.verb())
        return ((x0 + x1) / 2, (z0 + z1) / 2)

    def _accepted(self, v):
        super()._accepted(v)
        self._window = None
        self._edited_by = self._edited(self._cell) if self._cell is not None else []
        self._fill_verbs()
        self._say_window()

    # -- the words --
    def _pass_text(self, v, where):
        n = sum(1 for g in v.get("gates") or [] if g.get("ok"))
        return (f"Passes every gate ({n}): {self.verb()} {self.depth.value():g} u — "
                f"{VERB_WORDS.get(self.verb(), '')} along {self._window['L']:.0f} u of "
                f"{self._window['kind']}. Accept writes it to the draft, {disc4_words(v)}.", "ok")

    def _preview_text(self, pv):
        if pv["why"] == "no lawful coast window here":
            return ("Not a coast window: click near a real island's cliff base or beach waterline.", "warn")
        return f"Not here: {pv['why']}.", "warn"


def _cell_of(spec):
    a, b = str(spec).split(",")
    return (int(a), int(b))

