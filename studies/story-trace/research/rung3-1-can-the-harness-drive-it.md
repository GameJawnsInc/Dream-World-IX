## CAN THE HARNESS DRIVE IT UNATTENDED?

**Short answer:** mostly yes. Every verb it needs exists. But no scenario has ever driven a stock multi-field route, and there is one real gap: the harness cannot seed the party. Everything below comes from reading code and the `eb-src` output. Nothing here was run in-game.

### The verbs (`tools/harness/session.py`)
- **Walk to a point:** `walk_to(x,z)` (:1348). It steers on the published position and returns False cleanly if the field changes mid-walk (:1384). It needs `calibrate_axes`, which is cached per field id (:1171, :1261).
- **Walk into a region and trigger a gateway:** `cross(x,z,expect=)` (:1646) plus `expect_field_change` (:1621). The latter waits for the destination to be playable, not just loaded.
- **Find exits without reading the script:** `find_transitions` (:1683). ⚠ It re-homes with a bare `self.warp(home_field)` (:1731, :1775), which sends `warp N -1 -1`. The PLAN says never to do that because it drops both entrance and SC, so the sweep must not run inside a traced run.
- **Dialogue:** `interact` (:1981), `advance` (:2008), `options`/`option_index`/`select`/`choose` (:2044-2129).
- **Wait out cutscenes:** `wait_control` (:1783) and `watch_cutscene` (:1794), which presses Confirm through boxes. It stops pressing at a choice (:1830) but has no way to choose, so a choice inside a cutscene runs to the timeout.
- **Current field and SC:** `state.field_id` / `state.scenario` (channel.py:218-222), and `expect_field` (:3391).
- **Seeding:** `poke` (:2782), `flag` (:2778), `watch` (:2786), `timescale` (:2978).
- **No party verb:** the agent's verbs only reach `gEventGlobal` (HarnessAgent.cs:714-745).
- **No NPC positions are published:** channel.py has no object list. To talk to an NPC, a scenario has to take the coordinates from the `.eb` and walk there.
- **The ATE prompt** is `B_KEYON(1)`, which is `EventInput.Select = 1u` (EventInput.cs:537). Select goes through `HonoInputManager`, which checks the harness (HonoInputManager.cs:906-930), and `press select` exists (HarnessAgent.cs:1050). This has not been proven in-game.
- **The ATE menu is a script-masked choice:** `EnableDialogChoices(Int16[241]|0x8000)` at `eb-src 450` :432. That is the case where `options()` raises unless the engine publishes `active` (session.py:2066-2078). `option_index` uses `active` when it is present.

### Position space
- The harness publishes `po.pos[0]` and `pos[2]` (HarnessAgent.cs:1165-1167).
- The region test uses `go.transform.position.x/z` (EventEngine.TreadQuad.cs:9-10) against the Int16 region corners (QuadPos.cs).
- `SetRegion` packs each corner as an (x,z) pair of Int16s (content/region.py:381-390).
- I decoded the exit-region centres (entrance written in brackets):

| Field | Exits |
|---|---|
| 350 | →351 (449,6) · →354 (-932,293) · →353 (-1383,2548) · →356 (-686,4156) · →355 (1206,3771) · →358 (114,4452) · **→450 (2426,2544) [1]** |
| 351 | →350 (-1384,469) · →352 (-2,3048) |
| 352 | →351 (-4,-1092) |
| 353 | →350 (728,-1069) · →356 (639,1581) |
| 354 | →350 (906,-227) |
| 355 | →350 (-44,-1724) |
| 356 | →350 (1348,-630) · →353 (-278,-1561) · →358 (1080,1459) |
| 358 | →356 (-860,5158) |
| 450 | **→350 (30,-1770) [25]** |

- 357 and 359 have no region+`Field()` gateway.
- Arriving in 450 on an ordinary entrance places Zidane at (466,-1072) (`eb-src 450` :2399-2408). The walk to the 450→350 exit is about 823u.

