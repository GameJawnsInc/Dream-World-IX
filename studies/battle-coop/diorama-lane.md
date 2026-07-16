# The BATTLE DIORAMA (B3) — build spec (2026-07-15; recon PASS 1 complete + adversarially verified)

> The last rung of the authoritative-host roadmap: **the guest SEES the host's fight** — a live,
> full-3D rendering of the host's battle on the guest's machine, driven entirely by the wire.
> Sits inside the SPECTATOR-FIELD PARADIGM (PLAN.md): the guest is a combat participant and a field
> spectator; the diorama is where the combat-participant half becomes visual.
>
> **THE LAW: NEVER RE-SIMULATE.** The guest's diorama plays back *choreography*; every number
> (damage, HP, death) is the HOST's result arriving on the wire. The unseeded-RNG re-simulation
> dead-end is documented and closed — do not reopen it.

## THE HEADLINE FINDING — `isDebug` is a trap, not a tool

The skeleton assumed `FF9StateSystem.Battle.isDebug` was the diorama's "render-only" switch. **It is not.**

1. **It is a DEAD flag.** Nothing in the entire Memoria tree ever sets it true. Only two writers
   exist, both `= false`: `BattleStateSystem.cs:52` (Init) and `HonoluluFieldMain.cs:238`. It cannot
   arrive from Unity scene data either — `BattleStateSystem` is `AddComponent`'d at runtime
   (`FF9StateSystem.cs:46-47`) and its `Awake()` calls `Init()`. **The diorama must set it itself**,
   and re-assert it after any field encounter (`HonoluluFieldMain.cs:238` clears it on encounter start).
2. **It gates the INPUT half of the sim, not the OUTPUT half.** `battle.BattleMain()` is called
   UNCONDITIONALLY at `HonoluluBattleMain.cs:678`; the `if (!isDebug)` gate at :679 opens *after* it.
3. **Therefore a stock `BattleMapDebug` boot silently writes the guest's real save.**
   `ManageBattleEnd → btl_sys.SavePlayerData` (`btl_sys.cs:260-275`) has no isDebug gate and writes
   `PLAYER.cur` hp/mp/at/capa, trance, status, and serial_no — the guest's **real party**.
4. **And it never stops.** `IsOver` (the `ATTR.EXITBATTLE` bit) is set at exactly one site,
   `HonoluluBattleMain.cs:690`, *inside* `if (!isDebug)`. With isDebug on, the battle never ends,
   `UpdateBattleFrame` keeps running, and **`SavePlayerData` re-fires every frame**.

> **THE CONTAINMENT LAW:** `isDebug` buys the input half for free and is worth setting — but the
> diorama's save-safety comes from an explicit **suppression set** (below), never from `isDebug`.
> Containment is rung ZERO; nothing renders until the guest's save is provably untouchable.

## What is already proven / on the wire (don't rebuild)

| Piece | Where | Status |
|---|---|---|
| The scene's true composition | **`BattleMapDebug` == `BattleMap` − SwirlScene + one `BattleUI` MonoBehaviour.** Resolved at the ASSET level: `mainData` BuildSettings idx 9 = BattleMapDebug (`level8`), idx 21 = BattleMap (`level20`), idx 5 = SwirlScene (`level4`); hierarchies + component sets identical (`Battle Main` carries `HonoluluBattleMain`) | ★ asset-proven — closes the skeleton's one open premise |
| Battle boot by scene id | `BattleUI.cs:144-171`: set `battleMapIndex` + `patternIndex`, then `SceneDirector.Replace("BattleMapDebug", …)` | stock debug path |
| Enemy AI suppression | Dead at FOUR layers under isDebug: `HonoluluBattleMain.cs:191` (EVT_BATTLE never loaded), `battle.cs:73/178` (ServiceEvents never ticked), `:529` (RequestAction gated), `SBattleCalculator.cs:311` (dying/counter/reaction gated) | stock, free |
| ATB / ready / menu suppression | `HonoluluBattleMain.cs:679` wraps `YMenu_ManagerActiveTime()`, the only caller of `ProcessActiveTime` | stock, free |
| Local HP application suppression | `btl_para.cs:145` — damage renders via `fig.hp` but never lands. Exactly the wire-authoritative model | stock, free |
| The party's wire data | **state section 1** (NetSyncParty) — but its field set is INCOMPLETE, see B3.2 | ★ proven (rung 2), needs extension |
| Live battle truth | **B0 type-1 frames** (`NetSyncBattle.BattleView`), ~150 ms cadence | ★ two-machine proven |
| Guest commands | **B1 type-2 FIFO** + the digit-menu UI | ★ two-machine proven |
| Battle presence signal | `NetSyncBattle.PeerBattleLive` | ★ proven |
| HonoBehavior teardown law | **DOES NOT APPLY.** No battle-side object is a HonoBehavior (12 subclasses, all field/world/ending/movie; closed under transitivity; `grep HonoBehavior` over the battle tree is EMPTY). Stock raw-`Destroy`s battle actors | ★ verified — no ceremony needed |

## THE SUPPRESSION SET (rung 0 — the containment gate)

Every site below is **un-gated** and **save-visible** on a `BattleMapDebug` boot. Recommendation: a
dedicated `NetSyncDiorama.Active` flag (NOT `isDebug`, which is load-bearing elsewhere and whose
semantics are "no input", not "no writes"). Snapshot-and-restore is safer than per-site gating for
the counter families, which are fed from four different files.

| # | Lane | Site(s) | Why it matters |
|---|---|---|---|
| 1 | **Party writeback** | `btl_sys.SavePlayerData` **:260** — call sites `btl_sys.cs:168`, `:175`, `BattleUnit.cs:579` | Writes the guest's REAL party. Re-fires every frame. **The first hook.** |
| 2 | **Win/lose evaluator** | `btl_sys.CheckBattlePhase` **:52** — **FIVE** ungated call sites: `btl_mot.cs:349` (enemy die), `btl_mot.cs:366` (**player die**), `btl_mot.cs:726`, `btl_stat.cs:96` (any BattleEnd status — reachable in PHASE_NORMAL with no die_seq), `BattleUnit.cs:583` | Early-return it. Highest-value hook. Game-over = a KICK TO TITLE (`HonoluluBattleMain.cs:727` → `GameOverUI.cs:58`) — session-critical, not cosmetic |
| 3 | **The status TICK** | `btl_stat.cs:301` — `(effect as IOprStatusScript).OnOpr()` | **THE BURIED LANDMINE.** `Memoria/Scripts/DefaultStatus/*.cs` have **ZERO** isDebug guards (33 scripts). `PoisonStatusScript.cs:30-33` does `Target.CurrentHp -= damage` + `Target.Kill()` unconditionally. The guest **will self-kill actors**. Invisible solo; only manifests when a real poisoned actor ticks |
| 4 | **Kill counters** | `btl_mot.cs:342` `categoryKillCount[category]++`, `:344` `modelKillCount[dms_geo_id]++` | Save-serialized (`JsonParser.cs:932-945`) AND gameplay-live (feeds kill-count abilities). Fires on EVERY enemy death |
| 5 | **Flee gil penalty** | `battle.cs:455-470` — `sys.party.gil -= gilLost` | A live save write on the guest's OWN gil, ungated + IsOver-independent, whenever the diorama replays a host Flee |
| 6 | **Gil (other)** | `btl_scrp.cs:836` (opcode 38), `BattleCalculator.cs:62` (Scripts-DLL setter) | Script-driven gil writes |
| 7 | **Achievements** | `btl_sys.cs:172` (UpdateEndBattleAchievement) + mid-battle: `btl_stat.cs:126`, `btl_cmd.cs:1441/1507/1557`, `btl_sys.cs:210`, `BattleCalculator.cs:138` | Writes `AchievementState`, pops Steam |
| 8 | **Story flags** | `BattleActionCode.cs:698` — `gEventGlobal[arr] = …` | A battle SFX action-code can write the guest's save-backed flags |
| 9 | **Next-field hijack** | `btl_scrp.cs:831-832` (opcode 37) — `BTL_MAP_JUMP_ON` + `SetNextMap(val)` | A mirrored scripted fight can redirect where the guest lands |
| 10 | **Reward rolls** | `btl_sys.SetBonus` **:223-258** — `Comn.random8()` drops | RAM-only today (needs `GoToBattleResult`), but the draws advance the RNG stream. Gate it |
| 11 | **'No enemy left' auto-end** | `battle.cs:180-207` → sets `PHASE_CLOSE`/`SEQ_DEFEATCLOSE_FADEOUT`; the fade fires LATER at `battle.cs:168` | Gating only :180 is insufficient — :168 stays reachable whenever btl_phase reaches PHASE_CLOSE by any route |
| 12 | **Reward layer** | `BattleResultUI.cs:558/590/700/715` | Unreachable today only via the IsOver accident. Gate `GoToBattleResult` explicitly **before ever setting IsOver** |
| 13 | **In-battle menu** | `BattleHUD.Public.cs:801/813/820`, `BattleHUD.cs:2632-2641`, `:2775-2784` | Immediate item add/remove + party rewrite. Blocking the menu covers all of it |
| 14 | **★ THE ENCOUNT HOLE** | `DoEventCode.cs:957` (ENCOUNT `0x2A`) **and `:969` (ENCOUNT2 `0x8C`)** | `SuppressEncounters` reaches only `IsNoEncounter` (the random/step + worldmap counters) — **both scripted-battle opcodes are untouched**, so a following guest can run a full LOCAL battle and collect local rewards (`BattleResultUI.cs:700/715`) + Steal (`BattleCalculator.cs:766`). → `inventory-authority.md` |

