# HANDOFF — the Overload battle-hook channel (`ff9mapkit`)

> **What this is:** a self-contained continuation brief for the **Overload** plugin channel of the FF9
> Scripts-DLL. Point a fresh Claude session at this file to pick up exactly where the work paused. It is
> committed to the repo on purpose, so it travels via git to any machine/account that pulls `master`.
> Written 2026-07-11. The live deep-dive (with more engine citations) is the project-memory file
> `project-ff9-overload-hooks.md` (auto-loads on the original machine); the user docs are
> [`ff9mapkit/docs/SCRIPTS_DLL.md`](ff9mapkit/docs/SCRIPTS_DLL.md) §12.

## TL;DR

The Overload channel lets a mod-owned `Memoria.Scripts.<Mod>.dll` implement Memoria's `IOverload*` battle
hooks with **zero engine rebuild**. The architecture + first three features are **built, merged to `master`,
and in-game proven**:

| Feature | Hook | Kind | Status |
|---|---|---|---|
| **the hub** (`overload.py`) | — | one class implementing all claimed interfaces | ★ proven |
| **battle telemetry** (`telemetry.py`, CLI `battle-telemetry`) | OnBattleInit/Start/DamageFinalChanges/End | observer (dev tool) | ★ proven |
| **`[difficulty]`** (`difficulty.py`) | OnBattleInit | mutator — enemy HP/Str/Mgc scaling | ★★ proven, both variants |
| **`[rebalance]`** (`rebalance.py`) | OnDamageFinalChanges | mutator — player/enemy HP-damage × | ★★ proven, both variants |
| **`[deathrules]`** (`deathrules.py`) | OnGameOver (+OnBattleInit reset) | RETURNING single-owner — game-over verdict | ★ in-game proven 2026-07-11 (always-on second wind) |

**The returning-hook hub mode is BUILT** (2026-07-11): `RETURNING_HOOKS` in `overload.py` — the hub emits
`try { return <owner-expr>; } catch { } return <fail-safe>;`, single-owner enforced in `render_hub`
(ScriptCompileError names the claimants), registry value = an EXPRESSION (no `;`) for a returning hook. New
`flag_expr_cs` (the gate as a testable condition — for features whose VANILLA path must still run when the
flag is clear). The whole tree (hub + all 4 features) compiles against the live engine
(`test_tree_compiles_against_live_engine`, ran + passed).

**What's left:** the short-anim playtest (below); the **Trance/low-HP** feature (`UnitCheckPoint` — dive
DONE, see below); optionally a warp-on-defeat `[deathrules]` mode (a user design call).

### The SHORT-ANIMATION second wind — BUILT 2026-07-11, awaiting playtest

The user-flagged follow-up ("the full Rebirth Flame summon could get obnoxious in an authored context") is
built: **`animation = "short"`** + **`revive_hp`** (fraction of max, default 0.2, floor 1 HP). The dive
found the engine's OWN short revive — the death-changer status recipe:

- `AutoLifeStatusScript.OnDeath` (Memoria/Scripts/DefaultStatus/): revive = `Target.CurrentHp = N` +
  `btl_stat.RemoveStatus(Target, BattleStatusId.Death)`. **No VFX, no summon** — Auto-Life's whole visual
  is the unit standing up.
- `DeathStatusScript.Remove` (triggered by that RemoveStatus): ALL the un-death bookkeeping — `die_seq = 0`,
  clears `death_f`/`stop_anim`/`cmd_idle`/`escape_key`/`killer_track`, restarts texanims when the unit is in
  MP_DISABLE/MP_DOWN_DISABLE motion. This is why the direct revive is safe: the status system owns the state.
- `btl_mot.DecidePlayerDieSequence`'s cancel branch (btl_mot.cs:449-457): after a death-changer fires it
  calls `btl_mot.SetDefaultIdle(btl)` (stand back up) + `FF9StateSystem.Settings.SetHPFull()` (booster).
