# Battle co-op — feasibility study (2026-07-12)

> **STATUS: B0 + B1 are BUILT and ★ SOLO-TIER PROVEN including the full command set (same day) —
> engine patch `memoria-patches/s37-netsync-battle.patch`, wire v4: typed frames, the battle-state
> spectate panel, `[Netsync] GuestSlots`, and guest commands covering Attack/Defend/ABILITIES/ITEMS
> (a roster frame streams menu content; digit-menu UI with pagination + target pick; live host-side
> revalidation — an unlearned-cast cheat path was found and closed in playtest). ATB feel: the
> `RemoteMenuOpen` WAIT/Turn-Based freeze, capped per turn by `[Netsync] GuestWaitMs` (default 30s)
> so an idle guest can't lock the host indefinitely. Still out: Throw, double-cast/mix,
> monster-transform. Two-machine session pending (update both DLLs — v4 rejects older peers).
> CONFIG SURFACE SHIPPED (2026-07-12): every s37 knob is point-and-click — `ff9mapkit coop
> host|join --guest-slots/--guest-wait/--ghost-as/--follow-host` + `coop show`, and the Workspace
> Co-op tab's Play-style panel (Apply hot-reloads a running game); no more hand-editing
> Memoria.ini. V2 `[[coop]]` RUNG 1 ★ SOLO-PROVEN (same day, field 4003: "taking the step
> triggered the message once" — the fire AND the once-latch, since the Range body runs every
> frame in the plate): the engine coop cells (peer presence/position → gEventGlobal 2032-2039)
> + the kit-compiled two-plate gate (design + cell map below); test field `coopgate/`.
> RUNG 2 BUILT (same day; ⚠ deployed to 4003 as the 3-beat "twin vault", awaits the solo
> playtest): `zone =` gather gates, `requires_flag` sequencing, and `mode = "hold"` -- a
> LEVEL flag maintained while the peer stands on a plate (an always-inside poller region +
> one assign expression), consumed by the EXISTING flag-gated `[[gateway]]` = the classic
> co-op held-plate door. Pure kit work, zero new engine bytes.
> Two-machine symmetric-plates run pending like everything else s37.** The rest of this
> document is the research that shaped it. Companion to the s36 exploration co-op (ghost
> sync).
> Sources: the Memoria engine source (`C:\gd\FFIX\Memoria\Assembly-CSharp`, all cites below),
> the s36 patch (`memoria-patches/s36-netsync-ghost.patch`), and web prior-art (linked inline).

## Verdict

