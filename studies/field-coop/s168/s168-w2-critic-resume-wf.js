export const meta = {
  name: 's168-w2-critic-resume',
  description: 'Restart of the dead s168-w2-kit-bench critic + reconcile: 5 critic lenses, an adversarial verifier per lens, one fixer, the reconcile (domain tests once)',
  phases: [
    { title: 'Critic', detail: '5 read-only lenses: coverage, falsifiability, twins vs C#, re-keys+runners, the known red' },
    { title: 'Verify', detail: 'one adversarial verifier per lens with findings' },
    { title: 'Fix', detail: 'apply confirmed fixes only; break-it proof for each new check' },
    { title: 'Reconcile', detail: 'kit vs the engine clone once more; the co-op domain test set once' },
  ],
}
const WT = String.raw`C:\gd\Dream-World-IX\.claude\worktrees\sweet-kare-2581e5`
const SP = String.raw`C:\Users\skaki\AppData\Local\Temp\claude\9cb589916070fe89\f146d5fa-a1a5-48bd-ba36-8c1b6983bd56\scratchpad`
const CLONE = String.raw`C:\gd\FFIX\Memoria`
const CONTEXT = `
You are finishing round s168 W2 (the KIT and BENCH side) of the ff9mapkit netsync co-op stack: the co-op GUEST's stock main menu, rung 0 (view-only),
over a seated copy of the host's party (wire v15 cap b3; host section 12). A previous run of this workflow built the kit and the bench, then DIED on a
usage limit in its critic phase. You are part of the restart.
WHERE THINGS ARE (work ONLY here): the worktree ${WT}. It carries the whole s168 W2 delta UNCOMMITTED (21 modified + 16 new files) on top of commit
1f87d546 (W0, the v15 wire registry). The old worktree .claude\\worktrees\\s166-handoff-575aeb is SUPERSEDED: never treat it as truth and never write there
(a hook refuses writes into sibling worktrees; do not route around it).
THE ENGINE is built and reviewed in the shared clone ${CLONE}\\Assembly-CSharp (s158..s167 + the s168 delta, uncommitted by design; NOT deployed: the live game
runs s167 and must stay so until the owner's s167 two-PC session). It is byte-identical to the reviewed snapshot (${SP}\\s168w1snap\\SHA256SUMS.txt, 23 files).
READ-ONLY. The delta: \`py ${WT}\\studies\\field-coop\\s168\\s168diff.py --stat\` and \`... <path rel to Assembly-CSharp>\`. Offline proofs: 'guest menu selftest: OK
(420 rows, 249 mutants caught)', 'seat bracket selftest: OK (19 rows, 7 mutants caught)', 'world walk selftest: OK (534 rows, 198 mutants)'.
THE CONTRACT: the engine builders' reports ${SP}\\s168_w1p1.json (keys ab, core, harn, wire), ${SP}\\s168_w1p2.json (keys e, f, g, h, i; 'i' holds the FINAL
harness contract) and ${SP}\\s168_w1review.json (the review's four fixes: W1 the pairOn term in GuestMenuKeyStep, CR-2 NotPairedLineRule, CR-3 the
outside_settled/uid0_vars/sysvar192 keys, LC1 CutMemoryRule). THE DESIGN: ${WT}\\studies\\field-coop\\S168-DESIGN.md -- decisions 1-21 (s168), 31-36 (the
harness: levers, keys, fingerprint, proof, what each harness proves), "The bench" (the GM0-* rows with OLD/NEW/LEVER and harness S/D/T/O, THE CAL RULE, the
regression set, the Order), "Known limits", and "As built (s168 W1, 2026-11-07)" (W2's first step synced the doc to the as-built engine).
THE W2 BUILDERS' REPORTS (files written, tests run, deviations, open issues): ${SP}\\dead\\result.json, keys sync, kit, solo, duo, regr. The dead critic's
tool-call log (what it read and the leads it was chasing when it died; it edited nothing): ${SP}\\dead\\critic_calls.txt.
THE KIT: tools\\harness\\battlewire.py (the s168 twins, about line 16827 and 17273 on), tools\\harness\\fakegame.py (the opt-in 'guestmenu' rung,
GUEST_MENU_FAULTS), tools\\harness\\coop_peer.py; the scenarios studies\\test-harness\\scenarios\\coop_guest_menu.py (solo S legs, COOP_GM_LEG) and
coop_guest_menu_duo.py (D and T legs); the re-keys in coop_world_walk.py, coop_world_walk_t2.py, coop_world_follow.py, coop_field_swap_timing_duo.py,
_coop_peer_bench.py, coop_tape_record.py; the runners studies\\field-coop\\s168\\round_gm_{lib,old,new,lever,regress,rerun}.sh and round_gm_guard.py; the texts
ff9mapkit\\ff9mapkit\\health.py, ff9mapkit\\ff9mapkit\\workspace\\coopdoc.py, ff9mapkit\\docs\\tutorials\\17-coop.md; the tests
ff9mapkit\\tests\\test_coop_guest_menu.py, _bench.py, _duo.py, _runners.py and the touched test_harness_netsync.py, test_coop_world_walk.py,
test_coop_world_walk_b.py, test_coop_field_swap_timing_bench.py, test_coop_world_follow.py, test_health.py, test_coop.py. \`git -C ${WT} diff HEAD\` and
\`git -C ${WT} status\` show the whole delta. The s167 template round: studies\\world-coop\\s167\\.
RULES: Never launch the game, deploy, run a bench or the in-game harness, or build the engine. Never edit the engine clone, memoria-patches/, or another
worktree. Never start a netsync HOST role or listen on Any in a test (client vs a loopback listener only). Keep each file's line endings (check first: the
*.py files here are CRLF, *.sh are LF). No PowerShell text round trips. Write backslash-heavy content with the Edit/Write tools, not bash heredocs (they
collapse backslashes). The harness protocol stays 5. Never weaken a row; re-key it by stage. Pytest runs from ${WT}\\ff9mapkit, with
FF9_S168_CLONE=C:/gd/FFIX/Memoria/Assembly-CSharp to exercise the clone pins (about 13 tests skip without it). NEVER wrap \`py -m pytest -n N\` in bash
\`timeout\` (it orphans the xdist workers). For any run over about 2 minutes use run_in_background and wait with Monitor on its log, never sleep chains. A
timing red is re-run alone before you call it: the stand-in has wall-clock windows, and load reddens them.
`
const FINDINGS = { type: 'object', properties: {
  lens: { type: 'string' },
  coverage: { type: 'string', description: 'what you checked and found sound, with counts (rows mapped, twins compared, files diffed)' },
  findings: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string', description: 'short unique id, e.g. L2-3' },
    title: { type: 'string' },
    severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] },
    files: { type: 'array', items: { type: 'string' } },
    evidence: { type: 'string', description: 'file:line on both sides, quotes, commands run and their output' },
    why_it_matters: { type: 'string' },
    proposed_fix: { type: 'string', description: 'the exact change; kit/scenario/runner/test side only' } },
    required: ['id', 'title', 'severity', 'files', 'evidence', 'why_it_matters', 'proposed_fix'] } } },
  required: ['lens', 'coverage', 'findings'] }
