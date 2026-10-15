# Battle co-op round 3 — build plan: battle-start sync, Wait parity, flee and defeat, action replay, the guest's own field model

Status: **plan only — nothing is built.** Engine baseline: the deployed s95-s110 stack in the shared clone
`C:\gd\FFIX\Memoria\Assembly-CSharp` (clone HEAD `6b8bb2d5` plus the uncommitted stack). Line numbers were read
2026-10-13 and go stale as each patch lands: re-read before writing a hunk.

Inputs:
- `studies/battle-coop/r3-recon.md` (the owner's sitting-2 report, the owner's decisions, four recon lanes);
- four lane designs, each with an adversarial review. Appendix A lists every review finding as folded or rejected;
- `studies/battle-coop/B4-B5-DESIGN.md` (3.3 containment, 4.3, 5.3-5.8, 6.2 wire, 8 bench rules, 11 decisions).

Legend: **[V]** = verified by reading the code during this merge; **[I]** = inferred, not run.

**Next free patch number: s111.** `memoria-patches/README.md` tops out at s110 in the main repo and in this worktree.
No other worktree has an s111+ file, and `git log --all` names none (checked 2026-10-13). Numbers are assigned in the
build order of section 4. Re-read the README before each emit, because concurrent sessions may claim numbers.

---

> **Renumbered 2026-10-14 after sitting A:** the fix round s118-s121 (`R3-SITTING-A-FIXES.md`) took the next numbers, so group 2 below is now **s122-s130** (was s118-s126).

> **Renumbered again 2026-10-15 (owner decision):** s131 and s132 were captured first, and the patch stack and the pinned tests order patches by NUMBER, so group 2 is now **s133-s141**: action replay s122-s126 -> s133-s137, the guest's field model s127-s130 -> s138-s141. Every patch number below uses the new numbering except the two renumbering notes. Audit: `R3-ACTION-REPLAY-AUDIT.md` section 3.1.

## 1. What the owner asked, and the decisions already made

### 1.1 Reported after sitting 2 (both logs in hand)

1. The host no longer gets the battle fade-in; it skips straight into the fight, slightly ahead of the guest.
   Recon lane 1: this is the per-save setting `skip_btl_camera`, not a regression. The diorama applies the GUEST's
   own setting, and the laptop takes about 6 s from boot to `reconcile live`.
2. Attack and cast animations do not play on the guest, but effects and damage do. Recon lane 2: this was never
   built. Today the guest gets numbers, a flinch and a player-only MP_ATTACK swing.
3. New this round: the guest shows as Zidane on its own screen. It should show as its party character, or a moogle
   when the party has one member.
4. Not yet tested: all-target and self-target abilities, box 14 (stall hand-back), flee, and the F3.3 shop box.

### 1.2 Owner decisions for this round (asked and answered, r3-recon.md:22-29)

- **Scope:** action replay, the guest's model, battle-start sync, flee and defeat (stage 12), and the polish item
  Wait-mode parity.
- **Not this round:** hidden-enemy targeting, slot cycling, the 3D cursor, and B4.2 (v15 commands).
- **Action replay timing:** damage numbers wait for the replay's hit. HP bars still follow the host.
- **Battle start:** the host holds its gauges until the laptop's battle is live, capped at about 8 s, AND the laptop
  plays the same intro the host chose.

### 1.3 Standing laws this plan keeps

- The HOST's battle is the only real one. The guest's diorama never computes or writes battle state of its own, and
  a guest command is forwarded, never executed (containment, plus the R9 backstop in `btl_cmd`).
- Vanilla and solo play are unchanged. Every hot-path hook is a cheap static gate that reads false on vanilla. The
  host's own play does not get worse with no guest, or with a guest on an older DLL.
- **Wire stays v14** (`NetSyncSocket.cs:132`). Every addition is additive. Section 2 states what an old peer does
  with each one.
- **The harness protocol stays 5** (`HarnessAgent.cs:131`): additive verbs and keys only.
- Field laws: L1 never moves or freezes the guest; the NO-REINIT law; never fabricate a confirm for an
  `[NFOC]`/`[TIME]` window.
- Each stage is proven solo first, by checks calibrated red on the deployed DLL. A two-machine box follows.
- The desktop host runs `[Battle] Speed = 5` and `[Graphics] BattleSwirlFrames = 0`. The laptop's values are unknown;
  assume they differ. Wait vs Active is a per-save setting.

---

## 2. Wire and bit allocation across all four features

The four lane designs collided on type-1 header bit 3: the start-sync lane used it for "intro bit valid" and the
replay lane for "action starts". This table is the single allocation. Each patch claims only its own row.

| Lane / field | Bits or bytes | Patch | Meaning |
|---|---|---|---|
| type-1 header flags (`SampleOwnBattle`, `NetSyncBattle.cs:1109-1117`) | bit 0 (0x01) | existing | random encounter |
| | bit 1 (0x02) | s100, existing | `CapCommandPhaseGated` (`NetSyncBattle.cs:118`) |
| | bit 2 (0x04) | s111 | the host skipped this battle's intro |
| | bit 3 (0x08) | s111 | bit 2 is meaningful (an intro-mirror host) |
| | bit 4 (0x10) | s114 | the host's start hold is holding now (observability only) |
| | bit 5 (0x20) | s133 | `CapActionStarts`: this host sends action START/END frames and impact ids |
| | bits 6-7 | — | reserved |
| type-3 control (guest→host), byte 1 | values 2, 3 | s113 | 2 = window at the command root (or a pick in flight); 3 = below the root |
| type-3 control trailer | bytes 2-4 | s114 | `[fmt=1][host battle nonce][boot state 0-4]` |
| type-5 state section | id 8 | s139 | `SectionDress`: `[model u16][charId u8]` |
| type-6 action flags | bit 2 (0x04) | s133 | START record (old slots 0xFF) |
| | bit 3 (0x08) | s133 | END record (old slots 0xFF) |
| type-6 action payload | bytes 46+ | s133 | `0xA6` extension (impact id / START body / END id) |
| type-1 0xB5 trailer | fmt 2 record | s116 (owner: build) | `[fleeFlags u8][gilLost u32]` |

[V] Header bits 2-7 are unread by every s110 reader. `ParseView` takes the random bit and keeps the byte as
`HostCaps` (`NetSyncBattle.cs:1422-1424`). The only other reader tests bit 1 (`NetSyncBattle.StockMenu.cs:1139`).

[V] Type-6 flags use bits 0, 1, 4, 5, 6 and 7 today (`NetSyncBattle.cs:1570-1576`), so bits 2 and 3 are free.

[V] Type-5 section ids 0-7 are taken (`NetSyncState.cs:35-41`; party uses 1-3), so 8 is free.

[V] `Accept` (`NetSyncSocket.cs:344-392`) has no default case, so a new frame TYPE would be dropped silently. That is
why nothing below adds one.

**Harness bench state is not wire state.** The `bbench caps <0-255>` feed (`NetSyncBattle.StockMenu.cs:1857-1866`)
can set any header bit, which is how the guest-side benches fake a new host.

---

## 3. Feature designs

### 3.1 Battle-start sync and Wait parity (s111, s112, s113, s114)

#### 3.1.1 The ATB seam the hold uses [V]

- ATB advances in exactly one place. `HonoluluBattleMain.ProcessActiveTime` does
  `current.at += (Int16)(current.at_coef * 4)` (`HonoluluBattleMain.cs:481-482`), gated by
  `advanceAtb = UIManager.Battle.FF9BMenu_IsEnableAtb()` (`:463`). The same loop does `AddPlayerToReady`
  (`:545-546`) and the enemy `RequestAction(EnemyAtk)` (`:552`).
- That loop runs only from `YMenu_ManagerActiveTime`, behind
  `if (UIManager.Battle.IsNativeEnableAtb()) ProcessActiveTime(btl);` (`:432`). That in turn runs only under
  `!isDebug` and `FF9BMenu_IsEnable()` (`:700-703`).
- `IsNativeEnableAtb` (`BattleHUD.Public.cs:770-787`) runs these tests in order:
  1. `if (!_commandEnable) return false;`
  2. `if ((Int64)cfg.atb != 1L) return true;` (Active);
  3. `if (NetSyncBattle.RemoteMenuOpen) return false;` (`:780`);
  4. the stock Wait root test (`:783-786`).
- Its other callers are the escape roll (`btl_sys.cs:355`) and the declarable dequeue gate (`btl_cmd.cs:506`). Status
  timers hang off `FF9BMenu_IsEnableAtb` (`btl_stat.cs:289`).
- **The hold is therefore one line inside `IsNativeEnableAtb`, after the `_commandEnable` test and before the Active
  early return.** It reproduces the stock "menu not yet enabled" state an intro already uses, in every ATB mode and at
  every Speed. Speeds 3-5 use the same loop; only Speeds 1 and 2 add the `needContinue` catch-up (`:447`).

#### 3.1.2 s111 — intro mirror (host publishes, guest applies)

**Host [V seams].**
- `NoteOwnBattleStart` (`NetSyncBattle.cs:407-419`) latches
  `_ownIntroSkipped = cfg.skip_btl_camera == 0 && isRandomEncounter`. This is the same expression as
  `HonoluluBattleMain.cs:167`. It logs once:
  `[NetSync] battle intro: SKIPPED|PLAYED (skip_btl_camera K, random R) -- published in the type-1 header (bit 2)`.
- `SampleOwnBattle`, beside the bit-1 write (`:1114-1116`):

```diff
 if (gated) flags |= CapCommandPhaseGated;
+if (IntroMirrorOn) { flags |= CapIntroMirror /*0x08*/; if (_ownIntroSkipped) flags |= FlagIntroSkipped /*0x04*/; }
```

- `IntroMirrorOn = !(BenchIntroOff && IsSelfTestRole)`.
- `internal static Int32 WireIntro(Int32 f) => (f & 8) == 0 ? -1 : (f & 4) != 0 ? 1 : 0;`
- `TryGetPeerBattleOpen` (`:1811-1825`) gains `out Int32 hostFlags` (`view.HostCaps`).

**Guest.**
- `BootFromWire` (`NetSyncDiorama.cs:293`) gains a trailing `Int32 wireIntro = -1`. The default keeps both existing
  callers compiling.
- The watcher (`NetSyncClient.cs:1698`) passes `NetSyncBattle.WireIntro(hostFlags)`. The F6 wire bench
  (`NetSyncBattle.cs:1879`) passes `WireIntro(view.HostCaps)`. Its fabricated header stays flags 0x01
  (`NetSyncBattle.cs:1857`), so the bench keeps its own intro, byte-for-byte as before. **(review ctrl F9c)**
- `_wireIntro` follows the `_wireSongId` pattern. It is set in `BootFromWire`, and reset to -1 in the manual `Boot`
  overload (`:280-284`), in `ForceDisarm` (`:612-`) and in Boot's catch (`:526-545`).
- The BOOT line (`:419`) gains `intro=skip(host)|play(host)|own` and `swirl=<local BattleSwirlFrames>`.

```csharp
public static Boolean SkipBattleIntro(Boolean stock)
{
    if (!_booted || _wireIntro < 0 || (BenchIntroOff && NetSyncClient.IsSelfTestRole))
        return stock;                 // vanilla, every real battle, a manual or old-host boot: stock
    _introCalls++;
    return _wireIntro == 1;           // the HOST's choice
}
```

```diff
 // HonoluluBattleMain.cs:167
-if ((Int64)FF9StateSystem.Settings.cfg.skip_btl_camera == 0L && FF9StateSystem.Battle.isRandomEncounter)
+if (Memoria.Netsync.NetSyncDiorama.SkipBattleIntro((Int64)FF9StateSystem.Settings.cfg.skip_btl_camera == 0L && FF9StateSystem.Battle.isRandomEncounter))
     SFX.SkipCameraAnimation(-1);
 // battle.cs:495
-Boolean noDelayFade = FF9StateSystem.Settings.cfg.skip_btl_camera == 0 && FF9StateSystem.Battle.isRandomEncounter;
+Boolean noDelayFade = Memoria.Netsync.NetSyncDiorama.SkipBattleIntro(FF9StateSystem.Settings.cfg.skip_btl_camera == 0 && FF9StateSystem.Battle.isRandomEncounter);
```

- [V] `_booted = true` (`NetSyncDiorama.cs:386`) precedes the scene Replace (`:511/514`), so the new scene's `Start`
  sees it.
- [V] The diorama runs `SFX.StartBattle` without debug mode (`HonoluluBattleMain.cs:163`), so the plunge camera plays
  there and `SkipCameraAnimation(-1)` skips it.

**`NetSyncDiorama.LiveTick()`: one new per-frame call. It is a no-op unless booted.**
- Call sites:
  - Transport branch: after `ReconcileTick` (`NetSyncClient.cs:1376`). `Pump` (`:1363`) has already set
    `PeerBattleLive` this frame.
  - Selftest branch: after `StockMenuTick` (`:1138`), not after `EndTick`. **(review ctrl F1)** [V] `SelfTestPump`
    clears `PeerBattleLive` outside an own battle (`NetSyncBattle.cs:966-975`), and only the bench feed inside
    `StockMenuTick` re-publishes it (`StockMenu.cs:1239-1240`, `:1612-1613`).
- s111 latches `_normalMs`: the time from `BootTick` to the first frame with PHASE_NORMAL, loads latched
  (`LOAD_INITNPC|LOAD_INITCHR`) and `Active`. It logs once:
  `[NetSync] diorama reached its command phase N ms after the boot (intro X, swirl F frames)`. This is the
  measurement s114 and s112 need from the laptop.