- Timing is clean: when `OnGameOver` fires, every player is BattleEndFull and every Death-status unit has
  `die_seq == 6` (CheckBattlePhase's own loop guarantees it) — the same state a mid-battle Phoenix Down
  target is in.
- `SysReraise` (the old Auto-Life command) is DUMMIED (`btl_cmd.cs:1092 "Unused anymore"`) — dead end; the
  status-script path above is the modern mechanism.

The feature composes exactly those verbatim pieces per dead player (petrify stays, like the Phoenix ability;
nobody revivable → vanilla defeat). `animation = "full"` still emits the proven Phoenix variant unchanged.
Both variants compile against the live engine (the money test compiles the tree twice).

`master` is ahead of `origin` — **the user handles pushes.** Do not push.

---

## The architecture (enough to be self-contained)

**Engine mechanism** (pinned Memoria `6b8bb2d5`, `Memoria/Scripts/ScriptsLoader.cs:343-365`): the loader
registers any mod-DLL class implementing an `IOverload*` interface into a `Dictionary<Type,Type>` **keyed by
interface**. At each call site the engine does `GetOverloadedMethod(typeof(I…))`; **null → the vanilla inline
default runs**, non-null → a fresh instance (parameterless ctor) replaces it. So an implementation is
**override-only**: it must transcribe whatever default it displaces. The base `Memoria.Scripts.dll` implements
none of the 10 → all free. Registration is **one implementer per interface per DLL** (last-wins, `GetTypes()`
order unspecified → a silent coin flip if two classes claim one interface); first-wins across stacked mod
folders (silently).

**The one-hub design** (`ff9mapkit/ff9mapkit/battle/overload.py`): because of that last-wins rule, the kit
emits exactly **one** class — `Scripts/Sources/Overload/0000_OverloadHub.cs`, regenerated every compile — as
the sole `IOverload*` implementer. Features are **plain static classes** (no interface tokens) that the hub
calls at hand-authored splice points. A `FEATURES` registry lists each: `{name, dir, file, order, live_owned,
hooks, render}`. `hooks` maps a hook-method → the C# statement the hub splices. The hub composes multiple
features per hook **in `order`: mutators (low) before observers (high)** — so telemetry logs the
already-scaled numbers. Where a hook has an engine default, the hub carries it **verbatim** (moved from the
in-game-proven telemetry source).

- **Adding a void-splice feature = a registry entry + a static-class renderer + splice statements.** The hub
  does the interface plumbing.
- **Shared flag gate:** `overload.flag_gate_cs(flag_index, label=…)` emits the `gEventGlobal`-bit
  early-return both `[difficulty]` and `[rebalance]` use.
- **Collision gate:** `check_interface_collisions` refuses a hand-dropped `.cs` that claims an interface the
  hub (or another source) already owns.
- **The one compile path:** everything funnels through `overload.compile_tree` / `compile_live` (regen
  feature sources + hub → gate → compile ALL sources → `Memoria.Scripts.<Mod>.dll`). Empty tree deletes the
  DLL. Build wiring is `build._emit_scripts`.
- **Deploy stickiness (generic):** `tools/deploy_field.py` replaces build-owned Sources dirs
  (`Battle`/`Difficulty`/`Rebalance`/`Overload`) and, if any **live-owned** feature (telemetry) is present,
  recompiles the live DLL from all live sources via `overload.compile_live`.

### Laws learned (don't relitigate)

- **Mutators before observers** (hub `order`): a scaler must run before telemetry logs, else the log lies.
- **The 9999 damage cap is not ours to break.** `OnDamageFinalChanges` fires *pre-cap*; the engine clamps to
  `MaxDamageLimit` (9999) right after (`SBattleCalculator.cs:210`) unless the player set
  `[Battle] BreakDamageLimit = 1` in `Memoria.ini`. So a `[rebalance]` multiplier reads through below 9999,
  clamps above it. The kit **does not** force that global engine config from a mod hook — it documents it.
- **Only pure HP damage** scales in rebalance: guard `HpAlteration` set **and** `HpRecovery` clear (heal /
  recover / MP left alone).
- **THE GRANULARITY LAW** (discovered by playtest): a flag-gated feature's toggle latency = its hook's fire
  cadence. `[rebalance]` gates at damage time (**per hit** → F6→Flags flips it live *mid-battle*);
  `[difficulty]` gates at battle init (**per battle** → next battle only). Same gate, different granularity
  from where the hook sits. Pick the block whose cadence matches the effect.

---

## The 10 hooks (call sites + defaults)

`Memoria/Battle/Scripts/IOverloadableMethod.cs` defines them. Void hooks compose (splice); **returning hooks
can have only ONE owner** (see the extension below).

| Interface | Site | Returns | Default to transcribe |
|---|---|---|---|
| `IOverloadOnBattleInitScript` | battle.cs:545 | void | **none** (pure addition) — used by difficulty + telemetry |
| `IOverloadDamageModifierScript` (`OnDamageFinalChanges` + 2) | SBattleCalculator.cs:200 | void | reflect multiplier (+ ×1.5 stack / Attack=1) — used by rebalance + telemetry |
| `IOverloadOnBattleScriptStartScript` | SBattleCalculator.cs:63 | **bool** (true=skip) | backstab/weapon-element/kill-frozen — used by telemetry (returns false) |
| `IOverloadOnBattleScriptEndScript` | SBattleCalculator.cs:323 | void | none (⚠ enemy-target only — early-returns for player targets) |
| `IOverloadOnGameOverScript` | **btl_sys.cs:87** | **bool** (true=cancel) | **Eiko Rebirth Flame** — see below |
| `IOverloadUnitCheckPointScript` | **btl_para.cs:98** | **BattleStatus** | LowHP status logic (needs a source-dive) |
| `IOverloadOnCommandRunScript` | btl_cmd.cs:509 | **bool** (true=cancel) | Heat kills the actor |
| `IOverloadOnFleeScript` | battle.cs:447 | void | 10% gil loss |
| `IOverloadPlayerUIScript` | FF9UIDataTool.cs:107 | Result | menu HP/MP colors |
| `IOverloadVABattleScript` | BattleVoice.cs:18 | void | voice-acting init |

---

## NEXT WORK

### 0. ✔ DONE (2026-07-11) — the RETURNING-HOOK hub mode

Built as planned, with one deliberate deviation from the sketch: when **no** feature owns a returning
interface the hub does **not** implement it at all (the engine's inline default runs untouched — more
transparent than transcribing it), so verbatim-default transcription is the OWNING FEATURE's job. Single
owner enforced in `render_hub`; fail-safe per hook baked into the template (`OnGameOver` → `false`: a
vanilla defeat, never a canceled wipe with nobody revived = soft-lock). Tests mirror the void path
(`test_hub_deathrules_returning_hook`, `test_hub_returning_hook_is_single_owner`).

### 1. ★ IN-GAME PROVEN (2026-07-11) — `[deathrules]` on `OnGameOver` (btl_sys.cs:87)

`ff9mapkit/ff9mapkit/battle/deathrules.py` + build wiring + docs (SCRIPTS_DLL.md §12, FORMAT.md,
FEATURES.md, CHANGELOG). Knobs: `second_wind` (cancel the wipe ONCE per battle by queueing the engine's own
`SysLastPhoenix`/`RebirthFlame` on the fallen `dyingPC` + `FF9BMenu_EnableMenu(true)` — the exact vanilla
Eiko mechanism, so no hand-rolled revive state), `chance` (whole percent, roll = `Comn.random16() % 100`),
`keep_rebirth_flame` (default true — the Eiko default transcribed VERBATIM as
`VanillaRebirthFlame(state)`; false removes it), `flag` (gate; **clear = FULLY vanilla including Eiko** —
uses `flag_expr_cs` into a `ruleActive` local, NOT the shared early-return gate, because the vanilla path
must still run while the rule sleeps). Once-per-battle = a static `_secondWindUsed` reset at `OnBattleInit`;
the vanilla pending-revive guard (`CheckSpecificCommand2(SysLastPhoenix)` → keep the battle alive) runs
FIRST. Facts learned in the dive: the Eiko default's `return`s exit `CheckBattlePhase` entirely (= the
hook's `true`), and a dead unit CAN carry the queued command (vanilla queues it on the dead Eiko's
`cmd[0]`).

