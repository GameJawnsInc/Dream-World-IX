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

    THE FIXTURE PINS ITS OWN PREFS, at MODULE scope. The root conftest's autouse ``_isolate_user_config`` is
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


def test_the_ghost_combo_offers_every_ghost_name_the_kit_writes(coop):
    """[ff9mapkit netsync s139] The combo's data values ARE {'' (their own model), 'auto'} plus coop.GHOST_NAMES with the
    engine's aliases folded (garnet -> dagger, salamander -> amarant): a name the kit accepts (`ff9mapkit coop --ghost-as
    moogle`) but the combo lacks loads as index 0, and the next apply silently rewrites the user's GhostAs to 'off'."""
    from ff9mapkit import coop as kit
    combo = coop.combo_ghost
    data = [combo.itemData(i) for i in range(combo.count())]
    folded = {"garnet": "dagger", "salamander": "amarant"}
    assert len(data) == len(set(data)), data
    assert set(data) == {"", "auto"} | {folded.get(n, n) for n in kit.GHOST_NAMES}, data
    assert "moogle" in data
    assert {"cinna", "marcus", "blank", "beatrix"} <= set(data)     # [ff9mapkit netsync s140] rig rows 9-12


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
    exactly while the status needs it: game missing -> shown; engine without netsync or older than
    the current generation -> shown; current machine -> hidden. Both directions pinned via a fake install (never this machine's state)."""
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

    # an older-but-playable engine (s40) still reads amber and still shows the door: both players
    # should run the current bundle, and Setup & health is where it installs
    (managed / "Assembly-CSharp.dll").write_bytes(b"MZ NetSyncClient NetSyncBattle NetSyncDiorama")
    coop.refresh_status()
    assert coop.btn_setup.isVisibleTo(coop), "outdated s40 engine (amber) -> the door must show"
    assert coop.host_box.isEnabled(), "s37+ keeps the host's battle settings usable"

    from ff9mapkit import health
    (managed / "Assembly-CSharp.dll").write_bytes(
        b"MZ " + b" ".join(g[1] for g in health.NETSYNC_GENERATIONS))
    coop.refresh_status()
    assert not coop.btn_setup.isVisibleTo(coop), "current engine -> the door must GO AWAY"
    assert coop.btn_start.isEnabled()


def test_the_engine_row_reads_the_shared_health_source(coop, app, monkeypatch, tmp_path):
    """One source of truth: the Status card's `engine` line is now health.netsync_generation's summary
    verbatim, the SAME derivation Setup's 'Co-op engine' health row reads. Written a known s37 DLL, the
    card's text must EQUAL the helper's -- a coopdoc that reworded the sentence (two copies again) fails
    this, and the level must track (ok on the current generation, warn below)."""
    from ff9mapkit import config as cfg, health

    game = tmp_path / "game"
    managed = game / "x64" / "FF9_Data" / "Managed"
    managed.mkdir(parents=True)
    (game / "Memoria.ini").write_text("[Netsync]\nEnabled = 0\n", encoding="utf-8")
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)

    (managed / "Assembly-CSharp.dll").write_bytes(
        b"MZ " + b" ".join(g[1] for g in health.NETSYNC_GENERATIONS))                 # current
    coop.refresh_status()
    gen = health.netsync_generation(game)
    assert coop.lbl_engine.text() == gen["summary"], "the card's engine line must be the shared summary"
    assert gen["level"] == "ok" and coop.lbl_engine.property("state") != "warn"

    (managed / "Assembly-CSharp.dll").write_bytes(b"MZ NetSyncClient")                 # s36 -> warn
    coop.refresh_status()
    gen = health.netsync_generation(game)
    assert coop.lbl_engine.text() == gen["summary"]
    assert gen["level"] == "warn" and coop.lbl_engine.property("state") == "warn"


