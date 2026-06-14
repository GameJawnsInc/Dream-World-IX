# Fork Fidelity — the honest gap map toward "recreate the functioning game from borrowed fields"

> **North star (not a release).** The objective is to keep refining borrowed/forked fields until the kit can
> recreate the *functioning game itself* from them. The measure of progress is **fidelity**: fork a real
> field → does it play identically to the original? This doc is the honest, prioritized gap map. Produced by
> the `fork-fidelity-audit` workflow (7 parallel per-dimension auditors → synthesis), 2026-06-11; grounded in
> the current code (citations inline in the audit), the project memory, and the docs.

## Headline

Fork fidelity is **strong on the "physical" layer and partial-to-absent on the "narrative state" layer.**

- **Physical layer — faithful, in-game proven.** The SCENE dimension (camera math to 0.0005 px, verbatim
  `.bgi` walkmesh frame, native point-sampled per-tile occlusion, MapConfigData lighting) and the static
  mechanics (ladders, jumps, save-point synthesis, encounters, music, after-battle reinit) reproduce the real
  field.
- **Object/NPC carry — ~75% and advancing.** Verbatim `.eb`-entry graft + player-func graft + per-language
  text carry; the **verbatim save-moogle carry is COMPLETE** (P1–P6.1, on master — director graft + the
  spawn-pose fix that resolved both timing bugs). The graft lane is now FREE (the deferred items below unblock).
- **Narrative state — the weak axis.** A fork boots with a **zero `gEventGlobal`**, no ScenarioCounter, no
  flag presets, and a single heuristic spawn regardless of which door you entered. (A field's **entry
  cutscene** is NOT a separate problem — it runs from the field's own `.eb`, so a **verbatim** fork carries
  it; see the `NarrowMapList` correction below.)

**Honest grade: a high-fidelity diorama of a field, not yet a faithful slice of the playthrough** — *via the
declarative carry.* You can fork a story room and walk around it faithfully; the declarative rebuild can't yet
have it *behave* as that story beat.

> **`import --verbatim` changes this for self-contained story fields.** It ships the donor's WHOLE `.eb`
> (entry-0 + every object + every gateway, layout intact) and runs the **real logic** instead of
> re-synthesizing — a faithful *slice*, in-game proven on Dali Inn (the gated door OPENS, the cast gates by
> story beat). It ships the whole `.eb`, so it even subsumes #2b's ref-bearing gated doors (every entry is
> carried) **and now speaks** — it ships the donor's whole `.mes` so its index-txids resolve in the right
> language (in-game proven on Dali Inn: renders + runs the real logic + English dialogue). The only remaining
> item is the cosmetic entrance-fade model-streaming flicker on an F6-warp. (`content/verbatim.py` + the
> `[verbatim_eb]` block.) **Both field-load levers fire in a verbatim fork** — `[startup]` (boot a beat) and
> `[[on_entry]]` (a gated, once field-load beat) are armed onto the donor's real Main_Init (the shared
> `build._apply_startup` / `_apply_on_entry`), and an `[[on_entry]]` **narration message now SHOWS too**
> (in-game proven on a Dali-Inn verbatim fork): the authored line is appended to the donor `.mes` *above its
> txids* (`build._verbatim_on_entry_messages`, the `--carry-text` trick) so the hook's `WindowSync` resolves
> into it — message + gated state-advance both fire on top of the donor's real logic.
>
> **`import-chain --verbatim` extends this to a CONNECTED SLICE** (a region, not one room). Every member forks
> native + verbatim, and the in-chain `Field()` exits are **retargeted to the chain's own member ids** (the
> `[verbatim_eb] retarget` table, pre-filled from the chain's id assignment) so the doors warp between the
> forks instead of back into the live game; out-of-chain exits stay live seams. Each member ships its donor's
> whole `.mes` at the donor's **own registered textid** (`EVENT_ID_TO_MES` — a valid MesDB key, so the
> FieldScene registers; all 676 forkable fields are covered, so the `1073` fallback never fires; same-zone
> members share a textid and ship identical text → no clobber). `import-chain --verbatim --out C → build-all`
> compiles a drop-in mod whose `.eb`s carry the retargets in their shipped bytes. **In-game proven** (a 4-field
> Dali slice: the doors warp between the forks — ids verified via F6 — each screen runs its real logic and
> speaks its real dialogue).

## Play a fork today

