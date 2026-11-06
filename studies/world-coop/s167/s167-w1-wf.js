export const meta = {
  name: 's167-w1-engine',
  description: 's167 round B, W1: recon the round-B sites in the s166 clone, build the pure core and the engine wiring (walk, refusal, stall hole, re-arm, fingerprint, TPS, caps, minimap close, full map), adversarial review',
  phases: [
    { title: 'Recon', detail: 'read-only: every round-B site re-found in the s166 clone; the fingerprint inputs measured' },
    { title: 'Engine', detail: 'B-core, then the walk wiring, then fingerprint/TPS/caps, then the minimap close + the full map + surfaces' },
    { title: 'Review', detail: 'adversarial review of the whole s167 delta, fixing what it confirms' },
  ],
}

const WT = String.raw`C:\gd\Dream-World-IX\.claude\worktrees\s166-handoff-575aeb`
const SP = String.raw`C:\Users\skaki\AppData\Local\Temp\claude\9e463cf4f0985362\110b1b95-e2da-4a85-ab88-e0d8756cb21a\scratchpad`
const CLONE = String.raw`C:\gd\FFIX\Memoria`
const GAME = String.raw`C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX`

const CONTEXT = `
You are building round s167 of the ff9mapkit netsync co-op stack for the FF9 Memoria engine: world-map co-op RUNG 2, ROUND B ("the walk"). Today (s144-s166) a following guest lands on the world map at the host's spot and stands FROZEN until the host's next stop; round A (s166, live as b24e0123ac93960c, two-PC proven by the owner 2026-11-05) added wire v15 with a world trailer on type 0, the receiver cache, lane-gap lines on both roles, the host's world lines, the world ghost both ways, the dot from the trailer, the control-off kit-cell close (A0) and the pairing pull (A0b). Round B lets the guest WALK its own copy on foot on the walk worlds {9002, 9010, kit 9011}, refuses its entrances with a buzz and words, closes the stall hole, adds the world fingerprint, reports WorldTPS, opens the full map for a lawful walker (decision 8), and -- folded in by the owner 2026-11-05 -- fixes the frozen guest's minimap close (decision 27) with the hint quiet after a deliberate close (decision 28).

READ FIRST, the design ${WT}\\studies\\world-coop\\S166-DESIGN.md: "What happens today"; decisions 1-12 and 26 (round A's contract: what exists now); ROUND B: decisions 13-24 and 27-28; decision 25 (the harness; round B levers walk, pair, refuse, stallhold, decline, fp, tps, fullmap, minimap; keys netsync.world.walk and netsync.world.fp); "The owner-visible words" (the s167 lines); "The engine pieces" (A1's s167 additions, B1-B7); "The bench" (the stand-in's faults, the Round B rows incl. W-MINIMAP, the Order, the Regression paragraph's round-B sentence); "Known limits" (the s167-tagged items: W3A-T4/W3C-1 wire FeatureOn + a missing-caps line; W3C-4 map the world-out why codes to a class table); "The owner's calls" -- ALL DECIDED: item 4 decision 8 OPENED (the full map for a lawful walker on 9010/9011); item 6 freeze on a riding host AND on any host scene; item 7 keep walking through a stall/host loss (ghost stands ~300 ms, hides at 5 s); item 8 the fingerprint as recommended (six components, the loaded language only, s165's follow-out not gated); item 9 WorldTPS report-only (+ the owner-trial lever); item 10 the ~ menu Release row kept, its hint reworded; item 11 accepted; item 15 decisions 27-28.
Also read: ${WT}\\studies\\world-coop\\TWO-PC-CHECKS-S166.md "## Results" finding 1 (the minimap defect and its code traps); ${WT}\\studies\\world-coop\\S166-HANDOFF.md (how round A was built and what it left).
Prior art for idiom: Memoria/Netsync/NetSyncWorldWalk.cs (round A's pure core and its proof block: THIS FILE GROWS), NetSyncWorldGhost.cs, NetSyncWorldFollow.cs, NetSyncWorldDot.cs, NetSyncField.cs (WorldFreezeHold, WorldFreezeNow, WorldFreezeRule, WorldFreezeEdge, FilterScriptButtons, RefuseWorldUi, SpectatorField, the DeclineOnce books), and the patches ${WT}\\memoria-patches\\s165*.patch and s166*.patch for shape.
THE DESIGN'S LINE NUMBERS CITE THE s165 CLONE (e364ca8d). The clone is now s166: RE-FIND every site by name.

LAWS (true; respect them): THE KIT CELLS ARE ON EVERY FREE-ROAM WORLD (and 9013; the close keys on the reader, never a world set). THE TRIGGER IS NOT THE CELL (a world entrance fires only on its event-id triangles; 6603 only within 3 u of (80,-444)). THE BOAT READS EVERY CONFIRM ON 9011 (an eager KEYON; KEYON never short-circuits, so one press is read by several entries). THE BENCH TERM HOLDS THE FREEZE (on the forced selftest role SpectatorField's IsSelfTestRole && BenchGates holds the world freeze). THE ARM-FIRST ORDER. THE COMMIT'S LOAD IS A TRANSITION. A GAME PUBLISHES NOTHING DURING ITS OWN SYNC LOAD. THE PRE-INIT SAMPLE (world rows judge after world.block_ready and advancing world.ticks). THE ORDER SKEW (a control flip's own publish carries the old verdict). THE DUO CANNOT PULL A SELFTEST-ROLE LEVER (levers any-role where the duo needs them). THE CATCH LITERAL IS PART OF EVERY KEY ADDITION. LIVE VERDICT vs LAST DRAWN. A REFUSED STEP STRANDS A STOCK CYCLE (when a co-op guard refuses one state of a stock cycle, route the press to the next allowed state; walk every state after the refused one).

THE CLONE: ${CLONE} (shared; THIS session holds it per the netsync round queue). Engine source: ${CLONE}\\Assembly-CSharp = upstream 6b8bb2d5 + the stack s12..s166 (uncommitted by design). The s167 delta: \`py ${WT}\\studies\\world-coop\\s167\\s167diff.py --stat\` and \`py ${WT}\\studies\\world-coop\\s167\\s167diff.py <path relative to Assembly-CSharp>\` (against the s166 snapshot ${SP}\\s166base).

ENGINE RULES (non-negotiable):
- Tag every hunk: at least one ADDED line in each hunk carries \`[ff9mapkit netsync s167]\`.
- Keep each file's line endings exactly (check before editing: most netsync files are CRLF, HarnessAgent.cs is LF). Edit with the Edit tool or Python bytes I/O; NEVER a PowerShell text round trip. Never reformat untouched lines. Keep any BOM.
- Match the netsync idiom exactly (Int32/Byte[]/String/Boolean/Single, Log.Message("[NetSync] ..."), pure static rules with a selftest truth table and one-line mutants each proven caught BY ITS OWN ROW, comments that say WHY). Only C# features the surrounding code already uses.
- Compile ONLY with \`py tools/build_memoria.py --no-deploy\` from ${WT}. NEVER without --no-deploy. Never run restore/backup tools, never touch the game install, never launch the game or the in-game harness. (The owner may be playing; --no-deploy never touches the install.)
- To run a pure proof OFFLINE you may build a scratch C# exe under ${SP}\\s167proof that loads the built DLL and calls the pure statics, as round A did. It must NEVER construct the netsync HOST role (NetSyncSocket(true, ...)) or open any listener: that binds IPAddress.Any and pops the owner's firewall. Pure statics only.
- The harness protocol stays 5 (keys additive; every new key at its sentinel in AppendNetsync's netsync-off catch literal with a history line). No new ini knobs.
- The wire stays v15 (decision 2's law: round B is additive, gated on the PEER's caps b1). No v15 byte changes meaning.
- Never commit in the clone; never edit memoria-patches/* or any Python kit file (another workflow does the kit, the stand-in and the bench). Never throw from a per-frame or per-packet path (catch, log once per process). No per-frame allocation where the surrounding code avoids it.
- Never break s144, s145, s154, s157, s163, s164, s165, s166. Every round-B lever's off/old setting is s166 EXACTLY; with every round-B lever at its s166 setting the build behaves byte-identically to s166 on every path.
`

