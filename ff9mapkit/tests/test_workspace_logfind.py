"""Find-in-Output + the session job index (workspace/logfind.py + the shell's console wiring).

The console accumulates across jobs on purpose, which made it a DOCUMENT with a drain's controls. These
fence the three affordances that spend its structure -- find, jump-to-job, copy-just-that-job -- plus the
four traps the build actually hit:

  * ``QTextEdit.ExtraSelection``, not ``QPlainTextEdit``'s (PySide6 has no such attribute -- an
    AttributeError on the first keystroke of the first search);
  * the shell's ``self.pal`` is the RAW palette, so `find_bg`/`find_fg` must be DERIVED or KeyError;
  * the last job's span must not chop its final character (a traceback's closing quote, measured);
  * two jobs with the same subject in the same SECOND have byte-identical head lines.

OFFSCREEN-SAFE. Every width claim here is a RELATIONSHIP (grew / did not clip), never a pixel count:
offscreen stubs the font DB and has manufactured whole defects in this study from absolute widths.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtGui import QTextCursor                                          # noqa: E402
from PySide6.QtWidgets import QApplication, QPlainTextEdit                      # noqa: E402

from ff9mapkit.editor.theme import pick_palette                                 # noqa: E402
from ff9mapkit.workspace import anim, logfind                                   # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app):
    from ff9mapkit.workspace.shell import Workspace, _apply_app_theme
    anim.set_enabled(False)
    _apply_app_theme(app, pick_palette("dark"))
    w = Workspace(pick_palette("dark"))
    w.show()
    app.processEvents()
    yield w
    w.close()


def _seed(win, *, jobs=None):
    """A pinned multi-job log, written through the shell's own _log in run_job's registers."""
    jobs = jobs or [("09:41:02", "Build field 4003", 0, ["wrote scene.bgx", "wrote field.eb"]),
                    ("09:41:20", "Deploy field 4003", 0, ["wrote revert_deploy_4003.py", "deploy ok"]),
                    ("09:42:07", "Import field 354", 1, ["Traceback (most recent call last):",
                                                         "KeyError: 'walkmesh'"])]
    idx = []
    for stamp, subject, code, lines in jobs:
        head = f"[{stamp}] {subject}"
        idx.append({"head": head, "time": stamp, "subject": subject, "code": code, "stopped": False})
        win._log(head, "head")
        for ln in lines:
            win._log(ln, "body")
    win._job_index = idx
    return idx


# ------------------------------------------------------------------ the pure half (no Qt needed)
def test_find_all_is_case_insensitive_by_default_and_never_overlaps():
    assert logfind.find_all("Wrote a, wrote b", "wrote") == [0, 9]
    assert logfind.find_all("Wrote a, wrote b", "wrote", case=True) == [9]
    assert logfind.find_all("aaaa", "aa") == [0, 2], "non-overlapping: 'aaaa' holds TWO 'aa', not three"


def test_an_empty_needle_matches_nothing_not_everything():
    """The incremental path calls this on every keystroke, including the one that empties the field. A
    truthy-empty match would highlight the entire document and report a count of len(text)+1."""
    assert logfind.find_all("anything", "") == []


def test_the_step_wraps_both_ways():
    starts = [0, 5, 9]
    assert logfind.match_at_or_after(starts, 6) == 2
    assert logfind.match_at_or_after(starts, 999) == 0, "past the last match -> wrap to the first"
    assert logfind.match_at_or_after([], 0) == -1


def test_the_last_job_keeps_its_final_character():
    """`end - 1` drops the newline belonging to the NEXT head -- and the last job has no next head, so
    subtracting there ate a real character. Measured on a traceback, whose last line ends in a quote."""
    text = "[10:00:00] A\nline a\n[10:00:01] B\nKeyError: 'walkmesh'"
    heads = ["[10:00:00] A", "[10:00:01] B"]
    a, b = logfind.job_spans(text, heads)
    assert text[b[0]:b[1]].endswith("KeyError: 'walkmesh'"), "the final character is part of the job"
    assert not text[a[0]:a[1]].endswith("\n"), "a bounded job must not carry the next head's newline"
    assert text[a[0]:a[1]] == "[10:00:00] A\nline a"


def test_two_jobs_with_identical_heads_resolve_to_different_occurrences():
    """A head is `[HH:MM:SS] subject`, so two Checks in the same second are byte-identical. A naive
    text.find(head) returns the FIRST for both, and two menu rows silently jump to one place."""
    text = "[10:00:00] Check\nfirst\n[10:00:00] Check\nsecond"
    a, b = logfind.job_spans(text, ["[10:00:00] Check", "[10:00:00] Check"])
    assert a != b
    assert "first" in text[a[0]:a[1]] and "second" in text[b[0]:b[1]]


def test_a_trimmed_job_reports_none_rather_than_guessing():
    """The 5000-block cap drops blocks off the FRONT. A job whose head is gone has no span -- which is why
    the index stores head TEXT and not a block number, and why the menu row disables."""
    spans = logfind.job_spans("[10:00:01] B\nonly b", ["[10:00:00] A", "[10:00:01] B"])
    assert spans[0] is None and spans[1] is not None
    assert logfind.job_span("whatever", ["x"], 5) is None, "an out-of-range index is None, not an IndexError"


# ------------------------------------------------------------------ the mapping the pure half rests on
def test_a_pure_offset_is_a_document_position(app):
    """THE ASSUMPTION MADE EXPLICIT. find_all returns offsets into toPlainText(); the bar feeds them to
    QTextCursor.setPosition. That is only sound because a plain-text document's positions are 1:1 with its
    plain text (one character per block separator). Driven against the real QTextDocument.find rather than
    reasoned about -- if Qt ever disagrees, this is the fence that says so."""
    ed = QPlainTextEdit()
    ed.setPlainText("wrote a\nnot here\nwrote b\nwrote c")
    doc = ed.document()
    qt_positions, cur = [], QTextCursor(doc)
    while True:
        cur = doc.find("wrote", cur)
        if cur.isNull():
            break
        qt_positions.append(cur.selectionStart())
    assert qt_positions == logfind.find_all(ed.toPlainText(), "wrote"), \
        "a pure offset and a QTextDocument position have diverged -- the whole pure half rests on this"


# ------------------------------------------------------------------ the bar
def test_the_bar_counts_steps_wraps_and_says_when_it_misses(win, app):
    _seed(win)
    win._open_find("wrote")
    app.processEvents()
    bar = win._find_bar
    assert bar.isVisible()
    assert bar.count.text() == "1 / 3"
    bar.next_match(); assert bar.count.text() == "2 / 3"
    bar.next_match(); assert bar.count.text() == "3 / 3"
    bar.next_match(); assert bar.count.text() == "1 / 3", "Enter at the last match wraps to the first"
    bar.prev_match(); assert bar.count.text() == "3 / 3", "and backwards over the seam too"

    bar.field.setText("no-such-line")
    app.processEvents()
    assert bar.count.text() == "no matches"
    assert win.output.extraSelections() == [], "a miss leaves no marks behind"
    assert not bar.btn_next.isEnabled(), "stepping is meaningless with nothing to step through"


def test_the_miss_actually_renders_in_error_text(win, app):
    """A `state` PROPERTY is not a rendered colour, and asserting the property is a fence at the wrong bar --
    this study's most-repeated defect. The counter carries `role="muted"` too, and `QLabel[role="muted"]` sits
    at style.py:614 while `QLabel[state="error"]` sits at 632; which wins is a QSS cascade question, and the
    file's own `QLabel[role="muted"][state="warn"]` two-attribute rule exists because that cascade did NOT go
    the obvious way for warn. So this MEASURES the ink instead: grab the label and read the pixels.

    Measured when written (mist): hit -> #9fadc4 == `muted`, miss -> #ff6b6b == `error_text`. The error rule
    does win, and the fence now says so from pixels rather than from a property nobody rendered.
    """
    from collections import Counter
    from ff9mapkit.editor.theme import derive
    pal = derive(dict(pick_palette("dark")))
    _seed(win)

    def ink(label):
        img = label.grab().toImage()
        seen = Counter(img.pixelColor(x, y).name()
                       for y in range(img.height()) for x in range(img.width()))
        # the glyph ink is the most common colour that is not the (transparent/black) ground
        return [c for c, _n in seen.most_common(6) if c != "#000000"]

    win._open_find("wrote")
    app.processEvents()
    assert pal["muted"] in ink(win._find_bar.count), "a hit's counter is the quiet muted tier"

    win._find_bar.field.setText("no-such-line")
    app.processEvents()
    hues = ink(win._find_bar.count)
    assert pal["error_text"] in hues, (
        f"the miss must RENDER in the app's fenced error_text ({pal['error_text']}); got {hues[:3]}. "
        f"A hand-picked red here would be the breadcrumb chip's 1.12:1 bug again.")
    assert pal["muted"] not in hues, "role=muted must lose to state=error, or the miss reads as a hit"


def test_the_three_keys_the_field_owns(win, app):
    """Enter / Shift+Enter / Esc, driven as REAL key events on the focused field -- because each was broken
    or unreachable in the first build and none of them is reachable by calling a slot:

    * Shift+Enter lived on a QShortcut hosted by a HIDDEN QPushButton and never fired (Qt disables shortcuts
      owned by an invisible widget). Measured: the count went 1/3 -> 2/3, i.e. `returnPressed` won and the
      previous-match key advertised in the ▲ tooltip did nothing.
    * Esc would have been eaten by `setClearButtonEnabled`, emptying the field instead of closing the bar.
    """
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    _seed(win)
    win._open_find("wrote")
    app.processEvents()
    bar = win._find_bar

    def key(k, mods=Qt.KeyboardModifier.NoModifier):
        bar.field.setFocus()
        app.processEvents()
        app.sendEvent(bar.field, QKeyEvent(QEvent.Type.KeyPress, k, mods))
        app.processEvents()

    assert bar.count.text() == "1 / 3"
    key(Qt.Key.Key_Return)
    assert bar.count.text() == "2 / 3", "Enter steps forward"
    key(Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
    assert bar.count.text() == "1 / 3", "Shift+Enter steps BACK (the key the hidden shortcut never delivered)"
    key(Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
    assert bar.count.text() == "3 / 3", "...and wraps backwards over the seam"

    key(Qt.Key.Key_Escape)
    assert not bar.isVisible(), "Esc closes the bar rather than clearing the field"
    assert bar.field.text() == "wrote", "the needle survives a close, so a reopen offers your last search"


def test_a_reopen_with_no_seed_still_finds_its_own_needle(win, app):
    """close_bar drops the needle while the field keeps its text. Without a re-sync on open, a bare reopen
    showed a needle in the box, an EMPTY counter and no highlights -- the widget saying one thing and the
    state another. A seeded reopen hides it (setText fires textChanged), so this one opens bare."""
    _seed(win)
    win._open_find("wrote")
    app.processEvents()
    win._find_bar.close_bar()
    app.processEvents()
    win._open_find()                                  # no seed -- the Ctrl+F path
    app.processEvents()
    assert win._find_bar.field.text() == "wrote"
    assert win._find_bar.count.text() == "1 / 3", "the counter must agree with the box it sits beside"
    assert len(win.output.extraSelections()) == 3


def test_both_highlight_tiers_are_painted_and_only_one_is_current(win, app):
    """Highlight-ALL plus a distinguished current match: N marks, exactly one of them the loud accent."""
    _seed(win)
    win._open_find("wrote")
    app.processEvents()
    sels = win.output.extraSelections()
    assert len(sels) == 3, "every match is marked, not just the current one"
    pal = win._find_bar._pal
    loud = [s for s in sels if s.format.background().color().name() == pal["accent"]]
    quiet = [s for s in sels if s.format.background().color().name() == pal["find_bg"]]
    assert len(loud) == 1 and len(quiet) == 2
    assert loud[0].format.foreground().color().name() == pal["accent_fg"], \
        "the loud tier sets its ink EXPLICITLY -- log_fg on the accent is sub-AA in all 8 palettes"
    assert quiet[0].format.foreground().color().name() == pal["find_fg"]


def test_the_current_match_is_not_a_selection(win, app):
    """DELIBERATE: Qt paints the real selection OVER extra selections in the app palette's Highlight colour,
    so selecting the match would hand its ground to a colour the bar cannot fence. It also keeps the user's
    own selection (which Copy reads) out of the search's way."""
    _seed(win)
    win._open_find("wrote")
    app.processEvents()
    assert not win.output.textCursor().hasSelection()


