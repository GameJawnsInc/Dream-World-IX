# Changelog

All notable changes to `ff9mapkit`. Format follows [Keep a Changelog](https://keepachangelog.com);
versioning is [SemVer](https://semver.org). The Blender add-on has its own version, kept in lockstep.

## [Unreleased]

### Added — `import --swap-player <char>`: walk as a different existing character (Tier A, productionized)
- Fork a field and **swap who you walk as** to any existing playable — `import <field> --swap-player steiner`
  (zidane/vivi/steiner/garnet/freya/quina/eiko/amarant; aliases dagger, salamander). It patches the player
  entry's Init `SetModel` + the movement anim ids (idle/walk/run/turn-L/turn-R/idle-break) to that character's
  rig — a same-length, width-aware byte patch (`playerswap.swap_player`). Implies `--verbatim` (it needs the
  donor's real player entry in the shipped `.eb`); **party/menu state is unchanged** (field control and party
  roster are decoupled). The character table is real data, EXTRACTED from each character's home field (model
  id + eye-height + movement clips). ★ The productionized form of the **in-game-proven Tier-A probe** (walk as
  Steiner in a Zidane field; memory `project-ff9-pc-party-system`). New module `ff9mapkit/playerswap.py`
  (read-only transform) + the `--swap-player` flag wired through `cli.py` (forces verbatim, applies the swap to
  the shipped sidecar `.eb`). `.eb`-only, no DLL. ★ CAVEAT (warned): the swap repoints only the 6 MOVEMENT
  clips, so it's CLEAN on a free-roam field but on a CUTSCENE field the player's scripted GESTURES
  (`RunAnimation`, rig-specific) glitch on the new model — `playerswap.scripted_gesture_ops` counts them (Vivi
  field 100 = 15) and the CLI prints a `WARN`. For STORY fidelity (be a character *through* the story), use a
  verbatim fork at the right beat + the right party, not a model swap. 6 offline tests
  (`tests/test_playerswap.py`) — incl. a Vivi field→Steiner round-trip, a "swap to self is identity" check that
  proves the baked table matches the real game, and the gesture-warning detector. kit 0.9.26. (The complementary
  party-MEMBERSHIP authoring — `B_PARTYADD` etc. — is a declarative block in story_flags' lane; here only the
  fork-transform half landed.)

### Fixed — Story State console: B-slot dropdown + Memoria extra-save authority
- The Diff tab's **"B slot" dropdown couldn't be clicked** — it was created with no menu items and only
  populated when a *second* file loaded. It now fills from the loaded save's slots (or the B file's) on every load.
- **Memoria per-slot extra-save is now treated as authoritative** (the likely cause of "I set a flag but in-game
  it's still 0"): Memoria writes a per-slot `SavedData_ww_Memoria_*.dat` holding the gEventGlobal it RESTORES
  from on load, so the encrypted main block can be stale. `save.inspect` now reads the extra when present (and
  tags the slot) so the console shows what the game *actually loads*; `save.apply_story_edit` re-reads the extra
  after patching to **verify** the write took (`extra_patched`), and the GUI's Apply reports `[OK]` / `[WARN]`
  so an edit that won't show in-game is no longer silent. 3 save tests; kit 0.9.24.

### Added — Story State GUI console (inspect / diff / EDIT a save's story state)
- A new app `apps/ff9_storystate.pyw` (`StoryStateApp`) surfaces the story-flag pillar's save verbs in one
  window — the save-side companion to the Info Hub's story-flag *registry*: **Inspect** (each populated
  slot's ScenarioCounter→beat + story bits by named region, via `save.inspect` + `flags.render_report`),
  **Diff** (load a second save / slot → the A→B delta, `flags.diff_reports`), and **Edit** (set the
  ScenarioCounter / set+clear story bits → write back). Editing is **backup-guarded** (a `.bak` first) and
  **reserved-region-refused**, sharing the CLI's guards via a new `save.apply_story_edit` convenience
  (the in-place edit+backup+write+extra-patch path as one call, with a `dry_run` for the Preview;
  `edit_story_state` stays the shared core). Wired into the launcher + a Campaign-Editor tab. 3 save tests
  (`tests/test_save.py`) + a headless `--smoke` (inspect/diff crypto-free; edit-preview when pycryptodome is
  present). kit 0.9.23.

### Corrected — fork-fidelity #10 premise (entry cutscenes are `.eb`-borne, not a C# `NarrowMapList` trigger)
- A load-bearing belief in the docs/memory was **wrong** and is now corrected (verified directly in the Memoria
  source): `NarrowMapList.cs` is the engine's per-field **camera-WIDTH / widescreen** table (PSX screen widths,
  narrow-vs-wide cam, crop margins) with **zero** cutscene logic — its only callers are `FieldMap`/`PSXCameraAspect`.
  A field's **entry cutscene runs from its own `.eb`** (entry-0 + actor sequences), so a `--verbatim` fork carries
  it (in-game proven: Vivi/field 100's opening), and `[[on_entry]]` re-authors one for a synthesize fork. The
  "needs a dev-engine `NarrowMapList` patch" framing of #10 was a phantom; the only genuine engine-side residual is
  **cosmetic and keyed on the donor's real id** — widescreen camera-width (`MapWidth` defaults to 500 for a custom
  id), a few per-actor anim tweaks (`FieldMapActor.cs`), and FMV playback (field 70). Docs/comments-only correction
  across CLAUDE.md, FORK_FIDELITY.md, FORMAT.md, FEATURES.md, CAMPAIGN_IMPORT.md, `content/onentry.py`, `build.py`,
  the tests, and the project memory (no code-behaviour change).