def test_each_side_sees_only_its_own_settings(coop, app):
    """THE ROLE LAW, visible half. The first Co-op tab showed one shared play-style card to both sides, and a
    host could tick 'follow the host' -- which in the b20 smoke test sent host and guest chasing each other
    between two fields. Now the host sees its battle settings and no follow control at all; the guest sees
    no knobs, only what following means. Both directions: a page that shows both cards fails the first
    half, a page that never swaps fails the second."""
    try:
        coop.rb_host.setChecked(True)
        _settle(app)
        assert coop.host_box.isVisibleTo(coop) and not coop.guest_box.isVisibleTo(coop)
        assert coop.btn_start.text() == "Start hosting"
        coop.rb_join.setChecked(True)
        _settle(app)
        assert coop.guest_box.isVisibleTo(coop) and not coop.host_box.isVisibleTo(coop)
        assert coop.btn_start.text() == "Join game"
        assert not hasattr(coop, "cb_follow"), "following is the guest's role, not a checkbox either side can tick"
    finally:
        coop.rb_host.setChecked(True)
        coop._paste = ""                # [ff9mapkit s154] the module-scoped doc's stashed paste must not leak
        _settle(app)


def test_join_always_follows_and_the_host_never_does(coop, app, monkeypatch, tmp_path):
    """THE ROLE LAW, written half: what Start actually hands the CLI. Join passes --follow-host on and
    --ghost-as off (a guest-side outfit only re-dresses its view of the host); Host passes --follow-host off
    and its battle settings. Read from the argv the subprocess would get -- not from a widget."""
    from ff9mapkit import config as cfg
    from ff9mapkit.editor import jobs as J

    game = tmp_path / "game"
    managed = game / "x64" / "FF9_Data" / "Managed"
    managed.mkdir(parents=True)
    from ff9mapkit import health
    (managed / "Assembly-CSharp.dll").write_bytes(b"MZ " + b" ".join(g[1] for g in health.NETSYNC_GENERATIONS))
    (game / "Memoria.ini").write_text("[Netsync]\nEnabled = 0\n", encoding="utf-8")
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)
    seen = []
    monkeypatch.setattr(coop, "_run", lambda argv, **kw: seen.append(argv) or True)

    def flag(argv, name):
        return argv[argv.index(name) + 1] if name in argv else None
    try:
        coop.refresh_status()
        coop.rb_relay.setChecked(True)
        coop.rb_host.setChecked(True)
        for i, cb in enumerate(coop.cb_slots):
            cb.setChecked(i == 2)
        coop.start_coop()
        host = seen[-1]
        assert J.coop_setup_argv("host")[:5] == host[:5]
        assert flag(host, "--follow-host") == "off" and flag(host, "--guest-slots") == "3"

        coop.rb_join.setChecked(True)
        coop.code.setText("ff9-ABCD1234")
        coop.start_coop()
        join = seen[-1]
        assert flag(join, "--follow-host") == "on" and flag(join, "--ghost-as") == "off"
        assert "--guest-slots" not in join, "a guest has no battle settings to write"

        # Apply on the host side writes FollowHost = 0 next to the battle keys, never 1
        coop.rb_host.setChecked(True)
        coop.apply_playstyle()
        from ff9mapkit import coop as kit
        text = (game / "Memoria.ini").read_text(encoding="utf-8")
        assert kit.read_ini_key(text, "Netsync", "FollowHost") == "0"
        assert kit.read_ini_key(text, "Netsync", "GuestSlots") == "4"
    finally:
        coop.rb_host.setChecked(True)
        coop.code.clear()
        coop._paste = ""                # [ff9mapkit s154] the join paste above was stashed by the flip back to Host
        widgets.set_state(coop.lbl_session, "")


def test_a_live_session_shows_this_pcs_real_role(coop, app, monkeypatch, tmp_path):
    """A guest PC opening the tab must not find 'Host' selected: an enabled [Netsync] sets the role and the
    transport from the ini, and seeds the code the guest joined with. A switched-off ini leaves the user's
    own picks alone (otherwise every Refresh would undo a choice they had not started yet)."""
    from ff9mapkit import config as cfg

    game = tmp_path / "game"
    game.mkdir()
    ini = game / "Memoria.ini"
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)
    try:
        coop.rb_host.setChecked(True)
        coop.code.clear()
        ini.write_text("[Netsync]\nEnabled = 1\nRole = client\nSessionCode = ff9-ABCD1234\n"
                       "RelayUrl = ws://127.0.0.1:49201\n", encoding="utf-8")
        coop.refresh_status()
        assert coop.rb_join.isChecked() and coop.rb_relay.isChecked()
        assert coop.code.text() == "ff9-ABCD1234"
        assert "guest" in coop.lbl_session.text()

        coop.rb_host.setChecked(True)                 # the user's own pick, co-op switched off
        ini.write_text("[Netsync]\nEnabled = 0\nRole = client\n", encoding="utf-8")
        coop.refresh_status()
        assert coop.rb_host.isChecked(), "a switched-off ini must not flip the user's pick"
    finally:
        coop.rb_host.setChecked(True)
        coop.code.clear()
        coop._paste = ""                # [ff9mapkit s154] the live guest's code was stashed by the flip back to Host


