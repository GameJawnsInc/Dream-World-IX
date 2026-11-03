export const meta = {
  name: 's166-a0b-pairing-pull',
  description: 's166 round A, piece A0b: the pairing pull (decision 26) -- engine, review, T2/duo bench legs, reconcile',
  phases: [
    { title: 'Engine', detail: 'WorldOutStep term 3 narrowed, ArmMirror lifted and called at the world landing, the pairpull lever and key; then an adversarial review that fixes' },
    { title: 'Kit', detail: 'the stand-in pairing window + arm, coop_world_walk.py T2-A pair (+ D-PAIR if the duo can pair late), the s165 not_mirroring re-keys, tests' },
    { title: 'Reconcile', detail: 'kit vs engine contract, the offline tests once' },
  ],
}

const WT = String.raw`C:\gd\Dream-World-IX\.claude\worktrees\dreamy-allen-a2375f`
const SP = String.raw`C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX--claude-worktrees-dreamy-allen-a2375f\3f9e72b5-f0f3-488a-a7a3-4b0fc4406058\scratchpad`
const CLONE = String.raw`C:\gd\FFIX\Memoria`

const CONTEXT = `
You are building round s166 of the ff9mapkit netsync co-op stack for the FF9 Memoria engine: world-map co-op RUNG 2, ROUND A, and within it ONLY PIECE A0b: decision 26, THE PAIRING PULL. Piece A0 (decision 19, the control-off kit-cell close: NetSyncWorldWalk.cs, the \`worldwalk\` sub-verb with \`kitcell\`, the key netsync.world.kitcell, coop_world_walk.py's A-KITOFF / A-FERRYOFF) is ALREADY built, deployed and benched: build beside it, never change it. Nothing else of round A (no wire change, no trailer, no ghost, no dot change) -- later pieces come later, each built and benched alone.

READ FIRST: the design ${WT}\\studies\\world-coop\\S166-DESIGN.md -- decision 26 (the whole of it), "What happens today" (the pairing wait, the stall hole), decision 14 term 2 (THE WORLD PAIRING RULE), decision 25 (the harness), engine piece A0b, the bench (T2-A pair, the Duo row's D-PAIR, the stand-in, the Order paragraph). Then the two-PC evidence: ${WT}\\studies\\world-coop\\TWO-PC-CHECKS-S165.md "Results" finding 1 (the guest's line "world follow-out: waits: not mirroring the host's story yet (the pairing window: the s144 wait stands)", its pairing autosave written at pairing).
The code you change, in the clone (re-find every site by grep; line numbers drift):
- Memoria/Netsync/NetSyncWorldFollow.cs: WorldOutFacts (Mirroring, Bench), WorldOutStep's term 3 (WhyNotMirroring, THE PAIRING-WINDOW LAW), the Why* codes/names/words (benches key on the stable names: APPEND a new code at the end, never renumber), the proof ("world follow selftest: OK (N rows, M mutants)") and its mutants.
- Memoria/Netsync/NetSyncClient.cs: the facts' gathering (\`f.Mirroring = _storyMirroring;\`), THE PAIRING WINDOW (s154: _pairWindowOpen, _pairWrittenWhere, _pairSavedThisEntry, PairingEvaluate, PairingDurableVerdict / PairingLiveVerdict / PairingSaveVerdict, PairWindowAfter, NotePairingAtArm), the field-load mirror arm (the block that logs "state-mirror ARMED -- this guest's fields now stage the HOST's story": _storyMirroring = true, NotePairingAtArm, _sameFieldKickTries = 0, NetSyncSelfDress.ArmFromState(host), RestorePassEntrance), and s165's LandWorldOut (its ApplyStory of the chosen frame; its comment "The mirror is never armed here").
Background: s165's design ${WT}\\studies\\world-coop\\S165-DESIGN.md (decision 1, decision 9 the landing), s154's pairing autosave (grep "s154" in NetSyncClient.cs), and the A0 code as the idiom for this round's harness additions (NetSyncWorldWalk.cs, HarnessAgent.cs's worldwalk case).

THE CLONE: ${CLONE} (shared; THIS session holds it per the round queue). Engine source: ${CLONE}\\Assembly-CSharp = upstream 6b8bb2d5 + the stack s12..s165 + s166's A0 (uncommitted, by design). The s166 delta so far: \`py ${SP}\\s166diff.py --stat\` / \`py ${SP}\\s166diff.py <path relative to Assembly-CSharp>\` (against the s165 snapshot). A snapshot of the clone AT THE A0 BUILD is ${SP}\\s166a0base -- A0b's own delta is the clone against it (diff it yourself with Python/difflib, or pass the snapshot to s166diff's logic).

RULES (non-negotiable):
- Tag every hunk: at least one ADDED line in each hunk carries \`[ff9mapkit netsync s166]\`.
- Keep each file's line endings exactly (NetSyncClient.cs and NetSyncWorldFollow.cs are CRLF; HarnessAgent.cs is LF -- check). Edit with the Edit tool or Python bytes I/O; NEVER a PowerShell text round trip. Never reformat untouched lines. Keep any BOM.
- Match the netsync idiom exactly (Int32/Byte[]/String/Boolean, Log.Message("[NetSync] ..."), pure rules with a truth table and mutants proven caught, comments that say WHY). Only C# features the surrounding code already uses.
- Compile ONLY with \`py tools/build_memoria.py --no-deploy\` from ${WT}. NEVER without --no-deploy. Never run restore/backup tools, never touch the game install, never launch the game, never run the in-game harness.
- The wire stays v14; the harness protocol stays 5 (keys additive; every new key at its sentinel in AppendNetsync's netsync-off catch literal with a history line). No new ini knobs.
- Never commit in the clone; never edit memoria-patches/*. Never throw from a per-frame path.
- Never break s144 (the freeze, the rejoin, the waiting line), s145, s154 (THE PAIRING-WINDOW LAW's real job: a pairing autosave written in the window before the first netsync commit closes it -- a follow-out commit is such a commit), s164, s165 (the follow-out, the dot, the save guard), A0. Behaviour must be byte-identical for: a mirroring guest (its window already closed at the arm), the selftest bench (exempt from term 3, never mirrors, never arms), a host, vanilla, and \`pairpull old\` (s165 exactly).
`

