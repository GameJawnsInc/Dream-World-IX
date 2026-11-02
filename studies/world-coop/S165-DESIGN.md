# World-map co-op: the guest follows the host out (s165)

Today, when the host walks out of a field onto the world map, a following guest in that field stays where it is (s144
decision 5) until the host's next stop. s165 is rung 1 of `GUEST-FOLLOW.md`'s two-body order:

- **R1** the guest follows the host out, lands at the host's live spot, and stays frozen there (the s144 freeze) until the
  s144 rejoin;
- **R2** a dot on the guest's minimap shows where the host is, from section 0 (no wire change);
- **R3** the 9012 strand is fixed;
- **R4** the save guard moves to its call site.

The host's side changes only by log lines. The wire stays v14 (the owner put the world follow on v15 for later rungs; rung 1
takes no v15 dependency), and the harness protocol stays 5.

The recon (4 read-only lanes, an Opus verifier per lane, and a critic, with file:line evidence at the s164 clone's lines) is in
the session scratchpad as `wf/recon1.raw`, digested to `wf/digest1_*.md`. The sites below are its settled answers. The build
re-finds each one in the live clone.

## What happens today (s164)

- The host's `WMAPJUMP` emits no intent (only `MAPJUMP` calls `EmitFieldIntentIfHost`). `FollowHostTick` returns while the
  host's lane reads field 0, so nothing moves the guest. The field overlay says "Your partner is on the world map. You'll
  rejoin them at their next stop."
- A guest that walks out on its own lands where its own copy of the exit puts it (the exit's arrival constant), with its
  last field-load mirror of the story. That is not where the host now stands.
- No C# code has ever committed a field-to-world change. Every existing writer goes world to field (the rejoin, `WorldWarp`),
  world to world (`ArmWorldReload`) or field to field (the follow, the kick).
- **The 9012 strand.** A following guest that reaches 9012 (the chocobo's treasure dive) is frozen with Menu masked, and the
  rejoin refuses every event world, so it stays there until the exit ramp or the ~ Release lever. The route today is the talk
  relay of 1953's Region 7 press (traced, not seen in game).
- **The save hole.** `SaveLoadUI` refuses only `IsMirroringStory || NetSyncDiorama.Booted`. A guest that has paired but not
  yet mirrored, and the selftest bench, can save by hand (Alt+F5 on the world map; the MENU opcode already refuses under
  `SpectatorField`).

## The decisions (s165)

1. **The trigger.** Any field where a following, mirroring guest stands, when the host's frames say the host is on the world
   map (section 7 b6 `HfWorld`), on foot, on a free-roam world this install has. Not only the field the host left: the
   landing takes the host's pose wherever the guest starts. A late-paired guest that is not yet mirroring keeps s144
   decision 5 (THE PAIRING-WINDOW LAW: its pairing autosave may still be pending, and the move would shut the window).
2. **The world id** is `9000 + section0[102]`, read from the same frame as b6. Never `fldMapNo`, the guest's own `wldMapNo`,
   or the lane's Field. The checks: 102 in 0..12; not an event world (the static `ff9.eventWorldMaps` set, never
   `IsEventWorldMap`, which reads the guest's own last world); registered in both `FF9DBAll.EventDB` and
   `EventEngineUtils.eventIDToMESID` (the field shutdown indexes the second unguarded); unchanged across the debounce.
   **Known limit:** Path D's 9013 writes `[102] = 11`, like 9011. It is a dev bench world today (its entry field 30950 is not
   registered). The cure is the host's `wldMapNo` in v15's world section, or rung 2's fingerprint.
3. **The start gate** (a pure `WorldOutStep`, cheapest first, one reason per refusal, logged once per host world visit and
   reason, published as `why`):
   1. the lever is off;
   2. a following client in a live followed session with no exit ramp pending (or the selftest role with the bench on);
   3. already mirroring;
   4. no field follow, kick, world-out or world rejoin in flight;
   5. on a field, on FieldHUD, no field transition requested, the disc-change bit clear;
   6. my control on, no ETb line, no backlog;
   7. no ATE press waiting, no guest climb, no diorama booted;
   8. a host frame (the frame `_dlg.View` was parsed from) whose section 7 parses with b6 and b1 set, and no section 4 whose
      landed bit is clear (that intent belongs to the rejoin);
   9. a whole section 0 (2048 B) that passes decision 2;
   10. the host's `[190] == 0` and `[181] == 0` (on foot, no Choco call: see decision 5);
   11. the hold lever is off;
   12. **THE LIVE DEBOUNCE** (decision 4).

   Every refusal sits here. Once the guest has faded with control off, nothing may decline without writing a scene change
   (s42: the only recovery from a fade is a load).
4. **THE LIVE DEBOUNCE.** 1200 ms (a seed, the field follow's `FollowStableMs`) of host-ALIVE time: it counts only while the
   section-7 heartbeat moved within the last 400 ms, and it restarts on any b6 fall or any change of 102. b6 rises before the
   host's own synchronous all-block load (~4.4 s on this PC), which freezes the host's heartbeat while its writer thread keeps
   re-sending the last frame, so a hung host's re-sends never count. **Corrected by the first duos (in game):** the debounce does
   NOT reliably straddle that load -- the host's heartbeat ran 1.24 s past b6 before its load began on one run of two, so the
   1200 ms ended first and the guest committed inside the host's load (landing 0.3 s before the host's walk out returned; the
   other run waited the load out and landed 2.4 s after). Both landed at the same pose, height included ((17408, 819, -113664)),
   so the early commit costs only ONE-PC LOAD CONTENTION on the duo; the bench reports the heartbeat witness and never judges it.
   What the debounce does guarantee: a host that keeps b6 for 1200 ms of LIVE time (a bounce or a hung host never starts one).
5. **On foot only.** While the host rides (Choco, the boat, an airship, or a dock exit that lands it aboard), the guest waits
   on its field with a line, and s144's rejoin takes it into the host's next field. If the host mounts during the guest's
   load, the guest still lands on foot at the start's pose: the host's own walker stood there, so it is lawful ground. Never
   aboard in rung 1 (that is rung 4's pulled-aboard load). `[181]` is the Choco call (Gysahl Greens); applied on the guest it
   makes the guest's own Choco run in, so the start waits while it is set and the landing writes it to 0. The kit's Southern
   Ring ferry keeps 190 at 0 and freezes 64-72 at the port, so a guest that follows out during a voyage lands at the port,
   frozen (decision 11: kit vehicles not yet).
6. **Event worlds** (9001, 9004, 9006, 9012) are never followed into; s144 decision 5 stands there, with a line. R3 handles a
   guest that reached 9012 another way.
7. **The commit** reuses the field follow's fade (`NetSyncFollowFade`, s164's 12-tick fade, its due rules and the 0.9 s
   timer), but has its own pending slot and record (`_worldOutPending`, its timer, the start pin, `_worldOutCommittedTo`),
   never `_followWarpPending`: eight of that field's readers treat it as a field id. One internal `FollowFadeInFlight`
   predicate (either pending is set) replaces `_followWarpPending >= 0` at the seven sites that only mean "a fade is in
   flight" (the exit ramp's `safeToLoad`, the diorama boot, the talk start, ...); the eight field-id readers stay as they are.
   - At the start: `PairingEvaluate("world follow-out", false, true)`, the start pin kept, `SetUserControl(false)`, the fade.
   - At the write: `NoteMoveCommitted`, the record, a seed of the start pin's pose (2-3 by the 35 rule, 64-72, `190 = 0`),
     then stock's `WMAPJUMP` levers: `SetNextMap(w)`, `nextMode = 3`, `attr |= 2`, and `ClearIntentCache`. The commit guard
     (`FollowCommitStep`) stays: never write into another scene change.
   - No swap-record edge (`NoteFollow`, `NoteCommit`, `NoteDrop`): the record stays field-only. It gets its own stamped
     start, commit and landing lines and counters.
   - It runs beside `ServiceFollowWarp`, before the enabled gate (a fade in flight always finishes, across a redial too). The
     title drop clears it. A host epoch change (a relaunch, a Continue) resets the debounce and the pin.
8. **Supersede.** A field follow (the host's MAPJUMP intent, or the serial candidate) that arrives before the commit wins:
   it clears the world-out's fade ("superseded") and takes the darkening slot. After the commit, today's deferral stands:
   the guest rejoins from the world map.
9. **The landing.** A new `ApplyStoryBeforeWorldEvents(MapNo)` in `ff9InitStateWorldMap`, right after s145's
   `BeforeWorldEvents` and before `StartEvents`, runs only for a load whose record names this world (or the bench). It applies
   the host's whole section 0 and party (`NetSyncState.ApplyStory`) from the latest frame while it still carries b6 and the
   same 102, else from the start pin. If that frame's `[190] != 0`, the on-foot substitution: 64-72 from the pin, `190 = 0`.
   Then `[2..3] = 35` when it is 0 or a world sentinel 9995-9999, and `[181] = 0`.
   - 35 is the kit's `POSITION_PRESET_KEY`. Across the 13 dispatchers, `Int16[2]` is only ever tested `== 0` (the anchor
     default and the vehicle-record resets) or `== 59/60/61` behind the one-shot bits 841-843; nothing compares it with 35.
     So 35 keeps the live pose and the parked vehicle records, and triggers nothing. (A 0 would reset the walker to the
     dispatcher default and the parked Choco and boat to theirs.)
   - The latest post-Init frame carries bits 841-843 and `[101]` bit 0 already settled by the host, so no one-shot window
     replays and the guest fades in from black.
   - None of the field-landing hooks run (the s164 PIN, `NoteFieldLanding`, `OnFieldLoad`, the dialog-lock re-arm, the pass
     entrance). The world constructor's own fade resets the follow fade, so nothing is left black.
   - A FIELD landing while the record is still set is a lost commit: one line, the record cleared, the debounce restarted.
10. **No snap after the blocks load.** The guest stands where the host stood at the guest's seam, a few seconds stale; the
    dot shows where the host is now. The drift is published. A snap (`WorldTeleportTo`) is a rung-2 candidate, once the
    walker is free.
11. **The guest's own exit during the fade.** When the copy's own `WMAPJUMP` wins inside the world-out's fade and names the
    same world, the record is kept, so the seam applies the host's frame. Otherwise s144's own-exit landing is unchanged.
12. **The dot (R2), minimap only.**
    - A clone of the stock player pointer (`NGUITools.AddChild(MiniMapPanel, miniMapPlayerPointer)`), the panel's last child:
      it hides with the minimap and moves with its corner. Colliders and tweens removed, `SetAnchor(null)`, drawn under the
      guest's own arrow, a warm co-op tint, 1.25 times the donor's own scale. A failed mint latches.
    - Placed through `ff9.w_naviGetPos` on the guest's own map image, rotated by the host's facing
      (`Euler(0, 0, -(b72 * 360 / 256) - 90)`).
    - Shown only while: a following guest (or the bench); the live world scene with its blocks loaded; not an event world,
      the bee scene or a world diorama; no world transition in flight; a controlled walker; a fresh host (the heartbeat moved
      within 1000 ms: the keepalive re-sends make a hung host look fresh); b6; a section 0 whose pose lies inside the torus;
      the host's `[102]` equal to the guest's own live `[102]`; the same map band (story counter 5990 and up on both, or
      below on both). Each refusal is a published `why_not`.
    - On the disc-1 Mist window (map image 0), a host outside the window pins to the window's edge on the side where it
      really is (`x + 1536` when that lands nearer: the bench landing at x = 68 is just east of the right edge), dimmed.
    - The hook is the FIRST statement of `WorldHUD.DisplayMinimap` (stock dereferences the walker unguarded there, so a hook
      after it would freeze the dot on a throw). It never throws, and it reads only the cache the one reader fills.
    - **The full-map dot is not in rung 1.** The full map stays refused for a frozen guest (s144), and decision 8 (the full
      map for a free walker) is the owner's open item. The full-map dot comes with free walk.
    - **The minimap off.** A New Game lands with the minimap off (the host's mirrored `[100] = 0`). It is never forced on (that
      fights the s69 voyage bracket on `[100]`). Instead a line shows while the dot is wanted and the minimap is off.
13. **R3, the 9012 strand.** One call-site change in `WorldArmWhy`: 9012 is an event world that waits on the player (its
    Main_Init masks only the d-pad and keeps control on), so the rejoin may arm from it. The guest leaves 9012 on the host's
    dive intent. The arm's pure refusal table and its census are unchanged. The lever `r3 old` restores s164's refusal.
    Rejected: passing the guest's Menu (it would dive twice, into its own real bag), a world key relay (new wire semantics),
    bouncing `WMAPJUMP` (forbidden by decision 1).
14. **R4, the save guard at its call site.** `SaveLoadUI` refuses a save, at both Save sites (a new file and an overwrite),
    when `ManualSaveRefused(L, M, B, D, S)`: a live followed session, mirroring, the selftest bench (L, M and B are
    `SpectatorField`), a booted diorama, or `SuppressEncounters` (it holds through the ~2.3 s link stall, while L flickers
    false). The buzz (102), one line, a counter. The s154 pairing autosave (`Serializer.Autosave`) is untouched; Load stays on
    s38's gate; a host is never refused. The lever `saveguard old` is DRY: it reports "would save" and still refuses, so the
    bench never writes a real slot.
15. **The host's own lines** (no wire byte): "host: world-map exit from field F to world W" at its own `WMAPJUMP`, and once
    per world load "host: on world map W (b6) at world frame N, blocks ready yes/no".
16. **No new ini knobs.** One new harness sub-verb, `netsync worldfollow <op>`: on s164 an unknown netsync sub-verb fails
    closed, whereas an unknown `bench` op turns the field-gate bench on.
    - client or selftest: `off|on`, `hold|release` (the duo and T2 live-pose instrument), `dot off|on`, `r3 old|act`,
      `saveguard old|act`;
    - selftest with the bench on: `host <x> <z> [idx] [mode] [entrance] [veg]`, `host self`, `host nob6`, `host stale`,
      `host off` (a fabricated host frame through the real encoders; refused unless FollowHost is set and
      `SuppressEncounters` reads true, so a bench world landing never autosaves a fabricated pose);
    - any role: `clear`; plus a `savemenu` verb (the Alt+F5 adapter).

    Every lever is released with the harness on every role.
17. **The DeclineOnce world book re-arm stays in rung 2.** R1's own lines latch per host b6 visit; every counter is
    monotonic, and benches read deltas.
18. **Not in rung 1:** free walk, ghosts, the world pose on type-0, the split key mask, the full-map dot, the world-to-world
    follow (a host that changes world without a field leaves the frozen guest on its world, the dot hides with "other world",
    and the guest catches up at the host's next field), pulled aboard, and the 9013 fix.

**The owner-visible words** (proposed; the owner may change them):

- leaving: "Following your partner out onto the world map..."
- the host rides: "Your partner is riding. You'll rejoin them at their next stop."
- an event world: "Your partner is in a world-map scene. You'll rejoin them at their next stop."
- a world not on this install: "Your partner's world map isn't on this install."
- the minimap off: "Your partner is on the world map: press Select for the minimap."
- a refused save: the stock buzz, and the log line "save refused while following your partner".

## The engine pieces

**E1. The pure core (inert, new `Memoria/Netsync/NetSyncWorldFollow.cs`).** `HostWorldPoseOf(payload)` (section 7 format 1,
b6 `body[5] & 0x40`, b1 `& 0x02`, the heartbeat `body[3..4]`; section 0 read in place, no copy: 0-3, 64-72, 100-102, 181,
190; section 4 present and landed, a 3-byte body reading as landed); `WorldIdRule`; `WorldOutStep`; `LiveDebounceStep`;
`WorldOutFrameRule` (latest, pin or seed, and the on-foot substitution); `EntranceRule` (0 or 9995-9999 to 35);
`EventWorldWaitsOnPlayer` (9012); `ManualSaveRefused`; `DotRule`; the seam-aware map clamp. The proof line
`world follow selftest: OK (N rows, M mutants)`. Its mutants: a world taken from `fldMapNo`; `IsEventWorldMap` for the host's
world; the latest frame without the 102/b6 match; no on-foot substitution; entrance 0 kept; a wall-clock debounce; 181 not
refused; a pose-agreement gate (it would refuse a walking host forever); R4 without the S term; R3 lifting all four event
worlds; the dot reading socket state. No call sites.

**E2. The one reader, the cache, and the bench host (`NetSyncClient.cs`).** Once per new payload, in `ObserveHostDialog`
right after `SwapNoteHostFrame`, from that same byte array: parse `HostWorldPoseOf` into a cache (the last valid b6 pose, the
heartbeat and the tick it last changed, the b6 run, the 102 run, the debounce). A null frame invalidates it; a host epoch
change resets it. Internal static read-only accessors serve the dot and the seam (`NetSyncClient` is sealed and its members
private). The selftest bench host: `worldfollow host ...` makes `BenchHostTick` build a frame with section 0 from
`SnapshotStory()` plus the patched bytes, b6 set, b3 clear, the heartbeat bumped per build (`stale` freezes it, `nob6` clears
b6).

**E3. The follow-out (`NetSyncClient.cs`, one hunk in `ff9.cs`).** `WorldOutTick` in the client Update right after
`FollowHostTick`, and in the selftest branch before its `!inScope` return; `ServiceWorldOut` beside `ServiceFollowWarp`
before the enabled gate; its own drop path (`CommitDropWorld` with the same world keeps the record, otherwise cancels;
`CommitDropInFlight` cancels with a world-worded line; no `NoteDrop`, no re-arm); the supersede in `StartFollowWarp`; the
lost-commit check in `NoteFieldLanding`; world wording in `NoteGuestWorldJump`; the title drop; `FollowFadeInFlight` at the
seven gate sites; the new field overlay states; `ApplyStoryBeforeWorldEvents` at the world seam.

**E4. The dot (new `Memoria/Netsync/NetSyncWorldDot.cs`, one hunk in `WorldHUD.cs`, a hide in `WMScriptDirector.cs`).** The
hook at the top of `DisplayMinimap`; the lazy mint with a census of the donor (sprite, atlas, depth, the cone's and the
image's depth, colour, size, scale, colliders, panel clipping); placement; the harness fields (including the screen point
through the UI camera); `HideNow` backstops at the field-load hook, at `WMScriptDirector.HonoAwake`, and on the selftest
release. The minimap-off line.

**E5. R3 and R4 (`NetSyncClient.cs` `WorldArmWhy`; `SaveLoadUI.cs` at its guard and before the overwrite Save;
`NetSyncField.cs` `ManualSaveRefusedNow`).**

**E6. The host's lines (`EventEngine.DoEventCode.cs` at `WMAPJUMP`, `NetSyncClient.cs`).** Host role only; inert on a guest
and on vanilla.

**H. The harness (additive under protocol 5).**
- `world.block_ready` (`ff9.w_blockReady`) behind the world block's live gate;
- `netsync.world.out` {lever, hold, state idle|waiting|fading|committed|landed, why, world, from, debounce_ms, starts,
  commits, lands, lost, superseded, refused, substituted, entrance_fix, veg_zeroed, last {world, frame latest|pin|seed, x, z,
  start_to_land_ms, drift_u}};
- `netsync.world.host` {valid, why, x, y, z, yaw, mode, idx, story, entrance, veg, hb, hb_age_ms, b6, b1, intent_unlanded,
  payload_age_ms};
- `netsync.world.dot` {lever, want, why_not, shown, minimap, hud, navi_mode, mapno, host_x, host_z, host_face, host_idx,
  own_idx, own_world, host_sc, sx, sy, edge, px, py, rot, own_px, own_py, screen_x, screen_y, age_ms, hb_age_ms, frames,
  shows, hides, faults, last_fault, census};
- `netsync.saveguard` {refused, would_save, lever, last_why};
- `netsync.host.world` {b6, rise_frame, rise_block_ready, wmapjumps};
- the same keys at their sentinels in the netsync-off catch literal, with a history comment line;
- the kit side: a fakegame `worldfollow` rung, and tests pinning the call sites, the literal and the lever usage.

Every hunk is tagged `[ff9mapkit netsync s165]`, and each file keeps its own line endings. The two new `.cs` files go into the
csproj. `SaveLoadUI.cs` joins `tools/memoria_stack_replay.py`'s `DEFAULT_FILES`, with the two new files.

## The bench

A new scenario, `studies/test-harness/scenarios/coop_world_follow.py`, on coop_world_wait's route (6603 FARSHORE, then 9011
at the New-Game scenario). Every world landing is judged only after `world.block_ready` and advancing `world.ticks` (THE
PRE-INIT SAMPLE). A route that leaves the host at its landing cannot tell the live pose from the exit pose (both land at
FS_LANDING (68, -444)), so every live-pose row makes the host stand at ICE_TILE (1197.37, -796.7), about 1180 u away.

- **K1, the instruments, first, on the deployed s164.** A `COOP_TAPE_WORLD_WALK` tape recorded on the live s164 host (rung 1
  changes no host byte, so it is a valid oracle): the host waits on 6603, walks out to 9011, waits for its blocks, stands
  about 3 s at FS_LANDING, teleports to ICE_TILE, stands 60 s or more, then Confirms into 300. A pure `coop_peer where --pose`
  decoder per frame (x = s24(64)/256, z = s24(69)/256, yaw = b72 * 360 / 256, [102], [190], [2..3], [181], the heartbeat,
  b6/b1, the time, a torus distance). Then CAL-T2 and the duo's D1 on s164: OLD_PREDICTED = the guest stays on FieldHUD
  6603, the new keys are absent, nothing new is sent.
- **Solo, the selftest role** (FollowHost, bench on, `worldfollow host`): the proof line; leave 6603, block_ready, the pose,
  frozen, on foot; the substitution; entrance 0 to 35 (lands at the fabricated pose, not WORLD11's default); the event worlds
  refused; world 13 refused; the host rides and waits; the Choco call waits; a supersede by an injected field intent; an ETb
  line waits; the exit ramp inside the fade (exactly one load); the lever. The dot rows at ICE_TILE (`host self` lands on my
  own arrow), an edge row at FS_LANDING, the stale / nob6 / other-world rows, the dot lever. The R3 table; the R4 dry rows
  (the Continue slot's mtime never changes).
- **T2 against the walk tape:** leave and land; with `hold` / `release`, land within tolerance of the tape's own section-0
  pose at the guest's seam stamp and at least 1000 u from FS_LANDING; frozen; the rejoin into 300; the dot tracking
  `where --pose`.
- **The duo:** D-FO1 (the commit comes after the host's heartbeat resumed; the landing gap reported as noise, the s164 law);
  D-FO2 (`hold`, the host teleports to ICE_TILE, `release`, the guest lands there); D-DOT (within 8 u of the host's own
  `world.x/z`); D-REJOIN into 300 with the dot hidden before the guest's fade; D-SHARED (a log grep for sharing violations,
  an instrument row).
- **Regression:** every leg that tests s144/s145's OWN exit sends `worldfollow off` to its guest when the probe shows
  `netsync.world.out`, so it runs byte-identical to s164 (re-keyed by stage, never weakened): coop_world_wait's
  WT-FIELD/WT-FROZEN/D1/D2, coop_world_battle's T2 and duo routes, coop_world_party_duo's `mirror` leg.
- **Calibration:** R1 and R2 get a behavioural OLD on s164 (above). R3 and R4 calibrate by lever (`r3 old`, the dry
  `saveguard old`) and by their pure truth tables with mutants: no verbs-first deploy. Every piece gets LEVER_PREDICTED on
  s165.
- **Bench order after the deploy**, one change per test by lever: the solo follow-out first and alone (the first C#
  field-to-world commit ever run), with `dot off`; then the dot rows; then R3/R4; then T2; then the duo; then the regression
  set; then the owner's two-PC look (`game_snap -Id`).
- **The domain tests:** GATE-PROFILE's 18 files, the later co-op bench files and the new file, in the MAIN repo or with the
  templates extracted (the worktree skip trap).

## Known limits (s165)

- A host on Path D's 9013 reads as 9011 (decision 2). Dev-only today.
- The two PCs need the same world content (overrides, coast stamps, `TransportControls.csv`); decision 10's fingerprint is a
  later rung.
- The guest lands about 6-7 s after the host on the duo (less on a faster PC), where the host stood a few seconds earlier.
- The dot moves in steps of about 6.7 a second (section 0 every 150 ms), and holds its last pose while the host's request
  sequences run (calling, mounting, boarding, digging): the anchor stops updating then.
- World one-shots replay on the guest's copy at its landing (WORLD05's 9605 arrival has no once-bit). The benches land only
  on 9011 at the New-Game scenario.
- On this install FF9Coop's fork `30003 1953` takes every 9012 dive return, solo or co-op, onto that stub field. R3's legs
  judge the arm against the host's real landing field, never a hard-coded 1953.

## Open for the owner

- The dot's look: the tint, the size, and the edge policy on the disc-1 window (pin to the edge, dimmed; or hide).
- The words above.
- Whether FF9Coop (`30003 1953`, last in `FolderNames`) is still wanted.
