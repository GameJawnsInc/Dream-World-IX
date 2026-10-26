# Where the World tab makes you wait, and what would shorten it

**Status:** BUILT, 2026-10-26: the two defects and tiers 1-5 of the ranked list, each fix one commit with a test that
failed first, re-measured per tier; then five adversarial review rounds over the fixes (17, 9, 5, 6 and 4 confirmed,
all fixed). Owner requests: "explore performance improvements next", then "fix the two defects first, then
build the ranked list in order, one commit per fix with a test that fails before it, re-measuring after each tier".
What was built and what it measured is [below](#what-was-built); the exploration as it was written follows.

## What was built

Measured on the real install (read only), each fast path held to the code before it on real data. "Old" is the
module as it stood before the change, loaded from git into the probe (no switch in the package).

| what you wait on | before | after | how it was held to the old bytes |
|---|---|---|---|
| a forest Accept, click to the map back (a later one) | 22-25 s | 5.5 s | end-to-end trace, real tab and job |
| the same, the first Accept of a session (the draft drawn the first time) | 22-25 s | 9.7 s | |
| the click's freeze (begin_step + process start) | 1.2-1.5 s | 2-4 ms | |
| Undo / Redo, click to the map back | 8.2-10.7 s | 0.69-0.86 s | |
| the 3D reload after a 2-cell edit | 5.6-7.5 s | 0.65-0.71 s | Packed and textures == 6/6 (t1_reload) |
| a sink step's history: begin / commit / abort | 2.7 / 5.5 / 11.4 s | 1.7 / 0.74 / 0.65 s, on a worker | whole draft trees == after commit, undo, abort (t2_step) |
| a forest Check | 6.75 s | 5.21 s | verdict and printed text == 3/3 (t3_kernels) |
| world-forest --near | 305 s | 28 s | verdict and printed text == 3/3 |
| hill / mountain Check | 1.81 / 5.40 s | 1.39 / 5.07 s | verdicts == |
| a hill / sink Accept (the card's calls) | 6.6 / 9.3 s | 2.7 / 6.0 s | whole trees and printed text == |
| a recipe row: hill / sink | 6.8 / 26.6 s | 2.5 / 15.9 s | world, ledger, manifest == and == the card's Accept |
| the first 3D view | 9.45 s | 7.0 s | every mesh of discs 1 and 4 bit for bit; Packed == |
| forest ghost drag, per move (GUI thread) | 45-55 ms | 5 ms | 247/247 placements == |
| game-camera frame (GUI thread) | 95-104 ms | 11 ms | 1,868 ground probes == |
| seating the party (GUI thread) | 97-121 ms | 0.6 ms | |
| a card's island ready: reopen / after an Accept | 1.5-2.3 / 3.3-4.0 s | 0.54-0.75 / 0.62-1.08 s | soups == |
| the river card's first open each session | 15-24 s | 12-22 ms (cached) | the cached shape == a fresh read |
| Open...'s click | 13-23 s frozen | the copy and each row's steps on a worker | |

**The two defects** (ef520295, 3ce416e1): the game camera's ground probe now reads the scene drawn now; a Check's
report is disc 1's verdict, with the disc-4 preview's outcome beside it (40d347f8), so the sink and coast cards say
"on disc 1 only" when disc 4's replay refuses.

**Laws the review rounds paid for** (each a defect in a first fix):
- THE RACY-CLEAN RULE, three times (the step history, the md5 walk, the cell memo): a stat is trusted only for a file
  older than 2 s at the moment the stat was RECORDED; judging at the moment of reuse trusted a young file later.
- A JOB ALWAYS ENDS, ON ITS OWN EXIT: a job's output to a temp file, not a pipe another process can inherit; any start
  failure (the temp file included) ends it as a failed job; a done that raises is reported, never let out of wait();
  a call that ended without a verdict died, and is never called unchanged or a refusal (disc 4's call too).
- THE HISTORY IS WRITTEN IN AN ORDER A FAILURE LEAVES WHOLE: a commit renames its folder in first (retried, a fresh
  name), writes the history next and only then trims; an abort that failed is finished before the next step, edit,
  undo, redo, promote or revert touches its cells; a step that cannot be recorded is taken back at once, never left
  for whatever the user clicks next; a discard renames the draft aside before deleting it (Windows refuses that
  whole while a reader holds a file).
- EVERY HISTORY PRIMITIVE IS WHOLE OR NOTHING, AND A REFUSED ONE CAN RUN AGAIN (round 4, after round 3 made one of
  them so): an undo or redo the disk refuses part way puts the step's other side back; a commit whose history is
  refused goes back to pending; an Edit's open moves its folders back and redoes its undos; a cancel takes the
  put-back steps out of the history before their folders go, so run again it finishes the first. A caller's
  rollback is only as true as the primitives under it, and every bar path that can meet the disk catches OSError.
- WORK A REFUSAL LEAVES OWED IS KEPT ON DISK, AND THE DRAFT IS HELD UNTIL IT IS PAID (round 5, after round 4 caught
  the refusals): an edit whose cancel the disk refused stays open with the bar holding the draft -- every bar write
  refuses at its call site, the cards wait, nothing retries behind the user -- until Cancel edit closes it and runs
  the game's promote kept owed; a cancel's redos still owed live in the open edit; a refused take-back is named in
  history/take-back.json for the next abort. Catching an error and letting go of the draft let other writes run
  under a half-closed edit.
- A FAST PATH REFUSES AS THE SLOW ONE DID: a cut-short .ff9mesh raises struct.error, a NaN block takes the loop, a mesh
  the census precompute cannot read is asked per sample.

**Not built, decided after the re-measure:**
- **B3, the warm worker:** a Check still pays 1.3-1.9 s of start-up (UnityPy's import): forest 5.2 s, mountain 5.1 s.
  It would take most of that, at the price of a resident process's risks (PERF's list below). The next lever if
  Checks matter.
- **c4, the bytes-keyed soup memo:** a reopen is already 0.54-0.75 s; it would hold 130 MB for about 0.3 s more.
- **c6, the sink scan over processes:** once per install (126 s); still worth it for a first sink card.
- **D1 / R1, the river:** no river Check can start from the card on the live folder.

**Not checked:** no in-game run (the changes touch the editor's bookkeeping and its readers, not the bytes a verb
writes); the fifth review round's own fixes had no sixth.


## Method

One workflow, four lanes, each with a skeptic who re-ran its probes and tried to refute every number. Then a
completeness critic walked the tab as a user and listed what nobody measured.
- **gui:** the window, the scan and the 3D view.
- **reads:** what a card reads when it opens.
- **jobs:** the Check and Accept subprocesses.
- **chain:** the recipe bar, undo, put-back and promote.

All runs were against the real install, read only. Drafts lived under `out/perf/`, promote ran on a scratch game
root made of copies, and the install was stat-checked unchanged afterwards. Every speedup was a monkeypatch inside a
probe and compared with the shipped code on real data; "identical" below means `==` on bytes, report JSON or arrays.

Times are the min of 3 or more runs, because three lanes and other sessions loaded the 12-core machine. Probes are
in `perf/` (prefix = lane, `verify_` = skeptic, `critic_`). Evidence is under `out/perf/<lane>/`, local only.

## What you wait on today

| wait | where | measured |
|---|---|---|
| **every draft change reloads the whole 3D map** (Accept, Undo, Redo, Edit, Cancel, Delete, promote, revert, rescan) | worker; the view shows "Loading the map..." | 6.9-7.5 s alone, 8-16 s in the tab. A forest Accept is 22-25 s from click to map, and only 6-7.6 s of that is the job. Edit is usable after about 11.4 s. |
| **a sink Accept freezes the window** (begin_step / commit_step over all 480 cells, 2,088 files) | GUI thread | 10-16 s each time, 22-36 s the first time per draft |
| the same snapshot for island, carry, sink, morph and river rows in a put-back or Open... | GUI thread | Open... of a 5-row recipe takes 77-89 s, 37-44 s of it frozen |
| a Check | subprocess | forest 5.6, mountain 5.2, sink 3.3, island 3.2, carry 2.5, coast 2.3, hill 1.3 s. Of each, 1.3-1.9 s is start-up: UnityPy's import is about 1 s of attrs codegen that no .pyc caches. |
| the river card's first open each session | worker | 17-24 s, never cached |
| a card's island read | worker | 1.5-1.9 s on open and again on reopen; an Accept reads it twice |
| the sink card's island list, cold | worker | 126-144 s, once per install |
| the first 3D view of a session | worker | 8.1-8.4 s (its label says "about five seconds") |
| forest ghost drag | GUI thread | 45-55 ms per mouse move |
| game-camera frame | GUI thread | 95-104 ms (4 ground probes over 365k tris) |
| seating the party (each vehicle or height change) | GUI thread | 97-121 ms |
| starting any job (`QProcess.start`) | GUI thread | usually 6 ms; 0.5-1.2 s in 4 of 50 starts, cause unknown |

What is fine: the tab's first show (56 ms), the scan (0.7-0.9 s on a worker), the recipe bar's refresh (2 ms), the
chart (5-14 ms), the mountain drag (9-16 ms), a coast click (6-12 ms), a free-orbit frame (9-17 ms), Undo's own call
(0.2 s), and promote's job (5-6 s, then a reload).

**THE FIRST-OPEN COST.** The first open of a file after it is written costs about 5 ms on this machine. For the
2,088 files `ensure_draft` copies, that is 9-12 s for whoever reads them first; later passes take 0.2-0.3 s and a
stat costs nothing. It comes back for long-lived files too, after Defender security-intelligence events (2-3 a day
in the log). That is correlated with Defender, not proven: an exclusion test needs admin. So a fix must avoid
reading a file, not move the read somewhere else.

## Ranked: what to build, in order

Each line gives the gain on the user's wait, how output was shown unchanged, and the effort. CONFIRMED / ADJUSTED
is the skeptic's verdict; ADJUSTED means the skeptic re-measured a different number, and that is the one shown here.

**1. Reload only the cells that changed** (gui C1, CONFIRMED, M). Memo each cell's batches, keyed by the files that
cell resolves through the stack.
- Gain: the reload after a 2-cell edit goes from 6.9-7.5 s to 0.33-0.48 s. In the tab, Undo and Redo go from
  8.2-10.7 s to 0.55-0.77 s.
- Identity: the Packed and the textures are identical in every leg.
- Notes:
  - Leave out the lane's stock-master memo (V1): C1 is as fast without it.
  - The cell memo costs 41.7 MB.
  - Keep the 103 MB texture memo out too; the shipped path frees it after the upload.
- The first Accept of a draft still reads 925 fresh draft files (about 4.4 s of first-open cost). Only a key that
  skips the read avoids that: the manifest sha, so unedited cells hit the stack's memo. Not prototyped.
- Fences:
  - a file rewritten with the same size and mtime must not hit;
  - two changes inside one reload (a double Undo) must not double the wait. The shipped `_next` queue throws the
    running load away, which C1 makes cheap.

**2. One set of reads per draft change** (gui C2 + reads c1 + chain K3, CONFIRMED / ADJUSTED, S).
- The accepting card re-reads its island and its draft line, and then `island_changed` reads them again.
- Every built card, hidden or not, starts a draft-line walk on every change: 4 cards make 12 rglob walks, each
  6-9 s under contention.
- With C1, the duplicate reads are what is left of the Accept's wait. They cost about 1.2-2.6 s off the reload
  through the GIL, and K3 (one scandir walk, shared) another 2.2 s.
- Identity: soups and labels identical, 12/12.
- Law kept: the C12 review fix, under which every card forgets its per-folder reads, still holds.

**3. Stop snapshotting the whole map for one island** (the jobs skeptic's measurement, total estimated; jobs A2
CONFIRMED; S-M).
- `SinkTool._step_cells` returns `all_cells()` because "the disc-4 island's blocks are not known in advance". Yet
  the Check's own dry runs name them, and each of 6 sink Accepts kept exactly 1 cell.
- A snapshot of the named blocks (the union of the disc-1 and disc-4 dry runs) plus a stat sweep proving nothing
  else moved would cost about 0.4-0.5 s, against 10-23 s. The begin on the named block was measured at
  0.004-0.005 s; the total is an estimate.
- A2 (commit writes only the changed cells' "after" copies; one directory listing per row instead of one glob per
  cell): a sink step goes from 9.4 s to 3.5 s.
  - Identity: whole draft trees identical (2,109 and 2,167 files), and still identical after undo.
- `recipe.row_cells` gives `all_cells()` for every non-relief row. Narrowing it needs each verb's WRITE window (C11
  measured the read windows). It touches the undo-completeness law, so it is its own step.

**4. The step off the GUI thread** (jobs A1 / gui C5, ADJUSTED, M).
- On a worker, the longest gap a 10 ms heartbeat saw was 0.02 s; the total wait is unchanged.
- The C19 review law must cover the step: `writing()`, `close_tool`, `finish_writes` and `shutdown` today wait only
  on the QProcess. A quit mid-commit would leave the verb's bytes in the draft with no history record.
- `QProcess.start` (the intermittent 1 s) would leave the GUI thread with it.
- After items 1-3, re-measure before building this: item 3 may leave too little to move.

**5. The Check's own compute** (jobs, all CONFIRMED, S each, all in subprocesses behind a spinner).
- **P1, the census precompute:** each triangle's sample-independent tests are done once per census.
  - Gain: 3.3-3.5x, and the forest census drops from 1.35 s to 0.37 s.
  - Identity: 252 real censuses plus 260 stock stacks, every Check's verdict, and the scan order, which is the
    verdict.
- **P2, a footprint bounding-box prefilter:** the forest footprint law drops from 0.58 s to 0.05 s, and 300
  placements from 192 s to 10.6 s, so `world-forest --near` gains as well.
- **K4:** a draft has no bundles, so its doomed disc-4 mirror attempt should not import UnityPy first. That saves
  about 1 s per job that reads no stock (hill, relief rows), with identical printed text.
- **K2:** plan the sink once per `sink()` call instead of twice. The sink row drops from 21 s to 14 s.
- **K5:** world-fuse's second md5 walk re-hashes only files whose stat moved. That saves 0.4 s per row.
- **C6 F1 + F2, in `world/extract.py`:** an O(1) part lookup and a numpy channel decode.
  - Gain: the first 3D view is 2 s faster. Decoding all 2,199 meshes drops from 4.5 s to 1.5 s.
  - Identity: every mesh on disc 1 and disc 4 decodes identically, down to each float's bit pattern.
  - Every verb shares this code; their gain is not measured.
- **reads c8, a numpy `.ff9mesh` decode:** `read_deployed_blocks` drops from 0.28 s to 0.12-0.17 s, identical on
  all 126 files.

**6. The frames** (gui, S each).
- **C3, the forest preview:** reuse `SoupIndex.lo/hi` and cull the coast to the tested verts' box.
  - Gain: a drag goes from 45-55 ms to 5-8 ms per move, and a drop from 107 ms to 8 ms.
  - Identity: the same dict at 247 placements.
  - CONFIRMED.
- **C4, a plan grid for `ground_y`:** a game-camera frame drops from 95 ms to 10 ms.
  - Identity: the same heights at 1,868 points and the same 36 poses.
  - ADJUSTED:
    - build the grid on a worker when the camera turns on, not in every load (that would cost +0.4-0.5 s each);
    - rebind it on every reload (see defect 1).
- **C7, `_seat_party` off the GUI thread:** removes a 97-121 ms freeze per spin; overtaken seats are dropped.
  CONFIRMED.

**7. Card opens** (reads).
- **c5, cache the river shape per install:** 17-24 s drops to 0.2 ms. Key it on a code stamp and store it as JSON
  or npz, not pickle. CONFIRMED, S.
- **c2, read the frame the preview needs first:** saves 0.9 s on a reopen. ADJUSTED, S.
- **K8, Open...'s discard and `ensure_draft` off the GUI thread:** moves 2-10 s off the GUI thread. CONFIRMED, S.
- **c3, `draft()` from a stat:** stops 14-16 parses of the 423 KB `draft.json` per Accept. CONFIRMED, S.

**Then re-measure, and only then decide:**
- **B3, the warm worker:** forest 5.6 to 3.0 s, coast 2.3 to 0.36 s, carry 2.5 to 0.6 s, island 3.2 to 1.05 s, sink
  3.3 to 1.7 s. ADJUSTED, L. An 8-job resident run gave the same verdicts and draft trees as 8 subprocesses, but
  only n=1. Items 5 and K4 take part of its gain, and its risk list is long: stale modules,
  `_MOD_ENV_CACHE`, decode memos keyed by path, a crash path, shutdown while it writes.
- **c4, a bytes-keyed process-wide soup memo:** a reopen drops from 1.9 s to 0.28 s, but it holds 130 MB. M.
- **c6, the sink scan over 6 processes:** 126-144 s drops to 48-51 s, once per install. M.

## Refuted or not worth it now

- **S7 (copy a step's snapshot from the live folder):** refuted. In the ordinary state (draft warm, live folder
  cold) it makes the freeze 4x worse.
- **D1 (vectorised Delaunay, 19/19 inputs identical) and R1 (river move without its probe composition):** both are
  real, but no river Check can be started from the card on the live folder (no free shift). Keep them for a folder
  where the river can move.
- **G1 (a bytecode prefix for jobs):** only an agent shell sets `PYTHONDONTWRITEBYTECODE`; a human launch gains
  nothing. It does mean job times measured from agent shells before today are inflated 2-3x.
- **Turning off gc around reads:** 19% faster, but a process-wide toggle. An observation, not a candidate.
- **S1 (a disk cache of decoded stock blocks) and c9 (precomputed coast windows):** not prototyped.

## Defects found along the way (not performance)

1. **The game camera probes the old terrain after a reload.** `WorldView3DPanel.set_game_camera` binds
   `ground=lambda gx, gz: ground_y(packed, gx, gz)` to the Packed shown at that moment (`worldview3d.py:1199-1201`),
   and nothing rebinds it.
   - Effect: after an Accept, Undo or rescan with the game camera on, the eye lift reads the old ground, while the
     drawn scene and `_seat_party` use the new one.
   - It also keeps the old Packed and 35 MB of pick arrays alive.
   - Proven on synthetic scenes (`verify_gui_stale_ground.py`: the probe returns 1.0 while the drawn scene is at
     9.0).
2. **A Check's report can carry disc 4's verdict.** `cli._preview_disc4` re-runs the verb on disc 4 with
   `vars(args)`, `report_json` included, so the disc-4 dry run overwrites the disc-1 report the card reads. The
   sink's own replay clears it (`cli.py:5013`); the preview does not.
   - Seen in a real sink Check (`"disc": 4`).
   - The coast's in-place morph goes through the same preview (`cli.py:5324`).
3. The 3D page says "About five seconds for the whole map" (`worldview3d.py:1128`). It is 7-11 s.
4. Aside, bytes identical: Open... re-composes rows in world-fuse tier order, so the reopened history reads
   I, T, S, H, H2 for a saved H, H2, I, T, S.

## Not measured

- An Accept followed by an Undo inside one reload: the shipped queue discards the first load.
- Promote end to end in the tab: estimated 13-14 s, most of it the reload.
- Closing the app during a sink Accept: estimated up to about 18 s frozen.
- A folder switch.
- Check click to verdict, which includes a 600 ms debounce.
- Memory over a session, and with every memo combined (estimated about 355 MB on a 1 GB baseline).
- The hill, island, carry, sink and coast drags.
- What a Defender reset does to the 101 MB worldmap bundle.
- The cause of the intermittent 0.5-2 s process-start stall.
