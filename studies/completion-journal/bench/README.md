# Completion-journal rung-0 probe (field 30800)

One field, one window, seven live reads, one playtest round. It exists to falsify the
DLL-free half of the journal ladder before any of it is built: **if a row reads a stuck 0
while the game state says otherwise, that mechanism is dead** and the tier that depends on
it has to be re-scoped.

Files: `journal_probe.field.toml` (the whole probe), `art/` (the `ff9mapkit new`
placeholder background — a bench needs no real art).

## The headline correction

`studies/completion-journal/PLAN.md` §7.1 / §T1b called the expression-valued
`SetTextVariable` an unexercised mechanism and a kit gap. **It is neither.** The kit
already emits `66 02 <slot> <RPN tokens…> 7F` at three in-game-proven call sites:

| call site | what it publishes | status |
|---|---|---|
| `ff9mapkit/content/behavior.py` (HUD live pass) | behavior counters / gil / hp | proven, benches 30410-30416 |
| `ff9mapkit/content/numinput.py:413` | the Treno bid stepper's submit echo | proven, bench 30417 |
| `ff9mapkit/content/mognet.py:292` | mail sender/recipient names | proven |

Only the *named helper* was missing; it now exists as
`ff9mapkit.eb.opcodes.set_text_variable_expr`, and the HUD emitter calls it.

**So scope the playtest accordingly.** Slots 1-4 and 6 are cheap confirmations. The two
rows that have genuinely zero precedent in this kit are:

- **slot 0 — `Null.SBit[5]`**, a Memoria *custom variable* read
  (`EBin.cs:1689` → `GetMemoriaCustomVariable`, `memoria_variable.TREASURE_HUNTER_POINTS`
  = enum index 5, `EBin.cs:2416-2431` / `:1703-1704`). Never executed here.
- **slot 5 — `flex(16,3)`**, a `flexible_varfunc` read (`PLAYER_ABILITY_LEARNT`, the 17th
  entry of `EBin.cs:2388-2413`; implementation `EBin.cs:421-435`). Never executed either.

Both reads are **upstream Memoria**, absent from `memoria-patches/` — genuinely
stock-DLL-free, no custom engine required. The probe is a novel field, so it also needs no
fork-gate suite: nothing in the setup can confound a null result.

## What the seven rows are

| slot | reads | bytes |
|---|---|---|
| 0 | Treasure-Hunter points | `66 02 00 c3 05 7f` |
| 1 | ScenarioCounter | `66 02 01 dc 00 7f` |
| 2 | chocograph FOUND bitfield, RAW | `66 02 02 c8 bb 7f` |
| 3 | …and masked to 24 bits | `66 02 03 c8 bb 7e ff ff ff 00 24 7f` |
| 4 | key item, important id 0 | `66 02 04 7d 00 01 64 7f` |
| 5 | Zidane knows `AA:6` | `66 02 05 7d 00 00 7d 06 00 7d 00 00 d3 10 00 03 7f` |
| 6 | a clamped computed row index | `66 02 06 dc 00 7d e8 03 12 dc 00 7d e8 03 12 7d 00 00 1b 11 7f` |

Verified by building the field and disassembling the shipped `.eb` — the byte oracle is
pinned in `ff9mapkit/tests/test_opcodes_settextvar_expr.py`. Budget: **1488 of 65535**
(`binutils.eb_budget_used`, 2.3%), so T1b can add rows linearly for a long time.

## Corrections this probe bakes in

**The expression ceiling is 26-bit signed, not Int32.** Every *computed* intermediate is
pushed by `EBin.expr_Push_v0_Int24` (`EBin.cs:1270-1274`), which ORs the Int26 class tag
(`7 << 26`) into `_v0` with **no mask**, and is read back as `(t0 << 6) >> 6`
(`EBin.cs:1682-1684`). Overflow does not truncate — the high bits collide with the
`VariableSource` field and the stack entry is re-read as a *different variable class*.
Only a bare terminal var token bypasses the push and returns a full Int32 through `getv()`.
Ceiling: ±33,554,431 (`opcodes.EXPR_VALUE_MIN/MAX`, the same number
`content/behavior.py` already carries as `TABLE_VALUE_MIN/MAX`). Every T1b/T3 counter that
multiplies or sums must be bounded against it.

**Both `Int24` and `UInt24` sign-extend.** `EBin.cs:1858-1861` falls `Int24` through into
`UInt24` and casts the top byte `(SByte)buffer[ofs+2] << 16`, so the cast applies to both.
There is **no unsigned 24-bit spelling** — 24/24 chocographs found reads `-1` either way,
and `Global.UInt24[187]` will not rescue it. Mask with `const4(16777215) B_AND` at every
site. Rows 2 and 3 exist to show that side by side.

