# Guest gateway suppression + transition-intent early warp

READ-ONLY research. No engine/kit files were modified. All citations are `file:line` against the
live source tree `C:\gd\FFIX\Memoria\` (uncommitted working tree = s22-s41 + s42 applied) unless a
`memoria-patches\` or `studies\` path is given explicitly.

Context this builds on:
- `C:\Users\skaki\.claude\projects\C--gd-Dream-World-IX\memory\project-ff9-multiplayer-injector.md:606-615`
  **"THE SPECTATOR-FIELD PARADIGM"** (user-set 2026-07-15) already names, as an unscheduled
  near-term item, exactly this feature: *"SUPPRESS the guest's own field interactions while
  following (talk/chest/gateway inhibition) so a wandering guest can't advance or disturb the
  host's world."* This task is that item, plus the responsiveness half.

---

## 1. Stock gateway trace: HOST tread-region -> Field() -> fldMapNo flip -> pos-lane visibility

**Region body (kit convention).** A gateway's tag-2 body runs, per
`C:\Users\skaki\.claude\projects\C--gd-Dream-World-IX\memory\project-ff9-gateway-regions.md:44-54`:
`CalculateExitPosition` (`0xA4 MJPOS`) -> `ExitField` (`0x9E MOVQ`) -> `WalkToExit` (`0xA0 MOVJ`,
busy-loop) -> a fade opcode -> `Field(target)` (`0x2B MAPJUMP`). Verified in source:

- `MJPOS` (0xA4) computes `sMapJumpX/sMapJumpZ` by projecting the player onto the region's
  `q[0]->q[1]` edge — `EventEngine.DoEventCode.cs:2227-2246`.
- `MOVQ` (0x9E) sets `usercontrol = 0` and flags every active object `|= 6` (flush-pending) —
  `EventEngine.DoEventCode.cs:860-871`. **Control is already gone before any fade opcode runs.**
- `MOVJ` (0xA0) is a **per-frame busy-wait opcode**: it calls `MoveToward_mixed` toward
  `sMapJumpX/sMapJumpZ` and `return 1` ("re-run me next frame") until arrival —
  `EventEngine.DoEventCode.cs:872-877`. The player's avatar is walked to the door edge by the
  *script*, not the human, for however many frames that takes.
- The fade itself is a separate opcode (`WIPERGB` 0xEC "FadeFilter" —
  `EventEngine.DoEventCode.cs:632` — or the transport's own wrapper); the script then `Wait`s for
  it before calling `Field()`. The established fade-window CONSTANT used everywhere else in this
  codebase for "gateway-identical" fades is **24 frames / 0.9s** — see the F6 warp recipe below,
  whose own comment says it "matches the gateway FadeFilter."

**`Field()` (0x2B MAPJUMP) opcode handler:**
```
case EBin.event_code_binary.MAPJUMP: // 0x2B, "Field", "Change the field scene"
{
    this.SetNextMap(this.getv2());   // arg1: field scene destination
    return 4;
}
```
`EventEngine.DoEventCode.cs:1008-1012`.

**`SetNextMap` / `FF9ChangeMap`** — the arg is consumed, `nextMapNo` is stashed, but **`fldMapNo`
does NOT change yet**:
```
public void SetNextMap(Int32 MapNo) { this.FF9ChangeMap(MapNo); }
private void FF9ChangeMap(Int32 MapNo) {
    switch (this._ff9Sys.mode) {
        case 1: stateFieldSystem.loc.map.nextMapNo = (Int16)MapNo; break;   // field
        case 2: stateBattleSystem.map.nextMapNo = (Int16)MapNo; break;      // battle (SetBattleScene)
        case 3: stateWorldSystem.map.nextMapNo = (Int16)MapNo; break;       // world map
    }
}
```
`EventEngine.cs:1293-1320`.

**Same frame, immediately after:** `ServiceEvents()` returns 4 up to `FF9FieldMapMain`, which sets
`nextMode = 1` and `FF9Sys.attr |= 8u` (unless `nextMapNo == FLDSCRPT_EVTNO_ENDING`, in which case
`nextMode = 4` "Ending" instead — see §2 staleness) —
`HonoluluFieldMain.cs:242-253`. The function keeps running in the **same call**: at the bottom,
`changeScene = FF9Sys.attr & 15u` is now non-zero, so `shutdownField()` fires —
`HonoluluFieldMain.cs:288-296` — which calls `ff9ShutdownStateFieldMap()`, whose `case 1` does
**`this.FF9.fldMapNo = map.nextMapNo;`** — `HonoluluFieldMain.cs:428-432`.

**So `FF9StateSystem.Common.FF9.fldMapNo` flips to the NEW id in the SAME game frame the `Field()`
opcode executes** — well before any scene actually loads. Immediately after, still same frame:
`SceneDirector.Replace("FieldMap", SceneTransition.FadeOutToBlack_FadeIn, false)` —
`HonoluluFieldMain.cs:299-301` — tears down the old `FieldMap` GameObject and starts an async load
of the new one.

**When does the pos lane start carrying the new id?** `NetSyncClient`'s per-frame tick reads
`fld = FF9StateSystem.Common.FF9.fldMapNo` and gates `onField` on
`ee.gMode == 1 && ee.fieldmap != null` — `NetSyncClient.cs:632-641`. During the load window
(old `FieldMap` destroyed, new one not yet constructed) `ee.fieldmap` is null, so `onField` is
false and the socket broadcasts the **field-0 sentinel**, not the new id —
`NetSyncClient.cs:736-752` (comment: *"Broadcast my TRUE location every frame... the sentinel
makes it despawn instead"*). Only once the new `FieldMap`'s `HonoAwake`/`firstFrame` init has run
(`fieldmap` reassigned at `HonoluluFieldMain.cs:99`, gated behind `SceneDirector.IsReady` and
`!IsFading` at `HonoluluFieldMain.cs:188-190`) does `fld` read the new id again. **This means the
pos lane is silent (field-0) for the ENTIRE duration of the host's own fade-out + async scene
load + fade-in** — the new id only appears once the host's screen is already visible again on the
new field.

**Total latency estimate the guest currently eats before its OWN screen even starts changing**
(status-quo pos-lane detection path):

| Stage | Source | Duration |
|---|---|---|
| Host's own region fade-out (WIPERGB + Wait) | convention, matches `WarpFadeFrames`/`WarpFadeWait` | ~0.9s |
| Host's field load (art/walkmesh/actors) until `fieldmap != null` again | field-dependent, no fixed constant in source | **variable, unmeasured (L)** |
| Wire propagation of the new `rs.Field` | LAN ~ms, relay tens of ms | negligible |
| Guest `FollowHostTick` debounce, `FollowStableMs` | `NetSyncClient.cs:118`, `1091-1098` | **1200 ms fixed** |
| Guest's own fade-out wait before `SetNextMap` | `FollowFadeFrames`/`FollowFadeWait`, `NetSyncClient.cs:119-120`, `1108-1110`, `1158-1179` | **900 ms fixed** |
| Guest's own field load | field-dependent | variable (L') |

Fixed, unavoidable latency baked into the CURRENT design before the guest's screen even **starts**
its own fade-out: **0.9s (host fade) + L (host load, unbounded) + 1.2s (debounce) ≈ at least
2.1s + L**, and the guest doesn't finish (see the new field) until another ~0.9s + L' on top. The
1.2s debounce and the "wait for the load to finish before even detecting the move" gap are exactly
what the intent design in §2 removes.

---

## 2. EARLY-INTENT design

### 2.1 The funnel

Candidates and verdict:

- **The raw fade/wipe call** (`WIPERGB` 0xEC, or `SceneDirector.FF9Wipe_FadeOutEx`) — earliest in
  wall-clock time, but **not decidable**: fields fade the screen for reasons that are NOT a
  `Field()` transition (mood fades, flashback fades, camera-switch fades). Hooking it would
  produce false-positive "intent" frames. Rejected.
- **The `Field`(0x2B)/`WorldMap`(0xB6) opcode handlers** — decidable, but two call sites to hook,
  and miss the fact that `SetNextMap` is a narrower, unified choke point both already fall through
  to.
- **`EventEngine.SetNextMap(Int32 MapNo)`, `EventEngine.cs:1293-1296`** — **recommended funnel.**
  Every field-mode transition source funnels through it: `MAPJUMP` (gateways + scripted/cutscene
  `Field()` calls, `DoEventCode.cs:1010`), `WMAPJUMP` (world-map exits, `DoEventCode.cs:2429`),
  the F6 debug menu's own warp (`ee.SetNextMap(mapNo)` inside `ServicePendingWarp`,
  `backups\Ff9mkDebugMenu.cs.20260715-234506:1673-1690` region — direct C# call, no opcode), and
  `NetSyncClient`'s own `ServiceFollowWarp` (`NetSyncClient.cs:1171`, which must be **excluded**
  from re-broadcasting, see §2.4). It is called ONLY for mode 1 (field) and mode 3 (world map) —
  battle uses the sibling `SetBattleScene` -> `FF9ChangeMap` mode-2 branch (`EventEngine.cs:1298-1301`),
  so hooking `SetNextMap` specifically and NOT `FF9ChangeMap` generically **naturally excludes
  battle transitions** (battle already has its own diorama/spectator system, B0+B1 — a field-follow
  intent for battle would be redundant/conflicting).
  It fires at the moment the destination id is *decided* — which in practice is ~0.9s AFTER the
  host's screen visually started fading (the script `Wait`s out the fade before calling `Field()`,
  per §1) but still far, far earlier than "wait for the new id to survive the whole load + appear
  on the pos lane." This is the best available "screen just started going black, we know exactly
  where it's headed" hook without false positives.

### 2.2 Wire home: NOT `TypeControl` — extend `TypeState` instead

`TypeControl` (type 3) is tempting (task's own suggested candidate) but has an **existing,
unconditional per-tick owner**: `NetSyncBattle.Tick()` calls `socket.SetLocalControl(...)` (either
`BuildControl(...)` or `null`) every frame based on **that machine's own** battle/assist state —
`NetSyncBattle.cs:388-402`. On a normal host (host fights, guest assists), the host's own tick
takes the `else` branch and calls `socket.SetLocalControl(null)` **every frame regardless of what
we might want to say**, because `live` (peer-in-battle) is false. Writing transition-intent onto
`TypeControl` from a second call site (`NetSyncClient`'s `SetNextMap` hook) would be silently
stomped by `NetSyncBattle`'s own write on the very next tick — a genuine collision, not a
theoretical one.

`TypeState` (type 5) has no such collision: it is **already host-only, one-way** (comment:
*"the guest never produces TypeState"*, `NetSyncClient.cs:754-756`), already **section-tagged for
exactly this kind of extension** (`NetSyncState.cs:14-15`: `payload := section+` where
`section := [sectionId u8][len u16 LE][bytes[len]]`), and its ONLY writer is `NetSyncClient`'s own
tick (`_socket.SetLocalState(NetSyncState.SnapshotAll())`, `NetSyncClient.cs:757-761`) — the same
class that owns `FollowHostTick`. Existing sections: `SectionStory = 0` (`NetSyncState.cs:33`),
`SectionParty = 1`, `SectionKeyItems = 2`, `SectionBag = 3` (`NetSyncParty.cs:43-45`).
**Recommendation: add `SectionIntent = 4`**, payload `[destField u16][nonce u8]` (nonce = a
free-running counter so the guest can detect "this is a NEW intent, not the one I already acted
on" without needing sequence numbers on the whole frame).

Cadence: the normal state publish is throttled to ~7 Hz (`Environment.TickCount - _storyTick >= 150`,
`NetSyncClient.cs:757`) — too slow for "the instant the fade starts." But the underlying transport
write loop runs independently at **~30 Hz** (`Thread.Sleep(33)`,
`NetSyncSocket.cs:558-571`) and resends whatever the latest-slot value is as keepalive
(`INetTransport.SetLocalState` doc comment, `NetSyncSocket.cs:39`). So: the `SetNextMap` hook
should call `_socket.SetLocalState(NetSyncState.SnapshotAll())` **immediately, out-of-band**, the
moment it fires (bumping the intent nonce first) — bypassing the 150ms game-thread throttle for
that one call. The frame reaches the wire within one write-loop tick, **~33ms**, not 150ms and
absolutely not the multi-second pos-lane path from §1.

### 2.3 Does this need a wire version bump?

**Mechanically:** no. A new section on an already section-tagged, host-only lane is exactly the
kind of change `NetSyncState.ApplyStoryTo`'s parse loop already tolerates (unrecognized/absent
sections are simply not there; a peer without the new code just never looks for section 4).

**By this project's actual convention: yes, bump it anyway.** Every prior wire-payload addition —
even purely additive, backward-compatible-in-principle ones — has shipped with a version bump:
- v2 -> v3 introduced the whole typed-frame format itself (`[F9][ver][type][len][payload]`,
  types 0-3) — memory `project-ff9-multiplayer-injector.md:239-241`.
- v6 introduced `TypeState` (section 0, story) — memory `...md:507`.
- **v7 added sections 1-3 (party mirror) to the ALREADY section-tagged `TypeState` lane** —
  memory `...md:583-585` — i.e. the exact shape of change proposed here for section 4, and it
  still bumped.
- v8 added the diorama boot block to type-1; v9 added the action lane (type 6) + a trance byte;
  v10 added a songId field + a stat-tick bit — `NetSyncSocket.cs:87-90`.

The project's own stated rationale: `NetSyncSocket.cs:82-83` — *"v9 and older peers are REJECTED
by the version byte -> mixed engine versions silently don't sync (fail-safe; update both machines
together when the wire changes)."* This is a deliberate **reject-wholesale-over-partial-sync**
policy, not a strict-necessity one. **Recommendation: bump to wire v11** alongside adding
`SectionIntent`, matching every precedent, even though the section-tag mechanism alone would
probably survive a mismatched peer gracefully.

### 2.4 Staleness, cancellation, and re-entrancy

- **A fired `Field()` always completes (host-side).** Once `ServiceEvents()` returns 4,
  `HonoluluFieldMain.cs:242-253` unconditionally sets `nextMode` (1 or 4) and `attr |= 8u` in the
  same frame, and the `changeScene` check further down (`HonoluluFieldMain.cs:288-333`)
  unconditionally calls `shutdownField()` + `SceneDirector.Replace(...)`. No code path found that
  aborts a transition once `SetNextMap` has been called for mode 1/3. So an intent frame, once
  emitted from a genuine host-side `SetNextMap` call, is a reliable promise — no "intent fired but
  nothing happened" case to reconcile.
- **The ENDING exception.** `nextMapNo == FF9Define.FLDSCRPT_EVTNO_ENDING` (`FF9Define.cs:211`,
  value 16000) diverts `nextMode` to 4 ("Ending" scene) instead of 1 (`HonoluluFieldMain.cs:243-247`).
  `SetNextMap` cannot see this branch — it only stashes `nextMapNo`. **The intent hook must special-
  case `destField == FLDSCRPT_EVTNO_ENDING`**: either suppress the intent entirely, or emit a
  distinct "session terminating, do not follow" signal — there is no explorable field for the
  guest to warp into.
- **Battle transitions never reach this hook** (see §2.1 — `SetBattleScene`/mode-2 bypasses
  `SetNextMap`), so no special-casing needed there.
- **Game Over** (`ServiceEvents()` returning 8, `HonoluluFieldMain.cs:262-270`) also never touches
  `SetNextMap` — correctly, no intent frame, and existing peer-alive/exit-ramp logic
  (`NetSyncClient.cs:643-663`) already covers "host vanished."
- **Double-warp race with the pos-lane path.** `FollowHostTick`'s entry guard,
  `if (!_followHost || _followWarpPending >= 0) return;` (`NetSyncClient.cs:1075-1076`), already
  serializes ANY warp start. The intent handler must obey the **same** guard before firing. On
  success it must ALSO set `_followWarpedTo = destField` exactly as the pos-lane path already does
  (`NetSyncClient.cs:1111`), so that once `rs.Field` eventually catches up to the same destination,
  the existing `if (rs.Field == _followWarpedTo) return;` check (`NetSyncClient.cs:1089-1090`)
  suppresses the redundant second warp for free — no new dedup state needed, reuse what's there.
- **s42 same-field-kick interplay.** `SameFieldKickTick` is gated `_sameFieldKickDone ||
  _storyMirroring || _exitRampPending || _role != "client"` (`NetSyncClient.cs:1130-1135`) and is
  reached only from `FollowHostTick`'s `rs.Field == myField` branch (pairing while already
  co-located, pre-mirror). Intent-driven warps are a mid-session, post-mirror-arm phenomenon in
  the common case — temporally disjoint, no direct conflict. Corner case worth flagging, not
  resolving here: if the host itself performs a same-field reload (F6, or some future host-side
  s42 analogue) mid-session, `destField == myField == host'sOwnCurrentField`; that should route
  through the same "clean reload" path `SameFieldKickTick`/`ServiceFollowWarp` already use
  (`_followWarpPending = myField`, `NetSyncClient.cs:1146`), not be treated as a no-op.