**Also restore at teardown:** `isDebug`, `battleMapIndex`, `patternIndex`, `debugStartType`,
`party.battle_no`, `categoryKillCount[8]`, `modelKillCount`, Achievement counters, `party.gil`,
and the `gEventGlobal` band the mirrored scene could touch.
**Stale `btlMapNo`:** nothing writes it at debug boot, and `battle.cs:100` reads it — a stale 336
fires the Masked Man tutorial. Stamp it.
**Backstop:** keep the diorama inside the mirroring-session lifecycle so the AUTOLOAD EXIT RAMP
discards anything that slips through.

## THE RETURN (lifecycle — solved)

The return is decided by **`prevMode`**, not fldMapNo. Two independent variables: `prevMode` picks
the SCENE, `FF9.fldMapNo` picks WHICH field. `BattleResultUI.Hide` (`:51-56`) sets
`mode = prevMode` then `SceneDirector.Replace("FieldMap"|"WorldMap")` — **with no else**, so an
invalid prevMode fires no Replace at all and hangs on a faded-out result screen.

**The substitution (cleanest):** on the host's battle-end frame, replicate `Hide`'s tail —
```csharp
PersistenSingleton<FF9StateSystem>.Instance.mode = prevMode;
SceneDirector.Replace("FieldMap", SceneTransition.FadeOutToBlack, true);
```
This skips `UpdateOverFrame`, the Result screen, the EXP/AP/gil award, and `GoToGameOver`.
Verified safe out of `BattleMapDebug`: every SceneDirector branch fires identically as from
`BattleMap` — the sole difference is the AutoSplitter `SignalBattleEnd`, which doesn't fire because
`BattleMapSceneName == "BattleMap"` (`SceneDirector.cs:715`).

**Preconditions:** the guest must have `prevMode == 1` and `fldMapNo == <its own field>` before
booting. Do NOT re-point `map.nextMapNo` from the host's wire. The fork-return path is verified
benign (a fork-id lookup misses `ForkSiblingMap` and returns the input unchanged).
**The debug scene has NO designed way back to a field** (`BattleUI.cs:71/82` → `LastScene`/`MainMenu`) — B3 authors it.

## THE SWIRL / BGM (solved — one cheap win, one hook)

`Replace("BattleMapDebug", SceneTransition.SwirlInBlack, true)` buys **swirl + encounter SFX + battle
BGM with no new engine code** — `_Swirl` is target-agnostic (`SceneDirector.cs:549-550` stash
`PendingNextScene`; `BattleSwirl.cs:61` `ReplacePending` reads it). Untested pairing; worth a playtest.

The debug boot otherwise loses exactly what lives in `BattleSwirl.cs`: the swirl visual, the 636/635/634
SFX (`:74-76`), and the battle BGM (`:96` — the only battle-ENTRY `ff9btlsnd_song_play`). It KEEPS the
plunge camera, the 32-frame wipe-in + PHASE_ENTER, the staged actor fade-in, BattleVoice, and
`ApplyBattleEffects`. Sound dispatch is a non-issue (`FF9BattleSoundDispatch` is a pure forwarder to
`FF9AllSoundDispatch`, which `SceneDirector.cs:429` installs for BattleMapDebug anyway).

**Three flags must be mirrored from the host** (all un-armed by a debug boot):
- `isDebug` — see the headline.
- **`isRandomEncounter`** — set true at exactly one site (`EventEngine.ProcessEvents.cs:479`); scripted
  battles clear it. Drives the swirl's LOOK (`SFX_Rush.cs:37-56`), the actor fade SPEED
  (`battle.cs:490/530/555`), and `SkipCameraAnimation`. Unmirrored → always the scripted-battle swirl + slow fade.
- **`debugStartType`** — `btl_init.cs:105-108`: under isDebug, `scene.Info.StartType` is OVERRIDDEN by
  `debugStartType`. Stamp **`debugStartType`**, NOT `scene.Info.StartType` (which `SetupBattleEnemy`
  overwrites every run).

**BGM needs an s38 hook:** `BattleSwirl.cs:91` computes songid from the LOCAL fldMapNo — a guest
elsewhere gets its own field's theme. That exact line is already an ff9mapkit patch site (s33 wraps it
with `EffectiveFieldId`), so a wire song id with fail-safe fall-through is precedented. Note
`BattleSwirl.cs:82-86` only plays when `gMode` is 1 or 3 (captured at Awake).

**Field-side pre-swirl work to replicate** (`HonoluluFieldMain.cs:316-320`): song suspend +
`SuspendResidentSounds` + `SFX_Rush.SetCenterPosition(0)`. `SceneDirector.cs:405` stops sound EFFECTS
only — without this the guest's **field BGM keeps playing under the battle**.

## NEUTRALISE `BattleUI` (mandatory, and free)

`BattleMap` ships with **no** BattleUI at all, so `HonoluluBattleMain` provably runs without it — the
dependency is one-directional. Two reasons to kill it on the diorama:
- **A live hazard:** `BattleUI.Start:26` executes `btl_scene.PatNum = FF9StateSystem.Battle.patternIndex;`
  with **no isDebug guard**, running after `HonoluluBattleMain.Start` — clobbering PatNum *after*
  `InitBattleScene` already built the actors from `ChoicePattern()`'s roll. A silent PatNum/actor
  mismatch unique to this scene.
- Its `OnGUI` draws the full SQEX map/pattern/sequence panel over the diorama whenever isDebug is on.

**Also mirror the UIManager delta:** `UIManager.cs:282-290` omits `BattleHUDScene.Loading = true` and
sets `isEnable = true`, so `:317` **enables player control** — inverted vs BattleMap (`:244-252`).
A render-only guest wants control disabled.

## THE WIRE (v8) — corrected

