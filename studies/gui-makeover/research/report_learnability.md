I have thorough evidence across the first-run flow, Home, setup/health, tooltips, forms, Info Hub, feedback copy, and the (unlinked) external docs. Here is my research report.

---

# LEARNABILITY & ONBOARDING RESEARCH — FF9 Workspace

**Scope:** the newcomer's path through the PySide6 Workspace, tracing where a non-modder stalls and every domain concept that is assumed rather than taught. Evidence is cited at `file:line`. Product code was not modified.

**Headline finding:** The Workspace is a *well-built IDE for someone who already knows the domain*. Its onboarding surface is **one text-heavy Home page + a diagnostic health panel + one catalog glossary**. There is **no guided first-run, no interactive tutorial, no loadable sample project, and no in-app link to the excellent docs/glossary/tutorials that already exist on disk**. The single biggest lever is that a newcomer is dropped into a 10-tab IDE and told to "pick a starting point" using words (journey, campaign, field, fork, walkmesh, deploy, F6) that are never defined where they first appear. The *frame* around feedback is friendly (`editor/feedback.py`); the *vocabulary* inside it is not.

---

## 1. NEWCOMER JOURNEY — the first 10 minutes

**Launch (`shell.py:8537` `main`).** The window shows, then `startup_update_flow()` (`shell.py:470`) fires a modal: *"Check pypi.org once a day for a newer Dream World IX release?"* (`shell.py:478`). **The very first interaction a brand-new user has is a network-privacy consent dialog** — before they have any idea what the app is. On a source checkout this is skipped (`shell.py:473`), but an installed (bundled) user — exactly the less-technical target — hits it first.

**The Home page (`shell.py:1139` `_welcome`).** They land on tab 0, "Home". Content, top to bottom:
- Title "Dream World IX — Workspace" (`shell.py:1158`).
- A status line "Nothing open yet — pick a starting point below." (`shell.py:1277`).
- **If the game isn't configured**, a warning banner: *"⚠ FF9 install not configured — open Setup & health to fix it."* (`shell.py:1286–1290`, driven by `health.quick_issues()` `health.py:130`). This is the *only* nudge toward setup; it is one amber line the user may skim past.
- A one-sentence concept explainer: *"Start at any level — they nest (journey ▸ campaign ▸ field ▸ object), but none requires the one above. A journey is the front door…"* (`shell.py:1173–1175`). This is **the entire conceptual onboarding.** It uses four undefined nouns in one sentence.
- Six entry-point cards (`shell.py:1189–1206`): Journey / Campaign / Field / Battle / Import / Models / Save, each with a one-line description and Open…/New… buttons.
- Footer: "Press Ctrl-K to jump anywhere · Close returns here." (`shell.py:1208`).

**Where they stall — a realistic trace:**

1. **"What do I even click?"** The recommended path is Journey ▸ Open (the only accent-colored button, `shell.py:1190`), but a newcomer has no journey to *open* and doesn't know what one is. The descriptions ("the whole arc," "a connected chain of fields," "one explorable screen") are circular without a mental model. **Stall #1: no obvious "I'm brand new, start here" action.**

2. **They try "Field ▸ New…"** (the most concrete-sounding). Dialog `on_new_field` (`shell.py:2098`) asks for **Name, Destination, Field id, Area (≥10), Camera pitch**. A non-technical user cannot answer "Area (≥10)" or "Camera pitch" — there is a constraint note ("lower areas don't render in-game," `forms.py:56`) but no explanation of *what an area or camera pitch is or why 48*. The note at the bottom (`shell.py:2115`) says placeholder art is created and "Repaint the layers + author it here" — introducing *layers* and *author* as new undefined verbs. **Stall #2: the first creative action demands engine parameters.**

3. **If the game path isn't set**, the action fails *later* (not at the button), because `quick_issues` only warns; the New/Open buttons are never disabled. Templates-not-extracted and install-not-found surface as a downstream error, not a gate. **Stall #3: failure is deferred and disconnected from the cause.**

