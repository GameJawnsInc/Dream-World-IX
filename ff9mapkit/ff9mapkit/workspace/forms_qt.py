"""A generic Qt form renderer for :mod:`..editor.forms` specs (Phase 4 of the GUI makeover).

Builds a Qt form (a labelled widget per :class:`..editor.forms.Field`) + a dict of value getters from a
spec + flat values. Saving goes through ``forms.build_entity`` -- the SAME tk-free parser the tkinter
editor uses -- so a field edited in the Qt shell round-trips byte-identically to one edited in the old
editor. The renderer is thin; all parsing/validation stays in ``editor.forms`` (unit-tested headless).

Mapping: BOOL -> QCheckBox, PRESET -> an editable QComboBox seeded with the archetype names (a custom
string is still accepted), everything else -> a QLineEdit. A catalog-backed field also gets a "Browse…"
button wired to :class:`CatalogPicker`, which reuses the UI-agnostic ``infohub.browse`` spine (exactly
like the tkinter editor's picker) so the two stay in lockstep.
"""

from __future__ import annotations

import collections
import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QPlainTextEdit, QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

from .. import dialogue as _dlg
from .. import infohub
from ..content.text import DEFAULT_WRAP_WIDTH
from ..editor import forms

# Fields whose value is a line shown in an FF9 text window -> they get a live wrap-preview (FF9 never
# auto-wraps, so the kit pre-breaks long lines; this shows exactly where). Keys match editor.forms specs.
DIALOGUE_KEYS = {"dialogue", "message", "prompt", "reply"}


def _wrap_preview_panel(line_edit, get_text, palette, wrap_width):
    """A read-only pane under a dialogue field: how the line breaks on the FF9 screen, live as you type.
    Reuses the exact build-time wrapper (:func:`..dialogue.wrap_preview`). ``wrap_width`` None = the field
    set ``[dialogue] wrap = false`` (author wraps by hand) -> show the text raw, no preview break."""
    panel = QWidget()
    pv = QVBoxLayout(panel)
    pv.setContentsMargins(0, 3, 0, 0)
    pv.setSpacing(2)
    cap = QLabel("On-screen preview — how it wraps in the FF9 window:")
    cap.setStyleSheet(f"color:{palette['muted']};font-size:11px;")
    pv.addWidget(cap)
    box = QPlainTextEdit()
    box.setReadOnly(True)
    box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)     # show the kit's OWN break points, not Qt's
    box.setFixedHeight(74)
    pv.addWidget(box)
    # The note is ALWAYS in the layout at a fixed height (it carries the warning OR a quiet "fits" line):
    # toggling visibility would change the panel height and, inside the nested form/scroll, clip the
    # fixed-height box on the way back. A constant-height panel can't reflow.
    note = QLabel("")
    note.setFixedHeight(16)
    pv.addWidget(note)

    def refresh(*_):
        txt = get_text() or ""
        box.setPlainText((_dlg.wrap_preview(txt, wrap_width) if wrap_width is not None else txt) or "(empty)")
        over = _dlg.overflow(txt, wrap_width) if (txt and wrap_width is not None) else []
        if over:
            note.setText(f"⚠ {len(over)} line(s) may overflow the window — verify in-game.")
            note.setStyleSheet(f"color:{palette['warn']};font-size:11px;")
        elif txt:
            note.setText("✓ fits the window")
            note.setStyleSheet(f"color:{palette['muted']};font-size:11px;")
        else:
            note.setText("")

    line_edit.textChanged.connect(refresh)
    refresh()
    return panel


def _changed_signal(widget):
    """The 'value changed' signal of a form widget (QLineEdit/QPlainTextEdit textChanged, QComboBox
    currentTextChanged, QCheckBox toggled), or None."""
    for attr in ("textChanged", "currentTextChanged", "toggled"):
        sig = getattr(widget, attr, None)
        if sig is not None:
            return sig
    return None