def test_the_bar_derives_the_palette_it_is_handed(win, app):
    """`find_bg`/`find_fg` are DERIVED keys and the shell's self.pal is the RAW palette (main() does
    Workspace(pick_palette(...))). Reading them off the raw dict is a KeyError on the first paint -- the trap
    Workspace._derived exists to document. Re-checked through a live retheme in every palette."""
    from ff9mapkit.editor.theme import THEMES
    _seed(win)
    win._open_find("wrote")
    for mode in THEMES:
        win.retheme(pick_palette(mode))
        app.processEvents()
        assert win._find_bar._pal["find_bg"] and win._find_bar._pal["find_fg"]
        marks = win.output.extraSelections()
        assert len(marks) == 3, f"{mode}: a theme switch must repaint the marks, not drop them"
        assert any(s.format.background().color().name() == win._find_bar._pal["accent"] for s in marks), \
            f"{mode}: the loud tier must follow the new palette (a QTextCharFormat is beyond the sheet's reach)"


def test_escape_closes_the_bar_and_leaves_nothing_behind(win, app):
    """THE GOES-AWAY LAW: a highlight outliving the bar that explains it is a mark with no legend."""
    _seed(win)
    win._open_find("wrote")
    app.processEvents()
    assert win.output.extraSelections()
    seen = []
    win._find_bar.closed.connect(lambda: seen.append(True))
    win._find_bar.close_bar()
    app.processEvents()
    assert not win._find_bar.isVisible()
    assert win.output.extraSelections() == []
    assert seen, "the bar signals its own close -- the shell gives the borrowed height back on it"


