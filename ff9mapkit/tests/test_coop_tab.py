"""Round-9 fences: the Co-op tab, and the bare-transparent container trap it re-exposed.

No fence here compares a text-derived width TO A CONSTANT -- offscreen stubs the font DB, so absolute
widths are fiction. Colour and counts are safe; and the kv fence compares two readings of the SAME
metrics (a relationship both sides take from the stub), which is the one width shape that survives
offscreen (studies/gui-aesthetics/STATE.md).
"""

import os

import pytest

pytest.importorskip("PySide6", reason="GUI extra not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")

from collections import Counter                                                # noqa: E402

from PySide6.QtWidgets import QApplication, QPushButton, QWidget               # noqa: E402

from ff9mapkit.editor import theme                                             # noqa: E402
from ff9mapkit.workspace import style, widgets                                 # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _settle(app, n=4):
    for _ in range(n):
        app.processEvents()


def _dominant(img):
    counts = Counter()
    for x in range(3, img.width() - 3, 2):
        for y in range(3, img.height() - 3, 2):
            counts[img.pixelColor(x, y).name()] += 1
    return counts.most_common(1)[0][0]


def test_a_page_column_never_unfills_the_buttons(app):
    """THE BARE-TRANSPARENT TRAP, fenced at the PIXEL it costs.

    page_column shipped `setStyleSheet("background: transparent;")` -- a bare property list, i.e. an
    implicit universal selector -- and a widget sheet beats the app sheet regardless of specificity, so
    every button on all three form docs lost its `background` for two rounds. Default buttons stayed
    readable ($text ink on the dark page); the ACCENT tier's dark accent_fg ink went invisible -- the
    round-9 co-op snaps caught 'Start co-op' rendering as an empty box.

    So: an accent button inside a page column must RENDER the accent fill. Rendered, not read from the
    palette -- `w.palette()` reports the ink Qt resolved, but the fill loss happens in the cascade and
    only a pixel shows it. This fence goes red on the bare form and green on widgets.TRANSPARENT.
    """
    pal = theme.derive(dict(theme.THEMES["mist"]))
    host = QWidget()
    host.setStyleSheet(style.qss(pal, "comfortable", 100))
    col = widgets.page_column(host)
    btn = QPushButton("Start co-op")
    btn.setObjectName("accent")
    col.addWidget(btn)
    host.resize(640, 240)
    host.show()
    _settle(app)
    fill = _dominant(btn.grab().toImage())
    assert fill.lower() == pal["accent"].lower(), (
        f"an accent button inside page_column renders {fill}, not the accent {pal['accent']} -- "
        "the bare-transparent container trap is back (see widgets.TRANSPARENT)"
    )


def test_no_bare_background_sheet_on_any_widget(app, monkeypatch, tmp_path):
    """The trap's census, on the REAL shell: a property-only stylesheet (no selector -- nothing before
    a '{') silently out-ranks the app sheet. On a CONTAINER it strips every descendant's fill (the
    page_column regression); on a LEAF it still kills the widget's OWN app-sheet state rules -- the
    first cut exempted childless widgets and the review caught the half-fence. The fix is always a
    selector form: widgets.TRANSPARENT for containers, `Class#objectName { ... }` for a leaf's
    deliberate per-widget styling."""
    from ff9mapkit import prefs
    from ff9mapkit.workspace import shell as S
    monkeypatch.setattr(prefs, "_path", lambda: tmp_path / "prefs.json")   # close() writes layout
    pal = S.pick_palette("dark")
    win = S.Workspace(pal)
    try:
        bad = []
        for w in win.findChildren(QWidget):
            ss = w.styleSheet()
            if ss and "{" not in ss and "background" in ss:
                bad.append(f"{type(w).__name__}#{w.objectName() or '-'}: {ss[:60]!r}")
        assert not bad, (
            "bare property-only background sheets (they out-rank the app sheet -- on a container they "
            f"unfill every descendant; on a leaf they kill its own state rules): {bad}"
        )
    finally:
        win.close()
        win.deleteLater()
        _settle(app)


@pytest.fixture(scope="module")
def coop(app, tmp_path_factory):
    """One Workspace per module; tests read its coop_doc.

    THE FIXTURE PINS ITS OWN PREFS, at MODULE scope. conftest's autouse ``_isolate_prefs`` is
    FUNCTION-scoped, and pytest builds higher-scoped fixtures first and tears them down last -- so a
    module fixture's construction reads the developer's REAL prefs.json and, worse, its teardown
    ``win.close()`` runs closeEvent -> ``_save_layout`` AFTER the last test's isolation unwound,
    overwriting the developer's real layout with a never-shown offscreen window's squeeze fossil
    ([70, 494, 68] -- round 7's own disease, re-shipped by this file's first cut; the round-9
    adversarial review proved it end-to-end). The pin below covers both ends of the fixture's life."""
    from _pytest.monkeypatch import MonkeyPatch

    from ff9mapkit import config as cfg, prefs
    from ff9mapkit.workspace import shell as S
    mp = MonkeyPatch()
    store = tmp_path_factory.mktemp("coop_fixture_prefs")
    mp.setattr(prefs, "_path", lambda: store / "prefs.json")
    # ...and the GAME: construction runs refresh_status, which would read the developer's real install
    # (and paint their real [Netsync] SessionCode into the code field). Raise -- the REAL no-game
    # failure mode (find_game_path raises ConfigError; it never returns None) -- so every test starts
    # from a deterministic nogame state and re-pins what it needs.
    mp.setattr(cfg, "find_game_path",
               lambda *_a, **_k: (_ for _ in ()).throw(cfg.ConfigError("pinned: no game")))
    win = S.Workspace(S.pick_palette("dark"))
    yield win.coop_doc
    win.close()
    win.deleteLater()
    _settle(app)
    mp.undo()


