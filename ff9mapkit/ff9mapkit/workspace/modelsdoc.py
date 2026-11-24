"""The Models tab -- the custom-3D-models pillar's front door in the Workspace.

Browser (left): every GEO model the kit knows (catalog.models), searchable + group-filtered, with
REAL rendered thumbnails (models/preview.py via thumbs.ModelThumbService -- per-user disk cache;
a machine without the install degrades to text rows). Detail (right): the preview still, catalog
facts + the render's counts sidecar, the model->animation join as a CLIP LIST that arms a little
frame player (workspace/animframes.py streams the rendered frames; they paint into the still's own
box and Reset puts the still back), appearance caveats (story-evolved forms / the Garnet hair-swap),
overworld actor identity, and ready snippets. The still says WHAT IT SHOWS (the clip it was posed
from -- models/thumbcache writes that into the sidecar, catalog.stand_clip chooses it). Renders
follow the viewport (whatever scrolls into view), and the ``Previews`` menu under the list is the
cache's one control: its status, a background render-everything lane, and a clear. Actions: the whole
DLL-free round-trip in ONE place -- export a Blender-editable .glb, import the edited .glb back,
mint a new id (>=6000), dump editable .anim clips -- each streaming ``py -m ff9mapkit model-*``
through the shell's job runner. (Moved here from the Import tab, which now points at this tab.)

Same doc conventions as ImportDoc/BuildDoc: constructor injection (pal, kit root, run/problems
callbacks), a ``_kit`` streamer, ``_busy`` button-disable, ``crumb_label()`` for the breadcrumb.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QSize, QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                               QPushButton, QScrollArea, QSizePolicy, QSplitter, QVBoxLayout, QWidget)

from .. import catalog
from ..models import thumbcache
from ..models.appearance import appearance_notes
from . import clipplayer, modelcards, thumbs as thumbs_mod, widgets

_ICON = 56                                       # list-row icon size (px)
_DETAIL_IMG = 224                                # detail-pane preview size (px)
_THUMB_BATCH = 96                                # thumbnails auto-requested per filter result (top of list)
_VISIBLE_BATCH = 48                              # max cold renders enqueued per scroll settle
_VISIBLE_PAD = 4                                 # rows either side of the viewport rendered with it
_SCROLL_MS = 150                                 # scroll-settle debounce before requesting renders
_MINT_FLOOR = 6000                               # first id clear of every real GEO id (mint.MINT_BAND_START)
_RIG_BONES = 8                                   # fewer bones than this is a PROP (a barrel has 2, a weapon
#                                                  1): "this may be a bind pose" is a caution about a
#                                                  character's T-pose, and noise under a treasure chest
_CLIP_LIST_H = 150                               # clip-list cap (px) BEFORE a fill: a QListWidget's
#                                                  sizeHint is 256x192 whatever its row count (the
#                                                  dep_list idiom). A filled list re-caps on whole
_CLIP_ROWS = 5                                   # rows measured in the list's OWN font (CALIBRE),
_CLIP_LIST_CHROME = 5                            # + the QSS well's border(1) + padding(4) per side

_GROUPS = modelcards.GROUPS                      # one list, one order (the card picker shares it)


def _size(nbytes) -> str:
    """A byte count for a status line: whole MB, with a floor that never reads '0 MB' for real files."""
    mb = float(nbytes) / (1024.0 * 1024.0)
    if nbytes <= 0:
        return "0 MB"
    return "under 1 MB" if mb < 1.0 else f"{mb:.0f} MB"


class _IdEdit(QLineEdit):
    """A short numeric-id box sized in CHARACTERS of its OWN font, so it hears the text-size dial.

    It replaces ``setFixedWidth(70)``. A px constant is deaf to CALIBRE by construction: at the 150%
    rung the box showed ';000' for 6000 (snap-caught) -- the one field on this pane whose whole job is
    to be read before a destructive click. The hint is derived at CALL time, so a restyle re-measures
    it: QLineEdit's own hint is 17 'x' wide plus chrome, and the chrome is whatever is left over."""

    def __init__(self, text="", *, ch=6, parent=None):
        super().__init__(text, parent)
        self._ch = int(ch)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def sizeHint(self):
        hint = super().sizeHint()
        fm = self.fontMetrics()
        chrome = hint.width() - fm.horizontalAdvance("x") * 17
        hint.setWidth(fm.horizontalAdvance("0" * self._ch) + max(0, chrome))
        return hint

    def minimumSizeHint(self):
        return self.sizeHint()