**A `[behavior]` block carrying only a `hud` compiles to NOTHING, silently.**
`content/behaviortoml.py` `table()` is `return b if isinstance(b, dict) and
b.get("unit") else None`, and `validate()` still returns `[]`. Ship the probe without the
dummy `[[npc]]` + `[[behavior.unit]]` and the playtest reports "no window appeared" —
indistinguishable from "every read returned 0". The dummy unit is load-bearing; the trap is
now a checked precondition (`tests/test_behavior_hud_expr.py`).

**Width is the binding constraint, not height.** `Dialog.AutomaticSize` bakes Width once at
open from the widest rendered line; a value change only re-parses, never re-sizes. The
`digits` sentinel rides `SetTextVariable`'s u16 *immediate* operand, so it saturates at
65535 = five glyphs — it cannot reserve room for the raw chocograph row's `-8388608` (nine).
The header line is therefore the width pin. Do not add `[STRT=]` (flips
`CanAutoResize()` false) and do not add `[WDTH=]` (its `[TEXT=]` decode is the legacy packed
form and desyncs the param list; the divergence is inert only because its one call site is
`// Dummied`).

## What is deliberately NOT here

**The `[TEXT=bank,slot]` glyph.** Rendering one needs a minted text *entry* whose body is
split by `[TBLE=]`, and the kit's only `[TBLE=]` emitter is hardwired to the Mognet roster
(`build.py`, `build_mes_fixed`). That is rung 0b and wants a `[[text_table]]` lane — which
is T1b's whole prose layer, not probe-only scaffolding. Slot 6 therefore publishes the
*clamped number* instead, which still exercises the guard expression.

The guard itself ships regardless, and it is no longer something the author can get wrong:
`compile()` **wraps** every slot a `[TEXT=…]` tag reads in `E E const(0) B_GE B_MULT`
(`behavior.hud_row_index_clamp`), so an unclamped publish is *unrepresentable* rather than
merely refused. `ETb.GetStringFromTable` (`ETb.cs:270-284`) bounds the slot and the upper
row but has **no lower bound**, and a hud row re-parses every *rendered* frame, so a
negative is per-frame `IndexOutOfRangeException` spam, not a one-shot. `B_LMAX`/`B_LMIN`
are **not** clamps — they are party-member argmax/argmin selectors
(`EventEngine.OperatorExtract.cs:80-154`).

The earlier gate graded the author's spelling with a three-token *tail match*, which
certified the single-`E` form `E const(0) B_GE B_MULT` as safe — that form publishes an
unclamped number **and** underflows the CalcStack. Both halves are now structural: the
emitter writes the clamp, and `eb/exprsem.py` walks every hud expression's true arity
(`exprasm.assemble` is a byte encoder and checks none).

## Deploying (the human does this)

```
py tools/deploy_field.py studies/completion-journal/bench/journal_probe.field.toml --id 30800
```

- **First deploy of 30800 needs a RELAUNCH** (it registers a DictionaryPatch line). After
  that, `~` → Reload field.
- **Re-read the live registrations first.** EventDB/SceneData are GLOBAL across stacked mod
  folders and a collision is the null-`.eb` black screen; ~18 worktrees share this install,
  so check both `FF9CustomMap/DictionaryPatch.txt` and `FF9CustomMap-world/`'s before
  deploying. 30800 was free when this was written; that is a sample, not a registry.

## Reading it — what the offline suite cannot tell you

The offline tests prove the bytes are what the engine's *reader* specifies. They cannot
prove the reader does what the source says. Every semantic question needs the game, and
**every row needs both polarities in the same round** — a stuck 0 and a correct 0 are
identical on one sample:

1. **TH points** — cross-check against the `~` Flags panel / `flags.py`'s own
   recomputation from the same save. Stuck 0 with nonzero treasure bits ⇒ the
   `memoria_variable` arm is dead, and the cheapest journal column collapses.
2. **`flex(16,3)`** — read it with a character who *has* `AA:6` and one who does not.
3. **Chocographs** — needs a save with chocographs found. Expect row 2 = `-1` and row 3 =
   `16777215` at 24/24. A fresh save shows 0/0 and proves nothing.
4. **Key item** — toggle against Menu ▸ Key Items. Stay in important ids **0-79**: 80-254
   is the Folklore codex mint band (`content/folklore.py:93-94`) and a read there returns a
   codex entry, not a stock key item.
5. **The strip renders at full width**, all seven rows legible, one window, no clipping.

Ask for a short in-game **video**, not a verdict — seven numbers in one frame is exactly the
case where a still and a description diverge.
