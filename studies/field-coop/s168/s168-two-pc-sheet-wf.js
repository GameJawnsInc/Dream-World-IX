export const meta = {
  name: 's168-two-pc-sheet',
  description: 'Draft and fact-check the combined s167+s168 two-PC sheet and its read-only check script (no tests, no launches: a bench is running)',
  phases: [
    { title: 'Ground', detail: 's167 carry, s168 steps, package plan + check script, risks' },
    { title: 'Draft', detail: 'TWO-PC-CHECKS-S168.md' },
    { title: 'Fact-check', detail: 'engine words, package/install, owner walk-through; each verified' },
    { title: 'Fix', detail: 'apply confirmed fixes' },
  ],
}

const WT = 'C:/gd/Dream-World-IX/.claude/worktrees/sweet-kare-2581e5'
const CLONE = 'C:/gd/FFIX/Memoria/Assembly-CSharp'
const PKG167 = 'C:/Users/skaki/Desktop/FF9Coop-laptop-update-20261106-s167'
const SHEET = `${WT}/studies/field-coop/TWO-PC-CHECKS-S168.md`
const SCRIPT = `${WT}/studies/field-coop/s168/check-s168.ps1`

const RULES = `HARD RULES -- a live FF9 game bench is running on this machine RIGHT NOW (the s168 OLD calibration on the live s167):
- Read freely. Write ONLY the file(s) this task names. Never run pytest, tools/play.py, tools/harness/duo.py, tools/build_memoria.py,
  any deploy, or anything that launches FF9 or loads the CPU or disk (no bulk hashing of game or mod folders, no test runs).
- Never edit the engine clone ${CLONE} (its working tree IS the s168 engine: read it freely), memoria-patches/, the live install
  (C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX), the Desktop packages (read freely) or any other worktree.
- Never git commit, stash or checkout. Never start a netsync host role or listen on any port.
- The worktree is ${WT} (== master a10cfb9b: the s168 kit is merged). Paths in docs are repo-relative.
CONTEXT: s167 (the co-op guest walks the world map on its own copy) is deployed live (Assembly-CSharp.dll sha16 12be3220520813a6) and
benched on one PC; its two-PC session (studies/world-coop/TWO-PC-CHECKS-S167.md, the package ${PKG167}) has NOT been run yet. s168
(the guest's main menu, view only: studies/field-coop/S168-DESIGN.md) is built in the clone, its kit and one-PC bench merged; it will be
deployed after tonight's one-PC benches. THE OWNER WILL TEST BOTH IN ONE TWO-PC SESSION on the s168 build (s168 contains s167
unchanged): the desktop hosts, the laptop is the guest. This workflow writes that session's checklist (it becomes the laptop
package's README) and its read-only check script. The s168 DLL's sha is not known yet: write the placeholders <S168_SHA16> and
<S168_SHA256> wherever it is needed. Owner style: plain words, numbered steps, what to look for, no emoji, no codenames in titles.`

const GROUND = {
  type: 'object',
  properties: {
    report: { type: 'string', description: 'the full grounded report, markdown-ready' },
    citations: { type: 'array', items: { type: 'string' }, description: 'file:line for every literal or behaviour claimed' },
  },
  required: ['report', 'citations'],
}

