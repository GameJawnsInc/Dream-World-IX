"""Fences for the Sounds tab (:mod:`ff9mapkit.workspace.soundsdoc`) and its player tiers
(:mod:`ff9mapkit.workspace.audioplay`).

The laws fenced FIRST are the ones this surface exists to keep: construction and tab-show do NO work
(no catalog read, no install lookup, no audio player), and nothing here can reach this machine -- the
catalog, the audio, the player, the names file and the mod folder all arrive through constructor
seams, and ``sync=True`` runs the two workers inline. ``FF9MAPKIT_NO_AUDIO`` is the belt under the
``player_factory`` seam: no test in this process can open an audio device.

THE FIXTURE IS OWNED HERE (``sample_map`` / ``sample_audio`` / ``FakePlayer`` / ``make_doc``) and
``tools/gui_snap.py`` loads it by path for the ``sounds:*`` surfaces -- one owner, so the snap and
the tests can never disagree about what a loaded Sounds tab looks like. It is kit-authored data:
ids, file names and made-up lengths, zero game bytes.

Width constants are never asserted (offscreen lies about width): counts, text, states, relationships.
"""
from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6", reason="GUI extra not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("FF9MAPKIT_NO_THUMBS", "1")
os.environ.setdefault("FF9MAPKIT_NO_AUDIO", "1")

from PySide6.QtCore import QEvent, Qt                                           # noqa: E402
from PySide6.QtGui import QAccessible, QGuiApplication, QKeyEvent               # noqa: E402
from PySide6.QtWidgets import (QAbstractButton, QAbstractSlider, QAbstractSpinBox, QApplication,  # noqa: E402
                               QComboBox, QLineEdit, QListWidget, QPlainTextEdit, QScrollBar,
                               QTextEdit, QTreeWidget, QWidget)

from ff9mapkit import config, sound, soundcat                                   # noqa: E402
from ff9mapkit.editor.theme import pick_palette                                 # noqa: E402
from ff9mapkit.workspace import audioplay, icons                                # noqa: E402
from ff9mapkit.workspace.soundsdoc import SoundsDoc                             # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _isolate_data_dir(tmp_path, monkeypatch):
    """Nothing below should reach the kit cache -- and if something ever does, it lands in a tmp tree."""
    monkeypatch.setenv("FF9MAPKIT_DATA", str(tmp_path / "kitdata"))


# =============================================================================== THE FIXTURE ===
def _fields_of(place: str, n: int) -> list:
    """``n`` real field ids the packaged region catalog files under ``place`` -- so the fixture's
    where-used rows join to real place names without baking an id table here."""
    field_arc, arcs = soundcat.zone_join()
    ids = sorted(f for f, k in field_arc.items() if soundcat.place_label(arcs[k]["name"]) == place)
    return ids[:n]


_MUSIC = [(0, "music006"), (9, "music008"), (35, "music024"), (47, "music047"), (60, "music031"),
          (74, "music054"), (88, "music003"), (136, "music122")]
_SFX = [(101, "SE00", "se000003"), (103, "SE00", "se000001"), (108, "SE00", "se000004"),
        (633, "SE00", "se000012"), (1362, "SE00", "se000032"), (122, "SE03", "se031062"),
        (912, "SE05", "se050017"), (914, "SE05", "se050019"), (923, "SE06", "se060004"),
        (2210, "SE52", "se520008"), (2211, "SE52", "se520009")]
MOOGLE = 220                                                        # GEO_NPC_F0_MOG, a real catalog id
CHEST = 75                                                         # GEO_ACC_F0_TBX
_STREAM = [(5, "song0005_0"), (82, "song0082_0"), (125, "song0125_0")]
_MOVIE = [(0, "FMV001"), (7, "FMV008")]


def _ctx(play=(), ops=None, models=(), pre=(), pmodels=()) -> dict:
    """One sound's field-usage summary, in the shape ``soundcat.summarize_usage`` keeps."""
    return {"ops": dict(ops or {"play": sum(n for *_x, n in play)}), "play": [list(p) for p in play],
            "pre": [list(p) for p in pre], "models": [list(m) for m in models],
            "pmodels": [list(m) for m in pmodels]}


def sample_map() -> soundcat.SoundMap:
    """A small, representative catalog: named and unnamed rows of every kind, and one sound for each
    way the kit can DESCRIBE one -- a battle effect's, a monster's death cry (an invented monster: the
    fixture carries no game text), a Moogle's talk handler, an ambience loop, a door trigger -- plus
    sounds nothing names at all."""
    alex, ice, evil = _fields_of("Alexandria", 4), _fields_of("Ice Cavern", 3), _fields_of("Evil Forest", 2)
    rows = {"music": [{"id": i, "resource_id": f"Sounds01/BGM_/{stem}"} for i, stem in _MUSIC],
            "sfx": [{"id": i, "resource_id": f"Sounds0{'3' if bank >= 'SE10' else '2'}/{bank}/{stem}"}
                    for i, bank, stem in _SFX],
            "stream": [{"id": i, "resource_id": f"Sounds02/song_/{stem}"} for i, stem in _STREAM],
            "movie": [{"id": i, "resource_id": f"Sounds02/Movie_/{stem}"} for i, stem in _MOVIE]}
    uses = {"music": {9: alex, 60: ice, 88: evil, 35: ice[:1] + evil[:1]},
            "sfx": {633: alex + ice, 912: alex[:2], 914: ice, 108: alex[:1]},
            "stream": {5: evil, 82: ice[:1]}, "movie": {}}
    contexts = {"music": {}, "movie": {}, "stream": {
        5: _ctx([("logic", "routine", "", 2)]), 82: _ctx([("main", "routine", "", 1)])}, "sfx": {
        633: _ctx([("region", "touch", "warp", 7)]),
        108: _ctx([("object", "touch", "item+text", 1)], models=[(CHEST, 1)]),
        912: _ctx([("object", "talk", "text", 2)], models=[(MOOGLE, 2)]),
        914: _ctx([("main", "init", "", 3)], ops={"sustain": 3, "stop": 3, "shape": 2})}}
    audio = {}
    for kind, facts in (("music", [84.75, 1, 2]), ("sfx", [0.45, 0, 1]), ("stream", [12.0, 0, 1]),
                        ("movie", [120.0, 0, 2])):
        for r in rows[kind]:
            audio[r["resource_id"]] = list(facts)
    audio["Sounds02/SE05/se050019"] = [12.0, 1, 1]                   # the ambience loop really loops
    return soundcat.SoundMap(
        stamp="fixture", rows=rows, uses=uses, contexts=contexts, audio=audio,
        effects={"Sounds03/SE52/se520008": [5, 14], "Sounds03/SE52/se520009": [14]},
        monsters={122: {"die": ["Test Golem"]}}, field_count=9)


def sample_audio(tmp_dir):
    """An ``audio_fn`` over a tmp dir: each sound "extracts" to a small real file (so Export has bytes
    to copy) with made-up, kind-shaped facts -- music is long, stereo and looped; the rest is short."""
    calls = []

    def _fn(s, mod):
        calls.append((s.key, mod))
        p = tmp_dir / f"{s.stem}.ogg"
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"OggS-fixture-" + s.stem.encode())
        if s.kind == "music":
            info = {"rate": 44100, "channels": 2, "samples": 3737466, "seconds": 84.75,
                    "loop_start": 710984, "loop_end": 3737465}
        elif s.kind == "movie":
            info = {"rate": 44100, "channels": 2, "samples": 5292000, "seconds": 120.0,
                    "loop_start": 0, "loop_end": 0}
        else:
            info = {"rate": 44100, "channels": 1, "samples": 19845, "seconds": 0.45,
                    "loop_start": 0, "loop_end": 0}
        return p, info, "stock"

    _fn.calls = calls
    return _fn


