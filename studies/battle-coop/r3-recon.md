# Battle co-op round 3 — recon after two-machine sitting 2

Input for the round-3 design (`R3-DESIGN.md`). Four read-only recon lanes, run against the deployed
stack s95-s110 (engine `5c8e774adf24395b`). Line numbers are as read on 2026-10-13 and go stale.

## What the owner reported (sitting 2, both logs in hand)

Everything in the package worked except:

1. "the host doesn't get the battle fade-in screen now, they just skip directly to battle. puts it
   slightly out of sync with the guest but still functional."
2. "attack/casting animations don't play on the guest but their effects/damage do go through"
3. New feature for this pass: "the guest still shows as Zidane on the guest machine instead of showing
   as their character (or a moogle if the party only has 1 member)".
4. Untested: all-target / self-target abilities; box 14 (stall hand-back; owner thought ATB Wait was
   why); flee; the shop box.

Logs: three random encounters on field 250 (`diorama BOOT scene=67 ... rand`), boot to
`reconcile live` about 6 s on the laptop each time. Desktop Memoria.ini: `[Graphics] BattleSwirlFrames
= 0` (unchanged since July), `[Battle] Speed = 5`, `SFXRework` default 1.

## Owner decisions for round 3 (asked and answered)

- Scope: **action replay**, **guest model**, **battle-start sync**, **flee + defeat (stage 12)**, plus
  the polish item **Wait-mode parity**. Not this round: hidden-enemy targeting, slot cycling + 3D cursor,
  B4.2 (v15 commands).
- Action replay timing: **damage numbers wait for the replay's hit** (HP bars still follow the host).
- Battle start: **the host holds its gauges until the laptop's battle is live (cap about 8 s) AND the
  laptop plays the same intro the host chose**.

## Lane 1 — the host's skipped intro: a setting, not a regression

- Nothing s95-s110 changed on the host runs during the battle-start fade or intro. `NetSyncBattle.Pump`
  only reads; `TrackCommandPhase`, `TrackHostHold`, `HandBackGuestSlot` require PHASE_NORMAL; every
  fade write is guest-only (`EndTick`, the `FadeInEx(256)` lift in `ApplyReturnSettle`,
  `NetReplayHidden`, the s109 FPSManager call). Desktop Memoria.ini is byte-identical to the pre-F3.3
  backup.
- With `BattleSwirlFrames = 0` the swirl is about 6 frames with a 5-frame fade to black
  (`SFX_Rush.cs:14-15,81,96-104`); `battle.InitBattleMap` runs `FF9Wipe_FadeInEx(32)` (`battle.cs:75`).
- **The intro camera and the actors' delayed fade-in are skipped when
  `cfg.skip_btl_camera == 0 && isRandomEncounter`** (`HonoluluBattleMain.cs:167-168`
  `SFX.SkipCameraAnimation(-1)`; `battle.cs:495` `noDelayFade`). The setting is per save (default 1 =
  don't skip, `FF9CFG.cs:17`; Config UI `ConfigUI.cs:1195,1341`). Debug/harness battles force
  `isRandomEncounter = false` (`Ff9mkDebugMenu.cs:536`) so they always get the full intro.
- The diorama copies the host's random-encounter flag (`NetSyncDiorama.cs:~417`) but applies the
  GUEST's own `skip_btl_camera`, and runs its own swirl/fade from the boot transition (`:511/514`). The
  laptop takes ~6 s from boot to `reconcile live`, so the host's fight is under way first. Stage 8's
  mirrored menu made the gap visible.
- Fix directions: host header flag bit 2 = `skip_btl_camera == 0 && rand` on type 1 (beside bits 0/1,
  `NetSyncBattle.cs:~1110-1117`, additive); the diorama applies that bit instead of its own setting.
  Plus (owner decision) a start hold on the host.

## Lane 2 — no attack/cast animations on the guest: never built

- Type-1 per unit (`NetSyncBattle.cs:~1436-1452`): index, flags (player/alive/ready/trance/hidden),
  HP/MP cur/max, ATB, name, trance gauge. No animation, position or action. Sampled every 150 ms.
- Type-6 per CalcResult (`:~1558-1592`, `QueueActionFrame` `:~1602`, called from
  `SBattleCalculator.cs:331,355` = the IMPACT, not the action start). Carries damage numbers, raw
  HP/MP, a flinch bit, `cmd_no`/`sub_no` ("carried for later", never read on the guest).
- Guest apply (`NetSyncDiorama.cs:~1774-1878`): numbers via `Btl2dReq` (`:1827-1830`), target flinch
  `SetDamageMotion` (`:1843-1844`), `setMotion(MP_ATTACK)` on the actor ONLY for players
  (`:1847-1852`, enemies excluded on purpose `:1845-1846`), raw HP/MP writes (`:1880+`).
- No `SFX.Play` / `btlseq` / `UnifiedBattleSequencer` / `SFXData` anywhere in Netsync. The guest's
  `CommandEngine` and `BattleSubSystem` (incl. `UnifiedBattleSequencer.Loop`) run every frame
  (`battle.cs:244-245,568-576`) — the machinery runs, it is just never fed.
- History: `MP_ATTACK`/`CanPlayCosmeticMotion` only in `s40-netsync-diorama.patch`; scoped to "flinch +
  player-only swing" (`b35-recon.md:253,258`); enemy actor animation an accepted gap
  (`diorama-lane.md:428-429`); box 12 ("flinches + player weapon swings") passed two-machine
  (`diorama-lane.md:685`). s101's `RefuseLocalEnqueue` (`btl_cmd.cs:159-160`) blocks nothing visual.
- **Recommended (B): presentation-only replay.** Host: an "action start" message beside
  `btl_vfx.SelectCommandVfx(cmd)` (`btl_cmd.cs:~624`) carrying actor slot+side, cmd_no, sub_no, target
  mask, ideally the chosen vfx id. Wire without a bump: reuse type 6 with the old actor/target slots =
  0xFF (old guests ignore it, `NetSyncDiorama.cs:1791-1792`), flag bit 2, real fields appended after
  byte 46 (`TryParseAction` checks only a minimum length, `NetSyncBattle.cs:~1774`); do NOT consume
  `_seq`. Guest: a standalone CMD_DATA with `SetAAData(btl_util.GetCommandAction(cmd))` (as
  `btl_cmd.cs:176/416`), never through `SetCommand`/`EnqueueCommand`; run it with `SelectCommandVfx`;
  `btl_cmd.ExecVfxCommand` (`:~1521`) returns early for replay commands — no damage calc, no writes,
  no status, no number pops, at the hit (`UnifiedBattleSequencer.cs:~966`) and on reflect (`:~1078`).
- Risks: needs SFXRework on the laptop (on if `SFXRework` or Speed >= 3,
  `Configuration/Access/Battle.cs:10`); the old sequencer runs one action at a time off `cur_cmd`, so
  gate the replay to SFXRework. Desktop Speed 5 runs actions simultaneously; laptop camera differs if
  its Speed < 3 (`UnifiedBattleSequencer.cs:344,828`). Numbers land about one link delay before the
  replay's hit (owner: hold them until the hit). Idle logic reads `cur_cmd_list` (`btl_util.cs:98`,
  `btl_mot.cs:536-563`). Cancel on actor death; restore `base_pos` and meshes on teardown. Reflect is
  decided from guest statuses (cosmetic). Keep the old swing only when no replay runs for that actor.
