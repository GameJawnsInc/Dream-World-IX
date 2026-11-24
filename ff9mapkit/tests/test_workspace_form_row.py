"""SHELL-side fences for a mounted Editor form versus edits made in ANOTHER tab (review
finding P1).

An Editor form for a list row (a gateway, an NPC, an event…) remembered WHICH row it edits as
a list index, taken when it was mounted. Switching to the Place tab neither committed the form
nor told it anything, and Place deletes and reshapes rows of the same lists. The next fold
(any navigation, Save, Undo) then wrote the form's values into ``list[old index]``: with an
earlier row deleted, that is a DIFFERENT row — one gateway destroyed, another doubled. The
form's own Save, Delete and Reset buttons carried the same index.

Three things are pinned here: the row is found by IDENTITY, never by a remembered index (so no
route to a moved list can misroute a write); entering a tab that edits the open field commits
the pending form first; and a form left mounted is rebuilt when another tab changes its row.

Behaviour + data only — no geometry or font claim — so offscreen is sound here.
"""
from __future__ import annotations

import os
import tomllib

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QPushButton                  # noqa: E402

from ff9mapkit.editor import forms                                       # noqa: E402
from ff9mapkit.editor.theme import pick_palette                          # noqa: E402
from ff9mapkit.scene import guide                                        # noqa: E402
from ff9mapkit.workspace import shell                                    # noqa: E402
from ff9mapkit.workspace.forms_qt import read                            # noqa: E402

_M = "X"                                              # open_field keys the member by its [field] NAME


def _zone(x):
    return [[x, 600], [x + 100, 600], [x + 100, 700], [x, 700]]


_TOML = ('[field]\nid = 30999\nname = "X"\narea = 11\nsource_field = 351\n\n'
         + "".join(f'[[gateway]]\nname = "g{i}"\nto = {100 + i}\nzone = {_zone(i * 200)}\n\n'
                   for i in range(3)))
_NEW_QUAD = [(-640.0, 900.0), (-540.0, 900.0), (-540.0, 1000.0), (-640.0, 1000.0)]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def win(app, tmp_path, monkeypatch):
    from ff9mapkit import prefs
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")
    w = shell.Workspace(pick_palette("dark"))
    p = tmp_path / "X.field.toml"
    p.write_text(_TOML, encoding="utf-8")
    assert w.open_field(p)
    w.toml = p
    yield w
    w.hide()


def _gateways(win):
    return [(g["name"], g["to"]) for g in win._doc(_M).data.get("gateway", [])]


def _mount(win, key="gateway:1"):
    win._open_editor(_M, "object", key)
    assert win._save_ctx and win._save_ctx["key"] == key


def _select(win, key="gateway:1"):
    """Mount a row's form the way a user does: by selecting its row in the tree."""
    item = win._object_item(_M, key)
    assert item is not None, f"the tree has no row for {key}"
    win.tree.setCurrentItem(item)
    QApplication.processEvents()
    assert win._save_ctx and win._save_ctx["key"] == key


def _type(win, field, text):
    """Type into the mounted form's REAL widget (its getter is the widget's bound method), and do
    not navigate: the edit is pending, exactly as a user leaves it when they click another tab."""
    win._save_ctx["getters"][field].__self__.setText(text)


def _arm_place(win):
    """The Place tab with a room loaded (a kit-built flat floor; no install, no disk)."""
    pd = win.place_doc
    floor = [((-1000.0, 0.0, 500.0), (1000.0, 0.0, 500.0), (1000.0, 0.0, 2500.0)),
             ((-1000.0, 0.0, 500.0), (1000.0, 0.0, 2500.0), (-1000.0, 0.0, 2500.0))]
    bundle = {"donor": 351, "source": ("real", 351), "cam_index": 0, "n_cams": 1,
              "cam": guide.make_camera(26.0, 3000.0, fov_x_deg=42.0), "png": None,
              "tris": floor, "floors": [0, 0]}
    pd._bundles[(("real", 351), 0)] = bundle
    pd._apply_bundle(bundle, refit=True)
    return pd


def _row(pd, name):
    """The Place canvas row of the gateway called ``name`` (rows are addressed by feed order)."""
    return next(r["i"] for r in pd._region_rows_cache if r["label"].startswith(name + " "))


