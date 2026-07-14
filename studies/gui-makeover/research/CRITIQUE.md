# Adversarial critique — The Workspace Makeover phased plan

The plan is genuinely strong on the token substrate (Phase 1), the de-smush pass (Phase 2), and the accessibility measurement floor. It correctly treats tokens as an evolution not a rewrite, fences the CLI-only backlog, and keeps the expert lane (Ctrl-K/F9/F6) as the enabling principle. Most of Reports B, F, and I are faithfully phased. The problems below are about **dropped cohesion insight, a disclosure mechanism that doesn't reach the actual dense surfaces, sequencing that buries the brief's primary ask, and two under-called XL phases.**

---

## CRITICAL

**1. The "what do I do next" cohesion spine is entirely missing.**
*Where:* nowhere — Phases 3–4 and Milestone 2 ("Coherence proven"). *What's wrong:* the plan resolves "where am I" (the existing chip, already done per Report C §4) and "what is this word" (Phase 4 glossary), but not **"what's my next step."** Report C's Option D (mode-aware next-step spine) is called *"the north-star for cohesion"* and is the direct answer to F6 and F10; Report G's P10 (persistent next-action hints) and Report H's stage-4 status line say the same thing. Open Q4 offers A vs C but **never mentions D.** The brief's word is *cohesion*, and the reports locate the deepest cohesion failure precisely here ("five panels with five subjects and no unifying 'you are working on ___, here's the flow' spine," C-F10). *Fix:* add a modest, collapsible mode-aware next-action strip (EMPTY→"Fork a room / Open a project"; loose-field-unsaved→"Save · Deploy F9 · Playtest") as a Phase 3 or dedicated phase — it reuses state the shell already tracks (`shell.py:369-376`), so it's presentation, not new logic. At minimum, add D to Open Q4.

**2. The progressive-disclosure mechanism does not reach the densest surfaces.**
*Where:* Phase 4 scope + Design principle 1; it leans on "per-form Advanced accordions in `forms_qt.build_form`" and Report G's claim that "one disclosure mechanism covers all ~36 pillars." *What's wrong:* that is **only true for the Editor tab's 18 generated block forms.** The actual density offenders per Report E — Import (68 widgets), Build (6 panels), Battle (donor-site offset picker + donor-AI B_MEMBER table, E#3), and Save (nested Inspect/Diff/Edit sub-tabs, E#4) — are **hand-built doc modules, not generated forms**, so the central accordion mechanism never touches them. Phase 3 reorganizes Import and Build specifically, but **Battle's expert byte-level surfaces and Save's nested sub-tabs get no disclosure treatment in any phase.** *Fix:* explicitly scope per-doc disclosure work for battledoc/savedoc (Advanced drawer for donor pickers; flatten or fence the sub-tabs), and stop asserting the central form builder covers the pillars it structurally cannot.

**3. Learnability — the brief's PRIMARY ask — is gated behind the L-effort IA reorg and lands second-to-last.**
*Where:* Phase 4 "Dependencies: Phase 3." *What's wrong:* Reports D (priority read) and H (priority read) both rank the highest-ROI newcomer wins — **sample gallery, teaching empty-states, concept cards, "?" affordances, reassurance microcopy** — as *cheapest, fastest, ship-first*, and none of them hide anything, so none needs Ctrl-K or the reorg. The plan's justification ("the escape hatch must exist before you hide anything") is valid **only for the global Guided/Full HIDING mode** — it does not justify gating additive teaching. As written, a newcomer sees *zero* learnability improvement until after a large structural phase. *Fix:* split Phase 4. Pull the additive teaching (samples, teaching empty-states, concept-card registry + "?" links, F6/reassurance microcopy) forward into P0–P2 where it has no hard dependency; keep only the global Guided/Full mode after P3.

**4. Phases 2 and 4 are under-estimated (each is XL bundling 4–6 subsystems under one "L").**
*Where:* Phase 2 (L) and Phase 4 (L). *What's wrong:* Phase 2 bundles the **136-site inline-`setStyleSheet` sweep across the 8,562-line shell + ~14 doc modules** (Report B treats this as its own migration step #3) *plus* inspector redesign *plus* an empty-state system *plus* a density toggle. Phase 4 bundles first-run + sample gallery + concept-card registry + teaching empty-states + concept map + global Guided/Full mode + the **hidden error-translation subsystem (4g)**. Both are XL and regression-prone (the sweep especially). *Fix:* split each into two phases (or mark XL), and give the 136-site sweep its own screenshot-diffed sub-milestone.

