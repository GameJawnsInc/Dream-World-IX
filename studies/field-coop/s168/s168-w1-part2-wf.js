export const meta = {
  name: 's168-w1-part2',
  description: 's168 engine part 2 (no-deploy): W1e gate seam + who + words, W1f seat/door/restore, W1g confirm census, W1h forced closes, W1i remaining ops',
  phases: [{ title: 'Gate', detail: 'W1e' }, { title: 'Seat', detail: 'W1f' }, { title: 'Census', detail: 'W1g' }, { title: 'Closes', detail: 'W1h' }, { title: 'Ops', detail: 'W1i completion' }],
}
const WT = String.raw`C:\gd\Dream-World-IX\.claude\worktrees\s166-handoff-575aeb`
const SP = String.raw`C:\Users\skaki\AppData\Local\Temp\claude\9e463cf4f0985362\110b1b95-e2da-4a85-ab88-e0d8756cb21a\scratchpad`
const CLONE = String.raw`C:\gd\FFIX\Memoria`
const CONTEXT = `
You are building round s168 of the ff9mapkit netsync co-op stack for the FF9 Memoria engine: the co-op GUEST's stock main menu, rung 0 (view-only).
THE SPEC is ${WT}\\studies\\field-coop\\S168-DESIGN.md (binding; reviewed four rounds). Read its status, "What happens today", decisions 1-21 and 31-35, "The
owner-visible words", "The engine pieces" (W1e-W1i are yours, in order), "Known limits" and "Departures from the skeleton" incl. "Cut in round 3" (those cut
mechanisms must NOT be built: no input swallow, no fade choice, no step 0, no door_unarmed, no per-trigger levers, no :889 narrowing, no re-seat, no state swap,
no frame big). s169 (decisions 22-30) is NOT built now.
PART 1 IS DONE AND GREEN (read its full report ${SP}\\s168_w1p1.json: keys ab, core, harn, wire; each has 'contract', 'deviations_from_design', 'open_issues'):
W1a+W1b (NetSyncSeatBracket.cs; NetSyncDiorama.BuildSeatMembers(ff9, seat, bracket, overrides, rethrow) with SeatOverride keyed by CharacterId), W1c (the pure
core in NetSyncGuestMenu.cs: GuestMenuKeyStep, GuestMenuWhyNot over GmFacts, the door rules, the section-12 codec and pure readers, the witness, the guard,
the close-trigger rule over GmCloseFacts, the close-order states, the restore identity rule, the press deadline; KeyGuestOpen=5 / KeyGuestQuiet=6 /
SectionMenu=12 live there), W1i skeleton (the netsync guestmenu sub-verb with old|act|caps|clear, HarnessReleaseGuestMenu, the netsync.guestmenu key with
lever as an object, the engine-stamped fingerprints StampFpBefore / StampSeatFp / StampFpAfter / StampHostFp, NoteOpen / NoteRefusal; each later lever goes in
THREE places: its op in HarnessLever's commented slot, its reset in ReleaseGuestMenuLevers + its term in HarnessReleaseGuestMenu's 'any', its field in the
lever object + its sentinel in AppendNetsync's catch literal), W1d (caps b3 spoken 0x0B; section 12 sent to a b3 following guest by HostGuestMenuSectionNow
in its own try; the frame-cap guard; frame keys). Proofs now: 'guest menu selftest: OK (271 rows, 137 mutants caught)', 'world walk selftest: OK (534 rows,
198 mutants)', 'seat bracket selftest: OK (19 rows, 7 mutants caught)'. The offline proof exe pattern: ${SP}\\s168proof\\w1d (read how it was built; extend it,
in a new subfolder per step).
THE CLONE: ${CLONE} (this session holds it). The s168 delta: \`py ${WT}\\studies\\field-coop\\s168\\s168diff.py --stat\` / \`... <path>\` (vs ${SP}\\s167base).

ENGINE RULES (non-negotiable):
- Tag every hunk: at least one ADDED line in each hunk carries \`[ff9mapkit netsync s168]\`.
- Keep each file's line endings and BOM exactly (netsync files CRLF; HarnessAgent.cs LF; check stock files before editing). Edit with the Edit tool or Python bytes
  I/O; NEVER a PowerShell text round trip. Never reformat untouched lines.
- Match the netsync idiom; pure rules get rows and one-line mutants in the guest menu proof (each caught by its own row). Only C# features the surrounding code uses.
- Compile ONLY with \`py tools/build_memoria.py --no-deploy\` from ${WT}. NEVER without --no-deploy. Never run restore/backup tools, never touch the game install,
  never launch the game or the in-game harness.
- Offline proof exes never construct NetSyncSocket(true, ...) or open a listener. Pure statics and stand-ins only.
- Harness protocol stays 5; every new key/field at its sentinel in the catch literal. No new ini knobs. Wire stays v15.
- Never commit in the clone; never edit memoria-patches/*, studies/* or Python. Never throw from a per-frame/per-packet path. No per-frame allocation where the
  surrounding code avoids it (the gatherers fill ONE reused GmFacts/GmCloseFacts instance; a press or a door allocates nothing).
- VANILLA SAFETY: with co-op off, for the host, for an unfollowed client and for any player not in a guest-menu seat, behaviour is byte-identical to s167. Under
  \`netsync guestmenu old\` every s121 read is s121 exactly. Every hook in stock UI code keys on the seat flag (or the guest-session read the spec names) FIRST and
  returns to the untouched stock path otherwise; wrap new code in stock files in try/catch where the spec says (the door, the close tick, the backstops).
- Report every deviation with its reason; never silently redesign; if the spec is wrong about the code, do the safest minimal thing and say so.
`
const IMPL = { type: 'object', properties: {
  summary: { type: 'string' }, files_touched: { type: 'array', items: { type: 'string' } }, compile_ok: { type: 'boolean' }, compile_tail: { type: 'string' },
  proof: { type: 'string' }, contract: { type: 'string' }, deviations_from_design: { type: 'array', items: { type: 'string' } }, open_issues: { type: 'array', items: { type: 'string' } } },
  required: ['summary', 'files_touched', 'compile_ok', 'compile_tail', 'proof', 'contract', 'deviations_from_design', 'open_issues'] }
