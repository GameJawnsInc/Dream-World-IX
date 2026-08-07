# FF9 ATB & combat-timing control surface

> Research synthesis (2026-07-14). Scope: **how the ATB gauge and battle-turn cadence work in the Memoria
> engine, every lever that already reaches them, and the design space for pushing them further** — the
> timing analog of [`BATTLE_DESIGN.md`](BATTLE_DESIGN.md) (which covers stats/abilities/AI/rewards). Every
> claim cites Memoria source `file:line`, verified against the pinned engine commit **`6b8bb2d5`**
> (`memoria-patches/BASE_COMMIT`); any engine hook proposed here must build against that same commit.
>
> Provenance: analysis + citations only — **zero Square-Enix bytes**. All stat/formula values are read live
> from the user's install, never committed.
>
> **Status: RESEARCH + PLAN, not built.** Nothing in §7–§9 is shipped. This pillar is **deliberately
> deferred behind co-op Phase 2 (the authoritative-host diorama)** — see §8 for why, and why building ATB
> hooks *first* would be the wrong order. Read §8 before starting any engine work here.
>
> Related: [`BATTLE_DESIGN.md`](BATTLE_DESIGN.md) · [`SCRIPTS_DLL.md`](SCRIPTS_DLL.md) · [`ENGINE.md`](ENGINE.md).

---

## 1. Executive summary — the four control tiers

Everything you can do to combat sorts into four tiers by **reach vs. cost**. The kit already operates in
Tiers 0–2.

| Tier | Mechanism | Reach | Engine rebuild? | Relaunch? |
|---|---|---|---|---|
| **0 — Config** | `Memoria.ini` `[Battle]`/`[Hacks]`/`[Cheats]` + save-backed `cfg.atb`/`cfg.btl_speed` | Global battle behavior: ATB mode, fill rate, overflow-carry, menu turn-cost, and the stat/status/trance **NCalc formula strings** | No | ini: yes; in-game sliders: live |
| **1 — Data content** | CSV deltas, raw16, **enemy AI `.eb`**, `BattlePatch.txt`, `DictionaryPatch.txt`, `AbilityFeatures.txt` | Per-enemy/ability/status identity, AI behavior **including direct gauge writes**, status-mask membership | No | mostly yes |
| **2 — Scripts-DLL** | `Memoria.Scripts.<Mod>.dll`: additive `[BattleScript]`/`[StatusScript]`/`[FieldAbilityScript]` **+** override `IOverload*` | New battle formulas, new status *behaviors*, damage/command/gameover interception | Mod DLL only (compile-at-deploy) | yes (loads at title) |
| **3 — Engine** | `Assembly-CSharp.dll` rebuild (`memoria-patches/` stack) | *Anything* — including a real per-ATB-tick hook | Full engine (AUTO-DEPLOY, no backup) | yes |

**The load-bearing boundary:** the ATB fill loop is **invisible to every Tier-2 hook**. None of the 10
`IOverload*` interfaces and no `IStatusScript` hook fires on a gauge increment (§6). So per-tick gauge
control is strictly Tier 3 — *but* a surprising amount of ATB manipulation is reachable at Tiers 0–1 without
recompiling the engine (§4, §7).

---

## 2. The ATB bar dissected

### 2.1 The math (verified by three independent source reads)

```
storage:   POINTS.at      (Int16)   btl.cur.at = live gauge, btl.max.at = "full" threshold
           POINTS.at_coef (SByte)   per-unit fill coefficient
           BTL_INFO.atb   (Byte)    per-unit "may this gauge run" gate flag

MaxATB  =  (60 − Dexterity) × 40 << 2   =  (60 − Dex) × 160          btl_para.cs:56  (GetMaxATB)
per tick:  cur.at += (Int16)(at_coef × 4)                            HonoluluBattleMain.cs:461
at_coef =  8 / 10 / 14  (Slow / Normal / Fast, cfg.btl_speed)        btl_para.cs:66  (GetATBCoef; default 10)
"full"  =  cur.at ≥ max.at            (a comparison, never a stored boolean)
cadence =  15 TPS (BattleTPS)         GraphicsSection.cs:37; applied HonoluluBattleMain.cs:98,139
```

