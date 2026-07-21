# GUI-strings audit — master report

**Scope:** the ff9mapkit Workspace (PySide6 desktop app) and its shared editor/help vocabulary.
**Task:** inventory every user-visible *informational / instructional* string (tooltips, placeholders,
captions/hints, guide & concept-card prose, dialog explainers, empty-states, humanized errors, "what-is-this"
links) and judge each keep / fix / shorten / add. Plain button labels, window titles, pure data readouts, and
log lines were excluded unless the label itself teaches or misleads.

This report is the synthesis layer over 8 per-module chunks that were inventoried, fact-checked, and judged
independently. It resolves the cross-chunk issues no single judge could see (duplicated prose, terminology
drift, the same fact worded two ways, contradictory dispositions) and states one canonical wording where the
app disagreed with itself. The machine-applicable subset is in **`fixlist.json`** (37 entries); this document
is the human-readable rationale plus the recommendations that need code, not just a string swap.

---

## 1. What was audited

Eight chunks, all under `ff9mapkit/ff9mapkit/`:

| Chunk | Surfaces |
|---|---|
| shell-a / shell-b / shell-c | `workspace/shell.py` — the Workspace chrome, Home guide, journey/campaign IO, tree + Inspector, cutscene/choice/logic/chocobo editors, deploy status |
| build-import | `workspace/builddoc.py` (Build & Deploy tab), `workspace/importdoc.py` (Import tab) |
| coop-battle | `workspace/coopdoc.py` (Co-op tab), `workspace/battledoc.py` (Battle tab) |
| models-save | `workspace/modelsdoc.py` (Models tab), `workspace/savedoc.py` (Story-State + Item/Equip tabs), `workspace/mapview.py` (Campaign Map) |
| forms-feedback | `workspace/forms_qt.py` (form renderer, CatalogPicker, Info Hub), `editor/forms.py` (field/section/step help specs), `editor/feedback.py` (humanized error layer) |
| help-widgets | `workspace/concepts.py` (concept cards), `workspace/conceptmap.py`, `workspace/palette.py` (Ctrl-K), `workspace/setupdialog.py`, `workspace/tuningdialog.py`, `workspace/hero.py`, `workspace/widgets.py` |

## 2. Counts

- **Strings inventoried & judged:** several hundred (the eight chunks between them dispositioned ~430 items).
- **KEEP (accurate, correctly placed, no action):** the overwhelming majority — roughly 92% of judged items.
- **Actionable string edits accepted:** **24** (7 medium, 17 low) — 15 `fix` + 9 `shorten`. All 24 verified byte-exact against source and written to `fixlist.json`.
- **New teaching strings to add (pure string adds):** **13** (8 medium, 5 low) — in `fixlist.json` as `action: "add"`.
- **Recommendations that need code / a new widget (not in the mechanical fixlist):** **10** — §5 "needs code" items and the two `[?]`-affordances to BUILD in §3.
- **Judge dispositions I rejected or reworked:** **5** (§6) — 1 rejected, 4 narrowed/reworked.

> **Apply note:** every source file is **CRLF**. Multi-line `old` values in `fixlist.json` embed literal `\r\n`
> so they match byte-for-byte; the apply pass must not normalise newlines before matching.

---

## 3. The help-affordance policy

### What the app already has (the established in-place help channels)

1. **Concept cards** (`concepts.py`) — 26 plain-language glossary cards, each a 1–3 sentence explanation plus a
   muted *"Under the hood:"* technical aside. Surfaced four ways: the **"?" badge** on jargon form labels
   (`forms_qt.py:101`), the **Ctrl-K "Learn · &lt;concept&gt;"** rows (`palette.py`), the **"What's a X?"**
   concept nav-link (`shell.py:6982`), and the clickable boxes in the **Concept Map**.
2. **Concept Map** ("How it all fits", `conceptmap.py`) — the fixed node-link diagram of the domain spine, the
   newcomer's mental model.
