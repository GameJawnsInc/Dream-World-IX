# Co-op adversarial review and stock-experience roadmap

**Status: review only. Nothing was edited, built or deployed.** Run 2026-10-25 over the live shared engine tree
`C:\gd\FFIX\Memoria` at the netsync **s145** tip, plus the kit side (`coop.py`, the bridge, the Workspace Co-op
tab, the harness, tutorial 17). Line numbers drift as other sessions edit that tree.

**Method.** The stack was split into 10 subsystems, each with its own adversarial reviewer:
- transport/relay/bridge;
- session lifecycle and save safety;
- field gates and follow;
- dialogue authority;
- the battle command lane;
- the diorama;
- the world map;
- the ghost and self-dress;
- vanilla inertness;
- the kit and Python side.

Every finding then went to 1-2 independent skeptics told to refute it: a *reachability* lens (trace it end to
end yourself) and a *mitigation + severity* lens (is it guarded elsewhere, or a ratified decision?). A
completeness critic looked for what nobody covered.

**Result:** 69 findings, of which 64 survived (62 confirmed by every skeptic, 2 split) and 5 were refuted.
Several reviewers hit the same root cause independently; those are merged below. Full evidence for every
finding, including each skeptic's own trace, is in [`findings.json`](findings.json).

Companion: [`../field-coop/GUEST-TRAVERSAL.md`](../field-coop/GUEST-TRAVERSAL.md) covers the ladder/jump
census and design (the owner's ask).

**Health note first.** The architecture holds up under this pass. The paradigm, host-authoritative with the
guest as puppet, the exit ramp and the autosave guard, has no defect that leaks host state into a guest's
permanent save in ordinary play. The defects cluster in two places:
- **session edges:** quitting, disabling, reconnecting, titles, the ending;
- **the stock-play rough edges** a real pair would feel.

Most fixes are small.

## 1. Fix first: merged defects, ranked by what a real pair would hit

Numbers in brackets point at the appendix table and `findings.json`.

### 1.1 After the host quits, the guest's own game has no random battles and never autosaves [1, 10, 14, 19]

`suppress = _followHost && (connected || withinGrace || sessionHeld)` (`NetSyncClient.cs:1802`) uses
`_socket.IsConnected`. On the relay path that is only the loopback hop to the local bridge, which stays up
indefinitely after the host leaves. So after the exit ramp hands the guest its own save back, encounters stay
off and `EventEngine`'s `noSave |= SuppressEncounters` (`EventEngine.cs:693`) keeps autosave off. This lasts
until the guest stops the bridge or changes FollowHost.

Four reviewers filed it independently. It is the PEER-ALIVE law broken at the suppress site, and it is
**already listed as a KNOWN follow-up in the s120 README row**, but it was never fixed.

**Fix:** key the term on the peer being alive (`IsConnected && GetRemote().Valid`, held by a last-alive
tick), add `_role == "client"`, and drop suppression once the ramp has fired.

### 1.2 A guest watching a battle can be frozen in it forever [4, 8]

Every automatic diorama exit runs inside the enabled transport branch, after `if (!_enabled) return;`
(`NetSyncClient.cs:1414`): the watcher, fences 1-2, the hold and stall caps, the end-leave and the reconciler.
And the exit ramp waits on `!NetSyncDiorama.Booted` (`:1353`). So a guest who clicks *Turn co-op off*
mid-battle, edits a transport key, or drops FollowHost and then loses the link is stuck in a frozen battle.
The only exit is the developer ~ *Leave diorama*.

**Fix:** a minimal "session over → `Leave()` the booted wire diorama" step above the `_enabled` and
socket-null returns, and a direct `Leave()` from `ApplyConfigChange` and the unfollow edge.

### 1.3 A BOM in Memoria.ini wipes the player's whole mod list [12]

Every kit ini reader decodes plain `utf-8` (`coop.py:458`), so a BOM'd first line breaks the `[Mod]` header
match. `ensure_folder_registered` then appends a **second** `[Mod]` with `FolderNames = "FF9Coop"`, and the
engine, which is last-write-wins, loads only that folder: Moguri, FF9CustomMap and the -world overworld are
all gone. A verifier reproduced this with the worktree's own `coop.py`. Notepad and Notepad++ can both write
a BOM.

**Fix:** use `utf-8-sig` everywhere `coop.py` and the harness read Memoria.ini, and add a BOM regression test.

### 1.4 The ending is not followable [2, 18, 29]

- `RedirectGuestFieldJump` has no ENDING case (`NetSyncClient.cs:439`), and fields 3000-3012 put the UI in
  `PreEnding`. Both follow paths require `FieldHUD` (`:3735`, `:5388`).
- On 3011 the guest's `Field(16000)` is bounced. It replays the last beat about 3 times (~30 s) until the
  bounce budget lets it through.
- A guest lagging inside the ending chain cannot be rescued by any follow-warp.
- *Split verdict:* once the guest does reach EndingMain, the game-finish flag and the CompleteGame/Blackjack
  achievement status can reach the guest's disk, because `ReportAchievement` writes ReadyToUnlock before the
  co-op gate (`AchievementManager.cs:85`).
- The critic resolved the two reviewers' disagreement. The guest *does* get through, late, so the
  bounce-budget "never escapes" variant [29] has no demonstrated stock instance.

**Fix:**
- Pass `dest == FLDSCRPT_EVTNO_ENDING` and any jump inside the 3000-3012 band (a non-interactive chain both
  machines play identically), or accept `PreEnding` as follow-eligible.
- Move the achievement gate to the top of `ReportAchievement`.
- Gate `SetGameFinishFlagWithTrue` on `!IsMirroringStory`.

### 1.5 Dialogue: a paused guest loses the host's choices, and forced re-ask loops spin forever [6, 20]

- **The pause.** `Purge` ages host ADV/CHO events out after 20 s of wall time even while the guest is
  paused (`NetSyncDialog.cs:1053`); only the KEY clock is frozen. A guest who pauses through a host choice
  gets that line orphaned, and it is auto-committed as **Cancel**, which is "No" when the host picked "Yes".
  **Fix:** freeze the inbox clock in `HoldKeyClocks` the same way.
- **The re-ask loop.** The orphan rule always commits `CancelChoice` (`:1521`). Stock loops that re-ask on
  Cancel then spin about every 4 s with the guest's input swallowed. Two instances:
  - Ice Cavern/Outside 312, "Is that okay with you?" in a `while (GetDialogChoice == 1)` loop;
  - the Prima Vista crash-site ATE tutorial.

  **Fix:** remember orphan commits per key. On a repeat within ~10 s, pick the default (non-cancel) option,
  then hand the window back Local with a chip.

### 1.6 Battle: the digit panel can throw away the host's armour [7, 33]

- **Throw.** Amarant's Throw has no ability list, so the digit panel sends it as an Instant pick. The host
  intake never checks the command *type*, and queues Throw with `sub_no` 190 = **Maximillian**. A spare one
  in the host's bag is consumed (`NetSyncBattle.cs:5976`, `btl_util.cs:345`). The default stock-menu path
  greys Throw. The digit panel serves stranded slots, `GuestStockMenu=0` and the s145 world-map declines.
  The intake comment "the engine re-validates, so the worst case is a no-op" is a docstring wish.
  **Fix:** at the host intake, accept only Normal/Instant/Ability command types (refuse Throw/Item/Mix with
  a named drop), and leave them out of the digit roster.
- **Picks by position.** Digit-panel target and item picks are re-derived by list position at keypress
  (`:4741`). An enemy dying between draw and press moves `[2]` onto the host's Zidane.
  **Fix:** snapshot the candidates when the pick mode opens.

### 1.7 Follow and the world map [5, 9, 24/45]

- **A follow-warp racing the guest's own transition** strands the guest behind a stale `_followWarpedTo`
  latch, or reloads twice (`NetSyncClient.cs:5053`). **Fix:** refuse to start a follow while fading,
  `attr & 15`, or `nextMapNo != fldMapNo`, and retry after landing.
- **Pairing on the world map** seats the guest's *own* party in the host's world battles.
  `NetSyncParty.MirrorActive` is only armed at a field load (`NetSyncDiorama.cs:2723`). **Fix:** make
  "no party mirror" a world-verdict decline row, or parse the party sections at the wire boot.
- **FollowHost is not role-gated in the engine** (`:1105`, `:3691`). A host with a stale `FollowHost=1`
  follow-warps its *real* save to the guest's field and loses its own encounters and autosaves. Only the
  Python writers guard this. **Fix:** commit `_followHost = followHost && role == "client"`.

### 1.8 Session edges [17, 28, 21]

- **The exit ramp reloads an autosave that can predate the session.** Battle returns never autosave, and
  autosave is suppressed from the moment the bridge connects. A guest who grinds 30 minutes, then pairs,
  loses those 30 minutes when the session ends. The comment at `NetSyncClient.cs:698-702` claims a capture
  that does not exist. **Fix:** take one own-state snapshot at first pairing, and restore that.
- **A pending ramp survives a trip to the title.** It then yanks the player out of the Load or New Game they
  just chose (`:1459`). **Fix:** consume the ramp in place at the Title scene.
- **A cold field return after a mid-fight leave never stops the battle song**; it plays over the restored
  field song (`NetSyncDiorama.cs:1526`).

### 1.9 Transport and relay [3/23, 11/27 + 25, 13, 15, 16]

- **The direct-LAN listener is never closed.** `Stop()` never closes the host's `TcpListener`
  (`NetSyncSocket.cs:544`), so a live co-op restart can't bind, and the zombie eats the first guest dial.
- **Two people on one code evict each other.** The relay replaces a same-code leg and the bridge redials
  instantly (`netsync_bridge.py:465`, relay `main.go:199`), so two same-code legs evict each other in a tight
  loop that neither engine sees. Two friends clicking one invite is enough. It is made likelier by
  **a former guest's stored code being reused as its own host code** (`coop.py:678`). **Fix:** a relay close
  code on replace, a terminal "someone else is on this code" in the bridge, and a separate HostSessionCode.
- **A wire-version mismatch is silent over the relay** (`NetSyncRelay.cs:356`), and the host's overlay says
  "connected" with no peer at all. Tutorial 17 and the CHANGELOG say "mismatched engines refuse to pair."
  WIRE-5 is designed but not built.
- **The public relay has no read limit or connection caps** (`main.go:113`, gorilla `SetReadLimit` never
  called), so one client can OOM it and drop every session. ⚠ This was judged on the repo copy. Check the
  deployed relay before acting.
- **Latest-slot lanes re-send 2-5 KB of state every 33 ms** (~0.7-1.2 Mbit/s). WIRE-7 (send on change) is
  designed but not built.

### 1.10 One-line robustness fix [36]

`DriveGhost` calls `AnimationDB.GetValue` on the peer's raw anim id (`NetSyncClient.cs:9093`). That throws on
an unknown id every frame and aborts the rest of `Update`, including `Pump` and `DioramaTick`, while both
players share a field. Matching installs never trigger it; a mod-content mismatch or a hostile peer does.
**Already known as CLB-3 and deferred twice.** Fix: `TryGetValue`.

The remaining low-severity findings (UX, docs and kit-tab edges) are in the appendix.

## 2. What no reviewer covered (completeness critic, each spot-checked)

- **There is no session-compatibility handshake.** Nothing carries the language, the build within wire v14
  (43 README rows say "wire UNCHANGED"), or the mod set.
  - **JP vs non-JP breaks the script-key relay mechanically.** `ETb.KeyOn` applies the JP Confirm↔Cancel swap
    before the relay, so a JP host's Cancel-bit press never satisfies an EN guest's Confirm poll.
  - Field gates check only that a field id is *registered*, not that its content matches.
  - *Confirmed.*
- **The stock HUD minigames were never surveyed** (`EventHUD.cs:349-401`). Zero netsync references to
  EventHUD, MinigameHUD or TimerUI.
  - The disc-1 swordfight in the play (Chanbara @64) rolls its prompt from the guest's own RNG
    (`GetRandom & 7`).
  - The face-button answers come from the host's relayed keys, while the direction and Start answers come
    from the guest's own pad. So half the answers go to a different prompt.
  - Others: SwingACage 1208, GetTheKey 2204 (TimerUI), ChocoHot 2950, the Pandemonium elevator 2711, jump
    rope, the Hippaul race.
  - *Mechanism confirmed; in-game effect unverified.*
- **High Speed Mode and fast-forward asymmetry.** `HonoBehaviorSystem` runs `MainLoopUpdateCount` logic ticks
  per frame, but `NetSyncClient` is a plain MonoBehaviour on wall-clock ms. F1 / the pause-menu toggle has no
  co-op gate on either role. *Plausible.*
- **The user-facing ~ menu is mostly ungated on a following guest.** Warp, including the flag-reset and
  ScenarioCounter writes, is not a MAPJUMP, so the redirect never sees it. StartBattle boots a *real* local
  battle (`Ff9mkDebugMenu.cs:2389-2440`, `:563-600`). *Confirmed, static.*
- **Concurrent Memoria.ini writers.** The engine's `PersistSessionCode` does a full non-atomic rewrite with
  no lock (`NetSyncClient.cs:1265-1302`). Stock `SaveValue` takes a monitor; the kit writes atomically but
  read-modify-writes. *Confirmed, low.*
- **Checked and found sound:**
  - x86 vs x64;
  - the harness agent in user builds (dormant without its arm file);
  - Journal/Folklore on a guest (the main menu is refused);
  - the ATE menu;
  - a host on a field the guest lacks;
  - the exit ramp with no own save (goes to the title);
  - NetSyncParty parser bounds.

## 3. Roadmap: improving the stock experience

Two research lenses fed this: a *player* walk of disc 1 (Prima Vista → Alexandria → Evil Forest → Ice Cavern →
Dali → Lindblum) as guest and as host, and an *engineering-health* lens. Ranked; S/M/L = effort.

### Tier 0: before the next co-op sitting (all S, mostly one-site fixes)

§1.1, §1.2, §1.3, §1.4, the §1.5 pair, the §1.6 Throw intake check, the §1.7 FollowHost role gate, the §1.9
listener close and bridge eviction backoff, and §1.10.

Only §1.2 and §1.4 need care in the diorama and ending code. Batch the DLL-side ones into one round with one
in-game box each.

### Tier 1: make what exists usable

1. **Make recovery discoverable and refusals audible (S).** F11 / held L3 is documented *nowhere a user
   reads*: no hit in tutorial 17, `ff9mapkit/docs` or `docsite`. Every refusal and teleport decline goes
   only to Memoria.log.
   - Add a short rate-limited toast (never an ETb Dialog, because the s96 lock grabs those), a buzz on
     refused presses (the s121 precedent), and one tutorial paragraph.
   - Held L3 reads `JoystickButton8`, which is **Share on a raw DS4** (COMMS-MENU recon). Read XInput
     `LeftStick` instead.
2. **Peer-engine handshake (M).** An additive state section carrying the engine generation, language and a
   mod-set digest, shown on both overlays and both Co-op tabs, plus WIRE-5's mismatch line on the relay.
   This goes first among the M items because every later item is a DLL both players must take.
3. **Guest traversal: ladders, jumps, carries (M).** 86 stock regions in 38 fields; 75 of them strand the
   guest today. Design, census and rungs → `GUEST-TRAVERSAL.md`.
4. **A disc-1 duo acceptance walk (M).** `tools/harness/duo.py` pairs two real games on one desktop. Drive
   the host with the existing story-trace walkers (`o1_opening.py`, `dali_tour.py`) and record, per beat:
   - what the guest saw;
   - how far behind it followed;
   - which lines closed on a host seq and which orphaned;
   - warm vs cold battle returns;
   - every refusal.

   This turns every prediction here into measured defects before anything is built. Add delay/jitter/drop
   knobs to the duo relay so internet timing can be judged without two homes.
5. **A readable status line (S/M).** Place names via `FF9TextTool.LocationName`, not "field 1050". Host
   activity: "your partner is shopping / saving / playing cards / watching a movie". Section 7's flags byte
   is full, so this needs a small additive section.
6. **Moogles, shops and Mognet (S/M, MISC-06).** The guest's copy skips the menu and sits on "See you,
   kupo!" for the host's whole visit. Park the guest at the `Menu()` opcode (args consumed every pass,
   bounded wait) until the host's HfMenu bit drops.
