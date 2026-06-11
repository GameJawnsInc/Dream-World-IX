# Save-point synthesis (`[[savepoint]]`)

A functional FF9 **save point** — the save Moogle's *save* — synthesized as a press-to-interact region.
The deferred capstone after the object / player / text carry arc: instead of grafting the real save
moogle's un-graftable 7-entry-ish cluster (5 hidden objects + STARTSEQ helpers + player-pose surgery +
a `gEventGlobal` contract), the kit **synthesizes** the save from its functional core.

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

## Deferred (the cosmetic layer)

The visible **barrel + moogle** set-dressing and the **jump-out** animation are a later layer — place a
`[[prop]]`/`[[npc]]` over the zone (the moogle archetype `GEO_NPC_F0_MOG`, the cask `GEO_ACC_F0_CSK`),
optionally with a verbatim graft of the moogle's jump choreography. v1 is the functional save; you can
already stand on the zone and save.

## The one thing the kit can't self-verify

That the save menu **opens, writes a slot, and reloads** correctly **in a custom field (id ≥ 4000)** —
the save→Continue-into-a-custom-field path was previously untested (see the worldmap-feasibility note).
That's the in-game gate.
