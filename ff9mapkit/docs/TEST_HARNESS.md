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
| `close_ui` | presses Cancel until the game is on a field, the world map, or the title |
| soft reset | FF9's own L1+L2+R1+R2+Start+Select — closes every dialog, disables all button groups and the battle menu, un-pauses, normalises `btl_seq`, and replaces the scene with Title |

**Why `close_ui` comes first, and how we know.** An earlier version of this page said the soft reset
"reaches a battle, a stuck menu or a black screen". That was wrong about menus.
`UIKeyTrigger.Update` runs `if (HandleMenuControlKeyPressCustomInput()) return;` **before** the
soft-reset check, and that handler consumes `Control.Select` unconditionally — note the neighbouring
Pause branch *is* guarded with `&& !SoftResetKeyPSXForPause`, so the engine authors protected the
combo from one branch and not the other.

Reading the code gave two answers, so it was measured instead
(`scenarios/soft_reset_reach.py`): **from a field YES, from an open MainMenu NO.** A menu is where a
scenario is most likely to end and `warp` also refuses outside `FieldHUD`, so without the `close_ui`
rung the ladder would have poisoned every scenario after one that left a menu open. That scenario is
now in the suite and asserts the measurement, so an engine change reports itself.

Two more things worth knowing:

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

⚠ Under a suite the run-level `report.json` carries **no verdict** — it points at `suite.json`
instead. It is written from the session's check list, which belongs to whichever scenario ran last,
so scoring it would describe one member and label it the run. (It did exactly that until an audit
caught it: a ten-scenario suite whose first nine failed wrote `"passed": true`.)

### What you get back

`.harness-runs/<stamp>-suite-<name>/` with a `suite.json` tally, and **one directory per scenario**
holding its own `report.json` and screenshots. Shots are namespaced by scenario, so two scenarios
both capturing `"before"` no longer overwrite each other — and the evidence you lose that way is
always the failing run's. Every check carries a snapshot of the game as it was when the check was
made, and **the first failure of each scenario is photographed automatically**, because re-running to
see what the screen looked like costs the whole suite.

---

## Battles

The state channel was completely dark on battles until `s83` rev 3. It now publishes the roster, HP,
MP, ATB, statuses, the command cursor, the rewards and the result:

```python
g.start_battle(67)                     # a REAL battle, not the diorama
for u in g.state.units(player=False):
    print(u["name"], u["hp"], "/", u["hp_max"])
g.expect_battle_result("victory")
```

**The traps are the design.** Almost every value the engine keeps is ambiguous or stale rather than
absent, so a plausible wrong answer is the default failure here:

- `battle_result` is **0 both during a battle and before any has ever run**, and it persists after
  one. Everything is anchored to `battle_epoch` (`party.battle_no`), the only unambiguous start edge.
- `IsBattleScene()` is true for the **diorama** too, which runs under `isDebug` where the engine
  suppresses the auto-end - a fight that can never finish. `in_battle` excludes it, and
  `wait_battle_over()` refuses outright rather than hanging.
- Each unit carries HP **twice**: `hp`/`hp_max` are the logical values the HUD shows, `hp_raw`/
  `hp_max_raw` are what the AI script reads. They differ by 10000 for a non-dying boss. Asking for
  "the" HP is asking the wrong question.
- `alive` is the **Death status bit**, not `hp == 0` - a unit under a DeathChanger effect sits at 0
  HP alive.
- `name` is rendered and `name_raw` is the source, because enemy names carry markup
  (`[STRT=27,1]Fang[ENDN]`).
- `phase`, `units` and `turn` are published **only inside a battle**. The engine leaves them holding
  the last fight's contents, and a full historical battle reported on a field is worse than nothing.

---

## Playing a battle

```python
g.start_battle(306)
slot = g.wait_turn()                  # the game's own "your move" -- who it is asking
menu = g.menus(slot)                  # what that character can do, BY NAME
g.act("Attack", slot=slot)            # or "Fire", or "Potion": commands, abilities and items
g.fight()                             # ...or just play the whole thing out
g.expect_battle_result("victory")
g.flee()                              # or leave, if the scene allows it
```

Names come from the engine (`FF9TextTool`, resolved through the character's preset, trance state and
equipment), so nothing here keeps a table that can drift. `act()` resolves a name in three places in
order - the command list, the ability list (its parent command is inferred), then the inventory -
and picks a legal target for the ability's own target type unless you name one.

WARNING: **`act()` tests the battle logic, not the HUD.** Nothing in it presses a button: it commits
through `BattleHUD.SendNetCommand`, the same entry point co-op uses. A scenario that must prove the
menu itself works wants `battle_act()`, which steers the cursor.

WARNING: **`menus()` is a request, and its answer is a snapshot.** Collecting it writes the HUD's
ability cache, so it is not part of every state sample - an instrument may not mutate what it
observes thirty times a second. It carries `slot` and `epoch`; `state.menu_is_for(slot)` is what
tells you the answer is about this battle rather than the last one.

WARNING: **wait for `turn_slot`, never for `turn_slot_raw`.** `CurrentPlayerIndex` is reset by
`InitialBattle()`, which runs *later* than the battle scene goes live - so through the opening
camera of the second battle in a session the raw field still holds the previous fight's slot. Acting
on it froze a fight solid: no HUD, no ATB, the intro camera held for four minutes. `turn_slot` is
published through the engine's own `FF9BMenu_IsEnable()` gate and is safe; the raw one is kept only
so that window is diagnosable.

Fleeing is a **dice roll**, not a duration: `200 / avgEnemyLevel * avgPlayerLevel / 16` percent per
unbroken second of holding, integer division throughout. `flee()` returning False is usually
variance. It raises - rather than returning False - if the engine never saw the hold at all, because
that is a different fault entirely.

---

## Walking, and why every measurement settles first

`walk_to(x, z)` steers on the published position rather than counting frames, and it calibrates
which button moves the character which way in world space (`calibrate_axes`) because FF9 fields are
viewed by a yawed camera - "up" is +z on one field and -x on the next.

WARNING: **a displacement only means something if the character was stationary at both ends.** The
engine's movement runs about a frame behind the input, so the tail of one burst lands in the next
one's measurement window. Measured on 30820, one frame of `left` was credited with 114 units of pure
-z - the previous `down` still finishing - and `walk_to` concluded the axis basis was wrong and
discarded a perfectly correct one. `Session.settle()` is what closes that window, and every
measurement here goes through it.

For the same reason the basis verdict only judges a burst whose movement is *consistent with what
was commanded*: far too little means the character is blocked (24 units when 1350 were asked), far
too much means the window was contaminated (114 when 30 were asked). Neither is evidence about the
basis.

Calibration will step away from a wall and re-measure rather than refuse where it stands - being
against a wall is a fact about where the character is, not about the field, and it varies between
runs. It still refuses ground no retry can fix, and it refuses to walk through a gateway while
backing off, since that would cache the next room's basis under this room's id.

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