**★ Playtest PASSED 2026-07-11** (`scratch/deathrules_test.field.toml`, always-on variant, new game →
4003): first wipe → the Rebirth Flame summon plays → party resurrects at ~50 HP; second wipe same battle →
normal game over screen; continue → next battle → identical behavior (recharged). User: "all clear."
NOT separately playtested (mechanism-identical to ★-proven sibling gates / verbatim-transcribed code):
the `flag` round, `chance`, `keep_rebirth_flame = false` with an Eiko party. **User-flagged follow-up:**
the revive plays the FULL Rebirth Flame summon animation (vanilla `RebirthFlame` choreography — we queue
the real command, so we inherit it); fine for FF9 flavor, "could get obnoxious in an authored context" —
a short-animation knob (different revive command/ability with lighter btlseq choreography, or a minted
one) needs its own dive before promising TOML.

**Deferred design option (user gameplay call, NOT built):** warp-on-defeat (return to the World Hub / a
field instead of a hard game over). Riskier: there is no sanctioned battle-exit path from inside this hook
(would need flee/battle-end sequencing) — needs its own engine dive before promising a TOML knob.

### 2. Trance / low-HP — hook `UnitCheckPoint` (btl_para.cs:94-116) — SOURCE-DIVE DONE 2026-07-11

