# Multipart boss retype: in-game check

**Question.** Does `[[scene.enemy]] slot = 0, type = 0` leave a multipart boss whole? Before the fix
(9f7e1c0b), a `type` row wrote the slot's SB2_PUT flags as a plain targetable enemy (1). On the master
(type 0, flags 3) that cleared the multipart bit, so the slave parts had no master.

**Answer: yes, proven in-game by the harness.** Run `.harness-runs/20260923-011306-mp-retype-3` (in the
worktree that ran it), 11/11 checks, one launch:

| Bench | Bytes (slot 0, slot 1) | What happened |
|---|---|---|
| 30910 MPBOSS: GT_R004 (Sand Golem + Core) built by the fixed kit | (0, 3), (1, 3) | The battle initialised and asked for a command. Four Attacks on the Core, the SLAVE part (HP 100 → 54 → 12 → 12, one miss), killed it, and the Golem's AI folded: victory, back to the field. No exception in the battle code. |
| 30911 MPBOSSX: the same battle.toml with the pre-fix kit's bytes | (0, 1), (1, 3) | `NullReferenceException` at `btl_init.OrganizeEnemyData` (from `battle.BattleLoadLoop`), then every frame after it (about 637 in 45 s). It never reached a command prompt. On screen the owner saw the intro camera flip between two frames. |

The two raw16 files differ in one byte: offset 17, slot 0's flags. So the control shows the crash was
real, and that the scenario's log check can see it. The fix bench passing the same check in the same
launch is a real result.

## Reproduce

Scene ids 30910/30911 and the ship-as numbers BBG_B255/B256 were free on 2026-09-23. Re-check the live
`DictionaryPatch.txt` files before reusing them.

1. For each `bench/scene_*/battle.toml`, run its header's `battle-import` line into a scratch dir outside
   the repo, copy the toml over the generated one, and run `tools/deploy_battle.py`.
2. `py studies/battle-multipart/make_control.py` (flips 30911's slot 0 flags byte from 3 to 1).
3. `py tools/play.py studies/battle-multipart/mp_retype.py --label mp-retype` (relaunches FF9; saves are
   sandboxed).
4. Clean up: run `tools/scroll_out/revert_battle_BBG_B255.py` and `..._B256.py`, then remove the two
   `BattleScene 3091x` lines from `FF9CustomMap/DictionaryPatch.txt`. The revert scripts don't touch that
   file. The benches were removed after the run above.

## What the rounds taught

- **The first run's exception checks couldn't fail.** They read `x64/FF9_Data/output_log.txt`, but battle
  code throws into `Memoria.log`. `HonoluluBattleMain.Update` catches the exception and passes it to
  `Log.Error`, so it appears as `|E|` lines with the stack. Uncaught throws elsewhere (`MovePC`) go only to
  output_log. Read both logs.
- **The stat tuning exists only so a New Game party can finish the fight.** Core HP 100 means 2-3 hits,
  so the slave-hit path runs more than once. The Golem gets speed 1 and level 1: its Sandstorm scales
  with HP and it counters every hit on the Core, and at stock speed it wiped a 105-HP Zidane in two turns
  (run 2). These edits change the per-type monster blocks, never the SB2_PUT flags byte under test.
- A shot taken right after `start_battle` catches the black entry fade.
