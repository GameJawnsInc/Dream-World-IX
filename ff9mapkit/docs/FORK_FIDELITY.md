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

| # | Gap | Sev | Diff | Graft lane | Status |
|---|-----|-----|------|:---:|-----------|
| 1 | ~~**Story-flag / scenario presets** — a fork boots at scenario-zero~~ | **blocker** | medium | no | ✅ **LANDED** — the `[startup]` block (boot in the right beat). |
| 2 | ~~Story-branch **doors** collapsed (`if(flag){Field(A)}else{Field(B)}`)~~ | major | medium | no | ✅ **LANDED + IN-GAME PROVEN** — gated co-zone doors flagged + carried verbatim (see below). |
| 3 | ~~Scenario-counter doesn't advance on exit → chaining forks never progresses the story~~ | major | medium | no | ✅ **LANDED** — `[[gateway]]` `set_scenario` / `set_flags` on walk-out. |
| 4 | ~~**BG-borrow black-screens area<10** (Alexandria area1, Cargo Ship area0)~~ | **blocker** | easy | no | ✅ **LANDED** — `import` auto-routes area<10 to `--native` (in-game proven). |
| 5 | ~~Talkable-stub / dangling-player-tag **softlock / wrong-text on a plain (no-flag) import**~~ | major | medium | no | ✅ **LANDED** — build-blocking dangling-tag error + un-carried-text lint warn. |
| 6 | Battle-scene BGM metadata not wired (minted scene plays silent) | major | medium | no | OPEN — extract donor scene's battle song id → emit `BtlEncountBgmMetaData.txt` at build (battle/ + BattlePatch; no field graft). |
| 7 | ~~Large scrolling field unverified in real gameplay (math implemented + unit-tested only)~~ | minor | easy | no | ✅ **VERIFIED IN-GAME** — wide Alexandria Main St (3000) scrolls 1:1. |
| 8 | BG-borrow `.bgx` tile seams (bilinear path; edge-bleed exists only on the editable path) | major | medium | no | OPEN (mitigated) — steer faithful forks to `--native` (seam-free); optionally port edge-bleed into the `.bgx` writer. |
| 9 | ~~Per-door spawn arrival — one spawn regardless of entrance~~ | major | hard | was yes | ✅ **LANDED + IN-GAME PROVEN** — Arrival diagnostic + real-arrival default spawn (see below). |
| 10 | Field-entry cutscene on a fork | major | **mostly SOLVED** | no | ✅ **Premise corrected, covered both ways** — `--verbatim` carries the real cutscene; `[[on_entry]]` re-authors one (see below). |
| 11 | Non-tag-3 / choice/menu window carry — carried NPCs' choice prompts + event windows still point at donor TXIDs | major | medium | partly | OPEN (mostly covered + lint-warned) — residual = 2 niche fields' `[[gateway_carry]]` windows (352, 552); use `--verbatim`. |
| 12 | Non-Zidane player donors (~8%, Garnet/Steiner rig clip-id mismatch) | major | hard | **yes** | OPEN — clip-id remap table per donor rig, or carry the donor party-member as the fork player. **Defer** (player.py). |
| 13 | Per-fork battle-background override (scene_id maps to BBG globally) | major | hard | no | OPEN (low priority) — only when minting a scene that reuses vanilla gameplay but a custom BBG; battle-pillar enhancement. |
| 14 | ~~Make a forked field's render-only NPCs interactive (talk-handler graft closure)~~ | major | — | **was yes** | ✗ **CLOSED — PROVEN INFEASIBLE** — `--verbatim` is the answer; `fork-report --explain` reads the quest (see below). |

**#2 — gated story-branch doors (LANDED + in-game proven).** The import flags stacked story-branch doors (>1 distinct
dest at one zone; ~43 real fields) with a note + `requires_flag` stub per branch + a count/warning, and `lint_logic` warns
on ungated co-zone gateways; gating is proven end-to-end (`requires_flag`→`gate_flag`). **#2b:** a real `if(flag)` door is a
complex multi-flag state machine, not a simple gate, so it is carried **VERBATIM** — `scan_gateway_entries` classifies it, the
import emits a `[[gateway_carry]]` block + `.gatewayN.bin` sidecar, and `graft_gateway_entry` grafts the whole entry +
retargets its `Field()` ids (its GLOB conditions then read the `[startup]` story state). A forked Dali Inn gated door stays
**closed at scenario-zero** (reads GLOB flags 2064/2073/2078). 40 fields have them; **35/~50 gated entries are self-contained
(carried)**, 15 reference other entries (left as ungated seams + a warning — need the object-carry ref machinery).

**#9 — per-door arrival (LANDED + in-game proven).** `eventscan.scan_player_arrivals` decodes the real per-entrance arrival
table; `fork-report` gains an **Arrival** line flagging fields with >1 spawn point, and `extract_field` defaults the synth
`[player] spawn` to the donor's REAL main arrival (Dali fork moved `(83,209)`→ real entrance `(439,-122)`). A synth fork can't
reconstruct the per-DOOR table (its gateways are retargeted) — that fidelity is `--verbatim`'s job, and the Arrival line steers there.

