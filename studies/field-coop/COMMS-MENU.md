# Co-op comms menu: pings, quick-chat, emotes, warp to partner

**Status:** research only, 2026-10-12. Nothing is built. No engine, kit or wire change. The owner wants
an L3-opened in-game menu for co-op sessions on the field. It should carry pings, quick-chat, character
emotes and warp-to-partner, look like part of FF9 rather than the `~` debug menu, and match the stock UI
where possible.

Four read-only engine passes produced the evidence:
1. input and open/close plumbing;
2. the stock UI vocabulary and layering;
3. emote animation;
4. pings, chat display, warp and the wire.

Engine paths are relative to `Assembly-CSharp/` in the shared Memoria clone. **Line numbers in
`Memoria/Netsync/` come from a working tree that already carries the uncaptured F3.3 (C3, wire v14)
edits of the `coop-f33` worktree.** They will drift when that lands; re-read before building.

Related: [`DESIGN.md`](DESIGN.md) (field co-op decisions), [`F3.2-DESIGN.md`](F3.2-DESIGN.md) (the
dialogue lock this must not trip; its `suggestions` already propose an edge-of-screen marker toward the
host ghost, :1032, and inert "spectator subtitles", :1023), [`F1-BUILD.md`](F1-BUILD.md) (the held-L3
teleport and its open pad check).

## Voice chat (ruled out)

Voice was considered first and set aside:
- **Transport:** both transports are TCP (direct TCP, and WebSocket-over-TLS through the relay), so one
  lost packet stalls every later frame. Voice frames would also stall the dialogue and battle lanes
  queued behind them.
- **Playback:** SaXAudio already leaks about 0.75 MB per SE play.
- **Echo:** echo cancellation is out of reach.
- **Testing:** every round needs two machines and two listeners.

Players of a two-player mod already share a Discord call. What the game can add is what Discord cannot:
pointing at things in the game world, emoting the character, and moving to the partner. That is this
study.

## Decision summary (recommendations; owner calls are listed at the end)

| # | Area | Recommendation | Wire | Size |
|---|------|----------------|------|------|
| 1 | Open | **Tap** L3 opens the menu. **Hold** L3 keeps today's teleport. Read L3 through XInput, not `JoystickButton8`. Keyboard: F10 (verify), else Q/T. | none | S |
| 2 | While open | Freeze field movement and field input. Swallow until the closing button is **released**. Never touch usercontrol. | none | M |
| 3 | Look | Vertical command list from stock pieces. Rung 0 = a stock UI choice dialog; final = a clone of the battle command window. A radial cannot look stock without new art. | none | S then L |
| 4 | Wire | New bidirectional **type 8 (comms)**, sent as a latest-slot carrying a small seq ring with an epoch. **v15, after F3.3 proves.** | v15 | M |
| 5 | Ping | First at the sender's own position, drawn on the receiver with the stock `cursor_hand_here` hand. Then an aimed ping on the walkmesh, edge arrows and off-field toasts. | v15 | S then M |
| 6 | Quick-chat | Phrase **id** on the wire, rendered locally. An inert NGUI balloon (`dialog_frame_chat` frame, stock font) following the ghost. **Never a Dialog.** | v15 | M |
| 7 | Emote | Local: clone the engine's own idle-fidget path. Remote: EmoteId + nonce, mapped per rig. Bubble fallback for thin rigs. | v15 | M |
| 8 | Warp | The menu entry calls the existing `RequestTeleportToHost`. Guest-only, followed sessions only; the decline reason shows on screen. | none | S |

## 1. Opening the menu

**L3 is already bound.** `UIKeyTrigger.Update` gates on `(IsLiveFollowedSession || IsSelfTestRole) &&
TeleportKeyPressed()` (UIKeyTrigger.cs:188-190). The press is consumed either way (:194) and only acts in
`FieldHUD` (:192-193).

`TeleportKeyPressed` (NetSyncField.cs:170-214) works like this:
- F11 fires at once (:195).
- Holding `JoystickButton8` accumulates `_l3Hold` and fires once at 0.7 s, latched by `_l3Fired`
  (:178, :197-204).
- Release resets it (:206-210), and `ResetTeleportKey()` clears it at session edges
  (NetSyncClient.cs:872, :1374).

**Tap and hold can coexist.** A release with `_l3Hold < 0.7 && !_l3Fired` is a tap: open the menu. Capture
it before the reset at :208. Opening on *press* instead would make a hold both open the menu and teleport;
the menu would then have to absorb teleport entirely (owner decision 2).

**Read L3 through XInput.** `UnityXInput.Input.GetKey(KeyCode)` just calls Unity's `Input.GetKey`
(UnityXInput/Input.cs:357-360). Every other pad button goes through XInput `GetXButton` (Input.cs:81-142),
which only knows buttons 0-7 plus the triggers. So L3 is the one button read through a different input
system, and `JoystickButton8` means "button 8 on *any* joystick":
- On a raw DualShock 4 / DualSense, button 8 is usually **Share/Create** and 10 is L3.
- The Unity path also skips the `AlwaysCaptureGamepad` focus check (Input.cs:83).

