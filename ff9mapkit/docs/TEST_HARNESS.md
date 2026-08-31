# The in-game test harness

Drive a real running FF9 from Python: press buttons, read where the character is, read what the
dialogue box says, capture frames, and assert on all of it.

This lifts the project's oldest hard constraint. Before it, a change could be built, deployed and
photographed (`tools/game_snap.ps1`) but never *exercised* — so every behavioural claim cost a human
playtest, and "it built" was routinely mistaken for "it works".

> **It does not replace playtesting.** The harness answers *did the mechanism fire* — did the field
> load, did the flag set, did the chest give a Potion, did the character actually move. It cannot
> answer *does it feel right*, and it cannot see anything it was not told to look at. Feel, framing
> and art judgment stay with the human. This is the same lesson the gate suites taught: **a green run
> is a regression harness, not an oracle.**

---

## The two halves

| Half | Where | What it does |
|---|---|---|
| **Agent** | `memoria-patches/s83-harness-agent.patch` → `Memoria/Harness/HarnessAgent.cs` | Injects virtual controller input, publishes per-frame state, captures PNGs from inside the renderer. |
| **Driver** | `tools/harness/` + `tools/play.py` | Owns the process, sends steps, waits on state, records checks, keeps artifacts. |

They meet over four files in `<game>/x64/ff9harness/`:

```
arm            presence gates the whole mechanism -- no file, no harness
req.txt        driver -> game.  line-oriented text, first line `seq <n>`
state.json     game -> driver.  rewritten every other frame
events.jsonl   game -> driver.  append-only log of accepts, acks, shots, errors
shots/         PNGs captured by the engine itself
```

Text in, JSON out — deliberately asymmetric. The game side must parse requests inside the frame loop
and Assembly-CSharp bundles no JSON library, so a text protocol costs it a `Split`. The driver side
reads JSON for free. Neither half hand-rolls a parser it did not need.

### It does not take your keyboard

Input is injected at `HonoInputManager.IsInput` / `IsInputDown` / `IsInputUp` — the single choke point
every consumer reads. The game believes a controller button is held. Consequences worth knowing:

- **No window focus needed.** The game can sit behind your editor while a scenario runs.
- **Real input still works**, because the harness value is OR-ed in, never substituted. You can grab
  the controller mid-scenario and drive the same session by hand.
- Screenshots come from `ReadPixels` inside the engine, so they cannot return the all-black frame that
  exclusive fullscreen gives the external `PrintWindow` capture.

### It is inert unless armed

With no `ff9harness/arm` file, `HarnessAgent.Active` is a false static, the input hooks early-out on
one branch, and nothing is written. An unarmed engine behaves identically to an unpatched one — which
is what makes this safe on an install shared by many concurrent worktrees and by the person who
actually plays this game. The driver creates `arm` on start and removes it on teardown, **including
when the scenario raises**.

