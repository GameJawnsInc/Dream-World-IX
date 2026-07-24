# Rung 0 — the Festival of the Hunt decode + the actor-budget census (2026-07-24)

Sources: HW field-script exports `C:\gd\FFIX\reference\test2\` (817 files; some exports
repeat the whole script for a second language variant — census parses the FIRST copy only),
`reference/field-manifest.tsv`, Memoria C# source `C:\gd\FFIX\Memoria\` (read-only sweep).

## 1. The Hunt's architecture (fields 550–576, scenario band 3160–3180)

The Hunt is not a dedicated map — it is **the whole Lindblum city, scenario-gated**: every
field 550–576 checks `General_ScenarioCounter >= 3160 && < 3180` (music gate: "Hunter's
Chance", song 111). The three "Lindblum/Festival" manifest rows are: **574** = the pre-Hunt
cutscene (soldiers release five Fang actors into the streets, then `Field(576)`), **575/576**
= Festival square variants (576 carries 18 model actors — the biggest Hunt crowd).
**559** (B.D. Square) is the Zaghnol arena. Fields `test2_679/680/681` (shrines) merely
reuse the music — red herring.

## 2. The timer — GENERIC opcodes, not id-hardcoded C#

`ShowTimer(0|1)` / `ChangeTimerTime(N)` / `GetTimerTime` drive the countdown HUD. Unlike
the Chocobo Hot & Cold dig HUD (C#-gated on literal field ids 2950–2952, see
[[project-ff9-chocobo-hot-cold]]), **the plain countdown clock is available to ANY field,
including a custom id** — a custom minigame gets a real on-screen match clock for free.
The Hunt runs 720s; difficulty/wave tables key on `GetTimerTime` **bands
600/540/480/420/345** (repeated verbatim in Code4 of every hunting field).

## 3. The score economy (the exact variables)

| Var | Meaning |
|---|---|
| `VARL_GenUInt16_314` | **Zidane's real score** (the only fully-earned one) |
| `VARL_GenUInt16_316` | current LEADING score |
| `VARL_GenUInt8_313` | leader **bitmask**: 1 Zidane · 2 Vivi · 4 Freya · 8 Lani · 16 Quina · 32 Belna · 64 Genero · 128 Ivan |
| `VARL_GenUInt16_333/335` | Vivi's / Freya's shadow scores (ceremony + reward payout) |
| `VARL_GenUInt8_312` | "which monster am I fighting" marker, set right before each `Battle()` |
| `VAR_GlobUInt16_36` | the per-monster POINT VALUE consumed by the award path |
| `VARL_GenUInt16_318/320/322` | rival-ticker interval / elapsed / timer-snapshot |

**Player scoring:** the monster's contact handler sets `312 = <type>` → `Battle(0, id)` →
after-battle `Main_Reinit` routes to `Code1_11`, which does `314 += 36` and promotes `316`
if beaten. **Rival scoring is pure theater** (Code5 ticker): every `rand(45..74)` seconds
`316 += (rand%10+5)`-ish scaled points, then a new leader is drawn by RNG **weighted by
timer band** and announced via `SetTextVariable(7, score)` + `WindowAsync` ("X leads with
N points!"). Five of the eight competitors have no state at all beyond the announcement.
**Time-up** (Code7): winner = whoever holds the bit (non-Zidane/Vivi/Freya collapse to
Vivi), full-party heal, `ScenarioCounter = 3180`. **The Zaghnol set-piece** (559
`Main_16`): timer-gated cutscene → party juggling (reserve masks, forced Freya add) →
`Battle(0, 14)` — the exact shape of Fort Condor's "breach → fight the boss for real".

## 4. The monster actor anatomy — the reusable RTS unit

Exemplar: Mu at Main Street 552 (`test2_130`, entries 15–17).

- **Spawn:** normal entry — `SetModel` + `CreateObject(x,z)`, state-dependent spawn position
  (Init branches on a GLOB bool). `SetObjectFlags(7)` = the walk-through class (no push
  collision — the same 3345-use idiom as the co-op plates). Fang is instanced **×5 from one
  model** in 574 — same-model multi-instance is shipped stock.
- **THE CHASE LOOP** (`Mu_15`) — the headline find, an RTS seek behavior in stock opcodes:
  ```
  SetPathing( 1 )
  SetWalkTurnSpeed( 16 )
  while ( !over ) {
      InitWalk(  )
      Walk( GetEntryPosX(250), GetEntryPosY(250) )   // re-target the player's LIVE pos
      Wait( 1 )
  }
  ```
  `250` is the controlled-player UID — but `GetEntryPosX/Y(uid)` takes ANY uid, so this
  generalizes directly to unit-seeks-unit.
- **Engagement radius** — a shared proximity poller (`RunSharedScript(17)` → Entry17):
  `while (…) { if (DistanceWithEntry(UID_24) < 300) { set 312; Battle(0,12) } Wait(1) }`.
  `DistanceWithEntry` is the range-check primitive (also H&C's warmer/colder).
- **Contact handler** — `Function Mu_Range` (tag 2 on the MODEL entry): touching the
  monster fires `Battle()` directly. NOTE: tag-2/Range fires from the PLAYER's collision
  request (EventCollision → CheckNPCInput is controlled-char-driven; cf. the TREADQUAD
  law) — so contact events are player-centric; unit-vs-unit engagement must be
  distance-polling. Verify at rung 1.
- **Despawn/death:** `TerminateEntry(n)` (255 = self) + `StopSharedScript()`.
- **Choreography extras:** `Trick_Sparrow_18` flies parametric Sin/Cos arcs via per-frame
  `MoveInstantXZY` + `SetPitchAngle`, and **carries another monster** (`AttachObject` /
  `DetachObject`, `AttachObjectOffset`) — aerial units and rider/mount composites are
  expressible.

## 5. Engine ceilings (Memoria source sweep)

- **~250 concurrent objects.** `Obj.uid` is a **Byte** (`Obj.cs:127-137`); UIDs 250–255
  reserved (255 = gCur, 250 = controlled, 251–254 = party; `EventEngine.cs:945-950`) →
  ~0–249 addressable. A uid collision **silently disposes** the previous holder
  (`Obj.cs:22-26`). The objlist itself is a growable List (initial 32, no cap;
  `EventContext.cs:11-13,95-103`); model registries are per-uid Dictionaries, no pool cap.
- **255 script entries per `.eb`** (byte entry-count at header offset 3,
  `EventEngine.cs:513`); 255 functions per entry; ≤255 words of locals per entry.
- **The perf hazard is O(n²) collision:** `WalkMesh.Collision` linearly scans EVERY active
  object (`WalkMesh.cs:912-962`) and is called **per moving actor per frame**
  (`FieldMapActorController.cs:762`), plus several O(n) per-frame passes in
  `ProcessEvents`. Many simultaneous MOVERS is the wall, not many objects. (Battle-side
  `_objPtrList = new Obj[8]` bounds battle actors only.)

## 6. The actor-budget census (817 fields, `actor_census.py`)

| metric | p50 | p90 | p99 | max |
|---|---|---|---|---|
| script entries / field | 13 | 23 | 34 | **48** (Cleyra Cathedral 1108) |
| model-bearing actors / field | 5 | 11 | 18 | **23** (Mdn. Sari Kitchen 1607) |
| objects inited in Main_Init | 8 | 20 | 44 | **77** (I. Castle Mural Room 2510) |

- Stock never ships more than **23 model actors** on one field; the Hunt's 576 runs 18.
  A Fort Condor board (≈20 allies + ~10 attackers + player) would exceed every stock
  precedent → the rung-1 bench must prove 30–40 empirically.
- **Runtime (non-Main_Init) `InitObject` spawning is rare but shipped**: 11 fields, led by
  Ice Cavern 303 (12 mid-scene spawns) — the precedent for wave spawning from a
  pre-authored pool.

## 7. The vocabulary map (Hunt primitive → RTS use)

| Stock primitive | RTS use |
|---|---|
| chase loop (`SetPathing` + per-frame `Walk(GetEntryPos*(uid))`) | unit seek/intercept |
| `DistanceWithEntry < r` shared poller | engagement radius, target acquisition |
| `SetObjectFlags(7)` | walk-through units (no pile-up, dodges push physics) |
| `TerminateEntry` / runtime `InitObject` | death / wave spawn (pool + recycle) |
| `ShowTimer`/`ChangeTimerTime`/`GetTimerTime` | match clock + wave scheduling bands |
| `314/316/36`-style score vars + `SetTextVariable`+`WindowAsync` | funds/score + announcements |
| `312` marker + `Battle()` + `Main_Reinit` award path | breach → REAL boss battle (Zaghnol pattern) |
| `AttachObject` composites, Sin/Cos `MoveInstantXZY` flight | artillery arcs, flyers, mounts |

## 8. Open questions → rung 1 (ANSWERED where marked — the swarm bench, ★ 2026-07-24)

1. ★ Frame-rate envelope: **40 movers = no felt degradation** (playtest 3, field 30400,
   top-down 559 fork). The O(n²) concern does not bite at 40 flags-7 movers.
2. ★ 40 simultaneous per-frame `Walk()` re-targets: fine (same playtest).
3. Distance-poll cadence: 40 armed-tier polls/frame fine; UNGATED polls are a CRASH, not
   a cost — **THE PLAYER-REF EVAL LAW** (B_PTR/B_DISTANCEA hard-cast to Actor,
   EBin.cs:1161-73; evaluate only behind a player-alive gate; playtest 1's black screen).
4. ★ Model instancing ×40 (one model): fine. 10+ DISTINCT models still unprobed.
5. Persistent funds readout: still open (popups + the ★-proven generic timer HUD may
   suffice; s-patch only if the design demands it).