def test_host_start_survives_an_unusable_stored_session_code(coop, app, monkeypatch, tmp_path):
    """`coop host` deliberately treats a stored SessionCode it cannot vouch for as ABSENT and mints a
    fresh one. The tab has to match: in Host mode the code field is read-only -- so a value the user never
    typed must never dead-end Start with no way to clear it. [ff9mapkit s154] The Host field now shows only
    this PC's OWN code (coop.own_host_code: a no-Role SessionCode is nobody's), so the unusable value is not
    even seeded, and a host never forwards the field; JOINING still refuses a bad paste, because there the
    code IS the user's paste and silently replacing it would pair them with the wrong session."""
    from ff9mapkit import config as cfg

    game = tmp_path / "game"
    game.mkdir()
    (game / "Memoria.ini").write_text("[Netsync]\nEnabled = 1\nSessionCode = my session\n",
                                      encoding="utf-8")
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)
    coop.rb_host.setChecked(True)
    coop.code.clear()
    coop.refresh_status()
    assert coop.code.text() == "", "precondition: a value no host wrote is not seeded into the Host field"

    seen = []
    monkeypatch.setattr(coop, "_run", lambda argv, **kw: seen.append(argv) or True)
    coop.rb_relay.setChecked(True)                  # the LAN branch bails earlier, on its own message
    try:
        coop.start_coop()
        assert seen, "Host Start bailed on a code that came from the ini, not from the user"
        assert "my session" not in seen[0], "the unusable stored code was still passed to the CLI"
        assert coop.lbl_session.property("state") != "warn"

        # ...and the flip side: a guest's own bad paste must still be refused before any subprocess,
        # because THERE the code is the user's paste -- the ini-splice fence stays hard on that path
        seen.clear()
        coop.rb_join.setChecked(True)
        coop.code.setText("ff9-AAAA0000\nGuestSlots = 15")
        coop.start_coop()
        assert not seen, "a poisoned paste must not reach the CLI on the join path"
        assert coop.lbl_session.property("state") == "warn"
    finally:
        coop.rb_host.setChecked(True)
        coop.code.clear()
        coop._paste = ""                # [ff9mapkit s154] the poisoned paste was stashed by the flip back to Host
        widgets.set_state(coop.lbl_session, "")


# ------------------------------------------------- THE OWN-CODE LAW (s154): the Host field is never a joined code
#
# s153's tab seeded the read-only Host field from [Netsync] SessionCode -- after a `coop join` that is the FRIEND's code --
# and Start forwarded the field as an EXPLICIT `coop host <code>`: a switched-off guest (the radios default to Host) or a
# live guest flipping to Host hosted on its friend's invite (studies/coop-review/REVIEW.md appendix 25).

def _game_with(tmp_path, ini_text):
    from ff9mapkit import health
    game = tmp_path / "game"
    managed = game / "x64" / "FF9_Data" / "Managed"
    managed.mkdir(parents=True)
    (managed / "Assembly-CSharp.dll").write_bytes(b"MZ " + b" ".join(g[1] for g in health.NETSYNC_GENERATIONS))
    (game / "Memoria.ini").write_text(ini_text, encoding="utf-8")
    return game


def _positional_code(argv):
    """The code `coop host|join` would get from this argv (the token right after the action), or None."""
    from ff9mapkit.editor import jobs as J
    head = len(J.coop_setup_argv("host"))  # [python, -m, ff9mapkit, coop, host, --no-bridge]
    nxt = argv[head - 1] if len(argv) >= head else None
    return None if nxt is None or nxt.startswith("--") else nxt


