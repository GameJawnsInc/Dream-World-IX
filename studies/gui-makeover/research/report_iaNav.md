I now have comprehensive evidence across the whole navigation surface. Here is my report.

---

# IA / NAVIGATION / COHESION — Research Report (Workspace shell)

Scope: `ff9mapkit/ff9mapkit/workspace/shell.py` (8,562 lines) + the six doc surfaces + `palette.py`, `style.py`, `editor/breadcrumb.py`, `editor/theme.py`. All findings are read-only, evidence-cited.

The headline: the Workspace is a genuinely-hardened IDE, but its **primary spatial control — the 10-tab strip — is being asked to carry three incompatible jobs on one axis, and it is physically too narrow to show them.** The 2026-06-22 audit fixed *legibility of "where am I"* (breadcrumb + chip); it did **not** touch *the organization of the surfaces themselves*. That is this pass's opening.

---

## 1. NAV MAP — the whole surface

```
WORKSPACE (QMainWindow, 1280×820 default)
│
├─ TOOLBAR  (single QToolBar, non-movable, width-budgeted to 1280 — shell.py:742)
│  ├─ [Field ▾]      New Field (Ctrl-N) · Open Field                    (748)  ┐ 3 hierarchy
│  ├─ [Campaign ▾]   New Campaign (Ctrl-Shift-N) · Open Campaign        (751)  │ dropdowns =
│  ├─ [Journey ▾]    New Journey · Open Journey                         (754)  ┘ 6 file ops
│  │  ── separator ──
│  ├─ Open Save…                                                        (759)
│  ├─ Close          (the way OUT of any mode → empty Workspace)        (763)
│  │  ── separator ──
│  ├─ Undo · Redo · Save All · Check · Refresh(F5) · Lint               (769-802) 6 verbs
│  ├─ [Info Hub]     ← the ONLY filled/colored toolbar button (violet)  (803)
│  │  ══ expanding spacer ══
│  ├─ [⌕ Search anything (Ctrl-K)]  pill                                (817)
│  └─ [⚙ ▾]          Setup&health · Preferences · Updates · About       (825)  4 items
│                    → ~20 distinct actions reachable from the toolbar
│
├─ BREADCRUMB ROW  (its own styled strip — shell.py:864)
│  ├─ [CHIP]  persistent doc-mode chip: HUB/JOURNEY/CAMPAIGN/FIELD/BATTLE/SAVE/BUILD/MODEL  (297,3174)
│  ├─ ⌂ Hub ▸ ◆ Journey ▸ ▣ Campaign ▸ ● Field ▸ ▸ Object   (clickable ancestors)  (322)
│  └─ [▶ Deploy  F9]  ← accent button, DISABLED until a project opens   (873)
│
├─ CENTRAL = horizontal QSplitter, panes sized [300, 640, 240]  (995)
│  │
│  ├─ TREE pane (300px)                                                 (891)
│  │  ├─ ⌕ filter-the-tree box                                         (895)
│  │  └─ QTreeWidget — the journey▸campaign▸field▸object spine          (900)
│  │     └─ right-click / Delete-key CONTEXT MENU (per node):           (5022)
│  │        Add journey · Shared flags · Add region to arc · Set seed ·
│  │        Set tuning · Remove journey · Add field · Add NPC · Define ·
│  │        Delete <entity> · Remove <single>        (~11 conditional actions)
│  │
│  ├─ TAB pane (640px)  ← QTabWidget, 10 tabs, documentMode  (917, 965)
│  │  │  ***THE STRIP IS ~640px WIDE. 10 tabs need ~1150px. HALF OVERFLOW
│  │  │     INTO SCROLL-ARROW CHEVRONS at the default window size.***
│  │  ├─ 0  Home            landing / "Start here"           (1214)   ┐ landing
│  │  ├─ 1  Editor          the open node's form              (928)   ┐ open-project
│  │  ├─ 2  Map             campaign graph                    (932)   ┘ views
│  │  ├─ 3  Story State     save flags (ORTHOGONAL)           (936)   ┐ save-state
│  │  ├─ 4  Item & Equip    save inventory (ORTHOGONAL)       (938)   ┘ editors
│  │  ├─ 5  Battle          battle.toml (self-contained app)  (942)   ┐
│  │  ├─ 6  Models          ~710-model browser (self-cont.)   (947)   │ standalone
│  │  ├─ 7  Build & Deploy  the dev-loop console (self-cont.) (951)   │ UTILITY
│  │  ├─ 8  Import          fork-a-field (self-contained)     (956)   │ surfaces
│  │  └─ 9  Co-op           multiplayer host/join (self-cont.)(960)   ┘
│  │
│  └─ INSPECTOR pane (240px, capped 420px)                              (967)
│     └─ read-only card w/ clickable links:
│        goto:<member> · goto:battle:<id> · copy-path · jseed · jtuning · setup
│
├─ CONSOLE  (bottom pane of a VERTICAL splitter, collapsible — shell.py:1007)
│  └─ Problems  │  Output    (side-by-side, one draggable divider)
│
└─ Ctrl-K COMMAND PALETTE  (modal overlay — palette.py:32, index at shell.py:3267)
   ├─ ~26 fixed commands: New/Open ×spine · Open Save · Check · Lint ·
   │  Browse catalog · Fork FF9 regions · Undo · Redo · Save All ·
   │  Go to {Editor,Map,Story State,Item&Equip,Models,Build,Import,Co-op} ·
   │  Deploy now (F9) · Setup · Preferences · Updates · About
   ├─ + up to 5 mode-conditional (Add field / Add journey / Add region / Fill entry)
   ├─ + "Reopen X" per Recent entry
   └─ + EVERY navigable tree node (fuzzy, field-qualified)
```