def _navigate(win):
    """A tree navigation: it folds the leaving form (the boundary where the damage landed). The
    member row may ALREADY be current (a Place edit rebuilds the object rows, and Qt then parks
    the selection on their parent), in which case selecting it fires nothing — so the handler
    is run by hand, the way the shell's own ``_goto_focus`` does for an unchanged selection.
    Without that this helper folded nothing and every test built on it was vacuous."""
    win.tabs.setCurrentWidget(win.doc_scroll)
    item = win._member_items[_M]
    win.tree.setCurrentItem(item)
    item.setSelected(True)
    win._on_select()
    QApplication.processEvents()


# ------------------------------------------------------------------ the reported flow, end to end
def test_a_place_delete_of_an_earlier_row_does_not_misroute_the_pending_form(win):
    """Edit gateway g1's form, click the Place tab, delete g0 on the art, navigate. The fold
    used to land on index 1 — now g2 — destroying g2 and doubling g1."""
    _mount(win)
    _type(win, "to", "555")
    win.tabs.setCurrentWidget(win.place_doc)
    pd = _arm_place(win)
    pd._on_region_deleted(_row(pd, "g0"))
    _navigate(win)
    assert _gateways(win) == [("g1", 555), ("g2", 102)]


def test_a_place_delete_of_the_mounted_row_leaves_the_others_alone(win):
    _mount(win)
    _type(win, "to", "555")
    win.tabs.setCurrentWidget(win.place_doc)
    pd = _arm_place(win)
    pd._on_region_deleted(_row(pd, "g1"))              # the row the form is editing
    _navigate(win)
    assert _gateways(win) == [("g0", 100), ("g2", 102)]


def test_a_place_reshape_is_not_written_back_by_the_mounted_form(win):
    """The form holds the row's OLD zone in a text box. With a pending edit elsewhere on the
    form, the fold wrote every field back — undoing the drag just made on the art."""
    _mount(win)
    _type(win, "to", "555")
    win.tabs.setCurrentWidget(win.place_doc)
    pd = _arm_place(win)
    pd._on_region_changed(_row(pd, "g1"), _NEW_QUAD)
    want = [[int(x), int(z)] for x, z in _NEW_QUAD]
    ctx = win._save_ctx                                # the form left mounted now SHOWS the drag
    assert forms.build_entity(ctx["spec"], read(ctx["getters"]))["zone"] == want
    _navigate(win)
    g1 = win._doc(_M).data["gateway"][1]
    assert (g1["name"], g1["to"], g1["zone"]) == ("g1", 555, want)


# ------------------------------------------------------------------ entering a doc tab commits
@pytest.mark.parametrize("tab", ["place_doc", "cutscene_doc", "behavior_doc"])
def test_showing_a_tab_that_edits_the_field_commits_the_pending_form(win, tab):
    """These three tabs mutate the SAME document the form is editing, so the form's pending
    values are folded in (one undo step) before any of them can change a row under it — and
    the form, still mounted, is then clean: it cannot write those values a second time over a
    later change made elsewhere."""
    _mount(win)
    _type(win, "to", "555")
    steps = len(win._undo_stack)
    win.tabs.setCurrentWidget(getattr(win, tab))
    assert win.tabs.currentWidget() is getattr(win, tab)
    assert _gateways(win)[1] == ("g1", 555) and len(win._undo_stack) == steps + 1
    win._doc(_M).data["gateway"][1]["to"] = 777        # the same row, changed out of band
    assert win._commit_active_ck()
    assert _gateways(win)[1] == ("g1", 777)


@pytest.mark.parametrize("tab", ["place_doc", "cutscene_doc", "behavior_doc"])
def test_a_bad_form_value_keeps_you_on_the_editor(win, tab):
    """A value that cannot be folded must not be silently dropped by a tab click: the tree's own
    rule (stay on the form, Problems says why) applies to these tabs too."""
    _mount(win)
    _type(win, "zone", "not a zone")
    with pytest.raises(ValueError):                    # the premise: this really does not parse
        forms.build_entity(win._save_ctx["spec"], read(win._save_ctx["getters"]))
    win.tabs.setCurrentWidget(getattr(win, tab))
    assert win.tabs.currentWidget() is win.doc_scroll
    assert _gateways(win) == [("g0", 100), ("g1", 101), ("g2", 102)]