def test_the_counter_hears_the_text_dial_and_never_clips(win, app):
    """The GAUGE pattern: a width computed from a font is wrong the moment the font moves. And it is a
    MINIMUM, not a fixed width -- reserving room kills the jitter, a fixed width would CLIP a 4-digit count,
    and clipping is the defect this study has already paid for twice.

    THE LEVER IS THE DIAL, NOT setFont. The QSS base rule puts a font on every QWidget and re-resolves it
    over any programmatic setFont, so a setFont probe cannot move a styled widget's font and therefore cannot
    falsify a frozen width -- measured here first, 154 == 154, exactly as round 9's kv fence measured 98 == 98.
    A lever that cannot move the thing under test proves nothing. CALIBRE can move it.
    """
    gauge = win._find_bar.count

    def expected():
        return round(gauge.fontMetrics().horizontalAdvance(type(gauge)._WIDEST))

    assert gauge.minimumWidth() == expected(), "the counter is not a function of its OWN current font"
    before = gauge.minimumWidth()
    try:
        win._apply_text_scale(150)
        app.processEvents()
        assert gauge.minimumWidth() == expected(), "after the dial moves the counter must re-measure"
        assert gauge.minimumWidth() > before, \
            "the dial reached 150% and the counter never widened -- FontChange is not wired"
    finally:
        win._apply_text_scale(100)
        app.processEvents()
    gauge.setText("1234 / 5678")
    assert gauge.sizeHint().width() >= gauge.minimumWidth(), "a long count grows the label, never clips it"


