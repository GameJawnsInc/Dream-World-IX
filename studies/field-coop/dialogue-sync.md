# Dialogue / ATE / cutscene real-time mirroring — ground truth + divergence census + design ladder

> Scope: read-only research for the co-op lane that would make a FOLLOWING guest watch the SAME
> dialogue lines, at the SAME advancement pace, with the SAME choices, as the HOST — not just "run
> the same script off mirrored flags and hope the two copies agree." No code changed by this pass.

---

## 1. Ground truth

### 1a. How a dialogue window blocks the `.eb` script, and how confirm closes/advances it

**The block is a per-object byte, not a script-level wait primitive.** `MES`/`WindowSync` (`0x1F`,
`EventEngine.DoEventCode.cs:410-459`), `MESA`/`WindowSyncEx` (`0x95`, `:506-518`) and `WAITMES`
(`0x54`, `:569-580`) all end by setting `this.gCur.wait = 254; return 1;` — `gCur` is the **calling
object's own stack-frame entry** (an `Obj`/`PosObj`/`Actor`), not the engine as a whole; only *that*
object's script thread stalls. The window is actually created a few lines earlier by
`ETb.NewMesWin(textID, winnum, uiFlags, po)` (`ETb.cs:91-165`), which calls
`DialogManager.AttachDialog(...)` (`DialogManager.cs:99-159`).

The unblock check runs once per object per frame in `EBin.ProcessCode`'s tick
(`Global/EBin.cs:136-157`):
```
if (s1.wait == 254)                              // "wait for a window to close"
    if (s1.winnum == 255) s1.wait = 0;
    else if (!ETb.MesWinActive(s1.winnum)) { s1.winnum = 255; s1.wait = 0; }
```
`ETb.MesWinActive(num)` (`ETb.cs:204-207`) is `DialogManager.Instance.CheckDialogShowing(num)`
(`DialogManager.cs:176-182`) — a linear scan of `activeDialogList` for a `Dialog` whose `.Id ==
winnum`. So the block clears the instant that specific window is no longer in the active list.

**The confirm key path** (local input → window close), traced end to end:
1. `UIKeyTrigger.HandleDialogControlKeyPressCustomInput` (`UIKeyTrigger.cs:798-838`) reads the
   LOCAL machine's `HonoInputManager`/`Configuration.Control.DialogProgressButtons` and, on a
   confirm edge, calls `PersistenSingleton<UIManager>.Instance.Dialogs.OnKeyConfirm(activeButton)`
   (`:807-810`).
2. `DialogManager.OnKeyConfirm` (`DialogManager.cs:335-341`) fans out to
   `dialog.OnKeyConfirm(go)` for every dialog in `activeDialogList`.
3. `Dialog.OnKeyConfirm` (`Dialog.cs:731-785`): if `currentState == CompleteAnimation` (text fully
   printed) it calls `this.Hide()` (`:772-773`) unless choices are still resolving. If the text is
   still typewriter-animating (`currentState == TextAnimation`), the SAME confirm instead
   fast-forwards the print (`CurrentParser.AdvanceProgressToMax()`, `:780-784`) rather than closing
   — so a "confirm" on a still-printing window and a "confirm" on a fully-printed window do
   different things, both reachable from the identical key press.
4. `Hide()` → (animation) → `Dialog.AfterHidden()` (`:674-686`) →
   `DialogManager.ReleaseDialogToPool` (`:679`, removes it from `activeDialogList`) — this is the
   moment `CheckDialogShowing` starts returning false and the blocked `.eb` entry's `wait` clears
   on the next `EBin` tick.

### 1b. How a CHOICE works (`GetChoose`)

- **Setup, before the window opens:** `CHOOSEPARAM`/`EnableDialogChoices` (`0x7C`,
  `DoEventCode.cs:1943-1949`) calls `ETb.SetChooseParam(availMask, defaultChoice)` (`ETb.cs:248-260`),
  which stores static `sChooseMask`/`sChooseInit`. `NewMesWin`/`InitMesWin` (`ETb.cs:100-104`,
  `:21-29`) fold that into `sChoose` for the next window unless the `ResetChooseMask` window flag
  says otherwise.