const VERDICTS = { type: 'object', properties: {
  verdicts: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, real: { type: 'boolean' }, confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    evidence: { type: 'string', description: 'your own checks and their output' },
    fix: { type: 'string', description: 'the confirmed or refined exact change (empty when not real)' } },
    required: ['id', 'real', 'confidence', 'evidence', 'fix'] } } },
  required: ['verdicts'] }
const FIX = { type: 'object', properties: {
  summary: { type: 'string' },
  fixed: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, files: { type: 'array', items: { type: 'string' } },
    what: { type: 'string' }, can_fail_proof: { type: 'string', description: 'the break-it check: what you broke, the red, the byte-exact restore' } },
    required: ['id', 'files', 'what', 'can_fail_proof'] } },
  skipped: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, why: { type: 'string' } }, required: ['id', 'why'] } },
  files_touched: { type: 'array', items: { type: 'string' } },
  tests_run: { type: 'string', description: 'commands, wall times, counts' },
  open_issues: { type: 'array', items: { type: 'string' } } },
  required: ['summary', 'fixed', 'skipped', 'files_touched', 'tests_run', 'open_issues'] }
const REC = { type: 'object', properties: {
  summary: { type: 'string' },
  reread: { type: 'string', description: 'what you re-read against the clone and the result' },
  tests_run: { type: 'string', description: 'the exact commands, wall times, per-file counts, skips and why' },
  reds: { type: 'array', items: { type: 'object', properties: { test: { type: 'string' }, cause: { type: 'string' }, resolution: { type: 'string' } },
    required: ['test', 'cause', 'resolution'] } },
  files_touched: { type: 'array', items: { type: 'string' } },
  open_issues: { type: 'array', items: { type: 'string' } } },
  required: ['summary', 'reread', 'tests_run', 'reds', 'files_touched', 'open_issues'] }