# ------------------------------------------------------------------ identity, by ANY route
def test_the_fold_finds_its_row_by_identity_not_by_a_remembered_index(win):
    """The safety net under the two rules above: however a list moves under a mounted form, a
    fold can only ever write the row that form was mounted on."""
    _mount(win)
    _type(win, "to", "555")
    del win._doc(_M).data["gateway"][0]                # no hook, no tab change: the list just moved
    assert win._commit_active_ck()
    assert _gateways(win) == [("g1", 555), ("g2", 102)]


def test_a_form_whose_row_is_gone_writes_nowhere(win):
    _mount(win)
    _type(win, "to", "555")
    del win._doc(_M).data["gateway"][1]                # ITS row was removed; index 1 is now g2
    assert win._commit_active_ck()
    assert _gateways(win) == [("g0", 100), ("g2", 102)]


def test_the_forms_save_button_writes_its_own_row_after_the_list_moved(win):
    _mount(win)
    _type(win, "to", "555")
    del win._doc(_M).data["gateway"][0]
    win._save()
    disk = tomllib.loads(win.toml.read_text(encoding="utf-8"))
    assert [(g["name"], g["to"]) for g in disk["gateway"]] == [("g1", 555), ("g2", 102)]


def test_the_forms_delete_button_deletes_its_own_row_after_the_list_moved(win, monkeypatch):
    _mount(win)
    del win._doc(_M).data["gateway"][0]
    monkeypatch.setattr(win, "_confirm", lambda title, text: True)
    btn = next(b for b in win.doc_host.findChildren(QPushButton) if b.text() == "Delete Gateway")
    btn.click()
    assert _gateways(win) == [("g2", 102)]             # g1 — the row on screen — and only g1


def test_reset_restores_the_mounted_rows_own_saved_state(win):
    """Reset copies the row back from the last-saved document. After an unsaved delete of an
    earlier row the two lists no longer line up by index: it must find g1's OWN saved row."""
    _mount(win)
    data = win._doc(_M).data
    del data["gateway"][0]                             # unsaved: disk still has g0, g1, g2
    data["gateway"][0]["to"] = 999                     # ...and g1 itself was changed
    win._touch(_M)
    win._reset_active()
    assert _gateways(win) == [("g1", 101), ("g2", 102)]


# ------------------------------------------------------------------ the adversarial pass over the fix
def test_reset_of_a_renamed_row_restores_that_rows_own_saved_copy(win):
    """A row's NAME is one of the things Reset puts back. Matching a renamed row by its new name
    handed it the saved copy of whichever row used to carry that name."""
    data = win._doc(_M).data
    data["gateway"][1]["name"] = "g2"                  # g1 renamed onto g2's old name...
    data["gateway"][2]["name"] = "g3"                  # ...and g2 moved on (both unsaved)
    win._touch(_M)
    _mount(win, "gateway:1")
    win._reset_active()
    assert _gateways(win) == [("g0", 100), ("g1", 101), ("g3", 102)]


def test_reset_knows_its_row_after_a_delete_AND_a_rename(win):
    """Neither index nor name survives this: a row removed without a save shifts the index, and
    the row itself was renamed. The row OBJECT still says which saved row it was."""
    data = win._doc(_M).data
    del data["gateway"][0]
    data["gateway"][0]["name"] = "renamed"
    data["gateway"][0]["to"] = 999
    win._touch(_M)
    _mount(win, "gateway:0")
    win._reset_active()
    assert _gateways(win) == [("g1", 101), ("g2", 102)]


def test_reset_after_a_place_delete_and_a_place_draw_restores_the_right_row(win):
    """Delete one row and draw another in Place: the list is the same LENGTH as the saved one
    again, but shifted. An index check that trusts equal lengths pastes a deleted row's values
    over the row being edited (the second adversarial pass's catch on the first follow-up)."""
    from ff9mapkit.workspace import placedoc
    data = win._doc(_M).data
    placedoc.delete_region(data, "gateway", 0)         # g0 gone ...
    placedoc.place_gateway(data, [(0, 0), (9, 0), (9, 9), (0, 9)], 4005)   # ... and a new door0 drawn
    data["gateway"][0]["to"] = 999                     # g1, now at index 0, was edited
    win._touch(_M)
    assert [g["name"] for g in data["gateway"]] == ["g1", "g2", "door0"]
    _mount(win, "gateway:0")
    win._reset_active()
    assert _gateways(win) == [("g1", 101), ("g2", 102), ("door0", 4005)]


