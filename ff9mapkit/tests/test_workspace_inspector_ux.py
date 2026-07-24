"""Ask-user #14 (low-risk half) + #7 (tree half) -- the Inspector stops lying and starts jumping.

#14: 'Select something on the left.' is an INSTRUCTION, only true on the tree-driven Editor tab with a
populated tree (anywhere else a tree click JUMPS you away, and over an empty tree there is nothing to
select). The untouched inspector now shows a thin muted rule in the false cases instead.

#7: the CONTENTS rollup's tallies ('3 NPCs, BGM, ...') were inert muted text one line under a linked
encounter -- the call-site law's exhibit. Every tally is now a ``goto:tree:`` link that lands its own
tree row (group header for lists, section node for singles, member-row fallback -- never a dead click).

Headless (offscreen), NO_THUMBS -- opening a field must not touch any preview cache; prefs are isolated
by conftest's autouse ``_isolate_prefs``.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication                                     # noqa: E402

from ff9mapkit.workspace import anim                                           # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app):
    from ff9mapkit.editor.theme import pick_palette
    from ff9mapkit.workspace.shell import Workspace, _apply_app_theme
    anim.set_enabled(False)                              # a test that leaves motion on strands real animations
    _apply_app_theme(app, pick_palette("dark"))
    w = Workspace(pick_palette("dark"))
    w.show()
    app.processEvents()
    yield w
    w.close()


def _open_test_field(win, tmp_path, app):
    """A loose field with a list section (npc), two singles (music + encounter), and a name the rollup
    links will carry."""
    p = tmp_path / "T.field.toml"
    p.write_text(
        '[field]\nname = "T"\nid = 30100\n\n'
        '[music]\nsong = 42\n\n'
        '[encounter]\nscene = 67\nfreq = 32\n\n'
        '[[npc]]\nname = "bob"\npreset = "vivi"\ndialogue = "hi"\n',
        encoding="utf-8")
    assert win.open_field(str(p))
    app.processEvents()
    return p


# --------------------------------------------------------------------- #14: the tab-aware empty-state
def test_the_untouched_inspector_never_instructs_where_following_is_a_jump(win, app):
    """With nothing ever inspected: Home (empty tree) and a self-contained tab both show the thin muted
    rule -- never 'Select something on the left.', which is false in both places."""
    assert "Select something" not in win.insp_body.text(), "empty tree: nothing to select, no instruction"
    win.tabs.setCurrentWidget(win.build_deploy)
    app.processEvents()
    assert "Select something" not in win.insp_body.text(), "a self-contained tab never shows the instruction"
    assert win.insp_body.text(), "presence, not a blank void -- the rule is drawn"


def test_a_mounted_card_ends_the_empty_states_watch(win, app, tmp_path):
    """Opening a field mounts a real card; switching to a self-contained tab must keep the CARD (content
    stays put across tabs, as it always has) -- the tab-aware refresh only owns the never-touched state."""
    _open_test_field(win, tmp_path, app)
    card = win.insp_body.text()
    assert card and "Select something" not in card, "a real card mounted on open"
    win.tabs.setCurrentWidget(win.build_deploy)
    app.processEvents()
    assert win.insp_body.text() == card, "the card survives the tab change untouched"


# ------------------------------------------------------------------------- #7: rollup tallies are links
def test_every_rollup_tally_is_a_tree_link(win, app, tmp_path):
    """The Contents line links each tally: the npc LIST, and the music + encounter SINGLES ('BGM' was the
    proposal's named inert exhibit)."""
    _open_test_field(win, tmp_path, app)
    body = win.insp_body.text()
    assert 'href="goto:tree:T:npc"' in body, body
    assert 'href="goto:tree:T:music"' in body, "BGM must carry the jump it always named"
    assert 'href="goto:tree:T:encounter"' in body


def test_a_rollup_link_lands_its_own_tree_row(win, app, tmp_path):
    """Dispatching the npc tally's href selects the NPCs group row (the _reveal_after_undo resolve,
    finally spent from the rollup)."""
    _open_test_field(win, tmp_path, app)
    mi = win._member_items["T"]
    win.tree.expandItem(mi)                              # build the lazy subtree so the group row exists
    app.processEvents()
    win._inspect_link("goto:tree:T:npc")
    app.processEvents()
    p = win._payload(win.tree.currentItem())
    assert p and p[0] == "group" and p[2] == "npc", f"landed {p!r}, not the NPCs group"


def test_a_rollup_link_is_never_a_dead_click(win, app, tmp_path):
    """An EMPTY section's tree row still exists (group headers show their count + Add), so the jump
    lands it -- and an href for a member that is gone (stale card) is a guarded no-op, never a crash."""
    _open_test_field(win, tmp_path, app)
    win._inspect_link("goto:tree:T:gateway")             # no gateways authored -> the (0) group row
    app.processEvents()
    p = win._payload(win.tree.currentItem())
    assert p and p[0] == "group" and p[2] == "gateway", f"landed {p!r}, not the Gateways group"
    before = win.tree.currentItem()
    win._inspect_link("goto:tree:GONE:npc")              # a member that no longer exists
    app.processEvents()
    assert win.tree.currentItem() is before, "a stale href changes nothing (and crashes nothing)"