3. **Tooltips** (`setToolTip`) — the depth channel for *action* controls: preconditions, reversibility, where
   output lands, the "why" behind a bound. Length is allowed here because it is on-demand.
4. **Captions** (`widgets.caption`) — the inline **HINT tier**: wrapped, measure-capped (~74ch) explaining text
   under a control.
5. **Option-consequence captions** (`widgets.option`), **notices** (`widgets.notice`), **empty-state teach**
   text (`widgets.empty_state`) — inline, state-scoped.
6. **Info Hub** (`CatalogLibrary`) — browsable catalogs (models/NPCs/props/items/flags) with Copy name / Copy
   snippet and its own glossary help dialog.
7. **Setup & Health** dialog — the onboarding front door with ✓/⚠/✕ triage.
8. **Humanized error layer** (`feedback._REWRITES`) — plain-language friendly + next-step for raw failures.
9. **Home "Get started" guide + LedeCard** — the goes-away onboarding surface.

The glossary channel is **built and working**; the "?" badge, Ctrl-K Learn rows, and concept map all resolve
against the same `concepts.py` source of truth.

### The rule (one coherent policy for inline vs. behind a [?] / concept card)

- **Inline (caption / option-consequence / placeholder / notice):** the **one next action** plus the **single
  load-bearing constraint or consequence** for *this control, right now*. Kept within the measure (short
  lines). State-gated warnings that disappear once resolved.
- **Hover (tooltip):** depth on an *action* — preconditions, reversibility, the "why" behind a numeric bound,
  where output streams. Allowed to be longer.
