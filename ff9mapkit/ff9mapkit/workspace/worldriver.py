"""The World tab's river tool (overworld editor rung C5): move the carried river, whole, to another placement.

The carry cards' frame (:class:`worldforest.CarryTool`) with a river's parts. The card reads where the river stands
in the draft (or the folder) now, from the ledger; a click picks the nearest placement the river fits (a whole-block
shift onto open ocean, ``world.riveredit``), and the ghost is the river's own carried land and its island's coast
ring there. The preview marks a placement free or held (the river's own files do not count: they go first);
``world-river --move-from --dry-run`` judges the rest, and Accept moves it in the draft. A folder with no river in it
gets the plain carry (``world-river --at``).
"""
from __future__ import annotations

from .worldforest import GATE_WORDS, CarryTool
from . import widgets

RIVER_GATES = {**GATE_WORDS, "R0": "the move's source (no river there)", "R1": "the ownership read",
               "B1": "the binding and stack read", "C1": "the part budget", "W1": "the knit",
               "sea_plan": "the sea plan", "zip": "the zip envelope", "T0": "the water lattice",
               "T1": "the whole-block shift", "P0": "the audited write"}


class RiverTool(CarryTool):
    """The river card (rung C5)."""

    TITLE, NOUN, PART, VERB = "Move the river", "river", "river", "world-river"
    GATES = RIVER_GATES
    CHECK_TIME = "about forty seconds"                   # a passing world-river --move-from dry run, measured (C5)

    def __init__(self, pal, panel, *, game_fn, river_fn=None, stack_fn=None, **kw):
        from ..world import riveredit as RE
        self._stack_fn = stack_fn
        self._river_fn = river_fn or (lambda target, rs: self._read_river(target, rs))
        self._shift = None                               # the picked placement (a whole-block shift)
        self._river = None                               # (target, the river's shift now or None, held cells)
        super().__init__(pal, panel, game_fn=game_fn,
                         outline_fn=kw.pop("outline_fn", None) or (lambda _key: RE.shape(game=game_fn())), **kw)

    def _edit_module(self):
        from ..world import riveredit
        return riveredit

    def _build_handles(self, row):
        self.from_lbl = widgets.role_label("Reading where the river is…", "caption")
        self.from_lbl.setAccessibleName("The river now")
        self.from_lbl.setToolTip("Where the carried river stands in the draft (or the folder) now, by the folder's "
                                 "ledger: world-river's own deploy.")
        row.addWidget(self.from_lbl)
        self.to_lbl = widgets.role_label("Click where it goes.", "caption")
        self.to_lbl.setAccessibleName("Where it goes")
        row.addWidget(self.to_lbl)

    def donor(self):
        return self.FE.DONOR

    def _rs(self):
        return self._outlines.get(self.FE.DONOR)

    def river_at(self):
        """The river's shift in the target now (None: there is none, or it is not read yet). A read of the folder
        holds for the draft Check makes of it (an exact copy); every change to the draft (Accept, an undo or redo,
        a promote) reads it again."""
        r = self._river
        return r[1] if r is not None else None

    # -- where the river is, and what holds the placements --
    def _read_river(self, target, rs):
        """``(shift or None, held)``: the river's placement in ``target`` and ``{cell: folders}`` for every cell any
        placement writes that a folder of the stack (or the draft) holds, the river's own files left out."""
        from pathlib import Path
        from ..world import mesh as M
        from ..world import river as R
        game = self._game_fn()
        here = self.FE.placements(rs, str(target), game=game)
        at, mine = (here[0][0], set(here[0][1])) if here else (None, set())
        stack = self._stack_fn() if self._stack_fn else [str(game / f) for f in R.stack_folders(game)]
        folders = [str(target)] + [f for f in stack if Path(str(f)).name != self.source().name]
        cells = sorted({c for s in rs.shifts for c in rs.cells_at(s)})
        held = {}
        for fo in folders:
            for d in (1, 4):
                for p in M.existing_overrides(cells, fo, disc=d, game=game):
                    if Path(p) in mine:
                        continue
                    c = self.FE.cell_of_path(p)
                    if c is not None:
                        held.setdefault(c, set()).add(Path(str(fo)).name)
        return at, held

    def _load_river(self):
        rs, target = self._rs(), self.target()
        if rs is None or self._river is not None:
            return
        self._bg("river", lambda: (target, *self._river_fn(target, rs)))

    def _load_soup(self):
        super()._load_soup()
        self._load_river()

    def island_changed(self):
        self._river = None
        super().island_changed()

    def _accepted(self, v):
        self._river = None                               # the river moved in the draft: read where it is again
        self._shift = None
        super()._accepted(v)

    def _promote_done(self, kind, report, code, text):
        self._river = None                               # the folder (or the draft) moved: where is the river now
        super()._promote_done(kind, report, code, text)

    def _discard(self):
        self._river = None                               # the target goes back to the folder
        super()._discard()

    def _outline_loaded(self, donor, rs):
        self._load_river()
        if self.center is not None and self._shift is None:
            self.place(*self.center)                     # a click that landed before the read: pick for it now

    def _on_bg(self, what, serial, result, err):
        if what != "river":
            return super()._on_bg(what, serial, result, err)
        if err is not None:
            self._say(f"Where the river stands could not be read: {err}", "error")
            return
        target, at, held = result
        if target != self.target() or self._river is not None:
            return                                       # a read of a folder the tool no longer judges
        self._river = (target, at, held)
        self._sync_from()
        self._redraw()
        if self.center is not None and self._job is None and self._current_verdict() is None:
            self._timer.start(0)

    def _sync_from(self):
        at = self.river_at()
        if self._river is None:
            self.from_lbl.setText("Reading where the river is…")
        elif at is None:
            self.from_lbl.setText(f"No river in {self.target().name}: a click places a new one.")
        else:
            x, z = self.FE.offset_of(at)
            self.from_lbl.setText(f"The river is at {x:g}, {z:g} now.")

    # -- the placement under the click --
    def place(self, x, z, y=0.0):
        rs = self._rs()
        self._pick_y = float(y)
        if rs is None:                                   # not read yet: keep the click, pick once it is
            self.center, self._shift = (float(x), float(z)), None
            self._handles_changed()
            return
        self._shift = self.FE.nearest(rs, x, z)
        self.center = self.FE.centre(rs, self._shift)
        dx, dz = self.FE.offset_of(self._shift)
        self.to_lbl.setText(f"To {dx:g}, {dz:g}")
        self._handles_changed()

    def drag_to(self, x, z):
        rs = self._rs()
        if rs is not None and self.FE.nearest(rs, x, z) != self._shift:
            self.place(x, z)

    def drop_at(self, x, z):
        self.place(x, z)

    def handles(self):
        if self.center is None or self._shift is None or self._river is None:
            return None
        return tuple(self._cmd("-", dry_run=False))

    # -- the shape and the laws --
    def _cmd(self, target, *, dry_run, report=None):
        return self.FE.command(target, self._shift or (0, 0), move_from=self.river_at(), dry_run=dry_run,
                               report=report)

    def _shape(self, rs, ground_y):
        return self.FE.placed(rs, self._shift or rs.shifts[0])

    def _preview_at(self, rs, rim):
        if self._river is None or self._shift is None:
            return {"ok": False, "why": "reading", "where": [], "blocks": []}
        held = self._river[2]
        return self.FE.preview(rs, self._shift, river_at=self.river_at(),
                               occupied=lambda cells: {c: sorted(held[c]) for c in cells if c in held})

    def _step_cells(self, verdict):
        """A move writes the new placement's cells and empties the old one's: the verdict names both."""
        return [tuple(b) for b in (verdict or {}).get("blocks") or []] or \
            self._rs().cells_at(self._shift) + (self._rs().cells_at(self.river_at()) if self.river_at() else [])

    def _show_point(self, v):
        return tuple(v["bridge"]) if v.get("bridge") else super()._show_point(v)

    # -- the words --
    def _pass_text(self, v, where):
        n = sum(1 for g in v.get("gates") or [] if g.get("verdict") != "RED")
        dx, dz = self.FE.offset_of(self._shift)
        mf = v.get("move_from")
        frm = f"moved from {mf[0]:g}, {mf[1]:g} to {dx:g}, {dz:g}" if mf else f"carried to {dx:g}, {dz:g}"
        return (f"Passes every gate ({n}): the river {frm}, {v.get('files')} files. Accept "
                + ("moves" if mf else "carries") + " it in the draft.", "ok")

    def _preview_text(self, pv):
        if pv["why"] == "reading":
            return "Reading where the river stands and what holds each placement…", ""
        if pv["why"] == "the river is here now":
            free = self.FE.free_shifts(self._rs(), river_at=self.river_at(),
                                       occupied=lambda cells: {c: sorted(self._river[2][c]) for c in cells
                                                         if c in self._river[2]})
            spots = ", ".join("{:g}, {:g}".format(*self.FE.offset_of(s)) for s in free[:3])
            return ("The river is here now. " + (f"It can move to {spots}." if free else
                                                 "No other placement is free of edits."), "warn")
        return f"Not here: {pv['why']}.", "warn"