4. **They open Setup & health** (if they noticed the banner). `SetupHealthDialog` (`setupdialog.py`) is a **doctor/diagnostics panel** — a grid of ✓/⚠/✕ rows (`setupdialog.py:104–118`) with "Run setup," "Locate game…," "Install engine patches…". This is competent and the copy is decent ("Fix the red rows first," `setupdialog.py:44`), but it reads as *system administration*, not *welcome*. There is no "do this, then this" sequence — it's a status board. **Stall #4: setup is a checklist, not a walkthrough.**

5. **They explore the tabs** (Editor, Map, Story State, Item & Equip, Battle, Models, Build & Deploy, Import, Co-op). Every tab except Home assumes a loaded project. Editor shows "Select a field or an object on the left to edit it." (`shell.py:929`). Story State shows "Open a SavedData_ww.dat (or a Memoria extra-save / save JSON)…" (`savedoc.py:68`). Import's intro is dense with unexplained terms: *"Fork a single real field… FBG-name substring (e.g. 100, grgr, alxt_map016)"* (`importdoc.py:57,82`). **Stall #5: the tabs are empty rooms that name jargon at you; none teaches what it's for.**

6. **They find the Info Hub** (violet toolbar button, `shell.py:803`) — the one genuinely explorable, no-commitment surface (`CatalogLibrary`, `forms_qt.py:401`). It has a "?" glossary (`forms_qt.py:645` `_show_help`). But it only explains *catalog kinds* (archetype/creature/prop/model/item/scene/song/storyflag/sps, `forms_qt.py:361–379`) — the things you *place by name*. It does **not** explain journey/campaign/field/gateway/walkmesh/deploy. So the newcomer's best exploration tool teaches the *nouns of set-dressing*, not the *structure of the tool*.

**Net:** in the first 10 minutes a curious non-modder can (a) read one paragraph, (b) fail a New Field dialog on engine params, (c) find a diagnostics panel, and (d) browse a model catalog. They cannot: take a guided first action, open a working example to poke at, look up a term they don't know, or watch anything happen. **There is no moment of "I made a thing and saw it work" that onboarding is supposed to manufacture.**

---

## 2. UNEXPLAINED CONCEPTS

Ranked by how early/often a newcomer collides with each. "Explained?" = whether the meaning (not just a usage constraint) is given at the point of first contact.

| Concept | Where first hit | Current explanation | Gap |
|---|---|---|---|
| **journey / campaign / field / object** | Home intro + cards (`shell.py:1173–1206`), tree tooltips `_KIND_HELP` (`shell.py:163–172`) | One circular sentence + one-line card descs; tooltips name the type ("Journey — one playable arc") | **Told, never shown.** No diagram of how they nest/relate; "arc" and "hub" are themselves undefined. Hit within 5 seconds. |
| **fork / verbatim / native / editable** | Import intro & fork box (`importdoc.py:57,129,149`) | Verbatim hint is decent (`importdoc.py:129` "ships the field's real event script… runs the original"); native/editable only via a seams caveat | "Fork" assumed throughout the app (Home card, Ctrl-K, region-fork). The four *modes* are the hardest fork decision and are scattered, not compared side-by-side. |
| **Area (≥10)** | New Field dialog (`shell.py:2113`), `forms.py:56` | "must be ≥10 (lower areas don't render in-game)" | Explains the *rule*, not *what an area is*. First creative action demands it. |
| **Camera pitch** | New Field dialog (`shell.py:2109,2114`) | none (just a default of 48) | Pure engine param on the first-field form. No plain meaning. |
| **walkmesh** | Refresh tooltip (`shell.py:791`), Map, `walkmesh verify` | Only in external GLOSSARY.md (not linked) | Core concept ("where you can stand + depth") never surfaced in-GUI. |
| **deploy / F6** | Build & Deploy tab (`builddoc.py:123,168`), feedback next-actions | "reversible; play via F6 → Warp" (`builddoc.py:123`) | "Reversible" reassures, but **F6 is an in-game debug key on a dev build** — never explained. A newcomer reads "F6 → Warp" as gibberish. |
| **story flag / gEventGlobal / scenario** | Story State tab (`savedoc.py:31,68`) | "gEventGlobal story state (ScenarioCounter + story bits)" | Pure engine jargon as the tab's *self-description*. No plain "these track what the player has done." |
| **gateway / encounter / event / prop / ATE / save point** | object forms (`forms.py:79–146`), Info Hub | Per-field help is good once you're *in* the form; Info Hub covers prop/creature | The *object types* a field contains are never introduced as a set ("a field holds NPCs, gateways, events…"). |
| **text_block / mesID** | New Field form (`forms.py:57`) | "leave at 1073 unless you know you need another" | Punts entirely. Fine as a default, but the label is unexplained noise. |
| **borrow_bg / BG-borrow** | field form (`forms.py:61`), Import | "advanced: reuse a real field's art; leave blank otherwise" | Marked advanced — acceptable — but the concept underlies half the tool (hubs, quick fields). |
| **Memoria / engine patches** | Setup (`setupdialog.py:66`), health (`health.py:84`) | "novel fields run on stock Memoria; FORKED fields need the custom engine bundle" | The stock-vs-custom-engine split is a genuine gotcha (per CLAUDE.md §5). The copy states it but assumes you know what Memoria is. |
| **FBG name** | Import fork box (`importdoc.py:82`) | example only ("grgr, alxt_map016") | The field-name scheme is shown by example, never named/explained. |
| **archetype vs creature vs model vs prop** | Info Hub | **Well explained** in `_HUB_HELP` (`forms_qt.py:361–379`) + "?" glossary | The one concept cluster that *is* taught in-context. Model for the rest. |

