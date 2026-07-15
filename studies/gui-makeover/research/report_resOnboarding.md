# External Research — Onboarding & Teaching a Technical Tool to Non-Experts

**Scope:** Evidence-based patterns for first-run onboarding, in-context help, and teaching an unfamiliar domain model, mapped to the Dream World IX **Workspace** (PySide6 desktop IDE). All recommendations are desktop-native and build ON the scaffolding that already exists in the app — they do not assume a SaaS/web overlay stack.

**What the app already has (so recommendations extend, not repeat):** a Home/"Start here" tab with entry-point cards and a live status line (`workspace/shell.py:1139` `_welcome()`), per-node hover help (`_KIND_HELP`, `shell.py:163`), a first-run setup affordance on Home when the install isn't configured (`shell.py:1165–1172`), tooltips on nearly every toolbar action and menu, a "restore last session" button, a Ctrl-K command palette, an Info Hub catalog, and a deliberate "onboarding, not a crash" philosophy in lint/template output (`shell.py:234`, `_render_journey_toml`). The gap is not *absence* of help — it's that help is **passive, uniform, and un-sequenced**: everything is a tooltip, nothing teaches the domain model, and there is no guided path to a first win.

---

## 1. ONBOARDING PATTERN MENU

Effort/impact are rated for *this* app (PySide6 desktop, single-user, offline, expert-heavy today). "Fit" notes call out the specific Workspace surface each pattern lands on.

