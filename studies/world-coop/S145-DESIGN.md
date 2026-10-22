# World-map co-op: battles from the world map (s145)

s144 froze a following guest on the world map. When the host fights there, the guest today gets only the old digit panel.
s145 boots the guest's battle (the diorama, with the real menu) from the world map, and returns the guest to the world map
where it stood. The host's side is unchanged.

The recon (4 read-only lanes plus a critic, with file:line evidence at the s144 clone's lines) is in the session scratchpad
as `recon145.json`. The sites below are its settled answers; the build re-finds each one in the live clone.

## What happens today (s144)

- `DioramaTick` returns at its `if (!onField) return`, so a guest on WorldHUD never boots. `NoteBootWatch` needs gMode 1,
  so the guest reports NONE. The host's start hold never arms ("off a field -- a world-map battle"), and the guest commands
  its party members from the digit panel.
- The boot itself is field-shaped:
  - `PrimeWarmReturn` and `WarmVerdict` want a field (on the world map the log reads COLD, "not on a field");
  - the pre-swirl block suspends the song (the world swirl suspends it again: the double suspend wipes the world song's
    slot), suspends the FIELD resident SFX, and calls `SFX_Rush.SetCenterPosition(0)`, which throws on the world map inside
    the "cosmetic" catch;
  - `LeaveFrom` hard-codes `Replace("FieldMap")`, so a world boot would land the guest cold on the last field it left;
  - `ForceDisarm`'s undo is field-only, and `NoteFieldEventsStart` ignores gMode 3, so a world return is never counted.
- Stock's world battle round trip does nothing to the event context before the battle: no object suspension and no
  `BackupPosObjData` (field-only). The battle's own `StartEvents` copies ctx0 into ctx1. The return's `StartEvents` takes the
  reinit branch (gMode 3, ctx1 inited 3, lastmap == wldMapNo): ctx0 is restored wholesale, entry 0 runs Main_Reinit (tag 10),
  and `EnterBattleEnd` / `ExitBattleEnd` bracket it. The 9 free-roam dispatchers carry tag 10; the event worlds
  9001/9004/9006/9012 do not.

## The decisions (s145)

1. **The host's battle reaches a guest on the world map.** A following guest frozen on WorldHUD boots its diorama there:
   the same diorama as from a field (the real menu, the replay, the cut hold, Wait, flee and defeat, the start sync, the
   leader guard). That includes a host FIELD battle while the guest is on the world map (the source-field hold, a field
   the guest's install lacks, the follow debounce).
2. **Warm only.** The boot does the stock battle `StartEvents`' half itself, `ee.sEventContext1.copy(ee.sEventContext0)`
   (no `BackupPosObjData`), and Leave calls `Replace("WorldMap", FadeOutToBlack)`. The return takes stock's world reinit
   branch: the guest stands where it stood, with its camera, MAP vars and control. **A guest never takes a cold world
   reload** (the Main_Init spawn, MAP vars zeroed). When the warm verdict refuses, the guest does not boot. This retires
   S144-DESIGN's "observe a cold world reload aboard a vehicle first": production never cold-reloads.
3. **A decline keeps s144.** A declined guest stays frozen, sees the digit panel during the fight and the waiting line
   after it, and reports NONE (never DECLINED), so its slots keep s144's digit-panel ownership and `dioramaSeen` never
   rises. Durable refusals are properties of the world visit (an event world without tag 10, a travel mode other than on
   foot, the bee scene, topograph 52 -- a frozen guest cannot step off that cell, so as a wait it held the host's start every
   fight): they set `watching = false` before any nonce is seen, and each declined fight logs one line and counts once. Transient refusals (a transition in flight,
   a dialogue, control off, a reinit bracket still open, the full map) are quiet waits retried the next frame, inside the
   ordinary late-join rules. The watcher runs the pure verdict BEFORE `BootFromWire`, so a refusal is never counted as a boot
   failure (`NoteBootFail` would flip the report to DECLINED).
4. **Vehicles decline.** Aboard a chocobo, boat or airship the guest does not boot: stock never returns a world battle
   aboard (only the on-foot row of `w_moveCHRControl` has encounters), so that return is unexercised. Judged on the live
   `w_moveCHRControl_No`, not on the data (a TransportControls.csv can override `encount`). Lifting it is a later owner
   check.
5. **The world verdict** (pure, ordered cheapest-first, each row a one-line reason): sys mode 3, gMode 3, the scene
   WorldMap, WorldHUD; not the bee scene; on foot; ctx0 is this world's (inited 3, lastmap == wldMapNo & 0xFFFF); ctx1
   inited 0; entry 0 has tag 10 (`GetIP(sid, 10)`), `main.level > 0`; no reinit bracket open (`BattleReturnInFlight`); the
   shared world-transition latch free (read with booted = false: the boot's own `_booted` would otherwise refuse every world
   boot); `w_naviMode != 2`; topograph != 52; no dialogue; control on; a controlled actor. `Boot` re-checks it before `Arm`
   (the backstop for `dioboot` and the ~ menu), so a refusal never writes `isDebug`, `battleMapIndex` or `_booted`.
6. **The boot's world shape** (stock's world battle start), keyed on a boot-time world latch, never on `_warmPrimed`:
   `prevMode = 3`; the Replace FIRST, then, once `IsFading` is confirmed, `IsProcessingInput = false`,
   `IgnoreCheckingDirectionSources = false`, the world audio lanes (the battle song through `BtlBgmMapperForWorldMap` with
   wldMapNo, the SE / stream stops or `StopAllSounds(false)`, and NO own suspend: the world swirl suspends the song itself),
   and `SetCenterPosition(1)`, only on the live WorldMap. **Never write `nextMode = 2` from outside** (a dropped Replace would
   strand the world and wedge the shared latch). The field block stays byte-identical: F3.3's warm field return is the
   regression to guard.
7. **Every stay-on-the-world path undoes**, as a rule: a dropped Replace (fence 1 runs `ForceDisarm` on a live WorldMap),
   Boot's catch and the post-Replace check restore `prevMode`, clear the ctx1 copy, and give back `IsProcessingInput`,
   `IgnoreCheckingDirectionSources` and any paused sound. World liveness reads a boot-time director reference
   (`FindObjectOfType<WMScriptDirector>()`), never `WMScriptDirector.Instance`, whose getter constructs one.
8. **The world-load seam.** A new `BeforeWorldEvents` in `ff9InitStateWorldMap`, right before its `StartEvents`, applies the
   stale-copy law at a world load (a field copy, or a world copy for another wldMapNo, is cleared) and stops a battle song
   still playing over the suspended world song (a mid-fight or stall-cap leave), before the world's music restore.
   `BeforeFieldEvents` clears a world copy at a field load (a stale inited-3 copy there re-adds every modelled actor).
   `NoteFieldEventsStart` accepts gMode 3 and consumes the pending return at the first gMode 1 or 3 `StartEvents`, logging a
   kind mismatch, so a world return is counted on its own load and never on the next field's.
9. **The over-signal.** While booted, the watcher treats section-7 b6 HfWorld (its rising edge after the battle) as "the
   host is back", beside `hostField > 0`, so a world battle whose terminal latch was missed leaves at the settle instead of
   the 8 s stall cap.
10. **After the return** the guest is frozen again from the first world frame (the s144 rising edge), and the rejoin
    resumes. While a world-booted diorama is up, and until its world return has loaded, the follow compares against no field
    (`followFld = -1`). The ~ "Release
    world freeze" survives a world battle round trip: it ends at the next FIELD load, as S144-DESIGN decision 8 says (the s144
    code ended it at any world load; fixed here).
