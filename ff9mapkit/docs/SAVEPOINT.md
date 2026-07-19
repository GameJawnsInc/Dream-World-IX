# Save-point synthesis (`[[savepoint]]`)

> **Status: SHIPPED + IN-GAME PROVEN** (2026-07-18: the faithful menu flow, the Moogle's ACT, the
> Mognet identity, the stock dialogue/window shape, and the party-row clamp all playtested). Two paths exist. (1) **Synthesis** — a press-to-interact
> `[[savepoint]]` region around the functional core (`content/savepoint.py`, `eb/opcodes.py`). (2) The
> faithful **verbatim carry** of a real field's whole save-Moogle cluster — `import <field> --save-moogle`
> (`cli.py`), emitting a `[[save_moogle]]` block whose cluster + director are validated in `build.py` and
> grafted via `savepoint.py:graft_director`. Save → Continue **into** a custom field (id ≥ 4000) round-trips
> in-game (see "In-game proof" below).

A functional FF9 **save point** — the save Moogle's *save* — synthesized as a press-to-interact region.
The synthesis path takes the lean route after the object / player / text carry arc: instead of grafting the
real save moogle's un-graftable 7-entry-ish cluster (5 hidden objects + STARTSEQ helpers + player-pose
surgery + a `gEventGlobal` contract), the kit **synthesizes** the save from its functional core. The
faithful carry (below) does reconstitute that whole cluster.

## The recipe (the one load-bearing fact)

The functional save is a **single opcode**: `Menu(4, 0)` (`0x75`).

```
EventEngine.DoEventCode  ->  EventService.StartMenu(4, 0)  ->  FF9Menu_Command
  case 4u: if (subId == 0u) OpenSaveMenu()  ->  SaveLoadScene.Type = SaveLoadUI.SerializeType.Save
```

The menu enum (`EventService.cs`): `1` = name, `2` = shop, **`4` + subId `0` = SAVE**, `5` = chocograph.
Verified byte-exact (`75 00 04 00`) against the real **Dali save moogle** (field 122
`fbg_n08_udft_map122_uf_sto_0`, **entry 5, tag 3**). Everything else in that moogle — jump out of the
barrel (`SetupJump`/`Jump`), the player-pose `RunScriptAsync(4,250,13)` — is **cosmetic**; none of it is
needed to save the game. (The dialogue choice is NOT cosmetic and is now synthesized — see the census
below: every real save point asks before it saves.) (`Menu(2, <shopId>)` later in tag-3 is the Dali
moogle *also* running a shop — irrelevant to a save point.)

## The census — what a save point actually looks like (2026-07-18)

Scanning every FF9 field for an **instruction-aligned** `Menu(4, 0)` (a raw byte scan false-positives —
`75 00 04 00` also occurs inside jump-table operands, e.g. Madain Sari/Path) finds **55 save points in two
structurally unrelated families**:

| | fields | entry | size | model |
|---|---|---|---|---|
| **Save Moogle** | 48 | type 2, 3 funcs, tag 3, spawned hidden (`SetObjectFlags(14)`) | 7.1–8.4 KB | 220 `GEO_NPC_F0_MOG` (41) or 129 `GEO_NPC_F1_MOG` (7) |
| **Moogle-less save point** | 7 (Memoria / Crystal World) | type 0, 2 funcs, tag 1, Init is one `return` | **686 B** | none — a tent prop stands nearby |

**The moogle family is one stamped template.** Opcode-sequence similarity between the most distant
instances is **90–94%**. Field 407 (Dali/Storage Area — the barrel moogle) is a *typical* member, not an
advanced one: its tag 3 is the shared template; only its tag-1 loop is enlarged (374 B vs 295) to hop out
of the cask. **The staging varies between save points; the save act does not.**

**Both families ask before they save.** Neither jumps straight to the menu:

```
lock control ; DisableMenu
  option window   ->  row 0 "Save"
    confirm window ->  row 0 "Yes"
      GLOB(184) = 1 ; Wait(3) ; Menu(4, 0) ; Wait(3) ; GLOB(184) = 0
EnableMenu ; restore control
```

Moogle family (field 300 entry 3 tag 3): `EnableDialogChoices` + `WindowAsync(2, 8, 3)`, then
`WindowAsync(2, 8, 4)`, then the save at 4601 — note window slot **2**, flags **8** (the small selection
window, not the dialogue window 1/128). Moogle-less family (field 2919 entry 7 tag 1): txid 454, then 457,
then the save. `gEventGlobal[184]` (`General_LoadedGame`) is set to 1 immediately before the menu and
cleared immediately after, with `Wait(3)` on each side, in **both**.

## What ships