**Inventory totals:** ~20 toolbar actions · 2 breadcrumb-row controls · 10 tabs · ~11 tree context actions · ~26+ palette commands (+ all content nodes) · ~6 inspector link types · ~10 Home entry buttons. A newcomer's first screen therefore presents **roughly 40 always-visible interactive targets** before they have opened anything.

**Redundancy map** (same destination, many doors — mostly *intentional*, but it inflates the surface):

| Destination | Doors |
|---|---|
| Open Journey | Toolbar `Journey▾` · Home "Journey ▸ Open" (accent) · Ctrl-K "Open Journey…" · Recent row · drag-drop |
| New Field | Toolbar `Field▾` · Home "Field ▸ New" · Ctrl-K "New Field…" · Ctrl-N |
| Info Hub | Toolbar button · Ctrl-K "Browse catalog" |
| Go to Battle | Tab 5 · Home "Battle" row · Ctrl-K "Go to Battle" |
| Go to Models | Tab 6 · Home "Models" row · Ctrl-K "Go to Models" · Import "models" pointer · .glb drag-drop |
| Deploy | Breadcrumb `▶ F9` · Build&Deploy tab · Ctrl-K "Deploy now" · F9 key |
| Save | Toolbar Save All · Ctrl-S · Ctrl-Shift-S · Ctrl-K "Save All" · per-form Save button |

The "Go to X" duplication between **tabs and the palette** is the clearest pure-redundancy: every tab is *also* a palette command and *also* (for 4 of them) a Home row. The tabs are the weakest of the three because they're the ones that overflow.

---

## 2. IA FRICTION — ranked

### F1 — The tab strip carries three incompatible axes on one row, and is physically too narrow to show them *(hurts: everyone; acute for newcomers)*
The 10 tabs are not one kind of thing. They interleave: a **landing page** (Home), **views of the open project** (Editor, Map — these change when you open a field), **orthogonal save-file editors** (Story State, Item & Equip — ignore the open project, act on a `.dat`), and **five self-contained mini-apps** (Battle, Models, Build & Deploy, Import, Co-op — each a former standalone tkinter window folded in). A tab strip implies "different views of the same subject." Here, tab 1 (Editor) and tab 8 (Import) share nothing — Import doesn't even read the open project. This is the mechanical source of the brief's "unclear cohesion": the top-level spatial metaphor is lying.
*Where:* `shell.py:928-960` (addTab sequence).

