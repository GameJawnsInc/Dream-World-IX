# R3 action replay (s122-s126): audit of the design against the live stack

**What was audited.** `studies/battle-coop/R3-DESIGN.md` covers action replay in sections 3.3.1-3.3.6, 4, 5, 6.1, 6.7-6.11 and 7, plus its risk list. These were checked against two things:
- the live engine clone `C:\gd\FFIX\Memoria\Assembly-CSharp`, which is the deployed patch stack through s132;
- the repo harness.

The design was written on 2026-10-13 against s95-s110. Since then s111-s121, s131 and s132 have landed.

**How.** Seven audit lanes produced findings: s122, s123, s124, s125-s126, harness, cross-cutting and risks. Three independent verifiers checked each finding. Only findings that survived appear here. Refuted findings are listed once in section 5 so nobody argues them again.

**Plan order.** Unchanged. Action replay (s122-s126) is built first, then the guest's field model (s127-s130).

**Conventions.**
- Line numbers are live as of 2026-10-15.
- `NetSync*.cs` files are in `Memoria/Netsync/`. `HarnessAgent.cs` is in `Memoria/Harness/`.
- `UBS` means `Memoria/Battle/SFX/UnifiedBattleSequencer.cs`. `battle.cs` is `Global/battle/battle.cs`. `HonoluluBattleMain.cs` is `Global/Honolulu/`.
- Other stock file names (`btl_cmd.cs`, `btlseq.cs`, `btl_mot.cs`, `btl_util.cs`, `btl_vfx.cs`, `btl_stat.cs`, `btl_init.cs`, `CMD_DATA.cs`, `BTL_DATA.cs`, `SFX.cs`) are each unique in the clone.
- Short prefixes:
  - `test:` is `ff9mapkit/tests/test_harness_netsync.py`;
  - `design:` is `studies/battle-coop/R3-DESIGN.md`;
  - `fixes:` is `studies/battle-coop/R3-SITTING-A-FIXES.md`;
  - `fakegame.py`, `session.py`, `channel.py`, `battlewire.py` and `coop_peer.py` are under `tools/harness/`.
- "Tape bench" means the recorded-host replay (`coop_peer.py replay-host`, used by `coop_cut_hold.py`). The harness calls it T2.

---

## 1. Verdict

The mechanism is sound, but the design cannot be built as written. Four things block it outright:

1. **Patch numbering and stack order.** Group 2 keeps its reserved numbers s122-s130, but s131 and s132 were captured first.
   - The stack replayer and the pinned tests order patches by number (`tools/memoria_stack_replay.py:102-112`; test:1920-1923, :2212, :2474, :2680).
   - So an s122 captured on top of s132 would replay before s131. Its rewrite of the single-line AppendNetsync catch literal (HarnessAgent.cs:3255, which s131 also rewrote) would fail to apply.
2. **A name collision that does not compile.** The design's per-slot `_lastAppliedSeq[slot]` collides with the reconciler's existing scalar `private static UInt16 _lastAppliedSeq;` (NetSyncDiorama.cs:1816) in one non-partial static class (:56).
3. **A harness key shape that crashes the pinned key-law test.** `actbench` keyed on `netsync.battle.act` fails the unpack `sub, leaf = path.split(".", 1)` at test:2049.
4. **A false premise about how ends present.** The design says W3 plus "BattleTrailingLoop's wait on SFX.IsRunning()" covers flee and defeat (design:765-766, :1029-1030). In live code that wait (battle.cs:291) exists only in PHASE_MENU_OFF.
   - PresentClose, PresentDefeat and s117's no-settle annihilation write PHASE_CLOSE or PHASE_DEFEAT directly and fade at once (NetSyncDiorama.cs:2729-2731, :2741-2743, :2749-2751; battle.cs:151-176).
   - s115's per-unit run-away runs every frame regardless of running actions (battle.cs:332-369).
   - s124's held kills also make s117's `AllPlayersDown` read a dying player as standing (NetSyncDiorama.cs:2609; NetSyncEnd.cs:394, :408-411).

The design also predates hold-through. s119, s120 and s132 keep a booted diorama alive through up to 40 s of host silence, and on a short cut the host's queued type-6 frames arrive afterwards as a backlog. The design gives no age bound for a START, does not say which clock its timers count, and does not say where the guest reads host bit 5.

**What must change first, in order:**
1. The owner decides group 2's numbering (section 3.1). This must happen before any group-2 patch is captured.
2. Rename the per-slot seq array.
3. Re-key `actbench` and make the tests' sub-object descent path-keyed.
4. Rewrite the end-presentation contract: release held life changes at injection, hold the run-away while replays act, and skip the per-unit restore after an injection.
5. Specify a battle-time clock, a per-boot bit-5 latch, a two-step drain with a backlog decline rule, and an ActTick-owned trance resolver.

Everything else is an amendment the builder can make while building the patch it belongs to.

---

## 2. Build briefs

### 2.1 s122: host STARTs, ENDs and the impact extension

#### Live line map

| Hook site | Design cites | Live today |
|---|---|---|
| Type-1 header flags (SampleOwnBattle) | NetSyncBattle.cs:1109-1117 | NetSyncBattle.cs:1596 (method), :1624-1645 (flags built), :1659 `bw.Write(flags);`, :1726 `_lastSampleFlags = flags;` |
| Header bit constants | :118 (bit 1) | CapCommandPhaseGated :130; the others at :162-163, :236. Bit 5 (0x20) is unused. |
| Header readers | ParseView :1422-1424; StockMenu.cs:1139 | ParseView HostCaps :1951-1953. Bit-1 test at NetSyncBattle.StockMenu.cs:1147. s111 WireIntro reads bits 2-3 (`hostFlags = view.HostCaps;` NetSyncBattle.cs:2358, passed at NetSyncClient.cs:2039). |
| QueueActionFrame | :1642-1676 | :2134-2213. Gate :2136-2141 (Enabled, !Booted, !isDebug). Flags :2167-2172. `new Byte[46]` :2174. Writer :2175-2195. Bail when both slots are 0xFF: :2154-2155. |
| Drop-oldest enqueue (becomes EnqueueActionPayload) | :1665-1675 | :2197-2207, with a verbatim copy in QueueStatFrame :2267-2277. `ActionBufferCap = 64` :116. |
| Stat-tick frame | not cited | QueueStatFrame :2224. `flags |= 128` :2242. 46 bytes :2244. Called from btl2d.cs:116. |
| Type-6 layout comment | :1567-1569 | :2099-2101 |
| PeerAction flag bits | :1570-1576 | :2117-2124. Bits 0, 1, 4, 5, 6, 7 are used, so bits 2-3 are free. |
| TryParseAction | :1771-1805 | :2303-2338. `Length < 46` is rejected at :2306; a longer tail is ignored. |
| ResolveWireSlot | :1756-1767 | :2288-2299. Returns 0xFF on an exception (a null actor throws at :2292) or on no single-bit match. |
| Pump rising edge | 3.3.2 | :1299-1306 (`_battleNonce++` :1304, NoteOwnBattleStart :1306, method :710-735). Socket flush :1336-1341. Not-in-battle clear :1356-1359. |
| Selftest loopback (ActLoopAudit home) | 3.3.2 | :1510-1527 (`_loopActions` :1514-1519, "codec drift" log :1523-1527) |
| START site, CommandEngine | btl_cmd.cs:624 | btl_cmd.cs:624 holds (`TriggerOnBattleAct` :623). Player stance gate :586-595 (condition :588). |
| Failed-inspection path (no START) | btl_cmd.cs:572-575, :653-662 | :571-577 (IDLE :576); :652-659 (ReqFinishCommand :655); DONE set :1280; FinishCommand :661-662; list removal :1396 |
| START site, StartBtlSeq | btlseq.cs | btlseq.cs:90-113. Null checks :98-99, regist :104, unconditional cmd[0] overwrite :100-107, Execute :109-113. |
| SelectCommandVfx (Describe mirrors it) | btl_vfx.cs:106-182 | Holds. Load retry :114-119, Beatrix predicate :120-124, enemy :131-135, player :138-143, Defend :145-154 and :177. |
| BattleSubSystem runs Loop | battle.cs:575 | battle.cs:577-587, `Loop()` at :584 |
| Harness battles clear isDebug | Ff9mkDebugMenu.cs:537 | Global/UI/UIKey/Ff9mkDebugMenu.cs:540 |
| Harness protocol stays 5 | HarnessAgent.cs:131 | HarnessAgent.cs:217 |
| AppendNetsync catch literal | HarnessAgent.cs:2961 | AppendNetsync :3186-3259; catch :3253-3257. The literal is :3255, a single line in two parts around `NetsyncF3Retired` (const :4684). The `battle` object is in the second part. AppendNetsyncBattle starts at :3774. |
| `bbench caps` feed | StockMenu.cs:1857-1866 | NetSyncBattle.StockMenu.cs:1905-1915 |
| HarnessReleaseBench | NetSyncBattle.cs:2547-2575 | NetSyncBattle.cs:4077-4144, called from NetSyncClient.cs:4661 |
| hostgates re-pin | test:2758 | test:2918-2935. The mask already reads `(st.coop_host_caps & ~0x3C) == 0` at :2932. |

#### Amendments

1. **Calibration baseline.** In 6.7, "On s117: the act probe fails closed" (design:1265) should read "On s132". Fix the same stale label in box B13 (design:1486) and B19 (design:1497).
   - What goes red does not change: no `act` key, `actbench` verb or `act.host` exists anywhere under `Memoria/Netsync` or `Memoria/Harness`.
   - Sections 6.1 (design:1131) and 4 (design:996-997) say "the DLL deployed before the patch", which is generic and still correct.
   - Add `coop_handback_live.py` and `coop_cut_hold.py` to the 6.1 regression set (design:1138-1143). They prove s118-s132 (memoria-patches/README rows s118-s132).

2. **Update the header-reader statement.** "[V] Header bits 2-7 are unread by every s110 reader" is out of date: since s111 the guest reads bits 2-3 (NetSyncBattle.cs:2358; NetSyncClient.cs:2039). Bit 5 is still free.

3. **Classify stat-tick frames.** QueueStatFrame sends 46-byte type-6 frames with flags bit 7 through the same `_actionsOut` (NetSyncBattle.cs:2224, :2242, :2244). The design never says whether they get the 0xA6 extension, or how ActLoopAudit and the tape count them.
   - Recommendation: they stay 46 bytes and are identified by bit 7.
   - Restate the 6.7 GREEN rule as "every non-stat impact is 52 bytes", and leave stat frames out of `noid_impacts`.
   - Ticks happen only if a Poison, Regen or Venom script runs Btl2dStatReq. Battle 67's command plan inflicts none of these, but a party already carrying Poison or Venom would, so without this rule the red would come and go.
   - The guest's STAT_TICK branch the design cites (NetSyncDiorama.cs:1810-1822, :1890-1905) is now :2205-2222 (`if (a.StatTick)` at :2211).

4. **EnqueueActionPayload must take over both drop-oldest copies**: :2197-2207 and :2267-2277. Stat ticks share the same 64-frame budget.

5. **Unresolvable actor.** The design never says what QueueActionStart does when the actor cannot be resolved. Stock tolerates a null caster (btl_cmd.cs:588, :622, :626).
   - The realistic case is not a null. It is the dummy `this.regist = new BTL_DATA();` from the CMD_DATA constructor (CMD_DATA.cs:9). Its btl_id is 0, so ResolveWireSlot returns 0xFF.
   - Rule: if the actor slot is 0xFF, send no START, allocate no actId and send no END. This mirrors `if (casterSlot == 0xFF && targetSlot == 0xFF) return;` at :2154-2155.
   - Allocate the id only after every `regist` dereference used for actorFlags (player, is_monster_transform, counter slot, cmd[3]) has succeeded, inside the swallow-all try.

