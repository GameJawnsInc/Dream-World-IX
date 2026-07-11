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

**What's left:** two more candidate features — **death rules** (`OnGameOver`) and **Trance/low-HP**
(`UnitCheckPoint`). Both need one shared hub extension first (a **returning-hook mode**, below). Nothing is
blocked; it's greenfield with a clear plan.

`master` is ~72 commits ahead of `origin` — **the user handles pushes.** Do not push.

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

### 0. The prerequisite: a RETURNING-HOOK hub mode

The current hub only emits **void** methods that splice void feature calls (any number, composed). The next
two features hook **returning** interfaces (`OnGameOver`→bool, `UnitCheckPoint`→BattleStatus). A returning
hook is inherently **single-owner** (two features can't both decide game-over). So extend `overload.py`:

- Add a hook-template variant that emits `public <Ret> <Method>(<args>) { <verbatim-default-or>
  return <TheOneFeature>.<Method>(<args>); }`. When **no** feature owns the interface, the method body is the
  **verbatim engine default** (so the hub is transparent); when one owns it, the method returns the feature's
  verdict.
- Enforce single-owner in the registry/render (error if two features claim a returning hook).
- The feature's static method returns the verdict AND does its effect. It must reproduce any part of the
  default it wants to keep (returning `true` on OnGameOver skips the engine's game-over tail entirely — see
  below).

This is the one real design step. Keep it minimal — a second template shape + an owner check. Mirror the void
path's tests in `tests/test_overload.py`.

### 1. Death rules — `[deathrules]` / similar, hook `OnGameOver` (btl_sys.cs:87)

Fires when the party is downed. Returning `true` → engine does `return;` and **skips its game-over tail**
(`btl_sys.cs:118-124`: sets `SEQ_MENU_OFF_DEFEAT`, "Annihilated" message, disables menu, `KillAllCommand`).
Returning `false` → game over proceeds.

**The default you displace is the Eiko Rebirth Flame auto-revive** (btl_sys.cs:95-116). If a feature owns
this interface it REPLACES that block — so to keep Eiko working for anyone carrying her, transcribe it
verbatim into the feature (or into the hub's no-owner default; since a returning hook is override-only, the
feature itself should reproduce Eiko unless the design intentionally removes it). **Read btl_sys.cs:87-124
firsthand before writing anything** — the exact structure (loop for an Eiko unit, `NoRebirthFlame` check,
`PhoenixPinion` count vs `random8()`, `SetCommand(SysLastPhoenix, RebirthFlame)`) matters.

Design options (a user gameplay call — ask before building): a one-time party revive (roguelike "second
wind"), or return-to-World-Hub instead of a hard Game Over (`[[flag]]`-gated). Probably declarative
`[deathrules]` (a TOML shape like the other features), not a CLI tool — it's shipped content.

### 2. Trance / low-HP — hook `UnitCheckPoint` (btl_para.cs:98), returns `BattleStatus`

Least-scoped; the survey note ("LowHP status/UI colors") is thin. **Do its own `btl_para.cs:98` source-dive
first** to learn what the returned `BattleStatus` controls before designing. Also a returning hook → uses the
same hub extension as #1.

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

**Playtest fields used:** `scratch/difficulty_test.field.toml`, `scratch/rebalance_test.field.toml`
(2×/0.5×, Evil Forest scene 67, flag-gate lines to uncomment).

---

## Key files & references

- `ff9mapkit/ff9mapkit/battle/overload.py` — the hub, registry, flag gate, collision gate, compile paths.
- `ff9mapkit/ff9mapkit/battle/difficulty.py` / `rebalance.py` — the two declarative features (mirror these).
- `ff9mapkit/ff9mapkit/battle/telemetry.py` — the observer feature + JSONL reader/`--report`.
- `ff9mapkit/ff9mapkit/build.py` — `_emit_scripts` (collect+write+compile), `validate()`, the lint `csc` gate.
- `tools/deploy_field.py` — the reversible deploy + generic stickiness + the DLL-lock / backups fixes.
- `ff9mapkit/tests/test_overload.py`, `test_telemetry.py` — copy these patterns for a new feature.
- Docs: `ff9mapkit/docs/SCRIPTS_DLL.md` §12, `ff9mapkit/docs/FORMAT.md` (`[difficulty]`/`[rebalance]`).
- Memory (original machine, auto-loads): `project-ff9-overload-hooks.md`, `project-ff9-scripts-dll.md`.
- Engine source (read-only clone): `C:\gd\FFIX\Memoria\Assembly-CSharp\…` (btl_sys.cs, btl_para.cs,
  SBattleCalculator.cs, ScriptsLoader.cs, IOverloadableMethod.cs).
