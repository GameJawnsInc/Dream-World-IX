# The `.eb` file budget — a byte meter, then relief (study)

**Goal:** make the engine-fixed **~64KB whole-file reach** of the `.eb` entry table a *visible,
actionable* quantity at authoring time instead of a wall you discover at build — and then, in
stages, buy real headroom past it without silently costing stock-Memoria compatibility.

**Origin:** owner framing (2026-07-28): *"a byte meter in the CLI/GUI that warns when you're
approaching the stock limit; the compiler could automatically swap between a stock Memoria `.eb`
and our advanced handler."* Spun out of the wall found in
[`studies/behavior-trees/PLAN.md`](../behavior-trees/PLAN.md) (THE SECOND WALL) and measured on
the fort-condor donor. Related: [[project-ff9-behavior-trees]], [[project-ff9-eb-script-tooling]].

---

## 1. The problem, with receipts

The `.eb` entry table is **u16-addressed** → an entry's offset cannot exceed `0xFFFF` from
`ENTRY_TABLE_OFF`. **ENGINE-FIXED — no compiler pass removes it.** Everything a field owns shares
that one budget: the behavior ticker, every dispatch and duty function, dialogue, gateways,
cutscenes, chests.

| Measurement | Value | Source |
|---|---|---|
| Fort-condor donor, total behavior bodies | **≈50-55KB** | ticker + dispatch + duties, `studies/behavior-trees/PLAN.md` |
| Bench ISLES 30416 ticker alone (14-unit brawl) | **33,820 B** | ★ in-game proven 2026-07-25 |
| 20-ally × 6-raider full counter cross-product | **exceeds the FILE** | pair-branch scope is now a budget *design decision*, not a jump accident |
| Field 559 naive per-pair region test | **48KB** — will not assemble | interval compression → 8,140 B (0.17×) |

Two independent systems have already hit this. It is not hypothetical.

**The failure mode it produces is the bad kind.** Before the recent hardening, `set_u16` MASKED
(`& 0xFFFF`) — the first over-budget build wrapped an entry offset into garbage function tags
**with no error at the write site**; lint caught it post-hoc. That is the black-screen-at-playtest
class this project keeps paying for.

### ⚠ The same defect is still live on a sibling function

`binutils.py:39-41` — **`pu16` still masks (`& 0xFFFF`), unchecked**, on the pack path. This is
`set_u16`'s pre-hardening bug, unfixed, one function over. **S1 fixes it or the meter is built on
sand.**

---

## 2. THE LOAD-BEARING DECISION: escalation is DECLARED, never inferred

The owner's "compiler automatically swaps" is the right *capability* and the wrong *default*.

Engine-independence is currently a real, user-facing property: **a novel field runs on stock
Memoria; only a fork needs the DWIX bundle** (CLAUDE.md §5). A compiler that silently escalates a
big field to a custom-opcode path silently revokes that property — and on a stock install an
unknown opcode falls through `EventEngine.DoEventCode()`'s `default: return 1`, i.e. **a silent
no-op, not a crash.** Wrong behavior with no log is strictly worse than a refusal.

**THE ESCALATION LAW — an `.eb` never leaves stock-compatible without the author being told in
the same breath.**

```toml
[field]
engine = "stock"   # default. Budget is a HARD ceiling; over-budget is a build ERROR.
                   # "dwix" — extended path available; build stamps an engine requirement.
                   # "auto" — may escalate, but LOUDLY (logged + a lint finding naming the
                   #          exact byte count that forced it). Never quiet.
```

Corollaries:
- A `dwix`-requiring field **stamps a requirement** into the built mod; deploy reads it and
  refuses/warns against a stock install.
- The extended path's **first act at runtime is a capability probe**, so a mis-shipped mod says so
  instead of no-op'ing.

---

## 3. Stage 1 — THE METER (no engine work, no semantics change)

Ships value alone, and is the prerequisite for judging whether S2/S3 are even needed.

### 3.1 One definition of "used", consumed by every site

Today the limit is **inlined `0xFFFF` at 2 places** and there is **no named constant** anywhere:

| Site | What it checks |
|---|---|
| `ff9mapkit/binutils.py:55-65` | `set_u16` — STRICT, raises with the 64KB message |
| `ff9mapkit/eb/edit.py:96-134` | `append_entry` — `:119` `new_off > 0xFFFF` (`new_off = len(b) - ENTRY_TABLE_OFF`, `:116`) and `:124` entry size |