6. **StartBtlSeq can take over an in-flight cmd[0].** btlseq.cs:100-107 overwrites cmd[0] unconditionally, and `info.Reset()` sets `mode = CMD_MODE_INSPECTION` (CMD_DATA.cs:102). Two consequences:
   - The CommandEngine id for that cmd[0] is moved to `_actScripted` and never gets an END.
   - On the next CommandEngine tick the reset cmd[0] is inspected again (btl_cmd.cs:570-585). If it passes, a second START fires at :624 and moves the CMD_DATA back into `_actIds` under a new id, while the scripted sequence's impacts are still running.
   - Rule: when QueueActionStart finds the CMD_DATA in `_actIds`, emit an END for the displaced id first and count it as `scripted_takeover`.
   - Handle a re-entry at :624 for a CMD_DATA that is in `_actScripted` explicitly; do not move it silently.
   - The trigger is a battle-script BTLSEQ (EventEngine.DoEventCode.cs:2993), run by ServiceEvents at battle.cs:179. This is latent on battle 67 and real for scripted bosses.

7. **Define `no_end`.** The design only names it (design:1068, :1255). Define it as counted at NoteOwnBattleEnd, excluding scripted STARTs (actorFlags b3, which are never ENDed by design: design:577). Count STARTs that are still open at a mid-battle `NetSyncBattle.Reset` (NoteOwnBattleEnd at :678, `_wasInBattle = false` at :648) or at a mid-action teardown (OnDestroy, HonoluluBattleMain.cs:880) separately as `cut`.
   - A normal end cannot orphan a CommandEngine START. The end switch runs only when `cur_cmd == null` (battle.cs:289-292, :311-318), and FinishCommand is the only list removal (btl_cmd.cs:1396).

8. **The rising-edge window.** A battle-script BTLSEQ can run in the same BattleMain call as InitEnemyData (battle.cs:178-179 after battle.cs:535 → btl_init.cs:95), which is before the pump's rising edge. Its START is flushed with the previous battle's nonce (the bump is at :1304), so the guest drops it at NetSyncDiorama.cs:2158. NoteOwnBattleStart then clears its id, so its impacts carry id 0.
   - Recommendation: QueueActionStart declines while `!_wasInBattle` and counts the decline.
   - Severity is low. Whether any stock script fires 0xE5 on its first tick is unverified.

9. **Capacity.** START and END turn k impacts into k+2 frames for a CommandEngine action, and k+1 for a scripted one. The three drop-oldest buffers are:
   - host `_actionsOut`: 64, flushed every Pump. It logs once per battle (flag :118, re-armed :1305, :1486, :676).
   - socket out-queue: `MaxQueuedActions = 64` (NetSyncSocket.cs:259, :287-302). It logs once per transport object (`_actionDropLogged` :268, never reset).
   - guest in-queue: :370-374. It drops silently, with no log and no counter.

   For s122, add `dropped` to `act.host` and keep 64. Steady state fits, because WriteLoop drains every 33 ms (NetSyncSocket.cs:672-685). Inbound sizing and the inbound counter belong to s123 (see section 3.3).

10. **DescribeCommandVfx keying.** Write it as a pure mirror placed next to SelectCommandVfx in btl_vfx.cs.
    - Report kind 1 when `aa.Info.VfxAction != null` (it is loaded eagerly at BTL_SCENE.cs:157-168, after ApplyBattlePatch at :156), or when the Beatrix predicate at btl_vfx.cs:120-124 holds. Evaluate that predicate; do not assign.
    - Never key kind 1 on `SequenceFile` alone. A file that failed to load must report kind 2, as the real path does at :131-135.
    - This supersedes the s122 lane's D1 suggestion to key on `SequenceFile` (see section 5, s122-G4).

11. **Constants pinning.** Add a new per-round table (for example `CS_ACTION_CONSTANTS`) with its own test, following CS_OWN_CONSTANTS (battlewire.py:2022) and CS_ADOPT_CONSTANTS (:2269, test:6510-6512). Do not append to CS_BATTLE_CONSTANTS (battlewire.py:1384-1397).
    - Decide whether START 0x04, END 0x08, the 0xA6 tag, fmt 1, extLen 3/27 and kinds 1/2/3 become named C# constants. Today's type-6 flags are literals (NetSyncBattle.cs:2168-2172).
    - Leaving them unpinned turns nothing red: the NetSyncBattle checks run one way only (test:3209-3214).

12. **Catch-literal placement.** The `act.host` sentinels go inside the `battle` object in the second part of HarnessAgent.cs:3255, in the order AppendNetsyncBattle writes them.
    - The line must stay one line made of exactly two literals around `.Append(NetsyncF3Retired)`. Tests assert this: `_literals` at test:95, :854 and :6675; the append at :93 and :853. Edit the second literal in place, as s131's `expired` re-pin did (test:6669-6689).

13. **Sub-verb capability key.** Key `actbench` on `netsync.battle.act.host`, not `netsync.battle.act`.
    - test:2047-2049 computes `path = "act"` and its `sub, leaf = path.split(".", 1)` raises ValueError. Only s100 may key on the bare block (:2052).
    - Set `FG.NETSYNC_BATTLE_CAP_KEYS["actstart"] = {"act": ("host",)}`.
    - The accessor must return exactly False on a document without the block (test:2055), so use the `_nb_cap` pattern (channel.py:1115-1120).

14. **Tape egress.** 6.7's offline checks (`decode_action_legacy(START)` gives 0xFF/0xFF; every impact is 52 bytes) have no way to get the engine tape's bytes out. The keys publish only `tape{state, frames, starts, ms}`.
    - Option one: add an egress, such as a hex field in the `actbench tape info` reply, or a log line per frame (precedent: `netsync.battle.menu.ctl.hex`, HarnessAgent.cs:3689).
    - Option two: re-home those checks onto a host-role tape-bench recording. `coop_peer.py dump --type 6 --hex` already prints raw frame bytes (:2002-2003).

15. **The bench scene cannot pass as specified.** Battle 67 (BSC_EF_R007) is one enemy in both patterns. Group -1 picks between them 50/50: Goblin 33 HP or Fang 68 HP (HonoluluBattleMain.cs:394-410).
    - So "Fira's `tar` spans 2+ enemy bits" can never pass: CheckTargetCondition masks tar_id to living targets (btl_cmd.cs:1233-1238).
    - Use scene 306 (BSC_EF_R004) group 2 (Goblin + Fang) or group 4 (Fang ×2, 136 HP total) via `battle 306 <group>` (HarnessAgent.cs:856-870; session.py:7506-7531). battle_play.py:37 already uses 306.
    - s123 Leg C must then run `dioboot 306 <group>` so the replayed tape matches the booted formation.
    - There is no HP lever, so the six-command plan can still end early. Whether a seeded Vivi knows Fira is unverified.

#### Decisions

| # | Question | Recommendation |
|---|---|---|
| D1 | Where does QueueActionStart go: before SelectCommandVfx (the design) or after it? | Before, at btl_cmd.cs:624. It keeps FIFO order on both engines, including the old engine's synchronous Defend impact (btl_vfx.cs:177). Key Describe on VfxAction as in amendment 10. |
| D2 | Hand-written mirror, or a shared classifier extracted from SelectCommandVfx? | A mirror next to SelectCommandVfx. Add a selftest/bench check that compares each START's kind with the effectType of the action SelectCommandVfx added to runningActions in the same frame, so any drift shows up red. |
| D3 | Do stat ticks get the 0xA6 extension? | No (amendment 3). |
| D4 | Should the 64-frame caps change for the extra traffic? | Not in s122. Add `act.host.dropped`. Inbound sizing and the inbound counter go in s123. |
| D5 | In-engine `actbench tape`, the tape bench's `.f9tape`, or both? | Both. Keep the in-engine tape for the solo GREEN. Teach `coop_peer` describe/dump to decode type 6 via battlewire (coop_peer.py:207-229; it only counts type 6 at :782-783), so tape-bench recordings of an s122 host are readable for s123. |
| D6 | When StartBtlSeq takes over an open CommandEngine START, END it first? | Yes (amendment 6). |
| D7 | Extension length field: u8 (the design) or u16 like 0xB5 (NetSyncEnd.cs:13)? | u8. Type-6 records are small and fixed-size. Document that this is a different convention from the 0xB5 trailer. |
| D8 | Calibration baseline and ladder position? | s132, with `actstart` placed after `grace40`. See section 3.1 for the numbering decision that decides how this is spelled. |

### 2.2 s123: guest replay

#### Live line map

| Hook site | Design cites | Live today |
|---|---|---|
| ActionTick intake | NetSyncDiorama.cs:1750-1761 | :2131-2171. `!_booted` drain-and-discard :2137-2141. Quiesce gates (Active, PHASE_NORMAL, LOAD_INITNPC/LOAD_INITCHR) :2142-2149. Drain loop :2150-2161. Nonce gate :2158. ApplyActionFrame call :2160 (its only caller). |
| ApplyActionFrame | (no line) | :2174. 0xFF slot tests :2179/:2185. Return :2191-2192. selfCast :2193. lethalT :2198, lethalC :2199, reviveT :2200, reviveC :2201. hiddenT/C :2202-2203. STAT_TICK :2205-2222. Figures :2232-2235. Swing :2243-2252. State :2257-2260. Gate stamps :2264-2273. ApplyActionState :2280-2308. CanPlayCosmeticMotion :2312-2318. |
| An old guest drops START/END | :1791-1792 | :2191-2192 |
| cmd_idle cleared only by netsync | :2155 | InjectEnd :2679. R9 refuses SetCommand at btl_cmd.cs:160. |
| The diorama boots with isDebug=true | :408 | :799 |
| Boot reset block / catch | not cited | :776-797 (`ResetIntro()` :797) / :922-943 |
| ForceDisarm (ActDiscardAll goes between AbortReplay and Disarm) | :612-646, `_booted=false` :616 | :1010-1046. `_booted=false` :1014. Resets :1016-1021. AbortReplay :1035. Disarm :1036. |
| OnDestroy → ForceDisarm → SFX.EndBattle | HonoluluBattleMain.cs:876-878 | HonoluluBattleMain.cs:878-880. SFX.cs:1669-1681 (UBS call :1677). UBS.cs:16-23. |
| LeaveFrom | :566-600 | :964-1000. Fade deferral :970-975. AbortReplay :978. SettleForReturn :983. Replace :994. |
| BootFromWire / intro latch | not cited | :680 / `_wireIntro` at :698-699 (`if (!_booted)` :698) |
| SteadyFrame / LatchLive (s114) | not cited | :357-366 / :370-380 |
| Trailing-loop SFX wait | battle.cs:291 | Holds, but only inside BattleTrailingLoop (:287-375), which is reached from PHASE_MENU_OFF (:132-138). See section 3.2. |
| BattleMainLoop / BattleSubSystem | battle.cs:244-245, :575 | :244-245 holds. BattleSubSystem :577-587, Loop :584. |
| Player MP_ATTACK swing (a paired impact skips it) | :1845-1852 | :2243-2252 (guard :2247, `animFrame = 0` :2250) |
| Call order | 3.3.3 | Transport, NetSyncClient.cs: Pump :1593, ActionTick :1600, DioramaTick :1603, NoteBootWatch :1607, ReconcileTick :1610, LiveTick :1614, EndTick :1619, StockMenuTick :1624 (SessionTick :1304). Selftest: SelfTestPump :1315, EndTick :1319, StockMenuTick :1323, LiveTick :1327. No ReconcileTick (comment :1321). |
| Match key = master unit | NetSyncBattle.cs:1756-1767 | Host ResolveWireSlot NetSyncBattle.cs:2288-2300. Guest ResolveWireUnit NetSyncDiorama.cs:1885-1911. |
| IsBtlUsingCommandMotion hook | btl_util.cs:96-105 | Holds. `out` overload :96-100 (stock filter at :98). Wrapper :102-105. Out caller: SetDefaultIdle btl_mot.cs:532. Wrapper callers: btl_mot.cs:301, :682; btl_cmd.cs:459. |
| IsBtlUsingCommand / IsBtlTargetOfCommand | 3.3.3 | out :74-78, wrapper :91-94 |
| IsBtlBusy / ANY_CURRENT | 3.3.3 | btl_util.cs:107-131 / :529. die_seq 5 DelCharacter gate btl_mot.cs:337 (call :350). |
| Death apply decision | 3.3.3 | DeathStatusScript.cs:29-34. Fallback btlseq.cs:339. SetDefaultIdle at clip end btlseq.cs:353. |
| ExecVfxCommand short-circuit | 3.3.3 | Head btl_cmd.cs:1521. Jump return :1534-1536. SysTrans case :1553-1573. |
| SetDefaultIdle | not cited | btl_mot.cs:532-562 (monster-transform deref :533, early return :559-562). IdleDefend :571-572. |
| Escape per-unit loop | not cited | battle.cs:332-369 (fade decrement :358, :368-369). proceedEnd gate :370-376. |
| End presentation | 3.3.3 | EndTick allDown :2609. InjectVerdict call :2627. InjectEnd :2660-2764. InjectRunAway :2771-2795. EndWatchdogs :2932-2983 (paused accounting :2939-2943, W1 :2944-2947, W2 :2958). |
| Reconciler | not cited | ApplyUnit :1924-2023. Horizon gate :1928-1935. Dead early return :1944-1949. Hide :1985-1999. Trance bit :2002-2006. Model check :2010-2015. ATB :2017-2022. ReconcileTick :1835-1871 (phase :1842-1844, no-peer :1849-1851, dedupe :1852-1854). KillUnit :2025-2032. |
| LoadSFX magic caster | not cited | UBS.cs:331-335. ExecuteSingleCode :181-185 (`RemoveFirst` :185). Loop try/catch :29-51. |

