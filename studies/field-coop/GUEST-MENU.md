# Guest access to the main menu: equipment, abilities, items

**Status:** research only, 2026-10-30. Nothing is built. No engine, kit or wire change. The owner wants
the guest to open the main menu during a co-op session, so they can manage equipment, support abilities
and items for the party they fight with. The specifics were not decided up front, so this study lays out
the options and the considerations, and ends with the owner's decisions.

**Owner decisions answered 2026-10-31** (§15). **Build held until s164's two-PC test:** rung 0 shares
s164's follow code and needs a wire bump, so building it now would put two changes into one in-game test.

Engine paths are relative to `Assembly-CSharp/` in the shared Memoria clone. **Line numbers come from that
clone's working tree on 2026-10-30, which carries the patch stack through s163 and may carry s164 edits
that were being built at the time.** Re-read before building.

Related:
- [`../battle-coop/inventory-authority.md`](../battle-coop/inventory-authority.md): the July study this
  builds on. It settled who owns the bag, counted every write site, and named this feature "Road B".
- [`COMMS-MENU.md`](COMMS-MENU.md) §2: the open/refuse/auto-close predicates for a guest-side menu. They
  apply here almost unchanged.
- [`FIELD-SWAP-TIMING.md`](FIELD-SWAP-TIMING.md): the guest's field-swap lag, which a menu open on the
  guest makes longer.
- [`../battle-coop/B4-B5-DESIGN.md`](../battle-coop/B4-B5-DESIGN.md): the guest's stock battle menu, the
  closest working precedent (stock UI on the guest, every commit caught and forwarded).

## Decision summary (owner-answered 2026-10-31)

| # | Area | Decision |
|---|------|----------|
| 1 | Architecture | Option A: the stock menu on the guest, over a copy of the host's party; each confirm is forwarded and the host does the write |
| 2 | First build | View-only menu (rung 0), then support abilities (rung 1) |
| 3 | Characters | The whole party |
| 4 | Both players in menus | Allowed; the host rechecks, so a stale guest action is refused with a buzz and a line |
| 5 | Party order and row | Host only. Order changes which characters the guest commands |
| 6 | Item sort | Sorts the guest's view only; never reorders the host's bag |
| 7 | Battle start while the guest is in the menu | Close the guest's menu at the host's battle cut |
| 8 | Host leaves the field while the guest is in the menu | Close the guest's menu at once, then follow (the owner's pick over the study's "lag and follow on close") |
| 9 | Where the copy lives | In the guest's real arrays, only while the menu is open, restored on close |
| 10 | What the host sees | A one-line message on each applied guest change |

## 1. Where it stands today

The guest's menu is refused on purpose. Road A (s38) added the gate and s121 made the refusal audible:

- `Global/UI/UIKey/UIKeyTrigger.cs:699-702`: the Menu key. A mirroring guest gets `NetSyncField.RefuseMainMenu()`
  (SFX 102 plus one line on FieldHUD and WorldHUD, silent elsewhere).
- `UIKeyTrigger.cs:510` and `:552`: the Alt-hotkey shortcuts that skip `OnKeyMenu` (Alt+F2 party,
  Alt+F5-F9).
- `UIKeyTrigger.cs:869`: the second Menu-key read.

The audible-or-silent choice is `NetSyncField.cs:664`. (The world map's other refusals at
`Global/World/WorldHUD.cs:156` and `:238` are the autopilot pick and the full map, not the main menu.)

All four reads check `NetSyncClient.IsMirroringStory`. The predicate is true from the first mirrored field
load until the exit ramp fires.

**Why it was blocked.** The stock menu reads the guest's own party and bag, while every field script
around it answers from the host's mirrored story. Anything the guest used or equipped there was a write
the host never saw, and the item-farm defect in the July study came from exactly that kind of split.

**The rule the July study settled.** The host's save is the only one that persists. Two-way editing has no
safe form in this engine (§3). So the guest sends what it wants to do, and the host does it. The owner's
call then was "A first, then B". Road A shipped; this feature is Road B.

## 2. What already exists to reuse