`import --native --graft-player-funcs --carry-text`, warp in via F6. **You get:** correct background art with
seam-free per-tile occlusion + correct 3D-model lighting; the byte-exact (multi-floor) walkmesh; the right
camera + control direction; working ladders/jumps; the field's random encounters with the right BGM and a
clean after-battle return; carried NPCs/props that render byte-identically, speak their real per-language
lines, and respond to push/talk. **You don't get:** the field plays in its **scenario-zero state** — every
story-gated NPC/door/event defaults to the not-yet-happened branch (hidden areas may be exposed, story NPCs
absent); you **spawn at one fixed point** no matter which gateway you arrived through; any field-entry
**cutscene won't auto-fire** from the C# table (re-author it declaratively with `[[on_entry]]` — a gated,
once field-load beat); exit gateways warp correctly but **don't advance the ScenarioCounter** unless you add
a `[[gateway]]` `set_scenario`/`set_flags`.

Note: faithful carry is **opt-in** (the three flags above). A plain `import` is BG-borrow with no
object/text/func carry. For the most faithful single field use `import --verbatim`; for a connected region use
`import-chain --verbatim` (each member runs its real logic + speaks, doors wired to siblings — the scenario-zero
caveats above are then governed by each donor's real story gating, presettable per-member with `[startup]`).

## Solved (faithful today)

- **SCENE** — camera math (decompose/synthesize, `k=14/15`, exact scale-1 canvas map, yaw, character-offset
  measured 0); walkmesh frame (`vert+orgPos+floor.org`, verbatim `.bgi`, 7-floor seam reconcile); native
  seam-free per-tile occlusion (`--native`, no `.bgx`) + MapConfigData lighting.
- **MECHANICS** — navigable ladders (single/multi-rung/bent-vine) + jumps (Ice-Cavern arcs), verbatim;
  save-point synthesis (`Menu(4,0)`, save→reload into a custom field works); spawn-off-trigger guard.
- **BATTLE** — random-encounter scene/frequency/pattern carry + field BGM (entry + after-battle resume) +
  tag-10 Main_Reinit after-battle fix.
- **OBJECTS** — verbatim `.eb`-entry graft, STARTSEQ-helper closure, player-function graft, op78 expr-uid
  remap, multi-`DefinePlayerCharacter` normalization.
- **TEXT** — verbatim per-language `.mes` carry for grafted NPC tag-3 dialogue + text player funcs, remapped
  to a clean TXID band; byte-identical when not carried.
- **FLAGS** — read / name / create / recreate `gEventGlobal` + `flags-diff` + `save-edit`; reserved-band lint.

## Prioritized worklist (biggest leverage first)

A **graft-lane** tag = a fix would edit `content/object.py` / `content/player.py` / `eventscan.py` /
`content/savepoint.py` / the `extract.py` graft code. The save-moogle session that held this lane has **LANDED
(2026-06-11)** — the lane is now FREE, so the graft-tagged items (#9, #11, #12) are workable too (no longer
deferred). Orthogonal items remain the lowest-risk picks.

| # | Gap | Sev | Diff | Graft lane | Direction |
|---|-----|-----|------|:---:|-----------|
| 1 | ~~**Story-flag / scenario presets** — a fork boots at scenario-zero~~ | **blocker** | medium | no | **✅ LANDED — the `[startup]` block** (`content/startup.py`): `scenario = N\|"area"` + `flags = [{flag, value}]`, prepended to Main_Init via `edit.insert_in_function` (golden byte-identical when absent); lint flags reserved-region presets. A fork can now boot in the right beat. *In-game verification (a fork's F6 reads the asserted SC) is the human step.* Remaining: per-door spawn (#9) + gated doors (#2). |
| 2 | ~~Story-branch **doors** collapsed (`if(flag){Field(A)}else{Field(B)}`)~~ | major | medium | no | **✅ LANDED** — the import flags stacked story-branch doors (>1 distinct dest at one zone; ~43 real fields) with a note + `requires_flag` stub per branch + a count/warning; `lint_logic` warns on ungated co-zone gateways. Gating is in-game proven end-to-end (`requires_flag`→`gate_flag`). **#2b LANDED + IN-GAME PROVEN:** a forked Dali Inn gated door loads, runs, and stays **GATED (closed) at scenario-zero** instead of the declarative rebuild's always-open — the conditional state machine is preserved (it reads GLOB flags 2064/2073/2078; toggling them via F6→Flags makes the gate respond). A *story-gated DOOR* (a real `if(flag)` door is a complex multi-flag state machine, NOT a simple gate — capturing it as one `requires_flag` is wrong) is now carried **VERBATIM** — `scan_gateway_entries` classifies it, the import emits a `[[gateway_carry]]` block + `.gatewayN.bin` sidecar, and `graft_gateway_entry` grafts the whole entry + retargets its `Field()` ids (its GLOB conditions then read the `[startup]` story state). 40 fields have them; **35/~50 gated entries are self-contained (carried)**, 15 reference other entries (left as ungated seams + a warning — need the object-carry ref machinery). NPCs/events were never affected (objects are already grafted verbatim). |
| 3 | ~~Scenario-counter doesn't advance on exit → chaining forks never progresses the story~~ | major | medium | no | **✅ LANDED** — `[[gateway]]` gains `set_scenario` (ScenarioCounter; int or area name) + `set_flags = [{flag, value}]`: when the player TAKES that exit, the `set_var` writes are prepended to the gateway's Range trigger behind a `usercontrol` guard (fire only on a real walk-out) and behind any `requires_flag` gate (only when the exit is open), just before `Field()`. Reuses `startup.startup_body`; validate + reserved-band lint mirror `[startup]`. Pairs with #1/#2 so a forked chain progresses the beat. *(In-game: F6 reads the advanced flag/SC after walking the door — human step.)* |
| 4 | ~~**BG-borrow black-screens area<10** (Alexandria area1, Cargo Ship area0)~~ | **blocker** | easy | no | **✅ LANDED** — `_cmd_import` auto-routes area<10 to `--native` (ships its own art at a remapped area≥10, seam-free + lit), with a note. A plain `import` of an early-game field now works (in-game proven on the area-8 Dali room). |
| 5 | ~~Talkable-stub / dangling-player-tag **softlock / wrong-text on a plain (no-flag) import**~~ | major | medium | no | **✅ LANDED** (both halves, build-side). **(b) dangling player tag** = the softlock: `validate()` decodes each carried `[[object]]` and flags a `RunScript(player, tag)` to an un-grafted tag (`_entry_player_call_tags`) — a **build-blocking error** (import with `--graft-player-funcs`; init_only carries drop the interactive func so they don't dangle). **(a) un-carried talkable text** = wrong/missing dialogue: `lint_logic` decodes each carried object's talk windows (`_entry_window_txids`) and warns when a shown donor txid isn't in the `[carry_text]` plan (import with `--carry-text`, or author the line). Validated against real imports: a plain `--native` Daguerreo fork flags all 5 talkable NPCs; a `--carry-text` fork (DGLO_FORK) is silent (no false positive); props are skipped. (kit 0.9.20) |
| 6 | Battle-scene BGM metadata not wired (minted scene plays silent) | major | medium | no | Extract donor scene's battle song id → emit `BtlEncountBgmMetaData.txt` at build (battle/ + BattlePatch; no field graft) |
| 7 | ~~Large scrolling field unverified in real gameplay (math implemented + unit-tested only)~~ | minor | easy | no | **✅ VERIFIED IN-GAME** — a native fork of the wide Alexandria Main Street (field 3000, walkmesh ~12,800 units across, `[camera.scroll] enabled`) deployed to the test slot scrolls correctly: the camera pans 1:1 to follow the player across the full painting width, art stays aligned to the floor. The kit's scroll synthesis (`enable_camera_services` / BGCACTIVE) holds on a genuinely large field, not just the unit-tested math. |
| 8 | BG-borrow `.bgx` tile seams (bilinear path; edge-bleed exists only on the editable path) | major | medium | no | Steer faithful forks to `--native` (seam-free); optionally port edge-bleed into the `.bgx` writer |
| 9 | ~~Per-door spawn arrival — one spawn regardless of entrance~~ | major | hard | was yes | **✅ LANDED + IN-GAME PROVEN.** `eventscan.scan_player_arrivals` decodes the real per-entrance arrival table (warp sets entrance var `D8:2` → the player Init reads it via a `0x06 JMP_SWITCHEX` → one `D9(0)/D9(4)/D9(6)` block per door). **(a)** `fork-report` gains an **Arrival** line flagging fields with >1 spawn point. **(b)** `extract_field` now defaults the synth `[player] spawn` to the donor's REAL main arrival (nearest the visible centroid, among arrivals in-bounds/on-cam/clear/in-main) instead of the c.1 centroid guess — Dali fork moved `(83,209)`→ real entrance `(439,-122)`, in-game proven on scratch 4012. **Scope:** a synth fork can't reconstruct the per-DOOR table (its gateways are RETARGETED → donor entrance indices don't carry over); per-door fidelity is `--verbatim`'s job (it ships the whole player Init), and the Arrival line steers there. (kit 0.9.78-0.9.79) |
| 10 | Field-entry cutscene on a fork | major | **mostly SOLVED** | no | **✅ Premise CORRECTED + covered both ways.** The old framing ("entry cutscenes fire from a C# `NarrowMapList` table the `.eb` can't carry → needs an engine fork") was **WRONG** — verified in the Memoria source: `NarrowMapList` is the per-field **camera-WIDTH / widescreen** table (PSX screen widths, narrow-vs-wide cam, crop margins), with **zero** cutscene logic. A field's **entry cutscene runs from its own `.eb`** (entry-0 `Main_Init` + actor LOOP sequences). So it's covered: a **`--verbatim` fork carries the real cutscene** (in-game proven — Vivi/field 100's ticket-girl opening), and **`[[on_entry]]`** (`content/onentry.py`) re-authors a gated, once entry beat for a synthesize fork (`message`/`set_scenario`/`set_flags`, gated by `requires_scenario`/`requires_flag`; armed by `InitCode` in Main_Init). The only genuine engine-side residual is **cosmetic and keyed on the donor's real id**: the widescreen camera-width (`NarrowMapList.MapWidth` → defaults to 500 for a custom id), a few per-actor anim tweaks (`FieldMapActor.cs`), and FMV playback (field 70) — optional to backfill by registering the custom id in those tables. |
| 11 | Non-tag-3 / choice/menu window carry — carried NPCs' choice prompts + event windows still point at donor TXIDs | major | medium | partly | **Mostly covered + lint-warned.** `collect_carry` already scans windows in ALL kept object/player tags (not just tag-3), and choices ARE windows (carried). The residual is a NICHE: verbatim-carried `[[gateway_carry]]` story-gated doors that open their own window (only **2 real fields**: 352, 552) keep the donor txid — the carry-text remap doesn't touch gateway entries. `lint_logic` now WARNS on it (use `--verbatim`, which ships the whole `.mes`). Full carry+remap of gateway-entry windows deferred (low value). (kit 0.9.80) |
| 12 | Non-Zidane player donors (~8%, Garnet/Steiner rig clip-id mismatch) | major | hard | **yes** | Clip-id remap table per donor rig, or carry the donor party-member as the fork player. **Defer** (player.py) |
| 13 | Per-fork battle-background override (scene_id maps to BBG globally) | major | hard | no | Only when minting a scene that reuses vanilla gameplay but a custom BBG; battle-pillar enhancement, low priority |
| 14 | ~~Make a forked field's render-only NPCs interactive (talk-handler graft closure)~~ | major | — | **was yes** | **✗ CLOSED — PROVEN INFEASIBLE (2026-06-12).** Verified census of all 675 fields under MAXIMAL grafting (self-dep fixpoint modelled): **55 NPCs / 36 fields render but lose their tag-3 talk handler, and 0 are blocked only by a graftable gesture** — every one depends on the field's own logic (Main_Init shared branches 40 / exotic player sequences 15 / uncarried co-actors 4 / unsafe bg script 1 / party 1); a further 39 objects (20 fields) are refused outright (LOOP un-graftable). A dropped tag-3 isn't a gesture — it's the field's **quest logic**, inseparable from its text/economy/geometry (the engine even hardcodes a `mapNo==2803` walkmesh hotfix for Daguerreo 2F's librarian). **`--verbatim` already carries it byte-for-byte = the standing answer.** Shipped instead: **`fork-report --explain`** decodes any field's NPC routines to readable English so you read the quest + decide per-field. (NOT #11/#13 — those are separate and still open.) |

## The next step

**Landed:** #1 (`[startup]` presets), #2 (gated story-branch doors), #3 (`[[gateway]]` on-exit advance —
`set_scenario`/`set_flags`), #4 (auto-`--native` for area<10 — a plain `import` of an early-game field
now works, in-game proven), #5 (softlock + un-carried-text lint), #9 (per-door arrival: the Arrival diagnostic +
a real-arrival default spawn, in-game proven), **#10** (premise corrected — entry cutscenes are `.eb`-borne,
carried by a verbatim fork; `[[on_entry]]` re-authors a gated entry beat for a synthesize fork), #13 (the
story-event director/roster tail — roster-by-beat analyzer, synth director-skip, stacked-pair dedup, walkable
spawn), and #14 closed as proven-infeasible (`--verbatim` is the answer; `fork-report --explain` reads the quest).
Plus the verbatim save-moogle carry (P1–P6.1) and the verbatim `.eb`+`.mes` fork (`import --verbatim`).

