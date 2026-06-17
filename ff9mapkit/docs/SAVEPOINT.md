# Save-point synthesis (`[[savepoint]]`)

> **Status: SHIPPED + in-game proven.** Two paths exist. (1) **Synthesis** — a press-to-interact
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
barrel (`SetupJump`/`Jump`), the Save/Shop dialogue choice, the player-pose `RunScriptAsync(4,250,13)` —
is **cosmetic**; none of it is needed to save the game. (`Menu(2, <shopId>)` later in tag-3 is the Dali
moogle *also* running a shop — irrelevant to a save point.)

## What ships (v1 — the functional core)

A `[[savepoint]]` is the navigable cousin of [`content/jump.py`](../ff9mapkit/content/jump.py)'s `action`
region — same `Init SetRegion` / tread `Bubble("!")` / action shape — but the action dispatch is
`DisableMove; Menu(4, 0); EnableMove` instead of a player-arc `RunScriptSync`. **Unlike a jump, no
player-function graft is required** — the save is a self-contained engine call.

```toml
[[savepoint]]
zone = [[-275, -1947], [25, -1947], [25, -2247], [-275, -2247]]   # 4- or 5-pt press quad
# bubble = false   # hide the "!" prompt (e.g. when a visible model already signals the save)
```

- `ff9mapkit/eb/opcodes.py` — `menu(menu_id, sub_id=0)` (0x75; `menu(4,0)` = save).
- `ff9mapkit/content/savepoint.py` — `save_dispatch()`, `savepoint_region(zone, *, bubble)`,
  `inject_savepoint` / `inject_savepoints`.
- `build.py` — `[[savepoint]]` validated (zone 4–5 pts) + injected (a 4-pt zone is widened to the
  `quad_zone` doubled-last-vertex convex quad, the `IsInQuad` dead-zone fix).

## The cosmetic layer — two ways to get it

**v1 synthesis (manual cosmetics).** The visible **barrel + moogle** set-dressing and the **jump-out**
animation can be dressed by hand — place a `[[prop]]`/`[[npc]]` over the zone (the `moogle` archetype
(model `GEO_NPC_F0_MOG`), the cask `GEO_ACC_F0_CSK`), optionally with a verbatim graft of the moogle's
jump choreography. The synthesized `[[savepoint]]` is the functional save; you can stand on the zone and
save with no cosmetics at all.

**Faithful verbatim carry (SHIPPED — the full cluster, automatic).** `ff9mapkit import <field>
--save-moogle` carries a real field's save point **verbatim** as a faithful FF9 save point: the hidden
save Moogle pops out of its barrel and runs the full save flourish, exactly as the original. The flag
**implies `--graft-player-funcs`** (the carried objects + pose funcs must exist) and **only fires on a
field that actually has a save point**. It emits a `[[save_moogle]]` block:

```toml
[[save_moogle]]
carried = true                  # the cluster lives in the [[object]]/[[player_func]] blocks the import emits
director = "save_director.eb"   # the source field's main-loop puppeteer, grafted into entry-0 tag-1
```

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
can't self-check is that this **synthesized** region opens the Menu where you stand — that's the per-build
in-game placement gate the human owns (every region trigger has it).