The fix is `PersistenSingleton<UnityXInput.XInputManager>.Instance.CurrentState.Buttons.LeftStick`, using
`PreviousState` for edges (Memoria.XInputDotNetPure/GamePad.cs:55; `RightStick` :60). This fixes the
teleport read as well. It also settles the open "held L3 is STILL UNTESTED on the live pad" item
(F1-BUILD.md:199, :302, carried at :477/:541 and F3.2-DESIGN.md:955), because rung 0 will exercise L3 on
the real pad.

**Free inputs** (HonoInputManager.cs:25-50, :1205-1226; UIKeyTrigger.cs:239-404, :740-814;
ff9.cs:10647-10653):
- **Pad:** L3 and R3 (button 9 appears only in the iOS profile, HonoInputManager.cs:70-71).
- **Keyboard:** F10, Q, R, T, Z.
- **F10** is the natural keyboard twin of F11 and has no live read. Windows treats F10 as a system
  (menu-bar) key, so it needs an in-game check. Avoid F12 (Steam screenshot).
- `platforms-teleport.md:381-386` is stale: it still says F6 opens the debug menu and F10 is claimed.

**Who gets the menu:**
- Pings, chat and emotes are symmetric: both host and guest, in followed sessions *and* free-roam ghost
  sessions (`FollowHost=0`).
- Today the L3/F11 read only arms for a live followed guest or selftest. **No public host-side session
  predicate exists** (`IsLiveFollowedSession` requires role=client, NetSyncClient.cs:595-607), so rung 0
  adds one: enabled, paired, position lane fresh, any role.
- The warp entry stays guest-only (section 7).

## 2. While the menu is open: freeze, swallow, refuse, auto-close

**Order matters.** Menu, Confirm and Cancel reach the field scene through
`HandleMenuControlKeyPressCustomInput()` at UIKeyTrigger.cs:161, *before* the `~`, F11 and battle-digit
intercepts (:171-201). An intercept placed beside the teleport read would not eat Menu, so it has to sit
ahead of :161.

**NPC talk never goes through `UIKeyTrigger.Update`.** The chain is:
1. `EventEngine.cs:119` `ETb.ProcessKeyEvents`
2. `ETb.cs:50-62`, which reads `FPSManager.DelayedInputs`
3. `FPSManager.cs:126,134` `EventInput.ReadInputLight()`
4. `EventInput.cs:351-356`
5. `UIKeyTrigger.GetKey/GetKeyTrigger` (:92/:108)
6. `HonoInputManager`

The check itself is `EventCollision.cs:63,99` reading `ETb.KeyOn()`.