7. **FMV lockstep (S/M).** There is zero movie handling in Netsync. The host's skip should skip the guest's
   movie, and no follow-warp should fire mid-movie. *Predicted from source; needs one box.*

### Tier 2: story set pieces in lockstep

8. **Scripted boss battles warm (L, high risk; DIO-2).** Every disc-1 boss is a scripted `Battle()`: Baku,
   the Steiner fights, Plant Brain, the Black Waltzes, Sealion, Gizamaluke. The guest's ENCOUNT returns 0
   inline (`DoEventCode.cs:977`), so its copy plays the after-boss scene *ahead of the host*, then
   cold-returns.
   - Park the guest at the opcode until the host's battle ends.
   - Use a bounded fallback to today's path.
9. **Spectator subtitles (M).** Section 7 already carries the host's open `textId`s. Draw an inert box for
   host lines the guest's copy can't reproduce: "Received Potion!", signs, scenes the guest isn't standing
   in. Text variables (`[ITEM]`, `[NUMB]`) are not on the wire yet.
10. **Tread-scene relay (M, owner call).** Walk-in cutscenes only play on the copy whose actor stepped there.
    Promote a host tread start only when the host's scene rises within N ms (the quad-promotion shape).
11. **Doors that behave like doors (M).** Two fixes:
    - a walk-through grace, so the guest can take the host's door on foot;
    - bounce-in-place instead of a reload to the field's default entry when the guest steps into a door
      first.