const TASKS = [
  {
    key: 's167-carry', model: 'opus',
    prompt: `${RULES}

YOUR TASK -- carry the s167 two-PC checks onto an s168 build.
Read studies/world-coop/TWO-PC-CHECKS-S167.md in full (it is also ${PKG167}/README.md), studies/world-coop/S167-HANDOFF.md,
studies/world-coop/S166-DESIGN.md's Known limits (Round B), and the s168 design studies/field-coop/S168-DESIGN.md (decisions,
"The owner-visible words", "As built (s168 W1)", "As built (s168 W2)"). Ground every claim in the s168 engine source:
${CLONE}/Memoria/Netsync/*.cs (NetSyncClient.cs, NetSyncWorldWalk.cs, NetSyncGuestMenu.cs, NetSyncSeatBracket.cs, NetSyncState.cs,
HarnessAgent.cs ...) and the stock files s168 touched (UIManager, MainMenuUI, EventEngine, ...: grep the tag "[ff9mapkit netsync s168]").
For EVERY step and every expected observation of the s167 sheet (Step 0's install and line-up, steps 1-14, The look, The words,
Known limits, What to send back), decide on an s168 build:
- stands as is; or
- changes: the exact new expectation (quote format strings / literals with file:line). Things that certainly need checking: every
  proof/selftest log line printed at startup (world walk 532/196 -> 534/198 on s168; the new guest-menu 420/249 and seat-bracket 19/7
  proof lines; the main menu refusal selftest), the caps word (0x0003 -> 0x000B; under which levers), the wire line, the fingerprint
  lines, every place the s167 sheet expects a guest's Menu / Pause / save press to be refused, buzz or show a line (on s168 a
  following, mirroring guest's Menu opens the view-only main menu; check exactly when -- field, world on foot, riding, frozen,
  walking, not mirroring, during the link cut), the overlay lines (s168 adds state 29 "guest_menu" for a refused press), step 14's
  version check (s167's used the s166 DLL on the laptop; on s168 the "older build" is the s167 DLL: what each side then shows, from
  the caps / wire / refusal code);
- confounded by s168: steps whose failure could be s168's fault, so a failure must be bisected with the s167 DLL on both PCs.
Also return the exact startup and per-load log literals an s168 build prints that the owner should compare between the two logs.
Return a carry table (s167 step -> verdict -> new text) plus the literals, each with its citation.`,
  },
  {
    key: 's168-steps', model: 'opus',
    prompt: `${RULES}

YOUR TASK -- design the s168 half of the two-PC session: the steps a human on two real PCs can run, see and judge that the one-PC
bench cannot. Sources: studies/field-coop/S168-DESIGN.md in full (decisions 1-36, "The owner-visible words", "The bench" -- every row
whose harness is in-game-only or that names "the two-PC sheet" -- "Known limits (s168-s169)", "As built (s168 W1)", "As built (s168
W2)" incl. "Bench rows no leg reaches" and "Open"), the owner's calls at the end, the engine (${CLONE}/Memoria/Netsync/NetSyncGuestMenu.cs,
NetSyncSeatBracket.cs, NetSyncClient.cs, NetSyncState.cs and the stock files tagged "[ff9mapkit netsync s168]"), the tutorial bullet in
ff9mapkit/docs/tutorials/17-coop.md and GUEST_TERMS in ff9mapkit/ff9mapkit/workspace/coopdoc.py.
Produce an ORDERED list of owner-runnable steps (desktop hosts, laptop guest; keyboard or pad; the owner reads screens and each
Memoria.log), prioritised:
 1. The core: a following, mirroring guest on a field presses Menu -> the stock main menu over a copy of the host's party, the chip's
    exact words; browse every sub-screen it allows (items, key items, abilities, equipment, status, Folklore/Journal); which rows are
    greyed; a changing confirm buzzes and shows the refusal line (exact words, by why); item sort affects the guest's view only; Cancel
    closes and the guest's own party is back -- and how the owner can SEE that nothing changed on either side (concrete checks).
 2. Every forced close a human can trigger, each with its close line's exact words: the host leaves the field, starts a battle,
    starts a conversation / chest / ATE / scene, goes to the title, the session ends / the link is cut / Co-op is switched off.
 3. Refusals with their lines: before following (not mirroring), riding on the world map, the older build (the laptop on the s167
    DLL), the guest's save menus, any other why a human can reach.
 4. The world map menu on foot (walking and frozen guests on 9010/9011 if they differ).
 5. The routes the bench could not reach (GM0-LOAD's load path, GM0-DEATH, GM0-CUT-NOBOOT, GM0-CUT-QUIT / GM0-QUIT-D the quit prompt,
    the GM0-RAMP-FIELD / -WORLD press legs) -- include ONLY those a human can do safely, with exactly how; say which are skipped and why.
 6. The owner's calls on the look and the words (the design says the owner tunes them): list each word set to judge.
For each step: preconditions (which save, world map or field), exact actions, what each screen should show (exact words with file:line),
what each Memoria.log should show (exact literals), what to record. Flag anything that could hurt either save (the copy and its restore,
the session-end autosave reload) and the safe recovery. Return the steps markdown-ready plus citations.`,
  },
  {
    key: 'package', model: 'sonnet',
    prompt: `${RULES}

YOUR TASK -- plan the s168 laptop package and WRITE its read-only check script to ${SCRIPT} (the only file you write).
Model: the s167 package ${PKG167} (README.md, check-s167.ps1, HASHES.txt, DATA-WORLD-HASHES.txt, FOLDERS-MANIFEST.txt, dlls/x64|x86,
the three mod folders) and its record in studies/world-coop/S167-HANDOFF.md (the W3 row). Read tools/build_memoria.py and
tools/restore_memoria_dll.py (how the desktop backs up and reverts its DLLs, and the backup folder names).
The s168 package carries: dlls/x64|x86 = the six DLLs (only Assembly-CSharp.dll changes: <S168_SHA256>); dlls-s167/x64|x86 = the s167
Assembly-CSharp.dll (sha256 12be3220520813a6dd4bc365b38a1f257eefe7819552b4f290bcefc9b0464096) as a fallback to bisect an s167-step
failure and for the version check; the three mod folders; HASHES.txt (now listing both dll sets), DATA-WORLD-HASHES.txt,
FOLDERS-MANIFEST.txt; check-s168.ps1; README.md = the checklist.
Write check-s168.ps1: adapt check-s167.ps1 (same four sections, read-only, same OK/DIFFERS lines and exit codes) with s168 names, plus:
(a) a package-integrity section that hashes the package's own dlls/ and dlls-s167/ files against HASHES.txt; (b) a line that names
which engine this install has now, by the installed x64 Assembly-CSharp.dll's hash: "s168 (the package)", "s167 (the fallback)" or
"other <sha16>", where s167 is not a failure in itself but the summary must say the DLL check differs. PowerShell 5.1 compatible, ASCII
ONLY (PS 5.1 reads a BOM-less file as ANSI), CRLF line endings (write it so), no network, no writes. Do not run it against the real
install or a Desktop package; you may dry-run it against a tiny FAKE package + fake game folder you create under your own temp dir.
Also return, as text for the checklist: "Install on the laptop" / "Step 0" (back up, copy the DLLs, run the check on BOTH machines,
the Memoria.ini settings -- read the s167 README for them and say what is unchanged), and "Swap to s167 and back" (both machines, FF9
and the launcher closed: the laptop copies dlls-s167; the desktop the same or via restore_memoria_dll.py / the build's backup folder --
describe exactly what those tools do, and that a swap must be done on BOTH machines because a mixed pair is the version check).`,
  },
  {
    key: 'risks', model: 'sonnet',
    prompt: `${RULES}

YOUR TASK -- the session's safety net and its report-back list.
Read the earlier two-PC sheets' results and findings: studies/world-coop/TWO-PC-CHECKS-S165.md, TWO-PC-CHECKS-S166.md ("Results"),
TWO-PC-CHECKS-S167.md ("Known limits", "What to send back"), studies/world-coop/S166-HANDOFF.md, S167-HANDOFF.md, and
studies/field-coop/S168-DESIGN.md's "Known limits (s168-s169)" and "As built" Open items. Return:
1. Pre-flight: everything that went wrong or nearly wrong in past two-PC sessions (e.g. the laptop's mods line missing folders, the
   owner's bridge, controllers, overworld edits on the desktop before the session, save choice) and the check that prevents it now.
2. What could hurt a save or strand a player in THIS session (s167 world walk + s168 guest menu), and the recovery for each.
3. What to send back: which files (both Memoria.log, where they are), screenshots worth taking (which screens), the K1 reads or
   measurements S168-DESIGN.md asks for in game, the owner calls (the look, the words).
4. A short "if a step fails" triage: how the owner tells an s167 failure from an s168 one (the s167 DLL on both machines, redo the
   step), and what to note.
Markdown-ready, with citations.`,
  },
]

