"""F3.2 C2 HOST-AUTHORITATIVE DIALOGUE + F3.3 C3 THE DIALOGUE RING AND THE KEY RELAY -- the solo benches (s96, s98,
s99), run unattended on bench 30801. The C3 half (R-B0..R-B7) is documented after the C2 calibration note below.

THE CONTRACT (`studies/field-coop/F3.2-DESIGN.md` sync_changes S1-S8, s96). A following guest's ETb lines
are LOCKED from the frame they open, at every input seam (keys/pad/turbo, mouse click, drag, cursor
select, the voice auto-dismiss). Only HOST state moves them: the host's events, applied per window key
in host order (never drained, never handed back on a timer), the orphan rule (a line the host provably
lacks auto-closes at reading pace, Cancel else Default), the link reading dead for LinkGraceMs, the
session ending, or the ~ menu panic unlock. It replaces the F3 lockstep (coop_dialogue_lockstep.py,
retired): F3's lock armed only on a MATCHED frame, any flag-0 sample drained the queue, and its 8 s
DialogWaitMs timeout handed the line back to the guest ("local advance restored").

The bench: `netsync selftest 1` forces the selftest role for this process (Memoria.ini untouched), and
`bench 1` + `lock 1` + `hostscene 1` stand in for a live followed session whose host is mid-scene. Under
the bench the player cannot start a talk himself (the F1 spectator gate), so every line under test is
opened the way a guest's lines open: by the HOST's relayed start, `netsync talk <uid>` (F3.1). The uids
and the reference transcripts are learned first from LOCAL talks with every lever off.

WHAT IS PROVEN -- every check an OUTCOME (the window on screen, its text, the published tracker, the
engine's own log line), never an ack. Unless stated, the levers are lock 1 + hostscene 1.
  A11  at selftest start the engine's pure NetSyncDialog.SelfTest (host-scene machine, settle clock,
       orphan step, inbox) logs OK -- once per process, so the WHOLE log is searched.
  A1   lock from open: before any host event the line is `suppress` + windows[].cls "locked" + the
       'following' chip; Confirm x3, a held Confirm (with the turbo key) and two `netsync click`s leave it
       OPEN ON THE SAME TEXT (the behavioural half: keys the old DLL publishes too) and on the same tracked
       page, still locked (the F3.2-key half), with no close of any kind; then injected host advances page it
       exactly once each, and that transcript EQUALS the one the player's own Confirm paged locally. No drag
       or arrow here: on a PLAIN window stock OnDrag and the arrows act on nothing -- a no-op on any engine,
       so they could not fail; A2 carries them, on a choice.
  A1v  vanilla parity -- the same-run CONTROL for A1: `lock 0`, the same relayed line is untracked, not
       suppressed, and one click pages it (stock DialogManager.OnClick); Confirm finishes the transcript.
  A2   choice: two Down presses and a `netsync drag -80` never move a locked menu's SelectChoice (the
       OnItemSelect / OnDrag gates; the highlight re-assert is not published -- the screenshot shows it);
       `netsync choice <WANT>` lands the SAME follow-up window a local choose(<WANT>) leads to. Its same-run
       controls: the reference choose() moved the cursor with Down presses, and the DRAG CONTROL at setup
       moved the unlocked cursor with the same `drag -80`. (`drag 80` is not sent: from the default row 0
       MoveCurrentChoice(-1) clamps, a no-op on any engine.)
  A2b  an out-of-range host index falls back to the menu's DEFAULT (logged once) and lands the default's
       local follow-up. The guest's Down press first is CALIBRATION's DLG-10 discriminator: the old DLL lets
       it move the cursor and its fallback commits the guest's row. Under the F3.2 lock the cursor cannot
       leave the default, so on THIS DLL "the default" and "the guest's cursor" coincide -- this run cannot
       tell them apart, and does not claim to.
  A5   an EARLY choice event: sent the instant the menu window exists (asserted: the last sample before the
       send read it NOT ready) is held through the open, the typewriter and MinShowMs, then applied exactly
       once (no 'did not advance' retry) -- same follow-up as local. This is NOT DLG-7 itself: IsChoiceReady
       rises one frame after AfterShown (Dialog.cs:652, :163-164), long before MinShowMs (350 ms) runs out,
       so the IsChoiceReady gate (NetSyncDialog.cs:590) is never the binding condition here. No solo bench
       reaches it (it needs a choice page with no type animation and MinShowMs 0); the old DLL, too, holds
       such an event to CompleteAnimation.
  A4   per-key FIFO: an event for a key no window has (`unmatched`, win 15 / text 0xFFFF) queued AHEAD of
       the open line's advance blocks nothing -- the line pages, the stranger stays queued. A regression
       check, NOT a calibration discriminator (see CALIBRATION).
  A8   the [NFOC] polled story page: tracked as input-inhibited, `suppress` stays false, the chip is
       'the host is in a scene' (a polled strip is not a conversation), the menu's applied choice event
       left the inbox (a regression guard: this bench never fabricates an event for the page -- memory LAW
       :1369). [ff9mapkit netsync F3.3] Its old last check -- "the guest's own Confirm still closes it through
       its script's poll", the documented C2 gap -- is RETIRED: C3 closes the gap, so the same bench now runs
       R-B2 (below), which asserts the opposite.
  A3   no hand-back: with an unmatched event queued the locked menu sits QUIET (no guest input) for 9 s,
       past F3's 8 s DialogWaitMs -- no 'local advance restored' (or any dialogue timeout) in the log, and
       the event still queued; then it holds 10 s more of the guest mashing Confirm -- open (behavioural),
       still tracked locked under an engaged lock (F3.2 keys) -- with `host_settled_ms` -1 throughout. Then
       `hostscene 0`: the line turns 'orphaned' OrphanGraceMs (2 s) later with the 'closing it' chip,
       auto-closes AutoReadMs (2 s) after that on the menu's CANCEL row (Close: no reply window opens),
       one orphan line, orphan_closes +1, and not one input-driven or self-attributed close.
  A6   link dead: `stale 1` keeps the line locked (chip 'link hiccup') until LinkGraceMs (3 s), then
       releases it with one log line; the guest's own Confirm pages it.
  A7   panic unlock: `netsync unlock` drops the lock on this field (one log line) and the guest's own
       Confirm pages the line; a field reload re-arms it (one 're-armed' line) and a relayed line opens
       locked again.
  RESET  `reset` releases the override and every lever (bench, l1, lock, stale) -- a leaked run cannot hand
       the next player a swallowed Confirm.
  A12-lite  with co-op released, a local talk is stock: a click pages, the local transcript, and zero
       [NetSync] log lines meanwhile. (Its "nothing suppressed or locked" is a regression guard only: both
       reads are gated on `enabled`, which RESET already asserted False.)
SKIPPED, because a solo bench on 30801 cannot reach them: A9 (needs a field with an ATE gate and a scripted
Party()), A10 (needs a voiced field with AutoDismissDialogAfterCompletion), and A12's real half (Enabled=0
FROM LAUNCH -- zero [NetSync] lines in a whole run -- needs an ini edit, which the shared install forbids;
the two-machine package covers it). Turbo is not discriminating on 30801: the scribe carries [NTUR] and a
choice is turbo-immune, so A1's turbo hold is kept only as a regression step. Mouse HOVER over a choice row
cannot be injected (NGUI OnHover); the drag is the reachable stand-in.

SAME-RUN CONTROLS (why the lock checks can fail on THIS DLL): A1v pages the same line with the same click
and Confirm once the lock is off; the reference choose() at setup moved the menu's cursor with the same Down
presses, and the drag control there moved it with the same `drag -80`; A6 and A7 show the guest's Confirm
paging a line the moment the lock lets go.

CALIBRATION -- a check that cannot fail is not a check. Run once against the pre-F3.2 DLL (the F3 lockstep
build: no `dialogue` key, no lock/hostscene/stale/unlock/click/drag verbs) BEFORE trusting a green run.
COOP_CALIBRATE=1 forces it; an engine whose `netsync` block has no `dialogue` key gets it automatically.
In that mode the scenario spells every lever the OLD way -- the one F3 lever, `l1`, stands for both
`lock` and `hostscene` (it was the lockstep's engage gate); `netsync click` becomes a Confirm press;
`drag`, `stale` and `unlock` have no old equivalent and are skipped -- and runs the SAME assertions.
Expected red on the pre-F3.2 DLL:
  * BEHAVIOURAL (the real calibration -- each of these checks reads only keys and log lines the old DLL
    publishes too, so its red is the old BEHAVIOUR): A1's `suppress` (False: F3 armed on a matched frame)
    and A1's "left open on the same text" (the first local Confirm pages the un-injected line); A2 -- Down
    moves the cursor (no OnItemSelect gate); A2b's follow-up -- the guest's Down moved the cursor and F3's
    out-of-range fallback ('-- local default') committed it (OnKeyConfirm: IndexOf(ActiveButton)), so the
    guest's row's window opens, not the default's; A3's quiet phase -- F3's 8 s DialogWaitMs logs 'dialog
    frame ... timed out -- local advance restored' for the held-unmatched frame; A3's hold -- the first
    local Confirm closes the menu (that frame was never suppressed).
  * KEY-ABSENT (they fail, but that proves nothing about their teeth -- the same-run controls above do):
    the contract and default-gates checks, A11, every windows/inbox/chip/orphan/host_settled check and
    every apply/queue log line (F3 logged neither 'win N text T advanced (host seq' nor 'host seq N
    queued') in A1-A8 -- A4 and A5 included, A6/A7 (no old lever), RESET's lock/stale.
  * NOT discriminating: A1v and A12-lite (vanilla behaves the same on both), A2's choice landing, A5's
    landing, A4's paging, and A1's "the click seam was exercised". A4: the old bench inject wrote straight
    into F3's one-slot holder (`_dialogPending = body`), so `advance` REPLACED the held `unmatched` and
    applied -- on the bench the old engine never head-of-line-blocked (only its socket FIFO could, which a
    solo bench cannot reach), and the line pages on both DLLs. The click: in this mode a click IS a Confirm
    press; the check exists for the new DLL -- on an install with `[Control] DisableMouseForMenus` on,
    `netsync click` is refused, and A1, A1v and A12 then fail and NAME the refusal instead of passing
    without ever clicking.
On the NEW DLL in calibration mode (COOP_CALIBRATE=1 forced) A1 must ALSO fail -- `l1` alone engages no
lock there -- which proves the mode really runs the old procedure.

[ff9mapkit netsync F3.3] C3 (`F3.2-DESIGN.md` stage C3 R1-R9; s98 = the section-7 dialogue ring, wire v14; s99 = the
script-key relay R5 + the R9 tap-record bench). The bench HOST (`netsync host <op>`) builds section 7 through the REAL
HostRing.BuildSection + NetSyncState.AppendSection every bench tick, and the guest half reads it through the real
TryReadSection / TryParseHostSection / Merge -- no socket. The C2 verbs (`advance`/`choice`/`unmatched`) ride the same
ring on a C3 engine, so A1-A7 double as C3's A-series regression. Every check below is an OUTCOME (the window, the
published keys, the engine's own log line):
  R-B0  BUILD IDENTITY, not a second proof: the selftest proof line's description names the section-7 codec (round
        trip, seq wrap 65535->1, gap>32 once, truncated refused, re-send once, epoch reset w/o replay, stall 10000 ms)
        and the key relay's KeyScript. NetSyncDialog.SelfTest builds that text from LITERALS whenever its `??` chain
        returned null, so these clauses rise and fall with A11's OK line: they say the build CARRIES the C3 scripts
        (s98 / s99), not that each one ran -- a script dropped from the chain with its prose kept would stay green here.
  R-B1  RING DELIVERY. `host adv` pages the relayed scribe exactly once and is queued ONCE although the slot is
        re-sent every bench tick (last_seen == head_seq). `host gap 40`: one GAP line, `gaps` +1; the stranded line
        stays locked and, once the host scene falls, orphans and auto-closes. HEALING (WIRE-1): an ADV sent while
        the link reads dead (`stale 1`, inside LinkGraceMs) is delivered once the moment it comes back. EPOCH:
        `host epoch` changes `epoch`, empties the inbox (a queued stranger), moves the baseline to the new head and
        logs the dedup reset (WIRE-6/CLB-4); the new epoch's first ADV still applies. (NO-REPLAY itself is RingScript's,
        offline: the bench's `epoch` op empties its own ring, so there is no history here a wrong guest could replay.)
        A KEY carrying no host-owned button is ignored (`key_ignored` +1).
  R-B2  THE KEY RELAY, on the [NFOC] polled story page (inside A8, which opens it). `netsync advance` -- and, on a
        ring engine, `host adv` -- aimed at it is REFUSED naming LAW :1369; `key_hold` is true and `key_reader` is
        the polling uid N; Confirm x3 + two clicks leave it OPEN on the same text (the BEHAVIOURAL half); the log
        names N ('script button-poll by uid N ... suppressed'); a KEY for the wrong uid is held and closes nothing;
        `host key N 64` (compact b6 = Confirm) closes it through its OWN poll ('served to uid N's poll', then
        'closed by its own script/timer'), `key_served` +1; then, with both sides idle (host scene down, control
        back), the wrong-uid KEY and a second KEY for the page's reader -- whose poll ended with the page -- expire
        UNSERVED after KeyIdleMs (`key_expired` +2, `key_served` unchanged). That is the IDLE EXPIRY only: nothing
        on 30801 polls with control on, so "a KEY is never served to a control-on read" is not reached (SKIPPED).
  R-B2g THE ORDERING GUARD: a KEY sent in the same request right behind an ADV for a line still opening waits in
        `keys[]` as 'pending', and is released only after that ADV applied (log order), with no give-up.
  R-B3  RECORD / REPLAY -- the only solo run of the REAL host taps. Lock OFF + `tap-record 1`: the player's own
        Confirms on the relayed scribe tape one dialog tap per page (EmitDialogAdvanceIfHost), the last 'closes'.
        The paced `replay` into a LOCKED copy walks the same transcript while the guest mashes Confirm: one 'host
        seq N' apply line per page, zero self-attributed closes, `replay_left` 0. Then the keeper: the menu pick
        tapes a CHO and the polled page's Confirm a KEY (TapScriptKeyIfHost: a control-off poll hit) -- tape 2; the
        replay closes the locked menu on the recorded row and serves the KEY to the page's own poll.
  R-B4  CURSOR MIRROR: `host open <row>` puts the locked menu's cursor (and `cursor`) on the host's row, and the
        highlight follows the host's cursor as it moves -- the mirror's teeth. Local Down presses leaving it on the
        host's row is a C2 REGRESSION GUARD only: DialogManager.OnItemSelect already drops a guest's arrows on a locked
        choice (IsGuestLockedChoice, F3.2), so the mirror's snap-back cannot be told apart from that gate here -- no
        non-input cursor mover is reachable on this bench. While the host's open set holds
        the window it is not orphaned for OrphanGraceMs + AutoReadMs + 1 s with the host scene down (two R4 rules
        hold it and this bench cannot separate them: the open-set CLAIM, and section 7's b2 -- a host line open --
        which keeps the host from reading settled); `host shut` releases it to the orphan rule (orphaned, then
        auto-closed once).
  R-B5  CLOSES BIT: `host adv 0` (a NON-closing ADV) on the guest's LAST page is consumed as a no-op ('... consumed,
        no-op') and the line stays; the host's closing ADV then closes it once. The catch-up half (`host adv 1` on
        page 1 of a multi-page window pages it through to its close: one 'paging on to its close' line, ONE apply
        line, the local transcript) runs only when the scribe's window has >= 2 pages -- see SKIPPED.
  R-B6  HUNG HOST: `host freeze` keeps the line locked to >= 9.5 s and drops the lock HostStallMs (10 s) after the
        heartbeat stopped -- `host_stalled` true, one 'host looks HUNG' line, the line itself untouched. `host
        freeze 0` re-arms it (one line) and the line open across the stall stays LOCAL -- tracked again with class
        `local` (MarkOpenLocal; an empty tracker does not pass) -- and the guest's Confirm pages it.
  R7    CHIPS: `host menu 1` -> 'the host is in a menu -- waiting' (flags b4); `host battle 1` -> 'the host is in a
        battle -- this line continues after it' (b5 set, b3 clear), the line still locked.
  R-B7  VANILLA (inside A12-lite, co-op released): the polled story page closes on the player's own Confirm through
        the hoisted B_KEYON, with zero [NetSync] lines; `key_tick` still counts (the inert counter) and `key_taps`
        does not move -- a plain regression clause: after RESET this copy is no socket host and tap-record is off,
        so TapScriptKeyIfHost returns before tapping with or without its `!_enabled` gate (this bench cannot isolate it).
  RESET also releases the C3 levers (`host freeze` / `menu` / `battle`, `tap-record`) -- each first read SET, so a
        lever that never landed cannot pass as "released".
SKIPPED -- a solo bench on 30801 cannot reach them: the POLLED CHOICE (`host key N 64 <k>` landing the same
follow-up as a local choose(k), `cursor` = k): no 30801 window is a polled choice -- the keeper's menu is a
WindowSync choice the CHO lane drives and the story page is a polled PLAIN page (KeyScript proves the cursor wait
offline; a save moogle or a shop is the in-game bench). "A KEY is never served to a control-ON read" (bench step 6):
no 30801 object polls buttons with control on -- the keeper's B_KEYON lives only inside its open page and the
[behavior] unit only holds -- so a KEY sent with control on finds no reader and expires either way; the rule is
proven only by the fake (test_a_key_is_never_served_to_a_control_on_read keeps a control-on poll running) and by
construction (FilterScriptButtons' control-on branch returns before TakeRelayedScriptKey); a bench with a free-walk
Confirm poll by a known uid would reach it. R-B5's catch-up while every 30801 window is a single page
(its .mes carries no [PAGE] -- the scenario measures the scribe's transcript and says which). R-B3's quad halves
(no ladder or chest quad on 30801). The guard's GIVE-UP (`key_gaveup`: needs an ADV that can never apply to an open
driven line). R-B7's real half (Enabled=0 from LAUNCH -- an ini edit, the two-machine package).

C3 CALIBRATION -- on the currently deployed s96 engine (the F3.2 C2 build: it publishes no `wire`, `key_hold` or
`tap_record`, and its agent answers `host` / `tap-record` / `replay` "unknown sub-verb"). Expected there:
  * GREEN: A1-A7 and A8's C2 half -- that engine IS the C2 contract.
  * RED, BEHAVIOURAL (the real calibration: keys and log lines the s96 DLL publishes too): R-B2's "Confirm x3 and
    two clicks left the polled page OPEN" (on s96 the guest's own Confirm reaches the unmasked poll and closes the
    page -- the C2 gap), and R-B2's "`netsync advance` aimed at the polled page is REFUSED" (s96 accepts it and
    fabricates the event, which its ApplyEvents then skips until it ages out).
  * RED, KEY-ABSENT (they fail, but that proves nothing about their teeth -- the C3 run's same-run controls do):
    both R-B0 checks; A8's "the engine has the script-key relay"; ONE capability check per C3 bench (R-B1, R-B4,
    R-B5, R7, R-B2g, R-B3, R-B6 -- each records "<bench>: the engine has <capability>" FAILED and runs nothing, so
    none of its checks can pass there); A12/R-B7's `key_tick` check.
  * NOT RUN there: RESET's two C3 lever checks, set-before and released-after (they need the C3 keys to exist).
  * RED as a CONSEQUENCE (no separate evidence): R-B2's "the click seam was exercised" -- on s96 the first Confirm
    already closed the page, so both clicks are refused 'no dialogue window is open'.
  * NOT discriminating: R-B7's page check (vanilla closes the page on its own Confirm on every engine -- it is the
    regression guard for the EBin hoist).
  In all, on s96: 96 checks, 14 red (the 2 behavioural + the consequential click + 11 key-absent), 82 green (the
  81 C2 checks that survive A8's retired gap check, + R-B7's page).
  On an s98-only engine (the ring, no key relay) nine reds, the rest runs:
  * BEHAVIOURAL (s98 has the ring but neither the bench's LAW :1369 refusal -- InhibitedRefusal -- nor the poll mask,
    both s99): R-B2's two "REFUSED, naming LAW :1369" checks (`netsync advance` and `host adv` are accepted), and
    R-B2's hold barrage (the guest's own Confirm reaches the unmasked poll and closes the page).
  * CONSEQUENTIAL: R-B2's click check (the page is already gone: 'no dialogue window is open').
  * KEY-ABSENT: R-B2's "the engine has the script-key relay", R-B2g's and R-B3's capability checks, R-B0's key-relay
    clause (KeyScript's prose is s99's) and R-B7's `key_tick` (published from s99).
SAME-RUN CONTROLS for the C3 checks on the new DLL: R-B6 shows the guest's Confirm paging the line the moment the
stall releases it, and A1v/A6/A7 show it on the C2 seams; R-B2's KEY half closes the very page its hold barrage
could not; R-B4's claim check is followed by `host shut` orphaning the same window; R-B5's no-op is followed by the
closing ADV closing it; R-B1's healing check first proves the ADV did NOT arrive while the link read dead.

DRIVER NOTE. `Session.netsync` refuses a sub-verb missing from its NETSYNC_SUBVERBS BEFORE sending; the committed
driver predates s98/s99's `host`, `tap-record` and `replay` (the F3.3 driver stage adds them, each gated on its
capability key). `_ns_verb` sends a sub-verb the driver does not know as a raw `netsync ...` step instead (one note per
sub-verb); the AGENT's own gates and refusals apply unchanged. With a driver that knows the verb it is plain
`g.netsync`. Either way a C3 bench runs only when `_caps` reads the capability off the published keys, so the
scenario never depends on which driver refused first. (R-B2g sends its ADV + KEY as ONE raw request on purpose: the
KEY must land right behind the ADV.)

Bench 30801 (the journal dashboard): the scribe (a plain [NTUR] window) stands west, reached from
(-210, -837); the keeper (the 15-option journal menu: row 0 the [NFOC] polled story page, `Close` last
and the CANCEL row) stands east, reached from (210, -837).

    py tools/play.py studies/test-harness/scenarios/coop_dialogue_authority.py --field 30801
    COOP_CALIBRATE=1 py tools/play.py studies/test-harness/scenarios/coop_dialogue_authority.py --field 30801
"""
from __future__ import annotations

