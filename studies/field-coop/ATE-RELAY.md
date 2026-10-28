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
  id]`. That is the host's own menu actually opening. The title card (text 100) is opened by the same reader seconds
  later, past the two-tick window, and a compulsory grey ATE's title has no Select hit at all: neither is relayed.
- The tap-record bench (`netsync tap-record 1`) records the event to the tape like every other tap.

Wire: section 7's ring, v14 unchanged. An older guest logs "unknown kind 3 -- ignored" (`NetSyncDialog.IngestRing`)
and behaves as today. An older host never sends kind 3.

### Guest: serve the press to the same reader until its own menu opens

- The ring merge hands a kind-3 event to the ATE relay as a PENDING PRESS: field, reader uid, the host's menu (window,
  text), the seq.
- `FilterScriptButtons`' control-on branch (field mode only, not the world map) ORs `Select` into the read when the
  reader is the pending press's uid, the field matches, and the read's mask asks for Select. MISC-08's mask still
  removes the guest's own Select first.
- **Served, not consumed.** A served key is spent whether or not the guest's gate is true, so one serve proves nothing.
  The press is served to that reader on every key tick until the guest's own ATE window opens (the `NewMesWin` hook on
  the guest: the ATE caption, opened by that uid on that field), then retired. Success is proven by the lock's own
  "win 1 text 98 opened locked" line and the relay's "opened my copy's ATE menu" line, never by a serve count. It
  expires unopened after 5 s, at any field load, at a session reset, or when the lever is off.
- Once the menu is open it is an ordinary locked choice: the host's CHO event picks the row, its title is locked and
  closes on the host's close event.

### The episode: let the guest's own script carry it to the ATE and back

From the moment the guest's copy opens its ATE menu from a relayed press, the guest is in an **ATE episode**:
- **Hub phase** (on the menu's field). It notes whether the menu was closed by the host's own choice event (the lock's
  `ApplyEvents`, a closing CHO on an ATE-caption window). Only then:
  - **The own jump passes.** The copy's own `Field(dest)` passes `RedirectGuestFieldJump` (one line, "my copy's own
    Field(dest) passes: the host's pick"). Today it can bounce: the host's position lane reads field 0 while it loads
    350, so `dest == LastHostField` fails and the guest would reload 352 first (the double load the brief forbids). The
    check runs before the `dest == myField` pass, so a same-field ATE records its own jump too.
  - **The follow holds** while my control is off, up to 8 s from the host's pick: the host's intent toward 350 would
    otherwise black-fade over the guest's own white fade and title. One line per held destination.
- **Destination phase.** At the next field load, if it is the own jump's destination, the episode moves there (a
  same-field ATE lands on the same id: the landing, not the id, decides). There the follow holds while my control is
  off, up to 8 s from the first held tick: Finding 4's capped follow-hold, scoped here to the ATE episode. The guest's
  copy shows 324/325 from the host's events, runs its own fade and music load, and takes its own `Field(352)`, which
  passes as the host's announced destination (the live intent's field) or `LastHostField`. A first cut also required
  "a host event for my field still waiting", as Finding 4 words it; that let the follow's black fade cut the last
  second of the ATE, after its last line and before its own `Field()`.
- **The end.** Any other field load, the second landing, my control back for 1 s (the host picked Cancel, or the scene
  ended in place), the session ending, or the lever.

The cap keeps every hold bounded: a guest copy that diverged gets today's follow after 8 s.

### The step-out on the ATE menu: no

The s158 step-out would fire on the guest's menu (a fresh line with control off), darken a dressed guest and show a
Zidane stand-in for as long as the host browses the menu; the host's option C already hides the guest's ghost while the
host's own menu is up. The menu and the title card are system captions over a still room, not a party scene. So:
- ATE-caption windows (`Dialog.CapType == ActiveTimeEvent`) are never a fresh line (`NetSyncWindowSnapshot.AnyFresh`,
  shared by both screens' rules);
- while one is open on my copy, the step-out's base does not hold (a new term, "an ATE caption is open"), so the dwell
  cannot start it either.
The scene on the destination field is an ordinary scene: the step-out applies there as before.

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
- `NetSyncAte.SelfTest` rows for every pure rule, each with a mutant, in the selftest block after the step-out's line.

## Census, second count

The kit's disassembler over the install's 818 US field `.eb` binaries (`ebsrc.write_source`, every `B_KEYON` / `B_KEY`
whose constant mask has bit 0): **596 Select reads; 150 control-on (`B_SYSVAR[2] const(1) B_EQ` in the same
expression), one per field in 150 fields, every one followed by a winATE window and `EnableDialogChoices`**; 445
control-off `B_KEYON` reads and one `B_KEY` (206's tutorial wait). The HW exports hold each script twice, which is why
their totals are about double (1,152 / 305); the field count (150) and the verdict match. Scripts:
`census_select.py` (HW text) and `census_select_eb.py` (bytes), in this round's scratchpad.

## Status

Design. Not built.
