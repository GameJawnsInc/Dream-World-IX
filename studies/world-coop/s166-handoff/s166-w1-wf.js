export const meta = {
  name: 's166-w1-core-and-wire',
  description: 's166 round A, W1: the pure core (A1) and wire v15 (A2) in the engine, the kit wire lane (coop_peer v15, tapes, pins), review, reconcile',
  phases: [
    { title: 'K1', detail: 'read-only: type-0 inter-arrival times from the existing tapes (the gap seed, the real send rate)' },
    { title: 'Engine', detail: 'A1 the pure core (inert), then A2 wire v15 (version, caps, the trailer through both transports, the relay sentinel, the forward parse, the arrival tick, the peer-version line); then an adversarial review that fixes' },
    { title: 'Kit', detail: 'coop_peer v15 (send version from the game, restamp, --freeze-at, --no-follow, --gap-at, where --pose), the v14 pins to 15, the s157 39 B judges re-keyed' },
    { title: 'Reconcile', detail: 'kit vs engine contract, the offline tests once' },
  ],
}

const WT = String.raw`C:\gd\Dream-World-IX\.claude\worktrees\dreamy-allen-a2375f`
const SP = String.raw`C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX--claude-worktrees-dreamy-allen-a2375f\3f9e72b5-f0f3-488a-a7a3-4b0fc4406058\scratchpad`
const CLONE = String.raw`C:\gd\FFIX\Memoria`

const CONTEXT = `
You are building round s166 of the ff9mapkit netsync co-op stack for the FF9 Memoria engine: world-map co-op RUNG 2, ROUND A ("the wire, the cache, the lines, the ghosts, with the guest still frozen"). Pieces A0 (decision 19, the control-off kit-cell close) and A0b (decision 26, the pairing pull) are ALREADY built, deployed and benched -- build beside them, never change them. THIS workflow (W1) builds ONLY engine pieces A1 (the pure core, inert) and A2 (wire v15), plus the kit's wire lane. A3 (the sender at SetLocal, the receiver cache, the lane-gap and host lines), A4 (the world ghost) and the dot's re-source come in the next workflow; do not start them.

READ FIRST, the design ${WT}\\studies\\world-coop\\S166-DESIGN.md: "What happens today", decisions 1-12 (Round A) and 25 (the harness), "The owner-visible words", "The engine pieces" (A1, A2), "The bench" (K1, the stand-in, Tapes, the Round A rows, Order, Regression), "Known limits". Every owner call is DECIDED. The recon behind it is in ${SP}\\wf2\\ (digest2_N.md = the network/wire lane, digest2_G.md = the ghost lane, digest2_S.md, digest2_W.md, digest2_critic.md: file:line evidence at the s165 clone's lines; THE DESIGN WINS where they disagree). Line numbers in the design are the s165 clone's: re-find every site by grep.
Prior art to copy the idiom from: Memoria/Netsync/NetSyncWorldWalk.cs (A0's pure core and proof: this file grows), NetSyncWorldFollow.cs and NetSyncWorldDot.cs (s165), NetSyncSocket.cs / NetSyncRelay.cs / NetSyncFrames (the wire), and the patches ${WT}\\memoria-patches\\s157*.patch (the 39-byte type-0 record), s163*, s164*, s165* for shape.
Laws learned this round (true; respect them): THE TRIGGER IS NOT THE CELL (a world entrance fires only on its event-id triangles); WORLD11's boat reads every Confirm on 9011 through an eager KEYON (one press is read by several entries); on the forced selftest role \`netsync bench 1\` (SpectatorField's bench term) holds the world freeze, not the bench host; A GAME PUBLISHES NOTHING DURING ITS OWN SYNC LOAD (a peer in its load keeps ARRIVING -- the writer re-sends its last slot -- with a frozen seq); THE PRE-INIT SAMPLE (judge a world after block_ready and advancing ticks).

THE CLONE: ${CLONE} (shared; THIS session holds it per the round queue). Engine source: ${CLONE}\\Assembly-CSharp = upstream 6b8bb2d5 + the stack s12..s165 + s166's A0 and A0b (uncommitted by design). The s166 delta: \`py ${SP}\\s166diff.py --stat\` / \`py ${SP}\\s166diff.py <path relative to Assembly-CSharp>\` (against the s165 snapshot). The clone AT THE A0b BUILD is snapshotted at ${SP}\\s166a0bbase: this workflow's own delta is the clone against it.

ENGINE RULES (non-negotiable):
- Tag every hunk: at least one ADDED line in each hunk carries \`[ff9mapkit netsync s166]\`.
- Keep each file's line endings exactly (check before editing: most netsync files are CRLF, HarnessAgent.cs is LF). Edit with the Edit tool or Python bytes I/O; NEVER a PowerShell text round trip. Never reformat untouched lines. Keep any BOM.
- Match the netsync idiom exactly (Int32/Byte[]/String/Boolean/Single, Log.Message("[NetSync] ..."), pure static rules with a selftest truth table and one-line mutants each proven caught BY ITS OWN ROW, comments that say WHY). Only C# features the surrounding code already uses.
- Compile ONLY with \`py tools/build_memoria.py --no-deploy\` from ${WT}. NEVER without --no-deploy. Never run restore/backup tools, never touch the game install, never launch the game or the in-game harness.
- The harness protocol stays 5 (keys additive; every new key at its sentinel in AppendNetsync's netsync-off catch literal with a history line). No new ini knobs.
- Never commit in the clone; never edit memoria-patches/*. Never throw from a per-frame or per-packet path (catch, log once per process). No allocation per frame where the surrounding code avoids it.
- Never break s144, s145, s154, s157 (the 39-byte record's every byte keeps its meaning), s163, s164, s165, A0, A0b. A v15 build must behave byte-identically to A0b on every path that does not read the trailer.
`