const carry = (o) => JSON.stringify(o ? { summary: o.summary, contract: o.contract, deviations: o.deviations_from_design, open: o.open_issues, proof: o.proof } : null).slice(0, 9000)

phase('Gate')
const e = await agent(`${CONTEXT}
YOUR STEP: W1e, THE GATE SEAM, WHO, THE WORDS (decisions 6, 7, 8's live gatherer, 9's press half, 10; "The engine pieces" W1e). UIKeyTrigger.cs's scene-branch Menu
arm ONLY (the s38 gate + s121 branch; the dialogue path's Menu read stays byte for byte): the press pre-check through GuestMenuKeyStep with the live GmFacts
gatherer (decision 8's terms from the live reads the spec names; fill F2/term-11 and F3-F4/'scene' from the same reads), RefuseAudible -> RefuseMainMenu(why)
(NetSyncField: a new overload that takes the verdict as given, beside the byte-identical parameterless s121 entry), GuestOpen -> stock OnKeyMenu with the press
deadline stamped (decision 9), a press while UIManager.IsLoading -> stock OnKeyMenu (silent), and a fault inside a guest press -> RefuseAudible('fault') while a
fault before guestSession is known takes s121's read exactly (decision 6). Expose MenuKeyGuestOpen in NetSyncField and HarnessMenuKeyNow's 'guest' name. The why
classes in the DeclineOnce book. The guest words (decision 10): overlay state 29 (the timed refusal line, selected in the paired branch too, ended at scene
changes as the spec says, never outranking the wire-mismatch/reconnecting/lost-contact lines), the 'View only' chip beside DrawDialogChip (shown while seated),
the forced-close line drawn by OnGUI on its own 4 s timer (W1h will arm it; build the drawer and its arm function now). Add rows/mutants for the press step and
the word selection. Compile --no-deploy; re-run the offline proofs. Return the IMPL schema.`, { label: 'W1e gate + who + words', phase: 'Gate', schema: IMPL, model: 'opus' })
log(`W1e compile_ok=${e && e.compile_ok}`)

