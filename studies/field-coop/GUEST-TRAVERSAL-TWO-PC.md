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

### Built, deployed and solo-benched (2026-10-28)

s158 was written against s156 in a private copy while s157 ran, then merged three-way onto the s157 engine: s157's
lines first, s158's after. The merge met one real interaction. When s157's twin guard falls back (`TwinMissed`), the
body plays the fallback, not the twin. s158's raw record now follows what the body plays, so the stand-in's
last-play key still matches.

The engine is deployed as `Assembly-CSharp.dll` `1958ac7cfa492238`. Revert set `20261028-013714`.

- **`coop_step_out.py` reads 12/12.**
  - U-UP (undressed on 114) steps out by the dwell at 1.50 s and back in 0.50 s after control.
  - D-UP and D-DN (dressed as Steiner on 207) do the same, with the body dark on every out sample.
  - The stand-in is `GEO_MAIN_F0_ZDN` playing `LADDER_1_2`, 0 u from the body, at the body's clip time to within 0.001.
  - The shadow follows stock's own switch.
  - N-REST, N-CLIMB, N-TALK and N-DWELL never step out; N-DWELL's longest base was 0.92 s.
- **The calibration (`COOP_CALIBRATE=1`) reads 11/14.** Exactly U-UP, D-UP and D-DN go red, each on its marker.
- **The stills** (`.harness-runs/20261028-020435-s158-stills/`, an unjudged lab):
  - at rest, Steiner and his mirror ghost side by side;
  - mid-ladder after the dwell, only Zidane on the rungs in his own clip;
  - at the top, both back.
- **The regression set is green on s158:**
  - coop_guest_traversal 28/28;
  - coop_climb_anim 21/21;
  - coop_self_dress 65/65;
  - coop_talk_relay 28/28;
  - coop_dialogue_authority 147/147;
  - the duos coop_dress_wire 22/22 and coop_follow_race_duo 21/21.

  The shared install is live-configured as a host and refuses the selftest role, so the three single-game dialogue
  and dress benches ran on the host instance root.

Not proven: the two-PC session. The bench fakes the host's scene bit and reads the selftest mirror, so a real host's
option C and a real guest's mask over the relay are first seen there.

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

## The second two-PC session (2026-10-28, s157 + s158)