def _reset(coop):
    coop.rb_relay.setChecked(True)
    coop.rb_host.setChecked(True)
    coop.code.clear()
    coop._paste = ""
    widgets.set_state(coop.lbl_session, "")


def test_the_host_field_never_shows_a_joined_code(coop, app, monkeypatch, tmp_path):
    from ff9mapkit import config as cfg
    game = _game_with(tmp_path, "[Netsync]\nEnabled = 1\nRole = client\nSessionCode = ff9-ABCD1234\n"
                                "RelayUrl = ws://127.0.0.1:49201\n")
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)
    seen = []
    monkeypatch.setattr(coop, "_run", lambda argv, **kw: seen.append(argv) or True)
    try:
        _reset(coop)
        coop.refresh_status()
        assert coop.rb_join.isChecked() and coop.code.text() == "ff9-ABCD1234", "a live guest shows the code it joined"
        coop.rb_host.setChecked(True)                        # the guest PC decides to host instead
        _settle(app)
        assert coop.code.text() != "ff9-ABCD1234", "the Host field shows the friend's code as this PC's own"
        assert coop.code.isReadOnly()
        coop.start_coop()
        assert seen and "ff9-ABCD1234" not in seen[-1], f"Start hosting forwarded the joined code: {seen[-1]}"
        assert _positional_code(seen[-1]) is None, seen[-1]
        coop.rb_join.setChecked(True)                        # ...and back: the guest's code is still theirs
        _settle(app)
        assert coop.code.text() == "ff9-ABCD1234" and not coop.code.isReadOnly()
    finally:
        _reset(coop)


def test_a_switched_off_guest_ini_seeds_no_host_code(coop, app, monkeypatch, tmp_path):
    from ff9mapkit import config as cfg
    game = _game_with(tmp_path, "[Netsync]\nEnabled = 0\nRole = client\nSessionCode = ff9-ABCD1234\n"
                                "RelayUrl = ws://127.0.0.1:49201\n")
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)
    seen = []
    monkeypatch.setattr(coop, "_run", lambda argv, **kw: seen.append(argv) or True)
    try:
        _reset(coop)
        coop.refresh_status()                                # "Turn co-op off" left the guest's Role and code
        assert coop.rb_host.isChecked(), "precondition: a switched-off ini leaves the default Host pick"
        assert coop.code.text() == "", "the Host field was seeded with the code this PC joined with"
        from ff9mapkit.workspace.coopdoc import HOST_CODE_PLACEHOLDER
        assert coop.code.placeholderText() == HOST_CODE_PLACEHOLDER
        # a code-width field: a placeholder longer than a code ELIDES (the first cut's 27-char one read "made when you
        # st..." in the snap) -- the code's own shape is the length budget (character arithmetic: platform-proof)
        assert len(HOST_CODE_PLACEHOLDER) <= len("ff9-XXXXXXXX"), HOST_CODE_PLACEHOLDER
        coop.start_coop()
        assert seen, "Start hosting bailed"
        assert seen[-1][4] == "host" and _positional_code(seen[-1]) is None, f"Start forwarded a code: {seen[-1]}"
    finally:
        _reset(coop)


def test_the_host_field_shows_this_pcs_own_code(coop, app, monkeypatch, tmp_path):
    from ff9mapkit import config as cfg
    game = _game_with(tmp_path, "[Netsync]\nEnabled = 0\nRole = client\nSessionCode = ff9-ABCD1234\n"
                                "HostSessionCode = ff9-MINE0001\nRelayUrl = ws://127.0.0.1:49201\n")
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)
    try:
        _reset(coop)
        coop.refresh_status()
        assert coop.code.text() == "ff9-MINE0001", "the Host field must show this PC's own code"
    finally:
        _reset(coop)


