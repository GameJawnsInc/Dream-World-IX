# Fork-fidelity: engine behaviors gated on the real field id

> Auto-generated from a 9-agent sweep of Memoria `6b8bb2d5` (2026-06-17). A custom-id **fork**
> of a real field loses any behavior the engine hardcodes on that field's id (`fldMapNo == N`,
> id-keyed tables, name checks). The fork→donor-id remap engine patch restores them.

**280 gates found · 265 lost on a custom-id fork** — SOFTLOCK 12 · FUNCTIONAL 142 · COSMETIC 111.

## SOFTLOCK — a fork hangs / can't progress (patch these first)

| field id(s) | site | behavior | notes |
|---|---|---|---|
| 3009 | `Dialog.cs:820` | In AutoHide coroutine, on the Epilogue Stage field calls DialogManager.ForceControlByEvent(false) and yield-breaks (skips the timed auto-close wait), handing control back to the event. | Real fldMapNo == gate (field 3009 = Epilogue: Stage). A custom-id fork of 3009 falls through to the normal timed AutoHide instead of returning control to the ev |
| 3010 | `Dialog.cs:826` | Same as 3009: ForceControlByEvent(false) + yield-break in AutoHide for the Epilogue Stage field 3010. | Real fldMapNo == gate (field 3010 = Epilogue: Stage). Fork loses the event-control handoff in AutoHide; same break as 3009. |
| 100 | `DialogManager.cs:214` | In Close(), on Alexandria/Main Street when Map-byte-31 var == 3 (Puck hits Vivi), immediately calls dialog.AfterHidden() to force-finish the dialog instead of waiting for the close animation. | Real fldMapNo == gate (field 100 = Alexandria/Main Street, intro). A custom-id fork loses the immediate AfterHidden() flush during the Puck-hits-Vivi scripted b |
| 2200 | `EventEngine.cs:657` | Hotfix: clears the whole party (sets 4 slots to NONE) right after obtaining the Gulug Stone, even if AllCharactersAvailable=2. | Palace/Dungeon. This is a script-correctness hotfix; the comment notes the script normally adds characters back. A fork at a custom id misses it, so with AllCha |
| 2207 | `EventEngine.cs:667` | Hotfix: forces the party to be exactly Oeilvert's team (Zidane + up to 3 of Garnet/Amarant/Quina/Freya/Vivi/Steiner/Eiko chosen by VARL_GenBool_3536..3542) when bringing the Gulug Stone back. | Palace/Hall. Comment says it prevents another soft-lock later. A fork loses the forced-team correction => possible soft-lock / wrong party in the following cuts |
| 2301 | `EventEngine.cs:687` | Hotfix: ensures at least one normal character (forces Zidane+Steiner) for the Esto Gaza Priest cutscene if the party has none of Garnet/Steiner/Freya/Quina/Amarant. | Esto Gaza/Altar. Guards a cutscene that needs a normal actor present. A fork loses it => the cutscene can run with an unsupported party and soft-lock. Scenario  |
| 2362 | `EventEngine.cs:700` | Hotfix: forces a normal team (Zidane/Vivi/Steiner/Garnet) for the cutscene at the bottom of Gulug when Zidane or Vivi is missing or Eiko/non-standard members are present. | Gulug/Path. Cutscene party-shape guard. A fork loses it => possible soft-lock with wrong party. Scenario+flag gated. |
| 768 | `EventEngine.updateModelsToBeAdded.cs:80` | After the Beatrix battle in Burmecia/Palace, repositions and re-poses 7 actors (Brahne, Kuja, Zidane, Vivi, Freya, Quina, Beatrix) to fixed coordinates/animations (fix #664). | Burmecia/Palace post-battle reinit. A fork at a custom id loses the actor repositioning => the after-battle cutscene actors are in wrong spots/poses, and the sc |
| 2504,105,2605 | `FieldMapActorController.cs:923` | UpdateActiveTri: early-returns to EXEMPT the actor from per-frame walkmesh tri-snapping | THE canonical case. 2504 sid14 = I.Castle/Small Room Chest_TerranA (Fork chest); 105 sid4 = Alexandria/Alley Dante (ladder-climbing signmaker); 2605 sid11 = Ter |
| 2507 | `FieldMap.cs:102` | Starts DelayedActiveTri coroutine that disables NPC char-collision and specific walkmesh triangles after 0.5s (ladders+stairs room) | Also gated again at line 139 inside the coroutine. Disables tris 174/175/177/178 and de-activates non-player actor collision. A fork loses both → the ladder/sta |
| 1656 | `FieldMap.cs:1495` | Binds the player controller to obj uid 8 (selects Zidane) when none is set, before a scroll-release | Also see 1972 (SceneService3DScroll CrutchForEvaMap on 1656). This 'crutch' picks the controllable actor for a scripted scroll where playerController is null. A |
| 2512 | `FieldMap.cs:1966` | Binds player controller to obj uid 2 when null, so 3D scroll can track the player | Same 'crutch' pattern as 1656. Fork loses → playerController null during this Ipsen cutscene scroll → camera/scroll has nothing to follow → beat can stall. Soft |

## By field id (playtest lookup: forking field N? check here)

| field | worst | # gates | sites |
|---|---|---|---|
| 50 | COSMETIC | 1 | CommonSPSSystem.cs:230 |
| 51 | FUNCTIONAL | 2 | CommonSPSSystem.cs:230, FieldMap.cs:2532 |
| 52 | FUNCTIONAL | 1 | EventEngine.ProcessEvents.cs:518 |
| 60 | COSMETIC | 1 | SceneDirector.cs:593 |
| 64 | FUNCTIONAL | 2 | EMinigame.cs:12, EventHUD.cs:346 |
| 70 | FUNCTIONAL | 1 | EventEngine.cs:638 |
| 100 | SOFTLOCK | 2 | DialogManager.cs:214, fldfmv.cs:112 |
| 103 | FUNCTIONAL | 4 | EMinigame.cs:112, EMinigame.cs:136, EventCollision.cs:340, FieldMap.cs:686 |
| 105 | SOFTLOCK | 1 | FieldMapActorController.cs:923 |
| 107 | FUNCTIONAL | 1 | EventCollision.cs:340 |
| 112 | FUNCTIONAL | 1 | EMinigame.cs:345 |
| 116 | COSMETIC | 1 | FieldMapActorController.cs:472 |
| 150 | FUNCTIONAL | 1 | EventEngine.cs:640 |
| 153 | FUNCTIONAL | 1 | BGSCENE_DEF.cs:925 |
| 154 | FUNCTIONAL | 1 | FieldMap.cs:666 |
| 155 | FUNCTIONAL | 1 | SPSEffect.cs:244 |
| 162 | COSMETIC | 3 | CommonSPSSystem.cs:134, CommonSPSSystem.cs:136, CommonSPSSystem.cs:138 |
| 163 | COSMETIC | 2 | CommonSPSSystem.cs:140, CommonSPSSystem.cs:142 |
| 204 | COSMETIC | 1 | EMinigame.cs:543 |
| 205 | FUNCTIONAL | 2 | CommonSPSSystem.cs:128, FieldMapActorController.cs:329 |
| 206 | COSMETIC | 2 | EMinigame.cs:534, ETb.cs:424 |
| 207 | COSMETIC | 1 | CommonSPSSystem.cs:130 |
| 253 | COSMETIC | 1 | EMinigame.cs:543 |
| 257 | FUNCTIONAL | 1 | EventEngine.ProcessEvents.cs:109 |
| 262 | COSMETIC | 2 | CommonSPSSystem.cs:132, EMinigame.cs:545 |
| 301 | FUNCTIONAL | 1 | EventEngine.ProcessEvents.cs:25 |
| 302 | FUNCTIONAL | 1 | EventEngine.ProcessEvents.cs:31 |
| 303 | FUNCTIONAL | 2 | CommonSPSSystem.cs:126, EventEngine.ProcessEvents.cs:18 |
| 304 | FUNCTIONAL | 1 | EventEngine.ProcessEvents.cs:18 |
| 306 | COSMETIC | 1 | EMinigame.cs:550 |
| 312 | COSMETIC | 3 | FieldMap.cs:1655, FieldMap.cs:703, TileSystem.cs:670 |
| 350 | FUNCTIONAL | 2 | EventCollision.cs:532, FieldMapActorController.cs:351 |
| 352 | COSMETIC | 1 | EMinigame.cs:86 |
| 404 | FUNCTIONAL | 1 | FieldMapActorController.cs:328 |
| 406 | FUNCTIONAL | 1 | FieldMapActorController.cs:1240 |
| 455 | COSMETIC | 1 | EMinigame.cs:233 |
| 456 | COSMETIC | 1 | FieldMap.cs:703 |
| 457 | COSMETIC | 1 | EMinigame.cs:233 |
| 503 | COSMETIC | 1 | AllSoundDispatchPlayer.cs:135 |
| 505 | COSMETIC | 1 | FieldMap.cs:703 |
| 507 | FUNCTIONAL | 2 | EventCollision.cs:534, FieldMap.cs:662 |
| 552 | FUNCTIONAL | 3 | BGSCENE_DEF.cs:1721, BGSCENE_DEF.cs:1733, EMinigame.cs:562 |
| 554 | COSMETIC | 1 | EMinigame.cs:562 |
| 558 | COSMETIC | 1 | EMinigame.cs:329 |
| 565 | COSMETIC | 1 | EMinigame.cs:562 |
| 566 | FUNCTIONAL | 1 | EventCollision.cs:536 |
| 575 | FUNCTIONAL | 1 | FieldMap.cs:2532 |
| 576 | COSMETIC | 1 | FieldMapActorController.cs:441 |
| 600 | COSMETIC | 1 | EMinigame.cs:300 |
| 606 | FUNCTIONAL | 1 | EventInput.cs:142 |
| 609 | COSMETIC | 1 | FieldMap.cs:657 |
| 656 | FUNCTIONAL | 1 | EventCollision.cs:500 |
| 657 | FUNCTIONAL | 2 | EBin.cs:730, EventCollision.cs:500 |
| 658 | FUNCTIONAL | 1 | EventCollision.cs:500 |
| 659 | FUNCTIONAL | 1 | EventCollision.cs:500 |
| 661 | COSMETIC | 1 | FieldMapActor.cs:181 |
| 705 | FUNCTIONAL | 1 | EBin.cs:323 |
| 767 | FUNCTIONAL | 1 | FieldMap.cs:2532 |
| 768 | SOFTLOCK | 1 | EventEngine.updateModelsToBeAdded.cs:80 |
| 805 | COSMETIC | 1 | FieldMap.cs:1655 |
| 808 | COSMETIC | 1 | FieldMap.cs:1655 |
| 813 | FUNCTIONAL | 1 | FieldMap.cs:1503 |
| 900 | FUNCTIONAL | 2 | EventEngine.turnOffTriManually.cs:14, FieldMapActorController.cs:331 |
| 903 | FUNCTIONAL | 1 | EMinigame.cs:345 |
| 908 | FUNCTIONAL | 4 | EBin.cs:714, EMinigame.cs:329, EMinigame.cs:354, FieldMap.cs:1655 |
| 909 | FUNCTIONAL | 2 | EMinigame.cs:293, EventInput.cs:190 |
| 911 | COSMETIC | 3 | CommonSPSSystem.cs:177, CommonSPSSystem.cs:213, EMinigame.cs:177 |
| 916 | FUNCTIONAL | 1 | FieldMapActorController.cs:337 |
| 931 | FUNCTIONAL | 2 | FieldMap.cs:2532, FieldMap.cs:649 |
| 956 | COSMETIC | 1 | EMinigame.cs:625 |
| 1005 | FUNCTIONAL | 1 | FieldMapActorController.cs:339 |
| 1051 | COSMETIC | 1 | NarrowMapList.cs:932 |
| 1055 | FUNCTIONAL | 1 | FieldMap.cs:666 |
| 1056 | FUNCTIONAL | 1 | FieldMapActorController.cs:1348 |
| 1057 | COSMETIC | 1 | NarrowMapList.cs:932 |
| 1058 | COSMETIC | 1 | NarrowMapList.cs:932 |
| 1060 | FUNCTIONAL | 2 | EventEngineUtils.cs:1855, NarrowMapList.cs:932 |
| 1106 | FUNCTIONAL | 1 | FieldMapActorController.cs:1348 |
| 1108 | COSMETIC | 1 | FieldMap.cs:1655 |
| 1109 | COSMETIC | 1 | EMinigame.cs:246 |
| 1153 | COSMETIC | 1 | FieldMap.cs:703 |
| 1204 | COSMETIC | 1 | FieldMapActorController.cs:213 |
| 1205 | FUNCTIONAL | 1 | FieldMap.cs:666 |
| 1206 | COSMETIC | 1 | CommonSPSSystem.cs:198 |
| 1208 | FUNCTIONAL | 1 | EventHUD.cs:359 |
| 1214 | FUNCTIONAL | 1 | BGSCENE_DEF.cs:925 |
| 1215 | FUNCTIONAL | 1 | FieldMap.cs:666 |
| 1216 | FUNCTIONAL | 1 | SPSEffect.cs:244 |
| 1223 | COSMETIC | 1 | CommonSPSSystem.cs:198 |
| 1251 | FUNCTIONAL | 1 | EventEngine.cs:641 |
| 1306 | COSMETIC | 1 | EMinigame.cs:329 |
| 1307 | COSMETIC | 1 | EMinigame.cs:590 |
| 1315 | FUNCTIONAL | 1 | FieldMapActorController.cs:352 |
| 1353 | COSMETIC | 1 | EMinigame.cs:595 |
| 1410 | FUNCTIONAL | 1 | FieldMapActor.cs:243 |
| 1412 | FUNCTIONAL | 1 | FieldMapActor.cs:243 |
| 1413 | FUNCTIONAL | 1 | FieldMapActor.cs:135 |
| 1414 | FUNCTIONAL | 1 | FieldMapActor.cs:141 |
| 1420 | FUNCTIONAL | 3 | EventInput.cs:155, EventInput.cs:367, EventInput.cs:95 |
| 1421 | FUNCTIONAL | 3 | EMinigame.cs:381, EMinigame.cs:388, EMinigame.cs:500 |
| 1422 | FUNCTIONAL | 1 | EventInput.cs:159 |
| 1455 | FUNCTIONAL | 1 | EventEngine.turnOffTriManually.cs:32 |
| 1505 | FUNCTIONAL | 1 | BGSCENE_DEF.cs:925 |
| 1508 | FUNCTIONAL | 2 | FieldMap.cs:580, FieldMap.cs:582 |
| 1601 | COSMETIC | 1 | FieldMapActorController.cs:540 |
| 1602 | FUNCTIONAL | 1 | EventEngine.cs:642 |
| 1603 | FUNCTIONAL | 1 | EventCollision.cs:540 |
| 1606 | COSMETIC | 1 | FieldMapActorController.cs:486 |
| 1607 | FUNCTIONAL | 1 | EventInput.cs:151 |
| 1608 | FUNCTIONAL | 2 | Dialog.cs:1609, EventCollision.cs:542 |
| 1610 | COSMETIC | 1 | FieldMapActorController.cs:528 |
| 1651 | COSMETIC | 1 | FieldMap.cs:1655 |
| 1652 | FUNCTIONAL | 2 | ETb.cs:290, FieldMap.cs:666 |
| 1653 | COSMETIC | 1 | NarrowMapList.cs:932 |
| 1655 | FUNCTIONAL | 1 | FieldMap.cs:2532 |
| 1656 | SOFTLOCK | 3 | Actor.cs:26, FieldMap.cs:1495, FieldMap.cs:1972 |
| 1657 | COSMETIC | 2 | ETb.cs:123, FieldMap.cs:1655 |
| 1659 | COSMETIC | 3 | ETb.cs:301, FieldMapActor.cs:183, FieldMapActor.cs:185 |
| 1660 | COSMETIC | 1 | FieldMap.cs:1655 |
| 1661 | COSMETIC | 1 | SceneDirector.cs:598 |
| 1663 | FUNCTIONAL | 1 | HonoluluFieldMain.cs:301 |
| 1704 | FUNCTIONAL | 2 | EMinigame.cs:59, EventHUD.cs:369 |
| 1706 | COSMETIC | 2 | FieldMap.cs:582, FieldMap.cs:608 |
| 1707 | FUNCTIONAL | 1 | FieldMapActor.cs:147 |
| 1751 | FUNCTIONAL | 2 | BGSCENE_DEF.cs:925, FieldMapActorController.cs:327 |
| 1752 | FUNCTIONAL | 2 | BGSCENE_DEF.cs:925, FieldMapActorController.cs:1235 |
| 1753 | FUNCTIONAL | 1 | BGSCENE_DEF.cs:925 |
| 1754 | FUNCTIONAL | 1 | FieldMap.cs:2532 |
| 1757 | FUNCTIONAL | 1 | EventEngine.cs:643 |
| 1758 | COSMETIC | 1 | FieldMap.cs:1655 |
| 1806 | FUNCTIONAL | 1 | BGSCENE_DEF.cs:925 |
| 1807 | FUNCTIONAL | 2 | FieldMap.cs:666, FieldMapActorController.cs:1348 |
| 1808 | FUNCTIONAL | 1 | SPSEffect.cs:244 |
| 1823 | FUNCTIONAL | 1 | BGSCENE_DEF.cs:925 |
| 1850 | FUNCTIONAL | 5 | EMinigame.cs:404, EMinigame.cs:413, EMinigame.cs:697, ETb.cs:114, ETb.cs:401 |
| 1853 | COSMETIC | 1 | FieldMap.cs:686 |
| 1856 | FUNCTIONAL | 2 | EventCollision.cs:342, EventCollision.cs:544 |
| 1858 | COSMETIC | 1 | EMinigame.cs:211 |
| 1900 | FUNCTIONAL | 3 | EBin.cs:319, EMinigame.cs:204, EventEngine.turnOffTriManually.cs:8 |
| 1903 | FUNCTIONAL | 1 | EMinigame.cs:345 |
| 1908 | FUNCTIONAL | 4 | EBin.cs:714, EMinigame.cs:329, EMinigame.cs:354, FieldMap.cs:1655 |
| 1909 | FUNCTIONAL | 2 | EMinigame.cs:293, EventInput.cs:190 |
| 1911 | COSMETIC | 3 | CommonSPSSystem.cs:177, CommonSPSSystem.cs:213, EMinigame.cs:177 |
| 2050 | FUNCTIONAL | 1 | FieldMapActorController.cs:350 |
| 2053 | COSMETIC | 1 | FieldMap.cs:686 |
| 2102 | COSMETIC | 1 | FieldMapActor.cs:190 |
| 2103 | FUNCTIONAL | 1 | EventCollision.cs:468 |
| 2106 | COSMETIC | 1 | EMinigame.cs:329 |
| 2107 | COSMETIC | 1 | FieldMapActor.cs:190 |
| 2108 | FUNCTIONAL | 4 | EventCollision.cs:294, EventCollision.cs:369, EventCollision.cs:401, EventCollision.cs:458 |
| 2109 | FUNCTIONAL | 1 | EventCollision.cs:463 |
| 2113 | COSMETIC | 1 | EMinigame.cs:636 |
| 2150 | FUNCTIONAL | 1 | FieldMapActorController.cs:330 |
| 2159 | COSMETIC | 1 | FieldMap.cs:657 |
| 2161 | FUNCTIONAL | 2 | EventEngine.cs:646, FieldMap.cs:119 |
| 2169 | COSMETIC | 1 | EMinigame.cs:636 |
| 2173 | COSMETIC | 1 | EMinigame.cs:636 |
| 2200 | SOFTLOCK | 3 | EventEngine.cs:639, EventEngine.cs:657, FieldMap.cs:2532 |
| 2204 | FUNCTIONAL | 2 | EventHUD.cs:374, EventInput.cs:147 |
| 2207 | SOFTLOCK | 3 | EventEngine.cs:667, FieldMapActorController.cs:799, UIKeyTrigger.cs:484 |
| 2209 | COSMETIC | 1 | ETb.cs:309 |
| 2215 | COSMETIC | 1 | CommonSPSSystem.cs:116 |
| 2251 | COSMETIC | 1 | FieldMap.cs:1655 |
| 2252 | FUNCTIONAL | 2 | BGSCENE_DEF.cs:925, FieldMap.cs:1655 |
| 2259 | FUNCTIONAL | 1 | BGSCENE_DEF.cs:925 |
| 2301 | SOFTLOCK | 3 | CommonSPSSystem.cs:118, CommonSPSSystem.cs:120, EventEngine.cs:687 |
| 2302 | COSMETIC | 2 | CommonSPSSystem.cs:118, CommonSPSSystem.cs:120 |
| 2304 | COSMETIC | 2 | CommonSPSSystem.cs:122, CommonSPSSystem.cs:124 |
| 2351 | FUNCTIONAL | 1 | FieldMap.cs:1163 |
| 2356 | FUNCTIONAL | 1 | FieldMap.cs:112 |
| 2362 | SOFTLOCK | 1 | EventEngine.cs:700 |
| 2363 | COSMETIC | 2 | FieldMapActor.cs:169, FieldMapActor.cs:187 |
| 2456 | COSMETIC | 2 | EMinigame.cs:112, EMinigame.cs:136 |
| 2457 | COSMETIC | 1 | EMinigame.cs:419 |
| 2504 | SOFTLOCK | 3 | EventCollision.cs:403, FieldMapActorController.cs:1348, FieldMapActorController.cs:923 |
| 2507 | SOFTLOCK | 1 | FieldMap.cs:102 |
| 2510 | COSMETIC | 1 | FieldMapActor.cs:164 |
| 2512 | SOFTLOCK | 1 | FieldMap.cs:1966 |
| 2552 | FUNCTIONAL | 1 | FieldMap.cs:666 |
| 2553 | COSMETIC | 1 | CommonSPSSystem.cs:169 |
| 2600 | COSMETIC | 1 | FieldMap.cs:1655 |
| 2602 | COSMETIC | 1 | FieldMap.cs:1655 |
| 2604 | COSMETIC | 1 | FieldMap.cs:1655 |
| 2605 | SOFTLOCK | 3 | BGSCENE_DEF.cs:925, FieldMap.cs:1655, FieldMapActorController.cs:923 |
| 2606 | COSMETIC | 2 | FieldMap.cs:1655, FieldMap.cs:686 |
| 2607 | COSMETIC | 1 | FieldMap.cs:1655 |
| 2651 | COSMETIC | 1 | FieldMap.cs:1655 |
| 2653 | FUNCTIONAL | 2 | BGSCENE_DEF.cs:925, fldchar.cs:73 |
| 2654 | COSMETIC | 1 | fldchar.cs:73 |
| 2660 | COSMETIC | 1 | FieldMap.cs:1655 |
| 2711 | FUNCTIONAL | 1 | EventHUD.cs:396 |
| 2712 | FUNCTIONAL | 1 | FieldMapActorController.cs:1348 |
| 2714 | FUNCTIONAL | 2 | BGSCENE_DEF.cs:1837, BGSCENE_DEF.cs:925 |
| 2716 | COSMETIC | 1 | FieldMap.cs:703 |
| 2752 | FUNCTIONAL | 3 | EventEngine.cs:644, FieldMapActor.cs:147, MBG.cs:339 |
| 2755 | COSMETIC | 1 | FieldMap.cs:1150 |
| 2801 | FUNCTIONAL | 2 | EBin.cs:317, EMinigame.cs:204 |
| 2802 | FUNCTIONAL | 2 | EventCollision.cs:371, EventCollision.cs:473 |
| 2803 | FUNCTIONAL | 1 | EventEngine.turnOffTriManually.cs:40 |
| 2851 | COSMETIC | 1 | FieldMap.cs:1655 |
| 2855 | FUNCTIONAL | 2 | EventEngine.ProcessTurn.cs:18, EventEngine.ProcessTurn.cs:35 |
| 2901 | COSMETIC | 1 | SPSEffect.cs:231 |
| 2903 | COSMETIC | 3 | FieldMap.cs:1365, FieldMap.cs:688, FieldMap.cs:703 |
| 2913 | COSMETIC | 2 | EventEngine.ProcessEvents.cs:576, SPSEffect.cs:231 |
| 2914 | FUNCTIONAL | 1 | EventCollision.cs:373 |
| 2916 | COSMETIC | 1 | FieldMap.cs:1655 |
| 2919 | FUNCTIONAL | 1 | EventEngine.GetSysvar.cs:71 |
| 2921 | FUNCTIONAL | 2 | EventEngine.ProcessEvents.cs:37, EventHUD.cs:379 |
| 2922 | FUNCTIONAL | 2 | BGSCENE_DEF.cs:925, FieldMap.cs:1655 |
| 2923 | FUNCTIONAL | 3 | BGSCENE_DEF.cs:925, FieldMap.cs:1655, FieldMap.cs:690 |
| 2924 | FUNCTIONAL | 2 | BGSCENE_DEF.cs:925, FieldMap.cs:615 |
| 2925 | FUNCTIONAL | 2 | BGSCENE_DEF.cs:925, SPSEffect.cs:231 |
| 2926 | FUNCTIONAL | 1 | BGSCENE_DEF.cs:925 |
| 2928 | COSMETIC | 1 | CommonSPSSystem.cs:198 |
| 2929 | FUNCTIONAL | 1 | SPSEffect.cs:254 |
| 2933 | FUNCTIONAL | 5 | MBG.cs:356, MBG.cs:409, MBG.cs:547, MBG.cs:553, MovieMaterialProcessor.cs:11 |
| 2950 | FUNCTIONAL | 7 | Dialog.cs:741, EMinigame.cs:264, EventCollision.cs:546, EventEngine.ProcessAnime.cs:48, EventEngine.ProcessAnime.cs:73,  |
| 2951 | FUNCTIONAL | 7 | Dialog.cs:1633, Dialog.cs:733, EMinigame.cs:264, EventEngine.ProcessAnime.cs:48, EventEngine.ProcessAnime.cs:73, EventHU |
| 2952 | FUNCTIONAL | 7 | Dialog.cs:733, EMinigame.cs:264, EventEngine.ProcessAnime.cs:48, EventEngine.ProcessAnime.cs:73, EventHUD.cs:384, FieldM |
| 2953 | FUNCTIONAL | 4 | EventEngine.ProcessAnime.cs:48, SmoothFrameUpdater_Field.cs:119, SmoothFrameUpdater_Field.cs:196, SmoothFrameUpdater_Fie |
| 2954 | FUNCTIONAL | 5 | Actor.cs:24, EventEngine.ProcessAnime.cs:48, EventEngine.ProcessAnime.cs:73, FieldMapActor.cs:261, FieldMapActorControll |
| 2955 | FUNCTIONAL | 5 | EMinigame.cs:365, EventEngine.ProcessAnime.cs:48, EventEngine.ProcessAnime.cs:73, FieldMapActorController.cs:1348, Field |
| 3000 | FUNCTIONAL | 2 | FieldMap.cs:2364, FieldMap.cs:2532 |
| 3001 | FUNCTIONAL | 3 | EventEngine.cs:645, FieldMap.cs:2364, FieldMap.cs:2532 |
| 3002 | FUNCTIONAL | 3 | FieldMap.cs:2364, FieldMap.cs:2532, FieldMapActor.cs:297 |
| 3003 | FUNCTIONAL | 2 | FieldMap.cs:2364, FieldMap.cs:2532 |
| 3004 | FUNCTIONAL | 2 | FieldMap.cs:2364, FieldMap.cs:2532 |
| 3005 | FUNCTIONAL | 2 | FieldMap.cs:2364, FieldMap.cs:2532 |
| 3006 | FUNCTIONAL | 2 | FieldMap.cs:2364, FieldMap.cs:2532 |
| 3007 | FUNCTIONAL | 2 | FieldMap.cs:2364, FieldMap.cs:2532 |
| 3008 | FUNCTIONAL | 2 | FieldMap.cs:2364, FieldMap.cs:2532 |
| 3009 | SOFTLOCK | 6 | Dialog.cs:820, EBin.cs:1321, FieldMap.cs:106, FieldMap.cs:2364, FieldMap.cs:2532, VoicePlayer.cs:251 |
| 3010 | SOFTLOCK | 6 | Dialog.cs:826, FieldMap.cs:106, FieldMap.cs:2364, FieldMap.cs:2532, FieldMapActorController.cs:413, VoicePlayer.cs:251 |
| 3011 | FUNCTIONAL | 5 | Dialog.cs:832, EBin.cs:1310, FieldMap.cs:106, FieldMap.cs:2364, FieldMap.cs:2532 |
| 3012 | FUNCTIONAL | 2 | FieldMap.cs:2364, FieldMap.cs:2532 |
| 3100 | COSMETIC | 1 | EMinigame.cs:398 |

## FUNCTIONAL — wrong but playable (movement/camera/logic)

| field id(s) | site | behavior |
|---|---|---|
| 2954 | `Actor.cs:24` | Chocobo's Paradise: sets the Gold Chocobo actor's turn rate (omega) to 96 instead of the default 16. |
| 1656 | `Actor.cs:26` | Iifa Tree/Eidolon Mound: sets Vivi actor's turn rate (omega) to 48 instead of default 16. |
| 1505,2605,2653,2259,153,1806,1214,1823,1752,2922,2923,2924,2925,2926,1751,1753,2252,2714 | `BGSCENE_DEF.cs:925` | Selects the combined-mesh background build path (CreateSceneCombined) instead of per-sprite CreateScene, for fields with depth-sor |
| 552 | `BGSCENE_DEF.cs:1721` | Overrides per-overlay canCombine handling for Lindblum Main Street overlay 17 |
| 552 | `BGSCENE_DEF.cs:1733` | Marks sprites 202,203,214,215 of overlay 17 as separate (non-combined) sprites on Lindblum Main Street |
| 2714 | `BGSCENE_DEF.cs:1837` | Forces depth=400 on 5 specific maze sprites so they render in front correctly |
| —(table) | `Dialog.cs:489` | Marks textId 154/155 (or 149/150 IT, 134/135 default) as an 'overlay' dialog (moved off-screen, purple-digit number-entry UI) for  |
| —(table) | `Dialog.cs:505` | Marks textId 204-206 (US/UK) or 205-207 as overlay dialogs for Treno Auction House bidding number-entry. |
| —(table) | `Dialog.cs:518` | Marks textId 106/107 as overlay dialogs for Daguerreo ore->aquamarine transforming count UI. |
| —(table) | `Dialog.cs:522` | Marks per-language textId pairs as overlay dialogs for Madain Sari 'cook for how many people' count UI. |
| —(table) | `Dialog.cs:544` | Marks textId 251/252 (JP) or 252/253 as overlay dialogs for Chocobo Places Gysahl-Greens buy count UI. |
| 2951,2952 | `Dialog.cs:733` | In OnKeyConfirm, swallows the confirm keypress for specific Press/Release mes-id pairs (Chocobo Hot&Cold dig prompts) at Chocobo's |
| 2950 | `Dialog.cs:741` | Same confirm-keypress suppression for the Press/Release mes-id pairs (245/225, 246/226) at Chocobo's Forest. |
| 3011 | `Dialog.cs:832` | In AutoHide, on Epilogue Stage 3011 calls ForceControlByEvent(true) and adds a per-language timing offset to the auto-hide wait (d |
| 2801 | `EBin.cs:317` | Fast-trophy-mode shortcut: force-sets map var 46 = 8 at a specific script point in Daguerreo/Right Hall to skip ahead the Gilgames |
| 1900 | `EBin.cs:319` | Fast-trophy-mode shortcut: force-sets map var 26 = 8 at a specific script point in Treno/Pub Main to skip ahead. |
| 705 | `EBin.cs:323` | In the expression evaluator, when this exact NPC/IP is hit on Gizamaluke Bell Room, advances s1.ip by 7 and returns 0 early -- ski |
| 908,1908 | `EBin.cs:714` | Widescreen fix: in a less-than comparison, rewrites the literal 80 to 300 so the Treno gate trigger position is correct in widescr |
| 657 | `EBin.cs:730` | In a greater-than comparison, flips strict '<' to '<=' (t3 <= _v0) at many script points for Zidane in the Qu's Marsh Pond -- a co |
| 903,1903,112 | `EMinigame.cs:345` | Tetra Master: computes the Card Stadium tournament opponent id (fldMapNo*1000+flag+100), or routes the Alexandria/Pub card game to |
| 2955 | `EMinigame.cs:365` | Chocobo's Paradise: registers the Fat Chocobo Tetra Master opponent id. |
| 1421 | `EMinigame.cs:388` | Fossil Roo/Mining Site: a dig-minigame cheat that force-sets two map vars (digging assist for the Madain's Ring). |
| 1850 | `EMinigame.cs:697` | Alexandria/Main Street: overrides the Hippaul-race Vivi-speed var with Configuration.Hacks.HippaulRacingViviSpeed and clamps a min |
| 70 | `EventEngine.cs:638` | Suppresses the entry autosave on the Opening-FMV field (field 70). |
| 2200 | `EventEngine.cs:639` | Suppresses entry autosave on Palace/Dungeon first-time entrance. |
| 150 | `EventEngine.cs:640` | Suppresses entry autosave on A. Castle/Guardhouse (Zidane & Blank after sword fight). |
| 1251 | `EventEngine.cs:641` | Suppresses entry autosave on Pinnacle Rocks/Hole first-time entrance. |
| 1602 | `EventEngine.cs:642` | Suppresses entry autosave on Mdn. Sari/Path (night-time Zidane/Vivi/Eiko cutscene). |
| 1757 | `EventEngine.cs:643` | Suppresses entry autosave on Iifa Tree/Outer Seal (return after Soulcage). |
| 2752 | `EventEngine.cs:644` | Suppresses entry autosave on Invincible/Bridge (Assault of the Silver Dragons). |
| 3001 | `EventEngine.cs:645` | Suppresses entry autosave on Ending/AC. |
| 2161 | `EventEngine.cs:646` | Suppresses entry autosave on L. Castle/Guest Room (Zidane awakes after Mount Gulug). |
| 2919 | `EventEngine.GetSysvar.cs:71` | GetSysvar code 20 (the in-script countdown timer read) returns 0 on Crystal World 2919 so the Excalibur II time limit never expire |
| 2950,2951,2952,2953,2954,2955 | `EventEngine.ProcessAnime.cs:48` | On the Chocobo Hot & Cold maps, when a child actor's parent (Choco) changes idle/walk/run state, force-SetAnim the child to the ma |
| 2950,2951,2952,2954,2955 | `EventEngine.ProcessAnime.cs:73` | For one specific parented actor per Chocobo H&C map (the named sid), drive its animFrame independently (increment + modulo frameN) |
| 303,304 | `EventEngine.ProcessEvents.cs:18` | When the No-Encounter setting is on, clears GlobBool 205/206/207 on Ice Cavern/Icicle Field & Ice Path to prevent the Wyerd forced |
| 301 | `EventEngine.ProcessEvents.cs:25` | No-Encounter setting: clears GlobBool 238/239 on Ice Cavern/Ice Path. |
| 302 | `EventEngine.ProcessEvents.cs:31` | No-Encounter setting: clears GlobBool 206/207 on Ice Cavern/Ice Path. |
| 2921 | `EventEngine.ProcessEvents.cs:37` | No-Encounter setting: sets GlobUInt16_40 = 10 on Memoria/To the Origin (to skip a forced-encounter sequence). |
| 257 | `EventEngine.ProcessEvents.cs:109` | On Evil Forest/Nest, gates event-code processing on the dialog being fully visible (canProcessCode = !DialogManager.Activate || Co |
| 52 | `EventEngine.ProcessEvents.cs:518` | Keeps two specific actors (sid 6 & 13) visible on field 52 while a flag (var 6357) is set, instead of disabling their renderers. |
| 2855 | `EventEngine.ProcessTurn.cs:18` | During a specific scripted turn (turnAdd==32766) for model 273 at scenario 9370, wrap the candidate turn angle 'a' into [-180,180] |
| 2855 | `EventEngine.ProcessTurn.cs:35` | Mirror of line 18 for the opposite turn direction (turnAdd==32767): wrap angle 'a' into [-180,180] before the completion compariso |
| 1900 | `EventEngine.turnOffTriManually.cs:8` | Deactivates walkmesh triangle 56 (BGI_triSetActive(56,0)) for actor sid 4 on this field -- script-driven removal of a walkable tri |
| 900 | `EventEngine.turnOffTriManually.cs:14` | On field 900: sid 8 deactivates tri 56 once SC_COUNTER>=4450; sid 17 deactivates tri 62 unless SC>=4450 or map-index is 1/5 -- sce |
| 1455 | `EventEngine.turnOffTriManually.cs:32` | Deactivates walkmesh triangle 16 (BGI_triSetActive(16,0)) for actor sid 5 on this field. |
| 2803 | `EventEngine.turnOffTriManually.cs:40` | For sid 20 on field 2803, sets tris 105 and 106 active or inactive based on whether script var 761060 == 1 -- toggles a pair of wa |
| —(table) | `EventEngineUtils.cs:1687` | id-keyed TABLE mapping a field's quad/trigger (composite key field*1000+objN) to a partner NPC uid; consumed by EventCollision.IsQ |
| —(table) | `EventEngineUtils.cs:1722` | id-keyed TABLE replacing a field quad's collision shape with a circular (or augmented) region; IsInQuadHotFix uses it so the trigg |
| 1060 | `EventEngineUtils.cs:1855` | Forces the US-language .eb event binary to load for non-US/JP languages on Cleyra/Cathedral so the dancing scene uses the US/JP sc |
| 103,107 | `EventCollision.cs:340` | On fields 103 and 107, NPCs with sid 3 or 4 are exempted from being push-collided (CheckNPCPush returns false, so the player won't |
| 1856 | `EventCollision.cs:342` | On field 1856, NPCs with sid 5 or 6 are exempted from push collision (not pushable by the player). |
| 2108 | `EventCollision.cs:369` | On field 2108, a quad with sid 6 is only pushable when it is also talkable (push gated on facing/talkable test instead of always-t |
| 2802 | `EventCollision.cs:371` | On field 2802, a quad with sid 24 is exempted from push collision. |
| 2914 | `EventCollision.cs:373` | On field 2914, a quad with sid 13 is exempted from push collision. |
| 2108 | `EventCollision.cs:401` | On field 2108, a quad with sid 7 is made non-talkable (CheckQuadTalk returns false). |
| 2504 | `EventCollision.cs:403` | On field 2504, a quad with sid 9 is made non-talkable. |
| —(table) | `EventCollision.cs:449` | Looks up a talkable-quad partner object in QuadTalkableData using a key built from (fldMapNo, quad.uid); if absent, IsQuadTalkable |
| 2108 | `EventCollision.cs:458` | On field 2108, a registered talkable quad is only talkable when the player faces within a specific direction window (dir 91-159),  |
| 2109 | `EventCollision.cs:463` | On field 2109, talkable-quad facing window is dir 160-222. |
| 2103 | `EventCollision.cs:468` | On field 2103, talkable-quad facing window is dir 160-222. |
| 2802 | `EventCollision.cs:473` | On field 2802 a talkable quad requires both a facing window (dir 17-111) and obj-18's world Y-position > 950; all other (non-2802) |
| 656,657,658,659 | `EventCollision.cs:500` | On the Qu's-Marsh frog fields 656-659, frog NPCs (models 174/175/176/GoldenFrog) are only talkable when the eBin var 157157 > 0; o |
| 350 | `EventCollision.cs:532` | On field 350, NPC sid 34 is made non-talkable during a specific story beat (scenario counter 2600, map index 2). |
| 507 | `EventCollision.cs:534` | On field 507, NPC sid 15 is made non-talkable during scenario beat 2915 / map index 3 while object 10 exists. |
| 566 | `EventCollision.cs:536` | On field 566, NPC sid 7 is made non-talkable during scenario beat 3140 / map index 40. |
| 1603 | `EventCollision.cs:540` | On field 1603, the NPC with uid 133 is made non-talkable at scenario counter 6810. |
| 1608 | `EventCollision.cs:542` | On field 1608, NPC sid 15 talkability is gated on scenario counter >= 6850 (returns that boolean directly). |
| 1856 | `EventCollision.cs:544` | On field 1856, NPC uid 4 is suppressed from talk while the '!' bubble icon is showing. |
| 2950 | `EventCollision.cs:546` | On field 2950 (Chocobo's Forest), NPC sid 9 (Mene/chocobo-game NPC) talkability returns based on map index != 2 and eBin var 8401  |
| —(table) | `EventHUD.cs:41` | In zone 7 (Cleyra Trunk), mesId 113 opens the JumpingRope minigame HUD ('mash X'). |
| —(table) | `EventHUD.cs:47` | In zone 22, a per-language mesId opens the Telescope minigame HUD. |
| —(table) | `EventHUD.cs:70` | In zone 23, a per-language mesId opens the Auction minigame HUD (Potion bid). |
| —(table) | `EventHUD.cs:88` | In zone 33, mesId 233/246 open/close the JumpingRope minigame HUD. |
| —(table) | `EventHUD.cs:101` | In zones 70/741 (Treno 1 & 2), a per-language mesId opens the Auction minigame HUD (bidding dialog). |
| —(table) | `EventHUD.cs:116` | In zone 71, a per-language mesId opens the MogTutorial HUD. |
| —(table) | `EventHUD.cs:131` | In zone 90, mesId 147/148 open/close the RacingHippaul minigame HUD. |
| —(table) | `EventHUD.cs:140` | In zone 166, mesId 105 opens the Auction minigame HUD ('Place how many Ore?'). |
| —(table) | `EventHUD.cs:146` | In zone 358, a per-language mesId opens the Auction minigame HUD. |
| —(table) | `EventHUD.cs:170` | In zone 740, mesId 249/250 open/close the GetTheKey minigame HUD. |
| —(table) | `EventHUD.cs:183` | In zone 945, mesId 34/35 open the ChocoHotInstruction HUD; otherwise a per-language mesId opens the Auction HUD. |
| —(table) | `EventHUD.cs:201` | In zone 946, per-language mesIds open/close the JumpingRope minigame HUD. |
| 64 | `EventHUD.cs:346` | On field 64 (Alexandria Castle public seats), opens/closes the Chanbara (Blank vs Marcus sword-fight) minigame HUD based on dialog |
| 1208 | `EventHUD.cs:359` | On field 1208 (A. Castle dungeon), opens/closes the Swing-a-Cage minigame HUD when dialog progression == 13. |
| 1704 | `EventHUD.cs:369` | On field 1704 (Madain Sari Eidolon Wall), on mobile toggles player-control enable based on dialog visibility when user-control is  |
| 2204 | `EventHUD.cs:374` | On field 2204 (Palace/Odyssey), closes the Get-the-Key minigame HUD when the timer hits 0. |
| 2921 | `EventHUD.cs:379` | On field 2921, on mobile toggles player-control enable based on dialog visibility when user-control is off. |
| 2950,2951,2952 | `EventHUD.cs:384` | On the Chocobo Forest/Lagoon/Air-Garden fields, opens the ChocoHot minigame HUD when the timer is running and closes ChocoHotInstr |
| 2711 | `EventHUD.cs:396` | On field 2711, opens/closes the Pandemonium-Elevator minigame HUD based on whether dialog window ID7 shows the elevator-control te |
| 1420 | `EventInput.cs:95` | On field 1420 (Fossil Roo Cavern) while climbing ivy with the BubbleUI active, processes input with button-trigger disabled (false |
| 606 | `EventInput.cs:142` | On field 606, only processes movement input while the Telescope HUD is active (the whole else-branch is field-606 specific for tel |
| 2204 | `EventInput.cs:147` | On field 2204 while the timer is enabled, processes input with button-trigger disabled (false,false) - timed Get-the-Key input mod |
| 1607 | `EventInput.cs:151` | On field 1607, forces ProcessInput(false,false) - non-trigger (continuous) input mode for the kitchen scene. |
| 1420 | `EventInput.cs:155` | On field 1420, forces ProcessInput(false,true). |
| 1422 | `EventInput.cs:159` | On field 1422, forces ProcessInput(false,true). |
| 909,1909 | `EventInput.cs:190` | On mobile, fast-forward processing is normally skipped, but is force-enabled on fields 909 (Treno Auction Site) and 1909 (Treno Au |
| 1420 | `EventInput.cs:367` | During fast-forward, on the same-frame repeat the operation mask is cleared for all fields EXCEPT field 1420 in event-mode 1, wher |
| 1413 | `FieldMapActor.cs:135` | HonoLateUpdate: when out of depth range, sets actor.frontCamera = (sid==12) for Zidane (Fossil Roo/Nest) |
| 1414 | `FieldMapActor.cs:141` | HonoLateUpdate: when out of depth range, sets actor.frontCamera = (sid==16) for Zidane (Fossil Roo/Nest) |
| 2752,1707 | `FieldMapActor.cs:147` | HonoLateUpdate: out-of-depth-range fallback sets frontCamera=false UNLESS the field is 2752 or 1707 (Invincible/Bridge, Mdn.Sari/S |
| 1412,1410 | `FieldMapActor.cs:243` | GeoAttach: special-cases PC curPos when attaching to a parent node within the Fossil Roo zone (1400-1425) |
| 2954 | `FieldMapActor.cs:261` | GeoAttach: overrides geo attach offset to (30,150,0) (Chocobo's Air Garden, map index 8) |
| 3002 | `FieldMapActor.cs:297` | GeoDetach: sets HonoBehaviorSystem.ExtraLoopCount = 1 for a specific actor/anim (ending field) |
| 1751 | `FieldMapActorController.cs:327` | UpdateMovement: forces CopyLastPos for the PC even without user control (Iifa Tree/Inner Roots entrance after elevator) |
| 404 | `FieldMapActorController.cs:328` | UpdateMovement: forces CopyLastPos for the PC even without user control (Dali underground Entrance) |
| 205 | `FieldMapActorController.cs:329` | UpdateMovement: forces CopyLastPos for Steiner during scripted move (Prima Vista/Hallway front of Steiner's cell) |
| 2150 | `FieldMapActorController.cs:330` | UpdateMovement: forces CopyLastPos for Zidane during scripted move (L.Castle/Royal Chamber) |
| 900 | `FieldMapActorController.cs:331` | UpdateMovement: forces CopyLastPos for Dagger during scripted move (Treno/Pub) |
| 916 | `FieldMapActorController.cs:337` | UpdateMovement: clamps Dagger's X to 130 in a bounded Z band (Treno/Dock) |
| 1005 | `FieldMapActorController.cs:339` | UpdateMovement: two hardcoded XZ clamps for Zidane (Cleyra/Tree Trunk sand room) |
| 2050 | `FieldMapActorController.cs:350` | UpdateMovement (NPC branch): forces CopyLastPos for Mistodon NPC (Alexandria/Main Street) |
| 350 | `FieldMapActorController.cs:351` | UpdateMovement (NPC branch): forces CopyLastPos for Dali_GirlA NPC (Dali/Village Road) |
| 1315 | `FieldMapActorController.cs:352` | UpdateMovement (NPC branch): forces CopyLastPos for Lindblum_Soldier NPC (Lindblum/Town Walls) |
| 3010 | `FieldMapActorController.cs:413` | PlayAnimationViaEventScript: early-returns (skips re-playing the anim) for the Sword actor (Ending/TH) |
| 2950,2951,2952,2954,2955 | `FieldMapActorController.cs:448` | LateUpdate: calls PretendChocoboOffset to ride the Chocobo (positions rider over chocobo bone) |
| 2207 | `FieldMapActorController.cs:799` | CheckCollFallback: early-returns to skip the soft-lock collision fallback (Palace/Hall, Zidane summoned past stairs) |
| 2952 | `FieldMapActorController.cs:1047` | CalculateOriginalVertices: adds per-floor (curPos-orgPos) offset to walkmesh vertices (Chocobo's Air Garden) |
| 1752 | `FieldMapActorController.cs:1235` | ServiceForces: overrides wall-rejection factor (0.4/0.6 instead of 1.05) on specific tris (Iifa Tree/Inner Roots 2nd area) |
| 406 | `FieldMapActorController.cs:1240` | ServiceForces: overrides wall-rejection factor to 0.4 on specific tris (Dali/Underground room under the well) |
| 2712,2504,1056,2955,1807,1106 | `FieldMapActorController.cs:1348` | GetActiveTriIdxAtPos (foundTris.Count==1 case): applies a 432f height-difference gate before accepting the triangle, else result=- |
| 2356 | `FieldMap.cs:112` | Disables walkmesh triangles 78,79,80 (the wall the Red Dragon bursts through) |
| 2161 | `FieldMap.cs:119` | Disables walkmesh triangle 69 |
| 1508 | `FieldMap.cs:580` | RestoreAttachModel — re-attaches a model part to an actor on this inn field |
| 931 | `FieldMap.cs:649` | For 931 the entire widescreen X-clamp/scroll-margin logic is SKIPPED (boat scene scrolls freely) |
| 1205,1652,2552,154,1215,1807,1055 | `FieldMap.cs:666` | Custom X-threshold camera clamp (with per-field threshmargin tweaks for 1652 cam0 and 1055) |
| 2351 | `FieldMap.cs:1163` | Forces moved overlay depth to 3000 (the official mine-bucket depth fix) |
| —(table) | `FieldMap.cs:1449` | Overrides a specific overlay's Z-depth (curZ) per (field,cam,overlay) to fix lights/props sorting in front of/behind characters |
| 813 | `FieldMap.cs:1503` | Reassigns the camera-follow controller from Dagger (uid 8) to Mary (uid 2) for this scroll |
| 1656 | `FieldMap.cs:1972` | Reads event var 7385; when 1, nulls playerController and applies a fixed extraOffset (-16,-8) for camera framing |
| 51,575,767,931,1655,1754,2200,3000,3001,3002,3003,3004,3005,3006,3007,3008,3009,3010,3011,3012 | `FieldMap.cs:2532` | Excludes the field from smooth-camera interpolation (SmoothCamActive=false) — these fields glitch with smoothing |
| 100 | `fldfmv.cs:112` | In FMV service state 5, allows the field FMV to begin playing even when the PLAY attr bit was not set, specifically for field 100. |
| 1663 | `HonoluluFieldMain.cs:301` | Iifa Tree/Tree Trunk: force-closes all dialog boxes before the Mistodons battle swirl (a scripted-cutscene-to-battle hotfix). |
| 2752 | `MBG.cs:339` | MBG.UpdateCamera: applies the movie-background per-frame camera offset/RT to the field camera for ALL MBG fields EXCEPT 2752 (whic |
| 2933 | `MBG.cs:356` | MBG.UpdateCamera: advances the MBG playback frame counter (num++) for all MBG fields except 2933 (Crystal World mbg 1), which adva |
| 2933 | `MBG.cs:409` | MBG.UpdateCamera: Crystal World (2933) only -- repositions/clears flags on the actor (uid 4) along the scripted MBG path at specif |
| 2933 | `MBG.cs:547` | MBG.HonoUpdate calls MBGUpdate every HonoUpdate EXCEPT for field 2933 (which instead drives MBGUpdate from LateUpdate at line 553) |
| 2933 | `MBG.cs:553` | Crystal World (2933) only: drives MBGUpdate from Unity LateUpdate instead of HonoUpdate. |
| 2933 | `MovieMaterialProcessor.cs:11` | For field 2933, drives the streaming MovieMaterial.Update()/NativeUpdate() from Update() instead of LateUpdate(). |
| 155,1216,1808 | `SPSEffect.cs:244` | Alexandria Castle/Library (3 versions): applies a z-depth offset of 700 to SPS_0008 (fixes draw-order/occlusion). |
| 2929 | `SPSEffect.cs:254` | last/cw mbg a: enables 'useScreenPositionHack' for the teleportation SPS shown after the Necron battle (special screen-space proje |
| 2207 | `UIKeyTrigger.cs:484` | Palace/Hall: blocks opening the party-switch menu (plays the deny SFX and returns) when Zidane returns with the Gulug Stone -- pre |
| 3009,3010 | `VoicePlayer.cs:251` | In AfterSoundFinished_Dismiss: for a timed dialog (EndMode>0) it returns early to let the timer close it, EXCEPT on Epilogue Stage |

## COSMETIC — visual/audio only (lowest priority; narrow-map letterbox lives here)

| field id(s) | site | behavior |
|---|---|---|
| 60 | `SceneDirector.cs:593` | In Prima Vista/Interior, defers the Add-mode fade by 3 frames (StartCoroutine SetGlobalFade) when fast-forwarding, so the fade ren |
| 1661 | `SceneDirector.cs:598` | In Brahne's Fleet/Event at scenario 6930, defers the Add-mode fade by 3 frames so the global fade renders correctly. |
| 503 | `AllSoundDispatchPlayer.cs:135` | On Cargo Ship/Bridge at a specific scenario beat, forces a just-loaded music track (song 35) to volume 0 (mutes it). |
| —(table) | `Dialog.cs:1578` | In CanAutoResize, disables automatic dialog box resizing (uses STRT-tag size instead) for Fossil Roo lever/path-display windows. |
| 1608 | `Dialog.cs:1609` | In ForceUpperTail, for Madain Sari Secret Room at scenario 6840/6850 forces the dialog tail to the upper position based on camera  |
| 2951 | `Dialog.cs:1633` | In OverwriteDialogParameter (mobile only), for the Moogle (uid 13) choice dialog at Chocobo's Lagoon, detaches the dialog from the |
| 3011 | `EBin.cs:1310` | In the Wait command, for non-US/JP languages on the Ending field, remaps wait durations (82->102, 50->90) to retime the ending cut |
| 3009 | `EBin.cs:1321` | In the Wait command, for non-US/JP languages remaps wait 15->20 for uid 17 on the Ending field to retime a localized line. |
| 64 | `EMinigame.cs:12` | Alexandria Castle/Public Seats: Chanbara (Blank swordplay) minigame bonus-points + Steam SwordplayAssistance hacks (score +30%, en |
| 1704 | `EMinigame.cs:59` | Madain Sari/Eidolon Wall: reports the EidolonMural achievement when the name-reveal message is read. |
| 352 | `EMinigame.cs:86` | Dali/Inn: reports the ExcellentLuck (best fortune-telling) achievement. |
| 103,2456 | `EMinigame.cs:112` | Jump-rope: picks which gEventGlobal counter holds the jump count (field 103 early-game vs 2456 late-game) to drive the Rope100/Rop |
| 103,2456 | `EMinigame.cs:136` | Jump-rope: matches the per-language congratulation message id used to confirm a successful rope run for the achievement. |
| 911,1911 | `EMinigame.cs:177` | Treno/Queen's House: reports the QueenReward10 (Stellazzio) achievement, counting collected coins. |
| 1900,2801 | `EMinigame.cs:204` | Treno/Pub or Daguerreo/Right Hall: reports the TreasureHuntS achievement on a specific message. |
| 1858 | `EMinigame.cs:211` | Alexandria/Weapon Shop: reports the Shuffle9 (shuffle game) achievement on the congratulation message. |
| 457,455 | `EMinigame.cs:233` | Mountain/Shack or Mountain/Base: reports the ShipMaquette (theater-ship model) achievement. |
| 1109 | `EMinigame.cs:246` | Cleyra/Cathedral: reports CleyraVictimAll achievement if all three victims were helped. |
| 2950,2951,2952 | `EMinigame.cs:264` | Chocobo's Forest/Lagoon/Air Garden: reports the ChocoboLv99 (beak level) achievement on the per-language beak-update message. |
| 909,1909 | `EMinigame.cs:293` | Treno/Auction Site: reports the Auction10 achievement (10th auction win). |
| 600 | `EMinigame.cs:300` | Lindblum Castle/Royal Chamber: reports the ViviWinHunt achievement (Vivi won the Festival of the Hunt). |
| 558,1306,2106,908,1908 | `EMinigame.cs:329` | Tetra Master: groups certain card opponents to a canonical opponent id (and applies the Thief coin-condition card-upgrade) so the  |
| 908,1908 | `EMinigame.cs:354` | Treno/Gate: identifies the Thief card NPC (id 908009/1908006) and applies the coin-condition grouping. |
| 1421 | `EMinigame.cs:381` | Fossil Roo/Mining Site: reports the MadainRing dig achievement. |
| 3100 | `EMinigame.cs:398` | Mognet Central: reports the MognetCentral achievement. |
| 1850 | `EMinigame.cs:404` | Alexandria/Main Street (Hippaul race): in fast-trophy mode, bumps the race-win count var to 80 on a Vivi-win message. |
| 1850 | `EMinigame.cs:413` | Alexandria/Main Street: reports the AthleteQueen (Hippaul race) achievement on reward. |
| 2457 | `EMinigame.cs:419` | Alexandria/Mini-Theater: reports the SuperSlickOil achievement. |
| 1421 | `EMinigame.cs:500` | Fossil Roo/Mining Site: reports the Kuppo (dig up Mog) achievement. |
| 206 | `EMinigame.cs:534` | MappingATEID: maps the Prima Vista/Crash Site ATE choice to ATE-seen index 0 (for the ATE80 'seen 80 ATEs' achievement). |
| 253,204 | `EMinigame.cs:543` | MappingATEID: maps these fields' compulsory ATE to seen-index 5. |
| 262 | `EMinigame.cs:545` | MappingATEID: maps field 262's compulsory ATE to seen-index 6. |
| 306 | `EMinigame.cs:550` | MappingATEID: maps field 306's compulsory ATE to seen-index 7. |
| 554,552,565 | `EMinigame.cs:562` | MappingATEID: maps fields 554/552/565 compulsory ATEs to seen-indices 14/16/18 respectively. |
| 1307 | `EMinigame.cs:590` | MappingATEID: maps field 1307 ATE to seen-index 33. |
| 1353 | `EMinigame.cs:595` | MappingATEID: maps field 1353 compulsory ATE to seen-index 34. |
| 956 | `EMinigame.cs:625` | MappingATEID: maps field 956 compulsory ATE to seen-index 57. |
| 2169,2113,2173 | `EMinigame.cs:636` | MappingATEID: maps fields 2169/2113/2173 compulsory ATEs to seen-indices 70-77/73/75 (2169 further split by scenario counter). |
| 1850 | `ETb.cs:114` | Alexandria/Main Street: forces the on-screen button glyph to show for the 'press alternately' Hippaul-race prompt (Android TV only |
| 1657 | `ETb.cs:123` | Iifa Tree/Tree Roots: sets dialog.FocusToActor false for specific lines (per language) so the camera/window doesn't snap to the sp |
| 1652 | `ETb.cs:290` | Iifa Tree/Roots: suppresses (skips) a specific message ('How far is it gonna go...?') per language. |
| 1659 | `ETb.cs:301` | Iifa Tree/Seashore: skips re-showing a Queen Brahne line that's already on screen. |
| 2209 | `ETb.cs:309` | Palace/Sanctum: skips Zidane's 'No!!!' line (mes 393) when chasing Kuja. |
| 1850 | `ETb.cs:401` | Alexandria/Main Street: clears ForceShowButton after the Hippaul-race prompt closes (Android TV only). |
| 206 | `ETb.cs:424` | ProcessATEDialog/related: special-cases the Prima Vista/Crash Site ATE at scenario 1900 (ATE-seen ATE80 achievement path). |
| 2913 | `EventEngine.ProcessEvents.cs:576` | Scales the shadow of actor uid 6 by the actor's local Z scale on field 2913 (Crystal World-area giant actor); all other cases use  |
| 2108 | `EventCollision.cs:294` | On field 2108, when a pushable quad is engaged and the quad is talkable, polls the Exclamation '!' interaction icon (BubbleUI). |
| —(table) | `EventHUD.cs:32` | In zone 2 (Prima Vista), when mesId 35 closes, opens the basic control tutorial. |
| 2510 | `FieldMapActor.cs:164` | HonoLateUpdate: sets renderer _CharZ = 20 for the Water_Mirror actor (I.Castle/Mural Room) |
| 2363 | `FieldMapActor.cs:169` | HonoLateUpdate: sets renderer _CharZ = 20 for Thorn (Gulug/Path) |
| 661 | `FieldMapActor.cs:181` | HonoLateUpdate: applies a hardcoded shadow offset (-39,-14,80) for Quale (Marsh/Master's House) |
| 1659 | `FieldMapActor.cs:183` | HonoLateUpdate: shadow offset (0,-66,0) for Queen_Brahne instance 1 (Iifa Tree/Seashore) |
| 1659 | `FieldMapActor.cs:185` | HonoLateUpdate: shadow offset (0,-21,0) for Queen_Brahne instance 2 (Iifa Tree/Seashore) |
| 2363 | `FieldMapActor.cs:187` | HonoLateUpdate: shadow offset (0,-15,0) for Zorn/Thorn actors (Gulug/Path) |
| 2107,2102 | `FieldMapActor.cs:190` | HonoLateUpdate: overrides shadow position to the transform XZ with y=0 for the Pickaxe (Lindblum/Square, Lindblum/Main Street) |
| 1204 | `FieldMapActorController.cs:213` | Creates 5 debug sphere markers (marker1-5) at hardcoded coords for Zidane on A.Castle/Underground platform |
| 576 | `FieldMapActorController.cs:441` | LateUpdate: applies a hardcoded neck rotation to Cid Human (Royal Action Figures) (Lindblum/Festival) |
| 116 | `FieldMapActorController.cs:472` | CheckOffsetPosModel: nudges the Ladder model up 40 / forward 25 (Alexandria/Rooftop) |
| 1606 | `FieldMapActorController.cs:486` | CheckOffsetPosModel: nudges Stew Pot/Cooked Fish/Stew Plate props back 20 (Mdn.Sari/Resting Room) |
| 1610 | `FieldMapActorController.cs:528` | UpdateNeck: special neck rotation for Zidane Listen_1/Listen_2 (Mdn.Sari/Cove) |
| 1601 | `FieldMapActorController.cs:540` | UpdateNeck: special neck rotation (23deg) for Eiko Look_Up_2 first-time-there (Mdn.Sari/Open Area) |
| 3009,3010,3011 | `FieldMap.cs:106` | Enables frame-skip / fixed target frame time for the ending sequence fields |
| 1508,1706 | `FieldMap.cs:582` | RestoreShadowOff — suppresses an actor's shadow on restore |
| 1706 | `FieldMap.cs:608` | Per-uid character scaling (uid 4 JP=40, uid 3/5=80) — shrinks specific NPCs (Moogles/Eiko cooking scene) |
| 2924 | `FieldMap.cs:615` | Sets Zidane's render queue to 2000 (custom draw order) instead of default -1 |
| 609,2159 | `FieldMap.cs:657` | Applies a non-linear (quadratic) vertical camera curve during a specific Lindblum-tower beat |
| 507 | `FieldMap.cs:662` | Nudges camera X by +1 px |
| 103,1853,2053,2606 | `FieldMap.cs:686` | Adds +16 to the left camera threshold margin |
| 2903 | `FieldMap.cs:688` | Subtracts 32 from the right camera threshold |
| 2923 | `FieldMap.cs:690` | Adds +20 to the left camera threshold margin |
| 312,456,505,1153,2716,2903 | `FieldMap.cs:703` | Per-field hardcoded camera X (or Y clamp) for stretched-to-widescreen scrolling maps (Ice cavern out, Dali Summit, Cargo ship, Ros |
| 2755 | `FieldMap.cs:1150` | Adjusts a moving tile's dx to 0.75 and scales overlay 1.1x (widescreen fix for a moving prop) |
| 2903 | `FieldMap.cs:1365` | Shifts overlay 1's localPosition X by -1px |
| 1651,1758,312,805,808,908,1908,1108,1657,1660,2251,2252,2600,2602,2604,2605,2606,2607,2651,2660,2851,2916,2922,2923 | `FieldMap.cs:1655` | Per-field hardcoded parallax/loop overlay X/Y positions and scales to make scrolling/parallax backgrounds line up at widescreen |
| 3000,3001,3002,3003,3004,3005,3006,3007,3008,3009,3010,3011,3012 | `FieldMap.cs:2364` | Forces PSX field/screen width to 320 and disables widescreen for the ending fields |
| —(table) | `NarrowMapList.cs:45` | Forces a normally-wide field to render NARROW (320/432/478) during specific scenario beats (index/counter), or whitelists a few fi |
| —(table) | `NarrowMapList.cs:81` | Per-(field,cam) forces a narrower PSX camera width (caps the widescreen viewport ratio for cams that overshoot) |
| —(table) | `NarrowMapList.cs:117` | Returns the field's authored PSX render width (letterbox/narrow-cam masking width); falls back to 500 (=widescreen, no narrowing)  |
| 1051,1057,1058,1060,1653 | `NarrowMapList.cs:932` | Adds left/right camera crop margin for scrollable fields that pan too far |
| 2653,2654 | `fldchar.cs:73` | When creating the mirror-character (case 11), forces the mirror geo's renderQueue to 2000 so the reflection sorts correctly in the |
| 2215 | `CommonSPSSystem.cs:116` | Desert Palace: lowers a misaligned flame SPS (pos.y 1150 -> 1025). |
| 2301,2302 | `CommonSPSSystem.cs:118` | Esto Gaza: repositions a flame SPS_0000 to (-1330,710,674). |
| 2301,2302 | `CommonSPSSystem.cs:120` | Esto Gaza: lowers flame SPS_0001 (pos.y 400 -> 350). |
| 2304 | `CommonSPSSystem.cs:122` | Esto Gaza: repositions flame SPS_0000 to (-1030,1400,1716). |
| 2304 | `CommonSPSSystem.cs:124` | Esto Gaza: repositions flame SPS_0001 to (790,1400,2016). |
| 303 | `CommonSPSSystem.cs:126` | Ice Cavern: hard-sets smoke SPS_0002 position to (4330,-1227,-700). |
| 205 | `CommonSPSSystem.cs:128` | Prima Vista candle: shifts pos.x -110 -> -122. |
| 207 | `CommonSPSSystem.cs:130` | Prima Vista candle: repositions SPS_0000 to (845,485,-82). |
| 262 | `CommonSPSSystem.cs:132` | Field 262: shifts SPS_0000 pos.x 355 -> 385. |
| 162 | `CommonSPSSystem.cs:134` | Field 162: repositions SPS_0002 to (-350,640,-314). |
| 162 | `CommonSPSSystem.cs:136` | Field 162: repositions SPS_0003 to (-470,650,-314). |
| 162 | `CommonSPSSystem.cs:138` | Field 162: repositions SPS_0004 to (-580,640,-314). |
| 163 | `CommonSPSSystem.cs:140` | Field 163: repositions SPS_0002 to (735,475,4000). |
| 163 | `CommonSPSSystem.cs:142` | Field 163: repositions SPS_0001 to (1060,505,4000). |
| 2553 | `CommonSPSSystem.cs:169` | Wind Shrine/Interior: nulls the loaded SPS bin for 4 specific effect ids (suppresses those effects). |
| 911,1911 | `CommonSPSSystem.cs:177` | Treno/Queen's House: on SPS delete, resets pos/scale/rot to defaults for effects 33/34 before unload. |
| 1206,1223,2928 | `CommonSPSSystem.cs:198` | Hill of Despair / A.Castle Queen's Chamber: enables the mesh renderer only if spsBin != null (suppresses showing an unloaded SPS). |
| 911,1911 | `CommonSPSSystem.cs:213` | Treno/Queen's House: on OPERATION_POS, only applies the new SPS position if spsBin != null. |
| 50,51 | `CommonSPSSystem.cs:230` | Enlarges specific candle-light SPS scale by 1.30x. |
| 2901,2913,2925 | `SPSEffect.cs:231` | Memoria Entrance/Portal & Crystal World save spheres: brightens the SPS color by using basef=255 instead of 127 (no fade-dim). |
| 312 | `TileSystem.cs:670` | Returns overlay 5 as the padding-source-to-skip for a specific tile during atlas tile padding (Ice Cavern outside) |
| 2953 | `SmoothFrameUpdater_Field.cs:119` | Field smooth-frame interpolation: registers background overlay layers for sub-frame smoothing, normally skipping looping/scrolling |
| 2953 | `SmoothFrameUpdater_Field.cs:196` | Same Air-Garden looping-layer smooth-update exception, in the per-frame update pass. |
| 2953 | `SmoothFrameUpdater_Field.cs:240` | Same Air-Garden looping-layer smooth-update exception, in the final/commit smooth-update pass. |
| —(table) | `VoicePlayer.cs:321` | Festival of the Hunt: picks special '_held_N'/'_taken_N' voice-file append for the points messages of the 8 hunt participants, inc |
| —(table) | `VoicePlayer.cs:351` | Chocobo Hot&Cold: tracks specialCount and appends '_N' to the voice path for the gained-points message; resets count at game-start |
| —(table) | `VoicePlayer.cs:484` | Forces the dialog to be held open until the voice-acting sound finishes during the early-game 'I want to be your canary' Prima Vis |
| —(table) | `VoicePlayer.cs:488` | Holds dialog open until VA sound ends for the ending scene (Vivi monologue and stage afterwards). |
| —(table) | `VoicePlayer.cs:490` | Holds dialog until VA ends for Cid/Baku rescue lines against the Silver Dragons (zone 189). |
| —(table) | `VoicePlayer.cs:492` | Holds dialog until VA ends for the Alexander summoning chant lines (zone 89). |
| —(table) | `VoicePlayer.cs:494` | Holds dialog until VA ends for Kuja meeting the party at Mount Gulug (zone 484, 'How can that-'). |