def test_reset_of_a_row_added_since_the_save_says_so_and_changes_nothing(win, monkeypatch):
    """A new row has no saved copy -- not even when its minted name was once another row's."""
    from ff9mapkit.workspace import placedoc
    data = win._doc(_M).data
    data["gateway"][0]["name"] = "door0"               # (saved under this name on disk next:)
    win._save_all()
    placedoc.delete_region(data, "gateway", 0)         # the saved door0 is deleted ...
    placedoc.place_gateway(data, [(0, 0), (9, 0), (9, 9), (0, 9)], 4005)   # ... and Place mints door0 anew
    win._touch(_M)
    assert [g["name"] for g in data["gateway"]] == ["g1", "g2", "door0"]
    _mount(win, "gateway:2")
    said = []
    monkeypatch.setattr(win, "_show_problems", lambda verdict, problems: said.append(verdict))
    win._reset_active()
    assert _gateways(win)[2] == ("door0", 4005)        # NOT the deleted door0's saved target (100)
    assert said and "Nothing to reset" in said[0].headline


def test_reset_after_an_undo_falls_back_to_an_unambiguous_name_or_says_so(win, monkeypatch):
    """An undo swaps in a fresh copy of the whole document: no row object survives it. Then only
    a name unique on both sides identifies a row; a duplicated one does not, and Reset says so."""
    data = win._doc(_M).data
    data["gateway"][1]["to"] = 555
    win._on_place_edit(_M, "an edit")                  # one undoable step ...
    data = win._doc(_M).data
    data["gateway"][1]["to"] = 556
    win._on_place_edit(_M, "another")
    win._undo()                                        # ... and an undo: every row is a new object
    data = win._doc(_M).data
    assert _M not in win._clean_rows and data["gateway"][1]["to"] == 555
    _mount(win, "gateway:1")
    win._reset_active()
    assert _gateways(win)[1] == ("g1", 101)            # "g1" is unique on both sides
    data = win._doc(_M).data
    data["gateway"][2]["name"] = "g1"                  # now two live rows share the name
    data["gateway"][2]["to"] = 777
    win._touch(_M)
    win._clean_rows.pop(_M, None)                      # (as after another undo)
    _mount(win, "gateway:2")
    said = []
    monkeypatch.setattr(win, "_show_problems", lambda verdict, problems: said.append(verdict))
    win._reset_active()
    assert _gateways(win)[2] == ("g1", 777) and said and "Nothing to reset" in said[0].headline


def test_reset_on_a_row_that_is_gone_says_so(win, monkeypatch):
    _mount(win)
    del win._doc(_M).data["gateway"][1]
    said = []
    monkeypatch.setattr(win, "_show_problems", lambda verdict, problems: said.append(verdict))
    win._reset_active()
    assert _gateways(win) == [("g0", 100), ("g2", 102)]
    assert [v.headline for v in said] == ["This Gateway no longer exists"]


def test_save_and_delete_on_a_row_that_is_gone_touch_nothing(win, monkeypatch):
    """The form's row was removed under it: index 1 is now ANOTHER gateway. Its buttons must not
    fall back to that index."""
    _mount(win)
    _type(win, "to", "555")
    del win._doc(_M).data["gateway"][1]
    monkeypatch.setattr(win, "_confirm", lambda title, text: True)
    said = []
    monkeypatch.setattr(win, "_show_problems", lambda verdict, problems: said.append(verdict))
    win._save()
    next(b for b in win.doc_host.findChildren(QPushButton) if b.text() == "Delete Gateway").click()
    assert _gateways(win) == [("g0", 100), ("g2", 102)]
    assert [v.headline for v in said] == ["This Gateway no longer exists"] * 2
    disk = tomllib.loads(win.toml.read_text(encoding="utf-8"))
    assert len(disk["gateway"]) == 3                   # and nothing was written