### 1. The battle-OPEN frame → **SHIPPED as the type-1 HEADER BLOCK (B3.3), not a FIFO lane**
The recon-era "one-shot FIFO frame" design was superseded at build time: the type-1 battle frame
already streams at 150 ms with latest-slot semantics and already carries `mapNo` — and **real battles
stamp `battleMapIndex = btlMapNo` (`ff9.cs:9252`), so the debug boot and real battles share ONE id
space**; no mapping table exists or is needed. v8 inserts 4 bytes after `guestSlots`:
`[patNum u8][startType u8][flags u8 (bit0 = isRandomEncounter)][nonce u8]`
- **Latest-slot beats FIFO here**: a late-joining guest still gets the current battle, the lane going
  stale IS the battle-over signal (no close frame to lose — the PEER-ALIVE LAW's shape), and the
  NONCE (bumped per own-battle rising edge) distinguishes back-to-back battles even on the same
  map+pattern.
- **THE STACKED-STALENESS LAW** (verify-pass find): the transport serves the last frame for its own
  ~2 s window after the sender stops; re-stamping the consumer's freshness tick on those REPEATS
  stacked two windows (~4 s decay). The tick now refreshes only when the frame's **seq advances** —
  staleness tracks when the HOST last sent, not when the transport last served.
- `songId` deferred with the swirl/BGM pairing; `MonsterCount + typeNo × N` (the divergence assert
  for modded hosts) deferred with it — **so is per-pattern-index validation on the guest** (an
  out-of-range PatNum from a modded host throws inside `HonoluluBattleMain.Start`'s swallow; the
  failure is CONTAINED — the diorama is armed, F6 Leave works — but ugly. The scene-data hash in the
  version handshake is the real fix for the whole class.)

**The enemy set is 100% scene-file data**, selected by the pair `(battleMapIndex, PatNum)` — NOT by
`patternIndex` alone, and NOT randomized at spawn. The roster is immutable at runtime (all three
exclusivity greps reproduce one write site each, inside `BTL_SCENE.ReadBattleScene`), and
BattlePatch.txt cannot touch it by two independent mechanisms. **So typeNos are not needed for
correctness** — send `battleMapIndex` + the host's **resolved PatNum** (read back after
`HonoluluBattleMain.cs:185`; never mirror the RNG).

**StartType is NOT free** — `btl_sys.StartType` is a THIRD RNG (two `random8()` rolls vs
backAttackChance=24 / preemptiveChance=16, further modified by party SAs). It flips enemy rotation
180° on a pre-emptive, flips player base angle + `row ^= 1` on a back attack, and changes ATB seeding.
Under isDebug it silently pins to `BTL_START_NORMAL_ATTACK` forever. **Carry it.**
(A FOURTH RNG remains: player initial ATB, `Comn.random16() % btl.max.at`, `btl_init.cs:437`.)

**Boot-order law:** `InitEnemyData` does NOT run at `HonoluluBattleMain.cs:189` — its only call site is
`battle.cs:521`, inside `BattleLoadLoop` during PHASE_ENTER, **frames later**. So PatNum must be
authoritative BEFORE `HonoluluBattleMain.Start` and remain stable until PHASE_ENTER completes; any
re-stamp in that window repoints the STAT init away from the already-spawned MODELS.

### 2. The action-playback lane (FIFO)
**The choke point: `SBattleCalculator.CalcResult` (`SBattleCalculator.cs:141`), emitting at line 310**
(`FrameAppliedEffectList.Add(v)`), immediately before the `if (target.bi.player != 0 || isDebug) return;`
guard at :311. All three branches (guard/miss/hit) converge at :291; :291-309 are unconditional; :310
is the last statement before the first conditional return. Results are **final AND post-application**
(reflect ×, damage-limit clamp, 9999 cap, then `SetDamage` at :223 — all strictly before :310).

Four corrections to the naive frame:
- **Carry BOTH units, fresh, every call.** "One BattleCalculator = one (caster,target) triple" is FALSE:
  `:264-284` is an entire `if (v.Caster.Flags != 0)` block applying HP/MP to the **caster** (drain,
  recoil). WhiteDraw (`0041:33`) does `_v.Caster.Change(unit)` — its *target* never changes and the
  whole effect is caster-side; a target-keyed frame would emit N no-ops and drop every point of MP
  restored. Serialize `v.Caster.Id`, `v.Target.Id`, both `Flags`, both `HpDamage`/`MpDamage`. Never cache either.
- **Send raw `Data.cur.hp` / `Data.cur.mp`, NOT `BattleUnit.CurrentHp`.** `CurrentHp` is a property over
  `GetLogicalHP/SetLogicalHP` (`BattleUnit.cs:74-78`) that offsets by 10,000 for `FLG_NON_DYING_BOSS`
  and force-overrides under IsHpMpFull. The round trip is **lossy** — it would corrupt exactly the boss
  fights the diorama exists to show.
- **Emit in a `finally`.** `CalcResult` has no try/catch of its own and runs inside `CalcMain`'s try
  (catch at :115). An exception in :143-309 skips :310 while HP was ALREADY applied at :223 — host
  damages, no frame ships. Pair with a periodic absolute HP resync.
- **DO NOT hook `IOverloadOnBattleScriptEndScript` (:323)** — it sits BELOW the :311 guard, so it never
  fires for player targets or under isDebug.

Exactly 5 `PerformCalcResult=false` scripts exist (0040/0041/0049/0052/0061); all are covered.
**Verified:** no ff9mapkit/s22-s37 patch touches SBattleCalculator, btl_para, btlseq, btl_cmd,
BattleUnit, or BattleCalculator — the isDebug gates are stock.

### 3. The status-tick lane
`btl_stat.cs:301` (`OnOpr` dispatch, called from `battle.cs:228` + `HonoluluBattleMain.cs:558`) — the
second and last hook. Either gate it on the guest and mirror ticks from the wire, or accept self-kill.
Note the tick's floating number goes through `btl2d.Btl2dStatReq`, a DIFFERENT path from `btl.fig.hp`
— the "damage number for free" property does **not** transfer to ticks.

### 4. Type-1 stays the continuous truth
HP/MP/ATB/status/death; the diorama reconciles toward the frame after every playback.

## The rung ladder (revised — containment first)

- **B3.0 — THE CONTAINMENT GATE. ★ BUILT 2026-07-15** (`NetSyncDiorama.cs`), solo-selftest pending.
  `NetSyncDiorama.Active` = `_armed && NetSyncClient.IsMirroringStory` — **fail-safe by construction**:
  a flag stuck true can never suppress a real player's battle. Five gates + one bracket:
  | Lane | Where | Shape |
  |---|---|---|
  | Party writeback | `btl_sys.SavePlayerData:260` | early-return the **definition** (covers all 3 call sites) |
  | Win/lose evaluator | `btl_sys.CheckBattlePhase:52` | early-return the **definition** (covers all **5**) |
  | **The status tick** | `btl_stat.cs:301` | skip the `OnOpr` dispatch — *the buried one* |
  | Story flags | `BattleActionCode.cs:698` | skip the `gEventGlobal` write |
  | Next-field hijack | `btl_scrp.cs:829` (op 37) | skip `SetNextMap` |
  | gil + **both** kill-counter families | `Snapshot()`/`Restore()` bracket | fed from 4 files — a bracket can't be out-flanked |
  Types corrected against source: `categoryKillCount` is **`Int16[]`**, `modelKillCount` is
  **`EntryCollection<Int16,Int16>`** (a `Dictionary` subclass whose indexer returns a default rather than
  throwing — probe with `ContainsKey`).
  **Already closed upstream, not re-done here:** the Steam achievement escape and ENCOUNT/ENCOUNT2 (Road A,
  s38). The **reward layer** (`BattleResultUI`) stays unreachable *only because* the return substitutes
  `mode = prevMode` + `Replace("FieldMap")` instead of setting `IsOver` — **gate `GoToBattleResult`
  explicitly before ever setting `IsOver`.**
  SELFTEST (`NetSyncDiorama.SelfTest`, wired into the existing `_storyProofDone` block): proves the
  predicate is fail-safe and the bracket lossless — **without booting a scene**, since booting is rung 1.
