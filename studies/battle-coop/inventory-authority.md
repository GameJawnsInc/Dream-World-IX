# THE SHARED-BAG PROBLEM — inventory authority in co-op (2026-07-15, source census + adversarial verify)

> **THE QUESTION** (user-raised): an inventory sits at the GLOBAL-SAVE level, like story state — but
> unlike story flags, **the guest can change it** (potions, equipping, Throw). So either the
> read-only-mirror paradigm is unworkable, or we need a handshake that keeps it in sync — host-only
> forwarding (nominally "worst-case") or perfect collision-gating (nominally "best-case, improbable").
>
> **THE VERDICT: host-authoritative is FORCED, and it is not the worst case — it is what "shared"
> MEANS mechanically.** The 2-way shared-mutation model has no legal move in this engine. The
> read-only-mirror paradigm is **not falsified by the inventory — it is INCOMPLETE.** Story flags
> mirror because the guest never authors them. The bag needs one more lane: **reads mirror, writes
> forward.** That exact shape is already in-tree and two-machine proven (B1).

*(6 questions, each answered from source then adversarially verified — 12 agents. All 6 answers were
materially corrected by the verify pass.)*

---

## ★ THE LIVE DEFECT — the unbounded item farm (present-tense, reachable TODAY)

The root cause is not "the read says host, the write says local." It is a **LIFETIME ASYMMETRY**
between the two halves of a single `.eb` transaction:

| Half | Owner | Lifetime |
|---|---|---|
| **Flags** | mirror-owned | **TRANSIENT** — `NetSyncState.cs:107-109` overwrites the ENTIRE 2048-byte `gEventGlobal` from the host's snapshot (every index outside the 2032-2041 coop mask) on **every field load** (`HonoluluFieldMain.cs:135`) |
| **The bag** | guest-owned | **PERSISTENT** — the mirror never touches `FF9StateSystem.Common.FF9.item` at all |

**The exploit, mechanically certain:**
1. The guest opens a chest the host has not looted → `FF9Item_Add` lands in the **guest's real bag**,
   and the "chest opened" GLOB flag sets **locally**.
2. The next field load wipes that flag back to the host's value. **The chest is closed again.**
3. Re-enter, re-open, re-add. → **An unbounded local item farm, one item per field re-entry.**

**Save-safety does not touch this.** The exit ramp guarantees the *disk* stays pristine, but the drift
is live, player-visible, compounding, and it degrades exactly the thing the mirror exists to deliver.

> **SAVE-SAFETY IS NOT CONTAINMENT.** They have been conflated. The save gates prove the guest's
> Continue slot survives a session; they say nothing about whether the session itself is coherent.

