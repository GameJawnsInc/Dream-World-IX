export const meta = {
  name: 's168-w1-review',
  description: 'Adversarial review of the whole s168 engine delta (4 lenses + a completeness critic), verification, and a fix pass in the clone (no-deploy)',
  phases: [{ title: 'Review' }, { title: 'Critic' }, { title: 'Verify' }, { title: 'Fix' }],
}
const WT = String.raw`C:\gd\Dream-World-IX\.claude\worktrees\s166-handoff-575aeb`
const SP = String.raw`C:\Users\skaki\AppData\Local\Temp\claude\9e463cf4f0985362\110b1b95-e2da-4a85-ab88-e0d8756cb21a\scratchpad`
const CLONE = String.raw`C:\gd\FFIX\Memoria`
const CTX = `
Co-op ("netsync") round s168 for the FF9 Memoria engine: the co-op GUEST's stock main menu, rung 0 (view-only), over a seated copy of the host's party.
THE SPEC: ${WT}\\studies\\field-coop\\S168-DESIGN.md (binding; incl. "Cut in round 3": those mechanisms must NOT exist). THE BUILD: the shared clone ${CLONE}\\Assembly-CSharp,
built with --no-deploy only (live DLL = s167, untouched). The whole s168 delta: \`py ${WT}\\studies\\field-coop\\s168\\s168diff.py --stat\` and \`... <path rel to
Assembly-CSharp>\` (vs the s167 snapshot ${SP}\\s167base). The builders' reports (contracts, deviations, open issues): ${SP}\\s168_w1p1.json (keys ab, core, harn, wire)
and ${SP}\\s168_w1p2.json (keys e, f, g, h, i). Offline proofs: ${SP}\\s168proof (subfolders per step; the latest is the W1i one): guest menu 408 rows / 241
mutants, seat bracket 19/7, world walk 534/198. The tree is DECOMPILED: caller-grep before trusting any function; trace call sites, not definitions ("a law in
a docstring is a wish"). Read-only unless told otherwise: EDIT NOTHING in the review/critic/verify stages.`
const FIND = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] }, file: { type: 'string' }, line: { type: 'integer' },
  claim: { type: 'string' }, evidence: { type: 'string', description: 'file:line traces in the clone' }, scenario: { type: 'string', description: 'concrete steps -> wrong outcome' },
  fix: { type: 'string' } }, required: ['id', 'severity', 'file', 'claim', 'evidence', 'scenario', 'fix'] } }, summary: { type: 'string' } }, required: ['findings', 'summary'] }