class FakePlayer(audioplay.Player):
    """A player that keeps state and makes no sound -- the test double AND the snap's player."""
    name = "fake"
    label = "fake player"
    can_seek = True
    can_pause = True

    def __init__(self, parent=None, *, inline=True, can_seek=True):
        super().__init__(parent)
        self.inline = inline
        self.can_seek = can_seek
        self.log = []
        self._pos = 0

    def load(self, path, *, duration_ms=0):
        self.log.append(("load", os.path.basename(str(path))))
        self._path, self._duration, self._pos = str(path), int(duration_ms or 0), 0
        self._set_state(audioplay.STOPPED)
        self.durationChanged.emit(self._duration)

    def play(self):
        self.log.append(("play",))
        if self.inline:
            self._set_state(audioplay.PLAYING)

    def pause(self):
        self.log.append(("pause",))
        self._set_state(audioplay.PAUSED)

    def stop(self):
        self.log.append(("stop",))
        self._pos = 0
        self._set_state(audioplay.STOPPED)

    def seek(self, ms):
        self.log.append(("seek", int(ms)))
        self._pos = int(ms)
        self.positionChanged.emit(self._pos)

    def position(self) -> int:
        return self._pos

    def tick(self, ms):
        """The clock moved (what a real backend's positionChanged does)."""
        self._pos = int(ms)
        self.positionChanged.emit(self._pos)


class _Runner:
    """The shell's ``run_job`` stand-in: records the job and lets the test finish it."""

    def __init__(self):
        self.jobs = []

    def __call__(self, argv, **kw):
        self.jobs.append((list(argv), kw))
        return True

    def finish(self, code=0):
        self.jobs[-1][1]["on_finished"](code)


def make_doc(tmp_path, *, pal=None, load=True, **over):
    """A SoundsDoc wired entirely to doubles. Returns the doc; its doubles hang off it as
    ``doc.t_audio`` / ``doc.t_players`` / ``doc.t_run`` / ``doc.t_warns`` / ``doc.t_names``."""
    players, warns = [], []
    audio = over.pop("audio_fn", None) or sample_audio(tmp_path / "audio")
    run = over.pop("run", None) or _Runner()
    names = over.pop("names_path", None) or (tmp_path / "cfg" / "sound_names.toml")

    def _factory():
        p = over_player()
        players.append(p)
        return p

    over_player = over.pop("player", None) or FakePlayer
    kw = dict(run=run, catalog_fn=lambda force: sample_map(), audio_fn=audio,
              player_factory=_factory, names_path=names, mod_fn=lambda: None, sync=True)
    kw.update(over)
    doc = SoundsDoc(pal or pick_palette("dark"), tmp_path / "kit", **kw)
    doc.t_audio, doc.t_players, doc.t_run, doc.t_warns, doc.t_names = audio, players, run, warns, names
    doc._warn = lambda title, text: warns.append((title, text))
    if load:
        doc.load()
    return doc


def rewire(sd, scratch, *, catalog=None):
    """Swap a LIVE SoundsDoc's seams for the doubles -- for the tab the real Workspace built (the shell
    fences below, and gui_snap's ``sounds:*`` surfaces). Returns the list its players are appended to.
    After this the doc cannot reach an install, an audio device, or the user's names file."""
    players = []

    def _player():
        players.append(FakePlayer(sd))
        return players[-1]

    sd._catalog_fn = catalog or (lambda force: sample_map())
    sd._audio_fn = sample_audio(scratch / "audio")
    sd._player_factory = _player
    sd._names_path = scratch / "sound_names.toml"
    sd._mod_fn = lambda: None
    sd._sync = True
    if sd._names_path.exists():
        sd._names_path.unlink()                    # a prior run's names must not leak into this one
    return players


@pytest.fixture
def doc(app, tmp_path):
    d = make_doc(tmp_path)
    d.resize(1000, 760)
    d.show()
    app.processEvents()
    yield d
    d.shutdown()
    d.close()


def _rows(doc):
    return [doc.listw.item(i).text() for i in range(doc.listw.count())]


def _stems(doc):
    """The file stems of the listed rows, in order (a named row does not print its stem)."""
    by_key = {s.key: s.stem for s in doc._entries}
    return [by_key[tuple(doc.listw.item(i).data(Qt.ItemDataRole.UserRole))] for i in range(doc.listw.count())]


# ================================================================== no work until it is asked for ===
def test_construction_and_tab_show_touch_nothing(app, tmp_path):
    """The startup-spend law: the Workspace BUILDS this tab at launch, so building it (and showing
    it) may not read a catalog, look for the install or the mod folder, or open an audio device."""
    tripped = []

    def _trip(name):
        def _f(*a, **k):
            tripped.append(name)
            raise AssertionError(f"{name} ran uninvited")
        return _f

    d = SoundsDoc(pick_palette("dark"), tmp_path / "kit", run=_trip("run"), catalog_fn=_trip("catalog"),
                  audio_fn=_trip("audio"), player_factory=_trip("player"), mod_fn=_trip("mod"),
                  names_path=tmp_path / "names.toml")
    d.show()
    app.processEvents()
    d.hide()
    d.show()
    app.processEvents()
    assert tripped == []
    assert not d.loaded() and d._stack.currentWidget() is d._guide_page
    assert d._player is None and d.listw.count() == 0
    assert d.crumb_label() == "browse sounds"
    d.close()


def test_the_real_default_seams_are_not_resolved_at_construction(app, tmp_path, monkeypatch):
    """The same law for the DEFAULTS: with no seam injected, construction still must not call into the
    install lookup, the catalog builder or the player chooser."""
    hit = []
    monkeypatch.setattr(config, "find_game_path", lambda *a, **k: hit.append("game") or (_ for _ in ()).throw(AssertionError))
    monkeypatch.setattr(soundcat, "build_map", lambda *a, **k: hit.append("map"))
    monkeypatch.setattr(soundcat, "load_names", lambda *a, **k: hit.append("names") or {})
    monkeypatch.setattr(audioplay, "make_player", lambda *a, **k: hit.append("player"))
    d = SoundsDoc(pick_palette("dark"), tmp_path / "kit", run=lambda *a, **k: True)
    d.show()
    app.processEvents()
    assert hit == []
    d.close()


def test_load_fills_the_browser(doc):
    assert doc.loaded() and doc._stack.currentWidget() is doc._browser_page
    total = len(_MUSIC) + len(_SFX) + len(_STREAM) + len(_MOVIE)
    assert doc.listw.count() == total
    named = sum(1 for s in doc._entries if s.title)
    assert 0 < named < total, "the fixture must carry both named and unnamed rows"
    assert doc.count_lbl.fullText() == f"{total} sounds  ·  {total - named} unnamed"
    assert _rows(doc)[1] == "Vivi's Theme  ·  id 9"                   # the kit's own names table, spent
    assert doc.listw.item(1).toolTip() == "Vivi's Theme — Sounds01/BGM_/music008, id 9  ·  Music  ·  1:24 loop"
    assert doc.listw.textElideMode() == Qt.TextElideMode.ElideMiddle, \
        "a long title must elide in the middle, so the id at the row's end survives a narrow pane"
    assert doc.t_players == [], "loading the list must not build an audio player"
    assert not doc.play_btn.isEnabled(), "nothing is selected yet"


