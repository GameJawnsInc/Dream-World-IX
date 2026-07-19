# Overworld engine — world-states, exit cascade, vehicles (reference)

> Index + verbatim load-bearing facts only. Full RE: canonical doc `ff9mapkit/docs/OVERWORLD_ENGINE.md`
> (tick/actor model, dispatchers, minimap, environment, encounters, teleport fix) + memory
> `project-ff9-overworld-worlds` (13 dispatchers + exit cascade + minimap/encounter levers) and
> `project-ff9-overworld-vehicles` (the vehicle system + save-position layout).

## Contents

- [The 13 world-states (dispatchers)](#the-13-world-states-dispatchers)
- [The exit cascade (which state loads)](#the-exit-cascade-which-state-loads)
- [Vehicles](#vehicles)
- [Save-position layout](#save-position-layout)
- [Encounters / minimap / environment (no-DLL levers)](#encounters--minimap--environment-no-dll-levers)

## The 13 world-states (dispatchers)

- The overworld is 13 event-script dispatchers `EVT_WORLD_WORLD00..12` = `EventDB[9000..9012]`; exactly one
  is loaded as the per-frame brain, keyed by `ff.wldMapNo`. ONE shared set for ALL discs (disc 4 = distinct
  ART, same `.eb` family; disc 4 is `ScenarioCounter >= 11090`, re-derived every world load — 2026-07-18
  correction: `GetDisc()` checks `_customDiscModifier.HasCondition` (the Memoria config Disc4 override) FIRST,
  falling back to the SC>=11090 test — so it is not purely SC-derived with no other flag).
- Roles: free-roam area-switch states 9000/02/03/05/07/08/09/10/11 (vehicle switch -> AREA switch ->
  `Field()` + an entry-0 entrance-func table); cutscene states 9001/04/06/12 (no AREA switch). Foot-only
  free-roam = 9002/9010/9011. **9009 = every band's default arm** (all-vehicle, all-field superset — its
  Main_Init force-spawns every vehicle actor).
- Verbatim rule: "A custom entrance must be added to the WORLDxx actually loaded at that beat" — see
  terrain-entrance.md / `world-entrance` (it deploys to every dispatcher carrying the case).
- The 13 are the complete LIVE set (9100/9101/LND/TRE/PAGE = vestigial or dead registrations).

## The exit cascade (which state loads)

- `WorldMap()` opcode `0xB6` -> `SetNextMap(arg)` -> `EventDB[arg]` — the arg IS the wldMapNo. All 79
  world-exit fields carry a byte-identical cascade selecting by **(ScenarioCounter band) x (region key
  `Global.Int16[2]`)**; each exit field writes the region key itself, SC-gated. Band boundaries and the
  disc-1 region partition: memory `project-ff9-overworld-worlds` + OVERWORLD_ENGINE.md "The 13 world states".
- Entrance-table SC-dependence: each area icon's `Field()` destination is picked purely by
  `f(area, ScenarioCounter, occasional flag)` — SC reached out of natural order routes icons to fields
  authored for a different story beat (the "random field teleport" mechanism). Overworld->field entries pass
  the s28 `ForkSiblingField` redirect (a forked donor id lands in its fork).

## Vehicles

- Structural fact (memory `project-ff9-overworld-vehicles`): the overworld is a PURE EVENT-DRIVEN scene —
  "the `.eb` owns policy, C# owns mechanism." Unlock/placement/persistence are `.eb`-authored.
- Three DISTINCT numbering spaces — actor INDEX, GEO id, and MODE = `gEventGlobal[190]` (0=foot, 1-5 chocobo,
  6 gold-fly, 7 Blue Narciss, 8 Hilda Garde III, 9 Invincible). Chocobo OWNERSHIP tier = `gEventGlobal[191]`.
- Chocobo mount = TWO actors (mount controlled + rider slaved); airship = ONE combined model.
- Vehicle IDENTITY is bound at DISPATCHER-LOAD by `[190]` at that instant (each vehicle actor's Init runs
  `DefinePlayerCharacter` gated on `[190]`); an F6 poke afterwards changes only the movement PROFILE.
  Reliable F6 recipe: force On-foot (mode 0) -> reload the dispatcher -> then poke the desired vehicle,
  only on a dispatcher where that vehicle actor exists. Forcing a mode whose spawn gate isn't met on the
  other dispatchers = a real unguarded null-deref crash (the per-dispatcher fix table is in the memory).
- F6 vehicle buttons are allow-listed per wldMapNo; the vehicle-independent World-tab Teleport reaches test
  spots on gated states.

## Save-position layout

- The overworld player position IS in `gEventGlobal`: X @ bytes [64:67], Z @ [69:72], 24-bit LE signed
  `world*256` fixed-point; Y is NOT stored (re-derived by ground-snap). Per-actor array stride +19 (mounted
  chocobo @ [83]/[88]). Edit BOTH the Memoria extra file and the main block; only relocate to a VALID
  walkable spot (an invalid spawn risks the actor brick -> memory `project-ff9-overworld-actor-brick`).

## Encounters / minimap / environment (no-DLL levers)

All in-game proven, detailed in memory `project-ff9-overworld-worlds` + OVERWORLD_ENGINE.md:

- `world-encounter-rate` — rewrites the world `.eb`'s `w_frameEventBattleProb` writes (multiplier / set /
  peaceful), per-language, no DLL.
- `world-encounters` — edits the 355-record `discmr.img` encounter table (record selection is
  ZONE-slice-primary; target by `area`/`zone`, read `area` off F6; disc 1 and disc 4 have separate tables;
  RELAUNCH to apply).
- Minimap markers — reveal by `[startup] reveal_markers` (GLOB bit `736+locId`); rename by
  `world-rename-markers`. Adding/moving a marker = DLL.
- Weather/environment — `world-environment` emits Memoria's `Environment.txt` (mist / rain / light /
  effects / place forms); RELAUNCH to apply.
- Overworld texturing — one global 1024^2 atlas per part; tile picking via `world-atlas-catalog` /
  `world-mesh-build --tile`; new art goes in a free atlas region (`world-atlas-add-tile`). Sample the
  ACTIVE atlas (see terrain-entrance.md, Moguri warning).