**Pattern:** the app has two copy registers. **Per-field help inside forms is genuinely good** (`forms.py` is full of plain, useful hints). **Structural/engine concepts are either absent or stated in engine terms.** The gap is not "no help text" — it's "no help for the concepts you need *before* you reach a form."

---

## 3. RANKED LEARNABILITY GAPS

**G1 — No first-run experience at all (highest impact).** `main()` (`shell.py:8551`) shows the window and (maybe) restores the last session. There is no first-launch detection, no "Welcome, let's get you set up" flow, no gating of actions on setup. The first modal is an update-check consent (`shell.py:478`). A less-technical user gets an IDE and a paragraph.

**G2 — No sample project to explore.** The repo ships rich worked examples — `examples/vivi-hut`, `stolen-ember`, `thirteenth-character`, `continent-v1`, `world_hub` (confirmed on disk) — but **nothing in the GUI opens one.** Home offers only Open…/New… file dialogs (`shell.py:1191–1206`); a grep for sample/example loaders in `shell.py` returns nothing. The fastest way to learn ("open a working thing and poke it") is unavailable in-app.

**G3 — The excellent docs are invisible from the GUI.** On disk: `docs/GLOSSARY.md` (defines every term precisely), `docs/tutorials/` (12 single-goal walkthroughs incl. GUI tutorials 06/07), `docs/TUTORIAL.md`, `docs/FORMAT.md`. **The GUI links to none of them.** The only outbound links are in the About box → GitHub/PyPI/issues (`shell.py:719–721`), and a couple of `docs/JOURNEYS.md` strings buried in generated TOML comments (`shell.py:238`). There is no Help menu, no "Learn" affordance, no "?"-to-glossary except the Info Hub's catalog-only one.

**G4 — Concepts are told, never shown.** The journey→campaign→field→object relationship — the app's central mental model — exists as one sentence (`shell.py:1173`) and as tree nesting. There is no diagram, no visual "here's how these fit together." The Map tab (`shell.py:930`) *does* visualize a campaign's field graph, which is a strong "connect fields" surface, but it requires a loaded campaign and doesn't show the *level* hierarchy.

**G5 — Setup is a diagnostics board, not a path.** `SetupHealthDialog` (`setupdialog.py`) shows status rows and four buttons with no ordering or "next step" affordance. A non-technical user doesn't know Run setup comes before everything, or that "Install engine patches" is only needed for forks. The information is all present (`health.py` advice strings are good); the *sequencing* is not.

**G6 — First creative action demands engine parameters.** New Field (`shell.py:2098`) asks Area/pitch/id up front; New Campaign asks mod folder + id base (`shell.py:2156`); New Journey asks hub_id + borrow_bg (`shell.py:2272`). Sensible defaults exist, but they're presented as blank/decision fields, not "advanced, we picked good values."