What the site actually is: `CheckPointDataStatus(BattleUnit)`, called from `CheckPointData` for a unit
whose HP/MP just changed. Facts:

- **`cur.hp == 0` → `BattleStatus.Death` is returned BEFORE the hook** — a feature cannot save a unit at 0
  HP from death here (death-prevention belongs elsewhere, e.g. a damage mutator).
- The **returned `BattleStatus` only matters for its `Death` bit**: the caller checks
  `(status & BattleStatus.Death) != 0` → `AlterStatus(Death)`. So a feature CAN kill a unit by returning
  Death (e.g. "doom at low HP" hardcore rules); returning `LowHP` vs `0` changes nothing at the call site.
- Everything else is SIDE EFFECTS inside the default, which an owner must reproduce: the LowHP threshold
  (`IsPlayer && CurrentHp * 6 <= MaximumHp` → add/remove `BattleStatus.LowHP` via `btl_stat.Alter/
  RemoveStatus`), the UI colors (`unit.UIColorHP` yellow/white, `UIColorMP` at `MaximumMp / 6f`).
- So the honest feature here is a **`[lowhp]`-style threshold/status feature** (change the 1/6 LowHP
  fraction, which feeds LowHP-gated SA abilities + the yellow HP color; optionally a death-at-threshold
  hardcore rule), NOT "Trance" — the Trance gauge does not live at this site. Single-owner returning hook →
  the same hub mode as `[deathrules]` (add `UnitCheckPoint` to `RETURNING_HOOKS` + a template whose
  fail-safe returns `0`... careful: the fail-safe must NOT skip the default's side effects — probably the
  feature transcribes the default and the hub fail-safe just returns `0` after a swallowed exception).
- Design is a gameplay call (what knobs are worth shipping?) — ask the user before building.

---

## The build / deploy / playtest loop (+ the gotchas that bit us)

The Scripts DLL is **version-coupled** and loads **once at the title screen**.

