# SCRIPTS_DLL.md — custom battle FORMULAS with no engine rebuild (the Scripts-DLL channel)

> **Status: SHIPPED + in-game proven (2026-07-07).** A `[[playable]]` custom ability can carry
> `script = { template = "drain_hp" }` (or `{ body = "<C#>" }`) and the kit mints a genuinely new
> **battle-calc formula** — a `[BattleScript(id)]` class compiled into a **mod-owned
> `Memoria.Scripts.<Mod>.dll`** loaded *in addition to* the base engine, with **zero engine-DLL rebuild**.
> Proven in-game: Iviv's "Soul Leech" (a drain — deals damage *and* heals its caster) from one line of
> `field.toml`.
>
> **P7 — the fan-out (★ in-game proven 2026-07-07):** the *same* mod DLL also hosts **field effects** — a
> `script.field` sub-table mints a paired `[FieldAbilityScript(id)]` at the same scriptId, so a curative ability
> works both in *and* out of combat (§2). Proven: Iviv's "Lifewell" healed in battle *and* healed an ally from the
> field menu (the same ability, one DLL). And **custom status behaviours** — an ability's `status = [{template/
> body}]` mints a `[StatusScript]` for a new `CustomStatusN` ailment (revive-on-death, auto-attack, …) plus its
> `StatusData` row — are built too (offline + real-engine-compile proven, awaiting in-game; §2). Global battle
> overloads remain a scoped follow-on.
>
> Provenance: this doc is analysis + author-facing recipes only — **zero Square-Enix bytes**. The stock-donor
> formula/field templates live in `ff9mapkit/battle/scriptsource.py` (kit source: battle templates cloned from the
> install's loose `Scripts/Sources/Battle`, field templates transcribed from Memoria's MIT `SFieldCalculator` with
> the donor line cited per template); the compiled DLL is mod build-output (never committed). Deep recipe: project
> memory `project-ff9-scripts-dll`.

---

## 1. Why this exists — the data-path wall

FF9's shared abilities are data (`Actions.csv`), and the kit already reaches almost all of a spell's identity
with no code: `power` / `element` / `rate` / `mp` / `targets` / `category` / status-inflict, and even a re-point
of the `scriptId` cell to a *different existing* formula (see [BATTLE_DESIGN.md](BATTLE_DESIGN.md) §2(c)). The
`effect = "[code=...]"` channel ([`[[ability_feature]]`](BATTLE_DESIGN.md) / `AbilityFeatures.txt`) adds an NCalc
expression on top.

But some behaviours are a **formula**, not a value — and the data path structurally cannot express them:

- **drain** (deal damage AND heal the caster for the same amount),
- **%-of-max-HP** healing (share a fraction of the caster's own max HP),
- **MP drain / Osmose**,
- anything needing **sequencing, loops, branches, or engine-verb calls** (the NCalc `[code=]` channel is a
  single-pass scalar assignment — no control flow, no calc-verb calls).

Which formula an action runs is its `scriptId` (an `Actions.csv` column). The engine ships ~110 of them. A
*brand-new* formula is C#. **The Scripts-DLL channel lets you ship that C# as a per-mod plugin the engine loads
alongside its own — no `Assembly-CSharp.dll` rebuild, no version-locked engine fork.**

This is **Memoria's sanctioned additive-plugin surface**, distinct from a Tier-2 engine rebuild: it is additive,
per-mod, and blast-contained (a broken formula degrades only that mod's custom abilities).

---

## 2. The author surface — one line

A scripted formula rides on a **custom active ability** (a new `Actions.csv` row in the 192–223 band, cloned
from a stock donor and retuned) inside a `[[playable]]` character's command pool — the same
[13th-character ability kit](CUSTOM_MODELS.md) machinery that gives a character its own spells. You add one key,
`script`, to the inline ability table:

```toml
[[playable]]
name    = "Iviv"
borrow  = "vivi"        # looks like Vivi; a genuine new CharacterId
recruit = true

[playable.abilities]
menu_from = "vivi"      # clone Vivi's command menu as the starting point