| Piece | Where | What it gives this feature |
|---|---|---|
| The host's party streams every 150 ms | Wire sections 1-3, `Memoria/Netsync/NetSyncParty.cs:9-40` | Per member: character, level, row, HP/MP, 5 equipment slots, name. Since v9 also the pre-support-ability base stats, ability capacity, statuses, trance and the equipped support-ability set. Section 3 is the bag |
| Copying the host's party into the guest's live data | The battle diorama's seat, `NetSyncDiorama.cs:2896-2914` (s154) | THE SEAT LAW: seat from the boot's own host frame, never from the field-load parse. Already done safely inside battle |
| Intent → host recheck → host applies with stock code | Battle item use (B1); the guest's stock battle menu (B4/B5) | The proven template, with zero item writes anywhere in `Memoria/Netsync/` |
| The guest's save cannot keep session state | Save block (`SaveLoadUI`), autosave block, the exit ramp | Seating host data into the guest's arrays changes what the guest sees, not what it keeps |
| Positional ownership plus LeaderGuard | `[Netsync] GuestSlots` (s143) | The existing answer to "which characters are the guest's" |
| Re-dress waits for a closed menu | `NetSyncClient.cs` ~12057 | A precedent for party changes landing while a menu is open |

What the stream does not give: it is parsed only at a field load (`ParseSections` has one production
caller, the field-load seam), so the guest's copy goes stale between loads. §9 covers the missing fields.

## 3. The core constraint

**The stock screens read the raw arrays.** `ItemUI`, `EquipUI`, `AbilityUI`, `StatusUI` and `MainMenuUI`
read `FF9StateSystem.Common.FF9.party`, `.player` and `.item` directly. The July count found 18 raw bag
touches plus in-place reordering, and there is no accessor to wrap. The read-compare trick that rung 2
used for `B_PARTYCHK` and `B_HAVE_ITEM` cannot reach them. To show the host's party in the stock UI, the
host's data has to be copied into the guest's real arrays (seated).

**The stock code has no check-before-commit point.** Equipping does `FF9Item_Add(old, 1)` first and only
then `if (FF9Item_Remove(new, 1) != 0) equip = new` (`Global/EquipUI.cs:193/196`, Optimize at
`:1249/1252`, `Global/ff9feqp.cs:99/100`). If a remote change removes the new piece between the menu
drawing and the confirm, the character keeps the old piece and the bag gains a copy. That cannot happen
single-player because the menu only lists items with a count above zero. Item use heals first and then
removes the item with the return value ignored (`Global/ItemUI.cs:431`).

So the real change must happen on the host, inside the host's own call, right before the add or remove.
Every option below keeps to that.

## 4. Four ways to build it

### Option A: stock menu plus forwarding each action (recommended)

Seat the host's party and bag into the guest's arrays while the menu is open. Catch each confirm before
the stock code applies it and send it as an intent. The host rechecks it live against its own state and
applies it through its own stock primitives. The result comes back on the next state frame and re-seats
the guest's copy.

- For: the stock look (the owner moved battle from digit menus to the stock menu for this reason). The
  same template as B1 and B4. Safe even with both players editing at once, because the guest never writes
  anything that counts. Nothing is left uncommitted on the guest, so a forced close loses nothing.
- Against: the most work. About six kinds of action, each needing its own small host helper (§6). The
  support-ability screen has no single function to call; its boost-hierarchy loop is inline in
  `AbilityUI`.

### Option B: stock menu plus a lock while the guest edits

The guest's menu opening locks the host's menu. The guest edits a local copy with unmodified stock code.
On close, the host checks the net change (bag deltas, equipment slots, support-ability sets) and applies it.

- For: the stock UI runs untouched. One merge instead of many intent types.
- Against: the July study called a global lock host authority with worse UX and a worse failure mode.
  If the guest's game dies, the host's menu stays locked (THE PEER-ALIVE LAW), so it needs a lease
  timeout. The host's field scripts still change the party and bag during the lock (chests, `ITEMADD`,
  `PLAYER_EQUIP`, party changes), so the merge needs a three-way base. A battle can start mid-edit with
  the guest's work uncommitted.