**#10 — field-entry cutscene (premise corrected).** The old "entry cutscenes fire from a C# `NarrowMapList` table" framing was
**wrong** (`NarrowMapList` is the camera-WIDTH / widescreen table, zero cutscene logic); a field's entry cutscene runs from its
own `.eb`. So `--verbatim` carries the real cutscene (proven — Vivi/field 100's opening), and `[[on_entry]]`
(`content/onentry.py`) re-authors a gated, once entry beat for a synth fork. The only residual is cosmetic + keyed on the
donor's real id (widescreen `NarrowMapList.MapWidth` defaults to 500 for a custom id; a few per-actor anim tweaks; field-70 FMV).

**#14 — render-only NPC talk-handler graft (closed, proven infeasible 2026-06-12).** A census of all 675 fields under maximal
grafting found **55 NPCs / 36 fields lose their tag-3 talk handler, and 0 are blocked only by a graftable gesture** — a dropped
tag-3 is the field's quest logic, inseparable from its text/economy/geometry. `--verbatim` already carries it byte-for-byte
(the standing answer); shipped instead: `fork-report --explain` decodes any field's NPC routines to readable English.

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
>
> **Now machine-queryable per field** (kit 0.9.98, +v2 0.10.0): `ff9mapkit fork-report <id>` operationalizes the
> taxonomy so you don't consult the table by hand — an **Area title** line (the donor-identity card you DROP on a
> reuse / keep on `--verbatim`) and a **Lost on mint** section (the engine behaviors keyed on the real `fldMapNo`
> a fork loses: walkmesh hotfix, narrow-map letterbox, Chocobo dig HUD, intro FMV, **ATE achievement** — each
> noted auto-reproduced vs fork-in-place). Backed by `idgated.py` (+ the baked `_narrowmap_data.py` widths) and
> `walkmesh_hotfixes.py`. ★ **v2 (kit 0.10.0):** the **ATE achievement** is now per-field — the *ATE80* trophy is
> keyed on `fldLocNo`, and `fldLocNo == eventIDToMESID[fldMapNo]` (`HonoluluFieldMain.cs:19`), i.e. the field's
> registered MES id, so `idgated` resolves it from the baked `EVENT_ID_TO_MES` and flags the loss when that
> location is in `EMinigame.MappingATEID` (the ATE still plays; only the trophy bookkeeping is id-bound). And the
> **Verdict** line now SYNTHESIZES across every axis: the recommended fork MODE (`--verbatim` when the field has
> story-gated cast/logic / a non-Zidane player / party or item grants / per-door arrival — plus a `[startup]`
> beat; else `--native`) and a lost-on-mint fork-in-place steer. Plus an **Entry settle** line (coarse flag): a
> SCROLLING field's smooth-cam eases onto the spawn on warp-in, and a SYNTH fork reveals immediately so the ease
> is VISIBLE (worst on an F6/hard warp) — so it flags "scrolling → a `--native`/BG-borrow fork may drift; add
> `[camera] entry_settle`; `--verbatim` masks it." (A fixed-camera field shows no line.) The exact frame count is
> still a playtest tune; the flag answers *whether* you need it.

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
- **Perspective movement arcs are NOT a genuine residual** (corrected 2026-06-15 — an earlier draft called ladder
  climb-arcs / jump parabolas / the save-Moogle pop-out "copy-only, never generated from scratch"; that was wrong).
  These arcs are authored in **world coordinates**, and the engine projects world→screen through the fixed camera
  automatically (the solved scale-1 camera math) — so the "perspective" is **free**, there is nothing to hand-tune in
  screen space (`climb_arc_body`: *"the engine projects every world rung through the camera, so the climb traces the
  painted ledge for free"*). The real state per mechanic:
    - **Ladders — generated from scratch TODAY.** `navigable_climb_body` / `inject_navigable_ladder`
      (`content/ladder.py`) derive FF9's real navigable climb (line equation + height band + held-d-pad loop +
      mount/dismount) from just the **two world endpoints** — *"any new painted vine just supplies its own two
      points (read off the paint guide, same as walkmesh placement)."* Decoded byte-for-byte from field 706
      (Gizamaluke vine) and reproduces 706's loop verbatim for 706's endpoints. NOT copy-only.
    - **Jumps + save-Moogle pop-out — copy-only TODAY, but unbuilt-not-impossible.** `inject_jump` wants verbatim
      `jump_bytes` because no from-scratch `navigable_jump_body(from, to)` is wired yet; a jump is a one-shot
      `SetupJump(x,y,z,steps) + Jump` from two world points, so the generator is tractable (the deprecated
      `climb_arc_body` already interpolates `SetupJump/Jump` hops from two endpoints).
    - **The single genuine-eyeball residual: the off-floor height** (a jump's apex, a ladder's top, the moogle's
      pop height). The floor walkmesh pins depth *at floor level*, but these mechanics leave the floor plane, so
      that one number is read off the painting + confirmed in the playtest loop (Hard-Constraint §2). An **authoring
      task** like placing the walkmesh or painting the BG — NOT an engine wall and NOT an asset-absence impossibility
      (contrast cross-rig gesture remap below, where the clips literally do not exist).

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