const KIT_TEST_RULES = `TEST SCOPE AND PROCESS (world-map and wire work: the world-map tests plus the wire's own; never the co-op suite; the nightly gate owns the rest):
- From ${WT}. THE W1 SET: ff9mapkit/tests/test_coop_peer.py, ff9mapkit/tests/test_coop_world_walk.py, ff9mapkit/tests/test_coop_world_follow.py, ff9mapkit/tests/test_coop_world_wait.py, ff9mapkit/tests/test_world_coop_harness.py, ff9mapkit/tests/test_harness_world.py, the tests that pin the s157 "39 B" record (find them: _climb_anim_judges / coop_climb_anim_peer's tests), plus THE SHARED-HARNESS PINS \`py -m pytest @${SP}\\hn_pins.txt -q -n 6\` (append the node id of any test you add or change in test_harness_netsync.py -- including the \`== 14\` wire pin).
- ONE pytest process at a time, never while its imports are being edited; long runs \`-n 6\` in the background to a log under ${SP}; iterate by node id / -k; a red that goes green alone on a quiet re-run is load noise (note it). Report each command, wall time, counts. Never leave a pytest or xdist worker running.`

const IMPL_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    files_touched: { type: 'array', items: { type: 'string' } },
    compile_ok: { type: 'boolean' },
    compile_tail: { type: 'string' },
    selftest_rows: { type: 'string' },
    sites: { type: 'array', items: { type: 'string' } },
    contract: { type: 'string', description: 'every harness key, field, op, reply text and log line this piece added, exactly' },
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
    compile_ok: { type: 'boolean' }, compile_tail: { type: 'string' }, summary: { type: 'string' },
  },
  required: ['findings', 'compile_ok', 'compile_tail', 'summary'],
}
const KIT_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' }, files_touched: { type: 'array', items: { type: 'string' } },
    tests_run: { type: 'string' }, tests_green: { type: 'boolean' },
    contract_assumptions: { type: 'array', items: { type: 'string' } }, open_issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'files_touched', 'tests_run', 'tests_green', 'contract_assumptions', 'open_issues'],
}
const K1_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' }, method: { type: 'string' },
    host_to_guest: { type: 'string', description: 'type-0 inter-arrival distribution per tape (median, p95, p99, max), loads excluded and included' },
    guest_to_host: { type: 'string' },
    send_rate_hz: { type: 'string' },
    gap_seed_ms: { type: 'integer', description: 'the recommended LaneGapStep threshold (design seed 1000)' },
    open_issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['summary', 'method', 'host_to_guest', 'guest_to_host', 'send_rate_hz', 'gap_seed_ms', 'open_issues'],
}

