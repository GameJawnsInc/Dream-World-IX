# BATTLE_DESIGN.md — FF9 battle tuning & encounter authoring (the honest gap map)

> Recon synthesis (2026-06-12, `battle_design` branch). Scope: tune existing battles + author new
> encounters with **stock monster models**, on **stock Memoria (no engine-DLL rebuild)**. Every claim cites
> Memoria source `file:line` / a CSV column / a raw16 byte offset. This is the battle analog of
> `FORK_FIDELITY.md`: what the kit can already do, what it can't yet, and the prioritized path.
>
> Provenance: this doc is analysis + citations only — **zero Square-Enix bytes**. All enemy stat bytes and
> all CSV stat values are SE game DATA → read live from the user's install, never committed (the
> `itemstats.py` read-live vs `_itemdb.py` committed-names split).

---

## 1. Executive summary

"Tweaking battles" / "authoring encounters" in FF9 touches **four structurally different data channels** that
do NOT share a format or a merge model:

1. **Per-enemy stats / affinities / rewards** → a **per-scene binary**, `BTL_SCENE` (`dbfile0000.raw16`): a
   fixed **116-byte `SB2_MON_PARM`** per enemy *type*. There is **no CSV externalization** for enemy
   parameters — the only channels are a raw16 byte-patch or `BattlePatch.txt` reflection. (`BTL_SCENE.cs:50-125`)
2. **Shared actions/abilities (player + the player-side of enemy resolution), statuses, character growth** →
   **externalized human-readable CSVs** (`Data/Battle/*.csv`, `Data/Characters/*.csv`) that merge
   **per-id, partial-delta, low→high** across mod folders. (`FF9BattleDB.cs:56-65`, `AssetManager.cs:849-854`)
3. **Enemy AI** → the per-scene **`EVT_BATTLE_*.eb`** — the *same* `.eb` bytecode container + the *same*
   `EventEngine.DoEventCode()` interpreter as field scripts, with battle opcodes (`Attack 0x38`,
   `AttackSpecial 0xE5`) and battle expression reads. (`EbScript.from_bytes(x).to_bytes()==x` proven on real
   `EF_R007`/`BU_E072`/`AC_E031`)
4. **Encounter wiring** (which scenes a field rolls, how often) → **per-field-script state** set by
   `SetRandomBattles 0x3C` + `SetRandomBattleFrequency 0x57` — *not* a global formation table.
   (`EventEngine.DoEventCode.cs:978-992`)

**The no-DLL boundary is wide.** Every per-enemy field, every action/status CSV, every AI `.eb`, the encounter
wiring, and the BGM are stock-Memoria data-patches. The **only** DLL needs are (a) a *brand-new* battle-calc
formula / `scriptId` behavior — and even that is a separate, swappable **`Memoria.Scripts.<Mod>.dll`** loaded
per mod folder via `Assembly.LoadFile` (`ScriptsLoader.cs:283-291`), **NOT** the engine `Assembly-CSharp.dll` —
and (b) engine-enum changes (e.g. a wholly new `CharacterId`). The kit's `[scene]` tuner today reaches **~9 of
~40+ patchable enemy fields** and **zero** of the CSV/AI channels.

---

## 2. The complete lever map

Channel legend: **CSV** = `Data/*.csv` partial-delta merge · **raw16** = `dbfile0000.raw16` byte-patch ·
**raw17** = `btlseq.raw17` · **eb** = `EVT_BATTLE_*.eb` bytecode · **BP** = `BattlePatch.txt` reflection ·
**DP** = `DictionaryPatch.txt` · **DLL** = compiled C#.

### (a) Per-enemy stats / affinities / rewards — `SB2_MON_PARM` (raw16)

Offsets are **relative to the 116-byte monster block** at `8 + 56*PatCount + 116*t`, verified field-by-field
against the `BTL_SCENE.cs:53-122` read order + an empirical `EF_R007` parse. On disk the widths are
`u8`/`u16` (the struct widens several to `Int32`/`UInt32`).

