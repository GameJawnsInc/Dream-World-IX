# World-map co-op: the guest follows the host (options)

The owner's ask (2026-11-01): the guest actually follows on the world map. Today it stands frozen where it walked out (s144)
until the host's next field. This study lists what makes following tricky, the shapes it could take, and the decisions only
the owner can make. Nothing is built. **The owner decided (2026-11-01): two bodies**, the airships and the boat pull the
guest aboard, Choco is one bird each, the guest's own entries are refused, and there is no leash (see Decided, below).

The recon ran as one workflow: 4 read-only lanes (the world engine, the vehicles, the world scripts, netsync), a skeptic per
lane who re-opened every citation, and a completeness critic. Its output is in the session scratchpad as `wf/recon.raw`
(digest: `wf/digest.md`). C# citations are at the live s164 clone's lines (`C:\gd\FFIX\Memoria\Assembly-CSharp`). The
world-script facts come from a disassembly of the install's 13 dispatchers (EVT_WORLD_WORLD00-12), made with the kit's pure
readers and kept out of the repo, because it is game data.

## What happens today

- **s144:** on the world map a following guest is frozen (the `WorldFreezeHold` conjunct on the movement dispatcher,
  ff9.cs:5545), its world keys are masked and the full map is refused. The host drives. When the host enters a field, the
  guest warps into it. When the host walks OUT of a field onto the world map, a guest left on that field stays there
  (S144-DESIGN decision 5).
- **s145:** a host battle boots the guest's diorama from the world map and returns it warm. Aboard a vehicle the guest
  declines.
- Neither player sees the other on the world map: the position lane sends the field-0 sentinel there
  (NetSyncClient.cs:2329), and no ghost exists on either side.

## The shapes

- **1a, ride-along by carrying the walker.** Every world tick, the guest's own controlled actor is put at the host's pose.
  The guest sees one body, its own world Zidane, going where the host goes. That is stock's one-body look. Neither side
  needs a ghost.
- **1b, ride-along by camera.** The guest's actor stays put and hidden; its camera follows a ghost of the host.
- **2, free walk with ghosts.** Each walks its own copy and sees the other as a second body. A leash, or the existing
  rejoin at every stop, keeps them together.
- **3, hybrid.** Free walk on foot. Aboard a vehicle the guest is a passenger; after the landing it is set down beside the
  host.
- **4a, vehicle changes by world reload.** 1a between transitions. At each board or landing, the guest reloads its world
  from the host's story snapshot, so its own world script puts it aboard (or on foot) at the host's spot.
- **4b, the first step only.** Follow the host OUT onto the world map, and show the host as a marker on the frozen guest's
  minimap.
- **4c, a hidden walker under a vehicle ghost.** The guest's walker stays hidden in the on-foot row and is carried under
  the host. The host's vehicle is drawn as a bare ghost model.

## What is tricky

### 1. Vehicles (the owner's worry, confirmed and sharpened)