[playable.abilities.command1]
name = "Spark"          # a unique minted battle command
abilities = [
  # a custom active ability whose FORMULA is minted C# -> a real drain spell:
  { name = "Soul Leech", from = "Fire", power = 40, element = ["Dark"], mp = 12,
    script = { template = "drain_hp" } },
]
```

Build + deploy that field and Iviv learns **Soul Leech**: it animates like Fire (the `from` donor it clones),
costs 12 MP, hits for a Dark-element ~40-power magic attack, **and heals Iviv for the damage dealt** — a
behaviour no `Actions.csv` edit can produce. ★ In-game proven.

**`script` is a TABLE, not a scalar — that distinction is the whole channel:**

| `script = …` | Meaning | DLL? |
|---|---|---|
| `script = { template = "drain_hp" }` | mint a NEW formula from a named template | **yes** (built for you) |
| `script = { body = "<C# Perform() body>" }` | mint a NEW formula from raw C# | **yes** (built for you) |
| `script = 16` or `script = "DrainHp"` | re-point at an EXISTING (0–191) engine formula — data only | no |

A **scalar** `script` stays an ordinary `Actions.csv` override (it re-points the row at a formula the engine
already has); only a **table** `script` mints new C#.

### Also out of combat: paired field effects (P7)

A battle formula only runs *in* combat. A curative/support ability usually needs to work from the **field menu**
too (heal an ally while walking around). Add a `field` sub-table to `script` and the kit mints a **second** plugin
— a `[FieldAbilityScript(id)]` — into the *same* DLL at the *same* scriptId, so one ability behaves in *and* out
of combat:

```toml
[playable.abilities.command1]
name = "Spark"
abilities = [
  # heals in battle (white_wind formula) AND out of combat (field_white_wind):
  { name = "Lifewell", from = "Cure", targets = "SingleAlly",
    script = { template = "white_wind", field = { template = "field_white_wind" } } },
]
```

The field effect binds on the **same `Ref.ScriptId`** the battle formula already repoints — `SFieldCalculator`
runs `[FieldAbilityScript(256)]` when the ability is used on the field, `[BattleScript(256)]` when it's used in
battle. Zero new binding, one compiled DLL.

**`script.field` requires a paired battle `script`** (template or body) — they share one minted 256-band id, so a
field-only effect isn't supported yet (a stock field scriptId would clobber a vanilla effect globally). The kit
enforces this at build/lint.

**The field templates** (each transcribed verbatim from a `SFieldCalculator.DefaultFieldScript` arm — point
`targets` at an ally):

| `field` template | Cloned from | What it does |
|---|---|---|
| `field_heal_hp` | Magic Recovery | heal the target's HP (spell heal) |
| `field_white_wind` | White Wind | heal a fraction of the *caster's* max HP (pairs with the battle `white_wind`) |
| `field_chakra` | Chakra | heal HP + MP by a % of the target's max |
| `field_cure_status` | Magic Cure Status | cure the ability's status set off the target |
| `field_revive` | Revive | revive a KO'd ally |

Or a raw `field = { body = "<C# Apply(FieldCalculator v) body>" }` — the field calculator `v` exposes
`v.CanBeHealed(...)`, `v.HealHp()`, `v.TargetRecoverHp` / `TargetRecoverMp`, `v.CureActionStatuses()`,
`v.ReviveSpell()`, `v.Action.Ref.Power`, `v.Caster` / `v.Target` (see Memoria's `SFieldCalculator`).

**In-game proof:** give a recruited character a paired heal ability, wound an ally, open the field **Ability**
menu, use it → HP restored out of combat. Remove the `field` half and rebuild → the field menu greys/misses it
(the `DefaultFieldScript` default arm), proving the field script is what enabled it. (Relaunch after deploy — the
DLL loads once at the title screen.)

### And a custom STATUS behaviour (P7)

The same DLL can host a genuinely new **status ailment** — a stateful per-unit condition with C# on the engine's
status lifecycle. A custom ability's `status` list accepts a **table** (a minted custom status) alongside plain
status names:

```toml
abilities = [
  # a buff that grants a one-shot revive-on-death (Vanish = a positive-status-applying donor):
  { name = "Guardian", from = "Vanish",
    status = [{ name = "Rebirth", template = "auto_life" }] },
]
```

This mints, in one build: a `[StatusScript(BattleStatusId.CustomStatus1)]` (the behaviour) into the DLL, a
`StatusData.csv` row at the auto-allocated custom id (33–63, so the engine can inflict it), and the ability's
`StatusSets` row that applies it. Mix freely: `status = ["Silence", { name = "Rebirth", template = "auto_life" }]`.

**The templates** (transcribed from Memoria `DefaultStatus` donors — with the hook each uses):

| `template` | Hook | Cloned from | What it does |
|---|---|---|---|
| `auto_life` | `OnDeath` | AutoLife | revive the unit once when it would die, at `power`% of max HP (default 50) |
| `auto_attack` | `OnATB` | Berserk | force an auto-Attack each turn (loses manual control) |

`auto_life` takes a **`power`** knob (1–100) = the revive amount as a % of max HP: `{ template = "auto_life",
power = 100 }` revives at full HP, `power = 25` at a quarter (default 50).

Or a raw `{ name = "…", body = "<C# class-body>", hooks = ["death_changer"] }` — you write the `StatusScriptBase`
methods (`Apply`/`Remove`/`OnDeath`/`OnATB`/…) and declare which lifecycle interfaces (`hooks`) they implement:
`death_changer` (OnDeath), `auto_attack` (OnATB), `figure_point` (OnFigurePoint), `finish_command` (OnFinishCommand).

**The HUD icon** (in the status *panels*): a custom status **borrows a vanilla status's icon** — each template
picks a sensible default (`auto_life` → AutoLife, `auto_attack` → Berserk), or set `icon = "<vanilla status>"`
(e.g. `"Regen"`, `"Protect"`, `"Reflect"`) to choose. The kit emits a `BuffIcon`/`DebuffIcon` **DictionaryPatch**
line that registers the sprite at launch, so it shows in every panel display — the battle HUD Good/Bad-status
panel, the target/"hover" status, resists, and the party menu. (FF9 shows statuses by icon only — no text name.)

**The on-model visual** (over the character's 3D battle model): the panel icon and the *on-model* indicator are
**separate** engine mechanisms. To also show something on the model — like Haste's floating up-chevron or Slow's
down-chevron — set `over_model = "<vanilla status>"`; the custom status inherits that status's on-model effect
(its SHP over-model shape / SPS particle / colour tint from `StatusData`). Only some statuses have one: **Haste**
/**Slow** (chevrons), **Silence**/**Trouble** (shapes), a particle (`"Poison"`/`"Berserk"`/`"Blind"`…), or a tint
(`"Protect"`/`"Shell"`/`"Trance"`). `over_model` defaults to the `icon` donor — and **AutoLife has no on-model
effect**, so a revive buff needs e.g. `over_model = "Haste"` to be visible on the model:

```toml
status = [{ name = "Rebirth", template = "auto_life", over_model = "Haste" }]   # heart in the panel + up-chevron on the model
```

**Engine limit (honest):** a **per-tick DoT is not reachable** — the engine gates the per-tick `OnOpr` hook to
vanilla statuses only (a compile-time `OprCount` mask), so a custom status can't tick each frame. The reachable
hooks are `Apply`/`Remove` (on inflict/cure) + `OnDeath` / `OnATB` / `OnFigurePoint` / `OnFinishCommand`, which
dispatch off the applied-effects set (not the tick mask) and so fire for a custom bit.

**Inflicting it:** the custom status lands only if the inflicting ability's formula *applies* statuses — clone a
status-applying `from` (a positive-status buff); the build **warns** if `from` won't apply it (iterate on `from`
until the warning clears).

**In-game proof:** give a recruited character an ability that inflicts `auto_life`, cast it on an ally, let that
ally be KO'd → they auto-revive once. (Relaunch after deploy.)

---

## 3. The four templates

Each template is cloned **verbatim from a shipped FF9 donor formula** (the kit's "learn from the real bytes"
rule), so it can't crash the calc and it reads the ability's OWN `Actions.csv` tuning — `NormalMagicParams()`
pulls the `power` / `element` / `mp` you set on the same custom ability, so `power = 40` still tunes a
`drain_hp` spell.

| `template` | Cloned from | What it does | Point `targets` at |
|---|---|---|---|
| `drain_hp` | `0016` DrainHp | deal magic damage **and heal the caster** the same amount (the flagship) | an enemy |
| `drain_mp` | `0015` DrainMp | Osmose/Absorb — drain the target's MP to the caster | an enemy |
| `magic_damage` | `0009` MagicAttack | standard elemental magic damage — the baseline / parity check | an enemy set |
| `white_wind` | `0030` WhiteWind | heal the target a **fraction of the *caster's* max HP** (`power = 0` → 1/3, else `power`%) | an ally set |

> **Targeting is data, not formula.** The template decides the *math*; set who it can hit with the ability's
> own `targets` (a `TargetType` name, e.g. `"AllEnemy"` / `"SingleAlly"`) and `menu_window`. A `white_wind`
> pointed at enemies would try to "heal" them — point it at allies.

> **Status + formula don't mix freely.** A custom ability that also inflicts a `status = [...]` needs a formula
> that *applies* statuses (`TryAlter*Statuses`). Of the four templates, only `magic_damage` does — the build
> **warns** if you combine `status` with a non-applying `script`. Use `magic_damage` (or a `body` that calls
> `TryAlterMagicStatuses()`) for a status-inflicting scripted spell.

---

## 4. The `body` escape hatch + the formula API

When no template fits, write the C# `Perform()` **body** directly:

```toml
abilities = [
  { name = "Quarter", from = "Fire", targets = "SingleEnemy",
    script = { body = "_v.Target.Flags |= CalcFlag.HpAlteration; _v.Target.HpDamage = _v.Target.MaximumHp / 4;" } },
]
```

The kit wraps your body in the exact class shell the engine expects (namespace `Memoria.Scripts.Battle`,
`[BattleScript(Id)]`, `IBattleScript`, a `BattleCalculator _v` field) and compiles it. Your body is the method
body of `Perform()` — a `BattleCalculator _v` is in scope, and `using System; using Memoria.Data;` are already
imported (so `CalcFlag` resolves).

**The verbs a formula wields** (all on `_v`, the live `BattleCalculator` — clone a donor and retune):

| Piece | What it is |
|---|---|
| `_v.Caster`, `_v.Target` | the two combatants — `.Flags \|= CalcFlag.*` (`HpAlteration`/`HpRecovery`/`MpAlteration`/`MpRecovery`), `.HpDamage`, `.MpDamage`, `.MaximumHp`, `.CurrentMp`, `.IsZombie` |
| `_v.Command.Power` | the ability's tuned power (from your `power`) |
| `_v.NormalMagicParams()` | seed the standard magic power/defence params from the action + stats |
| `_v.CalcHpDamage()` / `_v.CalcMpDamage()` | run the real damage math into `Target.HpDamage`/`MpDamage` |
| `_v.PrepareHpDraining()` | set up the drain flags (so a heal follows the damage) |
| `_v.TryAlterMagicStatuses()` | apply the action's status set (needed if the ability inflicts a `status`) |
| `_v.IsCasterNotTarget()`, `_v.Target.CanBeAttacked()`, `_v.CanAttackMagic()` | the standard guards |
| `_v.Context.PowerDifference`, `_v.BonusElement()`, `_v.Caster.EnemyTranceBonusAttack()`, `_v.Caster.PenaltyMini()`, `_v.Target.PenaltyShellAttack()` | the modifier stack a magic formula walks |

The four templates in `scriptsource.py` are the best worked examples of these verbs in combination.

---

## 5. How it works end-to-end

```
field.toml  script = {template/body}          (author)
   │
   ▼  content/playable.parse_all               (deterministic)
   ├─ mint a custom ABILITY id (192–223)  ── Actions.csv new row (clone `from`, retune)
   └─ allocate a SCRIPT id (256–511)      ── the two number-spaces are DECOUPLED
   │
   ▼  build._emit_battle_data                  repoint the Actions.csv row's scriptId cell -> the 256-band id
   ▼  build._emit_scripts
   ├─ scriptsource.write_scripts              -> Scripts/Sources/Battle/NNNN_<Name>Script.cs   ([BattleScript(NNNN)])
   └─ scriptcompile.compile_scripts (csc)     -> Scripts/Memoria.Scripts.<Mod>.dll
   │
   ▼  in-game (engine)
   ScriptsLoader loads Memoria.Scripts.<Mod>.dll IN ADDITION to the base   (per FolderNames, ScriptsLoader.cs:283-311)
   cast Soul Leech -> Actions scriptId 256 -> BattleExtendedScripts[256] -> YourScript.Perform()