- **Unregistered destination.** The pos-lane path already refuses to warp to a field this install
  doesn't know: `if (!EventEngineUtils.eventIDToFBGID.ContainsKey(rs.Field)) return;`
  (`NetSyncClient.cs:1105-1106`), falling back to the `OvlPeerNoField` overlay
  (`NetSyncClient.cs:802-804`). **The intent handler must run the identical guard against
  `destField`** before acting — a host-only custom/forked field the guest's install doesn't have
  must not attempt a warp (it would immediately fail on `SetNextMap`'s own field-data lookups).

---

## 3. GUEST GATEWAY SUPPRESSION design

### 3.1 The fade-before-Field hazard, precisely

By the time a naive "just skip the `Field()` opcode" runs guest-side, the guest's OWN mirrored
copy of the SAME script has already, per §1:
1. `MJPOS` computed an exit point.
2. `MOVQ` set `usercontrol = 0` and flagged objects for flush.
3. `MOVJ` walked the guest's avatar to that point over N frames (script-driven, not player input).
4. A `WIPERGB`/fade opcode ran and the script `Wait`ed out the full fade window (~0.9s) — **the
   guest's screen is now fully black.**

If only the `Field()` opcode is skipped (`return 0` instead of `SetNextMap(...); return 4`), steps
1-4 all already happened and are **not undone** — the guest is left with `usercontrol = 0` and a
black screen, no scene transition ever arrives to fade back in. **This is a genuine softlock if
nothing else recovers it**, exactly as flagged.

### 3.2 Option evaluation

**(a) Skip `Field()` guest-side, mirroring the proven s38 `ENCOUNT`/`ENCOUNT2` pattern.**
`s38-netsync-spectator-field.patch` gates those opcodes with `if
(Memoria.Netsync.NetSyncClient.IsMirroringStory) return 0;` placed **after** the `getv()` calls
that consume the opcode's args (`memoria-patches\s38-netsync-spectator-field.patch:24-41`,
respecting the gArgUsed trap — see the in-repo comment at `EventEngine.DoEventCode.cs:966-968`).
The identical shape applies to `MAPJUMP`: consume `getv2()` first, THEN gate:
```
case MAPJUMP:
{
    Int32 destField = this.getv2();      // must run before any gate (gArgUsed trap)
    if (<suppress-guard>)
        return 0;                        // continue inline, no transition
    this.SetNextMap(destField);
    return 4;
}
```
This is decidable, minimal-diff, and reuses an already-shipped, already-playtested pattern.
**But it does not by itself solve the §3.1 hazard** — it needs a companion recovery.

  *What else flows through `Field()` guest-side that must not break:* a mirrored cutscene's own
  scripted `Field()` (fine to suppress — the destination is the same field the host is visiting,
  which §2's intent/follow-warp already drives the guest to); the exit ramp
  (`NetSyncState.ExitMirrorToOwnSave`, `NetSyncClient.cs:617`) does **not** go through the opcode
  at all — it is a direct save-reload, out of scope for an opcode-level guard; world-map exits
  (`WMAPJUMP`) are a **separate opcode** and would need the same treatment if the guard is meant
  to be comprehensive (the guest independently driving itself off the world map is the same
  "guest shouldn't decide where to go" problem).

  *Recovery, and why pairing with §2 makes it cheap:* once suppressed, the guest is faded-black
  with `usercontrol = 0`. In the **common case** — the guest touched the same gateway the host is
  also using — §2's intent frame is *already* in flight or about to be (the host started its own
  fade ~0.9s before calling `Field()`, and intent fires at that same `SetNextMap` moment), so
  `FollowHostTick`/`ServiceFollowWarp` will shortly call its own `FF9Wipe_FadeOutEx` +
  `SetNextMap` + `nextMode = 1` + `attr |= 8u` (`NetSyncClient.cs:1107-1179`) — which restores
  `usercontrol` itself (`ee.SetUserControl(false)` then the destination field's own load re-arms
  control normally) and **does** complete a real scene transition, fading back in on arrival. The
  suppressed gateway's leftover black screen is invisibly subsumed into the legitimate transition
  — no bespoke "force fade-in" hack needed for that path.
  The **uncovered case**: the guest touches a DIFFERENT gateway than the one the host is using (no
  intent will ever arrive for it, no follow-warp coming). This is a true dead end and needs an
  explicit safety net: **a short watchdog** — if `MAPJUMP` was suppressed and no
  `_followWarpPending`/fresh intent shows up within roughly one fade window's grace period, force
  `SceneDirector.FF9Wipe_FadeIn()` + `SetUserControl(true)` locally, leaving the guest standing at
  the exit edge on the SAME field, state otherwise untouched.

