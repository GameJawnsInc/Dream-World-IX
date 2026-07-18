# Save-point synthesis (`[[savepoint]]`)

> **Status: SHIPPED. The rung-2 dialogue flow is OFFLINE-VERIFIED and awaits a playtest** (it changes
> the bytes every existing `[[savepoint]]` emits). Two paths exist. (1) **Synthesis** — a press-to-interact
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
moogle's letter delivered BY a real moogle — works on stock Memoria unchanged. Read-mail is deferred.

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

### Deliberately not synthesized

The moogle's **reveal/hop** and its **book + feather** animation (clips exist and are addressable:
`ANH_NPC_F0_MOG_SAVE_JUMP` 6503, `MOG_SAVE_OPEN` 4645, `ACC_F0_MGR_SAVE_OPEN` 4641, `MGP_SAVE_OPEN` 4651),
and the **Tent / Select party members** rows of the real option menu. The tent's HP restore is not visible
in the field script at all — the Memoria branch is only `RunScriptSync(2, 9, 19)` + `RemoveItem(253, 1)` —
so a Tent row would mean guessing at the heal. Deferred rather than half-built; the verbatim carry below
is the way to get the full moogle act today.

- `ff9mapkit/eb/opcodes.py` — `menu(menu_id, sub_id=0)` (0x75; `menu(4,0)` = save).
- `ff9mapkit/content/savepoint.py` — `save_dispatch()`, `savepoint_region(zone, *, bubble)`,
  `inject_savepoint` / `inject_savepoints`.
- `build.py` — `[[savepoint]]` validated (zone 4–5 pts) + injected (a 4-pt zone is widened to the
  `quad_zone` doubled-last-vertex convex quad, the `IsInQuad` dead-zone fix).

## The moogle's ACT — two ways to get it

**Synthesis (the act is still manual).** `[[savepoint]]` places a visible save Moogle and runs the real
menu→confirm→save flow, but the Moogle does not yet **hop out** or **open its book**. Dress the rest by
hand — a `[[prop]]`/`[[npc]]` over the zone (the `moogle` archetype, model `GEO_NPC_F0_MOG`; the cask
`GEO_ACC_F0_CSK`; the `save_point` prop composite = moogle pose 2904 + book `GEO_ACC_F0_MGR` pose 1872).
The clips are all named and addressable if you author the choreography yourself:

| clip | id | role |
|---|---|---|
| `ANH_NPC_F0_MOG_IDLE` | 2904 | rest pose |
| `ANH_NPC_F0_MOG_SAVE_JUMP` | 6503 | the hop |
| `ANH_NPC_F0_MOG_SAVE_OPEN` | 4645 | the Moogle opens the book |
| `ANH_ACC_F0_MGR_SAVE_OPEN` | 4641 | the book opens |
| `ANH_ACC_F0_MGP_SAVE_OPEN` | 4651 | the feather writes |

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
