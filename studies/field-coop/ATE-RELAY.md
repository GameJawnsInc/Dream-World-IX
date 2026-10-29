# The ATE relay (engine patch s161)

The owner's report from the 2026-10-28 two-PC session: "no ATE dialogue boxes/titles when the host picks one (the
bottom-left notification that an ATE is available does show on the guest, just not the options or transitionary title
box)". The cause is traced in `GUEST-TRAVERSAL-TWO-PC.md`, "For later patches", second bullet. This document is the
design for the fix, and records how it was built and checked.

Round order (the shared round queue): s159 is the step-out anchor fix, s160 the chest relay, s161 this relay. Nothing of
s161 touches the shared clone `C:\gd\FFIX\Memoria` until s160 is released there.

## What goes wrong today (2026-10-28 logs, `.harness-runs/twopc-s158-20261028/`)

1. **The menu never opens on the guest.** 352's ATE menu lives in Code1's per-frame loop:
   `if (IsMovementEnabled == 1 && byte238 == 1 && IsButton(Select)) { DisableMove; EnableDialogChoices; WindowSync(1, 64, 98); switch (GetDialogChoice) ... }`
   (`test2_95.txt:270`). The host's press is a control-ON read. The host relays only control-off reads
   (`NetSyncClient.TapScriptKeyIfHost`), and the guest masks its own Select on control-on reads on purpose (MISC-08,
   `NetSyncField.ControlOnScriptKeys`). So the guest's copy never opens window 98, and the branch's white fade and title
   (text 100, "Vivi, Confused") never run there. The host's choice event for window 98 (seq 59) and its title close
   (seq 60) waited in the guest's inbox and were dropped when the guest followed to 350.
2. **The follow carried the guest to 350 instead of its own script.** The host's `Field(350)` sent a transition intent;
   the guest followed at once (`ServiceIntentFollow`). It still played the ATE on 350, because the follow lands with the
   host's story snapshot (entrance 16).
3. **The ATE's closing lines on 350 were dropped.** The host played texts 324, 325, 324 and left within 2 s (the host
   ran faster than 1x; Finding 4). The guest's copy had not reached them when the intent back to 352 arrived; the follow
   fired and the inbox purge dropped seq 63-65.

## The census (who reads Select with control on)

Two independent counts agree:
- **The HW text exports** (817 field scripts): 1,152 Select reads. 305 are control-on (`IsMovementEnabled == 1` in the
  same condition), in 150 fields, and **every one of them gates an ATE menu**: a `WindowSync(w, 64, t)` with
  `EnableDialogChoices` within the next lines. The other 847 are control-off waits: 837 `while (!(IsButton(Select) ||
  IsButton(Start)))` skip-waits inside ATE scenes, 206's tutorial `while (!IsButtonDown(Select))`, and the Chocobo's
  Forest moogles' dig menu (2950-2952). Those already ride s99's control-off KEY relay.
- **The install's `.eb` bytes** (the kit's disassembler, US field scripts): see "Census, second count" below.

So the control-on Select poll is the ATE menu's gate and nothing else. MISC-08 does **not** need widening: the guest's
own Select stays masked; only the host's relayed press is added.

## The design

### Host: relay the press only when it opened the host's own ATE window

- `TapScriptKeyIfHost`'s control-on branch notes a Select hit: the reader's uid (gExec), the field and the key tick.
  The raw read is not relayed: `&&` does not short-circuit in the field VM, so the `IsButton(Select)` read runs every
  frame whatever the gate says, and a press with the ATE unavailable opens nothing.
- `ETb.NewMesWin` (one hook line, behind a static armed flag) sees every window open. When a window with the ATE caption
  (`flags & winATE`) opens, and the object running the script (gExec) is the reader that hit Select within the last two
  key ticks on this field, the host appends a new ring event, **kind 3 = ATE PRESS**: `[uid][menu text id][menu window
  id][the menu's cancel row]`. That is the host's own menu actually opening. The title card (text 100) is opened by the
  same reader seconds later, past the two-tick window, and a compulsory grey ATE's title has no Select hit at all:
  neither is relayed.
- The tap-record bench (`netsync tap-record 1`) records the event to the tape like every other tap.

Wire: section 7's ring, v14 unchanged. An older guest logs "unknown kind 3 -- ignored" (`NetSyncDialog.IngestRing`)
and behaves as today. An older host never sends kind 3.