**(b) Prevent gateway regions from arming/firing for the guest at the `TreadQuad` level.**
`TreadQuad` (`EventEngine.TreadQuad.cs:6-22`) matches ANY `cid == 3` object with a live tag-2
function and returns the FIRST one whose quad contains the player — there is **no engine-level
type tag** distinguishing "this tag-2 body is a gateway" from "this tag-2 body is a
`[[coop]]` plate, a walk-triggered message, a camera-switch zone, a chocobo hot/cold probe, etc."
— it's opaque bytecode at the engine layer. **This is NOT decidable generically at runtime**
without a bytecode scan (walking the function's opcode stream looking for a reachable `MAPJUMP`)
— feasible in principle (a one-time static scan per region at field-load, cached per field id) but
non-trivial for arbitrary/forked real-FF9 regions the kit didn't author (no build-time manifest of
"which regions are gateways" exists for a `--verbatim` fork of a real field; only kit-authored
`[[gateway]]` blocks are self-describing). Compare to (a): the `Field()` opcode itself is the
**only** 100%-decidable, zero-false-positive signal that "this tag-2 body was, in fact, a
transition" — trying to classify *ahead* of `TreadQuad` reinvents that same signal less reliably.
**Not recommended** as the primary mechanism; a build-time-only refinement (kit-authored fields
tag their own gateway region slots) could layer on top of (a) later but isn't required.