const READONLY = `YOU ARE READ-ONLY: edit no file (scratch files under ${SP}\\crit\\ only). Propose fixes; a later step applies the confirmed ones.
Do not run pytest with -n unless your step says so; targeted single tests (-k, no -n) are fine. Report a finding only with evidence you produced yourself.`

const LENSES = [
  { key: 'coverage', model: 'sonnet', prompt: `YOUR LENS: (a) ROW COVERAGE and (e) SELFTEST CLAIMS.
(a) Build the full table: every GM0 row the design's bench table names for s168 (expand each -x family to the members the design lists) -> where it lives:
the solo scenario's row id, the duo scenario's row id, an offline test (its name), explicitly deferred (where the deferral is written, and its reason), or
MISSING. Do the reverse too: any scenario row id the design never names is an invented row unless the As-built section or a builder report records it.
The routes the runners list as 'not in any runner' (GM0-LOAD, GM0-DEATH, GM0-CUT-NOBOOT, GM0-CUT-QUIT, GM0-QUIT-D, the RAMP press legs, GM0-OVERLAY's
shot-only evidence) must be recorded as known gaps with a reason in the design, a scenario docstring or the runner headers; say where, or that it is missing.
(e) Decision 35: the forced selftest role proves the ACTION only. Every S row must be labelled that way, and its judge must never claim the key path for a
mirroring guest or a real close trigger. Check each S judge's words and what it reads. Also check each D row really runs on two instances (duo.py) and
each T row on a tape or T2 route, never quietly on the selftest role.
Put the full row table in coverage (compact: one row per line).` },
  { key: 'falsifiable', model: 'opus', prompt: `YOUR LENS: (b) EVERY NEW ROW CAN GO RED. A check that cannot fail is a defect.
For each row in coop_guest_menu.py and coop_guest_menu_duo.py, name what turns it red (an engine lever, the \`netsync guestmenu\` sub-verb op of decision 31;
a stand-in FAULT in fakegame's GUEST_MENU_FAULTS; OLD on the s167 stand-in; or a pure-judge negative), and check the wiring end to end:
(1) every fault in GUEST_MENU_FAULTS is read by the guestmenu rung's code, and a test asserts it turns exactly its rows red. The dead critic was checking
cut_ignored, scene_ignored, pause_closed, unmirrored_open, stall_open, dialog_drop_lifted, slot_keyed, leave_ignored and title_ignored for this.
(2) every judge_* and *_measured function in both scenarios is called by its leg and has a negative test. The dead critic found judge_keyitem called by
no test (bench=0, duo=0): find out whether any leg calls it at all.
(3) every lever the scenarios send is one the engine accepts, with the exact op words and arguments (the clone's netsync guestmenu op parser and usage
line in Memoria\\Harness\\HarnessAgent.cs and Memoria\\NetSync\\NetSyncGuestMenu.cs).
(4) the kit builder's open issue: \`frame <marker>\` copies the guest's own key items and rare_item_used with no key-item marker, so \`restore skip keyitems\`
over a plain marker frame reads fp EQUAL, and GM0-RESTORE's keyitems mutant leg cannot go red (only \`frame witness keyitem\` makes it falsifiable).
Confirm against the C# and the scenario, and propose the fix.
(5) judges that pass on a weaker sample than the design's row demands (e.g. 'on 1 of N samples' where the row says the state holds), or that accept 'not
reached' as green, or whose CAL row could pass with an unexpected red missing.` },
  { key: 'twins', model: 'opus', prompt: `YOUR LENS: (c) EVERY KIT TWIN MATCHES THE C#. Re-read the C# yourself; do not trust the twins' comments.
Compare every s168 twin and constant: battlewire.py's s168 section (the caps word and bits incl. OwnCapsRule's two arguments and CapGuestMenu; section 12's
byte layout and its pure readers; the witness components; the close-trigger ids and causes; the guest-menu why codes and verdict names incl.
MenuKeyGuestOpen 5 and MenuKeyGuestQuiet 6 read 'guest'; the line words: the refusal line, the forced-close line per cause, the chip; the fingerprint
component names and fold; the press-deadline rule; CutMemoryRule, PairOnRule, NotPairedLineRule, the close-line rule; the netsync.guestmenu key list and
order as HarnessAgent.cs emits it (decision 32, incl. outside_settled, uid0_vars, sysvar192); the unknown-sub-verb catch literal; the lever usage line);
fakegame's guestmenu rung constants and rule copies; coop_peer.py's section-12 decoder and b3 caps adoption vs the C# encoder (section 12's writer,
TrailReserve) and the caps handshake. Also the s167 rows the kit re-keyed (ww_own_caps_rule, ww_own_caps_by_stage) vs NetSyncWorldWalk.OwnCapsRule; whether
the \`old\` lever changes the caps word; and the stand-in's timing constants (StaleMs, the ghost grace, the line's 4 s life, PIN_MAX_AGE_MS, the press
deadline) vs the C#. Note where existing pin tests already pin a twin to the source and where nothing does.
Put a compact table in coverage: twin, python file:line, C# file:line, MATCH/MISMATCH, pinned-by-test yes/no.` },
  { key: 'rekeys-runners', model: 'opus', prompt: `YOUR LENS: (d) REGRESSION RE-KEYS, (f) RUNNERS, (g) TEXTS.
(d) For every changed regression file (\`git diff HEAD\` on the scenario and test files the kit and regr steps re-keyed), check each change is BY STAGE and
weakens nothing. An assertion loosened for every stage, a row removed, a tolerance widened, a skip added, or a want made optional is a defect unless it is
stage-gated. Covers PR-SAVEMENU (press.now gains 'guest' only when netsync.guestmenu is present), MENU_PRE_OK, _coop_peer_bench.STAGE_KEYS (the s168 key
and its ordering against engine_stage), the caps by stage (0x0B on s168, 0x03 under guestmenu caps off, 0x01 under fp off), and menu_refusal.now's change
to 'audible'. New netsync keys were appended (guestmenu, outside_settled, uid0_vars, sysvar192): find every regression-set judge that reads key ORDER or
'the last key' and say whether it breaks on s168. coop_cut_hold.py's s121 leg must be untouched (it IS the older-peer fallback row).
(f) The runners: they never deploy, build, or copy a DLL, and never run under a test suite (benchguard: a live pytest or the gate lock refuses). Each checks
FF9 is closed and the owner's bridge is down for T2, and pins the DLL per stage: OLD on 12be3220520813a6 (the live s167 x64 DLL), the bracket legs on
532486364ec05354, NEW on the s168 build, which is neither. Each has a cutoff before the 03:45-06:15 gate window, keeps duo ports clear of the excluded range,
and runs the complete regression set (round B's legs, the diorama legs B3-B5, coop_stock_menu, s164's Pause MENU legs, coop_cut_hold's s121 leg). Every
harness API the scenarios and runners call must exist with that signature: duo.py (topology, bridges, bridge ports), Session.soft_reset, play.py flags, and
the instance helpers. A wrong call crashes only in game, and the stand-in may mask it.
(g) health.NETSYNC_GENERATIONS' s168 marker is a literal the clone really contains (grep it), and the texts (coop.py GUEST_TERMS, coopdoc, 17-coop.md) sit
behind the caps condition ('when both builds have it').` },
  { key: 'reds', model: 'opus', prompt: `YOUR LENS: (h) THE KNOWN RED and (i) THE UNRE-RUN FILE. You MAY run pytest here, as stated below.
(h) The dead critic ran \`py -m pytest tests/test_coop_guest_menu_bench.py tests/test_coop_guest_menu_duo.py -n 6\`: 1 failed, 107 passed (422 s). The failure:
test_coop_guest_menu_duo.py::test_the_stand_in_legs_are_green_but_their_unmodelled_rows, AssertionError ('stall', {'GM0-PAIRED-LINE-LOST': "count +1, why
'link', seated False, 'guest_menu' on 1 of 10"}). The row is pinned in STANDIN_UNMODELLED (it must read red on the stand-in, which does not model the stall's
peer-lost line), but it read GREEN. The duo builder's last edit before it reported was 'the PAIRED-LINE-LOST press at StaleMs+500', and it never re-ran the file
after that. Find the root cause. Is the judge too lenient (passing on 1 of 10 samples, where decision 10 / CR-2 says the peer-lost connecting line outranks
state 29)? Did the stand-in start to model the line? Is the unmodelled pin stale? Or is it timing? Reproduce by running that test alone (-k, no -n) two or
three times. Read the stand-in's overlay code (fakegame's _gm_live_followed and its overlay choice) and the C# chain (NetSyncClient.cs: NotPairedLineRule's
call site, the overlay chain around state 29, what peer_alive publishes). Decide what the row SHOULD measure on a real duo, and whether the judge does that.
(i) test_coop_guest_menu_duo.py was never fully re-run after the duo builder's last edits (the T2-PEER prediction, GM0-FREEZE-D, GM0-RAMP-WORLD-D, the pair
and local judge test, set_netsync timeout=1.0, the frozen-guest readiness fallback, the PAIRED-LINE-LOST press). Run it ALONE once, in the background:
\`py -m pytest tests/test_coop_guest_menu_duo.py -q -p no:cacheprovider -n 6\` with FF9_S168_CLONE set (about 4-7 min). List every red with its cause; re-run
each red alone once before you call it.
(j) The duo builder's unfinished one-time pass over the co-op module set showed 3 unnamed failures at about 59-66% (its log was cut at 73%). Do not re-run
that set (the reconcile does). If your runs or your reading point at them, say so.
Do not apply fixes; give each one as an exact diff in proposed_fix.` },
]

