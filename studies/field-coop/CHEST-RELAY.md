# The chest relay: a guest sees the host open a stock chest (engine s160)

**Status: DESIGNED, REVIEWED and DRAFTED (rev 2, compile-checked on a private clone copy), 2026-10-28. Not built.**
The owner set the order on 2026-10-28:
1. s159, the step-out anchor and bench fixes;
2. this round, as s160;
3. the ATE menu and title, as s161, which rebases onto s160.

The order is logged in `netsync-round-queue.md` in the top session's notes. s160 is built only after s159 is captured and
released there.

## The defect

From the owner's 2026-10-28 two-PC session: "no item dialogue box or chest animations when opening a chest (tested on
301)". The same session reproduced it on 352 (text 52). The cause was traced and skeptic-checked in
`GUEST-TRAVERSAL-TWO-PC.md` ("For later patches", first bullet).

- A stock chest opens in its tag-2 `_Range` body.
- The engine requests that body at level 1 at the end of every event pass while the player stands in push range
  (`EventCollision.CollisionRequest`: `Request(obj, 1, 2)` after `CheckNPCPush`).
- The body draws the "!" bubble and polls `IsButton(Confirm|Special)` with control on (`test2_57.txt` ChestA_Range for
  field 200).
- That press never reaches `EmitTalkStartIfHost`, because only `CheckNPCInput` and `CheckQuadInput` call it. It never
  reaches the key relay either, because `TapScriptKeyIfHost` relays control-off reads only.
- So the guest's copy never runs the open, and the host's window (win 7, "Received Item!") ages out on the guest after
  20 s. This is F3.2's designed-in gap B (`F3.2-DESIGN.md`), not a regression.

## Owner decisions (2026-10-28)

1. **Chests only.** Pickups, signs, menus and button gateways stay host-only, as today.
2. **The guest kneels like stock.** On the guest's copy, the chest's own script turns the guest's character toward the
   chest and kneels it, holding it still until the window closes, wherever it stands. A relayed NPC talk already turns
   and holds the guest the same way. No extra engine code.
3. **Numbering:** chest relay = s160, ATE = s161.

## The census (`chest-census/census.py`)

The census reads the first language block of every export and keys entries by `#HW newentry` index. It does not key by
name: HW names an entry after its model, so three model-75 chests in one field are all `ChestA`. The first cut keyed by
name and undercounted to 186 / 140 / 9; the pre-build review caught it.

| Stock tag-2 Confirm/Special polls | 253 | facing-gated |
|---|---|---|
| chest | **207** (in 129 field scripts) | 0 |
| indirect (a player function, a barrel) | 23 | 9 |
| button gateway (`Field`) | 11 | 9 |
| menu / choice (the Lindblum air cab) | 10 | 10 |
| sign / text | 2 | 0 |

- **The chest models are an exact discriminator.** 224 entries use models 75, 91, 701 or 702, and every one is a chest.
  Of those, 207 poll in tag 2 (model 75: 158, 91: 38, 702: 6, 701: 5).
- **206 of the 207 bodies share one shape:** `ifnot(IsMovementEnabled) return; if ((!OPENED) && VAR_LocUInt8_0) {
  Bubble(1); if (IsButton(655360)) {...` followed by an item, gil or card grant and `WindowSync(7, …)`.
  - No chest checks facing, and no chest entry has a tag 3.
  - The exception is 704:13 (the Gizamaluke bell chest): no latch, and a `GetItemCount(268) == 0` branch.
- **Out of scope, 17 chest entries that never poll:**
  - 13 have Init/Loop only.
  - 4 Burmecia chests (754/755/761/762) open on touch, with no button.
  - 1254:18 is opened through a region's choice, so only the quad path can carry it.