### Guest: serve the press to the same reader until its own menu opens

- The ring merge hands a kind-3 event to the ATE relay as a PENDING PRESS: field, reader uid, the host's menu (window,
  text, cancel row), the seq.
- `FilterScriptButtons`' control-on branch (field mode only, not the world map) ORs `Select` into the read when the
  reader is the pending press's uid, the field matches, and the read's mask asks for Select. MISC-08's mask still
  removes the guest's own Select first.
- **Served, not consumed.** A served key is spent whether or not the guest's gate is true, so one serve proves nothing.
  The press is served to that reader on every key tick until the guest's own ATE MENU opens (the `NewMesWin` hook on
  the guest: the ATE caption on a choice window, opened by that uid on that field; a title card never retires a press),
  then retired. Success is proven by the lock's own "win 1 text 98 opened locked" line and the relay's "opened my
  copy's ATE menu" line, never by a serve count.
- **The press's life** (pure rules `PressKeep`, `PressHoldsEvent`, `PressRoundTripOver`, `PressLanding`,
  `PressExpiry`):
  - kept while its field is mine, my follow-warp's or the host's, or while the host's field is unknown (a relay blip
    reads -1, a load reads 0); meanwhile the inbox keeps the host's later events for that field (its pick and title
    close), so the press and its answer live and die together;
  - kept across a landing on its own field (a chained ATE: the guest still in the last ATE's tail on 350 while the
    host, back on 352, opens the menu again), dropped by a landing anywhere else;
  - dropped once the host has left its field for a real field and stood on it again: the host's ATE is over, and a
    menu opened now would replay it with the host's later entrance;
  - dropped when the dialogue session goes off (the inbox and its baseline are gone, so its answer cannot arrive);
  - expired 5 s after the first tick I stand on its field with my control on (a long control-off arrival or tail does
    not use it up), and 20 s after it arrived in any case.
- **One press at a time, and no stale choices.** A newer press replaces an older one. When the guest's menu opens, every
  queued event for that window key older than the press is dropped (`NetSyncDialog.DropStaleChoices`): it answered a
  host menu this copy never opened (the host cancelled and re-opened while the guest lagged), and the lock would
  otherwise hand it to this menu first.
- Once the menu is open it is an ordinary locked choice: the host's CHO event picks the row, its title is locked and
  closes on the host's close event. **If the host's row is masked on the guest's menu** (its availability mask
  diverged), a census-shaped menu (Cancel on its own row 15) closes with Cancel instead of its default row: the default
  is another ATE the host never picked, whose title, fade and `Field()` would play on the guest alone. Any other menu (a
  kit `[ate]` with no decline row) keeps the stock fallback.

### The episode: let the guest's own script carry it to the ATE and back

From the moment the guest's copy opens its ATE menu from a relayed press, the guest is in an **ATE episode**:
- **The pick.** The lock closing the menu on the host's EXACT row is the host's pick (not the masked-row fallback). A
  Cancel or Leave row is not told apart by its index (a kit menu with no decline row puts Cancel on a real row): the
  pick LAPSES the first tick the guest's control is back, because such a branch hands control back, while a branch that
  jumps never does before its `Field()`.
- **Hub phase** (on the menu's field). While the pick stands:
  - **The own jump passes.** The copy's own `Field(dest)` passes `RedirectGuestFieldJump` (one line, "my copy's own
    Field(dest) passes: the host's pick"). Before s161 it could bounce: the host's position lane reads field 0 while it
    loads 350, so `dest == LastHostField` fails and the guest would reload 352 first (the double load the brief
    forbids). The check runs before the `dest == myField` pass, so a same-field ATE records its own jump too. It keeps
    the copy's own entrance (16) through the landing's mirror, so a late copy whose host already wrote a later entrance
    still plays the ATE.
  - **The follow holds** while my control is off, up to 8 s counted from the title card's close (an open title card
    restarts the clock, at most 20 s after the pick): the host's intent toward 350 would otherwise black-fade over the
    guest's own white fade and title. One line per held destination.
