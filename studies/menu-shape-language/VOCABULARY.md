# The FF9 Menu Shape Language
### A vocabulary of stock NGUI menu construction (Memoria engine), distilled from a 10-screen + 3-machinery census

> Purpose: name the shapes stock FF9 menus are built from and the rules for composing them, so a new screen
> (the Folklore codex: name-only scrolling list + detail pane + category header) can be written as a sentence
> in the stock language. All citations are `file:line` into `C:/gd/FFIX/Memoria/Assembly-CSharp`.
>
> Two vocabulary-wide facts to internalize first:
> 1. **Almost all geometry is BAKED in the scene prefab.** Code binds it by `GetChild` index chains in Awake;
>    the GO-wrapper constructors (Memoria/Scenes/GO*.cs) are *schema assertions* over that bake —
>    `GetExactComponent<T>` throws unless exactly one exact-typed component exists (ExtensionMethodsGameObject.cs:11-26).
>    The truest runtime record of baked geometry is each screen's `UpdateUserInterface` "original*" constants.
> 2. **There is no auto-layout.** No reflow engine exists. Every runtime re-dimension is either `ChangeDims`
>    (the one list-resize verb, GOSubPanel.cs:42-58) or imperative `SetRawRect`/`SetAnchor` writes — and when
>    rows are inserted (the Memoria Party row) the code hand-lays *every* row and **disables the UITable**
>    (MainMenuUI.cs:717-726).

---

## 1. THE SHAPE INVENTORY

### 1.1 Background cloth (`background_cloth`)
The full-screen backdrop behind every menu.
- **Anatomy:** root UISprite baked as `menu_bg` + child(0) shadow sprite baked as `dialog_hilight`
  (GOMenuBackground.cs:14-15). Memoria conditionally re-sprites to a per-screen name (`item_bg`,
  `status_bg`, …) *only if the atlas contains it*, and re-sprites the shadow to `background_gradient`,
  stretching BOTH to `UIManager.UIContentSize` (GOMenuBackground.cs:19-33).
- **Geometry:** UIContentSize = 1543×1080 pillarboxed, or (1080·aspect)×1080 widescreen (UIManager.cs:653-666).
- **When used:** every censused screen, one cloth each; 13 stock screens pass per-screen alternates, and the
  binding records each screen's baked root-child slot for the cloth (main_menu child 4 — MainMenuUI.cs:819;
  item child 6 — ItemUI.cs:1030; ability child 7 — AbilityUI.cs:1526; equip child 6 — EquipUI.cs:1312;
  config child 8 — ConfigUI.cs:1652; card child 6 — CardUI.cs:488; chocograph child 7 — ChocographUI.cs:418;
  save_load child 8 — SaveLoadUI.cs:716; shop child 7 — ShopUI.cs:1299; status child 10 — StatusUI.cs:456).
- **API:** `GOMenuBackground(root.GetChild(n), "alt_bg_name")`.

### 1.2 The window-weight ladder (four grades of "window")
FF9 has a strict ladder of window chrome, heaviest to lightest. The frame is always **one 9-sliced sprite per
style, never assembled corner caps** — no cap/rail-segment sprite names exist anywhere in code (Dialog.cs:245-254).

| Grade | Anatomy | Wrapper | Users |
|---|---|---|---|
| **Framed dialog window** | children found **by name** (order unstable): `Caption`, `Body`, `Border`, `Shadow`; ctor writes Caption `preventWrapping` + `ClampContent` | `GOFrameBackground` (GOFrameBackground.cs:15-21) | ItemUI arrange dialog (ItemUI.cs:1073), Config warning (ConfigUI.cs:1634), Ability info pane (AbilityUI.cs:1573), Card ×2 (CardUI.cs:612,635) |
| **Caption window** (list header) | `TopBorder`(0) + `Border`(1) + `Body`(2) + optional `Shadow` + a `CaptionPanel` **UIPanel** of 1-4 header labels (Name/Info/Name2/Info2) | `GOScrollablePanel.CaptionBackground` (GOScrollablePanel.cs:28-44, 54-65) | every scrolling list's header rail |
| **Thin sprite window** | Border(0) + Body(1) | `GOThinSpriteBackground` (GOThinSpriteBackground.cs:5-14) | battle Back/Toggle/Run buttons |
| **Thin window** | own UIWidget + child(0) Border only | `GOThinBackground` (GOThinBackground.cs:5-14) | Config slider rows child 4 (ConfigUI.cs:1670), embedded as GONavigationButton child 2 |

**Known census quirk (bug in the wrapper, not the bake):** in CaptionBackground's Shadow branch, Shadow is
constructed from `GetChild(2)` — aliasing Body — despite the branch keying on `GetChild(3)` carrying a
UISprite (GOScrollablePanel.cs:34-36). Treat the intended anatomy as TopBorder/Border/Body/Shadow/Panel.

### 1.3 The scrollable-list compound (`sheet_with_rails`) — THE list shape
Every scrolling menu list in the game shares one invariant PREFAB child triple — 0=ScrollButton rail,
1=SubPanel viewport, 2=CaptionBackground header. `GOScrollablePanel` (GOScrollablePanel.cs:15-17) is
Memoria's typed *accessor* over that shape, constructed for 11 panels; SaveLoadUI and ConfigUI bind the
SAME triple by raw GetChild without the wrapper (SaveLoadUI.cs:70, 696, 717; ConfigUI.cs:1611-1612, 1653).
The triple is the invariant; the wrapper is not universal.
- **child 0 = ScrollButton rail** — UIPanel + ScrollButton; children Up(0)/Down(1) GOSpriteButton,
  ScrollBar(2), IgnoreAreaUp(3)/Down(4) (GOScrollButton.cs:19-26). Behavior: arrows *disable*
  (UIButtonColor Disabled + collider off) at list ends rather than hide (ScrollButton.cs:92-119); hold-to-repeat
  accelerates ×1→×5 with the repeat interval easing 0.2s→0.04s over the ~0.5s→2.5s hold window
  (ScrollButton.cs:281-310); scroll SFX 103 (ScrollButton.cs:170). The whole rail is dimmed to **alpha 0.5**
  as a norm and **0** when the list fits one page (ItemUI.cs:133-134; AbilityUI.cs:207-208).
