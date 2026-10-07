# Forms lane: adversarial verification

I re-read every cited engine and kit line against `C:\gd\FFIX\Memoria\Assembly-CSharp` (working tree = stock plus
the patch stack) and `memoria-patches/`. I re-ran all 14 lane scripts; every number in NOTES.md reproduced. Seven regenerated `out/*.json` files are
byte-identical to a pre-rerun snapshot. The byte check of `prefab_census.json` could not be done, because a sibling
lane's file of the same name overwrote the snapshot in the shared scratchpad. Its printed summary matches the lane,
and every file derived from it reproduced byte-identically. I also added 4 `verify_*.py` scripts that try to break the
most consequential claims. Everything was read-only except `out/` (regenerated) and the new files listed at the end.

**Overall:** the mechanism, census and tiering hold. The main error is **"the clean mid-visit refresh is
`WorldMap(<same id>)` from the world script."** That route is **inert in stock**: a world script has no way to reload
the world (details in F4 and A1). Two smaller errors: the streaming-rebuild path cited in F2 and F4 is dead in shipped
Memoria, and F8 undercounts the world-script writers (6 dispatchers, not 5).

## Verdicts

| id | verdict | note |
|---|---|---|
| F1 | confirmed | WMBlock.cs:10-20/155/164/210, WMWorld.cs:588-600, 638-656, 748-807, 812-858, 601-636 all read as claimed. WMBlock.cs is untouched by every patch. Nuance: at block 219, Sea3/4/5 are form-1 only and Sea3_2/4_2/5_2 form-2 only. The stock special objects added at blocks 158 (disc 4) and 389 sit outside the form lists, so they render in both forms. |
| F2 | corrected | The SetForm/ApplyForm split is right. The "streamed-out blocks are rebuilt on re-entry (WMWorld.cs:1312-1320)" path is **dead** in shipped Memoria: `WorldState.Awake` ends with `DiscardBlockWhenStreaming = false` (WorldState.cs:25), and `ff9.cs:3703` calls `LoadBlocks(false)`, which loads all 480 blocks at once. So ApplyForm runs exactly once per block per visit, plus the debug-only ResetBlockForms/SetBlockForms. |
| F3 | corrected | The core claim holds: the form is decided at scene load, never saved, and is per-block with `_form = 1`. But the "world-to-world jump (WMScriptDirector.cs:225-228)" reload trigger is **not a stock path**: the mode==3 `Replace("WorldMap")` branch is armed only by the custom debug menu (Ff9mkDebugMenu.cs:1595-1606). The stock reload triggers are battle return, field-to-world entry and save load. Refinement: the decision (WMScriptDirector.cs:61) runs **after** the dispatcher's first `ServiceEvents` pass (:60), so writes made in world-script Main_Init land in that same load. The walk-decode-claims.md:685 "fires mid-session" contradiction is decided in the lane's favour. |
| F4 | corrected | Confirmed: there is no clean mid-visit switch. 501 runs ResetBlockForms, then SetForm(2) only, then `SetDisc(1)`, which is a no-op. Conditions are memoized (WorldConfiguration.cs:634-653). Zero dispatchers use 501/502 (reproduced). Keypad9's `UpdateInput` has no caller. WMBeeMenu's form buttons are gated off outside the Bee scene (`showRightMenu = false`). **Refuted sub-claim:** "clean path: WMAPJUMP 0xB6 -> mode 3 -> Replace". In the world, WMAPJUMP only writes `FF9World.map.nextMapNo` and returns 5. `WMScriptDirector.HonoUpdate20FPS` handles results 3 and 4 only. 0 of 13 stock world dispatchers contain 0xB6 (`verify_world_eb_mapjumps.py`, `verify_world_reload_chain.py`). The real refresh routes are a Field() round trip, a battle, or an engine hook. Also, with no streaming, a 501 flip leaves the render on form 1 for the **whole** visit, not "until blocks stream out and back". |
| F5 | confirmed | Reproduced: on disc 1, list length is 1/2 at (13,12) and (14,12), and the index-0 role differs at (7,1), (8,1), (13,12) and (14,12). The cache is rebuilt per load (ff9.cs:1465-1466) and never invalidated mid-visit. A 1->2 flip feeds a cached Terrain1 triangle index (up to 541) into Object2 (36 tris), which is unchecked at WMPhysics.cs:56. A 2->1 flip, such as 501's ResetBlockForms, can hit WMBlock.cs:219. Only 501 reaches either. |
| F6 | confirmed | WorldConfiguration.cs:165-193 and 93-121, NCalc :94/:125/:272/:307, and EvaluationVisitor :179-181 read as cited. NCalc also supports `<<`/`>>` (:191/:195). `label_forms.py`'s check can fail and passed on rerun. The memory note project-ff9-overworld-worlds.md:95 ("RELAUNCH to apply") is superseded at source level: `PatchWorldEnvironment` clears and re-reads every folder's file on every `HonoAwake`. Caveats: a folder newly added to `FolderNames` still needs a relaunch, and none of this is in-game proven. |
| F7 | corrected | OR-accumulation, parse order, kit emitter with no `Clear`, and `Clean` (stock header lines 43-49) vs the parser's `Clear` (:400/:407) are all confirmed. One count is off: the kit's `WORLD_PLACES` has **65** names, matching the WorldPlace enum including `Dummy`, not 64. Note that `Place Clear` alone wipes **every** place's custom conditions from lower-priority folders, not just one place. |
| F8 | corrected | It is **6** dispatchers (world00/03/05/07/08/**09**) and **12** `B_LET` writes, plus 12 entry-0 reads (24 refs total). The lane printed only the first 20 hits and missed world09. Tag 15 in world00/03/05/07, tag 16 in world08/09. Bit mapping checked: 815 -> byte 101, 0x80 (Mognet); 814 -> 0x40 (Chocobo). |
| F9 | confirmed | `census_prefabs.py` and `probe_scene_worlddisc.py` reproduce: 26 switchable / 205 sea; scene sets equal prefab sets in level7 and level19; 0 slot->dir mismatches; Form lists empty. Child names are confirmed as Terrain2/Object2. |
| F10 | confirmed | All walk numbers and classes reproduce (disc 1 9/4/13, disc 4 8/2/16). Attack 1: the sampler omits the engine's 4078/4088/2040 skips and the 0x31EE mesh reject. Those IDs occur only on (16,14) and (9,17), both NO-OP cells, and 0 cells' numbers move with the filters applied (`verify_raycast_exceptions.py`, calibrated). Attack 2: multiset equality could hide changes in triangle order, winding or normals. All 9 disc-1 NO-OP cells are identical as ordered arrays (verts, tris, UVs, tangents, normals) (`verify_noop_exact.py`). |
| F11 | confirmed | Reproduced: Terrain2 is a disc-1 copy on 15/20 disc-gated cells and Object2 on 12/18; disc-4 Terrain1 differs from disc 1 on 23/26 cells; walk change (17,12) 1040, (14,16) 1395, (18,14) 335. |
| F12 | confirmed | 94/56/38 (disc 1) and 93/55/38 (disc 4); every orphan is a water/beach/river/stream/falls part on a switchable cell; 7 (disc 1) and 9 (disc 4) differ. The (19,11) river really is 17 vs 66 total tris. The only `0_2` reference in source is WMWorldPrefabMaker.cs:36. |
| F13 | confirmed | It stays a hypothesis, but source gives no way to break it. The key is the **prefab child's** `transform.name` (WMWorld.cs:823-825; s34 patch :82-84), and the census child names are `Terrain2`/`Object2`. `TryLoad` is part-generic, and `ObjectNameToPaths` maps Terrain2/Object2 to the same atlases (WMBlock.cs:313/315), so reskins apply to form 2 too. `override_relpath(part="Terrain2")` keeps `0_1`, which is correct; passing `lod="0_2"` would silently miss. Note: an Object2 override has a target on all 26 cells on disc 1 but only 25 on disc 4 ((13,4) has no ObjectForm2). The README.md:1235/1223 contradiction is decided for the lane. |
| F14 | confirmed | Reproduced: 1686 files (9:395, 4:646, 1:645); 0 of 1291 disc-1/4 files on switchable cells; the one hit is Path D (14,12). BLANK/CLONE match WorldDiscSpike.cs:187-198, and `CloneStockWorld` defaults to false. Nuance: in CLONE mode the (14,12) Sea3/4/5 overrides labelled "shared" would not load at all, because stock prefab (14,12) has no Sea slots. The Terrain form-1-only trap stands. |
| F15 | confirmed | `SetForm` gates on the **scene** WMBlock (mw_worldSetFormBit uses `InitialBlocks`). Form-2 components come only from prefab slots. Scene levels cannot be overridden from a mod folder, so no data route exists. The 3-step patch is a sound hypothesis: `WMWorld.Initialize` (`HonoAwake`:40) runs before `w_frameSystemConstructor` (:61). The renamed copy needs the extra name parameter, because `RegisterBlockComponent` keys the override on the source transform's name (`"Terrain"`). |
| F16 | confirmed | extract.py:11 says "0_2 is a far LOD". WMWorldPrefabMaker.cs:36, 120-139 (cited as 119-138) and 159-166 load `0_2` only into the form-2 slots, so `0_2` is the form-2 set. Census mismatches: 0. The lane is right. |
| F17 | corrected | The tiers stand: Tier 0 per F6, Tier 1 per F13 with Black Mage Village array-identical, Tier 2 per F15, and no rebake. The F0/F1 rung numbers reproduce (`rung_site.py`). `Ff9mkDebugMenu.cs:1383` prints `Form=` plus both walk lists. Correction: "mid-visit changes need a world reload" is right, but a world script **cannot trigger one** in stock. The proposed experiment "Same-id world reload" is predicted inert via the .eb route; it works only through the debug menu's ArmWorldReload. Caution, untested: F0 adds 257 entrance-event samples; stepping on them at a non-10600 story counter could fire a Water Shrine `Field()` at the wrong story state. |

## Additional findings

- **A1. No stock world-to-world reload.** A world-originated `WorldMap()` is inert, and the world tick's mode==3
  `Replace("WorldMap")` branch is reached only by the custom debug menu. This agrees with the recorded memory
  `project-ff9-f6-overworld-debug.md:142` ("there is NO native world→world path"). Without noticing, the lane
  contradicts that recorded law, and the law is right. Evidence: `verify_world_reload_chain.py`,
  `verify_world_eb_mapjumps.py` (0 WMAPJUMP across 13 dispatchers; calibrated with 597 Field() ops and
  RunWorldCode(26) = 18).
- **A2. Block streaming is dead in shipped Memoria:** WorldState.cs:19 is overwritten by :25 =
  `DiscardBlockWhenStreaming false`, and ff9.cs:3703 is `LoadBlocks(false)`. Two consequences: a walk-only form flip
  is never repaired by a render rebuild during the visit, and the open question about Form2Transforms clearing at
  WMWorld.cs:1317 is moot for normal play.
- **A3. diff_forms.py is not engine-faithful for reuse.** It omits the WMPhysics.cs:15-20 exception IDALLs and the
  WMBlock.cs:211 0x31EE mesh reject. Its current outputs are unaffected (proven), but any future bench prediction on
  cells carrying those IDs must add them.
- **A4. F8 recount:** world09 also writes Bits 814 and 815 (tag 16). That makes 6 free-roam dispatchers and 12 writes.

## Scripts added (rerun from this directory)

```
py verify_world_reload_chain.py   # F3/F4/F17: WMAPJUMP=5, world tick handles {3,4}, attr-0x1000 writers
py verify_world_eb_mapjumps.py    # F4: 0 WMAPJUMP in 13 world dispatchers (calibrated)
py verify_raycast_exceptions.py   # F10/F5: engine exception filters move 0 cells (calibrated)
py verify_noop_exact.py           # F10/F17: NO-OP cells identical as ordered arrays (calibrated)
```