const RECON_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    sites: { type: 'array', items: { type: 'object', properties: {
      piece: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' }, excerpt: { type: 'string' }, note: { type: 'string' } },
      required: ['piece', 'file', 'excerpt'] } },
    contradictions: { type: 'array', items: { type: 'string' }, description: 'design claims the s166 clone contradicts or s166 already changed' },
    measurements: { type: 'string' },
    recommendations: { type: 'array', items: { type: 'string' } },
    open_issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'sites', 'contradictions', 'measurements', 'recommendations', 'open_issues'],
}
const IMPL_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    files_touched: { type: 'array', items: { type: 'string' } },
    compile_ok: { type: 'boolean' },
    compile_tail: { type: 'string' },
    selftest_rows: { type: 'string' },
    sites: { type: 'array', items: { type: 'string' } },
    contract: { type: 'string', description: 'every harness key, field, op, reply text, log line and owner-visible line this piece added, exactly' },
    deviations_from_design: { type: 'array', items: { type: 'string' } },
    open_issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'files_touched', 'compile_ok', 'compile_tail', 'selftest_rows', 'sites', 'contract', 'deviations_from_design', 'open_issues'],
}
const REVIEW_SCHEMA = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] }, file: { type: 'string' },
      line: { type: 'integer' }, claim: { type: 'string' }, evidence: { type: 'string' },
      verdict: { type: 'string', enum: ['confirmed-fixed', 'confirmed-not-fixed', 'refuted'] }, fix_note: { type: 'string' } },
      required: ['id', 'severity', 'file', 'claim', 'evidence', 'verdict', 'fix_note'] } },
    compile_ok: { type: 'boolean' }, compile_tail: { type: 'string' }, selftest_rows: { type: 'string' }, contract_final: { type: 'string' }, summary: { type: 'string' },
  },
  required: ['findings', 'compile_ok', 'compile_tail', 'selftest_rows', 'contract_final', 'summary'],
}

