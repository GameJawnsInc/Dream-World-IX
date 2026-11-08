export const meta = {
  name: 's168-w2-kit-bench',
  description: 's168 W2: sync the design to the as-built engine, then the kit (twins, coop_peer b3 + section 12, pins), the GM0 bench legs, regression re-keys, runners, texts, a critic, the reconcile',
  phases: [
    { title: 'Sync', detail: 'S168-DESIGN.md amended to the as-built engine' },
    { title: 'Kit', detail: 'battlewire twins, coop_peer, fakegame guestmenu rung, pins' },
    { title: 'Bench', detail: 'solo legs, duo/T2 legs, regression re-keys + runners + texts' },
    { title: 'Critic', detail: 'every row can fail; completeness; fixes' },
    { title: 'Reconcile', detail: 'kit vs the engine clone; the domain tests once' },
  ],
}
const WT = String.raw`C:\gd\Dream-World-IX\.claude\worktrees\s166-handoff-575aeb`
const SP = String.raw`C:\Users\skaki\AppData\Local\Temp\claude\9e463cf4f0985362\110b1b95-e2da-4a85-ab88-e0d8756cb21a\scratchpad`
const CLONE = String.raw`C:\gd\FFIX\Memoria`
const CONTEXT = `
You are building the KIT and BENCH side of round s168 of the ff9mapkit netsync co-op stack: the co-op GUEST's stock main menu, rung 0 (view-only), over a seated
copy of the host's party (wire v15 cap b3; host section 12).
THE ENGINE IS BUILT AND REVIEWED in the clone ${CLONE}\\Assembly-CSharp (s158..s167 + the s168 delta, uncommitted by design; NOT deployed -- the live game runs
s167 and stays so until the owner's s167 two-PC look). THE CONTRACT (every rule, harness key/field, op, reply, log line, owner-visible line) is in the builders'
reports: ${SP}\\s168_w1p1.json (keys ab, core, harn, wire), ${SP}\\s168_w1p2.json (keys e, f, g, h, i; 'i' holds the FINAL contract) and ${SP}\\s168_w1review.json
(the review's four fixes, key 'fix': W1 the pairOn term in GuestMenuKeyStep, CR-2 NotPairedLineRule, CR-3 the outside_settled/uid0_vars/sysvar192 keys, LC1
CutMemoryRule). The delta: \`py ${WT}\\studies\\field-coop\\s168\\s168diff.py --stat\` and \`... <path rel to Assembly-CSharp>\`. Offline proofs: 'guest menu
selftest: OK (420 rows, 249 mutants caught)', 'seat bracket selftest: OK (19 rows, 7 mutants caught)', 'world walk selftest: OK (534 rows, 198 mutants)'.
THE DESIGN: ${WT}\\studies\\field-coop\\S168-DESIGN.md -- decisions 1-21 (s168), 31-35 (the harness: levers, keys, the fingerprint, the proof, what each harness
proves), "The bench" (the GM0-* rows with OLD/NEW/LEVER, harness S/D/T/O, THE CAL RULE, the regression set, the Order), "Known limits", "Cut in round 3".
THE TEMPLATE: s167's kit/bench round -- ${WT}\\studies\\world-coop\\s167\\s167-w2-wf.js (its steps and laws), the runners studies\\world-coop\\s167\\round_b_*.sh and
round_b_lib.sh, the scenarios studies\\test-harness\\scenarios\\coop_world_walk.py / coop_world_walk_t2.py, _coop_peer_bench.py, the kit harness tools\\harness\\
(battlewire.py, coop_peer.py, fakegame.py, duo.py, instance.py), the tests ff9mapkit\\tests\\test_harness_netsync.py, test_coop_peer.py, test_coop_world_walk*.py.
RULES: Never launch the game, never deploy, never run a bench or the in-game harness, never edit the engine clone or memoria-patches/. Never start a netsync HOST
role or listen on Any in any test (client vs a loopback listener only). Keep each file's line endings (check first; *.sh are LF). No PowerShell text round trips;
write backslash-heavy files with the Write tool. The harness protocol stays 5. Kit twins pin the C# (constants, rule tables) and are evaluated against the C# proof's
own rows where the pattern exists (_run_cs_rows). Every NEW bench row has OLD (s167) / NEW / LEVER and a way to fail. Do not run the full test suite: only the test
files you touch plus the W2 kit set (the reconcile runs them once). Report deviations; never silently redesign.
`
const KIT = { type: 'object', properties: {
  summary: { type: 'string' }, files_touched: { type: 'array', items: { type: 'string' } }, tests_run: { type: 'string', description: 'commands, wall times, counts' },
  contract_used: { type: 'string' }, deviations: { type: 'array', items: { type: 'string' } }, open_issues: { type: 'array', items: { type: 'string' } } },
  required: ['summary', 'files_touched', 'tests_run', 'contract_used', 'deviations', 'open_issues'] }