def build_form(spec, values: dict, palette: dict, pick=None, wrap_width=DEFAULT_WRAP_WIDTH, on_change=None):
    """Return ``(widget, getters)`` for ``spec`` + flat ``values`` (from ``forms.entity_to_values``).

    ``getters`` maps each field key to a 0-arg callable returning the widget's current value. ``pick``
    (optional) is ``pick(catalog: str, current: str) -> str | None``; when given, catalog-backed fields
    get a "Browse…" button that calls it and writes the chosen name back into the widget. Dialogue-bearing
    fields (:data:`DIALOGUE_KEYS`) get a live FF9-window wrap preview at ``wrap_width`` (None = wrapping off
    for this field -> show the line raw). ``on_change`` (optional) is called on ANY edit (for dirty
    tracking); each field is ALSO validated live -- a bad value turns its hint red with the parse error."""
    w = QWidget()
    lay = QFormLayout(w)
    lay.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)
    lay.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    lay.setHorizontalSpacing(14)
    lay.setVerticalSpacing(10)
    getters = {}
    hints = {}                                         # field key -> its hint QLabel (help text / live error)
    editable = []                                      # (key, widget) for wiring change -> validate + on_change
    muted_style = f"color:{palette['muted']};font-size:11px;"
    err_style = f"color:{palette['error']};font-size:11px;"

    def browse(field, getter, setter):
        name = pick(field.catalog, getter())
        if name:
            setter(name)

    for f in spec:
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        setter = None
        if f.kind == forms.BOOL:
            cb = QCheckBox()
            cb.setChecked(bool(values.get(f.key, f.default)))
            widget, getters[f.key] = cb, cb.isChecked
        elif f.kind == forms.PRESET:
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItems(list(forms.PRESETS))
            combo.setCurrentText(str(values.get(f.key, "") or ""))
            widget, getters[f.key], setter = combo, combo.currentText, combo.setCurrentText
        elif f.key in DIALOGUE_KEYS:
            # MULTI-LINE: dialogue carries explicit line breaks (Enter = a real \n, which is FF9's native
            # in-window line break; type [PAGE] for a new window). QLineEdit collapses newlines -> use a
            # plain text box. toPlainText returns real \n, preserved through build_entity/TOML/.mes. We ALSO
            # accept a typed literal "\n" (two chars, a common habit) and normalize it to a real newline, so
            # the preview, the saved .toml and the .mes all agree -- the getter does that normalization.
            te = QPlainTextEdit(str(values.get(f.key, "") or ""))
            te.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
            te.setTabChangesFocus(True)            # Tab -> next field (Enter is the line break, not Tab)
            te.setFixedHeight(72)                   # ~4 lines, like the old Dialogue Editor
            te.setToolTip("Line break: press Enter, or type \\n.   New window: type [PAGE].")
            widget, setter = te, te.setPlainText
            getters[f.key] = lambda box=te: box.toPlainText().replace("\\n", "\n")
        else:
            le = QLineEdit(str(values.get(f.key, "") or ""))
            if f.catalog:
                le.setPlaceholderText(f"a {f.catalog.split(',')[0]} name or id")
            widget, getters[f.key], setter = le, le.text, le.setText
        if f.catalog and pick is not None and setter is not None:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(widget, 1)
            b = QPushButton("Browse…")
            b.clicked.connect(lambda _=False, ff=f, g=getters[f.key], st=setter: browse(ff, g, st))
            row.addWidget(b)
            v.addLayout(row)
        else:
            v.addWidget(widget)
        hint = QLabel(f.help or "")                    # always present (hidden if no help) so a live error
        hint.setWordWrap(True)                          # has somewhere to show
        hint.setStyleSheet(muted_style)
        v.addWidget(hint)                               # PARENT it BEFORE setVisible: setVisible(True) on a
        hint.setVisible(bool(f.help))                   # parentless widget flashes a top-level window (Windows)
        hints[f.key] = hint
        editable.append((f.key, widget))
        if f.key in DIALOGUE_KEYS and hasattr(widget, "textChanged"):
            v.addWidget(_wrap_preview_panel(widget, getters[f.key], palette, wrap_width))
        label = QLabel(f.label + ":")
        label.setStyleSheet("font-weight:500;")
        lay.addRow(label, box)

    def validate():
        """Live per-field check: a value that fails its parser turns the hint red with the error; an OK
        field shows its normal help. Returns the count of invalid fields."""
        bad = 0
        for f in spec:
            if f.kind == forms.BOOL:
                continue
            h = hints[f.key]
            try:
                forms._parse_field(f.kind, getters[f.key]())
            except ValueError as e:
                h.setText(f"⚠  {e}")
                h.setStyleSheet(err_style)
                h.setVisible(True)
                bad += 1
                continue
            h.setText(f.help or "")
            h.setStyleSheet(muted_style)
            h.setVisible(bool(f.help))
        return bad

    def on_field_change():
        validate()
        if on_change:
            on_change()
    for _key, widget in editable:
        sig = _changed_signal(widget)
        if sig is not None:
            sig.connect(on_field_change)
    validate()                                          # seed the initial state (loaded values are valid)
    w.validate = validate                               # expose for tests / an external re-check
    return w, getters