const CONTRACT = `
THE A0b HARNESS CONTRACT (protocol 5, additive):
- \`netsync worldwalk pairpull old|act\` (any role; old = s165's term 3 and no arm at the world landing; act = the default). \`netsync worldwalk clear\` releases it too; released with the harness on every role (A0's scheme).
- A NEW key \`netsync.world.pairpull\`: {lever:"act"|"old", pending:bool (term 3's new fact now), arms:int (mirror arms at a world landing), last_world:int (-1 = none)} -- netsync.world's LAST key, after A0's \`kitcell\`; its sentinel in the catch literal.
- \`netsync.world.out.why\`: the new refusal's stable name \`pairing_save\` (words: "your pairing autosave is still pending"); \`not_mirroring\` stays the name under \`pairpull old\`.
- Log lines: the world landing's arm logs "[NetSync] state-mirror ARMED at world map W's landing -- this guest's fields now stage the HOST's story" (keep the "[NetSync] state-mirror ARMED" prefix the benches grep); NotePairingAtArm's no-autosave line names "world map W's landing" there instead of fldMapNo. The proof line stays "[NetSync] world follow selftest: OK (N rows, M mutants)" with the new rows and mutant counted in.
`

const TEST_RULES = `TEST SCOPE AND PROCESS (world-map work runs the world-map tests, never the co-op suite; the nightly gate owns the rest):
- From ${WT}. THE A0b SET: ff9mapkit/tests/test_coop_world_walk.py, ff9mapkit/tests/test_coop_world_follow.py, ff9mapkit/tests/test_coop_world_wait.py, ff9mapkit/tests/test_world_coop_harness.py, ff9mapkit/tests/test_harness_world.py, ff9mapkit/tests/test_coop_peer.py, plus THE SHARED-HARNESS PINS \`py -m pytest @${SP}\\hn_pins.txt -q -n 6\` (append the node id of any test you add or change in test_harness_netsync.py).
- ONE pytest process at a time, never while its imports are being edited; long runs \`-n 6\` in the background to a log under ${SP}; iterate by node id / -k; a red that goes green alone on a quiet re-run is load noise (note it). Report each command, wall time, counts.
- Never leave a pytest or xdist worker running when you finish (a live bench refuses to start under one).`

