# Battle co-op round 3 — sitting A findings and the fix round (s118-s121, tooling T1/T2, soak)

Source: two-machine sitting A (2026-10-14), logs archived in `.harness-runs/sittingA-20261014/` (gitignored run dir). This doc is the synthesis of a 5-agent read-only investigation, re-verified where the plan depends on it. Group 2 of R3-DESIGN.md (action replay + the guest model) shifts from s118-s126 to s122-s130.

## Owner decisions (asked and answered 2026-10-14)

- Session grace (s120): **30 s**, one value for the link-loss exit ramp and the diorama hold.
- A guest slot whose diorama is not live on this battle (s118): **the host keeps it** until a LIVE report returns, then hands it back at the command root.
- Guest main menu while following: **stay blocked (s38 Road A) + the stock buzz and a log line** (s121).
- The host freeze: **the dump catcher (T1) + an A/B soak test** (co-op on vs off) on the desktop.
- Cut recovery model: HOLD-THROUGH (keep the booted diorama frozen, resume the same nonce); rejoin-boot deferred.

## Verdict

NOT A NETSYNC LOGIC BUG, AND NOT CAUSED BY THE CUT/REJOIN.

The game-breaker was a whole-process freeze of the HOST (FF9.exe). It froze inside Unity's post-load asset garbage collection of the 4th encounter's Application.LoadLevel("SwirlScene") (SceneDirector.cs:560). The main thread and both NetSync socket threads stopped together at about 10:38:43.4. Windows closed the hung window at 10:43:45.

No netsync code was on the path:
- Not s111-s117: NoteOwnBattleStart (NetSyncBattle.cs:678, the "battle intro" line at :722) needs gMode 2/4 and was never reached.
- Not the older lanes either.

The holder of the lock that kept the managed world stopped is unknown, and no dump exists. So the hang 'fix' is an instrument first:
- T1: a bridge-side hang sentinel that auto-dumps.
- T2: a wire tap/replay so guest-side work can be benched solo.

A mitigation follows only once a dump names the holder.

BOX 8 is a real, verified, OLD (s56) defect plus two companions:
- The guest's diorama blip-hold tests `_socket.IsConnected` (NetSyncClient.cs:1631). Behind the local bridge that is always true, so a cut reads as 'fight over'. The guest left within ~2 s and stamped the skip nonce.
- The 3 s exit ramp then reloaded the guest's own autosave.
- The host handed slot 1 back at 10:37:27 to a guest whose diorama was gone, because any valid control frame stamps guest liveness (NetSyncBattle.cs:2859).

Fix order, each patch benchable solo:
1. T1, then T2 (tooling).
2. s118: hand-back only to a guest whose s114 report is LIVE/BOOTING for this battle.
3. s119: the diorama hold keyed on the peer, not the loopback.
4. s120: a 30 s session grace, which replaces both the 3 s ramp debounce and the 8 s hold cap, plus a peer-keyed 'reconnecting' overlay.
5. s121: an audible, logged menu refusal.
6. A conditional hang mitigation, chosen by the dump.

The redesign is HOLD-THROUGH (keep the booted diorama frozen and resume the same nonce), not leave-and-re-boot. Rejoin-boot (lane C) is deferred.

BOX 4 (no guest menu in free roam) is intended policy: s38 Road A, owner-chosen and two-machine-proven, untouched by s111-s117. It is only silent, and R3 box A5's precondition is unreachable by design.

Two lane errors are adjudicated here:
- hang-scene placed the freeze in LoadLevel("Loading") after the swirl. The unload-group arithmetic refutes that.
- cut-rejoin's ':1849-1851 reconciler freeze' is in NetSyncDiorama.cs, not NetSyncClient.cs.

Group-2 patches reserved at s118-s126 in R3-DESIGN.md shift to s122-s130.

## The host freeze

WHAT HAPPENED (verified unless marked inferred).

The host process froze whole: the main thread plus the NetSync-relay reader and the NetSync-relay-write threads. It froze inside the first Unity scene load of the 4th random encounter, Application.LoadLevel("SwirlScene") at SceneDirector.cs:560. The freeze fell after that load's serialized-file unload and before its asset-GC summary line.

EVIDENCE

(1) Windows Application log, queried read-only. WER 1001 AppHangB1 at 10:43:44.858 (P4=4b4f) and 'Application Hang' 1002 at 10:43:45.146: "FF9.exe ... stopped interacting with Windows and was closed". System log: no events between 10:36 and 10:45, so no display-driver TDR. WER ReportArchive has AppHang folders only from 2026-07-02, so no dump or report exists for today. Base rate from the same log: 1002 hangs for FF9 on 06-04, 06-06/07/08 (pre-co-op, P4 abaf/ebac/6e8a), 07-01/02 (8135/ad73), 09-04 (abaf), and today 4b4f (first seen). So this engine hangs without netsync too, though under different signatures.

(2) The live x64\FF9_Data\output_log.txt is SHA-identical to the captured copy (F24D907E...) and was last written 10:38:43.4. I parsed it offline into 44 'Unloading N Unused Serialized files' groups:
- Groups 1-13: start-up to 250.
- Then exactly 3 encounters, each [2/97-98, 0/0, 2/1, 4/big, 0/0]: _Swirl's LoadLevel("SwirlScene") then UnloadUnusedAssets, then ChangeScene's Loading/next/unload.
- 3 battle returns, each [2/2, 4/~1150, 0/0].
- 2 debug warps: [2/84, 4/2203, 0/0] and [2/82, 4/1029, 0/0].
- Group 44 is [2 files, UnloadTime 0.5712 ms] with NO 'Unloading N unused Assets ... Total' line. Every earlier swirl head printed that line within ~20 ms.
So the freeze is in the swirl head (SceneDirector.cs:560), not in ChangeScene's LoadLevel("Loading") (:399). Adjudication: the hang-scene lane read [4/1029] as SwirlScene, but no swirl head ever has 4 serialized files, and that reading leaves the 350->250 warp one group short. Its mechanism conclusion stands; its location does not.

(3) The guest proves the host's WRITER thread stopped too, which a main-thread-only hang cannot do:
- NetSyncRelay.WriteLoop (NetSyncRelay.cs:255-270) runs on its own thread: `_frames.CollectOutgoing(due); ... WriteBinaryFrame ...; Thread.Sleep(33);`.
- CollectOutgoing re-sends sticky slots every tick (NetSyncSocket.cs:337 `if (_outPos != null) into.Add(_outPos);`), and the slot is never null (sentinel seeded at NetSyncRelay.cs:82).
- The guest's staleness is receipt-time based: Accept stamps `_remoteTick = now` (NetSyncSocket.cs:358), and GetRemote goes invalid after 2000 ms (:401).
- The laptop logged 'dialogue lock released -- the link has read dead for 3 s' at 10:38:49 (NetSyncClient.cs:2667-2671, LinkGraceMs 3000 at NetSyncDialog.cs:50). That puts its last host frame at 10:38:44.x.
- Independently, its 75 s ReceiveTimeout (NetSyncRelay.cs:164) fired at 10:39:59 = 10:38:44 + 75 s.
- A frozen main thread with a live writer would instead have tripped the F3.3 R6 detector. The heartbeat bumps per host Update (NetSyncClient.cs:2176), and 'the host looks HUNG' (NetSyncDialog.cs:863) fires after HostStallMs 10000 on a FRESH lane (:58). It never fired.