const carry = (o) => JSON.stringify(o ? { summary: o.summary, files: o.files_touched, deviations: o.deviations, open: o.open_issues } : null).slice(0, 7000)

phase('Sync')
const sync = await agent(`${CONTEXT}
YOUR STEP: SYNC THE DESIGN TO THE AS-BUILT ENGINE. Read every 'deviations_from_design' and 'open_issues' entry in s168_w1p1.json and s168_w1p2.json and the review's
four fixes. For each deviation that changes what the design says (a rule's shape, a term, a key/field name, an op, a proof line, a pin name, a site), amend
${WT}\\studies\\field-coop\\S168-DESIGN.md: correct the passage in place where the spec is now wrong (e.g. decision 6's pseudo-code gains the review's pairOn:
'loading && FeatureOn(b3) -> GuestQuiet'; decision 10 ratifies where state 29 sits in each overlay chain and that the connecting line outranks it; GM0-WORLDTAG4's
judge uses outside_settled / uid0_vars / sysvar192; the new 'seat bracket selftest' proof line; KeyGuestOpen/KeyGuestQuiet = MenuKeyGuestOpen 5 / MenuKeyGuestQuiet 6;
the pin set names and sha; the lever object; the final key list), and add a section '## As built (s168 W1, 2026-11-07)' that lists, one line each, every deviation
kept and why, the final proof counts, the pinned W1a/b artifact (backups/*.pin-s168w1ab.20261107-001809, DLL sha 532486364ec05354), and every owed item (kit
twins, re-keys, bench rows changed). Keep the doc's plain style, CRLF endings and structure; do not touch "The owner's calls" except to add a ratification line where
a coordinator call changed. Return the KIT schema (files_touched = the doc).`, { label: 'sync the design', phase: 'Sync', schema: KIT, model: 'opus' })

phase('Kit')
const kit = await agent(`${CONTEXT}
Design sync report: ${carry(sync)}
YOUR STEP: THE KIT CORE. (1) battlewire.py: twins of every s168 constant and pure rule the bench reads or decodes (the caps word incl. OwnCapsRule's two arguments,
CapGuestMenu, section 12's byte layout and its pure readers, the witness components, the close-trigger ids and causes, the guest-menu why codes and verdict names
incl. MenuKeyGuestOpen/Quiet 'guest', the line words, the fingerprint component names, the press-deadline rule, CutMemoryRule, PairOnRule), pinned to the C# by
reading it (the existing twin-pin pattern; _run_cs_rows against the guest menu proof where it fits). (2) coop_peer.py: serve-guest's 'auto' caps also adopt b3
from the host (today only b1); the section-12 decoder in dump/replay; replay-host carries a v15 tape's section 12 as recorded; a fake guest can declare b3.
(3) fakegame.py: a 'guestmenu' rung modelling the ENGINE (the selftest role never mirrors) with the design's faults (capture_leak, restore_skip, cut_ignored,
leave_ignored, pause_closed, caps_ignored, slot_keyed, own_values, and any the as-built contract adds). (4) Pins and re-keys the engine changed: the proof tallies
(guest menu 420/249, seat bracket 19/7, world walk 534/198) wherever the kit pins proof lines; test_harness_netsync.py's netsync.guestmenu key + catch-literal
sentinel checks; the s167 caps rows decision 32 lists (test_coop_world_walk_b.py, fakegame, battlewire ww_own_caps_rule, lane.caps.own and CAPS_S167 re-keyed BY
STAGE: 0x0B on an s168 stage, 0x03 under guestmenu caps off, 0x01 under fp off) -- never weaken a row, re-key it by stage. Tests for everything you add. Return KIT.`,
  { label: 'kit core', phase: 'Kit', schema: KIT, model: 'opus' })

phase('Bench')
const solo = await agent(`${CONTEXT}
Kit core report: ${carry(kit)}
YOUR STEP: THE SOLO (S) AND OFFLINE (O) GM0 ROWS. A new scenario studies\\test-harness\\scenarios\\coop_guest_menu.py (legs selected by COOP_GM_LEG, the
coop_world_walk.py pattern: solo_ini guarding Memoria.ini, benchguard, the pre-init sample law, CAL rows) implementing every GM0 row the design marks S (and O rows as
offline tests): open/browse/refuse per census site, the seat and fp_before/fp_after/seat_fp, the door pass/fail/fault, the witness frames, the chip, the closes the
selftest role can fire (fireclose, close fault), the held key, release, the master-skip and achievement hold, the outside fingerprint, WORLDTAG4 (outside_settled,
uid0_vars, sysvar192), each with its OLD (the s167 DLL: verb unknown, key absent -> 'not reached'), NEW and LEVER prediction, and a stand-in (fakegame) test for each
leg where the stand-in can model it, with the faults proving each row can go red. Selftest rows prove the ACTION only (label them). Return KIT.`,
  { label: 'bench: solo + offline legs', phase: 'Bench', schema: KIT, model: 'opus' })