⚠ **Arming is a TRANSITION, not a file that exists.** The agent compares the file against its own flag
and returns early when they agree, so writing over an existing `arm` changes nothing on its side: the
sequence numbers are not reset, held buttons are not released, the error latch is not cleared. A run
that inherits a leaked arm therefore has every request discarded as stale *while the stale ack answers
its waits* — every step a silent no-op reported as success. The driver deletes, waits out the agent's
30-frame poll, then creates, and it will not start at all while another **live** run owns the arm (the
file carries the owner's pid).

### It does not touch your save

⚠ **It used to.** Measured on 2026-08-31: an ordinary `newgame(); warp()` — the opening every scenario
shares — rewrote both live save containers, because `EventEngine` autosaves on ordinary field entry and
`DisableAutoSave` is 0 on this install. Manual slots survived; the autosave did not.

Two defences now:

- **The engine sandboxes** (`s83` rev 2): while armed, saves go to `ff9harness/save/` instead of your
  save folder, and the path is published so the driver can check it. `Session.start()` **refuses to
  run** if the engine says it did not redirect. A sandbox that is trusted rather than verified is a
  check that cannot fail.
- **The driver backs up** the live containers into `<run>/saves-before/` before the game is launched,
  on every engine version, and tells you at teardown if any of them moved.

---

## Running a suite

One launch, many scenarios. The overhead a harness pays is almost all fixed -- a cold boot, the title
settle, the New Game cutscene -- and paying it once instead of ten times is most of what makes the
harness usable day to day. Measured on the core suite: **ten scenarios in 264s, against 519s run
one at a time.**

```bash
py tools/play.py --suite studies/test-harness/suites/core.toml
```

A manifest is TOML, and paths resolve against the repo root so it reads like the command line you
would otherwise have typed:

```toml
[suite]
name = "core"
field = 30801                 # default bench; a scenario entry can override it

[[scenario]]
path = "studies/test-harness/scenarios/walk_check.py"

[[scenario]]
path = "studies/test-harness/scenarios/cutscene_check.py"
field = 30601
```

### The isolation contract

Sharing a launch means sharing state, so the runner's real job is making sure a scenario that leaves
the game in a menu, mid-battle or on a black screen cannot poison whatever runs next.

**The baseline is the TITLE SCREEN** — not "a field", not "wherever the last one finished" — because
every scenario opens with `newgame()`, and that verb requires it.

The ladder, one rung at a time, **each followed by re-checking the precondition rather than assuming
the rung worked**:

| Rung | What it does |
|---|---|
| `reset` | releases every held button, clears the watch list, restores timescale |
| soft reset | FF9's own L1+L2+R1+R2+Start+Select — closes every dialog, disables all button groups and the battle menu, un-pauses, normalises `btl_seq`, and replaces the scene with Title |

The soft reset is the only rung that reaches a **battle** or a **black screen**; `warp` refuses
outside `FieldHUD`. Two things about it worth knowing:

- **All six buttons must report `IsInputDown` on the same frame**, which is why they go in one
  request — every step of a request drains in a single pass, so their Down edges coincide. Six
  separate presses would never overlap and the reset would simply never fire.
- It is gated on `[Control] SoftReset` in `Memoria.ini` (1 on this install; the **engine** default is
  0), so `soft_reset()` asserts the title actually arrived and raises naming that setting otherwise.

### Verdicts, and the two that exist to stop the suite lying

| Verdict | Means |
|---|---|
| `pass` | ran, recorded checks, all passed |
| `fail` | ran, at least one check failed |
| `error` | raised — the next scenario still runs |
| **`poisoned`** | **never ran**: the runner could not give it a clean baseline |
| **`proved-nothing`** | ran and recorded no checks |

`poisoned` is the important one. A scenario that never ran cannot have failed, and recording it as a
failure would be the harness blaming the game for its own inability to clean up — the exact mistake
this arc has already made three times. Neither `poisoned` nor `proved-nothing` counts toward a pass,
and the exit code is 0 only when every member passed.

### What you get back

`.harness-runs/<stamp>-suite-<name>/` with a `suite.json` tally, and **one directory per scenario**
holding its own `report.json` and screenshots. Shots are namespaced by scenario, so two scenarios
both capturing `"before"` no longer overwrite each other — and the evidence you lose that way is
always the failing run's. Every check carries a snapshot of the game as it was when the check was
made, and **the first failure of each scenario is photographed automatically**, because re-running to
see what the screen looked like costs the whole suite.

---

## What the driver refuses to tell you

A harness that reports confidently and wrongly is worse than no harness, and this one did it three
times before the defects were found. So a number of verbs now decline rather than guess. If one of
these fires, it is telling you it *cannot know* — not that the game is broken.

| It refuses | Because |
|---|---|
| a step whose request the agent never accepted | `req.txt` is one last-write-wins slot; overwriting it destroys the previous request invisibly |
| a predicate that raised on every sample | that is a broken assertion, not a failed game condition |
| a wait satisfied only by a frozen channel | a hung agent's last `state.json` satisfies most predicates |
| `warp` when no `DictionaryPatch.txt` can be read | "nothing is registered" and "I could not read the registrations" are different facts |
| an axis basis measured against a wall | the character keeps *moving* when he slides, so "did it move" cannot catch it |
| `expect_text("")` | `"" in anything` is true — it passed against an empty screen |
| `timescale 0` | the engine runs no logical ticks while every step still acks |
| a field verb on the overworld | `player.x` there is the same value ×256 — a different space, not a null |
| `menu_labels()` with no menu open | those 30 direction presses would drive the field instead, walking the character under test |
| a second run while another live one owns the arm | they would delete each other's artifacts and overwrite each other's requests |

`report.json` has three verdicts, not two: `pass`, `fail`, and **`proved-nothing`** for a run that
recorded no checks. It also records `driver_protocol` and `engine_protocol`, because a green run
against an older channel is green *under caveats*.

---

## Running one

```bash
py tools/play.py --smoke
```

The smoke test is the end-to-end proof that the loop is closed: it waits for the agent, starts a new
game if it is sitting at the title, checks the player has control, walks, **verifies the character's
position actually changed** (accepting a button is not the same as acting on it), and captures a frame.
Run it first whenever a harness result looks strange — it tells you whether the harness or the content
is the liar.

```bash
py tools/play.py --smoke --field 30810
```

Same, but warps to a slot first.

```bash
py tools/play.py scenarios/chest.py
```

A scenario is plain Python exposing `run(g)`:

```python
def run(g):
    g.newgame()
    g.warp(30810)
    g.walk("up", 45)
    g.press("confirm")
    g.expect_text("Potion")
    g.shot("after-chest")
```

Exit code is 0 only when every check passed **and at least one check was recorded** — a scenario that
asserts nothing is reported as having proved nothing, rather than passing.

Artifacts land in `.harness-runs/<stamp>-<label>/`: `report.json`, `events.jsonl`,
`state-final.json`, `Memoria.log`, and every `shots/*.png`.

### Process safety

The harness **refuses to start when an FF9 is already running** and only ever closes a game it
launched itself. Pass `--attach` to deliberately drive the running one (useful for poking at a
session you already have set up), or `--keep-open` to leave the game up after the scenario.

---

## The driver API

```python
from harness import Session

with Session(label="chest") as g:
    ...
```

**Acting**

| Call | Notes |
|---|---|
| `g.press(button, frames=2)` | Tap, and block for its duration. |
| `g.hold(button, frames)` | Start holding, do **not** block — so you can walk and act at once. |
| `g.release(button)` | |
| `g.walk(direction, frames)` | `hold` + `wait`. The everyday movement verb. |
| `g.wait_frames(n)` | The explicit sync. |
| `g.newgame()` | Title → New Game → control on a field. |
| `g.warp(field, entrance=, scenario=)` | Warp and wait until actually playable. |
| `g.teleport(x, z)` | Overworld position. |
| `g.flag(bit, value)` / `g.poke(index, value)` | Story flags / raw `gEventGlobal` bytes. |
| `g.timescale(x)` | Speed the game up — a long walk need not cost real seconds. |
| `g.shot(name)` | Returns the PNG path once it is on disk. |

Buttons take the enum names plus the aliases you would actually type: `confirm`/`x`, `cancel`,
`menu`, `special`, `start`, `select`, `up`/`down`/`left`/`right`, `l1`/`r1`/`l2`/`r2`. An unknown name
is rejected locally rather than shipped to the game.

**Observing**

`g.state` is a fresh sample: `.field_id`, `.field_name`, `.ui_state`, `.scene`, `.fading`,
`.sys_mode`, `.scenario`, `.player_x/y/z`, `.pos`, `.control`, `.world_id`, `.dialog_open`, `.texts`,
`.text`, `.choice`, `.held`, `.flag(bit)`.

`g.watch(*bits)` publishes those `gEventGlobal` bits in every later sample — flags are otherwise not
reported, because dumping 2048 bits per frame is noise.

**Waiting and asserting**

| Call | Notes |
|---|---|
| `g.wait_for(pred, timeout=, what=)` | Raises with the last state it saw. |
| `g.wait_playable()` | Waits for **control on a field**, not merely "the field loaded". |
| `g.expect(pred, description)` | Records a pass/fail instead of raising. |
| `g.expect_field(id)` / `g.expect_text(fragment)` / `g.expect_flag(bit, value)` | |
| `g.check(ok, description, detail)` | Record a result you computed yourself. |

`expect*` is non-fatal on purpose: one scenario should report **every** failed expectation, not stop
at the first.

> **`wait_playable`, not "the field loaded".** A field is loaded, faded in and rendering long before
> its entry script hands control over. A scenario that starts walking too early silently drops its
> input on the floor and then fails somewhere unrelated, which is a miserable thing to debug. Every
> built-in verb that lands you somewhere new already waits for control.

---

## Testing the harness itself

`ff9mapkit/tests/test_harness.py` drives the **driver** against `harness.fakegame` — a protocol
stand-in that implements the s83 wire format and nothing else. It runs in about five seconds with no
game.

Be precise about what that proves. A green run says sequence numbers advance and are awaited, torn
`state.json` reads are survived, waits are bounded and report the last state, a dead game is detected
instead of hung on, artifacts land, and the process guard holds. It says **nothing** about whether the
engine patch behaves. That is what `--smoke` against a real game is for.

The stand-in has already earned its keep: it caught the ack latch bug — the ack was held on a
frame-local "was the queue busy", so any command whose last step blocked (press, wait, warp, shot —
almost all of them) lost its ack forever and hung until timeout. That was found in five seconds
instead of across a dozen 40-second game launches, and the same bug was fixed in the engine.

---

## When something goes wrong

| Symptom | Likely cause |
|---|---|
| "the agent never published state" | The running engine predates s83, or the game never reached the title. Check the run's `Memoria.log`. |
| "FF9 is already running" | By design. Close it, or pass `--attach`. |
| Steps acknowledged but nothing happens | The game is in a UI state that ignores input (a transition, a modal). Sample `g.state.ui_state`. |
| `warp` refused | `Ff9mkDebugMenu.Warp` only fires from `FieldHUD`; use `world_warp` from the overworld. |
| Everything times out at once | The agent disarmed after an unhandled error — grep `Memoria.log` for `[ff9mk harness]`. |

The agent logs through `Memoria.Prime.Log.Message`, the only channel that reaches `Memoria.log`; a
plain `Debug.Log` is dead-lettered.
