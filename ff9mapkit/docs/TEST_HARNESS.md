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