11. **The swirl.** The diorama's swirl clamp (`[Netsync] DioramaSwirlFrames`, default 0) applies unchanged: the stage-0 probe
    below found no short-swirl stall. A bench that sees the agent go quiet on SwirlScene records an instrument row
    (SWIRL-HANG: the logs archived, a frame grabbed, one retry), never an engine verdict.
12. **No new ini knobs.** Calibration is a selftest-only lever, `netsync bench worldwarm off|cold|on`: `off` makes the verdict
    refuse (the guest declines); `cold` boots anyway with no copy, on foot on the benign 9011 only, as the cold reference
    that proves the warm rows can fail. Production never boots cold.

## The engine pieces

**E1. The pure core (inert, `NetSyncDiorama.cs`).** `WorldWarmVerdict` with each row tagged durable or transient; a
kind-aware `ReturnIsOurs(kind, id, loadKind, loadId, sysMode)`; the state (`_bootWorld`, the warm kind and world id, the
boot-time director reference, `prevMode` at boot); the lever static; `HarnessWorldResuming`; the observables (last boot world,
declines and the last decline reason, last return world); the proof line `world diorama selftest: OK (N rows)` (each
disqualifier alone, the latch read with booted false, ReturnIsOurs' world rows, DioramaWatchStep's host_world row, mutants).
No call site changes.

