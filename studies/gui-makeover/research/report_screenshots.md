I now have complete, clean visual evidence across all 10+ screens (both themes), plus confirmation that the header/breadcrumb overlaps in the batch tour were pure offscreen-capture staleness (fresh single-mount captures are pixel-clean). Here is the report.

---

# Workspace GUI Makeover — Visual Evidence & Critique

Rendered the real PySide6 Workspace offscreen (native Windows platform, `WA_DontShowOnScreen` + `grab()`), 1400×900, dark unless noted, sample campaign = `examples/stolen-ember` (members HEARTH/TRAIL/CHAPEL). PNGs live in `C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX--claude-worktrees-rung-2-virgin-shore-mint-2bc4f1\e45f115d-1dd0-4853-a2cf-6652513a58c8\scratchpad\shots\`.

**Capture caveat (not a bug):** in the fast batch tour, doc-headers and the breadcrumb showed *ghosted overlapping text* on every surface reached after the first (e.g. `03_editor_cutscene.png`, `07_builddeploy.png`). This is offscreen `grab()` staleness from re-mounting forms without a full repaint cycle — **fresh single-mount captures (`R_cutscene.png`, `R_npc.png`) are perfectly clean.** A real user never sees it. I critique the clean versions. Thumbnails/art are unavailable headless ("previews off") — noted where relevant, not counted against the design.

---

## TOP VISUAL PROBLEMS (ranked)

1. **The whole app is one flat grey plane with zero visual hierarchy** — *every screen.* Toolbar, breadcrumb, tree, tabs, form, inspector, and console all share the same 2–3 near-identical dark surfaces (`bg #1e2127`, `surface #262a31`, `surface_btn #2b3038`) separated only by 1px hairline borders (`style.py:22-142`). Nothing is elevated, tinted, or weighted to tell the eye "start here." A newcomer's gaze has no entry point and no path.

2. **The single accent color is spent on the wrong thing, and semantic color is essentially unused.** The *only* saturated element on most screens is the violet **Info Hub** button (top toolbar) — which implies it is THE primary action, when the real primary actions are Deploy/Build. The accent (`#4c8dff`) otherwise appears only as a selection highlight. The palette ships `success/warn/error/help` (`theme.py:46-69`) but the UI uses them almost nowhere except the Map legend and one Home warning. Color carries no meaning, so it can't guide.

3. **The toolbar is a 12-button wall of identical pills** (`Field▾ Campaign▾ Journey▾ Open Save · Close · Undo · Redo · Save All · Check · Refresh · Lint · Info Hub` + search + gear). All the same size, weight, and (except Info Hub) color. A less-technical user faces 12 equal-looking choices with no grouping into "open / edit / validate / deploy." Decision paralysis at the very top of the window.

4. **10 peer tabs overflow the tab strip and can't all be seen at once.** On `01_home_dark.png` at 1400px the strip shows Home…Build & Depl**[clipped]** and hides **Import** and **Co-op** entirely; other shots show a left-clipped "…Cs" (Editor — NPCs) and scroll arrows. Ten flat, ungrouped tabs (`shell.py:928-960`) is too many to scan, and hiding two of them behind a chevron is a discoverability failure.

5. **Forms are dense monotone stacks with jargon labels and wall-of-text help.** The cutscene form (`R_cutscene.png`) fires help like *"the DIRECTOR GATE: only plays when the ScenarioCounter == this beat"* and labels *Requires beat / Then set beat / Cast* with no plain-language framing. Every row — label, field, hint — is the same ~11–13px weight and color, so 6 fields read as one gray brick. No grouping of related fields (id/name/area vs. text-block/title/location sit in one undifferentiated column).

6. **Empty states are stark voids, not on-ramps.** Story State and Item & Equip (`10_story_state.png`, `10b_item_equip.png`) fill the entire central pane with a huge **black console box** and one line of hint, while showing inert Inspect/Diff/Edit sub-tabs. Battle (`08_battle.png`) shows **two competing empty-state sentences** *plus* a full column of dead action buttons (Add enemy slot, Add AI phase…) with nothing open. These are the moments a newcomer most needs guidance, and they get the least.

7. **Inspector and Home are undifferentiated text blobs.** The Inspector rollup (`05_inspector.png`) is flat prose — *"source: real field 557 · mode: borrow / contents: 1 NPC… / → exits to: TRAIL"* — labels and values share one style, and terms (borrow, source real field 557, BGM) are unexplained. Home (`01_home_dark.png`) opens with three prose paragraphs before the first actionable card, and only one card (Journey) sits above the fold.

