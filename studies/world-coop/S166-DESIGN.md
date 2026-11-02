# World-map co-op: free walk on foot, with ghosts both ways (s166-s167)

Today a following guest lands on the world map at the host's spot (s165) and stands there frozen until the host's next stop.
This is rung 2 of `GUEST-FOLLOW.md`'s two-body order: the guest walks its own copy of the world on foot, and each player
sees the other as a second body. It is one design, built in two rounds (decision 1, the owner's call):

- **Round A, s166: the wire and the ghosts, with the guest still frozen.** Wire v15 (owner decision 14) with the world pose
  both ways; the receiver cache; the lane-gap lines on both roles; the host's lines (decision 13); the world ghost both ways.
  The frozen guest sees the host's ghost walk, and the host sees the guest's ghost. First and alone: decision 19's
  control-off kit-cell close, which closes a live s165 hazard and changes no lawful guest behaviour. Second, also alone:
  decision 26's pairing pull (the owner, 2026-11-02): a guest that pairs while the host stands on the world map follows it
  out instead of waiting for the host's next stop.
- **Round B, s167: the walk.** The seam that frees the walker; the entry refusal and its words (decision 4); the pairing
  rule and the stall hole; the fingerprint (decision 10); the DeclineOnce re-arm; WorldTPS; and decision 8 (the full map)
  if the owner opens it.

The harness protocol stays 5. Every new lever's `off` (or `old`) is the previous round exactly, for s144, s145, s154, s163,
s164 and s165 alike. The one thing no lever restores is the version byte: from s166 on, both machines must run the new DLL.

The recon (4 read-only lanes, a verifier per lane, a critic, then a census of the deployed world scripts) is in the session
scratchpad as `wf2/recon2.raw`, digested to `wf2/digest2_*.md`; the census is `wf2/census/deployed_world{02,10,11}.pdis`
(the kit's pure reader, stdout and scratch only; no game bytes enter the repo). C# lines are the live s165 clone's
(`e364ca8d`). The build re-finds each site.

## What happens today (s165)

- **No one sees anyone.** On the world map both roles send type 0's field-0 sentinel (`SetLocal(0, ..., Vector3.zero, ...)`,
  NetSyncClient.cs:2403-2408). The guest has the minimap dot (section 0, about 7 steps a second); the host sees nothing, and
  its only world-map overlay is OvlConnecting when the transport drops. The host is blind to stalls: only the guest has an
  outage clock (2 s), and a ~2.3 s two-way stall (about one every 13 minutes on the owner's link) leaves no host trace.
- **A frozen guest's Confirm is masked silently.** FilterScriptButtons' gMode-3 branch (NetSyncField.cs:953-961) strips
  every HostOwnedKeys bit and logs "world script button-poll" once per world map, for the whole process: the DeclineOnce
  world book never re-arms, so a second visit to 9011 is silent.
- **The latent kit-cell hazard (exists on s165 today; closed in round A, s166, by decision 19).** The Southern Ring adds six cell functions
  to entry 0 of the deployed WORLD02/10/11 (6601 x4, 6602, 6603). Each reads a bare `KEYON(Confirm)` behind only an on-foot
  branch, with no usercontrol term, and on a press runs DisableMove, a fade and `Field()` itself (census: WORLD11 pdis
  L363-523). The engine requests a cell's function every frame the controlled walker stands on it, whether or not control
  is on (ff9.cs:5323-5353; compare w_movementControl behind GetUserControl, :5185-5187). FilterScriptButtons' control-off
  branch passes the guest's own keys when no dialogue lock holds (NetSyncField.cs:992-1004). So a Confirm pressed in any
  control-off tick while standing on a kit cell takes the guest into 6601/6602/6603 alone, faded: s42's no-recovery class.
  **Corrected by the A0 bench (2026-11-02):** the engine requests a cell function only while the walker stands on a terrain
  triangle carrying the entrance's event id (ff9.cs w_movementUpdate: `m_GetIDEvent(id) != 0` -> WorldEvent), and the
  6603 entrance was written with `--trigger-at 80 -444 --trigger-radius 3.0 --no-tile-area`, so only the triangles within
  3 u of (80, -444) carry it. FS_LANDING (68, -444) is in cell (2, 13) but 12 u off that trigger: it does NOT stand on the
  entrance (measured on s165: a frozen guest's control-off Confirm there did nothing). A guest stands on a trigger when the
  host stood on one at the follow-out (the guest lands on the host's spot), or after a teleport. A deterministic window: the ~ menu open with "Disable control" runs SetUserControl(false) in any scene
  (Ff9mkDebugMenu.cs:821, 839-848), the same menu that holds the s144 Release row. WORLD11's kit boat (entry 15) and ferryman
  (entry 16) read bare Confirm the same way (L2245, L2543). TWO-PC-CHECKS-S165 now carries the warning (2026-11-02): press nothing on the guest while it lands,
  and never open the ~ menu on the guest while it is on the world map.
- **A guest that pairs while the host stands on the world map waits on its field** (the s165 two-PC session, 2026-11-02).
  WorldOutStep's term 3 refuses a guest that is not mirroring yet (`not_mirroring`, THE PAIRING-WINDOW LAW), although the
  law protects only a pairing autosave that has not been written, and the owner's laptop wrote its autosave the moment it
  paired. It follows the host only into the host's next location. Decision 26 pulls it out.
- **A world-paired guest goes free in a stall.** A guest that paired or Continued on the world map is not mirroring (the
  mirror arms only at a field load, NetSyncClient.cs:1121-1128; decision 26 adds a follow-out's landing, which a guest
  already on the world map never takes), so SpectatorField rests on IsLiveFollowedSession, which
  needs a remote fresher than StaleMs 2000 (NetSyncSocket.cs:315). In a 2.3 s stall the whole s144 mask lifts:
  FilterScriptButtons returns the raw keys at `!SpectatorField` (NetSyncField.cs:928), so Confirm, Cancel and the full map
  pass; SkipWorldScriptedBattle keys on SpectatorField alone (:316), so the place-52 quicksand's Battle(0, 144) boots
  locally; and the lift and re-freeze lines print. Inherited from s144.
- **Kit 9011 is not stock 9011.** The deployed WORLD11 adds a boardable boat (entry 15, binds w_movePlanePtr, mode 7) and a
  ferryman whose Confirm runs a local fade-and-walk scene (entry 16; no `Field()`), besides the ferry voyage director in
  Main_Init on Global.Byte[1872]. Stock 9002/9010/9011 carry no vehicle at all.

## The decisions

### Both rounds

1. **Two rounds, one design (the owner's call; recommended).** Round A is observable while the guest is still frozen, so
   the wire, the cache and the ghosts are proven before anything rides on them. Reasons: one change per in-game test; THE
   DEFECT FOLLOWS THE AUTHORSHIP (round A is the larger new surface, and it changes no lawful guest behaviour); and v15 alone
   breaks every mixed pair and every recorded tape, so it should be proven on its own. The cost: walking waits one round.
   Decision 19 rides round A, first and alone, so neither the round-A deploy nor its two-PC look runs with the hazard live.
   Decision 26 (the pairing pull) follows it, second and alone: it needs no wire change, so its OLD is the A0 build.

### Round A (s166): the wire, the cache, the lines, the ghosts

2. **The v15 law.** `NetSyncWire.Version` 14 -> 15 (NetSyncSocket.cs:176), alone in this round. No v14 byte changes
   meaning. Every later v15 feature is additive (a trailer, a new section, a new type, a longer body) and gated on the
   PEER's capability bit, which rides the trailer both ways: b0 world pose (s166), b1 world fingerprint (s167), b2 comms,
   b3 the guest menu, b4 B4.2's v2 command frame. Two v15 builds of different vintages then pair and switch the newer feature
   off with a line, instead of half-syncing. "Off" always means the older behaviour: for the walk that is the s166 freeze,
   never a walk without the check (decision 14 term 10). Peer caps are re-read from every sample, never latched per link;
   every v15 frame carries the trailer, the relay's constructor sentinel included (decision 4). `B4-B5-DESIGN.md:1241` ("the
   single v15 bump is reserved for B4.2") gets a superseded note citing decision 14.
3. **An old peer never pairs; say so.** A v14 and a v15 engine reject each other's every frame: the relay drops them
   silently (NetSyncRelay.cs:356-372), TCP disconnects and redials every 2 s (NetSyncSocket.cs:894-901). The study's
   "degrade to the freeze on an old peer" is false under v15. The v15 side counts frames whose magic is right and whose
   version differs, logs once per process and peer version (never per link: TCP redials every 2 s) "the partner's engine
   speaks wire 14, this one speaks 15 -- update both machines", publishes `netsync.wire_peer` and shows a line; TCP redial
   lines dedupe to one per break reason. Every transport start logs its own wire in one line (today none does:
   NetSyncClient.cs:11224 is a harness key only). The laptop package gets a step 0: the certutil hash of the DLL on both
   machines; a rollback rolls back both.
4. **The world trailer on type 0.** The 39-byte s157 record is unchanged and `Field` stays 0 on the world map on both roles
   (eight readers take it as a field id: a world id there is the black-screen class). A trailer follows, little-endian:

   | Bytes | Field | Notes |
   |---|---|---|
   | 39 | tfmt u8 = 1 | 0 or absent: a capless peer |
   | 40-41 | caps u16 | decision 2's bits |
   | 42-43 | seq u16 | +1 per sender Update (re-sends repeat it) |
   | 44-47 | ms u32 | the sender's NowMs, low 32 bits; only differences are used |
   | 48 | place u8 | 0 none/title, 1 field live, 2 a scene transition in flight in any scene (SceneDirector.IsFading, a pending or swirl scene: field fades and loads, the world-out fade, a battle's swirl and load), 3 world loading (no w_blockReady), 4 world live, 5 battle, 6 world diorama |
   | 49 | state u8 | b0 frozen (WorldFreezeNow), b1 walking free, b2 user control, b3 own full map open, b4 content mismatch, b5 world-out in flight, b6 scene, b7 walker visible |
   | 50 | why u8 | high nibble the rule (1 WorldOutStep, 2 WalkFreeRule, 3 GhostRule), low nibble its refusal code |
   | 51-52 | world u16 | the live wldMapNo on place 4, else 0 |
   | 53-64 | x, y, z f32 | `w_moveActorPtr.RealPosition` (canonical) |
   | 65-80 | rot 4 x f32 | that actor's `transform.rotation`: one transform, one time base |
   | 81 | mode u8 | [190] |
   | 82-87 | model u16, anim u16, animFrame u8, frameN u8 | the walker's own |
   | 88-91 | digest u32 | 0 until s167's fingerprint |
   | 92 | worldTps u8 | the sender's [Graphics] WorldTPS, always filled |
   | 93 | flags u8 | b0 I follow (`_followHost` on the client role); b1-b7 zero |

   - The world block (51-87) is valid only on place 4 with a real walker (not null, not the dummy, not the bee scene) and
     zeroed elsewhere: inside a diorama the walker's transform belongs to an unloaded scene.
   - Never gEventGlobal 64-72: the anchor stops writing them while WORLD10/11's Map[37] is latched (a host Gysahl press, the
     kit voyage), so section 0's pose freezes there while the walker moves.
   - The scene bit b6 is the sender's own: control off, or its walker hidden, for over 500 ms, not counting its own full
     map (w_naviMode 2), a fade, or the ~ menu's "Disable control" hold (Ff9mkDebugMenu's `_controlHeld` through an
     accessor: SetUserControl(false) while open, :839-848, persisted and used routinely). Section 7 b1 alone cannot serve:
     the host's own full map drops it (WorldHUD.cs:254, 447).
   - The state byte is full and its b0 drops for a released guest and in a stall, so "the peer follows" rides flags b0;
     the host's terms of GhostRule and HostLineRule key on it.
   - Built at the one SetLocal site on both roles (NetSyncClient.cs:2394-2408), through `INetTransport.SetLocal` in both
     transports (the relay's SetLocal, NetSyncRelay.cs:99-104). The relay constructor's 65535 sentinel (:80-83) is built
     with the trailer too (tfmt 1, own caps, place 0, the world block zeroed). On the selftest role, which has no socket and
     returns before that site, the same builder and BuildPosPayload run beside WorldOutTick before the `!inScope` return
     (NetSyncClient.cs:2049-2050) into a harness-visible slot that publishes the tx keys. About 94 B at ~30 Hz: ~2.8 KB/s
     each way.
   - **Departure from the critic:** WorldTPS rides only this trailer, not also section 10's body[2]. The host's trailer
     already reaches the guest every write tick; one carrier keeps section 10 and s163's rows byte-identical.
5. **The receiver cache (both roles).** Every Update, right after GetRemote, with two clocks held across the 2 s Valid cliff
   (past StaleMs GetRemote returns a bare `Valid = false`, NetSyncSocket.cs:560-566): `lastArrival`, copied from
   rs.ArrivalTick on every Update where rs.Valid, same-seq re-sends included (Accept refreshes `_remoteTick` on every TypePos
   frame, :512-518); and `lastSeqMove`, the local tick when the seq last changed. On a new seq: parse forward and keep the last
   valid world sample with its seq and ms (RemoteState is a struct copy, so the type-5 lane's reference test cannot serve).
   NetSyncFrames exposes its `_remoteTick` as an arrival tick on RemoteState. The cache resets at the title, a session edge
   and the peer's epoch change. On the selftest role the bench path (the receiver, the bench host, decision 4's own
   trailer) runs before the `!inScope` return (NetSyncClient.cs:2049-2050), beside s165's WorldOutTick.
6. **The lane-gap lines (both roles).** A pure `LaneGapStep(now - lastArrival, now - lastSeqMove, lastPlace)`:
   - arrivals stopped >= 1000 ms is a GAP: a start line, and an end line with its length;
   - arrivals fresh but the seq frozen >= 1000 ms is a HANG, worded "loading" when the last place was 2 or 3. A peer in its
     own synchronous load keeps arriving (the writer re-sends its last slot) with a frozen seq: THE PRE-LOAD HEARTBEAT and
     A GAME PUBLISHES NOTHING DURING ITS OWN SYNC LOAD are the same fact here. A gap line keyed on the stamp, or on an
     arrival clock captured only on a seq move, would fire at every peer load, battle loads included (place 2);
   - every gap >= 250 ms is counted (no line); 20 line pairs per link, then "counted only";
   - the 1000 ms is a seed, set in K1 from the existing tapes' inter-arrival times. The guest's 2 s outage line is unchanged.

   This is the host's first stall evidence. Lever `lanegap off` (the lines only; the counters still count).
7. **The host's lines (decision 13).** A new host-only world tick in Update, read-only: it writes only its overlay state, and
   the host's key path is untouched (FilterScriptButtons returns at `!SpectatorField`, NetSyncField.cs:928-932). It never
   writes the guest's pose into the host's coop cells, story or save. Four overlay states, shown only while the host is on
   its own live world map with a following guest linked (the guest's trailer flags b0; a non-following peer gets no lines),
   recomputed every Update (so nothing outlives a scene change): the
   guest following out (place 2 with b5), loading (place 3, or a HANG from place 3), in a scene (place 4 with b6), and lost
   contact (an arrival gap >= 5 s). One log line per guest state edge, its duration on the end line, budget 20 per link.
   The host's field overlay chain is unchanged. Lever `hostlines off`. This is the first host-visible world-map change in co-op.
8. **The world ghost (both roles, the same code).** New `NetSyncWorldGhost.cs`: a static class plus a driver MonoBehaviour.
   - **Body:** `ModelFactory.CreateModel(geo, false, true, WorldSmoothTexture)`, the SetModel world call, so the ghost gets
     the walker's shader and every `_W0_` clip. The model sits under a root ("ff9mk coop world ghost") parented to
     `WMWorld.WorldMapRoot`, so it dies with every world scene. localRotation Euler(0, 0, 180); uniform scale (ratio/64)/256,
     ratio 67 for the walkers and 76 for the Mog. `_FogEnabled` set at mint. No WMActor, no Actor, no `Shadows` entry
     (SmoothFrameUpdater_World would lerp it against our writes).
   - Minted lazily and hidden once IsOnWorldNow and w_blockReady both hold; a failed mint latches with one line. Its own
     WMShadow prefab instance under WorldMapEffectRoot, scaled by the stock 6/36 formula with the live fogAMP.
   - **The strict gate.** w_blockReady reads stale-true on every field after a world visit (ff9.cs:9978; reset only by
     w_blockSystemConstructor, :2575-2578), and off the world map `ff9.world` (Singleton.cs:7-14) and `WorldMapRoot`
     (WMWorld.cs:1790-1809) create a stray WMWorld GameObject or throw. So the mint, the LateUpdate placement, the w_nwpHit
     probe and the shadow all run behind IsOnWorldNow plus w_blockReady; the backstops only hide or destroy cached
     transforms through Unity null checks, never reading `ff9.world` or `Singleton<WMWorld>.Instance`.
   - **Placement:** the pose is kept in canonical coordinates and mapped to the render frame every render frame in the
     driver's LateUpdate, in O(1) through `InitialBlocks[cx, cz].CurrentX/Y`. The wrap moves only ActorList actors
     (WMWorld.cs:1362-1437), and the world tick runs in no defined order against NetSyncClient.Update.
   - **Ground:** the body takes the wire's y. One `w_nwpHit` per new sample, with stock's non-controlled flags set and
     restored, the sky retry and the 0xFEE/0x1BEE/0x2CEE remaps, gives the shadow's height. A mismatch beyond tolerance
     outside water logs once and is published; the body is not dropped.
   - **Animation:** the sender's anim id and frame through s157's frame-follow core (GhostFrameFollow / Ease /
     KeepSourceTimeline), lifted into a shared helper that the field ghost calls unchanged. Never LocoAnim,
     GhostMissFallback or GhostAnimRule: ClassifyLoco reads every W0 body as LocoOther and would hand it a field clip.
   - Backstops: HideNow and reset at `WMScriptDirector.HonoAwake` (beside s165's dot), at the field load, the title and the
     harness release. Easing and stall timers use unscaled real time.
9. **GhostRule (pure, cheapest first, one why_not each):** the lever; a linked session with a following guest (either role;
   on the host, the guest's flags b0) or the selftest bench; my live world (place 4, blocks ready, a walker, not the bee scene, not a diorama, no world
   transition); not an event world; my world in the walk set {9002, 9010, 9011}; the peer's block valid (place 4, caps b0);
   the peer's world (the trailer's wldMapNo) equal to mine and SameBandRule; the peer on foot (mode 0) and not in a scene (b6
   clear); the peer fresh (decision 10). My own freeze never hides a ghost: a frozen guest really stands there. Lever
   `ghost off`.
   - **Scope:** the walk worlds only in rung 2. On the vehicle worlds the frozen guest keeps today's dot alone; rung 3 brings
     the mounted ghost. The rule already reads the peer's live mode, so rung 3 widens one term.
10. **Motion and the stall (recommended; the owner tunes after two-PC).** Ease in canonical space with torus-unwrapped
    deltas (dx into [-768, 768), dz into [-640, 640)), the field ghost's exponential LerpRate 12 (about 83 ms), plus a
    rotation Slerp; no extrapolation. Snap on the first show, on a jump over 64 u, on a world change. Timing by the ms
    stamp, never ticks or TPS (the booster divides the loop target). In a stall: the hold keys on the sender's seq; after
    ~300 ms with no new seq the body switches to its `_STAND` clip (a frame-followed clip would freeze mid-stride); at 5 s
    (the field's GhostGraceMs) it hides with a line. The stamps make a later playout buffer a no-wire-change upgrade.
11. **The dress: none in rung 2 (the owner's call; recommended).** An undressed ghost wears the sender's own world model from
    the trailer: Dagger (309) on 9002, Zidane (310) on 9010/9011. The study's "everything else -> Zidane" would draw a Zidane
    on 9002, where both players walk as Dagger (WORLD02 e14: SetObjectIndex(2), SetModel(309)). Undressed also removes the
    loadability risk: the sender's model is the one my own world already loaded. The cost: two identical bodies (the
    field's "two Zidanes"). A dress map (moogle -> the world Mog 307, Garnet -> 309) is a pure `WorldBodyRule` ready for
    the owner's word; a Mog ghost would read as the save moogle, and the guest's own walker is never self-dressed.
12. **The dot takes the host's live pose (the owner, 2026-11-02, item 14; two-PC finding 2).** Section 0's anchor (64-72)
    stops updating while the host rides, so s165's dot and its facing stood still until the host got off. From round A the
    dot's position and facing come from the trailer (53-80: x/z and the rotation's yaw) whenever the host's caps carry b0
    and its world block is valid (place 4); otherwise from section 0 exactly as s165 (an s165 host, a capless v15 peer, a
    host in a diorama or a load). Everything else stays s165's: DotRule's order and terms (b6, the whole section 0, the
    same [102], the band, freshness on the heartbeat, DotFreshMs 1000), the look and the edge. The source is reported on
    `netsync.world.dot` (`src`: "trailer" or "section0"). Lever `dot section0` restores s165's source exactly. Inference:
    `w_moveActorPtr` is GetControlChar's actor, whose RealPosition moves with a ride (the camera follows it);
    A-DOTRIDE and D-DOTRIDE prove it in game. A host-side dot of the guest stays a later lever. Named limit: in a stall
    the dot blinks out at 1 s while the ghost holds for 5 s.
26. **The pairing pull (round A, second and alone; the owner, 2026-11-02, open item 13; two-PC finding 1).** A following guest
    that pairs on a field while the host stands on the world map follows it out once its pairing autosave has resolved,
    instead of waiting on its field for the host's next stop. Numbered 26 so that no earlier decision's number moves.
    - **The term.** WorldOutStep's term 3 (`not_mirroring`, THE PAIRING-WINDOW LAW) narrows to the one thing the law
      protects. It refuses only while the pairing window is open, nothing has been written in it, and its verdict is busy
      (why `pairing_save`, words "your pairing autosave is still pending"). The follow-out starts on a written autosave, and
      also on a durable decline (not your own place, autosave off, the stock ladder refused), because the window will never
      write. A free-standing guest writes at once, so the start waits an Update or two at most. The build reads
      PairingEvaluate's own state, never a copy. A mirroring guest passes as today (its window closed at the arm), and the
      bench stays exempt. The s165 proof (`world follow selftest`) gains the rows busy, written, durable and mirroring, and a
      mutant that keeps s165's mirroring term (it must fail the written row).
    - **The arm.** For a live guest (never the bench, which never mirrors), `LandWorldOut` arms the mirror after its
      ApplyStory succeeds. It goes through the field load's own arm, lifted into one `ArmMirror(host, where)` that both sites
      call: the ARMED line; `NotePairingAtArm`, whose line names "world map W's landing" instead of `fldMapNo`;
      `_storyMirroring = true`; the kick's budget reset; and `NetSyncSelfDress.ArmFromState`. RestorePassEntrance stays
      field-only. The arm happens at the landing seam, before the visit's first tick, so THE WORLD PAIRING RULE's "during a
      visit it can only fall" (decision 14) still holds.
    - **What else it changes:** the guest's save is refused from the landing on (s165's R4 keys on IsMirroringStory); the
      rejoin stages the host's story as it does for any mirroring guest; and a pulled guest mirrors, so the stall hole does
      not reach it. A guest that paired or Continued while itself on the world map is unchanged: it has no field to follow
      out from, so it stays frozen until the host's next stop and keeps W-REFUSE's PAIR case and WR-PAIR.
    - No wire change and no host change: an s165 host pairs with it. While the autosave is pending, the guest's field keeps
      s144's waiting line. Lever `pairpull old` restores s165's term 3 and skips the arm.

### Round B (s167): the walk

13. **The seam.** WorldFreezeRule and its 32-row table stay byte-identical, and WorldFreezeNow changes only by decision 17's
    session term: they also drive the key mask, RefuseWorldUi and the release refusal (NetSyncField.cs:282-297, 362, 953). Only WorldFreezeHold's frozen path changes:
    `WorldFreezeNow && WalkFreeNow()` returns false, sets `_freezeHeld = false`, and logs one "world walk FREE" or "FROZEN
    (why)" line per edge. That lifts exactly the conjunct at ff9.cs:5544-5548: the directions, L1/R1, the right stick, R2
    and L2 come back with no new code, and the camera follow was never frozen. `WorldFreezeEdge` takes a why, so a
    re-freeze names the walk's reason instead of "the host drives". WalkFreeNow is a live read of engine statics plus the
    caches, never a frame-stamped verdict (the world loop and NetSyncClient.Update have no order, so a stamp could never
    walk). Allocation-free; a fault returns frozen. `freeze.on` stays true while walking; benches judge `walk.free` and x/z.
14. **WalkFreeRule, cheapest first, one why each:**
    1. the lever (`walk off` = s166 exactly);
    2. who: a following client with `IsMirroringStory && !_exitRampPending` (THE WORLD PAIRING RULE: the mirror arms only at
       a field load or a follow-out's landing (decision 26), both before a visit's first tick, so during a visit it can
       only fall), or the selftest bench (`BenchGates && _followHost`, never
       `NetSyncVisitor.FollowHost`, which the forced role still pins false at NetSyncClient.cs:11113) with a `pair
       unmirrored` lever;
    3. SuppressEncounters true (fail closed: a walker without it would roll its own battles on the host's party);
    4. not the bee scene, not an event world, no booted or returning diorama;
    5. my live wldMapNo in {9002, 9010, 9011} (never [102], never fldMapNo); my own [190] == 0,
       `w_moveCHRControl_No == 0` and the walker at index 1 or 2; `w_moveChocoboPtr` null (rung 3's backstop). A bound
       plane pointer is allowed and published: kit 9011's boat binds it at every load;
    6. the latch's cheap terms free (fading, nextMode 1/2, attr 0x3001, booted, the rejoin armed, a world-out pending): the
       C# twin of stock's DisableMove before `Field()` (the arm's next tick runs movement before the attr check);
    7. the host's caps carry b0;
    8. the host on the live world (section 7 b6 and trailer place 4), its trailer wldMapNo equal to mine, SameBandRule;
    9. the host on foot (trailer mode 0) and not in a scene (decision 15);
    10. the host's caps carry b1 (absent: frozen, why "older partner build", one line per process and peer version), then
        both fingerprints ready and equal (decision 21; b1 with digest 0 is "checking", bounded by one timeout line).

    No [181] term: nothing on 02/10/11 ever clears it, so one host Gysahl press would freeze the walk for the visit; the
    trailer's live mode is the riding signal. Kit 9011 counts as lawful: the boat's board read is a bare Confirm (the census
    corrects the recon's Confirm|Cross), still HostOwnedKeys, masked on every control-on read, and decision 19 closes it
    control-off.
15. **Decision 11's breadth (the owner's call).** Recommended: mode != 0 freezes at once with s165's riding words, and the
    host's scene bit freezes too (hiding the host's ghost). The scene bit is the only signal for the kit ferry voyage, which
    keeps [190] at 0 and parks 64-72 at the port. It is broader than decision 11 literally asks: a host's moogle save also
    freezes the guest for its length. The narrower option freezes on the mode only and merely hides the ghost on a scene.
16. **THE STALL HOLD, and a host lost.** A stale host frame keeps the last FRESH frame's inputs (never a verdict) and
    re-evaluates them live against my own state each tick, so a stall never flips the walk; a fresh frame that says
    otherwise freezes. The held inputs drop (frozen until a fresh frame) at every world load and s165 landing, the title, a
    session edge and a host epoch change, so nothing carries "free" into a new world. Through a host loss the guest keeps
    walking its own copy (its own pose and ground, saves refused) for up to SessionGraceMs 40 s; the ghost hides at 5 s with
    the line, and the exit ramp reloads the guest's own save. It never freezes on staleness alone: that would hitch every
    2.3 s stall. Recommended; the owner's call.
17. **The stall hole closed.** One predicate, `WorldSessionHeld` = `_followHost && _role == "client" && _sessionSeenLive &&
    (_sessionState == SessionLive || _sessionState == SessionGrace) && !_exitRampPending`, OR'd on gMode 3 into every
    SpectatorField read the stall lifts: FilterScriptButtons' entry test (`!SpectatorField && !(ee.gMode == 3 &&
    WorldSessionHeld)`, NetSyncField.cs:928), SkipWorldScriptedBattle (:316) and WorldFreezeNow (:130). SpectatorField itself
    is unchanged. SessionLive counts because `_sessionState` is recomputed once per Update (NetSyncClient.cs:4100-4138) while
    IsLiveFollowedSession flips at the StaleMs cliff on any read, and the world tick has no order against Update: SessionLive
    at the stall-onset tick means the peer was alive one Update ago. Its own piece and lever (`stallhold old`), benched
    with T2's blackhole.
18. **The entry refusal (decision 4), the rule the census supports.** At the read, in FilterScriptButtons' gMode-3 frozen
    branch, which still returns the masked keys (every stock write that could latch comes after the masked KEYON; refusing
    at `Field()` would come after the fade). The buzz fires when all of these hold:
    - a control-on read with WorldFreezeNow, `(keys & readMask & Confirm) != 0`, and `KeyTick != _entryRefusedTick`;
    - my world in the walk set (until K1 extends the census to all 13 deployed dispatchers);
    - one reader case:
      - (a) `reader.sid == 1` (entry 1; `sid` is the script entry index, EventEngine.cs:345), Bit 812 and Bit 811 clear,
        place `ee.GetMapVar()[24] != 52`. Entry 1's only Confirm reads are @00204 (the quicksand) and @00251 (the entry
        poll), both inside @00182's `Map[24] in [1, 90)` gate, so the read itself proves the guest stands on a place; or
      - (b) `reader.sid == 0`: a kit cell. Stock entry 0 has no KEYON on any of the three worlds; or
      - (c) on kit 9011, `reader.sid == 15` (the boat), [190] == 0 and Map[24] == 169: the test @00075 makes right after the
        read @00064, with no write between (WORLD11 pdis L2241-2259), so the buzz fires exactly when the press would board; or
      - (d) on kit 9011, `reader.sid == 16` (the ferryman) and Map[24] == 100: the test @01368 after the read @01357
        (L2541-2546), exactly when the press would start its scene.
    - Both kit reads sit inside their on-foot and proximity branches, so neither fires on open ground; the boat's other read
      (@00174, `[190] == 7 && KEYON`, every tick out of range) never buzzes. At the boat plate the press is read by sid 15
      (169) or by sid 1 (place 69), whichever runs after entry 1's tag 11 and before e0's per-tick reset: inference, K1
      confirms. The ids are the deployed kit's entries; K1 re-reads them.

    When it fires: FF9Sfx 102, the timed line, `entry_refused` +1, last_reader, last_place and last_cell, and one log line per
    entrance class per visit. Place 52 stays silent, as in s144.
    - **What K1 must still confirm in game:** KEYON never short-circuits (EBin.cs:1096-1110 calls the filter as its own
      operator; B_ANDAND, :849-865, only pops values already pushed), so one press is read twice by entry 1 (@00204 and
      @00251) and, on a kit cell, by entry 0 and entry 1. Which runs first in a frame is not settled offline. The rows:
      exactly one buzz per held press on a stock entrance, on a kit cell, on the boat plate and beside the ferryman;
      `last_place` in [1, 90) at every sid-1 read; the reader ids as predicted.
    - The same buzz for a FROZEN guest on the walk worlds, behind its own lever (`refuse silent` = s166).
19. **The control-off close (ships in round A, s166: its own piece, first and alone).** On gMode 3, under WorldFreezeNow on
    EVERY world map, a control-OFF read loses HostOwnedKeys when its reader is entry 0 or an entry beyond its stock
    dispatcher's last. **Widened by K1 (2026-11-02):** the six kit cells sit in entry 0 of all nine deployed free-roam
    dispatchers (9000, 9002, 9003, 9005, 9007, 9008, 9009, 9010, 9011), and Path D's 9013 adds three more; s165 lands a
    frozen guest on every one of them, and stock entry 0 reads no key on any of the 13 stock dispatchers in any language. So
    the close keys on the reader, never on the walk set. The stock last entries: 9000:11, 9001:7, 9002:14, 9003:12, 9004:3,
    9005:15, 9006:6, 9007:12, 9008:12, 9009:13, 9010:12, 9011:14, 9012:7, and 9013:14 (its donor WORLD11's); an unknown
    world closes entry 0 only. Only 9011 has reads beyond its stock last (the boat e15, the ferryman e16). Known hole: a kit
    function added INSIDE a stock-range entry, or in a stock-empty slot (9002's e12/e13), would escape the second term;
    none reads a key today. That covers the kit
    cells, the boat and the ferryman. No stock read is touched (stock entry 0 has none), and every stock control-off wait
    passes as before. It closes the s165 hazard (the ~ menu's hold included) and changes no lawful guest behaviour, so it
    is benched first in s166, alone, with OLD measured on s165. A world-paired guest in a stall stays outside it until
    decision 17's term (s167). Lever `kitcell old`.
    - **Departure from the critic** (sid 0 only): the census found the boat's and the ferryman's bare Confirm reads, evaluated
      every tick in range, and their object loops keep running while an open full map holds control off (decision 23).
20. **The DeclineOnce re-arm.** At a world load whose previous scene was a field or the title, never an s145 warm return:
    clear `_lastDeclineWorld` and the field book's world classes (the "main menu (world map)" line, NetSyncField.cs:831).
    Re-arming at every HonoAwake would re-speak every class, R4's save line included, after each world battle. The entry
    refusal has its own class per entrance: the buzz plays on every press, the line once per entrance per visit. Lever
    `decline old`.
21. **The fingerprint (decision 10).** Computed per world at each world load on the main thread (ff9InitStateWorldMap,
    beside s165's seam; the dispatchers come through AssetManager.LoadBytesMerged, an AssetBundle read), its cost logged:
    c0 the language; c1 the current dispatcher's bytes plus [Mod] MergeScripts, the folder order and the world's EventDB and
    WorldScene entries; c2 the WorldMap override tree (path and length, or a CRC once K1 has measured it); c3 the effective
    TransportControls.csv; c4 the environment patch; c5 the weather CSV.
    The combined u32 rides the trailer both ways; the host adds section 11 `[fmt][world][lang][n x (comp, crc)]` between 10
    and 7 (8 stays last), so the guest can name the component. A mismatch keeps the s144 freeze with one line per visit per
    side naming the component; 0 means "checking". The loaded language only: a US/FR pair is refused with that reason (the
    checklist already asks for one language). s165's follow-out is not gated, only logged: gating it would regress a
    two-PC-confirmed path. Levers `fp fake <hex>`, `fp off`, `fp old` (dry: it reports "would walk" and stays frozen).
22. **WorldTPS: report (the owner's call, item 9: the study's rung 2 named a mirror, GUEST-FOLLOW.md:306).** Both values are
    published, with one mismatch line per pair, and the laptop checklist gains "keep WorldTPS equal". Free walk is correct at any speed, because each player walks its own copy. s163 never sets a loop speed
    and SmoothFrameUpdater_World reads the ini, so an apply is an owner-trial lever only: `tps apply` applies the host's
    value at both SetMainLoopSpeed sites (WMScriptDirector.cs:39, SceneDirector.cs:36-40), at a world load only, held for
    the visit.
23. **Decision 8, only if the owner opens the full map (critic's recommendation, staged last).** On 9010/9011, for a
    lawful walker only, `RefuseWorldUi(WorldUiFullMap)` passes while WalkFreeNow. The location pick stays refused (it is
    airship-only anyway) and the menu stays on GUEST-MENU's track. The full-map dot is a per-frame hook in WorldHUD.Update's
    FullMap branch: a clone of `mapPlayerPointer` under `mapContent`, placed by DisplayFullmap's formula with s165's seam
    clamp, minted lazily and latched, hidden at the close and at every world load.
    Opening the map runs SetupBubble -> SetUserControl(false) and closing runs FallbackBubbleToEvent ->
    SetUserControl(true) unconditionally (WorldHUD.cs:254/447, 268/455), so while it is open the rejoin arm and the s145
    boot see control off. Before arming or booting, a co-op close therefore replays WorldHUD's own Select-close branch
    (never ForceCloseFullMap, which leaves control off): a new writer with its own lever (`fullmap old`) and row. The close
    lands in HUDNoMiniMap, hiding the minimap dot until the next Select. The open map's control-off window is why decision
    19 covers the boat and the ferryman.
24. **What changes without code.** s145 boots a walking guest warm at its OWN pose (ctx0 is copied before the Replace), and
    the latch term freezes it at the boot. The rejoin pulls the guest from anywhere, freezing on the arm. s165 lands it on
    lawful ground and it walks from the first dispatch (already block-ready and control-gated): no snap, it walks toward the
    dot. A free-roam world's exit ramp settles at once. The Ragtime Mouse never rolls on a suppressed guest (sysvar 205
    returns 0 under IsNoEncounter, ff9.cs:4244-4247). A guest that declines the host's world battle stays frozen through the
    host's fight (b6 clears during it) and walks again after it (recon W13; item 11). The ~ menu's Release row stays (the
    owner's call, item 10), its hint reworded to "Enter locations alone (until the next field load)", and the texts that say the guest waits are reworded (the ~ menu's co-op hint,
    GUEST_TERMS in coopdoc.py:62-68, 17-coop.md:65, coop.py:38's `--follow-host` help).

### The harness (both rounds)

25. A new sub-verb `worldwalk` (`worldfollow` refuses unknown ops). Every lever is any-role where the duo needs it (THE DUO
    CANNOT PULL A SELFTEST-ROLE LEVER) and is released with the harness. Round A: `kitcell`, `pairpull`, `dot section0|trailer`, `ghost off|sticky` (sticky:
    the ghost ignores the peer's place 2, the D-REJOIN mutant), `place render|act` (the WRAP mutant), `pose off` (tfmt 0: an
    s165-shaped v15 peer), `lanegap`, `hostlines`, `clear`; and the bench host (the selftest role with the ini's FollowHost
    and SuppressEncounters, as s165's G10): `host path <x0> <z0> <x1> <z1> [...] <ups> [loop]`, `hostseq freeze|run`,
    `hostgap <ms>`, `hostplace <n>`, `hoststate <bits>`, `hostmode <n>`, `hostworld <id>`, `hostmodel <id>`, `hosttps <n>`,
    `host off`, each setting its trailer field, built through the real BuildPosPayload into the reader the live branch
    uses. Round B: `walk`, `pair`, `refuse`, `stallhold`, `decline`, `fp`, `tps`, `fullmap`. Keys, all additive:
    `netsync.world.lane` on every role (tx/rx seq, place, state, flags, world, arrival and seq ages, peer caps and why, gaps,
    hangs, gaps_250, world_tps own and peer); `netsync.world.ghost` (want, why_not, shown, model, clip, canonical x/y/z,
    render x/z and their inverse from the same LateUpdate, ground_y, wire_y, snaps, holds, hides, mints, mint_ms, faults);
    `netsync.world.kitcell` {lever, closed, last_sid, last_world} (decision 19's witness: a close counted at the read);
    `netsync.world.line` {text, age, asked}, set where each new world line is decided and exempt from the selftest role's
    OvlOff (SetOverlay forces OvlOff there, NetSyncClient.cs:13056-13057, and the off-field branch asks it every tick,
    :2050-2053), so the solo rows can read the lines; `netsync.wire_peer`; `netsync.host.world.guest` {place, state, line};
    in s167 `netsync.world.walk` and `netsync.world.fp`. Each at its sentinel in the catch literal with a history line
    (THE CATCH LITERAL IS PART OF EVERY KEY ADDITION). Judge `shown` and `why_not` only when both agree (LIVE VERDICT vs LAST
    DRAWN).

**The owner-visible words** (proposed; the owner may change them):

- Both roles, a mismatched engine: "Your partner's co-op version doesn't match yours: update both games."
- Both roles, the ghost hidden after 5 s with no frame: "Lost contact with your partner -- waiting for their game..."
  (not shown while the guest's own session overlay already speaks).
- Host (s166): "Your partner is following you out onto the world map...", "Your partner is loading the world map...",
  "Your partner's game is in a world-map scene."
- Host (s167): "Your partner's world map differs from yours: they'll follow you as before.", "Your partner can't walk
  yet: they'll join you at your next stop." and, for a guest without caps b1, "Your partner's co-op build is older:
  they'll follow you as before."
- Guest, the entry refusal (s167), with the buzz: "Your partner leads the way. You'll join them at their next stop." It
  makes no claim about where the host is (it is true when the host stands on the same entrance) or that the place is an
  entrance (it is true at the boat plate and the ferryman). The critic's "You'll go in with your partner" claims an
  entrance. It is false when the host's next field is not on this install (RedirPassUnregistered) or the host changes
  world without a field (item 5).
- Guest (s167), while walking would be lawful but is refused: riding and scene reuse s165's words; pairing: "You'll walk
  once you've followed your partner into a location." (a battle is not one: the mirror arms only at a field load or a
  follow-out's landing, NetSyncClient.cs:1121-1128 and decision 26; this guest paired while itself on the world map); fingerprint: "Your world map differs from your partner's (<component>): you'll follow them
  as before."; checking: "Checking your world map against your partner's..."; a host without caps b1: "Your partner's
  co-op build is older: you'll follow them as before."
- Guest (s167, only with decision 8 and no co-op close): "Close the map to join your partner."

## The engine pieces

**A1. The pure core (inert; new `Memoria/Netsync/NetSyncWorldWalk.cs`).** The trailer codec (build, forward parse);
`LaneGapStep`; `HostLineRule`; `GhostRule`; `WorldBodyRule`; the torus ease and the canonical-to-render map; `BenchPathPose`;
`KitCellCloseRule` (decision 19); the scene-bit rule. In s167 it adds `WalkFreeRule`, `EntryRefusalRule(keys, readMask, sid,
world, place, mode, bit812, bit811, keyTick, lastTick)`, the fingerprint compare and `DeclineRearmRule`. One proof line
`world walk selftest: OK (N rows, M mutants)`, run in the selftest proof block, which runs only on a field. Mutants: the gap
line keyed on the stamp, the hold keyed on `rs.Valid`, a render-space ease, a naive canonical lerp across the seam, the ghost
on another world by [102], a Field carrying a world id, the dress map defaulting to 310 on 9002, a sid-0-only close (it must
fail the ferryman row), a mint on a stale w_blockReady while on a field, the host's ghost term read from state b0 (it must
fail the released-guest row), the scene bit counting the ~ menu's hold; in s167 a [181] term, the static-ids-only rule (it
must fail "kit 9011, host aboard"), a plane-pointer refusal (it must fail "kit 9011, both on foot"), no pairing term, freeze
on staleness, `NetSyncVisitor.FollowHost` read, a Map[24]-only refusal (it must fail the kit-cell row), buzz on any Confirm
(it must fail the open-ground row), a boat case without the 169 test (it must fail the boat-range row), and no KeyTick
dedupe.

**A0. The control-off close, first and alone (decision 19; `NetSyncField.cs` FilterScriptButtons' control-off branch).**
**A0b. The pairing pull, second and alone (decision 26; `NetSyncWorldFollow.cs` WorldOutStep's term 3 and its proof rows;
`NetSyncClient.cs` the term's facts from PairingEvaluate's state, `ArmMirror` lifted from the field-load arm, and its call in
`LandWorldOut`).**
**A2. Wire v15 (`NetSyncSocket.cs`, `NetSyncRelay.cs`):** the version, the caps word, the trailer through
`INetTransport.SetLocal` and both transports, the relay sentinel's trailer, the forward parse, the arrival tick on
RemoteState, the peer-version counter and line, the own-wire line, the TCP redial dedupe. **A3. The sender, the cache, the
lines (`NetSyncClient.cs`):** the trailer at the one SetLocal site on both roles and in the selftest slot, the receiver cache,
LaneGapStep on both roles, the host-only world tick and its overlay states, `netsync.world.line`, the bench host's trailer. **A4. The ghost (new `NetSyncWorldGhost.cs`; a `WMScriptDirector.cs` backstop beside s165's; s157's
frame-follow core lifted into a shared helper in `NetSyncClient.cs`).**

**B1. The walk (`NetSyncField.cs` WorldFreezeHold's frozen path, `WorldFreezeEdge(why)`; `NetSyncWorldWalk.cs` WalkFreeNow and
the held inputs; `NetSyncClient.cs` accessors).** **B2. The refusal (`NetSyncField.cs` FilterScriptButtons' frozen branch;
a timed overlay state in `NetSyncClient.cs`, cleared at every scene change: the
rejoin, an s145 boot, the ramp, the title; it never stacks with s165's hint).** **B3. The stall hole (`WorldSessionHeld` at
its three reads), the re-arm (`NetSyncField.cs`).** **B4. The fingerprint (`ff9.cs` at s165's seam; `NetSyncClient.cs` BuildStateFrame's section 11).**
**B5. WorldTPS (`NetSyncSpeed.cs` cache; the two SetMainLoopSpeed sites behind the lever).** **B6. Decision 8 (`NetSyncField.cs`
RefuseWorldUi; `WorldHUD.cs` the full-map dot and the co-op close), only if opened.** **B7. The owner surfaces
(`Ff9mkDebugMenu.cs`, coopdoc.py, 17-coop.md, coop.py).**

Every hunk is tagged `[ff9mapkit netsync s166]` or `s167`; each file keeps its own line endings; the new `.cs` files go into
the csproj and into `tools/memoria_stack_replay.py`'s `DEFAULT_FILES`; each round gets its `memoria-patches/` entry and README
status row. Builds go only through `tools/build_memoria.py`'s literal CLI, never while the owner plays.

## The bench

Every row names its OLD prediction (the deployed engine before the round: s165 `e364ca8d` for round A; s166 for round B, which
walks exactly like s165) and a lever (LEVER_PREDICTED on the new DLL), so every row can fail. Every world row is judged after
`world.block_ready` and advancing `world.ticks` (THE PRE-INIT SAMPLE), on frames first published after the edge it judges (A
GAME PUBLISHES NOTHING DURING ITS OWN SYNC LOAD), dropping each harness control flip's own publish (THE ORDER SKEW). Positions:
ICE_TILE (1197.37, -796.7), cell (37, 24), the Ice Cavern (loc 4, Field 300, discovery bit UInt16[92] & 8); FS_LANDING (68,
-444), the 6603 kit cell; BOAT_SPAWN (492, -1130), the boat's 40 u range; the ferryman at (29, -1168), 12 u range.

**K1, read-only, before the build.** The read-site census is done (this doc). Still to do: the type-0 inter-arrival times in
both directions from the existing tapes (the gap threshold, and the real send rate: `swap.slot.sends` counts only the host's
TypeState); the WorldMap override tree's size (c2); the entry-0 census on all 13 deployed dispatchers (widening decisions 18
and 19 beyond the walk worlds); and whether `duo.py` can start the guest's link after its host stands on 9011 (D-PAIR).

**The stand-in.** A `worldwalk` rung in `tools/harness/fakegame.py` (calibrated by `caps_through('worldfollow')`) with
battlewire twins of every A1 rule. It models the ENGINE's facts, never the design's intent: the forced selftest role
(`_followHost` from the ini, `NetSyncVisitor.FollowHost` false); the selftest Update's off-field return, never mirroring,
proofs only on a field; the selftest role drawing no overlay and re-asking OvlOff off-field; B_KEYON read on every evaluation
of its statement; the kit cells (entry 0), the boat (15) and the ferryman (16) reading bare Confirm with no usercontrol term,
the boat's board behind its proximity branch with its 169 test after the read; the kit-cell and boat rows run under both
e0/e1/e15 orders, so an order-dependent rule cannot pass offline; the control-off pass; the ~ menu's control hold; cell
requests not gated on control and skipped under w_naviMode 2; Map[24] reset every pass; SpectatorField dropping in a stall
for a non-mirroring guest; the v14/v15 header rejection (relay silent, TCP disconnect); the peer's seq frozen through its
synchronous loads (world, field and battle) while arrivals continue; a stale w_blockReady on a field after a world visit;
the pairing window's verdicts (busy until free-standing, the durable declines) and its close at a commit or the arm.
Faults: pairpull_early, pairpull_unarmed, ghost_unwrapped, gap_on_stamp, arrival_on_seq, hold_on_valid, ghost_stale_mint, wire_field_world, scene_menu_hold,
walk_unlawful, refuse_leak, refuse_silent, refuse_overfire, kitcell_leak, pairing_free, stall_free, ownmode_free,
decline_stale, fp_ignored.

**Tapes.** v15 makes every v14 tape unreadable: an s166 guest drops every frame and reads "never pairs", a red easy to misread
as a regression. So `coop_peer` accepts 14 and 15 and, in every mode (serve-guest, fake-guest-client, replay-host, the relay
tap header), takes its send version from the first header the game sends or the probed `netsync.wire`, never the constant
(coop_peer.py:120, 160, 168, 602); `replay-host --wire 15` restamps byte 1 (sound only under decision 2's law); the tape header
records the wire from the frames; `where --pose` parses the trailer; and every T2 leg asserts the live header version before
judging. A restamped s165 tape is exactly "a capless v15 host": the OLD calibration. `replay-host --freeze-at T --freeze-for
N` keeps the socket open and re-sends the last host frame byte-identical (the writer's real re-send): the guest-side HANG
and "Lost contact" instrument, which a T2 blackhole cannot be (it trips the guest's 2 s session overlay first). Serve-guest's
`--no-follow` sends flags b0 clear. The new COOP_TAPE_WORLD_ROAM (6603,
walk out, blocks, 3 s at FS_LANDING, three or four on-foot legs with stands, one L1 turn, one leg across the x seam, then
ICE_TILE, 20 s, Confirm into 300) is recorded on the s166 host only with the owner's bridge down and the ini written BEFORE
launch (THE RECORDER DIALS THE OWNER; a separate session is fixing the recorder). Its serve-guest emits a walking v15 guest
record, with `--gap-at` for the host's gap line.

**Round A rows (s166).** Solo on the forced selftest role (Enabled 0 and FollowHost 1 written before launch: THE FORCED-ROLE
PIN), 6603 -> 9011 by s165's follow-out (`worldfollow host`), and onto 9002/9010 with a fabricated [102] 2/10.

| Row | Judge | OLD (s165) | Lever (s166) |
|---|---|---|---|
| A-KITOFF | first and alone: FS_LANDING, `control off`, Confirm: still WorldHUD, never 6603; the same inside the ~ menu's "Disable control" hold | FieldHUD 6603 alone (today's hazard, measured) | `kitcell old` |
| A-FERRYOFF | within 12 u of the ferryman, `control off`, Confirm: Map[50] stays 0, no fade | the ferryman scene plays on the guest's copy | `kitcell old` |
| A-PROOF | the proof line on a field | absent | its mutants |
| T2-A pair | second and alone: `replay-host --from` a tape second where the host stands on 9011 past the debounce, the real guest on its own field (paired there, never mirrored): its pairing autosave line, then the follow-out's start, commit and landing at the tape's pose; `mirroring` true and the ARMED line once, naming the world landing; `savemenu` refused; the tape's rejoin into 300 stages the host's story | waits on its field (`not_mirroring`) until the tape's 300 | `pairpull old` |
| A-WIRE | an unrestamped s165 tape: never pairs, `wire_peer.rejected` rises, one line | pairs (v14) | `--wire 15`: pairs, s165 behaviour, ghost why_not no_record |
| A-TX | own block on 9011 from the selftest slot: place 4, world 9011, x/z within 1 u of `world.x/z`, seq advancing; place 3 in the load | key absent | `pose off`: tfmt 0 |
| A-GHOST | `host path` across the x seam: the ghost within GHOST_TOL of the canonical pose | nothing drawn | `ghost off`: want true, shown false |
| A-WRAP | a fixed point, my walker teleported around it over both seams: the inverse, `WMWorld.GetAbsolutePositionOf(ghostRoot.transform)` (the engine's own RealPosition path, independent of the forward map's InitialBlocks) from the same LateUpdate, equals the point within 0.01 u on every published frame; G36's SetAbsolutePositionOf oracle as a second witness | key absent | `place render`: red exactly at the wraps |
| A-STALL | `hostseq freeze`: hold, `_STAND` by ~300 ms, hidden at 5 s with the line (read on `netsync.world.line`); `hostgap 1500`: one gap line pair, the ghost held | absent | `lanegap off`: counters only |
| A-HANG | `hostseq freeze` after place 3: a HANG worded loading, no gap line | absent | `hostgap` in the same state: a gap line; `hostplace 4` then freeze: worded as a hang |
| A-DOTRIDE | `host path` moving with `hostmode 1`, section 0 parked: the dot (and its facing) on the trailer's pose within 1 px of the ghost's map point, `src` "trailer"; `pose off`: back on section 0 | the dot parked on section 0 | `dot section0` |
| A-RULE | each GhostRule refusal alone: event world, other world (`hostworld 9010` on 9011), riding (`hostmode 1`), scene, place 5 | absent | its bench op |
| A-BODY | 309 on 9002, 310 on 9010/9011: geo, renderers, clips, mint ms; one off-diagonal instrument row (`hostmodel 310` on 9002) for the dress call; 9002's HUD state and a `game_snap` | absent | none |
| A-MENU | the ~ menu open 1 s with "Disable control": b6 stays clear (solo, and the duo on both roles) | key absent | the proof's menu-hold mutant |
| A-FROZEN | `hold up` leaves x/z unmoved, `freeze.on`, edges +1: the round changes no lawful guest behaviour | green | `bench worldfreeze off`: x/z >= WALK_U |
| T2-A old | restamped COOP_TAPE_WORLD_WALK: every s165 row exactly | green on v14 | green |
| T2-A roam | the frozen guest's ghost on the ROAM tape's own trailer pose at the matched second; `--blackhole-at` a leg for 2.3 s: gap lines, hold, ease back; for 6 s: hide at 5 s, then a snap on the re-show (a first show) | no v14 tape | `ghost off`, `lanegap off` |
| T2-A freeze | `replay-host --freeze-at` 2.3 s and 6 s against a real s166 guest: hold, `_STAND`, hide at 5 s, the HANG's wording, the "Lost contact" words | no v14 tape | `lanegap off`, `ghost off` |
| T2-H | serve-guest's walking v15 record into a real s166 host: the host's ghost of the guest, its three lines, its gap line at `--gap-at`; a released guest's record (state b0 clear, flags b0 set): lines and ghost; `--no-follow`: no lines, no ghost | host shows nothing | `hostlines off`, `ghost off` |
| Duo | D-G1 the host walks: the guest's ghost within tolerance of the host's `world.x/z` on the shared clock; D-G2 the host's ghost of the frozen guest within tolerance of the guest's own published `world.x/z`, the landing gap reported (ONE-PC LOAD CONTENTION confounds a landing judgment); D-LINES the host's lines through the follow-out; D-REJOIN both ghosts hidden before the guest's fade; D-BATTLE both re-mint after the warm returns, zero non-loading HANG lines across a start and a return; D-SHARED; the s144/s145 rows under an active trailer; D-PAIR, if K1 finds `duo.py` can start the guest's link late (T2-A pair's judges); D-DOTRIDE (`vehicle 1` on the host on 9011, then it moves: the guest's dot within 8 u of the host's own `world.x/z`) | none | `ghost off` any role; `ghost sticky` for D-REJOIN |

**Round B rows (s167),** the same routes:

| Row | Judge | OLD (s166) | Lever (s167) |
|---|---|---|---|
| W-FREE | `host self`, `hold up`: moves >= WALK_U, `walk.free`, `freeze.on` still true | 0.00 u | `walk off` |
| W-CAM | L1/R1 change `cam_rot` (R2/L2 are raw keys: the owner's) | unchanged | `walk off` |
| W-REFUSE-x | NOB6, OTHER (10 on 9011), RIDE (mode 1), SCENE, OWNMODE (`vehicle 6` on the guest), PAIR (`pair unmirrored`), FP (`fp fake`, named line both sides): each frozen with its why | frozen | each its own op |
| W-STALE | `hostseq freeze` keeps walking; a fresh `nob6` freezes; a world reload drops the held inputs | frozen | `walk off` |
| W-ENTRY | ICE_TILE, Confirm held 30 frames: WorldHUD kept, `entry_refused` +1 once, last_reader 1, last_place 4, the request byte ([29]; [30] on 9002) and the discovery bit unchanged | silent, count 0 | `refuse silent`; positive control: the ~ Release on T2 enters 300 |
| W-KITCELL | FS_LANDING, control on, Confirm: one buzz for the sid-0 and sid-1 reads, never 6603 | silent | `refuse silent` |
| W-KITBOAT | on the boat plate: [190] stays 0, the walker pointer unchanged, one buzz per held press from sid 15 (Map[24] 169) or sid 1 (place 69), whichever reads first (inference, K1) | silent | `refuse silent`; positive control: the ~ Release on T2 boards |
| W-FERRY | within 12 u of the ferryman, control on, Confirm: one buzz (sid 16), Map[50] stays 0 | silent | `refuse silent` |
| W-OPEN | Confirm on 9011's open ground, out of the boat's range: `world.freeze.keys` +1 (the boat's eager @00174 read, which also measures K1's no-short-circuit claim), `entry_refused` 0 | keys +1, 0 buzz | the buzz-on-any mutant (proof); `keys` +1 is the in-game positive control |
| W-DECLINE | 9011 -> 300 -> 9011 re-speaks each line once; a warm battle return does not | once per process | `decline old` |
| W-STALLHOLE | T2 blackhole 2.3 s on a world-paired guest: frozen, `freeze.edges` unmoved across the blackhole; a Confirm at ICE_TILE inside it: `world.freeze.keys` +1, never 300; on place 52, `world.freeze.battles` +1, no local battle | free for the stall | `stallhold old` |
| W-TPS | `hosttps 20` against my 28: both values published, one mismatch line | none | `tps apply` (owner trial): my speed changes at the next world load |
| W-MAP | only with decision 8: open, the full-map dot, the co-op close before an arm | refused | `fullmap old` |
| T2-B | ROAM tape: WR-FREE, WR-REFUSE, WR-REJOIN-FAR, WR-PAIR (paired on the world map: frozen "pairing") | frozen | `walk off` |
| Duo | D-W1/2/3 ghosts both ways while walking; D-REFUSE; D-REJOIN-FAR; D-BATTLE (the guest boots and returns at its OWN pose); D-RIDE (`vehicle 1` on the host: judge the guest's verdict, never the dot); D-REJOIN-WAIT (the host walks back out while the rejoin waited: the ghost snaps, no follow-out); D-SHARED | frozen | `walk off` any role |

**Order, one change per test by lever.** Round A: K1; A-KITOFF and A-FERRYOFF first and alone (they close a live hazard); T2-A pair
second and alone (OLD measured on the A0 build, the tape restamped where the wire needs it); the proof; A-WIRE and the restamp; A-TX; the ghost rows with `lanegap off` and `hostlines off`; the stall rows; T2; the duo; the
regression set; the owner's two-PC look. Round B: the walk with `refuse silent`; the refusal; pairing, stall hole, decline,
fingerprint, TPS; decision 8 last; T2; the duo; the regression set; two-PC.

**Regression.** Round A changes no lawful guest behaviour, so the s144/s145/s165 legs run as they are on restamped tapes,
which exercise round A only dormant (capless): the duo owns those rows under an active trailer. Every coop_peer-based scenario
joins round A's set (coop_action_fallback/hold/replay, coop_cut_hold, coop_dress_wire, coop_self_dress, coop_climb_anim_peer,
coop_host_code, coop_ramp_title, coop_world_battle, beside s144/s145/s165's). The trailer rides type 0 on fields too, so the
s157 "39 B" judges (`_climb_anim_judges.py:305`, `coop_climb_anim_peer.py`) are re-keyed to ">= 39 B carrying the s157 bytes";
and `test_harness_netsync.py:1174`'s `== 14` pin, `test_coop_peer.py`'s v14 vectors and fakegame's `wire` (:6152) move to 15
in the same commit as the patch, or the nightly gate goes red. In round B
every leg that tests a frozen guest sends `worldwalk walk off` when the probe shows `netsync.world.walk`; the rows that move
meaning (S165-FROZEN, S165-WK-FROZEN, D-DOT's "own pose unmoved", WT-FROZEN, D2, `freeze.edges`, SKIPS_MIN) are re-keyed by
stage, never weakened, and TWO-PC-CHECKS-S165's red tell "the guest can walk" is rewritten. The domain tests (GATE-PROFILE's
files, the co-op bench files, the new `ff9mapkit/tests/test_coop_world_walk.py`) run in the MAIN repo or with the templates
extracted; no bench while the owner plays, never under a running test suite.

## Known limits (s166-s167)

- **Install and wire:** both PCs must update together, and every v14 tape needs the restamp. The same world content is required;
  s167's fingerprint names a difference but cannot heal it.
- **Bodies:** two identical bodies, with no dress or tint, until the owner says so. The ghost lags by the ease (~83 ms) plus
  the link, with no playout buffer. In a stall the dot blinks out at 1 s while the ghost holds 5 s.
- **Scope:** ghosts and walking only on 9002, 9010 and 9011, the three free-roam states with no vehicle object at all (all
  disc 1, story counter below 5990). The other six free-roam states (9000, 9003, 9005, 9007, 9008, 9009) are walkable too,
  but their dispatchers hold Choco or a ship: there the guest keeps s165's freeze and the dot until rung 3 (the event worlds
  9001, 9004, 9006 and 9012 have no free roam). Walking those six on foot only, frozen whenever the host rides, was
  offered; the owner kept the three for now (2026-11-02), to revisit once the six states' purposes are familiar.
- **9002 is under-benched:** no real route (only the fabricated landing), the minimap unproven in game (WORLD02 never arms it,
  yet WorldHUD.Show keys on the mirrored [100]), and both bodies Dagger.
- **s165's own limits stay:** a 9013 host reads as 9011 to the follow-out (the walk and the ghost compare the trailer's
  wldMapNo instead), and a host Gysahl press on 10/11 leaves [181] set, so later follow-outs wait. Curing either is its own
  lever'd WorldOutStep change.
- **The host off a field path:** a host that changes world without a field, or walks back out while the guest's rejoin waited,
  leaves the guest on its world (frozen as "other world", or with the pre-field story) until the host's next stop.
- **Kit reads:** on a kit cell one press is read by both entry 0 and entry 1, and at the boat plate by sid 15 or sid 1; their
  order in a frame is unsettled offline (K1 confirms in game).
- **The stall in round A:** decision 19's close runs under WorldFreezeNow, so a world-paired guest in a stall stays outside
  it until decision 17 (s167). A guest pulled out by decision 26 mirrors, so it is not world-paired in this sense.
- **Walking:** a walker keeps walking through a host loss for up to 40 s. Its own continent title can leave its [0] 10 above
  the host's (harmless, same band). WorldTPS mismatches change relative speed (reported only). If decision 8 opens the map,
  closing it hides the minimap dot until the next Select.

## The owner's calls

All DECIDED (2026-11-02): the owner took every recommendation below ("Yes, use them"), with item 2, 12 and 13 as recorded
in place; item 14 is decision 12 as revised.

1. The two-round split: the wire and the ghosts first (s166, with decision 19's control-off close first and alone), walking
   one round later (s167). Recommended.
2. The walk worlds: 9002, 9010 and kit 9011, its boat and ferryman refused with the buzz and closed control-off.
   DECIDED (2026-11-02): the three for now; the six vehicle states on foot are not in rung 2.
3. The ghost body: undressed for now (two identical figures); a dress map or a tint after the two-PC look. Recommended.
4. Decision 8: open the full map on 9010/9011 for a walking guest, with the dot and a co-op close, last in s167. Recommended.
5. The refusal words: "Your partner leads the way. You'll join them at their next stop." with the stock buzz. They replace
   owner decision 4's "a line saying its partner isn't there" (false when the host stands on the same entrance). They are
   false when the host's next field is not on this install or the host changes world without a field.
6. Kit vehicles and scenes: freeze on the host riding AND on any host scene (or riding only). Recommended: both.
7. Stalls and a host loss: keep walking; the ghost stands at ~300 ms and hides at 5 s. Recommended.
8. The fingerprint: the six components, the loaded language only, s165's follow-out not gated. Recommended.
9. WorldTPS: report-only with "keep WorldTPS equal" on the checklist (this install runs 28, the default is 20), or the
   study's rung-2 mirror. Recommended: report.
10. The ~ menu's Release row on the walk worlds: kept, its hint reworded to "Enter locations alone (until the next field
    load)". Recommended.
11. "Decline" is s145's word for the guest's game being unable to boot the host's world battle, never the player's choice:
    the guest aboard a vehicle, standing on the quicksand cell (52), mid-fade or loading, with a window, the ~ menu or the
    full map open, or with control off. Such a guest sits the fight out on the world map and, in s167, stays frozen until the
    host is back on the world map (b6 clears during the host's battle), then walks again. Recommended: accept.
12. The schedule: run the s165 two-PC session on s165 first (with the Confirm warning), or ship s166 to both machines and
    run s165's checks on it; every engine build auto-deploys over the shared install. DONE (2026-11-02): the session ran on
    s165 first; results in `TWO-PC-CHECKS-S165.md`.
13. **Pairing on the world map** (two-PC finding 1). The owner paired the guest while the host stood on the world map and
    expected it to be pulled out; it waited on its field, because it was not mirroring yet. The proposal: a guest that pairs
    while the host stands on the world map follows it out once its pairing autosave has resolved (WorldOutStep's
    not-mirroring term becomes "the pairing autosave has not resolved"), and `LandWorldOut` arms the mirror for a live guest
    (it already applies the host's whole story; `NotePairingAtArm` closes the window there). This reverses GUEST-FOLLOW's
    rung-2 "world pairing rule" for a guest paired on a field. DECIDED (2026-11-02): folded into s166 rather than a round of
    its own (s165b), as decision 26, round A's second piece, alone.
14. **The dot while the host rides** (two-PC finding 2). Section 0's pose freezes while the host rides, so the dot and its
    facing stood still until the host got off. The proposal revises decision 12: the dot takes the trailer's live pose and
    rotation whenever the host's caps carry b0, and section 0 otherwise (an s165 host). On the vehicle worlds, where the
    frozen guest has only the dot, it then tracks a riding host, and D-RIDE judges the dot moving. Recommended: in round A,
    right after the trailer. DECIDED: decision 12 (revised).

## What the s165 two-PC check answered (2026-11-02; `TWO-PC-CHECKS-S165.md` "Results")

- **The sequencing:** the session ran on s165 on both machines, before any s166 build (item 12).
- **The dot's look:** still open. The owner saw the dot track the host on foot, but has not answered on the tint, the size
  or the edge. The dot draws ABOVE the arrow at 80% (no free depth slot under it), not under it as the checklist said. A
  riding host froze it (item 14).
- **The link's stalls:** one 203 ms outage in about 8 minutes, recovered inside the grace. That is too little to retune the
  1000 ms gap line, the 300 ms stand or the 5 s hide, so they stand as designed.
- **The landing over a real link:** 0 u with the host standing still, and 18.3 u behind a walking host (the guest's world
  loaded 857 ms after the start). The ghost snaps on its first show (decision 10), so no extra snap after the landing.
- **The host's lines:** the two s165 lines and nothing else visible, which is the baseline for round A.
- **New: the two machines' world maps differ.** The laptop has no `FF9CustomMap-world` (nor `-schema` or `-msgs`). The s166
  package carries `FF9CustomMap-world`, and laptop step 0 compares the mods line in both logs. In s167, the fingerprint
  (decision 21, c2) would refuse the walk on mismatched world content.