#### Amendments

1. **Hook the `out` overload of IsBtlUsingCommandMotion** (btl_util.cs:96-100), after the stock Find at :98, so the wrapper and every caller inherit it.
   - SetDefaultIdle reads the out overload at every non-looping clip end (btl_mot.cs:532, called from btlseq.cs:353). With a wrapper-only hook, a replayed player drops CMD → NORMAL at its first clip end, and an enemy drops to def_idle mid-sequence.
   - Return the replay's CMD_DATA as `cmdUsed`. Never return true with a null `cmdUsed`; :533 dereferences it for monster-transform units.
   - Honour stock's `includeSysCmd` / cmd_no filter (:98), so a SysTrans/SysPhantom/SysLastPhoenix replay does not hold MP_IDLE_CMD.
   - Design:742's "the out overloads stay stock" applies only to IsBtlUsingCommand and IsBtlTargetOfCommand. Say so explicitly.
   - This overrides the cross-cutting lane's D8 (wrapper only). The side effect that lane worried about (InjectRunAway's MP_ESCAPE deferred for an acting runner) is handled by amendment 6.

2. **The launch stance follows the host's gate.** ActLaunch applies MP_IDLE_CMD only when `!actor.is_monster_transform && (cmd_no <= RushAttack(52) || cmd_no > BoundaryUpperCheck(99))`, the same condition as btl_cmd.cs:588.
   - Without this, SysTrans (59), SysPhantom (57) and SysLastPhoenix (58) show a ready stance the host never shows.
   - The dead-caster exemption (design:659-661) would also stand a dead Eiko up for SysLastPhoenix. Stock rejects a dead caster only outside 56-99 (btl_cmd.cs:940).

3. **Latch host bit 5 once per boot.** Do not read it from the live view.
   - The live view is null whenever the lane is stale: `LivePeerView()` at NetSyncBattle.cs:3978-3982, and Pump's `_peerView = null` at :1446. Since s131 that is a continuous stretch, and s119/s120/s132 keep the diorama booted through it for up to 40 s.
   - Stamp the latch in BootFromWire next to `_wireIntro` (:698-699).
   - OR in bit 5 from any live view of the booted nonce, including the bench feed's `ParseView(BuildFeedFrame())` (NetSyncBattle.StockMenu.cs:1640-1646). Never clear it on a null view.
   - Reset it wherever ResetIntro runs: the boot block :797, Boot's catch :941, ForceDisarm :1021.
   - Only the death-attack grace and any caps-keyed old-host verdict need the latch. The s126 trance grace runs only with a live view (section 5, s125-s126-G5). Decide the old-host verdict per impact from the missing 0xA6 extension (design:623-625) rather than from caps.

4. **The stale rule needs a two-step drain.** Today ActionTick parses and applies each payload as it goes (:2151-2161), so a START is dispatched before a later END in the same drain is seen.
   - Specify ActStart so that it only registers the record and its id: impacts later in the same drain then pair as "queued". ActHostEnd marks a record that has not yet launched as stale. ActTick launches the non-stale records; it already runs straight after ActionTick (design:780-781).
   - The selftest bench inbox (ActionTickBench) must apply the same PHASE_NORMAL/load gates so it models the transport path.

5. **Backlog decline.** On a short cut (TCP survives cuts under about 19 s: fixes:611-616), the host's queued frames arrive in one burst after the hold. A START whose END falls in a later drain then launches long after the host finished it.
   - The first steady drain after Boot also carries the Boot-to-steady backlog.
   - Rule: decline as `backlog` every START drained in the Update where the battle lane went from stale to live, or before the boot's LIVE latch (`_liveLatched`, :269; LatchLive :370-380).
   - Key this on the guest's own observation. NoteDioramaResume runs later in the same Update, inside DioramaTick (NetSyncClient.cs:1603 after ActionTick :1600; resume noted at :1865).
   - Their impacts take the legacy path with no fallback clip (s125 amendment 5).
   - Add an inbound drop counter at NetSyncSocket.cs:370-374.

6. **The run-away waits for replays.** The design's Leg E expectation "the run-away waits, then runs" (design:1293-1294) is false today.
   - InjectRunAway writes `PHASE_MENU_OFF` / `SEQ_MENU_OFF_ESCAPE` at once (NetSyncDiorama.cs:2786-2787), and InjectVerdict has no replay input (NetSyncEnd.cs:470-481).
   - The per-unit escape (`data.pos[2] -= 100f`, the fade, `SetDisappear(true, 5)` once `btl_escape_fade <= 0`) runs every MENU_OFF frame (battle.cs:342-361). `btl_escape_fade` starts at 32 (btl_sys.cs:32) and falls 2 per frame, so an acting caster is hidden about 15 frames in, mid-replay. Only the CLOSE switch waits (:370-376, :446-455).
   - The host never overlaps them: SysEscape dequeues only when `cur_cmd_list` is empty (btl_cmd.cs:510-511).
   - Rule: EndTick (or InjectVerdict) refuses the PresentFlee injection, and the annihilation's MENU_OFF row, with the reason "a replay is still acting" while ActLive is set, bounded by W3.
   - Rewrite Leg E around that rule.

7. **Clocks.** Use battle time. See section 3.5.

8. **Arming the death-attack grace.** DeathStatusScript decides die_seq synchronously inside KillUnit (DeathStatusScript.cs:29-34), so the grace stamp must come before the kill.
   - Stamp it before ApplyActionState at :2258, before the STAT_TICK lane's apply at :2217, and before ApplyUnit's KillUnit branch (:1944-1948). The reconciler kill path is used when a type-6 lethal was dropped, gated, or arrived after a late join.
   - Limit the grace to a lethal impact from a player caster, from the CalcMain path. That is the only host path that requests EnemyDying (SBattleCalculator.cs:336-338). Do not arm it for stat ticks or enemy casters, which would otherwise hold die_seq at 0 for 1500 ms with no START coming.
   - Read bit 5 from the latch in amendment 3.

9. **Scope of the busy-window restore** (design:769-772):
   - Restore only units still linked in btl_list and not in `_hiddenMask`.
   - Write `disappear` through SetDisappear/SetActiveBtlData (BTL_DATA.cs:31-59), not raw.
   - Do not resurrect a bystander enemy that faded during the window (`if (rate == 0) btl.SetDisappear(true, 5);`, btl_util.cs:444-445).
   - Add `animFlag`/`animSpeed`. PlayAnimation writes them (UBS.cs:531-547), and SetDefaultIdle resets them only when it changes the motion (btl_mot.cs:178-183).
   - `bi.def_idle` (btl_mot.cs:275-286) and `tar_bone` are host stance writes that persist on the host. Leave them unrestored and say so.
   - Drop "Channel effects" from the list. A channel ends by itself after about 70-80 frames (SFXChannel.cs:76-87; SFXDataMesh.cs:915).
   - Skip the per-unit restore entirely after `_endInjected` (section 3.2).

10. **The abort stays a hard release plus restore**, as designed, for every abort reason.
    - The s123 lane's D05 suggested stock `BattleAction.Cancel()` for the supersede and END+6 s cases. Cancel gates EffectPoint (`case "EffectPoint": if (cancel) break;`, UBS.cs:966-968), so held impacts could not release at the hit. It walks back only `pos` over several frames (:1324-1343).
    - DelCharacter's stock Cancel is unreachable on the guest (section 5, s123-G04).

11. **Per-boot reset.** Add an `ActResetForBoot()` next to `ResetIntro()` (:797), in Boot's catch (near :941) and in ForceDisarm. It resets:
    - the decline-once latch;
    - pending STARTs;
    - death-grace stamps;
    - the busy-window snapshot;
    - the bit-5 latch;
    - s124's state, once s124 lands.

    Also decide which `act.guest` counters are per-boot and which are process totals. The levers are harness-scoped and released by HarnessReleaseBench, not per boot.

12. **ActAbortAll("leave") goes after LeaveFrom's fade check**, next to the existing AbortReplay at :978 and before SettleForReturn (:983) and the Replace (:994). This follows the precedent at :4091 ("every Leave past its fade check").
    - Placed before the IsFading return (:970-975), a deferred Leave would abort replays while the diorama stays booted.
    - Leg D asserts that a deferred Leave does not bump `aborted`.

13. **The tripwire must cover SysTrans.** A fall-through on a SysTrans replay never reaches CalcMain, but it still causes these effects (btl_cmd.cs:1553-1573):
    - it writes the save-serialised `trance_no` (:1564 → BattleAchievement.cs:191-196) and `enable_trance_glow` (:1558);
    - it fires the support-ability triggers (:1566-1571);
    - it can write ReadyToUnlock through `SetAchievementStatus` (AchievementManager.cs:85) before the held funnel at :113.
    - Count booted entries at the head of ExecVfxCommand, after the short-circuit returns false, or in the SysTrans case.
    - Add a SysTrans `shortcircuit off` red leg with a `trance_no` / `ach_held` invariant.