phase('Ground')
const ground = await parallel(TASKS.map(t => () =>
  agent(t.prompt, { label: `ground:${t.key}`, phase: 'Ground', schema: GROUND, model: t.model })
    .then(r => ({ key: t.key, ...r }))))
const G = ground.filter(Boolean)
log(`ground: ${G.length}/4 returned (${G.map(g => g.key).join(', ')})`)
const groundText = G.map(g => `===== GROUND: ${g.key} =====\n${g.report}\n-- citations --\n${(g.citations || []).join('\n')}`).join('\n\n')

phase('Draft')
const draft = await agent(`${RULES}

YOUR TASK -- WRITE the combined two-PC checklist to ${SHEET} (the only file you write; ${SCRIPT} was written by the package lane --
read it, do not edit it; if it is missing say so).
Below are four grounded reports. Build the sheet from them, keeping every literal and expectation they ground (copy the exact words;
do not paraphrase an on-screen string or a log line). Read studies/world-coop/TWO-PC-CHECKS-S167.md first and keep its voice, layout
and level of detail; the new sheet replaces it for this session (it carries s167's steps, adjusted).
Structure (adapt as the material needs):
- Title "FF9 Co-op: laptop update package (<DATE>, s168 with s167)" (literal <DATE> placeholder), a short intro: what this session
  tests (s167's world walk, never tested on two PCs, and s168's guest main menu), the order, roughly how long.
- What's new: s167 (the guest walks, short, from the s167 sheet) and s168 (the guest's main menu, view only).
- Install on the laptop / Step 0: back up, copy, check both machines (check-s168.ps1), Memoria.ini, the line-up in game (the literals
  each log must show, both logs compared).
- What to try, desktop hosts, laptop guest: Part A = s167's steps as carried (numbered A1..), Part B = s168's steps (B1..). Order the
  session so it flows (you may interleave field and world steps for efficiency, but every step keeps its id and its s167 or s168
  origin). Each step: preconditions, actions, what each screen shows, what each log shows, what to note.
- The version check (last): the laptop on the s167 DLL (from the package's dlls-s167), what both sides show, then back.
- If a step fails: the s167-DLL bisect on both machines, what to note.
- The look (your call) and The words (your call): s167's and s168's.
- Known limits: s167's (carried) and s168's (what the owner might hit and should not report as a bug).
- What to send back, then an empty "## Results" section.
Use <S168_SHA16> / <S168_SHA256> placeholders. ASCII punctuation is fine; no emoji; CRLF or LF either.
Return a summary of the sheet's structure, every place you had to choose between conflicting grounding, and every placeholder.

${groundText}`, { label: 'draft:sheet', phase: 'Draft', model: 'opus',
  schema: { type: 'object', properties: { summary: { type: 'string' }, choices: { type: 'array', items: { type: 'string' } }, placeholders: { type: 'array', items: { type: 'string' } } }, required: ['summary'] } })

