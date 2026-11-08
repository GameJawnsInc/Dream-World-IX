export const meta = {
  name: 's168-w1-part1',
  description: 's168 engine part 1 (no-deploy): W1a+W1b behaviour-neutral extracts + pinned artifact, W1c pure core + proof, W1i skeleton, W1d caps b3 + section 12 sender',
  phases: [{ title: 'Extracts', detail: 'W1a bracket, W1b builder, pin the --no-deploy artifact' }, { title: 'Core', detail: 'W1c pure core + offline proof' },
    { title: 'Harness', detail: 'W1i skeleton: guestmenu sub-verb, old, key, fingerprints' }, { title: 'Wire', detail: 'W1d caps b3 + the section-12 sender' }],
}
const WT = String.raw`C:\gd\Dream-World-IX\.claude\worktrees\s166-handoff-575aeb`
const MAIN = String.raw`C:\gd\Dream-World-IX`
const SP = String.raw`C:\Users\skaki\AppData\Local\Temp\claude\9e463cf4f0985362\110b1b95-e2da-4a85-ab88-e0d8756cb21a\scratchpad`
const CLONE = String.raw`C:\gd\FFIX\Memoria`
const CONTEXT = `
You are building round s168 of the ff9mapkit netsync co-op stack for the FF9 Memoria engine: the co-op GUEST's stock main menu, rung 0 (view-only).
THE SPEC is ${WT}\\studies\\field-coop\\S168-DESIGN.md (1510 lines, reviewed four rounds; binding). Read its status paragraph, "What happens today", "Both
rounds" (decisions 1-4), "s168 (rung 0)" (decisions 5-21), "The harness" (decisions 31-35), "The owner-visible words", "The engine pieces" (W0, W1a-W1i: your
build order), "Known limits" and "Departures from the skeleton" (incl. "Cut in round 3": those mechanisms must NOT be built). s169 (decisions 22-30) is NOT built
now, but leave the seams the spec names for it (applyMask, section 13 and type 8 are registry-only in s168).
THE CLONE: ${CLONE} (shared; THIS session holds it per the netsync round queue). ${CLONE}\\Assembly-CSharp = upstream 6b8bb2d5 + the stack s12..s167 (uncommitted by
design; verified byte-exact). The s168 delta so far: \`py ${WT}\\studies\\field-coop\\s168\\s168diff.py --stat\` and \`py ${WT}\\studies\\field-coop\\s168\\s168diff.py <path rel to Assembly-CSharp>\`.
Prior art for idiom: Memoria/Netsync/NetSyncWorldWalk.cs (pure statics + proof block with rows and one-line mutants each caught by its own row), NetSyncField.cs
(MenuKeyStep, RefuseMainMenu, DeclineOnce), NetSyncDiorama.cs (THE SEAT, MirrorHostParty, the bracket, SeatSelfTest), NetSyncClient.cs (BuildStateFrame, the
overlay chain, OnGUI), Memoria/Harness/HarnessAgent.cs (sub-verbs, AppendNetsync and its catch literal), and ${WT}\\memoria-patches\\s166*.patch / s167*.patch.
The design's line numbers cite THIS clone (s167); still re-find every site by name before editing.

ENGINE RULES (non-negotiable):
- Tag every hunk: at least one ADDED line in each hunk carries \`[ff9mapkit netsync s168]\`.
- Keep each file's line endings and BOM exactly (most netsync files CRLF; HarnessAgent.cs LF). Edit with the Edit tool or Python bytes I/O; NEVER a PowerShell
  text round trip. Never reformat untouched lines.
- Match the netsync idiom (Int32/Byte[]/String/Boolean/Single; Log.Message("[NetSync] ..."); pure static rules with a selftest truth table and one-line mutants,
  each caught BY ITS OWN ROW; comments say WHY). Only C# features the surrounding code already uses (this is an old Mono/.NET 3.5-era tree).
- Compile ONLY with \`py tools/build_memoria.py --no-deploy\` run from ${WT}. NEVER without --no-deploy. Never run restore_memoria_dll / backup_memoria_dll as
  a deploy, never touch the game install, never launch the game or the in-game harness. (The owner may be playing; s167's two-PC look is pending.)
- Offline proofs: build a scratch C# exe under ${SP}\\s168proof that compiles the needed netsync sources with Unity stubs, exactly as ${SP}\\s167proof did
  (read its main.cs, stub_*.cs, check_stubs.py, build1.log to learn the compiler and the stub pattern). It must NEVER construct the netsync HOST role
  (NetSyncSocket(true, ...)) or open any listener (it binds IPAddress.Any and pops the owner's firewall). Pure statics only.
- The harness protocol stays 5 (keys additive; every new key at its sentinel in AppendNetsync's netsync-off catch literal, with a history line). No new ini knobs.
- The wire stays v15. No v15 byte changes meaning. s168 speaks cap b3 (decision 2).
- Never commit in the clone; never edit memoria-patches/*, studies/* or any Python kit file (other steps do the kit, docs and bench). Never throw from a per-frame
  or per-packet path (catch, log once per process). No per-frame allocation where the surrounding code avoids it.
- Never break s144-s167. With co-op off, for the host, and for any player outside a guest-menu seat, behaviour is byte-identical to s167 (the spec's
  vanilla-safety rules). Under \`netsync guestmenu old\` every s121 read is s121 exactly.
- Report every deviation from the spec with its reason; never silently redesign. If the spec is wrong about the code, say so and do the safest minimal thing.
`
const IMPL = { type: 'object', properties: {
  summary: { type: 'string' }, files_touched: { type: 'array', items: { type: 'string' } }, compile_ok: { type: 'boolean' }, compile_tail: { type: 'string' },
  proof: { type: 'string', description: 'every proof line run offline and its exact output (rows, mutants), or why not runnable offline' },
  contract: { type: 'string', description: 'every rule signature, why code, harness key/field/op, log line and owner-visible text this step added, exactly' },
  deviations_from_design: { type: 'array', items: { type: 'string' } }, open_issues: { type: 'array', items: { type: 'string' } } },
  required: ['summary', 'files_touched', 'compile_ok', 'compile_tail', 'proof', 'contract', 'deviations_from_design', 'open_issues'] }