phase('Critic')
const lensResults = await pipeline(LENSES,
  (L) => agent(`${CONTEXT}\n${READONLY}\n${L.prompt}\nReturn the FINDINGS schema (lens = '${L.key}').`,
    { label: `critic: ${L.key}`, phase: 'Critic', schema: FINDINGS, model: L.model }),
  (res, L) => {
    if (!res || !res.findings || res.findings.length === 0) return { lens: L.key, res, verdicts: [] }
    return agent(`${CONTEXT}
YOU ARE AN ADVERSARIAL VERIFIER for the '${L.key}' critic's findings below. For EACH finding, try to REFUTE it: re-read the cited code yourself (the cited
lines and their surroundings, both the Python and the C#), and run the cheapest decisive check (a grep, a python one-liner, a single targeted pytest -k
without -n). real=true only when your own evidence confirms it. Default to real=false when you cannot reproduce it, or when the design, the As-built
section, or a builder report already records it as a deliberate, stage-gated choice or a known limit. For a real finding, check that the proposed fix is
right and complete (it keeps line endings, never weakens a row, keeps the harness protocol at 5) and give the exact change in 'fix'. Edit no file
(scratch only under ${SP}\\crit\\).
The critic's coverage note: ${String(res.coverage).slice(0, 4000)}
FINDINGS: ${JSON.stringify(res.findings).slice(0, 40000)}
Return the VERDICTS schema, one verdict per finding id.`,
      { label: `verify: ${L.key}`, phase: 'Verify', schema: VERDICTS, model: 'opus' })
      .then(v => ({ lens: L.key, res, verdicts: (v && v.verdicts) || null }))
  })