8. **Inconsistent icon language; no real iconography.** Home mixes monochrome geometric glyphs (◆ ▣ ● ⚔ ⤵ ◈) with one full-color emoji (🧍 Models) — a jarring set (`shell.py:1190-1206`). The toolbar has no icons at all. There's no consistent glyph system tying tree ▸ breadcrumb ▸ tabs ▸ Home together into "one app."

9. **The bottom Problems·Output dock eats ~30% of height while empty.** On first run (`01_home_dark.png`) two large empty panels with placeholder text dominate the lower third before any build has run — vertical budget spent on nothing.

10. **The most important action — Deploy — is the easiest to miss.** `▸ Deploy F9` is a small un-accented dark button isolated on the far-right of a thin breadcrumb strip (`04_map.png`), and in light theme (`12b_editor_light.png`) it nearly disappears (light-on-light, no contrast). The one button that ships work to the game reads as the least important.

---

## Per-screen critique

### 1. Home — first run · `01_home_dark.png`
- Opens with a 22px title then **three stacked prose paragraphs** ("Nothing open yet…", the templates warning, "Start at any level…") before the first card — text-first where a newcomer needs choice-first.
- Only the **Journey** card clears the fold; Campaign/Field/Battle/Import/Models/Save cards are all below it. The primary orientation surface is mostly scroll-to-see.
- Glyph set is inconsistent: ◆ ▣ ● are thin monochrome, 🧍 (Models) renders as a full-color emoji — breaks the visual language.
- The **RECENT** list shows long truncated absolute paths (`…\rung-2-virgin-shore-mint…`) — visual noise; the useful bit (project name) competes with path clutter.
- Right **Inspector** panel is a large empty column ("Select something on the left.") — ~25% of the window is dead on the screen a newcomer lands on.
- The lone accent element is the violet **Info Hub** button up top; the Home page's own recommended action ("Journey ▸ Open…", the accent-blue button) competes with it for "the colored thing = the thing to click."

### 2. Editor — Field form · `02_editor_field.png`
- Clean, conventional right-aligned-label form (Field ID / Name / Area / Text block / Title / Location). This is the app at its most legible.
- But **six identical rows in one flat column** with no grouping — identity fields (ID/Name/Area) aren't visually separated from optional/advanced ones (Text block/Title/Location).
- Hints (*"leave at 1073 unless you know you need another"*, *"must be >= 10 (lower areas don't render in-game)"*) are the same muted size as everything — they blend into the field labels instead of reading as secondary.
- Label **"Text block"** and value **30102** mean nothing to a newcomer; no tooltip-vs-hint distinction, no "what is this?" affordance.
- Big empty gap between the right-aligned label and the very wide input — the eye travels a long blank corridor per row.

### 3. Editor — Cutscene sub-editor · `R_cutscene.png` (clean re-capture)
- Header help is a **5-line jargon paragraph**: *"a CAST (actors = [names]) lets steps walk/animate those NPCs… Gate it to a story beat (requires scenario)… the story-event director."* This is the single most newcomer-hostile block in the app.
- Field labels are engine-speak: **Requires beat / Requires flag set / Then set beat / Then warp to field**, each with a dense hint (*"the DIRECTOR GATE: only plays when the ScenarioCounter == this beat"*). No progressive disclosure — advanced story-machine controls sit at the same level as "Cast."
- The one interactive checkbox (**Play once**) is a small accent square with hint "off = replays every visit" — fine, but visually identical weight to the scary beat fields.
- Notably the *ordered step list* (the actual choreography, "4 steps") isn't visible above the fold — the scary gating fields are what greet you first.

### 4. Editor — NPC entity · `R_npc.png` (clean re-capture)
- The best-worded form in the set: header *"People who stand in the room: a model (preset), a line of dialogue, optional story gate."* — this is the plain-language tone the whole app needs.
- Still: **Model id / Animset id** rows labeled "advanced" sit inline at equal weight with Name/Preset/Dialogue — advanced fields aren't collapsed or de-emphasized.
- Nice touch: a monospace **"On-screen preview — how it wraps in the FF9 window"** box under Dialogue. But it's a bare mono block with no device framing, so it doesn't *read* as a preview.

### 4b. Editor — list group header · `03c_editor_group.png`
- Mounting a list group shows a lone **"+ Add NPC"** accent button floating above the previously-mounted form. Sparse; the group-header state doesn't establish "you are looking at the collection of NPCs" — it's just a button in space.