phase('Extracts')
const ab = await agent(`${CONTEXT}
YOUR STEP: W1a THEN W1b, BOTH BEHAVIOUR-NEUTRAL (the spec's "The engine pieces" W1a/W1b and decisions 11-12).
W1a: NetSyncDiorama.cs's static bracket (_realMember, _realPlayer, _havePartySnapshot and friends; RememberOriginalPlayer, RestoreParty; every clear) becomes an
instance type in a NEW file Memoria/Netsync/NetSyncSeatBracket.cs (add it to Assembly-CSharp.csproj next to the other Netsync files, same line endings), with the
diorama's single instance used everywhere the statics were. Keep the diorama's exact order of operations, logging and failure handling. Extend the bracket
selftest with the two-instance rows decision 31/GM0-BRACKET-CLEAR names (two instances never cross-restore; each clear clears only its own).
W1b: MirrorHostParty's per-slot scratch builder becomes a shared function whose only caller today is the diorama; it takes OPTIONAL per-member overrides (preset,
category and pa right after FF9Play_New; exp after FF9Play_Build; basisCapa before its own FF9Play_Update) and a 'rethrow' flag; the diorama passes neither, so
its per-slot containment and every byte it seats stay identical. Do NOT add any menu caller yet.
Prove behaviour-neutrality: diff the moved code against ${SP}\\s167base line by line (report it), run SeatSelfTest and the bracket selftest OFFLINE if they can
be stubbed (else say exactly why not and what in-game proof covers them), compile with --no-deploy until clean.
THEN PIN THE ARTIFACT (spec: W1a+W1b's --no-deploy artifact is kept for GM0-BRACKET): after the clean build, copy ${CLONE}\\Output\\Assembly-CSharp.dll and its
.mdb into ${MAIN}\\backups\\ under names from tools/backup_memoria_dll.py's canonical_name(dll, arch, ts, label) with label 'pin-s168w1ab' for BOTH arches
(x64 and x86 get the same bytes) and the current timestamp format that tool uses, and write their sha256 (first 16 hex) into your report. Never copy anything
into the game install. Return the IMPL schema.`, { label: 'W1a+W1b extracts + pin', phase: 'Extracts', schema: IMPL, model: 'opus' })
log(`W1a+b: compile_ok=${ab && ab.compile_ok}`)

phase('Core')
const core = await agent(`${CONTEXT}
Previous step (W1a+W1b) report: ${JSON.stringify(ab).slice(0, 4000)}
YOUR STEP: W1c, THE PURE CORE, INERT (decisions 5-21 as pure rules; "The engine pieces" W1c). New file Memoria/Netsync/NetSyncGuestMenu.cs (in the csproj):
GuestMenuKeyStep (decision 6, the press pre-check only: SIMP-DOOR -- the press arms nothing), the predicate GuestMenuWhyNot as a pure rule over named inputs
(decision 8's terms and why codes exactly), the door rule (decision 9: the one open verdict for every FieldHUD/WorldHUD -> MainMenu entry), the section-12 codec
(decision 5's exact byte layout; fmt 1; policy and applyMask zero in s168) with PURE order-keeping readers for sections 1/2/3/12 (decision 12: never
ParseSections or NetSyncParty statics), the content witness (decision 13), the section-12 guard with TrailReserve = 424 + 6 recomputed from NetSyncDialog's
HeaderLen/OpenLen/OpenCap/count byte/RingCap/EventLen by a proof row (decision 5, cut 10), the close-trigger rule (decision 18's table ids), the close-order states
(decision 21 as it now stands after the cuts), the restore identity rule (decision 16), the press deadline rule (decision 9 / the ramp settle term). Add
NetSyncDiorama's read-only \`internal static Boolean Armed => _armed;\` (or the bracket-era equivalent) for decision 8's term 10.
THE PROOF: a NEW proof line 'guest menu selftest: OK (N rows, M mutants caught)' in NetSyncGuestMenu.cs with its OWN row helper (never NetSyncField's MenuRow;
MenuRefusalSelfTest stays at its pinned 14 rows), rows for every rule's truth table and the mutants the spec names for these rules (decision 34 and the GM0-PROOF
row), each mutant caught by its own row. Hook the proof line into the same place the other proof lines are logged in game (find where 'world walk selftest'
is logged), appended after the last one. Build ${SP}\\s168proof (the s167proof pattern) and run it: report N/M exactly and every mutant's catching row.
Nothing calls these rules yet (inert). Compile --no-deploy until clean. Note for the coordinator (do not edit Python): tools/memoria_stack_replay.py DEFAULT_FILES
must gain NetSyncGuestMenu.cs and NetSyncSeatBracket.cs. Return the IMPL schema with the exact contract (every signature and why code).`,
  { label: 'W1c pure core + proof', phase: 'Core', schema: IMPL, model: 'opus' })
