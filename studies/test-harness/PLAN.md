# The in-game test harness

**Goal:** lift the project's oldest hard constraint — *the agent cannot play the game*. Before this, a
change could be built, deployed and photographed (`tools/game_snap.ps1`) but never *exercised*: no
button could be pressed, the character's position was unknown, on-screen dialogue was unreadable. Every
behavioural claim cost a human playtest, and "it built" kept getting mistaken for "it works".

**Branch:** `claude/test-harness-8d39f7` · **Guide:** [`ff9mapkit/docs/TEST_HARNESS.md`](../../ff9mapkit/docs/TEST_HARNESS.md)

| Half | Where |
|---|---|
| Agent (engine) | `memoria-patches/s83-harness-agent.patch` → `Memoria/Harness/HarnessAgent.cs` |
| Driver (Python) | `tools/harness/` + `tools/play.py` |
| Offline tests | `ff9mapkit/tests/test_harness.py` (16, ~6s, no game needed) |

---

## Status

### ★ PROVEN IN-GAME 2026-08-27 (agent-run, against a live FF9)

- **Unattended launch** — no launcher window, no Play click, no changelog dialog. Agent publishing
  state 4s after process start.
- **State publication** — every other frame: ui_state, scene, fading, sys_mode, ScenarioCounter,
  field id + name, world id, player x/y/z + floor/tri + control, dialogue texts + choices, watched
  story-flag bits, held buttons.
- **Field warp** — `warp 30801` from a fresh New Game, landing playable.
- **New Game from the title** — `TitleUI.HarnessStartNewGame`, no menu navigation.
- **Virtual input reaching the engine** — a `Menu` press opened the main menu and `Cancel` closed it,
  observed as a real `ui_state` transition. Confirmed again by the engine's own readout: with a
  direction held, `input.key_up` and `input.move_key` are **both true for the whole hold**, i.e. the
  injected press is seen by `UIKeyTrigger.GetKey` and acted on by `FieldMapActorController`.
- **Screenshots from inside the renderer** — ~160 KB PNGs, no window focus, immune to the all-black
  frame exclusive fullscreen gives the external PrintWindow capture.
- **Artifacts** — `.harness-runs/<stamp>-<label>/` with `report.json`, `events.jsonl`,
  `state-final.json`, `Memoria.log`, `shots/*.png`.

### ★ RESOLVED 2026-08-27 — the character walks

`hold up 120` moved Zidane **1014 units** across bench 30801 (z -837 → +177), owner-witnessed live and
confirmed in the before/after frames the harness captured itself. The arc has no open question.

**Root cause — and it is a lesson, not a typo.** With `[AnalogControl] Enabled=1` (the shipped default
in this install) `FieldMapActorController.MovePC` reads `analogVector = GetAxis()` and ends with

```csharp
if (analogVector.magnitude <= stickThreshold) actualMoveVec = Vector3.zero;
```

`GetAxis()` returns **Unity's own** Horizontal/Vertical axes. A physical keyboard feeds them; an
injected press does not. So the axis stayed `(0,0)` and the move vector was zeroed **downstream of
every signal we were measuring**: `movingUp` true, `ccSMoveKey` true, `GetUserControl()` true,
`dash_inh` 0, and the actor even *rotated*, because the rotation block is gated on `movingUp` rather
than on the move vector. Six different fields therefore read as "not walkable", and the harness
looked correct at every point a probe could ask.

**The general law, worth carrying beyond this arc:** *hooking the accessor a diagnostic reads proves
nothing about the value that decides the outcome.* Every instrument we had agreed the press landed.
The instruments were all upstream of the one assignment that mattered.

**The fix** (both inert unless armed, so real play is untouched):

| Hook | Why |
|---|---|
| `HonoInputManager.GetAxis` → `HarnessAgent.TryGetAxis` | Synthesises a unit vector from held directions; falls through to the real axis when the harness holds nothing, so a human still drives an idle session. |
| `HonoInputManager.CheckPersistentDirectionInput` | The engine's raw `GetAsyncKeyState` "is a direction key physically down" probe. `FieldMapActorController` derives `isStickMovement` from it, and with `UseAbsoluteOrientation=3` (walkpath for keys, absolute for sticks) answering false would still move the character — but along the **stick** orientation model, so a scenario would walk a different direction than the same press does by hand. |

**What caught it, and what did not.** The smoke test asserted the press was *received* — `key_up`,
`move_key` — and every one of those assertions was true while the character stood perfectly still.
The acceptance test that now guards this (`scenarios/walk_check.py`) asserts the one thing a
half-wired input path cannot fake: **the position changed.** Prefer that shape of assertion.

---

## Engine deployment state

