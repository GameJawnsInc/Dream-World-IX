---
name: authoring-ff9-field-scripts
description: Author or edit a field's `.eb` bytecode and event logic -- the engine substrate shared by novel fields, fork edits, and chocobo lanes. Use when running `logic-map`/`logic-add`/`logic-edit`/`lint-eb`/`disasm`, adding story flags, gateways/warps, chests/events, encounters, dialogue choices, cutscenes, ATEs, ladders, jumps, savepoints, or moving platforms -- or debugging a softlock, per-frame IndexOutOfRange log-spam, a `0x2A`-Battle-instead-of-warp crash, or a story flag that will not persist. Covers opcode traps (`Battle 0x2A` vs `Field 0x2B`, `0x01` JMP, `SETCAM`/`BGCACTIVE`), the `0x05`+`0x7F` RPN expression sub-language, `GLOB(0xC4)` save-backed vs `MAP(0xC5)` transient flags and the >=8512 safe band, region tags 2/3/10 and fade-before-`Field()`, talk-func >=9 bytes, and actor choreography in LOOP-not-Init. This owns AUTHORING `gEventGlobal` flags in an `.eb`; for reading/comparing/editing a save file's flags/items/stats see `editing-ff9-items-and-saves`; for camera/walkmesh/art see `authoring-ff9-scenes`.
---

> Thin router — link the canonical doc (Layer 3) and the memory recipe (Layer 2); do NOT recopy opcode tables, TOML schemas, or coast laws — those live once in docs/ and memory/ and would rot if forked here.

# Authoring FF9 Field Scripts

`.eb` is the shared engine substrate: novel fields, fork edits, and chocobo lanes all compile down to it. Author it in Python via the kit — never Hades Workshop (HW entry-adds corrupt the file; see brief §8). Runtime always loads the compiled `.eb` (no text→.eb path); per-language `.eb` differ ONLY in the 84-byte name field — bytecode is language-identical → byte-patch the code region at the same offset in all 7 langs. Verify every edit with `disasm` before deploy.

Wikilinks like `[[project-ff9-...]]` below are inert read-this pointers: open that file in the project memory store (`~/.claude/projects/C--gd-Dream-World-IX/memory/`).

## .eb format at a glance

Format: 44B header + 84B PSX name → entry table at offset **128** (10 slots × 8B); a function's `fpos` is measured from `entryStart+2`; 2-byte opcodes are prefixed `0xFF`. Full format + opcode detail → `references/eb-opcodes.md` (which names `ff9mapkit/ff9mapkit/eb/_optables.py` as the authoritative source — never fork it).

## Opcode traps (the crash list)