phase('K1')
const k1P = agent(`${CONTEXT}
YOUR STEP: K1, READ-ONLY (edit nothing; scratch under ${SP}\\w1k1). The type-0 inter-arrival times in both directions from the existing coop tapes (${'C:\\gd\\Dream-World-IX\\.harness-runs\\coop-tapes'} and the two-PC run folders under C:\\gd\\Dream-World-IX\\.harness-runs\\twopc-*), read with the kit's own tape reader (tools/harness/coop_peer.py and its tape format; read how it parses frames). Decision 6 seeds LaneGapStep's gap threshold at 1000 ms "set in K1 from the existing tapes' inter-arrival times"; the design also wants the real type-0 send rate (swap.slot.sends counts only the host's TypeState). Report per tape: the distribution (median, p95, p99, max) with the peer's own loads (a frozen seq while frames keep arriving, or a gap that straddles a field/world/battle load) shown separately, and a recommended seed that would not fire on ordinary jitter but would fire on the owner's ~2.3 s stalls. Return the K1 schema.`, { label: 'K1 inter-arrival', phase: 'K1', schema: K1_SCHEMA })

const kitP = agent(`${CONTEXT}
YOUR STEP: THE KIT WIRE LANE, Python only, in ${WT}. NEVER touch the clone. The design's "Tapes" and "Regression" paragraphs are your spec:
- tools/harness/coop_peer.py accepts wire 14 and 15 and, in EVERY mode (serve-guest, fake-guest-client, replay-host, the relay tap header), takes its SEND version from the first header the game sends or from the probed \`netsync.wire\`, never a constant (the design cites coop_peer.py:120, 160, 168, 602 at s165). \`replay-host --wire 15\` restamps byte 1 of every replayed frame (sound only under decision 2's law: a restamped v14 tape is exactly "a capless v15 host"); the tape header records the wire from the frames; \`where --pose\` parses the type-0 trailer when present (decision 4's table, little-endian) beside the s157 record; \`replay-host --freeze-at T --freeze-for N\` keeps the socket open and re-sends the last host frame byte-identical (the writer's real re-send); serve-guest's \`--no-follow\` sends trailer flags b0 clear; \`--gap-at\` for a gap in serve-guest's record. Serve-guest gains a walking v15 guest record mode (it may be a synthetic path over the ROAM route until the new tape is recorded -- say what you built).
- Every T2 leg asserts the live header version before judging (a v15 guest dropping every v14 frame reads "never pairs" -- a red easy to misread as a regression).
- The s157 "39 B" judges (_climb_anim_judges.py, coop_climb_anim_peer.py and their tests) are re-keyed to ">= 39 B carrying the s157 bytes" (the trailer rides type 0 on fields too). test_harness_netsync.py's \`== 14\` wire pin, test_coop_peer.py's v14 vectors and fakegame's \`wire\` move to 15 BY STAGE: the kit must stay green against the deployed A0b (v14) AND against the coming v15 build -- key the pin on the engine stage the test reads (the clone's NetSyncWire.Version, the s166 patch's presence, or the probe), never a bare constant flip. Say exactly how each pin decides its stage.
- Do NOT build the round-A bench rows or the stand-in's trailer model (the next workflow does, with the engine's final contract).
${KIT_TEST_RULES}
Return the KIT schema (contract_assumptions: every engine name/shape your code assumes -- the trailer layout, the version byte offset, the header shape).`, { label: 'kit wire lane', phase: 'Kit', schema: KIT_SCHEMA })