def test_the_ghost_combo_items_fit_its_closed_box(coop):
    """AdjustToMinimumContentsLengthWithIcon makes the closed box's sizeHint exactly
    minimumContentsLength characters -- and the trailing stretch hands it nothing more, so any LONGER
    item HARD-CLIPS when selected (no ellipsis; the round-9 snap read 'Their own model (classic gl').
    The law: every item fits the length the box asks for. Pure character arithmetic, platform-proof."""
    combo = coop.combo_ghost
    mcl = combo.minimumContentsLength()
    over = [combo.itemText(i) for i in range(combo.count()) if len(combo.itemText(i)) > mcl]
    assert not over, f"combo items longer than minimumContentsLength({mcl}): {over}"
    # ...and the OTHER half, which the first cut missed and the review measured: a setMaximumWidth px
    # cap is deaf to the text dial, and at 150% it clamped the box BELOW its own character-based
    # sizeHint -- re-creating the clip with this fence green. The character law above only holds while
    # no px cap can bind, i.e. while the box's maximum is effectively unbounded.
    assert combo.maximumWidth() >= 16777215, (
        f"a px maximumWidth ({combo.maximumWidth()}) caps the combo below its font-based hint at high "
        "text scales -- the hard clip returns while the character fence stays green")


def test_the_kv_key_column_tracks_its_own_font(coop, app):
    """The Status keys clipped at a 150% dial ("gameC:", "enginnetsync") because the column was a px
    measured from the CONSTRUCTION-time font, before the QSS landed, and never again. The law: a width
    computed from a font is recomputed on FontChange, by the widget wearing the font. Both halves:
    the RELATIONSHIP (width == its own current metrics, not some earlier font's), and the no-op check
    (a real font change MOVES the width -- a frozen column passes any single-font assert)."""
    key = coop.lbl_game.key_label

    def expected():
        return round(key.fontMetrics().horizontalAdvance("engine")) + type(key)._PAD

    assert key.width() == expected(), "the key column is not a function of the key label's OWN font"
    before = key.width()
    # The lever is the DIAL, not setFont: the QSS base rule re-resolves fonts, so a programmatic
    # setFont on a styled widget is silently overridden (measured: width 98 == 98) -- a lever that
    # cannot move the font cannot falsify the frozen column. CALIBRE can.
    win = coop.window()
    try:
        win._apply_text_scale(150)
        _settle(app)
        assert key.width() == expected(), "after the dial moves the column must re-measure"
        assert key.width() > before, ("the dial reached 150% and the key column never widened -- "
                                      "FontChange is not wired (the frozen-px clip is back)")
    finally:
        win._apply_text_scale(100)
        _settle(app)


def test_the_status_warning_carries_its_own_door(coop, app, monkeypatch, tmp_path):
    """'Run Setup & health… first' without a way to run it is a scavenger hunt. The Setup button shows
    exactly while the status needs it: game missing -> shown; engine without netsync -> shown; healthy
    s40 machine -> hidden. Both directions pinned via a fake install (never this machine's state)."""
    from ff9mapkit import config as cfg

    # The REAL no-game failure mode: find_game_path RAISES ConfigError (config.py:178/206 -- it never
    # returns None). The first cut pinned a return of None, a branch no real machine can reach.
    monkeypatch.setattr(cfg, "find_game_path",
                        lambda *_a, **_k: (_ for _ in ()).throw(cfg.ConfigError("no game")))
    coop.refresh_status()
    assert coop.btn_setup.isVisibleTo(coop), "no game found -> the Setup door must show"
    assert not coop.btn_start.isEnabled()

    game = tmp_path / "game"
    managed = game / "x64" / "FF9_Data" / "Managed"
    managed.mkdir(parents=True)
    (managed / "Assembly-CSharp.dll").write_bytes(b"MZ stock engine, no netsync")
    (game / "Memoria.ini").write_text("[Netsync]\nEnabled = 0\n", encoding="utf-8")
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)
    coop.refresh_status()
    assert coop.btn_setup.isVisibleTo(coop), "stock engine (no netsync) -> the Setup door must show"

    # s36: netsync present but the Play-style lanes need s37 -- the row warns and NAMES the newer
    # engine, so the door must show too (the warn/door predicates diverging was a review finding: the
    # scavenger hunt came back for exactly one engine generation).
    (managed / "Assembly-CSharp.dll").write_bytes(b"MZ NetSyncClient only")
    coop.refresh_status()
    assert coop.btn_setup.isVisibleTo(coop), "s36 engine (warned to upgrade) -> the door must show"

    (managed / "Assembly-CSharp.dll").write_bytes(b"MZ NetSyncClient NetSyncBattle NetSyncDiorama")
    coop.refresh_status()
    assert not coop.btn_setup.isVisibleTo(coop), "healthy s40 machine -> the door must GO AWAY"
    assert coop.btn_start.isEnabled()