# ------------------------------------------------------------------ the console makes room
def test_the_find_bar_does_not_pay_for_itself_out_of_the_log(win, app):
    """The console opens ~152px tall, so a ~46px bar inside it left the log ONE readable line. The height
    comes from the DOCUMENTS pane instead."""
    _seed(win)
    win._raise_console()
    app.processEvents()
    before = win._vsplit.sizes()
    win._open_find("wrote")
    app.processEvents()
    after = win._vsplit.sizes()
    assert after[1] > before[1], "the console pane grew to seat the bar"
    assert after[0] < before[0], "...and the documents pane paid for it"
    assert sum(after) == sum(before), "no height invented or lost"


def test_a_divider_the_user_dragged_is_not_undone(win, app):
    """Round 7's law, cutting the other way: we undo OUR OWN edit and nothing else. If the split no longer
    reads as the one we set, the user moved it while searching and their value wins."""
    _seed(win)
    win._raise_console()
    win._open_find("wrote")
    app.processEvents()
    ours = win._vsplit.sizes()
    dragged = [ours[0] - 60, ours[1] + 60]
    win._vsplit.setSizes(dragged)
    app.processEvents()
    moved = win._vsplit.sizes()
    win._find_bar.close_bar()
    app.processEvents()
    assert win._vsplit.sizes() == moved, "a split the user chose must survive closing the bar"