- **(A) stopgap / fallback:** choose the clip from cmd_no/sub_no at impact (MP_MAGIC spells, MP_ITEM1
  items, MP_ATTACK attacks; enemies: the matching attack's first animation from the guest's own scene),
  once per action, not per target. No run-up, visuals or sound.
- (C) a per-unit animation/position stream: faithful movement but no visuals/sound; rejected unless
  the laptop cannot run SFXRework.

## Lane 3 — the guest's model

- Ghosts: `EnsureGhost` (`NetSyncClient.cs:~4255-4343`), `DriveGhost` (`:~4449-4479`), the rig table
  `NetSyncVisitor.cs:43-53` (8 mains: model + idle/walk/run/turnL/turnR). `ResolveDress`
  (`NetSyncVisitor.cs:111-150`): "auto" = `party.member[first GuestSlots bit]`; a 1-member party
  returns 0 (`:131-133`) and the host's ghost falls back to the guest's wire model (Zidane). Call sites
  `NetSyncClient.cs:1305-1317` (live), `1180-1191` (selftest).
- What the guest knows on a field: the host's party charIds in type-5 section 1 (`NetSyncParty.cs:110-160`,
  parsed in `ApplyStoryBeforeEvents` `NetSyncClient.cs:~500` via `NetSyncState.cs:101`, right before
  `StartEvents` `HonoluluFieldMain.cs:148-149`). It does NOT know which slot is its own (GuestSlots only
  rides type-1 battle frames, `NetSyncBattle.cs:~1092/1419`). That is the only wire need.