| Lever | Controls | Channel | Location | DLL? | Kit |
|---|---|---|---|---|---|
| MaxHP / MaxMP | health / mana pool (turns-to-kill) | raw16 / BP | `@12 u16` / `@14 u16` | No | **done** |
| WinGil / WinExp | gil + EXP reward | raw16 / BP | `@16 u16` / `@18 u16` | No | **done** |
| WinItems[4] / StealItems[4] | 4 drop / 4 steal item ids (255=none) | raw16 / BP | `@20` / `@24`, 4×u8 | No | **done** (ids) |
| **WinItemRates[4] / StealItemRates[4]** | drop/steal **odds** | **BP only** | not in raw16; `[PatchableField]` arrays, defaults `{256,96,32,1}` / `{256,64,16,1}` (`SB2_MON_PARM.cs:53-60`) | No | **done** (BP `drop_rates`/`steal_rates`) |
| Radius / Geo / Mot[6] / Mesh[2] | collision + **model + 6 anim ids** (re-skin to a stock monster) | **raw16 only** | `@28 u16`, `@30 i16`, `@32` 6×u16, `@44` 2×u16 | No | **done (BODY re-skin, ★ in-game proven)** — `[[scene.enemy]] model=`/`model_scene=` transplants a real donor enemy's model block (`reskin.py`); the new model's idle/damage/death play (Mot-driven), but the ATTACK anim stays the target's (raw17-bound, retargeted onto the new mesh, `AnimationFactory.cs:60`) → build WARNS. Proven: a Goblin→Fang re-skin idled as a quadruped Fang but attacked Goblin-like |
| Flags | per-enemy MON flags (die_atk/die_dmg/**non_dying_boss** = survives HP=0) | **raw16 only** | `@48 u16` | No | **done** (`[[scene.enemy]] flags`; names or raw int) |
| AP (per-type) | type AP (note: the gameplay AP is the *pattern* AP) | **raw16 only** | `@50 u16` (not `[PatchableField]`) | No | **n/a** — inert for rewards; the gameplay AP = the pattern AP (`[scene] ap`, **done**) |
| Speed / Strength / Magic / Spirit | the 4 core battle stats | raw16 / BP | `@52/@53/@54/@55` u8 | No | **done** |
| (pad/trans/cur_capa/max_capa) | trance/capacity — inert for enemies | — | `@56-59` | — | pass-through |
| **GuardElement / AbsorbElement / HalfElement / WeakElement** | per-element immune / absorb / halve / weak | raw16 / BP | `@60/@61/@62/@63` u8 bitmask | No | **done** (`[scene]` `null`/`absorb`/`half`/`weak`, by name; + BP) |
| **BonusElement** | element the enemy's OWN attacks are imbued with | **BP only** | not in raw16; `[PatchableField]` (`SB2_MON_PARM.cs:85`) | No | **done** (BP `bonus_element`) |
| Level | level (variance, magic resist, steal, Level-N spells) | raw16 / BP | `@64 u8` | No | **done** |
| Category | race / killer / flight / undead / death-react | raw16 / BP | `@65 u8` | No | **done** (`[scene] category` + BP) |
| HitRate | enemy physical accuracy | raw16 / BP | `@66 u8` | No | **done** (`[scene] hit_rate` + BP) |
| **PhysicalDefence / PhysicalEvade / MagicalDefence / MagicalEvade** | the 4 defences | raw16 / BP | `@67/@68/@69/@70` u8 | No | **done** (`[scene]` phys/mag def+evade; + BP) |
| BlueMagic | Quina Eat / learn id | raw16 / BP | `@71 u8` | No | **done** (`[scene] blue_magic` + BP) |
| **ResistStatus / AutoStatus / InitialStatus** | immune / permanent / starting statuses (32-bit `BattleStatus` masks) | raw16 / BP | `@0/@4/@8` u32 LE | No | **done** (`[scene]` resist/auto/initial_status, by name; + BP) |
| WinCard | Tetra Master card drop | raw16 / BP | `@105 u8`; rate = `DefaultWinCardRate=32` constant | No | **done** (`[scene] win_card`; + BP `win_card_rate`) |
| **MaxDamageLimit / MaxMpDamageLimit** | per-enemy >9999 break-damage-limit | **BP only** | not in raw16; `[PatchableField]`, default `FF9PLAY_DAMAGE_MAX` (`SB2_MON_PARM.cs:20-21`) | No | **done** (BP `max_damage_limit`/`max_mp_damage_limit`) |
| Bone/SFX/Shadow/Icon/Konran/MesCnt | cosmetics / SFX / message count | raw16 only | `@72-114` | No | **partial** — carried as a BLOCK by the re-skin transplant (`reskin.py`); not individually tunable (Konran/MesCnt deliberately NOT carried — raw17/text linkage) |

> **`[PatchableField]` = "by-name without re-packing":** the status masks, all 5 element bytes, Level,
> Category, HitRate, all 4 def/evade, BlueMagic, gil/EXP/drop/steal + the rate arrays + MaxDamageLimit all
> carry `[Memoria.PatchableFieldAttribute]` (`SB2_MON_PARM.cs:33-109`), so `BattlePatch.txt` sets them by
> FieldInfo name (`DataPatchers.cs:99-113`). A few `[PatchableField]`s (WinItemRates/StealItemRates,
> BonusElement, MaxDamageLimit) are **not in the raw16 disk layout at all** → reachable ONLY via BattlePatch.
> **Not `[PatchableField]`** (so unreachable by BattlePatch — but the kit reaches them by **raw16 byte-patch**
> via `[scene]`/`[[scene.enemy]]`): `Flags@48` (`flags` lever) + the model wiring (`Radius/Geo/Mot/Mesh`, the
> re-skin). Genuinely inert / not exposed: `AP@50` (per-type; the gameplay AP is the *pattern* AP), the
> individual cosmetics, and `MonsterCount` (commented out, `SB2_PATTERN.cs:16`; the kit sets it directly anyway).

### (a′) Per-enemy ATTACK table — `AA_DATA[]` at the raw16 TAIL

Enemy attacks are **not** in `Actions.csv` — they live inline in the raw16 at `8 + 56*PatCount + 116*TypCount`,
one 16-byte `AA_DATA` per attack (`BTL_SCENE.cs:127-153`): a 4-byte bit-packed `BattleCommandInfo`
(Target/DefaultAlly/DisplayStats/VfxIndex/sfx/ForDead/Camera/OnDead) + `ScriptId, Power, Elements, Rate,
Category, AddStatusNo, MP, Type` (8×u8) + `Vfx2` u16 + `Name` u16. **Power/Elements/Rate are single BYTES here
(0-255).** The raw17 `btlseq` binds which attack indices belong to which monster (`EnemyGetAttackList` →
`GetEnemyIndexOfSequence`); the AI `.eb` selects among them. Tunable via raw16 byte-patch OR
`BattlePatch.txt`'s `Attack`/`AnyAttackByName` token (reflection on `AA_DATA`/`BTL_REF` `[PatchableField]`s,
`DataPatchers.cs:114-130`). **Kit: done via BattlePatch** — `[[battle_attack]]` (global `AnyAttackByName:`) /
`[[battle_patch.attack]]` (scene-scoped) reach the `AA_DATA`/`BTL_REF` attack table by name or index
(`battlepatch.ATTACK_FIELDS`: power/elements/rate/script/mp/category/type/status_set). `[scene]` (raw16) still
does NOT reach it (`scene_data` stops at the monster blocks).

### (a″) Formation / pattern — `SB2_PATTERN` + `SB2_PUT` (raw16)

| Lever | Controls | Channel | Location | DLL? | Kit |
|---|---|---|---|---|---|
| MonsterCount | # active enemies (engine cap 4) | raw16 only | `pattern+1 u8` | No | **done** |
| Camera | which camera index | raw16 / BP | `pattern+2 u8` | No | **done** |
| pattern Rate | spawn-rate weight of this formation | raw16 / BP | `pattern+0 u8` | No | **done via BP** (`[[battle_patch.pattern]] rate`); raw16/`[scene]` still absent |
| **pattern AP** | the **gameplay-effective** AP reward (whole, undivided) | raw16 / BP | `pattern+4 u32`; consumed `btlseq.cs:475` | No | **done** (raw16 `[scene] ap` → every pattern+4; + BP `[[battle_patch.pattern]] ap`) |
| SB2_PUT type/x/y/z/rot | per-slot enemy type + placement | raw16 | `pattern+8 + 12*j`: `TypeNo@0 Flags@1 X@4 Y@6 Z@8 Rot@10` | No | **done** |

### (a‴) Scene-wide rules — `SB2_HEAD.Flags` / `BTL_SCENE_INFO`

`SpecialStart`(preemptive) / `BackAttack` / `Runaway`(can-escape) / `NoGameOver` / `NoExp` / `WinPose` /
`NoMagical` / `ReverseAttack` / `FixedCamera1/2` / `AfterEvent` — decoded from `header.Flags @4 u16`
(`BTL_SCENE.cs:214-230`), all `[PatchableField]` on `BTL_SCENE_INFO`. **Kit: done via the BattlePatch SCENE token**
— `[[battle_patch]] scene = <id>` + any boolean: `special_start`/`preemptive`, `back_attack`, `runaway`/`can_escape`,
`no_game_over`, `no_exp`, `win_pose`, `no_magical`, `reverse_attack`, `fixed_camera1`/`fixed_camera2`, `after_event`
(`battlepatch.SCENE_FLAGS`, validated + CLI `battle-patch`). The raw16 byte-patch of `SB2_HEAD.Flags @4` is NOT
implemented — the raw16 `flags` key targets the per-enemy MON Flags @48, a separate lever.

### (b) Enemy AI — `EVT_BATTLE_*.eb`

| Lever | Controls | Channel | Location | DLL? | Kit |
|---|---|---|---|---|---|
| Spawn / AI binding | `InitObject(1+type, 0x80+slot)` per slot | eb | `event_data.rewrite_main_init`; `EventEngine.cs:560-571` | No | **done** (`[scene] monster_count` → one InitObject/slot; `[[scene.enemy]] ai_entry = N` overrides the `1+type` bind for offset-entry donors) |
| Attack select | which scene attack (0..AtkCount-1) on the ATB turn | eb | `BTLCMD 0x38` (`DoEventCode.cs:1198`); often an expression into a working var | No | **done** (`[[scene.ai_function]]`/`[[scene.ai_insert]]` author an `Attack({…})`; `[[scene.ai_patch]]` retunes the index in place; `[[scene.ai_phase]]` overrides the attack-index var) |
| AI thresholds / branches | HP%/MP/status/phase conditions | eb | expr ops `B_CURHP=82 / B_MAXHP=83 / B_CURMP=110 / B_SYSVAR=122 / B_SYSLIST=121` → `btl_scrp.GetCharacterData` | No | **done** (`[[scene.ai_phase]]` generates the in-game-proven `cur<max/N` HP-threshold branch; `[[scene.ai_insert]]` authors arbitrary `JMP_IF {expr}` branches) |
| Counter / dying / phase / call-help | new AI branches by tag | eb | tags via `Request/RequestAction`: tag 1 main loop, **tag 6 counter, tag 7 ATB, tag 9 dying** | No | **done** (`[[scene.ai_function]]` adds/replaces a function by tag — counter/ATB/dying/main — the length-changing primitive, lint-gated) |
| Instant special | fire a raw17 seq without an ATB turn | eb | `AttackSpecial 0xE5` | No | **done (authorable)** (`cmdasm` emits `AttackSpecial(…)` from any `ai_function`/`ai_insert`; not separately in-game-proven) |
| Forced / scripted battle | start a specific scene on a trigger | eb | `Battle 0x2A` / `BattleEx 0x8C` | No | **absent** (AI-eb scope) — scripted/forced battles are a FIELD-eb concern (`[encounter]`, a proven field pillar), misfiled here |

### (c) Shared actions / abilities — `Data/Battle/Actions.csv` (player-side)

Header (`Actions.csv:5`):
`Comment;id;menuWindow;targets;defaultAlly;forDead;defaultOnDead;defaultCamera;animationId1;animationId2;scriptId;power;elements;rate;category;statusIndex;mp;type;commandTitle`.
**192 rows required POST-MERGE** (`FF9BattleDB.cs:63-65`) — the base supplies them; a delta overrides a subset.

| Lever | Controls | Channel | Location | DLL? | Kit |
|---|---|---|---|---|---|
| power / elements / rate / mp | damage / element / hit-or-status% / MP cost | CSV | cols 12/13/14/16 → `BTL_REF`/`AA_DATA` (`BattleActionEntry.cs:13-45`) | No | **done** (`[[battle_action]] power/element/rate/mp`, `actiondelta`) |
| **scriptId** | which battle-calc formula runs | CSV (re-point) **/ DLL (new)** | col 11 → `ScriptsLoader.GetBattleScript` (`ScriptsLoader.cs:215-223`) | re-point **No** / new formula **Yes** (`Memoria.Scripts.<Mod>.dll`) | **done (re-point)** (`[[battle_action]] script` resolves the formula catalog; a NEW formula still needs the `.dll`) |
| category / type | physical/magic/reflectable/contact/weapon-props/crit bits | CSV | cols 15/17 (`type 0x8/0x10/0x20` only when `CustomBattleFlagsMeaning=1`) | No | **done** (`[[battle_action]] category/type`) |
| statusIndex (AddStatusNo) | which `StatusSets.csv` row it inflicts/cures | CSV | col 16 → `StatusSetId` | No | **done** (`[[battle_action]] status_index`) |
| targets / menuWindow / camera / vfx | targeting + cursor display + VFX ids | CSV | cols 3-10 | No | **done** (`[[battle_action]] targets`(TargetType)/`menu_window`(TargetDisplay)/`default_ally`/`for_dead`/`default_on_dead`/`camera`/`vfx1`/`vfx2`) |

Elements bitmask (`EffectElement.cs:8-16`): Fire=1, Cold=2, Thunder=4, Earth=8, Aqua=16, Wind=32, Holy=64,
Darkness=128 — the **same 8-bit space** as the enemy Guard/Absorb/Half/Weak bytes.

### (d) Statuses — `Data/Battle/StatusData.csv` + `StatusSets.csv` + `MagicSwordSets.csv`

| Lever | Controls | Channel | Location | DLL? | Kit |
|---|---|---|---|---|---|
| OprCount (tick) / ContiCount (duration) | how punishing each ailment is (0/0 = permanent) | CSV | `StatusData.csv` → `btl_stat.cs` | No | **done** (`[[status]] tick/duration`, `actiondelta`) |
| ClearOnApply / ImmunityProvided | what a status clears / blocks | CSV | `BattleStatusDataEntry.cs:29-70` | No | **done** (`[[status]] clear_on_apply`/`immunity_provided`, BattleStatus lists) |
| StatusSets (bundles) | the named multi-status groups actions apply | CSV | `StatusSets.csv` (`#! UnshiftStatuses`); ids ≥39 | No | **absent** for authoring (read-only catalog only — no emitter) |
| MagicSwordSets | Steiner+Vivi combo unlocks | CSV | `MagicSwordSets.csv` | No | **absent** |

`StatusData` requires ids 0-32 post-merge (`FF9BattleDB.cs:88`).

### (e) Party / character / growth — `Data/Characters/*.csv`

| Lever | Controls | Channel | Location | DLL? | Kit |
|---|---|---|---|---|---|
| **BaseStats** (Dex/Str/Mag/Will/Gems) | the real per-char combat stats | CSV (partial, 0-11) | `BaseStats.csv` → `ff9level.cs` | No | **done** (`[[character]]`, `characterdelta`) |
| **Leveling** (Exp / BonusHP / BonusMP) | 99-step growth curve; `HP=BonusHP*Str/50`, `MP=BonusMP*Mag/100` | CSV (**whole-file**, 99 rows) | `Leveling.csv` → `ff9level.cs:53` (`GetCsvWithHighestPriority`) | No | **done** (`[[leveling]]`, whole-file 99-row re-emit) |
| CharacterParameters | row / category / menu-preset / equip-set | CSV (partial, 0-11) | `CharacterParameters.csv` → `ff9play.cs` | No | **absent** |
| Commands / CommandSets | battle-menu definitions + per-char layout | CSV (partial) | `CharacterCommands.cs` (0-44 / 0-19) | No | **absent** |
| Abilities/`<Name>.csv` | learn list + AP cost | CSV (**whole-file per preset**) | `ff9abil.cs:432` (`GetCsvWithHighestPriority`) | No | **absent** |
| AbilityGems | support-ability stone costs | CSV (partial, 0-63) | `AbilityGems.csv` → `ff9abil.cs:409` | No | **done** (`[[ability_gem]]`, `characterdelta`) |
| AbilityFeatures.txt | the SA/AA effect DSL (Auto-Haste, killers, MP+20%…) | text (`>SA/>AA/>CMD`, `+`=cumulate) | `ff9abil.cs:448-534` | No | **absent** |
| DefaultEquipment / InitialItems | starting gear + bag | CSV | `content/equipment.py` / `content/inventory.py` | No | **done** (items_equipment) |
| BattleParameters | **COSMETIC ONLY** — model + 34 anim ids + bones | CSV (partial, 0-18) | `btl_mot.cs` | No | absent (don't confuse w/ BaseStats) |

### (f) Encounter trigger / rate / formation

| Lever | Controls | Channel | Location | DLL? | Kit |
|---|---|---|---|---|---|
| Random-battle scene set | up to 4 candidate scene ids + a pattern | eb | `SetRandomBattles 0x3C` (`DoEventCode.cs:985-992`) | No | **done** (`content/encounter.py`) |
| Encounter pattern | which of 4 hardcoded prob rows (`pattern&3`) | eb | table at `EventEngine.Static.cs:120-126` (pattern *byte* is data) | No | **done** |
| Encounter frequency (encratio) | how often (0=off…255=max) | eb | `SetRandomBattleFrequency 0x57` → `_context.encratio` | No | **done** |
| "No-battle zone" | disable encounters | eb | `freq=0` | No | **partial** |
| Distance interval / grace / persistence | global pacing | ini | `Memoria.ini` `EncounterInterval`/`Initial`/`PersistentDangerValue` | No (ini) | **absent** |

### (g) Battle BG / camera / BGM — already shipped (the battle-backgrounds pillar)

FBX geometry + textures (true codec round-trip, `fbx.parse_fbx↔emit_fbx`), `BattleScene` mint (DP), opening
camera nudge/sweep (raw17, `camera_data`/`camera_codec` — the camera codec is now **real-donor round-trip
proven**: `test_battle_scene_codec.py::test_camera_codec_golden_roundtrip_real_donor` asserts
`serialize_block(parse_block(raw17)) == raw17[camOffset:]` + `splice_block(raw17, …) == raw17` on `EF_R007`),
BGM (`BattlePatch Music: <akao song id>`). The raw17 `btlseq` attack-choreography BODY is shipped **verbatim**
— the *kit* has no codec for it yet, but it is **data-authorable without a DLL**; the old "cannot author" was
wrong (see §2(h)).

### (h) Attack SEQUENCES — `btlseq.raw17` + `Data/SpecialEffects/<ef>/*.seq` (choreography + a thin gameplay edge)

> Engine-verified 2026-06-13 (a 10-agent workflow, all 3 load-bearing claims adversarially re-derived from
> source at high confidence). Sequences are **mostly cinematic but NOT pure fluff**; they are **no-DLL within
> the engine's fixed opcode vocabulary**; and they are **NOT a custom-model stepping-stone** (§8).

**Two channels, both no-DLL whole-file overrides:**
- **Binary `btlseq.raw17`** — the legacy interpreter is a hard-coded 34-entry delegate table `gSeqProg[]`
  (`btlseq.cs:1223-1259`); opcodes `> table.Length` coerce to `0=End` (`btlseq.cs:196`). Loaded mod-folder-first
  via `LoadBytes` (FolderHighToLow, `AssetManager.cs:634-666`) — drop a higher-priority `.raw17` and yours runs.
- **Text `.seq`** (`Data/SpecialEffects/<ef>/Sequence.seq` + `PlayerSequence.seq`) — parsed by
  `BattleActionThread`/`BattleActionCode` (compile-time command dict, `BattleActionCode.cs:46-89`; the parser
  **silently skips** any unknown command, `BattleActionThread.cs:156-157`), run by `UnifiedBattleSequencer`.
  Loaded mod-folder-first via `LoadString` (FolderHighToLow). A third lever: `BattleCommandInfo.SequenceFile` is
  a `[PatchableField]` → `BattlePatch.txt` can repoint a named/indexed action at a custom `.seq` by reflection.

**A new OPCODE / new command / changed semantics = DLL** (both vocabularies are compiled). Asset registration is
**not** needed — sequences only *reference* pre-existing anim/VFX/SFX ids.

**Two caveats:**
- **The text `.seq` path is gated by `Configuration.Battle.SFXRework`** (default ON; forced on at Battle Speed
  ≥3 — `BattleSection.cs:61`, `Access/Battle.cs:10`). With `SFXRework=0` the legacy binary runs and a
  `.seq`-authored attack **silently no-ops** (`btl_vfx.cs:110`, `UnifiedBattleSequencer.cs:27`). So `.seq` is
  **not** engine-independent the way the kit's shipped mods are — it depends on a user ini setting.
- **Enemy choreography has no text channel** — `EnemySequence` is transpiled from the binary raw17 at runtime,
  never re-read from a `.seq` (`UnifiedBattleSequencer.cs:111-113`). Authoring *enemy* attack sequences needs
  the binary raw17 codec the kit lacks (or a `SequenceFile` BattlePatch override, which re-imposes the gate).

**Gameplay levers a sequence DOES own** (it can't change the damage *math*, but it owns when/how-many/whether/
against-whom it runs):
- **Hit count = total damage (BOTH channels).** Each `Calc` (binary opcode `0x02`) / `EffectPoint Type=Effect`
  (text) is an independent committed calc pass — `effect_counter++` → `CalcMain` → `btl_para.SetDamage` does a
  real `CurrentHp -= damage` (`btlseq.cs:523-534`, `btl_para.cs:147-156`). Two `Calc`s on a surviving target =
  two HP subtractions. **This is the one gameplay lever that works in the binary raw17 the kit already forks.**
- **Effect gating** — omit `Calc` and *nothing* applies (a pure-visual attack; `scriptId 64` relies on this).
- **(text path only) target re-scope** — `EffectPoint`'s `Char` arg (AllEnemies / RandomTarget / named /
  NCalc `MatchingCondition`) redirects/expands the calc's targets (`UnifiedBattleSequencer.cs:971-987`). Legacy
  raw17 cannot — `SeqExecCalc` filters strictly by the pre-set `cmd.tar_id` (`btlseq.cs:530`).
- **(text path only) save-state side-channel** — `SetVariable` writes `cmd_status`/`btl_seq`/`gEventGlobal[Index]`
  (the save-backed story-flag heap) straight from the sequence (`BattleActionCode.cs:694-700`). The binary
  `gSeqProg` table has **no** such opcode.
- `effect_counter` is read back by enemy AI ("multi-hit pattern changes", `btl_scrp.cs:758-759`).

**Cannot change** (use raw16 / `AA_DATA` / `scriptId` / CSV / `.eb`): the damage formula or per-hit value,
power/element/accuracy/status-set (bound from `AA_DATA`/`scriptId` *before* the sequence — `btlseq.cs:105-106`),
stats/defences, AP/EXP/gil rewards, whether the attack costs an ATB turn / how AI selects it, and the
single-vs-multi *command* designation + reflect routing (`cmd.tar_id`).

**Kit status:** the OPENING-CAMERA half of raw17 is a true codec (now real-donor proven, above); the SEQUENCE
BODY is **sliced-verbatim, never parsed** → the kit cannot yet author choreography. The body's format does
**not** share the camera block's self-describing offset structure (flat single-byte opcodes, per-opcode variable
operand widths, separate `seqOffset`/`animList` tables, the `+4` body skew — `btlseq.cs:1165-1218`), so the
camera codec's offset machinery is **not** reusable; only the high-level "rebuild offsets on emit" pattern
transfers. On-ramp (mirrors the proven `.eb` read→patch→author path): read-only `battle-seq` disassembler
(transcribe `gSeqProg` + the `AdvanceSeqCode` width table) → same-length in-place patch (retime a `Wait`, swap
a camera/anim id) → lossless parse↔repack codec (gated on a real-donor golden) → net-new sequence (assembler +
a coordinated raw16 `AA_DATA` + `.eb` AI-by-`sub_no` + raw17 edit — the deferred "highest cost" tail, §8).