const IMPL_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    files_touched: { type: 'array', items: { type: 'string' } },
    hunks_added: { type: 'integer' },
    compile_ok: { type: 'boolean' },
    compile_tail: { type: 'string' },
    selftest_rows: { type: 'string' },
    sites: { type: 'array', items: { type: 'string' } },
    pending_predicate: { type: 'string', description: 'term 3s new fact exactly as built: which pairing-window state it reads, and why that is the law protects' },
    deviations_from_design: { type: 'array', items: { type: 'string' } },
    open_issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'files_touched', 'compile_ok', 'compile_tail', 'selftest_rows', 'sites', 'pending_predicate', 'deviations_from_design', 'open_issues'],
}

const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          claim: { type: 'string' },
          evidence: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed-fixed', 'confirmed-not-fixed', 'refuted'] },
          fix_note: { type: 'string' },
        },
        required: ['id', 'severity', 'file', 'claim', 'evidence', 'verdict', 'fix_note'],
      },
    },
    compile_ok: { type: 'boolean' },
    compile_tail: { type: 'string' },
    summary: { type: 'string' },
  },
  required: ['findings', 'compile_ok', 'compile_tail', 'summary'],
}

const KIT_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    files_touched: { type: 'array', items: { type: 'string' } },
    tests_run: { type: 'string' },
    tests_green: { type: 'boolean' },
    bench_how_to_run: { type: 'string', description: 'exact command lines for each A0b leg (OLD on the A0 build, NEW, the lever) with env vars, tapes and the --from second, and what each needs (the owner bridge down for T2, etc.)' },
    contract_assumptions: { type: 'array', items: { type: 'string' } },
    open_issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'files_touched', 'tests_run', 'tests_green', 'bench_how_to_run', 'contract_assumptions', 'open_issues'],
}