- **Storage:** `POINTS.at` is `Int16`; carried twice per `BTL_DATA` as `cur` (live) and `max` (threshold)
  — `POINTS.cs:7-8`, `BTL_DATA.cs:138-139`. Logical accessors `BattleUnit.MaximumAtb` / `CurrentAtb` —
  `BattleUnit.cs:91-96`.
- **The fill lives in `HonoluluBattleMain.ProcessActiveTime`** (`:415-564`), **not** in `btl_para.cs`
  (which only holds the rate constants). Flag this — the natural assumption puts the fill in `btl_para`.
- **Higher Dexterity → smaller max → fills faster.** Ticks-to-fill = `(60−Dex)×40 / at_coef` (the two ×4s
  cancel). Worked: Dex 20, Normal → 160 ticks ≈ **10.7 s** at 15 TPS; Dex 40 → ~5.3 s; Fast coef → ~30% faster.
- **`bi.atb`** (`BTL_INFO.cs:15`) is the per-tick gate: a unit is skipped in the fill loop when
  `cur.hp == 0 || sel_mode != 0 || bi.atb == 0` — `HonoluluBattleMain.cs:447`.

### 2.2 `at_coef` is the *global time-dilation knob* — the key insight

`at_coef` does not just fill the gauge. The **same** value decrements status **durations**
(`btl_stat.cs:537`), **DoT/HoT tick** counters (`btl_stat.cs:307`), and Jump/Trance countdowns
(`× ATBTickCount`). So Haste literally makes your own Poison tick faster and your buffs expire sooner.
**Every periodic effect in FF9 is measured in ATB-fill units, not wall-clock.** This is the memory's
GRANULARITY LAW at the engine level: any custom time control automatically ripples through the whole status
system — a design opportunity *and* a test burden.

### 2.3 The latent crash boundary (Dexterity ≥ 60)

If effective Dexterity ≥ 60, `max.at ≤ 0`, and the battle-start seed `Comn.random16() % btl.max.at`
(`btl_init.cs:437,500`) divides by zero/negative. The default `SpeedStatFormula = Min(50, …)` is the
guardrail. **Any mod that raises the Speed cap past ~59 breaks the ATB.** Keep effective Speed < 60.

---

## 3. The two "mode" systems (do not conflate) + the gates

There are two independent mode systems, plus a fill-rate multiplier. All three are data-config.

| System | Field | Values | Gate | What it changes |
|---|---|---|---|---|
| **ATB Active/Wait** | `cfg.atb` (default 1 = Wait) — `FF9CFG.cs:12,34` | Active / Wait | `IsNativeEnableAtb()` — `BattleHUD.Public.cs:743` | Wait = **all** gauges freeze while any player has a sub-menu open; Active = never pauses |
| **Memoria "ATB Mode"** | `[Battle] Speed` (default 0) — `Access/Battle.cs:11,50` | 0 Default · 1 Fast · 2 Turn-based · 3–5 Simultaneous | `FF9BMenu_IsEnableAtb()` — `BattleHUD.Public.cs:723` | Turn-based (2) = freeze all while menuing *or* a command is queued; Speed ≥ 3 = **concurrent command execution** (`next_cmd_delay`, `cmd_delay_max=10`, `btl_cmd.cs:481-486`) |
| **Battle Speed (fill rate)** | `cfg.btl_speed` (default 1) — `FF9CFG.cs:16,38` | Slow/Normal/Fast → coef 8/10/14 | `GetATBCoef()` — `btl_para.cs:66` | Direct ×0.8 / ×1.0 / ×1.4 on the per-tick increment |

`[Hacks] BattleSpeed` folds in as `max([Battle].Speed, [Hacks].BattleSpeed)` — `Access/Battle.cs:52`.
Both mode gates ultimately decide whether `ProcessActiveTime` advances a unit's gauge this tick: the loop
runs only if `IsNativeEnableAtb()` (`HonoluluBattleMain.cs:411`), and each increment is gated by
`advanceAtb = FF9BMenu_IsEnableAtb()` (`:442`).

### 3.1 Reset timing — turns are paced by *animation*, not the gauge

