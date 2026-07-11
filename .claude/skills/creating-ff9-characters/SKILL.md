---
name: creating-ff9-characters
description: Create a genuinely new playable FF9 character (a 13th/14th `CharacterId`, zero DLL) via the `[[playable]]` TOML block. Use when the user adds a new party member or playable character, authors a bespoke ability kit / minted command / custom ability / status / effect, sets `[party]` or `[playable.abilities]`, swaps the controlled player (`--swap-player`), or works with the thirteenth-character example. Covers the CSV allocator + `CharacterDefaultName` + `B_PARTYADD` recruit path, `custom_battle_model` / `custom_battle_anims` / `portrait`, own `CharacterPresetId>=20` command menu + learn list, minted `command1`/`command2` -> new `BattleCommandId`, custom `Actions.csv` ability (192-223), `status=[names]` auto-mint, `effect='[code=...]'`, PC-control vs party-state, and the caveats (rename screen, leader-only field render). Compiles at build time (no dedicated CLI verb). For the engine battle-formula engine see `authoring-ff9-battles`; for the model mesh see `authoring-ff9-models`.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Creating FF9 Characters

Mint a genuinely NEW engine `CharacterId` — a 13th (14th, ...) party member alongside all 12 canon
characters — with the `[[playable]]` block in a `field.toml`. Zero DLL. **No dedicated CLI verb; the block
compiles at build time** (deploy like any field — the one exception is `playable-anims`, the Blender
animset edit loop). Canonical schema: `ff9mapkit/docs/FORMAT.md` `[[playable]]` section (key tables quoted
in `references/playable-schema.md`); worked example: `ff9mapkit/examples/thirteenth-character/iviv.field.toml`
(READ ONLY — never edit a bundled example in place).

Test loop: deploy -> **RELAUNCH** (the CSVs + name directive load at startup; F6 Reload won't) -> **New
Game** (the engine inits the party with the new id present) -> F6 warp -> verify menu / fight / save-reload.

## Allocate the character

`[[playable]] name / borrow / recruit / id / stats / params`. The CharacterParameters CSV row IS the
allocator (the engine roster is an unbounded `Dictionary<CharacterId,PLAYER>`); the name ships as
`CharacterDefaultName <id> <SYM> <name>` DictionaryPatch lines (all 7 langs); `recruit = true` prepends the
real `B_PARTYADD` (expression op `0x6D`) to Main_Init. `name` must not contain `;` or `#` (CSV corruption ->
boot crash; the parser rejects them). Safe id bands per CSV -> `references/id-band-allocations.md`. Deep
recipe + engine facts: read memory `[[project-ff9-13th-character]]`.

## Battle model / animset / portrait

- `custom_battle_model = true` — mint an independent, editable copy of the borrow's battle model bound to
  this character (own serial + BattleParameters row); the donor is never touched.
- `custom_battle_anims = true` — its own `Animations/<mintId>/` clip copies + `3DModelAnimation`
  registrations. Edit loop: `ff9mapkit playable-anims <toml> --export <glb>` -> Blender -> `--edit --deploy`;
  persist edits across re-deploys via `anim_edits = "x.glb"`.
- `portrait = "art/x.png"` — a 132x190 PNG -> a loose Face-Atlas sprite override (implies a battle serial).

Mesh/texture editing itself is the models pillar -> skill `authoring-ff9-models`, memory
`[[project-ff9-custom-models]]`.

## Ability preset

`[playable.abilities] preset = "custom"` allocates the character's OWN `CharacterPresetId` (band 20-23):
its own command menu (CommandSets row) + curated learn list (`Abilities/<id>.csv`; `ap = 0` = usable now).
`menu_from` names the base preset to clone/seed (defaults to the borrow; REQUIRED for a guest borrow 8-11).
The learn file must actually deploy — without it, AP-gating silently vanishes and the character knows every
pool spell. Read memory `[[project-ff9-ability-preset-system]]`.

## Minted command

`command1` / `command2` take a stock `BattleCommandId` name OR an inline `{ name, abilities }` table that
MINTS a new `BattleCommandId` (safe band: 46, then 35-40) with its own ability pool + a `com_name.mes` name
overlay. The menu shows the pool INTERSECT the learn list — a pool with no learned members opens empty.

## Custom active ability

An inline `{ name, from, power, element, mp, rate }` in a command pool mints a new `Actions.csv` row
(band 192-223) CLONED from the `from` donor and retuned, + an `aa_name.mes` overlay. Two number-spaces:
the command pool holds the RAW id; the learn file holds `AA:<id>` — mixing them is a boot crash / silent
dead spell (details in `references/id-band-allocations.md`). `power` tunes damage only if the donor's
script reads it (black/white magic yes; weapon/physical scripts no). The VFX is the donor's — clone from
the matching element for a matching look.

## status / effect

- `status = ["Silence", ...]` auto-mints a StatusSets row (band 100+) and injects the action's
  `statusIndex` (crash-safe by construction). Lands only if the donor formula applies statuses AND
  `rate` is non-zero.
- `effect = "[code=TAG] ... [/code]"` mints an `[[ability_feature]]` block keyed on the ability
  (Power/Element/MPCost/HitRate/...). Battle-side hook only — the out-of-battle field menu shows the
  base value.
- `script = { template/body }` — a genuinely NEW battle formula — is the Scripts-DLL channel: see skill
  `authoring-ff9-battles` and memory `[[project-ff9-scripts-dll]]`.

## PC-control vs party-state

Two decoupled systems. Field CONTROL (who you walk as) binds to the LAST unconditional
`DefinePlayerCharacter` (0x2C) by InitObject order — read memory `[[project-ff9-non-zidane-donors]]`.
PARTY state (the menu/battle roster) is `[party] add/remove` for existing characters, or `[[playable]]
recruit` for a custom one — read memory `[[project-ff9-pc-party-system]]`. `import --swap-player
<char|model>` changes who you walk as, never the party.

## Known caveats

- NEVER open the in-game rename screen for a custom id — `NameSettingUI`'s hardcoded `<12` reseed makes
  id 12 collide with "rename Zidane" (opening it overwrites Zidane). The name comes from the DictionaryPatch.
- FF9 renders only the party LEADER in the field — a custom member shows in menu/battle, not as a walking
  follower (`SetupPartyUID` aliases a custom id's field actor to an existing band).
- Magic drives BOTH spell damage AND the MP pool — tune one spell via its own `power` (when the donor
  script reads it), never by flooring the character's Magic stat.

## Additional resources

- Canonical schema: `ff9mapkit/docs/FORMAT.md` — the `[[playable]]` section (quoted, not forked, in
  `references/playable-schema.md`).
- Id bands + crash modes: `references/id-band-allocations.md`.
- Worked example: `ff9mapkit/examples/thirteenth-character/` (Iviv + Steiniv, two rigs; READ ONLY).
- Memory recipes (read on demand): `[[project-ff9-13th-character]]`,
  `[[project-ff9-ability-preset-system]]`, `[[project-ff9-pc-party-system]]`,
  `[[project-ff9-non-zidane-donors]]`.
- Sibling skills: `authoring-ff9-battles` (battle formulas / tuning / Scripts-DLL),
  `authoring-ff9-models` (mesh + animation editing).
