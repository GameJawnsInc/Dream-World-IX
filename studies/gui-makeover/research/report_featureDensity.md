I now have a complete evidence base. Here is my report.

---

# FEATURE SURFACE & DENSITY — Research Report

Scope: the PySide6 Workspace (`ff9mapkit/ff9mapkit/workspace/`, backends in `.../editor/`). Evidence is from the live source: the 10-tab construction at `workspace/shell.py:917-964`, the 112-command CLI at `ff9mapkit/ff9mapkit/cli.py:4595-6366`, and each doc module's section structure.

## The scale problem in one number

The CLI exposes **112 subcommands** (`cli.py`, one `sub.add_parser` each, lines 4595-6366) across **~11 pillar families**. The GUI fronts them through **10 tabs + 1 toolbar + 1 Ctrl-K palette**. That compression ratio is the root cause of the density the user feels — the tool genuinely does a lot, so the reorg must **redistribute**, not amputate.

---

## 1. FEATURE CENSUS

Density rating: ◍ low · ◐ medium · ● high · ⬤ very high. Sources are file:line.

| # | Tab | Fronts (concrete controls) | CLI/pillars behind it | Sections / nesting | Density |
|---|-----|------------|----------------------|--------|---------|
| 0 | **Home** (`shell.py:1139` `_welcome`) | Entry-point cards (Journey/Campaign/Field Open+New, Battle/Import/Models/Save jumps), Recent list, first-run setup banner | Navigation only | Flat card list, width-capped 860px | ◍ |
| 1 | **Editor** (`shell.py:921-929`) | Form for the selected tree node — **18 block specs**: field, npc, gateway, event, chest, sps, encounter, music, party, **playable**, startup, cutscene, marker, flag, choice+option, dialogue, player (`editor/forms.py:53-256`) | novel-field authoring + verbatim-fork editing (`edit`, `logic-map`) | One form at a time, driven by tree selection; scroll host | ◐ (per-node; the whole is large) |
| 2 | **Map** (`shell.py:930`, `mapview.py`) | Campaign graph, nodes render cached room art, click-to-open | campaign structure viz | Single canvas | ◍–◐ |
| 3 | **Story State** (`savedoc.py:30` `StoryStateDoc`) | **3 sub-tabs**: Inspect / Diff / Edit of `gEventGlobal` save flags | `flags`, `flags-inspect`, `flags-diff`, `save-edit` | Nested QTabWidget (`savedoc.py:62-64`) | ● (expert) |
| 4 | **Item & Equip** (`savedoc.py:378` `ItemEquipDoc`) | **2 sub-tabs** Inspect/Edit: gil, inventory, equip, key items, stats, AP, overworld XZ pos | `items-inspect`, `items-set-{gil,item,equip,keyitem,stat,ap}`, `save-edit` | Nested QTabWidget (`savedoc.py:413-414`) | ● (expert) |
| 5 | **Battle** (`battledoc.py:160` `BattleDoc`) | Encounter editor + donor-site picker + donor-AI index table + "Fork a real battle background" | `battle-import/build/scene/ai/seq/actions/patch/telemetry` (9 cmds) | GroupBoxes: donor sites (`:534`), donor AI (`:594`), fork bg (`:858`) + list editors | ⬤ (expert) |
| 6 | **Models** (`modelsdoc.py:45`) | Browse grid w/ rendered previews + Edit-model round-trip + playable battle-animset + deployed list | `model-{export,import,gltf,mint,anim,anim-new,preview,reskin,deployed}`, `playable-anims` (10) | GroupBoxes: Edit (`:167`), animset (`:265`), Deployed (`:343`) | ● |
| 7 | **Build & Deploy** (`builddoc.py:25`) | **6 GroupBoxes**: Build to field, Deploy campaign, Deploy journey, New Game landing, New Game entry, Deploy battle | `build/build-all`, `deploy-campaign/-journey`, `newgame`, `pack` | Kind-detected rendering, 6 stacked panels (`builddoc.py:113-249`) | ⬤ |
| 8 | **Import** (`importdoc.py:24`) | **~8-10 GroupBoxes in ONE scroll**: Fork a field, Fork mode, Background art, Carry-from-real, Fork a region, FF9 region catalog, Read & inspect, import-all archive, 3D-models pointer, Repaint native | `import`, `import-chain`, `fork-report`, `import-all`, `find-rooms`, `repaint-native`, `export-art` | Single QScrollArea, no sub-tabs (`importdoc.py:50`); sections at `:78,272,403,466,530,593,616` | ⬤ (heaviest) |
| 9 | **Co-op** (`coopdoc.py:34`) | Status, Session (host/join), Play-style hot-reload panel | `coop host|join|show` | 3 GroupBoxes (`coopdoc.py:77,94,131`) | ◐ |

