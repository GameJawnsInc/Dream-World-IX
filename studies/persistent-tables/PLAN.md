# Persistent data tables — a `gScriptVector` table that survives field entry

**Origin:** board entry #1 of [`../eb-uses-board/BOARD.md`](../eb-uses-board/BOARD.md), picked in
[`../eb-uses-board/HANDOFF.md`](../eb-uses-board/HANDOFF.md). Every `[[behavior.table]]` the kit emits
is force-wiped (`size←0`, `size←n`) at every `Main_Init`, by a deliberate law that makes the save-global
vector id namespace harmless. That same law is why no kit content remembers anything the story flags
cannot: no counts, no orderings, no logs. A persistent class turns the vector store into the project's
first author-owned durable structure.

**Status:** Rung 0 ★ PASSED in-game (harness, 21/21 checks over three launches). **Rung 1 ★ PASSED
in-game — the kit feature `persist = true` (harness, 40/40 checks over four launches).**

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

## Rung 1 — the kit feature `persist = true` ★ PASSED in-game

**Design** (settled by a 3-designer / 3-judge panel, minimal surface — the full spec is in the commit
`feat(behavior): persistent data tables`; the user-facing contract is BEHAVIOR.md § Persistent tables):

- **Identity:** an author-chosen `id` in 6000000..6999999, REQUIRED (like a `[[flag]]` index). The guard
  vector sits at id + 1000000. Ordinary tables and both auto allocators are refused the whole
  6000000..7999999 band — enforced where ids are assigned (`behavior.table_id_problem`,
  `_refuse_reserved_auto`), not in a docstring.
- **Check word:** sha256(salt, name, length) over a 2^24 floor — never 0, inside the 26-bit stack.
  NOT the values (a seed edit reaches new games only), not the id, not the field or mod (sharing).
- **The guard** (`persist_seed_block`, Main_Init only): seed only when stale (word mismatch or size ≠ n),
  then THE TABLE SEED verbatim, check word LAST. Every stale case degrades to the seed.
- **The append fence:** the engine APPENDS at `index == Count` (the docs said "lost"); a counter-indexed
  adjust/drift on a persistent table is fenced at `index < n`, or one write rides the save as an n+1th
  cell and trips the table's own guard.
- **Values** fenced to ±1000000. **`lint-campaign` (e4)** refuses members that declare one persistent id
  with a different name or length.

**Deferred** (and why): a `schema` key (changing `id` is the equivalent lever); grow-in-place (with the
length unhashed it would reinterpret data); a re-seed counter in the guard; derived ids (they split under
`deploy --id`); a `table:` HUD source; save tooling beyond `save.read_extra_vectors`; a build-stamp record
of persistent identities (the real fix for "forgot to change the id"); fencing ordinary tables.

**In-game proof** — `rung1_persist.py`, four launches, benches `bench/pwrite.field.toml` (30862: `memo`
persist id 6004242 + ordinary twin `eph` id 4300 + levers), `pwrite_v2` (11 cells), `pread` (30863):

| Launch | What it showed | Checks |
|---|---|---|
| WRITE | negative control; first entry seeds + writes the guard word, one past the end reads 0; bump → 4011 (eph 5012); **THE FENCE**: counter parked at n, a `memo[k]` write appends nothing; re-entering the writer **keeps memo 4011 while the same Main_Init re-seeds eph 5012 → 5005**; the entry autosave holds memo + guard + eph + nonce | 14/14 |
| READ | fresh process, Continue lands **in the declaring field**: memo 4011 survives that field's Main_Init, eph reads 5005 though the save held 5012 (Main_Init ran); a post-load bump → 4018 survives a round trip | 10/10 |
| RESHAPE | v2 (11 cells) deployed over 30862, same save: the length change re-seeds under the v2 check word (4004, cell 10 = 11011) — by design; the v2 table takes writes; the autosave carries it | 8/8 |
| LOST | extra file set aside: the main block restores the nonce, memo degrades to its SEED (4004, not the 4011 the lost file held), the game plays on | 8/8 |

Artifacts: `.harness-runs/20260922-20*-rung1-*`. The benches stay deployed at 30860-30863 (scratch; revert
with `tools/scroll_out/revert_deploy_<id>.py`). Re-running from WRITE needs `pwrite.field.toml` (v1)
redeployed first — the header check fails loudly otherwise.

### The review round

A 31-agent adversarial review of the feature commit (five lenses, two skeptics per finding) confirmed five
defects, all fixed in `fix(behavior): the persistent-tables review round`: persistent-id agreement was linted
inside one campaign only, though a journey's campaigns share one save (now `journey.lint_manifest` (g3));
the campaign lint crashed on a malformed member table; the BEHAVIOR.md example could not build (now a test
builds it); two fences were unpinned by tests. The bytecode lens found nothing. The branch's pre-merge
full-suite run also caught an unrelated red on master (the `[[ladder]]` key allow-list refusing 14 keys
the build honours), fixed alongside.

## Next — what this unlocks

The board's ledger family now stands on a proven substrate: the continuity ledger, the fight-writes-the-
ledger return path (a battle `.eb` writing a persistent id — board cheap move #3 is its falsifier), the
seeded PRNG's state cell, split tables, offstage agents. Pick consumers from `../eb-uses-board/BOARD.md`
§B; each one should declare its tables `persist = true` rather than mint a new mechanism.

**First consumer shipped:** board entry #4, the fight writes the ledger — a battle's `[scene.ledger]` writes a
persistent table under a live gate; rungs 0-1 in-game proven → [`../fight-ledger/PLAN.md`](../fight-ledger/PLAN.md).

**Second consumer shipped:** board entry #5, the roll stream — a seeded generator whose `persist = true` state rides
this guard (its check word hashes a key that folds the generator in), so a reload cannot re-roll; rungs 0-1 in-game
proven → [`../roll-stream/PLAN.md`](../roll-stream/PLAN.md).
