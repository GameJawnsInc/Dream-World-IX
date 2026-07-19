# Same-field separation: platforms/ladders + teleport-to-host — design study

**Status:** research only, nothing implemented. Read-only pass over `C:\gd\FFIX\Memoria\` (live
engine tree, source of truth), `memoria-patches\s21-dev-hotkeys-f6-f10.patch` /
`s22-debug-menu-f6.patch` / `s36-netsync-ghost.patch` / `s37-netsync-battle.patch`, the kit's
`content/ladder.py` / `content/platform.py`, and project memory (`project-ff9-moving-platforms-
elevators.md`, `project-ff9-jump-navigation.md`, `project-ff9-multiplayer-injector.md`). All cites
are `file:line` against the live tree unless marked "kit" (the mod repo) or "memory". A sibling
study, `studies/field-coop/camera.md`, covers the guest-camera-follows-host question in depth; this
doc cross-references it rather than duplicating it.

---

## 1. Mechanism ground truth — do platforms/ladders ride the talk path or the region path?

**Headline finding: platforms and ladders are REGION triggers (`cid==3` "Quad" objects), an
architecturally separate dispatch path from NPC dialogue (`cid==4` Actor objects). A suppression
scoped to NPC talk will NOT touch platforms/ladders/jumps/chests/gateways/savepoints unless it is
explicitly extended to the region path too.**

### 1.1 Two independent input-dispatch paths, same button

`EventCollision.cs` has two top-level checks, both run every frame off the SAME "confirm pressed"
read, but against different object populations:

- `CheckNPCInput` (`EventCollision.cs:85-…`) — reads `ETb.KeyOn() & Confirm(|Special)`, then calls
  `EventCollision.Collision(instance, po, 4, ref distance)` (a proximity/facing-angle test against
  `cid==4` Actor objects) and `IsNPCTalkable(obj)`. This is the NPC-dialogue path.
- `CheckQuadInput` (`EventCollision.cs:60-83`) — the identical key read, but calls
  `instance.TreadQuad(po, 4)` (`EventEngine.TreadQuad.cs:6-22`), which walks `_context.activeObj`
  and tests **`cid==3`** objects' `Quad` polygon against the caller's XZ position
  (`IsInQuadHotFix`/`IsInQuad`, `EventEngine.TreadQuad.cs:24-54`), gated on `IsQuadTalkable`
  (`EventCollision.cs:442-…`). This is the region-trigger path — gateways, chests, ladders,
  platforms, jumps, and savepoints (all authored by the kit as `REGION_ENTRY_TYPE = 1` entries,
  `content/region.py:113` "kit") share this SAME code path.
- The tread/"!" analogue is the same split one level up in `EventCollision.Update`-equivalent
  logic (`EventCollision.cs:250-268` for NPC-tread icon polling, `:279-304` for
  `TreadQuad(po, 2)`/`TreadQuad(po, 4)` region tread+action polling).

Both checks are driven by `instance.Request(obj, 1, tag, false)` (fires the object's own tag-2/3
function) — nothing routes an NPC talk through `TreadQuad`, and nothing routes a region trigger
through `Collision(..., 4, ...)`/`IsNPCTalkable`. **Design implication for the sibling
talk/chest-suppression agent:** a static guard flag (following the established
`NetSyncVisitor.SuppressEncounters` pattern, `Assembly-CSharp\Memoria\Netsync\NetSyncVisitor.cs:27`)
inserted only in `IsNPCTalkable`/`CheckNPCInput` leaves `CheckQuadInput`/`TreadQuad` — and therefore
every ladder/platform/jump/gateway/chest/savepoint region — completely unaffected. If chests need
suppressing too (the task brief says chest suppression is in scope for that agent), the guard must
ALSO cover `IsQuadTalkable`/`CheckQuadInput`, or more surgically discriminate chest quads from
ladder/platform/gateway quads inside that same function (chests are `content/chest.py` "kit"
region entries — same `cid==3` family, no engine-level tag distinguishing "chest" from "ladder"
region beyond what the `.eb` body itself does).

### 1.2 What actually moves the player: NOT engine tile-motion — a per-frame script rewrite

The engine's native tile-motion opcodes only ever touch a 2D background overlay image, never the
walkmesh or an actor's position:

- `BGLLOOP` / `0x5C` *"MoveTileLoop"* (`EventEngine.DoEventCode.cs:1725-1733`) →
  `fieldmap.EBG_overlaySetLoop(overlayNdx, isEnabled, xSpeed, ySpeed)`.
- `BGLPARALLAX` / `0x5D` *"MoveTile"* (`:1734-1741`) → `EBG_overlaySetParallax(...)`.
- `BGLATTACH` / `0x92` *"AttachTile"* (`:2045-2049`) → `fieldmap.EBG_charAttachOverlay(...)`, whose
  own inline doc comment reads *"Make a part of the field background follow the player's
  movements. Also apply a color filter"* — i.e. it makes a **BG overlay tile track the player**,
  not the other way around.

None of these three write `po.pos[]`/`curPos`/the walkmesh. This matches the kit's own byte-level
census (memory `project-ff9-moving-platforms-elevators.md`): the Lindblum lift (field 2151) is a
pure **SCROLL-illusion** (player stationary, BG tile loops, then a real `Field()` re-entry at the
destination floor) with **zero** `AttachTile`/`SIM` in its `.eb`.

The mechanism that DOES move the player — used by the kit's synthetic `[[platform]]`/navigable
ladder AND faithfully replicated from the one real interactive lift the kit found with genuine
in-place player motion (Pandemonium 2712/2713, `pd_elv`/`pd_evd`) — is a **per-frame script
rewrite of the player's own position**, always via the Y-aware move opcode:

- `POS3`/`DPOS3` / `0xA1`/`0xAD` *"MoveInstantXZY(Ex)"* (`EventEngine.DoEventCode.cs:2159-2226`) →
  `this.SetActorPosition(po, destX, destZ, destY)` — takes X, Z, **and Y** (height).
- `JUMP3` / `0xDC` *"Jump"* (`:2074-2087`) — same primitive, called once per frame from inside a
  `stay()`-looped opcode, interpolating `actor.pos[]` along the arc set up by `SETVY3`/`0xE2`
  *"SetupJump"* (`:2909`) and re-asserting it via `SetActorPosition` every tick.

Both the kit's ladder (`ff9mapkit\ff9mapkit\content\ladder.py`, "kit") and platform
(`ff9mapkit\ff9mapkit\content\platform.py`, "kit") primitives are grafted onto the **PLAYER's own
object entry** (`PLAYER_UID = 250`) and dispatched by a **region**, not a talk func:

```
# content/ladder.py:428-436 "kit" — ladder_region(): a type-1 region entry
init  = SetRegion(zone)
tread = MOVEMENT_GATE + Bubble(1)                                   # the "!" prompt
action = MOVEMENT_GATE + DisableMove + RunScriptSync(2, 250, climb_tag) + EnableMove
```
```
# content/platform.py:201-220 "kit" — platform_region(): identical shape
init  = SetRegion(zone)
tread = MOVEMENT_GATE + Bubble(1)              # or auto-fire on tread if trigger="tread"
action = MOVEMENT_GATE + DisableMove + RunScriptSync(2, PLAYER_UID, ride_tag) + EnableMove
```

`RunScriptSync` runs the destination function **in the player's own execution context (UID 250)**,
so its `MoveInstantXZY` writes move the controlled actor; `DisableMove`/`EnableMove` bracket
free-walk while the climb/ride plays out. This is the SAME primitive the kit's faithful ladder
(field 706 `EVT_GIZ_TO_WORLD`, held-d-pad navigable climb, `content/ladder.py:231-425` "kit") and
the faithful platform carry (Pandemonium, `content/platform.py:138-198` "kit") both use — confirmed
in-game per `project-ff9-moving-platforms-elevators.md`.

**Conclusion for point 1:** platforms and ladders trigger via the exact same region/`TreadQuad`
mechanism as gateways/chests/savepoints/jumps — never via NPC talk (`CheckNPCInput`/
`IsNPCTalkable`). They will keep working for a guest under any suppression design that is scoped to
NPC dialogue specifically. They ride/climb via a `RunScriptSync`-invoked function on the player's
OWN object, driven by per-frame `MoveInstantXZY` (0xA1) — pure script, no native engine "rider"
physics exists in this codebase for player-position carry.

---

## 2. Same-field separation / softlock scenarios for a following guest

Everything below follows from one structural fact, independently confirmed by the sibling camera
study (`studies/field-coop/camera.md:180-197`, "kit"): **host and guest each run their OWN
`EventEngine`/`FieldMap` instance.** Only `Field, Anim, Model, MeshVis, Loco, Pos, Rot` cross the
wire (`RemoteState`, `NetSyncSocket.cs:13-25`) — no story-flag/region-execution state at all beyond
what the separate STATE-MIRROR/PARTY-MIRROR lanes explicitly serialize. A region firing on the
host's machine (`TreadQuad`/`Request`, `EventEngine.TreadQuad.cs:6-22`) only ever tests the HOST's
own `po` against the HOST's own `activeObj` list — it has no way to also move the guest's actor.
Concretely:

1. **Platform ride, host boards, guest doesn't.** The host presses action inside the platform's
   region quad → `RunScriptSync(2, 250, ride_tag)` runs **only inside the host's EventEngine**,
   rewriting only the host's `PosObj.pos[]`. The guest, standing anywhere else (even right next to
   the region on their own screen), never enters that host-local `RunScriptSync` call — nothing
   moves the guest's actor. If the ride ends in a `warp_to` (`content/platform.py:191-194` "kit",
   the elevator-style inter-floor case: fade + `Field()`), the host's field-id BROADCAST changes and
   `FollowHostTick` picks it up (cross-field case, §2.4 below, already handled). If the ride is a
   pure in-field `rise`/`land` carry with no `warp_to` (the common in-screen lift case,
   `carry_body`/`_carry_land_body`, `content/platform.py:70-198` "kit"), the host's `Field` never
   changes — the two players end up standing at DIFFERENT world coordinates on the SAME field id,
   with no signal anywhere in the wire protocol that distinguishes "same field, far apart" from
   "same field, adjacent." This is the exact same-field-separation gap the brief describes.
2. **Ladder-gated ledge, only the presser climbs.** Identical shape: `RunScriptSync(2, 250,
   climb_tag)` (`content/ladder.py:433-435` "kit") runs host-local only. A ladder ending in
   `top_action="field"` (`navigable_climb_body`, `content/ladder.py:408-416` "kit") is a cross-field
   case (handled); a ladder ending `top_action="floor"` (dismount onto a higher/lower floor of the
   SAME field, `:421-422`) strands the non-climbing player exactly like the in-field platform case.
3. **One-way jumps/drops** (`content/jump.py` "kit", the region→`RunScriptSync`→`SetupJump`/`Jump`
   arc, memory `project-ff9-jump-navigation.md:16-25`) — same shape again: only whoever presses
   action at the ledge jumps. A ledge that's one-way by design (no jump back up) can leave the two
   players on opposite sides of an impassable gap with no shared crossing left.
4. **Scripted player-warps within a field** — any `.eb` cutscene that calls `MoveInstantXZY`/
   `SetActorPosition` on the PLAYER's own uid as part of a cutscene body (not through the
   ladder/platform/jump primitives specifically, just ordinary field-script choreography, e.g. a
   forced walk-and-reposition after a story beat) has the identical property: it runs inside
   whichever machine's `EventEngine` reached that instruction, and per the multiplayer memory's
   established law (quoted in `camera.md:193-197`, "kit"): *"the guest's cutscenes fire from the
   GUEST's own position — both machines run the same script off mirrored flags but the TRIGGER is
   local, so they are two independent scripts that happen to agree, not two views of one
   cutscene."* If the host's copy of a cutscene relocates the host mid-field and the guest's own
   mirrored trigger hasn't fired (different scenario/flag timing — the project's own documented
   "narrative-state is the weak axis," `CLAUDE.md` §1 "north star"), the two positions diverge with
   no recovery.
5. **A tread-only ("auto-fire on walk-in") region** — `trigger="tread"` platforms/jumps
   (`content/platform.py:213-215`, jump `trigger="tread"` per `project-ff9-jump-navigation.md:19`)
   fire on mere proximity, meaning a guest who is simply following behind and happens to walk
   through the same quad the host used could ALSO trigger it independently and ALSO end up
   separated if the two firings don't line up frame-for-frame (a race, not a guarantee of
   togetherness) — worth flagging even though it is a variant of cases 1-3, not a new mechanism.

### 2.3 Confirmed: follow-warp keys only on field-ID change, never on same-field separation

`FollowHostTick` (`Assembly-CSharp\Memoria\Netsync\NetSyncClient.cs:1073-1118`) is the entire
recovery mechanism today, and its very first branch (`:1082-1088`) is:

```csharp
if (rs.Field == myField)
{
    _followCandidate = -1;
    _followWarpedTo = -1;      // arrived; a future move re-arms the follow
    SameFieldKickTick(myField, onField);   // s42: co-located at link-up still needs ONE load boundary
    return;
}
```

There is no branch anywhere in this function (or anywhere else in `NetSyncClient.cs` — confirmed by
reading the full `FollowHostTick`/`ServiceFollowWarp`/`SameFieldKickTick` block, lines 1069-1179)
that compares `rs.Pos` against the local player's position while `rs.Field == myField`. The ENTIRE
follow-warp path is gated on `rs.Field != myField` (`:1082`, `:1089-1090` "already warped for this
destination", `:1097` the `FollowStableMs` debounce). **Same-field separation is therefore
structurally invisible to this system today — confirmed from source, not inferred.**

### 2.4 The s42 same-field kick fires once, at session/pairing start, never on runtime separation

`SameFieldKickTick` (`NetSyncClient.cs:1130-1155`) is gated by `_sameFieldKickDone`
(`:1132`, a one-shot latch). Its own comment block (`:1120-1129`) states the purpose precisely:
*"a guest that pairs while ALREADY standing on the host's field never crosses a field-load boundary,
so the story mirror never arms... Fire ONE forced reload of the current field... ONE-SHOT per
session."* `_sameFieldKickDone` is set `true` at `:1142` and only ever reset to `false` at two
places, both SESSION-BOUNDARY events, not separation events:
- `:479` inside `ApplyConfigChange` (a `[Netsync]` config edit / reconnect) — "kit" comment: *"...a
  co-located guest still needs ONE load boundary."*
- `:612` inside the autoload/exit-ramp path (`NetSyncState.ExitMirrorToOwnSave()` block, `:600-618`)
  — a session teardown/re-entry, not a live-play event.

Nothing in the per-frame `Update()` loop (`:590-834`) re-arms this latch based on distance or
position. **Confirmed: the s42 kick is a pairing-time fix for the story-mirror arming gap, not a
same-field recovery mechanism — exactly as the brief states.**

---

## 3. Designing TELEPORT-TO-HOST: the same-field snap primitive

### 3.1 The opcode family, and which one NOT to use

Two opcode families move an object's absolute position; only one is safe for a multi-floor snap:

- **`POS`/`DPOS` — `0x1D`/`0xBF`, *"CreateObject"/"MoveInstantEx"*** (`EventEngine.DoEventCode.cs:
  272-384`) — parses only **X and Z**; the height argument passed to `SetActorPosition` is the
  literal constant `this.POS_COMMAND_DEFAULTY` = **`32768f`** (`EventEngine.Constructor.cs:11`,
  field decl `EventEngine.cs:37`). Because the walkmesh floor-resolver (§3.2) picks whichever
  candidate triangle's center-Y is CLOSEST to the given Y, feeding it `32768` — a sentinel far above
  any real map — always resolves to the **topmost** overlapping triangle at that XZ. **Do not use
  this opcode/pattern for a teleport-to-host: on a multi-floor field it silently picks the wrong
  (topmost) floor regardless of which floor the host is actually standing on.**
- **`POS3`/`DPOS3` — `0xA1`/`0xAD`, *"MoveInstantXZY(Ex)"*** (`:2159-2226`) — parses X, Z, **and Y**,
  and calls `this.SetActorPosition(po, destX, destZ, destY)` with the real height. This is the
  opcode the kit's ladder/platform/jump primitives already use exclusively
  (`opcodes.move_instant_xzy`/raw `0xA1` encode throughout `content/ladder.py` and
  `content/platform.py`, "kit"). **This is the correct family** — but see §3.3 for why the
  recommended implementation bypasses the opcode layer entirely.

### 3.2 Floor/triangle re-binding: already solved, automatically, if Y is honest

`EventEngine.SetActorPosition` (`EventEngine.DoEventCode.cs:3452-3477`) is the shared internal for
both opcode families. In field mode (`gMode==1`) it calls
`((Actor)po).fieldMapActorController?.SetPosition(new Vector3(po.pos[0], po.pos[1], po.pos[2]),
true, true)` (`:3459`) — i.e. it defers entirely to `FieldMapActorController.SetPosition`.

`FieldMapActorController.SetPosition(Vector3 pos, bool updateLastPos, bool needCheckTri = true)`
(`Assembly-CSharp\Global\Field\Map\Actor\FieldMapActorController.cs:32-62`):

```csharp
if ((this.charFlags & 1) == 0 || !needCheckTri)      // :36 — bypass only if the "grounded" flag is off
{ this.curPos = pos; ...; return true; }
Int32 triIdxAtPos = this.GetTriIdxAtPos(pos);          // :44 — the real work
if (triIdxAtPos != -1)
{
    WalkMeshTriangle t = this.walkMesh.tris[triIdxAtPos];
    ... barycentric-project pos onto t's plane, set curPos ...
    this.activeFloor = t.floorIdx;  this.activeTri = t.triIdx;   // :53-54 — floor/triangle REBOUND HERE
    this.lastFloor = this.activeFloor;  this.lastTri = this.activeTri;
    this.SyncPosToTransform();                          // :57 — writes actor.transform.localPosition
    return true;
}
this.SetDefaultCharPos();   // :60 — off-mesh fallback: snaps to triangle 0's center (a safety net)
return false;
```

`charFlags` defaults to `1` (`HonoAwake`, `FieldMapActorController.cs:110`), so for the ordinary
controlled player `needCheckTri` gates the whole floor-rebind path on by default — a raw position
write through this API always re-triangulates and re-binds `activeFloor`/`activeTri`, with **no
separate "re-snap" step required**.

**Multi-floor disambiguation is answered directly by `GetTriIdxAtPos`**
(`FieldMapActorController.cs:1276-1303`):

```csharp
for (each triangle whose XZ contains pos)   // Math3D.PointInsideTriangleTestXZ, :1292
{
    Single dist = Mathf.Abs(pos.y - walkMeshTriangle.originalCenter.y);   // :1294
    if (dist < resultDist) { result = i; resultDist = dist; }             // :1295-1298
}
```

This is exactly the "choose the floor nearest the host's Y" rule the brief asks for — **already
implemented**, contingent only on the caller passing the REAL Y (§3.1's warning about the
`32768f` sentinel is precisely the failure mode that breaks this). There is a companion function,
`GetTopTriIdxAtPos` (`:1305-1324`), that instead always picks the highest triangle regardless of
`pos.y` — this is the one the XZ-only opcode family effectively emulates via the sentinel, and is
the WRONG one for this feature.

### 3.3 Recommended implementation: skip the opcode layer, call `SetPosition` directly

The brief's own precedent — `RemoteState.Pos` is documented and used elsewhere in the codebase as a
**direct, ready-to-use `transform.localPosition`** in the exact frame `FieldMapActorController`
expects (class doc, `NetSyncClient.cs:49`: *"we drive `transform.localPosition` ourselves"*;
`RemoteState.Pos` doc, `NetSyncSocket.cs:23`: *"the peer player's `transform.localPosition` (same
field frame -> 1:1)"*; and `DriveGhost`'s own direct assignment, `NetSyncClient.cs:1465`:
`t.localPosition = targetPos;`). This means a teleport-to-host implementation does **not** need to
go through the `.eb` opcode/bytecode-arg-order machinery at all (which has a confusing param-name
vs. positional-order mismatch between the decompiled `SetActorPosition(x,y,z)` signature and its
`(destX, destZ, destY)` call sites — not worth re-deriving when a cleaner path exists). The clean,
minimal-risk C# primitive:

```csharp
PosObj po = PersistenSingleton<EventEngine>.Instance.GetControlChar();   // EventEngine.cs:422-428
Actor me = po as Actor;
if (me?.fieldMapActorController != null)
    me.fieldMapActorController.SetPosition(rs.Pos, true, true);          // public API, FieldMapActorController.cs:32
