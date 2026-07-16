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
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTextEdit, QToolButton, QVBoxLayout,
    QWhatsThis, QWidget,
)

from . import concepts, style, widgets
from .. import dialogue as _dlg
from .. import infohub
from ..content.text import DEFAULT_WRAP_WIDTH
from ..editor import forms
from ..editor.theme import derive

# A form field whose value is a story-flag / scenario reference gets a "?" concept badge derived from its
# KIND (so every flag/scenario field is covered without tagging each Field); an explicit Field.concept wins.
_KIND_CONCEPT = {forms.FLAGREF: "story-flag", forms.FLAGPAIR: "story-flag",
                 forms.FLAGDICTLIST: "story-flag", forms.SCENARIOREF: "scenario"}

# Guided beginner mode (Phase 7): build_form tucks the expert fields of each spec into a per-form 'Advanced
# options' drawer. Global (not threaded through the many call sites); the shell sets it at startup + on toggle
# and re-mounts the open form. Nothing is removed -- Guided only tucks; Full shows every field inline.
_GUIDED = True


def set_guided(on):
    """Set the global Guided beginner mode read by :func:`build_form`."""
    global _GUIDED
    _GUIDED = bool(on)


# THE RICH-TEXT RAMP. This module's document bodies -- the Info Hub catalog card, an entry's detail, the
# concept card -- are HTML handed to a QTextEdit, and no QSS role reaches inside a text document. So they
# had their own private type ramp, hard-typed: a 13px body (the body rung's OLD value, stale since QUARTO
# P1 moved it to 14) with 14/15px headings that sat BELOW the app's 18px head. Two ramps, one app, and the
# smaller one was the only place a newcomer reads at length.
#
# It is also the last surface deaf to CALIBRE: a widget stylesheet OUT-RANKS the application sheet and
# survives its re-render, so the dial moved every tab and left the Info Hub at 13px.
#
# A GLOBAL, because this module already made that call for exactly this reason -- see _GUIDED above:
# "not threaded through the many call sites; the shell sets it at startup + on toggle". Same shape, same
# owner, same lifecycle. Threading a scale through build_form / CatalogPicker / every concept card would
# be a second mechanism for one fact.
_TEXT_SCALE = 100


def set_text_scale(pct):
    """Set the global text-size percent read by this module's rich-text bodies (the shell owns it)."""
    global _TEXT_SCALE
    _TEXT_SCALE = int(pct)


def _px(rung):
    """A type rung as a px int, at the live scale -- for HTML, which cannot reference a QSS token."""
    return style.type_px(rung, _TEXT_SCALE)


def _is_advanced(f):
    """An expert field the Guided mode tucks away: an explicit ``Field.advanced`` OR a help string that opens
    with 'advanced' (the convention already used across the specs for model/animset/borrow_bg/…)."""
    return getattr(f, "advanced", False) or (f.help or "").strip().lower().startswith("advanced")


def _concept_badge(term, palette):
    """A small '?' help badge that opens the plain-language concept card for ``term`` (via a lightweight
    What's-This bubble -- self-contained, no shell callback). Returns ``(button, card_html)`` or ``None`` if
    the term doesn't resolve to a card."""
    c = concepts.resolve(term)
    if c is None:
        return None
    card_html = f"<b>{c.title}</b><br>{c.html(palette['muted'])}"
    btn = QToolButton()
    btn.setText("?")
    btn.setObjectName("conceptBadge")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    # The 22x22 box (a bigger hit target, WCAG 2.5.8) is now QSS -- style.py's conceptBadge rule pins it
    # via min/max-width+height, keyed to style.badge_box(scale). It used to be setFixedSize(22, 22) here,
    # which CALIBRE could not reach: a Python pin freezes the circle while the "?" inside it grows with
    # the text (audited: the glyph overflows a frozen 22px box at 150%), and any badge built before a live
    # scale change would keep the stale size. In QSS, one re-render moves the box and the glyph together.
    btn.setToolTip(f"What's a {c.title.lower()}?")
    btn.setAccessibleName(f"What is {c.title}")
    btn.clicked.connect(lambda: QWhatsThis.showText(QCursor.pos(), card_html, btn))
    return btn, card_html