### 5. Map — campaign graph · `04_map.png`
- One of the stronger surfaces: a clean vertical node chain (HEARTH → TRAIL → CHAPEL), each a rounded card with `id 30100 · borrow`.
- **Legend is a single cramped tiny row** of 6 color keys (entry / needs export / unreachable / open / gateway / gated / seam) jammed at the top — the one place color *is* semantic, and it's rendered at ~10px in a thin strip.
- Huge empty canvas around a 3-node graph — the layout doesn't scale its content to the space (a newcomer sees mostly void).
- Node cards use the accent only for the selected node; unselected nodes are grey-on-grey, so the graph reads faint.

### 6. Inspector — populated · `05_inspector.png`
- Flat text rollup: `field id / source: real field 557 · mode: borrow / contents: 1 NPC, 1 gateway, cutscene (4 steps), BGM / → exits to: TRAIL / ← reached from: TRAIL / file: … copy`.
- **No visual structure** — labels and values are one color/size; it's a paragraph pretending to be a data card. Key facts (id, exits) don't stand out from filler.
- Unexplained jargon (borrow, real field 557, BGM) with no hover/definition. The cross-ref links (TRAIL) are the only styled elements.
- Capped at 420px but still just runs text down the column; no thumbnail, no icon, no grouping into "identity / contents / connections."

### 7. Import · `06_import.png` / `R_import.png`
- Reasonably grouped (group boxes "Fork a real field" / "Fork mode"), but **radio options carry full paragraphs**: *"Verbatim ships the field's real event script + dialogue WHOLE — it runs the original logic, story gating, real doors and rotating cast… A verbatim fork boots at scenario zero…"* — a wall no newcomer will read.
- Terms with zero scaffolding: *verbatim, re-authorable, scenario zero, [startup] block, rotating cast, [[npc]], Neutralize scripted gestures.*
- Controls are visually fine (radios, a search field + Find…, Preview fidelity), but the **text-to-control ratio is ~4:1** — it feels like documentation with inputs embedded.

### 8. Build & Deploy · `07_builddeploy.png`
- The **cleanest doc surface**: a titled radio group (Deploy / Build only / Wire New Game) + a "New Game entry" group box + a tidy action-button row (Check / Build/Deploy / Revert / Package). Good spacing and rhythm here — a model for the others.
- Still text-dense in the New Game explainer, and the action buttons are all identical neutral pills (the destructive **Revert campaign** looks exactly like **Build / Deploy**).

### 9. Battle · `08_battle.png`
- **Weakest empty state.** Two competing messages: top-center *"No battle map open — Open a battle.toml, or Fork one from a real FF9 battle background."* and center *"Open a battle.toml to tune its encounter."*
- A full left column of **dead action buttons** (Remove selected, Add enemy slot, Add AI phase, Add AI / sequence patch…, Add party/ability tuning…) plus an empty list box are shown with nothing loaded — exposing editing chrome before there's anything to edit. Overwhelming and confusing for a newcomer.

### 10. Models · `09_models.png`
- Model list is a scroll of **cryptic tokens**: `GEO_ACC_F0_BBT · id 240`, `GEO_ACC_F0_BBX · id 238`… A newcomer sees gibberish (friendly names + previews presumably need the game install; "previews off" / empty "Pick a model" box headless).
- Dense three-column layout (search+filters | list | preview + "Edit this model" with a long "Deploy into" path). Functional but intimidating; `710 model(s)` with no category chips beyond an "All groups" dropdown.

### 11. Story State · `10_story_state.png` & Item & Equip · `10b_item_equip.png`
- Both: a **giant black console-styled void** fills the central pane, one "Open Save…" button, inert Inspect/Diff/Edit sub-tabs, and a single hint line at the bottom (*"Open a save to read/edit gil, inventory, equipment, stats, abilities, key items."*).
- The empty state spends the entire canvas on a black rectangle — no illustration, no "here's what a save looks like," no sample. Reads as broken/loading rather than "ready for input."

### 12. Co-op · `10c_coop.png`
- **A model for the rest of the app:** three clear group boxes (Status / Session / Play style), plain-language framing (*"Two-player co-op: you and a friend each see the other's ghost…"*), readable status lines, a copyable session code, and labeled radios. This is what "accessible to less-technical users" looks like — the density and jargon problems elsewhere are *not* inherent to the domain.

### 13. Info Hub / Catalog Library · `11_catalog.png`
- **The best-designed surface.** Left category sidebar with live counts (All 2149, Archetypes 125, Creatures 22, Models 710, Songs 109, Story flags 117…), a searchable middle list, a right detail pane (key/value facts + a ready-to-paste snippet under "Use it"), and a friendly floating **"?"** help button.
- Weakness: the middle list is a **flat wall of near-identical rows** (music000…music022 [song]) with no sub-grouping, icons, or previews — hard to scan 2149 items. The detail pane is a bare key/value table (no visual card).
- This dialog's three-pane + counts + detail pattern is the template the main window's tabs should aspire to.