phase('Recon')
const [reconA, reconB] = await parallel([
  () => agent(`${CONTEXT}
YOUR STEP: RECON A, READ-ONLY (edit nothing; scratch only under ${SP}\\s167w1). For every engine site of decisions 13-20, 23, 24, 27 and 28 (pieces B1, B2, B3, B6 and B7's engine half), re-find it in the s166 clone and report the exact current file:line with a short excerpt, and flag every design claim that the s166 clone contradicts or that s166 already changed. At least: WorldFreezeHold's frozen path and the conjunct it feeds in ff9.cs's movement control; WorldFreezeEdge; WorldFreezeNow / WorldFreezeRule; FilterScriptButtons' entry test, its gMode-3 frozen branch and its control-off branch (A0's close); SpectatorField and the three reads decision 17 names (FilterScriptButtons' entry, SkipWorldScriptedBattle, WorldFreezeNow); _sessionState / SessionLive / SessionGrace / _sessionSeenLive / _exitRampPending / IsLiveFollowedSession and where Update recomputes the session state; IsMirroringStory; NetSyncVisitor.SuppressEncounters and FollowHost (and the forced-role pin); the latch's cheap terms (fading, nextMode, attr 0x3001, booted, the rejoin armed, a world-out pending); w_moveCHRControl_No, w_moveChocoboPtr, w_movePlanePtr, [190], the walker index; the bee scene; the event worlds; the DeclineOnce books (_lastDeclineWorld and the field book's world classes, the "main menu (world map)" line); WMScriptDirector.HonoAwake's backstops (s165's dot, s166's ghost); the reader's sid (EventEngine), KeyTick, Map[24] (ee.GetMapVar()), Bits 811/812; the kit cells' / boat's / ferryman's entries on deployed 9011 as the design describes them; the s145 diorama boot and the s144 rejoin arm (where a co-op full-map close must run first); WorldHUD: OnKeySelect, Update's FullMap branch, DisplayFullmap, SetupBubble / FallbackBubbleToEvent, ForceCloseFullMap, SetMinimapVisible / SetMinimapPressable / isSelectEnable, MapButtonGameObject, DisplayChocographLocation, byte_gEventGlobal_updateNaviMode, mapPlayerPointer / mapContent; NetSyncWorldDot.MinimapHintNow, HintRule and its caller in NetSyncClient (the overlay chain); NetSyncField.RefuseWorldUi and HarnessWorldFreezeMap; Ff9mkDebugMenu's Release row, its hint and the co-op hint text; the harness: HarnessAgent's \`worldwalk\` sub-verb (list every op round A shipped and how a new op is added), the netsync.world.* keys, and what already exists to judge W-FREE (hold up, world.x/z, freeze.on, freeze.edges). Also say where the timed overlay line for the refusal should live (the overlay states and their priorities) so it never stacks with s165's hint.
Return the RECON schema.`, { label: 'recon A: walk/refusal/stall/map sites', phase: 'Recon', schema: RECON_SCHEMA, model: 'opus' }),
  () => agent(`${CONTEXT}
YOUR STEP: RECON B, READ-ONLY (edit nothing in the clone or the repo; scratch only under ${SP}\\s167w1). For decision 21 (the fingerprint), decision 22 (WorldTPS), the caps (decision 2 and Known limits W3A-T4/W3C-1: FeatureOn and a missing-caps line) and W3C-4 (the why class table), re-find every site in the s166 clone with file:line and an excerpt: ff9InitStateWorldMap and s165's seam beside it; how the world dispatchers load (AssetManager.LoadBytesMerged, the EventDB / WorldScene entries for 9000-9013); Configuration's [Mod] MergeScripts and the folder order; the WorldMap override loader (the "[WorldMeshOverride] loaded ..." line: what it reads and how to enumerate the override tree cheaply); the effective TransportControls.csv; the environment patch; the weather CSV; the loaded language; BuildStateFrame's sections and the guest's section reader (where a section 11 goes: between 10 and 7, 8 stays last); the trailer codec's digest (bytes 88-91) and why byte (50) in NetSyncWorldWalk; NetSyncSpeed (s163) and the two SetMainLoopSpeed sites (WMScriptDirector, SceneDirector); FeatureOn and every live gate that reads the peer's caps today; the world-out why codes 1-29 (NetSyncWorldFollow) and how lane.rx.why folds codes 15-29 into 15.
MEASURE, read-only, on THIS machine: the WorldMap override tree of every folder in the install's Memoria.ini [Mod] FolderNames that has one (the install: ${GAME}; FF9CustomMap-world holds about 508 world meshes): file count, total bytes, and the wall time of (a) path + length only, (b) a full CRC32 over every byte, each cold-ish and warm, in Python; then the size of every other component's input. The fingerprint runs on the main thread at each world load, so recommend each component's form (the design: "path and length, or a CRC once K1 has measured it") with the numbers. Also check whether the two machines' paths could differ in case, separator or order, and how to make the digest deterministic.
Return the RECON schema.`, { label: 'recon B: fingerprint/TPS/caps sites + cost', phase: 'Recon', schema: RECON_SCHEMA, model: 'opus' }),
])
log('recon done')

