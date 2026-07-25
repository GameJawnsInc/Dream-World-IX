"""Find-in-Output, and the session's JOB INDEX -- the console read as a DOCUMENT rather than a drain.

WHY THIS EXISTS. An earlier round made ``run_job`` stop clearing the console on purpose: *"the header is a
SEPARATOR, and a separator with nothing above it separates nothing"*. That change turned Output into a
MULTI-JOB DOCUMENT -- a whole session of builds, deploys, lints and imports, up to 5000 blocks -- and left
it with a drain's three controls: Wrap, Copy-everything, Clear. There was no search **anywhere in the app**
(``Ctrl+F`` was unbound app-wide), so the only way to find a line in the densest surface the app ships was
to scroll and read it. And the document's own structure -- the ``[HH:MM:SS] subject`` head lines, which the
GUI writes ITSELF and therefore knows with certainty -- was spent by nothing at all.

So: one mechanism (the head-line index), three affordances (find / jump to a job / copy just that job).

THE ARITHMETIC IS PURE AND THE QT PART IS THIN, deliberately -- :func:`find_all` and :func:`job_span` take
a ``str`` and return offsets, so the matching, the wrap-around and the span logic are all testable without
a QApplication. That is only sound because of one fact worth stating: **for a PLAIN-TEXT QTextDocument, a
document position is the offset into ``toPlainText()``** (each block separator counts as exactly one
character). The console is plain text by construction -- ``_log`` uses QTextCursor + setCharFormat and
NEVER appendHtml, precisely so a line of stdout containing ``<`` is not eaten as markup -- so the mapping
holds. It is not assumed: ``test_a_pure_offset_is_a_document_position`` drives the real
``QTextDocument.find`` and asserts the two agree.

THE TRIM IS THE TRAP, and it is why a job is remembered by its TEXT and not by a block number. The console
caps at 5000 blocks (``setMaximumBlockCount``), which drops blocks off the FRONT -- so every stored block
number silently shifts on a long session, and a "jump to job" built on one would land somewhere else the
moment the log filled. A head line carries its own timestamp, so it is a locator: search for it, and if it
is gone, say so (the row disables) rather than guess.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QTextEdit, QToolButton, QWidget,
)

from ..editor.theme import derive
from . import widgets

# --------------------------------------------------------------------------------- the pure half


def find_all(text: str, needle: str, *, case: bool = False) -> list[int]:
    """Every start offset of ``needle`` in ``text``, left to right, non-overlapping. ``[]`` for an empty
    needle (an empty search matches nothing -- it must not match everything)."""
    if not needle:
        return []
    hay = text if case else text.lower()
    pin = needle if case else needle.lower()
    out, i = [], hay.find(pin)
    while i != -1:
        out.append(i)
        i = hay.find(pin, i + len(pin))
    return out


def match_at_or_after(starts: list[int], pos: int) -> int:
    """Index of the first match starting at or after ``pos``, wrapping to 0. ``-1`` if there are none.

    This is the "find from where I am" rule, and the wrap is what makes Enter-Enter-Enter cycle instead of
    dead-ending at the last match."""
    for i, s in enumerate(starts):
        if s >= pos:
            return i
    return 0 if starts else -1


def job_spans(text: str, heads: list[str]) -> list[tuple[int, int] | None]:
    """``(start, end)`` for every job head, in one pass. ``None`` where a head has been trimmed off the
    front of the document (see the module docstring -- a real state, not an error).

    IN ORDER, CUMULATIVELY, and that is not tidiness -- it is the fix for a collision the naive version has.
    A head is ``[HH:MM:SS] subject``, so two jobs with the same subject in the same SECOND have BYTE-IDENTICAL
    heads (a lint of a small file right after another; two Checks). ``text.find(head)`` then returns the
    first occurrence for BOTH, and two different menu rows silently jump to the same place. Searching each
    head from the end of the previous one resolves duplicates to distinct occurrences, in order.

    A job ENDS where the next SURVIVING head begins, so the span is derived rather than stored: the last job
    of the session -- or one still streaming -- runs to the end of the text.
    """
    at, pos = [], 0
    for h in heads:
        j = text.find(h, pos)
        at.append(j)
        if j != -1:
            pos = j + len(h)
    out: list[tuple[int, int] | None] = []
    for i, start in enumerate(at):
        if start == -1:
            out.append(None)
            continue
        nxt = next((j for j in at[i + 1:] if j != -1), None)
        # `nxt - 1` drops the newline that belongs to the NEXT head. The last job has no such newline to
        # drop, so it ends at len(text) -- subtracting there chopped a real character off the final line
        # (a traceback's closing quote, measured).
        out.append((start, len(text) if nxt is None else max(start, nxt - 1)))
    return out


def job_span(text: str, heads: list[str], i: int) -> tuple[int, int] | None:
    """One job's span. See :func:`job_spans`, which this delegates to (callers needing every row should use
    that directly -- per-row calls here would rescan the whole document once per row)."""
    if not (0 <= i < len(heads)):
        return None
    return job_spans(text, heads)[i]


# --------------------------------------------------------------------------------- the Qt half


class _Gauge(QLabel):
    """The match counter, which must not make the buttons beside it dance.

    ``setMinimumWidth``, never ``setFixedWidth`` -- reserving room for the common case kills the jitter,
    while a fixed width would CLIP the uncommon one, and clipping is the defect this study has already paid
    for twice (the round-9 status keys, ``kv``'s frozen column). Re-measured on FontChange because a width
    computed from a font is wrong the moment the text dial moves: same law as ``widgets._KvKey``/GAUGE.
    """

    _WIDEST = "8888 / 8888"

    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setProperty("role", "muted")
        self._fit()

    def _fit(self):
        self.setMinimumWidth(round(self.fontMetrics().horizontalAdvance(self._WIDEST)))

    def changeEvent(self, ev):                    # noqa: N802 (Qt override)
        super().changeEvent(ev)
        if ev.type() == QEvent.Type.FontChange:
            self._fit()


class _FindField(QLineEdit):
    """The needle box -- which has to own three keys ITSELF, because none of them arrive any other way.

    * **Shift+Enter.** ``returnPressed`` carries no modifier, so the previous-match binding cannot live
      there. The first build put it on a QShortcut hosted by a hidden zero-size QPushButton; measured, it
      NEVER FIRED (Qt disables shortcuts owned by an invisible widget) while the ``▲`` button's own tooltip
      advertised the key -- a documented affordance that did nothing.
    * **Enter.** Handled here too, so next/previous are one branch and cannot drift apart.
    * **Escape.** A QLineEdit with ``setClearButtonEnabled`` consumes Escape to clear itself, so the event
      never reaches the bar's ``keyPressEvent`` -- Esc would empty the field instead of closing the bar.

    Anything else falls through to QLineEdit, so ordinary typing, selection and the clear button are intact.
    """

    def __init__(self, bar):
        super().__init__(bar)
        self._bar = bar

    def keyPressEvent(self, ev):                   # noqa: N802 (Qt override)
        k, mods = ev.key(), ev.modifiers()
        if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if mods & Qt.KeyboardModifier.ShiftModifier:
                self._bar.prev_match()
            else:
                self._bar.next_match()
            ev.accept()
            return
        if k == Qt.Key.Key_Escape:
            self._bar.close_bar()
            ev.accept()
            return
        super().keyPressEvent(ev)


class FindBar(QWidget):
    """An incremental find bar over a read-only ``QPlainTextEdit``: match count, step, wrap, highlight-all.

    TWO GROUNDS, TWO INKS, BOTH MEASURED. Every match gets the quiet ``find_bg`` fill; the CURRENT one gets
    the full ``accent``. Each sets its foreground EXPLICITLY, because a highlight is a new ground under the
    log's text and the ``log_fg``/``log_bg`` fence does not reach it -- the NINTH-GROUND LAW. Letting the
    log's own ink ride an accent fill measures 1.16-3.43:1, sub-AA in all eight palettes; the quiet tier is
    sub-AA in solarized-light. See ``theme._find_token`` and ``evidence/probe_find_ground.py``.

    THE CURRENT MATCH IS NOT A SELECTION, and that is deliberate rather than incidental: Qt paints the real
    selection OVER extra selections using the app palette's Highlight colour, so selecting the match would
    hand its ground to a colour this bar cannot reach or fence. The cursor moves to the match WITHOUT an
    anchor; both tiers are painted by ``setExtraSelections``, which owns the whole appearance. It also
    leaves the user's own selection alone -- which is what makes the Copy button's selection-first rule and
    a live search coexist.
    """

    # The shell makes room for this bar out of the DOCUMENTS pane when it opens and gives that room back
    # when it closes -- and the bar closes ITSELF (Esc, the X), so the shell has to hear about it. A signal
    # rather than a callback the constructor takes: the bar must work with no shell at all, which is what
    # makes it unit-testable against a bare QPlainTextEdit.
    closed = Signal()

    def __init__(self, target: QPlainTextEdit, pal, parent=None):
        super().__init__(parent)
        self._target = target
        # DERIVE, because `find_bg`/`find_fg` are derived keys and the shell's ``self.pal`` is the RAW palette
        # (`main()` does `Workspace(pick_palette(...))`). Reading them off the raw dict is a KeyError, not a
        # silent fallback -- the same trap `Workspace._derived` exists to document, where a defensive `.get`
        # once meant a token was never drawn in any palette. `derive` is idempotent, so this is safe on either.
        self._pal = derive(dict(pal))
        self._starts: list[int] = []
        self._cur = -1
        self._needle = ""

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(6)

        self.field = _FindField(self)          # owns Enter / Shift+Enter / Esc -- see _FindField
        self.field.setPlaceholderText("Find in output")
        self.field.setClearButtonEnabled(True)
        self.field.setAccessibleName("Find in output")
        self.field.textChanged.connect(self._on_typed)
        lay.addWidget(self.field, 1)

        self.count = _Gauge()
        lay.addWidget(self.count)

        self.btn_prev = QPushButton("▲")
        self.btn_prev.setObjectName("consoleHeadBtn")
        self.btn_prev.setToolTip("Previous match (Shift+Enter)")
        self.btn_prev.clicked.connect(self.prev_match)
        self.btn_next = QPushButton("▼")
        self.btn_next.setObjectName("consoleHeadBtn")
        self.btn_next.setToolTip("Next match (Enter)")
        self.btn_next.clicked.connect(self.next_match)
        self.btn_case = QPushButton("Aa")
        self.btn_case.setObjectName("consoleHeadBtn")
        self.btn_case.setCheckable(True)
        self.btn_case.setToolTip("Match case (a build log is full of paths where case matters)")
        self.btn_case.clicked.connect(lambda _on: self.refresh())
        close = QToolButton()
        close.setText("✕")
        close.setAutoRaise(True)
        close.setToolTip("Close the find bar (Esc)")
        close.setAccessibleName("Close find")
        close.clicked.connect(self.close_bar)
        for w in (self.btn_prev, self.btn_next, self.btn_case, close):
            lay.addWidget(w)

        # Output keeps streaming while the bar is open, and every arriving chunk moves every offset after it
        # (and the 5000-block cap moves the ones BEFORE it too). Re-running per chunk would rescan the whole
        # document on every read of a build's stdout, so the refresh is coalesced through one timer.
        #
        # AND THAT IS THE WHOLE BUDGET -- there is no cap on painted matches, because the measurement said
        # one would be speculative machinery. At FULL log depth (5000 blocks / 179k chars): the pure scan is
        # ~1ms, and refresh + repaint is 27ms for 5,000 matches ("wrote") and 58ms for 10,000 (the single
        # letter "o" -- pathological, nobody searches it). Against this 180ms window even the pathological
        # case spends a third of one interval. A cap would also have to either lie in the counter or announce
        # itself, and neither is worth buying at 58ms.
        self._restat = QTimer(self)
        self._restat.setSingleShot(True)
        self._restat.setInterval(180)
        self._restat.timeout.connect(self.refresh)
        target.document().contentsChanged.connect(self._doc_changed)

        self.setVisible(False)

    # ---- state ----
    def _doc_changed(self):
        if self.isVisible() and self._needle:
            self._restat.start()

    def open_for(self, seed: str = ""):
        """Show the bar and take focus. ``seed`` pre-fills the field (used by 'search for this line').

        The needle is re-read from the FIELD rather than assumed, because ``close_bar`` drops ``_needle``
        while the field keeps its text (deliberately -- reopening with your last search selected is what
        every find bar does). Without this re-sync, a reopen with no seed showed a needle in the box, a blank
        counter and no highlights: the widget saying one thing and the state another. A seeded reopen hid the
        bug, since setText fires textChanged and _on_typed sets the needle for free.
        """
        self.setVisible(True)
        if seed:
            self.field.setText(seed)
        self._needle = self.field.text()
        self.field.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.field.selectAll()
        self.refresh()

    def close_bar(self):
        """Hide the bar, drop every highlight, hand focus back to the log.

        THE GOES-AWAY LAW: an affordance for a thing you are no longer doing must leave, and leave nothing
        behind -- a stale highlight after the bar is gone is a mark with no explanation on screen."""
        self.setVisible(False)
        self._starts, self._cur, self._needle = [], -1, ""
        self._restat.stop()
        self._target.setExtraSelections([])
        self._target.setFocus(Qt.FocusReason.OtherFocusReason)
        self.closed.emit()

    def keyPressEvent(self, ev):                   # noqa: N802 (Qt override)
        if ev.key() == Qt.Key.Key_Escape:
            self.close_bar()
            return
        super().keyPressEvent(ev)

    # ---- search ----
    def _on_typed(self, text):
        self._needle = text
        self._cur = -1                             # a fresh needle searches from the cursor, not from the
        self.refresh()                             # old match's index (which meant nothing for a new word)

    def refresh(self):
        """Re-scan, re-count, re-paint. Idempotent -- safe to call from the typing path, the case toggle
        and the coalesced document-change timer alike."""
        text = self._target.toPlainText()
        self._starts = find_all(text, self._needle, case=self.btn_case.isChecked())
        if self._starts:
            if self._cur < 0:
                self._cur = match_at_or_after(self._starts, self._target.textCursor().position())
            else:
                self._cur = min(self._cur, len(self._starts) - 1)
        else:
            self._cur = -1
        self._sync()
        if self._cur >= 0:
            self._reveal()

    def next_match(self):
        self._step(+1)

    def prev_match(self):
        self._step(-1)

    def _step(self, d):
        if not self._starts:
            return
        self._cur = (self._cur + d) % len(self._starts)     # wraps both ways
        self._sync()
        self._reveal()

    def _sync(self):
        """The counter + the enabled states + the highlights, from ``_starts``/``_cur``."""
        n = len(self._starts)
        if not self._needle:
            self.count.setText("")
            widgets.set_state(self.count, "")
        elif n:
            self.count.setText(f"{self._cur + 1} / {n}")
            widgets.set_state(self.count, "")
        else:
            self.count.setText("no matches")
            # `error_text`, via the app's own QLabel[state="error"] rule -- the one status ink already
            # fenced at 4.5:1 on every ground. A hand-picked red here would be the chip's old bug again.
            widgets.set_state(self.count, "error")
        for b in (self.btn_prev, self.btn_next):
            b.setEnabled(n > 1)
        self._paint()

    def _paint(self):
        """Both highlight tiers, in one ``setExtraSelections`` pass."""
        pal = self._pal
        quiet = QTextCharFormat()
        quiet.setBackground(QColor(pal["find_bg"]))
        quiet.setForeground(QColor(pal["find_fg"]))
        loud = QTextCharFormat()
        loud.setBackground(QColor(pal["accent"]))
        loud.setForeground(QColor(pal["accent_fg"]))
        sels = []
        for i, s in enumerate(self._starts):
            # QTextEdit.ExtraSelection, not QPlainTextEdit's -- Qt declares the struct on QTextEdit and
            # QPlainTextEdit.setExtraSelections consumes it. PySide6 has no QPlainTextEdit.ExtraSelection at
            # all, so the intuitive spelling is an AttributeError on the first keystroke of the first search.
            sel = QTextEdit.ExtraSelection()
            cur = QTextCursor(self._target.document())
            cur.setPosition(s)
            cur.setPosition(s + len(self._needle), QTextCursor.MoveMode.KeepAnchor)
            sel.cursor = cur
            sel.format = loud if i == self._cur else quiet
            sels.append(sel)
        self._target.setExtraSelections(sels)

    def _reveal(self):
        """Scroll the current match into view WITHOUT selecting it (see the class docstring)."""
        cur = self._target.textCursor()
        cur.setPosition(self._starts[self._cur])
        self._target.setTextCursor(cur)
        self._target.ensureCursorVisible()

    def retheme(self, pal):
        """A live theme switch: both tiers are QPainter-side formats, so the stylesheet cannot reach them."""
        self._pal = derive(dict(pal))
        if self.isVisible():
            self._paint()