**G7 — Feedback frame is friendly; feedback content isn't.** `editor/feedback.py` is a real asset: `Verdict` + `next_action` ("Relaunch once, then F6 → Warp → 2640," `feedback.py:47`) and plain headlines ("Build — 2 problems to fix," `feedback.py:64`). But the `Problem.message` strings come from validators/CLI and carry engine jargon (off-mesh, band-lint, mesID collision). The wrapper teaches "did it work + what next"; it can't translate the errors it's handed.

**G8 — No plain-language reassurance where it matters most.** "Reversible" appears on deploy radios (`builddoc.py:123,168,187`) and the engine-install confirm is excellent ("backed up first — reversible," `setupdialog.py:210`). But Undo/Redo exist without explanation of scope, and the dev-loop safety story (backups, revert scripts) is a CLI concept never surfaced to reassure a nervous newcomer that "you can't break your game."

---

## 4. LEARNABILITY LAYER — concrete proposals

Sized **S** (hours, copy/layout), **M** (a day or two, new widget/dialog), **L** (multi-day, new subsystem). Ordered by impact-per-effort. These build *on* the existing Home/Info-Hub/feedback scaffolding rather than replacing it.

### 4a. Guided first-run — "Let's get you playing" (M, highest ROI)
Detect first launch (a `prefs` flag alongside `restore_session`, `shell.py:662`). Instead of the update modal first, show a **3-step Welcome sheet**:
1. *"Point me at your FF9 game"* — inline the `Locate game…` action (`setupdialog.py:127`) with a live ✓ when valid.
2. *"Extract the base templates"* — the one-click `Run setup` (`setupdialog.py:198`) with a progress line and a plain "~1–2 min, once, non-destructive."
3. *"Open a sample, or make your first field"* — two big buttons → (4b) and New Field.

This reuses everything in `SetupHealthDialog` but *sequences* it and ends on a creative action. Gate nothing destructively — just make the recommended order visible. Defer the update-check consent to *after* Welcome. **Fixes G1, G5, G6.**

### 4b. "Explore a sample project" on Home (S–M, huge for G2)
Add a Home section **"Learn by example"** (a new `_home_section`, `shell.py:1217`) listing the bundled `examples/` projects with a one-line "what it shows" and an **Open (read-only copy)** button that copies the example to a scratch dir and opens it. Suggested first three: *vivi-hut* ("a tiny complete field"), *stolen-ember* ("a 3-field story with cutscenes"), *thirteenth-character* ("a custom party member"). Opening a working project into the real tree/Map/Editor is the single fastest way to build a mental model. **Fixes G2**; synergizes with the Map's existing graph view (G4).

### 4c. In-app concept glossary — extend the Info Hub's proven pattern (M, fixes G3+partly G2)
The Info Hub "?" glossary (`forms_qt.py:645`, `_HUB_HELP`) is the app's best learnability artifact. **Generalize it into a first-class "Concepts" section** that renders `docs/GLOSSARY.md` (already on disk, already excellent) as browsable cards: Field, Walkmesh, Gateway, Encounter, Journey, Campaign, Fork (with the verbatim/native/editable comparison), Deploy, F6, Story flag, Memoria. Add a **Concepts** category to the `CatalogLibrary` sidebar (`forms_qt.py:494`) or a sibling "Learn" tab. Since GLOSSARY.md is maintained, this stays in sync for free. **Fixes G3, most of §2.**

### 4d. "?" affordances on every jargon label — inline "what's this?" (S, broad fixes across §2)
The `forms.Field` dataclass already carries `help` (`forms.py:39`) and `build_form` already renders a hint label (`forms_qt.py:172`). Add an optional **`concept` key** that renders a small "?" next to the field label linking to the matching glossary card (4c). Prioritize the worst offenders: Area, Camera pitch, text_block, borrow_bg (`forms.py:56–61`), and the Story State tab's gEventGlobal/scenario labels (`savedoc.py:31,68`). Also add `?`-to-glossary next to the Import tab's fork-mode radios and "FBG name." **This is the cheapest high-coverage fix** — it's data, not new UI. **Fixes most of §2.**

