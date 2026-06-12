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
| **WinItemRates[4] / StealItemRates[4]** | drop/steal **odds** | **BP only** | not in raw16; `[PatchableField]` arrays, defaults `{256,96,32,1}` / `{256,64,16,1}` (`SB2_MON_PARM.cs:53-60`) | No | **absent** |
| Radius / Geo / Mot[6] / Mesh[2] | collision + **model + 6 anim ids** (re-skin to a stock monster) | **raw16 only** | `@28 u16`, `@30 i16`, `@32` 6×u16, `@44` 2×u16 | No | **absent** |
| Flags | per-enemy MON flags | **raw16 only** | `@48 u16` | No | **absent** |
| AP (per-type) | type AP (note: the gameplay AP is the *pattern* AP) | **raw16 only** | `@50 u16` (not `[PatchableField]`) | No | **absent** |
| Speed / Strength / Magic / Spirit | the 4 core battle stats | raw16 / BP | `@52/@53/@54/@55` u8 | No | **done** |
| (pad/trans/cur_capa/max_capa) | trance/capacity — inert for enemies | — | `@56-59` | — | pass-through |
| **GuardElement / AbsorbElement / HalfElement / WeakElement** | per-element immune / absorb / halve / weak | raw16 / BP | `@60/@61/@62/@63` u8 bitmask | No | **absent** |
| **BonusElement** | element the enemy's OWN attacks are imbued with | **BP only** | not in raw16; `[PatchableField]` (`SB2_MON_PARM.cs:85`) | No | **absent** |
| Level | level (variance, magic resist, steal, Level-N spells) | raw16 / BP | `@64 u8` | No | **done** |
| Category | race / killer / flight / undead / death-react | raw16 / BP | `@65 u8` | No | **absent** |
| HitRate | enemy physical accuracy | raw16 / BP | `@66 u8` | No | **absent** |
| **PhysicalDefence / PhysicalEvade / MagicalDefence / MagicalEvade** | the 4 defences | raw16 / BP | `@67/@68/@69/@70` u8 | No | **absent** |
| BlueMagic | Quina Eat / learn id | raw16 / BP | `@71 u8` | No | **absent** |
| **ResistStatus / AutoStatus / InitialStatus** | immune / permanent / starting statuses (32-bit `BattleStatus` masks) | raw16 / BP | `@0/@4/@8` u32 LE | No | **absent** |
| WinCard | Tetra Master card drop | raw16 / BP | `@105 u8`; rate = `DefaultWinCardRate=32` constant | No | **absent** |
| **MaxDamageLimit / MaxMpDamageLimit** | per-enemy >9999 break-damage-limit | **BP only** | not in raw16; `[PatchableField]`, default `FF9PLAY_DAMAGE_MAX` (`SB2_MON_PARM.cs:20-21`) | No | **absent** |
| Bone/SFX/Shadow/Icon/Konran/MesCnt | cosmetics / SFX / message count | raw16 only | `@72-114` | No | **absent** |

> **`[PatchableField]` = "by-name without re-packing":** the status masks, all 5 element bytes, Level,
> Category, HitRate, all 4 def/evade, BlueMagic, gil/EXP/drop/steal + the rate arrays + MaxDamageLimit all
> carry `[Memoria.PatchableFieldAttribute]` (`SB2_MON_PARM.cs:33-109`), so `BattlePatch.txt` sets them by
> FieldInfo name (`DataPatchers.cs:99-113`). A few `[PatchableField]`s (WinItemRates/StealItemRates,
> BonusElement, MaxDamageLimit) are **not in the raw16 disk layout at all** → reachable ONLY via BattlePatch.
> **NOT patchable** (raw16-byte-only): `AP@50`, `Flags@48`, the model wiring (`Radius/Geo/Mot/Mesh`), all
> cosmetics, and `MonsterCount` (commented out, `SB2_PATTERN.cs:16`).

### (a′) Per-enemy ATTACK table — `AA_DATA[]` at the raw16 TAIL