(4) After 10:38:49 the guest re-dialed three times (10:40:01, 10:41:19, 10:42:36). Each time the bridge-to-relay handshake succeeded ('relay connected' is logged only after the bridge's upstream dial; netsync_bridge.py:570-582 'Upstream FIRST'). Each time zero bytes followed and the 75 s timeout fired. So the '~75 s relay drops' are the guest's own read timeout against a silent host, not the relay failing.

ADJUDICATING THE SIX FACTS
- No 'battle intro': the battle never started.
- No Unity lines after group 44's UnloadTime: the main thread stopped mid-GC.
- Link dead after 2+3 s: the writer stopped within ~1 s of the main thread.
- 75 s timeouts: the host sent nothing even to fresh sessions.
- No host disconnect line: this fact is non-discriminating, since a live reader would not have timed out either.
- No host quit line: a hang-close is a TerminateProcess, so RaiseQuitEvent never runs.
Only one single mechanism makes the writer stop together with the main thread. The main thread never takes the writer's locks: _writeLock and the relay _lock are socket-thread only (NetSyncRelay.cs:277, :293, :370, :377), and NetSyncFrames._lock bodies are trivial. So the link has to be the managed runtime itself: a GC stop-the-world that never restarts, or the GC lock held forever. Every allocating Mono thread blocks (WriteBinaryFrame allocates twice per frame at :275/:280). That is exactly the window between the 'UnloadTime' and 'Unloading N unused Assets' lines. The GC part is inferred.

EXCLUDED, VERIFIED IN CODE
- s111/s113-s117 all run after NoteOwnBattleStart (NetSyncBattle.cs:1161-1165 needs InOwnBattle, gMode 2/4, :1425-1435).
- s112's SwirlFrames (NetSyncDiorama.cs:491-527) is pure and try/catch-wrapped, and logs nothing on a host. It may or may not have run before Unity's GC.
- The host-side follow/intent/dialogue hooks are wire-only or guest-only. The debug warps were ordinary field loads that completed (Map lines 10:38:27 and 10:38:35, ghost at 10:38:36).
- The guest's re-pair caused no host transport event: one host 'relay connected' at 10:32:52, no new thread, no new epoch.
- Not the owner's cut either: the cut changed only guest-side state. No causal path to the host GC was found.

UNKNOWN: which suspended thread held what the collector needed. Candidates:
- The NetSync relay reader and writer (co-op-only exposure; old code, unchanged this round).
- The SaXAudio XAudio2 callback thread. It is Mono-attached via reverse P/Invoke TriggerOnFinished (SaXAudio.cs:82, :215-218), and BattleSwirl.Awake plays SEs 634-636 (BattleSwirl.cs:20-28, :75-79).
- AudioEffectManager's FileSystemWatcher thread.
- Unity-internal causes.
A full dump of a hung host is the only discriminator. The 4-swirl sitting cannot discriminate.

### Confidence

Hang:
- Freeze location (the 4th swirl's LoadLevel("SwirlScene") asset GC) and its process-wide scope: HIGH. Six independent signals agree: the WER 1001/1002 events, the output_log stop with its group arithmetic, the guest's 2+3 s link-dead line, the 75 s timeout arithmetic, three empty re-pairs, and R6 never firing.
- Netsync logic (s111-s117 or older) as the cause: EXCLUDED, HIGH.
- The cut/rejoin as the cause: NOT SUPPORTED, MEDIUM-HIGH (no causal path found).
- The GC stop-world / GC-lock mechanism: MEDIUM (inferred; no stack).
- Which thread held the lock: UNKNOWN. Netsync relay threads vs stock SaXAudio/FileSystemWatcher/Unity are each low-confidence.

Box 8:
- The s56 hold predicate is dead behind the bridge: HIGH. Verified in code and in the laptop log: no 'relay disconnected' between 10:32:59 and 10:39:59, and no 'blip -- holding' line.
- The host handed a slot back to a DECLINED guest: HIGH (verified in code and log).
- That the s56 hold has been dead since the 2026-07-23 bridge decoupling: MEDIUM (commit times 96cb9e0d 17:25 vs 2d3514b0 18:27; inferred).

Box 4 is intended s38 policy: HIGH.

The fix plan's in-game behaviour, especially hold-through resume after a 20 s gap, is UNPROVEN until the T2 benches and a two-machine sitting.

## Box 4: the guest main menu

INTENDED POLICY, NOT A BUG AND NOT A REGRESSION. It is silent, which is why it reads as a bug.

The refusal (verified in the clone working tree). Global/UI/UIKey/UIKeyTrigger.cs:699:
`else if (PersistenSingleton<UIManager>.Instance.IsMenuControlEnable && !Memoria.Netsync.NetSyncClient.IsMirroringStory) // co-op: a FOLLOWING guest has no menu [ff9mapkit netsync spectator-field]`
- The same conjunct appears at :510 (Alt+F2 party), :552 (Alt+F5/F9) and :867 (dialog-path Menu).
- IsMirroringStory is `_instance._storyMirroring` (NetSyncClient.cs:602-605). It is true from 'state-mirror ARMED' until the exit ramp fires.
- On the laptop that covers every co-op free-roam window: 10:33:00-10:37:12 (laptop log :35 to :166) and 10:38:23-10:38:49 (:177 to :188).

Why it is intended:
- It is s38-netsync-spectator-field, Road A, recorded in studies/battle-coop/inventory-authority.md:243-258 as 'User chose "A first, then B"' and 'TWO-MACHINE PROVEN'.
- The rationale still holds: the guest's real party, bag and gil are never touched (NetSyncParty.cs:36-39), so an open menu would show the guest's OWN save while the field answers from the host's.
- s111-s117 never touch UIKeyTrigger.cs: grep '^diff --git' s11[1-7]-*.patch has no UIKeyTrigger hit; the only UIKey-path hit is Ff9mkDebugMenu.cs.
- No netsync code writes IsMenuControlEnable.

Two real problems:
(1) The refusal plays no SFX and logs nothing. s121 makes it audible and logged, on FieldHUD/WorldHUD only.
(2) R3 box A5 ('the guest is in its own main menu at the host's encounter', R3-DESIGN.md:1449) and the BUSY row (:270) assume states a mirroring guest cannot reach: main menu, shop, party UI and quad are all refused. The only reachable BUSY trigger is Pause (UIKeyTrigger.cs:681-686 gates only on IsPauseControlEnable). So A5 should be re-specified as 'guest paused'. INFERRED: the owner's 'box 4' is the attempt to set up A5. The owner's 1-8 numbering does not map one-to-one onto A1-A12.

A guest menu while following is a separate policy choice ('Road B-lite', see owner decisions), not a fix.

## The fix round

### T1 (tooling, no DLL; ship BEFORE the next sitting): bridge hang sentinel + auto-dump + timestamped bridge log

Turns the next host hang into a stack. The engine's WriteLoop sends at least 30 frames per second from its own thread, even in menus and loads (NetSyncRelay.cs:255-270; the bridge docstring at netsync_bridge.py:72-79 relies on the same fact). So a game hop that stays open but silent for 10 s or more means the FF9 process stopped sending: it is frozen or suspended.

The sentinel then:
- logs one line with wall-clock ms;
- writes ONE full minidump of FF9.exe per session through dbghelp MiniDumpWriteDump via ctypes (MiniDumpWithFullMemory|HandleData|ThreadInfo|UnloadedModules);
- copies output_log.txt and Memoria.log beside the dump (the memory rule: archive capture logs now);
- logs 'game hop resumed after N s' if frames come back.

It also adds wall-clock timestamps to every bridge line and tees them to a session file, so the sitting gets bridge timings too: the 20 s restore of a 6 s cut, upstream EOF and redial times.

To analyse the dump in WinDbg:
- `~*kb` and `!locks`, with the MS symbol server plus Unity's symbol server (whether symbols exist for 5.2.3p2 is UNVERIFIED);
- look for the main thread under UnityPlayer GarbageCollectSharedAssets / mono GC_stop_world or mark;
- find which suspended thread owns the critical section or heap lock it waits on: NetSync-relay(-write), the XAudio2/SaXAudio callback thread, the FSW thread, or Unity-internal.

**Seams.** ff9mapkit/ff9mapkit/netsync_bridge.py (the canonical copy; tools/netsync-bridge/netsync_bridge.py is a 23-line shim):
- log() at :604-605 (`print("[bridge] %s" % msg, flush=True)`, no timestamp).
- _FramedConn._pull at :287-302 and the read_frame header-wait loop at :312-322. Today, on a poll timeout it only checks the SHARED two-way activity clock (`self.activity.idle_for() >= IDLE_TIMEOUT`). Add a per-direction last-frame clock and an on_quiet callback.
- _Session._game_to_upstream at :467-492: install the sentinel there.
- handle_client at :543-589: resolve the game PID from addr's ephemeral port (iphlpapi GetExtendedTcpTable), falling back to the single FF9.exe.
- main()/argparse at :662-678 and the coop host/join launcher that starts the bridge in-process: add --hang-dump DIR, --log FILE and --hang-after S (default 10).

**Bench.** Solo, against the deployed s117 DLL:
1. Set the desktop to Role=host, RelayUrl ws://127.0.0.1:49201.
2. Run `ff9mapkit coop bridge --relay ws://127.0.0.1:7777` and a local relay (`go run studies/battle-coop/relay/main.go`).
3. Add a fake guest: adapt tools/netsync-bridge/test_relay_roundtrip.py ws_client_connect to role=guest and send v14 type-0 frames at 30 Hz, so the relay pairs and reads the host.
4. On field 250, suspend FF9.exe for 15 s (ctypes ntdll NtSuspendProcess / NtResumeProcess), which simulates the world stop.

RED today: the bridge prints nothing and no .dmp appears.
GREEN after T1:
- one 'game hop SILENT 10 s' line at about +10 s;
- one .dmp whose `~*` lists threads named NetSync-relay and NetSync-relay-write;
- one 'resumed after ~15 s' line;
- the game continues.

Also a pytest with a socketpair: a silent peer trips the sentinel at the threshold, and a 30 Hz peer never trips it.

### T2 (tooling, no DLL): wire tap + replay fake host with blackhole injection -- the solo two-role bench

Today no guest-side watcher, exit-ramp or mirror-gated behaviour can be benched solo:
- The selftest role returns before the transport and DioramaTick exist (NetSyncClient.cs:1180-1263 vs the transport at :1265-1286).
- IsMirroringStory needs a real socket (ApplyStoryImpl :549-577).

T2 fixes that:
- The bridge gains --tap FILE. It unmasks and records the game's outgoing NetSyncWire frames (types 0/1/4/5/6) with timestamps.
- tools/harness/wire_replay.py replays a recorded HOST session as role=host through the local relay.
- --blackhole-at T --blackhole-for N keeps the TCP open but sends nothing, which is what a Wi-Fi cut looks like behind the decoupled bridge (netsync_bridge.py:18-25).

The recording is a one-time solo run: the desktop as host plus a fake guest. Walk 250 to a random encounter, fight about 40 s, win. Replay then runs the desktop as Role=client with FollowHost=1 and its own save on 250. The same-field kick, mirror arm and diorama boot all come from the recorded type-5/type-1/type-4 frames.

**Seams.** - netsync_bridge.py _game_to_upstream at :467-492: the tap point. Frames are whole WS frames, masked; unmask with the 4-byte key.
- New file tools/harness/wire_replay.py: reuse ws_client_connect/send_binary from tools/netsync-bridge/test_relay_roundtrip.py:30-63, and the frame header layout from NetSyncWire.BuildFrame (NetSyncSocket.cs:158-170).
- Harness assertions read Memoria.log through tools/harness/logs.py.

**Bench.** Calibration: replay with no blackhole. The guest logs:
- 'paired on the host's field (250)';
- 'state-mirror ARMED';
- 'diorama BOOT';
- 'diorama LIVE';
- the end-leave.
If any is missing, the instrument is not trustworthy, so fix T2 before judging s119-s121 with it.

Then the sitting-A row: --blackhole-at <battle+10 s> --blackhole-for 6. On s117 it must reproduce laptop-Memoria.log:155-159 verbatim: 'diorama LEAVE requested' and 'watcher-leave settled (nonce N)' within about 2 s. That reproduction is the RED that later patches flip.

### s118-netsync-handback-needs-live-guest (HOST)

VERIFIED DEFECT (pre-existing B4 stage 11 / s110 code that s114 made fixable).

ParseControl stamps guest liveness on ANY valid control frame. NetSyncBattle.cs:2859:
`_assistTick = Environment.TickCount;   // any valid control frame = the guest is live + watching`
IsGuestOwnedSlot reads only that stamp (:531, `return (Environment.TickCount - _assistTick) < MenuStaleMs;`). The guest sends control frames whenever the host's lane is live and it is not in its own battle, booted or not (:1269, `if (live && !inBattle)`). So at 10:37:27 G3 (HandBackGuestSlot, :1016-1063) handed slot 1 back (desktop Memoria.log:73) to a guest that:
- had left its diorama, with the skip stamped (laptop :155-159);
- had reloaded its own autosave (:166);
- was therefore reporting DECLINED for nonce 3 (GuestBootState, :2663-2681).
Its only means of commanding was the legacy digit panel (laptop :157).

FIX: when the frame carries an fmt-1 trailer, stamp _assistTick only if the report names THIS battle (as StartHoldTick does at :3051: `_rptNonce == _battleNonce`) with rptBoot LIVE or BOOTING. NONE, DECLINED and BUSY leave the guest's slots with the host's ready loop. That honours the law at :512-517: 'a dropped/busy peer can never orphan a party member'.
- G3 then hands back the moment a LIVE report returns: root-only, code unchanged.
- Legacy trailer-less frames keep today's behaviour.
- Log one line per battle: 'the guest's control lane is live but it reports <X> for this battle -- its slots stay with the host's window'.
- Publish a harness counter.
- The s114 start hold reads rptThis/rptBoot separately, so it is unaffected.

**Seams.** - NetSyncBattle.cs ParseControl at :2844-2890 (the :2859 stamp; the trailer fields _rptNonce/_rptBoot are already set at :2864-2870).
- IsGuestOwnedSlot at :520-532: unchanged.
- TrackHostHold at :980-1012: the capture-line wording for the 'reports DECLINED' case, which today would read 'silent N ms'.
- HandBackGuestSlot at :1016-1063: unchanged.
- The guest send at :1269-1275: unchanged. It must keep sending, because the report and Wait parity ride the frame.
- Harness (HarnessAgent.cs): publish netsync.battle.host.handback.refused_report.
- Add a pure row table GuestOwnsFromReport to the existing ControlSelfTest (the StartHoldStep style, :3193-3225).

**Bench.** Solo selftest with existing s114/stage-11 levers (HarnessAgent.cs:1133, :1219), so it runs on the deployed s117:
1. `netsync selftest 1`, GuestSlots=2, start a battle.
2. `netsync bench boot live`, then let slot 1's turn reach the loopback guest.
3. `netsync bench lapse hold`. After about 2.5 s the host's window captures slot 1 ('hand-back: the host's local window holds guest slot 1').
4. `netsync bench boot declined`, then `netsync bench lapse end`.

RED on s117: 'guest slot 1 handed BACK' and handback.returns+1.
GREEN on s118:
- no hand-back;
- the host's window keeps slot 1;
- one 'reports declined' line;
- then `netsync bench boot live` gives one hand-back at the root.

Repeat with `bench boot busy` (stays with the host) and `bench boot booting` (handed back, which matches today).

### s119-netsync-diorama-hold-on-peer (GUEST)

VERIFIED DEFECT (s56 code, NOT s111-s117).

The watcher classifies a stale battle lane by the LOOPBACK. NetSyncClient.cs:1631 `Boolean transportUp = _socket != null && _socket.IsConnected;` and :1640-1644:
`else if (transportUp) { shouldLeave = true; // stale + link UP -> the fight is over`
Behind the local bridge, IsConnected stays true through any upstream cut shorter than UPSTREAM_REDIAL_HARD_CAP 45 s (netsync_bridge.py:86). So the hold branch at :1645-1662 never runs. Sitting A shows this:
- 'LEAVE requested' at 10:37:09, about 2 s after the cut;
- no 'relay disconnected' and no 'mid-battle link blip -- holding' line;
- the final flag (:1695) made teardown stamp the skip (:1557-1563): 'won't re-boot on reconnect'. Then :1709 `if (nonce == _dioramaSkipNonce) return;` blocked any re-entry.
The comment at :1625-1630 even says the discriminator is 'its 30 Hz position keepalive holds the link'. The code just reads the wrong thing. The repo already states the law at :611-623, IsLiveFollowedSession: 'IsConnected alone is a liar on the relay'.

FIX:
- peerAlive = IsConnected && GetRemote().Valid.
- 'Genuinely over' = peerAlive AND (the host is back on a field, i.e. rs.Field > 0 && != 65535, since the host sends field 0 throughout a battle, :1290-1302; OR the booted nonce's end block was latched TERMINAL while the lane was live).
- The latch is needed because TryGetPeerEnd reads only the live view, which is nulled when stale (NetSyncBattle.cs Pump `_peerView = null` in the !live branch). Use NetSyncEnd.IsTerminal.
- Everything else is a HOLD. The reconciler already freezes at the last applied state (NetSyncDiorama.cs:1849-1851 `no live peer battle: freeze at last applied state`). The s114 report stays LIVE (booted, same nonce, live latch), so s118 hands the slot back on resume.
- The cap stays DioramaBlipHoldMs 8000 (:449) in this patch; s120 widens it.

**Seams.** - NetSyncClient.cs DioramaTick: the booted branch at :1618-1706, specifically :1631 (predicate), :1634-1639 (latch the end kind while live), :1640-1644 (the 'over' test) and :1645-1662 (hold-line wording).
- NetSyncBattle.TryGetPeerEnd and NetSyncEnd.IsTerminal: read-only use.
- StockMenuTick's 'no live peer battle lane' close (laptop :156-157) is acceptable during a hold, because the ready mirror re-serves on resume. Verify on the bench.
- Extract a pure DioramaWatchStep (live, nonce, bootedNonce, peerAlive, hostField, terminalLatched, staleSinceMs, cap) -> NOTHING/HOLD/LEAVE_FINAL, and table-test it in SelfTest. Mirror it in tools/harness/battlewire.py.

**Bench.** T2 replay with a 6 s blackhole 10 s into the recorded battle.

RED on s117: within about 2 s, 'diorama LEAVE requested' then 'watcher-leave settled (nonce N)' (the sitting-A line pair).
GREEN on s119:
- one 'peer silent mid-battle -- holding' line;
- NO LEAVE;
- after the gap the reconcile applies a new seq on the SAME nonce and 'ready mirror is SERVING' returns.
Negative row: a blackhole spanning the recorded victory. On resume the host's position reads field 250, which gives LEAVE_FINAL and an ordinary return.
Pure-table calibrating row (sitting A): IsConnected=1, pos stale, battle stale, host field 0, not terminal. Old predicate gives LEAVE_FINAL; new gives HOLD.

NOTE: on s119 alone the 3 s exit ramp still goes pending during the gap and fires at the next settled field after the battle. That is s120's RED row, not s119's.

### s120-netsync-session-grace (GUEST)

VERIFIED: the session ends 3 s after the position lane dies, and a pending ramp is never cancelled.
- `private const Int32 ExitRampDebounceMs = 3000;` at NetSyncClient.cs:470.
- The arm at :1169-1177. `_exitRampPending` is cleared only by firing (:1121-1130). Firing also sets `_storyMirroring = false` and calls `NetSyncParty.Clear()` (:1124-1129).

A 6 s physical cut cost about 20 s end to end: host 'silent 8406 ms' at 10:37:16, back at 10:37:27-28. So with s119 alone the guest resumes the diorama and is then yanked to its autosave after the battle.

FIX:
- One SessionGraceMs (default 30000, an owner decision) replaces BOTH the link-loss ramp debounce and DioramaBlipHoldMs (:449). The diorama then holds exactly as long as the session lives. Past the grace: leave final, then the ramp, as today.
- Keep the immediate deliberate-config arms at :941 and :965.
- Keep LinkGraceMs 3000 for the dialogue lock only (NetSyncDialog.cs:50).
- Add `&& !NetSyncDiorama.Booted` to safeToLoad (:1085-1086) as belt-and-braces. INFERRED: today fieldmap is null in the battle scene, so the ramp already cannot fire mid-diorama.
- Add a 'reconnecting (N s)' overlay keyed on peer-alive. OvlConnecting (:1409-1410) and the s56 ghost blip-grace (:1385 `!_socket.IsConnected`) key on IsConnected and never trip behind the bridge. Move both to the same peer-alive predicate.

Why 30 s: it covers the observed ~20 s restore. It stays under the bridge's 45 s hard cap (netsync_bridge.py:86) and the relay's rejoinGrace 60 s (studies/battle-coop/relay/main.go:42). The disk stays safe because the save gates hold while _storyMirroring (:598-605).

**Seams.** NetSyncClient.cs:
- :449 and :470 (constants);
- :1078-1133 (ramp, safeToLoad);
- :1160-1177 (the sessionLive arm);
- :1385 (ghost grace);
- :1405-1411 (overlay selection);
- the DioramaTick hold cap at :1645-1662 (it reads the new constant).
Also the HarnessAgent publication of netsync.session.grace_ms and the remaining grace.

**Bench.** T2 replay legs:
- 20 s blackhole mid-battle. RED on s117 and on s119-alone: 'session ended -> reloading own autosave' (at once on s117, after the battle on s119). GREEN on s120: no session end, the diorama resumes on the same nonce, and after the recorded victory the guest stays mirrored ('state-mirror ARMED' stays true).
- 40 s blackhole: 'session ended' at about 32 s (bounded).
- 20 s blackhole in free roam: the 'reconnecting' overlay is shown, no ramp, and the ghost and mirror resume.

### s121-netsync-guest-menu-refusal-feedback (GUEST UX)

Box 4 is intended policy, but SILENT. UIKeyTrigger.cs:699 reads:
`else if (PersistenSingleton<UIManager>.Instance.IsMenuControlEnable && !Memoria.Netsync.NetSyncClient.IsMirroringStory) // co-op: a FOLLOWING guest has no menu`
It drops the key with no SFX and no log, unlike the Alt+F2 (:510) and Alt+F5/F9 (:552) gates, which play FF9Sfx 102.

FIX:
- Add a branch: when IsMirroringStory && IsMenuControlEnable && the UI state is FieldHUD or WorldHUD, play FF9Sfx 102 and call NetSyncField.DeclineOnce("main menu") (NetSyncField.cs:52-64).
- Optionally add one overlay hint naming the way back (the session ending, or ~ > Leave).
- Do NOT touch :867 (dialog path), the battle HUD (the B4-B5 stage-13b Menu-key decision) or the save gates.
- It is inert on vanilla, because IsMirroringStory is false there.

**Seams.** - Global/UI/UIKey/UIKeyTrigger.cs:694-701.
- NetSyncField.DeclineOnce.
- NetSyncClient.IsMirroringStory (:602-605).

**Bench.** T2 replay until 'state-mirror ARMED', then the harness presses Menu on FieldHUD.
- RED on s117: no refusal line, UI stays FieldHUD.
- GREEN on s121: exactly one 'main menu' decline line plus SFX 102, and UI stays FieldHUD.
- Control row: after the replay ends and the ramp fires, Menu opens the stock main menu.

### s12x (CONDITIONAL, numbered when built): hang mitigation chosen by the T1 dump

Ship nothing blind. Pick the branch the dump names.

(a) The holder is NetSync-relay or NetSync-relay-write:
- WriteLoop builds one reused buffer per tick with one stream.Write, instead of 2 allocations plus 1 send per frame (NetSyncRelay.cs:272-294). Mirror the change in NetSyncSocket's write loop.
- Add a scene-load quiesce: a static volatile deadline (now + 750 ms, under the guest's StaleMs 2000), set on the main thread at the LoadLevel/UnloadUnusedAssets seams. The writer sleeps rather than allocating. Never Stop() the transport, never block the main thread.
(b) The holder is the SaXAudio callback thread: TriggerOnFinished (SaXAudio.cs:215-218) enqueues voice ids for the main thread instead of running managed handlers on the XAudio2 thread. This is a stock-Memoria change, local patch stack only, never an upstream PR.
(c) Unity-internal with no managed holder: document it and stop. No netsync change is justified.

**Seams.** - (a) NetSyncRelay.cs:255-294 and SceneDirector.cs:80-83 (ReplaceNow), :399-401 (ChangeScene), :457-460 (ChangeSceneAsync), :558-566 (_Swirl).
- (b) SaXAudio.cs:82, :213-218; VoicePlayer subscribers.

**Bench.** An A/B soak on one machine, with T1 armed:
- host plus fake guest (T1 setup), 200 or more swirl loads (walk 250, or a harness fight that routes through SceneDirector.Swirl);
- versus the same loop with [NetSync] Enabled=0.
Count hangs per arm. RED on s117 only if the race reproduces; it is probabilistic, so say so. The fix is GREEN when its arm reaches the same N without a hang and the dump's lock pattern cannot form.

### D1 (docs, no DLL)

- R3-DESIGN.md:1449 A5: re-spec as 'the guest is PAUSED (laptop Backspace) at the host's encounter' and mark sitting-A A5 'not run -- precondition unreachable (s38)'.
- :270: the BUSY row lists main menu/shop/card game, which are refused to a mirroring guest. Pause is the only reachable BUSY.
- :1450 A6: its premise 'the laptop's blip-hold rides the cut' was false until s119/s120.
- :1001-1021 and :71-78: renumber group 2 from s118-s126 to s122-s130 (the wire tables say 's118').
- memoria-patches/README.md s56 row: note the hold was inert behind the bridge until s119.
- Memory (project-ff9-multiplayer-injector.md): the law 'every link-down test reads peer-alive (IsConnected && GetRemote().Valid), never IsConnected'.
- Sitting checklist: if the host hangs, leave it about 30 s for T1, or Task Manager > Create memory dump file BEFORE closing.
- Retest A3 (Dali cold), A5-as-pause, A6, A11 and A12 (flee), none of which were exercised.

**Seams.** studies/battle-coop/R3-DESIGN.md, memoria-patches/README.md, project memory.

**Bench.** Parse-check edited YAML/frontmatter (the YAML frontmatter trap). Otherwise none.

## Owner decisions as proposed (answers above)

- Next sitting before the hang is explained. RECOMMENDED: proceed. Netsync logic is excluded and the freeze is in stock Unity scene-load GC. Run T1 armed. If the host hangs, leave the hung window ~30 s for the auto-dump (or Task Manager > Details > FF9.exe > Create memory dump file) BEFORE closing it.
- T1 auto-dump default. RECOMMENDED:
- ON for dev-bundle coop host/join sittings: one full dump per session to %LOCALAPPDATA%\ff9mapkit\hangdumps, 1-3 GB, local only;
- opt-in (--hang-dump) in public releases;
- the timestamped bridge log always on.
- Blind hang mitigation (relay-writer quiesce or allocation-free writes) before a dump names the holder. RECOMMENDED: NO. Instrument first, as calibration before judgment. Revisit only if a second hang occurs without a dump being captured.
- Who commands a guest slot when the guest's diorama is NOT live on that battle (s118). The cases are a DECLINED, NONE or BUSY report: a cut, a ~ Leave, a pause. RECOMMENDED: the HOST keeps the slot until a LIVE report returns, then hands it back at the command root. BOOTING still counts as guest-owned, so a normal start is unchanged. The alternative is today's behaviour: the slot goes back to a guest whose only control is the legacy digit panel on its field.
- Session grace length (s120). RECOMMENDED 30 s, the same value for the exit ramp and the diorama hold. The valid range is about 15-40 s, and it must stay under the bridge's 45 s hard cap and the relay's 60 s rejoin grace. Cost: after a REAL host quit, the guest stays mirrored, unable to save, for about 32 s instead of about 5 s before reloading its own autosave.
- Cut recovery model. RECOMMENDED: HOLD-THROUGH (s119+s120). Keep the booted diorama frozen and resume the same nonce when the peer returns within the grace. DEFER the cut-rejoin lane's lapse-leave + rejoin-boot (C); build it only if a sitting shows a case hold-through misses, e.g. a diorama that genuinely left mid-cut.
- Guest main menu while following. RECOMMENDED: keep Road A (s38 spectator-strict) and ship the audible, logged refusal (s121). A 'Road B-lite' read-only subset (Config, Journal) or the full Road B shared bag is its own arc. Facts for that arc:
- the guest's menu reads the guest's own party, bag and gil (NetSyncParty.cs:36-39);
- writes there would be session-scoped and discarded (the save gates and the exit ramp);
- the seam would be UIKeyTrigger.cs:699 plus MainMenuUI entry greying.
- Re-spec R3 box A5 as 'guest paused (Backspace) at the host's encounter' and mark sitting-A A5 as 'not run -- precondition unreachable'. RECOMMENDED: yes.
- Patch numbering. The new s118-s121 take the next free numbers (s117 is the last README row). The R3-DESIGN group-2 reservations s118-s126 (action replay + the guest's own field model) shift to s122-s130, including the wire-table 's118' references at R3-DESIGN.md:71-78. RECOMMENDED: yes, renumber in D1 before group-2 work starts.

## Phase 1: every bench calibrated red on the deployed s117 (2026-10-14, in game, solo)

The harness pass (branch claude/resume-r3-build-harness-5e5400) was run on the desktop against the DEPLOYED s117 DLL (`c5d521b7`). Run dirs are in that worktree's gitignored `.harness-runs/20261014-22*`. The tape is `<main repo>/.harness-runs/coop-tapes/20261014-224827-host250-s117.f9tape`.

- coop_battle_start_hold: 24/24, B2 reading 'OK (33 rows)'. Needs `[Netsync] Enabled = 0`: the selftest role refuses a live host/client config ('refusing to override a real session'). An earlier launch stopped on a stray Pause mid-intro; the rerun was clean.
- coop_handback_live: red exactly P0, PROOF, N2, D1-D3, L1, L2, B1, B2, S1, S2; green S0, P1, P2, PRE, N1, T1. S18-CAL PASS. s117 hands slot 1 back to a guest reporting DECLINED, BUSY, a stale LIVE or NONE-after-a-diorama: the sitting-A defect, in game.
- coop_tape_record: 13/13. `battle 67 -1 rand` publishes as a real own battle; F1-F5 on a 12.2 MB tape; Memoria.ini restored byte-exact.
- coop_cut_hold cal: 10/10. ANSWERS the T2 unknown below: a recorded host replayed into a guest-role desktop pairs on 250, arms the mirror, boots the diorama, goes LIVE on the same nonce and leaves by the end-leave (never the watcher).
- Calibration legs (COOP_CALIBRATE=1), every <LEG>-CAL PASS, no unpredicted red:
  - s119: red G1-G5, K. S119-RED: sitting A's pair ('diorama LEAVE requested', 'watcher-leave settled (nonce 1)') inside 1-4.5 s of a 6 s cut.
  - s120-battle: red G1-G5, K. s120-long: red G1-G3, K. s120-roam: red G1-G5. Each RED: 'session ended -> reloading own autosave' 3.5-9 s after the cut.
  - span: red G1, G2, K. RED: the sitting-A pair before the cut ends (the guest abandons the unseen victory).
  - s121: red G0, G1, G2, G4, G5; G3 and C1 green (the s38 drop keeps the menu shut; the control row opens MainMenu). RED: the press is silent.

## Phase 3: s118-s121 deployed and solo-proven (2026-10-14/15, in game, solo)

Deployed by `build_memoria.py` (backup set `20261014-230936`; Assembly-CSharp `685e76902524e207`). The full-file audit read 98 of 98 clone files byte-exact with the stack before the build. The four new proof lines are in-game: 'battle control selftest: OK (53 rows)', 'diorama watcher selftest: OK (24 rows)', 'session grace selftest: OK (31 rows)', 'main menu refusal selftest: OK (14 rows)'.

- Selftest benches (`[Netsync] Enabled = 0` for the block, restored after): start hold 24/24 ('OK (53 rows)'); hand-back 18/18, COOP_CALIBRATE=1 19/19 (S18-CAL on the empty set).
- The 6.1 regression set, all at the s117 baseline: intro 18/18, wait parity 12/12, flee/defeat 53/53, host gates 20/20, containment 23/23, stock menu 27/27, content 35/35, live 40/40, end host 23/23, end guest 49/49, result replay 50/51 (S9-C4L, not reachable solo, as on s117), hand-back 21/21, diorama return 22/22, talk relay 28/28, dialogue authority 147/147.
- T2 on the s117 tape: cal 10/10 re-keyed to s121, then every leg GREEN:
  - s119 12/12: a 6 s cut held the frozen diorama 4047 ms on nonce 1, resumed, 'ready mirror is SERVING' again.
  - s120-battle 12/12: an 18 s cut, 'the host is back after 18015 ms -- inside the 30 s grace', the diorama held 16094 ms and resumed, still mirrored after the recorded victory.
  - s120-long 10/10: a 40 s cut gave up at 30016 ms, then the ramp.
  - s120-roam 11/11: the reconnecting overlay counted 24 -> 13 over 11.4 s, the ghost and mirror back within 3 s, story byte 1121 read the host's 0xA5 throughout.
  - span 9/9: the cut over the victory held 12 s, then 'the host's fight is over (the peer is alive and back on field 250) -- leaving'.
  - s121 13/13: one 'main menu suppressed (following guest) on field 250' line, count/lines 1/1 then 1/0, FieldHUD kept, the menu 'open' after the ramp.
- Each leg with COOP_CALIBRATE=1: only <LEG>-RED red (the s117 defect no longer reproduces), every <LEG>-CAL PASS.

Next: R3 sitting B, two machines, the real bridge + relay, T1 armed; retest A3, A5-as-pause, A6, A11, A12. Then group 2 (s122-s130). The s120-world leg (a hand-recorded world-map tape) is still unrun.

## Phase 4: the laptop package for sitting B (2026-10-15, cut, NOT copied to the laptop)

Package `Desktop\FF9Coop-laptop-update-20261015-r3b` (+ `.zip`, 4.8 MB; the Desktop is the OneDrive one). Recipe = the r3a folder: `dlls\x64|x86` (the three DLLs per arch, taken from the LIVE install), `bridge\`, `mod-overlay\` (field 30801's `.eb`, byte-identical to the live desktop copy and to the 2026-10-12 overlay), `HASHES.txt` (16-hex SHA-256 prefixes), `HASHES-full.txt`, and a `README.md` that IS the box sheet. No packaging script exists; the folder is hand-assembled (the assembly was a throwaway script, not committed).

- Engine: Assembly-CSharp `685e76902524e207` (full `685e76902524e207be54c49c8d31635546450596164519dbb50973e23613861e`) on both arches, identical to the live desktop install at packaging time; Memoria.Prime `783384a3b83953eb` and UnityEngine.UI `690852b1a40db178` are unchanged from r3a. Wire stays v14. Verified: live x64/x86 shas, folder == `HASHES-full.txt`, the zip's 15 files re-hashed from the zip.
- NEW vs earlier packages: `bridge\netsync_bridge.py` `88fcdf0a36cf642c` + `bridge\hangdump.py` `13db9d906f531b8e` (T1, the master copies). They run as a bare script from the folder (`py bridge\netsync_bridge.py --hang-dump`, hangdump.py beside it; smoke-tested, listens and arms) so the laptop's installed kit version is irrelevant. The earlier packages' 29638-byte bridge is the pre-T1 one. `--hang-dump` is default OFF: pass it on BOTH bridges for sitting B (the desktop: `py -m ff9mapkit coop bridge --hang-dump` from the repo `ff9mapkit\`).
- Sheet (README): A. the six cut legs proven solo (s119 6 s hold, s120 18-20 s inside the grace, the span-the-victory leg, the reconnecting overlay in free roam, the give-up at about 32 s on a 40 s cut, the s121 audible refusal); B. the sitting-A boxes never run (A3 Dali cold / back to back, A5 re-specced as guest PAUSED, A6 cut during the swirl, A11 bumper flee, A12 Zidane's Flee gil, the s117 defeat); C. one plain fight as a regression row. Plus the T1 procedure (a hung game: do not close it, wait for 'hang dump written' or at least 30 s, else Task Manager > Create memory dump file), the laptop's `[Netsync]` block with the new guest key `SessionGraceMs` (30000, clamped 5000-40000, live), and the return list (both Memoria.log + output_log.txt, both bridge logs from `%LOCALAPPDATA%\ff9mapkit\bridge-logs`, the cut clock times). The numbering is the README's own 1-13, not R3-DESIGN's A-/B-tables (R3-DESIGN's "Sitting B" table is the group-2 action-replay sitting and is not this build).
- Predictions in the sheet that were NOT proven solo and are marked as such: A6 (what the laptop does after a cut during its swirl: hold, late-boot or field), the real-link timings (a 6 s physical cut cost about 20 s end to end in sitting A; the bridge log is now timestamped to measure it).

## Open unknowns

- Which suspended thread held the lock that kept the host's managed world stopped. The candidates are NetSync-relay(-write), the SaXAudio/XAudio2 callback thread, the AudioEffectManager FileSystemWatcher thread, or Unity-internal. No dump exists: WER archived only July AppHang folders. This decides whether the hang is co-op exposure or stock.
- The exact phase inside Unity 5.2's LoadLevel where it stopped: the Mono collection vs the liveness/MarkObjects pass. It is also unknown whether BattleSwirl.Awake (SEs 634-636) and the s112 SwirlFrames call had already run.
- The hang's frequency: one in 4 swirls in sitting A versus none across many earlier two-machine battles. An A/B soak (host + fake guest vs Enabled=0) is needed to show whether netsync raises the odds.
- Desktop/laptop clock offset (about ±1 s). It only affects how tightly the 'writer stopped within ~1 s of the main thread' coincidence is bounded.
- Why a 6 s physical cut cost about 20 s end to end: bridge redial backoff, TCP RTO, Wi-Fi re-association, or the relay's stale-leg replace. Neither bridge console was captured and the bridge prints no timestamps; T1 fixes this.
- Whether the host's slot 1 acted at all between the 10:37:27 hand-back and the 10:38:13 victory, and whether the owner saw the legacy digit panel on the laptop field.
- Whether hold-through resume works in-game after a 20-30 s gap: the reconciler catching up on dead enemies, the stock menu re-serving, the s114 report reading LIVE. The s56 hold was never exercised on the bridge topology.
- ~~Whether T2's recorded-host replay boots a diorama faithfully on a guest-role desktop~~ ANSWERED YES (Phase 1, cal 10/10 on s117).
- Whether Unity's symbol server has symbols for the 5.2.3p2 x64 standalone player and its mono.dll, which affects how readable the T1 dump is.
- Boxes not exercised in sitting A, to retest: A3 (Dali cold / back-to-back), A5-as-pause, A6 (cut during the swirl), A11/A12 (bumper flee, Zidane's Flee gil relay) and the s117 defeat presentation.

## Appendix: the four investigation lanes (summaries)

### lane

VERDICT (my lane): the host did not have a main-thread-only hang. The whole process froze, and every managed thread stopped at the same moment: the main thread plus NetSync-relay-write and the NetSync-relay reader. It happened at about 10:38:43.4 (desktop clock). It froze inside the 4th encounter's first scene load, the swirl's Application.LoadLevel("SwirlScene") at SceneDirector.cs:560, between the serialized-file unload and the asset garbage collection that follows it. It stayed frozen until Windows closed it 5 minutes later.

VERIFIED (system and logs):
(1) Windows Application log. WER Event 1001 "AppHangB1" at 10:43:44, P1 FF9.exe, hang signature P4=4b4f, which is a first-seen signature (earlier FF9 hangs were abaf, ad73, 8135, ebac and others). Event 1002 "Application Hang" at 10:43:45: "FF9.exe ... stopped interacting with Windows and was closed". So the process was hung, not crashed or killed early. That is why there is no RaiseQuitEvent; the laptop quit at 10:43:37 in the same moment.
(2) The live x64\FF9_Data\output_log.txt was last written at 10:38:43.389. It is byte-identical to the copy in .harness-runs. Its final lines are "Unloading 2 Unused Serialized files (Serialized files now loaded: 17) / UnloadTime: 0.571200 ms" and it ends on the CRLF. I parsed all 44 unload groups offline. Every scene change has a fixed shape:
   - A normal scene change (Replace) is three groups, [small, big, 0|1/0]: LoadLevel("Loading"), then Resources.UnloadUnusedAssets(), then LoadLevel(next) (SceneDirector.cs:399-402).
   - Every swirl into battle adds [2/~97, 0/0] in front (_Swirl, SceneDirector.cs:560/566).
   The groups map exactly onto title->250, 3 x (field->battle, battle->field), 250->350 and 350->250. The final "2/<no asset line>" group is the 4th swirl's head. On all three earlier swirls that same unload was followed straight away by "Unloading 98/97/97 unused Assets ... Total ~18-20 ms (MarkObjects ~17-20 ms)" (log line pairs 165/168, 210/213, 255/258 in Read numbering). This time that line never came. The asset collections 8-16 s earlier took 21.8 ms (2203 assets) and 21.9 ms (1029 assets), so a slow-but-finite collection is ruled out.
(3) Guest side. Two independent measures put the last host frame at about 10:38:44.x (laptop clock), 0.6-1.6 s after the output_log stop, which fits a small clock offset:
   - the link-dead release logged at 10:38:49: StaleMs 2000 at NetSyncSocket.cs:257 plus LinkGraceMs 3000 at NetSyncDialog.cs:50;
   - the 75 s ReceiveTimeout (NetSyncRelay.cs:164) firing at 10:39:59.
   After that the guest received zero bytes through three fresh relay sessions (10:40:01, 10:41:19, 10:42:36), and each ended in another 75 s timeout. The public relay was up each time: the game logs "relay connected" only after the bridge's upstream handshake succeeds (netsync_bridge.py:570-581, "Upstream FIRST"). The guest never logged "session on" again.
(4) The host's Memoria.log has nothing after 10:38:36. Log.Write is synchronous, Monitor-guarded and flushed from any thread (Memoria.Prime/Log.cs).

VERIFIED IN CODE (why this means a process-wide freeze):
- NetSyncRelay.WriteLoop (NetSyncRelay.cs:255-270) runs on its own thread. Every 33 ms it re-sends the latest slots, and _outPos is never null: the constructor seeds a sentinel (:82-83) and every Update calls SetLocal (NetSyncClient.cs:1291-1303). So a host whose main thread alone hangs keeps sending stale frames.
- The engine anticipates exactly that case. The host heartbeat bumps every Update (NetSyncClient.cs:219, 2176). A frozen heartbeat on a still-fresh lane makes the guest log "the host looks HUNG" after 10 s (NetSyncDialog.cs:838-864). Instead the guest logged the link-dead release (NetSyncClient.cs:2667-2671), which only fires when sessionBase holds (not HostStalled) and the pos lane is stale (IsLiveFollowedSession, :615-626).
- There is no lock path from the main thread to the socket threads:
   - NetSyncFrames uses one leaf lock with trivial bodies and does no I/O under it (NetSyncSocket.cs:272-343).
   - The relay's _lock and _writeLock are only ever taken by socket threads (:277, :293, :370, :377).
   - The "out-of-band pushes" are slot swaps (NetSyncClient.cs:2036 SetLocalState).
   - Connect runs on the NetSync-relay thread (:149-193). Stop() is only called from ApplyConfigChange (:917-922) and OnDestroy (:1466-1471), and either would have logged.

What the host ran up to the freeze (all bounded, try/catch, no waits or loops):
- NetSyncClient.Update (:1058-1460);
- the SettingsState.cs:54 encounter gate (false on the host);
- SceneDirector.Replace -> Swirl (:134-138) -> _Swirl (:547-560): CreateScreen, then LoadLevel. FROZE here.
- BattleSwirl.Awake -> SFX_Rush constructor -> NetSyncDiorama.SwirlFrames (s112, NetSyncDiorama.cs:488-528; pure, try/catch). This may or may not have run before Unity's asset collection.

Never reached: SFX_Rush.update/NoteSwirlDone, the BattleSwirl song hooks, ChangeScene, HonoluluBattleMain.Start (:169/:193), and NoteOwnBattleStart (NetSyncBattle.cs:678/1164/1331, which is why there is no "battle intro" line). The guest saw no nonce-4 boot block either. So none of the s111/s113-s117 code ran, and the s114 start hold is excluded.

The preceding sequence changed nothing at the host's transport level:
- The host logged one "relay connected" (10:32:52) and no drop.
- The laptop's relay TCP survived the 6 s cut (no laptop "relay disconnected" until 10:39:59), so there were no new threads and no new epoch (the epoch is reset only at transport start, NetSyncClient.cs:1285).
- The guest's re-pair was guest-side session logic only.
- The hand-back battle ended cleanly at 10:38:20, and both intents (nonce 1, 2) landed.

INFERRED: Unity 5.2's post-load asset collection runs a Mono/Boehm collection and a liveness/MarkObjects pass with the managed world stopped. A stopped world that never restarts freezes every Mono-registered thread at once, which is the only single mechanism that fits all four signals. Which suspended thread held what the main thread needed is unknown without a dump. Candidates:
- SaXAudio's XAudio2 callback thread. It enters managed code via SetOnFinishedCallback/TriggerOnFinished (SaXAudio.cs:82, 213-217), and the swirl had just played SE 634-636 (BattleSwirl.cs:20-28, 75-79). This is stock Memoria and would hang solo too.
- The two always-on NetSync relay threads. They do two allocations and one send() per frame and recv per frame (NetSyncRelay.cs:248-394). This is co-op-only exposure in old code, not s111-s117.

**Fix direction.** Do not change netsync yet. Calibrate first: the class of failure (a stopped world during the swirl's scene load) is established, but the thread holding the lock is not.

1) INSTRUMENT. Before the next two-machine run:
- Pre-arm `procdump -ma -h FF9.exe` on the host. Or tell the owner: if the host hangs, do NOT close it; use Task Manager > Create memory dump file first.
- Then read `~*kb`. The decisive frames are the main thread (expected: UnityPlayer GarbageCollectSharedAssets / mono GC_stop_world or the liveness pass) and whichever suspended thread holds the lock the main thread waits on.
- Cheap detectors to add to the sitting checklist: Application-log Event 1002 for FF9.exe, and an output_log tail that ends at 'UnloadTime' with no 'Unloading N unused Assets' line.

2) IF THE HOLDER IS A NETSYNC THREAD. Reduce exposure without touching wire semantics:
(a) NetSyncRelay.WriteLoop (NetSyncRelay.cs:260-267) and WriteBinaryFrame (:272-293): coalesce one tick's frames into a single reused buffer with one stream.Write per tick. That removes about 10 allocations and 4 syscalls per tick. Mirror the change in NetSyncSocket.WriteLoop (NetSyncSocket.cs:670-688).
(b) A scene-load quiesce. A static volatile deadline set on the main thread at the four LoadLevel/UnloadUnusedAssets seams: SceneDirector.ReplaceNow (SceneDirector.cs:80-84), ChangeScene (:396-402), ChangeSceneAsync (:457-460) and _Swirl (:558-566). Set it to now + ~750 ms, which stays under the guest's StaleMs 2000 (NetSyncSocket.cs:257) so the pos lane never goes stale. The writer honors it by sleeping. Never Stop() the transport and never block the main thread.

3) IF THE HOLDER IS SAXAUDIO'S XAUDIO2 CALLBACK THREAD. Stop entering managed code from it: SaXAudio.cs:82 / 213-217 should enqueue voice ids into a lock-free queue that the main thread drains. This is stock Memoria, outside netsync.

The guest side needs no fix for this bug: it released the lock, ramped out and kept redialing exactly as designed.

**Repro.** This can't be reproduced with the selftest role. In selftest, NetSyncClient.Update returns at NetSyncClient.cs:1180-1262, before the transport is created at :1265-1286, so there are no socket threads, and the socket threads are half of the suspect set.

It doesn't strictly need two machines. A solo stress run:
1. Set the desktop to Role=host with RelayUrl pointing at a local bridge (`ff9mapkit coop bridge`) and a throwaway ff9- code.
2. Run a scripted fake guest. Adapt ws_client_connect in tools/netsync-bridge/test_relay_roundtrip.py to join as role=guest and send v14 type-0 frames (magic 0xF9, version 14, 37-byte pos payload) at 30 Hz, so the host's reader and writer carry real traffic. An unpaired relay host is NOT equivalent: the relay doesn't read an unpaired socket (NetSyncRelay.cs:159-163).
3. With `procdump -ma -h FF9.exe` armed, drive many swirl loads through tools/harness/session.py: `warp` 250<->350 plus walking on 250 for random encounters (or `fight`), each one a [2/~97,0/0]+[2/1,4/big,0/0] load sequence.
4. A/B the same loop with [NetSync] Enabled=0 (no socket threads) and with SFX-heavy swirls, to separate the netsync culprit from the SaXAudio one.

It is a race, so expect many iterations. The hang is detected by Event 1002 plus an output_log ending at 'UnloadTime'. The two-machine sitting can't discriminate further without a dump, and the dump is the instrument that decides it.

### lane

I found no host-side hang in netsync. The encounter's scene change was not swallowed or held up: the host started it, and the whole process froze partway through the battle load.

**Evidence, verified from the install and the Windows event log:**

1. **Unity's log shows the swirl finished and the battle load began.** The desktop log (`output_log.txt`, identical to the live install copy, last written 10:38:43.389) shows each scene change as a set of "Unloading ..." blocks:
   - The 3 earlier battles: field→battle = SwirlScene, unload, Loading (2 files, ~97 assets), unload, BattleMap (2 files, 1 asset). Battle→field and field→field are 3 blocks each.
   - The 250→350 and 350→250 warps are the next two 3-block sets, ending at lines 323-327.
   - Lines 323-335 then show the encounter's SwirlScene load (4 files, 1029 assets), its unload (0, 0), and the start of the "Loading" load. The file ends at `UnloadTime: 0.571200 ms` on a clean line boundary. The "Unloading N unused Assets" line that every earlier transition printed next never appears.
   - That "Loading" load can only come from `SceneDirector.ChangeScene` (`SceneDirector.cs:394-402`, `Application.LoadLevel("Loading")`). It is reached only through BattleSwirl's `SceneDirector.ReplacePending` (`BattleSwirl.cs:58-61`) and then `_Fade`. So the swirl completed, its `ReplacePending` was accepted, the fade-out ran, and the battle load began.
2. **Windows recorded a real hang, not a crash.** Application log event 1002 "Application Hang" at 10:43:45, plus WER event 1001 AppHangB1 at 10:43:44 (signature P4 4b4f, P5 134217728): "FF9.exe ... stopped interacting with Windows and was closed". So the main thread stopped responding from about 10:38:43 until the owner closed the window. There is no crash folder.
3. **The host's network writer stopped too.** `Memoria.log` was last written at 10:38:36.57 (the ghost-spawned line). The laptop's 10:38:49 "the link has read dead for 3 s" means the host's position frames stopped arriving at about 10:38:44. That is the 2 s staleness limit (`NetSyncSocket.cs:257/401`) plus the 3 s grace (`NetSyncDialog.cs:50`). After that the laptop got zero bytes through three 75 s read-timeout cycles (`NetSyncRelay.cs:164`): 10:39:59, 10:41:16, 10:42:34. But the host's relay writer is its own background thread that re-sends the latest frames every 33 ms regardless of the main thread (`NetSyncRelay.cs:255-270`, collected at `NetSyncSocket.cs`). A hung main thread alone cannot silence it.

**What this rules out (verified in code).** A swallowed Replace (`SceneDirector.cs:519`, silent return when `IsFading`) or any netsync gate waiting forever would leave the game running. The window would still respond and the writer would keep the laptop's link alive. Neither happened. The four facts together (load stopped at the asset-unload step, AppHang, writer silent within about 1 s, nothing logged afterwards) point to every managed thread freezing at once. That fits a stop-the-world garbage collection or native lock that never released, inside Unity's Loading-scene load. This is inferred; a dump would confirm it.

**s111-s117 versus older code:**
- Only s112 runs in this window on the host. `SFX_Rush.cs:43-44` calls `NetSyncDiorama.SwirlFrames`, which returns the host's own setting because no diorama is booted (`NetSyncDiorama.cs:488-528`). `SFX_Rush.cs:104-114` calls `NoteSwirlDone`, which only records a tick and does not log on a host. Both completed, since the Loading load started.
- s111 and s113-s117 only run after the battle starts. The start hold and the 'battle intro' line come from `NoteOwnBattleStart` (`NetSyncBattle.cs:1161-1165`), which needs gMode 2/4 (`NetSyncBattle.cs:1429`) and was never reached.
- `SceneDirector`'s scene-change code is stock apart from one s33 `EffectiveFieldId` change in `_SetFadeMode`.

**Host warp then encounter.** The warps left nothing pending on the host:
- The intent is wire-only: `EmitFieldIntentIfHost` (`NetSyncClient.cs:2022-2042`), cleared on landing at `:1312-1313`.
- The debug-menu warp is a plain `SetNextMap` (`Ff9mkDebugMenu.cs:2155-2190`).
- The guest's "paired on the host's field -- reloading" kick is guest-only (`_role != "client"` gate, `NetSyncClient.cs:1940`).

I scanned the 50 captured logs with host-role transition intents (repo `.harness-runs`, all worktrees, `studies`). None ever went into a battle after a host warp, so this combination had not been tested before sitting A. Sitting A is the only two-machine capture on disk. Windows also shows one earlier FF9.exe hang on 2026-09-04 16:53, with a different signature (abaf).

**Side finding for the box-8 lane (verified, not the hang cause).** The host's 10:37:27 "control lane is live again" handback went to a laptop that had already left its diorama. The guest sends control frames whenever the host's battle lane is live and it is not in its own battle, whether or not a diorama is booted (`NetSyncBattle.cs:1269-1275`). So the host handed slot 1 back to a guest with no command menu.

**Fix direction.** No code fix for the freeze is justified until we have a stack, because the freeze happens in stock Unity scene-load code, not in any netsync path. Suggested order:

1. **Capture a dump at the next hang (operational, safe).** Before closing a hung FF9.exe: Task Manager > Details > FF9.exe > Create dump file, or run `procdump -ma -h FF9.exe` beforehand. Open it in WinDbg (`~*k`) and look at the main thread in mono GC / stop-world / asset unload / a render-thread wait, and at where the NetSync-relay and relay-write threads are parked.
2. **Add a hang canary (small, engine-only, no wire change).**
   - A background thread started from NetSyncClient.Ensure (`NetSyncClient.cs:487-500`), or a tiny new class, appends `tick + phase` to a small file every 250-500 ms using a preallocated buffer and no Unity API.
   - The main thread sets a static `phase` int at SceneDirector.ChangeScene before and after `LoadLevel("Loading")` and `LoadNextScene` (`SceneDirector.cs:394-402, 93-111`), and in `_Swirl` around `LoadLevel("SwirlScene")` (`SceneDirector.cs:556-569`).
   - If the canary freezes in lockstep with the main thread, the world stopped (a GC or native lock). If it keeps writing with the phase stuck, the main thread alone is blocked (render thread or driver).
3. **Only if the dump implicates the relay threads:** the mitigation seam is NetSyncRelay.WriteLoop / WriteBinaryFrame (`NetSyncRelay.cs:255-293`). Options are reusing one frame buffer instead of allocating 2 arrays per frame, or quiescing relay I/O while `SceneDirector.IsFading` / during ChangeScene. Do not ship either blind.
4. **Separate box-8 seam (verified defect, not the hang):** NetSyncBattle.Pump guest branch (`NetSyncBattle.cs:1269-1275`). Add `&& NetSyncDiorama.Booted` (or the diorama-live latch) to the condition for sending control frames, so a guest with no diorama cannot reclaim a held slot (host handback at 10:37:27).
5. **Latent hardening, not this incident:** BattleSwirl.cs:58-61 latches `_isReplaceCalled` even when SceneDirector.Replace silently returns because of `IsFading` (`SceneDirector.cs:519`). Re-try ReplacePending while `PendingNextScene` is non-empty and the scene is still SwirlScene.

**Repro.** The harness cannot reproduce the exact freeze solo. The selftest role returns before the relay transport exists (NetSyncClient.cs:1180 selftest branch returns; the socket is only created at :1265-1293), so selftest benches never run the relay threads that are present in the hang. bench lapse, dioboot/dioleave and warp verbs exercise managed paths that were verified not to be involved.

Best one-machine approximation, a soak:
1. Desktop with Role=host and RelayUrl ws://127.0.0.1:49201, the local bridge/relay up (`coop host`), and a scripted fake guest that connects to /sess/<code>?role=guest and streams position frames at 30 Hz, so the host's reader and writer carry real traffic.
2. Use tools/play.py or session.py to loop: warp to 250 (or a debug Warp to 350 and back first, to copy sitting A), walk until an encounter, win or flee, repeat 100+ times.
3. Run a control soak with [Netsync] Enabled=0.
4. Watch for a stall: output_log stopping between 'UnloadTime' and 'Unloading N unused Assets', or a new Application Hang event 1002 for FF9.exe.

A faithful repro needs the two-machine topology only because a real guest is the easiest traffic source; the freeze itself is host-local. Whatever setup is used, the decisive artifact is a dump taken while the window is hung.

### lane

CUT-REJOIN LANE: the laptop log from 10:37:07 to 10:38:23, explained from code. Everything below was read-only; nothing was built or deployed.

WHAT HAPPENED (code verified unless marked "inferred")
1. 10:37:09 "diorama LEAVE requested". The watcher left because it decided the fight was over. It did not think the link was down. NetSyncClient.cs:1631 reads `Boolean transportUp = _socket != null && _socket.IsConnected;`, and :1640-1644 says `else if (transportUp) { shouldLeave = true; // stale + link UP -> the fight is over`. The battle lane went stale 2 s after the last host sample (NetSyncBattle.cs:77 `StaleMs = 2000`, keyed on seq at :1256-1268). IsConnected stayed TRUE because the game's websocket goes to the local bridge, and the bridge never closes it when its upstream dies. netsync_bridge.py:18-25 says "the bridge closes ONLY the upstream socket, redials it"; it closes the game hop only after `UPSTREAM_REDIAL_HARD_CAP = 45.0` (:86). The log proves this: the laptop has no "relay disconnected" line between 10:32:59 and 10:39:59 (NetSyncRelay.cs:178 logs one on every drop), and no "mid-battle link blip -- holding" line (NetSyncClient.cs:1653), so the s56 hold branch never ran. There is no 1 s predicate. The "~1 s after the cut" is the 2 s StaleMs seen through second-truncated timestamps. The host's "silent 8406 ms" at 10:37:16 puts the last guest frame at about 10:37:07.6-08.6.
   - So was the local ws closed by the bridge? No.
2. The two "stock menu" lines. StockMenuTick lost the lane on the same frame: `why = "no live peer battle lane"` (NetSyncBattle.StockMenu.cs:1143). "torn down" is ForceDisarm (NetSyncDiorama.cs:1044).
3. "watcher-leave settled (nonce 3) -- the same fight won't re-boot on reconnect". The leave at :1694-1698 set `_dioramaWatcherLeftFinal = true`, and teardown stamps `_dioramaSkipNonce = _dioramaWireNonce` (:1557-1563).
   - Why the rule exists: s56 (README.md:76) added it against "battles start twice". Before s56, the 2 s horizon left mid-blip and the same live nonce re-booted on reconnect.
4. "state-mirror skipped ... no host snapshot". The warm return's field load found the type-5 lane stale (NetSyncClient.cs:561-569).
5. 10:37:12, two separate 3 s timers, both started when the position lane went stale (NetSyncSocket.cs:401, about 2 s after the last frame, so about 5 s after the last frame):
   - "dialogue lock released -- the link has read dead for 3 s" is the s96/F3.2 dialogue lock: `LinkGraceMs = 3000` (NetSyncDialog.cs:50; NetSyncClient.cs:2667-2671).
   - "session ended -> reloading own autosave" is the s37 exit ramp. `sessionLive = ... IsConnected && GetRemote().Valid` (:1169-1170, the peer-alive law). `ExitRampDebounceMs = 3000` (:470) arms it at :1175-1176. It fired once the field had settled (:1078-1133: the s55 deferral plus F3.3's DIO-1 BattleReturnInFlight check), then ran ExitMirrorToOwnSave (NetSyncState.cs:192-221).
   - What the ramp protects: the guest must never be left playing the host's story at the host's location (NetSyncState.cs:182-191). Continue is kept pristine because the save gates hold until the ramp fires.
   - The ramp also cleared `_storyMirroring` and `NetSyncParty.Clear()` (:1124-1129). "Map 250 / Scenario counter 0" is the laptop's own autosave.
6. 10:37:28 "session on". The position lane was fresh again (the host handed the slot back at 10:37:27). The host fought nonce 3 until 10:38:13, but the watcher returned at :1709 (`if (nonce == _dioramaSkipNonce) return;`).
   - The s105 late-join decline (:1717-1726; `IsTerminal`, NetSyncEnd.cs:716) would NOT have declined: the host was still FIGHTING.
   - Even without the skip stamp, a re-boot would have seated the guest's own party (NetSyncDiorama.cs:1538 gates on `NetSyncParty.MirrorActive`), and the stock menu would have refused to own the slots: "the party mirror is not active" (StockMenu.cs:1140-1141).
7. 10:38:14-22 are only the end-block trail (NetSyncEnd.NotePeer). 10:38:22 "paired ... reloading it once" is SameFieldKickTick (:1932-1956). It was re-armed by the ramp and became possible only once the host was back on field 250, which re-armed the mirror at 10:38:23.

WHAT BOX A6 EXPECTED. R3-DESIGN.md:1450 says "the laptop's blip-hold rides the cut", i.e. the s56 hold. That hold has been dead on the bridge topology since it shipped (inferred). The bridge hop decoupling (96cb9e0, 2026-07-23 17:25) landed about an hour before s56 was captured (2d3514b03, 18:27). s56's premise was "IsConnected false for the ~2.5-3s reconnect cycle". Its acceptance run ("no drops so far") never exercised a drop.

WHAT s111-s117 CHANGED HERE. Only s111's hostFlags/WireIntro (:1579-1580, :1784) and s114's NoteBootWatch/NoteBootFail (:1440, :1610-1614, :1775-1790). None of them touched the hold predicate, the skip stamp, the exit ramp or LinkGraceMs; the defect is s37/s56 code. s114's start hold is final per battle (NetSyncBattle.cs:2975-2976 `if (h.Released) return HoldNothing;`), so a rejoin can never re-freeze the host.

THE SECOND END AT 10:38:49 (out-of-lane pointer). The host's 30 Hz background writer (NetSyncRelay.cs:255-268, independent of the main thread) also went silent. The laptop's loopback then read zero bytes for 75 s, three times (`ReceiveTimeout = 75000`, :164). The host's log has no relay line. So this is a host-wide stall at the encounter, not something the guest fed it (inferred). The host reads guest control and command lanes only inside its own battle (NetSyncBattle.cs:1222-1238), and it never got there: no "battle intro" line.

**Fix direction.** Four changes, in this order. Each is a separate patch and a separate in-game check.

(A) THE HOLD: classify a stale lane by what the host said, not by IsConnected. Seam: NetSyncClient.cs:1622-1664.
- Delete the `transportUp` test at :1631.
- While `live`, latch whether the booted nonce's end block is terminal (TryGetPeerEnd, NetSyncBattle.cs:1911; NetSyncEnd.IsTerminal :716). TryGetPeerEnd reads only the live view, which is nulled at :1288-1292, so the latch must be taken while live.
- When the lane is stale, the fight is genuinely over (leave final, as today) only if: the latched end block was terminal, OR `_socket.GetRemote().Valid && rs.Field > 0 && rs.Field != 65535` (the host is back on a field; it sends field 0 throughout its battle, :1302).
- Every other stale case is a HOLD: the reconciler already freezes at :1849-1851. Log once (:1653) and keep DioramaBlipHoldMs = 8000 (:449, "several seconds").
- This also stops today's leave-with-skip when the host merely alt-tabs (seq stale, position re-sent).

(B) LAPSE LEAVE, NOT A FINAL LEAVE. Seams: :1693-1698 and teardown :1546-1565.
- When the hold reaches its cap, call Leave() with `_dioramaWatcherLeftFinal = false`. The existing non-final teardown branch then stamps no skip.
- Record `_dioramaRejoinNonce = _dioramaWireNonce` with a per-nonce budget of 2.
- Genuine-over and new-nonce leaves keep the s56 skip stamp, so 'battles start twice' stays closed: short blips no longer leave at all.

(C) REJOIN BOOT. Seam: :1703-1803, the existing late-boot path (the same path A5 uses, R3-DESIGN.md:1449; the reconciler's late-join law is at NetSyncDiorama.cs:1875-1878).
- For `nonce == _dioramaRejoinNonce`, keep DeclineLateJoin (:1717-1726) first, then require:
  - IsMirroringStory and !_exitRampPending;
  - the peer alive, and the lane continuously live for RejoinStableMs = 1500;
  - the field settled, using the exit ramp's idiom (GetUserControl && FieldHUD && !NetSyncDiorama.BattleReturnInFlight, :1104-1105);
  - budget > 0.
- Then refresh `NetSyncParty.ParseSections(_socket.GetRemoteState())` (precedent: :3604-3605) and call `BootFromWire(..., wireIntro: 1)` (force skip: the fight is mid-way).
- Log one 'diorama REJOIN boot (nonce N, attempt k)' line. When the budget is spent, stamp the skip and log one line.
- The containment law needs nothing new: a rejoin is an ordinary Boot, so Arm/Snapshot runs before the scene (NetSyncDiorama.cs:759-774) and IsOver is never set (:653-657).
- The host side is already fine: the start hold is final (NetSyncBattle.cs:2975-2976), and G3 hands the slot back on the live control lane (:1016-1063).
  - Optional: hand back only once the guest's s114 report reads LIVE for that nonce.

(D) SESSION WINDOW. Seams: :470 and :1169-1177.
- Change ExitRampDebounceMs 3000 to 30000 (rename it SessionGraceMs). The ramp then ends the session about 32 s after the last frame.
- Why 30 s:
  - it covers the ~20 s restore observed for a 6 s cut;
  - it stays under the bridge's 45 s hard cap and the relay's 60 s rejoin grace (main.go:42), so the old pair can still re-join;
  - it is safe for the disk: IsMirroringStory and the save gates hold until the ramp fires (:598-605).
- Its cost: on a real host quit, the guest walks in the host's story without saving for about 30 s instead of about 5.
- Add `!NetSyncDiorama.Booted` to safeToLoad (:1085-1086).
- Keep the immediate arm for a deliberate config change (:941, :965). Keep LinkGraceMs 3000 for the dialogue lock only (NetSyncDialog.cs:50), now decoupled from the ramp.
- Show a 'reconnecting (Ns)' overlay keyed on peer-alive. OvlConnecting at :1409 keys on IsConnected, which never trips behind the bridge.

FOLLOW-UP with the same root cause: sweep the other IsConnected-as-link-down sites (:1385-1386 ghost grace, :1336-1349, :550) onto one PeerAlive predicate.

RISKS AND HOW EACH IS BOUNDED
- Re-boot loops on a flapping link: RejoinStableMs, the budget, and the existing 1 s rate limit (:1761).
- Double boots: rejoin only when !Booted and !LeaveRequestedRecently; Boot's own IsFading gate (NetSyncDiorama.cs:743-757); the BattleReturnInFlight settle.
- Ramp vs boot race: the !_exitRampPending gate plus the ramp's !Booted check. Once pending, the ramp is not cancelled by the link returning (:1171).
- Rejoin after the session already ended: declined, because the party mirror is off (NetSyncDiorama.cs:1538).
- Finished fights: declined by s105.
- Picks committed in the first ~2 s of a cut are lost, because the bridge drops frames while upstream is down (netsync_bridge.py:24-25). The host's hand-back and the mirror's fresh Ready bits cover it.

**Repro.** THE WATCHER CANNOT BE BENCHED IN SELFTEST TODAY. The selftest branch (NetSyncClient.cs:1180-1263) returns before DioramaTick (:1436), and the existing levers do not touch the guest watcher: `bench lapse` silences the host-side control lane, and `netsync stale` is the dialogue-lock DebugLinkDead. So bench it solo in three layers.

(1) PURE STEP (no game). Extract DioramaWatchStep (inputs: live, nonce, bootedNonce, terminal-latched, peerAlive, hostField, staleSinceMs, liveSinceMs, settled, mirroring, rampPending, budget; outputs: NOTHING / HOLD / LEAVE_FINAL / LEAVE_LAPSE / REJOIN_BOOT / DECLINE) and an ExitRampStep.
- Table-test them in SelfTest, in the same style as StartHoldStep in ControlSelfTest and DeclineLateJoin in NetSyncEnd.SelfTest.
- Mirror them in tools/harness/battlewire.py with pytest, the same way chase_step and inject_verdict are mirrored.
- The calibrating red row is sitting A: IsConnected=1, position stale, battle stale, host field 0, not terminal. Today's code answers LEAVE_FINAL; the fix must answer HOLD.
- Further rows: held 8001 ms gives LEAVE_LAPSE with no skip; live, the same nonce and stable for 1500 ms gives REJOIN_BOOT; live and terminal gives DECLINE; dead for 30001 ms gives the ramp pending.

(2) IN-GAME SOLO LEVER (a small engine bench). Run the new step in the selftest branch against a `dioboot <scene> [pattern] wire` diorama (s111 stamps a wire nonce through the real ParseView), plus a new named bench op `bench peer stale <ms> battle|all` / `bench peer back`.
- Pass: no LEAVE before the 8 s cap; a 'lapse' line with no 'watcher-leave settled'; then 'REJOIN boot' and the ready mirror SERVING again.
- `battle` alone with the host field > 0 gives LEAVE_FINAL.

(3) REAL TRANSPORT, ONE MACHINE (reproduces sitting A's topology exactly). Run the laptop-role game (Role client) against `ff9mapkit coop bridge --relay ws://127.0.0.1:7777`, a local jawn-relay (`go run studies/battle-coop/relay/main.go`), and a Python fake host that sends 30 Hz type-0 frames (field 250, then 0), a type-5 snapshot and seq-advancing type-1 boot frames (composed with battlewire.py). Kill the relay process for 6 s and then for 20 s: the bridge redials and the game hop stays up. Today this reproduces the immediate leave and 'watcher-leave settled'.

TWO-MACHINE CONFIRMATION, still needed for feel and the hand-back. Redo the sitting with the host in Wait:
- a 6 s cut: the scene holds, there is no LEAVE, and it resumes on the same nonce;
- a ~20 s cut: hold, lapse leave, then a rejoin boot with intro skip; the host's party is seated, the stock menu resumes, and the host hands the slot back;
- a 40 s cut: the session ends at about 32 s and the guest reloads its own autosave;
- a cut spanning the host's victory: 'late join DECLINED'.
Grab both bridge console logs as well as Memoria.log, because they time the restore.

### lane

BOX 4 is INTENDED, not an accident and not an s111-s117 regression. A following guest's field main menu has been blocked on purpose since s38-netsync-spectator-field.patch (2026-07-15). The owner chose Road A, "A first, then B", in studies/battle-coop/inventory-authority.md:255-258, and it was two-machine proven then ("menus refuse incl. both Alt lanes").

The seat [verified in code], C:\gd\FFIX\Memoria\Assembly-CSharp\Global\UI\UIKey\UIKeyTrigger.cs:694-701:
  if (...IsInputDown(Control.Menu) || keyCommand == Control.Menu) { keyCommand = Control.None; ...
  else if (PersistenSingleton<UIManager>.Instance.IsMenuControlEnable && !Memoria.Netsync.NetSyncClient.IsMirroringStory) // co-op: a FOLLOWING guest has no menu [ff9mapkit netsync spectator-field]
      sceneFromState.OnKeyMenu(activeButton);
  return true; }
The same conjunct appears at :867 (the dialog-path Menu key), :510 (Alt+F2 party) and :552 (Alt+F5/F9 save/load). The rationale comment at :504-508 reads "a FOLLOWING guest's menu shows the guest's OWN bag/party while every field script around it answers from the HOST's mirrored one". That rationale still holds today: NetSyncParty.cs:36-39 says "Menus and the guest's real FF9.party/item state are NEVER touched". The predicate, NetSyncClient.cs:602-605, is `_instance != null && _instance._storyMirroring`.

Log fit [verified]: the laptop's mirror was ARMED from 10:33:00 to 10:37:12 (laptop-Memoria.log:35, :166) and again from 10:38:23 to 10:38:49 (:177, :188). That covers every co-op free-roam window, including the 70 s gap on 250 between 10:35:04 and 10:36:14.

The refusal is SILENT [verified]. The :699 branch simply skips OnKeyMenu: no SFX 102 (unlike Alt+F2/F5/F9 at :510-513 and :552-555), no log line, no overlay. This is why it reads as a bug.

Not other netsync locks [verified]:
- No netsync code writes IsMenuControlEnable; the only writers are stock (SceneDirector, DoEventCode MENUON/MENUOFF :2306/:2314, FieldHUD:397, PauseUI, QuitUI and others).
- s99 FilterScriptButtons/HostOwnedKeys (NetSyncField.cs:94-131, :169-170) filters only script B_KEYON/B_KEY reads (EBin.cs:1104, :1135). Its control-on mask strips Confirm|Special|Select, never Menu.
- SuppressLocalDialogInput (s84/s96) sits only on the dialog path (UIKeyTrigger.cs:830). Free roam takes the main branch, since `!Dialogs.Activate` at :637.
- None of s111-s117 touches UIKeyTrigger.cs. Their file lists cover only NetSyncBattle/StockMenu/Diorama/Client/End, HarnessAgent, Ff9mkDebugMenu, HonoluluBattleMain, battle.cs, SFX_Rush and BattleHUD.Public. s113 only mentions UIKeyTrigger in comments.

The real defect is in the R3 DESIGN, not the code [verified]. Box A5 (R3-DESIGN.md:1449, "The guest is in its own main menu at the host's encounter") has a precondition that cannot be reached on a mirroring guest. The BUSY row at R3-DESIGN.md:270, "(main menu, shop, pause, card game)", and the strings at NetSyncClient.cs:1809, NetSyncBattle.cs:2785 and :3165 ("a menu, a shop, a pause") list states that are all refused:
- main menu: s38 at :699
- shop/save/name script menus: s44 F1 at EventEngine.DoEventCode.cs:2327-2331
- party UI: F3.2 MISC-07 at :2356-2360
- quad/talk starts: the F1 CheckNPCInput/CheckQuadInput gates

Pause is the only durable non-FieldHUD state a mirroring guest can reach. UIKeyTrigger.cs:681-686 gates it only on IsPauseControlEnable, and FieldHUD.OnKeyPause (:265-273) goes through OnKeyPauseAfterHide (:415-418) to UIState.Pause. That makes uiFree false at NetSyncClient.cs:1832-1833, so the report reads BUSY (NetSyncBattle.cs:2678-2679). The desktop log never shows a "busy" not-armed line, so A5 was never exercised.

Related, already known: the same :699 read also swallows the in-battle Menu key on the guest's diorama, i.e. B4-B5 stage 13b's Menu-key rotation (B4-B5-DESIGN.md:845). The guest's in-battle AccessMenu is greyed separately by s102 (owner decision 2, laptop log :53/:102/:152), so "the guest has no main menu" is consistent policy across field and battle.

**Fix direction.** No correctness fix is needed: the gate is intended (s38 / Road A). Three minimal, safe follow-ups, plus one owner decision:

(1) DOC fix, zero risk, do first.
- Re-spec R3-DESIGN.md:1449 A5 as: "The guest is PAUSED (its Pause key; the laptop binds Backspace) at the host's encounter". Pass: host "not armed -- the guest is busy", laptop "-> BUSY", the laptop boots on unpause and catches up.
- Correct the BUSY row at R3-DESIGN.md:270 to "a pause -- the main menu, shops, party and quad are refused to a mirroring guest (s38 UIKeyTrigger:699, s44 DoEventCode:2327, F3.2 :2356)".
- Fix the same wording in the strings at NetSyncClient.cs:1809, NetSyncBattle.cs:2785 and :3165 at the next touch (cosmetic; no behaviour).

(2) UX fix, guest-side, inert on vanilla (IsMirroringStory is false there). Make the refusal audible and logged so it stops reading as a bug. At UIKeyTrigger.cs:699 add a third branch after the existing one:
  else if (PersistenSingleton<UIManager>.Instance.IsMenuControlEnable && Memoria.Netsync.NetSyncClient.IsMirroringStory && (UIManager.Instance.State == UIManager.UIState.FieldHUD || UIManager.Instance.State == UIManager.UIState.WorldHUD)) { FF9Sfx.FF9SFX_Play(102); Memoria.Netsync.NetSyncField.DeclineOnce("main menu"); }
- Scope it to FieldHUD/WorldHUD so the guest's diorama (BattleHUD) Menu key does not buzz. That is the stage-13b Menu-key-rotation seat (B4-B5-DESIGN.md:845), which must stay a separate decision.
- Leave :867 alone (the dialog path).
- Optionally add one overlay line naming the way back to one's own menu (the session ending, or ~ > Leave).
- Needs a DLL rebuild, so batch it with the next round, not alone.

(3) R3 test sheet: mark A5 "not run (precondition unreachable)", not failed.

(4) OWNER DECISION, only if the guest should have a menu while following (a "Road B-lite"; this is a policy change, not a fix). Facts the owner needs:
- The guest's main menu reads the GUEST's real FF9.party/FF9.item (NetSyncParty.cs:36-39). So Item/Ability/Equip/Status/Order/Card/Party would show the guest's own save's characters, bag and gil, not the host's party that the diorama seats and the field scripts answer from (the s38 "two worlds" problem).
- Writes there (using a Potion, equipping, setting an SA, reordering) land on the guest's real arrays. They are session-scoped and discarded: save is blocked at SaveLoadUI.cs:154 and EventEngine.cs:693, and the exit ramp reloads the autosave. So they are confusing but not corrupting. The real answer for those entries is Road B (push the host's party/bag into the guest's display, inventory-authority.md:243-247).
- Candidates for a read-only or guest-local subset:
  - Config. It is the guest's own machine, but whether settings persist outside the save is UNVERIFIED.
  - Journal (MainMenuUI.cs:216-220). INFERRED: it reads gEventGlobal, so while mirroring it would show the HOST's story, which may be desirable.
- Seam if chosen: replace the bare IsMirroringStory at UIKeyTrigger.cs:699 with a predicate that admits the main menu on FieldHUD, then grey the disallowed entries in MainMenuUI.IsSubMenuEnabled (the MainMenuUI.cs:73-74 colour pattern, like s102's greyed AccessMenu). Keep Alt+F2 (:510) and Alt+F5/F9 (:552) closed, and keep save closed.
- Side effects of a guest sitting in a menu (all already designed for):
  - BUSY: the host does not freeze; the guest boots late (s114).
  - The follow warp waits (NetSyncClient.cs:1893).
  - The same-field mirror kick waits (:1945).
  - INFERRED: a host talk may be missed past the F3.2 relay's 4 s TTL (F3.2-DESIGN.md:917).

**Repro.** It needs two machines, or two live client/host sessions; it cannot be reproduced solo with the harness:
- The gate reads bare NetSyncClient.IsMirroringStory. That flag is set only in ApplyStoryImpl, which requires _enabled && _followHost && role != host && _socket.IsConnected && a host TypeState snapshot (NetSyncClient.cs:549-577).
- Role=selftest has no socket, so it is structurally unreachable there (NetSyncField.cs:18-19; Ff9mkDebugMenu.cs:864-865).
- The F1 BenchGates lever feeds only NetSyncField.SpectatorField, not the bare IsMirroringStory that the s38 menu gates read.
- HarnessAgent.cs does not publish IsMirroringStory (no grep hit).

Two-machine repro (trivial): pair on 250 and wait for the laptop's "state-mirror ARMED". On FieldHUD press Menu (Triangle): nothing happens, with no SFX and no log. Alt+F2 gives SFX 102. Pause (Backspace) still opens.

To run A5 as intended next sitting: pause the laptop, then trigger the host's encounter. Expect laptop "start hold report: host battle nonce N -> BUSY" and host "start hold ... not armed -- the guest is busy" with no gauge freeze, then the laptop boots on unpause.

The offline proof is the code reading above: UIKeyTrigger.cs:694-701, plus `grep '^diff --git' memoria-patches/s11[1-7]-*.patch` showing no UIKeyTrigger.cs change this round.
