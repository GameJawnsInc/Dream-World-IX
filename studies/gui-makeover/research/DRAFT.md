# The Workspace Makeover — A Phased Plan

## 1. North-star vision

The made-over Workspace feels like **one calm, confident instrument** — a coherent creative IDE where a newcomer can open a working FF9 room in their first five minutes and an expert can still deploy-and-test on a single keystroke. Surfaces breathe (a real spacing rhythm, a legible type hierarchy, layered depth instead of a flat grey plane), color *means something* (accent = the one thing to do next; status hues = status only), and every intimidating word — journey, fork, walkmesh, gEventGlobal — is teachable in place, the moment you meet it. The central tension is **power-density vs. approachability**: this app fronts 112 CLI commands across ~36 pillars through 10 tabs, and that compression is real. The resolution principle is the one every mature tool converges on: **a fast hidden lane for experts (Ctrl-K, F9/F6, keyboard everywhere) is what earns the right to make the *visible* lane calm.** We don't dumb the tool down; we disclose it progressively, teach it in context, and dress it in one coherent visual system — so the same window serves the frightened first-timer and the byte-level power user without either feeling it was built for the other.

## 2. Design principles

1. **Progressive disclosure by default.** Basics visible; expert controls (`mesID`, `gEventGlobal` band, `scenario`, donor offsets, fork modes) one deliberate step away — never on the front surface. Two tiers max (NN/g). Reports C-F4, E-§3, G-P3.
2. **Teach in context, in plain language.** Define a term where it first appears; plain label on the surface, engine term in the tooltip ("Story flag" on the label, "gEventGlobal, save-persistent" on hover). Never a manual the user won't open. Reports D-§2, G-P7, H-§4.
3. **One coherent visual system.** Every color, size, space, radius, and motion value comes from named tokens — not the 136 inline `setStyleSheet` calls and ~15 ad-hoc spacing values live today. Evolve `theme.py`/`style.py`, don't rewrite them. Reports B, F.
4. **Never punish the expert.** Anything simplified stays reachable in ≤2 clicks via Ctrl-K; F9/F6 loop stays one keystroke; a "Full/Advanced" mode is always one click away; nothing is *removed*, only *deferred*. Reports E-§4, G, H-anti-patterns.
5. **Color means something.** One restrained accent for the single primary action + focus + active state; `success/warn/error/info` reserved strictly for status; never status-by-color-alone (icon + text). Reports A-#2, F-§3.4, I-§4.
6. **Reversible & safe, and say so.** Surface the existing backup/revert story in plain words where nerves peak ("Deploys are reversible; your game is backed up first"). Reports D-G8, G-P11.
7. **Accessibility is a floor, not a finish.** WCAG 2.2 AA on contrast, focus, target-size, color-independence across all 7 themes — enforced by tests, not eyeball. Report I.
8. **Honor the tree as the one mental model.** journey▸campaign▸field▸object is the spine users learn once; breadcrumb, Map, and Ctrl-K reinforce it. Reports C-F10, G-P9.

## 3. The three problems, evidenced

### SMUSHED TEXT
Quantified, not asserted. **`muted` hint text fails WCAG AA 4.5:1 on 5 of 7 themes** (Report I measured table: nord 4.04/3.71, solarized-dark 4.02/3.48, solarized-light, light 4.46) — the "grey hint you can barely read." Spacing lives off-grid: toolbar spacing 6, button padding `6px 10px`, tree items `5px 4px`, GroupBox `margin-top:10/padding-top:8`, checkbox `spacing:7` — values of 5/6/7/9/10 on no grid (`style.py:22,26,91,107,57`). Forms stack six identical rows in one flat column with label, field, and hint all at the same ~11-13px weight, so "6 fields read as one gray brick" (Report A, `02_editor_field.png`, `R_cutscene.png`). The one caption role is hand-reinvented ~50+ times as `f"color:{pal['muted']};font-size:11px;"` (Report B).