---

## 3. The mod-vs-DLL boundary (per-file)

The decisive split is the **merge mode** — it dictates delta vs whole-file.

**Partial-delta, per-id, low→high — `EnumerateCsvFromLowToHigh<T>` (`AssetManager.cs:849-854`).** Ship only
changed rows; later folders overwrite by id. Confirmed for Actions.csv (`result[id]=...` per-row; the 192-check
is on the *merged* dict).
- `Actions.csv`, `StatusData.csv`, `StatusSets.csv`, `MagicSwordSets.csv` · `BaseStats.csv`,
  `CharacterParameters.csv`, `Commands.csv`, `CommandSets.csv`, `AbilityGems.csv`, `BattleParameters.csv` ·
  `DefaultEquipment.csv`.

**Whole-file, highest-priority-wins — `GetCsvWithHighestPriority<T>` (`AssetManager.cs:856-862`).** Must be
complete.
- `Leveling.csv` (all 99 rows) · `Abilities/<Name>.csv` per preset · `InitialItems.csv` (the full bag).

**Custom accumulator** — `AbilityFeatures.txt` (low→high; a redefined id clears lower features unless `>SA 5+`
cumulates).

**Whole-file binary override (NOT merged) — `LoadBytes` returns the first hit FolderHighToLow
(`AssetManager.cs:634-666`).** `dbfile0000.raw16`, `btlseq.raw17`, `Battle/<id>.mes` — highest-priority mod
folder's copy wins entirely. (The `.eb` path is the exception: optional binary-diff `LoadBytesMerged` when
`Configuration.Mod.MergeScripts` is on.)