phase('Engine')
const core = await agent(`${CONTEXT}
RECON (use it; verify anything you rely on): A ${JSON.stringify(reconA)}; B ${JSON.stringify(reconB)}
YOUR STEP: B-CORE, round B's pure core, inert except its proof, in ${CLONE}\\Assembly-CSharp\\Memoria\\Netsync\\NetSyncWorldWalk.cs (keep every round-A rule, row and mutant untouched). Build each as a pure static with its facts as plain values:
- WalkFreeRule: decision 14's ten terms, cheapest first, one why each, the whys as a small code table (W3C-4's class table can share it); no [181] term; the bench's \`pair unmirrored\` lever term.
- The stall hold (decision 16): a pure step that keeps the last FRESH frame's inputs (never a verdict), re-evaluated live against my state; the drop edges (world load, s165 landing, title, session edge, host epoch change); never freezes on staleness alone.
- WorldSessionHeld's pure predicate (decision 17).
- EntryRefusalRule (decision 18: the read's conditions, cases a-d with their Map[24]/[190]/sid/Bit 811-812 tests, the KeyTick dedupe, place 52 silent, the frozen-guest variant behind \`refuse silent\`).
- DeclineRearmRule (decision 20).
- The fingerprint's pure parts (decision 21): combining component CRCs into the u32, the compare, naming the first differing component from section 11, 0 = checking and its timeout, the language term. Shape the components per RECON B's measurements.
- The WorldTPS mismatch rule (decision 22).
- Decision 23's pure parts: the full-map open rule (a lawful walker on 9010/9011 only), the location pick still refused, the co-op close predicate (before a rejoin arm or an s145 boot).
- Decision 27: MinimapSelectRule(state, freezeNow, mapButtonEnabled, encount, ...) -> stock | coop close | (whatever the s166 verdict was for the lever); decision 28: MinimapHintQuietRule(hudNoMiniMap, verdictShow, closedThisVisit) and the latch's clear edge.
- FeatureOn for b1 (both caps words) and the missing-caps line rule (once per process and peer caps).
Proof: extend round A's proof (\`world walk selftest: OK (N rows, M mutants)\`, the text unchanged, counting every row) with a truth-table row set per new rule and the design's s167 mutants, each caught BY ITS OWN ROW: a [181] term; the static-ids-only rule (must fail "kit 9011, host aboard"); a plane-pointer refusal (must fail "kit 9011, both on foot"); no pairing term; freeze on staleness; NetSyncVisitor.FollowHost read; a Map[24]-only refusal (must fail the kit-cell row); buzz on any Confirm (must fail the open-ground row); a boat case without the 169 test (must fail the boat-range row); no KeyTick dedupe; plus decisions 27-28's: branching on RefuseWorldUi, reusing SetMinimapPressable(false), taking the full-map close branch, forgetting the hint latch; plus one per other new rule.
Compile with --no-deploy until clean; run the proof offline (the scratch exe rule) and report N/M exactly. Return the IMPL schema (contract: every rule's signature and why codes, exactly).`, { label: 'engine: B-core', phase: 'Engine', schema: IMPL_SCHEMA, model: 'opus' })
if (!core) throw new Error('B-core failed')

