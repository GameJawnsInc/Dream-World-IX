# SUBMENU.md — the dedicated "Folklore" main-menu submenu: build-ready implementation plan

> **Status: DESIGN COMPLETE, NOTHING BUILT.** Produced 2026-07-20 by a 31-agent adversarial workflow
> (5 recon axes / 16 verifications: 12 CONFIRMED · 1 REFUTED · 3 PARTIAL / 4 gap probes / synthesis with
> first-hand re-reads). This plan drives the s45(/s46) engine patch for a first-class Folklore codex
> screen — its own row beside Item/Ability/Equip/Status/Order/Card/Config, opening a stock-NGUI two-pane
> screen (scrollable entry list + detail pane + display window). It SUPERSEDES [PLAN.md](PLAN.md) §3's
> "display-window-in-Key-Items" sketch: the owner chose the dedicated-submenu path. PLAN.md's Layer-1
> data spine (P0) is unchanged and prerequisite.
>
> **Provenance discipline.** Citations marked *(re-read)* were verified first-hand by the synthesis pass
> in the read-only Memoria clone `C:\gd\FFIX\Memoria\Assembly-CSharp\` — specifically `UIManager.cs`,
> `MainMenuUI.cs`, `ItemUI.cs`, `ControlPanel.cs`. Citations tagged *(corpus: M#/recon-#/gap)* are carried
> from the verification/recon/gap-probe passes, which themselves distinguished "read in source" from
> "inferred". No SE bytes — references only.

---

## 1. ROUTE DECISION

**Decision: Route (a) — a genuine new `UIManager.UIState.Folklore` served by a code-built
`FolkloreUI : UIScene`, entered from a runtime-cloned main-menu row (the Party precedent). Reject the
overlay route (b) and shell-reuse route (c).**

**Why not (b), the `MenuUIControlPanel` overlay — verification-forced; it overturns recon's preliminary
hybrid.** Recon initially recommended a hybrid (Party-style row that opens a ControlPanel overlay).
**M4 REFUTED that overlay as a navigable screen.** `ControlPanel` is a plain non-MonoBehaviour with no
`Update`/key-poll and is not registered in `GetSceneFromState`, so the engine's key router keeps
dispatching all keyboard/gamepad input to the still-state-current, now-`SetActive(false)` underlying
scene *(corpus: M4; UIKeyTrigger.cs:629→OnKey\*)*. Its widgets are mouse-only (`AddWidgetCollider` +
`UIEventListener.onClick`, no `ButtonGroupState`/`UIKeyNavigation`), so on a pad/keyboard — the FF9
norm — the cursor can never land on them; and there is no Cancel handler, so pressing Cancel runs the
*underlying* scene's cancel and collapses the submenu instead of dismissing the overlay. **Cost had we
shipped (b): a mouse-only, un-navigable, no-cancel popup — unshippable as a first-class submenu.** The
overlay machinery survives only as a *widget builder* (§2), never as the screen host.

**Why not (c), cannibalize a spare UIState shell.** No clean shell exists: the only enum values lacking
a `GetSceneFromState` mapping are `Initial`/`QuadMistBattle`/`Quit`/`PreEnding` — all transient, no
reusable `UIScene` — while `Cloud`→`CloudScene` and `Card`→`CardScene` map to live features
(UIManager.cs:360-367, *re-read*). **Cost of (c): destroying Steam cloud-conflict handling or Tetra
Master for zero saving**, since (a)'s additions are cheap.

**Why (a) is now cheap (recon over-framed its cost).** Recon called route (a) "the largest surface …
four separate engine sites". The gap probes collapsed the *routing* cost to a handful of precedented
lines (§4); the dominant work is building the scene's widgets, which route (b) would have incurred
anyway. The main-menu ROW has an exact live precedent — the Party submenu is a runtime
`Object.Instantiate` clone, **not** a serialized asset (MainMenuUI.cs:680-716, *re-read*).

**The append-vs-insert sub-decision — APPEND at ordinal 28 + widen `IsUIStateMenu`.** Two gap probes
conflicted; resolved at the source. The netsync probe advised *inserting* `Folklore` inside the
`MainMenu..Tutorial` band "because UIState is never serialized." **That premise is false:** `state` and
`prevState` are serialized fields (UIManager.cs:654-657, *re-read*), so they bake an ordinal into the
Unity scene asset; a mid-enum insert would silently shift the baked ordinal of every member from the
insertion point up. Append never renumbers — `EndGame` is the last member (UIManager.cs:738, *re-read*),
so `Folklore` takes 28. The single compensating edit: 28 falls outside
`state >= MainMenu && state <= Tutorial` (UIManager.cs:626, *re-read*), so `IsUIStateMenu` must gain
`|| state == UIState.Folklore`; its five callers then inherit the fix (MenuFPS, help, pointer,
`ImpactfulActionCount`). The append-vs-insert probe's whole-tree sweep confirms this is the *only*
range/ordinal test on `UIState` and nothing else persists or ordinally-compares a raw `UIState` int
*(corpus: gap)*. **Enum-safety = exactly two lines.**

---

## 2. THE SCREEN

`FolkloreUI : UIScene`. The base is concrete with zero required overrides *(corpus: recon-8; note:
`OnLocalize`/`Awake` are convention/lifecycle methods, NOT `override`s)*; **`SaveLoadUI` is the
structural template** — the cleanest stock two-pane list+detail scene (named `ButtonGroupState` groups,
`Show`/`Hide` overrides that chain a local delegate before `base`, `OnItemSelect` refreshing the detail
as the highlight moves). The widget tree is BUILT IN CODE in a private `Awake` using the runtime-clone
technique `ControlPanel` ships, so **zero new serialized assets** *(corpus: M3 CONFIRMED — the pattern
is live-used by FieldCreator; recon-7)*.

**Donor pieces cloned:**
- **Frame / background / caption / help-bar.** Clone `MainMenuScene.GenericInfoPanel` for the stock
  window frame + caption label (ControlPanel.cs:339-357/410 precedent; the same panel the main menu uses
  for its time/gil box, MainMenuUI.cs:734-757, *re-read*). The help-bar is the stock `HelpDialog` driven
  by each button's `ButtonGroupState.Help.TextKey` — no new widget. Every window sprite is tagged
  `"Window Color"` so `UIScene.DisplayWindowBackground` auto-skins it onto the win_type-aware stock
  atlas at Show *(corpus: recon-9)*.
- **Scrollable entry list (left pane).** Clone `AbilityScene.SupportAbilityListPanel` to obtain a
  `RecycleListPopulator` (ControlPanel.cs:339-357, *re-read*; **M3 CONFIRMED**). Set `table.columns=1`,
  `draggablePanel`, `panel.baseClipRegion`, `ScrollButton`, `itemPrefab`; assign
  `PopulateListItemWithData` (cell = name label + lock/unlock icon — the inherited ability-cell
  structure, restyled in code, NOT a new prefab) and call `InitTableView(entries, 0)`. Each list cell
  carries its own `ButtonGroupState`, so navigation **and the free cursor-move SFX (103)** work with no
  extra wiring *(corpus: ButtonGroupState.cs:547-559)*.
- **Detail pane (right).** A second `GenericInfoPanel` clone: caption = entry name, lore body = a
  wrapped `UILabel` (from the P0 KeyItem `.mes` text), display window docked top-right.
- **Cursor.** Free — `PointerManager`/`ButtonGroupState` drive the pointer from the active group.

**Display window placement + content.** A `UITexture` cell in the detail pane (`mainTexture` accepts any
`Texture`, incl. a live `RenderTexture`). Bestiary → the render-rig RT (below); Places → a pre-rendered
field-art `Texture2D` (no landmark mesh exists — the ceiling for Places); Lore → omit or a decorative
sigil.

**Category treatment (Bestiary / Places / Lore) — L1/R1 bumper paging + a category caption.** The stock
idiom (`AbilityUI` pages characters via `OnKeyLeftBumper`/`OnKeyRightBumper`); adds no widgets: a bumper
updates the caption and repopulates the list (`InitTableView`, cursor→row 0). *Alternative* (visible tab
strip cloned from a stock button row) = more widgets + cursor-group juggling for no functional gain.

**Input / navigation / SFX contract (what makes it feel stock):**
- Groups `"Folklore.List"` (+ `"Folklore.Detail"` if separately focusable) as `private const` strings
  (SaveLoadUI pattern). Directional movement = NGUI `UIKeyNavigation` on the cells.
- `OnKeyConfirm` → SFX 103; locked/sentinel row → 102. `OnKeyCancel` → 101.
- `OnItemSelect(go)` → refresh detail caption/body/display-window as the highlight moves (where the
  render rig re-targets).
- `Show`/`Hide` overrides chain a local after-delegate arming `ButtonGroupState.ActiveGroup =
  "Folklore.List"` + cursor start-select row 0, then call `base`. **Assign `base.FadingComponent` from a
  `HonoFading` child** or the stock cross-fade does not run (SaveLoadUI:693 pattern) *(corpus: recon-9)*.
- `OnKeyCancel` **must** `Hide → ChangeUIState(MainMenu)` — `ChangeUIState` never hides the outgoing
  scene (UIManager.cs:559-599, *re-read*) — and set `MainMenuScene.CurrentSubMenu = SubMenu.Folklore` +
  call `MainMenuScene.StartSubmenuTweenIn()` so the row menu tweens back with the cursor on Folklore
  (MainMenuUI.cs:104-108, *re-read*).

**Display-window render rig (Bestiary 3D) — do NOT use the Libra bridge.** ⚠ CORRECTS PLAN.md §3: the
gap probe proved Libra battle-locked — it re-aims `Camera.main`/`"Battle Camera"` at a live `pBtl` unit
and NREs off-battle (BattleHUD.Public.cs:213-246) *(corpus: gap)*. Libra remains the *pattern* precedent
(camera → RenderTexture → widget), not liftable code. Instead, on entry-selection spawn a
**self-contained, lifecycle-scoped mini-rig**: a new `GameObject`+`Camera` with
`targetTexture = new RenderTexture(w,h,24)`; a **dedicated culling layer** holding only
`ModelFactory.CreateModel(geo)` (battle-agnostic, standalone) + three directional lights (the
`ModelViewerScene.cs:202-217` recipe, which already renders an animated model over a live *field*
scene); animate an idle clip via `AnimationFactory`, rotate slowly; bind the RT to the `UITexture`.
Destroy model/camera/RT/lights on `Hide` and on selection-change (mirror ModelViewer teardown).
*Inference:* confine model + lights to that layer and set `camera.cullingMask` to only it, so neither
the live field/world camera draws the model nor our camera draws the scene.

---

## 3. THE MAIN-MENU ROW

Follow the Party precedent verbatim — a live, shipping runtime clone of an 8th row
(MainMenuUI.cs:680-716, *re-read*):

**Awake (clone + wire):** `Instantiate(this.CardSubMenu)` → the Folklore row; set its child
`UILocalize.key="Folklore"` + `ButtonGroupState.Help.TextKey="FolkloreHelp"`; reparent into the
`SubMenuPanel` `UITable` (**recommend immediately before `Config`**, matching Party's reparent dance so
Config stays visually last); splice the `UIKeyNavigation` `onUp`/`onDown` chain; `localScale=one`;
`UIEventListener.Get(folkloreRow).Click += onClick` (feeds the base router like every row,
MainMenuUI.cs:708-716).

**Layout — the fragile axis (M1).** The Party branch disables the `UITable` and manually
`SetRawRect(201, y, 402, h)`s all rows with alternating 79/78 heights and `y -= h + 8`
(MainMenuUI.cs:696-705, *re-read*). This manual loop is the **only** layout path, **no auto-reflow**.
Generalize it to always run when the Folklore row is present, feeding the full ordered row array
(8 rows without Party, 9 with) through the same stepping.

**Row-set consumers to extend (all identity/string-based → safe):**
- `SubMenu` enum (MainMenuUI.cs:813-824, *re-read*): add `Folklore` before `None`.
- `Show()` color pass (:64-72, *re-read*): null-guarded
  `FolkloreSubMenu…color = IsSubMenuEnabled(SubMenu.Folklore) ? White : Gray`.
- `OnKeyConfirm` (:145-209, *re-read*): `case SubMenu.Folklore:` mirroring the Card/Config arms —
  `NeedTweenAndHideSubMenu=false`, set `submenuTransition.ShiftContentClip` to Folklore's offset,
  `SetState(Normal)`, then `this.Hide(delegate { ChangeUIState(UIState.Folklore); base.Loading = true; })`.
- `GetGameObjectFromSubMenu` (:546-569) + `GetSubMenuFromGameObject` (:571-590, *re-read*): the mapping.
- **The hand-tuned tween constants (named playtest gate, §7).** `shiftFactor` (:138) is
  `PartySubMenu==null ? 1 : 7/8` — i.e. `7/totalRows`, normalizing the per-row `ShiftContentClip`
  constants (98/196/294/490/588/686, ~+98 per row) to the 7-row baseline. With Folklore, `totalRows` is
  8 or 9, so `shiftFactor` must become a function of the true row count, and Folklore needs its own base
  offset (+ Config's shift if Folklore sits above it). A wrong value misplaces the tween-clip —
  cosmetic, not a crash.

**Cursor memory / return / gating:**
- Return-cursor is automatic (`CurrentSubMenu` setter + ButtonGroupState cursor-memorize);
  `FolkloreUI.OnKeyCancel` sets `CurrentSubMenu=SubMenu.Folklore` first. (`RemoveCursorMemorize`
  hardcodes its reset to `SubMenu.Item`, :119 — leave as-is.)
- `IsSubMenuEnabled` needs no edit: `EnabledSubMenus.Count==0 → true` (:360-361, *re-read*) — the row is
  enabled on the full field menu and auto-greys under field-script menu restrictions (save points).
- **Gating:** the row is gated on the `[Folklore] Enabled` ini flag (static bool, **false on stock**,
  s43/s44 convention) — fail-safe vanilla: no row, no scene, no filter unless the mod enables it.

**Label localization — the exact resource a mod ships** *(corpus: M6 CONFIRMED)*: labels resolve through
`Localization.GetWithDefault`. Ship rows in **`<modfolder>/StreamingAssets/Data/Text/LocalizationPatch.txt`**
(CSV; loaded low-to-high across mod folders by `LanguageMap.LoadModText`): a `Folklore`, a
`FolkloreHelp`, one row per caption, **each with all 7 language columns** (missing key → raw-key text,
no crash). Entry **names + lore bodies** do NOT go here — they ride the P0 KeyItem `.mes` files. Net:
the s45 C# carries no user-visible English. (`EventService.FF9Menu_Command` needs **no** edit — field
scripts open the whole main menu; a direct Field()-opens-Folklore MenuId is out of scope/future.)

---

## 4. FILE-BY-FILE CHANGE LIST

**Engine edits**
- **`Global/UI/UIManager.cs`**
  - `:738` enum — append `Folklore` after `EndGame` (ordinal 28). *Append never renumbers; serialized
    `state` (:654-657) makes insert unsafe.*
  - `:626` `IsUIStateMenu` — append `|| state == UIState.Folklore` (5 callers inherit the fix).
  - `:677-703` scene fields — add `public FolkloreUI FolkloreScene;` (code-assigned — a C# patch cannot
    add a serialized asset ref).
  - `:338-394` `GetSceneFromState` — `case UIState.Folklore: return this.FolkloreScene;`. *Mandatory or
    the state resolves null → silent stuck screen.*
  - `:192-198` `Start()` end — construct: `new GameObject` under `MainMenuScene.transform` (inside the
    DontDestroyOnLoad UI hierarchy), `AddComponent<FolkloreUI>()`, assign, null-guard. *The only code
    seam to build+own the scene; `Start` runs once per singleton life (corpus: gap).*
  - `:200-226` `OnLevelWasLoaded` sweep — add `this.FolkloreScene.gameObject.SetActive(false);`.
    **MANDATORY** — the sweep is hand-maintained; omit it and the codex renders over field/battle/world
    after a load *(corpus: gap; sweep re-read :202-226)*.
  - `:99-159` `StateName` — optional `case Folklore:` (debug label).
- **`Global/MainMenuUI.cs`** — row insertion + dispatch + mapping + color + generalized layout, per §3.
- **`Global/ItemUI.cs`** — the Key-Items folklore filter (§5): one guarded `continue` in
  `DisplayKeyItem`'s loop at `:728` *(re-read)*.
- **`Assembly-CSharp.csproj`** — `<Compile Include>` for the new `.cs` file(s), `Memoria.*` namespace
  (s44 convention: `NetSyncField.cs`).

**New files**
- **`FolkloreUI.cs`** — the scene. `Awake` builds the two-pane tree; `Show`/`Hide`; `OnKeyConfirm`/
  `OnKeyCancel`/`OnKeyLeftBumper`/`OnKeyRightBumper` (category paging)/`OnItemSelect`/`OnLocalize`;
  render-rig lifecycle.
- **`FolkloreRegistry.cs`** — reads `FolklorePatch.txt` → map: folklore key-item id → {category,
  Bestiary model geo, Places art resource}; exposes the folklore id **SET** (the ItemUI filter and
  persistence key on it). May fold into FolkloreUI.
- *(Optional)* **`FolkloreRenderRig.cs`** — the Camera+RT+model+lights helper.

**Sidecar + ini**
- **`FolklorePatch.txt`** — mod-shippable registry (Dictionary/BattlePatch line convention): one row per
  entry `<keyItemId> <category> <modelGeoOrArtResource>`. Single source of truth for the entry list,
  category buckets, render-rig model, AND the ItemUI filter set. Read per mod folder, low-to-high.
- **`[Folklore] Enabled`** in `Memoria.ini` — the gate. `0` on stock (no row, no scene, no filter).

**Patch packaging — SPLIT s45 + s46 along the text-vs-render seam (recommended).**
- **s45** = the complete navigable text codex: UIState + `IsUIStateMenu` + `FolkloreScene` +
  `GetSceneFromState` + Start/OnLevelWasLoaded hooks + the row + FolkloreUI (list + detail text +
  category paging) + the ItemUI filter + `FolklorePatch.txt` + ini + LocalizationPatch rows. Complete,
  shippable (a readable bestiary).
- **s46** = the display-window render rig: Camera+RT+model+lights mini-rig, the `UITexture` binding,
  Places 2D art + Bestiary 3D.
- *Rationale:* the rig carries the most playtest-only unknowns (culling-layer collision, teardown
  flicker / the known HonoBehavior-teardown camera hazard) and deserves an isolated slot for clean
  revert; the text codex is independently valuable — one-change-one-gate at patch granularity. They CAN
  collapse into one s45 (near-disjoint files) if atomic delivery is preferred.

---

## 5. KEY ITEMS TAB

**Filter site (M5).** `ItemUI.DisplayKeyItem` (ItemUI.cs:725-748, *re-read*) is the only place the
vanilla Key-Items list is built; the enumeration is at `:728`. Insert:
`if (folkloreFilterActive && FolkloreRegistry.IsFolklore(id)) continue;` — covers both first-populate
and refresh branches (both derive from `_keyItemIdList`, :733-734).

**Config gating — what makes "P0 text-only still works" true.** `folkloreFilterActive =
Configuration[Folklore].Enabled`. In a P0 text-only build (or stock) the submenu is absent, the filter
is OFF, and folklore entries stay visible in Key Items — their only home. Once s45 ships, the filter
turns ON and folklore lives only in the dedicated screen.

**Filter on the SET, not the band (M5 correction).** Key the guard on `FolkloreRegistry.IsFolklore(id)`
— the registered set from `FolklorePatch.txt` — **not** a blind 80-254 range (band-emptiness is
prior-secured but not re-verifiable from loose files; the set is robust even if another mod shares the
band).

**Edge cases — all handled by existing vanilla logic:** all-owned-are-folklore → empty list → the
existing sentinel row (`:730-731`, *re-read*; 255 renders non-interactive, `:756-762`); sentinel 255 is
outside 80-254; `_currentItemIndex`/cursor-memory are rebuilt-per-open + bounds-checked; save/co-op
untouched (display-only filter — ids stay in `rare_item_obtained`).

---

## 6. CORRECTIONS (what verification overturned — blunt)

1. **The overlay is NOT a viable screen** (M4 REFUTED): no input-focus capture, mouse-only widgets, no
   cancel-restore. The screen MUST be a real UIState+UIScene. Overlay machinery = widget builder only.
2. **The Libra render bridge is battle-locked.** PLAN.md §3's "Libra-exact snapshot" is unusable
   off-battle (NREs — needs `Camera.main`/`"Battle Camera"` + a live `pBtl` unit). Build the
   self-contained mini-rig instead (`ModelFactory`/`AnimationFactory` are battle-agnostic;
   `ModelViewerScene` proves the recipe over a field scene). Places-as-field-art **stands**.
3. **APPEND UIState, don't insert.** `state`/`prevState` are serialized (UIManager.cs:654-657) — insert
   shifts baked ordinals in the scene asset. Append at 28 + widen `IsUIStateMenu`.
4. **Route (a) is not "expensive."** Routing = two enum-safety lines + one `GetSceneFromState` case +
   one `Start` hook + one sweep line, all precedented. The dominant cost (widgets) is common to any route.
5. **"Every row consumer accounted for" glossed the hand-tuned constants.** `shiftFactor` (:138) + the
   per-row `ShiftContentClip` constants have NO auto-reflow — a real, named edit + playtest gate.

## 7. RISKS + IN-GAME GATES

**Ranked playtest-only unknowns:**
1. **HIGH — main-menu row layout.** Manual `SetRawRect` loop + `shiftFactor` + `ShiftContentClip`
   constants, hand-calibrated to 7 rows, no reflow. *Gate:* the Folklore row placed/aligned; every other
   row still tweens correctly.
2. **MEDIUM — render-rig culling layer.** *Gate:* only the creature in the window; nothing bleeds into
   the scene behind the menu.
3. **MEDIUM — render-rig teardown.** The HonoBehavior-teardown camera hazard (known from netsync visitor
   mode) applies. *Gate:* enter/leave + change selection many times — no flicker, no orphaned camera,
   no leak.
4. **MEDIUM — two-pane pixel fit.** *Gate:* list scrolls, text wraps, window square at 4:3 + widescreen.
5. **LOW — category paging feel.** *Gate:* Bestiary→Places→Lore reads like AbilityUI's character paging.
6. **LOW — netsync (predicted clean, structurally proven).** s44's KEYON mask is `.eb`-only
   (EBin.cs:1083/1111), disjoint from menu input; mirror-armed guests are walled out of the menu at
   UIKeyTrigger.cs:694; the screen writes no bag/party state. *Gate (confirmation):* two-machine bench —
   host + each non-blocked peer opens/navigates/cancels mid-session.

**Phased build order (one change → one gate; interleaves with PLAN.md P0-P3):**
- **P0 (existing, DLL-free).** Data spine; NO submenu, NO filter; entries appear in vanilla Key Items.
  *Gate:* obtain → visible with name+description; persists across reload.
- **Phase A (s45, change 1 — row + empty shell). ★ GATE PASSED 2026-07-20**
  (`memoria-patches/s45-folklore-submenu.patch`): row placed correctly, help line reads, shell frame +
  caption render, cancel returns with the cursor on Folklore, all other submenus clean. Shell geometry
  deliberately rough (Phase B replaces the panel wholesale). The 4-lens adversarial review caught 4
  real pre-deploy defects, all fixed: the missing `StartSubmenuTweenIn()` on return (HIGH — the row
  column would have stayed collapsed all session; ItemUI calls it in its Hide OVERRIDE — that is the
  idiom), the scene root on Unity layer 0 (culled by the UI camera — a fresh GameObject needs the UI
  layer), the frame-stripping child loop (GenericInfoPanel's root is a bare container; child 2 IS the
  window frame), and a HelpEnabled preference clobber. Parity-when-off verified bit-identical
  (IEEE-float level). Unchecked: the 9-row case (`[Hacks] AllCharactersAvailable = 1` + Folklore).
- **Phase B (s45, change 2 — list + detail text + categories).** Populate from `FolkloreRegistry`;
  `OnItemSelect` detail refresh; L1/R1 paging; flip ON the Key-Items filter. *Gate:* scroll Bestiary,
  page categories, folklore absent from Key Items. *(= PLAN.md P1 realized inside the dedicated screen.)*
- **Phase C (s46, change 3 — 2D display window).** The `UITexture`; Places art; static baked snapshot or
  placeholder for Bestiary. *Gate:* a Places entry shows its art. *(= PLAN.md P1 window / start of P2.)*
- **Phase D (s46, change 4 — live 3D render rig).** The mini-rig; live rotating creature;
  lifecycle-scoped teardown. *Gate:* live, rotating, correctly-lit creature; clean teardown.
  *(= PLAN.md P2+P3.)*
- **Netsync confirmation** folds in after Phase B on the two-machine bench.

---

## Appendix — the six mandatory verification verdicts

- **M1 row insertion: PARTIAL** — mechanism CONFIRMED (the Party clone, MainMenuUI.cs:680-716); caveat =
  the full edit-site list (§3) incl. the hand-tuned tween constants.
- **M2 UIState safety: PARTIAL** — routing safe; caveats = `IsUIStateMenu` must widen (append falls
  outside the range test) and enum+case+construction must land together (a missing case = silent stuck
  screen via null guards at ChangeUIState:572 / UIKeyTrigger:635).
- **M3 list-in-code: CONFIRMED** — RecycleListPopulator wireable by cloning
  `AbilityScene.SupportAbilityListPanel` (ControlPanel.cs:339-357 + ControlList.cs:79-81, live-used by
  FieldCreator); cells inherit the ability-cell structure (restyle in code, no new prefab).
- **M4 overlay route: REFUTED** — see §1.
- **M5 Key-Items filter: PARTIAL** — sound; filter on the registered SET, config-gated (§5).
- **M6 localization: CONFIRMED** — `LocalizationPatch.txt` CSV, low-to-high mod merge, all-7-column rows.

## Phase B record (built + FUNCTIONAL ★ 2026-07-21 — 16 playtest rounds; styling → the menu study)

**What shipped (s45, `FolkloreUI.cs` + the `ItemUI.cs` filter):** the two-pane codex — LEFT = the
**KEY ITEMS LIST donor** (`ItemScene.KeyItemListPanel` clone — M3's ability-list pick was WRONG for
faithfulness: its cells are icon+number bars that fight restyling; the key-items cell is the codex's
exact name-only shape, populated vanilla-style with ZERO restyling) forced 1-column via the engine's
own `GOSubPanel.ChangeDims`, wearing the donor's authentic `CaptionBackground` dressing (sheet +
capped rails; the CATEGORY name sits on the header rail where stock puts "ITEM"); owned = white +
the stock `New!` bang (Confirm clears it via `FF9Item_UseImportant`, save-persistent); locked =
grey `???`. RIGHT = a bordered detail window (frame caption = entry name; lore body ShrinkContent).
Stock `item_bg` backdrop; L1/R1 pages categories; `FolklorePatch.txt` registry (mod-root,
`<keyItemId> <category> [displayRef]`, low→high override); the Key-Items tab filters the REGISTERED set.

**The 16 rounds in one paragraph:** round 1's blank-after-field-load = the orphaned cell template
(RefreshPool wipes-then-throws); rounds 2-3 = anchors re-assert every frame + panel-depth sorting +
the window-color per-row sweep; rounds 4-6 = the donor swap + single column + dressing strip;
rounds 7-8 = the pooled pointer's per-group DEPTH (default 5 = buried) + its SCENE-SPACE limit rect;
rounds 9-10 = the borderless-frame dead end, reversed by resurrecting the donor's own dressing;
rounds 11-13 = chasing constants that were snapshots of NGUI's coupled scroll state
(panel transform + clipOffset); rounds 14-16 = the ChangeDims reshape, the template's row-0 seat
(spawn-position bounds cache), and the SetDragAmount(0,0) FIXPOINT. Full law set →
`~/.claude` memory `project-ff9-ngui-menu-construction` + the memoria-patches README s45 row.

**Open defects (cosmetic, deliberately deferred):** (a) ~3s hang on the FIRST open (the Awake clone
burst — profile before optimizing); (b) row 1 overlaps the top rail (content top = window top; stock
seats rows below the header rail).

**THE PIVOT (user call, 2026-07-21):** stop iterating the screen blind — run a **menu-shape-language
study** first (how stock FF9 menus compose: sheets vs bordered windows, rails/caps, header captions,
row grammars, margins, depth stacks), THEN redesign the codex screen from that vocabulary.
"The way we're going about it now isn't good for discoverability."
