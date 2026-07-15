# The BATTLE DIORAMA (B3) — build spec skeleton (2026-07-15, source-grounded recon)

> The last rung of the authoritative-host roadmap: **the guest SEES the host's fight** — a live,
> full-3D rendering of the host's battle on the guest's machine, driven entirely by the wire.
> Sits inside the SPECTATOR-FIELD PARADIGM (PLAN.md): the guest is a combat participant and a field
> spectator; the diorama is where the combat-participant half becomes visual.
>
> **THE LAW: NEVER RE-SIMULATE.** The guest's diorama plays back *choreography*; every number
> (damage, HP, death) is the HOST's result arriving on the wire. The unseeded-RNG re-simulation
> dead-end is documented and closed — do not reopen it.

## What is already proven / on the wire (don't rebuild)

| Piece | Where | Status |
|---|---|---|
| Battle boot by scene id | `BattleUI.cs:144-171`: set `FF9StateSystem.Battle.battleMapIndex` + `patternIndex`, then `SceneDirector.Replace("BattleMapDebug", FadeOutToBlack_FadeIn, true)` | stock debug path, in-game reachable |
| Enemy AI suppression | `HonoluluBattleMain.cs:529`: `FF9StateSystem.Battle.isDebug` true → the `RequestAction(EnemyAtk…)` branch never runs — enemies stand idle | stock |
| Party actor spawn | `HonoluluBattleMain.CreateBattleData:236-259` → `BattlePlayerCharacter.CreatePlayer(btl, PLAYER)` builds a full battle actor from a PLAYER | stock |
| The party's wire data | **state section 1** (NetSyncParty): charId/serial/level/row/hp/mp/equip×5/name per slot — designed as this exact input | ★ two-machine proven (rung 2) |
| Live battle truth | **B0 type-1 frames** (`NetSyncBattle.BattleView`): Seq, MapNo, GuestSlots + per-unit Index/IsPlayer/Alive/Ready/InTrance/HP/MP/ATB/Name, ~150 ms cadence | ★ two-machine proven |
| Guest commands | **B1 type-2 FIFO** command frames + the digit-menu UI | ★ two-machine proven |
| Battle presence signal | `NetSyncBattle.PeerBattleLive` (type-1 freshness) | ★ proven (drives the panel today) |

## What the wire is MISSING (the B3 additions — wire v8)

1. **The battle-intro event** (one-shot, FIFO lane like commands — must not be collapsed):
   `[battleMapIndex u16][patternIndex u8][enemy typeNo u8 × count]` (+ battle BGM id? check what the
   swirl needs). Sent by the host when its battle starts. The guest's own install resolves everything
   else from the scene data (`btlScene.MonAddr[typeNo]` etc. — same bytes, same install).
2. **The action-playback lane** (FIFO): per executed action on the host —
   `[actor unitIndex][cmdId u16][sub_no u16][target mask u16][per-target: damage/heal value + flags
   (miss/crit/death)]`. The guest plays the SEQUENCE (btlseq choreography is deterministic given
   command + result) and prints the HOST's numbers. Source hook: where the host's battle EXECUTES a
   command (find the single choke point — candidate: `btl_cmd`'s execution dispatch; recon TODO).
3. Type-1 stays the continuous truth (HP/MP/ATB/status/death) — the diorama reconciles after every
   playback (drift between a played sequence and the next type-1 frame resolves toward the frame).

## The rung ladder (each stands alone, provable in isolation)

- **B3.0 — boot an empty diorama.** Behind `[Netsync] Diorama = 1`: when `PeerBattleLive` goes true
  (guest side, following), set `battleMapIndex`/`patternIndex` from the intro event, `isDebug = true`,
  `SceneDirector.Replace("BattleMapDebug")`; on battle-end (type-1 says over / PeerBattleLive decays),
  leave back to the field (the follow-warp return recipe). SOLO-PROVABLE: a selftest hook that fires a
  synthetic intro event from the F6 menu (no real peer battle needed).
- **B3.1 — spawn the mirrored party.** Synthesize PLAYERs from state section 1 (candidate:
  `ff9play.FF9Play_New(charId)` then overwrite level/serial/equip/name — the New Game build path; NOT
  the guest's real `FF9.party`, a scratch array fed to a diorama-variant `CreateBattleData`).
- **B3.2 — enemies from the scene.** The intro event's typeNos through the stock enemy-spawn loop
  (`CreateBattleData`'s monster half already does this from `PatAddr` — pattern-driven, may suffice
  with `patternIndex` alone; verify the pattern fully determines typeNos or ship them explicitly).
- **B3.3 — drive the truth.** Type-1 frames → HP/MP/ATB bars, death poses, trance glows on the
  diorama actors (a reconcile tick, ~150 ms — same cadence the panel uses today).
- **B3.4 — action playback.** The new FIFO lane → btlseq choreography + the host's damage numbers.
- **B3.5 — the UI merge.** The B1 digit menus render over the diorama (the OnGUI spectate panel
  retires or becomes the no-diorama fallback); the guest commands its slots from inside the fight.

## Open recon questions (answer before building B3.0)

- The battle-end/return lifecycle on the guest: what `BattleMapDebug` expects to return TO (the
  debug room?) vs the follow-field — likely needs the same deferred-fade return the follow-warp uses.
- Does `isDebug` also gate the PLAYER ready loop / victory-defeat evaluation, or only enemy actions?
  (The diorama wants NO local win/lose — battle end comes from the wire.)
- The swirl/BGM: does `BattleMapDebug` run the full swirl + battle music (wanted) or a bare boot?
- Where the host's action execution has ONE choke point carrying final per-target results.
- The HonoBehavior teardown law applies to every diorama actor (`GeoTexAnim` riders) — teardown via
  `UnregisterHonoBehavior(dispose: true)` only.
- Save-safety: the diorama is render-only (no state writes) — but verify the debug scene doesn't
  autosave or touch `FF9StateSystem.Battle` in ways that leak into the guest's next real battle.

## Status

- 2026-07-15: recon skeleton written (this file). Rungs not started. Wire v8 not cut.
