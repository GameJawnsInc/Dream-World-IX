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

## The action library (calibrated in-game 2026-08-27)

Verbs are **closed-loop on published state**, never on frame counts. The calibration below is what
sizes a burst; correctness never depends on it being right.

| Verb | Notes |
|---|---|
| `walk_to(x, z)` | Steers on position. One axis at a time; walk speed for the final approach; gives up after two no-progress bursts. |
| `calibrate_axes()` | Probes which button moves which way in world space, per field, and rejects a deflected basis. |
| `interact()` | Confirm, then report the dialogue or `None`. Silence is a legitimate observation, not an error. |
| `advance()` | Pages a conversation, returning every distinct page. **Stops at a choice** rather than blundering through it. |
| `prompt()` / `options()` / `select(i)` / `choose(i)` | Choice handling. `select` is split from `choose` so cursor movement is assertable — confirming destroys the evidence. |
| `warp(id)` | Refuses an unregistered id up front (see below). |
| `expect_field_change()` / `cross(x,z)` / `find_transitions()` | Field transitions, including sweeping for an **invisible** gateway. ★ Proven: 30820 → 30821, gateway located by sweep. |
| `wait_control()` / `watch_cutscene()` | Sits through a withheld-control sequence, advancing boxes, returning the transcript. ★ Proven on 30601 (~9.8s, 5 pages, twice). |
| `open_menu()` / `menu_labels()` / `menu_pick(label)` | Menus driven **by name**, verified against the engine's published highlight. ★ Proven: read the full main menu and picked "Status". |
| `flag(n)` / `poke(i, v)` / `watch(*n)` / `expect_flag(n)` | `gEventGlobal` story state. ★ Proven: set/clear round trip, neighbours untouched, byte↔bit agreement, survives a field reload. |
| `recon` / `recon_all` scenarios | Visit fields and photograph them. One launch amortised across every bench. |
| `diagnose()` | Explains a hang from the engine log instead of from driver symptoms. |

### Menus and story flags (added 2026-08-27)

**Menus are driven by LABEL, never by keypress count.** The agent publishes the highlighted widget
(`UICamera.selectedObject`, falling back to `hoveredObject`) and the `UILabel` text under it, so
`menu_pick("Status")` moves until the engine itself says "Status" is highlighted. Counting presses is
what let the dialogue-choice off-by-one pick the wrong option, and menus are worse — entries get
reordered by content and hidden by story state, so "three downs" means different things on different
saves. Read back live on 30801: `Item, Ability, Equip, Status, Order, Card, Form Party, Journal,
Config`.

⚠ **`ui_state` does not change for menu SUB-screens.** Confirming "Status" enters character select and
`ui_state` stays `MainMenu`; the tell is `menu_label` becoming a character-name token (`[ZDNE]`).
Assert on the highlight, not on `ui_state`, inside a menu.