`Assembly-CSharp` is deployed with s83 (both arches, verified). **Inert without `ff9harness/arm`**, so
ordinary play is unaffected — that gating is what makes it safe on an install shared by ~26 worktrees.

Pre-build backups, newest last: `20260827-103835`, `20260827-111002`, `20260827-111541`,
**`20260827-181321`** (pre-axis-fix). Revert with `py tools/restore_memoria_dll.py <label>`.

The patch file is regenerated and gated: `git apply -R --check` is clean against the live tree, so
`s83-harness-agent.patch` is an exact description of what is deployed.

---

## Hard-won facts (each cost a failed run)

1. **`FF9.exe` cannot be started directly.** `BundleSceneSelector.Awake` calls the native
   `SteamAPIRestartAppIfNecessary()`, quits with code 0, and asks Steam to relaunch through
   `FF9_Launcher.exe` — which waits for a human to click Play, with a changelog dialog stacked in front
   after any DLL update. It also recursively deletes every `*steam_appid.txt` first, and setting
   `SteamAppId` in the environment does not stop it. s83 skips that one call **only when the arm file
   is present** (owner-approved 2026-08-27).
2. **The launch arguments are the launcher's**: `-runbylauncher -single-instance -monitor N
   -screen-width W -screen-height H -screen-fullscreen 0` (`UiLauncherPlayButton`).
3. **CWD is the GAME ROOT, not `x64`.** `StartGameProcess` never sets a WorkingDirectory, so the game
   inherits the launcher's. Launched from `x64` it gets surprisingly far and then dies inside
   `EncryptFontManager.SetDefaultFont` — font lookup is cwd-relative. `Memoria.log` follows cwd too.
4. **`.NET WriteAllText(Encoding.UTF8)` emits a BOM** and `json.loads` rejects it. Symptom: the agent
   published perfect state every frame while the driver reported "the agent never published state" for
   90 seconds. Read `utf-8-sig`.
5. **`os.replace` / `File.Replace` lose a Windows sharing violation** whenever the other side has the
   file open — at 30 writes/sec against a 30 Hz poll this is routine, in *both* directions. The driver
   retries; the agent skips (never spin for a file race inside the frame loop).
6. **`GetUserControl()` goes true before `GetControlChar()` does**, so "playable" must require a known
   position or movement assertions silently compare against `None`.
7. **The Bash tool's shell mangles backslash escapes and raw bytes in inline scripts.** Write the
   script to a file and run the file. → [[feedback-no-powershell-text-roundtrips]] (same family).
8. **Hooking the key booleans does not drive the character** — `[AnalogControl]` zeroes the move
   vector from `GetAxis()`, which is Unity's own axis and not on the `IsInput` path. See the
   resolution above; the transferable form is *the accessor a diagnostic reads is not the value that
   decides the outcome.*
9. **Settle ~10s on the title before New Game.** Memoria is still loading when the title appears, and
   starting during that window makes the opening cutscene run badly choppy (owner-observed). Now the
   default in `Session.newgame`; `settle=0` opts out.
10. **New Game lands in a CUTSCENE, not in control.** `newgame()` therefore waits for a *field*, not
    for control — requiring control there hung every scenario whose intent was "get in-game, then warp
    to the thing under test". `playable=True` opts back in.

---

## Next actions

The core loop is proven end to end. What is left is coverage and ergonomics, not feasibility.

The audit is **done** ([`INPUT-COVERAGE.md`](INPUT-COVERAGE.md), 22 confirmed / 6 refuted) and its
headline is **fixed** — NGUI navigation now works, so the harness can drive a menu.

1. **Assert on dialogue for real** — the state channel already carries `Dialog.Phrase` and
   `ChoicePhrases`, and the choice cursor now moves. The chest at 30810 (`expect_text("Potion")`) is
   the obvious first scenario; it exercises the narrative axis rather than the physical one, and it
   would separately prove the dialogue-choice half of the NGUI hook, which is currently only *expected*
   to work by sharing a code path with the menu cursor.
2. **World vehicles have no throttle** (`ff9.cs:6652`) and the overworld free-camera reads the raw
   right stick. Fix if an overworld scenario needs it — note camera yaw is not cosmetic there, it
   feeds `w_moveCHRControl_RotTrue` and changes which way a harness-driven walk goes.
3. **Publish the highlighted-widget name** in the state channel, so `menu_nav.py` can self-assert
   instead of leaving the verdict to be read off screenshots.
3. `Session.quit()` helper — disarming cancels the agent's pending queue, so a bare
   `send("quit", wait=False)` followed by teardown drops the step. Harmless today (the launched-game
   path waits on the process first) but a sharp edge.
4. Consider a nightly-gate lane for scenarios, separate from the offline suite — noting that scenarios
   need the real install and are therefore not a fit for the ordinary worktree gate.
