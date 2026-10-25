# An adversarial review of the World tab's GUI work, C12 to C23

**Status:** DONE, 2026-10-25. Owner request: "adversarially review the GUI changes that we've covered so far", then
"Fix the confirmed findings here ... One commit per fix with a test that fails before it."

## Method

Four rounds, each run as a workflow: a finder per slice, an independent skeptic told to refute each finding (it
reproduced or traced every survivor), and in the first two rounds a completeness critic. Rounds 2 to 4 reviewed the
fix commits of the round before. Every fix is one commit with a test that failed first. A test-only fix was shown
to fail by breaking its guard in memory (a pytest plugin swapping one line). Offline only: no game, no lab, the
install never written.

| round | reviewed | confirmed | fixed in |
|---|---|---|---|
| 1 | C12, C13, C16, C17, C18, C19, C21, C23 | 20 (1 high, 7 medium, 12 low) + 4 latent or unproven | 20 commits, 9499a5bd..3ec94eea |
| 2 | those 20 fixes | 13 | 10 commits, e4584c48..8b59402b |
| 3 | those 10 | 7 + 1 plausible | 6 commits, 4e878034..5141f2ad |
| 4 | those 6 | 7 (1 high) | 4 commits, 02d56505..e8c4176b |
| 5 | those 4 | 4, all low | 4 commits, 8c46a22a..c871a128 |

Round 5's four fixes had no sixth round: the rounds went 20, 13, 7, 7, 4, and the last were all low. All 44 commits
are ac551cfe..c871a128.

Left as latent (round 1, not confirmed reachable): the mountain card's zip-edge bound ignores the rim grain at
spread > 1 (no qualified donor shown to be refused wrongly); the bank-skip refusal marks take z from the normal (the
branch cannot fire); a mod's TransportControls.csv that remaps the gold chocobo's mode would make the Dead Pepper
choice raise.

## What it found, by law

**THE OWED PROMOTE.** C19's chain (revert the promotes over a step, edit it, promote back) kept what it owed the game
in memory, and promoted the whole draft back. A step placed after the last promote went into the game, even on
Cancel; the app closing or dying mid-edit left the game reverted, silently; a folder switch sent the cancel to
another folder's draft. Setting the later steps aside by undo and redo was tried and broke three ways (a disc-4
rebase makes the undo refuse; the redo puts an old ledger over the one the promote took; a death mid-promote left them
undone). What holds:
- an in-game step opens only with nothing after the game's steps on top: Promote or Undo them first;
- what the game is owed is on disk (`draft.owe_promote`), settled by the next launch or scan;
- closing the window waits for every job that writes, one after another, and a card's own; then it cancels and
  promotes back.

**ONE LOCK ROUTINE, AND A CARD THAT WRITES IS NEVER KILLED.** Gating each path that opens or closes a card was found
wanting three rounds running. What holds:
- `WorldDoc._on_bar_hold` / `_sync_locks` is the one place:
  - while the recipe bar holds the draft, no card opens but the edit's own;
  - while a card writes, every control that would close it waits;
- `CarryTool.close_tool` waits for a write and kills only a Check: the law at the one call site where a card's job
  dies. It waits for every call of the job (`finish_writes`: the sink's and the coast's Accept is two).
- A card's own Close and Cancel edit are off while it writes. Waiting there froze the window, and a Cancel waited
  out the Accept, which then accepted the edit.
- A scan landing waits for the cards' writes before it moves the tab.
- When the bar starts holding, it puts away every card it found open.

**A READ IS KNOWN BY ITS NUMBER, NOT ITS PATH.** An edit rewrites the draft at the same path. A read begun before (the
river's, the island's) landed after and decided the edit. So did its error, which came back with no number. Every
read now carries its number or generation, and so does its error; an outline read names its massif. The 3D view
draws the last load asked: one asked while another ran was dropped, and the view kept the old folder.

**A JOB ALWAYS ENDS.** A program that cannot start sends no finished signal: the runner stayed busy and a card's
write never ended, locking the tab. A failed start ends as a failed job. A refusal moves nothing, so it tells no
one the draft moved.

**THE SAID-BACK LAW WAITS FOR WHAT IT RESTS ON.** A mountain row's ground and reach follow reads, so saying the row
back at once refused every mountain off grass. Letting a retune skip the law instead opened rows the card cannot say.
The row now waits with its handles frozen, and rows compare as the editor writes them (`recipe.canon`).

**READ THE ENGINE, NOT THE COMMENT.** Memoria's fog defaults are its `BindInt32` values (250 / 350), not the ini
comment's "vanilla" 86 / 142. Its CSVs come through `GetCsvWithHighestPriority` (the stack first) and a .NET
`StreamReader`, which replaces bad bytes and strips a byte-order mark: `gamecam.csv_text`, for both tables.

## Not checked

No in-game run: the fixes touch the editor's own bookkeeping and the 3D view's fog, not the bytes a verb writes. Real
QProcess timing was emulated (a held runner), not timed.