def test_identity_tells_two_rows_with_equal_contents_apart(win):
    """Found by ``is``, never by ``==``: two rows may hold exactly the same values."""
    data = win._doc(_M).data
    data["gateway"][2] = dict(data["gateway"][1])      # g2 is now a twin of g1, a distinct object
    _mount(win, "gateway:2")
    _type(win, "to", "555")
    assert win._commit_active_ck()
    assert [g["to"] for g in data["gateway"]] == [100, 101, 555]   # the SECOND twin, not the first


def test_a_row_that_moved_takes_its_key_header_and_tree_row_with_it(win):
    _select(win)                                       # gateway:1 -- "g1", selected in the tree
    win.tabs.setCurrentWidget(win.place_doc)
    pd = _arm_place(win)
    pd._on_region_deleted(_row(pd, "g0"))
    ctx = win._save_ctx
    assert (ctx["key"], ctx["idx"], ctx["mounted_key"]) == ("gateway:0", 0, "gateway:0")   # rebuilt
    assert ctx["row"] is win._doc(_M).data["gateway"][0]
    cur = win.tree.currentItem()
    assert cur is not None and win._payload(cur)[2] == "gateway:0"  # the tree is back on that row


def test_a_form_whose_row_was_deleted_on_the_art_is_replaced_and_the_tree_moves_on(win):
    _select(win)
    win.tabs.setCurrentWidget(win.place_doc)
    pd = _arm_place(win)
    pd._on_region_deleted(_row(pd, "g1"))
    assert win._save_ctx is None                       # no form left to write anything
    cur = win.tree.currentItem()
    assert cur is not None and win._payload(cur)[0] == "group"     # not a row that is gone


@pytest.mark.parametrize("hook", ["_on_behavior_edit", "_on_cutscene_edit"])
def test_the_behavior_and_cutscene_tabs_resync_the_form_too(win, hook):
    """Those tabs change the same document through their own ops; the form behind them must
    show what they wrote, or its next edit writes the old values back."""
    _mount(win)
    row = win._doc(_M).data["gateway"][1]
    row["to"] = 4242                                   # what such an op does: mutate, then call its hook
    getattr(win, hook)(_M, "an edit made in that tab")
    ctx = win._save_ctx
    assert forms.build_entity(ctx["spec"], read(ctx["getters"]))["to"] == 4242


def test_a_place_edit_leaves_a_selection_on_the_field_row_where_it_was(win):
    """The field's own row is not rebuilt by a Place edit, so a selection parked on it must not
    be moved onto its 'Field' child (same form, different row -- the snap diff caught the jump)."""
    mi = win._member_items[_M]
    win.tree.setCurrentItem(mi)                        # the Field form mounts for the member row
    win._on_select()
    assert win._save_ctx and win._save_ctx["key"] == "field"
    win.tabs.setCurrentWidget(win.place_doc)
    pd = _arm_place(win)
    pd._on_region_deleted(_row(pd, "g0"))
    assert win.tree.currentItem() is mi


def test_a_place_drop_updates_the_inspector_contents_beside_the_tree(win):
    """Review finding P30. A Place drop rebuilt the tree's rows ('Props (1)') but never re-ran
    the Inspector, so CONTENTS on the same screen kept the old tally until the next selection."""
    mi = win._member_items[_M]
    win.tree.setCurrentItem(mi)
    win._on_select()
    assert "3 gateways" in win.insp_body.text() and "prop" not in win.insp_body.text()
    win.tabs.setCurrentWidget(win.place_doc)
    pd = _arm_place(win)
    pd.mode_btns["prop"].setChecked(True)
    pd._apply_hit({"xz": (0.0, 1500.0), "floor": 0})   # the drop the canvas click lands
    assert "1 prop" in win.insp_body.text(), win.insp_body.text()
    pd._on_region_deleted(_row(pd, "g0"))
    assert "2 gateways" in win.insp_body.text(), win.insp_body.text()
    # ...and by Ctrl+Z / Ctrl+Y (review of P30): undo lands through _apply_history ->
    # _goto_focus('place'), which with the field row already current only re-feeds Place
    win._undo()
    assert "3 gateways" in win.insp_body.text(), win.insp_body.text()
    win._undo()
    assert "prop" not in win.insp_body.text(), win.insp_body.text()
    win._redo()
    assert "1 prop" in win.insp_body.text(), win.insp_body.text()