- **Which vehicle you are is decided at world load.** Each vehicle's Init in the world script runs AttachObject plus
  DefinePlayerCharacter when the travel-mode byte (gEventGlobal 190) names it. A live write of that byte plus
  `w_movementChange` (what the ~ menu's vehicle lever does) only swaps the physics row: the speed, the terrain mask, the
  camera and the music (ff9.cs:5947-5988). It never rebinds the body. So C# cannot give the guest the host's travel mode in
  the middle of a world visit. That is the blocker for 1a aboard.
- **Boarding and landing are script sequences.** Each free-roam dispatcher has a request machine in entry 2, switching on
  Map.Byte[37]. Its requests are: call Choco, mount, dig, Dead Pepper, dismount, the gold chocobo's take-off and landing,
  board or leave the Blue Narciss, and board or land the Hilda Garde III and the Invincible. The request codes are numbered
  per dispatcher. C# only services them (RunWorldCode → `w_frameSetParameter`). The take-offs and landings are animated
  loops (the Hilda Garde III rises for 60 frames). If the guest plays its own copy of a sequence while a host pose is also
  being written, two writers fight over the transform for a second or more.
- **Every vehicle exists twice.** Each player's world spawns its own Choco, boat and airship from its own position records.
  On the guest, those are the host's spots as of the guest's last field load, and they stay put on the world map. If the host
  flies off, the guest still sees its own airship parked where it was. Under free walk the guest could board its own copy,
  which makes two airships and breaks the one-party-per-vehicle fiction.
- **A vehicle exists only if the guest's own story spawned it.** The dispatchers gate each vehicle on the story counter
  (the boat at 9400 on 9003, the Hilda Garde III at 10400 on 9007, the Invincible at 11100 on 9008), and Choco on
  gEventGlobal 191. On a dispatcher that never spawned it, the on-foot anchor's per-frame read of the vehicle dereferences
  null every frame (EBin.cs:1778-1789, unguarded). At load, an unclaimed travel mode is THE [190] DISPATCH LAW black screen.
  The kit's world self-heal can mask that as a foot actor running a vehicle row (ff9.cs:4630-4691). Any shape that gives the
  guest a vehicle mode needs a claim check BEFORE the load.
- **On foot cannot follow a vehicle.** The on-foot terrain mask excludes the boat's water and the open sea, and the airship
  moves at up to about 4.5x walking speed. A pose written onto an on-foot actor over an illegal tile never updates its ground
  or terrain id (ff9.cs:5598-5606), so the camera aims at a stale height. Free walk therefore fails across any vehicle
  segment unless a passenger rule exists.
- **The enterable vehicles.** Triangle aboard (the Menu key) enters the vehicle's bridge field: Blue Narciss/Bridge 2855
  (from 9003) or 2856 (9009), Hilda Garde 3/Bridge 2850, Invincible/Bridge 2750. Cancel on a location while aboard enters
  that location directly. Examples: the Hilda Garde III's Engine 2851 and Deck 2852; the Invincible's Bridge 2752, Memoria
  2901 and L. Castle/Airship Dock 2165; the boat's L. Castle/Harbor 2173 and A. Castle/Port 2403.
  - Every one of these entries writes the vehicle's live pose into the vehicle record before `Field()`.
  - **That is good news:** a field round trip is stock's own lawful way to put the guest aboard. A guest that follows the
    host into the bridge (s144 already does that) gets the travel mode, the fresh record and FieldEntrance 9999 from the
    story mirror. Its own exit from the bridge then lands it aboard its own copy, at the host's spot.
  - What is missing is the follow back OUT (section 3).
  - Unknown: whether the talk relay already replays the host's "new destination? Yes" on the Hilda Garde III bridge.
- **The vehicle record is stale while aboard.** The boat and both airships share one 9-byte record (gEventGlobal 74-82). It
  is written at landing, at the Triangle bridge entry and at a dock entry, never while sailing or flying. The live pose
  aboard is in the on-foot record (64-72), which the anchor rewrites every frame from the vehicle. Choco has its own record
  (83-91), rewritten while ridden. Any put-aboard or parked-vehicle sync must take the host's LIVE pose.
- **Choco is two bodies with one rider.** The mount is the controlled actor, and the rider (Zidane) is a separate actor
  slaved to it. A two-player ride means one of two things: the guest rides its own Choco copy at the host's pose (nothing
  extra is drawn), or a second bird rides beside the host. Calling Choco needs Gysahl Greens from the item menu, used on a
  track. Digging and Dead Pepper are host-only keys.
- **Battles never start aboard**, because only the on-foot row has encounters (ff9.cs:1483). The race to watch: the host
  lands and meets an encounter while the guest's set-down is still pending, so s145's vehicle decline makes the guest sit
  that fight out.
- **The kit's own vehicles break the stock rules.** The Southern Ring boat re-moors at home on every world load, so a
  reload cannot put the guest aboard it. The ferry voyage is a scene inside free-roam 9011 that nothing marks as an event
  world.
- **The physics rows are per-install data.** TransportControls.csv replaces the whole table at each world load. Two
  installs with different CSVs disagree on speed, terrain and encounters.

### 2. The world map is centred on the guest's own walker

The torus wrap, the sky, fog and rain domes, the camera aim, the minimap's player pointer, the location title and every
cell trigger (WorldEvent) all key on `w_moveActorPtr`, the guest's own controlled actor (WMWorld.cs:941-957 and
1145-1178; ff9.cs:2776-2800 and 5344-5353).

Terrain streaming is NOT the problem. This Memoria loads all 480 blocks at world frame 5 and never discards one
(ff9.cs:3703, WorldState.cs:25). That needs a block-ready census in game before anything relies on it: the kit's own
teleport fix assumed far blocks could be unstreamed.