const FINDINGS = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] },
      where: { type: 'string', description: 'file + section/step + quoted text' }, claim: { type: 'string' },
      evidence: { type: 'string', description: 'file:line and quoted source' }, fix: { type: 'string', description: 'exact replacement text' },
    }, required: ['id', 'severity', 'where', 'claim', 'evidence', 'fix'] } },
  },
  required: ['summary', 'findings'],
}
const VERDICT = {
  type: 'object',
  properties: {
    confirmed: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } }, required: ['id', 'evidence', 'fix'] } },
    refuted: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, why: { type: 'string' } }, required: ['id', 'why'] } },
  },
  required: ['confirmed', 'refuted'],
}

const LENSES = [
  { key: 'engine-words', model: 'opus', prompt: `Check EVERY quoted on-screen string, log line, number, key name and behaviour claim in ${SHEET} against the s168 engine
source in ${CLONE} (grep the literal; follow the code path that prints or decides it) and against S168-DESIGN.md / S166-DESIGN.md. A
claim that the engine does not make, a literal that differs by one character, a behaviour that holds only under a condition the step
does not set up, an s167 expectation the s168 delta changes -- each is a finding. Also check the sheet's "older build" expectations
against the caps / wire / refusal code.` },
  { key: 'package-install', model: 'opus', prompt: `Check the install, package and script side: every path, folder and file name in ${SHEET}'s install, Step 0, swap and
version-check steps; the Memoria.ini settings it names (against the s167 README in ${PKG167} and the engine's ini readers); the
consistency between the sheet and ${SCRIPT}; the script itself (PowerShell 5.1 compatibility, ASCII only, CRLF, strictly read-only,
the four s167 sections kept, the package-integrity section, the engine-identity line, exit codes; read it line by line). You MAY
dry-run the script against a tiny FAKE package + FAKE game folder you build under your own temp dir (never the real install or a
Desktop package) and report what it printed. Also check the desktop's revert story against tools/build_memoria.py and
tools/restore_memoria_dll.py.` },
  { key: 'walkthrough', model: 'opus', prompt: `Role-play the owner running ${SHEET} on two real PCs from the first line to Results, knowing only what the sheet says.
Find: missing preconditions (which save, which world map, which field, which party), steps a human cannot actually reach the way they
are written (e.g. is the guest really following and mirroring at that moment? is the host really able to start that scene there?),
ambiguous or overloaded wording, steps that leave the pair in a state the next step does not expect, recovery gaps, anything that risks
either save, order inefficiencies, and the total time. Cross-check each s168 step against S168-DESIGN.md's predicate (decision 8's
terms) so a step does not promise a menu where the predicate refuses it.` },
]