**Reflection patch (additive, no round-trip) — `BattlePatch.txt`** sets any `[PatchableField]` on
`SB2_HEAD/BTL_SCENE_INFO/SB2_PATTERN/SB2_MON_PARM/SB2_ELEMENT/AA_DATA/BTL_REF/BattleCommandInfo` by name/index,
in-memory after `ReadBattleScene` (`DataPatchers.cs:99-137,538-682`).

**Registration — `DictionaryPatch.txt`** (`BattleScene`/`BattleMapModel`).

**Needs DLL:** a new battle-calc formula / `scriptId` behavior → a separate **`Memoria.Scripts.<Mod>.dll`**
(`ScriptsLoader.cs:283-311`, NOT the engine DLL); a new `CharacterId`; the fixed accumulator / `d`-table /
escape-probability algorithms.

**Two caveats a delta emitter MUST encode:**
1. **CSV `#!` metadata is per-file** (`CsvReader.cs:21`). A delta that uses/omits an optional column must
   repeat the matching `#!` legend (`IncludeCastingTitleType`, `IncludeFullSet`, `IncludeVisuals`,
   `IncludeBoosted`, `UnshiftStatuses`, `IncludeId`) or its columns silently misparse — the most likely
   real-world failure.
2. **Coverage gates are on the MERGED dict** (192 actions / 33 statuses / 0-11 chars / 99 levels). A delta is
   fine *because the base supplies the rest in the lowest-priority `""` folder*; a standalone partial without
   the base throws.

---