### F2 — The tab strip is confined to the 640px middle splitter pane, so ~half the tabs clip into scroll chevrons at default size *(hurts: everyone; the reported "Build & Deploy clipped")*
`self.tabs` is added as the middle child of the horizontal splitter (`split.addWidget(self.tabs)`, shell.py:965), and the splitter defaults to `[300, 640, 240]` (shell.py:995). The 10 tab labels — including "Story State", "Item && Equip", "Build && Deploy" — need roughly 1,100–1,150px; they get ~640px. Qt's `QTabWidget` (usesScrollButtons defaults on) therefore hides the trailing tabs (Import, Co-op, and often Build & Deploy) behind left/right scroll arrows. **The overflow is not a font accident — it is structural: the strip can never widen past the middle pane, no matter how wide the window is, because the tree and inspector are fixed-ish siblings.** This is the same class of bug the 2026-07-06 pass fixed for the *toolbar* (overflow chevron hiding Ctrl-K/gear) — but it was never checked for the *tab bar*.
*Where:* `shell.py:965, 995`.

### F3 — There is no guided path for a newcomer; landing = a wall of ~40 targets with the primary action de-emphasized *(hurts: less-technical users — the brief's core ask)*
On cold start the app shows Home (good), but Home sits inside the full IDE chrome: a 20-action toolbar, a 10-tab strip, an empty tree, an empty inspector, an empty console. The single accent CTA is **"Journey ▸ Open"** on a Home card (shell.py:1191, `is_primary=True`), but the most visually prominent *colored* control on the whole screen is the toolbar's violet **Info Hub** button (shell.py:445 — the only filled toolbar button), which is a *reference catalog*, i.e. a secondary feature. The actual "start" and the visual emphasis point at different things. And "open a Journey" is itself the *hardest* concept for a newcomer (see F5) — pointing a first-timer at the deepest abstraction is backwards.
*Where:* Home `shell.py:1139-1215`; hub tint `shell.py:441-447`.

### F4 — Everything is shown at once; there is zero progressive disclosure / no "simple mode" *(hurts: less-technical users)*
Grep confirms **no beginner/advanced/simple-mode/expert toggle anywhere** in the shell. Tab visibility is never conditioned — `setTabVisible`/`removeTab` are never called (confirmed; the Chocobo memory note explicitly records "the app has NO tab-level hiding anywhere"). So a user who only wants to fork one room and walk it is shown Co-op, Models (710-model browser), Battle AI, and journey assembly with equal weight. The *doc surfaces themselves* are also maximally dense: Import alone mounts **24 buttons, 11 checkboxes, 14 inputs, 11 sections** on one scroll (measured); Save has 7 combos + 10 inputs across nested Inspect/Diff/Edit sub-tabs. Nothing collapses by task or skill.
*Where:* density measured across `importdoc.py` / `savedoc.py` / `builddoc.py`; no disclosure API in `shell.py`.

### F5 — The domain vocabulary is never taught at the point of first contact *(hurts: less-technical users)*
The nav *labels* are the jargon: Journey, Campaign, Field, Import (fork/verbatim), Story State (gEventGlobal), Co-op. The only teaching surfaces are **hover tooltips** (`_KIND_HELP`, shell.py:163) and one **Home intro sentence** ("Start at any level — they nest…", shell.py:1173). Tooltips are invisible until hovered and never appear on the tab strip itself. A newcomer reading the 10 tab titles gets no scaffolding for what "Story State" vs "Item & Equip" vs "Editor" even mean, or why "Battle" and "Import" are peers of "Editor." The concepts nest (journey▸campaign▸field▸object) but the *tabs* don't express the nesting — only the tree does.
*Where:* `_KIND_HELP` shell.py:163-172; Home intro shell.py:1173.