**(c) Block the guest's movement INTO gateway zones.** Requires the SAME undecidable
classification as (b) (which zones are "gateway" to block), plus turns a movement failure into a
UX dead-end/wall the guest bumps into for no visible reason. Rejected — strictly worse than (b).

**(d) Leave gatewaying live; let follow-warp instantly yank the guest back (status quo+).** Cheapest,
zero new engine surface, but does not satisfy the user's explicit ask ("the guest shouldn't decide
where to go") — the guest still visibly transitions to wherever its own script sends it (possibly
a field the host never visits) before being yanked away, and burns a real scene load + fade round
trip for nothing. Also does not compose with §2: an intent frame racing a guest-initiated `Field()`
the intent didn't cause is exactly the double-warp scenario §2.4 has to guard against for no
functional benefit.

### 3.3 Recommendation and guard predicate

**Recommend (a)** — gate `MAPJUMP` (and, for completeness, `WMAPJUMP`) guest-side with the same
consume-args-then-gate shape as s38's `ENCOUNT` — **plus** the watchdog recovery from §3.2, and
built together with §2 so the common case is a non-event.

**Guard predicate: `IsLiveFollowedSession`, NOT `IsMirroringStory`.** The two differ meaningfully
(`NetSyncClient.cs:265-294`):
- `IsMirroringStory` (`NetSyncClient.cs:269-272`) is true **only after the story mirror has armed**
  — which per its own comment happens "only at a field-load boundary that sees a host snapshot."
  It is false during the gap between "session goes live" and "first field-load boundary" — exactly
  the gap `SameFieldKickTick` exists to close (`NetSyncClient.cs:1130-1155`, gated
  `!_storyMirroring`). s38 uses this predicate for menu/battle suppression because those need the
  mirror's *data* to already be trustworthy before hiding local UI.