### 4e. Teach the hierarchy visually — a "How it fits together" panel (S–M, fixes G4)
Replace the single-sentence Home intro (`shell.py:1173`) with a small **nesting diagram**: Journey ▸ Campaign ▸ Field ▸ Object, each glyph (already defined: ◆ ▣ ● , `_RECENT_GLYPH` `shell.py:1293`) with a one-line "is a…" and "contains…". Static SVG/QLabel grid — no new engine. Reinforces that the same glyphs appear in the tree, breadcrumb, and Ctrl-K, so the visual language pays off. Consider linking the Map tab as "see a real campaign's fields as a graph." **Fixes G4.**

### 4f. Empty-states that teach, not just prompt (S, fixes G5-adjacent)
Every non-Home tab currently shows a bare "select/open something" line (`shell.py:929`, `savedoc.py:68`, `importdoc.py:57`). Convert each into a **2–3 line teaching empty-state**: what this tab is for, one plain sentence of concept, and the button that populates it. E.g. Story State: *"Story flags track what the player has done — which chests are opened, which cutscenes have played. Open a save to view or edit them."* This costs only copy + a QLabel per tab. **Fixes G5, part of §2.**

### 4g. Plain-language error translation layer (M, fixes G7)
Keep `editor/feedback.py` as-is (it's good) but add a **message-rewriting pass** in `problems()`/`classify` (`feedback.py:55,85`) that maps known engine phrases to plain-language + "what to do": off-mesh → "This object is placed off the walkable floor — move it onto the walkmesh in Blender or the Map." mesID collision, id-band, area<10, etc. A small dict keyed on substrings, applied when building `Problem` rows. The `next_action` field is the perfect home for the fix. **Fixes G7.**

### 4h. Reassurance microcopy — "you can't break your game" (S, fixes G8)
Surface the existing safety story in plain words where nerves peak: a persistent one-liner near the F9 Deploy button (`shell.py:873`) — *"Deploys are reversible; your game files are backed up first."* And on first deploy, a one-time reassurance toast. The facts already exist (`builddoc.py:123`, `setupdialog.py:210`); they just aren't where a scared newcomer looks. Also add a tooltip explaining **what F6 is** ("an in-game menu on the dev build — press it while playing to reload or warp") anywhere "F6" appears. **Fixes G8 + the F6 gap in §2.**

### 4i. An interactive "Make your first field" walkthrough (L, aspirational)
A coach-marks / stepper overlay that drives the real UI: New Field → repaint hint → add one NPC (Editor) → Check → Deploy → "press F6 in-game." Highest production cost; do it *after* 4a–4h prove the concept vocabulary lands. The bundled example (4b) is 80% of the value at 20% of the cost, so treat this as phase 2.

---

### Where to build on existing strengths (so the plan doesn't reinvent)
- **`editor/feedback.py`** — the Verdict/next-action model is the right pattern; extend (4g), don't replace.
- **Info Hub `_HUB_HELP` + "?" glossary** (`forms_qt.py:361,645`) — the proven in-app-help pattern; generalize it (4c, 4d).
- **`forms.Field.help`** (`forms.py:39`) — per-field help plumbing already exists; add a `concept` link (4d).
- **`docs/GLOSSARY.md` + `docs/tutorials/`** — high-quality, maintained; the job is to *surface* them in-app, not rewrite (4c).
- **The Map tab** (`shell.py:930`) — already a "connect fields" visual; reference it from the hierarchy teaching (4e).
- **Home `_home_row` cards + `_home_section`** (`shell.py:1189,1217`) — the Home is the natural host for the sample-projects and hierarchy-diagram additions (4b, 4e).

**Recommended phase-1 bundle (best step-change for least risk):** 4a (guided first-run) + 4b (sample projects) + 4c/4d (in-app glossary + "?" links) + 4f (teaching empty-states). Together these convert the first 10 minutes from "read a paragraph, fail a form, find a diagnostics panel" into "get set up in order, open a working example, and look up any word you don't know" — which is exactly the "explore, learn, connect concepts" the brief asks for.