The problem is distance. A camera that chases a ghost more than roughly 420 units in x or 290 in z from a parked walker
sees the edge of the layout. So 1b needs four things: re-keying the wrap and the domes in the engine, a C# chase camera,
and a gate on the parked walker's own entrance prompts, which keep showing. Even with all of that it ends up worse than
moving the walker. **1b is ruled out.**

### 3. Getting onto the world map at all

- **Following OUT does not exist.** The host's field exit to the world map (WMAPJUMP) sends no intent, and a guest left on
  the field stays there. Every shape needs this step. A late follow-out needs no wire change: section 7's b6 says the host
  is on the world map. The guest's own copy of the exit field's cascade then picks the same world from the host's story
  counter and region key, and section 0 carries both.
- **The world load is slow and lands late.**
  - Each world load ends with a synchronous load of all 480 blocks AFTER the first WorldHUD frame: 4.4 s on this PC under
    the harness.
  - Every new step must therefore key on `w_blockReady`, not on WorldHUD.
  - By the time the guest lands, the host may already have mounted Choco. The landing must take the host's live pose and
    mode, not a snapshot pinned at the host's exit.
- **Host and guest can be on different world states or discs.** Each copy picks its own world (wldMapNo) at its own exit.
  The disc art (story counter 11090 and up) and the Mist (below 5990) follow each copy's own counter. A host pose placed on
  the guest's copy of a different state can land on sea or inside a re-cut cliff. Detecting a mismatch is free: section 0
  already carries the host's world index (gEventGlobal 102) and story counter.
- **A guest that pairs or Continues on the world map** is not mirroring the host's story until its first field load, so it
  stands on its own save's world, possibly on another disc. Either keep s144's freeze until the first mirror, or reload the
  guest onto the host's world.

### 4. Seeing a second body (free walk and the hybrid)

- **Stock never draws a second walker on the world map.** The world has three walking bodies: Zidane (W0_001), Dagger
  (W0_002) and the world Mog (W0_011). So the co-op dress carries only partly: a moogle-dressed guest can be the world Mog,
  but Steiner and the other dresses fall back to Zidane. A field model gets the wrong shader on the world map.
- **A ghost must be a bare model outside the event lists.** It must never be an index 1-11 actor, because those indices
  bind pointers and share status slots. It needs:
  - re-placing from canonical coordinates every tick, after the wrap (a wrap shift moves only ActorList actors);
  - its own ground query, made in the render frame;
  - its own shadow.

  A mounted host is two models plus the chocobo's colour texture; an airship is one model.
- **The host needs a ghost of the guest too.** The host is blind to link stalls (it has no outage clock), so that ghost
  would vanish and reappear without a log line.
- **One roaming object differs per copy.** Each copy rolls a random spot (one of five, on five dispatchers) for a roaming
  object, model 452. The host's ghost can fly to a place that is not there on the guest's screen.

### 5. The camera, the sound and the feel of a carried walker

- **The camera.** Every camera input (L1/R1 yaw, the right stick, R2, L2) and the on-foot camera follow live in
  `w_movementBasicOperation`, which is the very call a pose writer replaces. Under 1a on foot the guest's camera neither
  follows the walker nor turns (ff9.cs:6143-6160 and 6447-6472). Either mirror the host's camera, or drive the yaw from the
  host's motion.
- **The effects.** Every travel effect comes from the input routine's speed: the foot splash and dust, the ship's wake, the
  chocobo and airship spray, the engine-hum volume and the airship's bank. A carried vehicle glides silently with a stuck
  hum. Restoring the effects is new code inside the vehicle routines.
- **The music.** It follows the guest's OWN row (and disc), so a guest left on foot under the host's airship hears walking
  music.

### 6. Control-off windows stall a drive

The movement seam where s144's freeze sits runs only while the guest has user control (ff9.cs:5185-5187). Every board,
landing, moogle and window case starts with DisableMove. And the guest's own world runs its own one-shots at its own
moment:
- WORLD00's story-counter-2400 tutorial window;
- WORLD05's 9605 arrival sequence, which replays on every load because it has no once-bit;
- the Invincible's one-time line.

