# Field co-op polish — design synthesis

**Date 2026-07-19. Research round only — nothing is implemented.** This doc is the decision layer;
every engine claim's file:line evidence lives in the six recon docs beside it (written the same day by
parallel source-verified research passes):

- [`interactions-census.md`](interactions-census.md) — chests/talk/menu suppression choke points
- [`gateways.md`](gateways.md) — gateway suppression + the transition-intent early warp
- [`camera.md`](camera.md) — guest camera follow
- [`platforms-teleport.md`](platforms-teleport.md) — platform/ladder mechanics + teleport-to-host
- [`dialogue-sync.md`](dialogue-sync.md) — dialogue/ATE/cutscene mirroring ladder
- [`surface-sweep.md`](surface-sweep.md) — every other surface + the canonical already-promised list

## The frame

The SPECTATOR-FIELD PARADIGM (user-set 2026-07-15): the guest is a COMBAT participant and a FIELD
spectator — interaction authority is the HOST's alone. Battle is stable (the diorama, s40/s41);
this round designs the field half. Unless stated otherwise every proposal below is **guest-side only,
fail-safe vanilla** (link death → vanilla behavior within the ~2s position-lane staleness), and
scoped to **follow-mode sessions only**: free-roam ghost co-op (`FollowHost=0`) keeps full vanilla
interactivity.

