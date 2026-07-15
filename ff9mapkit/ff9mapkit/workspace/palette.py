"""The Ctrl-K command palette for the Workspace -- fuzzy search over content + named commands.

A modal overlay: type to filter a flat list of entries (each ``(label, kind, callback)``), Enter / click
runs the selected one. The shell feeds it the named commands (Open Campaign, Check, switch tab, …) AND
the project content (every journey / campaign / field / object node in the tree), so a clicker and a
keyboard user reach the same place. Matching is a subsequence test (``ocm`` -> "Open Campaign"), so
abbreviations work. PySide6-only view; the entry list + callbacks are the shell's to build.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QDialog, QFrame, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout

from ..editor.theme import derive
from . import anim
from .widgets import attach_shadow


# Category prefix per command kind (Phase 6: verb-first, category-prefixed rows). The stored label is left
# untouched (the fuzzy matcher + tests key on it); this only shapes the DISPLAY string.
_CATEGORY = {
    "command": "Action", "view": "Go to", "recent": "Recent", "learn": "Learn",
    "field": "Go to", "object": "Go to", "group": "Go to", "campaign": "Go to",
    "journey": "Go to", "jset": "Go to", "jcampaign": "Go to", "jbare": "Go to",
}
# Keybinding hints for the commands that have a global shortcut (shown as a trailing ⌨ tag).
_SHORTCUTS = {
    "New Field…": "Ctrl+N", "New Campaign…": "Ctrl+Shift+N",
    "Save All fields": "Ctrl+Shift+S", "Deploy now": "F9", "Deploy now (F9)": "F9",
}


def display_row(label: str, kind: str) -> str:
    """The palette DISPLAY string for one entry: a category prefix + the label (with a redundant leading verb
    the category already conveys stripped for the common Go-to / Learn rows) + a keybinding hint if any."""
    cat = _CATEGORY.get(kind, kind)
    shown = label
    if kind == "view" and shown.startswith("Go to "):
        shown = shown[len("Go to "):]                  # "Go to · Battle", not "Go to · Go to Battle"
    elif kind == "learn" and shown.startswith("What is ") and shown.endswith("?"):
        shown = shown[len("What is "):-1]              # "Learn · Walkmesh", not "Learn · What is Walkmesh?"
    if shown.endswith(" (F9)"):
        shown = shown[:-len(" (F9)")]                  # the F9 hint moves to the ⌨ column
    row = f"{cat}  ·  {shown}"
    sc = _SHORTCUTS.get(label)
    if sc:
        row += f"      ⌨ {sc}"
    return row


def fuzzy(needle: str, hay: str) -> bool:
    """True if every char of ``needle`` appears in ``hay`` IN ORDER (a subsequence match). Both lower."""
    i = 0
    for ch in hay:
        if i < len(needle) and ch == needle[i]:
            i += 1
    return i == len(needle)


def rank(needle: str, label: str, kind: str):
    """A sort key: exact substring first, then earliest match, then shorter labels. Lower = better."""
    lab = label.lower()
    sub = lab.find(needle)
    return (0 if sub == 0 else 1 if sub > 0 else 2, sub if sub >= 0 else 1_000, len(label))


class CommandPalette(QDialog):
    """Type-to-filter overlay over ``entries`` (a list of ``(label, kind, callback)``)."""

    def __init__(self, parent, entries, palette):
        super().__init__(parent)
        self.setWindowTitle("Search content & commands")
        self.setModal(True)
        # A Spotlight-style FLOATING overlay: frameless + translucent so the inner rounded card can carry a
        # real drop shadow (a framed dialog would just get the OS chrome). The outer margin gives the blur room.
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(580, 440)
        self._entries = list(entries)
        self._filtered = list(entries)
        d = derive(palette)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 26)       # room for the shadow to spill (heavier at the bottom)
        card = QFrame()
        card.setObjectName("paletteCard")
        # 8px = the radius language's $radius_lg (style.py). Hardcoded rather than threaded because this
        # sheet is set on the WIDGET, which out-ranks the app sheet regardless of specificity -- so the
        # token cannot reach it. It must be kept in step by hand; the app's only floating card (the sole
        # attach_shadow caller) must not be the last 10px corner in the build.
        card.setStyleSheet(f"QFrame#paletteCard {{ background:{d['surface_3']}; border:1px solid {d['border']}; "
                           f"border-radius:8px; }}")
        outer.addWidget(card)
        attach_shadow(card)                            # the real QGraphicsDropShadowEffect (on the rounded card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 12, 12, 12)
        self.q = QLineEdit()
        self.q.setPlaceholderText("Search content & commands…  (a field name, or a command)")
        self.q.textChanged.connect(self._refilter)
        self.q.returnPressed.connect(self._run_current)
        self.q.installEventFilter(self)                # forward Up/Down to the list while typing
        lay.addWidget(self.q)
        self.lst = QListWidget()
        self.lst.itemActivated.connect(lambda _i: self._run_current())
        lay.addWidget(self.lst, 1)
        self._muted = palette["muted"]
        self._fill()
        self.q.setFocus()

    def showEvent(self, event):                        # noqa: N802 (Qt override)
        super().showEvent(event)
        anim.pop_in(self)                              # a subtle fade + rise into place (no-op if motion is off)

    def _fill(self):
        self.lst.clear()
        for label, kind, _cb in self._filtered:
            self.lst.addItem(QListWidgetItem(display_row(label, kind)))
        if self._filtered:
            self.lst.setCurrentRow(0)

    def _refilter(self, text):
        t = text.strip().lower()
        if not t:
            self._filtered = list(self._entries)
        else:
            self._filtered = sorted(
                (e for e in self._entries if fuzzy(t, e[0].lower()) or fuzzy(t, (e[0] + " " + e[1]).lower())),
                key=lambda e: rank(t, e[0], e[1]))
        self._fill()

    def _run_current(self):
        r = self.lst.currentRow()
        if 0 <= r < len(self._filtered):
            cb = self._filtered[r][2]
            self.accept()
            cb()

    def eventFilter(self, obj, ev):                    # noqa: N802 (Qt override)
        if obj is self.q and ev.type() == QEvent.Type.KeyPress and ev.key() in (Qt.Key_Down, Qt.Key_Up):
            self.lst.keyPressEvent(ev)                  # arrow keys move the list while focus stays in the box
            return True
        return super().eventFilter(obj, ev)