- `_normalMs` (and s114's `_liveLatched`) reset in Boot's per-boot block (`:386-410`), in Boot's catch and in
  `ForceDisarm`. **(review ctrl F2)**

**Harness only.** `Ff9mkDebugMenu.HarnessBattle` gains an optional `rand` argument. The default false keeps
`Ff9mkDebugMenu.cs:536`.

**Old peers.**
- An s110 guest ignores bits 2-3 and keeps its own intro setting.
- A new guest with an s110 host sees bit 3 clear, so `_wireIntro = -1` and it uses its own setting (today's behaviour).

#### 3.1.3 s113 — Wait parity (guest encodes, host decodes)

**One encoding in the existing control byte:**
- `0` = shut;
- `1` = open (sent only by pre-R3 guests);
- `2` = window at the command root, or a pick in flight;
- `3` = below the root (Ability or Item list, or the target window). Any other value is treated as 3.

**Host.**

```csharp
public const Byte CtlShut = 0, CtlOpenLegacy = 1, CtlOpenRoot = 2, CtlOpenDeep = 3;
private static Byte _remoteMenuByte;
public static Boolean RemoteMenuDeep   // the Wait freeze; RemoteMenuOpen keeps the turn-based any-open freeze, the cap, the staleness
{ get { return RemoteMenuOpen && (_remoteMenuByte != CtlOpenRoot || !WaitParityOn); } }
```

- `ParseControl` (`NetSyncBattle.cs:2234-2248`) stores `payload[1]` into `_remoteMenuByte` and keeps
  `open = payload[1] != 0`.
- `BattleHUD.Public.cs:780` becomes `if (Memoria.Netsync.NetSyncBattle.RemoteMenuDeep) return false;`.
  - A value of 3, a pre-R3 1, or any unknown value freezes. A value of 2 runs, which is exact parity with the stock
    root test at `:783-786`.
  - Turn-based keeps `RemoteMenuOpen` at `:759-760`, because stock turn-based freezes on the root panel too
    (`_commandPanel.IsActive`).
  - `GuestWaitMs` and the 2.5 s staleness rule are unchanged (`:326-337`).
  - **As built (s113 review B1):** in Wait the 30 s cap times only the current stretch below the root. Counting root
    time let one episode run across chained guest turns, so a deep window stopped freezing after 30 s with no log.
    Turn-based and legacy guests keep the old episode bound. A cap expiry now logs once.
  - **As built (s113 review B2):** a guest that pauses while its slot is Ready reads 2 (root), so the host's Wait
    gauges keep running through the guest's own pause. On s110 they froze, for up to 30 s. A guest's local pause no
    longer stalls the host's fight. Sitting A checks how this feels.

**Guest.**

```csharp
private static Byte GuestMenuByte(BattleView view)
{
    if (FirstReadyGuestSlot(view) < 0) return CtlShut;
    if (BenchCtl >= 0 && NetSyncClient.IsSelfTestRole) return (Byte)BenchCtl;          // `bench ctl` (loopback / feed only)
    Boolean deep = (_assistSlot >= 0 && _uiSlot == _assistSlot && _uiMode != UiRoot)  // the digit panel's sub-mode
                   || _stockDeep;                                                     // the stock menu
    return deep ? CtlOpenDeep : CtlOpenRoot;
}
// BattleHUD.Public.cs, the stock root test's own negation (parity by construction):
internal Boolean NetWindowDeep()
{
    if (CurrentPlayerIndex == -1) return false;
    String g = _hidingHud ? _currentButtonGroup : ButtonGroupState.ActiveGroup;
    return !(g == CommandGroupButton || g == String.Empty);
}
```

- `_stockDeep` is computed in `StockMenuTick`'s serving branch (`StockMenu.cs:1263-1270`, after `MirrorServe`):
  `hud.CurrentPlayerIndex` is in `_mirrorMask && hud.NetWindowDeep() && !QuitPromptUp()` (`:1311`). It is cleared in
  `MirrorStandDown`, `NoteMirrorBoot`, the not-booted early return (`:1241-1247`) and `Reset`.
- Call sites use `BuildControl(GuestMenuByte(...))`:
  - the Pump guest branch (`NetSyncBattle.cs:927`);
  - `SelfTestPump` (`:1038-1041`);
  - the bench feed (`StockMenu.cs:1618`). The feed records `_feedCtl` = the exact frame Pump would send.

**Old peers.**
- An s110 host reads `payload[1] != 0` (`:2242`), so 2 and 3 both freeze, exactly as today.
- A new host receiving an s110 guest's `[0][1]` reads 1 as deep, so it freezes as today.
- Turn-based reads any non-zero value as open on both old and new hosts.

#### 3.1.4 s114 — start hold (guest reports, host holds)

**Guest report: the control trailer.** The frame becomes `[0][menu][fmt=1][host battle nonce][boot]`, 5 bytes.
`nonce` is the guest's live `_peerView.Nonce`, which is the host's type-1 header byte.

| boot | Name | When |
|---|---|---|
| 0 | NONE | not following, world map, may not boot |
| 1 | BOOTING | will boot, booting, or in its intro |
| 2 | LIVE | its diorama of THAT battle reached its command phase with a host sample in hand |
| 3 | DECLINED | opt-out, late join, undisplayable scene, a settled leave, or a manual diorama is up |
| 4 | BUSY | watching, but in a durable non-FieldHUD state (main menu, shop, pause, card game) **(review ctrl F6)** |

```csharp
internal static Byte GuestBootState(Byte nonce, Boolean watching, Boolean uiFree, Int32 skipNonce,
                                    Boolean booted, Int32 bootedNonce, Boolean live)
{
    if (booted) {
        if (bootedNonce == nonce) return live ? BootLive : BootBooting;
        if (bootedNonce < 0) return BootDeclined;            // a manual (~ / harness) diorama
        return watching ? BootBooting : BootNone;            // an older battle's diorama: the watcher leaves it (NetSyncClient.cs:1556-1558)
    }
    if (!watching) return BootNone;
    if (skipNonce == nonce) return BootDeclined;             // opt-out, late join (:1640-1650), undisplayable (:1654-1696)
    if (!uiFree) return BootBusy;                            // the watcher's silent FieldHUD return (:1680-1684) would wait on the player
    return BootBooting;                                      // fades, warps, the 1 s rate limit clear by themselves
}
```

- Inputs come from the watcher's own predicates, noted right after `DioramaTick` (`NetSyncClient.cs:1373`):
  - `watching = _role == "client" && _followHost && _tapFieldMode && NetSyncDiorama.MayBootNow`;
  - `uiFree = State == FieldHUD || SceneDirector.IsFading || _followWarpPending >= 0`;
  - the skip nonce.
- [V] The watcher never boots off a field (`:1670`). A world-map battle therefore reports NONE.
- `live` is the `_liveLatched` latch set by `LiveTick`: the s111 command-phase predicates AND
  `NetSyncBattle.PeerBattleLive`.
- [V] The guest sends control every frame while the host's lane is live and it is not in its own battle
  (`NetSyncBattle.cs:922-937`; a diorama is not "inBattle", `:814`). [V] The socket write thread re-sends the latest
  slot at about 30 Hz (`NetSyncSocket.cs:336-341`, `:671-685`), which keeps the lane alive through the guest's scene-load
  stalls.

**Host: decide once per battle; every release is final. (review ctrl F5, F6, F7, F8)**

```csharp
// ParseControl, after `_assistTick = now;`
_ctlTrailer = payload.Length >= 5 && payload[2] == CtlFmt1;
if (_ctlTrailer) { _rptNonce = payload[3]; _rptBoot = payload[4]; _rptTick = now; _guestR3Seen = true;
                   if (payload[3] != _battleNonce) menu = CtlShut; }   // a frame about ANOTHER battle never freezes this one
else if (payload != null) _lastCtlLegacy = true;
// ParseControl(null) while holding sets _ctlNullSeen (the transport reported 2 s of silence)

public static Boolean StartHoldActive {               // read only by IsNativeEnableAtb, i.e. only once _commandEnable is true
  get { if (!_holdPrimed || _holdReleased) return false;            // vanilla: one static read
        Int32 now = Environment.TickCount;
        if (!_holdStarted) { _holdStarted = true; _holdSince = now; } // the first command-phase read starts the clock
        return now - _holdSince < StartHoldCapMs; } }               // self-capped: a dead pump cannot freeze a battle
```

```diff
 // BattleHUD.Public.cs IsNativeEnableAtb
 if (!_commandEnable) return false;
+if (Memoria.Netsync.NetSyncBattle.StartHoldActive) return false;   // every ATB mode, every Speed (3.1.1)
 if ((Int64)FF9StateSystem.Settings.cfg.atb != 1L) return true;
```

**`StartHoldTick()`** runs in both pumps right after `HandBackGuestSlot` (Pump `:888`, SelfTestPump `:1042`). Let
`rptThis = _ctlTrailer && _rptNonce == _battleNonce && now - _rptTick < MenuStaleMs`. Then:

1. **Off.** Lever off or `StartHoldMs <= 0`: clear, return.
2. **Released.** `_holdReleased`: return. This state is final until `NoteOwnBattleStart`.
3. **Intro** (`!_holdDecided && !_hostPhaseOpen`): `_holdPrimed = rptThis && _rptBoot == BOOTING`. It follows the
   latest report and never primes on silence. The old design's "no word yet" priming is gone, which removes ctrl F6's
   2 s silent-guest cost and F8's stale `_guestR3Seen`.
4. **Opening edge**, once: set `_holdDecided` and `_openTick`.
   - If primed, log `[NetSync] start hold ARMED for battle nonce N -- the guest's diorama is BOOTING; every gauge waits
     (cap C ms)`.
   - Otherwise, log `not armed -- <the guest is live|declined|busy|none|no word yet>`, and only if a lane or a trailer
     was seen.
5. **Late arm.** Not primed, and the report for this nonce turns BOOTING within `LateArmMs = 1000` of the opening: arm
   and log `late +N ms`. Past the window, set `_holdReleased` silently. This covers the first battle of a session.
6. **Holding.** Release with one line, `[NetSyncBattle] start hold RELEASED after N ms: <why>`. Possible reasons:
   - `cap` (held >= cap);
   - `live` (rptThis and LIVE);
   - `declined` (rptThis and NONE, DECLINED or BUSY);
   - `link` (`_ctlNullSeen`, about 2 s after a cut, `NetSyncSocket.cs:257`, `:417-425`);
   - `old guest` (a trailer-less frame).
   A release sets `_holdReleased`, so a later pause or Libra cannot re-freeze. **(review ctrl F7)**

**Other host details.**
- `_holdPrimed`, `_holdStarted`, `_holdDecided`, `_holdReleased`, `_ctlNullSeen` and `_lastCtlLegacy` clear in
  `NoteOwnBattleStart`, `NoteOwnBattleEnd` and `Reset`.
- Every tick baseline starts at `Environment.TickCount - 60000`, never `MinValue` (the TICK-BASELINE LAW).
- `SampleOwnBattle` sets header bit 4 while `_holdPrimed && _holdStarted && !_holdReleased`. A hold edge forces a
  sample.
- `[Netsync] StartHoldMs` (default 8000; 0 = off) is a behaviour key. It is parsed beside `GuestWaitMs`
  (`NetSyncClient.cs:747`) and added to `bsig` (`:811-814`), so an edit applies live.

**Why a link cut releases on the null frame, not on a seq.**
- [V] The transport serves the last control frame for 2 s after the sender stops (`NetSyncSocket.cs:257`, `:417-425`).
  Each re-serve re-stamps `_assistTick` (`NetSyncBattle.cs:2240`).
- So the lane reads stale only about 4.5 s after a cut. This is the STACKED-STALENESS LAW (memory
  `project-ff9-multiplayer-injector.md:837`).
- That law's own fix, a seq keyed on the sender, is wrong for THIS lane. During the guest's scene-load stall its write
  thread re-sends the same bytes (`NetSyncSocket.cs:671-685`). A seq would not advance there, so the lane would read
  dead exactly while the hold is needed.
- The null frame is the transport's own "2 s of silence" verdict. **(review ctrl F3)**

**Old peers.**
- An s110 host ignores bytes 2-4 (`:2236-2242`). The transport stores the payload opaque, so no hold exists.
- A new host with an s110 guest gets 2-byte frames. `_ctlTrailer` stays false, the host never primes, and byte 1 is
  not nonce-gated, as today.

#### 3.1.5 s112 — diorama swirl clamp (owner: build it; clamp to the desktop's swirl, default 0)

- [V] `SFX_Rush` reads `static readonly StartFadeOutFrame = Configuration.Graphics.BattleSwirlFrames`
  (`SFX_Rush.cs:14-15`, used `:98-101`) at 30 Hz.
- The code default is 115, about 3.8 s (`GraphicsSection.cs:44`). The ini template ships 0 (`Memoria.ini:57`).
- The fix makes the two values instance fields chosen in the constructor:
  `_fade = NetSyncDiorama.SwirlFrames(StartFadeOutFrame)`, where
  `SwirlFrames(local) = _booted && DioramaSwirlFrames >= 0 ? Math.Min(local, DioramaSwirlFrames) : local`.
  `[Netsync] DioramaSwirlFrames` defaults to 0; -1 keeps the guest's own value.
- Real battles on either machine are untouched. Guest only.

### 3.2 Flee and defeat on the guest (s115, s116, s117)

#### 3.2.1 What s110 does today [V]

- The host already ships both outcomes in the 0xB5 fmt-1 end block. `ClassifyEnd` (`NetSyncEnd.cs:189-219`) gives
  kind 4 Defeat and kind 5 Escape, with the raw phase, seq and result beside the kind (`:1229-1239`). The block also
  carries flags b3 escape_gil and the s108 manifest.
- The guest HOLDS both: `PresentAction(KDefeat|KEscape) = PresentHold` (`NetSyncEnd.cs:279-295`). `InjectEnd`'s hold
  branch (`NetSyncDiorama.cs:2161-2167`) closes the menu, hides the HUD and returns.
- The replay never arms for these outcomes (`ArmNotInjected`, `NetSyncEnd.cs:999-1000`). The exit already covers both.
  `StampFor` stamps ESCAPE and a NoGameOver DEFEAT, but never a Game-Over-scene DEFEAT (`:446-451`).
- 12a and 12b need **no wire change**: the guest starts acting on what every s103+ host already sends.

#### 3.2.2 s115 — guest flee presentation (12a)

**Classification (pure, `NetSyncEnd`):**

```csharp
public const Int32 PresentFlee = 4;
public const Int32 GuestHold = 3, GuestNoR9b = 4;           // `endbench guest hold|nor9b` (selftest only)
public static Int32 PresentFor(Int32 kind, Byte phase, Int32 guestMode, Boolean allDown) {
  Int32 a = PresentAction(kind);                           // the v1 table, still pinned by SelfTest `present`
  if (a != PresentHold || guestMode == GuestHold) return a;
  if (kind == KEscape) return phase == PHASE_MENU_OFF ? PresentFlee : PresentClose;   // CLOSE+ESCAPE: var 33 / a late join
  return PresentHold;                                      // s117 replaces this line (defeat rows)
}
```

**`EndTick` (`NetSyncDiorama.cs:2093`).** `PresentAction(e.Kind)` becomes
`PresentFor(e.Kind, e.Phase, NetSyncEnd.GuestMode, allDown)`.

**`InjectEnd` (`:2141-2190`)** becomes a switch on the action. The new case copies the SysEscape executor's
VISUAL half (`btl_cmd.cs:1041-1052`) and never its state half (`++escape_no`, `BTL_FLAG_ABILITY_FLEE`):

```csharp
case NetSyncEnd.PresentFlee:
  b.cmd_status |= 1;                       // the escape-pending bit SetDefaultIdle reads -> MP_ESCAPE (btl_mot.cs:565)
  if (NetSyncEnd.GuestMode == NetSyncEnd.GuestNoR9b) ff9.btl_flag |= battle.BTL_FLAG_ABILITY_FLEE;   // CALIBRATION ONLY
  for (BTL_DATA n = b.btl_list.next; n != null && g < 16; n = n.next, g++)
    if (n.bi.player != 0 && !btl_stat.CheckStatus(n, BattleStatusConst.CannotEscape) && n.cur.hp > 0
        && !btl_mot.checkMotion(n, BattlePlayerCharacter.PlayerMotionIndex.MP_ESCAPE)) btl_mot.SetDefaultIdle(n, false);
  b.btl_phase = PHASE_MENU_OFF; b.btl_seq = SEQ_MENU_OFF_ESCAPE; break;
```

Without that bit the party slides backwards in its normal idle. [V] Every host flee goes through the executor:
bumpers via `BattleCalculator.cs:362`, Zidane's Flee via `0057_FleeScript.cs:26`.

**R9b, in the escape tail.** `battle.cs`, right after `btlsys.btl_phase = PHASE_CLOSE;` (`:451`):

```diff
+if (Memoria.Netsync.NetSyncDiorama.Active && Memoria.Netsync.NetSyncDiorama.FleeTailR9b(sys))
+    break;      // the run-away above is presentation; the STATE half (a mod OnFlee, the gil penalty) is the host's
 IOverloadOnFleeScript overloadedMethod = ...
```

- `FleeTailR9b` counts and logs once per boot, then returns true. Under `GuestNoR9b` it returns false, so stock runs
  (the calibration red). A throw returns true: fail closed.
- `break` leaves the switch, and `:481-487` still set `SEQ_DEFEATCLOSE_FADEOUT` [V].
- [V] R9b's real weight is the `IOverloadOnFleeScript` skip:
  - `BTL_FLAG_ABILITY_FLEE` is set only by the executor (`btl_cmd.cs:1062-1063`), which never runs in a diorama, and
    `InitBattle` zeroes `btl_flag`.
  - Disarm's `Restore` puts `party.gil` back at every teardown (`NetSyncDiorama.cs:1349-1360`).
  - So an after-leave gil check cannot fail. The bench reads gil WHILE booted and forces the flag through `nor9b`.

**W2 becomes kind-aware.** The watchdog (`NetSyncDiorama.cs:2222-2240`) forces VICTORY on any MENU_OFF stall today.
It now uses `W2Force(_endAction, ...)`:
- Flee → CLOSE / FADEOUT / ESCAPE / END_LOAD;
- s117 adds the defeat rows;
- anything else stays VICTORY.

`MenuOffBlocker` (`:2241`) gains escape rows: dead units not down, a SysReraise pending, the escape fade value.

**THE NO-LEAK RULE ships here, scoped. (review end F1, F4)**
- [V] `btl_result` is outside Snapshot/Restore, and `ApplyReturnSettle` (`:2661-2705`) writes nothing when the stamp
  is -1. A stock tail that ran in the diorama can therefore reach the return's `Main_Reinit`.
- The rule reverts only the values the stamp policy refuses: a local DEFEAT or GAMEOVER (a Game Over in transit), or
  any local value when the host's final kind is Defeat (a flee that ended in an annihilation mid-run).
- [V] That second case needs only 12a: the host's player die path calls `CheckBattlePhase` in any phase
  (`btl_mot.cs:362-366`), and the guest injects once per boot.
- A legitimate local ESCAPE or VICTORY keeps s110's behaviour.

```csharp
public static Int32 NoLeakResult(Int32 stamp, Boolean injected, Byte local, Int32 preInject, Int32 hostKind) {
  if (stamp >= 0 || !injected || preInject < 0 || local == preInject) return -1;
  if (local == FF9StateGlobal.BTL_RESULT_DEFEAT || local == FF9StateGlobal.BTL_RESULT_GAMEOVER) return preInject;
  if (hostKind == KDefeat) return preInject;
  return -1;
}
// ApplyReturnSettle, after `if (_stampPending >= 0) {...}`:
else if (_settled && _stamped < 0) {
  Int32 back = NetSyncEnd.NoLeakResult(-1, _endInjected, ff9.btl_result, _preInjectResult,
                                       _exitSeen ? _exitLast.Kind : _endKind);
  if (back >= 0) { _revertedFrom = ff9.btl_result; ff9.btl_result = (Byte)back; done += "local " + _revertedFrom + " reverted to " + back; } }
```

`_preInjectResult = ff9.btl_result` is taken at the head of `InjectEnd`. The `exit off` lever is untouched.

**The replay arms for escape-with-gil, honestly. (review end F3)**
- [V] The host's `BattleResultUI.Show` takes the ESCAPE branch without reading `btl_bonus.Event`
  (`BattleResultUI.cs:26-31`). `SampleHost` still sets `FlagAfterEvent` from it (`NetSyncEnd.cs:1548-1549`), and
  `ArmVerdict` refuses on that flag (`:1008-1009`).
- `ArmVerdict` gains the host's result and ignores b0 when that result is ESCAPE, mirroring `Show`'s own branch.
- A SelfTest row pins it. Whether a Runaway + AfterEvent scene exists is [I].

**Bench churn this patch must carry in the same commit:**
- `coop_battle_end_guest.py` S5-B runs under `endbench guest hold`. The lever is cap-gated, so an s110 run is
  unchanged.
- `coop_battle_result_replay.py:814` changes `re.search(r"replay (\d+)\)", hit)` to `r"replay (\d+)[,)]"`, because
  SelfTest's detail now ends `..., replay N, flee M)`. **(review end F2)**

#### 3.2.3 s117 — guest defeat presentation (12b)

- **Classification.** `PresentFor`'s last line becomes:
  - MENU_OFF → `PresentAnnihilate` (5);
  - PHASE_DEFEAT → `allDown ? PresentAnnihilate : PresentDefeat` (6);
  - otherwise → `PresentClose`.
  - [V] The host's MENU_OFF/DEFEAT can last one battle tick. The settle needs every player at die_seq 6
    (`btl_sys.cs:65-67`), and several ticks can run per frame (`HonoluluBattleMain.cs:615-624`). The guest's receive is
    latest-slot. So the phase plus "every local player down" picks the path.
  - The same test separates a var-34 scripted end (`btl_scrp.cs:806-812`) from a real annihilation.
- **Annihilate.** Write `SetBattleFollowMessage(BattleMesages.Annihilated)` before the existing
  `FF9BMenu_EnableMenu(false)`, in stock order (`btl_sys.cs:125-130`). Then set MENU_OFF / SEQ_MENU_OFF_DEFEAT.
  - The stock settle follows: `battle.cs:307-310`, then PHASE_DEFEAT and the fade into R8.
  - Song 6 plays only in a Game-Over scene (`battle.cs:280`, `!btlsys.btl_scene.Info.NoGameOver`), so stock parity
    needs no song code of ours. This corrects box 36 (Appendix B).
- **Defeat (var 34's writes).** `btl_result = DEFEAT; PHASE_DEFEAT; SEQ_DEFEATCLOSE_FADEOUT`, with no message.
- `AllPlayersDown(b)`: every linked player is under `BattleStatusConst.BattleEndFull` (the `btl_sys.cs:66` test).
  `MenuOffBlocker` gains defeat rows. `W2Force` maps Annihilate → PHASE_DEFEAT / FADEOUT / DEFEAT, never VICTORY.
- **Bench ops (selftest only).**
  - `endbench kill [mask]` (default 15) runs the reconciler's own `KillUnit` (`NetSyncDiorama.cs:1625-1632`) on seated
    players in PHASE_NORMAL. It writes BTL_DATA only; `SavePlayerData` is gated (`btl_sys.cs:297`).
  - `endbench phase-defeat` builds the PHASE_DEFEAT template through the real codec.
- **SelfTest section `defeat`.** Mutants that must fail: "return local", "PHASE_DEFEAT always annihilates",
  "W2 forces VICTORY".
- **Bench churn in this commit:**
  - S6-C1/C2 run under `guest hold`. Stage-12 twins live in the new scenario.
  - S6-D1 stays on and is strengthened. **(review end F5)** It polls `end.injected` true, action `close` and local
    `battle.result == 6` before sending `ui 2`, then asserts `end_leave.reverted == 6` and field result 0.
    [V] Today it sends `other 6` and `ui 2` back to back (`coop_battle_end_guest.py:779-789`), so it can pass with
    nothing presented.

#### 3.2.4 s116 — the host's "Dropped N Gil" relayed (12c; owner: build it)

- **Host tap.** Right after `battle.cs:476` (`SetBattleFollowMessage(DroppedGil, gilLost)`), add
  `NetSyncEnd.HostNoteFleeGil(gilLost)`, gated by `HostTapWanted` (`NetSyncBattle.Enabled && _hostInBattle &&
  !Booted`). It runs once per flee and only on the default flee path.
- **Record.** `WriteHostTrailer` appends a fmt-2 record:
  `[0xB5][fmt 2][u16 len = 5][fleeFlags u8 (b0 = the stock gil-drop ran)][gilLost u32]`.
- **Guest.**
  - `ReadTrailer` (`NetSyncEnd.cs:1281-1312`) parses fmt 2. A body shorter than 5 bytes is counted as skipped and
    never nulls the end block.
  - Once its own run-away has reached R9b and before R8, the guest shows the HOST's figure through
    `SetBattleFollowMessage(DroppedGil, n)`. Its gil is never touched.
- **Old peers.**
  - An s103-s110 guest steps over the record by its length (`else { skipped++; }`, `:1308-1311`) and counts
    `trailer_skipped`.
  - A pre-s103 guest stops reading at `count` units (`NetSyncBattle.cs:1428-1454`).

### 3.3 Action replay on the guest (s133-s137)

#### 3.3.1 Why the guest sees nothing today [V]

- The diorama runs the SFXRework machinery every frame. `BattleMainLoop` runs `CommandEngine` and
  `BattleSubSystem` (`battle.cs:244-245`), and `BattleSubSystem` runs `UnifiedBattleSequencer.Loop()` (`:575`).
  Nothing feeds it.
- Every gameplay hit under SFXRework goes through one place: the EffectPoint op calls
  `btl_cmd.ExecVfxCommand(btl, cmd, runningThread)` (`UnifiedBattleSequencer.cs:987`).
  - Before the call, EffectPoint zeroes every unit's `fig`. After it, it collects `fig` into `btl2dParam`
    (`:976-1004`). The `Figure` point shows the collected values through `btl2d.Btl2dReq` (`:1007-1016`).
- The native "Effect Point" callback is hijacked under SFXRework (`SFX.cs:835-836`). The other `ExecVfxCommand`
  callers run only on the old engine or for `cur_cmd_list` commands (`btlseq.cs:531`, `btl_cmd.cs:1491`,
  `btl_vfx.cs:177`).

#### 3.3.2 s133 — host action-start lane (AR1; host only, no visible change)

**START.**
- One site reaches every actor: `btl_cmd.cs:624`, just before `btl_vfx.SelectCommandVfx(cmd)`. It sits after both
  `ConfirmValidTarget` checks and the cover redirect (`:597-620`). It is BEFORE the sequence, so a START precedes every
  impact on the FIFO.
- Scripted enemy sequences add a START in `StartBtlSeq` after `btlseq.cs:108`.

```diff
     if (caster != null)
         BattleVoice.TriggerOnBattleAct(caster, BattleVoice.BattleMoment.CommandPerform, cmd);
+    Memoria.Netsync.NetSyncBattle.QueueActionStart(cmd, false);
     btl_vfx.SelectCommandVfx(cmd);
```

**END.** The first line of `FinishCommand` (`btl_cmd.cs:1284`) calls `QueueActionEnd(cmd)`.
- [V] Under SFXRework a command finishes only after its action has left `runningActions`.

**Action ids. (review replay F8)**
- `_actIds` holds the CommandEngine lifecycles, which are END-eligible.
- `_actScripted` holds the `StartBtlSeq` lifecycles. They are never ENDed, and `QueueActionEnd` never consults this
  map.
- `QueueActionStart` removes the CMD_DATA from the other map. `QueueActionEnd` removes the id after emitting the END.
  [V] `StartBtlSeq` reuses `next.cmd[0]` (`btlseq.cs:100`), and a later cmd[0] command that fails inspection goes
  IDLE → DONE → `FinishCommand` without a SELECT_VFX (`btl_cmd.cs:572-575`, `:653-662`). With one map, that path would
  have ENDed a running scripted replay.
- Both maps clear in `NoteOwnBattleStart` and `NoteOwnBattleEnd`. Ids are u16 per battle; 0 is never issued.

**`btl_vfx.DescribeCommandVfx(cmd, out num)`.** This is a pure mirror of `SelectCommandVfx` (`btl_vfx.cs:106-182`)
for the host's own mode. It never calls Execute, loads lazily or uses RNG, and inside its try/catch an exception
returns Unknown (0xFF). The kinds:

| Kind | Meaning |
|---|---|
| 0 | NONE |
| 1 | the ability's .seq |
| 2 | ENEMY_SEQUENCE (num = sub_no) |
| 3 | SPECIAL_EFFECT, the host-resolved `GetPlayerCommandSFX`: weapon serial, trance attack, SysTrans Activate/End, item/Steal/Throw shapes, PatchedVfx, Vfx2 for ManyAny cursor 0, meteor_miss and the host-rolled short_summon |
| 4 | COMMON (Defend/Change) |

**Gate.** Same as `QueueActionFrame` (`NetSyncBattle.cs:1604-1609`): Enabled, !Booted, !isDebug. Harness battles
clear isDebug (`Ff9mkDebugMenu.cs:537`), so selftest own battles emit. Plus the lever `ActStartsOn`.
`ResolveWireSlot` (`:1756-1767`) finds the actor slot. Nothing throws.

**Impacts and caps.**
- `QueueActionFrame` (`:1642-1676`) appends the 6-byte impact extension, with the id looked up in `_actIds`, then
  `_actScripted`, else 0.
- The drop-oldest enqueue (`:1665-1675`) becomes the shared `EnqueueActionPayload`.
- `SampleOwnBattle` sets **bit 5** when `ActStartsOn` (section 2).

**Wire (type 6, all additive):**
- **IMPACT:** the unchanged 46 bytes (`NetSyncBattle.cs:1567-1569`), plus `[46] 0xA6 [47] fmt 1 [48] extLen 3
  [49] kind 1 [50-51] actId`. 52 bytes.
- **START, 76 bytes:**
  - `[0]` nonce; `[1-2]` the host `_seq`, NOT consumed (no state rides a START, so the STATE-WRITE⟺HORIZON law is
    untouched);
  - `[3]` 0xFF, `[4]` 0xFF (caster and target slots); 36 zero bytes;
  - `[41]` flags 0x04; `[42-45]` cmd/sub (legacy identity);
  - `[46]` 0xA6 `[47]` 1 `[48]` 27 `[49]` kind 2;
  - `[50-51]` actId; `[52]` actorSlot;
  - `[53]` actorFlags: b0 player, b1 host SFXRework, b2 host Speed >= 3, b3 scripted, b4 monster-transform, b5 counter
    slot, b6 cmd[3];
  - `[54-55]` cmd_no; `[56-59]` sub_no; `[60-61]` tar_id (after cover); `[62]` cursor;
  - `[63]` b0 meteor_miss, b1 short_summon, b2 cover;
  - `[64-65]` magic_caster_id; `[66]` vfxKind; `[67-70]` vfxNum; `[71-74]` PatchedVfx; `[75]` host Speed.
- **END, 52 bytes:** the inert record with flags 0x08, then `[49] kind 3 [50-51] actId`.
- **Parsing.** `TryParseAction` (`:1771-1805`) reads the 46 bytes as today. A separate `ReadActionExt` runs only when
  `Length >= 52 && payload[46] == 0xA6`, inside its own try. A bad or unknown extension leaves `HasExt = false` and
  never fails the frame.

**What an old peer does with type 6:**
- **An s110 guest.** The parse reads 46 bytes and never sees the extension. START and END resolve neither 0xFF slot
  and return at `NetSyncDiorama.cs:1791-1792` with no state, no motion and no log. Impacts behave exactly as today.
  Bit 5 is stored in `HostCaps` and never read.
- **A new guest with an s110 host.** No START, END or extension arrives, so every impact takes the legacy route (the
  s110 swing, then fallback A from s136). It logs once: "host predates action replay".

**Selftest loopback.**
- Every parsed payload also goes to `ActLoopAudit`, which counts STARTs, ENDs and impacts with an extension, and
  checks pairing.
- With `actbench tape rec` on, it records (tick, bytes), capped at 1024 frames.

#### 3.3.3 s134 — guest action replay (AR2)

**New file `Memoria/Netsync/NetSyncDiorama.Replay.cs`.** `NetSyncDiorama` becomes `partial`. The prefix is `Act`,
because `AbortReplay` and `ReplayArmTick` already belong to the result-screen replay.

**Intake.** `ActionTick` (`:1750-1761`) and the selftest bench inbox both route through `ApplyActionPayload`. That
applies the real `TryParseAction` plus the extension, and the nonce gate (bench frames skip only the nonce gate). It
then dispatches:
- `IsStart` → `ActStart`;
- `IsEnd` → `ActHostEnd`;
- anything else → `ApplyActionFrame`.

**`ActStart` declines** each reason once per boot, logged and published:
- `[Netsync] ActionReplay=0`, or the `actbench replay off` lever;
- this machine has no SFXRework (`Configuration/Access/Battle.cs:10`), since `Loop` returns at once without it
  (`UnifiedBattleSequencer.cs:27-28`);
- the end is already being presented;
- **stale:** its own END arrives in the same drain, meaning the host already finished it. The START's `_seq` is kept
  for logs only, because seq distance is not a time bound. **(review replay F6)**
- the actor is unresolved or hidden;
- the actor is dead or dying — **unless** stock would run it. Stock lets a Death-status caster run
  `cmd_no > EnemyCounter && cmd_no <= BoundaryUpperCheck` (EnemyDying 54, EnemyReaction 55; `btl_cmd.cs:940-941` [V]).
  The replay mirrors that while `die_seq < 5` and the actor is not deleted. **(review replay F3)**
- Unknown kind;
- a monster-transform command;
- a zero mapped target mask;
- six replays already running.

Two further rules:
- Kind NONE is recorded as NOOP: impacts apply at once, with no fallback clip.
- Per actor, as at the host's Speed >= 4 dequeue: a new START waits while the actor's running replay still holds its
  command motion. One pending start is kept, and a newer one replaces it. After 1500 ms the running replay is
  hard-aborted.

**`ActLaunch`: a standalone CMD_DATA that never enters SetCommand, EnqueueCommand or the queue.**

```csharp
CMD_DATA rc = new CMD_DATA(); btl_cmd.ClearCommand(rc); btl_cmd.ClearReflecData(rc);
rc.regist = actor; rc.cmd_no = (BattleCommandId)s.CmdNo; rc.sub_no = s.SubNo;
rc.SetAAData(btl_util.GetCommandAction(rc));                 // as btl_cmd.cs:176 / :416
rc.ScriptId = btl_util.GetCommandScriptId(rc);
rc.tar_id = ActMapMask(s.TarId); rc.magic_caster_id = ActMapMask(s.MagicCaster);
rc.info.cursor = s.Cursor; /* meteor_miss, short_summon, cover */ rc.IsShortRange = btl_util.IsAttackShortRange(rc);
rc.PatchedVfx = (SpecialEffect)s.PatchedVfx; rc.info.mode = command_mode_index.CMD_MODE_LOOP;
if (actor.bi.player != 0) { btl_mot.setMotion(actor, MP_IDLE_CMD); actor.evt.animFrame = 0; }   // (review replay F7)
_actByCmd[rc] = rec; ActLive = true;                         // BEFORE Execute: a same-frame hit already short-circuits
if (kind == SPECIAL) new UnifiedBattleSequencer.BattleAction(EffectType.SpecialEffect, num).Execute(rc);
else if (kind == ENEMY && scripted) new UnifiedBattleSequencer.BattleAction(EffectType.EnemySequence, num).Execute(rc);
else btl_vfx.SelectCommandVfx(rc);
rec.Action = UnifiedBattleSequencer.runningActions.FindLast(x => x.cmd == rc);
if (rec.Action == null) -> DECLINED "no sequence started on this install"
```

The command-stance line follows the host. [V] The host's SELECT_VFX waits for CMD stance (`btl_cmd.cs:588-595`), so
its first `WaitAnimation: Caster` is skipped (`UnifiedBattleSequencer.cs:213-216`). Nothing on the guest ever sets
`cmd_idle` (R9 refuses SetCommand; netsync only clears it, `NetSyncDiorama.cs:2155`). Without this line every player
replay would first wait out an idle loop.

[V] The replay is never in `cur_cmd_list`, so none of the following ever runs on it:
- `IncreaseAAUsageCounter` or `ItemUse` (`:626-643`);
- `UpdateCommandAchievement`;
- `FinishCommand`'s ATB and trance writes (`:1289-1393`);
- SetCommand's caster writes.

**The hit short-circuit.** It is the first statement of `ExecVfxCommand` (`btl_cmd.cs:1521`):

```diff
 public static void ExecVfxCommand(BTL_DATA target, CMD_DATA cmd = null, BattleActionThread sfxThread = null)
 {
+    if (Memoria.Netsync.NetSyncDiorama.ActLive && Memoria.Netsync.NetSyncDiorama.ActOnHit(target, cmd, sfxThread))
+        return;   // a REPLAY computes nothing: no CalcMain, no SysTrans model/achievement, no SysLastPhoenix phase flip
```

- `ActOnHit` returns true for any registered replay CMD_DATA, matched by reference, even on an internal exception.
  It returns false for null and for every real command.
- In s134 it only counts hits, and for a **Change** replay it performs the presentation half. **(review replay F4)**
  - [V] `SequenceChange.seq` moves the caster ±400 on `CasterRow`, then runs EffectPoint. The row switch lives in
    CalcMain's script 0055 → `btl_para.SwitchPlayerRow` (`btl_para.cs:336-341`).
  - So `ActOnHit` calls `SwitchPlayerRow(rc.regist)` once, which writes only the diorama BTL_DATA's row, base_pos and
    pos. `SavePlayerData` is Active-gated. The busy-window restore then skips that actor's base_pos and row.

**A tripwire for re-simulation. (review replay F1)**
- [V] The diorama boots with `isDebug = true` (`NetSyncDiorama.cs:408`), so `SetDamage` and `SetMpDamage` skip their
  HP and MP writes (`btl_para.cs:153`, `:221`). An invariant snapshot after an Attack replay is therefore blind to a
  fall-through.
- s134 counts CalcMain entries while booted, at the head of the 5-argument `SBattleCalculator.CalcMain`
  (`SBattleCalculator.cs:35`): `if (NetSyncDiorama.Booted) NetSyncDiorama.NoteCalcWhileBooted();`. That is one static
  read per hit and never per frame. The count is published as `act.guest.calc_while_booted`.
- A selftest-only lever, `actbench shortcircuit off`, makes `ActOnHit` return false for the next replay. This proves
  the counter can go red, and only on the sandboxed selftest save. A heal leg adds a second observable, because
  `SetRecover` is NOT isDebug-gated (`btl_para.cs:197-200`).

**Idle and busy hooks.** All sit behind the static `ActLive`, which is false on vanilla, solo, the host and an idle
guest.
- `IsBtlUsingCommandMotion` (`btl_util.cs:96-105`): a running replay's actor whose replay still holds its command
  motion counts.
- `IsBtlBusy` ANY_CURRENT (`:107-118`): the replay's actor, targets (and reflect targets) and magic caster count.
- `IsBtlBusy` ANY_QUEUED (`:119-128`): a `die_atk` enemy inside its **death-attack grace** counts as a
  QUEUED_CASTER. **(review replay F3)**
  - The grace is 1500 ms from the release of its lethal impact, and applies only when the host advertises bit 5.
  - [V] The guest's death apply then leaves `die_seq` at 0, the stock path for a die_atk enemy with a queued death
    attack (`DeathStatusScript.cs:30-33`). So the EnemyDying START has time to arrive.
  - It self-heals: the next animation-loop end sets `die_seq = 1` once the grace expires (`btlseq.cs:339`).
- The no-argument `IsBtlUsingCommand` and `IsBtlTargetOfCommand` (`:80-94`) consult replays. The `out` overloads stay
  stock.

**Sequencer hunks.**
- `Loop` (`UnifiedBattleSequencer.cs:32-43`) runs a replay action through `ActExecuteLoopGuarded`. [V] Today one
  throwing action aborts every action for the frame through the single outer catch (`:29-51`).
- `ReleaseRunningAction` (`:62`) changes from private to internal.
- Camera parity at `:344` and `:828` uses `ActSpeedFor(cmd)`: the host's Speed for a replay.
- `PlaySound` Song (`:913-915`) notes the song id against the replay, for `StopSong` on abort.
- `TrySetVariable` (`BattleActionCode.cs:676-`) gains an optional CMD_DATA from `:1057`. For a replay, `btl_seq` is
  refused and `cmd_status` may change only bit 1.

**Teardown. (review replay F2)**
- `ForceDisarm` (`NetSyncDiorama.cs:612-646`) gets `try { ActDiscardAll("teardown"); } catch { }` after
  `AbortReplay` and before `Disarm`. It drops records and held impacts, clears `_actLifeMask` and clears `ActLive`.
  **It never applies anything.**
  - [V] `ForceDisarm` sets `_booted = false` first (`:616`). With Active false, a held player kill would write the
    save-serialized `achievement.abnormal_status` (`btl_stat.cs:129-130`, `BattleAchievement.cs:186`).
  - `SFX.EndBattle` right after (`HonoluluBattleMain.cs:876-878`) releases every running action.
- `LeaveFrom` (`:566-600`) still releases and restores while Active is true, but every per-record step has its own
  try/catch, so the scene Replace is always reached.
- `ActAbortAll` also runs:
  - on the first R8 hit (NoteR8);
  - on W3: any injected end (victory, flee, annihilate, defeat, close) plus 4 s. Until then the guest's trailing loop
    waits on `SFX.IsRunning()` (`battle.cs:291`), as the host's does;
  - from `actbench clear`.
- `ActTick` aborts a replay still running 6 s after the host's END, after a 90 s cap, or when its actor is gone.
- **Busy-window restore.** When the running count goes 0 → 1, snapshot each linked unit's rot, scale, disappear,
  meshflags, mesh_current, shadow and base_pos. When it returns to 0 after an abort, restore them, then set
  pos = base_pos, `SetDefaultIdle`, reset the bbg intensity, `UnshiftWorld`, and `CameraNo = 0`. Nothing is restored
  after a natural end.

**Interactions.**
- An impact paired with a running or queued replay skips the player MP_ATTACK swing (`:1845-1852`).
- A replay never touches ReadyQueue, CurrentPlayerIndex or SetIdle, so the guest's stock menu (s102-s107) is
  unaffected apart from cmd_status bit 1, as on the host.
- `[Netsync] ActionReplay` (default 1) is a behaviour key in `bsig`.
- Call order:
  - transport: Pump → ActionTick → **ActTick** → DioramaTick → ReconcileTick → LiveTick → EndTick → StockMenuTick;
  - selftest: SelfTestPump → **ActionTickBench → ActTick** → EndTick → StockMenuTick → LiveTick.

#### 3.3.4 s135 — numbers, flinch and death wait for the replay's hit (AR3)

**On arrival** (`ApplyActionFrame`, after the stat-tick branch): if the impact's id pairs with a queued or running
replay and the hold is on:
- the non-life state lanes and the horizon gate apply NOW, so HP and MP bars follow the host (owner decision);
- figures, the flinch and a life change are kept in `HeldImpact{..., Seq = a.SeqHorizon}`;
- a lethal or revive change sets `_actLifeMask |= 1 << slot`;
- if the replay has already hit that target (a "credit"), the impact releases at once ("late").

**Release at the hit** (`ActOnHit`):
- The match key is the master unit, as `ResolveWireSlot` uses it.
- The held figures are written into `target.fig` (and the caster's triple for drain). EffectPoint collects them and
  shows them at the sequence's own Figure point, and the sequence's branches see the host's result. Modifiers stay
  empty (the F4 law).
- Then the flinch, decided from wire lethality first (the F5 law). Then the kill or revive.
- One held impact is released per call, oldest first per target.

**Held life changes respect newer frames. (review replay F9)**
- `_lastAppliedSeq[slot]` is stamped by every frame applied immediately, stat ticks included.
- At release, the held kill/revive and its raw HP/MP apply only if `(Int16)(h.Seq - _lastAppliedSeq[slot]) > 0`.
  Otherwise only the figure and the flinch show, logged "superseded".
- A STAT_TICK frame for a slot with a pending held life change queues behind it. [V] The STAT_TICK branch otherwise
  writes absolute values at once (`NetSyncDiorama.cs:1810-1822`, `:1890-1905`).

**Other releases** take the legacy path:
- "end": the replay finished without hitting that target;
- "host-done": the host's END + 1500 ms;
- "timeout": 2500 ms after arrival;
- "abort".

**Reconciler.** `ApplyUnit`, after the horizon gate (`:1530-1535`):
`if ((_actLifeMask & (1 << u.Index)) != 0) return;`. A paired replay owns that slot's kill or revive until its hit.
This skip is the only protection against the next post-horizon type-1 sample killing the target early.

#### 3.3.5 s136 — fallback A: one stock clip per action (AR4)

- This replaces the player-only MP_ATTACK swing (`NetSyncDiorama.cs:1845-1852`) for any impact no replay covers: an
  old host, a declined, stale or dropped START, or a guest without SFXRework.
- It plays at most once per action, keyed by `(nonce, actId)`, or for an old host by (caster, cmd, sub) within 500 ms.
- Guarded by `CanPlayCosmeticMotion` (`:1912`): not lethal, not revive, not hidden, not self-cast.
- **Clip choice:**
  - player Item/AutoPotion/Throw → MP_ITEM1;
  - player magic (category & 16) → MP_MAGIC;
  - Defend/Change → none;
  - other player commands → MP_ATTACK;
  - an enemy → the first caster `PlayAnimation` of its scene sequence. The sequence is parsed and never executed
    (`BattleActionThread.cs:202-238`), cached per (scene, sub), and played through `btl_mot.setMotion(d, String)`.
    [V] An enemy's mot table has 6 entries, so an index would throw.

#### 3.3.6 s137 — trance burst timing (AR5)

- The host's SysTrans START is kind 3, with Activate or End resolved on the host.
- The guest replays the burst. `ActOnHit` for a SysTrans replay calls `btl_vfx.SetTranceModel(actor, ...)` when the
  worn model differs.
- The reconciler's model check (`:1610-1615`) waits while that unit has a SysTrans replay that has not hit. With
  host bit 5 it also waits a 400 ms grace for the START, because type 1 and type 6 arrive in either order [I].

### 3.4 The guest's own field model (s138-s141)

#### 3.4.1 What exists [V]

- `SetModel` (0x2F, `EventEngine.DoEventCode.cs:1084-1132`) does `po.model = getv2()` (`:1086`) and
  `po.eye = -4*getv1()` (`:1088`). In field mode it creates the model from `FF9BattleDB.GEO.GetValue(po.model)`,
  including Garnet's hair (`:1091-1099`), then registers the character (`:1115-1121`).
- `DefinePlayerCharacter` (0x2C, `:1033-1045`) sets `controlUID`.
- The warm battle return deep-copies objects. `PosObj.copy` (`PosObj.cs:37-93`) carries model, anim, frameN and
  eye, and `updateModelsToBeAdded` rebuilds from `posObj.model` plus the stored loco ids (`updateModelsToBeAdded.cs:21-28`).
- Collision comes from the script (`4B`), not the model, so L1 is safe.
- The guest learns the host's party at `ApplyStoryBeforeEvents`, before `StartEvents`
  (`HonoluluFieldMain.cs:148-149`; `NetSyncClient.cs:524-565`). It does not know its own slot. That is the one wire need.

#### 3.4.2 s138 — instrument (M1, inert)

Harness keys only:
- `player.{model, anim, geo, anim_geo, eye, uid, sid}` and `objects[i].model`;
- a new top-level `dress` block with per-key Try: `ghost{model, geo, clip, rig}` and `party[4]`;
- `NetSyncVisitor.FolderOf(clip)`, AnimationFactory's naming rule.

No behaviour changes on any role. Later benches can then go red on VALUES, not on missing keys.

#### 3.4.3 s139 — host rule and section 8 (M2)

**Rig table** (`NetSyncVisitor.cs:34-53`).
- Each row gains Eye, Inactive and footfall frames: Zidane eye 93, Vivi 61, Garnet 91, Steiner 104, Freya 94,
  Quina 92, Eiko 63, Amarant 122.
- New row 8: MOOGLE, model 220 `GEO_NPC_F0_MOG`, idle 2904, walk 2927, run 2907, turnL 2923, turnR 2911, eye 50, no
  footsteps (stock fields 115/150/206).

**Guards. (review dress F8)**
- `MainRigCount = 8` guards only the party-member path inside the new `ResolveAuto`, so CharacterId 8 (Cinna) never
  hits the moogle row.
- The named path keeps `< Rigs.Length` (`:140`), so `GhostAs=moogle` works. A named moogle sends charId 0xFF.

**`ResolveAuto(mask, moogleWhenEmpty)`.**
- It returns the first named GuestSlots slot that holds a member; a member outside 0-7 → 0 (no dress).
- When every named slot is empty, it returns the moogle, but only if `moogleWhenEmpty`.
- That flag is derived **at call time from the live role**: host or selftest. It is never a config-time static,
  because `HarnessSelfTest` sets `_role` directly (`NetSyncClient.cs:3600-3605`). **(review dress F7)**

**The host's ghost wears the dress only when the guest's wire body is plain Zidane or already dressed. (review dress F3)**

```diff
 UInt16 dressModel = NetSyncVisitor.ResolveDress(_guestSlots, out dressRig);          // NetSyncClient.cs:1305
+if (dressModel != 0 && rs.Model != 98 && rs.Model != dressModel) dressModel = 0;     // a non-Zidane leader, 532, an opted-out guest: show it as it is
```

The selftest branch (`:1180`) gets the same guard. Both screens then agree in every case.

**Section 8 producer.**
- `BuildStateFrame` (`NetSyncClient.cs:1906-1925`, after the section-7 append) adds
  `AppendSection(all, SectionDress, DressSectionBody(model, charId))` on the host.
- The selftest role builds it only for the codec proof.
- Old guests skip it by id and length [V]: `ApplyStoryTo` applies id 0 only (`NetSyncState.cs:113-128`),
  `ParseSections` consumes 1-3 (`NetSyncParty.cs:224-245`), and `TryReadSection` stops at the first match.

#### 3.4.4 s140 — the guest dresses itself (M3)

**Arming.**
- `NetSyncSelfDress.ArmFromState` runs right after `ApplyStory` in `ApplyStoryImpl` (`NetSyncClient.cs:555`).
- It disarms, with a reason, when:
  - `[Netsync] SelfDress=0`;
  - section 8 is absent;
  - model is 0;
  - **charId is 0, because the slot member is Zidane and a dress would only strip Zidane's own presentation**
    **(review dress F4)**;
  - there is no rig row;
  - the effective field is 70 or 3000-3012. This uses `Memoria.DataPatchers.EffectiveFieldId`, so forks of those
    ids are excluded too **(review dress F2)**.
- A skipped apply during `_storyMirroring && client` keeps the last arm (sticky through a blip).
- `Clear()` runs at the exit ramp (`:1074`), in `OnDestroy` (`:1394`) and in `ApplyConfigChange`.
- In selftest, `ApplyStoryBeforeEvents` (`:500`) calls `ArmBench()`. The bench spec goes through the real encoder
  and reader first.

**Dress at SetModel** (after `DoEventCode.cs:1088`):

```diff
 po.eye = (Int16)(-4 * this.getv1());
+if (this.gMode == 1 && (Memoria.Netsync.NetSyncSelfDress.Armed || po.netSelfDress != 0))
+    Memoria.Netsync.NetSyncSelfDress.AtSetModel(this, po);   // rewrites po.model/po.eye BEFORE the GEO lookup
```

```csharp
// AtSetModel -- gate order matters (review dress F5)
asked = po.model;
if (po.netSelfDress != 0) { if (asked == 98) { po.model = Rig.Model; po.eye = -4*Rig.Eye; }
                            else { po.netSelfDress = 0; po.netDressSrc = 0; log "re-modelled -> dress dropped"; } return; }
if (!Armed || asked != 98 || !NetSyncClient.IsClientOrSelfTestRole || ExcludedField()) return;   // 98 only (review dress F4)
if (Gate && !EntryDefinesPlayer(ee, po.sid)) { SkipNpc++; log once; return; }                       // the player gate FIRST
PosObj ctl = ee.GetControlChar(); if (ctl != null && ctl != po && ctl.netSelfDress != 0) { SkipSecond++; return; }
po.netDressSrc = asked; po.netSelfDress = (Byte)(WantRig + 1); po.model = WantModel; po.eye = (Int16)(-4 * Rigs[WantRig].Eye);
```

`EntryDefinesPlayer` parses the entry with `EventEngineUtils.BinaryScript.Entry` and caches the result on the
`allObjsEBData[sid]` reference. It is true when any function contains 0x2C. If the parse throws (the parser's table
ends at 0x111, while Memoria's ops reach 0x11E), it falls back to the character-entry band `sid >= sSourceObjN - 9`.

**PosObj** gains `Byte netSelfDress` and `UInt16 netDressSrc`, and `PosObj.copy` copies both (beside garnet and
shortHair, `PosObj.cs:72-73`). Vanilla never sets them.

**Animations: keep the raw id for stock checks and the frame timeline. (review dress F1, F2)**
- **Loco setters.** AIDLE (`:1134-1176`), AWALK, ARUN, ASLEEP, ATURNL, ATURNR, AJUMP and AANIM_EX map their id
  AFTER the case's stock code has run, then attach the mapped clip. The `effMapNo` checks keep the raw id.
- **RunAnimation / RunAnimationEx:**

```diff
 Int32 anim = (UInt16)this.getv2();
 ... the jump-rope fixes (raw) ...
 AnimationFactory.AddAnimWithAnimatioName(actor.go, FF9DBAll.AnimationDB.GetValue(anim));   // stock: the raw clip is attached (never played on a dressed body)
+Int32 play = actor.netSelfDress != 0 ? Memoria.Netsync.NetSyncSelfDress.MapAnim(actor, anim) : anim;
+if (play != anim) AnimationFactory.AddAnimWithAnimatioName(actor.go, FF9DBAll.AnimationDB.GetValue(play));
 if (this.gMode == 1) {
     ...
-    this.ExecAnim(actor, anim);
+    this.ExecAnim(actor, play);
+    if (play != anim) Memoria.Netsync.NetSyncSelfDress.KeepSourceTimeline(actor, anim);   // frameN = the SOURCE clip's frames
     ... the effMapNo 307/561/1601/1605/2934 checks keep `anim` (raw) ...
```

- `KeepSourceTimeline` sets `actor.frameN = GetCharAnimFrame(actor.go, anim)`. That works because the raw clip is
  attached (`EventEngineUtils.cs:1836-1843`).
- [V] The field animation plays at `time = animFrame / frameN * length` (`FieldMapActorController.cs:418`, `:426`).
  The dressed idle therefore plays stretched across the source timeline.
- [V] Stock cutscenes wait on the player's frame number, through `GetEntryAnimFrame`, which reads `animFrame`
  (`EBin.cs:1845-1846`). Field 307 runs `RunAnimation( 2597 )` then `while ( GetEntryAnimFrame(255) < 58 )`
  (`test2_87.txt:1468-1562`), and ProcessAnime never lets `animFrame` pass `frameN - 1`
  (`EventEngine.ProcessAnime.cs:85-109`). With the stretch, those loops still end.
- [V] The Crystal World PreEnding trigger (`effMapNo == 2934 && actor.uid == 2 && anim == 12429`, `:1372-1383`) still
  fires.
- `MapAnim(actor, id)`:
  - the dressed character's own clips pass through;
  - other clips are classified by name suffix: IDLE, WALK, RUN, TURN_L, TURN_R, BREAK*;
  - anything else becomes the dressed idle;
  - an exception returns the dressed idle.

**DefinePlayerCharacter (`:1043`).** `NoteControl` counts `confirmed` (control bound to the dressed body) and
`ctl_elsewhere` (a co-actor binder).

#### 3.4.5 s141 — polish (M4)

- **Lighting.** `fldmcf.cs:81` falls back to the `netDressSrc` row (98) when the worn model has no mapconfig row.
  This mirrors the ghost's fallback (`NetSyncClient.cs:~4366`).
- **Mesh ops.** MESHSHOW/MESHHIDE (`:1270-1284`) on the dressed body are dropped. Their arguments are already
  consumed.
- **Footsteps.** CHRFX 16-19 (`:2010-2014`) go through `MapFootstep`:
  - a source Zidane walk/run key maps by ordinal to the dressed rig's stock footfall frames;
  - the moogle and Quina drop their keys, as in stock;
  - the surface sound id is kept.
- **Props.** `geoAttach` counts props attached to a dressed body (log only).

---

## 4. Combined build order

Each row is **one DLL build (`py tools/build_memoria.py`, which backs up first and auto-deploys) plus one solo bench,
calibrated first on the DLL deployed just before it.** Patches are emitted against live minus the change, and numbers
are taken in this order.

**Renumbered after the owner's answers (2026-10-13).** The owner chose two sittings, the swirl clamp, and the gil relay.
So the clamp and the gil relay move into group 1, next to the patches they belong with. Every patch number in this
document already uses the new numbering. The lane designs (and the workflow journal) used the old numbers: old
s130 -> s112, s112 -> s113, s113 -> s114, s114 -> s115, s129 -> s116, s115 -> s117, s116-s128 -> s122-s130.

| # | Patch | Feature | Runs on | Solo bench |
|---|---|---|---|---|
| 1 | `s111-netsync-intro-mirror` | host publishes intro choice; diorama applies it; LiveTick timing | both | `coop_battle_intro_mirror.py` |
| 2 | `s112-netsync-diorama-swirl-clamp` | clamp the diorama swirl (owner: clamp to the desktop's, default 0) | guest | `coop_battle_intro_mirror.py` leg S |
| 3 | `s113-netsync-wait-parity` | control byte 2/3; host Wait freezes below the root only | both | `coop_battle_wait_parity.py` |
| 4 | `s114-netsync-start-hold` | control trailer; host gauge hold until the guest is live | both | `coop_battle_start_hold.py` |
| 5 | `s115-netsync-guest-flee-presentation` | run-away, R9b, kind-aware W2, scoped no-leak rule | guest | `coop_battle_flee_defeat.py` part a |
| 6 | `s116-netsync-flee-gil-relay` | host's "Dropped N Gil" on the guest (owner: build it) | both | `coop_battle_flee_defeat.py` part c |
| 7 | `s117-netsync-guest-defeat-presentation` | annihilation / var-34 / CLOSE rows; kill and phase-defeat ops | guest | `coop_battle_flee_defeat.py` part b |
| -- | **two-machine sitting A** | | both | section 7 |
| 8 | `s133-netsync-host-action-start-lane` | START/END, impact ids, header bit 5, loopback audit, tape | host | `coop_action_host.py` |
| 9 | `s134-netsync-guest-action-replay` | standalone-CMD_DATA replay, short-circuit, hooks, tripwire | guest | `coop_action_replay.py` |
| 10 | `s135-netsync-replay-hit-hold` | numbers, flinch and death wait for the hit; life-mask skip | guest | `coop_action_hold.py` |
| 11 | `s136-netsync-replay-fallback-clip` | one stock clip per uncovered action | guest | `coop_action_fallback.py` |
| 12 | `s137-netsync-replay-trance-timing` | trance burst + model swap at the hit | guest | `coop_action_trance.py` |
| 13 | `s138-netsync-dress-instrument` | harness keys only | none (inert) | `coop_self_dress.py` leg I |
| 14 | `s139-netsync-dress-host-rule` | rig rows, moogle, ResolveAuto, section 8, host ghost guard | host | `coop_self_dress.py` leg G |
| 15 | `s140-netsync-guest-self-dress` | dress at SetModel, MapAnim + timeline, PosObj carry | guest | `coop_self_dress.py` legs S/W/X/N/T |
| 16 | `s141-netsync-self-dress-polish` | lighting row, mesh-op drop, footfall map | guest | `coop_self_dress.py` leg F |
| -- | **two-machine sitting B** | | both | section 7 |

**Why this order.**
- Start sync, Wait parity and flee/defeat are small, touch few stock files, and close the owner's first report.
- The replay is the biggest and touches the most stock battle code. It lands second, so its benches run against
  the final end presentation. W3 and BattleTrailingLoop's wait on `SFX.IsRunning()` cover flee and defeat as well as
  victory.
- The dress touches field opcodes only and is independent of battle.
- s113 changes the loopback's root byte, and s115/s117 move existing checks under `guest hold`. Landing them early
  settles the regression baselines before the replay's long bench.

**Hygiene for every row.**
- Back up before the build; DLL builds auto-deploy over the live install.
- One change per in-game test.
- Audit the shared clone's uncommitted stack before the first build.
- Re-read `memoria-patches/README.md` before each emit, and add one README row per patch.
- New `.cs` files (s134 `NetSyncDiorama.Replay.cs`, s140 `NetSyncSelfDress.cs`) need a csproj `<Compile Include>`.

---

## 5. Harness additions (protocol stays 5; additive only)

**Rules.**
- Every new key under `netsync.*` also gets its sentinel inside the `AppendNetsync` catch literal
  (`HarnessAgent.cs:2961`), and `test_harness_netsync.py` re-pins that literal per patch. This includes the end
  lane's new `end` keys; the lane design's "the literal does not change" was wrong, because s104-s109 added theirs.
- Every verb or lever is selftest-only and is released by `HarnessReleaseBench` (`NetSyncBattle.cs:2547-2575`) and
  the end/act/dress release paths.
- **Old-engine safety.**
  - An engine before a patch reads an unknown `netsync bench <op>` as `bench 1`, which turns the field-gate bench ON
    (`HarnessAgent.cs:1062-1063`, `:1086`). The driver therefore sends each new `bench` op only when its key is
    present (`NETSYNC_BENCH_OPS`).
  - `bench lapse <ms> reserve` needs no guard. An s110 engine rejects a 4-argument lapse (`:1070-1071`), so it fails
    closed.

### 5.1 Engine verbs and keys, per patch

| Patch | Verbs / ops (selftest) | Keys |
|---|---|---|
| s111 | `battle <scene> [group] [rand]`; `netsync dioboot <scene> [pattern] [wire] [skip\|play\|own] [rand]` (`wire` = the F6 wire bench: flags 0x01, or 0x0D/0x09 with `skip`/`play`; `wire rand` is refused); `bench intro 1\|0`; `bench cfg skipcam 0\|1\|restore` | `netsync.battle.host.cfg {atb, skip_btl_camera, speed, swirl_frames}`; `netsync.battle.host.intro {off, published, own_skip}`; `netsync.diorama.intro {wire, applied, own, off, calls, normal_ms, swirl_frames}` |
| s113 | `bench waitparity 1\|0`; `bench ctl auto\|shut\|legacy\|root\|deep`; `bench cfg atb wait\|active\|restore`; `bench lapse <ms> reserve` (the last frame re-served for 2000 ms, then silence) | `netsync.battle.host.wait {parity_off, menu, open, deep, legacy_seen}`; `netsync.battle.menu.ctl {menu, hex, src}`; feed gains `ctl`, `ctl_menu` |
| s114 | `bench boot auto\|none\|booting\|live\|declined\|busy\|stale\|silent\|late <ms>`; `bench starthold 1\|0\|cap <ms>` | `netsync.battle.host.start_hold {off, cap_ms, state, nonce, why, release, held_ms, late_ms, count, released{live, declined, link, oldguest, cap, ended}, guest{r3, lane_ms, fmt, nonce, boot, boot_name}}`; `menu.ctl` gains `nonce, boot, boot_name`; `netsync.diorama.live {latched, ms, nonce}` |
| s115 | `endbench guest hold\|nor9b` | `netsync.battle.end.flee {r9b, bypassed, overload, ability_flag, gil_now, penalty}`; `end.action` gains `flee`; `end.end_leave.reverted` (-1 = none); `battle.units[]` gains `mot`, `disappear`, `z` |
| s117 | `endbench kill [mask]`; `endbench phase-defeat` | `end.follow_msg`; `end.action` gains `annihilate`, `defeat` |
| s133 | new sub-verb `netsync actbench`: `tape rec\|stop\|clear\|info`, `hoststarts on\|off` | `netsync.battle.act.host {on, lever_off, starts, ends, ext_impacts, noid_impacts, scripted, kinds{...}, last{...}, loop{starts, ends, impacts_ext, paired, orphans, caster_mismatch, no_end}, tape{state, frames, starts, ms}}` |
| s134 | `actbench feed <hex>`, `feedat <ms> <hex>`, `tape play [pct]`, `replay on\|off`, `rework on\|off`, `shortcircuit on\|off`, `clear` | `netsync.battle.act.guest {on, why, rework, knob, host_caps, levers{...}, inbox, starts_rx, started, queued, running, declined, declined_why, stale, superseded, noop, aborted, abort_why, ended, faulted, hits, credits, swing_skipped, calc_while_booted, window{open, restores}, last{...}}`; `battle.units[]` gains `anim`, `anim_frame`, `away`, `rot_y`, `acting` |
| s135 | `actbench hold on\|off`; `actbench lifeskip on\|off`; `actbench unit <slot> dead\|alive\|trance0\|trance1` (sample seq = the slot's gate seq + 1, so it is post-horizon) | `act.guest.hold {on, held_now, held, rel_hit, rel_late, rel_end, rel_hostdone, rel_timeout, rel_abort, superseded, life_mask, figs[16]}` |
| s136 | `actbench fallback on\|off` | `act.guest.fallback {on, clips, deduped, last{actor, clip, cmd, sub, keyed_by}}` |
| s137 | `actbench trancegrace on\|off` | `act.guest.trance {deferred, swaps_by_hit, swaps_by_grace}` |
| s138 | — | `player.{model, anim, geo, anim_geo, eye, uid, sid}`, `objects[].model`, `dress.ghost{model, geo, clip, rig}`, `dress.party[4]` |
| s139 | new sub-verb `netsync selfdress`: `ghost <mask>\|off`, `empty <slot>\|off`, `clear` | `dress.ghost.bench_mask`, `dress.ghost.empty_slot`, `dress.codec`, `dress.rig_idle_frames[9]` (each rig idle's frame count) |
| s140 | `selfdress self <off\|auto [mask]\|zidane..amarant\|moogle>`; `selfdress gate 1\|0` | `dress.self {knob, armed, src, want_model, want_char, rig, why, uid, net_byte, from, confirmed, ctl_elsewhere, skip_npc, skip_second, remaps, timeline_kept, gate}` |
| s141 | — | `dress.self.steps`, `steps_dropped`, `light_row`, `mesh_drops`, `attach_notes`; `player.meshflags` |
| s116 | `endbench fleegil <n>\|none` | `host.end.flee_gil`, `peer.end.flee_gil`, `end.flee.msg_gil` |
| s112 | `bench swirl local <frames>\|ini` | `netsync.diorama.intro.swirl_clamp` |

### 5.2 Driver, fake and tests (repo)

- **`tools/harness/session.py`**
  - `NETSYNC_SUBVERBS` appends `actbench` (s133), then `selfdress` (s139), in the agent's order.
    `NETSYNC_AUTHORITY_SUBVERBS` gets both as well, so the capability gate runs BEFORE the step is spent
    **(review dress F6)**.
  - `NETSYNC_BATTLE_SUBVERBS` gains `actbench` keyed on `netsync.battle.act` (s133). A new `NETSYNC_DRESS_SUBVERBS`
    keys `selfdress` on `dress.ghost.bench_mask` (s139), and a per-op table puts `self` and `gate` on `dress.self`
    (s140).
  - `NETSYNC_BENCH_OPS` gains:
    - `intro`, `cfg` → `netsync.diorama.intro` (s111);
    - `waitparity`, `ctl` → `netsync.battle.host.wait` (s113);
    - `boot`, `starthold` → `netsync.battle.host.start_hold` (s114);
    - `swirl` → `netsync.diorama.intro.swirl_clamp` (s112).
  - `NETSYNC_ENDBENCH_OPS` gains `phase-defeat` and `kill` (s117) and `fleegil` (s116), each with its
    `NETSYNC_ENDBENCH_OP_CAPS` entry. The `guest hold|nor9b` values are cap-gated on `netsync.battle.end.flee` (s115),
    and an s110 engine's answer `netsync endbench guest: needs on|off|settle` goes into
    `NETSYNC_ENDBENCH_OLD_ANSWERS`.
  - Per-stage `actbench` op availability is keyed on `act.guest` (s134), `act.guest.hold` (s135),
    `act.guest.fallback` (s136) and `act.guest.trance` (s137).
  - Helpers: `hold_window()`, `atb_flat()`, `ctl_byte()`, `netsync_actbench()`, `selfdress()`.
- **`tools/harness/channel.py`**: State accessors for every new key. An absent key reads None.
- **`tools/harness/battlewire.py`**:
  - constants `FLAG_INTRO_SKIPPED=4`, `CAP_INTRO_MIRROR=8`, `FLAG_START_HOLD=16`, `CAP_ACTION_STARTS=32`;
    `CTL_SHUT/LEGACY/ROOT/DEEP`; `CTL_FMT1`; `BOOT_NONE..BUSY`; `VFX_KIND_*`;
  - `control_hex(menu, nonce=None, boot=None)`, `decode_control(frame, host_nonce)` (with the nonce gate),
    `wire_intro(flags)`;
  - pure mirrors `guest_boot_state(...)` and `start_hold_verdict(...)`;
  - `encode_action_impact` (46 or 52 bytes), `encode_action_start` (76), `encode_action_end` (52), `decode_action`,
    and `decode_action_legacy` (exactly the s110 46-byte reader).
- **`tools/harness/fakegame.py`**: capability rungs in lockstep (`intro`, `waitparity`, `starthold`, `flee`, `defeat`,
  `actstart`, `actreplay`, `acthold`, `actfallback`, `acttrance`, `dressinstr`, `dresshost`, `selfdress`,
  `dresspolish`, `fleegil`, `swirl`), with the fake keys and verbs.
- **`ff9mapkit/tests/test_harness_netsync.py`**:
  - re-pin the catch literal, the sub-verb tuples, `NETSYNC_BENCH_OPS` and the endbench lists;
  - unit-test the control codec, the nonce gate, `guest_boot_state`, `start_hold_verdict` and the action codec. The
    action codec cases: hand-checked byte vectors; `decode_action_legacy(START)` gives slots 0xFF/0xFF; every
    truncated extension prefix gives `has_ext False` with the 46-byte fields intact; an unknown fmt is skipped;
  - re-pin `test_hostgates_0_reverts_the_stage_to_the_pre_stage_host` (`:2758`) to mask the bits from s111 on,
    `(caps & ~0x3C) == 0`. **(review ctrl F9b)**
- **`studies/test-harness/scenarios/_coop_battle.py`** PROBES: `netsync.diorama.intro`, `netsync.battle.host.wait`,
  `netsync.battle.host.start_hold`, `netsync.battle.end.flee`. A new `_coop_action.py` holds the codec, the unit polls,
  the tape-then-dioboot flow, the invariant snapshot and the tripwire read.

---

## 6. Solo bench plan

### 6.1 Rules for every patch (B4-B5-DESIGN 8.1, unchanged)

- Selftest role (`netsync selftest 1`; saves sandboxed). Plan in ticks; arming is a transition.
- **Calibrate first.** Run the scenario with `COOP_CALIBRATE=1` on the DLL deployed before the patch.
  `Ledger.judge_calibration` must see exactly the predicted reds.
  - Where an earlier DLL cannot express a leg, the leg records the fail-closed probe ("not reached"). Its
    behavioural red then comes from the new DLL's calibration lever, which is the house pattern (design 8.2).
- **Two markers.** Every content bench uses values that exist nowhere else in the process.
- Archive `Memoria.log` and `output_log.txt` to scratch every run. Run from this worktree with the package
  pre-imported and its `__file__` asserted.
- **Regression set after every DLL:**
  - `coop_diorama_return` 22/22, `coop_dialogue_authority` 147/147, `coop_talk_relay` 28/28;
  - the battle set: `coop_battle_host_gates`, `coop_battle_containment`, `coop_stock_menu`,
    `coop_stock_menu_content`, `coop_stock_menu_live`, `coop_battle_end_host`, `coop_battle_end_guest`,
    `coop_battle_result_replay`, `coop_battle_handback`;
  - plus every earlier R3 scenario.
  - The dress patches (s138-s141) may skip the battle set, except `coop_battle_end_guest` (warm return).
- **Expected re-baselines** (each named in its patch's commit):
  - s111: own-battle caps gain 0x08 (+0x04). Scenario masks use `& 2` (`coop_battle_host_gates.py:272-273`). S8-A1's
    `caps == 2` reads the feed caps (`coop_stock_menu_live.py:379`, `StockMenu.cs:1555`), which are unchanged.
  - s113: the loopback root byte becomes 2. In a Wait save, enemies now act while a loopback guest slot waits at the
    root, so any `coop_battle_host_gates` or `coop_battle_handback` leg that assumed frozen gauges is re-baselined
    during calibration.
  - s115: S5-B moves under `guest hold`, and S10-R0's regex is relaxed.
  - s117: S6-C1/C2 move under `guest hold`, and S6-D1 is strengthened.
  - s133: own battles emit more type-6 frames; nothing else changes.

### 6.2 s111 — `coop_battle_intro_mirror.py`

Host legs use selftest own battles on scene 67. Guest legs use `dioboot 67 0` on bench field 30602.

| Check | Step | GREEN | RED on s110 (why) |
|---|---|---|---|
| I-A1 | `bench cfg skipcam 0` + `battle 67 -1 1` | `(host.caps & 0x0C) == 0x0C` **(review ctrl F9a)**, `host.intro.published == 1`, the "SKIPPED" line | the cfg op is withheld by the probe; `HarnessAgent.cs:767` passes args 0-1 only, so the battle is non-random → caps 0x02. Lever: `bench intro 0` → bits clear |
| I-A2 | `battle 67` (rand 0) | bit 3 set, bit 2 clear (published 0) | bit 3 clear |
| I-A3 | timing | A1's ENTER→NORMAL span is >= 1000 ms shorter than A2's | spans equal (rand ignored) |
| I-B1/B2 | `dioboot 67 0 skip`, `dioleave`, `dioboot 67 0 play` | `diorama.intro.wire` 1/0, applied skip/play, `calls > 0`, `normal_ms` recorded | extra args ignored (`HarnessAgent.cs:1194`); key absent. Lever: `bench intro 0` → `calls == 0` (B2's applied stays `play` under the lever on a non-random boot, so `calls` is its only red) |
| I-B3 | — | `T_play - T_skip >= 1500` ms | difference < 1500 |
| I-B4 | `bench cfg skipcam 0` + `dioboot 67 0 play rand` | applied `play`, own `skip` (the wire beats own) | not reached (no rand on a manual boot); lever `bench intro 0` → applied skip |
| I-B5 | — | the BOOT line names `intro=` and `swirl=`; one "reached its command phase" line | line absent |
| I-B6 | the F6 wire bench (its fabricated header stays flags 0x01, `NetSyncBattle.cs:1857`), solo via `dioboot 67 0 wire`; then `dioleave`, `dioboot 67 0 wire play` | boots as before and its BOOT line reads `intro=own` (bit 3 clear → `WireIntro` -1 through the new argument) **(review ctrl F9c)**; `wire play` reads `diorama.intro.wire == 0`, `intro=play(host)` (the parsed header through `BootFromWire`) | `intro=` token absent (a non-regression check); `wire` is ignored on s110 (a manual boot), so the `wire play` leg is "not reached" |

### 6.3 s113 — `coop_battle_wait_parity.py`

Host legs: an own battle on scene 67 with `guestslots 0x0F`, so the host's own window never opens. Wait mode is set
with `bench cfg atb wait`. On s111 the save's own `cfg.atb` applies (stock default 1 = Wait); W-A2 self-checks it.

| Check | Step | GREEN | RED on s111 (why) |
|---|---|---|---|
| W-A1 | a loopback guest slot ready, the digit panel at root | enemy atb sum rises within 2 s; `host.wait.menu == 2`, `deep` false | byte 1 → `RemoteMenuOpen` → `IsNativeEnableAtb` false (`BattleHUD.Public.cs:780`) → flat 3 s. Lever: `bench waitparity 0` → flat |
| W-A2 | `bench ctl deep` | menu 3, deep true, flat >= 3 s | green on both (non-regression; s111's Wait self-check) |
| W-A3 | `bench ctl legacy` | flat | green on both (old-guest compatibility) |
| W-A4 | `bench cfg atb active` | root and deep both run | not reached on s111; green |
| W-A5a | `bench ctl deep` + `bench lapse 3000` | **rises within one pump tick** (`ParseControl(null)` clears the flag, `NetSyncBattle.cs:2236-2239`) **(review ctrl F4)** | green on both |
| W-A5b | `bench ctl deep` + `bench lapse 3000 reserve` | flat about 2000 ms (the re-served frame), then rising | refused (4 args); recorded "not reached" |
| W-B1 | guest: `dioboot 67 0` + `bbench start 0x01` + `bbench ready 0x01` under **`bbench mode refuse`** **(review ctrl F10)**; walk root → Ability → target → Cancel → commit → `bbench ready 0` | `feed.ctl_menu`: 2, 3, 3, 2, 2 (pick in flight), 0 | no `ctl_menu` key; the s111 observable `feed.menu_open` is true at root and deep alike |
| W-B2 | `bbench caps 0` (the digit panel serves) at root | 2 | key absent |

### 6.4 s114 — `coop_battle_start_hold.py`

Host legs are own battles on scene 67, desktop Speed 5, Active unless stated. **The lever is set before `battle`**,
because the hold primes during the intro. `bench starthold cap 3000` shortens the cap legs.

| Check | Step | GREEN | RED on s113 (why) |
|---|---|---|---|
| H-A1 | `bench boot booting` + `battle 67` | from the first `turn.enabled` frame every unit's atb is constant >= 2.5 s; state "holding"; `caps & 0x10`; ARMED line | op withheld; atb rises within 0.5 s. Lever: `bench starthold 0` |
| H-A2 | then `bench boot live` | release "live" within 2 pump ticks; atb rising within 0.5 s; RELEASED line with held_ms | unreached |
| H-A3 | H-A1 under `bench cfg atb wait` | flat (mode independence) | as H-A1 |
| H-A4 | `none`, `declined`, `busy`, `silent` | "not armed" + why; atb rises within 0.5 s | green on both (`auto` = none is every other bench's default) |
| H-A5 | `booting`, then `stale` at +1 s (a LIVE naming the previous nonce) | the stale LIVE releases nothing; release "cap" at 3000 (+0..300) ms | no hold |
| H-A6 | `booting` + cap 3000 | release "cap" at 3000 (+0..300); atb rising after | no hold |
| H-A7 | `booting`, then `bench lapse 3000 reserve` at +1 s | release "link" at 1000 + 2000 (± 300) ms, before the cap **(review ctrl F3)** | no hold |
| H-A8 | `bench boot late 300` (NO frame until 300 ms after the opening, then BOOTING) **(review ctrl F5)** | ARMED late, `late_ms` about 300; then H-A2's release | no hold |
| H-A9 | after a "live" release: pause, wait 1 s, resume | count unchanged, no second ARMED line, **enemy atb rises within 0.5 s of the resume** **(review ctrl F7)** | no hold |
| H-B1 | guest: `dioboot 67 0 play` + `bbench start 0x01` once the scene is BattleMapDebug | `menu.ctl.boot` 1 during the intro, then 2 from PHASE_NORMAL; `diorama.live.ms` ≈ `intro.normal_ms`; nonce == the feed nonce | keys absent; feed frames carry no trailer |
| H-B1b | `dioleave`, fresh `dioboot` + `bbench start` | `boot == 1` until the NEW boot's PHASE_NORMAL (no carried latch) **(review ctrl F2)** | absent |
| H-B2 | selftest proof line "battle control selftest: OK" | its rows include the stale-nonce LIVE (no release), a 2-byte frame (no hold), an unknown fmt (ignored), the byte-1 nonce gate, the BUSY row and a released-then-paused row; mutants fail it | line absent |

### 6.5 s115 — `coop_battle_flee_defeat.py` part a (`COOP_S12_PART=a`)

Setup: field 30602, `dioboot 67 0` (Runaway true, NoGameOver false), a fresh boot plus `endbench clear` per leg.
Invariant: the sandbox fingerprint after teardown, plus `end.flee.gil_now` read WHILE booted.

| Check | Step | GREEN | RED on s114 (why) |
|---|---|---|---|
| P0/P1 | — | `netsync.battle.end.flee` present; `endbench guest hold` accepted | key absent; "needs on\|off\|settle" |
| A1 | `endbench escape` | injected, action "flee", inject 5/3, menu closed | `escape` is HELD (held true, phase 4) |
| A2 | — | within 0.5 s every living, non-CannotEscape player has `mot == 17` (MP_ESCAPE) | mot never 17 |
| A3 | — | each escaping player's `z` falls, then `disappear == 5` within 3 s | no run |
| A4 | — | phase 8, result 4, `btl_flag & 64`, `flee.r9b == 1` + the R9b line, `ability_flag` false, `gil_now` unchanged | held |
| A5 | — | R8 rising, the line "diorama R8: ManageBattleEnd refused (phase 8 seq 1" | no R8 |
| A6 | `game_snap` while z falls | PNG `s12a-runaway.png`, READ: backs turned, mid-run | — |
| A7 | `other 4`, `ui 1`, `state 7 loading` | result-hide trigger, warm return, field result 4, `wipe_lifted`; invariants byte-identical | wipe_lifted false (stamp 4 is green on s114 too: a regression check) |
| B | `manifest 2` + `escape`, wait R8, **`other 4`**, `ui 1` + `state 2` **(review end F1)** | replay verdict 0, opened (+321 gil on the PNG); `state 3..7` closes; field result 4 from the STAMP | verdict 2 ArmNotInjected |
| B-AE | as B with `afterevent` set | still opens (`ArmVerdict` ignores b0 for ESCAPE) **(review end F3)** | ArmAfterEvent |
| C | `other 4` | action "close", inject 8/0, mot never 17, r9b 0, R8 | held |
| NL | `escape`, wait for injection, `defeat` (the host's kind becomes Defeat), `ui 2` | stamp -1, `end_leave.reverted == 4`, field result 0 **(review end F4)** | escape held, nothing injected, `reverted` absent |
| L1 | `guest hold` + `escape` | HELD (s114's behaviour inside the s115 DLL) | — |
| L2 | `guest nor9b` + `escape` (precondition: `flee.penalty > 0`) | `ability_flag` true, `bypassed` 1, `gil_now == boot gil - penalty` WHILE booted; after `ui 1`/`state 7` the invariant gil is equal again | — |
| S | `endbench selftest` | "..., replay N, flee M)" with W2Force pins, NoLeakResult pins (including `(-1, true, 4, 0, KEscape) == -1`) and the ESCAPE+AfterEvent arm row | detail ends at "replay N" |

Regression in the same commit: `coop_battle_result_replay` S10-R0 with the relaxed regex, and S5-B under
`guest hold`.

### 6.6 s117 — `coop_battle_flee_defeat.py` part b

| Check | Step | GREEN | RED on s115 (why) |
|---|---|---|---|
| P0 | — | `endbench kill` accepted; `end.follow_msg` present | unknown op; key absent |
| A1 | `kill 15`, **poll until every seated unit reads `mot == 4`** **(review end F6)**, then `defeat` | action "annihilate", inject 5/1, `follow_msg` "annihilated" | held |
| A2 | — | MENU_OFF < 1.5 s with no watchdog; then phase 7, result 3, `btl_flag & 32` (song 6); R8 "(phase 7 seq 1" | held |
| A3 | `ui 2` | trigger game-over, back on 30602, no Title frame, stamp -1, field result 0, `reverted == 3`; invariants include members' HP | held; reverted 0 |
| B | `defeat` with no kill | W2 at 8 s, blocker "player(s) not down", forced phase 7 / result 3 (never 6/1), R8 | held, no W2 |
| C | a NOGO scene (12, 336, 339): `kill 15` + `defeat` | annihilate; phase 7; `btl_flag & 32 == 0` throughout (no song, `battle.cs:280`); then `phase-defeat`, `manifest 1`, `ui 1`, `state 0..7` → replay opens and closes; field result 3 | held; ArmNotInjected |
| D | `phase-defeat` with the party alive; then `kill 15` + `phase-defeat` | "defeat" (7/0, no message, never MENU_OFF); then "annihilate" | unknown op |
| E | `other 3` (scene 67, then a NOGO scene) | "close", inject 8/0, local 3; field 0 with `reverted 3`, or field 3 with `reverted -1` | held |
| F (S6-D1) | `other 6`, **poll injected + close + local 6**, `ui 2` | stamp -1, `reverted == 6`, field 0 **(review end F5)** | s115 holds defeat kinds → never injected; the strengthened check reads red |
| S | selftest | "..., flee M, defeat K)", mutants fail | detail ends at flee |

### 6.7 s133 — `coop_action_host.py`

Flow: `actbench tape rec`, then `battle 67`. Commands via `battlecmd`: Zidane Attack ×2, Vivi Fire (single) and Fira
(all), Garnet Potion on self, plus a Defend. Let the enemies act; `fight` to finish; `tape stop`.

**GREEN:**
- `act.host.on` and `peer.caps & 0x20`;
- `starts == loop.starts` and `ends == loop.ends`;
- `orphans == 0`, `caster_mismatch == 0`, `noid_impacts == 0`, `no_end == 0`;
- at least one enemy START of kind 2 with num == sub;
- both Zidane Attack STARTs are kind 3 with the same num;
- Fira's `tar` spans 2+ enemy bits;
- the Potion START is kind 3;
- offline over the tape: `decode_action_legacy(START)` gives 0xFF/0xFF with flags bit 2, and every impact is 52 bytes
  with its first 46 bytes unchanged;
- no "failed" line, and the battle ends normally.

**RED:**
- On s117: the `act` probe fails closed.
- Lever `actbench hoststarts off`: starts 0, `ext_impacts` 0, caps bit 5 clear, every tape impact 46 bytes.

### 6.8 s134 — `coop_action_replay.py`

Flow: s133's battle with `tape rec`, then back on 30602, `dioboot 67 <pat>`, wait for phase 4 and units loaded.
Snapshot the invariants: gil, a marker item's count, exp and levels, kill counts, `ach_held`, `r9_refused`, every unit's
`hp_raw` and mp. **Precondition:** `act.guest.calc_while_booted == 0` in this no-replay diorama.

**Legs:**
- **Leg A, a fabricated player replay.** START: actor 0, Attack, tar 0x10, kind 3, num = the taped Zidane num, speed 5.
  - Within 15 frames: `started == 1` and `units[0].acting`.
  - `anim` leaves idle.
  - `away` peaks above 400, then falls below 10.
  - `ended == 1`, `hits >= 1`.
  - Invariants unchanged, `cmd_busy == 0`, `r9_refused == 0`, **`calc_while_booted == 0`**.
- **Leg A-H, a heal leg.** A Potion kind-3 START on a damaged ally, with no impact: that ally's `hp_raw` is unchanged.
  **(review replay F1)**
- **Leg B, an enemy replay.** EnemyAtk, kind 2: the enemy's anim changes and returns to idle without a flinch.
- **Leg C, the real host frames.** `tape play`:
  - `started == tape.starts - declined`;
  - every decline is "noop" or "stale";
  - running reaches 0 within the tape length + 5 s;
  - `faulted == 0`, `aborted == 0`;
  - a mid-tape `game_snap`, READ: a visible spell effect.
- **Leg D, leave.** START, then `dioleave`: `aborted` 1 "leave", and a clean next boot.
- **Leg D2, teardown.** START, then a forced teardown with no Leave (`dioboot` → `warp` away): `ActDiscardAll` logged,
  nothing applied, `ach_held` unchanged, `r9_refused` 0. **(review replay F2)**
- **Leg E, end.** START, then `endbench victory`: the phase stays MENU_OFF while acting, then VICTORY.
  - Repeat with `endbench escape`: the run-away waits, then runs.
  - A long summon START, fabricated (kind 3, a stock full-summon effect id read from the engine's SpecialEffect
    list), forces W3 at 4 s.
- **Leg F, pairing.** START + impact (marker 4321): `swing_skipped` + 1, and the replay clip shows, not MP_ATTACK.
- **Leg G, an old-host impact.** 46 bytes give the s110 MP_ATTACK swing.
- **Leg H.** `rework off` → declined with the SFXRework reason.
- **Leg I.** A live edit of `ActionReplay=0` → declined with the knob reason, and the session stays up.
- **Leg J, stale.** A START and its END in one feed → declined "stale". **(review replay F6)**
- **Leg K, a death attack.** A lethal impact on an AttackOnDeath enemy, then an EnemyDying START for it within 1 s:
  the replay runs; `die_seq` stays 0 until it ends. **(review replay F3)**
- **Leg L, Change.** A Change START for a player: after its hit, `units[i].away < 10` from the NEW base_pos, and the
  row has flipped. **(review replay F4)**
- **Leg M, the player stance.** A player START: `anim` passes MP_IDLE_CMD → MP_SET with no idle-loop wait, and the hit
  comes within the same frame budget as the taped host's. **(review replay F7)**

**RED:**
- On s133: the probe fails closed.
- Lever `actbench replay off`: legs A/B/C red on started/acting/away/ended; F shows the swing.
- Lever `actbench shortcircuit off` on one Leg-A replay: `calc_while_booted >= 1`, the tripwire's own red.

### 6.9 s135 — `coop_action_hold.py`

- **Leg 1.** START + a non-lethal impact (4321): `hp_raw` follows within 1 frame. There is no 4321 figure until
  `first_hit_ms`, then one entry via "hit" within ±2 frames. The flinch comes only after the hit.
- **Leg 2, lethal.** `alive` stays true and `life_mask` has the bit until the hit; after it, dead, `die_seq > 0`,
  mask 0.
  - `actbench unit 4 dead` (post-horizon seq) while held must NOT kill.
  - With **`actbench lifeskip off`** it kills at the op, before `first_hit_ms`. That is the life-skip's own red.
    **(review replay F5)**
- **Leg 3, end release.** A **Defend** START (short; it hits only its caster) plus an impact for enemy 5: released
  via "end" before 2.5 s. **(review replay F7)**
- **Leg 4, timeout.** A long summon START whose impact names an enemy its sequence hits only after 2.5 s: released via
  "timeout" at 2500 ± 150 ms. The `feedat` variant applies an impact with no START at once.
- **Leg 5, late.** START, wait `hits >= 1`, then the impact: released via "late" at once.
- **Leg 6, abort.** START + impact, then `dioleave`: released via "abort", mask 0.
- **Leg 7, host END.** An impact on a target the replay never hits, plus END at +100 ms: released via "hostdone" at
  about 1600 ms.
- **Leg 8, superseded.** A held revive, then a newer stat-tick frame for that slot: at the hit, the figure shows, the
  life change is skipped, and `superseded` + 1. **(review replay F9)**

**RED:** on s134 the `guest.hold` probe is absent. With `actbench hold off`, leg 1 pops at arrival and leg 2 dies at
arrival.

### 6.10 s136 — `coop_action_fallback.py`

With `actbench replay off`, feed impacts:
- Potion → `mot[MP_ITEM1]`; BlackMagic → MP_MAGIC; Attack → MP_ATTACK.
- Enemy sub k → `fallback.last.clip` equals the first caster PlayAnimation of sequence k. The oracle is read from a
  replay of the taped enemy START.
- A burst of 3 legacy impacts within 100 ms: `clips + 1`, `deduped + 2`. With one id: `+ 1`.
- A lethal caster: no clip.

**RED:** on s135, and with `actbench fallback off`: Item and Magic play MP_ATTACK, the enemy gets no clip, and the
counters are absent.

### 6.11 s137 — `coop_action_trance.py`

Arm the stage-8 feed with **`bbench start 0x01` + `bbench caps 0x22`**, so the live peer view advertises bit 5.
**(review replay F6)**
- `actbench unit 0 trance1`: the normal model holds for up to 400 ms (`trance.deferred`).
- A SysTrans START inside the grace: the model swaps exactly at `first_hit` (`swaps_by_hit` + 1).
- Without a START: the swap comes by the grace at 400 ± 50 ms.

**RED:** on s136, and with `actbench trancegrace off`: the swap is immediate. Calibrate also with caps 0x02, which
must equal the lever red.

### 6.12 s138-s141 — `coop_self_dress.py`

**Leg I (s138), fields 250 then 30801:**
- I1-I4: `player.model == 98`, `geo == "GEO_MAIN_F0_ZDN"`, `anim_geo == geo` at rest, `eye == -372`.
- I5: walking → anim ∈ {25, 38}; at rest → 200.
- I6: NPC models are published and none is 98.
- I7: the ghost's model and clip mirror the player's.
- I8: `party` has 4 entries.
- RED on s137: key absent.

**Leg G (s139), field 250.** Read `dress.party` first.
- G1: `selfdress ghost 2` → `ghost.model == Rigs[party[1]]`, `rig == party[1]`.
- G2: `ghost 6` + `empty 1` → slot 2's member.
- G3: `ghost 2` + `empty 1` → model 220, `GEO_NPC_F0_MOG`, `ANH_NPC_F0_MOG_*` clips.
- G4: `dress.codec == "ok"`, plus the codec line.
- G5 (control): `clear` → back to `player.model`.
- G6: `rig_idle_frames` published for all 9 rows. This is the list s140's leg T judges.
- RED on s138: the verb is refused before the step ("not reached") and the codec is absent. G5 is green.

**Legs S/W/X/N/T (s140):**
- **S1:** `selfdress self freya` + `warp 250` → model 192, `GEO_MAIN_F0_FRJ`, eye -376, `dress.self.uid == player.uid`,
  `confirmed >= 1`, one dress line.
- **S2:** at rest 2556; walk 2553; run 2558; `anim_geo == geo` throughout.
- **S3:** `self auto 2` + `empty 1` + re-warp → model 220, eye -200 (selftest role at call time).
- **S4:** `self off` → model 98.
- **S5:** the ghost wears 192.
- **W1, field 30602:** dress, `dioboot 67` → `dioleave` → `last_return "warm"`, model 192, `dress.self.uid` unchanged,
  **`dress.self.net_byte` set**, then **a `netsync talk` to a gesturing NPC** after the return → `anim_geo` is still
  FRJ. **(review dress F6)**
- **W2:** the cold control → model 192 through SetModel, `confirmed + 1`.
- **X1/X2, the bench field:** the caller's conductor plays RunAnimationEx(250, 186) → `anim == 2556`, never a ZDN
  folder; control returns within the hold + 5 s.
- **N1:** the bench field's `twin` (InitObject ordered BEFORE the player) → `objects[twin].model == 98` and
  `skip_npc >= 1`. The gate runs first, so the counter rises only through it. **(review dress F5)**
- **N2:** `selfdress gate 0` → `skip_npc` stays 0, and the twin wears 192 (it comes first).
- **T1, the timeline:** a kit conductor on 250 runs RunAnimation(a Zidane gesture of 60+ frames) then
  `while obj(250).f[7] < 58 Wait(1)`. It must finish on every rig, the moogle included, with `timeline_kept + 1`.
  **(review dress F1)**
- **T2:** `effMapNo` checks see the raw id. Proven offline by a SelfTest row that `MapAnim` is applied after the
  special cases (the 2934 trigger itself is unbenchable solo).
- **RED on s139:** the `self` op is refused ("not reached"); where reached, model 98. S4 and N1 are **"not reached"**
  on s139, not green. **(review dress F6)**

**Leg F (s141):**
- F1: freya → steps {[2553,4], [2553,16], [2558,0], [2558,9]}.
- F2: moogle → steps [], `steps_dropped == 12`.
- F3 (control): off → {[25,4], [25,13], [38,0], [38,8]}.
- F4: `light_row == 98`. **Before relying on the `_Color` half, read field 250's 98 row and its default row, and keep
  the color check only if they differ.** **(review dress F6)**
- F5: the bench caller's HideObject(250,1) → `mesh_drops >= 1`, `player.meshflags == 0`.
- RED on s140: F1/F2/F4/F5. F3 is green.

**Bench field.** `selfdress.field.toml`, a 30000-band scratch id. Read the live DictionaryPatch first, pass `--id`,
relaunch once to register, and never pin the id in `.ff9deploy.toml`. It holds:
- a kit Zidane player;
- a `twin` Zidane NPC with no CC, whose InitObject comes first;
- a `caller` with the gesture and frame-wait conductors.

### 6.13 s116 and s112

- **s116, part c.**
  - G: `fleegil 77` + `escape` → `peer.end.flee_gil 77`, and after R9b `msg_gil 77`, gil unchanged. `none` → -1.
  - H: a real own battle with Zidane's Flee ability → `host.end.flee_gil` equals the gil lost.
  - K: codec SelfTest; a short fmt 2 record is skipped and the block kept.
  - RED on s141: unknown op, keys absent.
- **s112, leg S.**
  - `bench swirl local 115` + `DioramaSwirlFrames 0` + `dioboot` → SwirlScene dwell < 0.5 s.
  - `bench swirl ini` + `-1` → about 3.8 s.
  - The real proof is the laptop box.

---

## 7. Two-machine boxes for the next sittings

**Setup, every sitting:**
- The same DLL on both machines; update BOTH (wire v14).
- Host = desktop (`[Battle] Speed=5`, `[Graphics] BattleSwirlFrames=0`). Guest = laptop with FollowHost=1.
- Record the laptop's `[Battle] Speed`, `SFXRework`, `[Graphics] BattleSwirlFrames` and its save's ATB mode on the box
  sheet.
- Diff the meeting fields: 250 (warm) and Dali 350 (cold).
- Grab both `Memoria.log` and `output_log.txt` before any relaunch.
- `game_snap` both screens on visual boxes. Ask for side-by-side video early on anything visual.

### Sitting A — after s111-s117 (start sync, Wait parity, flee and defeat, the carried-over retests)

| Box | What | Pass |
|---|---|---|
| A1 | Intro mirror: a random encounter on 250 with the desktop skipping its intro | the laptop log reads `intro=skip(host)`; no plunge on the laptop; "reached its command phase N ms" below sitting 2's ~6 s. Then the desktop's skip off → both play the plunge |
| A2 | Start hold, warm (250) | host: "ARMED for battle nonce N" then "RELEASED after X ms: live", X < 8000; nothing moves on the desktop before it; `game_snap` on both within ~0.5 s of the release shows the same gauge fills |
| A3 | Cold (Dali 350) and back to back | each battle arms with its own nonce; the second is not released by the first's LIVE |
| A4 | The guest declines (~ Leave during its swirl, or FollowHost=0) | "declined" or "not armed" within ~RTT; the fight proceeds |
| A5 | The guest is in its own main menu at the host's encounter | host: "not armed -- the guest is busy" (no 8 s freeze); the laptop boots when it closes the menu and catches up |
| A6 | Cut the laptop's network during its swirl | the host releases about **2 s** after the cut ("link"); the laptop's blip-hold rides the cut |
| A7 | World-map battle | "not armed ... (none)" |
| A8 | Wait parity, host save in Wait | the guest's root → the host's gauges keep moving; Ability/Item/target → freeze; back to root → resume; commit → resume. Active: nothing freezes. Host harness shows menu 2 vs 3 |
| A9 | **Box 14 redone** (stall hand-back), host in Wait, the laptop's window open | **Leg 1, guest in a submenu:** cut the network 3 s → the freeze lifts about 2 s after the cut and there is NO capture (the takeover needs about 4.5 s: 2 s of re-served frames + 2.5 s MenuStaleMs). Cut 6 s → the host's window takes the slot about 4.5 s after the cut ("hand-back: the host's local window holds guest slot ..."); on reconnect, with the host's window at the root, the slot hands back. **Leg 2, guest at the root:** no freeze at all (parity); a 6 s cut → capture at about 4.5 s and hand-back on return |
| A10 | (optional) host Speed 2, turn-based | the guest's root window still freezes (stock any-open); the start hold still holds |
| A11 | Bumper flee on 250 | the guest party turns, runs and fades within about 0.5 s of the host's; it returns WITH the host (warm); one R9b line, R8 "(phase 8 seq 1", `btl_result -> 4`; the guest's gil is unchanged |
| A12 | Zidane's Flee ability | the host shows "Dropped N Gil" and loses N; the guest's gil is unchanged (with s116: the same N shown) |
| A13 | Flee-Gil SA on the host | the host's result screen shows the gil; the guest replays it; return with result 4 |
| A14 | The guest pauses as the host flees | on resume it presents the CLOSE fade (or nothing, if the host has already hidden) and leaves with the host; no black screen |
| A15 | NoGameOver defeat (owner's pick; NOGO scenes 12, 336, 339) | "Annihilated" on both, NO defeat song on either (stock), the guest's result replay follows, return with result 3 |
| A16 | Game-Over defeat (throwaway save, 250) | "Annihilated" + the start of song 6 on both; the host goes to Game Over then the title; the guest leaves to ITS OWN field, the song stops, the field reads result 0 ("reverted 3 -> 0"); the session survives the host's reload |
| A17 | Flee, then the next fight | the next fight boots and presents normally |
| A18 | **Carried over: all-target and self-target abilities** (Vivi Fira on all enemies, Garnet Cura on the party, Defend, a Potion on self, an Instant self-target) | every target's number on the guest; HP bars follow; the guest's stock menu and second-slot window behave; record what animates (flinches and the player swing only, before the replay) |
| A19 | **Carried over: the F3.3 shop box** (`F3.2-DESIGN.md:927` box 9) | while the host shops, the guest's farewell line waits, locked; it closes on the host's farewell confirm |
| A20 | (optional) mixed DLLs | new host + s110 laptop: no hold, the root freezes Wait, defeat/flee held as today. s110 host + new laptop: today's behaviour, no errors |

### Sitting B — after s133-s141 (action replay and the guest's model)

**Replay** (side-by-side video):

| Box | What | Pass |
|---|---|---|
| B1 | Zidane attacks | on the laptop he runs up, swings and returns; the number pops on the contact frame, not before |
| B2 | An enemy attacks the guest's character | the enemy's own animation and sound; flinch and number at the hit |
| B3 | **Retest: all-target and self-target, with animations** (Fira all, Cura party, Potion self, Defend) | the cast animation and effect play; every target's number lands at the effect's figure point; HP bars follow the host |
| B4 | The guest commands its own character (Attack, then an Item) | it sees its own character perform the host-executed action; the item list drops by one; the guest's own bag and save are unchanged; no window opens or closes because of a replay |
| B5 | A summon, short and full | effect and song play on the laptop; no camera swings (host Speed 5); numbers land at the eidolon's hit; total duration within about 0.5 s of the host's |
| B6 | Double-cast, and a counter | two casts with their own numbers; the counter plays right after its trigger |
| B7 | The killing blow | the death fade starts at the visible hit. Fade timing after the hit depends on the **laptop's** Speed (`btl_mot.cs:318`, `:333`): with Speed < 3 the fade does not wait for later actions; record it **(review replay F10)** |
| B8 | Speed 5 simultaneous fighting | concurrent replays, no camera jumps, no frozen effects; `faulted`/`aborted` 0 in both logs |
| B9 | The host wins while a replay is mid-air | victory starts right after that replay (W3 at most 4 s); result replay and return as in sitting 2 |
| B10 | Reflect | the hit on the reflector; bounced numbers at the replay's end (a known v1 gap); record it |
| B11 | A 3 s link blip mid-fight | replays finish; late numbers pop at once; no stuck animation |
| B12 | Memory after 10 fights | the laptop's process memory vs a pre-R3 run (the SaXAudio leak, about 0.75 MB per SE play) |
| B13 | Mixed DLLs | new host + s117 laptop: as sitting A. s117 host + new laptop: fallback A (enemy clips, MP_ITEM1, MP_MAGIC, once per action); "host predates action replay" once |
| B14 | The laptop on the legacy engine (`SFXRework=0`, Speed < 3) | every START declines with the SFXRework reason; fallback A plays; restore the setting after |
| B15 | Trance | the burst plays and the model swaps at its flash |
| B16 | Flee during fighting | no double run-away |
| B17 | A death attack (an AttackOnDeath enemy) | its death move plays on the laptop before it fades |
| B18 | A Change command | the character steps to the other row and stays there |

**Guest model:**

| Box | What | Pass |
|---|---|---|
| B19 | After s139 only, the laptop still on s117 (old-guest box) | with 2+ members the host sees the slot-1 member; with 1 member a MOOGLE that walks, runs and turns; the laptop's own screen is unchanged |
| B20 | Both on s141, field 250 | the laptop's body is the slot-1 character on both screens; one dress line per field load |
| B21 | 1-member party | the moogle on both screens; the speech bubble sits at moogle head height |
| B22 | A host party change mid-field | the host's ghost re-dresses when the menu closes; the laptop changes at its next door; no frozen camera, no NRE in `output_log.txt` |
| B23 | A talk relay whose scene animates the player (Dali/Lindblum) | the dressed body idles through the gestures; the scene ends on both machines |
| B24 | Warm and cold battle returns | still dressed after both |
| B25 | World map, the opening FMV, endings, the title | never dressed; dressed again back on a field |
| B26 | Session end | the exit ramp reloads the laptop's own save undressed |
| B27 | `SelfDress=0` (live) | at the next load the laptop stays Zidane, and the host's ghost ALSO shows Zidane (the guard) |
| B28 | A Steiner- or Dagger-led section, or a `ZDD` (532) field | both screens show the real body; nothing is dressed |
| B29 | After s141 | the tree shadow on 250 darkens the dressed body; footsteps audible for humanoids, silent for the moogle; a dagger-draw cutscene leaves the dressed body intact |
| B30 | Every box | the host's own Zidane is never dressed |

**Optional:** s116 (A12's figure on the laptop); s112 (the laptop's swirl as short as the desktop's, and A2's X
shorter).

---

## 8. Risks

1. **Re-simulation through a replay** (the never-re-simulate law).
   - The short-circuit is the first statement of `ExecVfxCommand` and returns true for any registered replay, even on
     an exception. Replays register before Execute. All five `ExecVfxCommand` callers were checked.
   - The CalcMain tripwire turns a fall-through into a counted, calibrated red.
   - A future Memoria merge that adds a CalcMain caller needs a re-census.
2. **A hold that never releases would freeze the host.**
   - The getter enforces the cap itself.
   - Release fires on LIVE, decline, busy, link (null frame), an old frame, or the cap. Every battle edge and `Reset`
     clear the state, and a release is final.
   - `StartHoldMs=0` is a live kill switch.
3. **The sequencer stalls.** One throwing action aborts every action for the frame (`UnifiedBattleSequencer.cs:29-51`).
   - A guest-only state difference makes a replay throw more likely: an absent magic caster in LoadSFX `:334`.
   - Replays run through a guarded loop. A hanging SFX is bounded by host END + 6 s and the 90 s cap.
4. **Hot-path cost.** The btl_util hooks, `Loop`, `IsNativeEnableAtb`, `SetModel` and the anim setters each sit behind
   one static read that is false on vanilla, solo and the host. `ActLive` must be recomputed at every add and remove,
   and cleared at teardown even on exceptions.
5. **Frame-number waits in dressed cutscenes.** Mitigated by keeping the source timeline (leg T1). A script that
   asks for a clip's frame count by id, through DoCalcOperationExt `:25`, gets the raw clip's count, because the raw
   clip stays attached.
6. **Timing on the real link.**
   - A stale control lane decays about 4.5 s after a cut, not 2.5 s.
   - The start hold releases on the null frame, about 2 s after a cut. The hand-back capture still takes about 4.5 s.
   - Held numbers can release on timeout before a slow laptop's visible hit [I: steady-state gap is a few frames].
7. **Bench churn.**
   - The loopback root byte changes (s113).
   - S5-B and S6-C move under `guest hold` (s115/s117).
   - The S10-R0 regex changes (s115).
   - The caps values change (s111).
   - Each change must land in the same commit as its DLL.
8. **Replay visual gaps in v1:**
   - reflect bounces decided from the guest's statuses (`btl_cmd.cs:871-931`);
   - the coverer does not move;
   - a dodge shows only "Miss";
   - statuses not mirrored mid-battle (Vanish, Float);
   - monster-transform commands declined;
   - scripted boss sequences replayed without their AI follow-ups.
9. **Install and Scripts-DLL parity.** Kinds 1 and 2, and custom summons, resolve from the GUEST's data. A sequence
   present only on the host declines or plays a different stock visual.
10. **The SaXAudio leak** now grows the laptop's memory with replay sounds (about 0.75 MB per SE play).
11. **Dress edge cases:**
    - 185 stock fields have a second player-defining entry; where both spawn, a dressed non-player can remain
      (counted, cosmetic, never undone mid-field: the HonoBehavior teardown law);
    - hand-bone props land on the same-index bone;
    - two copies of a character are possible in party cutscenes;
    - collision and talk radius stay Zidane's.
12. **The host's ghost changes for non-Zidane leaders.** The dress guard (s139) now shows a Steiner-led guest as
    Steiner, where s110's slot dress showed the slot member. Intended: both screens agree.
13. **Patch numbering and the shared clone.**
    - Builds auto-deploy.
    - The clone carries the whole uncommitted netsync stack.
    - Numbers are taken at emit, and concurrent sessions may claim numbers.
14. **The no-leak rule** changes what a stale-lane return after a locally presented defeat reads (0, not 3). This
    matches s110 and decision 15.

---

## 9. Owner questions — ANSWERED 2026-10-13: every default taken

The owner answered all nine: two sittings (A after s117, B after s141); clamp the laptop's diorama swirl to the
desktop's (build s112; the owner will read the laptop's `BattleSwirlFrames` for the record); a killing blow or revive
holds the HP bar with the pose until the replay's hit (cap 2.5 s); the replay camera follows the host's Speed; all
replay sounds and summon songs play; the v1 replay gaps are accepted; build s116 (the gil relay); the host's `GhostAs`
also drives the guest's own look; dress only the plain Zidane body (model 98) in v1. The questions as asked:


1. **Sitting cadence.** Two sittings, A after s117 and B after s141, or one sitting at the end?
   *Default: two.* Sitting A lands the start sync, Wait parity, flee and defeat, and the carried-over retests sooner.
   It also measures the laptop's boot time and swirl, which decides s112.
2. **The laptop's `[Graphics] BattleSwirlFrames`.** Please read it from the laptop's Memoria.ini (or launcher). If it
   is above 0, or absent (the code default is 115, about 3.8 s), should the diorama's swirl be clamped to the
   desktop's?
   *Default: yes, build s112 and clamp to 0.*
3. **Killing blows and revives.** Hold that unit's HP bar together with the death or revive pose until the replay's
   hit, capped at 2.5 s? This is an exception to "HP bars follow the host": an HP-0 bar without the death pose is not
   a stock state, and writing HP 0 early triggers the stock next-frame kill.
   *Default: yes.*
4. **Replay camera.** Follow the host's Speed? At Speed 5 that means no action or summon cameras on the laptop.
   *Default: yes.*
5. **Replay sounds.** Play every action sound and summon song on the laptop, accepting the known SaXAudio leak on long
   sessions?
   *Default: yes.* A mute knob can come later.
6. **Accept the v1 replay gaps** for this round: reflect bounce visuals, dodge sidestep, the Cover move, and scripted
   boss sequences replayed without their AI follow-ups?
   *Default: accept, and revisit after sitting B.*
7. **Build s116**, the host's "Dropped N Gil" on the laptop through an additive trailer record?
   *Default: yes, as the last core patch.*
8. **One knob for both screens.** Should the guest's own look follow the host's `GhostAs`, so that an empty `GhostAs`
   keeps everyone Zidane?
   *Default: yes.*
9. **Dress scope for v1.** Dress only the plain Zidane body (model 98)?
   - Zidane carrying Dagger (532) would lose Dagger from the scene if dressed.
   - In non-Zidane-led sections the guest is that leader.
   - Blank, Cinna, Marcus and Beatrix in the slot stay Zidane.
   *Default: yes for v1.* Widening later is a gate change.

---

## Appendix A. Review findings: folded and rejected

Every finding was re-checked in the code (the citations are in the finding's fold site above).

### A.1 Folded into the design

**Battle-start sync and Wait parity:**
- **ctrl F1 [V]** The selftest LIVE latch never saw `PeerBattleLive`. Fix: `LiveTick` runs after `StockMenuTick`
  (3.1.2).
- **ctrl F2** `_liveLatched`/`_normalMs` had no per-boot reset. Fix: reset in Boot's block, its catch and
  `ForceDisarm`, plus bench H-B1b (3.1.2, 6.4).
- **ctrl F3 [V]** Stacked control staleness, about 4.5 s. Fixes: the hold releases on the null frame ("link", about
  2 s); the box timings are corrected (A6, A9); new `bench lapse <ms> reserve` (3.1.4, 6.3, 6.4, 7).
- **ctrl F4 [V]** W-A5 was mis-specified. Fix: re-specified as W-A5a (immediate) and W-A5b (reserve) (6.3).
- **ctrl F5 [V]** `late` sent 2-byte frames. Fix: `late` now sends no frame until its time (6.4).
- **ctrl F6 [V]** BOOTING was reported for durable menus, and a silent guest was primed. Fixes: boot value 4 BUSY;
  "no word" priming dropped (3.1.4).
- **ctrl F7** The hold could re-prime after a pause. Fix: decide once, every release final, and H-A9 asserts the
  resume (3.1.4, 6.4).
- **ctrl F8 [V]** `_guestR3Seen` survived a DLL swap. Fix: moot, since priming no longer reads it (it is observability
  only) (3.1.4).
- **ctrl F9 [V]** Three items: the operator precedence in I-A1; the fake caps test; `WireBenchBoot`'s
  `BootFromWire`. Fixes: all three corrected (5.2, 6.2, 3.1.2).
- **ctrl F10** W-B1's commit read 0 under accept. Fix: that step runs under `bbench mode refuse` (6.3).

**Action replay:**
- **replay F1 [V]** The invariants were blind under isDebug. Fixes: the CalcMain-while-booted tripwire with its
  `shortcircuit off` red; a heal leg (3.3.3, 6.8).
- **replay F2 [V]** Teardown released held state after `_booted = false`. Fix: `ForceDisarm` discards only, in its own
  try; `LeaveFrom` steps are each guarded (3.3.3).
- **replay F3 [V]** Death-time enemy actions never replayed. Fixes: the stock dead-caster exemption; a 1500 ms
  death-attack grace in the QUEUED hook; Leg K (3.3.3, 6.8).
- **replay F4 [V]** Change displaced the actor. Fix: `SwitchPlayerRow` at the Change replay's hit, kept out of the
  restore; Leg L (3.3.3, 6.8).
- **replay F5 [V]** The life-skip was masked by the horizon gate. Fixes: the `unit` op uses a post-horizon seq; the
  `lifeskip off` lever (5.1, 6.9).
- **replay F6 [V]** The AR5 grace needed a peer view, and the stale rule was seq-based. Fixes: the feed with caps 0x22;
  the structural stale rule; Leg J (3.3.3, 6.8, 6.11).
- **replay F7 [V]** Player replays started from idle. Fixes: the MP_IDLE_CMD stance at launch; Leg 3 on Defend; Leg 4
  made deterministic (3.3.3, 6.9).
- **replay F8 [V]** A spurious END for scripted sequences. Fix: a separate scripted id map that END never consults
  (3.3.2).
- **replay F9 [V]** Held life changes could land out of order. Fixes: horizon-stamped releases; stat ticks queued
  behind; Leg 8 (3.3.4, 6.9).
- **replay F10 [V]** Three wrong citations. Fixes: corrected here (Appendix B); the Box B7 expectation is tied to the
  laptop's Speed (7).

**Flee and defeat:**
- **end F1 [V]** The no-leak rule reverted every local result. Fixes: scoped to DEFEAT/GAMEOVER or a host Defeat; bench
  B fabricates `other 4`; pins added (3.2.2, 6.5).
- **end F2 [V]** The S10-R0 regex. Fix: relaxed in the s115 commit (3.2.2).
- **end F3 [V]** Escape with gil in an AfterEvent scene. Fix: `ArmVerdict` ignores b0 for ESCAPE; leg B-AE (3.2.2, 6.5).
- **end F4** ESCAPE leaked into a Game-Over return. Fix: the no-leak rule moves into s115 (leg NL) (3.2.2, 6.5).
- **end F5 [V]** S6-D1 was vacuous. Fix: it is strengthened from s117 (3.2.3, 6.6).
- **end F6** The A2 threshold was uncalibrated. Fix: poll for MP_DISABLE before `defeat` (6.6).

**Guest model:**
- **dress F1 [V]** Frame-threshold loops wedge. Fixes: keep the source timeline (frameN from the raw clip, which stays
  attached); leg T1; `rig_idle_frames` published (3.4.4, 6.12).
- **dress F2 [V]** The 2934 trigger was lost. Fixes: the raw id is kept for every `effMapNo` check; the exclusions use
  `EffectiveFieldId` (3.4.4).
- **dress F3 [V]** The screens split for a non-Zidane body. Fix: the host dresses only a plain-Zidane or
  already-dressed wire body (3.4.3).
- **dress F4** Dressing as Zidane, and the Dagger loss on 532. Fixes: charId 0 disarms; 98 only (3.4.4, Q9).
- **dress F5** The one-body check preceded the gate. Fixes: the gate runs first; the twin is ordered first (3.4.4, 6.12).
- **dress F6 [V]** Calibration claims and the harness gate. Fixes: S4/N1 "not reached"; W1 asserts `net_byte` and a
  post-return setter; F4's color check is conditional; `selfdress` joins the authority list (5.2, 6.12).
- **dress F7 [V]** The moogle fallback was a config-time static. Fix: derived from the live role at call time (3.4.3).
- **dress F8 [V]** The `MainRigCount` guard blocked the named moogle. Fix: it guards only the party path; a named
  moogle sends 0xFF (3.4.3).

**Found during the merge (no reviewer raised these):**
- Header bit 3 was claimed by both the start-sync and replay lanes. `CapActionStarts` moves to bit 5 (section 2).
- The end lane said the catch literal "does not change". Wrong: s104-s109 added their `end` keys, so the new keys
  get sentinels (5).
- Both the end and replay lanes added `battle.units[].disappear`. It ships once, in s115 (5.1).

### A.2 Rejected (one line each)

- **ctrl F3, the seq half** (a seq byte in the control trailer). The guest's write thread re-sends the same bytes
  through its scene-load stall (`NetSyncSocket.cs:671-685`), so a seq would make the lane read dead exactly when the
  hold is needed. The null-frame release is used instead.
- **replay F10(c), the code half** (gate DieSequence's Speed checks on the host's Speed). It adds stock-code surface
  for a fade-timing nuance. The laptop's Speed is recorded and Box B7's expectation is adjusted instead.
- **end F1, the optional half** (stamp `StampFor(local)` when the host's result is INITIAL). Not needed: the scoped
  no-leak rule keeps s110's behaviour for those returns, and decision 15 is met.
- **dress F2, the optional half** (exclude field 2934 outright). Keeping the raw id makes the trigger fire on the
  dressed body; an exclusion would only drop the dress on a story field.
- **dress F4, the alternative** (have the host send model 0 for a Zidane slot). The guest-side disarm is simpler and
  keeps section 8's body honest.
- **replay F4, the alternative** (decline Change replays). Running `SwitchPlayerRow` at the hit keeps the visible
  step and costs one presentation-only write.

---

## Appendix B. Corrections to earlier documents

- **B4-B5-DESIGN.md 5.8 (stage 12):**
  - The run pose needs cmd_status bit 0 plus `SetDefaultIdle(n, false)` (`btl_mot.cs:565`).
  - R9b's weight is the OnFlee-overload skip: the default gil penalty cannot fire in a diorama, and Disarm restores
    gil anyway.
  - Song 6 plays only in a Game-Over scene (`battle.cs:280`).
  - The defeat path is chosen from the raw phase plus "every local player down".
  - W2 is kind-aware.
  - The scoped no-leak rule applies at the return.
- **B4-B5-DESIGN.md sitting 3, box 36.** A NoGameOver defeat plays NO defeat song in stock. Box A15 supersedes it.
  Boxes 37-39 (hidden enemies, menu-key rotation, the 3D cursor) are out of this round's scope (owner decision).
  Box 40 (WAIT feel) is box A8.
- **r3-recon.md lane 4, box 14.** "Only a silent lane for 2.5 s triggers the takeover" holds only for the selftest
  lapse. On the real link the transport re-serves the last frame for 2 s first, so the takeover comes about 4.5 s
  after a cut, and a 3 s cut shows no capture (box A9).
- **Replay lane citations:**
  - `battle.cs:336` is the ESCAPE dead-unit gate. Victory waits only on `SFX.IsRunning()` (`battle.cs:291`).
  - "SysEscape is never replayed" is moot: `CheckCommandCondition` returns false for SysEscape in PHASE_NORMAL
    (`btl_cmd.cs:1040-1071`), so it never reaches SELECT_VFX.
  - The enemy fade waits for actions only when the GUEST's Speed is >= 3 (`btl_mot.cs:318`, `:333`).
- **Dress lane citation.** `btl_mot.cs:650` sits in the unused `SetDefaultIdleOld`. `:565` is the live MP_ESCAPE pick.

---

## Effort

- **Engine C#: about 5k lines.**
  - Start sync and Wait parity: about 0.7k.
  - Flee and defeat: about 0.5k.
  - Action replay: about 2.0k (s134 alone about 1k).
  - Guest model: about 1.0k.
  - HarnessAgent: about 0.8k.
- **Repo Python: about 2-2.5k lines.** Twelve new scenario files or parts, the codecs, session.py, fakegame.py,
  channel.py, and the pinned tests.
- **Cadence.** 16 DLL rounds (the owner chose to build s112 and s116). Each round is one build, one calibrated
  solo bench and one patch. That is about 10-13 focused build sessions and two two-machine sittings.
- **Adversarial review.** One review of the s114, s134 and s140 diffs before their deploys. This arc's history says a
  verify pass corrects most single-pass claims.
- **Unknowns, settled only in game, in order:**
  1. The laptop's boot-to-live time and swirl (s111's log line; it decides s112).
  2. Whether replays compose and look right over `BattleMapDebug` at Speed 5 (s134).
  3. The real-link timing between the replay's hit and the host's impact frames (s135).
  4. Dressed-body cutscene behaviour in stock story fields (s140).