**E2. Boot, Leave, teardown and the world seam (`NetSyncDiorama.cs`, `ff9.cs`).** Decisions 2, 5-8: the pre-Arm refusal;
`PrimeWarmWorld`; the world pre-swirl shape; `ResumeBootAudio` gains the world's paused sounds; `LeaveFrom`'s world Replace;
`ForceDisarm` / `UndoWarm` with the director test and the `prevMode` restore; kind-aware `BeforeFieldEvents`;
`NoteFieldEventsStart` on gMode 3; `BeforeWorldEvents` hooked at `ff9InitStateWorldMap` before `StartEvents`.

**E3. The watcher, the report and the over-signal (`NetSyncClient.cs`, doc lines in `NetSyncBattle.cs`).**
- `DioramaTick(onField, onWorld)`: accept the world at the onField return and WorldHUD at the UI gate; a LIVE
  `WorldTransitionWhy()` (never the `_worldLatch` computed earlier in Update, before the rejoin can arm), `w_naviMode 2` and
  the bee scene as quiet waits; the world pre-verdict before `BootFromWire`.
- `NoteBootWatch`: `watching` uses the LOOSE gMode 3 (a back-to-back fight 2 is watched from inside a world-booted
  BattleMapDebug, where the strict onWorld is false), with the durable refusals setting it false; world `uiFree` covers
  `IsFading`, WorldHUD and the construct frames before WorldHUD.
- `DioramaWatchStep`: the `hostWorld` input and `WatchWhyHostWorld`.
- `followFld = -1` while a world-booted diorama is up; the release lever survives a world load (decision 10).
- A logged bound for the exit ramp's world branch, defence in depth: the verdict makes a reinit-missing return unreachable.

**H. The harness and the ~ menu (additive under protocol 5).**
- `netsync dioboot` accepts a live world map with the latch free (it keeps s144's refusal text for any other scene).
- A `netsync.world.dio` block (boot world, warm or cold, declines and why, returns, last return world, resuming), plus world
  keys: the camera (`cam_rot`, `cam_upper`), the travel mode, `battle_prob` (`w_frameEventBattleProb`: a position-free
  warm/cold witness), a MAP-var digest, `prev_mode`. Sentinels in the catch literal.
- `bench worldwarm off|cold|on` (selftest only, released on every harness release path).
- A `vehicle <mode>` verb through `SetVehicle` (it honours `VehicleAllowByWorld`, never the force override), to reach the
  decline aboard.
- Optionally `DrawDiorama` on the ~ menu's world Go tab.

Every hunk is tagged `[ff9mapkit netsync s145]`, and each file keeps its own line endings. The wire stays v14; the harness
protocol stays 5.

## The bench

A new scenario, `studies/test-harness/scenarios/coop_world_battle.py`, imports coop_world_wait's route and judges (that 2k-line
file and its `slow_leg` registry stay put).

