# The save-moogle REVEAL study (2026-07-19)

The decode behind `reveal_style = "barrel_pop"` — how a save moogle *presents itself* before you talk
to it, as opposed to the interact-time ACT (which was decoded in an earlier round and lives in
`content/savepoint.py`'s "THE MOOGLE'S ACT" section).

The conclusions are already in the shipped code and in [`docs/SAVEPOINT.md`](../../ff9mapkit/docs/SAVEPOINT.md).
This directory keeps the **working artifacts**, so the next round starts from the census rather than
rebuilding it.

---

## What's here

| file | what it is |
|---|---|
| `ebload.py` | **The `.eb` loader.** Resolves a NUMERIC field id → EVT name → the compiled script out of your install. Also `find_moogles()` and a whole-map `--census`. |
| `moogle_census.json` | The scan: **88 moogle fields, 58 of them save moogles**, with each moogle's entry index, model, per-tag sizes, and which tag holds `Menu(4,0)`. |
| `idcheck.py` | Byte-identity harness — proves a change leaves the DEFAULT `[[savepoint]]` output untouched. |
| `BARRELPOP/` | The playtest field (deployed at scratch id 30210). Placeholder art from `ff9mapkit new`; the `[[savepoint]]` block is the thing under test. |

### ⚠ Use `ebload.py`, not the kit's FBG path

`extract.extract_event_script()` takes an **FBG name**, and the FBG→EVT map **collapses fields that
share a background**. Fields **904 and 1904** (Treno, two story beats) share one FBG, so a name lookup
silently resolves to only one of them. Any census built that way quietly studies the wrong field.
`ebload.load(<numeric id>)` goes through `ID_TO_EVT` instead and keeps them distinct.

---

## What the census overturned

A prior round's taxonomy was wrong on five counts. The bytes win:

- **No save moogle is visible at Init.** All 58 spawn hidden (`SetObjectFlags(14)`) and are shown by an
  *external* entry writing a shared transient MAP byte. "plain" doesn't mean "visible from Init" — it
  means *the reveal case is a bare flag flip with no choreography*. The **who/when** axis (who writes
  the state var) is orthogonal to the **how-it-looks** axis, and no bucket captures it.
- **The shown-flag value is 5, not 7.** Map-wide tally over all 58: `14`×119, `5`×67, `7`×1, `15`×6.
- **Canonical `barrel_pop` is FOUR fields — 253, 351, 407, 853** — the only ones carrying the distinct
  airborne clip **2917**. Fields 1421 and 2655 also use `SetupJump` but reuse the Init-preloaded 6503
  hop clip: a separate, still-undecoded shape. (The decode round itself excluded 1421 for lacking 2917
  while keeping 2655, which also lacks it. Don't inherit the "×6".)
- **Field 706 is not "flying" and its reveal carries no greeting.** Zero `TO_FLY`/`FROM_FLY` bytes exist
  anywhere in 706; its `MAKE_A_BOW` 4968 fires in **tag 3 (the act)**. 706 has a *second* moogle
  (entry 8, an item-giving errand NPC) — the likely source of the original mis-scan.
- **306 is not "bespoke" alongside 115.** 115 locks control (`DisableMove`/`DisableMenu`) and faces the
  player across 13 windows; 306 does neither.

**Model does not predict style** — 810 is model 129 and plain.

## The invariant spine (4/4 canonical donors)

```
SetJumpAnimation(2917, blendA, blendB)
[TurnTowardPosition(x, z) ; WaitTurn]      <- 351 has no turn
RunJumpAnimation ; WaitAnimation
SetupJump(x, y, z, steps) ; Jump
RunLandAnimation ; WaitAnimation
```

Everything else is **per-donor, not law** — recorded as a table in `content/savepoint.py` so it can't be
promoted into an invented default again:

| field | sfx | emerge gesture | steps | blend | post-land dressing |
|---|---|---|---|---|---|
| 253 | 1363 | 2928 | 15 | (6, 23) | no |
| 351 | *none* | — | 6 | (4, 16) | no |
| 407 | 1362 (vol 99) | — | 10 | (4, 16) | yes |
| 853 | *none* | — | 10 | (4, 16) | yes |

## The cycle (field 407, the reference donor)

The moogle never reveals itself — it's a puppet on two shared MAP vars (**★ 2026-07-22: decoded END
TO END** — the director's full 44 instrs, the moogle's whole tag-1 switch, the cask's tags 29+30, and
the act's close-out tail; this section is now the complete decoded truth):

**The handshake**: any writer raises `MAP.Bit[327]` + writes `MAP.Byte[32]`; the moogle's tag-1 loop
consumes the state and clears BOTH every pass (its epilogue @rel 351). A writer's "wait" polls
`while (Bit[327] == 1)` — i.e. waits for the moogle's ack.

**The director is a ONE-SHOT LOAD SEQUENCE, not a post-save actor.** Entry-0 tag-1 issues
`1 (show) → 4 (disarm: moogle selfvar0 = 0) → 102 (stow: MoveInstantXZY into the cask + shrink to
(8,8,1))` back-to-back at field load, sets the background color, and dies at its RETURN — tag-1
functions run **once**; the moogle's loop persists only because it ends in an explicit jump back to
rel 0. (The earlier "the director walks 1→4→102 *after the save*" framing was wrong.)

```
load        director: show → disarm → STOW into the cask  (cask at x=-250, y=-2, z=-571;
            the moogle ends SHOWN but concealed inside the cask mesh, size (8,8,1))
press cask  cask tag 30: lock control, state=101
              -> moogle case 101 jumps STRAIGHT UP onto the cask (-250, -362, -571)
                 SAME x/z, only the height differs -- the hop is VERTICAL, nothing is hand-placed
                 (+ sets Int16[43]=1, the "moogle is out" latch)
            then state=3 -> case 3: selfvar0 = 1 = ARM the act (tag 3's head gates on it)
            then the cask SHRINKS its own press zone (1,50,50) -> (14,14,22): the moogle takes over
press again the moogle answers, opening its menu
Save        the ACT (tag 3): leaps OFF to a ground spot, book + save there, leaps back UP onto the
            cask; the act's OWN menu loop (@6590) redisplays the menu -- no director involved
Cancel      the act's CLOSE-OUT TAIL (@6593): turn + an ANIMATED dive back INTO the cask
            (RunJumpAnimation + SetupJump(-250, -2, -571, 10) + land), size restored, then
            RunScriptSync(cask tag 29) = RE-ARM: press zone back to (1,50,50), Int16[43] cleared
            -- the whole cycle is re-pressable
```

**Why the donor survives `SetPathing(1)` at the perch (the live bug's root cause):** the act calls it
at BOTH lerp ends (@538 ground, @761 the cask top) — and the perch call is inert **only by geometry**:
the cask corner `(-250, -571)` has **no walkmesh triangle** under it (verified against 407's `.bgi`;
nearest walkable is `(0, -400)`). A kit field's cask on walkable ground gets snapped down into the
barrel by the same call. The kit now derives the pathing arg per spot: floor → attach, off-floor →
detach (`act_save_body` + `reveal_state_loop`, 2026-07-22).

State writers, whole-field: entry 0 tag 1 (**the director**, load only) writes `1 → 4 → 102`; the
moogle's Init writes `MAP.Byte[38] = 200`; the cask's tag 30 writes `101` then `3`.

⚠ **Coordinate convention.** The kit's emitters take `y` as height with **UP = POSITIVE** and negate on
encode. The donor's raw `-362` is kit `+362`. Getting this backwards puts the moogle underground with
no build-time signal.

---

## Where this stopped — the frontier

**1. After a SAVE the moogle lands *in* the barrel instead of *on* it. ★ ROOT-CAUSED + FIXED
2026-07-22 (playtest pending).** The prescribed decode (the director end to end) was executed and
settled the suspect list: it was **(a)** — and *only* (a). The director **never re-places anything**
(it is a one-shot load sequence; suspect (b) is refuted), and the donor's own act DOES call
`SetPathing(1)` at the perch — surviving purely because its cask corner is **off the walkmesh** (no
triangle to snap to; probed against 407's `.bgi`). The kit's demo cask sat ON walkable ground, so the
re-attach snapped the perched moogle down into the barrel. Fix: the pathing arg is now derived from
each spot's height (floor → `SetPathing(1)`, off-floor → `SetPathing(0)`), in `act_save_body`'s two
sites + the reveal loop's pop (detach on the perch) and stow (re-attach at ground) arms. Ground
savepoints are byte-identical. The lesson the frontier note predicted held exactly: three rounds
synthesized around the undecoded piece, and the 44-instruction read settled it in one.

**2. The menu carries no speaker name.** Field 407's Init seeds **`MAP.Byte[37] = 8`** (Kumop's roster
id) and every window renders it through **`[TEXT=0,0]`**. The kit does exactly this — but only when
`[savepoint.mognet]` is configured (`build._speaks_as_roster` + the `prologue=` hook on
`save_dispatch_menu`/`_prompted`). Giving any save moogle a roster identity is the fix. The project
owner granted a provenance exception for the menu wording ("the wiki-with-dialog case").

## The process lesson

Across three build rounds, **every** playtest bug was in kit-authored *control flow* — never in
donor-derived constants. Geometry, clips, SFX and the tent heals were right throughout. The three:
dead code appended past a `RETURN`; a **guessed** opcode (`0x9A` `EnablePathTriangle` for
`HideAllObjects`, really **`0xD5`**); and a backward-jump displacement that omitted the if-condition's
5 bytes and landed mid-instruction. All three passed a green suite, because the emitter faithfully
emitted what it was told.

**Disassemble the BUILT FIELD, not the emitter's output** — that is what caught the last two. And
finish the decode *before* authoring an emitter: a 188-agent decode round produced less usable
correction than eight lines of playtest notes.