12. **A minigame policy, one per minigame (M).** For each, watch with a status line or mirror it. Hot & Cold
    cannot work on the guest today (a control-on Special poll), and the §2 swordfight is broken in a
    different way. Also gate MINIGAME 0xAE [30]: a tread-started Treno card match boots a *local* Tetra
    Master on the guest.
13. **The gil/frog/card read mirror (M; DIO-3).** Inns, shops and Stiltzkin branch on gil. The guest's copy
    reads its own gil, so a relayed inn talk can take the "not enough gil" branch while the host sleeps.

### Tier 3: things to do as a guest

14. **A read-only partner menu, then the guest manages its own character's gear (L).** The guest commands
    Vivi every battle but can never look at her. The party sections already reach the guest each load.
    *inventory-authority.md* Road B.
15. **Comms menu (L; designed in COMMS-MENU.md):** pings, quick-chat, emotes, a warp-to-partner entry, and
    a "partner is still reading" mark on the host's window.
16. **Guest flavor talk (owner call).** Same classifier as traversal: 694 stock NPC talks write nothing
    persistent. See GUEST-TRAVERSAL.md §5.
17. **Camera follow (M; deferred by the owner)** on multi-camera fields. It matters more once the guest can
    roam (item 3).
18. **World map: the host's marker on the frozen guest's minimap (M),** then a ride-along later (XL).
19. **B4.2 battle commands (L, v15):** Throw, Change, double-cast, auto-battle, acks, hidden-enemy
    targeting. Bundle it with the comms v15.