During each, three things happen: a drive at that seam stops, the rejoin refuses ("a world script holds control"), and the
host cannot see why. A drive needs one of three things: a seam that runs regardless of user control, a world variant of
the key relay, or a host-side line.

### 7. What the guest may do on its own

- **Its own location entry.** Today, under the ~ Release lever, a guest's Confirm on an entrance passes when the host is on
  the world map, so the guest walks into a town alone and waits there. Under free walk this must be refused at the press,
  unless the host is entering the same place.
- **Host-owned in every shape:** boarding its own vehicle copy (Confirm), dismounting or landing it (Cancel), the bridge
  (Triangle), the Chocograph dig (Special), Dead Pepper and the world moogle's save. s144's mask already covers all of them.
- **An existing defect, found in the scripts and not yet seen in game.** WORLD12, the chocobo-dive stop, masks the d-pad
  from its Main_Init. Its only exit is a control-on Menu poll (Dead Pepper → field 1953), which the freeze masks, and the
  rejoin refuses event worlds. A frozen guest that lands on 9012 is stranded until the ~ Release lever is used.

### 8. Story and saves: less risky than feared

The s144 worry, "every world script that fires on position", turns out to be mostly harmless:
- every world-map write on a following guest lands in the mirrored story array, and the next field load overwrites it;
- the guest can never save it (a manual save is refused, and autosave is suppressed while mirroring);
- it never reaches the host;
- the world map writes the story counter at exactly one place (WORLD00's 2400 → 2411).

What remains is:
- scene changes: the guest's own entries, the bridge exits, 9012;
- visible disagreement until the next field load: stale parked vehicles, the roaming object;
- the same-world rule.

One guard to add whatever the shape: put the save refusal at the save call site, on `SpectatorField`, not only in the key
mask, before any shape frees the guest's world input.

### 9. The wire and the link

- **The host's world pose already reaches the guest.** Section 0 is the host's whole story array, sent every 150 ms in
  every mode. On the world map it holds the host's live pose in absolute world units x256 (64-72, or the vehicle's pose
  while aboard), the travel mode (190), the Choco record and tier, the world index and the story counter. That is enough for
  a minimap marker and a coarse follow, with no wire change.
- **Smooth motion needs the 30 Hz position lane.** Trailing bytes on the type-0 record stay inside v14 (old readers stop at
  their own length). Never put a world id (9000-9012) in the lane's Field: an old guest would treat it as a field.
- **Section 7's flags byte is full** (s144 took the last two bits).
- **v14 or v15.** The v15 bump is already promised to comms, the guest menu and B4.2. World follow can stay additive under
  v14 and degrade to s145's freeze on an old peer, or it can ride v15. The owner's call.
- **Link stalls at airship speed.** The two-PC link stalls for about 2.3 s roughly every 13 minutes. At airship speed that
  is a jump of 90-125 units (up to 250 doped). No velocity or sequence number rides the lane today, so there is nothing to
  dead-reckon from.