⚠ **The budget is an OFFSET budget, not a file-length budget** (`len(b) - ENTRY_TABLE_OFF`). A
meter that reports raw `len(eb)` will disagree with the enforcement and lose the author's trust the
first time they differ. **A law in a docstring is a wish** — mint it once and make both existing
sites consume it:

- `EB_FILE_BUDGET = 0xFFFF` + `eb_budget_used(b) -> int` in `binutils.py`.
- `binutils.py:55-65` and `eb/edit.py:119` both call it. No third definition is permitted.
- Fix `pu16` (§1) to the same strict contract.

⚠ **Measure the FINAL assembled bytes.** `labelasm`'s island insertion (`JMP skip; island: JMP
target; skip:`, 6B each, fixpoint-iterated) **adds bytes**. A pre-relaxation measurement
under-reports. The meter reads what gets written.

### 3.2 The number that is actually actionable

Percent-full is a weak headline. The behavior compiler already knows **per-unit cost**
(`content/behavior.py:910-960`, `CompiledBehavior.sizes` / `size_report()` — the source of the
50-55KB figure). So report three things:

```
  .eb budget   48,231 / 65,535 B   [██████████████░░░░░]  73%
    ticker 33,820 · duties 8,104 · dispatch 4,192 · dialogue 1,610 · other 505
    headroom ≈ 17,304 B — about 9 more units at current cost (~1,830 B/unit)