log(`W1c: compile_ok=${core && core.compile_ok}`)

phase('Harness')
const harn = await agent(`${CONTEXT}
Previous steps: W1a+b ${JSON.stringify(ab).slice(0, 2000)}\nW1c ${JSON.stringify(core).slice(0, 5000)}
YOUR STEP: W1i's SKELETON (the spec's build order puts it before W1d-W1h, which each add their own levers and keys to it). In Memoria/Harness/HarnessAgent.cs (LF):
the \`netsync guestmenu\` sub-verb appended LAST in the unknown-sub-verb literal (decision 31) with \`old|act\` and \`clear\` now (the other ops come with their
pieces; leave a clear place for them), HarnessReleaseGuestMenu wired into NetSyncBattle.HarnessReleaseBench's release chain (decision 31's release list as far as
the ops exist), the \`netsync.guestmenu\` key (decision 32's fields as far as they exist now: lever, caps, why, session, seated, opens, closes, refused, fp,
seat_fp; later steps add theirs) with its sentinel in AppendNetsync's netsync-off catch literal and a history line, the \`old\` lever state read by
GuestMenuKeyStep's \`old\` input, and the ENGINE-STAMPED fingerprints in NetSyncGuestMenu.cs (decision 33: fp_before at the seat, fp_after at the restore, named
components over what the save's Common serializer writes for players, party, bag in order, gil and key items; seat_fp; host_fp harness-only) as functions the
seat/restore will call (W1f wires them). Add proof rows for the fingerprint's component naming (a changed component is named). Compile --no-deploy; re-run
${SP}\\s168proof. Return the IMPL schema with the exact contract.`, { label: 'W1i skeleton', phase: 'Harness', schema: IMPL, model: 'opus' })
log(`W1i: compile_ok=${harn && harn.compile_ok}`)

phase('Wire')
const wire = await agent(`${CONTEXT}
Previous steps: W1c ${JSON.stringify(core).slice(0, 3000)}\nW1i ${JSON.stringify(harn).slice(0, 3000)}
YOUR STEP: W1d, CAPS b3 AND THE SENDER (decisions 2, 3, 5; "The engine pieces" W1d; decision 32's re-key list for s167's caps rows). NetSyncWorldWalk.cs:
OwnCapsRule gains its second argument exactly as decision 2 states (fpOff ? OwnCaps : (OwnCapsWalk | (menuOff ? 0 : CapGuestMenu))), the OwnCapsFn delegate
becomes two-argument, OwnCapsNow passes the live \`guestmenu caps off\` lever (add that op to the guestmenu sub-verb and its release), the new proof row
caps.own_s168_word and the re-keyed s167 rows/mutants (keep every s166/s167 row's meaning; where a pinned value must change, change the row and say so).
NetSyncState.cs: the section-12 constant (and reserve 13 by comment only). NetSyncClient.cs BuildStateFrame: append section 12 ONLY to a b3 following guest
(the FpSectionSendRule pattern; decision 5's send rule), built by HostGuestMenuSectionNow in its OWN try (a throw drops the section with one line per process and
\`frame.faults\`, never the frame), with the FRAME-CAP-GUARD's LOCAL check at 12's append (frame so far + 3 + len(12) + TrailReserve <= NetSyncWire.MaxPayload;
BuildStateFrame's order and the 5+7 one-snapshot rule UNTOUCHED), the \`frame\` key fields decision 32 lists. Proof rows for the send rule and the guard. Compile
--no-deploy; re-run the world walk proof AND the guest menu proof offline (both lines, exact N/M). Return the IMPL schema with the exact contract.`,
  { label: 'W1d caps b3 + sender', phase: 'Wire', schema: IMPL, model: 'opus' })
return { ab, core, harn, wire }
