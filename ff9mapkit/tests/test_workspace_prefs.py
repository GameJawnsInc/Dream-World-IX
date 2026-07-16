"""GUI wiring for Preferences/About + the live theme switch. Headless (offscreen); no network, no modal
dialogs are opened (those .exec() — we drive the underlying state/handlers directly)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

import shutil                                         # noqa: E402
import subprocess                                      # noqa: E402

from PySide6.QtWidgets import (                         # noqa: E402
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget)

from ff9mapkit.editor import theme                    # noqa: E402
from ff9mapkit.editor.theme import pick_palette       # noqa: E402
from ff9mapkit.workspace import shell                 # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _win(app):
    return shell.Workspace(pick_palette("dark"))


def test_retheme_swaps_palette_for_every_theme(app):
    w = _win(app)
    for mode, pal in theme.THEMES.items():
        w.retheme(pick_palette(mode))
        assert w.pal is pal, mode
        # the global stylesheet tracks the new palette (its bg colour appears in the QSS)
        assert pal["bg"] in w.styleSheet(), mode


def test_retheme_retints_the_version_chip(app):
    w = _win(app)
    w.retheme(pick_palette("nord"))
    assert theme.NORD["muted"] in w.version_label.styleSheet()      # plain chip = muted, in the new palette
    # once an update is known, the chip goes accent — and a later retheme keeps it accent in the new palette
    w._on_update_result({"current": "0.0.0", "latest": "9.9.9", "ok": True, "newer": True}, manual=False)
    w.retheme(pick_palette("gruvbox-dark"))
    assert theme.GRUVBOX_DARK["accent"] in w.version_label.styleSheet()


def test_retheme_retints_persistent_chrome(app):
    """The always-alive chrome must follow a theme switch -- and the best way to guarantee that is to
    have no inline sheet to re-tint at all.

    This test used to assert the OPPOSITE for the breadcrumb: that its background was re-applied inline
    on every retheme. That inline sheet was SELECTOR-LESS, so it did not style the bar -- it styled the
    bar AND cascaded a stray underline onto every crumb label, six pixels above the real rule (rendered
    proof: two rows of border ink instead of one). Deleting it needed no replacement, because the bar is
    a QWidget subclass without WA_StyledBackground: it paints no background of its own, `#crumbRow` shows
    through from the app sheet, and it became theme-live for free.

    So the assertion inverts. An inline sheet is now the defect, not the mechanism.
    """
    w = _win(app)
    w.retheme(pick_palette("gruvbox-dark"))
    assert w._hub_btn.objectName() == "hub"
    assert theme.GRUVBOX_DARK["help"] in w.styleSheet()                 # #hub violet tint tracks pal['help']
    assert not w.crumb.styleSheet(), (
        "the breadcrumb must carry NO inline sheet -- a selector-less one cascades to every child, and "
        "any inline one has to be hand-re-tinted and can go stale"
    )
    # and the app sheet really does paint that band, so deleting the inline sheet lost nothing
    assert "QWidget#crumbRow" in w.styleSheet()


def test_run_upgrade_without_uv_shows_manual_command(app, monkeypatch):
    # the path CI/non-Windows takes: no detached PowerShell spawn, just the manual command.
    w = _win(app)
    monkeypatch.setattr(shutil, "which", lambda _n: None)
    info, popen = [], []
    monkeypatch.setattr(shell.QMessageBox, "information", lambda *a, **k: info.append(a))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: popen.append(a))
    w._run_upgrade()
    assert info and not popen
    assert any(shell.update_check.UPGRADE_COMMAND in str(a) for a in info)


def test_run_upgrade_non_windows_shows_manual_command(app, monkeypatch):
    w = _win(app)
    monkeypatch.setattr(shutil, "which", lambda _n: "/usr/bin/uv")      # uv present...
    monkeypatch.setattr(shell.os, "name", "posix")                      # ...but not Windows
    info, popen = [], []
    monkeypatch.setattr(shell.QMessageBox, "information", lambda *a, **k: info.append(a))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: popen.append(a))
    w._run_upgrade()
    assert info and not popen


def test_preferences_cancel_reverts_live_preview(app, monkeypatch):
    w = _win(app)
    w.retheme(pick_palette("dark"))
    monkeypatch.setattr(shell.prefs, "theme", lambda: "dark")           # combo opens on Dark
    monkeypatch.setattr(shell.prefs, "set_theme", lambda *_: None)

    def fake_exec(dlg):
        combo = dlg.findChild(QComboBox)
        combo.setCurrentIndex(combo.findData("gruvbox-dark"))           # live preview fires
        assert w.pal is theme.GRUVBOX_DARK                             # ...and is applied
        dlg.reject()                                                   # Cancel -> finished -> revert
        return 0

    monkeypatch.setattr(shell.QDialog, "exec", fake_exec, raising=False)
    w._open_preferences()
    assert w.pal is theme.DARK                                         # reverted to the pre-dialog palette


def test_preferences_ok_keeps_preview_and_persists(app, monkeypatch):
    w = _win(app)
    w.retheme(pick_palette("dark"))
    monkeypatch.setattr(shell.prefs, "theme", lambda: "dark")
    saved = []
    monkeypatch.setattr(shell.prefs, "set_theme", lambda m: saved.append(m))
    monkeypatch.setattr(shell.update_check, "is_installed", lambda: False)   # skip update-state write here

    def fake_exec(dlg):
        combo = dlg.findChild(QComboBox)
        combo.setCurrentIndex(combo.findData("gruvbox-dark"))
        dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
        return 1

    monkeypatch.setattr(shell.QDialog, "exec", fake_exec, raising=False)
    w._open_preferences()
    assert w.pal is theme.GRUVBOX_DARK                                 # kept (not reverted)
    assert saved == ["gruvbox-dark"]                                   # persisted


def test_preferences_writes_update_optin_only_when_installed(app, monkeypatch):
    monkeypatch.setattr(shell.prefs, "theme", lambda: "dark")
    monkeypatch.setattr(shell.prefs, "set_theme", lambda *_: None)
    monkeypatch.setattr(shell.update_check, "is_enabled", lambda: False)

    def run_ok(installed):
        w = _win(app)
        monkeypatch.setattr(shell.update_check, "is_installed", lambda: installed)
        calls = []
        monkeypatch.setattr(shell.update_check, "set_preference", lambda v: calls.append(v))

        def fake_exec(dlg):
            chk = dlg.findChild(QCheckBox, "update_chk")   # only present on an installed copy (by NAME --
            if chk is not None:                            # the restore-session checkbox always exists)
                chk.setChecked(True)
            dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
            return 1

        monkeypatch.setattr(shell.QDialog, "exec", fake_exec, raising=False)
        w._open_preferences()
        return calls

    assert run_ok(True) == [True]      # installed copy persists the opt-in
    assert run_ok(False) == []         # source checkout never writes update-check state


def test_preferences_update_toggle_only_on_installed(app, monkeypatch):
    # installed -> a real clickable checkbox; source checkout -> NO dead/disabled checkbox (a note instead)
    monkeypatch.setattr(shell.prefs, "theme", lambda: "dark")
    seen = {}

    def fake_exec(dlg):
        seen["chk"] = dlg.findChild(QCheckBox, "update_chk")
        dlg.reject()
        return 0

    monkeypatch.setattr(shell.QDialog, "exec", fake_exec, raising=False)
    monkeypatch.setattr(shell.update_check, "is_installed", lambda: True)
    _win(app)._open_preferences()
    assert seen["chk"] is not None
    monkeypatch.setattr(shell.update_check, "is_installed", lambda: False)
    _win(app)._open_preferences()
    assert seen["chk"] is None


def test_upgrade_ps1_is_parameterized():
    # the detached helper takes its inputs as params (no interpolation) and uses each one.
    ps1 = shell._UPGRADE_PS1
    assert "param([int]$AppPid, [string]$Uv, [string]$Launcher)" in ps1
    assert "Wait-Process -Id $AppPid" in ps1       # waits on the app PID (lock-safety)
    assert "$Uv tool upgrade ff9mapkit" in ps1     # upgrades via the passed uv path
    assert "Start-Process $Launcher" in ps1        # relaunches the passed launcher


def test_settings_menu_and_palette_commands_exist(app):
    w = _win(app)
    assert w._settings_btn is not None
    labels = {c[0] for c in w._command_index()}
    assert {"Preferences…", "About Dream World IX", "Check for updates…"} <= labels


def test_startup_uses_the_saved_theme(app, monkeypatch):
    # main() resolves the palette from prefs.theme(); a saved "nord" must drive the window's palette.
    monkeypatch.setattr(shell.prefs, "theme", lambda: "nord")
    monkeypatch.setattr(shell.update_check, "auto_check_allowed", lambda: False)   # no network/prompt
    monkeypatch.setattr(shell.sys, "exit", lambda *_a, **_k: None)                 # don't kill the test run
    monkeypatch.setattr(shell.QApplication, "exec", lambda *_a, **_k: 0)
    created = {}
    real_init = shell.Workspace.__init__

    def _spy(self, pal):
        created["pal"] = pal
        real_init(self, pal)

    monkeypatch.setattr(shell.Workspace, "__init__", _spy)
    monkeypatch.setattr(shell.Workspace, "show", lambda self: None)
    shell.main(["ff9_workspace"])
    assert created["pal"] is theme.NORD


# ---- recent projects (MRU) — prefs-level, no Qt needed beyond the module import above ----

@pytest.fixture()
def prefs_file(tmp_path, monkeypatch):
    """Point the prefs store at a throwaway file so MRU tests never touch the real prefs.json."""
    from ff9mapkit import prefs
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    return prefs


def test_recent_round_trip_dedupes_and_caps(prefs_file, tmp_path):
    p = prefs_file
    for i in range(p.RECENT_LIMIT + 3):
        p.add_recent("field", tmp_path / f"f{i}.field.toml")
    rows = p.recent()
    assert len(rows) == p.RECENT_LIMIT                       # capped
    assert rows[0]["path"].endswith(f"f{p.RECENT_LIMIT + 2}.field.toml")   # most recent first
    p.add_recent("field", tmp_path / f"f{p.RECENT_LIMIT}.field.toml")      # re-open -> moves to front, no dup
    rows = p.recent()
    assert rows[0]["path"].endswith(f"f{p.RECENT_LIMIT}.field.toml")
    assert len({e["path"] for e in rows}) == len(rows)


def test_recent_survives_garbage_and_unknown_kinds(prefs_file, tmp_path):
    p = prefs_file
    p.add_recent("overworld", tmp_path / "nope.toml")        # unknown kind -> ignored
    assert p.recent() == []
    (tmp_path / "prefs.json").write_text(
        '{"recent": ["junk", {"kind": "field"}, {"kind": "campaign", "path": "C:/x/campaign.toml"},'
        ' {"kind": "field", "path": 7}], "theme": "dark"}', encoding="utf-8")
    rows = p.recent()                                        # only the one well-formed entry survives
    assert rows == [{"kind": "campaign", "path": "C:/x/campaign.toml"}]
    assert p.theme() == "dark"                               # unrelated keys untouched


def test_remove_recent(prefs_file, tmp_path):
    p = prefs_file
    p.add_recent("save", tmp_path / "SavedData_ww.dat")
    p.add_recent("journey", tmp_path / "journeys.toml")
    gone = p.recent()[1]["path"]
    p.remove_recent(gone)
    assert [e["kind"] for e in p.recent()] == ["journey"]


def test_restore_session_and_layout_prefs(prefs_file):
    p = prefs_file
    assert p.restore_session() is False                      # opt-in: default off
    p.set_restore_session(True)
    assert p.restore_session() is True
    p.set_layout({"geometry": "QUJD", "state": "REVG", "central_split": [300, 640, 240]})
    assert p.layout() == {"geometry": "QUJD", "state": "REVG", "central_split": [300, 640, 240]}
    p.set_layout({"geometry": 7, "central_split": ["x", -1]})   # garbage -> dropped per-key
    assert p.layout() == {}


def test_layout_prefs_carry_the_console_pane(prefs_file):
    p = prefs_file
    p.set_layout({"console_split": [560, 220], "console_collapsed": True})
    assert p.layout() == {"console_split": [560, 220], "console_collapsed": True}
    p.set_layout({"console_split": [560, 220], "console_collapsed": False})
    assert p.layout() == {"console_split": [560, 220]}           # only a TRUE collapse is persisted
    p.set_layout({"console_split": "tall", "console_collapsed": "yes"})   # garbage -> dropped per-key
    assert p.layout() == {}


def test_a_squeezed_panel_is_not_a_preference(app):
    """One narrow session must not be permanent.

    THE BUG: the document column has a hard minimum, so a too-narrow window can only take the width out of
    the OUTER panes, which clamp to their minimums. _save_layout persisted that as a choice, and because
    the middle pane holds stretch factor 1 it swallowed the entire surplus on the next launch -- so
    [90, 542, 66] saved at 700px reopened at 1280 as [90, 1122, 66] and the panels never came back at any
    width. (The reporter's real prefs read [76, 1138, 64].)

    The floor is READ, never written as a literal: it is font-dependent (78 real / 74 offscreen), and this
    module runs offscreen, whose stub font DB has already manufactured a fake width once this arc.
    """
    w = _win(app)
    sp = w._central_split
    tree_floor = sp.widget(0).minimumSizeHint().width()
    insp_floor = sp.widget(2).minimumSizeHint().width()

    # PINNED AT THE MINIMUM == forced by the window. Heal it. (A no-op _repair fails both of these.)
    assert w._repair_central_split([tree_floor, 1138, 640]) == shell._DEFAULT_CENTRAL_SPLIT
    assert w._repair_central_split([640, 1138, insp_floor]) == shell._DEFAULT_CENTRAL_SPLIT
    assert w._repair_central_split([tree_floor + 2, 1138, 640]) == shell._DEFAULT_CENTRAL_SPLIT

    # COLLAPSED TO ZERO == chosen (childrenCollapsible is on -- the user dragged it shut). Keep it.
    assert w._repair_central_split([0, 940, 240]) == [0, 940, 240]
    assert w._repair_central_split([240, 940, 0]) == [240, 940, 0]

    # Comfortably above the floor == a real drag. Keep it.
    assert w._repair_central_split([420, 620, 380]) == [420, 620, 380]
    assert w._repair_central_split(list(shell._DEFAULT_CENTRAL_SPLIT)) == list(shell._DEFAULT_CENTRAL_SPLIT)

    # Wrong arity never reaches setSizes (prefs.layout() fences it too -- belt and braces).
    assert w._repair_central_split([300, 640]) == shell._DEFAULT_CENTRAL_SPLIT
    w.close()


def test_the_restore_path_spends_the_repair(app, monkeypatch):
    """The mechanism above is worth nothing if the call site does not spend it -- this arc's oldest lesson.
    A saved squeeze must not survive _restore_layout.

    THIS ASSERTS THE REQUEST, NOT THE RENDERED SIZES, and the distinction is the whole reason the test is
    written this way: offscreen's stub font DB reports mid_col's minimum as 1156 (real: 542), so offscreen
    re-clamps the healed [300, 640, 240] straight back to [74, 1156, 66]. Asserting sizes() here fails on
    a CORRECT fix -- the harness, not the code. What restore owes us is that it never HANDS the squeeze to
    the splitter; what the splitter then does with a fake font DB is offscreen's business.
    """
    from PySide6.QtWidgets import QSplitter
    seen = []
    orig = QSplitter.setSizes

    def spy(self, sizes):
        seen.append(list(sizes))
        return orig(self, sizes)

    monkeypatch.setattr(QSplitter, "setSizes", spy)
    monkeypatch.setattr(shell.prefs, "layout", lambda: {"central_split": [76, 1138, 64]})
    w = _win(app)                                        # __init__ runs _restore_layout
    assert [76, 1138, 64] not in seen, "the squeeze was replayed -- the repair is not wired into restore"
    assert list(shell._DEFAULT_CENTRAL_SPLIT) in seen, "restore never asked for the healed layout"
    w.close()


def test_console_collapses_to_its_header_and_re_expands(app):
    w = _win(app)
    w.show()                                                     # the splitter needs a layout pass
    assert not w.findChildren(QDockWidget)                       # no docks == no dock-drag artifacts
    assert not w._console_open                                   # P0 makeover: collapsed by default on a cold start
    w._toggle_console()                                          # expand it (the header caret)
    assert w._console_open
    open_h = w._vsplit.sizes()[1]
    assert open_h > w._console_head_h()

    w._toggle_console()                                          # click the header caret again -> collapse
    assert not w._console_open and not w.console_body.isVisible()
    assert w.console_panel.maximumHeight() == w._console_head_h()

    w._raise_console()                                           # a job starting must re-open the console
    assert w._console_open and w.console_body.isVisible()
    assert w._vsplit.sizes()[1] == open_h                        # restored to where the user left the divider
    w.close()


def test_console_collapse_state_round_trips_through_prefs(app, monkeypatch):
    w = _win(app)
    w.show()
    saved = {}
    monkeypatch.setattr(shell.prefs, "set_layout", saved.update)
    # P0 makeover: the console is collapsed by default. It must persist AS collapsed, carrying the
    # remembered EXPANDED sizes (so a re-open restores the divider, not the collapsed header pin).
    assert not w._console_open
    w._save_layout()
    assert saved["console_collapsed"] is True
    assert saved["console_split"][1] > w._console_head_h()       # the EXPANDED sizes, not the collapsed pin
    w.close()


def test_restore_reopens_a_console_the_user_left_open(app, monkeypatch):
    # The prefs layer DROPS console_collapsed when it's False (only a TRUE collapse persists), so a saved
    # session where the user had the console OPEN carries console_split but no flag. Restore must reopen it,
    # overriding the P0 collapsed-by-default -- else returning users silently lose their open console.
    w = _win(app)
    w.show()
    assert not w._console_open                                    # cold-start default = collapsed
    monkeypatch.setattr(shell.prefs, "layout", lambda: {"console_split": [560, 220]})
    w._restore_layout()
    assert w._console_open and w.console_body.isVisible()
    w.close()


def test_restore_honors_a_saved_collapse(app, monkeypatch):
    w = _win(app)
    w.show()
    w._toggle_console()                                           # expand first, so the restore has to re-collapse
    assert w._console_open
    monkeypatch.setattr(shell.prefs, "layout",
                        lambda: {"console_split": [560, 220], "console_collapsed": True})
    w._restore_layout()
    assert not w._console_open
    w.close()


def test_the_text_size_dial_drives_every_surface_it_owns(app):
    """THE LIVE PATH, which nothing tested -- and it shipped a NameError past 3621 green tests.

    `_apply_text_scale` reached for `_fq`, which is a LOCAL in `__init__`. Compiles clean, imports clean,
    every test passes; the first turn of the dial raises. Nothing drove it because CALIBRE's fences all
    assert `qss(pal, density, scale)` -- a pure function -- and the SHELL's job is the other half: telling
    the three surfaces a stylesheet cannot reach.

    So this drives the real method and asserts each surface actually moved:
      * the QSS (every tab),
      * the hero band (QPainter -- PLINTH),
      * forms_qt's rich-text ramp (HTML in a QTextEdit -- no QSS role reaches inside a text document).
    """
    import re

    from ff9mapkit import prefs
    from ff9mapkit.workspace import forms_qt

    win = _win(app)
    seen = []
    for pct in prefs.TEXT_SCALES:
        win._apply_text_scale(pct)
        body = int(re.search(r"QWidget \{[^}]*font-size: (\d+)px", win.styleSheet()).group(1))
        band = win._hero.height()
        hub = forms_qt._px("type_body")
        seen.append((body, band, hub))
        assert forms_qt._TEXT_SCALE == pct, f"{pct}%: the rich-text ramp was not told"
    win._apply_text_scale(100)

    for i in range(1, len(seen)):
        assert all(c >= p for c, p in zip(seen[i], seen[i - 1])), f"a surface did not follow the dial: {seen}"
    assert seen[-1] != seen[0], "nothing moved at all"
    assert len({s[2] for s in seen}) > 1, "the Info Hub's ramp is frozen -- it was 13px at every scale"