Enemy attacks are **not** in `Actions.csv` — they live inline in the raw16 at `8 + 56*PatCount + 116*TypCount`,
one 16-byte `AA_DATA` per attack (`BTL_SCENE.cs:127-153`): a 4-byte bit-packed `BattleCommandInfo`
(Target/DefaultAlly/DisplayStats/VfxIndex/sfx/ForDead/Camera/OnDead) + `ScriptId, Power, Elements, Rate,
Category, AddStatusNo, MP, Type` (8×u8) + `Vfx2` u16 + `Name` u16. **Power/Elements/Rate are single BYTES here
(0-255).** The raw17 `btlseq` binds which attack indices belong to which monster (`EnemyGetAttackList` →
`GetEnemyIndexOfSequence`); the AI `.eb` selects among them. Tunable via raw16 byte-patch OR
`BattlePatch.txt`'s `Attack`/`AnyAttackByName` token (reflection on `AA_DATA`/`BTL_REF` `[PatchableField]`s,
`DataPatchers.cs:114-130`). **Kit: absent** (`scene_data.py` computes the monster base but never reaches the
attack block).

### (a″) Formation / pattern — `SB2_PATTERN` + `SB2_PUT` (raw16)

| Lever | Controls | Channel | Location | DLL? | Kit |
|---|---|---|---|---|---|
| MonsterCount | # active enemies (engine cap 4) | raw16 only | `pattern+1 u8` | No | **done** |
| Camera | which camera index | raw16 / BP | `pattern+2 u8` | No | **done** |
| pattern Rate | spawn-rate weight of this formation | raw16 / BP | `pattern+0 u8` | No | **absent** |
| **pattern AP** | the **gameplay-effective** AP reward (whole, undivided) | raw16 / BP | `pattern+4 u32`; consumed `btlseq.cs:475` | No | **absent** |
| SB2_PUT type/x/y/z/rot | per-slot enemy type + placement | raw16 | `pattern+8 + 12*j`: `TypeNo@0 Flags@1 X@4 Y@6 Z@8 Rot@10` | No | **done** |

### (a‴) Scene-wide rules — `SB2_HEAD.Flags` / `BTL_SCENE_INFO`

`SpecialStart`(preemptive) / `BackAttack` / `Runaway`(can-escape) / `NoGameOver` / `NoExp` / `WinPose` /
`NoMagical` / `ReverseAttack` / `FixedCamera1/2` / `AfterEvent` — decoded from `header.Flags @4 u16`
(`BTL_SCENE.cs:214-230`), all `[PatchableField]` on `BTL_SCENE_INFO` → BP (Scene token) or raw16. **Kit: absent.**

### (b) Enemy AI — `EVT_BATTLE_*.eb`

| Lever | Controls | Channel | Location | DLL? | Kit |
|---|---|---|---|---|---|
| Spawn / AI binding | `InitObject(1+type, 0x80+slot)` per slot | eb | `event_data.rewrite_main_init`; `EventEngine.cs:560-571` | No | **partial** (only this) |
| Attack select | which scene attack (0..AtkCount-1) on the ATB turn | eb | `BTLCMD 0x38` (`DoEventCode.cs:1198`); often an expression into a working var | No | **absent** |
| AI thresholds / branches | HP%/MP/status/phase conditions | eb | expr ops `B_CURHP=82 / B_MAXHP=83 / B_CURMP=110 / B_SYSVAR=122 / B_SYSLIST=121` → `btl_scrp.GetCharacterData` | No | **absent** |
| Counter / dying / phase / call-help | new AI branches by tag | eb | tags via `Request/RequestAction`: tag 1 main loop, **tag 6 counter, tag 7 ATB, tag 9 dying** | No | **absent** |
| Instant special | fire a raw17 seq without an ATB turn | eb | `AttackSpecial 0xE5` | No | **absent** |
| Forced / scripted battle | start a specific scene on a trigger | eb | `Battle 0x2A` / `BattleEx 0x8C` | No | **absent** |

### (c) Shared actions / abilities — `Data/Battle/Actions.csv` (player-side)