- **child 1 = SubPanel** — the clipped viewport: UIPanel + UIScrollView + Rigidbody + SnapDragScrollView on
  one object, child(0) = UITable of row buttons, optional `RecycleListPopulator` (GOSubPanel.cs:24-39).
  Two modes: **recycling** (every stock list except one) vs **static table** (Chocograph is "currently the
  only GOSubPanel without list populator", GOSubPanel.cs:74). SnapDrag quantizes scroll to ItemHeight
  multiples via SpringPanel, Speed 24 (SnapDragScrollView.cs:62-84, 106); rows' nav components are disabled
  during momentum and re-enabled on snap (SnapDragScrollView.cs:26-43, 86-102).
- **child 2 = CaptionBackground** — the header rail (see 1.2).
- **Resize API:** `SubPanel.ChangeDims(cols, rows, colW, rowH)` — writes SnapDrag ItemHeight + VisibleItem,
  UITable.columns, `Panel.SetAnchor(null)` then `baseClipRegion = (cols·colW, rows·rowH)` **keeping the clip
  center**, populator cellHeight, prefab `SetRawRect(0,0,colW,rowH)`, prefab ScrollKeyNavigation.ItemHeight,
  RefreshTableView (GOSubPanel.cs:42-58). Static mode instead does per-entry SetDimensions + an end-of-frame
  reposition coroutine with the hardcoded pivotOffset (0, 0.5) chocograph hack (GOSubPanel.cs:59-87).
- **Stock holders:** Item ×2, Ability ×2, Equip, Chocograph, Shop ×3, BattleHUD ability+item
  (ItemUI.cs:1019-1020; AbilityUI.cs:1524-1525; EquipUI.cs:1294; ChocographUI.cs:413; ShopUI.cs:1280-1282;
  BattleHUD.Unity.cs:86-87).

### 1.4 The list ROW (`GOButtonPrefab`) — the selectable cell
- **Components on the row root** (the row IS the button): UIButton + BoxCollider + UIKeyNavigation +
  ButtonGroupState + ScrollItemKeyNavigation + UIDragScrollView + optional RecycleListItem
  (GOButtonPrefab.cs:27-34).
- **Content anatomy** (positional, one indirection: if child(0) has children, content = child(0)):
  optional IconSprite (+UISpriteAnimation), NameLabel, NumberLabel (GOButtonPrefab.cs:36-45);
  NameLabel.fixedAlignment forced true (GOButtonPrefab.cs:46-47).
- **Cell text norms:** base fontSize **36**, label shadow effectDistance **4**, both × (rowH/originalRowH)
  (ItemUI.cs:168-173). Internal anchors are RELATIVE fractions of the row, never absolute px — e.g. Item cells:
  icon .105-.191 x / .184-.816 y forced square, name .215-.795, count .8-.9 (ItemUI.cs:164-171).
- **State grammar:** disabled = label `FF9TextTool.Gray` + `SetButtonAnimation(false)`, row stays clickable,
  confirm plays buzzer SFX 102 (MainMenuUI.cs:64-72, 228-231; ShopUI.cs:805-816). Enabled = White.
  State changes are **atlas-sprite-name swaps**, not tints (Card cells: `card_type{n}_normal/_select/card_slot`,
  CardUI.cs:360-376; Chocograph boxes: `chocograph_box_open/_close/±_null`, ChocographUI.cs:296-333).
- **Name-only row variant (the Key-Item cell — the codex's direct ancestor):** root ButtonGroupState →
  [0] name UILabel, [1] NewIcon UIWidget → NewIconSprite + NewIconLabelSprite; New! badge sprite
  `icon_new_exclamation` until read (ItemUI.cs:1040-1057, 774-783).
- **Menu-row variant (`GONavigationButton`):** Name(0)/Highlight(1)/Background(2) — the highlight sprite sits
  *between* text and window (GONavigationButton.cs:15-35).
- **Empty-list law:** never show an empty list — inject one sentinel row (KeyItemId 255 blank disabled row,
  ItemUI.cs:737-738; Equip NoItem row, EquipUI.cs:825-826).

### 1.5 Bordered sub-window (`sub_window` / side pane)
A baked mid-weight window that slides or toggles over/next to the main sheet: Item's use-target pane
(ItemUI.cs:49, 342-354), Ability's target chooser (AbilityUI.cs:29, 372-384), Equip's ability-detail pane
(EquipUI.cs:1283-1286), Item's KeyItemDetailPanel (ItemUI.cs:1027), Chocograph's HintContentPanel/
SelectedContentPanel (ChocographUI.cs:189-206, 392-399). Positions are baked; slide-ins start at the content
edge x=±1543 and enter from the side **opposite** the selected column (rest x = +338 even column / −398 odd,
ItemUI.cs:342-353; AbilityUI.cs:372-384).

### 1.6 Row bar (`row_bar`) — the sub-menu rail
A short horizontal/vertical strip of 2-7 command buttons owned by the screen: Item's Use/Arrange/Key rail
(ItemUI.cs:34-36), Ability's Use/Equip (AbilityUI.cs:1517-1519), Equip's Equip/Optimize/Off (EquipUI.cs:1332-1334),
Shop's Buy/Sell (ShopUI.cs:1443-1444), Chocograph's Select/Cancel (ChocographUI.cs:422-425). Labels are
runtime-stretched full-button leftAnchor(0,0)/rightAnchor(1,0) + ShrinkContent (EquipUI.cs:1321-1329).
The rail stays visibly lit while a child list is active (see §2.4).

### 1.7 Help bubble (`help_bubble`)
The shared `HelpDialog` singleton: child 0 body, 1 border, 2 caption, 3 phrase UILabel (fontSize 42,
DarkBlue), 4 tail sprite (HelpDialog.cs:256-267, 108). Runtime math: body sized to measured text; **border =
body + 36px each dimension**; caption pinned top-left at 22px inset half-out of the body; text padding 30/58
inside body padding 18/62 (HelpDialog.cs:104-176, 297-300). Renders at **(group pointer depth − 1)**, default 4, on the
`ButtonGroupState.ShowHelpDialog` path (ButtonGroupState.cs:542) — not universal: StatusUI's detail help
writes `Depth = 5` directly, equal to the default pointer depth (StatusUI.cs:252). Help *content* lives ON the button: `ButtonGroupState.Help.TextKey/.Text`, with rich
`[ICON=]/[SPRT=]/[FEED]/[XTAB=]` markup (MainMenuUI.cs:432-486). Toggle = Select key, SFX 682 on / 101 off
(ButtonGroupState.cs:487-493). Tail=false = pinned tail-less caption (StatusUI.cs:250-252).

### 1.8 Dialog frame (the field-speech window, reusable inside menus)
Body fill + 9-slice border ring + corner tail on one clip UIPanel; border spriteName by style:
`dialog_frame_chat` (Auto/NoTail) / `dialog_frame_info` (Plain) / "" (Transparent) (Dialog.cs:243-254);
4 shared tail caps `dialog_pointer_topleft/topright/downleft/downright` (Dialog.cs:1344-1358 = HelpDialog.cs:237-246).
Core numbers: DialogLineHeight 68, DialogYPadding 80, clip = size + (36, 80), panel depth = 68 − 2·id,
phrasePanel always body+1 (Dialog.cs:360-376, 863-872, 1748-1754). SaveLoad proves it is legal to
`AttachDialog(..., WindowStylePlain, CaptionType.Notice)` INSIDE a menu as a toast (SaveLoadUI.cs:481, 489).

### 1.9 Finger cursor (pointer)
Pooled per-DEPTH under PointerManager (one cached UIPanel per distinct depth, PointerManager.cs:187-208).
Size (114, 62) (PointerManager.cs:177). Parks at the target widget's **left edge**:
`(−targetW/2 + ptrW/4, −ptrH/4)` + per-group offset, x-mirrored RTL (UIPointer.cs:44-56, 86).
All pointer chrome is **per-GROUP static config keyed by group name**: offset, limit rect, depth, count,
outside-rect behavior (ButtonGroupState.cs:196-235). Defaults: offset (0,0), depth **5**, rect = full screen
(ButtonGroupState.cs:648-649). The scrolling-list limit rect derives from the list panel's widget:
left/right = x∓w/2, bottom = y−h/2−14+rowH/2, top = y+h/2−20−rowH/2 — the **−14/−20 rail-margin fudge**
(ButtonGroupState.cs:206-218). Blink = enabling the pointer's baked TweenAlpha (held state / multi-target,
UIPointer.cs:112-122; ButtonGroupState.cs:246-258, 355-420).

### 1.10 Memoria-authored panel (the clone-and-gut recipe)
Memoria never builds chrome from raw NGUI. Recipe (ControlPanel.cs:197-222): Instantiate
`MainMenuScene.GenericInfoPanel` (ControlPanel.cs:410) → separately instantiate its frame child(2) →
`DestroyChildren()` the clone → re-parent the frame → clear its caption's UILocalize and write the panel
title as rawText → 4-anchor the frame to the panel → panel lives at scene ROOT, unanchored; geometry is one
fixed SetRect per pivot: side 700×1000, top/bottom 1600×500, corner 700×500, center 1600×1000
(ControlPanel.cs:59-72). Row grammar: rowHeight 50, row gap 10, element gap 10; content insets left 50 /
top 28 / right 50; rows chain by anchor off the previous row's first element (ControlPanel.cs:12-14, 246-270,
363-380). Every widget is harvested from a baked stock scene (labels/sprites from GenericInfoPanel, slider
from ConfigScene, input from NameSetting, scroll list from AbilityScene's SupportAbilityListPanel,
ControlPanel.cs:283-357).