import os
import re
import time
from types import SimpleNamespace

try:                                     # play.py puts tools/ on sys.path before it loads a scenario
    from harness import HarnessError
except ImportError:                      # pragma: no cover - imported outside the driver (py_compile, a stub)
    HarnessError = RuntimeError          # HarnessError IS a RuntimeError

FIELD = 30801
WEST = (-210.0, -837.0)         # beside the scribe: a plain window
EAST = (210.0, -837.0)          # beside the keeper: the journal menu
WANT = "Tetra Master"           # a named option, so the index is the engine's own, not our arithmetic
STORY = "Story & treasure"      # row 0: the [NTUR][NFOC] WindowAsync + B_KEYON polled page
CLOSE = "Close"                 # the last row = the engine's CANCEL row (content/choice.py); no reply
MAX_PAGES = 14
IGNORES_INPUT = ("[NFOC]", "[TIME=")    # the tags that set Dialog.ignoreInputFlag / FlagButtonInh
CHOICE_GROUP = "Dialog.Choice"          # Session.CHOICE_GROUP: the dialog's own button group is active

# NetSyncDialog.cs -- the clocks the timed checks are judged against (wall-clock: Environment.TickCount)
LINK_GRACE_S = 3.0              # LinkGraceMs
ORPHAN_GRACE_S = 2.0            # OrphanGraceMs
AUTO_READ_S = 2.0               # AutoReadMs
QUIET_S = 9.0                   # A3's quiet phase: past F3's DialogWaitMs (8 s), the old hand-back clock --
#                                 and with HOLD_S still inside PendingTtlMs (20 s) when the inbox is read
HOLD_S = 10.0                   # A3: how long an unmatched event + a mashing guest must hold the line
SLACK_S = 0.6                   # an UPPER bound's allowance: one tick at 31 fps + the publish (every 2 frames) + our poll
EARLY_S = 0.08                  # a LOWER bound's allowance: Environment.TickCount's ~16 ms resolution + one frame

CHIP_FOLLOWING = "Co-op: following the host's conversation"
CHIP_CLOSING = "Co-op: this line isn't on the host's screen -- closing it"
CHIP_HICCUP = "Co-op: link hiccup -- holding this conversation for the host"
CHIP_HOST_SCENE = "Co-op: the host is in a scene"
# [ff9mapkit netsync F3.3] C3 -- NetSyncDialog.cs / NetSyncField.cs
CHIP_HOST_MENU = "Co-op: the host is in a menu -- waiting"                           # R7, section 7 b4
CHIP_HOST_BATTLE = "Co-op: the host is in a battle -- this line continues after it"  # R7, b5
HF_ON_FIELD, HF_MENU, HF_BATTLE = 0x08, 0x10, 0x20     # section 7's flags byte (b3 / b4 / b5)
KEY_CONFIRM = 64                # a KEY's compact bits: b6 = Confirm (NetSyncField.CompactKeys; the poll's mask has it)
KEY_NO_HOST_BUTTON = 1024       # b10: outside the 10 host-owned compact bits -> refused at ingest (`key_ignored`)
GAP_N = 40                      # `host gap 40`: more lost events than the ring holds (RingCap 32)
STALL_S = 10.0                  # HostStallMs: a heartbeat frozen this long drops the lock (R6)
KEY_IDLE_S = 1.5                # KeyIdleMs: an unserved KEY expires once both sides have been idle this long
HEAL_S = 1.2                    # R-B1 healing: how long the link reads dead -- well inside LinkGraceMs (3 s)
MIN_SHOW_S = 0.35               # MinShowMs: a completed page shows at least this long before a host event applies
_SERVED = re.compile(r"key relay: host seq (\d+) served to uid (\d+)'s poll")
_MASKED = re.compile(r"script button-poll by uid (-?\d+) \(the host drives this scene\) suppressed")
_OPENED = re.compile(r"dialogue lock: win (\d+) text (\d+) opened locked")

#: COOP_CALIBRATE=1 forces the pre-F3.2 procedure (see the module note); unset, the scenario reads the
#: engine's own `netsync.dialogue` contract tag and falls back to it when the tag is absent.
FORCE_CALIBRATE = os.environ.get("COOP_CALIBRATE", "").strip() not in ("", "0")

_APPLIED = re.compile(r"dialogue: win (\d+) text (\d+) (advanced|closed) \(host seq (\d+)(?:, choice (-?\d+))?\)")
_QUEUED = re.compile(r"dialogue: host seq (\d+) queued \(field (\d+) win (\d+) text (\d+) kind (\d+)")


# ---------------------------------------------------------------------------------------- observing
def _log_lines(g) -> list:
    p = g.engine_log()
    if p is None:
        return []
    try:
        return p.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _mark(g) -> int:
    return len(_log_lines(g))


def _new(g, mark: int) -> list:
    return _log_lines(g)[mark:]


def _count(lines, needle: str) -> int:
    return sum(1 for ln in lines if needle in ln)


def _grep(lines, *needles, limit: int = 300) -> str:
    return "; ".join(ln for ln in lines if any(n in ln for n in needles))[:limit]


def _applied(lines, win, text) -> list:
    """The apply lines (advanced / closed by a host event) for ONE window key: [(verb, seq, choice)]."""
    out = []
    for ln in lines:
        m = _APPLIED.search(ln)
        if m and int(m.group(1)) == win and int(m.group(2)) == text:
            out.append((m.group(3), int(m.group(4)), None if m.group(5) is None else int(m.group(5))))
    return out


def _served_to(line: str, uid: int) -> bool:
    """[ff9mapkit netsync F3.3] a 'key relay: host seq S served to uid N's poll' line for this uid."""
    m = _SERVED.search(line)
    return m is not None and int(m.group(2)) == uid


def _ns(st) -> dict:
    return st.netsync or {}


def _wins(st) -> list:
    return _ns(st).get("windows") or []


def _front(st) -> dict | None:
    """The newest tracked line (the tracker appends in open order)."""
    w = _wins(st)
    return w[-1] if w else None


def _heads(st) -> list:
    return (_ns(st).get("inbox") or {}).get("heads") or []


def _key(st):
    w = _front(st)
    return (w["win"], w["text"]) if w else (None, None)


def _ignores_input(st) -> bool:
    return any(tag in raw for raw in st.raw_texts for tag in IGNORES_INPUT)


def _listener(st) -> int:
    return int((st.raw.get("player") or {}).get("listener", -1))


def _choice_ready(s) -> bool:
    return s.choice is not None and s.menu_group in (None, CHOICE_GROUP)


def _poll(g, predicate, timeout: float, what: str):
    """``g.wait_for`` that answers None on a timeout instead of raising: the check that follows carries the
    verdict. A dead game still raises -- the next send asserts the process is alive."""
    try:
        return g.wait_for(predicate, timeout=timeout, what=what)
    except HarnessError:
        return None


def _paged_by(g, act, *, tries: int = 6, frames: int = 12) -> bool:
    """Do ``act`` the way a player does -- repeatedly, reading between -- until the open line pages or closes.
    A line still typewriting eats the first Confirm/click as a fast-forward (Dialog.OnKeyConfirm)."""
    st = g.state
    if not st.dialog_open:
        return False
    first = st.text
    for _ in range(tries):
        act()
        g.wait_frames(frames)
        s = g.state
        if not s.dialog_open or (s.text.strip() and s.text != first):
            return True
    return False


def _follow_up(g, *, timeout: float = 4.0) -> str:
    """The text of the window a closed choice LEADS TO -- waited for, since it opens a beat later (sampling
    the frame the menu closes reads an empty screen: the follow-up is built on a later tick)."""
    if _poll(g, lambda s: s.choice is None, timeout, "the choice menu to close") is None:
        return ""
    st = _poll(g, lambda s: s.dialog_open and bool(s.text.strip()), 3.0, "the follow-up window to open with text")
    return st.text if st is not None else ""