### F6 — Mode legibility is solved for "what am I editing" but not for "what CAN I do here / where do I go next" *(hurts: intermediate users)*
The 2026-06-22 chip+breadcrumb work (F-refs below) genuinely fixed *identity* — the chip always names HUB/JOURNEY/CAMPAIGN/FIELD/BATTLE/SAVE/BUILD/MODEL (shell.py:3174) and the breadcrumb is truthful per-tab (`_on_tab_changed`, shell.py:3202). But that answers "where am I," not "what's my next step." There's no next-action affordance tied to the current mode: an empty EMPTY-mode Workspace, a JOURNEY with unforked arcs, a LOOSE field ready to deploy — all present the same static chrome. The Deploy button greys/ungreys (shell.py:6071) but nothing guides the *sequence* author → check → deploy → playtest.

### F7 — Save-state editors are mis-filed as peer tabs of the project editors *(hurts: everyone; a conceptual category error)*
Story State (tab 3) and Item & Equip (tab 4) edit a **game save file** — orthogonal state that shares only the flag namespace with the open project (the audit itself classifies them "ORTHOGONAL"). Yet they sit *between* Map and Battle in the primary strip, so opening a save silently changes what two of your ten tabs mean, with no visual grouping to say "these two are a different subject." They earned a SAVE chip, but a chip on a mis-placed tab is a patch, not a fix.
*Where:* `shell.py:936-938`; classification in the audit note (memory).

### F8 — The toolbar mixes app-file ops, per-project verbs, and global utilities without grouping cues *(hurts: intermediate users)*
Reading left→right (shell.py:748-829): file-open dropdowns → Open Save → Close → Undo/Redo/Save All/Check/Refresh/Lint → Info Hub → search → gear. Only two separators break ~14 slots. "Close" (a project-lifecycle verb) sits next to "Open Save" (a file op) and just before "Undo" (an edit verb). Check / Refresh / Lint are three *validation* verbs that look identical but do different things (in-process check vs re-read-scene vs subprocess-lint) — their only differentiation is a tooltip. There's no visual grammar telling a user which buttons act on *the file*, which on *the open project*, which are *global*.

### F9 — Palette and tabs duplicate the same "Go to" navigation, doubling maintenance and user model *(hurts: everyone, mildly)*
Every tab has a matching Ctrl-K "Go to X" (shell.py:3285-3292) and 4 have a Home row too. Three parallel navigation systems (tabs, palette, Home cards) index the same surfaces. For a power user this is fine (redundancy = reach); for a newcomer it's three things to learn that do the same job, and it means every new surface must be wired in three places.

### F10 — Cohesion of the frame itself is strong at the chrome level but weak at the "one app" level *(hurts: perception / the "prettification" ask)*
Positives worth stating: a single QSS built from one 22-key palette (`style.py`), Fusion forced, one accent color, consistent radii, `QFrame#card` Home cards, glyph language shared across tree/breadcrumb (`⌂◆▣●▸⚔◈`). So the *pixels* cohere. What doesn't cohere is the *conceptual frame*: the toolbar acts on files, the tree on the project spine, the tabs on a grab-bag of subjects, the inspector on the selected node, the console on jobs — five panels with five different subjects and no unifying "you are working on ___, here's the flow" spine. The chip is the only thread tying them, and it's a 60px label.

---

## 3. REORG OPTIONS

Four options, roughly increasing in ambition. They compose — A+B is a natural pairing, D is the north-star.

### Option A — Regroup the 10 tabs into task-phase clusters; fix the physical overflow *(low risk, high clarity)*
Stop treating the 10 as one flat list. Group them into the author→test→deploy→learn arc the workflow already implies:

- **AUTHOR** — Editor, Map *(views of the open project)*
- **ASSETS** — Models, Battle, Import *(the things you pull in / fork)*
- **STATE** — Story State, Item & Equip *(the orthogonal save layer — visually fenced off)*
- **SHIP** — Build & Deploy, Co-op *(the dev loop + multiplayer)*
- Home stays the landing; it's not a peer of the rest.

Express the grouping with either (a) a **left activity/rail bar** (VS Code-style icons: Author / Assets / State / Ship / Learn) that swaps the tab set beneath it, or (b) grouped tab rows with separators/section labels. Either removes the overflow **structurally** by never showing all 10 at once, which also fixes F2 without fighting the splitter.
*Trade-offs:* an activity bar is a bigger visual change (users must relearn where tabs went once); grouped rows are cheaper but a `QTabBar` can't natively render separators so it needs a custom tab bar or a two-row layout. Either way, must preserve the Ctrl-K "Go to X" so muscle memory survives. Lowest-risk concrete win: at minimum, **move the tab strip out of the 640px splitter pane to full window width** (host it above the splitter) — that alone kills the clip.

### Option B — A newcomer default view ("Start" mode) with progressive disclosure *(medium risk, directly answers the brief)*
Introduce an app-level **complexity mode** (persist in `prefs.py` beside `theme()`): *Guided* vs *Full*. In **Guided**:
- The tab set collapses to the three a first-timer needs: **Home · Editor · Build & Deploy** (author → the room → make it run). Models/Battle/Co-op/Import/Save move behind a "More…" affordance or the activity rail.
- Home becomes a **stepper**, not a menu: "1. Open or fork a room → 2. Edit it → 3. Deploy & playtest," each step lighting up as the prior completes, driven off the existing mode state (`manifest`/`plan`/`_loose`, shell.py:369-376) and `_current_target()` (shell.py:1260).
- The primary accent CTA points at the *easiest* real start — "Fork a real FF9 room" or "New Field" — not "Open Journey" (invert F3).
*Trade-offs:* tab-hiding is new machinery (the codebase has deliberately avoided it — Chocobo memory note); must be reversible and discoverable ("Show all features"). Risk of a "kiddie mode" feel — mitigate by making Full one click away and never *removing* Ctrl-K access to hidden surfaces. This is the single highest-leverage change against "accessible to less-technical users."

### Option C — Separate author-surfaces from utility-surfaces spatially *(medium risk, resolves F1/F7 cleanly)*
Keep tabs but split the metaphor honestly: the **tab strip becomes ONLY views of the open project** (Editor, Map, and — when a save is open — Story State / Item & Equip appear *as a fenced pair*). The five standalone mini-apps (Import, Models, Battle, Build & Deploy, Co-op) move to a **"Tools" launcher** — either a top-level menu, the activity rail's bottom section, or full-screen panels invoked from Home/palette. This makes the tab strip finally mean one thing ("the open project, from different angles"), and Import/Models/Co-op stop pretending to be project views.
*Trade-offs:* Build & Deploy is used *constantly* mid-author, so it can't be buried — it likely stays pinned (or becomes the breadcrumb-row Deploy's expandable panel). Requires deciding the home for each utility; more re-plumbing than A. But it's the most *conceptually* correct fix for F1.

### Option D — A mode-aware "next step" spine (guided flow overlay) *(higher effort, the north-star for cohesion)*
Layer a thin, always-present **workflow ribbon** under the breadcrumb that reads the current mode and names the *next* legible action(s): EMPTY→"Fork a room / Open a project"; LOOSE field, unsaved→"Save · Deploy(F9) · Playtest"; JOURNEY with unforked arcs→"Fork the arcs" (the exact nudge the journey overview already computes, memory). This turns the five disconnected panels into one felt flow and directly answers F6/F10 — the app stops being "a set of surfaces" and becomes "a process with surfaces." It reuses state the shell already tracks; it's presentation, not new logic.
*Trade-offs:* another horizontal strip competing for vertical space (the breadcrumb + crumb-row already take two); must be collapsible and must never nag a power user. Best shipped *after* A so it has room.