- **B3.1 — boot + return. ★ IN-GAME PROVEN 2026-07-15** (solo, F6 → Go → Battle diorama): the scene
  boots, renders the party, **ATB frozen and nobody acts** (isDebug's input-half suppression, confirmed
  visually), **returns cleanly**, **gil untouched**. Boot = the STOCK recipe verbatim
  (`battleMapIndex` + `patternIndex` → `Replace("BattleMapDebug", FadeOutToBlack_FadeIn)`); `SwirlInBlack`
  deliberately deferred (untested pairing + its BGM song id resolves from the LOCAL fldMapNo). The scene
  list is read live from `FF9StateSystem.Battle.mapName` (the shipped `BattleMapList.txt`) so ids are
  never guessed. **The predicate went through three rejected designs — see the block below; each was a
  real hole.**
- **B3.2 — the mirrored party.** Extend wire section 1 with **`basis{max_hp,max_mp,dex,str,mgc,wpr}`**
  (~12B) + `status` + `permanent_status` + `trance` + `sa`/`saExtended`. **Carry basis, NOT max** —
  `FF9Play_Update` begins `play.max.hp = play.basis.max_hp` unconditionally (`ff9play.cs:276-277`), so a
  written max does not survive; and carrying only max leaves `elem[4]` at the level-1 minimum. This is
  exactly what the save's own PLAYER-deserialize path carries (`JsonParser.cs:827-835` → restore →
  `FF9Play_Update`). Follow the save's precedent.
  **ORDER LAW:** mutate `FF9.player[charId]` IN PLACE (never construct a bare PLAYER; `party.member[i]`
  aliases the dict via `FF9Play_SetParty`), write row+equip+Name+level+basis, then **`FF9Play_Update`**
  (NOT `Build` — Build re-derives basis from the guest's zeroed `bonus` and destroys it), then assign
  `cur.hp`/`cur.mp` **LAST**.
  Traps: don't write `info.menu_type` without resizing `pa[]` (`BattleHUD.cs:1375-1383` indexes
  unchecked → IndexOutOfRange); `Name` silently falls back to the stock default if dropped
  (`PLAYER.cs:127-136`). Freebie: a wire hp of 0 gives a correctly-downed actor for free
  (`btl_init.cs:477-484`).
  **`CreatePlayer` is a red herring** — it reads ONE field (`p.info.serial_no`) and everything else comes
  from the static `BattleParameterList`. The real build is `btl_init.OrganizePlayerData` (`:369-488`).
  `serial_no` itself is DERIVED (NCalc over equip[0]) and force-recomputed after every battle/equip/load
  — redundant on the wire given equip[5].
