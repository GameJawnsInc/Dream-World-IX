# Scripts-DLL + Overload — engine battle code with no engine rebuild

Distilled from memory `project-ff9-scripts-dll` and `project-ff9-overload-hooks` (the canonical deep
recipes — loader line refs, compile command, hub internals, proof history). Canonical doc:
`ff9mapkit/docs/SCRIPTS_DLL.md` (§1-11 formulas/field/status, §12 Overload + the shipped features).

## Contents

- [The mechanism](#the-mechanism)
- [The three Scripts-DLL surfaces](#the-three-scripts-dll-surfaces)
- [Compile, version-coupling, relaunch](#compile-version-coupling-relaunch)
- [The Overload channel (IOverload* hooks)](#the-overload-channel-ioverload-hooks)
- [The one-hub architecture (laws)](#the-one-hub-architecture-laws)
- [Returning hooks + the GRANULARITY LAW](#returning-hooks--the-granularity-law)
- [Shipped features: difficulty / rebalance / deathrules](#shipped-features-difficulty--rebalance--deathrules)
- [Battle telemetry](#battle-telemetry)
- [Deploy stickiness](#deploy-stickiness)

## The mechanism

A mod-owned **`Memoria.Scripts.<ModFolder>.dll`** at `<mod>/StreamingAssets/Scripts/` is loaded IN
ADDITION to the base Scripts DLL — Memoria's sanctioned additive-plugin surface, distinct from an
engine (`Assembly-CSharp.dll`) fork. It is a PREBUILT DLL (`Assembly.LoadFile`; no runtime compile —
shipping `.cs` alone does nothing). scriptIds **>= 256** land in the unbounded `BattleExtendedScripts`
dict = the safe custom band. Two number-spaces stay decoupled: the ABILITY id (192-223 band) vs the
**scriptId** (256+). Higher-priority mod folder wins a scriptId collision.

## The three Scripts-DLL surfaces

All three hang off a `[[playable]]` custom-ability inline table; the kit mints the C# from templates or
a raw body and compiles at build (`build._emit_scripts`):

1. **Battle FORMULA** — `script = { template = "drain_hp" }` or `{ body = "<C# Perform() body>" }` →
   a `[BattleScript(id>=256)]` class; the Actions.csv row's scriptId cell is repointed. (A SCALAR
   `script` is data-only — repoints to an EXISTING stock 0-191 formula, no DLL.) Templates:
   `drain_hp` / `drain_mp` / `magic_damage` / `white_wind`, cloned verbatim from FF9 donors.
2. **FIELD effect** — `script.field = { template/body }` → a paired `[FieldAbilityScript]` at the SAME
   scriptId (binds on the action's ScriptId; battle attr runs in battle, field attr on the field menu —
   zero new binding). REQUIRES the paired battle formula. Templates: field_heal_hp / white_wind /
   chakra / cure_status / revive.
3. **STATUS behaviour** — `status = [{ name, template/body, hooks }]` → `[StatusScript(CustomStatusN)]`
   (band 33-63) + a minted StatusData row + a `BuffIcon`/`DebuffIcon` DictionaryPatch line (panel icon;
   registered at startup so every HUD consumer shows it) + `over_model = "<vanilla status>"` (the
   on-model SHP/SPS/tint — a SEPARATE mechanism from the panel icon) + a `power` knob. Per-tick DoT
   (`OnOpr`) is engine-gated by a const mask → unreachable (documented limit); viable hooks:
   Apply/Remove/OnDeath/OnATB/OnFigurePoint/OnFinishCommand. The inflict lands only if the ability's
   formula APPLIES statuses (build warns).

## Compile, version-coupling, relaunch

- Compiled at DEPLOY against the local install's Managed dir via `csc` (VS BuildTools Roslyn; `$FF9_CSC`
  override). A lint-time toolchain gate fails EARLY when no `csc` is findable.
- The DLL is code bound to the installed `Assembly-CSharp` — a stale DLL throws MissingMemberException
  at cast time. The kit stamps `<dll>.buildinfo.json` and warns on engine drift (`doctor`/deploy).
  Rule: always compile at deploy time; never check in a compiled DLL.
- **RELAUNCH required** — the DLL loads once at the title screen; ~ Reload does NOT re-load it.
- **Fully QUIT FF9 before a redeploy that touches the DLL** — a running process memory-maps it and the
  overwrite fails (`OSError: [Errno 22]`); the title screen still holds it.

## The Overload channel (IOverload* hooks)

10 fixed `IOverload*` interfaces (all battle-side; hook list + call sites: memory
`project-ff9-overload-hooks`). Registration is keyed BY INTERFACE, no attribute. **Override-only**: an
implementation REPLACES the engine's inline default, so it must transcribe what it displaces.
First-wins across stacked mod folders, SILENTLY; last-wins within one DLL — which is why the hub exists.

## The one-hub architecture (laws)

Quoted verbatim from memory `project-ff9-overload-hooks`:

> `ScriptsLoader.ProcessType` registers Overload implementations into a `Dictionary<Type, Type>` keyed
> BY INTERFACE -- within one DLL the LAST-processed type silently wins, and `Assembly.GetTypes()` order
> is unspecified. So two independent classes claiming the same interface (telemetry's OnBattleInit + a
> difficulty scaler's OnBattleInit) = a silent coin flip. The kit therefore emits exactly ONE
> `Sources/Overload/0000_OverloadHub.cs` (REGENERATED on every compile; implements only the interfaces
> active features claim) and features are PLAIN STATIC classes with no interface tokens. The hub splices
> feature calls at hand-authored per-hook positions: **mutators (order 10) before observers (order 90)**

Displaced engine defaults are transcribed VERBATIM into the hub (position hand-authored per hook); each
spliced call is try/catch-wrapped; a collision GATE refuses a hand-dropped `.cs` colliding with the hub.
Adding a feature = one registry entry (dir/file/order/live_owned/hooks/render) + a static-class renderer
+ splice statements (`ff9mapkit/battle/overload.py`).

## Returning hooks + the GRANULARITY LAW

Quoted verbatim from the same memory:

> **THE RETURNING-HOOK HUB MODE:** hooks whose return value the engine acts on
> (`RETURNING_HOOKS = {OnGameOver}`; UnitCheckPoint joins with its feature) are SINGLE-OWNER -- the
> registry value is a C# EXPRESSION (no `;`), the hub emits `try { return <expr>; } catch { } return
> <fail-safe>;` (OnGameOver fail-safe = `false`: a vanilla defeat, never a canceled wipe with nobody
> revived = soft-lock), and `render_hub` raises ScriptCompileError naming the claimants if two features
> claim one.

> THE GRANULARITY LAW: a flag-gated Overload feature's toggle latency = its hook's fire cadence.
> rebalance = per-hit (live mid-fight berserk/enrage); difficulty = per-battle. Same gate mechanism,
> different granularity from WHERE the hook sits.

## Shipped features: difficulty / rebalance / deathrules

All three are `field.toml` tables, mod-global, optionally gated on a `gEventGlobal` flag (clear or any
exception = vanilla). All in-game proven 2026-07-11.

- **`[difficulty]`** — `enemy_hp`/`enemy_attack`/`enemy_magic` (floats 0.05-20; all-1.0 refuses) +
  `flag`. Enemies only, at `OnBattleInit` (flag bites per-BATTLE). Scales through the LOGICAL HP
  properties (raw `max.hp` writes would corrupt +10000 non-dying bosses).
- **`[rebalance]`** — `player_damage`/`enemy_damage` (floats 0.05-20) + `flag`. Scales the final
  HpDamage at `OnDamageFinalChanges`, both directions by `Caster.IsPlayer`; pure HP damage only (heals
  untouched); flag bites per-HIT. The ONLY way to scale what the PARTY deals. **The 9999 cap** (quoted
  verbatim): "the hook fires PRE-cap, and the engine clamps to `MaxDamageLimit` (9999) RIGHT AFTER
  unless the player set `[Battle] BreakDamageLimit = 1` in Memoria.ini" — the kit does not force that
  engine config from a mod hook.
- **`[deathrules]`** — owns the `OnGameOver` verdict: `second_wind` (cancel a wipe ONCE per battle by
  queueing the engine's own Rebirth Flame revive — inherits the FULL summon animation; a short-anim
  knob is a noted follow-up), `chance` (whole percent), `keep_rebirth_flame` (false = Eiko-removal),
  `flag` (clear = fully vanilla INCLUDING Eiko). Recharges next battle.

They COMPOSE (difficulty = enemy stats; rebalance = a flat post-formula multiplier).

## Battle telemetry

`battle-telemetry <mod> | --off | --report | --clear` — a hub-hosted observer (order 90) logging every
calc to `<game>/ff9mk_battle_telemetry.jsonl`: `battle` roster (post-mutator, so difficulty-SCALED —
telemetry IS the difficulty/rebalance verification oracle), `calc` (a `calc` with no `result` = a miss),
`result` (pre-cap), `applied` (post-cap). `--report` = per-ability balance stats (strips the raw FF9
text markup in enemy names). RELAUNCH-scoped like the whole channel.

## Deploy stickiness

`tools/deploy_field.py` is generic: it REPLACES build-owned Sources dirs and preserves live-owned ones
(telemetry), then recompiles if any live-owned feature is present — one code path for every feature.
⚠ `ff9mapkit/deploy.py` (deploy-campaign/journey wholesale-replace) has NO stickiness — a live
telemetry install is wiped by those; re-install after.