- **WorldTPS is per-install.** This install runs 28 (Memoria's default is 20), and the s163 speed mirror carries only
  FieldTPS. That does not matter for a ride-along, but under free walk the two players cross the world at different speeds.
- **Install parity.** Netsync has no content handshake. The world overrides (the Southern Ring, the coast stamps), Path D's
  9013, TransportControls.csv and the [Worldmap] ini knobs can all differ between the two PCs. Placing the guest at the
  host's coordinates on a different world is the actor-brick class.

### 10. The host drops mid-flight

What the guest is left standing on depends on the shape:
- bound to its own airship copy (1a or 4a aboard), it hovers, which is safe;
- a hidden foot walker carried under the host (4c) is left over sea or a mountain with a stale ground, and an unfollow then
  hands the guest a foot actor on an illegal tile.

A deliberate host quit sends nothing, so the guest waits out the 40 s grace (backlog item 15). A rule is needed: on peer
loss, never hand free control to a guest whose mode or pose came from the host. Either hold it until the exit ramp
reloads its own save, or reload at once.

### 11. What can be benched

- **On foot:** world legs are harness-benchable; 9011 is the proven bench.
- **Vehicles:** reachable through the load-time poke route the terrain study proved (Hilda Garde III 13/13). The airship
  throttle (Confirm) is hooked, but the climb stick and the free camera are raw XInput.
- **The duo:** its two world loads would coincide by design, which on one PC is ONE-PC LOAD CONTENTION.
- **The feel** (camera, wake, sound, stall jumps) is an owner two-PC check.

## The shapes compared

| Shape | What the guest sees | Vehicles | Verdict |
|---|---|---|---|
| 4b: follow out + host marker | its own frozen walker, the host as a minimap dot | untouched | recommended first rung |
| 1a: walker carried to the host | one body (its own Zidane) going where the host goes | blocked on its own | recommended on-foot base |
| 4a: 1a + vehicle changes by reload | as 1a, aboard its own copy of the host's vehicle | stock Init binds it; a black load per board or landing | viable for the airships and the boat |
| 3: free walk on foot, passenger aboard | two bodies on foot; aboard, as 4a | needs 4a or a relay | viable later rung |
| 2: free walk + ghosts | two bodies everywhere | fails without a passenger rule | risky; foot-only worlds only |
| 4c: hidden walker under a vehicle ghost | a ghost airship over a walker it cannot see | foot row under a vehicle | risky fallback |
| 1b: camera follows a ghost | the host's ghost, its own walker parked | ghost only | ruled out |

## Decided (the owner, 2026-11-01)

1. **Two bodies.** Each player sees the other walk on the world map. That is shape 2 on foot, with a vehicle rule per
   vehicle (shape 3's division of labour). The ride-along shapes (1a, 4b as an end state, 4c) are not the goal. The
   ride-along stays the mechanism for the airship leg only.
2. **The airships and the boat: pulled aboard.** When the host boards, the guest's screen goes black and it reloads aboard
   its own copy of the host's vehicle at the host's spot (shape 4a's reload). It rides along, and is set down at the host's
   landing point. Both players see one vehicle; the guest is inside it, so the host draws no ghost of the guest.
3. **Choco: each rides its own bird.** The guest may mount its own Choco copy, and each player sees the other on a ghost
   chocobo. This supersedes the s144 call's "one party per chocobo" for Choco only. Digging and Dead Pepper stay host-only.
4. **The guest's own location entry: refused with a buzz.** The guest stays outside, with a line saying its partner isn't
   there. It enters a town only through the existing rejoin, when the host enters.
5. **No leash.** The guest may roam anywhere on the host's world. A partner dot on the minimap and the full map shows
   where the host is, and the rejoin pulls the guest in at the host's next stop.

## What the decisions mean

- **Ghosts both ways** (section 4): a bare world model, re-placed from canonical coordinates after every wrap, grounded in
  the render frame, with its own shadow and sampled animation. A ghost of a mounted player is two models (W0_003 in the
  tier's colour plus W0_001 on its `*_CHO` clips). The dress maps to a world body: moogle → the world Mog (W0_011), Garnet
  → Dagger (W0_002), everything else → Zidane (W0_001), unless the owner says otherwise.
- **The world pose on the wire both ways, at 30 Hz.** Trailing bytes on the type-0 record, inside v14, with the lane's
  Field kept at 0; canonical coordinates, the travel mode, the animation and the frame. Section 0 stays the host's coarse
  source for the dot.
- **The split key mask.** The s144 freeze lifts for directions and the camera. Confirm on an entrance cell is refused with
  the stock buzz (102) and a line. Confirm near the guest's own Choco must still pass, to mount it, and so must the gold
  chocobo's take-off. Inference, to settle in the design: the stock entrance poll already requires the Choco proximity
  flag (Bit 812) to be clear, so the place byte set on an entrance cell (on foot or mounted) tells the Confirms apart. Special (dig, the world moogle), Select and Menu stay host-owned:
  Menu covers the bridge exits and Dead Pepper. Cancel passes (dismounting the guest's own Choco, the gold chocobo's
  landing).
- **The guest's own Choco** obeys the guest's own terrain rows, so the gold chocobo can fly with the host. The guest's
  Choco copy sits at its last mirrored spot, and the next field load re-mirrors it to the host's. While the guest rides,
  s145's vehicle decline holds: if the host walks into a battle, a mounted guest sits that fight out on the digit panel.
- **Pulled aboard** needs, in order: a claim check before the load (the vehicle exists on the guest's dispatcher under its
  mirrored story, and both are on the same world); the host's LIVE pose (64-72 or the wire, never the stale 74-82); one
  black world load; the guest's copy carried in-tick by the host's pose with the guest's input masked; then the set-down.
  Landing into a town needs nothing new (the rejoin). A landing in the open needs a second black load onto foot at the
  host's getoff-validated landing point, which must finish before the host's first possible encounter. Triangle to the
  bridge needs nothing new either: the guest follows into the bridge field, and its own exit puts it aboard, once
  following OUT exists. On 9009 there is no boat object, so a guest there waits on the ground.
- **No leash** means the guest can be far from the host when the host enters a town or boards. Both the rejoin and the
  pulled-aboard reload move the guest from anywhere, so nothing new is needed.

## The order (two bodies)

1. **Follow OUT, the partner dot, and two fixes.** The guest follows the host out of a field onto the world map; the dot
   on the minimap and the full map, from section 0 (no wire change); the 9012 strand; the save guard at its call site.
   Key the landing on `w_blockReady`, take the host's live pose, check the same world. The guest stays frozen on the world
   map in this rung. Benchable solo and on the duo (6603 → 9011).
2. **Free walk on foot with ghosts both ways, on the foot-only worlds (9002, 9010, 9011).** The world ghost and its dress
   map, the world pose on type-0 both ways, the split mask and the entry refusal, the same-world rule, a world pairing rule
   (a guest that pairs on the world map stays frozen until its first field mirror), the inbound lane-gap line on both
   roles, and a WorldTPS mirror beside s163's FieldTPS. Re-arm the DeclineOnce world book at each world load.
3. **Free walk on the vehicle worlds, with Choco.** The guest mounts its own Choco; the mounted ghost; the guest's parked
   airship or boat copy hidden or re-placed when the host moves its own; the Choco-call rule (still open, below).
4. **Pulled aboard: the airships, then the boat.** The claim check, the reload aboard, the carried copy, the set-down, the
   encounter race. The kit's Southern Ring boat cannot be pulled aboard by a reload (it re-moors at home), so it waits on
   the owner's scope call.

## Still open for the owner

1. When the host calls Choco with Gysahl Greens, where does the guest's bird come from? Its copy appears beside the guest,
   or beside the host, or the guest rides only a bird it walks to (its menu is refused while mirroring, so it cannot call
   one itself).
2. A mounted guest when the host walks into a battle: sit it out (s145 today), or dismount it and boot the battle, which
   needs an in-game check that a world battle starts and returns warm around that dismount.
3. May the free-walking guest open the full map and its menu? s144 refuses the full map because opening and closing it
   rewrites usercontrol, which the rejoin reads. GUEST-MENU named the world map as the menu's natural place.
4. Is a second black load acceptable when the host lands in the open, or should the set-down drive the guest's own stock
   landing case instead (unproven, below)?
5. Content parity: enforce identical world content on both PCs (FF9CustomMap-world, Path D, TransportControls.csv), or
   detect a mismatch and refuse?
6. The kit's own vehicles (the Southern Ring boat, the ferry voyage): in scope, or stock vehicles only?
7. The host drops mid-flight: hold the guest until the grace ends, or reload its own save at once? Should a deliberate quit
   send a goodbye word (backlog 15)?
8. Should the host also get a line when the guest is loading or held by a window?
9. Wire: additive under v14, or ride the v15 bump with comms and the guest menu?
10. Game knowledge:
    - Which moments take control away mid-free-roam (WORLD05's 9605 arrival, the Invincible's one-time line, others)?
    - Can a host be aboard the Blue Narciss on 9009 in stock play? 9009 spawns no boat object.
    - Is model 452 the Chocobo's Air Garden?

## Open: needs an in-game look

- Does a world-to-world reload with the host's story applied run the dispatcher's Main_Init cleanly: the minimap armed, the
  walker placed, the vehicle re-attached? The proven lever is a field-to-world exit with poked bytes. A world-to-world
  reload has never run.
- Does the talk relay already replay the Hilda Garde III bridge's "Yes"?
- Does writing the guest's request byte from C# run a stock board case to completion with the guest's input masked? The
  cases leave the byte latched when their preconditions fail.
- A block-ready census after world frame 5, to confirm that every block is resident.
- Does a world battle start and return warm around a mounted guest, if the owner wants a mounted guest dismounted for
  the host's battle (open decision 2)?
- Can the guest's own stock landing case run from C# at the host's landing point, to replace the second black load
  (open decision 4)?