**Battle co-op is feasible — as an experimental pillar, not a moonshot.** The trap to avoid is
framing it as "network two running ATB battles." The winning frame: **one authoritative battle
(the host's), with the guest as a networked controller 2** commanding an assigned subset of the
party. That is not an invention — it is *restoring a native FF9 feature the PC port deleted*:

- **PS1 FF9 shipped 2-player battle.** A config option assigned each of the 4 battle party
  slots to controller 1 or 2; player 2 entered ATB commands for their characters, battle-only
  ([FF Wiki "Multiplayer"](https://finalfantasy.fandom.com/wiki/Multiplayer),
  [first-hand thread](https://www.finalfantasyforums.net/threads/ffix-2-player-function.34161/)).
  FF4/5/6 had the same design. The Steam port stripped it — no code remnant survives (grepped:
  the port's `FF9CFG` keeps `btl_speed`/`atb` but no per-slot pad assignment).
- **Nobody has done FF9 co-op on PC.** [Memoria issue #64](https://github.com/Albeoris/Memoria/issues/64)
  asked for exactly this and was closed "Won't do" (2020). s36 ghost sync appears to be the
  first FF9-PC multiplayer of any kind; a battle lane would be the first of its kind, period.
- **Every retrofit that shipped in this genre used command delegation into one authoritative
  instance** — the [Expedition 33 co-op mod](https://github.com/Kouzukii/expedition33-coop),
  the [Chrono Trigger multiplayer hack](https://www.romhacking.net/hacks/8337/), the KH2
  multiplayer hack. None mirrored the combat sim; none did game-level lockstep (only emulator
  netplay does that, at the emulator layer). We sit *inside* the engine, so we can delegate at
  the command-queue layer — a cleaner seam than any of them had.

## Why the engine is unusually friendly to this

1. **Latency tolerance is structural, not mode-dependent.** Commands are discrete and a ready
   slot simply waits in the queue until commanded — in EVERY ATB mode, a guest deciding slowly
   is mechanically identical to a local player deciding slowly (see "ATB modes" below for the
   full matrix). On top of that, WAIT-style modes freeze gauges during menus
   (`BattleHUD.IsNativeEnableAtb`, `BattleHUD.Public.cs:742-754` + the Turn-Based logic in
   `FF9BMenu_IsEnableAtb`, `:723-740`), the sim is a fixed-timestep tick decoupled from
   rendering (`FPSManager` accumulator, `HonoluluBattleMain.UpdateFrames:580-608`), and a clean
   full-sim pause exists (`IsPaused` → `UpdateBattleFrame` early-return,
   `HonoluluBattleMain.cs:673`; plus `FPSManager.DelayMainLoop`).

2. **Command injection is a shipped pattern, not a hack.** Memoria's own auto-battle is the
   template (`BattleHUD.Unity.cs:582-602` `SendAutoAttackCommand`): borrow `CurrentPlayerIndex`,
   call `btl_cmd.SetCommand(btl.cmd[0], commandId, sub_no, tar_id, cursor)` (`btl_cmd.cs:153`),
   add to `InputFinishList`, release focus. Berserk/Confuse inject from the ATB loop the same
   way. Our own deathrules second wind already queues commands from mod code in-game (proven).
   Validity rules are mapped: a normal command needs the unit alive + not `NoInput`/`CannotAct` +
   `cmd[0]` free (`CheckUsingCommand`, dropped otherwise at `btl_cmd.cs:933`); Sys-range commands
   may target even dead units. Targets are a plain `u16` btl_id bitmask (players = bits 0-3,
   enemies = 4-7; `ProcessCommand`, `BattleHUD.cs:1568-1582`).

3. **Battle input is one global focus over a ready queue** (`ReadyQueue` / `CurrentPlayerIndex` /
   `InputFinishList`, `BattleHUD.Public.cs:27-55`; menu opens via `SwitchPlayer`,
   `BattleHUD.cs:1242`). Slot ownership = "the HUD skips guest-owned slots; the network feeds
   them instead." Small, local change.

4. **The state a spectator needs is tiny.** `EnumerateBattleUnits()`
   (`FF9StateBattleSystem.cs:111`) + `BattleUnit` accessors give name/HP/MP/ATB/status/trance;
   a full 4v4 snapshot is ~300-400 bytes, deltas far less. HP reads must use the logical
   accessors (`BattleUnit.CurrentHp` — the +10000 non-dying-boss convention).

5. **s36 infrastructure already reaches into battle.** `NetSyncClient.Update()` runs every frame
   in battle (today it just sends the field-0 sentinel); the transport lives all session; both
   lanes (TCP `NoDelay`, WS relay) are reliable ordered streams. The 38-byte fixed packet is a
   framing choice, not a limit — see "wire v3" below.

## The architecture decision

**Host-authoritative command delegation.** The host runs the only real battle. The guest gets a
live readout + command entry for the slots assigned to them. Rejected alternatives:

- **Deterministic lockstep: DEAD END** (do not re-explore without an engine-refactor appetite).
  All combat RNG — damage calc, enemy AI, ATB init — draws from one global, **unseeded**
  `UnityEngine.Random` (`Comn.random8/16`, `FF9/Comn.cs:8-16`; `GameRandom` aliases the same),
  with no snapshottable state, *shared with frame-coupled cosmetics* (camera pick, voice, rain,
  SPS). Two machines diverge on the first draw. Fixing it means isolating a seeded sim-only PRNG,
  a networked tick clock, and asset-preload guarantees (sequences stall on `WaitSFXLoaded`,
  `UnifiedBattleSequencer.cs:232-256`) — a research project on its own, for no UX gain over
  host-authoritative.
- **Full mirrored battle on the guest's machine**: not needed for co-op to be real, and HIGH
  risk. Kept as an optional *cosmetic* rung (B3) because the engine half-supports it — see below.

## The rung ladder (each rung independently shippable + playtestable)

### B0 — Battle presence + live spectate readout (LOW risk)
Extend the wire with battle-state frames. When the peer is in battle, the overlay shows the real
fight: enemy roster, party HP/MP/ATB bars, whose menu is open. Read-only — zero desync surface.
This alone transforms "friend on field N (frozen)" into watching their fight unfold.
- Host side: a sampler in the existing per-frame Update (gMode 2/4 branch), serializing the
  `EnumerateBattleUnits` scalars on change (~a few B/tick).
- Guest side: render in the existing OnGUI overlay (the s22 F6 menu proves rich OnGUI in-game).

### B1 — Networked controller 2 (MEDIUM risk — the pillar's heart)
The guest commands their assigned party slots in the host's battle.
- **Host:** a slot-assignment mask (`[Netsync] GuestSlots` or negotiated in-session). The HUD's
  ready-loop skips guest slots (the exact place it already skips `InputFinishList` /
  `_unconsciousStateList`, `BattleHUD.Unity.cs:292-319`); a command frame from the wire is
  validated (alive, `cmd[0]` free, legal ability/MP — the engine re-checks at inspection anyway,
  fail = silent drop + re-offer) and injected via the auto-battle pattern.
- **Guest:** a battle command menu in the overlay (commands/abilities/items/targets come from
  the B0 state stream + a once-per-battle roster frame). The guest is meanwhile standing on a
  field in their own game — assist mode captures menu input, like F6 does.
- **Latency UX:** the `RemoteMenuOpen` flag (see "ATB modes" above) OR'd into the two existing
  gauge gates gives every host ATB mode its native feel for remote turns. Optional hard gate:
  `IsPaused` while waiting on a guest turn.
- **Fail-safe law (same as all coop):** guest stale/disconnected (existing 2s staleness) →
  slots revert to host control instantly; feature off → byte-identical vanilla behavior.
- Precedent UX spec: the PS1 config screen (per-slot 1P/2P assignment, P2 battle-only).

### B2 — The guest's own character rides along (SHELVED 2026-07-12 — see "Beyond B1" below)
The guest's character joins the host's party for the session and the guest commands it (B1
machinery). **Shelved after the solo-proof design review**: in visitor mode (below), the guest
commanding one of the HOST's party members via `GuestSlots` already delivers the play-together
fantasy without B2's save-authority questions (whose XP/levels? what happens to "their"
character on disconnect?). B2 only earns its complexity if a design specifically wants the
guest's own build imported — revisit then. The substrates stay proven for that day:
- **Party membership:** `B_PARTYADD` is dedup/overflow-guarded and DLL-free (in-game proven,
  incl. custom 13th characters) — add the guest character while co-op is live, party ≤ 4.
- **Stat sync:** the engine ships `btl_init.SwapPlayerCharacter(unit, PLAYER)` (`btl_init.cs:610`)
  and the `OnBattleInit` Overload hook (`battle.cs:545`) — seed a slot from a serialized PLAYER
  blob (stats/equipment/abilities) sent by the guest at session start / battle start.
- **HARD WALL — do not attempt a 5th party slot:** `PLAYER[4]`, 8-bit `btl_id` (players own
  bits 0-3), fixed `btl_data[8]`, the 4-slot party UI, and every win/lose scan assume ≤4
  players. Slot replacement/party-add only.

### B3 — Visual mirror on the guest's machine (HIGH risk, optional, later)
Cosmetic-only puppet: the guest's engine boots the same encounter and *replays* the host's
commands; authority stays with the host (state corrections streamed). The engine half-supports
it: any encounter boots directly from `battleMapIndex` (+ pinned `PatNum` + `debugStartType` —
the `BattleMapDebug` path, `BattleUI.cs:144-171,257-271`), and the `isDebug` branch already
suppresses enemy AI entirely (`HonoluluBattleMain.cs:529-541`) while injected commands still
play their full animations through `CommandEngine`. Divergence sources to force/ignore are
enumerated (StartType roll, pattern roll, initial-ATB rolls, idle-anim phase). Build only after
B1 proves fun; B0's readout may be plenty.

## ATB modes — no strict requirement needed (analyzed 2026-07-12)

FF9/Memoria has TWO orthogonal knobs, and **only the HOST's settings matter** (the battle exists
only on the host; the guest's config is irrelevant — half the compatibility matrix vanishes):

- **Vanilla Active/Wait** (`cfg.atb`, the in-game ATB option): Wait freezes gauges while a
  target/ability/item submenu is open (`IsNativeEnableAtb`, `BattleHUD.Public.cs:742-754` —
  note vanilla Wait does NOT freeze on the top-level command list); Active never freezes.
- **Memoria "ATB Mode"** (the config dropdown = INI `[Battle] Speed`; label→value mapping in
  `ConfigUI.cs:1227-1229,1390-1392`): Normal=0, Fast=1, Turn-Based=2, **Dynamic=5** (the INI's
  "Simultaneous" — it changes command-EXECUTION concurrency at dequeue, `btl_cmd` Speed≥3
  paths, and forces SFXRework; it does not change command entry). Fast/Turn-Based add a
  catch-up loop (`ProcessActiveTime` do/while, `HonoluluBattleMain.cs:424-563`) that
  fast-forwards idle time; **the loop re-checks `FF9BMenu_IsEnableAtb()` every iteration
  (`:442`) and stops when a player's gauge fills** (`needContinue=false`, `:480,489-491`) — it
  cannot skip past a pending (guest) turn. Turn-Based's freeze = `isMenuing || hasQueue` in
  `FF9BMenu_IsEnableAtb` (`:728-739`).

**Correctness is mode-independent.** The seam (ready slot waits in `ReadyQueue` → wire command
→ `SetCommand`) works identically in all 2×4 combinations; a slow guest is exactly a slow local
player. What differs is only *pressure* (how much battle time passes while the guest menus) —
the same difference those modes already impose on local players.

**The one real finding: the freeze gates read LOCAL panel state.** `IsNativeEnableAtb` checks
`ButtonGroupState.ActiveGroup` and Turn-Based checks `_commandPanel/_targetPanel/….IsActive` —
a guest menuing over the wire opens no local panel, so on a Wait or Turn-Based host the battle
would keep running during guest turns (Active-like pressure), *unless* we OR a **`RemoteMenuOpen`
flag** (set by a wire frame while the guest's command UI is up; cleared on submit + staleness
timeout so a hung guest can never freeze the host's battle) into those two functions. That
single flag gives every mode its native feel for remote turns: Wait/Turn-Based hosts get their
expected freeze, Fast's catch-up holds automatically (it polls the same gate), Active/Dynamic
need nothing. It's a two-line engine change plus one wire frame — include it in B1; do NOT
restrict modes. Docs recommendation only: "Turn-Based feels best for relaxed co-op."

## Beyond B1 — the design space (added 2026-07-12, after the solo proof)

Three visions of "what FF9 co-op IS", sorted by how they relate to the architecture's
load-bearing fact: **each machine runs its own complete game** (own save, own flags, own
field); the shared world is an illusion produced by position frames on a shared screen.
Everything cheap lives downstream of that fact; everything expensive fights it.

### V1 — The stock experience: "visitor mode" (BUILT + ★ SOLO TIER PROVEN 2026-07-12, wire v5 —
### dressing/lighting/masks/encounter-pause all in-game verified; follow-warp awaits the
### two-machine session)
The guest is a presence inside the HOST's game: a cosmetic extra party member running around
the map, who commands one-or-more party slots in battle (`GuestSlots` is already a bitmask —
"or more" works today). Three additions complete it, all on proven rails:
1. **Ghost-as-party-member dressing** (cheap): the wire already carries a model id per frame
   and the ghost re-dresses live; a knob (`GhostAs = <char>`, or "dress the peer as their
   GuestSlots member") makes the guest LOOK like the Vivi they command.
2. **Follow-host warp** (moderate): the host's true field id is already broadcast every frame;
   a `FollowHost=1` guest auto-warps to match on change (the F6-Warp machinery, automated).
3. **Guest-side encounter suppression** while following (cheap): only the host's battles
   exist; the guest assists through the existing B0/B1 lanes.
**The honest wart — story-state divergence**: the guest's copy of a field renders THEIR flags
(different NPCs/doors; worst case a cutscene grabs them on entry). Same-story-beat saves
mostly mask it; visitor mode ships labeled experimental because of it. The guest is a spirit:
their chest/NPC interactions touch their own save and should be treated as void while
following.

### V2 — The from-scratch co-op campaign: the `[[coop]]` vocabulary (the kit's home turf)
"Two characters on two fields" already works today (independent games + everywhere-mode
meetups). What a from-scratch 2-player mod adds is DESIGNED INTERLOCK, and the trick that
makes it cheap: **position-derived cooperation needs no state sync**. The engine knows both
players' positions; it can compute "both standing on the plates" locally and set an ordinary
`gEventGlobal` flag that an ordinary kit gateway polls (`setVarManually` — verified public and
bit-identical to `.eb` GLOB writes back in the s36 era; this was the sketched-but-never-built
"two-plate puzzle"). From that one primitive: both-players-present doors, split-up-and-flip-
switches puzzles, hold-the-bridge encounters — an authorable `[[coop]]` block in `field.toml`,
each player advancing their own save through content authored for two. Zero story-divergence
problem, because we author both sides. This is the most differentiated thing the kit could
build on the co-op foundation.

### V3 — True shared-world stock wandering (research horizon — a remaster, not a feature)
Both players free-roaming ONE coherent stock world needs real state sync. The gradient:
one-way **flag sync is genuinely feasible** (GLOB writes broadcast as events over the reliable
wire) and shared-flags+chests would make the world mostly cohere. The killers: the single-
party data model (who owns Vivi when you're on different continents?) and stock cutscenes,
which are authored to seize "the player" — all ~674 fields would need coop-safe handling.
If ever attempted, it starts as a scoped flag-sync experiment, not a commitment.

**The recommended ladder**: two-machine validation of B0/B1 → V1 dressing → V1 visitor mode →
the V2 `[[coop]]` vocabulary → V3 stays a labeled research question with flag-sync as its
first probe. B2 stays shelved until a concrete design pulls the guest's own character in.

## V2 `[[coop]]` — the design (2026-07-12, studied from source; rung 1 = the two-plate gate)

**The split (same one that won the vehicle system): engine = mechanism, `.eb` = policy.** The
engine's ONLY new job is to broadcast the peer's presence + position into the flag substrate;
every gate/door/puzzle compiles to ordinary kit-authored field logic reading those cells. No new
wire frames (the position frame already carries everything), no engine knowledge of plates.

**The reserved cells — gEventGlobal bytes 2032-2039 ("the netsync coop cells")**, sitting at the
top of the kit's custom bit band beside the proven `MASK_SCRATCH_IDX = 2040` precedent (transient-
value cells high in the map; a save carries stale values harmlessly — they rewrite every frame
while co-op runs, and the engine NEVER touches them unless `[Netsync] Enabled = 1`):
- `2032` (byte): peer presence — 1 = the peer's ghost is live on MY current field, else 0
- `2034-2035` (Int16 LE): peer X, walkmesh units — the same space `SetRegion` quads use
- `2036-2037` (Int16 LE): peer Z
- `2033`, `2038-2039`: reserved zero
Addressing verified against `EBin.GetVariableValueInternal` (EBin.cs:1859): `VariableType.Int16`
reads `buffer[ofs] | (SByte)buffer[ofs+1] << 8` — BYTE-addressed, little-endian, sign-extended —
matching the kit's `GLOB_INT16` (0xD8) encoder incl. the long-index bit (`region._push_var`).
Writes are bare array pokes (`FF9StateSystem.EventState.gEventGlobal[i] = ...`), the same idiom
the F6 Flags tab ships. Selftest writes the mirror's position (player +250x) → the whole V2 loop
is SOLO-PROVABLE with plates spaced exactly 250 apart.

**Rung 1 — `[[coop]]` two-plate gate in `field.toml`:**
```toml
[[coop]]
plate_a = [-180, -60, -60, 60]   # x1, z1, x2, z2 -- axis-aligned rects in walkmesh units
plate_b = [70, -60, 190, 60]     # 250 apart center-to-center = solo-testable in selftest
set_flag = 8600                  # fires ONCE when both players stand on the two plates
text = "The twin seals release!" # optional message on fire
```
Compiles to TWO region entries (the proven `content.region.inject_region` lane — camera-switch
shape, Range tag-2 body runs EVERY frame while standing inside): plate A's body is
`if (!flag) { if (presence==1 && peerX/Z inside plate_b rect) { message; set flag } }` and
plate B's is the mirror (peer inside plate_a) — SYMMETRIC, so it fires no matter which player
takes which plate. The peer-side compare is a compound RPN AND chain (`T_ANDAND`) over the
reserved cells; the self-side containment IS the region. **No poller object, no new opcodes.**
The minted flag then gates doors/gateways/cutscenes through the EXISTING vocabulary — `[[coop]]`
only mints the flag. Each machine computes its gate locally and sets its OWN save's flag: zero
state sync, zero divergence problem (we author both sides).

Later rungs (same cells, pure kit work): `require_flag`/`scenario` gating on the block; "while
both present" LEVEL semantics (clear-on-exit); N-plate sets; a `peer_near = [x, z, r]` sugar;
per-plate `text`. Later engine rung if ever needed: a peer FLOOR/tri cell for multi-floor gates.

## Wire v3 (the one infrastructure change)

Typed frames over the same transports: `[type:u8][len:u16][payload]`.
- Type 0: position state (the current 38-byte payload) — latest-slot semantics, 30Hz keepalive.
- Type 1: battle state (B0) — latest-slot.
- Type 2: battle command / control (B1: command frames, slot claims, join/leave-assist) — **FIFO
  queue, never collapsed** (the streams are already reliable+ordered; only today's in-process
  latest-slot collapse loses data).
- Version byte bumps to 3; v2 peers are length/version-rejected — the established fail-safe
  ("mixed engine versions silently don't sync; update both machines").

Where the code lives: the engine patch lane (`s37-netsync-battle` extending `Memoria.Netsync` —
it needs per-frame Update + HUD access), staying independent of s22 like s36 does. The Overload
hub can contribute `OnBattleInit` seeding for B2, but the pillar is an engine patch by nature.

## Open questions (answer during B0/B1 build)

1. Guest input capture while standing on a field: reuse the F6 menu's input-swallow pattern;
   confirm no conflict when BOTH players fight their own battles simultaneously (assist simply
   unavailable — both sides send type-1 frames, neither can command).
2. Menu-data fidelity on the guest: ability lists/MP costs come from the host's units (roster
   frame) so a modded host (custom abilities) renders correctly on a vanilla-ish guest.
3. Double-cast/mix command shapes (`cmd[3]`+`cmd[0]`, `BattleHUD.cs:1665-1778`) — support or
   v1-exclude (Vivi dualcast in Trance etc.).
4. Trance on a guest-owned slot (menu changes shape mid-battle) — state frame carries trance;
   guest menu re-renders.
5. Whether B1 should ALSO offer an `IsPaused` hard gate on guest turns (a stricter option than
   the RemoteMenuOpen gauge-hold) — playtest call, default off.

## Dead ends (proven here — don't re-explore)

- **Deterministic lockstep** — global unseeded shared-with-cosmetics RNG (above).
- **A 5th battle participant** — fixed-size everything (above).
- **Recovering the PS1 2P code from the port** — stripped; no remnant in `FF9CFG`/input layer.
- **Faking controller input to drive the guest's slots** — pointless; `SetCommand` is the seam
  (the engine's own auto-battle/Berserk/debug-UI all use it).

## Recommended first milestone

**B0 + the B1 skeleton in one arc:** wire v3 framing → battle-state frames → overlay spectate
(playtest tick: watch the peer's fight live) → slot gating + command frames for ONE guest slot,
Attack/Defend only (playtest tick: guest wins a fight commanding one character) → then abilities
/items/targets. Every rung degrades to vanilla on disconnect. Label the whole lane
**experimental** in docs from day one.
