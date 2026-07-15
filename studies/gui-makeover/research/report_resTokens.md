# External Research: Modern Design-System Tokens for a PySide6/Qt Desktop App

Scope: what a cohesive, "premium" desktop design system looks like in 2025–26 and how to express it in Qt/QSS, tuned to *this* codebase — which already generates a single QSS string from a flat 22-key palette dict (`ff9mapkit/ff9mapkit/editor/theme.py`, 7 themes) via `string.Template` (`ff9mapkit/ff9mapkit/workspace/style.py`). That existing generate-QSS-from-a-dict pipeline is exactly the right substrate; the work is to grow the dict from a flat 22-key palette into a real **token architecture** and to tokenize the non-color scales (spacing/radius/type/motion) that are currently hardcoded magic numbers scattered through the QSS template.

---

## 1. Recommended Token Architecture

### 1a. The three-layer model (industry consensus)

Modern systems (Figma, Contentful, Penpot, UXPin all converge) use **three token tiers**:

- **Primitive tokens** — raw values, reference-only, never applied directly: color ramps (`blue-500`), px measures, font sizes. ([Figma](https://www.figma.com/resource-library/design-tokens/), [Contentful](https://www.contentful.com/blog/design-token-system/))
- **Semantic (alias) tokens** — a primitive given a *role* name: `blue-500` → `action`, `text-secondary`. **Name for role, not appearance** — "a token named `text-secondary` will outlast a rebrand." Semantic tokens should point to primitives, **not chain to other semantics**. ([Penpot](https://penpot.app/blog/the-developers-guide-to-design-tokens-and-css-variables/), [UXPin](https://www.uxpin.com/studio/blog/managing-global-styles-in-react-with-design-tokens/))
- **Component tokens** — most specific: `button.bg`, `card.radius`, `input.padding`. Describe *execution*; keep them next to the component when not reused. ([Figma](https://www.figma.com/resource-library/design-tokens/))

**Where this app is today vs. the model:** the 22-key palette (`bg`, `surface`, `accent`, `accent_hover`, `muted`, `success`…) is *already a semantic layer* — but it's **hand-authored 7 times** (once per theme dict), with **no primitive ramps underneath**, so every new role means editing 7 dicts and re-picking `accent_hover`/`accent_pressed`/`hover`/`pressed` by eye. That is the core maintainability tax. The gaps that matter for this makeover:

| Missing role | Why it matters here |
|---|---|
| **Elevation tiers** — only `bg`/`surface`/`surface_btn` exist (one level) | The IDE has a page, a tree, cards (`QFrame#card`, style.py:141), an inspector, menus, a Ctrl-K palette, dialogs, and a Problems dock — all currently rendering on ~the same surface. No visual depth hierarchy. |
| **`info` status color** | Have `error`/`warn`/`success`/`help` but no info/neutral-notice — needed for the newcomer teaching layer (tips, "what is a walkmesh?"). |
| **Focus** as its own token | Focus currently *is* `accent`. A distinct focus role lets you tune a11y contrast without moving the brand accent. |
| **`on-surface-variant` / a 3rd text emphasis** | Only `text` + `muted`. Apple/Primer use 3–4 label levels; a third de-emphasis tier declutters dense panels (the brief's "smushed text" complaint). |
| **Selection-subtle / hover-tint** | Lists/trees fill full-saturation `accent` on select (style.py:93). A low-alpha accent tint reads far calmer. |
| **Scrim/overlay** | For modal dimming behind the Ctrl-K palette and dialogs. |

### 1b. Concrete target: keep 7 hand-authored palettes as a small PRIMITIVE set, *derive* the rest

Don't rewrite 7 themes into 12-step ramps by hand. The pragmatic path that fits `theme.py`/`style.py`:

**Layer 1 — base palette (per theme, hand-authored):** keep the existing hues but reframe them as a compact primitive/anchor set: a neutral anchor (`bg`), the darkest/lightest surface anchor, `text`, `muted`, one `accent`, and the status hues (`error`/`warn`/`success`/`info`). ~14 keys.

**Layer 2 — a pure `derive(base) -> tokens` function (new, in `theme.py`, tk-free/testable):** computes the *expanded semantic + component* token dict from the base via color math (Qt/QSS has **no runtime `color-mix`**, so all mixing must be precomputed in Python). This is where the elevation ladder, subtle tints, disabled states, and focus ring get generated instead of hand-picked:

```
# elevation ladder (Material-3 style tint-on-tint, since Qt has no box-shadow)
surface_1 = mix(bg, text, 0.03)      # tree / inspector
surface_2 = mix(bg, text, 0.06)      # cards
surface_3 = mix(bg, text, 0.09)      # menus / popovers / Ctrl-K palette
# interactive states, derived from ONE accent (Radix step logic)
accent_hover   = mix(accent, text, 0.10)
accent_pressed = mix(accent, bg,   0.15)
selection_bg   = rgba(accent, 0.14)   # calm list/tree selection
focus_ring     = accent               # or a tuned high-contrast variant
outline        = mix(bg, text, 0.14)
outline_variant= mix(bg, text, 0.08)  # subtle divider
text_subtle    = mix(text, bg, 0.45)  # 3rd emphasis tier
disabled_fg    = mix(text, bg, 0.60)
```

This gives you Material 3's **surface-container tiers** and Radix's **role-per-step** discipline (see §4) *without* authoring ramps by hand, and it removes the current per-theme guesswork for `accent_hover`/`accent_pressed`/`hover`/`pressed`/`scroll`. A `mix(hexA, hexB, t)` + `rgba(hex, a)` helper (~15 lines, pure) is all the color math required.

**Recommended semantic color-role set to target** (mapping Material 3 roles ([m3.material.io/styles/color/roles](https://m3.material.io/styles/color/roles)) to this app):

- Surfaces: `surface` (page), `surface_1/2/3` (raised tiers), `on_surface` (=text), `on_surface_variant` (=muted), `on_surface_subtle` (3rd tier)
- Accent: `primary`, `on_primary`, `primary_hover`, `primary_pressed`, `primary_subtle` (selection/badge fill), `on_primary_subtle`
- Lines: `outline`, `outline_variant`, `focus`
- Status: `error`/`warn`/`success`/`info` each with an `on_*` and a `*_subtle` fill (for banner backgrounds)
- Utility: `scrim`, `disabled_fg`, `disabled_bg`

Keep **one** accent (the brief asks for restraint). If you ever want to color-code the ~36 pillars, do it with a **fixed categorical hue map** (a primitive ramp used only for pillar icons/badges), not by adding secondary/tertiary brand accents.

### 1c. Non-color scales — tokenize the magic numbers

These are currently hardcoded and inconsistent in `style.py` (radius **6px** on buttons, **7px** on the search pill (line 43), **8px** on trees/tabs/groupbox, **10px** on cards (line 141); padding `6px 10px`, `6px 12px`, `7px 16px`, `4px 8px` ad hoc). A premium look demands **rhythm**, i.e. one scale. Add a **theme-independent** `SCALES` dict that `style.py` also substitutes:

- **Spacing — 4/8pt grid** (the universal standard; Carbon's `spacing-01..09` = 2/4/8/12/16/24/32/40/48px ([Carbon spacing](https://carbondesignsystem.com/elements/spacing/overview/)), Carbon's 8px "mini unit" ([2x grid](https://carbondesignsystem.com/elements/2x-grid/overview/))). Adopt `space_0=0, 1=2, 2=4, 3=8, 4=12, 5=16, 6=24, 7=32, 8=48`. Drive **layout** margins/spacing from these too, not just QSS padding.
- **Radius scale:** `radius_sm=4, md=6, lg=8, xl=12, pill=999`. Pick ONE per component class and stop mixing 6/7/8/10.
- **Type scale — 5 sizes + 2 weights.** Body 13px is fine for a dense IDE (Primer/GitHub Desktop run 12–14px). Target: `caption 11`, `label 12`, `body 13`, `title 15/16 semibold`, `display 20 semibold`; line-heights unitless ~1.35–1.5, snapped so line boxes land on the 4px grid (Primer's rule ([Primer typography](https://primer.style/foundations/css-utilities/typography))). Weights: 400 + 600 only. Keep the system font stack (`Segoe UI` here is correct on Windows — Fluent-native); only bundle a font if you need cross-platform identical rendering.
- **Motion tokens** (see §2 for the Qt mechanism). From Material 3 ([easing & duration](https://m3.material.io/styles/motion/easing-and-duration/tokens-specs)): durations `short (100–200ms)` for hover/press/small state, `medium (250–400ms)` for panel expand/dialog; easing families `standard` (cubic-bezier .2,0,0,1), `emphasized`, `decelerate`, `accelerate`. Qt equivalents: `QEasingCurve.InOutCubic` (standard), `OutCubic` (decelerate), `InCubic` (accelerate).

### 1d. Keep the generator honest

`style.py` uses `Template.substitute()` which **raises on any missing key** — keep that (it's your compile-time guarantee every theme is complete). A test already asserts key-set parity across themes (theme.py comment lines 71–75); extend it to assert the *derived* token set is complete for all 7. This is a lightweight, in-repo version of what dedicated pipelines (Style Dictionary) do: **one source of truth → generated output** ([Contentful](https://www.contentful.com/blog/design-token-system/)).

---

## 2. Qt/QSS Capabilities & Limits (what's actually achievable)

Qt Style Sheets implement roughly **CSS2, not CSS3** ([Qt Forum](https://forum.qt.io/topic/26107/solved-unknown-property-box-shadow-styling-with-css)). Know the ceiling before designing to it:

**Works in QSS (use freely):**
- Pseudo-states: `:hover :focus :pressed :checked :disabled :selected :on/:off`, and `:!` negation.
- **Property selectors** `QToolButton[popupMode="2"]` (already used, style.py:35) — the Qt way to do variant styling; set a dynamic property in Python + `style().polish(w)` to re-apply.
- `rgba()` **alpha colors** — this is how you get the subtle selection tints/scrims from §1b without a compositor.
- `qlineargradient`/`qradialgradient` — the only way to fake soft inner-highlight/elevation *within* QSS; a 1–2% top-to-bottom gradient on cards reads as gentle lift.
- `border-image` **9-slice** — the QSS-only way to fake a drop shadow (a pre-rendered shadow PNG sliced around the widget). More work but travels with the stylesheet.
- Per-subcontrol styling (`::indicator ::menu-indicator ::handle ::section ::tab ::title`) — already leveraged well.

**Does NOT work in QSS (and the workaround):**
- **`box-shadow`** → not supported. Elevation options, best-first for this app: **(a) tint-based tiers** (Material 3 model — `surface_1/2/3`, zero cost, no clipping bugs — *make this the default*); **(b) `QGraphicsDropShadowEffect`** for the few genuinely floating layers (menus, dialogs, the Ctrl-K palette, toasts) via `setGraphicsEffect()` — but note it's **one effect per widget**, doesn't compose with other effects, and can **bleed past rounded corners / clip oddly** on a widget with a QSS `border-radius`; wrap the rounded content in a transparent container and put the shadow on the container. ([QGraphicsDropShadowEffect docs](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QGraphicsDropShadowEffect.html)); **(c)** 9-slice `border-image`.
- **`transition` / animation in QSS** → not supported. Animate via **`QPropertyAnimation`** on a real Qt property with a setter that triggers a repaint ([pythonguis](https://www.pythonguis.com/tutorials/pyside6-animated-widgets/)). Animatable without custom painting: `windowOpacity` (fades), `geometry`/`pos`/`size` (slides), `maximumHeight` (expand/collapse panels), `QGraphicsOpacityEffect.opacity` (cross-fades), the drop-shadow's `blurRadius`/`color` (hover lift). For an animated *background color* you expose a custom `@Property(QColor)` and repaint. Default Qt anim duration is 250ms; use 120–180ms for hovers.
- **`transform` / rotation / scale** → none in QSS; use `QGraphicsView`/custom paint or animate geometry.
- No `text-overflow: ellipsis` control in most widgets → use `QFontMetrics.elidedText()` in code; `QLabel` needs manual elision.
- No outer-glow focus ring → approximate with a 2px `border` on `:focus` (compensate padding by 1px to avoid reflow), or paint it.

**QSS × QPalette × Fusion — the interplay (important, this app sets a full QSS):**
- **QSS overrides QPalette.** Once a stylesheet touches a widget, `setPalette()`/`setFont()` on it can silently no-op, and the widget **won't follow OS theme changes** ([KDAB](https://www.kdab.com/say-no-to-qt-style-sheets/), [runebook](https://runebook.dev/en/docs/qt/qwidget/palette-prop)). **Don't mix** palette-driven and QSS-driven coloring on the same widgets — pick QSS (which this app has) as the single source, and if you also set a `QPalette` do it only for things QSS can't reach (e.g., `QToolTip` base, text-cursor, some item-view details). ([Qt Forum: mixing](https://forum.qt.io/topic/117293/)).
- **Fusion is required** (already the case) because native Windows/macOS styles ignore most color options — the same reason `theme.py` forces `clam` for the tk side (theme.py:8–12). Fusion + QSS is the recommended pip-distribution combo for consistent cross-OS rendering ([pythonguis](https://www.pythonguis.com/faq/installation-via-pip-styling/)).
- **Perf caveat:** every `setStyleSheet()` reparses; reparenting clears the cache ([KDAB](https://www.kdab.com/say-no-to-qt-style-sheets/)). Set the big stylesheet **once at the app level** (not per-widget) and re-set only on theme switch — which the single-string design already does.
- **When to drop to custom painting:** KDAB's stance is QSS doesn't scale to complex/native-integrated UIs and a `QProxyStyle`/`QStyle` subclass is more robust ([KDAB](https://www.kdab.com/say-no-to-qt-style-sheets/)). For *this* app that's overkill — but reserve custom `paintEvent`/`QStyledItemDelegate` for the handful of showpiece widgets where QSS can't deliver: elevated cards with shadow+radius, animated toggles, the tree's rich rows (icon + title + subtitle + badge), status pills, and empty-state panels.

**High-DPI:** Qt6 **auto-enables** high-DPI scaling — no `AA_EnableHighDpiScaling` needed ([Qt High DPI](https://doc.qt.io/qt-6/highdpi.html)). Use **px in QSS** (they're logical px, scaled by `devicePixelRatio`); font point sizes track OS scaling. The one gotcha: **raster assets** (`QPixmap`/icons) are raw device pixels — ship SVG icons (Qt renders them crisp at any DPI) or `@2x` PNGs; `QGraphicsDropShadowEffect` blur is in logical px so it's DPI-safe.

---

## 3. Premium Polish Checklist (all Qt-achievable)

1. **8pt spacing rhythm, applied to *layouts* not just QSS.** Set every `QLayout` margin/spacing from the spacing scale (§1c). Uniform rhythm is the single biggest "premium" signal and directly answers "smushed text, dense regions."
2. **Elevation ladder via surface tint** (Material 3 model): page `surface` < tree/inspector `surface_1` < cards `surface_2` < menus/popovers/Ctrl-K `surface_3` < dialogs `surface_3` **+** a *real* `QGraphicsDropShadowEffect` only on floating layers. Never shadow every card (perf + corner bleed).
3. **One radius per component class** from the radius scale — kill the current 6/7/8/10 drift.
4. **Restrained, meaningful accent.** One accent for primary action + focus + active-tab only. Replace full-saturation `accent` list/tree selection (style.py:93) with `primary_subtle` (accent @ ~12–14% alpha) + `on_surface` text — far calmer, still clearly selected. Reserve `error/warn/success/info` strictly for status.
5. **Three text-emphasis tiers** (`text` / `muted` / `subtle`) so dense panels can de-emphasize labels/units/hints instead of cramming everything at full contrast.
6. **Visible, consistent focus ring** on *every* interactive widget (2px accent border on `:focus`, padding-compensated). Accessibility + polish; currently uneven across widget types.
7. **Consistent iconography:** one SVG icon set, on a 16/20/24 size grid, tinted `on_surface_variant` by default and `primary` when active. SVG keeps them crisp at all DPI. Icons on tabs, tree rows, and toolbar unify the shell.
8. **Empty states everywhere** (icon + one plain-language line + a primary CTA) for the tree, Problems dock, each tab before a project is open, search-with-no-results. This is the **highest-leverage newcomer-learnability** move and is pure QWidget composition.
9. **Subtle motion** (respecting a "reduce motion" pref): 120–180ms hover/press feedback, 200–250ms panel/inspector expand-collapse (`maximumHeight` anim), 150ms tab/page cross-fade (`QGraphicsOpacityEffect`), 200ms Ctrl-K palette fade+slide (`windowOpacity`+`pos`). Easing `InOutCubic`/`OutCubic`.
10. **Dividers + whitespace over boxes.** Prefer 1px `outline_variant` dividers and spacing to group, instead of nesting `QGroupBox` outlines (style.py:106) — reduces the "dense/boxy" noise the brief calls out. Keep boxes only where a section genuinely needs a labeled container.
11. **Status as pills/badges**, not colored text: small rounded `*_subtle` fill + `on_*_subtle` text — reads as designed, not debug output.
12. **Tighten the mono/console block** (style.py:114): a distinct `surface`/`outline`, generous padding, and the same radius scale, so the Output/Problems dock looks intentional rather than a raw terminal.
13. **Light/dark parity discipline:** derive both from the same `derive()` function so tiers/tints/focus are structurally identical across all 7 themes; test contrast (aim WCAG AA 4.5:1 body text, 3:1 large/UI) — Radix targets APCA Lc60/Lc90 for the two text steps ([Radix](https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale)).

---

## 4. Reference Systems — the one transferable idea from each

1. **Material 3 — tint-based surface-container elevation.** Elevation via "incremental container color shifts," no shadow reliance ([m3 color roles](https://m3.material.io/styles/color/roles)). *Transfer:* this is **the** elevation strategy for a no-`box-shadow` Qt app — adopt the `surface_1/2/3` ladder as your default depth model; reserve shadows for floating layers only.

2. **Radix Colors — a 12-step scale with a fixed role per step** (1–2 backgrounds, 3–5 interactive normal/hover/pressed, 6–8 borders, 9–10 solid, 11–12 text) ([Radix scale](https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale)). *Transfer:* gives you a **principled recipe to derive** `hover`/`pressed`/`outline`/`selection`/text tiers from one accent hue in `derive()`, replacing the per-theme hand-picking of `accent_hover`/`accent_pressed`. Also: APCA/AA contrast targets baked into the steps.

3. **IBM Carbon — a numeric spacing token ladder on a 2px/8px mini-unit** (`spacing-01..09`) + role-based type tokens ([Carbon spacing](https://carbondesignsystem.com/elements/spacing/overview/), [2x grid](https://carbondesignsystem.com/elements/2x-grid/overview/)). *Transfer:* the exact **spacing scale to adopt** and the discipline of driving *all* geometry (grid, margins, padding) from one unit.

4. **GitHub Primer — role-named tokens + system font stacks + unitless line-heights on a 4px grid** (`fg.default/fg.muted/fg.subtle`) ([Primer typography](https://primer.style/foundations/css-utilities/typography)). *Transfer:* "**name for role, not appearance**," the 3-tier foreground naming (motivates your third text emphasis), and keeping the native system font (validates `Segoe UI`).

5. **Apple HIG / macOS semantic system colors — 4 label emphasis levels** (primary/secondary/tertiary/quaternary) and materials for depth. *Transfer:* the idea that **text hierarchy is a first-class scale**, not just "normal + grey"; and depth via translucent materials → maps to your tint tiers.

6. **Microsoft Fluent 2 — neutral-first layering, subtle strokes, accent used sparingly; Windows-native language.** *Transfer:* since this is a **Windows** app on Segoe UI, Fluent's "neutral surfaces + one restrained accent + hairline strokes" is the most native-feeling target — directly supports the "restrained accent / purposeful color" polish goal.

7. **Tailwind — the primitive→semantic split via generated variables + a numeric scale mindset** (`space-1..12`, `rounded-sm..xl`) ([UXPin](https://www.uxpin.com/studio/blog/managing-global-styles-in-react-with-design-tokens/)). *Transfer:* ergonomics — expose tokens as `$space_4`, `$radius_lg`, `$font_body` placeholders in the QSS template so authoring reads as intent, not magic numbers.

8. **Style Dictionary — one JSON token source, transformed to many platform outputs** ([Contentful](https://www.contentful.com/blog/design-token-system/)). *Transfer:* validates and formalizes what `style.py` already half-does. Keep it in-house: **base palette (per theme) → `derive()` → token dict → `Template.substitute()` → QSS**, with a parity test as the "build fails if a token is missing" guarantee.

---

### Bottom line for the plan

The codebase's `theme.py` + `style.py` generate-from-a-dict pattern is already the correct architecture — it just stops at a flat, hand-authored semantic layer. The step-change is: **(1)** insert a pure `derive(base)->tokens` function that computes an *elevation ladder*, *subtle interactive tints*, a *third text tier*, *focus*, *info*, and *scrim* from a smaller hand-authored base (color math precomputed in Python, since QSS has no `color-mix`); **(2)** add theme-independent **spacing / radius / type / motion** scales and thread them through both the QSS template *and* the Qt layouts; **(3)** spend the Qt-specific budget on the four things QSS can't do — tint-tier + selective drop-shadow elevation, `QPropertyAnimation` micro-motion, SVG iconography, and composed empty-state/pill widgets — which together deliver the "premium, learnable, un-smushed" result the brief asks for.

**Sources:** [Figma design tokens](https://www.figma.com/resource-library/design-tokens/) · [Contentful token system](https://www.contentful.com/blog/design-token-system/) · [Penpot developer guide](https://penpot.app/blog/the-developers-guide-to-design-tokens-and-css-variables/) · [UXPin global styles](https://www.uxpin.com/studio/blog/managing-global-styles-in-react-with-design-tokens/) · [Material 3 color roles](https://m3.material.io/styles/color/roles) · [Material 3 motion tokens](https://m3.material.io/styles/motion/easing-and-duration/tokens-specs) · [Radix Colors scale](https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale) · [Carbon spacing](https://carbondesignsystem.com/elements/spacing/overview/) · [Carbon 2x grid](https://carbondesignsystem.com/elements/2x-grid/overview/) · [Primer typography](https://primer.style/foundations/css-utilities/typography) · [Qt QGraphicsDropShadowEffect](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QGraphicsDropShadowEffect.html) · [QSS box-shadow unsupported (Qt Forum)](https://forum.qt.io/topic/26107/solved-unknown-property-box-shadow-styling-with-css) · [KDAB "Say No to Qt Style Sheets"](https://www.kdab.com/say-no-to-qt-style-sheets/) · [QPalette vs QSS (runebook)](https://runebook.dev/en/docs/qt/qwidget/palette-prop) · [Fusion styling for pip apps](https://www.pythonguis.com/faq/installation-via-pip-styling/) · [PySide6 QPropertyAnimation](https://www.pythonguis.com/tutorials/pyside6-animated-widgets/) · [Qt6 High DPI](https://doc.qt.io/qt-6/highdpi.html)