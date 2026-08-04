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

**The `[TEXT=bank,slot]` glyph — ★ NO LONGER MISSING, the lane shipped.** This section used to
read: rendering one needs a minted text *entry* whose body is split by `[TBLE=]`, and the kit's
only `[TBLE=]` emitter is hardwired to the Mognet roster, so **slot 6 of the rung-0 probe
publishes the clamped number instead**. That remains true of the *probe* (`journal_probe.field.toml`
is a recorded artifact and is not re-cut), and it is what left T1b shipping two frozen literal
rows — the Treasure-Hunter rank stuck on `H`, the Hunt winner on a fixed name — until the owner
reported them: *"T hunter rank and chests opened are wrong."*

The lane is now `ff9mapkit/ff9mapkit/content/texttable.py`:

```toml
[[text_table]]
name = "th_rank"
rows = ["H", "G", "F", "E", "D", "C", "B", "A", "S"]
```

Each block becomes one `.mes` entry, `[TBLE=<n>,]` + the rows newline-separated, added **last** so
a field without one is byte-identical to before. The bank operand of a `[TEXT=<name>,slot]` tag is
a **name**, and `build.collect_text` substitutes the txid it actually allocated (through
`content.text.txid_map`, the same function `build_mes` derives its own mapping from — one owner, so
the substituted id cannot be off by one from the id the entry lands on). A hand-authored bank number
was never possible and now is never needed; an *unknown* name raises at the substitution site rather
than shipping, because the in-game symptom is `String.Empty` — a blank line, no log, which a player
reads as a bug.

**Bank txids above 255 are fine.** `NGUIText.GetDialogWidthFromSpecialOpcode` (`NGUIText.cs:60-84`)
carries a second, packed `[TEXT=]` decode for `tableId > Byte.MaxValue` that the replacement path
does not implement — but that decoder is reachable only from `OnWidths`, i.e. the `[WDTH]` tag,
which Memoria marks `// Dummied`. The live render is a plain
`ETb.GetStringFromTable(UIntParam(0), UIntParam(1))` (`DialogBoxSymbols.cs:59-60`). The bench's
banks land at txid 509/510 and render through that one function. Do **not** add `[WDTH=]` to an
entry carrying a `[TEXT=]`.

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


---

# T1b -- the paged completion dashboard (field 30801)

`journal_dash.field.toml` is the **T1b dashboard bench -- live**. It is GENERATED
(`ff9mapkit.journalfield.bench_toml()`), a test asserts the checked-in file equals the generator's
output, and hand-editing it fails the suite. A second test BUILDS it and asserts the emitted `.eb`
carries the value writes (see "It shipped once as a mockup" below).

## What T1b built

| piece | where | what it is |
|---|---|---|
| `RowSpec.eb` / `eb_source` / `eb_absent` | `ff9mapkit/ff9mapkit/journal.py` | the in-game half of the ONE row catalog: 31 rows carry an `.eb` expression, 17 carry an explicit reason |
| `EB_EXPRESSIONS` / `EB_ABSENT` | same | the 48 decisions, contiguous, each with an engine `file:line` |
| `eb_bounds` / `eb_eval` / `eb_geg_reader` | same | an interval evaluator (the 26-bit gate) and an RPN interpreter (the offline cross-validator) |
| the exhaustiveness gate | `journal.lint_rows` | EXACTLY ONE of `eb` / `eb_absent`; no third state to default into |
| `EB_SCALE` / `RowSpec.eb_scale` / `eb_unit` | same | THE UNIT LAW -- the one row (`meta.play_time`) whose renderers publish different units DECLARES the conversion; `lint_rows` refuses an undeclared divide and the cross-validation asserts `offline // scale == eb_eval` |
| `PAGES`, `render_page`, `page_body`, `talk_body`, `lint_pages` | `ff9mapkit/ff9mapkit/journalfield.py` | the 7-page layout, its `.mes` text, its `.eb` bytes, and every ceiling enforced |
| `journal pages` / `journal eb` | `ff9mapkit/ff9mapkit/cli.py` | print the measured layout / disassemble the emitted stream |

`py -m ff9mapkit journal lint` now runs BOTH halves and exits 2 on any violation. `--offline` drops
the ONE check that reads the game install (the `/80` key-item bake); WITHOUT it, a machine that
cannot read the install FAILS rather than passing on a bake nobody verified.