## 4. Re-export fidelity (vs the project's "import → tweak → verify byte-accuracy" methodology)

The status is **asymmetric**:

| Asset | Byte-perfect round-trip today? | How | Methodology fit |
|---|---|---|---|
| **FBX battle-BG + PNG** | **YES, test-proven** | `fbx.parse_fbx ↔ emit_fbx` (`test_battle.py`) + in-game | **Fully satisfies** import→tweak→verify (the only lever that does) |
| **raw17 opening camera** | **YES, true codec — real-donor proven** | `camera_codec.parse_block ↔ serialize_block` (offset-table repack) | **Fully satisfies** import→tweak→verify: `splice_block(raw17, parse_block(raw17)[1]) == raw17` asserted on `EF_R007` (`test_battle_scene_codec.py`) |
| **battle `.eb`** | **YES, general codec** | `EbScript.from_bytes(x).to_bytes()==x` on real donors | Container round-trips; **full enemy-AI authoring ships** (`ai_function`/`ai_phase`/`ai_insert`/`ai_patch`, Phase 6c) beyond `rewrite_main_init` |
| **raw16 (`SB2_MON_PARM`)** | **YES, full codec — real-donor proven** | `scene_codec.parse_scene ↔ serialize_scene` (golden round-trip incl. the engine-ignored tail, `EF_R007`) | **Fully satisfies** import→tweak→verify; `scene_data` stays surgical for individual field edits |
| **raw17 btlseq (sequences)** | sliced-verbatim, **never parsed** | `camera_codec.py` splices `raw17[:camOffset]` | KIT has no codec yet → can't *author* choreography; but the ENGINE permits **data authoring with no DLL** (§2(h)) — hit-count/effect-gating already work in the verbatim raw17 |
| **`.mes`** | **copy only** | `shutil.copyfile` | Never parsed |
| **Actions/Status/Character CSVs** | **delta emitters ship** | `actiondelta`/`characterdelta` live-read the install base CSVs + emit partial deltas (Phase 3/5/5b) | Partial deltas non-destructive by design (lossless on untouched rows) |

**Honest framing:** the methodology's "parse a real X → re-emit → prove ==" is now codec-proven on real donors
for the **FBX**, the **raw17 opening camera**, the **raw16 scene** (incl. the engine-ignored tail), and the
**battle `.eb`** container. The remaining passthrough-copy assets are the **raw17 btlseq sequence body** (no codec
yet) and the **`.mes`**; the CSV levers ship as non-destructive partial deltas.

**What each new lever needs first** (most are now SHIPPED — the list is nearly drained):
- ~~raw16 affinity/status/defence/AP fields~~ — **SHIPPED** (`scene_data`/`battlepatch`; the whole per-enemy
  table is covered, §2(a), gated by the `EF_R007` raw16 golden round-trip).
- ~~Actions/Status/Character CSV deltas~~ — **SHIPPED** (`actiondelta`/`characterdelta`, Phase 3/5/5b; live-read
  the base CSVs, partial deltas, `#!` legends carried).
- ~~Enemy AI bodies~~ — **SHIPPED** (Phase 6c: `exprasm`/`cmdasm`/`aiauthor`/`ailint` + the declarative
  `[[scene.ai_*]]` surfaces).
