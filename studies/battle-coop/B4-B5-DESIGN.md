# Battle co-op B4 + B5 — build plan: the guest's stock command menu, and victory plus the reward screen

> Status: DESIGN, not built (2026-10-12). Written read-only against the shared Memoria clone
> `C:\gd\FFIX\Memoria\Assembly-CSharp` (HEAD `6b8bb2d5`, the whole netsync stack uncommitted). Paths
> below are relative to that root unless they start with `studies/`, `tools/`, `ff9mapkit/` or
> `memoria-patches/`, which are relative to this worktree.
>
> Inputs: two independent design rounds (B4 and B5, each a native-vs-minimal judgment) and five recon
> lanes (guest command path, diorama, stock HUD, victory pipeline, wire and lifecycle). This pass
> re-read the disputed and load-bearing lines in source, and found six corrections (section 3.8).
>
> Legend: **[V]** = read in source; **[I]** = inferred, not executed. No claim below is an in-game
> observation unless it says so.
>
> Prior art to read with this: `README.md` (roadmap), `diorama-lane.md` (B3), `b34-recon.md` (the
> menu-wake trace, :389/:397), `b35-recon.md`, `b36-round.md`, `inventory-authority.md`; memory
> `project-ff9-multiplayer-injector.md` (B3 .. B3.6, the spectator-field paradigm, F3.3),
> `project-ff9-battle-party-gui.md`, `project-ff9-ngui-menu-construction.md`.

---

## 1. What the owner asked

After the F3.3 two-machine sitting (save moogle, warm battle return, choice by host seq all proven;
the shop box was not run), the owner asked for two battle features:

- **B4 — the guest gets the actual FF9 battle command menu.** Today the guest picks commands for its
  slots through a debug-style text panel driven by digit keys. "The debug functionality works but it
  looks dumb." The ask is the stock command panel, the ability and item submenus and target selection,
  with the stock look and feel.
- **B5 — victory animations, then the battle reward screen on the guest,** ideally following the host's
  inputs, the way the field dialogue lock does: the host drives and the guest's view stays in step.

Topology is unchanged: host on the desktop runs the real fight; guest on the laptop follows
(`FollowHost`) and watches the fight in the diorama (a stock `BattleMapDebug` scene driven by wire
units). `[Netsync] GuestSlots` names the host party slots the guest commands.

## 2. The plan in one screen

- **Both features build on the live diorama, and neither v1 needs a wire bump.** B4 adds one header
  flag bit to the type-1 battle frame. B5 appends a self-delimiting trailer to the same frame. Old peers
  ignore both (section 6.2). The wire stays **v14**. The one future bump (**v15**) belongs to the optional
  full command relay (B4.2), bundled with the comms lane's reserved type 8.
- **B4 mechanism:** the guest's diorama already runs a live stock `BattleHUD`. Its menu never opens only
  because the single `ReadyQueue` feeder is gated behind `!isDebug`. The guest feeds that queue from
  the host's per-unit Ready bit. It captures every stock commit BEFORE `btl_cmd.SetCommand` and forwards
  it as today's v1 command frame. It fills the panels from the host's type-4 roster, not from the
  diorama's stand-in characters. No NGUI is built or cloned.
- **B5 mechanism:**
  - The host publishes an END BLOCK (how the battle ended, plus its result-screen state).
  - The guest injects the stock victory sequence: fanfare, win poses, victory camera.
  - It then opens the stock `BattleResultUI` in a write-nothing replay. The replay shows the host's
    numbers and steps whenever the host's result-screen state steps.
  - It leaves the diorama with the host through `NetSyncDiorama.Leave`.
  - The guest's own Confirm is inert, the same contract as the dialogue lock.
- **Shared foundation:** a host stage that gates the Ready bit and command intake on the live command
  phase. It also fixes two live bugs in today's digit-panel lane: an intro command freezes the fight,
  and a command can land at the victory edge.
- **12 core stages** (one DLL build, one calibrated solo bench and one patch each), then **3 two-machine
  sittings**. Stage 3 is the only go/no-go: the first-ever look at the stock command panels inside
  `BattleMapDebug`. If it fails, B4 goes back to design and B5 continues unaffected.

---

## 3. Recon findings that matter

### 3.1 How the guest commands today

| Finding | Evidence |
|---|---|
| [V] The panel the owner dislikes is an IMGUI text panel, not the `~` debug menu. | `NetSyncClient.cs:4118-4120` `private void OnGUI() { NetSyncBattle.DrawGUI(); ...`; `NetSyncBattle.cs:1698` `AppendMenu(sb, view, mySlot, dioramaLive);   // ALWAYS` |
| [V] Input is digit keys only, read raw from `UnityEngine.Input`, and swallowed from the game while the panel waits. | `NetSyncBattle.cs:1381-1387` ReadDigit; `Global/UI/UIKey/UIKeyTrigger.cs:200` `if (Memoria.Netsync.NetSyncBattle.SwallowAssistKey())` |
| [V] Guest to host is one 9-byte command frame `[1][slot][action 0-4][menu][id u16][mask u16][cursor]` plus a 2-byte control frame `[0][menuOpen]`. | `NetSyncBattle.cs:1465-1483` BuildCommand, `:1485-1488` BuildControl |
| [V] The host validates hard, then queues through `SendNetCommand`. That method passes no `cmdMenu` and refuses the slot whose local menu is open. | `BattleHUD.Unity.cs:617-631`: `if (playerIndex == CurrentPlayerIndex) return false; ... btl_cmd.SetCommand(cmd, commandId, subNo, tarId, cursor);` (stock `SendCommand` passes `cmdMenu: command.Menu`, `BattleHUD.cs:1659`) |
| [V] The per-unit Ready bit is not phase-gated. | `NetSyncBattle.cs:592-593` `ready = hud.ReadyQueue.Contains(index) && !hud.InputFinishList.Contains(index) && !btl_cmd.CheckUsingCommand(d.cmd[0]);` |
| [V] Command intake is not phase-gated either. The harness already learned what that costs. | `NetSyncBattle.cs:1509-1554` (no `_commandEnable` test); `HarnessAgent.cs:739-742` "SendNetCommand will happily queue a command on a unit whose battle is still in its opening camera -- and doing so FREEZES the fight" |
| [V] `ReadyQueue`/`InputFinishList` are cleared only by `InitialBattle` (at `FF9BMenu_EnableMenu(true)`). They therefore carry the previous battle's entries through a later battle's intro, and this battle's entries through victory. | `BattleHUD.cs:1504-1505`; `BattleHUD.Public.cs:762-785` |

### 3.2 Why the live HUD is the B4 surface

| Finding | Evidence |
|---|---|
| [V] `BattleHUD.Update` runs the ready pump BEFORE the diorama early-return. | `BattleHUD.Unity.cs:36-50`: `UpdatePlayer(); UpdateMessage(); if (!_commandEnable) return; ... if (Memoria.Netsync.NetSyncDiorama.Active) return;` |
| [V] The ready loop opens the real panel through `SwitchPlayer` for the first queued slot that is not finished, not unconscious and not guest-owned. | `BattleHUD.Unity.cs:300-328` (`SwitchPlayer(current); break;`) |
| [V] The only `ReadyQueue` feeder has no duplicate guard, and its blink lookup is a LINQ `First()` that throws before `DisplayParty`. | `BattleHUD.Public.cs:657-665`: `if (_unconsciousStateList.Contains(playerId)) return; ReadyQueue.Add(playerId); _partyDetail.GetCharacter(playerId).ATBBlink = true;` |
| [V] Its only caller sits in `ProcessActiveTime`, reached only under `!isDebug`, and the diorama sets `isDebug`. | `HonoluluBattleMain.cs:546`, `:700-703`; `NetSyncDiorama.cs:291` |
| [V] The diorama enters `UIState.BattleHUD` and enables commands at the PHASE_NORMAL flip with no diorama gate. | `Global/UI/UIManager.cs:320-327`; `Global/battle/battle.cs:120-121` |
| [V] The ready loop has an auto-battle branch that commits directly. | `BattleHUD.Unity.cs:320-323` `if (_isAutoAttack) { SendAutoAttackCommand(current); break; }` |
| [I] The command, ability, item and target panels compose and take input in `BattleMapDebug`. Only the party panel has ever been seen there. The debug branch also skips `BattleHUDScene.Loading = true`. | `diorama-lane.md:316-318`; `UIManager.cs:282-290` vs `:320-327` |

### 3.3 Containment: a local commit would re-simulate the host's fight

| Finding | Evidence |
|---|---|
| [V] `CommandEngine` runs ungated in the diorama's main loop. | `Global/battle/battle.cs:244` `btl_cmd.CommandEngine(btlsys);` |
| [V] Under `isDebug` it skips its ATB gate. At execution it consumes the guest's REAL bag and bumps the AA counter. | `Global/btl_cmd.cs:499`; `:619-636` (`IncreaseAAUsageCounter`, `UIManager.Battle.ItemUse(itemId)`) |
| [V] `SetCommand` mutates the caster and plays voice lines before enqueueing, so capture must sit upstream of it. | `btl_cmd.cs:279-298` |
| [V] Stock commit sites: `SendCommand` `BattleHUD.cs:1654`, `SendDoubleCastCommand` `:1667`, `SendMixCommand` `:1681` (its fail path calls `ItemUse` at `:1735-1737` before any `SetCommand`), `SendAutoAttackCommand` `BattleHUD.Unity.cs:591` (own `SetCommand` at `:607`). | quoted: `SendCommand` = `cmd.regist.sel_mode = 1; btl_cmd.SetCommand(cmd, command.CommandId, command.SubId, command.TargetId, command.TargetType, cmdMenu: command.Menu); ... InputFinishList.Add(CurrentPlayerIndex);` |
| [V] Side paths that mutate without a `Send*`: manual trance, AccessMenu/`OpenMainMenu`, the Vivi auto-magic write, and `ForceNextTurn`. | `BattleHUD.Scene.cs:192-205` (`btl.Trance = Byte.MaxValue; btl.AlterStatus(BattleStatusId.Trance);`), `:215-218`, `:576`; `BattleHUD.cs:1650` `caster.Data.cmd[0].info.IsZeroMP = true;`; `BattleHUD.Public.cs:25` |

### 3.4 What the guest cannot compute locally

| Finding | Evidence |
|---|---|
| [V] Each seated stand-in is `FF9Play_New`'d: default preset, `pa[]` all zero. Section 1 carries neither. | `NetSyncDiorama.cs:1019-1021`; `Global/ff9play.cs:135-136` `play.info = new PLAYER_INFO(..., parameter.DefaultMenuType); play.pa = new Int32[...]` |
| [V] Ability rows below max AP are hidden, so a local menu would hide almost every learned ability. | `BattleHUD.cs:1330-1340`, `:818-823` |
| [V] The item list reads the GUEST's bag. | `BattleHUD.cs:676` `foreach (FF9ITEM ff9Item in FF9StateSystem.Common.FF9.item)` |
| [V] The command set reads `party.member[pos].PresetId`, which is not mirrored (and is script-changeable on the host). | `BattleHUD.Const.cs:229`; `EventEngine.DoEventCode.cs:2734-2736` |
| [V] Mid-battle the reconciler mirrors only HP/MP, death, trance and ATB. `bi.target` and NoInput/Silence are not mirrored. | `NetSyncDiorama.cs:1389-1468`; `BattleUnit.cs:34` `IsTargetable => Data.bi.target != 0` |
| [V] The host already ships authoritative per-slot content in the type-4 roster: Attack, Ability1, Ability2 plus one item list. | `BattleHUD.Unity.cs:725-831` (`menus = { Attack, Ability1, Ability2 }` at `:729`); `NetSyncBattle.cs:673-762` |

### 3.5 The stock victory and reward pipeline

