# What the harness can and cannot drive — the input-bypass audit

An adversarial sweep of every subsystem that reads player input, looking for the *same class* of
bug the analog axis turned out to be: a consumer that reads input around the harness hooks rather
than through them. Five agents swept in parallel, one per subsystem; every candidate was then
handed to an independent agent whose job was to **refute** it by reading the code, defaulting to
"not a bypass" when uncertain.

**22 confirmed, 6 refuted.**

> ⚠ 2026-08-31 — the OVERWORLD section below is partly WRONG, and the correction is the same shape as
> the law at the top of this file. A recon pass refuted three of its four premises: `w_movementHumanOperation`
> does NOT read the pad directly, so **the harness can already walk on foot on the overworld**. What
> actually failed there was the DRIVER, which steered on `player.x` — not null on the world map but the
> same value ×256, a different coordinate space — and therefore converged on confident wrong numbers
> instead of failing. The field verbs now refuse off-field. The vehicle-throttle and camera-yaw entries
> stand. Re-verify a claim here before acting on it.

> Read this before concluding the harness is broken. If a scenario cannot drive something, check
> here first — the honest answer may be that the hooks do not reach it yet.

---

## The headline: one hook would fix four subsystems

`UICamera.cs:954` — `UnityXInput.Input.GetAxisRaw(axisName)` — is **the** cursor-movement path for
every NGUI surface in the game, and it turns up independently in the battle, field, menus and title
sweeps. It governs the battle command cursor and target cursor, the field dialogue-choice highlight
(every Yes/No the game asks), every menu cursor (item, ability, equip, config, shop, save/load), and
the title menu itself. Its terminal read is `UnityXInput/Input.cs:309`, which special-cases
`Horizontal`/`Vertical` to physical keys before falling through to the XInput stick.

**★ FIXED 2026-08-27** — `UnityXInput.Input.GetAxisRaw` now consults
`HarnessAgent.TryGetNavigationAxis` for the two navigation axes. Proven in-game: from the main menu,
three `press down` moved the cursor Item → Ability → Equip → Status and one `press up` returned it to
Equip — exactly one step per press, both directions
(`studies/test-harness/scenarios/menu_nav.py`). Battle cursors and dialogue choices ride the same
site and are expected to follow, but are **not yet separately proven in-game**.

The gap it closed: the harness could open a menu (`Menu`/`Confirm`/`Cancel` all route through `IsInput`) but
**cannot move the cursor inside one**, and cannot pick a dialogue choice. That is the single biggest
gap, and hooking `GetAxisRaw` for the two navigation axes closes all four subsystems at once.

---

## Field (beyond MovePC)

| Site | Effect | What it governs |
|---|---|---|
| `UICamera.cs:954` | **ignored** | Moving the highlight between options in a field DIALOGUE CHOICE (Yes/No, multi-option scripted choices, Mognet choices, the Pandemonium elevator dialog, auction/quantity choice dialogs) — i.e. every choice a field .eb script asks the player to make. |
| `UICamera.cs:1449` | **ignored** | The vertical (up/down) step of the field dialogue choice cursor — the axis FF9 actually uses for a stacked choice list, since NGUIExtension.SetKeyNevigation only wires onUp/onDown. |
| `NetSyncField.cs:119` | **ignored** | The co-op field recovery action 'teleport to host' — dispatched from UIKeyTrigger.cs:188-195, which calls NetSyncClient.RequestTeleportToHost() when UIManager state is FieldHUD. |

## Menus and UI navigation

| Site | Effect | What it governs |
|---|---|---|
| `ConfigUI.cs:413` | **ignored** | Assigning a new keyboard key in Config -> Controller -> Custom (the captured key is written to FF9StateSystem.Settings.cfg.control_data_keyboard[currentControllerIndex] at :420). |
| `ConfigUI.cs:447` | **ignored** | Assigning a new controller button in Config -> Controller -> Custom, including the analog triggers: `:483 if (UnityXInput.Input.GetAxisRaw("LeftTrigger") != 0f && !hasJoyAxisSignal[0])` and `:491 ... GetAxisRaw("RightTrigger")` in CheckPCVitaJoystickKeys. |
| `UICamera.cs:954` | **ignored** | MENU CURSOR MOVEMENT (Up/Down/Left/Right) in every NGUI menu — main menu, item, ability, equip, status, config, shop, save/load, party, title. Also Config option value changes and Shop quantity +/-. |
| `UICamera.cs:1504` | **ignored** | The whole NGUI "OnKey" notification path: Tab / shift-Tab focus cycling (UIKeyNavigation.OnKey, :223), closing an open popup list with the cancel key (UIPopupList.OnKey, :413), and dropping focus out of a text field (UIInput.OnKey, :346). |
| `UIInput.cs:268` | **ignored** | Typing a character's name on the rename screen (NameSettingUI). NameSettingUI holds the field focused — `NameInputField.isSelected = true` at NameSettingUI.cs:49 and again at :131 — and the typed value is what is committed at NameSettingUI.cs:175 `FF9StateSystem.Common.FF9.GetPlayer(SubNo).Name =... |
| `UIInputOnGUI.cs:16` | **ignored** | Backspace, Delete, caret movement (arrows/Home/End), and copy/paste inside the name-entry field — UIInput.ProcessEvent (UIInput.cs:380) switches on ev.keyCode for UpArrow/DownArrow/RightArrow/LeftArrow/Home/End/Backspace/Delete with ctrl/shift modifiers from ev.modifiers. |
| `UIKeyTrigger.cs:740` | **ignored** | The direct-open menu shortcuts: Alt+F1 = Config UI, Alt+F2 = Party setting screen, Alt+F4 = Quit dialog, Alt+F5 = Save screen, Alt+F9 = Load screen, Alt+Space = widescreen toggle; also Shift+F4 / Ctrl+Shift+F4 encounter toggles at :795. |

