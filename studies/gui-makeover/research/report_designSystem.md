I have complete evidence. Compiling the report.

---

# Design-System Audit — the Workspace as CODE

Scope: the visual design system that dresses the PySide6 Workspace. Two files define the system (`editor/theme.py` — the palettes; `workspace/style.py` — the QSS); ~14 view modules consume it, and **136 inline `setStyleSheet` calls bypass it**. Net finding: the system is a **flat 22-key color dict + one 130-line QSS string**. It has real strengths (7 themes with enforced key-parity, a Fusion+QPalette fallback, a compact chrome QSS) but it is a *color palette*, **not a token system** — there is no type scale, no spacing scale, no elevation language, no semantic role layer, no motion, and no shared component vocabulary. The single most consequential structural fact: **the one "caption/hint" role is hand-reinvented ~50+ times as `f"color:{pal['muted']};font-size:11px;"`**, and the live-retheme path can only recolor a hardcoded subset of those, leaving open panels visibly stale on a theme switch (`shell.py:449`).

---

## 1. CURRENT TOKENS (what is actually defined)

### 1a. Color — the palette (`editor/theme.py:20-197`)
**22 keys per theme, 7 themes** (`LIGHT, DARK, NORD, DRACULA, SOLARIZED_DARK, SOLARIZED_LIGHT, GRUVBOX_DARK`), key-set parity enforced by a test. One key (`dark`) is a boolean flag, so **21 are colors**.

| Key | Design role it serves | Notes |
|---|---|---|
| `dark` | bool flag (is-dark) | not a color; drives OS-probe logic |
| `bg` | window/page background | elevation L0 |
| `surface` | tree/form/card surface | elevation L1 |
| `surface_btn` | neutral button face / header cell | doubles as elevation L2 **and** control fill — overloaded |
| `field` | input background (entry/list) | |
| `text` | primary on-surface text | only 2 text tones exist |
| `muted` | secondary/hint text | hand-tuned per theme "for hint legibility" (comments at `:29,:107,:157`) |
| `accent` | primary action, selection, focus | the **only** accent |
| `accent_fg` | on-accent text | the **only** "on-color" defined |
| `accent_hover` / `accent_pressed` | accent interaction states | |
| `help` / `help_hover` | violet "info/help" affordance | a *de-facto second accent*, named for one use |
| `border` | every border, everywhere | one weight only |
| `success` | OK text | text-only; no on-color, no container tint |
| `warn` | warning text | text-only |
| `error` | error text | text-only |
| `hover` / `pressed` | neutral control interaction states | |
| `scroll` | scrollbar thumb | |
| `log_bg` / `log_fg` | console/mono surface + text | |