@pytest.mark.parametrize("exc,title", [
    (config.ConfigError("no FF9 here"), "FF9 install not found"),
    (RuntimeError("UnityPy is missing"), "The sounds could not be read"),
])
def test_a_failed_load_teaches_and_a_retry_recovers(app, tmp_path, exc, title):
    state = {"fail": True}

    def _catalog(force):
        if state["fail"]:
            raise exc
        return sample_map()

    d = make_doc(tmp_path, catalog_fn=_catalog)
    assert not d.loaded() and d._stack.currentWidget() is d._guide_page
    texts = [w.text() for w in d._guide_page.findChildren(QWidget) if hasattr(w, "text")]
    assert title in texts
    if type(exc) is RuntimeError:                                   # (ConfigError IS-A RuntimeError)
        assert "UnityPy is missing" in texts, "the real error text is surfaced, never swallowed"
    state["fail"] = False
    d.load()
    assert d.loaded() and d.listw.count() > 0
    d.close()


def test_a_failed_rescan_keeps_the_list_that_is_already_up(app, tmp_path):
    state = {"n": 0}

    def _catalog(force):
        state["n"] += 1
        if state["n"] > 1:
            raise RuntimeError("bundle locked")
        return sample_map()

    d = make_doc(tmp_path, catalog_fn=_catalog)
    before = d.listw.count()
    d.rescan_btn.click()
    assert d.listw.count() == before and d._stack.currentWidget() is d._browser_page
    assert "bundle locked" in d.note.text() and d.note.property("state") == "error"
    assert d.rescan_btn.isEnabled() and d.rescan_btn.text() == "Rescan"
    d.close()


# ================================================================================== the filters ===
def _pick(combo, key):
    i = combo.findData(key)
    assert i >= 0, f"{key!r} is not offered: {[combo.itemData(j) for j in range(combo.count())]}"
    combo.setCurrentIndex(i)


def test_every_sound_is_filed_under_a_category_with_a_count(doc):
    """The category filter is the tab's map of the catalog: every sound lands in exactly one, only
    categories that hold something are offered, and each says how many."""
    items = {doc.category.itemData(i): doc.category.itemText(i) for i in range(doc.category.count())}
    total = len(doc._entries)
    assert items[None] == f"All sounds  ({total})"
    assert items["music"] == f"Music  ({len(_MUSIC)})"
    assert items["ability"] == "Battle: spells & abilities  (2)"
    assert items["monster"] == "Battle: monster voices  (1)"
    assert items["ambience"] == "Ambience & loops  (1)"
    assert items["door"] == "Doors & exits  (1)"
    assert items["stream"] == f"Streams & vocals  ({len(_STREAM)})"
    assert "world" not in items and "minigame" not in items, "an empty category is not offered"
    counted = sum(int(t.rsplit("(", 1)[1].rstrip(")")) for k, t in items.items() if k is not None)
    assert counted == total, "every sound is in exactly one category"


def test_the_category_filter_narrows_the_list_and_refills_the_banks(doc):
    _pick(doc.category, "ability")
    assert _stems(doc) == ["se520008", "se520009"]
    banks = [(doc.bank.itemData(i), doc.bank.itemText(i)) for i in range(doc.bank.count())]
    assert banks == [(None, "All banks"), ("SE52", "SE52 · Battle effects")], "only this category's banks"
    _pick(doc.category, None)
    banks = [doc.bank.itemData(i) for i in range(doc.bank.count())]
    assert banks == [None, "BGM_", "SE00", "SE03", "SE05", "SE06", "SE52", "song_", "Movie_"], \
        "music first, the SE banks in number order, then streams and movie audio"
    _pick(doc.bank, "SE05")
    assert doc.bank.currentText() == "SE05 · Alexandria, Ice Cavern", "an area bank names its areas"
    assert _stems(doc) == ["se050017", "se050019"]
    _pick(doc.category, "music")
    assert doc.bank.currentData() is None, "a bank the new category lacks falls back, never sticks"
    assert doc.listw.count() == len(_MUSIC)


def test_search_matches_a_name_a_tag_an_id_and_a_place(doc):
    doc.search.setText("vivi")
    assert _rows(doc) == ["Vivi's Theme  ·  id 9"]
    doc.search.setText("music008")                                  # the FILE, though the row hides it
    assert _stems(doc) == ["music008"]
    doc.search.setText("moogle")                                    # a tag, AND a description
    assert set(_stems(doc)) == {"se000032", "se050017"}, "named by the kit, or played by a Moogle"
    doc.search.setText("1362")                                      # an id
    assert _stems(doc) == ["se000032"]
    doc.search.setText("death cry")                                 # what the kit worked out
    assert _stems(doc) == ["se031062"]
    doc.search.setText("thundera")                                  # the battle effect that loads it
    assert _stems(doc) == ["se520008"]
    doc.search.setText("ambience loop")
    assert _stems(doc) == ["se050019"]
    doc.search.setText("ice cavern")                                # a PLACE its field scripts sit in
    stems = set(_stems(doc))
    assert {"music031", "se000012", "se050019", "song0082_0"} <= stems
    assert "music008" not in stems
    assert doc.count_lbl.fullText().startswith(f"{doc.listw.count()} of ")


def test_an_unnamed_row_leads_with_what_the_kit_worked_out(doc):
    """A bare file stem tells a browsing user nothing, and most effects have no name. So an unnamed
    row IS the kit's description of the sound (its id tells apart two that share one), and a sound
    nothing describes keeps its stem and trails whatever its bank says."""
    rows = dict(zip(_stems(doc), _rows(doc)))
    assert rows["se520008"] == "Thundera (single) +1  ·  id 2210"
    assert rows["se520009"] == "Berserk (single) · sound 2 of 2  ·  id 2211"
    assert rows["se031062"] == "Test Golem death cry  ·  id 122"
    assert rows["se050017"] == "Moogle talk · Alexandria  ·  id 912"
    assert rows["se050019"] == "Ambience loop · Ice Cavern  ·  id 914"
    assert rows["song0005_0"] == "Scene event · Evil Forest  ·  id 5"
    assert doc.listw.item(_stems(doc).index("se050017")).toolTip().startswith("Sounds02/SE05/se050017, id 912"), \
        "the file a described row leaves out is one hover away"
    assert rows["se060004"] == "se060004  ·  id 923  ·  area set", "nothing describes it: the bank speaks"
    assert rows["song0125_0"] == "song0125_0  ·  id 125  ·  stream"
    assert rows["se000012"] == "Door opening  ·  id 633", "a NAMED row is its name"


def test_a_long_row_elides_instead_of_scrolling_sideways(app, doc):
    """A row wider than the list must elide in the middle (keeping its id), never push an h-bar -- and
    it must not depend on which row happens to be first: under 'Unnamed only' the first row is a long
    description, and with uniform item sizes its hint was every row's."""
    doc.resize(520, 700)
    for unnamed in (False, True):
        doc.unnamed_only.setChecked(unnamed)
        app.processEvents()
        assert doc.listw.horizontalScrollBar().maximum() == 0, f"unnamed_only={unnamed}"
        first = doc.listw.visualItemRect(doc.listw.item(0))
        assert first.width() <= doc.listw.viewport().width(), "a row is never wider than the list"