const walk = await agent(`${CONTEXT}
RECON: A ${JSON.stringify(reconA)}
B-CORE is built (its report: ${JSON.stringify(core)}).
YOUR STEP: THE WALK WIRING -- B1, B2, B3 and the re-arm -- in the clone (NetSyncField.cs, NetSyncClient.cs, NetSyncWorldWalk.cs, HarnessAgent.cs; others only if a site demands it, and say why):
- B1 (decisions 13, 14, 16): only WorldFreezeHold's frozen path changes; WorldFreezeRule's table stays byte-identical and WorldFreezeNow changes only by decision 17's term. \`WorldFreezeNow && WalkFreeNow()\` returns false and sets \`_freezeHeld = false\`, one "world walk FREE" or "FROZEN (why)" line per edge; WorldFreezeEdge takes a why. WalkFreeNow is a live read of engine statics + the receiver cache + the held inputs, never a frame-stamped verdict; allocation-free; a fault returns frozen. \`freeze.on\` stays true while walking.
- B2 (decision 18): the entry refusal at the read, in FilterScriptButtons' gMode-3 frozen branch (which still returns the masked keys): the buzz (FF9Sfx 102), the timed overlay line "Your partner leads the way. You'll join them at their next stop." in NetSyncClient, cleared at every scene change (the rejoin, an s145 boot, the ramp, the title), never stacked with s165's hint; counters and one log line per entrance class per visit; the same buzz for a FROZEN guest on the walk worlds behind its own lever (\`refuse silent\` = s166).
- B3 (decision 17): WorldSessionHeld OR'd on gMode 3 into exactly the three reads; SpectatorField itself unchanged; lever \`stallhold old\`. And decision 20's DeclineOnce re-arm (lever \`decline old\`).
- The guest's refused-walk words (the s167 lines in "The owner-visible words": riding and scene reuse s165's words; pairing; "Checking your world map against your partner's..."; the fingerprint and older-build lines may read facts the next step fills: leave clean hooks) and the host's s167 lines through HostLineRule's states (the same: hooks for the fingerprint ones).
- The harness: the round-B levers walk / pair / refuse / stallhold / decline in the \`worldwalk\` sub-verb (any role where the duo needs them; released with the harness), the key netsync.world.walk (lever states, free, why, edges, held-input age, entry_refused, last_reader, last_place, last_cell, and a minimap_closes field the next steps fill) at its sentinel in the catch literal with a history line; any bench-host op W-REFUSE-x needs that round A lacks.
Compile with --no-deploy until clean; re-run the proof offline. Return the IMPL schema with the exact contract.`, { label: 'engine: the walk wiring', phase: 'Engine', schema: IMPL_SCHEMA, model: 'opus' })
if (!walk) throw new Error('walk wiring failed')