# ------------------------------------------------------------------------------------------- acting
class _Levers:
    """The F3.2 bench levers -- or, in CALIBRATION mode, the pre-F3.2 equivalents (module note): the old
    engine's one lever `l1` was both the host-scene flag and the lockstep's engage gate."""

    def __init__(self, g, legacy: bool):
        self.g, self.legacy = g, legacy

    def lock(self, on: bool) -> None:
        self.g.netsync("l1" if self.legacy else "lock", 1 if on else 0)

    def scene(self, on: bool) -> None:
        self.g.netsync("l1" if self.legacy else "hostscene", 1 if on else 0)

    def stale(self, on: bool) -> None:
        if not self.legacy:              # no old equivalent: F3 had no link-dead lever
            self.g.netsync("stale", 1 if on else 0)

    def unlock(self) -> None:
        if not self.legacy:              # no old equivalent: F3 had no panic unlock
            self.g.netsync("unlock")

    def click(self) -> None:
        if self.legacy:
            self.g.press("confirm", 4)   # F3 had no click verb: its guard's own (keyboard) path
        else:
            self.g.netsync("click")

    def drag(self, dy: int) -> None:
        if not self.legacy:              # no old equivalent
            self.g.netsync("drag", dy)

    def engage(self) -> None:
        """The standard bench: bench + lock + host scene ON."""
        self.g.netsync("bench", 1)
        self.lock(True)
        self.scene(True)
        if not self.legacy:
            _poll(self.g, lambda s: _ns(s).get("lock_engaged") is True, 3.0, "the bench lock to engage")


def _try(g, what: str, fn, *args) -> str | None:
    """One input step of a barrage. A refusal (e.g. `click` with no window left to click) is evidence for
    the check that follows, not a crash of the bench. Returns None when the step ran, else the refusal."""
    try:
        fn(*args)
        return None
    except HarnessError as err:
        g.note(f"{what}: refused -- {str(err)[:160]}")
        return str(err)[:200]


def _click_pages(g, lv) -> tuple[bool, str]:
    """Click the open line the way a player clicks (see _paged_by). (paged, why-not): a refused click -- e.g.
    `[Control] DisableMouseForMenus` on this install -- is named, never read as "the click did nothing"."""
    refused = []

    def act():
        why = _try(g, "click", lv.click)
        if why:
            refused.append(why)
    paged = _paged_by(g, act)
    return paged, ("click refused: " + refused[0]) if refused else ""


def _open_by_relay(g, uid: int, *, choice: bool = False, timeout: float = 6.0):
    """Open a line the way a guest's lines open: the host's relayed start (`netsync talk`), on my copy."""
    g.netsync("talk", uid)
    if choice:
        st = _poll(g, _choice_ready, timeout, f"the relayed start (uid {uid}) to open the menu")
    else:
        st = _poll(g, lambda s: s.dialog_open and bool(s.text.strip()), timeout,
                   f"the relayed start (uid {uid}) to open its window")
    if st is None:
        raise HarnessError(f"the relayed start for uid {uid} opened nothing within {timeout:.0f}s")
    return st


def _tracked(g, *, timeout: float = 2.0):
    """The state once the tracker has registered the open line (one guest tick after it opens)."""
    return _poll(g, lambda s: bool(_wins(s)), timeout, "the tracker to register the open line") or g.state


def _inject_until_closed(g, first_page: str, *, max_pages: int = MAX_PAGES):
    """Drive the open line to its close with injected host ADVANCE events. Returns (pages, injects). Never
    injects into a choice or a script-polled ([NFOC]/[TIME]) window -- no host could emit for one."""
    pages, injects = [first_page], 0
    for _ in range(max_pages):
        before = g.state
        if not before.dialog_open or before.choice is not None or _ignores_input(before):
            break
        g.netsync("advance")
        injects += 1
        last = pages[-1]
        st = _poll(g, lambda s: (not s.dialog_open) or s.choice is not None or (s.text.strip() and s.text != last),
                   6.0, "the injected advance to page or close the line")
        if st is None or not st.dialog_open or st.choice is not None:
            break
        pages.append(st.text)
    return pages, injects


def _clear(g, close_idx: int, *, max_steps: int = 24) -> bool:
    """Clear the screen by the player's OWN input (call with the lock off): the keeper's menu on its Close row,
    anything else -- a plain page, or a polled page whose script closes it -- with Confirm."""
    for _ in range(max_steps):
        st = g.state
        if not st.dialog_open:
            return True
        if _choice_ready(st):
            try:
                g.choose(close_idx)
                continue
            except HarnessError:
                pass
        g.press("confirm", 4)
        g.wait_frames(12)
    return not g.state.dialog_open


def _settle(g, lv: _Levers, c, name: str) -> None:
    """Between benches: the lock OFF (everything local), the screen cleared by the player's own input,
    control back, then the standard bench again -- so the next line opens under a lock that PREDATES it
    (a line already open when the lock rises is marked local, by design)."""
    why = ""
    try:
        if not lv.legacy and _ns(g.state).get("stale"):
            g.netsync("stale", 0)
        if _ns(g.state).get("tap_record"):
            _ns_verb(g, "tap-record", 0)     # [ff9mapkit netsync F3.3] R9's lever (needs only the bench)
        lv.lock(False)
        cleared = _clear(g, c.close_idx)
        ctl = _poll(g, lambda s: s.control, 6.0, "control back between benches")
        lv.engage()
        g.wait_frames(10)
        _tidy_bench_host(g)
        ok = cleared and ctl is not None and not g.state.dialog_open
    except HarnessError as err:
        ok, why = False, str(err)[:300]
    g.check(ok, f"{name}: the screen was cleared and the bench re-engaged for the next bench", why or repr(g.state))


def _phase(g, lv: _Levers, c, name: str, fn, *args) -> None:
    """Run one bench. A refusal or a timeout fails THIS bench (one check), the screen is cleared, and the
    scenario goes on -- calibration mode depends on it: the old engine refuses the new verbs."""
    g.note(name)
    try:
        fn(g, lv, c, *args)
    except HarnessError as err:
        g.state                          # a dead game raises here, out of the bench
        g.check(False, f"{name}: the bench ran to completion", str(err)[:400])
    _settle(g, lv, c, name)


# ------------------------------------------------------------------------- [ff9mapkit netsync F3.3] C3
#: What each C3 capability is, as the engine publishes it (an ABSENT key = an engine that cannot, never "nothing").
_NEEDS = {
    "ring": "the section-7 dialogue ring (netsync.wire >= 14, memoria-patch s98)",
    "keys": "the script-key relay (netsync.key_hold, s99)",
    "tape": "the tap-record bench (netsync.tap_record, s99)",
}


def _caps(st) -> SimpleNamespace:
    """The C3 capabilities the engine ADVERTISES in its `netsync` block (additive keys under protocol 5)."""
    ns = _ns(st)
    wire = ns.get("wire")
    ring = isinstance(wire, int) and not isinstance(wire, bool) and wire >= 14
    return SimpleNamespace(ring=ring, keys="key_hold" in ns, tape="tap_record" in ns, wire=wire)


_RAW_NOTED: set = set()


def _ns_verb(g, sub: str, *args):
    """`netsync <sub> [args]` -- through the driver when it knows the sub-verb, else as a raw step (module note: today's
    driver predates `host` / `tap-record` / `replay`). The agent's refusals come back either way, as HarnessError."""
    known = getattr(g, "NETSYNC_SUBVERBS", None)
    if known is None or sub in known:
        return g.netsync(sub, *args)
    if sub not in _RAW_NOTED:
        _RAW_NOTED.add(sub)
        g.note(f"driver predates `netsync {sub}` (not in Session.NETSYNC_SUBVERBS) -- sent as a raw step; the agent's "
               f"own gates still apply")
    g.send("netsync " + " ".join([sub, *(str(a) for a in args)]), timeout=20.0)
    return g.state


def _hv(g, op: str, *args):
    """The bench HOST: `netsync host <op> [n ...]` (selftest role + bench + the bench lock)."""
    return _ns_verb(g, "host", op, *args)


def _c3_phase(g, lv, c, name: str, needs, fn, *args) -> None:
    """A C3 bench: run only on an engine that ADVERTISES what it needs. Otherwise ONE check records the missing
    capability as FAILED and nothing runs -- so on a pre-C3 engine none of the bench's checks can pass (module note)."""
    caps = _caps(g.state)
    missing = [n for n in needs if not getattr(caps, n)]
    if missing:
        g.note(name)
        g.check(False, f"{name}: the engine has " + " and ".join(_NEEDS[n] for n in missing),
                f"absent -- a pre-C3 engine (wire={caps.wire!r}); this bench is NOT run, so none of its checks pass here")
        return
    _phase(g, lv, c, name, fn, *args)


def _host_until_closed(g, first_page: str, *, max_pages: int = MAX_PAGES):
    """Drive the open line to its close with bench-host ADVs (`host adv`, each its window's own closes test).
    Returns (pages, sends)."""
    pages, sends = [first_page], 0
    for _ in range(max_pages):
        before = g.state
        if not before.dialog_open or before.choice is not None or _ignores_input(before):
            break
        _hv(g, "adv")
        sends += 1
        last = pages[-1]
        st = _poll(g, lambda s: (not s.dialog_open) or s.choice is not None or (s.text.strip() and s.text != last),
                   6.0, "the ring's ADV to page or close the line")
        if st is None or not st.dialog_open or st.choice is not None:
            break
        pages.append(st.text)
    return pages, sends


def _tidy_bench_host(g) -> None:
    """Between benches, with the bench lock back ON (`host` rides it): a C3 bench that failed half-way must not hand
    the next one its levers -- the bench host's open set would CLAIM the next window (it never orphans), a frozen
    heartbeat would drop the next lock 10 s in, a menu/battle flag would change its chip."""
    if not _caps(g.state).ring:
        return
    ns = _ns(g.state)
    for key, op in (("host_frozen", "freeze"), ("host_menu", "menu"), ("host_battle", "battle")):
        if ns.get(key):
            _hv(g, op, 0)
    if ns.get("host_open"):
        _hv(g, "shut")


def _control_back(g, what: str, timeout: float = 6.0):
    """Control back and the screen empty (between two relayed opens inside one bench)."""
    st = _poll(g, lambda s: s.control and not s.dialog_open, timeout, f"control back {what}")
    g.wait_frames(10)
    return st


# ------------------------------------------------------------------------------------------ the run
def run(g, field: int = FIELD):
    g.note("F3.2 C2 host-authoritative dialogue + F3.3 C3 ring / key relay: the solo benches (lock from open, per-key "
           "apply, orphan, release; section-7 delivery, cursor mirror, closes bit, KEY relay, record/replay, stall)")
    g.newgame()
    g.warp(field)
    g.wait_frames(60)
    g.calibrate_axes()
    run_mark = _mark(g)                  # R-B2: the masked-poll line is latched once per field per reader

    # ---- the forced selftest role, the contract, A11 ----------------------------------------------------
    st = g.netsync("selftest", 1)
    ns = _ns(st)
    g.check(st.netsync is not None and ns.get("selftest") and ns.get("instance") and ns.get("forced"),
            "the harness forced the selftest role for this process (Memoria.ini untouched)", repr(st.netsync))
    contract = ns.get("dialogue")
    legacy = FORCE_CALIBRATE or contract != "authority"
    g.note(f"mode: {'CALIBRATION (the pre-F3.2 procedure: l1 / Confirm)' if legacy else 'F3.2 (lock/hostscene/click)'}"
           f" -- netsync.dialogue={contract!r}, COOP_CALIBRATE={'1' if FORCE_CALIBRATE else 'unset'}")
    g.check(contract == "authority",
            "the engine publishes the F3.2 dialogue contract (netsync.dialogue == 'authority')", f"dialogue={contract!r}")
    gates = ("bench", "lock", "lock_engaged", "suppress")
    g.check(all(ns.get(k) is False for k in gates),          # PUBLISHED and False: an absent key is not "closed"
            "every dialogue gate is published and closed by default (bench off, lock off, not engaged, no suppress)",
            f"missing={[k for k in gates if k not in ns]} {repr(ns)[:300]}")
    proof = _poll(g, lambda s: _count(_log_lines(g), "dialogue authority selftest:") >= 1, 8.0,
                  "the selftest proof block to log the dialogue authority self-test")
    lines = _log_lines(g)
    g.check(proof is not None and _count(lines, "dialogue authority selftest: OK (") >= 1
            and _count(lines, "dialogue authority selftest: FAIL") == 0,
            "A11: NetSyncDialog.SelfTest logged OK (host-scene machine, settle clock, orphan step, inbox)",
            _grep(lines, "selftest:", limit=400))
    _rb0_codec(g, lines)
    caps = _caps(g.state)
    g.note(f"C3 capabilities: ring={caps.ring} (wire={caps.wire!r}) keys={caps.keys} tape={caps.tape}")
    lv = _Levers(g, legacy)

    # ---- the references, measured LOCALLY with every lever off -----------------------------------------
    c = _references(g, lv)
    if c is None:
        return
    c.run_mark = run_mark
    lv.engage()
    st = g.state
    g.check(_ns(st).get("lock_engaged") is True and not st.dialog_open,
            "the bench lock engaged with no line open (bench + lock + hostscene)", repr(_ns(st))[:300])

    _phase(g, lv, c, "A1 lock from open", _a1_lock_from_open)
    _phase(g, lv, c, "A1v vanilla parity (lock off)", _a1v_vanilla)
    _phase(g, lv, c, "A2 choice: cursor lock + host pick", _a2_choice)
    _phase(g, lv, c, "A2b out-of-range host pick", _a2b_out_of_range)
    _phase(g, lv, c, "A5 choice event held until IsChoiceReady", _a5_choice_held)
    _phase(g, lv, c, "A4 per-key FIFO", _a4_per_key)
    _phase(g, lv, c, "A8 / R-B2 [NFOC] polled page + the KEY relay", _a8_polled_page)
    _phase(g, lv, c, "A3 no hand-back, then the orphan", _a3_no_handback)
    _phase(g, lv, c, "A6 link dead", _a6_link_dead)
    _phase(g, lv, c, "A7 panic unlock", _a7_unlock, field)

    # ---- [ff9mapkit netsync F3.3] C3: the section-7 ring, the key relay, record/replay ---------------------
    _c3_phase(g, lv, c, "R-B1 ring delivery, dedup, gap, healing, epoch", ("ring",), _rb1_ring)
    _c3_phase(g, lv, c, "R-B4 cursor mirror + the open-set claim", ("ring",), _rb4_cursor_mirror)
    _c3_phase(g, lv, c, "R-B5 closes bit / fewer pages", ("ring",), _rb5_closes_bit)
    _c3_phase(g, lv, c, "R7 chip variants", ("ring",), _r7_chips)
    _c3_phase(g, lv, c, "R-B2g the KEY ordering guard", ("ring", "keys"), _rb2g_key_guard)
    _c3_phase(g, lv, c, "R-B3 tap-record / replay", ("ring", "keys", "tape"), _rb3_record_replay)
    _c3_phase(g, lv, c, "R-B6 hung host", ("ring",), _rb6_host_stall)

    _reset_releases(g, lv)
    _a12_vanilla(g, lv, c)
    _rb7_vanilla_poll(g, c)


