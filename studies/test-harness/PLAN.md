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

### ⚠ OPEN — the character does not translate

With `Up` held for 150 frames on **4010, 4011, 4012, 4013, 30416 and 30801**, position never changes
and successive frames differ only by idle animation. The engine says it received and acted on the
press (`key_up=true`, `move_key=true`, `dash_inh=0`, `control=true`, `floor=0`, `tri=0`).

Ruled out: window focus (tested foregrounded — no difference), the analog/stick branch (`axis_x/y` are
0, so the digital branch runs), and the driver (`held` matches what was scheduled, every frame).

**Not yet verified: whether a REAL keyboard press walks the character on these same fields right now.**
The owner expects it does, but could not test at the time — so this is an expectation, not evidence,
and the arc must not be closed on it. That one check is the next action and it splits the outcome:

- *Keyboard walks* → real and virtual input diverge somewhere past the movement decision. Suspect the
  apply/collision step, or a consumer reading `CheckPersistentDirectionInput` (raw `GetAsyncKeyState`,
  which the hook deliberately does not cover) rather than `IsInput`.
- *Keyboard does not walk either* → the harness is fully correct and this is a property of these test
  rooms or the current build (no walkmesh under the spawn, or a debug-warp arrival whose field script
  never finishes handing over). Record the harness as proven; file the movement question separately.

A secondary possibility either way: `PosObj.pos` may not be the record ordinary walking updates, making
this a *readout* bug rather than a movement one. The screenshots argue against it — he visibly stays put
— but on a static bench that is not conclusive.

---

## Engine deployment state

`Assembly-CSharp` is deployed with s83 (both arches, verified). **Inert without `ff9harness/arm`**, so
ordinary play is unaffected — that gating is what makes it safe on an install shared by ~26 worktrees.

Pre-build backups, newest last: `20260827-103835`, `20260827-111002`, `20260827-111541`.
Revert with `py tools/restore_memoria_dll.py <label>`.

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

---

## Next actions

1. **Resolve the movement question** with the keyboard A/B above. Everything else waits on it, because
   until it is answered the harness's most-used verb is unproven.
2. Point the smoke test at a genuinely walkable field once one is identified.
3. `Session.quit()` helper — disarming cancels the agent's pending queue, so a bare
   `send("quit", wait=False)` followed by teardown drops the step. Harmless today (the launched-game
   path waits on the process first) but a sharp edge.
4. Record a real scenario as a regression test once movement is settled — the chest at 30810 is the
   obvious first one (`expect_text("Potion")`).
5. Consider a nightly-gate lane for scenarios, separate from the offline suite.