const fp = await agent(`${CONTEXT}
RECON B: ${JSON.stringify(reconB)}
Built so far: B-CORE ${JSON.stringify(core)}; THE WALK ${JSON.stringify(walk)}.
YOUR STEP: B4 + B5 + the caps + the why table, in the clone:
- B4 (decision 21): the fingerprint computed per world at each world load on the main thread at s165's seam, its cost logged once per load; the components per RECON B's recommendation; the u32 in the trailer's digest (88-91) on both roles; the host's section 11 \`[fmt][world][lang][n x (comp, crc)]\` between 10 and 7 (8 stays last); a mismatch keeps the freeze (WalkFreeRule term 10) with one line per visit per side naming the component; 0 = "checking", bounded by one timeout line; the loaded language only; s165's follow-out NOT gated (logged only). Fill the words hooks the walk step left (guest: "Your world map differs from your partner's (<component>): you'll follow them as before.", "Checking your world map against your partner's...", "Your partner's co-op build is older: you'll follow them as before."; host: "Your partner's world map differs from yours: they'll follow you as before.", "Your partner can't walk yet: they'll join you at your next stop.", "Your partner's co-op build is older: they'll follow you as before.").
- The caps: set b1 in the own caps word (this build carries the fingerprint); FeatureOn wired at every live gate that needs both caps words (W3A-T4); one missing-caps line per process and peer caps word (W3C-1). An s166 peer (caps b0 only) must keep s166 behaviour on BOTH roles: the guest stays frozen with "older build", the host draws its ghost and lines as s166.
- W3C-4: map the world-out why codes to a class table so the trailer's why and lane.rx.why stop folding 15-29.
- B5 (decision 22): WorldTPS report: both values published, one mismatch line per pair; the owner-trial lever \`tps apply\` applies the host's value at both SetMainLoopSpeed sites at a world load only, held for the visit (off = report only = s166 plus the report).
- Levers \`fp fake <hex>\`, \`fp off\`, \`fp old\` (dry: reports "would walk", stays frozen), \`tps apply|report\`; the key netsync.world.fp (own digest, peer digest, components, compute ms, state checking/match/mismatch/older, the named component) at its sentinel in the catch literal.
Compile with --no-deploy until clean; re-run the proof offline. Return the IMPL schema.`, { label: 'engine: fingerprint, TPS, caps', phase: 'Engine', schema: IMPL_SCHEMA, model: 'opus' })
if (!fp) throw new Error('fingerprint step failed')

const map = await agent(`${CONTEXT}
RECON A: ${JSON.stringify(reconA)}
Built so far: B-CORE ${JSON.stringify(core)}; THE WALK ${JSON.stringify(walk)}; FINGERPRINT ${JSON.stringify(fp)}.
YOUR STEP: decisions 27-28, then decision 23 (B6), then B7's engine half:
- Decision 27 in WorldHUD.OnKeySelect: while WorldFreezeNow holds (asked directly, never through RefuseWorldUi, which buzzes, counts and logs) and the state is HUD with the map button enabled and no encounter, Select goes straight to HUDNoMiniMap: the state, MiniMapPanel off, w_naviMode 0, the chocograph marker off; the block's shared byte_gEventGlobal_updateNaviMode writes [100]. NOT SetMinimapVisible(false) (its SetMinimapPressable(false) kills Select), NOT the full-map close branch (it never hides MiniMapPanel; its control writes are forbidden here). No buzz; \`minimap_closes\` +1 on netsync.world.walk; one log line per world visit. A walker on 9010/9011 under decision 8 keeps stock's cycle. Lever \`minimap old\` = s166's stranded cycle exactly (and s165's hint).
- Decision 28: the hint latch (closed this visit -> quiet), set by a Select close (decision 27's, or stock's own close from the full map on a walker), cleared at every world load beside the dot's backstop; s165's hint rows kept.
- Decision 23 (B6): RefuseWorldUi(WorldUiFullMap) passes for a lawful walker on 9010/9011 only while WalkFreeNow; the location pick stays refused; the full-map dot as a per-frame hook in WorldHUD.Update's FullMap branch (a clone of mapPlayerPointer under mapContent, placed by DisplayFullmap's formula with s165's seam clamp, minted lazily and latched, hidden at the close and every world load); before a rejoin arm or an s145 boot, a co-op close that replays WorldHUD's own Select-close branch (never ForceCloseFullMap), its own line; "Close the map to join your partner." only where no co-op close runs; lever \`fullmap old\` = s166 (the full map refused).
- B7's engine half: Ff9mkDebugMenu's Release row hint "Enter locations alone (until the next field load)" and its co-op hint text that says the guest waits -> walks (decision 24); only the engine's texts (the kit's Python texts are another workflow's).
Compile with --no-deploy until clean; re-run the proof offline. Return the IMPL schema.`, { label: 'engine: minimap close, full map, surfaces', phase: 'Engine', schema: IMPL_SCHEMA, model: 'opus' })
if (!map) throw new Error('map step failed')