def test_a_description_is_shown_in_italics_and_is_not_a_name(doc):
    """Italics say 'derived, not named' -- and the font carries ONLY the italic flag, so the delegate
    resolves it against the list's own font and the row follows the text-size dial."""
    by_stem = {s.stem: doc._items[s.key] for s in doc._entries}
    for stem in ("se520008", "se031062", "se050017", "se050019"):
        assert by_stem[stem].font().italic(), stem
    for stem in ("music008", "se000012", "se060004", "song0125_0"):
        assert not by_stem[stem].font().italic(), f"{stem}: named, or nothing to describe"
    from PySide6.QtGui import QFont
    assert by_stem["se520008"].font().resolveMask() == doc._italic.resolveMask() != QFont("x", 30).resolveMask()
    described = sum(1 for s in doc._entries if s.described)
    assert f"{described} of the unnamed sounds are DESCRIBED" in doc.count_lbl.toolTip()
    doc.unnamed_only.setChecked(True)                               # ...and described is still UNNAMED
    assert {"se520008", "se031062", "se050017"} <= set(_stems(doc))


def test_unnamed_only_keeps_exactly_the_rows_that_need_a_name(doc):
    doc.unnamed_only.setChecked(True)
    assert doc.listw.count() == sum(1 for s in doc._entries if not s.title)
    titled = {s.stem for s in doc._entries if s.title}
    assert not titled & set(_stems(doc))
    doc.unnamed_only.setChecked(False)
    assert doc.listw.count() == len(doc._entries)


# ============================================================================ the detail pane ===
def test_selecting_a_sound_fills_the_detail_and_reads_its_audio(doc):
    assert doc.select("music", 9)
    assert doc.d_title.text() == "Vivi's Theme"
    assert doc.d_sub.text() == "Music  ·  id 9  ·  Sounds01/BGM_/music008"
    assert doc.crumb_label() == "Vivi's Theme"
    assert doc.name_edit.text() == "Vivi's Theme"
    assert [doc.places.item(i).text() for i in range(doc.places.count())] == ["Alexandria  ·  4 fields"]
    assert doc.places.item(0).toolTip().startswith("field ids ")
    assert doc.places_sum.text() == "Named by 4 field scripts across 1 place."
    assert doc.t_audio.calls == [(("music", 9), None)]
    assert doc.d_facts.text().splitlines() == [
        "Length 1:24  ·  44100 Hz  ·  stereo",
        "Loops from 0:16 to 1:24 (samples 710984–3737465)"]
    assert doc.time_lbl.text() == "0:00 / 1:24" and doc.seek.maximum() == 84750
    assert doc.note.text() == "Ready — press Play."
    assert doc.play_btn.isEnabled() and doc.loop_chk.isEnabled()
    assert doc.t_players == [], "selecting must not build the audio player"


def test_the_detail_pane_says_what_the_kit_worked_out_and_why(doc):
    doc.select("sfx", 2210)                                         # a battle effect's sound
    assert doc.d_sub.text() == "Battle: spells & abilities  ·  id 2210  ·  Sounds03/SE52/se520008"
    assert doc.about.text().splitlines() == [
        "Looks like: Thundera (single) +1",
        "Loaded by battle effects: Thundera (single) (effect 5), Berserk (single) (effect 14)."]
    assert not doc.places.isVisible() and not doc.places_sum.isVisible()
    doc.select("sfx", 122)                                          # a monster's
    assert doc.about.text().splitlines() == ["Looks like: Test Golem death cry", "Death cry of: Test Golem."]
    doc.select("sfx", 912)                                          # a field script's
    assert doc.d_sub.text().startswith("NPCs & creatures  ·  id 912")
    assert doc.about.text().splitlines() == ["Looks like: Moogle talk · Alexandria",
                                             "Played when you talk to it ×2."]
    assert doc.places_sum.text() == "Named by 2 field scripts across 1 place."
    doc.select("sfx", 914)
    assert doc.about.text().splitlines() == [
        "Looks like: Ambience loop · Ice Cavern", "Played at field startup ×3.",
        "Scripts also control it: 3 held starts, 2 fades or pans, 3 stops."]
    doc.select("sfx", 633)                                          # NAMED: the same read, as a use
    assert doc.about.text().splitlines()[0] == "Used as: Door or exit · Alexandria +1"
    assert "(that routine also leaves the field)" in doc.about.text()


def test_a_sound_nothing_describes_says_so_instead_of_showing_an_empty_card(doc):
    doc.select("sfx", 101)                                          # named, in the system bank, unplaced
    assert not doc.places.isVisible() and not doc.places_sum.isVisible()
    assert doc.about.text().startswith("No field script or battle effect names it")
    doc.select("sfx", 923)                                          # unnamed, in an area bank
    assert doc.about.text().splitlines() == ["Unplaced — area set.", "No script names it."]
    doc.select("movie", 0)
    assert doc.about.text().splitlines() == ["Unplaced — movie audio.",
                                             "Movie audio plays with its video, not from a script."]


def test_the_length_shows_the_moment_a_row_is_picked(app, tmp_path):
    """The catalog already knows every sound's length -- the pane must not wait for the audio to say
    it. (The async lane: the audio has NOT landed when this reads the pane.)"""
    d = make_doc(tmp_path, load=False, sync=False)
    d.load(sync=True)
    d.select("sfx", 914)
    d._debounce.stop()
    assert d._audio is None
    assert d.d_facts.text().splitlines() == ["Length 0:12  ·  mono", "Loops"]
    assert d.seek.maximum() == 12000 and d.time_lbl.text() == "0:00 / 0:12"
    d.select("sfx", 633)
    d._debounce.stop()
    assert d.d_facts.text().splitlines() == ["Length 0.5s  ·  mono", "Plays once (no loop points)"]
    d.shutdown()
    d.close()


def test_a_short_unlooped_sound_reports_that_it_plays_once(doc):
    doc.select("sfx", 633)
    assert doc.d_facts.text().splitlines() == ["Length 0.5s  ·  44100 Hz  ·  mono",
                                               "Plays once (no loop points)"]
    assert not doc.loop_chk.isEnabled(), "no loop points -> the Loop box has nothing to do"


def test_only_music_and_sfx_offer_replace_add_and_a_snippet(doc):
    for kind, sid, ok in (("music", 9, True), ("sfx", 633, True), ("stream", 5, False), ("movie", 0, False)):
        doc.select(kind, sid)
        assert doc.replace_btn.isEnabled() is ok and doc.add_btn.isEnabled() is ok, kind
        assert doc.copy_snip_btn.isEnabled() is ok, kind
        assert doc.copy_id_btn.isEnabled() and doc.export_btn.isEnabled(), kind
        assert doc.suggest_btn.isEnabled() is bool(doc._current.describe), kind