def read(getters: dict) -> dict:
    """Collect the current ``{key: value}`` from a getters dict (call each getter)."""
    return {k: g() for k, g in getters.items()}


class CatalogPicker(QDialog):
    """A modal Info-Hub catalog picker: search + a result list, returning the chosen entry NAME. Reuses
    the same ``infohub.browse`` spine as the tkinter editor's picker (archetype/creature/item/flag/...)."""

    def __init__(self, parent, kinds, initial, plan, palette, *, browse=False, limit=300):
        super().__init__(parent)
        self.setWindowTitle("Browse the catalog" if browse else "Pick from the catalog")
        self.resize(560, 460)
        self.kinds = kinds
        self.plan = plan
        self.browse = browse                           # browse mode: "Use this" copies the name + stays open
        self.limit = limit
        self.result = None
        self._entries = []
        lay = QVBoxLayout(self)
        self.q = QLineEdit(initial or "")
        self.q.setPlaceholderText("Search…")
        self.q.textChanged.connect(self._refresh)
        self.q.returnPressed.connect(self._ok)
        lay.addWidget(self.q)
        self.lst = QListWidget()
        self.lst.itemDoubleClicked.connect(lambda _i: self._ok())
        self.lst.currentRowChanged.connect(self._describe)
        lay.addWidget(self.lst, 1)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setStyleSheet(f"color:{palette['muted']};")
        lay.addWidget(self.info)
        bar = QHBoxLayout()
        use = QPushButton("Copy name" if browse else "Use this")
        use.setObjectName("accent")
        use.clicked.connect(self._ok)
        cancel = QPushButton("Close" if browse else "Cancel")
        cancel.clicked.connect(self.reject)
        bar.addWidget(use)
        bar.addWidget(cancel)
        bar.addStretch(1)
        lay.addLayout(bar)
        self._refresh()
        self.q.setFocus()

    def _refresh(self):
        try:
            self._entries = infohub.browse(self.q.text(), kinds=self.kinds, limit=self.limit,
                                           campaign_context=self.plan)
        except Exception:                              # noqa: BLE001 -- a catalog needing data we lack
            self._entries = []
        self.lst.clear()
        for e in self._entries:
            self.lst.addItem(f"{e.name}    [{e.kind}]")
        where = f" in {', '.join(self.kinds)}" if self.kinds else ""
        capped = self.limit is not None and len(self._entries) >= self.limit
        note = " (capped — type to narrow)" if capped else ""
        self.info.setText(f"{len(self._entries)} match(es){where}{note}")

    def _describe(self, row):
        if 0 <= row < len(self._entries):
            e = self._entries[row]
            self.info.setText(f"{e.name}  [{e.kind}]  —  {e.summary}")

    def _ok(self):
        row = self.lst.currentRow()
        if row < 0 and len(self._entries) == 1:
            row = 0
        if not (0 <= row < len(self._entries)):
            return
        e = self._entries[row]
        if self.browse:                                # Info Hub browse: copy the name, keep browsing
            QApplication.clipboard().setText(e.name)
            self.info.setText(f"Copied “{e.name}” [{e.kind}] to the clipboard.")
            return
        self.result = e.name
        self.accept()