def _drag_control(g, lv) -> None:
    """A2's drag CONTROL, on the keeper's menu opened LOCALLY (bench and lock off): the same `netsync drag -80` A2
    sends must move an UNLOCKED cursor (DialogManager.OnDrag: dy < -50 -> MoveCurrentChoice(+1)). Without it a drag
    seam that silently did nothing would pass A2's "the drag never moved the locked cursor". Calibration has no drag
    verb (module note): skipped there. Leaves the cursor off the default -- the caller's choose() steers back."""
    if lv.legacy:
        g.note("drag control: skipped (calibration: the pre-F3.2 DLL has no `netsync drag`)")
        return
    st = _poll(g, _choice_ready, 6.0, "the keeper's menu to be ready for the drag control")
    if st is None:
        g.check(False, "drag control: the keeper's menu was ready for it", repr(g.state))
        return
    before = int(st.choice.get("selected", -1))
    active = list(st.choice.get("active") or range(int(st.choice.get("count", 0))))
    pos = active.index(before) if before in active else -1
    if not 0 <= pos < len(active) - 1:
        g.check(False, "drag control: the menu's cursor rests on a row with one below it",
                f"selected={before} active={active}")
        return
    want = active[pos + 1]
    why = _try(g, "drag -80", lv.drag, -80)
    moved = _poll(g, lambda s: s.choice is not None and int(s.choice.get("selected", -1)) != before, 2.0,
                  "the drag to move the unlocked cursor")
    after = int(moved.choice.get("selected", -1)) if moved is not None else before
    g.check(why is None and after == want,
            "drag control: with the lock OFF `netsync drag -80` moved the cursor one row down (A2's drag can fail)",
            why or f"selected {before} -> {after} (want {want})")