### Option C: a custom co-op panel

A purpose-built panel, like the old battle digit menus, built from wire data and sending intents.

- For: the smallest surface, only the actions chosen. No seating.
- Against: a non-stock look, and equipment stat comparisons would have to be rebuilt by hand.

### Option D: view-only stock menu

Seat the data and allow browsing; refuse every confirm that changes something, with the buzz.

- For: cheap, and it proves the seat and restore safely.
- Against: not the feature on its own. It is rung 0 of Option A.

### Ruled out: the guest drives a menu on the host's machine

The game has one `UIManager` and one set of menu scenes, and the host's screen would show the guest's menu.

## 5. Which characters the guest may edit

The possible answers:
1. The whole party.
2. Only the guest's `GuestSlots` characters.
3. A host setting, `[Netsync] GuestMenu = off/view/own/all`, which covers both and lets the host turn it off.

What complicates answer 2:
- Ownership is positional, and story scripts reorder the party (s143: field 257 seats
  [Blank, Zidane, Vivi, Steiner], 261 leaves [Garnet, Zidane, Vivi, Steiner]). "The guest's characters"
  changes under them as the story moves.
- The **Order** screen swaps `party.member[]` in place and flips rows (`Global/MainMenuUI.cs:637-649`).
  A guest reorder would change which characters the guest commands in battle. Keep Order host-only.
- Intents must name a character by `CharacterId`, never a party slot index. The slot index is what
  reorders change.

## 6. Screen by screen

| Screen | What it writes | Risk | Notes |
|---|---|---|---|
| Status | nothing | none | Needs EXP and level bonuses, which are not on the wire (§9) |
| Ability: equip support abilities | the character's capacity and support-ability bits (`AbilityUI.cs` ~419-437, ~628-665) | low, no bag | Needs the per-ability AP table to show what is learned. The s154 seat already applies a support-ability set to a character, so the host helper has a starting point |
| Ability: use in the field (Cure, Life) | caster MP, target HP and status (`AbilityUI.cs` ~512-529) | medium | Two characters change in one action |
| Equip, remove, Optimize | bag plus equipment slot (`EquipUI.cs:193/196`, `:235`, `:1249/1252`) | high | Both must change in one step on the host. Model the helper on `PLAYER_EQUIP` (`Global/Event/Engine/EventEngine.DoEventCode.cs:3189-3201`: headless, keyed by `CharacterId`, `equip.Change` then `FF9FEqp_UpdatePlayer`) plus a count check first |
| Item: use | target HP and status, then the bag (`ItemUI.cs:431`) | medium | `SFieldCalculator.FieldCalcMain` is UI-free and host-callable, but the remove is a separate statement, so the host needs a small helper. Gysahl Greens (`ItemUI.cs:321-327` and its dialog/coroutine path) cannot be driven remotely: refuse them |
| Item: key item use | `FF9Item_UseImportant` (`ItemUI.cs:855`) | low | Reached directly, bypassing the other four bag functions |
| Item: sort | reorders the bag in place | odd | Would reorder the host's bag. Keep sorting local to the guest's view |
| Order and row | `party.member[]` and `info.row` | ownership | See §5 |
| Card | the guest's own cards | none | Cards are deliberately local |
| Config | local settings | low | The guest's own random encounters are already off while following (`SettingsState.cs:53-54`) |
| Folklore, Journal | nothing | none | Read story flags, which hold the host's story while mirroring |
| Save | blocked | n/a | Stays blocked |
| Shops, synthesis | gil and bag | high | Opened by the `.eb` Menu opcode on the host's scripts, not from the main menu. Out of scope; gil has no single write funnel (`PARTY_DATA.gil` is a raw field) |

Memoria's in-battle main menu stays refused on the diorama. Its refusal is already silent there
(`NetSyncField.cs:664`; selftest row `:791`).

## 7. Timing: the guest's field freezes while the menu is open