def pick_catalog(parent, catalog, initial, plan, palette):
    """Open :class:`CatalogPicker` for a comma-separated ``catalog`` string; return the chosen name or
    None. The shell passes this (curried with its window/plan/palette) as ``build_form``'s ``pick``."""
    kinds = [k.strip() for k in catalog.split(",")] if catalog else None
    dlg = CatalogPicker(parent, kinds, initial, plan, palette)
    dlg.exec()
    return dlg.result


# friendly section names for the Info Hub library sidebar (one per catalog 'kind').
_KIND_LABEL = {
    "field": "Campaign fields", "flag": "Campaign flags",
    "archetype": "Archetypes", "creature": "Creatures", "composite": "Composites",
    "prop": "Props", "model": "Models", "item": "Items", "scene": "Battle scenes",
    "storyflag": "Story flags",
}
# sidebar order: the open campaign's OWN content first, then the static catalogs (in infohub.KINDS order).
_LIBRARY_ORDER = ("field", "flag") + infohub.KINDS


def _esc(s) -> str:
    return html.escape(str(s))


# one-line glossary per catalog kind -- the Info Hub Help button (so 'archetype' etc. is self-explanatory).
_HUB_HELP = {
    "archetype": "named, NPC-ready character types (the playable cast + NPC types). Place with "
                 "<code>[[npc]] archetype = \"name\"</code> — the model + its animations/movement resolve for you.",
    "creature": "<code>GEO_MON</code> monster field objects (also placed as an NPC, by name).",
    "composite": "multi-part set pieces — several models posed together as one object.",
    "prop": "single static set-dressing (chests, signs, barrels). Place with <code>[[prop]] prop = \"name\"</code>.",
    "model": "the raw GEO models by their engine name — the lowest level, no animation join.",
    "item": "item / equipment names (+ stats read from your install).",
    "scene": "battle encounter scenes, by id.",
    "storyflag": "FF9's built-in story-state registry — named engine vars, scenario beats, reserved bit regions.",
    "field": "the fields in the OPEN campaign (this section shows only when a campaign is loaded).",
    "flag": "the named story flags in the OPEN campaign.",
}


def _hub_help_html() -> str:
    """The Info Hub help text: a one-line intro, the per-section glossary (static catalogs first, the
    campaign-only sections last), and how Copy name / Copy snippet are used."""
    order = list(infohub.KINDS) + ["field", "flag"]
    rows = "".join(f'<p style="margin:4px 0;"><b>{_KIND_LABEL.get(k, k)}</b> — {_HUB_HELP[k]}</p>'
                   for k in order if k in _HUB_HELP)
    return (
        "<div style=\"font-family:'Segoe UI';\">"
        '<div style="font-size:15px;"><b>Info Hub — the catalog</b></div>'
        "<p>Everything you can place in a field or reference by <b>name</b>, grouped into sections. Pick a "
        "section on the left, search within it, and select an entry to see its details on the right.</p>"
        '<p style="font-size:14px;"><b>Sections</b></p>' + rows +
        '<p style="font-size:14px;"><b>Using an entry</b></p>'
        "<p><b>Copy name</b> — paste into a form's catalog field (an NPC's <code>archetype</code>, a prop's "
        "<code>prop</code>, …).</p>"
        "<p><b>Copy snippet</b> — paste a ready-to-edit <code>field.toml</code> block straight into a field.</p>"
        "</div>")