- **B3.3 — enemies. ★★ TWO-MACHINE PROVEN 2026-07-16** (after B3.3b telemetry + B3.3c tick-baseline
  fix, DLL `128C7B5C60569FC8`): **"the diorama works! host battles pull the guest in now"** — the
  authoritative-host battle headline: the host enters a fight and the FOLLOWING guest's screen fades
  into the same battle, live. Known cosmetic bug, FILED not chased (user: meatier features first):
  the F6 opt-out replays the battle intro once — suspects = a ≥2 s lane blip clearing the skip-nonce
  (`!live` resets it) or a host-side `InOwnBattle` flap bumping the nonce mid-fight (the watcher
  would leave-and-reboot itself); the guest log now narrates every boot, so a captured log names it.
  Solo tier had passed all five boxes first try:
  `btlFields=ok` in the containment selftest; the wire bench booted a visibly PRE-EMPTIVE diorama
  (`parsed map=0 pat=0 start=FIRST rand=1 nonce=77 -> boot`) while the plain Boot's normal layout
  stood as the A/B; Leave clean; and a real selftest encounter put the ENCODER's boot block on the
  spectate panel (`scene 67 pat 1 NORM rand` — note `rand` lit on a random encounter, the flag's own
  proof). Both codec halves and the boot path are now in-game proven; only the watcher's live
  behaviors (auto-boot/leave, nonce, skip) remain two-machine. Enemies come FREE through the
  stock spawn — B3.1/B3.2 already proved the `(battleMapIndex, PatNum)` boot path with locally-chosen
  scenes, so this rung's real content was THE WIRE: the type-1 header block (above), the guest-side
  watcher (`NetSyncClient.DioramaTick`, the battle-lane analogue of FollowHostTick: boot on a live
  boot block while free-standing on a field + `_storyMirroring`; LEAVE on lane staleness; nonce change
  = come home then re-boot; a deliberate F6 leave sets a per-battle SKIP nonce so the watcher never
  yanks the user back into a fight they walked out of; `[Netsync] Diorama` default 1 opts out), and
  `Boot` growing `debugStartType` + `isRandomEncounter` stamps (both BRACKETED, with
  `battleMapIndex`/`patternIndex`, in Snapshot/Restore + the selftest's new btlFields lane).
  **Verify-pass finds folded in:** the CONTAINMENT-LAW enforcement gap (Boot rendered even when
  `Snapshot()` failed, and a failed snapshot makes every Restore a NO-OP — the un-gateable
  `++battle_no` would leak; Boot now REFUSES on `!_haveSnapshot`); the stacked-staleness law (wire
  section); the un-installable-scene log spam (the watcher skip-nonces that battle with ONE line);
  and **a recon correction: the diorama never arms `gMode`** (isDebug skips `StartEvents`, the only
  gMode 2/4 writer) — so `InOwnBattle` is ALREADY false inside it, the guest was never going to
  stream the projection back, and the `&& !Booted` qualifier on Pump's `inBattle` is defense in
  depth, not a fix. A welcome corollary: the B1 assist digit menus + spectate panel STAY USABLE over
  the diorama (`live && !inBattle` holds) — most of B3.6 arrives early.
  **The solo bench** = F6 → "Wire bench": a fabricated v8 frame through the REAL `ParseView` →
  `BootFromWire` → the `debugStartType` stamp → the engine. Marker = `StartType = FIRST_ATTACK` —
  NON-ZERO (`BACK_ATTACK == 0`: a zeroed byte can't fake it) and NON-DEFAULT (Init and the plain F6
  Boot both stamp NORMAL == 2). PASS = the enemies stand ROTATED 180° (the pre-emptive layout) + the
  bench log line. (The panel does NOT render inside a bench diorama — no sampling at gMode 1; the
  encode side is instead proven by any real selftest ENCOUNTER, whose panel header now shows
  `[scene/pat/start/rand]`.) Two-machine items (auto-boot/leave, nonce re-boot, skip-nonce) pending.
  *(Recon contingency notes, kept for B3.4+: `btl_sys.AddCharacter` NREs on an EMPTY list
  (`btl_sys.cs:293`; the head's `.next` is nulled at InitBattleSystem) — a manually-inserted first
  actor is required if actors are ever spawned outside the stock path; actors must link into
  `btl_list` or they get no texture animation (`BattleTexAnimWatcher.Update`); spawn after
  `CreateBattleRoot` (`:176`) and always pass `isBattle:true` or `ModelFactory.cs:199` silently
  skips parenting.)*
- **B3.4 — drive the truth. ★ SOLO PROVEN 2026-07-16 (DLL `1DF72621C60C82EA`).** The state bench
  passed whole: CARNAGE killed every enemy (poses + fades) **with the battle simply standing** — the
  phase-flipper proof — and the party panel read **HP 123 / MP 45 / half ATB / trance glow** on slot
  0; RESTORE stood everyone back up through the real revive lane, UI never blinking (ATB 0 after
  restore is the fabricated frame's own value — a live wire re-drives it in 150 ms). En route the
  bench FOUND **R7**: `btl_sys.CheckForecastMenuOff` on last-enemy-dead hides the battle HUD ahead
  of a victory transition the diorama doesn't have, and nothing re-enables it (the enable is a
  one-shot at the PHASE_NORMAL flip) — gated at the definition, which also fences the AutoSplitter
  win signal (the audit's R6 note) for free. Spectate-panel regression passed (dead units now show
  KO instead of vanishing — better). **Two-machine pending**: the host's live fight driving the
  guest's actors (HP under damage, kills, trance, revives, hidden/submerged enemies).
  Recon = workflow `wf_9eeb1bc2-c3a` (13 agents, 4 CONFIRMED / 2 CORRECTED / 0 REFUTED; **full
  verified record = `b34-recon.md`**). The BUILD verify pass (2 more agents) then killed two of my
  own deviations before the DLL: **(1) the missing-as-dead sweep REFUTED** — it contradicted the
  recon's hold-last-state law and would have PERMANENTLY killed alive-but-unlinked host enemies
  (the case-33 submerge/reinforcement idiom); fixed at the ROOT the way the recon prescribed: the
  host sampler now enumerates **`btl_data` directly** (dead units ride the wire as Alive=false — a
  late-joining guest kills them on its first reconcile, no inference; script-hidden units carry a
  new **HIDDEN bit** — info bit 16, v8-benign — that the guest mirrors as the case-33 renderer
  idiom without the list surgery); **(2) the Alive bit read LOGICAL CurrentHp** — under
  `CustomBattleFlagsMeaning=1` a non-dying boss inside its dying band reads logical 0 while alive
  and the guest would kill it; the sampler now derives Alive from **raw `cur.hp` + the Death
  status**. En route: the slot IS GetIndex, so the sampler's log2 loop is gone. PHASE_NORMAL
  reachability in the diorama was CONFIRMED from source (the MENU_ON→NORMAL promotion is neither
  isDebug- nor containment-gated) — the reconciler runs. The five R-gates verified to preserve
  every normal path. **The solo bench** = F6 in a diorama → "State bench (kill/restore)": carnage
  kills ALL enemies (doubling as the phase-flipper proof: with CheckBattlePhase + R1 both gated,
  the all-dead diorama must simply STAND) + player 0 at HP 123 / MP 45 + TRANCE + half ATB;
  restore revives everyone (the real revive lane if pressed before the fade completes).
  The distilled design:
  **THE RESOLUTION PRIMITIVE (C1):** wire Index == the `btl_data` ARRAY SLOT (GetIndex = log2(btl_id);
  players = COMPACTED party positions 0-3, enemies 4-7 in pattern order — deterministic, no RNG on the
  identity path; no mid-battle unit creation exists anywhere: summons/multi-part = pre-spawned pattern
  units relinked with btl_id unchanged). Resolve by DIRECT `btl_data[Index]` + guards (btl_id == 1<<i,
  side match, player bi.slot_no vs the HOST-compacted NetSyncParty.Slots CharId — never the guest's own
  party). **NEVER EnumerateBattleUnits** (btl_list is blind to DelCharacter'd units) and **NEVER
  GetIndex() guest-side** (btl_id==0 → infinite loop). Ready when the boot latch AND
  `btl_load_status & (LOAD_INITNPC|LOAD_INITCHR)` == both (one BattleLoadLoop frame sets ALL of it).
  **THE HP WRITE SPLIT (C2, dissolves the logical-vs-raw conflict):** btl_para's ±10000 boss transform
  is ENEMY-only (bi.player==0) and the IsHpMpFull booster snap is PLAYER-only (bi.player!=0) ⇒
  **players = raw `Data.cur.hp/cur.mp`** (exact, booster-immune) · **enemies = logical
  `CurrentHp`/`MaximumHp`** (the inverse of the host's logical sample) · MP raw both · max lane FIRST
  (CheckPointData clamps cur to max next frame).
  **DEATH (the pipeline is ungated and self-driving):** wire-dead + no Death status ⇒ raw `cur.hp = 0`
  ONCE (+ optional same-tick AlterStatus(Death) + one SetDefaultIdle for snappy onset) — CheckPointData
  applies Death next frame; the POSE comes from btlseq.DispCharacter's anim-END block → SetDefaultIdle
  (NOT DieSequence — its setMotion is commented out), so up to one idle-cycle latency. Dead stays dead:
  Death status present ⇒ write NOTHING (idempotent). **REVIVE = HP FIRST, then RemoveStatus(Death)**
  (the engine's own AutoLife idiom; fail-safe on an aborted tick). A fully-faded enemy (die_seq 6,
  DelCharacter'd) needs FindBattleUnitUnlimited + a MANUAL tail-safe re-link (**AddCharacter NREs on
  tail insertion**) + SetDisappear(false,5) + renderer + die_fade_rate from a boot snapshot.
  **TRANCE:** raw stat.cur Trance bit (**REQUIRED for enemies too** — the glow candidate list builds
  from CurrentStatus; enable_trance_glow is only the inner key) + `enable_trance_glow`; players' model
  swap via the STATELESS PROBE `(data.gameObject == data.tranceGo) != wire.InTrance` →
  btl_vfx.SetTranceModel (corpse-safe, revive-self-healing; C4: Death does NOT strip the bit in a
  command-less diorama — edge-triggers are fragile, the probe isn't). Never AlterStatus(Trance), never
  SetTranceModel on enemies (tranceGo null).
  **ATB (safe to drive):** players only — raw `max.at` then CurrentAtb clamped; menu-wake impossible
  (AddPlayerToReady's only caller is inside the gated ProcessActiveTime chain). Enemies have no gauge.
  **R1-R6 — THE RESIDUAL CONTAINMENT SET (ships in the SAME DLL round; R1-R4 are preconditions):**
  R1 `battle.cs:180` auto-end block on !Active (the last mirrored enemy death → die_seq 5 →
  DelCharacter → the UNGATED "no enemy left" cascade → btl_result/fades/ManageBattleEnd per frame →
  VICTORY achievement); R2 `btl_stat.cs:125` player UpdateAbnormalStatus on !Active (save-serialized +
  fires at diorama BOOT via OrganizePlayerData's status replay — definition-level, a bracket can't
  undo a live Steam report); R3 `SettingsState.SetTranceFull` on Active (per-frame booster war:
  AlterStatus→SysTrans→CommandEngine→persistent trance achievement); **R4 the BUMPER-ESCAPE HOLE —
  LIVE IN THE CURRENT DIORAMA TODAY**: BattleMapDebug runs in UIState.BattleHUD, and after the
  PHASE_NORMAL command-enable a guest holding L+R bumpers drives btl_sys.CheckEscape → the flee
  script runs the SIM (gate BattleHUD.Unity's combo or CheckEscape on !Active); R5 the
  `btl_para.cs:98` IOverloadUnitCheckPointScript dispatch on !Active (the kit's OWN Overload hub runs
  per frame on mirrored actors — a [deathrules] second-wind would resurrect reconciled deaths; +
  PARITY LAW: Scripts-DLL parity joins the DLL-version law); R6 (hygiene) AutoSplitterPipe already
  double-gated by Speedrun config — document only.
  **WIRING:** ReconcileTick from NetSyncClient.Update right after DioramaTick; data via an internal
  `NetSyncBattle.TryGetPeerUnits` struct-copy seam; guard ladder Booted+Active → btl_phase ==
  PHASE_NORMAL exact → the load latch → fresh seq. Laws: trust Alive over HpCur; wire frame missing a
  known index ⇒ hold last state; NEVER mirror AutoLife/DeathChanger statuses; boosters documented-off
  (with R3 + raw player writes they stop being load-bearing).
  **In-game-only residue:** the phase-flipper census (a baked scene MonoBehaviour is invisible to
  source — the BattleUI precedent), SetTranceModel pose-pop outside a SysTrans, faded-revive
  shadow/texanim residue, death-pose latency acceptability, and whether the party panel renders bars
  worth driving.
- **B3.5 — action playback. ★ SOLO PROVEN 2026-07-16 (wire v9, DLL `6F999C4575266592`) — "solo test
  100% pass."** The figure bench popped its hand-built 1234 over enemy slot 4 repeatedly (the
  Singleton<HUDMessage>-aliveness precondition holds — the wire lane's display path is real); the
  state bench regression passed on an 8-unit scene ×2 cycles; a real selftest battle ran the emit
  with zero codec-drift lines; clean teardown. Bonus proof: the user's 2-second carnage→restore
  gap let one fast-fading enemy reach die_seq 5, and **the faded-revive guard fired live with its
  designed telemetry** ("unsupported, holding dead") — the documented limitation observed exactly
  as specified, not discovered as a bug.
  Recon = `b35-recon.md` (workflow `wf_c9729bc5-5b2`, 11 agents, 5/5 CORRECTED + the audit's 13-item
  checklist); implementation delegated against the checklist, then adversarially verified — **the
  first large round of the arc with ZERO confirmed defects** (the CalcResult surgery diffed
  byte-exact; the seq-horizon math holds at every boundary; the party codec byte-symmetric; F1-F6
  all realized). What shipped: **the TypeAction FIFO** (type 6, own 64-cap queue pair in the shared
  frame-slots — never collapsible, both transports); **the CalcResult emit** (whole-body try +
  `emitted` flag + finally backstop; dual dmg_mot capture incl. the DirectHP branch; ~46 B frames:
  both units' raw post-application HP/MP, both fig triples, flags, cmd identity, and the
  **seq-horizon** — the emit CONSUMES the sampler's shared `_seq`, so `sample.seq >= horizon ⇔
  post-application`, exact by construction); **the guest ActionTick** (drain-before-reconcile;
  apply order: nonce gate → resolve → FIGURES FIRST via hand-built empty-modifier `Btl2dReq` (never
  Btl2dReqInstant — the v9 status carry arms the IFigurePointStatusScript trap) → guarded
  flinch/player-swing decided from WIRE lethality → raw-vs-raw state writes bypassing the logical
  lanes → per-slot horizon gates that make a stale type-1 sample skip the whole unit); **party v9**
  (section-1 basis/status/trance/SA carry; the seat gains the equip ContainsKey→NoItem guard,
  per-slot containment, `FF9Abil_SetEnableSA` replay, and the *never Validate**\* law — the 9999
  clamp and default-SA gaps close); the type-1 **trance-gauge byte**; F2 receiver drain-and-discard;
  F3 nonce plumbing; the self-cast aliasing skip (found at build time: target.fig IS caster.fig).
  **Accepted gaps (documented, per-design):** Poison/Regen TICK figures never pop (they bypass
  CalcResult — the most visible gap; a future Btl2dStatReq emit closes it), enemy caster motions
  (their `mot` sets have no generic swing), the trance ENTER burst, IFigurePointStatusScript display
  modifiers. **Solo bench** = F6 "Figure bench (pop 1234)" (the audit's precondition: prove
  Singleton<HUDMessage> aliveness before trusting the lane) + the state bench regression + a real
  selftest battle (the emit side runs on any host battle; selftest loops it through TryParseAction
  with a codec-drift log). Two-machine = README boxes 11-14.
- **B3.6 — the UI merge.** B1 digit menus over the diorama; the OnGUI spectate panel retires or becomes
  the no-diorama fallback.

## THE PREDICATE — three rejected designs, each a real hole (2026-07-15)

`NetSyncDiorama.Active` guards a save-corruption path, so its shape was adversarially attacked before
shipping. Every earlier candidate was wrong:

| Candidate | Why it FAILED |
|---|---|
| `_armed && IsMirroringStory` | `IsMirroringStory` needs a live socket, and **the selftest branch returns before the socket is ever built** — so it is STRUCTURALLY UNREACHABLE in `Role=selftest`, the project's own solo-proof mode. The diorama could never be benched, and the containment selftest became a **TAUTOLOGY that could not fail** (`IsMirroringStory \|\| !Active` — either disjunct is trivially true). It reported green while proving nothing. |
| `CurrentScene != "BattleMap"` (suppress unless proven a real battle) | **DANGEROUS.** A real battle boots THROUGH THE SWIRL, so `CurrentScene` reads `"SwirlScene"` while the real BattleMap activates → the test is TRUE → **a stuck flag suppresses a REAL battle**. It flips a fail-safe default into a fail-dangerous one. |
| `SceneDirector.CurrentScene == "BattleMapDebug"` | `CurrentScene` is SceneDirector's **bookkeeping copy and LAGS the live scene**: `ChangeSceneAsync` assigns it only *after* an awaited `LoadLevelAsync`, which ACTIVATES the scene first. Reachable whenever `_discChange != 0` — and that flag is **never reset after a disc change**. Scene live + predicate false = uncontained writes. |

**SHIPPED:** `_armed && _booted && Application.loadedLevelName == "BattleMapDebug"` — the ENGINE's live
scene name (correct by the new scene's `Awake`, hence before `HonoluluBattleMain.Start`; it is what
SceneDirector itself seeds `CurrentScene` FROM, and what `UIManager.OnLevelWasLoaded` keys on). The test
is **POSITIVE**, so every uncertainty fails toward "diorama unsuppressed" (a bug) rather than "real
battle suppressed" (corruption).

### The companion bugs the same pass found — all were LIVE in the first cut
- **`NetSyncBattle.SelfTest` is DEFAULT-TRUE** on every install that never wrote a `[Netsync]` section
  (`_role != "host" && _role != "client"`, **not** gated on `_enabled`). Using it bare in the boot gate
  would have let **any vanilla player** boot a diorama. → new `NetSyncClient.IsSelfTestRole` (positive,
  enabled-gated, so a typo'd role fails CLOSED). *Its one existing consumer is safe only because it
  always pairs it: `if (!Enabled || !SelfTest)`.*
- **`Leave()` cleared containment BEFORE the fade** — `Replace` fades over MULTIPLE FRAMES with the
  diorama still live and `BattleMain()` still pumping, now unsuppressed, with `btl_phase` possibly parked
  in PHASE_VICTORY/DEFEAT whose branches call `ManageBattleEnd → SavePlayerData`. → Leave is
  **request-only**; teardown moved to `HonoluluBattleMain.OnDestroy` **gated on `Booted`** (unconditional
  would Restore a stale snapshot over EVERY REAL battle's rewards — the fix that is itself a bug).
- **`SceneDirector.Replace` silently no-ops while fading** (`if (this.IsFading) return;`). Booting
  mid-fade would arm + set `isDebug` and never change scene → **isDebug stranded TRUE on a live field**,
  which softlocks the next real battle (the overworld encounter path never clears it, and with it on the
  battle can never end). → Boot gates on `IsFading`; Leave defers instead of stranding.
- **`Arm()` was a loaded gun** — it early-returned without re-snapshotting, so a leaked `_armed` meant the
  next `Disarm` wrote a STALE snapshot over real progress. → always re-snapshot.
- **`party.battle_no`** (`battle.cs:61`) runs from `InitBattle ← Start` with the isDebug gate AFTER it —
  no call site to gate. → bracket-only, by necessity.
- **Boot's catch called `Leave()`** → now DISCARDS the bracket (nothing has scribbled yet; applying it
  would write stale state for no reason).

## B3.2 — THE MIRRORED PARTY ★★ IN-GAME PROVEN 2026-07-16 (both markers)

### THE SCRATCH-PARTY IS DEAD — not risky, structurally impossible
A battle actor's identity is a **`Byte`**, not a pointer: `btl_init.cs:378` stamps
`btl.bi.slot_no = (Byte)p.info.slot_no`, and from that instant **every** PLAYER resolution is a
**dictionary lookup keyed on that byte** — `btl_util.getPlayerPtr/getSerialNumber/getWeaponNumber`, and
`BattleUnit.Player` (the accessor the whole battle system uses). A scratch PLAYER reachable only via
`party.member[]` is abandoned the moment the spawn path hands it off, and the engine finds the guest's
own character again. One HUD would disagree with itself: `BattleHUD.cs:1160` reads `unit.Player` (dict)
while `:428` reads `party.member[..].PresetId` (pointer).
*Corroborating invariant:* all **13** writes to `party.member[]` in the tree assign `null` or a
**dict-resolved** PLAYER. No PLAYER outside the dict has ever been in that array.
*Also:* there is **no same-call bracket** — `CreateBattleData` runs in `Start`, `InitPlayerData` runs
**N frames later** inside `BattleMain`, `SFX.InitBattleParty` later still. Any mutation spans the
diorama's whole lifetime: Boot -> ForceDisarm.

### THE SHIPPED SHAPE — THE DICT-VALUE (REFERENCE) SWAP
Install a **scratch** into the dict slot (`ff9.player[id] = scratch`) and put the **original object
references** back on teardown. Pointer and dict agree (both see the scratch), and **the guest's own
PLAYER objects are never touched** — so "a missed field in the bracket" becomes *impossible* rather than
carefully avoided. **Total by construction.**
> Rejected: mutate-in-place + a per-field content bracket. The ORDER LAW mandates `FF9Play_Update`,
> which resets `mpCostFactor` + 4 limits and `Clear()`s saForced/saBanish/saHidden — so in-place needs a
> bracket over **14 reference members plus re-derived scalars**: a list that rots. **Pick one; never
> stack them** (a reference bracket is worthless under in-place).
> Rejected: a JSON round-trip clone. `ParseCommonDataToJson` is private + whole-state, and the save does
> **not** persist `permanent_status`/`mpCostFactor`/`saForced`/`saBanish`/`saHidden`. Not total.
> **Every copy helper in this family is already rotted:** `btl_init.CopyPoints` drops POINTS' 5th field
> (`at_coef`); `CharacterEquipment.Clone()` drops `Comment` + `Id`.

### The build, with the traps that crash it
- **`new PLAYER()` does NOT construct `info` or `pa`** (`PLAYER.cs:10-31` builds cur/max/elem/defence/
  basis/equip/bonus/sa but not those two) -> NRE on the first `p.info.serial_no`. **`FF9Play_New(id)` is
  mandatory** (it sets info + sizes `pa[]`).
- **`Mathf.Clamp((Int32)s.Level, 1, ff9level.LEVEL_COUNT)`** — Level is a wire **Byte**; >99 indexes
  `CharacterLevelUps[lv-1]` out of range. (The engine's own two-sided precedent: `DoEventCode.cs:3111`.)
- **Guard the throwing indexers**: `ff9level.CharacterBaseStats.ContainsKey(id)` and
  `btl_mot.BattleParameterList.ContainsKey(serial)` — both fed by unchecked wire bytes.
- **`MirrorHostParty` needs its OWN try/catch calling `RestoreParty`** — `HonoluluBattleMain.Start`
  swallows everything (`catch (Exception err) { Log.Error(err); }`), which would hide the failure AND
  strand the swap.
- **Set the snapshot flag BEFORE the scribble.**
- **Assign `party.member[i]` DIRECTLY — never `FF9Play_SetParty`**: it calls `FF9Play_Add`, which sets
  `player.info.party = 1` — **save-persistent** and read by 4 live sites. It would permanently mark a
  guest's character as in-party. (`FF9Play_SetFaceDirty` is dead — zero callers.)
- **`FF9Play_Build(scratch, lv, init:true, lvup:false)` is legal on a scratch** (`lvup:false` only reads
  `bonus`) and is the engine's canonical source for `basis.dex/str/mgc/wpr`, which the wire lacks.
- **NEVER write `info.slot_no`** (it is the dict key's identity) or `info.menu_type` (the `pa[]` trap).
- Restore: dict entries by key to the **original objects**, then element-wise `Array.Copy` into the
  existing `party.member` array (`BattleHUD.cs:2641` writes into it). Wire into `ForceDisarm()`, gated on
  `Booted`, never `Active`.

### RUNG 2.5 — the bracket before the apply ★ BUILT 2026-07-15 (selftest pending)
The diorama bracket covers gil/battle_no/kill-counters and **nothing about the party**, and
**`Role=selftest` has NO save guard at all** (`IsMirroringStory` needs a socket, so the autosave block,
the manual-save block and the ENCOUNT gates never fire) — on the very machine the bench runs on.
**Extend the bracket — or add an explicit save block on `NetSyncDiorama.Booted` — BEFORE any apply.**

**BUILT (no apply yet — the net exists before anything can fall onto it):**
- `SnapshotParty()` at Arm / `RestoreParty()` at Disarm — the four `party.member[]` **references**, plus
  `RememberOriginalPlayer(id)` for the apply to call immediately before `ff9.player[id] = scratch`
  (**first-write-wins**, so a re-entrant apply can never bury the real object behind a scratch).
  Restore is idempotent and safe when the apply never ran (the maps are simply empty).
- **The save block on `Booted`** — `EventEngine`'s autosave ladder + `SaveLoadUI`. **Not redundant:**
  every other save guard keys on `IsMirroringStory`, which needs a live socket, so `Role=selftest` —
  the mode the diorama is benched in — has **none of them armed**.
- **A selftest that can FAIL:** it takes a real PLAYER, records `cur.hp` + the `saExtended` count, runs a
  full swap-and-restore over it, then asserts **both** `refs=ok` (reference identity restored, i.e. the
  swap undid) **and** `untouched=ok` (the real object was never written through). Reference identity
  alone would pass even if we had mutated-and-restored — the probe is what proves the reference bracket
  is buying what it was chosen for.

### The solo bench — "the impostor slot", and why the obvious bench is vacuous
A loopback that mirrors the guest's **own** party makes a correct apply **invisible** — the same vacuous
trap as the old `failsafe=OK`. So the bench needs **TWO** markers:
- **Marker A (the SEAT)** — an **impostor** CharId in slot 0. Select it as the first `CharacterId` in
  `FF9.player` **absent from `party.member[]`** — *never* `info.party == 0`, which means RECRUITED, not
  benched. Falsifies model, tag, row-from-dict, shadow-from-dict, and the HUD name.
- **Marker B (the CARRY)** — a **scratch source** PLAYER (fields copied **explicitly**; `PLAYER_INFO` is
  a **class**, so a shallow clone aliases) with `Name = "BENCH"`, `level = 99`. A source-swap seam makes
  every wire scalar identity for the impostor, so Marker A alone proves the seat, **not the carry**.
- Add a `SlotSource` seam to `NetSyncParty` (mirror of `NetSyncDiorama.SceneName`), restored in a
  `finally`. Arm it in **`HonoluluBattleMain.Start()`**, not `Boot()` — a Boot-time arm opens a
  mirrored-field window on a machine with no save guard.
- `Clear()` on Disarm must be **selftest-gated**: production's mirror is **field-load-scoped**
  (`ParseSections` has one production caller, `HonoluluFieldMain.cs:135`), so an unconditional Clear
  wipes a real host mirror on every diorama exit.
- **PASS = the impostor's model in slot 0 AND the HUD reads BENCH at level 99.** Both, or it proved half.

### BUILT — what landed
- **`NetSyncDiorama.MirrorHostParty()`**, hooked at **`InitBattleScene`'s top** (upstream of both
  consumers). No-op unless `Active && _havePartySnapshot && NetSyncParty.MirrorActive` — with no host
  data the guest's own party stands, i.e. B3.1 behaviour.
- **The private-indexer problem, solved transitively:** `FF9Play_New` indexes the **private**
  `CharacterParameterList[slotId]`, which we cannot guard from outside — but `FF9Play_Init` builds
  `FF9.player` **from** it (`ff9play.cs:65-73`), so the key sets are identical *by construction* and
  `ff9.player.ContainsKey(id)` covers it. (`FF9Play_New` also mutates `ff9.player[id]` in place, so the
  scratch must be installed **first**.)
- **The bench** — `NetSyncParty.SelfTestMirror` + a `SlotSource` seam; armed in **`Start`**, gated on
  `IsSelfTestRole`; `Clear()` on Disarm selftest-gated.

### ★★ THE PROOF (2026-07-16, solo bench)
Party was Blank / Zidane / Steiner / Vivi. Boot →
```
[NetSync] diorama party BENCH: armed (slot 0: Blank -> Dagger, name BENCH, lv99)
[NetSync] diorama seated the host's party: 4 slot(s)
```
- **SEAT ✓** — slot 0 rendered **Garnet's model**, not Blank's. The dict swap reached the model spawn,
  the actor tag (`bi.slot_no`), and the HUD's dict-keyed name lookup.
- **CARRY ✓** — the HUD read **BENCH**: a string invented on a scratch source, through the real encoder
  → the real parser → the apply. A no-op apply would still have shown the impostor, but under *Blank's*
  name — which is exactly why Marker B exists. (Level is unobservable in the battle HUD but rides the
  identical path.)
- **RESTORE ✓** — Blank back in slot 0 on leave; the reference bracket undid a live 4-slot swap on the
  guest's real party.

**This is the mechanism B3 exists for:** the host's characters can stand in the guest's diorama, and the
guest's own party survives untouched.

### Known fidelity gap (a wire question, not a safety one)
The wire carries no SA data, so the scratch's `mpCostFactor`/limits/SA re-derive from an empty
`saExtended` -> host characters render with correct stats/equip/HP but **default SA modifiers**. And
`max.hp` clamps to `maxHpLimit` 9999, so a modded host's HP renders capped. -> v8 (B3.2b).

## Recon status

**PASS 1 COMPLETE (2026-07-15)** — 8 questions, each answered from source then adversarially verified
(16 agents). 7 of 8 answers were materially corrected by the verify pass; the corrections are folded in
above. Notable saves: the `IOprStatusScript` self-kill lane (the original answer built a false safety
guarantee on a `// Dummied` function with zero callers), the `basis`-vs-`max` party contract, the
caster-side result frame (WhiteDraw), and `CurrentHp`'s lossy round-trip on non-dying bosses.

**Cross-resolved:** the swirl agent settled the lifecycle agent's one open premise by reading the
shipped Unity scene assets directly — `BattleMapDebug` provably carries `HonoluluBattleMain`.

**RESOLVED IN-GAME 2026-07-15 (was UNRESOLVED from source):** `BattleUI` **IS** attached to the
BattleMapDebug scene. The C# tree could never settle it — scene composition lives in the bundles, and no
`AddComponent<BattleUI>`/`GetComponent<BattleUI>` exists anywhere in the assembly. The first diorama boot
drew its "Pattern 1/1" panel over the scene. **So both of its hazards are LIVE**: `Start:26` re-stamps
`btl_scene.PatNum` with no isDebug guard (benign for us — we author `patternIndex`, so it agrees), and
`OnGUI` is held shut only by `isDebug`, which the diorama must set. Closed by gating `BattleUI.OnGUI` on
`NetSyncDiorama.Active` — which also kills its **"Back" button, a rogue `Replace("MainMenu")` under
isDebug** that would skip the authored Leave and dump a guest into the main menu.
- Custom-FBX prefabs carrying a serialized HonoBehavior — the residual unknown in the teardown census.
  The diorama controls that input anyway.

**Rungs 0, 1, 2.5, 2, 3 ★ solo proven (wire v8 CUT + laptop package `FF9Coop-laptop-update-20260716`
carrying the two-machine checklist).**

### B3.3b — THE SILENT-CHAIN FIX (2026-07-16, same day; retest pending)
The FIRST two-machine run declined the diorama with ZERO diagnostic output: guest followHost=1,
relay, follow-warped to 250, ghost + spectate panel fine — no diorama, and NO log line explains why
(the absence of Boot's REFUSED line is what triangulated it to `_storyMirroring == false`, a
diagnosis that took the better part of an hour and a source dive to reach). Two lessons, one round:
- **EVERY GATE THAT CAN DECLINE MUST SAY SO** (the `BootBlockedReason` principle, applied to the
  whole chain): `ApplyStoryImpl` now logs each field-load outcome (ARMED once / transport
  not-created / not-connected / no-host-snapshot / apply-FAILED — real guests only, one line per
  load); `DioramaTick` logs ONE line per peer-battle nonce naming a durable block (FollowHost=0 /
  Diorama=0 / party-mirror-not-armed note; client-only — on a HOST whose guest fights,
  "FollowHost=0" would be true but describe nothing wrong); the `mapName` catch skip-nonces + logs.
- **THE DIORAMA'S SESSION PREDICATE IS PEER-ALIVENESS, NOT THE STORY MIRROR.** `_storyMirroring`
  arms only at a field-load boundary that sees a host snapshot — a session where that hasn't
  happened yet silently disqualified the diorama, even though its save-safety never depended on
  the mirror (the rung-2.5 bracket + `Booted` save block are self-contained, and fresh battle
  frames are the strongest peer-alive signal there is). New `NetSyncClient.IsLiveFollowedSession`
  (enabled + FollowHost + role=client + connected + position-lane `Valid` — every conjunct
  defaults false, vanilla stays fail-closed) joins `MayBoot`; the watcher drops its mirror gate.
  An un-armed party mirror degrades to the-guest's-own-party, logged.
Root cause of the mirror not arming: **still unknown** — that is exactly what the new telemetry
answers on the next run, whichever way it goes. No wire change (still v8; mixed same-version DLLs
pair fine, both machines updated anyway — `CCD07F16C06CC0D2`).

### B3.3c — THE TICK-BASELINE LAW (2026-07-16; the REAL root cause, both runs)
The B3.3b telemetry earned its keep in ONE run: `state-mirror ARMED` printed 3 s after pairing —
**the mirror was never the problem, and run 1's diagnosis-by-absence was wrong.** This run's
healthy-silent rising edge (no durable block to name) narrowed the decline to the gates classified
"transient", and exactly one of them can be permanent:
```
private Int32 _dioramaActionTick;                                  // = 0
if (Environment.TickCount - _dioramaActionTick < 1000) return;     // silent
```
**`Environment.TickCount` wraps NEGATIVE at 24.86 days of machine uptime** (the laptop: 25 d 7 h,
CONFIRMED). `now - baseline` is wrap-safe only between two REAL ticks; against a field's 0 default
it flips permanently on one side of the wrap — `now - 0 < 1000` became always-true and the watcher
declined every frame, forever, on that one machine, under every DLL. **The timeline corroborates:
the laptop crossed the boundary between 07-15 and 07-16 — the same suite passed one day and failed
the next with zero code change.** THE LAW: every tick baseline initializes from
`Environment.TickCount` at construction; never compare a tick against a 0/MinValue default.
The sweep fixed 8 fields, most of them LATENT pre-existing members of the same class, keyed to
whichever machine's uptime crosses first: `_dioramaActionTick` (the actual failure) ·
`_storyTick` (a long-uptime HOST would never publish TypeState — the story mirror itself) ·
`_lastSampleTick`/`_lastRosterTick` (a long-uptime host never streams battles — B0/B1 dead) ·
`_lastPoll` (config hot-reload dead — dead on the laptop since 07-15) · `_ghostLightTick` (ghost
tint never re-applies) · `_lastSendTick` (assist keys swallowed forever) · `_assistTick`, the
**MinValue variant**: `TickCount - MinValue` OVERFLOWS small/negative for half the tick space, so
on ordinary positive-tick machines a host's GuestSlots read guest-owned with NO guest ever
connected. (B3.3b's relaxation + telemetry both stay — good design that found the truth in one
run vs an hour of absence-forensics.)
**Next:** B3.4 (type-1 → HP/death/trance on the diorama's actors) · B3.2b (the party v9 extension:
basis/status/trance/SA — ride it with B3.5's action lane, one bump) · the swirl/BGM pairing · the
scene-data hash divergence assert. Emit the whole B3 arc as **s40** when it settles (s39 is taken).