const confirmed = []
const unverified = []
for (const r of lensResults.filter(Boolean)) {
  if (!r.res) { log(`lens ${r.lens}: the critic returned nothing`); continue }
  if (r.verdicts === null) { log(`lens ${r.lens}: the verifier returned nothing; its ${r.res.findings.length} findings stay unverified`); unverified.push(...r.res.findings); continue }
  const byId = new Map(r.verdicts.map(v => [v.id, v]))
  for (const f of r.res.findings) {
    const v = byId.get(f.id)
    if (v && v.real) confirmed.push({ ...f, lens: r.lens, verify: { confidence: v.confidence, evidence: v.evidence, fix: v.fix } })
  }
  log(`lens ${r.lens}: ${r.res.findings.length} findings, ${r.verdicts.filter(v => v.real).length} confirmed`)
}
const sev = { blocker: 0, major: 1, minor: 2, nit: 3 }
confirmed.sort((a, b) => (sev[a.severity] ?? 9) - (sev[b.severity] ?? 9))

let fix = null
if (confirmed.length) {
  phase('Fix')
  const payload = JSON.stringify(confirmed)
  if (payload.length > 90000) log(`confirmed findings payload is ${payload.length} chars; passing the first 90000 (the rest are in the run result)`)
  fix = await agent(`${CONTEXT}
YOUR STEP: THE FIXER. Below are the critic findings that an independent adversarial verifier CONFIRMED, most severe first, each with the verifier's
evidence and its exact fix. Apply each one in the worktree: kit, scenarios, runners and tests only, plus a factual correction of S168-DESIGN.md only where
a finding is about the doc. Never the engine, never memoria-patches/. If a confirmed fix turns out wrong when you apply it, skip it and say why; do not
redesign. For every fix that adds or tightens a check, PROVE IT CAN FAIL: break the code under test, watch the test go red, restore it byte for byte (check
the sha), and report it in can_fail_proof. After the fixes, run every test file you touched: targeted runs first, then each touched file once (the slow
stand-in files -- test_coop_guest_menu_bench.py about 5 min and test_coop_guest_menu_duo.py about 4-7 min at -n 6 -- in the background, one pytest at a
time). Do not run the whole domain set; the reconcile does that. Do not commit.
CONFIRMED: ${payload.slice(0, 90000)}
Return the FIX schema.`, { label: 'fixer', phase: 'Fix', schema: FIX, model: 'opus' })
} else {
  log('no confirmed findings: the fixer is skipped')
}