The gauge resets at **`FinishCommand`** (`btl_cmd.cs:1409`), *after* the action's `btlseq` animation
completes — not at command-select. A running command sits in `CMD_MODE_LOOP` until it leaves
`UnifiedBattleSequencer.runningActions` (`btl_cmd.cs:1427-1431`), and (in Speed < 3) the next command can't
dequeue while `cur_cmd != null` (`btl_cmd.cs:478`). **So the raw17 `btlseq` sequence length sets the floor
on turn cadence** — and the kit now has a full seq codec (`seqasm.py`/`seqauthor.py`/`seqcodec.py`), so
animation-pacing is authorable (this supersedes the "raw17 deferred" note in older memory).

Reset carries overflow when `[Battle] KeepRestTimeInBattle` (default **true**, `Access/Battle.cs:69`):
`cur.at = max(0, cur.at − max.at)` instead of hard-zero (`btl_cmd.cs:1411-1414`) — a fast unit banks its
overshoot toward its next turn.

---

## 4. Levers you already have (no engine rebuild)

| Lever | Where | Effect | Tier |
|---|---|---|---|
| `[Battle] Speed` / `[Hacks] BattleSpeed` | ini | ATB mode: Default/Fast/Turn-based/Simultaneous | 0 |
| `cfg.btl_speed` (8/10/14) | in-game slider | Global fill-rate ×0.8/×1.0/×1.4 | 0 |
| `cfg.atb` | in-game | Active vs Wait | 0 |
| `[Battle] KeepRestTimeInBattle` | ini | Overflow-carry vs clamp-reset | 0 |
| `[Battle] SpeedStatFormula` (default `Min(50, …)`) | ini (**NCalc**) | Redefine the Dexterity→gauge-length curve; the cap that prevents the §2.3 crash | 0 |
| `[Battle] StatusTickFormula` / `StatusDurationFormula` / `TranceDecreaseFormula` | ini (**NCalc**) | DoT cadence, buff durations, trance drain | 0 |
| `[Cheats] SpeedMode` / `SpeedFactor` (×3) | ini | Fast-forward the *whole* battle clock (FPSManager runs the loop N×, `FPSManager.cs:95`, `SettingsState.cs:319`) | 0 |
| Per-character Speed stat | BaseStats.csv (kit `[[character]]`) | Per-unit gauge length | 1 |
| **Enemy AI gauge writes** | `.eb` (kit `[[scene.ai_*]]`) | **Read/write any addressable unit's `cur.at`/`max.at`** — see §5.3 | 1 |
| Status-mask membership | `DictionaryPatch.txt` `BattleStatus …` — `DataPatchers.cs:346` | Enrol a status into `StopAtb`/`OprCount`/`ContiCount`/`PreventATBConfirm` | 1 |
| Custom status behavior | `[StatusScript]` (kit `[[status]]`) | `OnATB` (auto-act at full), `OnOpr` (DoT), `SetupATBCoef` (custom haste/slow) | 2 |

The **booster** shortcuts (runtime toggles, defaults from `[Cheats]`): `IsBoosterButtonActive[0]` =
BattleAssistance (`SetATBFull` slams `cur.at = max.at` each frame, `SettingsState.cs:270`), `[1]` =
FastForward, `[3]` = Attack9999, `[4]` = NoRandomEncounter, `[7]` = MasterSkill.

---

## 5. Statuses & Trance — the timing layer

### 5.1 Timing statuses

- **Haste / Slow** rescale `at_coef`: Haste `GetATBCoef() * 3 / 2` (×1.5), Slow `* 2 / 3` (×0.667) —
  `HasteStatusScript.cs:19`, `SlowStatusScript.cs:19`; mutually exclusive (applying one strips the other).
  They compose with `cfg.btl_speed` because the base is re-read from `GetATBCoef()`.
- **Freeze the gauge = a static bitmask, not script code.** `BattleStatusConst.StopAtb =
  Petrify | Death | Stop | Jump` (`BattleStatus.cs:133`) → on apply `bi.atb = 0` (`btl_stat.cs:98`),
  re-pinned each loop (`btl_stat.cs:282`). Petrify additionally hard-zeroes `cur.at`
  (`PetrifyStatusScript.cs:19`).