| Finding | Evidence |
|---|---|
| [V] PHASE_MENU_OFF hides the HUD only outside debug, then runs the trailing loop. PHASE_VICTORY fades and calls `ManageBattleEnd`. | `battle.cs:132-149`: `if (!FF9StateSystem.Battle.isDebug) UIManager.Battle.FF9BMenu_EnableMenu(false); battle.BattleTrailingLoop(...)` ... `else if (... SEQ_VICTORY_WAIT && ff9Battle.btl_fade_time++ > 32) { return btl_sys.ManageBattleEnd(ff9Battle); }` |
| [V] The per-unit settle check exists for `SEQ_MENU_OFF_VICTORY` and `_DEFEAT`, not for `SEQ_MENU_OFF_VICTORY_WITH_ENEMY` (= 4). Both victory seqs share the tail that stamps VICTORY, plays song 5, enters PHASE_VICTORY and calls `SFX.SetCamera(2)`. | `battle.cs:300-306`, `:379-418`; `FF9StateBattleSystem.cs:22-29`. The only `WITH_ENEMY` writers are `battle.cs:201` and `btl_scrp.cs:792` |
| [V] The trailing loop still waits on SFX and the command queue. | `battle.cs:291-292` `if (SFX.IsRunning() \|\| btlsys.cmd_queue.next != null \|\| btlsys.cur_cmd != null) proceedEnd = false;` |
| [V] `ManageBattleEnd` fires the end-battle achievement with no diorama gate. | `FF9/btl_sys.cs:187-189` `if (ff9.btl_result == FF9StateGlobal.BTL_RESULT_VICTORY \|\| ...) BattleAchievement.UpdateEndBattleAchievement();` |
| [V] The achievement funnel is gated only on `IsMirroringStory`, but a diorama may boot under `IsLiveFollowedSession` or selftest. | `Assets/SiliconSocial/AchievementManager.cs:110`; `NetSyncDiorama.cs:139-140` |
| [V] The result screen is the reward WRITE: exp/level, `pa`, gil, bag and cards. | `Global/battle/Result/BattleResultUI.cs:558`, `:620/:625`, `:641`, `:700`, `:715`, `:722` |
| [V] Its exit bypasses `Leave`. | `BattleResultUI.cs:44-56` `... mode = prevMode; ... if (mode == 3) SceneDirector.Replace("WorldMap", ...) else if (mode == 5 \|\| mode == 1) SceneDirector.Replace("FieldMap", ...)` |
| [V] Only `OnKeyConfirm` moves it between states, and `None` (8) sorts after `Hide` (7). | `BattleResultUI.cs:75-153`; `:979-990` |
| [V] A Confirm sent through the base class answers the quit prompt if one is up. | `Global/UI/UIScene.cs:108-118` `if (... QuitScene.isShowQuitUI) { ... QuitScene.OnKeyConfirm(go); return false; }` |
| [V] Game Over goes to the title with no gMode write. | `Global/Game/GameOverUI.cs:44-58` `SceneDirector.Replace("Title", SceneTransition.FadeOutToBlack_FadeIn, true);` |
| [V] `GoToBattleResult` is one-shot per HUD show. `_oneTime` is reset in the ctor and in `BattleHUD.Show`, so a guest replay can fire once per diorama. | `BattleHUD.Public.cs:65`, `:681-706`; `BattleHUD.Scene.cs:59` |

### 3.6 What the guest sees today at the host's win

| Finding | Evidence |
|---|---|
| [V] The guest stays in PHASE_NORMAL. There are no poses, no fanfare and no result screen, and the HUD stays up. | `btl_sys.cs:61`, `:157` (CheckBattlePhase and CheckForecastMenuOff return on Active); `battle.cs:185` (R1); `HonoluluBattleMain.cs:700-712` (IsOver needs `!isDebug`) |
| [V] The host's type-1 lane stays live through its victory and its whole result screen, so the guest leaves only about 2 s after the host is back on the field. | `NetSyncBattle.cs:520-530` InOwnBattle (gMode 2/4); gMode writers only `EventEngine.cs:581-596`, `EventEngine.Initialize.cs:24-29`. [I] that players stay linked in `btl_list` through the result screen |
| [V] The laptop log shows boot at 19:09:17, "reconcile live" at 19:09:24 (the intro), and a stale-lane leave plus warm return at 19:09:44. | `laptop-Memoria.log:101-110` (package `FF9Coop-laptop-update-20261012b`) |

### 3.7 Wire and lifecycle facts the design leans on

| Finding | Evidence |
|---|---|
| [V] Wire v14. An unknown type is dropped silently because `Accept` has no default case. | `NetSyncSocket.cs:132` `public const Byte Version = 14;`; `:346-394` |
| [V] `ParseView` reads exactly `count` units and ignores trailing bytes. Its whole-frame catch returns null. | `NetSyncBattle.cs:824-872` (`for (Int32 i = 0; i < count && i < 8; i++)` ... `catch (Exception err) { Log.Error(err, "[NetSync] bad battle-state frame"); return null; }`) |
| [V] Header flags carry only bit 0 today. | `NetSyncBattle.cs:560-561` `Byte flags = 0; try { if (FF9StateSystem.Battle.isRandomEncounter) flags \|= 1; } catch { }`; decode `:837-838` |
| [V] The per-Update order is Pump, then ActionTick, then DioramaTick, then ReconcileTick (DRAIN-BEFORE-RECONCILE). The selftest branch runs `SelfTestPump` instead. | `NetSyncClient.cs:1337-1352`; `:1118` |
| [V] `Leave()` is request-only, stamps the leave intent, and DEFERS while a fade is in flight. | `NetSyncDiorama.cs:442-470` (`if (sd != null && sd.IsFading) { Log.Message("... leave deferred ..."); return; }`, then `_leaveTick = Environment.TickCount;`) |
| [V] A teardown after a non-watcher `Leave` stamps the skip nonce through the "leave noted" branch, but only when the watcher booted the diorama. | `NetSyncClient.cs:1430-1468`; `_dioramaWireNonce` is written only at `:1646` |
| [V] Commands are drained only while the host is in its own battle, with no battle nonce. | `NetSyncBattle.cs:355-361` |

### 3.8 Corrections found during this merge pass

1. **R9's slot scope does include some status-script enqueues** [V]. `BattleUnit.ATBCommand` is `cmd[0]`
   (`Memoria/Battle/Calculator/BattleUnit.cs:320`), and Berserk and Confuse enqueue on it
   (`BerserkStatusScript.cs:33`, `ConfuseStatusScript.cs:36`). Garnet's trance phantom recast enqueues on
   `cmd[3]` (`TranceStatusScript.cs:107`), and a battle script can enqueue `SummonEiko` on `cmd[0]`
   (`btl_scrp.cs:566`).
   - The B4 design's rationale ("status scripts untouched") is therefore wrong for those.
   - In a diorama all of them would be re-simulation, so refusing them is the desired outcome.
   - The stage 2 receipt (`r9_refused == 0` in a plain diorama) still holds, because those statuses are
     not mirrored mid-battle.
   - What the scope genuinely leaves alone is `cmd[4]` SysTrans, `cmd[1]` counters and `cmd[2]` SysStone.
2. **`Leave()` defers during any SceneDirector fade** (`NetSyncDiorama.cs:449-453`). B5's end-leave must
   retry (its 1 Hz rate limit does) and log the deferral once. It must not depend on a single call
   landing.
3. **The "same fight never re-boots" proof is two-machine only.** The skip nonce is stamped from
   `_dioramaWireNonce`, which only the production watcher sets (`NetSyncClient.cs:1646`). `dioboot` and
   `WireBenchBoot` leave it at -1, so a solo bench cannot assert the stamp.
4. **`HandleCommandPayload` is not as silent as reported.** It already logs three refusals: not a guest
   slot, absent or KO, and not awaiting input (`NetSyncBattle.cs:1517-1553`). The silent returns are
   `mask == 0`, a null HUD or battle system, and the per-action failures after the ready gate.
5. **`_oneTime` is re-armed at every `BattleHUD.Show`** (`BattleHUD.Scene.cs:59`). The guest's replay
   variant of `GoToBattleResult` therefore fires once per diorama, and needs no reset of its own.
6. **The B4 round assumed B5 would own a v15 bump.** The B5 round then showed its trailer needs none
   (`ParseView` ignores trailing bytes). Merged result: no bump for either v1 (section 6.2).

---

## 4. Merged B4 design — the stock command menu on the guest

### 4.1 Shape

Three seams on the LIVE diorama `BattleHUD`:
- **(a) OPEN:** feed `AddPlayerToReady` from the wire Ready bit.
- **(b) FEED:** panel content comes from the host's roster.
- **(c) CAPTURE:** every stock commit is forwarded instead of executed.

Because no NGUI is built or cloned, the PRESERVE-THE-BAKE and SCROLL-SUM laws are not engaged. Only the
list-refresh cursor-beep law applies: hold `ButtonGroupState.MuteActiveSound` around a rebuild.

Base design: the MINIMAL candidate. The wire stays v14 and the host reuses `SendNetCommand`, which
already patches per slot. It carries seven grafts:
- **G1** a scoped R9 backstop;
- **G2** `IsGuestOwnedSlot` false while Active;
- **G3** a gentler hand-back;
- **G4** a `bi.target` overlay for hidden enemies (polish);
- **G5** a capability bit;
- **G6** Ready excludes the host's own open slot;
- **G7** a per-slot digit fallback.

The NATIVE candidate's full CommandDetail relay is deferred to B4.2. It would refactor the vanilla
`Send*` bodies, which carry hidden `CurrentPlayerIndex` reads (`BattleHUD.cs:2398-2401`, `:1656`,
`:1766`, `:688`); swap the guest's real `FF9.item` by reference; and force a bump.

### 4.2 Predicates (layered on purpose)

- **Containment** = `NetSyncDiorama.Active` (`NetSyncDiorama.cs:71-79`). It is false in every real
  battle on both machines. All capture and side-path gates key on this alone.
- **Content** = `NetSyncBattle.IsMirroredSlot(L)` = Active && local slot L belongs to the mirror.
- **Ownership** = `StockMenuOwns` = `GuestStockMenu` && Active && (`NetSyncParty.MirrorActive` ||
  bench armed) && `view.HostCaps` bit 1 && !faulted. `MirrorActive` is required: without it the
  diorama seats the guest's own party (`NetSyncDiorama.cs:987-988`), and the wire-to-local mapping is
  meaningless.

### 4.3 Containment (stage 2 and stage 3)

**R9, the scoped backstop** at the head of `btl_cmd.SetCommand` (`btl_cmd.cs:153`):

```csharp
if (Memoria.Netsync.NetSyncDiorama.Active && cmd.regist != null && cmd.regist.bi.player != 0
    && (cmd == cmd.regist.cmd[0] || cmd == cmd.regist.cmd[3]))
{ Memoria.Netsync.NetSyncDiorama.NoteRefusedEnqueue(cmd, commandId); return; }   // log once per (boot, cmd_no); count
```

Capture is the primary layer, and R9 turns a missed site into a logged refusal instead of a
re-simulation. See 3.8 item 1 for what the scope covers.

**Capture**, Active-keyed, at the TOP of each commit site:
- `SendCommand` (`BattleHUD.cs:1654`) and `SendDoubleCastCommand` (`:1667`) go through
  `NetCaptureCommit`. Double-cast forwards the first detail only, so it casts once, as today.
- `SendMixCommand` (`:1681`): SFX 102 and refuse, before the fail-path `ItemUse` at `:1735`.
- `SendAutoAttackCommand` (`BattleHUD.Unity.cs:591`): forward Attack at the first live enemy, never
  reaching `:607`.
- `SelectViviMagicInsteadOfAttack` (`BattleHUD.cs:1593`): early return when Active. It runs inside
  `ProcessCommand` before any `Send*` and writes `IsZeroMP` (`:1650`).