def _references(g, lv):
    """Uids, transcripts and follow-ups from LOCAL talks (bench off): the yardsticks every bench compares to."""
    g.walk_to(*WEST, tolerance=45, strict=False)
    opened = g.interact(timeout=6.0)
    if opened is None or opened.choice is not None:
        g.check(False, "the scribe opened a plain window locally", repr(opened))
        return None
    west_uid = _listener(opened)
    g.check(not _ignores_input(opened), "the scribe's window accepts Confirm (no [NFOC]/[TIME])",
            repr(opened.raw_texts)[:200])
    local_pages = list(dict.fromkeys([opened.text] + g.advance(max_pages=MAX_PAGES)))
    g.check(0 <= west_uid < 255 and len(local_pages) >= 1 and not g.state.dialog_open,
            "the scribe's window paged to its close by the player's Confirm (the reference transcript)",
            f"uid={west_uid}; {len(local_pages)} page(s): {local_pages[0][:50]!r}")
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the scribe")
    g.wait_frames(20)

    g.walk_to(*EAST, tolerance=45, strict=False)
    menu = g.interact(timeout=6.0)
    if menu is None or menu.choice is None:
        g.check(False, "the keeper opened its menu locally", repr(menu))
        return None
    keeper_uid = _listener(menu)
    ready = g.wait_for(_choice_ready, timeout=6.0, what="the keeper's menu to be ready")
    default_idx = int(ready.choice.get("selected", -1))
    names = g.options()
    want = WANT if WANT in names else names[min(3, len(names) - 1)]
    want_idx = g.option_index(want)
    story_idx = g.option_index(STORY) if STORY in names else 0
    close_idx = g.option_index(CLOSE) if CLOSE in names else int(ready.choice.get("count", 1)) - 1
    g.check(0 <= keeper_uid < 255 and keeper_uid != west_uid and default_idx >= 0,
            "the keeper's uid, its default row and its named rows were read off the live menu",
            f"uid={keeper_uid} default={default_idx} {want!r}={want_idx} {STORY!r}={story_idx} {CLOSE!r}={close_idx}")
    g.choose(want_idx)                   # the same Down presses A2 makes -- they MOVE the cursor here
    local_follow = _follow_up(g)
    g.check(bool(local_follow.strip()), f"choosing {want!r} locally leads to a window", local_follow[:80])
    g.check(_clear(g, close_idx), "the screen cleared after the local choice", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the local choice")
    g.wait_frames(20)

    g.walk_to(*EAST, tolerance=45, strict=False)
    menu = g.interact(timeout=6.0)
    if menu is None or menu.choice is None:
        g.check(False, "the keeper re-opened its menu locally (the default's reference)", repr(menu))
        return None
    _drag_control(g, lv)                 # A2's drag control, on this unlocked menu (select() steers back after)
    g.choose(default_idx)
    local_default_follow = _follow_up(g)
    g.check(bool(local_default_follow.strip()), f"the default row ({default_idx}) locally leads to a window",
            local_default_follow[:80])
    g.check(_clear(g, close_idx), "the screen cleared after the default's reference", repr(g.state))
    g.wait_for(lambda s: s.control, timeout=6.0, what="control back after the references")
    g.wait_frames(20)
    return SimpleNamespace(west_uid=west_uid, keeper_uid=keeper_uid, local_pages=local_pages,
                           default_idx=default_idx, want=want, want_idx=want_idx, story_idx=story_idx,
                           close_idx=close_idx, local_follow=local_follow,
                           local_default_follow=local_default_follow)


# ------------------------------------------------------------------------------------------ the benches
def _a1_lock_from_open(g, lv, c):
    mark = _mark(g)
    o0 = _ns(g.state).get("orphan_closes")
    st = _open_by_relay(g, c.west_uid)
    first = st.text
    st = _tracked(g)
    w = _front(st)
    win, text = _key(st)
    g.check(_ns(st).get("suppress") is True,
            "A1: the guest's own dialogue input is swallowed from the line's first frame (suppress), before any host event",
            repr(_ns(st))[:300])
    g.check(w is not None and w.get("cls") == "locked" and not w.get("inh"),
            "A1: the relayed line opened LOCKED (windows[].cls), before any host event", repr(_wins(st)))
    g.check(_ns(st).get("chip") == CHIP_FOLLOWING, "A1: the chip reads 'following the host's conversation'",
            repr(_ns(st).get("chip")))
    fresh = _new(g, mark)
    g.check(win is not None and _count(fresh, f"dialogue lock: win {win} text {text} opened locked") == 1,
            "A1: the engine logged the line opening locked, once", _grep(fresh, "dialogue"))
    g.shot("authority-A1-locked")

    page0 = (w or {}).get("page")
    for _ in range(3):
        g.press("confirm", 4)
        g.wait_frames(12)
    # a held Confirm, with the turbo key (RightBumper: TurboDialog's synthesized confirm) held over it
    g.send("hold confirm 45", "hold r1 45", "wait 50")
    clicks = []
    for _ in range(2):
        clicks.append(_try(g, "click", lv.click))
        g.wait_frames(12)
    # (no drag / arrow here: on a PLAIN window stock OnDrag and the arrows act on nothing -- A2 carries them)
    after = g.state
    fa = _front(after)
    fresh = _new(g, mark)
    # BEHAVIOURAL half -- keys the old DLL publishes too, so calibration's red here is the old behaviour
    g.check(after.dialog_open and after.text == first,
            "A1: Confirm x3, a held Confirm (+turbo key) and two clicks left the line open on the same text",
            f"open={after.dialog_open} text_same={after.text == first} text={after.text[:60]!r}")
    # F3.2-key half
    g.check(fa is not None and fa.get("page") == page0 and fa.get("cls") == "locked",
            "A1: ...on the same tracked page, still LOCKED (windows[])",
            f"page {page0}->{(fa or {}).get('page')} cls={(fa or {}).get('cls')}")
    g.check(not any(clicks), "A1: the click seam was exercised (both `netsync click`s were accepted)",
            "; ".join(c for c in clicks if c))
    g.check(_ns(after).get("orphan_closes") == o0 and o0 is not None
            and _count(fresh, "closed by its own script/timer") == 0 and not _applied(fresh, win, text),
            "A1: no close of any kind meanwhile (no orphan close, no self-attributed close, no apply)",
            _grep(fresh, "closed", "orphan"))

    pages, injects = _inject_until_closed(g, first)
    after = g.state
    fresh = _new(g, mark)
    applied = _applied(fresh, win, text)
    g.check(not after.dialog_open and injects == len(c.local_pages) and pages == c.local_pages,
            "A1: host advances paged the line exactly once each, and the transcript equals the local Confirm one",
            f"{injects} inject(s); host={pages!r}\n    local={c.local_pages!r}")
    g.check(len(applied) == injects and injects > 0 and _count(fresh, "did not advance") == 0,
            "A1: one 'advanced/closed (host seq N)' line per host event, never a retry",
            f"{len(applied)} apply line(s) for {injects} inject(s): {applied!r}")
    # A close runs Hide -> CloseAnimation -> Reset (Idle) -> AfterHidden, and only AfterHidden takes the window out
    # of ActiveDialogList -- so for a frame or two the tracker still lists an Idle line (suppress is already
    # down). Give that one tracker tick to land; a line still listed a second later is a real leak.
    settled = _poll(g, lambda s: not _wins(s), 1.0, "the closed line to leave the tracker") or g.state
    g.check(not _wins(settled) and not _ns(settled).get("suppress") and (_ns(settled).get("inbox") or {}).get("count") == 0,
            "A1: after the close nothing is tracked, nothing suppressed, nothing left in the inbox",
            f"windows={_wins(settled)!r} suppress={_ns(settled).get('suppress')} inbox={_ns(settled).get('inbox')!r}")


def _a1v_vanilla(g, lv, c):
    lv.lock(False)
    st = _poll(g, lambda s: _ns(s).get("lock_engaged") is not True, 3.0, "the lock to disengage") or g.state
    st = _open_by_relay(g, c.west_uid)
    g.wait_frames(10)
    st = g.state
    g.check(st.dialog_open and not _ns(st).get("suppress") and not _wins(st),
            "A1v: with the lock OFF the same relayed line opens untracked and unsuppressed", repr(_ns(st))[:300])
    first = st.text
    paged, why = _click_pages(g, lv)
    s = g.state
    g.check(paged, "A1v: with the lock off a click pages the line (stock DialogManager.OnClick) -- A1's control",
            why or repr(s))
    seen = [first] + ([s.text] if s.dialog_open and s.text.strip() and s.text != first else [])
    pages = list(dict.fromkeys(seen + (g.advance(max_pages=MAX_PAGES) if g.state.dialog_open else [])))
    g.check(pages == c.local_pages and not g.state.dialog_open,
            "A1v: click + Confirm walked the same transcript as the local reference",
            f"vanilla={pages!r}\n    local={c.local_pages!r}")


def _a2_choice(g, lv, c):
    mark = _mark(g)
    st = _open_by_relay(g, c.keeper_uid, choice=True)
    st = _tracked(g)
    win, text = _key(st)
    sel0 = int(st.choice.get("selected", -1)) if st.choice else -1
    g.check(_ns(st).get("suppress") is True and (_front(st) or {}).get("cls") == "locked" and sel0 == c.default_idx,
            "A2: the relayed menu opened locked, on its default row", f"sel={sel0} default={c.default_idx} {_wins(st)!r}")
    seen, refused = [], []
    # `drag -80` only: from the default row 0, `drag 80` (MoveCurrentChoice(-1)) clamps -- a no-op on any engine
    for act in (lambda: g.press("down", 4), lambda: g.press("down", 4),
                lambda: refused.append(_try(g, "drag -80", lv.drag, -80))):
        act()
        g.wait_frames(2)
        s = g.state
        seen.append(int(s.choice.get("selected", -1)) if s.choice else None)
    g.shot("authority-A2-cursor")
    g.check(all(x == sel0 for x in seen) and not any(refused),
            "A2: Down x2 and a `drag -80` never moved the locked menu's SelectChoice (the reference choose() and the "
            "drag control moved it unlocked)",
            f"selected after each: {seen} (opened on {sel0}); {'; '.join(r for r in refused if r)}")
    g.netsync("choice", c.want_idx)
    follow = _follow_up(g)
    fresh = _new(g, mark)
    applied = _applied(fresh, win, text)
    g.check(bool(follow.strip()) and follow == c.local_follow,
            f"A2: the host's pick ({c.want!r}) lands the SAME follow-up as a local choose({c.want_idx})",
            f"host={follow[:80]!r}\n    local={c.local_follow[:80]!r}")
    g.check(len(applied) == 1 and applied[0][0] == "closed" and applied[0][2] == c.want_idx,
            f"A2: exactly one 'closed (host seq N, choice {c.want_idx})' line for the menu", repr(applied))


def _a2b_out_of_range(g, lv, c):
    mark = _mark(g)
    st = _open_by_relay(g, c.keeper_uid, choice=True)
    count = int(st.choice.get("count", 0))
    bad = count + 40
    # the guest's cursor: calibration's DLG-10 discriminator -- the OLD DLL moves it and its fallback commits it.
    # Under the F3.2 lock it cannot leave the default, so this DLL cannot show "never the guest's cursor".
    g.press("down", 4)
    g.wait_frames(8)
    g.netsync("choice", bad)
    follow = _follow_up(g)
    fresh = _new(g, mark)
    hits = [m for m in (re.search(rf"host choice {bad} is out of range on win (\d+) text (\d+) -- its default \((-?\d+)\) instead",
                                  ln) for ln in fresh) if m]
    g.check(len(hits) == 1 and int(hits[0].group(3)) == c.default_idx,
            f"A2b: index {bad} of {count} fell back to the menu's DEFAULT ({c.default_idx}), logged once",
            _grep(fresh, "out of range", "host choice"))
    g.check(bool(follow.strip()) and follow == c.local_default_follow,
            "A2b: ...and landed the default's local follow-up (on this DLL the locked cursor sits on the default "
            "anyway; the guest's-cursor case is calibration's)",
            f"host={follow[:80]!r}\n    local default={c.local_default_follow[:80]!r}")


def _a5_choice_held(g, lv, c):
    mark = _mark(g)
    g.netsync("talk", c.keeper_uid)
    st = _poll(g, lambda s: s.dialog_open, 6.0, "the keeper's menu window to exist")
    if st is None:
        raise HarnessError(f"the relayed start for uid {c.keeper_uid} opened nothing within 6s")
    ready_at_inject = _choice_ready(st)
    g.netsync("choice", c.want_idx)      # the instant the window is up -- before its choice may be ready
    follow = _follow_up(g)
    fresh = _new(g, mark)
    # the precondition: without it this run sent a LATE event and proved nothing about holding an early one
    g.check(ready_at_inject is False,
            "A5: the choice event was sent while the menu was not yet ready (the last sample before the send)",
            f"choice ready at the send: {ready_at_inject}; {st.choice!r} group={st.menu_group!r}"[:300])
    queued = [m for m in (_QUEUED.search(ln) for ln in fresh) if m and m.group(5) == "1"]
    win, text = (int(queued[0].group(3)), int(queued[0].group(4))) if queued else (None, None)
    applied = _applied(fresh, win, text)
    g.check(len(queued) == 1 and len(applied) == 1 and applied[0][0] == "closed" and applied[0][2] == c.want_idx
            and _count(fresh, f"did not advance win {win} text {text}") == 0,
            "A5: the early choice event was held through the open, the typewriter and MinShowMs, then applied "
            "exactly once (no retry) -- not DLG-7 itself (module note)",
            f"queued={len(queued)} applied={applied!r}")
    g.check(bool(follow.strip()) and follow == c.local_follow, "A5: ...and it landed the same follow-up as the local pick",
            f"host={follow[:80]!r}\n    local={c.local_follow[:80]!r}")


def _a4_per_key(g, lv, c):
    mark = _mark(g)
    st = _open_by_relay(g, c.west_uid)
    first = st.text
    st = _tracked(g)
    win, text = _key(st)
    g.netsync("unmatched")               # a stranger AHEAD in the inbox: win 15 / text 0xFFFF
    g.netsync("advance")                 # ...then the open line's own event
    st = _poll(g, lambda s: (not s.dialog_open) or (s.text.strip() and s.text != first), 4.0,
               "the open line's event to apply past the stranger")
    after = g.state
    fresh = _new(g, mark)
    stranger = [h for h in _heads(after) if h.get("win") == 15 and h.get("text") == 0xFFFF]
    # behavioural half (old-DLL keys only) -- a regression check: the OLD bench pages here too (module note)
    g.check(st is not None,
            "A4: the open line paged with an unmatched event queued AHEAD of its own (it blocked nothing)",
            f"open={after.dialog_open} text={after.text[:60]!r}")
    g.check(len(_applied(fresh, win, text)) == 1,
            "A4: ...by its own host event: one apply line for its key (per-key FIFO)", _grep(fresh, "dialogue:"))
    # ('tried' is not asserted: it is set only by an apply onto a window of key 15/0xFFFF, which cannot exist)
    g.check(len(stranger) == 1,
            "A4: the stranger is still queued -- nothing consumed it", repr(_heads(after)))


def _a8_polled_page(g, lv, c):
    st = _open_by_relay(g, c.keeper_uid, choice=True)
    g.netsync("choice", c.story_idx)     # the host picks the polled story page
    page = _poll(g, lambda s: s.choice is None and s.dialog_open and _ignores_input(s), 6.0,
                 "the [NFOC] polled story page to open")
    if page is None:
        raise HarnessError(f"row {c.story_idx} ({STORY!r}) did not open a [NFOC] polled page")
    st = _poll(g, lambda s: any(w.get("inh") for w in _wins(s)), 2.0, "the tracker to register the polled page") or g.state
    inh = [w for w in _wins(st) if w.get("inh")]
    g.check(bool(inh) and _ns(st).get("suppress") is False,
            "A8: the polled page is tracked as input-inhibited and does NOT raise suppress (FlagButtonInh excluded)",
            f"windows={_wins(st)!r} suppress={_ns(st).get('suppress')!r}")
    g.check(_ns(st).get("chip") == CHIP_HOST_SCENE,
            "A8: the chip reads 'the host is in a scene' -- a polled strip is not a conversation", repr(_ns(st).get("chip")))
    g.check((_ns(st).get("inbox") or {}).get("count") == 0,
            "A8: the menu's applied choice event left the inbox (a regression guard -- this bench fabricates no event "
            "for the polled page, LAW :1369)", repr(_ns(st).get("inbox")))
    g.shot("authority-A8-polled")
    win, text = (inh[0]["win"], inh[0]["text"]) if inh else (None, None)
    first = page.text
    _rb2_key_relay(g, lv, c, win, text, first)


def _rb2_key_relay(g, lv, c, win, text, first: str) -> None:
    """[ff9mapkit netsync F3.3] R-B2 on the polled page A8 opened. The C2 GAP check that stood here ("the guest's own
    Confirm still closes it") is retired: on a C3 engine the page's script poll is the HOST's. The LAW :1369 refusal
    and the hold barrage run on ANY engine -- on s96 both go red by BEHAVIOUR (module note); the KEY half needs s99.
    Every "page left" verdict judges the PAGE leaving (no [NFOC]/[TIME] text left on screen), not the screen emptying:
    a handler that went back to its menu (journalfield.talk_body's while latch) would re-open the menu a few ticks
    after the page, and "the screen emptied" would then read only the gap between them."""
    caps = _caps(g.state)
    # LAW :1369 at the call site: no bench verb fabricates a confirm-advance for an input-inhibited window. (Before any
    # guest input -- on s96 the barrage below closes the page.)
    why = _try(g, "advance at the polled page", g.netsync, "advance")
    g.check(why is not None and "LAW :1369" in why,
            "R-B2: `netsync advance` aimed at the polled page is REFUSED, naming LAW :1369 (no confirm-advance is ever "
            "fabricated for an input-inhibited window)",
            why or "ACCEPTED -- the bench fabricated a confirm-advance for an [NFOC] window (the pre-s99 bench)")
    if caps.ring:
        why = _try(g, "host adv at the polled page", _hv, g, "adv")
        g.check(why is not None and "LAW :1369" in why,
                "R-B2: ...and so is the bench host's `host adv` (the ring's own verb)", why or "ACCEPTED")
    served0 = _ns(g.state).get("key_served")
    reader = -1
    if caps.keys:
        st = _poll(g, lambda s: _ns(s).get("key_hold") is True and isinstance(_ns(s).get("key_reader"), int)
                   and _ns(s)["key_reader"] >= 0, 2.0, "the script-key lock to mask the page's poll") or g.state
        reader = _ns(st).get("key_reader", -1)
        g.check(_ns(st).get("key_hold") is True and isinstance(reader, int) and reader >= 0,
                "R-B2: the script-key lock holds the page (key_hold) and publishes its polling uid (key_reader)",
                f"key_hold={_ns(st).get('key_hold')!r} key_reader={reader!r}")

    # the HOLD -- behavioural (keys and lines the s96 DLL publishes too): its red there IS the C2 gap
    mark = _mark(g)
    for _ in range(3):
        g.press("confirm", 4)
        g.wait_frames(12)
    clicks = []
    for _ in range(2):
        clicks.append(_try(g, "click", lv.click))
        g.wait_frames(12)
    g.wait_frames(20)
    after = g.state
    fresh = _new(g, mark)
    g.check(after.dialog_open and _ignores_input(after) and after.text == first
            and _count(fresh, f"dialogue: win {win} text {text} closed by its own script/timer") == 0,
            "R-B2: Confirm x3 and two clicks left the polled page OPEN on the same text -- its script's poll answers "
            "the HOST (on s96 the guest's own Confirm closed it: the C2 gap)",
            f"open={after.dialog_open} polled={_ignores_input(after)} same={after.text == first}; {_grep(fresh, 'closed')}")
    g.check(not any(clicks), "R-B2: the click seam was exercised (both `netsync click`s were accepted)",
            "; ".join(x for x in clicks if x))
    if not caps.keys:
        g.check(False, "R-B2: the engine has " + _NEEDS["keys"],
                f"absent -- a pre-s99 engine (wire={caps.wire!r}); the KEY half of R-B2 is NOT run")
        return
    if not (after.dialog_open and _ignores_input(after)):
        raise HarnessError("the polled page closed under the guest's own input -- the KEY half has no page to drive")

    # the log names the polling uid (latched ONCE per field per reader -- searched from the run's start)
    lines = _log_lines(g)[c.run_mark:]
    named = sorted({int(m.group(1)) for m in (_MASKED.search(ln) for ln in lines) if m})
    g.check(reader in named,
            f"R-B2: the log names the polling uid {reader} ('script button-poll by uid N (the host drives this scene) "
            f"suppressed')", f"uids named: {named}; {_grep(lines, 'script button-poll')}")

    # a KEY for the WRONG uid: held, closes nothing
    wrong = c.west_uid if c.west_uid != reader else (reader + 1) % 255
    _hv(g, "key", wrong, KEY_CONFIRM)
    held = _poll(g, lambda s: any(k.get("uid") == wrong for k in (_ns(s).get("keys") or [])), 2.0,
                 f"the wrong-uid KEY ({wrong}) to reach keys[]")
    g.wait_frames(30)
    s = g.state
    g.check(held is not None and s.dialog_open and _ignores_input(s) and s.text == first
            and _ns(s).get("key_served") == served0,
            f"R-B2: a KEY for the WRONG uid ({wrong}) waits in keys[] and closes nothing (key_served stays {served0})",
            f"keys={_ns(s).get('keys')!r} open={s.dialog_open} served={_ns(s).get('key_served')!r}")

    # the RIGHT uid: the page closes through its own poll
    mark = _mark(g)
    _hv(g, "key", reader, KEY_CONFIRM)
    left = _poll(g, lambda s: not _ignores_input(s), 4.0, "the relayed press to close the page through its own poll")
    g.wait_frames(10)
    fresh = _new(g, mark)
    served = [i for i, ln in enumerate(fresh) if _served_to(ln, reader)]
    closed = [i for i, ln in enumerate(fresh) if f"dialogue: win {win} text {text} closed by its own script/timer" in ln]
    g.check(left is not None and len(served) == 1 and len(closed) == 1 and served[0] < closed[0],
            f"R-B2: `host key {reader} {KEY_CONFIRM}` (Confirm) closed the page THROUGH ITS OWN POLL -- one 'served to uid "
            f"{reader}'s poll' line, then 'closed by its own script/timer'",
            f"page left={left is not None}; {_grep(fresh, 'key relay', 'closed', limit=500)}")
    g.check(_ns(g.state).get("key_served") == served0 + 1,
            "R-B2: key_served went up by exactly one", f"{served0} -> {_ns(g.state).get('key_served')!r}")

    # both sides idle: the wrong-uid KEY, and a KEY for a reader whose poll has ENDED, expire UNSERVED.
    # [ff9mapkit netsync F3.3] This is the KeyIdleMs expiry ONLY. The second KEY is NOT a proof of "never served to a
    # control-on read": the keeper's B_KEYON lived only inside the closed page and nothing else on 30801 polls with
    # control on, so an engine that served control-on reads would still find no reader here (module note: SKIPPED).
    if _control_back(g, "after the polled page") is None:
        raise HarnessError("control never came back after the polled page closed")
    ns = _ns(g.state)
    exp0, served1 = ns.get("key_expired"), ns.get("key_served")
    mark = _mark(g)
    t0 = time.time()
    lv.scene(False)
    _hv(g, "key", reader, KEY_CONFIRM)   # the page's reader -- its poll ended with the page
    gone = _poll(g, lambda s: not any(k.get("uid") in (wrong, reader) for k in (_ns(s).get("keys") or [])),
                 KEY_IDLE_S + 5.0, "both KEYs to expire once both sides are idle")
    t1 = time.time()
    g.wait_frames(5)
    ns = _ns(g.state)
    fresh = _new(g, mark)
    g.check(gone is not None and t1 - t0 >= KEY_IDLE_S - EARLY_S and ns.get("key_expired") == exp0 + 2
            and ns.get("key_served") == served1,
            f"R-B2: with both sides idle (host scene down, control back) the wrong-uid KEY and a KEY for a reader whose "
            f"poll has ended expired UNSERVED after KeyIdleMs ({KEY_IDLE_S:.1f}s)",
            f"gone after {t1 - t0:.2f}s; expired {exp0} -> {ns.get('key_expired')!r}; served {served1} -> "
            f"{ns.get('key_served')!r}")
    g.check(_count(fresh, "expired -- both sides idle") == 2,
            "R-B2: ...two 'expired -- both sides idle' lines", _grep(fresh, "key relay"))
    lv.scene(True)


def _rb0_codec(g, lines) -> None:
    """[ff9mapkit netsync F3.3] R-B0: the same once-per-process proof line as A11 -- its C3 clauses (s98's RingScript,
    s99's KeyScript; pure, offline, at selftest start). BUILD IDENTITY only: SelfTest writes this description from
    literals whenever its whole `??` chain returned null, so the clauses cannot fail apart from A11's OK -- they name
    which scripts the build carries, not that each one ran (module note)."""
    ok = [ln for ln in lines if "dialogue authority selftest: OK (" in ln]
    line = ok[-1] if ok else ""
    ring = ("section 7: round trip", "seq wrap 65535->1", "gap>32 once", "truncated refused", "re-send once",
            "epoch reset w/o replay", "stall 10000 ms")
    miss = [p for p in ring if p not in line]
    g.check(bool(line) and not miss,
            "R-B0 (build identity): the OK proof line names the section-7 codec script (round trip, seq wrap 65535->1, "
            "a gap > 32 once, truncated refused, re-send once, epoch reset w/o replay, stall 10000 ms)",
            f"missing {miss}: ...{line[-220:]!r}" if line else "no OK proof line")
    keys = ("key relay: compact bits", "guard holds behind an earlier open driven line", "one press per reader per key tick")
    miss = [p for p in keys if p not in line]
    g.check(bool(line) and not miss,
            "R-B0 (build identity): ...and the script-key relay's KeyScript (compact bits, the ordering guard, one press "
            "per reader per key tick, expiry)", f"missing {miss}" if line else "no OK proof line")


def _a3_no_handback(g, lv, c):
    st = _open_by_relay(g, c.keeper_uid, choice=True)
    st = _tracked(g)
    win, text = _key(st)
    o0 = _ns(st).get("orphan_closes")
    mark = _mark(g)
    g.netsync("unmatched")
    settled_seen = []

    def sample():
        s = g.state
        hs = _ns(s).get("host_settled_ms")
        if hs is None or hs != -1:
            settled_seen.append(hs)
        return s

    # phase 1 -- QUIET: no guest input at all, past F3's DialogWaitMs. The old DLL logs its hand-back here ('dialog
    # frame ... timed out -- local advance restored'); mashing first would close its menu at once and the 8 s
    # clock would never be reached -- that is why the quiet phase comes first.
    t0 = time.time()
    quiet_closed = None
    while time.time() - t0 < QUIET_S:
        g.wait_frames(20)
        s = sample()
        if not s.dialog_open or s.choice is None:
            quiet_closed = round(time.time() - t0, 2)
            break
    quiet = g.state
    lines = [ln for ln in _log_lines(g) if "[NetSync]" in ln and "dialog" in ln]
    g.check(quiet_closed is None and _count(lines, "local advance restored") == 0 and _count(lines, "timed out") == 0,
            f"A3: {QUIET_S:.0f}s with no guest input, past F3's 8 s DialogWaitMs: the menu stayed up and no 'local "
            "advance restored' (or any dialogue timeout hand-back) was logged",
            f"closed after {quiet_closed}s; {_grep(lines, 'restored', 'timed out')}")
    # read inside PendingTtlMs (20 s): the stranger ages out of the inbox after that by design
    g.check(any(h.get("win") == 15 and h.get("text") == 0xFFFF for h in _heads(quiet)),
            "A3: the unmatched event is still queued after the quiet phase -- held, never drained", repr(_heads(quiet)))

    # phase 2 -- the guest mashes Confirm all through the hold
    t1 = time.time()
    closed_at = None
    while time.time() - t1 < HOLD_S:
        g.press("confirm", 4)
        g.wait_frames(20)
        s = sample()
        if not s.dialog_open or s.choice is None:
            closed_at = round(time.time() - t1, 2)
            break
    held = time.time() - t1
    s = g.state
    fs = _front(s)
    # behavioural half (old-DLL keys only) -- its calibration red: the first local Confirm closes the menu
    g.check(closed_at is None and held >= HOLD_S and s.dialog_open and s.choice is not None,
            f"A3: ...then the guest mashing Confirm for {HOLD_S:.0f}s: the menu holds",
            f"closed after {closed_at}s; held {held:.1f}s")
    # F3.2-key half
    g.check(fs is not None and fs.get("cls") == "locked" and _ns(s).get("lock_engaged") is True,
            "A3: ...still tracked LOCKED, under an engaged lock", f"front={fs!r} lock_engaged={_ns(s).get('lock_engaged')!r}")
    g.check(not settled_seen, "A3: the host never read settled while its scene was up (host_settled_ms -1 throughout)",
            f"settled samples: {settled_seen[:6]}")

    # the host's scene ends: the line is provably not on the host's screen
    t_before = time.time()
    lv.scene(False)
    t_after = time.time()
    orph = _poll(g, lambda s: (_front(s) or {}).get("cls") == "orphaned", ORPHAN_GRACE_S + 3.0,
                 "the line to turn orphaned")
    t_orph = time.time()
    g.check(orph is not None and t_orph - t_before >= ORPHAN_GRACE_S - EARLY_S
            and t_orph - t_after <= ORPHAN_GRACE_S + SLACK_S,
            f"A3: hostscene 0 -> the line turned 'orphaned' OrphanGraceMs ({ORPHAN_GRACE_S:.0f}s) later",
            f"after {t_orph - t_before:.2f}s (from the send) / {t_orph - t_after:.2f}s (from the ack)")
    if orph is not None:
        hs = _ns(orph).get("host_settled_ms")
        g.check(isinstance(hs, int) and hs >= ORPHAN_GRACE_S * 1000 and _ns(orph).get("chip") == CHIP_CLOSING,
                "A3: ...with the host read settled >= 2 s and the chip 'this line isn't on the host's screen'",
                f"host_settled_ms={_ns(orph).get('host_settled_ms')} chip={_ns(orph).get('chip')!r}")
    gone = _poll(g, lambda s: s.choice is None, AUTO_READ_S + 4.0, "the orphaned menu to auto-close")
    t_gone = time.time()
    g.check(gone is not None and t_gone - t_before >= ORPHAN_GRACE_S + AUTO_READ_S - EARLY_S
            and t_gone - t_after <= ORPHAN_GRACE_S + AUTO_READ_S + 2 * SLACK_S,
            f"A3: ...and auto-closed AutoReadMs ({AUTO_READ_S:.0f}s) after it was orphaned (reading pace)",
            f"closed {t_gone - t_orph:.2f}s after the orphan sample, {t_gone - t_before:.2f}s after the send")
    g.wait_frames(45)
    s = g.state
    fresh = _new(g, mark)
    auto = [int(m.group(1)) for m in (re.search(rf"dialogue orphan: win {win} text {text} auto-closed "
                                                r"\(host idle \d+s, choice (-?\d+)\)", ln) for ln in fresh) if m]
    g.check(auto == [c.close_idx] and not s.dialog_open,
            f"A3: one auto-close line, on the CANCEL row ({c.close_idx} = {CLOSE!r}), and no reply window opened",
            f"auto-close choices {auto}; dialog_open={s.dialog_open}; {_grep(fresh, 'orphan')}")
    g.check(o0 is not None and _ns(s).get("orphan_closes") == o0 + 1
            and _count(fresh, f"win {win} text {text} is not on the host's screen") == 1,
            "A3: orphan_closes went up by exactly one, after exactly one orphan line", f"{o0} -> {_ns(s).get('orphan_closes')}")
    g.check(_count(fresh, "closed by its own script/timer") == 0 and not _applied(fresh, win, text),
            "A3: zero input-driven or self-attributed closes -- the orphan rule closed it, nothing else",
            _grep(fresh, "closed"))
    lv.scene(True)


def _a6_link_dead(g, lv, c):
    _open_by_relay(g, c.west_uid)
    st = _tracked(g)
    g.check((_front(st) or {}).get("cls") == "locked", "A6: the relayed line opened locked", repr(_wins(st)))
    mark = _mark(g)
    t_before = time.time()
    lv.stale(True)
    t_after = time.time()
    held_late, released, hiccup = None, None, False
    while time.time() - t_before < LINK_GRACE_S + 4.0:
        s = g.state
        el = time.time() - t_before
        if _ns(s).get("lock_engaged") is True:
            if _ns(s).get("suppress") is True and s.dialog_open:
                held_late = el
            hiccup = hiccup or _ns(s).get("chip") == CHIP_HICCUP
        else:
            released = time.time()
            break
        g.wait_frames(1)
    g.check(held_late is not None and held_late >= LINK_GRACE_S - 0.25,
            f"A6: with the link reading dead the lock HOLDS the line ({LINK_GRACE_S - 0.25:.2f}s+ still locked)",
            f"last locked sample {held_late}s after the stale")
    g.check(hiccup, "A6: ...under the chip 'link hiccup -- holding this conversation for the host'", "")
    g.check(released is not None and released - t_before >= LINK_GRACE_S - EARLY_S
            and released - t_after <= LINK_GRACE_S + SLACK_S,
            f"A6: ...and released it LinkGraceMs ({LINK_GRACE_S:.0f}s) after the link died",
            f"released {None if released is None else round(released - t_before, 2)}s after the send")
    fresh = _new(g, mark)
    g.check(_count(fresh, "dialogue lock released -- the link has read dead for 3 s") == 1,
            "A6: one 'lock released -- the link has read dead' line", _grep(fresh, "dialogue lock"))
    st = g.state
    g.check(not _ns(st).get("suppress") and not _wins(st), "A6: released = nothing tracked, nothing suppressed",
            repr(_ns(st))[:300])
    g.check(_paged_by(g, lambda: g.press("confirm", 4)), "A6: the guest's own Confirm pages the released line", repr(g.state))
    lv.stale(False)


def _a7_unlock(g, lv, c, field):
    _open_by_relay(g, c.west_uid)
    st = _tracked(g)
    g.check((_front(st) or {}).get("cls") == "locked", "A7: the relayed line opened locked", repr(_wins(st)))
    mark = _mark(g)
    lv.unlock()
    st = _poll(g, lambda s: _ns(s).get("unlocked") is True and _ns(s).get("lock_engaged") is False, 2.0,
               "the panic unlock to drop the lock") or g.state
    g.check(_ns(st).get("unlocked") is True and _ns(st).get("lock_engaged") is False and not _ns(st).get("suppress"),
            "A7: `netsync unlock` dropped the lock on this field", repr(_ns(st))[:300])
    g.check(_paged_by(g, lambda: g.press("confirm", 4)), "A7: the guest's own Confirm pages the line after the unlock",
            repr(g.state))
    fresh = _new(g, mark)
    g.check(_count(fresh, f"dialogue lock released on field {field} (manual unlock)") == 1,
            "A7: one 'released on field N (manual unlock)' line", _grep(fresh, "dialogue lock"))
    _clear(g, c.close_idx)
    _poll(g, lambda s: s.control, 6.0, "control back before the reload")

    mark = _mark(g)
    if lv.legacy:
        lv.lock(False)                   # the old l1 pin holds control; the warp waits for a playable field
    g.warp(field)                        # the reload: the unlock lasts until the next field load
    if lv.legacy:
        lv.engage()
    g.wait_frames(30)
    st = _poll(g, lambda s: _ns(s).get("unlocked") is False and _ns(s).get("lock_engaged") is True, 5.0,
               "the lock to re-arm after the reload") or g.state
    fresh = _new(g, mark)
    g.check(_ns(st).get("unlocked") is False and _ns(st).get("lock_engaged") is True
            and _count(fresh, "dialogue lock re-armed (field load)") == 1,
            "A7: a field reload re-armed the lock (one 're-armed (field load)' line)", _grep(fresh, "dialogue lock"))
    _open_by_relay(g, c.west_uid)
    st = _tracked(g)
    g.check((_front(st) or {}).get("cls") == "locked" and _ns(st).get("suppress") is True,
            "A7: after the reload a relayed line opens LOCKED again", repr(_wins(st)))


# --------------------------------------------------------------- [ff9mapkit netsync F3.3] the C3 benches
def _wait_s(g, seconds: float) -> None:
    """Let `seconds` of WALL time pass (the engine's clocks are Environment.TickCount; the frame rate varies)."""
    t0 = time.time()
    while time.time() - t0 < seconds:
        g.wait_frames(3)


def _relay_scribe(g, c):
    """The scribe's plain line, opened by the host's relayed start and registered. -> (state, win, text, first page)."""
    st = _open_by_relay(g, c.west_uid)
    first = st.text
    st = _tracked(g)
    win, text = _key(st)
    return st, win, text, first


def _close_by_host(g, what: str) -> None:
    """Close whatever line is open with bench-host ADVs, then wait for control (between two opens in one bench)."""
    st = g.state
    if st.dialog_open and st.choice is None and not _ignores_input(st):
        _host_until_closed(g, st.text)
    if _control_back(g, what) is None:
        raise HarnessError(f"control never came back {what}")


def _rb1_ring(g, lv, c):
    # (a) delivery + dedup: one ADV, re-sent in the slot every bench tick, merged and applied once
    st, win, text, first = _relay_scribe(g, c)
    g.check((_front(st) or {}).get("cls") == "locked", "R-B1: the relayed scribe opened locked", repr(_wins(st)))
    mark = _mark(g)
    _hv(g, "adv")
    moved = _poll(g, lambda s: (not s.dialog_open) or (s.text.strip() and s.text != first), 4.0,
                  "the ring's ADV to page or close the line")
    _wait_s(g, 1.5)                      # dozens of re-sends of the same slot
    fresh = _new(g, mark)
    ns = _ns(g.state)
    applied = _applied(fresh, win, text)
    queued = [m for m in (_QUEUED.search(ln) for ln in fresh) if m and int(m.group(3)) == win and int(m.group(4)) == text]
    g.check(moved is not None and len(applied) == 1,
            "R-B1: `host adv` -- section 7 through the real codec -- paged/closed the relayed line exactly once",
            f"applied={applied!r}")
    g.check(len(queued) == 1 and isinstance(ns.get("head_seq"), int) and ns.get("last_seen") == ns.get("head_seq"),
            "R-B1: ...queued ONCE although the slot was re-sent every bench tick (merge dedup: last_seen == head_seq)",
            f"{len(queued)} 'queued' line(s); last_seen={ns.get('last_seen')!r} head_seq={ns.get('head_seq')!r}")
    _close_by_host(g, "after the delivery check")

    # (b) a GAP: events the ring no longer holds -- the line they were for falls to the orphan rule
    gaps0 = _ns(g.state).get("gaps")
    st, win, text, first = _relay_scribe(g, c)
    mark = _mark(g)
    _hv(g, "gap", GAP_N)
    seen = _poll(g, lambda s: isinstance(_ns(s).get("gaps"), int) and _ns(s)["gaps"] > gaps0, 2.0,
                 "the gap to be detected")
    _wait_s(g, 1.0)                      # "once": a re-sent slot must not re-detect it
    s = g.state
    fresh = _new(g, mark)
    g.check(seen is not None and _ns(s).get("gaps") == gaps0 + 1 and _count(fresh, "dialogue ring: GAP -- ") == 1,
            f"R-B1: `host gap {GAP_N}` was detected ONCE (gaps +1, one 'dialogue ring: GAP' line)",
            f"gaps {gaps0} -> {_ns(s).get('gaps')!r}; {_grep(fresh, 'GAP')}")
    g.check(s.dialog_open and s.text == first and (_front(s) or {}).get("cls") == "locked",
            "R-B1: ...the line those lost events were for stays open and locked (nothing for it arrived)", repr(_wins(s)))
    lv.scene(False)
    orph = _poll(g, lambda s: (_front(s) or {}).get("cls") == "orphaned", ORPHAN_GRACE_S + 3.0,
                 "the stranded line to turn orphaned")
    gone = _poll(g, lambda s: not s.dialog_open, (AUTO_READ_S + 1.0) * len(c.local_pages) + 3.0,
                 "the orphan rule to auto-close it")
    fresh = _new(g, mark)
    g.check(orph is not None and gone is not None
            and _count(fresh, f"dialogue orphan: win {win} text {text} auto-closed") >= 1,
            "R-B1: ...and once the host scene fell it went to the orphan rule (orphaned, then auto-closed)",
            f"orphaned={orph is not None} closed={gone is not None}; {_grep(fresh, 'orphan')}")
    lv.scene(True)
    _close_by_host(g, "after the orphan")

    # (c) HEALING (WIRE-1): an ADV sent while the link reads dead arrives the moment it comes back
    st, win, text, first = _relay_scribe(g, c)
    mark = _mark(g)
    lv.stale(True)
    _hv(g, "adv")
    _wait_s(g, HEAL_S)
    held = g.state
    fresh = _new(g, mark)
    g.check(held.dialog_open and held.text == first and not _applied(fresh, win, text)
            and _ns(held).get("lock_engaged") is True,
            f"R-B1 healing: with the link reading dead ({HEAL_S:.1f}s, inside LinkGraceMs) the ring's ADV has NOT "
            f"arrived -- the line holds, still locked",
            f"open={held.dialog_open} same={held.text == first} applied={_applied(fresh, win, text)!r} "
            f"lock_engaged={_ns(held).get('lock_engaged')!r}")
    lv.stale(False)
    healed = _poll(g, lambda s: (not s.dialog_open) or (s.text.strip() and s.text != first), 3.0,
                   "the link to come back and deliver the ADV")
    _wait_s(g, 0.7)
    fresh = _new(g, mark)
    g.check(healed is not None and len(_applied(fresh, win, text)) == 1 and _count(fresh, "dialogue lock released") == 0,
            "R-B1 healing: the moment the link came back the re-sent slot delivered that ADV, once -- a blip loses no "
            "line and releases no lock", f"{_grep(fresh, 'dialogue')}")
    _close_by_host(g, "after the healing check")

    # (d) EPOCH: a host relaunch -- the inbox drops, the baseline moves, the new session is not "already seen".
    # [ff9mapkit netsync F3.3] NOT a no-replay proof: the bench's `epoch` op empties its own ring (BenchHostOp), so there
    # is no old-epoch history in section 7 for a wrong guest to replay. No-replay is RingScript's, offline (R-B0).
    st, win, text, first = _relay_scribe(g, c)
    g.netsync("unmatched")               # a stranger in the inbox, to watch the epoch clear it
    queued = _poll(g, lambda s: (_ns(s).get("inbox") or {}).get("count", 0) >= 1, 2.0, "the stranger to be queued")
    e0 = _ns(g.state).get("epoch")
    mark = _mark(g)
    _hv(g, "epoch")
    st = _poll(g, lambda s: isinstance(_ns(s).get("epoch"), int) and _ns(s)["epoch"] not in (e0, -1), 2.0,
               "the guest to see the new epoch")
    g.wait_frames(5)
    ns = _ns(g.state)
    fresh = _new(g, mark)
    g.check(queued is not None and st is not None and (ns.get("inbox") or {}).get("count") == 0
            and ns.get("last_seen") == ns.get("head_seq"),
            "R-B1 epoch: `host epoch` (a host relaunch) -- a new epoch, the queued stranger dropped with the inbox, the "
            "baseline moved to the new head",
            f"epoch {e0!r} -> {ns.get('epoch')!r}; inbox={ns.get('inbox')!r}; last_seen={ns.get('last_seen')!r} "
            f"head_seq={ns.get('head_seq')!r}")
    g.check(_count(fresh, "dialogue ring: host epoch ") == 1
            and _count(fresh, "host epoch changed -- talk/intent/event/diorama dedup reset") == 1,
            "R-B1 epoch: ...one epoch line and one dedup-reset line (WIRE-6/CLB-4)", _grep(fresh, "epoch"))
    mark = _mark(g)
    _hv(g, "adv")
    after = _poll(g, lambda s: (not s.dialog_open) or (s.text.strip() and s.text != first), 4.0,
                  "the new epoch's first ADV to apply")
    fresh = _new(g, mark)
    g.check(after is not None and len(_applied(fresh, win, text)) == 1,
            "R-B1 epoch: ...and the new epoch's first ADV applies to the open line (its restarted seq is not read as "
            "'already seen')", _grep(fresh, "dialogue"))
    _close_by_host(g, "after the epoch check")

    # (e) a KEY with no host-owned button never reaches a poll
    ki0 = _ns(g.state).get("key_ignored")
    _hv(g, "key", 12, KEY_NO_HOST_BUTTON)
    st = _poll(g, lambda s: _ns(s).get("key_ignored") == ki0 + 1, 2.0, "the button-less KEY to be ignored")
    g.check(st is not None and not any(k.get("bits") == KEY_NO_HOST_BUTTON for k in (_ns(g.state).get("keys") or [])),
            "R-B1: a KEY carrying no host-owned button is refused at ingest (key_ignored +1, never in keys[])",
            f"key_ignored {ki0!r} -> {_ns(g.state).get('key_ignored')!r}; keys={_ns(g.state).get('keys')!r}")


def _rb4_cursor_mirror(g, lv, c):
    st = _open_by_relay(g, c.keeper_uid, choice=True)
    st = _tracked(g)
    win, text = _key(st)
    count = int(st.choice.get("count", 0)) if st.choice else 0
    sel0 = int(st.choice.get("selected", -1)) if st.choice else -1
    rows = [r for r in range(2, count) if r not in (sel0, c.close_idx)]
    if len(rows) < 2:
        raise HarnessError(f"the keeper's menu has too few rows for the mirror ({count} rows, default {sel0})")
    want, want2 = rows[0], rows[1]
    _hv(g, "open", want)                 # the host's open set: this (frontmost) window, its cursor on `want`
    st = _poll(g, lambda s: s.choice is not None and int(s.choice.get("selected", -1)) == want
               and _ns(s).get("cursor") == want, 1.5, "the host's cursor to land on the locked menu")
    ho = _ns(g.state).get("host_open") or []
    g.check(st is not None and any(o.get("win") == win and o.get("text") == text and o.get("cursor") == want for o in ho),
            f"R-B4: `host open {want}` (the host's open set) put the locked menu's cursor on {want} -- `cursor` reads it",
            f"selected={int(g.state.choice.get('selected', -1)) if g.state.choice else None} "
            f"cursor={_ns(g.state).get('cursor')!r} host_open={ho!r}")
    seen = []
    for _ in range(2):
        g.press("down", 4)
        g.wait_frames(3)
        s = g.state
        seen.append(int(s.choice.get("selected", -1)) if s.choice else None)
    g.wait_frames(6)
    s = g.state
    now = int(s.choice.get("selected", -1)) if s.choice else None
    # [ff9mapkit netsync F3.3] a C2 regression guard, NOT an R4 proof: DialogManager.OnItemSelect drops a guest's arrows
    # on a locked choice (IsGuestLockedChoice) before the mirror is involved, and no non-input cursor mover is reachable
    # here -- so a mirror that set the cursor once and never re-asserted it passes too (module note, R-B4).
    g.check(now == want, f"R-B4 (C2 regression guard): local Down presses leave the locked menu on the host's row "
            f"({want})", f"after each Down: {seen}; settled on {now}")
    g.shot("authority-RB4-mirror")
    _hv(g, "open", want2)
    st = _poll(g, lambda s: s.choice is not None and int(s.choice.get("selected", -1)) == want2
               and _ns(s).get("cursor") == want2, 1.5, "the cursor to follow the host's")
    g.check(st is not None, f"R-B4: ...and the highlight follows the host's cursor as it moves ({want} -> {want2})",
            f"selected={int(g.state.choice.get('selected', -1)) if g.state.choice else None}")

    # the open set CLAIMS the window: with the host scene down it is never orphaned
    o0 = _ns(g.state).get("orphan_closes")
    hold_s = ORPHAN_GRACE_S + AUTO_READ_S + 1.0
    t0 = time.time()
    lv.scene(False)
    lost = None
    while time.time() - t0 < hold_s:
        s = g.state
        if not s.dialog_open or s.choice is None or (_front(s) or {}).get("cls") != "locked":
            lost = round(time.time() - t0, 2)
            break
        g.wait_frames(10)
    # (two R4 rules hold it here, and this bench cannot tell them apart: the open-set CLAIM, and section 7's b2 --
    # a non-[NFOC] host line open -- which keeps the host from reading co-located-and-settled at all)
    g.check(lost is None and _ns(g.state).get("orphan_closes") == o0,
            f"R-B4: while the host's open set holds the menu (the claim + section 7 b2) it is never orphaned -- "
            f"{hold_s:.0f}s with the host scene down, still locked", f"lost after {lost}s; front={_front(g.state)!r}")
    mark = _mark(g)
    _hv(g, "shut")
    orph = _poll(g, lambda s: (_front(s) or {}).get("cls") == "orphaned", ORPHAN_GRACE_S + 3.0,
                 "the unclaimed menu to orphan")
    gone = _poll(g, lambda s: s.choice is None, AUTO_READ_S + 4.0, "the orphaned menu to auto-close")
    g.wait_frames(30)
    fresh = _new(g, mark)
    g.check(orph is not None and gone is not None and _ns(g.state).get("orphan_closes") == o0 + 1
            and _count(fresh, f"dialogue orphan: win {win} text {text} auto-closed") == 1,
            "R-B4: `host shut` (the open set empties) released the claim: the menu orphaned, then auto-closed once",
            f"orphaned={orph is not None} closed={gone is not None}; {_grep(fresh, 'orphan')}")
    lv.scene(True)


def _rb5_closes_bit(g, lv, c):
    # (a) FEWER PAGES: a non-closing ADV on the guest's LAST page is a no-op, consumed
    n = len(c.local_pages)
    st, win, text, first = _relay_scribe(g, c)
    page = first
    for _ in range(n - 1):               # to the last page (a single-page window is already there)
        _hv(g, "adv")
        nxt = _poll(g, lambda s: s.dialog_open and s.text.strip() and s.text != page, 4.0, "the next page")
        if nxt is None:
            raise HarnessError("the scribe's line did not page on to its last page")
        page = nxt.text
    _wait_s(g, MIN_SHOW_S + 0.4)         # the last page complete + MinShowMs: the event is judged at once
    mark = _mark(g)
    _hv(g, "adv", 0)
    noop = _poll(g, lambda s: _count(_new(g, mark), "-- consumed, no-op") >= 1, 3.0,
                 "the non-closing ADV to be consumed")
    g.wait_frames(15)
    s = g.state
    fresh = _new(g, mark)
    g.check(noop is not None and s.dialog_open and s.text == page and not _applied(fresh, win, text)
            and (_ns(s).get("inbox") or {}).get("count") == 0,
            "R-B5: a NON-closing ADV (`host adv 0`) on the guest's LAST page is consumed as a no-op ('... consumed, "
            "no-op') -- the line stays", f"open={s.dialog_open} same={s.text == page}; {_grep(fresh, 'dialogue')}")
    _hv(g, "adv")
    closed = _poll(g, lambda s: not s.dialog_open, 4.0, "the closing ADV to close the line")
    applied = _applied(_new(g, mark), win, text)
    g.check(closed is not None and len(applied) == 1 and applied[0][0] == "closed",
            "R-B5: ...and the host's closing ADV then closes it, once", repr(applied))
    if n < 2:
        g.note("R-B5 closes-bit CATCH-UP: SKIPPED -- the scribe's window is a single page on this deploy (30801's .mes "
               "carries no [PAGE]); the catch-up needs page 1 of >= 2 pages (the bit's codec is RingScript's, offline)")
        return

    # (b) THE CLOSES BIT: one closing ADV against page 1 pages the window through to its close
    if _control_back(g, "before the catch-up") is None:
        raise HarnessError("control never came back before the catch-up")
    st, win, text, first = _relay_scribe(g, c)
    _wait_s(g, MIN_SHOW_S + 0.4)
    mark = _mark(g)
    _hv(g, "adv", 1)
    seen = [first]
    t0 = time.time()
    while time.time() - t0 < n * (MIN_SHOW_S + 1.5) + 4.0:
        g.wait_frames(3)
        s = g.state
        if not s.dialog_open:
            break
        if s.text.strip() and s.text != seen[-1]:
            seen.append(s.text)
    s = g.state
    fresh = _new(g, mark)
    applied = _applied(fresh, win, text)
    g.check(not s.dialog_open and seen == c.local_pages,
            "R-B5: ONE closing ADV (`host adv 1`) on page 1 paged the window through every page to its close (the "
            "local transcript)", f"host={seen!r}\n    local={c.local_pages!r}")
    g.check(_count(fresh, f"closed win {win} text {text} on the host -- paging on to its close here") == 1
            and len(applied) == 1 and applied[0][0] == "closed",
            "R-B5: ...with one 'paging on to its close' line and ONE apply line ('closed (host seq N)')",
            f"applied={applied!r}; {_grep(fresh, 'paging on')}")


def _r7_chips(g, lv, c):
    st, win, text, first = _relay_scribe(g, c)
    g.check(_ns(st).get("chip") == CHIP_FOLLOWING, "R7: the locked line's chip reads 'following the host's conversation'",
            repr(_ns(st).get("chip")))
    _hv(g, "menu", 1)
    st = _poll(g, lambda s: _ns(s).get("chip") == CHIP_HOST_MENU, 1.5, "the 'host in a menu' chip")
    hf = _ns(g.state).get("host_flags")
    g.check(st is not None and isinstance(hf, int) and hf & HF_MENU,
            "R7: `host menu 1` (section 7 b4): the chip reads 'the host is in a menu -- waiting'",
            f"chip={_ns(g.state).get('chip')!r} host_flags={hf!r}")
    _hv(g, "menu", 0)
    st = _poll(g, lambda s: _ns(s).get("chip") == CHIP_FOLLOWING, 1.5, "the chip back to 'following'")
    g.check(st is not None, "R7: ...and back to 'following' once the host's menu closes", repr(_ns(g.state).get("chip")))
    _hv(g, "battle", 1)
    st = _poll(g, lambda s: _ns(s).get("chip") == CHIP_HOST_BATTLE, 1.5, "the 'host in a battle' chip")
    s = g.state
    hf = _ns(s).get("host_flags")
    g.check(st is not None and isinstance(hf, int) and hf & HF_BATTLE and not hf & HF_ON_FIELD and s.dialog_open
            and (_front(s) or {}).get("cls") == "locked",
            "R7: `host battle 1` (b5 set, b3 clear): 'the host is in a battle -- this line continues after it', and the "
            "line stays locked", f"chip={_ns(s).get('chip')!r} host_flags={hf!r} front={_front(s)!r}")
    _hv(g, "battle", 0)
    _poll(g, lambda s: _ns(s).get("chip") == CHIP_FOLLOWING, 1.5, "the chip back to 'following'")
    _host_until_closed(g, g.state.text)


def _rb2g_key_guard(g, lv, c):
    kg0 = _ns(g.state).get("key_gaveup")
    uid = c.keeper_uid                   # a reader with no poll running: its KEY is only ever released, never served
    g.netsync("talk", c.west_uid)
    st = _poll(g, lambda s: s.dialog_open, 6.0, "the scribe's window to exist")
    if st is None:
        raise HarnessError(f"the relayed start for uid {c.west_uid} opened nothing within 6s")
    mark = _mark(g)
    # ONE request: the KEY lands right behind an ADV for a line still opening (held through the typewriter + MinShowMs)
    g.send("netsync host adv", f"netsync host key {uid} {KEY_CONFIRM}")
    pend = _poll(g, lambda s: any(k.get("uid") == uid and k.get("state") == "pending"
                                  for k in (_ns(s).get("keys") or [])), 1.0, "the KEY to wait as 'pending'")
    rel = _poll(g, lambda s: _count(_new(g, mark), f"released for uid {uid} ") >= 1, 5.0, "the KEY to be released")
    g.wait_frames(10)
    fresh = _new(g, mark)
    adv = next((m for m in (_QUEUED.search(ln) for ln in fresh) if m and m.group(5) == "0"), None)
    key = (int(adv.group(3)), int(adv.group(4))) if adv else (None, None)
    i_apply = next((i for i, ln in enumerate(fresh) for m in [_APPLIED.search(ln)]
                    if m and (int(m.group(1)), int(m.group(2))) == key), None)
    i_rel = next((i for i, ln in enumerate(fresh) if f"released for uid {uid} " in ln), None)
    g.check(pend is not None,
            "R-B2g: a KEY sent right behind an ADV for a line still opening waited in keys[] as 'pending'",
            f"keys={_ns(g.state).get('keys')!r}")
    g.check(rel is not None and i_apply is not None and i_rel is not None and i_apply < i_rel
            and _ns(g.state).get("key_gaveup") == kg0,
            "R-B2g: ...and was released only AFTER that ADV applied (log order), with no give-up",
            f"apply line #{i_apply}, release line #{i_rel}; gave up {kg0} -> {_ns(g.state).get('key_gaveup')!r}; "
            f"{_grep(fresh, 'key relay', 'dialogue: win', limit=500)}")


def _rb3_record_replay(g, lv, c):
    # ---- record the scribe: the lock OFF, so this copy plays the host and its real taps go to the tape
    lv.lock(False)
    _poll(g, lambda s: _ns(s).get("lock_engaged") is not True, 3.0, "the lock to disengage")
    st = _ns_verb(g, "tap-record", 1)
    g.check(_ns(st).get("tap_record") is True and _ns(st).get("tape") == 0,
            "R-B3: `tap-record 1` armed a fresh, empty tape (bench on, lock off)",
            f"tap_record={_ns(st).get('tap_record')!r} tape={_ns(st).get('tape')!r}")
    mark = _mark(g)
    st = _open_by_relay(g, c.west_uid)
    rec_pages = list(dict.fromkeys([st.text] + g.advance(max_pages=MAX_PAGES)))
    _control_back(g, "after the recorded scribe")
    _ns_verb(g, "tap-record", 0)
    tape = _ns(g.state).get("tape")
    rec = [ln for ln in _new(g, mark) if "dialog tap RECORDED:" in ln]
    g.check(rec_pages == c.local_pages and len(rec) == len(rec_pages) and tape == len(rec) and bool(rec)
            and " closes " in rec[-1],
            "R-B3: the player's own Confirms on the relayed scribe taped one host tap per page (the REAL "
            "EmitDialogAdvanceIfHost), the last one 'closes'",
            f"pages={len(rec_pages)} recorded={len(rec)} tape={tape!r}; {rec[-1][-120:] if rec else 'none'}")

    # ---- replay it into a LOCKED copy while the guest mashes
    lv.engage()
    st, win, text, first = _relay_scribe(g, c)
    g.check((_front(st) or {}).get("cls") == "locked", "R-B3: the replay's target line opened locked", repr(_wins(st)))
    mark = _mark(g)
    _ns_verb(g, "replay")
    seen, lefts = [first], []
    t0 = time.time()
    while time.time() - t0 < 6.0 + 2.0 * len(c.local_pages):
        g.press("confirm", 2)            # the guest mashes all through the replay (sampled every ~5 frames:
        g.wait_frames(3)                 # a host-paged page shows at least MinShowMs)
        s = g.state
        lefts.append(_ns(s).get("replay_left"))
        if not s.dialog_open:
            break
        if s.text.strip() and s.text != seen[-1]:
            seen.append(s.text)
    _wait_s(g, 0.5)
    fresh = _new(g, mark)
    applied = _applied(fresh, win, text)
    g.check(not g.state.dialog_open and seen == c.local_pages,
            "R-B3: the paced replay walked the SAME transcript on the locked copy while the guest mashed Confirm",
            f"replay={seen!r}\n    local={c.local_pages!r}")
    g.check(len(applied) == len(c.local_pages) and bool(applied) and applied[-1][0] == "closed"
            and _count(fresh, f"dialogue: win {win} text {text} closed by its own script/timer") == 0
            and _count(fresh, f"dialogue orphan: win {win} text {text}") == 0,
            "R-B3: every page turn and the close were the host's (one 'host seq N' apply line each) -- zero input-driven, "
            "self-attributed or orphan closes", f"applied={applied!r}; {_grep(fresh, 'closed', 'orphan')}")
    g.check(_ns(g.state).get("replay_left") == 0 and _count(fresh, "replay: done (") == 1,
            "R-B3: the replay ran to its end (replay_left 0, one 'replay: done' line)",
            f"replay_left samples {lefts[:12]}; {_grep(fresh, 'replay:')}")
    _control_back(g, "after the scribe's replay")

    # ---- record the keeper: a menu pick (CHO) and the polled page's Confirm (a KEY from a control-off poll hit)
    lv.lock(False)
    _poll(g, lambda s: _ns(s).get("lock_engaged") is not True, 3.0, "the lock to disengage")
    _ns_verb(g, "tap-record", 1)
    mark = _mark(g)
    _open_by_relay(g, c.keeper_uid, choice=True)
    g.choose(c.story_idx)
    page = _poll(g, lambda s: s.choice is None and s.dialog_open and _ignores_input(s), 6.0,
                 "the polled story page (recording)")
    left = None
    if page is not None:
        for _ in range(8):
            g.press("confirm", 4)
            left = _poll(g, lambda s: not _ignores_input(s), 0.8, "the polled page to leave (recording)")
            if left is not None:
                break
    _clear(g, c.close_idx)
    _control_back(g, "after the recorded keeper")
    _ns_verb(g, "tap-record", 0)
    fresh = _new(g, mark)
    tape = _ns(g.state).get("tape")
    dlg = [ln for ln in fresh if "dialog tap RECORDED:" in ln]
    kts = [re.search(r"key tap RECORDED: uid (\d+) bits (\d+)", ln) for ln in fresh if "key tap RECORDED:" in ln]
    kuid, kbits = (int(kts[0].group(1)), int(kts[0].group(2))) if kts and kts[0] else (-1, 0)
    g.check(page is not None and left is not None and len(dlg) == 1 and " kind 1 " in dlg[0] and len(kts) == 1
            and kbits & KEY_CONFIRM and tape == 2,
            "R-B3: recording the keeper taped the menu pick as ONE CHO and the polled page's Confirm as ONE KEY "
            "(TapScriptKeyIfHost: a control-off poll hit) -- tape 2",
            f"page={page is not None} left={left is not None} tape={tape!r}; {_grep(fresh, 'RECORDED', limit=500)}")

    # ---- replay it: the CHO closes the locked menu on the recorded row, the KEY drives the page's own poll
    lv.engage()
    st = _open_by_relay(g, c.keeper_uid, choice=True)
    st = _tracked(g)
    mwin, mtext = _key(st)
    mark = _mark(g)
    _ns_verb(g, "replay")
    t0 = time.time()
    while time.time() - t0 < 14.0:       # mash; done once the tape is fed and the polled page came and went
        g.press("confirm", 2)
        g.wait_frames(3)
        s = g.state
        if _ns(s).get("replay_left") == 0 and not s.dialog_open \
                and _count(_new(g, mark), "closed by its own script/timer") >= 1:
            break
    _wait_s(g, 0.5)
    fresh = _new(g, mark)
    menu = _applied(fresh, mwin, mtext)
    # the page by its LOG lines, not by sampling the screen: a KEY that arrived before the page opened is served on
    # the page's first poll, so the page may live only a few frames -- shorter than one sample of this loop
    opened = [(int(m.group(1)), int(m.group(2))) for m in (_OPENED.search(ln) for ln in fresh) if m]
    pkey = next((k for k in opened if k != (mwin, mtext)), None)
    served = [i for i, ln in enumerate(fresh) if _served_to(ln, kuid)]
    own = [i for i, ln in enumerate(fresh)
           if pkey is not None and f"dialogue: win {pkey[0]} text {pkey[1]} closed by its own script/timer" in ln]
    g.check(len(menu) == 1 and menu[0][0] == "closed" and menu[0][2] == c.story_idx,
            f"R-B3: the replayed CHO closed the locked menu on the recorded row ({c.story_idx})", repr(menu))
    g.check(pkey is not None and not g.state.dialog_open and len(served) == 1 and len(own) == 1 and served[0] < own[0],
            f"R-B3: the replayed KEY drove the locked polled page's own poll under the guest's mashing -- 'served to uid "
            f"{kuid}'s poll', then the page 'closed by its own script/timer'",
            f"page={pkey}; {_grep(fresh, 'key relay', 'opened locked', 'closed', 'replay:', limit=600)}")


def _rb6_host_stall(g, lv, c):
    st, win, text, first = _relay_scribe(g, c)
    g.check((_front(st) or {}).get("cls") == "locked", "R-B6: the relayed line opened locked", repr(_wins(st)))
    mark = _mark(g)
    t_before = time.time()
    _hv(g, "freeze")
    t_after = time.time()
    held_late, released = None, None
    while time.time() - t_before < STALL_S + 4.0:
        s = g.state
        el = time.time() - t_before
        if _ns(s).get("lock_engaged") is True and not _ns(s).get("host_stalled"):
            if s.dialog_open and (_front(s) or {}).get("cls") == "locked":
                held_late = el
        else:
            released = time.time()
            break
        g.wait_frames(3)
    g.check(held_late is not None and held_late >= STALL_S - 0.5,
            f"R-B6: a frozen host heartbeat HOLDS the line ({STALL_S - 0.5:.1f}s+ still locked)",
            f"last locked sample {held_late}s after the freeze")
    g.check(released is not None and released - t_before >= STALL_S - EARLY_S
            and released - t_after <= STALL_S + SLACK_S,
            f"R-B6: ...and drops the lock HostStallMs ({STALL_S:.0f}s) after the heartbeat stopped",
            f"released {None if released is None else round(released - t_before, 2)}s after the freeze")
    s = _poll(g, lambda s: _ns(s).get("host_stalled") is True, 1.0, "host_stalled to read true") or g.state
    fresh = _new(g, mark)
    g.check(_ns(s).get("host_stalled") is True and _ns(s).get("lock_engaged") is False
            and _count(fresh, "the host looks HUNG") == 1,
            "R-B6: host_stalled reads true, the lock is off, one 'the host looks HUNG' line",
            f"host_stalled={_ns(s).get('host_stalled')!r} lock_engaged={_ns(s).get('lock_engaged')!r}; "
            f"{_grep(fresh, 'HUNG')}")
    g.check(s.dialog_open and s.text == first, "R-B6: the line itself is untouched by the stall (open, same text)",
            f"open={s.dialog_open} text={s.text[:60]!r}")
    mark = _mark(g)
    _hv(g, "freeze", 0)
    st = _poll(g, lambda s: _ns(s).get("host_stalled") is False and _ns(s).get("lock_engaged") is True, 3.0,
               "the heartbeat to move and the lock to re-arm")
    fresh = _new(g, mark)
    g.check(st is not None and _count(fresh, "heartbeat moved again -- the lock re-arms") == 1,
            "R-B6: `host freeze 0` -- the heartbeat moved, host_stalled cleared and the lock re-armed (one line)",
            _grep(fresh, "heartbeat", "dialogue lock"))
    # [ff9mapkit netsync F3.3] the rise re-tracks every open window as Local (MarkOpenLocal): require one, so an EMPTY
    # tracker -- nothing tracked at all -- cannot pass as "stays local"
    s = _poll(g, lambda s: any(w.get("cls") == "local" for w in _wins(s)), 1.0,
              "the re-armed tracker to list the open line as local") or st or g.state
    g.check(any(w.get("cls") == "local" for w in _wins(s))
            and not any(w.get("cls") in ("locked", "orphaned") for w in _wins(s)) and not _ns(s).get("suppress"),
            "R-B6: ...and the line open across the stall stays LOCAL -- tracked again as `local` (it predates the "
            "re-armed session)", repr(_wins(s)))
    g.check(_paged_by(g, lambda: g.press("confirm", 4)), "R-B6: the guest's own Confirm pages that local line",
            repr(g.state))


def _reset_releases(g, lv):
    """`reset` releases the override AND every lever -- a leaked run must not swallow the next player's Confirm."""
    caps = _caps(g.state)
    c3 = [k for k, have in (("host_frozen", caps.ring), ("host_menu", caps.ring), ("host_battle", caps.ring),
                            ("tap_record", caps.tape)) if have]
    try:
        g.netsync("bench", 1)
        lv.lock(True)
        lv.scene(True)
        if caps.ring:                    # [ff9mapkit netsync F3.3] the bench host's levers (they ride the lock)
            for op in ("menu", "battle", "freeze"):
                _hv(g, op, 1)
        if caps.tape:
            _ns_verb(g, "tap-record", 1)
        lv.stale(True)
        if c3:
            # [ff9mapkit netsync F3.3] the PRECONDITION: each C3 lever reads SET before the reset -- else "released"
            # below would pass on a lever that never landed (False before and after)
            pre = _poll(g, lambda s: all(_ns(s).get(k) is True for k in c3), 2.0, "the C3 levers to read set") or g.state
            g.check(all(_ns(pre).get(k) is True for k in c3),
                    "RESET (C3): the bench host's levers and the tap-record lever read SET before the reset ("
                    + ", ".join(c3) + ")", repr({k: _ns(pre).get(k) for k in c3}))
        g.send("reset")
        st = _poll(g, lambda s: s.netsync is not None and not _ns(s).get("forced"), 5.0,
                   "`reset` to release the forced selftest") or g.state
    except HarnessError as err:
        g.check(False, "RESET: the levers were set and `reset` was sent", str(err)[:300])
        return
    ns = _ns(st)
    g.check(ns.get("enabled") is False and ns.get("bench") is False and ns.get("l1") is False
            and ns.get("lock") is False and ns.get("stale") is False and ns.get("lock_engaged") is False
            and ns.get("suppress") is False,
            "RESET: `reset` released the selftest override, the bench, l1, lock and stale", repr(ns)[:300])
    if c3:                               # [ff9mapkit netsync F3.3] (not run on a pre-C3 engine: the keys do not exist)
        g.check(all(ns.get(k) is False for k in c3),
                "RESET (C3): ...and the bench host's levers and the tap-record lever (" + ", ".join(c3) + ")",
                repr({k: ns.get(k) for k in c3}))
    st = _poll(g, lambda s: s.control, 5.0, "control on after the reset") or g.state
    g.check(st.control, "RESET: the character is not left frozen by a released run", repr(_ns(st))[:200])


def _a12_vanilla(g, lv, c):
    """A12-lite: co-op released in this process (not Enabled=0 from launch -- module note)."""
    g.walk_to(*WEST, tolerance=45, strict=False)
    mark = _mark(g)
    opened = g.interact(timeout=6.0)
    if opened is None or opened.choice is not None:
        g.check(False, "A12: the scribe opened locally with co-op released", repr(opened))
        return
    st = g.state
    g.check(not _ns(st).get("suppress") and not _ns(st).get("lock_engaged"),
            "A12: with co-op released nothing is suppressed or locked (a regression guard: both reads are gated on "
            "`enabled`, which RESET asserted False)", repr(_ns(st))[:200])
    first = opened.text
    paged, why = _click_pages(g, lv)
    s = g.state
    seen = [first] + ([s.text] if s.dialog_open and s.text.strip() and s.text != first else [])
    pages = list(dict.fromkeys(seen + (g.advance(max_pages=MAX_PAGES) if g.state.dialog_open else [])))
    g.check(paged and pages == c.local_pages and not g.state.dialog_open,
            "A12: a click pages the line and click + Confirm walk the reference transcript (stock)",
            f"paged={paged} {why}; {pages!r}")
    fresh = _new(g, mark)
    g.check(_count(fresh, "[NetSync]") == 0, "A12: zero [NetSync] log lines through a stock talk with co-op released",
            _grep(fresh, "[NetSync]"))
    g.shot("authority-A12-vanilla")


def _rb7_vanilla_poll(g, c):
    """[ff9mapkit netsync F3.3] R-B7, co-op released (module note): the polled story page answers the player's OWN
    Confirm through the hoisted B_KEYON / FilterScriptButtons (keys unchanged on vanilla); KeyTick is an inert counter
    that still counts. `key_taps` holding is a plain regression clause: after RESET this copy is no socket host and
    tap-record is off, so TapScriptKeyIfHost returns before tapping whether or not its `!_enabled` gate exists."""
    if _poll(g, lambda s: s.control and not s.dialog_open, 6.0, "control back after A12") is None:
        g.check(False, "R-B7: control came back after A12", repr(g.state))
        return
    ns0 = _ns(g.state)
    kt0, taps0 = ns0.get("key_tick"), ns0.get("key_taps")
    g.walk_to(*EAST, tolerance=45, strict=False)
    mark = _mark(g)
    menu = g.interact(timeout=6.0)
    if menu is None or menu.choice is None:
        g.check(False, "R-B7: the keeper opened its menu locally with co-op released", repr(menu))
        return
    g.choose(c.story_idx)
    page = _poll(g, lambda s: s.choice is None and s.dialog_open and _ignores_input(s), 6.0,
                 "the polled story page (co-op released)")
    left = None
    if page is not None:
        for _ in range(8):
            g.press("confirm", 4)
            left = _poll(g, lambda s: not _ignores_input(s), 0.8, "the polled page to leave on the player's Confirm")
            if left is not None:
                break
    _clear(g, c.close_idx)
    fresh = _new(g, mark)
    g.check(page is not None and left is not None and _count(fresh, "[NetSync]") == 0,
            "R-B7: with co-op released the polled story page closes on the player's own Confirm (the hoisted poll reads "
            "stock keys) -- zero [NetSync] lines", f"page={page is not None} left={left is not None}; "
            f"{_grep(fresh, '[NetSync]')}")
    ns = _ns(g.state)
    kt, taps = ns.get("key_tick"), ns.get("key_taps")
    g.check(isinstance(kt0, int) and isinstance(kt, int) and kt > kt0 and taps == taps0,
            "R-B7: `key_tick` still counts on vanilla (the inert EventEngine counter) and `key_taps` did not move (a "
            "regression clause)", f"key_tick {kt0!r} -> {kt!r}; key_taps {taps0!r} -> {taps!r}")
