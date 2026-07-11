# Battle tuning — the 4-channel model, CSV/AI/seq, the B_MEMBER map

Distilled from memory `project-ff9-battle-tuning` (the deep recipe: formats, phase history, every
adversarial-review durable fact) and `project-ff9-battle-ai-members` (the selector map's canonical home).
Doc: `ff9mapkit/docs/BATTLE_DESIGN.md` (the complete lever map — §2 per channel, §3 mod-vs-DLL boundary).

## Contents

- [The 4-channel data model](#the-4-channel-data-model)
- [Channel 1 — raw16 enemy data](#channel-1--raw16-enemy-data)
- [BattlePatch.txt (by-name tuning)](#battlepatchtxt-by-name-tuning)
- [Channel 2 — CSV deltas](#channel-2--csv-deltas)
- [Channel 3 — enemy AI](#channel-3--enemy-ai)
- [The B_MEMBER(N) selector map](#the-b_membern-selector-map)
- [raw17 btlseq choreography](#raw17-btlseq-choreography)
- [Model swaps: body re-skin + palette swap](#model-swaps-body-re-skin--palette-swap)
- [Combat-math levers](#combat-math-levers)

## The 4-channel data model

The channels do NOT share a format or merge mode:

1. **Per-enemy stats/affinities/rewards** = per-scene BINARY `BTL_SCENE` (`dbfile0000.raw16`), a fixed
   116-byte `SB2_MON_PARM` per enemy TYPE. No CSV externalization for enemies — edit via raw16 byte-patch
   OR `BattlePatch.txt` reflection. (Layout: memory `project-ff9-battle-tuning` + `BTL_SCENE.cs`.)
2. **Shared player abilities, statuses, character growth** = externalized CSVs (`Data/Battle/*.csv`,
   `Data/Characters/*.csv`), merged per-id low-to-high.
3. **Enemy AI** = per-scene `EVT_BATTLE_*.eb` — the SAME `.eb` container + interpreter as fields.
4. **Encounter wiring** = per-field-script `SetRandomBattles` + `SetRandomBattleFrequency` — NOT a global
   formation table (the kit's `content/encounter.py`).

The only DLL needs: a genuinely NEW formula/scriptId (→ `references/scripts-dll-overload.md`) or a new
`CharacterId` (→ the `creating-ff9-characters` skill).

## Channel 1 — raw16 enemy data

- Inspect: `battle-scene <donor>`. Author: `[scene]` / `[[scene.enemy]]` in `battle.toml`.
- Coverage is ~ALL per-enemy levers (`battle/scene_data.py` `_MON_FIELDS`/`_MON_ELEM_FIELDS`/
  `_MON_STATUS_FIELDS`): hp/mp/gil/exp/ap, 4 stats, level, category, hit_rate, 4 defences, element
  affinities by name (`weak`/`null`/`absorb`/`half`), status masks, drop/steal, `flags`
  (incl. `non_dying_boss`), placement, `monster_count`, camera, model. Check the CODE for coverage, not a
  doc's "absent" column (the doc went stale once already).
- `monster_count` re-authors Main_Init's `InitObject` bindings up to the 4-enemy engine cap — spawning
  more enemies than the donor's AI was authored for corrupts event state (the "player twitch" bug).
- Do not hand-parse the 116-byte layout — offsets live once in the memory file and `battle/scene_codec.py`
  (golden round-trip proven).

## BattlePatch.txt (by-name tuning)

`[[battle_patch]]` (scene-scoped) + `[[battle_enemy]]`/`[[battle_attack]]` (global by-name — retune every
enemy/attack of that name across ALL scenes, the campaign-wide lever). Reaches the BP-ONLY fields
(drop/steal RATE arrays, BonusElement, MaxDamageLimit/MaxMpDamageLimit, WinCardRate) and the enemy
ATTACK table (`AA_DATA` — enemy attacks are NOT Actions.csv). Gotchas (all engine-verified, memory
`project-ff9-battle-tuning`):

- `status_set`/`AddStatusNo` is a **StatusSetId ROW (0-38), not a status** — 16 = the "Dispel" bundle,
  Poison = 20; 39+ = a KeyNotFoundException crash (the kit caps it).
- Selector grammar is STATEFUL — scene flags must precede narrower selectors (the emitter enforces order).
- Emit INTEGER masks for enums (`Enum.Parse` accepts any int, unbounded); `True`/`False` for bools.
- A BattlePatch change needs a RELAUNCH.

## Channel 2 — CSV deltas

`[[battle_action]]` → Actions.csv, `[[status]]`/`[[status_set]]` → StatusData/StatusSets.csv,
`[[character]]` → BaseStats.csv, `[[leveling]]` → Leveling.csv, `[[ability_gem]]`, `[[command_set]]`,
`[[learn]]`, `[[magic_sword_set]]`, `[[character_param]]`, `[[ability_feature]]` → AbilityFeatures.txt.
Durable facts (each cost a bug):

- Merge is per-id **whole-ROW replacement** — to change one field, emit the COMPLETE row (the kit reads
  the base row live from the install) and preserve the base file's `#!` option lines (parsed per-file).
- Leveling.csv (+ Abilities/<Name>.csv, InitialItems) are WHOLE-FILE highest-wins — a partial file WIPES
  the curve; re-emit all 99 rows.
- The install's Data CSVs are **cp1252, NOT UTF-8** (curly apostrophes in 4 action names).
- Range-check Byte/UInt16 columns OFFLINE — an out-of-range value = a null row = **the game quits at boot**.
- `BattleParameters.csv` is COSMETIC (model/anims); real combat stats are `BaseStats.csv`.

## Channel 3 — enemy AI

The staged stack (all in-game proven): read → same-length patch → assemble → insert → lint.

- **Read:** `battle-ai <scene>` (annotated disassembly; entry `1+T` = type T's AI by convention, but see
  the binding trap below). `battle-ai <scene> --sites` lists patchable numeric literals.
- **Same-length patch:** `[[scene.ai_patch]]` — `at` (from `--sites`) + a REQUIRED `old` guard + `new`
  (same width; `B_CONST4` values cap at `0x3FFFFFF` — engine-masked).
- **Author:** `[[scene.ai_function]]` (replace/add a function; body must end in a flow TERMINATOR),
  `[[scene.ai_insert]]` (fragment at a `before`/`after`/`at` locator), `[[scene.ai_phase]]`
  (`stat`/`below`/`then`/`else` — generates the relative `cur < max/N` branch before the `Attack`).
  Assemblers: `eb/exprasm.py` + `eb/cmdasm.py` (round-trip self-verifying); `battle-ai --asm`/`--asm-block`.
- **Lint:** `battle-ai --lint` / build-time `lint_ai` — jump bounds, reachable terminator, Attack index
  (562-scene sweep = 0 false positives).

Dispatch model (load-bearing for WHICH tag to edit): a normal enemy turn dispatches to **tag 7 (ATB)**,
but tag 7 only sets ATB timing — **the `Attack` command lives in tag 5** (RET tag 5 to neutralize an
enemy; proven). Tag 6 = Counter, tag 9 = Dying, tag 1 = Main (runs once at Init). The AI ENTRY is bound
by Main_Init's `InitObject`, possibly switched on `B_SYSVAR[31]` = the PICKED PATTERN index, not the
enemy type — `[[scene.enemy]] ai_entry = N` overrides the generic binding for offset-entry donors.
Enemy attack selection is a per-slot SEED (`Instance.Int24[0]`, four 6-bit slot indices) — RESEED it to
change the attack; forcing the final `Attack` index desyncs target/category and fizzles.

## The B_MEMBER(N) selector map

Canonical home: memory `project-ff9-battle-ai-members` (sourced from `btl_scrp.GetCharacterData`).
Quoted verbatim from it:

> **`N` is a SWITCH-CASE selector in `btl_scrp.GetCharacterData(BTL_DATA, id)` — NOT a byte offset, NOT a
> table index.**

> **`B_SYSLIST[1]` = the acting unit (SELF/caster), `B_SYSLIST[0]` = the target.** The **setter is
> symmetric** (`SetCharacterData`, `btl_scrp.cs:415+`, same case numbers)

> **NOT the same as `B_CURHP`/`B_MAXHP`** (op_binary 82/83): those call `GetPlayer(chr2slot(arg)).cur.hp` — a
> PARTY-slot read, useless for an enemy reading itself. For enemy-self HP use `B_MEMBER(36)`/`(35)`.

| N | field | | N | field |
|---|---|---|---|---|
| 35 | **max.hp (MAX HP)** | | 52 | bi.target |
| 36 | **cur.hp (CURRENT HP)** | | 53 | bi.disappear |
| 37 | max.mp | | 55/56 | model scale set/reset (WRITE-only, no read case) |
| 38 | cur.mp | | 57 | dms_geo_id (model id) |
| 39 | max.at (max ATB) | | 64 | bi.row (front/back) |
| 40 | cur.at (ATB gauge) | | 65 | bi.line_no (slot 0-7) |
| 41 | level | | 72/73 | elem.str / elem.mgc |
| 42/43 | stat.invalid hi/lo (immune set) | | 74/75 | PhysicalDefence / PhysicalEvade |
| 44/45 | stat.permanent hi/lo | | 76/77 | MagicalDefence / MagicalEvade |
| 46/47 | **stat.cur hi/lo (CURRENT status)** | | 100-103 / 104-107 | steal / drop item[0..3] |
| 48/49/50/51 | def_attr invalid/absorb/half/weak (elements) | | 112 / 114 | cur motion id / cur attack id |
| | | | 140/141/142 | pos x / -y / z (143-145 = rot) |
| | | | 146/147/148 | bonus_exp / bonus_gil / trance |

The "below half HP" idiom 56 shipping bosses use (a member compare MUST go through the `_E`/extract op):

> `SET({B_SYSLIST[1] B_MEMBER(36) B_SYSLIST[1] B_MEMBER(35) B_PICK const(2) B_DIV B_LT_E B_COUNT B_EXPR_END}); JMP_IFNOT(...)`
> = "if cur < max/2"

Boss AI can also gate on absolute HP constants — after retuning `hp`, re-read the AI and fix thresholds
via `[[scene.ai_patch]]` (or generate a relative gate with `[[scene.ai_phase]]`).

## raw17 btlseq choreography

The attack choreography (animation/timing/camera/vfx/sfx) — real gameplay, not fluff (each `Calc`
opcode = a damage pass; hit-count = total damage). Fixed 34-opcode vocabulary (a new opcode = DLL).

- Read: `battle-seq <scene>` (+ `--sites` for patch targets). Lint: `battle-seq --lint` (Anim index +
  camera-id bounds — the two refs the engine doesn't check). Assemble: `battle-seq --asm`.
- Edit: `[[scene.seq_patch]]` (same-length, `old`-guarded), `[[scene.seq_replace]]` (whole body),
  `[[scene.seq_insert]]` (fragment splice; the whole raw17 repacks).
- **Timing fact (verbatim from memory):** "the sequence interpreter ticks ~15 fps — `Wait(frames=150)` ≈
  10 s in real time".
- 289/562 scenes ALIAS one body across several attack indices — a patch there rewrites ALL of them
  (surfaced in `--sites`, warned on apply). raw17 is language-independent (one patch, all langs).
- Format details (the +4 offset skew, header, opcode-34 crash guard): memory `project-ff9-battle-tuning`
  + `battle/seqcodec.py`.

## Model swaps: body re-skin + palette swap

- `[[scene.enemy]] model=`/`model_scene=`+`model_type=` — transplant a real donor enemy's model block.
  It is a BODY re-skin, NOT full: the per-ATTACK animation stays bound by the donor scene's raw17
  (`Konran@78`), so the attack plays the target's clip retargeted (never crashes — clips load by name).
  Battle geo names are `GEO_MON_B3_*` — DISJOINT from the field/InfoHub `GEO_MON_F0_*` space.
- `[[scene.enemy]] skin = { id, hue|tint|textures }` — palette-swap: mints a recolored variant model at
  a new id (`Geo@30` takes a minted i16 id, cap 32767); keeps its own skeleton/clips; composes after a
  `model=` transplant. Relaunch (DictionaryPatch).

## Combat-math levers

Damage `Base = Power - Defence` floored at 1 → Defence is SUBTRACTIVE (a wall when Power <= Def, ~free
when Power >> Def). Weakness x1.5 / half x0.5 / absorb heals — element affinity is the biggest one-edit
swing. Enemy Level is multi-purpose (variance, magic resist, steal difficulty, gates the Level-N spell
family). AP is per-FORMATION, awarded whole (`[scene] ap`). Full math notes: `BATTLE_DESIGN.md` §5.