- **Which lines are choices** is parsed OUT OF THE TEXT ITSELF: `Dialog.HasChoices` (`Dialog.cs:29-36`)
  runs `CurrentParser.Parse(TextParser.ParseStep.ChoiceSetup)` and checks `startChoiceRow >= 0` — an
  in-line text opcode (`[INIT_MULTICHOICE]`-class), not a separate opcode call.
- **Building the choice widgets:** `Dialog.InitializeChoiceProcess` (`Dialog.cs:106-166`) creates one
  `GameObject` per available (non-`disableIndexes`) line, wires them into `ButtonGroupState`/
  `UIKeyNavigation` (the SAME generic focus-navigation system every other menu uses — arrow input
  moves the highlighted button, not a bespoke choice-nav codepath), and calls
  `SetCurrentChoice(defaultChoice)` (`:162`).
- **Navigating** = ordinary UI focus movement (`MoveCurrentChoice`, `Dialog.cs:189-198`, driven by
  drag/analog in `DialogManager.OnDrag` at `:321-333`, or by focus-key input through
  `UIKeyNavigation`) or a direct tap (`Dialog.OnItemSelect`, `:805-815`,
  `SelectChoice = choiceList.IndexOf(go)`).
- **Where the chosen index is stored:** `Dialog.SelectChoice`'s setter (`Dialog.cs:59-76`) ALSO
  writes the static `DialogManager.SelectChoice` (`:74`, backing field `DialogManager.cs:492`) — a
  single global slot, not one per dialog (matches the PSX one-active-choice-window model).
- **Confirming a choice:** `Dialog.OnKeyConfirm` (`Dialog.cs:757-773`), when `HasChoices`, sets
  `this.SelectChoice = choiceList.IndexOf(ButtonGroupState.ActiveButton)` (`:770`) — i.e. it commits
  whatever is currently highlighted — then `Hide()`s.
- **Where the script reads it:** `B_SYSVAR` code `9` → `EventEngine.GetSysvar(9)` →
  `ETb.GetChoose()` (`EventEngine.GetSysvar.cs:37-38`; `ETb.cs:262-268`), which reads
  `DialogManager.SelectChoice` into `ETb.sChoose` and returns it. This is evaluated strictly AFTER
  the `wait==254` block clears (the window is already closed by the time the `.eb` gets back control
  and evaluates the expression that calls sysvar 9).

### 1c. `B_KEYON` — what it is, every consumer found

`B_KEYON` is expression opcode **79** (`EBin.cs:2509`; handler `EBin.cs:1078-1084`):
```
_v0 = (Mathf.Abs(EvaluateValueExpression() & ETb.KeyOn(japaneseSwap)) <= 0) ? 0 : 1;
```
It is a **press-edge bitmask test read from the LOCAL machine's own input this frame**. `ETb.KeyOn()`
(`ETb.cs:65-70`) reads static `ETb.sKeyOn`, computed once per frame in `ETb.ProcessKeyEvents`
(`ETb.cs:50-56`) from `FPSManager.DelayedInputs` — i.e. this machine's controller/keyboard state,
never anything received over the wire. Consumers found:
- The `.eb` script itself, via the `B_KEYON` RPN token — the documented ATE "Press SELECT" gate
  (`if (usercontrol==1 && avail==1 && 1 B_KEYON)`, per `project-ff9-ate-system.md`) and other
  poll-loop input gates (ladders/jumps per that memory file).
- `EventCollision.CheckQuadInput`/`CheckNPCInput` (`EventCollision.cs:60-83`, `:85-...`): both gate
  the **talk (tag-3/mode-4 quad or NPC)** trigger on `ETb.KeyOn() & (Confirm|Special)` being nonzero
  THIS FRAME, in addition to a position/proximity test — position alone is not sufficient for a
  talk-triggered cutscene.
- `EIcon.ProcessHereIcon` (`EIcon.cs:357-365`): `instance.GetUserControl() && (ETb.KeyOn()&1)>0` —
  the "here" talk-prompt bubble flourish, not story-relevant.
