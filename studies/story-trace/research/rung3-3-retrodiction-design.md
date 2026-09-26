## Rung 3 design: the Dali retrodiction

**The core idea.** Start every side at 359 (the village entrance) at SC 2540 and let the game play its own scripted segment. Then drive a blind exit tour that is registered before any run. Compare stock against **two** fork builds, both built by tools and neither edited by hand:
- **F0** is the current `import-chain` output with no seed. By its own zone rule it omits 450, so the missing member is its only defect.
- **F4** is the same 11 members, seeded by the round-4 kit (`d3e2f4a1`). That adds the pre-tripped latches.

Nothing has to be planted, because both defects come out of the tools that made them.

**Why the start is not a chosen route.** 312 writes 2530/2540 and then exits only to the WorldMap, and no Dali field warps into 359. 359 never reads SC or its entrance: `Int16[2]` is only written, at 359.ebs:12 and :344. It also sets the party itself: it removes non-members and adds ids 0-3 (359.ebs:148-205). That covers the harness's missing party verb (HarnessAgent.cs:714-745). From there the script plays 359→351→352 (359.ebs:344-345; 351.ebs:3552-3797) up to control in 352 at SC 2600.

**Why the tour is not a chosen route.** At every field reached, the tour crosses every walk-in exit in the order `eventscan.scan_gateways` lists them (eventscan.py:105-111). It goes depth-first, returns along tree edges, never talks to anyone, and ignores ATE prompts. It repeats whole passes until a pass adds no new stock key, with a cap of 3. The pass count stock needs is then frozen for every side. 450 is entered only because 350 has an exit to it. The later passes are there because the ping's countdown needs room entries after it. That is a property of the controller, not of 450.

### Smallest first step

**Step 0, offline, minutes.** Extend `storytrace.compare` with three things:
- a `members` set: fork-side rows whose `fld` is a real id after the first member entry count as SEAM;
- a step-window cut: the driver pokes a step counter into a safe-band byte (≥1089, flags.py:54) before each crossing. These arrive as `harness` rows (storytrace.py:720) and are never keys;
- a WRITERS index: for each stock target=value, the donors that wrote it.

Then run mutants on synthetic rows, as rung 2 did (PLAN.md:168-170):
- a 450 visit with `fld=don=450` must be named SEAM;
- the same rows as a member must come out clean.

With `members` omitted, the rung-2 report must not change.

**Step 1, in-game, one stock run.** No deploy, no relaunch, no DLL. New Game → `storytrace(True)` → `warp(359, entrance=0, scenario=2540)` → `watch_cutscene` until control returns in 352 at SC 2600 → run the tour to its fixpoint → `storytrace(False)`.

The approach dies here if either of these happens:
- the segment cannot be driven unattended (a choice stalls `watch_cutscene`, session.py:1830; or `walk_to` breaks on the stock route);
- the blind tour's trace has no `Bit[2102]=1` at donor 450.

Its executed step list becomes the registered route.

### The full rung

**Builds.** Take free ids read live from DictionaryPatch. 30830 is TRC552 now, and 30831-30859 were free at the reader's check.
- **F0:** `import-chain 351 --verbatim --whole-zone --fresh-ids --id-base A --name-prefix T0`, no seed. The dry run already lists `350 -> 450` as an out-of-scope portal.
- **F4:** the same import with `--id-base B --name-prefix T4`, then `story-seed --chain <dir> --beat 2600` from the exported round-4 kit (`scratchpad\r4kit`). Before deploying, check that F4's `[startup]` reproduces PLAYTEST.md:150-157 and :176 (latches 2064/2075/2079, words 239=6 and 296=192, no 297). That check is what makes F4 round 4.

**Deploy.** Use `tools/deploy_field.py <toml> --id N --mod-folder FF9CustomMap` for each of the 22 members, never `deploy_campaign`. Each deploy writes its ForkDonorPatch row (deploy_field.py:382-392), and the engine reads that file per folder (s24-fork-donor-remap.patch:235,272). Relaunch once.

**Runs.** 9 runs in one launch, interleaved S, F0, F4 ×3, using the rung-2 loop (rung2_trace.py:95-106). The only change per side is the start: `warp(<359 or its fork id>, 0, 2540)`. Every side replays the frozen step list.

If a side's field changes when the driver did not command it, that side's tour ends at step k. The analysis then compares the common step window. The seam and seam-field rows are reported separately.

### Pass / fail

