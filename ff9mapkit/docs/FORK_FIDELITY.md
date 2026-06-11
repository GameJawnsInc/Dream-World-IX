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
  flag presets, a single heuristic spawn regardless of which door you entered, and **no field-entry cutscene**
  (those fire from the C# `NarrowMapList` table, not the `.eb`).

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
| 7 | Large scrolling field unverified in real gameplay (math implemented + unit-tested only) | minor | easy | no | Deploy one wide scrolling fork to the test slot, ask the human to playtest — pure verification |
| 8 | BG-borrow `.bgx` tile seams (bilinear path; edge-bleed exists only on the editable path) | major | medium | no | Steer faithful forks to `--native` (seam-free); optionally port edge-bleed into the `.bgx` writer |
| 9 | Per-door spawn arrival — one spawn regardless of entrance | major | hard | **yes** | Reconstruct a `if(FieldEntrance==N)` arrival table in player-init (`scan_gateways` already recovers each exit's entrance id). **Defer**; interim: emit discovered entrance ids as commented `[[spawn]]` stubs |
| 10 | Field-entry cutscene auto-fire (C# `NarrowMapList`, not the `.eb`) | major | needs-engine-fork | no | **✅ v1 LANDED — the `[[on_entry]]` block** (`content/onentry.py`): fire a narration `message` and/or story-state writes (`set_scenario`/`set_flags`) on field load, **once**, GATED by `requires_scenario` (ScenarioCounter `== N`) / `requires_flag` — the gating neither `[startup]` nor `[cutscene]` could express. Armed by `InitCode` in Main_Init (no movement gate — runs before control); the gate sits *outside* the once-block so it fires on the first entry that matches. Byte-identical when absent; 14 tests. The declarative re-authoring of a lost entry cutscene. True auto-fire from the C# table still needs a dev-engine `NarrowMapList` patch (research) |
| 11 | Non-tag-3 / choice/menu window carry — carried NPCs' choice prompts + event windows still point at donor TXIDs | major | medium | **yes** | Extend `collect_carry` to all kept funcs' windows + choice txids. **Defer** behind the graft session; lint-warn meanwhile |
| 12 | Non-Zidane player donors (~8%, Garnet/Steiner rig clip-id mismatch) | major | hard | **yes** | Clip-id remap table per donor rig, or carry the donor party-member as the fork player. **Defer** (player.py) |
| 13 | Per-fork battle-background override (scene_id maps to BBG globally) | major | hard | no | Only when minting a scene that reuses vanilla gameplay but a custom BBG; battle-pillar enhancement, low priority |

## The next step

**Landed:** #1 (`[startup]` presets), #2 (gated story-branch doors), #3 (`[[gateway]]` on-exit advance —
`set_scenario`/`set_flags`), #4 (auto-`--native` for area<10 — a plain `import` of an early-game field
now works, in-game proven), and **#10 v1** (`[[on_entry]]` — gated, once field-load beats: the declarative
re-authoring of a lost `NarrowMapList` entry cutscene), plus the verbatim save-moogle carry (P1–P6.1) and the
verbatim `.eb`+`.mes` fork (`import --verbatim`) — so the graft lane is FREE.

The next levers, biggest narrative-state leverage first (the weak axis — making a fork *behave* as its beat):
- **#5 — softlock lint on a plain import** (medium): a plain fork of a field with a talkable/interactive
  carried object can softlock; the classifier exists, the build-side lint wiring doesn't.
- **#9 — per-door spawn** (hard, graft lane now free): reconstruct the entrance→spawn arrival table so a fork
  spawns where you entered, not at one fixed point.

Extraction of *which* flags a real prior field set on exit remains a separate, later, eventscan-touching task —
the author asserts the beat for now (they have the game knowledge — cf. `feedback_trust_user_game_knowledge`).

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
