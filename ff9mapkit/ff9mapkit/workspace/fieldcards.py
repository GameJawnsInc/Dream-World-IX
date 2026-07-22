"""The field card picker -- FF9's ~818 real fields as background-art cards, categorized by REGION.

The sibling of :mod:`.modelcards`, for the other visual search: choosing a fork donor. Text rows
(``Find…``'s picker) identify a field by name; recognizing "the room I mean" is a VISUAL job, so this
dialog shows every real field as a card of its actual pre-rendered background, with a REGION list on
the left (Prima Vista, A. Castle, Alexandria, … -- derived from the field names' place prefix, ordered
by first field id = rough story order) dividing the catalog into the game's places.

Art comes through the SHARED field :class:`~.thumbs.ThumbService` (the same composites the campaign
Map and Inspector show): warm disk cache answers instantly; cold composites render on the worker ONLY
for the cards actually in view (scroll-driven, debounced -- a composite is seconds each, and the
first-ever render also builds the field index, so flooding the queue is never acceptable). A machine
without the install degrades to labeled cards with no art.

Entry points: the Import tab's **Cards…** (fills the source id) and the realfield picker's
**Card view…** (answers the picker). ``result`` is the field id as a string.
"""
from __future__ import annotations

from typing import NamedTuple

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLineEdit, QLabel, QListView, QListWidget,
                               QListWidgetItem, QPushButton, QSplitter, QVBoxLayout, QWidget)

from .. import infohub
from . import thumbs as thumbs_mod, widgets

CARD_W, CARD_H = 168, 118                       # card art size (px; the 360px cache PNG scales down)
_VISIBLE_BATCH = 40                             # max cold composites enqueued per scroll settle (seconds EACH)
_SCROLL_MS = 150
_KEY = "fieldcards:"                            # the ThumbService member-key namespace this dialog owns


class FieldEntry(NamedTuple):
    """One real field: ``region`` is the place prefix of its human name ('Prima Vista/Cargo Room')."""
    id: int
    region: str
    room: str
    name: str
    summary: str


def field_entries() -> list:
    """Every real field as a :class:`FieldEntry` (the ``realfield`` Info-Hub kind -- baked, offline)."""
    out = []
    for e in infohub.browse("", kinds=["realfield"], limit=None):
        region, _sep, room = e.name.partition("/")
        out.append(FieldEntry(int(e.ident), region, room or e.name, e.name, e.summary))
    return out


def regions_of(entries) -> list:
    """``[(region, count)]`` ordered by each region's FIRST field id -- roughly story order."""
    firsts, counts = {}, {}
    for e in entries:
        firsts.setdefault(e.region, e.id)
        firsts[e.region] = min(firsts[e.region], e.id)
        counts[e.region] = counts.get(e.region, 0) + 1
    return [(r, counts[r]) for r in sorted(firsts, key=firsts.get)]