Both PCs ran `Assembly-CSharp.dll` `1958ac7c…` (s158 on top of s157) over the relay, with the guest dressed as Steiner.
The logs are archived in `.harness-runs/twopc-s158-20261028/` in the main repo and in `C:\gd\SCRATCH\guest-traversal\logs\`
(`desktop-host.20261028-105911.log`, `laptop-guest.20261028-105941.log`). Each finding below was traced by one agent and
checked by skeptics asked to refute it; the corrections are folded in.

| Check | Owner | Verdict |
|---|---|---|
| 114 ladder (undressed) | "looked good" | s157's ghost frame: **two-PC confirmed** |
| 207 ladders and 408 jumps (dressed as Steiner) | "looked good" | s157's twin clips: **two-PC confirmed** |
| 359 (Steiner walks in) | no defect reported | stepped out on the first line, as designed |
| 352 (the Dali inn night scene) | "Zidane was replaced by Steiner in the scene on the guest" | **s158 defect**, below |
| An emergence scene | not tested | open |
| After a dialogue box closes | "animation jitter sometimes on the guest" | open, below |

### Finding 6: 352's night scene keeps the guest's Steiner in Zidane's part

**Cause (confirmed).** s158 anchors the episode on the controlled actor (`ServiceStepOut` passes `ee.GetControlChar()`;
`StepOut` takes `_body = local` and `_dressed = local.netSelfDress != 0`). 352's first load is entrance 3, the night scene
351's inn rest starts. There Zidane_Init dresses uid 17 as Steiner but skips its own `DefinePlayerCharacter` (test2_95.txt:1502),
and Dagger_Init binds control to uid 19 (:3196-3217); the guest log says so ("binds control to uid 19 -- not the dressed body
(uid 17): a co-actor binder, accepted (D3)"). So the step-out went OUT on Dagger, undressed ("the body stays"), and nothing
darkened uid 17. It stood lit as a second Steiner beside the real one (entry 20) and spoke all of Zidane's window-4 lines, 28
lines over two minutes. The episode ended "body" when Steiner_Loop's `TerminateEntry(19)` zeroed control. The entrance-4 reload
bound control to Zidane and stepped out correctly. The root is shared with s140: the D3 dress of a Zidane entry that is not the
binder was accepted there, and s158's header listed "multi-binder fields keep the double" as a gap. This is the first real scene
to hit it. Exposure: 165 stock fields have a non-player entry that also binds control in an Init (the s140 audit's count), and any
field where a co-actor binds after the dress is exposed during its scenes.

359 behaved as designed: its dressed Zidane (uid 6) was the only binder, and the 11:01:57 "IN ... -- body" was Steiner_Bis_Loop's
`TerminateEntry(6)`, which disposes the body. The IN line's wording ("the body is back") is wrong for a disposed body.

**Fix: engine patch s159 (built, deployed and solo-benched 2026-10-28).**
The episode now acts on the guest's DRESSED body, picked in this order:
- the controlled actor, if it is dressed;
- else the body dressed on this load (`NetSyncSelfDress.DressUid`), while it lives;
- else the controlled actor.

"Lives" means three things:
- the body is still in the active object list (`FindLive`, a null-safe walk: a TerminateEntry'd body is unlinked at once);
- it still wears its dress;
- it still has its go.

A control rebind no longer ends an episode; the anchor's death, or a lost go or dress, still does. A start still needs a
controlled actor, as in s158, so the arrival law keeps its timing on loads that bind after the dress. The stand-in, the darken
and relight, the Renderer hook and the eye swap were already keyed on the episode's body. On 352 the eye swap matters: the speaker
window anchors on uid 17. The wire mask and the ghost hide are unchanged. The IN line now says "the body is gone" when the anchor
was unlinked.

The harness:
- `netsync.stepout.anchor` {uid, ctl_uid, dressed_uid, ctl_rends_on} is a new key;
- `body_rends_on` and the shadow reads now judge the anchor;
- a `stepout ctl` lever puts s158's rule back, for calibration;
- the proof line has 44 rows and 15 mutants.

The bench leg M-352 clears 352's control latch (`flag 158 0`), as 351's inn rest does. Without that, 352's Main_Init gives
control and the step-out never starts. It then warps with a raw step, because `Session.warp` waits for control that the night scene never
gives, and raises the host scene. The witness is a new `ctl_elsewhere` on 352 with two different bodies in `anchor`.

Results on s159 (`029b2456…`, then the tagged `09bc8ec6…`), one game at a time on an idle machine:
- the bench reads 13/13;
- `COOP_CALIBRATE=anchor` reds exactly M-352, on its marker: OUT on the controlled uid 19, with the dressed uid 17 left lit;
- `COOP_CALIBRATE=1` reds exactly U-UP, D-UP, D-DN and M-352.
- the regressions are green: guest traversal 28/28, climb anim 21/21, self-dress 65/65, and the duos dress-wire 22/22 and
  follow race 21/21.

A pre-build review (four lenses, two skeptics per finding) upheld 6 of 11 findings. All six were fixed:
- the leg's latch and raw warp;
- the null-safe lookup;
- the rule owning liveness;
- the "gone" wording;
- the driver's role-first words.

One bench judge was also fixed. The step-in debounce is now measured from the last control-off sample, because a 171 ms publish
stall made a correct engine read 0.40 s.

**A bench law learned here:** never bench while the test suite runs. With six pytest workers busy the frame rate swung between
35 and 84 fps, and timing legs went red on a correct engine. On an idle machine, every red was exactly a predicted one.

### Finding 7: animation jitter on the guest after a dialogue box closes (open)

The logs cannot say which character jittered. The candidates, by fit:
1. **The Zidane stand-in flashes a wrong frame for one logic tick (new in s158).** On a dressed body every Zidane gesture is
   remapped to the rig's idle alias, and the alias shares the idle's clip name. Memoria's frame smoother keys on the clip name,
   so a new gesture reads as a time jump inside one clip, and the stand-in samples its new Zidane clip at that stale smoothed
   time. A looped Talk_x_2 that a box close cuts off at an arbitrary point, then Talk_x_3, is the classic after-close shape
   (351's step-out had the most of them). Fix lane: Follow samples the body's logical frame for the tick a new play starts (a
   per-body play counter bumped at RunAnimation catches same-id and alias-to-alias starts).
2. **The step-in hand-off.** About 1 s after the scene's last box closes, the stand-in hides, Steiner relights and the host's
   ghost reappears at the host's own position and frame: one Zidane swaps for a slightly different one. Its timing fits exactly.
3. **A visible dressed body's gestures on the idle alias (s140's alias law),** smoothed the same way. 352's scene showed it for
   two minutes.
4. **s157's ghost frame-follow** on the host's ghost; unlikely while stepped out, since the ghost is hidden then.

Needed from the owner: which character jittered (the Zidane stand-in, the guest's Steiner, or the host's ghost), whether it was
mid-scene or only as a scene ended, and the laptop's `Memoria.ini` `[Graphics] FieldFPS` (smoothing is off when it equals
FieldTPS 30; candidates 1 and 3 need it on). A short video settles it.

### For later patches (traced, not built)

- **Chests: the guest sees no lid and no item window** (301, and again on 352). A stock chest opens in its tag-2 `_Range` body,
  which polls Confirm with control on. That never reaches the talk relay (`EmitTalkStartIfHost`) or the key relay
  (`TapScriptKeyIfHost` relays only control-off reads), so the guest's copy never runs the open, and the host's "Received Item!"
  window ages out on the guest after 20 s. This is F3.2's designed-in gap B, not a regression. Lane: a tag-2 "poll start"
  relay modeled on quad promotion (the host arms on its control-on Confirm read of the chest, promotes when the window rises; the
  guest serves the press once to that chest's next control-on read). Risks: 301's chest latch is off on the guest's copy, so
  prove it on a latch-free chest first; the guest's item grant is session-scoped; the same tap covers pickups and signs; a
  version gate for older guests.
  **Designed as engine s160, 2026-10-28: `CHEST-RELAY.md`.** Owner decisions: chests only (stock models 75/91/701/702,
  140 of the 186 stock tag-2 button spots), and the guest kneels like stock. It builds after s159; the ATE round is s161.
- **ATEs: the guest sees the "ATE" icon but never the menu or the title.** Each copy draws the icon itself. The menu opens only
  on a Select read with control ON, which the host never relays and the guest masks on purpose (MISC-08). So the guest's copy
  never opens the choice window (text 98), and the title card and the white fade inside that branch never run. The ATE's
  closing lines on 350 were also queued and dropped on the guest when the host's intent pulled it back. Lane: relay the host's
  ATE press keyed on the host's own menu actually opening (not the raw Select read: `&&` does not short-circuit, so the read
  runs every frame), serve it Select-only to the same reader on the guest, and let the guest's own `Field(350)` through
  `RedirectGuestFieldJump`. **Now engine patch s161: design, census and status in `ATE-RELAY.md`.**
- **Noticed:** from the ATE's arrival on 350 the host re-armed the guest's dress as the moogle fallback (`section 8 model 220
  charId 255`) until 350 re-armed Steiner at 11:09:13; the cause is not traced. And on 350 and 359 the step-out started on
  window 6 text 51, which opens at those arrivals.

## The third two-PC session (2026-10-28, s159 + s160 + s161)

Both PCs ran `Assembly-CSharp.dll` `f42f0c05…` over the relay, host GuestSlots 2, GhostAs auto, the guest dressed as Steiner
from pairing on 408. The logs are archived in `.harness-runs/twopc-s161-20261028/` in the main repo
(`desktop-host.20261028-204100.log`, `laptop-guest.20261028-204059.log`; the host clock runs about 1-1.5 s ahead). Each
finding was traced by one agent and checked by a skeptic asked to refute it; all three root causes survived, and the
corrections are folded in.

| Check | Owner | Verdict |
|---|---|---|
| 302 chest 15 (s160) | "good" | **two-PC confirmed**, but the guest was dressed, not undressed as the README said |
| 301 chest 15 (s160) | "good, no text window or animation" | host-only, as predicted (`not served`) |
| 352 night scene (s159) | "good, shows Zidane on guest now" | **two-PC confirmed** |
| 352 morning chest 16 (s160) | "chest is good", but "why is the guest Steiner when the party is just Zidane" | **confirmed**; the dress question is Finding 8 |
| 352 ATE "Vivi, Confused" (s161) | "worked", "2 Vivis for the first ~1s" | **confirmed**; the double is Finding 9 |
| Back on 352 after the ATE | "the guest was the Moogle instead of Steiner" | Finding 8 |
| ATE Cancel (s161), on 351 twice | "worked" | **confirmed** |
| Guest ahead (README step 3, the GUEST at 3x) | not run | still self-test only |
| "Dagger Tries" 351->450->351 with the HOST at 3x | "the guest played out the ATE at normal speed ... didn't warp back until the ATE completed" | Finding 10 |

### Finding 8: the guest's dress lags a scripted party change by one door

The two dress notes are one mechanism, seen from both sides.

- At pairing, the host's party slot 1 (GuestSlots 2) held Steiner, so section 8 said Steiner and both screens showed him.
- 352's wake-up reload (20:47:21) still had Steiner in slot 1. After the wake-up lines 175-178, Zidane_Loop case 28 runs
  `RemoveParty(2)`, `RemoveParty(1)`, `RemoveParty(3)` and sets scenario 2600 (test2_95.txt:2004-2207, :2322; host log
  20:47:40). The party is now [Zidane], mid-field, with no load. RemoveParty nulls the slot in place (ff9play.cs:156-163).
- From that frame the host's section 8 is the moogle (220, charId 255): the empty-slot rule, which is the owner's own goal
  ("a moogle if 1-person party", R3-FIELD-MODEL-AUDIT.md:7; box B21).
- But the guest reads section 8 only at a field load (`ArmFromState`, only from the ApplyStory success branch), and a dressed
  body keeps its dress until its next `SetModel` (THE TEARDOWN LAW). So the morning chest showed a stale Steiner on both
  screens. The host's ghost passes the guest's dressed wire body through (`GhostGuard(220, 5489) = 0`), so the host agreed.
  This is box B22 ("the laptop changes at its next door"), applied to a scripted RemoveParty instead of a menu reorder.
- The next door was the ATE's landing on 350. The arm read the moogle there (laptop log 20:48:24) and stays the moogle,
  correctly by B21, while Zidane walks Dali alone; nothing refills slot 1 on 351, 352 or 450.
- On 350 the host's ghost showed Vivi, not the moogle: the guest's copy controls an undressed Vivi (self-dress acts only on
  `SetModel(98)`), and GhostGuard passes a non-98 wire body through.

So the moogle is the design, and the Steiner at the morning chest is the lag. Closing the lag needs a live mid-field re-skin of
the guest's controlled body (high risk under the teardown law) or a same-field reload. The alternative rule, a sticky last
member when an owned slot empties, changes B19 and B21, duplicates the member where the story puts him on the map, and
disagrees with battle's "You: watching" (NetSyncBattle.cs:985-1003). The default moogle duplicates too: 351 inits a
Moogle_Male with model 220 (test2_94.txt:89). **OWNER-DECIDED (2026-10-28): the moogle, as now.** B21 stands, and B22's
one-door lag now covers a scripted RemoveParty too. No engine change.

### Finding 9: the peer shows twice for about 1 s at an ATE's landing

On 350 both copies control the same undressed Vivi. Each screen spawned the peer's ghost as Vivi at the landing (laptop
20:48:24, host 20:48:25), and neither ghost hid until the first line opened: the guest's step-out went OUT on text 321 ("--
line", 20:48:25), and the host's option C rose on its own first line (20:48:26). The step-out has no landing input: in the
DEST phase s161 feeds it nothing (ATE-RELAY.md: "the scene on the destination field is an ordinary scene"), so s158's
StartRule waits for a fresh line or DwellMs 1500. The ATE landing is treated like a door arrival (THE ARRIVAL LAW). The same
window opened on 450 (guest ghost GRN 20:51:31, OUT at 20:51:32). It opens at every scene start (301, 352 night), unnoticed
where the two bodies are different characters. It is not FieldFPS: every clock on this path is `Environment.TickCount`.

**Status: BUILT, DEPLOYED, SOLO- AND DUO-BENCHED as engine patch s162 (2026-10-29); TWO-PC CONFIRMED in the fourth session ("no 2 Vivis").** `coop_ate_relay.py` S-LAND reads one
`step-out: OUT on field 350 (...) -- ate` between the copy's landed line and line 321; detail, calibrations and the gates in
`memoria-patches/README.md`, the s162 row. The duo (on the s163 DLL) reads 25/25: D10 the OUT by `ate` at the landing, D11
and D12 neither screen shows the peer on 350; its s161-DLL calibration reds exactly D10-D12, with both screens showing
the peer (the guest's from +0.91 s; the "2 Vivis"). The two-PC replay is next.

**Fix (as designed for engine round s162; built with a debounced spend and a `landing` hide reason, see the README row):** the ATE relay's own-jump landing (`NetSyncAte.OnLanding`, next phase DEST) arms a one-shot latch; StartRule
starts at once while it stands and the base holds (new reason `ate`), and the wire mask reads 0 from the landing, gated on
`eligible && !LeverOff`, so the guest's first packet on the ATE field already hides it on the host. THE ARRIVAL LAW stays for
every other landing: a DEST landing needs the host's exact pick with control still off, so it is never a door. A copy carried
in by the follow (no DEST) keeps today's window. Bench slices that cut at the first `Map: 350` (coop_ate_relay S1,
coop_ate_relay_duo D8) must re-slice at the landing line; the kit mirrors (fakegame.py out_why, the selftest row counts) move.

### Finding 10: a 3x host leaves a 1x guest behind in an ATE (Finding 4, in an ATE)

The host played "Dagger Tries" at 3x (FieldTPS 30, SpeedFactor 3; the line gaps run about 3:1). Both copies reached 450 within
a second. The host paged 153-175 in about 16 s and left at 20:51:52; the guest at 1x had shown 153-161. Its follow then
held on the tail hold, and let go at 20:52:01 by the **8 s no-progress clock** (`TailHoldMs`), not the 30 s cap: progress
counts only lines and windows, and stock 450 plays a 9 s wordless beat between texts 161 and 162 (the Old Lady walks twice
with a MoveCamera, Dagger plays Kyorokyoro_2 and Wait(45); test2_112.txt:727-738, :2775-2782). The log line says "ran past
the tail hold's cap" for either clock (NetSyncAte.cs:672-681). The guest was cut at line 162 of 175, and seqs 88-101 were
dropped as another field's. Text 162's window was briefly re-tracked over 351 after the load, which is likely why the
owner saw the ATE as "completed". The host waited about 11 s for the guest's ghost on 351.

**OWNER-DECIDED (2026-10-28): match the host's speed** (over "snap back with the host" and "let the guest finish"). Engine
round s163. Finding 4's rate relay is the cause-level fix. Mirror the host's effective field
factor on a following guest while its copy plays the host's scene or an ATE episode: an additive state section 10, a
`FastForwardFactor` seam re-asserted every tick, never writing the guest's own booster flag. Its traps, from the skeptic:
- stock SetFastForward also drives `MBG.SetFastForward`, and a type-1 in-field movie turns the booster off on the raw flag;
- `BattlePlayerCharacter` reads the factor once at a battle boot, so the scope must be read live in the getter;
- "host here with control off" cannot tell the host's scene from the guest's own climb, talk or chest;
- at equal speed the guest can now get ahead, into the exit-hold regime proven only by self-test;
- every two-PC lane was proven at 1x.
Ship the log split (which clock released the hold) either way.

**Status: BUILT, DEPLOYED, SOLO- AND DUO-BENCHED as engine patch s163 (2026-10-29), on top of s162; TWO-PC CONFIRMED in the fourth session.** As built it differs
from the sketch above: the wire carries the host's booster SETTING, not its effective factor, and the guest applies its
OWN SpeedFactor, only while its control is off (`SPEED-MIRROR.md`, The rule and Revision 3). `coop_speed_mirror.py`
reads 13/13 (host 5 above my SpeedFactor 3, so a factor of 3 is provably mine), and its `speed off` calibration reads
10/15, exactly S-ON, S-LATCH, S-BACK, S-BATTLE and S-OFF red. Design and the accepted risks: `SPEED-MIRROR.md`; detail and the gates:
`memoria-patches/README.md`, the s163 row. The log split shipped in s162. The duo (`coop_speed_mirror_duo.py`, this ATE
with the host at 3x, two real games on one PC) reads 22/22: the guest's copy reached 175 with no drop and no tail
release and was back on 351 0.39 s after the host (here ~11 s); with `netsync speed off` on the guest it reds exactly
D4-D8, the copy cut at 162 and 7.58 s late -- this finding's shape. A first duo run read 21/22, D1 red on the bench
host's own slow paging (see the README row); the host paging that passed still took ~20 s against the owner's ~16 s,
so the owner's own pace is the two-PC replay's to show. The fourth session showed it: the owner paged 162-169 in about
5 s at 3x, and the copy left 450 within about a second of the host. Finding 4's capped
follow-hold for NON-ATE scenes is still open.

### Also noticed (the owner saw none of these)

- **351's inn rest loaded 351 twice before 352.** The guest's own `Field(352)` ran while the host was mid-load, so
  `RedirectGuestFieldJump` bounced it into a 351 reload (the non-ATE pass compares only against `LastHostField`), which
  cancelled the parallel follow; the serial follow then loaded 352. The known class CLA-11 (F3.2-DESIGN.md:1029). Probably
  an extra fade.
- **A sub-second orphan chip on 352's last morning line** (text 178): `NetSyncDialog.Orphans` does not skip a window
  ApplyEvents already closed (`ClosedByUs`). Cosmetic; a fix must bound the skip, because a voiced choice departs late.
- **301's debug reload at scenario 0:** the host's same-field intent is dropped on the guest; it played in step only
  because the guest walked into an exit. Debug-only.
- **`DeclineOnceAt` latches the bounce line per field,** so "no bounce line" proves nothing on 351 after 20:45:37.

## The fourth two-PC session (2026-10-29, s162 + s163)

Both PCs ran `Assembly-CSharp.dll` `7687fb58…` (s163, which carries s162) over the relay, host GuestSlots 2, GhostAs auto,
the guest dressed as Steiner. The logs are archived in `.harness-runs/twopc-s163-20261029/` in the main repo and in
`C:\gd\SCRATCH\guest-traversal\logs\` (`desktop-host.20261029-144923.log`, `laptop-guest.20261029-145240.log`; the host
clock runs about 1-2 s ahead).

| Check | Owner | Verdict |
|---|---|---|
| 352 -> 350 "Vivi, Confused" at 1x (s162) | "no 2 Vivis" | **two-PC confirmed**: the guest's OUT by `ate` at its landing on 350 (14:55:00), a second before line 321 opened |
| 351 -> 450 "Dagger Tries", the HOST at 3x (s163) | "3x host -> guest automatically goes 3x speed" | **two-PC confirmed** (below) |
| 350 -> 351 "Cat's Eye", the GUEST at 3x (s161's exit hold, the package's step 3) | "3x guest -> waits for host's prompts" | **two-PC confirmed** (below) |
| The same "Cat's Eye" run | the guest's copy left the cat's first line while the host was still on it | Finding 11 |

**"Dagger Tries" (s163).** The guest logged an ON on 351 when the ATE menu opened and an ON on 450 at factor 3. The owner
turned the host's booster off and on mid-scene, and the guest's mirror ended ("the host's booster is off", 14:56:38) and
started again with it (14:56:41). The owner paged 162-169 in about 5 s, and every host close was applied as it arrived.
Line 175 opened locked, and the copy's own `Field(351)` came within about a second of the host's leaving (guest 14:57:05,
host 14:57:07). No line dropped and no tail hold released. The guest also turned its own booster on mid-scene: the mirror
kept the scene at 3 and the OFF line put back the guest's own value ("factor back to 3 (my own)").

**"Cat's Eye" (s161's exit hold).** The guest ran its own booster at 3 (the log reads factor 3), the host at 1x. The copy's
lines waited for the host's pages, it took its own exit to 350 first ("the host is still on field 351: the follow back into
it waits until it leaves"), and the hold ended when the host left 351 for 350. Each field loaded once each way, and the ATE
did not replay.

### Finding 11: a guest ahead of its host closes a host line itself ("Cat's Eye" on 351)

The guest's copy, at 3x, landed on 351 before the host's copy and opened the cat's first line (text 113) about 2 s after
landing (guest 14:57:17). The host's copy, at 1x, was still playing the cat's leap onto the desk, with its control off and
no window open; its scene rose about 7 s after its own landing (host 14:57:24) and closed 113 at 14:57:30. The guest's
orphan watchdog read the host as idle: no host scene since its field change, for at least `OrphanGraceMs` (2000). It
classed 113 as an orphan and closed it at reading pace (14:57:17 -> 14:57:20). Text 114 then opened and started the same
way, until the host's scene rose ("held -- the host is busy again"). The host's later close of 113 (seq 91) matched no
window and was dropped at the next field change. From 114 on, the two stayed in step.

Not an engine bug. `NetSyncDialog.OrphanSettled` (`NetSyncDialog.cs:1198`) counts the co-located host's control being
off (`HostHoldsInput`, section 7 b1) only for a script-polled line (`FlagButtonInh`); a plain line ignores it, so a host
cutscene that has not reached its first line yet looks idle. Before, a guest was rarely ahead of its host (it trails the
host's load). A guest booster makes it reachable, and so would any field-swap tightening that lets the guest arrive first.

**Status: built in s164 as item B, and two-PC confirmed in the fifth session's check 4.**

**Fix sketch (as traced before s164):** a plain locked line is not orphaned while the host stands on my field with its control
off, the same term the polled line already uses. The cost: a genuine orphan during a long host cutscene waits until the
host's control comes back. A cap needs a number to justify it; "Dagger Tries" at 3x against 1x would put the guest about
20 s ahead.

### Also noticed (the owner reported none of these)

- **Joining mid-scene.** The guest paired while the host's 351 inn scene was already past line 131. Its copy restarted the
  scene at 129, which no host event could close (the ring baselined at seq 10, after 129's close), so it sat on 129 for
  24 s while the host's 132-140 queued. All of them dropped at the follow to 352.

## The fifth two-PC session (2026-10-31, s164)

Both PCs ran `Assembly-CSharp.dll` `29f351aa…` (s164, the laptop package of 2026-10-30) over the relay, host GuestSlots 2,
GhostAs auto, the guest dressed by the host (see The guest's dress, below). The owner loaded the 351 morning save,
paired the guest on 350 (18:39:39) and warped the host to 359 at 18:40:49, as the package README asks. The logs are archived in
`.harness-runs/twopc-s164-20261031/` in the main repo (with the laptop's `Memoria.ini`) and in
`C:\gd\SCRATCH\guest-traversal\logs\` (`desktop-host.20261031-183921.log`, `laptop-guest.20261031-183920.log`; the host
clock runs about 1.5-2 s ahead). Neither log has a `field swap fault` line. The owner confirmed the Field Message speed
setting is the same on both machines.

**Analysed (2026-11-01).** Five agents read both logs end to end against the package README, the engine source at
`29f351aa` (the clone with s158-s164 applied) and the stock scripts. A skeptic then tried to refute each of the four verdict
sets, and its corrections are folded in. Every first-pass verdict held; the numbers below replace the first pass's. Cites
without a file name are to the archived logs: `host:` is `desktop-host.20261031-183921.log`, `guest:` is
`laptop-guest.20261031-183920.log`.

**The guest's dress.** The host's section 8 set it, not a guest setting. It was the moogle while the party was Zidane alone,
Steiner from the desk scene on 351 through 352's night scene (`section 8 model 5489 charId 3`, guest:168), and the moogle
again from the ATE on 350 (18:44:23, guest:365). So check 2's 352 step-out was the README's Steiner case.

| Check (package README) | Owner | Log |
|---|---|---|
| 1. Doors at 1x | (no remark) | **green.** Four doors: guest swaps #2-#5, which are host #1-#4. #16, a fifth door, ran at 1x pace inside check 3. Every start reads `fast: the screen reads visible`, and every due line ends `the screen reads black, one dialogue pass later`. Due 398-417 ms / 12 ticks, commit +399-417, landed +732-788 ms after the guest read the host's intent. The host landed 294-339 ms after its emit (the summary lines, on the swap clock). No `today's` start and no fallback anywhere in the log. Guest #1 is the pairing join, #6 follows the host's ~ warp to 359, and #7 is check 2's exit |
| 2. 359 -> desk scene -> the rest (351 -> 352) at 1x | (no remark) | **green.** One follow reached 359 (#6) and one left it (#7, no bounce). #7's intent arrived `cached on field 359 (host lane 0)` (guest:158), which is the known 359 bounce's precondition, but the follow committed before the copy ran its own `Field(351)`. The desk scene played from its first line: 129-140 were closed by host seq 7-18 in order. The rest took one load: `joining its own fade (no re-init)`, then `own Field(352) passes ... (one load)`, and the summary ends `(seen); follows 1, bounces 0, reloads 0` (guest:233). 352's three guard lines came in the README's order |
| 3. Doors with the guest at 3x | "looked good" | **green.** Seven 3x follows (#11-#15, #17, #18): due 149-150 ms / 13 ticks (#17: 14), landed 451-468 ms after the seen edge. During #16 the guest's script ticked 12 times in 400 ms, which is 30 per second, so the guest's own booster was off for that fade. The host stayed at 1x all session, and the speed mirror never applied. No line logs the guest's own booster edge. Two bounces on 352: Finding 13 |
| 4. "Cat's Eye" on 351, the guest at 3x (Finding 11) | "cat's eye was good" | **green.** 113 opened locked and was `held -- the host's control is off on my field` (guest:578). The hold ended `(a host event claims it)` (guest:580) when the host's own 113 showed in the host's open-window set, after 5100 ms on the swap stamps (the line's 5110 ms is TickCount). Then 113-117 each closed by host seq 64-68, in order. No `auto-closed` line anywhere. The guest's 113 opened at most about 5.1 s before the host's |

Neither log has a `field swap fault` line, nor any `|E|` line.

For anyone pairing the two logs by swap number: the guest's numbers run one ahead of the host's through #8, then match
from #9 to #20. Guest #1 is the pairing join, and the host's 352 -> 352 reload (host #8) opened no guest record. Swaps #11
and #17 each fold a bounce and the host's later exit into one record. Their `landed +5091` and `+20364` are counted from the
bounce, so they are not landing delays. Leave both out of landing statistics.

### What the arrival guard's X measures

**X is not a landing gap.** Both of its instants are on the guest's clock (`Environment.TickCount`):
- "My landing" is the first statement of `NetSyncSwap.OnFieldLoad`. It runs in the new scene's first HonoUpdate after
  `IsReady`, just before `StartEvents` (`NetSyncClient.cs:999`, `HonoluluFieldMain.cs:150`).
- "The host landed" is the first guest Update that read a host frame whose section 4 carries the landed bit for that nonce
  and field (`NetSyncSwap.cs:1257`, `:2041`).
- The wording only says which came first (`NetSyncSwap.cs:2133-2139`).

On every 1x follow, the host's landed frame arrived while the guest's own scene load was blocking the main thread (250-275
ms from the commit to the first post-load Update), and the first post-load Update read it. So X is the guest's own
interval from that Update to its landing hook.

All 19 guard lines (every X is a whole number of 15.625 ms TickCount ticks):
- `the host landed X ms before me`: #2 78, #3 78, #4 93, #5 78, #6 63, #7 78, the rest #8 94, the 352 reload at 18:43:52 62
  (no swap number), #16 94.
- `the host's landing reached me X ms after mine`: the copy's own `Field()` entries #9 172, #10 156, #19 391; the 3x
  follows #11 140, #12 63, #13 125, #14 79, #15 125, #17 187, #18 93.

**The real two-PC landing gap.**
- **Method.** For each nonce, d = the guest's swap-clock stamp of its first line naming the nonce, minus the host's stamp of
  `transition intent -> field F (nonce N)`. Over the 18 nonces where the guest was not mid-load, d = 1100792342-1100792390
  ms, so the clock offset is at most 1100792342. A round trip bounds it from below: the host spawned the guest's ghost on
  352 within 18:47:08 (host:204), after the guest landed at t 1178020809, so the offset is above 1100792111. The one-way
  latency is therefore 0-231 ms, or at most 116 ms if both directions are equal.
- **1x doors (#2-#5, #16):** at least 439-503 ms, median 479, plus the latency: about 0.44-0.62 s. The duo's median was
  426.5 ms (375-461), so the real link adds at least about 0.01-0.08 s plus the latency. It is still about half of s163's
  0.93-1.04 s.
- **The rest (#8):** at least 357 ms. **3x doors:** at least 116-186 ms.
- The same mappings put the host's system clock 1678-1909 ms ahead of the laptop's. The transport probe wrote no lines: it
  logs only on a swap's close.

**The late anchor.** The sign split is where the design puts it. The in-time wording appeared on gaps of about 0.36 s or
more, and the late wording on gaps of about 0.19 s or less (`ARRIVAL-GUARD-S164.md:28-31`). But the in-time wording does not
mean an in-time read. On every 1x follow, the anchor waited out the guest's own load. It sat 332-383 ms plus the latency
after the host's real landing (231 ms plus the latency on the rest), against the 50-90 ms the duo measured. A wordless
step-out on a 1x door would therefore come about 2.87-2.92 s plus the latency after the host's landing. That is about 0.24-0.33 s
later than an in-time anchor would give. The design already accepts that a late anchor means more suppression, bounded by
the cap, and no arrival this session showed it on screen.

**352's dwell.** The OUT came at landing + 2477 ms. The rule predicts + 2446 ms (the read tick + 2540); the extra 31 ms is one
frame step plus tick rounding. 2.48 s is the README's "about 2.5 s minus X", at the top of the desktop's 1.9-2.5 s.
Measured from the host's landing, it is about 2.80 s plus the latency.

**The s164 row's NOT PROVEN list, against this session:**
- **The two-PC follow gap:** measured, as above.
- **`arrive.lead_ms`'s sign:** measured, with the meaning corrected as above.
- **The laptop's Unity order:** read on 18 loads as a guest: `NetSyncClient.Update` runs before the per-scene
  `HonoBehaviorSystem.Update`. The strongest evidence is the own passes: #8 and #10 cleared the intent cache 256 and 253 ms
  after the pass, and the other order would clear it within one frame. Its consequence for a laptop host (LIFE under `swap
  life old`) is not reached; that needs the laptop to host.
- **Risk 14's band:** not reached. Doors gave control back 143-230 ms after landing, 352's night scene stepped out, and the
  ATE entries stepped out by `ate`. Given the late anchor, the band on 1x doors runs about 2.54 s to 2.9 s plus the latency.

Still open: the host's delay from its landing hook to its first landed frame (it publishes about every 164 ms), and the
link latency. A host line stamped on the swap clock when it builds its first landed frame, the guest's read on the swap
clock, and a logged round trip would settle both.

### Finding 12: the guest held a line about 2.2 s after the host closed it: a 2.3 s link stall ("Vivi, Confused", 350, at 1x)

The owner: a couple of lines into the ATE, they closed a line just before the children run away. The guest kept that line up
and played the run only later, at about the host's next close, as they recall it.

**Cause (confirmed): a 2.3 s link stall in both directions. It is not a speed, font or frame-rate effect.** For each host
close, K = the guest's ingest stamp minus the host's tap stamp. That is the clock offset plus the one-way latency. Over the
whole session K sits in a 46 ms band, 1100792346-1100792392, median 1100792373:

| Seq (text) | Host tap | Guest ingest | K vs the median | Guest apply |
|---|---|---|---|---|
| 54 (98, a choice) | host:165 | guest:355 | +9 ms | waited 9 ms |
| 55 (100) | host:166 | guest:359 | -11 ms | waited 0 ms |
| 56 (322) | host:177 | guest:378 | +19 ms | waited 366 ms, shown 816 ms |
| **57 (323)** | host:178 | guest:384 | **+2175 ms** | waited 0 ms, shown 5100 ms |
| 58 (324) | host:180 | guest:387 | -15 ms | waited 0 ms, shown 2217 ms |
| 59 (325) | host:181 | guest:390 | -4 ms | waited 0 ms, shown 4734 ms |
| 60 (324) | host:182 | guest:393 | +3 ms | waited 0 ms, shown 3150 ms |

- **323: +2175 ms late.** The first pass's +2.2 s holds. On time, 323 would have shown for about 2925 ms instead of 5100 ms.
- **322 was on time.** The first pass's +0.4 s is overturned. The 366 ms is the guest's readability floor: a host close
  fast-forwards a page that is still typing, then waits `MinShowMs` 350 ms from its completion (`NetSyncDialog.cs:51`). That
  is why the waits cluster at 366, 367, 383 and 384 ms all session.
- **The stall.** The guest calls the host silent once the position lane is more than 2000 ms stale, and "back after 344 ms"
  counts from that moment (`NetSyncClient.cs:4102`, `:4127`). So the guest received nothing for about 2344 ms. The last frame
  that got through left the host about 168 ms before the 323 tap, and 2344 - 168 = 2176, which matches seq 57's lateness.
  The guest applied the close in the same update it arrived in, so nothing on the guest added delay. The relay writer is its
  own thread, re-sending the latest slots every 33 ms (`NetSyncRelay.cs:265-277`), so a hitch in the host's game thread
  cannot cause this.
- **The other direction.** The host has no outage clock, and its ghost despawns without a line. Its re-spawn of the
  guest's ghost at 18:44:38 (host:179) is the only host re-spawn this session that matches no field event on either log. That
  fits a guest-to-host stall of over 2000 ms (inferred: a null host control actor or a field mismatch would also despawn it).
- **Where.** Both games dial `ws://127.0.0.1:49201`, a ws-to-wss bridge on each PC that forwards to the public relay. "The
  hop is up" means only the guest game's loopback link to its own bridge, so the stall sat further out. The bridge's own
  notes record upstream EOFs from a relay wobble, and on a redial it drops game-to-relay frames rather than queueing them
  (`netsync_bridge.py:20-24`, `:97-99`). That is the leading candidate. These logs cannot tell. The desktop's bridge-log
  folder holds only 2026-10-15 files; the laptop's was not checked.
- **The settings** (the laptop's `[Font] Enabled = 1` and `FieldFPS = 120`) are ruled out. The delay came before the close
  reached the guest, and those settings act only after.

**Which line, and the run.** It was 323, Gudo's line in window 6 (`test2_93.txt`). Two of the three children run off while
323 is still up, on both copies: the girl (case 16) and the other boy (case 17). Only Gudo's own run waits. It is case 18,
which needs the beat to reach 18 and then `WaitWindow(6)`. So the guest held back Gudo's run. On the guest it ran about 2.2 s
late, ending about 2.2 s before the host's next close. The guest caught up at that close: the host's close of 324 arrived on
time, so the guest showed 324 for only 2217 ms. So the owner's "at about the host's next close" describes the catch-up, not
when the run played. When the host's own run started is not known: the host logs no opens or beats.

**Is a 2 s hiccup normal here?** Across all five two-PC sessions (about 53 minutes paired), the guest logged 4 outages
mid-session, each a total silence of about 2.16-2.34 s:
- 10-27 15:07:34 (back after 172 ms): it delayed a host intent;
- 10-28 morning, 10:59:59 and 11:00:59, 60 s apart (156 and 188 ms): the first delayed a close;
- 10-31 18:44:36 (344 ms): this one.

10-28 evening and 10-29 logged none, though the first ~3 minutes of 10-29's pairing have no archived guest log. So about one
stall every 13 minutes is this link's norm so far, not an s164 regression. A stall longer than about 5 s would free the
guest to close the line itself: the lock lets go once the link reads dead for 3 s past the 2 s staleness.

**Open.** Where the stall sat: the bridge consoles from both PCs, the relay's log for 22:44:34-38 UTC, or an engine line on
both roles for any inbound gap over about 500 ms would settle it. How long the guest-to-host stall lasted. Whether 10-28's
60 s spacing repeats.

### Finding 13: the guest walked into 352's exit twice and was bounced, as designed

Twice the guest's copy took its own `Field(351)` on 352 while the host still stood on 352 (guest 18:46:58 and 18:48:46).
The guest read the host's own exits 4635 ms and 19902 ms later, and each bounce reloaded 352 on the guest in 302 and 317 ms.

**The path.** A script's `Field()` (MAPJUMP) calls `RedirectGuestFieldJump` on a following guest. No ATE verdict printed, and
s164's own pass found nothing to match: no follow was pending, the host had no live intent, and nothing was cached for 351.
351 was neither the guest's field nor the host's lane, so the copy bounced to a reload, as it has since s163. The
`gateway (bounced to a reload) suppressed` line printed only before the first bounce. Its latch keeps the last field per
class and never re-arms, so a second bounce on the same field prints only s164's `swap: own` line.

**Which call.** 352 has three `Field(351)` sites (`test2_95.txt`):
- ATE choices +3 and +4 (:403, :433). Excluded: a following guest's own Select is masked (`NetSyncField.cs:905-911`), and no
  ATE serve line appears near either bounce.
- `Region14_Range` (:1107), the south door. It needs only control, then runs a 24-frame fade to black, `Wait(25)`, sets
  entrance 6 and calls `Field(351)`.

So it was the door. That is an inference by elimination: no line names the runner.

**What put the body in the door.** Entrances 2 and 6 place the body at (-16, -720), about 43 units north of the door's
polygon (top vertex (8, -756)). The engine tests the region every tick while control is on. A body placed inside would have
fired as soon as control came back. Instead the bounces came 121 s after #10's landing and 47 s after #16's, so the body was
moved there long after it landed. The candidates:
- **netsync movers:** a teleport would log a line, and AutoTeleport is off in the laptop's ini. Excluded.
- **the host's ghost:** a bare model with no actor, so it cannot push. Excluded.
- **stock scripts:** no 352 code at entrances 2, 6 or 17 walks the player. Zidane_Loop's stale case 2 does place him inside
  the door, but it opens window 4 and runs at landing. Excluded.
- **the self-dress and the booster:** the region test reads position only. Excluded.
- **the laptop's own movement input:** this remains. Both bounces fall in windows where the laptop's player switched the
  booster on: 1x at #7 (18:41:47) then 3x at #11 (18:47:03), and 1x at #16 (18:47:58) then 3x at #17 (18:49:05). So someone was
  at the laptop each time. Check 3 also says "Walk a few doors", and one short press south from the spawn reaches the door.

No line records local input, so this is the best-supported reading, not a proof. **It is not a copy-ahead and not an s164
regression.** Any following guest who walks into a gateway has been bounced this way since F1. No earlier session bounced on
352. 3x did not cause the trigger; at most it carried a walking body farther per second.

**Harm.** One fade to black and a 0.3 s reload. Main_Init re-runs the music, the ambient sound, the chests, the regions and the
ATE mask. The counter stays 2600, and no story byte changes.

**Owed.** The owner's word on whether the laptop's player walked on 352. For the next build: the own-jump line could name the
runner (cid, sid, tag), the body's (x, y), the control state, whether a direction key was down recently, and the booster flag.
Then one line would tell a guest's walk from a scripted placement.

### Backlog from the owner (not s164 regressions; traced, unverified)

- **14. 351's drawn door does not play its open animation on the guest** when the host walks through it.
  - **Cause.** The door is a tile animation, `RunTileAnimationEx(0, 0, 4)`, started in 351's `Region18_Range`, the gateway to
    352 (`test2_94.txt:3144-3205`, the call at :3183). The engine runs a region body only for the controlled player
    (`EventEngine.ProcessEvents.cs:187-191`). On the guest that is the guest's own body. The host's body there is a bare
    `CreateModel` ghost, not an event actor (`NetSyncClient.cs:90-94`), so the guest's copy never runs `Region18_Range` for
    the host. The host's intent leaves only at the `Field()` commit, after its door animation and fade. The first crossing
    (the scripted inn walk, #8) ran on the guest's own copy, and its script starts the door too (:3394). So the free walks
    (#12, #14, #16) are the likely cases; which crossing the owner saw is unconfirmed.
  - **Fix model.** It is the s160 chest relay's cause again: a tag-2 `_Range` body that runs only for the player. Model the
    fix on that relay. The host stamps the moment its copy enters the region, and the guest plays the animation before its
    follow fade reads black.
  - **Reach.** At most 85 of the 817 exports have a region body with both a tile animation and a `Field(`.
  - **Scope.** Cosmetic only.
- **15. The guest waits out the full 40 s grace when the host quits on purpose** (host quit 18:50:32; the guest ended the
  session at 18:51:13, `silent for 40015 ms, past the 40 s grace`, then the exit ramp reloaded its own autosave).
  - **Cause.** The host's deliberate quit sends nothing. The path runs `ConfirmQuit`, `Application.Quit`, then
    `RaiseQuitEvent` (`UIKeyTrigger.cs:412-432`), and NetSync does not subscribe to `GameLoopManager.Quit`. The relay
    transport's `Stop` closes the stream with no close frame (`NetSyncRelay.cs:93-97`). The wire has no session-end type
    (`NetSyncSocket.cs:193-200`; `NetSyncEnd.cs` is the battle end block). The relay parks the dropped leg for its 60 s
    rejoin, and the guest's own link stays up, so the guest sees an ordinary outage.
  - **The cheap half.** At the quit, the host pushes one in-band session-end word out of band. The guest takes it straight into
    the existing give-up and exit ramp. It has to be in band, because the guest's bridge redials and would hide a relay
    close. A missed word falls back to today's 40 s, so it fails safe. It may need a flush before the window is destroyed.
  - **The guest-menu work.** `GUEST-MENU.md` has no quit or leave decision, so the word can ship before it. A guest
    choosing to leave during a grace stays with the menu work.

### Next

1. **The owner:** did the laptop's player walk the guest on 352 during check 3 (Finding 13)? If not, Finding 13 is a real
   defect and needs the runner line above.
2. **Log-only asks for the next engine round:**
   - a line on the guest's own booster edge (`UIKeyTrigger`, `PauseUI` and `BoosterSlider` toggle it silently);
   - the own-jump runner line (Finding 13);
   - an inbound lane-gap line on both roles for any gap over about 500 ms, on the swap clock (Finding 12);
   - a host swap-clock stamp on its first landed frame (the arrival guard).
3. **Queued in the round queue:** 14 as its own item (a door relay modeled on s160), and 15's session-end word, which does not
   wait for the guest-menu work.
4. **Still not reached:**
   - the laptop as host (LIFE under `swap life old`);
   - risk 14's band;
   - the s158 shape on a real link (an own jump before the intent);
   - the emergence scene (Finding 3).

## Order of work

1. **One engine round: Finding 2's twin rows plus Finding 1's frame on the ghost lane.** Bench solo first: the
   selftest role with `selfdress self steiner` on a 207 ladder and the 408 jumps, judged by a twin counter, the
   harness `rig` read and `game_snap` stills, and made red by a lever. Then two-PC on 114 undressed and 207/408
   dressed, one change per test.
   **Status: BUILT, DEPLOYED and SOLO-BENCHED as engine patch s157 (2026-10-28).** `coop_climb_anim.py` reads
   21/21, each lever's calibration reds exactly its predicted rows, and the s156 DLL reds the four twin rows on
   the idle alias; the wire half `coop_climb_anim_peer.py` reads 9/9 (s156: 3/5). The stills show Steiner gripping
   the 207 rungs and kicking through his own jump on 408, where s156 stood him upright. Detail and the gates:
   `memoria-patches/README.md`, the s157 row. **Two-PC confirmed (2026-10-28):** 114 undressed and 207/408 dressed
   "looked good".
2. **The party-scene step-out** (Finding 3, A+C+E), after the owner's taste call.
   **Status: BUILT, DEPLOYED and SOLO-BENCHED as engine patch s158 (2026-10-28), on top of s157.**
   `coop_step_out.py` reads 12/12, and its lever calibration reds exactly its three predicted rows. The stills show
   only Zidane on the 207 rungs while a Steiner-dressed guest is stepped out. Detail and the gates:
   `memoria-patches/README.md`, the s158 row. **Two-PC (2026-10-28):** 359 worked; 352's night scene kept the guest's
   Steiner in Zidane's part (Finding 6); a post-dialogue jitter is open (Finding 7); the emergence scene is untested.
   **s159 (2026-10-28): the step-out anchors on the dressed body; built, deployed and solo-benched (M-352 green, both
   calibrations exact). Two-PC confirmed in the third session.** **s162 (2026-10-29): Finding 9's landing start; built,
   deployed and solo-benched (S-LAND green, its noland calibration exact); duo 25/25 on the s163 DLL, its s161-DLL
   calibration exact. Two-PC confirmed in the fourth session.**
3. **The host's field rate on the wire, plus the capped follow-hold** (Finding 4; seen again in an ATE as Finding 10).
   **s163 (2026-10-29): the rate half -- the host's booster setting on the wire (state section 10) and mirrored on a
   following guest during the host's scenes; built, deployed and solo-benched (13/13, its `speed off` calibration exact);
   duo 22/22, its calibration exact. Two-PC confirmed in the fourth session.** The capped follow-hold for non-ATE scenes
   is not built.
4. **The same-field reload** (Finding 5): backlog. It has real stock cases, so it is not only debug hygiene.
5. **Field-swap timing, second pass** (the owner, after the fourth session): the guest's copy starts a scene about 1 s
   behind the host's after a field change, and stays behind until the host rests on a line. Designed in
   `FIELD-SWAP-TIMING.md`: about 90% of it is the guest's 0.9 s follow timer, which starts only after the host's own
   fade has ended; plus a bounce reload on 2 of the 5 scripted Dali exits.
   **s164 (2026-10-30): round 1, built, deployed, solo- and duo-benched. Two-PC run in the fifth session (2026-10-31),
   analysed 2026-11-01: checks 1-4 green; the 1x door gap is at least 0.44-0.50 s plus the link latency.**
6. **Finding 11's orphan hold** (a guest ahead of its host): **built in s164 (item B); two-PC confirmed in the fifth
   session's check 4.**
7. **Queued after the fifth session:** 14, a door relay modeled on s160; and 15, a session-end word on the host's quit.
