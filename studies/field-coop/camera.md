# Guest camera: follow the host? — decidability study

**Status:** research only, nothing implemented. Read-only pass over `C:\gd\FFIX\Memoria\` (live
engine tree, source of truth) + the `s36-netsync-ghost.patch` co-op sidecar + the multiplayer
project memory. All cites are `file:line` against that tree unless marked otherwise.

---

## 1. How the field camera decides what to look at, per frame

### 1.1 The per-frame pipeline

`FieldMap.HonoLateUpdate` (`FieldMap.cs:291-299`) runs, in order, every frame:

```
SceneService2DScroll()   // FieldMap.cs:~1820-1880 — SCRIPTED pan (BGSSCROLL/BGSRELEASE), NOT player-driven
SceneService3DScroll()   // FieldMap.cs:1959-2031  — the FOLLOW-THE-PLAYER scroll target + clamp
CenterCameraOnPlayer()   // FieldMap.cs:633-759    — turns the scroll state into an actual camera move + eases it
SceneServiceScroll(...)  // background-layer parallax bookkeeping
UpdateOverlayAll()
```

### 1.2 The scroll-target read

`SceneService3DScroll` (`FieldMap.cs:1959-2031`) is the function that answers "what do we look
at": it reads **`this.playerController.curPos`** — a single `FieldMapActorController` reference
held on the `FieldMap` instance:

```csharp
// FieldMap.cs:1987-1997
if (this.playerController != null)
{
    prevScrOffset = this.playerController.curPos;
    prevScrOffset.y += this.charAimHeight;
    prevScrOffset = PSX.CalculateGTE_RTPT(prevScrOffset, Matrix4x4.identity,
        bgCamera.GetMatrixRT(), bgCamera.GetViewDistance(), this.offset);
}
else
{
    prevScrOffset.x += this.offset.x + this.extraOffset.x;
    prevScrOffset.y += this.offset.y + this.extraOffset.y;
}
```

`this.playerController` is **not** "whichever actor is netcode-controlled" — it's just whichever
`FieldMapActorController` was last flagged `isPlayer=true`, assigned at exactly three call sites,
all local-only: `SetPlayer` (`FieldMap.cs:508`), `AddFieldChar` when `isPlayer` (`FieldMap.cs:589`),
and `updatePlayer` (`FieldMap.cs:630`, used by `--swap-player`/PC-swap features). **No netsync
patch (s36–s41) ever assigns it** (confirmed: `grep playerController\s*= across memoria-patches/*.patch`
— the only hits are the pre-existing fork-fidelity crutches at `FieldMap.cs:1968`/`1977`, unrelated
to co-op). So on the guest's own client, `playerController` is always the guest's own controlled
character, never the ghost.

`curPos` is exactly `transform.localPosition` in the field's local frame — `SetPosition` /
`SyncPosToTransform` write `actor.transform.localPosition = this.curPos` directly
(`FieldMapActorController.cs:93-97`; the two are the same number, not just "close").
`this.charAimHeight` (`FieldMap.cs:2151`, default 324, `FieldMap.cs:91,811`) is a FieldMap-level
constant added to `.y` before the GTE projection — script-overridable via the `BGCHEIGHT` opcode
(`FieldMap.cs:2151` is the field; write site `EventEngine.DoEventCode.cs:1880-1884`). It is **not**
actor-specific, so whatever `Vector3` feeds this pipeline gets the same treatment.

### 1.3 The clamp (scroll bounds / camera windows)

Still inside `SceneService3DScroll` (`FieldMap.cs:2000-2025`): the projected target `(aimX, aimY)`
is clamped against the **active camera's own window**, `BGCAM_DEF.vrpMinX/vrpMaxX/vrpMinY/vrpMaxY`
(`BGCAM_DEF.cs:157-176`, read straight from the `.bgx`/scene data per camera):

```csharp
// FieldMap.cs:2008-2025
if (aimX < bgCamera.vrpMinX) prevScrX = ...vrpMinX;
else if (aimX > bgCamera.vrpMaxX) prevScrX = ...vrpMaxX;
if (aimY < bgCamera.vrpMinY) prevScrY = ...vrpMinY;
else if (aimY > bgCamera.vrpMaxY) prevScrY = ...vrpMaxY;
...
this.curVRP.x = Mathf.Clamp(aimX, bgCamera.vrpMinX, bgCamera.vrpMaxX) - bgCamera.centerOffset[0] - HalfFieldWidth;
this.curVRP.y = Mathf.Clamp(aimY, bgCamera.vrpMinY, bgCamera.vrpMaxY) + bgCamera.centerOffset[1] - HalfFieldHeight;
```

This is an **unconditional `Mathf.Clamp`** — there is no branch that can throw, wrap, or leave the
viewport in an invalid state if the input position is far outside the window. A scroll target
arbitrarily outside the bounds is *safe by construction*: the camera simply pins to whichever edge
is nearest and stops moving further, exactly as it already does for the normal player (walking to
the edge of a scrolling room today).

`CenterCameraOnPlayer` (`FieldMap.cs:633-759`) then converts `this.charOffset`
(derived from `curVRP`, set at `FieldMap.cs:2018-2019`) into an actual `CamPositionX/Y`, applies a
battery of per-map widescreen-margin hacks (`FieldMap.cs:649-720`, all keyed on hardcoded `map`
ids — irrelevant to co-op), then **eases** it:

```csharp
// FieldMap.cs:734-751 — the CameraStabilizer ease
if (SmoothCamActive)
{
    if (SmoothCamDelay <= 0)
    {
        SmoothCamDelta.x = (Prev_CamPositionX - CamPositionX) * SmoothCamPercent;
        CamPositionX += SmoothCamDelta.x;
        ...
    }
    else SmoothCamDelay--;
}
```

`SmoothCamPercent` (`FieldMap.cs:2424`) = `Configuration.Graphics.CameraStabilizer / 100`, an INI
setting, **default 85** (`Memoria.ini:63`, comment at `Memoria.ini:40`: *"stickiness of camera to
its original position, each frame"*). This is a per-frame exponential ease toward whatever
`CamPositionX/Y` was just computed — it runs on **every** frame the game is active, not only after
camera cuts, so it will smooth *any* discontinuity in the upstream target, including one this study
proposes to introduce (see §4). `SmoothCamDelay` is set to 4 (`FieldMap.cs:412`) or 6
(`FieldMap.cs:457`) specifically on a camera-index switch — for those few frames the ease is
*skipped*, i.e. multi-camera switches are intentional hard **cuts**, not pans (see §1.4).

### 1.4 What `SETCAM` changes, and the per-frame "camera N is active" state

Opcode `0x7E` (`SETCAM`/`SetFieldCamera`) is handled at
`EventEngine.DoEventCode.cs:1950-1969`, reading one arg and calling
`this.fieldmap.SetCurrentCameraIndex(newCamIdx)` (`FieldMap.cs:383-417`, line 1960 is the call
site). `SetCurrentCameraIndex` is a no-op if the index is unchanged (`FieldMap.cs:385-386`);
otherwise it sets `this.camIdx` (the *requested* index, `FieldMap.cs:2117`), calls
`ActivateCamera()`, and re-derives `this.offset` / global shader uniforms
(`_MatrixRT`/`_ViewDistance`/`_OffsetX`/`_OffsetY`) from the new `BGCAM_DEF`.

`ActivateCamera()` (`FieldMap.cs:463-478`) is where the actual "camera N is active" state lives:
`this.curCamIdx` (`FieldMap.cs:2149`) is set equal to `this.camIdx` when they differ, and every
`BGCAM_DEF` GameObject in `scene.cameraList` is `SetActive(i == this.camIdx)`
(`FieldMap.cs:472-477`). `SceneService3DScroll`'s early-out at `FieldMap.cs:1963`
(`this.curCamIdx < 0 || this.curCamIdx > this.scene.cameraList.Count`) and every
`scene.cameraList[this.curCamIdx]` read elsewhere (walkmesh, overlays, animations — see the full
grep list) key off this same field. **Both `camIdx` and `curCamIdx` are plain instance fields on
the single per-client `FieldMap` MonoBehaviour** — there is one `FieldMap` per game process, so
there is one active-camera index per *machine*, not per session.

Distinct opcodes exist for the two other camera behaviors named in the brief:
- `BGSSCROLL` 0x6F *"MoveCamera"* (`EventEngine.DoEventCode.cs:1854-1864`) — a **scripted pan**
  to `(destX,destY)` over `duration` frames, handled by `SceneService2DScroll`
  (`FieldMap.cs:~1820-1880`, runs *before* `SceneService3DScroll` each frame, `FieldMap.cs:293-294`)
  — this is FF9's cutscene camera-pan primitive, independent of any actor position.
- `BGSRELEASE` 0x70 *"ReleaseCamera"* (`EventEngine.DoEventCode.cs:1865-1871`) returns control to
  the normal follow behavior.
- `BGCACTIVE` 0x71 *"EnableCameraServices"* (`EventEngine.DoEventCode.cs:1872-1879`) toggles
  `this.IsActive`, the flag `SceneService3DScroll` checks at its very first line
  (`FieldMap.cs:1963`) — **this is the master on/off switch for player-follow scrolling**, distinct
  from which camera index is active.

All four of these (`SETCAM`, `BGSSCROLL`, `BGSRELEASE`, `BGCACTIVE`) are ordinary `.eb` opcodes,
executed synchronously inside `EventEngine.DoEventCode` on whichever machine's script instance
reaches that instruction. Nothing about them is broadcast.

---

## 2. Today's guest experience, established precisely

### 2.1 Host walks beyond the guest's camera window, guest stands still

Confirmed nothing re-centers on the ghost. Chain of evidence:

- The ghost is a bare `GameObject` with **no `FieldMapActorController`, no `Obj`/`Actor` slot, no
  uid** (`s36-netsync-ghost.patch:55-57` design comment; `EnsureGhost`,
  `s36-netsync-ghost.patch:473-548`, never touches `sObjTable`/`activeObj`).
- `this.playerController` is set exactly three times, all pointing at a *real*
  `FieldMapActorController`-bearing actor (`FieldMap.cs:508,589,630`); no co-op patch (s36–s41)
  ever reassigns it (verified by grep across every `memoria-patches/*.patch`).
- Therefore `SceneService3DScroll`'s scroll target on the guest's client is **always the guest's
  own `playerController.curPos`** (`FieldMap.cs:1987-1991`) — the ghost's position never enters the
  scroll-target computation at all, on either machine.
- The ghost is driven purely cosmetically: `DriveGhost` (`s36-netsync-ghost.patch:634-664`)
  lerps `_ghost.transform.localPosition` toward the wire's `RemoteState.Pos` at a fixed
  `LerpRate = 12` (`s36-netsync-ghost.patch:86`), completely decoupled from `curVRP`/`charOffset`/
  `CamPositionX/Y`.

Result: if the host walks past the edge of the guest's current camera window while the guest is
idle, the guest's camera **does not move** (clamped at the window edge per §1.3, since the guest's
own position hasn't changed) and the ghost visually walks off-window/off-screen on the guest's
client. Nothing breaks — the ghost is a huge-localBounds unculled renderer
(`s36-netsync-ghost.patch:519-523`), so it just silently renders wherever its lerped position maps
to, potentially off the painted background entirely.

### 2.2 Multi-camera field: guest and host can hold different active cameras simultaneously

Confirmed. Camera-zone switches are ordinary tag-2/3 **region triggers** — scanned by
`EventEngine.TreadQuad` (`EventEngine.TreadQuad.cs:6-22`), which walks `this._context.activeObj`
(a linked list of registered `Obj`s on *that machine's* `EventEngine`) and tests each region quad
against `po.go.transform.position` — `po` being the caller's own controlled `PosObj`. The ghost is
never inserted into `activeObj` (§2.1), so **it cannot trigger a region on the machine that renders
it** — only a real local `Obj` can. Since the guest and host each run their own independent
`EventEngine`/`FieldMap` instance with only position+anim+field state crossing the wire (§2.3), a
camera-zone `SETCAM` fired by the host's movement only calls `SetCurrentCameraIndex` on the host's
`FieldMap.camIdx`; it has zero effect on the guest's `FieldMap.camIdx`. The guest's own camera
index changes only when the *guest's own* controlled character crosses that field's region quads.
On a field with N cameras, host and guest can therefore legitimately sit on different `camIdx`
values at the same moment — confirmed by the region-trigger mechanics, not just inferred.

This matches the multiplayer memory's established law for cutscenes generally
(`project-ff9-multiplayer-injector.md:696-700`): *"the guest's cutscenes fire from the GUEST's own
position — both machines run the same script off mirrored flags but the TRIGGER is local, so they
are two independent scripts that happen to agree, not two views of one cutscene."* Camera zones are
the same mechanism (a region body calling `SETCAM`), so the same law applies verbatim.

### 2.3 During a host cutscene, the guest's camera does what?

Nothing — it is unaffected. The wire (`NetSyncSocket.cs:13-24`, `RemoteState`) carries exactly
`Field`, `Anim`, `MeshVis`, `Loco`, `Pos`, `Rot`, `Valid` — **no camera state of any kind**
(confirmed by grepping `camera|Camera|CamIdx` across `NetSyncClient.cs`, `NetSyncVisitor.cs`,
`NetSyncSocket.cs`: zero hits outside unrelated comments/culling-layer code). `BGSSCROLL`/
`BGCACTIVE`/`SETCAM`/`BGCHEIGHT` calls made by a host-side cutscene script execute inside the
*host's* `EventEngine.DoEventCode`, mutating the *host's* `FieldMap` instance fields
(`camIdx`, `IsActive`, `charAimHeight`, the 2D-scroll `startPoint`/`aimX`/`aimY` pan state) — none
of that is serialized or observable by the guest. Two sub-cases:

- **The guest has not independently triggered the same cutscene** (different story-flag state, or
  the cutscene is gated on a one-shot flag the guest's own save already cleared, etc.): the guest's
  camera keeps doing its normal 3D-scroll follow on the guest's own actor, unaffected. Only the
  ghost's position/animation updates (per the wire's pos lane, 30 Hz), so the host's character may
  appear to teleport/pan/walk in ways that look like a "movie" happening inside the guest's own
  static or independently-scrolling view — camera-wise indistinguishable from any other moment.
- **The guest's own mirrored script independently reaches the same trigger** (the established
  co-op pattern per `project-ff9-multiplayer-injector.md:683,697-699`): the guest's *own* local
  cutscene fires, with its *own* local `SETCAM`/`BGSSCROLL` calls, tracking the guest's own actor —
  which is not guaranteed to be frame-synchronized with the host's copy of the same cutscene (two
  independent script instances, no lockstep).

Either way: **there is no path today by which a host-side camera command reaches the guest's
camera.** This is the literal gap the brief calls "uncharted."

---

## 3. Evaluating the options

### (A) Scroll-target substitution

**Mechanism.** Feed the ghost's position into `SceneService3DScroll`'s target instead of
`this.playerController.curPos`, guest-side only, while following + ghost-visible + same-field.

**Exact substitution point:** `FieldMap.cs:1987-1991`. Today:
```csharp
if (this.playerController != null) { prevScrOffset = this.playerController.curPos; ... }
```
would become (conceptually — nothing implemented): swap in a `Vector3` sourced from the ghost
instead of `playerController.curPos`. **Confirmed this needs nothing else:** the GTE call on the
next line (`PSX.CalculateGTE_RTPT(prevScrOffset, Matrix4x4.identity, bgCamera.GetMatrixRT(), ...)`,
`FieldMap.cs:1991`) takes a bare `Vector3` — it doesn't touch `FieldMapActorController` or `Actor`
at all beyond reading `.curPos`. The ghost already has the right value at the right scale/frame:
`RemoteState.Pos` is documented "the peer player's `transform.localPosition` (same field frame ->
1:1)" (`NetSyncSocket.cs:23`), the ghost is parented `g.transform.parent = ee.fieldmap.transform`
(`s36-netsync-ghost.patch:501` — "share the field's local frame"), and it's lerped there every
frame (`DriveGhost`, `s36-netsync-ghost.patch:634-649`). Since `FieldMapActorController.curPos` is
itself just `transform.localPosition` in the same parent space
(`FieldMapActorController.cs:93-97`), `_ghost.transform.localPosition` is numerically the exact
same kind of value `playerController.curPos` already is — a straight `Vector3` swap, no coordinate
conversion needed. `charAimHeight` (§1.2) applies identically to either source since it's a flat
FieldMap-level offset, not actor-specific.

**Fallback:** trivial — `if (following && ghostVisible && ghostOnSameField) use ghost.pos else use
playerController.curPos`, decided fresh every frame at the substitution point; no state machine
needed beyond what already tracks ghost presence (`_ghost != null`, already the existing spawn/
despawn gate, `s36-netsync-ghost.patch:279-370`).

**Effort:** small. One conditional read at one call site, guest-side only, **zero wire changes**
(everything needed — the ghost's live position — already crosses the wire at 30 Hz today).

**Risk — cutscene interaction.** Because `SETCAM`/`BGSSCROLL`/`BGCACTIVE` are unaffected by this
(they still run purely off the *guest's own* locally-triggered script, §2.3), a scroll-target swap
does **not** create any new interaction with the guest's own mirrored cutscene camera — that camera
logic is orthogonal to what `SceneService3DScroll` targets each frame; `SceneService2DScroll` runs
*before* `SceneService3DScroll` in `HonoLateUpdate` (`FieldMap.cs:293-294`) and, per `BGCACTIVE`
(`FieldMap.cs:1963` gate), can **suspend** 3D-scroll entirely while active. So: if the guest's own
mirrored script starts a scripted pan (`BGSSCROLL`) or disables 3D-scroll (`BGCACTIVE 0`), the
substitution is silently overridden/suspended exactly as it would be for the guest's own actor
today — no special-casing required, this composes for free. The one genuine risk: if the *ghost*
walks (via host movement) while the *guest* is independently mid-cutscene with 3D-scroll re-enabled
partway through, the camera would whip toward wherever the ghost now is — a coherence question, not
a crash risk (see failure modes below).

**Failure modes.** "Host offscreen beyond this field's scroll bounds" is **not** possible to break
anything — confirmed at §1.3, the clamp is an unconditional `Mathf.Clamp` with no failure path; an
out-of-window target simply pins the view to the nearest edge, identical to what already happens
when the *guest's own* actor is deep in a corner of an oversized field today. The only real failure
mode is **staleness**: if the peer link drops mid-follow, the ghost's `s36-netsync-ghost.patch:634-664`
`DriveGhost` keeps lerping toward its *last known* `RemoteState.Pos` forever (nothing currently ages
it out) — a substitution reading that position would freeze the camera on a stale point rather than
resuming the guest's own follow, unless the fallback condition explicitly checks link/staleness
(the existing `rs.Valid`/`socket.IsConnected` freshness signals used elsewhere,
e.g. `NetSyncClient.cs:768-772`, are exactly what §4's fallback should key on).

### (B) Camera-state mirror

**Mechanism.** Host broadcasts its `camIdx` (the active BGCAM index) and a scroll offset/`curVRP`
each frame; guest applies them directly instead of computing its own.

**Effort:** larger. Needs a **wire version bump** (current `Version = 10`,
`NetSyncSocket.cs:87`, and per the brief's stated fail-safe convention this rejects older peers —
consistent with every prior bump in this stack) to add a new field to the pos-lane frame (a byte for
`camIdx` + 2×Int16 for a `curVRP`-equivalent would suffice bandwidth-wise; the frame is already sent
30×/s).

**Risk.** This throws away the guest's *own* locally-simulated camera state (§2.2's independent
per-machine `camIdx`) and forces the guest to literally render through the host's camera slot,
including the host's own `BGSSCROLL`/`BGCACTIVE` cutscene pans if those are also mirrored (they are
not, today — mirroring only `camIdx` + offset would leave the guest's screen *cutting* to the host's
camera index but *not* replaying the host's scripted pans, an inconsistent middle state: the guest
would see the right camera framing but static/wrong scroll position during a host pan). Fully
correct mirroring would mean mirroring `BGSSCROLL`'s destX/destY/duration too — scope creep beyond
"a few bytes."

**Failure modes.** If host and guest have *diverged* story/scenario state (a realistic condition per
this project's established narrative-state gap — `ff9mapkit/docs/FORK_FIDELITY.md`, the north-star
gap), the host's `camIdx` may not even be a valid index into the guest's own `scene.cameraList` if
the two machines somehow loaded different field variants — `ActivateCamera`'s own guard
(`FieldMap.cs:467-470`, `if (this.camIdx >= this.scene.cameraList.Count) { this.camIdx =
this.curCamIdx; return; }`) protects against a literal out-of-range index, but a mirrored index that
happens to be in-range yet means a *different* physical camera on the guest's copy of the field
would silently mis-frame the guest's own screen — a subtler, harder-to-detect failure than (A)'s
"pins to an edge."

### (C) Hybrid — local ghost-position target + mirror only the camera-index

**Mechanism.** (A)'s local substitution (no wire change) for the *pan/scroll* target, plus mirror
just the host's `camIdx` (one byte) so multi-camera fields agree on *which* camera, not where within
it.

**Effort:** small-to-medium — (A)'s zero-wire-change substitution, plus a minimal wire bump (one
byte) purely for `camIdx`. Still needs the version bump (any wire change does, per the stated
convention), but the payload is trivial compared to (B).

**Risk.** Better-composed than (B) alone: applying the mirrored `camIdx` via the existing
`SetCurrentCameraIndex` call (`FieldMap.cs:383`) on the guest gets the *entire* existing machinery
for free — the shader-uniform re-derivation, `walkMesh.UpdateActiveCameraWalkmesh()`, the
`SmoothCamDelay=4` hard-cut behavior (§1.4) that makes camera *switches* feel like real FF9 cuts
rather than pans. Still inherits (A)'s cutscene-composition profile (§3.A risk) for the scroll part.
One new risk specific to the hybrid: **fighting inputs** — if the guest's *own* region trigger also
fires a `SETCAM` at a moment the mirrored index disagrees, the two writes to `this.camIdx` race
(last-write-wins per frame, since both go through the same `SetCurrentCameraIndex` no-op-if-same
guard, `FieldMap.cs:385-386`) — a real but narrow edge case (only visible in fields where the
guest's own crossing and the mirrored value diverge in the same window).

**Failure modes.** Same "clamp makes it safe" guarantee as (A) for the pan target. The camera-index
mirror inherits (B)'s out-of-range guard (`FieldMap.cs:467-470`) but not (B)'s "wrong camera,
in-range index" risk as badly, since scroll-target still comes from a real position rather than a
mirrored offset — a wrong-but-in-range `camIdx` would frame from the wrong angle, but the *content*
in frame would still be geometrically sane (ghost projected through whatever camera is active),
degrading gracefully rather than desyncing pixel-for-pixel.

### (D) Do nothing

This **is** the current shipped behavior, confirmed exhaustively in §2: zero wire fields, zero
`FieldMap` call-site changes, zero risk — and zero benefit. The ghost can and does walk off-window
during ordinary two-machine play whenever the host outpaces the guest's camera window; nothing
crashes (§1.3's clamp already protects the existing single-player case this borrows from), it is
just visually unsatisfying for a "spectate the host" framing.

---

## 4. Recommendation

**Recommend (A) — local scroll-target substitution, no wire change**, with (C)'s camera-index
mirror as a deliberate, separately-scoped follow-up rather than bundled into the same change.

Reasoning: (A) is the only option that is (a) buildable with **zero protocol version bump** — it
reads data (`RemoteState.Pos`) that already crosses the wire at 30 Hz for the ghost's own rendering,
so there is no fail-safe-peer-rejection cost to ship it; (b) provably safe at the boundary
(§1.3's unconditional clamp — this was verified by reading the exact clamp code, not assumed); and
(c) composes for free with the guest's own local cutscene camera logic, because that logic
(`BGSSCROLL`/`BGCACTIVE`) already lives *above* `SceneService3DScroll` in the per-frame pipeline
(§1.1) and already overrides/suspends the follow-target on the guest's own actor today — swapping
which `Vector3` feeds that target changes nothing about how those higher-priority systems interact
with it. (C) is a legitimate second step (multi-camera fields genuinely can disagree on framing,
§2.2) but it is the one option here that *requires* the version bump and inherits real
composition risk with the guest's own independently-triggered `SETCAM` calls — worth doing once (A)
is proven, not before.

**Fallback story (link blip → smooth return, no snap):** the substitution's fallback condition
(§3.A) should key off the *same* freshness signal the rest of the stack already uses for
"is the peer actually here" (`rs.Valid`/staleness checks already present at
`NetSyncClient.cs:768-772` and the position-lane freshness law cited in the brief's "PEER-ALIVE LAW"
— transport-up is not peer-alive). When that signal goes stale, fall back to
`playerController.curPos` (the guest's own actor) at the *same* substitution point
(`FieldMap.cs:1987-1991`) — critically, this fallback needs **no special smoothing code of its
own**: §1.3's `CenterCameraOnPlayer` ease (`FieldMap.cs:734-751`, `SmoothCamPercent` from
`Configuration.Graphics.CameraStabilizer`, **default 85** — heavy stabilization,
`Memoria.ini:63`) runs unconditionally on *every* frame's computed `CamPositionX/Y`, regardless of
which `Vector3` produced it upstream — so a target swap (ghost → own actor, or vice versa) is
automatically eased over several frames rather than cut, for free, as long as the field isn't
mid-camera-switch (`SmoothCamDelay`, §1.4, which deliberately *skips* the ease for ~4-6 frames after
a `SETCAM` — a pre-existing "cut" behavior, not something this design introduces). The one caveat:
a player who has set `CameraStabilizer=0` in their own INI gets **zero** smoothing on *anything*
today (including their own single-player camera) — this substitution would inherit that same
snap-on-every-frame behavior for such a player, which is consistent with, not worse than, existing
engine behavior, but worth flagging rather than silently relying on a setting outside this
feature's control.

**On free-walk coherence (flagged, not resolved — movement is out of this study's scope):**
camera-follows-host and guest-keeps-free-walk are not contradictory, but they do interact: with (A)
alone, a guest who walks away from the host's ghost would find their own camera no longer centered
on *them* — the screen follows the ghost, the guest's own controlled character can walk toward the
clamp edge or even (per §2.1's existing mechanics) off the visible window, with no local visual
feedback tying camera position to their own input anymore. That's a legitimate design question for
whoever owns guest movement/interaction — this study's read of engine facts doesn't resolve whether
that's acceptable "pure spectator" framing (consistent with the established
`project-ff9-multiplayer-injector.md:606-615` **SPECTATOR-FIELD PARADIGM**, "field walking is purely
flavorful... interaction authority is the HOST's alone") or whether it argues for constraining/
auto-walking the guest once camera-follow-host ships. Flagging the interaction per the brief's
instruction; not making the movement-policy call here.

---

## Appendix: file:line index

| Fact | Location |
|---|---|
| Per-frame pipeline order | `FieldMap.cs:291-299` (`HonoLateUpdate`) |
| Scroll-target read (`playerController.curPos`) | `FieldMap.cs:1959-2031` (`SceneService3DScroll`), read at `1987-1991` |
| `playerController` assignment sites (all local, none netsync) | `FieldMap.cs:508`, `589`, `630` |
| `curPos` == `transform.localPosition` | `FieldMapActorController.cs:93-97` (`SyncPosToTransform`) |
| `charAimHeight` (default 324, field-level) | `FieldMap.cs:2151`; defaults `91`,`811`; script write `EventEngine.DoEventCode.cs:1880-1884` (`BGCHEIGHT`) |
| Camera-window clamp | `FieldMap.cs:2000-2025`; window fields `BGCAM_DEF.cs:157-176` |
| Camera ease (CameraStabilizer) | `FieldMap.cs:734-751`; `SmoothCamPercent` def `FieldMap.cs:2424`; INI default 85 `Memoria.ini:40,63` |
| Camera-switch hard-cut window | `SmoothCamDelay` set `FieldMap.cs:412,457`, consumed `736-747` |
| `SETCAM` opcode handler | `EventEngine.DoEventCode.cs:1950-1969` |
| `SetCurrentCameraIndex` | `FieldMap.cs:383-417` |
| `ActivateCamera` (curCamIdx = active-camera state) | `FieldMap.cs:463-478` |
| `camIdx`/`curCamIdx` field decls | `FieldMap.cs:2117`, `2149` |
| `BGSSCROLL`/`BGSRELEASE`/`BGCACTIVE` opcodes | `EventEngine.DoEventCode.cs:1854-1879` |
| Region-trigger scan (`TreadQuad`) — local-Obj-only | `EventEngine.TreadQuad.cs:6-22` |
| Ghost has no Obj/Actor/uid | `s36-netsync-ghost.patch:55-57` (design comment), `473-548` (`EnsureGhost`) |
| Ghost parented to field-local frame | `s36-netsync-ghost.patch:501` |
| Ghost position drive/lerp | `s36-netsync-ghost.patch:634-664` (`DriveGhost`) |
| Wire `RemoteState` struct (no camera fields) | `NetSyncSocket.cs:13-24` |
| Wire version (fail-safe reject-old-peer convention) | `NetSyncSocket.cs:87,107,121` (`Version = 10`) |
| No co-op patch touches `playerController` | grep across `memoria-patches/*.patch`, only pre-existing fork-fidelity hits (`FieldMap.cs:1968,1977`) |
| Cutscene-triggers-are-local law (prior art) | `project-ff9-multiplayer-injector.md:683,696-700` |
| SPECTATOR-FIELD PARADIGM (prior art) | `project-ff9-multiplayer-injector.md:606-615` |