class FieldCardPicker(QDialog):
    """A modal region-divided card grid over the real fields; ``result`` is the field id (str) or None."""

    def __init__(self, parent, palette, field_thumbs, *, initial=""):
        super().__init__(parent)
        self.setWindowTitle("Pick a real field")
        self.pal = palette
        self.thumbs = field_thumbs
        self.result = None
        self._all = field_entries()
        self._entries = []
        self._items = {}                         # field id -> QListWidgetItem (current filter)
        self._icons = {}                         # field id -> QIcon (decode each cache PNG once)
        self._blank = QPixmap(CARD_W, CARD_H)
        self._blank.fill(Qt.GlobalColor.transparent)
        self._blank_icon = QIcon(self._blank)
        if self.thumbs is not None:              # receiver-scoped connect: Qt drops it with the dialog
            self.thumbs.ready.connect(self._thumb_ready)

        lay = QVBoxLayout(self)
        split = QSplitter()
        lay.addWidget(split, 1)

        # ---- left: the region list (the categories) ----
        self.regions = QListWidget()
        self.regions.setAccessibleName("Regions")
        self.regions.addItem(f"All regions  ·  {len(self._all)}")
        self.regions.item(0).setData(Qt.ItemDataRole.UserRole, None)
        for region, count in regions_of(self._all):
            it = QListWidgetItem(f"{region}  ·  {count}")
            it.setData(Qt.ItemDataRole.UserRole, region)
            self.regions.addItem(it)
        self.regions.setCurrentRow(0)
        self.regions.currentRowChanged.connect(self._refill)
        split.addWidget(self.regions)

        # ---- right: search + the card grid ----
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(6, 0, 0, 0)
        self.q = QLineEdit(initial or "")
        self.q.setAccessibleName("Search fields")
        self.q.setPlaceholderText("Search by place, room, id, or FBG name — cargo, 1205, alxt_map016…")
        self.q.textChanged.connect(self._refill)
        self.q.returnPressed.connect(self._ok)
        rv.addWidget(self.q)
        self.listw = QListWidget()
        self.listw.setAccessibleName("Field cards")
        self.listw.setViewMode(QListView.ViewMode.IconMode)
        self.listw.setResizeMode(QListView.ResizeMode.Adjust)
        self.listw.setMovement(QListView.Movement.Static)
        self.listw.setUniformItemSizes(True)
        self.listw.setIconSize(QSize(CARD_W, CARD_H))
        self.listw.setGridSize(QSize(CARD_W + 18, CARD_H + 52))
        self.listw.setSpacing(4)
        self.listw.itemDoubleClicked.connect(lambda _i: self._ok())
        self.listw.currentItemChanged.connect(self._describe)
        rv.addWidget(self.listw, 1)
        self.info = QLabel("")
        self.info.setProperty("role", "muted")
        self.info.setWordWrap(True)
        rv.addWidget(self.info)
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)

        bar = QHBoxLayout()
        use = QPushButton("Use this")
        use.setObjectName("accent")
        use.clicked.connect(self._ok)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        bar.addWidget(use)
        bar.addWidget(cancel)
        bar.addStretch(1)
        if thumbs_mod.enabled():
            bar.addWidget(widgets.caption("Art renders in the background as you browse — the very "
                                          "first browse also builds the field index (~1–2 min)."))
        bar.addStretch(2)
        lay.addLayout(bar)

        self._scroll_timer = QTimer(self)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.setInterval(_SCROLL_MS)
        self._scroll_timer.timeout.connect(self._request_visible)
        self.listw.verticalScrollBar().valueChanged.connect(lambda _v: self._scroll_timer.start())

        self._refill()
        widgets.fit_dialog(self, ch=170, list_rows=4, lines=0)
        self.q.setFocus()

    # ------------------------------------------------------------------ fill + filters
    def _region(self):
        it = self.regions.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it is not None else None

    def _refill(self, *_a):
        cur = self.listw.currentItem()
        keep = cur.data(Qt.ItemDataRole.UserRole) if cur is not None else None
        region = self._region()
        q = (self.q.text() or "").strip().lower()
        self._entries = [e for e in self._all
                         if (region is None or e.region == region)
                         and (not q or q in e.name.lower() or q in e.summary.lower()
                              or q == str(e.id))]
        self.listw.clear()
        self._items = {}
        for e in self._entries:
            it = QListWidgetItem(f"{e.room}\n#{e.id}")
            it.setData(Qt.ItemDataRole.UserRole, e.id)
            it.setToolTip(f"{e.name}  ·  {e.summary}")
            it.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            it.setIcon(self._icon_for(e.id))
            self.listw.addItem(it)
            self._items[e.id] = it
        if keep is not None and keep in self._items:
            self.listw.setCurrentItem(self._items[keep])
        where = f" in {region}" if region else ""
        off = "" if thumbs_mod.enabled() else "  ·  previews off"
        self.info.setText(f"{len(self._entries)} field(s){where}{off}")
        self._scroll_timer.start()

    def _icon_for(self, fid) -> QIcon:
        ic = self._icons.get(fid)
        if ic is not None:
            return ic
        png = self.thumbs.cached(f"{_KEY}{fid}") if self.thumbs is not None else None
        if png:
            ic = QIcon(QPixmap(png))
            self._icons[fid] = ic                # memo ONLY real art -- a blank must not mask a late render
            return ic
        return self._blank_icon

    def _request_visible(self):
        """Enqueue composites for the cards in (or one row shy of) the viewport -- never the list."""
        if self.thumbs is None or not thumbs_mod.enabled():
            return
        vp = self.listw.viewport().rect().adjusted(0, -CARD_H, 0, CARD_H)
        n = 0
        for fid, it in self._items.items():
            if n >= _VISIBLE_BATCH:
                break
            r = self.listw.visualItemRect(it)
            if r.isValid() and r.intersects(vp):
                if self.thumbs.cached(f"{_KEY}{fid}") is None:
                    self.thumbs.request(f"{_KEY}{fid}", None, fid)
                    n += 1
            elif r.isValid() and r.top() > vp.bottom():
                break                            # row order -- past the fold, done

    # ------------------------------------------------------------------ async arrivals
    def _thumb_ready(self, member, png):
        if not member.startswith(_KEY):          # the shared service also serves the Map/Inspector
            return
        try:
            fid = int(member[len(_KEY):])
        except ValueError:
            return
        it = self._items.get(fid)
        if it is None:
            return
        ic = QIcon(QPixmap(png))
        self._icons[fid] = ic
        it.setIcon(ic)

    # ------------------------------------------------------------------ selection
    def _describe(self, item, _prev=None):
        if item is None:
            return
        e = next((x for x in self._entries if x.id == item.data(Qt.ItemDataRole.UserRole)), None)
        if e is None:
            return
        self.info.setText(f"{e.name}  ·  field #{e.id}  ·  {e.summary}")

    def _ok(self):
        it = self.listw.currentItem()
        if it is None and len(self._entries) == 1:
            it = self.listw.item(0)
        if it is None:
            return
        self.result = str(it.data(Qt.ItemDataRole.UserRole))
        self.accept()