```

**Two number-spaces stay decoupled.** The **ability id** stays in the 192–223 pool (`BattleAbilityId` math); the
**scriptId** is independent, 256+. The engine packs its base scripts 0–109 into a 256-slot array, so **id ≥ 256
lands in the unbounded `BattleExtendedScripts` dict** (`ScriptsLoader.cs:215-224`) — the safe custom band. The
kit uses 256–511.

**The DLL is discovered per mod folder.** `ScriptsLoader` walks `AssetManager.FolderHighToLow` and, for a
`FolderNames` entry, loads `Scripts/Memoria.Scripts.{folder}.dll` from `<mod>/StreamingAssets/` **in addition to**
the base `Memoria.Scripts.dll`. For the folder `FF9CustomMap` the DLL MUST be named exactly
**`Memoria.Scripts.FF9CustomMap.dll`** — the kit derives the name from the deploy folder, so a mismatch would
silently load no custom formulas. Higher-priority mod folders win a `scriptId` collision.

**Determinism invariant.** `_emit_battle_data` (which writes the Actions `scriptId` cell) and `_emit_scripts`
(which writes `[BattleScript(id)]`) each call `parse_all` independently, so the two ids MUST match — `parse_all`
is deterministic (sequential allocators, list iteration), so they always do.

---

## 6. The toolchain — a C# compiler (`csc`)

The DLL is compiled at **build/deploy** time (not at runtime — the engine only ever `Assembly.LoadFile`s an
already-built DLL). So a scripted ability needs a **C# compiler** on the build machine. The kit finds one
automatically, probing in order:

1. **`$FF9_CSC`** — an explicit `csc.exe` path (wins if set and it exists).
2. A **Visual Studio Build Tools Roslyn `csc`** (the same toolchain used for an engine rebuild), e.g.
   `…/Microsoft Visual Studio/*/*/MSBuild/*/Bin/Roslyn/csc.exe`.
3. The **always-present .NET Framework `csc`** at
   `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`.

**The lint gate (fail early, not mid-build).** If a field carries a scripted ability but **no compiler is
findable**, `ff9mapkit lint` reports a build-blocking **error** naming the ability — so you learn at lint time,
not when a build dies half-way:

```
$ ff9mapkit lint my.field.toml
  ERROR  scripted custom ability (Soul Leech) needs a C# compiler (csc) to build its `script = {...}` battle
         formula into Memoria.Scripts.<Mod>.dll, but none was found -- the build would fail at compile time.
         Install Visual Studio Build Tools (Roslyn csc) or point $FF9_CSC at a csc.exe ...
  1 error(s), 0 warning(s)
```

The gate fires only when the channel is actually used (no scripted ability → no requirement; a *scalar*
data-only `script` needs no compiler). The FF9 install is **not** required at lint (you can author on a machine
without the game) — but building the DLL is compiled **against the installed engine** (§7), so the actual build
needs both the compiler and the install.

**The compile itself** mirrors the shipped `Memoria.Compiler`: `csc /target:library /nostdlib+ /noconfig
/optimize+` with the 7 reference DLLs (`mscorlib`, `System`, `System.Core`, `Assembly-CSharp`, `Memoria.Prime`,
`UnityEngine`, `XInputDotNetPure`) pulled from the install's `x64/FF9_Data/Managed`. The `/nostdlib+ /noconfig` +
explicit Unity `mscorlib` avoid a double-`mscorlib` conflict.

---

## 7. The honest cost — version-coupling + RELAUNCH

- **Version-coupling.** The mod DLL is *code* bound to the installed `Assembly-CSharp` types, so it is valid only
  against the engine it was compiled against — **more coupled than any other kit pillar** (every other channel is
  data). A stale DLL is **not** caught at load; it throws `MissingMemberException` at *cast*, logged as
  "incompatible with the current version of Memoria" naming the mod (`SBattleCalculator.cs`). **RULE: always
  build/deploy against the local install's `Managed` dir** (never a checked-in `Assembly-CSharp`) — the same
  discipline as an engine rebuild's version-match. Blast radius is contained: additive + per-mod, so a broken DLL
  degrades only that mod's custom formulas.

- **Drift is caught offline (before the game throws).** Each build **stamps** the DLL with the engine's
  FileVersion (a `<dll>.buildinfo.json` sidecar, carried into the mod on deploy). The deploy step and the kit's
  **health check** (the Workspace's *Setup & Health* page) compare that stamp against the *currently-installed*
  engine and **warn** on a mismatch — so if you update Memoria after deploying, you're told to rebuild *before*
  the game hits `MissingMemberException` in battle. It's best-effort/advisory (the Windows FileVersion): quiet
  when it can't read a version, and it won't false-alarm across identical released engine bundles (they share a
  FileVersion) — it fires on a real engine swap/update.

- **RELAUNCH required.** A scripts DLL loads **once at the title screen** (`TitleUI.cs` → `Assembly.LoadFile`).
  **F6 → Reload does NOT re-load it** (like an engine-DLL or CSV-startup change). Deploy prints a relaunch note;
  close FF9 fully and relaunch after deploying a scripted ability.

---

## 8. Build / deploy / revert

- **Build:** `py -m ff9mapkit build <field.toml>` (or the dev loop `py tools/deploy_field.py <field.toml>`) emits
  `Scripts/Sources/Battle/*.cs` + compiles `Memoria.Scripts.<Mod>.dll` into the mod. A build with **no** scripted
  ability never invokes a compiler (the whole channel is a no-op) and *drops* any stale `Scripts/` tree from a
  prior build (so removing the last scripted ability un-ships the DLL).
- **Deploy:** `deploy_field.py` syncs the DLL reversibly (it rides the CSV-revert idiom) and copies the `Sources/`
  for provenance. Because the DLL loads at the title, **relaunch FF9** after the deploy (F6 won't pick it up).
- **Revert:** `py tools/scroll_out/revert_deploy_<id>.py` restores the slot (removing the DLL + CSV deltas).

---

## 9. Provenance

- The **four templates** (`scriptsource.py`) are C# formula bodies cloned from FF9's own donor scripts — they
  live in the **kit source**, not committed game data. This doc names the donors and describes behaviour; it does
  not paste the cloned bodies.
- The **compiled DLL** and the emitted `.cs` are **mod build-output** — never committed (`Scripts/` is gitignored
  in a mod folder). The `.cs` is shipped alongside the DLL inside a *deployed* mod for provenance + re-compile
  against a future engine, but is runtime-inert (the game loads only the DLL).
- A minted formula reads live install types at compile time; nothing SE-derived is checked in.

---

## 10. When NOT to use it (reach for data first)

Scripted formulas are the **last** lever, not the first — they carry the version-coupling cost. Prefer, in order:

1. **`Actions.csv` data** (`power`/`element`/`rate`/`mp`/`targets`/`category`/`status`) — most spell identity.
2. **A scalar `script` re-point** to an *existing* engine formula (still no DLL).
3. **`effect = "[code=...]"`** (the NCalc `AbilityFeatures` channel) — for a scalar tweak (e.g. `[code=MPCost] 0`)
   with no control flow.
4. **A scripted `script = {template/body}`** — only when the behaviour is a genuinely new *formula* (drain,
   %-max-HP, sequencing) the above can't express.

---

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ff9mapkit lint` → `ERROR … needs a C# compiler` | no `csc` on the build machine | install VS Build Tools, or `set FF9_CSC=<path to csc.exe>` (the .NET Framework csc works) |
| build → `ScriptCompileError` with csc diagnostics | the `body` / template C# doesn't compile against this engine | fix the C# (the diagnostics name the line); clone a template as a starting point |
| build → "needs your FF9 install / managed DLLs" | no FF9 install to compile against | build on the machine with FF9 installed (the DLL is version-coupled to it) |
| `Memoria.log` → `Unknown script id: N` | the DLL didn't load / the id didn't bind | relaunch FF9 (F6 won't load the DLL); check the DLL name matches the mod folder |
| `Memoria.log` → "incompatible with the current version of Memoria" | a **stale** DLL (compiled against a different engine) | re-deploy so the kit re-compiles against the current install (deploy + the health check warn on this drift *before* the game does — §7) |
| the spell inflicts no status | the `script` formula doesn't apply statuses | use `magic_damage` (or a `body` calling `TryAlterMagicStatuses()`); the build warns about this |
| the spell shows the base MP cost in the field menu | a `[code=MPCost]` effect is a **battle**-side hook | expected — the field menu reads the base cost; the effect applies in battle |
| the ability "Miss"es / greys out when used from the **field** menu | no paired `script.field`, or a stale/not-yet-loaded DLL | add `script.field` (§2), rebuild, and **relaunch** — an unbound custom scriptId hits the field default arm (Miss) |

---

## 12. The Overload channel — engine hooks, one hub per mod

The same mod DLL can implement Memoria's **`IOverload*` interfaces** — engine choke points where a registered
class *replaces* an inline engine default (`ScriptsLoader` registers by interface, no attribute needed).
The engine keeps **one implementer per interface per DLL** (a last-wins dictionary, type order unspecified),
so the kit emits exactly one **hub** class (`Scripts/Sources/Overload/0000_OverloadHub.cs`, regenerated on
every compile — never edit it) and builds features as plain static classes the hub calls in a fixed order:
**mutators before observers** (a difficulty scaler runs before telemetry logs the roster, so the log shows
the stats you actually fight). Where a hook displaces an engine default (backstab/kill-frozen, the ×1.5
damage-modifier stack, the reflect multiplier), the default is **transcribed verbatim** into the hub —
gameplay is unchanged unless a feature changes it on purpose. Hooks whose **return value** the engine acts
on (like `OnGameOver`, where `true` cancels the game over) are **single-owner**: exactly one feature supplies
the verdict, and that feature transcribes whatever part of the displaced default it keeps. Four features
exist today:

### Battle telemetry (dev tool — `ff9mapkit battle-telemetry`)

Logs every battle calc as one JSON line to `<game>/ff9mk_battle_telemetry.jsonl`, so battle balance can be
analyzed offline instead of eyeballed.

```
ff9mapkit battle-telemetry FF9CustomMap     # install into a live mod folder -> RELAUNCH -> fight
ff9mapkit battle-telemetry --report         # per-ability casts / hit% / crit% / damage stats
ff9mapkit battle-telemetry --clear          # start a fresh capture
ff9mapkit battle-telemetry FF9CustomMap --off   # remove the hook (recompiles the DLL without it)
```

Events: `battle` (boundary + full unit roster), `calc` (one per formula invocation, **both** directions,
before it runs — a calc with no matching `result` is a miss/guard/no-effect, so hit rates fall out for free),
`result` (computed **pre-cap** damage on the hit branch, both directions), `applied` (post-cap damage + target
HP after — enemy-targeted calcs only; the engine's call site early-returns for player targets).

Every log write is `try/catch`-swallowed, so the hook can never break a battle. The source lives at
`Scripts/Sources/Telemetry/` (a sibling of `Sources/Battle`, so a field build never wipes it), and
`deploy_field` re-folds any live Overload feature into a freshly deployed DLL automatically.

### `[difficulty]` — declarative enemy scaling (shipped content)

A journey/field author's "hard mode": one table in `field.toml` scales every **enemy** once per battle, at
battle init (a hook with **no engine default** — nothing vanilla is displaced). Players are never touched.

```toml
[difficulty]
enemy_hp = 1.5        # x max+current HP of every enemy
enemy_attack = 1.25   # x Strength (physical)
enemy_magic = 1.25    # x Magic
flag = "hard_mode"    # OPTIONAL gate: scale only while this gEventGlobal BIT is set
                      # (a [[flag]] name or a bit index; omit = always on)
```

Scales are `0.05`–`20.0` (unset = `1.0`); HP clamps at 9,999,999 logical, byte stats at 255. The block is
**mod-global** (the DLL is per deployed folder): a campaign may repeat an *identical* block on several
members, but two different blocks refuse at build. With `flag`, the gate is read fresh at every battle —
seed it from `[startup]`/an event for a hard-mode journey, or toggle it live with **F6 → Flags** while
testing; the bit clear (or any state hiccup) means *vanilla*, never a broken battle. Like the whole channel
it compiles at build time (needs `csc` — the lint gate names it) and loads once at title (**relaunch**).

### `[rebalance]` — declarative damage multiplier (shipped content)

Scales the **final HP-damage number** by the caster's side, at the last write before the engine applies it.
Where `[difficulty]` scales enemy *stats* (which feed the formula), `[rebalance]` is a flat post-formula
multiplier — and the only way to scale what the **party** deals.

```toml
[rebalance]
player_damage = 1.5   # x HP damage dealt BY players (party hits harder)
enemy_damage = 0.75   # x HP damage dealt by enemies (softer incoming hits)
flag = "hard_mode"    # OPTIONAL gate (same shape as [difficulty])
```

Same `0.05`–`20.0` range, same mod-global + flag-gate rules. Only **pure HP damage** is touched — healing,
recovery, and MP are left alone. Two honest limits worth knowing: the engine clamps damage to **9999** right
after this hook unless the player set `[Battle] BreakDamageLimit = 1` in `Memoria.ini`, so a multiplier reads
through below 9999 and is capped above it (the kit won't force a global engine config from a mod hook); and
the `IsDmg9999` cheat forces *player* damage to 9999 after this regardless of the scale. `[difficulty]` and
`[rebalance]` **compose** — use difficulty to make enemies tankier/tougher, rebalance to dial the raw numbers.

**Flag-gate granularity differs between the two.** A gated feature is re-checked every time its hook fires,
so the toggle latency follows the hook: `[rebalance]` gates at damage time (**per hit**), so flipping the bit
with F6 → Flags takes effect *immediately, mid-battle*; `[difficulty]` gates at battle init (**per battle**),
so its bit only bites from the *next* battle. Pick the block whose cadence matches the effect you want (a live
mid-fight damage swing → rebalance; a per-encounter difficulty toggle → difficulty). ★ Both in-game proven.

### `[deathrules]` — declarative game-over rules (shipped content)

Owns the **party-wipe verdict** (`OnGameOver` — a returning, single-owner hook): when the last player goes
down, the feature decides whether the game over proceeds or is canceled.

```toml
[deathrules]
second_wind = true          # cancel the wipe ONCE per battle: the party is revived
chance = 60                 # OPTIONAL percent chance the second wind fires (whole 1-100; default 100)
animation = "short"         # OPTIONAL: "full" (default) = the Phoenix summon plays; "short" = no
                            # choreography, the party just stands back up
revive_hp = 0.25            # OPTIONAL, "short" only: revive HP as a fraction of max (0 < x <= 1)
keep_rebirth_flame = false  # OPTIONAL: false REMOVES Eiko's vanilla auto-revive (default true = kept)
flag = "mercy_mode"         # OPTIONAL gate (same shape as the siblings)
```

The **second wind** is a roguelike mercy rule: the first wipe of a battle revives the party, then recharges
at the next battle; a second wipe in the same battle is a normal game over. Both revive flavors are
engine-sanctioned, not hand-rolled: `animation = "full"` queues the engine's own `Rebirth Flame` command
exactly the way the vanilla Eiko default queues it — the full Phoenix summon plays and the ability decides
the revive HP; `animation = "short"` revives the fallen directly the way the engine's death-changer statuses
(Auto-Life) do — no choreography at all, the party simply gets up at `revive_hp` × max HP (floor 1; only the
*dead* revive — petrify stays, and a wipe with nobody revivable falls through to a normal defeat).
`keep_rebirth_flame = false` is the hardcore mirror: it removes Eiko's vanilla auto-revive (with no
`second_wind` it makes wipes strictly final). Owning the hook *displaces* the Eiko default, so the kit
transcribes it verbatim and keeps it unless you turn it off.

`flag` semantics differ from the siblings **on purpose**: bit clear means *fully vanilla* — Eiko's auto-revive
still fires even when `keep_rebirth_flame = false`, because the rule is asleep, not half-applied. Granularity:
the hook fires at wipe time, so the flag toggles the rules **live** — the very next wipe obeys the new state.
Mod-global + build rules identical to `[difficulty]`/`[rebalance]`. Fail-safe: any hiccup returns `false` (a
vanilla defeat) — never a canceled game over with nobody revived, which would stall the battle.

**`on_defeat`** — warp instead of a game over (`on_defeat = { warp_to = <field id>, hp = 0.2, gil_loss =
0.1 }`): the fallen party revives quietly at `hp` × max HP, optionally loses `gil_loss` × its gil, and the
battle ends through the engine's **own flee sequence** (the run-away fade — no flee-stat side effects, no
double gil cut); back on the field, the after-battle handler warps to `warp_to` (a kit-built check the build
injects into every encounter field carrying the block). Composes with `second_wind`: the wind fires first,
and only a spent wind (or a failed `chance` roll) falls through to the warp — a roguelike "one free revive,
then back to camp". The wipe marker rides a kit-reserved story bit (8508; override via `on_defeat.flag`).
Coverage rule: repeat the identical `[deathrules]` block on **every** encounter field of the mod — the build
names any gaps (a wipe in an uncovered field revives and flees but cannot warp).

### `[lowhp]` — the LowHP threshold (shipped content)

Owns the **HP/MP checkpoint verdict** (`UnitCheckPoint` — the second returning, single-owner hook) to
reparameterize when a player counts as *"HP is low"*: vanilla is at or below **1/6** of max HP, the point
where the HP number turns yellow and the engine's `LowHP` status applies (the status HP-is-low supporting
abilities and AI key on).

```toml
[lowhp]
threshold = "1/3"     # the LowHP fraction of max HP (vanilla 1/6): "N/D" string (exact, denominator
                      # <= 100) or a number in (0, 1) (snapped to <= 1/100 granularity)
flag = "hard_mode"    # OPTIONAL gate: bit clear = the vanilla 1/6; toggles LIVE (per HP/MP change)
```

The displaced default's side effects (add/remove `LowHP`, the yellow/white HP color, the MP color rule) are
transcribed verbatim with only the threshold comparison changed — exact integer math in the engine's own
`* 6` shape, so there's no float-boundary drift. Players only, like vanilla. Two honest scope notes: a unit
at 0 HP is dead *before* this check runs (this is not a death-prevention hook), and the checkpoint's return
value only matters for its `Death` bit — everything player-visible here is the side effects.

One caveat shared with the whole channel: if a *second* stacked mod folder ships its own implementation of
the same `IOverload*` interface, the higher-priority folder's wins silently. Within one mod the kit refuses
a hand-dropped `.cs` that collides with the hub (a clear compile-time error instead of a coin flip).

---

## 13. See also

- [BATTLE_DESIGN.md](BATTLE_DESIGN.md) — the full battle-tuning lever map; §2(c) is the `scriptId` (re-point vs
  new-formula) row this channel completes.
- [CUSTOM_MODELS.md](CUSTOM_MODELS.md) — a custom 13th character (the `[[playable]]` block a scripted ability
  rides on) with its own model, animset, command, and ability kit.
- Project memory `project-ff9-scripts-dll` — the engine mechanism (source-cited), the compile recipe, and the
  7-phase build plan. `project-ff9-ability-preset-system` / `project-ff9-13th-character` — the ability-kit stack
  this builds on.

**Key refs:** `ScriptsLoader.cs:215-311,343-365`, `SBattleCalculator.cs:63,109-131,200,323`, `btl_sys.cs:87`,
`TitleUI.cs:1528` · `ff9mapkit/battle/scriptsource.py`, `scriptcompile.py`, `overload.py` (the hub),
`telemetry.py`, `difficulty.py`, `rebalance.py`, `deathrules.py`, `content/playable.py`, `build.py`
(`_emit_scripts`).