### 14. Light theme parity · `12_home_light.png` / `12b_editor_light.png`
- Good overall parity — layout, spacing, and forms translate cleanly to the soft-grey light scheme.
- **Contrast failures:** `▸ Deploy F9` (breadcrumb, top-right) is nearly invisible (light button, light bg, no border emphasis); the Output console placeholder and the mono "Build, deploy…" text are very low-contrast on the light log surface.
- The single-accent problem is *worse* in light: the violet Info Hub button is the only saturated pixel on an otherwise white-grey screen, pulling all attention to a secondary action.

---

## QUICK WINS (cheap, high visual impact)

- **Re-rank toolbar color.** Make **Deploy** (and/or Build) the one accent-colored primary; demote Info Hub to a neutral/violet-outline. Reserve the blue accent for the single most important action per context (`style.py` `#accent` + the breadcrumb Deploy button `shell.py`).
- **Group the toolbar** with separators into clusters (Open · Edit history · Validate · Info) instead of 12 equal pills — the `QToolBar::separator` style already exists (`style.py:23`), just use it meaningfully.
- **Give forms a type/weight hierarchy:** make field labels slightly bolder/darker and hints one step smaller + more muted, so label ≠ value ≠ hint at a glance. Pure QSS/label-style change.
- **Fix the two Battle empty-state messages → one**, and hide the dead action column until a battle is open (`08_battle.png`).
- **Replace the black-void empty states** (Story State / Item & Equip) with a centered icon + one-line "what this does" + the Open button, instead of a full-pane black console box.
- **Collapse the console dock by default** when there's no output, reclaiming ~30% height on first run (the collapse mechanism already exists — `_toggle_console`, `shell.py:1109`).
- **Fix light-theme contrast** on the Deploy button and console placeholder (`theme.py` LIGHT `log_fg`/muted; give the breadcrumb Deploy button an accent or border in both themes).
- **Unify the Home glyphs** — drop the lone 🧍 emoji for a monochrome glyph so the ◆▣●⚔⤵◈ set is consistent (`shell.py:1201`).
- **Tighten the Map legend** into a small wrapped chip row (or move to a corner key) and let nodes fill more of the canvas.
- **Lead forms/Import with the plain-language sentence, demote the jargon paragraph** into a collapsible "Details" / "?" — the NPC form's one-liner and the Co-op tab prove the tone works.

## STRUCTURAL (real rework)

- **Establish a genuine elevation/hierarchy system:** distinct surface tiers (page vs. panel vs. card vs. input) with subtle tint/shadow, not just hairline borders, so the eye can parse regions. This is the root cause of "flat grey plane" and touches `theme.py` (add a `surface_raised`/`card` tier) + `style.py` (apply it to inspector card, form sections, map nodes).
- **Reorganize 10 flat tabs into grouped/nested navigation** (e.g. Build/Author/Content/State/Multiplayer, or a left rail with sections) so nothing hides in an overflow chevron and related surfaces cluster (`shell.py:928-960`).
- **Redesign the Inspector as a real data card** — thumbnail + grouped fact rows (Identity / Contents / Connections) with styled labels vs. values and inline "what's this?" for jargon (borrow, mode, source field) — instead of a prose blob (`05_inspector.png`).
- **Introduce a newcomer learnability layer** for the domain vocabulary (journey/campaign/field/fork/verbatim/walkmesh/gEventGlobal/gateway/scenario): hover-glossary or a persistent "?" that defines the term in place. The Catalog's "?" button is the seed; extend the pattern app-wide.
- **Progressive disclosure in forms:** split each form into "Basics" (always shown) and a collapsed "Advanced" (Model id/Animset id/beat gating/text-block), so a first-timer sees 3 fields, not 8. Requires form-spec/grouping metadata in `editor/forms` + the mount logic (`shell.py:_mount_form`).
- **Adopt the Catalog Library's three-pane, count-badged, detail-pane pattern** as the house style for the dense browsers (Models especially, and the empty Battle/Story/Item states) so the app feels like one coherent system rather than 10 differently-organized tabs.
- **Design a real empty-state system** (icon + purpose + primary action + optional "show me an example") shared across Battle/Story State/Item & Equip/Models-preview — currently each improvises (competing text, black voids, dead buttons).