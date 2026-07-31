"""The animation PICKER -- choose a clip by watching it, not by hunting an id.

ONE dialog, three modes, because they are three views of the same question ("which clip, on which
rig?") and a second dialog class would fork the preview:

* ``gesture``  -- a one-shot for a cutscene step or a ``[[prop]] pose``. Lists only the model's OWN-FORM
  clips (THE CROSS-FORM CLIP TRAP: a different form code is a different skeleton, and a one-shot played
  across forms twists the model in-game) and answers with the action NAME, which the build resolves
  through that actor's own rig.
* ``movement`` -- one of the five slots an ``[[npc]] anims`` line pins. Lists everything the rig can
  play, cross-form rows MARKED (the movement slots are the one place the any-form join is proven), and
  answers with the numeric id, because that is what the ``.eb`` anim setters take.
* ``slots``    -- the whole ``anims = { stand = …, walk = … }`` line at once: five rows, each with its
  current value, a Browse into ``movement`` mode, and an Auto that clears the slot back to whatever the
  block's model/preset resolves. It answers with the formatted line.

WHICH RIG is never guessed here: the caller hands in a
:class:`~ff9mapkit.blockmodel.BlockModel` -- the same precedence the BUILD spends -- so the picker can
never scope itself to a different model than the one the field ships (a preset NPC's clips are the
ARCHETYPE's model's, not the block's absent ``model =``). A block with no model at all opens unscoped
with the reason in a hint row rather than an empty, unexplained list.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout)

from .. import catalog
from ..editor import forms
from . import clipplayer, thumbs as thumbs_mod, widgets

MODES = ("gesture", "movement", "slots")
_PREVIEW = 200                                   # the frame box (px) -- an IMAGE, not text-bearing geometry


def _rows_for(model, mode):
    """The clip rows this mode offers for a model: gesture = own-form only (deduped by label, the
    movement tier's slot names first), movement = everything with the cross-form ones marked."""
    if model is None:
        return []
    rows, seen = [], set()
    for r in catalog.clip_inventory(model.id):
        if mode == "gesture" and not r["own_form"]:
            continue                             # a different form is a different skeleton
        if r["label"] in seen:
            continue
        seen.add(r["label"])
        rows.append(r)
    return rows


class AnimPickerDialog(clipplayer.ClipPlayer, QDialog):
    """Pick one clip (or a whole movement set) with the frames rendered in front of you.

    ``result`` is the string to write back into the form field: an action NAME (gesture), a numeric id
    (movement), or the ``stand=…, walk=…`` line (slots) -- and None on Cancel."""

    def __init__(self, parent, palette, *, mode="gesture", block=None, current="", anim_frames=None,
                 hint="", label="animation"):
        super().__init__(parent)
        if mode not in MODES:
            raise ValueError(f"unknown anim picker mode {mode!r} (know: {', '.join(MODES)})")
        self.pal = palette
        self.mode = mode
        self.block = block
        self.result = None
        self._single = mode in ("gesture", "movement")
        self.model = catalog.model(block.model) if (block is not None and block.model is not None) else None
        self._init_player(anim_frames)            # the shared service: the slots mode's nested Browse reuses it
        self.setWindowTitle({"gesture": "Pick an animation", "movement": "Pick a movement clip",
                             "slots": "Movement clips"}[mode])
        lay = QVBoxLayout(self)
        lay.addWidget(self._scope_label(label))
        if self._single:
            self._build_single(lay, current)
        else:
            self._build_slots(lay, current)
        why = hint or self._unscoped_reason()
        if why:                                   # the hint ROW: an empty list must say why it is empty
            note = widgets.caption(why)
            note.setWordWrap(True)
            note.setProperty("state", "warn")
            widgets.repolish(note)
            lay.addWidget(note)
        lay.addLayout(self._button_bar())
        widgets.fit_dialog(self, ch=96, list_rows=8, lines=0)

    # ------------------------------------------------------------------ chrome
    def _scope_label(self, label):
        """WHICH RIG these clips belong to, and where that answer came from -- the picker's whole
        contract in one line (a list of gestures means nothing without the model it plays on)."""
        if self.model is None:
            text = f"No model resolved for this {label} — nothing to preview."
        else:
            src = {"archetype": "from its archetype", "preset": "from its preset",
                   "model": "from its model =", "player": "from [player] model =",
                   "player-default": "the stock player avatar (Zidane)"}.get(
                       getattr(self.block, "source", ""), "")
            text = f"Clips {self.model.name} can play" + (f"  ·  {src}" if src else "")
        lbl = QLabel(text)
        lbl.setProperty("role", "muted")
        lbl.setWordWrap(True)
        lbl.setAccessibleName("Which model these clips play on")
        return lbl

    def _unscoped_reason(self) -> str:
        if self.model is not None:
            return ""
        why = getattr(self.block, "reason", None) if self.block is not None else None
        return (f"{why}. " if why else "") + (
            "Give the block a model / preset first, or type a numeric clip id by hand.")

    def _button_bar(self):
        bar = QHBoxLayout()
        self.use_btn = QPushButton("Use this")
        self.use_btn.setObjectName("accent")
        self.use_btn.setAccessibleName("Use the selected animation")
        self.use_btn.clicked.connect(self._ok)
        cancel = QPushButton("Cancel")
        cancel.setAccessibleName("Cancel without changing the animation")
        cancel.clicked.connect(self.reject)
        bar.addWidget(self.use_btn)
        bar.addWidget(cancel)
        bar.addStretch(1)
        return bar

    # ------------------------------------------------------------------ single-clip modes
    def _build_single(self, lay, current):
        body = QHBoxLayout()
        self.listw = QListWidget()
        self.listw.setAccessibleName("Animation clips")
        self.listw.currentItemChanged.connect(self._on_row)
        self.listw.itemDoubleClicked.connect(lambda _i: self._ok())
        body.addWidget(self.listw, 1)
        self.img = QLabel()
        self.img.setFixedSize(_PREVIEW, _PREVIEW)
        self.img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img.setAccessibleName("Animation preview")
        self.img.setObjectName("animPickerImg")   # SELECTOR FORM: a bare property list out-ranks the app sheet
        self.img.setStyleSheet("QLabel#animPickerImg { background: transparent; "
                               f"border: 1px solid {self.pal['border']}; border-radius: 6px; }}")
        self.img.setText("pick a clip" if self.model is not None else "")
        body.addWidget(self.img)
        lay.addLayout(body)
        # the transport is its OWN full-width row, never inside the fixed preview column (round 13: a
        # control squeezed under its content minimum in a fixed column CLIPS rather than scrolls)
        lay.addWidget(self._build_transport(note="Pick a clip to render and play it."))
        lay.addWidget(self.anim_note)
        self._fill(current)

    def _fill(self, current):
        rows = _rows_for(self.model, self.mode)
        cur = str(current or "").strip()
        for r in rows:
            text = f"{r['label']}  ·  id {r['anim_id']}"
            if not r["own_form"]:
                text += "  ·  other form"
            it = QListWidgetItem(text)
            it.setData(Qt.ItemDataRole.UserRole, r)
            self.listw.addItem(it)
            if cur and cur in (r["label"], str(r["anim_id"])):
                self.listw.setCurrentItem(it)     # re-open on what the field already holds
        if not rows and self.model is not None:
            self.anim_note.setText("No clips catalogued for this model (a numbered battle-only token "
                                   "or a static prop).")

    def _on_row(self, item, _prev=None):
        if item is None or self.model is None:
            return
        self.arm_clip(self.model.name, item.data(Qt.ItemDataRole.UserRole)["anim_id"])

    def _row_value(self, row) -> str:
        """What this mode writes back: the action NAME for a gesture (the build resolves it through the
        actor's own rig, and a name survives a model swap), the numeric id for a movement slot (the .eb
        anim setters take u16 ids -- ``content.npc._anim16`` int()s the value)."""
        return str(row["label"]) if self.mode == "gesture" else str(row["anim_id"])

    # ------------------------------------------------------------------ slots mode
    def _build_slots(self, lay, current):
        try:
            vals = forms.parse_animset(current) or {}
        except ValueError:                        # a half-typed line: show the slots empty, don't refuse to open
            vals = {}
        auto = dict(getattr(self.block, "anims", None) or {})
        auto_src = {"archetype": "from the archetype", "catalog": "from the model",
                    "explicit": "from this block", "player": "from [player]"}.get(
                        getattr(self.block, "anims_source", ""), "")
        lay.addWidget(widgets.caption(
            "Blank = AUTO: the slot resolves from the block's model/preset at build time"
            + (f" ({auto_src})" if auto_src else "") + ". Browse previews the rig's clips."))
        # a GRID, not five QHBoxLayouts: per-row boxes measure each label on its own, so the five
        # editors started at five different x -- a ragged column the snap caught immediately.
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setColumnStretch(1, 1)
        self.slot_edits = {}
        for r, slot in enumerate(forms.ANIM_SLOTS):
            lbl = QLabel(f"{slot}:")
            le = QLineEdit(str(vals[slot]) if slot in vals else "")
            le.setAccessibleName(f"{slot} animation clip id")
            a = auto.get(slot)
            le.setPlaceholderText(f"Auto ({auto_src or 'from preset/model'}) → {a}" if a is not None
                                  else f"Auto ({auto_src or 'from preset/model'})")
            lbl.setBuddy(le)
            b = QPushButton("Browse…")
            b.setAccessibleName(f"Browse clips for the {slot} slot")
            b.clicked.connect(lambda _=False, s=slot: self._browse_slot(s))
            clr = QPushButton("Auto")
            clr.setAccessibleName(f"Clear the {slot} slot back to auto")
            clr.setToolTip("Clear this slot — the build resolves it from the block's model/preset.")
            clr.clicked.connect(lambda _=False, e=le: e.clear())
            for col, w in enumerate((lbl, le, b, clr)):
                grid.addWidget(w, r, col)
            self.slot_edits[slot] = le
        lay.addLayout(grid)

    def _browse_slot(self, slot):
        dlg = AnimPickerDialog(self, self.pal, mode="movement", block=self.block,
                               current=self.slot_edits[slot].text(), anim_frames=self.anims,
                               label=f"{slot} slot")
        dlg.exec()
        if dlg.result:
            self.slot_edits[slot].setText(dlg.result)

    # ------------------------------------------------------------------ answers
    def _ok(self):
        if self._single:
            it = self.listw.currentItem()
            if it is None:
                return
            self.result = self._row_value(it.data(Qt.ItemDataRole.UserRole))
        else:
            vals = {}
            for slot, le in self.slot_edits.items():
                t = le.text().strip()
                if t:
                    vals[slot] = t
            try:                                  # parse+format through the FORM's own owner, so what
                text = forms.format_animset(       # the dialog writes is what the field can read back
                    forms.parse_animset(", ".join(f"{s}={v}" for s, v in vals.items())) or {})
            except ValueError as e:
                return self._reject_slots(str(e))
            self.result = text
        self.accept()

    def _reject_slots(self, msg):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Not a clip id", msg)

    def _set_detail_image(self, png):
        """ClipPlayer's paint hook -- the preview box. A null pixmap HOLDS the previous frame."""
        pm = QPixmap(png)
        if not pm.isNull():
            self.img.setText("")
            self.img.setPixmap(pm.scaled(_PREVIEW, _PREVIEW, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation))

    def done(self, code):
        """Closing the dialog cancels its fill -- a background clip render must not outlive the surface
        that asked for it (and the slots mode's nested dialog shares this very service)."""
        if self._single:
            self.disarm()
        super().done(code)


def pick_animation(parent, palette, *, kinds, current, model_hint=None, anim_frames=None, label="animation"):
    """The shell's doorway: open the right mode for a form field's ``catalog=`` kinds and return the
    string to write back (or None). ``animset`` is the whole five-slot line; ``anim`` is one gesture."""
    mode = "slots" if "animset" in kinds else "gesture"
    hint = ""
    if not thumbs_mod.enabled():
        hint = ("Previews are off (no install, or FF9MAPKIT_NO_THUMBS) — the clip list still works; "
                "the ids/names paste straight into the field.")
    dlg = AnimPickerDialog(parent, palette, mode=mode, block=model_hint, current=current,
                           anim_frames=anim_frames, hint=hint, label=label)
    dlg.exec()
    return dlg.result