- **Destination phase.** At the next field load, if it is the own jump's destination, the episode moves there (a
  same-field ATE lands on the same id: the landing, not the id, decides). There the follow holds while my control is
  off and its copy keeps making progress on the ATE field (the landing, a host line applied, a window opened) within 8 s,
  at most 30 s from the first held tick: Finding 4's capped follow-hold, scoped here to the ATE episode and counted by
  progress (a 3x host announces its departure long before the guest's last line). The guest's copy shows 324/325 from the
  host's events, runs its own fade and music load, and takes its own scripted `Field()` out:
  - a press waiting on that destination with its pick queued (a chained ATE) keeps the jump on course;
  - else it goes where the host is (its announced field, else the field it stands on, if this install has it), but never
    back into the ATE field itself while the host has not left it since the guest's landing: the host is still in this
    ATE and the guest's exit just beat the host's intent frame;
  - else it takes its own destination.
  Every pass that is not rewritten keeps the copy's own entrance through the landing's mirror (350's tail writes 17 for
  352, or 17 for its own reload on a same-field ATE, while the host's mid-tail snapshot still says 16 and would replay the
  ATE). When the exit beat a host still in the ATE, the **exit hold** keeps the follow out of the ATE field until the host
  stands on another field (at most 20 s): without it the serial follow pulled the guest straight back into the ATE field
  with the host's entrance 16, replaying the ATE. "Still in the ATE" means the host has not left the field since the
  guest's landing AND still carries the entrance the guest's ATE ran on (stock writes the tail's entrance on the frame of
  its own `Field()`); a host that walked back in by a gateway does not arm it. While it stands, the guest's own jumps (a
  walk into the held field, a bounced gateway) keep their own entrance, since the host's snapshot still says 16. A gateway walk is never the ATE's own exit: control on, or a region runs
  the jump (every stock and kit gateway runs `ExitField` first, so control alone never tells it). Any line open on the ATE
  field counts as progress until it leaves, and the tail's clocks stop while the link is down or the host is stalled.
  It is never bounced into a reload of the ATE field. A rewrite seeds the host's entrance and commits the move, as the
  world redirect does. A first cut also required "a host event for my field still waiting", as Finding 4 words it; that
  let the follow's black fade cut the last second of the ATE, after its last line and before its own `Field()`.
- **A chained ATE.** When the host finishes first, returns to the hub, opens the next ATE and leaves for it while the
  guest is still in the last one, the guest's pending press is dropped (neither copy is on its field). If the host's pick
  for it was already queued, the drop records the host's new field: the guest's own exit is rewritten there (with the
  host's entrance, so the ATE plays), and that landing carries the episode, so the second ATE's tail keeps its hold and
  the never-reload rule. The guest misses only the second menu, its title and its white fade. Routing the guest back
  through the hub to open the menu was rejected: the hub's landing would mirror the host's mid-ATE story, which can clear
  the menu's gate.
- **Before the pick** (a late guest: its control came back after the host already picked and left). PREPICK: while its
  menu is open (control off) and the host's pick for it is already queued and is not that menu's cancel row, the
  follow waits, up to 2 s from the menu's open (the open tween, MinShowMs and IsChoiceReady). PENDING: while a press
  waits on the guest's field and its pick is queued (not the cancel row), the follow waits, up to 5 s from the first
  held tick; this row also applies beside a live episode (a newer press after a Cancel, a chained ATE). The intent
  fast-path also waits one Update whenever ring events have arrived but are not merged yet, so a press and its pick
  that ride the same frame as the host's intent (after a lane stall) are seen first.
- **The end.** Any other field load, the second landing (unless it is the chained ATE's), my control back for 1 s (the
  host picked Cancel, or the scene ended in place), a session reset, or the lever. The exit hold outlives the episode and
  ends on its own. Not an epoch change: a host's transport reset mid-ATE still runs the
  picked branch, and the keep rule drops a real relaunch's press on its own.

The caps keep every hold bounded: a guest copy that diverged gets today's follow after 2-8 s.

**The hub pass is destination-blind on purpose.** A rule that also required `dest == the host's announced field` was
considered and dropped: the guest's own `Field(350)` and the host's intent frame are produced about 5 frames apart, so the
own jump can run before the intent arrives, and the stricter rule would then bounce it into a 352 reload, the double load
the brief forbids. The exact pick, standing only while control stays off, is the guard instead: the guest's copy runs the
host's case on the host's mirrored state.

### The step-out on the ATE menu: no

The s158 step-out would fire on the guest's menu (a fresh line with control off), darken a dressed guest and show a
Zidane stand-in for as long as the host browses the menu. On s158 the host's option C also hides the guest's ghost while
the host's own menu is up (that menu is a fresh line on the host). The menu and the title card are system captions over a
still room, not a party scene. So, on BOTH screens, for the RELAY'S OWN captions only (the guest's hub phase on its
field; on the host, the relayed menu's field until the next load):
- an ATE-caption script window (lockable, `Dialog.CapType == ActiveTimeEvent`; a pooled UI dialog can keep a stale
  caption type, so the caption alone is not enough) is never a fresh line (`NetSyncWindowSnapshot.AnyFresh`, shared by
  the guest's start rule and the host's option C). A behaviour change on the host: from s161 the guest's ghost stays
  visible while the host browses its ATE menu and reads the title card;
- while one is open on my copy, the step-out's base does not hold (a new term, "an ATE caption is open"), so the dwell
  cannot start it either;
- an active step-out steps in when the guest's ATE menu opens (a new reason, "ate": the guest's control came back under
  the step-in debounce and the served Select reopened the menu at once).
