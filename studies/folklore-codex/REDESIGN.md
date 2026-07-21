# The Folklore Codex Screen — Option B Redesign Spec ("the Chocograph sentence")

> **Status: SPEC — awaiting user look-over before the engine round.** Chosen 2026-07-21 (user: "B sounds
> tailor fit"). Written in the vocabulary of `studies/menu-shape-language/VOCABULARY.md`; mechanics per
> the NGUI laws (`project-ff9-ngui-menu-construction`). Build = a recapture of **s45** (top of the
> memoria-patches stack), replacing FolkloreUI's Phase-B layout.

## 0. The user's wariness, resolved

*"Chocograph doesn't open from the menu Folklore is currently in."* Two answers, verified in source:

1. **The entry path is already ours and does not change.** FolkloreUI is a main-menu submenu (Phase B):
   the MainMenu row, the hub collapse/regrow handshake (`StartSubmenuTweenIn`), the cloth. Option B
   changes the composition *inside* the screen; Chocograph's own field-context entry is never used.
2. **We take Chocograph's pattern, not its pieces.** Every cloned asset is a main-menu-native donor we
   already use (Item scene + GenericInfoPanel). And even if we wanted a Chocograph pane later, it is
   reachable: `UIManager.ChocographScene` is a public field on the persistent singleton, present-but-
   inactive from init (UIManager.cs:722, 241) — identical to `ItemScene`, which Phase B already clones
   from while inactive. The silhouette law, hover-populate, and buzzer-on-locked are *idioms* (code);
   the picture atlas is the one genuinely Chocograph-bound asset and we don't need it (detail is text
   now; the s46 render rig later).

## 1. The sentence

Cloth + **one** sheet_with_rails (list, left) + **one persistent framed detail pane** (right,
hover-populated) + the caption rail as the live category header. No modality: the detail pane never
covers the list; undiscovered entries are silhouette rows in place. This is stock's only
list-plus-always-visible-detail collection pattern (Chocograph, VOCABULARY §2.3 pattern 2, §5).

## 2. Shapes and donors

| Piece | Shape | Donor / API | Notes |
|---|---|---|---|
| Backdrop | background_cloth | current Phase-B clone (`item_bg` reskin) | unchanged |
| List | sheet_with_rails | `ItemScene.KeyItemListPanel` clone (current) | keep the recycling SubPanel; `ChangeDims` only |
| Row | Key-Item cell | baked cell in the donor | name label + New! badge; **bars stay 745 wide** — stock itself pins key-item columns at 745 in widescreen rather than stretch the bar (ItemUI.cs:178) |
| Category header | caption rail | the donor's own CaptionBackground | header Name label = live category; Info label inactive |
| Detail pane | framed sub-window | `BuildFramedPane` (GenericInfoPanel frame recipe, Phase B) | persistent, never tweened over the list |
| Undiscovered row | silhouette law | idiom (ChocographUI.cs:292, 309-316) | row stays in the group; name = "???" gray; confirm = buzzer 102 |
| Read-marks | New! badge + FF9Item_Is/UseImportant | current | confirm on unread = mark read, SFX 103 |

## 3. Geometry (the numbers)

- **Canvas frame:** compose inside the 1543-wide pillarbox frame with stock's outer margins (~26.5 each
  side — the 1490-on-1543 norm). Widescreen extends cloth only.
- **List:** 1 col × 8 rows × **745 × 98** = the donor's exact bake (784 = 8·98 — the clip-height
  invariant satisfied with ZERO re-derivation, VOCABULARY §3, §6.2). Seated left: outer edge at the
  stock margin.
- **Detail pane:** right of the list, filling the remaining frame minus a standard gutter; caption
  fontSize 34 (current), body label per Phase B. Populated on cursor REST (OnItemSelect), hidden or
  placeholder-text when the cursor sits on a silhouette row.
- **Pointer:** offset (54, 0) (the Item-list norm), depth = list panel + 1, limit rect from the list
  panel widget **with the −14/−20 bottom/top trims** (ButtonGroupState.cs:206-218) so the finger
  respects the rail.
- **THE PRESERVE-THE-BAKE LAW (new, this build's core discipline):** move ONLY the compound root.
  The donor's *internal* offsets — SubPanel localPosition relative to the CaptionBackground, the
  table's baked seat, the rail geometry — are the bake's own solution to "rows sit under the rail";
  do not renormalize them. Phase B's hand-rolled scroll fixpoint zeroed the panel's local position,
  which is the prime suspect for the row-over-rail defect (§5.2). The rebuild: record the donor's
  internal offsets first (one-shot log or offline read), seat the root, `ChangeDims`, seat the
  template at the row-0 seat, then `SetDragAmount(0,0)` — and assert the internal offsets survived.

## 4. Behavior

- **Groups:** `Folklore.List` single-tier under the MainMenu ladder (unchanged); descend/cancel per the
  group-ladder grammar (VOCABULARY §2.4). Cursor memory per category.
- **Categories:** L1/R1 pages Bestiary/Places/Lore — SFX **1047** (the universal page-flip id; Phase B
  used the wrong id family), header label swaps, list refreshes via `SetOriginalData` (count-changed
  rebuild is acceptable stock cost).
- **Hover-populate:** detail refresh on cursor rest, not on confirm. Confirm = mark-read (unread) /
  buzzer (silhouette). Cancel = 101, back to MainMenu with the hub regrow.
- **Empty-category law:** never an empty list — one sentinel silhouette row (the KeyItemId-255 idiom,
  ItemUI.cs:737-738).

## 5. The two open defects, owned here

1. **~3s first-open hang — PROFILE FIRST.** The verified populator mechanics (VOCABULARY §6.1) say a
   visible-pool rebuild is cheap; a ~3s burst points at the Awake pane-clone chain or something else
   entirely. Instrument (frame-time log around Awake stages), then apply the stock law: construct
   once at Awake/first-Show, cache; opens are refreshes. Do NOT optimize unmeasured.
2. **Row 1 over the top rail.** Root-cause hypothesis: Phase B's fixpoint zeroed the donor's baked
   SubPanel-vs-rail offset (§3, the preserve-the-bake law). Fix by preservation, not by nudging: keep
   the baked internal geometry, and keep rows·rowH exactly at the donor's 784.

## 6. Build plan

1. Offline: dump the donor's baked internal offsets (extend the Phase-B one-shot census log).
2. Rewrite FolkloreUI's Awake/layout to the spec (the diff is mostly *deletion* — the hand-rolled
   frame math goes away in favor of preserved bake + ChangeDims).
3. Profile the first-open path; fix what the numbers name.
4. One playtest round: layout + rail + categories + silhouette + read-marks + hang timing.
5. Recapture s45 (both patch gates), README/SUBMENU/memory updates.
