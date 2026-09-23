# The roll stream — a seeded, predictable PRNG in pure `.eb` RPN

**Origin:** board entry #5 of [`../eb-uses-board/BOARD.md`](../eb-uses-board/BOARD.md) (dossier:
[`data-structures.md` § 2, the Lehmer Seed Box](../eb-uses-board/dossier/data-structures.md#2-the-lehmer-seed-box)),
the third consumer of persistent tables ([`../persistent-tables/PLAN.md`](../persistent-tables/PLAN.md)). Every
random draw the kit emits is `B_SYSVAR[0]` (`Comn.random8` = `UnityEngine.Random.Range(0,256)`): impure, shared
with the whole engine, never seeded, never saved. A Lehmer recurrence over one table cell gives a stream that is
deterministic, save-persisted when asked (a reload cannot reroll it), and — because it is pure 26-bit-bounded
arithmetic — **predictable offline**: the one narrow case where a kit gate can genuinely be an oracle.

**Generator:** `x' = 236 · x mod 65537` (the one owner: `ff9mapkit/content/rollstream.py`, which proves it at
import). Full period (236 is a primitive root of the prime 65537: every state 1..65536 once, 0 never reached); largest
intermediate 236 · 65536 = 15,466,496 < 2^25 (2.17× headroom, and below the 15,532,032 rung 0 read back in-game). A
textbook MINSTD (16807 mod 2^31−1) is unrepresentable on the 26-bit CalcStack — its products need 46 bits.

*Why not 237* (the rung-0 choice): `39 + 7·237² ≡ 0 mod 65537`, so `39·x_i + 7·x_{i+2} ≡ 0` — every SECOND draw lies
on a lattice spaced 39.6 apart (2-D spectral ν2 at lag 2). Two consumers alternating on one stream, or a d100 read on
alternate draws, would feel it. 236 has the best worst case over lags 1..16 among the cheap full-period multipliers
(ν2 ≥ 131); the board's 13 mod 32749 falls on 13 lines and the dossier's 75 mod 65537 is mediocre. The generator tag
`lehmer236.65537` is folded into every stream's backing key, so a future generator change re-seeds every saved
stream through its guard instead of misreading it.

**Status:** ★★ Rung 0 PASSED in-game (instrument calibration, 6/6) · Rung 1 PASSED in-game — the kit feature (`[[behavior.stream]]`, branch `roll`, seeded `wander`, the `stream:` HUD source) produced the offline oracle's exact sequences across draw, ~Reload, save → quit → Continue, and a new process (21/21 + 15/15).

---

## Rung 0 — calibrate the instruments ★ PASSED

No kit code. `rung0_roll.py`, one launch, bench [`bench/roll0.field.toml`](bench/roll0.field.toml) (30890): HUD rows
that evaluate the generator's arithmetic as pure expressions, and one STOCK wander unit whose rolled targets live in
`Global.Int16` blackboard slots the harness watches bit for bit.

| Check | Result |
|---|---|
| `237·65536 mod 65537`, `237·12345 mod 65537`, `65536·237`, `65535 / 256` | **65300, 42137, 15532032, 255** — exactly the offline values (`B_MULT`/`B_REM`/`B_DIV`, `const4` operands) |
| `(2^25 − 1) + 1` | **−33554432**: CalcStack overflow WRAPS mod 2^26 and stays an Int26 — it does not change the variable class, as three kit comments (`behavior.py` `ADJUST_MAG_MAX`, `journal.py`, `eb/opcodes.py`) and the dossier claim |
| the watched mirror slots `mx`/`mz` vs `obj(uid).f[0]/f[2]` through the HUD | identical (315, −1193): the dry-compile blackboard slot map holds in the real build |
| stock wander targets `wtx`/`wtz` | 11 re-rolls in 16 s, every one inside the ±400 box |
| **control:** a `~ Reload` of the stock wander | a DIFFERENT target sequence — the instrument can tell a seeded stream from an unseeded one |

Artifacts: `.harness-runs/20260923-004842-rs-rung0`.

(Rung 0 calibrated with 237 — the arithmetic, wrap and slot-map facts it proved are generator-independent.)

---

## Rung 1 — the kit feature, in-game ★ PASSED

**The surface** (docs: [BEHAVIOR.md § Roll streams](../../ff9mapkit/docs/BEHAVIOR.md#roll-streams--seeded-randomness-you-can-predict)):

```toml
[[behavior.stream]]                  # a named stream: one gScriptVector cell holding the Lehmer state
name = "fate"
seed = 7                             # 1..2^31-1; hashed with the name to the start state x0 (never time-seeded)
persist = true                       # optional: survives the save (guarded like a persistent table)
id = 6004321                         # REQUIRED with persist, 6000000..6999999

  [[behavior.unit.branch]]           # a DRAW rides THE EDGE IDIOM (a selected branch executes every tick)
  when = [{ flag = "ask" }]          # a public flag raised from outside (a [[choice]] row, an [[event]], ...)
  roll = { stream = "fate", counter = "omen", range = [1, 6] }     # omen <- 1 + S % 6, after one advance
  clear_flags = ["ask"]              # consumed by this branch, cleared by no other
  do = { hold_post = true }

do = { wander = [0, -1100], radius = 300, seed = 1 }   # a SEEDED wander: its targets come from a private stream
values = ["stream:fate"]             # a HUD row showing the raw state
```

The build prints every stream's x0 and first predicted states (and each seeded wander's first targets) — the author's
oracle. Laws, all refusals at build: a roll only on the edge idiom (its flag public, required by the branch's `when`,
cleared by it and no other branch, never raised by `raise_flags` or an alternator); a roll in `when` is refused
permanently (a condition is evaluated per tick); no roll into a scan headcount or the wave-schedule counter; a
declared stream no roll draws; streams on class rows or `brains = true` (v1 ticker only); a seeded wander beside a
second wander on one unit; a `[behavior]` with no unit (it compiles to nothing — streams never seeded); a walk tread
with `once = false` that raises a roll's edge flag (it would draw once per tick while stood in).

**The bench** [`bench/roll1.field.toml`](bench/roll1.field.toml) (30900): an ephemeral stream `eph` (seed 1, x0 14369)
drawn by two consumers (`pick` 0..5 and `die` 1..6), a persistent `dwix_rs1` (id 6004900, x0 28707, check word
26896899) drawn into `pickp` 1..100, an `epoch` counter bumped by an edge (the Main_Init witness: 0 after every
entry), a SEEDED walker wander (private stream, x0 30217) beside a STOCK control wander, and a HUD row per state.
`rung1_roll.py` runs two launches chained by a state file; every slot, flag and vector index comes from a dry compile
of the bench and every expected value from `rollstream.py` — nothing hard-coded.

| Check | Result |
|---|---|
| preflight: the DEPLOYED `.eb` | exactly 4 advances (3 rolls + the seeded wander), all `const(236) B_MULT const4(65537) B_REM`; no 237 |
| NC1: the first entry's autosave (taken before Main_Init) | written, no stream vector in it |
| A0: seeds on the HUD | E 14369, P 28707, CHECK 1 — the oracle's x0s, persistent guard live |
| K3: before `walk` (and after every re-entry) | both wanders' `wtx`/`wtz` read their box centres (Main_Init preset) |
| W1: the seeded walker's first 5 targets | **(225,−915) (152,−1023) (−96,−1332) (−241,−1371) (−297,−1308)** — exactly the prediction |
| A1: 16 ephemeral draws | PE[1..16], each roll == state % 6 |
| A2: 45 frames after the last draw | no extra draw — the edge was consumed once |
| A8: a second consumer on the shared stream | takes PE[17] (49887 → die 4) |
| A1p: 8 persistent draws | PP[1..8], each roll == 1 + state % 100 |
| A3: `~ Reload` (a same-field warp) | epoch 0 (Main_Init ran); E re-seeded to 14369; **P held PP[8] = 44440** (no re-seed, no hidden draw); the walker replays the identical 5 targets; 16 draws replay PE[1..16] |
| NC2: the stock control across that reload | a DIFFERENT sequence — the instrument can see the difference |
| A4 | the persistent stream continues: PP[9] = 1920 |
| A5a: the reload's autosave, decoded offline | P = [44440] under guard word 26896899, E = [49887] |
| A5b → Continue (a fresh process) | B0 the sandbox save is byte-identical to the one WRITE left; the nonce came back |
| B1 / NC5 | P loaded at PP[9] = 1920; E re-seeded to 14369 although the save held PE[16] |
| **A5: a reload cannot re-roll** | the 4 draws after Continue **== the 4 "doomed" draws** WRITE made after its save (59898, 45473, 49097, 52380) |
| B2: a new process | PE[1..3] and the walker's 5 targets again |
| A7: discrimination | a = 237, a = 235 or seed 2 would mismatch all 16 recorded ephemeral positions |

Artifacts: `.harness-runs/20260923-021615-rs-rung1-write`, `.harness-runs/20260923-021725-rs-rung1-continue`
(archived with rung 0's into the main repo's `.harness-runs/`).

**Offline:** `tests/test_rollstream.py` (the generator proof, seed hash goldens, bias bound) and
`tests/test_behavior_stream.py` (emission, laws, the persistent guard/repair, and the EXHAUSTIVE 65536-state check that
the compiled advance + draw, run in the `.eb` interpreter, equals `rollstream` for every state); 15/15 guard mutants
killed; all 40 repo `[behavior]` tomls compile byte-identically before/after. The Workspace simulator replays a seeded
wander's stream (`workspace/behaviorsim.py`).

**Not in scope (and why):** streams on `brains`/class rows (one emitted site drives N members — unproven); a
battle-side draw (the ledger already covers battle → field); time-seeding (it would defeat the point).