def test_a_live_host_shows_the_code_its_game_dials(coop, app, monkeypatch, tmp_path):
    """A LIVE host (Enabled=1, Role=host) shows and copies the code its game DIALS (SessionCode), which the guest must
    join -- not HostSessionCode. They part when the engine mints a code into an emptied SessionCode (it never writes
    HostSessionCode: the bridge README's own guest-to-host hand edit) or after a CLI `coop host <joined code>`; the first
    s154 cut showed the stale own code there while the row read 'ON, hosting', so Copy handed out a code nobody hosts on.
    Off, or not a host, the field goes back to the own code (what Start hosting uses)."""
    from ff9mapkit import config as cfg
    from ff9mapkit.workspace import coopdoc
    game = _game_with(tmp_path, "[Netsync]\nEnabled = 1\nRole = host\nSessionCode = ff9-ENGINEY1\n"
                                "HostSessionCode = ff9-OWNX0001\nRelayUrl = ws://127.0.0.1:49201\n")
    ini = game / "Memoria.ini"
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)
    seen = []
    monkeypatch.setattr(coop, "_run", lambda argv, **kw: seen.append(argv) or True)
    copied = []

    class _App:                                          # Copy's clipboard, without a Qt class patch
        @staticmethod
        def clipboard():
            return type("C", (), {"setText": staticmethod(copied.append)})()
    monkeypatch.setattr(coopdoc, "QApplication", _App)
    try:
        _reset(coop)
        coop.refresh_status()
        assert coop.rb_host.isChecked() and "hosting" in coop.lbl_session.text()
        assert coop.code.text() == "ff9-ENGINEY1", "a live host's field shows a code its game does not dial"
        coop._copy_code()                                      # the Copy button's own handler
        assert copied == ["ff9-ENGINEY1"], copied
        coop.rb_join.setChecked(True)                          # a flip away and back renders the same dialled code
        _settle(app)
        coop.rb_host.setChecked(True)
        _settle(app)
        assert coop.code.text() == "ff9-ENGINEY1", coop.code.text()
        coop.start_coop()
        assert seen and _positional_code(seen[-1]) is None, f"Start forwarded the field: {seen[-1]}"
        # an unusable dialled code is never shown (Copy would hand it out), and never falls back to the own code
        ini.write_text("[Netsync]\nEnabled = 1\nRole = host\nSessionCode = not a code!\n"
                       "HostSessionCode = ff9-OWNX0001\nRelayUrl = ws://127.0.0.1:49201\n", encoding="utf-8")
        coop.refresh_status()
        assert coop.code.text() == "", coop.code.text()
        # switched off: the field is the own code again, what a bare `coop host` (Start hosting) goes back to
        ini.write_text("[Netsync]\nEnabled = 0\nRole = host\nSessionCode = ff9-ENGINEY1\n"
                       "HostSessionCode = ff9-OWNX0001\nRelayUrl = ws://127.0.0.1:49201\n", encoding="utf-8")
        coop.refresh_status()
        assert coop.code.text() == "ff9-OWNX0001", coop.code.text()
        # an enabled ini with NO Role is not a live host (the engine's default role is selftest): its code is nobody's
        ini.write_text("[Netsync]\nEnabled = 1\nSessionCode = ff9-BENCH001\n", encoding="utf-8")
        coop.refresh_status()
        assert coop.code.text() == "", coop.code.text()
    finally:
        _reset(coop)


def test_start_hosting_after_the_cli_cure_keeps_the_fresh_code(coop, app, monkeypatch, tmp_path):
    """The two-hosts cure the bridge log and tutorial 17 name: `ff9mapkit coop host --new-code --no-bridge` in a terminal,
    then Start hosting again. Start (a bare `coop host`, end to end through the REAL kit) must keep the code the cure
    minted -- not go back to the old one -- and its done() must show and copy that code."""
    from ff9mapkit import cli, coop as kit, config as cfg
    from ff9mapkit.workspace import coopdoc
    game = _game_with(tmp_path, "[Netsync]\nEnabled = 1\nRole = host\nSessionCode = ff9-OLDCODE1\n"
                                "HostSessionCode = ff9-OLDCODE1\nRelayUrl = ws://127.0.0.1:49201\n")
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)
    monkeypatch.setattr(kit, "_copy_clipboard", lambda _t: False)          # never the developer's clipboard
    copied = []

    class _App:                                          # done()'s clipboard, without a Qt class patch
        @staticmethod
        def clipboard():
            return type("C", (), {"setText": staticmethod(copied.append)})()
    monkeypatch.setattr(coopdoc, "QApplication", _App)
    monkeypatch.setattr(coop, "start_bridge", lambda: None)                 # no real bridge thread
    said = []

    def kit_run(argv):
        return kit.run(cli.build_parser().parse_args(["--game", str(game), *argv]), out=said.append)

    def run_job(argv, **kw):
        kw["on_finished"](kit_run([*argv[3:], "--no-room"]))
        return True
    monkeypatch.setattr(coop, "_run", run_job)
    try:
        _reset(coop)
        coop.refresh_status()
        assert coop.code.text() == "ff9-OLDCODE1"
        assert kit_run(["coop", "host", "--new-code", "--no-bridge", "--no-room"]) == 0   # the terminal half of the cure
        fresh = kit.read_ini_key(kit.read_ini_text(game / "Memoria.ini"), "Netsync", "SessionCode")
        assert fresh and fresh != "ff9-OLDCODE1"
        coop.start_coop()                                                   # ...then Start hosting again
        ini = kit.read_ini_text(game / "Memoria.ini")
        assert kit.read_ini_key(ini, "Netsync", "SessionCode") == fresh, f"Start went back to the old code: {said}"
        assert kit.read_ini_key(ini, "Netsync", "HostSessionCode") == fresh
        assert coop.code.text() == fresh and copied == [fresh], (coop.code.text(), copied)
    finally:
        _reset(coop)