**Scope predicate.** Recommend `NetSyncClient.IsLiveFollowedSession` (enabled + FollowHost +
role=client + connected + position-lane fresh) as the default guard for the new gates — "FollowHost=1
⇒ spectator rules," armed from pairing, not from the first mirror boundary.
`IsMirroringStory` is the alternative for state-flavored gates (it matches s38 doctrine: pre-mirror,
the guest's own game is legitimately its own), but it leaves the pre-mirror arming gap the s42
same-field kick exists to close (gateways.md §3). Per-gate final call at build time; either way,
**every gate needs a selftest arm** — `IsLiveFollowedSession` requires `role=client`, which
`Role=selftest` can never satisfy, so each feature ships with an `IsSelfTestRole`-based bench path or
it is solo-untestable (the diorama's containment-predicate lesson, verbatim).

**Knob policy.** Per the Diorama-knob verdict (removed, 3/3 judges): no per-feature `[Netsync]` knobs.
These behaviors ARE the follow-mode contract. Dev levers only where a solo bench needs one.

## Decision table

| # | Area | Recommendation | Wire | Size | User decision needed |
|---|------|----------------|------|------|----------------------|
| 1 | Chests / talk / script menus | Gate `CheckNPCInput` + `CheckQuadInput`; add the `Menu()`-opcode gate | none | S | accept the verbatim-stock-chest hole? |
| 2a | Guest gatewaying | Gate the `MAPJUMP` opcode + watchdog fade-in recovery | none | S–M | no |
| 2b | Early warp | Transition-intent emitted at `SetNextMap`, state-lane section | v11 | M | no |
| 3 | Camera | Scroll-target substitution → the ghost's position (option A) | none | S–M | invest at all? (user leans yes) |
| 4 | Teleport-to-host | `SetPosition(rs.Pos)` direct; **F11** + **held L3**; auto-TP off | none | S | mapping taste; auto-TP default |
| 5 | Dialogue/ATE | L1 co-location pin+teleport → L2 confirm/choice mirror | v11 (L2) | L | pacing tradeoff (below) |
| 6 | Safety fixes | ATE-achievement gate · F6 snapshot leak · `Menu()` gate | none | S | no |

## 1. Chests + talk + the menu family (nix guest interaction — yes, and it's cheap)

**Today (source-verified):** a guest opening a chest writes only its OWN bag + local flags — there is
**no guest→host channel on the field at all** (zero-hit grep for item mutation in `Netsync/`), the
host's chest stays closed, and the guest's copy is wiped at the next field-load mirror / discarded by
the exit ramp. So the feared both-open-both-loot dupe **cannot reach any surviving state** — the real
problem is desync theater and the guest disturbing its own mirrored world. The user's recollection
("host receives the guest's item") was inverted: nothing crosses; each side loots its own world.

**The seam is exactly where we hoped.** Starting a new interaction and advancing an open window are
*structurally disjoint* paths: all new tag-3 interactions start through one funnel
(`EventCollision.CollisionRequest` → `CheckNPCInput`/`CheckQuadInput`, reading `ETb.KeyOn`), while
window advancement runs through `UIKeyTrigger`/`Dialog.OnKeyConfirm` and never touches `KeyOn`
(interactions-census.md §1, dialogue-sync.md §1). **Gate the two Check\*Input calls** on the scope
predicate — a two-line s38-style diff, zero gArgUsed exposure (they aren't opcode handlers),
structurally incapable of touching tread regions (`[[coop]]` plates, gateways) or window advance.
One choke point covers kit NPCs, kit chests, savepoint moogles, shops, and Mognet (all tag-3).

**Plus the `Menu()`-opcode gate** (surface-sweep.md §B1 found the hole): s38's menu gate lives in
`UIKeyTrigger` (key presses); the `Menu()` opcode (`0x75`) is a different path with zero gating — a
guest talking to a moogle today gets the full Save/Tent/Mogshop/party UI (only the final save confirm
is blocked). The interaction gate closes the moogle *talk*; the opcode gate is defense-in-depth for
any mirrored script that opens a menu spontaneously. ⚠ gArgUsed-sensitive: consume both `getv1()`s
before returning.

**The accepted hole:** the *stock* chest idiom (decoded from field 200) is a tread-entered body that
polls the confirm button *internally* — on a **verbatim fork**, that chest stays openable by the
guest. Closing it means masking `KeyOn`'s Confirm bit globally for followed guests, which would also
break kit action-prompt idioms. Recommendation: accept (rare, ramp-discarded, invisible to the host);
the KeyOn-mask is a documented follow-up rung if playtests surface it.

## 2. Gateways (suppress) + the transition intent (early warp)

**Why the guest learns so late today** (gateways.md §1): the host's `fldMapNo` flips the *same frame*
`Field()` fires, but the pos lane goes **silent** (field-0 sentinel) for the whole fade+load window
because the fieldmap is torn down — the destination reaches the wire only after the host's new field
finishes loading. The guest then eats a 1.2s debounce + its own ~0.9s fade, all serial. Total ≈
0.9s + host load + broadcast + 1.2s + 0.9s.

**Suppression:** classifying "gateway regions" at TreadQuad is **not decidable** (no engine tag
separates gateway bodies from other tag-2 logic) — so gate the **`MAPJUMP` opcode guest-side**, the
proven s38 ENCOUNT pattern (consume `getv2()` first; gArgUsed). ⚠ The fade-before-Field hazard is
real: by opcode time the guest's script has already blacked the screen and killed user control, so the
gate ships **with a watchdog fade-in + control restore** — suppression without recovery is a softlock
generator. Scripted cutscene `Field()`s are also caught, correctly: the guest's move is the intent
lane's job.

**The intent lane:** `EventEngine.SetNextMap` is the single funnel every field→field transition
crosses at its START (gateways, scripted warps, world-map exits, F6) and structurally excludes battle.
Host emits `SectionIntent` (destination field) on the **state lane** — NOT the control lane, which
`NetSyncBattle` unconditionally overwrites every tick (a real collision the recon caught) — pushed
out-of-band past the 150ms throttle, so it reaches the guest in ~1 write tick (~33ms). Guest treats a
fresh intent as authoritative: fade immediately, skip the debounce, keep the registration guard.
Guest fade+load now runs in PARALLEL with the host's — the win is roughly the host's entire
load + debounce + serialization, i.e. multiple seconds per transition. Wire → **v11** (precedent:
every payload addition bumped, deliberately, even when mechanically parseable). Dedup vs the pos-lane
fallback path and the s42 kick via the existing `_followWarpedTo` latch; ENDING/battle/staleness
semantics in gateways.md §2.

**Composition:** with `MAPJUMP` gated, ALL guest transitions become follow-driven — the intent lane
is not a nicety, it is the responsiveness floor of the whole design. Full state machine (intent /
pos-lane fallback / s42 kick / exit ramp) in gateways.md §4.

## 3. Camera — follow the host (option A: scroll-target substitution)

Cheaper than feared, and more justified than a polish item: on multi-camera fields the active camera
switches on the *guest's* regions (the ghost has no `Obj`/uid and never enters region scanning), so
host and guest can legitimately hold **different cameras** today — the guest can be looking at the
wrong part of the room entirely.

The scroll target is one read — `playerController.curPos` in `FieldMap.CenterCameraOnPlayer` — and the
result is **unconditionally clamped** to the active camera's window, so ANY substituted position is
provably safe. **Option A:** while following + same field + ghost fresh, feed the ghost's position as
the scroll target (data already streamed at 30Hz — zero wire change); fall back to the guest's own
actor on blip/absence, smoothed for free by the existing `CameraStabilizer` ease. Scripted cutscene
pans (`SceneService2DScroll`) already run upstream and override naturally. What A does NOT fix: the
active-camera INDEX on multicam fields still switches on guest position — the C-hybrid (mirror the
camera index on the wire) is the documented escalation if playtests show wrong-camera moments;
full B/C/D analysis in camera.md §3.

Interaction flag: with the camera on the host, a free-walking guest can walk *itself* offscreen —
which is why auto-teleport flips on with this feature (below).

## 4. Platforms / ladders / same-field separation — teleport-to-host

**Ground truth** (platforms-teleport.md §1): platforms, ladders, jumps, kit chests, gateways, and
savepoints are all one family — press-gated quad-region triggers — separate from NPC dialogue and
from walk-on tread. So the §1 gate DOES take ladders/platforms from the guest (the user's hunch was
right), and it doesn't matter that it does, because **no rider physics exists anyway**: a platform
ride is a script rewriting the *triggering* player's position per-frame — it only ever moves the
machine that started it. Host rides away; guest was getting left behind regardless. Nothing recovers
same-field separation today (follow-warp keys only on field change; the s42 kick is a session-start
one-shot).

**Teleport-to-host:** bypass the `.eb` layer entirely — `FieldMapActorController.SetPosition(rs.Pos,
true, true)` from C#, using the host position the ghost already renders from (the coordinate frame is
1:1 by the s36 recipe). Multi-floor is already solved: `GetTriIdxAtPos` picks the triangle nearest the
given Y — the caller must stay in the Y-aware path (the XZ-only opcode family snaps to the topmost
floor; platforms-teleport.md §3). Camera recenters next frame with the ease. Cross-field: the hotkey
just re-fires follow-warp.

**Mapping:** **F11** tap (confirmed unclaimed in field context) + **held L3** ~0.6–1s (unbound in the
default controller profile), intercepted in `UIKeyTrigger.Update` via the SwallowAssistKey/F6 early
pattern, guarded on the scope predicate. The Alpha1/help-menu collision is the cautionary precedent —
both picks were vetted against the full MemoriaKeyBindings + s21/s22 + Alt+F* inventory.

**Auto-teleport:** off by default (a wandering spectator shouldn't be yanked); **flips on when
camera-follow ships** (a separated guest would be steering an actor it cannot see). Threshold shape:
ghost > N units for > T seconds.

## 5. Dialogue / ATE / cutscenes — the mirroring ladder

**Today:** the two machines run the same script off mirrored flags, but every trigger is local — a
guest away from the host's cutscene sees ghost pantomime with idle NPCs; GLOB consequences self-heal
at the next field load; **MAP-scoped consequences and ATE bookkeeping never self-heal** (the mirror
carries GLOB only); choices are fully local. Mechanism luck (dialogue-sync.md §1): the window-block is
a per-object wait byte; the confirm funnels through `Dialog.OnKeyConfirm`; choices resolve through a
**single static** `DialogManager.SelectChoice`; and the engine already uses `(fldMapNo, winnum,
textId)` as a window identity — our cross-machine alignment key exists for free. Forced (mode-6) ATEs
have no accept input at all; only optional (mode-1) ATEs involve a choice.

**The ladder** (recommend building in this order):
- **L1 — co-location:** when the host enters a blocking event (predicate candidate:
  `GetUserControl()` false — ⚠ also false during ordinary gateway walks; needs the in-game
  falsification pass, dialogue-sync.md §3), broadcast it; the guest is pinned + teleported to the
  host's position so the guest's **own genuine copy** of the trigger fires locally — both watch in
  real time. Reuses the §4 teleport primitive. What still diverges: window pacing and choices.
- **L2 — confirm/choice mirror:** host taps `Dialog.AfterHidden` (window closed) and the choice
  commit; emits FIFO frames (the command-lane family, not latest-slot — bursts must all arrive)
  tagged with the alignment key; the guest suppresses local dialogue input, forces
  `Dialog.SelectChoice` to the host's index before confirming, and drops misaligned frames. Timeout
  (`GuestWaitMs` precedent) restores local advancement — a guest hung forever on a lost confirm is a
  shipping bug. Wire → v11 (bundle with the intent lane).
- **L3 — "play the game without a player"** (guest runs no triggers; host drives everything) stays
  the research horizon — a different architecture, explicitly NOT this round.

**The pacing decision (user's call):** L2 as specified = the guest reads at the HOST's pace (true
lockstep, never desyncs, can't linger on a line). The middle option exists: **choices-only mirroring**
(force the host's choice, leave confirm pacing local) — guest reads at its own pace, decisions still
agree; cost = transient pantomime drift mid-scene, converging at scene end.

## 6. The sweep — safety fixes + scope rulings

Three finds should ride the first engine round as straight fixes (no design needed):
1. **ATE achievement escape** — an unsynced guest ATE accept can file a real Steam report (`ETb.cs`
   path, no mirror gate) — the same class s38's funnel gate exists for; verify the path truly bypasses
   `ProcessAchievementReport` (the EMinigame precedent says it can), then gate it.
2. **The F6 snapshot leak** — Snapshot-while-mirroring → session ends → RestoreSnapshot → manual save
   writes HOST story into the guest's PERMANENT save: the second known exit-ramp escape. Fix: stamp
   snapshots taken while mirroring and refuse restore-after-ramp (or clear them at the ramp).
3. **The `Menu()` opcode gate** (§1).

Noted, no action this round: `PARTYDELETE`/`GILADD`/`GILDELETE` are unconditional unmirrored writes
(ramp-scoped — theater only; PARTYADD is accidentally shielded via `partychk`). **World-map following
is a structural non-feature** (the `gMode==1` broadcast scope; guest waits on its last field until the
host enters the next field — fails safe) — ruled an explicit FRONTIER, not part of this round; zero
vehicle/world-map netsync code exists, honest scope in surface-sweep.md §B4. **Guest F6** stays
available (cheats are ramp-scoped; warp-away is yanked back by follow-warp) except the snapshot fix
above. **The `[[coop]]` plates and all tread regions remain untouched by every proposal here** — the
suppression seams were chosen specifically because they cannot reach tag-2.

The canonical already-promised list (20 items, each DONE / SHIPPED-UNPROVEN / OPEN with sources) is
surface-sweep.md §A — this round's items subsume the "near-term cheap flip side" note and the
cutscene-sync research note from the memory.

## Build plan

- **Round F1 — one DLL, no wire bump:** teleport-to-host (the recovery primitive ships FIRST — it is
  what makes suppression softlock-safe) + the §1 interaction/Menu gates + the §2 MAPJUMP gate with its
  fade-in watchdog + the three §6 safety fixes + (optional, same round) §3 camera substitution.
  Everything guest-side; a stale peer keeps pairing (behavior gates don't force updates — the s38
  asymmetry rule applies: update both machines anyway).
- **Round F2 — wire v11:** the transition-intent lane + dialogue L1 (co-location) — L1 needs the
  host's in-event broadcast, so it shares the bump.
- **Round F3:** dialogue L2 (confirm/choice mirror), shaped by the pacing decision.
- Each gate ships with its selftest bench arm (see The frame) and one-line decline telemetry (the
  B3.3b every-gate-logs law). Sequencing vs the outstanding netsync queue: the s42 fixes are
  deployed-unproven and the B3.6 two-machine boxes are still open — F1 should not land in the same
  DLL as an unproven s42 unless the next two-machine session proves s42 first.

## Open decisions (the user's)

1. **Camera:** ship option A in F1, or defer camera work entirely? (Recon says A is small and safe;
   multicam index mirroring stays a documented escalation.)
2. **Dialogue pacing:** full lockstep (L2), choices-only mirror, or stop at L1 co-location?
3. **Teleport mapping:** F11 + held-L3 acceptable? Auto-teleport-when-camera-follows acceptable?
4. **The verbatim stock-chest hole:** accept, or add the KeyOn-mask rung?
5. **World map:** confirm it stays a frontier (out of this arc's scope).