phase('Review')
const review = await agent(`${CONTEXT}
YOUR STEP: an ADVERSARIAL REVIEW of the WHOLE s167 delta (\`s167diff.py\` against the s166 snapshot), then FIX every confirmed finding yourself and recompile until clean. Reports (orientation only; verify everything): B-CORE ${JSON.stringify(core)}; WALK ${JSON.stringify(walk)}; FINGERPRINT ${JSON.stringify(fp)}; MAP ${JSON.stringify(map)}.
Hunt for:
1. LEVER PARITY: with every round-B lever at its s166 setting, is the behaviour byte-identical to s166 on every path (field, battle, world map, title, session edges, the selftest role, a host)? Diff each changed function's old vs new.
2. THE WALK'S SAFETY: can a guest ever walk while it could roll its own battles, take an entrance alone, board the boat, start the ferryman, walk on a mismatched world, on a vehicle world or an event world, during a fade / load / world-out / rejoin, with a booted or returning diorama, with an s166 host (caps b0 only)? Is every term of decision 14 present, in order, each with its why?
3. THE REFUSAL vs decision 18: KEYON evaluated twice per press (the KeyTick dedupe), each reader case exactly (a-d), place 52 silent, the open ground silent, the masked keys still returned, the overlay cleared at every scene change and never stacked with the hint.
4. THE STALL: never freezes on staleness alone; the held inputs drop at every listed edge; WorldSessionHeld at exactly the three reads; SpectatorField unchanged.
5. DECISIONS 27-28's traps (RefuseWorldUi's side effects, SetMinimapPressable, the full-map close's control writes), the latch's clear edge, the walker's stock cycle.
6. DECISION 23: the control writes of SetupBubble / FallbackBubbleToEvent; the co-op close before EVERY rejoin arm and s145 boot; the location pick refused; the full-map dot's lifecycle off the world map (no stray WMWorld).
7. THE FINGERPRINT: main-thread cost only at a world load, never per frame; deterministic across two machines (path case, separators, ordering, language); 0/checking and its timeout; section 11 placement and parse; an s166 peer.
8. THE WIRE: v15 unchanged; every v14/s166 byte keeps its meaning; b1 gating both ways via FeatureOn; the missing-caps line once.
9. THE HARNESS: keys and levers exactly as contracted; extract AppendNetsync's catch literal and parse it as JSON with every new key at its sentinel; protocol 5; levers released with the harness; any-role where the duo needs them.
10. Every hunk tagged s167; line endings; BOMs; the csproj if a file was added.
11. THE PROOF: apply 6 mutants mentally (or offline), name each catching row; the proof line's text.
Compile with --no-deploy; re-run the proof offline and report N/M. Return the REVIEW schema (contract_final: the whole s167 harness/log/words contract as it now stands).`, { label: 'review + fix the s167 delta', phase: 'Review', schema: REVIEW_SCHEMA, model: 'opus' })

return { reconA, reconB, core, walk, fp, map, review }