Header (`Actions.csv:5`):
`Comment;id;menuWindow;targets;defaultAlly;forDead;defaultOnDead;defaultCamera;animationId1;animationId2;scriptId;power;elements;rate;category;statusIndex;mp;type;commandTitle`.
**192 rows required POST-MERGE** (`FF9BattleDB.cs:63-65`) — the base supplies them; a delta overrides a subset.

| Lever | Controls | Channel | Location | DLL? | Kit |
|---|---|---|---|---|---|
| power / elements / rate / mp | damage / element / hit-or-status% / MP cost | CSV | cols 12/13/14/16 → `BTL_REF`/`AA_DATA` (`BattleActionEntry.cs:13-45`) | No | **absent** |
| **scriptId** | which battle-calc formula runs | CSV (re-point) **/ DLL (new)** | col 11 → `ScriptsLoader.GetBattleScript` (`ScriptsLoader.cs:215-223`) | re-point **No** / new formula **Yes** (`Memoria.Scripts.<Mod>.dll`) | **absent** |
| category / type | physical/magic/reflectable/contact/weapon-props/crit bits | CSV | cols 15/17 (`type 0x8/0x10/0x20` only when `CustomBattleFlagsMeaning=1`) | No | **absent** |
| statusIndex (AddStatusNo) | which `StatusSets.csv` row it inflicts/cures | CSV | col 16 → `StatusSetId` | No | **absent** |
| targets / menuWindow / camera / vfx | targeting + cursor display + VFX ids | CSV | cols 3-10 | No | **absent** |

Elements bitmask (`EffectElement.cs:8-16`): Fire=1, Cold=2, Thunder=4, Earth=8, Aqua=16, Wind=32, Holy=64,
Darkness=128 — the **same 8-bit space** as the enemy Guard/Absorb/Half/Weak bytes.

### (d) Statuses — `Data/Battle/StatusData.csv` + `StatusSets.csv` + `MagicSwordSets.csv`

| Lever | Controls | Channel | Location | DLL? | Kit |
|---|---|---|---|---|---|
| OprCount (tick) / ContiCount (duration) | how punishing each ailment is (0/0 = permanent) | CSV | `StatusData.csv` → `btl_stat.cs` | No | **absent** |
| ClearOnApply / ImmunityProvided | what a status clears / blocks | CSV | `BattleStatusDataEntry.cs:29-70` | No | **absent** |
| StatusSets (bundles) | the named multi-status groups actions apply | CSV | `StatusSets.csv` (`#! UnshiftStatuses`); ids ≥39 | No | **absent** |
| MagicSwordSets | Steiner+Vivi combo unlocks | CSV | `MagicSwordSets.csv` | No | **absent** |

`StatusData` requires ids 0-32 post-merge (`FF9BattleDB.cs:88`).

### (e) Party / character / growth — `Data/Characters/*.csv`

