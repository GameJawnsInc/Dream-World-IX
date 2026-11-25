"""The Sounds tab -- browse, HEAR, name and reuse every sound in the FF9 install.

The audio pillar's front door, shaped like the Models tab beside it: a browser on the left (every
music track, sound effect, stream and movie-audio track, searchable by name, file, id, tag or the
PLACE it plays in), and on the right the selected sound -- a transport that plays it, its length and
loop points, where the game uses it, a name box, and the DLL-free round trip (export the ``.ogg``,
replace it with your own audio, or add a brand-new track) streamed through the shell's job runner.

Three laws this surface is built around:

* **No I/O uninvited.** Construction and tab-show touch nothing: the catalog needs the install, so it
  is read behind the user's own *Load sounds* click (a ~5 s scan the first time, one JSON read after),
  on a worker. The audio player is not even CHOSEN until the first Play (:mod:`.audioplay` -- Qt's
  audio module is not part of the kit's Essentials pin, so the player is a guarded, tiered choice).
* **Every outside thing arrives through a seam.** ``catalog_fn`` / ``audio_fn`` / ``player_factory`` /
  ``names_path`` / ``mod_fn`` are constructor seams, and ``sync=True`` runs the two workers inline --
  so a test or a snap can never reach this machine's install, its speakers, or its names file.
* **The identity fence lives at the slot.** Audio for a sound is fetched on a worker after a short
  debounce (arrowing down a 2,800-row list must not queue 2,800 reads); the answer carries the request
  it belongs to and a stale one paints nothing.

Naming is the part only a person can do: most sound effects have no name anywhere, and nothing but
ears can give them one. *Name it* writes to a per-user overlay (:func:`soundcat.save_user_name`), and
Shift+Enter there saves and moves to the next sound -- hear, type, next.

What the kit CAN do without ears is describe: :func:`soundcat.lore` reads how the game uses each
sound (the battle effect that loads it, the monster whose cry it is, the door or Moogle or ambience
loop a field script plays it from) and the tab files every sound under a CATEGORY and leads an
unnamed row with that description -- in ITALICS, because a description is not a name, and "Unnamed
only" still lists it. A tag that names a category re-files the sound: the user's word wins.
"""
from __future__ import annotations

import dataclasses
import shutil
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea,
                               QSizePolicy, QSlider, QSplitter, QStackedLayout, QStyledItemDelegate,
                               QVBoxLayout, QWidget)

from .. import config, soundcat
from . import audioplay, icons, widgets

_DEBOUNCE_MS = 180                               # select -> fetch: let an arrow-key run settle first
_PLACE_ROWS = 5                                  # the where-used list's cap, in rows of its own font
_PLACE_CHROME = 5                                # the QSS well's border(1) + padding(4) per side
_PLACE_LIST_H = 130                              # ...and its cap before the first fill (a QListWidget's
#                                                  sizeHint is 256x192 whatever its row count)
_FIELDS_IN_TIP = 40                              # field ids listed in a place row's tooltip
_IMPORTABLE = ("music", "sfx")                   # what audio-import can replace / mint


class _RowsFitTheList(QStyledItemDelegate):
    """Rows exactly as wide as the list, never wider.

    A list row elides only inside the rect it is given, and a QListView gives a row its own size hint
    when that is wider than the viewport -- so a long row is laid out past the edge, an h-bar appears,
    and the id at the row's end (the part ElideMiddle exists to keep) is simply off-screen. Worse, with
    uniform item sizes the FIRST row's hint is everyone's, so it depended on which row happened to lead:
    fine with "Battle Theme" on top, broken under "Unnamed only" (snap-caught at the 150% text size).
    A width hint of 1 makes every row the viewport's width, so every long row elides in the middle."""

    def sizeHint(self, option, index):             # noqa: N802 (Qt override)
        hint = super().sizeHint(option, index)
        hint.setWidth(1)
        return hint