- Manual trance: `triggerManualTrance &= !Active` (`BattleHUD.Scene.cs:192`).
- `OpenMainMenu` (`BattleHUD.Scene.cs:576`): SFX 102 and return before any state write. This one gate
  covers AccessMenu, `OnKeyMenu` and the main-menu party swap.
- `CanForceNextTurn` (`BattleHUD.Public.cs:25`) gains `&& !NetSyncDiorama.Active`.
- `ForceDisarm` (`NetSyncDiorama.cs:480`) clears `BattleHUD.ForceNextTurn`, whose only reset is in
  `ProcessActiveTime`.

```csharp
private Boolean NetCaptureCommit(CommandDetail c) {
    CharacterCommand cc = CharacterCommands.Commands[_currentCommandId];
    Int32 id = cc.Type == CharacterCommandType.Ability ? (Int32)cc.GetAbilityId(_currentSubMenuIndex) // UNPATCHED: the host patches per slot (Unity.cs:692-701)
             : cc.Type == CharacterCommandType.Item ? c.SubId : 0;
    if (!Memoria.Netsync.NetSyncBattle.ForwardStockCommand(CurrentPlayerIndex, (Int32)_currentCommandIndex,
            (Int32)cc.Type, id, c.TargetId, c.TargetType))
    { FF9Sfx.FF9SFX_Play(102); return false; }
    SetPartySwapButtonActive(false); InputFinishList.Add(CurrentPlayerIndex); _partyDetail.SetBlink(CurrentPlayerIndex, false);
    return true;   // the stock SetIdle / SFX 103 flow continues
}
```

`ForwardStockCommand` maps commands to v1 actions:
- Attack → ActAttack; Defend → ActDefend.
- Ability-type Ability1/2 → ActAbility(menu, unpatched id).
- Normal- or Instant-type → ActInstant(menu).
- Item → ActItem(id).
- Anything else returns false, and the command shows greyed (4.5).

Target mapping:
- Player caster and target bits map local to wire through character id, built on `ResolveWireUnit`
  (`NetSyncDiorama.cs:1335-1359`), never `GetIndex`.
- Enemy bits 4-7 are identity. Group masks 0x0F/0xF0/0xFF pass verbatim.
- The stock `GetSelectMode` 0/1/2 (`BattleHUD.cs:2426-2431`) is the v1 cursor.

Bytes come from an `EncodeCommand` extracted unchanged from `BuildCommand`. They go into an outbox
(cap 8) that the Pump guest branch drains.

**G2:** `IsGuestOwnedSlot` (`NetSyncBattle.cs:213`) returns false while Active. On a two-machine guest
it is already false, because `_assistTick` is stamped only host-side or in selftest. In selftest,
`SelfTestPump`'s `ParseControl` would otherwise make the diorama HUD skip the very slot the bench
opens (`BattleHUD.Unity.cs:317`).

### 4.4 Host rules

The host rules are the shared stage 1 (section 6.1), plus G6 and the hand-back at stage 11 (4.7).

### 4.5 Content hooks (stage 7): mirrored slots only; the host's type-4 roster is the truth

1. **Command resolution.** `ResolveMenuCommand` inside `GetCommandFromCommandIndex`
   (`BattleHUD.Const.cs:226-240`) and in the `DisplayCommand` loop (`BattleHUD.cs:442-447`). Use the
   roster's cmdId only when it is NOT one of the local preset's patched {normal, trance} variants for
   that menu, which is the script-changed preset case. Otherwise keep the local value, which is
   trance-exact because the reconciler mirrors the Trance bit.
2. **Greyed commands.** `ClampMenuState` after `:446` sets state 1 (grey) for Change, Throw-type, Mix and
   AccessMenu. The manual-trance label branch (`:451`) is skipped for mirrored slots.
3. **Ability state.** Early return at the top of `GetAbilityState` (`BattleHUD.cs:1318`):
   `RosterAbilityState(slot, abilId, menu)` converts the ability index to the active id
   (`ff9abil.GetActiveAbilityFromAbilityId`, as `:1325` does). Present → Enable or Disable by its flag;
   absent → None, which renders a blank row exactly like stock. This one hook covers list rows, the
   confirm check (`BattleHUD.Scene.cs:303`) and `DisplayAbilityRealTime`.
4. **Item list.** `DisplayItem` (`BattleHUD.cs:676`) enumerates `RosterBag(slot) ?? FF9.item`, as
   `new FF9ITEM(id, count)`.
5. **Item count at target time.** `ManageTargetCommand` (`BattleHUD.Unity.cs:463`) uses
   `RosterItemCount`. These are the only two bag reads on the menu path.
6. **Single cast.** `IsDoubleCast` and `IsMixCast` (`BattleHUD.Public.cs:23-24`) read false for a
   mirrored `CurrentPlayerIndex`, so a double-cast command makes one pick.
7. **Repaint on change.** `NetRefreshMenus()` on a roster byte change, under `MuteActiveSound`:
   `DisplayCommand` if the command group is active, `DisplayAbility` if the ability panel is open, and
   `_needItemUpdate = true`.

Not hooked, on purpose: the target-time MP and CannotUseMagic checks (`BattleHUD.Unity.cs:443/453`). A
divergence bounces back to the list with stock SFX 101, or the host refuses. It never commits locally.

### 4.6 The guest ready mirror (stage 8): `NetSyncBattle.StockMenuTick()`

**Call sites:** after `NetSyncDiorama.EndTick()` (section 6.3) in the transport branch, and in the
selftest branch after `SelfTestPump` (`NetSyncClient.cs:1118`). The second call is load-bearing,
because the selftest branch never reaches Pump or ReconcileTick.

**Gate:** `StockMenuOwns` && `PeerBattleLive` && view != null && local `btl_phase == PHASE_NORMAL` &&
`LOAD_INITNPC|LOAD_INITCHR` both set && `hud.FF9BMenu_IsEnable()` && `UIManager.State == BattleHUD`.
If the gate fails: `CloseAll()`.

**Per wire player unit u with a `view.GuestSlots` bit:**
- **Map it.** `L = LocalIndexForWire(u.Index)`. If L is unresolved: mark the slot stranded, log once,
  continue.
- **Decide.** want = `u.Ready && u.Alive && roster has u.Index`.
- **If a command is pending:**
  - Ready falls, or `view.Nonce` changes: the command is accepted or obsolete. Clear pending and run
    `RemovePlayerFromAction(1<<L, true)`.
  - Ready is still up after at least 2500 ms AND at least 3 seq advances: refused or lost. Run
    `RemovePlayerFromAction`, then `AddPlayerToReady(L)`, SFX 102 once and one log line.
- **Else, want && not queued:** `AddPlayerToReady(L)`, guarded by `!ReadyQueue.Contains(L)`. If
  `_unconsciousStateList` refuses it silently (`BattleHUD.Public.cs:659`), mark the slot stranded and
  log once (G7).
- **Else, !want and L is queued or finished:** if `CurrentPlayerIndex == L`, `SetIdle()` first; then
  `RemovePlayerFromAction(1<<L, true)`. Pass a power of two only: the loop at `Public.cs:672-674` never
  ends otherwise.
- **Any exception:** set `faulted`, `CloseAll`, log once. The digit panel returns.

**Digit panel after stage 8:**
- The control frame is unchanged: `BuildControl(FirstReadyGuestSlot(view) >= 0)`.
- The digit UI serves only `assistSlot`, which is the first ready guest slot that is stranded, or any
  slot when `!StockMenuOwns`.
- `AssistInputActive = assistSlot >= 0`.
- `DrawGUI` draws the menu half only for `assistSlot`.

**Config:** `[Netsync] GuestStockMenu` (default 1). Parse it next to `DioramaSwirl`
(`NetSyncClient.cs:756`) and add it to the behaviour signature `bsig` (`:802`), so an edit applies
live and never tears the session down (the config-signature teardown law).

### 4.7 Guest-slot hand-back (stage 11, host): BTL-1

- **G6:** the host's Ready bit also requires `hud.CurrentPlayerIndex != index`. While the host's local
  menu holds a slot, the guest's window stays closed instead of buzzing refusals.
- **G3, root-only hand-back.** After `ParseControl` (`NetSyncBattle.cs:360`, `:495`):

  ```csharp
  if (hud.CurrentPlayerIndex >= 0 && IsGuestOwnedSlot(hud.CurrentPlayerIndex)
      && ButtonGroupState.ActiveGroup == BattleHUD.CommandGroupButton) { hud.SetIdle(); /* log */ }
  ```

  Mid-submenu, the host finishes its own pick.

### 4.8 Deferred to B4.2 (the one v15 round)

All of these ride one wire bump, coordinated with comms type 8:
- A v2 command frame carrying CommandDetail(s): double-cast `cmd[3]+cmd[0]`, Mix, Throw, Change, manual
  trance and auto-battle. It also carries a battle nonce and a per-slot turn token.
- Ack codes on type 1.
- Control v2 with seq (BTL-2, BTL-3).
- `cmdMenu` passed together with a command-context host validator. Passing `cmdMenu` alone would make
  the validator (`BattleHUD.cs:1361-1363`, context-free) and the executor (`btl_cmd.cs:1191`) disagree.

---

## 5. Merged B5 design — victory and the reward screen

### 5.1 Shape

Base design: the MINIMAL candidate. The replay writes nothing, enforced at every write site. It follows
the host's result STATE (a latest-slot value), and the learned-ability schedule is computed on the
host. So it stays safe even with the guest's REAL party seated. Victory is injected through
`SEQ_MENU_OFF_VICTORY_WITH_ENEMY`, which has no per-unit settle (3.5), so a linked but host-hidden enemy
cannot stall it.

Grafted from the NATIVE candidate:
- leave on the host's Game Over or Title;
- the quit-prompt guard;
- open the replay only after the guest's own fade (first R8 hit);
- carry the host's Loading bit;
- widen the achievement funnel to `Booted`;
- stamp the host's `btl_result` before leaving.

Rejected from the native candidate: exact-press following, `SetDisappear` settling, stand-in seeding
(writes PresetId and resizes `pa[]`), the 6 s stale-leave grace, and a GameOverUI replay in v1.

New in the B5 round:
- `CLOSE + DEFEAT` classified as Defeat;
- the trailer parsed in its own try;
- `None` excluded from the chase;
- change-triggered sampling instead of input taps;
- the phase guard placed before the ownership check.

### 5.2 Host end block (stage 4)

`SampleOwnBattle` (`NetSyncBattle.cs:532-624`) appends `NetSyncEnd.WriteEndTrailer(bw)` after the
count backpatch. The layout is in section 6.2.

```csharp
static Byte ClassifyEnd(Byte ph, Byte seq, Byte res) {
  switch (ph) {
    case PHASE_MENU_OFF: return seq==SEQ_MENU_OFF_VICTORY||seq==SEQ_MENU_OFF_VICTORY_WITH_ENEMY ? KVictoryPending
                             : seq==SEQ_MENU_OFF_DEFEAT ? KDefeat : seq==SEQ_MENU_OFF_ESCAPE ? KEscape
                             : KEvent;                       // seq 2 = var 32 / auto-end transient: NOT an end
    case PHASE_VICTORY:  return KVictory;
    case PHASE_DEFEAT:   return KDefeat;
    case PHASE_CLOSE:    return res==VICTORY||res==VICTORY_NO_POSE ? KVictoryNoPose : res==ESCAPE ? KEscape
                             : res==DEFEAT||res==GAMEOVER ? KDefeat : KOtherEnd;   // INTERRUPTION, ENEMY_FLEE
    case PHASE_EVENT:    return KEvent;
    default:             return KFighting; } }
```

Why each branch is needed [V]:
- `btl_scrp.cs:786-799`: var 33 with val ≠ 1 lands in PHASE_CLOSE carrying that result. A scripted
  DEFEAT is CLOSE + 3.