### Added — `fork-report` Dialogue axis (the #5 text gap, previewed before you fork)
- `fork-report` now reports a **Dialogue** axis (orthogonal to the interaction-safety axis): how many carried
  NPCs **speak** (a tag-3 talk window) and how many lines — e.g. Daguerreo 2F "6 NPC(s) speak 36 line(s)".
  Their words render **wrong** unless the fork carries the text, so the line says ship with `--carry-text`
  (or `--verbatim`), pointing at the build-side lint (FORK_FIDELITY.md #5) as a *before-you-fork* preview.
  Read-only — reuses `dialogue.scan_dialogue` (the analysis-layer `.eb` reader), filtered to the carried
  objects' talk handlers; no scanner logic of its own. Validated on real fields (Daguerreo 6/36, Dali Inn
  1/8). 2 offline tests + an install-gated assertion (`tests/test_forkreport.py`); kit 0.9.21.

### Added — `fork-report` computes the REAL controlled PC in a multi-PC non-Zidane fork
- The control-bind mechanism is now **engine-sourced + in-game proven** (a 3-lens workflow over the Memoria
  C# + the donor bytes + a verbatim playtest). When a field defines >1 `DefinePlayerCharacter` (0x2C), the
  engine binds player control to the entry whose 0x2C **executes LAST** at load (`controlUID = gExec.uid`,
  last-write-wins, `EventEngine.DoEventCode.cs`); entries run their Init in **InitObject (0x09) order**, so the
  binder is the entry whose tag-0 Init runs a 0x2C **unconditionally** and is InitObject'd **latest**. It is
  **party-leader-independent** for fixed-SID character fields. ★ **IN-GAME PROVEN** on a verbatim fork of the
  Treno Dagger+Steiner room (`evt_treno1_tr_qhm_0`, shipped over the FBG scene): you control **Garnet** (entry
  9, last-executed 0x2C) — NOT Steiner (entry 10, spawned first), NOT Zidane (party leader); free-roam, and the
  bind persists across gateways. The party MENU still shows Zidane — `controlUID` is decoupled from party state.
- So `fork-report`'s **Player** axis now reports the *real* controlled character (`controlled_player` = last
  unconditional 0x2C by InitObject order) for a non-Zidane multi-PC field — e.g. `controls Eiko of [Garnet,
  Eiko]` — instead of the old `pents[0]` guess (the FIRST entry, which mispredicts: ac_alt binds Eiko not the
  first-entry Garnet). It's scoped to the non-Zidane lane (where it's validated); a **Zidane-present** multi-PC
  field keeps the conservative "likely Zidane party-leader" hedge (control there can route through a party slot
  to the live leader, which this doesn't model — the Cargo Ship would mispredict). Confidence is hedged (`?`)
  when the binder is multi-spawned or only gated. Read-only (`forkreport.py` only). 2 tests; memory
  `project-ff9-non-zidane-donors`. (No reliable offline free-roam-vs-cutscene flag exists — player-LOOP length
  doesn't separate them: Vivi-100/Dali-Inn free-roam at ploop 254/272, the ac_alt *cutscene* at 50 — so none
  was added; the first multi-PC probe burned a playtest on the ac_alt coronation cutscene.) kit 0.9.22.

### Added — `fork-report` is now PLAYER-CHARACTER aware (non-Zidane donors)
- A field's controlled character isn't always Zidane (Vivi/Steiner/Garnet/Eiko/Freya/Amarant solo sequences).
  A census of all 818 field `.eb` (one events-bundle pass; `eventscan.resolve_player_entries` + `_player_model`)
  found **178 non-Zidane-primary** fields, ~80 *truly playable as a party member*. `fork-report` now reports a
  **Player** axis: who you play as, single- vs **multi-PC** (`[MULTI-PC]`), and — for a non-Zidane controlled
  character — switches the suggested recipe to **`--verbatim`** (which ships the donor player rig + anim packs
  + the field's own party/cutscene setup whole; the `--graft-player-funcs` path *drops* a non-Zidane player's
  funcs as `"model"` graft-safety — another rig's clip ids). The multi-PC inference is conservative: the FIRST
  `DefinePlayerCharacter` is NOT reliably who you control (the Cargo Ship lists Blank first; you play Zidane),
  so a single-PC field is crowned confidently while a multi-PC field is only called non-Zidane-controlled when
  **no Zidane is among the PCs** (the Treno Dagger/Steiner split) — else it's flagged "likely the Zidane
  party-leader; co-actors are the rest". **★ In-game proven (Vivi / Alexandria street, field 100):** a
  `import --verbatim` fork plays IDENTICALLY — Vivi renders + animates + is in the party menu, and the field's
  real ticket-girl opening cutscene plays (so that intro lives in the `.eb` entry-0, not a C# `NarrowMapList`
  table — the verbatim fork carries it). So a clean single-PC non-Zidane field already forks faithfully with
  ZERO new code; the frontier is the multi-PC / scenario-gated-player bind. Read-only (`forkreport.py` only),
  reuses the existing scanners. 2 tests (`tests/test_forkreport.py`); memory `project-ff9-non-zidane-donors`.
  kit 0.9.19.

### Added — softlock / wrong-text lint for a plain (no-carry) import (FORK_FIDELITY.md #5)
- A plain `import` (no carry flags) carries a real field's objects but **not** their player funcs or dialogue
  text, which can softlock or mis-render in-game. Both halves are now caught **build-side, offline**:
  - **(b) dangling player tag = the softlock** was already a build-blocking `validate()` error — a carried
    `[[object]]` that `RunScript`s the player at an un-grafted tag (`_entry_player_call_tags`).
  - **(a) un-carried talkable text = wrong/missing dialogue** is the new piece: `lint_logic` decodes each
    carried object's talk windows (`_entry_window_txids` — mirrors the player-call decoder) and warns when a
    shown donor txid isn't in the `[carry_text]` plan (\"import with --carry-text, or author the line\").
  Validated against real imports — a plain `--native` Daguerreo fork flags all 5 talkable NPCs, a
  `--carry-text` fork is silent (no false positive), props are skipped. Reads only stable build-side
  representations (the `[[object]]` bins + the carry plan); orthogonal to the eventscan classifier.
  5 tests (`tests/test_carry_text_lint.py`); kit 0.9.20.

### Added — message-in-verbatim: an `[[on_entry]]` narration line now SHOWS in a verbatim fork
- After the convergence (`build._apply_on_entry` runs on the verbatim path), an `[[on_entry]]` gated
  state-advance already fired in a `--verbatim` fork — but the narration **message** was dropped (the donor
  `.mes` ships verbatim, with no slot for authored text). Now the authored line is **appended to the donor
  `.mes` above its max txid** (`build._verbatim_on_entry_messages`, floored at `textcarry.CARRY_BASE_TXID`
  1000 — the same append-and-resolve trick `--carry-text` uses), and the hook's `WindowSync` resolves into
  it. So a verbatim fork's on_entry beat now fires its message **and** its state-advance on top of the
  donor's real logic. `_apply_on_entry` is unchanged (its `drop_messages` param stays a general capability);
  only the verbatim branch of `build_field` now supplies the text channel, and the now-obsolete
  "message won't show in verbatim" lint warning is retired. **In-game proven** on a Dali-Inn verbatim fork
  (the appended line renders, `set_flags` advances state, the inn's own NPCs still speak their real lines).
  3 tests (`tests/test_on_entry.py`); kit 0.9.18.

### Added — deploy-time text-block SHADOW guard (`deploystack.py`)
- A field loads its dialogue by **mesID** (`text_block`), and the engine reads that `.mes` from the **first**
  mod folder in `Memoria.ini` `FolderNames` that defines `field/<mesID>.mes`. When several stacked worktree
  mod folders (`FF9CustomMap-*`) all use the kit-default block **1073**, a lower-priority folder's text is
  **shadowed** — the field renders a *higher*-priority folder's block-1073 text instead. This bit an
  `[[on_entry]]` playtest: a probe in `FF9CustomMap-sf` showed `FF9CustomMap`'s stale "Rally-ho!" rather than
  its authored line (the flags were correct; only the text was someone else's). `tools/deploy_field.py` now
  **warns at deploy time** — naming the shadowing folder and suggesting real mesIDs no higher-priority folder
  defines (e.g. "use text_block = 187"). The check is a pure, offline, tested kit function
  (`deploystack.check_text_block_shadow` / `parse_folder_names` / `shadow_warning`); deploy also accepts
  `--text-block N` (or `text_block = N` in `.ff9deploy.toml`) to pin a worktree-unique block. 8 tests
  (`tests/test_deploystack.py`). kit 0.9.16.

### Added — `[[on_entry]]`: gated, once field-load beats (FORK_FIDELITY.md #10)
- *(Premise corrected later — see "fork-fidelity #10 premise" below: a field's entry cutscene runs from its own
  `.eb`, so a verbatim fork carries it; `[[on_entry]]` re-authors one for a synthesize fork. The "C# `NarrowMapList`
  table" framing was a misread — that's the camera-width table.)* `[[on_entry]]` is the declarative re-authoring
  hook: fire a narration `message`
  and/or story-state writes (`set_scenario` / `set_flags`) the moment the player **enters** the field, **once**,
  but **only when the story state matches** (`requires_scenario` = a ScenarioCounter `== N`, and/or
  `requires_flag`). The gating is the new capability — neither `[startup]` (unconditional, every entry) nor
  `[cutscene]` (ungated, single) can say "fire this beat only at scenario N / when bit B is set". Each hook is a standalone code entry armed by an `InitCode`
  in Main_Init (the proven narration-cutscene arming, now robust for any count via the region-arming fix below),
  so it runs at field load *before* control is re-enabled (hence no movement gate); a `message` beat reuses the
  cutscene's reorder-`Wait` + `DisableMove`/`EnableMove` lock so the window shows cleanly during the entry fade.
  `content/onentry.py` + `build.py` (validate / collect_text / inject / lint) + `flags.py` (name resolution,
  read/write parity); surfaced in the dialogue viewer/editor (`collect_text_refs`). Byte-identical when absent.
  An adversarial pre-commit review (4 read-only lenses) hardened two edges: the single-field auto once-flag
  band is guarded against reaching FF9's reserved chest bitfield (a `BuildError` instead of silent save
  corruption), and `lint_logic` warns when `[[on_entry]]` coexists with a `--verbatim` fork (which ships the
  donor `.eb` as-is, bypassing the hook). 16 tests (`tests/test_on_entry.py`); 828 suite. kit 0.9.15.

### Fixed — region arming silently lost on fields with >2 regions
- `eb.edit.activate` (the Main_Init region-arming primitive) overwrites a `Wait` filler shift-free, but the
  blank/borrowed template has only **2 `Wait` fillers**; the 3rd+ region fell back to a raw `insert_bytes` at
  a **stale Main_Init position**, so the 2nd+ insertion landed in already-consumed bytecode and that region
  **silently never armed** (its trigger never fired). It bit a forked **campaign chain** (a field's 2 gateways
  consumed both fillers, so its on-entry events never fired) and would bite any content-rich fork. Fixed by
  routing the fallback through `insert_in_function` (the fpos-fixing insert, same primitive `[startup]` uses),
  so any number of regions arm correctly even on a borrowed field with a real entry-0 tag-1 function.
  Within-budget fields (≤2 regions) still hit the patch path and are **byte-identical**. New `tests/test_arming.py`
  (5 regions all arm; the `.eb` stays parseable). Surfaced by an adversarial diagnosis workflow.
- `build.lint_logic` now counts a gateway's `set_flags` and `[startup]`'s `flags` as flag **setters**, so a
  same-field "a door reveals an NPC" pattern no longer false-warns "no event sets it".

### Added — `fork-report`: preview a real field's fork fidelity (offline)
- **`ff9mapkit fork-report <field>`** (id or FBG substring) answers, before you fork, "will this field play
  faithfully?" — reading the compiled `.eb` with no game running. It reports two INDEPENDENT axes:
  **roster fidelity** (how many objects a fork carries, how many are `Field()`-warp **directors** = cutscene
  actors carried as NPCs, and whether content rotates by story beat) and **interaction fidelity** (per NPC,
  whether its talk handler ports — `clean` = fully interactive / `init_only` = render-only / `refuse` = stub).
  Plus story-gated doors, the ScenarioCounter **beats the field gates content on**, and a suggested
  `[startup] scenario` (the earliest gate) + `import` recipe. Verdict: a clean static-roster field (forks
  faithfully) vs a story-event field (a high-fidelity diorama — rotating cast / cutscene actors). Validated:
  the real Dali Weapon Shop → STORY-EVENT (1 director, 11 rotating beats Dali→Pandemonium); Daguerreo 2F →
  CLEAN static-roster. **Read-only** — reuses `eventscan.scan_objects_verbatim` (the carry `graft_safety`
  classification) + `scan_gateway_entries` + the `flags` beat table; adds no carry/scanner logic. New module
  `ff9mapkit/forkreport.py` (pure `analyze_eb` + thin id-loader, unit-tested offline against a fixture).
  Surfaced as a **Preview fidelity** button in the FFIX Import GUI (`apps/ff9_import.pyw`) — standalone and the
  Campaign Editor's Import tab — so you can read the verdict before importing.
  (`docs/FORK_REPORT.md`; `docs/FORK_FIDELITY.md` — the north star is "fork a real field → does it play identically?")

### Added — `[[gateway]]` on-exit story advance (fork-fidelity #3)
- A `[[gateway]]` can now **advance story state when the player takes that exit**: `set_scenario = N | "area"`
  bumps the ScenarioCounter and `set_flags = [{flag = <index|name>, value = 0|1}]` sets/clears gEventGlobal
  bits. The `set_var` writes are prepended to the gateway's Range trigger **behind a `usercontrol` guard**
  (so they fire on an actual walk-out, not a puppeted pass) and **behind any `requires_flag` gate** (so a
  gated door only advances the story when it's actually open), just before `Field()` — the values commit to
  the save-backed gEventGlobal before the transition. This is the write-side complement to `[startup]`'s
  entry-side assert: a forked field **chain** can now progress the beat as the player moves through it.
  Reuses `content/startup.startup_body`; `validate` + the reserved-band `lint` mirror `[startup]` (a write
  into a reserved region is flagged). Flag **names** in `set_flags` (and `[startup]`'s `flags`) resolve at
  load against the project's `[[flag]]` table **merged with campaign-shared names** — read/write parity with
  `requires_flag`, so a campaign member can write a shared story flag by name. Byte-identical build when the
  keys are absent. (`docs/FORK_FIDELITY.md` #3.)

### Added — FFIX Import GUI: the import-from-game functions, made discoverable
- **`apps/ff9_import.pyw`** — a front door to the kit's "bring content in from the real game" commands, so
  the powerful but cryptic `import` flags become **plain checkboxes**. Two tabs: **Field** (pick a real
  field — `Find…` runs `list-fields` — choose Background art `Native` / BG-borrow / Editable, and tick what
  to carry: *NPCs & props* / *real dialogue* / *dialogue stubs* / *save point*; then `Import field`) and
  **Read & Inspect** (`dialogue-import` a field, `flags-inspect` a save, `list-fields`, regenerate base
  templates). Each action shells out to `py -m ff9mapkit …` from the kit root and **streams** the output;
  the Field tab ends with a "→ deploy with Build & Deploy" hint. Standalone (in the `ff9_studio` launcher)
  **and** a new **Import** tab in the Campaign Editor. The fidelity mapping is a pure, smoke-tested
  `import_args()` (e.g. Native + carry-NPCs + carry-text → `import <f> --out … --id … --native
  --graft-player-funcs --carry-text`).

### Added — `[startup]`: assert the story beat a forked field represents
- **A forked real field boots with a zero `gEventGlobal`**, so every story-gated NPC/door/event takes the
  not-yet-happened branch — the field plays in its scenario-zero state. The new **`[startup]`** block presets
  the **ScenarioCounter** (`scenario = N` or an area name like `"Alexandria Castle"`) and/or specific story
  bits (`flags = [{flag = <index|name>, value = 0|1}]`) **unconditionally at field load**, prepended to
  Main_Init so every gate evaluated afterwards sees the asserted state. The biggest single fork-fidelity lever
  (`docs/FORK_FIDELITY.md` #1): a fork can finally boot in the right beat.
- Author-side only (you assert the beat — you have the game knowledge); no extraction. The ScenarioCounter is
  written via the engine's `0xDC` token (`set_var(GLOB_UINT16, 0, value)`); a story bit via
  `set_var(GLOB_BOOL, idx, value)` (long-index aware). Injected with `edit.insert_in_function` (entry-0 tag-0,
  offset 0 → byte-safe, fpos fixed), so a field **without** `[startup]` builds byte-for-byte as before.
- Unlike authored `set_flag` (safe `[8512,16320)` band only), a `[startup]` preset is *meant* to assert REAL
  FF9 story bits below 8512 — so the safe-band rule doesn't apply; the lint still flags a preset into a
  genuinely *reserved* region (chest bitfield / byte-23 handshake / worldmap unlocks / choice scratch).
  Spine: `content/startup.py`. *In-game verification (F6 reads the asserted beat) is the human step.*

### Added — story-flag registry depth: the worldmap Navi known-location words
- **Four new engine-grounded named vars** (`flags.NAMED_WORDS`): `WorldmapKnownLocationsF0..F3` (bytes
  92/94/96/98, UInt16, tier a) — the worldmap Navi cursor's known-location bitmasks (`keventNaviLocF0..F3`;
  F0 is the engine's own `knownLocations`). The first engine-reader pass grepped `gEventGlobal[<const>]`
  directly and missed the wrapper-accessor form (`ushort_gEventGlobal(92)`); re-scanning the complete
  fixed-index set recovered them. Naming bytes 92–99 as words also reclassifies that slice of the
  "write-only worldmap-unlock bits" as recognized word data (a decoded save now reports
  `WorldmapKnownLocationsF0 = N` instead of anonymous set bits). Surfaces automatically through
  `flags-inspect` / the Info Hub / `flags-diff`. `NAMED_WORDS` stays tier-(a)-pure (tested invariant).

### Added — dialogue polish: campaign-wide review + a live-text resolver diagnostic
- **`ff9mapkit dialogue` now accepts a `campaign.toml`** (it auto-detects a `[campaign]` manifest) and
  reviews **every member field's** authored dialogue in one pass — per-field sections with the final
  on-screen wrapping, plus a roll-up (total lines, which fields may overflow). A member that fails to load
  is noted and skipped, never aborts the review. Single-field `dialogue <field.toml>` is unchanged. Spine:
  `dialogue.campaign_dialogue` + `dialogue.flag_overflow` (the overflow check, now shared by both paths).
- **`dialogue-import` now says WHY a real field's text didn't resolve.** When the live `<zone>.mes` read
  comes back empty it distinguishes the two install/dependency failure modes — UnityPy not installed, or
  the game install / `resources.assets` not found (pass `--game`) — from "the source is fine, the field's
  block just didn't cover these txids; pass `--zone-id`." Spine: `dialogue.text_source_status` (never raises).
- **`ff9mapkit lint <field.toml>` runs the WHOLE offline suite in one go.** It used to be schema
  (`validate`) + story/flag logic (`lint_logic`) only; the walkmesh geometry / content-placement /
  layer-art / cutscene-movement checks lived behind `walkmesh verify`, and the camera-pitch advisory
  behind `guide`. They now all surface through `lint`, grouped by `[section]` — `logic`, `flags`,
  `placement`, `camera`. The pass degrades gracefully: a project whose camera/walkmesh can't resolve
  still reports its schema + logic findings (the resolve failure is recorded as an error, never a crash).
  Spine: `build.lint_all(project) -> LintReport` (the single source of truth; `walkmesh verify` is
  unchanged and still standalone).
- **New check — reserved story-flag bands.** A raw `set_flag = [N, 1]` / hand-written once `flag = N` /
  `requires_flag = N` (on an event, NPC, **prop**, gateway, cutscene, or choice) that lands in a *reserved*
  `gEventGlobal` region (the treasure-chest 'opened' bitfield 8376-8511, the byte-23 menu handshake, the
  worldmap-unlock bits, or the choice-mask scratch) is flagged and named — a WRITE there corrupts real
  save/engine state; a chest-band READ is unreliable. This extends the `[[flag]]` validator's safe-band
  guard to the literal indices that bypass it. The kit's established 8000+ working band is free space, so
  it draws no warning. `build.lint_flag_bands`.
- **Refined — the off-walkmesh content check no longer cries wolf on back-wall NPCs.** An NPC is placed by
  a world transform and renders regardless of the walkmesh; a normal FF9 NPC stands against the back wall,
  just past the floor edge, and the player talks to it from the adjacent floor. The check now HARD-warns
  only when an NPC is *grossly* off (farther than talk reach outside the floor's bounding box — a real
  misplacement), instead of flagging every edge-adjacent NPC as "will float / be unreachable." The player
  spawn and ladder landings still require being on the mesh. (Fixes a false-positive the unified `lint`
  exposed on the in-game-verified `vivi-hut` oracle; affects `build` / `walkmesh verify` warnings too.)

### Added — `flags-diff`: compare two saves' story state
- **`ff9mapkit flags-diff <A> [B]`** decodes two saves' `gEventGlobal` and shows the **A → B delta** — the
  ScenarioCounter change (with beat names), FieldEntrance, Treasure-Hunter points, chests, named word vars,
  and the story **bits set / cleared** (grouped by named region). The practical way to learn what a story
  beat writes: save before, do the thing, save after, diff. Reads the same forms as `flags-inspect` (an
  encrypted `SavedData_ww.dat`, a Memoria extra-save, a save JSON, or a bare Base64 blob); with one save,
  `--slot-a` / `--slot-b` diff two slots (default slot 0 → slot 1). Spine: `flags.diff_reports` /
  `flags.render_diff` (the bit-grouping is shared with `render_report`, so a bit is classified identically).

### Added — faithful object carry v1.5: the STARTSEQ-helper closure (+ two v1 correctness fixes)
- **A forked object now carries the concurrent Seq it launches.** A real field object often runs a
  benign per-frame helper via `STARTSEQ` (RunSharedScript) — a forward-lean, a shadow toggle, a small
  animation loop. v1 dropped that helper, so the object was REFUSED (left to a hand-authored stub).
  v1.5 carries the helper too — appended at a free slot and the launcher's entry-arg remapped, exactly
  like the proven ladder `sequences` graft — so the object renders faithfully. Across the real game this
  **un-refuses 53 objects and un-stubs 23 more** (faithful object coverage ~65% → ~70%); 109 helpers are
  carried, every one a benign type-1 Seq. Always on for `import` (a pure fidelity win, no flag).
- **The closure is body-vetted, not blind.** A helper that runs a cutscene op — a `MoveCamera` sweep, a
  `Battle`, a `Field`/`PreloadField` warp, a menu, a window — is NOT carried (it would fire in a static
  fork): those objects stay refused. The helper is appended-but-never-armed (a Seq is launched at runtime,
  not `InitObject`'d) and a helper shared by several objects is appended **once** (field-scoped dedup).
  `ff9mapkit lint` rejects an unsafe / non-type-1 / nested-STARTSEQ / double-armed helper.
- **Sibling-OBJECT closure was investigated and found EMPTY** — every uncarried object-to-object reference
  resolves to the party, the player, a controller, save machinery, or out-of-range, so there is nothing
  safe to carry there; v1.5 is exclusively the STARTSEQ-helper closure (a 676-field census + adversarial
  verification).
- **Fix: a sibling read inside an EXPRESSION operand is now remapped.** A grafted body that reads another
  object via the `op78` (B_OBJSPECA) expression token kept the donor's entry index after the move → it
  acted on the wrong/empty fork entry. The graft now walks the expression token stream and remaps it (a
  same-length 1-byte patch) — fixing ~31 already-shipped v1 objects as well as the closure.
- **Fix: a field with several `DefinePlayerCharacter` entries (182 of them) is classified correctly.** A
  reference to a *secondary* player entry was mis-read as an uncarried sibling; it now classifies as the
  player and the graft normalizes every PC entry to the runtime controlUID (250). Removes ~170 false
  "uncarried" refs and 7 secondary-PC false objects.
- Single-field authored builds stay **byte-identical** (the closure is off by default in
  `scan_objects_verbatim`; the hut SHA-256 golden is unchanged). Every real field's objects graft and
  round-trip (676/676, 0 errors). See `docs/OBJECT_CARRY.md` §2.

### Added — dialogue pillar (a dialogue editor + a stock-dialogue viewer)
- **The read side of FF9 field text.** New `ff9mapkit.dialogue` spine (UI-agnostic, tk-free): `parse_mes`
  (the missing `.mes` reader — handles BOTH the base game's index-implicit entries, where the txid is the
  entry's 0-based position with no `[TXID=]` tags, and the kit's explicit form it round-trips), `scan_dialogue`
  (decode every dialogue-window call + its txid out of a field's `.eb`), and `read_local_dialogue` /
  `read_field_dialogue` that JOIN the two into "NPC → text". A real field's text block is found via the
  engine's own `eventIDToMESID` table (baked into `_fieldtext.py`), language picked by stopword match.
  `project_dialogue` lists a `field.toml`'s authored lines with their final on-screen wrapping. The proven
  write path (`content.text` wrap/build_mes) is untouched — goldens stay byte-identical.
- **`ff9mapkit dialogue <field.toml>`** views a field's authored dialogue (every NPC line / event message /
  choice prompt+reply / cutscene say) and how each line wraps; flags lines that may overflow the window.
- **`ff9mapkit dialogue-import <field>`** reads a REAL FF9 field's dialogue live from your install and shows
  "NPC → text" — the "import from the game to prove plausibility" verb. `--mod <built mod folder>` reads a
  field offline with no install (the kit's own shipped hut joins to *"I miss you Zidane"*); `--zone-id <n>`
  reads a specific `<n>.mes` text block; `--out` writes a gitignored JSON view (SE-derived). By default it
  shows only real dialogue — `flags=0` system/notification windows (a field's error guard, "Received item!"
  popups) and repeated call sites are hidden (`--all` shows them), and the kit-only `@x,z` position heuristic
  is dropped on real fields.
- **Re-author a fork (`ff9mapkit import <field> --dialogue`)** appends the real field's NPC lines as
  ready-to-use, commented `[[npc]]` blocks (real model resolved by GEO name, clean editable text, a `pos`
  placeholder) — the "fork a field and rewrite its script" workflow. They parallel the verbatim-carried
  `[[object]]` NPCs; uncomment + reposition + rewrite the ones you want.
- **A dedicated Dialogue editor GUI** (`apps/ff9_dialogue.pyw`): every line of a field in one list, each with
  a **live preview of how it wraps on the FF9 screen** (so simple dialogue stays well-formatted — FF9 never
  auto-wraps), speaker + window-tail edited alongside, and an "Import from game" panel that views stock
  dialogue and can drop lines in as NPC stubs. Edits round-trip the same `field.toml` the Logic Editor uses.
- **Integrated:** a **Dialogue tab** in the Campaign Editor that **shares one `FieldDoc`** with the Logic
  Editor (the words edited in either are the same data, no divergence); the Logic Editor's new **"Dialogue…"**
  button hands the current field off to it; and a launcher entry. View stock dialogue, or word-smith a
  campaign's lines, from the same surface.

### Added — battle-map pillar (custom 3D battle backgrounds)
- `ff9mapkit battle-import <BBG>` forks a REAL FF9 battle background out of your install (geometry +
  per-submesh textures) into an editable `battle.toml` + `<BBG>.fbx`; `ff9mapkit battle-build` compiles
  it into a Memoria mod; `tools/deploy_battle.py` installs it reversibly into the per-worktree mod
  folder. `battle-list` browses the real BBGs available to fork.
- A battle map is a real textured **3D mesh** (child groups Group_0/2/4/8 = additive/ground/minus/sky)
  shipped as a loose ASCII **FBX** that **stock Memoria** loads instead of the bundle — no engine
  rebuild. **In-game verified** (texture reskin, a synthetic quad, and a byte-faithful BBG_B013
  round-trip). The first practical custom-battle-background pipeline for FF9. See `docs/FORMAT.md`
  → "Battle maps". Provenance-clean: geometry/textures are extracted from your own install at runtime,
  never committed.
- **Tier-c MINT — a brand-new battle SCENE (in-game proven).** `battle-import --fork-scene <DONOR>`
  also forks a real battle's gameplay/sequence/camera/text (raw16 + raw17 + per-lang `.eb` + `.mes`) into
  the project; `battle-build` emits a net-new `BattleScene <id> <NAME> <BBG>` registration plus those
  assets, and `--ship-as BBG_B<N>` ships the geometry under a **brand-new bbg number** (a wholly original
  map — the kit authors a static `.inb` for it). `deploy_battle.py --trigger-field N` repoints a field's
  encounter at the minted scene so you can fight it. No camera authoring needed (the donor's raw17 carries
  a working camera; a static `.inb` dodges the per-id anim tables). **In-game proven**: a net-new
  `BBG_B200` + scene on stock Memoria, fully fightable. The kit's emitted raw16/raw17/eb/mes are
  byte-identical to the hand-built probe verified in real gameplay. Provenance-clean: forked scene assets
  are SE-derived, written to a gitignored project dir, never committed.
- **Tune the fight (`[scene]`).** A minted battle's forked gameplay is now AUTHORABLE, not just a clone:
  a `[scene]` section in battle.toml overrides enemy **positions** (`pos`/`y`/`rot`), **stats**
  (`hp`/`mp`/`gil`/`exp`/`level`/`speed`/`strength`/`magic`/`spirit`), **rewards** (`drop`/`steal`, items
  by name), and the **camera** pose. The kit surgically patches the forked `raw16` (only edited bytes
  change) and keeps enemy TYPES intact so the forked attack sequences stay valid; items resolve by name
  (`"Hi-Potion"`); shared-type edits warn. Validated against the real Evil Forest scene (Goblin HP 33 →
  1500, etc.).
- **Spawn composition (`[scene]`) — recompose AND grow the encounter.** `monster_count` sets how many
  slots spawn (1–4, the engine cap) and a per-slot `type` chooses which enemy fills it (the scene's
  EXISTING types, so the forked raw17 sequences + GEO cover them; made targetable + auto-grounded). It
  writes the composition to EVERY pattern (a deterministic fight) and **re-authors the battle eb's
  `Main_Init` to bind one enemy-AI object per spawned slot** (`InitObject(1+type, 0x80+slot)`, reusing the
  donor's per-type AI entries). That removes the earlier donor-count cap entirely: a mint can now spawn
  MORE enemies than its donor natively did (e.g. a 1-enemy Evil Forest → four Goblins) with no player-model
  twitch — every slot has a real AI object, so no death misroutes into the player
  (`EventEngine.RequestAction`). In-game proven. Errors only if a needed per-type AI entry is absent
  (a non-standard donor eb). raw16 + Main_Init only; raw17 untouched.
- **Opening-camera tweaks (`[scene]`).** `camera_yaw` / `camera_pitch` / `camera_zoom` rotate / tilt / zoom
  a minted battle's opening camera by offsetting the donor's `SFXDataCamera` keyframes in raw17 IN PLACE
  (no offset-table repack). Cracked the "closed DLL camera" frontier: the native FF9SpecialEffectPlugin.dll
  reads the raw17 camera bytes directly (`SFX_StartPlungeCamera` gets the pinned raw17 + camOffset), so this
  renders with NO engine rebuild — in-game proven. Targets `cameraList[CameraNo]` = the raw16 `camera`
  selector. yaw + zoom are predictable; **pitch is an offset onto the donor's base angle (large values can
  dip the camera below the floor — use small steps).** Full from-scratch keyframe authoring (length-changing)
  is a future tier needing the offset repack.

### Added — `give_item` by name; gil can subtract
- `give_item = ["Potion", 1]` — items resolve by name (case/space/hyphen-insensitive) or numeric id,
  baked from Memoria's `RegularItem` enum (`ff9mapkit items` lists them). No more memorizing ids
  (236 = Potion; 232 was Sapphire). Negative `gil` now correctly **subtracts** (`RemoveGil`).

### Added — dialogue choices (`[[choice]]`)
- Talk to an NPC, pick from a menu, and **branch** on the answer — the interaction / puzzle primitive
  (merchant, Yes/No lever, quest-giver). Each option can show a reply, give an item / gil, and set a
  story flag (feeding the same `requires_flag` system). Grounded byte-for-byte in a real FF9 shop
  choice: a synchronous `WindowSync` prompt (rows after `[CHOO]`) + a `GetChoose()` branch. See
  `docs/FORMAT.md` → `[[choice]]`. **In-game verified.**
- The form editor (`ff9mapkit edit`) has a **Choices** section: edit the prompt/NPC and a list of
  options (text / reply / give item / gil / set flag), reorderable, with `give_item` by name.
- A choice can be **zone-triggered** (a lever / sign): `[[choice]] zone = [...]` instead of `npc`.
  Default `trigger = "action"` (stand on the zone and press) — re-usable, "decline" is non-destructive,
  and it can't loop (edge-triggered by the button), like a real FF9 lever. `trigger = "walk"` auto-pops
  on tread (flag-gated for loop-safety; `once` true/false). Movement locks while the menu is open.

### Added — modern Field Editor look
- The form-based editor (`ff9mapkit edit`) now ships a cohesive theme: a flat `clam`-based palette
  that **matches your Windows light/dark setting** (with a safe light fallback), Segoe UI typography,
  an accent on the primary actions (Save / Build & Test), roomier tree rows, and a colour-tagged
  console log. No new dependency — the palettes + OS probe are pure-stdlib (`editor/theme.py`).

### Changed — provenance: the repo ships no Square Enix game data
- The blank field, exit-region template, and binary test fixtures are no longer committed. They are
  regenerated from the user's **own** FF9 install by the new **`ff9mapkit extract-templates`**
  command, into a local (gitignored) cache. The repo/wheel ship only our copy/insert **patches**
  (our edits + copy offsets) and a SHA-256 manifest — never game bytes. Verified airtight: no patch
  insert run ever duplicates a run in the source field; a built wheel contains zero game bytes.
- `doctor` now reports whether templates are extracted; the byte-level test suite skips cleanly (with
  a pointer to `extract-templates`) when they aren't, so a fresh clone still runs the pure-logic
  tests offline. See [`docs/PROVENANCE.md`](docs/PROVENANCE.md).

Toward the first public **1.0**, remaining:
- Gallery screenshots (`docs/gallery/`).

## [0.9.3] — feature-complete, in-game-verified

The full custom-field pipeline, proven end to end in real gameplay. See
[`docs/FEATURES.md`](docs/FEATURES.md) for the complete capability list and
[`docs/TECHNICAL.md`](docs/TECHNICAL.md) for how the hard parts work. Highlights:

### Fields & camera
- Mint brand-new fields on a **stock Memoria** install (no engine fork).
- BG-borrow and fully-editable custom scenes.
- **Import / fork any of ~670 real fields** — camera, walkmesh, art, and (extracted from the script)
  exits, encounters, field BGM, and movement tuning.
- Author **any camera angle** from scratch; scrolling fields; multi-camera switch zones.

### Walkmesh & art
- Hand-model in Blender or import a real walkmesh; reshape multi-floor forks (seam-preserving).
- Pixel-accurate paint guide; depth layers; foreground occlusion; light/shadow blend layers.
- Build-time validation: reachability, content-on-mesh, near-edge, zero-area tris, seams, layer aspect.

### Content & scripting
- NPCs, custom dialogue, gateways, encounters (+ battle music), events (chests/gil/flags),
  story branching, and cutscenes (narration + actor walk/turn/emote/teleport). Save-persistent flags.

### Front-ends & engineering
- CLI, Blender add-on, form-based logic editor, build GUI; two-file (scene/logic) authoring.
- Byte-exact codecs (`.eb` / `.bgi` / `.bgx` / `.mes`); 254 kit + 47 Blender offline tests;
  opcode + projection math baked from Memoria source.

### Notes
- `0.9.x` unified the CLI and Blender add-on versions; the CLI was previously `0.1.0`.

[Unreleased]: https://github.com/
[0.9.3]: https://github.com/