```

- `GetControlChar()` (`EventEngine.cs:422-428`) is the same accessor `NetSyncClient` already calls
  every frame (`NetSyncClient.cs:677,740`) to find the locally-controlled actor — no new lookup
  machinery needed.
- `rs.Pos` is already sitting in `NetSyncClient.Update()`'s `rs.Field == fld` branch
  (`NetSyncClient.cs:769-791`, where the ghost is currently driven) — the SAME frame this branch
  already confirms "peer is valid and on my field," which is exactly the guard a same-field snap
  needs (§4.4).
- `SetPosition` is `public` (`FieldMapActorController.cs:32`), so this compiles from `NetSyncClient`
  with no new engine surface area — it is literally the same call `EventEngine.SetActorPosition`
  makes internally (`:3459`), just invoked one layer up, in the caller's own known-good `Vector3`
  frame, sidestepping the bytecode arg-order translation entirely.
- Off-mesh safety net is already built in (`SetDefaultCharPos` fallback, `:60-61`) — should never
  trigger under the brief's own stated assumption (the host's position is walkmesh-valid host-side
  and both machines run the identical field data), but costs nothing extra to have.

### 3.4 Camera/scroll behavior after the snap — automatic, but an EASE not an instant cut

Per the sibling camera study (`studies/field-coop/camera.md:85-111`, "kit"), the per-frame pipeline
(`FieldMap.HonoLateUpdate`, `FieldMap.cs:291-299`) re-reads `playerController.curPos` — which
`SyncPosToTransform` (`FieldMapActorController.cs:93-97`) has already updated synchronously inside
the same `SetPosition` call — every single frame, with **no dependency on how the position changed**
(walked vs. scripted vs. this new C# call). So no explicit "refresh the camera" step is needed. BUT:
`CenterCameraOnPlayer`'s `SmoothCamPercent` ease (default 85, `Memoria.ini` default,
`FieldMap.cs:734-751`) applies unconditionally to any discontinuity in the upstream scroll target
UNLESS `SmoothCamDelay` was just reset by an explicit camera-INDEX switch (`FieldMap.cs:412,457`) —
which a plain position teleport does NOT trigger. **Practical read: a same-field snap will produce a
smooth ~quarter-second "swoop" toward the host's position (governed by the player's own
`CameraStabilizer` INI setting), not a jarring instant cut** — arguably a pleasant "teleport"
sensation for free, not a bug to fix. If a hard instant cut is preferred instead, pair the snap with
the existing `FollowFadeFrames`/`FF9Wipe_FadeOutEx` fade primitive already used for the cross-field
warp (§3.5) — cheap, proven, and consistent with the rest of the feature's visual language.

**Multi-camera zone crossing:** per `camera.md:178-197` ("kit"), camera-zone switches (`SETCAM`,
`0x7E`) are themselves ordinary `cid==3` region triggers, scanned by the SAME `TreadQuad` mechanism
described in §1.1 — driven off the caller's OWN `po`, re-evaluated every frame regardless of how
that `po` got to its current position. Since the teleport moves the GUEST's own real `po` (not a
ghost, which per `camera.md:181-184` is never inserted into `activeObj` and therefore cannot
trigger regions), a snap that lands the guest inside a different camera zone than they started in
should self-correct on the very next frame's tread scan — the same way walking into that zone would.
This is a direct, reasoned inference from the confirmed region mechanism (§1.1) plus the sibling
study's confirmed camera-zone-is-a-region finding; it has not been separately verified in-game and
is flagged here as the one open item worth a specific playtest ("teleport across a multi-camera
field's zone boundary — does the destination camera activate?").

### 3.5 The cross-field case: re-fire the existing follow-warp, not a new mechanism

When `rs.Field != fld` (host is on a different field entirely), no new primitive is needed — the
hotkey should simply invoke the SAME deferred-fade path `FollowHostTick`/`ServiceFollowWarp` already
implement (`NetSyncClient.cs:1073-1179`): `SetUserControl(false)` →
`SceneDirector.FF9Wipe_FadeOutEx(FollowFadeFrames)` → after `FollowFadeWait` (`0.9f`) →
`SetNextMap(rs.Field)` + `FF9Field.loc.map.nextMode = 1`. Concretely, the hotkey handler can just
reset `_followWarpedTo = -1` (so `FollowHostTick`'s `:1089-1090` "already warped" guard doesn't
block a re-fire) and let the existing per-frame `FollowHostTick` call pick it up on the very next
tick — no duplicated fade/warp logic. This also means the SAME hotkey naturally does the right thing
in both cases (same-field snap vs. cross-field warp) without the player needing to know which one
applies; the handler just branches on `rs.Field == fld` at the moment it's pressed.

---

## 4. Input mapping

### 4.1 What's already claimed in FIELD context (`UIManager.UIState.FieldHUD`)

**Keyboard — Memoria's own remappable bindings** (`Configuration.Control.KeyBindings[]`, parsed by
`HonoInputManager.InitKeyBindings`, `Assembly-CSharp\Global\Hono\HonoInputManager.cs:112-158`):

| Index | Role | Default `KeyCode` |
|---|---|---|
| 0-3 | Movement (Up/Down/Left/Right — actual order set by `Configuration.Control.KeyBindings[0..3]`) | `W`,`A`,`S`,`D` |
| 4 | Pause | `Backspace` |
| 5 | Help/Select | `Alpha1` — the exact key the brief flags as a real collision-bug history |

**Keyboard — the ten `Control` enum actions** (`defaultInputKeys`, `HonoInputManager.cs:25-37`):
`X`(Confirm) `C`(Cancel) `V`(Menu) `B`(Special) `G`(LeftBumper) `H`(RightBumper) `F`(LeftTrigger)
`J`(RightTrigger) + `Backspace`(Pause) + `Alpha1`(Select) — indices 8/9 literally alias
`MemoriaKeyBindings[4]`/`[5]` above.

**Function-key boosters/cheats** (`UIKeyTrigger.HandleBoosterButton`, `UIKeyTrigger.cs:216-339`,
gated on `Configuration.Cheats.Enabled`): `F1` SpeedMode, `F2` BattleAssistance, `F3` Attack9999,
`F4` NoRandomEncounter, `F5` MasterSkill, `F6` LvMax (**superseded** — see next paragraph), `F7`
GilMax, `F8` SoftReset (if `Configuration.Control.SoftReset` + paused, or the PSX 6-button chord
`L1+R1+L2+R2+Start+Select`, `:55-61`), `F9` TurboDialog (`:377`).

**`F6`/`F10` — ff9mapkit dev hotkeys, already intercept BEFORE the boosters above**
(`UIKeyTrigger.cs:158-180`, s21/s22 patches): `F6` toggles the `Ff9mkDebugMenu` (Go/Cheats/Flags/
Time/Warp) in FieldHUD, BattleHUD, or WorldHUD — this early `return` (`:173`) means the stock `F6`
LvMax booster (`:301-311`) is **dead code today** (unreachable in any state this intercept covers).
`F10` (only in the s21 patch text, `s21-dev-hotkeys-f6-f10.patch:9-41`) resets `gEventGlobal` +
reloads. Both already fully claimed by this project's own tooling.

**Alt-chords** (`UIKeyTrigger.cs:719-772`): `Alt+F1` config, `Alt+F2` party scene command, `Alt+F4`
quit, `Alt+F5` save, `Alt+F9` load, `Alt+Space` widescreen toggle, `Alt+Shift+Ctrl+S` sound debug
room, `Alt+Shift+Ctrl+M` Memoria menu, `Alt+Shift+Ctrl+F12` `GameObjectService.Start()`. Also
`Shift+F4` (+`Ctrl`) friendly-battle-only / rapid-encounter toggles (`:774-793`).

**Battle-only digits** (`NetSyncBattle.SwallowAssistKey`, `Assembly-CSharp\Memoria\Netsync\
NetSyncBattle.cs:241-251`, reading `Alpha0..9`/`Keypad0..9` via `ReadDigit`, `:1378-…`) — gated on
`AssistInputActive`, itself only ever `true` while the co-op assist menu is open in battle
(`:393,438,494`). **Not a field-context claim** — irrelevant to a field hotkey design, but
architecturally the exact pattern to copy (§4.3).

**Not found bound anywhere in `Assembly-CSharp` for FIELD gameplay:** `F11` (only appears in generic
keycode-name lookup tables used by the rebind UI — `FF9UIDataTool.cs:1406`, `NGUITools.cs:1571,
1780` — never read by an `Update()`/`HonoUpdate()` for an actual game action). **`F11` is the
cleanest unclaimed keyboard key**, and fits the project's own existing `F6`→`F10` dev-hotkey
numbering without colliding with either.

### 4.2 Controller mapping

Memoria maps controller input through **Unity's own generic joystick strings** (`Input.GetButton
("JoystickButtonN")`/`GetAxis`), not a vendor SDK — no `OuyaInput` references exist in this
codebase; the wrapper is `UnityXInput.Input` (thin pass-through, used identically to
`UnityEngine.Input` throughout). Default non-Android/iOS mapping
(`defaultJoystickInputKeys`, `HonoInputManager.cs:38-50`):

```
JoystickButton0 Confirm(Cross)   JoystickButton1 Cancel(Circle)
JoystickButton2 Special(Square)  JoystickButton3 Menu(Triangle)
JoystickButton4 LeftBumper       JoystickButton5 RightBumper
JoystickButton6 Select           JoystickButton7 Pause(Start)
"LeftTrigger"/"RightTrigger"     (analog axis strings, not digital buttons)
```

**`JoystickButton8`/`JoystickButton9` (L3/R3 — left/right analog-stick click) are UNBOUND for the
default (non-iOS) profile** — confirmed by grepping every `JoystickButton8`/`9` reference in
`Assembly-CSharp`: they appear only in the iOS-specific array (`HonoInputManager.cs:70-71`, a
DIFFERENT platform profile) and in generic UI keycode-name tables (`FF9UIDataTool.cs:867-868`,
`ConfigUI.cs:140-141`, `NGUITools.cs:1629-1631,1806-1807` — all just icon/label lookups, never
functional bindings). On the shipping (non-iOS) profile, L3/R3 do nothing in field context today.

### 4.3 Recommendation: `F11` (keyboard), hold L3 ~0.6-1s (controller)

- **Keyboard: `F11`, plain tap.** Fully unclaimed (§4.1); no hold needed since nothing else can fire
  from it.
- **Controller: hold `JoystickButton8` (L3 click) for ~0.6-1s.** Unclaimed outright (§4.2), so a
  plain tap would already be safe — the HOLD is recommended anyway as a debounce against accidental
  activation from a thumb resting on/bumping the stick during normal movement (a stick click is
  physically easy to trigger unintentionally while walking), not to avoid a binding collision. This
  mirrors the engine's own precedent for a deliberate multi-frame/held gesture:
  `SoftResetKeyPSXDown`'s 6-button PSX chord (`UIKeyTrigger.cs:55-61`) — held-chord gestures for
  "significant" actions are an established idiom in this codebase, not a novel pattern.

### 4.4 Where the intercept must live, and its guard

Follow the exact `SwallowAssistKey` pattern already shipping (`UIKeyTrigger.cs:175-180`):

```csharp
// existing, s37:
if (Memoria.Netsync.NetSyncBattle.SwallowAssistKey())
    return;