- `btl_scrp.cs:774-784`: var 32 parks the host in MENU_OFF/EVENT with result 0. Treating that as an end
  would freeze the guest, because the reconciler quiesces outside NORMAL (`NetSyncDiorama.cs:1288`).

**Change-triggered sampling.** `Pump` (`NetSyncBattle.cs:311`) and `SelfTestPump` (`:443`) compare a
cheap per-frame key (phase, seq, result, ui, resState with Loading) with the last sample. On any change
they sample immediately instead of waiting out `SampleMs`.
- Every result state lives at least 100 ms (the BattleAutoConfirm repeat, `UIKeyTrigger.cs:654-675`),
  so the 33 ms writer sends each one [I].
- The extra samples consume `_seq` like any state write.

**Host side of the result state.** `BattleResultUI` becomes `partial`, with only a
`NetStateRaw | (Loading ? 0x80 : 0)` accessor at this stage.

### 5.3 Guest end presentation (stage 5): `NetSyncDiorama.EndTick()`

**Gates:** `_booted && Active`, a `PeerEnd` from `NetSyncBattle.TryGetPeerEnd` (the live seq-advanced
view, or the bench seam), and `e.Bench || e.Nonce == BootedWireNonce`.

**InjectEnd, once per boot.** It requires load latched, `btl_phase == PHASE_NORMAL` and a terminal kind.

```csharp
Memoria.Netsync.NetSyncBattle.StockMenuCloseAll("end injected");   // B4 coupling: SetIdle + drain ReadyQueue/InputFinishList
UIManager.Battle.FF9BMenu_EnableMenu(false);          // battle.cs:133's hide is !isDebug-gated
b.btl_escape_key = 0; b.cmd_status &= 0xFFFD; btl_cmd.KillAllCommand(b);
for (BTL_DATA n = b.btl_list.next; n != null; n = n.next) n.bi.cmd_idle = 0;
switch (kind) {
  case KVictoryPending: case KVictory:                 // stock tail: fanfare 5, poses, SFX.SetCamera(2)
      b.btl_phase = PHASE_MENU_OFF; b.btl_seq = SEQ_MENU_OFF_VICTORY_WITH_ENEMY; break;
  case KVictoryNoPose: case KOtherEnd:                 // battle.cs:151-175 fade path
      ff9.btl_result = hostResult==VICTORY ? VICTORY_NO_POSE : hostResult;
      b.btl_phase = PHASE_CLOSE; b.btl_seq = SEQ_DEFEATCLOSE_FADEOUT; break;
  case KDefeat: case KEscape: break;                   // v1: HUD off, hold, keep reconciling; stage 12 injects these
}
```

**R8** at the top of `btl_sys.ManageBattleEnd` (`FF9/btl_sys.cs:169`):

```csharp
if (Memoria.Netsync.NetSyncDiorama.Active) { NetSyncDiorama.NoteR8(); return 1; }
```

- Without it, `:187-189` (the end-battle achievement) and `:175-180` (DEFEAT rewritten to GAMEOVER)
  would re-fire every frame at the WAIT seq, because `IsOver` never sets.
- The return value is irrelevant: `HonoluluBattleMain.cs:699-712` reads it only under `!isDebug`.
- The FIRST R8 hit is the "guest's own presentation is done" signal.

**Achievement funnel:** `AchievementManager.cs:110` becomes
`if (IsMirroringStory || NetSyncDiorama.Booted) return;`.

**Watchdogs (one log line each):**
- **W1:** PHASE_VICTORY + `SEQ_VICTORY_CAMERA_MOVE` for more than 4 s after the host's ui ≥ 1. Action:
  `btl_seq = SEQ_VICTORY_FADEOUT`. This covers the [I] case where the native camera callback (code 110,
  `SFX.cs:874-876`) never fires in `BattleMapDebug`.
- **W2:** PHASE_MENU_OFF for more than 8 s after injection. Action: name the blocker (SFX, `cmd_queue`,
  `cur_cmd`, song sync) and force the next stock phase.

**DrawGUI:** returns early when `EndInjected`.

### 5.4 Guest exit with the host (stage 6)

**Trigger:** `hostExit = (ui==1 && (resState&0x7F)==Hide) || ui==2 || ui==3`, rate-limited to one
attempt per second (3.8 item 2: `Leave` may defer).

**Sequence:**
1. If a replay is open (stage 10), wait up to 5 s for the chase to reach Hide.
2. `NetAbortReplay()`.
3. Stamp `ff9.btl_result` with the host's final result. NO_POSE becomes VICTORY; GAMEOVER and INITIAL
   are skipped. `btl_result` is RAM-only and is outside the diorama Snapshot
   (`NetSyncDiorama.cs:1180-1214`), so the stamp survives teardown. This closes the F3.3 residue: the
   warm return read `GetBattleResult` 0.
4. If a victory was injected and the replay did not already shut the songs:
   `battle.ff9ShutdownStateBattleResult()`, so the fanfare never bleeds onto the field.
5. One log line, then `Leave()`. The teardown stamps the skip nonce through the "leave noted" branch
   (`NetSyncClient.cs:1462-1468`).

**Late join:** in `DioramaTick`, after `if (nonce == _dioramaSkipNonce) return;`
(`NetSyncClient.cs:1595-1596`), a terminal peer end kind stamps the skip and logs once. The guest does
not boot a finished fight.

`Leave()` and `ForceDisarm()` also call `NetAbortReplay`, which stops SFX loops 105/109.

### 5.5 Host result manifest (stage 9)

**Capture point:** the tail of `InitialNormal` (`BattleResultUI.cs:372`) calls
`if (!_netReplay) NetSyncEnd.HostCaptureManifest(this)`.
- That point is after `GoToBattleResult`'s 'BattleEnd' and `InitialInfo`'s 'RewardAll'/'RewardSingle'
  support-ability triggers, so the values are post-SA.
- It is before any exp/`pa` write (`UpdateExp`/`AddAp`).

**Contents:**
- **Per RAW party slot:** charId, needExp/needAp/drawEnabled, levelBefore, levelAfter (a pure loop over
  `ff9level.CharacterLevelUps`), expBefore, expGain, apGain, status.
- **Learn schedule:** `AddAp`'s loop (`:596-633`) replayed on a CLONE of `pa[]` in 1-AP steps, giving
  (abilId, apAt). It is capped at 9999 steps.
- **Totals:** defaultExp, defaultAp, gilGain, gilBefore, ≤ 6 items, the card.
- **Overflow:** a sticky item-overflow bit set from the host's `UpdateItem`.

Everything is wrapped in try/catch; null means the guest holds black and leaves on Hide.

### 5.6 Guest result-screen replay (stage 10)

**Arming conditions:**
- injected and `R8Hits > 0`;
- host ui == 1 with a manifest, not AfterEvent, resState ≠ Hide;
- guest `UIManager.State == BattleHUD`;
- at least one valid row, where valid means `member[i] != null && member[i].info.slot_no == row.charId`.

Then `NetSyncEnd.ArmReplay(m)` and `UIManager.Battle.NetGoToBattleResultReplay()`. That method is
`GoToBattleResult` (`BattleHUD.Public.cs:681-706`) minus `ClearBattleBonus`, the 'BattleEnd'
support-ability loop and `escape_gil`. It never sets `IsOver`.

**Seams in `BattleResultUI.cs`** (stock today; this is its first patch). The class becomes `partial`,
and the new `BattleResultUI.Net.cs` holds the replay state and shadows.

| Seam | Line | Replay behaviour |
|---|---|---|
| a. Show | `:15` | after `isTimerDisplay`: `if (NetBeginReplay()) return;` → InitialNormal only; never InitialEvent |
| b. Hide tail | `:46` | `if (NetReplayHidden()) return;` → FadeInEx(256), song shutdown, panels off, timer restore; never touches `prevMode`, never `Replace` |
| c. OnKeyConfirm | `:75-153` | switch body moved verbatim into `StepConfirm()`; `if (base.OnKeyConfirm(go)) { if (NetLocksLocalConfirm) return true; StepConfirm(); } return true;` — the guest's quit prompt still gets the guest's press because base routes it first; the driver calls `StepConfirm()` directly |
| d. InitialInfo | `:404` | `if (NetFillReplay()) return;` → manifest values through the shared stock step math (two extracted static helpers) |
| e. DisplayCharacterInfo | `:202` | skip invalid rows; level/exp/status from shadows |
| f. IsEnableDraw | `:325` | manifest draw flag |
| g. DisplayLevelup | `:248` | shadow level++, animation; no `GrowLevel` |
| h. UpdateExp | `:538` | same math on shadows, capped and forced to levelAfter |
| i. AddAp | `:596` | `apValue.current += ap`; fire scheduled learns with apAt in (old, new] |
| j. ApLearned | `:641` | achievement behind `!_netReplay` |
| k. UpdateGil / DisplayGilAndItemInfo | `:685-708`, `:175` | `party.gil` through a shadowing `NetPartyGil` property |
| l. UpdateItem | `:710` | no `FF9Item_Add`, no `MiniGame_SetCard`; play 1046/108 if the host overflowed and return the inverse of the host's overflow |
| m. Update | `:752` | `if (_netReplay) NetFollow();` before the tick switch |

**NetFollow:**
- It waits while `Loading || QuitScene.isShowQuitUI`.
- It allows one step per local state per 1.5 s, which prevents a double TweenOut or fade.
- `ChaseStep` never steps when H == None, because None (8) sorts after Hide (7).

| Local state L | Inject `StepConfirm()` when host state H |
|---|---|
| Start | H > Start |
| EXPAndAPTick, EndEXPAndAP | H > EndEXPAndAP, or H == EndEXPAndAP && host Loading |
| StartGilAndItem | H > StartGilAndItem |
| ItemFullDialog | H > ItemFullDialog |
| GilTick | H > GilTick |
| End | H == Hide |

### 5.7 "Follow the host's inputs" — why state, not presses

The owner asked for the reward screen to follow the host's inputs. Each host Confirm press advances the
host's `ResultState` (`BattleResultUI.cs:75-153`), and the guest steps on each state change within one
sample, so the guest's screen moves when the host presses. The guest's own Confirm, pad and mouse do
nothing; its Quit and Pause stay local. This is the dialogue-lock contract.

Exact press relay was rejected for two reasons:
- The screen is a monotone state machine. State plus Loading already converges.
- BattleAutoConfirm (default on, `ControlSection.cs:48`) repeats Confirm every 100 ms while held, so
  presses are noisy and can skip states inside one 150 ms sample. State-chasing cannot lose a step.

### 5.8 Flee and defeat presentation (stage 12)

- **Escape:** inject MENU_OFF/ESCAPE so the native run-away plays. Add R9b in the `SEQ_MENU_OFF_ESCAPE`
  tail (`battle.cs:452-478`): skip `IOverloadOnFleeScript` and the gil penalty while Active.
- **Defeat:** inject MENU_OFF/DEFEAT with `SetBattleFollowMessage(Annihilated)`; song 6 comes from
  `BattleIdleLoop` (`battle.cs:280`).
- The replay also opens for the escape-with-gil and NoGameOver-defeat result screens.
- Optional later (owner opt-in): a GameOverUI replay (never the Title), the win pose applied per
  stand-in, and an AfterEvent gMode-4 dialogue relay.

---

## 6. Shared work, the wire, and the call order

### 6.1 Stage 1, shared by both arcs: host command-phase gates

Both rounds designed this independently. Merged:

- **Ready sample** (`NetSyncBattle.cs:592-593`):
  ```csharp
  ready = hud.FF9BMenu_IsEnable() && btlsys.btl_phase == FF9StateBattleSystem.PHASE_NORMAL
       && hud.ReadyQueue.Contains(index) && !hud.InputFinishList.Contains(index)
       && !btl_cmd.CheckUsingCommand(d.cmd[0]);
  ```
  `FF9BMenu_IsEnable` is `_commandEnable` (`BattleHUD.Public.cs:718-721`). It falls at the victory
  menu-off and on pause.