`[[savepoint]]` authors that spine. It is the navigable cousin of
[`content/jump.py`](../ff9mapkit/content/jump.py)'s `action` region — same `Init SetRegion` / tread
`Bubble("!")` / action shape — and **no player-function graft is required** (the save is a self-contained
engine call). `build.py` also places a visible save Moogle at the zone by default, whose TALK runs the
same dispatch.

```toml
[[savepoint]]
zone = [[-275, -1947], [25, -1947], [25, -2247], [-275, -2247]]   # 4- or 5-pt press quad
# dialogue = false   # skip the menu+confirm and open the save menu on touch (no real save point does this)
# bubble = false     # hide the "!" prompt (e.g. when a visible model already signals the save)
```

### The nesting hazard (a correctness constraint, not a style choice)

`choice.branch` emits one **independent** if-block per option — `if(GetChoose()==0){b0}
if(GetChoose()==1){b1}` — and each block **re-reads sysvar 9**. That is fine for a flat menu, but the save
flow nests a second window inside row 0, and that window **overwrites sysvar 9**. So a bodied row 1 at the
outer level would test the *inner* answer: pick "Save" then "No" → `GetChoose()==1` → the outer Cancel arm
also fires.

`savepoint._row0_only` therefore gives a body to **row 0 only** at each level; `branch` skips empty bodies,
so exactly one if-block is emitted per window and no stale read is possible. **Adding a Tent or
Select-party row means switching to the real fields' pattern** — copy `GetChoose()` into a scratch var and
switch on *that* (`op_05{op7A(9)}` + `op_0B`, as field 2919 does) — **not** adding a second body here.

### The network moogle — `[savepoint.mognet]` (rungs 3-5)

The save Moogle can **join FF9's real Mognet network as a brand-new 42nd identity** (id 41). Verified
across two adversarial multi-agent passes + a live-save probe (2026-07-18): Mognet is driven entirely by
field bytecode + text — no C# letter logic, no roster in the engine, and **no bound anywhere on the
identity byte** (every routing comparison in all 818 fields is equality; `EBin` reads variable indices
from the instruction pointer, so moogle-indexed storage cannot even exist). The mailbox is
`gEventGlobal`: guard `Byte[1024]`, delivered-counter `Byte[1032]`, three 4-byte slots at `1034+4k`
(occupied/variant/FROM/TO), and two 64-bit variant one-shot lock tables (bits 8376-8503,
`bit(v) = anchor + 8*(v//8) - (v%8)`, anchors 8383/8447 — live-pinned). **The real ceiling is the letter
VARIANT id (< 64; shipped content reaches 48 → custom letters use 49-63), not the moogle id.**