phase('Review')
const LENSES = [
  { key: 'vanilla', prompt: `LENS: VANILLA AND HOST SAFETY. Every hunk in a STOCK file (UIKeyTrigger.cs, UIManager.cs, MainMenuUI.cs, EquipUI.cs, AbilityUI.cs, ItemUI.cs,
SceneDirector.cs, JsonParser.cs, EventEngine.cs, AchievementManager.cs) and every netsync hunk that runs on a non-guest path (NetSyncParty, NetSyncVisitor,
NetSyncDiorama's extract, NetSyncClient's Update order, BuildStateFrame, the close tick before the enabled gate): prove that with co-op OFF, for the HOST, for an
unfollowed client, and for a following guest NOT in a guest-menu seat, behaviour is byte-identical to s167 (the s167base snapshot) -- same branches, same writes,
same logs, no new exception path, no per-frame allocation. Pay special attention to: the door in ChangeUIState (its try, its reads on every state change), the
close tick placed before the enabled gate (does it read anything or allocate on vanilla?), the diorama bracket/builder extract (behaviour-neutral? the battle
co-op lane is two-PC proven), the host-side section 12 send (only to a live b3 following guest?), the caps word change and its effect on s166/s167 peers.` },
  { key: 'save', prompt: `LENS: THE SEAT, THE RESTORE AND SAVE SAFETY. The host's save must never be written by anything the guest does; the guest's own data must come
back exactly. Trace: the seat (one fresh frame, pure readers, the witness, BuildSeatMembers with overrides+rethrow, all-or-nothing with its fault path, seat by
reference, the menu's own bracket instance), every restore path (the one door, the identity rule + load epoch, the Replace / ramp-fire / load-entry backstops,
the session's clear points), and what runs while seated (SetMasterSkill skip, AchievementManager hold, the autosave seat term, LiveSlotChars, the diorama Boot
refusal, the census hooks). Find any path where (a) a scratch PLAYER/bag/rare set/gil stays installed after the menu is gone, (b) the guest's real objects are
written while seated, (c) a save (autosave, manual, ramp autoload, pairing autosave) can capture seated data, (d) the diorama could snapshot the menu's scratches,
(e) a restore lands on a deserialized state, (f) a throw leaves a half seat.` },
  { key: 'wire', prompt: `LENS: THE WIRE, THE LEVERS AND THE HARNESS. Check the section-12 codec against decision 5's byte layout (both ends, bounds, clamps, a hostile or
truncated block, trailing bytes), the pure readers, the send rule and the frame-cap guard (TrailReserve vs the real section 7/8 maxima), the caps word (0x0B,
0x03 under caps off, 0x01 under fp off) and every peer combination (s166, s167, s168, caps off), the FeatureOn + liveness gates. Then lever parity: 'guestmenu old'
must make every s121 read s121 exactly (keys, count, log line, verdict names) INCLUDING for the unmirrored guest; every lever/op in decision 31 exists, is released
by HarnessReleaseGuestMenu on disarm/fault/reset, appears in the 'lever' key, and has its sentinel in AppendNetsync's catch literal (parse that literal as JSON);
'netsync.guestmenu' fields match decision 32; the harness protocol stays 5; the proof rows can each fail (a mutant per rule; spot-check that mutants are caught by
the row they name, and that no row is tautological).` },
  { key: 'closes', prompt: `LENS: THE FORCED CLOSES AND THE LIFECYCLE. Walk the guest-menu session through every event (the press, the door pass/fail/fault, each close
trigger: leave, out, rejoin, world, cut, ending, title, scene; the guest's Cancel at each depth incl. item target picker, equip candidate list, ability target,
the quit confirm (Alt+F4) and its cancel; OnLevelWasLoaded; Replace real/dropped; a soft reset; the ramp's arm and fire on both branches with the press deadline
and the world seat term; co-op switched off / role change; link loss; a throw at each step; the watchdog; a second press during the HUD hide). Verify in the
CODE that every path ends with the HUD shown, events and control on, the seat restored or dropped, the session/watchdog/close record cleared, EnabledSubMenus
cleared, the chip gone, held keys written into ETb.sKey before the HUD route, and the battle-cut report BOOTING (or BUSY while the quit prompt holds the close).
Check CoopCloseGuestMenuIfDue is asked FIRST at each waiting site the spec lists (a close behind an earlier quiet wait never runs), and that the close tick
never throws out of NetSyncClient.Update.` },
]
const reviews = await parallel(LENSES.map(l => () => agent(`${CTX}\n\n${l.prompt}\nReport only real defects with a concrete scenario; severity blocker = can
corrupt a save or break vanilla/host play, major = wrong behaviour or a strand/leak, minor = small/latent, nit = wording. Return the schema.`,
  { label: `review:${l.key}`, phase: 'Review', schema: FIND, model: 'opus' }).then(r => r ? { lens: l.key, ...r } : null)))
const ok = reviews.filter(Boolean)

phase('Critic')
const digest = ok.map(r => `## ${r.lens}: ${r.summary}\n` + r.findings.map(f => `- ${f.id} [${f.severity}] ${f.file}:${f.line || ''} ${f.claim}`).join('\n')).join('\n\n')
const critic = await agent(`${CTX}\n\nFour reviewers covered vanilla/host safety, the seat/save, the wire/levers/harness and the closes/lifecycle. Their findings:\n${digest}\n\nYou are
the COMPLETENESS CRITIC: what did they MISS? A hunk nobody read (walk s168diff.py --stat and check every file got a lens), a spec decision with no code (or code for a
CUT mechanism), a decision-32 key or decision-31 op missing, an s167 behaviour changed without a lever, a builder deviation (in the two JSON reports) that is
actually wrong. Verify each in the clone before reporting. Return the schema; ids CR-n.`, { label: 'critic', phase: 'Critic', schema: FIND, model: 'opus' })
const all = ok.concat(critic ? [{ lens: 'critic', ...critic }] : [])