**Chrome that carries additional surface** (outside the tabs):
- **Toolbar** (`shell.py:742-839`): 3 hierarchy dropdowns (Field/Campaign/Journey, each New+Open), Open Save, Close, Undo, Redo, Save All, Check, Refresh, Lint, Info Hub, ⌕ search pill, ⚙ gear (Setup/Prefs/Updates/About) — **~14 controls**.
- **Ctrl-K palette** (`shell.py:3267` `_command_index`): ~26 named commands + every tree node + Recent "Reopen" rows.
- **Info Hub** (`forms_qt.py:401` `CatalogLibrary`): a category-sidebar library over the reference catalogs — Models, Archetypes, Creatures, Composites, Props, Items, Battle scenes, SPS, Flags (`model.py:348-349`, `_KIND_LABEL`). Fronts `catalog`, `models`, `archetypes`, `items`, `scenes`, `sps`, `flags`, `animations`, `characters`.

Widget-instantiation density (count of QPushButton/QComboBox/QCheckBox/QLineEdit/QSpinBox/QRadioButton/QGroupBox/addTab per module) confirms the ranking: **importdoc 68**, builddoc 36, savedoc 31 (two docs), modelsdoc 27, battledoc 22, coopdoc 20, forms_qt 15.

---

## 2. OVERLOADED SURFACES (ranked)

**#1 — Import tab (`importdoc.py`) — the single worst offender.**
One vertical `QScrollArea` (`:50`) stacks ~8-10 GroupBoxes with no sub-navigation. It fuses **four unrelated jobs**: (a) fork ONE field, (b) fork a whole REGION/campaign (`import-chain`), (c) browse the FF9 region catalog, (d) bulk `import-all` archive, plus (e) read/inspect maintenance and (f) a repaint-native round-trip and (g) a pointer to Models. A newcomer wanting "clone a room" scrolls past region-forking, archive tooling, and native-repaint HD workflows. The "Fork mode" GroupBox (`:120`) exposes verbatim/editable/native — the single most jargon-dense choice in the app — with no teaching. **This is the top reorg target.**

**#2 — Build & Deploy tab (`builddoc.py`).**
Six co-equal GroupBoxes (`:113-249`) with overlapping-but-distinct semantics: Build-to-field vs Deploy-campaign vs Deploy-journey vs two New-Game panels vs Deploy-battle. The New-Game landing panel is flagged "single-owner" (`:200`) — a footgun that wipes on every campaign re-deploy — sitting visually equal to routine Build. The tab does kind-detection (`:268`) to grey out irrelevant panels, but all six render regardless, so the user always sees five things that don't apply to what's open.

**#3 — Battle tab (`battledoc.py`).**
Mixes an encounter/tuning editor with a raw **donor-site offset picker** (`:534`) and a **donor-AI B_MEMBER index table** (`:594`) — byte-level expert surfaces — in the same pane as "Fork a real battle background." No progressive disclosure between "tune an encounter" (approachable) and "patch AI at a donor offset" (deeply expert).

**#4 — Story State + Item & Equip (`savedoc.py`).**
Each uses **nested sub-tabs** (Inspect/Diff/Edit; Inspect/Edit). Tab-inside-tab is a known IA smell — the outer QTabWidget already competes for the same mental slot. These are inherently expert (raw save-flag bytes, `gEventGlobal`) but present as peers to newcomer-facing tabs.

**#5 — Toolbar (`shell.py:742`).**
~14 actions competing for a 1280px-budgeted bar (the code itself notes overflow-chevron risk at `:814`). Undo/Redo/Save-All/Check/Refresh/Lint are five verbs that a newcomer can't distinguish (Check vs Lint is in-process-validate vs subprocess-validate — a purely technical split).

---

## 3. EXPERT vs NEWCOMER SPLIT

The surface cleaves cleanly. The makeover should **foreground the left column, tuck the right column** behind progressive disclosure / an "advanced" affordance — but keep everything ≤2 clicks (see §4 reachability).

| Should be NEWCOMER-FRONT (learnable, guided) | Inherently EXPERT (keep, but tuck away) |
|---|---|
| **Home** entry cards — already the right instinct (`shell.py:1189-1206`) | **Battle donor-site offset picker** (`battledoc.py:534`) — byte offsets |
| **Make a room** (novel field): `new` → Editor form. Today `on_new_field` (`shell.py:2098`) is a bare destination+name scaffold — no guided "your first room" flow | **Battle donor-AI index table** (`battledoc.py:594`) — B_MEMBER selectors |
| **Fork a field** — the *simple* case (one room, pick art), split OUT from region/archive tooling | **Fork MODE** verbatim/editable/native (`importdoc.py:120`) — needs a teaching layer before it's newcomer-safe |
| **Deploy** — the F9 one-button loop already exists (`shell.py:839`); it should be THE deploy story, with the 6-panel builddoc as "advanced deploy" | **New Game landing** single-owner footgun (`builddoc.py:200`) |
| **Explore the catalog** (Info Hub) — browse models/NPCs/props/items by name (`forms_qt.py:401`) — strong newcomer on-ramp, currently a toolbar button | **Raw `.eb` logic / logic-map**, `lint-eb`, `disasm` — expert only |
| **Map** — visual campaign structure (`mapview.py`) | **Save-flag Diff / gEventGlobal Edit** (`savedoc.py:63-64`) — expert |
| | **`import-chain` region fork** (`importdoc.py:272`) — power-user bulk op |
| | **Models mint / anim-new / reskin** round-trip (`modelsdoc.py:167-265`) |
| | **Co-op Play-style hot-reload** (`coopdoc.py:131`) — advanced multiplayer tuning |