What ships: `content/mognet.py` emits the protocol (give = first-EMPTY-slot with full-refusal +
structural `Byte[1024]=1`; accept = counter + thanks + read-lock + the donor's compaction);
`savepoint.save_dispatch_mognet` is the 3-row menu (Save / Mognet / Cancel, `op_0B` dispatch); the build
ships the roster (your install's 41 names + the new one) as text entry 0 of the field's **minted** text
block, and resolves `give.to` names against it. The tests **execute** every path of the built moogle in
a mini-VM over a simulated `gEventGlobal` — an occupied slot is never overwritten, a full mailbox
refuses with zero writes, delivery compacts without holes, Save never touches a mognet byte.

Two honest limits: **inbound** (a real moogle addressing OUR moogle) needs a verbatim donor fork — the
recipient is a per-field immediate constant — and is a deferred, opt-in rung; and on **stock fields**
the new name renders blank (their rosters have 41 rows; fails safe to an empty string). Outbound — our
moogle's letter delivered BY a real moogle — works on stock Memoria unchanged.

**READ-MAIL (decoded 2026-07-19; donors 115/300/418/1102 + a 58-field census — one invariant
template).** The moogle re-reads its OWN received letters, stock's third mechanic, now synthesized in
full. How stock does it, and therefore how we do: each field hardcodes up to 10 rows, row *k* gated on
`read_lock_bit(variant_k)` — the bit the ARRIVAL paths set; every Mognet open rebuilds the payload
(`Byte[1064+k]` = variant, mask `|= 1<<k`, `Byte[1079+k]` = sender — the write order is the donor's)
and masks a "which letter" window with it; a pick re-seeds text var 1 *from the payload byte* and
re-displays the letter through the same `letter_display` bracket. A read is **pure** — no lock write,
no mailbox write — so a known letter is re-readable forever. The whole 3-row submenu (**Give \<name\>
a letter / Read mail / Cancel**) appears only when a delivery is pending OR a letter is known, gated
on a computed availability word exactly like the donor's; masked rows vanish from navigation
(`Dialog.SetupChooseMask`). Arrivals come from **two sources**, both stock's: the player's own
delivery (the accept path — sets the lock since rung 4), and **story-gated auto-arrivals**
(`received = [...]` — announce + letter + lock when `requires_flag`/`requires_scenario` first holds;
the lock is the once-guard). One consequence worth naming: this decode found stock read-mail's payload
bytes sitting exactly on the kit's old `FIRST_SAFE_FLAG = 8512` — the safe flag band moved to
**8712** (see `flags.py`).

**Letter CONTENT, decoded (field 1865 @6191-6310):** a letter's body is ONE text entry in the
RECIPIENT's field block, shown frameless (window 3, flags 16) inside a fade bracket
(`FadeFilter(2,24,·,220,220,250)` in, `(7,16,·,0,0,0)` out), selected by an `op_06` switch on the
variant with HARDCODED arms — the default skips the window but the fade still runs, which is exactly
the observed "empty letter flash" when a stock moogle received our variant 56. The entry's shape
(1865 entry 49): a fixed header template — widths, the moogle portrait built from `[ICON=27/28/29]`,
the colored `From [TEXT=0,1] to [TEXT=0,0]` line through roster table 0 — then the body. So:
**letters delivered TO OUR moogle render fully** (`accept = [{ variant, letter = "..." }]` — the
build ships the entry + `mognet.letter_display` runs the faithful bracket in the accept arm);
letters delivered to STOCK moogles show the graceful empty flash until their `.eb` is patched (the
same donor-fork class as inbound; deferred together).

### The other real rows — Tent / Mogshop / Switch party members

The real moogle's menu is seven rows (Save · Tent · Mognet · Mogshop · Switch party members · Debug ·
Cancel) behind a runtime availability mask; a field shows a subset. `[[savepoint]]` emits the subset you
configure, in that order (`savepoint.menu_rows` — the `[CHOO]` list and the `op_0B` dispatch both derive
from it, so they cannot drift), and never emits stock's dev-only `Debug`.

**Tent** (`tent = true`), decoded at field 300 @5016-5608 — and the heal was never missing, just *before*
the `RemoveItem` rather than after it:

```
for slot 0..7:  if (CURHP(slot) != 0):            # not KO'd -- and an unheld slot reads 0 too
                    SetHP(slot, CURHP + (MAXHP+1)/2)
                    SetMP(slot, CURMP + (MAXMP+1)/2)
RemoveItem(253, 1)
```

So a tent restores **half of maximum, rounded up** (SetHP/SetMP clamp at the max), never revives the
dead, and the prompt carries the live remaining count via text var 7 + `[NUMB=7]`.

**Mogshop** (`shop = <id>`) is `Menu(2, shopId)` — the row just opens an ordinary `[[shop]]`.
**Switch party members** (`party = true`) is `Party(min_size, locked_mask)` + `UpdatePartyUID()`
(`EventEngine.DoEventCode` PARTYMENU 0xB2: arg1 = minimum party size, arg2 = a bitmask of locked
character slots); the donor calls `Party(4, 1)`.

> ⚠ **The min-size softlock** (in-game 2026-07-18). `PartySettingUI.FF9Party_Check` is the *only* exit
> from the party screen — `OnKeyCancel` runs it and, when it fails, just buzzes and stays — and it reads
> `selected >= party_ct`. So a literal `Party(4, …)` with fewer than four characters available is
> **unescapable**. Stock never hits it (its party row only appears on late-game moogles with a full
> roster), and the engine clamps this same value elsewhere (`UIKeyTrigger.cs:1002`:
> `party_ct = Math.Min(4, selectList.Count)`). So the kit's **default** is that clamp, computed at
> runtime: arg1 is an expression summing `partychk()` over every character, which equals the screen's
> own `selected` count on entry — always escapable, and exactly `4` once the party is full. Setting
> `party_min` explicitly emits that literal instead, softlock and all.

### Not synthesized

The moogle's bespoke pre-interaction **reveals** (the barrel-pop, the flying Treno shuttle, the two
one-off story cutscenes) — the verbatim carry below is the way to get those. The interact-time ACT
itself IS synthesized now (next section).

- `ff9mapkit/eb/opcodes.py` — `menu(menu_id, sub_id=0)` (0x75; `menu(4,0)` = save).
- `ff9mapkit/content/savepoint.py` — `save_dispatch()`, `savepoint_region(zone, *, bubble)`,
  `inject_savepoint` / `inject_savepoints`, and the ACT section (`act_save_body`, `inject_act_cluster`).
- `build.py` — `[[savepoint]]` validated (zone 4–5 pts) + injected (a 4-pt zone is widened to the
  `quad_zone` doubled-last-vertex convex quad, the `IsInQuad` dead-zone fix).

## The moogle's ACT — two ways to get it

**Synthesis (SHIPPED, default ON).** `[[savepoint]]`'s moogle now performs the real save choreography.
The 4-agent byte census (2026-07-18, every one of the 65 `Menu(4,0)` field ids) proved the interact-time
act is ONE invariant template across all 57 moogle instances, so the kit emits that template: on the
confirmed Yes — and only then, the donor's decline law — the moogle hops (`SAVE_JUMP` 6503 + the
universal SFX 1362/2631), the **book** (model 133) and **feather** (model 134) snap to it and open
(4641 / **4652** — the 4651 the old table listed is wrong, byte-verified in fields 300 AND 810), the
moogle opens its book (4645) while its save line shows, `Menu(4,0)` runs latched, then everything
reverses (props vanish, hop back with the direction-asymmetric landing thud 682, the player-watch pose
releasing through the donor's own `MAP.Bit[322]` handshake). The build injects the whole cluster —
the two hidden props with appear/hide tags, two grafted player functions, the moogle's load-bearing
`SetJumpAnimation(6503, 26, 30)` preload — automatically.

```toml
[[savepoint]]
zone = [[-100,-100],[100,-100],[100,100],[-100,100]]
act = true                    # the default; false = the pre-act still moogle
act_text = "Here we go, kupo!"   # the WindowAsync(1,128,·) line during the act
act_hop_to = [-347, 7514]     # OPTIONAL landing spot: hop there and back with the donor's
                              # 15-frame lerp (default: hop in place at the moogle's pos)
```

The act requires the moogle and dialogue (it plays inside the confirmed-Yes arm); the press REGION
stays actless by design — a type-1 region has no model, exactly the donor's moogle-less Memoria family.

The census's clip law, for reference (and for hand-authored choreography):

| clip | id | role |
|---|---|---|
| `ANH_NPC_F0_MOG_IDLE` | 2904 | rest pose |
| `ANH_NPC_F0_MOG_SAVE_JUMP` | 6503 | the hop — both directions, both moogle models (220 AND 129) |
| `ANH_NPC_F0_MOG_SAVE_OPEN` | 4645 | the Moogle opens the book |
| `ANH_ACC_F0_MGR_SAVE_OPEN` | 4641 | the book opens (book = model 133 in 57/57 fields) |
| `ANH_ACC_F0_MGP_SAVE_OPEN` | **4652** | the feather writes (feather = model 134 in 55/57) |

**Faithful verbatim carry (SHIPPED — the full cluster, automatic).** `ff9mapkit import <field>
--save-moogle` carries a real field's save point **verbatim** as a faithful FF9 save point: the hidden
save Moogle pops out of its barrel and runs the full save flourish, exactly as the original. The flag
**implies `--graft-player-funcs`** (the carried objects + pose funcs must exist) and **only fires on a
field that actually has a save point** — on **either** save-Moogle model (`eventscan.SAVE_MOOGLE_MODELS`
= {220, 129}; seeding on 220 alone silently dropped the save point on the 7 model-129 fields). It emits a
`[[save_moogle]]` block:

```toml
[[save_moogle]]
carried = true                  # the cluster lives in the [[object]]/[[player_func]] blocks the import emits
director = "save_director.eb"   # the source field's main-loop puppeteer, grafted into entry-0 tag-1
```

**Donor coverage is limited and now says so.** The director is only carried when the donor's entry-0
tag-1 is a clean shared-var driver — true for just **14 of the 55** save fields (field 407 is the
reference; the canonical Ice Cavern moogle, field 300, is *refused*). When it is refused the import now
prints the reason and leaves it as a comment in the emitted TOML, instead of silently shipping a Moogle
with no puppeteer. See `eventscan.savepoint_director_report`.

It reconstitutes the real cluster: the **hidden Moogle + book/feather/tent**, the **player-pose surgery**
(tags 13/14/15), and the **director** — the save Moogle's main-loop state machine, which `build.py` grafts
via [`savepoint.py:graft_director`](../ff9mapkit/content/savepoint.py) into the fork's empty entry-0 tag-1
(it drives the Moogle through shared transient MAP vars, so it grafts verbatim). `build.py` validates that a
`carried=true` block has its `[[object]]`/`[[player_func]]` cluster. The spawn pose is normalised to its
rest pose so a fork shows no load flash.

## In-game proof

The save menu **opens, writes a slot, and reloads** correctly **in a custom field (id ≥ 4000)** — the
save → Continue-into-a-custom-field path round-trips in-game (CAMPAIGN_IMPORT.md §7, load-bearing test #2;
the `fldMapNo` round-trip is detailed in [GLOBAL_RESOURCES.md](GLOBAL_RESOURCES.md)). The verbatim
save-moogle carry is complete and proven (see [FORK_FIDELITY.md](FORK_FIDELITY.md)). The only piece the kit
can't self-check is that this **synthesized** region opens the Menu where you stand — that placement is
verified manually in-game per build (every region trigger has this step).