**The small/orthogonal narrative-state backlog is now CLEAR.** What remains is bigger or out-of-lane:
- **#6 / #13(battle-bg)** — battle-pillar (BGM metadata / per-fork BBG); the `battle_design` lane owns these.
- **#8** — BG-borrow `.bgx` tile seams: already mitigated (faithful forks use `--native`, seam-free); porting
  edge-bleed into the `.bgx` writer is a low-priority cosmetic.
- **#11** — gateway-entry window carry+remap: only 2 niche fields; now lint-warned (use `--verbatim`).
- **#12** — non-Zidane SYNTH donors (rig clip-id mismatch): `--verbatim` already plays them identically + the
  controlled PC is computed; `fork-report` warns on a `--swap-player` gesture glitch. Synth is lossy by design.

Extraction of *which* flags a real prior field set on exit remains a separate, later, eventscan-touching task —
the author asserts the beat for now (they have the game knowledge — cf. `feedback_trust_user_game_knowledge`).

## The carry decision — bring-in vs drop vs impossible (fork-mode taxonomy)

> A cross-dimension consolidation (12-dimension `fork-content-taxonomy` workflow, 2026-06-14: classify → adversarial
> challenge → synthesize; every "impossible/should-not" call was challenged, and the corrections are folded in —
> claims a challenger refuted are NOT carried forward; two were re-verified against live code before landing here).
> It reframes the "Solved vs worklist" split above into the question an author actually faces per content type:
> **do I carry this, drop it, or accept it as lost?** The entry-camera `entry_settle` dig is what surfaced the
> need — it isn't a fidelity *bug*, it's the band-aid for one genuinely-impossible item, and telling that apart
> from "donor identity I should drop" is the whole point.