phase('Seat')
const f = await agent(`${CONTEXT}
W1e report: ${carry(e)}
YOUR STEP: W1f, THE SEAT, THE DOOR, THE RESTORE (decisions 9's door, 11-16, 33; "The engine pieces" W1f). UIManager.ChangeUIState's door: the ONE open verdict for
every FieldHUD/WorldHUD -> MainMenu entry while guestSession holds and the lever is not 'old' (the :889 route, WorldHUD's entry and a script's OpenMainMenu
included), in its own try with the door's fault path (decision 9); pass = the seat (decisions 12-14: one fresh frame's sections 1/2/3/12 through the pure
readers, the witness, BuildSeatMembers with the section-12 overrides and rethrow, the menu's OWN NetSyncSeatBracket instance, seat by reference -- scratch
PLAYERs, a fresh List<FF9ITEM> in host order, fresh rare sets, gil by value --, ALL-OR-NOTHING with its own fault path and the 'seat fault <component>' lever;
EnabledSubMenus = {Item, Ability, Equip, Status, Folklore}; StampFpBefore before installing, StampSeatFp after, NoteOpen at a pass; the session begins at the
seat); fail = buzz, the why's line, the HUD's own Show (GetSceneFromState(this.state).Show(null)), NoteRefusal. The restore at the one door (leaving the menu
family, read from this.state before the prevState assignment), onto the same FF9StateGlobal with no deserialization since the seat (JsonParser's load epoch),
element-wise, idempotent, cleared in a finally, EnabledSubMenus cleared, StampFpAfter, the session's clear points exactly as decision 16 lists them; the
backstops: SceneDirector.Replace (restores and ends the session; Replace('Title') quietly, other targets with the alarm), the ramp's fire (QuitScene.Hide() if
the prompt is up, then the restore, both in one try that always falls through to ExitMirrorToOwnSave; quiet under ramp_quit), the Alt+F9 load entry (restores and
ends the session). While seated (decision 14): MainMenuUI.Show skips SetMasterSkill (count master_skipped); AchievementManager holds reports; the autosave
ladder's seat term (the ONLY save-gate edit: cut 12); LiveSlotChars reads the seat record's real refs; the diorama's Boot refuses while a seat is held (in Boot's
own refusal, NOT MayBoot: decision 14) and the open refuses while a diorama is Booted/Armed/returning. The bench sources for the 'frame' op (the _gmBenchFrame slot
and the bag/key-items/rare_item_used/gil seams beside SlotSource; decision 31) and the 'frame', 'frame witness ...', 'seat skip party', 'restore skip <c>', 'seat
fault <c>', 'door fault open|restore' ops through the three-place lever pattern. Proof rows: the two-marker seat round trip, the clear points, the restore identity,
the door rules as wired. Compile --no-deploy; re-run proofs. Return the IMPL schema.`, { label: 'W1f seat + door + restore', phase: 'Seat', schema: IMPL, model: 'opus' })
log(`W1f compile_ok=${f && f.compile_ok}`)

phase('Census')
const g = await agent(`${CONTEXT}
W1e: ${carry(e)}\nW1f: ${carry(f)}
YOUR STEP: W1g, THE RUNG-0 CONFIRM CENSUS (decision 17 as it stands after the cuts). EquipUI.cs, AbilityUI.cs (BOTH support handlers, OnKeyConfirm and
OnKeySpecial, and the field-ability target confirm), ItemUI.cs (item use and Gysahl) at the spec's sites: each hook keys on the SEAT FLAG ALONE, sits above
the first state write and above ImpactfulActionCount++, and reuses the screen's own neighbouring stock 102 branch at the same depth (no tween, no group
change), counts refused + last_site/last_screen, and stays inert under the 'capture off' lever (the three-place pattern; capture off = the stock bodies run into
the SEATED copy). Order/Party/Card/Config are greyed by EnabledSubMenus (W1f) -- verify the greying in code. Item sort and the key-item/Folklore read markers stay
live on the copy. The census classifier rows per site in the proof (decision 34), and the outside-state fingerprint fold for GM0-OUTSIDE (fp.outside_equal over
gEventGlobal, the Achievement/EventState counters, MiniGame cards, hintmap_id) if not built. Compile --no-deploy; re-run proofs. Return the IMPL schema.`,
  { label: 'W1g confirm census', phase: 'Census', schema: IMPL, model: 'opus' })
