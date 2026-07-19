# Field-side co-op polish — surface sweep (2026-07-19)

> Scope: everything field-side NOT already owned by the five other polish-round agents (chests/talk
> suppression; gateway suppression + early warp; camera follow; platforms/ladders + teleport-to-host;
> dialogue/ATE mirroring). Section A collects every already-recorded follow-up/wart. Section B sweeps
> every other field-side interaction surface. READ-ONLY research — nothing in the engine tree or the kit
> was modified to produce this document.
>
> Every engine claim below was re-verified directly against `C:\gd\FFIX\Memoria\Assembly-CSharp\`
> (2026-07-19 tree state, DLL `E16DC1809417CA50`, s42 built/deployed but not yet in-game proven) rather
> than trusted from the studies/memory prose — citations point at the live file:line.

---

## A. THE ALREADY-PROMISED LIST

Legend: **DONE** = built + in-game proven · **SHIPPED-UNPROVEN** = code landed, awaits solo or two-machine
proof · **OPEN** = documented, not built.

| # | Item | Status | Source |
|---|---|---|---|
| 1 | Steam achievement funnel gate (`AchievementManager.ProcessAchievementReport`, keyed on `IsMirroringStory`) | **DONE** — two-machine proven 2026-07-15 | `inventory-authority.md` "ROAD A RUNG 1"; verified live at `AchievementManager.cs:101-116` (patch `s38-netsync-spectator-field.patch:1-19`) |
| 2 | ENCOUNT `0x2A` + ENCOUNT2 `0x8C` scripted-battle suppression on a mirrored script | **DONE** — two-machine proven 2026-07-15 (Evil Forest Plant Brain skipped on guest) | `inventory-authority.md`; verified live at `EventEngine.DoEventCode.cs:957-990` (s38 patch lines 20-53) |
| 3 | Field menu block — 4 `UIKeyTrigger` reads incl. Alt+F2 (party) / Alt+F5-F9 bypasses | **DONE** — two-machine proven 2026-07-15 | `inventory-authority.md`; verified live at `UIKeyTrigger.cs:480-484, 522-528, 675, 831` (s38 patch lines 54-106) — **this gate does NOT cover script-opened menus**, see §B.1/B.2 below |
| 4 | "The near-term cheap flip side" — suppress the guest's own field interactions (talk/chest/gateway) while following | **OPEN**, explicitly deferred behind B3 | `README.md` "THE SPECTATOR-FIELD PARADIGM" (PLAN.md banner) + memory line 613-615 — **this is the work item the other 5 agents are now executing; not re-swept here** |
| 5 | Cutscene-sync research note ("play the game without a player") | **OPEN**, research frontier not scheduled | `HANDOFF.md` "Cutscene sync — RESEARCH NOTE"; `inventory-authority.md` bottom section; memory lines 606-615, 696-700. Root cause: the guest's cutscenes fire off the GUEST's own local position/confirms, not the host's — two independent scripts that happen to agree, not one shared view |
| 6 | `[Netsync] SelfTestOffset = "dx,dz"` ini knob | **DONE** — built, deployed, solo-proven (the retest after fixing the checklist's own quoting bug) | `b36-round.md` Lane 6 (`537-598`); memory lines 1066-1071 ("mirror moved south" retest passed); live default `250,0` unless overridden, `NetSyncClient.cs` per b36-round §Lane 6 spec |
| 7 | s42: config-signature split (transport vs. behavior), the same-field kick, Diorama knob full deletion | **SHIPPED-UNPROVEN** — DLL `E16DC1809417CA50` built+deployed 2026-07-19, "NOT yet in-game proven" | memory lines 1192-1227 |
| 8 | B3.6 polish round (6 lanes: swirl+BGM songId carry wire v10, StatTick figures, spectate-panel-as-fallback, F6 opt-out intro-replay fix, `ValidateWireBoot` PatNum guard, SelfTestOffset) | **DONE** — solo round closed 2026-07-16 ("mirror moved south" retest passed), s41 emitted | `b36-round.md` (full spec); memory lines 1023-1082 |
| 9 | B3.6 remaining TWO-MACHINE boxes: host music (incl. a `Music:` fork override), host-silent (0xFFFE), tick numbers, panel-swap, opt-out across blips + the 3 older boxes (TranceFull booster, Plant Brain hidden-enemies, Feather Boots/Auto-Float) | Mixed — **DONE**: opt-out sticks, host music, trance-ENTER (closed 2026-07-19 round 2). **OPEN**: tick numbers, Plant Brain hidden-enemy recipe re-confirm, Feather Boots SA, host-silent bench | memory lines 1079-1082 (box list), 1130-1191 (round-2 results: panel-swap FAILED → diagnosed as the config-signature teardown bug, fixed by s42) |
| 10 | Guest "self-dress" idea — the guest sees THEMSELVES rendered as their own commanded party member (symmetric to `GhostAs`, which only re-skins the peer's ghost on the *other* viewer's screen) | **OPEN**, explicitly demoted/parked | memory line 485 ("optional guest-self-dress"); memory lines 456-461 explain why it was left as-is: symmetric re-skin needs a live control-Actor re-skin (HonoBehavior-teardown risk, cutscene-gesture T-pose) or a build-time `swap_player` on custom fields only — "leave as-is (you're a visiting spirit)" |
| 11 | `.NET bridge exe` (a compiled bridge binary instead of the Python one) | **DECIDED AGAINST** (dropped, not merely open) | memory lines 196-202: "every reachable co-op user has Python... DROPPED" |
| 12 | Engine-auto-spawn of the Python bridge (the DLL launches the bridge process itself) | **OPEN**, deliberately a "consideration only" | memory lines 199-200: "the user prefers the bridge owned by the GUI/terminal (visible lifecycle), so don't build it unprompted" |
| 13 | Panel/overlay UX: spectate panel becomes the no-diorama fallback (key on `Active`, never `Booted`) | **DONE** — built in B3.6, ground-truth corrected 2026-07-19 (the host never sees the panel in a follow session — README fixed) | `b36-round.md` Lane 3; memory lines 1167-1173 |
| 14 | The shared-bag verdict itself: Road B ("SHARED-BAG CO-OP" — push the mirror into the guest's real arrays + forward 4 write composites: item use, field ability use, equip, support-ability equip) | **OPEN**, explicitly "if we build it" — Road A ("SPECTATOR-STRICT") was chosen first and B was never started | `inventory-authority.md` "THE WORK (if we build it)" + "THE REAL DECISION" section |
| 15 | Rung-2 residue (post Road-A): the verbatim-fork chest still opens (item lands in a bag nothing reads, theater not corruption) | **OPEN** — explicitly OWNED BY THE CHEST/TALK-SUPPRESSION AGENT, not re-swept here | `inventory-authority.md` "Rung 2 — NOT shipped" |
| 16 | Rung-2 residue: SYSVAR 6 (guest's own gil readable by any mirrored script), the `0xD3` varfuncs, the `.eb` MENU opcode (a mirrored script can open a shop/save UI on the guest) | **OPEN** — the MENU-opcode item is the load-bearing finding for §B.1/B.2 below; confirmed still true on the current tree (see §B.1) | `inventory-authority.md` "Rung 2 — NOT shipped" |
| 17 | Rung-2 residue: F6/Booster self-gift (`Ff9mkDebugMenu.cs` give-item/give-gil, `BoosterSlider.cs`, `SettingsState.cs`) | **DOWNGRADED to inert-but-undecided** — "post-A a self-gift is inert, so it is no longer urgent" (ramp discards it) | `inventory-authority.md` "F6 / boosters — A DECISION IS NEEDED"; re-verified: zero `IsMirroringStory` hits anywhere in `Ff9mkDebugMenu.cs` today (see §B.7) |
| 18 | THE ENCOUNT HOLE will need REPLACING, not keeping, once B3 (diorama) ships broadly — under the diorama, ENCOUNT must *boot the diorama* instead of skip | **OPEN**, explicitly flagged as future work; **confirmed STILL UNCHANGED** as of the 2026-07-19 round-2 census | `diorama-lane.md` "★ THE ENCOUNT HOLE"; memory line 1148-1150: "the s38 ENCOUNT/ENCOUNT2 opcode gate is UNCHANGED since s38... the studies' 'B3 will replace this gate with a diorama boot' note NEVER SHIPPED" |
| 19 | The `Diorama` ini knob | **REMOVED** (not just deprecated) — 3/3 judge panel voted full delete, executed in s42 | memory lines 1185-1191, 1209-1211 |
| 20 | s42 test list (same-field kick, live behavior-config apply, transport-edit reconnect + the carried-over old boxes) | **OPEN** — "NEXT SESSION test list", not yet run | memory lines 1220-1225 |

---

## B. THE SURFACE SWEEP

Lane vocabulary used below: **SUPPRESS** (block the interaction outright, the shape the other agents are
building for chests/talk/gateways) · **MIRROR** (extend the read-compare wrap pattern, B1's proven
forwarding template) · **LEAVE** (already correctly handled by the exit-ramp/session architecture, no
action needed) · **OPEN QUESTION** (needs a design decision this sweep can't make alone).

### B.1 Save moogles / the `[[savepoint]]` menu

**What happens today:** talking to a moogle is dialogue (`B_KEYON`), which s38 deliberately leaves
untouched — a following guest CAN talk to a moogle. The moogle's dialogue choice then runs `Menu(4,0)`
(`EBin.event_code_binary.MENU`, opcode `0x75`) — verified live at
`EventEngine.DoEventCode.cs:2297-2311` — which calls `EventService.StartMenu(4, 0)` →
`EventService.FF9Menu_Command` → `case 4u: if (subId==0u) OpenSaveMenu()` (`EventService.cs:6-37`) →
`ChangeUIState(UIManager.UIState.Serialize)`. **None of this path checks `IsMirroringStory`** — the s38
menu gate lives entirely in `UIKeyTrigger.cs` (player-pressed Menu/Cancel keys), which is a completely
different code path from a script-invoked `Menu()` opcode. **So yes: a following guest can still open the
save menu by talking to a moogle.** A grep for `IsMirroringStory` across every file in `Global/*.cs`
returns exactly one hit — `SaveLoadUI.cs` — confirming no other menu screen (Shop/Party/Item/Equip/Ability)
has any netsync awareness at all.

Once the menu is open, the individual rows resolve differently:
- **Save row** → `SaveLoadUI` with `Type = SerializeType.Save`. `OnKeyConfirm` (`SaveLoadUI.cs:130-158`)
  DOES gate this: `if (this.type == SerializeType.Save) { if (IsMirroringStory || NetSyncDiorama.Booted) {
  refuse + deny beep } }` — verified live at `SaveLoadUI.cs:148-158`. **So the save-menu screen opens, but
  the actual save write is refused with a deny beep** — matches `PLAN.md`/`state-mirror-lane.md` §6/§11.
- **Tent row** — per `project-ff9-savepoint.md:106-107`, this is NOT a `SaveLoadUI` branch at all; it's
  the savepoint field's own `.eb` sequence (per-slot `if CURHP!=0 → SetHP/SetMP = CUR+(MAX+1)/2` then
  `RemoveItem(253,1)`), triggered directly from the dialogue choice, never touching `SaveLoadUI`. **This
  write is completely unguarded** — a following guest gets a real (if session-scoped) HP/MP heal and
  consumes a real Tent from their own bag. `RemoveItem` is `ITEMDELETE` (`EventEngine.DoEventCode.cs:1458`,
  census-confirmed unguarded in `inventory-authority.md`'s "THE `.eb` event lane" table).
- **Mogshop row** → `Menu(2, shopId)` → `EventService.OpenShopMenu` → `ChangeUIState(UIManager.UIState.Shop)`
  (`EventService.cs:16-18, 39-47`). Zero netsync awareness anywhere in the shop path (see §B.2).
- **Switch party row** → `Party(min, lockedMask)` (`EBin.event_code_binary.PARTYMENU`, `0xB2`, verified live
  at `EventEngine.DoEventCode.cs:2312-2340`) → `EventService.OpenPartyMenu` → `PartySettingUI`. Zero
  netsync awareness (`PartySettingUI.cs` has no `IsMirroringStory` hits either) — the guest can freely
  reassign their own party while following.

**Severity:** UX/theater, not corruption. Every write here (Tent's HP/MP+item, a shop purchase, a party
reassignment) lands on the guest's own session-scoped state, discarded whole by the autoload exit ramp on
session end (`NetSyncState.ExitMirrorToOwnSave`). The one exception, the manual save-confirm, is already
correctly refused.

**Right lane:** **SUPPRESS**, same lane as the chest/talk work already in flight. The natural hook is
identical to that agent's chest fix: gate the moogle's `B_KEYON` confirm (or the `Menu()` opcode itself,
which is the more general fix — it also covers Mogshop's `Menu(2,·)` and any other scripted `Menu()` call)
on `IsMirroringStory`. **Recommend coordinating with the chest/talk agent rather than building a second,
overlapping gate** — both need the same "which confirms are player-authored vs. mirrored-script-authored"
distinction. Note the save-CONFIRM refusal (deny beep) already ships and should stay even after a menu-open
suppression lands, as defense in depth.

### B.2 Shops (`opens_shop` / stock shop dialogue → shop UI)

**What happens today:** confirmed reachable exactly as above — `Menu(2, shopId)` opens `ShopUI` with zero
netsync gating (`grep IsMirroringStory Global/ShopUI.cs` = no hits). `inventory-authority.md`'s census
already flags `ShopUI.cs:391/395` (buy, **no gil floor guard** — `gil -= …` can UInt32-underflow to
~4.29e9) and `:446/449/451` (sell, which DOES clamp). A following guest can walk into any shop dialogue
reachable via dialogue/`B_KEYON` (untouched by s38) and buy/sell against their own gil/bag.

**Severity:** UX/theater. Gil is a raw public field (`PARTY_DATA.cs:17`) with no funnel and ~15 write sites
(per `inventory-authority.md`); a shop purchase, even an underflowed one, is entirely session-scoped and
wiped by the autoload exit ramp (which does a full `Serializer.Autoload` from disk — disk was never
touched, since autosave is also blocked while mirroring). No corruption path exists today.

**Right lane:** **SUPPRESS** — same fix as B.1 (gate `Menu()` at the opcode, or gate the shop-NPC's
confirm alongside chests/talk). Worth flagging explicitly to whichever agent builds the general menu-open
gate: Mogshop and stock shop NPCs share the identical `Menu(2,·)` call shape, so one fix covers both.

### B.3 Mognet letter delivery (writes flags + bag)

**What happens today:** per `project-ff9-mognet-protocol.md:82-94`, Mognet's entire state lives in
`gEventGlobal` — the same 2048-byte array the state-mirror overwrites wholesale on every field load
(`NetSyncState.cs` masked `Array.Copy`, applied at `HonoluluFieldMain.cs:135`). A following guest CAN
accept/read a letter via dialogue (untouched by s38), which writes `Byte[1064+k]`/`Byte[1079+k]` etc.
locally. **This is the exact LIFETIME ASYMMETRY bug class already documented for the verbatim-fork chest**
(`inventory-authority.md` "★ THE LIVE DEFECT"): the write survives only until the next field load, at
which point the host's mirrored snapshot silently overwrites it back to the host's own mognet state. A
Mognet acceptance a guest makes today is functionally identical to the chest exploit's *shape* (though not
its "farmable" severity, since there's no repeatable item gain here — reading a letter twice is a pure
re-read per the memory's "pure re-reads" note) — it just doesn't stick past one field transition.

**Severity:** UX/theater (visually confusing — "I read that letter" reverts on the next room), not
corruption; the exit ramp's whole-array discard covers it regardless.

**Right lane:** **SUPPRESS**, same mechanism as B.1/B.2 (moogle dialogue → `B_KEYON`/`Menu()` gate) — Mognet
Central and every mailbox moogle are dialogue-driven the same way a save moogle is. No separate fix needed
if the general moogle-interaction gate lands; flagging here so the chest/talk agent's fix explicitly
includes Mognet's moogle, not just save moogles and chest containers.

### B.4 World map — can the guest follow the host there at all?

**Verified from source, not just cited:** the position-broadcast scope gate is
`Boolean onField = fld > 0 && ee != null && ee.gMode == 1 && ee.fieldmap != null;` at
`NetSyncClient.cs:640` — **strictly `gMode==1`**. `gMode==3` (world map) does NOT count as `onField`
anywhere in the broadcast/follow path. The only place `gMode==3` appears at all in `NetSyncClient.cs` is
line 604, inside the **exit-ramp's** "safe to autoload" check
(`(e2.gMode == 1 && e2.fieldmap != null) || e2.gMode == 3` — world map is a second safe moment to reload,
alongside a field; nothing else). So: **when the host exits to the world map, their broadcast field
becomes the field-0 sentinel** (per the existing co-op-everywhere design, `ee.gMode == 1` gate feeding the
sentinel path). Confirmed at `FollowHostTick` (`NetSyncClient.cs:1073-1118`): `if (!rs.Valid || rs.Field <=
0 || rs.Field == 65535) { _followCandidate = -1; return; }` — **the guest simply does nothing** when the
host's broadcast field is ≤0. The guest is not warped anywhere; they stay exactly where they were on their
last field until the host's broadcast field becomes positive again (i.e. the host enters a new field).
**This is exactly the "guest stays behind" gap the task description predicted, and it falls out mechanically
from the existing `gMode==1` scope gate — it was never specifically designed or excluded, it's a natural
consequence of "ghosts/follow only exist on fields."**

A `grep -rn "vehicle\|WMWorld\|WorldMap" Memoria/Netsync/*.cs` returns **zero** vehicle-aware or
world-map-aware code anywhere in the netsync tree (only the exit-ramp's `gMode==3` check and a scene-name
string comparison in the diorama fence, `NetSyncClient.cs:872`, `if (scene == "FieldMap" || scene ==
"WorldMap")`, which is unrelated to following). The overworld terrain/vehicle *mechanism* is mature
(s34 loose-mesh override, s39 self-heal, the `.eb`-owns-policy vehicle system per
`project-ff9-overworld-vehicles.md`), but **none of it is wired to netsync** — extending following onto
the world map is a green-field research item, not a small patch. It would need at minimum: a ghost
renderer for `WMWorld` (a different scene/camera/scale regime than field characters — the s36 ghost recipe
is field-specific, per `project-ff9-multiplayer-injector.md` lines 30-51), a position frame that carries
world coordinates instead of field-local ones, and a decision about vehicle state (does the guest's ghost
need to render mounted on the host's chocobo/ship/airship model?).

**Severity:** none — this is a designed (if implicit) gap, not a bug. No writes, no desync, just an absent
feature.

**Right lane:** **OPEN QUESTION** / documented frontier, not a polish-round item. Recommend the synthesis
doc state explicitly: "world-map following is out of scope for this round; the gap is structural
(`gMode==1`-scoped broadcast) and the guest correctly freezes in place rather than doing anything
dangerous — this is the safe failure mode, not an oversight to patch reactively."

### B.5 Vehicles (host boards chocobo/ship/airship)

Directly downstream of B.4: since following requires `gMode==1` (a field), and boarding a vehicle happens
on the world map (`gMode==3`), **a host boarding a vehicle is indistinguishable, from the guest's
position-broadcast point of view, from any other world-map excursion** — the guest just sees the host's
broadcast field drop to the sentinel and freezes in place, exactly as in B.4. No vehicle-specific code
exists in `Memoria/Netsync/` (confirmed by the same grep as B.4). There is no separate vehicle bug here —
it's the same gap, restated.

**Severity:** none (same reasoning as B.4).

**Right lane:** folds into B.4's **OPEN QUESTION** — do not treat as a separate work item.

### B.6 Chocobo Hot & Cold, card games, minigames

**Chocobo Hot & Cold** (`[savepoint.mognet]`/`[chocobo]` per `project-ff9-chocobo-hot-cold.md`) is a
declarative field-lane on a verbatim forest fork — mechanically it's ordinary field dialogue + item
rewards, same category as B.1's Tent row (unguarded `.eb` writes, session-scoped). Not independently
verified beyond that; no chocobo-specific netsync code exists.

**Tetra Master / card games:** boots via `EBin.event_code_binary.MINIGAME` (`0xAE`, `"TetraMaster"`),
verified live at `EventEngine.DoEventCode.cs:2347-2355` — `EventService.SetMiniGame(minigameFlag)` (sets
`FF9StateSystem.Common.FF9.miniGameArg`) then `return 7` (a special dispatch code, same category as
`return 1` for MENU or `return 8` for GAMEOVER — hands control to a mode-switch outside `DoEventCode`).
**Zero `IsMirroringStory` references anywhere in `EventService.cs` or the `MiniGameState.cs`/
`QuadMistGame.cs` boot path** — same un-gated shape as MENU (B.1). Cards themselves are explicitly
"deliberately local" per the shared-bag census (`inventory-authority.md`: `TryItemCount` falls through at
`NetSyncParty.cs:309` for cards — the mirror doesn't even attempt to read the host's deck), so a card game
played by a following guest uses the guest's own (session-scoped) deck; no host-state confusion, just an
un-suppressed interaction like every other dialogue-gated menu.

**Achievements funnel:** already covered map-wide by `AchievementManager.ProcessAchievementReport`'s single
choke-point gate (§A item 1/2) — this covers minigame achievements too (the funnel is opcode-agnostic,
gated at the one Steam-call site every channel crosses). The task description's "EMinigame" concern is
specifically addressed in `inventory-authority.md`'s note that `ITEMADD` fires five `EMinigame` achievements
that must NOT be gated at `FF9Item_Achievement` (too narrow) — confirmed the shipped gate is at
`ProcessAchievementReport`, the correct, general choke point.

**Severity:** UX/theater across the board (session-scoped local writes, discarded at the ramp); no
achievement-escape risk (already closed).

**Right lane:** **SUPPRESS**, same general "block a mirrored-story guest from opening ANY dialogue-summoned
menu/minigame" fix as B.1-B.3. Do not build a separate minigame-specific gate — one fix at the `Menu()`/
`MINIGAME` opcode level (or at the dialogue-confirm layer the chest/talk agent is already touching) covers
save/shop/mognet/chocobo/cards uniformly.

### B.7 The F6 debug menu on the guest

Verified live: `grep -n "IsMirroringStory" Global/UI/UIKey/Ff9mkDebugMenu.cs` returns **zero hits**. The
menu's only netsync awareness at all is diorama-specific (`NetSyncDiorama.Booted`/`BootBlockedReason`,
`Ff9mkDebugMenu.cs:502-536, 644-715` — F6's own "Battle diorama" buttons correctly refuse/adapt). Everything
else — Warp, teleport, disc switch, Cheats, Flags (including raw byte pokes into `gEventGlobal` at
`Ff9mkDebugMenu.cs:1966-1985`), and the whole-array **Snapshot/RestoreSnapshot** pair
(`Ff9mkDebugMenu.cs:2141-2149+`) — is completely unaware a mirroring session exists.

Per-feature read:
- **Warp / teleport / disc switch:** low real risk. A stray F6 warp off the host's field would just get
  chased down by `FollowHostTick` on the next tick (same debounce as a normal field transition) — cosmetic
  hiccup, not a bug. Fine to leave ungated; this is user-facing debug tooling the human explicitly reaches
  for, and the follow machinery is designed to reconcile.
- **Cheats (give item/gil, boosters):** per `inventory-authority.md`'s own re-framing, now **inert, not
  urgent** — every write lands on the guest's session-scoped state and the ramp discards it, exactly like
  every other surface in this document. No new severity found.
- **Flags editor / raw byte pokes:** low risk BUT interacts oddly with the mirror's own apply timing — a
  live poke mid-field visibly changes the guest's rendered state until the *next* field load, when the
  host's snapshot silently overwrites it back (identical shape to B.3's Mognet finding). Cosmetic
  confusion at worst.
- **★ Snapshot / RestoreSnapshot — the one finding worth flagging with real (if narrow) severity.** These
  two buttons operate on a COMPLETELY SEPARATE buffer from the state-mirror's own capture/restore
  machinery (`NetSyncState.CaptureLiveStory`/`RestoreLiveStory`, which the mirror itself no longer even
  uses post-2026-07-15 redesign — see §A's exit-ramp history). Trace the escape: (1) guest is
  mirroring — `IsMirroringStory` true (`NetSyncClient.cs:269-272`); (2) guest presses F6 "Snapshot" — this
  captures the CURRENT `gEventGlobal`, which at that moment holds the **host's** mirrored story, into the
  F6 menu's own private buffer; (3) session ends — the exit ramp fires, sets `_storyMirroring = false`
  (`NetSyncClient.cs:611`) and reloads the guest's own pristine autosave
  (`NetSyncState.ExitMirrorToOwnSave`, `NetSyncClient.cs:617`); (4) `IsMirroringStory` is now **false**, so
  the manual-save block (`SaveLoadUI.cs:154`) no longer applies; (5) guest presses F6 "RestoreSnapshot" —
  this overwrites the freshly-reloaded pristine array with step (2)'s stale buffer, **which still contains
  the host's story bytes**; (6) guest saves normally (now unblocked) → **the host's mirrored story is
  written to the guest's permanent save file.** This is a real escape from the save-safety guarantee, but
  it requires a deliberate 4-step user action sequence through a debug tool explicitly aimed at power users
  — not a passive/accidental bug.

**Severity:** everything except Snapshot/RestoreSnapshot is UX-only. Snapshot/RestoreSnapshot is a genuine,
if narrow and deliberate-action-gated, save-corruption path.

**Right lane:** most of F6 needs nothing (**LEAVE**). Recommend **SUPPRESS** (or at minimum a loud
in-tool warning) specifically on Snapshot/RestoreSnapshot while `IsMirroringStory` is true, OR clear the F6
snapshot buffer at the same moment the exit ramp fires (mirroring the discipline the state-mirror's own
`_ownStory` machinery used to have before it was replaced by the whole-array reload design). This is a
**genuinely new finding** not present in any prior study doc — worth a dedicated one-line callout in the
synthesis.

### B.8 The `[[coop]]` plates/gates under the coming suppression round

Confirmed still deliberately untouched: `inventory-authority.md` "Deliberately NOT blocked: tread regions
(tag 2 — `[[coop]]` plates + gateways) and dialogue/`B_KEYON`." The mechanism (peer presence/position
broadcast into `gEventGlobal` bytes 2032-2039, read by an ordinary tag-2 region body) is completely
independent of the menu/shop/mognet gates above — it never opens a menu, never touches the bag, and both
machines compute their own flag locally from the peer's broadcast position. **This must keep working
un-suppressed** as the other agents build interaction gates — flagging explicitly for the synthesis: any
general "block dialogue/menu while mirroring" gate must NOT accidentally catch tread-region bodies (a
different opcode class entirely — `TreadQuad`, not `B_KEYON`/`MENU`), and any general "block gateways while
following" gate (owned by the gateway-suppression agent) must be scoped to NOT break the Twin Altar's held
east-arch door, which IS a flag-gated `[[gateway]]` fed by a `[[coop]]`-minted flag — suppressing gateway
firing wholesale for a following guest would break the one showcase piece that currently works
two-machine. **Interplay note for the synthesis doc, not a bug**: the coop-cell flags (2032-2039) sit
inside the reserved-and-masked window the state-mirror explicitly skips copying
(`state-mirror-lane.md` §4 "Mask the reserved windows... bytes 2032-2041") — so the mirror and the `[[coop]]`
cells already coexist safely today; no new gate should touch that masked range.

### B.9 Field-scripted PARTY changes (mirrored `B_PARTYADD`/party ops on the guest)

Two DIFFERENT opcodes here, verified to behave differently:

- **`B_PARTYADD` (value-function, op 109)** — `EventEngine.partyadd(x)` (`EventEngine.cs:887-905`) —
  **is naturally protected today**, not by design but by a fortunate composition: `partyadd` internally
  calls `this.partychk(x)` FIRST and only writes (`ff9play.FF9Play_SetParty`) if `partychk` returns false.
  `partychk` (`EventEngine.cs:872-885`) itself is **already the party mirror's read-wrap** —
  `if (Memoria.Netsync.NetSyncParty.TryPartyChk(charId, out mirrored)) return mirrored;` — so when a
  mirrored script asks "do I have Vivi?", it gets the HOST's answer. If the host has already recruited the
  character (the normal in-lockstep case), `partychk` returns true, `partyadd`'s guard trips, and the
  write is silently skipped. **The party read-mirror (rung 2, already shipped) incidentally neutralizes
  most PARTYADD writes for free** — a nuance not called out in any existing study doc.
- **`PARTYDELETE` (opcode `0xDD`)** — verified live at `EventEngine.DoEventCode.cs:2723-2735` — is
  **unconditional**, no `partychk` guard anywhere in its body: `ff9play.FF9Play_SetParty(party_id,
  CharacterId.NONE)` fires whenever the character is found in the GUEST's own local `party.member[]`,
  regardless of what the mirror says. A story beat that scripts a character temporarily leaving the party
  (a common FF9 pattern) will genuinely remove that character from the guest's own real, local party
  during the session.

**Severity:** UX/desync, not corruption (discarded at the ramp like everything else) — but potentially
more disruptive than the other surfaces in this document, since a `PARTYDELETE` could drop the guest below
a usable party size mid-session (cosmetic softlock-adjacent: no battle-blocking risk since the guest isn't
in the host's actual battle roster, but menus/UI could look broken with fewer members than expected).

**Right lane:** **MIRROR** — the existing read-wrap pattern (`partychk`/`PARTY_MEMBER`/`B_HAVE_ITEM`) is
exactly the right shape; `PARTYDELETE` is the one write in this family that fell outside it. Recommend
wrapping `PARTYDELETE` the same way the `.eb` write lane's `ITEMADD`/`ITEMDELETE`/`GILADD`/`GILDELETE`/
`PLAYER_EQUIP` already need wrapping per `inventory-authority.md`'s open residue (§A item 16) — this is one
more opcode for whichever future round builds "suppress the `.eb` write lane on the guest since the host
performs the same write authoritatively" (the census's own recommended fix shape for that whole opcode
family).

### B.10 Gil writes by mirrored scripts

Already censused exhaustively in `inventory-authority.md`'s "THE CENSUS" table (§ "The `.eb` event lane"):
`GILADD`/`GILDELETE` (opcode `0xCE`/`0xCF`, verified live at `EventEngine.DoEventCode.cs:2616-2628`) — both
unconditional, no partychk-style protection exists for gil (gil has no read-mirror at all; `NetSyncParty`
doesn't carry it — `inventory-authority.md`: "SYSVAR 6 (the guest's own gil, readable by any mirrored
script — needs a wire section)" is still listed as open residue). **Confirmed unchanged** on the current
tree — no gil-related gate exists anywhere in `Memoria/Netsync/`.

**Severity:** ramp-scoped, no escape found (gil is not part of the achievement funnel and not
save-persisted until the (blocked) manual save or the (blocked) autosave). Purely session-scoped drift.

**Right lane:** **MIRROR/SUPPRESS**, same opcode-family fix as B.9's `PARTYDELETE` — fold `GILADD`/
`GILDELETE` into the same "`.eb` write lane" suppression that `ITEMADD`/`ITEMDELETE`/`PLAYER_EQUIP` already
need. No new escape path found beyond what's already documented.

### B.11 Other opcodes found beyond the given list (grepped `EventEngine.DoEventCode.cs`'s full opcode
table for other world-writing codes a mirrored script can fire)

| Opcode | What it does | Gated today? | Severity/lane |
|---|---|---|---|
| `DISCCHANGE` (`0xAC`, `EventEngine.DoEventCode.cs:604-624`) | Changes the disc (`_ff9fieldDisc.FieldMapNo`), optionally shows the PSX disc-change screen if `Configuration.Interface.DisplayPSXDiscChanges` | No | A mirrored disc-transition beat (end of disc 1, etc.) would change the GUEST's own disc state too — session-scoped, but potentially jarring (a loading-screen interruption) if `DisplayPSXDiscChanges` is on. **SUPPRESS** alongside the other `.eb` write-lane opcodes; low-frequency (fires only at major story pivots) |
| `MAXAP`/`CLEARAP` (`0xF4`/`0xF3`, learn/unlearn ability, `:2830-2845`) | Directly sets a character's AP for an ability | No | Session-scoped ability-learn drift on the guest's own characters (mirrors a story-taught ability). **MIRROR/SUPPRESS**, low severity |
| `PLAYERNAME` (`0xDE`, rename a party member, `:2744`) | Sets a character's display name | No | Purely cosmetic, session-scoped. **LEAVE** — not worth gating |
| `FULLMEMBER` (`0xB4`, `SetPartyReserve`, `:2709-2722`) | Rebuilds party reserve eligibility (deletes then re-adds by mask) | No | Session-scoped party-roster-adjacent write, same family as B.9. **MIRROR/SUPPRESS** alongside `PARTYDELETE` |
| `CLEARSTATUS`/`ADD_STATUS`/`REMOVE_STATUS` (`0xD9` + battle-status opcodes, `:2846-2907`) | Cures/applies/removes a status on a field-context unit | No | Cosmetic/session-scoped; low real impact on a field (no battle context to corrupt) | 
| `WPRM` (`0xC4`, `"RunWorldCode"`, `:2498`) | World-map effects (weather/music/chocobo call/auto-pilot) | No | **Unreachable in practice** — per §B.4, a following guest is never ON the world map while mirroring a field-scoped script, so this opcode has no realistic trigger path today. Noted for completeness, not actionable |
| `SPS`/`SPS2` (`0xB3`/`0xDA`, model-effects scripting, `:2378-2379`) | Runs SPS particle/model-effect code | No | Cosmetic-only, no save-state writes — already known fork-fidelity class (`project-ff9-sps-fork.md`), unrelated to co-op specifically. **LEAVE** |
| `VIBSTART`/`VIBACTIVE`/`VIBTRACK`/`VIBRATE`/`VIBFLAG`/`VIBRANGE` (`0xF6-0xFC`, `:2988-3023`) | Controller vibration | No | Zero save-state impact. **LEAVE** |
| `SETMAPNAME`/`RESETMAPNAME` (`0xB0`/`0xB1`, `:2368-2377`) | Changes the field's displayed name | No | Cosmetic text only. **LEAVE** |
| `MINIGAME` (`0xAE`) | See §B.6 | No | Covered in §B.6 |

**Method note:** the full opcode table (`grep "case EBin.event_code_binary\."
EventEngine.DoEventCode.cs`) was read in its entirety; the rows above are every write-shaped opcode not
already covered in §A/§B.1-B.10 or owned by another polish-round agent (chest/dialogue-adjacent opcodes
like `ITEMADD`/`ITEMDELETE`/`PLAYER_EQUIP` are re-flagged in B.9/B.10 only because they compose with the
party/gil findings, not as new discoveries — they're already censused in `inventory-authority.md`).

---

## Summary of the worst finds (for the synthesis doc)

1. **The s38 menu gate does NOT cover script-opened menus** (§B.1). A following guest can still walk up to
   a save moogle, Mognet moogle, or shop NPC and — via dialogue, which is deliberately untouched — trigger
   `Menu()`/`MINIGAME` opcodes that open the Save/Tent/Mogshop/Party/Card-game UI locally. The manual SAVE
   confirm specifically is blocked; everything upstream of it (opening the menu, Tent's HP/MP+item write,
   shop purchases, party reassignment, mognet reads) is wide open. All of it is session-scoped/ramp-discarded
   — theater, not corruption — but it's a bigger surface than "the chest still opens," and the fix (gate
   `Menu()`/`MINIGAME` at the opcode, or the moogle/shop-NPC's `B_KEYON` confirm) is the same shape and
   should be coordinated with the chest/talk-suppression agent rather than built twice.
2. **A real, if narrow, save-corruption path through F6's Snapshot/RestoreSnapshot** (§B.7) — a 4-step
   deliberate sequence (Snapshot while mirroring → session ends → RestoreSnapshot → Save) can write the
   HOST's story into the guest's permanent save, bypassing the manual-save block entirely because it fires
   after `_storyMirroring` has already gone false. This is a genuinely new finding, not in any prior study
   doc, and worth its own line in the synthesis.
3. **`PARTYDELETE` and `GILADD`/`GILDELETE` are unconditional writes with zero mirror protection**, unlike
   `PARTYADD` which is accidentally shielded by its own internal `partychk` call. A scripted "character
   leaves the party" story beat will genuinely empty a slot in the guest's own local party mid-session.
4. **World-map following is a clean, structural non-feature, not a bug** (§B.4/B.5) — it falls directly out
   of the existing `gMode==1` broadcast scope, the guest fails safe (freezes in place, no crash, no
   corruption), and zero vehicle/world-map-aware netsync code exists to build on. Recommend the synthesis
   explicitly scope this out rather than let it read as an oversight.
