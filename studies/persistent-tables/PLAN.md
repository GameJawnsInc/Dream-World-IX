# Persistent data tables — a `gScriptVector` table that survives field entry

**Origin:** board entry #1 of [`../eb-uses-board/BOARD.md`](../eb-uses-board/BOARD.md), picked in
[`../eb-uses-board/HANDOFF.md`](../eb-uses-board/HANDOFF.md). Every `[[behavior.table]]` the kit emits
is force-wiped (`size←0`, `size←n`) at every `Main_Init`, by a deliberate law that makes the save-global
vector id namespace harmless. That same law is why no kit content remembers anything the story flags
cannot: no counts, no orderings, no logs. A persistent class turns the vector store into the project's
first author-owned durable structure.

**Status:** Rung 0 ★ PASSED in-game (harness, 21/21 checks over three launches). Rung 1 = the kit
feature — designing.

---

## Rung 0 — does a vector cell survive save → quit to desktop → relaunch → load? ★ YES

Run entirely by the in-game harness (no human playtest needed for a mechanism question):
`rung0_persist.py`, three separate launches chained by a nonce, against two scratch benches in
[`bench/`](bench/):

| Bench | Id | Role |
|---|---|---|
| `vecwrite.field.toml` | 30860 | declares tid 4242 (10 cells) + tid 8400000 (a const4 id); public flag `bump` (14867) adds 7 to cell 3 |
| `vecread.field.toml` | 30861 | declares **no** table, so its `Main_Init` cannot re-seed what it reads; a 7-slot HUD strip |

| Launch | What it showed | Checks |
|---|---|---|
| WRITE | New Game → reader reads every vector **absent** (negative control) → writer seeds → one bump makes cell 3 = **4011**, a value only play creates → nonce poked → reader sees it all in-session → the sandbox autosave's **Memoria extra file** decodes to exactly `{4242: [...4011...], 8400000: [424242, 17]}` | 9/9 |
| READ | fresh process → title **Continue** → nonce matches (this launch loaded that save) → reader HUD: size 10, cell 3 = 4011, sum 55062, high cell 424242, control id 0 → entering the writer: its entry autosave (taken **before** `Main_Init`) still holds 4011, then its `Main_Init` **re-seeds** cell 3 to 4004 | 7/7 |
| LOST | extra file set aside → Continue loads the main block alone: nonce back (gEventGlobal rides the main block), **every vector empty**, game plays on | 5/5 |

Artifacts: `.harness-runs/20260922-1858*-rung0-*` (report.json, shots, steps).

### What rung 0 established (each measured, not read)

1. **Vectors persist across a real relaunch.** The whole premise of board entry #1 — and of ~20 board
   ideas downstream of it — holds.
2. **They ride ONLY the Memoria extra file** (`SavedData_ww_Memoria_Autosave.dat` /
   `_Memoria_{slot}_{save}.dat`). Lose that file and the save still loads, with every vector empty.
   So a persistent table is **enrichment, never a gate**: it must degrade to its seed, not break.
3. **The kit's re-seed law is what erases them today** — observed directly: loading into a field that
   declares the table wipes the loaded value before any script can read it.
4. **The field-entry autosave runs before the entered field's `Main_Init`** (observed: the writer's
   entry autosave still held 4011; its `Main_Init` then re-seeded). So what a field writes reaches disk
   on the *next* field entry, and a reseed on entry never erases the save you are entering with.
5. A tid above the 16-bit `const()` range (8400000, `const4`) round-trips end to end.

### Engine facts behind it (source, `C:\gd\FFIX\Memoria`)

- Save: `JsonParser.cs:236` writes `gScriptVector` only into `MemoriaExtraData` (`oldSaveFormat=false`);
  the main block's writer (`:40`, `oldSaveFormat=true`) never serializes vectors (`:580`).
- Load: parsing the main block **clears** vectors (`:524`); the extra file refills them (`:338`) only if
  its play time is within 1 s of the main block's (`:326`). A vector with 0 cells is dropped (`:546`).
- New Game clears them (`EventEngine.Initialize.cs:45`); the `~` Flags "reset all" clears them too.
- Reads never throw: a missing id or out-of-range index is 0; size of a missing id is 0
  (`EBin.cs:1646-1658`). A write at `index == Count` appends; at 0 on a missing id creates; anywhere
  else on a missing/short vector is **silently dropped** (`:1924-1937`) — hence grow-then-write.
- Storage is Int32, but every CalcStack value is 26-bit signed — keep cells within ±2²⁵.
- `ClearMemoriaVector` (0x11A) = `vect.Clear()`, identical in effect to `size←0`; nothing proven uses it.

### Instruments this rung added

- `ff9mapkit.save.read_extra_tree` / `read_extra_vectors` — decode the extra file (SimpleJSON
  **binary**, not text; `File.OpenWrite` never truncates, so a stale tail is ignored).
  `tests/test_save_extra.py` writes its fixtures with a port of the engine's own serializers.
- `tools/play.py` no longer dies on a check label outside cp1252 (it crashed the first READ launch
  mid-scenario, after the game had already been driven).

---

## Rung 1 — the kit feature (design draft, to be settled before code)

`persist = true` on a `[[behavior.table]]`:

- **Not re-seeded at `Main_Init`.** Instead a **guard** decides: if the table's check word does not
  match (or its size is not `n`), seed it (`size←0`, `size←n`, non-zero cells) and write the check word
  **last** — a torn seed re-seeds next time. New Game, a lost extra file and the debug "reset all" all
  land here and simply re-seed: the degrade path is the seed path.
- **The check word lives in its own guard vector**, not in cell 0 or past the end of the payload:
  cell 0 would shift every computed index the kit emits, and a cell past the end breaks the
  read-off-the-end-is-0 terminator the wave clock relies on. It must live in the **same container** as
  the data (a vector, never `gEventGlobal`, which also rides the main block and would claim "seeded"
  after the extra file was lost).
- **A reserved tid band** that the auto allocators can never reach and ordinary explicit `id =` is
  refused from — enforced where ids are assigned, not in a docstring.
- **Save-global identity.** A persistent tid is shared by every field that names it (the point, for a
  cross-field ledger) and by every mod on the machine (the risk, same as story flags). The check word
  hashes the table's name and shape, so a different table reusing the id is detected and re-seeded
  rather than silently reinterpreted.

Open questions for the design round: explicit-only ids vs derived ids; what the check word hashes
(values? length? an explicit `schema` bump?); whether a length change should re-seed or grow in
place; lint scope (one field vs campaign); the in-game rung-1 scenario (load back into the WRITER and
see the value survive; a redeploy with a new schema re-seeds).
