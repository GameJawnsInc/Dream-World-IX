"""The World tab's river tool (overworld editor rung C5): move the carried river, whole, to another placement.

The carry cards' frame (:class:`worldforest.CarryTool`) with a river's parts. The card reads where the river stands
in the draft (or the folder) now, from the ledger; a click picks the nearest placement the river fits (a whole-block
shift onto open ocean, ``world.riveredit``), and the ghost is the river's own carried land and its island's coast
ring there. The preview marks a placement free or held (the river's own files do not count: they go first);
``world-river --move-from --dry-run`` judges the rest, and Accept moves it in the draft. A folder with no river in it
gets the plain carry (``world-river --at``).

Edit (rung C12) opens the card on a placed river step's row: its placement picked again among the river's fitting
shifts, once the river's shape is read; and once where the river stands in the draft before the step is read, that
must be where the step moved it from. Pick another placement and Accept.
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
        self._river_ask, self._river_asks = None, 0      # the read of it in flight (its number), and the count
        self._from_check = None                          # an edited row, its move_from held until the river is read
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
        if rs is None or self._river is not None or self._river_ask is not None:
            return                                       # (one read at a time: _forget_river drops one in flight)
        self._river_asks += 1
        ask = self._river_ask = self._river_asks

        def read():                                      # its error carries its number too: a stale read's failure
            try:                                         # must not free the live read's slot (review of the C12 fixes)
                return (ask, target, *self._river_fn(target, rs))
            except Exception as e:                       # noqa: BLE001 -- surfaced on the GUI thread, as _bg's are
                return (ask, target, e, None)
        self._bg("river", read)

    def _forget_river(self):
        """The draft moved (an edit lifting steps out, an Accept, a promote, a discard): where the river stands is
        read again, and a read begun before is dropped when it lands. Its path is the same and its bytes are not, so
        the path alone took a read from before an Edit for the draft before the step, and the move's held
        move_from cancelled the edit against it (review of C12)."""
        self._river = None
        self._river_ask = None

    def _load_soup(self):
        super()._load_soup()
        self._load_river()

    def island_changed(self):
        self._forget_river()
        super().island_changed()

    def _accepted(self, v):
        self._forget_river()                             # the river moved in the draft: read where it is again
        self._shift = None
        super()._accepted(v)

    def _promote_done(self, kind, report, code, text):
        self._forget_river()                             # the folder (or the draft) moved: where is the river now
        super()._promote_done(kind, report, code, text)

    def _discard(self):
        self._forget_river()                             # the target goes back to the folder
        super()._discard()

    def _outline_loaded(self, donor, rs):
        self._try_seat()
        self._load_river()
        if self.center is not None and self._shift is None and self._pending_row is None:
            self.place(*self.center)                     # a click that landed before the read: pick for it now

    # -- a placed river step (rung C12) --
    def load_row(self, row):
        self._from_check = None
        self._pending_row = row
        self._try_seat()

    def _seat_row(self, row):
        rs = self._rs()
        at = tuple(float(v) for v in row["at"])
        if rs is None:                                   # the river's shape: about fifteen seconds, once
            self.center, self._shift = at, None
            return False
        s = next((s for s in rs.shifts if self.FE.offset_of(s) == at), None)
        if s is None:
            raise ValueError(f"its placement {at[0]:g}, {at[1]:g} is not one the river fits on open ocean")
        self._shift = s
        self.center = self.FE.centre(rs, s)
        self.to_lbl.setText(f"To {at[0]:g}, {at[1]:g}")
        self._handles_changed()
        return True

    def _said_back(self, row, mine=None):
        """Where the river stands is a read of its own (the draft's ledger): the placement is held to the row at once,
        and ``move_from`` when that read is in."""
        strip = (lambda r: {k: v for k, v in r.items() if k != "move_from"})
        super()._said_back(strip(row), strip(self._place_row()))
        self._from_check = row
        self._check_from()

    def _place_row(self):
        """The row the placement alone builds (where the river is moved from left out)."""
        from ..world import recipe as RC
        return RC.row_for(self.FE.command("-", self._shift or (0, 0), dry_run=False))

    def _check_from(self):
        row = self._from_check
        if row is None or self._river is None:
            return
        self._from_check = None
        at = self.river_at()
        have = [*self.FE.offset_of(at)] if at is not None else None
        want = [float(v) for v in row["move_from"]] if row.get("move_from") else None
        if have != want:
            where = f"at {have[0]:g}, {have[1]:g}" if have else "nowhere"
            raise ValueError(f"the draft before it holds the river {where}, not where the step moved it from")

    def _on_bg(self, what, serial, result, err):
        if what != "river":
            return super()._on_bg(what, serial, result, err)
        if err is not None:
            self._river_ask = None
            self._say(f"Where the river stands could not be read: {err}", "error")
            return
        ask, target, at, held = result
        if ask != self._river_ask:
            return                                       # begun before the draft moved: not where the river is now
        self._river_ask = None
        if isinstance(at, Exception):
            self._say(f"Where the river stands could not be read: {at}", "error")
            return
        if target != self.target() or self._river is not None:
            return                                       # a read of a folder the tool no longer judges
        self._river = (target, at, held)
        try:
            self._check_from()
        except ValueError as e:
            if self._editing is not None:
                self._refuse_edit(str(e))
                return
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
