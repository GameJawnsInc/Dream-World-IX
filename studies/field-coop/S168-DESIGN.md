# The guest's main menu: view-only, then support abilities (s168-s169)

**Status: s168's engine, kit and bench are built, 2026-11-07; nothing is deployed.** W1a-W1i and the W1 review's four
fixes sit in the shared clone's working tree (uncommitted by design), compiled with `tools/build_memoria.py --no-deploy`
and proven offline. W2 built the kit twins, the fakegame `guestmenu` rung, `coop_peer`'s b3 side, the three-harness
bench and its runners, then ran a five-lens critic whose 24 confirmed findings are fixed; the co-op domain tests are
green. No bench leg has run in game. "As built (s168 W1)" (below the Departures) lists every engine deviation kept,
the final proof counts, the pinned W1a/b artifact and what is owed; "As built (s168 W2)" is the kit's ledger. The
decisions are corrected in place to match the build.
s168 (rung 0, the view-only menu) is deployed and benched in game only AFTER the owner's s167 two-PC look; if that look
needs an s167 engine fix, the fix lands first and s168 rebases onto it. s169 (rung 1, support abilities) is designed
here and built only after s168 is green. Each round is built, deployed and benched alone (one change per in-game test).
s168 takes the clone under a TAKING THE CLONE line in the round queue when its engine edits start.

This is rung 0 and rung 1 of `GUEST-MENU.md`'s Option A: the stock main menu on the guest, over a copy of the host's
party, every changing confirm caught; from rung 1 the support-ability confirm is forwarded and the host does the write.
Sources: the study `GUEST-MENU.md` and the owner's decisions of 2026-10-31; a grounding pass (eight read-only lanes --
gate, seat, wire, close, confirms, abilities, bench, cross -- and a completeness critic whose verdicts on contradictions
are adopted); four review rounds (54, 39, 10 and 19 confirmed findings, each finding adversarially verified), the
third's fourteen simplifications adopted by the coordinator (listed under "Cut in round 3" in the Departures); and the
owner's four answers of 2026-11-06. The coordinator's skeleton and the cut verdict are kept beside this file
(`s168/DECISIONS-SKELETON.md`, `s168/CUTS-ADOPTED.md`); the grounding and review reports (`gm_ground.json`,
`s168_review*.json`) are in the s166-handoff-575aeb session's scratchpad. **The study has two numberings for
the owner's decisions** (its summary table and its section 15), so this document cites them **by name only**: Architecture, First build, Which
characters, Both players in menus, Party order and row, Item sort, The host starts a battle, The host leaves the field,
The copy's lifetime, Host notification.

C# lines are the live shared clone's (`C:\gd\FFIX\Memoria`, base `6b8bb2d5` with the s158-s167 stack in its working
tree), each re-read on 2026-11-06. Paths are relative to `Assembly-CSharp/`. The tree is decompiled: the grounding lanes
caller-checked the functions cited, and this design re-read every anchor it gives; where a claim could not be checked
it says "unverified". The build re-finds each site. The harness protocol stays 5. The wire stays v15: no bump.
These anchors are the pre-s168 clone's: the s168 delta moves them (NetSyncClient.cs alone grew by about 1600 lines), so
the corrections made after the build and the As built section name s168's own sites by symbol.

## What happens today (s167)

- **The refusal.** Every ordinary Menu press into the field or world main menu goes through one read: the Menu arm of
  `UIKeyTrigger`'s scene branch (`Global/UI/UIKey/UIKeyTrigger.cs:714-724`). The scene branch runs only when a scene
  exists for the state and no dialogue is Activate, unless paused (:660). Line 719 (s38) opens the menu when
  `IsMenuControlEnable && !IsMirroringStory`. Lines 721-722 (s121) send a mirroring guest to
  `NetSyncField.RefuseMainMenu` (`Memoria/Netsync/NetSyncField.cs:1067-1103`). Its pure step `MenuKeyStep` (:995-1002)
  makes the refusal audible on FieldHUD/WorldHUD and silent elsewhere. "Audible" is FF9Sfx 102 plus one **log** line,
  `[NetSync] main menu suppressed (following guest) on field N` (DeclineOnce, :838-860; the world class latches on
  wldMapNo, :1092). **Nothing is drawn on screen.** The other reads stay as they are: Alt+F2 party (:510), Alt+F5 save /
  Alt+F9 load / the harness `savemenu` (:572), and the dialogue path's silent drop (:886-891). `MenuRefusalSelfTest`
  (NetSyncField.cs:1111-1145) holds 14 rows, pinned by `ff9mapkit/tests/test_harness_netsync.py:6588`.
- **The hole.** `IsMirroringStory` (`Memoria/Netsync/NetSyncClient.cs:1266-1269`) is a latch set only by `ArmMirror`
  (:1233-1244), at a field load or at a world follow-out's landing. A guest that paired or Continued while on the world
  map, or a field-paired guest before its first arm, passes line 719 and opens **its own** party's stock menu
  (`WorldHUD.Show` sets menu control from `ff9.GetUserControl()`, `Global/World/WorldHUD.cs:68`; the s144 freeze never
  touches usercontrol). In battle the same guest fights with the host's party (the s154 seat), so it sees two parties.
  Read from code; not run in game.
- **The study's anchors moved.** `UIKeyTrigger.cs:699-702` is now :714-724; `:552` is :572; `:869` is :889;
  `NetSyncField.cs:664` is :995. The study's "one line" is a log line. ParseSections has three production callers
  (NetSyncState.cs:115 and :154, the talk/chest accept), not one. Section 3 is written in the host's list order
  (NetSyncParty.cs:178-192); only the story mirror's `ParseBag` (:354-368) loses it. saExtended already rides section 1;
  saForced/saBanish/saHidden are re-derived inside every FF9Play_Update (`Global/ff9play.cs:347-368`). The study's
  "the host's gauges wait 8000 ms" is wrong (next table).