- `B_KEYON2`/`B_KEYOFF2`/`B_KEY2` exist as a second variant (`EBin.cs:551-553`,
  `DoCalcOperationExt.cs:62-66`) but their handler only consumes the argument and returns 0 — inert
  stubs in this build, not a real consumer.

Tag-2 **tread** triggers (auto-fire, no confirm) are the other half of the picture: every field tick,
`instance.TreadQuad(po, 2)` (`EventEngine.TreadQuad.cs:6`, called from `EventCollision.cs:281`) tests
the controlled actor's CURRENT position against the region geometry and, if inside AND
`Request(obj, 1, 2, false)` succeeds (`EventEngine.cs:336-346`, gated on the object's own execution
`level`, not on a walked-in/out edge), calls the tag. This is a fresh containment test every frame —
it does not care whether the actor arrived by walking or by being placed there.

### 1d. ATEs — trigger/run mechanism, mode 1 vs mode 6, parallel entry or not

**No parallel engine.** Per `project-ff9-ate-system.md` (verified against `EIcon.cs`/`ETb.cs`/
`ActiveTimeEvent.cs`): the engine contributes exactly three things — the blinking HUD icon
(`AICON`/`0xD7` → `EIcon.SetAIcon`), the `winATE=64` window flag (`ETb.cs:179-180`, makes an ordinary
`MES`/`MESN` window render with `CaptionType.ActiveTimeEvent`), and post-hoc achievement bookkeeping
(`Dialog.AfterHidden` → `ETb.ProcessATEDialog`, `ETb.cs:408-434` → `EMinigame.MappingATEID`/
`ATE80Achievement`). **Everything else — the trigger gate, the menu, the branch dispatch — is
ordinary field `.eb` code run by the SAME `EventEngine.ProcessCode` loop as any other entry.** An ATE
is not a special execution mode; it is a normal poll-loop or region/gateway-triggered function that
happens to open `winATE`-flagged windows.
- **Mode 1 (blue, optional):** the icon renders only with `GetUserControl()==true` (no force bit) —
  i.e. drawn only while the player is free to act. The player's accept input is the exact same
  `B_KEYON(SELECT)` + `GetChoose()`/`op_0B` jump-table mechanism as 1b, just wrapped in a
  `winATE`-captioned window. Opening the menu is a normal talk/poll-loop trigger, not a separate
  input channel.
- **Mode 6 (grey, forced):** NOT a menu at all — a scripted WARP-IN under a `DisableMove` lock
  (`ATE(6) → Wait → FadeFilter → ATE(0) → WindowAsync(0,64,txid) → Field(N)` per the memory file,
  itself grounded in `EIcon.cs:416-474`). `WindowAsync` (`MESN`/`0x20`, `:461-505`) never sets
  `gCur.wait`, i.e. it auto-advances — there is no blocking accept input for the forced flavor at
  all.

### 1e. A cheap, per-frame, comparable "where the script is" identifier