HandleBoosterButton();
```

The intercept for teleport-to-host belongs at the **same call site**, in `UIKeyTrigger.Update()`
(`UIKeyTrigger.cs:127-188`), immediately alongside the existing `F6` debug-menu check (`:167-174`)
and `SwallowAssistKey()` (`:179-180`) — i.e. BEFORE `HandleBoosterButton()`/
`HandleDialogControlKeyPressCustomInput()`, for the same reason those two are placed there:
`Update()` runs every render frame (reliable `GetKeyDown`), and consuming the key here with an early
`return` prevents it from ALSO reaching any game handler that might otherwise see it.

**Guard — a ready-made predicate already exists and should be reused as-is:**
`NetSyncClient.IsLiveFollowedSession` (`NetSyncClient.cs:282-294`, public static) — *"True while
this machine is a LIVE FOLLOWED guest: enabled, FollowHost, role=client, transport connected AND the
peer's position lane fresh."* Combine with the existing field-state check the `F6` intercept already
uses (`UIState == FieldHUD`, `:167-170`) — battle/world-map are out of scope for this feature (the
brief's "on the field" framing) — and the current-frame `RemoteState` the `NetSyncClient.Update()`
loop already computes at `:767` (`RemoteState rs = _socket.GetRemote();`). Recommended shape:

```csharp
if (PersistenSingleton<UIManager>.Instance.State == UIManager.UIState.FieldHUD
    && Memoria.Netsync.NetSyncClient.IsLiveFollowedSession
    && teleportKeyPressed())          // F11 tap, or JoystickButton8 held >= ~0.6s
{
    Memoria.Netsync.NetSyncClient.RequestTeleportToHost();   // new method: same-field snap OR re-fire follow-warp
    return;
}
```

The actual snap/re-warp logic (§3.3, §3.5) should live inside `NetSyncClient` itself (it already
owns `_socket`, the current `RemoteState`, and the follow-warp state machine) rather than in
`UIKeyTrigger` — the key-handler's only job is detecting the press/hold and consuming it, matching
how `SwallowAssistKey()` itself is a thin `NetSyncBattle`-owned predicate called from
`UIKeyTrigger`, not logic inlined there.

---

## 5. Auto-teleport: evaluation and a combined policy recommendation

### 5.1 The mechanics of a distance/time trigger

All the data needed already exists at exactly one point in the codebase:
`NetSyncClient.Update()`'s `rs.Field == fld` branch (`NetSyncClient.cs:769-791`) — the SAME branch
that currently drives the ghost. `rs.Pos` (peer) and `local.fieldMapActor.transform.localPosition`
(`:743`, guest) are both already local variables in scope there. A distance check
(`Vector3.Distance(rs.Pos, local.fieldMapActor.transform.localPosition) > N`) sustained for `T`
seconds (an `Environment.TickCount`-baselined timer — see the TICK-BASELINE LAW already documented
at `NetSyncClient.cs:94-100` for why a raw `0`/`MinValue` baseline is unsafe across long uptimes) is
a small, local addition to a branch that already runs every frame under the exact conditions needed
(same field, peer valid).

### 5.2 Pros / cons

**Pros:**
- Zero input burden — recovers a separated guest with no player action, valuable for a less
  engine-literate co-op partner who may not know a hotkey exists or what it's for.
- Composes naturally with §3.3's snap primitive — same call, just triggered by a timer instead of a
  keypress.

**Cons:**
- **Yanks a wandering spectator.** The project's own established SPECTATOR-FIELD PARADIGM (quoted in
  `camera.md:398-400`, memory `project-ff9-multiplayer-injector.md:606-615`): *"field walking is
  purely flavorful... interaction authority is the HOST's alone."* A guest who is deliberately
  exploring off to the side (looking at scenery, standing somewhere for a screenshot, etc.) getting
  forcibly snapped back is a worse experience than the separation it "fixes," for the common case
  where separation is harmless (both players still on the same visible screen, just not adjacent).
- A poorly-tuned threshold could fire during ordinary gameplay lag/desync blips, not just genuine
  platform/ladder separation — needs the same staleness/freshness guard already used elsewhere
  (`rs.Valid`, `IsLiveFollowedSession`) to avoid firing on a transient wire hiccup.

### 5.3 Interaction with a host-following camera (the sibling `camera.md` proposal)

`camera.md`'s recommended design (option A, scroll-target substitution, `camera.md:229-273,353-369`
— **not yet implemented**, research-only same as this doc) would make the guest's OWN camera follow
the ghost's position instead of the guest's own actor while following. That study explicitly flags,
without resolving, the exact tension this section needs (`camera.md:391-402`, "On free-walk
coherence"): *"a guest who walks away from the host's ghost would find their own camera no longer
centered on them... with no local visual feedback tying camera position to their own input
anymore."*

This is a direct, strong argument that **auto-teleport becomes materially more attractive if
camera-follow-host ships**: under that design, a same-field-separated guest isn't just "somewhere
else" — they are actively CONTROLLING AN OFFSCREEN, UNSEEN CHARACTER while watching a camera glued
to the host. There is no way for that guest to even SEE where their own actor is well enough to walk
it back manually. In that world, "yanks a wandering spectator" (§5.2's main con) mostly stops
applying, because the guest was never able to meaningfully see/steer their own position in the first
place once the camera detached from them — the auto-teleport isn't overriding a choice the player
was making with visual feedback, it's recovering a state the player couldn't perceive.

### 5.4 Recommended combined policy

- **Hotkey (§4) always available**, regardless of camera-follow-host's status — the low-risk,
  player-initiated primitive, useful in every configuration.
- **Auto-teleport OFF by default under today's shipped camera behavior** (guest's own camera stays
  on the guest's own actor, per `camera.md:151-176` "Today's guest experience" — the guest has full
  visual feedback on their own position, so an unrequested snap is more likely to feel like an
  interruption than a rescue).
- **If/when camera-follow-host (camera.md option A) ships, auto-teleport should default ON** for the
  same-field-separated case specifically (not for "far apart but still both visible on the current
  camera window" — only once the guest's actor has left the ACTIVE camera's clamped viewport
  entirely, which is already a computable signal: `SceneService3DScroll`'s own clamp inputs,
  `FieldMap.cs:2000-2025`, or more simply, a distance threshold tuned to the field's window size).
  This turns the two features into a matched pair: the camera follows the host so the player can SEE
  the host, and once separation is bad enough that the player's own body would otherwise be
  invisible/unreachable, auto-teleport keeps the underlying game state (the guest's actual
  controlled actor) consistent with what the camera is already showing.
- **Threshold/cooldown, either way:** gate on the SAME freshness signals already used everywhere
  else in this stack (`rs.Valid`, `IsLiveFollowedSession`) so a wire hiccup can't fire it, and apply
  a debounce comparable to `FollowStableMs` (`NetSyncClient.cs:118`, 1200 ms) rather than an instant
  trigger, consistent with every other automatic-recovery decision this class already makes.

---

## Appendix: file:line index

| Fact | Location |
|---|---|
| `CheckNPCInput` (NPC talk path) | `EventCollision.cs:85-…` |
| `CheckQuadInput` (region/ladder/platform/chest/gateway path) | `EventCollision.cs:60-83` |
| `TreadQuad` (region quad scan, `cid==3`) | `EventEngine.TreadQuad.cs:6-22` |
| `IsQuadTalkable` / `IsNPCTalkable` (separate hardcode-exception functions) | `EventCollision.cs:442-…`, `:491-…` |
| `NetSyncVisitor.SuppressEncounters` (the precedent pattern for a suppression flag) | `Assembly-CSharp\Memoria\Netsync\NetSyncVisitor.cs:27` |
| `MoveTileLoop`/`MoveTile`/`AttachTile` = BG overlay only, never player/walkmesh | `EventEngine.DoEventCode.cs:1725-1741`, `:2045-2049` |
| `MoveInstantXZY(Ex)` / `0xA1`/`0xAD` (Y-aware move — the correct family) | `EventEngine.DoEventCode.cs:2159-2226` |
| `CreateObject`/`MoveInstantEx` / `0x1D`/`0xBF` (XZ-only, `Y=32768` sentinel — WRONG for multi-floor) | `EventEngine.DoEventCode.cs:272-384`; sentinel `EventEngine.Constructor.cs:11` |
| `EventEngine.SetActorPosition` (shared internal, calls `FieldMapActorController.SetPosition`) | `EventEngine.DoEventCode.cs:3452-3477` |
| `FieldMapActorController.SetPosition` (public API — the recommended direct call) | `FieldMapActorController.cs:32-62` |
| `GetTriIdxAtPos` (multi-floor disambiguation: nearest-Y triangle wins) | `FieldMapActorController.cs:1276-1303` |
| `GetTopTriIdxAtPos` (the WRONG one — always picks highest) | `FieldMapActorController.cs:1305-1324` |
| `GetControlChar` | `EventEngine.cs:422-428` |
| `FollowHostTick` (cross-field-only recovery, confirmed) | `NetSyncClient.cs:1073-1118`, same-field early-return `:1082-1088` |
| `SameFieldKickTick` (s42, one-shot at pairing, not separation) | `NetSyncClient.cs:1130-1155`; latch resets `:479`, `:612` |
| `ServiceFollowWarp` (the deferred-fade F6-style warp) | `NetSyncClient.cs:1158-1179` |
| `NetSyncClient.IsLiveFollowedSession` (ready-made hotkey/auto-teleport guard) | `NetSyncClient.cs:282-294` |
| `RemoteState` struct (`Pos` = direct usable `transform.localPosition`) | `NetSyncSocket.cs:13-25` |
| `UIKeyTrigger.Update` intercept precedent (`F6` debug menu, `SwallowAssistKey`) | `UIKeyTrigger.cs:127-188`, `:158-180` |
| `MemoriaKeyBindings` (movement/pause/help defaults) | `HonoInputManager.cs:111-158` |
| `defaultInputKeys`/`defaultJoystickInputKeys` (the 10-action keyboard+controller map) | `HonoInputManager.cs:25-50` |
| `HandleBoosterButton` (F1-F9 cheats, gated `Configuration.Cheats.Enabled`) | `UIKeyTrigger.cs:216-339` |
| `F6`/`F10` dev-hotkey intercepts (already claim those keys) | `UIKeyTrigger.cs:158-180`; `s21-dev-hotkeys-f6-f10.patch:9-41` |
| Alt-chords / Ctrl+Shift chords | `UIKeyTrigger.cs:719-793` |
| `NetSyncBattle.SwallowAssistKey` (the exact pattern to copy) | `NetSyncBattle.cs:241-251` |
| `JoystickButton8`/`9` unbound on default profile (iOS-only elsewhere) | `HonoInputManager.cs:38-50` (default, no 8/9) vs. `:70-71` (iOS only) |
| `SoftResetKeyPSXDown` (precedent for a deliberate held-chord gesture) | `UIKeyTrigger.cs:55-61` |
| Kit ladder region trigger (`ladder_region`) | `ff9mapkit\ff9mapkit\content\ladder.py:428-442` |
| Kit platform region trigger (`platform_region`) | `ff9mapkit\ff9mapkit\content\platform.py:201-220` |
| Camera per-frame pipeline / ease / region-driven `SETCAM` (sibling study) | `studies/field-coop/camera.md:1-419` (full doc; §1.1, §1.4, §2.2, §4 cited above) |