# Fields whose value is a line shown in an FF9 text window -> they get a live wrap-preview (FF9 never
# auto-wraps, so the kit pre-breaks long lines; this shows exactly where). Keys match editor.forms specs.
DIALOGUE_KEYS = {"dialogue", "message", "prompt", "reply"}


def _wrap_preview_panel(line_edit, get_text, wrap_width):
    """A read-only pane under a dialogue field: how the line breaks on the FF9 screen, live as you type.
    Reuses the exact build-time wrapper (:func:`..dialogue.wrap_preview`). ``wrap_width`` None = the field
    set ``[dialogue] wrap = false`` (author wraps by hand) -> show the text raw, no preview break."""
    panel = QWidget()
    pv = QVBoxLayout(panel)
    pv.setContentsMargins(0, 4, 0, 0)
    pv.setSpacing(4)
    pv.addWidget(widgets.caption("On-screen preview — how it wraps in the FF9 window:"))
    box = QPlainTextEdit()
    box.setReadOnly(True)
    box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)     # show the kit's OWN break points, not Qt's
    box.setFixedHeight(74)
    pv.addWidget(box)
    # The note is ALWAYS in the layout at a fixed height (it carries the warning OR a quiet "fits" line):
    # toggling visibility would change the panel height and, inside the nested form/scroll, clip the
    # fixed-height box on the way back. A constant-height panel can't reflow.
    note = QLabel("")
    note.setProperty("role", "caption")            # muted by default; state='warn' colours the overflow line
    # 18, not 16: QUARTO P1 moved the caption rung 11 -> 12 and this pin was the wall it hit. A 12px Segoe
    # line box is 15.94px against the old 16 -- it "fits" with 0.06px to spare, i.e. one hinting or DPI
    # nudge from clipping its own descenders, silently, in the panel that reports overflow. (At 11px it had
    # 1.39px; at 13px it clips outright by 1.27.) The height is FIXED on purpose -- see above, a
    # constant-height panel cannot reflow and clip the box behind it -- so the number has to be raised by
    # hand rather than released. 18 restores ~2px of headroom at the new rung. If the body/caption rungs
    # ever move again this is a real blocker, not a warning: it is checked by test_workspace_forms.
    note.setFixedHeight(18)
    pv.addWidget(note)

    def refresh(*_):
        txt = get_text() or ""
        box.setPlainText((_dlg.wrap_preview(txt, wrap_width) if wrap_width is not None else txt) or "(empty)")
        over = _dlg.overflow(txt, wrap_width) if (txt and wrap_width is not None) else []
        if over:
            note.setText(f"⚠ {len(over)} line(s) may overflow the window — verify in-game.")
            note.setProperty("state", "warn")
        elif txt:
            note.setText("✓ fits the window")
            note.setProperty("state", "")
        else:
            note.setText("")
        widgets.repolish(note)

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
    lay.setVerticalSpacing(12)                         # 4pt-grid rhythm: field -> field
    getters = {}
    hints = {}                                         # field key -> its HINT (the help; constant, teaches)
    notes = {}                                         # field key -> its NOTICE (the live error; reports)
    #                                                    Two dicts because they are two jobs -- see DICTION
    #                                                    at the call site below. One label used to be both,
    #                                                    and the error ate the help.
    editable = []                                      # (key, widget) for wiring change -> validate + on_change
    # Guided mode: expert fields go into an 'Advanced options' drawer (a second form layout) instead of inline.
    adv_lay = None
    adv_box = None
    if _GUIDED and any(_is_advanced(f) for f in spec):
        adv_box = widgets.disclosure("Advanced options")
        _adv_inner = QWidget()
        adv_lay = QFormLayout(_adv_inner)
        adv_lay.setLabelAlignment(Qt.AlignRight | Qt.AlignTop)
        adv_lay.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        adv_lay.setHorizontalSpacing(14)
        adv_lay.setVerticalSpacing(12)
        adv_box.content_layout.addWidget(_adv_inner)

    def browse(field, getter, setter):
        # a numeric field (e.g. the encounter battle scene, an INT) wants the picked entry's id, not its name
        val = pick(field.catalog, getter(), want_id=field.kind in (forms.INT, forms.OPTINT))
        if val:
            setter(val)

    def browse_file(field, setter):
        # a file-backed field (Field.file = the dialog's name filter, e.g. the [music] custom track)
        fn, _ = QFileDialog.getOpenFileName(w, f"Pick {field.label}", "", field.file)
        if fn:
            setter(fn)

    for f in spec:
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)                                # 4pt-grid rhythm: field -> its hint
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
        elif getattr(f, "file", None) and setter is not None:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(widget, 1)
            b = QPushButton("Browse…")
            b.clicked.connect(lambda _=False, ff=f, st=setter: browse_file(ff, st))
            row.addWidget(b)
            v.addLayout(row)
        else:
            v.addWidget(widget)
        # DICTION: TWO labels, because they are two different things and one of them was eating the other.
        # The HINT teaches ("a unique number for your field (use >= 4000)") and is always on screen. The
        # NOTICE reports ("expected a whole number, got 'abc'") and only appears when it has something to
        # say. They used to be ONE label: validate() overwrote the help with the error and only restored it
        # once the value parsed -- so the sentence telling you what a valid value LOOKS like vanished at
        # exactly the moment you were failing to type one. Proven live, not inferred.
        hint = widgets.caption(f.help or "")
        v.addWidget(hint)                               # PARENT it BEFORE setVisible: setVisible(True) on a
        hint.setVisible(bool(f.help))                   # parentless widget flashes a top-level window (Windows)
        hints[f.key] = hint
        note = widgets.notice("")                       # the body rung -- an error is never smaller than
        v.addWidget(note)                               # the field it is about (see style.py's notice rule)
        note.setVisible(False)
        notes[f.key] = note
        editable.append((f.key, widget))
        if f.key in DIALOGUE_KEYS and hasattr(widget, "textChanged"):
            v.addWidget(_wrap_preview_panel(widget, getters[f.key], wrap_width))
        label = widgets.role_label(f.label + ":", "label")   # weight-500 field label (the type ramp)
        term = f.concept or _KIND_CONCEPT.get(f.kind)         # a jargon field -> a "?" concept badge (Phase 5)
        badge = _concept_badge(term, palette) if term else None
        target = adv_lay if (adv_lay is not None and _is_advanced(f)) else lay   # Guided: expert -> Advanced drawer
        if badge is not None:
            btn, card_html = badge
            widget.setWhatsThis(card_html)                    # Shift-F1 on the field too, not just the badge
            lw = QWidget()
            lh = QHBoxLayout(lw)
            lh.setContentsMargins(0, 0, 0, 0)
            lh.setSpacing(5)
            lh.addWidget(label)
            lh.addWidget(btn)
            lh.addStretch(1)
            target.addRow(lw, box)
        else:
            target.addRow(label, box)
    if adv_box is not None:
        lay.addRow(adv_box)                                   # the Advanced drawer spans, below the plain fields

    def validate():
        """Live per-field check: a value that fails its parser raises a NOTICE under the field; the help
        stays put either way. Returns the count of invalid fields.

        THE HINT IS NEVER TOUCHED HERE, and that is the fix. This used to `h.setText(f"⚠ {e}")` -- one
        label doing two jobs, so the error DESTROYED the teaching and only gave it back once the value
        parsed. The help said "use >= 4000"; type "abc" and it vanished, which is the only moment it was
        load-bearing. Now the help is a constant and the notice is the variable.
        """
        bad = 0
        for f in spec:
            if f.kind == forms.BOOL:
                continue
            n = notes[f.key]
            try:
                forms._parse_field(f.kind, getters[f.key]())
            except ValueError as e:
                n.setText(f"⚠  {e}")
                n.setProperty("state", "error")         # -> the notice[state=error] rule, at the body rung
                widgets.repolish(n)
                n.setVisible(True)
                bad += 1
                continue
            n.setText("")
            n.setVisible(False)                         # a notice with nothing to report says nothing
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

    def __init__(self, parent, kinds, initial, plan, palette, *, browse=False, limit=300, want_id=False,
                 sps_context=None):
        super().__init__(parent)
        self.setWindowTitle("Browse the catalog" if browse else "Pick from the catalog")
        self.resize(560, 460)
        self.kinds = kinds
        self.plan = plan
        self.sps_context = sps_context                 # the open field's carried effects (for the 'sps' kind)
        self.browse = browse                           # browse mode: "Use this" copies the name + stays open
        self.limit = limit
        self.want_id = want_id                         # a numeric field (e.g. encounter scene) wants the id back
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
        self.preview = QLabel()                        # a thumbnail for kinds that render one (SPS effects/templates)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setFixedHeight(0)                 # collapsed until an entry has a preview
        lay.addWidget(self.preview)
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
                                           campaign_context=self.plan, sps_context=self.sps_context)
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
        if not (0 <= row < len(self._entries)):
            return
        e = self._entries[row]
        self.info.setText(f"{e.name}  [{e.kind}]  —  {e.summary}")
        png = None
        if e.kind in ("sps", "sps_template"):          # render a thumbnail for an effect / template
            try:
                png = infohub.detail(e, sps_context=self.sps_context).preview_png
            except Exception:                          # noqa: BLE001 -- preview is best-effort
                png = None
        elif e.kind in ("model", "archetype", "creature", "prop"):
            # model-backed entries: CACHE READS ONLY (the Models tab / model-preview fill the cache;
            # rendering here would block the GUI thread on a p0data load)
            try:
                from ..models.thumbcache import cached_png
                from .. import catalog as _catmod
                m = _catmod.model(e.ident) if e.ident is not None else (
                    _catmod.model(e.model) if e.model else None)
                png = cached_png(m.id) if m else None
            except Exception:                          # noqa: BLE001 -- preview is best-effort
                png = None
        if png:
            pm = QPixmap(png)
            if not pm.isNull():
                self.preview.setFixedHeight(140)
                self.preview.setPixmap(pm.scaledToHeight(132, Qt.TransformationMode.SmoothTransformation))
                return
        self.preview.clear()
        self.preview.setFixedHeight(0)

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
        # a numeric field (want_id) takes the entry's id (e.g. a battle scene #67 -> "67"); else its name
        self.result = str(e.ident) if self.want_id and e.ident is not None else e.name
        self.accept()