class ModelsDoc(clipplayer.ClipPlayer, QWidget):
    """Browse every FF9 model with rendered previews + run the whole edit round-trip on the selection."""

    def __init__(self, pal, kit_root, *, run, problems=None, model_thumbs=None, anim_frames=None,
                 parent=None):
        super().__init__(parent)
        self.pal = pal
        self.kit = str(kit_root)
        self._run = run
        self._problems = problems
        self.thumbs = model_thumbs if model_thumbs is not None else thumbs_mod.ModelThumbService(self)
        self.thumbs.ready.connect(self._thumb_ready)
        self.thumbs.missed.connect(self._thumb_missed)
        # the clip player's frame source -- injected in tests (a double with the same surface), so no
        # test can reach a worker thread or this machine's install through it. The transport row and the
        # playback state machine are clipplayer.ClipPlayer's, shared with the anim PICKER dialog.
        self._init_player(anim_frames)
        self._current = None                     # the selected catalog.Model (or None)
        self._items = {}                         # geo name -> QListWidgetItem (the CURRENT filter's rows)
        self._icons = {}                         # geo name -> QIcon (decode each cache PNG ONCE, not per refill)
        # probed no-geometry ids (grows live via missed). Lazily scanned on first NEED -- the tab is
        # built at Workspace construction, and the sidecar sweep (hundreds of small files) belongs to
        # the hide-toggle/miss paths, not to startup. None = not scanned yet (tests assign a set).
        self._absent = None
        self._blank = QPixmap(_ICON, _ICON)      # constant-size placeholder so rows never shift
        self._blank.fill(Qt.GlobalColor.transparent)
        self._blank_icon = QIcon(self._blank)
        self._clip_rows = []                     # the selected model's WHOLE clip inventory (pre-filter)
        # scroll-driven renders: a row past the first _THUMB_BATCH used to stay blank until it was
        # SELECTED -- two thirds of the catalog was a text list. Now whatever scrolls into view renders.
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.setInterval(_SCROLL_MS)
        self._scroll_timer.timeout.connect(self._request_visible)
        self._build()
        self.listw.verticalScrollBar().valueChanged.connect(self._on_list_scrolled)
        self._refill()

    # ------------------------------------------------------------------ layout
    def _build(self):
        muted = f"color:{self.pal['muted']};"
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        split = QSplitter()
        root.addWidget(split)

        # ---- left: the browser ----
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 6, 0)
        srow = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setAccessibleName("Search models")
        self.search.setPlaceholderText("Search by name, token, or a friendly name — vivi, GRN, MON_B3…")
        self.search.textChanged.connect(self._refill)
        srow.addWidget(self.search, 1)
        self.cards_btn = QPushButton("Cards…")
        self.cards_btn.setToolTip("Browse the same list as big thumbnail cards — a visual search "
                                  "when you'd recognize the model but don't know its name.")
        self.cards_btn.clicked.connect(self.on_cards)
        srow.addWidget(self.cards_btn)
        lv.addLayout(srow)
        # TWO rows, not one: a checkbox's label is its minimumSizeHint (no wrap), so combo + both
        # checkboxes in one row put a ~450px floor under the LEFT pane -- in the ~700px document column
        # that starved the right pane below its own content width and (with its h-bar then forced off)
        # every control on it CLIPPED mid-glyph at the default window size.
        grow = QHBoxLayout()
        self.group = QComboBox()
        self.group.setAccessibleName("Filter models by group")
        for label, _arg in _GROUPS:
            self.group.addItem(label)
        self.group.currentIndexChanged.connect(self._refill)
        grow.addWidget(self.group)
        grow.addStretch(1)
        lv.addLayout(grow)
        frow = QHBoxLayout()
        self.field_only = QCheckBox("Field-placeable only")
        self.field_only.setToolTip("Keep the field-form (F*) models — the ones an [[npc]] can wear.")
        self.field_only.toggled.connect(self._refill)
        frow.addWidget(self.field_only)
        self.no_geo = QCheckBox("Hide no-geometry")
        self.no_geo.setToolTip("Drop the ids probed as UNSHIPPED (PSX-era catalog leftovers with "
                               "nothing to place or preview). The set fills in as previews render — "
                               "a fresh cache hides nothing yet.")
        self.no_geo.toggled.connect(self._refill)
        frow.addWidget(self.no_geo)
        frow.addStretch(1)
        lv.addLayout(frow)
        self.listw = QListWidget()
        self.listw.setAccessibleName("Model catalog")
        self.listw.setIconSize(QSize(_ICON, _ICON))
        self.listw.setUniformItemSizes(True)
        self.listw.currentItemChanged.connect(self._on_select)
        lv.addWidget(self.listw, 1)
        crow = QHBoxLayout()
        self.count_lbl = QLabel("")
        self.count_lbl.setProperty("role", "muted")
        crow.addWidget(self.count_lbl, 1)
        # the preview cache's ONE control: a menu, because its three verbs are rare and its status
        # costs a directory scan (paid in aboutToShow, never at startup). A QPushButton with a menu
        # draws its own arrow -- do not type a caret into the label.
        self.cache_btn = QPushButton("Previews")
        self.cache_btn.setProperty("role", "quiet")
        self.cache_btn.setAccessibleName("Preview cache")
        self.cache_btn.setToolTip("The rendered-preview cache: render every model's preview in the "
                                  "background, or clear the cache.")
        self.cache_menu = QMenu(self.cache_btn)
        self.cache_status_act = self.cache_menu.addAction("")
        self.cache_status_act.setEnabled(False)
        self.cache_clips_act = self.cache_menu.addAction("")
        self.cache_clips_act.setEnabled(False)
        self.cache_menu.addSeparator()
        self.cache_render_act = self.cache_menu.addAction("Render all previews")
        self.cache_render_act.triggered.connect(self.on_render_all)
        self.cache_clear_act = self.cache_menu.addAction("Clear the preview cache…")
        self.cache_clear_act.triggered.connect(self.on_clear_cache)
        self.cache_menu.aboutToShow.connect(self._refresh_cache_menu)
        self.cache_btn.setMenu(self.cache_menu)
        self.cache_btn.setVisible(thumbs_mod.enabled())      # previews off -> there is no cache to manage
        crow.addWidget(self.cache_btn)
        lv.addLayout(crow)
        split.addWidget(left)

        # ---- right: detail + actions (scrolled) ----
        right_host = QWidget()
        rv = QVBoxLayout(right_host)
        rv.setContentsMargins(10, 0, 0, 0)
        self.d_title = QLabel("Pick a model")
        self.d_title.setTextFormat(Qt.TextFormat.PlainText)
        self.d_title.setProperty("role", "head")
        rv.addWidget(self.d_title)
        self.d_sub = QLabel("")
        self.d_sub.setProperty("role", "muted")
        self.d_sub.setWordWrap(True)
        rv.addWidget(self.d_sub)

        img_row = QHBoxLayout()
        self.d_img = QLabel()
        self.d_img.setFixedSize(_DETAIL_IMG, _DETAIL_IMG)
        self.d_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # BOTH of this round's traps in one expression, and it survived the SPEND census because that
        # census grepped `background:{...}` -- this rule's background is `transparent` and the hex rode on
        # `border`. `'border'` is in all 8 palettes, so the `.get` default could never fire (dead), and
        # `#444` is a palette-blind grey that no theme switch can reach (loaded). Index it.
        # SELECTOR FORM, never a bare property list: a bare sheet out-ranks the app sheet for this
        # widget's own state rules too (the round-9 census fence covers every widget now, not just
        # containers). The id scopes it to exactly this label.
        self.d_img.setObjectName("modelDetailImg")
        self.d_img.setStyleSheet("QLabel#modelDetailImg { background: transparent; "  # was pal.get('panel', ...)
                                 f"border: 1px solid {self.pal['border']}; border-radius: 6px; }}")
        img_row.addWidget(self.d_img)
        facts_col = QVBoxLayout()
        self.d_facts = QLabel("")
        self.d_facts.setWordWrap(True)
        facts_col.addWidget(self.d_facts)
        self.d_pose = widgets.caption("")    # what the still SHOWS (its clip, or "rest pose") -- its own
        facts_col.addWidget(self.d_pose)     # line: the picture is unreadable without it on a T-pose
        self.d_pose.hide()
        self.d_notes = widgets.caption("")   # appearance caveats -> a small cautionary note
        self.d_notes.setProperty("state", "warn")
        facts_col.addWidget(self.d_notes)
        facts_col.addStretch(1)
        img_row.addLayout(facts_col, 1)
        rv.addLayout(img_row)
        copy_row = QHBoxLayout()
        self.copy_name_btn = QPushButton("Copy name")
        self.copy_name_btn.clicked.connect(self._copy_name)
        copy_row.addWidget(self.copy_name_btn)
        self.copy_snip_btn = QPushButton("Copy [[npc]] snippet")
        self.copy_snip_btn.clicked.connect(self._copy_snippet)
        copy_row.addWidget(self.copy_snip_btn)
        self.copy_anims_btn = QPushButton("Copy anims= snippet")
        self.copy_anims_btn.setToolTip("The five movement slots this model resolves to, as a TOML "
                                       "inline table to paste into an [[npc]] block.")
        self.copy_anims_btn.clicked.connect(self._copy_anims)
        copy_row.addWidget(self.copy_anims_btn)
        copy_row.addStretch(1)
        rv.addLayout(copy_row)

        rv.addWidget(self._anim_box())
        rv.addWidget(self._actions_box())
        rv.addWidget(self._playable_box())
        rv.addWidget(self._deployed_box())
        rv.addStretch(1)

        right = QScrollArea()
        # NoFrame like the other 7: Qt draws its own frame here otherwise, in a colour taken from the
        # STYLE palette rather than ours -- it is in no palette, never re-tints on a theme switch, and
        # measured #eaebee/1.011 in light and ~1.24 in the darks. Quiet, but un-chosen. 7 of 10 already
        # set this; these were the stragglers.
        right.setFrameShape(QFrame.Shape.NoFrame)
        right.setWidgetResizable(True)
        # AsNeeded, not AlwaysOff: the labels/line edits re-flow first, but the action ROWS have a real
        # minimum, and below it a widgetResizable scroll area with the h-bar forced off does not scroll --
        # it CLIPS (the shipped defect: 'Copy [[npc]] snip', 'Deploy r' cut mid-glyph at the default
        # window). The bar appears only in the squeeze it exists to make honest.
        right.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        right.setWidget(right_host)
        split.addWidget(right)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        split.setSizes([340, 640])

    def _anim_box(self):
        """The clip list + the player transport -- a FULL-WIDTH row of the detail pane.

        NOT inside the 224px preview column: that column is `d_img`'s fixed box, and the round-13
        lesson is that a control squeezed under its content minimum in this pane CLIPS rather than
        scrolls. The rendered frames paint into `d_img` itself (Reset puts the still back), so the
        strip owns only the transport -- one play/pause toggle, one reset, the scrub slider and an
        elided counter that says the HONEST rate (a strided clip plays slower than its sample rate).
        """
        box = widgets.section("Preview an animation")
        v = box.content_layout
        # A FILTER, because the list is five rows tall and Zidane has 416 clips. Shown only when the
        # model has more clips than the list has rows.
        self.clip_filter = QLineEdit()
        self.clip_filter.setAccessibleName("Filter animation clips")
        self.clip_filter.setClearButtonEnabled(True)
        self.clip_filter.textChanged.connect(self._fill_clip_rows)
        self.clip_filter.hide()
        v.addWidget(self.clip_filter)
        self.clip_list = QListWidget()
        self.clip_list.setAccessibleName("Animation clips for this model")
        self.clip_list.setMaximumHeight(_CLIP_LIST_H)     # see _CLIP_LIST_H (the dep_list idiom)
        self.clip_list.currentItemChanged.connect(self._on_clip)
        v.addWidget(self.clip_list)
        v.addWidget(self._build_transport())     # ClipPlayer's transport row (shared with the picker)
        v.addWidget(self.anim_foot)              # ...its prose line (+ speed) stays OUTSIDE the strip:
        return box                               # NO_THUMBS hides the strip and the sentence must survive

    # ------------------------------------------------------------------ the clip player
    def _still_png(self):
        """ClipPlayer's Reset target: this model's cached ModelThumbService still (already warm on disk
        whenever the detail pane painted one)."""
        return self.thumbs.cached(self._current.name) if self._current is not None else None

    def _refill_clips(self, m):
        """The model's clip inventory -> rows 'label · id N' (+ 'other form' where the clip's ANH
        names a DIFFERENT form code: a different form is a different skeleton). Install-free."""
        rows = catalog.clip_inventory(m.id) if m is not None else []
        self._clip_rows = rows
        self.clip_filter.blockSignals(True)       # a new model starts unfiltered
        self.clip_filter.clear()
        self.clip_filter.blockSignals(False)
        self.clip_filter.setPlaceholderText(f"Filter {len(rows)} clips — walk, talk, attack…")
        self.clip_filter.setVisible(len(rows) > _CLIP_ROWS)
        self._fill_clip_rows()
        if not rows:
            self.anim_note.setText("No clips catalogued for this model (a numbered battle-only "
                                   "token or a static prop).")
            return
        # cap on a WHOLE number of rows, measured from the list's REAL row height so the cap hears
        # CALIBRE (a px constant is deaf by construction -- the fixed 150 sliced the 5th row in half)
        row_h = self.clip_list.sizeHintForRow(0)
        if row_h > 0:
            self.clip_list.setMaximumHeight(row_h * _CLIP_ROWS + 2 * _CLIP_LIST_CHROME)
        if thumbs_mod.enabled():                 # NO_THUMBS keeps its own "previews off" line
            self.anim_note.setText(f"{len(rows)} clip(s) — pick one to render and play it.")

    def _fill_clip_rows(self, *_a):
        """(Re)build the clip rows from the inventory through the filter box. Signals are blocked: a
        refill must not arm a row by itself, and a filter keystroke must not re-arm the playing clip
        (its row is re-selected silently when it survives the filter)."""
        q = self.clip_filter.text().strip().lower()
        armed = self._armed[1] if self._armed else None
        self.clip_list.blockSignals(True)
        self.clip_list.clear()
        for r in self._clip_rows:
            label = f"{r['label']}  ·  id {r['anim_id']}"
            if not r["own_form"]:
                label += "  ·  other form"
            if q and q not in label.lower():
                continue
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, r["anim_id"])
            self.clip_list.addItem(it)
            if armed is not None and r["anim_id"] == armed and self.clip_list.currentItem() is None:
                self.clip_list.setCurrentItem(it)
        self.clip_list.blockSignals(False)

    def _on_clip(self, item, _prev=None):
        if item is None or self._current is None:
            return
        self.arm_clip(self._current.name, item.data(Qt.ItemDataRole.UserRole))

    def hideEvent(self, ev):
        """Leaving the tab stops the clock and cancels the fill -- a background clip render must not
        outlive the surface that asked for it."""
        self.stop_playback()
        self.anims.supersede()
        self._scroll_timer.stop()                # a parked widget's single-shot fires in a LATER test
        super().hideEvent(ev)

    def _actions_box(self):
        """The DLL-free round-trip, keyed on the selected model. Same argv shapes the Import tab's old
        models box streamed -- the object names (mdl_*) are kept so the smoke + muscle memory carry."""
        muted = f"color:{self.pal['muted']};"
        box = widgets.section("Edit this model")
        v = box.content_layout

        dep = QHBoxLayout()
        _l_dep = QLabel("Deploy into:")
        dep.addWidget(_l_dep)
        from ..editor import jobs
        gm = jobs.detect_game_mod(Path(self.kit).parent)   # keyed on THIS checkout's pin, like the Build tab
        self.mdl_mod = QLineEdit(str(gm) if gm else "")
        self.mdl_mod.setPlaceholderText("a mod folder, e.g. <game>/FF9CustomMap")
        _l_dep.setBuddy(self.mdl_mod)          # see the buddy note in coopdoc
        dep.addWidget(self.mdl_mod, 1)
        mb = QPushButton("Browse…")
        mb.clicked.connect(self.browse_model_mod)
        dep.addWidget(mb)
        v.addLayout(dep)

        exp = QHBoxLayout()
        self.mdl_gltf_btn = QPushButton("Export .glb…")
        self.mdl_gltf_btn.setToolTip("Write the selected model as a Blender-openable glTF "
                                     "(File ▸ Import ▸ glTF 2.0): mesh + rig + textures + animations.")
        self.mdl_gltf_btn.clicked.connect(self.on_model_gltf)
        exp.addWidget(self.mdl_gltf_btn)
        _l_anims = QLabel("anims:")
        exp.addWidget(_l_anims)
        self.mdl_anims = QComboBox()
        _l_anims.setBuddy(self.mdl_anims)
        self.mdl_anims.addItems(["auto", "all", "none"])
        self.mdl_anims.setToolTip("Which clips to embed in the .glb: auto = idle/walk/run/turns; "
                                  "all = the model's whole folder; none = mesh only.")
        exp.addWidget(self.mdl_anims)
        exp.addStretch(1)
        v.addLayout(exp)

        clips = QHBoxLayout()
        self.mdl_anim_btn = QPushButton("Dump editable clips…")
        self.mdl_anim_btn.setToolTip("Write the model's animation clips as hand-editable .anim JSON "
                                     "(model-anim). Deploy an edited clip by copying it into a mod folder's "
                                     "StreamingAssets/Assets/Resources/Animations/<id>/.")
        self.mdl_anim_btn.clicked.connect(self.on_model_anim)
        clips.addWidget(self.mdl_anim_btn)
        clips.addStretch(1)
        v.addLayout(clips)

        rsk = QHBoxLayout()
        self.mdl_tex_btn = QPushButton("Export textures…")
        self.mdl_tex_btn.setToolTip("The CHEAPEST edit — no Blender: write the model's textures as "
                                    "editable PNGs (any editor, any size, keep the names).")
        self.mdl_tex_btn.clicked.connect(self.on_model_textures)
        rsk.addWidget(self.mdl_tex_btn)
        self.mdl_reskin_btn = QPushButton("Deploy reskin PNG(s)…")
        self.mdl_reskin_btn.setToolTip("Ship edited {name}.png file(s) into the mod folder — the engine "
                                       "probes them by NAME and swaps the texture, mesh untouched.")
        self.mdl_reskin_btn.clicked.connect(self.on_model_reskin)
        rsk.addWidget(self.mdl_reskin_btn)
        rsk.addStretch(1)
        v.addLayout(rsk)

        imp = QHBoxLayout()
        _l_glb = QLabel("Edited .glb:")
        imp.addWidget(_l_glb)
        self.mdl_glb = QLineEdit()
        _l_glb.setBuddy(self.mdl_glb)
        self.mdl_glb.setPlaceholderText("the .glb you exported from Blender (drag-and-drop works too)")
        imp.addWidget(self.mdl_glb, 1)
        gb = QPushButton("Browse…")
        gb.clicked.connect(self.browse_model_glb)
        imp.addWidget(gb)
        self.mdl_import_btn = QPushButton("Import model")
        self.mdl_import_btn.setToolTip("Splice the edited geometry back over the pristine rig of the model "
                                       "selected above (falls back to the kit's glTF stamp if nothing's "
                                       "selected) + write any CHANGED animation clips.")
        self.mdl_import_btn.clicked.connect(self.on_model_import)
        imp.addWidget(self.mdl_import_btn)
        v.addLayout(imp)

        mint = QHBoxLayout()
        _l_mint = QLabel("Mint new id:")
        mint.addWidget(_l_mint)
        self.mdl_mint_id = _IdEdit(str(_MINT_FLOOR))        # 6 digits wide: the band tops out at 65535
        _l_mint.setBuddy(self.mdl_mint_id)
        self.mdl_mint_id.setToolTip("The new model id — ≥ 6000 (clear of every real id). It moves "
                                    "off an id the Deploy-into folder is already using.")
        mint.addWidget(self.mdl_mint_id)
        self.mdl_mint_btn = QPushButton("Mint from model")
        self.mdl_mint_btn.setToolTip("Re-export the selected model to a brand-new id + register it in "
                                     "DictionaryPatch.txt (3DModel line). Place it with [[npc]] model = <id>.")
        self.mdl_mint_btn.clicked.connect(self.on_model_mint)
        mint.addWidget(self.mdl_mint_btn)
        mint.addStretch(1)
        v.addLayout(mint)

        hint = QLabel("Mesh edits show on ~ → Reload; edited ANIMATIONS and newly MINTED ids need a game "
                      "relaunch (clips + DictionaryPatch load at startup).")
        hint.setWordWrap(True)
        hint.setProperty("role", "muted")
        v.addWidget(hint)
        self._buttons = [self.mdl_gltf_btn, self.mdl_anim_btn, self.mdl_import_btn, self.mdl_mint_btn,
                         self.mdl_tex_btn, self.mdl_reskin_btn]
        return box

    def _playable_box(self):
        """The 13th-character battle-animset loop (`playable-anims`): export the donor's battle model
        with Blender Actions NAMED by battle motion, edit, route the edits onto the character's OWN
        minted animset (donor untouched). Field-toml-scoped -- the [[playable]] block must carry
        custom_battle_anims = true (editable in the field editor's Playables section)."""
        muted = f"color:{self.pal['muted']};"
        box = widgets.section("Custom playable's battle animset")
        v = box.content_layout
        v.addWidget(widgets.caption("Works on a field.toml's [[playable]] block — not the model selected above."))
        frow = QHBoxLayout()
        _l_pa = QLabel("field.toml:")
        frow.addWidget(_l_pa)
        self.pa_field = QLineEdit()
        _l_pa.setBuddy(self.pa_field)
        self.pa_field.setPlaceholderText("the field.toml carrying the [[playable]] custom_battle_anims block")
        frow.addWidget(self.pa_field, 1)
        fb = QPushButton("Browse…")
        fb.clicked.connect(self.browse_pa_field)
        frow.addWidget(fb)
        v.addLayout(frow)
        brow = QHBoxLayout()
        self.pa_export_btn = QPushButton("Export donor .glb…")
        self.pa_export_btn.setToolTip("Write the donor battle model with each Action NAMED by battle "
                                      "motion (23_attack, …) — edit any of them in Blender.")
        self.pa_export_btn.clicked.connect(self.on_pa_export)
        brow.addWidget(self.pa_export_btn)
        self.pa_edit_btn = QPushButton("Route edited .glb…")
        self.pa_edit_btn.setToolTip("Splice the edited clips onto the character's OWN minted animset "
                                    "(Animations/<mintId>/) — the donor stays untouched. RELAUNCH to see it.")
        self.pa_edit_btn.clicked.connect(self.on_pa_edit)
        brow.addWidget(self.pa_edit_btn)
        brow.addStretch(1)
        v.addLayout(brow)
        hint = QLabel("For a [[playable]] with custom_battle_anims = true (edit the block in the field "
                      "editor's Playables section). Also survives re-deploys via its anim_edits key.")
        hint.setWordWrap(True)
        hint.setProperty("role", "muted")
        v.addWidget(hint)
        self._buttons += [self.pa_export_btn, self.pa_edit_btn]
        return box

    def browse_pa_field(self):
        f, _ = QFileDialog.getOpenFileName(self, "The field.toml with the [[playable]] block", "",
                                           "field.toml (*.toml)")
        if f:
            self.pa_field.setText(f)

    def _pa_field_arg(self):
        f = self.pa_field.text().strip().strip('"')
        if not f or not Path(f).is_file():
            self._warn("No field.toml", "Pick the field.toml carrying the [[playable]] block first.")
            return None
        return f

    def on_pa_export(self):
        field = self._pa_field_arg()
        if field is None:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Export the donor battle model", "playable_anims.glb",
                                             "glTF binary (*.glb)")
        if not out:
            return
        self._kit(["playable-anims", field, "--export", out], subject="Export donor .glb",
                  ok_next=f"Wrote {out} — Actions are named by battle motion (23_attack, …). Edit in "
                          "Blender (active action only), then Route edited .glb.")

    def on_pa_edit(self):
        field = self._pa_field_arg()
        if field is None:
            return
        mod = self._model_mod_arg()
        if mod is None:
            return
        glb, _ = QFileDialog.getOpenFileName(self, "The Blender-edited donor .glb", "",
                                             "glTF (*.glb *.gltf)")
        if not glb:
            return
        self._kit(["playable-anims", field, "--edit", glb, "--deploy", mod], subject="Route animset edits",
                  ok_next="Edited clips spliced onto the character's OWN animset (donor untouched). "
                          "RELAUNCH FF9 to see them; add anim_edits = \"<the .glb>\" to the [[playable]] "
                          "block so re-deploys keep the edit.")

    def _deployed_box(self):
        """What's actually deployed model-wise in the 'Deploy into' folder -- overrides / reskins /
        mints / anim overrides / dangling 3DModel lines -- with a confirm-first per-entry revert.
        The loose-override system is write-only; this is the read side."""
        muted = f"color:{self.pal['muted']};"
        box = widgets.section("Deployed in this mod folder")
        v = box.content_layout
        self.dep_list = QListWidget()
        self.dep_list.setAccessibleName("Models deployed in this mod folder")   # no visible label to buddy
        self.dep_list.setMaximumHeight(170)
        v.addWidget(self.dep_list)
        row = QHBoxLayout()
        self.dep_refresh_btn = QPushButton("Refresh")
        self.dep_refresh_btn.clicked.connect(self.on_deployed_refresh)
        row.addWidget(self.dep_refresh_btn)
        self.dep_revert_btn = QPushButton("Revert selected…")
        self.dep_revert_btn.setToolTip("Delete this entry's loose files (a mint also loses its "
                                       "3DModel line). The bundled original takes over again.")
        self.dep_revert_btn.clicked.connect(self.on_deployed_revert)
        row.addWidget(self.dep_revert_btn)
        row.addStretch(1)
        v.addLayout(row)
        self.dep_hint = QLabel("Pick a mod folder above, then Refresh.")
        self.dep_hint.setWordWrap(True)
        self.dep_hint.setProperty("role", "muted")
        v.addWidget(self.dep_hint)
        return box

    def on_deployed_refresh(self):
        from ..models import deployed
        mod = self.mdl_mod.text().strip().strip('"')
        self.dep_list.clear()
        if not mod or not Path(mod).is_dir():
            self.dep_hint.setText("Pick a mod folder above (Deploy into:), then Refresh.")
            return
        try:
            entries = deployed.scan_mod(mod)
        except OSError as e:
            self.dep_hint.setText(f"Scan failed: {e}")
            return
        for e in entries:
            it = QListWidgetItem(deployed.describe(e))
            it.setData(Qt.ItemDataRole.UserRole, e)
            self.dep_list.addItem(it)
        self.dep_hint.setText(f"{len(entries)} deployed entr{'y' if len(entries) == 1 else 'ies'}."
                              if entries else "No loose model overrides in this folder.")
        self._suggest_mint_id(mod)

    # ------------------------------------------------------------------ the mint id
    def _suggest_mint_id(self, mod):
        """If the id in the box is one ``mod`` already uses, advance it to the next free id AT OR ABOVE
        it (so a hand-typed 6100 becomes 6101, not 6000). A free id is never touched. The old constant
        6000 meant the SECOND mint into a folder silently replaced the first."""
        from ..models import deployed
        if not mod or not Path(mod).is_dir():
            return
        cur = self.mdl_mint_id.text().strip()
        base = int(cur) if cur.isdigit() and int(cur) >= _MINT_FLOOR else _MINT_FLOOR
        free = str(deployed.next_mint_id(mod, floor=base))
        if free != cur:
            self.mdl_mint_id.setText(free)

    def on_deployed_revert(self):
        from ..models import deployed
        it = self.dep_list.currentItem()
        if it is None:
            return self._warn("Nothing selected", "Pick a deployed entry to revert first.")
        e = it.data(Qt.ItemDataRole.UserRole)
        mod = self.mdl_mod.text().strip().strip('"')
        detail = deployed.describe(e)
        if QMessageBox.question(self, "Revert this entry?",
                                f"Delete:\n\n{detail}\n\nfrom {mod}?\n\nThe bundled original takes "
                                "over again. A registered mint id needs a game RELAUNCH to unregister.") \
                != QMessageBox.StandardButton.Yes:
            return
        try:
            r = deployed.revert_entry(mod, e)
        except (OSError, ValueError) as err:
            return self._warn("Revert failed", str(err))
        bits = [f"removed {len(r['removed'])} folder(s)"]
        if r["directive_removed"]:
            bits.append("stripped the 3DModel line (relaunch to unregister)")
        self.dep_hint.setText(f"Reverted {e['name'] or e['geo_id']}: " + ", ".join(bits) + ".")
        self.on_deployed_refresh()

    # ------------------------------------------------------------------ browser
    def _absent_ids(self):
        """The probed no-geometry set, sidecar-scanned on FIRST need (gated like every other cache
        read: a NO_THUMBS run never scans the developer's real preview cache)."""
        if self._absent is None:
            self._absent = modelcards.absent_geo_ids() if thumbs_mod.enabled() else set()
        return self._absent

    def _refill(self, *_a):
        cur = self.listw.currentItem()
        keep = cur.data(Qt.ItemDataRole.UserRole) if cur is not None else None
        q = self.search.text().strip()
        grp = _GROUPS[self.group.currentIndex()][1]
        hide = self.no_geo.isChecked()
        entries, hidden = modelcards.filter_models(q, grp, field_only=self.field_only.isChecked(),
                                                   hide_absent=hide,
                                                   absent=self._absent_ids() if hide else frozenset())
        self._count_base = f"{len(entries)} model(s)" + (f"  ·  {hidden} with no geometry hidden"
                                                         if hidden else "")
        self.listw.clear()
        self._items = {}
        for m in entries:
            label = m.name + (f"  ·  id {m.id}" if m.id is not None else "")
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, m.name)
            it.setIcon(self._icon_for(m.name))
            self.listw.addItem(it)
            self._items[m.name] = it
        if keep is not None and keep in self._items:     # a live filter update must not steal the pick
            self.listw.setCurrentItem(self._items[keep])
        self._update_count()
        # warm the visible top of the list (the rest render on selection; all cache forever). Known
        # no-geometry ids are skipped -- a render attempt on them is a guaranteed miss. cached() is
        # probed FIRST: on a warm cache nothing needs the absent set, so startup skips its sidecar scan.
        if thumbs_mod.enabled():
            for m in entries[:_THUMB_BATCH]:
                if self.thumbs.cached(m.name) is None and m.id not in self._absent_ids():
                    self.thumbs.request(m.name)

    def _warming(self) -> bool:
        """Is (or was, one arrival ago) the background warm-up running? The second half clears the
        'N to go' text when the LAST render lands and the lane reads empty."""
        return bool(self.thumbs.bulk_pending()) or "rendering previews" in self.count_lbl.text()

    def _update_count(self):
        """The count line: the filter result, plus the background warm-up's progress while it runs."""
        left = self.thumbs.bulk_pending()
        self.count_lbl.setText(getattr(self, "_count_base", "")
                               + (f"  ·  rendering previews, {left} to go" if left else "")
                               + ("" if thumbs_mod.enabled() else "  ·  previews off"))

    # ------------------------------------------------------------------ renders follow the viewport
    def _on_list_scrolled(self, _value=0):
        if self.isVisible():                     # a hidden tab's refill must not arm a timer (a parked
            self._scroll_timer.start()           # widget's single-shot fires in somebody else's test)

    def _visible_rows(self) -> range:
        """The row span in (or a few rows shy of) the viewport. Rows are uniform, so two hit-tests
        bound it; an empty/short list answers with what it has."""
        n = self.listw.count()
        if n == 0:
            return range(0)
        vp = self.listw.viewport()
        top = self.listw.indexAt(QPoint(4, 2)).row()
        bot = self.listw.indexAt(QPoint(4, max(2, vp.height() - 2))).row()
        top = 0 if top < 0 else top
        bot = n - 1 if bot < 0 else bot
        return range(max(0, top - _VISIBLE_PAD), min(n, bot + _VISIBLE_PAD + 1))

    def _request_visible(self):
        """Enqueue cold renders for the rows in view -- never the whole list (the Cards picker's
        discipline; 'Render all previews' is the explicit way to ask for everything)."""
        if not thumbs_mod.enabled():
            return
        asked = 0
        for row in self._visible_rows():
            name = self.listw.item(row).data(Qt.ItemDataRole.UserRole)
            if self.thumbs.cached(name) is not None:
                continue
            gid = thumbs_mod._geo_id(name)
            if gid is not None and gid in self._absent_ids():
                continue                          # a known no-geometry id is a guaranteed miss
            self.thumbs.request(name)
            asked += 1
            if asked >= _VISIBLE_BATCH:
                break

    def showEvent(self, ev):
        super().showEvent(ev)
        self._scroll_timer.start()               # the list has real geometry now -> render what shows
        # NOT the deployed scan. It was here, and the first snap painted THIS MACHINE's mod folder
        # (a real minted model) into the picture: any harness that shows the tab would report on its
        # developer. The list refreshes when it actually goes stale -- after a deploy -- and on Refresh.

    # ------------------------------------------------------------------ the preview cache menu
    def _refresh_cache_menu(self):
        """Fill the menu's status lines (one directory scan each, paid only when the menu opens)."""
        stills = thumbcache.still_cache_stats()
        clips = thumbcache.anim_cache_stats()
        total = len(catalog.all_models())
        self.cache_status_act.setText(
            f"{stills['rendered']} of {total} previews rendered"
            + (f", {stills['absent']} have no geometry" if stills["absent"] else "")
            + f"  ·  {_size(stills['bytes'])}")
        budget = thumbcache.anim_cache_budget()
        self.cache_clips_act.setText(
            f"{clips['clips']} animation clip(s) rendered  ·  {_size(clips['bytes'])}"
            + (f" of a {_size(budget)} budget" if budget > 0 else ""))
        left = self.thumbs.bulk_pending()
        self.cache_render_act.setText(f"Stop rendering ({left} to go)" if left
                                      else "Render all previews")

    def _unrendered_names(self) -> list:
        absent = self._absent_ids()
        return [m.name for m in catalog.all_models()
                if m.id not in absent and self.thumbs.cached(m.name) is None]

    def on_render_all(self):
        """Toggle the background warm-up: queue every un-rendered model behind the interactive
        requests (or stop it). After it, browsing is instant and 'Hide no-geometry' is complete --
        that filter only knows the ids a render has actually probed."""
        if self.thumbs.bulk_pending():
            self.thumbs.cancel_bulk()
        else:
            self.thumbs.request_many(self._unrendered_names())
        self._update_count()

    def on_clear_cache(self):
        if QMessageBox.question(
                self, "Clear the preview cache?",
                "Delete every rendered model preview and animation frame?\n\n"
                "Nothing of yours is lost — they are re-rendered from your FF9 install as you "
                "browse (a preview takes a fraction of a second, a clip a few seconds).") \
                != QMessageBox.StandardButton.Yes:
            return
        self.thumbs.cancel_bulk()
        self.disarm()                            # the playing clip's frames are about to vanish
        freed = thumbcache.clear_preview_cache()
        self.thumbs.invalidate()
        self._icons.clear()
        self._absent = None
        self._refill()
        if self._current is not None:            # the detail still was one of the files that just went
            it = self._items.get(self._current.name)
            if it is not None:
                self._on_select(it)
        self._count_base += f"  ·  cleared {_size(freed)}"
        self._update_count()
        self._scroll_timer.start()

    def _icon_for(self, name):
        """The row icon, resolved ONCE per session: a refill used to re-load every cached PNG from disk
        on every keystroke of the search box. FILE-BACKED (QIcon(path), not QIcon(QPixmap(path))): Qt
        defers the PNG decode to first PAINT, so a warm cache of ~700 previews costs the startup refill
        nothing -- eager decodes here were the GUI-thread seconds behind the slow-launch report. A
        RE-rendered PNG must not serve Qt's stale pixmap cache, so _thumb_ready stays eager."""
        ic = self._icons.get(name)
        if ic is not None:
            return ic
        png = self.thumbs.cached(name)
        if png:
            ic = QIcon(png)
            self._icons[name] = ic               # memo ONLY real art -- a blank must not mask a late render
            return ic
        return self._blank_icon

    def _thumb_ready(self, name, png):
        self._icons[name] = QIcon(QPixmap(png))
        it = self._items.get(name)
        if it is not None:
            it.setIcon(self._icons[name])
        if self._current is not None and self._current.name == name:
            self._refresh_facts(self._current, clips=False)   # the sidecar landed WITH the still
            if self._armed is None:
                self._set_detail_image(png)      # never over a playing clip's frame
        if self._warming():
            self._update_count()

    def _thumb_missed(self, name):
        """A render landed as a miss: when the sidecar says UNSHIPPED, grow the absent set (and, with
        the hide toggle on, drop the row live). A plain miss (no install) writes no sidecar."""
        if self._warming():
            self._update_count()
        m = catalog.model(name)
        meta = thumbs_mod.model_thumb_meta(m.id) if m else None
        if not (meta and meta.get("absent")) or m.id in self._absent_ids():
            return
        self._absent_ids().add(m.id)
        if self.no_geo.isChecked() and name in self._items:
            self._refill()

    def on_cards(self):
        """The card-grid picker over the SAME filter state; picking selects that model here."""
        dlg = modelcards.ModelCardPicker(self, self.pal, self.thumbs,
                                         initial=self.search.text().strip(),
                                         group_index=self.group.currentIndex(),
                                         field_only=self.field_only.isChecked())
        dlg.exec()
        if not dlg.result:
            return
        self.search.setText(dlg.result)          # the GEO name is an exact filter -> the row shows
        it = self._items.get(dlg.result)
        if it is not None:
            self.listw.setCurrentItem(it)        # fires _on_select -> the detail pane fills

    def _on_select(self, item, _prev=None):
        if item is None:
            return
        m = catalog.model(item.data(Qt.ItemDataRole.UserRole))
        if m is None:
            return
        self._current = m
        self.disarm()                            # a model switch cancels the old model's fill
        self.d_title.setText(f"{m.name}  ·  id {m.id}")
        world = catalog.world_character(m.name)
        sub = f"{m.kind}  ·  group {m.group} / form {m.form}"
        if world:
            sub += f"  ·  OVERWORLD actor — {world}"
        if m.field:
            sub += "  ·  field-placeable"
        self.d_sub.setText(sub)
        absent = self._refresh_facts(m)
        png = None if absent else (self.thumbs.cached(m.name) or self.thumbs.request(m.name))
        if png:
            self._set_detail_image(png)
        else:
            self.d_img.setPixmap(QPixmap())
            self.d_img.setText("no geometry" if absent else
                               ("rendering…" if thumbs_mod.enabled() else "previews off"))

    @staticmethod
    def _pose_fact(meta) -> str:
        """One short line saying what the still SHOWS, from the sidecar the render wrote. The two
        cautionary forms (rest pose / "may be a bind pose") are for RIGS only; a prop gets a line only
        when a real stand-like clip posed it. Empty for a sidecar that predates the field."""
        if not meta or "pose" not in meta:
            return ""
        action = meta.get("pose_action")
        rigged = int(meta.get("bones") or 0) >= _RIG_BONES
        if not meta.get("pose"):
            return "Shown in its REST pose — no clip on disc poses this rig." if rigged else ""
        if (meta.get("pose_rank") or 0) >= catalog.STAND_RANK_NONE:
            return (f"Posed from its ‘{action}’ clip — this rig has no idle or stand clip on disc, "
                    "so this may be a bind pose.") if rigged else ""
        if action == "000":
            return "Posed from its battle idle (clip 000)."
        return f"Posed from its ‘{action}’ clip."

    def _refresh_facts(self, m, *, clips=True) -> bool:
        """Fill the facts/notes labels; True if the model is a known UNSHIPPED id (no geometry on disc).
        ``clips=False`` leaves the clip list alone (a late-landing still must not reset the filter)."""
        meta = thumbs_mod.model_thumb_meta(m.id)
        acts = catalog.animations_for_model(m.id)
        facts = []
        absent = bool(meta and meta.get("absent"))
        if absent:
            facts.append("UNSHIPPED id: no geometry on disc (a PSX-era catalog leftover) — "
                         "nothing to preview, export, or reskin")
            meta = None
        if meta:
            facts.append(f"{meta.get('bones', '?')} bones · {meta.get('meshes', '?')} mesh part(s) · "
                         f"{meta.get('verts', '?')} verts · {len(meta.get('textures') or [])} texture(s)")
        facts.append(f"{len(acts)} animation action(s)")
        self.d_facts.setText("\n".join(facts))
        pose = self._pose_fact(meta)
        self.d_pose.setText(pose)
        self.d_pose.setVisible(bool(pose))
        notes = appearance_notes(m.name, minted=False)
        self.d_notes.setText("\n".join(notes))
        self.d_notes.setVisible(bool(notes))
        if clips:
            self._refill_clips(m)                # the comma-blob of action names is a LIST now, and
        return absent                            # every row arms the player (Stage B)

    def _set_detail_image(self, png):
        pm = QPixmap(png)
        if not pm.isNull():
            self.d_img.setText("")
            self.d_img.setPixmap(pm.scaled(_DETAIL_IMG, _DETAIL_IMG, Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))

    # ------------------------------------------------------------------ copy helpers
    def _copy_name(self):
        if self._current:
            QGuiApplication.clipboard().setText(self._current.name)

    def _copy_snippet(self):
        m = self._current
        if not m:
            return
        if m.group == "WEP":
            text = (f"# {m.name} is a battle WEAPON (a static mesh, id {m.id}).\n"
                    f"# Reskin it with Export textures… → edit the PNG → Deploy reskin PNG(s)…\n"
                    f"# (it lands at BattleMap/BattleModel/6/{m.id}/ in the mod folder)\n")
        else:
            text = (f'[[npc]]\nname = "my_npc"\nmodel = "{m.name}"\npos = [0, 0]\n'
                    f'dialogue = "Hello!"\n')
            if not m.field:
                text = f"# NOTE: {m.name} is a battle/world form — field NPCs usually wear an F* model.\n" + text
        QGuiApplication.clipboard().setText(text)

    def _copy_anims(self):
        """The five movement slots this model resolves to, as a TOML INLINE TABLE -- the line an
        [[npc]] pastes to pin its animations instead of leaning on auto-resolution."""
        m = self._current
        if not m:
            return
        a = catalog.npc_anims(m.id)
        if not a:
            return self._warn("No movement clips",
                              f"{m.name} has no field movement gestures to resolve the five slots "
                              "from (a battle-only or effect model). Give explicit ids instead.")
        body = ", ".join(f"{slot} = {a[slot]}" for slot in catalog.NPC_SLOT_ACTION if slot in a)
        QGuiApplication.clipboard().setText(f"anims = {{ {body} }}\n")

    # ------------------------------------------------------------------ actions
    def set_glb(self, path):
        """Drag-and-drop entry point (the shell routes a dropped .glb here)."""
        self.mdl_glb.setText(str(path))

    def _warn(self, title, text):
        QMessageBox.warning(self, title, text)

    def _busy(self, b):
        for btn in self._buttons:
            btn.setEnabled(not b)

    def _kit(self, args, *, subject, ok_next=""):
        self._busy(True)

        def _done(code):
            self._busy(False)
            if code == 0 and "--deploy" in args:      # the folder just changed under the list (and
                self.on_deployed_refresh()            # the id that was just minted is taken now)

        started = self._run([sys.executable, "-m", "ff9mapkit", *args], cwd=self.kit, subject=subject,
                            ok_headline=f"{subject} — done", ok_next=ok_next,
                            fail_hint="See the Output panel (model commands need UnityPy + your FF9 install).",
                            on_finished=_done)
        if not started:
            self._busy(False)

    def _sel_token(self):
        if self._current is None:
            self._warn("No model", "Pick a model in the list first.")
            return None
        return self._current.name

    def _model_mod_arg(self):
        m = self.mdl_mod.text().strip().strip('"')
        if not m:
            self._warn("No mod folder", "Pick the mod folder to deploy into (Deploy into:).")
            return None
        return m

    def on_model_gltf(self):
        token = self._sel_token()
        if token is None:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Export for Blender", f"{token}.glb",
                                             "glTF binary (*.glb)")
        if not out:
            return
        anims = ["auto", "all", "none"][self.mdl_anims.currentIndex()]
        self._kit(["model-gltf", token, "--out", out, "--anims", anims], subject="Export .glb",
                  ok_next=f"Wrote {out} — Blender: File ▸ Import ▸ glTF 2.0. Edit, export a .glb, then "
                          "Import model below.")

    def on_model_anim(self):
        token = self._sel_token()
        if token is None:
            return
        d = QFileDialog.getExistingDirectory(self, "Folder to write the Animations/<id>/ clip JSONs into")
        if not d:
            return
        self._kit(["model-anim", token, "--out", d], subject="Dump clips",
                  ok_next=f"Wrote editable .anim JSON under {d}. Edit values, then copy the file into a mod "
                          "folder's StreamingAssets/Assets/Resources/Animations/<id>/ and RELAUNCH.")

    def on_model_import(self):
        glb = self.mdl_glb.text().strip().strip('"')
        if not glb or not Path(glb).is_file():
            return self._warn("No .glb", "Pick the edited .glb you exported from Blender.")
        mod = self._model_mod_arg()
        if mod is None:
            return
        # The kit auto-detects the source GEO from a stamp it embeds in asset.extras/node.extras -- but
        # Blender's own glTF exporter only carries that through if "Include > Custom Properties" is
        # checked (off by default), so a bare re-export commonly loses it. Fall back to the model still
        # selected in the browser (the natural "export this, edit it, import it back" flow) rather than
        # dead-ending on "needs --id".
        args = ["model-import", glb]
        if self._current is not None:
            args += ["--like", self._current.name]
        args += ["--deploy", mod]
        self._kit(args, subject="Import model",
                  ok_next="Override deployed. Mesh edits: ~ → Reload on a field using the model. "
                          "Edited animations need a game RELAUNCH.")

    def on_model_mint(self):
        token = self._sel_token()
        if token is None:
            return
        mod = self._model_mod_arg()
        if mod is None:
            return
        mid = self.mdl_mint_id.text().strip()
        if not mid.isdigit() or int(mid) < _MINT_FLOOR:
            return self._warn("Bad id", "The mint id must be a number ≥ 6000 (below is the real-model band).")
        from ..models import deployed
        try:
            taken = int(mid) in deployed.mint_ids_in_use(mod)
        except OSError:
            taken = False
        if taken and QMessageBox.question(
                self, "That id is already minted",
                f"{mod} already has a minted model at id {mid}.\n\nMinting {token} there REPLACES "
                f"it. The next free id is {deployed.next_mint_id(mod, floor=_MINT_FLOOR)}.\n\n"
                f"Replace id {mid}?") != QMessageBox.StandardButton.Yes:
            return
        self._kit(["model-mint", token, "--id", mid, "--deploy", mod], subject="Mint model",
                  ok_next=f"Minted id {mid} + registered it in DictionaryPatch.txt. RELAUNCH FF9, then "
                          f"place it with [[npc]] model = {mid} (its animations came along from the source).")

    def on_model_textures(self):
        token = self._sel_token()
        if token is None:
            return
        d = QFileDialog.getExistingDirectory(self, "Folder to write the editable texture PNGs into")
        if not d:
            return
        self._kit(["model-reskin", token, "--export-textures", d], subject="Export textures",
                  ok_next=f"Wrote the pristine PNGs to {d}. Edit them in any image editor (any size "
                          "works), KEEP THE NAMES, then Deploy reskin PNG(s)…")

    def on_model_reskin(self):
        token = self._sel_token()
        if token is None:
            return
        mod = self._model_mod_arg()
        if mod is None:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "The edited reskin PNG(s)", "",
                                                "PNG images (*.png)")
        if not files:
            return
        self._kit(["model-reskin", token, "--deploy", mod, "--texture", *files], subject="Deploy reskin",
                  ok_next="Reskin deployed. Field models: ~ → Reload field. Battle/weapon models load "
                          "on battle entry — a RELAUNCH is the sure path.")

    def browse_model_mod(self):
        d = QFileDialog.getExistingDirectory(self, "Mod folder to deploy models into")
        if d:
            self.mdl_mod.setText(d)

    def browse_model_glb(self):
        f, _ = QFileDialog.getOpenFileName(self, "The Blender-edited glTF", "", "glTF (*.glb *.gltf)")
        if f:
            self.mdl_glb.setText(f)

    # ------------------------------------------------------------------ shell hooks
    def crumb_label(self):
        return self._current.name if self._current else "browse 3D models"