const k1 = await k1P

phase('Engine')
const e1 = await agent(`${CONTEXT}
K1 (the inter-arrival evidence; use its gap seed): ${JSON.stringify(k1)}
YOUR STEP: ENGINE PIECE A1, THE PURE CORE (inert: nothing calls it from a live path yet, except the proof), in ${CLONE}\\Assembly-CSharp\\Memoria\\Netsync\\NetSyncWorldWalk.cs (A0's file grows; keep A0's KitCellCloseRule and its rows and mutants untouched). Build exactly the design's A1 list, each a pure static with its facts as plain values:
- the trailer codec (decision 4's table: build into a caller's Byte[] at an offset, no allocation; a forward parse that tolerates a longer future trailer and reads tfmt 0 / absent as "capless"; the world block valid only on place 4, zeroed elsewhere);
- LaneGapStep(now - lastArrival, now - lastSeqMove, lastPlace) (decision 6: GAP, HANG worded loading on place 2/3, the 250 ms counter, the 20-pair line budget; K1's seed);
- HostLineRule (decision 7: the four overlay states, keyed on the guest's trailer flags b0, recomputed every Update);
- GhostRule (decision 9: cheapest first, one why_not each, the walk set {9002, 9010, 9011}, my own freeze never hides a ghost);
- WorldBodyRule (decision 11: undressed -- the sender's own model; the dress map as data for later);
- the torus ease and the canonical-to-render map's pure parts (decision 10: torus-unwrapped deltas dx in [-768, 768), dz in [-640, 640), LerpRate 12, snap on first show / a jump over 64 u / a world change; the stall hold keyed on the sender's seq, _STAND at ~300 ms, hide at 5 s; timing by the ms stamp);
- BenchPathPose (the bench host's \`host path\` pose at a time);
- the scene-bit rule (decision 4's b6: control off or the walker hidden for over 500 ms, not counting the own full map, a fade, or the ~ menu's hold);
- the caps word and the peer-version compare (decision 2, 3).
One proof line \`world walk selftest: OK (N rows, M mutants)\` (A0's line: it now counts A0's and A1's rows together; keep its text), run in the selftest proof block on a field. The design's A1 mutants (each caught by its OWN row): the gap line keyed on the stamp, the hold keyed on rs.Valid, a render-space ease, a naive canonical lerp across the seam, the ghost on another world by [102], a Field carrying a world id, the dress map defaulting to 310 on 9002, a mint on a stale w_blockReady while on a field, the host's ghost term read from state b0 (it must fail the released-guest row), the scene bit counting the ~ menu's hold -- plus any your rules need. Compile with --no-deploy until clean. Return the IMPL schema (contract: the codec's exact offsets and every rule's signature).`, { label: 'engine A1 core', phase: 'Engine', schema: IMPL_SCHEMA })
if (!e1) throw new Error('A1 failed')

const e2 = await agent(`${CONTEXT}
A1 is built (its report: ${JSON.stringify(e1)}).
YOUR STEP: ENGINE PIECE A2, WIRE v15, in the clone (NetSyncSocket.cs, NetSyncRelay.cs, NetSyncFrames and the transports; NetSyncClient.cs only for the own-wire line at transport start and the peer-version publish): decision 2 (NetSyncWire.Version 14 -> 15, alone; the caps word), decision 3 (count frames whose magic is right and whose version differs; ONE line per process and peer version "the partner's engine speaks wire 14, this one speaks 15 -- update both machines" and the owner-visible words "Your partner's co-op version doesn't match yours: update both games." as an overlay state for A3 to show -- expose it, do not draw it yet; publish \`netsync.wire_peer\` {rejected, last_version, ...: define it and state it in the contract}; TCP redial lines dedupe to one per break reason; every transport start logs its own wire in one line), and decision 4's TRANSPORT part: the trailer travels through \`INetTransport.SetLocal\` in BOTH transports (the relay's SetLocal, the TCP path) as extra bytes after the 39-byte record -- the s157 record byte-identical, Field stays 0 on the world map; the relay constructor's 65535 sentinel is built WITH a trailer (tfmt 1, own caps, place 0, the world block zeroed) via A1's codec; the receive side parses forward (A1's parse) and exposes the trailer and the arrival tick on RemoteState (NetSyncFrames' _remoteTick as an arrival tick) WITHOUT anything reading it yet beyond the harness keys you add. Until A3 builds a real trailer at the one SetLocal site, the SetLocal sites send a capless trailer (tfmt 0) or none -- say which, and why it is byte-safe for an A0b peer of the SAME v15 build (there is none: v15 rejects v14 entirely) and for the coming A3.
Also: the selftest role has no socket; do not build its slot here (A3 does).
Compile with --no-deploy until clean. Return the IMPL schema (contract: every key, field, log line).`, { label: 'engine A2 wire', phase: 'Engine', schema: IMPL_SCHEMA })
if (!e2) throw new Error('A2 failed')