**Recommended sequencing:** **A (structural regroup + full-width strip)** first — it's the cheapest fix for the loudest mechanical complaint (F2) and re-establishes an honest metaphor (F1). Then **B (Guided default)** for the accessibility mandate. **D** as the cohesion capstone. **C** is the ideologically-cleanest but highest-churn — fold its *idea* (fence the save pair, group the utilities) into A rather than doing it as a separate teardown.

---

## 4. What the 2026-06-22 IA audit already fixed — build on, don't repeat

The prior audit (folded into the GUI-makeover memory, "GUI-workflow / IA audit (2026-06-22, DONE)") was a **legibility/wayfinding** pass, not a **structural reorganization** pass. It is complete and *live in the code today* — reconfirmed against current `shell.py`. Do **not** redo:

- **Persistent doc-mode chip + per-tab-truthful breadcrumb** (#1 keystone). `BreadcrumbBar.set_chip` never cleared by `set()` (shell.py:302), `tabs.currentChanged → _on_tab_changed` wired (shell.py:964, 3202), chip = selected-node TYPE via `_chip_for_kind` (shell.py:3166). Off-spine BATTLE/SAVE glyphs (`⚔ ◈`) and per-node `_KIND_HELP` tooltips exist. **"Where am I / what am I editing" is solved — this pass is about the surfaces themselves, not the label.**
- **Clickable encounter→Battle jump** (#2), **visible journey-tier actions** (#3), **a visible toolbar Close** (shell.py:763), **broadened Open-Field filter** — all live.
- **The schema-aware "Start here" Home** (#4) — the card rows (shell.py:1139) ARE the audit's deliverable. Reorg it (Option B stepper), don't rebuild from scratch.
- **Loose-field→parent-campaign upward jump** (#5), **battle pre-aim** (#6), **named-flag labelling + `[[flag]]` editor** (#7) — live.
- **#8 (per-node tree action-bar) was deliberately REJECTED** as clutter — don't resurrect it.
- The audit's own verbatim lessons still bind this pass: *"a glyph alone is not a legible type cue — back it with a word + hover"* and *"always give a visible escape from a mode."* Any new grouping/rail must keep those.

**The gap the audit explicitly did not address — and this pass owns:** it fixed the *breadcrumb lie* (the symptom of "unclear cohesion"), but left untouched (1) the **tab strip's mixed-axis organization** (F1), (2) its **physical overflow inside the 640px pane** (F2 — never even measured for the tab bar; only the toolbar overflow was caught, 2026-07-06), (3) the **absence of progressive disclosure / a newcomer default** (F3/F4 — the memory confirms *"the app has NO tab-level hiding anywhere"*), and (4) **vocabulary teaching at first contact** (F5). Those four are the substance of the new brief and are genuinely new ground.

---

### Key files for the synthesizer
- Tab construction & the 640px-pane overflow root: `ff9mapkit/ff9mapkit/workspace/shell.py:917-965, 995`
- Toolbar (all ~20 actions): `shell.py:742-839`
- Breadcrumb + persistent chip + per-tab truth: `shell.py:285-353, 3166-3231`; `editor/breadcrumb.py`
- Home landing (the reorg target for Option B): `shell.py:1139-1258`
- Ctrl-K palette + command index: `workspace/palette.py`; `shell.py:3267-3319`
- Mode state (drives any "next step" spine): `shell.py:369-376, 1260-1291, 6071`
- Design system (already cohesive — preserve): `workspace/style.py`; `editor/theme.py` (22-key, 7 themes)
- Density evidence for the standalone doc surfaces: `importdoc.py` (24 btn/11 chk/14 input), `savedoc.py` (nested Inspect/Diff/Edit), `builddoc.py`, `battledoc.py`, `modelsdoc.py`, `coopdoc.py`