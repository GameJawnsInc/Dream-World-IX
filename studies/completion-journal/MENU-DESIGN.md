# JournalUI — the in-game Journal menu screen (design proposal, awaiting owner ratification)

> **Status: ★ RATIFIED (owner, 2026-08-26) — building.** All four questions in §4 answered as
> recommended: Folklore HIDDEN entirely; the 3 tabs STORY / SIDE QUESTS / RECORDS; unreached
> sections render "????" (SC-gated); the story tab is MERGED (NOW banner + section checklists in
> one). The owner directive: replace Folklore's main-menu row with Journal; fit the stock UI while
> staying a modern, efficient UX. The laws this build must honor:
> [[project-ff9-ngui-menu-construction]] (PRESERVE-THE-BAKE, SCROLL-SUM, the group ladder, the
> title-plate/collapse law) and `studies/menu-shape-language/VOCABULARY.md` (the shape inventory).

## 0. What is already proven that this reuses

Every structural piece has an in-game-proven precedent — **this screen is a recomposition, not an
invention**:

| need | proven piece |
|---|---|
| a main-menu row that descends to a custom screen | the s45 9-row squeeze (count-generalized pitch; Folklore's row IS the seat we take) |
| the screen skeleton (cloth, title-plate, help bubble) | FolkloreUI (s45), the title-plate/collapse law |
| a scrollable name-row list | `sheet_with_rails` — KeyItemListPanel donor, `GOScrollablePanel.ChangeDims` |
| list-next-to-detail | pattern 2, persistent hover-driven side pane (Chocograph `HintContentPanel`) |
| framed detail panes, stacked | `GenericInfoPanel` / `BuildFramedPane` xN (the Equip-screen split) |
| focus/navigation | the group ladder (no screen stack; cancel walks up a tier; cursor memory per group) |
| kit-authored data reaching the DLL at runtime | **s45's `FolklorePatch.txt` read via `AssetManager.FolderLowToHigh`** |
| the live reads | the same stores the `.eb` reads, natively: `EventState` (SC, gEventGlobal), items, minigame |

## 1. The data plumbing (the load-bearing decision)

**The DLL never bakes catalog content.** The kit emits **`JournalPatch.txt`** (TAB-separated
records — **NOT JSON**: the game's Unity-5.2 Mono profile throws `TypeLoadException` the moment a
method referencing the Managed Newtonsoft-13 types is JITted, measured in-game 2026-08-26; the
first M1 cut shipped JSON and blanked the screen) into the mod folder at deploy — sections (id/title/objective/sc window), entries (predicate/bit/item/gil/th/
missable/detail), deferred bits — generated from `data/journal_catalog.toml` by the same
single-source machinery the bench uses (`journalcatalog.py`). JournalUI parses it at `Show()`.

Consequences: catalog authoring (the massive prose project) iterates with **zero DLL rebuilds**;
the schema's laws stay enforced at kit lint time; the DLL's job shrinks to *rendering + reading
engine state* — the smallest possible new C# surface (THE DEFECT FOLLOWS THE AUTHORSHIP).

Display names stay LAW-5 runtime: the DLL renders item names via `FF9TextTool.ItemName/
ImportantItemName/CardName` off the id in the record — never a baked string.

## 2. The screen shape (proposed)

**One screen, three tabs**, bumper-paged like stock category rails (SFX 1047), landing on Story:

```
[ STORY ]  [ SIDE QUESTS ]  [ RECORDS ]        <- row_bar rail, bumpers page
+---------------------------------------------------------------+
| NOW: Kidnap Princess Garnet                    <- the objective|
+--------------------+------------------------------------------+
| The Prima Vista &  |  == section detail (hover-driven) ==     |
|   Alexandria    <  |  OK  47 Gil     Cargo hold, at the meeting|
| Evil Forest        |  OK  Potion     Also in the cargo hold   |
| Ice Cavern         |  --  Phoenix Pinion  Engine room ...     |
| Dali               |  ...                                     |
| (scrolls, 44 rows) |  Treasures 2/30      <- the section tally|
+--------------------+------------------------------------------+
|  help bubble: contextual                                      |
```

- **STORY** — the main quest. Top banner: the NOW objective (the round-8 ladder, read natively
  from SC). Left: the 44 main-path spine sections (`sheet_with_rails`), the current section
  highlighted, completed-tally per row. Right: the hovered section's entry checklist (marks +
  runtime names + detail prose), scrolling when long — pattern 2, populated on cursor rest.
- **SIDE QUESTS** — the 11 side sections (Chocobo H&C, Chocographs, Stellazzio, Mognet, Frogs,
  Ragtime, Friendly Monsters, Treno Auction, Daguerreo, Quan's, Excalibur II) as the left list;
  right pane = that arc's counter rows (the dashboard's chocobo/minigame/mognet pages, relocated
  to where they belong) + its entry checklist where authored. Same skeleton as STORY — one
  implementation, two data feeds.
- **RECORDS** — the remaining aggregate rows (Tetra Master, Party, Combat & Meta) as framed panes.
  No list; the smallest tab. *(As BUILT, M4: three always-open groups feeding the SAME list +
  counter pane as SIDE QUESTS — zero new UI surface; the owner may still ask for panes.)*

Missable rendering (LAW 4, unchanged): "PERMANENTLY MISSED" only at `confidence = "owner"`;
`derived` renders "Window likely closed"; no verdict text otherwise. *(As BUILT, M5: a
closed-window uncollected row wears the stock warning red; the verdict text leads the help
bubble ahead of the locator prose; `journalcatalog.missable_verdict` and
`JournalUI.MissableVerdict` are the same function, the kit test pins all states.)*

The field bench (30801) stays the dev/experiment surface; the menu is the player surface.

## 3. Engineering shape

- **Patch: s81** (next free), `JournalUI.cs` new + a `MainMenuUI` splice swapping Folklore's row
  (label, descend target, and the `collapseInstantly` seat s45 already wired). Folklore's screen
  class stays compiled — hidden, not deleted (cheap to re-expose later if wanted).
- Build/verify per `building-the-memoria-engine` (backup gate, msbuild flags, sha verify);
  patch-capture per the CRLF/pre-marker rules. NEVER an upstream PR (standing).
- Kit side: `journalcatalog.emit_patch()` -> `JournalPatch.txt`, wired into `deploy_field`/
  `deploy_campaign`'s existing patch-merge lane; a golden test pins the emitted TSV against the
  loaded catalog.
- Rung order (one playtest each): **M0** row swap + empty skeleton opens/closes clean ->
  **M1** STORY tab static (sections list + NOW banner, no detail reads) -> **M2** live marks in
  the detail pane -> **M3** SIDE QUESTS -> **M4** RECORDS -> **M5** missable column + polish.

## 4. Owner questions (blocking ratification)

1. **Folklore's fate** — hidden entirely (proposed), or re-seated later as a 4th Journal tab?
2. **The tab set** — STORY / SIDE QUESTS / RECORDS as proposed? (Alternative: split "Collections"
   out of Records; or fold Records into Side Quests.)
3. **Spoiler policy for the STORY list** — the spine names all 44 sections up front. Proposed:
   sections the save has not reached render as "????" rows (SC-gated, one comparison), so a first
   playthrough discovers the walkthrough as it goes. Or: show everything (it is a completion tool).
4. **Merged story tab** — the proposal folds "where am I" (NOW banner) and the per-section
   checklist into ONE tab. Keep merged (recommended), or separate "Main Story" and "Walkthrough"
   tabs?