| Lever | Controls | Channel | Location | DLL? | Kit |
|---|---|---|---|---|---|
| **BaseStats** (Dex/Str/Mag/Will/Gems) | the real per-char combat stats | CSV (partial, 0-11) | `BaseStats.csv` → `ff9level.cs` | No | **absent** |
| **Leveling** (Exp / BonusHP / BonusMP) | 99-step growth curve; `HP=BonusHP*Str/50`, `MP=BonusMP*Mag/100` | CSV (**whole-file**, 99 rows) | `Leveling.csv` → `ff9level.cs:53` (`GetCsvWithHighestPriority`) | No | **absent** |
| CharacterParameters | row / category / menu-preset / equip-set | CSV (partial, 0-11) | `CharacterParameters.csv` → `ff9play.cs` | No | **absent** |
| Commands / CommandSets | battle-menu definitions + per-char layout | CSV (partial) | `CharacterCommands.cs` (0-44 / 0-19) | No | **absent** |
| Abilities/`<Name>.csv` | learn list + AP cost | CSV (**whole-file per preset**) | `ff9abil.cs:432` (`GetCsvWithHighestPriority`) | No | **absent** |
| AbilityGems | support-ability stone costs | CSV (partial, 0-63) | `AbilityGems.csv` → `ff9abil.cs:409` | No | **absent** |
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
camera nudge/sweep (raw17, `camera_data`/`camera_codec`), BGM (`BattlePatch Music: <akao song id>`). The raw17
`btlseq` attack choreography is shipped **verbatim** (no codec → cannot author).

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
| **raw17 opening camera** | **YES, true codec** | `camera_codec.parse_block ↔ serialize_block` (offset-table repack) | Satisfied **but tested only on SYNTHETIC raw17** — never asserted vs a real donor block |
| **battle `.eb`** | **YES, general codec** | `EbScript.from_bytes(x).to_bytes()==x` on real donors | Container round-trips; **no AI-body authoring** beyond `rewrite_main_init` |
| **raw16 (`SB2_MON_PARM`)** | **COPY-identity only** | `scene_data.py` byte-patches ~9 offsets; rest verbatim | Surgical = byte-accurate-by-construction for those 9; **no full parse↔repack codec** |
| **raw17 btlseq (sequences)** | sliced-verbatim, **never parsed** | `camera_codec.py` splices `raw17[:camOffset]` | No codec → cannot author attack choreography |
| **`.mes`** | **copy only** | `shutil.copyfile` | Never parsed |
| **Actions/Status/Character CSVs** | **no reader at all** | — | Absent — but a *partial delta* is inherently lossless on untouched rows |

**Honest framing:** with no `[scene]` overrides a forked→built `raw16/raw17/eb/mes` is byte-identical to the
donor — but by **passthrough copy**, not a parse→emit codec. The methodology's "parse a real X → re-emit →
prove ==" is genuinely proven **only for the FBX**; the gameplay assets rely on **never touching bytes they
don't understand**.

**What each new lever needs first:**
- **raw16 affinity/status/defence/AP fields** → trivial: extend `_MON_FIELDS` with the verified offsets (all
  fixed-width scalars, identical `struct.pack_into` pattern). **No new codec.** Gate: a **real-donor golden
  round-trip test** (`import EF_R007 raw16 → parse → re-serialize → assert == original`), **capturing the
  engine-ignored tail verbatim** (a naive re-emitter that stops at body-end *truncates* — `EF_R007` 652→448).
- **Actions/Status/Character CSV deltas** → a read-live + delta-emit module mirroring `itemstats.py`; partial
  deltas are non-destructive by design; must carry `#!` legends.
- **Enemy AI bodies** → the container round-trips, so it's an **emitter/vocabulary** task (battle opcode names
  + SV_ model + an expression assembler), not a parser task.
- **raw17 btlseq + a new attack id** → needs a btlseq codec (camera-codec's offset-table repack proves it's
  feasible). Highest cost, lowest priority.

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

**`[scene]` today** (`scene_data.py`): surgically byte-patches a *forked* raw16 for **exactly 9
`SB2_MON_PARM` fields** (`hp@12, mp@14, gil@16, exp@18, speed@52, str@53, mag@54, spr@55, level@64`) + drop/steal
ids (`@20/@24`, by name) + `SB2_PUT` placement + MonsterCount + Camera + the opening camera (raw17). With
`monster_count` it re-composes every pattern and re-authors the eb `Main_Init` InitObject bindings (up to the
4-enemy engine cap, existing types only).

**Misses:** the whole enemy combat identity (5 element bytes, 3 status masks, 4 def/evade, HitRate, Category,
BlueMagic, MaxDamageLimit — all `[PatchableField]`, all trivially addable); rewards (AP ×2, drop/steal rates,
WinCard); scene flags; pattern Rate; **all CSV channels** (no action/ability layer at all — item *names* only);
**enemy attack table** (raw16 tail); **enemy AI bodies**; a `BattlePatch.txt` emitter; model re-skin (`Geo/Mot`).

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

### Phase 2 — the validation/lint suite (the superpower)
Ship the §5 checks. Reuses Phase-0 catalogs + Phase-1 fields; can ship incrementally.