def pick_catalog(parent, catalog, initial, plan, palette, *, want_id=False, sps_context=None):
    """Open :class:`CatalogPicker` for a comma-separated ``catalog`` string; return the chosen NAME (or the
    entry's numeric id as a string when ``want_id`` -- for an INT field like an encounter's battle scene),
    or None. The shell passes this (curried with its window/plan/palette) as ``build_form``'s ``pick``.
    ``sps_context`` (the open field's carried effects) makes the ``sps`` kind browse THIS field's effects."""
    kinds = [k.strip() for k in catalog.split(",")] if catalog else None
    dlg = CatalogPicker(parent, kinds, initial, plan, palette, want_id=want_id, sps_context=sps_context)
    dlg.exec()
    return dlg.result


# friendly section names for the Info Hub library sidebar (one per catalog 'kind').
_KIND_LABEL = {
    "field": "Campaign fields", "flag": "Campaign flags", "sps": "SPS effects",
    "sps_template": "SPS templates",
    "archetype": "Archetypes", "creature": "Creatures", "composite": "Composites",
    "prop": "Props", "model": "Models", "item": "Items", "scene": "Battle scenes",
    "song": "Songs", "storyflag": "Story flags",
}
# sidebar order: the open project's OWN content first (fields/flags/SPS effects), then the static catalogs.
_LIBRARY_ORDER = ("field", "flag", "sps") + infohub.KINDS


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
    "song": "the game's music tracks, by song id (from your install's manifest) — pick one in the Music "
            "form, or mint your own via <code>[music] file</code>. Appears after the first song browse.",
    "storyflag": "FF9's built-in story-state registry — named engine vars, scenario beats, reserved bit regions.",
    "field": "the fields in the OPEN campaign (this section shows only when a campaign is loaded).",
    "flag": "the named story flags in the OPEN campaign.",
    "sps": "the particle effects (fire/smoke/magic) a native fork carries in its <code>sps/</code> sidecar — "
           "decode + preview them, and copy a <code>[[sps_edit]]</code> re-skin block.",
    "sps_template": "ready-made particle effects (fire/smoke/sparkle/…) for the Tier-2 creator — preview one, "
                    "then add it to a field as an <code>[[sps]]</code> block (or pick it in the Effects form).",
}