const duo = await agent(`${CONTEXT}
Kit core: ${carry(kit)}\nSolo legs: ${carry(solo)}
YOUR STEP: THE DUO (D) AND T2 (T) GM0 ROWS. A new scenario coop_guest_menu_duo.py (the coop_world_walk_t2.py / coop_field_swap_timing_duo.py patterns: duo.py two
instances, bridge ports clear of the excluded range, a lever any-role where the duo needs it, THE DUO CANNOT PULL A SELFTEST-ROLE LEVER) for every D row: the real Menu
key path for a mirroring guest, both forced closes (leave, cut incl. the BOOTING report and no-boot cut, out, rejoin, world, title, scene, ending), the ramp settle legs,
the quit-confirm wait, GM0-BW/frame size, GM0-STSCENE (does the host's own world menu raise StScene: measure), GM0-HUDSTRIP's known-limit row on a kit strip field,
the caps-off older-partner rows, the restore fingerprint after each close. T rows: what a tape can prove (replay-host carrying section 12; a recording plan for a
b3 tape in coop_tape_record.py, owner-gated like the ROAM tape: the bridge down, the owner's go). OLD / NEW / LEVER each; stand-in tests where possible. Return KIT.`,
  { label: 'bench: duo + T2 legs', phase: 'Bench', schema: KIT, model: 'opus' })
const regr = await agent(`${CONTEXT}
Kit core: ${carry(kit)}\nSolo: ${carry(solo)}\nDuo: ${carry(duo)}
YOUR STEP: REGRESSION RE-KEYS, RUNNERS, TEXTS. (1) Re-key by stage, never weaken: coop_world_walk.py PR-SAVEMENU (press.now gains 'guest' only when
netsync.guestmenu is present), coop_field_swap_timing_duo.py MENU_PRE_OK, _coop_peer_bench.STAGE_KEYS gains the s168 stage key, and every other row the design's
decision 32 re-key list names; coop_cut_hold.py's s121 leg stays untouched (it IS the older-peer fallback row). (2) Runners modelled on studies\\world-coop\\s167\\
round_b_lib.sh + round_b_{old,new,lever,regress,rerun}.sh: studies\\field-coop\\s168\\round_gm_lib.sh and round_gm_{old,new,lever,regress,rerun}.sh (benchguard,
FF9 closed, the owner's bridge down for T2, a DLL pin check -- OLD on s167 12be3220520813a6, the bracket legs on the pinned W1a/b DLL 532486364ec05354, NEW on the
s168 build --, a cutoff before the 03:00 gate, duo ports clear of the excluded range, the regression set incl. round B's legs, the diorama legs B3-B5, coop_stock_menu,
s164's Pause MENU legs and coop_cut_hold's s121 leg) -- written, NOT run. (3) Texts: ff9mapkit coop.py GUEST_TERMS and the co-op tutorial words updated behind the caps
condition ('when both builds have it'), health.NETSYNC_GENERATIONS gains an s168 marker string the engine actually contains (grep the clone for a stable literal),
with fence tests. Tests for every file you touch. Return KIT.`, { label: 'bench: regression, runners, texts', phase: 'Bench', schema: KIT, model: 'opus' })

phase('Critic')
const critic = await agent(`${CONTEXT}
Reports: sync ${carry(sync)}\nkit ${carry(kit)}\nsolo ${carry(solo)}\nduo ${carry(duo)}\nregr ${carry(regr)}
YOUR STEP: THE CRITIC. (a) Every GM0 row in the design exists in a scenario (or is explicitly O/offline or deferred with a reason); list any missing. (b) Every NEW row
can go red: name its lever or fault, and check the fault is wired (a check that cannot fail is a defect). (c) Every kit twin matches the C# (re-read the C#). (d) Every
regression re-key is by stage and weakens nothing. (e) Selftest rows never claim a key path or a trigger. (f) The runners never deploy, never run under a test suite,
and pin the right DLL per stage. Fix confirmed gaps in the kit/scenarios/runners/tests (not the engine, not the design except a factual correction). Return KIT
(open_issues = what stays a known gap).`, { label: 'critic', phase: 'Critic', schema: KIT, model: 'opus' })

phase('Reconcile')
const rec = await agent(`${CONTEXT}
Critic: ${carry(critic)}
YOUR STEP: RECONCILE. Re-read the final kit against the engine clone once more (constants, key names, op names, usage strings, the catch literal), then run the W2 kit
test set ONCE in the worktree: every test file touched in this workflow plus test_harness_netsync.py, test_coop_peer.py, test_coop_world_walk*.py,
test_world_coop_harness.py and the coop.py/coopdoc tests (\`py -m pytest -q -n 6 <files>\` from ${WT}\\ff9mapkit; a timing red is re-run alone before you call it).
Fix any red the kit caused. Do NOT commit, deploy or launch the game. Return KIT (tests_run: the commands, wall times and counts; open_issues).`,
  { label: 'reconcile', phase: 'Reconcile', schema: KIT, model: 'opus' })
return { sync, kit, solo, duo, regr, critic, rec }