- **Fill-but-can't-act:** `PreventATBConfirm = Venom | Sleep | Freeze` (`BattleStatus.cs:151`) — the gauge
  fills but a full gauge can't be confirmed into a turn (`HonoluluBattleMain.cs:483,489,497`). `Freeze`/`Sleep`
  scripts are empty stubs; all behavior is mask-driven.

### 5.2 The mask trick — custom time-statuses with **no engine rebuild**

The static masks that gate the gauge are **runtime-mutable via a `DictionaryPatch.txt` `BattleStatus`
directive** (`DataPatchers.cs:346-367` → `BattleStatusConst.Update()` `:652`). Combine two data levers:

- **Tier 2** — a `[StatusScript]` (custom ids 33–63 = `CustomStatus1..31`, `BattleStatusId.cs:39`) supplies
  the *behavior*: e.g. `btl_para.SetupATBCoef(u, GetATBCoef()*2)` for super-haste, or `CurrentAtb = 0` for a
  stun, or `IOprStatusScript.OnOpr` for a custom DoT.
- **Tier 1** — a `DictionaryPatch` line enrols the status into the gating lane:
  ```
  BattleStatus StopAtb    Add CustomStatus1     # freeze this custom status' gauge
  BattleStatus OprCount   Add CustomStatus2     # give it periodic OnOpr ticks
  BattleStatus ContiCount Add CustomStatus2     # give it an auto-decrementing duration
  ```

This makes "a new status that freezes / slows / DoTs the ATB" **fully authorable off a stock engine**.
Relevant masks: `StopAtb`, `PreventATBConfirm`, `OprCount = Venom|Poison|Regen|GradualPetrify|Doom`
(`BattleStatus.cs:124`, gates `OnOpr` at `btl_stat.cs:294`), `ContiCount` (`:123`), `CannotAct`, `CmdCancel`.

### 5.3 Enemy-AI gauge writes (the standout Tier-1 lever) — **no DLL**

The enemy-AI script accessor (`btl_scrp.cs`) reads and writes the ATB gauge of any addressable unit:

| Member | Op | Line |
|---|---|---|
| `max.at` | read | `btl_scrp.cs:213` (case 39) |
| `cur.at` | read | `btl_scrp.cs:216` (case 40) |
| `cur.at` | **write** | `btl_scrp.cs:457` (case 40 set) |
| fill + queue a command | write | `btl_scrp.cs:564` (case 78 — the scripted-summon idiom: `cur.at = max.at; sel_mode = 1; SetCommand(...)`) |

So an enemy AI branch can **drain a targeted player's gauge** (`cur.at = 0`), **self-haste / instant-ready**
(`cur.at = max.at`), or **gauge-lock** a target. Real boss AI uses these (the Ozma special-case guards the
write on Speed 1/2 maps 57/211, `btl_scrp.cs:455`). This rides the kit's **existing declarative AI stack**
(`[[scene.ai_function]]`/`ai_insert`/`ai_phase`; `cmdasm`/`exprasm` already round-trip `B_MEMBER` set/get) —
it needs only a small kit addition: a `cur.at`/`max.at` naming in the disassembler and a `SetBattleData(40,…)`
emitter in `aiauthor`. **Highest-leverage, lowest-cost ATB control available, and in-game-provable today on
the existing `bt_goblin` bench.**

### 5.4 Trance — a separate byte, calculator-owned (not `ProcessActiveTime`)

`btl.trance` is a `Byte` (max 255, gate `bi.t_gauge`, `BattleUnit.cs:201-207`). It **fills on damage taken**:
`TranceIncrease = Comn.random16() % Target.Will` (`BattleCalculator.cs:177`), applied `Target.Trance += …`
(`SBattleCalculator.cs:358`); at 255 → auto-`Trance` status (suppressible by `[Battle] NoAutoTrance`,
`SBattleCalculator.cs:367`). **Drains on act:** `(300 − Level) / Will * 10` per finished command
(`btl_cmd.cs:1295`). The `TranceStatusScript` does **not** manage the gauge (`TranceStatusScript.cs:8-9`
warns it can't be recycled). Tunable only via NCalc config (`TranceDecreaseFormula`, the `TranceIncrease`
ability param) or AI opcode 148 (`btl_scrp.cs:690`), **not** a status script.

---

