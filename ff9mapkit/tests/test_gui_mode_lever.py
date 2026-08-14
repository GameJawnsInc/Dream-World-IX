"""GUI-UX wave (shell.py cluster, part 1):

  * ASK #12 — 'Beginner mode' as a real CROSS-TAB lever: Full opens every expert drawer, Guided
    collapses them, and the computed auto-expand overrides (a non-default co-op play style, a
    configured Walk-as swap) keep WINNING over the mode default (chair ruling).
  * ASK #10 — a quiet status-bar MODE CHIP (Guided / Full) that opens Preferences.
  * ASK #1's Preferences row — 'Ask before reversible deploys', live-applied on OK, dropped on Cancel.

Headless (offscreen). No modal is exec()'d -- shell's QDialog NAME is swapped for a subclass whose
exec runs the test's script (never a patch of the live Qt class), the same way test_workspace_prefs
does. prefs._path is pinned at a throwaway file (THE DISEASE)."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt                                     # noqa: E402
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog,   # noqa: E402
                               QDialogButtonBox, QToolButton)

from ff9mapkit.workspace import forms_qt, shell                   # noqa: E402
from ff9mapkit.workspace.shell import pick_palette                # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _pin_prefs(tmp_path, monkeypatch):
    # THE DISEASE: never read/write the developer's prefs.json. Pin _path at a throwaway file for the
    # whole test; the empty file means every getter returns its default (guided=True), so the window
    # constructs deterministically in Guided mode regardless of the machine it runs on.
    monkeypatch.setattr(shell.prefs, "_path", lambda: tmp_path / "prefs.json")
    _saved = forms_qt._GUIDED                       # the shell mutates this process global -- restore it
    yield
    forms_qt.set_guided(_saved)


def _win():
    return shell.Workspace(pick_palette("dark"))


def _scripted_dialog(monkeypatch, script):
    """Swap shell's QDialog NAME for a subclass whose exec runs the test's script against the live
    dialog -- built before any instance exists, never a patch of the live Qt class (the shiboken
    override-cache poison, studies/pyside-gc-crash). _open_preferences builds `QDialog(self)` from
    shell's module global, so the name swap is the seam."""
    class _ScriptedExec(QDialog):
        def exec(self):
            return script(self)

    monkeypatch.setattr(shell, "QDialog", _ScriptedExec)


def _neutralize_coop(cd):
    """Zero Co-op's play-style widgets to their defaults. The comes-back override reads whatever this
    machine's real Memoria.ini says, so a dev box with a granted party slot would keep the drawer open
    regardless of the mode -- reset the widgets so the override is deterministically OFF for the tests
    that assert the plain mode default."""
    for cb in cd.cb_slots:
        cb.setChecked(False)
    cd.combo_ghost.setCurrentIndex(0)
    cd.cb_follow.setChecked(False)


# ---------------------------------------------------------------- ASK #12: the cross-tab lever ---
def test_full_mode_opens_every_expert_drawer_and_guided_collapses_them(app):
    """THE LEVER. Full blows every always-visible expert drawer open; Guided (no override active)
    collapses them all. The no-op fence: we open them via Full FIRST, so a Guided that does nothing
    would leave them open and fail the second loop."""
    w = _win()
    _neutralize_coop(w.coop_doc)                     # the coop override reads the machine's Memoria.ini
    drawers = [w.build_deploy._advanced, w.coop_doc.style_drawer,
               w.import_field.swap_drawer, w.import_field._more_import]
    w._apply_guided(True)                            # a known Guided baseline (no override) -> all collapsed
    for d in drawers:
        assert not d.toggle_button.isChecked()
    w._apply_guided(False)                           # -> Full
    for d in drawers:
        assert d.toggle_button.isChecked(), "Full opens every expert drawer"
    w._apply_guided(True)                            # -> Guided (no override) collapses them; a no-op fails
    for d in drawers:
        assert not d.toggle_button.isChecked(), "Guided collapses every expert drawer"
    w.close()


def test_a_nondefault_coop_play_style_keeps_its_drawer_open_in_guided(app):
    """CHAIR RULING: the computed auto-expand override wins over the mode default. A granted party slot
    keeps Co-op's Advanced drawer open even in Guided -- a configured knob is never hidden."""
    w = _win()
    cd = w.coop_doc
    _neutralize_coop(cd)                             # start from a clean, override-free baseline
    cd.cb_slots[0].setChecked(True)                  # a non-default play style = the override
    w._apply_guided(True)                            # Guided would normally collapse it...
    assert cd.style_drawer.toggle_button.isChecked(), "the override wins over the Guided default"
    cd.cb_slots[0].setChecked(False)                 # clear it -> now the mode default applies
    w._apply_guided(True)
    assert not cd.style_drawer.toggle_button.isChecked(), "with no override, Guided collapses it"
    w.close()


def test_a_configured_walk_as_swap_keeps_its_drawer_open_in_guided(app):
    """The Import Walk-as override (a set swap) wins over the Guided default, while its sibling 'More ways
    to import' -- which has no override -- follows the mode."""
    w = _win()
    im = w.import_field
    im.swap_player.setCurrentText("vivi")            # a set swap = the override (also opens it live)
    w._apply_guided(True)
    assert im.swap_drawer.toggle_button.isChecked(), "a set swap keeps the drawer open in Guided"
    assert not im._more_import.toggle_button.isChecked(), "'More ways' has no override -> follows the mode"
    im.swap_player.setCurrentText("")                # clear -> the mode default applies
    w._apply_guided(True)
    assert not im.swap_drawer.toggle_button.isChecked(), "with no swap, Guided collapses it"
    w.close()