1. **Compile is at build/deploy time against the LIVE installed engine** (`x64/FF9_Data/Managed/`), never a
   checked-in Assembly-CSharp. Needs a C# compiler (`csc`: VS BuildTools Roslyn, or the .NET Framework one;
   `$FF9_CSC` overrides). The lint gate names any feature that needs it.
2. **Verify every engine member you emit is PUBLIC** in the pinned source *before* writing C# — grep the call
   site + members. This is why the whole tree compiled first try each time.
3. **Deploy from `master`** (`C:\gd\Dream-World-IX`), not a fresh worktree. Reason (real, cost us a scare):
   `provision.templates_present()` gates a whole byte-level test tier; a fresh worktree lacks the gitignored
   extracted templates, and *partially* populating them (e.g. copying `blank_field`+`region_template.bin` to
   make a deploy work) flips the gate True and un-skips ~230 tests that then fail with `FileNotFoundError`
   (all environmental, zero code). `master` has the full data dir — use it.
4. **Test loop:** `cd ff9mapkit` → `py -m ff9mapkit …` (cwd at the kit root shadows any installed package);
   deploy via `py tools\deploy_field.py <field.toml> --id 4003`.
5. **RELAUNCH FF9 after every DLL change** — F6 does *not* reload the Scripts DLL (it loads once at title).
6. **QUIT FF9 COMPLETELY before redeploying** — a running game memory-maps the loaded DLL, so Windows refuses
   the overwrite (surfaces as `OSError errno 22`, now caught with a clear message). The title screen still
   holds it; fully exit the process.
7. **Telemetry is the oracle.** `py -m ff9mapkit battle-telemetry FF9CustomMap` (install) → fight → read
   `<game>/ff9mk_battle_telemetry.jsonl` or `battle-telemetry --report`. Because telemetry is an observer
   ordered after mutators, it logs the *post-effect* numbers — that's how difficulty (byte-exact maxHP) and
   rebalance (out-of-vanilla-range damage) were proven. `deploy_field` auto-folds telemetry back into a fresh
   DLL (stickiness), so it stays on across deploys.
8. **`backups/` is auto-created** now (was a fresh-worktree crash). Back up
   `Memoria.Scripts.<Mod>.dll` before compiling over it if you care about the prior build.

**Playtest fields used:** `scratch/difficulty_test.field.toml`, `scratch/rebalance_test.field.toml`,
`scratch/deathrules_test.field.toml` (Evil Forest scene 67, flag-gate lines to uncomment; scratch/ is
gitignored — these live in MASTER's working tree only).

---

## Key files & references

- `ff9mapkit/ff9mapkit/battle/overload.py` — the hub, registry, RETURNING_HOOKS, flag gates, collision gate,
  compile paths.
- `ff9mapkit/ff9mapkit/battle/difficulty.py` / `rebalance.py` / `deathrules.py` — the three declarative
  features (mirror these; deathrules is the returning-hook exemplar).
- `ff9mapkit/ff9mapkit/battle/telemetry.py` — the observer feature + JSONL reader/`--report`.
- `ff9mapkit/ff9mapkit/build.py` — `_emit_scripts` (collect+write+compile), `validate()`, the lint `csc` gate.
- `tools/deploy_field.py` — the reversible deploy + generic stickiness + the DLL-lock / backups fixes.
- `ff9mapkit/tests/test_overload.py`, `test_telemetry.py` — copy these patterns for a new feature.
- Docs: `ff9mapkit/docs/SCRIPTS_DLL.md` §12, `ff9mapkit/docs/FORMAT.md` (`[difficulty]`/`[rebalance]`).
- Memory (original machine, auto-loads): `project-ff9-overload-hooks.md`, `project-ff9-scripts-dll.md`.
- Engine source (read-only clone): `C:\gd\FFIX\Memoria\Assembly-CSharp\…` (btl_sys.cs, btl_para.cs,
  SBattleCalculator.cs, ScriptsLoader.cs, IOverloadableMethod.cs).