## 6. The hook opportunity map (for the eventual Tier-3 work)

### 6.1 The 10 `IOverload*` hooks — none touches the gauge

`Memoria/Battle/Scripts/IOverloadableMethod.cs` defines 10 interfaces; call sites (`GetOverloadedMethod`):

| Interface | Call site |
|---|---|
| `UnitCheckPoint` (LowHP/UI) | `btl_para.cs:98` |
| `PlayerUI` | `FF9UIDataTool.cs:107` |
| `OnBattleInit` | `battle.cs:545` |
| `OnBattleScriptStart` | `SBattleCalculator.cs:63` |
| `OnBattleScriptEnd` | `SBattleCalculator.cs:323` |
| `OnCommandRun` | `btl_cmd.cs:509` |
| `OnGameOver` | `btl_sys.cs:87` |
| `OnFlee` | `battle.cs:447` |
| `DamageModifier` (3 methods) | `BattleCalculator.cs:154` |
| `VABattleScript` | `BattleVoice.cs:18` |

**Confirmed: none is invoked from the ATB fill loop; none reads/writes `cur.at`/`max.at`/`at_coef`.** Closest:
`OnCommandRun` (fires *after* a gauge fills and a turn starts) and `UnitCheckPoint` (HP→status colors only).
The base `Memoria.Scripts.dll` implements **none** of the 10 (all slots free).

**Adding a new `IOverload*` interface is an engine edit, not a mod-DLL change** — it must be declared in
`IOverloadableMethod.cs` **and** whitelisted in `ScriptsLoader.ProcessType` (`:345-364`).

### 6.2 The Scripts-DLL status timing hooks (available today)

- `IAutoAttackStatusScript.OnATB()` — fires **at gauge-full** (players `HonoluluBattleMain.cs:509`, enemies
  `EventEngine.DoEventCode.cs:1224`), but only for a unit carrying such a status (Berserk/Confuse). Not per-increment.
- `IOprStatusScript.OnOpr()` — the per-tick DoT hook, dispatched `btl_stat.cs:300`, gated by the `OprCount`
  mask (`:294`).

Neither intercepts an arbitrary unit's increment; that's Tier 3.

### 6.3 Exact splice points for a hypothetical engine ATB hook

| Granularity | Splice point | Signature idea |
|---|---|---|
| **Per-unit, per-tick** (finest) | `HonoluluBattleMain.cs:461` — `current.at += (Int16)(at_coef * 4)` | `OnAtbTick(BattleUnit u, ref Int32 increment)` — has the unit, `cur.at`, `max.at`, `at_coef` |
| **Gauge-full / turn-ready** | `HonoluluBattleMain.cs:509` (player) / `:531` (enemy) | `OnAtbFull(BattleUnit u)` — same site as the stock `OnATB` status hook |
| **Global pause (allow/freeze all)** | `BattleHUD.Public.cs:743` — `IsNativeEnableAtb()` | already the site **s37 patches** for co-op menu-freeze — the working template |
| **Turn arbitration** | `btl_cmd.cs:428` — `GetFirstCommandReadyToDequeue` | initiative tiers, interrupts, overflow-extra-turn |

Delivered through the kit's existing **Overload one-hub** (`battle/overload.py`): a static feature class + one
registry entry, composed into the regenerated `0000_OverloadHub.cs`. The engine hook itself is one new
`sNN-atb-hook.patch` against `6b8bb2d5`.

---

## 7. Design catalog — how far can it be pushed

### 7.1 Tier 0–1 (data only, no engine rebuild) — larger than it looks

- **Global pacing overhauls.** Turn-based + slow fill = a deliberate, tactical FF9; Simultaneous (Speed 5) +
  Fast = a frantic all-acting-at-once FF9. Pure ini.
- **Reshape the speed curve** via `SpeedStatFormula` (NCalc) — make Speed matter far more, flatten it, or
  gate it on level; keep the `Min(<60,…)` cap.
- **Custom DoT/regen cadence & buff durations** via `StatusTickFormula`/`StatusDurationFormula`.
- **★ Enemy-side ATB warfare** authored in the AI `.eb` you already compile (§5.3): gauge-drain "time mage"
  enemies, self-haste bosses, gauge-lock stalls.