On the host the latch ends the first frame its control is back (a Cancel or Leave row), as well as at the next load.

Any other ATE-caption window is an ordinary line: a kit compulsory-ATE cutscene (`[cutscene] ate = true`) gives every
line the ATE caption, and those scenes keep the step-out. The scene on the destination field is an ordinary scene.

### Same-field ATEs (the 71 `Field(own)` rows)

The guest's own `Field(own)` already passes (`dest == myField`), and the host's same-field intent is dropped by both
sides, so each copy reloads once. The episode records the own jump before that pass and moves to the destination phase
on the reload's landing. The record (`NetSyncAte.OwnReloadLanded`) is what Finding 5's landing dedup will read when the
host's own reload is relayed; nothing in s161 reloads a field for the host.

### Beside s160's chest relay

s160 (the chest relay, built before this round) arms in the same `TapScriptKeyIfHost` control-on branch and serves in
the same `FilterScriptButtons` control-on branch. The two serves stay separate on purpose: s160's is one-shot (a chest's
tag-2 poll), while the ATE press must be served on every key tick until the guest's own menu opens, because the guest's
gate (its control, byte 238) can be false at the first read and a served key is spent either way. On the wire there is
no overlap: s160 rides a new state section (9); s161 is ring kind 3.

### The lever and the reads

- `netsync ate act|off|noexempt|clear` (selftest role, released with the harness): `off` = the whole relay off on this
  copy (no host arm, no serve, no own-jump pass, no hold, no exemption: the s160 rule); `noexempt` = the relay on, the
  step-out exemption off.
