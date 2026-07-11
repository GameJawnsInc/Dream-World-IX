Canonical source: `ff9mapkit/docs/FORMAT.md`, the `### [[playable]]` section — this file QUOTES its key tables verbatim for quick lookup and is NOT a fork; if this file and FORMAT.md ever disagree, FORMAT.md wins (update this quote).

# `[[playable]]` schema — key tables (quoted from FORMAT.md)

Everything below the rule is quoted verbatim from `ff9mapkit/docs/FORMAT.md`. Relative links inside the
quoted blocks (e.g. `CUSTOM_MODELS.md`, `../examples/...`) resolve against `ff9mapkit/docs/`, not this file.

## Contents

- [Section intro + relaunch rule](#section-intro--relaunch-rule)
- [Block skeleton](#block-skeleton)
- [Core keys](#core-keys)
- [Custom battle model + animset](#custom-battle-model--animset)
- [`[playable.abilities]`](#playableabilities)
- [Minting a unique command](#minting-a-unique-command)
- [Minting a custom ability](#minting-a-custom-ability)
- [Minting a custom status](#minting-a-custom-status)

---

## Section intro + relaunch rule

> ### `[[playable]]` — a brand-new custom playable character
>
> Mint a **genuinely new engine `CharacterId`** — a 13th (14th, …) party member alongside all 12 canon
> characters, with its own name, stats, battle model, and ability kit. **Zero DLL** (CSV deltas + `.eb`
> recruit op), *except* a custom battle **formula** (`script`, see below) which uses the Scripts-DLL channel.
> Full worked example: [`examples/thirteenth-character/`](../examples/thirteenth-character/iviv.field.toml)
> (Iviv + Steiniv); the engine mechanism is in the memory `project-ff9-13th-character`.
>
> > **Relaunch + New Game.** The new `BaseStats`/`CharacterParameters` rows and the name directive load at
> > **startup / New-Game init** — F6 Reload won't pick them up. So: deploy → **relaunch** → **New Game** (so
> > the engine inits the party with the new id present) → reach the field (Main_Init recruits it).

## Block skeleton

```toml
[[playable]]
name   = "Iviv"          # the menu/battle name (no ';' or '#')
borrow = "vivi"          # REQUIRED: clone stats + rig from a base character (name, or a 0–11 id)
recruit = true           # B_PARTYADD(id) prepended to Main_Init -> joins the party at field load
id     = 12              # the CharacterId; OPTIONAL, defaults to 12 (the first custom slot). >= 12.
stats  = { magic = 40 }  # override cloned stats (below)
portrait = "art/iviv_portrait.png"   # OPTIONAL custom menu avatar (132×190 PNG)
```

## Core keys

> | key | meaning |
> |---|---|
> | `name` | REQUIRED — the menu/battle name. No `;` or `#` (they'd corrupt the CSV row). |
> | `borrow` | REQUIRED — a base character (`"zidane"`…`"amarant"`, or a `0`–`11` id) to clone BaseStats + CharacterParameters (command-set / equip-set / stats / rig) from. |
> | `id` | the new `CharacterId`. Optional; default `12` (the first custom slot). A second custom character takes `13`, etc. — the kit auto-allocates distinct CSV/preset/command/ability bands so they don't collide. |
> | `recruit` | `true` → the character JOINS the party at field load (real `B_PARTYADD`, prepended to Main_Init). Arrives with its normal starting gear. Omit to define it without adding it yet. |
> | `names` | per-language name overrides: `names = { jp = "…", fr = "…" }` (the base `name` is used for any language not listed). |
> | `stats` | override cloned stats — any of `strength`, `magic`, `dexterity`, `will`, `gems`. (Magic drives BOTH spell damage AND the MP pool — to weaken one spell, use its `power`, not this.) |
> | `params` | CharacterParameters overrides — `equip_set`/`equipment_set` (a name or id), `row`, `category`, `win_pose`, `name_keyword` (auto-unique). `menu_type`/`preset`/`serial_formula` are owned by `[playable.abilities]` / the battle-model keys — don't set them by hand. |
> | `portrait` | a custom menu avatar (a 132×190 PNG) → a loose Face-Atlas sprite override. Implies a new battle serial (below). |

## Custom battle model + animset

> **Custom battle model + animset** (optional — the look; a separate pillar, see [CUSTOM_MODELS.md](CUSTOM_MODELS.md))
>
> | key | meaning |
> |---|---|
> | `custom_battle_model` | `true` → mint an INDEPENDENT, editable copy of the borrow's battle model bound to this character (its own serial + BattleParameters row), so reshaping it in Blender never touches the donor. |
> | `battle_model_id` / `battle_model_from` | (with `custom_battle_model`) the minted model id / a `GEO` name to build it from. |
> | `custom_battle_anims` | `true` (needs `custom_battle_model`) → also give the minted model its own editable animset (faithful clip copies + registrations), so editing its poses never touches the donor. |
> | `anim_edits` | a path to a Blender-edited `.glb` (from `playable-anims … --export`) the build ships onto the animset, so edits PERSIST across re-deploys. Needs `custom_battle_anims`. |
> | `battle_serial` / `battle_borrow_serial` | the minted BattleParameters serial / a donor serial `0`–`18` to clone. Auto-assigned when `custom_battle_model`/`portrait` is set — only override if you know why. |

## `[playable.abilities]`

> **`[playable.abilities]`** — the character's own battle command menu + learn list (optional; zero-DLL, its
> own `CharacterPresetId` in band 20–23). Deep mechanism: [BATTLE_DESIGN.md](BATTLE_DESIGN.md).
>
> | key | meaning |
> |---|---|
> | `preset` | `"custom"` (default → auto-allocate a preset id 20–23) or an explicit custom-band id. |
> | `menu_from` | a base preset `0`–`15` (a canon character) to clone the command menu + seed the learn file from. Defaults to the `borrow` for a MAIN character (0–7); **required** when `borrow` is a guest (8–11). |
> | `command1` / `command2` | the two command slots. Either a stock `BattleCommandId` name (`"Black Magic"`) **or** an inline `[playable.abilities.command1]` table to MINT a unique command (below). |
> | `command1_trance` / `command2_trance` | the trance-mode slots (default: mirror the regular slots). A stock command only — can't mint here (put the mint on `command1`/`command2`; it applies in trance too). |
> | `learn` | a list of `{ ability, ap }` — the learnable abilities (`ap = 0` = usable now). A minted command's pool auto-seeds this at `ap = 0`, and your explicit entries win on AP. |

## Minting a unique command

> **Minting a unique command** — an inline `[playable.abilities.command1]` table:
>
> | key | meaning |
> |---|---|
> | `name` | the command's display label (a `com_name.mes` overlay renames just this command). |
> | `abilities` | the ability POOL — a list mixing stock spells (a bare name, e.g. `"Blizzard"`) and **custom abilities** (inline `{ name, from, … }` tables, below). Shown under the command = its pool ∩ the learn list. |

## Minting a custom ability

> **Minting a custom ability** — an inline `{ … }` in a command's `abilities` pool (its own new AA id, cloned
> from a stock donor and retuned):
>
> | key | meaning |
> |---|---|
> | `name` | the ability's display name. |
> | `from` | REQUIRED — a stock ability to clone its ANIMATION + damage formula (e.g. `from = "Fire"`). (FF9 doesn't recolor by element, so the on-screen VFX is the donor's — clone from the matching element for a matching look.) |
> | `power` / `element` / `mp` / `rate` / … | `Actions.csv` overrides that retune the clone (e.g. `power = 55`, `element = ["Thunder"]`, `mp = 18`, `rate = 50` for a status hit-rate). |
> | `status` | a list of statuses the ability inflicts — stock names (`["Silence"]`, auto-mints a StatusSets row) and/or **custom-status** tables (below). Lands only if the donor formula applies statuses AND `rate` is non-zero. |
> | `effect` | a power-user `AbilityFeatures` `[code=TAG] … [/code]` NCalc body keyed on this ability (`Power`/`Element`/`MPCost`/`HitRate`/`Status`/…). E.g. `effect = "[code=MPCost] 0 [/code]"` makes it free. |
> | `script` | a NEW battle FORMULA no data edit can express — `script = { template = "drain_hp" }` (or `{ body = "<C#>" }`), minted into a mod `Memoria.Scripts.<Mod>.dll`. Needs a C# compiler + a **relaunch**. A paired field-menu effect: `script.field = { template = … }`. Full detail: [SCRIPTS_DLL.md](SCRIPTS_DLL.md). |

## Minting a custom status

> **Minting a custom status** — an inline `{ … }` in an ability's `status = [ … ]` list (a minted
> `[StatusScript]` behaviour; [SCRIPTS_DLL.md](SCRIPTS_DLL.md) §12):
>
> | key | meaning |
> |---|---|
> | `name` | the status name. |
> | `template` | a built-in behaviour (`auto_life`, `auto_attack`) — OR set `body = "<C#>"` + `hooks = [ … ]` (the lifecycle interfaces it implements) for a hand-written one. |
> | `icon` | a vanilla status name to borrow its HUD panel icon from (`"AutoLife"`, `"Regen"`, `"Berserk"`). Defaults to the template's icon. |
> | `over_model` | a vanilla status name to borrow its ON-MODEL visual (chevron / particle / tint), e.g. `"Haste"`. Defaults to the `icon` donor. |
> | `power` | a template knob — for `auto_life`, the revive % of max HP (1–100). |
