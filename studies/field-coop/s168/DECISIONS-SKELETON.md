> The coordinator's binding skeleton for `../S168-DESIGN.md` (2026-11-06), kept as written. The design supersedes it;
> its Departures section lists every deliberate change.

# s168/s169 guest main menu -- the coordinator's decision skeleton (binding for the design writer)

Sources: the study `studies/field-coop/GUEST-MENU.md` (owner decisions 2026-10-31, cite them BY NAME, never by number:
the study has two numberings), the grounding `gm_ground.json` (eight lanes + a completeness critic; the critic's
verdicts on contradictions are adopted below), and the owner's answers of 2026-11-06 (marked OWNER 11-06).

## Rounds
- s168 = rung 0 (view-only). s169 = rung 1 (support abilities). Each is built, deployed and benched ALONE.
- OWNER 11-06: s168 is built now with `--no-deploy` (engine + kit + offline proofs), and deployed/benched in game only
  AFTER the owner's s167 two-PC look. If that look needs an s167 engine fix, the fix lands first and s168 rebases.
- s168 takes the clone under a TAKING THE CLONE line in the round queue when its engine edits start.

## D1 Wire: v15, no bump
- The menu is an additive v15 feature gated on the PEER's cap b3 (`CapGuestMenu` 0x08, NetSyncWorldWalk.cs), per
  S166-DESIGN decision 2. s168 speaks 0x0B (b0|b1|b3); `guestmenu caps off` speaks s167's 0x03 exactly; `worldwalk fp off`
  keeps its meaning. FeatureOn(own, peer, b3) is re-read every Update and never latched; every gate also needs a LIVE peer
  (caps outlive the peer: the cache is held past the 2 s cliff).
- Off (an older partner build, or the lever) = s121's refusal exactly (keys, count, log line), PLUS the owner's on-screen
  refusal line (D7) naming an older partner build. The existing caps line already names "guest menu".
- ONE wire registry, written into memoria-patches/README.md and the S166 decision-2 bit list before code:
  section 12 = the guest-menu block (host->guest, s168); section 13 = the menu answers (host->guest, s169); type 8 = the
  shared guest->host ring (s169; COMMS-MENU sec 4 updated to it: variable-length entries, a kind per feature, each kind
  gated on its own cap bit, epoch u16 + seq u16); trailer flags b1..b7 stay ZERO (no role-dependent meaning: the critic
  refuted both proposed b1 uses). The quit word (GUEST-TRAVERSAL item 15) takes the next free id when it is designed.

## D2 When the menu data is sent
- Section 12 rides EVERY state frame to a b3 following guest (FpSectionSendRule pattern), not request/reply: the seat
  happens at the door and MainMenuUI.Show reads the party synchronously, so the data must already be in hand; a tape can
  replay it (replay-host never answers a request); the open is instant.
- Cost: state the measured-on-paper size (per member preset/category/exp/capa/pa u16 x preset length; gil; rare_item_used)
  and the re-send rate (the frame is rebuilt every 150 ms and re-sent every ~33 ms write tick). FRAME-CAP-GUARD: never
  append 12 (or 13) past NetSyncWire.MaxPayload 8192: drop the SECTION with one line per process and a counter, never the
  frame. The guest then refuses the open ("the menu data did not arrive"). A bench row reports the frame size worst case.
- Body (rung 0): [fmt u8=1][policy u8: all bits reserved zero in s168, b0 reserved for a future host off switch]
  [applyMask u8: zero in s168; s169 sets b0 = SA sets][gil u32][usedN u16][rare_item_used u16 x usedN][memberN u8<=4] x
  [charId u8][presetId u8][category u8][exp u32][basisCapa u32][paN u8][pa u16 x paN, clamped].

## D3 The gate seam
- Lift exactly UIKeyTrigger.cs's scene-branch Menu arm (s38 gate + s121 branch) with ONE verdict from MenuKeyStep, which
  gains MenuKeyGuestOpen (harness name 'guest'). Leave unchanged: the dialogue path's silent drop (critic: the code backs
  the gate lane), Alt+F2 party, Alt+F5/F9 + harness savemenu, BattleHUD/diorama refusals, the .eb MENU/PARTYMENU refusals,
  SaveLoadUI's guards. Never write UIManager.IsMenuControlEnable. Fail closed: a fault in the rule = an audible refusal.
- Lever `netsync guestmenu old` = s121 exactly.