- **Intake guard.** In `HandleCommandPayload`, placed right after the length/version check
  (`NetSyncBattle.cs:1511-1512`) and BEFORE `IsGuestOwnedSlot` (`:1517`): refuse when not PHASE_NORMAL
  or the menu is disabled. Count it in `cmd_refused` and log once per battle per reason. It sits before
  the ownership check so a bench with `GuestSlots = 0` still hits it.
  - The host drains the queue every frame while it is in battle (`:355-361`), so frames left from the
    victory edge or the previous battle are drained and refused during the next intro instead of
    freezing it [I, follows from the drain site].
- **Logs.** Every remaining silent return gains a log line (3.8 item 4).
- **Roster.** `BuildRoster` (`:678`) returns null unless `FF9BMenu_IsEnable()`, and is forced to
  rebuild once on its rising edge, so the first turn never waits up to `RosterMs` = 1000.
- **Capability bit.** Header flags bit 1 = "my Ready bit and intake are command-phase gated", written
  beside bit 0 (`:560-561`). `ParseView` keeps the whole byte as `view.HostCaps`; old guests read
  bit 0 only (`:837-838`).

This stage changes nothing on the guest. It fixes the intro freeze and the victory-edge command race
for today's digit panel.

One guest-visible effect follows from the tightened Ready bit, and it is accepted. A host pause, the
in-battle main menu, or a Libra window disables the menu while the phase stays PHASE_NORMAL, so every
Ready bit drops. The guest's digit panel (old or new guest) then resets an in-progress pick to the root.
On resume, the host's `GuestWaitMs` episode restarts. Before this stage, the pause instead burned that
cap. Stage 8's stock menu behaves the same way (sitting 1, box 7).

### 6.2 The wire: no bump for either v1

| Lane | Change | Stage | Peer on the old DLL |
|---|---|---|---|
| type 1 header flags | bit 1 = command-phase-gated host | 1 | ignored (`ParseView` masks bit 0; `WireBenchBoot` validates bit 0 only, `:1227`) |
| type 1 per-unit Ready bit | meaning tightened: + PHASE_NORMAL + `FF9BMenu_IsEnable`; from stage 11 also + `CurrentPlayerIndex != slot` | 1, 11 | same byte |
| type 1 trailer | END BLOCK (stage 4), manifest (stage 9) | 4, 9 | ignored: `ParseView` stops after `count` units |
| type 4 roster | cadence only (gated, rising-edge rebuild) | 1 | same layout |
| type 2 command | unchanged v1, 9 B | — | — |
| type 3 control | unchanged; optional stage 13d sends 2 (root) / 3 (submenu) | 13d | any non-zero still reads "open" |
| types 0, 5, 6 | unchanged; type 7 retired; type 8 reserved for comms | — | — |

**Trailer layout** (after the `count` unit records):

```
u8  magic = 0xB5, u8 fmt = 1, u16 len           // unknown fmt -> skip len; truncation -> End = null, units kept
-- END BLOCK (always) --
u8  kind      // 0 Fighting, 1 VictoryPending, 2 Victory, 3 VictoryNoPose, 4 Defeat, 5 Escape, 6 OtherEnd, 7 Event (not an end)
u8  phase, u8 seq, u8 result                    // raw, for logs and the harness
u8  ui        // 0 battle/other, 1 BattleResult, 2 GameOver, 3 Title
u8  resState  // ui==1: ResultState 0..8, bit7 = Loading; else 0xFF
u8  flags     // b0 AfterEvent, b1 manifest follows, b2 item overflow (sticky), b3 escape_gil, b4 BTL_CONTI_FLD_SONG
u8  winPoseMask
-- MANIFEST (iff flags.b1; from stage 9) --
u8  rowMask   // RAW party slots 0-3
per row: u8 charId, u8 rowFlags (b0 needExp, b1 needAp, b2 drawEnabled), u8 levelBefore, u8 levelAfter,
         u32 expBefore, u32 expGain, u16 apGain, u64 status, u8 learnN (<=8) x {i32 abilId, u16 apAt}
u32 defaultExp, u16 defaultAp, u32 gilGain, u32 gilBefore
u8  itemN (<=6) x {i32 itemId, u8 count}
i32 card
```

**Parsing.** The trailer is read inside its OWN try after the unit loop. A bad trailer can therefore
never turn the whole view null, which would make the lane go stale and the guest leave early (3.7).

**Size and binding:**
- Type 1 grows from ≤ 324 B to ≤ about 680 B, only while a host battle runs (about 20 KB/s).
- `MaxPayload` 8192 is a receiver-only cap (`NetSyncSocket.cs:147`, `:177-181`). The encoder caps
  learnN, itemN and the row count, and logs once if it truncates.
- The trailer is bound to a battle by the header's existing nonce and inherits type-1's seq-keyed
  staleness (the STACKED-STALENESS law).

**Mixed versions:**
- New guest + old host: the capability bit is absent, so the digit panel stays and the reason is logged;
  no end block arrives, which is today's behaviour.
- Old guest + new host: today's behaviour, plus the stage-1 host fixes.
- Nothing half-syncs, because no type and no layout changed.

**The one future bump (v15)** is the optional B4.2 round (4.8), bundled with the comms lane's type 8.
Never add a frame type without a bump: `Accept` has no default case, which gives a silent half-sync.

### 6.3 Guest per-Update call order

```
transport branch:  Pump -> ActionTick -> DioramaTick -> ReconcileTick -> EndTick (B5) -> StockMenuTick (B4)
selftest branch:   SelfTestPump -> EndTick -> StockMenuTick -> (existing benches, early returns)
```

- DRAIN-BEFORE-RECONCILE is untouched.
- EndTick runs after ReconcileTick, so a final death lands before the phase flip, after which the
  reconciler quiesces (`NetSyncDiorama.cs:1288`, `:1546`).
- StockMenuTick runs after EndTick, so an end injected this frame closes the stock menu in the same
  frame. InjectEnd also calls `StockMenuCloseAll` itself.

### 6.4 Harness surface (additive; protocol stays 5)

**Battle doc:**
- `battle.seq` beside `phase` (`HarnessAgent.cs:2069`);
- `battle.hud` (`NetDescribeHud`: active group, command labels and states, visible rows);
- `battle.result_ui` (`NetDescribe`: state, loading, label texts, rows, items, card).

**One new `netsync.battle` block** with four sub-objects, so the `AppendNetsync` catch literal
(`HarnessAgent.cs:2483`) gains one key:
- `host{caps, ready_mask, cmd_refused, end{kind, phase, seq, result, ui, res_state, loading, flags, manifest_len}}`
- `peer{live, seq, nonce, caps, ready_mask, end{...same..., rows, bench}}`
- `menu{stock_owns, why, assist_slot, mirrored, stranded, pending{slot, ms, seqs}, refused, captured{slot, action, menu, id, mask, cursor}, roster_slots, r9_refused}`
- `end{injected, kind, r8_hits, watchdog, replay{armed, open, closed, state, rows, refused}, end_leave, declined}`

**Verbs** (selftest only):
- `netsync guestslots <mask>` — a process-local override of the pin at `NetSyncClient.cs:3544-3548`;
- `netsync bcmd <hex>`;
- `netsync bmenu open|close <L> | capture on|off`;
- `netsync bbench start <mask> | ready <mask> | caps <bits> | mode accept|refuse|freeze | roster <hex> | unmap <w> | stop`;
- `netsync bench lapse <ms>`;
- `netsync endbench victory|pending|nopose|other <res>|defeat|escape|event|ui <n>|state <n> [loading]|manifest <preset>|overflow 0|1|afterevent 0|1|cmd|clear`.

**Repo side:**
- `tools/harness/session.py`: `NETSYNC_SUBVERBS` (:8273) plus helpers.
- `tools/harness/fakegame.py`: capability list in lockstep.
- `ff9mapkit/tests/test_harness_netsync.py`: the two-literal catch-line pin around `NetsyncF3Retired`.
- A Python v1 roster and type-1 codec, plus an end-block codec, for composing bench markers.

### 6.5 Files touched (engine)

| File | Stages |
|---|---|
| `Memoria/Netsync/NetSyncBattle.cs` (`partial`) | 1 (gates, caps, roster cadence, logs), 2 (G2, R9 counter), 3 (codec extraction, `PeerUnit.Ready`), 4 (trailer, change sampling, `PeerEnd`), 5 (DrawGUI guard), 8 (Pump guest branch, DrawGUI), 11 (G6, hand-back) |
| `Memoria/Netsync/NetSyncBattle.StockMenu.cs` (NEW) | 3 (capture, outbox, `StockMenuCloseAll`, bench opener), 7 (content), 8 (mirror, bench feed) |
| `Memoria/Netsync/NetSyncEnd.cs` (NEW) | 4 (codec, ClassifyEnd, SelfTest), 5-6 (arm state, bench seam), 9 (manifest) |
| `Memoria/Netsync/NetSyncDiorama.cs` | 2 (`NoteRefusedEnqueue`), 3 (`LocalIndexForWire`/`WireIndexForLocal`, ForceDisarm resets), 5 (EndTick, InjectEnd, NoteR8, watchdogs), 6 (exit, stamp, Leave hooks), 13a (`bi.target` overlay) |
| `Memoria/Netsync/NetSyncClient.cs` | 5 (EndTick calls), 6 (late-join decline), 8 (`GuestStockMenu`, StockMenuTick calls), 4 (SelfTest registration) |
| `Global/btl_cmd.cs` | 2 (R9) |
| `FF9/btl_sys.cs` | 5 (R8) |
| `Assets/SiliconSocial/AchievementManager.cs` | 5 (widen to `Booted`) |
| `Global/battle/BattleHUD/BattleHUD.cs`, `.Const.cs`, `.Unity.cs`, `.Scene.cs`, `.Public.cs` | 3 (capture, side-path gates, `NetDescribeHud`), 7 (content hooks), 10 (`NetGoToBattleResultReplay`), 13 (optional) |
| `Global/battle/Result/BattleResultUI.cs` (+ NEW `BattleResultUI.Net.cs`) | 4 (`partial` + state accessor), 9 (host taps), 10 (seams a-m) |
| `Global/battle/battle.cs` | 12 (escape R9b), 13c (optional cursor) |
| `Global/UI/UIKey/UIKeyTrigger.cs` | 13b (optional Menu-key rotation) |
| `Memoria/Harness/HarnessAgent.cs` | every stage, additive |
| `Assembly-CSharp.csproj` | 3, 4, 10 (three new `<Compile>` entries) |

---

## 7. Combined stage order

Each stage is one DLL build through `py tools/build_memoria.py` (it backs up first; the raw build
auto-deploys), one calibrated solo bench, and one patch emitted against live-minus-the-change. The
latest patch at writing is `s99`, so this arc tentatively starts at `s100`. Re-read
`memoria-patches/README.md` before each emit, because concurrent sessions claim numbers.