phase('Engine')
const engineP = (async () => {
  const e = await agent(`${CONTEXT}
${CONTRACT}
YOUR STEP: THE ENGINE for A0b, in the clone.
1. THE TERM. WorldOutFacts gains the pairing window's fact; WorldOutStep's term 3 refuses a non-mirroring, non-bench guest ONLY while its pairing autosave is still pending: the window open, nothing written in it, and no durable decline (a durable decline -- not your own place, autosave off, the stock ladder refused -- means the window will never write, so the follow-out may start). Read PairingEvaluate's own state (the fields it writes, its last verdict) -- never a parallel copy. Find out (and report in pending_predicate) whether the window's tick runs before the world-out tick in the same Update, so a free-standing guest writes and starts within an Update or two. Under \`pairpull old\` term 3 is s165's exactly (WhyNotMirroring). The new refusal is a NEW Why code appended at the end (stable name \`pairing_save\`, the contract's words). The s165 proof gains rows busy / written / durable / mirroring / bench / old, and a mutant that keeps s165's mirroring term (it must fail the written row); keep every existing row and mutant.
2. THE ARM. Lift the field-load arm into ONE \`ArmMirror(Byte[] host, String where)\` that both sites call: the ARMED line (the contract's two wordings: the field load's line stays byte-identical), NotePairingAtArm (its no-autosave line naming \`where\`), _storyMirroring = true, _sameFieldKickTries = 0, NetSyncSelfDress.ArmFromState(host). RestorePassEntrance stays at the field site only. The field site must behave byte-identically (same lines, same order, same guards). In LandWorldOut: after its ApplyStory succeeded, for a live following guest (never the selftest bench, never under \`pairpull old\`), when not already mirroring, call ArmMirror with the frame it applied and "world map W's landing"; count \`arms\` / last_world. Update LandWorldOut's comment ("The mirror is never armed here") to the new truth. Check every reader of _storyMirroring / IsMirroringStory that can run on the world map right after the landing (the save guard R4, the exit ramp's arm, SessionRampArms, the rejoin's story pin, s145's world battle paths, the self-dress) and report what each now does for a pulled guest.
3. The harness: \`pairpull old|act\` under A0's \`worldwalk\` sub-verb (extend its usage text), the \`netsync.world.pairpull\` key (last, after kitcell) with its sentinel and history line, the lever released with the harness on every role.
Compile with \`py tools/build_memoria.py --no-deploy\` until clean. Return the IMPL schema.`, { label: 'engine A0b', phase: 'Engine', schema: IMPL_SCHEMA })
  if (!e) throw new Error('engine A0b failed')
  const r = await agent(`${CONTEXT}
${CONTRACT}
YOUR STEP: an ADVERSARIAL REVIEW of the A0b engine change, then FIX every confirmed finding yourself and recompile until clean. The implementer's report (orientation only; verify everything): ${JSON.stringify(e)}
Hunt for:
- THE PAIRING-WINDOW LAW broken: can the follow-out now commit before a pairing autosave that WOULD have been written (a busy verdict misread as durable; the window tick running after the world-out tick so the start wins the race; a write that fails -- "pairing autosave FAILED" -- read as resolved)? Can the world-out commit close the window with nothing written when a write was still possible?
- the arm: does the field-load path still log the same lines in the same order with the same guards (diff the old block against the new helper)? Is the world arm skipped for the bench, under the lever, on a failed ApplyStory, for a guest already mirroring? What happens on the landing for every _storyMirroring reader (the save guard, the exit ramp and SessionRampArms -- a pulled guest that is then unpaired must ramp back to ITS pairing autosave, not reload something else --, the rejoin's story pin, s145, the self-dress arm, the title's consume)?
- a guest that paired while ITSELF on the world map: unchanged (no field to follow out from)?
- regressions for a mirroring guest, the bench, a host, vanilla, \`pairpull old\` (byte-identical to s165 + A0).
- the proof: rows right; apply 3 mutants mentally and name the catching row; WhyNames appended, not renumbered (the benches' stable tokens).
- the harness contract exactly; the catch literal still parses as JSON with the new sentinel last in netsync.world; the lever released on every role.
- every hunk tagged; line endings preserved; no allocation or log spam per frame.
Compile with \`py tools/build_memoria.py --no-deploy\` from ${WT}. Return the REVIEW schema.`, { label: 'review A0b', phase: 'Engine', schema: REVIEW_SCHEMA })
  return { e, r }
})()

