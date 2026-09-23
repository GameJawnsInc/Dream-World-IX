# Handoff — the persistent vector class (board entry #1)

> **PICKED UP.** Rung 0 ★ PASSED in-game (harness, 3 launches, 21/21 checks): vectors survive save → quit → relaunch → load, riding only the Memoria extra file. The arc now lives in [`../persistent-tables/PLAN.md`](../persistent-tables/PLAN.md). The "confirm first" note below is stale: bench 30415 was in-game proven over 3 rounds (`studies/behavior-trees/PLAN.md`), and rung 0 exercised the table seed + `adjust` + HUD-read path directly.

> **NEXT CONSUMER PICKED:** entry #4, *The fight writes the ledger* — rungs 0-1 in-game proven, arc in
> [`../fight-ledger/PLAN.md`](../fight-ledger/PLAN.md) (`[scene.ledger]`).
>
> **SECOND CONSUMER PICKED:** entry #5, *The roll stream* — rungs 0-1 in-game proven, arc in
> [`../roll-stream/PLAN.md`](../roll-stream/PLAN.md) (`[[behavior.stream]]`, branch `roll`, `wander` `seed`).

**Picked:** entry #1 of [`BOARD.md`](BOARD.md), a `gScriptVector` table class that survives field entry.
**Paused because:** its first rung is a hard-quit/relaunch round trip. That needs the real machine: the game install,
the harness and `game_snap`. The session that picked it ran in a bare cloud container.

Line numbers below are from `master` at `8c7a5b4`. Re-check them before editing.

## What's in this directory

| File | What it is |
|---|---|
| [`BOARD.md`](BOARD.md) | The ranked write-up: top 10, the rest by theme, three cheap first moves, the kill list |
| [`DOSSIER.md`](DOSSIER.md) | Index of all 173 ideas (124 survived, 49 killed), linking to [`dossier/<lens>.md`](dossier/). Each has the full mechanism, screen verdict and both verifiers' reasoning |
| [`BRIEFS.md`](BRIEFS.md) | The four background briefs every idea agent worked from (opcodes, shipped/dead ends, constraints, engine services) |
| `HANDOFF.md` | This file |

**Where the reasoning behind #1 lives.** "The Persistent Table" is a name the final writer gave to several dossier
ideas combined, so no single entry has that title. Read these:

- [Vector Schema Version Guard](dossier/data-structures.md#3-vector-schema-version-guard): the check word and
  migration design. Its screen correction is where "limit this to vectors that must survive" comes from.
- [The Save-Boundary Census](dossier/gap-1.md#7-the-save-boundary-census): which script-readable state actually
  rides the save. Rung 0 is its first cell.
- [The Sparse Dictionary Ledger](dossier/data-structures.md#4-the-sparse-dictionary-ledger): the `B_DICTIONARY`
  alternative, and whether a miss returns 0 or throws.
- Consumers that depend on it: [The Continuity Ledger](dossier/narrative-state.md#1-the-continuity-ledger),
  [The Fight Writes The Ledger](dossier/gap-1.md#2-the-fight-writes-the-ledger),
  [The Lehmer Seed Box](dossier/data-structures.md#2-the-lehmer-seed-box),
  [Ring-Buffer Message Bus](dossier/gap-2.md#4-ring-buffer-message-bus),
  [The Ghost Racer](dossier/genre-transplant.md#1-the-ghost-racer).

## Checked on current master

- **Tables are wiped at every `Main_Init`, at three sites in `content/behavior.py`:** plain tables (`:2444`),
  counters (`:2451`), class strided state (`:3112`). Each sets `B_VECTOR_SIZE` to 0 and then to n. The comment at
  `:2440` gives the reason: clear stale leftover cells an older deploy left in the save.
- **The `TableSpec` docstring (`:999`) states the wipe as a rule** ("RE-SEEDED at every Main_Init"). A persistent
  class is a named exception to it and has to say so there.
- **Allocation:** `TABLE_ID_BASE = 1000` (`:715`), `TABLE_MAX_LEN = 64` (`:716`). There are two allocators,
  `_auto_tid` (`:1488`) and `_alloc_tid` (`:1777`). Both count up from the base separately for each field build.
  But the id namespace is **save-global**, so every kit field with a table gets tid 1000. That's the board's
  cross-mod collision, and it's real.
- **An explicit `id =` is accepted with no range check** (`:1508`). It can land inside the auto band.
- **`ClearMemoriaVector` (`0x11A`)** is in `eb/_optables.py:570` and `eb/_regen_optables.py:37` (one operand, the
  vector id), but nothing emits it. The planned migration path would be its first use.
- **Nothing in `content/` or `eb/` does durable table storage today.**

## The main design point

The wipe exists to guard against stale save data. So a persistent table needs its own guard in the wipe's place,
not just a way to skip it:

- a **reserved tid band** that both allocators and any explicit `id =` are refused from, enforced in the
  allocator itself (a rule that lives only in a docstring isn't enforced, per CLAUDE.md §7);
- a **magic+schema check word**, checked before the first read. On a mismatch, clear the vector (`0x11A`) and
  seed it again. Write the check word **last**, so a half-finished migration runs again. The board suggests putting
  the check word in its own guard vector rather than cell 0 of the payload, so the hot loop doesn't have to skip it;
- values fenced to ±2²⁵ (the 26-bit CalcStack);
- writes on the proven pair: `<tid> B_VECTOR_SIZE <n> B_LET` to grow, then `<tid> <idx> B_VECTOR <v> B_LET`.

## Rung 0 — before any code

1. Write ten cells at a tid from the reserved band.
2. Show them on screen (a `[[behavior.hud]]` row).
3. Quit to desktop, relaunch, load the save.
4. Read the cells back.

Four places in the repo say `gScriptVector` is saved with the game (the board cites `JsonParser.cs:521-545`).
Nobody here has observed it. **If the cells don't survive, about twenty ideas on the board shrink to
things that last one session, and the implementation isn't worth building.**

Also check **which save container it lands in**. The board says it rides only the Memoria extra save. If so, a
lost extra file has to fall back to today's behaviour, not break the story.

## Confirm first

The data-tables layer this builds on (bench 30415, "BTTABLE") is **deployed but still waiting on a playtest**,
per the `authoring-ff9-field-scripts` skill. Confirm that bench works first. Otherwise a failed rung 0 could be
blamed on the wrong layer.