### 1b. Typography (`workspace/style.py:17,116` + inline)
- **Only two declared roles:** UI = `Segoe UI 13px` (`style.py:17`); mono = `Cascadia Code/Consolas 12px` (`style.py:116`).
- **No scale.** Everything larger/smaller is inline. Actual sizes found in code: **22, 17, 16, 15, 14, 13, 11 px** (7 ad-hoc sizes; `11px` appears 11× as the "caption").
- **Weights:** `500`(×1), `600`(×16), `700`(×2), `bold`(×1) — inline, untokenized.
- **No line-height, one `letter-spacing`** (`shell.py:1220`). (QSS mostly can't set line-height — a real constraint.)
- **Legacy dead weight:** `theme.py:264-269` still reconfigures tkinter named fonts at **10px** — the ttk styler for the retired tkinter apps lives in the same module as the live palette.

### 1c. Spacing — **no scale exists**
- `setContentsMargins`: `(0,0,0,0)` ×40, then a scatter of `14/8/10/16/12/30/26/6/4/3/2/1` px.
- `setSpacing`: `2`(×5), `6`(×4), `10`(×4), `4, 1, 0, 8, 5, 3, 12`.
- QSS paddings: **11 distinct value-pairs** (`0 5px`, `4px`, `4px 8px`, `5px`, `5px 4px`, `5px 8px`, `6px`, `6px 10px`, `6px 12px`, `6px 22px`, `6px 9px`, `7px 16px`).
- Values *cluster* near a 2px grid but nothing is named; every widget re-picks. The toolbar even documents its magic numbers as load-bearing (`style.py:19-21`: "spacing 6 / button padding 10 … must FIT at 1280px").

### 1d. Shape / Elevation
- **Radii:** `3, 4, 6, 8, 15 px` (5 values; `6`/`8` dominate; `15` = the circular help badge). No scale, no tokens.
- **Elevation:** none. QSS has no `box-shadow`; `QGraphicsDropShadowEffect` exists in Qt but is **never used**. "Depth" is faked with 2–3 background tints (`bg`/`surface`/`surface_btn`).
- **Card primitive:** `QFrame#card` (`style.py:141`) — defined once, used **once** (Home rows). Every other "section" is a `QGroupBox` (**39 instances**) styled at `style.py:106-112`.

### 1e. Iconography
- **Text glyphs only.** Home cards: `◆ ▣ ● ⚔ ⤵ 🧍 ◈` (`shell.py:1190-1206`). Scattered in labels: `⚠`×13, `→`×10, `•`×5, `✓`×3, `⚙`, `🐤`, `▸`, `▶`. **Mix of geometric Unicode + emoji** (🧍/🐤 render in OS color-emoji font, breaking the tinted-monochrome look). The grep surfaced **mojibake (`�`)** — some multibyte glyphs are inconsistently encoded.
- Glyphs are colored `QLabel`s (`shell.py:1234`: `color:{accent};font-size:17px;` + `setFixedWidth(26)`), so sizing/alignment are per-call.
- **Tabs carry NO icons** — all 10 are text (`shell.py:928-960`).
- **One real asset:** `workspace/dreamworldix.ico` (372 KB, multi-res) — window/taskbar only (`shell.py:86-91`).

### 1f. Motion
- **None.** Zero `QPropertyAnimation / QVariantAnimation / QEasingCurve / QGraphicsOpacityEffect` anywhere. No hover/press transitions (QSS cannot animate — a genuine Qt constraint; motion needs Python animation objects). The UI is fully static.

### 1g. Theming architecture
- 7 palettes as **flat dicts**, identical key sets (test-enforced), consumed by one `string.Template` QSS (`style.py:14`, `$name` placeholders because QSS uses `{}`).
- **Fusion is mandatory** (`shell.py:122-128`) — Win11's default style paints OS chrome *under* the QSS; Fusion + a derived `QPalette` (`shell.py:94-119`, 13 roles mapped) catches everything QSS misses (native frames, combo popups, message boxes).
- Retheme is **partial by design** (`shell.py:449-468`): it swaps the global QSS + re-tints a *hardcoded* "always-alive" set (version chip, hub button, unsaved dot, inspector base, breadcrumb). Its own docstring admits: "the [panel] currently open keeps its inline hint colours until it's next rebuilt."

---

## 2. GAPS — ranked (what a modern token system needs that's absent)

**P0 — structural, blocks everything else**

1. **No semantic role layer / no shared component tokens.** The palette is raw color *values*, not roles. There is no `text-secondary`, `border-subtle`, `elevation-1`, `focus-ring`, `on-success`. Consequence: the "hint" role is re-expressed ~50+ times as a literal `f"color:{pal['muted']};font-size:11px;"` string, and there is **no reusable caption/section-header/card helper** (each module rolls its own — `savedoc._section`, `shell._header`, `shell._muted_label`, `shell._muted`, `shell._home_section`). This is the root cause of both the visual incoherence and the retheme staleness.

2. **No type scale.** 13px + 12px-mono is the entire declared system; 7 more sizes and 4 weights float inline. A newcomer-facing UI needs a named ramp (display/title/heading/body/label/caption/mono) so headings, card titles, and hints are *consistent and teachable*, not per-widget guesses.

3. **No spacing scale.** ~15 distinct margin/padding/spacing values with no tokens ⇒ the "smushed text / dense regions / unclear cohesion" the brief calls out is baked in at the pixel level. A 4px-base scale (4/8/12/16/24/32) is the single highest-leverage fix for density complaints.

**P1 — color completeness**

4. **Elevation is 2 tints, and `surface_btn` is overloaded** (it is simultaneously "elevation L2" and "neutral button fill"). Modern surfaces need 3–5 distinct levels (page / raised / overlay / sunken) so cards, docks, popovers, and the inspector read as layered rather than flat.

5. **Status colors are text-only and have no on-colors or container tints.** `success/warn/error` are only ever used as `color:` (see hotspots). There is no `info` role at all (the violet `help` is repurposed), and no `*-container`/`*-bg` variant, so a success/warning **banner** can only tint text — it can't fill a legible chip. A full set = `{info,success,warn,error} × {fg, on, container}`.

6. **Single accent + one border weight.** No secondary/tertiary accent (the app already *needs* two — `accent` and the violet `help` — but only one is named as an accent). No `border-subtle` vs `border-strong`, so separators, input outlines, and card edges all share one weight.

7. **No focus-ring, overlay/scrim, or disabled tokens.** Focus reuses `accent` (fine as a value, but not a controllable token — you can't tune ring vs fill independently). Modal dialogs have **no scrim** (`CatalogPicker`, `CommandPalette` open with no dimmed backdrop). Disabled is derived ad-hoc (`muted`+`bg`).

8. **Contrast is managed by eyeball, not contract.** `muted` was hand-nudged per theme "for hint legibility" (`theme.py:29,107,157`) — evidence there's no ratio guarantee. `11px` muted-on-surface captions (the most-repeated pattern) are a real WCAG-AA risk for the *less-technical users* this pass targets.

**P2 — polish / affordance**

9. **No iconography system.** Text-glyph mixing (geometric + emoji + mojibake) can't be tinted uniformly, doesn't scale crisply, and gives tabs no visual anchor. A monochrome SVG/icon-font set (theme-tinted) would let tabs, cards, tree nodes, and the breadcrumb share one visual language — directly serving "clearer ways to explore."

10. **No motion language.** No fade/slide on tab/panel changes, no press feedback beyond a color swap. Even minimal Qt animation (opacity fades on view swap, a focus-ring ease) reads as "modern" and reduces the abrupt, developer-tool feel. Requires Python `QPropertyAnimation` (QSS can't do it) — scope it deliberately.

11. **No elevation/shadow affordance** (Qt limit): cards and docks are edge-only. `QGraphicsDropShadowEffect` on cards/popovers/the active tab is the one available lever and is entirely unused.

12. **Ghost/typo tokens.** `modelsdoc.py:120` reads `self.pal.get('panel', 'transparent')` — **`panel` is not a palette key**, so that background is *always* transparent (silent dead code). Defensive `.get(..., '#c90')` fallbacks (`modelsdoc.py:129`) show the palette contract isn't trusted. A typed token object would make these impossible.

---

## 3. AD-HOC STYLING HOTSPOTS (refactor targets)

**136 `setStyleSheet` calls** bypass the central QSS. Distribution:

| File | count | dominant pattern |
|---|---|---|
| `shell.py` | 60 | `color:{muted}` hints, `font-weight:600;font-size:15px` headers, chrome re-tints |
| `importdoc.py` | 23 | `muted` hints (a local `muted=` string reused per method) |
| `forms_qt.py` | 12 | caption/error/help-badge/prose-pane |
| `battledoc.py` | 11 | `color:{muted}` / `color:{warn}` cell labels |
| `modelsdoc.py` | 9 | headers + the `panel` ghost token |
| `savedoc.py` | 8 | `color:{muted};font-size:11px` |
| `builddoc.py` | 7 | `color:{muted}` / `color:{accent}` dest labels |
| `tuningdialog.py` / `setupdialog.py` | 3 / 3 | intro + level marks |

**The repeated roles that should become ONE component each:**

- **Caption/hint** — `f"color:{pal['muted']};font-size:11px;"` — the single most-duplicated string. Examples: `forms_qt.py:45,65,68,105`; `savedoc.py:118,132`; `shell.py:5614,5643`; and the bare `color:{muted}` variant at **~50 sites** across all docs (e.g. `builddoc.py:82,215,243,262,512`; `importdoc.py:61,86,136,152,200,229,282,305,324,353,358,371,433,450,524,541,572,603,627,652,794,823`; `battledoc.py:194,259,276,320,548,603,609,632,974`).
- **Section header** — `"font-weight:600;font-size:15px;"` (`shell.py:972,5276`) and `"font-weight:600;font-size:16px;"` (`modelsdoc.py:109`) and `"font-weight:600;"` (`forms_qt.py:182`, `shell.py:4619`) — the same intent, four sizes.
- **Warn/error inline text** — `color:{warn}` (`battledoc.py:543`, `shell.py:3864,1767`), `color:{error}` (`forms_qt.py:106,197`).
- **The violet help badge** — a full multi-line QSS block duplicated at `forms_qt.py:473-476` and `shell.py:444-447` (+ `_retint_hub_button`).
- **Prose-over-console override** — `QTextEdit { font-family:'Segoe UI'; ... }` duplicated at `forms_qt.py:453-455` and `forms_qt.py:654-656` (fighting the global rule that makes `QTextEdit` monospace, `style.py:114`).
- **Chrome re-tints that force `retheme` to hand-maintain a list** — `shell.py:296,310,319,437,439,865,1017,1024` (crumb bar, chip, version chip, console header).
- **Transparent-background patch** — `"background: transparent;"` at `shell.py:812,1184,1239` (working around the global `QWidget{background:$bg}` rule bleeding onto nested containers — a symptom of over-broad base selectors).

**Why this matters for the makeover:** every one of these is a place the design is decided *locally*, so a global visual change (new type ramp, new spacing, a tint tweak) can't be made centrally, and a live theme switch can't reach them (§1g). Collapsing them into a token set + a handful of styled component classes (`QLabel[role="caption"]`, `[role="h2"]`, a real `Card`) is the concrete refactor.

---

## 4. RECOMMENDED TOKEN ARCHITECTURE (fits QSS/PySide6)

A design that works *within* Fusion+QSS and eliminates the hotspots. Keep the winning parts (flat theme dicts, key-parity test, the Template QSS, the QPalette fallback); add a **role layer** on top.

### 4a. Split raw palette → semantic roles (two-tier)
Keep the 7 raw palettes but **derive a semantic role map** from each (a pure function, headless-testable exactly like today). Widgets/QSS consume *roles*, never raw hues — so re-theming and re-scaling become central.

```
raw (per theme, ~20 hues)  →  roles (stable names)  →  QSS + QPalette + component classes
```

**Color roles to add (names, not values):**
- Surfaces / elevation: `surface.page` (=bg), `surface.raised` (=surface), `surface.overlay` (popover/menu, +1 tint), `surface.sunken` (console/field). Stop overloading `surface_btn`: split into `control.fill` and `surface.raised`.
- Text: `text.primary`, `text.secondary` (=muted), `text.tertiary` (new, for the 11px captions — a distinct, contrast-checked tone), `text.on-accent`.
- Borders: `border.subtle` (separators, card edges) + `border.strong` (input outline, focus base).
- Accents: `accent` + `accent.secondary` (adopt the existing violet `help` as a *named* second accent).
- Status ×3 each: `{info,success,warn,error}.fg`, `.on`, `.container` (container = a low-chroma tint for banner/chip fills; `info` newly introduced so `help` isn't overloaded).
- System: `focus.ring`, `scrim` (semi-transparent overlay for modals — Qt supports `rgba()` in QSS), `state.hover`, `state.pressed`, `state.disabled.fg`, `state.disabled.bg`.

Add contrast as a **CI contract**: a headless test asserting AA (4.5:1 body, 3:1 large/UI) for `text.*` on each surface across all 7 themes — retires the per-theme eyeball nudging.

### 4b. Type scale (named ramp, applied via QSS attribute selectors)
Six roles, Segoe UI, sizes on a modular ramp; expose as `QLabel[role="…"]` classes in the central QSS so a header becomes `lbl.setProperty("role","h2")` instead of an inline string:

| role | size / weight | replaces |
|---|---|---|
| `display` | 22 / 700 | Home title (`shell.py:1159`) |
| `h1` | 17 / 600 | |
| `h2` | 15 / 600 | section headers (`shell.py:972,5276`) |
| `h3` | 14 / 600 | card titles (`shell.py:1244`) |
| `body` | 13 / 400 | default |
| `label` | 13 / 500 | form labels (`forms_qt.py:182`) |
| `caption` | 11 / 400, `text.tertiary` | **the ~50 muted-hint sites** |
| `mono` | 12 / 400 | console |

(QSS can't do line-height; where breathing room is needed, use `contentsMargins` from the spacing scale, not font metrics.)

### 4c. Spacing scale (4px base)
Tokens `space.0/1/2/3/4/5/6 = 0/4/8/12/16/24/32`. Provide Python helpers (`margins(2)`, `gap(3)`) and use them at every `setContentsMargins/setSpacing`. This is the highest-leverage lever for the "smushed/dense" complaint — it lets density be tuned globally (even a future "comfortable/compact" toggle).

### 4d. Radius + elevation
- Radius tokens `radius.sm/md/lg/pill = 4/6/8/999`; retire `3` and `15`→`pill`.
- Elevation: define `elev.0/1/2` as (surface tint + optional `QGraphicsDropShadowEffect` blur/offset). Apply shadows to true floating layers only — **cards, the command palette, menus, the active tab** — via a `apply_elevation(widget, level)` helper (the one Qt-available depth mechanism, currently unused). Everything else stays flat/edge-only.

### 4e. Iconography
Ship a **small monochrome SVG set** (or an icon font) rendered through `QIcon` and tinted from `text.secondary`/`accent`. Replace the Home glyphs and, importantly, **add icons to the 10 tabs and tree nodes** (one shared visual language across tab/tree/breadcrumb/card — directly serving "clearer ways to explore, learn, and connect"). Purge emoji (🧍🐤) and the mojibake. Keep `dreamworldix.ico` for the window.

### 4f. Motion (scoped, opt-in)
Add a tiny `anim.py` with two reusable helpers: a `fade_in(widget, 120ms, OutCubic)` for tab/panel swaps and a focus-ring ease. Token the durations (`motion.fast=120 / .base=200`) and easing. Deliberately minimal — this is the one axis that needs Python `QPropertyAnimation` (QSS can't), so keep it to 2–3 sanctioned uses, not everywhere.

### 4g. Component layer (kills the hotspots)
Central styled classes so modules stop inlining: `Card` (replaces the 39 `QGroupBox` + the one `#card`), `Caption`/`SectionHeader` label factories (replace the ~50 muted-hint strings and the 4 header variants), `StatusChip(kind)` (uses the new `*.container`), `HelpBadge` (the violet badge, defined once). All read from the role layer, so `retheme()` becomes a single `setStyleSheet(qss(roles))` with **no hand-maintained re-tint list** — the documented staleness bug (`shell.py:449`) disappears.

### 4h. Migration shape (for the synthesizer to phase)
1. **Foundations** — add the role-map function + type/spacing/radius token dicts; keep raw palettes; contrast test. *No visual change yet.*
2. **QSS role classes** — `QLabel[role]`, `Card`, status/help classes in `style.py`.
3. **Hotspot sweep** — mechanically replace the 136 `setStyleSheet` calls with `setProperty("role",…)` / component factories, file by file (start `shell.py` → docs). Fixes the ghost `panel` token and the staleness bug as a side effect.
4. **Icons + elevation** — SVG set on tabs/tree/cards; shadows on floating layers.
5. **Motion** — the 2–3 sanctioned animations.

**Key files the plan touches:** `editor/theme.py` (add role derivation beside the palettes), `workspace/style.py` (grow the QSS with role/component classes), and every `workspace/*doc.py` + `shell.py` (hotspot replacement). The architecture stays PySide6-free where it is today (theme/style remain headless-testable), which preserves the existing test discipline.