def test_a_battle_target_keeps_builddoc_advanced_open_in_guided(app):
    """builddoc's one computed override: the Deploy-battle box lives INSIDE the Advanced drawer, so a
    loaded battle target reveals it (builddoc._update_dest). That reveal must WIN over the Guided default
    (chair ruling), or a battle deploy's controls vanish in Guided mode."""
    w = _win()
    bd = w.build_deploy
    bd.kind = "battle"                              # simulate a loaded battle target = the override
    w._apply_guided(True)                           # Guided would normally collapse it...
    assert bd._advanced.toggle_button.isChecked(), "a battle target keeps the Advanced drawer open"
    bd.kind = "field"                               # a plain field: no override -> the mode default applies
    w._apply_guided(True)
    assert not bd._advanced.toggle_button.isChecked(), "a non-battle target follows the Guided default"
    w.close()


def test_battledoc_apply_guided_is_safe_with_no_node_open(app):
    """The Battle panel is _GUIDED-gated (Full inline / Guided drawer), so its lever REBUILDS the mounted
    form -- but with no battle.toml loaded there is no node to re-mount. That must be a quiet no-op, not a
    raise (currentRow() is -1)."""
    w = _win()
    w.battle.apply_guided(True)                      # no node -> no-op
    w.battle.apply_guided(False)
    w.close()


def test_cancel_reverts_a_previewed_mode_flip(app, monkeypatch):
    """The round-5 lesson: a live preview that Cancel does not undo is a bug. Flipping the mode in the
    Preferences preview opens the drawers; Cancel must put them (and the mode) back."""
    w = _win()
    drawer = w.build_deploy._advanced
    assert not drawer.toggle_button.isChecked()      # Guided default

    def fake_exec(dlg):
        w._apply_guided(False)                       # preview Full -> the drawer opens
        assert drawer.toggle_button.isChecked()
        dlg.reject()                                 # Cancel -> _finish reverts
        return 0

    _scripted_dialog(monkeypatch, fake_exec)
    w._open_preferences()
    assert forms_qt._GUIDED is True, "Cancel restores the mode"
    assert not drawer.toggle_button.isChecked(), "Cancel re-collapses the previewed-open drawer"
    w.close()


# ---------------------------------------------------------------- ASK #10: the mode chip ---
def test_the_mode_chip_names_the_mode_and_is_a_focusable_tab_stop(app):
    w = _win()
    chip = w.mode_chip
    assert isinstance(chip, QToolButton) and chip.objectName() == "modeChip"
    assert chip.focusPolicy() != Qt.FocusPolicy.NoFocus, "the chip is a keyboard tab stop"
    assert chip.accessibleName(), "the chip announces a screen-reader name"
    assert chip.text() == "Guided"                   # the pinned default
    w._apply_guided(False)
    assert chip.text() == "Full", "the chip tracks a live mode flip"
    w._apply_guided(True)
    assert chip.text() == "Guided"
    w.close()


def test_the_mode_chip_is_quiet_no_accent(app):
    # ONE accent per surface: the chip is muted, never the accent. Its id-rule (style.py) sets `color:
    # muted`, and it carries no #accent objectName the way the co-op Start button does.
    from ff9mapkit.workspace.style import qss
    from ff9mapkit.editor.theme import pick_palette as _pp
    sheet = qss(_pp("dark"))
    assert "QToolButton#modeChip" in sheet, "the chip has its own quiet id-rule"
    assert "QToolButton#modeChip:focus" in sheet, "and a visible focus ring (WCAG 2.4.7)"
    assert _win().mode_chip.objectName() != "accent"


def test_the_mode_chip_opens_preferences(app, monkeypatch):
    w = _win()
    seen = []

    def fake_exec(dlg):
        seen.append(dlg.windowTitle())
        dlg.reject()
        return 0

    _scripted_dialog(monkeypatch, fake_exec)
    w.mode_chip.click()
    assert seen == ["Preferences"], "activating the chip opens the Preferences dialog"
    w.close()


# ---------------------------------------------------------------- ASK #1's Preferences row ---
def test_confirm_reversible_row_persists_on_ok(app, monkeypatch):
    w = _win()
    saved = []
    monkeypatch.setattr(shell.prefs, "set_confirm_reversible_deploys", lambda v: saved.append(v))
    monkeypatch.setattr(shell.update_check, "is_installed", lambda: False)   # no update-pref write here

    def fake_exec(dlg):
        chk = dlg.findChild(QCheckBox, "confirm_reversible_chk")
        assert chk is not None, "the Preferences dialog carries the confirm-reversible row"
        assert chk.isChecked() is False, "it reflects the default (off = one-key F9 loop)"
        chk.setChecked(True)
        dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
        return 1

    _scripted_dialog(monkeypatch, fake_exec)
    w._open_preferences()
    assert saved == [True], "OK persists the opt-in"
    w.close()


def test_confirm_reversible_row_does_not_persist_on_cancel(app, monkeypatch):
    w = _win()
    saved = []
    monkeypatch.setattr(shell.prefs, "set_confirm_reversible_deploys", lambda v: saved.append(v))

    def fake_exec(dlg):
        dlg.findChild(QCheckBox, "confirm_reversible_chk").setChecked(True)
        dlg.reject()
        return 0

    _scripted_dialog(monkeypatch, fake_exec)
    w._open_preferences()
    assert saved == [], "Cancel writes nothing"
    w.close()