phase('Fact-check')
const checked = await pipeline(LENSES,
  l => agent(`${RULES}

YOUR TASK -- a READ-ONLY fact-check lens (${l.key}) on the drafted checklist. Edit nothing.
${l.prompt}
Return findings with exact replacement text. Severity: blocker = the owner would be misled into a wrong verdict or a save risk; major
= a step cannot be run as written or a literal is wrong; minor = unclear or incomplete; nit = wording.`,
    { label: `check:${l.key}`, phase: 'Fact-check', schema: FINDINGS, model: l.model }),
  (r, l) => {
    if (!r || !r.findings || r.findings.length === 0) return { lens: l.key, findings: [], verdict: { confirmed: [], refuted: [] }, summary: r ? r.summary : 'lens returned nothing' }
    return agent(`${RULES}

YOUR TASK -- adversarially VERIFY the ${l.key} lens's findings on ${SHEET}${l.key === 'package-install' ? ' and ' + SCRIPT : ''}. Edit nothing.
For each finding, try to REFUTE it from the sources (the engine in ${CLONE}, the design docs, the s167 package, the tools). Confirm only
what survives, and give the exact fix text to apply (correct the lens's fix if it is wrong). When unsure, refute.

FINDINGS:
${JSON.stringify(r.findings, null, 1)}`, { label: `verify:${l.key}`, phase: 'Fact-check', schema: VERDICT, model: 'opus' })
      .then(v => ({ lens: l.key, findings: r.findings, verdict: v || { confirmed: [], refuted: [] }, summary: r.summary }))
  })

const C = checked.filter(Boolean)
const confirmed = C.flatMap(c => (c.verdict.confirmed || []).map(v => {
  const f = (c.findings || []).find(x => x.id === v.id) || {}
  return { lens: c.lens, id: v.id, severity: f.severity, where: f.where, claim: f.claim, evidence: v.evidence, fix: v.fix }
}))
const SEV = { blocker: 0, major: 1, minor: 2, nit: 3 }
confirmed.sort((a, b) => (SEV[a.severity] ?? 4) - (SEV[b.severity] ?? 4))
log(`fact-check: ${C.map(c => `${c.lens} ${c.findings.length} found / ${(c.verdict.confirmed || []).length} confirmed`).join('; ')}`)

phase('Fix')
let fix = null
if (confirmed.length) {
  fix = await agent(`${RULES}

YOUR TASK -- apply the confirmed fact-check fixes to ${SHEET} and ${SCRIPT} (the only files you write). Re-read the cited source for
each before applying; if a fix is wrong in the light of the source, apply the correct version and say so. Keep the two files
consistent with each other. The script stays ASCII-only, CRLF, read-only, PowerShell 5.1. Do not run anything that loads the machine.
Return what you applied and anything you skipped and why.

CONFIRMED (most severe first):
${JSON.stringify(confirmed, null, 1)}`, { label: 'fix:sheet', phase: 'Fix', model: 'opus',
    schema: { type: 'object', properties: { summary: { type: 'string' }, applied: { type: 'array', items: { type: 'string' } }, skipped: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'applied', 'skipped'] } })
}

return { ground: G.map(g => ({ key: g.key, report: g.report })), draft, checked: C, confirmed, fix }
