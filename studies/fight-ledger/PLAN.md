# The fight writes the ledger — enemy AI as a producer of persistent state

**Origin:** board entry #4 of [`../eb-uses-board/BOARD.md`](../eb-uses-board/BOARD.md) (dossier:
[`gap-1.md` § 2](../eb-uses-board/dossier/gap-1.md#2-the-fight-writes-the-ledger)). It is the first consumer
of the persistent tables arc ([`../persistent-tables/PLAN.md`](../persistent-tables/PLAN.md)): an enemy's
battle `.eb` writes rows into a field's `persist = true` table, and the field that catches the player after
the fight — or any field later — reads them back. Every shipped field↔battle seam runs one way (pick a
scene, pick music, handle losing). This is the return path: who fell, to what, how the fight went.

**Status:** Rung 0 ★ PASSED in-game (harness, one launch, 31/31 checks).

---

## Rung 0 — can a battle `.eb` write a field's persistent table? ★ YES

`rung0_ledger.py`, one launch, three benches in [`bench/`](bench/) (all scratch, `FF9CustomMap`):

| Bench | Id | Role |
|---|---|---|
| `ledger0.field.toml` | 30870 | declares `fight_ledger0` (persist, id 6004870, 16 zero cells); a never-raised `battle` branch installs the tag-10 Main_Reinit; a `table_ge` branch raises `seen_b` when cell 8 turns 1 |
| `scene_a/battle.toml` | 30871 | EF_R007 forked to one Goblin (HP 90), **no** `die_atk`; writes from tag 0, tag 7 and an added tag 9 |
| `scene_b/battle.toml` | 30872 | the same with `die_atk`; tag 9 records the killer, command, ability, own HP |

The forked donor assets (`scene/`, `.fbx`, `image*.png`) are Square Enix bytes and are gitignored;
each `battle.toml` header carries the `battle-import` line that regenerates them.

| Step | What it showed |
|---|---|
| New Game → 30870 | the table seeds: 16 zeros under check word 20525896 (negative control) |
| battle A (no `die_atk`) | Init wrote cell 0 = **30871** (`B_SYSVAR[24]`, the scene) and cell 1 = **30870** (`B_SYSVAR[191]`, the field it came from); tag 7 ran **once per hit** (2 hits, 2 Attacks) **including the lethal one**, recording ability 176 (Attack) and its own max HP 90 via `B_SYSLIST[1] B_MEMBER(35) B_PICK`; the added tag 9 **never ran**; the hook's flag bit was set before the field came back |
| return | tag 10 ran and returned: the player walked 840u |
| battle B (`die_atk`) | tag 9 ran on the killing blow: `B_SYSLIST[0]` = **1** (Zidane), `B_SYSVAR[28]/[29]` = **1/176** (Attack), own cur.hp **0**, the killer's max HP **131** (Zidane had levelled after A — read live), enemy list count **1**; tag 7 ran for the 2 non-lethal hits and **not** for the lethal one (only one hook per kill); the Goblin, never authored for `die_atk`, died without stalling |
| return | walked 900u; **the field's own ticker read cell 8 and raised `seen_b`** — the catching field reacted to the fight in the same session |
| 30863 / 30870 / 30863 | the entry autosaves before and after 30870's fresh `Main_Init` both hold the identical 16 cells; its HUD shows them after the guard: **a declaring field's re-entry keeps the battle-written ledger** |

Artifacts: `.harness-runs/20260922-220500-fl-rung0` (report, shots, steps).

### What rung 0 established (measured, not read)

1. **Battle `.eb` shares the field's expression layer, write path and vector store.** `0xD3` VECTOR as a
   `B_LET` lvalue works from a battle body; nothing clears or restores vectors around a battle.
2. **Tag 7 is the post-hit reaction, not the ATB turn.** It runs on every effect landed on the enemy
   (the lethal one included when the enemy has no `die_atk`). The kit's labels called it "ATB"; tag 5 is
   the ATB turn (`ProcessEvents.cs:136`).
3. **Tag 9 (Dying) runs only with `die_atk`** — and, per the engine, only on a player's killing blow
   through the damage calculator with no Petrify/Venom/Stop/Freeze/Death/Sleep on the target
   (`SBattleCalculator.cs:335-338`). With it, the lethal hit's tag-7 request is refused: exactly one hook
   per kill.
4. **Inside tag 9**: `B_SYSLIST[0]` = the killer's battle id, `B_SYSVAR[28]/[29]` = the killing command /
   ability, `B_SYSLIST[1] B_MEMBER(n) B_PICK` = the dying enemy's own stats (0 HP), the enemy is still in
   `B_SYSLIST[3]`. `B_MEMBER` needs `B_PICK` to read a scalar.
5. **The return path is tag 10 only** (`Main_Init` does not run); the field's behavior ticker resumes and
   sees the battle's writes. The return does not autosave — the rows reach disk at the next fresh field
   entry.
6. **A fixed-length table written in place stays under the persist guard.** Nothing in rung 0 appended;
   an append (index == n) or a size change would make the next declaring `Main_Init` re-seed the table.

### Engine facts behind it (source, `C:\gd\FFIX\Memoria\Assembly-CSharp`)

- Battle scripts start through the same `EventEngine.StartEvents` (`HonoluluBattleMain.cs:212-218`); the only
  battle branch in the interpreter sets `SysList[1]` to the running object (`EBin.cs:180-184`).
- Tag requests: 5 at level 3 (ATB, `ProcessEvents.cs:133-139`), 6 at 1 (counter), 7 at 2 (every
  `CalcResult` on an enemy, `SBattleCalculator.cs:342`), 9 at 0 (`:335-338`); a request fires only below
  the object's current level (`EventEngine.cs:339-349`).
- Victory waits for every enemy's `die_seq == 6` and no queued EnemyDying (`btl_sys.cs:65-67, 89-90`), so a
  tag-9 body's first instructions always run; a removed enemy's script is suspended, so nothing after a
  long `Wait` in tag 9 is safe.
- Return: `EventEngine.cs:666-671` restores the field context, requests entry-0 tag 10, suspends the rest;
  `updateModelsToBeAdded.cs:47` consumes the snapshot, so a later warp into the same field is a fresh load.
- A Game Over discards the fight's rows (the save reloads); an escape keeps any rows written before it.