### The governing principle

**The taxonomy is fork-MODE-relative, and one engine fact decides almost every call: is the behavior owned by the
field's `.eb`/`.mes` bytes, or by an engine table keyed on the donor's real `fldMapNo`/FBG-name?**

- **Donor-IDENTITY content** (area-title card, scenario cutscene roster, the donor's lines, its doors, its player
  rig, its encounter table/BGM) is **`.eb`/`.mes`-owned** → **BROUGHT-IN under `--verbatim`** ("BE this field" — you
  ship the whole `.eb`+`.mes` and want exactly this) and **DROP under BG-borrow / repurpose** ("reuse the room" — the
  hub borrows Mognet's room but is NOT Mognet). NATIVE-SYNTH sits between: faithful *physical* layer + carried
  objects/text where graftable, but **re-synthesized logic that boots at scenario-zero** — it keeps the diorama and
  drops the narrative *machinery* (warp-directors, rotating roster).
- **IMPOSSIBLE is the residual no mode can reconstruct on stock Memoria**, and it is *narrow*: almost entirely
  **engine tables keyed on the real `fldMapNo`/FBG-name** that a minted id (≥4000) is simply absent from, with **no
  `.eb` opcode reach**. For each, a dev-only DLL patch *would* solve it (the proven-but-unshipped `s23` narrow-map
  patch is the template) but is **declined to keep the shipped mod engine-independent**.
- **One genuinely-hard NON-engine residual: copy-only perspective geometry** — ladder climb-arcs, jump parabolas,
  the save-Moogle pop-out coords are hand-tuned to the donor camera and can only be *copied* (verbatim carry), never
  generated from scratch. Not an engine wall; a from-scratch *authoring* ceiling.

**Decision shortcut:** `.eb`/`.mes`-owned → flips by mode (verbatim keeps, repurpose drops). Keyed on a real
`fldMapNo`/FBG-name engine table → mode-independent and IMPOSSIBLE on a mint.

### The author's decision rule

Pick the fork's PURPOSE first; the mode and the carry/drop list follow.

1. **Faithful replica ("be this field") → `--verbatim`.** Carry everything (`.eb`+`.mes` whole, only `Field()`
   retargeted). Then: **assert the beat** with `[startup] scenario=N` (a verbatim fork still boots scenario-zero —
   `gEventGlobal` is the save blob, not in the `.eb`; this is what makes the carried directors/roster/gated-doors/
   area-title behave). **Keep the donor id IN-PLACE** iff you need a real-`fldMapNo`-gated engine behavior
   (narrow-map masking, Chocobo live-HUD, ATE trophy) — otherwise accept those as lost on the mint.
2. **Reuse-the-room ("new purpose") → plain `import` (BG-borrow) or the hub generator.** Carry no donor-identity by
   default: **suppress** the area-title (`hide_area_title`), author your own `[[npc]]`/`[[choice]]` dialogue and
   `[player] model=`, emit no donor `[encounter]`/`[music]`, let the synth director-skip drop warp-directors. Author
   the new graph (your `[[gateway]]`, retargeted exits, a synth `Menu(4,0)` save point). **Add `entry_settle`** (a
   thin synthesized Main_Init reveals immediately — the black-hold is the *faithful* answer, the same convergence-
   behind-black the real game uses). Single-owner discipline: the HUB owns field-70; per-journey items via scripted
   `give_item`, not the global CSVs; accept `Leveling.csv` as a global default.
3. **Faithful diorama, re-synthesized logic → `import --native --graft-player-funcs --carry-text`.** Room contents
   without its story machine. **Fall back to `--verbatim`** when the field has a moving platform/lift (no synth
   tile-motion injector), a non-Zidane player (synth refuses the anim-bearing rig), or per-door arrival that matters.

### IMPOSSIBLE on stock Memoria — the genuine engine residuals

All keyed on the real `fldMapNo`/FBG-name or a fixed compile-time structure with no `.eb` reach. A dev-only DLL patch
would fix each; all declined (the only sanctioned custom DLL is the dev-only F6 menu; `s23` narrow-map is the
proven-but-deliberately-unshipped template).

| # | Residual | Why engine-blocked | Stock band-aid |
|---|----------|--------------------|----------------|
| 1 | **Entry-camera ease elimination** | `SmoothCamDelay`/`SmoothCamActive` engine internals; player binds AFTER the snap window; `SmoothCamExcludeMaps` is a hardcoded real-id set (`FieldMap.cs:2532`); no `.eb` op re-arms it. **Universal across all synth modes** — verbatim only *hides* it behind a long real entry sequence. | `entry_settle` black-hold (faithful, not a kludge) + source-side `WARP_FADE`. Runtime `CameraStabilizer` is per-user (`Memoria.ini`) → a baked `Wait` can't adapt; offline default-stabilizer estimator is UNBUILT-not-impossible. |
| 2 | **ATE seen-state + ATE80 trophy** on a custom id | `EMinigame.MappingATEID` is a hardcoded if/else on real `fldMapNo` → −1 for ≥4000; `AteCheck` lives on `AchievementState`, not `gEventGlobal`. The ATE itself *plays* fine (verbatim / `[ate]`); only the bookkeeping is lost. | Fork in-place on the real id (in tension with verbatim's normal ≥4000 mint). |
| 3 | **Narrow-map letterbox masking** on a mint | `NarrowMapList.MapWidth` is a hardcoded `fldMapNo` table (ids ≤3100) → mint falls to `return 500` = not-narrow; the `ConditionalForceNarrow` escape ALSO requires a real-id match (`RestrictedWidthScenesList`). | Fork in-place (keeps `fldMapNo`); `s23` patch proven 2026-06-14, NOT shipped. → `project-ff9-narrow-map-fork-letterbox`. |
| 4 | **Chocobo live dig-HUD** on a minted fork of 2950–2952 | `EventHUD.cs:384` gates the live timer HUD on literal `fldMapNo==2950\|\|2951\|\|2952`. (The *instruction popup* is `FieldZoneId==945`-keyed → reachable via `--text-block 945`; only the live HUD is id-locked.) | Fork in-place on 2950–2952. |
| 5 | **Field-70 FMV + ~12 per-actor anim tweaks** on a mint | `FieldMapActor.cs` has `fldMapNo`-keyed per-actor tweaks; FMV bound to the real id. *Generalizes:* any real-`fldMapNo`-gated engine behavior is lost on a mint. | Retarget the stock field-70 override rather than mint FMV behavior. |
| 6 | **A brand-NEW FMV slot** (beyond FMV000–060) + paired audio | `MBG.MBGDiscTable` is a fixed `static readonly` jagged array `MBG.Seek` indexes directly — no `.eb` reach; `.akb` audio is name-keyed (doubly blocked). | Reuse/repoint an existing slot (`fmv-swap` proven on FMV000); the `.bytes` layer is open. |
| 7 | **Per-fork BBG/tuning on a REUSED vanilla scene** | scene→BBG resolves `Info.BattleBackground ?? MapModel[...]`; `BattleBackground` is the `[PatchableField]` override point but still **per-scene-id global**, no per-field dimension; `raw16`/`raw17` are per-scene-id whole-file. | **Unnecessary**: MINT a fresh scene (`battle-import --fork-scene`) → its own BBG + tuning on stock. |
| 8 | **A brand-NEW custom playable member** (13th+ in menu/battle/save) | `CharacterId` is a fixed 0–11 compile-time enum; fixed-layout save (`PLAYER[9]`); `SetupPartyUID` can't bind a no-event-id member. The hard frontier. | None for a true new member (reskin a slot or add existing cast). |

Two residuals are **not engine-fixable at all** (no DLL helps): **cross-rig gesture remap** (0/15 of a Vivi
cutscene's clips have a Steiner equivalent in the global `AnimationDB` — a DLL can't invent artist-authored clips)
and **from-scratch perspective-correct arcs/pop-out** (hand-tuned coords, copy-only). The faithful answer to both is
`--verbatim` with the original rig.

### SHOULD-NOT — donor identity to DROP on a reuse (flips to BROUGHT-IN under verbatim)

The genuinely-new category. Each is correct-and-wanted under `--verbatim` (the fork BE-comes the field) and wrong
under BG-borrow/repurpose. Most are already handled; the gaps are flagged.

- **Area-title card** ("Mognet Central"/"Ice Cavern") — donor-identity name overlays. HANDLED: `[field]
  hide_area_title=true` → `content/areatitle.hide` prepends `ShowTile(i,0)`; hub auto-emits. In-game proven (hub 4600).
  ✅ **Now also auto-suppressed on a `--native`/`--editable` synth fork** (kit 0.9.97): the leak isn't BG-borrow-only
  — the title is keyed on the scene `mapName` (`FieldMapLocalizeAreaTitle.GetInfo`) and active-by-default, so a synth
  fork ships the donor scene's overlays with no donor `.eb` to fade them (static card). `import --native`/`--editable`
  of an area-title field auto-emits `hide_area_title` + `area_title_overlays` (via `areatitle.title_range`);
  **`--verbatim` is left untouched** (it carries the donor `.eb`'s real scenario-gated show+fade — title wanted there).
- **Scenario cutscene roster / warp-directors carried as standing NPCs** — HANDLED on synth (`_loop_warps` drops any
  LOOP firing `Field()`; 2-shopkeeper→1 proven) and BG-borrow (carries no `.eb`). ⚠ The destructive synth-drop keys
  on `Field()` (0x2B) ONLY — **deliberately narrow** (spares animated props + the save-Moogle puppet, per worklist
  #13b); a pure *phase-switch* rotation director (no warp) slips it and is caught only *incidentally* by the #13
  arg-dedup + roster analyzer. (The advisory `forkreport._is_director` is correctly *wider* — 0x2B OR 0x06. The
  asymmetry is by design: advisory-wide, destructive-narrow.)
- **Donor talk dialogue / choice prompts** as the room's words — opt-in + import-only, so a plain import ships none.
- **Donor player identity** (you-become-Vivi) in a hub — plain import carries no player `.eb`; the hub declares its
  own `[player] model=` Moogle. (And `--swap-player --neutralize-gestures` trades a cutscene rig's emoting for
  not-glitching when reusing a cutscene field for free-roam.)
- **Donor exit destinations pointing back into the live game** — `verbatim.remap_fields` retargets in-chain `Field()`
  (0x2B), leaves out-of-chain as commented live seams. ⚠ A WorldMap (0xB6) lift/gateway exit needs the SEPARATE
  `worldmap_inject` path — any "retarget the exits in a chain" guidance must name BOTH link modes.
- **Donor party-reset on entry** (`SetPartyReserve` 0xB4) overwriting an authored `[party]` — surfaced (advisory
  `party.field_resets_party`, verbatim path), not stripped.
- **Per-fork single-owner globals** — field-70 New-Game ownership (a non-hub slice must not hijack it; `deploy_journey`
  refuses New Game unless `--wire-newgame`), per-journey items baked into global `InitialItems`/`DefaultEquipment` CSVs
  (`lint_manifest` warns → scripted `give_item`), per-fork character GROWTH (`Leveling.csv` is whole-file
  highest-wins, single-owner — the *curve* is authorable on stock; making it differ *per-fork* is the same
  single-owner-global limit as items, so accept the global default).
- **Per-door D8:2 arrival table** — NOTE: this is really an **UNBUILT fidelity gap, not donor-identity-to-drop**.
  Carrying it would be *more* faithful; synth collapses to one spawn only because multi-branch player-Init authoring
  (decode + entrance-write + SWITCHEX-emit — all primitives the kit already has) isn't wired. `--verbatim` carries it.

### Audit corrections & doc-refresh items (verified against live code 2026-06-14)

- **`[startup]`/`[party]`/`[[on_entry]]` on a 0x06-jump-table donor WORKS** — a prepend (`rel_off==0`) is exempt from
  the jump-table refusal (`eb/edit.py:227`, the check only fires on a *mid-function* insert; docstring cites field
  206). The `build.py:2062` `_field_load_inject` BuildError docstring + message still name "field 100 … can't yet
  shift past" — **STALE**; the prepend path handles jump-table donors, the guard now only nets a hypothetical
  mid-function field-load insert. (Refresh the prose.)
- **Battle BGM (#6) is overstated as "minted scene plays silent."** The `Battle:`/`Music:` BattlePatch channel is
  WIRED and keys on the battle *scene id* (which a fork keeps), so the donor's exact battle song reproduces when set.
  The true residual: `extract` doesn't auto-prefill the donor song → `battle_music` defaults to `0` (Battle Theme)
  (`build.py:3335`). Downgrade #6 to "auto-detect the donor battle song," not "silent."
- **✅ LANDED — engine walkmesh hotfixes lost on a mint (`walkmesh_hotfixes.py` + `content/walkmesh_hotfix.py`,
  kit 0.9.97).** A handful of fields rely on a hardcoded `BGI_triSetActive` keyed on the real `fldMapNo` (toggles a
  walkmesh triangle's walkable bit); a fork runs at a custom id, so the `mapNo==<real id>` guard is false and the
  hotfix never fires. The catalog classifies all ~11 fields (from `FieldMap.cs` / `DoEventCode.cs` /
  `turnOffTriManually.cs`) into two classes: **LOAD-TIME unconditional** (Gulug 2356, L.Castle 2161, I.Castle 2507) →
  **AUTO-reproduced** — `import` emits `[field] walkmesh_tri_toggles` and the build prepends `EnablePathTriangle(tri,
  state)` (opcode 0x9A == the engine's `BGI_triSetActive`) to Main_Init (the `.bgi` stays byte-verbatim); and
  **EVENT-CODE / DYNAMIC** (Daguerreo 2803 — tracks `gEventGlobal` var 761060 — Treno 900, Dali 450, Fossil Roo 1421,
  1753/1606/1900/1455) which key on runtime position/sid/story-var state, so they're **flagged** by `fork-report`
  ("Walkmesh fix: lost on a mint → fork in-place") rather than auto-applied. Refines #14's "verbatim is the answer":
  even a verbatim fork at a remapped id loses these; the load-time subset is now reproduced, the dynamic ones steer
  to fork-in-place. *(In-game: confirm a fork of Gulug 2356 / L.Castle 2161 keeps the blocked tris.)*
- **Mognet/Chocobo-Paradise world-map alternate-form STATE (bits 815/814) is BROUGHT-IN** — `WorldConfiguration.cs`
  `UsePlaceAlternateForm` is a pure `gEventGlobal` byte read (NOT id-gated), so `[startup] flags=[{flag=815}]`
  reproduces it; only the achievement-WRITE paths (`DigUpKupo fldMapNo==1421`, ATE80) are id-blocked.

## Docs to refresh (flagged by the audit)

- `project_ff9_object_carry.md` — stale test counts (cites 628/726; current baseline **765**); save-point
  synthesis IS landed (it's in the P6 director-graft phase, not unstarted).
- `docs/OBJECT_CARRY.md` §7 / `content/prop.py` comment — "save-moogle (field 300, entry 5)" is wrong: field
  300 entry 5 is a type-1 region; shown moogle is entry 9 (Mene). Hidden-in-cask is field 122 entries 5–10.
- `project_ff9_camera_math.md` — trim the legacy per-pitch `sx/sy` (0.926/0.889) prose; the only live model is
  `frame="world"` (org=0, no offset) + exact scale-1 `to_canvas`.
- `project_ff9_import_fidelity.md` — accurate on the remaining gaps; refresh the "LARGELY DONE" note to name
  **flag-preset** and **per-door spawn** as the two explicit blockers.
- `project_ff9_encounters.md` — battle-scene BGM metadata gap still open; add a "still open 2026-06-11" stamp.
- `CLAUDE.md` §5/§10 — once `[startup]` presets land, add a story-flag-preset line (today neither mentions
  presets or per-door arrival as known fidelity gaps).