- **raw17 btlseq + a new attack SEQUENCE** → the ONE remaining gap: needs a btlseq codec (camera-codec's
  offset-table repack proves it's feasible) + a coordinated raw16(`AA_DATA`)+eb+raw17 edit. Highest cost, lowest
  priority. → §2(h).

---

## 5. What designers need for BALANCED encounters

### The FF9 combat math that makes some levers high-leverage

- **Damage = Base × Bonus × Modifier**, `Base = Power − Defence`, **floored at 1** (`CalcContext.cs:37`).
  Defence is **subtractive** → a *hard wall* when `Power ≤ Def`, *nearly irrelevant* when `Power ≫ Def`. Model
  the non-linearity; don't treat Def as % mitigation.
- **Bonus** = `stat + rand%(1 + ((Level+stat)>>2 or >>3))` (`BattleCaster.cs:17-30`) → **enemy Level widens the
  random damage band** (higher average *and* variance).
- **Modifier stacks multiplicatively**: each weakness ×1.5 (`Attack*3>>1`), each half ×0.5, absorb → heal *and*
  zeroes defence. **Element affinity is the single biggest one-edit damage swing** + the primary counter-play
  telegraph.
- **Enemy Level is uniquely multi-purpose**: scales attack variance, **resists incoming magic**
  (`hitRate += casterLvl − targetLvl`, `BattleCalculator.cs:239`), sets **steal difficulty** (random Defence
  in `0..Level-1`), and **gates the Level-N spell family** (`Target.Level % Command.HitRate == 0` IS LV5 Death
  / LV3 Def-less / LV4 Holy, `BattleCalculator.cs:480-487`). A zone of all-multiple-of-5 levels is **free LV5
  Death bait.**
- **Economy is no-grind by construction**: `EXP = Σ(killed WinExp) / surviving players`
  (`BattleResultUI.cs:516`); `gil = Σ WinGil` (whole); **AP is per-FORMATION (`SB2_PATTERN.AP`),
  level-independent, awarded WHOLE/undivided** (`btlseq.cs:475`). Treat EXP/gil as level-pacing knobs and **AP
  as a flat ability-unlock budget** — the kit edits the pattern struct but **never exposes AP**, the
  highest-value missing economy lever.

### Designer-facing knobs (priority order)
1. Enemy HP + the 4 stats + Level (pacing + the derived effects above).
2. **Element weak/half/absorb** — give every enemy ≥1 exploitable weakness (else a stat-check wall).
3. **Status resist/auto/initial** — partial vulnerability > total immunity (a boss immune to all statuses makes
   those abilities dead choices).
4. Defences/evade/hit-rate (parry/dodge/accuracy profile).
5. EXP/gil/**AP** on a zone curve; drop/steal **rates** + "best item in the rarest slot."
6. Formation shape (count ≤4, placement, per-pattern Rate) + scene flags (back-attack ambush, no-escape boss).
7. Enemy AI (the real fight redesign — phases, HP-threshold triggers, counters).

### Automated LINT/VALIDATION the kit should add (the "I can't see the game" superpower)
All derivable **offline** from the fields above + the known formulas:
- **Turns-to-kill estimator** — total enemy HP vs party DPS at level L via the real `Base×Bonus×Modifier`;
  flag HP-sponges / one-shots. Plus the symmetric **enemy time-to-kill-a-PC** ("is this fair?").
- **Level-N exploit lint** — warn when a zone's levels are all `%5`/`%4`/`%3` (free LV5 Death / LV4 Holy / LV3
  Def-less).
- **Counter-play lint** — "every enemy has ≥1 weak element"; "boss immune to all 32 statuses → dead choices."
- **Economy/curve lint** — EXP/gil/AP off the zone curve; rare drop on a trivial enemy; no reward on a hard one.
- **Drop/steal sanity** — steal slots ordered rare→common; referenced item ids exist (reuse `items.resolve`).
- **Subtractive-defence wall** — flag `Def ≥ likely incoming Power`.
- **AA_DATA byte-width guard** — a player ability's Int32 power/rate **cannot exceed 255** in an enemy raw16
  slot (`BTL_SCENE.cs:144-146`).
- **Type-shared-stats warning** — two formation slots sharing a `TypeNo` share ALL stats (the kit already
  warns for the 9 fields; extend to all new ones).

---

## 6. Current kit capability vs the gap

**The kit today** spans the no-DLL channels. **raw16 `[scene]`** (`scene_data.py`, Phase 1) byte-patches a
*forked* scene's enemy combat identity — HP/MP/gil/exp, the 4 stats, level, category, hit-rate, the 4 def/evade,
blue-magic, win-card, the 4 element-affinity bytes + 3 status masks (by name), drop/steal ids, `SB2_PUT`
placement, MonsterCount, Camera, pattern AP + the opening camera (raw17); `monster_count` re-composes every
pattern and re-authors the eb `Main_Init` bindings (≤4 existing types). **CSV deltas** (`actiondelta.py`, Phase
3) rebalance the 192 shared player abilities + the 33 statuses. **`BattlePatch.txt`** (`battlepatch.py`, Phase 4)
reaches ANY scene by name **without forking** — the BP-only rate arrays / `BonusElement` / `MaxDamageLimit` /
`WinCardRate`, the enemy ATTACK table, scene flags, pattern Rate/AP — plus the cross-scene
`AnyEnemyByName:`/`AnyAttackByName:` channel. Offline **lint** (`scenelint.py`, Phase 2) sits over all of it.

**Still missing:** **character/growth CSVs** (`BaseStats`/`Leveling`/abilities — Phase 5); **enemy AI bodies**
(the battle `.eb` opcode/expression authoring layer — Phase 6); **model re-skin** (`Geo/Mot`, raw16-only); a
net-new raw17 attack SEQUENCE (needs a btlseq codec); and a brand-new battle-calc **formula** (a separate
`Memoria.Scripts.<Mod>.dll`, not the engine DLL).

---

## 7. Community baseline & where ff9mapkit wins

**Hades Workshop** is the canonical FF9 editor — full enemy struct, the 192-action table, statuses, formations,
**and a real enemy-AI script editor** (Main/Init/ATB/Loop/Counter/Death), and it can **export Memoria
mod-folder CSVs** (so HW and the CSV path are complementary). But HW is a retired Windows GUI, **corrupts
entry-adds**, and has no campaign-wide / validation / declarative workflow. Difficulty mods reveal the
high-leverage levers: *Alternate Fantasy* (up-statted enemies + harder AI + status-on-elemental-hit);
*Trance Seek* ships a **forked engine** — confirming the ceiling (stat/AI/ability tuning is data; novel formulas
ship custom C#).

**Where the kit WINS** (don't out-GUI HW on single-enemy editing): CSV-delta ability/status balance (the
`itemstats.py` pattern); **campaign-wide tuning** ("buff every Goblin across the chain"); **offline
lint/validation**; declarative `battle.toml`/`field.toml` authoring; provenance-clean byte-verified
import→tweak→verify; clean `BattlePatch.txt` emission. **Where NOT to bother:** a single-enemy GUI; novel
`scriptId` formulas; cross-scene net-new formations needing a new type's raw17 seqs + GEO.

---

## 8. Prioritized roadmap (each engine-independent unless flagged)

### ⭐ Phase 0 — FIRST MOVE: read-only catalogs + a raw16 golden round-trip test
- A **read-live `battlecsv.py`** (mirror `itemstats.py`): parse `Actions.csv` (192), `StatusData.csv` (33),
  `StatusSets.csv` by their `#`-legend; resolve names/ids/elements/scriptIds; **commit name/id tables only,
  never stats**. A designer-facing **scriptId catalog** flagging "re-point = no DLL / new formula = DLL."
- A **full `SB2_MON_PARM` read-only scanner** presenting all ~40 fields as one record.
- **The gate the methodology demands:** a **real-donor golden round-trip test** (`EF_R007` raw16 →
  parse → re-serialize → `== original`), capturing the engine-ignored tail verbatim. Converts "copy-identity"
  into "codec-identity" and unblocks every raw16 extension safely.

### Phase 1 — raw16 enemy combat-identity extension (biggest no-DLL gap, highest leverage:weight)
Add to `scene_data._MON_FIELDS` the verified scalar offsets: element affinities `@60-63`, status masks
`@0/4/8` (u32 + a name→bit helper), defences `@67-70`, HitRate `@66`, Category `@65`, BlueMagic `@71`, pattern
AP `@4` + type AP `@50`, WinCard `@105` (drop/steal rates + MaxDamageLimit via BattlePatch arrays). Each = the
identical `struct.pack_into` surgical pattern. Add element/status/category **name↔bit tables** (committable).

### Phase 2 — the validation/lint suite (the superpower) ✅ DONE (kit 0.9.46)
`battle/scenelint.py` — `lint_scene(scene) -> [Finding]` over the Phase-0 parsed scene, surfaced in
`battle-scene` (inspector footer) and `battle-build` (lints the **tuned** raw16 → `BattleResult.lint`). The bar
is TRUST (quiet on vanilla, loud only on real problems), so every check was **validated against a 562-scene
sweep** (a 3-lens adversarial review). Checks shipped: **no_reward** / **bad_item** (`warn`: a fight that rewards
nothing; a drop/steal id that isn't a real item — both 0 false-positives across all 562 scenes), **status_immune**
(immune to every common offensive status → status abilities dead), **element_wall** (resists/absorbs/halves ≥7/8
elements), **phys/mag_wall** (defence in the weapon-power band ≥50 — real enemies cap ~24, FF9 weapon power ~108 —
→ attacks floored, subtractive defence), **level5** (level %5 AND not Death-immune → LV5 Death one-shots).
Severity: `warn` = likely real problem, `info` = design awareness. ★ The review CAUGHT + we removed three
over-firing heuristics the single smoke missed: an `hp_sponge`/turns-to-kill estimate (fired on ~49% of real
scenes — FF9 damage is multiplicative `Strength×(weaponPower−def)` ×party, off by 10-40× without a live party
model), the raw `level3/4/5` divisibility notes (~74%, plus a backwards "LV4 Holy" on Holy-absorbers), and a
standalone `no_weakness` note (~29%, a normal design choice). DEFERRED (needs a live party model): a precise
turns-to-kill / time-to-kill-a-PC estimator + the economy-curve-vs-zone check. 9 lint tests (incl. a
normal-late-game-enemy-is-clean regression) + the real-donor sweep.

### Phase 3 — CSV-delta ability + status authoring (the natural WIN vs HW) ✅ DONE (kit 0.9.47)
`battle/actiondelta.py` — `[[battle_action]]` (rebalance a shared ability: `power`/`element(s)`/`rate`/`mp`/
`script`/`category`/`type`) and `[[status]]` (`tick`/`duration`) on a `field.toml`, emitted at the mod-write
stage (`build._emit_battle_data` → `ModLayout.actions_csv`/`status_data_csv`). The engine merges these by
**whole-ROW replacement** keyed on id, so to change one field we read the base row LIVE from the install,
modify the named columns, and emit the complete row — preserving the base file's **`#!` option lines**
(load-bearing: the engine parses by column POSITION and `#!` toggles optional columns). Mod-global (always-on,
not new-game-scoped), aggregated across all fields, dup-id warned; `script` resolves a formula name (warns if
it's not a stock scriptId — a new formula needs a `Memoria.Scripts.<Mod>.dll`). Provenance: the authored
`field.toml` holds only the overrides; the emitted CSV is mod build-output (never committed). `deploy_field`
ships the two CSVs reversibly. Offline `lint` does structural checks; name→id + value resolution happens at
build (which has the install). (Enemy attacks live in raw16, not Actions.csv → the enemy-attack analog is the
Phase-4 BattlePatch emitter.) ★ A 3-lens adversarial review (engine source + real CSVs) verified the merge +
byte-preservation sound and caught three real bugs (fixed): the install CSVs are **cp1252** not UTF-8 (4 ability
names carry a 0x92 apostrophe — `errors="replace"` corrupted them + blocked name lookup → read/write cp1252 +
straighten curly apostrophes); narrow engine columns (elements/category/type = Byte, tick = Byte, duration =
UInt16) were unguarded so an out-of-range value would **crash the game at boot** (`Byte.Parse` overflow →
`ConfirmQuit`) → range-checked OFFLINE; a name that maps to several ids now raises "ambiguous — use the id". 14
tests + real-install smoke; *in-game proof (the rebalanced ability behaves) is the human step.*

### Phase 4 — `BattlePatch.txt` emitter for enemy/attack/scene tuning ✅ DONE (kit 0.9.51)
`battle/battlepatch.py` — three `field.toml` blocks map 1:1 to the engine's selector model
(`DataPatchers.PatchBattles`/`TryParseBattleSelector`, `DataPatchers.cs:538-682`):
- **`[[battle_patch]]`** — scene-scoped (`scene = <id|BSC_ name>` → `Battle:`): scene flags (→ `BTL_SCENE_INFO`
  Booleans) + nested **`[[battle_patch.enemy]]`** (`index =`/`name =` → `Enemy:`/`EnemyByName:`),
  **`.attack`** (→ `Attack:`/`AttackByName:`), **`.pattern`** (→ `Pattern:`). Patches ANY scene **in place**
  (no fork, no raw16 repack) — the lever raw16 `[scene]` structurally can't offer.
- **`[[battle_enemy]]`/`[[battle_attack]]`** — global by-name (`AnyEnemyByName:`/`AnyAttackByName:`): retune
  EVERY enemy/attack of that name across ALL scenes (the campaign-wide WIN).
- Reaches the **BP-only** levers with no raw16 slot — drop/steal **rate** arrays, `BonusElement`,
  `MaxDamageLimit`/`MaxMpDamageLimit`, `WinCardRate` — and the **enemy ATTACK table** (`AA_DATA`/`BTL_REF`
  power/element/rate/`status_set`/mp/script), which the kit could not touch before. Plus the full enemy combat
  identity (stats/affinities/status masks/defences/level/category/drop+steal ids).
- **Uniform integer emission**: `.NET Enum.Parse` accepts an integer string for every enum/flags field, so all
  element/status/item values resolve through the committed `battlecsv`/`itemstats` name↔bit tables +
  `items.resolve` — **no new SE-derived table is committed**. Narrow engine column types (Byte/UInt16/UInt32 +
  the `StatusSetId` 0-38 enum) are RANGE-CHECKED offline (a value the engine would mis-store / `KeyNotFound`-crash
  fails the lint/build instead).
- **Non-clobbering deploy** (`merge_battle_patch`): the built block is spliced into the live `BattlePatch.txt`
  under per-field `//` sentinel markers (the engine skips `//` lines, `DataPatchers.cs:551`), so a co-deployed
  battle's repoint/`Music:` lines + a stacked worktree's lines survive — idempotent + reversible
  (`deploy_field.py`). `build_mod` merges the Phase-4 lines with the per-encounter BGM `Battle:`/`Music:` block.
- CLI `battle-patch <field.toml>` (offline preview) + `--fields` (the tunable-field catalog); offline lint in
  `validate_field`. ★ A 4-lens adversarial review (engine source + the structs) verified the grammar/ordering,
  every field name↔[PatchableField]↔token↔range, and the value-encoding sound, and CAUGHT three real bugs
  (fixed): the `status_set`/`AddStatusNo` cap was `_U16` but `StatusSetId` only defines 0-38 → an undefined id
  is a `KeyNotFoundException` crash at command-build (capped at 38); a malformed (non-table / non-list) toml
  block tracebacked instead of raising `BattlePatchError` (the linter-never-traceback invariant); and the
  `scene` selector was unvalidated → a float/list/over-Int32 value silently emitted a DEAD `Battle:` line that
  the engine never matches (the whole block no-oping — the exact silent-drop class the module exists to
  prevent). 23 tests. ★ **IN-GAME PROVEN (2026-06-12):** a `[[battle_patch.attack]]` on the forked EF_R007
  Goblin patched the enemy's normal attack by index (`power`+`status_set`) and both landed — the attack inflicted
  the authored `StatusSets.csv` bundle (the `AA_DATA` enemy-attack lever, untouchable before, works by name).
  (Author note: `status_set` is a `StatusSetId` row — 16 = the Dispel bundle, Poison = 20.) Surfaced + fixed a
  `deploy_field` wholesale-snapshot DictionaryPatch revert that clobbered a co-deployed `BattleScene`
  registration (→ black screen); the revert is now surgical (drops only the field's own line).
  ★ **FULLY PROVEN (2026-06-12):** a follow-up confirmed EVERY Phase-4 channel in one fight — `AnyEnemyByName:
  Goblin` (the Goblin started **Poisoned** via `initial_status`; "Goblin" is a real FF9 enemy → the same block
  buffs real Goblin battles, the campaign-wide win), `AnyAttackByName: Goblin Punch` (neutered to **power 1**),
  the `back_attack` **scene flag** (party started reversed), and a guaranteed `drop_rates` **Elixir**. So all
  selectors + the BP-only rate arrays + scene flags are in-game proven.

### Phase 5 — character/growth CSV deltas ✅ DONE (kit 0.9.58)
`battle/characterdelta.py` — the PLAYER side of balance (the `actiondelta` twin), read-live `Data/Characters`
deltas: **`[[character]]` → BaseStats.csv** (`dexterity`/`strength`/`magic`/`will`/`gems` by name/0-11 id; per-id
PARTIAL delta, `EnumerateCsvFromLowToHigh`) + **`[[leveling]]` → Leveling.csv** (`exp`/`bonus_hp`/`bonus_mp` by
`level=1..99`; **WHOLE-FILE** — `GetCsvWithHighestPriority` + a ≥99-row gate, so we read the base 99 live, patch,
and re-emit ALL 99; HP=`BonusHP·Str/50`, MP=`BonusMP·Mag/100`). Range-checked offline vs the real column types
(Byte/UInt16/UInt32); `CharacterId` name table committed (the enum), stat values read live. Wired mod-global into
`build`/`validate_field`/`deploy_field` + the deploy-time shadow guard (Leveling is whole-file like InitialItems);
CLI `characters`. ★ A 4-lens adversarial review caught a provenance leak (a fixture row matched the install —
de-leaked), the missing Leveling shadow guard (added), and a `[character]` vs `[[character]]` build/lint
disagreement (normalized). 15 tests + real-install smoke. ★ **IN-GAME PROVEN (2026-06-12):** a `[[character]]`
boost of Vivi (40/80/90/45) + `[party] add=["vivi"]` on a New-Game field → at a fresh New Game her status menu
read Speed 40 / Str 80 / Mag 90 / Spr 45 (vanilla 16/12/24/19) — `[[character]]`→BaseStats.csv lands at the
New-Game party build (Leveling shares the machinery; its in-game proof is a follow-up).
**Phase 5b ✅ DONE (kit 0.9.61):** `[[ability_gem]]` → `AbilityGems.csv` (re-cost a support ability's gem
requirement; per-SupportAbility partial delta, the build-economy lever). `ability` by enum/display name or 0-63
id (committed SupportAbility name table); `#! IncludeBoosted` + the Boosted column preserved; CLI `ability-gems`.
A 3-lens review verified the 64-name table + the Boosted handling + provenance, and aliased the one display name
("Odin's Sword") whose possessive broke resolution. 6 tests. **Still deferred:** `CharacterParameters.csv`
(mostly menu/row), `Commands`/`CommandSets`. **Explicitly NOT `BattleParameters.csv`** (cosmetic only — model/anims).

### Phase 6 — enemy-AI authoring (highest ceiling, hardest). Staged: disassembler → same-length patch → new branch.
**Phase 6a ✅ DONE (kit 0.9.62)** — the **disassembler VIEW** (read-only `battle-ai <scene>`, the import→SEE
step). The battle `.eb` IS the field `.eb` container/interpreter, so the kit already round-trips + decodes it; 6a
added the missing VOCABULARY: `eb/_exprtable.py` (the `op_binary` operator table, all 128, from `EBin.cs`) + the
`0xC0+` variable-token decode (`Global.Bit[8512]` story-flags, `B_CURHP` enemy-HP); `eb/disasm.pretty_expr`
(names an expression stream, mirroring `read_expr`'s byte-walk); `battle/battleai.py` (walks entry 0 = Main_Init
spawn-binding, entries `1..TypCount` = per-type AI, functions by TAG [Main/Counter/ATB/Dying], with named commands
incl. a control-opcode overlay + annotated expressions). ★ The load-bearing property = **byte-walk PARITY**: a
test asserts `_decode_func_pretty`'s instruction offsets == the proven `read_code`'s across every AI function of a
real donor, so the view can never desync. Reads the real EF_R007 Goblin AI cleanly. 10 tests; a 3-lens review
(table vs `EBin.cs` / byte-walk / presenter+provenance) found only a low truncated-eb `IndexError` (guarded).
**Phase 6b ✅ DONE (kit 0.9.64)** — **same-length AI constant patches** (`battle/aipatch.py`, the first authoring
step). `constant_sites` locates every patchable numeric constant (command immediates + `B_CONST`/`B_CONST4` expr
literals) with offset+width — a walk that mirrors `read_code`/`pretty_expr` byte-for-byte; `battle-ai --sites`
prints them (224 on EF_R007). `[[scene.ai_patch]]` (in `battle.toml`) cites `at`/`old`/`new`: a same-length,
old-value-GUARDED in-place edit (no `fpos`/entry-table fixup), applied per-language to the forked eb at build
(bytecode is language-identical). ★ A 3-lens review found + fixed: a 3-byte (Int24) immediate `KeyError`
(→ generic width-N pack), a truncated-eb `IndexError` (→ clean `AiPatchError`), and the `B_CONST4` 26-bit engine
mask (→ per-site cap); the `B_CONST` signedness path is benign (byte-faithful). 9 tests. *In-game proof = human.*
**Phase 6c-i ✅ DONE (kit 0.9.67)** — the enemy-AI **expression ASSEMBLER** (`eb/exprasm.py`), the keystone of
new-branch authoring: the exact inverse of the 6a disassembler. `assemble("{ B_CURHP const(50) B_LT B_EXPR_END }")`
→ the RPN expression bytes the engine evaluates, round-trip-exact with `pretty_expr` (`assemble(pretty_expr(b))==b`
byte-for-byte, proven against the real EF_R007 AI). Each token inverts a `pretty_expr` branch (op mnemonic / `const`
+ `const4` / the `0xC0` minimal var encoding / sysvar / obj / member-ptr). CLI `battle-ai --asm`. ★ A 3-lens review
confirmed the byte-layout matches `EBin.cs` and fixed: an `opXX` back-door that assembled a bare operand-byte
(→ desync; now `opXX` accepts only unnamed pure operators `<0xC0`), an unguarded re-disasm crash (→ `assemble()`
**self-verifies** its own round trip as a library invariant), and silent const masking (→ range-checked). 35 tests.
**Phase 6c-ii ✅ DONE (kit 0.9.70)** — the enemy-AI **COMMAND assembler** (`eb/cmdasm.py`) + **branch insertion**
(`battle/aiauthor.py`), the first LENGTH-CHANGING AI edit. `assemble_instruction`/`assemble_block` mirror
`read_code`'s byte-walk (argFlag, forced-`SET`, the variable-count ops, the `0xFF` page), so they reproduce its
exact bytes; `assemble_block` resolves `label:`/symbolic jumps in two passes. `add_ai_function`/`replace_ai_function`
splice the assembled branch into a forked eb via the existing byte-safe `eb.edit` primitives (entry-table + `fpos`
fixup). CLI `battle-ai --asm-block`. Round-trip proven on the real EF_R007 AI (every instruction + every function
byte-for-byte; `add_ai_function` re-parses with everything else byte-intact). ★ A 3-lens review fixed: a missing
flow-TERMINATOR check (no per-function length bound in-engine → a RET-less branch runs off the function; now
`aiauthor` requires `RET`/`TerminateEntry`) and a backward `JMP_IFNOT` (the engine reads its offset UNSIGNED, unlike
`JMP`/`JMP_IF` → now rejected). 35 tests.
**Phase 6c-iii ✅ DONE (kit 0.9.72)** — the enemy-AI **LINTER** (`battle/ailint.py`) + the declarative
`[[scene.ai_function]]` build surface — the CAPSTONE. `lint_ai(eb, atk_count=)` runs SOUND offline checks (decode /
jump bounds / **reachable RET** via a forward reachability walk / Attack-index `< atk_count`); ★ **a 562-scene sweep
lints ALL shipping scenes CLEAN (0 false positives)**. CLI `battle-ai --lint`. `[[scene.ai_function]]`
(`aiauthor.apply_ai_functions`) adds/replaces an AI function in `battle.toml`, spliced per-language at build AFTER
`ai_patch`; the validate hook lints the COMPOSED (shipped) eb. ★ A 3-lens review (it re-ran the 562-sweep itself)
fixed 4: a `JMP_IFNOT` decoded signed but read UNSIGNED in-engine (missed the backward-jump fault → now unsigned);
the validate hook lit the un-patched donor not the composed eb (→ composes + lints the shipped bytes); an incomplete
terminator set (`GameOver`/`STOP`/… also end dispatch → false-flagged, now widened + shared with `aiauthor`); and an
out-of-range tag raising a raw `struct.error` (→ clean error). **Phase 6c COMPLETE** (read → tune → author →
validate the whole enemy-AI stack, no DLL). ★ **IN-GAME PROVEN (2026-06-13):** a `[[scene.ai_function]]` RET-ing the
forked Goblin's **tag-5 attack routine** (`battle_tests/bt_goblin`, scene 30055) made it stand idle in real battle
(Phase-4 Poison then finished it). Dispatch model learned: an enemy turn dispatches to **tag 7 (ATB)**; the spawned
enemy's AI ENTRY is bound by Main_Init's `InitObject(<entry>,…)` (the Goblin binds to **entry 2**, decoupled from the
raw16 "type"); the `Attack` (0x38) command lives in **tag 5**. **Defer raw17 btlseq sequence authoring** (new codec
+ a coordinated raw16+eb+raw17 edit).

---

## 9. Open questions & risks

- ~~**`Configuration.Mod.MergeScripts` default**~~ — **RESOLVED**: default **false** (`ModSection.cs:20`; live
  `Memoria.ini [Mod]` = 0), so a battle `.eb` whole-file-clobbers (highest folder wins) — mod-folder priority is
  the operative rule; no per-`.eb` binary merge to reason about.
- **In-game smoke test a sparse partial `Actions.csv`/`StatusData.csv`** — the merge accepts it in theory (base
  supplies the rest), but the coverage gates + per-file `#!` reset make an in-game check mandatory before
  shipping a delta emitter.
- ~~**raw16 tail provenance**~~ — **RESOLVED**: `scene_codec` captures + re-appends the post-`AtkCount` tail
  verbatim (`scene_codec.py:289/306`); the golden round-trip `serialize_scene(parse_scene(EF_R007)) == raw16`
  asserts byte-identity INCLUDING the tail (`test_battle_scene_codec.py`).
- ~~**Camera codec on a real donor raw17**~~ — **RESOLVED 2026-06-13**: `splice_block(raw17, parse_block(raw17)[1])
  == raw17` is asserted on `EF_R007` (`test_battle_scene_codec.py::test_camera_codec_golden_roundtrip_real_donor`,
  install-gated). The opening-camera codec is lossless on real bytes; the SEQUENCE BODY remains un-parsed (§2(h)).
- **Enemies do NOT pull from `Actions.csv`** — a tool editing `Actions.csv` to retune enemy moves mis-targets
  every enemy edit (enemy attacks = raw16 AA_DATA / BattlePatch only). (`btl_util.cs:353-354`)
- **Category default bits / the vanilla `type` byte** — only the `CustomBattleFlagsMeaning=1` meanings are
  documented; trace `CalcResult` before a designer-facing picker labels them.
- **Provenance discipline** — all raw16 stat bytes + all CSV stat values are SE game DATA: read live, never
  commit. Only name↔id/element/status/category tables (from open-source Memoria enums) are committable.

**Key refs:** `BTL_SCENE.cs:50-153`, `SB2_MON_PARM.cs:20-179`, `FF9BattleDB.cs:35-117`,
`AssetManager.cs:849-862`, `DataPatchers.cs:60-137,413-682`, `EventEngine.DoEventCode.cs:956-1234,2938`,
`BattleCalculator.cs:210-741`, `ScriptsLoader.cs:215-311`, `scene_data.py:32-36`.