| Pattern | What it is | Evidence / example | Fit for this PySide6 modding IDE | Effort → Impact |
|---|---|---|---|---|
| **Empty state as teacher** | A blank region (tree, tab, Problems dock, canvas) becomes an instructional CTA: "what will appear here, why it matters, one obvious action." | Empty states are "one of the most common silent drop-off points" and a good one "explains what will appear, why it matters, and gives one obvious action" ([digia](https://www.digia.tech/post/how-to-build-in-app-onboarding-flow-first-win/), [useronboard](https://www.useronboard.com/onboarding-ux-patterns/empty-states/)). Duolingo withheld the dashboard until first lesson; "two parts instruction, one part delight." | The Home tab (`_welcome`) is already an empty-state front door — but the **left project tree**, the **Map tab**, **Story State**, and the **Problems dock** are all blank on cold start with no teaching. Each is a free teaching surface. | Low → High |
| **Sample / template projects** | Ship ready-made example projects users can open, run, and dissect — removes setup friction and shows "what working looks like." | Templates/demo data are the top lever for reducing time-to-first-value; InVision uses pre-made templates in its empty state ([digia](https://www.digia.tech/post/how-to-build-in-app-onboarding-flow-first-win/), [useronboard](https://www.useronboard.com/onboarding-ux-patterns/empty-states/)). | The repo already contains `examples/` (vivi-hut, stolen-ember, continent-v1). Surface them as **one-click "Open example" cards on Home** with a "what this teaches" label. Highest-leverage single move. | Low → Very High |
| **Interactive walkthrough ("learn by doing")** | User performs the *real* action at each step; the step advances only when done — not a passive "Next"-clicking overlay. | Interactive onboarding sees **~50% higher activation** and cuts time-to-value **~40%** vs passive tours; "watching ≠ doing" cognitive gap ([userpilot](https://userpilot.com/blog/interactive-walkthroughs-improve-onboarding/), [guideflow](https://www.guideflow.com/blog/interactive-tutorial-tools), [algocademy](https://algocademy.com/blog/why-watching-tutorials-is-not-learning-the-cognitive-gap-between-seeing-and-doing/)). | A guided "**Fork your first field → deploy → see it in-game**" flow that drives the *real* Import tab and F9 Deploy button. Honors the app's own doctrine (fork/learn from real bytes; edit→deploy→F6). Higher build cost. | High → Very High |
| **First-success / time-to-first-value (TTFV)** | Design the shortest path to one real win; measure/aim for it. | Industry target for first value is **under ~15 min** ([rework](https://resources.rework.com/libraries/saas-growth/onboarding-time-to-value), [digia](https://www.digia.tech/post/how-to-build-in-app-onboarding-flow-first-win/)). "A well-built walkthrough that leads to first success trumps every other onboarding format" ([guideflow](https://www.guideflow.com/blog/interactive-tutorial-tools)). | Define the app's canonical "first win" = a forked field visible in-game via F6. Everything else (glossary, concept map) is scaffolding around this spine. | Design task → Very High |
| **Progressive disclosure / progressive onboarding** | Reveal capability *as it becomes relevant*, not all at once; simplify the first session; introduce advanced features on demonstrated readiness. | "Especially valuable for complex products… reveals capability as it becomes relevant" ([appcues](https://www.appcues.com/blog/user-onboarding-ui-ux-patterns), [skillable](https://www.skillable.com/resources/virtual-training-labs/guided-onboarding/)); "never show advanced tips to users who have not mastered the basics" ([userpilot](https://userpilot.com/blog/progressive-onboarding/)). | The 10-tab QTabWidget + dense Inspector is the overwhelm surface. A **Beginner/Standard density** preference could collapse advanced tabs (Co-op, Models internals) and defer expert Inspector fields until needed. | Medium → High |
| **Contextual help panel (in-context, not modal)** | A dockable/inline panel that explains the *current* view/state and links deeper — proactive or reactive. | Contextual help "answers questions before they realize they have them, in the moment, in the product"; provide **multiple levels** of help, keep inline instructions **<150 chars**, use plain language ([chameleon](https://www.chameleon.io/blog/contextual-help-ux), [userpilot](https://userpilot.com/blog/contextual-help/), [Adobe Spectrum](https://spectrum.adobe.com/page/contextual-help/)). | The **right Inspector panel** is the ideal host: add a collapsible "About this <thing>" section that changes with selection (field/object/gateway). Reactive, never nagging. | Medium → High |
| **Qt native 3-level help (tooltip → status tip → What's This)** | Desktop-native layered help: flyweight tooltip, one-line status-bar tip, and a "What's This?" mode that can be *three paragraphs*. | Qt explicitly distinguishes Tooltip / Status Tip / "What's This?"; the last "can be a three-paragraph explanation" ([flylib](https://flylib.com/books/en/2.18.1/tooltips_status_tips_and_whats_this_help.html), [Qt docs](https://doc.qt.io/qt-6/helpsystem.html)). Don't tooltip obvious controls — repeating a label "adds no information and only distracts." | The app over-uses tooltips as the *only* tier. Add **`setStatusTip`** (feeds the existing bottom dock) and **`setWhatsThis`** for the jargon-heavy controls so a substantive explanation exists without cluttering the tooltip. Built into the framework already. | Low → Medium |
| **Coach marks / spotlights — but at point-of-need only** | A single highlight+callout fired the *first time a user reaches a specific feature*, not at session start. | Session-start tours are skipped/forgotten; NN/g 2024 found tooltips without contextual triggers dismissed **82% of the time within 1.2s**; coach marks "used at the first point of interaction… perform significantly better" ([michaellisboa](https://michaellisboa.com/blog/four-reasons-coach-marks-onboarding-tours-dont-work/), [saasfactor](https://www.saasfactor.co/blogs/why-most-product-tours-fail-and-how-to-implement-contextual-onboarding)). | Use sparingly: a one-time callout the first time the Deploy button or the Import tab is opened. Never a startup carousel. | Medium → Medium |
| **Onboarding checklist w/ visible progress** | A dismissible, skippable checklist of first tasks with progress. | "Progress bars, checklists, and badges make the path to mastery visible… far more likely to finish"; HubSpot's checklist has skip buttons ([userpilot](https://userpilot.com/blog/progressive-onboarding/), [appcues](https://www.appcues.com/blog/best-user-onboarding-examples)). | A small "Getting started" card *on the Home tab* ("① Configure install ② Open an example ③ Fork a field ④ Deploy"), collapsible and remembered — reuses the Home surface, no overlay machinery. | Low → Medium |
| **Concept map / mental-model diagram** | A visual of how the domain's concepts relate (labeled edges, multiple parents) to make an unfamiliar model legible. | Concept maps suit "interconnected concepts… emphasize cause-and-effect," let learners "connect concepts with action," and support **multiple parents** unlike hierarchies ([NN/g](https://www.nngroup.com/articles/cognitive-mind-concept/)). | Journey▸campaign▸field▸object *plus* the off-spine pieces (battle/import/save/models) is exactly a multi-parent graph. A one-screen "How it all fits" diagram directly answers the brief's "connect concepts." The app already owns a `graphview` module in `editor/`. | Medium → High |
| **Glossary / concept cards, inline term teaching** | A searchable glossary + hover/click "concept cards" on jargon terms embedded in the UI. | Contextual help should teach vocabulary "at the moment it occurs" using plain language ([chameleon](https://www.chameleon.io/blog/contextual-help-ux), [userpilot](https://userpilot.com/blog/contextual-help/)). | Directly targets the 15-term jargon wall (journey, walkmesh, fork, gEventGlobal, gateway, mesID, FBG…). See §4. Fits the Info Hub as a home and the Ctrl-K palette as an entry ("search a concept"). | Medium → High |

---

## 2. RECOMMENDED "LEARNABILITY LAYER" FOR THIS APP

A single coherent layer, sequenced as **first-run → first success → in-context help → concept scaffolding → exploration**. Each stage reuses an existing Workspace surface, is skippable, and never blocks an expert.

### Stage 0 — First-run (the moment of entry)
The current Home already detects an unconfigured install (`shell.py:1165`). Extend the Home tab (do **not** add a modal splash) with:
- A **"Getting started" checklist card** at top on cold start only: configure install → open an example → fork a field → deploy. Collapsible, dismissible, progress remembered. Rationale: visible progress drives completion, and it lives in the app rather than as an interrupting overlay ([userpilot](https://userpilot.com/blog/progressive-onboarding/), [appcues](https://www.appcues.com/blog/best-user-onboarding-examples)).
- **"Open an example" cards** for the bundled `examples/` projects, each labeled with *what it teaches* ("Vivi's hut — a minimal field"; "The Stolen Ember — a story campaign"). This is the highest-leverage move: sample projects are the single biggest TTFV lever and turn the empty Workspace into a teacher ([digia](https://www.digia.tech/post/how-to-build-in-app-onboarding-flow-first-win/), [useronboard](https://www.useronboard.com/onboarding-ux-patterns/empty-states/)).

### Stage 1 — First success (the one win that earns retention)
Pick ONE canonical win and instrument the shortest path to it: **fork a real field → deploy → see it in-game (F6)** — target well under the ~15-min TTFV benchmark ([rework](https://resources.rework.com/libraries/saas-growth/onboarding-time-to-value)). Deliver it as an **interactive walkthrough that drives the real Import tab and the real F9 Deploy button**, advancing only when the user performs each action — not a passive tour ([userpilot](https://userpilot.com/blog/interactive-walkthroughs-improve-onboarding/), [algocademy](https://algocademy.com/blog/why-watching-tutorials-is-not-learning-the-cognitive-gap-between-seeing-and-doing/)). This aligns perfectly with the project's own "study real bytes → replicate → verify in-game" doctrine, so the tutorial *is* the real workflow, not a sandbox.

### Stage 2 — In-context help (just-in-time, never nagging)
Layer help so depth is available on demand ([chameleon](https://www.chameleon.io/blog/contextual-help-ux)):
- **Tier A — status tips:** add `setStatusTip` to actions so the existing bottom dock narrates hover in one line (currently the app only uses tooltips). ([Qt docs](https://doc.qt.io/qt-6/helpsystem.html))
- **Tier B — substantive "What's This?":** for the ~15 jargon-bearing controls, add `setWhatsThis` — the one place a 2–3 paragraph plain-language explanation belongs without bloating tooltips ([flylib](https://flylib.com/books/en/2.18.1/tooltips_status_tips_and_whats_this_help.html)).
- **Tier C — Inspector "About this…" section:** a collapsible, selection-aware panel in the right Inspector explaining the currently-selected concept and linking to its concept card. Reactive/proactive contextual help, hosted where the user already looks. Cap first-session contextual prompts to **3–5** ([userpilot](https://userpilot.com/blog/contextual-help/)).

### Stage 3 — Concept scaffolding (make the model legible)
- A **"How it all fits" concept map** — one screen (Info Hub or a Home link) showing journey▸campaign▸field▸object *and* the off-spine pieces (battle, import, save, models) with **labeled relationships** and multiple parents, because the domain is a graph, not a tree ([NN/g](https://www.nngroup.com/articles/cognitive-mind-concept/)). Directly satisfies the brief's "connect concepts." The `editor/graphview` module already exists to render it.
- A **glossary / concept-card library** (see §4) reachable from Ctrl-K ("search a concept") and the Info Hub.

### Stage 4 — Exploration (self-guided, expert-respecting)
- Keep everything above **skippable and non-recurring**; power users see the checklist once and dismiss it forever.
- Ctrl-K becomes a discovery engine: it already jumps to commands/fields/objects — extend it to also match **concepts** so "gateway" surfaces its card, not just a command. Discoverability without hand-holding ([Laws of UX — onboarding for active users](https://lawsofux.com/articles/2024/onboarding-for-active-users/)).
- A **density/beginner preference** (progressive disclosure) that defers advanced tabs/Inspector fields until invoked — an opt-in simplification, not a locked "beginner mode" ([userpilot](https://userpilot.com/blog/progressive-onboarding/)).

---

## 3. ANTI-PATTERNS TO AVOID

- **Startup modal tour / carousel of coach marks.** 5-step tours complete at a **~34% median**; interactive demos at **~30%**; users forget content shown before they need it ([saasfactor](https://www.saasfactor.co/blogs/why-most-product-tours-fail-and-how-to-implement-contextual-onboarding), [digia](https://www.digia.tech/post/anatomy-of-a-great-in-app-onboarding-tour/)). Prefer point-of-need callouts.
- **Guidance fatigue from acontextual tooltips.** NN/g 2024: tooltips without contextual triggers are dismissed **82% of the time within 1.2s** — too fast to process ([saasfactor](https://www.saasfactor.co/blogs/why-most-product-tours-fail-and-how-to-implement-contextual-onboarding)). The app's current "everything is a tooltip" habit risks exactly this; move depth into What's This / Inspector, and don't tooltip self-evident controls ([Qt guideline](https://flylib.com/books/en/2.18.1/tooltips_status_tips_and_whats_this_help.html)).
- **Setup-wizard-as-onboarding.** Traditional wizards "focus on technical setup and rarely teach users how to use the product meaningfully," aren't interactive, and are impersonal ([userpilot](https://userpilot.com/blog/onboarding-wizard/)). The existing `setupdialog.py` should stay a *config* step, never the teaching path.
- **Hiding real features behind a beginner mode.** Progressive disclosure means *reveal as relevant*, not *lock away* ([guideflow](https://www.guideflow.com/blog/user-onboarding-best-practices)). Any density preference must be a reversible view filter, and experts must be able to turn it fully off.
- **Dumbing-down microcopy that insults experts.** Plain language "benefits all users, regardless of expertise" — it is not the same as childish copy ([NN/g plain language](https://www.nngroup.com/videos/plain-language-for-experts/)). Write at a 6th–8th-grade level *and* keep precise terms, defining them inline (§4).
- **Non-skippable / recurring prompts.** Anything that re-appears after dismissal becomes noise; onboarding must respect expert speed and be one-and-done ([userpilot](https://userpilot.com/blog/progressive-onboarding/)).
- **Over-gamification.** Badges/progress are fine for the getting-started checklist; don't extend points/streaks into a professional modding tool.

---

## 4. HOW TO TEACH *THIS* DOMAIN'S VOCABULARY IN-APP

The brief names the real learnability blocker: journey, campaign, field, object, fork/verbatim/editable/native, walkmesh, gEventGlobal/story-flag, gateway, encounter, mesID, FBG, Memoria, F6, deploy, scenario. Principles from the research, applied concretely:

**a) Define at point-of-use, not in a manual.** Teach a term "at the moment it occurs" ([chameleon](https://www.chameleon.io/blog/contextual-help-ux)). The app already does a light version of this in `_KIND_HELP` (`shell.py:163`) — extend that dictionary into a real **concept-card registry** and reuse the same strings everywhere the term appears (tree hover, Inspector, glossary), so one definition stays consistent.

**b) Layer the depth (tooltip → What's This → concept card).** A first-glance gloss in the tooltip/status tip, a paragraph in What's This, and a full concept card (with a diagram and "related concepts" links) for the curious ([Qt 3-level help](https://flylib.com/books/en/2.18.1/tooltips_status_tips_and_whats_this_help.html), [chameleon multi-level help](https://www.chameleon.io/blog/contextual-help-ux)).

**c) Plain language + one analogy per term.** Keep the precise term, add a 6th–8th-grade sentence and a familiar analogy (e.g., *walkmesh* = "the invisible floor that says where the character can stand and how far away things look"; *fork* = "make your own editable copy of a real FF9 room"; *gateway* = "a doorway trigger that warps the player to another field"). Unclear instructions cause ~50% of user errors and users scan rather than read, so lead with the analogy ([NN/g cognitive load](https://www.nngroup.com/articles/4-principles-reduce-cognitive-load/), [NN/g plain language](https://www.nngroup.com/videos/plain-language-for-experts/)).

**d) Show relationships, not just definitions — a concept map.** The vocabulary is interconnected (a *journey* contains *campaigns* which contain *fields* which contain *objects* like *gateways*; a *fork* produces a *field*; *deploy* + *F6* is the loop; *gEventGlobal* is orthogonal state). Concept maps with labeled edges and multiple parents are the right tool to make this legible and let users "connect concepts with action" ([NN/g](https://www.nngroup.com/articles/cognitive-mind-concept/)). One "How it all fits" diagram converts a jargon list into a mental model.

**e) Distinguish the four fork modes explicitly.** verbatim/editable/native/import is the highest-confusion cluster. A tiny comparison card ("verbatim = exact copy; editable = re-authorable scaffold; native = seamless art; import = the umbrella command") at the Import tab's point of choice prevents the classic wrong-mode mistake — an in-context help panel attached to the mode selector ([Adobe Spectrum contextual help](https://spectrum.adobe.com/page/contextual-help/)).

**f) Make concepts searchable.** Route the existing Ctrl-K palette to match concept names so a newcomer who hears "encounter" can find its card instantly — discoverability without hand-holding ([Laws of UX](https://lawsofux.com/articles/2024/onboarding-for-active-users/)).

**g) Teach through the sample projects.** The strongest vocabulary lesson is a real, runnable example annotated with the terms in situ (open `examples/vivi-hut`, and its objects/gateways/walkmesh are labeled with hover cards). Learn-by-doing beats definitions ([guideflow](https://www.guideflow.com/blog/interactive-tutorial-tools)).

---

## Priority read (fast wins first)

1. **Example-project cards + "Getting started" checklist on the existing Home tab** (low effort, very high impact — sample projects are the top TTFV lever). ([digia](https://www.digia.tech/post/how-to-build-in-app-onboarding-flow-first-win/))
2. **Concept-card registry** extending `_KIND_HELP`, surfaced via Qt `setWhatsThis` + an Inspector "About this…" panel + Ctrl-K (directly dismantles the jargon wall, framework-native). ([chameleon](https://www.chameleon.io/blog/contextual-help-ux), [Qt](https://doc.qt.io/qt-6/helpsystem.html))
3. **Empty-state teaching** for the tree / Map / Story State / Problems dock (low effort, high impact). ([useronboard](https://www.useronboard.com/onboarding-ux-patterns/empty-states/))
4. **One "How it all fits" concept map** (answers "connect concepts" directly, reuses `editor/graphview`). ([NN/g](https://www.nngroup.com/articles/cognitive-mind-concept/))
5. **Interactive "fork → deploy → F6" first-success walkthrough** (highest impact, highest effort — schedule after 1–4). ([userpilot](https://userpilot.com/blog/interactive-walkthroughs-improve-onboarding/))

---

## Sources

- [In-App Onboarding Flow: Getting Users to Their First Win — Digia](https://www.digia.tech/post/how-to-build-in-app-onboarding-flow-first-win/)
- [The Anatomy of a Great In-App Onboarding Tour — Digia](https://www.digia.tech/post/anatomy-of-a-great-in-app-onboarding-tour/)
- [SaaS Onboarding UX Examples — SaaSUI](https://www.saasui.design/blog/saas-onboarding-ux-examples)
- [Onboarding UX: 10 patterns — Appcues](https://www.appcues.com/blog/user-onboarding-ui-ux-patterns)
- [26 Best User Onboarding Examples — Appcues](https://www.appcues.com/blog/best-user-onboarding-examples)
- [Onboarding & Time-to-Value — Rework](https://resources.rework.com/libraries/saas-growth/onboarding-time-to-value)
- [Onboarding UX Patterns: Empty States — UserOnboard](https://www.useronboard.com/onboarding-ux-patterns/empty-states/)
- [Guided Onboarding for Technical Products — Skillable](https://www.skillable.com/resources/virtual-training-labs/guided-onboarding/)
- [4 Reasons Coach Marks & Onboarding Tours Don't Work — Michael Lisboa](https://michaellisboa.com/blog/four-reasons-coach-marks-onboarding-tours-dont-work/)
- [Why Most Product Tours Fail — SaaSFactor](https://www.saasfactor.co/blogs/why-most-product-tours-fail-and-how-to-implement-contextual-onboarding)
- [Contextual Help UX in 2026 — Chameleon](https://www.chameleon.io/blog/contextual-help-ux)
- [Provide Contextual Help with 8 UX Patterns — Userpilot](https://userpilot.com/blog/contextual-help/)
- [Contextual Help — Adobe Spectrum](https://spectrum.adobe.com/page/contextual-help/)
- [Progressive Onboarding — Userpilot](https://userpilot.com/blog/progressive-onboarding/)
- [Onboarding for Active Users — Laws of UX](https://lawsofux.com/articles/2024/onboarding-for-active-users/)
- [Tooltips, Status Tips, and What's This? Help — flylib (Qt)](https://flylib.com/books/en/2.18.1/tooltips_status_tips_and_whats_this_help.html)
- [Help System — Qt 6 docs](https://doc.qt.io/qt-6/helpsystem.html)
- [Interactive Walkthroughs Improve Onboarding — Userpilot](https://userpilot.com/blog/interactive-walkthroughs-improve-onboarding/)
- [Best Interactive Tutorial Tools 2026 — Guideflow](https://www.guideflow.com/blog/interactive-tutorial-tools)
- [User Onboarding Best Practices — Guideflow](https://www.guideflow.com/blog/user-onboarding-best-practices)
- [Why Watching Tutorials Is Not Learning — AlgoCademy](https://algocademy.com/blog/why-watching-tutorials-is-not-learning-the-cognitive-gap-between-seeing-and-doing/)
- [Why the Onboarding Wizard Falls Short — Userpilot](https://userpilot.com/blog/onboarding-wizard/)
- [Cognitive Maps, Mind Maps, and Concept Maps — NN/g](https://www.nngroup.com/articles/cognitive-mind-concept/)
- [4 Principles to Reduce Cognitive Load in Forms — NN/g](https://www.nngroup.com/articles/4-principles-reduce-cognitive-load/)
- [Plain Language For Everyone, Even Experts — NN/g](https://www.nngroup.com/videos/plain-language-for-experts/)
- [What are Mental Models? — Interaction Design Foundation](https://ixdf.org/literature/topics/mental-models)