⚠ **Two things this table used to imply and no longer does.** A `Line` carries neither a denominator
nor a unit -- both come from the RowSpec, so a page cannot render a fraction or a unit the catalog
disagrees with, and there is no rule "checking" it because there is no second place to write it. And
the header/widest-value relation is a CONSTRUCTION of `render_page`, not a gate: it holds for every
possible page, so nothing lints it (measured -- 120 label widths never fired the old rule). The width
rule that CAN fail is the 28.0-unit wrap on the grown header.

## The layout: 7 pages, 48 rows, nothing dropped

| page | lines | slots | `.eb` bytes | header / widest value line (units) |
|---|---|---|---|---|
| STORY & TREASURE | 5 | 3/8 | 137 | 20.20 / 19.95 |
| CHOCOBO | 6 | 5/8 | 303 | 21.05 / 20.70 |
| MINIGAMES | 6 | 5/8 | 119 | 22.95 / 22.45 |
| TETRA MASTER | 7 | 5/8 | 1430 | 22.60 / 22.10 |
| MOGNET | 9 | 7/8 | 579 | 20.35 / 19.35 |
| PARTY | 11 | 2/8 | 415 | 21.75 / 21.70 |
| COMBAT & META | 11 | 4/8 | 43 | 22.65 / 21.85 |
| **whole talk handler** | | | **3114 of 65535 (4.8%)** | |

Every one of the 48 catalog rows appears on exactly one page -- as a number, as `--` (a save carries
it but no expression can reach it) or as `n/a` (the game keeps nothing, or keeps a counter it never
moves). The placement audit is a lint rule, not a claim.

`minigame` is the only category that had to split, and it splits along the engine's own seam:
gEventGlobal minigames (MINIGAMES) versus the `30000_MiniGame` deck (TETRA MASTER). `combat` is a
single row, so it rides with `meta` rather than costing a menu slot for one line.

## Four source-over-design corrections, all load-bearing

**1. `party.key_items` IS readable in-game, and needs no sibling row.** The design refused it, on the
premise that `B_HAVE_ITEM` reads HELD while the offline row counts OBTAINED, and proposed a new
`party.key_items_held`. The engine says otherwise: `FF9Item_GetCount_Generic` routes an important id
to `FF9Item_IsExistImportant` (`ff9item.2.cs:229`), which is literally
`rare_item_obtained.Contains(id)` (`:343-345`). `rare_item_used` is a SEPARATE set --
`FF9Item_UseImportant` only ADDS to it (`:333-336`) and never removes from `obtained`; only
`FF9Item_RemoveImportant` clears both (`:327-331`). The offline reader counts the same set
(`obtained` per entry, `JsonParser.cs:1004`). **Same quantity, one row, two renderers** -- which is
the whole bet. Adding the sibling would have shipped two rows for one number.

**2. The `.eb` byte costs in the design table are low by ~25%.** A `Global.Bit[i]` above index 255
takes the long-index encoding (`0xE4 <u16>`, 4 bytes, not 3), and the interleaved `B_PLUS` per term
costs 1 more. Measured: 24 bits = 96 bytes for the leaves **plus** 23 `B_PLUS` plus the terminator.
Every number in the table above is `len()` of the real assembled stream.

**3. `B_HAVE_ITEM`'s value range is BAND-dependent and it matters for width.** An important id (256-511)
returns 0/1; a regular id returns a Byte count; a card id counts deck entries. A blanket
over-approximation is not free -- the header width pin is computed against these bounds, so a 4x-wide
bound widens every window for nothing.

**4. `eb_bounds` is correlation-blind, so the hunt-winner clamp needed EVALUATION, not intervals.**
Interval arithmetic reports `minigame.hunt_winner` as 0..255 because it cannot see that the
multiplicand and the predicate are the same byte. `eb_eval` runs the expression over all 256 byte
values and shows the clamp folds every out-of-range byte to table row 0 -- which matters because
`GetStringFromTable` guards the UPPER row by returning `String.Empty` (`ETb.cs:278`), i.e. a blank
line that reads as a bug.

## What the bench IS

The seven real pages, verbatim, at their real widths and line counts, in a real modal field window,
**with live numbers**. It answers the three questions the offline suite cannot:

1. does a ~26-unit line render **unwrapped**;
2. does an **11-line** window sit inside `kLimitTop`/`kLimitBottom` at the owner's aspect ratio;
3. does the `--` vs `n/a` distinction read as **informative** or as broken.

Each menu row is a `[[choice]]` option; the page text is its `reply`; and the option's **`values`**
list publishes that page's catalog expressions into `gMesValue` 0..N-1 immediately before the reply
window opens (`content/choice.py:option_values_body` -> `eb/opcodes.py:set_text_variable_expr`).