| # | Stage | From | Runs on | Owner-visible result |
|---|---|---|---|---|
| 1 | Host command-phase gates + capability bit | B4 S1 + B5 S1 | host | today's digit panel can no longer freeze an intro or land a command at the victory edge |
| 2 | Guest containment backstop (R9, G2) | B4 S0 | guest | none (inert) |
| 3 | **Stock menu first look + capture — GO/NO-GO** | B4 S2 | guest bench | first screenshots of the real panels in the diorama |
| 4 | Host end block | B5 S0 | host (+ guest parse) | none |
| 5 | Guest victory presentation (InjectEnd, R8, watchdogs) | B5 S2 | guest | fanfare, win poses, victory camera |
| 6 | Guest exit with the host | B5 S3 | guest | the guest returns with the host, not 2-3 s later |
| 7 | Roster-fed menu content | B4 S3 | guest | host's abilities and bag in the real panels (bench) |
| 8 | Production ready mirror + `GuestStockMenu` | B4 S4 | guest | the real menu replaces the digit panel |
| — | **TWO-MACHINE SITTING 1** (boxes 1-23) | | both | |
| 9 | Host result manifest | B5 S4 | host | none |
| 10 | Guest result-screen replay | B5 S5 | guest | the stock reward screen, following the host |
| 11 | Guest-slot hand-back (G6, G3) | B4 S5 | host | a guest returning from a stall gets its slot back |
| — | **TWO-MACHINE SITTING 2** (boxes 24-34) | | both | |
| 12 | Flee and defeat presentation | B5 S6 | guest | native run-away and defeat on the guest |
| 13a-d | B4 polish, each its own round: hidden-enemy targeting, Menu-key rotation, 3D cursor, WAIT parity | B4 S6 | guest/host | |
| — | **TWO-MACHINE SITTING 3** (boxes 35-40) | | both | |
| later | B4.2 full command relay (v15, with comms type 8); B5 opt-ins | | | |

**Why this order:**
- **Stage 1 first.** Both arcs need it, it is host-only, and it fixes two live bugs in the shipped
  lane.
- **Containment before surface.** Stage 2 lands before anything can fill a guest `ReadyQueue`.
- **Go/no-go early.** Stage 3 is the one question source cannot answer, and its answer decides whether
  stages 7, 8, 11 and 13 build. Nothing in B5 depends on it.
- **Low-risk, owner-visible B5 work next.** Stages 4-6 deliver victory plus a synchronized return.
  Stage 5's InjectEnd closes the stage-3 bench menu, so the coupling is tested from the first B5 build.
- **Sitting 1 tests both halves.** Stages 7-8 finish B4 v1, so the owner's first sitting covers the
  real menu and victory plus return together.
- **The riskiest B5 work lands after sitting 1.** Stages 9-10 (manifest, reward-screen seams). Stage 11
  is a small host round that rides sitting 2.

**If stage 3 is a NO-GO** (a panel fails to compose or take input in `BattleMapDebug`):
- Do not build stages 7, 8, 11 or 13.
- Keep stages 1-2, which stand alone, and continue B5 unchanged. InjectEnd's `StockMenuCloseAll` stays
  a no-op.
- Return B4 to design: a cloned panel under the NGUI laws (PRESERVE-THE-BAKE, SCROLL-SUM), or a
  restyled digit panel. Report to the owner before choosing.

**Per-stage contents and in-game proof:**

1. **Host command-phase gates** (6.1). Proof:
   - Across a SECOND battle's intro, and from the victory menu-off onward, `peer.ready_mask` reads 0
     and `host.caps` has bit 1.
   - An intro `bcmd` is refused and logged, and `turn.enabled` still rises (no freeze).
   - After enable, the roster is non-empty within 2 frames and the same `bcmd` lands.
2. **Guest containment backstop**:
   - R9 at `btl_cmd.cs:153`; G2; `NetSyncBattle` becomes `partial`; the `r9_refused` counter.
   - Proof: harness `battlecmd` inside a selftest diorama leaves `cmd[0]` NOT queued, with
     `r9_refused == 1` and a log line. A plain 60 s diorama reads `r9_refused == 0`.
   - `coop_diorama_return.py` 22/22.
3. **Stock menu first look + capture** (4.3). Changes:
   - every capture site and side-path gate;
   - `ForceDisarm` resets;
   - codec extraction; `LocalIndexForWire`/`WireIndexForLocal`; `PeerUnit.Ready`;
   - `StockMenuCloseAll`, `NetDescribeHud` and the selftest-only `bmenu open|close`.

   Proof:
   - `game_snap` PNGs READ for the command, ability, item and target panels.
   - Attack and Item commits decode to the right v1 frames.
   - The guest's real Potion count is unchanged, and `r9_refused` stays 0.
   - **Go/no-go recorded here.**
4. **Host end block** (5.2). Proof:
   - A selftest REAL battle's loopback peer block walks kind 0 → 1 → 2; ui 0 → 1; `res_state` walks
     Start → ... → Hide with Loading set exactly during the fade ping-pong.
   - The lane falls only after the field load. A Game Over leg records ui 2 → 3 and whether the lane
     stays live at the title (settles two [I] claims).
   - Co-op off is unchanged.
5. **Guest victory presentation** (5.3). Proof on a bench diorama:
   - NORMAL → MENU_OFF → VICTORY with fanfare, poses and camera 2 (or W1 logged).
   - The guest holds at the WAIT seq while `r8_hits` climbs.
   - A MENU_OFF/EVENT edge leaves the guest in NORMAL.
   - An open bench stock menu closes at injection.
   - Gil, bag, cards, kill counters and achievements are unchanged at leave.
6. **Guest exit with the host** (5.4). Proof:
   - `ui 1` + Hide → end-leave line, warm return, `battle.result` reads 1 on the field, invariants
     byte-identical.
   - `ui 2` → leave to own field, Title never appears.
   - The skip stamp is a two-machine box (3.8 item 3).
7. **Roster-fed content** (4.5). Proof:
   - A fabricated roster through the REAL `ParseRoster` shows locally impossible content, read from
     the live NGUI via `battle.hud`.
   - A double-cast roster yields one pick.
8. **Production ready mirror** (4.6). Proof: the bench feed drives open, accept, refuse-then-reopen,
   stale-close, unmapped-slot digit fallback, caps-absent digit fallback and a live knob flip.
9. **Host result manifest** (5.5). Proof:
   - The selftest loopback's peer manifest equals the host's live result labels (`battle.result_ui`).
   - A learning fight's schedule matches the host popup.
10. **Guest result-screen replay** (5.6). Proof:
    - The stock screen shows impossible host values, steps only on host states and ignores the guest's
      Confirm.
    - It returns with zero writes while the guest's REAL party is seated.
11. **Guest-slot hand-back** (4.7). Proof with the lapse lever:
    - The host captures the slot and Ready bit 1 drops (G6).
    - At root it hands back within 3 frames; in a submenu it does not.
    - Calibrated red on the stage-10 DLL.
12. **Flee and defeat presentation** (5.8). Bench, then two-machine.
13. **B4 polish**, each owner-approved and benched alone:
    - (a) the `bi.target` overlay in the reconciler's hidden lane (`NetSyncDiorama.cs:1431-1446`), which
      saves and restores rather than doing list surgery;
    - (b) Menu-key rotation between ready guest slots (`UIKeyTrigger.cs:699`);
    - (c) the 3D active-character cursor (`battle.cs:225`), whose `(cmd_status & 2)` precondition must be
      checked in game;
    - (d) WAIT parity through control byte 2/3 (`BattleHUD.Public.cs:753`), only if the owner wants it.

---

## 8. Solo bench plan

### 8.1 Rules for every stage

- Everything runs unattended through the in-game harness in the selftest role (`netsync selftest 1`;
  saves sandboxed). Read the test-harness memory before any run: arming is a transition, and plan in
  ticks.
- **Calibrate first.** Run each scenario on the PREVIOUS DLL. It must go red on exactly the predicted
  assertions; record those reds (the a-check-that-cannot-fail law).
- **Two markers.** Every content bench carries values that exist nowhere else in the process. Choose
  markers at arm time from the guest's own state, so they are guaranteed absent locally (the TWO-MARKER
  law).
- **Regression set after every DLL:** `coop_diorama_return.py` 22/22, `coop_dialogue_authority.py`
  147/147, `coop_talk_relay.py` 28/28.
- Run scenarios from this worktree with the worktree package pre-imported and its `__file__` asserted;
  study scripts otherwise pin the MAIN repo.
- Archive `Memoria.log` to scratch in the same session.
- **What a solo bench cannot prove:**
  - non-identity wire-to-local mapping (the bench seats the own party, so the mapping is identity);
  - relay timing;
  - the skip-nonce stamp (3.8 item 3);
  - the real host validator against a real guest.

  Each has a two-machine box.

### 8.2 Scenarios

New scenarios live under `studies/test-harness/scenarios/`.

**`coop_battle_host_gates.py`** — stages 1 and 11; a REAL selftest own battle with `netsync guestslots 2`.
- Battle A: let slot 1 fill, leave it uncommanded, then win with `fight`. `peer.ready_mask` loses bit 1
  from the first frame `battle.phase != NORMAL` or `turn.enabled == false`, and stays 0 through the
  result screen. `host.caps` has bit 1.
- Battle B, intro: `ready_mask == 0`, `roster_slots` empty. `netsync bcmd 01 01 00 00 00 00 10 00 00`
  (the 9-byte v1 frame `ver slot action menu idLo idHi maskLo maskHi cursor`: slot 1 Attack at enemy
  slot 4), parked on the field after A, logs the "not in the command phase" refusal,
  `host.cmd_refused` rises by 1, and `turn.enabled` still rises.
- Battle B, after enable: `roster_slots` is non-empty within 2 frames (`host.roster_lag` 0..2), and the
  same `bcmd` logs "peer command: slot 1 Attack".
- A `bcmd` sent during battle A's victory raises `cmd_refused` exactly once, with one log line per
  battle per reason. (`endbench cmd` is the stage-4 form of the same leg.)
- Calibration. The pre-stage DLL has neither `netsync.battle` nor the verbs, so it runs only the
  capability probe, which must fail closed. The behavioural reds run on the stage DLL with
  `netsync hostgates 0`, which reverts exactly the stage's paths:
  - `host.caps` and `peer.caps` lack bit 1, and the Ready bit stays set through victory;
  - the victory Attack `bcmd` is NOT refused, but it does not land either: every enemy is dead at the
    victory edge, so the Attack retarget drops it (`cmd_dropped` +1, "no living target left to
    retarget to"). A frame that CAN land there is Defend `01 01 01 00 00 00 02 00 00` (`cmd_queued`
    +1). It puts slot 1 into `InputFinishList`, which hides B's leak, so send it only in a separate
    battle after the freeze leg (reload the sandbox save), never between A and B;
  - `roster_lag` follows the free-running `RosterMs` cadence, uniform over 0..`RosterMs`, so a single
    opening lands in 0..2 in roughly 5-10% of runs. Assert it over several openings (at least 4 of 5
    above 2 frames), never on one;
  - battle A's queue leaks into B's intro, and the parked intro `bcmd` freezes the fight. Run the freeze
    leg last, on a throwaway sandbox save.
- Stage 11 part: `netsync bench lapse 4000` as slot 1 fills.
  - The host captures it (`turn.slot == 1`), and `ready_mask` bit 1 == 0 (G6).
  - When the lapse ends at root, `turn.slot != 1` within 3 frames, with the hand-back log.
  - Repeat in the ability submenu: no hand-back until the pick commits.

**`coop_battle_containment.py`** — stage 2.
- `dioboot <scene>` from a live field, wait for `battle.turn.enabled`, then `battlecmd 0 1 176 16 0`.
- Assert: unit 0's `cmd[0]` is not in use, `netsync.battle.menu.r9_refused == 1`, and a log line names
  `cmd_no` 1.
- A second plain diorama held 60 s reads `r9_refused == 0`. `dioleave` gives a warm or cold return as
  before.
- Calibration: the command queues and the local sim plays the swing.

