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
- **Object/NPC carry — ~70% and advancing.** Verbatim `.eb`-entry graft + player-func graft + per-language
  text carry; the save-moogle director graft (P6) is mid-flight in the concurrent session.
- **Narrative state — the weak axis.** A fork boots with a **zero `gEventGlobal`**, no ScenarioCounter, no
  flag presets, a single heuristic spawn regardless of which door you entered, and **no field-entry cutscene**
  (those fire from the C# `NarrowMapList` table, not the `.eb`).

**Honest grade: a high-fidelity diorama of a field, not yet a faithful slice of the playthrough.** You can
fork a story room and walk around it faithfully; you cannot yet fork it and have it *behave* as that story
beat.

## Play a fork today

`import --native --graft-player-funcs --carry-text`, warp in via F6. **You get:** correct background art with
seam-free per-tile occlusion + correct 3D-model lighting; the byte-exact (multi-floor) walkmesh; the right
camera + control direction; working ladders/jumps; the field's random encounters with the right BGM and a
clean after-battle return; carried NPCs/props that render byte-identically, speak their real per-language
lines, and respond to push/talk. **You don't get:** the field plays in its **scenario-zero state** — every
story-gated NPC/door/event defaults to the not-yet-happened branch (hidden areas may be exposed, story NPCs
absent); you **spawn at one fixed point** no matter which gateway you arrived through; any field-entry
**cutscene never fires**; exit gateways warp correctly but **don't advance the ScenarioCounter**, so chaining
forks won't progress the story.

Note: faithful carry is **opt-in** (the three flags above). A plain `import` is BG-borrow with no
object/text/func carry; `import-chain` text carry needs a live install (offline `.mes` read not yet wired).

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
`content/savepoint.py` / the `extract.py` graft code, **where the concurrent save-moogle session is
mid-flight** — those are **deferred** until it lands. The orthogonal items are workable now.

| # | Gap | Sev | Diff | Graft lane | Direction |
|---|-----|-----|------|:---:|-----------|
| 1 | **Story-flag / scenario presets** — a fork boots at scenario-zero, so every story-gated NPC/door/event takes the wrong branch | **blocker** | medium | no | **`[startup]` preset block** wired into Main_Init via existing `content/event.set_flag` + `inject_events` (author asserts the beat; no extraction for v1) |
| 2 | Story-gated doors/content shown unconditionally (scanner collapses `if(flag){A}else{B}`) | major | medium | no | Once (1) exists: surface a lint when conditional `Field()` arms were collapsed; let the author attach `requires_flag` to emitted `[[gateway]]` stubs (`gateway.inject_gateway` already gates) |
| 3 | Scenario-counter doesn't advance on exit → chaining forks never progresses the story | major | medium | no | `[[on_exit]]` / gateway-side `set_flag`/`set_scenario` injected into the gateway region before `Field()` (reuses `content/event.set_flag`) |
| 4 | **BG-borrow black-screens area<10** (Alexandria area1, Cargo Ship area0) | **blocker** | easy | no | Auto-select `--native` for area<10 instead of raising (native already remaps ≥10, seam-free + lighting); document BG-borrow as the ≥10 fast path. Tiny cli/build change |
| 5 | Talkable-stub / dangling-player-tag **softlock on a plain (no-flag) import** — worst case is a softlock on a user's first import | major | medium | partial | Wire `lint_all` to flag (a) carried talkable objects with un-carried text and (b) carried interactive tags referencing absent player tags. The classifier is in eventscan (graft lane); the **lint wiring is build-side (orthogonal)** — do that now |
| 6 | Battle-scene BGM metadata not wired (minted scene plays silent) | major | medium | no | Extract donor scene's battle song id → emit `BtlEncountBgmMetaData.txt` at build (battle/ + BattlePatch; no field graft) |
| 7 | Large scrolling field unverified in real gameplay (math implemented + unit-tested only) | minor | easy | no | Deploy one wide scrolling fork to the test slot, ask the human to playtest — pure verification |
| 8 | BG-borrow `.bgx` tile seams (bilinear path; edge-bleed exists only on the editable path) | major | medium | no | Steer faithful forks to `--native` (seam-free); optionally port edge-bleed into the `.bgx` writer |
| 9 | Per-door spawn arrival — one spawn regardless of entrance | major | hard | **yes** | Reconstruct a `if(FieldEntrance==N)` arrival table in player-init (`scan_gateways` already recovers each exit's entrance id). **Defer**; interim: emit discovered entrance ids as commented `[[spawn]]` stubs |
| 10 | Field-entry cutscene auto-fire (C# `NarrowMapList`, not the `.eb`) | major | needs-engine-fork | no | v1: document + offer a manual fire-on-entry hook (`InitCode` in Main_Init). True fidelity: a dev-engine `NarrowMapList` patch registering custom ids → cutscene metadata (research) |
| 11 | Non-tag-3 / choice/menu window carry — carried NPCs' choice prompts + event windows still point at donor TXIDs | major | medium | **yes** | Extend `collect_carry` to all kept funcs' windows + choice txids. **Defer** behind the graft session; lint-warn meanwhile |
| 12 | Non-Zidane player donors (~8%, Garnet/Steiner rig clip-id mismatch) | major | hard | **yes** | Clip-id remap table per donor rig, or carry the donor party-member as the fork player. **Defer** (player.py) |
| 13 | Per-fork battle-background override (scene_id maps to BBG globally) | major | hard | no | Only when minting a scene that reuses vanilla gameplay but a custom BBG; battle-pillar enhancement, low priority |

## The recommended next step (orthogonal to the graft lane)

**Ship the `[startup]` story-flag preset authoring block (worklist #1).** It is the single highest-leverage
fidelity lever — it directly unfreezes the scenario-zero boot state that breaks every story-gated NPC / door /
event — and it lives entirely in the **authoring half**: a declarative `field.toml` `[startup]` /
`[[flag_preset]]` block wired into Main_Init at build time, on top of the **existing**
`content/event.set_flag` + `inject_events` arming-entry primitives. It touches **`build.py` + `content/event.py`
only** — never `object.py` / `player.py` / `eventscan.py` / `savepoint.py` / `extract.py`-graft, so **zero
contention** with the concurrent save-moogle session.

Sketch: `[startup] flags = [{flag=8520, value=1}, ...]` (+ optional scenario word) → `build_field` injects one
Main_Init arming entry that runs the `set_flag` bodies once unconditionally → lint against the reserved-flag
band (`lint_flag_bands` exists) → authored builds stay byte-identical when `[startup]` is absent (hut golden
tripwire). This makes "fork a story field and have it boot in the right beat" possible for the first time.

Extraction of *which* flags a real prior field set on exit is a separate, later, eventscan-touching task — keep
it out of v1; let the author assert the beat (they have the game knowledge — cf. `feedback_trust_user_game_knowledge`).

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