## D4 Who may open (OWNER 11-06: refuse the unmirrored guest)
- A following client in a live session, using s167's session latch (WorldSessionHeld-style: seen live, LIVE or GRACE, no
  ramp) so a ~2.3 s stall never flickers it, AND mirroring the host's story. A paired guest that is NOT mirroring yet
  (paired or Continued on the world map, or a field-paired guest before its first mirror arm) is REFUSED with the buzz and
  "You'll get the menu once you've followed your partner into a location." This closes s38's hole where such a guest
  opened its OWN party's menu. `guestmenu old` restores that old behaviour too (s121 exactly).
- The bench: IsSelfTestRole && BenchGates is in 'who', so a solo bench presses the REAL Menu key through the verdict.
- Out of scope, named as a Known limit: Alt+F9 Load for an unmirrored paired guest (pre-existing; its own lane).

## D5 The open predicate (pure, cheapest first, one why each)
- Common: lever; who; caps; live; host place field or world (no transition, battle, diorama, loading); host not fighting;
  section 12 present + fresh in the latest frame and CONTENT-WITNESS passes (D9); my control; not busy (booted, follow
  fade, transition, session end, battle return, in-flight local jump, step-out); THE OPEN MIRROR: never open what a close
  trigger (D11) would close at once.
- UI quiet: use NetSyncDialog.AnyEtbLine(false) (+ !SuppressLocalDialogInput, !IsLoading), NOT Dialogs.Visible (the critic:
  a persistent kit HUD strip counts as visible and would refuse forever). With a strip up, stock FieldHUD.OnKeyMenu runs
  HideAllHUD -> CloseAll on the guest's copy exactly as single-player does; follow stock and bench it on a kit HUD field.
- Field terms: LastHostField == my field; no unseen section-4 intent for another field; GuestHostSceneWhy(fld) == null;
  not a windowless host-holds-input beat. Never refuse on section 7 b4 HfMenu (the host's own menu: both players in menus
  is the owner's call).
- World terms: the gate lane's list (HUD/HUDNoMiniMap, on foot, not an event world, not navi mode 2, no world transition,
  no world-out pending/committed, the host not on a field, block valid, same world, StScene clear). NO host-menu flag: the
  claim that the host's own main menu raises StScene is unproven (critic). A bench row measures it first; if it does, a
  Known limit (on the world map the guest cannot open while the host is in its menu) and a later fix.

## D6 Opening timing (the critic's window)
- The verdict runs at the press and arms the guest-menu SESSION flag there (so every close trigger covers the window).
- The SEAT is taken at the door: UIManager.ChangeUIState from FieldHUD/WorldHUD to MainMenu, before MainMenuUI.Show, with
  the predicate RE-CHECKED there. If it fails at the door, the menu does not open: route back to the HUD (stock fade-in)
  with the refusal line. A follow or boot that started inside the window is a close trigger.

