# The roll stream — a seeded, predictable PRNG in pure `.eb` RPN

**Origin:** board entry #5 of [`../eb-uses-board/BOARD.md`](../eb-uses-board/BOARD.md) (dossier:
[`data-structures.md` § 2, the Lehmer Seed Box](../eb-uses-board/dossier/data-structures.md#2-the-lehmer-seed-box)),
the third consumer of persistent tables ([`../persistent-tables/PLAN.md`](../persistent-tables/PLAN.md)). Every
random draw the kit emits is `B_SYSVAR[0]` (`Comn.random8` = `UnityEngine.Random.Range(0,256)`): impure, shared
with the whole engine, never seeded, never saved. A Lehmer recurrence over one table cell gives a stream that is
deterministic, save-persisted when asked (a reload cannot reroll it), and — because it is pure 26-bit-bounded
arithmetic — **predictable offline**: the one narrow case where a kit gate can genuinely be an oracle.

**Generator:** `x' = 237 · x mod 65537`. Full period (237 is a primitive root of the prime 65537: every state
1..65536 once), largest intermediate 237 · 65536 = 15,532,032 < 2^25 (2.16× headroom), and the best 2-D/3-D spectral
balance among multipliers that fit (the board's 13 mod 32749 falls on 13 lines; the dossier's 75 mod 65537 is
mediocre). A textbook MINSTD (16807 mod 2^31−1) is unrepresentable on the 26-bit CalcStack.

**Status:** Rung 0 ★ PASSED in-game (instrument calibration, 6/6).

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