- `IsLiveFollowedSession` (`NetSyncClient.cs:282-294`) is true as soon as the session is
  enabled + following + connected + the peer's position lane is fresh — **before** the mirror has
  necessarily armed. Its own comment explains it was added "deliberately NOT IsMirroringStory" for
  exactly this kind of gap-sensitive consumer (the diorama).

Gateway suppression is about **navigation authority**, not story-state trustworthiness — it should
be true from the moment following begins, including in the pre-mirror-arm gap (where, notably,
`SameFieldKickTick` may ITSELF be about to fire a same-field reload — suppressing the guest's own
gateway wandering during that exact window is squarely in scope). Using `IsMirroringStory` would
leave a real coverage hole (a guest could wander through a gateway in the first few seconds of a
session before the first mirror boundary lands). **Use `IsLiveFollowedSession`.**

**Failure modes of the recommended design:** (i) the "different gateway than the host" dead end
from §3.2, covered by the watchdog; (ii) a guest mid-walk-to-exit-edge (`MOVJ`, still consuming
frames) when the session state flips from `IsLiveFollowedSession==true` to `false` (host
disconnects mid-approach) — the in-flight `MOVJ` will complete and `Field()` will fire normally
(guard re-evaluated fresh each opcode dispatch, and by then suppression is correctly off) — no new
hazard, this is just the region behaving like solo play from that point on; (iii) `WMAPJUMP` left
unguarded if only `MAPJUMP` is patched — call out explicitly as a follow-up, same shape.