**The harness's input choke point covers the field consumers.** If `HonoInputManager.IsInput /
IsInputDown / IsInputUp` return false and `GetAxis` returns zero (:897-957, the harness override slot),
then the menu plane, NPC talk, script button polls, walking and running all go quiet.

**The open design problem is splitting field consumers from menu consumers.** A blanket choke-point swallow
also blinds the menu's own navigation if the menu is a stock Dialog or ButtonGroup (both read the same UI
key path). The two candidate splits:

| Menu kind | How the menu reads input | What must be gated |
|---|---|---|
| Stock UI choice dialog (rung 0) | `Dialogs.Activate` routes keys to the dialog handler, not the scene (UIKeyTrigger.cs:640, :203) | Only movement and the ETb key path. Movement is read by `FieldMapActorController` from axes and keys; analog walking bypasses `GetKey` (FieldMapActorController.cs:601, :612-615). |
| Custom NGUI menu | Reads its own buttons and stick straight from XInput | Everything at the choke point (one static `CommsMenu.Active`) |

**Rung-0 recon:** confirm whether the field player can still walk while a UI-form dialog is open (the
FieldHUD skip-movie dialog only ever opens during a movie, so there is no precedent). Settle the movement
gate seam. F3.2 owner decision 1's alternative names `FieldMapActorController.cs:636-641/:650` and flags
that file for uncaptured patch drift.

**Traps (each has cost a round before):**
- **Never use usercontrol.** It is the script-visible movement flag:
  - every stock `_SpeakBTN` opens with `ifnot(IsMovementEnabled) return` (THE L1 LAW, F3.2 C1);
  - walk-on triggers need it (EventEngine.ProcessEvents.cs:186-187);
  - the menu's own warp entry would be declined (NetSyncClient.cs:3801);
  - control-off lifts the guest's free-walk Confirm/Special/Select mask (NetSyncField.cs:106-113);
  - a blind restore clobbers any DisableMove/EnableMove a script ran meanwhile. The `~` menu's "Disable
    control" box does exactly this (Ff9mkDebugMenu.cs:601-621).
- **Never use the controller pad mask.** Clearing a movement mask does not restore walking; only EnableMove
  does (FieldMapActorController.cs:161-173; memory `project-ff9-movement-locks`).
- **Release edge.** `FPSManager` collects press edges (:126-129), so the Confirm that closes the menu can
  land in the field as a fresh press. Keep swallowing until that button is released.
- **Mouse.** Left mouse is Confirm on the field (UIKeyTrigger.cs:105), and any field mouse-up issues
  click-to-move unless `DisableMouseInFields` is set (FieldMapActorController.cs:1737-1743).
- **The `~` menu is not a model.** IMGUI consumes nothing, and Triangle still opens the main menu under it
  (UIKeyTrigger.cs:694-700).

**Refuse to open unless all of these hold.** All the predicates exist:
- `ee.gMode == 1 && ee.fieldmap != null` (NetSyncClient.cs:1017) and `UIState == FieldHUD`;
- `ee.GetUserControl()` (EventEngine.cs:1421);
- `!ui.Dialogs.Visible` (DialogManager.cs:42);
- `!SuppressLocalDialogInput` (NetSyncClient.cs:628-639);
- `IsMenuControlEnable && !IsPause && !IsLoading && IsEventEnable` (UIManager.cs:95-97, :715);
- no follow-warp in flight (`_followWarpPending`, private, :135) and no `BattleReturnInFlight`
  (NetSyncDiorama.cs:658);
- no FMV (UIKeyTrigger.cs:241), no `BubbleUI.IsActive`, no `EventHUD.CurrentHUD` (EventInput.cs:91, :113).

The auto-teleport busy test (NetSyncClient.cs:3960-3966) is the nearest existing combined check.

**Auto-close.** If any of those predicates goes false while the menu is open, close it at once with no
action. The likely cases: a relayed host talk opens a locked line on the guest, a script takes control,
or a battle or warp starts. The menu must never be the thing holding a line or a transition.

## 3. The look

**Why today's surfaces read as dev tools:**
- Both the `~` menu (Ff9mkDebugMenu.cs:632-664, flat hex fills :2908-2930) and the co-op overlay
  (NetSyncClient.cs:4106-4149) are IMGUI: no 9-sliced FF9 window, no finger cursor, outside UI Root
  scaling.
- IMGUI draws after every camera, so they sit on top of dialogs, menus and fades.

**What stock offers:**
- **Window skins.** The Gray and Blue atlases (`FF9UIDataTool.WindowAtlas`, FF9UIDataTool.cs:269-283)
  each carry `dialog_bg`, `dialog_frame_chat/info/timer`, `dialog_hilight`, the four `dialog_pointer_*`
  tails, `panel_face` and `panel_frame` (40x40, 10 px 9-slice).
- **General Atlas:** `cursor_hand_choice`, `cursor_hand_here`, `menu_bg`, `list_frame`,
  `battle_bar_highlight`, `balloon_*`, `scroll_arrow_*`.
- **Icon Atlas:**
  - 184 item icons and 25 `icon_status_*` (FF9UIDataTool.cs:918-989);
  - `balloon_exclamation/question/card/beach` (+`_act`, :1006-1016);
  - `arrow_up/down/left/right`, `icon_help`, `icon_new_exclamation`.
- **Font:** the stock font is reachable. `UILabel` falls back to TBUDGoStd-Bold (UILabel.cs:140;
  EncryptFontManager.cs:33-43), and a cloned stock label brings its size and shadow.
- **Finger cursor:** the pooled per-depth `PointerPrefab` (PointerManager.cs:134-204).

**No radial UI exists anywhere in stock FF9 or Memoria,** and no stock atlas holds a ring or slice
sprite. NGUI's `Radial360` fill (UIBasicSprite.cs:582-627) is unused.

| Layout | Built from | Stock look | Notes |
|---|---|---|---|
| **Vertical command list** (recommended) | Rung 0: a stock UI choice dialog opened from C#. Final: a clone of `BattleHUDScene.CommandPanel` (public, BattleHUD.Unity.cs:28; 6 `GONavigationButton` rows + caption, BattleHUD.UI.PanelCommand.cs:26-36). | **Genuinely stock:** real frame, finger and font. | Memoria already clones a command row at runtime (PanelCommand.cs:37-49), which is the template for extra rows. Battle's command-to-submenu idiom fits `Say ▸` and `Emote ▸`. |
| **Four-direction cross** | Four `panel_frame` chips (`BuildFramedPane`, JournalUI.cs:814-851) + Icon Atlas glyphs | Stock pieces, invented arrangement | Stick-flick selection, close to the radial's feel. Four slots cap the top level. |
| **Radial** | New ring/slice art merged into an atlas (mod PNG + `.tpsheet`, UIAtlas.cs:62-85) | Cannot look stock | New art is a human task. Needs custom angle-to-slice input, and the finger has no radial idiom (it parks at a widget's left edge). |

**Rung-0 path: the stock choice dialog.** `FieldHUD` already opens a C#-built choice dialog on the field
(FieldHUD.cs:281-284) and reads the result (:428-435). UI dialogs centre their choices (Dialog.cs:125-131).
This means zero new widgets. Caveats:
- it writes the script-visible `ETb.sChoose` (Dialog.cs:92-99). That is safe only because the menu
  refuses to open with any dialog up.
- Confirm broadcasts to every open window, and TURBO-DIALOG (F9) applies (memory
  `project-ff9-message-windows`).
- Netsync ignores UI dialogs (Id 9; NetSyncDialog.cs:266-272), which is what we want.

**The final menu is the project's first in-field NGUI overlay.** The two existing NGUI surfaces are full
screens with their own `UIState`:
- the Folklore codex cost about 32 in-game rounds (s45/s46);
- the Journal (s81/s82) took rungs M0-M5 plus about 5 fix rounds (completion-journal/PLAN.md:9, :738-741).

These laws from memory `project-ff9-ngui-menu-construction` apply to an overlay:
- DontDestroyOnLoad parentage under the UIManager tree;
- `SetAnchor(null)` on every moved clone and its dressing children;
- pivot before `SetRawRect`;
- the `DisplayWindowBackground` colour sweep;
- panel-depth sorting;
- the finger's pooled depth (`SetPointerDepthToGroup(panel+1)`);
- the UI layer (a fresh layer-0 GameObject is culled, UIManager.cs:207);
- `[NonSerialized]` fields;
- `OnDisable` teardown;
- CALIBRATE-THE-MARGIN;
- PRESERVE-THE-BAKE in spirit (do not reshape baked labels).

SCROLL-SUM and the cell-template laws do not apply.

**Parenting and depth:**
- A child of `FieldHUDScene` is swept on load (UIManager.cs:237) and returns with
  `ChangeUIState(FieldHUD)` (:277). It also hides itself when the main menu opens (FieldHUD.cs:258-262).
- Dialog panels sit at `68 − 2·id` + 22 (Dialog.cs:1708-1709; DialogManager.cs:446-449), so a panel
  below 54 draws under every dialog. That is correct here, because the menu auto-closes when a dialog
  opens.
- The `MenuUIControlPanel` host was refuted (no input focus; folklore-codex/SUBMENU.md:25-35). The menu
  needs its own intercept (section 2).

## 4. The wire: a comms lane

**Today's frame is `[0xF9][version][type u8][len u16 LE][payload]`** (NetSyncSocket.cs:60, :146-182).

| Type | Lane | Notes |
|---|---|---|
| 0 | position, latest-slot | 37 bytes |
| 1 | battle state, latest-slot | |
| 2 | battle command, FIFO | |
| 3 | control, latest-slot | |
| 4 | roster, latest-slot | |
| 5 | story state, latest-slot | Sections 0-7; host-to-guest only (NetSyncClient.cs:1229-1236) |
| 6 | battle action, FIFO | |
| 7 | dialogue, FIFO | Retired at v14 |

Latest-slots are re-sent every 33 ms (NetSyncSocket.cs:322-342). The relay is an opaque pipe
(studies/battle-coop/relay/main.go:217-257). The relay drops frames while the partner is away and the
bridge drops frames while redialling, so FIFO delivery is at-most-once.

**Where comms cannot go:**
- **The command FIFO:** it drains only in battle (NetSyncBattle.cs:355-361), so out-of-battle pings would
  dump into the next battle.
- **A type-5 section:** host-to-guest only.
- **TypeControl:** NetSyncBattle overwrites it every tick (:394/:402).

**Recommendation: type 8, bidirectional, sent as a latest-slot that carries a ring**, the C3 WIRE-1
pattern. Re-sending every tick survives relay and bridge drops; the receiver dedups by `(epoch, seq)`. It
needs a slot pair in `NetSyncFrames` plus set/get on both transports (the type-4/5 precedent). A sketch:

```
type 8 payload: [epoch u8][count u8] + count x entry (16 bytes)
entry:          [seq u8][kind u8][field u16 LE][body 12 bytes]
  kind 1 ping   body = x f32, y f32, z f32       (world position, exact 1:1 on the same field)
  kind 2 chat   body = phrase u8, pad
  kind 3 emote  body = emote u8, nonce u8, pad