### DENSE REGIONS
The **Import tab is one `QScrollArea` stacking ~8-10 GroupBoxes** fusing four unrelated jobs (fork one field / fork a region / browse catalog / bulk archive) plus repaint-native — 68 widget instantiations, the heaviest surface in the app (Report E-§2, `importdoc.py:50`). **Build & Deploy shows six co-equal panels** regardless of context, including the New-Game single-owner footgun visually equal to routine Build (`builddoc.py:113-249`). **Battle shows a full column of dead action buttons and two competing empty-state sentences with nothing loaded** (Report A-#6, `08_battle.png`). Story State / Item & Equip fill the whole central pane with a **black console void** (Report A-#11). Save editors nest sub-tabs inside the tab (Report E-#4).

### UNCLEAR COHESION
The root cause is structural: **the 10-tab strip carries three incompatible axes on one row** — a landing page (Home), views of the open project (Editor, Map), orthogonal save-file editors (Story State, Item & Equip), and five self-contained mini-apps (Battle, Models, Build, Import, Co-op that doesn't even read the open project). A tab strip implies "different views of one subject"; here tab 1 and tab 8 share nothing (Report C-F1). Worse, **the strip is confined to the 640px middle splitter pane and can never widen**, so ~half the tabs clip into scroll chevrons at default size — Import and Co-op hide entirely (Report C-F2, `shell.py:965,995`). Visually, everything is **one flat grey plane**: toolbar, tree, tabs, form, inspector, console share 2-3 near-identical dark surfaces separated only by 1px hairlines at ~1.3:1 contrast (below the 3:1 WCAG floor for a control edge) — "nothing is elevated, tinted, or weighted to tell the eye where to start" (Reports A-#1, I). The single accent is spent on the **wrong thing**: the violet Info Hub button is the only saturated element, implying a reference catalog is the primary action while Deploy — the button that ships work — is a tiny un-accented dark button that nearly vanishes in light theme (Reports A-#2/#10).

### The newcomer-accessibility gap
There is **no first-run experience, no sample-project loader, and no in-app link to the excellent on-disk docs** (`docs/GLOSSARY.md`, `docs/tutorials/`) (Report D-§1,G3). The first modal a bundled user sees is a network-privacy consent dialog before they know what the app is (`shell.py:478`). The entire conceptual onboarding is **one circular sentence** using four undefined nouns (`shell.py:1173`). The recommended first action ("Journey ▸ Open") points at the *deepest* abstraction; the first creative action (New Field) demands "Area (≥10)" and "Camera pitch" a non-modder can't answer (Report D-Stall #1,#2). Domain vocabulary (journey, campaign, field, fork/verbatim/native, walkmesh, gEventGlobal, gateway, encounter, mesID, FBG, Memoria, F6, deploy, scenario) is never taught at first contact — the one place it's done well (Info Hub's `_HUB_HELP` "?") only covers catalog kinds, not app structure (Report D-§2). And there is **zero screen-reader labelling** (`setAccessibleName`) and a **global `* { outline: 0 }` that kills the focus ring on every non-input control** — a flat WCAG 2.4.7 fail (Report I-§0).

## 4. Cross-cutting foundations

These four substrates are built first (Phases 1-2) because every later phase consumes them.

### (a) Design token system — *what:* a three-tier token architecture grown from the existing dict pipeline. *Why:* the app already generates one QSS string from a flat 22-key palette via `string.Template` — the correct substrate, but it stops at a hand-authored semantic layer with no primitives, no type/spacing/radius/motion scales, and one overloaded surface tier. The evolution (not rewrite):
- **A pure `derive(base) -> tokens` function** in `theme.py` (tk-free, testable) that computes an elevation ladder (`surface_1/2/3` via Material-3 tint-on-tint, since QSS has no `box-shadow`), subtle interactive tints (`selection_bg` = accent @ ~14% alpha, replacing full-saturation selection), a third text tier (`text_subtle`), `focus`, `info`, `scrim`, and disabled states — from a smaller hand-authored base per theme. A ~15-line `mix(a,b,t)` + `rgba(hex,a)` helper is all the color math (precomputed in Python; QSS has no `color-mix`). Reports F-§1b, B-§4a.
- **Theme-independent scales**: spacing 4pt (`0/4/8/12/16/24/32/48`), radius (`sm4/md6/lg8/pill`), a 6-9-step type ramp (display 24 / h1 20 / h2 16 / body 13 / caption 11 / mono 12, three weights 400/500/600, line-heights on the 4px grid), motion durations (120-180ms fast, 200-250ms medium) + easing. Threaded through both the QSS template *and* the Qt layout `setContentsMargins/setSpacing`. Reports F-§1c, I-§2,§3.
- **A component layer** (`QLabel[role="caption"/"h2"]`, a real `Card`, `StatusChip`, `HelpBadge`) that kills the 136 inline styles and, as a side effect, fixes the retheme-staleness bug (`shell.py:449`) and the ghost `panel` token (`modelsdoc.py:120`). Report B-§4g.

### (b) IA / navigation reorganization — *what:* regroup the 10 flat tabs into ~5 task-based **workspaces** and lift the tab strip out of the 640px pane. *Why:* the mixed-axis strip *is* the incoherence, and its confinement is the mechanical overflow bug. Group by intent (Blender/DaVinci model): **Author** (Editor, Map) · **Assets** (Import, Models, Battle) · **State** (Story State, Item & Equip — fenced as the orthogonal save layer) · **Ship** (Build & Deploy, Co-op) · **Learn/Home**. Strengthen Ctrl-K into a true verb-first, category-prefixed command palette — the escape hatch that makes simplification safe. Reports C-§3 Option A, E, G-P1/P2.

### (c) Learnability layer — *what:* a first-run → first-success → in-context-help → concept-scaffolding → exploration ladder, each reusing an existing surface. *Why:* the app has help (tooltips) but it's passive, uniform, and un-sequenced with no path to a first win. Concretely: a guided first-run that *sequences* the existing `SetupHealthDialog` steps and ends on a creative action; a "New from sample" gallery over the bundled `examples/`; a concept-card registry extending `_KIND_HELP` surfaced via `setWhatsThis` + an Inspector "About this…" panel + Ctrl-K + a "?" on jargon labels; teaching empty-states; and a "How it all fits" concept map reusing `editor/graphview`. Reports D-§4, G-P4/P5/P7, H-§2.

### (d) Accessibility baseline — *what:* WCAG 2.2 AA on contrast/focus/target-size/color-independence across all 7 themes + basic screen-reader labelling. *Why:* two one-line-visible gaps undercut a real head start (the app already has a WCAG luminance test and 7 parity-enforced themes). Replace `* { outline: 0 }` with per-widget `:focus` rings; raise the contrast-test floors from 4.0/2.7/3.0 to AA (4.5/4.5/4.5 + a 3:1 border/status check) and retune the named failing tokens; audit 15px indicators to the 24px target floor; add `setAccessibleName` to every actionable control; never status-by-color-alone. Report I.

## 5. The phased plan

Ordered so foundations land first and each phase ships visible value. The offscreen-screenshot harness (native Windows `WA_DontShowOnScreen` + `grab()`, per Report A) makes most success criteria screenshot-verifiable; the QSS-from-dict architecture keeps theme/token work headless-testable.

---

### Phase 0 — Quick wins & safety net (ship first, de-risks everything)
- **Goal:** immediate visible relief + guardrails, no architecture change.
- **Scope (in):** re-rank toolbar color so Deploy is the accent and Info Hub demotes to violet-outline; group the toolbar with separators (Open · Edit · Validate · Ship · Info); collapse the empty console dock by default (`_toggle_console` exists); merge Battle's two empty-state messages and hide its dead action column until a battle loads; unify the lone 🧍 emoji to a monochrome glyph; fix light-theme Deploy/console contrast; **restore the focus ring** (delete `* { outline:0 }`, add per-widget `:focus`). **(out):** token system, tab reorg, onboarding.
- **Deliverables:** the Report A "Quick Wins" list + Report I priority #1 (focus).
- **Dependencies:** none.
- **Effort:** S.
- **Risks & mitigations:** focus-ring reflow → pad-compensate the 2px border; toolbar regrouping muscle-memory → keep all actions, only add separators.
- **Success criteria:** screenshot shows Deploy as the single accent in both themes; Tab-key walkthrough shows a visible ring on buttons/tabs/tree; console dock absent on cold start; Battle empty state = one message, no dead buttons.

### Phase 1 — Token foundation (the visual substrate)
- **Goal:** insert the `derive()` function + scales + component classes with *no visual change yet* — an evolution of `theme.py`/`style.py`.
- **Scope (in):** the `derive(base)->tokens` color function (elevation ladder, tints, 3rd text tier, focus/info/scrim/disabled); spacing/radius/type/motion scale dicts substituted into the QSS template; QSS role classes (`QLabel[role]`, `Card`, `StatusChip`, `HelpBadge`); extend the parity test to the derived set; **raise contrast-test floors to AA and retune failing palette values** (Report I's table names each). **(out):** applying tokens app-wide (that's Phase 2), icons, motion.
- **Deliverables:** expanded token architecture per Reports F-§1 and B-§4; a green contrast CI contract across 7 themes.
- **Dependencies:** Phase 0.
- **Effort:** M.
- **Risks & mitigations:** hand-authored palettes drift from derived → keep 7 bases small, derive the rest; contrast retune shifts brand feel → tune base hues, not the derivation.
- **Success criteria:** all 7 themes pass AA at 4.5/4.5/4.5 + 3:1 borders/status (test); token dict complete for every theme; no pixel change in screenshots yet (proves the substrate is inert until applied).

### Phase 2 — The "de-smush" pass (apply tokens; spacing + type hierarchy + elevation)
- **Goal:** the step-change in perceived quality — replace the flat grey plane and cramped forms with rhythm, hierarchy, and depth.
- **Scope (in):** mechanically replace the 136 inline `setStyleSheet` calls with `setProperty("role",…)`/component factories, file by file (`shell.py` → docs); apply the 4pt spacing scale to every layout margin/spacing (label→field 4, field→field 12, section→section 24, input padding →`8px 10px`, tree rows →`6px 8px`); apply the type ramp (label ≠ value ≠ hint); apply the elevation ladder (page < tree/inspector < cards < menus/palette) + a real `QGraphicsDropShadowEffect` on floating layers only; redesign the Inspector as a grouped data card (Identity/Contents/Connections); replace black-void empty states with icon + one-line purpose + primary action; a **density toggle** (Comfortable default / Compact) via two QSS-var sets. **(out):** IA reorg, onboarding, icons.
- **Deliverables:** Reports A-Structural (elevation, inspector, empty-states), I-§2/§3, B-hotspot sweep.
- **Dependencies:** Phase 1.
- **Effort:** L.
- **Risks & mitigations:** 136-site sweep regressions → do it per-file with screenshot diffs; retheme staleness → the component layer eliminates the hand-maintained re-tint list; drop-shadow corner-bleed → shadow a transparent wrapper, not the rounded widget (Report F-§2).
- **Success criteria:** before/after screenshots of Editor/Cutscene/Inspector show three distinct type weights and grouped sections; regions read as layered (measurable surface-tint deltas); zero `color:{muted};font-size:11px` inline strings remain (grep); density toggle visibly re-rhythms rows.

### Phase 3 — IA / navigation reorg + full-width strip + Ctrl-K palette
- **Goal:** an honest spatial metaphor and the expert escape hatch that makes later simplification safe.
- **Scope (in):** lift the tab strip to full window width (kills the 640px clip structurally); regroup 10 tabs into ~5 task workspaces (Author/Assets/State/Ship/Learn), fencing the save pair; split Import's four fused jobs (fork-one-field foregrounded, region/archive/repaint behind disclosure); collapse Build & Deploy's six panels into a guided deploy + an "advanced" drawer; promote Ctrl-K to verb-first names + category prefixes + keybinding hints + concept matching. **(out):** the CLI-only world-*/audio/image-field backlog (fenced, §7); new feature wiring.
- **Deliverables:** Reports C-§3 Option A (+ folded-in Option C ideas), E-§2 top-two reorg targets, G-P1/P2.
- **Dependencies:** Phase 2 (workspaces need the card/elevation vocabulary).
- **Effort:** L.
- **Risks & mitigations:** users relearn where tabs went → keep every "Go to X" in Ctrl-K + a one-time callout; `QTabBar` can't render separators → host workspaces as a lightweight rail/segmented control above the tabs; preserve all keybindings.
- **Success criteria:** at 1280px no tab clips into a chevron (screenshot); Import default view shows only the simple-fork path; Ctrl-K surfaces "gateway" as a concept card; deploy still reachable via F9 + palette + one visible button.

### Phase 4 — Learnability layer (first-run, samples, in-context help, concept map)
- **Goal:** convert the first 10 minutes from "read a paragraph, fail a form, find a diagnostics panel" into "get set up in order, open a working example, look up any word."
- **Scope (in):** a 3-step guided first-run (locate game → extract templates → open a sample/make first field) that *sequences* existing `SetupHealthDialog` actions and defers the update-consent modal; a "Learn by example" Home section that opens read-only copies of `examples/` (vivi-hut, stolen-ember, thirteenth-character); a concept-card registry extending `_KIND_HELP` surfaced via `setWhatsThis` + a collapsible Inspector "About this…" + a "?" affordance on jargon labels (`forms.Field.concept` key) + Ctrl-K; teaching empty-states on tree/Map/Story State/Problems; a "How it all fits" concept map (reuse `editor/graphview`); a global **Guided/Full mode** with per-form Advanced accordions. **(out):** the aspirational full interactive coach-marks walkthrough (defer).
- **Deliverables:** Reports D-§4 (4a-4h), G-P3/P4/P5/P7, H-§2 stages 0-3.
- **Dependencies:** Phase 3 (help hangs off the reorganized surfaces + palette).
- **Effort:** L.
- **Risks & mitigations:** "kiddie mode" feel → Full is one click, nothing removed, Ctrl-K always reaches hidden surfaces; tooltip fatigue (NN/g: 82% dismissed <1.2s) → depth goes in What's This/Inspector, not more tooltips; blank-canvas trap → samples ship before the toggle.
- **Success criteria:** a first-launch user reaches a running sample without hitting an engine-param form; every term in the §3 vocabulary list resolves to a plain-language card in ≤2 interactions; Guided mode hides `mesID`/`scenario` fields, Full restores them.

### Phase 5 — Iconography
- **Goal:** one visual language across tabs, tree, breadcrumb, cards, toolbar.
- **Scope (in):** replace unicode/emoji/mojibake glyphs with a monochrome SVG set (Lucide/Feather/Fluent, OSS-licensed) rendered via `QIcon`+`QtSvg`, tinted from `text_secondary`/`accent`; add icons to the 10 tabs (workspace rail), tree nodes, breadcrumb; grid-align at 16/20/24; pair every icon with a label or `setAccessibleName`. **(out):** custom illustration; motion.
- **Dependencies:** Phase 1 (tint tokens), Phase 3 (tab/rail structure).
- **Effort:** M.
- **Risks & mitigations:** DPI crispness → SVG only; license → OFL/MIT/ISC sets; high-contrast mode → SVG (not icon-font) survives.
- **Success criteria:** zero emoji/mojibake in the UI (grep); tabs+tree+breadcrumb share one glyph family; icons re-tint correctly across all 7 themes (screenshot matrix).

### Phase 6 — Accessibility hardening across all 7 themes
- **Goal:** provable WCAG 2.2 AA everywhere + screen-reader baseline.
- **Scope (in):** `setAccessibleName`/`Description` on every actionable control (currently zero); target-size audit (24×24 min, pad buttons not glyphs); status = icon+text not color-alone in Problems/lint/Check; focus-not-obscured check on scroll; 200%-zoom/font-scaling survival (the 1280-tuned toolbar is the risk); custom-canvas accessibility for tree/graph/map. **(out):** deep `QAccessibleInterface` trees beyond the canvases (stretch).
- **Dependencies:** Phases 1-2 (focus token, contrast) + 5 (icons carry the status shapes).
- **Effort:** M.
- **Risks & mitigations:** toolbar clipping at 150% → verify against the "must FIT at 1280px" note (`style.py:20`); screen-reader coverage of custom widgets → `setAccessibleName` suffices for common cases.
- **Success criteria:** AA contrast/focus/target/color-independence checklist (Report I-§1) passes on all 7 themes; NVDA/Narrator reads meaningful names for toolbar + tabs + tree; UI legible at 200% with no truncation.

### Phase 7 — Polish & motion pass
- **Goal:** the final "premium, intentional" layer.
- **Scope (in):** 2-3 sanctioned `QPropertyAnimation` uses only — 120-180ms tab/panel cross-fade, focus-ring ease, panel expand/collapse (`maximumHeight`), Ctrl-K palette fade+slide; status as pills not colored text; dividers+whitespace over nested GroupBox outlines; loading states (indeterminate progress/skeleton) on long `jobs.py` work; all motion gated behind an OS reduced-motion probe + in-app toggle. **(out):** animating everything (deliberately scoped).
- **Dependencies:** all prior.
- **Effort:** M.
- **Risks & mitigations:** motion sprawl → keep to 2-3 helpers in one `anim.py`; WCAG 2.3.3 → ≤200ms, disable-able, jump-to-end on reduced-motion.
- **Success criteria:** tab switches and palette open animate smoothly ≤180ms; reduced-motion toggle produces instant end-states; no frozen panel during a build (progress visible).

## 6. Sequencing & milestones

**Recommended order and rationale:**
- **P0 first** — cheap, visible relief + the one-file WCAG focus fix; buys goodwill and de-risks.
- **P1 before P2** — you can't apply tokens you haven't defined; keeping P1 visually inert proves the substrate is safe.
- **P2 before P3** — workspaces/cards need the elevation + card vocabulary to look like one system.
- **P3 before P4** — the learnability layer hangs off reorganized surfaces and the enriched palette; the escape hatch (Ctrl-K) must exist before you hide anything.
- **P5/P6 after structure settles** — icons carry status shapes; accessibility hardening wants the final focus token, icons, and layout.
- **P7 last** — motion is the garnish, not the meal.

**Milestones — "you can tell it worked when…":**
1. **De-smush proven (end P2):** side-by-side screenshots show the Editor/Inspector with three distinct type weights, grouped sections, and layered depth — and the CI contrast contract is green on all 7 themes.
2. **Coherence proven (end P3):** no tab clips at any window width; the tab strip means one thing (task workspaces); Import's simple-fork path is the default and Ctrl-K reaches everything hidden.
3. **Newcomer proven (end P4):** a fresh-install user opens a running sample room and looks up "walkmesh" in-app, both within the first ~10 minutes, without touching an engine-param form — while an expert flips to Full/Compact and loses nothing.

## 7. Scope guardrails

**Explicitly NOT touched (fence so effort isn't misspent):**
- **The ~29 `world-*` overworld commands** (custom continents/coast/entrances) — the single largest CLI-only pillar, *zero* GUI. Building windows for them is net-new feature work, a different project. Report E-§5.
- **`audio-import`, `image-field`, FMV pipeline, the Overload `[difficulty]`/`[rebalance]`/`[deathrules]` and `[chocobo]` TOML blocks, and a character-creation wizard** — CLI-only or hand-edit-only today; form-coverage gaps, not visual-makeover items. Report E-§5.
- **The engine (Memoria DLL, `.eb` format, fork gates), and any new pillar features.** This is a VISUAL/COHESION/LEARNABILITY pass on the ~83 already-surfaced commands.

**Constraints to honor:**
- **CLI-second rule** — the GUI wraps proven CLI flows; don't invent behavior the CLI lacks.
- **PySide6 + Fusion required** — Fusion stays mandatory (it's why QSS colors take); don't mix QPalette and QSS coloring on the same widgets.
- **Keep the tk-free-backend / QSS-from-tokens architecture** — theme/style remain headless-testable; the parity + contrast tests stay the compile-time guarantee.
- **Don't break `--smoke`** — the smoke harness and the offscreen screenshot harness must keep passing every phase.
- **Don't regress power-user speed** — F9/F6 one-keystroke loop, Ctrl-K reach, and Compact density must survive every simplification.

## 8. Open questions for the user

1. **Bundle a custom font?** Report I recommends shipping Inter (UI) + JetBrains Mono/Cascadia (OFL/MIT, redistribution-clean) for identical cross-machine rendering and guaranteed tabular figures for the many ids/coords — vs. staying on system Segoe UI (Fluent-native on Windows, zero packaging risk). Given the existing Qt-LGPL/packaging caution, which way?
2. **Beginner/Advanced mode: global toggle, or per-form disclosure only?** A global Guided/Full mode is the strongest accessibility lever but is new machinery the codebase has deliberately avoided ("NO tab-level hiding anywhere"). Do you want the global mode, or just per-form Advanced accordions (lower risk, less dramatic)?
3. **Interactive tutorial vs. rich samples + empty states?** The "fork → deploy → F6" coach-marked walkthrough is highest-impact but highest-effort (and risks the tour anti-patterns). The sample-gallery + teaching-empty-states path is ~80% of the value at ~20% of the cost. Ship the cheap path first and defer the walkthrough, or invest in the full walkthrough now?
4. **How far to reorganize the 10 tabs?** Option A (task-workspace rail, reparent-only, reversible) vs. the more ambitious Option C (tabs = *only* the open project; the five mini-apps become a Tools launcher). A is safer; C is more conceptually correct but higher-churn. How much re-learning are you willing to ask of existing users?
5. **Real SVG icon set vs. refined monochrome glyphs?** A licensed SVG set (Lucide/Feather/Fluent) is the accessibility- and DPI-correct answer and unifies tabs/tree/breadcrumb — but adds an asset dependency. Acceptable, or prefer to stay glyph-only (cheaper, but can't tint uniformly or survive high-contrast mode)?
6. **Density default:** ship **Comfortable** as the default (newcomer-friendly, more whitespace) with Compact opt-in for experts — or keep today's dense default and make Comfortable the opt-in? This sets the app's first impression.