**`coop_stock_menu.py`** — stages 3, 7, 8.
- **Part 1 (stage 3), dioboot diorama:**
  1. `bmenu open 0` → `turn.slot == 0`, `battle.hud.group == command`.
  2. One `game_snap` PNG per panel (command, ability, item, target), each READ.
  3. Confirm, confirm → `captured == {slot 0, action 0, menu 0, mask 0x10, cursor 0}`, decoded by the
     host's own `TryDecodeCommand`. `turn.done` contains 0, `cmd[0]` is free, `r9_refused == 0`.
  4. Item: record the guest's Potion count N; close/open; Item → Potion → self. Assert `{action 3,
     id Potion}`; the count is still N after 5 s.
  5. Calibration lever `bmenu capture off` (bypasses only the forward): the same script shows
     `r9_refused` +1, no capture and the count still N. That proves capture fired and R9 stands behind
     it.
  6. AccessMenu with in-process `AccessMenus=3`: UI state stays BattleHUD and SFX 102 is logged.
     `CanForceNextTurn` reads false while Active.
- **Part 2 (stage 7), slot 0 = the guest's own Zidane.** `bbench roster <hex>` through the REAL
  `ParseRoster`:
  - Ability1 = WhiteMagic (a command outside Zidane's preset);
  - Ability2 = SkillZ listing ONLY an ability the save has NOT learned (enabled, MP 1) and omitting one
    it HAS learned;
  - items = [an item the guest owns 0 of, ×77], with Potion omitted.

  Expect:
  - the "White Magic" label;
  - the unlearned row enabled and the learned row blank;
  - the item list exactly "<marker> 77";
  - Change greyed;
  - picking the marker keeps the target panel open (no SFX 101 bounce) and captures `{action 3, id
    marker}`;
  - a Vivi seat with Ability1 = DoubleBlackMagic yields ONE pick.

  Calibration (stage-3 DLL): every marker fails the opposite way.
- **Part 3 (stage 8).** `bbench start 0x01` builds a type-1 every 150 ms from the live units (seq
  advancing, caps bit 1) through the REAL `ParseView`, with the part-2 roster.
  - `bbench ready 0x01`: `turn.slot == 0` within 2 frames, `stock_owns` true, `assist_slot -1`, and
    digits are not swallowed.
  - Mode accept: commit Attack → the bench clears the bit → the window stays shut; re-raising the bit
    reopens it.
  - Mode refuse: after ≥ 2.5 s and ≥ 3 seq, `refused` +1, one log line, `turn.slot == 0` again.
  - Drop the bit with the target panel open: `turn.slot -1`.
  - `bbench freeze 1`: about 2 s later the lane is dead and `mirrored` is empty.
  - `bbench caps 0`: `stock_owns` false, why = "host predates the command-phase gates", and the digit
    panel is back.
  - `bbench unmap 1` with `ready 0x02`: `stranded` has 1 and `assist_slot == 1`, so the digit panel
    serves it.
  - `GuestStockMenu=0` edited live: the session stays up and the digit panel returns.

**`coop_battle_end_host.py`** — stages 4 and 9, host half; selftest, no diorama.
- `battle 67`, `fight` to the win, polling `netsync.battle.peer.end` every tick. Then `leave_battle`
  (`session.py:8198`), which records each Confirm.
- Assert:
  - the kind sequence is 0 → (1 or 4) → 2;
  - ui flips to 1;
  - each recorded press is followed by a `res_state` increase, with Loading set during the EndEXPAndAP
    fade;
  - `res_state` ends at Hide;
  - `peer.live` falls only after the field load.
- Game Over leg: lose deliberately on a bench save; record ui 2 → 3 and whether `peer.live` stays up at
  the title.
- Offline, before building: `NetSyncEnd.SelfTest` by reflection on a scratch copy of the DLL.
  - It covers the codec (every truncated prefix refused, a trailer-less v10 frame, an unknown-format
    skip), ClassifyEnd and ChaseStep.
  - Mutants must each fail: seq-2-as-end, None-chased, and step-at-natural-EndEXPAndAP.
- Stage 9: the peer manifest equals `battle.result_ui` for:
  - exp, AP and gil received; current gil;
  - each row's level, exp, next and dim flag;
  - items and card.

  Plausibility check on a party without reward support abilities: `gilGain == bonus.gil`, and
  `expGain == bonus.exp / eligible members`. A teaching fight's schedule matches the popup.

**`coop_battle_end_guest.py`** — stages 5, 6, 10, 12; warm bench field 30602.
- Setup: `netsync dioboot 67 0`, wait for phase 4. Snapshot these invariants:
  - gil;
  - the count of a marker item chosen by its ABSENCE;
  - each member's exp and level;
  - card count;
  - Achievement enemy_no and abilities;
  - `categoryKillCount`.
- **Stage 5:**
  - `endbench victory` → `end.injected`; phase 5 → 6, seq reaches 2 within 10 s (else W1 must log
    after `ui 1` + 4 s); `battle.result == 1`; HUD hidden, no assist text; `r8_hits` rising; a
    `game_snap` of the poses.
  - With a `bmenu open 0` window up first: injection closes it (`turn.slot -1`).
  - Negatives: `endbench event` stays in phase 4; `defeat`/`escape` hide the HUD without injecting.
  - Variants: `nopose` (PHASE_CLOSE, fade, R8) and `other 7`.
- **Stage 6:**
  - `ui 1` + `state 7` → `end_leave`, `netsync.diorama.returns` +1, a warm return, `battle.result` 1 on
    the field, invariants byte-identical.
  - `ui 2` → leave to own field, never Title.
  - The late-join decline is a pure predicate, benched through SelfTest.
- **Stage 10** (the guest's REAL party seated, since the bench mirror is unarmed). `endbench manifest 1`
  loads TWO-MARKER values:
  - gilBefore 1234567;
  - the marker item ×7 and a card;
  - row 0 two levels up;
  - a learn at apAt 3.

  Then `ui 1` + `state 0`. Assert:
  - the replay opens at state 0, and `game_snap` shows 1234567 and LEVEL UP;
  - harness Confirm ×3 and a 2 s held Confirm change nothing;
  - `state 1` steps the replay;
  - `state 2` without Loading: the local ticks end naturally, with no injected step;
  - `state 2 loading`: the guest steps into the fade;
  - `overflow 1` + `state 4` shows the ItemFullDialog;
  - `5 → 6 → 7` closes the replay and leaves.

  After the leave, every invariant is byte-identical and loops 105/109 are stopped.

  Quit guard: open the guest's quit prompt, then send `state 1`. The prompt stays unanswered and the
  replay waits.

  Negative: a manifest whose charIds match no seated member gives `replay.refused`, a black hold and a
  clean leave.
- **Stage 12:** `endbench escape` leaves gil unchanged (R9b); `endbench defeat` plays the Annihilated
  message and song 6; `manifest 2` (escape_gil) opens the replay.

---

## 9. Two-machine boxes

**Setup for every sitting:**
- Host on the desktop, guest on the laptop, `FollowHost`, wire v14, the SAME DLL on both machines.
- Diff the meeting fields first (the laptop-package staleness trap).
- Grab BOTH `Memoria.log` files before any relaunch.
- Meeting fields: 250 (warm leg, random encounters) and Dali 350 (cold leg).
- The laptop package README must say "update BOTH machines". A new guest with an old host falls back to
  the digit panel by design.

### Sitting 1 — after stage 8

**The stock menu:**
1. The guest character's ATB fills: blink, the 1044 chime and the REAL command window on the guest
   (`game_snap` on both machines). No digit panel anywhere.
2. Attack: target window, pick, and the host executes it (host log "peer command: slot N Attack"). The
   guest sees the swing and the damage figures.
3. Abilities: the list is the HOST's learned set. AP-learned rows present, unlearned rows blank, a no-MP
   ability greyed.
4. Items: the list is the HOST's bag, including an item the guest's save lacks. Using it lowers the
   host's count. The guest's own bag and save are unchanged afterwards.
5. Defend, and an Instant-type command (self or all-target).
6. Two guest slots ready: the second window opens right after the first commit, and a portrait click
   switches between them.
7. The host KOs the guest's character while its window is open: the window closes. The host pauses:
   the window closes, then reopens at the root on resume.
8. Refusal: the guest picks an item the host has just used up. The host log names the refusal, and the
   guest window reopens about 2.5 s later with one buzzer.
9. Trance: caption, colour and commands switch. Double Black Magic casts ONCE.
10. Change and Throw are greyed. With the host's NoAutoTrance on, no Trance button appears on the guest.
11. Fallbacks:
    - `GuestStockMenu=0` brings the digit panel back live, with no teardown.
    - A battle before the party mirror arms uses the digit panel.
12. Relay blip mid-window: the window closes while stale, reopens when fresh, and nothing double-fires.
13. Back-to-back battles: no guest window during the second battle's intro.
14. `r9_refused` = 0 in every guest log.

**Victory and the return:**

15. The host wins a random fight on 250 while the guest's window is open.
    - The guest window closes at the host's menu-off and the HUD vanishes; no YOUR-TURN panel at any
      point.
    - The fanfare, win poses and victory camera start within about 0.5 s of the host's.
    - The guest log shows "B5 victory injected (nonce N)". The host's victory never stalls, and nothing
      lands during the poses.
16. The guest fades and holds black, or keeps posing if W1 fired (logged). The R8 counter is logged.
    There are no achievement or Steam lines on the guest.
17. On the host's final result Confirm the guest returns WITH the host.
    - Warm on 250: the field song resumes and the fanfare does not bleed.
    - Cold on 350: no fanfare.
18. The same fight never re-boots (the skip is stamped; this is the only place that proves it). The next
    fight boots normally.
19. The host flees. The guest's HUD hides, it holds, then returns with the host. The guest's gil is
    unchanged.
20. A NoGameOver loss, then a deliberate party wipe. The guest leaves to its own field when the host
    reaches Game Over, and never sees the title. The session survives the host's save reload.
21. Late join: the guest arrives while the host is on its result screen. No diorama boots, and the guest
    logs one line.
22. (Optional) Mixed DLLs, a stage-8 host with a pre-stage-1 guest, then the reverse: today's behaviour,
    no errors. The digit panel shows with the "host predates" log.

**Carried from F3.3:**

23. The shop box from the `20261012b` package (not run in the last sitting).

### Sitting 2 — after stage 11

24. The guest's result screen opens after its own fade. Compare side by side with the host's
    (`game_snap` on both): EXP and AP received; each row's Lv/EXP/Next/dim and statuses; level-up
    flashes; learned-ability popups; gil received; current gil; items; card.
25. The host pages with Confirm, and the guest follows each page within about 0.3 s.
    - The guest's own Confirm, held Confirm, gamepad and MOUSE CLICKS do nothing. The mouse seam is
      unproven in source.
    - The guest's Quit prompt stays local and is never answered by the host's presses.
26. A fight that levels a character and teaches an ability shows the same popups for the same
    characters. If the installs' data tables differ, the final level still equals the host's.
27. Item overflow (the host carries 99 of a drop): the overflow dialog appears on both.
28. The host holds Confirm (BattleAutoConfirm): the guest converges on the same final page, is never
    ahead, and never sticks.
29. Two fights back to back: the second result screen shows the second fight's numbers.
30. The guest presses `~` → Leave mid-result: a clean return, with no stuck tick-loop sound.
31. A link blip mid-result (kill the relay leg for 3 s): the guest holds, then resumes or leaves cleanly
    within the 8 s hold.
32. An AfterEvent boss: the guest holds black and leaves on the host's exit.
33. Afterwards the guest's own menu shows its gil, items, levels, AP and cards unchanged.
34. Hand-back: stall the guest for more than 2.5 s while its slot is ready.
    - The host's window takes the slot, and the guest's window stays closed (no buzzing).
    - When the guest returns with the host at root, the host's window closes and the guest's opens.
    - Mid-submenu, the host finishes first.

### Sitting 3 — after stages 12-13

35. A flee: the guest's party plays the native run-away, and the guest's gil is unchanged.
36. A NoGameOver defeat: the defeat song and the Annihilated message play on the guest, then the result
    screen follows the host's.
37. A hidden-enemy census fight: no invisible target name on the guest.
38. Menu-key rotation with two guest slots.
39. The 3D active-character cursor on the guest.
40. Feel in WAIT and Turn-Based. This decides the WAIT-parity call (owner decision 6).

---

## 10. Risks

Ordered by how much they could cost.

1. **The stock panels may not compose in `BattleMapDebug`** (3.2, [I]).
   - Only the party panel has been seen there, and the debug branch skips `BattleHUDScene.Loading`.
   - Stage 3 is the first look, before any production feeder. On a no-go, B4 returns to design (section
     7).
2. **Re-simulation (THE NEVER-RE-SIMULATE law).** B4 deliberately breaks the b34 invariant that nothing
   in a diorama fills `ReadyQueue` (`b34-recon.md:389/:397`).
   - Mitigations: Active-keyed capture at every verified commit site; R9 behind it; the `r9_refused`
     receipt in every guest log.
   - Any future Memoria merge that adds a `BattleHUD` `SetCommand` call needs a re-census.
   - The menu-wake trace must be redone and filed with stage 3. It must list every opener now live: the
     new feeder, the auto-battle branch, `ForceNextTurn`, `switchBtlId` and the `OnKeyMenu` rotation.
3. **Reward-write leak.** The stock result screen IS the reward write (3.5).
   - Every writer is closed at its call site in replay mode, and the achievement funnel is widened to
     `Booted`.
   - The stage-10 bench runs with the guest's REAL party seated, so any miss shows as a changed
     invariant.
4. **Host Game Over wedge** ([I], `GameOverUI.cs:44-58`). The host may keep its lane live at the title.
   The guest leaves on ui 2 or 3, never only on a result Hide. Stage 4 records the truth.
5. **Quit-prompt injection** (`UIScene.cs:108-118`). The driver calls the extracted `StepConfirm()`,
   never the base `OnKeyConfirm`, and waits while the quit prompt is up.
6. **Fade interactions.**
   - The guest's own victory fade could land over an early replay, so the replay arms only after the
     first R8 hit.
   - `Leave()` defers during any fade (3.8 item 2), so the end-leave retries at 1 Hz and logs once.
7. **Classification edges.**
   - `None` (8) sorts after `Hide` (7); `ChaseStep` excludes it and a SelfTest mutant pins it.
   - var 32's non-terminal MENU_OFF is classified as Event and has a negative bench.
   - CLOSE + DEFEAT is Defeat.
8. **One bad trailer.** `ParseView`'s whole-frame catch would null the view and stale the lane (3.7).
   The trailer is parsed in its own try.
9. **No ack lane in B4 v1.** Refusal is detected by time (≥ 2.5 s and ≥ 3 seq).
   - On a fast-ATB config a turn can refill inside 2.5 s, so a correct reopen arrives with a misleading
     buzzer [I].
   - A slow link can duplicate a command; the host drops it as "not awaiting input".
   - Turn tokens and acks are in B4.2.
10. **Roster staleness and context.**
    - The 1 s cadence plus RTT means rows can lag around trance or MP changes. `NetRefreshMenus` repaints
      on change, and the host revalidates every pick.
    - Roster state and MP are computed without command context, the same as the host validator, so
      menu-keyed features can differ from a local stock menu. Validator and executor stay consistent
      until B4.2 upgrades both.
11. **Local target-time checks** (`BattleHUD.Unity.cs:443/453`) read the guest unit's MP and Silence,
    which are not mirrored mid-battle. A divergence bounces back to the list (stock) or the host
    refuses; it never commits locally.
12. **Status divergence strands a slot.**
    - A seat-carried NoInput status cured on the host leaves the guest unit in `_unconsciousStateList`,
      so `AddPlayerToReady` refuses it (`BattleHUD.Public.cs:659`).
    - G7 routes that slot to the digit panel. Sitting 1 should report how often this fires.
13. **Index mapping.** Wire slots are the host's compacted positions, and a guest seat failure shifts
    local compaction (`NetSyncDiorama.cs:1106-1110`).
    - Mapping goes through character id both ways, and `StockMenuOwns` requires `MirrorActive`.
    - The solo bench proves identity only; sitting 1 proves the rest.
14. **Host-hidden enemies stay targetable** on the guest until stage 13a.
    - A pick on one is retargeted only for Attack (`NetSyncBattle.cs:1572-1573`).
    - Other actions rely on the engine's dequeue check (`btl_cmd.cs:564`) [I].
15. **Selftest is not production.** Each item below is proven two-machine only:
    - the own party is seated;
    - a bench feed stands in for the relay;
    - `IsGuestOwnedSlot` is forced false while Active;
    - the skip stamp needs a watcher boot.
16. **Leaks across battles.**
    - `ForceNextTurn` is cleared at `ForceDisarm`.
    - `_isAutoAttack` carries over from the guest's own fights; it is forwarded as Attack.
    - `ReadyQueue` entries are drained by `CloseAll` at `ForceDisarm`, wrapped in try/catch because the
      persistent `BattleHUD` outlives the scene.
17. **Music.**
    - The injected fanfare's suspend branch (`btl_util.cs:187-193`) meets the warm, cold and host-silent
      return lanes (the s54 class).
    - Leave adds `ff9ShutdownStateBattleResult`, and the warm return's battle-song stop stays the second
      stop. Sitting 1 checks warm and cold.
18. **Install-data parity and tick skew.**
    - The guest's level-up timing and "Next" label use its own level table. The final level is forced
      to the host's, so a mismatch is display only.
    - A slower guest lags on tick pages and is fast-forwarded by the chase.
19. **The `btl_result` stamp changes behaviour.** A NoGameOver defeat now makes the guest's
    `Main_Reinit` take the host's defeat branch. That is parity (9 of 385 stock `Main_Reinit`s test it),
    but it is an owner call.
20. **AfterEvent battles.** The guest holds black for the host's whole post-battle script; gMode-4
    dialogue is not relayed (the F3 taps are gMode-1 only) [I].
21. **R9's scope includes some status scripts** (3.8 item 1). That is desired, but a later round that
    mirrors Berserk/Confuse through `AlterStatus` would make `r9_refused` non-zero by design. Re-baseline
    the receipt then.
22. **Engine build hygiene.**
    - Builds AUTO-DEPLOY with no backup: use `tools/build_memoria.py` only.
    - The shared clone has the whole netsync stack uncommitted (82 modified paths at writing). Audit the
      stack and diff the live tree before each round.
    - Coordinate patch numbers with concurrent sessions.

---

## 11. Owner decisions (recommended defaults)

| # | Decision | Recommended default |
|---|---|---|
| 1 | Wire ordering | Ship B4 v1 and B5 v1 on wire v14 (no bump). The single v15 bump is reserved for the optional B4.2 round (true double-cast, Mix, Throw, Change, manual Trance, acks, turn tokens), coordinated with comms type 8. |
| 2 | B4 v1 command scope | Attack, Defend, the ability lists (Ability, Normal, Instant types) and Item now. Double-cast commands cast ONCE, as the digit panel does today. Change, Throw, Mix, AccessMenu and manual Trance show greyed until B4.2. |
| 3 | `[Netsync] GuestStockMenu` | Default 1 (stock window on); 0 is the live fallback to the digit panel. It is a behaviour key and never tears down the session. |
| 4 | Host taking over a stalled guest slot (BTL-1) | Root-only hand-back: when the guest returns, the host's captured window closes only while it sits at the command root; mid-submenu the host finishes its pick. The guest's window stays closed while the host holds the slot. |
| 5 | Host pause, a tutorial pop-up or the host's own AccessMenu | Close the guest's window; it reopens at the root afterwards (the same gate that stops late commands at victory). |
| 6 | WAIT mode | Keep today's behaviour in v1 (an open guest window freezes the host's gauges), then decide after the sitting-3 feel test. Vanilla parity is the optional stage 13d. |
| 7 | Several guest slots ready | The stock ready order plus a portrait click in v1; Menu-key rotation in stage 13b. |
| 8 | Host NoAutoTrance=1 | The guest's character cannot trigger manual Trance in v1. Note it in the laptop package README. |
| 9 | Hidden-enemy targeting | Fix it as its own polish round (stage 13a). |
| 10 | Should the guest receive rewards? | No. The guest's screen shows the host's numbers. The host's growth reaches the guest through the party mirror at the next field load, and the guest's save never changes. |
| 11 | Who advances the reward screen | The host only. The guest's Confirm is inert; the guest's Quit and Pause stay local (the dialogue-lock contract). |
| 12 | A guest that falls behind | Chase the host's state, cutting a tick animation short if needed. Never ahead, never waiting for a guest press. |
| 13 | Host Game Over | The guest leaves to its own field the moment the host reaches Game Over: no Game Over screen, never the title. A Game Over replay is a later opt-in. |
| 14 | Flee and defeat | v1 hides the HUD, holds and returns with the host. Stage 12 adds the native run-away (guest gil untouched) and the defeat song with the Annihilated message. |
| 15 | Stamp the host's battle result on the guest's return | Yes, for every outcome except Game Over, including NoGameOver defeats. This closes the F3.3 `GetBattleResult` 0 residue. |
| 16 | Late join during the host's victory or result screen | Decline the boot, with one log line. |
| 17 | AfterEvent battles | v1 holds black and leaves on the host's exit; a gMode-4 dialogue relay comes later. |
| 18 | Win pose per character, and extra guest UI on the reward screen | Carry the win-pose byte now and apply it later. No extra guest UI (no "waiting for host" line, no slot highlight) — stock fidelity. |
| 19 | Rollout | The interleaved order in section 7: sitting 1 covers the real menu plus victory and the synchronized return. If the owner wants victory sooner, stages 4-6 can move ahead of stage 3 with no other change. |

---

## 12. Effort

**Engine C#: about 2.2-2.8k lines.** The figures below are each arc's own estimate, before removing
overlap.

| Piece | Approx. lines |
|---|---|
| B4: BattleHUD hooks | ~100 |
| B4: `NetSyncBattle.StockMenu.cs` including the bench | ~500 |
| B4: host gates, caps bit, codec extraction, hand-back | ~150 |
| B4: diorama mapping, R9 counter, stage 13a | ~80 |
| B4: `btl_cmd` R9 | ~10 |
| B4: client knob and tick calls | ~40 |
| B5: `NetSyncEnd.cs` including SelfTest | ~350 |
| B5: `BattleResultUI.Net.cs` + seams | ~300 |
| B5: `NetSyncDiorama` | ~180 |
| B5: `NetSyncBattle` | ~90 |
| B5: `NetSyncClient`, BattleHUD replay entry, R8, achievement funnel, escape R9b | ~55 |
| HarnessAgent (both arcs) | ~450 |

Removing overlap (the shared host gates, the merged harness block and its plumbing) saves about 100-150
lines.

**Repo Python: about 0.9-1.0k lines.** Five scenarios, the v1 roster, type-1 and end-block codecs,
`session.py` and `fakegame.py` updates, and the pinned catch-line test.

**Cadence:**
- 12 core DLL rounds, each one build + one calibrated solo bench + one patch, plus up to 4 optional
  polish rounds.
- About 6-8 focused build sessions and 3 two-machine sittings.
- One adversarial review of the stage 3, 8 and 10 diffs before each deploy; this arc's history says a
  verify pass corrects most single-pass claims.

**Unknowns, settled only in game, in order:**
1. Stage 3: whether the stock command, ability, item and target panels compose and take input in
   `BattleMapDebug`. This is the single go/no-go.
2. Stage 5: whether the victory camera callback advances in `BattleMapDebug` (W1 covers a no).
3. Stage 10: the result-screen composition over the debug scene, and mouse routing.
4. Stage 4: whether the host's lane stays live through the result screen and at the title.
5. Sitting 1: how often status divergence strands a slot, whether the 2.5 s refusal window feels right
   on the real relay, and music on the warm and cold lanes.

Wire, host validation and index resolution reuse lanes already proven two-machine. No wire-level
unknown remains for either v1.