**What a guest outside FieldHUD/WorldHUD does to each lane today.** A mirroring guest reaches no main menu today, so these
waits were seen only through the pause screen (s164's MENU leg). The main menu makes them reachable for minutes.

| Lane | Today, with the guest's UI off the HUD | Anchor |
|---|---|---|
| Field follow, serial | Returns at `State != FieldHUD`, keeping its candidate. The "mid-battle/menu" comment sits on `!onField`, which a menu never takes | NetSyncClient.cs:5132-5137 |
| Field follow, intent | Defers without marking the nonce seen; fires on the first FieldHUD frame (s164 DL-DEFER: within 200 ms) | :11012-11013 |
| Follow-out, field to world | Refused at WorldOutStep's FieldHud term, one line per host world visit; its 1200 ms debounce keeps counting | `NetSyncWorldFollow.cs:479-480` |
| Rejoin, world to field | `WorldFollowFire` asks the s167 full-map close first, then waits on WorldArmWhy ("the world HUD is not up") | NetSyncClient.cs:6149-6156 |
| Host battle | DioramaTick returns at its UI gate before its 1 s stamp; NoteBootWatch reads `uiFree` false, so `GuestBootState` says BUSY; the host's start hold arms only on BOOTING, so its gauges run at once and the guest boots late into a running fight | :3751-3756, :4537-4552; `NetSyncBattle.cs:5502-5503` |
| Relayed talk, chest | Rides `TalkRelayTtlMs` 4000, then "expired before my copy was free" | NetSyncClient.cs:592 |
| Relayed ATE press | Expires after `PressTtlMs` 5000 of control-on time (a menu leaves control on) | `NetSyncAte.cs:77` |
| Dialogue ring events | Age out after `PendingTtlMs` 20000 | `NetSyncDialog.cs:52` |
| Exit ramp | Field: settles only on FieldHUD, but fires after `ExitRampSettleMaxMs` 10 s anyway; world: no UI term, settles at once. The Autoload deserializes into whatever objects are installed | NetSyncClient.cs:1088, :1965-2048; `NetSyncState.cs:313-329` |
| Same-field kick | Not reached by a mirroring guest or the bench: SameFieldKickTick returns while `_storyMirroring` and on any non-client role. Its FieldHUD wait concerns only the unmirrored guest, which decision 7 refuses | NetSyncClient.cs:7212, :7223 |
| Ghost re-dress | EnsureGhost waits for FieldHUD; `LiveSlotChars` reads the live party every tick | :15544-15551; `NetSyncVisitor.cs:326` |
| Speed mirror, step-out | Need my control off: cannot be live under an open menu | `NetSyncStepOut.cs:79-82` |
| Field and world scripts | Frozen: the HUD's Hide sets `FF9.attr \|= 0x102` | `Global/UI/UIManager.cs:457-463`; `Global/Field/FieldHUD.cs:242`; WorldHUD.cs:95 |

## The decisions

### Both rounds

1. **Two rounds, one design.** s168 is rung 0 (view-only), s169 is rung 1 (support abilities), as the owner chose in
   *First build*. Each is built, deployed and benched alone. The schedule is the owner's of 2026-11-06: s168 is built
   now with `--no-deploy` and deployed only after the s167 two-PC look (an s167 fix, if one is needed, lands first and
   s168 rebases). s169 starts after s168 is green.

2. **The wire: v15, no bump; the feature is cap b3.** The menu is an additive v15 feature under S166-DESIGN decision 2's
   law: it runs only when `FeatureOn(own, peer, CapGuestMenu)` holds (`Memoria/Netsync/NetSyncWorldWalk.cs:226`, b3 =
   0x08; FeatureOn :503-506). s168 speaks 0x0B (b0|b1|b3): `OwnCapsRule(fpOff, menuOff)` =
   `fpOff ? OwnCaps : (OwnCapsWalk | (menuOff ? 0 : CapGuestMenu))` (today `OwnCapsRule(fpOff)`, :2513-2516), so
   `fp off` stays s166 exactly (0x01). The proof's `OwnCapsFn` delegate becomes two-argument (fpOff, menuOff), and
   `OwnCapsNow` passes the live `guestmenu caps` lever as menuOff; s167's caps rows are re-keyed over it, never weakened
   (decision 32's re-key list).
   `NetSyncWorldFpArmed.OwnCapsNow` stays the one live source, so the trailer, the bench host and the relay keepalive pick
   b3 up with no other edit. FeatureOn is re-read every Update from `PeerCapsOf(_wwCache.Latest)` (:496-499) and never
   latched. **Caps are not liveness:** the cache is held past the 2 s StaleMs cliff, so every gate below also needs a
   live peer. "Off" (an older partner build, or the lever) is s121's read exactly for a mirroring guest: on the scene
   branch its refusal -- keys, count, log line -- plus the on-screen refusal line naming an older partner build (decision
   10), a press inside a HUD fade included (the W1 review's `pairOn`, decision 6: GuestQuiet is a feature-on pair's
   only); on the dialogue path its silent drop (decision 6). An unmirrored paired
   guest stays refused (decision 7), and only `guestmenu old` restores its s121 open. The existing caps line already
   names it: `CapsNames[3]` is "guest menu" (:2511), so CapsLineText logs "the partner's co-op build lacks my guest menu (its caps
   0x0003, mine 0x000B) -- off for this pair: the older behaviour" once per process and caps pair. A new proof row
   `caps.own_s168_word` pins `OwnCapsRule(true, *) == 0x01`, `(false, false) == 0x0B` and `(false, true) == 0x03`
   beside s167's `caps.own_s167_word`, which is re-keyed to `OwnCapsOf(false, true) == 0x03` (decision 32). As built
   (W1d), a second new row `caps.line_text_s168` pins that caps line's exact words for an s168 build against an s167
   partner, and the world walk proof compiles with NetSyncGuestMenu.cs (OwnCapsNow reads its `caps` lever).
   **Lever:** `netsync guestmenu caps off` speaks s167's 0x03 exactly. `worldwalk fp off` keeps its s167 meaning, s166
   exactly (0x01), which also turns the guest menu off.

3. **One wire registry, written before any code** into `memoria-patches/README.md` and S166-DESIGN decision 2's bit
   list, with `COMMS-MENU.md` section 4 updated to the shared type-8 ring (the entry format changes; its bidirectional
   type 8 is kept, the host-to-guest direction reserved for comms). A battlewire twin pins it (GM0-REGISTRY).

   | Space | Id | Meaning | Round |
   |---|---|---|---|
   | caps (trailer 40-41) | b0 0x01 | world pose | s166 |
   | | b1 0x02 | world fingerprint | s167 |
   | | b2 0x04 | comms (reserved) | later |
   | | b3 0x08 | the guest menu (sections 12-13, type 8 kind 1) | s168 speaks it |
   | | b4 0x10 | B4.2's v2 command frame (reserved) | later |
   | trailer flags (93) | b0 | I follow | s166 |
   | | b1-b7 | **zero**. No role-dependent meaning: the critic refuted both proposed b1 uses (a host-menu bit and a menu-wanted bit) | -- |
   | type-5 sections | 0-11 | story, party, key items, bag, intent, event, talk, dialogue, dress, chest, speed, world fingerprint | taken |
   | | 12 | the guest-menu block, host to guest | s168 |
   | | 13 | the menu answers, host to guest | s169 (reserved in s168) |
   | | next free | the quit word (GUEST-TRAVERSAL item 15) takes it when it is designed | later |
   | section order | | `[0,1,2,3,(4),5,(6\|9),10,(11),(12),(13),7,8]`: 8 stays right after 7 and last (DressSelfTest, the kit's dress tape) | s168 |
   | frame types | 0-7 | in code (7 retired, still compiled; `Memoria/Netsync/NetSyncSocket.cs:220-227`) | taken |
   | | 8 | the shared ring: one latest slot per direction (the type-8 slot pair exists both ways, decision 23), variable-length entries, epoch u16 + seq u16, a kind per feature, each kind gated on its own cap bit. s169 uses the guest-to-host direction; the host-to-guest direction is reserved, unassigned, for comms (b2) to claim when comms is designed | s169 (reserved in s168) |
   | type-8 kinds | 1 | SA_SET (the guest menu, b3): guest to host only | s169 |
   | | 2+ | comms' ping, chat and emote (b2), when comms is built; later guest-menu kinds (equip, use) under section 12's applyMask | later |
   | section 12 applyMask | b0 | this host applies SA sets | s169 |
   | | b1, b2 | equip; item and field-ability use (rungs 2-3) | reserved |
   | section 12 policy | b0 | reserved for a future host off switch (decision 4) | reserved |
   | | b1-b7 | zero | -- |
   | overlay states (local, listed to avoid collisions) | 29 | the guest's timed refusal line, one text at a time (the forced-close line is drawn by OnGUI on its own timer, never through state 29: decision 10) | s168 |
   | | 30 | the host's timed menu line | s169 |

   Older engines ignore every addition three ways: `NetSyncFrames.Accept` has no default case, so an unknown type is
   dropped (NetSyncSocket.cs:718-770); every section walker skips an unknown id by its length; s166/s167 read only flags
   b0. The relay and the kit's bridge are opaque pipes.

4. **No host off switch at rungs 0-1.** *Which characters* gave the whole party and asked for no setting. Section 12's
   policy b0 is reserved so an ini key can come later with its own words, **never by withholding b3** (that would make
   the guest's caps line wrongly say the host's build lacks the menu). Nothing to undo.

### s168 (rung 0): view-only

5. **The menu block, section 12, rides every state frame to a b3 follower.** The host appends it in `BuildStateFrame`
   between section 11 and section 7 (`NetSyncClient.cs:10626-10634`), only while a send rule in the `FpSectionSendRule`
   pattern holds (NetSyncWorldWalk.cs:2816): the host role, FeatureOn(b3) over both words, the peer's trailer flags b0
   (it follows), the peer live. As built that rule is the pure `GmSectionSendRule`; its host term reads the real role
   (`_role == "host"`), never HostFpSectionNow's `hostSections` argument, because the selftest role's DressSelfTest and
   speed proof call `BuildStateFrame(true, true)` and must keep their pinned bytes; its live term is the existing
   peer-alive read (`IsConnected && GetRemote().Valid`). It is not request/reply, for three reasons the code decides:
   the seat happens at the door and `MainMenuUI.Show` reads the party synchronously (`Global/MainMenuUI.cs:38-77`), so
   the data must already be in hand; a replayed tape never answers a request, so request-gated data could not be
   benched on T2; the open is instant.
   **Fault isolation:** section 12 (and section 13 from s169) is built through a `HostGuestMenuSectionNow` helper in
   HostFpSectionNow's idiom (NetSyncClient.cs:9691-9708): its own try returns null on any fault, so the section drops and
   the frame never does. BuildStateFrame runs on the host at the 7 Hz publish (inside NetSyncClient.Update's single try),
   at the out-of-band MAPJUMP intent emit and at every talk and chest start, so an escaped throw would lose story,
   intent, the dialogue ring and the dress, and at the publish would skip the rest of the host's Update (its battle pump,
   the world lane, the start hold) on every frame. The helper logs one line per process and bumps `frame.faults`; the
   guest then refuses with `no_data`, as the FRAME-CAP-GUARD below already says.

   | Bytes | Field | Notes |
   |---|---|---|
   | 0 | fmt u8 = 1 | keeps "present" distinct from "absent" (`AppendSection` drops an empty body, NetSyncState.cs:255-269) |
   | 1 | policy u8 | every bit zero in s168; b0 reserved (decision 4) |
   | 2 | applyMask u8 | zero in s168; s169 sets b0 (SA sets) |
   | 3-6 | gil u32 | `party.gil` |
   | 7-8 | usedN u16 | |
   | 9.. | rare_item_used u16 x usedN | the Key Items "new!" marks (ItemUI.cs:774) |
   | then | memberN u8 (<= 4) | the present party members |
   | per member | charId u8, presetId u8, category u8, exp u32, basisCapa u32, paN u8, pa u16 x paN | keyed by CharacterId (the value section 1 sends as charId). pa is clamped at 65535 (every installed cost is far below) |

   As built (W1c, W1d): the encoder (`HostMenuBlockOf`, over section 1's own `NetSyncParty.SlotSource` seam) writes at
   most 4 members and at most 255 pa each, skips null members and ids outside 0..65535, and leaves OUT a member whose
   preset (`info.menu_type`) is outside 0..255 rather than truncate it to a u8 that could name another preset: section 1
   still names that member, so the guest refuses `no_data` (it fails closed; the proof's `block_preset_wraps` mutant).
   The reader skips bytes after the last member, so an additive fmt-1 append is read past the way the section walkers
   skip an unknown id. All four of the seat's sections (1, 2, 3, 12) are read from one frame, all or nothing
   (`TryReadSeatFrame`).

   **Cost, computed on paper from the codec (not measured):** 3 (section header) + 10 + 2 x usedN + the sum over members of (12 + 2 x paN). With four members
   on the main presets (48 abilities each) that is 445 + 2 x usedN bytes: about 450-570 B typical, about 960 B with 256 key
   items marked. The host rebuilds the state frame every 150 ms, but both transports re-send the latest slot on every
   ~33 ms write tick (NetSyncSocket.cs:677-716), so each byte costs about 30 B/s for the whole session: about 13-29 KB/s
   host to guest, only to a b3 follower. Today's frame is about 2.9 KB typical and about 5.0 KB at its computed worst,
   so the worst case with section 12 is about 6 KB. GM0-BW measures both on the duo.
   **FRAME-CAP-GUARD, a local check at section 12's append:** `BuildStateFrame` appends section 12 only if
   len(frame so far) + 3 + len(12) + `TrailReserve` <= `NetSyncWire.MaxPayload` 8192 (NetSyncSocket.cs:218).
   `TrailReserve` is the codec maximum of everything appended after 12: section 7 at its largest, 424 B with its header
   (HeaderLen 12 + OpenLen 6 x OpenCap 4 + the count byte + EventLen 12 x RingCap 32; NetSyncDialog.cs:84-89,
   BuildSection :653-686), plus section 8's 6 B (a 3-byte body, NetSyncClient.cs:10632-10636): 424 + 6 = 430 B in s168;
   s169 adds section 13's maximum + 3. Section 11 comes before 12, so it is already in the frame so far. One proof row
   recomputes TrailReserve from HeaderLen, OpenLen, OpenCap, the count byte, RingCap and EventLen, and (as built) section
   8's part from `NetSyncVisitor.DressBodyLen` (3) plus its 3-byte header, so the constant cannot rot. From s169,
   section 13 is appended only when 12 was: s169's answer-echo law wants 13 with 1 and 12 in one frame, and its reader
   assumes 13 implies 12. BuildStateFrame's order and F3.3's rule that sections 5 and 7 leave in one
   snapshot (:10612-10614) stay exactly as they are. A drop removes the **section**, never the frame, with one line per
   process and a counter, the precedent of BuildPosPayload's trailer drop (NetSyncSocket.cs:281-292). There is no
   sender-side guard on the state frame today, and an over-cap frame breaks a TCP link into a redial loop
   (NetSyncSocket.cs:410) and silently stales the relay lane. The guest then refuses the open with "the menu data did not
   arrive". The cost: section 12 can drop up to about 0.45 KB earlier than strictly necessary, and only in frames already
   above about 7.3 KB. `frame.type5_len`, `frame.sec12_len` and `frame.dropped` are stamped at the build (the last BUILT
   type-5 payload), so a selftest reads them with no socket. As built they stamp at EVERY BuildStateFrame on any role
   (the selftest role's own builds too); `sec12_len` is section 12's body length (0 when the last frame carried none, -1
   before any build), `type5_max` the largest payload built in the process. **Lever:** `guestmenu caps off` on either
   role stops the section. The guard's call site is proven by the pure rule and the TrailReserve row (GM0-FRAME), not
   by an in-game oversize build.

6. **The gate seam: a pre-check at the press.** Lift exactly the scene branch's Menu arm (`UIKeyTrigger.cs:719-722`): its
   two `IsMirroringStory` conjuncts become ONE verdict read at the press. `MenuKeyStep`'s verdicts gain
   `MenuKeyGuestOpen` (5) and `MenuKeyGuestQuiet` (6), both harness name `guest` (NetSyncField's constants equal
   `NetSyncGuestMenu.KeyGuestOpen` 5 / `KeyGuestQuiet` 6, one source). The press arms nothing: it refuses audibly or
   calls stock `OnKeyMenu`, and the door (decision 9) is the one open verdict. As built (W1e) a new arm sits after the
   Android TV arm and ahead of s38's line, keyed first on `NetSyncField.GuestMenuPressInPlay` (`WorldSessionHeld ||
   IsMirroringStory || (IsSelfTestRole && BenchGates)`: three static reads, never the guest-menu class, and a fault
   reads false); when it is false, s38's and s121's two lines run byte for byte as in s167. When it is true the press
   takes ONE verdict and spends it through the pure `PressActRule`: stock OnKeyMenu for every open, the press deadline
   for GuestOpen only, a guest refusal through the given-verdict `RefuseMainMenu` below, s121's own refusals through the
   parameterless s121 entry, nothing for MENUOFF. The pure rule, in `NetSyncGuestMenu.cs` (its live reads lazy):

   ```
   GuestMenuKeyStep(enable, old, guestSession, mirroring, loading, pairOn, state, whyNot):
     !enable                            -> StockOff       (stock's own MENUOFF: silent, as ever)
     old                                -> MenuKeyStep(enable, IsMirroringStory, state)   (s121 exactly)
     !guestSession                      -> Open           (vanilla, a host, an unfollowed client)
     state not FieldHUD and not WorldHUD -> MenuKeyStep(enable, IsMirroringStory, state)
                                           (s121's step: s38's silent drop for a mirroring guest; the bench and an
                                            unmirrored guest keep Open, so BattleHUD's diorama refusal still buzzes and counts)
     loading && pairOn                  -> GuestQuiet     (the HUD's Hide in flight, e.g. a second press inside its fade:
                                                           stock OnKeyMenu, which reads false while Loading -- silent,
                                                           never counted, no line, `now` stays `guest`; never `ui`)
     why == null                        -> GuestOpen      (sceneFromState.OnKeyMenu and the press deadline, decision 9; nothing armed)
     else                               -> RefuseAudible(why)
   guestSession = WorldSessionHeld || IsMirroringStory || (IsSelfTestRole && BenchGates)
   loading = UIManager.IsLoading (UIManager.cs:97: the current state's scene is Loading, or there is no Unity scene)
   pairOn = PairOnRule(old, WorldOwnCapsNow, _wwCache.Latest)
          = !old && FeatureOn(own, PeerCapsOf(Latest), CapGuestMenu)    (the W1 review: term 3's own reads)
   why = whyNot() = GuestMenuWhyNot(...), evaluated only for the last two lines
   ```

   **GuestQuiet is a feature-on pair's only** (the W1 review): with the guest menu off for the pair (an older partner,
   `guestmenu caps off`, `worldwalk fp off`) a press inside a HUD fade falls through to the predicate, whose who-before-caps
   order gives `not_mirroring` or `session`, else `older`: s121's audible refusal exactly (decision 2), never a silent,
   uncounted press. `pairOn` is the fourth lazy read, asked only inside the fade, inside the same try (a fault there is
   `fault`). `guestSession` includes `IsMirroringStory` so a mirroring guest whose session latch fell (the ramp pending) is
   refused, never opened. **Fail closed, but only inside a guest press:** GuestMenuWhyNot is evaluated lazily, only after
   `enable`, `old` and `guestSession` say a guest press is in play, and an exception once guestSession is known true is
   `RefuseAudible("fault")`, never an open. A fault before that, or with guestSession false, takes s121's read exactly
   (`MenuKeyStep(enable, IsMirroringStory, state)`, UIKeyTrigger.cs:719-722), so a vanilla player, a host or an
   unfollowed client never loses the menu; a proof row pins that fallback.
   **`RefuseMainMenu(why)` takes the verdict as given:** a RefuseAudible from GuestMenuKeyStep buzzes, counts and logs on
   FieldHUD/WorldHUD without re-running s121's MenuKeyStep, which reads Open for an unmirrored guest and for the bench
   (neither is mirroring) and would drop the refusal silently. As built its signature is
   `RefuseMainMenu(verdict, why, member, component)`: the verdict to take as given, plus the content witness's member
   (named in the line, decision 13) and component (logged); it buzzes, counts, calls `NoteRefusal(why)` and asks the
   decline book, then arms the 4 s refusal line. The parameterless s121 entry stays byte-identical for the
   `old` path. Proof rows: the bench with why `link` refuses audibly (count +1, buzz asked); an unmirrored session with
   `not_mirroring` refuses audibly; a guest press on FieldHUD with that HUD Loading reads GuestQuiet, count +0, no line
   (a double tap inside the hide fade is ordinary at FadeDuration 300); the same press with the feature off for the pair
   refuses audibly (`key.loading_caps_off_older`; mutant `key_quiet_caps_blind`). Because the bench and an unmirrored
   guest are in a guest press, `menu_refusal.now` reads `audible` for them on FieldHUD/WorldHUD where s167 read `open`,
   and `count`, `lines` and `silent` also count guest-press refusals (intended; decision 32's re-keys).
   **Never write `UIManager.IsMenuControlEnable`:** it is a public field (`UIManager.cs:715`) that
   `FieldMapActorController.cs:167` reads to idle inactive actors. **Left unchanged:** Alt+F2
   (:510), Alt+F5/F9 and the harness `savemenu` (:572), BattleHUD's diorama refusal
   (`Global/battle/BattleHUD/BattleHUD.Scene.cs:586-597`), the `.eb` MENU and PARTYMENU refusals
   (`Global/Event/Engine/EventEngine.DoEventCode.cs:2364-2407`), SaveLoadUI's R4 and s38 guards, and **the dialogue
   path's read (:889), byte for byte** (skeleton D3). Any open window that sets `Dialogs.Activate` -- a persistent
   [NFOC]/[TIME=-1] kit HUD strip, or a transient stock window while it is up -- makes UIKeyTrigger skip the scene branch
   (it runs only while `!Dialogs.Activate` or paused, :660) and send Menu down the dialogue path, which returns on
   `!IsMenuControlEnable || IsMirroringStory` and otherwise calls `OnKeyMenu` (:886-891; DialogManager.cs:366-383 sets
   Activate for every dialog but the world-HUD event-cell case). So a mirroring guest's press there is s121's silent
   drop: the guest menu does not open while the location keeps a window up (a Known limit; GM0-HUDSTRIP measures it on a
   kit strip field). A non-mirroring guestSession player (the unmirrored guest, the bench) reaches `OnKeyMenu` there,
   whose HideAllHUD (FieldHUD.cs:257-258) closes that player's own window, line or strip, before the door: the door then
   refuses the unmirrored guest with `not_mirroring` and seats the bench (decision 9). `MenuKeyRoute` and
   `HarnessMenuKeyNow` report the route as s121 does, `dialog` for that silent drop.
   **Menu presses inside an open guest menu** take s121's step: a mirroring guest takes RefuseSilent (s38's drop) and
   counts under `menu_refusal.silent` with `last_state` = the menu state, as s121's silent path does; the bench takes
   s121's Open, whose stock `OnKeyMenu` on those screens is a no-op. Nothing visible changes. A proof row pins MainMenu
   and a sub-screen with guestSession true (mirroring) giving RefuseSilent. **Lever:** `netsync guestmenu old` = s121
   exactly.

7. **Who may open (the owner, 2026-11-06: refuse the unmirrored guest).** The `who` term is
   `NetSyncClient.WorldSessionHeld && IsMirroringStory`, or the bench `IsSelfTestRole && BenchGates`.
   `WorldSessionHeld` (NetSyncClient.cs:1298-1308) is s167's latch: a following client whose link carried a live peer,
   its session LIVE or in its GRACE, no exit ramp pending. The property has no gMode term (only NetSyncField's three s167
   reads add gMode 3), so it serves fields and the world alike, and a ~2.3 s stall never flickers it (the bare
   `IsLiveFollowedSession`, :1279-1291, flips at the 2 s cliff). A paired guest that is **not** mirroring yet -- paired or
   Continued on the world map, or a field-paired guest before its first arm -- is refused with the buzz and "You'll get
   the menu once you've followed your partner into a location." This closes s38's hole. The term sits before the caps
   term, so it is guest-local: an older partner does not reopen the hole. Because the bench is in `who`, a solo bench
   presses the REAL Menu key through the verdict (the critic). Out of scope, a Known limit: Alt+F9 Load for an unmirrored
   paired guest (pre-existing, its own lane). **Lever:** `guestmenu old` restores s121, the unmirrored open included.

8. **The open predicate, `GuestMenuWhyNot` (pure, cheapest first, one why each, null = open).** Every term but one is a
   read that already exists; the rule takes them as inputs. The exception is term 10's "no diorama armed": `_armed` is
   private and NetSyncDiorama exposes only `Active` and `Booted`, so W1c adds `internal static Boolean Armed => _armed;`
   in NetSyncDiorama.cs.

   | # | Term | Read | Why |
   |---|---|---|---|
   | 1 | the lever | `guestmenu old` off | `lever` |
   | 2 | who | decision 7 | `not_mirroring` (paired, unmirrored), `session` (mirroring, latch fallen) |
   | 3 | caps | `FeatureOn(WorldOwnCapsNow, PeerCapsOf(_wwCache.Latest), CapGuestMenu)` | `older` |
   | 4 | live | `IsLiveFollowedSession` and `GetRemoteState() != null`; the bench: `!DebugLinkDead` (NetSyncClient.cs:506) | `link` |
   | 5 | host place | trailer `Latest.Has`, place field (1) or world (4): no transition, battle, diorama or loading (NetSyncWorldWalk.cs:232-233) | `host_busy` |
   | 6 | host not fighting | section 7 b5 HfBattle clear (NetSyncDialog.cs:97) and `!NetSyncBattle.PeerBattleLive` (NetSyncBattle.cs:73) | `host_battle` |
   | 7 | menu data | section 12 present, fmt 1, in the latest fresh frame (`GetRemoteState`, `TryReadSection`, NetSyncState.cs:275); as built also a consistent block: section 12 names each present section-1 member exactly once and nobody else (`BlockMatchesPartyRule`; nothing about the install differs, so `no_data`, not `data_differs`) | `no_data` |
   | 8 | content witness | decision 13 | `data_differs` |
   | 9 | my control | `ee.GetUserControl()` (`Global/Event/Engine/EventEngine.cs:1431`) | `control` |
   | 10 | not busy | `BusyRule(Booted, GuestFollowFadeNow, FieldTransitionNow(), GuestSessionEndingNow) == null` (`NetSyncGuestLocal.cs:428-439`; NetSyncClient.cs:1467, :5297, :1488), with `FieldTransitionNow()` passed on a field only (as built: it reads "handed over" whenever FF9StateSystem.mode is 3, so passed on the world it would refuse every world press; the world's transitions are WT5's), `!BattleReturnInFlight` (NetSyncDiorama.cs:1345), no diorama armed, `!(NetSyncGuestLocalArmed.On && InFlightNow)` (NetSyncGuestLocal.cs:61, :596), `!NetSyncStepOutArmed.On`, `_worldOutCommittedTo < 0` (NetSyncClient.cs:289; here, not in WT5, so a field reads it too: a follow-out committed inside the opening window) | `busy` |
   | 11 | THE OPEN MIRROR | never open what a close trigger (decision 18) would close at once: the same rule, read as an open term. As built all eight causes map: `leave`, `out`, `rejoin`, `world` give `leaving`, `scene` gives `scene`, and `cut`, `ending`, `title` keep the why of the term that refuses them first in game (`host_battle`, `session`, `host_busy`), so the pure rule never returns null for a firing trigger; `cut` reads the close book's cut-nonce memory (decision 18) | `leaving`, `scene` |
   | 12 | UI quiet | `!NetSyncDialog.AnyEtbLine(false)` (NetSyncDialog.cs:322), `!SuppressLocalDialogInput` (NetSyncClient.cs:1395), `!UIManager.IsLoading` (UIManager.cs:97) | `ui` |
   | F1 | host here | `LastHostField == fld` (NetSyncClient.cs:415) | `host_elsewhere` |
   | F2 | no intent away | no section-4 intent with an unseen nonce and `0 < dest != fld`, `dest != FF9Define.FLDSCRPT_EVTNO_ENDING` (ServiceIntentFollow's own test, :10987-10999, which also excludes the ending pseudo-field). F2 and term 11's `leave`, and F3/F4 and term 11's `scene`, are separate named inputs filled from ONE read each (`FillIntentFacts`, `FillSceneFacts`), so each deletion mutant stays visible | `leaving` |
   | F3 | no host scene here | `GuestHostSceneWhy(fld) == null` (:1504): the host's scene here, a relayed talk deferred, held or on the lane, a pending relayed key | `scene` |
   | F4 | no windowless beat | `!(_glSceneField == fld && _glHostHoldsInput)` (:11723-11726): a door walk, a ladder | `scene` |
   | WT1 | my live world | `IsOnWorldNow` (:5803), `w_blockReady`, `ui.State == WorldHUD` | `world_busy` |
   | WT2 | HUD state | `WorldHUD.CurrentState` in {HUD, HUDNoMiniMap} (WorldHUD.cs:173) | `world_busy` |
   | WT3 | on foot | `CurrentCharacterStateIndex == 0` (WorldHUD.cs:14-16, 177): stock's silent rule, now audible | `riding` |
   | WT4 | not an event world, no full map | `!ff9.IsEventWorldMap`, `w_naviMode != 2` | `world_busy` |
   | WT5 | no world transition | `WorldTransitionWhy() == null` (:6049; it reads `_worldFollowArmed`, :6067), `_worldOutPending < 0` (:286) | `move` |
   | WT6 | host on the world, my world | `rs.Field <= 0` (a host on a field means a rejoin is due); `Latest` block valid and `Latest.World == wldMapNo`. As built the relay's 65535 host-field sentinel reads as 0 (no field) here and in term 11's serial `rejoin`, as FollowHostTick and the s144 overlay rows read it; otherwise every relay session on the world would refuse `leaving` | `leaving` |
   | WT7 | host not in a world scene | `(Latest.State & StScene) == 0` (NetSyncWorldWalk.cs:243-244) | `scene` |

   **The bench inputs (the selftest role).** The selftest is meant to press the real Menu key through the verdict and the
   seat, so every term has a named bench source: term 2, `IsSelfTestRole && BenchGates`; terms 3 and 5, the s166 bench
   host's trailer (`worldwalk host ...`, `hostplace 1|4`, `hostworld <id>`), which `guestmenu frame` also arms with my
   caps word, place 1 on a field or 4 on the world, and my world; term 4, `!DebugLinkDead`; term 6, `_benchState`'s
   section 7 b5 through the existing ops `netsync lock 1` (BenchHostTick builds `_benchState` only under the bench
   dialogue lock or the world bench host, NetSyncClient.cs:11825-11832; otherwise it is null) plus `netsync host battle 1`
   (DebugHostBattle sets b5, :11846); terms 7 and 8, a dedicated `_gmBenchFrame` slot that only
   `guestmenu frame` and `clear` write and that BenchHostTick never touches (it rebuilds or nulls `_benchState` every
   tick); F1, a bench host field equal to my field unless `guestmenu host elsewhere` moves it (`swap intent` leaves it on
   my field: a real host still stands on my field when it emits its intent; the selftest branch hard-sets
   `LastHostField` to -1 every Update, NetSyncClient.cs:2497, so F1 cannot read it there); F2, `guestmenu frame intent
   <field>`, which writes a section 4 with a fresh nonce and dest != my field into `_gmBenchFrame`, where F2 reads it;
   F3-F4, the existing bench ops (`swap hostctl off`, `hostscene`), the frame's sections 6/9 absent; terms 9-12 and
   WT1-WT5, the bench's own live state. `swap intent` marks its nonce seen and starts the real follow, so it fires the
   move-in-flight why (term 10's `busy`), never F2's `leaving`. As built the two slots are `_gmBenchFrame` and the bench
   host field (`_gmBenchHostField`), created empty in W1e and written by W1f's `frame`, `frame witness`, `frame intent`
   and `host elsewhere|here`; `frame` arms the s166 bench host directly (a one-point, 0 u/s path at my world walker, or
   at (1, -1) on a field), skipping `worldwalk host path`'s FollowHost and encounter-pause refusals (an already-running
   bench host keeps its path; only place and world are set, and the release puts them back). Until a `frame`, a bench
   press on FieldHUD/WorldHUD reads audible `no_data` (s167: the bench's own menu opened).

   **The terms the design refuses to add.** Never refuse on section 7 b4 HfMenu: that is the host's own menu, shop or
   pause, and *Both players in menus* allows it. Never `Dialogs.Visible` for "UI quiet" (the critic): it also counts a
   persistent [NFOC]/[TIME=-1] kit HUD strip, so it would refuse forever on such a field -- the same-field kick avoids it
   for that reason (NetSyncClient.cs:7218-7223). With a strip up, `Dialogs.Activate` is true on a field, so the press
   arrives through the dialogue path (DialogManager.cs:366-383, UIKeyTrigger.cs:659), whose s121 read stays (decision
   6): a mirroring guest's press there is the silent drop, a Known limit GM0-HUDSTRIP measures. Where a window is
   Visible without Activate (the world-HUD event-cell case) the press reaches the verdict, and on GuestOpen stock's
   OnKeyMenu runs HideAllHUD -> CloseAll on the guest's copy exactly as single-player does (FieldHUD.cs:257-258,
   UIManager.cs:592-598); the design follows stock. No host-menu flag on the world: the claim that the host's own main
   menu raises StScene (TWO-PC-CHECKS-S167.md:414) is unproven -- `SceneBitStep` clears the bit whenever control and the walker's
   visibility hold (NetSyncWorldWalk.cs:1323-1328), and `WorldHUD.Hide` changes neither (WorldHUD.cs:83-96). GM0-STSCENE
   measures it first; if it does rise, it is a Known limit with a later fix. Frozen (s144) and walking (s167) guests both
   qualify. **Lever:** `guestmenu old`; each term has a proof mutant that deletes it, and the bench ops below fire most
   whys in game.

9. **The door is the one open verdict; the seat is taken there (the critic's window).** A press does not change the UI
   state: `FieldHUD.OnKeyMenu` hides the HUD and only the Hide's callback calls `ChangeUIState(MainMenu)`
   (FieldHUD.cs:253-263, :410-413), one UIScene fade later (`Global/UI/UIScene.cs:74-88`); WorldHUD does the same with a
   delegate (WorldHUD.cs:177-182). For that fade (FadeDuration, clamped 0-5 s,
   `Memoria/Configuration/Access/Interface.cs:130`; 40 ms by default, 300 in the original game) every HUD-gated lane
   still reads FieldHUD or WorldHUD.
   - **At the press: a pre-check only** (decision 6). It refuses audibly or calls stock `OnKeyMenu`, and arms nothing.
     GuestOpen stamps one press deadline: the press time + CloseCapMs + the live FadeDuration, scaled as UIScene.Hide
     scales it (divided by FastForwardFactor under IsFastForward, UIScene.cs:81). The exit ramp's settle reads it (below;
     decision 18).
   - **At the door:** `UIManager.ChangeUIState` (UIManager.cs:601-641), when the current state (`this.state`, read before
     :607's `this.prevState = this.state`) is FieldHUD or WorldHUD, the new state is MainMenu, guestSession holds and the
     lever is not `old`, re-runs the whole predicate before anything else, for EVERY such entry, with or without a press
     verdict: the scene branch's press; the dialogue path's `OnKeyMenu` (UIKeyTrigger.cs:889, for a non-mirroring
     guestSession player: the unmirrored guest, the bench); WorldHUD's delegate (WorldHUD.cs:181); the script's `EventService.OpenMainMenu`
     (EventService.cs:104-112, refused first by SpectatorField for a following guest, EventEngine.DoEventCode.cs:2375, so
     only an unmirrored guest in GRACE reaches the door that way, and it is refused `not_mirroring`). The UI-quiet term's
     `AnyEtbLine(false)` and `!SuppressLocalDialogInput` are included: a line that arrives inside the opening window is
     caught here. Only `!UIManager.IsLoading` may be exempted, and only if the build measures it true there (AfterHide
     clears Loading before the Hide callback runs, UIScene.cs:95-96); as built the exemption is NOT taken, and the bench
     reads IsLoading at the door. As built (W1f) the door is the first statement of ChangeUIState's try, before
     `this.prevState = this.state`: `NetSyncGuestMenu.DoorKeyed(this.state, uiState) && NetSyncClient.GuestMenuDoor(this,
     uiState)`. DoorKeyed is true only while a seat record is held, or for a FieldHUD/WorldHUD -> MainMenu entry inside a
     guest session, so vanilla, a host and an unfollowed client run the stock body byte for byte; a held record is
     retried first at any HUD -> MainMenu door, guest session or not (decision 16). **If it passes,** the seat is taken there
     (decisions 11-14), before `MainMenuUI.Show` (UIManager.cs:615 calls it), which reads the party at once, and the
     guest-menu session begins at the seat (decision 16).
   - **What the window catches.** `FieldHUD.Hide` turns player control and events off (FieldHUD.cs:241-242), but the
     state still reads FieldHUD, so a follow, a boot or a relayed talk can fire inside the window. The door's state terms
     catch it: a follow already started reads term 10's `busy` (`FollowFadeInFlight` through GuestFollowFadeNow,
     NetSyncClient.cs:1467-1484; `_worldOutCommittedTo`; Booted and Armed), an intent not yet acted on reads F2's
     `leaving`, a host scene, a relayed talk or a pending ATE press F3/F4. Edge triggers consumed in the window (a relayed
     talk accepted there) are caught only through those state reads; with events frozen in the window, that coverage
     holds. After the seat no move can start: every move lane waits for the HUD (decision 18). The guest sees the door's
     refusal line for its why (a follow already started reads "Try the menu again in a moment."), never a forced-close
     line: the menu never opened.
   - **If it fails at the door,** the menu does not open: the door refuses and returns at the top of the body, before
     :607's `this.prevState = this.state` and before `this.State = uiState`, touching neither, so it keeps the HUD state
     and re-shows that HUD scene with its own Show (`GetSceneFromState(this.state).Show(null)`, the HUD state read before
     any assignment; never the `prevState` field, which at the door still holds the state before the HUD -- after any
     earlier menu close, MainMenu -- and would run MainMenuUI.Show unseated; `ChangeUIState(FieldHUD)` would be a no-op,
     the state never left the HUD), so `FieldHUD.OnShownAction` or `WorldHUD.Show` turns events and control back on
     (FieldHUD.cs:394-398, WorldHUD.cs:66-69); it buzzes and shows the why's refusal line (none once co-op is off,
     decision 10). As built: the HUD's own Show, then `NetSyncField.RefuseMainMenu(Audible, why, member, component)` (the
     buzz, the line, NoteRefusal) and `door_refused.<why>` +1. Nothing was seated, so the
     session never began. The door, the seat and the seat's fault path (decision 12) all run ahead of :607 and never read
     the `prevState` field. GM0-DOOR judges events and control back on, and that after one normal open and close a door
     refusal leaves MainMenuUI inactive and the state FieldHUD. The press already ran stock's HideAllHUD, so a window it
     closed stays closed after a door refusal, as after a normal open and close (a Known limit).
   - **The door's own fault path.** The whole door, open and restore halves, sits in its own try inside ChangeUIState's
     log-only catch (the re-check's ~25 terms, term 8's section-12 parse, the guestSession read and the restore test all
     run after the HUD's Hide has turned events and control off). A fault before guestSession is known true, with no held
     record, falls through to the stock body unchanged, so vanilla, a host and an unfollowed client never lose a state
     change. Once guestSession is known true, a fault takes the door's refusal path:
     `GetSceneFromState(this.state).Show(null)`, the buzz, why `fault`, one line (as built, the door's fault line is logged
     once per process), nothing seated. The verdict is the pure `DoorFaultRule`. A fault in the restore half against
     the same state keeps the record and the seat flag with the alarm line (only an identity or epoch mismatch drops
     it, decision 16), puts EnabledSubMenus back, then lets the stock body run; the next backstop or door retries the
     restore element-wise. The selftest-only `guestmenu door fault open|restore` injects each (GM0-DOOR's fault legs).
   - **The ramp never fires inside the window.** The exit ramp could arm and fire inside the fade: the world branch
     settles a free-roam world at once, and the field branch's settle reads the `.eb` usercontrol (EventEngine.cs:1431,
     which FieldHUD.Hide does not touch) and FieldHUD, both still true mid-hide. The Hide's callback would then reach the
     door with guestSession false (the fire drops `_storyMirroring`, NetSyncClient.cs:2035) and open stock's menu over the
     loading scene. So both branches' settle also reads "no press deadline in the future" (decision 18): the door runs
     first and refuses (`session`: the ramp's arm drops WorldSessionHeld while IsMirroringStory still holds), and the ramp
     fires once the deadline has passed. A bound of CloseCapMs alone would not cover a FadeDuration above it, so the
     deadline carries the fade.

   **Lever:** none of its own; `guestmenu old` reproduces OLD, and the proof's "seat at the press" mutant must fail.

10. **The guest's words (the owner, 2026-11-06: all three).** Words are seeds; the owner tunes them, as in s165-s167.
    - **A refused press:** the buzz on every press; one log line per place per why class (the DeclineOnce book, the world
      classes in s167 decision 20's per-visit re-arm; the `older` and `lever` whys write s121's own line, so "off" is
      s121 exactly); and a 4 s on-screen line naming the reason (s167's EntryLineMs idiom, NetSyncWorldWalk.cs:2613),
      ended at every scene change (as built: explicit clears at every field load, every world load, the title and the
      exit ramp's fire, plus a game-mode term -- a battle has no load hook, so `RefusalLineLiveRule` also ends the line
      when `EventEngine.gMode` differs from its arm's). Today the paired branch forces the overlay off every Update --
      "the ghost IS the status" (NetSyncClient.cs:2662-2665) -- so a new timed overlay state 29 (`OvlGuestMenuLine`,
      overlay name `guest_menu`) is chosen there in place of OvlOff while its timer runs (in the paired branch and in its
      blip-grace hold), and in the not-paired chain.
      **Where state 29 sits, ratified by the coordinator (the W1 review's CR-2).** In the not-paired chain it comes right
      after the wire-mismatch line, the reconnecting line (the session grace) and the world's lost-contact line
      (OvlWorldLost), and it is armed only while the peer is not lost (`NotPairedLineRule(lineLive, peerLost)` = lineLive
      && !peerLost), so the post-grace connecting line (OvlConnecting: the field chain's, and SetWorldGuestOverlay's own on
      the world) outranks it too. It never outranks those four. For its 4 s it does outrank everything below it in that
      chain: on the world the whole world-guest chain (OvlRejoining, the hold, host_world, and s167's entry-refused,
      walk-refused and close-map lines); on a field OvlFollowing, OvlWorldOut, OvlPeerNoField and OvlPeerElsewhere. Each
      comes back when the line ends. Moving 29 down to the OvlOff fallbacks was refused: a following world guest with the
      host on the world resolves to OvlHostWorld, not OvlOff, so almost every world refusal line would be hidden.
      So a refusal raised after co-op is turned off draws no line (state 29 is
      chosen only in the overlay chains past the enabled gate, NetSyncClient.cs:2057, and ApplyConfigChange nulls
      `_ovlText`, :1814): the buzz, the count and the log line only. One raised while the peer is lost (a `link` refusal,
      or one on a grace-expiry ramp, on a field or the world) shows only the connecting or lost-contact line; the buzz,
      the count and the log line still happen.
    - **A forced close:** one line naming the cause (decision 18's table), drawn by OnGUI for its own timer only (seed
      4 s, as EntryLineMs): nothing else ends it, and a newer close line replaces it. OnGUI already draws it independently
      of `_ovlText` (which ApplyConfigChange nulls) and of the overlay chain past the enabled gate, so a plain timer is its
      whole lifetime, and "the co-op session is ending" still shows when co-op is turned off while seated; it never uses
      overlay state 29. The cost: after a fast landing the line can stay about 2-3 s over the new field or the battle's
      opening (OnGUI draws above everything); the owner can shorten the seed. A refusal line and a close line can show
      together for a moment (a refusal, then an open and a forced close inside its 4 s); each ends on its own terms, so
      the harness reads them as two keys, `line` and `close_line` (decision 32). As built (W1h) the close line is armed at
      the close's request, unless the guest's quit prompt holds the close: then at the close's first act (its one Hide,
      or the watchdog's or the fault end's sweep or HUD Show), once per close, since a line armed at the request would
      say "menu closed" over a menu still open under the prompt.
    - **A "View only" chip while seated:** IMGUI at top centre beside the F3.2 dialogue chip (`OnGUI`, :15481;
      `DrawDialogChip`, :15512), which already draws above NGUI menus. As built it stacks below the dialogue chip when
      that one is up, keys on the seat flag (OnGUI reads `NetSyncGuestMenu.Seated` each frame), and `guestmenu chip off`
      (the selftest bench) is its in-game mutant (GM0-CHIP).
    - **Silent cases stay silent:** MENUOFF, the non-HUD states, the dialogue path's silent drop (:889, decision 6), a
      press while the HUD's Hide is in flight (GuestQuiet, decision 6).

    The words are listed under "The owner-visible words" below. **Lever:** `guestmenu old` (no line, no chip).

11. **The seat has its own bracket.** The diorama's bracket state (`_realMember`, `_realPlayer`, `_havePartySnapshot`,
    NetSyncDiorama.cs:2853-2855) is static with a single owner: `Disarm` restores it unconditionally (:1182-1186), and a
    failed Boot and the snapshot-failure path clear it (:999-1002, :815-818). Shared with a menu seat, a diorama teardown
    would restore or erase the menu's record, and the reverse. So the **first engine piece** (W1a) extracts that static
    bracket into an instance type with two instances, the diorama's and the menu's, behaviour-neutral, proven offline by
    `SeatSelfTest` (:2942) and the bracket selftest and in game by the round's regression set (the diorama legs). The
    per-slot scratch builder inside `MirrorHostParty` (:3106-3268) is extracted the same way in W1b (the
    decisions were silent on the builder and the lanes split; the seat lane's extract is taken because the s154 code
    itself warns that copies in this family rot). Never share the diorama's statics.
    **As built (W1a, W1b, extended in W1f).** The type is `NetSyncSeatBracket` (new `Memoria/Netsync/NetSyncSeatBracket.cs`)
    with Snapshot, RememberOriginalPlayer, Restore and Clear, each the s167 body verbatim with the owner's name (`Who`)
    spliced into its log words; the diorama holds `new NetSyncSeatBracket("diorama")`, so every log line is unchanged.
    s167 had no bracket selftest (the closest were the containment selftest's party rows, unchanged), so W1a adds a NEW
    proof line, `seat bracket selftest: OK (19 rows, 7 mutants caught)`, carrying the bracket's laws, GM0-BRACKET-CLEAR's
    two-instance rows and the no-cross-restore rows; it is logged in NetSyncClient's selftest proof block right after
    the world walk line (one NetSyncClient.cs hunk). The builder is `NetSyncDiorama.BuildSeatMembers(ff9, seat, bracket,
    overrides, rethrow)`, returning the count seated; `overrides` is a `Dictionary<CharacterId, SeatOverride>` (Preset,
    Category, Pa, Exp, BasisCapa; a present override applies all five, a null Pa keeps FF9Play_New's array, pa is always a
    fresh copy), keyed by CharacterId because section 12 is. With `rethrow` the faulting slot's scratch stays in the
    dictionary and its member slot untouched, for the caller's record to restore. The diorama passes `(null, false)` and
    is the only caller; offline its Arm -> seat -> Disarm transcripts equal s167's over seven scenarios. W1f added five
    methods over an explicit state (SnapshotOf, RememberOriginalPlayerOf, RestorePlayersInto, RestoreMembersInto,
    RecordedMember), so the menu's own instance is the record for the dictionary and the members; the diorama's four are
    byte-identical. SeatSelfTest cannot run offline (it reads live Unity state); GM0-BRACKET covers it in game.
    **Lever:** none (behaviour-neutral); the rollback is the patch.

12. **Seat by reference, from one frame.**
    - **By reference, never by content:** scratch PLAYERs go into `ff9.player[id]` and `party.member[i]` with the original
      remembered first (MirrorHostParty's idiom, NetSyncDiorama.cs:3162-3164); a fresh `List<FF9ITEM>` goes into
      `ff9.item` in the host's order; fresh `rare_item_obtained` and `rare_item_used` sets; gil by value. These are plain
      public fields (`Global/ff9/State/FF9StateGlobal.cs:938-976`). Never write through a guest object: the equip preview,
      ArrangeAuto, UseImportant and the deserializer all write through whatever is installed.
    - **From ONE fresh frame:** sections 1, 2, 3 and 12 of the frame read at the door, through PURE parsers: the
      `TryParsePartyInto` style (NetSyncParty.cs:259) plus new order-keeping bag and key-item readers. Never
      `ParseSections` (:220), never `NetSyncParty.Slots/_bag/_keyItems`, never `MirrorActive`: they are the read wraps of
      `B_PARTYCHK`, `PARTY_MEMBER` and `B_HAVE_ITEM` (the s154 SEAT LAW generalised).
    - **The surface:** `party.member[4]`; per member, the s154 derivation. FF9Play_New sizes `pa[]` from the default
      preset inside itself (`Global/ff9play.cs:135-139`), and the shared builder (W1b) runs FF9Play_Update itself right
      after setting basis.capa = BasisMaxCapa, so these writes go in through the builder's optional per-member overrides,
      each at its own point: right after `FF9Play_New`, `info.menu_type` (the wire presetId) and `category`, then `pa[]`
      re-allocated to the wire's paN and filled (the witness has already checked paN ==
      `_FF9Abil_PaData[preset].Length`); `exp` after FF9Play_Build (Build rewrites it, :229-230); `basis.capa` from
      section 12's basisCapa before the builder's own FF9Play_Update, replacing BasisMaxCapa. The diorama passes no
      overrides, so it stays behaviour-neutral. basis.capa decides cur.capa only under LockEquippedAbilities 1 or 3
      (FF9Play_Update reads cur.capa from it, ff9play.cs:279); in every other mode CalculateGemsPlayer re-derives
      cur.capa from max.capa. saForced/saBanish/saHidden are re-derived by
      FF9Play_Update from install data (no wire bytes). `bonus` and `permanent_status` are not seated: no screen reads
      them (the critic adopted the wire lane's census). Then the bag, the two key-item sets, gil.
    - **Not seated:** cards, Settings, gEventGlobal, frogs, kill and battle counters, non-party characters.
    - **All or nothing.** The door runs inside `UIManager.ChangeUIState`, whose body is one try/catch that only logs, so
      the seat carries its own fault path. FF9Play_New mutates the live dictionary entry, so a scratch PLAYER can only be
      built in place, and the order is: (1) write the complete record of every original reference first -- every
      `ff9.player` id the frame names, `party.member[0..3]`, `ff9.item`, both rare sets, gil and EnabledSubMenus; (2)
      build the PLAYERs in place through the shared builder, which installs as it goes, and build the bag list, the
      key-item sets and gil off-line; (3) install those last; (4) on any exception, or on any refusal raised after the
      build (a short seat: seated < memberN; an unknown bag id), restore from the record (decision 16's element-wise
      restore), so the session never begins, re-show the HUD with its own Show (`GetSceneFromState(this.state).Show(null)`,
      decision 9's refusal path), buzz, and refuse -- a short seat as `data_differs`, an exception as `fault` -- logging
      the component. The menu's call asks W1b's builder to rethrow (a `rethrow` flag; the diorama keeps its per-slot
      containment, whose catch would otherwise absorb a fault inside a slot). The door's seat call carries its own try,
      so the outer catch never sees it.
    - **As built (W1f).** The seat is the pure `NetSyncGuestMenu.SeatOver` over a given state and the frame the predicate
      just judged; it never records over a held record. There is ONE seat flag: `Seated` reads the seat record's `Held`.
      SeatOver also refuses an unknown bag id itself (component `bag`, rolled back), though the witness refuses it first.
      **One exception to "nothing seated":** if the rollback after a seat fault itself faults, the record AND the seat flag
      stay held, the door refuses `fault` and logs the alarm, so every consumer (the autosave term, the achievement hold,
      the chip, Boot's refusal) keeps gating while scratches may still be installed; the next backstop or door retries.
      The proof's two-marker round trip runs the real SeatOver and RestoreRecord with a probe builder of
      BuildSeatMembers' shape (the real builder reads the live state through FF9Play_New; its override and rethrow
      behaviour is W1b's offline proof and the in-game rows).

    **Lever:** `guestmenu old` (no seat). The selftest-only `restore skip <component>` is the mutant (decision 33);
    the selftest-only `guestmenu seat fault <component>` throws inside the seat, outside the builder's per-slot catch,
    so GM0-SEATFAULT reads `fault` (one shot, spent by the next seat).

13. **The content witness.** The open is refused with "Your game data differs from your partner's (<member>)." if any
    member's preset is missing on this install, its pa length differs from `_FF9Abil_PaData[preset].Length`, an
    equipment or SA id is unknown here (the diorama's ContainsKey guards, NetSyncDiorama.cs:3150-3165), or a member's
    CharacterId is unknown here (`ff9.player` or `ff9level.CharacterBaseStats` lacks it); it is also refused if the shared
    builder seats fewer members than memberN (it leaves an unknown member's slot EMPTY with only a log warning); that
    refusal comes after the in-place build, so it restores from the record (decision 12's all or nothing). The
    component is logged. Never seat a preset the guest lacks: `StatusUI` indexes `CharacterCommands.CommandSets[menu_type]`
    (`Global/StatusUI.cs:96`; a Dictionary, `Memoria/Database/CharacterCommands.cs:14`) and throws.
    - **The bag:** refused with the same `data_differs` words, component "bag", when any section-3 id fails
      `ff9item._FF9Item_Data.ContainsKey`; the id is logged. ItemUI indexes that throwing dictionary for every bag row and
      in Auto sort, and the kit's [[item]] pillar mints ids a partner may lack. This also guards EquipUI's candidate lists,
      which read the bag.
    - **Key items:** unknown ids are seated unchanged (stock tolerates them with a blank name, FF9TextTool.cs:475) with
      one line naming them; they are never refused.
    - **As built (W1c):** equipment and SA ids are checked from section 1, where the wire carries them; NoItem (255)
      never refuses and negative SA ids are skipped, as the builder skips them; the member's name in the line comes from
      section 1, else `character <id>`; a member with no section-12 entry would report component `preset`, a defensive
      branch only, since term 7's consistency rule refuses that frame first as `no_data`.

    **Lever:** `guestmenu old`; GM0-WITNESS's mutant (seat anyway) must throw.

14. **While seated.**
    - **No Master Skill:** `MainMenuUI.Show` calls `SetMasterSkill` (MainMenuUI.cs:49) on every return to MainMenu, from
      eight sub-screens. With the booster on it walks `PlayerList x item` (`Global/SettingsState.cs:389-412`) and writes
      `pa[]` on the guest's REAL benched characters, which no party seat brackets. Skip it on every Show while seated.
    - **Achievements held:** the seat joins AchievementManager's two holds beside `NetSyncDiorama.HoldAchievement`
      (`Assets/SiliconSocial/AchievementManager.cs:80`, :119), so a seated bench (not mirroring, not booted) never reports
      to the platform.
    - **Own-party readers read the record:** the ghost dress's `LiveSlotChars` (NetSyncVisitor.cs:326) reads the seat
      record's real member refs. The read goes inside LiveSlotChars itself, so every caller is covered: the client ghost
      through ResolveDress (NetSyncVisitor.cs:256, from NetSyncClient.cs:2683) and the host and bench paths through
      ReadSlotChars (NetSyncClient.cs:13969).
    - **The autosave ladder keys on the seat:** EventEngine's autosave ladder gains the seat as its own term, the
      `Booted` precedent (EventEngine.cs:703-704). The ladder ORs in SuppressEncounters, IsMirroringStory and Booted, and
      nothing for the selftest role, so it is the one save gate where the bench, a possible seat holder, has no term.
      The other three save gates are not edited, because every possible seat holder is already refused by terms that
      exist. A mirroring guest: s38's Alt+F5 gate (UIKeyTrigger.cs:572), `ManualSaveRefusedNow`'s M term
      (NetSyncField.cs:921-930, called at SaveLoadUI's two Save sites ahead of the s38 floor) and PairingDurableVerdict's
      `OwnStoryNow` (NetSyncClient.cs:5369, :5565). The bench: `ManualSaveRefusedNow`'s B term, and `PairingWindowTick`
      returns on any role but client (:5541-5544). From the main menu SaveLoadUI cannot be reached (no Save row;
      TryShowSaveScene needs FieldHUD/WorldHUD, UIKeyTrigger.cs:603-615), and `PairingFreeStanding` needs the
      FieldHUD/WorldHUD state (:5677-5690); but in decision 16's restore-fault cell the seat stays held on a live
      FieldHUD/WorldHUD, where both are reachable, and the terms above are the guard there. The layer this gives up is
      named in the Known limits.
    - **Never with a diorama:** the open is refused while a diorama is booted, armed or returning (`Booted || Armed ||
      BattleReturnInFlight(ee)`, decision 8's new `Armed` accessor); and the diorama's Boot
      refuses while a seat is held -- in `Boot`'s own refusal (NetSyncDiorama.cs:752-756), **never** in `MayBoot` /
      `MayBootNow` (:635-639). This changes the skeleton's D8, which put the term in MayBoot (and the seat lane's "a term
      in MayBoot"): MayBootNow feeds BootWatching (NetSyncClient.cs:4698-4701), so a seat term there would turn decision
      19's BOOTING into NONE. It is listed under Departures from the skeleton for the coordinator to ratify. Arm snapshots
      whatever is installed as "the guest's own" (:1173-1180), so a boot over a seat would restore the menu's scratches
      after the battle. The battle-cut close restores first.
    - **EnabledSubMenus:** set before Show to {Item, Ability, Equip, Status, Folklore}; stock greys Order, Party, Card
      and Config and buzzes 102 on them (IsSubMenuEnabled, MainMenuUI.cs:386-393; the labels :64-74; the row confirm
      :152, :239-242). Order and Party are *Party order and row*. Card and Config are a coordinator scope call (the
      owner's calls): Card shows the guest's own MiniGame cards, not the seat, and Config's settings revert at the
      session's end anyway (every load restores `50000_Setting`, JsonParser.cs:265-266); greyed, neither needs a census
      hook or a close step. The Folklore row is the Journal when `[Journal] Enabled` (:216-220): one `SubMenu.Folklore`
      row either way (the SubMenu enum has no Journal entry, :946-958), so the set needs nothing more. Its earlier value
      (empty outside battle) is put back on every restore path, drops and faults included (decision 16).
    - **As built (W1f):** MainMenuUI.Show skips SetMasterSkill while seated (`master_skipped`); both AchievementManager
      holds gain `NetSyncGuestMenu.HoldAchievement` (`ach_held`, one line per seat); the autosave ladder gains
      `AutosaveSeatTerm` after Booted's; Boot refuses in its own `BootSeatRefused` after MayBoot (MayBoot and MayBootNow
      untouched); LiveSlotChars reads the record's real member references.

    **Lever:** `guestmenu old`. GM0-MASTER, GM0-SAVEGATES, GM0-DIORAMA and GM0-GHOST each carry a mutant.

15. **Seat once per open.** s168 seats once, at the door (decision 9); the copy is the host's party as of the open until
    the restore door. `MainMenuUI.Show` re-reads the party on every return to MainMenu (each sub-screen calls
    `ChangeUIState(MainMenu)`, and Show reads the party, MainMenuUI.cs:38-77), so it re-reads the same seated objects:
    nothing else writes `ff9.player`, `party.member` or `ff9.item` while screens are open. The view goes stale if the host
    equips, levels or reorders while the guest's menu is open: rung 0 is view-only, so a stale view writes nothing, the
    restore record from the open stays exact, and Cancel then reopen refreshes it; a host scene, battle or departure
    already closes the menu (decision 18). The guest's item sort (*Item sort*) simply lasts until the close. s169 adds
    only the re-seat it needs, decision 25's: member C alone. Story bytes the screens read (gEventGlobal[16] in the Status
    trance gate, the NOMAGIC flag, the chocobo bytes) stay the guest's last field-load mirror: a Known limit for rung 0.
    **Lever:** `guestmenu old`.

16. **The restore: one door, the same state, the backstops.**
    - **The door:** `UIManager.ChangeUIState` (UIManager.cs:601-641) when the current state (`this.state`, read before
      :607's `this.prevState = this.state`) is in the menu family (`IsUIStateMenu`, :666-669: MainMenu..Tutorial,
      QuadMist, Chocograph, Folklore, Journal) and `uiState` is not -- never the `prevState` field, which at the top of
      the body still holds the state before the current one (FieldHUD/WorldHUD on a root close), as decision 9 says for
      the open door -- at the top of the body, BEFORE the new scene's Show (:615), so before SetEventEnable(true) and
      before any HUD-gated lane can run.
    - **The same state only:** restore only if `ReferenceEquals(FF9StateSystem.Common.FF9, seat.State)` and no
      deserialization ran since the seat (a load epoch counter bumped at the top of `JsonParser.ParseToFF9StateSystem`,
      `Global/JsonParser.cs:251`). Otherwise DROP the record without writing, with one line. A title load builds a new
      FF9StateGlobal, and an in-game load writes through the installed objects (`ParseCommonJsonToData`, :1126-1141).
    - **Idempotent and element-wise:** the dictionary originals back by reference, `Array.Copy` into the live member
      array (RestoreParty's shape, NetSyncDiorama.cs:3274-3296), the bag and key-item sets back by reference, gil by
      value; one try per family. The record is cleared only once every family is back, or by the identity rule's drop
      (an identity or epoch mismatch, above). A fault against the same state keeps the record and the seat flag and logs
      the alarm line; the next backstop or door, either direction, retries element-wise before anything else (each
      family's restore stays idempotent; a HUD -> MainMenu door that still holds a record retries it first and refuses
      `fault` if it fails again, so a scratch is never recorded as an original). EnabledSubMenus is put back on every
      path, drops and faults included, outside the identity rule: it is UI state, not FF9StateGlobal.
    - **Backstops, each with a loud "should never happen" line** (except the two expected paths below: a Replace("Title")
      and a ramp fire the quit prompt held). The top of the static `SceneDirector.Replace`
      (`Assets/Scripts/Common/SceneDirector.cs:114`), where it covers the swirl branch too: it restores at once, logs its
      alarm and ends the session there; it requests no close. **The soft reset and any Replace("Title") restore quietly,**
      with no "should never happen" line: the guest's own soft reset to the title (UIKeyTrigger.cs:344-395, no netsync
      guard) is an expected path; the alarm stays for every other target. A Replace that really loads sweeps the menu at
      `OnLevelWasLoaded` (UIManager.cs:234-264). A Replace DROPPED while seated (the instance Replace and Swirl return
      while IsFading, SceneDirector.cs:516-519, :540-543) is a double fault: while seated, events and the world frame are
      frozen (attr 0x102), the follow, diorama and world-out lanes wait for the HUD, and the ramp has its own backstop, so
      the only live Replace caller is the guest's own soft reset. If it happens, the open menu shows the guest's own
      restored objects until the guest Cancels: the census is inert there (it keys on the seat), a stock handler whose
      cached screen index no longer matches the restored list can throw (UIKeyTrigger.Update runs it inside a try: logged,
      not a crash), and any change touches only the guest's own objects, which a mirroring guest cannot save (the s38 and
      s165 gates) and the exit ramp's own-save reload discards (a Known limit).
      Then the exit ramp's fire, BEFORE `ExitMirrorToOwnSave` (NetSyncClient.cs:2048), because the deserializer runs
      before `ReplaceLoadMap` (NetSyncState.cs:315-329); when `QuitScene.isShowQuitUI` while a seat is held, the fire first
      calls `QuitScene.Hide()` (decision 21 step 1). The fire's `QuitScene.Hide()` and its backstop sit in their own try,
      which logs once per process and always falls through to ExitMirrorToOwnSave (that region has no enclosing try,
      decision 21). A guest who left the quit prompt up is an expected path (GM0-QUIT), so when the prompt held the close
      at the fire the backstop restores quietly, under its own key `restore.backstops.ramp_quit` and its own plain line;
      every other ramp-fire backstop keeps the alarm. And the Alt+F9 load entry (`TryShowLoadScene`,
      UIKeyTrigger.cs:618-622, which has no UI-state gate): it restores and ends the session, as the Replace backstop
      does.
    - **The session is the seat.** The guest-menu session begins at the door's seat (decision 9) and ends when the seat
      flag clears, at exactly these points: the restore door, after its restore or drop, on any menu-family -> non-menu
      exit (a restore fault against the same state keeps the record and the seat flag, above); a seat fault (decision 12:
      nothing seated); the Replace backstop; the ramp's fire backstop; the load-entry backstop; `OnLevelWasLoaded`,
      `TitleTick`, or any `UIManager.UnityScene` change from the seat's. Every consumer keys on it: the census, the
      chip, the Master Skill skip, the achievement hold, LiveSlotChars, the autosave term, the world ramp's settle term
      and the close request.
      **A forced close is its own record** (cause, request time). It is requested only while seated -- a close request
      with no seat does nothing -- and it outlives the restore door until decision 21's step 5 (the HUD's Show turned
      events back on) or the watchdog's end; it ends early at `OnLevelWasLoaded`, `TitleTick`, a UnityScene change or the
      ramp's fire.
      **A co-op session end (ApplyConfigChange, the ramp's arm, a transport stop) is never a clear point while seated.**
      ApplyConfigChange arms the ramp for a mirroring guest (NetSyncClient.cs:1803-1808), and the ramp requests its close
      (cause `ending`) and its settle holds the fire until the close has reached the HUD (decision 18). Where the ramp will
      not arm (`!_storyMirroring`: the selftest role), ApplyConfigChange itself requests the `ending` close, serviced by
      the pre-gate tick (decision 21). Proof rows: a config edge while seated leaves the session held and the close
      pending; after a normal stock Cancel the session and close-pending flags read clear, and a following `fireclose` is
      a no-op with no watchdog line (GM0-REOPEN too).
    - **As built (W1f, W1h).** The restore is `RestoreRecord` / `RestoreFamilies`; every backstop and clear point goes
      through `GuestMenuEndAt(site)`, its lines decided by `SessionEndsRule` / `BackstopLineRule`; the alarm lines are
      Log.Warning. The load epoch is `NoteDeserialize` at ParseToFF9StateSystem's top while seated. `OnLevelWasLoaded`,
      `TitleTick` and a UnityScene change restore through the identity rule, with the alarm, if a record is somehow still
      held (`restore.backstops.scene`); a family fault there keeps the record and the seat, the fault rule above winning
      over "the session ends at the clear point". A forced close's record ends at the same points: their gates (and the
      ramp-fire backstop's) read `SeatedOrClosing`, not `Seated`; the backstop's `QuitScene.Hide()` stays keyed on
      `Seated`.

    **Every close path ends in a restore or a drop:**

    | Path | How it reaches the restore | Restore or drop |
    |---|---|---|
    | Normal cancel | MainMenuUI's root cancel: Hide, then `ChangeUIState(HUD)` (MainMenuUI.cs:329-346) | the door |
    | A forced close (each trigger) | THE CLOSE ORDER LAW ends in `ChangeUIState(HUD)` | the door |
    | The watchdog | in the menu family on the request's UnityScene: the held-bit write, the stock scene-load sweep, then `ChangeUIState(HUD)`; on FieldHUD/WorldHUD with step 5 not reached: the held-bit write and that HUD's own Show; any other state: the close ends, one line (decision 21) | the door; already restored in the last two |
    | A door refusal (the press-to-door window) | nothing seated; the HUD re-shown with its own Show (decision 9) | nothing to restore |
    | Gysahl Greens (refused at rung 0) | ItemUI.WaitForFade -> `ChangeUIState(WorldHUD)` (ItemUI.cs:979-995) | the door |
    | The exit ramp's arm | the ramp's close request at the arm (decision 18); the field settles only on FieldHUD and the world's settle reads the seat, so the fire waits for the close, bounded by ExitRampSettleMaxMs | the door |
    | A config edge with no ramp (`!_storyMirroring`: the selftest role) | ApplyConfigChange's own `ending` close, serviced by the pre-gate tick (decision 21) | the door |
    | The exit ramp's fire | `QuitScene.Hide()` if the quit prompt is up, then the backstop before `ExitMirrorToOwnSave`, both in their own try: quiet (`restore.backstops.ramp_quit`) when the quit prompt held the close, else "should never happen" on either branch | restore, else drop |
    | A dropped Replace | the Replace backstop restores and ends the session; the menu stays open over the guest's own objects until Cancel (a double fault, a Known limit) | the backstop; the door finds no record |
    | A soft reset to the title | `SceneDirector.Replace("Title")` from any state (UIKeyTrigger.cs:344-395): an expected path, restored quietly, the session ended there | the Replace backstop (quiet) |
    | A scene load's sweep | `OnLevelWasLoaded` deactivates menu scenes without their Hide (UIManager.cs:234-264); the load began at Replace, whose backstop ended the session | the Replace backstop first; the door finds no record |
    | A world load | `OnLevelWasLoaded` issues no ChangeUIState for the WorldMap | the Replace backstop |
    | Alt+F9 load (refused for a mirroring guest at :572) | `TryShowLoadScene` -> Serialize, a menu state | the load-entry backstop, which ends the session |
    | The quit confirm | over the menu; quitting (`ConfirmQuit`, QuitUI.cs:133-139) writes no save (the seat lane's census of the OnQuit handlers); a cancel returns to the seated menu | nothing to do; a forced close waits for the player's answer, its watchdog paused (decision 21 step 1); the ramp's fire hides the prompt first |
    | The state replaced (title New Game or Load) | a new FF9StateGlobal, built only inside the Title scene, after a Replace("Title") whose backstop already restored and ended the session | nothing left; the identity rule would drop, one line |
    | Link death | the menu stays open as a view (decision 20) and closes at the ramp's arm | the door |
    | Process death or a crash | nothing ran | none needed: no save is written while seated (decision 14) |

    **Lever:** the selftest-only `restore skip <component>` (the mutant); the backstops have none (their line is the
    alarm), so a "backstop off" mutant is proof-only, never on disk. **The identity rule is proven offline:** the proof's
    restore-identity rows (EnabledSubMenus put back on the drop path among them) test the pure rule, and GM0-LOAD covers
    the one in-game path that changes the state under a seat, a load, where the load-entry backstop restores first. No
    in-game row swaps the state: the only construction of a new FF9StateGlobal is `CommonState.Init` (CommonState.cs:15),
    through `FF9StateSystem.ReInitStateSystem` (FF9StateSystem.cs:64-67), whose only callers are TitleUI.cs:349 and :976,
    inside the Title scene, so after a Replace("Title") whose backstop restored first. The cost: a wiring error that made
    the real door's identity read always TRUE would show nowhere (only an always-false one reddens GM0-RESTORE); it would
    be harmless only because every route to a new state or a deserialization passes a restoring backstop first.

17. **The rung-0 confirm census.** Every hook keys on the **seat flag alone**: vanilla, solo and the host run byte-for-byte
    stock (B4's "keyed on Active alone" law). Each refusal reuses the screen's own neighbouring stock buzz branch at the
    same group depth, above the first write and above `ImpactfulActionCount++`: no tween, no group change. Mouse clicks
    route into OnKeyConfirm (UIScene.cs:208-258), so the confirm hooks cover them. Paths are `Global/`.

    | Id | Site | Hook (file:line) | What it writes | The refusal (stock template) |
    |---|---|---|---|---|
    | E1 | Equip > equip a piece | `EquipUI.cs:183`, after the NoItem check (:178-182), before :184 | ImpactfulActionCount, the Moonstone counter (outside any seat), FF9Item_Add/Remove, the slot, FF9FEqp_UpdatePlayer (:184-199) | the NoItem branch: 102, return (:180-181) |
    | E2 | Equip > Off (remove) | `EquipUI.cs:225`, before :227 | ImpactfulActionCount, Moonstone, FF9Item_Add, the slot (:227-237) | the weapon-slot buzz and its read-only redraws (:245-252) |
    | E3 | Equip > Optimize (and the Shift "Ability" optimize) | `EquipUI.cs:315`, before :316 | ImpactfulActionCount, then Add/Remove through EquipStrongest or CharacterEquipment.Change | 102, the sub-menu group kept |
    | A1 | Ability > support ability, Confirm | `AbilityUI.cs:416-419`, after abilityType, before :419 (both Enable and Selected) | ImpactfulActionCount, FF9Abil_SetEnableSA, cur.capa, FF9Play_Update (:421-483) | the CantSpell branch (:487-490) |
    | A2 | Ability > support ability, Special | `AbilityUI.cs:625-628`, before :628 | the same, with a full hierarchy fill (:630-705) | :709-712 |
    | A3 | Ability > field ability use | `AbilityUI.cs:502-504`, before FieldCalcMain (:512) | target HP and status, caster MP, the AA usage counter and whtMag_no, both outside any seat (:512-538) | the no-effect branch (:542-545) |
    | I1 | Item > use on a target | `ItemUI.cs:408`, before :410 | target HP and status (FieldCalcMain, :416), ImpactfulActionCount, FF9Item_Remove (:429-431) | :447-450 |
    | I2 | Item > Gysahl Greens | `ItemUI.cs:321`, before :323 | gEventGlobal[vegetable] (:969), a dialog and its own close to WorldHUD (:973-995), Remove | :332-335 |
    | O | Order and row | MainMenuUI row confirm (:152) | party.member swap, info.row (ToggleOrder, :633-650) | EnabledSubMenus greys it; buzz (:239-242) |
    | P | Party (when the row exists, :751) | MainMenuUI row confirm (:224-236) | FF9Play_SetParty on the guest's real benched PLAYERs | EnabledSubMenus greys it |
    | CG | Card and Config (a coordinator scope call, decision 14) | MainMenuUI row confirm (:152) | Card: the guest's own MiniGame cards (the discard, `Card/CardUI.cs:80`), never seated; Config: the guest's own settings, its Booster panel (Master Skill pa[] on every character, SettingsState.cs:389-412), Return to Title and the controls tutorial | EnabledSubMenus greys both; buzz (:239-242) |

    - **Local writes allowed on the copy, lost at close:** item sort, Auto and manual (ItemUI.cs:296, :453-461); the
      key-item read marker (FF9Item_UseImportant, :855, reached by both Confirm and Cancel of a description, :249-253)
      and Folklore's (`FolkloreUI.cs:246`). The menu has no key-item "use".
    - **No backstop at the write primitives:** browsing Equip reaches them (the stat preview writes the candidate and runs
      FF9Play_Update twice, `EquipUI.cs:565`, :571). The bench backstop is a close-time fingerprint of the state OUTSIDE
      the seat: gEventGlobal, the Achievement and EventState counters, MiniGame cards, hintmap_id (GM0-OUTSIDE).
    - **The ~ menu:** its scene changes are HUD-gated, so none fires from inside the menu; its HealParty, GiveItem and
      GiveGil rows have no UI gate and land on the scratches, discarded at the restore (the critic's finding, taken over
      the seat lane's proposal to refuse them, because the reference seat already contains them). A Known limit.
    - **MenuOpenEvent on the world:** every MainMenu Show on the world map (the open and each sub-screen return)
      requests the guest's world copy's UID 0, tag 4 (UIManager.cs:581-589). K1 reads tag 4 in the deployed dispatchers;
      GM0-WORLDTAG4 compares the runtime state before the open and after the close on 9010 and 9011 (as built, through
      the review's settle stamp and its `uid0_vars` / `sysvar192` keys, decisions 32-33).
    - **Chocograph is out of scope:** it is opened only by a script (EventService.OpenChocoGraph, menu 5;
      EventService.cs:60-69 writes hintmap_id) or by WorldHUD's chocobo menu (WorldHUD.cs:1154), never from the guest's
      main menu. The open's WT3 riding term keeps a seat away from the world entry, and decision 18's "never a
      script-opened menu" covers the close.
    - **As built (W1g).** Eight hooks, each `if (NetSyncGuestMenu.Seated && NetSyncGuestMenu.CensusRefuses(site, detail,
      State)) { <the screen's own 102 template> }`, insertion-only (no stock line changed), each above its site's first
      write and its ImpactfulActionCount++; a static check proves every such write in the three screens' confirm handlers
      sits behind a hook. E2 copies the weapon slot's stock branch (102, then its three read-only redraws, return) rather
      than editing `if (this.currentEquipPart != 0)`. A1/A2 pass `abilityType` as detail and also refuse a forced
      Selected (stock buzzes there without writing; counted). A3 and I1 hook the target confirm's top, before
      FieldCalcMain, so a confirm FieldCalcMain would judge no-effect is counted too. E2 on an empty non-weapon slot is
      refused and counted. An unknown site, or a fault inside CensusRefuses while seated, refuses (fail closed). One line
      per site per seat. `captures` counts the confirms the census caught; `passes` (added) counts those `capture off` let
      through, which `seat_fp` (stamped only at the seat) cannot show.
    - **The outside fingerprint (GM0-OUTSIDE), as built:** five components, stamped inside StampFpBefore and
      StampFpAfter and judged by decision 33's verdict law (`fp.outside_equal`, `fp.outside_named`): `events`
      (gEventGlobal without bytes 2032-2041, NetSyncState's co-op window that co-op writes every Update; without the mask
      every live duo run reads red), `eventstate` (gStepCount, gAbilityUsage order-free, and the script store
      gScriptVector / gScriptDictionary), `achievement` (every public instance field of AchievementState), `cards` (in
      order, plus sWin, sLose, sDraw) and `hintmap`.

    **Lever:** `guestmenu capture off` (the changing confirms run their stock bodies into the SEATED copy).

18. **The forced closes: one `CoopCloseGuestMenuIfDue(site)`, asked FIRST at every waiting site.** Modelled on s167's
    `CoopCloseFullMapIfDue` (NetSyncClient.cs:9946-9999). A pure rule over the host's facts names the cause; the site
    keeps deferring exactly as today (the close is a request, idempotent, and with no seat it does nothing), and the
    follow, rejoin or boot fires on its own first HUD frame, as DL-DEFER already proves. The close never starts a follow.
    No move can start after the seat, because every move lane already waits for the HUD: FollowHostTick returns unless
    FieldHUD (NetSyncClient.cs:5135-5136), ServiceIntentFollow defers without marking the nonce seen (:11012-11013),
    WorldOutStep returns at its FieldHud term (`NetSyncWorldFollow.cs:479-480`), WorldArmRefusal's first gate is the world
    HUD (:5836), and DioramaTick has its UI gate (:3753-3756). **Scope:** only the guest-menu session (the seat). Never
    Pause or the quit confirm (s164's MENU legs hold Pause across the host's exit), never a script-opened menu, never the
    ~ menu, never the full map (s167 owns that close). Decisions *The host leaves the field* and *The host starts a
    battle* make one rule: the guest's menu never outlives the host staying put.
    **It never throws:** its own try, one fault line per process, `closes.faults` +1 (CoopCloseFullMapIfDue's idiom).
    Two of its sites sit in NetSyncClient.Update's pre-gate region, which has no enclosing try: the request at the
    ramp's arm and ApplyConfigChange's explicit request (called from the unwrapped config poll). An escaped throw there
    would abort every Update before ServiceFollowWarp (the s42 never-abandon law), or, inside the ramp settle's try{},
    leave `safeToLoad` false every frame so the ramp never fires, not even at ExitRampSettleMaxMs. So the arm-site
    request also sits outside the settle's try{}.
    **The Id column** names each trigger: `closes.<id>` and `last_close.cause` (decision 32), `fireclose <id>`
    (decision 31) and the fakegame's `<id>_ignored` faults use it. The Close words column names the drawn line only
    (the owner-visible words), never a key.

    | Id | Trigger | Signal | Where it is asked (anchor) | Close words |
    |---|---|---|---|---|
    | `leave` | Host leaves a field for a field | an unseen section-4 nonce naming a real field other than mine; or the serial candidate due (FollowStableMs 1200) | ServiceIntentFollow before its HUD defer (:10993-11013); FollowHostTick before its HUD return (:5119-5137) | following |
    | `out` | Host walks out to the world | section 7 b6 HfWorld (NetSyncDialog.cs:100) for a follower past the world-out's first terms; WMAPJUMP emits no intent | WorldOutTick (:7465), ahead of WorldOutStep's FieldHud term | following |
    | `rejoin` | Host enters a place from the world | the gMode-3 MAPJUMP intent (EventEngine.DoEventCode.cs:1040) or the serial world branch (:5127-5131) | WorldFollowFire, beside the full-map close (:6153) | following |
    | `world` | Host changes world without a field | the trailer's world valid and not my wldMapNo | inside WorldLaneStep (:8940), immediately after WorldCacheStep (:8944) and before its `if (line == LineNone) return;`, which returns on every Update with no lane edge; client role only (WorldLaneStep runs for both roles and the bench, :2639, :8834); no follow lane exists, and whether stock ever does this is unverified | following |
    | `cut` | The host's battle cut, at EVERY cut, booted or not | the battle lane live on a host battle nonce this session has not yet closed for (TryGetPeerBattleOpen, NetSyncBattle.cs:4506); section 7 b5. A later open in the same fight is still refused by term 6. As built the memory of the last closed nonce (the pure `CutMemoryRule`, the W1 review's LC1) is set at every accepted cut request, forgotten at a host epoch change and at the session reset (`ResetGuestDedupForEpoch`, `ResetIntentAndL1State`: a relaunched host restarts its Byte nonce, which also wraps at 256), spent when a different nonce goes live (`NoteCutLive`, DioramaTick's live branch), and kept through staleness (B3.6: staleness is not a battle boundary) | the top of DioramaTick's live-nonce branch, after `if (!live) return` and before the skip check (:3697), so ahead of WorldBootWaits (:3751) and the UI gate (:3755): a scene not on this install or a late join stamps the skip nonce on the first tick; NoteBootWatch (:4537-4552) | battle |
    | `ending` | The exit ramp armed (both branches) | `_exitRampPending` (set at :1805, :1839, :2146, :7821), while seated; where no ramp arms (`!_storyMirroring`: the selftest role), ApplyConfigChange's own explicit request (decision 16) | the ramp's tick at its arm, ahead of its settle (:1965-2020; THE RAMP'S SETTLE below); ApplyConfigChange (:1773-1812) for the explicit request | ending |
    | `title` | The host at the title | section 7 b7 HfTitle (NetSyncDialog.cs:101) | each Update, beside ServiceDialogAuthority (:11574) | title |
    | `scene` | A host conversation, chest, ATE or scene on my field (the owner, 2026-11-06) | a relayed talk or chest start for my field (sections 6/9); the s161 relayed ATE press for my field; section 7 b0 HfScene with the scene field mine (`_glSceneHere`, :11723-11726) | ServiceTalkFollow before its defer (:12677); NetSyncAte.Tick (`NetSyncAte.cs:978`); ServiceDialogAuthority | scene |

    **Lever: one, `guestmenu close old|act`.** `old` is today's defer-only behaviour for every trigger at once. Each
    trigger is proven in isolation offline: the proof line's close-rule rows carry one mutant per trigger, deleting that
    trigger's row. Each GM0-<trigger> bench row fires exactly one trigger, so `close old` reproduces that row's
    defer-only behaviour, each leg predicted under THE CAL RULE (GM0-TITLE's: no ramp arms while the host sits at the
    title, since it keeps its link live, so the menu stays seated until the leg's own Cancel).
    The cost: there is no in-game way to switch off one trigger while the others stay live; isolating one misbehaving
    trigger on the two-PC sheet needs a rebuild, or the whole `close old`. The battle cut closes at every cut, booted or
    not: *The host starts a battle* read literally, and the critic ruled this is not an owner question (`BootMapRule` is
    the full map's rule, and the full map is not the main menu). The host-at-title close has its own id, `title` (the
    critic's row filed it under leave); its words are a seed: "FF9 co-op: menu closed -- your partner is at the title
    screen.", on the owner's tune list.
    **As built (W1h).** `CoopCloseGuestMenuIfDue(cause[, arg])` keys on the seat first, has its own try, fills ONE reused
    GmCloseFacts with the site's signal and asks `TriggerFires`. It is asked first at eleven NetSyncClient sites: the
    ramp's arm (outside the settle's try), ApplyConfigChange when no ramp arms, `title` beside ServiceDialogAuthority,
    `cut` in DioramaTick's live-nonce branch before the skip check, the serial `leave` in FollowHostTick and the intent
    `leave` in ServiceIntentFollow (each before its HUD defer), `rejoin` in WorldFollowFire ahead of the full-map close,
    `out` in WorldOutTick, `world` in WorldLaneStep right after WorldCacheStep, and `scene` in ServiceDialogAuthority and
    in ServiceTalkFollow; and at NetSyncAte.Tick's `scene` site. Three narrowings: a close is asked only from a
    menu-family UI state (a seat kept on a HUD by a restore fault would otherwise count a close, re-arm the line and
    log an end every frame); `world` only for a seat taken on the world (`SeatScene == World`: a field seat's wldMapNo
    is stale, and WorldLaneStep runs before WorldOutTick, so a walk-out would book `world` instead of `out`); both
    `leave` sites set LeaveIntent and all three `scene` sites set TalkHere (TriggerFires ORs each cause's signals: the
    same verdict). `fireclose` goes through CloseRequestRule, so `close old` holds it too, and it bypasses the
    menu-family guard. One log line per close, at its END: cause, from-state, ms and how it ended (`last_close.end`:
    done, nothing, watchdog, scene, clear_point, fault).

    **THE RAMP'S SETTLE.** The close request at the ramp's arm stays; the fire then waits on the ramp's existing settle
    structure, with no clock of its own. The field branch already settles only on FieldHUD (NetSyncClient.cs:2007-2009),
    so it waits for the close by itself. The world branch's `settled` (:2004) settles a free-roam world at once, menu open
    and control on, so it gains the same UI term while seated: `&& !(seated && ui.State != UIState.WorldHUD)`. Both
    branches also gain the press term "no press deadline in the future" (the GuestOpen press's deadline: press +
    CloseCapMs + the live scaled FadeDuration, decision 9; the ramp never fires inside the press-to-door fade).
    `safeToLoad`, `_exitRampSafeSince` and the settle clock (:2013-2016) stay untouched, so the outer bound is the ramp's
    existing fail-safe, `ExitRampSettleMaxMs` (:1088, 10 s): past it the ramp fires through the fire backstop's restore
    before ExitMirrorToOwnSave (:2048), save-safe and alarmed (quiet only when the quit prompt held the close, decision
    16). The cost: a world close
    that stalls past the watchdog fires the ramp at 10 s instead of about 1.8 s. The close's service tick must sit before
    the enabled gate (decision 21); otherwise co-op turned off while seated would always run into the 10 s fail-safe. The
    restore door runs before the HUD's Show, so `seated` is false whenever the state reads WorldHUD after a close, and
    GM0-RAMP-WORLD can tell the door's restore from the backstop's. As built both terms are the pure `RampSettleRule`,
    run on both branches inside the settle's try; the press term reads `PressHoldsNow` (the deadline GuestOpen stamps);
    on the field branch the seat term never fires (that branch already requires FieldHUD), so only the press term
    changes it.

19. **The battle cut reads BOOTING.** While a close is in flight for the host's battle nonce, `GuestBootState`'s `uiFree`
    input reads free (NoteBootWatch, NetSyncClient.cs:4537-4552), so the report says BOOTING
    (NetSyncBattle.cs:5487-5505) and the host's start hold arms (StartHoldStep, :5886; `LateArmMs` 1000, :247). **Except
    while the quit prompt holds the close** (`QuitScene.isShowQuitUI`, decision 21 step 1): the report stays BUSY, never
    BOOTING, so the host's gauges are never held for the guest's own prompt. A durable decline, an opt-out and the skip
    nonce keep their own reports. As built this is the pure `CutUiFreeRule`; a cut merged into a close already in flight
    for another cause also reads BOOTING (the menu is closing either way). **Lever:** `close old` (the report reads
    BUSY: the host's HoldNotArmed, measured).

20. **A link outage keeps the view.** A stall or the grace does not close the menu: it stays open as a view (from rung 1,
    confirms are refused while the link is not live) and closes when the ramp arms. Relay stalls of ~2.3 s are routine,
    the grace runs to 40 s, and nothing is lost either way. Opening still needs a live peer (decision 8, term 4).
    **Lever:** none; GM0-STALL-VIEW's mutant closes on peer death.

21. **THE CLOSE ORDER LAW.** One close, in this order (the close lane's law with the critic's quit-confirm rule). A close
    is requested only while seated (decision 16), so it normally starts in the menu family (a seat kept by a restore
    fault on a HUD state is the exception, step 4).
    1. **The quit confirm first.** While `QuitScene.isShowQuitUI`, the close waits and the watchdog's clock is paused, as
       stock's own gates wait on that modal: the Alt+F2/F5/F9 handlers buzz while it is shown (UIKeyTrigger.cs:497-498,
       :559-560), and the soft reset returns while its button group is active (:345). `QuitUI.Show` records the enables
       and `Hide` writes them back (QuitUI.cs:24-48, :63-75), so a close under it would let a later cancel put events-off
       and control-off back on a live FieldHUD. QuitUI is the guest's own prompt and ends itself: Yes runs ConfirmQuit (no
       save is written while seated); No or Cancel returns to the seated menu (QuitUI.cs:130-150), and the close then runs.
       Nothing in the close or its watchdog hides the prompt. The one `QuitScene.Hide()` is on the load path: at the exit
       ramp's fire, when `QuitScene.isShowQuitUI` while a seat is held, it runs BEFORE the fire backstop and
       ExitMirrorToOwnSave, writing back the menu-time enables, which the load's HUD Show then supersedes; it shares the
       fire's own try with that backstop, which then restores quietly (decision 16).
       Without it the Autoload lands under the prompt (OnLevelWasLoaded never sweeps QuitScene, UIManager.cs:234-264) and
       the guest's later Cancel writes events-off, menu-off and control-off onto the loaded field: a hard strand, new with
       the menu (in s167 the same load under a prompt on FieldHUD writes back HUD-time enables, which are on). The costs: a
       guest who leaves the prompt up holds the close (for *The host leaves the field*, the close lands when the guest
       answers, not at about 1.5 s; the close is still requested at once, and stock lets that modal own input); the battle
       cut's report stays BUSY meanwhile (decision 19); the ramp's fire waits on a held prompt up to ExitRampSettleMaxMs
       (decision 18); after that fire the seated screen gets its input back while the Autoload and the Replace fade run,
       over the guest's own objects, with the census off (the session ended at the backstop) and every row enabled, until
       the Autoload's scene load sweeps it.
    2. **Wait while `UIManager.IsLoading`:** HonoFading never calls back on a busy fader, so a Hide there strands.
    3. **Memoria's control panel:** if `MainMenuUI.UIControlPanel` is shown, set `Show = false` while its Scene is still
       set, so `onHide` reactivates the scene (`Memoria/Scenes/MenuHUD/MenuUIControlPanel.cs:49-59`); never `ExitMenu`
       first (it nulls the Scene, :62-68, and the scene stays inactive: a strand).
    4. **One Hide of the current scene, ending in stock's own fade.** Only a menu-family scene (`IsUIStateMenu`) is ever
       hidden; in any other state (a seat flag kept by a restore fault, decision 16) the close ends without touching a
       scene. The two stock close forms:
       - **At MainMenu depth** (the root and the character pick): stock's root-Cancel statements.
         `NeedTweenAndHideSubMenu = true` is set BEFORE the Hide, as stock does (MainMenuUI.cs:336; the setter sets both
         flags, :29-36), so the Hide's own after-hide runs `FF9Wipe_FadeInEx(12)` and turns SubMenuPanel off (:78-87). In
         the callback: EnabledSubMenus put back, the held-bit write (below), then `ChangeUIState(FieldHUD or WorldHUD by
         UnityScene)`, where the door restores before the HUD's Show.
       - **Below MainMenu:** ItemUI.WaitForFade's form (ItemUI.cs:979-994): `SceneDirector.FF9Wipe_FadeInEx(12)`, then the
         screen's Hide; in its callback SubMenuPanel off, `UIControlPanel?.ExitMenu`, EnabledSubMenus put back,
         `UIManager.Input.ResetKeyCode`, the held-bit write, `ChangeUIState(HUD)`, then `NeedTweenAndHideSubMenu = true`
         (priming the next open, as WaitForFade does).

       `FF9Wipe_FadeInEx` is `FadeEventSetColor(Sub, white)` then `InitFade(Sub, frame, black)` (SceneDirector.cs:687-691).
       The follow that fires next then starts exactly like a follow from a guest standing on the HUD: s164's Begin reads
       the slot and joins a black one, hurries a heading one, or fades a visible one from where it is, with no flash
       (NetSyncFollowFade.cs:113-124, :207-222, :324); ReassertRule fades once more if a fade-in turns the slot visible
       mid-fade (:267-270, :405-411). Where a screen's Show leaves a sub-panel standing (GM0-REOPEN finds which), the close
       resets it itself; replayed input is not the mechanism. **The visible cost:** on a follow close the field being left
       brightens before Begin fades it out again. At MainMenu depth the follow starts within a tick or two of the fade-in,
       so it barely shows. Below MainMenu, FadeInEx starts BEFORE the sub-screen's Hide fade (FadeDuration), so at
       FadeDuration 300 the field is about 3/4 visible before Begin fades it out over 12 ticks: a visible
       brighten-then-darken. The follow also commits about 12 game ticks later than a join (~400 ms at 30 Hz, less on
       fast-forward), which eats into `PinMaxAgeMs` 2500's margin; GM0-TIMING measures it.
    5. **Done** when the field's OnShownAction ran SetEventEnable(true) (FieldHUD.cs:394-396), or WorldHUD.Show did (:67).
       The session already ended at the door; the close's own record ends here.

    - **WHERE THE CLOSE RUNS:** the close's per-Update service -- the step machine (the quit and Loading waits, the depth
      steps) and the watchdog -- runs in ONE tick placed AFTER ServiceFollowWarp() and ServiceWorldOut() and before
      NetSyncClient.Update's `if (!_enabled) return;` (NetSyncClient.cs:2054-2055), with no role test, so an in-flight
      follow always commits first (the s42 never-abandon law). The sites in decision 18 only REQUEST the close; this tick
      advances it. So co-op turned off, or the Role changed to host, while seated still closes the menu, lets the ramp
      fire and frees input. **That region has no enclosing try**, so the tick carries its own, as TitleTick's caller does:
      a fault logs one line per process, bumps `closes.faults` and ends the close in a second guarded step -- in the menu
      family, the held-bit write, the sweep, then `ChangeUIState(HUD)`; on a HUD state with events still off, the held-bit
      write and that HUD's own Show -- then ends the close record only; a seat kept by a restore fault stays held with its
      record, and the next backstop or door retries it (decision 16). An escaped throw
      there would abort the whole enabled section of Update every frame. The selftest-only `guestmenu close fault <step>`
      injects it (GM0-DEPTH's fault leg).
    - **THE WATCHDOG:** a close that has not reached step 5 by its deadline acts by the state it finds, with one line.
      The deadline is stamped at the request: CloseCapMs (seed 1500 ms) plus two of the live FadeDuration on a field (the
      screen's Hide fade, then the HUD's Show fade before OnShownAction) or one on the world, each scaled as UIScene
      scales it (divided by FastForwardFactor under IsFastForward, UIScene.cs:54, :81); its clock is paused while the quit
      prompt holds the close and while step 2 waits on Loading. So a healthy close never trips it, at any FadeDuration
      (clamped 0-5 s). At FadeDuration 300 a field close's deadline is 2100 ms, under the pin's 2500 ms; above about 1 s
      of FadeDuration a follow close ages the pin past `PinMaxAgeMs` anyway (a Known limit). In the menu family
      with `UIManager.UnityScene` still the request's: the held-bit write, the stock scene-load sweep (the deactivation list
      of UIManager.cs:234-264, without a load), then `ChangeUIState(HUD)`. On FieldHUD/WorldHUD with step 5 not reached
      (the close's ChangeUIState ran, but its HUD's Show never turned events back on): the held-bit write and that HUD's own
      Show (`GetSceneFromState(state).Show(null)`, as the door's refusal does), never the sweep, which would deactivate the
      HUD scene itself and leave events off. Any other state: the close ends. A scene load or the title ends the close
      first (decision 16), so the watchdog never sweeps over a new scene.
    - **THE HELD-BIT WRITE:** a button held through the close must never land on the guest's copy as a fresh press. The
      fix sits at the script's key edge: immediately before EVERY route that ends a seat at the HUD (the close's
      `ChangeUIState(HUD)`, the watchdog's sweep and its HUD Show, the tick's fault step), for Confirm, Cancel, Special and
      Menu, `if (HonoInputManager.Instance.IsInput(c)) ETb.sKey |= EventInput.GetKeyMaskFromControl(c)`
      (HonoInputManager.cs:904; `Global/Event/EventInput.cs:476`). `ETb.ProcessKeyEvents` sets `sKeyOn = inputs & ~sKey`,
      then `sKey = inputs` (`Global/ETb/ETb.cs:50-56`); its one caller is ServiceEvents (EventEngine.cs:119), which the
      field skips while attr & 256 or attr & 2 (`Global/Honolulu/HonoluluFieldMain.cs:236-240`) and the world while attr &
      2 (`Global/ff9/ff9.cs:3697`), so the written bit stands until the first frame with events back. A button held
      through the close then reads as held, never as a KeyOn; a real re-press is a real edge; a button not held is
      untouched, so no false KeyOff. The field's and the world's interaction read ETb.KeyOn (EventCollision.cs:63, :109;
      EIcon.cs:360). `sKey` is externally edited state already: UIKeyTrigger.cs:1014 and VoicePlayer.cs:266 CLEAR Confirm
      from it, the opposite purpose (to inject a fresh edge). The UI side needs no rule: the HUD's GetKeyTrigger reads
      IsInputDown edges (UIKeyTrigger.cs:108-125), a Hide sets Loading (UIScene.cs:83) and OnKeyConfirm/OnKeyCancel return
      while it is set (:108-111, :122-125), and the census refuses every write, so navigation during the close is
      harmless. The costs: a press (not a hold) in the close's own frame can still reach the menu before its Hide
      (navigation only); an `.eb` that reads a held button's LEVEL (B_KEY, not B_KEYON) still sees it after the close; a
      button still held when a following load lands is a KeyOn on the new field, because `EventEngine.Initialize`'s
      InitKeyEvents zeroes sKey (EventEngine.Initialize.cs:34-36), as stock does on any load; a button released and
      pressed again inside the HUD's show fade, and still held at the first tick back, reads as held, so that re-press is
      lost. GM0-HELDKEY judges it (the `held` keys, decision 32).
    - **THE TIMING BUDGET:** to the HUD state within one FadeDuration plus the Loading wait; events back one FadeDuration
      later (the watchdog's deadline carries both fades). At the default 40 ms: the HUD within 150 ms of the request;
      the follow start within 200 ms of that (the follow fades a visible slot, about 12 ticks later than a join, step
      4); the landing with the pin under `PinMaxAgeMs` 2500 (NetSyncSwap.cs:142); for a battle, BOOTING before the
      host's opening plus `LateArmMs`. A full replayed-Cancel unwind at FadeDuration 300 could miss LateArmMs, so the
      direct close is the contract.
    - **One line and harness keys per close:** cause, from-state, ms.
    - **As built (W1c, W1h).** The step machine is `GmCloseTick` + `CloseDriveRule`, with `RequestCloseOver` (one close at
      a time, idempotent; a cut's nonce merges into a close already in flight). The quit wait applies at every step; the
      Loading wait (step 2) only before the close has issued its own Hide -- after it, Loading is the close's own fade and
      the watchdog clock runs, otherwise the fades in the deadline would never count. A new UnityScene ends the close
      first. Fade times come from `FadeMsRule`: rounded to the nearest ms (UIScene works in Single seconds), a
      FastForwardFactor <= 0 read as unscaled. The watchdog's and the fault end's sweep covers OnLevelWasLoaded's
      menu-family scenes (MainMenu, Item, Ability, Equip, Status, Card, Config, SaveLoad, Cloud, Shop, NameSetting,
      PartySetting, Tutorial, QuadMist, Chocograph, Folklore, Journal), turns SubMenuPanel off, calls DisableAllGroup,
      clears HelpEnabled and exits the control panel first; it never touches the HUD scenes, BattleResult, GameOver,
      Title, Ending, EndGame, or Dialogs.CloseAll (the field's own windows). The sub form copies step 4's listed
      statements, so it omits WaitForFade's depth pair (the ScreenFade panel at 100, then 10) and plays no FF9Sfx 101;
      GM0-FADE and GM0-DEPTH judge the look. The tick's guarded fault end touches nothing while the quit prompt is up and
      only ends the close record (step 1's law), so a cut close that faults under the prompt leaves the menu open until
      the guest's own Cancel (the cut's nonce memory never re-asks). The held-bit write is `HeldBitsRule`, its harness
      watch `HeldWatchStep`; the keys add `close_step` and `last_close.end`.

    **Lever:** `guestmenu close old|act` (decision 18).

### s169 (rung 1): support abilities

22. **Where the host applies, and what s169 adds.** The host applies a support-ability change anywhere on the field or
    the world map, and refuses in battle, on the result screen and with no live party. No stock `.eb` reads saExtended
    (the only read is Memoria's own `PLAYER_SUPPORT_ENABLED`, `Global/EBin.cs:441-446`), and battle reads the set by
    reference (`btl.saExtended = p.saExtended`, `Global/btl_init.cs:393-394`). s169 adds section 13 and frame type 8;
    s168 reserves both in the registry only. **Lever:** `guestmenu apply off` (decision 31).

23. **The guest-to-host ring: type 8, kind 1 SA_SET.** A latest slot carrying a ring, the section-7 pattern: re-sent on
    every write tick, so a frame lost in a relay or bridge redial heals on the next tick. Never type 2 (drained only in
    the host's own battle and refused there, NetSyncBattle.cs:2048-2063) and never type 3 (battle-owned).
    `[fmt u8=1][epoch u16][n u8 <= 4] x [seq u16][kind u8][len u16][body]`, oldest first; kind 1's body is
    `[charId u8][nBefore u8][saId i32 x nBefore, ascending][nAfter u8][saId i32 x nAfter, ascending]`: absolute target
    sets keyed by CharacterId, never a slot index. **'before' is the set AS RECEIVED** in section 1 for that character
    (the v9 SA list, NetSyncParty.cs:147-161), never the guest's derived copy (CalculateGemsPlayer can drop SAs there).
    The slot is non-null only while the guest holds an unanswered entry, and is sent only under FeatureOn(b3) and section
    12's applyMask b0. The epoch is drawn at each transport start with `NewEpoch(avoid, avoid2)` (NetSyncClient.cs:11533).
    `NetSyncFrames` gains the type-8 slot pair, with Set/Get on both transports and `INetTransport`; the host drains it
    only in its menu code. A full ring of four refuses the next confirm locally with the buzz (the decisions were silent on
    the size and the lanes split between four and eight; the wire lane's four is taken because every entry rides every
    tick and four covers a boost-chain walk).
    **Lever:** `guestmenu apply off` on the host clears applyMask b0, so the guest sends nothing; an entry already in
    flight is answered LEVER (decision 26's gate 1).

24. **Section 13, the answers.** Host to guest, beside 12 in the order law. `[fmt u8=1][guestEpoch u16][through u16 =
    the highest seq processed][n u8 <= 8] x [seq u16][kind u8][charId u8][result u8]`, newest last, sent while FeatureOn
    and the guest's type 8 is non-null or an answer is under ~5 s old. Results (the names are the abilities lane's):

    | Code | Result | Code | Result |
    |---|---|---|---|
    | 0 | APPLIED | 8 | NOT_ALLOWED (forced, hidden or banished) |
    | 1 | ALREADY (current == after: no write) | 9 | NOT_LEARNED |
    | 2 | STALE | 10 | STONES |
    | 3 | BATTLE | 11 | SHAPE |
    | 4 | BUSY | 12 | ENGINE (a tripwire fired) |
    | 5 | LOCKED | 13 | OLDER (a kind this host build does not implement) |
    | 6 | NOT_IN_PARTY | 14 | MALFORMED |
    | 7 | UNKNOWN (an id this install lacks) | 15 | LEVER (the kind's applyMask bit cleared by this host's `apply off`) |

    The guest resolves every pending entry with seq <= through; a seq missing from the list reads as processed with an
    unknown result (re-seat, no buzz).

25. **The guest's press bracket, the member data check, the pending hold.**
    - **The bracket** wraps BOTH support branches, OnKeyConfirm (AbilityUI.cs:407-501) and OnKeySpecial (:616-719). It
      replaces A1/A2 and keeps their law (decision 17): HEAD and TAIL run only while the seat flag is set, keyed on the
      seat alone, and with no seat both branches are byte-for-byte stock (vanilla, solo, the host, a guest in its own
      menu after the session). HEAD,
      right after abilityType (:416, :625) and before ImpactfulActionCount++: refuse (102, the line, nothing written) if
      the seat's link is not live, the member is view-only, applyMask b0 is clear, or the ring is full. TAIL, after the
      branch's DisplaySA: compare before and after; equal (the stock buzz paths) sends nothing; changed queues one entry.
      The stock code computes the set: neither machine re-implements the boost loop. GM1-PROOF rows: no seat with a
      vanilla toggle gives the stock result (saExtended changed, ImpactfulActionCount +1) with zero entries queued and
      nothing sent; a host-role toggle queues nothing.
    - **THE MEMBER DATA CHECK:** a member is editable only if the seated copy's saExtended after the seat's FF9Play_Update
      equals the wire set exactly (otherwise the two installs disagree on gems, forced or banished abilities, and every CAS
      would read STALE forever). Otherwise that member is view-only, with one line naming them.
    - **THE PENDING HOLD:** while C has an unanswered entry, C keeps the guest's toggled view. Only these re-seat C (s168
      seats once per open, decision 15, so no other host frame re-seats C): the answer, from THAT frame's section 1; the
      hold's expiry or the session grace, from the latest frame (below); a host epoch change seen in section 7 (decision
      28), from the frame carrying the new epoch. Each re-seat keeps the open's guards: decision 13's witness over C and
      decision 12's all-or-nothing order, with one difference: a re-seat never writes the open's restore record (first
      write wins, as RememberOriginalPlayer does, NetSyncDiorama.cs:2878-2881), so the restore still puts back the guest's
      own objects. Before the build it takes its own rollback snapshot of C's current scratch reference, and of C's
      `party.member` slot if the reference changes; on a witness or build failure it reinstalls that snapshot, so C keeps
      its current copy and turns view-only, with its line. A refusal plays 102 and the line;
      later entries for C are CAS-chained and dropped with the first. The hold has a 3 s cap: on its expiry, or the
      session grace, the pending entries drop, C re-seats from the latest frame, and the line says "Your change didn't
      reach your partner's game."

26. **The host gates, cheapest first, one verdict each** (`Memoria/Data/ff9abil.cs` for the helpers):
    1. caps and applyMask b0 -> LEVER when b0 is clear because of this host's own `apply off`; OLDER only for a host
       build without the kind;
    2. a live party and `ee.gMode` 1 or 3 -> BATTLE if gMode 2 or 4, BUSY otherwise (title, game over, endings);
    3. the UI state not BattleHUD, BattleResult or GameOver -> BATTLE or BUSY;
    4. `LockEquippedAbilities` not 1 or 3 (a per-machine ini value; the host's decides,
       `Memoria/Configuration/Structure/BattleSection.cs:74`) -> LOCKED;
    5. exactly one party.member with `Index == C` (scanned only after gate 2, never in battle) -> NOT_IN_PARTY;
    6. every id in before and after has a `_FF9Abil_SaData` and a `_FF9Abil_SaFeature` entry -> UNKNOWN;
    7. THE ONE-ANSWER LAW: a seq this epoch already answered republishes its first verdict. In code this is the intake,
       ahead of gates 1-6: only `seq == through + 1` is evaluated, a repeat is answered from the ledger;
    8. CAS: current saExtended == before; else current == after -> ALREADY (no write); else STALE;
    9. no change to a member of saForced -> NOT_ALLOWED;
    10. no added id in saHidden or saBanish -> NOT_ALLOWED;
    11. each added id has `FF9Abil_GetIndex >= 0` (:183) and is learned (`pa[k] >= PaData[preset][k].Ap`, or the preset
        has no AP) or taught by an equipped item -> NOT_LEARNED (the stock rule, `AbilityUI.CheckSAType`,
        AbilityUI.cs:1271-1308; not the study's "pa at or above its cost" alone);
    12. the sum of `GetSAGemCostFromPlayer` (:308) over after <= the current `max.capa` -> STONES;
    13. the non-forced difference lies inside ONE hierarchy (`GetHierarchyFromAnySA`, :226) and every non-forced member of
        after has its predecessor on -> SHAPE.

    Gates 9-13 test the host's live derived sets, never the guest's. **Lever:** `guestmenu check off
    learned|capacity|party|known|allowed|shape` (host; one gate disabled, for the INV mutants; `allowed` is gates 9-10,
    forced, hidden and banished; `shape` is gate 13).

27. **The apply, the tripwires, the one-character write.**
    - **THE APPLY:** for each non-forced id in before\after, `FF9Abil_SetEnableSA(p, id, false)` (:118); for each in
      after\before, `FF9Abil_SetEnableSA(p, id, true)`; then `FF9Play_Update(p)` ONCE (ff9play.cs:274). These are
      AbilityUI's own primitives. Never `FF9FEqp_UpdatePlayer` (its sweep drops unrelated abilities), `FF9Play_Build`,
      `PLAYER.ValidateSupportAbility` or `ValidateBasisStatus`; no manual cur.capa arithmetic; never touch
      ImpactfulActionCount, the bag, gil or the party order. The helper takes its target PLAYER as an argument and never
      reads `FF9StateSystem.Common.FF9` for it, so the selftest loopback can apply to a bench host's copy.
    - **THE TRIPWIRES**, after the Update: TW1 `set(p.saExtended) == after` (catches a CalculateGemsPlayer drop, a
      re-forced or re-banished id, a MaxGems surprise); TW2 `p.cur.capa == p.max.capa - p.GetActiveSupportAbilityPoint()`
      (THE LOAD-WIPE EQUATION: `ValidateSupportAbility` clears the whole set at the host's next load when it fails,
      `Global/PLAYER.cs:48-59`, called at JsonParser.cs:1301). On a trip: reverse the membership writes, run
      FF9Play_Update, restore the pre-apply cur.hp, cur.mp, status and permanent_status (clamped), log an error, answer
      ENGINE. The pre-checks make a trip a bug signal, never a routine path.
    - **THE ONE-CHARACTER WRITE:** an SA intent changes only C's PLAYER (saExtended, sa[], and what FF9Play_Update
      derives). The bench snapshots the other members, the bag, the key items and gil around every apply.

28. **The answer-echo law and exactly-once.**
    - **THE ANSWER-ECHO LAW:** the host drains type 8 in its Update BEFORE that Update's BuildStateFrame, then runs
      PushStateNow (NetSyncClient.cs:10899) after any decision. The answer (section 13) and the post-apply party (sections
      1 and 12) leave in ONE frame: a frame that answers seq N always shows C's post-apply set.
    - **EXACTLY-ONCE:** at-least-once delivery (the latest slot re-sends every tick until the answer covers the entry),
      plus the one-answer law (the host evaluates `seq == through + 1` for the current guest epoch, in order, once, and
      republishes the first verdict for any repeat; `through` resets when the guest's epoch changes), plus the CAS (a late
      duplicate after a host restart reads ALREADY). A host epoch change seen in section 7 voids the guest's pending
      entries, which re-seat as stale (from the frame carrying the new epoch, decision 25).
    - **THE CLOSE CARRIES THE QUEUE:** a forced close never cancels queued or pending entries; they are still sent and
      answered, so *Architecture*'s "a forced close loses nothing" holds. An answer after the close is a line only (no
      seat is left to snap back).

29. **The host's line and the redraw hook (*Host notification*).** A new timed overlay state 30, armed per applied
    change, live for 4 s (a seed, as EntryLineMs is); a newer change replaces it; it ends at scene changes. It is chosen
    in place of OvlOff in the paired branch and ahead of OvlOff off-field and on the world, and never outranks the
    wire-mismatch, reconnecting or lost-contact lines. It names the ability when exactly one changed
    (`FF9TextTool.SupportAbilityName`, `Assets/Sources/Scripts/UI/Common/FF9TextTool.cs:506`). Plus a log line
    `[NetSync] guest menu: applied support abilities for <name> (+X -Y) seq N`. **THE REDRAW HOOK, both roles:** one
    internal AbilityUI method that, when the screen is active on the support list for `party.member[currentPartyIndex]`
    == C and not Loading, runs `InitialData` (AbilityUI.cs:1421), `DisplaySA` (:1085) and `DisplayCharacter(false)`
    (:915). The host calls it after an applied change; the guest after a re-seat or a snap-back. Equip and Status
    refresh at their next draw. **Lever:** none for the line; the redraw has the GM1-REDRAW mutant.

30. **The rung-1 guest words** are listed under "The owner-visible words". APPLIED and ALREADY are silent on the guest.
    Each refusal also logs `[NetSync] guest menu: support abilities for <name> refused (<gate>) seq N` on both roles.

### The harness

31. **The lever set: a new sub-verb `netsync guestmenu`,** appended last in the unknown-sub-verb literal
    (`Memoria/Harness/HarnessAgent.cs:2505`; `worldwalk` refuses unknown ops and an unknown `bench` op switches the
    field-gate bench ON, so each round adds a new sub-verb). Every lever is released with the harness: a
    `HarnessReleaseGuestMenu` appended after HarnessReleaseWorldWalk in `NetSyncBattle.HarnessReleaseBench`'s chain,
    which runs on disarm, fault and reset. It does everything `clear` does -- restores every bench source seam
    (as built: `NetSyncParty.SlotSource` and the two new NetSyncParty seams `BagSource` and `KeyItemSource`, each put back
    to its live source; rare_item_used and gil were never seams, see `frame` below), nulls `_gmBenchFrame` (its base,
    marker, witness, intent and tick too), drops the bench host trailer `frame` armed (or puts the bench place and world
    back) and sets the bench host field to -1 -- then returns every lever (`old|act`, caps, capture, close, chip, events,
    poke, seat skip, restore skip, seat fault, door fault, close fault: twelve in s168; from s169 also `apply`, back to
    on, and `check`, every gate back on) to its default (GM0-RELEASE), logging `[NetSync] harness: guestmenu levers
    released (with the harness)` once, only when something was set. Any role (THE DUO CANNOT PULL A SELFTEST-ROLE LEVER;
    co-op on, except `clear`): `old|act`;
    `caps off|on`; `capture off|on`; `close old|act` (every close trigger at once, decision 18); `clear`; from s169
    `apply off|on` (host) and `check off <gate>` (host).
    Selftest role with bench gates only (otherwise refused: "netsync guestmenu: needs the selftest role with the bench on
    (netsync selftest 1, netsync bench 1)"):
    - `frame <marker 1-9999>` builds a two-marker host frame BEFORE any seat (refused while seated): sections 1, 2, 3 and
      12 through the real encoders, with a bench source substituted for every seated component and restored in a finally
      (the `NetSyncParty.SlotSource` seam, NetSyncParty.cs:82, for the party; as built the new `BagSource` and
      `KeyItemSource` seams for the bag and the key-item set, while gil and rare_item_used are passed as arguments to
      `HostMenuBlockOf`, the seam W1d built for exactly this, so they need none). The bytes are joined with
      `NetSyncState.AppendSection` directly, never through the role-gated send rule (it needs the host role). The marker
      sets gil and one bag item to values the guest does not hold; slot 0 is an impostor named "BENCH<marker>" at level
      99 and every member's exp is a marker; GM0-SEAT's gil and exp markers come from it. The frame is read back through
      the door's own readers into the dedicated `_gmBenchFrame` slot (decision 8's bench inputs), and `frame` also arms a
      bench host trailer (my caps word, place 1 on a field or 4 on the world, my world; decision 8: directly, past
      `worldwalk host path`'s refusals) and a bench host field equal to my field, all released with the harness. The
      Menu key then opens through the verdict.
    - `frame witness preset|pa|equip|sa|char|bag|keyitem` (GM0-WITNESS's variants, each built before the seat like every
      bench frame); `frame intent <field 1-65535>` (term F2: a section 4 with a fresh nonce and dest != my field written
      into `_gmBenchFrame`); `seat fault players|party|bag|gil|keyitems|off` (GM0-SEATFAULT; one shot); `door fault
      open|restore|off` (decision 9's door fault path, GM0-DOOR; one shot); `close fault
      quit|loading|panel|root|sub|hide|show|off` (throws inside the close's service tick at that step, decision 21,
      GM0-DEPTH's fault leg; one shot); `host elsewhere|here` (term F1). A one-shot lever is spent by the next seat,
      door half or close step, so a fault leg never loops. Term 6 reuses the existing `netsync lock 1` and
      `netsync host battle 1` (decision 8).
    - The in-game mutants: `chip off|on` (seated with no chip), `seat skip party|off` (the guest's own values drawn),
      `events on|off` (the seat calls SetEventEnable(true) once, right after a complete seat: nothing turns events off
      again while seated), `poke` / `poke off` (one shot: the next seat flips gEventGlobal[2047] bit 0 after fp_before's
      outside stamp, so the restore's `fp.outside_equal` reads false and names `events`, GM0-WORLDTAG4's S leg; byte 2047
      sits above the co-op window 2032-2041 and every kit band in flags.py, and it is not restored: the S leg must stay
      red and the bench reloads its sandbox), `restore skip <component>|off`. `seat skip` and `restore skip` persist
      until `off`, `clear` or the release.
    - `fireclose leave|out|rejoin|world|cut|ending|title|scene` (the close ACTION without its trigger; the selftest role
      runs no DioramaTick; it goes through CloseRequestRule, so with no seat it does nothing, decision 16, and `close old`
      holds it; its ack names which: requested, already in flight, no seat, close old); from s169 `intent <hex>`
      (loopback through the real decoder), `intent duplicate` and `intent drop` (GM1-ONCE).
    - **Refusals** (HarnessAgent throws `InvalidOperationException(why)`): an unknown op or a bad arity answers the usage
      line "netsync guestmenu: expected old|act, caps off|on, capture off|on, close old|act or clear (any role), or chip
      off|on, frame <marker>|witness <component>|intent <field>, host elsewhere|here, seat skip party|off, seat fault
      <component>|off, restore skip <component>|off, door fault open|restore|off, close fault <step>|off, fireclose <id>,
      events on|off, poke [off] (the selftest bench)"; co-op off: "netsync guestmenu: co-op is off -- no role to act
      on"; a fault: "netsync guestmenu: the lever faulted (<msg>)". Each lever lives in three places: its op in
      `HarnessLever`, its reset in `ReleaseGuestMenuLevers` plus its term in `HarnessReleaseGuestMenu`'s `any`, and its
      field in the `lever` key with its catch-literal sentinel.

32. **The keys.** A new `netsync.guestmenu` (additive, protocol 5), netsync's LAST key. As built (W1i, extended by each
    piece and the W1 review), in this order:
    - `lever` {menu, caps, chip, seat_skip, restore_skip, seat_fault, door_fault, capture, close, close_fault, events,
      poke}: every lever's current setting, one field per lever (GM0-RELEASE). Live values: menu act|old; caps, chip,
      capture on|off; seat_skip party|off; restore_skip and seat_fault <component>|off; door_fault open|restore|off;
      close act|old; close_fault <step>|off; events on|off; poke armed|off.
    - `caps` {own, peer, on}.
    - `why`: the LAST refusal's why, from the closed set of 19 (stamped through `NoteRefusal`; not a live predicate read).
    - `open`: `UIManager.IsUIStateMenu(State)` now, seated or not, the one read that tells a guest's own menu (GM0-HOLE's
      OLD: `open` true, `seated` false) from a seated one.
    - `session`: decision 6's guestSession, read live.
    - `seated`: the seat record held (the session, decision 16).
    - `opens`.
    - `closes` {leave, out, rejoin, world, cut, ending, title, scene, faults}: per trigger, keyed by decision 18's Id
      column (the close words are the drawn text only, never a key); `faults` counts the close's service tick and the
      close request's own try (decisions 18 and 21).
    - `refused` {count, last_site, last_screen}; `captures` (the confirms the census caught); `passes` (the confirms
      `capture off` let through into the seated copy).
    - `fp` {before, after, equal, named, components, outside_equal, outside_named} (decision 33; `outside_*` is the
      outside fold, decision 17).
    - `seat_fp` {value, components}: over the installed, seated copy, stamped at the seat (from s169 also at C's
      re-seat); readable while seated.
    - `frame` {type5_len, type5_max, tx_bps, sec12_len, dropped, faults}: decision 5's book, stamped at every build;
      `tx_bps` is computed only at the harness read (production pays nothing): the last built payload length times the
      state slot's StateProbe.Sends delta per second, over windows of at least 1000 ms between reads, in payload bytes
      (the 5-byte frame header not counted), -1 with no transport.
    - `host_fp` {value, components}: on the host role with b3, over the same component set as `seat_fp`, stamped only
      while HarnessAgent.Active, inside HostGuestMenuSectionNow's try, at each BuildStateFrame that carries section 12.
    - `line` {text, age} (the refusal line's book while it lives, also on the selftest role, where state 29 is never
      drawn); `close_line` {text, age} (the forced-close line: two independently timed lines, decision 10); `chip` (the
      drawn words, or null).
    - `seat` {src, frame_age_ms, marker}: `frame_age_ms` reads -1 for a wire seat (the state slot exposes no arrival
      stamp) and is measured only for bench frames.
    - `door_refused` {lever, not_mirroring, session, older, link, host_busy, host_battle, no_data, data_differs, control,
      busy, leaving, scene, ui, host_elsewhere, world_busy, riding, move, fault}: one counter per why.
    - `restore` {doors, drops, backstops {replace, ramp, ramp_quit, load, scene}}: `scene` counts the restores found at
      OnLevelWasLoaded, the title tick or a UnityScene change (decision 16).
    - `master_skipped`; `ach_held` (the seat's own, distinct from battle.end.ach_held); `event_enable`
      (UIManager.IsEventEnable).
    - `bench` {marker, witness, intent, host_field}: the bench frame's marker and variant, its intent and the bench host
      field.
    - `impactful` (MainMenuScene.ImpactfulActionCount).
    - `close_pending` (a forced close's record, up to its step 5 or watchdog) and `close_step`.
    - `last_close` {cause (decision 18's ids), from, ms, end (done, nothing, watchdog, scene, clear_point, fault)}.
    - `held` {bits (the last held-bit write's mask), keyon (KeyOn edges ETb has read, after that write, of a Confirm,
      Cancel, Special or Menu button held continuously since it; harness-only, stamped by the close's service tick while
      HarnessAgent.Active)}.
    - `outside_settled` {set, equal, named}, `uid0_vars` and `sysvar192` (the W1 review's CR-3, harness-only, for
      GM0-WORLDTAG4). The settle is armed by StampFpAfter only while HarnessAgent.Active; its tick
      (`GuestMenuSettleTick`, own try, disarmed by a fault) sits in the pre-gate region after ServiceWorldOut and before
      the close tick, and restamps the outside fold at the first frame after the one that first read FieldHUD/WorldHUD
      with IsEventEnable true (the pure `SettleStepRule`), judged by decision 33's law against the seat's outside stamp;
      the next seat clears it. `uid0_vars` is `VarsDigestRule` over the world copy's UID-0 object's instance variables
      (`FindObjByUID(0).buffer[vofs*4, sofs*4)`), null off the world or with no object; `sysvar192` is GetSysvar(192) on
      the world, -1 off it.
    From s169 the key also gains host {intents_rx, applied, refused, last_why, last_char, line, line_age_ms,
    apply_count}. Every key's sentinel goes into AppendNetsync's catch literal (the catch at :4274, its
    sentinel literal at :4363; the method is at :4194) in the same change (THE CATCH LITERAL IS PART OF EVERY KEY
    ADDITION); as built the writer's static keys and the sentinel's are in the same order (a static check), and the
    `fp`, `seat_fp` and `host_fp` components are keyed players, party, bag, gil, keyitems.
    `netsync.menu_refusal` (:4258) keeps every key and meaning: `now` gains `guest` (GuestOpen and GuestQuiet), and a
    refused guest press reads `audible` -- the bench and an unmirrored guest on a HUD, where s167 read `open`, and with the
    guest menu off for the pair a press inside a HUD fade (decision 6); `count`, `lines` and `silent` also count
    guest-press refusals. Under `guestmenu old` every s121 read is byte-identical; against a peer without b3, every s121
    read of a mirroring guest is (an unmirrored guest stays refused, decision 7). The overlay's name for state 29 is
    `guest_menu` (`session.overlay`). Re-key, never weaken:
    coop_world_walk.py's PR-SAVEMENU and coop_field_swap_timing_duo.py's `MENU_PRE_OK` (:174) accept `guest` only when
    the probe shows `netsync.guestmenu`; `_coop_peer_bench.STAGE_KEYS` (:210) gains the s168 stage; S167-P0's
    `lane.caps.own` and the round-B duo's `CAPS_S167` are re-keyed by stage (0x0B on an s168 stage, 0x03 under
    `guestmenu caps off`) whenever round B's legs are rerun; coop_cut_hold.py's s121 leg stays as it is, the fallback
    row. Pause is untouched: s164's MENU legs stay green. The engine's s167 caps proof is bound to the one-argument rule
    and is re-keyed too, never weakened:
    - the `OwnCapsFn` delegate becomes two-argument (fpOff, menuOff);
    - `caps.own_s167_word` pins s167's word as `OwnCapsOf(false, true) == 0x03`;
    - `caps.fp_off_speaks_s166` pins `OwnCapsOf(true, *) == 0x01`;
    - `capswire.own_word_always_b0` and the mutants `own_caps_fp_always` and `own_caps_off_drops_b0` are rewritten over
      the two-argument delegate;
    - battlewire's twin becomes `ww_own_caps_rule(fp_off, menu_off)`, with test_coop_world_walk_b.py:273, :488 and :490
      re-keyed by stage (s167's '0003' = menu_off True), and fakegame.py:9872's call site follows;
    - the world-walk proof's tallies move: the kit gains an s168 tally constant beside `WORLD_WALK_PROOF_S167`, and
      test_coop_world_walk_b.py's fallback assertions are re-keyed by stage. As built it is (534, 198), from s167's
      (532, 196): the new rows `caps.own_s168_word` and `caps.line_text_s168`, and the mutants `own_caps_menu_never` and
      `own_caps_menu_lever_blind`.

33. **THE MENU FINGERPRINT, stamped by the engine.** The engine stamps `fp_before` at the seat and `fp_after` at the
    restore, as the result screen stamps `_netFpOpen` (`Global/battle/Result/BattleResultUI.Net.cs:414`). The hash covers,
    in-engine and read-only, every value the save's Common writer serializes for players, party, bag (in order), gil and
    key items (`ParseCommonDataToJson`, JsonParser.cs:765), and names its components; it does not call the writer
    (whether that call is side-effect-free is unverified). The verdict is `fp_after == fp_before`, never read while
    seated. `NetFingerprint` alone (:899) is not acceptable: it misses equipment, support abilities, capa, HP/MP,
    statuses, row and name. A separate seat fingerprint (`seat_fp`, decision 32, over the same component set as the
    host's `host_fp`) serves the capture rows. Mutants: `restore skip <component>`,
    once per component; each must go red and name its component.
    **As built (W1i, W1f, W1g).** Five components, the restore families, so `restore skip <component>` names itself:
    `players`, `party`, `bag`, `gil`, `keyitems`. The stamps are `StampFpBefore` (before anything is installed),
    `StampSeatFp` (after the install), `StampFpAfter` (after a clean element-wise restore; a drop or a restore fault
    stamps no after, so `equal` reads false, no verdict) and `StampHostFp`; the verdict needs both stamps and is never
    read while seated; a null state clears the stamp with one fault line per process. The hash uses FNV-1a-64's offset
    and prime with ONE step per value (MixU), not NetSyncEnd.FpMix's byte-wise fold: the byte-wise fold made the guest
    menu selftest cost 772 ms per run offline, the word-wise one 126 ms, and each step is a bijection, so one changed
    value always changes its component (`_netFpOpen` above is the stamping pattern, not the hash). Three
    departures from "what the Common writer writes", each to make the compares sound: `players` folds order-free (the
    loader re-keys them by slot_no, so the dictionary's order is not state); `party` adds an identity bit (is each
    member the dictionary's own entry?), so `restore skip party` with the same members is visible; `bag` skips count-0
    rows, as section 3 and NetFingerprint do, or `seat_fp` could never equal `host_fp`. `keyitems` folds each set in
    enumeration order, the order the Key Items screen draws, so a `seat_fp` / `host_fp` compare leans on K1's HashSet
    read. The outside fold (decision 17's five components) rides inside StampFpBefore and StampFpAfter, and the W1
    review's settle stamp (decision 32's `outside_settled`) re-judges it once the HUD has turned events back on.

34. **A new proof line in a new file.** `guest menu selftest: OK (N rows, M mutants caught)`, appended after the last
    proof line, from `NetSyncGuestMenu.cs` with its own row helper. `MenuRefusalSelfTest` stays at its pinned 14 rows
    and NetSyncField.cs's row count does not move. Rows: the key verdict, every predicate term, the door, the confirm
    classifier per site, the close rule (Pause excluded; one mutant per trigger, deleting that trigger's row, decision 18),
    the close order states, the restore identity rule (EnabledSubMenus put back on the drop path among its rows), the
    section-12 guard and its TrailReserve row (decision 5), the press-deadline row at FadeDuration > CloseCapMs (decision
    9), the two-marker seat round trip; from s169 the codec, each host gate, the one-answer ledger, the re-seat record
    row (decision 25). Battlewire twins are evaluated against the new proof's OWN rows (the
    `_run_cs_rows` pattern).
    **As built, the selftest role's proof block ends with three lines, in this order** (a red line is a Log.Error `|E|`
    line, `FAIL`):
    - `[NetSync] world walk selftest: OK (534 rows, 198 mutants)` (s167: 532 / 196; decision 32);
    - `[NetSync] seat bracket selftest: OK (19 rows, 7 mutants caught)` (new, W1a: `NetSyncSeatBracket.SelfTest`,
      decision 11);
    - `[NetSync] guest menu selftest: OK (420 rows, 249 mutants caught)` (new, W1c-W1i and the W1 review's four fixes;
      every mutant caught by its own distinct row, row names unique).
    `MenuRefusalSelfTest` stays at 14. The proof is pure statics over probe states: the seat round trip uses a probe
    builder (decision 12), and nothing in NetSyncClient is compiled into it, so two of GM0-PROOF's listed mutants are
    not proof rows -- the throwing close request at the ramp's arm and the throwing section-12 reader (the helper's
    build inside BuildStateFrame). Their own-try call sites are pinned by the build's static call-site checks
    (`check_order.py`, `check_w1h.py`), not by a row. Its cost: about 0.4 s per run offline (.NET Framework, unoptimized)
    by W1g and more since, the seat rows rebuilding probe states for every mutant pass; Mono may be 2-3x slower. It runs
    once per process, on the selftest role only.

35. **What each harness proves.**
    - **The selftest role proves the ACTION only.** It never mirrors (the mirror arms only from a real socket's
      snapshot) and runs no DioramaTick. Its rows: the proof; the key verdict through the real Menu key (the bench is in
      `who`); seat, browse, refuse and restore from a `frame` marker; each close action through `fireclose`; the s169
      loopback against a bench host's copy. **Bench frames are built BEFORE the seat** (the critic): a frame built from
      the live state while seated serializes the scratches, and the seat checks pass vacuously. The SlotSource seam
      (NetSyncParty.cs:82) substitutes only section 1's four PLAYERs; sections 2 and 3 read `ff9.rare_item_obtained` and
      `ff9.item` directly (:169, :182), and section 12 reads gil and rare_item_used. So `frame` uses decision 31's
      widened seams, restored in a finally as SlotSource is: as built `BagSource` and `KeyItemSource` for sections 3
      and 2, and gil and rare_item_used passed to `HostMenuBlockOf` as arguments.
    - **The duo** (`tools/harness/duo.py`, two real games) proves the key path, the real triggers and parity end to end.
      It cannot run mixed DLLs (the instance roots junction `Managed`), so its older-peer row is `guestmenu caps off`;
      true version skew only on the two-PC sheet.
    - **T2** needs `coop_peer` to adopt b3 (its serve-guest "auto" caps adopt only b1 today,
      `tools/harness/coop_peer.py:1439-1446`) and a new tape recorded from a b3 host. Until that tape exists, the key-path
      rows run on the duo. Existing s166/s167 tapes and the restamped v14 tape are the older-peer rows for free.

36. **The kit.** battlewire twins of every new rule and constant (`tools/harness/battlewire.py`, beside `MENU_KEY_*`,
    :2014-2017); a fakegame `guestmenu` rung (`tools/harness/fakegame.py`) modelling the ENGINE's facts, with faults
    capture_leak, restore_skip, cut_ignored, leave_ignored, scene_ignored, title_ignored, pause_closed, caps_ignored,
    unmirrored_open, stall_open, seat_at_press, quit_under_close, dialog_drop_lifted, slot_keyed, own_values; `coop_peer`
    (b3 adoption, the section-12 decoder, a `guestmenu` tape plan; from s169 the type-8 encoder and `--intent-at`);
    scenarios and runners under `studies/field-coop/s168/` (and `s169/`), modelled on s167's `round_b_lib.sh`;
    `GUEST_TERMS` (`ff9mapkit/ff9mapkit/workspace/coopdoc.py:63`, "there is no main menu and no saving") and
    `ff9mapkit/docs/tutorials/17-coop.md:81` reworded behind the caps condition ("when both builds have it");
    an s168 marker in `health.NETSYNC_PENDING_GENERATIONS` (`ff9mapkit/ff9mapkit/health.py`), moved into
    `NETSYNC_GENERATIONS` by the commit that ships the s168 engine bundle (W2 critic RK-3: a current row turns every
    pre-s168 install amber with no build to clear it); docs. No new Workspace
    control (there is no off switch).

### The owner-visible words (proposed seeds; the owner tunes them)

- **Guest, a refused press (s168),** by why: `not_mirroring` "You'll get the menu once you've followed your partner into
  a location." (the owner's words); `older` "Your partner's co-op build is older: the shared menu stays closed.";
  `link` "Waiting for your partner's game: try the menu again in a moment."; `no_data` "The menu data did not arrive. Try
  again in a moment."; `data_differs` "Your game data differs from your partner's (<member>)."; `host_battle` "Your
  partner is in a battle."; `host_busy`, `busy`, `ui`, `world_busy` "Try the menu again in a moment."; `scene` "Your
  partner is in a scene. Try again when it ends."; `leaving`, `move`, `host_elsewhere` "You're about to follow your
  partner."; `riding` "The menu opens on foot."; `fault` "The menu couldn't open."; `control` "Try the menu again in a
  moment."; `session` "The co-op session is ending." Each line is prefixed "FF9 co-op: ". (`lever` is silent by design.)
- **Guest, a forced close (s168),** on its own 4 s timer (decision 10): "FF9 co-op: menu closed -- following your
  partner." / "-- your partner's battle." / "-- your partner's scene." / "-- the co-op session is ending." / "-- your
  partner is at the title screen."
- **Guest, the chip (s168):** "View only: your partner's game makes the changes." From s169 the support list of an
  editable member is no longer view-only; the chip's words there are the owner's to tune.
- **Guest, rung-1 refusals (s169):** STALE "Your partner changed <name>'s abilities first. Try again." | NOT_IN_PARTY
  "<name> isn't in your partner's party now." | BATTLE "Your partner is in a battle." | BUSY "Your partner's game is busy.
  Try again in a moment." | LOCKED "Your partner's game locks abilities to equipment." | UNKNOWN "Your partner's game
  doesn't have that ability." | NOT_LEARNED "<name> hasn't learned that ability in your partner's game." | NOT_ALLOWED
  "That ability can't be changed for <name>." | STONES "Not enough magic stones." | SHAPE, ENGINE, MALFORMED, LEVER "Your
  partner's game refused that change." | OLDER "Your partner's co-op build can't change abilities yet." | the hold's
  cap "Your change didn't reach your partner's game." | a view-only member "<name>'s data differs from your partner's:
  view only."
- **Host (s169):** "FF9 co-op: Your partner equipped <ability> on <name>." / "FF9 co-op: Your partner removed <ability>
  from <name>." / otherwise "FF9 co-op: Your partner changed <name>'s support abilities."

## The engine pieces

**W0, docs before any code:** the registry rows (decision 3) in `memoria-patches/README.md`, S166-DESIGN decision 2's bit
list and COMMS-MENU section 4. Done (commit 1f87d546).

**s168 (W1), each piece small.** **Build order** (so each change is proven before the next depends on it): W1a and
W1b, then a `build_memoria.py --no-deploy` artifact kept and pinned for GM0-BRACKET (its output DLLs copied into the
MAIN repo's `backups/` under a label, the backup_memoria_dll.py naming, with their sha recorded; the deploy route is
Order step 2); W1c; W1i's skeleton (the
`guestmenu` sub-verb, `old`, the key with its catch-literal sentinel, the engine-stamped fingerprint); then W1d to W1h,
each adding its own levers and keys to W1i. The two-marker seat round-trip proof rows land with W1f, not W1c. As built
the order was kept, with a W1i completion step after W1h (`events`, `poke`, the `open` key) and the W1 review's four
fixes last. The W1a/b pin is label `pin-s168w1ab`, set 20261107-001809 (the As built section has its files and shas).

- **W1a. The bracket extract (behaviour-neutral, first and alone).** `Memoria/Netsync/NetSyncDiorama.cs`: the static
  bracket (:2853-2896, RememberOriginalPlayer and RestoreParty, :3274-3296; its clears at :815-818, :999-1002, :6246)
  becomes an instance type, with the diorama's instance used everywhere the statics were. A new
  `Memoria/Netsync/NetSyncSeatBracket.cs`. Proven by SeatSelfTest, the bracket selftest (which carries GM0-BRACKET-CLEAR's
  two-instance rows) and the diorama legs. As built the bracket selftest is a new proof line, so NetSyncClient.cs gains
  one hunk (its line in the proof block), and SeatSelfTest runs in game only (decision 11).
- **W1b. The builder extract (behaviour-neutral).** `NetSyncDiorama.cs` MirrorHostParty's per-slot scratch builder
  (:3140-3250) becomes a shared function with the diorama as its only caller. It takes optional per-member overrides
  (preset, category and pa right after FF9Play_New; exp after FF9Play_Build; basisCapa before its own FF9Play_Update)
  and a `rethrow` flag (the menu's seat, decision 12); the diorama passes neither, so it keeps its per-slot containment
  and stays behaviour-neutral. The same proofs. As built: `BuildSeatMembers(ff9, seat, bracket, overrides, rethrow)`
  with `SeatOverride` keyed by CharacterId (decision 11).
- **W1c. The pure core (inert).** New `Memoria/Netsync/NetSyncGuestMenu.cs`: GuestMenuKeyStep, the predicate's rule, the
  door rule, the section-12 codec and its pure order-keeping readers, the content witness, the section-12 guard and its
  TrailReserve, the close-trigger rule, the close-order states, the restore identity rule; the proof line (decision 34).
  Into the csproj and `tools/memoria_stack_replay.py`'s `DEFAULT_FILES` (:60). `NetSyncDiorama.cs` gains the read-only
  `internal static Boolean Armed => _armed;` (decision 8's term 10). As built the key constants (`KeyGuestOpen` 5,
  `KeyGuestQuiet` 6) and `SectionMenu` live here; NetSyncField's `MenuKeyGuestOpen`/`MenuKeyGuestQuiet` (W1e) and
  NetSyncState's `SectionGuestMenu` (W1d) are tied to them, one source each. The replay list carries the two created
  files in this worktree's uncommitted `tools/memoria_stack_replay.py`; the stock files s168 touches are owed (As
  built).
- **W1d. Caps b3 and the sender.** `NetSyncWorldWalk.cs` (OwnCapsRule's second argument; the `OwnCapsFn` delegate made
  two-argument, `OwnCapsNow` passing the live menu lever; the new proof row and s167's re-keyed rows and mutants,
  decision 32); `NetSyncState.cs` (the section-12 constant beside :53); `NetSyncClient.cs` BuildStateFrame
  (:10626-10634) with the send rule, the `HostGuestMenuSectionNow` helper (its own try, decision 5) and the
  FRAME-CAP-GUARD's local check at section 12's append (TrailReserve; BuildStateFrame's order untouched). As built:
  `NetSyncState.SectionGuestMenu = 12` (13 reserved by comment only); `GmSectionSendRule`, `HostMenuBlockOf` /
  `HostMenuBlockNow`, `Sec12FitsRule`; the `caps off|on` lever and the `frame` and `host_fp` keys.
- **W1e. The gate seam, who, the words.** `Global/UI/UIKey/UIKeyTrigger.cs` (:719-722 only; the dialogue path's :889
  stays byte for byte); `NetSyncField.cs` (RefuseMainMenu(why), which takes the verdict as given, beside the
  byte-identical parameterless s121 entry; HarnessMenuKeyNow's `guest`; the why classes in the DeclineOnce book);
  `NetSyncClient.cs` (the press deadline, decision 9; overlay state 29 and its selection in the paired branch at
  :2662-2665 and the off-field chains, the chip beside DrawDialogChip at :15512, the forced-close line drawn by OnGUI on
  its own timer). As built: UIKeyTrigger +5 lines, a new arm ahead of s38's line keyed first on `GuestMenuPressInPlay`
  (W1f adds 2 more lines there, the load-entry backstop: +7 in all, :889 untouched); NetSyncField's `MenuKeyGuestOpen` 5 /
  `MenuKeyGuestQuiet` 6, `GuestMenuPress` and `RefuseMainMenu(verdict, why, member, component)` (decision 6), each why
  its own decline class "main menu (<why>)" (`older` and `lever` write s121's own line), the refusal line cleared at the
  field load; NetSyncClient's live gatherer (`GatherGuestMenuFacts` / `GuestMenuWhyNow`: ONE reused GmFacts, created
  lazily, never on vanilla); the `chip off|on` lever; the `line`, `close_line` and `chip` keys.
- **W1f. The seat, the door, the restore.** `Global/UI/UIManager.cs` (ChangeUIState's door, :601-615: the one open
  verdict for every FieldHUD/WorldHUD -> MainMenu entry, in its own try); `Global/MainMenuUI.cs` (SetMasterSkill skipped
  while seated, :49; EnabledSubMenus); `SceneDirector.cs` (the Replace backstop, :114: it restores and ends the
  session); `NetSyncClient.cs` (the ramp-fire backstop and its `QuitScene.Hide()` before :2048, both in their own try
  that falls through to ExitMirrorToOwnSave, the backstop quiet under `ramp_quit` when the prompt held the close);
  `UIKeyTrigger.cs` (the load-entry backstop, :618: it restores and ends the session); `Global/JsonParser.cs` (the load
  epoch, :251); `Assets/SiliconSocial/AchievementManager.cs` (:80, :119); `EventEngine.cs` (the autosave ladder's seat
  term, beside :703-704); `NetSyncVisitor.cs` (LiveSlotChars itself, :326, covering ResolveDress at :256 and
  ReadSlotChars at NetSyncClient.cs:13969); `NetSyncDiorama.cs` (Boot's refusal, :752-756). The seat's own
  all-or-nothing fault path (decision 12) and the session's clear points (decision 16). As built also:
  `NetSyncParty.cs` (the `BagSource` and `KeyItemSource` seams and `LiveSlotSource`, for `frame` and the release);
  `NetSyncSeatBracket.cs` (five methods over an explicit state, decision 11); the bench ops `frame`, `frame witness`,
  `frame intent`, `host elsewhere|here`, `seat skip`, `seat fault`, `restore skip`, `door fault`; the `seat`,
  `door_refused`, `restore`, `master_skipped`, `ach_held`, `event_enable` and `bench` keys.
- **W1g. The confirm census.** `Global/EquipUI.cs`, `Global/AbilityUI.cs`, `Global/ItemUI.cs` at decision 17's sites;
  Order, Party, Card and Config are greyed through EnabledSubMenus (W1f). As built: eight insertion-only hooks
  (decision 17), the `capture off|on` lever, the `captures`, `passes` and `impactful` keys, and the outside fold with
  `fp.outside_equal` / `fp.outside_named`.
- **W1h. The forced closes.** `NetSyncClient.cs`: CoopCloseGuestMenuIfDue, in its own try (decision 18), and its sites
  (:1965-2020: the close request at the ramp's arm, outside the settle's try{}, and THE RAMP'S SETTLE's two terms, the
  world branch's seat term at :2004 and the press term on both branches; :3697-3756, :4537-4552 with decision 19's BUSY
  while the quit prompt holds the close; :5119-5137, :6153, :7465; the world-to-world close inside WorldLaneStep right
  after WorldCacheStep, :8944, before its LineNone return, client role only; :10993-11013, :11574, :12677;
  ApplyConfigChange's explicit `ending` request, :1773-1812, decision 16); the close's service tick (the step machine
  and the watchdog) after ServiceFollowWarp/ServiceWorldOut (:2054-2055) and before the enabled gate, with no role test,
  in its own try with the guarded fault end and `closes.faults` (decision 21); the close order law with stock's two fade
  forms, the watchdog (its deadline stamped at the request, the fades included), and the held-bit write into `ETb.sKey`
  before each HUD route; `NetSyncAte.cs` (the ATE site, :978); `Global/QuitUI.cs` read only. As built also the `close`,
  `close fault` and `fireclose` levers and the `close_pending`, `close_step`, `last_close` and `held` keys; UIManager's
  OnLevelWasLoaded gate widened to `SeatedOrClosing` (decision 16).
- **W1i. The harness and the fingerprint.** `Memoria/Harness/HarnessAgent.cs` (the `guestmenu` sub-verb at :2505; the
  key and its sentinels in AppendNetsync's catch, :4274, sentinel literal :4363); `HarnessReleaseGuestMenu` in
  NetSyncBattle.HarnessReleaseBench's chain; the `_gmBenchFrame` slot and the bench source seams for the bag, key
  items, rare_item_used and gil beside `NetSyncParty.SlotSource` (decision 31); the engine-stamped fingerprints (`fp`,
  `seat_fp`, the harness-only `host_fp`) in `NetSyncGuestMenu.cs`. As built W1i's skeleton carried the sub-verb, `old`,
  `act`, `clear`, the release, the session book and the fingerprint; the bench slots and seams landed with W1e and W1f
  (bag and key items only, decision 31), `host_fp`'s key with W1d, and a W1i completion step after W1h added `events`,
  `poke` and the `open` key.

**s169 (W2):** W2a the type-8 lane (`NetSyncSocket.cs` NetSyncFrames and INetTransport, `NetSyncRelay.cs`); W2b section 13
and the host helper, gates and tripwires (`NetSyncGuestMenu.cs`, `NetSyncClient.cs` BuildStateFrame and its Update
order; section 13 appended only when 12 was, TrailReserve grown by 13's maximum + 3, decision 5); W2c the press
bracket and the redraw hook (`Global/AbilityUI.cs`); W2d the host's line (overlay state 30, `NetSyncClient.cs`).

Every hunk is tagged `[ff9mapkit netsync s168]` or `s169`; each file keeps its own line endings; each round gets its
`memoria-patches/` entry and README status row. Builds go only through `tools/build_memoria.py`'s literal CLI, with
`--no-deploy` until the owner's s167 two-PC look is done, and never while the owner plays; the pinned W1a/b artifact is
deployed only through `tools/restore_memoria_dll.py` after a `tools/backup_memoria_dll.py` snapshot (Order step 2).
As built the s168 delta is 23 files, every hunk tagged, every file's BOM and line endings kept (CRLF throughout,
HarnessAgent.cs LF); its `memoria-patches/` entry and README row are still owed.

## The bench

Every row names its OLD prediction (measured on the deployed s167 DLL: there the `guestmenu` sub-verb is unknown and fails
closed, the key is absent, the guest menu cannot open (the guest's own menu still opens in the s38 hole, GM0-HOLE), so
rows that need `guestmenu` ops or keys read "not reached") and a LEVER that reproduces OLD on the
new DLL. **THE CAL RULE:** every launch carries a CAL row: exactly the predicted reds, each measured. An S row's OLD is
the selftest role's s121 reading (`open`), never a mirroring guest's. Runners follow
`round_b_lib.sh`: benchguard, FF9 closed, the owner's bridge down for T2, a DLL pin, a cutoff before the 03:00 gate, duo
ports clear of the excluded range. Rows are judged after the init (THE PRE-INIT SAMPLE), on frames published after the
edge they judge, dropping each harness control flip's own publish (THE ORDER SKEW). No bench while the owner plays, and
never under a running test suite.

**K1, read-only, before the s168 deploy (Order step 1):** tag 4 of UID 0 in the deployed world dispatchers
(MenuOpenEvent); whether HashSet enumeration keeps insertion order on this Mono (the key-item display order); the stock
MainMenu close time at FadeDuration 40 and 300. The W1 build was to wait on one K1 result only: the HashSet-order
read, which decides the order-keeping key-item reader (W1c). As built it did not wait: the readers keep wire order
whatever a HashSet does, so the read now decides only whether the seated key-item sets keep that order for the Key
Items screen and for the `keyitems` component of a `seat_fp` / `host_fp` compare (decision 33); it is measured in step 1
with the rest. Also measured there or in step 3, as the builders asked: `UIManager.IsLoading` at the door (decision 9),
whether `frame`'s bench host trailer reaches the receiver cache on a field (terms 3 and 5 on the selftest role), and
whether the HUD's Show turns events and control back on after a door refusal (GM0-DOOR). (No type-5 length readout
exists today, only type-0 `len`; decision 32's `frame` keys add it as
build work.)

**The stand-in:** the fakegame `guestmenu` rung and the battlewire twins (decision 36). A green offline run proves the
driver, not the engine. **Tapes:** a new `COOP_TAPE_GUEST_MENU` (a field roam, a host talk and a chest, a host `warp` out
and back, a walk out to the world and back in, a battle), recorded from a b3 host with the owner's bridge down and the ini
written before launch (THE RECORDER DIALS THE OWNER).

**s168 rows.** Harness: S = selftest (the action only), D = duo, T = T2 replay-host, H = T2 serve-guest, O = offline.

| Row | H | Judge (NEW) | OLD (s167) | Lever / mutant |
|---|---|---|---|---|
| GM0-PROOF | S | the proof lines, in order: `world walk selftest: OK (534 rows, 198 mutants)`, `seat bracket selftest: OK (19 rows, 7 mutants caught)` and `guest menu selftest: OK (420 rows, 249 mutants caught)` (decision 34), with `MenuRefusalSelfTest` at 14; `caps.own_s168_word`, `caps.line_text_s168` and s167's re-keyed caps rows (decision 32); the W1 review's rows (`key.loading_caps_off_older` and `key.pair_on_rule`, `line.never_over_connecting` and `line.not_paired_arm_while_live`, the `settle.*` and `vars.*` rows, the `cut.memory_*` rows); the fault fallback row (a fault with guestSession false takes s121's read); the GuestQuiet row and the RefuseMainMenu(why) rows (decision 6); the door's fault rows (decision 9); the clear-points and config-edge rows (decision 16); the close-rule rows, one mutant per trigger (decision 18); the section-12 guard and the TrailReserve row (decision 5); the press-deadline row at FadeDuration > CloseCapMs (decision 9); the close request's own try (decision 18); the restore-identity rows, EnabledSubMenus put back on the drop path among them (decision 16) | absent | its mutants (each term deleted, seat at the press, Dialogs.Visible for UI quiet, guestSession on IsLiveFollowedSession, MayBoot seat term, a slot-index key, a fault that refuses outside a guest press, each close trigger's row deleted, the identity check skipped, EnabledSubMenus put back only on a restore, the restore door on the `prevState` field; a press bound of CloseCapMs alone: at FadeDuration > CloseCapMs the ramp fires inside the press-to-door fade; a throwing close request at the ramp's arm: the ramp must still fire and ServiceFollowWarp still run; a throwing section-12 reader: sections 0-11, 7 and 8 must stay in the built frame and the publish's Update must still reach NetSyncBattle.Pump -- as built these last two are static call-site checks, not proof rows, decision 34; the W1 review's `key_quiet_caps_blind`, `line_over_connecting`, `settle_same_frame`, `settle_events_blind`, `vars_digest_skips_last`, `cut_memory_never_forgets`, `cut_memory_never_spent` and `cut_memory_spent_by_staleness`) |
| GM0-OFFLINE | O | each fakegame fault reds exactly its own row | n/a | the faults |
| GM0-REGISTRY | O | every flag bit, section id and frame type assigned once across the guest menu, comms, the quit word and B4.2 | n/a | two claims of b1 or of section 12: red |
| GM0-BRACKET | S, D | after W1a and W1b alone, on the pinned W1a/b DLL (label `pin-s168w1ab`, DLL sha256 532486364ec05354...): SeatSelfTest's line and the containment selftest's line (`party[refs=ok untouched=ok]`) identical to s167, and the NEW `seat bracket selftest: OK (19 rows, 7 mutants caught)` green (s167 had no bracket selftest, decision 11); the diorama legs green: coop_diorama_return, coop_battle_flee_defeat, coop_battle_end_guest, coop_battle_result_replay, coop_leader_guard, coop_stock_menu with its _live and _content legs | green | one shared instance for both owners: the cross-restore row red |
| GM0-BRACKET-CLEAR | S (rows of the bracket selftest, shipped with W1a) | two NetSyncSeatBracket instances, a record held in the menu instance; the diorama instance's two failure-clear routines run (the failed-boot clear, the :999-1002 shape; the snapshot-failure clear, the :815-818 shape): the diorama instance empty, the menu instance's references unchanged, party.member ReferenceEquals the originals (as built the rows `clear.snapfail.menu_record_kept`, `clear.failboot.menu_record_kept`, `clear.menu_restores_originals` and the `cross.*` rows) | n/a (one bracket, no menu instance) | one shared instance (the proof's `shared_instance` mutant): the menu's record erased, red |
| GM0-HOLE | T, D | a world-paired unmirrored guest presses Menu: refused, `not_mirroring`, the owner's line; `menu_refusal.now` `audible` | its own stock menu opens (`open`), measured | `guestmenu old`: opens (`guestmenu.open` true, `seated` false) |
| GM0-STALL-WHO | T (the duo's blackhole until the tape exists) | the same guest inside a 3 s blackhole: still refused | opens in the stall | mutant: guestSession on IsLiveFollowedSession (decision 6): the own menu opens in the stall |
| GM0-KEY | D (T once the tape exists) | on FieldHUD with a b3 peer: `now` guest, MainMenu up, `menu_refusal.count` +0, opens +1, seated. A double-tap leg at FadeDuration 300 (two presses 100 ms apart): one open, `menu_refusal.count` +0, no line | `audible`, count +1, lines +1, FieldHUD for 2 s | `guestmenu old`: exactly OLD; mutant: no GuestQuiet row: the second press refused `ui`, count +1, the line over the opening menu |
| GM0-WORLD | D | GM0-KEY on WorldHUD, frozen and walking; aboard: refused `riding`, audible | `audible` + the world-class line | `guestmenu old` |
| GM0-SILENT | S, D | S: `now` reads `open` on BattleHUD and Pause (the bench keeps s121's step, decision 6), the diorama's BattleHUD refusal still buzzes and counts; D: a mirroring guest reads `silent` there; `bmenu mainmenu` still refused on the diorama (coop_stock_menu.py's X row) | S: `open` on BattleHUD and Pause, measured (the selftest role is not mirroring); D: `silent`; `bmenu mainmenu` still refused by BattleHUD's Active gate | the non-HUD RefuseSilent for the bench: S reads `silent`, red; a verdict that opens on BattleHUD: D reads `open`, red |
| GM0-DIALOG-PATH | D, T | (a) a locked host line: judged at :852, `suppress` true, the window stays; (b) an input-taking line the lock does not hold (after the ~ menu unlock): judged at :889, s38's silent drop, `now` `dialog`, the window stays | green | (b) lift :889 for input-taking lines: the line closes |
| GM0-WHY-x | S, D | one row per why: hostscene, host holds input (`swap hostctl off`), intent away (`guestmenu frame intent <field>`: `leaving`), a follow in flight (`swap intent`: `busy`), battle (`netsync lock 1` + `netsync host battle 1`), link dead, no data. On S every row but no data runs after a `guestmenu frame <marker>` (without one, a bench press reads `no_data`, decision 8); each judges `why` and `door_refused.<why>` or `menu_refusal.count` | not reached | each bench op; `guestmenu old` |
| GM0-DOOR | D (FadeDuration 300); S for the :889 and fault legs | Menu pressed as the host's intent arrives inside the HUD fade: the door refuses (`busy` once the follow has started, `leaving` for an intent not yet acted on) with that why's line, events and control back on, no seat, the follow lands; fp equal. One leg opens and closes the menu once on the field, then triggers a door refusal: FieldHUD shown, MainMenuUI inactive, events and control on. The :889 leg (S, on GM0-HUDSTRIP's strip field, `guestmenu host elsewhere`): the bench reaches OnKeyMenu through the dialogue path with no press verdict; the door refuses `host_elsewhere` with its line, the HUD back with events and control on, the strip stays closed (a Known limit). Fault legs (`guestmenu door fault open\|restore`): each ends on a live HUD with events and control on; nothing seated after the open leg; the restore leg keeps the record and the seat flag, and after the next backstop or door ff9.player[*], party.member[*], ff9.item and the rare sets are ReferenceEquals the originals and Order is not grey | not reached | mutant: seat at the press (fp differs, or the follow fade stalls under the menu); mutant: the refusal re-shows `prevState`: MainMenuUI active unseated on FieldHUD; mutant: the door re-runs the predicate only after a press verdict: the :889 leg opens the bench's own party, `seated` false |
| GM0-SEAT | S, D | S: the marker character (slot 0's "BENCH<marker>" at level 99), level and name drawn on Status and in `guestmenu.seat` (`src` the bench frame, `marker`); the gil and exp markers come from `frame`'s bench sources (decision 31); D: for every wire-carried component `seat_fp` per component equals the host's `host_fp` (`keyitems` leans on K1's HashSet-order read, decision 33; `seat.frame_age_ms` reads -1 for a wire seat); TWO-MARKER: the guest's own exp and gil markers on no screen | not reached | `guestmenu old`: own party |
| GM0-SEATFAULT | S | `guestmenu seat fault <component>`: ff9.player[*], party.member[*], ff9.item and the rare sets ReferenceEquals the originals; FieldHUD back with events and control on; why `fault`; opens +0 | not reached | mutant: no rollback: a scratch stays installed |
| GM0-WITNESS | S | `frame witness` frames (decision 31): a preset missing, a pa length off, an unknown equip or SA id, an unknown CharacterId: refused `data_differs`, the component logged; an unknown bag item: refused, component "bag"; an unknown key item: seated, a blank row, the line | not reached | mutant: seat anyway: StatusUI throws |
| GM0-BROWSE | S, D | Item, Ability, Equip, Status, Folklore (or Journal) by label, ui_state per screen, Cancel back, one shot per screen READ; Order, Party, Card and Config are 102 rows (grey, the buzz, no screen opens); Alt+F5 in the menu refused with 102 (s38's mirror gate for a mirroring guest; TryShowSaveScene's state gate on the bench); the main menu has no Save row | not reached | `guestmenu seat skip party`: the guest's own values drawn, red |
| GM0-REFUSE-x | S (D spot checks) | one row per census id. E1-E3, A1-A3, I1 and I2: 102, `refused.count` +1 and `captures` +1 with the site (`refused.last_site`, `last_screen`), `impactful` 0, group as the stock template; Cancel walks back up; at the close `fp_after == fp_before`. (As built `seat_fp` is stamped only at the seat, so "`seat_fp.value` unchanged" would be vacuous at rung 0; the W1g builder's re-key.) O, P and CG (no census hook; greyed through EnabledSubMenus, decision 14): grey, 102, refused +0, no screen opens, as in GM0-BROWSE | not reached | per row: E1-E3, A1-A3, I1 and I2 red under `capture off` (`passes` +1, `impactful` > 0, the seated copy changed) while GM0-RESTORE stays green; O, P and CG excluded from the `capture off` sweep, their own mutant EnabledSubMenus not set: the row opens |
| GM0-LOCAL | S, D | Auto and manual sort, a key-item read, a Folklore read: the seated copy changes, the host's bag order does not, GM0-RESTORE green | not reached | mutant: a sort forwarded to the host |
| GM0-RESTORE | every leg that opens | `fp_after == fp_before` per component; the sandbox saves unchanged; never judged while seated. One leg opens and Cancels at the root with no sub-screen visited (the close's `prevState` field then reads FieldHUD, decision 16) | not reached | `restore skip <c>` once per component: red, `named` == c; mutant: the restore door reads the `prevState` field: the root-only leg leaves the scratches installed, red |
| GM0-OUTSIDE | S | gEventGlobal, Achievement and EventState counters, MiniGame cards, hintmap_id unchanged across a full refusal sweep: as built `fp.outside_equal` true and `fp.outside_named` null at the close (components events, eventstate, achievement, cards, hintmap; events skip the co-op window 2032-2041, decision 17) | not reached | mutant: the Gysahl hook removed on a world map: [181] becomes 1 (`outside_named` `events`); `guestmenu poke` reddens it the same way |
| GM0-MASTER | S (booster on) | SetMasterSkill not called while seated across two sub-screen returns (`master_skipped` +2); `guestmenu.ach_held` rises; nothing reaches the platform | not reached | mutant: the hold without the seat term |
| GM0-SAVEGATES | O | with a seat held on the bench (not mirroring, not booted), the autosave ladder refuses through its seat term: the pure table alone reddens the mutant | n/a | mutant: drop the seat term (pure table only, never on disk) |
| GM0-LOAD | S | seat, then a sandbox load: the backstop restored first (`restore.backstops.load` +1), `seated` false right after it while Serialize is up, and the loaded data sits in the real objects | n/a | backstop off (proof-only, never on disk): the dictionary holds scratches |
| GM0-DIORAMA | S | Boot refused while seated; the open refused while booted, armed or returning | n/a | mutant: a boot over the seat: after teardown the dictionary holds scratches |
| GM0-GHOST | D (GhostAs=auto) | the ghost's rig unchanged for the whole open | not reached | LiveSlotChars on the installed party: the rig flips |
| GM0-FREEZE | S, T (the duo until the tape exists) | `event_enable` false while open, true after; on a tape the talk relay catches up after a short close | not reached | `guestmenu events on` (SetEventEnable(true) while seated): `event_enable` true, red |
| GM0-LEAVE | D (T) | the host `warp`s while the guest sits in Equip's candidates: closes.leave +1, pin age < 2500 ms, the guest lands; a game_snap within 4 s of the close reads the close line on screen | not reached | `close old` + a cancel 3.5 s after the emit: DP-AGED |
| GM0-OUT | D | the host walks out to the world: the close within one host frame of b6, the world-out starts at LiveMs >= 1200, no "the field HUD is not up" | not reached | `close old`: that line until a manual close |
| GM0-REJOIN | D (9010) | the host enters a place: the close, then WorldFollowFire arms with no "world HUD" wait; frozen and walking guests | not reached | `close old` |
| GM0-CUT | D (T; S for the action) | the host's `battle 67 -1` while the guest sits in Item: closes.cut +1, the report BOOTING, start_hold armed, the diorama LIVE, fp equal after the diorama's return; a game_snap within 4 s of the close reads the close line on screen. A quit-prompt leg: the guest's quit prompt up at the cut: the close waits, the report BUSY (never BOOTING), the host's gauges run | not reached | `close old`: BUSY, HoldNotArmed; mutant: BOOTING while the prompt holds the close: the host's gauges held up to StartHoldMs |
| GM0-CUT-NOBOOT | D | a host battle the guest's world visit declines: the menu still closes; the field variant, a host battle scene missing on the guest: closes.cut +1, the "not on this install" line | not reached | `close old` |
| GM0-TITLE | D | the host soft-resets to the title: closes.title +1 within the budget | not reached | `close old`, predicted under THE CAL RULE: closes.title +0; the menu stays open and seated for the leg's hold (no ramp arms: the host at the title keeps its link live); then the leg's own guest Cancel restores at the door (`restore.doors` +1, no backstop line, fp_after == fp_before) |
| GM0-SCENE | D | the host talks to an NPC, then opens a chest, on the guest's field with the menu open 6 s: closes.scene +1, the scene plays, no "expired before my copy was free"; a game_snap within 4 s of the close reads the close line on screen | not reached | `close old`: that line, talk.accepted +0 |
| GM0-RAMP-FIELD | T (`--stop-at` past the grace; the duo's blackhole until the tape exists); S; D for the press leg | on a field: the menu closes at the ramp's arm, ExitRampSettleMaxMs never spent; the field's settle waits for FieldHUD, so the fire follows the close; the door's restore line precedes "reloading own autosave"; the post-ramp fp equals the guest's own. Press leg (a mirroring guest, on a launch whose FadeDuration outlasts the 2 s config poll): Menu, then Enabled=0 lands inside the press-to-door fade: the door refuses `session`: the buzz, `door_refused.session` +1 and its DeclineOnce log line, with no on-screen line (co-op is off: state 29 is chosen only in the overlay chains past the enabled gate, and ApplyConfigChange nulled `_ovlText`); the HUD back with events on, then the ramp's fire once the press is older than CloseCapMs plus FadeDuration; MainMenu never entered | not reached | `close old`: no close; the ramp waits out ExitRampSettleMaxMs and fires with the menu open, the backstop's "should never happen" line before "reloading own autosave"; mutant: no press term: the press leg's ramp fires inside the fade, and stock's menu opens unseated over the Autoload; mutant: a press bound of CloseCapMs alone: at this launch's FadeDuration (above 2 s, so above CloseCapMs) the same |
| GM0-RAMP-WORLD | T (`--stop-at`; the duo's blackhole until the tape exists); S; D for the press leg | on the world: the fire waits for the close (the settle's seat term); WorldHUD is the state at the fire; the door's restore line precedes "reloading own autosave"; no backstop line; fp_after == fp_before. Press leg as GM0-RAMP-FIELD's, on the world | not reached | `close old`: no close; the settle's seat term holds the fire to ExitRampSettleMaxMs, then it fires with the menu open, the ramp-fire backstop's "should never happen" line logged before "reloading own autosave" (`restore.backstops.ramp` +1), and fp_after == fp_before, sandboxed; mutant: no seat term: the ramp fires at its arm with the menu open (the backstop's line); mutants: no press term, and a press bound of CloseCapMs alone, as GM0-RAMP-FIELD's |
| GM0-RAMP-CFG | S, D | D: write Enabled=0 to Memoria.ini while seated, one leg at a sub-screen fade: the menu closes, the ramp fires within CloseCapMs plus one FadeDuration of its arm, input is live after, "FF9 co-op: menu closed -- the co-op session is ending." drawn, fp_after == fp_before; a second leg writes Role=host while seated: the same. S (the selftest role never mirrors, so no ramp arms): the same two edits: ApplyConfigChange's own `ending` close closes the menu, the line drawn, input live after, fp_after == fp_before; no ramp claim | not reached | mutant: the close serviced after the enabled gate: D, the ramp fires at ExitRampSettleMaxMs with the menu open (the ramp-fire backstop's line), no close line; S, the Enabled=0 leg leaves the menu open, no close line |
| GM0-STALL-VIEW | T (blackhole 3 s, menu open; the duo's blackhole until the tape exists) | the menu stays open through the stall | not reached | mutant: close on peer death |
| GM0-QUIT | S; D for the ramp leg | open, Alt+F4 (the quit confirm), `fireclose leave`: the close waits, with no watchdog line past CloseCapMs; then cancel the quit by KEY (Cancel): the close runs, FieldHUD with events and control on. A second leg: a keyboard Confirm on "Quit" quits (the process exits; no save written). The ramp leg (a mirroring guest, on a field): the prompt left up, then Enabled=0: the ramp's fire waits out ExitRampSettleMaxMs and hides the prompt before its backstop, which restores quietly (`restore.backstops.ramp_quit` +1 and its plain line, `restore.backstops.ramp` +0, no "should never happen" line); after the Autoload no prompt, events and control on | not reached | mutant: close under QuitUI: events off on FieldHUD after the Cancel; mutant: no QuitScene.Hide at the fire: the prompt survives the Autoload and its Cancel leaves events and control off on the loaded field |
| GM0-DEPTH | S | `fireclose` at each depth (root, character pick, Item list, target picker, Equip candidates, Ability list, Status, control panel shown): FieldHUD within 150 ms at 40 ms fades, events on, one line. Fault legs (`guestmenu close fault <step>`, at a sub-screen and with a `swap intent` follow in flight): a live HUD, events on, `closes.faults` +1, one line, and the follow still commits | not reached | mutant: the tick unguarded: the enabled section of Update dead every frame, the follow never commits; mutant "ExitMenu before Hide" strands at the control-panel depth (the watchdog line) |
| GM0-REOPEN | S | after each forced close, reopen: each screen's active group and sub-panels at their Show defaults; after the session, the guest's own menu has Order not grey; after a normal stock Cancel, `seated` and `close_pending` read clear and a following `fireclose` is a no-op with no watchdog line | not reached | mutant: EnabledSubMenus cleared only at :339; mutant: the seat flag left held by the restore door: the following `fireclose` counts a close and draws its line |
| GM0-SOFTRESET | S | a soft reset while seated, at FadeDuration 300: the title live with working input (its Confirm works), TitleScene active, no FieldHUD, the session ended at the Replace backstop, the restore quiet (no "should never happen" line) | not reached | mutant: the alarm on a Replace("Title"): the "should never happen" line, red |
| GM0-TIMING | D | close-to-HUD ms at FadeDuration 40 and 300, fast-forward on and off; the follow-start lag (a follow from a visible slot, about 12 ticks later than a join); the pin age against `PinMaxAgeMs` 2500; the LateArmMs margin | not reached | mutant: a full Cancel unwind at 300 misses the late arm |
| GM0-FADE | D | a follow close at MainMenu depth and at one sub-screen depth, each at FadeDuration 40 and 300: the follow starts like a follow from a guest standing on the HUD (s164's Begin joins, hurries or fades the slot from where it is, no hard flash; the pin under 2500 ms); a game_snap pair records the brighten-then-darken below MainMenu at 300 (the visible cost, a Known limit); a close with no follow ends on the stock fade-in, never black | not reached | `close old`: no close; the follow waits for a manual Cancel, then starts from the HUD (today's DL-DEFER) |
| GM0-HELDKEY | S | on a bench field with the guest facing a talkable NPC: Confirm held through a `fireclose`: `held.bits` has Confirm, `held.keyon` +0, no talk starts; released and pressed again: the talk starts (a real re-press is a real edge) | not reached | mutant: no held-bit write: `held.keyon` +1, the talk starts on the held Confirm |
| GM0-PAIRED-LINE | D (one field; one world leg on 9011) | a refused press: the overlay state is 29 (`session.overlay` `guest_menu`) for its timer, not OvlOff, then back. The world leg (added for the W1 review's CR-2, decision 10): a following world guest's refused press (e.g. aboard: `riding`) shows 29 over the world-guest chain's line for its 4 s, then that line returns. A peer-lost leg (the duo's blackhole): a press inside the blip hold (most likely `link`) shows 29 (the paired branch's hold); a press past the grace, before the ramp fires, refuses `session` and shows only the connecting line; the buzz and `menu_refusal.count` +1 either way | no line | mutant: the unchanged paired branch; the connecting-line precedence is proof-only (`line_over_connecting`) |
| GM0-CHIP | S, D | the chip shows while seated, hides at the close | absent | `guestmenu chip off`: seated with no chip, red; `guestmenu old`: not reached |
| GM0-RELEASE | S | every lever set off its default (`old`, `caps off`, `capture off`, `close old`, `chip off`, `events on`, `poke`, `seat skip party`, `restore skip <c>`, `seat fault`, `door fault`, `close fault`: the twelve fields of `lever`; from s169 `apply off` and `check off <gate>`), then a disarm, and separately a harness fault and a reset: `netsync.guestmenu.lever` reads every lever at its default, the release line said once (none when nothing was set), the bench frame, host field and trailer dropped, and the next bench seat (after a new `frame`) draws `frame`'s marker values | not reached | mutant: a release that skips `seat skip`: the next seat draws the guest's own values, red |
| GM0-CAPS-a | D | the host pulls `guestmenu caps off`: the guest's press is s121 exactly (`audible`, count +1, lines +1, FieldHUD), one caps line on the guest, the older-build line on screen | n/a | `caps on`: opens |
| GM0-CAPS-b | T (s166 and s167 tapes) | refused as s121; the caps line names "guest menu" | refused as s121; the caps line names "world fingerprint" (s166 tape) or no line (s167 tape) | none |
| GM0-CAPS-c | T (coop_cut_hold's s121 leg on its v14 tape, unchanged) | a capless peer: G0-G5 and C1 green, no caps line | green | none (the fallback row) |
| GM0-FRAME | O (the proof line's rows and their battlewire twins) | the TrailReserve row recomputes 430 from HeaderLen, OpenLen, OpenCap, the count byte, RingCap and EventLen, plus section 8's 6 B; the pure guard rule appends 12 exactly when len + 3 + len(12) + TrailReserve <= 8192; from s169, 13 only with 12 | n/a | mutants: TrailReserve one byte short (the constant row red); the check without TrailReserve (a frame near the cap with a full ring goes past 8192, red); 13 appended without 12 (red) |
| GM0-BW | D | `frame.type5_len` and `frame.tx_bps` with b3 and with `caps off`, LAN and relay (`tx_bps` is payload bytes per second over windows of at least 1000 ms between harness reads, decision 32: read the key at least 1 s apart) | n/a | `caps off`: the frame shrinks by the block |
| GM0-HUDSTRIP | D (a mirroring guest on a kit field with a persistent [NFOC] strip) | MEASURING ROW for the Known limit (no guest menu while the location keeps a window up): the press takes s121's silent drop at :889: `now` `dialog`, `menu_refusal.count` and `.silent` +0, opens +0, no line, the strip stays | the same, measured | none (a Known limit) |
| GM0-STSCENE | D (one PC, 9011) | MEASURING ROW: the host opens its own main menu for 2 s; read the guest's view of the host trailer's StScene and the walk's why | measure on s167 | none: if StScene rises, a Known limit and a later fix |
| GM0-WORLDTAG4 | D (9010, 9011) | open the seated menu on the world, do at least one sub-screen round trip (Item, then Cancel), close with no load following. Judge runtime state before the open and after the close (the s167 world fingerprint hashes install content only and cannot see a script's writes), as built (the W1 review's CR-3) through harness-only keys: the outside fold stamped at the seat against the settle stamp, `outside_settled.set` true, `outside_settled.equal` true and `named` null (restamped one frame after the HUD turned events back on, so MenuOpenEvent's queued tag-4 request has run; `fp.outside_equal`, stamped at the restore door before the HUD's Show, cannot see it); and `uid0_vars` and `sysvar192` read before the open equal those read after `outside_settled.set`. mapNameStr, MenuOpenEvent's own expected write, stays excluded (no outside component folds it) | not reached | an S leg with `guestmenu poke` (flips gEventGlobal[2047] bit 0 at the next seat, after fp_before's outside stamp; proves the judge sees runtime state): `outside_settled.equal` false, `named` `events`, red; each tag-4 write K1 lists: expected to show |
| GM0-WALKGHOST | D + game_snap | the host's ghost of the guest while the guest's world menu is open (expected: frozen mid-stride) | n/a | none (a Known limit) |
| GM0-OVERLAY | game_snap | the IMGUI lines and chips over the stock menu: readable, nothing covered | n/a | none |
| GM0-DEATH | S, D | kill the guest while seated and relaunch: Continue loads its own or the pairing autosave, fp equal to the pre-session one | n/a | run under the existing `saveguard old` dry-write: any `would_save` +1 while seated is red, the sandbox untouched |

**s169 rows:**

| Row | H | Judge (NEW) | OLD (s168) | Lever / mutant |
|---|---|---|---|---|
| GM1-PROOF | S | the proof gains the codec, gates 1-13, the one-answer ledger, the tripwires; the bracket's seat-only rows (decision 25: no seat with a vanilla toggle gives the stock result, saExtended changed and ImpactfulActionCount +1, zero entries queued, nothing sent; a host-role toggle queues nothing); the re-seat record row (decision 25: open, re-seat C, close: ff9.player[C] ReferenceEquals the guest's original) | absent | per gate; a re-seat that rewrites the open's restore record (the close puts a scratch back as C's own, red); the study's "pa >= cost only" rule must refuse the equipment-taught row; a slot-keyed decoder |
| GM1-CODEC | S | type 8 and section 13 through the real encoder and decoder; truncated, oversized, unknown fmt and n too big refused; an s168 reader skips 13; the order row | n/a | 13 appended after 8: the order row red |
| GM1-LANE | S | a type-8 frame never reaches HandleCommandPayload across a bench battle | n/a | routed on type 2: the malformed counter rises |
| GM1-LOOP | S | a captured support confirm encodes one entry, decodes, applies to the BENCH HOST's copy (its fp moves by exactly the bit and the capa), re-seats; the guest's fp_after == fp_before | buzz, sent +0 | a helper that reads FF9StateSystem moves the guest fp |
| GM1-APPLY | D, H (`--intent-at`) | exactly one entry sent; the host applies; its line for ~4 s; the echo re-seats; the guest's fp equal | buzz, sent +0 | `apply off` (host): an entry in flight answered LEVER (its words); later presses refused locally (applyMask b0 clear), sent +0 |
| GM1-STALE | D (both in menus) | the host toggles first; the guest's confirm: STALE, buzz, line, snap back; the host's edit survives | n/a | mutant: skip the CAS |
| GM1-INV-x | H (crafted), S | unknown id, not in party, unlearned, over capacity, a forced removal, a hidden or banished add, a two-hierarchy set: each refused with its own code, host fp unchanged | n/a | `check off <x>` (learned, capacity, party, known, allowed, shape): that one applies |
| GM1-TRIP | S | `check off capacity` and an over-capacity set: TW1 fires, rolls back, ENGINE, state == before, cur.hp included | n/a | tripwire off: the silent drop |
| GM1-WIPE | S | after an apply, save to a scratch slot and reload: the set survives ValidateSupportAbility | n/a | an apply without FF9Play_Update: the wipe |
| GM1-ONCE | S (`intent duplicate`, `intent drop`) | the host apply counter is 1 per seq; the answer arrives | n/a | without `seq == through + 1`: the counter reads 2 while the state looks the same |
| GM1-RESTART | D | the host relaunches with an entry pending: no double apply (ALREADY or STALE) | n/a | mutant: no epoch reset |
| GM1-PATHS | S, D | OnKeyConfirm and OnKeySpecial each forward exactly one entry | n/a | capture on one path only |
| GM1-SLOT | D | after the host reorders its party, an entry for C lands on C | n/a | a slot-index decoder |
| GM1-IMPACT | D (host) | a remote apply never raises ImpactfulActionCount | n/a | apply through the stock UI path |
| GM1-REDRAW | D | the host's own Ability screen on C redraws to the new state | n/a | the hook off: the stale row |
| GM1-CUT | D | the guest presses just before the host's battle: the menu closes at the cut, the entry is answered BATTLE, the line after the close | n/a | `close old` |
| GM1-LINKDOWN | T (blackhole) | a confirm while the link is not live: refused locally, sent +0 | n/a | mutant: send while down |
| GM1-HOLD | T | a replayed host never answers: C keeps the guest's toggled view while pending, and no host frame re-seats it; at 3 s the hold drops, C re-seats from the latest frame (its old set back), the line | n/a | mutant: no expiry: C keeps the unconfirmed set, with no line |
| GM1-VIEWONLY | S | a member whose derived set differs from the wire is view-only with its line | n/a | mutant: no member data check |

**Order, one change per in-game test by lever.** s168:
1. K1, GM0-STSCENE and every OLD leg on the deployed s167 (an `s168_old.sh` with CAL), before any s168-family deploy:
   the first s168 deploy replaces s167, and OLD can no longer be measured after it.
2. After the owner's s167 two-PC look (and any s167 fix): GM0-BRACKET alone, on the pinned W1a/b DLL
   (GM0-BRACKET-CLEAR is a row of the bracket selftest that DLL carries). The deploy route: the live s167 DLLs are
   snapshotted with `tools/backup_memoria_dll.py`, then the pin kept in the main repo's `backups/` at W1a/b time is
   deployed with `tools/restore_memoria_dll.py <label>` and its sha verified against the recorded one (never a hand
   copy, which skips the pre-build backup and the sha check). If an s167 fix rebases s168, W1a/b are rebuilt and
   re-pinned before this step. As built the label is `pin-s168w1ab` (set 20261107-001809, DLL sha256
   532486364ec05354...); the restore copies the two DLLs only, so the live `.mdb` stays s167's (stack-trace line
   numbers only; the pinned `.mdb` sits beside the DLLs if wanted).
3. The full s168 deploy, after the owner's s167 two-PC look: GM0-PROOF and GM0-OFFLINE; GM0-HOLE and GM0-STALL-WHO; the
   key and seat rows; the census and restore rows; the close rows one trigger at a time (each fires one trigger;
   `close old` is the lever); the measuring rows (GM0-BW, GM0-TIMING).
4. Record COOP_TAPE_GUEST_MENU (the s168 host deployed, the owner's bridge down).
5. The T rows. Until the tape exists, GM0-STALL-WHO, GM0-STALL-VIEW, GM0-RAMP-FIELD, GM0-RAMP-WORLD and GM0-FREEZE run
   on the duo with the duo's blackhole.
6. The regression set; the owner's s168 two-PC look.

s169: the codec and lane rows; the loop; the duo; the regression set; two-PC.

**Regression (judged on the new DLL with the guest menu ACT, never under `guestmenu old` except legs that pull it
themselves):** s167's `round_b_regress.sh` list; the diorama legs (because of the bracket extract and the builder move:
`coop_diorama_return`, coop_battle_flee_defeat, coop_battle_end_guest, coop_battle_result_replay, coop_leader_guard,
coop_stock_menu with its _live and _content legs, SeatSelfTest, the bracket selftest with GM0-BRACKET-CLEAR's rows);
the world walk selftest with s167's caps rows re-keyed over the two-argument rule (decision 32);
coop_cut_hold.py's s121 leg (unchanged); coop_world_walk.py PR-SAVEMENU (re-keyed by
stage); coop_field_swap_timing_duo.py MENU (the Pause legs DL-DEFER, DP-DEFER, DP-AGED unchanged; MENU_PRE_OK re-keyed);
coop_ramp_title.py p17-ownwalk; coop_stock_menu.py's X row; the B4-B5 set (`coop_dialogue_authority`, `coop_talk_relay`);
the kit's proof pins (`MenuRefusalSelfTest` stays 14) and `_coop_peer_bench.engine_stage`. The domain tests run in the
MAIN repo or with the templates extracted.

## Known limits (s168-s169)

- **Story bytes stale mid-field:** the screens read the guest's last field-load mirror (gEventGlobal[16] for the trance
  bar, the NOMAGIC flag, the chocobo bytes).
- **Item sort and the read markers are lost at close** (*Item sort*, *The copy's lifetime*).
- **The view goes stale while open:** rung 0 seats once per open (decision 15), so a host equip, level or reorder shows
  only after Cancel and reopen; a host scene, battle or departure closes the menu anyway.
- **Config and Card are greyed while seated** (a coordinator scope call, decision 14): no in-game settings and no card
  view while the guest's menu is open in a session, which is s167's state for a mirroring guest. A setting changed
  outside the menu still reverts at the session's end: the exit ramp's autoload restores Settings (every load restores
  `50000_Setting`, JsonParser.cs:265-266).
- **No guest menu while the location keeps a window up** -- a persistent kit HUD strip (the kit's behaviour and sim HUDs,
  the persistent-table and ledger readouts, the journal field) or a transient stock window while it is up: a mirroring
  guest's press there is s121's silent drop (:889), with no buzz and no line (decision 6). GM0-HUDSTRIP measures it on a
  kit strip field.
- **A door refusal still costs a window** the press's HideAllHUD closed: stock FieldHUD/WorldHUD.OnKeyMenu runs it before
  the door, so a strip a non-mirroring guestSession player closed through :889, or a world event-cell window, stays
  closed after the refusal, as after a normal open and close (GM0-DOOR's :889 leg).
- **A refusal inside the press-to-door window names the door's why** (decision 9): a follow that starts inside the HUD's
  hide fade shows "Try the menu again in a moment.", not a forced-close line (the menu never opened).
- **A refusal raised after co-op is turned off draws no line** (state 29 is chosen only past the enabled gate,
  NetSyncClient.cs:2057; ApplyConfigChange nulls `_ovlText`, :1814), and one raised while the peer is lost (a `link`
  refusal past the blip hold, or one on a grace-expiry ramp, on a field or the world) is outranked by the reconnecting,
  lost-contact or connecting line (decision 10, the W1 review's CR-2): the buzz, the count and the log line only.
- **The refusal line covers the status lines below it for its 4 s** (decision 10, ratified): on the world the
  world-guest chain's lines (rejoining, the hold, host_world, s167's entry-refused, walk-refused and close-map), on a
  field the following, world-out, peer-no-field and peer-elsewhere lines. Each returns when the line ends.
- **A HUD Hide that never calls back after a guest's Menu press** leaves the HUD dead and the field frozen, as stock
  does; s167 never ran that Hide for a mirroring guest. The guest-menu design no longer recovers it (the press arms
  nothing, so no session, close record or watchdog exists in that window); the next follow or ramp load does.
- **A follow close brightens, then darkens** (decision 21 step 4): below MainMenu at FadeDuration 300 the field is about
  3/4 visible before the follow fades it out; the follow commits about 12 ticks later than a join (GM0-TIMING measures
  the pin margin). Above about 1 s of FadeDuration a follow close ages the pin past `PinMaxAgeMs` 2500 anyway (decision
  21's watchdog).
- **The forced-close line can linger** about 2-3 s over the new field or the battle's opening after a fast landing (its
  own 4 s timer, decision 10).
- **A held button after a close** (decision 21's held-bit write): an `.eb` reading a button's level still sees it; a
  button still held when a following load lands is a KeyOn there, as in stock; a re-press inside the HUD's show fade,
  still held at the first tick back, reads as held; a press (not a hold) in the close's own frame can still reach the
  menu before its Hide (navigation only; the census refuses any write).
- **The quit prompt holds the close** (decision 21 step 1): the close lands when the guest answers; the battle cut's
  report stays BUSY meanwhile; the ramp's fire waits up to ExitRampSettleMaxMs on a held prompt, and its backstop then
  restores quietly (`restore.backstops.ramp_quit`). After that quit-held fire the menu stays open over the guest's own
  objects, with input live, the census off and every row enabled, until the Autoload's scene load sweeps it. A cut
  close whose service tick faults under the prompt ends its record without acting, and the cut's nonce memory never
  re-asks, so that menu stays open until the guest's own Cancel (as built, decision 21).
- **A seat rollback that itself faults** (a double fault) keeps the record and the seat flag held with the alarm
  line, so the scratches may stay installed until the next backstop or door retries the restore element-wise
  (decision 12, as built); every seat consumer keeps gating meanwhile.
- **A world close that stalls past the watchdog:** the ramp fires at ExitRampSettleMaxMs (10 s) instead of about
  1.8 s, through the fire backstop's restore, alarmed (decision 18).
- **No in-game switch for one close trigger:** `guestmenu close old` turns them all off; isolating one on the two-PC
  sheet needs a rebuild.
- **The save gates' seat term sits in the autosave ladder only** (decision 14): ManualSaveRefusedNow, SaveLoadUI's s38
  floor and PairingFreeStanding are not edited; every seat holder is already refused by other terms (a mirroring guest
  by s38's :572 gate, ManualSaveRefusedNow's M term and PairingDurableVerdict's OwnStoryNow; the bench by
  ManualSaveRefusedNow's B term and the client-only PairingWindowTick), including in the restore-fault cell, where the
  seat is held on a live HUD. If a later change lets a player who is neither mirroring nor the bench hold a seat, those
  three would not refuse.
- **A Replace dropped while seated** (a double fault) leaves the menu open over the guest's own restored objects until
  the guest Cancels; the census is inert there, and a stock handler with a stale screen index can throw (logged).
- **The state-identity read is proven offline only** (decision 16): no in-game row swaps the FF9StateGlobal, so a wiring
  error that made the real door's identity read always true would show nowhere.
- **Section 12 can drop early:** the guard's constant reserve drops it up to about 0.45 KB before strictly necessary,
  only in frames already above about 7.3 KB (decision 5).
- **The host's ghost of the guest stands mid-stride** while the guest's world menu is open: the trailer keeps saying
  "walking" (WalkFreeRule reads no UI state). Unchecked visually; GM0-WALKGHOST takes the shot.
- **IMGUI over the stock menu:** OnGUI draws its lines and chips with no UI-state test (NetSyncClient.cs:15481). GM0-OVERLAY
  checks.
- **MenuOpenEvent's world tag 4** runs on the guest's world copy at every MainMenu Show on the world map (the open and
  each sub-screen return); its effect is unverified until K1 and GM0-WORLDTAG4. The settle stamp that judges it (the
  W1 review's CR-3) reads one frame after events come back: a tag-4 script that waits across frames could still write
  after it, and if a follow load lands right after the close, the settle reads the new place.
- **The outside fingerprint skips the co-op window** (gEventGlobal 2032-2041, written every Update while co-op is on):
  a stray write there while seated is invisible to GM0-OUTSIDE (decision 17).
- **True version skew** is proven only on two PCs; the duo uses `guestmenu caps off`.
- **Alt+F9 for an unmirrored paired guest** stays guarded only by s38's mirror gate (pre-existing; its own lane).
- **The world StScene question:** if GM0-STSCENE shows the host's own main menu raising StScene, the guest cannot open on
  the world map while the host is in its menu, until a later fix.
- **A partner that stops speaking b3 while the menu is open** leaves it open as a view (seated once, nothing re-reads
  section 12); the next open is refused with the older-build words.
- **The menu block costs** about 13-29 KB/s host to guest for the whole session with a b3 follower, menu open or not.
- **The ~ menu's Heal, Give Item and Give Gil** act on the view and are lost at close.
- **Content differences refuse the whole open** at rung 0 (the content witness); rung 1 makes a member whose derived
  set differs view-only.
- **LockEquippedAbilities is per machine** (rung 1): the guest's screen may allow a toggle the host refuses as LOCKED.
- **An answer after a forced close is a line only** (rung 1): no seat is left to snap back.
- **The world-to-world close** keys on the trailer's world; whether stock ever moves the host world-to-world without a
  field is unverified.

## Departures from the skeleton (for the coordinator to ratify)

- **D8, the diorama's seat term** sits in Boot's own refusal, not in MayBoot: MayBootNow feeds BootWatching
  (NetSyncClient.cs:4698-4701), so a seat term there would turn decision 19's BOOTING into NONE (decision 14).
- **D3's fail-closed is scoped to a guest press** (a correction the code forces): the skeleton's "a fault in the rule =
  an audible refusal" would cost vanilla, solo and the host their menu, so a fault refuses only once guestSession is
  known true; otherwise s121's read stands (decision 6).
- **D10's world-fingerprint compare is replaced** (a correction the code forces): the s167 world fingerprint hashes
  install content only and cannot see a script's runtime writes, so GM0-WORLDTAG4 judges runtime state.
- **D8's pa[] ordering is impossible as written** (a correction the code forces): FF9Play_New sizes pa[] itself
  (ff9play.cs:135-139), so menu_type and category are set after FF9Play_New and pa[] is re-allocated (decision 12).
- **Type 8's direction:** the skeleton calls it the shared guest-to-host ring. The registry keeps COMMS-MENU's
  bidirectional type 8: one latest slot per direction, s169 using guest to host, the host-to-guest direction reserved,
  unassigned, for comms (decision 3).
- **D8's re-seat at screen boundaries is cut** (a coordinator call, round 3): s168 seats once per open; s169 re-seats
  only member C, from the frame that answers C's entry, at the pending hold's expiry or the session grace, or at a host
  epoch change (decisions 15 and 25).
- **D11's one lever per trigger is cut** (a coordinator call, round 3): one `guestmenu close old|act`, each trigger
  proven in isolation by its own proof mutant (decision 18).
- **D10's Config and Card: greyed** (a coordinator scope call, round 3), like Order and Party, instead of Config staying
  live behind its Booster and Return-to-Title hooks and Card's discard being refused (decision 14; the owner's calls).

### Cut in round 3

The coordinator adopted fourteen simplifications from round 3's review, each with its verifier's correction. What each
removed, so a later reader can tell a cut from an omission:

1. **The press arms nothing** (it supersedes skeleton D6's press-time session flag): the door re-runs the predicate for
   every FieldHUD/WorldHUD -> MainMenu entry, and the session begins at the seat (decision 9). Cut: step 0 of the close
   order, the door's silent refusal with why `closing`, the "no unseated open" rule with its `door_unarmed` key and
   `door fault unarmed`, the press-to-door CloseCapMs expiry with GM0-EXPIRY and `hide nocallback`, the `move` close
   trigger with its `moveclose` lever and words, GM0-WINDOW, and the two-lines-in-the-window precedence. Kept: one press
   deadline (press + CloseCapMs + FadeDuration), read by the ramp's settle. The expiry's cost is a Known limit: a HUD
   Hide that never calls back after a guest's press is no longer recovered by the guest-menu design.
2. **THE INPUT SWALLOW** (skeleton D11) is replaced by the held-bit write into `ETb.sKey` (decision 21): its static flag,
   its UIKeyTrigger and EventInput :231 seams, its held snapshot, its (a)-(f) bound, the `swallowed` key and the
   `watchdog off` op are gone. GM0-SWALLOW is now GM0-HELDKEY.
3. **THE FADE CHOICE** (skeleton D11): every close ends in stock's own fade (decision 21 step 4). The black hold, THE
   CLOSE TAIL (its one remaining duty, the HUD-Show recovery, moved into the watchdog and the tick's fault step) and
   GM0-FADE's black legs are gone.
4. **The :889 narrowing** and its D3 Departure: the dialogue path's read stays byte for byte (decision 6). Its sub-rules,
   MenuKeyRoute's dialogue verdict, the dialogue-path proof rows, GM0-DIALOG-PATH's leg (c), GM0-HUDSTRIP's lever legs
   and GM0-CAPS-a's strip legs are gone; the cost is a Known limit.
5. **Config and Card greyed** (skeleton D10 and D11): the close's Config step (the key capture and the Tutorial depth,
   with its D11 Departure), the census hooks C1, G1 and G2, the Config Known limit and GM0-CFG-RAMP are gone. The quit
   wait stays: QuitUI is still reachable through Alt+F4.
6. **THE RAMP HOLD**: no clock of its own; the world settle reads the seat, both branches read the press deadline, and
   ExitRampSettleMaxMs is the bound (decision 18).
7. **The per-trigger close levers** (`leaveclose` to `sceneclose`) are one `close old|act` (D11 above).
8. **The watchdog's QuitUI.Hide** (skeleton D11's "or hide QuitUI first"): the close just waits on the prompt, and one
   `QuitScene.Hide()` sits on the ramp's fire path (decision 21 step 1).
9. **The re-seat** (D8 above): the re-seat compare, its scratch-set bookkeeping, the item-sort permutation re-apply,
   `frame witness ... next` and GM0-WITNESS's re-seat legs are gone.
10. **The final-frame cap guard** is a local check with a constant TrailReserve (decision 5): `frame big`, `guard off`
    and GM0-FRAME's S row and mutant are gone.
11. **`state swap`** and GM0-STATEID are gone: the identity rule is proven offline (decision 16).
12. **Three of the four save-gate edits** (skeleton D8's list): only the autosave ladder's seat term stays (decision 14).
13. **The dropped-Replace detector** is gone: the Replace backstop restores and ends the session; the `backstop` close
    cause and `closes.backstop` are gone (decision 16).
14. **The landing tracking** of the forced-close line and its D7 Departure are gone: the line lives on its own 4 s timer
    (decision 10).

## As built (s168 W1, 2026-11-07)

W1a-W1i, a W1i completion step and the W1 review's four fixes (W1, CR-2, CR-3, LC1) are built in the shared clone's
working tree (`C:\gd\FFIX\Memoria\Assembly-CSharp`), uncommitted by design: 23 files, every hunk tagged
`[ff9mapkit netsync s168]`, every file's BOM and line endings kept. `tools/build_memoria.py --no-deploy` compiles clean (0
errors, 187 warnings, none in a touched file) and verified the 12 live engine files byte-identical before and after:
nothing is deployed, and the live game runs s167 until the owner's s167 two-PC look. The decisions above are corrected
in place; this section is the ledger. The builders' and the review's reports are `s168_w1p1.json`, `s168_w1p2.json`
and `s168_w1review.json` in the s166-handoff-575aeb session's scratchpad, with every offline proof under its
`s168proof\`.

**The proofs (offline exes over the live clone files; no socket, no listener):**
- `world walk selftest: OK (534 rows, 198 mutants)` -- s167's 532 / 196 plus the two s168 caps rows and two mutants.
- `seat bracket selftest: OK (19 rows, 7 mutants caught)` -- new; W1b's neutrality transcripts equal s167's (S1-S7).
- `guest menu selftest: OK (420 rows, 249 mutants caught)` -- new; each mutant caught by its own distinct row.
- `MenuRefusalSelfTest` unchanged at 14 rows; the whole-delta static checks green (`catchjson_w1r.py`, `check_w1r.py`,
  `check_w1ic.py`, `check_order.py`, `hunktags.py`, BOM and line endings).

**The pinned W1a/b artifact (GM0-BRACKET, Order step 2):** label `pin-s168w1ab`, set 20261107-001809, in the main
repo's `backups/`:
- `Assembly-CSharp.x64.dll.pin-s168w1ab.20261107-001809` and `...x86.dll...`: DLL sha256 532486364ec05354..., 7949312 B.
- `Assembly-CSharp.x64.mdb.pin-s168w1ab.20261107-001809` and `...x86.mdb...`: sha256 39fced7ae666c52c..., made by
  pdb2mdb on a scratch copy (Output's `.mdb` is stale under `--no-deploy`; pdb2mdb is not deterministic).
- The `.mdb` is named `Assembly-CSharp.<arch>.mdb.pin-...`, never `.dll.mdb`, so restore's `Assembly-CSharp.dll.*`
  glob cannot copy it over the DLL; `restore_memoria_dll.py pin-s168w1ab` resolves to the two DLL pins only.
- `restore_memoria_dll.py` restores DLLs only: after step 2 the live `.mdb` stays s167's (stack-trace line numbers
  only). If an s167 fix rebases s168, W1a/b are rebuilt and re-pinned first.

**Deviations kept, and why (one each):**
- W1a: the bracket selftest is a new proof line logged after world walk (one NetSyncClient.cs hunk): s167 had none,
  so GM0-BRACKET's "identical" is the containment line unchanged plus this line green.
- W1a: `Clear()` writes in the Boot clear sites' order, not the containment finally's: on one thread with no throw
  between the writes, unobservable.
- W1a: the bracket's log label is `Who` ("diorama"): every line identical; only an exception's stack frame now names
  BuildSeatMembers.
- W1a: SeatSelfTest's red-row text still names `!_havePartySnapshot`, kept byte-identical (shown only on a red row).
- W1b: SeatOverride is a CharacterId-keyed map applying all five fields, Pa null keeps FF9Play_New's array, pa always
  copied: section 12 keys members by CharacterId.
- W1b: under `rethrow` the faulting slot's scratch stays installed for the caller's record to restore (decision 12).
- W1c: F2 also excludes the ending pseudo-field: ServiceIntentFollow's real test.
- W1c: term 11 maps all eight close causes, so the pure rule never returns null for a firing trigger.
- W1c: F2 / term 11's leave and F3-F4 / `scene` are separate inputs from one read, so each deletion mutant stays seen.
- W1c: term 7 also refuses an inconsistent block as `no_data`: nothing about the install differs.
- W1c: the section-12 reader skips trailing bytes and the encoder caps members, pa and ids: additive fmt-1 appends.
- W1c: the witness's defensive `preset` branch, names from section 1, NoItem never refuses, negative SA ids skipped:
  the builder's own rules, where the design was silent.
- W1c: the close's Loading wait applies only before its own Hide; after it the fade is the close's and the clock runs.
- W1c: FadeMsRule rounds to the nearest ms and reads FastForwardFactor <= 0 as unscaled (UIScene would divide by 0).
- W1c: KeyGuestOpen 5, KeyGuestQuiet 6 and SectionMenu live in NetSyncGuestMenu; NetSyncField/NetSyncState tie to them.
- W1c: extra pure helpers (GuestSessionRule, RefuseEffectRule, the Door* rules, CloseRequestRule, the word seeds): inert,
  each with rows.
- W1c: TrailReserve's section-8 part is recomputed from `NetSyncVisitor.DressBodyLen` plus its header, not the bare 6 B.
- W1i: the fingerprint hash is word-wise FNV-1a 64 (MixU), not FpMix's byte fold: 772 ms -> 126 ms per offline run.
- W1i: `players` folds order-free, `party` adds an identity bit, `bag` skips count-0 rows: sound before/after and
  seat/host compares.
- W1i: `why` is the last refusal's why (NoteRefusal), not a live verdict; `session` is the live guestSession.
- W1i: `lever` is an object, one field per lever, so each later lever adds a field (twelve in s168).
- W1i: its skeleton built the verb with `old`/`act`/`clear`, the release, the book, the key and the fingerprint; every
  other op, slot, seam and key came with the piece that uses it.
- W1d: the send rule reads the real host role, never `hostSections`: the selftest's pinned BuildStateFrame(true, true)
  bytes stay.
- W1d: an out-of-range preset leaves its member out (the guest refuses `no_data`) instead of wrapping to another preset.
- W1d: `tx_bps` is computed only at the harness read over >= 1000 ms windows: production pays nothing.
- W1d: `sec12_len` is section 12's body length; the frame book stamps at every build on any role.
- W1d: the new row `caps.line_text_s168` pins decision 2's caps-line words; the usage line names `caps`.
- W1d: the world walk proof now compiles with NetSyncGuestMenu.cs (OwnCapsNow reads its lever).
- W1d: HostGuestMenuSectionNow also returns null on an empty body (defensive: the block is always at least 10 B).
- W1d: an s167 HarnessAgent comment that named the own word 0x0003 gains a tagged s168 note; its code is unchanged.
- W1e: term 10 passes FieldTransitionNow on a field only: as written it refused every world press (a spec bug).
- W1e: the relay's 65535 host-field sentinel reads as 0 for WT6 and term 11's serial rejoin, as FollowHostTick reads it.
- W1e: RefuseMainMenu's overload is (verdict, why, member, component): the verdict as given, the witness's member named.
- W1e: state 29 also replaces OvlOff in the paired branch's blip-grace hold, where a `link` refusal is most likely.
- W1e: "ended at every scene change" is explicit clears plus a gMode term: a battle has no load hook.
- W1e: `close_line` sits beside `line`: the two lines are timed independently.
- W1e: the bench slots exist from W1e so the gatherer has decision 8's named bench inputs; until a `frame`, a bench
  press on a HUD reads audible `no_data`.
- W1e: `chip off|on` is built as GM0-CHIP's own mutant (selftest bench, read live).
- W1e: extra pure rules (PressActRule, FillIntentFacts, FillSceneFacts, LineWordsRule, the two line-live rules,
  ChipShownRule, DeclineClassRule) and the press-deadline book: each with rows and mutants.
- W1e: the gather reuses ONE GmFacts/GmSeat (none on vanilla); a guest press still parses its frame once, and the
  harness `now` runs the full gather per publish while armed (harness-only cost).
- W1e: GuestMenuPress's catch refuses `fault` for a fault outside the key step's guards (the caller already keyed on a
  guest press).
- W1e: `menu_refusal.now` reads `audible` (s167 `open`) for the bench and an unmirrored guest on a HUD, and counts them.
- W1e: OnGUI reads `Seated` each frame, so NetSyncGuestMenu type-initialises on vanilla (static arrays only, no engine
  read).
- W1f: the record clears only when every family is back or on the identity drop (decision 16), not in a finally.
- W1f: one seat flag, `Seated` = the record's `Held`; W1i's placeholder flag is gone.
- W1f: a faulting rollback keeps the record and the flag held, so every consumer keeps gating (decision 12's exception).
- W1f: five additive bracket methods over an explicit state, so the menu's own instance is the record (decision 11);
  the diorama's four stay byte-identical.
- W1f: the seat round trip runs with a probe builder: the real builder reads live state through FF9Play_New.
- W1f: gil and rare_item_used are HostMenuBlockOf arguments, not seams; the bag and key items got NetSyncParty seams.
- W1f: `seat fault`, `door fault` (and W1h's `close fault`) are one shot, so a fault leg never loops.
- W1f: extra keys `restore.backstops.scene` (the scene clear points' restores) and `bench` (the bench frame's facts);
  `seat.frame_age_ms` is -1 for a wire seat (no arrival stamp).
- W1f: a scene clear point holding a record restores through the identity rule with the alarm; a fault keeps the seat.
- W1f: a HUD -> MainMenu door retries a held record guest session or not (decision 16's retry rule).
- W1f: SeatOver refuses an unknown bag id itself (rolled back), though the witness refuses it first: decision 12's list.
- W1f: alarm lines are Log.Warning; the door's fault line is once per process.
- W1f: `frame` arms the bench host directly, skipping `worldwalk host path`'s refusals; `events on` and `poke` came later.
- W1f: the door's IsLoading exemption was not taken (AfterHide clears Loading before the callback); the bench measures
  it.
- W1f: the seat-keyed hooks also type-initialise NetSyncGuestMenu on vanilla (allocation only).
- W1g: E2 copies the weapon slot's stock branch: every census hunk is insertion-only, no stock line changed.
- W1g: `captures` = confirms caught; `passes` added for confirms `capture off` let through (seat_fp cannot show them).
- W1g: `fp.outside_named` added beside `outside_equal`, naming the first changed outside component.
- W1g: the outside fold masks the co-op window 2032-2041 and adds the script store (else every duo run reads red).
- W1g: A1/A2 also count a forced Selected, A3/I1 hook the confirm's top, unknown sites and census faults refuse.
- W1g: the outside stamps ride inside StampFpBefore/After (no new NetSyncClient site); a drop or restore fault has no
  after, so no verdict.
- W1g: the hooks book through `NoteCensusRefusalAt(site, UIState)`, so a refused press allocates nothing (W1i's
  string form kept).
- W1g: key order: captures/passes after refused, outside_* inside fp, impactful appended (decision 32's list had
  diverged).
- W1h: the close line arms at the close's first act when the quit prompt holds it: no "menu closed" over an open menu.
- W1h: a close is asked only from a menu-family state: a seat kept on a HUD would book a close every frame.
- W1h: `world` is asked only for a world seat: a field seat's wldMapNo is stale and would book `world` for `out`.
- W1h: the tick's fault end touches nothing under the quit prompt (step 1's law) and only ends the record.
- W1h: the watchdog's sweep list is OnLevelWasLoaded's menu family plus the panel steps; never the HUD (its own Show
  follows) or Dialogs.CloseAll (the field's own windows).
- W1h: the sub form omits WaitForFade's depth pair and FF9Sfx 101: the design listed neither.
- W1h: one log line per close, at its end; `close_step` and `last_close.end` added for GM0-DEPTH/QUIT/REOPEN.
- W1h: `fireclose` goes through CloseRequestRule, so `close old` holds it too.
- W1h: both leave sites set LeaveIntent and all three scene sites TalkHere: TriggerFires ORs them, same verdict.
- W1h: a cut merged into another close in flight reads BOOTING; term 11 reads the cut memory (W1e's -1 replaced).
- W1h: three clear-point gates widened from `Seated` to `SeatedOrClosing`, so a close's record ends there too.
- W1i completion: `open` = `IsUIStateMenu(State)`, seated or not: the one read telling the guest's own menu from a seat.
- W1i completion: `poke` = gEventGlobal[2047] bit 0, above every kit band, not restored (the S leg must stay red).
- W1i completion: `events off` and `poke off` added as disarm forms, like every other lever's `off`.
- W1i completion: `events on` calls SetEventEnable(true) once at the seat: nothing turns events off again while seated.
- W1i completion: the release restores the three seams that exist (SlotSource, BagSource, KeyItemSource).
- W1i completion: the poke has 3 rows and 3 mutants, not one row: every mutant needs its own distinct row.
- W1i completion: the catch literal's history gains the missing W1h line beside its own.
- Review W1: GuestQuiet only for a feature-on pair (`pairOn`), so an off pair's fade press is s121's audible refusal.
- Review CR-2: state 29 kept in place, never over the peer-lost connecting line: moving it would hide most world lines.
- Review CR-3: `outside_settled`, `uid0_vars`, `sysvar192` make GM0-WORLDTAG4 judgeable on this DLL, no rebuild later.
- Review LC1: the cut memory resets at an epoch change and the session reset, spent by another live nonce, not by
  staleness.

**Bench rows changed by the build** (corrected in the table above):
- GM0-PROOF: three proof lines with their counts; the W1 review's rows and mutants; the two throwing mutants are
  static checks.
- GM0-BRACKET: the containment line unchanged plus the new seat bracket line, on the `pin-s168w1ab` DLL.
- GM0-BRACKET-CLEAR: the bracket selftest's `clear.*` and `cross.*` rows; the `shared_instance` mutant.
- GM0-HOLE: `menu_refusal.now` `audible`; under `guestmenu old` the `open` key true with `seated` false.
- GM0-WHY-x: every bench row but `no_data` runs after a `guestmenu frame`.
- GM0-SEAT: the BENCH<marker> impostor; `keyitems` leans on K1; `frame_age_ms` -1 for a wire seat.
- GM0-REFUSE-x: judged on `refused` / `captures` +1, `impactful` 0 and fp equal (not the vacuous seat_fp); `capture
  off` reads `passes`.
- GM0-OUTSIDE: judged on `fp.outside_equal` / `outside_named`; `poke` reddens it too.
- GM0-PAIRED-LINE: a world leg and a peer-lost leg (CR-2).
- GM0-WORLDTAG4: judged on `outside_settled` plus `uid0_vars` and `sysvar192` (CR-3); the `poke` S leg named.
- GM0-RELEASE: the twelve lever fields, one release line.
- GM0-BW: `tx_bps`'s window (read the key at least 1 s apart).

**Bench rows no leg reaches (s168 W2; named in the scenarios and `round_gm_new.sh`):**
- GM0-LOAD: no harness verb injects Alt+F9. The proof's restore-identity rows and the stand-in's `gm_backstop` /
  `gm_load` seams stand in, so the in-game load path of the decision text above ("GM0-LOAD covers ... a load") is
  unrun.
- GM0-DEATH: a kill plus a relaunch; no runner launches it (an open item).
- GM0-CUT-NOBOOT: one install has no missing battle scene; the world decline has no route.
- GM0-CUT-QUIT and GM0-QUIT-D: no any-role quit-prompt verb (`endbench quit on` is the selftest role's).
- The GM0-RAMP-FIELD / GM0-RAMP-WORLD press legs: no instance-root [Interface] FadeDuration writer, so the
  press-to-door fade stays under the 2 s config poll.
- Halves the built legs do not reach: GM0-DIORAMA's open refused while armed or returning (no verb holds either
  state; the booted half is GM0-SILENT's press) and GM0-SILENT's "still buzzes and counts" (not judged); GM0-HOLE's D
  half (a duo pairs a mirroring guest: GM0-HOLE-T is the route) and GM0-DIALOG-PATH's T half (an open item);
  GM0-REJOIN and GM0-WORLDTAG4-D on 9010 (the New-Game exit cascade lands on 9011 only: both run on 9011) and
  GM0-REJOIN's frozen guest (an open item); GM0-PAIRED-LINE's past-grace press (`session` under the session's own line:
  OvlReconnecting while SessionGrace holds, not the connecting line the row names; the window is ~0 at the stall
  leg's SessionGraceMs 5000 against GhostGraceMs 5000; the precedence stays proof-only, `line_over_connecting`).

**Owed (not built here):**
- Kit twins in battlewire, evaluated against the proof's own rows (`_run_cs_rows`): every new rule and constant of
  W1c-W1i and the review (the key step with `pairOn`, PairOnRule, PressActRule, the fill and line rules,
  NotPairedLineRule, the codec and send/guard rules, the door, seat, restore and census rules, the close rules,
  CutMemoryRule, SettleStepRule, VarsDigestRule, the fingerprint rules and MixU constants, PokeRule/PokeByte/PokeBit,
  OutMaskLo/Hi, GuestLineMs/OvlGuestLine, the site ids and component names) and `ww_own_caps_rule(fp_off, menu_off)`.
- Kit pins: guest menu (420, 249), seat bracket (19, 7), an s168 world walk tally (534, 198) beside
  `WORLD_WALK_PROOF_S167`, MenuRefusalSelfTest 14.
- Kit readers: the full `netsync.guestmenu` key (decision 32), the usage line, `menu_refusal.now`
  `guest`/`audible`, `session.overlay` `guest_menu`.
- Re-keys: test_coop_world_walk_b.py:273, :488, :490 and fakegame.py:9872 (caps by stage); `lane.caps.own` and
  CAPS_S167 (0x0B on an s168 stage, 0x03 under `caps off`); PR-SAVEMENU and MENU_PRE_OK; STAGE_KEYS' s168 stage.
- Re-keys: any bench leg that pressed Menu on a HUD with the field-gate bench on (now audible, `no_data` until a
  `frame`); any check keyed on guestmenu's last key (now `sysvar192`).
- The fakegame `guestmenu` rung and decision 36's faults; `coop_peer`'s b3 adoption and section-12 decoder; the
  `COOP_TAPE_GUEST_MENU` tape.
- Scenarios and runners under `studies/field-coop/s168/`; a GM0-RELEASE driver that sets all twelve levers.
- `health`'s s168 marker (built in W2 as `NETSYNC_PENDING_GENERATIONS`; the bundle's ship commit moves it); GUEST_TERMS and `17-coop.md:81` reworded behind the caps condition.
- `tools/memoria_stack_replay.py` DEFAULT_FILES: the two created files are in this worktree (uncommitted); the eight
  stock files (UIManager, MainMenuUI, JsonParser, AchievementManager, EventEngine, EquipUI, AbilityUI, ItemUI) at the
  freeze.
- The `memoria-patches/` s168 entry and README status row.
- The step checkers that compare against their own step's snapshot (check_w1e's +5, catchjson_w1h's 10-lever object,
  check_w1f's old anchor) read expected drift; the whole-delta checks supersede them at the freeze.
- In game, after the s167 two-PC look: every GM0 row; the K1 reads and the measurements named under "The bench" (K1).

## As built (s168 W2, the kit and the bench, 2026-11-07)

W2 ran as one workflow (`s168/s168-w2-kit-bench-wf.js`: sync, kit, bench, critic, reconcile). Its critic and reconcile
died on a usage limit and were re-run from the finished phases (`s168/s168-w2-critic-resume-wf.js`). Nothing in W2
touched the engine clone (it still matches the 23-file snapshot the W1 review signed off), `memoria-patches/`, the live
install or the game.

**What landed:**
- `tools/harness/battlewire.py`: twins of every s168 constant and pure rule the bench reads or decodes (the caps word by
  stage, the key step with the lazy `pairOn`, the 23 predicate terms, the close order law and causes, the doors, the
  13 sites, section 12's codec and readers, the line rules with CR-2's NotPairedLineRule, the census and fingerprint
  rules, the harness literals and GUEST_MENU_SENTINELS). The proof-row evaluator runs the twins against the proof's own
  C# rows: 148 pass, 0 fail, 141 skip (block lambdas and probe builders). Pins: guest menu 420 / 249, seat bracket
  19 / 7, world walk 534 / 198, each derived from the source when `FF9_S168_CLONE` is set, else the W1 build's tallies.
- `tools/harness/fakegame.py`: an opt-in `guestmenu` rung (`guest_menu_stand_in`, never on the ladder; the default
  stand-in stays s167) with 18 faults (`GUEST_MENU_FAULTS`: decision 36's plus release_skip, settle_same_frame and
  guest_menu_proof_fail), each red on its own row.
- `tools/harness/coop_peer.py`: `caps_now` 'auto' adopts b3 from an s168 host, `--caps 3` pins an s167-shaped guest,
  section 12 is decoded in `dump` / `where --pose`, and replay-host carries section 12 as recorded.
- Scenarios: `coop_guest_menu.py` (S: 17 legs, 63 rows) and `coop_guest_menu_duo.py` (D: 15 legs, 39 rows; T: 4 legs,
  10 rows). Runners under `s168/` (`round_gm_lib.sh`, `round_gm_{old,new,lever,regress,rerun}.sh`,
  `round_gm_guard.py`): OLD 35 launches, NEW 36 plus 2 named tape skips, LEVER 53, REGRESS 62 (9 with
  `ROUND_GM_SET=bracket`). They keep s167's guards and add a DLL pin by kind (old `12be3220520813a6`, bracket
  `532486364ec05354`), a gate-window refusal (02:30-07:00), a port preflight and a proof-block diff against OLD's
  reference. Only their `ROUND_GM_PLAN=1` dry mode has run.
- Re-keys by stage, none weakened: decision 32's list, plus two the regression pass found that would have reddened every
  s165-s167 leg on s168 (`coop_world_follow.judge_probe`'s netsync tail gains `guestmenu` only when present;
  S166-A-PROOF and S167-W-PROOF read their tally through `proof_stage`).
- Texts: GUEST_TERMS and tutorial 17 behind the caps condition. The health marker waits in
  `NETSYNC_PENDING_GENERATIONS` (RK-3, below).

**The critic:** five read-only lenses (row coverage, falsifiability, twins against the C#, re-keys and runners, the
open reds), each finding adversarially verified: 33 found, 24 confirmed, 0 unverified. One fixer applied all 24, and
every fix that adds or tightens a check was broken on purpose, seen red and restored byte for byte (22 cases). The
substantive ones:
- Calibration: OLD now needs every predicted red MEASURED (`needs = pred`), and `cal_verdict` reds an s168 launch whose
  lever was refused or never read back (L-3, L-6).
- The stall rows: STALL-VIEW needs a stale sample, STALL-WHO-T counts only an in-stall press (the T hole's blackhole is
  now STALL_S + 1.5), and PAIRED-LINE-LOST judges only samples taken while the link was still down (L-4, L-5, H1).
  H1 was the red the dead run left: the duo leg read 29 after the link returned.
- The close rows now judge the close WORDS (`_CloseWatch` samples the line at the close; L-7); the paired line needs
  three live samples, every one `guest_menu` (L-9); the ramp's `close old` measure waits 2.5 s (L-8); GM0-WORLD's
  frozen half must first read frozen (L-13); the pin bound is inclusive like PinUseRule (T-4).
- The proof-row evaluator stopped dropping rows (three more mutants caught: CloseEndsAt, CutMemory, Boot; T-1).
- RK-3: a current health row would turn every pre-s168 install, the owner's live s167 included, amber with no build
  to clear it. The row waits in `NETSYNC_PENDING_GENERATIONS`, which `netsync_generation` never reads; **the commit
  that ships the s168 engine bundle moves it into `NETSYNC_GENERATIONS`** and updates test_health's pending pin.

The reconcile re-read every fix against the clone and found one defect both had missed: GM0-QUIT-D read
`netsync.battle.end.quit_open`, which no engine publishes, so its "no quit prompt after the Autoload" half could not
fail. It now reads `cb.quit_prompt_up`, and a new clone pin checks every `netsync.*` / guestmenu path the two s168
scenarios read (221) against the catch literal's key tree.

**Tests:** the co-op domain set (24 files, `FF9_S168_CLONE` set, clone pins live) ran once at `-n 6`: 3007 passed,
1 failed, 46 skipped (all predating s168) in 1:22. The one red, test_coop_world_battle's `warm_lever_stuck`, passed
alone: wall-clock noise under load. The two files the reconcile touched then re-ran green (141).

**Open (beyond "Bench rows no leg reaches" above):**
- `_CloseWatch` reads the guest's state from a second thread while the main thread drives the other game; proven on
  the stand-in only. The first real duo run should confirm the close words land on the out, rejoin and scene legs.
- The T hole leg's 4.5 s blackhole fits `pick_window`'s span offline only; `_t_pull`'s lever read-back and the T run's
  `needs = pred` have no offline test (no T leg runs on the stand-in).
- GM0-QUIT-D still has no duo route (`endbench quit on` is the selftest role's); its corrected read has never run.
- The coverage tests still accept a row named anywhere in a docstring.
- Still owed from W1's list: `tools/memoria_stack_replay.py`'s DEFAULT_FILES (left uncommitted until the freeze), the
  `memoria-patches/` s168 entry, the `COOP_TAPE_GUEST_MENU` tape (owner-gated), OLD on the live s167 before any s168
  deploy, then every GM0 row in game.

## The owner's calls

All DECIDED. From 2026-10-31 (`GUEST-MENU.md`), by name:

- *Architecture*: Option A, the stock menu over a copy of the host's party; the host does every write.
- *First build*: view-only (rung 0, s168), then support abilities (rung 1, s169).
- *Which characters*: the whole party; no setting was asked for (decision 4: no off switch at rungs 0-1).
- *Both players in menus*: allowed; the host rechecks, so a stale guest change is refused with the buzz and a line.
- *Party order and row*: host only (Order and Party greyed).
- *Item sort*: sorts the guest's view only.
- *The host starts a battle*: close the guest's menu at the battle cut (every cut).
- *The host leaves the field*: close the guest's menu at once, then follow.
- *The copy's lifetime*: only while the menu is open, restored on close.
- *Host notification*: a one-line message on each applied guest change, from rung 1.

From 2026-11-06:

- **Refuse the unmirrored guest** with the buzz and "You'll get the menu once you've followed your partner into a
  location." (decision 7).
- **Close on a host scene:** a host conversation, chest, ATE or scene starting on the guest's field closes the menu
  (decision 18).
- **All three guest words:** the refusal line, the forced-close line and the "View only" chip (decision 10).
- **Deploy after the s167 two-PC look:** s168 built now with `--no-deploy`, deployed after that look (decision 1).

**A coordinator scope call the owner may reverse later** (round 3): Config and Card are greyed while seated, like Order
and Party (decision 14). The study's screen table listed both as the guest's own (GUEST-MENU.md:170-171), and the
owner's decisions are silent on them.

**A coordinator call the owner may reverse later** (the s168 W1 review, CR-2, ratified 2026-11-07): the refusal line
(overlay state 29) yields to the wire-mismatch, reconnecting, lost-contact and connecting lines and, for its 4 s, covers
the following and world status lines below it (decision 10).

**Open:** none. Only seeds the owner may tune after the two-PC look: every line's words (including the host-at-title
close words and the rung-1 chip), the 4 s guest and host lines, CloseCapMs 1500 ms, the 3 s pending hold.