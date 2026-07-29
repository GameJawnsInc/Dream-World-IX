# What a synthetic WorldDisc INHERITS from stock — the 9013 sailing census

Owner sailed the all-sea Path D world (9013, spike armed) 2026-07-29 and catalogued what showed up in an
ocean that was supposed to be empty. This is the most useful accidental experiment of the arc: it maps
exactly how much stock behavior is **not** carried by the block grid, and therefore survives replacing it.

Grid convention: the engine names cells `Block[InitialX][InitialY]`, and `Number = InitialY * 24 + InitialX`.

---

## Class A — CELL-KEYED (the block grid carries it)

### A1. Our own loose overrides — 56 cells

The Southern Ring's `Terrain.ff9mesh` + `Donor.txt` files under
`FF9CustomMap-world/FF9_Data/WorldMap/Disc1/`. Because Path D keeps `currentDisc == 1`, every override
lookup resolves against the **same** disc-1 namespace, so all of our real disc-1 edits bleed into the
synthetic world.

Owner sightings: Quay Islands `blk[22][18]` and `blk[6][19]`; the grass-island→desert-island+beach at
`blk[12][18]`; grass+forest+hill at `blk[2][3]`.

**Fix: `s74`, the sentinel-disc override namespace.** This is the concrete justification for it — not a
hypothetical future collision, an observed one.

### A2. Stock `block.Number` special objects — exactly FOUR active on disc 1

Ten `if (block.Number == N)` cases exist in `LoadBlock`; **six are empty stubs** (219 second occurrence,
31, 115 first occurrence, 283, 219 third, 397). The active ones:

| Number | Cell | What it spawns | Site |
|---|---|---|---|
| 219 | `blk[3][9]` | Water Shrine | `WMWorld.cs:~569` |
| 158 | `blk[14][6]` | tree object — **gated on `w_frameDisc == 4`**, so inert here | `:626` |
| 389 | `blk[5][16]` | prefab `Block[5][16] Object` — the Daguerreo bridge / cave mouth | `:678` |
| 91 | `blk[19][3]` | `Effects/Quicksand` | `:693` |
| 115 | `blk[19][4]` | `Effects/Quicksand` ×N | `:704` |

Owner confirmed 115 ("sandpits at blk[19][4]") and 389 ("floating remnants of Daguerreo at blk[5][16]").
**Unconfirmed predictions from this model: 219 at `blk[3][9]` should be the Water Shrine, and 91 at
`blk[19][3]` more sandpits.** If either is absent the model is wrong.

These appear because `s71` deliberately sets stock row-major `Number` (cell identity, useful for
debugging, and their appearance is positive evidence cell addressing works). **Decision for a real Path D
world: keep row-major `Number` but guard the four special-object cases behind "not a synthetic disc"** —
a new continent should not contain Daguerreo's bridge. Fold into `s74`.

> ⚠ The owner's `blk[19][11]` "misty SFX" is Number **283**, which is an EMPTY STUB. That sighting is
> Class B, not a block special — a useful negative result that keeps the model honest.

---

## Class B — POSITION-KEYED (survives regardless of the grid)

None of this comes from `WMBlock`. It keys off **world position** or the running dispatcher, both of which
Path D preserves exactly, so it is inherited wholesale with **disc-1 geography's semantics**.

| Owner sighting | Mechanism |
|---|---|
| airships `~blk[19][12]`, the Cleyra tornado | actors **our own verbatim WORLD11 clone spawns** — a real disc-1 dispatcher doing its job |
| mist | `ff9.w_frameFog` ← `w_weatherFogCheck()` (`ff9.cs:8459`) ← `WorldConfiguration.UseMist()`. ⚠ Keyed on the **ScenarioCounter**, NOT position or world id, and there is **no `.eb`/RunWorldCode route to it at all** (no `w_frameSetParameter` case writes `w_frameFog`). Suppressed for synthetic worlds by `s75`. |
| desert-continent orange tint | **A DIFFERENT SYSTEM — lighting, not fog** (this row originally said `w_frameFog`/area tables; that was wrong). It is weather-light mode 1 "Evening" from `WeatherColors.csv`, selected by `ff9.w_weatherMode` ← `WorldConfiguration.GetWeatherLight()`, a pure XZ-distance test against 3-4 **hardcoded world positions**, two of which fall inside the 1536×1280 grid. **Turning mist off does not remove it.** Clean fix is pure data: any `Light Add` line in `Environment.txt` sets `_customLightModifier.Count > 0`, which makes `GetWeatherLight` skip all four hardcoded zones. |
| vibrations / earthquakes `blk[18][5]` | vibration data + position triggers (the `vib` lane s62 touched) |
| misty SFX `blk[19][11]` | world SPS (`WorldSPSSystem`, created in `LoadEffects`, `WMWorld.cs:1772/1833`) |