phase('Reconcile')
const rec = await agent(`${CONTEXT}
YOUR STEP: THE RECONCILE. Fixer report: ${JSON.stringify(fix ? { summary: fix.summary, fixed: fix.fixed.map(f => ({ id: f.id, files: f.files, what: f.what })), skipped: fix.skipped, open: fix.open_issues, tests: fix.tests_run } : 'no fixer ran').slice(0, 20000)}
(1) Re-read the final kit against the engine clone once more: constants, key names and order, op names, usage strings, the catch literal. Focus first on
whatever the fixer changed.
(2) Run the co-op W2 domain test set ONCE in this worktree, from ${WT}\\ff9mapkit, in the background with FF9_S168_CLONE=C:/gd/FFIX/Memoria/Assembly-CSharp:
\`py -m pytest -q -p no:cacheprovider -n 6 tests/test_coop_guest_menu.py tests/test_coop_guest_menu_bench.py tests/test_coop_guest_menu_duo.py
tests/test_coop_guest_menu_runners.py tests/test_harness_netsync.py tests/test_coop_peer.py tests/test_coop_world_walk*.py
tests/test_coop_field_swap_timing_bench.py tests/test_coop_world_follow.py tests/test_world_coop_harness.py tests/test_health.py tests/test_coop.py
tests/test_coop_tab.py tests/test_coop_leader_guard.py tests/test_coop_world_battle.py tests/test_coop_world_wait.py tests/test_world_diorama_harness.py
tests/test_harness_duo.py\` (expand the glob in bash; drop any name that does not exist and say so). Log to ${SP}\\crit\\reconcile.log with -rfEs so every
skip and red is named. Wait with Monitor; do not chain sleeps. It may take an hour or more. Confirm the clone pins RAN, not skipped.
(3) Re-run every red ALONE once. A red that is green alone is timing noise: report it as such. Any red the kit caused, fix it (kit side only), re-run that
file, and report. A red that predates the s168 delta (check with \`git stash\`? NO -- never stash; instead compare against the s167 tree with a
read-only \`git -C ${WT} show HEAD:<path>\` reading, or reason from the diff) is reported, not fixed.
Do NOT commit, deploy or launch the game. Return the REC schema.`, { label: 'reconcile', phase: 'Reconcile', schema: REC, model: 'opus' })

return {
  lenses: lensResults.filter(Boolean).map(r => ({ lens: r.lens, coverage: r.res && r.res.coverage, findings: r.res && r.res.findings, verdicts: r.verdicts })),
  confirmed, unverified, fix, rec,
}
