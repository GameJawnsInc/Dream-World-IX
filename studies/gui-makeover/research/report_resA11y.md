# GUI Makeover Research — External Standards: Accessibility, Typography & Visual Polish

Scoped to what a **PySide6/QSS desktop app** can actually implement, and calibrated against the Workspace's real code. I read the live palette (`ff9mapkit/ff9mapkit/editor/theme.py:20-208`), the QSS (`ff9mapkit/ff9mapkit/workspace/style.py`), and the existing contrast test (`ff9mapkit/tests/test_editor_theme.py:79-104`), then measured every theme against WCAG. The findings below are backed by that measurement, not assertion.

---

## 0. Head start & the two load-bearing gaps (read first)

**The head start is real.** The app already has (a) a **WCAG relative-luminance + contrast helper** encoded as an invariant test (`test_editor_theme.py:80-104`, the exact `0.2126/0.7152/0.0722` sRGB-linear formula from [WCAG 1.4.3](https://webaim.org/articles/contrast/)), (b) **7 themes sharing one enforced key-set** (`test_palettes_share_one_key_set`), and (c) **semantic tokens already split out** (`success`/`warn`/`error`/`help`). That is the scaffolding most apps lack. Retuning to WCAG AA is a values-and-floors job, not an architecture job.

**Two gaps undercut it, though, and both are one-line-visible:**

1. **`style.py:16` — `* { outline: 0; }` globally kills the focus ring.** Only `QLineEdit`/`QComboBox`/`QAbstractSpinBox` re-add a `:focus` border. `QPushButton`, `QToolButton`, `QTabBar::tab`, `QTreeView::item`, `QCheckBox::indicator`, and `QRadioButton::indicator` have **no `:focus` rule at all** — so a keyboard-only user cannot see where focus is on most of the UI. This is a **direct fail of [WCAG 2.4.7 Focus Visible (AA)](https://www.w3.org/TR/WCAG22/)** and the single highest-priority accessibility fix.

2. **The contrast test floors are set *below* WCAG AA** (`test_editor_theme.py:99-102`: text ≥ 4.0, muted ≥ 2.7, accent-fg ≥ 3.0). They were written to "fire only on a real regression," so several themes ship legitimately sub-AA text. Measured proof follows.

### Measured contrast — every theme, every load-bearing pair
(ratio; **bold = fails the relevant WCAG AA floor**. Normal text needs **4.5:1**, large/bold text & UI-component/focus contrast need **3:1** — [WebAIM](https://webaim.org/articles/contrast/), [WCAG 1.4.11](https://www.w3.org/TR/WCAG22/))

| theme | text/bg | muted/bg | muted/surf | accentFg/accent | accent/bg | border/surf | error/surf | warn/surf |
|---|---|---|---|---|---|---|---|---|
| light | 13.74 | **4.46** | 4.93 | 4.57 | 3.79 | **1.34** | 4.99 | 4.30 |
| dark | 13.14 | 6.31 | 5.64 | **3.20** | 5.04 | **1.38** | 5.19 | 6.80 |
| nord | 10.84 | **4.04** | **3.71** | **4.03** | 3.10 | **1.33** | **2.80** | 7.33 |
| dracula | 13.36 | 4.64 | 4.33 | 5.90 | 5.90 | **1.45** | 4.23 | 11.88 |
| solarized-dark | 5.61 | **4.02** | **3.48** | **3.68** | 4.08 | **1.33** | **2.81** | 4.05 |
| solarized-light | **4.39** | **4.14** | 4.37 | **3.68** | 3.00 | **1.25** | 3.98 | **2.76** |
| gruvbox-dark | 10.75 | 5.30 | 4.72 | 5.84 | 5.84 | **1.49** | 3.82 | 7.74 |

**What this proves, concretely:**
- **`muted` (hint text) fails 4.5:1 on 5 of 7 themes** against `bg` and worse against `surface`. This is the "smushed grey hint you can barely read" problem, quantified. Muted text is small (11–13px), so it needs the full 4.5:1, not the 3:1 large-text allowance.
- **Accent-button label text fails 4.5:1 on dark, nord, solarized-dark, solarized-light** (3.20–4.03). A 13px non-bold white label on the accent is *normal* text.
- **Every theme's 1px input/control border sits at ~1.25–1.49:1** — well under the 3:1 that [WCAG 1.4.11](https://www.w3.org/TR/WCAG22/) requires for the visual boundary of a UI control. Text fields, combos and cards currently have no perceptible edge; that reads as "no structure / smushed regions."
- **`error` fails 3:1 on nord & solarized-dark**, **`warn` fails on solarized-light** — status colors that can't be seen as status.

There are **zero** `setAccessibleName`/`setAccessibleDescription`/`QAccessible` calls anywhere in `workspace/` (confirmed by grep), and **zero** `QPropertyAnimation`/`QGraphicsOpacityEffect` — so there is no screen-reader labelling and no motion layer yet. Both are greenfield.

---

## 1. ACCESSIBILITY CHECKLIST (WCAG 2.2, desktop-scoped, Qt-achievable, pass/fail-able)

Each item is written as a testable assertion. "AA" is the target tier. WCAG 2.2 added 9 criteria and **removed 4.1.1 Parsing**; the desktop-relevant new ones are 2.4.11, 2.4.13, 2.5.8 ([W3C What's New in 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/)).

### Contrast (WCAG 1.4.3 AA, 1.4.11 AA)
- [ ] **Body & label text ≥ 4.5:1** against its actual background (`bg` *and* `surface`). → raise the test floor from 4.0 to **4.5** and fix `solarized-light` text.
- [ ] **`muted`/hint text ≥ 4.5:1** (it is small text). → raise floor from 2.7 to **4.5**; retune muted on light/nord/solarized-dark/solarized-light.
- [ ] **Text on the accent button ≥ 4.5:1** (13px non-bold). → raise floor from 3.0 to **4.5**, or set accent-button labels to 600-weight/≥15px so 3:1 legitimately applies. Fix dark/nord/solarized themes.
- [ ] **Control boundaries (input/combo/card/tree borders) ≥ 3:1** against their fill (1.4.11). → the `border` token needs a stronger value *or* focus/active states must supply the 3:1 edge. Currently ~1.3:1 everywhere — **fail**.
- [ ] **Status colors (`error`/`warn`/`success`) ≥ 3:1** against the surface they sit on (they're graphical status objects, 1.4.11). → fix nord/solarized error & solarized-light warn.
- [ ] **Focus ring ≥ 3:1** against *both* the focused component and the adjacent background (1.4.11 + [2.4.13 spirit](https://dequeuniversity.com/resources/wcag-2.2/)).

### Focus & keyboard (WCAG 2.4.7 AA, 2.4.11 AA, 2.4.13 AAA-aspirational)
- [ ] **Every focusable control shows a visible focus indicator** — buttons, tool-buttons, tabs, tree items, checkboxes, radios, list items. → the `* { outline: 0 }` at `style.py:16` must be replaced with per-widget `:focus` rules (a 2px accent ring or 2px inset border). **Currently fail on all non-input controls.**
- [ ] **Focus indicator ≥ 2px thick and ≥ 3:1 contrast** vs unfocused state ([2.4.13 Focus Appearance](https://testparty.ai/blog/wcag-22-new-success-criteria)). Aspirational-AAA but cheap in QSS.
- [ ] **Focused item never fully hidden** by overlays/sticky headers ([2.4.11 Focus Not Obscured, AA](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/)) — verify the breadcrumb/toolbar don't clip a focused tree row on scroll.
- [ ] **Full keyboard operability**: every action reachable by Tab/Enter/Space/arrows; logical tab order; Ctrl-K palette already models this well — extend to a documented shortcut sheet.
- [ ] **Focus order matches visual order** across the toolbar → breadcrumb → tree → tabs → inspector → problems dock.

### Target size (WCAG 2.5.8 AA — 24×24 CSS px minimum)
- [ ] **Interactive targets ≥ 24×24px**, or ≥ 24px apart ([2.5.8](https://testparty.ai/blog/wcag-22-new-success-criteria)). → **audit the 15px checkbox/radio indicators** (`style.py:59-61`) and the compact toolbar buttons (`padding: 6px 10px`, `style.py:26`). The clickable `QCheckBox` includes its label so it likely passes as a row, but the standalone indicator and any icon-only tool-button need a 24px min hit area (pad the button, not just the glyph).

### Color-independence (WCAG 1.4.1 AA)
- [ ] **No status conveyed by color alone.** Every error/warning/success needs an **icon or text label** beside the color ([design-systems consensus](https://paletterx.com/blog/color-for-error-and-success-states)). → the Problems dock, lint results, and Check output must carry a shape/glyph, not just red/yellow text.
- [ ] Selection state in the tree/list not signalled by color only (Qt selection also inverts text — OK, but verify against theme).

### Motion (WCAG 2.3.3 AAA, 2.2.2 A)
- [ ] **Any animation added is ≤ ~200ms, non-essential, and can be disabled** ([Animation from Interactions](https://www.w3.org/TR/WCAG22/)). App currently has none, so it *passes by default* — the requirement bites only when you add the polish in §4. Gate motion behind an OS reduced-motion probe + an in-app toggle.
- [ ] No auto-playing/looping motion > 5s without pause (2.2.2) — relevant only if you add skeleton shimmers.

### Text scaling & reflow (WCAG 1.4.4 AA, 1.4.12 AA)
- [ ] **UI survives 200% zoom / OS font scaling** without clipping ([Resize Text](https://www.w3.org/TR/WCAG22/)). → verify high-DPI (`Qt::AA_EnableHighDpiScaling` / Qt6 automatic) and that fixed-height rows don't truncate at large fonts. The compact toolbar (`style.py:20-22`, explicitly tuned to "FIT at 1280px") is the risk area — test it at 150%.

### Screen-reader / semantics (Qt-specific, maps to WCAG 4.1.2)
- [ ] **Every icon-only or ambiguous control has `setAccessibleName()`** (short title, e.g. "Deploy") and, where useful, `setAccessibleDescription()` (e.g. "Build and deploy the current field") — [Qt guidance](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QAccessible.html). Currently **zero** set. Qt bridges to MSAA/UIA on Windows out of the box, so this is low-effort, high-value.
- [ ] **Custom-painted widgets expose an accessible interface** — e.g. `PlaceholderListWidget` (`widgets.py:39`), `graphview.py`, `mapview.py`. For fully custom canvases, subclass `QAccessibleInterface`; for the common cases, `setAccessibleName` on the widget suffices ([MuseScore/NVDA writeup](https://andreituicu.wordpress.com/2014/08/18/how-to-implement-accessibility-for-custom-widgets-in-qt-for-nvda-screen-reader/)).
- [ ] **Fusion style retained** (already required) — it honours QSS colors *and* keeps native accessibility roles.

**Realistic Qt ceiling:** aim for **WCAG 2.2 AA on contrast, focus, target-size, and color-independence** (all fully QSS/PySide-achievable) plus **basic screen-reader labelling** (accessibleName on every actionable control). Full AAA focus-appearance and deep custom-widget `QAccessibleInterface` trees are stretch goals — worth it for the tree/graph/map canvases, optional elsewhere.

---

## 2. TYPOGRAPHY

The app is on **Segoe UI 13px body / mono 12px** in the Qt shell (`style.py:17,116`) but **10pt everywhere on the tk side** (`theme.py:266`) — an inconsistency to unify on the Qt values. There is currently **one body size and ad-hoc bolding**; a real scale is missing, which is a chief cause of "no clear hierarchy / smushed."

### A concrete type scale (base 13px, ~1.2 "minor third" ratio)
A 6–9 step scale is the recommendation for UI ([Pacgie type-scale guide](https://www.pacgie.com/guides/what-is-type-scale)); a ratio near **1.2** suits *dense* desktop tools (bigger ratios waste vertical space).

| Token | Size | Weight | Line-height | Use |
|---|---|---|---|---|
| `display` | 24px | 600 | 1.25 (30px) | Home hero / empty-state title |
| `h1` | 20px | 600 | 1.3 (26px) | Page/tab title |
| `h2` | 16px | 600 | 1.35 (22px) | Section header, GroupBox title |
| `subtitle` | 15px | 500 | 1.4 (21px) | Inspector object name |
| **`body`** | **13px** | **400** | **1.5 (20px)** | default text, form labels |
| `body-strong` | 13px | 600 | 1.5 | emphasis, active tab |
| `small` | 12px | 400 | 1.45 (17px) | secondary meta, tree rows |
| `caption` | 11px | 500 | 1.4 (15px) | hints, badges, status-bar |
| `mono` | 12px | 400 | 1.5 | code/log/`.eb` output |

**Line-height / measure rules** ([Pacgie](https://www.pacgie.com/guides/what-is-type-scale), [UX-Republic modular scale](https://www.ux-republic.com/en/practical-guide-to-creating-a-modular-scale-type-for-your-interfaces/)):
- **Body 1.5, headings 1.2–1.3, dense table rows 1.3–1.4** — headings tighter, body looser for scan-ability.
- Wrapped hint/description text (the `PlaceholderListWidget`, form help) must use ~1.5 line-height — cramped 1.0–1.1 wrapping is a direct cause of "smushed."
- Cap measure at **~66 characters** for any multi-line help/description block (constrain width with `setMaximumWidth`), don't let hints run the full panel.

**Weight hierarchy:** Segoe UI ships Light/Semilight/Regular/Semibold/Bold. Use exactly **three weights** — 400 body, 500 for small labels/captions, 600 for headings & emphasis. Avoid 700 (too heavy against the flat theme) and avoid faux-bold. Hierarchy should come from **size + weight + color (muted vs text)**, not from one bolded blob.

**Numeric alignment (high value here — the UI is full of ids, coordinates, byte offsets, field numbers):**
- Turn on **tabular figures** so `4003`, `30110`, `(344,−1152)` columns align. In Qt 6.7+, `QFont::setFeature("tnum", 1)` (or `font-feature-settings` isn't in QSS, so set it in code on the mono/data fonts). Segoe UI supports tabular numerals; a bundled Inter/IBM Plex guarantees it ([wpDataTables](https://wpdatatables.com/best-fonts-for-tables/), [Valiotti](https://valiotti.com/choosing-fonts-data-viz/)).
- Right-align numeric table columns; keep ids/coords in the **mono** face so digit width is fixed regardless of OpenType support.

**Letter-spacing:** the `QHeaderView::section` (`style.py:94`) and any all-caps micro-labels benefit from **+0.3–0.5px tracking** (all-caps needs it); body text needs none. Add slight negative tracking only on `display`/`h1` (−0.2px) for optical tightness.

**Bundled font — worth it.** A bundled **Inter** or **IBM Plex Sans** gives identical rendering across every user's machine, guaranteed tabular figures, and clearer glyph distinction at 11–13px than Segoe UI's hinting on non-Windows/older boxes ([data-table font guidance](https://wpdatatables.com/best-fonts-for-tables/)). Both are **OFL** (redistribution-clean), which matters given the existing Qt-LGPL/font packaging caution in this project. Recommendation: **ship Inter (UI) + a mono like JetBrains Mono/Cascadia** as bundled resources, fall back to Segoe UI → system. Load via `QFontDatabase.addApplicationFont`.

---

## 3. SPACING & DENSITY — the cure for "smushed"

The current metrics are **off-grid and cramped**: toolbar spacing 6 / button padding `6px 10px` (`style.py:22,26`), tree item `5px 4px` (`style.py:91`), GroupBox `margin-top:10; padding-top:8` (`style.py:107`), checkbox `spacing:7` (`style.py:57`). Values of 5/6/7/9/10 don't sit on any grid, which reads as visual noise.

### Adopt a 4pt base scale (8pt rhythm for structure)
The industry-standard scale — **4, 8, 12, 16, 24, 32, 48, 64** ([8pt grid](https://www.rejuvenate.digital/news/designing-rhythm-power-8pt-grid-ui-design), [designsystems.com](https://www.designsystems.com/space-grids-and-layouts/)). A dense IDE benefits from the **4pt** granularity for component internals while keeping **8pt** for layout gaps ([Cieden](https://cieden.com/book/sub-atomic/spacing/choosing-a-spacing-system)). Define tokens:

| Token | px | Use |
|---|---|---|
| `space-1` | 4 | icon↔label, tight inner |
| `space-2` | 8 | control padding-y, list-item inset |
| `space-3` | 12 | field↔field within a group |
| `space-4` | 16 | card padding, section inner |
| `space-5` | 24 | between form sections |
| `space-6` | 32 | major region gaps |
| `space-8` | 48 | page margins / empty-state |

### The "smushed" fixes (concrete)
- **Vertical rhythm in forms** (biggest win): label→field **4px**, field→field **12px**, section→section **24px**, section title→content **12px**. Right now stacked forms have near-uniform tight gaps, so groups don't read as groups.
- **Input padding to `8px 10px`** (from `6px 9px`) — this both relieves cramping *and* pushes control height to **≥24px** for the 2.5.8 target-size floor.
- **Card padding 16px** (`QFrame#card`, `style.py:141`) with 12px between stacked cards.
- **Tree/list rows to `6px 8px`** (from `5px 4px`) → ~28px rows, comfortable, and a real 24px target.
- **The "internal ≤ external" rule** ([Cieden best-practices](https://cieden.com/book/sub-atomic/spacing/spacing-best-practices)): padding *inside* a group must be ≤ the margin *around* it, so the eye reads containment. Verify GroupBox inner padding (8) < inter-section gap (24). Currently the near-equal small gaps blur boundaries.
- **Whitespace as the primary hierarchy device** ([wpDean](https://wpdean.com/what-is-the-8-point-grid-system/)): dense regions (Problems dock, catalogs) need *more* gutter, not smaller text, to feel calm.

### Density modes (comfortable / compact)
Ship a **density toggle** like Material's density system (4px step changes, default stays on the 8pt grid — [Medium/8pt](https://medium.com/@vishnupriyapb31/why-8pt-and-4pt-grids-rule-ui-design-and-why-5-6-7-or-10pt-grids-are-the-wild-cousins-we-dont-2da40bd53c87)):
- **Comfortable (default, newcomer-friendly):** row 28–30px, input 8px pad, section gap 24px.
- **Compact (power-user):** row 22–24px, input 6px pad, section gap 16px — but never below the 24px target-size floor for hit areas.

Implement by swapping two QSS-variable sets (you already generate QSS from a dict in `style.py:qss()`, so add `space_*` and `row_h` keys to the palette-render call — same mechanism as colors). This directly serves the brief's "great for experts, accessible to newcomers": experts pick Compact, newcomers get airy Comfortable by default.

---

## 4. COLOR + ICONOGRAPHY + MOTION polish standards

### Color
- **Keep the 7-theme architecture** — it's a genuine asset and rare. Retune values to clear the AA floors in §1 rather than removing themes.
- **Escape the lone-accent trap.** You already have a *second* meaningful hue (`help`/violet) — good ([design-system guidance](https://imperavi.com/blog/designing-semantic-colors-for-your-system/) says reserve the accent for primary CTAs/active states only). Formalize it: accent = primary action + active/selected only; `help`/info = discovery affordances; keep status hues (`success`/`warn`/`error`) *exclusively* for status.
- **Add semantic *background* tints** for banners/badges so status text can meet 4.5:1 on them. Today `error`/`warn`/`success` exist only as *foreground* colors; a red banner has nowhere legible to put text. Add `success_bg`/`warn_bg`/`error_bg`/`info_bg` (low-chroma tints of each, per theme) — this is the standard token split of "semantic intent" vs "surface" ([Backbase](https://designsystem.backbase.com/latest/design-tokens/semantic-colors/introduction-K7Gq5Ylx), [aufait](https://www.aufaitux.com/blog/color-tokens-enterprise-design-systems-best-practices/)). It extends the existing key-set discipline (add the keys to all 7 palettes; the `test_palettes_share_one_key_set` guard already enforces parity).
- **Add an explicit `focus` token** (don't overload `accent`) so the focus ring can be tuned to clear 3:1 against *both* accent-colored and surface-colored components — on nord (`accent/bg` = 3.10) and solarized-light (3.00) the accent is too close to the floor to double as a focus ring.
- **Dark/light parity:** map *every* semantic token in *every* theme (not just bg/text) — [color-token best practice](https://medium.com/design-bootcamp/color-tokens-guide-to-light-and-dark-modes-in-design-systems-146ab33023ac). The shared-key-set test already enforces this structurally; just fill the new keys.
- **Strengthen `border`** (or its focus/hover state) to reach 3:1 where it defines a control edge (1.4.11). Purely decorative dividers can stay subtle; input/combo/card outlines cannot.

### Iconography
- **Move from unicode/emoji glyphs to a monochrome SVG icon set.** Emoji (gear, chevrons) render in the OS color font, ignore the theme, and differ across Windows/macOS/Linux; icon fonts disappear in high-contrast mode. **SVG is the 2025 standard** for desktop UIs — theme-able, high-DPI crisp, and accessibility-friendly ([SVG vs font icons](https://changethisfile.com/blog/icon-fonts-vs-svg), [CSS-Tricks accessible icons](https://css-tricks.com/can-make-icon-system-accessible/)).
- **Use an OSS set:** **Lucide** (ISC), **Feather** (MIT), or **Fluent UI System Icons** (MIT, and it has a high-contrast variant). Load via `QIcon`+`QtSvg`; recolor to the theme's `text`/`muted`/`accent` by rendering the SVG through a `QPainter` tint or by templating `currentColor` in the SVG string before load.
- **Grid-align icons** at 16 / 20 / 24px (the spacing scale) with the label baseline; pair **every** icon with a text label or `setAccessibleName` (never icon-only without a name — that's the 1.4.1 + screen-reader failure).

### Motion / micro-interactions
- **Reality check: QSS has no `transition`/`animation`.** Hover/press color changes are instant swaps (as they are today). Any *smooth* motion needs **`QPropertyAnimation`/`QVariantAnimation`** on a widget property ([Qt forum](https://forum.qt.io/topic/121192/transition-in-qpushbutton-change-from-normal-to-hover-and-pressed), [Qt docs](https://doc.qt.io/qt-6/qpropertyanimation.html)). Budget: subclass a handful of high-traffic widgets (primary buttons, tab underline, the F9 Deploy button, panel expand/collapse) — don't try to animate everything.
- **Micro-interaction spec:** durations **120–180ms**, **ease-out** (`QEasingCurve.OutCubic`); animate the *focus ring* fade-in, the tab-underline slide, button press "settle," and panel open/close height. Keep it subtle — this is an IDE, not a landing page.
- **Loading states:** the app already runs async work (`jobs.py`); pair long jobs with a **QProgressBar (indeterminate)** or a lightweight **skeleton shimmer** (a `QPropertyAnimation` sweeping a gradient across placeholder rows) instead of a frozen panel. The existing `PlaceholderListWidget` empty-state pattern (`widgets.py:39`) is the right instinct — extend it to a *loading* variant.
- **Respect reduced motion (WCAG 2.3.3):** probe the OS (Windows: `SystemParametersInfo SPI_GETCLIENTAREAANIMATION` via `ctypes`; macOS: `NSWorkspace accessibilityDisplayShouldReduceMotion`) **and** expose an in-app "Reduce motion" toggle. When either is set, jump straight to end-states (no animation). Because the app ships *zero* motion today, you start compliant — the only rule is: whatever you add must be disable-able.

---

## Priority ordering for the synthesizer
1. **Restore focus visibility** (`style.py:16` + per-widget `:focus` rules) — WCAG 2.4.7 fail, one file.
2. **Raise the contrast test floors to WCAG AA (4.5 / 4.5 / 4.5, add a 3:1 border/status check) and retune the failing palette values** — the measured table names exactly which token in which theme.
3. **Adopt the 4pt spacing scale + input padding → 8px** (fixes "smushed" and the 24px target-size floor simultaneously).
4. **Introduce the type scale + tabular figures** (hierarchy + aligned ids/coords).
5. **Semantic background tints + `focus` token + color-not-alone icons** on status.
6. **`setAccessibleName` on every actionable control** (cheap screen-reader win).
7. **SVG icon set + subtle 150ms micro-interactions gated behind reduced-motion.**

Items 1–4 are the step-change in perceived quality and are pure QSS/palette/values work — the existing generate-QSS-from-a-dict architecture (`style.py:qss()`) and the enforced shared-key-set make them low-risk to land.

---

### Sources
- WCAG 2.2 What's New (new/removed criteria): https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- WCAG 2.2 spec: https://www.w3.org/TR/WCAG22/
- WCAG 2.2 new-criteria implementation guide (2.4.11/2.4.13/2.5.8): https://testparty.ai/blog/wcag-22-new-success-criteria
- Deque WCAG 2.2 resources: https://dequeuniversity.com/resources/wcag-2.2/
- WebAIM contrast (4.5:1 / 3:1, large-text definition, 1.4.11): https://webaim.org/articles/contrast/
- Qt QAccessible (setAccessibleName/Description, MSAA/AT-SPI): https://doc.qt.io/qtforpython-6/PySide6/QtGui/QAccessible.html
- Qt custom-widget accessibility for NVDA: https://andreituicu.wordpress.com/2014/08/18/how-to-implement-accessibility-for-custom-widgets-in-qt-for-nvda-screen-reader/
- Type scale for UI (6–9 steps, ratios): https://www.pacgie.com/guides/what-is-type-scale
- Modular scale practical guide: https://www.ux-republic.com/en/practical-guide-to-creating-a-modular-scale-type-for-your-interfaces/
- Fonts for data tables / tabular figures: https://wpdatatables.com/best-fonts-for-tables/ · https://valiotti.com/choosing-fonts-data-viz/
- 8pt grid & rhythm: https://www.rejuvenate.digital/news/designing-rhythm-power-8pt-grid-ui-design · https://www.designsystems.com/space-grids-and-layouts/
- Spacing best-practices (internal ≤ external, choosing a system): https://cieden.com/book/sub-atomic/spacing/spacing-best-practices · https://cieden.com/book/sub-atomic/spacing/choosing-a-spacing-system
- Semantic color tokens / dark-light parity / accent discipline: https://designsystem.backbase.com/latest/design-tokens/semantic-colors/introduction-K7Gq5Ylx · https://medium.com/design-bootcamp/color-tokens-guide-to-light-and-dark-modes-in-design-systems-146ab33023ac · https://imperavi.com/blog/designing-semantic-colors-for-your-system/
- Error/warning/success color + color-not-alone: https://paletterx.com/blog/color-for-error-and-success-states
- SVG vs icon-font vs emoji (accessibility, high-contrast): https://changethisfile.com/blog/icon-fonts-vs-svg · https://css-tricks.com/can-make-icon-system-accessible/
- Qt QSS has no transitions; use QPropertyAnimation: https://forum.qt.io/topic/121192/transition-in-qpushbutton-change-from-normal-to-hover-and-pressed · https://doc.qt.io/qt-6/qpropertyanimation.html