### It shipped once as a mockup, and that is worth remembering

The first cut had **no value writes at all** -- `grep -c "expr:"` on the TOML returned 0. Neither
existing lane could attach a raw talk-handler body (`[[logic_add]]` is refused unless the project
carries `[verbatim_eb]`, `build.py:930-934`; `[behavior]` is refused ON a verbatim fork), so the
generator was right and the wiring was simply absent.

**It did not render zeros.** `ETb.gMesValue` is `Int32[8]` allocated once at engine init
(`EventEngine.Initialize.cs:30`) and is never cleared on a field load, so all seven pages rendered
the *previous* bench's leftover slot vector -- `[7200, 22, 0, 6, 0, 0, 0]`, the rung-0b probe's
readings from bench 30800. Plausible numbers, in the right columns, entirely stale ("Mognet: In hand
22/3"). An unwritten slot is not blank; it is whatever the last field to write it left there.

The lesson that generalizes past this bench: **an offline test of a generator cannot see an unwired
field.** `tests/test_journalfield.py` now BUILDS this TOML and asserts the emitted `.eb` carries the
expected `SetTextVariable` ops -- right count, right slots, right expressions, per page.

The two `[TEXT=bank,slot]` rows show their widest table string instead of the tag: the bank is a txid
the build assigns by POSITION (`build.py:7795-7834`) and is not authorable in a TOML at all. Their
slot is still *published*, so every later slot index matches the shipped page exactly; nothing in the
bench reads it, so nothing clamps it (the non-negative `[TEXT=]` clamp is emitted for the slots an
option's own reply actually indexes).

## Reviewing the emitted `.eb` without building anything

```
py -m ff9mapkit journal pages            # the layout, every width measured
py -m ff9mapkit journal eb --page meta   # one page's arm, disassembled
py -m ff9mapkit journal eb               # the whole talk handler
```

The COMBAT & META arm in full -- 43 bytes, 4 slot writes and one `WindowSync`:

```
[0]  SetTextVariable(0, {Global.Bit[1584] B_EXPR_END})
[7]  SetTextVariable(1, {B_SYSVAR[20] const(3600) B_DIV B_EXPR_END})
[17] SetTextVariable(2, {B_SYSVAR[20] const(60) B_DIV const(60) B_REM B_EXPR_END})
[31] SetTextVariable(3, {Global.UInt16[2] B_EXPR_END})
[37] WindowSync(1, 128, 706)
```

Two things to read in the whole-handler listing:

* the loop's back-hop prints as `op_01(62434)`. **That is not a bug.** The disassembler renders the
  operand unsigned; the engine reads a SIGNED int16 via `getShortIP`, so 62434 is -3102 and the jump
  lands exactly on the loop condition. The two jump ops differ in signedness and it is load-bearing:
  `0x02` (JMP_IFNOT) reads UNSIGNED and can only go forward, which is why the return hop must be the
  unconditional `0x01`.
* there is exactly ONE `op_0B`. Every arm opens a window and a window overwrites sysvar 9, so the
  per-arm `if (GetChoose()==i)` form would test the PAGE window's answer and misfire from the second
  row on. `build.py:6097` selects switch dispatch only when a row carries `input`/`qte`, so the
  generator asks for it explicitly.

## Deploying (the human does this)

```
py tools/deploy_field.py studies/completion-journal/bench/journal_dash.field.toml --id 30801
```

* **First deploy of 30801 needs a RELAUNCH** (it registers a DictionaryPatch line). After that,
  `~` -> Reload field.
* **Re-read the live registrations first.** EventDB/SceneData are GLOBAL across stacked mod folders
  and a collision is the null-`.eb` black screen; ~18 worktrees share this install. 30801 was free
  when this was written; that is a sample, not a registry. **30800 is the rung-0/0b probe -- leave it.**

## What only a playtest can settle

Ask for a short in-game **video**, page by page. Specifically:

1. **PARTY and COMBAT & META** are the tall pages (11 lines). Do they fit, or does the bottom clip?
2. **MINIGAMES** has the widest header (22.95 units). Does it render on one line?
3. **PARTY** has eight `--`/`n/a` rows in a row. Does that read as "the game does not keep this", or
   as "the journal is broken"? If it reads as broken, the fix is prose, not code -- and it is cheaper
   to learn now than after the wiring rung.
4. If everything fits comfortably, `[dialogue] wrap` can be raised above 28.0 and the labels can grow.
   That is a lever the layout does not depend on.