# ------------------------------------------------------------------ the job index
def test_the_jobs_menu_carries_a_verdict_shape_per_job(win, app):
    """Verdict by SHAPE, not colour (WCAG 1.4.1) -- a QMenu row's colour is the menu QSS's to own."""
    idx = _seed(win)
    idx[2]["stopped"] = True
    win._fill_jobs_menu()
    rows = [a.text() for a in win._jobs_menu.actions() if not a.isSeparator()]
    assert rows[0].startswith("⏹"), "a Stop reads as stopped, not as a failure"
    assert rows[1].startswith("✓") and rows[2].startswith("✓")
    assert "Import field 354" in rows[0], "newest first"
    idx[2]["stopped"] = False
    win._fill_jobs_menu()
    assert [a.text() for a in win._jobs_menu.actions() if not a.isSeparator()][0].startswith("✗")


def test_a_trimmed_job_row_disables_instead_of_mis_jumping(win, app):
    _seed(win)
    win._job_index.insert(0, {"head": "[00:00:00] Ancient job", "time": "00:00:00",
                              "subject": "Ancient job", "code": 0, "stopped": False})
    win._fill_jobs_menu()
    gone = [a for a in win._jobs_menu.actions() if "Ancient" in a.text()][0]
    assert not gone.isEnabled()
    assert "scrolled out of the log" in gone.text(), "say why it cannot be reached"
    assert win._job_span(0) is None


def test_a_jump_selects_the_job_and_reveals_its_HEAD(win, app):
    """Selected BACKWARD on purpose: ensureCursorVisible scrolls to the cursor POSITION, so a forward
    selection would reveal the job's last line and scroll its header off the top."""
    _seed(win)
    win._goto_job(1)
    app.processEvents()
    cur = win.output.textCursor()
    assert cur.hasSelection()
    assert cur.position() == min(cur.position(), cur.anchor()), "the cursor sits at the HEAD, so we scroll there"
    lo, hi = sorted((cur.position(), cur.anchor()))
    assert win.output.toPlainText()[lo:hi] == ("[09:41:20] Deploy field 4003\n"
                                               "wrote revert_deploy_4003.py\ndeploy ok")