## Battle

| Site | Effect | What it governs |
|---|---|---|
| `UICamera.cs:954` | **ignored** | ALL cursor movement inside the battle HUD: moving the command cursor (Attack / Ability1 / Ability2 / Item / AccessMenu), scrolling the ability list and the item list, moving the target cursor between individual enemies and party members, and BattleHUD's own AllEnemy<->AllPlayer group swap (Battle... |
| `BattleHUD.Scene.cs:97` | **ignored** | PSX/"Legacy Interface" battle command menu: holding Left slides in the CHANGE (party swap) command, holding Right slides in DEFEND. Called every battle tick from HonoluluBattleMain.YMenu_ManagerActiveTime (HonoluluBattleMain.cs:431 -> BattleHUD.UpdateSlidingButtonState). |

## Overworld / world map

| Site | Effect | What it governs |
|---|---|---|
| `ff9.cs:6151` | **ignored** | Overworld free-camera while on foot / on a chocobo (w_movementHumanOperation): right-stick X rotates the world camera (w_cameraSysDataCamera.rotation += stickX * 6f) and right-stick Y drives the camera aim-height tweak (cameraAimTweak, i.e. camera pitch). |
| `ff9.cs:6228` | **ignored** | Overworld free-camera while piloting a BOAT (w_movementShipOperation, w_moveCHRControlPtr.type == 2): right-stick X rotates the world camera; right-stick Y drives camera aim-height, but only when [Worldmap] AlternateControls is set. |
| `ff9.cs:6270` | **ignored** | AIRSHIP / flying-vehicle CLIMB and DIVE (w_movementPlaneOperation). leftStickY feeds `verticalMovementSpeed = ff9.S(-(Int32)ff9.w_moveCHRControlPtr.speed_updown * leftStickY / ff9.p1)` at ff9.cs:6310, i.e. the vertical throttle of the Hilda Garde / Invincible. |
| `ff9.cs:6305` | **ignored** | Overworld free-camera yaw while flying (w_movementPlaneOperation, airship / chocobo-flight). Adds stickX * 6f to w_cameraSysDataCamera.rotation each frame. |
| `ff9.cs:6652` | incomplete | ff9.w_moveGetPadStateR -- the FORWARD/REVERSE THROTTLE for every world vehicle: boat (w_movementShipOperation:6203) and airship/flying chocobo (w_movementPlaneOperation:6267, feeding w_moveCHRControl_XZSpeed). Also sets ff9.w_movePadDOWN for the plane at ff9.cs:6277. |
| `ff9.cs:10642` | **ignored** | Consumed at ff9.cs:6136 as `ff9.w_movePadDOWN = ff9.Pad.kPadLDown;` in w_movementHumanOperation. w_movePadDOWN is read at ff9.cs:2993 inside w_cameraSetEyeAim, where `if (ff9.m_GetIDTopograph(idall) == 49 \|\| ff9.w_movePadDOWN \|\| ff9.w_movePadLR) num11 = 4f;` quadruples the world camera's height c... |

## Title, boot and minigames

| Site | Effect | What it governs |
|---|---|---|
| `EndingUI.cs:166` | incomplete | The four DIRECTIONAL steps (Control.Up, Control.Down, Control.Left, Control.Right) of the hidden ending button code that unlocks the EndGame / Blackjack minigame -- blackjackKeyCodeList at EndingUI.cs:175-193. |
| `TitleUI.cs:1537` | **ignored** | Left/Right paging through the LICENSE / legal-notice pages on the title screen (TitleUI.OnKeyNavigate, lines 659-678, calls this.LicenseCenterOnChild.CenterOn(...) on KeyCode.LeftArrow / KeyCode.RightArrow). |
| `UICamera.cs:954` | **ignored** | Every NGUI menu CURSOR MOVE in this subsystem: the title menu selection (Continue / New Game / Load Game / Cloud / Language / Staff / Movie Gallery / Blackjack), the language-select list, the movie-gallery thumbnail grid, the Tetra Master card-collection screen (QuadMistUI), and the EndGame wager... |
| `Input.cs:309` | **ignored** | The terminal physical-key read behind all menu navigation above ("Vertical" at 309-310, "Horizontal" at 304-305); falls through to Input.GetXAxis(axisName) for the XInput stick/DPad when no key is down. |

---

## Deliberately out of scope

Some of the confirmed sites are real bypasses that the harness should **not** try to close, because
driving them is not a thing a test scenario legitimately does:

- **`ConfigUI` key/button rebinding** (`ConfigUI.cs:413`, `:447`) — captures a raw physical keypress
  in order to *assign* it. A virtual controller has nothing meaningful to assign.
- **Name entry** (`UIInput.cs:268`, `UIInputOnGUI.cs:16`) — reads Unity's IMGUI event queue and
  `Input.inputString`. If a scenario ever needs a custom character name, set it in the save data
  rather than typing it.
- **`UIKeyTrigger.cs:740` Alt+F-key shortcuts** — a developer convenience, and every screen they
  open is reachable by normal navigation once the cursor works.

`EndingUI.cs:166` (the hidden Blackjack unlock code) and `NetSyncField.cs:119` (co-op
teleport-to-host) are confirmed but niche; fix them only if a scenario needs them.