**Story flags round-trip correctly.** `flag`/`poke`/`watch` were written in the first build and never
exercised until now. Proven on a fresh game: bits start clear, set and clear round-trip, **neighbours
in the same byte stay untouched** (the check that actually proves the bit math rather than "something
changed"), a raw byte poke of `0b10000101` decodes to exactly flags 8712/8714/8719 — confirming
`gEventGlobal[n >> 3]` bit `n & 7` — and the values survive a field reload.

⚠ Allocate from **8712** up. 8512-8711 is stock read-mail payload written a whole byte at a time by
ordinary play, and 8376-8511 is the MOGNET lock band; either is a live save-corrupter.

### Measured constants (30801 bench)

- **Run 30.0 units/frame; walk 15.0** — so **Cancel is the WALK modifier**, running is the default.
- Diagonal 29.6, not 42 — the synthetic axis is normalised, as intended.
- **Movement saturates against the walkmesh edge:** a 75-frame hold covered 1014 units where 30 u/frame
  implies 2250. This is why `walk(direction, frames)` is a bad primitive and `walk_to` exists.

### Three traps these runs surfaced

1. **Warping to an unregistered id black-screens the game** on a null `.eb`, and reaches the driver as
   a generic timeout blaming *control* or *position*. `warp` now reads the live `DictionaryPatch.txt`
   files and refuses first. Ids are a global namespace shared with every other worktree's deploys, so
   yesterday's bench may simply not be there today. Currently registered: **4010–4013, 30416, 30801**.
2. **The choice-option off-by-one.** `Dialog.ChoicePhrases` prepends the whole pre-choice header as
   element 0 while `SelectChoice` counts only selectable lines from zero. Asking for index 3 against
   the raw array — which reads "Minigames" — left the cursor on **Tetra Master**. For a story scenario
   that is the difference between testing a branch and testing a different one. `options()` now drops
   the header so its indices are the ones `select()` lands on. `ChoicePhrases` can also be *shorter*
   than `count` (a 15-option menu published 13 phrases), so **`count` is authoritative**.
3. **A box is open before it has words.** `ActiveDialogList` carries the dialog before `Phrase` is
   assigned, so a probe stopping at `open` reads an empty string.

### ★ RESOLVED — "walking out of 30820 hangs the game" was MY BUG, not the field's

**The gateway works.** 30820 → 30821 crossed cleanly, destination handed over control, 3/3 checks.
It sits on bearing **180° (south)**, ~950 units from the arrival point.

**What was actually happening.** The driver's `state.json` read was livelocking against the agent's
publish. The agent used the textbook publish-atomically idiom — write a temp, `File.Replace` it — and
`ReplaceFile` demands **exclusive** access to the destination. That file is rewritten ~30×/second and
the driver polls it every few milliseconds, so the two fought: the driver's open blocked the replace,
the agent skipped the publish, the driver's next read hit the replace that did get through. The
channel stalled for seconds at a stretch, leaving `state.json~RF********.TMP` wreckage in the channel
directory as evidence.

The stall was cheap. **The diagnosis was expensive.** The driver reported it as "no state published",
concluded the game was hung, and the blame landed on the field — I wrote "walking out of room 30820
hangs the game" into a commit message and a study. The game was fine throughout: instrumenting the
raw channel file showed `process alive: True`, and the last good sample had the character at the far
north wall with control, on the right field, not fading.

**Fixes:**

| Where | Change |
|---|---|
| agent | `state.json` is written **in place with `FileShare.Read`**, not replaced. A reader is never locked out; it can catch a partly written document instead, which the driver already retries. A torn read recovers itself, a lock does not. |
| driver | `Channel.state()` distinguishes `PermissionError` (a transient sharing violation — wait it out on a long budget) from `FileNotFoundError` (genuinely absent). Treating a lock as absence is what declared a healthy game dead. |
| driver | `diagnose()` dropped its `invalidFieldMapID` marker. The engine emits that during an ordinary New Game boot, so it matched on **every** run and confidently blamed a bad warp for whatever had gone wrong. A marker that fires routinely is worse than no marker. |

**A second, independent error compounded it.** The first sweep used radius 430 and began due north.
The gateway is due *south* at ~950, so even with a healthy channel it would have reported "no gateway
here". Overshooting a sweep is free — `walk_to` stalls harmlessly against the mesh — while
undershooting silently returns the wrong answer.

**A red herring, for the record:** `EVT_ROOM_A`'s gateway handler contains `PreloadField(5, 103)` and
stores 103 while warping to `Field(30821)`. That looks wrong and is not: the crossing works. Do not
"fix" it on the strength of reading the disassembly.

**The transferable lesson:** when a tool says the system under test is broken, suspect the tool first
— especially when the tool is new. Three separate false statements came out of this one arc, and each
was a confident explanation rather than an admission of ignorance.

### Three of my own tools lied, and each is now fixed

1. **`diagnose()` read a stale log.** `Memoria.log` is written relative to the working directory, so
   both the game root and `x64/` hold one and either may be hours old. Reading them in a fixed order
   made it report a `NullReferenceException` from **eight hours earlier** as the cause of a live hang.
   It now takes the newest, refuses to speak from a log older than 5 minutes, and names the file it
   read. `_collect_log` already did the right thing, which is exactly why the archived log disagreed
   with the diagnosis and gave the game away.
2. **`--field` was silently ignored for scenarios.** `play.py` called `scenario.run(g)` and dropped
   the flag. Nothing was ever mis-tested — the values I passed happened to match the module defaults —
   but the flag was lying about what had been exercised. It is now passed when `run()` accepts it, and
   says so when it does not.
3. **`watch_cutscene` was non-deterministic.** Control flickers true for a moment as a field loads,
   before the script takes it away, and a single sample was enough to return early: the same verb on
   the same bench produced **0 pages on one run and 5 on the next**. It now requires the end
   condition to *hold* for ~1s. Two consecutive runs since: 5 pages, ~9.8s, both.

### On flattering tests

The first `walk_to` acceptance run scored **0.0u on every leg** and was discarded rather than
celebrated: the offsets were +300 and the run speed is exactly 30, so every leg divided evenly and
landed dead-on in a single burst. It could not have detected a convergence bug. Re-run with offsets
coprime to both 30 and 15 it lands 13.0 / 35.4 / 27.2 units out — the loop actually closing. Likewise
`talk_check` first passed on "something answered" while one responder returned an open box and zero
pages; asserting per-responder turned that shrug into a real diagnosis.

★ The choice work also **closes the last gap left open by the NGUI hook**: dialogue choices were
previously only *expected* to work by sharing a code path with the menu cursor. `select(3)` landing on
"Tetra Master", confirmed in the captured frame, proves it directly.

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