## D7 Guest words (OWNER 11-06: all three)
- A refused Menu press: the buzz on every press, one log line per place per why class (DeclineOnce), and a 4 s on-screen
  line naming the reason (s167's EntryLineMs idiom), ended at every scene change. The paired branch forces the overlay off
  today ("the ghost IS the status"): add a timed state that shows there too.
- A forced close: one line naming the cause ("FF9 co-op: menu closed -- following your partner." / "-- your partner's
  battle." / "-- your partner's scene." / "-- the co-op session is ending."), cleared at the next scene change.
- A 'View only' chip while seated at rung 0 (IMGUI, the F3.2 chip precedent that draws above NGUI): "View only: your
  partner's game makes the changes." Words are seeds; the owner tunes them as in s165/s167.
- Silent cases stay silent (MENUOFF, non-HUD states, the dialogue path).

## D8 The seat
- Its OWN bracket: extract the diorama's static bracket into an instance type with two instances (the diorama's and the
  menu's), behaviour-neutral, as the FIRST engine piece; proven offline by SeatSelfTest + the bracket selftest and in game
  by the round's regression set (the diorama legs). Never share the diorama's statics.
- Seat by REFERENCE: scratch PLAYERs into ff9.player[id] and party.member[i] (MirrorHostParty's idiom), a fresh
  List<FF9ITEM> in the host's order, fresh rare_item_obtained/rare_item_used sets, gil by value. Never write through a guest
  object.
- From ONE fresh frame's sections 1, 2, 3 and 12 through PURE parsers (TryParsePartyInto style; new order-keeping bag and
  key-item readers). Never ParseSections, NetSyncParty statics or MirrorActive (the s154 SEAT LAW generalised).
- Surface: party.member[4]; per member the s154 derivation plus menu_type and category set BEFORE sizing pa[], pa[], exp;
  saForced/saBanish/saHidden are re-derived by FF9Play_Update from install data (no wire bytes); bonus and permanent_status
  are not seated (no screen reads them: the critic adopted the wire lane). Bag, rare sets, gil. NOT seated: cards, settings,
  gEventGlobal, frogs, counters, non-party characters.
- CONTENT-WITNESS: the open is refused with "Your game data differs from your partner's (<member>)." if any member's preset
  is missing, its pa length differs, or an equipment or SA id is unknown on this install (StatusUI throws on a missing
  preset: never seat one). Log the component.
- While seated: skip MainMenuUI.Show's SetMasterSkill (it runs on every return to MainMenu and would write pa[] on the
  guest's REAL benched characters); hold AchievementManager reports (add the seat to its holds); own-party readers (the
  client ghost's LiveSlotChars) read the seat record's real refs; the save gates key on the seat (autosave ladder,
  SaveLoadUI's s38 floor, ManualSaveRefusedNow, PairingFreeStanding); refuse the open while a diorama is booted, armed or
  returning, and the diorama's MayBoot refuses while a seat is held (the D11 battle-cut close restores first).
- Re-seat only at screen boundaries (entering MainMenu from a sub-screen) and only when the seated sections' BYTES differ;
  never under an open character screen. The guest's local item sort is kept as a permutation by item id and re-applied.
- Story bytes the screens read (gEventGlobal[16] etc.) stay the guest's last field-load mirror: a Known limit for rung 0.

## D9 The restore
- At ONE door: UIManager.ChangeUIState leaving the menu family for a non-menu state, BEFORE the HUD's Show (so before
  SetEventEnable(true) and before any HUD-gated lane can run). Restore only onto the SAME FF9StateGlobal instance with no
  deserialization since the seat; otherwise DROP the record without writing (one line). Idempotent, element-wise, cleared
  in a finally. EnabledSubMenus is cleared (or put back) at every close.
- Backstops with a loud 'should never happen' line: the top of SceneDirector.Replace; the exit ramp's fire BEFORE
  ExitMirrorToOwnSave (the deserializer runs before ReplaceLoadMap); the Alt+F9 load entry.
- Every close path ends in a restore or a drop: a table of all of them (normal cancel, each forced close, the ramp's arm and
  fire, a soft reset to the title, the quit confirm, link death, process death = nothing needed because no save was written
  while seated).

## D10 Rung-0 confirm census
- Hooks key on the seat flag ALONE (vanilla, solo and the host run stock). Each refusal reuses the screen's own neighbouring
  stock buzz branch at the same depth, above the first write and above ImpactfulActionCount++: the confirms lane's E1-E3,
  A1-A3 (BOTH AbilityUI handlers, OnKeyConfirm and OnKeySpecial), I1 (item use), I2 (Gysahl), C1 (card discard: refused),
  K1 (Config's Booster panel: refused), K2 (Return to Title: refused). Order and Party: EnabledSubMenus greys them.
- Local writes allowed on the copy and lost at close: item sort (Auto + manual), the key-item and Folklore read markers.
- Config (the guest's own settings) stays live; Known limit: the exit ramp reloads the guest's own autosave, which restores
  Settings, so Config changes made during a session revert at session end.
- No backstop at the write primitives (browsing Equip reaches them). The bench backstop is a close-time fingerprint of the
  state OUTSIDE the seat (gEventGlobal, Achievement/EventState counters, MiniGame cards, hintmap_id).
- MenuOpenEvent runs the guest's world copy's UID 0 tag 4 on every world-map open: W1 recon reads tag 4 in the dispatchers;
  a bench row compares the s167 world fingerprint before and after an open on 9010/9011.

## D11 Forced closes (one CoopCloseGuestMenuIfDue(site), asked FIRST at every waiting site)
- Scope: only the guest-menu session flag; never Pause, the quit confirm, a script-opened menu, the ~ menu or the full map.
- Triggers: the host leaves (an unseen section-4 nonce for another field; the serial candidate due; section 7 b6 for
  field->world; world->field in WorldFollowFire; a world->world move); the host's battle cut at EVERY cut, booted or not
  (the owner's battle-cut decision, read literally; the critic: not an owner question); the exit ramp armed (both
  branches); the host at the title (section 7 b7); OWNER 11-06: a host conversation, chest, ATE or scene starting on my
  field (the relayed talk/chest/ATE starts, and b0 HfScene for my field).
- While a close is in flight for the host's battle nonce, GuestBootState's uiFree reads free, so the report is BOOTING and
  the host's start hold arms.
- A link outage does NOT close the menu: it stays open as a view (rung 1 refuses confirms while the link is not live), and
  closes when the ramp arms. (Relay stalls of ~2.3 s are routine; nothing is lost either way.)
- THE CLOSE ORDER LAW (the close lane) plus the critic's quit-confirm rule (wait while isShowQuitUI, or hide QuitUI first,
  so a later cancel cannot put back events-off on a live FieldHUD), Config's key capture exits through SetControllerSettings,
  TutorialUI covered generically, the WATCHDOG (CloseCapMs seed 1500 -> the stock scene-load sweep), THE FADE CHOICE, THE
  INPUT SWALLOW, the timing budget, one line + harness keys per close, one lever per trigger.

## D12 Rung 1 (s169), designed now, built after s168 is green
- Kind 1 SA_SET on type 8: absolute before/after sets keyed by CharacterId; 'before' = the set AS RECEIVED on the wire.
- The host gates 1-13, the apply (FF9Abil_SetEnableSA + one FF9Play_Update), tripwires T1/T2 with rollback, the
  one-character write, the answer-echo law (drain before publish: the answer and the post-apply party leave in one frame),
  exactly-once (one-answer law + at-least-once resend + CAS: a late duplicate reads ALREADY), the guest's 3 s pending
  hold, THE MEMBER DATA CHECK (a member whose derived set differs is view-only), the AbilityUI redraw hook on both roles,
  the host's 4 s line (decision 'host notification': name the ability when exactly one changed), the refusal words, the
  close carries the queue.
- The host applies anywhere on the field or world map; refused in battle, on the result screen and with no live party
  (no stock .eb reads saExtended; battle reads the set by reference).
- No host off switch at rungs 0-1 (the owner asked for none); section 12's policy b0 is reserved so an ini key can come
  later with its own words, never by withholding b3.
- rung 1 needs section 13 + type 8: s169 adds them; s168 reserves them in the registry only.

## D13 Benches
- The bench lane's lever set (`netsync guestmenu ...`), the `netsync.guestmenu` harness key (its sentinel in AppendNetsync's
  catch literal), the ENGINE-STAMPED menu fingerprint over the save's Common serializer components with `restore skip
  <component>` mutants (NetFingerprint alone is not acceptable), a new proof line in a NEW file ('guest menu selftest: OK
  (N rows, M mutants caught)'; MenuRefusalSelfTest stays at its pinned 14 rows), s121's keys keep their meaning (`now`
  gains 'guest' only when active; re-key coop_world_walk PR-SAVEMENU and coop_field_swap_timing_duo MENU_PRE_OK by stage;
  coop_cut_hold's s121 leg stays as the fallback row), Pause untouched (s164's MENU legs stay green), OLD measured on s167,
  NEW, LEVER with CAL on every launch, the regression set (round B's + the diorama legs, because of the bracket extract).
- Selftest rows prove the ACTION only (the selftest role never mirrors and runs no DioramaTick); the key path and the
  triggers are proven by the duo or T2. Bench frames are built before the seat or through the SlotSource seam (the critic).
- T2 needs coop_peer to adopt b3 and a new tape from a b3 host; until a tape exists, the key-path rows run on the duo.
- The duo cannot run mixed DLLs: its older-peer row is `guestmenu caps off`; true skew only on the two-PC sheet.

## D14 Kit
- battlewire twins of every new rule and constant; the fakegame `guestmenu` rung with the bench lane's faults; coop_peer
  (b3 adoption, the section-12 decoder, later the type-8 encoder); scenarios + runners `studies/field-coop/s168/...`;
  GUEST_TERMS and the co-op tutorial words updated behind the caps condition; health.NETSYNC_GENERATIONS gains an s168
  marker; docs. No Workspace change (no off switch).

## D15 Known limits (rung 0)
- story bytes stale mid-field; item sort and read markers lost at close; Config reverts at session end; the host's ghost of
  the guest stands mid-stride while the guest's world menu is open (the trailer keeps 'walking'; check with game_snap);
  IMGUI overlays drawing over the stock menu (check); MenuOpenEvent's world tag 4 (verify); true version skew only on two
  PCs; Alt+F9 for an unmirrored paired guest (pre-existing); the world StScene question (D5).