def test_advanced_drawer_comes_back_for_a_non_default_play_style(coop, app):
    """THE COMES-BACK RULE. The Play-style card is folded into a collapsed Advanced drawer -- but a knob
    that was configured on this machine must not hide from the person who set it. _load_playstyle re-opens
    the drawer whenever the ini carries a non-default GuestSlots / GhostAs / FollowHost, and only then.

    Both directions are the law: a default ini leaves a collapsed drawer collapsed (so an 'always expand'
    implementation fails the first half), and each non-default key ALONE re-opens it (so a no-op auto-expand
    fails the second half). Reads only the passed ini text -- no game, no prefs."""
    drawer = coop.style_drawer

    def loads_open(ini):
        drawer.toggle_button.setChecked(False)      # start collapsed -- the rule only ever opens
        coop._load_playstyle(ini)
        _settle(app)
        return drawer.toggle_button.isChecked()

    try:
        assert not loads_open("[Netsync]\n"), "an all-default ini must leave the drawer collapsed"
        assert not loads_open(
            "[Netsync]\nGuestSlots = 0\nGhostAs = off\nFollowHost = 0\nGuestWaitMs = 30000\n"
        ), "explicit-default values must still leave it collapsed"
        # Wait / diorama are NOT signals (both have non-empty engine defaults) -- a non-default wait alone
        # must not trip the rule.
        assert not loads_open("[Netsync]\nGuestWaitMs = 5000\nDiorama = 0\n"), (
            "wait/diorama are not comes-back signals -- they must not open the drawer")
        # Each real signal, alone, re-opens it.
        assert loads_open("[Netsync]\nGuestSlots = 1\n"), "a granted battle slot must re-open the drawer"
        assert loads_open("[Netsync]\nGhostAs = vivi\n"), "a visitor outfit must re-open the drawer"
        assert loads_open("[Netsync]\nFollowHost = 1\n"), "follow-host must re-open the drawer"
    finally:
        drawer.toggle_button.setChecked(False)
        coop._load_playstyle("[Netsync]\n")         # leave the shared doc at its default state
        _settle(app)


def test_host_start_survives_an_unusable_stored_session_code(coop, app, monkeypatch, tmp_path):
    """`coop host` deliberately treats a stored SessionCode it cannot vouch for as ABSENT and mints a
    fresh one. The tab has to match: refresh_status SEEDS the code field from the ini, and in Host mode
    that field is read-only -- so a value the user never typed dead-ended Start with no way to clear it.
    Hosting drops the bad code (the subprocess mints one); JOINING still refuses, because there the code
    IS the user's paste and silently replacing it would pair them with the wrong session."""
    from ff9mapkit import config as cfg

    game = tmp_path / "game"
    game.mkdir()
    (game / "Memoria.ini").write_text("[Netsync]\nEnabled = 1\nSessionCode = my session\n",
                                      encoding="utf-8")
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)
    coop.rb_host.setChecked(True)
    coop.code.clear()
    coop.refresh_status()
    assert coop.code.text() == "my session", "precondition: the ini's value is seeded into the field"

    seen = []
    monkeypatch.setattr(coop, "_run", lambda argv, **kw: seen.append(argv) or True)
    coop.rb_relay.setChecked(True)                  # the LAN branch bails earlier, on its own message
    try:
        coop.start_coop()
        assert seen, "Host Start bailed on a code that came from the ini, not from the user"
        assert "my session" not in seen[0], "the unusable stored code was still passed to the CLI"
        assert coop.lbl_config.property("state") != "warn"

        # ...and the flip side: a guest's own bad paste must still be refused before any subprocess,
        # because THERE the code is the user's paste -- the ini-splice fence stays hard on that path
        seen.clear()
        coop.rb_join.setChecked(True)
        coop.code.setText("ff9-AAAA0000\nGuestSlots = 15")
        coop.start_coop()
        assert not seen, "a poisoned paste must not reach the CLI on the join path"
        assert coop.lbl_config.property("state") == "warn"
    finally:
        coop.rb_host.setChecked(True)
        coop.code.clear()
        widgets.set_state(coop.lbl_config, "")
