---
name: editing-ff9-items-and-saves
description: Edit FF9 items, equipment, shops, weapon models, and real save files -- stock Memoria, no DLL. Use for `items-set-gil`/`item`/`equip`/`keyitem`/`stat`/`ap`, `items-inspect`, `save-edit`, `flags`/`flags-inspect`/`flags-diff`, the `[[item]]`/`[[weapon]]`/`[[shop]]`/`[[item_text]]` blocks, or reading/comparing/writing gil/items/equipment/key items/stats/AP or a save's `gEventGlobal` state. Covers the 3-layer item/equip/shop CSV model + id bands, custom weapon models (`Weapons.csv` Model takes a minted GEO name), item name/description text via `[[item_text]]` -> `TextPatch.txt >DATABASE` (relaunch to apply), and the dual-container save (encrypted main + Memoria extra, where the extra WINS). This owns reading/comparing/editing a SAVE FILE's bytes (gil/stats/items/flags); for AUTHORING `gEventGlobal` story flags in an `.eb` script see `authoring-ff9-field-scripts`.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Editing FF9 Items & Saves

Two surfaces, both stock-Memoria (no DLL): **authoring** item/equip/shop data via `field.toml`
blocks compiled into CSV/TextPatch deltas, and **reading/editing a real save file's bytes**
(gil, items, equipment, key items, stats, AP, story state).

## Item/equip/shop CSV model + id bands

Engine item data is external CSV under `<game>\StreamingAssets\Data\Items\` — 3 layers: an
`Items.csv` catalog row (price, who-can-equip, taught abilities) + FK rows in
`Weapons.csv`/`Armors.csv`/`ItemEffects.csv` + a `Stats.csv` equip-bonus table. A mod ships a
PARTIAL delta, merged by id. Authoring blocks: `[[item]]` / `[[weapon]]` / `[[armor]]` /
`[[equip_bonus]]` / `[[item_effect]]` / `[[shop]]` / `[[synthesis]]` / `[start_inventory]` /
`[[equipment]]`. Schemas: `ff9mapkit/docs/FORMAT.md`. Id bands + save data model:
`references/save-layout.md`.

## Custom weapon models

`[[weapon]] model = "GEO_WEP_*"` (stock swap) or `model = { id = 6000-32767, hue/tint/textures }`
(mint a recolored variant). The `Weapons.csv` Model column takes a minted GEO name — zero-DLL.
Weapons load on battle entry → RELAUNCH, not the menu reload. Read memory `[[project-ff9-items-equipment]]`
(the CUSTOM WEAPON MODELS section).

## Item text via >DATABASE

`[[item_text]] name=` + `display_name` / `description` → a `TextPatch.txt` `>DATABASE` block at
the mod-folder root (a text channel, NOT a CSV). The engine flags help-desc and battle-desc
identically, so `description` sets BOTH. Verbatim gotcha (FORMAT.md):

> **★ RELAUNCH to apply:** `TextPatch.txt` is read once at engine startup (~ → Reload field will NOT pick it up).

Full channel spec: read memory `[[project-ff9-item-text]]`.

## The dual-container save

A save's items/equip/gil live in TWO copies — the encrypted main AES block inside
`SavedData_ww.dat` plus the Memoria extra file `SavedData_ww_Memoria_{slot}_{save}.dat`. The rule,
verbatim from memory `project-ff9-save-item-layout`:

> ★ EDIT TARGET = BOTH, extra wins (the decisive finding).

> editing only the main block is a silent no-op when a valid extra exists.

The kit's `items-set-*` verbs dual-write (extra leg FIRST); save edits need NO relaunch (the extra
is re-read on every save-load). Layout detail + write rules: `references/save-layout.md`.

## The verbs

- **Item/save editing:** `items-inspect`, `items-set-gil`, `items-set-item`, `items-set-equip`,
  `items-set-keyitem`, `items-set-stat`, `items-set-ap` — dry-run by default, `--apply` writes
  (atomic, `.bak` backup).
- **Save-state read/compare:** `flags` (browse the story-flag registry), `flags-inspect` (decode a
  save's `gEventGlobal` state), `flags-diff` (what a story beat changed), `save-edit` (set
  ScenarioCounter + flags + overworld position).

Per-verb map with arguments: `references/save-layout.md`.

## Boundary

This skill owns reading/comparing/editing a SAVE FILE's bytes (gil/stats/items/flags); for
AUTHORING `gEventGlobal` story flags in an `.eb` script (`[[flag]]` blocks, GLOB vs MAP
persistence, flag bands) see `authoring-ff9-field-scripts`.

## Additional resources

- `ff9mapkit/docs/FORMAT.md` — the block schemas: `[start_inventory]`/`[[equipment]]`, `[[shop]]`,
  `[[synthesis]]`, `[[weapon]]`/`[[armor]]`/`[[item]]`/`[[equip_bonus]]`/`[[item_effect]]`,
  `[[item_text]]`.
- Memory (read on demand): `[[project-ff9-items-equipment]]` (the CSV model + every built lever),
  `[[project-ff9-save-item-layout]]` (the save codec, offsets, dual-write history),
  `[[project-ff9-item-text]]` (the TextPatch.txt `>DATABASE` channel spec).
- `references/save-layout.md` — the dual-container layout + the verb map.