- Player build (field 250 entry 10): `2F[98,93]` SetModel, `33`,`34`,`35`, `7A`,`7B`, `52`, `4B` (collision),
  twelve footstep `88` codes, then `2C` DefinePlayerCharacter last. SetModel creates the GO immediately
  in field mode then AddFieldChar (`DoEventCode.cs:~1084-1126`, incl. Garnet's hair). Anim setters store
  the id and load the clip (`:1134-1190,1662,1951-1961,2086`).
- A Zidane clip on Vivi: `AnimationFactory.AddAnimWithAnimatioName` (`AnimationFactory.cs:54-66`) picks
  the folder from the clip name, so it lands on Vivi's bones: glitch/T-pose, never throws. Substituting
  the dressed idle is safe (`WaitAnimation` waits on afExec; the kit's `neutralize_gestures` proves it).
- Warm battle return rebuilds the GO from `posObj.model` + the actor's idle/walk/run/turn ids without
  re-running setup (`updateModelsToBeAdded.cs:21-28,143-156`; deep copy `NetSyncDiorama.cs:688-709`), so
  a dress made at the opcode survives it.
- Risks: collision radius comes from `4B` (`DoEventCode.cs:1498-1535`), not the model — unchanged (L1
  safe). Eye height (Vivi 61, moogle 50). Per-model light tint (`fldmcf.cs:81`) — reuse the ghost's
  fallback (`NetSyncClient.cs:~4381`). Neck turns (`FieldMap.cs:564`) and mirror reflections
  (`fldchar.cs:62`) are model-keyed (fine). Host-driven cutscenes: the talk relay makes the guest's
  player the listener on its own copy (`NetSyncClient.cs:3499-3517`), so Zidane gesture ids reach the
  dressed model. Mesh show/hide bits (`:1270-1284`) are model-specific: drop for the dressed actor.
  Hand-bone props land on the wrong bone. Footstep `88` codes keyed to anim ids (Vivi walk 571 frames
  4/14, run 419 frames 0/9, from field 100). Two Vivis possible in party cutscenes. A model-keyed rule
  (98/532) could dress a non-player Zidane actor in rare cutscene fields. No ghosts on the world map
  (`onField`, `NetSyncClient.cs:1100`): field mode only.
- **Recommended A: dress at the `SetModel` (0x2F) opcode** gated on mirroring + field mode + the
  player's model (98/532); one helper `SelfDressAnim(actor, id)` for every anim setter and
  RunAnimation (0x40/0xBD): Zidane movement ids → the dressed movement ids, other Zidane-family ids →
  the dressed idle, the dressed character's own ids pass through. Lighting fallback, mesh-op drop.
  Moogle rig row: model 220 `GEO_NPC_F0_MOG` (save moogle), idle 2904, walk 2927, run 2907, turnL 2923,
  turnR 2911 (stock fields 115/150/206). `ResolveDress` "auto" with an empty slot → the moogle. Wire:
  type-5 section 8 `[model u16][charId u8]` filled by the host's `ResolveDress` so both screens agree;
  unknown sections are skipped, so an older guest stays Zidane. The earlier "leave as-is" verdict
  (memory `project-ff9-multiplayer-injector.md:459-462`, HonoBehavior teardown) only bites a mid-field
  re-dress: defer that to the next field load.
- B (proxy over a hidden Zidane, reusing EnsureGhost/DriveGhost): leaks Zidane via the mirror, props,
  neck turns, footsteps, bubble height; a rung-0 fallback only.
- Solo: selftest never mirrors → a knob (`[Netsync] SelfDress=auto|vivi|moogle` or a harness verb
  `netsync selfdress`); the harness publishes no player model/anim today (`HarnessAgent.cs:2167-2194`)
  → add `player.model` / `player.anim`. Field 250 + `game_snap`; `netsync talk <uid>` on a field whose
  NPC animates the player proves the gesture fallback; `netsync dioboot`/`dioleave` proves the dress
  survives the warm return; a 1-member party → moogle.

## Lane 4 — box 14 and Wait mode

- Box 14 did not fail: the README wording was wrong. A slot stays the guest's while
  `(TickCount - _assistTick) < MenuStaleMs` (`NetSyncBattle.cs:307-319`, `MenuStaleMs = 2500` `:66`).
  `_assistTick` refreshes on every valid control frame (`ParseControl` `:2241`, pumped `:887`); the
  guest sends `SetLocalControl(BuildControl(...))` every tick while watching (`:927`) and the socket's
  write thread resends at ~30 Hz (`NetSyncSocket.cs:339,683`) even if the main thread stalls. Only a
  silent lane for 2.5 s triggers the takeover (a short network cut, the guest leaving the battle view
  `:937` null, or the selftest `bench lapse`). Re-test: cut the laptop's network 3-5 s with its window
  open. Takeover/hand-back never read the ATB setting (`BattleHUD.Unity.cs:307-324`,
  `HandBackGuestSlot` `NetSyncBattle.cs:690-745`, root-only `:704`).
- **Wait today:** `RemoteMenuOpen` (`NetSyncBattle.cs:326-337`) makes `IsNativeEnableAtb` return false
  (`BattleHUD.Public.cs:778-781`) and counts as menuing for turn-based in `FF9BMenu_IsEnableAtb`
  (`:759-760`). The control byte means "any guest slot ready" (`:927`; comment
  `NetSyncBattle.StockMenu.cs:1042`), so the guest's window at the ROOT already freezes the host's gauges
  — stricter than stock Wait, which runs at the root (`BattleHUD.Public.cs:786`). Capped at
  `GuestWaitMs = 30000` per open window (`:50,:333`), ends when the lane goes stale.
- Parity hooks: guest `BuildControl` (`:2229-2232`) + its call `:927` to send the window depth (root vs
  Ability/Item/Target); host `ParseControl` (`:2234-2248`) to store it and `RemoteMenuOpen` (`:326`) to
  return true only for submenu/target; the Wait decision `BattleHUD.Public.cs:780` in `IsNativeEnableAtb`
  (callers `HonoluluBattleMain.cs:432`, `btl_sys.cs:355`, `btl_cmd.cs:506`); turn-based at
  `BattleHUD.Public.cs:759-760`. The control payload is 2 bytes on v14: a new value in the existing
  byte avoids a bump.