20. **Owner-decision items:**
    - the guest keeps a copy of the shared save (via the Workspace, never the Continue slot);
    - head-to-head Tetra Master (XL; needs deterministic card RNG).

### Maintenance

- **Consolidate the netsync stack (L, quiet window).** It is 45,930 lines in 14 files, with 593 hook
  markers in 48 engine files and 54 patches (5.3 MB). Each feature costs a byte-gated capture, and a Memoria
  upstream rebase touches all of it.
- **Re-cut into a few layer patches** (transport, field gates, dialogue, battle, world) only when no netsync
  round is in flight.

## 4. Appendix: every finding

Severity is the reviewer's claim, then each skeptic's corrected severity. `drop` = refuted.

| # | verdict | severity: claimed → each skeptic | reviewer | finding | where |
|---|---|---|---|---|---|
| 1 | conf | high → high/medium | session-save | Behind the bridge, encounter and autosave suppression never ends after the host quits (PEER-ALIVE law broken at the suppress site) | `NetSyncClient.cs:1802` |
| 2 | conf | high → high/high | field-gates | The ending is unfollowable: Field(16000) is always bounced on the guest, and the PreEnding UI state blocks every follow-warp through fields 3000-3012 | `NetSyncClient.cs:439` |
| 3 | conf | high → medium/medium | transport | Direct-LAN host: Stop() never closes the TcpListener, so a live co-op restart leaves a zombie listener and the new host cannot bind | `NetSyncSocket.cs:544` |
| 4 | conf | high → medium/medium | session-save | A session-ending config edit while the guest watches a battle diorama strands it, and the exit ramp then waits on Booted forever | `NetSyncClient.cs:1414` |
| 5 | conf | high → medium/medium | field-gates | A follow-warp racing the guest's own field transition is lost (guest stranded behind a stale _followWarpedTo latch) or replays as a second load | `NetSyncClient.cs:5053` |
| 6 | conf | high → medium/medium | dialogue | Window events keep ageing out while the guest is paused (KEY TTL is frozen, the inbox TTL is not), so later host choices are lost and auto-picked as Cancel/Default | `NetSyncDialog.cs:1053` |
| 7 | conf | high → medium/medium | battle-cmd | Digit-panel 'Throw' (Amarant) is sent as an Instant pick; the host throws item #190 (Maximillian) and can permanently consume it | `NetSyncBattle.cs:5976` |
| 8 | conf | high → medium/medium | diorama | A booted diorama has no exit once co-op is turned off, a transport key changes, or FollowHost is dropped and the link is then cut; the exit ramp also waits on it | `NetSyncClient.cs:1414` |
| 9 | conf | high → medium/medium | world | A guest who pairs on the world map boots the host's world battles seated with its OWN party (the s42 own-party diorama is back) | `NetSyncDiorama.cs:2723` |
| 10 | conf | high → medium/medium | vanilla-inertness | Encounter and autosave suppression key on the bridge hop (IsConnected), not on a live host: a FollowHost guest's own solo game has no random battles and no autosave | `NetSyncClient.cs:1790` |
| 11 | conf | high → medium/medium | kit-python | Bridge redials instantly after the relay deliberately REPLACES its leg: two same-code legs evict each other in a tight loop the engines never see | `netsync_bridge.py:465` |
| 12 | conf | high → medium/medium | kit-python | A UTF-8 BOM in Memoria.ini makes the first co-op setup replace the player's whole mod list with just "FF9Coop" | `coop.py:458` |
| 13 | conf | medium → medium/low | transport | Silent no-pair over the relay: a wire-version mismatch is dropped without a signal, and the host's overlay says 'connected' with no peer at all | `NetSyncRelay.cs:356` |
| 14 | conf | medium → medium/medium | transport | Following guest's encounter suppression keys on the bridge hop (IsConnected), so after a session ends the guest's own save runs with random encounters off | `NetSyncClient.cs:1790` |
| 15 | conf | medium → medium/low | transport | Public relay has no message-size limit or connection caps, so one client can exhaust its memory and drop every live session | `main.go:113` |
| 16 | conf | medium → medium/low | transport | Latest-slot lanes re-send the full 2-5 KB story-state (and roster) every 33 ms, about 0.7-1.2 Mbit/s sustained, which backs up on weak links and through the relay | `NetSyncSocket.cs:355` |
| 17 | conf | medium → medium/low | session-save | The exit ramp reloads an autosave that is older than the pre-session state; the docs claim a capture that does not exist | `NetSyncState.cs:186` |
| 18 | plau | medium → medium/low | session-save | The ending escapes the save guards: the game-finish flag and the CompleteGame/Blackjack achievements reach disk and later Steam | `AchievementManager.cs:85` |
| 19 | conf | medium → medium/low | field-gates | Encounter and autosave suppression key on IsConnected, so behind the bridge they stay on with no live host (before pairing and after the exit ramp) | `NetSyncClient.cs:1790` |
| 20 | conf | medium → medium/low | dialogue | The orphan rule's Cancel pick live-locks the guest on stock forced-choice re-ask loops | `NetSyncDialog.cs:1521` |
| 21 | conf | medium → medium/medium | diorama | A cold field return after a mid-fight leave never stops the battle song; it plays over the restored field song | `NetSyncDiorama.cs:1526` |
| 22 | conf | medium → low/medium | diorama | A wire boot that passes ValidateWireBoot but throws in InitBattleScene sits in a half-built diorama for the whole fight | `NetSyncDiorama.cs:715` |
| 23 | conf | medium → medium/low | vanilla-inertness | Direct-TCP host: Stop() never closes the TcpListener, so disabling co-op leaves port 49200 open and a later live re-enable cannot bind | `NetSyncSocket.cs:544` |
| 24 | conf | medium → medium/low | vanilla-inertness | FollowHost is honored regardless of role: a host with FollowHost=1 follow-warps its real save to the guest's field and suppresses its own encounters and autosave | `NetSyncClient.cs:3691` |
| 25 | conf | medium → medium/low | kit-python | A former guest's stored SessionCode (the friend's invite) is silently reused as this PC's own host code | `coop.py:678` |
| 26 | conf | medium → medium/low | kit-python | CLI `coop join` keeps stale host-side keys (FollowHost=0, GhostAs, GuestSlots), and tutorial 17 says the tab runs a bare `coop join <code>` | `coop.py:186` |
| 27 | conf | medium → low/low | transport | Relay 'replace the stale occupant' plus the bridge's immediate redial livelocks whenever two live clients share a code and role | `main.go:190` |
| 28 | conf | medium → low/low | session-save | A pending exit ramp survives a trip to the title and yanks the player out of the save or New Game they just chose | `NetSyncClient.cs:1459` |
| 29 | plau | medium → low/low | field-gates | The bounce budget's 20 s sliding window cannot stop an auto-transition loop whose period exceeds 20 s | `NetSyncClient.cs:442` |
| 30 | conf | medium → low/low | field-gates | MINIGAME (0xAE) is un-gated: the guest's copy of a story card match (Treno Card Stadium tread) boots a local Tetra Master game | `EventEngine.DoEventCode.cs:2433` |
| 31 | conf | medium → low/low | field-gates | ENCOUNT/ENCOUNT2 on a field still gate on IsMirroringStory, but the F3.1 talk relay now replays host talks on a not-yet-mirroring live guest | `EventEngine.DoEventCode.cs:977` |
| 32 | conf | medium → low/low | dialogue | A handed-back (Local) script-polled line is masked again as soon as the host gets busy, because the key lock is per field, not per window | `NetSyncDialog.cs:1161` |
| 33 | conf | medium → low/low | battle-cmd | Digit-panel target and item picks are index-based and re-derived at keypress; a death or count change between draw and press lands the pick on another unit (friendly fire) or another item | `NetSyncBattle.cs:4741` |
| 34 | conf | medium → low/low | world | A field guest paired while the host is off-field arms the host's story on its first warm diorama return: Main_Reinit runs the guest's own-story field with the host's flags | `NetSyncClient.cs:716` |
| 35 | conf | medium → low/low | ghost-dress | The wire position is the player's LOCAL transform, which is bone-local while the player rides something (Fossil Roo Gargant), so the peer's ghost jumps to the field origin | `NetSyncClient.cs:1749` |
| 36 | conf | medium → low/low | ghost-dress | DriveGhost's AnimationDB.GetValue throws on an unknown wire anim id, every frame, aborting the rest of NetSyncClient.Update while the players share a field | `NetSyncClient.cs:9093` |
| 37 | conf | medium → low/low | kit-python | The bridge binds with SO_REUSEADDR on Windows, so a second bridge co-binds 49201 and the GUI's 'port in use' branch is dead for the common case | `netsync_bridge.py:778` |
| 38 | conf | medium → low/low | kit-python | Workspace 'Disconnect' closes only the listening socket: the live game<->relay session keeps running while the tab says 'not connected' | `coopdoc.py:544` |
| 39 | conf | medium → low/low | kit-python | 'Apply now' trusts the role radio, not the live ini: on a paired guest it writes FollowHost=0 and the host's dress keys, which ends the guest's session | `coopdoc.py:553` |
| 40 | conf | medium → low/low | kit-python | `coop --rebuild-room` with field 30003 registered in another active folder builds and registers a SECOND 30003 (cross-folder EventDB collision) | `coop.py:495` |
| 41 | conf | low → low | transport | FIFO lanes are not loss-proof through the bridge or relay (docs say 'latest-state, harmless'), and command frames carry no battle id, so a queued pick can land in the next battle | `netsync_bridge.py:562` |
| 42 | conf | low → low | transport | Bridge binds with SO_REUSEADDR, which on Windows lets a second bridge silently co-bind 127.0.0.1:49201 and defeats the Workspace's port-in-use error | `netsync_bridge.py:778` |
| 43 | conf | low → low | session-save | The ~ snapshot taint exemption checks the CURRENT role, so a co-op-tainted snapshot restores after a switch to Role=selftest, which has no save gate | `Ff9mkDebugMenu.cs:2901` |
| 44 | conf | low → low | session-save | Guest-driven co-op cells are saved into the HOST's permanent save and read as a phantom peer once co-op is off | `NetSyncClient.cs:1829` |
| 45 | conf | low → low | session-save | FollowHost is not role-gated in the engine, so a host with FollowHost=1 follows its guest and silently loses its own autosaves and encounters | `NetSyncClient.cs:3691` |
| 46 | conf | low → low | field-gates | Teleport-to-host snaps onto any triangle at the host's XZ (GetTriIdxAtPos ignores the active-triangle flag), including ones the guest's copy has disabled | `NetSyncClient.cs:8566` |
| 47 | conf | low → low | field-gates | The spectator guest still gets the stock talk/'!' prompts for interactions it can never start, and the refusal is silent | `EventCollision.cs:111` |
| 48 | conf | low → low | field-gates | Ladders, jumps and platforms are blocked for the guest by the blanket quad gate, although a mover-only guest lane is cheap and authority-safe | `EventCollision.cs:74` |
| 49 | conf | low → low | dialogue | Advanced() consumes a host CHO on a promise: the global VoicePlayer.closeDialogOnFinish, which any other window's Hide clears | `NetSyncDialog.cs:1291` |
| 50 | conf | low → low | dialogue | Cross-language pairs are 'unsupported' only on paper: the JP Confirm/Cancel swap inverts relayed script keys silently | `NetSyncClient.cs:5607` |
| 51 | conf | low → low | dialogue | The authoritative patch README rows for s96, s98 and s99 contradict themselves on proof status | `README.md:84` |
| 52 | conf | low → low | battle-cmd | Host intake trusts the guest's menu class, item id, mask and cursor: a modified guest can consume host equipment or hit all targets at single-target strength | `NetSyncBattle.cs:6049` |
| 53 | conf | low → low | diorama | The reconciler applies whatever battle the peer view holds, without checking it against BootedWireNonce | `NetSyncDiorama.cs:3036` |
| 54 | conf | low → low | diorama | The reconciler's design header still documents MISSING-AS-DEAD, which the code removed | `NetSyncDiorama.cs:2983` |
| 55 | conf | low → low | world | World dioramas seat a party snapshot from the last FIELD load, never refreshed across world battles | `NetSyncDiorama.cs:2736` |
| 56 | conf | low → low | world | The frozen guest's world overlay says 'Rejoining' when no rejoin can arm, and gives no way out when the host is on a field this install lacks | `NetSyncClient.cs:4713` |
| 57 | conf | low → low | world | The world rejoin and watcher allocate strings and walk the object list every frame while they wait | `NetSyncClient.cs:4073` |
| 58 | conf | low → low | ghost-dress | The peer's submesh mask comes from a cached renderer list that includes held props and is never refreshed, so the ghost hides or shows the wrong submeshes | `NetSyncClient.cs:9053` |
| 59 | conf | low → low | ghost-dress | Memoria DIALOG text patches read SpeakerModelId / SpeakerAnimationId off the dressed body, so a model-keyed patch renders Zidane's lines differently on the guest's screen | `TextPatcher.cs:131` |
| 60 | conf | low → low | ghost-dress | The wire loco byte classifies Zidane's walk and run by exact slot id, so a host-dressed 98 ghost glides in idle on every variant or alias walk | `NetSyncVisitor.cs:207` |
| 61 | conf | low → low | vanilla-inertness | A mistyped Role (e.g. 'guest') fails OPEN into the selftest bench in the user's real game, though the docstring says a typo fails closed | `NetSyncClient.cs:1499` |
| 62 | conf | low → low | vanilla-inertness | The engine rewrites the whole Memoria.ini non-atomically, with no backup, to persist a minted session code | `NetSyncClient.cs:1302` |
| 63 | conf | low → low | kit-python | 'Turn co-op off' or 'Apply now' during a running setup job is overwritten when the job finishes, and done() starts the bridge anyway | `coopdoc.py:564` |
| 64 | conf | low → low | kit-python | `coop show` and the Workspace report a missing Role as 'host' while the engine runs the selftest mirror | `coop.py:547` |
| 65 | drop | low → low | ghost-dress | The ghost skips stock's per-actor depth gate and per-field render-queue fixes, so it draws where stock would hide or re-order a character | `NetSyncClient.cs:8929` |
| 66 | drop | low → none | transport | Sender never enforces MaxPayload, and an oversized frame is reported as a wire-version mismatch (endless reconnect on TCP, a silently stale lane on the relay) | `NetSyncSocket.cs:166` |
| 67 | drop | low → none | dialogue | The talk relay permanently declines (consumes the nonce) when the NPC object has not spawned yet on the guest's copy | `NetSyncClient.cs:6794` |
| 68 | drop | low → none | battle-cmd | Guest-issued commands lose their command menu (cmdMenu None) and are validated with command/menu None, unlike the same pick made locally | `BattleHUD.Unity.cs:662` |
| 69 | drop | low → none | ghost-dress | EnsureGhost's catch drops a half-built ghost GameObject without destroying it, and the caller retries every frame | `NetSyncClient.cs:8964` |