```

"About 9 more units" is a number an author can plan against. `73%` is not.

### 3.3 The four call sites — THE CALL-SITE LAW

[[project-ff9-gui-makeover]]'s standing failure here is *a correct mechanism no call site ever
spends*. Named explicitly, all four:

| # | Call site | Change |
|---|---|---|
| 1 | **build** | `len(eb)` is computed **nowhere** today (`build.py:7799` writes the bytes; `FieldResult` `:7264-7279` has no size field). Add `eb_size` + the per-contributor breakdown to `FieldResult`. |
| 2 | **lint** | `LintReport` (`build.py:3119-3136`) already has `errors` + advisory buckets (`logic/flags/placement/camera`) and `EbIssue.severity` is already `"error"｜"warning"` — **a graduated warning needs NO new severity.** Add a `budget` bucket; over-wall goes to `errors`. Flows to CLI + GUI unchanged. |
| 3 | **deploy** | `tools/deploy_field.py` has **no validation step at all** — but `:93` already reads the built bytes back into hand (`eb0 = tl.eb_path(...).read_bytes()`). That is a **one-line hook**. Print the meter beside the existing `built {FBG} | … | scroll={scroll}` line at `:96`; refuse on an engine-requirement mismatch. |
| 4 | **GUI** | `workspace/builddoc.py` (`BuildDoc`, `_verdict` `:898`, in-process lint `:904-906`) is the natural home for the per-field readout. `workspace/behaviordoc.py:2065-2068` already renders `size_text` — extend that existing byte-histogram surface with the whole-file meter rather than minting a rival one. Problems flow through `shell.py:_show_problems` `:8906`. |

CLI note: there is **no shared formatter/table/color helper** — each verb prints ad hoc, convention
`  ERROR  {p}` / `  warn  [{tag}] {w}` (`cli.py:796-800`). The meter is the first thing that wants a
bar; keep it a small local renderer, do not start a console-formatting framework.

Verification: **`tools/gui_snap.py` — render the real surface and READ the PNG.** Never assert from
source (`working-on-the-ff9-workspace`).

### 3.4 ★ Do this first: the census

Before any of S2/S3 is justified, run the new measurement across **every bundled example, every
bench field, and a sample of forks** and publish the distribution. If the worst real field sits at
30%, S3 is speculative and S2 is enough. If the benches sit at 85%, S3 is urgent. **This is a
half-day answer to a question the whole rest of the plan is gated on.**

---

## 4. Stage 2 — compiler-side relief (still zero engine work)

The meter is useless if it only ever says "you're full." S2 gives it a lever to recommend.

- **Table-ize the cross-products.** The already-proven route: stock Memoria gives `.eb` **computed
  array indexing (`0xD3`)** — the kept dividend from the falsified dynamic-region-test path
  ([[project-ff9-eb-script-tooling]]). One generic dispatcher + a constant table turns an O(N×M)
  *code* problem into O(1) code + O(N×M) *data*, and data carries no opcode/entry overhead. The
  20×6 counter cross-product is the exact shape this fixes.
- **Structural compression.** Field 559's 48KB → 8,140 B (0.17×) came from DFS region numbering
  making each row piecewise-constant. Generalize: find the structure in the combinatorics before
  unrolling it into near-duplicate branches.
- **Push pure data out to CSV.** The overworld vehicle system already proves the pattern
  (`TransportControls.csv` = physics as pure data, [[project-ff9-overworld-vehicles]]). Matchup /
  stat / tuning tables belong there, off the `.eb` budget entirely. Only works where the shape is a
  lookup the engine already reads generically — not arbitrary branching.

S2's wins are only legible **because** S1 measured them. Order matters.

---

## 5. Stage 3 — the engine path (a real patch, DWIX-only)

Only if the §3.4 census says so. Next free patch number is **s69** (the stack currently runs to
s68; ⚠ note two distinct patches are both numbered s48 — disambiguate by filename).

### The scoping result that shapes this

A companion-DLL, zero-rebuild hook **does not exist** for `.eb` execution.
`EventEngine.DoEventCode()` is a ~3,509-line hand-written `switch` over ~262 opcodes ending in a
plain `default: return 1` — no reflection, no `ScriptsLoader`, no unused slot, no callback list.
(`Memoria/Field/SFieldCalculator.cs:24-46`'s `[FieldAbilityScript]` **is** a real zero-rebuild
reflection hook, but it fires only on a **field-usable ability/item cast from the menu** — it is
the field-side twin of `[BattleScript]`, not an `.eb` extension point. Useless for always-running
actor AI.) Anything general is a genuine base-engine patch.

### ★ Recommendation: a BANKED entry table, not a C# call-out

Two candidate shapes. I recommend the first, and the reasoning is not cost — it is *semantics
ownership*.

| | **A. Banked / far-call** (recommended) | **B. C# call-out** (`[FieldEventScript]`) |
|---|---|---|
| Shape | One new opcode + two-level `(bank, offset)` addressing; logic spans multiple `.eb`-like files | New opcode routes to a reflection-discovered C# class, mirroring `ScriptsLoader` |
| Where logic lives | **All still `.eb`**, all still through the existing compiler + emitters | C# — **a second backend** |
| Compiler laws | Unchanged; existing emitters apply | **Re-opened.** Every fort-condor playtest failure was a hand-authoring error the compiler prevents; a C# backend restores each of those as a hand-authoring surface in another language, free to drift |
| Precedent | The **same shape** as the already-shipped island/JMP-relocation fix for the body wall — one level up | None on the field side |
| Cost | One opcode + a loader | An opcode + a discovery subsystem + a whole second semantics implementation |

**B is not worthless** — it stays the right answer for genuinely *computational* work that is
miserable as bytecode (a pathfinding solve, a scoring pass). But that is a narrow, later, optional
lane, not the answer to "the field ran out of room."

Runtime obligations either way: a capability probe on first use (§2), and the requirement stamp
honored by deploy.

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| **The meter lies** (measures a different quantity than the enforcement) | §3.1 — one constant, one function, both existing sites consume it |
| **Under-reporting pre-relaxation** (islands add bytes after the fact) | Measure the final assembled bytes only |
| **Silent loss of stock compatibility** | §2 THE ESCALATION LAW — declared target, loud `auto`, requirement stamp, runtime probe |
| **A meter nothing spends** | §3.3 names all four call sites; verify GUI with `tools/gui_snap.py` PNGs, never from source |
| **A green test run that proves nothing** | Byte-level slices don't COLLECT in a fresh worktree — run the suite in the MAIN repo or extract templates first ([[project-ff9-test-suite-perf]]) |
| **Building S3 for a problem nobody has** | §3.4 census gates it |

---

## 7. Do-next

1. **`EB_FILE_BUDGET` + `eb_budget_used()`; fix `pu16`; both existing sites consume it.** (§3.1)
2. **`eb_size` + breakdown on `FieldResult`; `budget` bucket in `LintReport`; the `ff9mapkit lint` line.** (§3.2-3.3)
3. **★ The census** — every example + bench + a fork sample. Publish the distribution here. (§3.4)
4. Deploy-path meter at `deploy_field.py:93`, GUI readout in `BuildDoc`. (§3.3)
5. Re-read §3.4's numbers, then decide S2 scope and whether S3 is real.

Steps 1-2 are small and immediately tell us where every field in the repo stands. **Nothing past
step 3 should be scoped before step 3's numbers exist.**