`FieldHUD.Hide` calls `SetEventEnable(false)` (`Global/Field/FieldHUD.cs:242`), which sets
`FF9.attr |= 0x102` (`Global/UI/UIManager.cs:457-463`). The guest's copy of the host's field stops running
until the menu closes (`FieldHUD.cs:396` turns it back on). What that does to each co-op lane:

| Lane | Today's behaviour with a guest outside FieldHUD | Consequence |
|---|---|---|
| Follow the host to a new field | Waits (`NetSyncClient.cs` ~4878: `I'm mid-battle/menu/transition -- try again when free`) | **Owner decision: close the guest's menu at once**, then the normal follow runs. The spec must pick the trigger against s164's follow code (the host's field-change intent or the s164 pin) and say whether field-to-world and world-to-field moves count too |
| Host battle start | The diorama boot needs FieldHUD or WorldHUD (`NetSyncClient.cs:3515`) | The guest never boots. The host's gauges wait up to `StartHoldMs` (8000 ms, host side), then the host plays the guest's slots. **Close the guest's menu at the host's battle cut** |
| World-map battle (s145) | Same WorldHUD gate | Same fix |
| Talk relay, dialogue ring | Defers and keeps the host's events (TALK-7 catches up page by page) | Lags, then catches up |
| ATE relay, chest relay, step-out | Built for a live field | Check each before building; the COMMS-MENU §2 auto-close list is the starting point |

**Where opening is natural.** The world map, where the guest is already frozen (s144), and any field
where the host is walking freely. Open only when the COMMS-MENU §2 predicates hold, plus "the host is not
mid-scene". The stock MENUOFF of the guest's own copy already refuses quietly under scenes
(`MenuKeyStep(false, true, Fld) == MenuKeyStockOff`).

## 8. Both players in menus at once

With Option A this is safe, because the host rechecks every intent against its live state. The costs are
in the guest's experience:
- the guest's view goes stale under the host's edits;
- the stock screens cache their lists when they open (`ItemUI._itemIdList`, the equip candidate list,
  `ShopUI` max counts), so a re-seat under an open screen needs a redraw, or should wait for the next
  screen change;
- a refusal ("that sword is gone") needs a clear buzz and a line.

The alternative is one player in a menu at a time. The host's own menu would then be refused while the
guest's is open, with the same dead-peer timeout problem as Option B. Owner decision 2.

## 9. The wire

**Missing from section 1 today** (`Global/PLAYER.cs:165-199`):

| Field | Needed by |
|---|---|
| `pa[]` (AP per ability) | Ability screen: what is learned and how far along |
| `exp` | Status screen |
| `bonus` (level bonuses) | Status screen, stat display |
| `saExtended`, `saForced`, `saBanish`, `saHidden` | Ability screen on modded kits |
| `permanent_status` | Status screen |
| gil | Main menu header (the guest's own gil shows today) |
| bag order | Item screen; section 3 is an unordered set and drops zero counts |

**Freshness.** Sections ride every host state frame (every 150 ms in every mode) but are parsed only at
a field load. Two ways to get a live copy:
1. parse the latest frame while the menu is open, the way the diorama's seat reads its boot frame;
2. a menu snapshot on request: the guest asks on open, and the host replies after each applied intent.

Option 2 keeps the 150 ms frame small. `pa[]` alone is an `Int32` per ability per character.

**Version.** A new intent lane means a wire bump. The wire is at v14 (`NetSyncSocket.cs:176`), and **v15
is already promised twice**: to the comms lane (COMMS-MENU §4) and to B4.2. Coordinate the numbering.
A bump forces both machines to update, which is the safe direction. A guest-side behaviour gate with no
bump fails silently on a stale peer (the s38 rule).

## 10. Feel: local apply and the echo

Simplest: let the stock code change the guest's seated copy instantly, send the intent, and let the
host's echo overwrite the copy. A refusal snaps back with the buzz. The stock duplication path (§3) can
fire on the guest's copy, but only cosmetically, and the next re-seat erases it.

Waiting for the host's confirmation before each redraw would feel laggy over the relay. It would also
need hooks into every screen's redraw.

## 11. The host's save is real

This is the feature's main hazard. Any bug in the forwarding path writes the host's persistent save. Each
host helper needs invariants checked before it applies anything:
- **Equip:** the total of bag count plus equipped count, per item, is the same before and after.
- **Support abilities:** each one is learned (`pa[]` at or above its cost), and the set fits the
  character's capacity.
- **Item and field ability use:** the item is present, or the caster has the MP, at the host's own call.
- **Every intent:** a known `CharacterId` that is in the host's party.

A refused intent logs one line and changes nothing.

## 12. What the host sees

The guest's body stands still while the guest is in the menu. Options, none built:
- a "partner is in the menu" marker over the guest's ghost;
- a toast on each applied change ("Partner equipped Vivi with a Mage Masher");
- a host veto, which is really the `GuestMenu` setting from §5.

## 13. Rung ladder (Option A)

| Rung | Scope | New pieces |
|---|---|---|
| 0 | View-only main menu on the guest | Lift the s38/s121 gate; seat on open, restore on close; refuse every changing confirm; close on the host's battle cut and on the host's field change; the missing wire fields (§9) |
| 1 | Support abilities | Intent "set character C's support-ability set to S"; host helper with the learned and capacity checks; the host's one-line message per applied change |
| 2 | Equip, remove, Optimize | Intent (character, slot, item); host helper modelled on `PLAYER_EQUIP` with the conservation check. Optimize sends its result as one batch |
| 3 | Item use, field abilities, key items | Host helpers around `SFieldCalculator.FieldCalcMain` plus the remove; Gysahl Greens refused |
| later | Order and row, shops | Only if the owner wants them (§5, §6) |

## 14. Solo testability

- **The selftest role** loops intents through the real encoder and decoder on one machine, as B1 did.
  It needs an unconfigured instance root (the s158 law: the shared install is configured as host and
  refuses `netsync selftest 1`).
- **`harness/duo.py`** pairs two real games on one machine for the battle-cut close and the follow lag.
- **Prove each check can fail.** Break the conservation check and confirm the bench goes red before
  trusting it green.
- **Fingerprint the guest's save after the copy is restored**, never while seated. That is the diorama's
  s110 law.

## 15. Owner decisions (answered 2026-10-31)

1. **Which characters:** the whole party. (§5) No `GuestMenu` setting was asked for; whether the host
   still gets an off switch is a spec question.
2. **Both players in menus at once:** allowed. (§8)
3. **The host leaves the field** while the guest is in the menu: **close the guest's menu at once**, then
   follow. This overrides the study's recommendation to let the guest lag. (§7)
4. **The host starts a battle** while the guest is in the menu: close the guest's menu at the battle cut.
5. **First build:** view-only (rung 0), then support abilities (rung 1). (§13)
6. **Party order and row:** host only. (§5)
7. **Item sort:** sorts the guest's view only. (§6)
8. **The copy's lifetime:** only while the menu is open, restored on close.
9. **Host notification:** a one-line message on each applied guest change, from rung 1 on. No marker. (§12)

Decisions 3 and 4 make one rule: **the guest's menu never outlives the host staying put.** Under
Option A a forced close loses nothing, because every guest edit is already applied or refused on the host.

## 16. Traps carried from earlier studies

- **Gate at the read, never through an `IsMenuControlEnable` getter.** `FieldMapActorController` reads
  that flag to decide whether an inactive actor idles (Road A).
- **Never raise `MainMenuScene.ImpactfulActionCount` from a remote apply.** It triggers
  `UpdateBattleAfterMainMenu`'s roster reconciliation (`BattleHUD.cs` ~2767).
- **Do not reuse a `party.member` scan inside battle.** BattleHUD nulls and rebuilds those entries around
  its in-battle menu.
- **Caller-grep before trusting a write function.** This tree is decompiled and keeps dummied stock
  functions that read like live ones. Three July defects came from citing a definition without its callers.
- **Never make a guest window an ETb Dialog.** `IsLockable` would trip the F3.2 lock (COMMS-MENU).
- **A wire bump forces both machines to update; a behaviour gate does not.** Ship this behind a bump.