def test_a_paste_survives_a_flip_to_host_and_back(coop, app, monkeypatch, tmp_path):
    from ff9mapkit import config as cfg
    game = _game_with(tmp_path, "[Netsync]\nEnabled = 0\nRole = host\nHostSessionCode = ff9-MINE0001\n"
                                "SessionCode = ff9-MINE0001\n")
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)
    try:
        _reset(coop)
        coop.refresh_status()
        coop.rb_join.setChecked(True)
        _settle(app)
        assert coop.code.text() == "", "the Join field starts empty, never the host's own code"
        coop.code.setText("ff9-PASTE001")
        coop.rb_host.setChecked(True)
        _settle(app)
        assert coop.code.text() == "ff9-MINE0001", "Host shows the own code, not the guest's paste"
        coop.refresh_status()                                # a Refresh while Host is up keeps the paste aside
        coop.rb_join.setChecked(True)
        _settle(app)
        assert coop.code.text() == "ff9-PASTE001", "the guest's paste was lost by a flip to Host and back"
    finally:
        _reset(coop)


def test_start_hosting_on_a_former_guest_hosts_and_copies_its_own_code(coop, app, monkeypatch, tmp_path):
    """End to end through the REAL kit: the argv Start hands the subprocess is run in-process, then the job's done()
    -- the ini must host on a fresh own code, and the field and the clipboard must carry that code, never the friend's."""
    from ff9mapkit import cli, coop as kit, config as cfg
    from ff9mapkit.workspace import coopdoc
    game = _game_with(tmp_path, "[Netsync]\nEnabled = 0\nRole = client\nSessionCode = ff9-FRIEND01\n"
                                "RelayUrl = ws://127.0.0.1:49201\n")
    monkeypatch.setattr(cfg, "find_game_path", lambda *_a, **_k: game)
    monkeypatch.setattr(kit, "_copy_clipboard", lambda _t: False)          # never the developer's clipboard
    copied = []

    class _App:                                          # done()'s clipboard, without a Qt class patch
        @staticmethod
        def clipboard():
            return type("C", (), {"setText": staticmethod(copied.append)})()
    monkeypatch.setattr(coopdoc, "QApplication", _App)
    monkeypatch.setattr(coop, "start_bridge", lambda: None)                 # no real bridge thread
    said = []

    def run_job(argv, **kw):
        args = cli.build_parser().parse_args(["--game", str(game), *argv[3:], "--no-room"])
        kw["on_finished"](kit.run(args, out=said.append))
        return True
    monkeypatch.setattr(coop, "_run", run_job)
    try:
        _reset(coop)
        coop.refresh_status()
        coop.start_coop()
        ini = kit.read_ini_text(game / "Memoria.ini")
        code = kit.read_ini_key(ini, "Netsync", "SessionCode")
        assert code != "ff9-FRIEND01", f"the tab hosted on the code this PC joined with: {said}"
        assert kit.read_ini_key(ini, "Netsync", "HostSessionCode") == code
        assert coop.code.text() == code and copied == [code], (coop.code.text(), copied)
    finally:
        _reset(coop)