### Phase 3 — CSV-delta ability + status authoring (the natural WIN vs HW)
Read-modify-emit minimal `Actions.csv`/`StatusData.csv`/`StatusSets.csv` deltas via `ModLayout`, carrying the
`#!` legends. A `[[battle_action]]`/`[[status]]` block. Composes campaign-wide. (Enemy attacks live in raw16,
not Actions.csv → the enemy-attack analog is the Phase-4 BattlePatch emitter.)

### Phase 4 — `BattlePatch.txt` emitter for enemy/attack/scene tuning
By-name/index `Battle:`/`AnyEnemyByName:`/`AnyAttackByName:`/`Pattern:`/`Scene:` blocks targeting
`[PatchableField]`s (scene flags, drop-rate arrays, **enemy AA_DATA** power/element/rate/status) — the only
clean way to reach the rate arrays + enemy attacks without re-packing raw16. *Verify:* coexistence with the
kit's existing repoint/Music BattlePatch lines (avoid the wholesale-restore clobber the field pillar warned of).

### Phase 5 — character/growth CSV deltas
`BaseStats.csv` (partial), `Leveling.csv` (**whole-file, 99 rows**), `AbilityGems.csv`, optionally
`Commands/CommandSets`. Pairs with story_flags' `[party]`/`[startup]`. **Explicitly NOT `BattleParameters.csv`**
(cosmetic only).

### Phase 6 — enemy-AI authoring (highest ceiling, hardest)
Substrate exists (`EbScript` round-trips; `replace_function_body`/`add_function` byte-safe). Needs a
**battle-opcode name/semantics layer** (SV_Target/SV_ model, `B_CURHP/SYSVAR` vocabulary), an **expression
assembler**, and a **battle linter** (valid tags 1/6/7/9, Attack index `< AtkCount`). Stage: disassembler view →
same-length literal patches → new branches. **Defer raw17 btlseq sequence authoring** (new codec + a
coordinated raw16+eb+raw17 tri-file edit).

---

## 9. Open questions & risks

- **`Configuration.Mod.MergeScripts` default** — gates whether two mods' `.eb` edits to the same battle merge
  or whole-file-clobber. Check the live `Memoria.ini [Mod]`.
- **In-game smoke test a sparse partial `Actions.csv`/`StatusData.csv`** — the merge accepts it in theory (base
  supplies the rest), but the coverage gates + per-file `#!` reset make an in-game check mandatory before
  shipping a delta emitter.
- **raw16 tail provenance** — the post-`AtkCount` block is overwhelmingly zero and `ReadBattleScene` never
  reads it; confirm no other loader reads `dbfile0000.raw16` by a larger length before a re-emitter re-appends
  it.
- **Camera codec on a real donor raw17** — `parse_block↔serialize_block` is synthetic-tested only; assert
  `serialize_block(parse_block(raw17)) == raw17[camOffset:]` on `EF_R007`.
- **Enemies do NOT pull from `Actions.csv`** — a tool editing `Actions.csv` to retune enemy moves mis-targets
  every enemy edit (enemy attacks = raw16 AA_DATA / BattlePatch only). (`btl_util.cs:353-354`)
- **Category default bits / the vanilla `type` byte** — only the `CustomBattleFlagsMeaning=1` meanings are
  documented; trace `CalcResult` before a designer-facing picker labels them.
- **Provenance discipline** — all raw16 stat bytes + all CSV stat values are SE game DATA: read live, never
  commit. Only name↔id/element/status/category tables (from open-source Memoria enums) are committable.

**Key refs:** `BTL_SCENE.cs:50-153`, `SB2_MON_PARM.cs:20-179`, `FF9BattleDB.cs:35-117`,
`AssetManager.cs:849-862`, `DataPatchers.cs:60-137,413-682`, `EventEngine.DoEventCode.cs:956-1234,2938`,
`BattleCalculator.cs:210-741`, `ScriptsLoader.cs:215-311`, `scene_data.py:32-36`.