phase('Verify')
const VER = { type: 'object', properties: { verdicts: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, real: { type: 'boolean' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] }, evidence: { type: 'string' }, fix: { type: 'string' } },
  required: ['id', 'real', 'severity', 'evidence'] } } }, required: ['verdicts'] }
const halves = [all.filter((_, k) => k % 2 === 0), all.filter((_, k) => k % 2 === 1)]
const verified = await parallel(halves.filter(h => h.some(r => r.findings.length)).map((h, n) => () => agent(`${CTX}\n\nAdversarially VERIFY these findings. For EACH,
try to REFUTE it by tracing the code paths in the clone: is the scenario reachable, does the code really do what the finding says? real=false if refuted or
unreachable; real=true with the corrected severity and the exact fix otherwise. Default to refuted when the evidence does not hold.\n${JSON.stringify(h.map(r => ({ lens: r.lens, findings: r.findings })))}`,
  { label: `verify:${n}`, phase: 'Verify', schema: VER, model: 'opus' }).then(v => v ? h.flatMap(r => r.findings.map(f => ({ ...f, lens: r.lens, verdict: v.verdicts.find(x => x.id === f.id) || null }))) : null)))
const flat = verified.filter(Boolean).flat()
const real = flat.filter(f => f.verdict && f.verdict.real && f.verdict.severity !== 'nit')
log(`${flat.length} findings; ${real.length} real (blocker ${real.filter(f => f.verdict.severity === 'blocker').length}, major ${real.filter(f => f.verdict.severity === 'major').length})`)

phase('Fix')
const FIXR = { type: 'object', properties: { results: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, status: { type: 'string', enum: ['fixed', 'skipped'] }, note: { type: 'string' } }, required: ['id', 'status', 'note'] } },
  compile_ok: { type: 'boolean' }, compile_tail: { type: 'string' }, proof: { type: 'string' }, summary: { type: 'string' } }, required: ['results', 'compile_ok', 'compile_tail', 'proof', 'summary'] }
let fix = null
if (real.length) fix = await agent(`${CTX}

YOU MAY NOW EDIT THE CLONE (only the clone's Assembly-CSharp files; never memoria-patches/, studies/, Python, the game install). Fix these VERIFIED findings, each
the smallest correct change that keeps the spec, tagged \`[ff9mapkit netsync s168]\` in every hunk, line endings and BOM kept (Edit tool or Python bytes I/O, never
PowerShell text), adding a proof row + mutant where a rule changes. Compile ONLY with \`py tools/build_memoria.py --no-deploy\` run from ${WT}; never deploy, never
launch the game. Re-run every offline proof (extend the latest ${SP}\\s168proof subfolder's build; offline exes never construct NetSyncSocket(true, ...) or listen)
and report exact N/M for guest menu, seat bracket and world walk. Return one result per id.\n${JSON.stringify(real.map(f => ({ id: f.id, lens: f.lens, severity: f.verdict.severity,
file: f.file, line: f.line, claim: f.claim, scenario: f.scenario, fix: f.verdict.fix || f.fix })))}`, { label: 'fixer', phase: 'Fix', schema: FIXR, model: 'opus' })
return { counts: { findings: flat.length, real: real.length }, real: real.map(f => ({ id: f.id, lens: f.lens, severity: f.verdict.severity, claim: f.claim })),
  refuted: flat.filter(f => !(f.verdict && f.verdict.real)).map(f => ({ id: f.id, lens: f.lens, claim: f.claim.slice(0, 200) })), fix }