log(`W1g compile_ok=${g && g.compile_ok}`)

phase('Closes')
const h = await agent(`${CONTEXT}
W1e: ${carry(e)}\nW1f: ${carry(f)}\nW1g: ${carry(g)}
YOUR STEP: W1h, THE FORCED CLOSES (decisions 16 (clear points), 18-21 as they stand after the cuts; "The engine pieces" W1h). CoopCloseGuestMenuIfDue(site) in
its OWN try (never throws), asked FIRST at every waiting site the spec lists (the ramp's arm outside the settle's try, THE RAMP'S SETTLE's two terms -- the world
branch's seat term and the press-deadline term on both branches --, the battle cut at the top of DioramaTick's live-nonce branch before the skip check, the boot
report's BUSY while the quit prompt holds the close and BOOTING while a close is in flight for the nonce (decision 19), the serial and intent field follows, the
world follow-out, WorldFollowFire, the world-to-world close in WorldLaneStep, the relayed talk/chest/ATE starts and b0 HfScene for my field (the owner's
'close on a host scene'), the host at the title (section 7 b7), ApplyConfigChange's explicit 'ending' request). The close's service tick after
ServiceFollowWarp/ServiceWorldOut and before the enabled gate, no role test, in its own try with the guarded fault end and closes.faults; THE CLOSE ORDER LAW
with stock's two fade forms (root: stock root-Cancel statements with NeedTweenAndHideSubMenu = true BEFORE the Hide; below MainMenu: ItemUI.WaitForFade's form),
the quit wait (watchdog paused), the Loading wait, Memoria's control panel step, the WATCHDOG (deadline stamped at the request incl. the fades; sweep in the menu
family, the HUD's own Show on a HUD state), the held-bit write into ETb.sKey before EVERY route that ends a seat at the HUD; one line + harness keys per close
(closes.<id>, last_close.cause); the forced-close line armed (W1e's drawer); ONE lever 'guestmenu close old|act' plus 'fireclose <id>' and 'close fault <step>'
through the three-place pattern; per-trigger proof mutants. NetSyncAte.cs's ATE site. Compile --no-deploy; re-run proofs. Return the IMPL schema.`,
  { label: 'W1h forced closes', phase: 'Closes', schema: IMPL, model: 'opus' })
log(`W1h compile_ok=${h && h.compile_ok}`)

phase('Ops')
const i = await agent(`${CONTEXT}
W1e: ${carry(e)}\nW1f: ${carry(f)}\nW1g: ${carry(g)}\nW1h: ${carry(h)}
YOUR STEP: W1i COMPLETION. Compare decision 31's lever/op list and decision 32's key list against what W1d-W1h actually built (HarnessAgent.cs, NetSyncGuestMenu.cs,
the release chain). Build every op and key field the spec lists that is still missing for s168 (s169's apply/check are NOT built: leave their reserved slots), each
through the three-place pattern; make HarnessReleaseGuestMenu return every s168 lever to its default and log when any was set (GM0-RELEASE); make sure the
'lever' key reports every lever; check every key field has its sentinel in the catch literal and a history line names the s168 additions (the new proof lines
included). Then a consistency pass over the WHOLE s168 delta (s168diff.py): every hunk tagged, line endings kept, no cut mechanism built, no s169 mechanism built,
every proof line current. Compile --no-deploy; run every offline proof (guest menu, world walk, seat bracket) and report exact N/M. Return the IMPL schema with the
FINAL s168 contract: every op, key field, log line and owner-visible line.`, { label: 'W1i completion + consistency', phase: 'Ops', schema: IMPL, model: 'opus' })
return { e, f, g, h, i }