class CatalogLibrary(QDialog):
    """The Info Hub as a SECTIONED LIBRARY (replacing the all-in-one browse list). Three columns: a category
    sidebar with per-kind counts, a per-section searchable result list, and a rich DETAIL pane built from
    ``infohub.detail`` -- facts, animations, the movement set, composite parts, model aliases, and a ready
    ``field.toml`` snippet -- the data the flat browser computed and then threw away. Browse-only: 'Copy
    name' / 'Copy snippet' put text on the clipboard; nothing is returned (the in-form picker stays
    :class:`CatalogPicker`)."""

    def __init__(self, parent, plan, palette):
        super().__init__(parent)
        self.setWindowTitle("Info Hub — catalog library")
        self.resize(900, 580)
        self.plan = plan
        self.pal = palette
        self._entries = []
        self._kind = None                                  # the selected section's kind (None = All)
        self._cat_kinds = []                               # sidebar row -> kind (or None for 'All')

        root = QHBoxLayout(self)
        split = QSplitter(Qt.Horizontal)
        root.addWidget(split)

        self.cats = QListWidget()                          # col 1: category sidebar (kinds + counts)
        self.cats.setMaximumWidth(200)
        self.cats.currentRowChanged.connect(self._on_category)
        split.addWidget(self.cats)

        mid = QWidget()                                    # col 2: search + result list
        mv = QVBoxLayout(mid)
        mv.setContentsMargins(0, 0, 0, 0)
        self.q = QLineEdit()
        self.q.setPlaceholderText("Search…")
        self.q.textChanged.connect(self._refresh_list)
        mv.addWidget(self.q)
        self.lst = QListWidget()
        self.lst.currentRowChanged.connect(self._describe)
        self.lst.itemDoubleClicked.connect(lambda _i: self._copy_name())
        mv.addWidget(self.lst, 1)
        self.count = QLabel("")
        self.count.setStyleSheet(f"color:{palette['muted']};")
        self.count.setWordWrap(True)
        mv.addWidget(self.count)
        split.addWidget(mid)

        right = QWidget()                                  # col 3: rich detail pane + copy buttons
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        # the app's global QSS renders QTextEdit as a monospace CONSOLE; the detail pane is PROSE -> give it a
        # readable proportional font on the normal surface (the snippet <pre> stays monospace by its tag).
        self.detail.setStyleSheet(
            f"QTextEdit {{ font-family:'Segoe UI'; font-size:13px; background:{palette['surface']}; "
            f"color:{palette['text']}; border:1px solid {palette['border']}; border-radius:8px; padding:8px; }}")
        rv.addWidget(self.detail, 1)
        bar = QHBoxLayout()
        cn = QPushButton("Copy name")
        cn.setObjectName("accent")
        cn.clicked.connect(self._copy_name)
        cs = QPushButton("Copy snippet")
        cs.setToolTip("Copy a ready-to-paste field.toml block for this entry")
        cs.clicked.connect(self._copy_snippet)
        helpb = QPushButton("?")
        helpb.setToolTip("What's in the Info Hub? (glossary + how to use it)")
        helpb.setFixedWidth(32)
        helpb.clicked.connect(self._show_help)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        bar.addWidget(cn)
        bar.addWidget(cs)
        bar.addStretch(1)
        bar.addWidget(helpb)
        bar.addWidget(close)
        rv.addLayout(bar)
        split.addWidget(right)

        split.setSizes([190, 320, 390])
        self._build_categories()
        self.cats.setCurrentRow(0)                         # land on 'All'
        self.q.setFocus()

    def _build_categories(self):
        """One browse over the cached catalogs -> per-kind counts -> the sidebar sections (only non-empty
        kinds; the campaign's own field/flag sections appear only when a campaign is open)."""
        try:
            allent = infohub.browse("", kinds=None, limit=None, campaign_context=self.plan)
        except Exception:                                  # noqa: BLE001 -- a catalog needing data we lack
            allent = []
        counts = collections.Counter(e.kind for e in allent)
        self._cat_kinds = [None]
        self.cats.addItem(f"All  ({len(allent)})")
        for k in _LIBRARY_ORDER:
            if counts.get(k):
                self.cats.addItem(f"{_KIND_LABEL.get(k, k)}  ({counts[k]})")
                self._cat_kinds.append(k)

    def _on_category(self, row):
        if 0 <= row < len(self._cat_kinds):
            self._kind = self._cat_kinds[row]
            where = "all sections" if self._kind is None else _KIND_LABEL.get(self._kind, self._kind).lower()
            self.q.setPlaceholderText(f"Search {where}…")
            self._refresh_list()

    def _refresh_list(self):
        kinds = None if self._kind is None else [self._kind]
        try:
            self._entries = infohub.browse(self.q.text(), kinds=kinds, limit=None, campaign_context=self.plan)
        except Exception:                                  # noqa: BLE001
            self._entries = []
        self.lst.clear()
        for e in self._entries:
            self.lst.addItem(f"{e.name}    [{e.kind}]" if self._kind is None else e.name)
        sect = "all sections" if self._kind is None else _KIND_LABEL.get(self._kind, self._kind)
        self.count.setText(f"{len(self._entries)} in {sect}")
        if self._entries:
            self.lst.setCurrentRow(0)
        else:
            self.detail.setHtml("")

    def _current(self):
        r = self.lst.currentRow()
        return self._entries[r] if 0 <= r < len(self._entries) else None

    def _describe(self, _row=0):
        e = self._current()
        if e is None:
            self.detail.setHtml("")
            return
        try:
            d = infohub.detail(e, campaign_context=self.plan)
        except Exception:                                  # noqa: BLE001 -- degrade to the one-line summary
            self.detail.setHtml(f"<b>{_esc(e.name)}</b> [{_esc(e.kind)}]<br>{_esc(e.summary)}")
            return
        self.detail.setHtml(self._render(d))

    def _render(self, d) -> str:
        muted = self.pal["muted"]
        h = [f'<div style="font-size:15px;"><b>{_esc(d.name)}</b> '
             f'<span style="color:{muted};">[{_esc(d.kind)}]</span></div>']
        if d.facts:
            h.append('<table cellspacing="0" cellpadding="2" style="margin-top:6px;">')
            for label, val in d.facts:
                h.append(f'<tr><td style="color:{muted};vertical-align:top;">{_esc(label)}</td>'
                         f'<td>&nbsp;&nbsp;{_esc(val)}</td></tr>')
            h.append('</table>')
        if d.movement:
            mv = ", ".join(f"{k} #{v}" for k, v in d.movement.items())
            h.append(f'<p><b>Movement</b><br><span style="color:{muted};">{_esc(mv)}</span></p>')
        if d.anims:
            an = ", ".join(f"{a} #{i}" for a, i in d.anims)
            h.append(f'<p><b>Animations ({len(d.anims)})</b><br>'
                     f'<span style="color:{muted};">{_esc(an)}</span></p>')
        if d.parts:
            pr = "<br>".join(f"{_esc(nm)} (pose {_esc(p)}) @ ({_esc(dx)}, {_esc(dz)})"
                             for nm, p, dx, dz in d.parts)
            h.append(f'<p><b>Parts</b><br><span style="color:{muted};">{pr}</span></p>')
        if d.aliases:
            h.append(f'<p><b>Also on this model</b><br>'
                     f'<span style="color:{muted};">{_esc(", ".join(d.aliases))}</span></p>')
        if d.locations:
            loc = ", ".join(f"{nm} ({fid})" for fid, nm in d.locations[:24])
            h.append(f'<p><b>Appears in</b><br><span style="color:{muted};">{_esc(loc)}</span></p>')
        if d.snippet:
            h.append(f'<p style="margin-top:8px;"><b>Use it</b></p>'
                     f'<pre style="background:{self.pal["surface_btn"]};padding:6px;'
                     f'border-radius:4px;white-space:pre-wrap;">{_esc(d.snippet)}</pre>')
        return "".join(h)

    def _copy_name(self):
        e = self._current()
        if e is not None:
            QApplication.clipboard().setText(e.name)
            self.count.setText(f"Copied “{e.name}” to the clipboard.")

    def _copy_snippet(self):
        e = self._current()
        if e is not None:
            QApplication.clipboard().setText(infohub.snippet(e))
            self.count.setText(f"Copied the {e.kind} snippet for “{e.name}”.")

    def _show_help(self):
        """A small modal glossary: what each section is (archetype vs creature vs model vs prop …) and how
        Copy name / Copy snippet are used."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Info Hub — help")
        dlg.resize(470, 540)
        v = QVBoxLayout(dlg)
        body = QTextEdit()
        body.setReadOnly(True)
        body.setStyleSheet(
            f"QTextEdit {{ font-family:'Segoe UI'; font-size:13px; background:{self.pal['surface']}; "
            f"color:{self.pal['text']}; border:1px solid {self.pal['border']}; border-radius:8px; padding:10px; }}")
        body.setHtml(_hub_help_html())
        v.addWidget(body, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        ok = QPushButton("Got it")
        ok.setObjectName("accent")
        ok.clicked.connect(dlg.accept)
        row.addWidget(ok)
        v.addLayout(row)
        dlg.exec()