# ================================================================================== playback ===
def test_play_builds_the_player_lazily_and_drives_it(doc):
    doc.select("music", 9)
    doc.play_btn.click()
    assert len(doc.t_players) == 1
    p = doc.t_players[0]
    assert p.log == [("load", "music008.ogg"), ("play",)]
    assert p.state() == audioplay.PLAYING and p.duration() == 84750
    assert p.volume() == pytest.approx(0.6), "the volume slider's value reaches a player built later"
    p.tick(12500)
    assert doc.seek.value() == 12500 and doc.time_lbl.text() == "0:12 / 1:24"
    doc.play_btn.click()                                            # pause
    assert p.state() == audioplay.PAUSED
    doc.play_btn.click()                                            # resume: NO reload
    assert p.log[-2:] == [("pause",), ("play",)] and p.state() == audioplay.PLAYING
    doc.stop_btn.click()
    assert p.state() == audioplay.STOPPED and doc.seek.value() == 0
    assert doc.note.text() == "Ready — press Play."
    doc.play_btn.click()                                            # from stopped: load again, then play
    assert p.log[-2:] == [("load", "music008.ogg"), ("play",)]
    assert len(doc.t_players) == 1, "one player for the tab's life"


def test_the_seek_slider_seeks_and_the_clock_never_fights_the_thumb(doc):
    doc.select("music", 9)
    doc.play_btn.click()
    p = doc.t_players[0]
    doc.seek.setValue(30000)                                        # a key press / a click on the groove
    assert p.log[-1] == ("seek", 30000)
    n = len(p.log)
    p.tick(31000)                                                   # the clock moving the slider...
    assert doc.seek.value() == 31000 and len(p.log) == n, "...must not come back as a seek"
    doc.seek.setSliderDown(True)                                    # the user is dragging
    p.tick(32000)
    assert doc.seek.value() == 31000, "the user's thumb outranks the clock"
    doc.seek.setValue(60000)
    assert len(p.log) == n, "no seek until the thumb is let go"
    doc.seek.setSliderDown(False)                                   # emits sliderReleased
    assert p.log[-1] == ("seek", 60000)


def test_a_thumb_parked_before_play_is_where_playback_starts(doc):
    doc.select("music", 9)
    doc.seek.setValue(20000)
    doc.play_btn.click()
    assert doc.t_players[0].log[-3:] == [("load", "music008.ogg"), ("play",), ("seek", 20000)]


def test_the_loop_box_hands_the_player_the_tracks_own_region_in_ms(doc):
    doc.select("music", 9)
    doc.play_btn.click()
    p = doc.t_players[0]
    assert p._loop is None
    doc.loop_chk.setChecked(True)
    assert p._loop == (int(710984 * 1000 / 44100), int(3737465 * 1000 / 44100))
    doc.loop_chk.setChecked(False)
    assert p._loop is None


def test_the_volume_slider_reaches_the_player(doc):
    doc.select("sfx", 633)
    doc.play_btn.click()
    doc.volume.setValue(25)
    assert doc.t_players[0].volume() == pytest.approx(0.25)


def test_selecting_another_sound_silences_the_one_playing(doc):
    doc.select("music", 9)
    doc.play_btn.click()
    p = doc.t_players[0]
    doc.select("sfx", 633)
    assert p.state() == audioplay.STOPPED and p.log[-1] == ("stop",)
    assert doc.d_title.text() == "Door opening" and doc.seek.maximum() == 450
    assert doc.time_lbl.text() == "0.0 / 0.5s", "a sub-ten-second sound must not read 0:00 / 0:00"


def test_play_on_select_auditions_each_row(doc):
    doc.autoplay.setChecked(True)
    doc.select("sfx", 633)
    p = doc.t_players[0]
    assert p.log[-2:] == [("load", "se000012.ogg"), ("play",)]
    doc.select("sfx", 108)
    assert p.log[-3:] == [("stop",), ("load", "se000004.ogg"), ("play",)]


def test_typing_in_the_search_box_does_not_stop_the_music(doc):
    doc.select("music", 9)
    doc.play_btn.click()
    p = doc.t_players[0]
    n = len(p.log)
    doc.search.setText("viv")
    assert p.state() == audioplay.PLAYING and len(p.log) == n
    assert doc.listw.currentItem().text().startswith("Vivi's Theme"), "the pick survives the refill"
    doc.search.setText("door")                                      # the playing row is filtered OUT
    assert p.state() == audioplay.PLAYING and doc.d_title.text() == "Vivi's Theme"


def test_leaving_the_tab_silences_it(app, doc):
    doc.select("music", 9)
    doc.play_btn.click()
    doc.hide()
    app.processEvents()
    assert doc.t_players[0].state() == audioplay.STOPPED


def test_a_superseded_selections_late_audio_paints_nothing(app, tmp_path):
    """The identity fence, on the ASYNC lane's own slot: an answer for a selection the user has
    already left must not fill the pane or start playing."""
    d = make_doc(tmp_path, load=False, sync=False)                  # the debounced worker lane...
    d.load(sync=True)                                               # ...with the catalog read inline
    d.autoplay.setChecked(True)
    d.select("music", 9)
    stale = (("music", 9), d._gen)
    d.select("sfx", 633)                                            # the user moved on before it landed
    d._debounce.stop()
    d._req = (("sfx", 633), d._gen)
    d._on_audio(stale, tmp_path / "music008.ogg", {"seconds": 84.75, "rate": 44100}, "stock", "")
    assert d._audio is None and d.t_players == [] and "Hz" not in d.d_facts.text()
    d._on_audio(d._req, tmp_path / "se000012.ogg", {"seconds": 0.45, "rate": 44100, "channels": 1}, "stock", "")
    assert d._audio is not None and d.t_players and d.t_players[0].log[-1] == ("play",)
    d.shutdown()
    d.close()


def test_pressing_play_before_the_audio_lands_plays_it_when_it_does(app, tmp_path):
    d = make_doc(tmp_path, load=False, sync=False)
    d.load(sync=True)
    d.select("sfx", 633)                                            # debounce armed, nothing fetched yet
    assert d._audio is None
    d._debounce.stop()
    d._req = (("sfx", 633), d._gen)                                 # the fetch is in flight
    d.play_btn.click()
    assert d.t_players == [], "nothing to play yet"
    d._on_audio(d._req, tmp_path / "se000012.ogg", {"seconds": 0.45, "rate": 44100}, "stock", "")
    assert d.t_players[0].log[-1] == ("play",)
    d.shutdown()
    d.close()


def test_audio_that_cannot_be_read_is_reported_and_disarms_the_transport(app, tmp_path):
    def _audio(s, mod):
        raise FileNotFoundError("no bundled audio for 'Sounds02/SE00/se000012'")

    d = make_doc(tmp_path, audio_fn=_audio)
    d.select("sfx", 633)
    assert "no bundled audio" in d.note.text() and d.note.property("state") == "warn"
    assert not d.play_btn.isEnabled() and not d.export_btn.isEnabled()
    assert d.name_edit.isEnabled(), "a sound that will not play can still be named"
    d.close()


def test_a_player_failure_keeps_its_own_sentence(doc):
    doc.select("sfx", 633)
    doc.play_btn.click()
    p = doc.t_players[0]
    p.failed.emit("the device is busy")
    p.stop()                                                        # the stop a failure causes
    assert doc.note.text() == "Playback failed — the device is busy"
    assert doc.note.property("state") == "error"
    doc.play_btn.click()                                            # a fresh try clears it
    assert doc.note.property("state") == ""


