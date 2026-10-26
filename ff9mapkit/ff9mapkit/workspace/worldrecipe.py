"""The World tab's recipe bar (overworld editor rung C3): the draft as a ``world-fuse`` recipe.

Every Accept of a carry tool is one row of the draft's recipe (``world.draft.history``). The bar says how many, walks
them with Undo and Redo (byte for byte, from each step's snapshots: no verb re-runs), saves them as a TOML that
``world-fuse`` composes (``world.recipe.dumps``), and opens one: a fresh draft, then each row composed by
``world-fuse`` itself, one job per row, so every row is its own undoable step.

THE CLI STAYS THE ORACLE here too: opening a recipe never carves in the Workspace's process.

EDITING A PLACED STEP (rung C9): a click on the 3D view picks the step placed there (``world.recipe.step_at``), and
the bar's second row names it, with Edit and Delete. Edit lifts the step and the ones after it out of the draft
(``world.draft.begin_edit``) and opens the step's own card on its row; the card's Accept writes the edited shape in
its place. Delete puts nothing in its place. Then the steps after it go back on top in their order: each REPLAYED
from its record where no block it reads changed (``draft.dirty_after``), else composed again by ``world-fuse``. A
step that refuses on the new ground stops the edit, and the draft goes back exactly as it was.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMessageBox, QPushButton, QWidget

from . import widgets
from .worldforest import JobRunner, StepWorker, kit_cwd


class RecipeBar(QWidget):
    """``source_fn()`` the mod folder the tab shows; ``game_fn()`` the install; ``on_changed(draft)`` re-reads the
    view and the tools after the draft moved; ``on_select(step)`` marks the picked step on the view (None: no step);
    ``on_edit(row, label)`` opens the step's card on its row; ``on_hold(held)`` says when the bar holds the draft
    (:meth:`holding`: the folder must not change under it); ``cards_writing()`` says a card's job is writing now. ``runner``, ``ask``, ``save_path_fn(default)`` /
    ``open_path_fn()`` (file dialogs) and ``drafts_root`` are the test and snap seams. ``sync``: Open...'s draft
    copy and history steps inline (default: when a runner is injected, a test's or a snap's), else on a worker."""

    def __init__(self, pal, *, game_fn, source_fn, on_changed=None, runner=None, drafts_root=None, ask=None,
                 save_path_fn=None, open_path_fn=None, on_select=None, on_edit=None, on_hold=None,
                 cards_writing=None, sync=None):
        super().__init__()
        self.pal = pal
        self._game_fn, self._source_fn, self._on_changed = game_fn, source_fn, on_changed
        self._on_hold = on_hold
        self._cards_writing = cards_writing or (lambda: False)
        self._steps = StepWorker(sync=(runner is not None) if sync is None else bool(sync))
        self._runner = runner or JobRunner()
        self._drafts_root = drafts_root
        self._ask = ask or (lambda title, text: QMessageBox.question(self, title, text)
                            == QMessageBox.StandardButton.Yes)
        self._save_path_fn = save_path_fn or self._save_dialog
        self._open_path_fn = open_path_fn or self._open_dialog
        self._queue = None                               # an opened recipe's rows still to compose
        self._on_select, self._on_edit = on_select, on_edit
        self._sel = None                                 # the picked step's index (rung C9), or None
        self._edit = None                                # the open edit of a placed step, or None
        self._job = None                                 # "revert" / "promote" while an in-game step's job runs (C19)
        self._prep = None                                # the in-game step being taken out of the game to edit
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 0, 2, 0)
        lay.setSpacing(8)
        lay.addWidget(widgets.role_label("Recipe", "cardtitle"))
        self.status_lbl = widgets.role_label("", "caption")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setAccessibleName("Recipe")
        lay.addWidget(self.status_lbl, 1)
        # rung C9: a picked step's actions, in the same row (the status names the step): a row of their own raised the
        # window's floor to 871px at 150%, past a 1280x850 window, and squeezed an open card's verdict
        for attr, text, tip, slot in (
                ("edit_btn", "Edit", "Open this step's card on its handles: move, turn or retune it, then Accept. The "
                 "steps after it go back on top.", self.edit),
                ("delete_btn", "Delete", "Take this step out of the recipe; the steps after it go back on top.",
                 self.delete),
                ("cancel_btn", "Cancel edit", "Stop putting the steps back and leave the draft exactly as it was.",
                 lambda: self.cancel_edit())):
            b = QPushButton(text)
            b.setProperty("role", "quiet")
            b.setToolTip(tip)
            b.clicked.connect(slot)
            b.hide()
            lay.addWidget(b)
            setattr(self, attr, b)
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setProperty("role", "quiet")
        self.undo_btn.clicked.connect(self.undo)
        lay.addWidget(self.undo_btn)
        self.redo_btn = QPushButton("Redo")
        self.redo_btn.setProperty("role", "quiet")
        self.redo_btn.clicked.connect(self.redo)
        lay.addWidget(self.redo_btn)
        self.save_btn = QPushButton("Save…")              # (the row's title says what: a recipe)
        self.save_btn.setProperty("role", "quiet")
        self.save_btn.setToolTip("Save the recipe: the draft's edits as a TOML world-fuse composes (ff9mapkit "
                                 "world-fuse <recipe> --mod-folder <folder> makes the same bytes).")
        self.save_btn.clicked.connect(self.save)
        lay.addWidget(self.save_btn)
        self.open_btn = QPushButton("Open…")
        self.open_btn.setProperty("role", "quiet")
        self.open_btn.setToolTip("Open a recipe: compose it into a fresh draft of this folder, one world-fuse job per "
                                 "row (each row undoable). The install is not touched.")
        self.open_btn.clicked.connect(self.open_recipe)
        lay.addWidget(self.open_btn)
        self.refresh()

    # -- the draft --
    def source(self) -> Path:
        return Path(self._source_fn())

    def draft(self):
        from ..world import draft as D
        p = D.draft_path(self.source(), root=self._drafts_root)
        return p if D.is_draft(p) else None

    def refresh(self):
        """Say what the recipe holds and which way it can walk."""
        from ..world import draft as D
        d = self.draft()
        if d is not None and self._edit is None and self._queue is None and D.history(d)["edit"] \
                and D.promote_owed(d) is None:       # (one the game is owed a promote for is :meth:`settle`'s)
            try:                                         # an edit this Workspace did not open (it closed mid-edit,
                D.cancel_edit(d)                         # or the disk refused its cancel: R4-4)
            except (ValueError, OSError):
                pass
        h = D.history(d) if d is not None else {"steps": [], "cursor": 0, "promoted": 0}
        steps, cur, prom = h["steps"], h["cursor"], h["promoted"]
        busy = self._queue is not None or self._edit is not None or self._job is not None
        if not steps:
            text = "No edits yet: each Accept adds a row, and Save writes them as a recipe for world-fuse."
        else:
            text = f"{cur} step{'s' if cur != 1 else ''}"
            if cur:
                text += f", the last {steps[cur - 1]['label']}"
            if len(steps) > cur:
                text += f"; {len(steps) - cur} undone"
            if prom:
                text += f"; the first {prom} in the game (promoted)"
        if self._sel is not None and self._sel >= cur:
            self._sel = None
        if self._queue is not None:
            left = len(self._queue["rows"])
            text = f"Composing {self._queue['name']}: {self._queue['done']} row(s) done, {left} to go…"
        elif self._job == "revert":
            text = (f"Taking the promote out of the game to {self._prep['mode']} step {self._prep['k'] + 1} "
                    f"(Revert promote)…")
        elif self._job == "promote":
            text = "Promoting the recipe into the game again…"
        elif self._edit is not None:
            text = self._edit_text(self._edit)
        elif self._sel is not None:
            i = self._sel
            text = f"Step {i + 1} of {cur}: {steps[i]['label']}" + (
                ". It is in the game: Edit or Delete takes its promote out of the game first, and promotes the "
                "recipe again after." if i < prom else ".")
        self.status_lbl.setText(text)
        widgets.set_state(self.status_lbl, "")
        editing = self._edit is not None
        for b in (self.undo_btn, self.redo_btn, self.save_btn, self.open_btn):
            b.setVisible(not editing)                    # an open edit holds the history: they wait for it
        self.undo_btn.setEnabled(not busy and cur > prom)
        self.undo_btn.setToolTip(f"Undo: {steps[cur - 1]['label']}" if cur > prom else
                                 "The steps here are in the game: Revert promote first." if cur else "Nothing to undo.")
        self.redo_btn.setEnabled(not busy and len(steps) > cur)
        self.redo_btn.setToolTip(f"Redo: {steps[cur]['label']}" if len(steps) > cur else "Nothing to redo.")
        self.save_btn.setEnabled(not busy and cur > 0)
        self.open_btn.setEnabled(not busy)
        picked = self._sel is not None and not busy
        self.edit_btn.setVisible(picked)
        self.delete_btn.setVisible(picked)
        self.cancel_btn.setVisible(editing and "queue" in self._edit)   # an open card has its own Cancel edit
        if picked:
            from ..world import recipe as RC
            live, table = self._sel < prom, steps[self._sel]["row"].get("table")
            self.edit_btn.setEnabled(table in RC.EDITABLE_TABLES)
            self.edit_btn.setToolTip(("Open this step's card on its handles: move, turn or retune it, then Accept. The "
                                      "steps after it go back on top." if table in RC.EDITABLE_TABLES else
                                      f"A {table} step has no card that opens on it: Delete it, then place it again.")
                                     + (" It is in the game: its promote comes out of the game while you edit, and "
                                        "the recipe is promoted again when you accept or cancel." if live else ""))
            self.delete_btn.setEnabled(True)
            later = self._later_out_of_game(self._sel)
            if later:                                    # (an in-game step with steps after the game's on top)
                for b in (self.edit_btn, self.delete_btn):
                    b.setEnabled(False)
                    b.setToolTip(self._later_text(later)[0].upper() + self._later_text(later)[1:])
                self.status_lbl.setText(f"{text} {self._later_text(later)[0].upper()}{self._later_text(later)[1:]}")
        if self._on_hold is not None:
            self._on_hold(self.holding())

    def holding(self) -> bool:
        """The bar holds the draft: an edit is open (its steps lifted out), an opened recipe's rows are going in, or an
        in-game step's chain is taking its promotes out of the game or putting them back. The folder the tab shows
        must not change meanwhile: a switch closed the card, and the cancel went to the new folder's draft (review
        of C19)."""
        return self._edit is not None or self._queue is not None or self._job is not None or self._prep is not None

    def writing_live(self) -> bool:
        """An in-game step's chain is taking its promotes out of the game or putting them back: its jobs write the live
        folder and the draft's records, so no card may write either meanwhile."""
        return self._job is not None or self._prep is not None

    @staticmethod
    def _edit_text(e) -> str:
        after = e["applied"] - 1
        them = f"the {after} step{'s' if after != 1 else ''} after it"
        if "queue" in e:
            done = e["replayed"] + e["rerun"]
            return (f"{'Deleting' if e['mode'] == 'delete' else 'Edited'} step {e['k'] + 1}, {e['label']}: putting "
                    f"{them} back on top, {done} done, {len(e['queue'])} to go…")
        return (f"Editing step {e['k'] + 1}, {e['label']}, in its card below."
                + (f" {them[0].upper()}{them[1:]} come{'s' if after == 1 else ''} back on top when you accept."
                   if after else ""))

    # -- the picked step (rung C9) --
    def steps(self) -> list:
        """The applied steps (the recipe), each its history record."""
        from ..world import draft as D
        d = self.draft()
        if d is None:
            return []
        h = D.history(d)
        return h["steps"][:h["cursor"]]

    def pick(self, x, z):
        """A click on the view with no card open: pick the step placed there (or none). Returns its index."""
        from ..world import recipe as RC
        if self._edit is not None or self._queue is not None:
            return None
        i = RC.step_at(self.steps(), x, z)
        self.select(i)
        return i

    def select(self, i):
        self._sel = i
        self.refresh()
        if self._on_select is not None:
            steps = self.steps()
            self._on_select(steps[i] if i is not None and i < len(steps) else None)

    # -- edit and delete (rung C9) --
    def edit(self):
        """Open the picked step in its card: the draft goes back to before it (the step and the ones after it lifted
        out), and the card opens on its row. A step that is in the game (promoted) is taken out of it first
        (:meth:`_unpromote`, rung C19)."""
        from ..world import draft as D
        d, i = self.draft(), self._sel
        if d is None or i is None or self._edit is not None or self._job is not None:
            return
        if self._card_writes("opened") or self._out_of_game(i, "opened"):
            return
        if i < D.history(d)["promoted"]:
            s = self.steps()[i]
            if not self._ask("Edit a step that is in the game?", f"Step {i + 1}, {s['label']}, is in the game. To edit "
                             f"it, its promote is taken back out of the game first (Revert promote: "
                             f"{self.source().name} exactly as it was before it), the step opens in its card, and when "
                             "you accept or cancel the recipe is promoted again. The game shows it on its next world "
                             "load."):
                return
            self._unpromote(d, i, "edit")
            return
        self._open_edit(d, i)

    def _later_out_of_game(self, i):
        """For step ``i`` in the game: how many steps after the game's are applied but not in it (0 for a step not in
        the game). The chain's promote back writes the whole draft, so it would carry them into the game; setting
        them aside by undo and redo broke where their blocks met a promote's (review of C19, twice)."""
        from ..world import draft as D
        d = self.draft()
        if d is None:
            return 0
        h = D.history(d)
        return h["cursor"] - h["promoted"] if i is not None and i < h["promoted"] else 0

    def _card_writes(self, what) -> bool:
        """Refuse any write of the bar's (Edit, Delete, Undo, Redo, Open) while a card's job writes the draft or the
        live folder: the two would write the same draft and its records at once, and opening the step's card (or the
        chain's start) closes the open card (review of the C19 fixes; the bar's own writes, its fourth round)."""
        if self._cards_writing():
            self._refuse(f"Not {what}: a card is still writing (its Accept, Promote or Revert promote); wait for it "
                         "to finish.")
            return True
        return False

    def _refuse(self, note):
        """Say a refusal. Nothing moved, so no one is told the draft did: the draft-moved pass (every card's island
        read again, the view reloaded from a draft mid-write, whose own reload the busy view then dropped) ran for
        a click that changed nothing (review of the C19 fixes, fifth round)."""
        self.refresh()
        widgets.set_state(self.status_lbl, "error")
        self.status_lbl.setText(note)

    def _out_of_game(self, i, what) -> bool:
        """Refuse a chain for in-game step ``i`` while steps after the game's are out of it (the law at the call
        site; the buttons say it too)."""
        n = self._later_out_of_game(i)
        if n:
            self._refuse(f"Not {what}: {self._later_text(n)}")
        return bool(n)

    @staticmethod
    def _later_text(n) -> str:
        return (f"the {n} step{'s' if n != 1 else ''} after the game's {'are' if n != 1 else 'is'} not in the game. "
                "Promote them (from a card) or Undo them first: an in-game step opens with nothing after the "
                "game's steps on top.")

    def _open_edit(self, d, i, *, fence=None):
        """``fence``: the steps that were in the game before the chain took them out (rung C19), promoted again when
        the edit closes; None for a step that was not in the game."""
        from ..world import draft as D
        s = D.history(d)["steps"][i]                     # the step of the draft it opens in, not the folder shown
        try:
            e = D.begin_edit(d, i)
        except (ValueError, OSError) as err:            # (an OSError: the disk refused a pending abort, H2)
            self._closed(d, {"fence": fence}, f"Not opened: {err}.", "error")
            return
        self._edit = {"k": i, "mode": "edit", "label": s["label"], "lifted": e["lifted"], "applied": e["applied"],
                      "fence": fence, "draft": d}
        self._moved()
        if self._on_select is not None:
            self._on_select(None)
        if self._on_edit is not None:
            self._on_edit(s["row"], s["label"])

    def _edit_draft(self, e):
        """The draft edit ``e`` is open in (it never changes under the edit), else the shown folder's."""
        from ..world import draft as D
        d = (e or {}).get("draft")
        return Path(d) if d is not None and D.is_draft(Path(d)) else self.draft()

    def edit_accepted(self, note=""):
        """The card wrote the edited shape in the step's place: put the steps after it back on top. ``note``: what the
        card had to say of its Accept (disc 4's), said with the edit once it closes (round 4, R4-5)."""
        from ..world import draft as D
        e = self._edit
        d = self._edit_draft(e)
        if d is None or e is None:
            return
        new = D.history(d)["steps"][e["k"]]
        e["new_label"], e["note"] = new["label"], note
        self._start_put_back(d, D.dirty_after(set(), e["lifted"][0], new))

    def delete(self):
        from ..world import draft as D
        d, i = self.draft(), self._sel
        if d is None or i is None or self._edit is not None or self._job is not None:
            return
        if self._card_writes("deleted") or self._out_of_game(i, "deleted"):
            return
        steps = self.steps()
        s, after = steps[i], len(steps) - i - 1
        live = i < D.history(d)["promoted"]
        if not self._ask("Delete the step?", f"Take step {i + 1}, {s['label']}, out of the draft's recipe?"
                         + (f" The {after} step{'s' if after != 1 else ''} after it "
                            f"{'go' if after != 1 else 'goes'} back on top (any whose ground changed is composed again "
                            "by world-fuse)." if after else "")
                         + (" It is in the game: its promote is taken back out of the game first, and the recipe "
                            "without it is promoted again." if live else "")):
            return
        if live:
            self._unpromote(d, i, "delete")
            return
        self._run_delete(d, i)

    def _run_delete(self, d, i, *, fence=None):
        from ..world import draft as D
        s = D.history(d)["steps"][i]
        try:
            e = D.begin_edit(d, i)
        except (ValueError, OSError) as err:            # (an OSError: the disk refused a pending abort, H2)
            self._closed(d, {"fence": fence}, f"Not deleted: {err}.", "error")
            return
        self._edit = {"k": i, "mode": "delete", "label": s["label"], "lifted": e["lifted"], "applied": e["applied"],
                      "fence": fence, "draft": d}
        self.refresh()                                   # (the hold begins: an idle card is put away)
        if self._on_select is not None:
            self._on_select(None)
        self._start_put_back(d, D.dirty_after(set(), e["lifted"][0], None))

    def _start_put_back(self, d, dirty):
        e = self._edit
        e.update(dirty=dirty, queue=list(e["lifted"][1:e["applied"]]), replayed=0, rerun=0)
        self._put_back(d)

    def _put_back(self, d):
        """The next lifted step back on top: replayed from its record where nothing it reads changed, else composed
        again by world-fuse (a job); when none is left the edit closes."""
        from ..world import draft as D
        from ..world import recipe as RC
        e = self._edit
        while e["queue"]:
            s = e["queue"][0]
            try:
                if not RC.replay_window(s) & e["dirty"] and D.replay(d, s):
                    e["queue"].pop(0)
                    e["replayed"] += 1
                    continue
                D.begin_step(d, RC.row_cells(s["row"]))
            except OSError as err:                       # (the disk refused a step's record: R4-6)
                self._put_back_refused(s, err)
                return
            tmp = Path(tempfile.mkdtemp(prefix="ff9_edit_")) / "row.toml"
            tmp.write_text(RC.dumps_one(dict(s["row"])), encoding="utf-8")
            argv = self._fuse_argv(tmp, d)
            self.refresh()
            self._runner.start(argv, kit_cwd(), lambda code, text, s=s: self._put_back_done(d, s, code, text))
            return
        D.finish_edit(d)
        self._edit = None
        n = e["replayed"] + e["rerun"]
        back = (f" The {n} step{'s' if n != 1 else ''} after it {'are' if n != 1 else 'is'} back on top "
                f"({e['replayed']} as they were, {e['rerun']} composed again on the new ground)." if n else "")
        if e["mode"] == "delete":
            self._sel = None
            if e.get("fence") is not None:               # the deleted step was one of the game's: one fewer goes back
                e["fence"] -= 1
                D.owe_promote(d, e["fence"])
            self._closed(d, e, f"Deleted step {e['k'] + 1}, {e['label']}.{back}", "ok")
            return
        self._sel = e["k"]
        said = f" {e['note']}" if e.get("note") else ""
        self._closed(d, e, f"Edited step {e['k'] + 1}: {e['label']} is now {e.get('new_label', e['label'])}.{back}"
                     f"{said}", "warn" if said else "ok")
        if self._on_select is not None:
            self._on_select(self.steps()[e["k"]])

    def _put_back_done(self, d, s, code, text):
        from ..world import draft as D
        e = self._edit
        if e is None:
            return
        if code != 0:
            try:
                D.abort_step(d)
            except OSError:                              # (the cancel's own abort finishes it: R4-6)
                pass
            last = [ln for ln in text.splitlines() if ln.strip()][-1:] or [f"exit code {code}"]
            what = "deleted" if e["mode"] == "delete" else "edited"
            self.cancel_edit(f"Not {what}: on the new ground, {s['label']} (a step after it) refuses: {last[0]}. "
                             "The draft is exactly as it was.", "error")
            return
        try:
            new = D.commit_step(d, s["row"], s["label"])
        except OSError as err:
            self._put_back_refused(s, err)
            return
        e["dirty"] = D.dirty_after(e["dirty"], s, new)
        e["queue"].pop(0)
        e["rerun"] += 1
        self._put_back(d)

    def _put_back_refused(self, s, err):
        """A step after the edited one could not be put back on top because the disk refused its record: the edit
        is cancelled, the draft as it was (the pending step taken back by the cancel's abort). It left the job's
        done unseen, the bar saying the steps were going back while nothing ran (review of the perf fixes, round 4,
        R4-6)."""
        what = "deleted" if self._edit["mode"] == "delete" else "edited"
        self.cancel_edit(f"Not {what}: {s['label']} (a step after it) could not be put back on top ({err}). The "
                         "draft is exactly as it was.", "error")

    def cancel_edit(self, note=None, state=""):
        """Close the open edit, the draft exactly as it was before it (the card's Cancel edit, a closed card, a step
        that refused on the new ground, the bar's own Cancel edit while the steps are put back)."""
        from ..world import draft as D
        e = self._edit
        if e is None:
            return
        d = self._edit_draft(e)                          # the edit's own draft, whatever the tab shows now
        self._edit = None
        if "queue" in e:
            self._runner.kill()
        undone = d is not None
        if d is not None:
            try:
                D.cancel_edit(d)
            except (ValueError, OSError) as err:         # (an OSError: the disk refused it; closed once it lets: R4-4)
                note, state, undone = f"The edit could not be undone: {err}.", "error", False
                if e.get("fence") is not None:
                    note += " The game does not have the recipe now; Promote it from a card."
                D.settle_promote(d)                      # (a draft not known to be as it was is never promoted)
        self._sel = e["k"]
        note = note or f"Edit cancelled: the draft is exactly as it was, {e['label']} in its place."
        # an in-game step goes back into the game only from a draft known to be as it was
        self._closed(d, e if undone else {**e, "fence": None}, note, state)
        if self._on_select is not None:
            steps = self.steps()
            self._on_select(steps[e["k"]] if e["k"] < len(steps) else None)

    # -- a step that is in the game (rung C19): out of it, the edit, back into it --
    def _unpromote(self, d, i, mode):
        """Take the draft's promotes back out of the game, newest first, until step ``i`` is no longer promoted, then
        open the edit (or the delete); when it closes, :meth:`_closed` promotes the recipe again. Each revert is
        ``world-promote --revert`` (it refuses over later work at its blocks); one refusing after another went
        through promotes straight back, so the game is never left half reverted. The FENCE is how many steps were in
        the game when the chain began: the promote back is those steps, never a step placed after them that was not
        promoted (:meth:`_repromote`)."""
        from ..world import draft as D
        self._prep = {"k": i, "mode": mode, "reverted": 0, "fence": D.history(d)["promoted"]}
        D.owe_promote(d, self._prep["fence"])            # on disk: a Workspace that dies mid-chain owes it still
        self._revert_next(d)

    def _revert_next(self, d):
        from ..world import draft as D
        p = self._prep
        if D.history(d)["promoted"] <= p["k"]:
            self._prep, self._job = None, None
            if self.draft() is None or Path(self.draft()) != Path(d):    # a scan begun before the chain moved the tab
                what = "opened" if p["mode"] == "edit" else "deleted"   # off its folder: its cards would open there
                self._repromote(d, p["fence"], f"Not {what}: the tab moved to another folder while the step's promote "
                                "came out of the game.", "error")
                return
            (self._open_edit if p["mode"] == "edit" else self._run_delete)(d, p["k"], fence=p["fence"])
            return
        if D.last_promote(d) is None:
            self._fail_revert(d, "the step is marked in the game but the draft holds no promote to revert")
            return
        report = Path(tempfile.mkdtemp(prefix="ff9_revert_")) / "verdict.json"
        argv = [sys.executable, "-m", "ff9mapkit", "--game", str(self._game_fn()), "world-promote", str(d),
                "--revert", "--report-json", str(report)]
        self._job = "revert"
        self.refresh()
        self._runner.start(argv, kit_cwd(), lambda code, text: self._reverted(d, report, code, text))

    def _reverted(self, d, report, code, text):
        from ..world.forestedit import read_verdict
        v = read_verdict(report) or {}
        if not v.get("ok"):
            self._fail_revert(d, v.get("error") or ([ln for ln in text.splitlines() if ln.strip()][-1:]
                                                    or [f"exit code {code}"])[0])
            return
        self._prep["reverted"] += 1
        self._moved()                                    # the tab draws the folder as it now stands
        self._revert_next(d)

    def _fail_revert(self, d, why):
        p, self._prep, self._job = self._prep, None, None
        what = "opened" if p["mode"] == "edit" else "deleted"
        note = f"Not {what}: its promote could not be taken back out of the game ({why})."
        if p["reverted"]:                                # some went: put the game back as it was
            self._repromote(d, p["fence"], note, "error")
        else:
            from ..world import draft as D
            D.settle_promote(d)
            self._moved(note + " The game and the draft are as they were.", "error")

    def _closed(self, d, e, note, state):
        """The edit (or delete) closed: promote the recipe again when the step was taken out of the game for it."""
        if e.get("fence") is not None and d is not None:
            self._repromote(d, e["fence"], note, state)
        else:
            self._moved(note, state)

    def _repromote(self, d, fence, note, state):
        """Promote the recipe's first ``fence`` steps into the game again. ``world-promote`` writes every edit the
        draft holds, and a chain opens only with nothing after the game's steps on top (:meth:`_out_of_game`), so
        that is exactly the fence's steps."""
        from ..world import draft as D
        if D.history(d)["promoted"] >= fence:            # the promotes still standing cover them (a deleted step was
            D.settle_promote(d)                          # all of the newest): the game holds them already
            folder = Path((D.read_meta(d) or {}).get("source") or self.source()).name
            self._moved(f"{note} {folder} holds the recipe's first {fence} step{'s' if fence != 1 else ''} already "
                        "(their promotes stand): nothing to promote again.", state)
            return
        if D.history(d)["cursor"] > fence:               # (never, by the refusal; a promote would carry them in)
            D.settle_promote(d)
            self._moved(f"{note} Promoting it again did not run: the draft holds steps after the game's, which the "
                        "game never had; the game does not have the recipe now. Promote it from a card.", "error")
            return
        report = Path(tempfile.mkdtemp(prefix="ff9_promote_")) / "verdict.json"
        argv = [sys.executable, "-m", "ff9mapkit", "--game", str(self._game_fn()), "world-promote", str(d),
                "--report-json", str(report)]
        self._job = "promote"
        self.refresh()
        self._runner.start(argv, kit_cwd(), lambda code, text: self._repromoted(d, note, state, report, code, text))

    def _repromoted(self, d, note, state, report, code, text):
        from ..world import draft as D
        from ..world.forestedit import read_verdict
        self._job = None
        v = read_verdict(report) or {"ok": False, "error": ([ln for ln in text.splitlines() if ln.strip()][-1:]
                                                            or [f"exit code {code}"])[0]}
        D.settle_promote(d)                              # it ran: a refusal is said now, never retried at each launch
        folder = Path((D.read_meta(d) or {}).get("source") or self.source()).name
        if v.get("ok"):
            self._moved(f"{note} Promoted into {folder} again: the game shows it on its next world load.", state)
        else:
            self._moved(f"{note} Promoting it again did not run ({v.get('error')}): the game does not have the "
                        "recipe now; Promote it from a card.", "error")

    def settle(self):
        """Put right a promote the game is owed and no chain here is paying (rung C19): a Workspace that closed or
        died with a step that is in the game taken out of it. The draft goes back to before the edit, and the steps
        that were in the game are promoted again. The tab calls it once its 3D page and this bar are up."""
        from ..world import draft as D
        d = self.draft()
        if d is None or self._edit is not None or self._queue is not None or self._job is not None \
                or self._prep is not None:
            return
        fence = D.promote_owed(d)
        if fence is None:
            return
        note = "The Workspace closed with a step that is in the game taken out of it"
        if D.history(d)["edit"]:
            try:
                D.cancel_edit(d)
            except (ValueError, OSError) as err:
                D.settle_promote(d)
                self._moved(f"{note}, and it could not be undone ({err}): the game does not have the recipe now; "
                            "Promote it from a card.", "error")
                return
            note += ", its edit open: the draft is back as it was before the edit."
        else:
            note += "."
        self._repromote(d, fence, note, "")

    def closing_runner(self):
        """The Workspace is closing (``WorldDoc.shutdown``): the runner of the bar's job, to wait for, or None. An
        opened recipe stops after the row that runs: each row is its own step and the recipe owes the game nothing,
        so composing the rest inside closeEvent froze the window for minutes (review of the C19 fixes, third
        round)."""
        if self._queue is not None:
            self._queue["closing"] = True
        if self._steps.busy():                           # an opened recipe's draft copy or a row's history step
            return self._steps
        return self._runner if self._runner.busy() else None

    def close_in_game_edit(self) -> bool:
        """The Workspace is closing and no job runs: an edit of a step that is in the game is cancelled, and its steps
        promoted back (a job, waited for in turn). True when there was one."""
        if self._edit is None or self._edit.get("fence") is None:
            return False
        self.cancel_edit("The Workspace closed with the edit open: it is cancelled.")
        return True

    def _moved(self, note=None, state="ok"):
        self.refresh()
        if self._on_changed is not None:
            self._on_changed(self.draft())               # (the tab refreshes this bar too: the note goes last)
        if note:
            widgets.set_state(self.status_lbl, state)
            self.status_lbl.setText(note)

    # -- undo, redo --
    def undo(self):
        from ..world import draft as D
        d = self.draft()
        if d is None or self._card_writes("undone"):
            return
        try:
            s = D.undo(d)
        except (ValueError, OSError) as e:               # (an OSError: the disk refused a pending abort, round 3 H4)
            self._moved(f"Not undone: {e}.", "error")
            return
        self._moved(f"Undone: {s['label']}.", "")

    def redo(self):
        from ..world import draft as D
        d = self.draft()
        if d is None or self._card_writes("redone"):
            return
        try:
            s = D.redo(d)
        except (ValueError, OSError) as e:               # (an OSError: the disk refused a pending abort, round 3 H4)
            self._moved(f"Not redone: {e}.", "error")
            return
        self._moved(f"Redone: {s['label']}.", "")

    # -- save, open --
    def recipe_text(self) -> str:
        from ..world import draft as D
        from ..world import recipe as RC
        return RC.dumps(D.recipe_rows(self.draft()), base=self.source().name)

    def save(self):
        d = self.draft()
        if d is None:
            return
        path = self._save_path_fn(f"{self.source().name}-recipe.toml")
        if not path:
            return
        Path(path).write_text(self.recipe_text(), encoding="utf-8")
        self._moved(f"Saved the recipe to {path}.", "ok")

    def open_recipe(self):
        from ..world import draft as D
        from ..world import recipe as RC
        if self._card_writes("opened"):
            return
        path = self._open_path_fn()
        if not path:
            return
        try:
            rows = RC.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            self._moved(f"Not opened: {e}.", "error")
            return
        d = self.draft()
        if d is not None and (D.history(d)["steps"] or D.edits(d)):
            if not self._ask("Replace the draft?", f"Compose {Path(path).name} into a fresh draft of "
                             f"{self.source().name}? The draft's current edits and their history are deleted (the "
                             "install is not touched)."):
                return
        self._queue = {"name": Path(path).name, "rows": list(rows), "done": 0}   # held from here to the last row
        self.refresh()
        source, game, root = self.source(), self._game_fn(), self._drafts_root

        def fresh():                                     # (2-10 s on the window's thread: PERF.md 7)
            if d is not None:
                D.discard(d, root=root)
            return D.ensure_draft(source, game=game, root=root)
        self._steps.start(fresh, self._opened)

    def _opened(self, d, err):
        if self._queue is None:
            return
        if err is not None:
            self._queue = None
            self._moved(f"Not opened: the fresh draft could not be made ({err}).", "error")
            return
        self._next_row(d)

    def _next_row(self, d):
        from ..world import draft as D
        from ..world import recipe as RC
        q = self._queue
        if not q["rows"]:
            self._queue = None
            self._moved(f"Composed {q['name']}: {q['done']} row{'s' if q['done'] != 1 else ''} into the draft.", "ok")
            return
        if q.get("closing"):
            self._queue = None
            self._moved(f"Stopped {q['name']} as the Workspace closed: {q['done']} row{'s' if q['done'] != 1 else ''} "
                        f"composed into the draft, {len(q['rows'])} not.", "warn")
            return
        row = q["rows"][0]
        cells = RC.row_cells(row)                        # (a whole-map step for an island, carry or sink row: on a
        self._steps.start(lambda: D.begin_step(d, cells),   # worker, PERF.md 7)
                          lambda _r, err: self._row_snapshotted(d, row, err))

    def _row_snapshotted(self, d, row, err):
        from ..world import recipe as RC
        q = self._queue
        if q is None:
            return
        if err is not None:
            self._queue = None
            self._moved(f"Stopped at {RC.label(row)} ({q['done']} row(s) composed): the draft's history could not be "
                        f"snapshotted ({err}).", "error")
            return
        if q.get("closing"):                             # the Workspace closed while the snapshot ran: a row not
            from ..world import draft as D               # started is not run (review of the perf commits)
            self._steps.start(lambda: D.abort_step(d), lambda _r, _err: self._next_row(d))
            return
        tmp = Path(tempfile.mkdtemp(prefix="ff9_recipe_")) / "row.toml"
        tmp.write_text(RC.dumps_one({k: v for k, v in row.items()}), encoding="utf-8")
        argv = self._fuse_argv(tmp, d)
        self.refresh()
        self._runner.start(argv, kit_cwd(), lambda code, text: self._row_done(d, row, code, text))

    def _fuse_argv(self, recipe, d):
        """The world-fuse job that composes one row into the draft ``d``. With ``--allow-overwrite``: THE MANIFEST
        DRIFT GATE refuses to compose over files its world_manifest.json recorded and that changed since, which in a
        live folder means another session wrote them; in a draft they change by design (an undo, an edit's lifted
        steps, a card's Accept), and the draft's history is its record. An edit of an opened recipe refused its own
        put-back on it. The ownership refusal at the write seam (another session's bytes) still stands."""
        return [sys.executable, "-m", "ff9mapkit", "--game", str(self._game_fn()), "world-fuse", str(recipe),
                "--mod-folder", str(d), "--allow-overwrite"]

    def _row_done(self, d, row, code, text):
        from ..world import draft as D
        from ..world import recipe as RC
        q = self._queue
        if q is None:
            return
        if code != 0:
            last = [ln for ln in text.splitlines() if ln.strip()][-1:] or [f"exit code {code}"]

            def stopped(_r, err):
                self._queue = None
                lost = "" if err is None else (f"; its writes could not be taken back ({err}): the draft holds an "
                                               "unrecorded change, taken back when the next step begins")
                self._moved(f"Stopped at {RC.label(row)} ({q['done']} row(s) composed): {last[0]}{lost}", "error")
            self._steps.start(lambda: D.abort_step(d), stopped)
            return
        self._steps.start(lambda: D.commit_step(d, row, RC.label(row)),
                          lambda _r, err: self._row_recorded(d, row, err))

    def _row_recorded(self, d, row, err):
        from ..world import recipe as RC
        q = self._queue
        if q is None:
            return
        if err is not None:                              # its step is left whole: taken back now (round 3, H3)
            from ..world import draft as D

            def taken_back(_r, err2):
                self._queue = None
                back = ("its writes were taken back" if err2 is None else
                        f"its writes stay in the draft until they can be taken back ({err2}): the next step, Undo, "
                        "Redo or Promote takes them back first")
                self._moved(f"Stopped at {RC.label(row)} ({q['done']} row(s) composed): its history step could not "
                            f"be recorded ({err}), so {back}.", "error")
            self._steps.start(lambda: D.abort_step(d), taken_back)
            return
        q["rows"].pop(0)
        q["done"] += 1
        if self._on_changed is not None:
            self._on_changed(d)
        self._next_row(d)

    def _save_dialog(self, default):
        path, _f = QFileDialog.getSaveFileName(self, "Save recipe", default, "Recipe (*.toml)")
        return path

    def _open_dialog(self):
        path, _f = QFileDialog.getOpenFileName(self, "Open recipe", "", "Recipe (*.toml)")
        return path

    def retheme(self, pal):
        self.pal = pal