### 1.11 Specialty shapes (single-screen but reusable)
- **Character plate** (`CharacterDetailHUD`): avatar / name+Lv / HP / MP / stones / 7 status icons, with the
  `'Empty'`-named placeholder child marking absent optional panes (CharacterDetailHUD.cs:10-72, 41, 55).
  Battle-row encoded as a 26px avatar x-shift (−418 front / −392 back, MainMenuUI.cs:15-16).
- **AP bar** (`APBarHUD`): UISprite+UISlider root, foreground `ap_bar_progress`/`ap_bar_complete`, master star
  `ap_bar_complete_star`, text panel (APBarHUD.cs:10-18; FF9UIDataTool.cs:239-261).
- **Cascade panel stack** (Status): baked sub-windows dealt one-per-Confirm by TweenIn, only the topmost
  caption visible, whole stack swept out on Cancel (StatusUI.cs:117-146).
- **Silhouette slot** (Chocograph): undiscovered row = button kept in the group, Content child SetActive(false),
  confirm = buzzer (ChocographUI.cs:292, 309-316) — the collection-screen "what remains" grammar.
- **Fat data row** (SaveLoad): each row is its own bordered window, swept with a **data-driven** window color
  (the save file's stored win_type, SaveLoadUI.cs:393).

---

## 2. THE COMPOSITION RULES

### 2.1 Screen skeleton
A stock menu screen = **cloth + 2-6 baked panes + 1-3 button groups + one fade sprite**. Pane positions are
baked; code toggles, binds, and re-dimensions. Pane counts observed: MainMenu 5, Item 4 main + 3 modal,
Ability 6, Equip 6, Status 7 (no groups at all), Config 2 + 2 modal, SaveLoad 2 swapped-in-place + 5 modal,
Shop 3-of-N mode sheets, Chocograph 5, Card 4 + 1 modal. **One dominant sheet per screen** — two lists never
compete; siblings swap in place by SetActive (Ability's action/support lists, AbilityUI.cs:816-827;
Item's item/keyitem lists, ItemUI.cs:586-599; Shop's three mode sheets, ShopUI.cs:1202-1241) or by
whole-scene crossfade (SaveLoad slot↔file, SaveLoadUI.cs:568-578).

### 2.2 Titles and captions
- Column headers live on the **caption rail** (CaptionBackground.CaptionPanel): Name/Info per column, 4 labels
  at 2 columns. Law: when a runtime pass grows columns beyond the baked count, headers go **alpha 0** rather
  than relayout (ItemUI.cs:157-161; AbilityUI.cs:201-205; ShopUI.cs:100-104).
- A pane *title* is the frame's baked caption label (GOFrameBackground Caption; the Memoria recipe reuses
  the donor's caption seat as the title, ControlPanel.cs:208-209).
- Right-edge text law: Memoria pins deep labels off the window's right edge with `rightAnchor.Set(1f, −40)`
  (recurs across screens: AbilityUI.cs:1527,1537; CardUI.cs:490,494,616; ChocographUI.cs:419-421;
  ItemUI n/a −90 variant for Info captions ItemUI.cs:1034-1035; −28/−32/−34/−68 variants ConfigUI.cs:1650,
  SaveLoadUI.cs:717-720, EquipUI.cs:1314-1319).

### 2.3 List-next-to-detail conventions (three stock patterns — pick one)
1. **Slide-over (modality, not real estate):** the detail/target pane is OFFSTAGE and tweens in over the same
   region on confirm; the parent list row stays lit as a held secondary group underneath. (Item target pane,
   Item key-item detail, Equip inventory sheet — ItemUI.cs:342-364, 836; EquipUI.cs:285-296.)
2. **Persistent side pane, hover-driven:** the detail pane is always seated, populated on cursor rest,
   hidden when the cursor sits on a blank/undiscovered row. (Chocograph HintContentPanel —
   ChocographUI.cs:189-206; Ability's AbilityDetailPanel + CommandPanel.)
3. **In-place pane swap with crossfade:** two full sheets share one seat, FadePingPong covers the swap
   (SaveLoad, SaveLoadUI.cs:568-578).

### 2.4 The group ladder (focus model — there is no screen stack)
Named static ButtonGroupState groups + an ActiveGroup state machine replace any navigation stack; OnKeyConfirm/
OnKeyCancel branch purely on `ButtonGroupState.ActiveGroup` (MainMenuUI.cs:144-346). Descending a tier:
`ActiveGroup = child; SetSecondaryOnGroup(parent); HoldActiveStateOnGroup(parent)` — the parent row stays
visibly selected (MainMenuUI.cs:170-180; ItemUI.cs:198-200; EquipUI.cs:308-310; ShopUI.cs:307-308).
Cancel walks up one tier. Mouse-clicking a *held* parent replays the cancel chain with `FF9Sfx.muteSfx = true`
then confirms (OnSecondaryGroupClick — ItemUI.cs:618-647; AbilityUI.cs:854-871; ChocographUI.cs:208-218).
Per-group cursor memory GameObjects persist selection (`SetCursorMemorize`/`SetCursorStartSelect`/
`RemoveCursorMemorize`, ButtonGroupState.cs:452-468), wiped on true exit, kept on fast-switch (ItemUI.cs:213-226).

### 2.5 The depth stack recipe
Panel depths are **baked**; code writes only exceptions. The reliable runtime layers:
- Pointer = a pooled PANEL depth per group; **default 5** (ButtonGroupState.cs:649; PointerManager.cs:134,185).
  Observed spread: Card grid **2** (tuck under cells, CardUI.cs:20) · Item/Ability/Chocograph list **4** ·
  default 5 · Shop quantity **6** (ShopUI.cs:41) · target/sub-screen groups **7** (ItemUI.cs:100;
  AbilityUI.cs:118; ConfigUI.cs:615-616) · MainMenu SubMenu **10** / Order **12** (MainMenuUI.cs:417-418) ·
  SaveLoad file rows **11** (above the fat-row window sprites, SaveLoadUI.cs:65). Rule of thumb: a floating
  sub-window's pointer must beat the sheet's pointer.
- Help bubble = pointer depth − 1 on the ShowHelpDialog path (ButtonGroupState.cs:542); StatusUI writes
  Depth = 5 directly (StatusUI.cs:252).
- Fade sheet panel depth is a **per-path write**: 7 while a descend animation must stay visible, 10 to cover
  everything on exit (MainMenuUI.cs:94-99; SaveLoadUI.cs:83, 102).
- Lifting a modal above its baked seat = `Panel.depth += 1` at Awake (Shop quantity dialog, ShopUI.cs:1315).
- The caption rail's CaptionPanel is its OWN UIPanel, so header text sorts independently of the clipped rows
  (GOScrollablePanel.cs:47).

### 2.6 The window-color LAW
Two mandatory tiers:
1. **Scene sweep** — first act of every `UIScene.Show`: walk `GetComponentsInChildren<UISprite>(true)`
   (including inactive), re-atlas every sprite **tagged "Window Color"** (skipping General/Icon atlases) to
   `FF9UIDataTool.WindowAtlas` = Gray Atlas (win_type 0) or Blue Atlas (UIScene.cs:48, 261-273;
   FF9UIDataTool.cs:269-283). Sprite *names* are untouched — the two atlases carry identical names.
2. **Per-row sweep on recycle init** — pooled rows are instantiated AFTER the scene sweep, so every populate
   delegate runs `DisplayWindowBackground(item.gameObject, null)` once at `isInit`
   (ItemUI.cs:702, 762; AbilityUI.cs:1048-1049; EquipUI.cs:873-877; ShopUI.cs:802, 878, 942).
   Also sweep any subtree that might have been inactive during the scene sweep (MainMenuUI.cs:50).
Data-driven variant: SaveLoad forces the per-row atlas from the save's own stored win_type (SaveLoadUI.cs:393).

### 2.7 The widescreen/relayout pass
`UpdateUserInterface`, gated on `Configuration.Interface.IsEnabled`, exists on the LIST screens only
(Item ItemUI.cs:129-189, Ability AbilityUI.cs:141-273, Equip EquipUI.cs:77-101, Shop ShopUI.cs:69-170,
Chocograph ChocographUI.cs:49-68, plus BattleHUD); MainMenu, Config, SaveLoad have **none** and keep their
bake at every aspect. The pass pattern: record baked truth as `original*` constants → rows from the ini knob →
`lineHeight = round(originalPanelHeight / rows)`, `scale = lineHeight/originalRowH` → `ChangeDims` → re-anchor
cell internals relatively → font `round(36·scale)` → RefreshTableView.
**Roster, settled by direct grep + read (2026-07-21):** geometry relayout passes exist on
Item/Ability/Equip/Shop/Chocograph + BattleHUD (and Memoria's Menu/Battle ControlPanel HUDs). Card and
Status DO carry an `UpdateUserInterface`, but theirs are RTL-text-only colon-blanking (CardUI.cs:47-55;
StatusUI.cs:384-393). MainMenu, Config, SaveLoad have none.

### 2.8 Modality
- Group-swap modality (no new scene): warning dialogs, controller remap — `ActiveGroup` change +
  HoldActiveStateOnGroup + optionally a full-screen hit-catcher whose OnScreenButton KeyCommand is swapped
  per context (ConfigUI.cs:703-724, 1615; ShopUI.cs:1092, 1457).
- Scene modality: `NextSceneIsModal = true` suppresses the fade AND the deactivate — the next screen appears
  instantly over the live current one (UIScene.cs:16-24).
- `Loading = true` is the master input gate around every tween: all OnKey* return false, all pointers hide,
  active group disables; restored in the tween callback (UIScene.cs:108-120, 280-298; ItemUI.cs:274, 356).

---

## 3. THE GEOMETRY GRAMMAR (the recurring numbers)

| Quantity | Value | Source |
|---|---|---|
| UI canvas | 1543×1080 pillarboxed; (1080·aspect)×1080 widescreen | UIManager.cs:653-666 |
| ResourceMultiplier (PSX→UI) | ≈4.82 (1543/320, 1080/224) | UIManager.cs:668-671, 799-800 |
| Full-width list panel | **1490** → 2 cols of **745** (Item, Shop sell; key-item col fixed 745) | ItemUI.cs:135-139, 178; ShopUI.cs:157 |
| Ability grid panel | **1488** → 2 cols of **744** | AbilityUI.cs:162-166 |
| Shop buy list width | **916** (1 col) | ShopUI.cs:80 |
| Equip inventory width | **752** (1 col) | EquipUI.cs:81-84 |
| Chocograph list width | **658** (1 col) | ChocographUI.cs:55 |
| MainMenu command rows | **402** wide, pivot x=201 | MainMenuUI.cs:721 |
| Baked row heights | **98** (Item/Shop/MainMenu pitch), **92** (Ability), **90** (Equip), **86** (Chocograph) | ItemUI.cs:136; AbilityUI.cs:164; EquipUI.cs:83; ChocographUI.cs:53; MainMenuUI.cs:154 etc. |
| Baked visible rows | 8 (Item/Shop), 6 (Ability), 5 (Equip/Chocograph/Shop-weapon) | ItemUI.cs:135; AbilityUI.cs:163; EquipUI.cs:81; ChocographUI.cs:53; ShopUI.cs:76-78 |
| Baked panel heights (rows·rowH exactly) | 784, 552, 450, 430, 490 | ItemUI.cs:139; AbilityUI.cs:166; EquipUI.cs:84; ChocographUI.cs:56; ShopUI.cs:82 |
| Memoria row-count knobs (defaults) | Item 12, Ability 9, Equip 7, Chocograph 7 | InterfaceSection.cs:68-71; Memoria.ini:327-330 |
| Cell font / shadow | **36** / **4**, × scale = rowH/originalRowH | ItemUI.cs:168-173 |
| MainMenu command pitch | baked **98** + **9** top inset (`ShiftContentClip = 9 + 98·row`); hand-relaid to 87/86 (h 79/78, gap 8, y from −39) when a row is inserted, UITable disabled *(the s45 Folklore loop generalizes this by row count: 8 rows = the exact 79/78 walk, 9 rows = 69/68 @ −34, always inside the 684-unit span)* | MainMenuUI.cs:143, 154-269, 717-726 |
| Pointer size / default depth | (114, 62) / depth **5**; help = depth−1 | PointerManager.cs:177, 185; ButtonGroupState.cs:542, 649 |
| Pointer limit-rect trims | bottom −14+rowH/2, top −20−rowH/2 off the panel widget rect | ButtonGroupState.cs:206-218 |
| Pointer finger offsets observed | (54,0) Item lists, (50,0) Shop lists, (48,0) SaveLoad, (52,0) Config, (40,0) Ability grids, (30,0) Chocograph, (10,0) Equip inventory | ItemUI.cs:101; ShopUI.cs:32-34; SaveLoadUI.cs:66; ConfigUI.cs:613; AbilityUI.cs:119; ChocographUI.cs:16; EquipUI.cs:59 |
| Sub-window rest x | +338 / −398 (= −338−60), slide from ±1543 | ItemUI.cs:49, 342-353; AbilityUI.cs:29 |
| Scroll-rail alpha | 0.5 norm; 0 when one page | ItemUI.cs:133-134; AbilityUI.cs:207-208 |
| Help bubble | border = body+36; caption inset 22; font 42; text pad 30/58; body pad 18/62 | HelpDialog.cs:125-174, 297-300 |
| Dialog frame | line height 68; clip = size+(36,80); depth 68−2·id | Dialog.cs:360-376, 863-872, 1748-1754 |
| Memoria panel recipe | rows 50 + gaps 10/10; insets 50/28/50; sheets 700×1000 / 1600×500 / 1600×1000 | ControlPanel.cs:12-14, 59-72, 246-249 |
| Right-edge label pin | rightAnchor.Set(1f, −40) (most common; −28/−32/−34/−68/−90 variants exist) | CardUI.cs:490; ConfigUI.cs:1650; SaveLoadUI.cs:717-720; EquipUI.cs:1314; ItemUI.cs:1034 |
| New! badge | widget 117×64, sprite 44×58, label 90×58 @0.6-rel, × scale (pooled prefab 115×64, id 400) | ItemUI.cs:182-184; FF9UIDataTool.cs:366, 841 |
| RecycleListPopulator prefab default cellHeight | 94 (always overridden by ChangeDims) | RecycleListPopulator.cs:531 |

---

## 4. THE MOTION GRAMMAR

Three composable layers per transition (each screen spends only what it needs, UIScene.cs:45-101):
1. **Alpha fade** — HonoFading black foreground sprite; every Show/Hide overwrites duration with
   `Configuration.Interface.FadeDuration` = **40 ms Memoria default, 300 ms original game**, clamp 0-5 s
   (InterfaceSection.cs:76; Memoria.ini:302; Interface.cs:128-131); anti-flash skip at ≤0.05 s
   (HonoFading.cs:62-69). Screens also pre-set the event-shader fade black:
   `SceneDirector.FadeEventSetColor(FadeMode.Sub, Color.black)` (ItemUI.cs:117 et al.).
2. **Panel slide** — HonoTweenPosition: duration **0.4 s**, in from (+1543, 0), out to (−1543, 0), per-panel
   delayList stagger, anchors detached in flight and restored after **0.2 s** resetAnchorDelay,
   deactiveAfterTweenOut default true (HonoTweenPosition.cs:280-292, 304). Used for: MainMenu plate slide-in,
   Item/Ability target panes (side opposite the picked column), Equip inventory sheet, Status cascade,
   Card duplicate-stack ping-pong.
3. **Clip grow** — HonoTweenClipping: baseClipRegion + companion sprite grown from a ClipPos corner,
   AnimationTime default **0.16 s** but re-timed to FadeDuration by MainMenu (HonoTweenClipping.cs:193;
   MainMenuUI.cs:100, 108); clip-height fudge −20 during the tween (HonoTweenClipping.cs:117). THE
   hub↔submenu handshake: the command window collapses toward the chosen row via
   `ShiftContentClip = (0, 9 + shiftFactor·98·rowIndex)` and every sub-screen's Hide calls
   `MainMenuScene.StartSubmenuTweenIn()` to regrow it (MainMenuUI.cs:143-216, 106-110; ItemUI.cs:215).
   Also: dialog windows inflate from their tail edge in 0.15 s (DialogAnimator.cs:87-96, 213).

**SFX vocabulary (universal):** **103** confirm/descend/cursor-move/scroll (ButtonGroupState.cs:556-557;
ScrollButton.cs:170) · **101** cancel/back/help-close · **102** refused/disabled buzzer · **107** equip/toggle
change (EquipUI.cs:232; ChocographUI.cs:127) · **1047** page-flip/bumper/character-switch (StatusUI.cs:116;
CardUI.cs:218) · **106** item consumed (ItemUI.cs:326) · **1045** shop transaction (ShopUI.cs:390) ·
**682** help open · **1044/1046/1261** save preview-ok/error/success (SaveLoadUI.cs:538, 581, 601).
Cross-group mouse shortcuts replay cancel chains with `FF9Sfx.muteSfx = true`.

**Pointer behavior in motion:** Loading hides all pointers and disables the group (UIScene.cs:280-298);
`ShowPointerWhenLoading = true` opts a cosmetic tween out (CardUI.cs:222-223). Outside-limit-rect behavior
defaults to **Limit** (clamp); drag flips a group to **Hide** (blank >2 px outside) and restores Limit on drop
(UIPointer.cs:61-84; ItemUI.cs:378, 467).

---

## 5. SCREEN DIFF MATRIX

| Screen | Shapes used | List grammar | Unique / off-grammar |
|---|---|---|---|
| **MainMenu** (MainMenuUI.cs) | cloth, bordered command window, 4 character plates, 2 corner info windows, fade | 1×7 static rows, 402 wide, pitch 98+9; no scroll, no caption | Owns the collapse/regrow handshake; hand-relay to 87/86 pitch on row insert with UITable disabled (717-726); NO UpdateUserInterface; pointer depths 10/12 |
| **Item** (ItemUI.cs) | cloth, rail, 2 swapped sheet_with_rails, slide-over target sub-window, key-item detail sub-window, clip-reveal arrange dialog | 2×8×98 @1490 baked; key items pinned 2×745 name-only + New! badge | The codex's donor: name-only cell + detail slide-over + read-marks; empty sentinel row 255 |
| **Ability** (AbilityUI.cs) | cloth, character pane + arrows, rail, command-name sub-window ↔ gem pane swap, info pane (GOFrameBackground), 2 swapped grids, target sub-window | 2×6×92 @1488; fit-fallback ladder | L1/R1 character paging; boosted-gem 6-color table; AP bar anchored −234..−54/−64..−30 |
| **Equip** (EquipUI.cs) | cloth, rail, identity window, 9-row stat compare window, 5-row static part list, detail window, offstage slide-in inventory sheet | inventory 1×5×90 @752 baked → 7×64 | Three-tier group ladder; caption swap while sheet is up; preview-by-mutation compare; zero runtime panel-depth writes; explicit pointer rect (−7,−49,745,325) (EquipUI.cs:61) |
| **Status** (StatusUI.cs) | cloth, 7 static sub-windows, cascade panel stack, tail-less help bubble | none scrolling; cascade = 6 panels × 8 rows, paged by Confirm | **Pointerless** — zero button groups (UIManager.cs:590); UpdateUserInterface = RTL colon-blanking only |
| **Config** (ConfigUI.cs) | cloth, full-width control sheet (snap list), booster row bar, framed warning dialog, group-swap remap sub-screen | 1 col full-width rows (column −745..745 = 1490), baked ItemHeight, 17 baked rows + Memoria mints via template-clone | Row-is-the-button with inner sub-targets; help disabled screen-wide; the template-seat row-mint idiom (1426-1474); survives widescreen with zero re-dimension |
| **SaveLoad** (SaveLoadUI.cs) | cloth, title, help strip, slot row list ↔ fat-row file sheet (in-place FadePingPong swap), 5 modal overlays, dialog-frame toasts | 15 fat rows, ALL baked+eager (no populator); 10 slot rows | Per-row window color from the save's OWN win_type (393); pointer depth 11; world-space toast anchoring (430) |
| **Shop** (ShopUI.cs) | cloth, title/help, rail, 3 mode sheets each sheet_with_rails, info rails, compare strip, quantity sub-dialog +1 depth, legend bars | buy 1×8×98 @916; weapon 5 rows (0.65·rows); sell 2×8×98 @1490 | Live type-flip as cursor crosses mixStartIndex; hold-to-repeat spinner 0.115s→×10 after 1s; runtime-minted key-glyph tooltips at depth+1 |
| **Chocograph** (ChocographUI.cs) | cloth, sheet_with_rails (STATIC), caption rail, hover detail pane (picture+text+icon strip), equipped pane, ability strip, 2-button rail | 1×24 fixed rows, 658×86 baked → 7×61; the game's only static GOSubPanel | THE stock collection/codex analog: silhouette blanks, hover-populated side detail, dedicated content atlas baked in scene, state via sprite-name variants |
| **Card** (CardUI.cs) | own cloth, bordered stats window, 10×10 grid pane, detail window w/ pager, framed discard dialog | 100 cells all visible — no scrolling, no rail, no limit rect | Pointer depth **2** (below default); transposed id involution (i%10)·10+i/10; UpdateUserInterface = RTL only; no fast-switch |

---

## 6. CODEX RECOMMENDATIONS

The Folklore codex needs: a name-only scrolling list, a detail pane, a category header, read-marks. Written
in the vocabulary, the stock-faithful options are:

### Option A — "Key-Items sentence" (the current Phase-B build, tightened)
Shapes: cloth (`folklore_bg` via GOMenuBackground) + ONE sheet_with_rails + the KeyItemDetailPanel slide-over +
the caption rail as category header.
Numbers: ChangeDims(2, rows, **745**, round(784/rows)); name label font round(36·scale); New! badge 117×64·scale
(ItemUI.cs:178-186); pointer offset (54,0), depth 4, limit rect from the panel widget with −14/−20 trims
(ItemUI.cs:99-110); detail = HonoTweenPosition slide from ±1543 with Loading latched (ItemUI.cs:836, 274).
Category = swap the caption rail's Name/Info label keys per L1/R1 page + SFX 1047.
Verdict: legal and proven, but the detail is modal (hides the list) — weak for a browse-heavy codex.

### Option B — "Chocograph sentence" (RECOMMENDED shape, with one substitution)
Chocograph IS the stock codex: browse list left, hover-populated picture+flavor pane right, silhouette slots
for undiscovered entries, counters, 2-button rail. Compose exactly:
- List: sheet_with_rails at **658** wide, rows = MenuChocographRowCount-style knob, rowH = round(430/rows)
  (ChocographUI.cs:53-60) — but **substitute the recycling SubPanel mode** (populator present) for the static
  24-row bake, because folklore entries are unbounded; the populator path of ChangeDims handles it
  (GOSubPanel.cs:51-58). Cell = name label + optional New! widget (the Key-Item cell, ItemUI.cs:1040-1057);
  undiscovered = the silhouette law (Content SetActive(false) + buzzer 102, ChocographUI.cs:292, 309-316).
- Detail: a persistent baked sub-window populated on cursor rest, hidden on blank rows
  (ChocographUI.cs:189-206) — name label + description label (spacingY captured/re-applied per the key-item
  detail, ItemUI.cs:1013-1016) + optional picture sprite.
- Category header: the caption rail's CaptionPanel label as the live category name, L1/R1 to page categories
  with SFX 1047 (the universal page-flip id) — the CharacterArrowPanel idiom, shown only when >1 category
  (AbilityUI.cs:907-913).
- Groups: `Folklore.SubMenu` → `Folklore.Item` two-tier ladder with the secondary-hold idiom (§2.4);
  pointer depth 4, offset (30,0), rect from the list widget (ChocographUI.cs:13-21).
Verdict: **pick this.** It is the only stock pattern where list + always-visible detail + collection
silhouette coexist on one screen with no modality.

### Option C — "Equip-inventory sentence"
752-wide 1-col list sliding in over a static left column of category windows; detail as the persistent
EquipmentAbilityPanel-style window; caption swap while the sheet is up (EquipUI.cs:284-296).
Verdict: viable, but its sheet is offstage-by-default — wrong resting state for a codex.

### Option D — "Memoria panel sentence" (ControlPanel clone-and-gut)
A 700×1000 right-docked InstantiatePanel sheet with a ControlList (600 wide × 19 rows) + ControlHelp sub-panel
(ControlPanel.cs:59-72, 339-357). Verdict: reject for a player-facing screen — it reads as dev chrome
(50px rows, no caption rail, DisablePointerCursor, ControlList.cs:44-47), not as the game's menu language.

### The two open defects, solved in vocabulary terms
1. **~3s first-open clone-burst hang.** Stock law: chrome is built **once** and reused. RecycleListPopulator
   instantiates only the visible pool; the `ItemsPool.Count == 0` gate on `InitTableView` (ItemUI.cs:679-691,
   742-754; EquipUI.cs:837-847) is a CORRECTNESS guard — it prevents re-assigning the populate delegate and
   double-subscribing the click handler — not a cost defense: `SetOriginalData` takes the cheap update path
   only when the item COUNT is unchanged, else it falls through to a full pool rebuild (destroy +
   re-instantiate, RecycleListPopulator.cs:99-111, 498-514), a cost stock accepts because a visible pool is
   small. ItemUI's `JumpToIndex` is itself conditional on no memorized cursor (ItemUI.cs:688-690, 751-753).
   Per-row `DisplayWindowBackground` runs only at `isInit` (§2.6). SaveLoad shows the ceiling: even its eager
   path is 15 baked rows, never N clones. Fix = construct the codex scene (panel clones + row pool) exactly
   once at Awake/first-Show and cache it (the MenuUIControlPanel precedent: lazily constructed once, cached
   static, UIKeyTrigger.cs:479-482); subsequent opens are refreshes. If donor panes must be Instantiated, do
   it off the open path (the hub's Awake) — and profile: a ~3s burst is far beyond a visible-pool rebuild,
   so measure before assuming the pool is the culprit.
2. **Row 1 overlapping the top rail.** The stock invariant: the clip region equals rows·rowH exactly, and
   rows·rowH **equals the baked panel height** (784 = 8·98; 552 = 6·92; 450 = 5·90; 430 = 5·86 — §3), because
   every screen derives rowH as `round(originalPanelHeight/rows)` *before* calling ChangeDims, and ChangeDims
   re-centers the clip (`SetAnchor(null)` then baseClipRegion, GOSubPanel.cs:49-50). The caption rail is a
   SIBLING outside the clip (child 2, own CaptionPanel UIPanel, GOScrollablePanel.cs:17, 47) — rows can only
   appear under it if the clip was grown beyond the baked height or the row container was seated without the
   baked top inset (compare MainMenu's 9-unit inset and GOSubPanel's static reposition
   `posY = padding + row·(2·pad+rowH)`, GOSubPanel.cs:71-87). Fix = derive rowH from the donor's baked panel
   height (never grow rows·rowH past it), pass it through ChangeDims rather than resizing the panel directly,
   and keep the pointer limit rect's −20 top trim so the finger also respects the rail
   (ButtonGroupState.cs:213-216).

### Explicit census conflicts (do not average)
- **UpdateUserInterface roster — SETTLED** (direct grep + read, 2026-07-21): geometry passes on
  Item/Ability/Equip/Shop/Chocograph + BattleHUD (+ Memoria's two ControlPanel HUDs); Card and Status =
  RTL-text-only colon-blanking (CardUI.cs:47-55; StatusUI.cs:384-393); MainMenu/Config/SaveLoad none.
  The Card lane's "only two in the tree" phrasing was wrong.
- **CaptionBackground Shadow aliasing:** the wrapper binds Shadow from GetChild(2) (= Body) in the branch
  keyed on GetChild(3) (GOScrollablePanel.cs:34-36) — treat as a wrapper bug; the baked anatomy intends a
  distinct Shadow child.
- **ScrollButton hold-accel window:** cited as 0.5s→2.5s (shared lane, ScrollButton.cs:281-310), "over 2s
  after a 0.5s hold" (SaveLoad numbers), and "over 2.5s" (Config numbers) — same mechanism, off-by-phrasing;
  the code citation is authoritative.
- **Chocograph baked row count:** 5 visible rows PC bake, with a code comment saying PSX was 7
  (ChocographUI.cs:53-59; InterfaceSection.cs:71) — Memoria's default 7 restores the PSX density.
- **MainMenu row pitch:** 98 (vanilla bake, proven only via ShiftContentClip constants) vs 87/86 (Memoria's
  hand-relay when a row is inserted) — two regimes, not a contradiction; any row insert must accept the
  hand-relay + UITable-disable cost (MainMenuUI.cs:143, 154, 717-726).
---

## 7. VERIFICATION RECORD

Synthesized 2026-07-21 from a 13-agent census (10 screens + 3 machinery lanes; 32 agents total including
verification; raw returns: [`census.json`](census.json)). The 18 load-bearing claims were each handed to a
skeptic agent instructed to REFUTE them against source: **15 CONFIRMED, 3 REFUTED** — all three corrections
are folded into the text above (§1.3 the wrapper-vs-prefab-invariant split; §1.7/§2.5 the help-depth path
qualifier; §6.1 the populator-lifecycle mechanics). The one census conflict the synthesis flagged (§2.7
roster) was settled by direct grep + read after synthesis. Composes with the mechanical law set in project
memory `project-ff9-ngui-menu-construction` (how cloned pieces BEHAVE; this document is which pieces exist
and how they COMBINE).