const r = await agent(`${CONTEXT}
YOUR STEP: an ADVERSARIAL REVIEW of A1 + A2 together (the delta against ${SP}\\s166a0bbase), then FIX every confirmed finding yourself and recompile until clean. Reports (orientation only; verify everything): A1 ${JSON.stringify(e1)}; A2 ${JSON.stringify(e2)}.
Hunt for:
- THE WIRE: every v14 byte's meaning kept (the 39-byte record, every other type and section); Field never a world id; the version gate rejects v14 both ways and counts it once per process + version; a longer future trailer parses; a short or corrupt trailer never throws and reads capless; the relay sentinel carries a trailer; the arrival tick refreshes on every TypePos frame including same-seq re-sends (decision 5's two clocks depend on it); no allocation per packet beyond what the transports already do; TCP redial line dedupe.
- REGRESSIONS: diff every changed function's old vs new behaviour for a v15 peer pair on a field, in a battle, on the world map, through a redial, a host epoch change, the title, a session edge; s157's twin clips and ghost frame, s160's chest relay, s161's ATE relay, s163's speed mirror, s164's swap record, s165's world follow-out and dot, A0, A0b.
- the pure core: each rule against the design's decision text; the torus ranges; the stall timings by stamp, never ticks; the scene bit's exclusions; GhostRule's order and the walk set; apply 4 mutants mentally and name the catching row; the proof line text.
- the harness: keys exactly as the contract says, sentinels in the catch literal (extract and parse it as JSON), protocol 5.
- every hunk tagged; line endings; the csproj (no new file expected in W1 unless the implementer added one).
Compile with --no-deploy. Return the REVIEW schema.`, { label: 'review A1+A2', phase: 'Engine', schema: REVIEW_SCHEMA })

const kit = await kitP

phase('Reconcile')
const rec = await agent(`${CONTEXT}
YOUR STEP: RECONCILE the kit wire lane with the final A1+A2 engine, then the offline tests once. Engine: A1 ${JSON.stringify(e1)}; A2 ${JSON.stringify(e2)}; review ${JSON.stringify(r)}; kit lane ${JSON.stringify(kit)}.
1. Grep the clone for every name and shape in the engine contracts and the kit's contract_assumptions (the version byte, the trailer offsets and tfmt, the header, netsync.wire / netsync.wire_peer, the own-wire and peer-version log lines). Fix the KIT side wherever it disagrees; report (do not edit the clone) if the engine is wrong against the design.
2. Check every stage-keyed pin decides correctly for BOTH the deployed A0b (v14) and the v15 clone.
3. The final offline pass ONCE, nothing being edited: THE W1 SET, whole files, plus the shared-harness pins -- \`-n 6\` in the background to a log under ${SP}. Fix kit-side failures you caused; re-run only those node ids.
${KIT_TEST_RULES}
Do NOT commit, deploy or launch the game. Return the KIT schema.`, { label: 'reconcile W1', phase: 'Reconcile', schema: KIT_SCHEMA })

return { k1, a1: e1, a2: e2, review: r, kit, reconcile: rec }
