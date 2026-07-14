<!--
Dream World IX — Workspace GUI makeover: phased research plan.
Produced 2026-07-14 via a 12-agent research workflow (5 GUI audits with offscreen
screenshots + 4 web best-practice streams -> synthesize -> adversarial critique -> revise).
Every quantified claim below was spot-verified against the code (e.g. the 136 inline
setStyleSheet count + per-file breakdown, `* { outline: 0 }` at style.py:16, the
`[300,640,240]` splitter at shell.py:995). Supporting reports live in ./research/.
NOTE: overlapping text seen in the offscreen Home/breadcrumb renders is a KNOWN harness
artifact (deleteLater labels paint over successors under nested processEvents), NOT an
app bug -- the plan guards against it with a repaint-regression check, it does not "fix" it.
-->

# The Workspace Makeover — Final Phased Plan

> **Progress — Phase 0 landed (2026-07-14, offline-verified, committed `82ed086`).** Files: `workspace/style.py`,
> `workspace/shell.py`, `workspace/battledoc.py`, `tests/test_workspace_prefs.py`. **Done:** Info Hub demoted
> to a violet OUTLINE so Deploy is the only saturated fill; toolbar grouped with separators (Edit · Validate ·
> Info); the empty console COLLAPSES by default (any job re-expands it, and restore is now faithful in BOTH
> directions — fixed a real regression where a returning user's open console would collapse, since prefs only
> persists the collapsed flag; +2 new tests); Battle's dead action column hidden until a battle loads and its
> two competing empty-state sentences merged into one; the lone 🧍 color emoji → a monochrome ▦; a restored
> keyboard focus ring (per-widget `:focus`, WCAG 2.4.7); Deploy-button reassurance tooltip (reversible +
> what F6 does); the Home intro de-circularized (points a newcomer at Field first). **Verified:** smoke green,
> 260 workspace/battle tests pass, offscreen screenshots reviewed. **Deferred from P0, with cause:** the
> network-consent-modal retiming (consent-sensitive AND a no-op on source checkouts → untestable here); the
> systematic light-theme `muted` contrast retune (belongs to Phase 1's contrast-floor raise); the Map legend
> chip (minor). **6 decisions locked** (see §8).

> **Progress — Phase 1 landed (2026-07-14, offline-verified).** The token & component foundation, built to be
> visually INERT. Files: `editor/theme.py`, `workspace/style.py`, `workspace/widgets.py`, `workspace/modelsdoc.py`,
> `tests/test_editor_theme.py`, `tests/test_workspace_style.py`, `tests/test_workspace_widgets.py` (new). **Done:**
> a pure idempotent `theme.derive(base)` adds the semantic tokens (elevation ladder `surface_2/3`, tinted
> `selection_bg`, `text_subtle`, a `focus` token guaranteed ≥3:1 on the surface, `info`) — all `#rrggbb` so the
> hex/parity guarantees hold; spacing/radius/type scales + a `MOTION` const threaded into the QSS via
> `qss()=substitute({**_SCALES, **derive(pal)})`; component role classes (`QLabel[role=…]`, `QFrame[role=card]`,
> chip) + `workspace.widgets` factories (`heading`/`caption`/`card`/`status_chip`) with `setAccessibleName` baked
> in, plus a `tabular()` tnum helper; the P0 focus ring rewired from `$accent` to the `$focus` token (fixes nord's
> sub-3:1 ring); the ghost `panel` token cleaned. **Contrast floors RAISED to 4.5 text / 4.5 muted (bg AND
> surface) / 3.0 accent-fg / 3.0 focus — all 7 themes now pass** (retuned `muted` on light/nord/dracula/
> solarized-dark/-light + solarized-light `text`), which **resolves the light-theme contrast item deferred from
> P0**. **Verified:** smoke green, 320 tests pass, screenshots show zero structural change (light/dark/nord
> identical, sub-perceptible muted nudge). **Deviation from the plan, with cause:** did NOT remove `theme.apply_theme`
> — the research agent assumed it dead, but `editor/app.py`, `dialogs.py`, and `graphview.py` still use it. The
> component-token *application* app-wide (retiring the 136 inline styles) is Phase 2.

> **Progress — Phase 2 IN PROGRESS (De-smush A — the XL inline-style sweep, one file per commit).** The
> token/component system REPLACES ad-hoc inline styles, file by file, each with a before/after screenshot check.
> Per-file `setStyleSheet` tally:
> - ✅ **`forms_qt.py` 12→5** — the field-editor forms (`build_form` + wrap-preview): caption/label/error-hint
>   inline styles → `caption`/`label` roles + a `state='error'` property (repolished, QSS-coloured, no inline) +
>   4pt row rhythm (vspacing 10→12, field→hint 2→4). Faithful (the form renders identically) + a red-error unit
>   test. The 5 remaining are the Info Hub **dialog** styles (detail/prose/count/help) — deferred to a
>   headless-verifiable pass. New: style roles `label` + `caption[state=error|warn]`; `widgets.repolish()`.
> - ✅ **`builddoc.py` 7→0** — the Build & Deploy jargon wall: all 7 hints → `muted`/`accent`/`caption` roles
>   (the New-Game jargon paragraph recedes to a smaller caption); page rhythm 10→12/margins 16. **The ELEVATION
>   LADDER landed here, globally**: `QGroupBox` now fills with `surface_2` so panels read as RAISED cards (a net
>   win across every group-boxed doc — verified in Build & Deploy AND Import). Learning: a 12px side-padding on
>   the panel pushed Build's long non-wrapping New-Game radio into a horizontal scroll → dropped to padding-top
>   only (the >60-char radio label itself is a Phase-6 New-Game-fencing content fix, not styling).
> - ✅ **`importdoc.py` 23→1** — the "four jobs in one scroll." Census found all 22 muted labels are wrapped
>   EXPLANATORY paragraphs (none a tight field label), so all → the smaller `caption` role uniformly: the wall
>   of muted text RECEDES and the controls (inputs/buttons/radios) stand out — real hierarchy. Page rhythm
>   10→12/margins 16; the elevation ladder (already global) lifts its 6 panels + the nested Fork-mode box. Only
>   the 1 dynamic mode-chip (`Will fork: VERBATIM/RE-AUTHORABLE`, live accent/warn colour) stays inline. Removed
>   3 now-unused `muted` locals. Verified before/after (controls pop, no h-scroll).
> - ⬜ `shell.py` 60 · `battledoc.py` 11 · `modelsdoc.py` 9 · `savedoc.py` 8 — pending.
> New roles: `muted`, `accent`. Verified: smoke green, 268–301 workspace/style/theme/battle tests pass per round.


## 1. North-star vision

The made-over Workspace feels like **one calm, confident instrument** — a coherent creative IDE where a newcomer opens a working FF9 room in their first five minutes and an expert still deploy-and-tests on a single keystroke. Surfaces breathe (a real spacing rhythm, a legible type hierarchy, layered depth instead of one flat grey plane), color *means something* (accent = the one thing to do next; status hues = status only), every intimidating word — journey, fork, walkmesh, gEventGlobal — is teachable in place the moment you meet it, and the window always answers three questions at once: **where am I, what is this word, and what do I do next.**

The central tension is **power-density vs. approachability.** This app fronts ~112 CLI commands across ~36 pillars; **~83 are surfaced in the GUI today**, the rest (world-*, audio, image-field, FMV) are the fenced CLI-only backlog (§7). That compression is real. The resolution principle every mature tool converges on: **a fast hidden lane for experts (Ctrl-K, F9/F6, keyboard everywhere) is what earns the right to make the *visible* lane calm.** We don't dumb the tool down; we disclose it progressively, teach it in context, give it a workflow spine, and dress it in one coherent visual system — so the same window serves the frightened first-timer and the byte-level power user without either feeling it was built for the other.

## 2. Design principles

1. **Progressive disclosure by default.** Basics visible; expert controls (`mesID`, `gEventGlobal` band, `scenario`, donor offsets, fork modes, `B_MEMBER` selectors) one deliberate step away — never on the front surface. Two tiers max. Applies to *both* the generated Editor forms (via `forms_qt.build_form` accordions) *and* the hand-built dense docs (Import/Build/Battle/Save), which the form builder cannot reach and which need their own per-doc drawers.
2. **Teach in context, in plain language.** Define a term where it first appears; plain label on the surface, engine term in the tooltip ("Story flag" on the label, "gEventGlobal — save-persistent" on hover). Additive teaching hides nothing, so it ships early.
3. **One coherent visual system.** Every color, size, space, radius, and motion value comes from named tokens — not the **136 inline `setStyleSheet` calls** (verified: 144 total − 8 `.pyc`) and ~15 ad-hoc spacing values live today. Evolve `theme.py`/`style.py`; don't rewrite them.
4. **Never punish the expert.** Anything simplified stays reachable in ≤2 clicks via Ctrl-K; the F9/F6 loop stays one keystroke; a "Full/Advanced" affordance is always one click away; nothing is *removed*, only *deferred*.
5. **Color means something.** One restrained accent for the single primary action + focus + active state; `success/warn/error/info` reserved strictly for status; never status-by-color-alone (icon + text).
6. **Reversible & safe, and say so.** Surface the existing backup/revert story in plain words where nerves peak ("Deploys are reversible — your game is backed up first").
7. **Accessibility is a floor, not a finish — so it's built in, not bolted on.** `setAccessibleName`, focus rings, target size, and color-independence land *as controls are touched* in every phase; the dedicated a11y phase is audit + verification + custom-canvas cases, not the first time a screen reader gets a label.
8. **Honor the tree as the one mental model, and give it a workflow.** journey▸campaign▸field▸object is the spine users learn once; the breadcrumb, Map, Ctrl-K, and a new **mode-aware next-action strip** all reinforce it.

## 3. The three problems, evidenced

### SMUSHED TEXT
Quantified, not asserted. **`muted` hint text fails WCAG AA 4.5:1 on 5 of 7 themes** (Report I: nord 4.04/3.71, solarized-dark 4.02/3.48, solarized-light, light 4.46) — the "grey hint you can barely read." Spacing lives off-grid: toolbar `spacing:6px; padding:5px 8px` (`style.py:22`), separator `margin:5px 4px` (`:23`), button `padding:6px 10px` (`:26`), checkbox `spacing:7px` (`:57`), indicator `15px` (`:59`), tree items `padding:5px 4px` (`:91`), GroupBox `margin-top:10; padding-top:8` (`:107`) — values of 5/6/7/9/10 on no grid. Forms stack identical rows in one flat column with label, field, and hint all at ~11–13px similar weight, so "6 fields read as one gray brick." The one caption role is hand-reinvented: **the idiom `color:{muted};font-size:11px` recurs 15× verbatim**, part of the 136 inline styles.

### DENSE REGIONS
The **Import tab is one `QScrollArea` stacking ~8–10 GroupBoxes** fusing four unrelated jobs (fork one field / fork a region / browse catalog / bulk archive) plus repaint-native — 68 widget instantiations, 23 inline styles, the heaviest surface in the app (`importdoc.py:50`). **Build & Deploy shows six co-equal panels** regardless of context, including the New-Game single-owner footgun visually equal to routine Build (`builddoc.py:113-249`). **Battle** carries a donor-site offset picker and a donor-AI `B_MEMBER` table at full byte-level density (11 inline styles), plus a dead action column and two competing empty-state sentences with nothing loaded. **Save editors nest Inspect/Diff/Edit sub-tabs inside the tab** (`savedoc.py`, 8 inline styles). Story State / Item & Equip fill the central pane with a **black console void.** Crucially, the density offenders are **hand-built doc modules, not `forms_qt`-generated forms** — so a single form-level accordion mechanism structurally cannot fix them; each needs its own disclosure work.

### UNCLEAR COHESION
Structural root cause: **the 10-tab strip carries three incompatible axes on one row** — a landing page (Home), views of the open project (Editor, Map), orthogonal save-file editors (Story State, Item & Equip), and five self-contained mini-apps (Battle, Models, Build, Import, Co-op — the last doesn't even read the open project). A tab strip implies "different views of one subject"; here tab 1 and tab 8 share nothing. Worse, **the strip is confined to the 640px middle splitter pane** (`shell.py:995`, sizes `[300,640,240]`) and can never widen, so ~half the tabs clip into scroll chevrons at default size — Import and Co-op hide entirely (`shell.py:965`). Visually it's **one flat grey plane**: toolbar, tree, tabs, form, inspector, console share 2–3 near-identical dark surfaces separated only by 1px hairlines at ~1.3:1 contrast (below the 3:1 WCAG floor for a control edge). The single accent is spent on the **wrong thing**: the violet Info Hub button is the only saturated element, implying a reference catalog is the primary action, while Deploy — the button that ships work — is a tiny un-accented dark button that nearly vanishes in light theme. And the deepest gap the reports name (Report C-F10, G-P10, H-stage-4): **five panels with five subjects and no unifying "you are working on ___, here's the flow" spine** — the app answers "where am I" (the breadcrumb chip, already shipped) but never **"what's my next step."**

### The newcomer-accessibility gap
There is **no first-run experience, no sample-project loader, and no in-app link to the on-disk docs** (`docs/GLOSSARY.md`, `docs/tutorials/`). The first modal a bundled user sees is a network-privacy consent dialog before they know what the app is (`shell.py:478`). The conceptual onboarding is **one circular sentence** using four undefined nouns (`shell.py:1173`). The recommended first action ("Journey ▸ Open") points at the *deepest* abstraction; the first creative action (New Field) demands "Area (≥10)" and "Camera pitch" a non-modder can't answer. Domain vocabulary (journey, campaign, field, fork/verbatim/native, walkmesh, gEventGlobal, gateway, encounter, mesID, FBG, Memoria, F6, deploy, scenario) is never taught at first contact; the one place it's done well (Info Hub's `_HUB_HELP` "?") covers only catalog kinds, not app structure. Accessibility has two one-line-visible holes: **zero `setAccessibleName` anywhere** (total screen-reader blindness) and a global **`* { outline: 0; }`** (`style.py:16`) that kills the focus ring on every non-input control — a flat WCAG 2.4.7 fail.

## 4. Cross-cutting foundations

Five substrates the later phases consume; the first two are built before any broad application.

### (a) Design token system — *evolution of the existing dict→QSS pipeline.*
The app already generates one QSS string from a flat 22-key palette via `string.Template` — the right substrate, but it stops at a hand-authored semantic layer with no primitives, no scales, and one overloaded surface tier.
- **A pure `derive(base) -> tokens` function** in `theme.py` (tk-free, testable) computing, per theme, an **elevation ladder** (`surface_1` page / `surface_2` tree+inspector ≈ +4% tint / `surface_3` cards+menus ≈ +8% tint, via Material-3 tint-on-tint since QSS has no `box-shadow`), a **subtle `selection_bg` = accent @ ~14% alpha** (replacing full-saturation tree selection), a third text tier `text_subtle`, plus `focus`, `info`, `scrim`, disabled states — from a *smaller* hand-authored base per theme. A ~15-line `mix(a,b,t)` + `rgba(hex,a)` helper is all the color math (precomputed in Python; QSS has no `color-mix`).
- **Theme-independent scales** threaded through both the QSS template *and* the Qt layout calls (`setContentsMargins`/`setSpacing`): spacing `0/4/8/12/16/24/32/48`; radius `sm=4 / md=6 / lg=8 / pill`; type ramp `display 24/600 · h1 20/600 · h2 16/600 · label 13/500 · body 13/400 · caption 11/500 · mono 12/400` with line-heights on the 4px grid; motion `fast 120–160ms · medium 200–240ms` + standard easing `cubic-bezier(0.2,0,0,1)`.
- **A component layer** (`QLabel[role="caption"|"h1"|"h2"]`, a real `Card`, `StatusChip`, `HelpBadge`) that kills the 136 inline styles, folds `setAccessibleName` into the factory, and as a side effect fixes the retheme-staleness bug (`shell.py:449`) and the ghost `panel` token (`modelsdoc.py:120`).

### (b) IA / navigation reorganization.
Regroup the 10 flat tabs into ~5 task workspaces (Blender/DaVinci model) and fix the geometry (§ Phase 6 picks one target). Group by intent: **Author** (Editor, Map) · **Assets** (Import, Models, Battle) · **State** (Story State, Item & Equip — fenced as the orthogonal save layer) · **Ship** (Build & Deploy, Co-op) · **Learn/Home**. Strengthen Ctrl-K into a verb-first, category-prefixed command palette — the escape hatch that makes simplification safe.

### (c) Learnability layer — *additive teaching ships early; hiding waits.*
A first-run → first-success → in-context-help → concept-scaffolding → exploration ladder, each reusing an existing surface. The **additive half** (sample gallery, teaching empty-states, concept-card registry + "?" affordances, reassurance microcopy, plain-language error rewriting) hides nothing, needs no reorg, and lands in early phases. Only the **global Guided/Full HIDING mode** waits for the reorg + palette (you must be able to reach hidden things before you hide them).

### (d) The cohesion spine — the missing answer to "what do I do next."
A modest, collapsible **mode-aware next-action strip** driven by state the shell already tracks (`shell.py:369-376`) — presentation, not new logic. Examples: EMPTY → "Fork a room · Open a project"; loose-field-unsaved → "Save · Deploy (F9) · Playtest (F6)"; deploy-succeeded → "Reload field (F6) · Warp to it". This is Report C's Option D, named there *"the north-star for cohesion."*

### (e) Accessibility baseline — built in, verified last.
WCAG 2.2 AA on contrast/focus/target-size/color-independence across all 7 themes + basic screen-reader labelling. Replace `* { outline:0 }` with per-widget `:focus` rings (Phase 0); raise the contrast-test floors from 4.0/2.7/3.0 to **4.5 text / 3.0 border+status / 3.0 focus** and retune the named failing tokens (Phase 1); fold `setAccessibleName` into the component factory and every touched control (Phases 1–6); enable **tabular figures** (`tnum` via `QFont::setFeature`, Qt 6.7+) on all id/coord/offset text independent of any font-bundling decision (Phase 2/3); audit 15px indicators to a 24px hit target; the dedicated phase (9) is the audit + custom-canvas cases.

## 5. The phased plan

Ordered so foundations land first and each phase ships visible value. The offscreen-screenshot harness (`WA_DontShowOnScreen` + `grab()`) makes most success criteria screenshot-verifiable; the QSS-from-dict architecture keeps theme/token work headless-testable. **Every phase that changes mount/repaint (2, 3, 6) adds "no offscreen-harness repaint regressions" as an explicit check** (Report A documented a re-mount repaint artifact). **Phases 4 and 5 (additive learnability) have no dependency on the reorg and may run in parallel with 2–3** once Phase 1 components exist.

---

### Phase 0 — Quick wins, safety net & reassurance copy
- **Goal:** immediate visible relief + a11y floor + plain-language reassurance, no architecture change.
- **Scope (in):** re-rank toolbar color so **Deploy is the accent** and Info Hub demotes to a violet-outline button; group the toolbar with separators (Open · Edit · Validate · Ship · Info); collapse the empty console dock by default (`_toggle_console` exists); merge Battle's two empty-state messages and hide its dead action column until a battle loads; unify the lone 🧍 emoji to a monochrome glyph; fix light-theme Deploy/console contrast; **restore the focus ring** (delete `* { outline:0 }` at `style.py:16`, add per-widget `:focus`); **reassurance microcopy** — a one-liner near F9 ("Deploys are reversible; your game is backed up first") and a "what is F6?" tooltip; **Home prose trim** (the circular sentence at `shell.py:1173`) and a **Map legend chip**; defer the network-consent modal (`shell.py:478`) out of the cold-launch path. **(out):** token system, tab reorg, onboarding flows.
- **Deliverables:** Report A "Quick Wins" + Report I priority #1 (focus) + Report G8/D-§2 microcopy.
- **Dependencies:** none. **Effort:** S.
- **Risks:** focus-ring reflow → pad-compensate the 2px border; toolbar regroup muscle-memory → keep all actions, only add separators.
- **Success criteria (screenshot-verifiable):** Deploy is the single accent in both light+dark; Tab-key walkthrough shows a visible ring on buttons/tabs/tree; console dock absent on cold start; Battle empty state = one message, no dead buttons; consent modal does not appear before Home renders.

### Phase 1 — Token & component foundation (the substrate, visually inert)
- **Goal:** insert `derive()` + scales + component classes + a11y hooks with **no visual change yet.**
- **Scope (in):** the `derive(base)->tokens` color function (elevation ladder, `selection_bg` tint, `text_subtle`, focus/info/scrim/disabled); the spacing/radius/type/motion scale dicts substituted into the QSS template; QSS role classes (`QLabel[role]`, `Card`, `StatusChip`, `HelpBadge`) with `setAccessibleName` baked into each factory; extend the theme-parity test to the derived set; **raise contrast-test floors to 4.5/3.0/3.0 and retune the named failing tokens** (nord, solarized-dark/-light, light `muted`); remove dead ttk styling (`theme.py:264-269` tkinter font reconfig) and the ghost `panel` token; enable `tnum` on the mono/data font role. **(out):** applying tokens app-wide (Phase 2), icons, motion.
- **Deliverables:** the token architecture (Reports F-§1, B-§4); a green contrast CI contract across 7 themes.
- **Dependencies:** Phase 0. **Effort:** M.
- **Risks:** hand-authored palettes drift from derived → keep the 7 bases small, derive the rest; contrast retune shifts brand feel → tune base hues, not the derivation.
- **Success criteria:** all 7 themes pass 4.5 text / 3.0 border+status / 3.0 focus (test); token dict complete for every theme; component factory emits `accessibleName`; **no pixel change in screenshots yet** (proves the substrate is inert until applied).

### Phase 2 — De-smush A: the inline-style migration + spacing/type/elevation sweep (XL)
- **Goal:** the core visual step-change — replace the flat grey plane and cramped forms with rhythm, hierarchy, and depth. *This is the highest-regression-risk phase; it is scoped alone.*
- **Scope (in):** mechanically replace the **136 inline `setStyleSheet` calls with `setProperty("role",…)`/component factories, file by file** (`shell.py` 60 sites → `importdoc.py` 23 → `forms_qt.py` 12 → `battledoc.py` 11 → `modelsdoc.py` 9 → `savedoc.py` 8 → `builddoc.py` 7 → dialogs); apply the 4pt spacing scale to every layout (label→field 4, field→field 12, section→section 24, input padding →`8px 10px`, tree rows →`6px 8px`, GroupBox margins onto the grid); apply the type ramp (label 13/500 ≠ value 13/400 ≠ caption 11/500); apply the elevation ladder (`surface_1` page < `surface_2` tree/inspector < `surface_3` cards/menus/palette). Continue folding `setAccessibleName` onto each control as it's touched; apply `tnum` to id/coord/offset labels. **(out):** inspector/empty-state redesign (Phase 3), IA reorg, icons, motion.
- **Deliverables:** the 136-site migration (Report B step #3) + Reports I-§2/§3 spacing/type + A-elevation. **The 136-site sweep is its own screenshot-diffed sub-milestone**, done per-file.
- **Dependencies:** Phase 1. **Effort:** XL.
- **Risks:** 136-site regressions → per-file screenshot diffs, one file per commit; retheme staleness → the component layer eliminates the hand-maintained re-tint list; repaint artifact → add the harness repaint-regression check.
- **Success criteria:** grep shows **zero `color:{muted};font-size:11px` inline strings and zero raw `setStyleSheet` in the 8 named files**; before/after screenshots of Editor/Cutscene show three distinct type weights and grid-spaced rows; regions read as layered (measurable surface-tint deltas between page/tree/card); no repaint regressions in the harness.

### Phase 3 — De-smush B: surfaces (inspector, empty-states, density)
- **Goal:** finish the visual quality pass on the composite surfaces the sweep didn't restructure.
- **Scope (in):** redesign the **Inspector as a grouped data card** (Identity / Contents / Connections) with `role`-styled sections; replace black-void and competing-sentence empty states across tree/Map/Story State/Item & Equip/Battle/Problems with **icon + one-line purpose + a primary action + (where apt) a teaching sentence** — the empty-state system is authored once here so teaching empty-states cost nothing extra; a **density toggle** (Comfortable / Compact) via two QSS-var sets, defaulting to whatever Open Q6 resolves *before* this phase builds it; a real `QGraphicsDropShadowEffect` on floating layers only (menus, Ctrl-K, dialogs), applied to a transparent wrapper (not the rounded widget). **(out):** IA reorg, onboarding, icons, per-doc disclosure.
- **Deliverables:** Reports A-Structural (inspector, empty-states) + H teaching empty-states + the density lever.
- **Dependencies:** Phase 2. **Effort:** L.
- **Risks:** drop-shadow corner-bleed → shadow a transparent wrapper (Report F-§2); density toggle churn → build only the resolved default + one opt-in set.
- **Success criteria:** Inspector shows three labelled sections instead of a flat list (screenshot); every empty state = icon + purpose line + action, no black void, no double sentence; density toggle visibly re-rhythms tree/form rows; no repaint regressions.

### Phase 4 — Learnability, additive part 1: first-run, sample gallery, "Try it now"
- **Goal:** convert the first 10 minutes from "read a paragraph, fail a form, find a diagnostics panel" into "get set up in order, open a working example, poke a safe sandbox." *No hiding; parallelizable with 2–3.*
- **Scope (in):** a **3-step guided first-run** that *sequences* the existing `SetupHealthDialog` actions (locate game → extract templates → open a sample / make first field) and ends on a creative action, with the consent modal deferred to after it; a **"Learn by example" Home section** opening read-only copies of the bundled `examples/` (vivi-hut, stolen-ember, thirteenth-character) into tree+Editor with **no engine-param dialog**; a **"Try it now" safe-sandbox framing** of the existing 4003/F6 loop (Report G-P11); a **"just get me started" default setup path** deferring id-band/mod-folder choices to sane defaults (Report G-P8). **(out):** concept cards, error layer, hiding mode.
- **Deliverables:** Reports D-§4 (first-run, samples), G-P8/P11, H stages 0–1.
- **Dependencies:** Phase 1 (components). **Effort:** M.
- **Risks:** blank-canvas trap → samples ship before any hiding toggle; setup friction → the default path removes required choices.
- **Success criteria (screenshot-checkable half):** cold-launch Home shows the sample gallery + a getting-started checklist; clicking a sample opens it read-only in tree+Editor with no engine-param dialog. **(human-playtest gate):** a fresh-install user reaches a running sample within ~10 minutes without touching a param form.

### Phase 5 — Learnability, additive part 2: concept cards, "?"/What's-This, plain-language errors
- **Goal:** make every intimidating word answerable in place, and every failure legible.
- **Scope (in):** a **concept-card registry** extending `_KIND_HELP`/`_HUB_HELP`, one card per §3 vocabulary term (journey, campaign, field, fork/verbatim/native/editable, walkmesh, gEventGlobal/story-flag, gateway, encounter, mesID, FBG, Memoria, F6, deploy, scenario), surfaced via `setWhatsThis` + a collapsible Inspector **"About this…"** panel + a **"?" affordance on jargon labels** (a `forms.Field.concept` key) + Ctrl-K concept matching; the **plain-language error layer (4g)** — a rewriting pass in `feedback.py` that maps raw CLI/engine errors to human sentences + a next step, **surfaced through the existing bottom Problems dock via `setStatusTip`** (its own M-effort deliverable, its own criterion). **(out):** the concept *map* (Phase 7), hiding mode.
- **Deliverables:** Reports D-§2, G-P7/G7, H stages 2–3.
- **Dependencies:** Phase 1 (components); Phase 3 (Inspector card) for the "About this…" host. **Effort:** L.
- **Risks:** tooltip fatigue (82% dismissed <1.2s) → depth lives in What's-This/Inspector, not more tooltips; registry drift → one source-of-truth dict, parity-tested against the vocabulary list.
- **Success criteria:** every term in the §3 vocabulary list resolves to a plain-language card in ≤2 interactions (test enumerates the registry); a deliberately-broken build shows a rewritten one-sentence error + a next step in the Problems dock (not a raw stack).

### Phase 6 — IA / navigation reorg: rail + strip geometry + Ctrl-K palette
- **Goal:** an honest spatial metaphor and the expert escape hatch that makes hiding safe.
- **Scope (in):** **pick one target geometry — a workspace rail that *swaps* the tab set** (Author/Assets/State/Ship/Learn), never showing all 10 tabs, which kills the 640px overflow *without* fighting the central `[300,640,240]` splitter (Report C's cleaner fix; the tree stays left, inspector stays right, only the middle tab set swaps). State this explicitly and treat the central-layout touch as its own risk line. Split Import's four fused jobs (fork-one-field foregrounded; region/archive/repaint behind disclosure); collapse Build & Deploy's six panels into a guided deploy + an "advanced" drawer (New-Game fenced out of the routine path); promote **Ctrl-K to verb-first names + category prefixes + keybinding hints**. **(out):** per-doc Battle/Save disclosure (Phase 7), the CLI-only backlog (§7).
- **Deliverables:** Reports C-§3 (rail option), E top-two reorg targets, G-P1/P2.
- **Dependencies:** Phases 2–3 (workspaces need the card/elevation/empty-state vocabulary). **Effort:** L.
- **Risks:** users relearn tab locations → every "Go to X" stays in Ctrl-K + a one-time callout; `QTabBar` can't render separators → the rail is a segmented control above the tabs; central-splitter regressions → screenshot-diff + repaint check.
- **Success criteria:** at 1280px **no tab clips into a chevron** (screenshot); the rail swaps tab sets and the tree/inspector are unmoved; Import default view shows only the simple-fork path; **Ctrl-K surfaces every tab as a verb-first, category-prefixed command with a keybinding hint** (a Phase-6-owned deliverable — not the concept card, which lives in Phase 5); deploy reachable via F9 + palette + one visible button.

### Phase 7 — Cohesion spine + per-doc disclosure + (conditional) global Guided/Full mode
- **Goal:** answer "what do I do next," and finish disclosure on the hand-built dense docs the form builder can't reach.
- **Scope (in):** the **mode-aware next-action strip** (§4d) — a collapsible row driven by `shell.py:369-376` state (EMPTY / project-open / loose-field-unsaved / deploy-succeeded), one primary + ≤2 secondary actions each; **per-doc disclosure** for the surfaces `forms_qt` cannot touch — a Battle **Advanced drawer** hiding the donor-site offset picker + `B_MEMBER` table until asked, and a Save **flatten/fence** of the nested Inspect/Diff/Edit sub-tabs; a **"How it all fits" concept map** reusing `editor/graphview`; **the global Guided/Full mode is built here only if Open Q2 approves it** (it is not scoped-in by default — it is new machinery the codebase has deliberately avoided) — if approved, per-form Advanced accordions + a one-click Full restore, nothing removed. **(out):** icons, motion.
- **Deliverables:** Reports C-Option D, G-P10, H-stage-4 (spine); E#3/E#4 (per-doc disclosure); D-§4 (concept map); conditionally the global mode.
- **Dependencies:** Phase 6 (Ctrl-K must exist before hiding; the spine reinforces the reorganized surfaces). **Effort:** L.
- **Risks:** "kiddie mode" feel → Full is one click, nothing removed; spine noise → collapsible, ≤3 actions, muted styling; per-doc disclosure regressions → screenshot-diff each doc.
- **Success criteria:** the next-action strip shows the correct primary action in each of the 4 states (screenshot per state); Battle's advanced pickers are hidden by default and one click restores them; Save shows no nested sub-tabs; if built, Guided mode hides `mesID`/`scenario`/`gEventGlobal` fields and Full restores every one.

### Phase 8 — Iconography
- **Goal:** one visual language across rail, tree, breadcrumb, cards, toolbar.
- **Scope (in):** replace unicode/emoji/mojibake glyphs with a monochrome SVG set (Lucide/Feather/Fluent, OSS-licensed — pending Open Q5) via `QIcon`+`QtSvg`, tinted from `text_secondary`/`accent`; add icons to the workspace rail, tree nodes, breadcrumb; grid-align at 16/20/24; pair every icon with a label or `setAccessibleName`. **(out):** custom illustration; motion.
- **Dependencies:** Phase 1 (tint tokens), Phase 6 (rail structure). **Effort:** M.
- **Risks:** DPI crispness → SVG only; license → OFL/MIT/ISC sets; high-contrast mode → SVG (not icon-font) survives.
- **Success criteria:** grep shows zero emoji/mojibake in the UI; rail+tree+breadcrumb share one glyph family; icons re-tint correctly across all 7 themes (screenshot matrix).

### Phase 9 — Accessibility hardening & verification across all 7 themes
- **Goal:** provable WCAG 2.2 AA everywhere + screen-reader verification (the *audit*, since labelling was built in from Phase 1).
- **Scope (in):** verify `setAccessibleName`/`Description` coverage on every actionable control and fill gaps; target-size audit (24×24 min, pad buttons not glyphs; the 15px indicators from `style.py:59`); status = icon+text not color-alone in Problems/lint/Check; focus-not-obscured on scroll; **200%-zoom / font-scaling survival** (the 1280-tuned toolbar at `style.py:20` is the risk); custom-canvas accessibility for tree/graph/map. **(out):** deep `QAccessibleInterface` trees beyond the canvases (stretch).
- **Dependencies:** Phases 1–3 (focus/contrast), 8 (icons carry status shapes). **Effort:** M.
- **Risks:** toolbar clipping at 150% → verify against the "must FIT at 1280px" note; custom-widget SR coverage → `setAccessibleName` suffices for common cases.
- **Success criteria:** the AA contrast/focus/target/color-independence checklist passes on all 7 themes (test); NVDA/Narrator read meaningful names for toolbar + rail + tabs + tree; UI legible at 200% with no truncation.

### Phase 10 — Polish & motion pass
- **Goal:** the final "premium, intentional" layer.
- **Scope (in):** 2–3 sanctioned `QPropertyAnimation` uses only — 120–160ms tab/panel cross-fade, focus-ring ease, panel expand/collapse (`maximumHeight`), Ctrl-K palette fade+slide; status as pills not colored text; dividers+whitespace over nested GroupBox outlines; loading states (indeterminate progress/skeleton) on long `jobs.py` work; all motion gated behind an OS reduced-motion probe + in-app toggle, kept in one `anim.py`. **(out):** animating everything.
- **Dependencies:** all prior. **Effort:** M.
- **Risks:** motion sprawl → 2–3 helpers, one file; WCAG 2.3.3 → ≤200ms, disable-able, jump-to-end on reduced-motion.
- **Success criteria:** tab switches and palette open animate ≤160ms; reduced-motion toggle produces instant end-states; no frozen panel during a build (progress visible).

## 6. Sequencing & milestones

**Order and rationale:**
- **P0 first** — cheap visible relief + the one-file WCAG focus fix + reassurance copy; buys goodwill, de-risks.
- **P1 before P2** — you can't apply tokens you haven't defined; keeping P1 visually inert proves the substrate is safe.
- **P2 alone (XL)** — the 136-site sweep is the single riskiest change; isolate it with per-file screenshot diffs.
- **P3 after P2** — inspector/empty-state/density need the card+elevation vocabulary.
- **P4/P5 parallel to P2–P3** — additive teaching hides nothing and needs only Phase-1 components; the brief's primary ask does **not** wait for the reorg.
- **P6 before P7** — the escape hatch (Ctrl-K) and honest metaphor must exist before any hiding.
- **P7** — the cohesion spine + per-doc disclosure + conditional global mode.
- **P8/P9 after structure settles** — icons carry status shapes; a11y hardening wants the final focus token, icons, and layout.
- **P10 last** — motion is the garnish.

**Milestones — "you can tell it worked when…":**
1. **De-smush proven (end P3):** side-by-side screenshots show Editor/Inspector with three distinct type weights, grid-spaced grouped sections, and layered depth; the CI contrast contract is green on all 7 themes; grep shows zero inline `setStyleSheet` in the 8 named files.
2. **Newcomer proven (end P5, ahead of the reorg):** cold-launch shows the sample gallery + checklist; a sample opens read-only with no param dialog; every §3 term resolves to a plain-language card in ≤2 interactions; a broken build shows a rewritten error — while an expert loses nothing.
3. **Coherence proven (end P7):** no tab clips at any width; the rail means one thing (task workspaces); Import's simple-fork path is the default; the next-action strip shows the right primary action in every state; Battle/Save expert surfaces are behind disclosure; Ctrl-K reaches everything hidden.

## 7. Scope guardrails

**Explicitly NOT touched (fence so effort isn't misspent):**
- **The ~29 `world-*` overworld commands** (continents/coast/entrances) — the largest CLI-only pillar, zero GUI; building windows for them is net-new feature work.
- **`audio-import`, `image-field`, the FMV pipeline, the Overload `[difficulty]`/`[rebalance]`/`[deathrules]` + `[chocobo]` TOML blocks, and a character-creation wizard** — CLI-only or hand-edit-only; form-coverage gaps, not visual-makeover items.
- **The engine (Memoria DLL, `.eb` format, fork gates) and any new pillar features.** This is a visual/cohesion/learnability pass on the ~83 already-surfaced commands (of ~112 total).

**Constraints to honor:**
- **CLI-second rule** — the GUI wraps proven CLI flows; don't invent behavior the CLI lacks.
- **PySide6 + Fusion required** — Fusion stays mandatory (it's why QSS colors take); don't mix QPalette and QSS coloring on the same widgets.
- **Keep the tk-free-backend / QSS-from-tokens architecture** — theme/style stay headless-testable; the parity + contrast tests stay the compile-time guarantee.
- **Don't break `--smoke`** — the smoke harness and the offscreen screenshot harness must keep passing every phase; phases 2/3/6 add a repaint-regression check.
- **Don't regress power-user speed** — the F9/F6 one-keystroke loop, Ctrl-K reach, and Compact density survive every simplification.

## 8. Open questions for the user

> **Decisions locked (2026-07-14, user):** **Q1 — bundle a custom font** ✓ (licence care: user said "MIT"; most
> quality faces — Inter, JetBrains Mono, IBM Plex — are **SIL OFL**, which is bundle-safe and already used by the
> installer; pure-MIT faces are rare. Pick a permissive OFL/MIT face and ship its licence text). **Q2 — build the
> global Guided/Full beginner mode** ✓ (no longer conditional; P7 scopes it in; Full is always one click, nothing
> removed). **Q3 — samples first** ✓ (P4/P5 build the sample-gallery + teaching-empty-state path; the coached
> walkthrough is a deferrable later add-on). **Q4 — the RAIL that swaps tab sets** ✓ (tree/inspector unmoved, P6)
> **+ the cohesion spine is a YES** ✓ (the mode-aware next-action strip is committed in P7). **Q5 —
> licensed SVG icon set** ✓ (drop the ASCII/unicode glyphs). **Q6 — Comfortable default + Compact toggle** ✓ (ship
> both; Comfortable is the default, Compact is the opt-in — resolves the P3 density default). The originals:


1. **Bundle a custom font?** Ship Inter (UI) + JetBrains Mono/Cascadia (OFL/MIT) for identical cross-machine rendering and guaranteed tabular figures, vs. staying on system Segoe UI (Fluent-native, zero packaging risk). *Note:* `tnum` tabular figures are wired in Phase 2/3 **regardless** — Segoe UI already supports them — so this question is about brand rendering, not the numerals.
2. **Global Guided/Full mode: build it or not?** It is the strongest accessibility lever but new machinery the codebase has deliberately avoided ("NO tab-level hiding anywhere"). **Phase 7 builds it only if you approve here;** the fallback is per-form Advanced accordions only (lower risk, less dramatic). It is *not* scoped-in by default.
3. **Interactive tutorial vs. rich samples + teaching empty-states?** The coach-marked "fork → deploy → F6" walkthrough is highest-impact/highest-effort (and risks tour anti-patterns). The sample-gallery + teaching-empty-state path (Phases 4–5) is ~80% of the value at ~20% of the cost. Ship the cheap path first and defer the walkthrough, or invest now?
4. **How far to reorganize the 10 tabs?** Option A (task-workspace **rail** that swaps tab sets, tree/inspector unmoved — the plan's default) vs. the more ambitious Option C (tabs = *only* the open project; the five mini-apps become a Tools launcher). **And separately: do you want Option D, the mode-aware next-action spine?** The plan treats D as core (Phase 7) because the reports call it "the north-star for cohesion" — confirm you want it, since it changes the shell's chrome.
5. **Real SVG icon set vs. refined monochrome glyphs?** A licensed SVG set (Lucide/Feather/Fluent) is the accessibility- and DPI-correct answer and unifies rail/tree/breadcrumb but adds an asset dependency. Acceptable, or stay glyph-only (cheaper, can't tint uniformly or survive high-contrast mode)?
6. **Density default — resolve before Phase 3 builds it.** Ship **Comfortable** as default (newcomer-friendly, more whitespace) with Compact opt-in, or keep today's dense default with Comfortable opt-in? This sets the first impression *and* determines which of the two QSS-var sets Phase 3 builds first.

---

**Key files for the executing team:** `ff9mapkit/ff9mapkit/editor/theme.py` (palette + `derive()` target; dead ttk at `:264-269`), `ff9mapkit/ff9mapkit/workspace/style.py` (QSS template; `outline:0` at `:16`, toolbar metrics `:20-23`, indicators `:57-59`, tree `:91`, GroupBox `:107`), `ff9mapkit/ff9mapkit/workspace/shell.py` (8562 lines; 60 inline styles; splitter `:995` `[300,640,240]`, tab strip `:965`, consent modal `:478`, onboarding sentence `:1173`, state tracking `:369-376`, retheme staleness `:449`), `importdoc.py` (23 styles, `:50`), `battledoc.py` (11), `builddoc.py` (7, panels `:113-249`), `savedoc.py` (8, nested sub-tabs), `modelsdoc.py` (9, ghost `panel` token `:120`), `forms_qt.py` (12, `build_form`), `editor/feedback.py` (error-translation host), `editor/graphview` (concept map), `jobs.py` (loading states).