**5. Scope commits to machinery the plan is simultaneously asking permission for, and a criterion inverts its dependency.**
*Where:* Phase 4 scope-in lists "a global Guided/Full mode" as decided, while Open Q2 asks *whether to build it* and flags it as "new machinery the codebase has deliberately avoided." Separately, Phase 3's success criterion "Ctrl-K surfaces 'gateway' as a concept card" **references a Phase 4 deliverable** — concept cards don't exist until Phase 4. *Fix:* move the global-mode work behind the Q2 decision (don't scope-in an open question); retarget the Phase 3 criterion to something Phase 3 actually produces (e.g. "Ctrl-K surfaces every tab as a verb-first, category-prefixed command with keybinding hint").

---

## IMPORTANT

**6. "Full-width strip" and "5-workspace rail" are conflated, and the reparent is riskier than L.**
*Where:* Phase 3 scope. *What's wrong:* it says both "lift the tab strip to full window width" **and** "regroup into ~5 workspaces (rail/segmented control)" — two different structural solutions. Lifting a 10-tab strip full-width doesn't reckon with **where the tree and inspector go**: today all three are children of one horizontal splitter (`shell.py:995`, `[300,640,240]`). Report C's cleaner fix is a rail that *swaps* the tab set (never shows all 10) — which also kills the overflow without fighting the splitter. *Fix:* pick one target geometry and state what happens to tree/inspector; treat the central-layout restructure as its own risk line.

**7. The error-translation layer and reassurance microcopy are buried inside "4a-4h."**
*Where:* Phase 4 deliverables ("Reports D-§4 (4a-4h)"). *What's wrong:* 4g (plain-language error rewriting in `feedback.py`, Report G7) is a distinct **M-effort subsystem** and 4h (reassurance one-liner near F9 + "what is F6" tooltip, Report G8/D-§2) is cheap-and-high-value — both vanish inside a range citation with no own success criterion, and cheap things that aren't named don't get built. Report H's Qt `setStatusTip` tier (feeds the existing bottom dock) is also unmentioned. *Fix:* surface 4g as its own item; move 4h microcopy into Phase 0 (it's pure copy).

**8. Accessibility contradicts its own "floor, not finish" principle by deferring the bulk to Phase 6.**
*Where:* principle 7 vs Phase 6. *What's wrong:* `setAccessibleName` (zero today, Report I) is explicitly "low-effort, high-value" and target-size/color-not-alone are cheap, yet they land in the last hardening phase — meaning P0–P5 all ship screen-reader-blind. *Fix:* front-load `setAccessibleName` on actionable controls as controls are touched in P0/P2/P3 (add it to the component/factory work), leaving Phase 6 for the audit/verification and custom-canvas cases.

**9. Tabular figures are stranded inside the font open-question.**
*Where:* Open Q1 only. *What's wrong:* Report I flags `tnum` (via `QFont::setFeature`, Qt 6.7+) as high-value because the UI is "full of ids/coords/byte offsets," and it's **independent of bundling a font** (Segoe UI already supports tabular numerals). It's a concrete Phase-1/2 typography deliverable, not a font-bundling side-effect. *Fix:* assign tnum-on-data/mono-fonts to Phase 2 regardless of the Q1 decision.

**10. Newcomer success criteria aren't machine-verifiable and lean on unavailable usability testing.**
*Where:* Phase 4 criteria + Milestone 3 ("a first-launch user reaches a running sample… within ~10 minutes"). *What's wrong:* the offscreen screenshot harness can capture the GUI but cannot simulate a naive human's 10-minute path. *Fix:* split each into a screenshot-checkable half ("cold-launch Home shows the sample gallery + getting-started checklist; clicking a sample opens it read-only in tree/Editor with no engine-param dialog") and an explicit human-playtest gate for the timing claim.

**11. Cheap newcomer levers from the reports are dropped.**
*Where:* not present. *What's wrong:* Report G's P11 ("Try it now" safe-sandbox framing of the existing 4003/F6 loop) and P8 ("just get me started" default setup path deferring id-band/mod-folder choices) are low-effort, high-retention, and reuse existing loops; Report A's "adopt the Catalog three-pane, count-badged pattern as house style" is a coherence lever; the Map-legend-chip and Home-prose-trim quick wins are also dropped. *Fix:* fold the first-run default path + "Try it now" into the first-run work; fold Map legend + Home prose into Phase 0/2.

---

## NICE

**12. Density-toggle decision ordering.** Phase 2 builds the toggle and ships Comfortable as default, but the default is Open Q6 — resolve Q6 before Phase 2 builds two QSS-var sets you might not want.

**13. Numeric framing drift.** The north-star says the app "fronts 112 CLI commands through 10 tabs," but Report E is clear only ~83 are surfaced (112 total, ~29 world-* + audio/image/FMV are the fenced backlog). Tighten so §7's fence stays internally consistent.

**14. Screenshot-harness staleness risk uncalled.** Report A documents a re-mount repaint artifact in the offscreen harness. Since screenshot-diff *is* the success-criteria engine for Phases 0–3, phases that change mount/repaint (2, 3) should add "no repaint regressions" as an explicit check.

**15. Minor cleanup capture.** The ghost `panel` token (`modelsdoc.py:120`) is captured (Phase 1); the legacy tkinter font reconfig (`theme.py:264-269`, Report B §1b) isn't — harmless but worth a one-line Phase-1 cleanup note so the token module stops carrying dead ttk styling.

---

## The 5 most important changes

1. **Add the next-action / workflow cohesion spine** (Report C Option D, G-P10, H-stage-4). The plan fixes "where am I" and "what is this word" but not "what do I do next" — the deepest cohesion gap the reports name. Put D in a phase and in Open Q4.
2. **Fix the disclosure gap for the hand-built dense docs.** The central `forms_qt` accordion covers only the Editor's generated forms; Battle (donor pickers), Save (nested sub-tabs), and the rest need explicit per-doc disclosure. Stop claiming one mechanism covers all pillars.
3. **Re-sequence learnability forward.** Pull samples, teaching empty-states, concept cards, "?" affordances, and reassurance microcopy into P0–P2 (they hide nothing, need no reorg); gate only the global Guided/Full HIDING mode behind P3. The brief's primary ask can't be the second-to-last phase.
4. **Re-estimate/split Phases 2 and 4** — each is XL, not L; give the 136-site sweep and the error-translation subsystem (4g) their own named deliverables and success criteria so the buried, regression-prone work is visible.
5. **Resolve the internal contradictions and front-load cheap a11y** — un-scope the Guided mode that Q2 still questions, fix the Phase-3 criterion that references a Phase-4 concept card, add `setAccessibleName` and tabular figures early to honor principle 7.