**This gives the SPECTATOR-FIELD PARADIGM teeth.** It was set on design instinct ("the guest isn't
meant to interact outside combat"). It is now a **correctness requirement** — and nothing enforces it
today: `FollowHostTick` calls `SetUserControl(false)` only transiently during the warp itself
(`NetSyncClient.cs:659`). **A following guest keeps full field control and full menu access.**

---

## THE GATE CENSUS — three blocks, three reads, ZERO write gates

An engine-wide grep for `NetSync` outside `Memoria\Netsync\` returns **16 hits**:

| Kind | Sites |
|---|---|
| **Blocks (3)** | `SaveLoadUI.cs:150` (manual save) · `EventEngine.cs:687` (autosave) · `SettingsState.cs:54` (random encounters) |
| **Reads (3)** | `EventEngine.cs:875` (B_PARTYCHK) · `EBin.cs:396` (PARTY_MEMBER) · `EventEngine.DoCalcOperationExt.cs:16` (B_HAVE_ITEM) |
| **Plumbing** | `HonoluluFieldMain.cs:29/135` · `UIKeyTrigger.cs:179` + 7 `BattleHUD.*` hooks (all B1, host-side) |
| **WRITE GATES** | **NONE.** |

**The mirror is a read-only overlay on a sidecar.** The host's bag lands in a *private* `_bag` dict
(`NetSyncParty.cs:59`), read only by `TryItemCount` (:294), whose only caller is the `B_HAVE_ITEM`
opcode. It is **structurally unreachable** from `ItemUI`/`EquipUI`/`ShopUI`. The rung-2 header comment
already conceded this: *"Menus and the guest's real FF9.party/item state are NEVER touched."*

**Also frozen:** `ParseSections` has exactly ONE production call site — `ApplyStoryBeforeEvents` from
`HonoluluFieldMain.cs:135`. **The mirror latches at field load and nowhere else** — stale by
construction during a battle, and structurally unable to support live 2-way convergence. The wire is
also **lossy**: `NetSyncParty.cs:128-135` ships an `(id,count)` SET and drops `count<=0` — it cannot
author a bag.

---

## WHY 2-WAY IS FORCED OUT (the collision model)

**Not because of order convergence** — that leg is WITHDRAWN. `ItemUI.ArrangeAuto` (`:934-947`) is a
live, user-invoked canonical sort (total order, insertion-history-independent). Order *is* expressible.
The model dies on two other legs, both confirmed at every commit site:

**1. There is no check-commit boundary.** Zero `lock`/`Interlocked`/`Monitor`/`volatile` anywhere in
`Memoria/Data/`. The bag is `public List<FF9ITEM>` of mutable `Byte` counts. Every economy site caches
its own snapshot at menu-open and commits later **with no re-check** (`ShopUI` maxCount `:1163-1165`,
`ItemUI._itemIdList` `:651-678`, `ff9feqp._FF9FEqp.item[]` `:83-91`). *(The netsync layer does lock —
but only socket buffers; frames apply on the game thread. So intra-function tearing is impossible and
every race is TOCTOU **across** frames. That locates the hazard; it doesn't rescue the model.)*

**2. Rollback is unimplementable.** Mutations are destructive in place, and **callers have already
committed side effects before the failure is knowable**:
- `ItemUI.cs:416/424` applies the **heal**, *then* `:431` removes the item — return value **ignored**.
- `BattleHUD.Public.cs:799-804` `ItemUse` is **`void`**: the failure isn't discarded, it is
  **unreportable**. `btl_cmd.cs:633-638` sets `CMD_MODE_LOOP` unconditionally regardless.

**The concrete corrupt end-states:**

| Race | End-state |
|---|---|
| Both use the last Potion (battle) | **Two heals land, one potion consumed** |
| Both use the last Potion (field) | **Free heal** — effect applied before the ignored Remove |
| Guest buys what the host's gil already spent | **UInt32 underflow → ~4.29e9 gil.** `ShopUI.cs:395` `gil -= …` with **no floor guard** (the *sell* path clamps at `:450-451`; buy does not) |
| Guest sells what the host just used | **Gil minted from nothing** |
| Both equip the same unique weapon | **Equipment DUPE** |

> ### ★ THE LATENT STOCK BUG THAT SETTLES IT
> `ff9feqp.cs:98-104` (and `EquipUI.cs:189-203`, `:1244-1253`) does **`FF9Item_Add(old, 1)` FIRST**,
> then `if (FF9Item_Remove(new, 1) != 0) { equip = new; }`. If the peer took the item: the character
> **keeps the old piece AND the bag gained a copy.** No rollback.
>
> This is **unreachable single-machine** (the menu only lists `count>0`). **Any scheme that lets a
> remote write land between menu render and commit ARMS this dupe** — sufficient on its own to reject
> 2-way mirroring even if every other race were gated.

**The only "gate" that works** is a global bag lock held across the peer's entire menu interaction —
i.e. host-authority with worse UX and a worse failure mode (**the PEER-ALIVE LAW**: transport-up ≠
peer-alive, so a lock holder can vanish and freeze the host's menus).

---

## ★ THE FORWARDING TEMPLATE (already built, already proven — copy it, don't invent)

B1's item lane is **genuinely host-authoritative**, verified in the strong form:
`grep -rnE "FF9Item_Remove|FF9Item_Add|FF9Item_Set|\.count\s*=" Memoria/Netsync/` → **EXIT 1. Zero item
mutations in the entire Netsync tree.** The guest never mutates; there is nothing to roll back.

```
guest picks item  → NetSyncBattle.cs:809-814  reads roster.Items[idx] (ADVISORY), BuildCommand → 9-byte frame
                  → Pump :307  socket.SendCommand           [inside `if (live && !inBattle)` — the spectating branch]
HOST receives     → Pump :273-277  HandleCommandPayload     [inside `if (inBattle)` — only the battle owner applies]
       revalidate → :1068  if (ff9item.FF9Item_GetCount(id) <= 0) { log "dropped (none left)"; return; }
       execute    → :1073  hud.SendNetCommand(...)
                  → BattleHUD.Unity.cs:618-621  btl_cmd.SetCommand(...)      [the engine's OWN local call site]
                  → btl_cmd.cs:633-635  UIManager.Battle.ItemUse(itemId)
                  → BattleHUD.Public.cs:799-804  ff9item.FF9Item_Remove(id, 1)   ← ONE bag moves. The HOST's.
mirror back       → roster lane (RosterMs=1000, rebuilt on byte-change)
```

> **THE TEMPLATE:**
> 1. The authority **PROJECTS** a read-only view built from its own state.
> 2. The peer emits **INTENT**, never mutation.
> 3. The authority **REVALIDATES LIVE** against its own state — *not* against the projection it sent.
> 4. The authority **EXECUTES through the engine's own stock call site**, so the mutation is
>    byte-identical to a local one and mirrors back through the projection.
>
> **Collision-gating is unnecessary because intent-forwarding REMOVES the guest's write entirely
> rather than arbitrating it.**

> **THE GATING LAW:** the engine has NO check-commit boundary. Therefore the ONLY safe place to
> validate a networked mutation is **INSIDE the host's own call, immediately before
> `FF9Item_Add`/`Remove`** — never in the caller, never on the guest.

**The suspected second hole is REFUTED:** the guest's battle item list is the HOST's bag.
`BuildRoster` (`:511-548`) runs only inside `if (inBattle)` and calls `CollectNetMenus`, which
enumerates the **host's** `FF9.item` (`BattleHUD.Unity.cs:788`). The guest's UiItem branch reads
`roster.Items` exclusively, with no fallback.

**Two lanes, two consistency domains** (a correction to the rung-2 model): section 3's `_bag` latches
at *field load* and feeds only the `.eb` read wrap; the live post-consumption count reaches the guest
via the **roster** lane. Section 3 is stale during a battle **by construction**.

---

## THE CENSUS — ~31 live surfaces, 11 writer files

Legend: **(1)** writes guest's own local state · **(2)** mirrored · **(3)** a following guest can reach it

### The `.eb` event lane — the guest runs the HOST's mirrored script locally ★
| Surface | Site | (1) | (2) | (3) |
|---|---|---|---|---|
| **ITEMADD 0x48** ★ | `DoEventCode.cs:1433` | YES | **NO — read wrapped, write not = THE INCOHERENCE** | YES |
| ITEMDELETE 0x49 | `DoEventCode.cs:1449` | YES | NO | YES |
| GILADD 0xCE / GILDELETE 0xCF | `DoEventCode.cs:2605` / `:2612` | YES | NO | YES |
| **PLAYER_EQUIP** ★ | `DoEventCode.cs:3090` → `equip.Change` → Add+Remove+equip write | YES | NO | YES |

> **This lane is not a menu the player chooses to open** — on a guest it is driven by the HOST'S
> MIRRORED SCRIPT. Write and read hit **different bags in the same frame**. It is arguably the
> *easiest* to fix: a mirrored script's writes can simply be **SUPPRESSED** on the guest, since the
> host runs the same script and performs the same write authoritatively.

### Field menu / equip (zero netsync gates)
`ItemUI.cs:431` (item use) · `:327` (Gysahl) · `:848` (`FF9Item_UseImportant`) · `EquipUI.cs:193/196/198`
· `:235/236` (un-equip) · `:1249/1252/1253` (Optimize — **no count pre-check**) ·
`CharacterEquipment.cs:114/119/121` · `ff9feqp.cs:99/100/102` · `ff9play.cs:453/455`

### Shop
`ShopUI.cs:391/395` (buy — **no gil floor guard**) · `:404/408` · `:418/422/423` (synthesis) · `:446/449/451` (sell)

### Battle
B1 item/Throw/Mix = **correctly host-authoritative**. But via the ENCOUNT hole (below), a local guest
battle reaches: **STEAL** (`BattleCalculator.cs:766`) · reward items (`BattleResultUI.cs:715`) · reward
gil (`:700`) · gil-cost abilities (`BattleAbilityHelper.cs:107`) · battle-script gil (`btl_scrp.cs:836/838`)
· flee gil (`battle.cs:464/469`) · Scripts-DLL gil (`BattleCalculator.cs:62`)

### ★ THE ENCOUNT CONTAINMENT HOLE (feeds B3.0, task #12)
`SuppressEncounters` reaches only `IsNoEncounter` — the random/step counter and the worldmap counter.
**Both scripted-battle opcodes are untouched: ENCOUNT `0x2A` (`DoEventCode.cs:957`) and ENCOUNT2
`0x8C` (`:969`).** A following guest can run a full local battle and collect local rewards + Steal.
**B3.0's containment gate must cover both opcodes explicitly.**

### F6 / boosters — A DECISION IS NEEDED
`Ff9mkDebugMenu.cs:1784` (give item) · `:1806` (give gil) · `BoosterSlider.cs:371` · `SettingsState.cs:432`.
F6 is **user-facing and ships in the bundle**. Gate it or consciously exempt it — silence means a guest
can self-gift mid-session.

### Deliberately local (correct as-is)
Cards (`TryItemCount` falls through at `NetSyncParty.cs:309`) · new-game/save-load init.

---

## THE WORK (if we build it)

| Axis | Shape | Cost |
|---|---|---|
| **The bag** | **The funnel is AIRTIGHT** — `FF9Item_GetPtr` returns a mutable ref but never escapes `ff9item.2.cs` (3 callers, all internal). **FIVE** wrap sites cover everything: `FF9Item_Add` (:248), `FF9Item_Remove` (:275), `FF9Item_AddImportant` (:321), `FF9Item_RemoveImportant` (:327), **`FF9Item_UseImportant` (:333)** — the last is reached directly from `ItemUI.cs:848` and bypasses the other four. (`FF9Item_UnuseImportant` :338 is dead.) | **CHEAP** |
| **Gil** | **NO funnel** — `PARTY_DATA.cs:17` `public UInt32 gil;`, a raw public field, ~15 live write sites. Convert to a property with a mirror-aware setter; `BattleCalculator.cs:62` already demonstrates the shape. | one refactor |
| **Equipment** | **A SECOND, DISTINCT AXIS — do not fold it into the bag fix.** An equip change is TWO mutations (bag + equip array) that must forward **atomically** or the guest dupes. 6 sites, **two of them grep-invisible**: `CharacterEquipment.cs:121` is an **INDEXER**; `ff9play.cs:455` is an **ALIASED array** (neither matches a `.equip[` grep). | harder |
| **The `.eb` write lane** | SUPPRESS on the guest (the host performs the same write authoritatively). | cheap |
| **Field forwarding** | `SFieldCalculator.FieldCalcMain` (`:17-22`) is **UI-free and host-callable**, with exactly 4 external call sites. But `ItemUI.cs:431`'s Remove is a **separate statement outside it** — so "one function the host invokes" doesn't exist; it needs a ~6-line host helper. `DoEventCode.cs:3082-3093` (PLAYER_EQUIP) is the ready-made headless, **CharacterId-keyed** equip shape — copy it + add a count pre-check. **Identity = CharacterId** (already on the wire at `NetSyncParty.cs:93`; never a slot index — `MainMenuUI.cs:613-615` permutes `party.member[]` in place). | 4 composites |

**Scope correction — budget FOUR composites, not one:** item use · **field ABILITY use**
(`AbilityUI.cs:512/520`, MP decrement inline at `:527-529`) · equip · **SUPPORT-ABILITY equip**
(`AbilityUI.cs:419-428`, `:628-656` — mutates `cur.capa` + `FF9Abil_SetEnableSA` inline through a
boost-hierarchy loop with **no primitive to call**; the real worst case).

**Blacklist:** Gysahl Greens (`ItemUI.cs:958-968` — mode-gate + `AttachDialog` + `StartCoroutine`; genuinely undriveable).
**Trap:** do NOT increment `ImpactfulActionCount` from a remote apply — it triggers
`UpdateBattleAfterMainMenu`'s roster reconciliation (`BattleHUD.cs:2644+`). *(Not a null-deref risk —
`MainMenuScene` is an inspector-assigned serialized field, never lazily constructed.)*
**Caveat:** don't reuse a `party.member` scan in battle — `BattleHUD.cs:2639-2641/2778-2784` nulls and
rebuilds those entries around the in-battle menu. Field-only idiom.

---

## ★ THE REAL DECISION — the guest's DISPLAY

**Rung 2's read-COMPARE technique cannot fix the guest's menu.** There is **no accessor to wrap**: 18
raw `Common.FF9.item` touches, plus in-place reordering (`ItemUI.cs:459-461`, `:936-937`). Showing the
guest the host's bag requires **pushing the mirror into the guest's REAL arrays** — a genuine departure
from "the guest never mutates local state."

**What makes it survivable:** the save gates (`SaveLoadUI.cs:150`, `EventEngine.cs:687`) + the autoload
exit ramp already guarantee the guest's disk never sees session state. The guest's real bag is *already*
session-scoped and discarded. Pushing the mirror into it changes what the guest **sees**, not what they
**keep**.

**The two roads:**
- **(A) SPECTATOR-STRICT** — block the guest's field menu + field interaction entirely. Cheap, honest,
  matches the paradigm as set, kills the farm. Single best hook: `UIScene.OnKeyMenu` (`UIScene.cs:136`)
  — every HUD override funnels through it in one line. **Plus** the Alt-hotkey shortcuts that BYPASS it:
  `UIKeyTrigger.cs:483` (Alt+F2 party) and `:519` (Alt+F5/F9). *(A getter gate on
  `IsMenuControlEnable` would cover all four in one edit, but it is a public field not a property, and
  `FieldMapActorController.cs:167` reads it as a "player has agency" proxy — it would change behavior.)*
- **(B) SHARED-BAG CO-OP** — push the mirror into the guest's arrays + forward the 4 composites. The
  guest genuinely plays from the shared pool. Much more work; much more co-op.

**(A) is a prerequisite for (B), not an alternative to it** — the farm must close either way.

---

## Status

- **2026-07-15:** census + verify complete. Verdict recorded.
- **2026-07-15 — ROAD A RUNG 1 ★ BUILT + TWO-MACHINE PROVEN** (`s38-netsync-spectator-field.patch`).
  User chose **"A first, then B"**. Three gates, all on `IsMirroringStory`: the **Steam achievement
  funnel** (`ProcessAchievementReport` — the ONE write the exit ramp cannot retract), **ENCOUNT
  `0x2A` + ENCOUNT2 `0x8C`** (a mirrored script was booting a local battle the host wasn't in), and
  **the menu** (all four `UIKeyTrigger` reads incl. the Alt-hotkey bypasses). Proofs: menus refuse
  both lanes · Evil Forest Plant Brain + plant-spider skipped on the guest while the host fought ·
  zero regressions in coop gates, battle B0/B1, cutscenes, the exit ramp.
  - **My "the bag is inert post-A" claim was REFUTED by the census** — six live readers survived, and
    the achievement lane escapes the ramp entirely. Road A was re-specified from an *input* framing to:
    **no interaction authority, no local state authority, no local escape.**
  - **The strand risk did not bite** — the guest's movement isn't blocked when the host's battle
    starts, so there is nothing to re-enable. ⚠ **B3 will REPLACE this gate, not keep it**: under the
    diorama ENCOUNT must *boot the diorama* instead of skipping, and the 30 strand sites go live again
    the moment the guest enters and returns from a battle scene.
  - **New rule minted:** *a wire bump forces a peer update; a behavior gate silently does not.* s38
    changes no wire (still v7), so a stale peer still pairs — but **the gates are guest-side**, so both
    machines need the DLL for symmetric protection.

### Rung 2 — NOT shipped (the known residue)
- **The verbatim-fork chest still opens.** A real chest is proximity-dispatched with its confirm read
  *inside* the script (`B_KEYON`), so the engine-level confirm gate never sees it. Post-A the item lands
  in a bag nothing reads and the ramp discards → **theater, not corruption.** Closing it needs a pad
  mask, which risks wedging any script that polls a button (the kit's own `--action-prompt` entrance is
  that idiom) — census the donors first.
- Also open: SYSVAR 6 (the guest's own gil, readable by any mirrored script — needs a wire section),
  the `0xD3` varfuncs (kit content only), the `.eb` MENU opcode (a mirrored script can still open a
  shop/save UI on the guest), and **F6/F7/Booster** (ours, user-facing, ships in the bundle — a
  decision, not a bug; post-A a self-gift is inert, so it is no longer urgent).

### Cutscene sync — RESEARCH NOTE, not scheduled (user-observed 2026-07-15)
The guest must advance its own dialogue in step with the host or get left behind. **This is not a Road A
regression** — dialogue/`B_KEYON` is deliberately untouched, and it self-heals at field boundaries when
follow-warp yanks the guest. The real shape is deeper than "sync the confirms": **the guest's cutscenes
fire from the GUEST's own position**, not the host's. Both machines run the same script off mirrored
flags, but the *trigger* is local — so they are not two clients showing one cutscene, they are two
independent scripts that happen to agree. Force-feeding the host's confirms would advance whatever the
guest's script is sitting on, which is not guaranteed to be the same thing. That is the full
**"play the game without a player"** arc → its own recon pass, after B3.

## Method note (durable)

Three defects in this pass shared one root cause: **citing a write primitive's DEFINITION without
grepping its CALLERS** (`ff9sell.cs`, `BattleItem.RemoveFromInventory`, `ItemUnuse` — all dead or
no-ops). Two census gaps (STEAL, PLAYER_EQUIP) were the direct downstream cost. **The caller-grep
discipline is not optional in this tree — it is decompiled, and it retains dummied stock functions that
read exactly like live ones.** (Same root cause as the B3 recon's `btl_para` false-safety finding.)
