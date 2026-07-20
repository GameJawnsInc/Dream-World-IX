# FF9 save layout + the item/save verb map

Distilled from memory `project-ff9-save-item-layout` + `project-ff9-items-equipment` (the
canonical deep recipes — every blockquote below is VERBATIM from them or from
`ff9mapkit/docs/FORMAT.md`; read those files for offsets, codecs, and the full build history).

## Contents

- [The dual-container save (extra WINS)](#the-dual-container-save-extra-wins)
- [Write rules](#write-rules)
- [Data model quick facts](#data-model-quick-facts)
- [The verb map](#the-verb-map)
- [Relaunch rules (what applies when)](#relaunch-rules-what-applies-when)

## The dual-container save (extra WINS)

Items/equipment/gil live in the `40000_Common` module, written to TWO copies per save:

1. The **main encrypted AES block** (old-save fixed layout) inside `SavedData_ww.dat`.
2. The **Memoria extra file** `SavedData_ww_Memoria_{slot}_{save}.dat` (or `_Autosave`) — a
   SimpleJSON binary tree.

Verbatim, from `project-ff9-save-item-layout`:

> ★ EDIT TARGET = BOTH, extra wins (the decisive finding).

> Same trap story_flags hit with gEventGlobal — editing only the main block is a silent no-op when a valid extra exists.

> So: patch the EXTRA (authoritative) AND mirror to MAIN (fallback for vanilla/no-extra saves + when the time-gate fails); **never touch `00001_time`**. No extra file → MAIN alone is authoritative.

A save with NO extra file is a vanilla save: the main block alone is authoritative, and the kit's
verbs edit it directly (gil / items / equipment / key items / stats / AP all proven on both
containers — see the memory's step log).

## Write rules

- The dual-write orchestrators write the EXTRA leg first. Verbatim (a reviewed fix):

> **now the EXTRA leg writes FIRST** (partial failure leaves the visible value correct)

- Every write verb defaults to a DRY-RUN preview; `--apply` writes atomically with a timestamped
  `.bak` backup (`--no-backup` skips), a scoped-change gate (only the intended bytes may move), and
  a post-write re-read confirm.
- Save edits need no relaunch. Verbatim:

> ★ **No relaunch needed — the extra is re-read on EVERY save-load** (not cached at process launch), so the edit→load loop is as fast as a debug-menu field reload.

## Data model quick facts

Verbatim lines from `project-ff9-save-item-layout`:

> RegularItem = single Byte 0-254, **255=NoItem**. Bands: wpn 0-87 / wrist 88-111 / helm 112-147 / body 148-191 / accy 192-223 / gem 224-235 / usable 236-254.

> gil = UInt32, in-game cap **9,999,999**; count clamps 99.

> Engine SAFETY NET: on load it DROPS items / resets equip ids not in `ff9item._FF9Item_Data` (write only real ids).

And from `project-ff9-items-equipment`:

> **Key/Important items = SEPARATE id-space** (256 slots, a save bit-packed membership set, metadata = name+help+icon only, NO stats/effects; `items.resolve` can't reach them)

Shop-id and CSV-merge rules (shop ids >= 32, highest-wins vs merged CSVs, stacked-folder shadows)
live in `ff9mapkit/docs/FORMAT.md` and `project-ff9-items-equipment` — do not re-derive them here.

## The verb map

Run `py -m ff9mapkit <verb>` from the kit root. Save target for the `items-*` verbs = a
`SavedData_ww_Memoria_*.dat` extra file OR a `SavedData_ww.dat` container (then pass
`--slot`/`--save-no` or `--autosave`); a container target dual-writes.

| Verb | Reads / edits |
|---|---|
| `items-inspect <save>` | read-only decode: gil, inventory, equipment, key items, stats, abilities |
| `items-set-gil <save> <gil>` | gil (0..9,999,999) |
| `items-set-item <save> <item> <count>` | one inventory stack (count 0 removes; clamps to 99) |
| `items-set-equip <save> <char> <slot> <item>` | one equip slot — weapon/head/wrist/armor/accessory; `empty`/255 unequips |
| `items-set-keyitem <save> <name> [--remove] [--used]` | a KEY item (separate id-space; names read live from the install) |
| `items-set-stat <save> <char> <stat> <value>` | permanent growth stat — Speed/Strength/Magic/Spirit (Speed/Spirit cap 50, Strength/Magic cap 99) |
| `items-set-ap <save> <char> <ability> <value>` | ability AP/mastery; ability = name / `AA:X` / `SA:X` / id / `all`; value = `master` / `max` / `forget` / 0-255 |
| `flags [filter]` | browse the story-flag registry (named vars / reserved regions / milestones) — no save needed |
| `flags-inspect <save>` | decode a save's story state (`gEventGlobal`); accepts a container, an extra-save, a save JSON, or a bare Base64 blob |
| `flags-diff <a> [b]` | diff two saves' story state (A -> B): what scenario/flags a beat changed; with one save, `--slot-a`/`--slot-b` diff two slots |
| `save-edit <save>` | set a save's story state: `--scenario` (value or area name), `--set`/`--clear` flag lists (`--names` maps `[[flag]]` names), `--world-pos`, `--list`, `--out` |

`ff9mapkit items --abilities` lists resolvable ability names for `items-set-ap`. The Workspace app
(`apps/ff9_workspace.pyw`) carries the GUI save-editor surface.

## Relaunch rules (what applies when)

- **Save edits:** NO relaunch (see the verbatim rule above — the extra is re-read on every
  save-load).
- **Item stat CSVs** (`[[weapon]]`/`[[armor]]`/`[[item]]`/`[[equip_bonus]]`/`[[item_effect]]`,
  `[[synthesis]]`) — verbatim from FORMAT.md:

> **★ RELAUNCH to apply:** item CSVs load once at game **startup** — ~ → Reload field will NOT pick up a stat change. Deploy, then relaunch.

- **Item text** (`[[item_text]]`) — verbatim from FORMAT.md:

> **★ RELAUNCH to apply:** `TextPatch.txt` is read once at engine startup (~ → Reload field will NOT pick it up).