- **Latch classes of the 207:**
  - **191 latch-free.** 190 have the template latch functions but nothing calls them; 704:13 has no latch.
  - **9 story-driven.** Scene brackets: 352:15, 802:18, 1707:4/5. Story-state gates: 450:20, 1606:26/27, 1608:7, 2214:7.
  - **3 traversal or positional:**
    - 301:15 (the ice jumps);
    - 951:8 (each copy's own camera zone);
    - 2513:7 (the carry; it fails open on the guest).
  - **4 other:**
    - 302:16 and 303:19 (Vivi melts them);
    - 407:12 ("Kick it");
    - 1254:18 (permanently latched).
  - Wherever the guest's latch differs from the host's, the guest's body returns before `IsButton`, and the relay degrades
    to today's behaviour with a "not served" line.

## Design (rev 2, after the pre-build review)

### Host: stamp at the chest's own read

At `TapScriptKeyIfHost`'s control-on branch, the s158 site where the script consumes the press, `ArmChestStart` stamps a
**chest start** at once when all of these hold:
- host role with a socket, field mode;
- a press edge: `keys & readMask & ChestPressBits(jp)` is non-zero.
  - `ChestPressBits(jp)` is `Special | (jp ? Cancel : Confirm)`.
  - The JP scripts poll Cancel|Special (589824), and `ETb.ProcessJapaneseLayout` swaps the physical Confirm into Cancel
    for them.
  - A held (`B_KEY`) read counts on its press tick only.
- the reader (EBin's `gExec`) is a `PosObj` with a stock chest model;
- the reader's current function is its tag 2: `TagAtIp(reader.ebData, reader.ip)` takes the largest `2 + offset` that is
  at most `ip` in the entry's function table, the same table `GetIP` reads, never assumed sorted.

Repeat reads by the same chest in one key tick are the same press. This matters because `IsButton(A) || IsButton(B)` reads
twice: `||` does not short-circuit.

**Why stamp at the press, not at the window.** Rev 1 promoted the start like a quad, when the window rose. The review
showed three problems with that (upheld 3/3):
- The guest's copy then started a whole turn, kneel and lid open behind the host. Its "Received Item!" box opened with the
  host's close already waiting, flashed, and its character stayed knelt about 1.3–1.9 s after the host was free.
- R8 refreshed the guest's bag wraps from a frame built after the host's `AddItem`. A host at 98 of an item then sent the
  guest into "Cannot carry another Item", and 704:13 granted the wrong item.
- The window gate adds no safety for a chest. Every stock chest body is committed to its window from the `IsButton` that
  arms it (the census).

Stamping goes through `StampTalk(uid, fld, chest: true, bits)`, which gives:
- one shared nonce and the out-of-band push;
- `StartSceneAt`, whose `_hostSceneTalk` makes the scene an interaction, so s158's option C keeps the guest visible;
- the existing supersede rules: an armed quad start drops ("superseded by a chest"), and a later NPC talk replaces the
  start on the lane.

The quad promotion code is untouched, byte for byte.

**Residual.** A chest body whose `VAR_GlobBool_159` is not 1 skips `DisableMove`, and its host scene then falls while the
window is still open. Every relayed NPC talk shares this. Whether stock free roam ever clears 159 is not checked yet.

### Wire: a new section is the version gate, and the kind rides the section

`SectionChest = 9`: `[field u16 LE][uid u16 LE][nonce u8][bits u16 LE]`, at least 7 bytes. The bits are
`NetSyncField.CompactKeys` of the PHYSICAL press: the host's JP swap is undone by `NetSyncField.LayoutSwap`, its own
inverse, and the guest swaps into its own layout.

The ids taken are:
- 0–7: story, party, intent, event, talk, dialogue;
- 8: the dress;
- 9: the chest, claimed here.

The ATE relay (s161) rides section-7 ring kind 3, not a section.

While a chest start rides, `SectionTalk` does not: the lane carries one start at a time.
- **An older guest never reads section 9**, so it cannot replay a chest start as a tag-3 `Request`. Many regions carry
  both a tag-3 `SpeakBTN` and a tag-2 `_Range` (301's ice jumps). The older guest sees no start, which is today's
  behaviour. An older host sends none.
- **The kind is read off the section, never the body length.** Rev 1 used a length law (a talk is 5 bytes, a chest 7).
  The review showed that breaks section 6's forward rule: a later host could lengthen section 6, and an s160 guest would
  decline every NPC talk as "not a stock chest". `ReadStartLane(state, out chest)` now reports which section the start
  came from.
- **The s156 climb hold keeps only the body**, so ServiceTalkFollow records the held start's nonce and kind
  (`_heldStartNonce` / `_heldStartChest`) when it hands a start to the hold.

### Guest: accept, request (or not), serve once

`ServiceTalkFollow` reads the start lane through `ReadStartLane`. So do `NoteTalkScene` and `GuestHostSceneWhy`'s lane;
`GuestView.TalkLiveHere` reads both sections itself. A chest start therefore:
- defers, holds over a climb (D8b), purges at accept (`PurgeAtRelayAccept`) and refreshes the bag wraps (R8) exactly as a
  talk start does;
- marks the step-out's relay accept (`NoteRelayAccept`), so the guest does not step out.

`ApplyChestStart`, the tag-2 twin of `ApplyTalkStart`:
- **Decline** (nonce consumed, one line) when:
  - there is no object with that uid;
  - it is not a stock chest model, or it has no tag 2;
  - the start carries no Confirm/Special;
  - live, **my story is not mirroring the host's**. The opened flag and the item would land in my own save, because the
    exit ramp arms only while mirroring (GuestPress's `storyOk`; review, upheld 2/2).
- **Defer**, as a talk does, when:
  - there is no controlled actor yet;
  - my control is off;
  - my own climb is in flight;
  - the chest is busy in another handler.
- **Apply.** Arm a one-shot serve: `(field, uid, bits in my script layout, armed tick)`.
  - **I stand in push range:** the stock range request has already queued the body between passes (level 1, ip at its
    tag-2 entry, not yet run). That queued body takes the serve on the next pass, and I request nothing. Rev 1 deferred
    here forever (upheld 3/3, by three lenses).
  - **Otherwise:** `Request(obj, 1, 2)`. The body runs on my copy wherever I stand.

The serve sits in `NetSyncField.FilterScriptButtons`, at the top of the spectator's control-on branch, field mode only:
- The first read by that reader on that field whose mask meets the bits takes them.
- Every read by the reader in that key tick sees the same press (the `TakeRelayedScriptKey` rule). The next tick spends it.
- My own Confirm/Special/Select stay masked exactly as before.
- One-shot is enough for a chest: its `IsButton` read happens only after its own gates (`IsMovementEnabled`, the opened
  flag, the latch) pass. An unpassed gate means no read, and the serve expires unspent. s161's ATE serve differs: it
  re-serves every key tick, because the ATE gate can be false at the first read. The two compose without touching each
  other.

**An unserved serve expires** after `ChestServeMs` (2000 ms), on a field change, or at a session reset, with one line:
"chest start uid N not served (...)". That covers the latch classes above, 301 first.

### What the guest's copy then does

- The chest body runs stock:
  1. `DisableMove`.
  2. The turn and kneel: the player's function, whose number varies by field (19/20 on 200, 21/22 on 301, 29/30 on 352).
  3. The lid clip (7336 on models 75/701, 22 on 91/702).
  4. `Wait(2)`, `AddItem`, then `WindowSync(7, 0, <Received Item!>)`.
- Stamped at the press, the guest's copy runs one network delay behind the host's. Both windows are open together, and the
  host's `ADV` closes both: the lock holds the guest's from its first frame.
- `GetItemCount` answers from the host's bag as it was at the press (R8's wraps, refreshed from the frame that carried
  the start). So the "Cannot carry another Item" branch and 704:13's branch match the host's.
- **The item grant stays session-scoped.** This holds only while mirroring, hence the decline above.
  - `AddItem` lands in the guest's live bag. The Continue slot is frozen for the session (the pairing autosave), and the
    exit ramp reloads it.
  - The opened flag is the guest's own until the next field load re-mirrors the host's, which has it set too.
- The press-to-window latency of a stock Zidane chest is about 37–48 event ticks (1.3–1.9 s at ~30 ticks/s): turn 0–10,
  kneel 25, lid 10, `Wait(2)`. The worst case found is 2.1 s (a 34-frame kneel).

### Harness

- **`netsync chest <uid> [confirm|special]`** (selftest role, the role refused first, then the field-gate bench).
  Fabricates a section-9 frame through the real codec and hands it to the same accept path, with the talk bench's TTL
  parity.
- **The calibration levers.** They are set as-is, act on the selftest role only (the leaked-lever law), and are released
  with the harness.
  - `netsync chest serve on|off`: off means the body runs and the read stays masked.
  - `netsync chest request on|off`: off means no forced `Request`, so only a body the stock range request queued is
    served.
- **The key `netsync.chest`** is netsync's LAST key, after `stepout`. It is built by `HarnessAgent.AppendChest` with the
  agent's own Str/Num/Bool/Try helpers. It carries:
  - the levers;
  - the serve (armed, active, uid, `script_bits`, age);
  - the guest's counters (accepted / served / expired / declined), `last_uid` and `why`;
  - `selftest`;
  - `host` (stamped, riding).
- **The proof block's LAST line:** "chest relay selftest: OK (N rows, M mutants caught)", currently 37 rows and 6 mutants.
  - The rows cover the models, the tag map on an unsorted table, the JP swap across mixed-language pairs, the serve rule,
    and the kind by section (a lengthened section 6 stays a talk).
  - Each mutant must fail a row: a sorted-table tag map, no swap, any reader served, a serve never spent, every 70x model
    a chest, and the kind by length. An escaped mutant is named.
- **`NetSyncState.SelfTest`** gains section-9 rows in production order: a section after 9 reads back exactly, and a frame
  with section 9 BEFORE the story applies the whole story.
- **The kit rung (not yet written; it waits for s159's to merge):**
  - `tools/harness/session.py`: `chest` in `NETSYNC_SUBVERBS`, a `NETSYNC_CHEST_SUBVERBS` row, and a `chest()` helper.
  - `tools/harness/channel.py`: a `coop_chest` capability accessor and the block.
  - `tools/harness/fakegame.py`: the s160 rung after s159's `stepanchor`, the catch sentinels, the refusals in the
    engine's words, and the release.
  - Pins in `ff9mapkit/tests/test_harness_netsync.py`.

## Bench plan (solo first)

**Single game, the guest half** (`coop_chest_relay.py`, the selftest role, `--instance C:\gd\ff9-inst\host`; the shared
install is live-configured).

Field 200 (Prima Vista/Hallway, `test2_57.txt`), ChestA entry 9 = uid 9:
- model 75 at (576, 80), collRad 40, push radius 346 (`objects[].range_r`), walking stop r 256;
- opened flag `VARL_GenBool_7244`, item 112 (Leather Hat), text 70 ("Received Item!") or 74 ("Cannot carry");
- player functions 19 (turn + kneel 2606/2605) and 20 (stand 2590/200).

Arrival:
1. `newgame`, `noencounter`.
2. Zero bytes 13 and 14 (the env-slot law). Set flag 2471 = 1 (no Nero walking through) and flag 7244 = 0, then
   `watch 7244 2471`.
3. `warp 200 entrance=0 scenario=2000`. The player spawns at (-90, 171), face 0.
4. Preflight `objects[]`: uid 9 is the chest, and uids 4/6/17 are absent.
5. `netsync selftest 1`, `netsync bench 1`, optionally `netsync lock 1`. `netsync.windows` is empty without the lock.
6. Stay undressed. Keep `|SelfTestOffset| < 640`.

The spots:
- **FAR** = the spawn (distance 672). The expected face after the turn is about 198.
- **NEAR** = (290, 80), distance 286, reached with `walk_to(290, 80, tolerance=20)`. Its walkability is judged from the
  published distance.

Each row is judged on an outcome, never on "the input was received":

| Row | Check | Predicted on `serve off` | on `request off` |
|---|---|---|---|
| C1 | FAR: `netsync chest 9` -> accepted, then served; control off; face turns to about 198; position held; flag 7244 set; a window opens naming the Leather Hat (with the lock: `netsync.windows` holds win 7 text 70) | RED | RED |
| C2 | NEAR (256 < d < 346, face turned away first): the same outcomes, with the "already queued" accept line | RED | green |
| C3 | after the window closes: stand clip, control back, face held | RED | RED far / green near |
| C4 | NEAR, no start, my own Confirm: no window, 7244 stays clear, control stays on | green | green |
| C5 | `chest 10` (Zidane, model 98) and `chest 99`: one decline line each, nothing opens | green | green |
| C6 | a start on the opened chest: accepted, then "not served" after 2 s, nothing opens | green | green |
| C7 | FAR with my control off: one "deferred" line; control back inside 4 s -> the C1 outcomes | RED | RED |

- The accept-to-first-window time in C1 measures the press-to-window path. Log it.
- Each lever's calibration must go red on exactly its predicted rows.
- "The same nonce twice applies once" cannot be driven solo, because the verb mints a fresh nonce. It moves to the duo.

**Duo, the wire half** (`coop_chest_relay_duo.py`: two games on one machine, field 200 or 352). Every row is a log line or
published state:
- the host's real Confirm at the chest stamps one chest start at the press (`netsync.chest.host.stamped` +1, "chest
  relay: host opened chest 9");
- the guest accepts within about 1 RTT, and its window 7 opens while the host's is still open;
- the host's Confirm closes both;
- the same nonce is applied once;
- the host's ghost of the guest stays visible (option C), and the guest does not step out;
- the guest's autosave bytes are unchanged.
- **The version gate:** a third leg with the guest root on the s159 DLL. No window opens there, there is no tag-3
  `Request` line, and the guest is neither moved nor frozen.

**Two-PC (the owner):** field 352, Dali Inn, **ChestA entry 16**:
- (875, -279), flag `VARL_GenBool_7278`, an Antidote, text 52;
- latch-free on every load, and created on every load.

Entry 15 (flag 7279) loses its latch only inside the wake scene. Both chests are closed in the owner's 301 save
(scenario 2500), and 352 is free roam from scenario 2600. Check flags 7278/7279 in any later save.

The steps:
1. First undressed, then dressed.
2. Skip the ATE prompt first: the guest sees ATE menus only from s161.
3. Then 301, expected to stay as today (the latch), with the not-served line in the guest log.

Alternatives, all latch-free and created unconditionally:
- 302:15 (Potion), one field on from the 301 save;
- 304:16/17 and 303:17/18;
- 357:12/13 (Dali windmill; the guest must climb 356's ladder on its own copy).

## The pre-build review (2026-10-28)

A six-lens adversarial review (host, guest, wire, script, timing, harness) read the rev-1 draft. Each finding went to three
refute-by-default skeptics, then a completeness critic and its own two skeptics; 88 agents in all. 26 findings survived
and one was refuted.

**Fixed in rev 2:**
- stamping at the press;
- the in-range deadlock;
- the mirror gate;
- the kind by section, with the held-kind record;
- the post-grant bag;
- the role-checked levers;
- the proof line's format and published verdict, with named mutants;
- consistent bits wording (`press` compact on the wire, `script bits` on the guest);
- `last_uid` moving on declines and expiries;
- role-first parsing;
- the lever-aware expiry text;
- the block built with the agent's helpers;
- the codec rows made able to fail;
- the census;
- the stale comments and tags.

**Carried as follow-ups:** below.

## Order and coordination

1. s159 builds first. s160 rev 2 is a diff against the s158 clone (private copy, compile-clean). When s159 is released in
   the queue:
   1. Log `TAKING THE CLONE: s160`.
   2. Three-way merge the draft onto the s159 files.
   3. Write the kit rung.
   4. Build through `tools/build_memoria.py`, which backs up and verifies.
   5. Bench.
   6. Capture `memoria-patches/s160-netsync-chest-relay.patch` with its README row.
   7. Log `RELEASED: s160 <sha16> <revert set>`.
2. The files touched:
   - `NetSyncClient.cs`: the stamp, the lane, the accept, the serve, the proof, the harness reads;
   - `NetSyncField.cs`: the serve call and `LayoutSwap`;
   - `NetSyncState.cs`: the id and the codec rows;
   - `NetSyncBattle.cs`: the release;
   - `HarnessAgent.cs`: the sub-verb and `AppendChest`;
   - the kit rung.
3. s161 (ATE) rebases onto s160. They share these call sites:
   - `TapScriptKeyIfHost`'s control-on branch;
   - `FilterScriptButtons`' control-on branch (s160 returns early at the top, s161 ORs at the end);
   - the LAST netsync key (`chest`, then `ate`);
   - the proof block's last line;
   - `HarnessReleaseBench`.

## Follow-ups (not this round)

- **The talk relay has the same mirror gap.** `ApplyTalkStart` never checks `IsMirroringStory`, so an unmirrored
  co-located guest runs a relayed talk against its own save. Gate both relays in `ServiceTalkFollow`'s live accept.
- **A host battle in the guest's chest or talk tail boots the guest's diorama COLD.** Control is off or a dialog is
  visible, and no line attributes the cold boot to the chest. s156's `NoteBoot` attributes a climb's. Stamping at the
  press shrinks the tail to one network delay.
- **The latched chests** (301, 951, 302/303, 407, 2513): carrying a chest's latch belongs with the LOCO+LATCH traversal
  rung and with relaying the scenes that set it.
- **JP host, non-chest spots:** s158's `NoteHostInteraction` tests Confirm|Special only. So a JP-language host's pickup,
  sign or gateway press (Cancel) is not marked an interaction, and option C may hide the guest there. Chests are covered
  by the stamp.
- **Mixed-language pairs and the control-off KEY relay:** a KEY carries script-space bits, so a host and guest on
  different languages swap Confirm and Cancel. The chest relay is layout-neutral; the KEY relay is not.
- **Out of reach:** the 4 Burmecia touch chests and 1254's region-opened chest.