- `netsync.ate` (the harness state's netsync LAST key): the lever, the pending press, the episode phase and flags, and
  cumulative counters (relayed, served ticks, opened, expired, own jumps passed, holds).
- `NetSyncAte.SelfTest` rows for every pure rule, each with a mutant, in the selftest block after s160's chest relay line
  (the block's last line).

## Pre-build review, round 1

One reviewer read the first cut (three lenses: the relay and episode, the netsync machinery around it, vanilla/host/solo
safety) and reported ten findings. Each was then checked by two verifiers with different lenses (a code trace; real-play
reachability plus an attack on the proposed fix). All held at least in part; three proposed fixes were rejected by a
verifier and replaced:

| # | Finding | Verdict | Resolution |
|---|---|---|---|
| F1 | A chained ATE's press, or one that arrives while the guest follows onto its field, is lost (expired on a field mismatch, dropped at every landing) | confirmed, reachable | The keep / landing / expiry rules above. A first fix (an on-field TTL alone) lost in-place chains and could outlive the choice event; replaced by the inbox's own retention rule plus a control-on live clock |
| F2 | The hub pass is destination-blind and `by_host` was set on the masked-row fallback and on Cancel | confirmed (precondition rare in mirrored play) | `by_host` only on an exact, non-Cancel pick; a masked host row closes with Cancel. The proposed "dest must match the intent" clause was dropped (see above) |
| F3 | Nothing holds the follow before the pick lands | confirmed | The pending / pre-pick holds above, narrowed to "the host's pick for this menu is already queued and is not Cancel", plus the one-Update ring deferral |
| F4 | A newer press drops an unopened one, and the lock then hands the earlier menu's Cancel to the guest's only menu | confirmed | Drop the menu key's older choice events when it opens. A FIFO of presses was rejected: it replays every cancelled menu and still misaligns after an expiry |
| F5 | An epoch change does not reset the relay | partly: harmless on a relaunch | No reset (it would break a host reconfigure mid-ATE); the comment now says so |
| F6 | A pooled UI dialog with a stale ATE caption suppresses the step-out | confirmed | Require a lockable (script) window |
| F7 | The hold allocated a string every held frame; the intent was read every frame | confirmed | Two Int32s for the log dedup; the intent is read only at a jump |
| F8 | `OwnReloadLanded` was never cleared | confirmed | Cleared at the episode's end and published only while the destination phase lives |
| F9 | The tap-record pass was not limited to field mode | confirmed (bench only) | `gMode == 1` |
| F10 | Host option C no longer hides the guest's ghost during the host's ATE menu | intended | Stated as a behaviour change above |

The self-test grew to 83 rows and 26 mutants. It now also runs OFFLINE: the built `Assembly-CSharp.dll` loads under
PowerShell's .NET Framework with an assembly resolver pointed at the game's `Managed` folder, and
`NetSyncAte.SelfTest`, `NetSyncStepOut.SelfTest` and `NetSyncDialog.SelfTest` are invoked by reflection (all three
pass: 83/26, 37/12, and the dialogue proof). The pure rules touch no Unity state, so no game is needed.

## Pre-build review, round 2

Three finders read the revised diff (the new state machine; the seams with the existing netsync code; safety and cost),
then two verifiers checked each finding. Ten findings, all at least partly confirmed; where a verifier rejected the
proposed fix, the better fix was taken:

| # | Finding | Resolution |
|---|---|---|
| R2-0 | A newer pending press got no hold while an older episode lived (a Cancel and re-press, a chained ATE) | The PENDING row also applies beside a live episode, after the episode rows (never stacking ahead of them) |
| R2-1, R2-7 | In the destination phase the copy's own jump back bounced into a reload of the ATE field when the host had already left the hub (a 3x host) | The scripted jump goes where the host is (announced field, standing field, else the hub); a gateway walk (control on) is not touched |
| R2-2 | A very late copy's own jump landed with the host's later entrance and lost the ATE | A press whose host made a round trip off its field is dropped (the host's ATE is over) |
| R2-3 | PREPICK shared PENDING's clock and could cap in the half second before the queued pick applied | PREPICK has its own 2 s clock from the menu's open |
| R2-4 | The press could outlive its answer (the inbox's field rule dropped the pick while the keep rule tolerated an unknown host field) | The inbox keeps the pending press's later events for its field; the press drops when the dialogue session goes off. Dropping the blip tolerance instead was rejected: it loses a chained press on a 2 s relay blip |
| R2-5 | The hub hold timed out 8 s after the pick while the host still read the title card | An open title card restarts the clock, capped 20 s after the pick |
| R2-6 | An active step-out stayed out through the menu and title | Step in on the menu's open (reason "ate") |
| R2-8 | The caption exemption covered every ATE-caption window, so kit compulsory-ATE cutscenes lost the step-out | Only the relay's own captions are exempt |
| R2-9 | Kit `[ate]` menus have no fixed Cancel row 15 | Any exact pick, lapsing with control back; the cancel row travels in kind 3's fourth byte and is read per menu; the Cancel fallback only on the census shape |

The self-test grew to 108 rows and 37 mutants (offline: all three self-tests pass). The rows name each earlier rule a
round rejected, and a mutant restores it, so a regression to a first cut reds the proof line.

## Pre-build review, round 3

Three lenses again: the round-2 fixes themselves; regressions outside the ATE; and an end-to-end dry run of the real
352 -> 350 -> 352 sequence (host at 1x and at 3x) and of both benches, row by row. Eleven findings, two verifiers each:

| # | Finding | Resolution |
|---|---|---|
| R3-0, 3, 8 (high) | Round 2's destination rewrite sent the guest's own exit back into a reload of the ATE field while the host was still in it (the guest's `Field(352)` beat the host's intent frame; the host lane read 350) | Never route back into the ATE field unless the host has stood there since the landing and then left it (`EpHostStep`); with nothing better known, the copy's own destination with its own entrance |
| R3-1 | A kit menu's reported cancel row is a real ATE, so the pre-pick holds never fired there | Only a census-shaped Cancel (row 15) holds nothing; on any other menu every row holds (a Leave row costs a late guest at most 5 s) |
| R3-2 | The destination rewrite could route away from a field where a chained press waited | A press waiting on the destination with its pick queued keeps the jump on course |
| R3-4 | The kit harness still pinned round 1's proof line and step-out reasons | The kit rung follows the final engine (below) |
| R3-5 | The host's caption latch lasted until the next load, so a later kit compulsory-ATE scene on that visit lost option C | The latch ends the first host frame its control is back |
| R3-6 | The step-out reads ran unguarded in host-only play | Both answer at once when nothing is armed |
| R3-7 (high, bench) | The duo bench poked the host's gate before the warp, and 352's own load wipes it | Gate after both copies settle (host last), read the bytes back through watched story bits, and prove the load wiped them first |
| R3-9 | The tail hold's 8 s cap ran from the host's departure, so a 3x host still cut the closing lines | The tail counts by progress (8 s since the last line or window), 30 s overall |
| R3-10 (bench) | No bench row tested the host half of the caption exemption | Duo row D9: the host's `host_plain_scene` stays false through its menu and title, and its `ate.stepout_exempt` reads true at the menu |

The self-test grew to 122 rows and 43 mutants. The offline run caught a gap the row tables had: a mutant restoring
round 1's fixed "row 15 is Cancel" rule survived every row until a row with row 15 on a kit menu was added.

## Pre-build review, round 4

Round 4 read only the round-3 changes, with two lenses: the round-3 fixes themselves, and an end-to-end walk of the
352 -> 350 -> 352 sequence with the host and guest at different speeds. Seven findings, two verifiers each:

| # | Finding | Resolution |
|---|---|---|
| R4-0 (medium) | The guest's own exit to 352 while the host was still on 350 left nothing holding the follow: it pulled the guest back into 350 with the host's entrance 16 and replayed the ATE (reachable on menu ATEs whose tail after the last line is long; 350's is under the follow's debounce) | The exit hold, kept inside the relay (the s144 world hold is untouched): armed on that exit, it holds follows into the ATE field until the host stands elsewhere, 20 s at most |
| R4-1 (low) | A host field this install lacks dropped the jump to the old bounce, a reload of the ATE field | An unusable field is skipped; the jump falls through to its own destination with its own entrance |
| R4-2 (low) | A late guest that never saw the host on the ATE field cannot read its later departure | No change to `EpHostStep`: the proposed "start at Seen" reopens R3-0 for a guest that lands while the host's lane still reads the hub. The hub pass now keeps the copy's own entrance, so a late copy plays its ATE; the leftover is one extra load |
| R4-3 (low) | The "control on = a gateway walk" test never matches, because every gateway runs `ExitField` first | A region-run jump (the executing object is a region quad) is a gateway too; a debounced control latch was rejected because kit cutscenes hand control back for two frames at their landing |
| R4-4 (medium) | A same-field ATE's own exit landed with the host's entrance 16 and replayed the ATE | Every pass that is not rewritten keeps the copy's own entrance (the hub pass too) |
| R4-5 (medium) | A chained ATE's press was dropped once the host stood on the next ATE's field, so the guest landed in it with no hold for its tail | The chain carry above. Keeping the press alive through the tail was rejected (it widens every clock and mirrors a mid-ATE story into the hub) |
| R4-6 (low) | A link outage spent the tail's progress clock, so the follow cut the closing lines as the link came back | The tail's clocks stop while the session is not live; an open line counts as progress until it leaves |

The self-test grew to 146 rows and 53 mutants (offline: 146/53, step-out 37/12, the dialogue proof). The new rules
(`JumpUsable`, `OwnEntranceRule`, `ExitHoldArms`, `ExitHoldEnds`, `ChainRecords`, the chained `LandingStep`) each have
a mutant restoring round 3's behaviour.

Not bench-proven: the exit hold and the chain need a guest ahead of its host, or a host that finishes one ATE and
starts the next while the guest is still in the first. Neither bench drives two speeds. Both are covered by the
self-test rows only, plus the two-PC checklist's "guest ahead" line.

## Pre-build review, round 5

Round 5 read the round-4 diff and the rebase onto s159 + s160 rev 3, with one finder per lens, then verifiers. Four findings,
all low:

| # | Finding | Resolution |
|---|---|---|
| R5-0 | While the exit hold stood, the guest's own walk into the held field passed through the follow allowance and landed with the host's entrance 16 (the ATE replayed); any bounced gateway's reload took that 16 too | While the hold stands, the guest's own jumps keep their own entrance. Bouncing the walk instead was rejected: the bounce reloads the hub with the host's 16, which on 350 stages "Vivi, Confused" |
| R5-1 | The exit hold also armed for a late copy whose host had walked back into the ATE field by a gateway: the guest was stranded on the hub for up to 20 s with nothing to protect | The hold arms only while the host's entrance is still the one the guest's ATE ran on (read once at the jump; unknown on either side still arms). A census of the HW exports: 23 of 7,177 entrance-then-`Field()` pairs have any wait between them, none in Dali |
| R5-2 | Since s160 every chest accept runs the relay-accept purge, which could drop the pending press's queued answer; the chest serve and the ATE serve can then fire in one key tick | The purge spares the pending press's own menu key (newer than the press), not its whole field. NOT done: making the ATE serve yield to a chest or talk start accepted on the same field. Its reach is unverified (it needs control to come back from an object that runs after the menu's code entry) and it would read s160's private serve state; the cost is a relayed chest or talk the guest's copy misses while a cancelled menu flashes |
| R5-3 | The kit rung still pins s158's order (`stepout`, `ate`); with s160 the engine's order is `stepout`, `chest`, `ate`, and the AppendAte header said "after `stepout`" | The engine comment is fixed; the kit re-pins after s160's kit reaches master (the merge order: s160's branch into master, then master into this branch) |

The self-test grew to 156 rows and 58 mutants (offline, on the rebased tree: 156/58, step-out 44/15 with s159's rows, the
dialogue proof).

## Census, second count

The kit's disassembler over the install's 818 US field `.eb` binaries (`ebsrc.write_source`, every `B_KEYON` / `B_KEY`
whose constant mask has bit 0): **596 Select reads; 150 control-on (`B_SYSVAR[2] const(1) B_EQ` in the same
expression), one per field in 150 fields, every one followed by a winATE window and `EnableDialogChoices`**; 445
control-off `B_KEYON` reads and one `B_KEY` (206's tutorial wait). The HW exports hold each script twice, which is why
their totals are about double (1,152 / 305); the field count (150) and the verdict match. Scripts:
`census_select.py` (HW text) and `census_select_eb.py` (bytes), in this round's scratchpad.

## Status

**Built, deployed and solo-benched (2026-10-28).** `memoria-patches/s161-netsync-ate-relay.patch`, live `Assembly-CSharp.dll`
`f42f0c051302b459` (revert to s160: `py tools/restore_memoria_dll.py 20261028-163601`), rebased onto s159 + s160 rev 3.
- `coop_ate_relay.py` 14/14 on the shipping rule. `COOP_CALIBRATE=1` (`ate off`): exactly T-TTL, P-QUEUE, P-MENU, P-PICK,
  P-TITLE, P-JUMP, P-LAND, S1 red, each with its marker. `COOP_CALIBRATE=noexempt`: exactly S1 red.
- The live proof line: "ATE relay selftest: OK (156 rows, 58 mutants caught, ...)".
- The duo bench (`coop_ate_relay_duo.py`, two real games, 352 -> 350 -> 352 at 1x): 22/22 -- the menu, the pick, the title,
  the own jump with one load, the ATE and its closing lines locked to the host, the own way back with the follow held and
  never fired, no step-out over a caption, the host's option C. Its s160 calibration (the live DLL swapped to s160 for
  the run, then s161 restored byte-exact): 17/23, exactly D1, D2, D3, D4, D7, D9 red, as predicted. On s160 the follow
  carries the guest to 350 with the host's entrance, so its copy still plays the ATE there (D5, D6 green): the
  menu, the title, the own exits and the host's option C are what s161 adds.
- Next: the owner's two-PC check on 352, in the combined s159 + s160 + s161 session (the checklist is in the round queue
  note). Not proven by any bench: the exit hold and the chained-ATE carry (a guest ahead of its host), and round 5's
  deferred serve yield.