| Check | Pass |
|---|---|
| R3-RUNS | 9 closed runs; each reached control in 352 at SC 2600; no INCOMPLETE run |
| R3-DONOR / R3-JOIN | as in rung 2: every member row has `don` = its donor; 0 join failures |
| R3-PING (premise) | `Bit[2102]=1` at donor 450, e19, in 3/3 stock runs; WRITERS lists only 450 for value 1 |
| R3-NULL-PRE (F0) | STOCK ONLY within F0's pre-seam window is **empty**: rung 2 at zone scale |
| R3-SEAM (F0) | 3/3 F0 runs report the seam member(350) → real 450, and 450's ping as a stock key reached only across that seam |
| R3-LATCH (F4) | FORK ONLY holds the prepend (`off<0`, storytrace.py:30) writes 2064, 2075, 2079 = 1; STOCK ONLY holds stock's own `2064:=1`; the new PRE-EMPTED section names 2064 |

**Falsified if any of these happens:**
- R3-PING fails;
- F0 has pre-seam STOCK ONLY keys (zone-scale noise);
- F4 writes the 450 ping (the latch model is wrong).

UNSTABLE keys are listed, not failed.

### What STOCK ONLY should contain, and why

The key is (donor, m, src, sid, tag, off, target, value) with **no `fld`** (storytrace.py:637-651). So a fork that crosses into the real 450 and writes the ping there matches stock. That is why F0 needs the SEAM split, and why the causes separate across the two builds.

**F4 vs S:**
- **450, e19 func 2: `Bit[2102]=1`, `SByte[296]=3|2`, `Bit[2085]=1`** (450.ebs:2186-2199; census offsets 11669/11690). F4's stamped `2079=1` fails the inner guard `2079==0` (450.ebs:2188-2189), even inside the real 450.
- **351, e16 walk-in: `Bit[2064]=1`** (351.ebs:3263-3277). Its guard is `2064==0`, and the F4 seed pre-sets 2064.
- **The controller's `2079=1`, `2075=1`, `296=-64`, `2102=0`**, in whichever room the count reaches 0 (450.ebs:672-749). F4 never gets the ping.
- Expected but not a failure: a few SC-gated keys in 351/352, because F4's 359 member stamps 2600 where stock arrives at 2540.

**F0 vs S:** nothing before the seam. The finding is the SEAM line plus WRITERS (2102=1 ← {450}). That is PLAYTEST.md:178-180, produced without reading a script.

### Risks

- **F4 may be truncated before it reaches 450.** The seed makes 354's Garnet spawn guard true (`297&1 && 2079==1 && 2600≤SC<2610`, 354.ebs:76-85). 297 comes from 359.ebs:51. In scan order, 350 lists →354 before →450. This is the reason F0 is **required**: it carries defect (a) alone.
- **Cutscenes:** a choice inside a scene stalls `watch_cutscene` until timeout. `walk_to` aborts when a scene takes control, so each leg needs a guard and a resume. Stacked story-conditional doors (eventscan.py:1493-1496) are handled by recording whichever field is actually landed in.
- **Seams:** the scripted `Field(450,16/17)` hops in 350-358 and 356→404 (DL_WMS.field.toml:47) leave the zone. They are symmetric across sides but cost time. World exits are blocked at SC 2600-2639 (350.ebs:3412-3426, 450.ebs:1975-1989).
- **Encounters:** none. 350-359 and 450 contain no `SetRandomBattles` or `Battle` op.
- **Ids and names:** EventDB is global, and about 40 worktrees exist, so read DictionaryPatch at deploy time. The T0/T4 name prefixes stop the scene and `.eb` names from shadowing each other.
- **Donor mapping:** a missing ForkDonorPatch row turns a member's rows into fork-id keys and floods FORK ONLY. R3-DONOR catches it.
- **Relaunch:** one, after deploying the 22 ids. Step 1 needs none.
- **The debug warp and bit 184:** the ~ menu warp may set bit 184. It only matters for the first field, and 359.ebs:9-14 handles it.
- **Blind spot:** party and ATE seen-state are outside what the trace records (PLAN.md:192-193).

### Owner questions

1. Is it OK to spend 9 runs (three sides, N=3), given that F4 alone may never reach 450?
2. In round 4, did you go into the weapon shop, and was Garnet there? 354.ebs:76-85 says she should have been under that seed. The trace will test it either way.
3. Where should the forks go: FF9CustomMap, deployed per member (the default, no ini change), or their own folder? An own folder needs a backed-up Memoria.ini FolderNames edit but would survive another session's `deploy_campaign` wipe.
4. After the rung, should the 22 ids be kept or reverted?

Files: `<worktree>\ff9mapkit\ff9mapkit\storytrace.py`, `...\studies\story-trace\rung2_trace.py`, `...\ff9mapkit\ff9mapkit\eventscan.py`, and the decompiles in `<archive>\scratchpad\dali\` (the `<id>.ebs` files).