---

## 4. Composition: how suppression + early-intent fit together

With guest gatewaying OFF (§3), the guest **never** self-initiates a field transition while
`IsLiveFollowedSession` — every legitimate guest transition is follow-driven. This makes the
intent lane (§2) the primary, and in the common case *only*, path that moves the guest at all —
its responsiveness is no longer a "nice to have," it's the whole transition experience.

Guest transition sources, reconciled:

```
                    host SetNextMap(dest) fires  ─────────────► §2: SectionIntent(dest, nonce)
                              │                                  pushed out-of-band, ~33ms to wire
                              │ (host fade already ~0.9s in)              │
                              ▼                                          ▼
                    host's own scene loads/fades                FollowHostTick sees a NEW nonce:
                    (field-dependent L)                          - skips the 1200ms debounce
                              │                                  - skips waiting for rs.Field
                              │                                  - guarded by the SAME entry check
                              ▼                                    (_followHost, _followWarpPending<0)
                    pos-lane eventually carries dest too  ───►  - guarded by the SAME registration
                    (rs.Field == dest, §1's slow path)             check (eventIDToFBGID)
                              │                                  - fires SetUserControl(false) +
                              │   if intent already warped:        FF9Wipe_FadeOutEx + sets
                              │   rs.Field == _followWarpedTo        _followWarpedTo = dest
                              │   → FollowHostTick no-ops           (dedup: pos-lane path below
                              ▼                                      becomes a no-op, §2.4)
                    (redundant path suppressed for free)                 │
                                                                          ▼
                                                                 ServiceFollowWarp (0.9s later):
                                                                 SetNextMap(dest) + nextMode=1 +
                                                                 attr|=8u  — same F6-recipe warp
                                                                 already in use today

  Meanwhile, guest's OWN gateway touch (if any):
    MAPJUMP suppressed (§3) while IsLiveFollowedSession
      → if the above intent/warp is already in flight (common case): its fade-out/fade-in
        subsumes the guest's already-black screen, no visible seam
      → if NOT (guest wandered into an unrelated gateway): watchdog force-fades back in,
        guest stays put on the current field, no transition

  s42 same-field kick: fires only pre-mirror-arm, on rs.Field == myField at link-up
    (NetSyncClient.cs:1082-1088, 1130-1155) — temporally disjoint from the above in the
    common case; a host-side same-field reload mid-session should reuse this same
    "_followWarpPending = myField" path rather than being treated as a no-op (§2.4)

  Exit ramp: NetSyncState.ExitMirrorToOwnSave (NetSyncClient.cs:617) — session-end only,
    bypasses SetNextMap/opcodes entirely, orthogonal to all of the above
```