Opcode traps worth memorizing: **`Battle = 0x2A`** (NOT PreloadField — encoding a warp as 0x2A starts a battle on a bad scene id → crash/black); real `PreloadField = 0xFD` is a no-op HINT on Steam; `Field = 0x2B` is the real warp; **`0x01` is an undocumented unconditional JMP** (don't overwrite a Wait that sits right after it — the activation is skipped). Camera/scroll mechanics: **`SETCAM = 0x7E`** (switch active camera), **`BGCACTIVE = 0x71`** (enable scroll / camera-services). **THE OBJECT-INIT GATE LAW:** an object's Init must NEVER return before `SetModel` -- a passing gate loads the object permanently HIDDEN (interactable, unrendered; 18688 stock inits, zero early returns). Story-gate the `InitObject` CALL SITE in Main_Init instead (`region.guarded_call`; the invisible-innkeeper bisect -> the stolen-ember memory).

## Expression sub-language

Opcode `0x05` + a `0x7F`-terminated RPN stack; var token byte = `0xC0 | (type<<2) | source`. `B_SYSVAR=0x7A` (code 9 = `GetChoose`, reads the picked choice row); `GetItemCount` = expr fn `0x64`. Reusable for chests/levers/choices. Detail → `references/eb-opcodes.md`.

## Flag persistence: GLOB vs MAP

A var's **source** decides persistence: **GLOB (src 0, `0xC4`) = save-backed `gEventGlobal`** (2048 bytes, persists across field reloads + saves) vs **MAP (src 1, `0xC5`) = per-field, WIPED on every field load.** HW naming is INVERTED. `EventContext.mapvar` is only 80 bytes → a high MAP index is out-of-bounds = hard crash. Use GLOB for chests / story flags / cutscene-once; safe band = bit >= 8512; indices > 0xFF need the long-index token encoding. A `once=true` event/cutscene won't replay for testing once its flag is set → use F6 → Flags → reset (or `once=false` / a fresh New Game). Detail → `references/flags.md`.

## Regions & gateways

Region tag 2 = tread (every frame in the quad), tag 3 = press-to-interact (func MUST be >= 9 bytes or per-frame IndexOutOfRange log-spam), tag 10 = Main_Reinit. Triggers fire only when `usercontrol == 1`; polygon point ORDER sets the exit walk-out direction; `IsInQuad` tests a fan of consecutive vertex-triplets (collinear = dead zone — use a convex quad with the last vertex DOUBLED); a field→field warp MUST fade to black BEFORE `Field()`. Detail (incl. region arming + the >2-region silent-arming bug) → `references/regions-encounters.md`.

## Encounters & the after-battle fix

A field cloned from a cutscene field needs an entry-0 tag-10 Main_Reinit or it softlocks after battle (`EnterBattleEnd` suspends objects; nothing resumes them). BattlePatch `Music:` = the akao **song-play id** (0 = Battle Theme), NOT a file number; field BGM = `RunSoundCode(0, <song id>)`. Detail → `references/regions-encounters.md`.

## Cutscene choreography rules

Actor choreography runs in the NPC's **LOOP (tag 1), not its Init (tag 0)** — Init runs at `state == 2` where `ProcessAnime` never advances `animFrame` (transform moves, skeleton freezes). A warm-up `Wait(~30)` before the first actor command; `SetWalkTurnSpeed(255)` before walks (else orbit/softlock); **never `WaitTurn`/`WaitAnimation` on a player-cloned NPC** (softlock — instant turns + a fixed `Wait(40)`); `MoveInstantXZY` args are `(worldX, −worldY, worldZ)` + `SetPathing(1)` after. Read `[[project-ff9-cutscene-multiactor]]` (conductor model for multi-actor scenes).

## Dialogue, choices, ladders, jumps, savepoints, ATEs, platforms

- **Dialogue + choices** — speaker tags, auto-wrap, NPC/zone choices, flag-gated rows → `ff9mapkit/docs/DIALOGUE.md`.
- **Ladders** — navigable vertical/slant/bent shapes, floor/gateway/worldmap tops, re-entry → the "NAVIGABLE LADDER" section of `[[project-ff9-eb-script-tooling]]`.
- **Jumps** — ladder mechanism minus the climb loop → `[[project-ff9-jump-navigation]]`.
- **Savepoints** — synthesized `Menu(4,0)` + region → `ff9mapkit/docs/SAVEPOINT.md` + `[[project-ff9-savepoint]]`.
- **ATEs** — both flavors (optional blue menu + grey unskippable) → `ff9mapkit/docs/ATE_SYSTEM.md` + `[[project-ff9-ate-system]]`.
- **Moving platforms / elevators** — advanced interactables: `--verbatim` carries them; a declarative `[[platform]]` block is the frontier → `[[project-ff9-moving-platforms-elevators]]`.

## Editing a verbatim fork's .eb in place

`logic-map` (decode/read the entangled script), `lint-eb` (validate), `logic-edit`/`logic-add` (edit/add in place — the whole EDIT tier is in-game proven). Read `[[project-ff9-field-logic-map]]`; for the fork workflow itself see the `forking-ff9-fields` skill.

## Additional resources

- Docs (Layer 3): `ff9mapkit/docs/FORMAT.md` (field.toml schema), `DIALOGUE.md`, `ATE_SYSTEM.md`, `SAVEPOINT.md`, `GLOBAL_RESOURCES.md`.
- Memory (Layer 2): `[[project-ff9-eb-script-tooling]]` (the `.eb` bible), `[[project-ff9-story-flags]]` (incl. flag scopes), `[[project-ff9-gateway-regions]]` (incl. region arming), `[[project-ff9-encounters]]` (incl. the song-0 fork battle-BGM fix), `[[project-ff9-moving-platforms-elevators]]`.