Three candidates, cheapest first:
- **`(Dialog.Id, Dialog.TextId)` of the currently open window** — `Dialog.Id` is the window slot
  (`== gCur.winnum`, a small int 0-9) and `Dialog.TextId` is the mesID (data-driven, byte-identical
  on both machines since it comes from the same field's `.mes`). Already exposed by
  `DialogManager.GetDialogByWindowID`/`GetDialogByTextId` (`DialogManager.cs:406-412`, `:459-465`)
  and already used as an identity check by `ETb.ProcessATEDialog` (`ETb.cs:408-434`, compares
  `dialog.Id`/`dialog.TextId`). Two small ints — this is the natural alignment key.
- **`(Obj.sid, Obj.ip)`** — the calling entry's script id + byte instruction pointer, i.e. its actual
  program counter. Directly referenced by real special-cases in source (`this.gCur.sid == 19 &&
  this.gCur.ip == 1849`, `DoEventCode.cs:571-576`; `this.gCur.sid == 1 && this.gCur.ip == 145`,
  `:451`). Finer-grained than the window id/textId pair, but only meaningful once the two machines
  are actually running the SAME call — it doesn't establish that on its own.
- **`ETb.gMesCount`** (`ETb.cs:499`, incremented every `NewMesWin`) — a coarse monotonic
  "Nth window opened this field-load" counter. Cheap but not specific enough to name a message.

**Recommendation for any mirroring design: `(fldMapNo, winnum, textId)`.** It is already computed,
already exposed, and — critically — is the SAME triple `ETb.ProcessATEDialog` already trusts for
identity, so there is in-tree precedent for treating it as a safe comparison key.

---

## 2. Today's divergence census

### (a) Host walks into a forced cutscene trigger the guest hasn't touched

The guest's controlled actor has not entered the guest's own copy of the trigger region — nothing
about the host's local `UCOFF`/`Request()` call reaches the guest's `EventEngine` (the only
guest-visible channel is the position/anim broadcast). Concretely:
- **The guest keeps free control.** `usercontrol` (`EventContext.usercontrol`, `EventContext.cs:132`)
  is a per-`EventEngine`-instance field; `UCOFF`/`0x2D` (`DoEventCode.cs:1026-1042`) only flips the
  HOST's copy. The guest's own `_context.usercontrol` is untouched.
- **NPCs on the guest's field keep running their own idle/wander scripts** — NPC state is never
  ghost-broadcast (only the host's CONTROLLED actor is, per `NetSyncSocket.cs:13-25`'s
  `RemoteState`), so any NPC the host's cutscene is choreographing appears untouched/idle on the
  guest's screen.
- **The ghost still pantomimes**, because the broadcast is "whatever the host's controlled actor is
  doing this frame" — cutscene `MOVE`/anim opcodes still drive that same `Actor`, so the ghost walks
  the choreographed path and plays the cutscene animations, but with **no dialog window** (dialog
  state is 100% `DialogManager.activeDialogList`-local, never broadcast) and, per the point above,
  often opposite an NPC that isn't doing its half of the scene. The visible result is a ghost
  talking to nobody, or walking a path the guest's own NPCs don't react to.

### (b) The guest later walks the same trigger — fires out of sync locally

Whether this "self-heals" depends entirely on the flag SCOPE the cutscene's once-gate uses (GLOB
`gEventGlobal` vs MAP per-field-instance — see `project-ff9-story-flags.md`):
- **GLOB-gated once-flag:** the STATE MIRROR (`NetSyncClient.ApplyStoryImpl`, `:207-247`) overwrites
  the guest's ENTIRE `gEventGlobal` from the host's snapshot at the guest's NEXT field-load boundary
  (`ApplyStoryBeforeEvents`, called from `HonoluluFieldMain` before `ee.StartEvents` per the class
  comment at `:196-200`). If the host's cutscene set that GLOB flag, the guest's local trigger will
  read "already done" the next time it loads this field and silently skip — this is the "self-heal"
  case, though what actually happened is "the guest never got to watch its own copy at all," not
  "the two copies converged."
- **MAP-scoped once-flag** (the more common shape for a single-field one-shot, per the GLOB-vs-MAP
  split in `project-ff9-story-flags.md`): NEVER mirrored — `EventContext.mapvar` and per-field
  MAP-band flags are entirely outside the mirror's `gEventGlobal`-only scope. The guest's local copy
  fires FRESH regardless of what the host already did — an independent, permanently unsynced replay.

### (c) Choices: host picks X, guest's copy never ran or could pick Y

`DialogManager.SelectChoice` is a machine-local static, never transmitted. If/when the guest's own
copy of the SAME choice window independently triggers (per (a)/(b)), it resolves off the guest's own
local `ButtonGroupState`/input — nothing stops it from landing on a different index than the host's.
What diverges, and its lifetime:
- **A GLOB-flag consequence of the choice** — self-heals (gets silently overwritten) at the guest's
  next field-load-boundary state-mirror, same mechanism as (b).
- **A MAP-scoped/`EventContext.mapvar` consequence** — never mirrored, never self-heals; the guest's
  field-local state can permanently disagree with the host's for that visit (only a genuine field
  reload, which re-runs `Main_Init` from flag-zero, resets it — not the story mirror).
