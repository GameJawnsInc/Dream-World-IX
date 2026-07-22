"""The card-grid model picker -- a big visual browse over the GEO catalog.

The Models tab's list (and the catalog picker's text rows) identify a model by NAME; finding "the
one you want" among ~2000 rows is really a VISUAL search, so this dialog shows the same catalog as a
grid of thumbnail CARDS: search + group / field-only / no-geometry filters on top, the art large
enough to recognize, double-click (or Use this) returns the GEO name.

Preview discipline: thumbnails come through the SHARED :class:`~.thumbs.ModelThumbService` -- warm
disk cache answers instantly (one stat), cold renders are requested ONLY for the cards actually in
view (scroll-driven, debounced), so opening the dialog never floods the render queue with 2000 jobs.
A machine without the install degrades to labeled cards with no art.

The no-geometry filter reads the render worker's ``absent`` sidecars (models PROBED and found
unshipped -- PSX-era catalog leftovers with nothing to place, preview, or reskin). It is honest
about its source: a fresh cache hides nothing, and the set grows live as renders land
(:attr:`~.thumbs.ModelThumbService.missed`).
"""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QListView, QPushButton, QVBoxLayout)

from .. import catalog
from ..models import thumbcache
from . import thumbs as thumbs_mod, widgets

CARD_ICON = 112                                  # card art size (px; the 256px cache PNG scales down)
_VISIBLE_BATCH = 80                              # max cold renders enqueued per scroll settle
_SCROLL_MS = 150                                 # scroll-settle debounce before requesting renders

# combo label -> catalog.models(group=...) arg (None = all). Shared with the Models tab (one list,
# one order -- the tab's smoke indexes into it by position).
GROUPS = [
    ("All groups", None),
    ("Characters (MAIN)", "MAIN"),
    ("NPCs", "NPC"),
    ("Monsters", "MON"),
    ("Sub && world (SUB)", "SUB"),
    ("Weapons (WEP)", "WEP"),
    ("Accessories (ACC)", "ACC"),
]


def absent_geo_ids() -> set:
    """The probed no-geometry id set (one sidecar scan; empty on a fresh cache)."""
    return thumbcache.absent_ids()


def filter_models(query, group, *, field_only=False, hide_absent=False, absent=frozenset()):
    """The shared browse filter: ``(entries, hidden_count)``. ``hide_absent`` drops the ids in
    ``absent`` (the probed no-geometry set) and reports how many it dropped -- the count label says
    so, so rows never vanish silently."""
    entries = catalog.models(query or None, group=group, field_only=field_only)
    if hide_absent and absent:
        kept = [m for m in entries if m.id not in absent]
        return kept, len(entries) - len(kept)
    return entries, 0


def _card_label(m) -> str:
    """Two card lines: the GEO name minus its constant prefix (fits the grid cell), then the id."""
    short = m.name[4:] if m.name.startswith("GEO_") else m.name
    return f"{short}\nid {m.id}"


