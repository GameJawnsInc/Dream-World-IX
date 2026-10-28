# The chest relay: a guest sees the host open a stock chest (engine s160)

**Status: DESIGNED 2026-10-28, drafted and compile-checked, not built.** The owner set the order on 2026-10-28:
s159 (the step-out anchor and bench fixes), then this round as s160, then the ATE menu and title as s161, which
rebases onto it (`netsync-round-queue.md` in the top session's notes).

## The defect

From the owner's 2026-10-28 two-PC session: "no item dialogue box or chest animations when opening a chest
(tested on 301)". The same session reproduced it on 352 (text 52). The cause was traced and skeptic-checked:
`GUEST-TRAVERSAL-TWO-PC.md`, "For later patches", first bullet.

- A stock chest opens in its tag-2 `_Range` body. The engine requests that body at level 1 every frame the
  player stands in push range (`EventCollision.CollisionRequest`: `Request(obj, 1, 2)` after `CheckNPCPush`).
  The body draws the "!" bubble and polls `IsButton(Confirm|Special)` with control on
  (`test2_81.txt` ChestA_Range; `test2_57.txt` for field 200).
- That press never reaches `EmitTalkStartIfHost` (only `CheckNPCInput`/`CheckQuadInput` do) or the key relay
  (`TapScriptKeyIfHost` relays control-off reads only). So the guest's copy never runs the open. The host's
  window (win 7, "Received Item!") sits unmatched on the guest and ages out after 20 s.
- This is F3.2's designed-in gap B (`F3.2-DESIGN.md`, "B. The host's window never opens on the guest"), not a
  regression.

## Owner decisions (2026-10-28)

1. **Chests only.** Pickups, signs, menus and button gateways stay host-only, as today.
2. **The guest kneels like stock.** On the guest's copy the chest's own script turns the guest's character
   toward the chest and kneels it, holding it still until the window closes, wherever it stands. This is the
   same way a relayed NPC talk already turns and holds the guest. No extra engine code.

## The census (`chest-census/census.py`)

186 stock tag-2 bodies (unique field-script x entry) poll Confirm or Special with control on.

| Kind | Bodies | Facing-gated |
|---|---|---|
| chest | 140 | 0 |
| indirect (a player function, a barrel) | 23 | 9 |
| button gateway (`Field`) | 11 | 9 |
| menu / choice (the Lindblum air cab) | 10 | 10 |
| sign / text | 2 | 0 |

- **The chest models are an exact discriminator.** Models 75, 91, 701 and 702 are used by chest entries only,
  and every chest entry uses one of them. 140 of those entries poll in tag 2.
- **Out of scope:** nine chest entries that have only Init and Loop (no tag-2 poll), and the 46 non-chest
  spots (owner decision 1).

## Design

### Host: arm on the chest's own read

At `TapScriptKeyIfHost`'s control-on branch, the s158 site where the script consumes the press, the host arms a
**chest start** when all of these hold:
- host role with a socket, field mode;
- a press edge: `keys & readMask & ConfirmBits` is non-zero, where `ConfirmBits = Special | (jp ? Cancel : Confirm)`.
  The JP scripts poll Cancel|Special (589824), and `ETb.ProcessJapaneseLayout` swaps the physical Confirm into
  Cancel for them. A held (`B_KEY`) read arms on its press tick only.
- the reader is a `PosObj` whose `model` is a stock chest model (75, 91, 701, 702);
- the reader's current function is its tag 2. This is mapped from `reader.ip` to the entry's function table:
  the largest `2 + offset` that is at most `ip`, the same table `GetIP` reads.

Repeated reads by the same reader in the same key tick fold into one arm. The s158 `NoteHostInteraction` line
above it stays byte-for-byte.

### Host: promote when the window rises

The chest start shares the quad promotion's single slot (`_quadArmed`) with a kind (3 = quad talk, 2 = chest)
and the press bits. So a quad press, an NPC talk or a chest press supersedes the others exactly as today.
`ServiceQuadPromotion` keeps every rule:
- left the field: drop;
- no fresh window inside the deadline: drop;
- the player moved more than `QuadMovedDist` with control off: drop;
- control taken and handed back with no window: drop;
- a lockable window rose that was not open at the press: promote.

Chests add two things:
- **The reader must still be running a requested handler at promotion** (`obj.level <= 1`). A chest's body sits
  in `WindowSync` when its window rises, so this ties the window to the chest's own handler.
- **The deadline is its own constant, `ChestPromoteMs`.** A stock chest's window comes after a turn, a kneel,
  the lid clip and `Wait(2)`, which can approach the quad's 3000 ms. The seed is 6000 ms; the bench measures the
  press-to-window latency on 200 and 352 and sets it. The other rules keep a long deadline safe.

The promotion goes through `StampTalk`. That gives one shared nonce, the out-of-band push, and `StartSceneAt`,
whose `_hostSceneTalk` makes the scene an interaction. So s158's option C keeps the guest visible however long
the chest takes, and the 2 s interaction mark stops mattering for chests.

### Wire: a new section is the version gate

`SectionChest = 9`: `[field u16 LE][uid u16 LE][nonce u8][bits u16 LE]`, 7 bytes. The ids taken are 0-7 (story,
party, intent, event, talk, dialogue) and 8 (dress). While a chest start rides, `SectionTalk` does not: the lane
carries one start at a time, as today.
- **An older guest never reads section 9**, so it cannot replay a chest start as a tag-3 `Request`. Many
  regions carry both a tag-3 `SpeakBTN` and a tag-2 `_Range` (301's ice jumps), so a tag-3 replay could move it.
  It sees no start, which is today's behaviour. An older host sends none.
- **The bits are layout-neutral on the wire.** The host un-swaps its JP layout before it encodes and the guest
  swaps into its own, so a Japanese-language guest's chest (polling Cancel|Special) is served by an English
  host's Confirm. Compact form: `NetSyncField.CompactKeys`.

### Guest: accept, request, serve once

`ServiceTalkFollow` reads the start lane as `SectionTalk`, else `SectionChest`, through one helper. The other
three readers of the talk lane use the same helper: the s156 traversal host-scene term,
`GuestView.TalkLiveHere`, and `NoteTalkScene`. So a chest start defers, holds over a climb (D8b), purges at
accept, refreshes the bag wraps (R8), and marks the step-out's relay accept exactly as a talk start does.
A chest body is told from a talk body by its length (7 against 5). That rule is pinned in the codec selftest.

`ApplyChestStart` (the tag-2 twin of `ApplyTalkStart`):
- **decline** (nonce consumed, one line): no object with that uid, it is not a chest model, or it has no tag-2
  function;
- **defer** (as `ApplyTalkStart`): no controlled actor yet, my control is off (the body's
  `ifnot(IsMovementEnabled) return` would bail), my own climb is in flight, or the object is running at
  level 1 or below;
- **apply:** arm a one-shot serve `(field, uid, bits swapped into my layout, armed tick)`, then
  `Request(obj, 1, 2)`. The body runs on my copy wherever I stand, because the stock request needs push range
  and mine does not. If I do stand in range, the stock request finds the object busy and does nothing.

The serve sits in `NetSyncField.FilterScriptButtons`, at the top of the spectator's control-on branch, field mode
only. The first read by that reader on that field whose mask meets the bits takes them, and every read by the
reader in that key tick sees the same press (the `TakeRelayedScriptKey` rule). The next tick spends it. My own
Confirm/Special/Select stay masked exactly as before.

**An unserved serve expires** after `ChestServeMs` (2000 ms), on a field change, or at a session reset, with one
line: `chest start uid N not served (my copy's handler never polled it)`. That is the 301 case: its latch
`VAR_LocUInt8_0` is set by the ice-jump regions the guest's copy never took (the LOCO+LATCH rungs), so the
body returns before `IsButton`. It degrades to today's behaviour with a log line.

### What the guest's copy then does

- The chest body runs stock: `DisableMove`, the turn and kneel (the player's function 19/21), the lid clip
  (7336), `AddItem`, then `WindowSync(7, 0, <Received Item!>)`.
- Its window is locked from its first frame, and the host's retained `ADV` closes it (TALK-7). That is the
  catch-up a late-opening relayed talk already gets.
- `GetItemCount` answers from the host's bag (R8's wraps, refreshed from the frame that carried the start). So
  the "Cannot carry another Item" branch matches the host's.
- **The item grant stays session-scoped.** `AddItem` lands in the guest's live bag. The Continue slot is frozen
  for the session (the pairing autosave), and the exit ramp reloads it. The opened flag (`VARL_GenBool_*`) is
  the guest's own until the next field load re-mirrors the host's, which has it set too. The duo bench checks
  that the guest's autosave bytes do not change across a relayed chest.

### Harness

- `netsync chest <uid> [confirm|special]` (selftest role, the bench gates on): fabricates a section-9 frame
  through the real codec and hands it to the same accept path, with the talk bench's TTL parity.
- **Levers:**
  - `netsync chest serve on|off`: off = the serve never answers, so the body runs and the read stays masked.
  - `netsync chest request on|off`: off = no forced `Request`, so only a body the stock range request runs is
    served.
- **Keys:** `netsync.chest` (LAST, after s158's `stepout`, or after whatever s159 adds): lever states, last uid, armed, served, expired,
  declined, and the host's armed / promoted / dropped counts.
- **An unknown sub-verb throws on an older engine.** A driver probes `netsync.chest` before sending, so a
  pre-s160 engine can never misparse it.

## Bench plan (solo first)

**Single game, the guest half** (`coop_chest_relay.py`, the selftest role, `--instance C:\gd\ff9-inst\host`
because the shared install is live-configured). Field 200, ChestA (entry 9), opened flag `VARL_GenBool_7244`
cleared before entry.

| Row | Check (an outcome, never "the input was received") | Predicted on `serve off` | on `request off` |
|---|---|---|---|
| C1 | far (outside push range): `netsync chest 9` -> the lid clip plays, window 7 text 70 opens, item 112 +1, flag 7244 set | RED | RED |
| C2 | near (in push range): the same | RED | green |
| C3 | the player turned toward the chest and returned to control after the window closed | RED | RED far / green near |
| C4 | my own Confirm beside a closed chest (no start) opens nothing (F1's mask holds) | green | green |
| C5 | a start for a non-chest uid is declined with one line, nothing opens | green | green |
| C6 | a start on an opened chest is not served and expires with one line | green | green |
| C7 | a start while my control is off defers one line, then applies inside the TTL | RED | RED |
| C8 | the same nonce twice applies once | green | green |

Each lever's calibration must go red on exactly its predicted rows.

**Duo, the wire half** (`coop_chest_relay_duo.py`, two games on one machine, field 200 or 352). Every row is a
log line or published state:
- the host's real Confirm at the chest arms one chest start and promotes it at its window;
- the guest's window 7 opens, and the host's Confirm closes both;
- the host's ghost of the guest stays visible (option C), and the guest does not step out;
- the guest's autosave bytes are unchanged.
- **The version gate:** a third leg with the guest root on the s159 DLL. No window opens there, there is no
  tag-3 `Request` line, and the guest is neither moved nor frozen.

**Two-PC (the owner):** 352's chest from the Dali save, outside the night scene, first undressed, then dressed.
Then 301, expected to stay as today (the latch) with the not-served line in the guest log.

## Order and coordination

1. s159 builds first. s160 is drafted against the s158 clone in a private copy (compile-clean, 2026-10-28) and replayed
   onto the shared clone only after s159 is captured and released in the queue. Its files: `NetSyncClient.cs` (the arm, the promotion kind, the section,
   the accept, the serve state), `NetSyncField.cs` (the serve call), `NetSyncState.cs` (the id and the codec
   pin), and `HarnessAgent.cs` (the sub-verb and the key).
2. s161 (the ATE round) serves a control-on Select to the ATE reader in the same `FilterScriptButtons` branch. It
   rebases onto s160, so it can reuse s160's one-shot serve instead of adding a second one.
3. Bench solo, then ask the owner for the two-PC check.

## Follow-ups (not this round)

- **301's latch:** the chest's `VAR_LocUInt8_0` follows the ice jumps the guest's copy never runs. Carrying it
  belongs with the LOCO+LATCH traversal rung.
- **JP host, non-chest spots:** s158's `NoteHostInteraction` tests Confirm|Special only. So a JP-language host's
  pickup, sign or gateway press (Cancel) is not marked an interaction, and option C may hide the guest there.
  Chests are covered by the promotion.
- **Mixed-language pairs and the control-off KEY relay:** a KEY carries script-space bits, so a host and guest
  on different languages swap Confirm and Cancel. The chest relay is layout-neutral; the KEY relay is not.