def _hub_help_html() -> str:
    """The Info Hub help text: a one-line intro, the per-section glossary (static catalogs first, the
    campaign-only sections last), and how Copy name / Copy snippet are used."""
    order = list(infohub.KINDS) + ["field", "flag", "sps"]
    rows = "".join(f'<p style="margin:4px 0;"><b>{_KIND_LABEL.get(k, k)}</b> — {_HUB_HELP[k]}</p>'
                   for k in order if k in _HUB_HELP)
    return (
        "<div style=\"font-family:'Segoe UI';\">"
        f'<div style="font-size:{_px("type_head")}px;"><b>Info Hub — the catalog</b></div>'
        "<p>Everything you can place in a field or reference by <b>name</b>, grouped into sections. Pick a "
        "section on the left, search within it, and select an entry to see its details on the right.</p>"
        f'<p style="font-size:{_px("type_body")}px;"><b>Sections</b></p>' + rows +
        f'<p style="font-size:{_px("type_body")}px;"><b>Using an entry</b></p>'
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

    def __init__(self, parent, plan, palette, sps_context=None):
        super().__init__(parent)
        self.setWindowTitle("Info Hub — catalog library")
        self.resize(900, 580)
        self.plan = plan
        # DERIVE AT THE DOOR. The shell hands us its RAW palette (`CatalogLibrary(self, self.plan,
        # self.pal, ...)`), so a derived key -- `help_fg`, below -- is simply not in it and would raise.
        # derive() is idempotent and documented safe on a base OR an already-derived dict, so one call
        # here makes every token reachable and nothing downstream has to know which kind it holds. This is
        # the alternative to the `pal.get("derived_key", pal["raw_key"])` idiom, whose fallback fires 100%
        # of the time and quietly renders the wrong tier forever.
        palette = derive(dict(palette))
        self.pal = palette
        self.sps_context = sps_context                     # {label: sps_dir} of the open project's carried effects
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
            f"QTextEdit {{ font-family:'Segoe UI'; font-size:{_px('type_body')}px; background:{palette['surface']}; "
            f"color:{palette['text']}; border:1px solid {palette['border']}; border-radius:8px; padding:8px; }}")
        rv.addWidget(self.detail, 1)
        bar = QHBoxLayout()
        cn = QPushButton("Copy name")
        cn.setObjectName("accent")
        cn.clicked.connect(self._copy_name)
        cs = QPushButton("Copy snippet")
        cs.setToolTip("Copy a ready-to-paste field.toml block for this entry")
        cs.clicked.connect(self._copy_snippet)
        self.blender_btn = QPushButton("Export for Blender…")
        self.blender_btn.setToolTip("Write this model as a .glb (mesh + rig + textures + its standard "
                                    "animations) — Blender opens it via File ▸ Import ▸ glTF 2.0. Edit it, "
                                    "then bring it back on the Import tab's Custom models box.")
        self.blender_btn.clicked.connect(self._export_gltf)
        self.blender_btn.setEnabled(False)
        helpb = QPushButton("?")
        helpb.setToolTip("What's in the Info Hub? (glossary + how to use it)")
        # A circular violet badge -- it pops out from the neutral Copy/Close buttons (a distinct 'info' hue).
        # The box and its radius are a GEOMETRIC pair (radius = half the box = a circle, not a squircle) and
        # they stay pinned here; only the GLYPH joins the ramp. Its 15px was a private number one rung under
        # the app's head, and deaf to the dial like everything else in this module's widget stylesheets.
        helpb.setFixedSize(30, 30)
        # `help_fg`, not `accent_fg`. This wore the ACCENT's ink on the HELP fill -- two hexes nothing had
        # ever asserted were compatible, because `accent_fg` is fenced against `$accent` alone
        # (test_editor_theme::test_the_accent_button_label_is_text). Measured on nord it lands 2.51:1, a
        # sub-AA glyph. A token borrowed from the ground next door is not a token, it is a coincidence.
        helpb.setStyleSheet(
            f"QPushButton {{ background:{palette['help']}; color:{palette['help_fg']}; border:0; "
            f"border-radius:15px; font-weight:bold; font-size:{_px('type_body')}px; }}"
            f"QPushButton:hover {{ background:{palette['help_hover']}; }}")
        helpb.clicked.connect(self._show_help)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        bar.addWidget(cn)
        bar.addWidget(cs)
        bar.addWidget(self.blender_btn)
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
            allent = infohub.browse("", kinds=None, limit=None, campaign_context=self.plan,
                                    sps_context=self.sps_context)
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
            self._entries = infohub.browse(self.q.text(), kinds=kinds, limit=None, campaign_context=self.plan,
                                           sps_context=self.sps_context)
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

    @staticmethod
    def _model_token(e):
        """The GEO model behind an entry (for the Blender export), or None: a raw model entry IS one;
        archetypes/creatures/props carry theirs in ``e.model``."""
        if e is None:
            return None
        return e.name if e.kind == "model" else e.model

    def _describe(self, _row=0):
        e = self._current()
        if hasattr(self, "blender_btn"):
            self.blender_btn.setEnabled(self._model_token(e) is not None)
        if e is None:
            self.detail.setHtml("")
            return
        try:
            d = infohub.detail(e, campaign_context=self.plan, sps_context=self.sps_context)
        except Exception:                                  # noqa: BLE001 -- degrade to the one-line summary
            self.detail.setHtml(f"<b>{_esc(e.name)}</b> [{_esc(e.kind)}]<br>{_esc(e.summary)}")
            return
        self.detail.setHtml(self._render(d))

    def _export_gltf(self):
        """Export the selected model as a Blender-editable .glb, IN-PROCESS (a couple of seconds behind a
        wait cursor — the library is modal, so streaming to the shell's Output would be invisible). The
        success box carries the model's appearance caveats (hair-swap / story-evolved forms)."""
        token = self._model_token(self._current())
        if token is None:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Export for Blender", f"{token}.glb",
                                             "glTF binary (*.glb)")
        if not out:
            return
        from PySide6.QtGui import QCursor
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        try:
            from ..models import gltf as _gltf
            info = _gltf.export_gltf(token, out)
        except Exception as e:                             # noqa: BLE001  (no install / no UnityPy / bad token)
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Export failed", f"{e}\n\n(The model export needs your FF9 install "
                                                       "+ UnityPy — check Settings ▸ Setup & health.)")
            return
        QApplication.restoreOverrideCursor()
        notes = []
        try:
            from ..models.appearance import appearance_notes
            notes = appearance_notes(token, minted=False)
        except Exception:                                  # noqa: BLE001
            pass
        extra = ("\n\nHeads-up:\n" + "\n".join(f"• {n}" for n in notes)) if notes else ""
        QMessageBox.information(
            self, "Exported for Blender",
            f"Wrote {out}\n\nBlender: File ▸ Import ▸ glTF 2.0. When you're done editing, export a .glb "
            f"and bring it back via Import ▸ Custom models ▸ Import edited .glb.{extra}")

    def _render(self, d) -> str:
        muted = self.pal["muted"]
        h = [f'<div style="font-size:{_px("type_head")}px;"><b>{_esc(d.name)}</b> '
             f'<span style="color:{muted};">[{_esc(d.kind)}]</span></div>']
        if getattr(d, "preview_png", None):
            # the preview LEADS -- a model page's animation list can run hundreds of entries, and an
            # image below the fold reads as no image at all
            from pathlib import Path
            h.append(f'<p style="margin-top:6px;">'
                     f'<img src="file:///{Path(d.preview_png).as_posix()}" width="200"></p>')
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
            f"QTextEdit {{ font-family:'Segoe UI'; font-size:{_px('type_body')}px; background:{self.pal['surface']}; "
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
