# FF9 movement / control-lock survey — the complete map (2026-08-03)

Three cross-checked censuses, same method as `studies/messages/SURVEY.md`: the Memoria engine
source (`C:\gd\FFIX\Memoria\Assembly-CSharp\`), all 817 HW field-script exports
(`C:\gd\FFIX\reference\test2\`, **us-section only** — 411 exports carry a second `jp` block that
doubles naive grep counts), and the kit's own emitters. Engine line numbers are from the local
Memoria clone at commit-of-record; export citations give `test2_N.txt` + the field name from
`reference/field-manifest.tsv`.

---

## 0. The model in one paragraph

**There is no engine rule that dialogue, cutscenes, or events stop the player.** Field movement is
gated by four independent engine switches (§1), and everything that *feels* like an automatic lock
in stock FF9 is the script hand-rolling it: 1,108 of 1,108 stock talk handlers that open a window
take the lock explicitly (§6), via one universal five-flag macro used at 99.8% of all 6,051
`DisableMove` sites (§3). The lock is a **script convention with perfect compliance**, consumed by
a guard (`ifnot IsMovementEnabled return`) that opens 100% of stock trigger handlers. Control on
field entry is granted by the **script**, not the engine — `usercontrol` is zeroed on every field
load and the player object's `_Init` re-grants it, gated on the arrival entrance so chained
cutscenes can arrive still locked (§8).

## 1. The four engine gates (+ the pause umbrella)

All four are read inside `FieldMapActorController` (`Global\Field\Map\Actor\`); any one of them
being "off" stops the player. Above all of them, `UIManager.IsPause` (Pause/Quit UI) skips the
entire HonoBehavior list — a total freeze.

| # | Gate | State variable | Script access | Key engine sites |
|---|---|---|---|---|
| 1 | **usercontrol** | `EventContext.usercontrol` (global byte, NOT per-actor) | `DisableMove` 0x2D / `EnableMove` 0x2E; **`ExitField` 0x9E zeroes it too**; read-only as sysvar 2 (`IsMovementEnabled`) | write: `DoEventCode.cs:1048/1066`, `:866` (ExitField), `EventEngine.cs:627` (zeroed on EVERY field load); read: `FieldMapActorController.cs:638-641` |
| 2 | **pad mask** | `EventInput.PSXCntlPadMask[0]` | `AddControllerMask` 0xB9 / `RemoveControllerMask` 0xBA; `DisableMenu` sets only the menu bit | masking any direction bit flips `isMovementControl=false` → full stop **independent of usercontrol** (`EventInput.cs:395-401`, `FieldMapActorController.cs:586`) |
| 3 | **actor suspend** | `originalActor.state != stateRunning` | battle end (`EnterBattleEnd` suspends every object until the tag-10 handler returns at level 0) | `EventEngine.cs:780-791`, `FieldMapActorController.cs:588` |
| 4 | **UI player-control** | `FieldMapActorController.isActive` via `SetPlayerControlEnable` | none (engine-side: menus, shops, save, pause, transitions) | ⚠ quirk: `isActive==false` ALONE falls through into movement unless `IsMenuControlEnable` or `IsWarningDialogEnable` is also true (`FieldMapActorController.cs:161-169`) |

**What stops vs. what keeps ticking under `usercontrol = 0`:**

| Stops | Keeps ticking |
|---|---|
| d-pad AND analog walking, running, free turning, click-to-move | every object's script VM — **scripts are unaffected** |
| NPC talk/push detection + the "!" bubble (`ProcessEvents.cs:180-181` gates `CollisionRequest`) | NPC scripted motion (`MoveNPC` has no usercontrol gate — the lock is **player-only**) |
| **random-encounter accumulation** (`ProcessEvents.cs:493`) — a locked scene is encounter-safe | timers (`TimerUI` is a plain Update), collision service, camera |
| idle/sleep animation timer; the here-icon | scripted turns / head-focus (`ProcessEvents.cs:262-269`) |

`DisableMove` also kills the here-icon, resets `gMesCount`, clears the click-path, **and
force-disables the menu** (`UIManager.SetMenuControlEnable(false)`, `DoEventCode.cs:1051`);
`EnableMove` re-enables the menu **only if the pad mask permits** (`:1076`). So a bare move
bracket implicitly menu-locks for its duration, and a standing `DisableMenu` correctly survives it.

## 2. The opcodes

| op | HW name | engine | semantics |
|---|---|---|---|
| 0x2D | `DisableMove` | `UCOFF`, `DoEventCode.cs:1046` | usercontrol=0 + here-icon off + menu off + click-path cleared. Zero-arg, global — **no per-actor variant exists** |
| 0x2E | `EnableMove` | `UCON`, `:1064` | usercontrol=1 + conditional menu re-grant + idle-timer reset |
| 0xAB | `DisableMenu` | `MENUOFF`, `:2309` | pad-mask menu bit + `SetMenuControlEnable(false)`. **Cannot stop walking** (the menu bit is not in the movement mask). Yields the frame (returns 1) |
| 0xAA | `EnableMenu` | `MENUON`, `:2301` | clears the mask bit + re-enables. Does not yield |
| 0x27 | `SetTriangleFlagMask` | `BGIMASK`, `:2630` → `BGI_systemSetAttributeMask` | walkmesh-triangle attribute mask: **127 disables "restricted triangle" attributes** (scripted walks can cross normally-unwalkable triangles), 255 restores. A cutscene-walk enabler — NOT an exit-trigger guard |
| 0x9E | `ExitField` | `MOVQ`, `:866` | **also a lock**: usercontrol=0 + `flags\|=6` (collision-inhibit) on every active object + the movQData walk-out |
| 0xB9/0xBA | `Add/RemoveControllerMask` | `SETKEYMASK`/`CLEARKEYMASK`, `:2484` | the one script lock independent of sysvar 2; enables **partial control** (mask everything but one button) |
| 0x6A/0xF0 | `DisableRun`/`EnableRun` | `dashinh` | blocks running only |
| — | `SetEventEnable` | **NOT a script opcode** — engine C# API (`UIManager.cs:437`) | sets `FF9.attr\|=0x102`: pauses `ServiceEvents` (all scripts, encounters, fades) but **NOT the actor controller** — it alone never stops walking. Called by menus/shop/pause/text-load; scripts cannot reach it |

Sysvar 2 is **read-only** from script (`GetSysvar.cs:17`; no Set case) — `UCOFF`/`UCON` are the
only script writes. `EventInput.ReadInput()` — the function containing all the dialog/minigame
input checks — is **dead code** (zero callers; only `ReadInputLight()` runs).

## 3. THE STOCK MACRO — the control state machine

Stock never calls the verbs bare: **6,040 of 6,051 `DisableMove` sites (99.82%)** are this exact
macro, and 5,603 of 5,605 `EnableMove` (99.96%) its mirror:

```
set VAR_GlobBool_158 = 0                      |  set VAR_GlobBool_158 = 1
if ( VAR_GlobBool_159 == 1 ) {                |  if ( VAR_GlobBool_159 == 1 ) {
    DisableMove(  )                           |      if ( VAR_GlobBool_156 == 0 ) {
    if ( VAR_GlobBool_144 == 0 ) {            |          EnableMove(  )
        DisableMenu(  )                       |          SetTriangleFlagMask( 255 )
    } else { Wait( 1 ) }                      |          if ( VAR_GlobBool_144 == 0 ) {
}                                             |              EnableMenu(  )   } } }
SetTriangleFlagMask( 127 )                    |
```

| Flag | Meaning |
|---|---|
| `GlobBool_158` | "control should be ON" — the latch. `Main_Init` re-affirms it conditionally (812/817 fields), `Main_Reinit` too (380/385): **restore-not-grant** semantics after battle/menu |
| `GlobBool_159` | "this field session is control-capable" — cleared at the top of Main_Init, set near its end |
| `GlobBool_156` | one-way "never re-grant this session" (set-only; 44 fields: Festival of the Hunt, the Alexandria escape, Chocobo H&C timeout) |
| `GlobBool_144` | "menu externally suppressed — don't touch it" (Festival, Marsh frog-catching) |

**The universal guard:** 100% of `_SpeakBTN` (1,593), `_Range` (2,344), `_CardBTN` (250) open with
`ifnot ( IsMovementEnabled ) { return }` — zero exceptions. It *consumes* the lock (prevents
re-trigger during one); it is not a substitute for it. This is the kit's `MOVEMENT_GATE`, verbatim.

**Menu inside the macro:** redundant-looking (UCOFF already menu-locks) but load-bearing at the
edges — it makes menu suppression independent of the move bracket (the 144 flag, and the
walk-but-no-menu shape in §4).

## 4. THE DECISION TABLE — situation → stock form

| Situation | Stock form | Compliance / count |
|---|---|---|
| NPC talk (action press) | guard → **disable macro** → window(s)/choice → **enable macro** | **1,108/1,108 window-bearing `_SpeakBTN` — 100.0%** |
| Passive banner / ambience | `WindowAsync`, **no lock** — player walks under it | the ONLY lock-free stock windows: 6 sites (tutorial "Press [BTN]" ×4, Dali pigeon "Chirp", one leftover debug window) |
| Treasure chest | `Bubble(1)` **outside** the lock; Confirm enters: lock → kneel anim → `AddItem` + "Received!" (win 7) → unlock | `Bubble()` is inside a lock at only 0.7% of 1,049 sites — locking around a Bubble is wrong |
| Exit region (warp) | guard → duck sound → `CalculateExitPosition` → `ExitField` → macro → `PreloadField(5,·)` → white fade 24, `Wait(25)` → set `FieldEntrance` → `Field()` | `ExitField` BEFORE the lock (1,190/1,371); **nobody re-enables before a warp: 0/3,843 `Field()` sites**; destination re-grants |
| Shop | talk bracket + `Wait(3); Menu(2,N); Wait(3)` + NPC turn-back after unlock | `Menu(2,·)` 119/130 in-lock; no special substrate |
| Save moogle / Mognet | ONE long talk bracket (1,100+ lines) around everything incl. `Menu(4,0)` | `Menu(4,·)` **65/65 in-lock** |
| Card game | lock → prompt → fade white → `TetraMaster(deck)` → fade back → unlock **in place** (not a warp) | 246 brackets, 97.1% in-lock |
| Cutscene | lock in the trigger, body delegated via `RunScriptSync` (Waits tick in the callee), enable at the end or warp away | B3 = 889 brackets; only 1.9% of `Walk` sites are lexically in-lock — delegation is the norm |
| Timed sequence / festival | `144=1` (menu off for the whole event, script re-implements the menu button itself — the only unlocked `Menu(0,0)` sites), `156=1` on timeout, `Main_Reinit` re-locks per branch | Festival fields 550-572; Marsh 656-659 |
| Walk-but-no-menu | `EnableMove; SetTriangleFlagMask(255); DisableMenu` | **Chocobo H&C only** — 26 sites, all 4 forest fields, nowhere else |
| Arrive locked (chained scene) | the destination player-`_Init` grant gated on `General_FieldEntrance != N` | 64 sites |
| Partial control (tutorial) | raw `DisableMove` + `AddControllerMask` (all buttons but one) | Marsh moogle (652) only — the sole raw, guard-free lock toggles in the game |

## 5. The bracket taxonomy (6,011 brackets)

| # | Shape | brackets | fields |
|---|---|---|---|
| B1 | WARP/EXIT (never closed — destination re-grants) | 3,044 | 751 |
| B2 | DIALOGUE-ONLY | 1,409 | 437 |
| B3 | DELEGATE (lock, `RunScriptSync`, enable in the callee) | 889 | 381 |
| B4 | CARD GAME | 246 | 114 |
| B5 | MENU/SHOP/SAVE | 116 | 103 |
| B6/B7 | scripted motion / camera cutscene | 55 / 36 | 41 / 33 |
| B8 | TIMED (Festival) | 35 | 19 |
| B9 | BARE (`Wait` only — timing guards) | 114 | 98 |
| B10-B12 | anim-only / battle / ATE-toggle | 47 / 12 / 8 | — |

**Distribution:** `DisableMove` in 762 of 817 fields; the lock-heaviest fields are **towns** (Dali
Village Road 53, Lindblum Shopping 41), not cutscene fields — the count scales with NPC/exit
density. The 56 zero-lock fields are pure-cutscene (no-control) fields. **Pairing:** of 2,049
in-function-unpaired disables, 1,704 warp, 28 GameOver, 206 delegate the enable to a callee, ~92
unresolved. Double-disables are branch siblings or Festival re-locks — the macro is idempotent and
stock treats re-issue as harmless.

## 6. Dialogue — the ground truth (the census's decisive answer)

**The engine never locks the player for a window.** Audited: all 15 consumers of
`DialogManager.Visible/Activate`, `ETb.NewMesWin`, and the window opcode handlers. A window opcode
blocks only the **calling object's own thread** (`wait=254`, consumed at `EBin.cs:136-157`); the
player object is untouched. **A `WindowAsync` with no `WaitWindow` leaves the player free to walk
under the window — a real authoring capability** (stock uses it for its 6 passive banners).

The stock "can't move during dialogue" feel = the script's own `DisableMove`, 100% compliance
(§4). The only engine-side dialog effects: the **menu key** is suppressed while a dialog is
`Activate` (`UIKeyTrigger.cs:635`); a running talk drops the NPC to level 1, so a second talk
cannot fire mid-talk; plus 3 hardcoded exceptions (field 257 pauses the whole VM until the window
finishes animating; fields 1704/2921 auto-lock — **mobile only**).

**The stock rule to productize:** `WindowSync` (blocking) ⇒ always inside a lock.
`WindowAsync` as a passive banner ⇒ lock-free is legitimate.

## 7. Field entry, exit, and battle — where control actually comes from

- **Entry:** `StartEvents` zeroes `usercontrol` on every load (`EventEngine.cs:627`); the engine's
  entry grant (`FieldHUD.OnShownAction`, `FieldHUD.cs:394-401`) only *mirrors* `usercontrol`. **The
  field's own `.eb` `EnableMove` is the sole grant** — stock puts it in the player object's `_Init`
  right after `DefinePlayerCharacter` (567 fields), entrance-gated for arrive-locked scenes.
- **Exit:** `ExitField` zeroes usercontrol *before* the macro even runs; the destination re-grants.
  A field that warps away mid-lock is the normal case, not an error.
- **Battle:** entry backs up positions (`isBattleBackupPos` gate) and snapshots the event context;
  **return restores the pre-battle `usercontrol` via context-copy** (`EventEngine.cs:668`,
  `EventContext.cs:75`) and suspends every object until the tag-10 (`Main_Reinit`) handler returns.
  Stock's Reinit re-affirms via the 158 latch — **restore-not-grant**. (A scripted battle inside a
  lock comes back still locked; random encounters can't fire while locked at all, §1.)
- **Traps:** ladders force `SetPlayerControlEnable(true)` behind the script's back
  (`FieldMapActorController.cs:180-187`); 5 hardcoded fields run `MovePC` even with control off
  (1751, 404, 205/sid16, 2150/sid13, 900/sid13); `PauseUI.Hide` re-derives event-enable from a
  getter that only tests bit 1 — a `0x100`-only state can't round-trip.

## 8. The kit's surface today (from the 2026-08-03 kit census)

- **Faithful already:** the gateway warp template is the field-109 stock bracket **verbatim**
  (guard + 158/159/144 macro + `ExitField` + preload/fade/entrance/`Field`) — but the macro's lock
  is **conditional on GlobBool 159**, which no kit code sets: in kit-authored fields it's dead code
  and `ExitField`'s own usercontrol=0 carries the lock (in campaigns passing through stock fields,
  159 is usually left =1 and the macro fires). `MOVEMENT_GATE` = the stock guard verbatim. The
  choice/shop-region/savepoint/ladder/jump/platform lanes bracket like stock; savepoint is the only
  `DisableMenu` emitter (double bracket = the stock macro shape). Conductor/narration cutscenes
  lock with the grant-spin + watchdog + `REORDER_WAIT` machinery (three separate solutions to the
  entry-grant race stock solves with the 158/159 latches + entrance-gated grant).
- **The two kit laws:** (1) *RunScript-delegation* — an inline lock+Wait tread body froze in-game
  (the forced-ATE bug), so timed bodies delegate into an actor func (stock's B3, 889 brackets,
  agrees) — ⚠ the MECHANISM originally claimed here ("dispatch is usercontrol-gated" as the
  freeze explanation) was falsified by the §11 calibration: stock blocks under lock in tag-2 at
  518 working sites, and the engine gate is on NEW dispatch only. The practice stands; the
  discriminant is open; (2) *gate-inside-talk softlock* — `MOVEMENT_GATE` in a menu context
  early-returns because the talk already locked (the Lantern Hall ferry bug; stock never puts the
  guard anywhere but trigger heads).
- **Author surface:** `[cutscene] owns_control=false` is the ONLY control key an author can set
  (a release toggle, narration-lane-ignored, undocumented in FORMAT.md). No lock verb, no menu
  verb, no arrive-locked surface.

## 9. Cross-check verdicts — what fell

| Claim | Verdict |
|---|---|
| `npc.py`/`shop.py`: "the talk already halts the player, no DisableMove bracket needed" | **FALSIFIED** (engine: no such rule; stock: 1,108/1,108 talk handlers lock). **Kit plain-NPC dialogue and `shop_speak_body` let the player walk away mid-window** — un-stock behavior shipping today. `choice.py`'s contrary comment was right |
| export-census inference "`SetTriangleFlagMask(127)` masks exit triggers during a lock" | **corrected** — it's `BGI_systemSetAttributeMask`: 127 makes *restricted triangles crossable* for scripted walks; 255 restores |
| seed "0x25 = ATE launch" | wrong — 0x25 is `InitWalk`; ATE is `AICON 0xD7` + the winATE window flag |
| "call `SetEventEnable` from a field script" | impossible — engine API only, and it wouldn't stop walking anyway |
| seed facts confirmed | 0x2D/0x2E/0xAB identities; sysvar 2; MOVEMENT_GATE = stock's universal guard; the region-body law (mechanism: usercontrol-gated dispatch); shop hard-pause via `SetEventEnable` (engine-side) |

## 10. GAPS — engine/stock capabilities the authoring layer doesn't reach (ranked)

> **Tier 1 (items 1–4) is BUILT and IN-GAME PROVEN** (WINSTYLE bench @30601, 4 playtest rounds,
> owner-confirmed): the lock brackets on npc/shop/event bodies (per-lane stock defaults; a locked
> tread delegates via a player func), the `lock`/`lock_menu` keys, narration `owns_control`
> honored, `[player] locked_entrances` + `[[on_entry]] entrance` (the coverage-validated unlock
> hook), and the entrance-gated entry-settle grant. Two laws the playtests minted: THE
> CONCURRENT-BRACKETS LAW (two load-time lock brackets interleave — the first EnableMove frees the
> player mid-scene) and the narration lane's reorder-wait FALSIFIED (the player-init entry grant is
> model-load-timed; narration scenes now run the conductor's grant-spin + watchdog). 500 domain
> tests; the whole arc is on master.

**Tier 1 — the fidelity bug + the missing verb:**
1. **Lock the dialogue-bearing bodies like stock does.** `[[npc]]` plain talk, `shop_speak_body`,
   and `[[event]]` bodies with a sync `message` ship lock-free today (§9). Stock: 100%. Shape:
   default `lock=true` on any body that opens a blocking window; `lock=false` expressible for the
   passive-banner idiom (async, stock's 6 exceptions). `[[on_entry]]` already locks — make the
   lanes consistent.
2. **An author-facing `lock` surface** beyond the implicit lanes (e.g. per-block `lock` override;
   the release half exists as `owns_control` on one lane only — and is silently ignored on the
   narration form).
3. **A menu-lock surface** (`DisableMenu`/`EnableMenu` are raw constants with no wrapper, no key):
   per-block `menu=false`, and the walk-but-no-menu shape (stock's Chocobo idiom) for minigames.
4. **Arrive-locked entry** (stock: entrance-gated grant in the player `_Init`). Would replace the
   `REORDER_WAIT`/watchdog *race* with stock's race-free design for `then_warp` chains — the
   destination simply doesn't grant for that entrance id.

**Tier 2 (items 5–7) — BUILT 2026-08-03** (offline-proven; nothing here changes an in-game-verified
byte path except the Reinit gate, which is behavior-identical for every free-roam battle):
5. ~~`SetTriangleFlagMask` on scripted walks~~ ★ BUILT — a WALK-bearing locked conductor scene
   brackets the mask like stock's macro (127 with the lock, 255 with the enable; a `then_warp`
   scene skips the restore — the engine resets the mask per field load, WalkMesh.cs:1690).
   Walkless scenes byte-identical.
6. ~~**Lock-hygiene lint**~~ ★ BUILT into eblint (warnings), **calibrated over all 818 real fields
   before shipping**: unpaired-lock (71 stock hits = exactly this section's ~92 cross-object
   residue, e.g. field 57's lock-and-raise-Map[24] choreography; subroutines + Init funcs exempt),
   gate-under-lock + its dispatched flavor (**0 stock hits**), and the cross-field
   `lint_warp_grants` (a literal `Field(N)` into a sibling that never `EnableMove`s — wired into
   multi-member `build_mod`). ⚠ The planned **inline-lock tread-freeze check was FALSIFIED and
   dropped** — see §11.
7. ~~Partial-control / one-way latch / Reinit~~ ★ BUILT: `[[event]] mask_buttons`/`unmask_buttons`
   (0xB9/0xBA, stock's tutorial lane — the census missed that stock uses it beyond Marsh: masks
   240/255/128/1 ship across ~8 fields); `[cutscene] stay_locked` (latches stock's own MAP 156);
   and `Main_Reinit` is now RESTORE-NOT-GRANT with **zero bracket churn** — the engine restores the
   pre-battle `usercontrol` via context-copy BEFORE requesting tag-10 (EventEngine.cs:668-669), so
   the handler gates its grant on `IsMovementEnabled && !MAP156`: the engine's restored context IS
   the latch stock maintains GlobBool 158 for.

## 11. Open questions

- **The tread-freeze discriminant (SHARPENED 2026-08-03, the item-6 calibration).** The old law
  "a tag-2 body's blocking ops stop ticking under its own lock" is **FALSE as a generalization**:
  stock ships **518** tag-2 sites that block under their own `DisableMove` and work — field 51
  entry11/tag2 is a complete counterexample (the ExitField-less exit variant: guard → macro lock →
  `Wait(1)` → STFM → Preload → `RunScriptSync(player)` → `Wait(4)` → `Wait(5)` → fade → `Wait(25)`
  → `Field(53)`, ALL inline in the tread body). Engine: `ProcessEvents.cs:177-181` gates only
  DISPATCH (`if (GetUserControl()) CollisionRequest(actor)` — new tag-2/3 Requests need control);
  an already-running body's script VM ticks regardless. So the kit's in-game forced-ATE freeze
  (real, observed, fixed by delegation) has some OTHER discriminant — untraced. The delegation
  shape stays the kit's proven idiom; a static freeze check is unsound and was calibrated out.
- Whether GlobBool 158/159 residue from stock fields can make a kit field's gateway macro fire
  differently mid-campaign (harmless either way — `ExitField` locks regardless — but untested).