- **Behind the [?] / concept card:** the **definition of a domain noun** ("what *is* a walkmesh / fork /
  scenario / .eb"). Any explanation that teaches a *concept* rather than an *action* belongs in a concept
  card, reached from the "?" badge / Ctrl-K Learn / concept map — **not spent as always-visible prose.**

**The recurring defect class this audit keeps hitting** (and the study's own "measure / restraint" law): a
correct caption that carries **implementation lore** or a **concept definition** onto the always-visible work
surface. Examples corrected here: `"a base-0 contiguous GetChoose switch + a [CHOO] row list"` (shell 5911),
`"(the story dispatch)"` (shell 6638), the 470-char verbatim-mode paragraph (importdoc 133). **Fix pattern:**
keep the next-action inline, move the *mechanism* to the hover tooltip, move the *concept* to a card.

### [?] affordances that need to be BUILT (not string edits)

1. **Inspector Camera note → "What's a scene.toml?" link** (`shell.py:7457`, and the editor Camera section).
   The note now says "read-only here" with no route forward. A `field.toml vs scene.toml` concept card already
   exists (`concepts.py:140`); the missing piece is a **concept-link affordance** on the read-only note so a
   user who wants to change the camera can reach it. (The string fix in `fixlist.json` at least names the file;
   the *link* is the build item.)
2. **Multi-`[[cutscene]]` warning → an "Open the .toml" affordance** (`shell.py:6638`). The caption instructs
   "edit the rest in the TOML" but the Workspace offers **no way to open the file** — scenes #2+ are only
   reachable by hand-editing on disk. BUILD an open-file link/button (or GUI editing for scenes beyond #1).

Everything else in this audit is a string edit or a string add.

---

## 4. Cross-chunk resolutions

**R1 — "campaign.toml" vs the three-level model (terminology drift → canonical wording).**
`shell.py:424` and `:548` tell the user to "Open a **campaign.toml**", but the app is journey / campaign /
field, and the post-close status at `shell.py:2867` already says *"open a journey, campaign, or field to
begin."* **Canonical:** the three-level phrasing. Both surfaces are corrected in `fixlist.json` to match 2867.

**R2 — the safe-flag band: `[8712, 16320)` vs `[8712, 16256)` (contradictory dispositions → REJECT the isolated change).**
The forms-feedback judge marked `editor/forms.py:232` (`[8712, 16320)`) *stale* and wanted `16256`
(`COOP_CELLS_FLOOR`), because the co-op cells `[16256, 16320)` are reserved. But the shell-c judge marked the
**same band** *current* where it is interpolated as `[{FIRST_SAFE_FLAG}, {CHOICE_SCRATCH_FLOOR})` — which
renders **`[8712, 16320)`** at `shell.py:3217`, `:7724`, `:7732`, **and inside `flags.py`'s own validators**
(lines 422/427/430). Ground truth in `flags.py`: `FIRST_SAFE_FLAG = 8712`, `COOP_CELLS_FLOOR = 16256`,
`CHOICE_SCRATCH_FLOOR = 16320`; the *truly-safe* band is `[8712, 16256)` (the docstring says so and
`is_safe_custom` excludes the reserved co-op cells), but every displayed surface renders **16320** from the
live constant and the reserved-region check backstops allocation. **Resolution: REJECT** the isolated
forms.py→16256 change — it is the *only* surface that would then say 16256 while every other surface (and the
validator error the user would see) says 16320, i.e. it *creates* drift instead of removing it. The correct
band is `[8712, 16320)` everywhere today. **Open item for the maintainer (out of scope for a strings pass):**
if the displayed ceiling should reflect the truly-safe `16256`, that is a *coordinated* change to the display
convention (the interpolated `CHOICE_SCRATCH_FLOOR` usage across shell + validator + the forms.py literal),
done together — not a one-line string edit. Left unchanged.

**R3 — engine-bundle naming (the same thing called three names → standardize).**
The patched engine is "the small bundled patch set" / "s23–s34 patches" (`concepts.py` Memoria card), "s34
engine patch" (`concepts.py` Overworld card), and "the dwix-custom-memoria DLL bundle" / "dwix-custom-memoria-*.zip"
(`setupdialog.py`). **Canonical name:** *"the dwix-custom-memoria engine bundle."* **Canonical suite ids:**
**s23–s33 = the fork-gate patches**, **s34 = the overworld override**. The concrete factual error — the Memoria
card's *"s23–s34 patches"* — is fixed in `fixlist.json` (`concepts.py:122` → *"s23–s33 fork-gate patches"*).
The broader rename to one bundle name across all surfaces is a low-priority follow-up (§5, needs coordinated
wording), not forced mechanically.

**R4 — scenario-zero / `[startup]` guidance stated three times (redundancy → one canonical home).**
`importdoc.py:133` (verbatim-mode caption), `:442`, `:748` (Preview fidelity), `:905` (Import verdict) all
explain "a verbatim fork boots at scenario zero → add a `[startup]` beat." **Canonical homes:** the Preview
fidelity verdict (748) and the Import verdict (905) — the action points where the user just got a suggested
beat. The 133 caption is trimmed to stop re-teaching it in always-visible prose.

**R5 — version literal drift (self-contradiction → single source).**
`hero.py:383` paints *"1.0.0b15"* on the Home banner while the status bar and Setup health both read
*v1.0.0b17* (real `__version__`). Fixed to `1.0.0b17`; recommend binding to `__version__` so it cannot
re-stale (code follow-up, §5).

**R6 — acknowledged intentional duplication (no action).** These repeat by design and are already identical /
scope-distinct, so no drift to fix:
- *"Line break: press Enter, or type \\n.  New window: type [PAGE]."* — `shell.py:6664` (cutscene say editor)
  and `forms_qt.py:242` (form dialogue field). Identical wording; correct.
- *"No save loaded."* / *"Open a save (above) to list its slots here."* — `savedoc.py` 49/57 and 408/415:
  parallel tabs, expected mirror.
- The destructive-save confirm *"This edits your REAL save…"* — `savedoc.py:271` and `:627`: intentional
  cross-tab consistency.

**R7 — minor wording drift, low priority (noted, not fixed).** The Walk-as/Neutralize guard is worded two ways:
`importdoc.py:396` *"Neutralize only applies with a swap."* vs `:891` *"Neutralize rewrites the swapped rig's
gestures, so it only applies with a swap."* Both accurate; the 891 form is the fuller, canonical one. Not
worth a change this pass.

---

## 5. Findings by file (ranked by severity)

Legend: **[E]** = edit in `fixlist.json`, **[A]** = add in `fixlist.json`, **[C]** = needs code / a widget
(report-only, not in the mechanical list).

### `workspace/shell.py`
- **[E] medium · 548** — "Open a campaign.toml to begin." → "Open a journey, campaign, or field to begin." (R1)
- **[E] medium · 3700** — logic-map note: drop the internal "(Phase 2)" dev-label; "edit it by opening a routine below, not here."
- **[A] medium · 2934** — New-field dialog "Camera pitch" (default 48) is a bare number with no unit/range and no error path teaches it. Add a caption/tooltip.
- **[A] medium · 2980** — New-campaign "Mod folder" (prefilled FF9CustomMap) is unexplained. Add a tooltip/caption.
- **[E] low · 424** — "No campaign open …" → three-level phrasing (R1).
- **[E] low · 1092** — Close tooltip: drop the emphatic "the way OUT of any journey / campaign / field"; keep "works from any tab".
- **[E] low · 1123 (Refresh tooltip)** — trim the redundant "(only the scene side is re-read)".
- **[E] low · 2905** — area error cites "CLAUDE.md §7" (internal doc) → "single-digit areas black-screen the game".
- **[E] low · 4758** — group-node header: drop the navigation clause that restates on-screen affordances.
- **[E] low · 5911** — choice-menu add dialog: strip "(a base-0 contiguous GetChoose switch + a [CHOO] row list)" implementation lore (mechanism stays on the tooltip at 5639).
- **[E] low · 6638** — cutscene warning: drop the "(the story dispatch)" aside; "edit the rest in the TOML".
- **[E] low · 7457** — Inspector Camera note: name the sibling scene.toml instead of dead-ending at "read-only here".
- **[A] low · 2497** — optional story-beat inputs (also 2554, 3106): add "Leave blank unless a fork/report gave you a beat number."
- **[A] low · 5395** — Chocobo timer seed: "difficulty" is referenced but never defined; add a muted hint that difficulty is a runtime value and the preview is a floor.
- **[C] medium · 6638** — BUILD an "Open the .toml" affordance so cutscene scenes #2+ are reachable (see §3).
- **[C] medium · ~2495 (New-journey / Add-journey dialogs)** — Hub field id (4600) and Entry field id (4100/2495) accept bare numbers with no band hint and — unlike New Field — no validation ever fires. Add "(custom band 4000–32767)" captions AND OK-time validation mirroring lines 2906–2907. (Needs validation code.)
- **[C] medium · ~4995 (edit-value dialog, dialogue-line site)** — the multi-language overwrite warning only shows when `site.note` is truthy; a note-less dialogue site silently overwrites all localized .mes copies. Show a fixed caption *"This replaces the line in every language."* unconditionally. (Needs the guard removed.)
- **[C] low · 2357** — the "fork manually" dead-end arc row: add the concrete per-arc `import-chain` command. (Per-arc dynamic string.)
- **[C] low · ~5455 (Chocobo prize-slot dialog)** — one "Value" field serves Item/Gil/Nothing with no static per-mode guidance; add a mode-dependent placeholder ("item name or id" / "gil amount"). (Needs mode-driven code.)
- **[C] low · 7457 (Inspector Camera)** — BUILD a "What's a scene.toml?" concept-link so the read-only note has a route (see §3).

### `workspace/builddoc.py`
- **[A] medium · 169** — "Build only — to a folder" is the only one of four destinations with **no** inline caption (its meaning surfaces only after selection). Add a `widgets.option` caption matching 177/180/183.
- **[C] low · ~300–317** — on an installed / no-tools copy, the Advanced "Deploy battle map" box gives no "(dev repo only)" marker (only the after-the-fact rejection dialog explains it). Mirror the Test-slot pattern. (Needs the has_tools conditional.)

### `workspace/importdoc.py`
- **[E] medium · 133** — verbatim-mode caption: ~470-char run-on → trimmed; scenario-zero/`[startup]` guidance kept only at 748/905 (R4).
- **[A] medium · 205** — the Fork-a-field card has a *source* "field id" at the top and a *destination* "Field id: 4003" below; both read as "field id". Add "The new fork's id and name — not the source field above."
- **[E] low · 559** — soften the UNVERIFIABLE "~2–3 GB / ~500 MB" figures to an estimate.
- **[E] low · 567** — soften the UNVERIFIABLE "~15–20 s / ~2–3 GB" figures; keep the verified skip behavior.
- **[A] low · 159** — the "Real dialogue, verbatim" + "editable [[npc]] stubs" checkboxes are alternatives; add "Pick one dialogue strategy: carry the real lines, or re-author them as stubs."

### `workspace/coopdoc.py`
- **[E] medium · 308** — the 7-line bottom hint: trim (its tail triplicates the caption at 272 and the log at 549). *Kept the hardcoded `30003` as a plain string: this caption lives in `_build_ui`, which does **not** import `coop` at that scope, so a `{coop.COOP_FIELD}` f-string would `NameError`. Swapping to the runtime constant is a code follow-up (add a local `from .. import coop`).*
- **[A] medium · 282** — "Stop bridge" and "Disable co-op" both mean "turn co-op off" with no distinguishing tooltip. Add: "Stops the local relay — co-op stays configured in Memoria.ini; press Start co-op to reconnect."
- **[A] medium · 284** — "Disable co-op" tooltip: "Turns co-op off in Memoria.ini and stops the bridge — the game reverts to solo."
- **[A] low · 263** — clarify Start-vs-Apply ("Start co-op already uses these settings — Apply only pushes changes to a game that's already running").

### `workspace/battledoc.py`
- **[A] medium · 251** — the battle-pane Check button has no tooltip; the Check-validates-but-Save-persists distinction lives only in code comments. Add "Check for problems without saving — results go to the Problems dock. Save writes your changes to the battle.toml."

### `workspace/modelsdoc.py`
- **[A] medium · 289** — the "Custom playable's battle animset" section renders for every browser selection but operates on a chosen field.toml's `[[playable]]` block, not the highlighted model — "Export donor .glb" is a real trap. Add "Works on a field.toml's [[playable]] block — not the model selected above."
- **[E] low · 345** — drop the exclamation on the work-surface success string "(active action only!)".
- **[E] low · 646** — file-dialog title "The edited {name}.png file(s)" leaks an un-interpolated template brace → "The edited reskin PNG(s)" (the name-keeping rule is taught at 233/636).

### `workspace/savedoc.py`
- **[E] medium · 105** — Compare placeholder wrongly implies a second save is *required*; it falls back to a two-slot diff of the same save (line 258). Reword to name both modes.
- **[E] low · 614** — Editing-target label: drop the field enumeration that restates the section titles + status bar (429); keep the shared-equipment-record caveat.

### `editor/forms.py`
- **[E] low · 121** — chest opened-flag hint: trim the "Not auto-allocated … resilient to reordering" rationale tail (overflows the measure); keep required-ness + the two valid value forms.
- **[E] low · 264** — grammar: "(an debug-menu warp" → "(a debug-menu warp".
- **[REJECTED] · 232** — see R2; left at `[8712, 16320)`.

### `workspace/forms_qt.py`
- **[E] low · 101** — "What's a {c.title.lower()}?" misreads for acronym/technical titles ("What's a mes?") → "Open the {c.title} concept card" (case-preserving, article-free).
- **[A] low · 445** — CatalogPicker browse mode: Copy name deliberately does NOT close the dialog and nothing signals it. Add "Copy name keeps this open — close when you're done."

### `workspace/concepts.py`
- **[E] medium · 122** — Memoria card aside: "s23–s34 patches" → "s23–s33 fork-gate patches" (s34 is the overworld override; R3). *Fixed on the engine-term line only — the card body is accurate and the renderer adds the "Under the hood:" prefix, so it must not be baked in.*

### `workspace/hero.py`
- **[E] medium · 383** — stale banner version "1.0.0b15" → "1.0.0b17" (R5). Recommend binding to `__version__` (code follow-up).

### `workspace/palette.py`
- **[E] low · 101** — Ctrl-K placeholder: promote the buried glossary route → "(a field, a command, or a concept to learn)".

### `workspace/tuningdialog.py`
- **[C] medium · lede (line 66)** — the dialog silently drops hand-authored blocks (`[[learn]]`, `[[status_set]]`, `[[ability_feature]]`, `[[magic_sword_set]]`) and only explains itself in the malformed-block warning. Append a clause to the lede naming which tables show here and which are edited in the TOML directly. (Appends to existing prose; verify exact source before applying.)

### cross-file
- **[C] low — engine-bundle name** — standardize on "the dwix-custom-memoria engine bundle" across `concepts.py` (Memoria + Overworld cards) and `setupdialog.py`, citing s23–s33 (fork gates) / s34 (overworld) where a number is used (R3).

---

## 6. Judge dispositions I rejected or reworked

1. **REJECTED — `editor/forms.py:232` (`[8712, 16320)` → `16256`).** Cross-chunk contradiction: every other
   surface renders `[8712, 16320)` from the live `CHOICE_SCRATCH_FLOOR`, so the isolated change would create
   drift, not remove it. Full reasoning in **R2**; the underlying "should the displayed ceiling be 16256?"
   question is logged as a coordinated, out-of-scope follow-up.
2. **REWORKED — `concepts.py` Memoria card (help-widgets).** The judge proposed rewriting the whole card body
   *and* aside and baking a "Under the hood:" prefix into the text. But the card **body is accurate**, and the
   renderer (`concepts.py:33`) already prepends "Under the hood:". The real defect is one stale token in the
   *engine-term* field. Narrowed the fix to `line 122` only: "s23–s34 patches" → "s23–s33 fork-gate patches".
3. **REWORKED — `shell.py` Refresh tooltip (shell-a, line 1120/1123).** The judge's replacement reworded the
   whole tooltip ("updates"→"refreshes", etc.). Kept the change minimal and faithful to the stated rationale
   ("trim the redundant clause"): removed only "(only the scene side is re-read)".
4. **NARROWED — `hero.py:383` (help-widgets).** The judge wanted the literal bumped *and* the value bound to
   `__version__`. Applied the string bump (b15→b17) now; the `__version__` binding is a code change, logged as
   a follow-up rather than forced through a string edit.

5. **NARROWED — `coopdoc.py:308` (coop-battle).** The judge proposed swapping hardcoded `30003` for
   `{coop.COOP_FIELD}`. Verified this would **break at runtime**: the caption is built in `_build_ui`, which
   does not import `coop` at that scope (the module imports `coop` *locally per-method*, e.g. lines 340/412),
   so the f-string would `NameError`. Applied the trim only, kept `30003` as a plain string, and logged the
   constant swap as a code follow-up.

---

## 7. How to apply

`fixlist.json` drives the mechanical pass: 24 `edit` + 13 `add`. Each `edit`'s `old` was extracted verbatim
from source and verified to occur exactly once; multi-line `old` values contain literal `\r\n` (files are
CRLF) and must be matched without newline normalisation. `add` entries carry `old: null`, an anchor `line`,
and a `note` naming the widget/attribute and location. The `[C]` items in §5 and the two `[?]` builds in §3
are **not** in the fixlist — they need validation logic, a new widget, or a concept-link wire, and should be
handled as code changes.