Net effect: intent collapses the guest's screen-starts-changing latency from **~2.1s + L**
(§1: host fade 0.9s + host load L + 1.2s debounce) down to **effectively the host's own fade
window** (~0.9s, the time already visible on the HOST's screen before `Field()` fires) **+ wire
latency (~33ms)** — the guest's fade-out can start essentially in lockstep with the host's,
instead of only after the host has already finished loading the destination and broadcast it. The
1.2s debounce and the "wait for the full load" gap are both bypassed for the intent-driven path;
they remain, unused in the common case, as the fallback for any transition intent doesn't cover
(e.g. a peer running pre-intent code, or the destField-unregistered/ENDING/battle exclusions in
§2.4) — the pos-lane path is not removed, just made redundant when intent gets there first.

---

## Sources consulted

- `C:\gd\FFIX\Memoria\Assembly-CSharp\Global\Event\Engine\EventEngine.cs` (SetNextMap/FF9ChangeMap/SetUserControl)
- `C:\gd\FFIX\Memoria\Assembly-CSharp\Global\Event\Engine\EventEngine.DoEventCode.cs` (MAPJUMP/WMAPJUMP/ENCOUNT/MJPOS/MOVQ/MOVJ/WIPERGB opcodes)
- `C:\gd\FFIX\Memoria\Assembly-CSharp\Global\Event\Engine\EventEngine.TreadQuad.cs`
- `C:\gd\FFIX\Memoria\Assembly-CSharp\Global\Honolulu\HonoluluFieldMain.cs`
- `C:\gd\FFIX\Memoria\Assembly-CSharp\Assets\Scripts\Common\SceneDirector.cs`
- `C:\gd\FFIX\Memoria\Assembly-CSharp\Memoria\Netsync\NetSyncClient.cs`
- `C:\gd\FFIX\Memoria\Assembly-CSharp\Memoria\Netsync\NetSyncSocket.cs`
- `C:\gd\FFIX\Memoria\Assembly-CSharp\Memoria\Netsync\NetSyncState.cs`
- `C:\gd\FFIX\Memoria\Assembly-CSharp\Memoria\Netsync\NetSyncParty.cs`
- `C:\gd\FFIX\Memoria\Assembly-CSharp\Memoria\Netsync\NetSyncBattle.cs`
- `C:\gd\FFIX\Memoria\Assembly-CSharp\Global\ff9\FF9Define.cs`
- `C:\gd\FFIX\Memoria\backups\Ff9mkDebugMenu.cs.20260715-234506` (the F6 deferred-fade warp recipe)
- `C:\gd\Dream-World-IX\.claude\worktrees\field-coop-design-4f3761\memoria-patches\s38-netsync-spectator-field.patch`
- `C:\Users\skaki\.claude\projects\C--gd-Dream-World-IX\memory\project-ff9-gateway-regions.md`
- `C:\Users\skaki\.claude\projects\C--gd-Dream-World-IX\memory\project-ff9-multiplayer-injector.md`