class SoundsDoc(QWidget):
    """Browse every FF9 sound, play the selection, name it, and run the audio round trip on it."""

    _load_done = Signal(object, str, str)        # (SoundMap | None, guide state, detail)
    _load_stage = Signal(str)                    # what a fresh read is doing right now
    _audio_done = Signal(object, object, object, str, str)   # (request, path, info, source, error)

    def __init__(self, pal, kit_root, *, run, problems=None, on_setup=None, catalog_fn=None,
                 audio_fn=None, player_factory=None, names_path=None, mod_fn=None, sync=False,
                 parent=None):
        super().__init__(parent)
        self.pal = pal
        self.kit = str(kit_root)
        self._run = run
        self._problems = problems
        self.on_setup = on_setup
        self._catalog_fn = catalog_fn or (
            lambda force: soundcat.build_map(force=force, progress=self._stage))
        self._audio_fn = audio_fn or (lambda s, mod: soundcat.playable(s.resource_id, mod_folder=mod))
        self._player_factory = player_factory or (lambda: audioplay.make_player(self))
        self._names_path = names_path            # None -> the real per-user overlay, resolved at CALL time
        self._mod_fn = mod_fn or self._detect_mod
        self._sync = bool(sync)
        self._sm = None                          # the loaded soundcat.SoundMap
        self._index = None                       # soundcat.LoreIndex: the shared lookups of one load
        self._entries = []                       # every soundcat.Sound, names + lore applied
        # a FONT WITH ONLY ITALIC SET: the item delegate resolves it against the list's own font at
        # paint time, so a described row follows the text-size dial instead of freezing a point size
        self._italic = QFont()
        self._italic.setItalic(True)
        self._overridden = set()                 # lowercased ResourceIDs the mod folder replaces
        self._items = {}                         # sound key -> QListWidgetItem (the CURRENT filter's rows)
        self._current = None                     # the selected soundcat.Sound
        self._audio = None                       # (path, info, source) once fetched for _current
        self._req = None                         # the in-flight audio request: (key, generation)
        self._gen = 0
        self._pending_play = False
        self._player = None                      # built on the first Play, never before
        self._busy = False
        self._seek_guard = False                 # True while the slider is being set by the clock
        self._failed = False                     # the last play ended in a reported failure
        self._guide_state = ("start", "")
        self._load_done.connect(self._finish_load)
        self._load_stage.connect(self._on_stage)
        self._audio_done.connect(self._on_audio)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._fetch_audio)
        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._guide_page = self._build_guide(*self._guide_state)
        self._stack.addWidget(self._guide_page)
        self._browser_page = self._build_browser()
        self._stack.addWidget(self._browser_page)
        self._stack.setCurrentWidget(self._guide_page)

    # ------------------------------------------------------------------ the guide (pre-load) page
    def _build_guide(self, state, detail):
        """One teaching empty-state per situation. Rebuilt per state and per retheme (the glyph pixmap
        is palette-tinted at build time)."""
        glyph = icons.pixmap("sound", self.pal["muted"], 46)
        if state == "nogame":
            acts = [("Open Setup && health…", self.on_setup) if self.on_setup else None,
                    ("Try again", self.load)]            # && -- a lone & is eaten as a mnemonic
            return widgets.empty_state("", "FF9 install not found",
                                       teach="The sounds are read from your own FF9 install. Point the "
                                             "kit at it in Setup & health, then load again.",
                                       actions=acts, icon_pixmap=glyph)
        if state == "error":
            return widgets.empty_state("", "The sounds could not be read",
                                       teach=detail or "Unknown error.",
                                       actions=[("Try again", self.load)], icon_pixmap=glyph)
        if state == "busy":
            return widgets.empty_state("", detail or "Reading your install…",
                                       teach="The sound tables, every field script, the battle scenes and "
                                             "each sound's own header — to learn what each sound is and "
                                             "where it plays. About fifteen seconds the first time.",
                                       icon_pixmap=glyph)
        return widgets.empty_state(                # "start" -- the front door
            "", "Hear every sound in your FF9 install",
            teach="Music, sound effects, ambience and movie audio — sorted into categories and "
                  "searchable by name or by the place it plays. Loading reads your install (about "
                  "fifteen seconds the first time, instant after). It only reads — nothing in the game "
                  "is changed.",
            actions=[("Load sounds", self.load)], icon_pixmap=glyph)

    def _show_guide(self, state, detail=""):
        self._guide_state = (state, detail)
        old = self._guide_page
        self._guide_page = self._build_guide(state, detail)
        self._stack.addWidget(self._guide_page)
        self._stack.setCurrentWidget(self._guide_page)
        self._stack.removeWidget(old)
        old.deleteLater()

    # ------------------------------------------------------------------ the browser page
    def _build_browser(self):
        page = QWidget()
        root = QHBoxLayout(page)
        root.setContentsMargins(10, 10, 10, 10)
        split = QSplitter()
        root.addWidget(split)

        # ---- left: the browser ----
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 6, 0)
        self.search = QLineEdit()
        self.search.setAccessibleName("Search sounds")
        self.search.setPlaceholderText("Search name, id, tag or place…")
        self.search.setToolTip("Matches a sound's name, file name, id, tags, bank, the places it "
                               "plays, and what the kit worked out about it — try vivi, door, fire, "
                               "death cry, loop, or lindblum.")
        self.search.textChanged.connect(self._refill)
        lv.addWidget(self.search)
        # ONE combo per row, each the pane's full width: their items are sentences-long ("SE06 · Dali,
        # Ice Cavern, Cargo Ship"), and a combo sized to its longest item would floor the pane. So the
        # size hint is pinned to a few characters and the LAYOUT stretches them instead.
        self.category = QComboBox()
        self.category.setAccessibleName("Filter sounds by category")
        self.category.setToolTip("What a sound is FOR, worked out from how the game uses it — or from "
                                 "your own tags: a tag that names a category files the sound there.")
        self.category.addItem("All sounds", None)
        self.category.currentIndexChanged.connect(self._on_category)
        self.bank = QComboBox()
        self.bank.setAccessibleName("Filter sounds by bank")
        self.bank.setToolTip("A bank is the folder a sound ships in. SE05 to SE15 are area sets — each "
                             "holds the sounds of a few places — and SE50 and up are battle effects.")
        self.bank.addItem("All banks", None)
        self.bank.currentIndexChanged.connect(self._refill)
        for combo in (self.category, self.bank):
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(8)
            lv.addWidget(combo)
        frow = QHBoxLayout()
        self.unnamed_only = QCheckBox("Unnamed only")
        self.unnamed_only.setToolTip("Keep the sounds nobody has named yet — the ones to listen to "
                                     "and name.")
        self.unnamed_only.toggled.connect(self._refill)
        frow.addWidget(self.unnamed_only)
        self.autoplay = QCheckBox("Play on select")
        self.autoplay.setToolTip("Play each sound as you select it — arrow down the list to audition.")
        frow.addWidget(self.autoplay)
        frow.addStretch(1)
        lv.addLayout(frow)
        self.listw = QListWidget()
        self.listw.setAccessibleName("Sound catalog")
        self.listw.setUniformItemSizes(True)
        # elide in the MIDDLE: a long title then keeps its start AND the id at the row's end (elided on
        # the right, "Assault of the White Dragon…" lost the one number a modder types -- snap-caught)
        self.listw.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.listw.setItemDelegate(_RowsFitTheList(self.listw))    # ...which needs rows the list's width
        self.listw.currentItemChanged.connect(self._on_select)
        lv.addWidget(self.listw, 1)
        foot = QHBoxLayout()
        self.count_lbl = widgets.ElideLabel("", "muted")
        self.count_lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        foot.addWidget(self.count_lbl, 1)
        self.rescan_btn = QPushButton("Rescan")
        self.rescan_btn.setProperty("role", "quiet")
        self.rescan_btn.setToolTip("Read the install again — after a game update, or to pick up tracks "
                                   "a deploy just added to the mod folder.")
        self.rescan_btn.clicked.connect(lambda: self.load(force=True))
        foot.addWidget(self.rescan_btn)
        lv.addLayout(foot)
        split.addWidget(left)

        # ---- right: the selected sound (scrolled) ----
        right_host = QWidget()
        rv = QVBoxLayout(right_host)
        rv.setContentsMargins(10, 0, 0, 0)
        self.d_title = QLabel("Pick a sound")
        self.d_title.setTextFormat(Qt.TextFormat.PlainText)
        self.d_title.setProperty("role", "head")
        self.d_title.setWordWrap(True)           # a long title must wrap, never push the pane wide
        rv.addWidget(self.d_title)
        self.d_sub = QLabel("")
        self.d_sub.setTextFormat(Qt.TextFormat.PlainText)
        self.d_sub.setProperty("role", "muted")
        self.d_sub.setWordWrap(True)
        rv.addWidget(self.d_sub)
        rv.addWidget(self._player_box())
        rv.addWidget(self._places_box())
        rv.addWidget(self._name_box())
        rv.addWidget(self._use_box())
        rv.addStretch(1)

        right = QScrollArea()
        right.setFrameShape(QFrame.Shape.NoFrame)
        right.setWidgetResizable(True)
        # AsNeeded, not AlwaysOff: under widgetResizable an h-bar forced off does not scroll, it CLIPS
        right.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        right.setWidget(right_host)
        split.addWidget(right)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        split.setSizes([360, 620])
        self._set_selected(False)
        return page

    def _player_box(self):
        box = widgets.section("Listen")
        v = box.content_layout
        self.transport = QWidget()
        # a bare QWidget paints the PAGE colour over the card's fill (the sheet's universal QWidget
        # rule) -- snap-caught as a dark band behind the transport. Exact-class form, never the bare one.
        self.transport.setStyleSheet(widgets.TRANSPARENT)
        trow = QHBoxLayout(self.transport)
        trow.setContentsMargins(0, 0, 0, 0)
        trow.setSpacing(8)
        # SVG icons, never the unicode media glyphs (they fall back to the Windows emoji face)
        self.play_btn = QPushButton()
        self.play_btn.setProperty("role", "quiet")
        self.play_btn.setIcon(icons.icon("play", self.pal["text"]))
        self.play_btn.setAccessibleName("Play or pause the selected sound")
        self.play_btn.setToolTip("Play / pause")
        self.play_btn.clicked.connect(self.toggle_play)
        trow.addWidget(self.play_btn)
        self.stop_btn = QPushButton()
        self.stop_btn.setProperty("role", "quiet")
        self.stop_btn.setIcon(icons.icon("stop", self.pal["text"]))
        self.stop_btn.setAccessibleName("Stop the selected sound")
        self.stop_btn.setToolTip("Stop and rewind")
        self.stop_btn.clicked.connect(self.stop_audio)
        trow.addWidget(self.stop_btn)
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setObjectName("soundSeek")     # carries the reserved focus ring (style.py)
        self.seek.setAccessibleName("Playback position")
        self.seek.setAccessibleDescription("Seek within the selected sound")
        self.seek.setRange(0, 0)
        self.seek.setMinimumWidth(120)           # never starved to a sliver by the time readout
        self.seek.valueChanged.connect(self._on_seek_value)
        self.seek.sliderReleased.connect(self._on_seek_released)
        trow.addWidget(self.seek, 1)
        # a PLAIN label, never an ElideLabel: the readout is a dozen fixed-format characters, and
        # eliding it ("0:31 / 1:...") loses exactly the number it exists to show (snap-caught)
        self.time_lbl = QLabel("")
        self.time_lbl.setTextFormat(Qt.TextFormat.PlainText)
        self.time_lbl.setProperty("role", "muted")
        self.time_lbl.setProperty("mono", True)
        trow.addWidget(self.time_lbl)
        v.addWidget(self.transport)
        orow = QHBoxLayout()
        self.loop_chk = QCheckBox("Loop")
        self.loop_chk.setToolTip("Repeat the track's own loop region, the way the game does. A preview: "
                                 "the jump back is close to, not sample-exact with, the in-game loop.")
        self.loop_chk.toggled.connect(self._apply_loop)
        orow.addWidget(self.loop_chk)
        orow.addSpacing(8)
        _l_vol = QLabel("Volume")
        _l_vol.setProperty("role", "muted")
        orow.addWidget(_l_vol)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setObjectName("soundVolume")
        self.volume.setAccessibleName("Preview volume")
        self.volume.setRange(0, 100)
        self.volume.setValue(60)
        self.volume.setMinimumWidth(80)
        self.volume.valueChanged.connect(self._on_volume)
        _l_vol.setBuddy(self.volume)
        orow.addWidget(self.volume, 1)
        orow.addStretch(2)
        v.addLayout(orow)
        self.d_facts = QLabel("")
        self.d_facts.setTextFormat(Qt.TextFormat.PlainText)
        self.d_facts.setWordWrap(True)
        v.addWidget(self.d_facts)
        # a NOTICE, not a caption: this line reports (reading / playing / failed), and the sheet
        # deliberately has no error state at the caption rung ("never demote a diagnostic")
        self.note = widgets.notice("Pick a sound, then press Play.")
        v.addWidget(self.note)
        return box

    def _places_box(self):
        box = widgets.section("What it is, where it plays")
        v = box.content_layout
        self.about = QLabel("")                    # the kit's own read of the sound: lore's sentences
        self.about.setTextFormat(Qt.TextFormat.PlainText)
        self.about.setWordWrap(True)
        v.addWidget(self.about)
        self.places_sum = QLabel("")
        self.places_sum.setTextFormat(Qt.TextFormat.PlainText)
        self.places_sum.setWordWrap(True)
        v.addWidget(self.places_sum)
        self.places = QListWidget()
        self.places.setAccessibleName("Places that use this sound")
        self.places.setMaximumHeight(_PLACE_LIST_H)
        v.addWidget(self.places)
        return box

    def _name_box(self):
        box = widgets.section("Name it")
        v = box.content_layout
        nrow = QHBoxLayout()
        _l_name = QLabel("Name:")
        nrow.addWidget(_l_name)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("what you hear — e.g. Wooden door creak")
        _l_name.setBuddy(self.name_edit)
        self.name_edit.installEventFilter(self)
        nrow.addWidget(self.name_edit, 1)
        v.addLayout(nrow)
        trow = QHBoxLayout()
        _l_tags = QLabel("Tags:")
        trow.addWidget(_l_tags)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("comma-separated — door, wood")
        self.tags_edit.setToolTip("Search words of your own. A tag that names a category — door, "
                                  "pickup, npc, menu, ambience, monster, spell… — also files the sound "
                                  "under it.")
        _l_tags.setBuddy(self.tags_edit)
        self.tags_edit.installEventFilter(self)
        trow.addWidget(self.tags_edit, 1)
        v.addLayout(trow)
        brow = QHBoxLayout()                       # its own row: beside Tags it squeezed the box
        self.save_name_btn = QPushButton("Save name")
        self.save_name_btn.clicked.connect(lambda: self.save_name())
        brow.addWidget(self.save_name_btn)
        self.suggest_btn = QPushButton("Use the description")
        self.suggest_btn.setProperty("role", "quiet")
        self.suggest_btn.setToolTip("Start the name from what the kit worked out about this sound, "
                                    "then correct it to what you actually hear.")
        self.suggest_btn.clicked.connect(self.use_description)
        brow.addWidget(self.suggest_btn)
        brow.addStretch(1)
        v.addLayout(brow)
        self.name_status = widgets.notice("")    # "Saved to ..." / a failed write -- a report
        self.name_status.hide()
        v.addWidget(self.name_status)
        v.addWidget(widgets.caption("Enter saves. Shift+Enter saves and moves to the next sound. "
                                    "Names are kept in your own names file and survive kit updates."))
        return box

    def _use_box(self):
        box = widgets.section("Use it in a mod")
        v = box.content_layout
        self.copy_id_btn = QPushButton("Copy id")
        self.copy_id_btn.clicked.connect(self.copy_id)
        self.copy_snip_btn = QPushButton("Copy snippet")
        self.copy_snip_btn.setToolTip("The line that plays this sound from a field.toml — "
                                      "[music] song = N for music, sfx = N for a sound effect.")
        self.copy_snip_btn.clicked.connect(self.copy_snippet)
        self.export_btn = QPushButton("Export .ogg…")
        self.export_btn.setToolTip("Save the sound as a plain Ogg Vorbis file any audio editor opens.")
        self.export_btn.clicked.connect(self.on_export)
        self.copy_row = self._spill_row([self.copy_id_btn, self.copy_snip_btn], self.export_btn)
        v.addWidget(self.copy_row)

        dep = QHBoxLayout()
        _l_dep = QLabel("Mod folder:")
        dep.addWidget(_l_dep)
        self.mod_edit = QLineEdit()
        self.mod_edit.setPlaceholderText("<game>/FF9CustomMap")
        self.mod_edit.setToolTip("Where a replaced or added track is written — and the folder whose own "
                                 "replacements and added tracks this list shows.")
        _l_dep.setBuddy(self.mod_edit)
        self.mod_edit.editingFinished.connect(self._on_mod_changed)
        dep.addWidget(self.mod_edit, 1)
        self.mod_browse_btn = QPushButton("Browse…")
        self.mod_browse_btn.setAccessibleName("Browse for the mod folder")
        self.mod_browse_btn.clicked.connect(self.browse_mod)
        dep.addWidget(self.mod_browse_btn)
        v.addLayout(dep)

        self.replace_btn = QPushButton("Replace with my audio…")
        self.replace_btn.setToolTip("Put your own audio file (wav / mp3 / ogg / flac) in this sound's "
                                    "place: every field that plays it plays yours instead.")
        self.replace_btn.clicked.connect(self.on_replace)
        self.add_btn = QPushButton("Add as a new track…")
        self.add_btn.setToolTip("Add your own audio file as a brand-new id of this kind, leaving every "
                                "existing sound alone. The Output panel prints the new id.")
        self.add_btn.clicked.connect(self.on_add)
        self.import_row = self._spill_row([self.replace_btn], self.add_btn)
        v.addWidget(self.import_row)
        self.use_note = widgets.caption(
            "A replaced or added track is heard after a game RELAUNCH — audio loads at startup. Replacing "
            "also sets PriorityToOGG = 1 in Memoria.ini (backed up first) so your file wins. Needs ffmpeg.")
        v.addWidget(self.use_note)
        self._job_buttons = [self.replace_btn, self.add_btn]
        return box

    @staticmethod
    def _spill_row(lead_buttons, tail):
        """A button row that SPILLS its last button to a second line when the pane is narrow. A plain
        HBox floors its card at the SUM of its buttons: at the 150% text size the two rows here put a
        522px floor under a 500px pane, and a pane under its content's floor grows an h-bar and clips
        the transport's time readout (snap-caught). Spilled, the floor is the wider half."""
        lead = QWidget()
        lead.setStyleSheet(widgets.TRANSPARENT)    # a bare QWidget would paint the page over the card
        h = QHBoxLayout(lead)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        for b in lead_buttons:
            h.addWidget(b)
        h.addStretch(1)
        return widgets.SpillRow(lead, tail, margins=(0, 0, 0, 0))

    # ------------------------------------------------------------------ loading the catalog
    def load(self, *, force=False, sync=None):
        """Read the sound catalog -- always a user gesture, never the shell's. Runs on a worker;
        ``sync=True`` (or the constructor's) is the deterministic lane for tests and snaps."""
        if self._busy:
            return
        self._busy = True
        self.stop_audio()
        self.rescan_btn.setEnabled(False)
        self.rescan_btn.setText("Scanning…")
        if self._sm is None:
            self._show_guide("busy")
        if self._sync if sync is None else sync:
            self._load_worker(force)
            return
        threading.Thread(target=self._load_worker, args=(force,), name="ff9-sounds-load",
                         daemon=True).start()

    def _load_worker(self, force):
        try:
            sm, state, detail = self._catalog_fn(force), "", ""
        except config.ConfigError as e:
            sm, state, detail = None, "nogame", str(e)
        except Exception as e:                     # noqa: BLE001 -- surfaced on the GUI thread
            sm, state, detail = None, "error", str(e)
        try:
            self._load_done.emit(sm, state, detail)    # RuntimeError-guarded: the doc may be dead
        except RuntimeError:
            pass

    def _stage(self, text):
        """The catalog reader's progress callback (it runs on the worker thread)."""
        try:
            self._load_stage.emit(str(text))
        except RuntimeError:                       # the doc died mid-read
            pass

    def _on_stage(self, text):
        if not self._busy:
            return
        if self._sm is None:
            self._show_guide("busy", text)         # the first load: the guide names the stage
        else:
            self.count_lbl.setText(text)           # a rescan: the list is up, the footer says it

    def _finish_load(self, sm, state, detail):
        self._busy = False
        self.rescan_btn.setEnabled(True)
        self.rescan_btn.setText("Rescan")
        if sm is None:
            if self._sm is None:
                self._show_guide(state or "error", detail)
            else:                                  # a failed RESCAN keeps the list that is already up
                self._say(f"The rescan failed — {detail or 'unknown error'}", "error")
            return
        self._sm = sm
        self._index = soundcat.LoreIndex(sm)
        if not self.mod_edit.text().strip():
            mod = self._mod_fn()
            if mod:
                self.mod_edit.setText(str(mod))
        self._rebuild_entries()
        self._stack.setCurrentWidget(self._browser_page)

    def _detect_mod(self):
        from ..editor import jobs
        return jobs.detect_game_mod(Path(self.kit).parent)    # keyed on THIS checkout's pin

    def loaded(self) -> bool:
        return self._sm is not None

    def _mod(self):
        m = self.mod_edit.text().strip().strip('"')
        return m or None

    def _scan_overrides(self, mod):
        """The lowercased ResourceIDs the mod folder ships a loose Ogg for (one directory walk)."""
        out = set()
        if not mod:
            return out
        root = Path(mod) / "StreamingAssets" / "Assets" / "Resources" / "Sounds"
        try:
            for p in root.rglob("*.ogg"):
                out.add(p.relative_to(root).with_suffix("").as_posix().lower())
        except OSError:
            pass
        return out

    def _rebuild_entries(self):
        """Re-derive the entry list from the map + the names files + the mod folder, then refill."""
        if self._sm is None:
            return
        mod = self._mod()
        names = soundcat.load_names(self._names_path)
        self._entries = soundcat.sounds(self._sm, names, index=self._index,
                                        extra_rows=soundcat.mod_custom_rows(mod, self._sm))
        self._overridden = self._scan_overrides(mod)
        self._refill_categories()
        self._refill_banks()
        self._refill()
        if self._current is not None:              # the selection's own entry may have changed under it
            fresh = next((s for s in self._entries if s.key == self._current.key), None)
            if fresh is not None:
                self._current = fresh
                self._fill_detail(fresh)

    # ------------------------------------------------------------------ the list
    def _on_category(self, *_a):
        self._refill_banks()
        self._refill()

    def _refill_categories(self):
        """The category filter, with a count beside each -- only the categories that have a sound."""
        keep = self.category.currentData()
        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem(f"All sounds  ({len(self._entries):,})", None)
        for key, label, n in soundcat.category_counts(self._entries):
            self.category.addItem(f"{label}  ({n:,})", key)
        i = self.category.findData(keep) if keep is not None else 0
        self.category.setCurrentIndex(i if i >= 0 else 0)
        self.category.blockSignals(False)

    def _refill_banks(self):
        """The bank filter for the current category, each bank saying what it holds."""
        keep = self.bank.currentData()
        self.bank.blockSignals(True)
        self.bank.clear()
        self.bank.addItem("All banks", None)
        for b in soundcat.banks(self._entries, category=self.category.currentData()):
            self.bank.addItem(soundcat.bank_label(b, self._index), b)
        i = self.bank.findData(keep) if keep is not None else 0
        self.bank.setCurrentIndex(i if i >= 0 else 0)
        self.bank.blockSignals(False)

    def _row_text(self, s):
        text = s.label
        if s.custom:
            text += "  ·  added"
        elif s.resource_id.lower() in self._overridden:
            text += "  ·  replaced"
        return text

    def _refill(self, *_a):
        """Rebuild the rows for the current filter. The selection is restored SILENTLY: a keystroke in
        the search box must not re-arm (and so stop) the sound that is playing."""
        entries = soundcat.filter_sounds(
            self._entries, self.search.text(), category=self.category.currentData(),
            bank=self.bank.currentData(), unnamed_only=self.unnamed_only.isChecked())
        keep = self._current.key if self._current is not None else None
        self.listw.blockSignals(True)
        self.listw.clear()
        self._items = {}
        for s in entries:
            it = QListWidgetItem(self._row_text(s))
            it.setData(Qt.ItemDataRole.UserRole, s.key)
            it.setToolTip(s.full_label)
            if s.described:                        # a description, not a name: italics say so
                it.setFont(self._italic)
            self.listw.addItem(it)
            self._items[s.key] = it
        if keep is not None and keep in self._items:
            self.listw.setCurrentItem(self._items[keep])
        self.listw.blockSignals(False)
        total = len(self._entries)
        unnamed = sum(1 for s in self._entries if not s.title)
        described = sum(1 for s in self._entries if s.described)
        shown = f"{len(entries):,} of {total:,}" if len(entries) != total else f"{total:,} sounds"
        self.count_lbl.setText(f"{shown}  ·  {unnamed:,} unnamed")
        tip = (f"{described:,} of the unnamed sounds are DESCRIBED from how the game uses them — those "
               "rows are in italics. A description is not a name: only listening gives one.")
        if self._sm is not None and self._sm.gaps:
            tip += " Could not be read on this install: " + "; ".join(self._sm.gaps) + "."
        self.count_lbl.setToolTip(tip)

    def _on_select(self, item, _prev=None):
        if item is None:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        s = next((e for e in self._entries if e.key == tuple(key)), None)
        if s is None:
            return
        self._current = s
        self._fill_detail(s)
        self._arm(play=self.autoplay.isChecked())

    def select(self, kind, sound_id) -> bool:
        """Select a sound by identity (tests, snaps, a future 'open in Sounds' link). False if the
        current filter hides it."""
        it = self._items.get((kind, int(sound_id)))
        if it is None:
            return False
        self.listw.setCurrentItem(it)
        return True

    # ------------------------------------------------------------------ the detail pane
    def _set_selected(self, on):
        """Everything that acts on 'the selected sound', enabled as ONE decision."""
        for w in (self.play_btn, self.stop_btn, self.seek, self.loop_chk, self.name_edit, self.tags_edit,
                  self.save_name_btn, self.suggest_btn, self.copy_id_btn, self.copy_snip_btn,
                  self.export_btn, self.replace_btn, self.add_btn):
            w.setEnabled(bool(on))

    def _fill_detail(self, s):
        self._set_selected(True)
        self.d_title.setText(s.title or s.stem)
        what = soundcat.CATEGORY_LABEL.get(s.category) or soundcat.KIND_LABEL[s.kind]
        sub = f"{what}  ·  id {s.id}  ·  {s.resource_id}"
        if s.custom:
            sub += "  ·  added by this mod folder"
        elif s.resource_id.lower() in self._overridden:
            sub += "  ·  replaced in this mod folder"
        self.d_sub.setText(sub)
        self.name_edit.setText(s.title)
        self.tags_edit.setText(", ".join(s.tags))
        self._name_say("")
        importable = s.kind in _IMPORTABLE
        for b in (self.replace_btn, self.add_btn):
            b.setEnabled(importable)
        self.copy_snip_btn.setEnabled(importable)
        self.suggest_btn.setEnabled(bool(s.describe))
        # _set_selected enabled these wholesale; two of them answer to facts it does not know
        self.loop_chk.setEnabled(self._audio is not None and self._loop_ms(self._audio[1]) is not None)
        if self._player is not None and not self._player.can_seek:
            self.seek.setEnabled(False)
        self._fill_places(s)

    def _fill_places(self, s):
        join = self._index.join if self._index is not None else None
        groups = soundcat.places(self._sm, s.kind, s.id, join=join) if self._sm else []
        self.places.clear()
        for g in groups:
            n = len(g["fields"])
            it = QListWidgetItem(f"{g['name'] or 'Other fields'}  ·  {n} field{'s' if n != 1 else ''}")
            ids = ", ".join(str(f) for f in g["fields"][:_FIELDS_IN_TIP])
            more = f" … and {n - _FIELDS_IN_TIP} more" if n > _FIELDS_IN_TIP else ""
            it.setToolTip(f"field id{'s' if n != 1 else ''} {ids}{more}")
            self.places.addItem(it)
        self.places.setVisible(bool(groups))
        if groups:                                # cap on WHOLE rows of the list's own font (CALIBRE)
            row_h = self.places.sizeHintForRow(0)
            if row_h > 0:
                self.places.setMaximumHeight(row_h * min(len(groups), _PLACE_ROWS) + 2 * _PLACE_CHROME)
        if groups:
            nf = sum(len(g["fields"]) for g in groups)
            self.places_sum.setText(f"Named by {nf} field script{'s' if nf != 1 else ''} across "
                                    f"{len(groups)} place{'s' if len(groups) != 1 else ''}.")
        self.places_sum.setVisible(bool(groups))
        self.about.setText(self._about_text(s))

    def _about_text(self, s) -> str:
        """The kit's read of the sound: what it looks like (when unnamed) or is used as (when named),
        then lore's own sentences. Never empty -- "nothing names it" is itself the finding."""
        if s.custom:
            return "Added by this mod folder — it plays wherever your own fields ask for its id."
        lr = soundcat.lore(self._sm, s, self._index) if self._sm is not None else None
        lines = []
        if s.describe:
            lines.append(f"{'Used as' if s.title else 'Looks like'}: {s.describe}")
        elif s.hint and not s.title:
            lines.append(f"Unplaced — {s.hint}.")
        lines += list(lr.notes) if lr is not None else []
        return "\n".join(lines) or "Nothing in the game's data says what this is."

    def _fill_facts_from_entry(self, s):
        """What the catalog already knows, shown the moment a row is picked -- the audio itself
        (its sample rate, its loop points in time) refines this when it lands."""
        if not s.seconds:
            self.d_facts.setText("")
            return
        bits = [f"Length {soundcat.format_seconds(s.seconds)}"]
        facts = self._sm.audio.get(s.resource_id) if self._sm is not None else None
        if facts and facts[2]:
            bits.append({1: "mono", 2: "stereo"}.get(facts[2], f"{facts[2]} channels"))
        self.d_facts.setText("  ·  ".join(bits) + "\n" + ("Loops" if s.loops else "Plays once (no loop points)"))

    def _fill_facts(self, info, source):
        lines = []
        secs = float(info.get("seconds") or 0.0)
        bits = []
        if secs:
            bits.append(f"Length {soundcat.format_seconds(secs)}")
        if info.get("rate"):
            bits.append(f"{info['rate']} Hz")
        ch = info.get("channels")
        if ch:
            bits.append({1: "mono", 2: "stereo"}.get(ch, f"{ch} channels"))
        if bits:
            lines.append("  ·  ".join(bits))
        loop = self._loop_ms(info)
        if loop is not None:
            lines.append(f"Loops from {audioplay.format_ms(loop[0])} to {audioplay.format_ms(loop[1])} "
                         f"(samples {info['loop_start']}–{info['loop_end']})")
        elif secs:
            lines.append("Plays once (no loop points)")
        if source == "override":
            lines.append("This is the mod folder's replacement, not the game's own audio.")
        self.d_facts.setText("\n".join(lines))

    @staticmethod
    def _loop_ms(info):
        rate, ls, le = info.get("rate") or 0, info.get("loop_start") or 0, info.get("loop_end") or 0
        if not rate or le <= ls:
            return None
        return int(ls * 1000 / rate), int(le * 1000 / rate)

    def _say(self, text, state=""):
        self.note.setText(text)
        widgets.set_state(self.note, state)

    def _name_say(self, text, state=""):
        self.name_status.setText(text)
        widgets.set_state(self.name_status, state)
        self.name_status.setVisible(bool(text))

    # ------------------------------------------------------------------ fetching + playing the audio
    def _arm(self, *, play):
        """Point the transport at the current sound: silence the old one, then fetch the new one's
        audio (debounced on a worker -- or inline under ``sync``)."""
        self.stop_audio()
        self._audio = None
        self._pending_play = bool(play)
        self._gen += 1
        self._req = None
        self._set_duration(int((self._current.seconds if self._current is not None else 0) * 1000))
        if self._current is not None:
            self._fill_facts_from_entry(self._current)
        self.loop_chk.setEnabled(False)
        self._say("Reading the audio…")
        if self._sync:
            self._fetch_audio()
        else:
            self._debounce.start()

    def _fetch_audio(self):
        s = self._current
        if s is None:
            return
        req = (s.key, self._gen)
        self._req = req
        mod = self._mod()
        if self._sync:
            self._audio_worker(req, s, mod)
        else:
            threading.Thread(target=self._audio_worker, args=(req, s, mod), name="ff9-sounds-audio",
                             daemon=True).start()

    def _audio_worker(self, req, s, mod):
        try:
            path, info, source = self._audio_fn(s, mod)
            err = ""
        except Exception as e:                     # noqa: BLE001 -- surfaced on the GUI thread
            path, info, source, err = None, {}, "", str(e) or type(e).__name__
        try:
            self._audio_done.emit(req, path, info, source, err)
        except RuntimeError:
            pass

    def _on_audio(self, req, path, info, source, err):
        if req != self._req or self._current is None or req != (self._current.key, self._gen):
            return                                 # a superseded selection's late answer paints nothing
        self._req = None
        if err or path is None:
            self._pending_play = False
            self._say(f"No audio for this sound — {err or 'nothing to play'}", "warn")
            for w in (self.play_btn, self.stop_btn, self.seek, self.loop_chk, self.export_btn):
                w.setEnabled(False)
            return
        self._audio = (str(path), dict(info or {}), source)
        self._fill_facts(self._audio[1], source)
        self._set_duration(int(float(self._audio[1].get("seconds") or 0.0) * 1000))
        self.loop_chk.setEnabled(self._loop_ms(self._audio[1]) is not None)
        self._say("Ready — press Play.")
        if self._pending_play:
            self._pending_play = False
            self._play()

    def _ensure_player(self):
        if self._player is None:
            p = self._player_factory()
            p.positionChanged.connect(self._on_position)
            p.durationChanged.connect(self._on_duration)
            p.stateChanged.connect(self._on_state)
            p.failed.connect(self._on_failed)
            p.set_volume(self.volume.value() / 100.0)
            self._player = p
            self.seek.setEnabled(bool(p.can_seek))
        return self._player

    def _play(self):
        if self._audio is None:
            return
        p = self._ensure_player()
        path, info, _source = self._audio
        self._failed = False
        start = 0
        if p.path() != path or p.state() == audioplay.STOPPED:
            start = self.seek.value()              # a thumb parked before Play is where it starts
            p.load(path, duration_ms=int(float(info.get("seconds") or 0.0) * 1000))
        self._apply_loop()
        p.play()
        if start > 0 and p.can_seek:
            p.seek(start)
        if not p.inline:
            self._say(f"Opened in {p.label}. Install ffmpeg (it ships ffplay) to hear sounds here "
                      "in the app.")
        elif p.name == "ffplay":
            self._say("Playing through ffplay — the position shown is an estimate.")
        elif p.name == "null":
            self._say(p.label)
        else:
            self._say("Playing.")

    def toggle_play(self):
        """The Play button: play, pause, or resume -- and if the audio is still being read, play it
        the moment it lands."""
        if self._current is None:
            return
        p = self._player
        if p is not None and p.state() == audioplay.PLAYING:
            p.pause() if p.can_pause else p.stop()
            return
        if self._audio is None:
            self._pending_play = True
            if self._req is None and not self._debounce.isActive():
                self._fetch_audio()
            return
        self._play()

    def stop_audio(self):
        self._debounce.stop()
        self._pending_play = False
        if self._player is not None:
            self._player.stop()
        self._set_position(0)

    def _apply_loop(self, *_a):
        if self._player is None or self._audio is None:
            return
        loop = self._loop_ms(self._audio[1]) if self.loop_chk.isChecked() else None
        if loop is None:
            self._player.set_loop()
        else:
            self._player.set_loop(*loop)

    def _on_volume(self, value):
        if self._player is not None:
            self._player.set_volume(value / 100.0)

    def _set_duration(self, ms):
        self._seek_guard = True
        self.seek.setRange(0, max(0, int(ms)))
        self.seek.setValue(0)
        self._seek_guard = False
        self._show_time(0)

    def _set_position(self, ms):
        if self.seek.isSliderDown():               # the user's thumb outranks the clock
            return
        self._seek_guard = True
        self.seek.setValue(min(int(ms), self.seek.maximum()))
        self._seek_guard = False
        self._show_time(ms)

    def _show_time(self, ms):
        total = self.seek.maximum()
        if not total:
            text = ""
        elif total < 10000:                        # a short effect: m:ss would read "0:00 / 0:00"
            text = f"{max(0, int(ms)) / 1000:.1f} / {total / 1000:.1f}s"
        else:
            text = f"{audioplay.format_ms(ms)} / {audioplay.format_ms(total)}"
        self.time_lbl.setText(text)
        self.time_lbl.setAccessibleName(text)

    def _on_position(self, ms):
        self._set_position(ms)

    def _on_duration(self, ms):
        if ms > 0 and ms != self.seek.maximum():   # the decoder's own length beats the header's
            pos = self.seek.value()
            self._seek_guard = True
            self.seek.setRange(0, int(ms))
            self.seek.setValue(min(pos, int(ms)))
            self._seek_guard = False
            self._show_time(self.seek.value())

    def _on_state(self, st):
        playing = st == audioplay.PLAYING
        self.play_btn.setIcon(icons.icon("pause" if playing else "play", self.pal["text"]))
        if st == audioplay.STOPPED:
            self._set_position(0)
            # a failure's own sentence must outlive the stop it causes
            if self._audio is not None and self._player is not None and self._player.inline and not self._failed:
                self._say("Ready — press Play.")

    def _on_failed(self, text):
        self._failed = True
        self._say(f"Playback failed — {text}", "error")

    def _on_seek_value(self, value):
        if self._seek_guard:
            return
        self._show_time(value)
        if not self.seek.isSliderDown():           # a key press or a click on the groove: seek now
            self._seek_to(value)

    def _on_seek_released(self):
        self._seek_to(self.seek.value())

    def _seek_to(self, ms):
        if self._player is not None and self._player.can_seek:
            self._player.seek(int(ms))

    def hideEvent(self, ev):                       # noqa: N802 (Qt override)
        """Leaving the tab silences it -- a preview must not outlive the surface that asked for it."""
        self.stop_audio()
        super().hideEvent(ev)

    def shutdown(self):
        """Window close: stop, and let the player release its device / kill its child."""
        self._debounce.stop()
        if self._player is not None:
            self._player.shutdown()

    # ------------------------------------------------------------------ naming
    def eventFilter(self, obj, ev):                # noqa: N802 (Qt override)
        # getattr: the filter is installed while the page is still being built
        edits = (getattr(self, "name_edit", None), getattr(self, "tags_edit", None))
        if obj in edits and ev.type() == QEvent.Type.KeyPress \
                and ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.save_name(advance=bool(ev.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            return True
        return super().eventFilter(obj, ev)

    def use_description(self):
        """Start the Name box from the kit's description (the user then corrects it by ear)."""
        s = self._current
        if s is None or not s.describe:
            return
        self.name_edit.setText(soundcat.suggest_title(s))
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def save_name(self, *, advance=False):
        """Write the Name / Tags boxes to the user overlay for the selected sound, relabel its row, and
        (``advance``) move on to the next sound with the caret back in the Name box."""
        s = self._current
        if s is None:
            return
        title = self.name_edit.text().strip()
        tags = soundcat.parse_tags(self.tags_edit.text())
        row = self.listw.row(self._items[s.key]) if s.key in self._items else -1
        try:
            path = soundcat.save_user_name(s.kind, s.stem, title, tags, path=self._names_path)
        except OSError as e:
            self._name_say(f"The name could not be saved — {e}", "error")
            return
        # re-read: clearing an overlay entry falls back to the kit's own name, which only a reload knows
        ent = (soundcat.load_names(self._names_path).get(s.kind) or {}).get(s.stem.lower()) or {}
        tags_now = tuple(ent.get("tags") or ())
        derived = soundcat.lore(self._sm, s, self._index).category if self._sm is not None else s.category
        fresh = dataclasses.replace(
            s, title=ent.get("title") or "", tags=tags_now,
            category=(soundcat.tag_category(tags_now) if s.kind == "sfx" else None) or derived)
        self._entries = [fresh if e.key == s.key else e for e in self._entries]
        self._current = fresh
        if fresh.category != s.category:           # a tag that names a category re-filed it
            self._refill_categories()
            self._refill_banks()
        if s.kind == "music":                      # the Music form's song picker shows these titles too
            from .. import infohub
            infohub.forget_songs()
        self._fill_detail(fresh)                   # the title, the category line, "Used as" -- all of it
        self._refill()
        self._name_say(f"Saved to {path}" if (title or tags) else
                       "Cleared — the kit's own name (if it has one) is back.")
        if advance and self.listw.count():
            still = s.key in self._items           # 'Unnamed only' drops a sound the moment it is named
            nxt = row + 1 if still else row
            if 0 <= nxt < self.listw.count():
                self.listw.setCurrentRow(nxt)
                self.name_edit.setFocus()
                self.name_edit.selectAll()

    # ------------------------------------------------------------------ copy / export
    def copy_id(self):
        if self._current is not None:
            QGuiApplication.clipboard().setText(str(self._current.id))

    def snippet(self) -> str:
        s = self._current
        if s is None:
            return ""
        label = s.title or s.stem
        if s.kind == "music":
            return f"[music]\nsong = {s.id}  # {label}\n"
        if s.kind == "sfx":
            return f"sfx = {s.id}  # {label}\n"
        return f"{s.id}\n"

    def copy_snippet(self):
        if self._current is not None:
            QGuiApplication.clipboard().setText(self.snippet())

    def _ask_save_ogg(self, default_name):
        out, _ = QFileDialog.getSaveFileName(self, "Export the sound", default_name, "Ogg Vorbis (*.ogg)")
        return out or None

    def _ask_open_audio(self):
        f, _ = QFileDialog.getOpenFileName(self, "Your audio file", "",
                                           "Audio (*.wav *.mp3 *.ogg *.flac *.m4a *.aif *.aiff);;All files (*)")
        return f or None

    def on_export(self):
        s = self._current
        if s is None:
            return
        try:
            path = self._audio[0] if self._audio is not None else self._audio_fn(s, self._mod())[0]
        except Exception as e:                     # noqa: BLE001
            return self._say(f"Nothing to export — {e}", "warn")
        out = self._ask_save_ogg(f"{s.stem}.ogg")
        if not out:
            return
        try:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, out)
        except OSError as e:
            return self._say(f"The export failed — {e}", "error")
        self._say(f"Exported to {out}. Edit it in any audio editor, then Replace with my audio…")

    # ------------------------------------------------------------------ replace / add (the job runner)
    def _warn(self, title, text):
        QMessageBox.warning(self, title, text)

    def browse_mod(self):
        d = QFileDialog.getExistingDirectory(self, "Mod folder to write audio into")
        if d:
            self.mod_edit.setText(d)
            self._on_mod_changed()

    def _on_mod_changed(self):
        if self._sm is not None:
            self._rebuild_entries()

    def _job_busy(self, b):
        for btn in self._job_buttons:
            btn.setEnabled(not b and self._current is not None and self._current.kind in _IMPORTABLE)

    def _kit(self, args, *, subject, ok_next=""):
        self._job_busy(True)

        def _done(_code):
            self._job_busy(False)
            self._rebuild_entries()                # the list shows the new 'replaced' / 'added' rows

        started = self._run([sys.executable, "-m", "ff9mapkit", *args], cwd=self.kit, subject=subject,
                            ok_headline=f"{subject} — done", ok_next=ok_next,
                            fail_hint="See the Output panel (audio import needs ffmpeg on PATH and "
                                      "your FF9 install).",
                            on_finished=_done)
        if not started:
            self._job_busy(False)

    def _import_args(self):
        """``(sound, mod folder, source file)`` for a replace/add, or None after telling the user why not."""
        s = self._current
        if s is None:
            return None
        if s.kind not in _IMPORTABLE:
            self._warn("Not replaceable here", "Only music and sound effects can be replaced or added "
                                               "from this tab.")
            return None
        mod = self._mod()
        if not mod:
            self._warn("No mod folder", "Pick the mod folder to write the audio into (Mod folder:).")
            return None
        src = self._ask_open_audio()
        if not src:
            return None
        return s, mod, src

    def on_replace(self):
        got = self._import_args()
        if got is None:
            return
        s, mod, src = got
        args = ["audio-import", src, "--song", str(s.id), "--kind", s.kind, "--deploy", mod]
        # the subject must not say "deploy": the shell's job runner treats that word as a field deploy
        self._kit(args, subject="Replace sound",
                  ok_next=f"{s.title or s.stem} now plays your file. RELAUNCH FF9 to hear it — audio "
                          "loads at startup.")

    def on_add(self):
        got = self._import_args()
        if got is None:
            return
        s, mod, src = got
        args = ["audio-import", src, "--new-song", "--kind", s.kind, "--deploy", mod]
        self._kit(args, subject="Add sound",
                  ok_next="Added as a new id — the Output panel prints it. RELAUNCH FF9, then play it "
                          "from a field (music: [music] song = <id>).")

    # ------------------------------------------------------------------ shell hooks
    def crumb_label(self):
        if self._current is not None:
            return self._current.title or self._current.stem
        return "browse sounds"

    def retheme(self, pal):
        """The transport icons and the guide glyph are palette-tinted at build time -- re-tint them."""
        self.pal = pal
        playing = self._player is not None and self._player.state() == audioplay.PLAYING
        self.play_btn.setIcon(icons.icon("pause" if playing else "play", pal["text"]))
        self.stop_btn.setIcon(icons.icon("stop", pal["text"]))
        if self._stack.currentWidget() is self._guide_page:
            self._show_guide(*self._guide_state)