### Why this matters more than it looks

**PLAN.md §8 assumed these systems would be ABSENT or degraded on a new world. They are not — they are
actively inherited, keyed to the OLD geography.** That is a different problem from the one the plan
scoped, and in some ways a better one: encounters, weather, vibration and SPS all work for free. But it
means **geography and world-state are coupled through position tables**, so a Path D continent placed at
the old desert's coordinates will read as desert — orange tint, desert encounters — whether or not that
is the design intent.

Two consequences for the arc:
1. A Path D world is never a blank slate; it is disc-1's *semantic* layer with new geometry under it.
2. §8's "defer encounters/minimap/weather" is still right as sequencing, but the reason changes: not
   "they don't exist yet" but "they exist and say the wrong thing."

---

## Research backlog (owner-suggested, separately scoped)

Each is genuinely useful beyond Path D — several are reusable capabilities for the existing two discs.

1. **The position-keyed inheritance census.** Enumerate every system that keys off world position rather
   than the block grid (weather/fog, area/zone, vibration, SPS, encounter tables, minimap, continent
   title) and record, for each, whether Path D wants to inherit / override / suppress it. Highest value —
   it is the real §8 rewrite.
2. **The Cleyra tornado.** A stock, location-triggered set-piece. Understanding how it is spawned and
   positioned is the template for authoring any custom world set-piece.
3. **Airship placement on the world map.** How the dispatcher spawns and parks them; prerequisite for
   putting a custom vehicle anywhere on a Path D world.
4. **Weather / lighting by location.** The orange desert tint and mist are the most visible "sense of
   place" tools available; a Path D continent needs them keyed to ITS geography, not the old one.
5. **World vibration / earthquake zones.** Small, self-contained, and directly reusable.
6. **The four `block.Number` special objects.** Not just to suppress them — this is the stock idiom for
   attaching a fixed object to a named cell, i.e. exactly how to place a landmark on a custom continent.

---

## Dali — the shaping target (recon 2026-07-29)

**Dali is block (17,12).** Three independent sources agree to within ~14 world units: the engine's navipos
landmark table (loc 13), the debug menu's hardcoded "Go to Dhali" teleport, and the hardcoded Dali windmill
world-effect position. Raw fixed-point `(280253, -206433)` ÷256 → world `(1094.74, -806.38)` →
`x = 1094.74/64 = 17`, `z = 806.38/64 = 12`. Finer 32u cell = `(34,25)`, exactly the cell the overworld
dispatcher matches for Dali's entrance. Block `Number` = `12*24+17` = **305**.

**Dali is DEEP INLAND — the single biggest shaping fact.** Of the 121 blocks in a radius-5 window, **96
carry a terrain mesh and only 25 are water**, and there is no deep-sea (topograph 57) triangle anywhere
within radius 3. Water is confined to two lobes: a bay north-west at `y=8..9` (blocks `(12..17,8)`,
`(12,9)`, `(13,9)`) and open sea along `y=17` south of `x=17` plus the eastern margin at `x=21..22,
y=7..10`.

**Four constraints on reshaping here:**
1. **(17,12) is a DOUBLE entrance block** — it holds Dali (case 14, cell 34,25) AND Observatory Mountain
   (case 13, cell 34,24).
2. **Its ring is the densest entrance cluster on the map** — 17 distinct entrance cases inside radius 5,
   including all five South Gate arches, both North Gate arches, Ice Cavern ×2, and the Evil Forest and
   Cleyra scripted triggers.
3. **Chocobo's Forest** sits two blocks south at `(16..17, 14..15)`.
4. Dali's overworld entrance is **field 350** (Village Road), or **359** while `ScenarioCounter <= 2540`.
   Its own fields are 350-359, 400-408, 450-454.

**Mist-off is not free of gameplay consequence.** `w_frameFog` is part of the ENCOUNTER lookup key
(`ff9.w_worldGetBattleScenePtr`), so a mist-free world draws each zone's fog=0 encounter twin instead of
its fog=1 one. Verified there are no table holes near Dali — both twins exist for every walkable topograph
present — but the monsters change: on the topograph-10 ground that dominates block (17,12), battle scene
**247 → 245**.