- **★ Custom time-statuses** via the §5.2 mask trick: Stop/Slow/Haste/DoT variants at custom ids off a stock
  engine.

### 7.2 Tier 2 (Scripts-DLL) — behavior at gauge-full or on-status-tick

- `OnATB` — "at full gauge, do X instead of opening the menu."
- `OnOpr` — custom Poison/Regen/Doom-style countdowns.
- Cannot intercept the increment, scale an arbitrary unit's gauge, or add a new battle-loop hook.

### 7.3 Tier 3 (engine rebuild) — the endgame of detailed control

- **`OnAtbTick`** (§6.3) → declarative conditional/aura/momentum haste (fill faster below 25% HP; a unit
  slows all enemies' gauges; fill scales with combo/kills), row/position-based speed, elemental "time" resonance.
- **New gauges on the same clock** — a **stagger/break gauge**, proper **charge-time (cast-delay)** systems (a
  second gauge that fills after command-select before the spell fires), or **cooldowns**. ⚠ Heed the
  serialization law (`project-ff9-memoria-build`): add *methods* and `[NonSerialized]`/private runtime fields
  freely, but **never a serialized field to a baked MonoBehaviour**.
- **Rework turn arbitration** (`GetFirstCommandReadyToDequeue`) — initiative tiers, interrupt/counter priority,
  overflow-extra-turn.

---

## 8. Sequencing & the co-op interaction — **read before starting engine work**

**Decision (2026-07-14): the ATB gameplay hooks are deferred behind co-op Phase 2 (the authoritative-host
diorama). Do co-op first. Do not build ATB hooks first.** The reasoning:

1. **Co-op's ATB requirements are already solved.** The battle-co-op feasibility study concluded
   *"ATB MODES: NO restriction needed"* — the battle exists only on the host, only the host's ATB settings
   matter, and the Fast/TB catch-up loop polls `FF9BMenu_IsEnableAtb` per iteration and stops on a filled
   player gauge (can't skip a guest turn). The one real gap (Wait/TB hosts freezing while a *remote* guest is
   menuing) was closed in **s37**: `NetSyncBattle.RemoteMenuOpen` OR'd into `IsNativeEnableAtb()` (WAIT) and
   the TB `isMenuing` check — built and two-machine-proven. The ATB gameplay hooks (§7) are content features;
   nothing in Phase 2 consumes them.
2. **The diorama deliberately avoids the ATB simulation.** Per the co-op pivot
   (`project-ff9-multiplayer-injector`, 2026-07-13), Phase 2 is the **battle-puppet**: boot the host's
   authoritative battle on the guest's screen with **AI/ATB suppressed via `isDebug`**, driven by the existing
   B0 state stream, **never re-simulated** (combat RNG is one global unseeded `UnityEngine.Random`, so any
   re-sim diverges on the first draw). The guest *displays* the host's ATB (already in the B0 frame as ATB%),
   it does not compute it. A per-tick ATB hook does nothing for rendering a mirror.
3. **Shared, fragile code region → doing ATB first maximizes churn for no benefit.** Both live in
   `HonoluluBattleMain.ProcessActiveTime`, `BattleHUD.Public/Unity/Scene/.cs`, and the command queue. s37
   already did heavy surgery there (freeze gates, four HUD skip-guard sites, `SendNetCommand`); Phase 2 edits
   the same region again. Landing a large ATB-hook patch (s38) first, then a Phase-2 patch that also touches
   `ProcessActiveTime`/`BattleHUD`, means maintaining two overlapping hunks in the most regression-prone part
   of the engine — the overlap-vs-drift pain from `project-ff9-memoria-conflict-forensics`.

**When ATB *would* become co-op-relevant:** only if the shelved **B2** rung is revived — the guest as a
*genuine authoritative battler with their own gauge* (a real 5th slot / slot-replacement). The pivot shelved
B2 precisely because the 5th-party-slot hard wall (`PLAYER[4]`, 8-bit `btl_id`, `btl_data[8]`) and the
RNG-divergence wall make an independent guest battler a research project. If B2 ever returns, ATB engine work
becomes part of *it*, not a prerequisite built in advance.

---

## 9. Recommended build order + kit-feature shape

1. **Finish co-op Phase 2 (the diorama) + the empty-command fix.** (Its own track — see
   `project-ff9-multiplayer-injector`.)
2. **`[[scene.ai]]` ATB opcodes (Tier 1, cheapest, biggest payoff).** Teach `battleai`/`aiauthor` the
   `cur.at`/`max.at` member set/get (§5.3). No DLL; in-game-provable on `bt_goblin`. Gauge-manipulating bosses
   become declarative.
3. **Custom time-statuses (Tier 1+2).** A `[[status]]` extension pairing a `[StatusScript]` behavior with the
   `DictionaryPatch BattleStatus … Add` mask enrollment (§5.2).
4. **An `[atb]` / `[timing]` config block (Tier 0).** A declarative `field.toml`/campaign surface that writes
   the ini levers (`Speed`, `KeepRestTimeInBattle`, `SpeedStatFormula`, tick/duration formulas) as authored
   presets — "tactical mode," "action mode," "slow-burn boss."
5. **The `OnAtbTick` engine hook + kit Overload feature (Tier 3).** The real per-unit gauge control, delivered
   through the existing Overload hub, following the s37 `IsNativeEnableAtb` template. **If pursued soon,
   co-locate it with a battle-region rebuild rather than a separate earlier one** — once Phase 2 has settled
   the battle-loop/BattleHUD layout and you're already re-testing the whole battle path, dropping in the seam
   is cheap and gets tested alongside co-op (one rebuild, one playtest pass, one set of hunks).

---

## 10. Constants, clamps & key files

**Hardcoded (engine-rebuild-only) targets:** `GetMaxATB` formula `(60 − Dex) × 40 << 2` (`btl_para.cs:58`);
per-tick `at_coef × 4` (`HonoluluBattleMain.cs:461`); speed coefficients `8/10/14` (`btl_para.cs:69-73`);
Haste `×3/2` / Slow `×2/3` (ship as replaceable default StatusScripts); `FF9PLAY_DEF_AT = 10`
(`ff9play.cs:49`); battle-start seeding (`btl_init.cs:432-437,500`).

**Integer widths / clamps:** `cur.at`/`max.at` = `Int16`; `at_coef` = `SByte` (Haste×Fast = 21 is safe; very
large custom coefs overflow); `trance` = `Byte`. **`max.at` must stay > 0 — keep effective Speed < 60.**

**Key files** (all under `Assembly-CSharp/`, pinned `6b8bb2d5`):

- `Global/btl_para.cs` — `GetMaxATB` (:56), `GetATBCoef` (:66), `SetupATBCoef` (:61).
- `Global/Honolulu/HonoluluBattleMain.cs` — `ProcessActiveTime` (:415-564, fill at :461), gauge-full (:509/:531).
- `Global/POINTS.cs` / `Global/BTL_INFO.cs` / `Global/BTL_DATA.cs` — gauge storage.
- `Global/btl_init.cs` — battle-start ATB seeding (:300-311, 401-437, 498-506).
- `Global/battle/BattleHUD/BattleHUD.Public.cs` — `FF9BMenu_IsEnableAtb` (:723), `IsNativeEnableAtb` (:743).
- `Global/btl_cmd.cs` — command queue (`SetCommand` :153, `GetFirstCommandReadyToDequeue` :428, `FinishCommand`/reset :1409).
- `Global/btl_stat.cs` — status tick/duration decrements (:294 OprCount gate, :307/:537 `at_coef` decrements).
- `Global/btl_scrp.cs` — AI-script gauge read/write (cases 39/40 :213-216/:457, case 78 :564).
- `Memoria/Scripts/DefaultStatus/{Haste,Slow,Stop,Petrify,Trance}StatusScript.cs` — timing statuses.
- `Memoria/Battle/Scripts/IOverloadableMethod.cs` + `Memoria/Scripts/ScriptsLoader.cs` (:345-364) — the hook channel.
- `Memoria/Data/Battle/BattleStatus.cs` — the timing masks (`StopAtb` :133, `PreventATBConfirm` :151, `OprCount` :124, `ContiCount` :123).
- `Memoria/Configuration/{Access/Battle.cs, Structure/BattleSection.cs, Memoria.ini}` — the `[Battle]` config levers.