def test_with_no_in_app_player_play_hands_the_file_to_the_system(app, tmp_path):
    d = make_doc(tmp_path, player=lambda: FakePlayer(inline=False, can_seek=False))
    d.select("music", 9)
    d.play_btn.click()
    p = d.t_players[0]
    assert p.log[-2:] == [("load", "music008.ogg"), ("play",)]
    assert d.note.text().startswith("Opened in fake player.") and "ffmpeg" in d.note.text()
    assert not d.seek.isEnabled(), "a player that cannot seek gets no live seek bar"
    d.select("sfx", 633)
    assert not d.seek.isEnabled(), "...and a new selection does not re-enable it"
    d.close()


# ===================================================================================== naming ===
def _press(widget, key, mods=Qt.KeyboardModifier.NoModifier):
    QApplication.sendEvent(widget, QKeyEvent(QEvent.Type.KeyPress, key, mods))


def test_naming_a_sound_writes_the_overlay_and_relabels_the_row(doc):
    doc.select("sfx", 912)
    assert doc.d_title.text() == "se050017" and doc.name_edit.text() == ""
    doc.name_edit.setText("  Castle bell  ")
    doc.tags_edit.setText("Bell, alexandria ,bell")
    doc.save_name_btn.click()
    over = soundcat.parse_names(doc.t_names.read_text(encoding="utf-8"))
    assert over == {"sfx": {"se050017": {"title": "Castle bell", "tags": ["bell", "alexandria"]}}}
    assert doc.d_title.text() == "Castle bell" and doc.tags_edit.text() == "bell, alexandria"
    assert doc.listw.currentItem().text() == "Castle bell  ·  id 912"
    assert doc.name_status.isVisible() and doc.name_status.text().startswith("Saved to ")
    doc.search.setText("bell")
    assert _rows(doc) == ["Castle bell  ·  id 912"], "the new tag is searchable at once"


def test_enter_saves_and_shift_enter_saves_then_moves_on(doc):
    doc.unnamed_only.setChecked(True)                               # the naming queue
    first, second = doc.listw.item(0).text(), doc.listw.item(1).text()
    doc.listw.setCurrentRow(0)
    stem = doc._current.stem
    doc.name_edit.setText("Named one")
    _press(doc.name_edit, Qt.Key.Key_Return)                        # Enter: save, stay
    assert doc._current.stem == stem and doc._current.title == "Named one"
    assert first not in _rows(doc), "'Unnamed only' drops a sound the moment it is named"
    assert doc.listw.item(0).text() == second
    doc.listw.setCurrentRow(0)
    nxt = doc.listw.item(1).text()
    doc.name_edit.setText("Named two")
    _press(doc.tags_edit, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)   # either box
    assert doc.listw.currentItem().text() == nxt, "Shift+Enter moved to the next unnamed sound"
    assert doc.name_edit.text() == "" and doc._current.title == ""
    names = soundcat.parse_names(doc.t_names.read_text(encoding="utf-8"))
    assert sorted(e["title"] for t in names.values() for e in t.values()) == ["Named one", "Named two"]


def test_the_description_can_start_a_name(doc):
    """One click turns the kit's read into a draft the user then corrects by ear."""
    doc.select("sfx", 912)
    assert doc.name_edit.text() == ""
    doc.suggest_btn.click()
    assert doc.name_edit.text() == "Moogle talk, Alexandria"
    doc.select("sfx", 2211)
    doc.suggest_btn.click()
    assert doc.name_edit.text() == "Berserk (single), sound 2 of 2"
    doc.select("sfx", 923)                                          # nothing to start from
    assert not doc.suggest_btn.isEnabled()


def test_a_tag_that_names_a_category_refiles_the_sound(doc):
    """The user's word outranks the derived category: tag an 'ambience loop' as a door and it moves."""
    items = lambda: {doc.category.itemData(i): doc.category.itemText(i) for i in range(doc.category.count())}  # noqa: E731
    assert items()["ambience"] == "Ambience & loops  (1)" and items()["door"] == "Doors & exits  (1)"
    doc.select("sfx", 914)
    doc.name_edit.setText("Portcullis rattle")
    doc.tags_edit.setText("metal, door")
    doc.save_name()
    assert doc._current.category == "door"
    assert doc.d_sub.text().startswith("Doors & exits  ·  id 914")
    assert "ambience" not in items() and items()["door"] == "Doors & exits  (2)"
    _pick(doc.category, "door")
    assert set(_stems(doc)) == {"se000012", "se050019"}
    doc.tags_edit.setText("metal")                                  # drop the tag -> the derived one is back
    doc.save_name()
    assert doc._current.category == "ambience" and items()["ambience"] == "Ambience & loops  (1)"