### Prior art and what broke
- **No scenario has crossed a stock gateway or walked a multi-field route.** `cross`/`find_transitions` appear only in `gateway_check.py` (bench 30820). `watch_cutscene` has only been proven on benches 30601/30801 (`cutscene_check.py:1-22`). All the Dali rounds were owner playtests (PLAYTEST.md:97-260).
- Things that broke on benches:
  - movement tails contaminated a burst's measurement;
  - calibrating with the back to a wall;
  - a stranded `find_transitions` leg (memory project-ff9-test-harness.md:276-302);
  - a treasure chest walling off about 265u of walkmesh (:479).

### Failure modes
- **Random encounters:** not a factor. 350-359 and 450 contain no `SetRandomBattles` or `Battle` op. The harness cannot switch them off anyway:
  - it has no booster verb (HarnessAgent.cs:528-892);
  - the ~ menu's "No encounters" toggle (Ff9mkDebugMenu.cs:1048) is an IMGUI control no verb reaches;
  - the Shift+F4 key is on the list of inputs the harness cannot send (INPUT-COVERAGE.md, UIKeyTrigger.cs:795).
  - `IsNoEncounter` is `IsBoosterButtonActive[4]` (SettingsState.cs:53). A `booster` verb could be added at the next s88 rebuild.
- **Party:** a stock run started from New Game has whatever party the opening sets (I did not check which). 450 decides who you control with `B_PARTYCHK` (`eb-src 450` :91), and fork-report lists scenes gated on party membership. Two ways around it:
  - the chain's hub pick (it does `party_add`);
  - a real save: title → Continue loads the sandbox autosave; there is no load verb (memory :179-185).
- **Cutscene timing:** `walk_to` does not know about cutscenes. If a region scene takes control mid-walk, it raises or returns False, so each leg needs `watch_cutscene` and then a resume. Example: 450's entry-18 region (x 1460-2100, z -428 to -1105, SC 2600-2640), which is off the path to the exit.
- **Nothing to test against:** the only registered slots in 30800-30860 are 30801, 30830 (now the rung-2 TRC552 fork, ForkDonorPatch 30830→552) and 30860. The chain (30830-30841) and hub 30850 are gone, 30830 is taken, and the chain directory is not in the repo. Redeploying on new ids needs a relaunch.

### The short test: warp straight into 450?
Standing still, 450 does **not** write 2102 by itself. Main_Init (entry 0 func 0) has no 2102 store. The only stores in 450 are:
- **The shared ATE routine (e2 f1):** reads 2102 and clears it to 0 (`eb-src 450` :749).
- **The exit gateway (e19 f2):** writes 2102=1 (:2192/:2196) when 2085==0, SC<2610, `UInt16[297]&1`, and 2079==0. It also sets 2085=1 and 296 to 2 or 3.
- **The kid's every-frame loop (e5 f1):** writes 2102=1 (:1128) in its `Map.Int16[33]==16` branch, then `Field(354)` (:1186-1187).

The kid's-loop branch only opens through Garnet's scene. Entrance 16 spawns Garnet as the player (:91-94), and her setup sets `Map.Int16[33]=1` (:2803). That is the self-playing oglop ATE scene, the one that sends Garnet to the weapon shop.

That gives two short tests, each on a single field:
- **(A)** `warp 450 1 2600`, then `poke 297 1` and `poke 298 0`, then `cross(30,-1770, expect=350)`.
- **(B)** `warp 450 16 2600`, then `watch_cutscene()`. The scene's boxes need Confirm; the 2102 write at :1128 does not depend on 297.

Both are circular for rung 3, because the field and entrance were picked by reading 450's script. They are good as a calibration of the trace, not as retrodiction.

A non-circular route the harness can drive: from the wake room, cross every decoded exit of every field reached, in breadth-first order. That walks 350→450 and back out through e19 without anyone choosing 450. Cost per field is one `calibrate_axes`, one `cross` per exit, and a `watch_cutscene` guard. Re-homing must use a warp with an explicit entrance and SC.

Scratch decompiles are in `<archive>\scratchpad\` (`eb350.txt`…`eb450.txt`, and `quads.py`, which builds the exit table).