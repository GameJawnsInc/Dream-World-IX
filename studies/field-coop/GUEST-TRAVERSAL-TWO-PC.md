# Guest traversal: the first two-PC session (2026-10-27)

Both PCs ran engine s156 (`Assembly-CSharp.dll` `628e4c47…`) over the relay. The host was set to
`guestSlots=2 ghostAs=auto`, and the guest commanded Steiner. The owner ran the five R3 checks on fields
359, 114, 207, 408, 300 and 301.

The logs are archived in two places: `.harness-runs/twopc-r3-20261027/` in the main repo, and
`C:\gd\SCRATCH\guest-traversal\logs\`. Each holds `desktop-host.20261027-151000.log` and
`laptop-guest.20261027-151000.log`. Read those copies, not the live `Memoria.log`.

Every cause below was traced in the engine source by one agent and then checked by a second agent asked to
refute it. All five held, with the corrections folded in here. Cites are against `C:\gd\FFIX\Memoria\Assembly-CSharp`
at s156. The agents' scratch censuses are in that session's scratchpad (`wf\`); the counts are quoted here.

## What it proved (R3, two machines)

| Check | Owner | Guest log |
|---|---|---|
| Climb up and down | good | 114 entry 9 six times (as Vivi, undressed); 207 entries 10/11 six times; 408 entries 4/6/8/10; 301 entries 7/8. Every one `climb started … verified` then `climb ended`, except the 301 jump a battle cut into |
| Host talks while the guest is mid-climb | good | the start is held and applied at the dismount: start 2 at 15:02:09 (held 4000 ms) and start 5 at 15:02:49 (held 2234 ms). Start 1 was dropped when the host's conversation ended during a 28.5 s hang (by design, D8b) |
| Host battle mid-climb | good: "ended up back at the entrance on the guest" | 301 entry 7 at 15:09:39: `diorama boot: COLD return`, the climb record dropped at the reload (15:10:25). The next battle (15:10:30, control on) primed WARM |
| F11 mid-climb | good | refused at 15:03:27, `a guest climb is in flight` |
| A press during a host scene | good: nothing happened | no log line names it |

Two presses on 301 were declined: entries 9 and 11, `not on the traversal table`. Both are LOCO+LATCH jumps,
the later rung, so the refusals were correct.

Two side effects show in the log. Neither needs a change now:
- **A dropped hold leaves the guest one conversation behind on that NPC.** After start 1 was dropped, the
  guest's copy applied start 2 and played the NPC's first conversation (texts 159-162). The host was already on
  its second conversation (text 166). The orphan rule closed those four lines at reading pace (15:02:13-15:02:25),
  and the next talk matched. NPC talk counters are field-local, so this cannot outlive the field.
- **The 30 s long-climb line fired inside the battle** (15:10:08). It is telemetry only. It could skip diorama
  time.

## Finding 1: ghosts keep climbing when the climber stops (both screens)

**Cause.** Stock FF9 never plays a ladder clip. The climb loop (114's `Vivi_17`; 207's `Zidane_50`) sets
afHold (`SetAnimationFlags(1,0)`) and moves the anim frame by hand with `SetAnimationInOut(f±1)` only while a
direction is held. `PlayAnimationViaEventScript` samples `animFrame/frameN` at speed 0
(`FieldMapActorController.cs:405-431`), so a stopped climber holds its pose.

The 30 Hz position lane carries the anim id but not the frame (`NetSyncClient.cs:1922-1928`; type-0 payload
37 B, `NetSyncSocket.cs:192-229`). `DriveGhost` plays the clip with `WrapMode.Loop` at speed 1 and never sets
`time` or `speed` (`NetSyncClient.cs:10523-10563`). So every ghost free-runs its climb clip while the id
stays the same: the host's ghost on the guest's screen, the guest's ghost on the host's screen, and the selftest
mirror. The same loop plays while moving, at the clip's own rate and forward on the way down.

The guest's own body is not affected: it is the stock climb on its own copy.

**Fix (recommended).** Send the anim frame and frame count as trailing bytes on the type-0 lane. A v14 receiver
reads the first 37 B and ignores the rest, so this is no wire bump. Sample the ghost like the engine does, with
four precautions:
- ease `time` toward the wire frame at the position's `LerpRate` (12), wrap-aware. This install runs
  `FieldFPS -1`, so the local body's animation is smoothed (`SmoothFrameUpdater_Field.cs:100-185`) and a
  raw 30 Hz snap would step.
- hold while the frame is unchanged, and snap on a clip change.
- restore `speed = 1` on every free-run path. `AnimationState.speed` persists per clip, so a ghost could
  otherwise stay frozen after a re-dress, a 37-B peer or a return to walk.
- guard `frameN` 0, 1 and 255.

Prove the wire half with `coop_peer` or the duo harness: the selftest mirror reads `me.animFrame` locally and
proves only the sampling. Also update the kit pin `test_coop_peer.py:173-180` (37 B) and the relay keepalive
`NetSyncRelay.cs:82-83`.

An unbumped change lands silently on a mixed pair. That is cosmetic, and the owner can decide.

**Fallback with no wire change.** Integrate the clip time from the ghost's smoothed height delta (one frame per
about 20 u, as stock steps it). This fixes ladders only.

**How often:** 51 fields / 94 stock functions hand-step the frame this way (ladders and poles).

## Finding 2: a dressed guest glides up ladders and through jumps in a standing pose (the "pencil")

**Cause.** Self-dress (s140) sorts every Zidane `LADDER_*`/`JUMP*` clip into class 7 and deliberately sends it to
the worn rig's idle alias (`NetSyncSelfDress.cs:206-245`; for Steiner, 2002 = `ANH_MAIN_F0_STN_IDLE`). The
twin rows were deferred (s141 amendment 7, `:1202`). `KeepSourceTimeline` keeps Zidane's frame count, so the
script's frame steps scrub an idle clip at k/frameN while `MoveInstantXZY` or `Jump` carries the body.

It is not the bind pose: the alias clip is attached and sampled.

On the host's screen, the guest's ghost receives anim 2002 on model 5489. `GhostAnim` plays the raw wire anim
when the dress equals the wire model (`NetSyncVisitor.cs:458-469`), so the host also sees the idle glide.

Field 114 looked right because the guest's body there is the field's own Vivi (SetModel 8, never dressed).
Field 301 glided too (dressed, uid 20); the owner judged that rung on the battle return only.

**Fix (recommended): same-suffix twin rows, one engine patch, no wire bump.** Map each Zidane ladder or jump clip
to the worn rig's own clip of the same suffix at the play and jump sites, with `KeepSourceTimeline` untouched.
Put the clip-present guard in `MapAndAttach`, because `MapRigAnim` is pure. Share the table with the ghost side
(`GhostAnim`) for a host dressing an undressed guest.

Rigs with real clips on disc:
- ladders: Vivi, Garnet, Steiner, plus Marcus `1_x` only;
- `JUMP_1/2/3`: Vivi, Garnet, Steiner, Freya, Quina, Eiko, Amarant, Beatrix.

Every other rig keeps the idle slide (owner decision 4).

Caveats:
- **Steiner's ladder clips are a different length** (10/13/13/11/11 frames against Zidane's 8/12/14/11/12).
  On Zidane's timeline they are retimed slightly. Ladders could instead run on the twin's own timeline, since
  stock windows match across Vivi, Garnet and Steiner.
- **Several twins are never played by any stock script:** Steiner `JUMP` 7242 and `JUMP_2` 12031, Garnet
  `JUMP_2`, Beatrix `JUMP_1-3`, Marcus ladders, Blank `JUMP`. Zidane's `JUMP_2` is used on 408 entry 9, so a
  Steiner guest would land on his unplayed one. Either limit the table to stock-played clips or bench each with
  a `game_snap` still.
- **Rewrite three checks with it:** the in-game selftest `AliasTable` (`NetSyncSelfDress.cs:2917-2935`), the
  Python twin in `tools/harness/battlewire.py` (`:8513-8566`), and the `test_dress_census` ladder mutant.

**Ship it with Finding 1.** Otherwise the host's ghost loops Steiner's real climb at speed 1 instead of his idle.

**Today's workaround:** the host sets **They appear as: Their own model**. That empties `GhostAs`, section 8 ships
model 0, and the guest disarms its dress. A body already dressed stays dressed until its next SetModel, which is
the next field load.

## Finding 3: the guest's character appears twice in story scenes (Dali 359)

**Cause.** Both copies run the same scene script. Each walks its own player object (359 entry 6, "Zidane")
along the same authored path, and each draws the other player's ghost at that player's real position, which is
the same spot.

- **Host's screen:** the host's Zidane; the guest's ghost dressed as Steiner, inside Zidane (trailing by
  `LerpRate`); and the scene's own Steiner (entry 9, `Steiner_Bis`, model 658) walking in. So two Steiners, one
  inside Zidane.
- **Guest's screen:** the guest's own body. It is the field's player object, dressed as Steiner at SetModel, and
  plays Zidane's part, with Zidane's gestures falling back to Steiner's idle. Beside it, the host's ghost as
  Zidane at the same spot, plus the real Steiner.

Two more facts constrain the fix. The dress cannot be taken off mid-field: there is no path that rebuilds a live
actor's model, and the teardown law keeps a dressed body dressed until its next SetModel. And nothing hides a
ghost during a scene today; the only hide is the per-submesh mask. The same coincidence appears briefly at
every parallel-follow arrival.

**How often:** 346 of 817 stock field scripts (42%) have a non-player entry with a party-member model; in 282
fields the script walks one. Those are upper bounds, since an entry is not always on stage. Emergences from
Zidane use authored coordinates and could not be isolated statically: 120 fields place or walk a party actor
within 40 u of the player's authored points, 58 of them by placement.

**Options:**

| Option | What it does | Cost | Gets wrong |
|---|---|---|---|
| A. Guest step-out | while the guest's copy holds its body for a host scene, its body and blob shadow go dark (a term in `SetRenderer`'s flag4, `ProcessEvents.cs:537`); the host's ghost of it vanishes through the mesh mask it already ships, and the host honours a zero mask | about 100 lines, no wire bump, no model rebuild | on the guest's screen, the protagonist becomes the host's ghost, which loops every clip, has no shadow, runs on the host's clock, and has its bubbles anchored to the hidden body |
| B. Hide only the ghosts (the first idea) | each screen hides the other player's ghost during host scenes | about 20 lines | fixes the host's screen only; the guest's screen keeps Steiner-as-Zidane and loses Zidane entirely |
| C. Host-side scene hide | the host hides the guest's ghost during its own plain scenes | about 20 lines | covers scenes the guest's copy never runs (the guest keeps control), never the guest's screen |
| D. Undress for the scene | rebuild the guest's body as Zidane mid-field | large, high risk | breaks the teardown law; the frozen-camera class |
| E. Borrowed pose | while stepped out, draw Zidane on the guest's screen from the guest's own hidden body: its position, the raw source clip and its own frame | about 100 lines | the edges between the two drive sources must snap cleanly |
| F. Double rule | hide a dressed ghost while any visible actor wears the same character | table + object scan | misses the coincidence when the guest's character is not cast; can hide the guest for a whole visit |
| G. Proximity rule | hide a ghost or body that overlaps another actor while both players' control is off | about 40 lines | flickers under clock skew; R needs tuning |
| H. Fade, not pop | fade over about 10 frames | unknown | needs alpha support in the field shader (unconfirmed) |

**Recommendation: A + C + E as one patch.** The guest steps out on both screens, and its own screen draws Zidane
from its own copy's clock. Both screens then show exactly the solo scene.

Trigger: the host is on my field with control off (section 7 b1), my own control is off, I am not in a guest
climb (`NetSyncGuestLocal.InFlightNow`), and the scene is not a relayed talk. The last test uses the existing
`_talkSceneNonce` (`NetSyncClient.cs:7451-7468`). This trigger also covers scenes with no dialogue line, such as
walk-ins and emergences, which the host's sticky scene misses. End on my control back (debounced about 500 ms),
a field change, or the session end.

It still leaves a few things untouched:
- free-roam doubles (a party NPC in town while both players have control; F is a host-only option there);
- a talk that turns into a party cutscene (G refines it);
- the pop.

**This is a taste call for the owner** before it is built: during host scenes the guest does not see themselves.
The owner already wants plain NPC talks to keep the guest visible.

**Owner decisions (2026-10-27):**
- step out on both screens (A + C + E), as recommended;
- pop, not fade;
- the host hides the guest's ghost during its own plain scenes, even when the guest still has control (C);
- no free-roam rule (F) this round.

### Build: engine patch s158 (`memoria-patches/s158-netsync-step-out.patch`)

The number is s158 because another round took s157. The code is `NetSyncStepOut` plus hooks in `NetSyncClient`,
`NetSyncSelfDress`, `SetRenderer`, `PosObj` and the harness.

The guest's rule:
- **Start.** Every base term must hold: a following, mirroring guest on a field; the host on my field with its control
  off; my control off; no guest climb in flight; not a relayed talk; the lever not off. Then the guest steps out at once
  when a fresh line opens on its own copy, and otherwise after a 1.5 s dwell. (The pre-build review dropped an earlier
  host-scene shortcut; see below.)
- **The arrival law.** A door's fade-in has control off on both copies and no line. The dwell keeps it from stepping
  out. Without it, a dressed guest would flash Zidane at every parallel arrival.
- **End.** My control back for 500 ms, a field change, the controlled body changing, the session ending, or the lever.
  It also ends at once when a relayed talk or a guest climb starts inside the episode. The host's state does not end it,
  because the guest's copy may still be playing the tail of the scene.
- **The talk test** is the guest's own copy. A relay accept owns the control-off episode it starts. Before the accept,
  the host's section-5 nonce equal to `_talkSceneNonce` also counts as a talk.

While the guest is stepped out:
- its wire mask is 0, so the host's ghost of it hides;
- its own screen hides the host's ghost;
- a dressed body's meshes go dark through a flag4 term, but the blob shadow keeps stock's flag4, because it sits under
  the stand-in;
- a Zidane stand-in (the body's `netDressSrc` model) follows the body. It copies the body's local position, rotation
  and scale. It plays the body's raw source clip at the body's own normalized time, takes the body's room tint, and
  shows only when stock would show the body. It runs in its own `LateUpdate`, after the logic tick and the smoothing
  pass. The raw clip is recorded in `PosObj.netRawAnims` wherever `NetSyncSelfDress` maps one: the slot setters,
  `RunAnimation`, the dress-time slot store and the jump;
- an undressed body stays visible, because it already is the solo protagonist.

The host's side:
- a zero wire mask now hides the ghost in every dress branch. Before s158, only the same-model branch read it;
- while the host's sticky scene is up and was not raised by a relayed talk (`StartSceneAt` marks those), the guest's
  ghost hides.

Accepted gaps:
- a prop held by a dressed body hides with it;
- the head focus is not copied to the stand-in;
- free-roam doubles (F);
- a talk that turns into a party cutscene (G);
- a scene with no line, shorter than the dwell, shows the double for its length;
- the pop.

### Pre-build review (2026-10-27)

Before the first build, six reviewers each read the private engine copy through one lens: visibility, the trigger, the
stand-in, the wire and the host, the harness and bench, and stock safety. Two skeptics then tried to refute each serious
finding, and a completeness critic looked for misses. 34 of 36 findings survived, and the critic added 4. Fixed before the
build:
- **The client's no-mask ghost branch never came back.** A guest whose own GhostAs dresses the host's ghost as a model
  equal to neither body lost the ghost for the rest of the field after its first step-out. The branch now re-asserts the
  spawn look every frame.
- **The episode carried on through a relayed talk.** A talk or a guest climb accepted inside the 500 ms debounce
  re-dropped control, so a plain NPC talk stayed stepped out. Both now end the episode at once. Talk ownership is also
  scoped to its field.
- **OUT drew the body and the stand-in together** for one logic tick. `SetRenderer` runs only inside a tick, so a dressed
  body now goes dark in the same frame. StepIn re-evaluates the actors that were under the body, so a prop detached
  mid-episode lights again.
- **The host's scene and a HUD strip started step-outs.** On a field with a persistent strip, the sticky scene rises at
  every control-off beat, and AnyEtbLine counts the strip. The start is now a **fresh line**: a lockable, non-inhibited
  window that was not open when the base began. The host-scene shortcut is gone. Option C uses the same fresh-line rule
  against the host's control-off edge, and the card button (`Request(obj, 1, 8)`, never relayed) counts as an NPC
  interaction.
- **The stand-in copies the body's material state every frame:** shader, render queue, `_Slice` and the `_Color` rgb. So
  stock's wading slices (2800, 2951, Evil Forest) and blend fades (2928) reach it. While out, it also takes the source
  rig's eye height, so the speaker's window points at its head. A spawn fault can no longer leak a model.
- **Smaller fixes:**
  - the talk-lane check gets `_talkSceneTalk`'s guard;
  - stale harness reads are gone: `ghost.hide` and `host_plain_scene` are written every frame;
  - the stand-in's published clip time is read off its own AnimationState.
- **Bench defects fixed:**
  - the mirror witness is `dress.ghost.shown_mask`; `hidden` is a list of renderer paths, never a bool;
  - the shadow is judged against stock's own switch (`shadow_off`), because the 207 ladder turns the shadow off itself;
  - IN allows one logic tick for the relight;
  - the time and clip checks could not fail, so they now need a ZDN ladder clip mid-ladder and a moving clip time;
  - the distance check allows one frame of motion (80 u);
  - the climbs hang past the dwell, and a new N-DWELL leg checks that a short climb never steps out.

Accepted and documented: a mirror floor reflects the dressed body; multi-binder fields keep the double; the dress rig's
footsteps keep sounding under the stand-in; a prop attached mid-episode stays at the dark rig's hand; a loco
`RunAnimation` can colour which walk variant the stand-in plays.

**Second round, on the code the first round added** (three lenses, two skeptics each; 14 of 15 survived). Fixed:
- **Option C hid the guest at stock chests, hidden pickups and button-polled signs and posters.** These are an IsButton
  poll in a tag-2 `_Range` function and never reach EventCollision. A control-off episode that begins within 300 ms of
  Confirm, Cancel or Special now counts as an interaction.
- **The inhibit flag was unstable.** `[TIME]` and `[INCS]` set FlagButtonInh only at the label's first render. Only
  `[NFOC]` is never fresh now; it is the one tag that also clears `FlagResetChoice`, at Show.
- **The snapshots anchor on control.** The host's is taken every control-on frame, so a line opened in the DisableMove
  tick counts. The guest's is anchored on its own control, not the whole base, so a line its copy opened before a host
  term held still counts.
- **A promoted quad blinked the guest's ghost for one frame**, because StartSceneAt ran after option C's per-frame read.
  It now clears that read.
- **StepIn is synchronous.** The stand-in hides and the darkened renderers relight in the same frame. The source eye is
  restored even when the field (and the go) is gone.
- **The bench:**
  - IN's mask and mirror checks get the relight grace;
  - the ladder witness needs the loop's own `LADDER_1_2`, since a lost raw record plays the mount clip;
  - the shadow is judged in the step-in debounce, where a dark-term leak would show;
  - N-DWELL raises the host scene once mounted and judges the dwell clock (`base.age_ms`);
  - the part hold before the hang is measured in game units, not frames;
  - the body's clip time is read live.

**Third round, on the second round's code** (two lenses, two skeptics each; 5 of 5 survived). Four of them were one
mechanism: the 300 ms held-input press exemption. It could miss the tap that the same tick consumed, by Unity's update
order (NetSyncClient is added at runtime). It also counted a held Cancel, which is stock's walk/run modifier, so a host
walking into a story trigger escaped option C. The exemption now sits where the script consumes the press:
`TapScriptKeyIfHost` already sees every host script button read, and a control-on read that hit Confirm or Special arms
`NoteHostInteraction`, so the scene that rises within 2 s is an interaction. The fifth was a bench bug: N-DWELL read the
lever's never-armed base as a red, which made K-CAL unreachable; under the lever it now judges only "never out". The
findings went 34, then 14, then 5, all from one mechanism now replaced by a 10-line check at the script's own read, so the
review is closed. The in-game bench and the two-PC session are the next instruments.

## Finding 4: the guest lags the host's F1 high speed through conversations

**Cause.** F1 is stock Memoria's High Speed booster (`UIKeyTrigger.cs:237-256`). `FastForwardFactor` returns
`[Cheats] SpeedFactor` (3 on the desktop), and `FPSManager` runs that many logic ticks
(`FPSManager.cs:83, 95-97`). So the host's field scripts, walks, typing and SFX run 3x.

Nothing about it is on the wire. Netsync never reads `FastForwardFactor` or the boosters. The guest's copy runs
the same cutscene at 1x, and a host confirm can only page a guest window with the same (field, win, text) key
that is open now (`NetSyncDialog.cs:1096-1105, 1307-1330`). The backlog grew to about 10 s over 6 host-seconds
on field 300 (seq 26-33).

When the host's script left for 301, the follow fired at once. `ServiceIntentFollow` has no backlog gate
(`NetSyncClient.cs:6733-6788`), and the inbox purge dropped seq 34-36 at the commit. The guest never saw texts
95, 96 and 98.

The drop-on-follow is structural: any guest lag longer than the host's post-line tail drops the last lines.

**Fix (recommended):**
- **Relay the host's effective field rate** (`FieldTPS` × factor) in a new additive section 9. That needs no wire
  bump; old guests skip it by id and length. The guest mirrors the rate only while its copy plays the host's
  co-located scene: the host is here with control off and my control is off. Apply it level-triggered through a
  field-scoped `FastForwardFactor` seam, re-asserted every tick, because stock `SetFastForward` re-runs at every
  scene load. Never touch the guest's own booster flag, so battles, the world map, menus and FMVs stay out.
- **A narrow capped follow-hold:** hold the follow only while an inbox event for my field waits and my copy is
  in the scene, capped at about 8-10 s. It closes the drop that the rate relay only narrows.

**Also on the list:**
- `[Graphics] FieldTPS` is a second rate knob that is not relayed; the desktop's is 30.
- `TurboDialog` (F9 plus held Shift/RB) auto-confirms at the guest's 350 ms floor, so a mirror cannot remove that
  lag.
- A host log line on the F1 edge would let the next session prove the state.

**Interim:** the guest can press F1 too. It is ungated, but it needs `[Cheats] Enabled=1` and `SpeedMode=1` on
the laptop, and it also speeds the guest's battle diorama.

## Finding 5: the host's ~ Reload field leaves the guest mid-conversation

**Cause.** Four rules combine:
1. The host's scene record ends only on a field-id change, the world map, or control back for 500 ms
   (`NetSyncDialog.cs:2275-2316`). A reload keeps the id, and 359's Main_Init re-raises the scene, so nonce 1
   stayed up from 14:55:23 to 14:59:40.
2. The guest drops a transition intent for the field it is on without logging it
   (`NetSyncClient.cs:6749-6753`), so its copy never reloaded.
3. The host clears a same-field intent on its next Update (`:1942-1943`), so even a guest fix could miss it.
4. The lock releases only on host state. The orphan rule needs the host's scene down for 2 s, and the host's
   scene never fell.

The guest's line 109 closed when the host's replay reached the same key (14:58:35).

**It is not only a debug path.** 174 stock `Field()` calls target their own field, in 82 field scripts. Two
independent counts agree: the kit over the install's `.eb` bytes, and the HW text exports. Of the 174:
- 71 are ATE menu choices played on the current field;
- 59 are the matching return-to-origin;
- 18 are region self-gateways (Iifa Tree roots 1651/1758, Marsh 655, the Lindblum Castle telescope 615,
  Gargan Roo 956);
- 6 are the chocobo places;
- 1 is 257's after-battle reload;
- 19 are other scene and minigame reloads (1607 Eiko's kitchen ×11, 2204 ×7, 352 Dali Inn).

359 is not among them.

**Fix (backlog):**
- the host publishes a cold-load generation as state, level-triggered, not as a longer intent;
- the guest treats a host reload of the field it is on as a re-entry: it reloads its own copy and purges the
  inbox for that field;
- a landing dedup, so a guest copy that ran the stock `Field(own)` itself does not reload twice. This matters for
  the self-jump chains 1607/2204, and extends the s154 follow-landing law.

The cost to accept: on a same-field ATE, the guest takes two fades.

**Interim escape:** wait. The guest re-syncs when the host's replay reaches its line, or when the host leaves the
field. The guest's own ~ Reload field is the faster manual re-sync. The `~` "release dialogue lock" escape is NOT
reliable here: the guest's copy runs ahead into the scene's own `Field(114)`, which bounces into a 359 reload.

## Order of work

1. **One engine round: Finding 2's twin rows plus Finding 1's frame on the ghost lane.** Bench solo first: the
   selftest role with `selfdress self steiner` on a 207 ladder and the 408 jumps, judged by a twin counter, the
   harness `rig` read and `game_snap` stills, and made red by a lever. Then two-PC on 114 undressed and 207/408
   dressed, one change per test.
2. **The party-scene step-out** (Finding 3, A+C+E), after the owner's taste call.
3. **The host's field rate on the wire, plus the capped follow-hold** (Finding 4).
4. **The same-field reload** (Finding 5): backlog. It has real stock cases, so it is not only debug hygiene.