def test_shift_enter_steps_down_a_list_that_keeps_named_rows(doc):
    _pick(doc.category, "stream")
    doc.listw.setCurrentRow(0)
    doc.name_edit.setText("Forest ambience")
    _press(doc.name_edit, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
    assert doc.listw.currentRow() == 1 and doc.listw.item(0).text().startswith("Forest ambience")


def test_clearing_your_name_brings_the_kits_own_back(doc):
    doc.select("music", 9)
    doc.name_edit.setText("My Vivi cue")
    doc.save_name()
    assert doc.d_title.text() == "My Vivi cue"
    doc.name_edit.setText("")
    doc.tags_edit.setText("")
    doc.save_name()
    assert doc.d_title.text() == "Vivi's Theme" and doc.name_edit.text() == "Vivi's Theme"
    assert "kit's own name" in doc.name_status.text()


def test_a_name_that_cannot_be_written_is_reported_not_swallowed(doc, monkeypatch):
    def _boom(*a, **k):
        raise PermissionError("names file is read-only")
    monkeypatch.setattr(soundcat, "save_user_name", _boom)
    doc.select("sfx", 912)
    doc.name_edit.setText("x")
    doc.save_name()
    assert "read-only" in doc.name_status.text() and doc.name_status.property("state") == "error"
    assert doc._current.title == "", "a failed save changes nothing on screen"


# ======================================================================= copy / export / jobs ===
def test_the_snippet_is_the_line_that_plays_the_sound(doc):
    doc.select("music", 9)
    assert doc.snippet() == "[music]\nsong = 9  # Vivi's Theme\n"
    doc.copy_snip_btn.click()
    assert QGuiApplication.clipboard().text() == "[music]\nsong = 9  # Vivi's Theme\n"
    doc.select("sfx", 912)
    assert doc.snippet() == "sfx = 912  # se050017\n", "an unnamed sound is annotated with its file"
    doc.copy_id_btn.click()
    assert QGuiApplication.clipboard().text() == "912"


def test_export_writes_the_sounds_own_bytes(doc, tmp_path):
    doc.select("sfx", 633)
    asked = []
    out = tmp_path / "exports" / "door.ogg"
    doc._ask_save_ogg = lambda default: asked.append(default) or str(out)
    doc.export_btn.click()
    assert asked == ["se000012.ogg"], "the dialog proposes the file's own name"
    assert out.read_bytes() == b"OggS-fixture-se000012"
    assert str(out) in doc.note.text()
    doc._ask_save_ogg = lambda default: None                        # cancelled: nothing happens
    doc.export_btn.click()


def test_replace_streams_audio_import_for_the_selected_id(doc, tmp_path):
    mod = tmp_path / "MyMod"
    doc.mod_edit.setText(str(mod))
    doc.select("sfx", 633)
    doc._ask_open_audio = lambda: "C:/mine/creak.wav"
    doc.replace_btn.click()
    argv, kw = doc.t_run.jobs[-1]
    assert argv[1:] == ["-m", "ff9mapkit", "audio-import", "C:/mine/creak.wav", "--song", "633",
                        "--kind", "sfx", "--deploy", str(mod)]
    assert "deploy" not in kw["subject"].lower(), \
        "the shell's job runner reads 'deploy' in a subject as a FIELD deploy and snapshots the project"
    assert "RELAUNCH" in kw["ok_next"]
    assert not doc.replace_btn.isEnabled(), "busy while the job runs"
    doc.t_run.finish(0)
    assert doc.replace_btn.isEnabled()


def test_add_mints_a_new_id_of_the_selections_kind(doc, tmp_path):
    doc.mod_edit.setText(str(tmp_path / "MyMod"))
    doc.select("music", 9)
    doc._ask_open_audio = lambda: "C:/mine/theme.flac"
    doc.add_btn.click()
    argv, kw = doc.t_run.jobs[-1]
    assert argv[3:] == ["audio-import", "C:/mine/theme.flac", "--new-song", "--kind", "music",
                        "--deploy", str(tmp_path / "MyMod")]
    assert "--song" not in argv and "deploy" not in kw["subject"].lower()


def test_replace_refuses_without_a_mod_folder_and_a_cancelled_picker_runs_nothing(doc, tmp_path):
    doc.select("sfx", 633)
    asked = []
    doc._ask_open_audio = lambda: asked.append(1) or "C:/x.wav"
    doc.replace_btn.click()
    assert doc.t_warns and doc.t_warns[-1][0] == "No mod folder"
    assert asked == [] and doc.t_run.jobs == [], "no file dialog, no job, before the folder is known"
    doc.mod_edit.setText(str(tmp_path / "MyMod"))
    doc._ask_open_audio = lambda: None
    doc.add_btn.click()
    assert doc.t_run.jobs == []


def test_the_mod_folders_own_tracks_and_replacements_show_in_the_list(doc, tmp_path):
    mod = tmp_path / "MyMod"
    mp = sound.manifest_override_path(mod, "music")
    mp.parent.mkdir(parents=True)
    stock = [{"id": r["id"], "resource_id": r["resource_id"], "type": "Music"} for r in sample_map().rows["music"]]
    mp.write_text(sound.serialize_manifest(
        stock + [{"id": 1000, "resource_id": "Sounds01/BGM_/custom1000", "type": "Music"}]), encoding="utf-8")
    loose = mod / sound.override_rel_path("Sounds02/SE00/se000012")
    loose.parent.mkdir(parents=True)
    loose.write_bytes(b"OggS")
    doc.mod_edit.setText(str(mod))
    doc.mod_edit.editingFinished.emit()
    rows = _rows(doc)
    assert "custom1000  ·  id 1000  ·  added" in rows
    assert "Door opening  ·  id 633  ·  replaced" in rows
    doc.select("music", 1000)
    assert doc.d_sub.text().endswith("added by this mod folder")
    assert doc.about.text().startswith("Added by this mod folder")
    doc.select("sfx", 633)
    assert doc.d_sub.text().endswith("replaced in this mod folder")
    assert doc.t_audio.calls[-1] == (("sfx", 633), str(mod)), "the audio is asked for AS THIS FOLDER plays it"


def test_a_finished_job_refreshes_the_list(doc, tmp_path):
    mod = tmp_path / "MyMod"
    doc.mod_edit.setText(str(mod))
    doc.select("sfx", 633)
    doc._ask_open_audio = lambda: "C:/x.wav"
    doc.replace_btn.click()
    loose = mod / sound.override_rel_path("Sounds02/SE00/se000012")     # what the job would have written
    loose.parent.mkdir(parents=True)
    loose.write_bytes(b"OggS")
    doc.t_run.finish(0)
    assert doc.listw.currentItem().text().endswith("replaced")
    assert doc.d_sub.text().endswith("replaced in this mod folder")


# ========================================================================== a11y + the shell ===
_WATCH = (QAbstractButton, QLineEdit, QComboBox, QAbstractSpinBox, QPlainTextEdit, QTextEdit,
          QListWidget, QTreeWidget, QAbstractSlider)


def _acc_name(wd) -> str:
    iface = QAccessible.queryAccessibleInterface(wd)
    return (iface.text(QAccessible.Text.Name) or "").strip() if iface is not None else ""


def test_every_control_of_the_loaded_tab_announces_a_name(app, doc):
    """The Workspace-wide a11y sweep only ever sees this tab's GUIDE page (it never loads sounds), so
    the loaded browser is swept here, with a sound selected -- every state its controls can be in."""
    doc.select("music", 9)
    app.processEvents()
    holes = []
    for wd in doc.findChildren(QWidget):
        if not isinstance(wd, _WATCH) or not wd.isVisible() or isinstance(wd, QScrollBar):
            continue
        if wd.objectName().startswith("qt_") or isinstance(wd.parentWidget(), (QComboBox, QLineEdit)):
            continue
        if not _acc_name(wd):
            holes.append(f"{type(wd).__name__}#{wd.objectName() or '-'}")
    assert not holes, f"controls with no screen-reader name: {holes}"


def test_the_button_rows_spill_instead_of_flooring_the_pane(doc):
    """A plain HBox floors its card at the SUM of its buttons; at the 150% text size that sum was wider
    than the detail pane, which then grew an h-bar and clipped the time readout. The two button rows are
    SpillRows (floor = the wider half). Structural on purpose -- offscreen lies about every width."""
    from ff9mapkit.workspace import widgets
    for row, tail in ((doc.copy_row, doc.export_btn), (doc.import_row, doc.add_btn)):
        assert isinstance(row, widgets.SpillRow)
        assert row._tail is tail
        assert row.minimumSizeHint().width() < row.sizeHint().width(), "spilling must buy width back"


def test_the_transport_icons_exist_in_the_family(app):
    assert {"play", "pause", "stop", "sound"} <= set(icons.names())
    assert not icons.pixmap("stop", "#ffffff", 16).isNull() and not icons.pixmap("sound", "#ffffff", 46).isNull()


def test_the_sliders_carry_a_focus_ring_rule():
    from ff9mapkit.workspace import style
    css = style.qss(pick_palette("dark"))
    assert "QSlider#soundSeek, QSlider#soundVolume { border: 1px solid transparent" in css
    assert "QSlider#soundSeek:focus, QSlider#soundVolume:focus" in css


@pytest.fixture
def win(app):
    from ff9mapkit.workspace import anim
    from ff9mapkit.workspace.shell import Workspace, _apply_app_theme
    anim.set_enabled(False)
    _apply_app_theme(app, pick_palette("dark"))
    w = Workspace(pick_palette("dark"))
    w.show()
    app.processEvents()
    yield w
    w.close()


def test_the_shell_spends_the_tab_everywhere_a_tab_is_reached(app, win):
    """The call-site law: a tab the rail, the Home page and Ctrl-K do not reach is a tab nobody finds."""
    sd = win.sounds_doc
    i = win.tabs.indexOf(sd)
    assert i >= 0 and win.tabs.tabText(i) == "Sounds"
    assets = dict(win._rail_groups)["Assets"]
    assert sd in assets and assets.index(sd) == assets.index(win.models_doc) + 1, "beside Models"
    cmds = {label: fn for label, _kind, fn in win._command_index()}
    go = next(fn for label, fn in cmds.items() if label.startswith("Go to Sounds"))
    go()
    app.processEvents()
    assert win.tabs.currentWidget() is sd
    assert not sd.loaded() and sd._player is None, "reaching the tab loads nothing by itself"
    win.retheme(pick_palette("light"))                              # the tinted icons re-render, no crash
    assert sd.pal == win.pal


def _focus_delta(app, w) -> int:
    """Pixels that change when ``w`` takes keyboard focus -- measured from a baseline FORCED to rest
    (Qt focuses the first tab stop the moment a window shows; an unforced baseline reads that control
    as already focused and reports it as having no ring -- the a11y suite's own lesson)."""
    w.clearFocus()
    app.processEvents()
    assert not w.hasFocus()
    rest = w.grab().toImage()
    w.setFocus()
    app.processEvents()
    after = w.grab().toImage()
    w.clearFocus()
    app.processEvents()
    return sum(rest.pixelColor(x, y) != after.pixelColor(x, y)
               for y in range(rest.height()) for x in range(rest.width()))


def test_every_tab_stop_of_the_loaded_tab_shows_where_the_keyboard_is(app, win, tmp_path):
    """WCAG 2.4.7 for the LOADED browser. The Workspace-wide walk only ever reaches this tab's guide
    page, and `* { outline: 0 }` removes Fusion's own focus rect app-wide -- so a control here with no
    ring rule of its own would be silent, and the two id-scoped sliders are exactly that kind (a bare
    QSlider has no frame to recolour). Under the REAL app sheet; colour is font-independent, so
    offscreen is honest about it."""
    sd = win.sounds_doc
    rewire(sd, tmp_path)
    win.tabs.setCurrentWidget(sd)
    sd.load()
    sd.select("music", 9)
    win.activateWindow()                           # Qt paints focus only on the ACTIVE window
    win.raise_()
    app.processEvents()
    stops = {"search": sd.search, "category": sd.category, "bank": sd.bank, "unnamed only": sd.unnamed_only,
             "play on select": sd.autoplay, "list": sd.listw, "rescan": sd.rescan_btn, "play": sd.play_btn,
             "stop": sd.stop_btn, "seek": sd.seek, "loop": sd.loop_chk, "volume": sd.volume,
             "places": sd.places, "name": sd.name_edit, "tags": sd.tags_edit, "save name": sd.save_name_btn,
             "use description": sd.suggest_btn,
             "copy id": sd.copy_id_btn, "copy snippet": sd.copy_snip_btn, "export": sd.export_btn,
             "mod folder": sd.mod_edit, "browse": sd.mod_browse_btn, "replace": sd.replace_btn,
             "add": sd.add_btn}
    dead = [name for name, w in stops.items() if w.isEnabled() and _focus_delta(app, w) == 0]
    assert not dead, f"tab stops that show nothing when focused: {dead}"
    sd.shutdown()


# ============================================================================ the player tiers ===
def test_ffplay_is_started_headless_at_an_offset_and_volume():
    argv = audioplay.ffplay_argv("ffplay", "C:/a b/x.ogg", 12345, 0.25)
    assert argv[0] == "ffplay" and argv[-1] == "C:/a b/x.ogg"
    assert {"-nodisp", "-autoexit"} <= set(argv), "no window, and it exits at the end"
    assert argv[argv.index("-ss") + 1] == "12.345" and argv[argv.index("-volume") + 1] == "25"
    assert "-ss" not in audioplay.ffplay_argv("ffplay", "x.ogg", 0)
    loud = audioplay.ffplay_argv("ffplay", "x.ogg", 0, 7.0)
    assert loud[loud.index("-volume") + 1] == "100", "volume is clamped"


def test_no_audio_env_forces_the_silent_player(app, monkeypatch):
    monkeypatch.setenv("FF9MAPKIT_NO_AUDIO", "1")
    p = audioplay.make_player()
    assert isinstance(p, audioplay.NullPlayer)
    seen = []
    p.stateChanged.connect(seen.append)
    p.load("x.ogg", duration_ms=1000)
    p.play()
    p.seek(400)
    assert (p.state(), p.position(), p.duration()) == (audioplay.PLAYING, 400, 1000)
    p.pause()
    p.stop()
    assert seen == [audioplay.PLAYING, audioplay.PAUSED, audioplay.STOPPED] and p.position() == 0


def test_the_player_is_chosen_best_first_and_never_raises(app, monkeypatch):
    monkeypatch.setattr(audioplay, "audio_disabled", lambda: False)

    class _NoQt(audioplay.Player):
        def __init__(self, parent=None):
            raise ImportError("No module named 'PySide6.QtMultimedia'")   # the Essentials-only install

    class _Ffplay(audioplay.Player):
        name = "ffplay"

        def __init__(self, exe, parent=None):
            super().__init__(parent)
            self.exe = exe

    monkeypatch.setattr(audioplay, "QtPlayer", _NoQt)
    monkeypatch.setattr(audioplay, "FfplayPlayer", _Ffplay)
    monkeypatch.setattr(audioplay, "find_ffplay", lambda: "C:/ff/ffplay.exe")
    p = audioplay.make_player()
    assert p.name == "ffplay" and p.exe == "C:/ff/ffplay.exe"
    monkeypatch.setattr(audioplay, "find_ffplay", lambda: None)
    p = audioplay.make_player()
    assert isinstance(p, audioplay.ExternalPlayer) and not p.inline and not p.can_seek


def test_a_loop_region_must_be_a_real_forward_span(app):
    p = audioplay.NullPlayer()
    p.set_loop(1000, 5000)
    assert p._loop == (1000, 5000)
    for bad in ((5000, 1000), (0, 0), (None, 5000), (-5, 100)):
        p.set_loop(*bad)
        assert p._loop is None, bad
    p.set_loop(0, 5000)
    assert p._loop == (0, 5000), "a loop from the very start is a real loop"


def test_the_qt_multimedia_import_is_guarded_and_local():
    """The Essentials pin (pyproject): QtMultimedia is an Addons module, so it may be imported in
    exactly one place -- inside QtPlayer's constructor -- and never at module import."""
    import ast
    import inspect
    import ff9mapkit
    from pathlib import Path
    root = Path(inspect.getfile(ff9mapkit)).parent                  # the WHOLE package, not just the GUI
    sites = []
    for py in sorted(root.rglob("*.py")):
        text = py.read_text(encoding="utf-8")
        if "QtMultimedia" not in text:                              # cheap prefilter: parse only suspects
            continue
        for node in ast.walk(ast.parse(text)):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            mod = getattr(node, "module", None) or ""
            if "QtMultimedia" in mod or any("QtMultimedia" in a.name for a in node.names):
                sites.append((py.name, node.col_offset))
    assert [s[0] for s in sites] == ["audioplay.py"], sites
    assert sites[0][1] > 0, "the import sits inside a function, not at module top"


@pytest.mark.parametrize("ms,text", [(0, "0:00"), (84750, "1:24"), (999, "0:00"), (600000, "10:00"), (None, "0:00")])
def test_ms_format(ms, text):
    assert audioplay.format_ms(ms) == text
