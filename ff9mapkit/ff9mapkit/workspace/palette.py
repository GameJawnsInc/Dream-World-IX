"""The Ctrl-K command palette for the Workspace -- fuzzy search over content + named commands.

A modal overlay: type to filter a flat list of entries (each ``(label, kind, callback)``), Enter / click
runs the selected one. The shell feeds it the named commands (Open Campaign, Check, switch tab, …) AND
the project content (every journey / campaign / field / object node in the tree), so a clicker and a
keyboard user reach the same place. Matching is a subsequence test (``ocm`` -> "Open Campaign"), so
abbreviations work. PySide6-only view; the entry list + callbacks are the shell's to build.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout


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
        self.resize(580, 440)
        self._entries = list(entries)
        self._filtered = list(entries)
        lay = QVBoxLayout(self)
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

    def _fill(self):
        self.lst.clear()
        for label, kind, _cb in self._filtered:
            it = QListWidgetItem(f"{label}     ·  {kind}")
            self.lst.addItem(it)
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