- **Solo, the selftest role** (it never runs the watcher: the solo bench proves the boot and return mechanics only). Route:
  newgame, the party seed, 6603, walk out onto 9011, `bench 0`, walk off the landing, turn the camera, `bench 1` (frozen),
  snapshot A. Rows: the keys and the proof line; `dioboot 359 0 wire` boots warm (boot world 9011, `prev_mode` 3, gMode stays
  3); no "pre-swirl audio replicate failed" line; `dioleave` lands on WorldHUD with the return counted warm on its own load;
  the place (x/z within 4 u of A and away from the landing), the camera, the MAP digest, the travel mode, the music; still
  frozen; `reset` with a world diorama up; the vehicle row (`vehicle 1` on 9011, then the boot DECLINES: never booted, no
  world reload); the lever; WC, the cold reference, last.
- **T2, a real client replaying a tape:** a `COOP_TAPE_WORLD_BATTLE` recorder variant, recorded on the live s144 host (the
  world battle verb, `battle 67 0 rand`, a safe win). The guest pairs on 6603, walks out, is frozen, moves to the Ice Cavern
  tile, and replays the tape: on s144 it stays WorldHUD and reports NONE; on s145 it boots BOOTING then LIVE, its stock menu
  is served, it leaves on `terminal` or `host_world` (never `stall_cap`), returns warm at its spot, still frozen, then rejoins
  300 with no second return counted there. Plus a leg where the host fights on the held field.
- **The duo:** s144's D0-D2, then the host's world battle: the guest boots from WorldHUD and the host's start hold reads
  booting then live; the guest plays; both back on the world map, the guest warm at its spot and frozen; then s144's D3 (the
  rejoin into 300). Optionally the race: the host enters the Ice Cavern within 2 s of its victory, and the shared latch
  serializes the leave and the rejoin.
- **Calibration:** every leg first on the deployed s144 (OLD_PREDICTED), then on s145 with the lever (LEVER_PREDICTED: every
  boot row "declined", never a cold return). Every check can fail, pinned by a fake-driven red test. Re-key s144's stage tests
  by stage where s145 turns an answer, never weaken them; `coop_cut_hold`'s s120-world expectation turns from `stall_cap` to
  `host_world`.
- **The domain tests:** the 18 files of `studies/workflow-perf/GATE-PROFILE.md` plus the s145 files. Intermediate stages run
  `-m "not slow_leg"` plus the s145 files whole; the last stage runs everything once.

## Stage 0: the swirl probe

One of four s144 world-battle-verb starts froze the game right after `LoadLevel("SwirlScene")` (the Unity log ended at "LL2":
the swirl's `UnloadUnusedAssets` never completed; no harness fault, no dropped Replace). The live install's
`[Graphics] BattleSwirlFrames` is 0, Memoria's default, so every battle in ordinary play already takes that short swirl, world
battles included, and none has been reported frozen. The s144 bench wrote the harness state every frame across that swirl.
The probe counted stalls over repeated world battle starts on s144, with no DLL change.

- **Result: 20 of 20 clean** under the frozen run's own conditions: the selftest role, the state written every frame, the
  0-frame swirl, `battle 67 0 rand` on 9011, each fight won and back on WorldHUD. Battle up in 1.1-1.5 s each time.
- With s144's runs that is 1 stall in 26 starts. The 0-frame swirl is Memoria's default and every ordinary world battle
  takes it, so the clamp stays (decision 11), and the stall is a known intermittent to watch.
- The probe and its driver are in the session scratchpad (`probe145/`); the rows are
  `.harness-runs/s145/swirl/results.jsonl` in the main repo.

## Known limits (s145)

- The guest's world map takes none of the host's post-battle story writes (the s144 limit); scripted host world battles
  (WORLD11's quicksand, the Ragtime Mouse) boot like any other.
- A guest frozen aboard a vehicle declines (decision 4); a real chocobo or airship round trip is the owner's two-PC check.
- The JP dispatchers were not scanned; the runtime tag-10 row covers them.
