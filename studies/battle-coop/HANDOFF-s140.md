# Handoff: battle co-op group 2, next is s140 (2026-10-17)

## Where things stand
- **Deployed live:** s139. Assembly-CSharp `1365959f2efca2e7`, backup `20261017-175116`
  (`py tools/restore_memoria_dll.py 20261017-175116` reverts to s138). Memoria.ini sha `efaebbf47c36e752` (the owner's;
  every runner restores it byte-exact from `backups/Memoria.ini.pre-r3-phase1.20261014-222737`).
- **Done:** action replay s133-s137 (s133-s135 owner-confirmed), the field model s138 (inert instrument) and s139 (the
  host's dress rule + wire section 8), each deployed, proven in game, merged to master with the ledger green.
- **Branch:** `claude/resume-r3-build-harness-5e5400` (worktree `zealous-dubinsky-016505`); master has it merged.
- **The record:** `studies/battle-coop/R3-GROUP2-BUILD.md` (per-patch sections, lessons),
  `memoria-patches/README.md` (authoritative rows), `studies/battle-coop/R3-FIELD-MODEL-AUDIT.md` (the s138-s141
  pre-build audit: it OVERRIDES R3-DESIGN.md 3.4; read section 2.3 for s140 and 2.4 for s141).

## Owner decisions (all binding)
- s137: a unit's own SysTrans burst in flight is exempt from the 2.5 s trance cap, bounded at 8.5 s.
- s139 D1: the host's GhostAs is the one knob; a guest's SelfDress=0 only switches off its own dressing.
- s139 D2: a spectating guest (GuestSlots 0) wears the MOOGLE ("2 zidanes just looks weird").
- **NEW, not yet built: Blank, Marcus, Cinna and Beatrix (CharacterId 8-11) get THEIR OWN MODELS** ("their own
  models"), replacing s139's undressed result (two Zidanes in the disc-1 opening). Fold into s140: census their field
  model ids / GEO / idle-walk-run-turn clips / eye bytes from the install (they are playable, so the rigs exist), add
  rig rows (rig 8 stays the moogle; a rig index is not a CharacterId), ResolveAuto maps 8-11 to them, section 8 carries
  charId 8-11, and leg G's 8-11 expectations (its rows and DressSelfTest's ResolveAuto table) change from undressed to
  the rig.

## Next: s140 -- the guest dresses itself (audit 2.3)
- The riskiest patch: the SetModel hook (rewrite po.model/po.eye before the GEO lookup), arming from section 8,
  EntryDefinesPlayer, PosObj.netSelfDress carried through the warm return, MapAnim, and the **blocking B_FRAME timeline
  law** (field 2705 Pandemonium's `GetEntryAnimFrame < GetAnimDuration(8847) - 1` loop must still end on a dressed body).
- Plus the 8-11 rig rows above.
- The bench field: `selfdress.field.toml` at **30606 in FF9CustomMap-msgs** (audit D7). Deploy with
  `py tools/deploy_field.py <toml> --id 30606 --mod-folder FF9CustomMap-msgs`, re-reading every folder's
  DictionaryPatch first; the first launch registers it.
- Bench: coop_self_dress.py legs S/W/X/N/T (audit 4.4); its LEGS registry and PHASES take them.
- Then s141 (polish, audit 2.4), then s142 (the selftest Leave-mid-swirl strand fix, queued since s134).

## The per-patch recipe that worked (s133-s139)
1. One build workflow: engine (clone `C:\gd\FFIX\Memoria`, `build_memoria.py --no-deploy` only), then harness + bench,
   then a 4-lens review with two skeptics per finding, fix, re-review, fix. Template:
   `studies/battle-coop/bench/run/r3-s139-build.workflow.js` (change the patch name, the `--stop-after` baseline and
   the CONTEXT).
2. Verify yourself: `py -X utf8 tools/memoria_stack_replay.py diag` (29 of 29), `git -c core.autocrlf=false apply
   --numstat <patch>`, `build_memoria.py --no-deploy`, the domain tests (test_harness_netsync, test_memoria_stack_replay,
   test_coop_peer, test_harness; plus test_coop, test_coop_tab, test_harness_duo when touched; `-n 6`, about 20 min).
   Commit as "captured, compile-checked, not deployed".
3. Calibrate the new bench RED on the live previous DLL (COOP_CALIBRATE=1) before deploying.
4. **Ask the owner before deploying**: the permission classifier blocks `build_memoria.py` (a production deploy).
5. Prove: the new bench + its lever, the regression set (block A), the tape legs, the T2 cut legs. Rerun genuine flakes.
6. README row, build-log section, the CLAUDE.md section-10 line (it is at exactly 200 chars: SHORTEN it when you edit),
   the memory note, commit, `git -C C:\gd\Dream-World-IX merge --no-ff`, check the ledger line.

## Runners (copied into the repo; edit `WT=` to your worktree)
- `studies/battle-coop/bench/run/selftest_block.sh <outdir> <label>:<field>:<scenario>[:ENV=VAL,...] ...` flips
  [Netsync] Enabled to 0 for selftest-role benches and restores the ini on any exit.
- `selftest_block_noghost.sh` also blanks GhostAs (s139 acceptance step 2).
- `full139.example.sh` and `cal138.example.sh` are the s139 proof and calibration blocks, as models.

## Laws learned the hard way
- `memoria_stack_replay.py emit` needs `--stop-after <previous patch>` once the new patch file exists.
- A sampled witness's origin is a BRACKET (last publish before the event, first after it), never one edge.
- Never depend on which move or clip a run picks; a follow-up that must land before an event rides the same request.
- Run coop_tape_record.py into its OWN `COOP_TAPE_DIR`, or it rewrites the default tapes' latest.json.
- THE UNATTENDED LAW: the owner keeps controllers off and the FF9 windows unfocused during runs (a controller caused a
  title-screen exit and a Pause; a stray key drifts a menu cursor).
- The selftest role seats a "BENCH" impostor (Freya) in Zidane's slot: read identity off the live unit or FF9.party.
- Long inline bash heredocs with apostrophes fail in this shell wrapper: write scripts to files and run them.

## Also pending (not s140)
- A laptop package carrying s133+ for a two-machine sitting. Sitting-B leftovers: defeat, Zidane's Flee gil, the s121
  refusal, the Dali cold re-spec, back-to-back fights. Boxes B19-B29 test the field model after s141.