14. **LoadSFX fault policy.** The magic-caster dereference (UBS.cs:331-335; FindBattleUnit can return null) throws after the op is consumed (:185) and after `cmd.magic_caster_id` was OR'd (:333), but before anything was added to sfxList.
    - Recommendation: treat a caught fault as an abort. Count `faulted` and `aborted` with `abort_why = "fault"`, release held impacts as "abort", and run the restore.
    - Continuing would leave a stale `defaultSFXIndex`, and only END+6 s or 90 s would bound it.

15. **The Defend pose.** SequenceDefend ends with `PlayAnimation Anim=Idle`. SetDefaultIdle picks MP_DEFENCE only under the IdleDefend status (btl_mot.cs:571-572), which the guest never has: ApplyUnit mirrors no status but Death and Trance.
    - Name this explicitly in risk 8 and in the B3 expectation.
    - This is not a regression; the s110-s132 guest never showed the pose either.

16. **Change row.** The Change replay's hit is the only lane that changes a row. Type-1 carries no row (ApplyUnit :1924-2023).
    - SwitchPlayerRow toggles (btl_para.cs:338-339). Once diverged, every later Change flips the guest to the opposite of the host.
    - Script 0107 attacks, and the boot seed from `PLAYER.info.row` (NetSyncDiorama.cs:1577; NetSyncParty.cs:122, which an in-battle switch never updates), also go uncorrected.
    - Decision: name this in risk 8, or carry the caster's resulting absolute row in the START and set it rather than toggle.

17. **Keep the MP_IDLE_CMD launch.** It makes the guest's first-WaitAnimation skip deterministic, while the host's skip depends on `animFrame <= 1` (UBS.cs:213-216). Judge Leg M against the taped host timing with a tolerance of one IDLE_CMD loop.

18. **Unit keys.** s115 already publishes `mot`, `disappear` and `z` (HarnessAgent.cs:3082-3084).
    - s123's `anim` must be the clip name. MotIndex returns -1 for every enemy sequence clip (:3100-3104).
    - Add `die_seq` (Legs K and 2) and `row` (Leg L). `away` alone cannot show that base_pos moved.
    - The unit-tail order test (test:5296-5314, :5309) grows with them.

#### Decisions

| # | Question | Recommendation |
|---|---|---|
| D01 | Which overload carries the hook? | The out overload (amendment 1). |
| D02 | How does s115's run-away coexist with replays? | Hold the injection while ActLive, bounded by W3 (amendment 6). |
| D03 | How does the guest learn bit 5? | A per-boot latch (amendment 3). |
| D04 | Battle time or wall time? | Battle time, except the 90 s cap (section 3.5). |
| D05 | Cancel() or a hard release? | A hard release plus restore, everywhere (amendment 10). |
| D06 | How is "stale" detected, and is a post-outage burst declined? | A two-step drain plus the backlog rule (amendments 4 and 5). |
| D07 | Scope of the restore? | Amendment 9. |
| D08 | Keep the MP_IDLE_CMD launch? | Yes (amendment 17). |
| D09 | Tape-bench leg for s123? | Yes, in addition to the selftest legs (section 4.9). |
| D10 | Does the death grace arm on a reconciler kill? | Yes, before KillUnit in both lanes (amendment 8). |

### 2.3 s124: held impacts and the life mask

#### Live line map

| Hook site | Design cites | Live today |
|---|---|---|
| Hold branch in ApplyActionFrame | (no line); ActionTick :1750-1761 | ApplyActionFrame :2174. STAT_TICK branch :2205-2222 (`if` :2211, Btl2dStatReq :2214, ApplyActionState :2217, stamps :2218-2219, returns). Figures :2232-2235. Motions :2243-2252. State :2257-2260. Gate stamps :2264-2273. |
| STAT_TICK writes absolute values at once | :1810-1822, :1890-1905 | :2211-2222 and ApplyActionState :2280-2308 (lethal :2283-2289, revive :2304-2307) |
| Reconciler skip site | ApplyUnit :1530-1535 | ApplyUnit :1924. Gate :1928-1935. Resolve :1936-1941. `if (!u.Alive)` :1944-1949. |
| `_lastAppliedSeq[slot]` | 3.3.4 | Already exists as a scalar `UInt16` at :1816: the type-1 sample dedupe (:1852-1854, also :4274). The existing per-slot stamps are `_gateSeq` / `_gated` (:1829-1830). |
| Release match key | ResolveWireSlot :1756-1767 | Host NetSyncBattle.cs:2288-2300. Guest ResolveWireUnit :1885-1911. |
| EffectPoint collect and pop | 3.3.4 | UBS.cs:966-1017. Default "Both" :969-970. Zero/collect :980-1004. ExecVfxCommand :987. Figure half :1007-1016 (Btl2dReq :1013). |
| Figure suppressed by disappear | not cited | btl2d.cs:62 `if (btl.bi.disappear == 0)` |
| F4 law comment | not cited | :2226-2231 ("NEVER write d.fig"), :2240-2241 |
| Crit shove / restore | not cited | btl_mot.cs:689-690 / :747-752 |
| Host fig and caster lanes | not cited | SBattleCalculator.cs:210-211 (info ORs), :281-301 (caster lanes), emits :331, :355 |
| Catch literal | HarnessAgent.cs:2961 | :3255. s119 hold keys :3383-3403. |
| End presentation | not cited | allDown :2609. PresentFor NetSyncEnd.cs:382-398 (:394). AnnihilateSettles :408-411. No-settle tail :2723-2736. AllPlayersDown :2797-2802 (count :2813-2826). |

#### Amendments

1. **Rename the per-slot array**, for example `UInt16[8] _actAppliedSeq` with a `Boolean[8]` seen flag. The design's name causes CS0102 or CS0021.
   - It must not be stamped by a held frame's own arrival. Design:787 applies the held frame's horizon gate NOW; if that wrote the stamp, `(Int16)(h.Seq - stamp)` would be 0 and every held life change would read "superseded".
   - Do not reuse `_gateSeq` for the same reason.
   - Stamp it from frames applied immediately, including stat ticks (alongside :2218-2219 and :2266-2272).
   - A release stamps it only when its life change actually applies.
   - Clear it wherever `_gateSeq` is cleared: the boot block :789, Boot's catch :937, ForceDisarm :1017.

2. **Release every held life change at the end injection.**
   - s117 computes `allDown` from LOCAL Death when the host's defeat block arrives (:2609). A player whose kill is still held reads as standing.
   - In host MENU_OFF this takes `AnnihilateSettles(false)` (NetSyncEnd.cs:408-411). That is the s117-1 tail that skips the settle (:2723-2736): a direct PHASE_DEFEAT and an immediate fade, while the killing replay is still in the air.
   - With `_hostEvent` set, a host PHASE_DEFEAT is misread as var 34's PresentDefeat (:394).
   - It also breaks the stage-5 law ("the sample that carries the end lands its final deaths before the phase flips", NetSyncClient.cs:1616-1619, NetSyncDiorama.cs:2340-2342) for masked slots. After the flip, ReconcileTick (:1842-1844) and ActionTick (:2145-2146) quiesce.
   - Fix: at the head of EndTick's injection branch, before AllPlayersDown, release every held life change and every frame queued behind one through the legacy path, with reason `end-inject`.
   - The window is narrow but reachable. The host's annihilation waits for its own fall (btl_sys.cs:64-66; btl_mot.cs:357-366), so a collision needs the guest's hit to lag by more than that: a pending START (up to 1500 ms), the 2500 ms timeout, or a target the replay never hits.
   - Add a bench leg: a held lethal impact on the last player, then `endbench phase-defeat`. Expect "annihilate" with the settle.

3. **Re-check the hidden guard at release.** Today's arrival path skips figures for `_hiddenMask` units (:2232-2235 with `!hiddenT`), because the guest hides by toggling renderers (:1985-1999) and never sets `bi.disappear`. Btl2dReq checks only `bi.disappear` (btl2d.cs:62).
   - At release (hit, late or legacy), re-read `_hiddenMask`. If the unit is hidden, skip the fig write and the flinch, and still apply the life change.
   - Design:822 claims CanPlayCosmeticMotion covers "not hidden". It does not (:2312-2318).

4. **Hold the whole frame, both lanes.**
   - Write the caster triple whenever it is non-zero and `!selfCast`, as the arrival path does (:2234). Do not limit it to drains: Darkside's HP recoil (0032) and WhiteDraw's MP gain (0041) are non-drain caster figures.
   - Mask the caster's life change like the target's. Sacrifice (0045, `_v.Caster.Kill(_v.Caster)`) sends `CastHpRaw == 0` with a different target, and applying it now kills the caster mid-replay.
   - Set the mask bit for the caster slot too, because ApplyUnit would otherwise kill it early.

5. **Queue unpaired frames behind a held change.** An impact with no START (declined, NOOP, or replaced pending) for a slot with a pending held life change currently applies at once, kills or revives early, and then supersedes the paired release.
   - The likeliest case is a held revive. `reviveT` is derived from the guest's own Death bit (:2200), so any unpaired non-lethal frame revives the unit at once (:2306-2307).
   - Generalise the STAT_TICK queue rule to every frame for that slot, bounded by the same timeout.

6. **Leg 8 contradicts 3.3.4.** A stat tick for a held slot queues, so it cannot stamp the slot before the release and cannot cause "superseded" (design:804-805 against :1331-1332).
   - With amendment 5, the remaining job of the superseded guard is ordering between held changes released by different paths.
   - Proposed Leg 8: two held changes on one slot from different replays, an older kill and a newer revive. The revive's replay hits first, and when the kill's release fires it is skipped as superseded.
   - Also decide whether a queued tick's figure (Btl2dStatReq) is delayed with its state.

7. **Release and credit key: (actId, master target).** Credits are counted per (actId, target). Specify:
   - A host buffer drop (:2197-2199) loses an impact, so the next impact on that target releases "late".
   - WhiteDraw (0041) and DragonBreath (0040) emit several CalcResults for one hit on the same target. "One release per call" leaves the extras for "end" or "host-done".
   - Phoenix (0049) and AngelSnack (0052) emit through a nested `new CMD_DATA()`, so their impacts carry id 0 and apply at once.
   - Jump/JumpInTrance (btl_cmd.cs:1534-1536) and SysTrans emit no impacts, so their credits never meet one.

8. **Record `figs[]` at the display, not at the write.** Recording it at ActOnHit's write makes "one entry via hit" true by construction.
   - Add a cheap tap on EffectPoint's Figure half (UBS.cs:1013) or in Btl2dReq, tagged with the release reason.
   - Restate Leg 1 as "no figure before `first_hit_ms`, then one display at the sequence's Figure point". Every stock `.seq` splits Effect and Figure (no stock file uses `Type=Both`): ef100/ef101 PlayerSequence Attack waits 4 frames, ef000 waits 12. So "±2 frames" is wrong.

9. **A replaced pending START releases its held impacts.** A newer START that replaces the pending one (design:669-671) leaves no named release for the old one's held impacts (design:807-811). They fall to host-done (only if host-done is keyed on actId, not on a live record) or to the timeout, while `_actLifeMask` keeps the reconciler off that slot.
   - Release them at once through the legacy path, with reason `replaced` and a `rel_replaced` count.
   - Key host-done on actId.

10. **Measure the real-link lag** (open unknown 3, design:1751; risk 6, design:1539). Add `act.guest.hold.lag{n, min, p50, max}` = hit_ms - arrival_ms per paired release (negative means a credit).
    - Give each `figs[]` entry `{slot, value, via, arrival_ms, release_ms}`.
    - Log one line per release.
    - HeldImpact already needs an arrival time for its timeout; stamp it at :2160.

