# Id-band allocations — the crash-avoidance table

Safe custom bands per CSV / id-space for `[[playable]]` characters. The kit auto-allocates inside these
bands; you almost never set them by hand. Every band value in the summary table is transcribed from the
verbatim source lines quoted below (memory `project-ff9-13th-character` and
`project-ff9-ability-preset-system`) — do not invent new bands.

## Contents

- [Summary table](#summary-table)
- [Two number-spaces for a custom ability (boot-crash trap)](#two-number-spaces-for-a-custom-ability-boot-crash-trap)
- [Per-character auto-allocation (a 2nd character)](#per-character-auto-allocation-a-2nd-character)
- [CSV coverage gates are floors, not caps](#csv-coverage-gates-are-floors-not-caps)
- [Verbatim source lines](#verbatim-source-lines)

## Summary table

| Id space (where it lands) | Safe custom band | Kit allocator constant | Failure mode outside the band / without the row |
|---|---|---|---|
| `CharacterId` — BaseStats + CharacterParameters row id | 12-15 (default 12) | `CUSTOM_CHAR_MAX=15` (4 custom chars) | a bare `[party] add = [12]` with NO `[[playable]]` defining it null-derefs at field load (the build now hard-errors this) |
| `CharacterPresetId` — CommandSets row + `Abilities/<id>.csv` learn file | 20-23 (`preset = "custom"` auto-allocates) | `_PRESET_CUSTOM_MIN/MAX` | menu-open does an UNGUARDED `CommandSets[presetId]` index -> KeyNotFoundException if the CommandSets row isn't shipped; a missing learn file = AP-gating silently lost (knows every pool spell) |
| `BattleCommandId` — Commands.csv (minted command) | 46, then 35-40 | `_CMD_CUSTOM_BAND` | SKIP 45 (AccessMenu) and 47 (EnemyAtk); 48-99 are engine-reserved |
| `BattleAbilityId` — Actions.csv (custom active ability) | 192-223 | `_CUSTOM_ACTION_MIN/MAX` = 192/223 | the base is packed 0-191 (the loader gate is a floor, so 192+ is purely additive); see the two number-spaces trap below |
| StatusSets row (auto-minted by `status = [names]`) | 100+ | `_CUSTOM_STATUS_SET_MIN=100` | `statusIndex` is kit-injected only — the engine's `add_status[statusIndex]` is a direct KeyNotFound-throwing indexer, so a hand-set index to a missing row crashes at cast time |
| `CharacterSerialNumber` — BattleParameters row (battle look) | >= 19 (Iviv 19, Steiniv 20) | `_BATTLE_SERIAL_MIN=19` | auto-assigned with `custom_battle_model` / `portrait`; only override if you know why |
| Minted battle-model GEO id (`Models/2/<id>/`) | >= 6000 | (mint id; Iviv 6100, Steiniv 6101) | — |
| AnimationDB keys (`3DModelAnimation` registrations) | fresh keys >= 1M | — | a missing clip freezes the motion (fail-loud `AnimsetError` at deploy) |
| `[[ability_feature]]` `>AA` header for a custom ability's `effect` | the RAW pool id 192-223 | `_AA_MAX` lifted 191 -> 223 | the header takes the RAW id, NOT the `AA:` 256+ learn form |

Also crash-relevant, not a band: `[[playable]] name` must contain no `;` or `#` — a `;` shifts the
BaseStats CSV columns (`Byte.Parse` throws -> hard boot crash); a leading `#` silently drops the row. The
parser rejects both.

## Two number-spaces for a custom ability (boot-crash trap)

A custom ability id (e.g. 192) is written in TWO different token forms and they are NOT interchangeable:

> **THE TWO NUMBER-SPACES (load-bearing):** the command ListEntry
> holds the **RAW id 192** (`CsvParser.Int32Array`; an `AA:` there = a boot crash) while the learn file Abilities/20.csv
> holds **`AA:192`** (`CsvParser.AnyAbility` maps it to abilId 256; a plain 192 there = a silent dead spell) -- the kit
> emits each form correctly (pool via `_resolve_active_ability`, learn via `_resolve_learn_token`).

## Per-character auto-allocation (a 2nd character)

Two (up to four) custom characters coexist — the kit steps every band per character:

> the kit auto-allocates fully DISTINCT bands per character (BaseStats/CharParams id
> 13, preset 21 vs 20, command 35 vs 46, action 193 vs 192, model 6101 vs 6100, serial 20 vs 19, statusset 101 vs 100)

## CSV coverage gates are floors, not caps

Why an added row in a custom band loads at all:

> **CSV COVERAGE GATES are MINIMUMS (pass with 0-11 present; id-12 is ADDITIVE via partial delta, base supplies rest):**
> ff9level.cs:35 (BaseStats min 12), ff9play.cs:118 (CharacterParameters min 12), ff9play.cs:94 (DefaultEquipment min
> 15 by EquipmentSetId), CharacterCommands.cs:71 (CommandSets min 20 by CharacterPresetId), btl_mot.cs:137
> (BattleParameters min 19 by CharacterSerialNumber). All merge via `EnumerateCsvFromLowToHigh`. A NEW serial(≥19)/
> preset(≥20)/equipset(≥15) also just loads (ParseEntry casts int→enum) but bumps its gate; REUSE an existing 0-18/
> 0-19/0-14 for the first proof → zero gate concern.

## Verbatim source lines

From memory `project-ff9-13th-character`:

> id defaults to 12 (band 12-15).

> Band supports 12-15 (`CUSTOM_CHAR_MAX=15`; 4 custom chars).

> `custom_battle_model` (a) mints an editable copy
> of the donor's battle-MAIN GEO at a new id (≥6000, `Models/2/<id>/` — battle MAINs use the SAME path as field
> mains; only GEO_WEP uses BattleMap/BattleModel), (b) adds a new `BattleParameters` serial row (≥19) whose ModelId
> is the minted GEO but which REUSES the donor's 34 ANH clips

> register with `3DModelAnimation <key> <name>` (fresh AnimationDB keys ≥1M; `DataPatchers.cs:598`)

> (1) an unsanitized
> `[[playable]] name` with `;` flowed into the BaseStats Comment col (before Id) → column shift → `Byte.Parse` throws →
> `ConfirmQuit` HARD BOOT CRASH (a leading `#` silently drops the id-12 BaseStats row) → `parse_playable` now rejects
> `;`/`#`. (2) a bare `[party] add = [12]` for an UNDEFINED custom id built clean, emitted B_PARTYADD(12), then
> null-derefed at field load (no PLAYER allocated) → `build_mod` now hard-errors a numeric custom-band recruit with no
> mod-global `[[playable]]`.

From memory `project-ff9-ability-preset-system`:

> `preset = "custom"` (auto-allocates a custom-band preset 20-23)

> **The one HARD requirement:** the menu-open does an UNGUARDED `CommandSets[presetId]` index (`BattleHUD.cs:444`) → the new
> preset MUST ship its CommandSets row (KeyNotFoundException otherwise — this is the crash the kit's "20-254 menu_type
> crashes" comment warns about, avoidable by authoring the row).

> If the preset's `Abilities/<id>.csv` learn file ISN'T LOADED, HasAp=false → `GetAbilityState` skips ALL AP-gating
> (`BattleHUD.cs:1328`) → the char knows EVERY pool spell.

> **Custom-command band = {46 Reserve4, 35-40}** (unused enum rows; SKIP 45
> AccessMenu / 47 EnemyAtk; 48-99 engine-reserved).

> a NEW Actions.csv row in the **safe band 192-223** (the base
> is packed 0-191; `aa_data` is a `Dictionary<BattleAbilityId,AA_DATA>` with NO array bound + the loader gate is a FLOOR
> 0-191 -> 192+ is purely additive)

> (a) `status = ["Silence"]` -> the kit AUTO-MINTS a StatusSets row (band 100+, deduped by status list) + injects its id
> as the action's `statusIndex`.

> (b) `effect = "[code=TAG]...[/code]"` -> a minted `[[ability_feature]]`
> `>AA <rawId>` block (the engine casts the header id straight to BattleAbilityId in an uncapped Dictionary -- lift
> abilityfeatures `_AA_MAX` 191->223; the header uses the RAW pool id 192-223, NOT the AA:256 learn form).
