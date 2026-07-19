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

The moogle never reveals itself — it's a puppet on two shared MAP bytes plus a **director**:

```
load        hidden INSIDE the cask                       (cask at x=-250, y=-2, z=-571)
press cask  cask tag 30 writes state 101
              -> moogle case 101 jumps STRAIGHT UP onto the cask (-250, -362, -571)
                 SAME x/z, only the height differs -- the hop is VERTICAL, nothing is hand-placed
press again the interact target has SWITCHED: the moogle answers, opening its menu
Save        leaps OFF to a ground spot, book + save there, leaps back UP onto the cask
Cancel      hops back down INTO the cask  (case 102: MoveInstantXZY to the cask's own spot + shrink)
```

State writers, whole-field: entry 0 tag 1 (**the director**) writes `1 → 4 → 102`; the moogle's Init
writes `MAP.Byte[38] = 200`; the cask's tag 30 writes `101` then `3`.

⚠ **Coordinate convention.** The kit's emitters take `y` as height with **UP = POSITIVE** and negate on
encode. The donor's raw `-362` is kit `+362`. Getting this backwards puts the moogle underground with
no build-time signal.

---

## Where this stopped — the frontier

**1. After a SAVE the moogle lands *in* the barrel instead of *on* it.** Still open; two attempted fixes
did not resolve it. Ruled out by inspecting the built field: the act's return lerp is correct
(barrel-top → ground → barrel-top), and the reopen jump lands on an instruction boundary (that fix was
real, but it fixed the post-save *cancel softlock*, a different symptom). Suspects, in order:

- **(a)** `act_save_body`'s `SetPathing(1)`, which runs *after* the return lerp and may snap the actor
  onto the walkmesh, off its perch — the donor calls it too, but its moogle may be re-placed afterwards
  by the director.
- **(b)** the donor's post-save state walk — the director drives `1 → 4 → 102`, and case 102 *is* the
  stow, so the kit may simply be missing the re-place step.
- **(c)** the act's `_self_angle_flip` / head-focus close-out.

> **NEXT MOVE: decode field 407's entry-0 tag-1 director end to end.**
>
> ```
> cd ff9mapkit
> py ../studies/moogle-savepoints/ebload.py 407 --disasm 0:1
> ```
>
> It is 222 bytes and is the one piece of this cycle never fully read. Three attempts
> synthesized *around* it instead; that is why the shape kept coming out wrong.

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