11. **Re-derive revive at release:** lethal from the raw wire HP, revive = `!lethal && local Death at release`.
    - Classified at arrival, a revive that arrives while an older kill on the same slot is still held reads as non-revive. Its Death removal is then never applied, and a faded enemy never heals (:1973-1981).

12. **Per-boot reset and ownership.** s124 adds `_actLifeMask`, the held list and the renamed seq array, and extends s123's ActDiscardAll. s123 stays free of s124 state.
    - Clear the mask first inside ActDiscardAll, so a throw later cannot leak it.
    - Also clear these in the boot block and in Boot's catch, as a defence in depth that matches the B3.5 three-site convention (:785-789, :936-937, :1016-1017).

13. **Amend the F4 law comment** (:2226-2231, :2240-2241). `d.fig` is now written only inside EffectPoint's zero/collect bracket.
    - The crit shove that follows (btl_mot.cs:689-690) matches stock. The host does it too (fig.info is OR'd before SetDamage at SBattleCalculator.cs:210), and stock restores `pos[2]` (btl_mot.cs:747-752).
    - Legacy releases (late, end, timeout, abort, replaced) keep the direct Btl2dReq and never touch `d.fig`.

14. **Keep the whole-record mask skip** (design:813-815). It matches the horizon gate's rule (:1928-1929). For a held kill it changes nothing, because a dead sample already returns at :1948. For a held revive it freezes max HP/MP, hide, trance and ATB for up to 2.5 s; record that in the README row.
    - Skipped samples are consumed by the dedupe (:1852-1854), so after the release the slot catches up on the next new sample (about 150 ms).

15. **Notes.**
    - s117's `endbench kill` calls KillUnit directly and bypasses the mask, so do not combine it with a held-lethal leg.
    - "hold" now names three things: `netsync.diorama.hold` (s119), `host.start_hold` (s114) and `act.guest.hold` (s124). Grep and log lines must use full paths.

#### Decisions

| # | Question | Recommendation |
|---|---|---|
| D01 | What to call the per-slot array? | `_actAppliedSeq[8]` (amendment 1). |
| D02 | Held changes versus the end injection? | Release them at injection (amendment 2). |
| D03 | Target lane only, or the whole frame? | The whole frame (amendment 4). |
| D04 | Whole-record or partial reconciler skip? | Whole-record (amendment 14). |
| D05 | Unpaired frames on a masked slot? | Queue them behind the held change (amendment 5). |
| D06 | Where is `figs[]` recorded? | At the display (amendment 8). |
| D07 | Who owns the fields? | s124 (amendment 12). |
| D08 | F4 comment and the crit shove? | Amend the comment and accept the shove (amendment 13). |
| D09 | Release key? | (actId, master target) (amendment 7). |
| D10 | Real-link lag? | Add the lag key (amendment 10). |
| D11 | When is revive decided? | At release (amendment 11). |
| D12 | Does release run outside PHASE_NORMAL? | ActTick releases only in PHASE_NORMAL. Amendment 2 flushes everything at injection, and after an injection ActionTick drains nothing more, so no new holds can form. A hit release from ActOnHit is allowed in any phase. |

### 2.4 s125: fallback A

#### Live line map

| Hook site | Design cites | Live today |
|---|---|---|
| Player MP_ATTACK swing replaced by fallback A | NetSyncDiorama.cs:1845-1852 | :2245-2252, inside ApplyActionFrame :2174. The combined guard is at :2247: `dC != null && !selfCast && a.CasterIsPlayer && !lethalC && !reviveC && !hiddenC && CanPlayCosmeticMotion(dC)`. |
| CanPlayCosmeticMotion | :1912 | :2312-2318. It checks only die_seq, stop_anim, Death and FrozenAnimation. Lethal, revive, hidden and self-cast are separate conjuncts at the call site (:2247). |
| Enemy clip parse | BattleActionThread.cs:202-238 | LoadFromBtlSeq :202. PlayAnimation op (case 5) :263-267 (anim byte 255 becomes the literal "Idle" at :265). END appends `PlayAnimation Anim=Idle` at :238-242. |
| setMotion(BTL_DATA, String) | 3.3.5 | btl_mot.cs:178-184. Writes only currentAnimationName, animSpeed, animFlag and animEndFrame. |
| Stock clip attach and frame reset | not cited | btlseq.cs:609-614 (attach if missing :610-611, `animFrame = 0` :614). 255 mapping :600-605. Sequencer BattleActionCode.cs:284-285 (`btl.mot[btl.bi.def_idle]`), :304. |
| Category source | 3.3.5 | GetCommandAction btl_util.cs:349-359. GetCommandTypeSafe :279-288. SetAAData copies `AbilityCategory = aa.Category` (CMD_DATA.cs:50). Monster-transform predicates :259-272 (null-safe). |

#### Amendments

1. **Set `evt.animFrame = 0` after every fallback setMotion**, player and enemy alike. The live swing marks this MANDATORY (:2250), and stock does it too (btlseq.cs:614). Without it, btlseq.cs:331 can end the clip on its first update.
   - Mirror stock's defensive attach for clips outside the unit's own model folder: `if (GetClip(name) == null) AnimationFactory.AddAnimWithAnimatioName(go, name)` (btlseq.cs:610-611). Cross-folder references (the Wraith remap, btlseq.cs:1150-1159) and unregistered mod clips need it.
   - Enemies auto-attach their whole animation folder at creation (ModelFactory.cs:171, :177), so the missing-clip case is narrow. When it happens the clip just does not show (btl_mot.cs:225-227); it is not a freeze.

2. **Skip "Idle" entries.** "The first caster PlayAnimation" can be the literal "Idle": either from byte 255 (:265), or from the PlayAnimation that END appends to any sequence with no case-5 op (:238-242).
   - `setMotion(d, "Idle")` names no clip. The loop frame becomes 65534 (GeoAnim.cs:18-21, :47-55) and the unit freezes until the next setMotion.
   - Rule: take the first non-Idle caster PlayAnimation. If none exists, play nothing. Bench 6.10's oracle uses the same rule.

3. **Derive the category explicitly.** Build a scratch `CMD_DATA {regist = dC, cmd_no, sub_no}` with `SetAAData(btl_util.GetCommandAction(rc))` and read `AbilityCategory & 16`. This is the same idiom as ActLaunch (design:676-678).
   - Classify Item/Throw with `btl_util.GetCommandTypeSafe(cmd_no)`, which needs no regist and also covers mod commands.
   - Check Item/Throw first: GetCommandMainActionIndex returns Void for Item (btl_util.cs:299-300).
   - Record that a support-ability override of the host's live category (CharacterAbilityGems.cs:657, :817) is not mirrored. The clip is cosmetic, so accept this.

4. **Self-cast.** Inheriting the swing's `!selfCast` gives a self-targeted Potion or Cure no clip.
   - That guard exists to prevent figure doubling (:2193-2195), and figures are a separate step (:2232-2235).
   - Allow the caster clip on self-cast when the impact has no DmgMot.
   - 6.10's Potion leg (the s122 tape records "Garnet Potion on self", design:1250) would otherwise go red.

5. **Burst guard.** The design limits fallback A only by "once per action, keyed by (nonce, actId)" plus the old-host 500 ms key (design:819-821).
   - After a resume burst or a boot backlog, every stale-declined, dropped or truncated START plays its clip at once.
   - Rule: no fallback clip for impacts drained in a backlog Update (the s123 amendment 5 trigger). Their figures and state still apply.
   - Several clips on one actor in one frame collapse to the last one written (btl_mot.cs:178-184), so `fallback.clips` would count clips that never showed.

6. **Fix the guard description.** Design:822 lists "not lethal, not revive, not hidden, not self-cast" as CanPlayCosmeticMotion's coverage. Those four are call-site conjuncts (:2247). If fallback A calls only the helper, it loses them.

#### Decisions

| # | Question | Recommendation |
|---|---|---|
| D-a | Skip Idle entries, or resolve them through `btl.mot[def_idle]` or `et.mot[...]`? | Skip (amendment 2). Two resolution rules exist (btlseq.cs:600-604 and BattleActionCode.cs:284-285) and they disagree. |
| D-b | Clip on a self-cast impact? | Yes when no DmgMot (amendment 4). |
| D-c | Clip for backlog impacts? | No (amendment 5). |

### 2.5 s126: trance burst

#### Live line map

| Hook site | Design cites | Live today |
|---|---|---|
| Reconciler model check (where the design puts the wait) | NetSyncDiorama.cs:1610-1615 | :2010-2015 inside ApplyUnit :1924. The trance stat bit is at :2002-2006. |
| Host trance swap | 3.3.6 | btl_cmd.cs:1553-1573. `toTrance = CheckStatus(cmd.regist, Trance)` at :1557 is read at the hit. SetTranceModel at :1562. |
| Effect resolved at SELECT_VFX | 3.3.6 | btl_vfx.cs:48-49 (Activate 257 / End 489) |
| SetTranceModel / ChangeModel | not cited | btl_vfx.cs:184-225 / BTL_DATA.cs:11-29 |
| Trance ENTER order | 3.3.6 [I] | The status is applied in the inflicting hit's calculator (SBattleCalculator.cs:401). The next 150 ms sample carries it (`if (unit.InTrance) info |= 8;` NetSyncBattle.cs:1705; SampleMs :75). The START follows only when the queued SysTrans dequeues: btl_cmd.cs:485, :508, :439-459, :1670 by Speed. |
| Trance END order | 3.3.6 | FinishCommand removes Trance (btl_cmd.cs:1321-1324), and TranceStatusScript.cs:59-60 queues SysTrans |
| SetPresentColor after SysTrans | not cited | btl_cmd.cs:1513-1517 (CheckCommandLoop finish), btl_stat.cs:238-245 |

#### Amendments

1. **Resolve the deferral in ActTick, not in ApplyUnit.**
   - On the selftest branch, where 6.11 runs, ReconcileTick never runs (NetSyncClient.cs:1315-1327, comment :1321). A deferral recorded there never resolves.
   - On the transport branch, ApplyUnit runs only on a new type-1 seq (:1852-1853; up to 150 ms apart, with a strict `>` at NetSyncBattle.cs:1313) and only in PHASE_NORMAL (:1842-1844). So 6.11's "400 ± 50 ms" is out of reach, and a deferral pending when the phase leaves NORMAL is stranded.
   - Rule: ApplyUnit only records the pending target state per slot. ActTick runs on both branches (design:780-781) and resolves hit, grace, decline, abort, end-without-hit and phase exit every frame.
   - This omission predates s111. The selftest branch has lacked ReconcileTick since s107.

2. **The SetTranceModel argument** is the guest's mirrored stat bit at the hit, which matches the host's read at the hit (btl_cmd.cs:1557). Guard it with the stateless probe (swap only when the worn model differs).
   - Note the cases where the bit freezes: ApplyUnit returns before :2002 at the horizon gate (:1930-1933), on a dead sample (:1944-1948) and under the s124 mask. A death that strips Trance on the host (DeathStatusScript.cs:38-41) is mirrored through the bit.

3. **Grace length and release conditions.** ENTER is type-1-first by construction. At host Speed 4 or below the START trails the InTrance sample by whatever remains of the inflicting action, which can exceed 400 ms.
   - Rule: wait while any queued, pending or running replay or held impact names that unit, then 400 ms, capped at 2500 ms.
   - A QUEUED or pending SysTrans START counts as "not hit". The END START is queued from the unit's own FinishCommand, and the per-actor rule can park it.
   - Any decline of that unit's SysTrans START ends the grace at once. Without this rule, a guest without SFXRework (which declines every START) or a stale decline makes every swap 400 ms late with no burst.
   - Gate the grace on this guest being able to replay (SFXRework on, ActionReplay=1).

4. **Launch stance.** SysTrans is outside the host stance gate (s123 amendment 2). The ef257 PlayerSequence plays only a conditional MP_MAGIC, and ef489 plays no caster animation at all.

5. **SetPresentColor.** Stock runs `btl_stat.SetPresentColor(btlData)` when a SysTrans finishes (btl_cmd.cs:1516-1517). A replay never enters cur_cmd_list, so this never runs on the guest.
   - Most of it is redone every frame by CheckStatusLoop → SetStatusVfx (battle.cs:233; btl_stat.cs:344-451). The lasting difference is the weapon tint after a trance End: SetDefaultShader colours only `btl.gameObject` (:484-492), so the weapon keeps its last glow tint.
   - Call SetPresentColor (or `SetBBGColor(actor.weapon_geo)`) when a SysTrans replay ends, naturally or by abort, and after the reconciler's own swap (:2014). Or waive it explicitly.

6. **No restore exemption is needed for the swap.** Every field in the busy-window snapshot is BTL_DATA state, re-applied every frame to whichever model is worn (btlseq.cs:366-385; geo.cs:29-54). This overrides the s126 lane's D6 (see section 5, s125-s126-G4).

#### Decisions

| # | Question | Recommendation |
|---|---|---|
| D1 | Where does the deferral live? | Recorded in ApplyUnit, resolved in ActTick (amendment 1). |
| D2 | Which value goes to SetTranceModel? | The mirrored stat bit at the hit (amendment 2). |
| D3 | Grace length? | Hold while the unit is being acted on, then 400 ms, capped at 2500 ms (amendment 3). |
| D4 | Launch stance for system commands? | Mirror the host gate (amendment 4). |
| D5 | (s125) Self-cast clip? | See 2.4 D-b. |
| D6 | Restore exemption for the swapped model? | None (amendment 6). |

---

## 3. Cross-cutting amendments

### 3.1 Patch numbering and stack order (blocking; decide before the first capture)

- **Replay order.** `tools/memoria_stack_replay.py:102-112` `stack()` sorts by `int(m.group(1))`. The only override, `POSITION_AFTER` at :90, pins s84 after s57. Its docstring (:22) says "numbering is CAPTURE order", but group 2's numbers are not even capture order.
- **What breaks if s122 replays before s131.** s131 rewrote the AppendNetsync catch literal (its hunk `@@ -3246`), and every key-adding group-2 patch must rewrite that same single line (HarnessAgent.cs:3255). So s122 placed before s131 fails to apply; this is more than fuzz.
- **Test helpers that assume number order.**
  - `_caps_at`: test:1920-1923.
  - The `have` filters: :2212, :2680.
  - The hard-coded sub-verb patch list: :2229.
  - BATTLE_CONTAINERS: :2474.
  - The predecessor idiom `f"s{int(patch[1:]) - 1}"`: :2063, :2080, :2103, :4390. For s122 it names s121; the true predecessor is s132.
  - `_prefix` (:1872-1882), `_catch_doc_in` (:843-856) and `_cs_block` (:5401-5424) walk `msr.stack()`.
  - `_all_caps_through` (:1866-1869) uses dict position, so the two orders would disagree.
  - BATTLE_LEVELS (:2197-2199) ends `"s121", "s131", "s132"` with the comment "(s122-s130: group 2's reservation)".
- **Calibration stand-ins are built by subtraction** (S117/S121/S131_CAPS, test:5378-5382). New group-2 caps would silently join them. test:6736 would fail, comparing the s121 stand-in's leaves to `_catch_doc_in("s121")`. :6135, :6306 and :6371 would keep passing while modelling an engine that never existed.
- **Decision for the owner.** The README records the reservation as an owner decision, so ask the owner.
  - (a) **Renumber group 2 to s133-s141 (recommended).** Number order then equals capture order, no test helper changes, and only design tables change (section 4 table, 5.1, the sittings).
  - (b) **Keep s122-s130.** Add a POSITION_AFTER chain (s122 after s132, s123 after s122, and so on). Replace every numeric level comparison with a stack-position helper. Order BATTLE_LEVELS and `NETSYNC_BATTLE_CAPS` by stack position. Land this as a test-only commit before s122 is emitted.
  - Either way, redefine the calibration stand-ins as ladder prefixes (for example `_all_caps_through("menurefusal")`) rather than subtractions, and add an S132 stand-in.
  - Patch names in this document follow the design. Under (a) they become s133-s137.

### 3.2 End presentations

- **The SFX wait exists only in MENU_OFF.** `if (SFX.IsRunning() || ...) proceedEnd = false;` (battle.cs:291) is inside BattleTrailingLoop (:287-375), which only PHASE_MENU_OFF reaches (:132-138).
  - These go straight to BattleIdleLoop, which has no SFX test (battle.cs:151-176, :249-285): PresentClose (NetSyncDiorama.cs:2749-2751; also var 33, late-join flee, VictoryNoPose and OtherEnd: NetSyncEnd.cs:351-353, :388, :395), PresentDefeat (:2741-2743) and the no-settle annihilation (:2729-2731).
  - They fade at once (`FF9Wipe_FadeOutEx(32)` :168). A Game-Over defeat waits only on `ManageBattleSong(30, 6)` (:280-281). ManageBattleEnd and R8 follow about 33 frames later (:171-173).
  - So for these kinds the first R8 hit aborts running replays about 1.1 s after injection, well before W3's 4 s.
  - Amend design:765-766 and :1029-1030.
- **The run-away is not gated** (battle.cs:332-369). See s123 amendment 6.
- **The ActionTick lane closes at injection.** ActionTick leaves frames queued outside PHASE_NORMAL (:2145-2146) and runs before EndTick (NetSyncClient.cs:1600 against :1619).
  - ENDs and impacts that arrive after the injection frame are never drained. They are discarded at teardown (:2137-2141).
  - After an injection, s124's host-done release and ActTick's END+6 s abort cannot fire for them, and the release ladder collapses to the hit, the timeout, W3 and R8.
  - ActStart's "the end is already being presented" decline (design:655) is reachable only through the selftest `endbench guest hold` lever (NetSyncEnd.cs:616-619) or through `EndHudOff`'s ExitFollowing case (:2474-2477, :3435-3438). Define its predicate as `EndHudOff` and record that on transport it is nearly dead.
- **Held life changes are released at injection.** See s124 amendment 2.
- **No per-unit restore after an injection.** When an abort follows `_endInjected` (W3 or R8), release only: sound, SFX, bbg intensity, UnshiftWorld and CameraNo.
  - Skip the per-unit restore (rot, scale, disappear, meshflags, shadow, `pos = base_pos`, SetDefaultIdle). The s115 escape tail and the victory tail own unit pose and visibility then (battle.cs:342-351, :389-404).
  - Restoring disappear and pos re-shows faded runners until the next tail tick. Body materials stay additive black (btl_util.cs:421-425; SetDefaultShader returns while `isFade`, btl_stat.cs:488). The blob shadow can reappear (BTL_DATA.cs:53-54; HonoluluBattleMain.cs:758-777).
- **Cameras after injection.** InjectEnd disables the menu (:2672-2673; KeepHudOff re-asserts it every frame, :2917-2930) and leaves PHASE_NORMAL. The camera tests then force SFX cameras regardless of Speed: `|| btl_phase != PHASE_NORMAL || !FF9BMenu_IsEnable()` (UBS.cs:344), the PlayCamera skip only in NORMAL (:828), and the CameraNo reset only in NORMAL (:36).
  - For a replay CMD_DATA, decide UseCamera and the PlayCamera skip from the host Speed alone (owner decision 4).
  - `useCamera` is fixed when the SFX loads (SFXData.cs:161), so only steps after the injection are affected.
  - ActivateReflect refuses once the menu is off (:1380). That falls inside the accepted v1 reflect gap (decision 6).
  - The hold row (PresentHold) hides the menu but keeps NORMAL, so only the :344 menu term applies there.

### 3.3 Cut, hold and session grace

- **Through a hold, replays keep running.** The s119 hold freezes only the reconciler: TryGetPeerUnits returns 0 when `!PeerBattleLive` (NetSyncBattle.cs:2016-2018; NetSyncDiorama.cs:1849-1851). BattleMain and the sequencer keep running.
  - Let replays run to their natural end through the hold (the owner's hold-through model) and count `act.guest.hold_through` once per hold.
- **Type-6 delivery across a cut.**
  - Type-6 is a FIFO with no re-send (NetSyncSocket.cs:328-338).
  - There are three drop-oldest caps of 64 (s122 amendment 9). The guest's inbound drop is silent.
  - ClearRemote clears only the inbound queues (NetSyncSocket.cs:463-478).
  - The bridge drops game→relay frames while its upstream is down (netsync_bridge.py:562-568), and the relay drops frames for a parked leg (`studies/battle-coop/relay/main.go:235-236`, writeTimeout :43).
  - On a short cut where TCP survives, frames are delivered late as a backlog. A ~6 s cut measured an in-game outage of 13.7 s (fixes:611-617).
  - s122 must add the drop counter, and s123 the inbound counter plus the backlog decline rule (s123 amendment 5).
- **Order on resume.** Pump adopts the first new type-1 (NetSyncBattle.cs:1403-1408) before ActionTick (NetSyncClient.cs:1593, :1600). The watcher notes the resume later, in DioramaTick (:1865).
  - A type-6 frame drained before the first post-cut type-1 still sees `_peerView == null`. This is one more reason for the bit-5 latch (s123 amendment 3).
- **Box B11** ("a 3 s link blip mid-fight", design:1484) predates hold-through. Re-spec it against the real outage (the cut plus 5-10 s):
  - the reconciler frozen by the hold;
  - one stock-menu close at the stale edge, and one "not re-adopted" line (s131);
  - a resume on the same nonce;
  - possibly the host capturing a Ready guest slot about 4.5 s in. That comes from IsGuestOwnedSlot with `MenuStaleMs = 2500` (NetSyncBattle.cs:78), not from s118, which only gates the hand-back;
  - then the backlog: stale declines, legacy figures with no fallback clips, and late launches bounded by host-done or END+6 s.
- **Boundary redials.** The laptop redialled 53 times and the desktop 11 times in 13 minutes, with gaps of 110-455 ms (fixes:624-626). That is about 64 type-6 loss windows per 13 minutes, or 1-3.7% of link time.
  - A lost START is covered (fallback A). A lost END leaves the replay to end naturally; held impacts take the 2500 ms timeout, and only the 90 s cap bounds a hang. This weakens risk 3's "bounded by END + 6 s" (design:1529).
  - A lost lethal impact lets the next post-horizon type-1 kill the unit before the replay's hit. Bench that case (section 4.8, 6.9).

### 3.4 Start hold and the boot backlog

- **Before the boot, type-6 is drained and discarded** (:2137-2141). ActionTick runs before DioramaTick boots (NetSyncClient.cs:1600, :1603). Only the Boot-to-steady window queues; in sitting B that was about 1.6-2.1 s (fixes:596-597).
- **s114's hold does more than freeze ATB.** RunCommandFromQueue also stops dequeuing every declarable command while it is active (btl_cmd.cs:506; IsCommandDeclarable at btl_util.cs:274-277).
  - Only these can emit during an armed hold: non-declarables 49-65 (counters, AutoPotion, RushAttack, EnemyCounter/Dying/Reaction, the Sys* ids, ScriptCounter1-3), commands already in cur_cmd_list, and BTLSEQ, which runs outside the queue (EventEngine.DoEventCode.cs:2993).
- **When the hold does not arm:**
  - a guest that is busy or has sent no word yet, unless its report comes within `LateArmMs = 1000` (NetSyncBattle.cs:242, :3263-3278);
  - after the `StartHoldMs = 8000` cap (:239).

  Sitting B had two battles that never armed (fixes:603-604).
- **The rule.** The same-drain stale rule declines every backlog action the host already finished. The pre-LIVE decline (s123 amendment 5) covers the ones still running.

### 3.5 Clocks

- **The design states no time base** for any of its timers:
  - W3 (+4 s);
  - ActTick's END+6 s and 90 s cap;
  - the 1500 ms pending-start hard abort;
  - the 1500 ms death-attack grace;
  - s124's 2500 ms timeout and END+1500 host-done;
  - s125's 500 ms old-host dedupe;
  - s126's 400 ms grace.
- **Why it matters.** A guest pause stops BattleMain (`if (IsPaused) return;`, HonoluluBattleMain.cs:694-697; IsPaused :972-975) and with it `UBS.Loop` (battle.cs:584). NetSyncClient.Update keeps running ActionTick and EndTick.
  - On wall time, a pause aborts frozen replays: the busy-window restore runs mid-pause, and the action's effects vanish because LoopRender keeps running (UBS.cs:54-60). It also releases held numbers ahead of their hit.
  - The legacy lane already applies impacts mid-pause today, so a wall-clock timeout release is no worse than s110. The aborts are new harm.
- **Recommendation.** Use one battle-time accumulator that skips paused spans, using the same read as EndWatchdogs: `NOPUTDISPENV || isSpecialTutorialWindow` (:2939-2943), counted only between two paused reads.
  - EndWatchdogs' own `_endPausedMs` is fed only after an injection (:2563-2573, reset :2756-2759), so s123 needs its own accumulator. W3 can reuse the end accumulator.
  - Apply battle time to every in-scene timer. Keep wall time only for the 90 s cap.
  - The death-attack grace is evaluated only inside BattleMain anyway, so its clock barely matters. Battle time keeps it uniform.
- **A START that arrives while paused** goes into the actor's pending slot and launches after the unpause. ActTick does not launch while IsPaused.
- **Bench leg.** Pause 3-8 s mid-replay and expect no abort and no early release.

### 3.6 Containment and observability

- **Keys publish in every role.** Do not copy the `IsSelfTestRole ? x : -1` getter pattern (NetSyncBattle.StockMenu.cs:2002).
  - `act.host.loop{}` and `act.host.tape{}` are fed only by the selftest loopback (design:634-637) and legitimately read zero on a live role. A tape-bench guest must not judge from them.
- **The tripwire covers SysTrans** (s123 amendment 13).
- **Teardown.** Put ActDiscardAll between AbortReplay (:1035) and Disarm (:1036). It never applies anything (design:755-757).
- **The diorama-end NRE baseline.** Single `SmoothFrameUpdater_Battle.Apply` NREs appear at diorama ends.
  - They come from a stale smooth delegate that fires after the scene is replaced (FPSManager.cs:31-34, :113-122; stack from SceneDirector.Update). This happens in stock code and predates s111.
  - The s131 laptop had 2 in 4 dioramas (`.harness-runs/sittingB-20261015/output_log-laptop.txt:296-302`, :396-402). Desktop guest benches have shown it since 2026-10-12.
  - Replay state cannot reach it (section 5, cross-G6). Box B22's "no NRE in output_log.txt" (design:1500) must exclude that known stack, or be judged in a launch with no diorama.

### 3.7 Process hang (new risk, next to risk 10 and box B12)

- **The unknown holder.** The host's whole-process hang in Unity's asset GC has an unidentified lock holder. One candidate is the SaXAudio XAudio2 callback, which enters Mono through a reverse P/Invoke (SaXAudio.cs:82, :213-218; fixes:96-101, :652-654). A second native-to-managed callback runs on every OGG bank add (SdLibAPIWithSaXAudio.cs:98).
- **What replay changes.** Replay raises the laptop's sound-effect plays back towards what solo stock plays. Sitting B ran with T1 armed and saw no hang (fixes:580-585).
- **What to do.** Arm T1 on the laptop bridge in the action-replay sitting. Cross-reference the conditional s12x lane (fixes:341-357).
  - Its soak compares host plus fake guest against Enabled=0, so it does not measure replay load on the guest. Add a guest-replay arm if the hang recurs.

---

## 4. Harness and bench plan amendments

### 4.1 Capability ladder

- **Rung order and calibration sets.** Append `actstart`, `actreplay`, `acthold`, `actfallback` and `acttrance` after `grace40` in `NETSYNC_BATTLE_CAPS` (fakegame.py:168-191). The ladder rule (fakegame.py:124-125) forbids gaps. Give each rung a calibration set like `NETSYNC_S131_CAPS` / `NETSYNC_S132_CAPS` (:197, :200).
- **Numbering.** This depends on section 3.1. Under option (b), every numeric comparison in the tests moves to stack position.
- **Keyless levels.** BATTLE_KEYLESS_LEVELS (test:2202) is defined as "adds NO harness key". s122-s126 all add keys, so they do not join it.
  - The dress stages (s127-s130) add keys only outside `netsync`. That needs either a redefinition or their own level table. Decide this when s127 is designed.

### 4.2 Keys, containers, sentinels

- **The block.** `act` is a new `netsync.battle` sub-object, with `host` (s122) and `guest` (s123): `CAP_KEYS["actstart"] = {"act": ("host",)}`, `["actreplay"] = {"act": ("guest",)}`.
  - s124-s126 nest `hold`, `fallback` and `trance` inside `act.guest` via `NETSYNC_BATTLE_NESTED_KEYS`.
  - `act.host` and `act.guest` go into BATTLE_CONTAINERS (test:1843-1847), or the ladder's nested check (:1993-1999) cannot see them.
- **Make the test's descent path-keyed.** `_leaves` descends only into dicts whose bare key name is in FIXED_SUBOBJECTS (test:1837-1841, :1859).
  - "guest" is already there (from s114's `start_hold.guest`), so `act.guest` descends. "host" descends only at top level.
  - "last" is already the nullable `host.handback.last` (BATTLE_NULLABLE :1849-1850).
  - Recommendation: descend by path using BATTLE_CONTAINERS, a small test-only change, so s122-s126 keep readable names.
- **Specify the unspecified sub-objects.** `act.host.kinds{...}`, `act.host.last{...}`, `act.guest.levers{...}` and `act.guest.last{...}` have no key sets (design:1068-1069). `act.guest.fallback.last` is specified (:1071).
  - Decide for each `last` whether it is a nullable record (one leaf, BATTLE_NULLABLE, sentinel `null`) or a fixed sub-object. Recommendation: nullable, like `handback.last`.
- **Sentinels** follow the live convention in HarnessAgent.cs:3255: counts 0, ids and ms -1, booleans false, strings and nullable records null, fixed sub-objects written out whole.
- **Accessors.** Every key needs an accessor and every accessor a key, with sentinel types matched (test:2120-2146; `State.NETSYNC_BATTLE_ACCESSORS` channel.py:2191-2192).
  - Each keyed level needs exactly one new capability accessor (test:2451-2460).
  - Use a `coop_act_*` prefix. The `coop_replay_*` (channel.py:1439-1468) and `coop_hold_*` (:1669-1700) families are taken.

### 4.3 Sub-verbs and op tables

- **`actbench`** goes into four places together: HarnessAgent's unknown-sub-verb refusal literal (HarnessAgent.cs:1768), `NETSYNC_SUBVERBS` (session.py:8359-8362), `NETSYNC_AUTHORITY_SUBVERBS` and `NETSYNC_BATTLE_SUBVERBS`, keyed on `netsync.battle.act.host` (s122 amendment 13).
- **Op tables.** Add `Session.NETSYNC_ACTBENCH_OPS` / `NETSYNC_ACTBENCH_OP_CAPS`, `FG.actbench_ops(caps)`, an `elif sub == "actbench"` branch in Session.netsync (beside the branches at session.py:8609-8675), and a row in the capability-key law loop (test:2066).
  - Per-op keys are `act.guest` (s123), `act.guest.hold` (s124), `act.guest.fallback` (s125) and `act.guest.trance` (s126) (design:1098-1099).
- **A later value of an older op.** `tape play` (s123) is a later value of s122's `tape` op. Give it a value-cap table like `NETSYNC_ENDBENCH_VALUE_CAPS` (session.py:8442-8448), plus the s122 engine's own refusal text.
- **The two `clear` ops.** s122 has `tape clear` and s123 adds a top-level `clear` (design:1068-1069, :767). Keep them distinct in the op table.
- **Refusals.** Pin per-op argument refusals in `R3_REFUSALS` (test:4462, checked at :4492).
- **Dress verbs (s127-s130, for later).** `selfdress` in a separate `NETSYNC_DRESS_SUBVERBS` is never consulted by Session.netsync's gate (session.py:8583-8608, `cap = f33 or nb`). Its `dress.*` key also fails the `netsync.battle` prefix law (test:2046). Widen the gate and give dress its own key-law test when s128 is designed.

### 4.4 Constants and selftest proofs

- **Constants.** See s122 amendment 11.
- **A selftest for the pure decisions.** Pin the s122 codec and the pure decisions of s123-s125 with engine selftest rows plus a proof line: decline reasons, the stale rule, release reasons, the superseded rule, clip choice and the dedupe key.
  - Put them in a new `XxxSelfTest` in `NetSyncDiorama.Replay.cs`, logged after PROOF_ADOPT (NetSyncClient.cs:1368-1383).
  - Add Python twins with parameters equal to the C# method's (test:5652-5664), the proof list per engine (test:6151-6158), and the fake's proof block.
- **The "rewrite the whole block in one hunk" worry is wrong.** Per-patch marker sections that run to the stop line read cleanly (the s118 precedent at test:5693). Only rewriting an earlier patch's row lines, in a hunk that does not hold the whole block, goes stale.
- **Row counts.** Do not add rows to ControlSelfTest, whose count is pinned at 53 (battlewire.py:1693; test:5699-5702).

### 4.5 Release and reset

- **A reset test.** Add the actbench analogue of `test_reset_releases_every_r3_lever` (test:5240-5263):
  - set `hoststarts off`, `replay off`, `rework off`, `shortcircuit off`, `hold off`, `lifeskip off`, `fallback off` and `trancegrace off`;
  - set `tape rec` and feed one inbox frame;
  - run `reset`, wait for `not forced`, and re-read every lever at rest under `selftest 1`.
- **Wiring.** Hook the act release into HarnessReleaseBench (NetSyncBattle.cs:4077-4144) after the s111-s118 releases. Mirror it in fakegame's `_selftest_release`.

### 4.6 Unit observables

Add `die_seq` and `row` to AppendUnits (HarnessAgent.cs:3037, keys :3051-3087). Make `anim` the clip name. Name a hit-time key (`first_hit_ms`, inside `act.guest.last`) that Leg 1, Leg 3 and 6.11 can read. Grow the unit-tail order test (test:5296-5314).

### 4.7 Calibration catalogs

Sections 6.7-6.11 give only prose REDs. Following the house pattern:
- Give every check an ID and a `-CAL` row.
- **OLD_PREDICTED:** everything except setup, probe and CAL, derived from 6.1's rule (design:1131-1134).
- **LEVER_PREDICTED:** one set per lever.
- **Maybe sets:** for probabilistic reds, such as Leg C's `started == tape.starts - declined` arithmetic and 6.10's dedupe counts.
- Precedents: `coop_battle_start_hold.py:250`, :259-262, :465; `coop_battle_wait_parity.py:143-151`; `coop_battle_flee_defeat.py:313`, :328-342; `coop_cut_hold.py:382-427`.
- The design never specified these for 6.2-6.6 either. They were built at build time, and should be here too.

### 4.8 Per-bench changes

- **6.7 (s122 host).**
  - Scene 306 group 2 or 4 (s122 amendment 15).
  - RED on s132 (s122 amendment 1).
  - Tape egress (s122 amendment 14).
  - GREEN as "every non-stat impact is 52 bytes".
  - `no_end` as defined in s122 amendment 7.
- **6.8 (s123 guest).**
  - **Leg C:** `dioboot` uses the same scene and group as the tape.
  - **Leg D2** needs a new no-Leave teardown seam. A selftest-only `actbench teardown` should run ForceDisarm, then SFX.EndBattle, inside a booted bench diorama.
    - `warp` is refused off FieldHUD (Ff9mkDebugMenu.cs:2123-2124; BattleMapDebug sets BattleHUD at UIManager.cs:319-324).
    - Harness release Leaves through the authored path (HarnessAgent.cs:1799-1802, :1848-1851).
    - ForceDisarm also runs after every normal Leave, so D2 really tests "no LeaveFrom first".
  - **Leg E** is rewritten for the run-away hold (s123 amendment 6). Add close and defeat injections while a replay is running; the expected abort for those is at R8, not W3.
  - **Leg I** must not edit Memoria.ini mid-run.
    - Any change to bsig re-commits `_enabled` / `_role` from the ini (NetSyncClient.cs:981-983). That drops the forced selftest role, and the bench stops (Update returns at `if (!_enabled)`).
    - The live install's ini currently reads `Enabled = 1`, `Role = host`, so `netsync selftest 1` is refused outright (:4635-4638).
    - Add a process-local `actbench knob 0|1|ini` instead (precedent: `bbench knob`, HarnessAgent.cs:1608-1609; "Memoria.ini is READ, never written", coop_stock_menu_live.py:47-48).
    - ActionReplay must also join the bsig set (NetSyncClient.cs:972-979; design:778).
  - **Leg K** arms `bbench start 0x01`, then `bbench caps 0x22`. The start op resets caps to 0x02 (NetSyncBattle.StockMenu.cs:1791). The grace must read the per-boot latch: in the selftest order PeerBattleLive is false outside StockMenuTick (SelfTestPump zeroes it; BenchFeedTick sets it at StockMenu.cs:1262-1263, :1653-1654).
  - **Leg L** reads the new `row` key.
  - **Leg M** uses the one-loop tolerance from s123 amendment 17.
  - **New legs:**
    - a pause leg (section 3.5);
    - a deferred-Leave leg that expects no change to `aborted`;
    - a backlog leg: a split START/END burst after a stale→live edge, expecting a `backlog` decline;
    - a SysTrans `shortcircuit off` leg.
- **6.9 (s124 hold).**
  - Leg 1 is timed at the Figure point and observed at the display (s124 amendment 8).
  - Leg 8 is rewritten (s124 amendment 6).
  - **New legs:**
    - a held lethal impact on the last player, then defeat (s124 amendment 2);
    - a hidden-target release;
    - a Darkside-shaped caster triple;
    - a replaced pending START;
    - a held kill with no paired lethal impact, then a dead type-1 sample.
- **6.10 (s125 fallback).**
  - Say which target the Potion leg uses (s125 amendment 4).
  - Add an Idle-only sequence leg and a burst leg with distinct actIds.
- **6.11 (s126 trance).**
  - Timing is achievable only with the ActTick resolver (s126 amendment 1).
  - Add a leg with a SysTrans START parked past 400 ms behind a running replay, expecting the swap at `first_hit`.
  - Add a leg with a declined START, expecting the swap at once.

### 4.9 Tape bench

- **Why use it.** It is the only solo way to exercise the real intake.
  - `BootedWireNonce` is stamped only by the watcher (NetSyncClient.cs:2063), so a selftest dioboot drops real-path frames (NetSyncDiorama.cs:2158).
  - The selftest chain never runs ReconcileTick or ActionTick (NetSyncClient.cs:1315-1327).
  - So keep the selftest `actbench` legs for every fabricated leg and every lever calibration, and add an act leg on the tape bench.
- **The act leg.**
  - Record an s122+ host tape with `coop_tape_record.py`. Its policy already plays Attack, Defend and Potion (coop_tape_record.py:316-331). Add Fire/Fira entries if wanted. Stock Fire and Fira resolve to kind 3, not kind 1 (only CSV `SequenceFile` data gives kind 1).
  - Replay it into an s123+ guest with `replay-host`.
  - Judge it on `act.guest` counters, which publish in every role.
  - The existing s117 arc tape already drives the old-host path: no START, so legacy impacts, plus fallback A from s125.
- **Limitation.** `replay-host`'s blackhole drops frames rather than delaying them (coop_peer.py:981-983, :1063-1065). It cannot reproduce a resume burst. Add a delay mode (withhold, then send back-to-back) and calibrate it red against the real-link burst before it judges B11.
- **Decoding.** Teach `coop_peer` to decode type 6 through battlewire (s122 D5). A sixth tape fact ("STARTs on this tape") is needed only for the act leg.
- **Regression use.** Add the `coop_cut_hold` legs to the 6.1 regression set from s123 on, since s123 changes ForceDisarm, LeaveFrom and the tick order.
  - Pin `COOP_TAPE` to the s117 arc tape (`20261014-224827-host250-s117.f9tape`; `ARC_TAPE_NAME` at `_coop_peer_bench.py:83`) for those runs. Otherwise a fresh s122 recording silently becomes `latest.json`'s default (`coop_tape_record.py:378-385`; `latest_tape` at `_coop_peer_bench.py:1422-1438`).
  - Any new tape needs its own CAL pass: the sidecar is keyed by sha256 and fails closed (`read_cal` :1452-1467).
  - The MATCHERS (`_coop_peer_bench.py:696-771`) read no action-lane line and need no recalibration. `engine_stage` (:201-208) already reports s122-s130 as stage 131.

### 4.10 The two-machine sitting

- **Rename it.** "Sitting B" already names the r3c/s131 run in fixes (:578, :429), the commit log (b5422d47) and the README. Call the group-2 sitting "Sitting C".
- **Fold in boxes that were never run:**
  - A12 (Zidane's Flee gil);
  - A15/A16 (the s117 defeat), which must be proven before s124 lands because they interact (s124 amendment 2);
  - the s121 menu refusal;
  - a clean back-to-back pair;
  - A13, A14 and A17;
  - A18 (multi-target and self-target numbers), as B3's baseline, run before the s123 deploy;
  - A19 (the shop box).

  Evidence: design:1464-1465, :1476; fixes:599-600, :661, :429. The sitting also arms T1 on the laptop bridge (section 3.7).
- **Mixed-DLL box B13.** The old side is s132, not s117. An s117 laptop lacks s119, s120 and s131, which would confound the box. Pre-prove "s132 host + new guest" solo by replaying an s131/s132 host tape (section 4.9).
- **The cold leg.** Field 350 (Dali) has no random encounters (fixes:595, :661). It is still the right cold field: WarmVerdict's cold reasons (NetSyncDiorama.cs:1177-1180) and the README s97 row both rest on it, and every random-encounter field has a Main_Reinit (F1-BUILD.md:662-663), so moving the leg would make it warm.
  - Start the fight on 350 with the harness verb `battle <scene> [group]` (HarnessAgent.cs:856-870 → Ff9mkDebugMenu.cs:516-556, `isDebug = false`). Write that step into A3 and B24.
- **B11** is re-specified (section 3.3).
- **B22** excludes the known Apply NRE (section 3.6).
- **B3** names Defend's idle pose as expected (s123 amendment 15).

---

## 5. Refuted findings (do not re-litigate)

- **s122-G4** "DescribeCommandVfx cannot mirror lazily decided branches". The VfxAction load is eager (BTL_SCENE.cs:157-168), and the Beatrix fix is a pure predicate (btl_vfx.cs:120-124). Key Describe on VfxAction (s122 amendment 10).
- **s122-G9** "The engine's unknown-sub-verb literal is left unspecified". Design 5.1 and 5.2 (":1068", ":1083", ":1114") plus the pinned tests (test:101-106, :127-132, :1962-2006) force the HarnessAgent.cs:1768 edit.
- **s123-G04** "A DelCharacter-cancelled replay is unclassified". Every DelCharacter caller on the guest is either gated by IsBtlBusy ANY_CURRENT (btl_mot.cs:337), which the s123 hook covers, or unreachable (isDebug ServiceEvents, OpenMainMenu blocked). Cancel's only caller is btl_sys.cs:327.
- **s124-G03** "Self-cast double-writes the figure at release". The host sends identical target and caster triples from one fig object (NetSyncBattle.cs:2183-2188), and EffectPoint collects one entry per unit (UBS.cs:988-1004).
- **s124-G13** "Leg 2's die_seq depends on the enemy's AttackOnDeath flag". Both scene-67 enemy types have flags 0x0002 (no die_atk), so DeathStatusScript.cs:33 never consults IsBtlBusy.
- **s125-s126-G4** "The busy-window restore writes old mesh state onto the trance model". Every restored field is BTL_DATA state, re-applied every frame to the worn model (btlseq.cs:366-385; geo.cs:29-54). No exemption is needed.
- **s125-s126-G5** "The s126 grace's bit-5 source is undefined across a blip". The model check runs only with a live view (NetSyncDiorama.cs:1849-1851; NetSyncBattle.cs:2016-2018). The s123 death grace still needs the latch.
- **harness-c22** "s122 re-baseline 'nothing else changes' is false". Every live caps reader masks (test:2932 already has `~0x3C`; scenario checks use `& 2` or masks), and `actions_this_battle` only feeds log text.
- **harness-x04** "State accessor name collisions". The design names no accessors, and its namespace is `act`.
- **harness-g10** "The stand-in behaviour model is unspecified". It is specified at the same level as the rungs that landed, and the behaviour is in 3.3 and 6.8-6.11.
- **harness-g12** "coop_tape_record cannot produce an action tape". The design uses the in-engine tape and 6.7's command plan, and the recorder already plays Potion, Defend and Attack.
- **cross-G6** "The SmoothFrameUpdater NRE sits at the seam the replay extends". It is a stale stock smooth delegate firing after the scene unloads (FPSManager.cs:31-34, :113-122), it predates s111, and replay state cannot reach it. B22 still needs its baseline (section 3.6).

**Lane recommendations overridden in this synthesis:**
- Cross-cutting D8 (hook only the wrapper overload) is overridden by s123-G01 (s123 amendment 1).
- s123 D05 (use Cancel() for the supersede and timeout aborts) is overridden by the Cancel/EffectPoint evidence (s123 amendment 10).
- s125-s126 D6 (re-snapshot mesh state on a model swap) is overridden by refuted s125-s126-G4.
- s122 D1's "key kind 1 on SequenceFile" is overridden by refuted s122-G4.
