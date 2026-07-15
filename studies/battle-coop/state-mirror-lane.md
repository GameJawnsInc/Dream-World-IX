# The state-mirror lane — build spec (host→guest authoritative state sync)

> **Status: IMPLEMENTED — written + adversarially reviewed 2026-07-13; NOT yet compiled/built** (awaits the
> DANGEROUS rebuild + the selftest codec proof). The grounded feasibility is in
> [`README.md`](README.md) § "THE AUTHORITATIVE-HOST ROADMAP"; the source cites here are from probe
> `wf_f019fe71`. This is the ONE new subsystem the authoritative-host paradigm ("play the standard game
> together") is built on. It is an **engine change** (s37 patch + a wire-version bump v5→v6) — see § Build
> discipline. The code review (`wf_da6dc78f`) found it compile-clean + logic-sound; both findings are FIXED:
> the apply gate now excludes `_role == "host"`, and the spectator-save is COMPLETE — a following guest's
> save is blocked (`SaveLoadUI` refuses when `NetSyncClient.IsMirroringStory`, inert in normal play) so it
> can never persist the host's story over the guest's own file. Every `file:line` is a real location in
> `C:\gd\FFIX\Memoria\Assembly-CSharp\`; re-confirm before editing (cites drift ±a few lines).

---

## 1. Goal & scope

Make the guest's locally-booted field render the **host's** story state instead of the guest's own, so a
following guest sees the same NPCs / doors / branches / story-appropriate scenes as the host. The mechanism
is a one-way **host→guest** broadcast of the host's `gEventGlobal` (the 2048-byte story-flag heap), applied
to the guest's identical array at the field-load boundary.

**In scope (rung 1):** `gEventGlobal` mirror + the mandatory spectator-save wrapper + a selftest loopback
proof. **Designed-for but deferred:** a `party` payload section (rung 2, the diorama's input) and a
`gScriptVector`/`gScriptDictionary` section (long-tail fidelity). **Explicitly NOT in scope:** cutscene
lockstep (interactive beats read local state — the honest ceiling, a separate subsystem).

**Why this first:** it is the substrate the diorama also needs (party rides the same lane), it delivers the
paradigm's headline value alone (guest stops rendering scenario-zero), and it closes the fork-fidelity
narrative-state gap. Lowest risk, highest leverage.

---

## 2. Architecture

One new latest-slot frame type, **host-authoritative / one-way**, with a **section-tagged** payload so the
single lane extends to party (and beyond) without minting a frame type per data class.

```
TypeState = 5   (pos=0, battle=1, command=2, control=3, roster=4 already exist)

payload := section+   where section := [sectionId u8][len u16 LE][bytes[len]]
  sectionId 0 = gEventGlobal snapshot   (2048 bytes, reserved windows masked — see §4)
  sectionId 1 = party subset            (RUNG 2 — deferred; the diorama's actor-spawn input)
  sectionId 2 = gScriptVector/Dictionary(long-tail — deferred)
```

**Directionality is the one departure from s37.** Every existing lane is symmetric (both sides send).
`TypeState` is produced ONLY by the host and applied ONLY by the guest. Gate both ends on role: the host
(`_role == "host"`, or more precisely "I am someone's authoritative host") produces; the **follower**
(`_followHost && _socket.IsConnected`) applies. The host must ignore inbound `TypeState` (except the
selftest loopback, §8).

---

## 3. Wire protocol (`NetSyncSocket.cs`)

Frame format is unchanged: `[magic 0xF9][version u8][type u8][len u16 LE][payload]`, `HeaderSize 5`,
`MaxPayload 8192` (`NetSyncSocket.cs:59-96`). A 2048-byte section + a few header bytes is one frame,
comfortably under `MaxPayload` — **no delta/dirty-range needed for v1** (a later optimization only).

Changes:
1. **`NetSyncWire.Version 5 → 6`** (`NetSyncSocket.cs:62`). `TryParseHeader` already rejects a mismatched
   version byte and drops the link (`:91, :441-446`) — this preserves the fail-safe for free (mixed
   engine builds silently don't sync; **both machines must update in lockstep**).
2. **`NetSyncFrames`: add a latest-slot state slot**, mirroring the battle slot exactly
   (`:156-157, :169, :213-215, :244-252`): `_outState` (re-sent every ~33 ms write tick as keepalive),
   `_inState` + `_inStateTick` (2000 ms stale window like the other `_in*` slots).
3. **`INetTransport`: add `SetLocalState(byte[])` and `GetRemoteState()`** (`:36, :40`), following
   `SetLocalBattle`/`GetRemoteBattle`.
4. **`ClearRemote()` must drop `_inState` too** (`:280-290`) — critical for the fail-safe (§7): on link
   loss the guest must stop seeing a stale host snapshot.

`TypeState` is latest-slot, NOT FIFO — we want the newest full story state, never the intermediate ones
(the FIFO discipline is `TypeCommand`-only, `:172-180`).

---

## 4. Host side — the producer

Sample the host's `gEventGlobal` on a cadence and publish it; the write loop re-sends as keepalive.

- **Cadence:** ~150 ms, like `SampleOwnBattle` (`NetSyncBattle.cs:48, :247-251`). Story state changes
  rarely, so this is generous; a change-detect (only `SetLocalState` when the masked array differs from
  the last sent) keeps the wire quiet, matching the roster frame's dirty-check (`:253-262`).
- **Read fresh:** `FF9StateSystem.EventState.gEventGlobal` — `InitEvents()` replaces the array reference
  (`EventEngine.Initialize.cs:43`), so cache nothing; read it each sample (as `WriteCoopCells` and
  `RestoreSnapshot` already do).
- **Mask the reserved windows** before sending (and the guest masks again on apply, defense-in-depth):
  bytes **2032-2041** = the netsync coop cells 2032-2039 (`NetSyncClient.cs:26-34, :242-261`) + the
  reserved 2033/2038-2039 + the choice-mask scratch 2040 (`flags.py:151-152`, `region.py:57`). Copying
  the host's coop-cell view onto the guest would poison the guest's `[[coop]]` gates. (Harmless in
  practice since `Update` rewrites them next frame, but mask for correctness.)
- **Gate:** only a host with a connected follower produces `TypeState`. When nobody's following, don't
  send (or send and let the guest's apply-gate drop it — but not sending is cleaner).

Sketch:
```csharp
// in NetSyncClient.Update, host branch, ~every SampleMs
byte[] snap = MaskReserved(FF9StateSystem.EventState.gEventGlobal); // Array.Copy + zero 2032..2041
if (Changed(snap)) _socket.SetLocalState(BuildStateFrame(sectionId:0, snap));
```

---

## 5. Guest side — the applier + the apply hook

The guest copies the latest received host snapshot into its own `gEventGlobal` **before the field's
`Main_Init` runs**, because the field reads flags once at scene load and does not re-poll — a snapshot that
lands one frame late leaves the guest at scenario-zero for that field with no cheap recovery.

**The apply gate (hard):** apply ONLY while `_followHost && _socket.IsConnected` (the same predicate
`NetSyncVisitor.SuppressEncounters` uses, `NetSyncClient.cs:434`). Applying host flags during the guest's
own solo/federated play would corrupt their live game mid-field.

**The apply hook — the clean synchronous window.** The guest's field-load order is:
`HonoAwake()` → `NetSyncClient.Ensure()` (`HonoluluFieldMain.cs:29`) runs FIRST, then later
`ff9InitStateFieldMap()` → `ee.StartEvents(map.evtPtr)` (`:135`) parses the `.eb` and queues entry-0 via
`NewThread(0,0)` + `activeObj.state = stateInit` (`EventEngine.cs:635-636`); entry-0 bytecode then executes
over subsequent frames. So there is a synchronous slot **in `HonoAwake` right after `Ensure`, or
immediately before `StartEvents`**, to `Array.Copy` the latest host blob into `gEventGlobal` before any
GLOB read fires.

**Ties into follow-warp.** `ServiceFollowWarp` (`NetSyncClient.cs:553-574`) is what warps the guest to the
host's field; the destination field then loads through the hook above, and the latest host snapshot for
that field is already in `_inState` (latest-slot). Sequence: host advances a field → broadcasts flags +
its field id → guest follow-warps → destination `HonoAwake` applies the latest `_inState` → `Main_Init`
reads the host's flags → correct render.

**The write** is the proven bare-array copy (`RestoreSnapshot`, `Ff9mkDebugMenu.cs:2024-2034`;
`WriteCoopCells`, `NetSyncClient.cs:242-261`), masking 2032-2041 so the guest keeps its own coop cells.

Sketch:
```csharp
// in the field-load hook (HonoAwake after Ensure), guest+following only
if (_followHost && _socket != null && _socket.IsConnected) {
    byte[] host = _socket.GetRemoteState(sectionId:0);   // latest-slot, may be null/stale
    if (host != null) {
        var g = FF9StateSystem.EventState.gEventGlobal;   // read FRESH
        CopyExceptReserved(host, g);                      // Array.Copy, skip 2032..2041
    }
}
```

---

## 6. The spectator-save wrapper (MANDATORY companion — build with rung 1, not after)

`gEventGlobal` is the **authoritative save-backed** story heap: Memoria serializes it as a 2048-byte
Base64 `String4K` in the extra-save (`save.py:13, :71, :107-111`). Copying the host's array into the
guest's LIVE array therefore mutates the guest's persistent save — if the guest saves during/after the
session, their solo progress is overwritten by the host's. **Omitting this bricks the guest's save.**

Requirements:
- **On the FIRST real apply** (`FollowHost` on + connected + the host's first `TypeState` snapshot in
  hand): snapshot the guest's OWN `gEventGlobal` into memory, the same tick as the first live write —
  never earlier, or anything the guest does between connecting and the host's first frame is silently
  rolled back by the restore. This is exactly F6 `Snapshot()` (`Ff9mkDebugMenu.cs:2016-2022`).
  *(Correction, 2026-07-15: this spec originally also required bracketing `gScriptVector`/
  `gScriptDictionary` here — the implementation deliberately does NOT, and neither does the F6
  `Snapshot()`/`RestoreSnapshot()` primitive this cites (those containers are only ever `.Clear()`'d
  elsewhere). Inert for rung 1, which never writes them; becomes a real requirement only when a
  future section starts carrying them — see §9.)*
- **While following:** block or redirect saving. Simplest: disable the save-point menu / the save action
  while `_followHost && connected`. Alternative: redirect to a throwaway "co-op spectator" slot. Decide
  and document; blocking is the safe default.
- **On leaving** (clean disconnect, `FollowHost` off, or exit-to-solo): restore the guest's own snapshot
  (F6 `RestoreSnapshot`, `:2024-2034`) so their solo game is untouched. Follower mode is **non-persistent
  by construction.**

---

## 7. Fail-safe & staleness

Preserve the co-op law "feature off / link down → byte-identical vanilla":
- **Version mismatch (v5 vs v6):** the link drops at `TryParseHeader` (`NetSyncSocket.cs:441-446`) — mixed
  builds silently don't sync, as today.
- **Link-down (the critical hazard):** `ClearRemote` drops `_inState` (`:280-290`) so the guest stops
  applying; then the spectator-save wrapper **restores the guest's own `gEventGlobal`** (§6). Never leave
  the host's last snapshot frozen in the guest's live array.
- **Staleness mid-field:** do NOT hard-revert while a field is live (it would pop NPCs mid-scene). HOLD
  the last applied snapshot, raise the existing "connecting / lost" overlay (`NetSyncClient.cs:601-611`),
  and fully revert only on clean disconnect or exit-to-solo (the wrapper's restore path).
- **Apply-gate discipline:** never apply outside `_followHost && connected` — the single most important
  guard against corrupting the guest's own game.

---

## 8. Selftest loopback proof (solo, before any two-machine test)

Copy the `NetSyncBattle.SelfTestPump` pattern (`NetSyncBattle.cs:332-391`): in `Role=selftest`, run the
host's own `gEventGlobal` through the full serialize → frame → parse → apply codec locally (to a scratch
buffer, NOT the live array), and assert the round-trip is byte-identical (minus the masked window). This
proves the wire format + mask + apply math with one machine, exactly as the battle lane was solo-proven,
before the laptop is involved.

---

## 9. Honest limits (document these; they are the ceiling, not bugs)

- **State OUTSIDE `gEventGlobal` won't sync.** Fields also branch on party membership (`B_MEMBER`, op 41,
  `EBin.cs:861-867, :2466`) and item possession (`B_HAVE_ITEM`, op 100, `:544-549, :2525`), read from live
  `FF9StateSystem` party/inventory — the guest's own, as a visitor. So party/item-gated NPCs/doors/branches
  diverge even with identical flags. The mainline spine is overwhelmingly ScenarioCounter + GLOB-bit (so it
  matches); party/item-conditional beats are the fidelity hole. (Rung 2 party-mirror narrows the party
  half.)
- **`gScriptVector`/`gScriptDictionary`** (`EventState.cs:13-14`) are separate save-persisted containers,
  not in the array. Vanilla fields rarely use them; kit/HW-scripted content can. Future section 2.
- **Cutscenes do not lockstep.** Same field + same flags → the guest's own event engine runs the scene
  independently; interactive gates (choices, input-gated dialogue, tread beats) read local state and
  diverge (README § "THE HONEST CEILING"). Separate subsystem, later frontier.

---

## 10. File-by-file change list

| File | Change |
|---|---|
| `Memoria/Netsync/NetSyncSocket.cs` | `Version 5→6`; `TypeState=5`; `_outState/_inState/_inStateTick` latest-slot; `SetLocalState`/`GetRemoteState` on `INetTransport` + both transports; `ClearRemote` drops `_inState`. |
| `Memoria/Netsync/NetSyncClient.cs` | host: sample+mask+`SetLocalState` (~150 ms, change-detect). guest: the apply hook (field-load boundary, `_followHost && connected`, masked `Array.Copy`). Enter/leave-follower → spectator-save snapshot/restore. selftest loopback. |
| `Global/Honolulu/HonoluluFieldMain.cs` | the apply call site — invoke the guest apply right after `NetSyncClient.Ensure()` (`:29`) / before `StartEvents` (`:135`). (Or route entirely through `NetSyncClient` and have it hook the field-load itself — prefer the least field-main coupling.) |
| `Memoria/Netsync/NetSyncState.cs` | (built) `CaptureLiveStory`/`RestoreLiveStory` = the spectator-save capture/restore (a self-contained `Array.Copy`, not a call into the F6 menu). |
| `Global/SaveLoadUI.cs` | (built) the SAVE-BLOCK: the save-confirm path (`OnKeyConfirm`, the `SerializeType.Save` branch) refuses + deny-beeps when `NetSyncClient.IsMirroringStory`; inert in normal play. ⚠ the console `aaaaPlatform` quicksave path in `Show()` is NOT gated (PC saves via the menu path; console is out of scope). |
| `memoria-patches/s37-netsync-battle.patch` | regenerate at rebuild (reverse-apply-check CLEAN before commit); `SaveLoadUI.cs` is NEWLY in the s37 change set. |
| kit (`ff9mapkit/coop.py`) | (built) `coop host` forces `FollowHost=0`. |

No wire change is needed on the kit side for rung 1 (flags are engine-internal). A future `[[coop]]`/journey
"co-op dungeon" preset (curated safe fields) is kit work, separate.

---

## 11. Acceptance / test plan

1. **Solo (selftest loopback):** round-trip the host's own `gEventGlobal` through the codec; byte-identical
   minus the masked window. Gate the whole feature behind this passing.
2. **Two-machine — the core proof:** host warps to a field with a ScenarioCounter/flag-gated NPC or door
   (e.g. a scene that only appears at a given story beat); the following guest sees the SAME NPC/door state
   (not the guest's own scenario-zero version). Confirm on a couple of real fields at different beats.
3. **Two-machine — render-matches-host across rooms:** host moves room-to-room; the guest follows and each
   room renders the HOST's story state (right NPCs/doors). NOTE sequential follow-warp itself is already
   validated (5+ fields warped, guest kept up, 2026-07-13; overworld the known exception) — this test is
   specifically the state-mirror RENDER-match, which needs the lane built.
4. **Save safety:** after a co-op session, the guest exits; confirm the guest's OWN save is unchanged
   (spectator-save restored). Deliberately trigger a link-drop mid-field and confirm the guest reverts to
   its own state, no corruption.
5. **Fail-safe:** a v5 (old-DLL) peer + a v6 host → they simply don't sync (no half-state, no crash).

---

## 12. Build discipline (DANGEROUS — engine rebuild)

Per the repo brief: an engine DLL build AUTO-DEPLOYS with NO backup. Before rebuilding:
- **Close FF9** (the DLL is file-locked while running; the live two-machine session must end first).
- **Back up** `Assembly-CSharp.dll` x64 AND x86 → `backups/<file>.<timestamp>` (and note the pre-change
  hash), per the standard s37 backup convention (`…preSTATEMIRROR.<stamp>`).
- Build via the standard MSBuild recipe; verify the emitted `s37-netsync-battle.patch`
  **reverse-applies CLEAN** against the live tree before committing.
- **Update BOTH machines** — the v5→v6 bump means the laptop must get the new DLL or nothing syncs. Re-cut
  the laptop package (the `FF9Coop-laptop-update` bundle) with the new DLLs.
- One change per in-game test; the human playtests (I can't see the game).

Bundle the two queued small fixes into the SAME rebuild so it's one DLL round: the **empty-command fix**
(`BattleHUD.Unity.cs CollectNetMenus` — omit zero-usable-ability Ability commands) and **`coop host` →
FollowHost=0**.
