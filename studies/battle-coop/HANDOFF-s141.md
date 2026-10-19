# Handoff: battle co-op group 2, next is s141 (2026-10-19)

## Where things stand
- **Deployed live:** s140. Assembly-CSharp `2be623db3bb2ecb5`, backup `20261018-233617`
  (`py tools/restore_memoria_dll.py 20261018-233617` reverts to s139). Memoria.ini sha `efaebbf47c36e752` (the owner's;
  the selftest runners now SNAPSHOT it at the start of each block and restore that snapshot, never a fixed backup).
- **Done:** action replay s133-s137, the field model s138 (instrument), s139 (the host's rule and section 8) and s140 (the
  guest dresses itself, plus rig rows 9-12 for CharacterId 8-11), each deployed, proven in game and merged to master.
- **Branch:** `claude/build-s140-2148ea` (worktree `gallant-easley-04ab74`); master has it merged.
- **The record:** `studies/battle-coop/R3-GROUP2-BUILD.md` (the s140 section and its lessons), `memoria-patches/README.md`
  (the authoritative rows), `studies/battle-coop/R3-FIELD-MODEL-AUDIT.md` 2.4 (the s141 brief) and 4.5 (leg F).

## Owner decisions (all binding)
- s139 D1: the host's GhostAs is the one knob; a guest's SelfDress=0 only switches off its own dressing.
- s139 D2: a spectating guest (GuestSlots 0) wears the MOOGLE.
- 2026-10-17: Blank, Marcus, Cinna and Beatrix (CharacterId 8-11) get THEIR OWN MODELS (rigs 9-12: Cinna 107, Marcus 109,
  Blank 5467, Beatrix 204; rig 8 stays the moogle).
- 2026-10-18: the disc-1 opening is ACCEPTED as built: a guest puppeting Cinna / Marcus / Blank stands beside that
  member's own NPC (two Cinnas in field 63 after battle 338). Audit 2.3 amendment 13's "never dressed" no longer holds.

## Next: s141 -- polish (audit 2.4)
- Lighting fallback (fldmcf.cs:81 the `netDressSrc` row; the ghost fallback at the local player's row), mesh-op drop,
  MapFootstep (Steiner 925; the moogle and Quina drop 16-19, including 19), held props to the worn rig's R_hand pair, the
  optional twin clips for ladders/jumps (s140 already runs the jump slot on stock ticks), the `selfdress polish on|off`
  lever, leg F (F1-F8).
- Carried from s140: Cinna has NO stock footstep registration (her row is -1/-1: she walks silently -- decide in s141);
  Cinna's and Marcus's hand bones came from the kit's label_skeleton heuristic (labels_for has no R_hand for their family):
  s141's prop remap must read the rig table, not labels_for; `objects[].body` was deferred (N legs judge the player's body
  witness and per-load dress lines instead); the bench's flag bits 13200-13218 sit in the campaign lane of flags.py.
- The bench field 30606 ships through `py studies/battle-coop/bench/selfdress_bench.py deploy` (deploy_field.py, then the
  seated conductors); a stale seat fails S140-PF closed. COOPSUB 30605 seats Blank (CharacterId 10).
- Then s142 (the selftest Leave-mid-swirl strand fix, queued since s134).

## The per-patch recipe that worked (s133-s140)
1. A build workflow (census or audit inputs, engine stages in the clone with `build_memoria.py --no-deploy` only, harness,
   bench), then a review workflow (5 lenses, two skeptics per finding, fix, re-review, fix). The s140 scripts are under the
   session's workflows dir; the review script re-cuts the patch with `studies/battle-coop/bench/run/recut_whole_hunks.py`
   so rewritten selftest blocks sit whole.
2. Verify yourself: `py -X utf8 tools/memoria_stack_replay.py diag` (34 of 34), `git -c core.autocrlf=false apply
   --numstat <patch>`, a FORCED recompile (touch a source: an up-to-date build skips CoreCompile), the domain tests
   (test_harness_netsync, test_memoria_stack_replay, test_coop_peer, test_harness, test_coop, test_coop_tab,
   test_dress_census, test_harness_duo; `-n 6`, about 25 min). Commit as "captured, compile-checked, not deployed".
3. Calibrate the new bench RED on the live previous DLL (COOP_CALIBRATE=1) before deploying.
4. **Ask the owner before deploying** (`build_memoria.py` overwrites the live DLL).
5. Prove: the new bench + every lever, the regression block A, the tape legs, the T2 cut legs, AND every earlier DUO leg
   (coop_dress_wire.py): a later patch can turn an earlier bench's invariant into a stage fact.
6. README row, build-log section, the CLAUDE.md section-10 line (<= 200 chars), the memory note, commit,
   `git -C C:\gd\Dream-World-IX merge --no-ff`, check the ledger line.

## Runners (in the repo; edit `WT=` to your worktree)
- `studies/battle-coop/bench/run/selftest_block.sh <outdir> <label>:<field>:<scenario>[:ENV=VAL,...] ...` and
  `selftest_block_noghost.sh` (GhostAs blanked); `cal140.example.sh` and `full140.example.sh` are the s140 calibration and
  proof blocks. Write run outputs OUTSIDE the repo (the example runners write next to themselves).

## Laws learned the hard way
- THE UNATTENDED LAW: controllers off, FF9 windows unfocused during runs.
- A sampled witness's origin is a BRACKET; never depend on which move or clip a run picks.
- A twin that judges the actual wire can pass a stale body: pin the phase's intended dress too (s140's G9f).
- Run coop_tape_record.py into its OWN `COOP_TAPE_DIR`.
- Long inline heredocs with backslashes or apostrophes break in this shell wrapper: write scripts to files.