class ModelCardPicker(QDialog):
    """A modal card grid over ``catalog.models``; ``result`` is the chosen GEO name (or None)."""

    def __init__(self, parent, palette, model_thumbs, *, initial="", group_index=0,
                 field_only=False, hide_no_geometry=True):
        super().__init__(parent)
        self.setWindowTitle("Pick a model")
        self.pal = palette
        self.thumbs = model_thumbs
        self.result = None
        self._entries = []
        self._items = {}                         # geo name -> QListWidgetItem (current filter)
        self._icons = {}                         # geo name -> QIcon (decode each cache PNG once)
        # gated like every other cache read: a NO_THUMBS run never scans the real preview cache
        self._absent = absent_geo_ids() if thumbs_mod.enabled() else set()
        self._blank = QPixmap(CARD_ICON, CARD_ICON)   # constant-size placeholder: cards never reflow
        self._blank.fill(Qt.GlobalColor.transparent)
        self._blank_icon = QIcon(self._blank)
        if self.thumbs is not None:              # receiver-scoped connects: Qt drops them with the dialog
            self.thumbs.ready.connect(self._thumb_ready)
            self.thumbs.missed.connect(self._thumb_missed)

        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.q = QLineEdit(initial or "")
        self.q.setAccessibleName("Search models")
        self.q.setPlaceholderText("Search by name, token, or a friendly name — vivi, GRN, MON_B3…")
        self.q.textChanged.connect(self._refill)
        self.q.returnPressed.connect(self._ok)
        top.addWidget(self.q, 1)
        self.group = QComboBox()
        self.group.setAccessibleName("Filter models by group")
        for label, _arg in GROUPS:
            self.group.addItem(label)
        self.group.setCurrentIndex(group_index)
        self.group.currentIndexChanged.connect(self._refill)
        top.addWidget(self.group)
        lay.addLayout(top)
        frow = QHBoxLayout()
        self.field_only = QCheckBox("Field-placeable only")
        self.field_only.setToolTip("Keep the field-form (F*) models — the ones an [[npc]] can wear.")
        self.field_only.setChecked(bool(field_only))
        self.field_only.toggled.connect(self._refill)
        frow.addWidget(self.field_only)
        self.no_geo = QCheckBox("Hide models with no geometry")
        self.no_geo.setToolTip("Drop the ids probed as UNSHIPPED (PSX-era catalog leftovers with "
                               "nothing to place or preview). The set fills in as previews render — "
                               "a fresh cache hides nothing yet.")
        self.no_geo.setChecked(bool(hide_no_geometry))
        self.no_geo.toggled.connect(self._refill)
        frow.addWidget(self.no_geo)
        frow.addStretch(1)
        lay.addLayout(frow)

        self.listw = QListWidget()
        self.listw.setAccessibleName("Model cards")
        self.listw.setViewMode(QListView.ViewMode.IconMode)
        self.listw.setResizeMode(QListView.ResizeMode.Adjust)
        self.listw.setMovement(QListView.Movement.Static)
        self.listw.setUniformItemSizes(True)
        self.listw.setIconSize(QSize(CARD_ICON, CARD_ICON))
        self.listw.setGridSize(QSize(CARD_ICON + 44, CARD_ICON + 54))
        self.listw.setSpacing(4)
        self.listw.itemDoubleClicked.connect(lambda _i: self._ok())
        self.listw.currentItemChanged.connect(self._describe)
        lay.addWidget(self.listw, 1)

        self.info = QLabel("")
        self.info.setProperty("role", "muted")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        bar = QHBoxLayout()
        use = QPushButton("Use this")
        use.setObjectName("accent")
        use.clicked.connect(self._ok)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        bar.addWidget(use)
        bar.addWidget(cancel)
        bar.addStretch(1)
        lay.addLayout(bar)

        # scroll-driven renders: request only what the viewport shows, after the scroll settles
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.setInterval(_SCROLL_MS)
        self._scroll_timer.timeout.connect(self._request_visible)
        self.listw.verticalScrollBar().valueChanged.connect(lambda _v: self._scroll_timer.start())

        self._refill()
        widgets.fit_dialog(self, ch=150, list_rows=4, lines=0)
        self.q.setFocus()

    # ------------------------------------------------------------------ fill + filters
    def _refill(self, *_a):
        cur = self.listw.currentItem()
        keep = cur.data(Qt.ItemDataRole.UserRole) if cur is not None else None
        grp = GROUPS[self.group.currentIndex()][1]
        self._entries, hidden = filter_models(self.q.text().strip(), grp,
                                              field_only=self.field_only.isChecked(),
                                              hide_absent=self.no_geo.isChecked(),
                                              absent=self._absent)
        self.listw.clear()
        self._items = {}
        for m in self._entries:
            it = QListWidgetItem(_card_label(m))
            it.setData(Qt.ItemDataRole.UserRole, m.name)
            it.setToolTip(f"{m.name}  ·  id {m.id}")
            it.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            it.setIcon(self._icon_for(m.name))
            self.listw.addItem(it)
            self._items[m.name] = it
        if keep is not None and keep in self._items:     # a live absent-set update must not steal the pick
            self.listw.setCurrentItem(self._items[keep])
        note = f"  ·  {hidden} with no geometry hidden" if hidden else ""
        off = "" if thumbs_mod.enabled() else "  ·  previews off"
        self.info.setText(f"{len(self._entries)} model(s){note}{off}")
        self._scroll_timer.start()               # request the (new) visible set once the layout settles

    def _icon_for(self, name) -> QIcon:
        ic = self._icons.get(name)
        if ic is not None:
            return ic
        png = self.thumbs.cached(name) if self.thumbs is not None else None
        if png:
            ic = QIcon(QPixmap(png))
            self._icons[name] = ic               # memo ONLY real art -- a blank must not mask a late render
            return ic
        return self._blank_icon

    def _request_visible(self):
        """Enqueue renders for the cards in (or one row shy of) the viewport -- never the whole list."""
        if self.thumbs is None or not thumbs_mod.enabled():
            return
        vp = self.listw.viewport().rect().adjusted(0, -CARD_ICON, 0, CARD_ICON)
        n = 0
        for name, it in self._items.items():
            if n >= _VISIBLE_BATCH:
                break
            r = self.listw.visualItemRect(it)
            if r.isValid() and r.intersects(vp):
                if self.thumbs.cached(name) is None:
                    self.thumbs.request(name)
                    n += 1
            elif r.isValid() and r.top() > vp.bottom():
                break                            # items lay out in row order -- past the fold, done

    # ------------------------------------------------------------------ async arrivals
    def _thumb_ready(self, name, png):
        it = self._items.get(name)
        if it is None:
            return
        ic = QIcon(QPixmap(png))
        self._icons[name] = ic
        it.setIcon(ic)

    def _thumb_missed(self, name):
        """A render landed as a miss: if the sidecar says UNSHIPPED, grow the absent set (and re-filter
        live when the hide toggle is on). A plain miss (no install) writes no sidecar and changes nothing."""
        m = catalog.model(name)
        meta = thumbcache.model_thumb_meta(m.id) if m else None
        if not (meta and meta.get("absent")):
            return
        if m.id in self._absent:
            return
        self._absent.add(m.id)
        if self.no_geo.isChecked() and name in self._items:
            self._refill()

    # ------------------------------------------------------------------ selection
    def _describe(self, item, _prev=None):
        if item is None:
            return
        m = catalog.model(item.data(Qt.ItemDataRole.UserRole))
        if m is None:
            return
        bits = [f"{m.name}  ·  id {m.id}", m.kind, f"group {m.group} / form {m.form}"]
        if m.field:
            bits.append("field-placeable")
        if m.id in self._absent:
            bits.append("no geometry on disc")
        self.info.setText("  ·  ".join(bits))

    def _ok(self):
        it = self.listw.currentItem()
        if it is None and len(self._entries) == 1:
            it = self.listw.item(0)
        if it is None:
            return
        self.result = it.data(Qt.ItemDataRole.UserRole)
        self.accept()