def test_copy_takes_the_selection_when_there_is_one(win, app):
    """The old Copy meant 'this job' when the log held one job; accumulation silently turned it into 'the
    whole session'. A Jobs jump leaves one job selected, so Copy right after it is per-job."""
    _seed(win)
    win._goto_job(1)
    win._copy_output()
    got = QApplication.clipboard().text()
    assert got.startswith("[09:41:20] Deploy field 4003")
    assert got.endswith("deploy ok"), "the selection, and only the selection"
    assert " " not in got and "\n" in got, \
        "QTextCursor.selectedText joins blocks with U+2029 -- that would paste as ONE unbroken line"

    c = win.output.textCursor()
    c.clearSelection()
    win.output.setTextCursor(c)
    win._copy_output()
    whole = QApplication.clipboard().text()
    assert whole.count("[09:4") == 3, "with nothing selected, Copy still means the whole console"


def test_copy_the_last_job_is_the_last_job(win, app):
    _seed(win)
    win._copy_last_job()
    got = QApplication.clipboard().text()
    assert got.startswith("[09:42:07] Import field 354")
    assert got.endswith("KeyError: 'walkmesh'"), "including its final character"


def test_copy_the_last_job_is_a_no_op_with_no_jobs(win, app):
    """Never silently copy the WHOLE console when the caller asked for one job."""
    QApplication.clipboard().setText("sentinel")
    win._job_index = []
    win._copy_last_job()
    assert QApplication.clipboard().text() == "sentinel"


def test_clearing_the_log_clears_the_index_that_describes_it(win, app):
    """An index outliving its document offers jumps to lines that no longer exist (every row disabled)."""
    _seed(win)
    win._open_find("wrote")
    app.processEvents()
    win._clear_output()
    app.processEvents()
    assert win._job_index == []
    assert not win._find_bar.isVisible(), "the bar's matches are gone with the text -- so is the bar"
    win._fill_jobs_menu()
    rows = [a for a in win._jobs_menu.actions() if not a.isSeparator()]
    assert len(rows) == 1 and not rows[0].isEnabled(), "an empty index says so and offers nothing"


def test_run_job_records_the_same_head_string_it_writes(win, app):
    """The index and the document must agree BY CONSTRUCTION -- one site, one string, one moment. A second
    formatting of the timestamp is a second chance to disagree."""
    win.run_job(["cmd-that-does-not-exist-ff9mapkit"], subject="Probe job")
    app.processEvents()
    assert win._job_index, "run_job records its head"
    rec = win._job_index[-1]
    assert rec["head"] in win.output.toPlainText(), "the recorded head is findable in the document"
    assert rec["subject"] == "Probe job"
    assert logfind.job_spans(win.output.toPlainText(), [r["head"] for r in win._job_index])[-1] is not None
    win._stop_job()
    app.processEvents()


def test_find_is_reachable_by_keyboard_and_by_the_palette(win, app):
    """Ctrl+F was unbound APP-WIDE before this -- the app shipped no find of any kind. Both routes exist, and
    Ctrl-K carries the per-job copy too (this app's convention: every command is palette-reachable)."""
    from PySide6.QtGui import QKeySequence, QShortcut
    bound = {sc.key().toString() for sc in win.findChildren(QShortcut) if not sc.key().isEmpty()}
    assert QKeySequence("Ctrl+F").toString() in bound
    labels = [lbl for lbl, _k, _cb in win._command_index()]
    assert any("Find in Output" in lbl for lbl in labels)
    assert any("Copy the last job" in lbl for lbl in labels)


def test_a_collapsed_console_is_raised_before_the_bar_takes_focus(win, app):
    """The console collapses to its header strip. A find bar inside a HIDDEN body takes focus the user cannot
    see and then swallows every keystroke -- so raising it first is load-bearing, not cosmetic."""
    win._toggle_console(expand=False)
    app.processEvents()
    assert not win._console_open
    win._open_find("wrote")
    app.processEvents()
    assert win._console_open, "Ctrl+F on a collapsed console expands it"
    assert win._find_bar.isVisible()
    assert win._find_bar.field.hasFocus() or win._find_bar.field.isVisible()