```

- The sender drops an entry after its TTL (about 3 s) and bumps `epoch` per session, so a reconnect never
  replays old pings.
- Four entries cost 66 bytes; at 30 Hz that is about 2 KB/s against today's ~90 KB/s.
- F3.2's WIRE-7 suggestion (send on change plus a 2-4 Hz keepalive) would cut that further.

**Versioning:**
- An unknown *type* is silently dropped by older builds (`Accept` has no default, NetSyncSocket.cs:351-392).
  So a type-8 lane alone would degrade gracefully.
- But project precedent bumps on every new lane, and a mismatch disconnects on direct TCP (:654-660) and
  silently never syncs on the relay (NetSyncRelay.cs:343-360).
- v14 (F3.3) is in flight and uncaptured. Folding comms into it would cost bisectability (CLAUDE.md's one
  change per in-game test). **Recommended: v15, after F3.3 is proven and captured.**
- Both machines must update, as always.

**The harness protocol stays 5** (memory law, HarnessAgent.cs:70): a `netsync.comms` block and `netsync
comms ...` verbs, additive only.

## 5. Pings

Field positions are exact 1:1 between machines on the same field: the position lane carries
`transform.localPosition` == `curPos` (FieldMapActorController.cs:93-97, :267-269). Send world (x,y,z)
plus the field id. **Each receiver projects with its own camera,** because multi-camera fields diverge
between machines.

**What a ping points at:**
- **(a) The sender's position** ("ping here"): one menu entry, no aiming. Rung 1.
- **(b) The partner's position:** trivial (`rs.Pos`), but no obvious use.
- **(c) An aimed spot on the walkmesh:** the pick already exists.
  - `WalkMesh.GetTriangleIndexAtScreenPos` (WalkMesh.cs:353-375) plus a perspective-correct barycentric
    step back to world. Both click-to-move (`CheckPosInProjectedWalkMesh`,
    FieldMapActorController.cs:1735-1770) and the `~` menu's `PickPoint` (Ff9mkDebugMenu.cs:2268-2310) do
    this from `PSXCameraAspect.GetLocalMousePosRelative()`.
  - A gamepad needs a virtual reticle in that screen space, driven by the left stick in an "aim" sub-mode.
  - The mouse can click directly, minding the click-to-move hazard (section 2). Rung 4.

**Drawing it on the receiver:**
- Create an empty GameObject under `fieldmap.transform` at the ping's world position. Attach a
  `UIFieldMapFollowTarget` (UIFieldMapFollowTarget.cs:47-65): a public component that projects any
  Transform with the GTE every `LateUpdate` and yields an NGUI `localPosition`.
- Re-resolve the field map lazily after each load (the `EIcon.FieldMap` idiom, EIcon.cs:7-16).
- **Sprite:** `cursor_hand_here` is FF9's own "here" pointer (`SetHereIcon`, EIcon.cs:341-401), so the
  ping reads as native. `balloon_exclamation` is the alternative.
- **Do not reuse the `BubbleUI` singleton.** It is the player's own "!": `ProcessFIcon` hides anything not
  polled each tick (EIcon.cs:181-201), and its buttons are clickable Confirms (BubbleButton.cs:50-68).
- **Off-screen:** the follower does not clamp. Clamp to the screen edge and swap to an `arrow_*` glyph
  pointing inward. This is the same machinery as F3.2's proposed "look over there" ghost marker, so build
  it once.
- **Partner on another field:** world positions are meaningless there. Show a toast ("Partner pinged — on
  field N"; a field-name lookup is unverified) drawn like the dialogue-lock chip (NetSyncClient.cs:4134-4149).
- **TTL** about 4 s.
- **Sound:** at most one stock SE on receipt. SaXAudio leaks about 0.75 MB per SE play
  (studies/menu-leak/FINDINGS.md), so rate-limit pings (about one per 1.5 s per sender). That also limits
  spam.

## 6. Quick-chat

**Send a phrase id, never text.** Each machine renders its own language, which removes one more
same-language assumption (F3.2 owner decision 10). Field `.mes` text cannot serve: text blocks are
per-zone, so a fixed textId means different text in different zones.

Phrase table options:
- a C# table in the engine (precedent: the lock chip strings, NetSyncDialog.cs:90-96);
- Memoria's `Data/Text/LocalizationPatch.txt` through `Localization.Get` (LanguageMap.cs:191-203). Its
  format is unverified, and the kit does not emit it today.

A starting set of about ten lines: *Over here! · Wait for me · Let's go · Hold on · Thanks! · Yes · No ·
Look! · Ready · Found a save point.* The list is an owner call.

**Display: an inert NGUI balloon, never a stock Dialog.**
- **An ETb-form Dialog is a trap.** `AttachDialog`'s ETb form (DialogManager.cs:99-159) creates a window
  that passes `IsLockable = IsETbDialog && Id != 9 && TextId >= 0` (NetSyncDialog.cs:269-272). F3.2's lock
  would catch it and the relays would key it by `(fld, win, textId)`.
- **A UI-form Dialog has its own problems,** even though it is never tracked (Id 9, DialogManager.cs:77-97):
  - an explicit position nulls `Po`, so it would not follow a moving ghost (Dialog.cs:901-902);
  - the ghost cannot be `Po` anyway, because Dialog casts it to `Actor` (:906-923);
  - Confirm reaches every open window, so it closes on the receiver's next Confirm and arms turbo-dialog
    unless `FlagButtonInh` (DialogManager.cs:339-345, :428-434);
  - `Dialogs.Activate` reroutes keys (UIKeyTrigger.cs:640);
  - `Dialogs.Visible` makes auto-teleport and battle-return "busy" (NetSyncClient.cs:3962-3966;
    NetSyncDiorama.cs:732).
- **The balloon:** a `dialog_frame_chat` 9-slice frame plus a cloned stock label on a
  `UIFieldMapFollowTarget` bound to the ghost's transform, raised by the head offset. The ghost has no
  `PosObj`, so `eye` comes from a per-rig table (the kit's `playerswap.CHARACTERS` has it,
  playerswap.py:44-51; `NetSyncVisitor.Rigs` does not).
- **Behaviour:** it closes on its timer (about 3 s), takes no input, and is outside every netsync tracker
  by construction. The sender sees a small echo over their own character.
- This is the same inert-window idea as F3.2's "spectator subtitles" (:1023), sharing the widget.

Free text chat (typing) is out of scope: no field text-entry surface exists outside menus, and it would
need moderation.

## 7. Emotes

### Playing one on the local player

The engine already does this during free roam. `CheckSleep` (EventEngine.cs:534-552) plays the idle
fidget on the control actor: `inFrame=0; outFrame=255; ExecAnim(p, sleep); animFlag |= afLower`.
- **Moving cancels it for free.** ProcessEvents.cs:276-283 switches to walk/run when the exec/lower/freeze
  bits equal `afExec|afLower`. `afLower` also stops head-tracking from overriding a nod (ProcessNeck.cs:22).
  Without it the player glides while gesturing.
- **The clip end returns to idle:** NextFrame → `AnimLoop` → `AnimStop` → `DefaultAnim(idle)`
  (ProcessAnime.cs:91-93, :152-153, :176-178, :204-210).
- **There is no per-frame fight with `FieldMapActorController`:** it only samples `anim/animFrame`
  (FieldMapActorController.cs:157-160, :405-431).

The recipe:
1. Gate on field mode, control on, `(animFlag & (afExec|afFreeze)) == 0`, not turning (`flags&128`), not
   jumping, not on a ladder.
2. Call `AnimationFactory.AddAnimWithAnimatioName(go, name)` and **confirm the clip resolved.** A missing
   clip gives frameN 255, which is about an 8 s frozen "emote", and a `SmoothFrameUpdater` NRE after battle
   (EventEngineUtils.cs:1836-1842).
3. **Clear stale `afHold|afLoop|afPalindrome`** and set `loopCount=0`. `PREJUMP` leaves `afHold` behind
   (DoEventCode.cs:2110), and a stale hold freezes the player on the last frame.
4. Set `inFrame=0; outFrame=255`, call `ExecAnim`, then OR in `afLower`.

`ExecAnim`, `SetAnim` and `AnimStop` are private (EventEngine.cs:1403; ProcessAnime.cs:174/193), so the
engine patch needs a public wrapper.

Clips carry no baked sound or effects (no `AnimationEvent` in Global). Weapon visibility is script-driven
(`MESHSHOW/MESHHIDE`, DoEventCode.cs:1270-1281), not clip-driven.

### The clip catalog

The source is the kit's `_animdb.py` `MAIN_ANIMATIONS` (the 8 mains). Use `catalog.own_form_gestures()`
(catalog.py:186-209), which encodes the cross-form trap: a clip from another form twists the model
upside-down. Unique F0 actions per character: ZDN 401, STN 230, VIV 197, GRN 188, FRJ 112, EIK 105,
KUI 60, SLM 64.

| Rig | Usable gestures (examples, anim ids) | Coverage |
|---|---|---|
| Zidane | YES 111, NO 108, SURPRISED_1_x 10550.., ANGRY_1_x 10394.., THINK_x 587.., LETSGO_*, HURRY_UP_x 6170.., DISAPPOINTED_x 3670.., JUMP_x 10446.., SIT_x 3003.., HIZA_OJIGI_1 5876 (kneel bow), idle breaks 54-59 | Full (no literal wave/laugh) |
| Vivi | YES 905, NO 901, LAUGH 900, GLAD 902, SAD 898, ANGRY 899, REI 6531 (bow), EXCITE_*, YAWN 2690 | Full |
| Garnet | YES 827, NO 477, BOW 5234, CHEER_x, AMAZING_x, ANGRY_x | Full |
| Steiner | YES 7235, NO 7225, SALUTE 1983, CHEER_1 9971, POSE_GUTS 5938, SURPRISED_x | Full |
| Freya | YES 6028, NO 6036, SHOCK_x, ANGRY_x, HIZA_OJIGI_x | Good |
| Eiko | YES_1 14490, NO_1 14492, ANGRY_1, CRY_x, GUTS 7572 | Good |
| Quina | YES_1 10396, NO_1 10400, GLAD_YES 4781, REFUSE, SURPRISED 5416 | Thin |
| Amarant | BYE 1022, UDEGUMI_2 5081 (arms crossed), no yes/no/angry | Poor: bubble fallback |

All 8 share TALK_x_x, LOOK_UP_1..3 and JUMP_1..3.

**The rig-neutral emote set** is an owner call: *Yes · No · Surprised · Angry · Think · Cheer/Glad ·
Bow · Jump · Sit*, mapped per rig, with a blank where a rig has nothing.
- Exclude prop- and story-bound clips (TELESCOPE, POT, CHO_*, SWORD_*…).
- Every clip must be previewed in the Workspace clip player before it is whitelisted.
- The `_1/_2/_3` = in/hold/out reading is from names only. A three-part chain needs sequencing, or only
  the single-part clips are used.
- Jump, sit and kneel may displace the root (cosmetic, snaps back, not verified per clip).
- Memoria toggles the shadow for sit clips (DoEventCode.cs:1355-1364).
- Any model outside the 8 rigs gets bubble-only: Dagger-short 532, Beatrix, Blank, custom characters.

### Replication on the ghost

**Today it is broken in three ways.** `DriveGhost` forces `WrapMode.Loop` and does not restart a clip that
is already playing (NetSyncClient.cs:4366-4379). So:
- a one-shot mostly works, but can flash back to frame 0 near its end for the link latency;
- held or chained clips visibly loop;
- the same emote twice may not restart.

**A dressed ghost (`GhostAs`) shows nothing.** It maps `LocoOther` to idle (NetSyncVisitor.cs:76-77,
:104). Sending the raw clip id across rigs would hit the cross-form bug.

**The fix rides the comms lane.** A kind-3 entry carries the EmoteId and a nonce; the receiver maps the
EmoteId on *the rig it is rendering* (peer's own or the dress rig, `Rigs[]` NetSyncVisitor.cs:43-53) and
plays it once (`ClampForever`/`Once`). `DriveGhost`'s locomotion pick yields until the clip ends. Stock
clips load by name on every install (AnimationFactory.cs:54-66), so no asset ships.

**A zero-wire half-fix exists:** play `Loco == LocoOther` clips with `ClampForever` instead of `Loop`.
It fixes the looping but neither restarts nor dressed ghosts.

### Bubble icons

`BubbleUI.IconType` offers Question, Exclamation, ExclamationAndDuel, Beach and ExclamationAndBeach
(BubbleUI.cs:506-522). Only `balloon_exclamation/question/card/beach` are named in code; no note, sweat,
anger, heart or Zzz sprite is referenced (the atlas itself was not dumped; a UnityPy look is cheap).

Bubbles cover every rig, including dressed ghosts and Amarant. Draw them with the same follower widget as
the ping, never through `BubbleUI`. New glyphs would mean authored art merged through a `.tpsheet`: possible
and provenance-clean, but no longer stock.

## 8. Warp to partner

The menu entry calls `RequestTeleportToHost` (NetSyncClient.cs:3772) and reuses every gate of
`TeleportToHostImpl` (:3791-3872), in order:
1. warp in flight
2. control off
3. no actor
4. the selftest branch
5. no live followed session
6. stale peer lane
7. same field: `SnapToHost` → `SetPosition`
8. partner's field not installed: the `eventIDToFBGID` guard
9. otherwise cross-field: re-arm `FollowHostTick` → `StartFollowWarp`

The code comment "do not add an automatic caller back" (:3883-3885) is about automatic callers; a menu
entry is manual.

- **Guest-only in followed sessions.** A host following its guest is never valid, so the entry is hidden
  for hosts and free-roam guests.
- **Show the decline reason on screen** (the existing `TpDecline` strings), not only in the log.
- **No cross-field warp in free-roam.** There is no story mirror there, so the warper's own story would
  be staged at the partner's location: the out-of-sequence state NetSyncState.cs:26-31 exists to prevent,
  except here it can be saved. A free-roam same-field snap is also unsafe as-is, because `GetTriIdxAtPos`
  ignores the active flags (FieldMapActorController.cs:1279-1305) and can land on a story-disabled
  triangle. Deferred.
- **Held L3 and F11 stay** as no-UI shortcuts (owner decision 2).

## 9. Other entries worth a slot later

These are not rung material; they are listed so the menu's shape leaves room:
- **Find partner:** the edge marker toward the ghost (F3.2 :1032), the same widget as the off-screen ping.
- **Release dialogue lock:** the F3.2 panic unlock lives in the `~` menu today. It is user-facing, so the
  comms menu is a more integrated home.
- **Co-op status:** paired / waiting / partner on field N. This could replace the IMGUI status overlay
  with a stock-look line.

## 10. Solo testability

Follow the `NetSyncState.SelfTest` precedent (NetSyncState.cs:227-290): loop comms entries through the
real codec (`BuildFrame` → `TryParseHeader` → parse) and render them over the selftest mirror ghost
(`Role=selftest`, `SelfTestOffset` "250,0", NetSyncClient.cs:41, :82, :756-771).

Add harness verbs `netsync comms open|ping|chat|emote|warp` and a `netsync.comms` telemetry block, both
additive under protocol 5.

Asserts:
- the label or marker appears near the mirror's projected point and expires on its timer;
- a repeated slot does not re-show (seq dedup), and an epoch bump does not replay;
- **no lockable Dialog opens, `suppress` stays false, usercontrol is untouched;**
- the menu auto-closes when a bench lock or host-scene toggle rises;
- the release-edge Confirm does not reach the field;
- a field-id override produces the off-field toast;
- the warp entry goes through the selftest branch (:3812-3827);
- a local emote returns to idle and a move cancels it.

Per memory `feedback-a-check-that-cannot-fail`, every new check must first be shown failing on the
pre-change DLL. `netsync selftest` refuses while `coop host` owns the shared ini (`coop off` first).

## 11. Rung ladder

Each rung is one engine change and one in-game test, captured as its own sNN after the F3.3 patch.

| Rung | Content | Wire | Proof |
|---|---|---|---|
| **0** | L3 tap/hold split + XInput L3 read + F10. The open/close intercept ahead of UIKeyTrigger.cs:161, the field-input freeze, release-edge swallow, refuse and auto-close predicates, the host-side session predicate. The menu is a **stock UI choice dialog**. Local actions only: emote on Zidane (no replication), warp entry. | none | Solo harness + owner pad check (closes the L3 item) |
| **1** | The type-8 comms lane (v15). Ping at self with the `cursor_hand_here` follower. Quick-chat balloons. Off-field toast. | v15 | Selftest loopback, then two machines |
| **2** | Emote replication (EmoteId + nonce, per-rig table, dressed ghosts). Leader tables for all 8 rigs, bubble fallback. | v15 | Selftest mirror, then two machines |
| **3** | The stock-look menu: battle command window clone with `Say ▸`/`Emote ▸` submenus, replacing the choice dialog. | none | Owner look-and-feel playtest |
| **4** | Aimed ping (reticle + walkmesh pick, mouse click), edge arrows, find-partner. | v15 | Two machines |

Rung 3 comes after the plumbing on purpose. NGUI construction is where the project's UI rounds have gone,
and every earlier rung's behaviour stays identical when only the surface changes. If the owner wants the
look sooner, rung 3 can move to second place without touching rungs 1-2.

## 12. Owner decisions

1. **Layout:** vertical command list (recommended; stock frame, finger and font) · four-direction cross
   (stock pieces, stick-flick) · radial (needs new ring art; cannot look stock).
2. **L3:** tap opens the menu and hold keeps the teleport (recommended) · the menu absorbs teleport
   (open on press).
3. **Movement while open:** frozen (recommended; the left stick picks the entry, and L3 is that stick) ·
   walkable, with selection on the right stick, which is unused on the field.
4. **Who:** pings, chat and emotes for both roles, in followed and free-roam sessions (recommended) ·
   followed sessions only.
5. **Ping aim:** at self first, aimed in rung 4 (recommended) · aimed from the start.
6. **Phrase list and languages:** the starting ten, English first, a C# table (recommended) · a
   `LocalizationPatch.txt` route.
7. **Emote set:** the nine rig-neutral emotes, bubble fallback for Amarant and non-main models.
8. **Sequencing:** after F3.3 proves and is captured, wire v15 (recommended) · fold into v14.
9. **Keyboard key:** F10 if Windows' system-key handling allows it (recommended) · Q or T.
10. **Sound on receipt:** one rate-limited stock SE for pings and chat (recommended) · silent.
11. **Panic unlock:** move it into the comms menu (it stays in `~` too) · leave it in `~` only.

## 13. Risks

- **First in-field NGUI overlay.** No precedent for a field-time NGUI surface. The layering, sweep-on-load
  and finger-depth laws are known, but this combination is new.
- **The input split (section 2).** Freezing the field without blinding the menu is the one genuinely open
  engine question, and the movement seam sits in a file flagged for uncaptured patch drift.
- **The physical L3 button** is unconfirmed until rung 0's pad check. The XInput read removes the
  DualShock Share ambiguity but should be checked on both pad families.
- **Emote flags.** A stale `afHold` freezes the player, and a missing clip freezes for about 8 s. Both are
  guarded by the recipe's checks and need explicit bench cases.
- **Spam and the SE leak.** Rate limiting is a correctness requirement, not polish.
- **Wire bump.** Both machines must update. A v15/v14 mismatch never pairs on the relay and says nothing;
  F3.2's WIRE-5 suggestion (count header-rejected frames so the overlay can say so) would help here too.
- **The shared clone.** F3.3 is uncaptured in the working tree. Comms work must start from its captured
  patch and a clean `tools/memoria_stack_replay.py`, never on top of an in-flight tree.