**One** residual is **not engine-fixable at all** (no DLL helps): **cross-rig gesture remap** — 0/15 of a Vivi
cutscene's clips have a Steiner equivalent in the global `AnimationDB`, and a DLL can't invent artist-authored
clips. The faithful answer is `--verbatim` with the original rig. *(An earlier draft also listed "from-scratch
perspective arcs/pop-out" here — that was WRONG and is corrected in "The governing principle" above: those arcs are
world-space + engine-projected, ladders already generate from two endpoints, and jumps/pop-out are an unbuilt
generator rather than an impossibility.)*

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
  ★ **IN-GAME PROVEN by A/B (2026-06-14):** two native Mognet Central (3100) forks — id 30006 *without* the hide shows
  the static "Mognet Central" card (the leak is real for native forks), id 30005 *with* the auto-emitted hide shows
  no card (the suppression works).
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
  206). **✅ FIXED (kit 0.9.99):** the `_field_load_inject` docstring + BuildError message + `content/party.py`'s
  `inject_party` docstring no longer claim prepending fails on a jump-table donor or cite "field 100" — they now say
  a prepend is always safe (the levers all prepend / append-activate) and the guard is a *defensive* net for a
  hypothetical future mid-function field-load insert.
- **Battle BGM (#6) — auto-detection LANDED for random encounters; the real residual is SCRIPTED battles.**
  `import` now auto-detects the donor's battle song (`battle_bgm.py` reads the install's `BtlEncountBgmMetaData.txt`
  `(field, scene) -> song` map LIVE, provenance-clean) and prefills `[encounter] battle_music`; the build reproduces
  it via the scene-keyed `Music:` BattlePatch line (`FF9SndMetaData.BtlBgmPatcherMapper`, which wins over the lost
  `(fldMapNo, scene)` lookup a mint can't satisfy). ★ **EMPIRICAL FINDING (kit 0.9.99):** every one of the game's
  ~101 *random*-encounter fields maps to song `0` (the standard Battle Theme), so the prefill is correctness /
  future-proofing, not a behavior change for existing forks. The SPECIAL battle themes (e.g. song `35`) belong to
  ~30 *scripted*-battle fields (a `Battle(0x2A)` op, scene at `imm(1)`, NO `SetRandomBattles`) — a `--verbatim` fork
  carries the `Battle` op but the kit emits no `Music:` line, so the boss theme is lost on the custom `fldMapNo`.
  ★ **✅ CLOSED (kit 0.9.101): the scripted-battle carry.** `eventscan.scan_battle_scenes` decodes the donor's
  `Battle(0x2A)`/`BattleEx(0x8C)` scenes (scene = `btlId & 0x7FFF`, engine `DoEventCode.cs:962`); `import --verbatim`
  looks each up in the BGM map and auto-emits `[[battle_bgm]] scene=N song=M` for the NON-zero (boss/special)
  songs; the build emits a scene-keyed `Music:` line per pair (deduped — `BtlBgmPatcherMapper` is scene-keyed +
  mod-global). Song 0 is skipped (= the build default + would override the scene globally for nothing), so random
  encounters (all song 0) add no lines. ★ **IN-GAME PROVEN (2026-06-17):** a `--verbatim` fork of `EVT_GIZ_BOSS`
  (field 707, Gizamaluke / Sacred Room) → `[[battle_bgm]] scene=326 song=35` → `Battle: 326 / Music: 35`; deployed
  to slot 30050 (`FF9CustomMap-bt`), the Gizamaluke fight plays the **boss battle theme** (song 35), not the normal
  battle theme — the user confirmed by ear. (Offline-proven first on `import 656 --verbatim` = KUINA_KM_SWP/Marsh,
  scene 330 → 35.) **#6 fully closed (random prefill + scripted carry), in-game proven.**
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
  to fork-in-place. ★ **IN-GAME PROVEN by A/B (2026-06-14, Gulug 2356):** two identical native forks — id 30003
  *with* the toggle, id 30004 *without* — teleporting to the deactivated-patch EDGE (−543,1667), ~120u from the
  chest (beyond its collision reach), is **STUCK with the toggle and FREE without it**. So the prepended
  `EnablePathTriangle` is what blocks that floor, not the co-located treasure-chest prop (entry 5,
  `GEO_ACC_F0_TBX` @ (−426,1664)); the patch extends ~120u around the chest, so it blocks *more* than the chest's
  collision — the hotfix is not redundant. (Lessons learned the hard way: the engine's "Red Dragon bursting
  through wall" comment names the *room*, not the tris' job; a co-located created object's `CreateObject` registers
  walkmesh collision (`BGI_charSetActive`) and can mask the toggle at the patch *center* — isolate it at the edge,
  and don't claim "proven" without the A/B.)
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