const kitP = agent(`${CONTEXT}
${CONTRACT}
YOUR STEP: THE KIT LANE for A0b, Python only, in ${WT}. NEVER touch the clone.
1. Harness client + stand-in: \`pairpull\` in Session's worldwalk table (A0 added the sub-verb: extend it), State accessors for netsync.world.pairpull, battlewire's s166 contract section (the op, words, usage, the new key's sentinel, the pairing_save name and words, the ARMED line's world wording). The fakegame \`worldwalk\` rung (A0's) gains THE PAIRING WINDOW as the engine has it (read s154's PairingEvaluate and its verdicts in the clone: busy until free-standing, the durable declines, the window's close at a netsync commit or the arm) and the world landing's arm; faults pairpull_early (the start wins before a pending write: the window closes with nothing written) and pairpull_unarmed (lands without the arm: mirroring stays false, the save guard lets a save through).
2. The bench, in studies/test-harness/scenarios/coop_world_walk.py (A0's file; add, never change A0's legs):
   - T2-A pair (the design's primary): the real guest launched on its own field (6603), paired there, never mirrored, against \`coop_peer replay-host --from <T>\` of the COOP_TAPE_WORLD_WALK tape (recorded on s164, v14: no restamp needed while the wire is v14), where T is a tape second at which the host already stands on 9011, on foot, past the 1200 ms debounce (find T with coop_peer's own \`where\`/pose tooling and pin it as a named constant with its evidence). Judges: the guest's pairing autosave line, then the follow-out's start / commit / landing at the tape's pose (within s165's POSE_TOL), \`mirroring\` true and the ARMED line once naming the world landing, netsync.world.pairpull.arms +1, \`savemenu\` refused, and the tape's later rejoin into 300 staging the host's story. Judge after world.block_ready + advancing ticks and on frames first published after each edge. OLD_PREDICTED (the A0 build, where netsync.world.pairpull is ABSENT -- probe first, never send pairpull when absent): the guest waits on its field with why \`not_mirroring\` until the tape's 300. LEVER_PREDICTED (\`pairpull old\`): exactly OLD. Read how the s165 T2 legs (coop_world_follow.py's walk leg, coop_world_wait.py's T2 legs) launch the guest, set its ini, start replay-host and refuse when the owner's Workspace bridge holds 127.0.0.1:49201 -- follow that exactly, and report whether T2 needs that port free.
   - D-PAIR (only if tools/harness/duo.py can start the guest's link after its host stands on 9011 -- a staggered launch, or an existing harness/transport op; find out, never add an engine op for it): the same judges on the duo. If the duo cannot, say so and do not build it.
   - THE PAIRING AUTOSAVE ON THE BENCH: find out what the pairing autosave writes on the bench machine (which slot/file) and whether the s164/s165 T2 legs already let it write; the bench must never overwrite the owner's own saves beyond what those legs already did. Report it.
3. Re-key, never weaken: grep every s165 bench judge and test that expects the guest's \`not_mirroring\` refusal (coop_world_follow.py, coop_world_wait.py, coop_world_battle.py, their tests, fakegame's s165 rung) -- a leg that tests s165's OWN pairing wait sends \`worldwalk pairpull old\` when the probe shows netsync.world.pairpull, by stage, and its tests follow.
4. ff9mapkit/tests/test_coop_world_walk.py: fake-driven reds for every new judge (via the faults and the lever) and the OLD/LEVER predictions on the fake.
${TEST_RULES}
Return the KIT schema.`, { label: 'kit lane A0b', phase: 'Kit', schema: KIT_SCHEMA })

const eng = await engineP
const kit = await kitP

phase('Reconcile')
const rec = await agent(`${CONTEXT}
${CONTRACT}
YOUR STEP: RECONCILE the kit with the final A0b engine, then the offline tests once. Engine: ${JSON.stringify(eng.e)}; review: ${JSON.stringify(eng.r)}; kit lane: ${JSON.stringify(kit)}
1. Grep the clone for every name in the CONTRACT and in the kit lane's contract_assumptions (keys, fields, ops, reply text, log lines, the Why name and words, the proof line). Fix the KIT side wherever it disagrees; if the engine is clearly wrong against the contract, report it (do not edit the clone).
2. Make the stand-in model the engine's FINAL pending predicate and arm exactly.
3. The final offline pass ONCE, nothing being edited: THE A0b SET, whole files, plus the shared-harness pins -- one \`-n 6\` run in the background to a log under ${SP}. Fix kit-side failures you caused; re-run only those node ids.
${TEST_RULES}
Do NOT commit, deploy or launch the game. Return the KIT schema (bench_how_to_run final).`, { label: 'reconcile A0b', phase: 'Reconcile', schema: KIT_SCHEMA })

return { engine: eng.e, review: eng.r, kit, reconcile: rec }