- **Achievement bookkeeping specifically for ATEs** (`AchievementState.AteCheckArray`, per
  `project-ff9-ate-system.md`) lives in a SEPARATE state container from `gEventGlobal` and is never
  touched by the mirror at all — permanently host-only/guest-only, not just "until next load."

### (d) ATEs: host accepted, guest didn't

Same divergence class as (c) — an ATE accept is the same `GetChoose`/`B_KEYON` mechanism. Two extra
wrinkles specific to ATEs:
- A mode-1 hub typically `Field()`-warps away to a destination cutscene field on accept. If
  `FollowHost` is on, the guest's follow-warp will chase the host into that destination field, and
  THAT field-load IS a mirror boundary — so a GLOB-scoped ATE-accepted flag self-heals right there,
  even though the hub field itself never re-synced. Any MAP-local gate on the abandoned hub instance
  is just left behind (the guest's own hub `EventEngine` context is torn down on field change).
- `EMinigame.ATE80Achievement(ateID)` (`ETb.cs:419`, inside `ProcessATEDialog`) runs on **any** local
  dialog close with a `winATE` caption — there is no `IsMirroringStory` gate on it today. This means
  an unsynced guest independently clicking through its own copy of an ATE can file a REAL Steam
  achievement report, the same class of un-retractable write the Road A note already flagged for
  `FF9Item_Add → ... → ProcessAchievementReport` (`project-ff9-multiplayer-injector.md:667-671`,
  `inventory-authority.md:19-44/259-265`) — worth carrying into any future containment pass even
  though this document doesn't propose closing it.

**Summary — self-heals at next guest field-load vs. never:**
| Divergence | Self-heals? |
|---|---|
| GLOB/`gEventGlobal` story flags (any dialogue/choice/ATE consequence) | Yes — wholesale overwritten by `NetSyncState.ApplyStory` |
| MAP-scoped/`EventContext.mapvar` flags | Never — outside the mirror's byte range entirely |
| `AchievementState.AteCheckArray` / Steam achievement reports | Never — a different container / already left the machine |
| The guest's own already-played-out camera/actor motion, once its local copy has run | Never — already visually happened |
| The ghost's silent pantomime of a host-only cutscene | Resolves the instant the host's local trigger ends (reverts to normal ghost mirroring) — but the guest never watched a synced scene; nothing "fixes" that after the fact |

---

## 3. Design ladder

### L0 — status quo

As censused in §2. Ships today, zero new work. Keep as the fail-safe floor every other rung degrades
to.

### L1 — CO-LOCATION + LOCAL RUN

**Predicate candidate (host side):** `EventEngine.Instance.GetUserControl()` — a public accessor
(`EventEngine.cs:1415-1418`) over `_context.usercontrol` (`EventEngine.cs:624` zeroes it at
`StartEvents`; toggled by `UCOFF`/`0x2D` and `UCON`/`0x2E`, `DoEventCode.cs:1026-1062`). `gMode`
itself is USELESS as the signal — it stays `1` for the field's entire lifetime (`EventEngine.cs:579-581`)
regardless of cutscenes; `usercontrol` is the real "the script took the wheel" bit.

**Caveat found in source, not resolvable from source alone:** `usercontrol` ALSO drops to 0 on an
ordinary gateway crossing — `MOVQ`/`ExitField` (`0x9E`, `DoEventCode.cs:860-869`) sets
`_context.usercontrol = 0` at `:866` as part of walking off-screen through a normal door, not just
inside "big" cutscenes. A naive broadcast of `usercontrol==0` would also fire on every routine field
transition (which FollowHost/state-mirror already handle via field-load, needing no teleport at all).
Recommend gating the broadcast on `usercontrol==0` held for ≥ a few frames AND no imminent
`Field()`/`PreloadField()` call, or requiring at least one open dialog window as corroboration — this
needs an in-game check (per the project's own "I cannot see the running game" constraint) before
trusting either heuristic; flag as OPEN.

**Guest side:** on the rising edge of the host's cutscene-lock signal, IF the guest is already
co-located on the SAME field (mirrors the existing s42 "SAME-FIELD PAIRING GAP" precedent,
`NetSyncClient.cs:126-139`), teleport/pin the guest's own controlled actor to the host's reported
position so the guest's OWN copy of the region trigger now contains it.

**Does a forced (tag-2 tread) trigger actually fire on a teleported actor? Yes, mechanically.**
`TreadQuad(po, 2)` (`EventEngine.TreadQuad.cs:6`, called every tick from `EventCollision.cs:281`)
is a fresh position-containment test each frame — it has no memory of HOW the actor arrived, so a
teleport landing inside the quad reads identically to a walk-in (and is actually SAFER than a fast
walk, which can tunnel through a thin quad in one frame — a known class the project's own
TREADQUAD LAW already documents, CLAUDE.md §10). **Tag-3 talk triggers are different: they ALSO
require `ETb.KeyOn() & (Confirm|Special)` to be nonzero THIS FRAME**
(`EventCollision.cs:60-83`/`85-115`) — position alone is not sufficient. So L1's pure teleport
mechanically auto-fires tread (tag-2) regions and ordinary forced-warp gateways, but a talk-triggered
(tag-3) cutscene or a mode-1 ATE's SELECT-gated menu would still sit un-opened on the guest even
after co-location, unless L1 also synthesizes one confirm press at teleport-time. The
`inventory-authority.md:278-282` residue note independently observed the same asymmetry from the
opposite direction ("a real chest is proximity-dispatched with its confirm read *inside* the
script — `B_KEYON`").

**What still diverges at L1:**
- Window advancement SPEED — each machine's window still waits for its OWN local confirm key; no
  timing is shared, so pacing free-runs independently (host could be on window 3 while guest is on
  window 1 or 5).
- CHOICES remain fully local (§1b/§2c) — co-location gets the guest watching the SAME script from
  the SAME start point, not the SAME branch.
- A guest who is NOT co-located when the host's trigger fires gets none of this — still pure L0
  ghost-pantomime for that instance.

### L2 — INPUT/CHOICE MIRROR

**Wire lane:** reuse the EXISTING FIFO command lane (`NetSyncWire.TypeCommand = 2`,
`NetSyncSocket.cs:96`, `SendCommand`/`NextRemoteCommand` at `:46-47/96/280/454-456`) — already
reliable+ordered and already proven for B1 guest battle commands
(`studies/battle-coop/inventory-authority.md:116-155`). **Not** the type-3 Control lane — that lane
is explicitly LATEST-SLOT (`NetSyncSocket.cs:70`, used today for `RemoteMenuOpen`-style assist
status), which would silently drop a confirm/choice event if two arrived in the same tick; a
dialogue advance must never be collapsed.

**Payload:** a new command sub-tag riding `TypeCommand`, e.g.
`[subtype=DialogAdvance][fldMapNo u16][winnum u8][textId u16][selectChoice i8, -1=no choice]` — the
`(fldMapNo, winnum, textId)` alignment key from §1e, plus whatever `DialogManager.SelectChoice`
held at close (`-1` for a plain non-choice confirm).

**Host broadcast point:** `Dialog.AfterHidden` (`Dialog.cs:674-686`) already computes exactly this
tuple at exactly the right moment — `this.AfterDialogHidden(this.HasChoices ? this.SelectChoice :
-1)` (`:682`) is the natural tap: a netsync listener on that same event, reading `dialog.Id`
(winnum) and `dialog.TextId` alongside the choice result.

**Guest suppress-local-input:** the same shape as the EXISTING s38 Menu-key gate
(`UIKeyTrigger.cs:834`, `if (... || NetSyncClient.IsMirroringStory) return;`) — add an analogous
guard around the confirm branch of `HandleDialogControlKeyPressCustomInput`
(`UIKeyTrigger.cs:807-817`) so a following+dialogue-mirroring guest's own key presses do not reach
`Dialogs.OnKeyConfirm` directly.

**Exact injection points:**
1. **The window-close wait is UNCHANGED.** `EBin.cs:138-149`'s `wait==254`/`MesWinActive` loop still
   drives the `.eb`-side block; L2 never touches it — it only arranges for
   `Dialog.ForceClose()`/`Hide()` on the GUEST to be triggered by the host's confirm rather than the
   guest's own key, so the existing unblock plumbing needs zero changes.
2. **The choice-result read** — before invoking the guest's `OnKeyConfirm` equivalent, set
   `dialog.SelectChoice = hostChoiceIndex` (the setter at `Dialog.cs:59-76` also writes the static
   `DialogManager.SelectChoice`, and mirroring `SetCurrentChoice` — `Dialog.cs:183-187` — additionally
   moves `ButtonGroupState.ActiveButton` so the visible cursor matches) BEFORE calling
   `OnKeyConfirm`/`Hide()`. Since `ETb.GetChoose()` only runs strictly after the `.eb`'s block clears
   (i.e. after this close), there is no race to manage.

**Misalignment / buffering:** a guest window can legitimately be BEHIND the host's — its own
teleport-triggered copy started a frame or two later, or its typewriter print
(`Dialog.currentState == TextAnimation`) hasn't reached `CompleteAnimation` yet, and
`OnKeyConfirm`'s close branch only fires once it has (`Dialog.cs:749`). An early-arriving host
confirm frame for a still-printing guest window must be **held, not dropped**, and applied once the
guest's window reaches `CompleteAnimation`. Because `TypeCommand` is FIFO+ordered (not latest-slot),
frames naturally arrive in host-emission order — the guest should peek (not dequeue) until its
alignment key matches its own currently-open window, and only then apply-and-dequeue.

**Timeout — the fail-safe law, made concrete:** if no matching confirm frame arrives within a bounded
window, the guest MUST regain local control of that dialog rather than hang — the existing
`RemoteMenuOpen`/`GuestWaitMs` precedent (`NetSyncBattle.cs:35`, default 30000 ms;
gating logic at `:225-236`, "the guest is taking too long -- gauges resume") is the exact pattern to
reuse for a `DialogWaitMs`-style knob: past the cap, stop waiting for the host and let the guest's
own local confirm input work again for that window.

**Late-join (guest arrives mid-cutscene via follow-warp):** `ApplyStoryImpl` fires BEFORE
`ee.StartEvents` (`NetSyncClient.cs:196-200`), so the guest's `Main_Init` runs fresh off the
now-matching GLOB snapshot — but scripts have no "resume from message N" concept, so the guest
typically starts the SAME cutscene from window 1 while the host may already be near the end. Under
L1/L0 this is just "two copies, temporally offset" (harmless). Under L2 it is worse WITHOUT a policy:
the host would already be emitting confirm/choice frames tagged for windows the guest's fresh-started
copy hasn't reached — those sit correctly queued (FIFO preserves order) until the guest catches up,
OR time out and get discarded per the law above, after which the guest falls back to local advance
until a LATER alignment key happens to match again. **Recommend: suppress L2 mirroring entirely for
the first cutscene after a late-arrival follow-warp** (fall back to L1/L0 for that one instance) —
consistent with the already-accepted precedent that the story-mirror's own "arming gap" is correct,
not a hole (`project-ff9-multiplayer-injector.md:684-685`).

**The speed tradeoff — a decision for the user, not an engineering detail:** mirroring confirms means
the guest literally cannot read faster OR slower than the host; every window closes on the HOST's
cadence. This is materially different from a "choice-only mirror" alternative — forward only the
FINAL `selectChoice` when a choice window closes (not every plain confirm), letting the guest advance
plain dialogue at its own pace while still guaranteeing branch agreement at the moments that matter
for story state. That alternative is NOT what L2 as specified delivers (real-time lockstep) and
should be surfaced as a explicit fork in the design, not folded silently into "the choice mirror."

### L3 — "play the game without a player"

Scoped honestly, not attempted: the guest's `EventEngine` stops running its own field triggers
entirely; the host would need to broadcast, in order, essentially every branch-relevant decision a
field script makes — not just confirms/choices, but every `Field()`/gateway warp, every talk-trigger
firing (not merely its result), every chest/pickup, every `SETCAM` camera change, every actor
`MOVE`/animation not already on the position lane, and every MAP-scoped flag write (today entirely
outside the state mirror's `gEventGlobal`-only scope — `EventContext.mapvar` is 80 `Int32` slots per
field-load, `EventContext.cs`, never touched by `NetSyncState.ApplyStory`). This converges toward
replicating the ENTIRE `EventEngine` tick remotely rather than running a second instance of it off
shared flags — a genuinely different architecture, not an incremental extension of L1/L2. This is
exactly the already-recorded "play the game without a player" research horizon
(`project-ff9-multiplayer-injector.md:606-616`, `inventory-authority.md:288-296`) — named,
deliberately not scheduled, and out of scope for this round.

---

## 4. Recommendation

**Order: L0 (already shipped) → L1 → L2 → L3 (research horizon, not this round).**

L1 is buildable with **no new wire frame type** and arguably no version bump if the cutscene-lock bit
piggybacks unused space; realistically it needs one, since the existing `TypePos` payload is a fixed
37-byte struct (`NetSyncSocket.cs:128-143`) with no spare bits. L2 reuses the existing `TypeCommand`
FIFO lane with a new payload subtype — no new frame type needed there either, but per the project's
own fail-safe convention ("version bumps reject older peers"), ship both changes under one version
bump (v10 → v11) rather than mixing a breaking struct change with a soft-compatible one.

**Wire changes:**
- v11: add one `Flags` byte to the `TypePos` payload (`NetSyncSocket.cs:128-143`), bit 0 =
  "controlled actor is under a blocking event" (host-computed from the L1 predicate below).
- v11: define a `DialogAdvance` subtype on the existing `TypeCommand` FIFO lane:
  `[fldMapNo u16][winnum u8][textId u16][selectChoice i8]`.

**Guard predicates:**
- L1 broadcast (host): `GetUserControl()==false` (`EventEngine.cs:1415-1418`) held ≥ a few frames
  AND no imminent `Field()`/`PreloadField` — **OPEN, needs an in-game validation pass**, this
  document cannot confirm the debounce is sufficient to exclude ordinary gateway crossings from
  source alone.
- L1 apply (guest): only while `FollowHost` is active AND the guest is ALREADY co-located on the
  host's field (mirrors the s42 same-field precedent) — teleport once per rising edge, not every
  frame of a long cutscene.
- L2 suppress (guest): `NetSyncClient.IsMirroringStory` AND a per-window alignment match — NOT a
  blanket "mirroring is on" gate, so a guest that has fallen out of alignment (per the timeout law)
  regains local control automatically without needing the whole session to drop out of mirroring.
- Fail-safe timeout: reuse the `GuestWaitMs` numeric convention (`NetSyncBattle.cs:35`, 30 s default)
  under a new `DialogWaitMs`-style knob for L2's per-window confirm wait.

**What each rung explicitly does NOT fix:**
- **L0** — mid-field visible wrongness for any cutscene the guest hasn't independently reached; MAP
  var/`AteCheckArray`/achievement divergence (never, out of `gEventGlobal` entirely).
- **L1** — window-advancement pacing (still fully local); choice agreement (still fully local);
  talk-triggered (tag-3) and ATE-SELECT-gated content still needs a synthesized confirm, not just a
  teleport; delivers nothing for a guest who is NOT already co-located when the host's trigger fires
  (still pure L0 ghost-pantomime); same MAP-var/achievement gaps as L0.
- **L2** — read-at-own-pace (an explicit tradeoff, not a bug — flag to the user as a fork, see §3);
  late-join mid-cutscene realignment (needs the fallback-to-L1 policy for the FIRST cutscene after a
  follow-warp); has no meaning without L1 as a prerequisite (assumes the guest's own copy of the SAME
  window is already open); still does not mirror MAP-scoped/`mapvar` state or `AteCheckArray` — a
  "perfectly synced" dialogue experience can still leave the guest's field-local flags subtly
  different from the host's for any side effect outside the confirm/choice itself (e.g. an actor
  spawn/despawn as a script side effect) unless that happens to also be GLOB-scoped.
- **L3** — not attempted this round; the named research horizon, scoped above only to make clear WHY
  it is a different architecture rather than "L2 plus more frame types."