**Cross-cutting learnability gap:** none of the expert surfaces teach the **domain vocabulary** (journey/campaign/field/object, fork/verbatim/editable/native, walkmesh, gEventGlobal, gateway, mesID, deploy). The Home intro (`shell.py:1173`) is the *only* place that defines the journey▸campaign▸field nesting. Terms like "verbatim fork," "donor," "carry," "New Game landing single-owner" appear cold. Any accessibility pass needs an inline glossary / hover-definitions layer — the tooltips exist (e.g. `shell.py:783-806`) but are dense and assume the vocabulary.

---

## 4. REACHABILITY — what must stay 1-2 clicks away

If the default view simplifies, these power-user paths **cannot regress** (they're proven, in-game-validated flows):

- **Fork mode = verbatim/editable/native** — the fidelity spine; must survive a "simple fork" default. Keep as an "advanced options" disclosure on the fork flow, not removed.
- **The F9 / F6 dev loop** — save-all + deploy + in-game reload is the core iteration cycle (`shell.py:839`, deploy button `:873`). Must remain one keystroke.
- **Donor AI / donor-site pickers** (`battledoc.py:534,594`) — the only GUI path to byte-level battle patching. Tuck behind an "Advanced" toggle in Battle, keep reachable.
- **Ctrl-K palette** (`shell.py:3337`) — already the universal escape hatch to any command/node. This is the *reason* the default can safely simplify: anything hidden stays palette-reachable. Strengthen it as the "power user's everything-bar."
- **New-Game re-wire** (`builddoc.py:222`, `newgame`) — must stay reachable because it silently wipes on every campaign deploy (documented footgun).
- **Info Hub** — the reference library must stay a single click (it's the vocabulary/asset teaching surface).

The palette + Info Hub together mean a **two-track design is viable**: a calm newcomer default with everything reachable via Ctrl-K and an explicit "Advanced" disclosure per heavy tab.

---

## 5. CLI-ONLY BACKLOG — EXCLUDE from this makeover's scope

These are proven-in-CLI pillars with **no GUI surface**. The plan must NOT scope them as "makeover" work — they'd be net-new feature-building, a different project. Confirmed by grepping the whole `workspace/` dir (matches were incidental strings, not command flows):

- **OVERWORLD / world-\* — ~29 commands, ZERO GUI** (`cli.py:5245-6011`): `world-terrain/reclaim/coast/transplant/fuse/island/forest/hill/mirror/water/entrance/morphs/minimap/environment/encounters/atlas-*/mesh-*` etc. This is the **single largest CLI-only pillar** — a whole feature domain (custom continents, coastlines, entrances) with no window. The only `world` strings in the GUI are the save-editor's overworld-XZ field (`savedoc.py:121`) and Models' overworld-actor label (`modelsdoc.py:445`) — incidental, not the pillar.
- **Custom music / SFX (`audio-import`)** — no GUI at all (grep empty). CLI-only (`cli.py:5199`).
- **Image → field (`image-field`)** — experimental, no GUI (grep empty). CLI-only (`cli.py:5111`).
- **FMV pipeline** — no GUI (the only `shell.py` hit is a test fixture, `:6892`).
- **New playable character creation** — *partial*: the `[[playable]]` block is form-editable via the Editor (`PLAYABLE_SPEC`, `forms.py:167`), but there is **no guided character-creation wizard**. Treat "a character wizard" as backlog, not makeover.
- **Overload battle hub blocks** (`[difficulty]`/`[rebalance]`/`[deathrules]`) and `[chocobo]` — **TOML-hand-edit only**; no editor form (grep of `editor/forms.py` for these = empty). The Editor covers 18 block types but not these — a form-coverage gap, not a visual-makeover item.

**Bottom line for the synthesizer:** the makeover's canvas is the **10 tabs + chrome + Info Hub + palette** — reorganizing and prettifying the ~83 commands that *do* have a surface. The ~29 world-\* commands, audio-import, image-field, FMV, and the Overload/chocobo TOML blocks are out-of-scope backlog; the plan should explicitly fence them so effort isn't spent "makeovering" windows that don't exist yet. The two highest-value reorg targets are **Import** (split the 4 fused jobs; add a fork-mode teaching layer) and **Build & Deploy** (collapse 6 co-equal panels into a guided deploy + an "advanced" drawer), and the highest-value *newcomer* investments are a real "make your first room" flow and an inline vocabulary/teaching layer over the jargon.