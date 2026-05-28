# CLAUDE.md — FF9 Custom Map Mod (Memoria Engine)

> This file is read automatically at the start of every Claude Code session.
> Read it fully before doing anything. Update the **Session Log** at the end of
> every session. Treat the **Hard Constraints** as non-negotiable.

---

## 1. Project goal

Add a new, playable field ("room") to *Final Fantasy IX* (Steam) using the
**Memoria Engine**, then wire it into the game with working entrances/exits,
NPCs, dialogue, and at least one encounter.

**Chosen strategy: MINT new fields.** Use HW's `Memoria → Export as Custom Field` to register a brand-new field ID + `DictionaryPatch.txt` line, drop the generated assets into our mod folder, and the engine accepts it. **Proven Session 2** — see the project memory `project-ff9-mint-proven` for the verified runtime path layout and gotchas.

This supersedes the earlier "REPURPOSE, don't mint" plan from Session 0. Session 0's worry about "two unsolved problems (registering a new field ID, authoring a walkmesh)" turned out to be solvable: HW's Custom Field export handles registration, and Memoria's `FieldCreatorScene.cs` (in-game editor) loads `.obj` walkmeshes — so walkmesh authoring is a Blender (or other 3D tool) workflow, not hand-binary-editing.

**THE working recipe (proven Session 4) — see project memory `project-ff9-bg-borrow-solution`:** HW's cloned atlas is broken, so we don't use it. Instead, the `FieldScene` DictionaryPatch directive decouples BG / script / text by ID — so we mint a custom field ID + custom script, then point its BG lookup at a REAL base-game field's art:

```
FieldScene 4000 11 LDBM_MAP203_LB_HNG_0 CUSTOM_FIELD_001 1073
```

This resolves the BG to the real `FBG_N11_LDBM_MAP203_LB_HNG_0` (Hangar art in p0data) while running our custom script under field ID 4000. Renders clean. **CRITICAL gotcha:** the area ID must be ≥ 10 — the parser builds `"FBG_N" + areaID` with no zero-padding and the asset loader reads exactly 2 chars, so single-digit areas (00–09) black-screen. Borrow art from an area ≥ 10 field.

**Reference custom field (Session 2–4):** ID `4000`, `CUSTOM_FIELD_001`, script cloned from field 1357, BG borrowed from the real Hangar (area 11). Renders cleanly in-game. (HW's own cloned atlas under `FBG_N57_CUSTOM_FIELD_001/` is broken and unused.)

**What this does NOT give us:** truly novel painted background art — that's a Hard-Constraint §2 human/art task anyway. BG-borrow is a complete solution for a playable custom room that reuses existing art.

**Field 1357 is no longer required.** Originally chosen as the throwaway target before we knew minting worked. Kept for now only as a known-good base to clone from. The Lindblum Castle Hangar cutscene we feared affecting is no longer at risk — we don't have to gut 1357 anymore.

**Community context:** Per Session 1 research, no shipped FF9 mod has previously minted brand-new fields. We are likely the first practical reference for this workflow. Worth eventually documenting publicly (qhimm forum post, Moogles & Mods Discord).

---

## 2. Hard constraints (read every session)

These define what Claude Code can and cannot do here. Do not burn a session
fighting these.

- **You cannot paint background art.** Pre-rendered backgrounds are an art task.
  The human supplies any new/edited background image and its depth layers.
- **You cannot author or judge the walkmesh / camera alignment.** It is a 3D
  spatial task done in a GUI (Hades Workshop) against a fixed-perspective
  background. You cannot see the running game. The human owns this.
- **You cannot verify in-game results.** After every change that should be
  visible, STOP and ask the human to playtest and report back. Never assume a
  change worked because it compiled.
- **You CAN own:** the field event script (PSX-style assembler), exits/gateways,
  triggers, flags, dialogue text, encounter + BGM + battle-background metadata,
  the build/patch loop, version control, and all notes/logs.
- **Back up before every edit.** Copy any file to `backups/<file>.<timestamp>`
  before modifying it. The base game files are the only source of truth if we
  corrupt something.
- **One change per build.** When a build breaks in-game, we need to know which
  edit did it. Do not batch unrelated changes into a single test.

---

## 3. Environment & tools (verify in Session 0, then trust)

| Thing | Location / note | Status |
|---|---|---|
| Memoria source | `C:\gd\FFIX\Memoria\` (clone of `Albeoris/Memoria`, gitignored) | ✅ verified S0 |
| Memoria installed via | Memoria.Patcher.exe v2025.07.04 run against game folder | ✅ verified S0 |
| Game install folder | `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\` | ✅ verified S0 |
| Memoria compiler | `<game>\StreamingAssets\Scripts\Compiler\Memoria.Compiler.exe` | ✅ verified S0 |
| Battle scripts source | `<game>\StreamingAssets\Scripts\Sources\Battle\` | ✅ verified S0 |
| Field scripts | edited via **Hades Workshop v0.50** (`C:\gd\FFIX\Hades-Workshop\` clone for source; runtime binary installed separately) | ✅ verified S0 |
| Hades Workshop opens | `<game>\FF9_Launcher.exe` (patcher overwrites in place; no separate Memoria.Launcher.exe is installed) | ✅ verified S0 |
| Mod folder | Memoria Mod Manager install path `TBD` (set when first mod is installed) | TO SET |
| Memoria.ini | `<game>\Memoria.ini` — engine toggles | ✅ verified S0 |
| Bulk field-script export | `reference/test2/` (gitignored, 817 files, ~84 MB) — regenerable via HW Batch → Export Field Scripts | ✅ verified S0 |
| Field manifest | `reference/field-manifest.tsv` — TSV of filename / field ID / field name | ✅ verified S0 |

> Anything marked TO VERIFY: confirm the real path exists on disk and record the
> absolute path in the Session Log before relying on it. Do not assume.

---

## 4. Anatomy of a field (what we're actually editing)

A FF9 field is several coupled pieces. We control the first group; the human
controls the second.

**Claude-owned (text / code / data):**
- **Event script** — the field logic. Entry point is `Function Main_Init`.
  Encounters are set there, e.g. `SetRandomBattles( slot, id, ..., id )`.
- **Exits / gateways** — links from other fields into ours and back out.
- **Encounter music** — `BtlEncountBGMMetaData.txt` (field battles). A field
  with no entry here plays NO battle music; add one if we add encounters.
  (`WldBtlEncountBGMMetaData.txt` is the world-map equivalent — probably N/A.)
- **Battle background** — the "Dictionary Patch" must point our encounters at a
  valid battle background, or battles load wrong/broken.
- **Dialogue / text** — field text entries.

**Human-owned (visual / binary):**
- **Background image** + its depth layers.
- **Walkmesh** geometry + **camera/frustum** alignment to the background.

---

## 5. The build / patch / test loop

Standard cycle for every change:

1. `git status` — confirm clean tree, know what we're about to touch.
2. Back up the target file → `backups/<name>.<timestamp>`.
3. Make exactly ONE logical change.
4. Recompile if it's a script (`Memoria.Compiler.exe`) / re-export from Hades
   Workshop if it's a field script.
5. Reinstall/activate the mod via the Memoria Mod Manager if needed.
6. `git add -A && git commit -m "<what changed + why>"`.
7. **STOP. Ask the human to launch the game and report what they see.**
8. Record result (pass/fail + symptom) in the Session Log.

If a step's exact command is unknown, find it once, then record it in section 3.

---

## 6. Conventions

- **Git everything** except the base game install. The repo holds our scripts,
  metadata edits, Hades Workshop `.hws` source, backups, and these docs.
- Commit messages: `<area>: <change> (<why>)` e.g.
  `field: rewrite Main_Init exits to link new room (was throwaway)`.
- Keep a `KNOWN_GOOD` tag/commit for the last state that loaded in-game cleanly.
  Roll back to it rather than debugging a deep hole.
- Never hand-edit a file you don't understand the format of. If it's binary or
  undocumented, ask the human to do it in the GUI and describe the result.
- Prefer reading an existing, working field's exported script as a template
  over inventing script structure from memory.

---

## 7. Phased plan (check off as completed)

### Session 0 — Recon & setup
- [ ] Record absolute paths for every row in section 3.
- [ ] Confirm Memoria is installed and the base game still launches.
- [ ] `git init` the mod repo; commit a clean baseline + `.gitignore` for the
      game install.
- [ ] Export ONE existing field's script via Hades Workshop; save it as a
      reference template in `reference/`.
- [ ] Pick the throwaway field to repurpose; record its ID in section 1.

### Session 1 — Prove the loop
- [ ] Make a trivial visible edit to the throwaway field (e.g. change one NPC
      line or an encounter id).
- [ ] Run the full build/test loop. Human confirms the change shows in-game.
- [ ] Tag `KNOWN_GOOD`.

### Session 2 — Background swap
- [ ] Human supplies the new background + layers; you record where they go.
- [ ] Wire the field to use it; human confirms it renders (alignment may be off
      — that's expected, walkmesh comes next).

### Session 3 — Walkmesh & camera (human-led)
- [ ] Human adjusts walkmesh/camera in the GUI until movement matches the art.
- [ ] You document the final values and re-export cleanly.

### Session 4 — Bring the room to life
- [ ] Rewrite `Main_Init`: NPC placements, triggers, dialogue, flags.
- [ ] Add encounter(s) + `BtlEncountBGMMetaData.txt` entry + battle-background
      dictionary entry.

### Session 5 — Wire it into the world
- [ ] Add a gateway from an existing field into the new room and an exit back.
- [ ] Full playthrough of entering, interacting, fighting, and leaving.
- [ ] Tag a release; write install notes.

---

## 8. Glossary

- **Field** — a single explorable room/screen with a fixed-perspective
  pre-rendered background.
- **Walkmesh** — invisible geometry defining walkable area + depth.
- **Main_Init** — the field event script's entry function.
- **Gateway** — a trigger that moves the player between fields.
- **HWS** — Hades Workshop source file (our editable field/data project).
- **Mod Manager** — Memoria's in-game installer/activator for mods.

---

## 9. Open questions / risks (update as resolved)

- Does our repurposed field's walkmesh need full re-authoring, or can the old
  one be reused with a similar background layout? (Cheapest if reused.)
- Exact Hades Workshop export → game-folder path for field scripts. (Confirm S0.)
- Whether battle-background dictionary edits persist through Mod Manager
  reinstalls, or must be reapplied.
- ~~Does the chosen throwaway field get referenced anywhere else in the game's
  scripts (breaking something when we gut it)? Grep before committing to it.~~
  **Resolved S0:** Field 1357 has zero `Field()`/`PreloadField()` references in
  field scripts, but is registered in `NarrowMapList.cs` (a Memoria C# table) —
  meaning a Lindblum cutscene fires from game code, not field scripts. Tradeoff
  accepted by user. Lesson kept in memory: grep alone is insufficient because
  cutscenes can trigger from C#.

---

## Session Log
> Append a dated entry every session: what you changed, what the human verified,
> what broke, and the next concrete step. Newest at the bottom.

### 2026-05-28 — Session 0 — Environment recon & setup

**Done:**
- Scaffolded mod repo at `C:\gd\FFIX` (commits `a91e45e`, `bec22b3`, `e5ed1f4`, `19e0906`).
- Verified Steam install: `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\`.
- Installed Memoria via `Memoria.Patcher.exe` v2025.07.04. Confirmed Memoria.Compiler.exe, Sources\Battle\, FF9_Launcher.exe (overwritten in place), and Memoria.ini all present post-patch. Human confirmed the game launches via the new Memoria-branded launcher.
- Installed Hades Workshop v0.50 (from hiveworkshop.com mirror — no GitHub releases for that repo). Opened the game in HW.
- Cloned reference sources: `Memoria/` and `Hades-Workshop/` (gitignored).
- Exported field 0109 Alexandria/Wpn. Shop as the canonical script-format reference (`reference/field-0109-alexandria-wpn-shop.txt`). Learned the script format (Functions, entries, regions, exits, NPC patterns).
- Bulk-exported all 817 field scripts to `reference/test2/` (gitignored, regenerable). Built `reference/field-manifest.tsv` mapping HW filename → in-game field ID → name.
- Filled in CLAUDE.md §3 with all verified paths.
- **Chose throwaway field: 1357 L. Castle/Hangar.** First grep-based recommendation (1357 + 1365) was rightly vetoed by human as cutscene-used; reframed as "which cutscene are we OK affecting" and human picked Hangar. Tradeoff: gutting it will affect the Lindblum hangar cutscene.

**Human verified:**
- Patcher ran successfully against the Steam install.
- Game launches via the new Memoria launcher.
- Hades Workshop opens the game project and shows the Environment → Fields panel.
- Per game knowledge: L. Castle/Hangar and L. Castle/Telescope are both used in cutscenes (correcting my initial grep-only assessment).

**Open issues / risks:**
- Mod folder path (Memoria Mod Manager install location) still TBD — will be set in Session 1 when we install our first mod.
- We can't actually test that field 1357 is "safe" until we gut it and play through Lindblum — accepted risk.

**Next concrete step (Session 1):**

1. **Set up a debug warp to field 1357.** Human has no Lindblum-area save and field 1357 is mid-Disc-2 content (hours of play to reach normally). Plan: pick a very early field (probably Alexandria/Main Street, field 100 or 101 — confirm at session start), and add `Field( 1357 )` as the first executable line of its `Main_Init` so launching a new game teleports straight to the Hangar after the unskippable intro. Memoria's `[Graphics] SkipIntros = 3` is already set, so the title-loop is bypassed.
2. **Confirmed cleanup plan:** this warp is a debug-only hack — track it in a `backups/<early-field>.<timestamp>` snapshot of the original script so we can revert in one step. Do NOT let it ship.
3. **Once warped in,** make one trivial visible edit to field 1357 itself (e.g. shift Zidane's spawn coordinates by a clearly-visible amount, or add a single popup window on entry). Run the full build/test loop. Human confirms in-game.
4. **Revert the debug warp**, recompile, confirm normal game start still works, tag a new `KNOWN_GOOD`.

Also rule out option C (Memoria's `[Debug] StartFieldCreator`) for our use case — it's a field *editor* scene, not a field warp; loads geometry but not player behaviour. Sanity check only.

### 2026-05-28 — Session 1 — Build/test loop proven; field 1357 fully usable

**Done:**
- Established the mod-folder workflow: HW's "Save Steam Mod" (Ctrl+M) writes a complete mod structure to `<game>\FF9CustomMap\` (StreamingAssets/.../field/<lang>/evt_*.eb.bytes plus ModDescription.xml). Memoria auto-enabled the mod (visible in Memoria.log Mods list: `'FF9CustomMap' 'AlternateFantasy' 'MoguriVideo' 'MoguriMain'`).
- First warp attempt (commits `b575fcd`, `53b2d3c`) injected `PreloadField + Field(1357) + return` into field 50's `Main_Init`. Failed → black screen + Cargo Room ambient. Two lessons surfaced:
  - HW's parser rejects unreachable code after `return` (1 error + 204 warnings on first import; lost the whole import).
  - A bare `Field(N)` call from a stripped-down `Main_Init` doesn't trigger a transition — the engine needs InitObject + sound sync + FadeFilter + `Wait(25)` first. (Saved as project memory.)
- Pivoted (commit `bc41620`): restored field 50, hijacked field 70 (Opening-For FMV) instead by swapping its existing `Field( 50 )` → `Field( 1357 )` inside the case +0 path. This piggybacks on the engine-correct transition pattern the game itself uses.
- Warp confirmed via in-game popup `"Error Env Play() Slot=0"` (text ID 62 from field 1357's own text table — could not appear unless we'd reached 1357).

**Human verified:**
- Save Steam Mod creates `FF9CustomMap/` with the expected internal structure.
- After warp: popup dismisses → black fades into the Hangar background art.
- WASD moves Zidane around the Hangar map.
- V opens the menu; Zidane is in the party as expected.

**Big surprise (positive):** Field 1357 is a complete, fully-rendering, walkmesh-having playable map. Background art exists, walkmesh works, camera works, player object spawns and moves correctly. The `[AssetManager] invalidFieldMapID` errors in Memoria.log during the warp were transient noise — not a real missing-asset issue.

**Implications for the phased plan:**
- ~~Session 2 (Background swap)~~ — skip. 1357's existing Lindblum Castle Hangar BG is usable as-is.
- ~~Session 3 (Walkmesh & camera)~~ — skip. Original Hangar walkmesh already correct.
- Jump straight to **Session 4 (Bring the room to life)** as the next session.

**Open issues / risks:**
- The `"Error Env Play() Slot=0"` popup is benign noise on entry. It fires because 1357's Main_Init expects some environment-audio state set by the cutscene that normally precedes it — and we entered fresh from the warp without that state. To suppress: gate the popup behind a flag or reset `VAR_GenUInt8_13` before calling Field(1357) in field 70. Not blocking; defer to Session 4 cleanup.
- Field 1357 still has zero exits — once we're in, we're in. Currently fine for testing (the warp puts us right back if we restart). Adding a debug "exit to main menu" or a real exit comes in Session 4/5.
- Field 50 (Prima Vista Cargo Room) cutscene is now skipped from game start because of the warp — accepted for as long as the warp is in. Reverting one line in field 70 restores normal flow.
- Mod folder path for [CLAUDE.md §3](CLAUDE.md): `C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\` — verified S1.

**Next concrete step (Session 4 — formerly "Session 2"):**

1. **Suppress the "Error Env Play()" popup** so entry to 1357 is clean. Either gate it with a flag check, or set `VAR_GenUInt8_13 = 0` (and `_14 = 0`) inside the warp before `Field(1357)` in field 70.
2. **Add the first NPC** to field 1357 — author a new `#HW newentry` block with an NPC `_Init` (SetModel, CreateObject, animations) and `_SpeakBTN` (TurnTowardObject, WindowSync dialogue). Use the LibrarianA pattern from `reference/field-0109-alexandria-wpn-shop.txt` as the template.
3. **Re-import, Save Steam Mod, human plays in.** Confirm the NPC appears, can be talked to, says the line we wrote.
4. **Iterate:** add a second NPC, an interactive object, a region trigger that pops a window. Each as its own commit, each verified in-game.
5. After we have ~2 NPCs and 1 interactable working, **plan the exit/entrance back to a real world field** (Session 5 territory).

### 2026-05-28 — Session 2 — MINT proven; pivot from REPURPOSE

**Done:**
- Researched the FF9 modding community (general-purpose agent report): confirmed no shipped mod has minted brand-new fields. We'd be the first practical reference.
- Used HW's `Memoria → Export as Custom Field` with field 1357 as base, scriptid=4000, mapid+fieldid=CUSTOM_FIELD_001 → 13 files generated (562 KB) in expected layout. No errors.
- HW dialog produced this DictionaryPatch line: `FieldScene 4000 57 CUSTOM_FIELD_001 CUSTOM_FIELD_001 1073`.
- Integrated generated assets into `FF9CustomMap/StreamingAssets/...` and created `FF9CustomMap/DictionaryPatch.txt` with the registration line.
- Redirected Session-1 warp in field 70 from `Field(1357)` → `Field(4000)`.
- Game launched → field 4000 loaded → engine accepted the new ID and rendered the cloned BG.

**Human verified:**
- In-game render is unmistakably the Lindblum Castle Hangar (brown wooden beams, arched windows, lattice structure) — proves cloned assets are being used.
- BUT atlas tile mapping is broken: many tiles render in correct screen positions but source from wrong/empty regions of `atlas.png`, producing a fragmented image. Player object spawned, walkable (assumed).

**What this proves:**
- ✅ Custom field IDs work (`DictionaryPatch.txt` `FieldScene` directive)
- ✅ Memoria's asset loader honors mod-folder paths for FieldMaps + per-language EventBinary
- ✅ Full required-path layout captured in project memory `project-ff9-mint-proven`
- ⚠️ HW's Custom Field clone has an atlas-UV bug (or atlas extraction bug) — recognizable Hangar imagery in wrong UV positions
- ⚠️ Same benign `invalidFieldMapID` log noise as Session 1; unrelated to atlas issue

**Strategic pivot:** [CLAUDE.md §1](CLAUDE.md) rewritten around MINT (was REPURPOSE). Field 1357 is no longer needed as a sacrificial throwaway — it stays only as a known-good base to clone from. The original Lindblum hangar cutscene we feared affecting is no longer at risk.

**Open issues / risks:**
- **Atlas-UV bug** — render is broken-but-recognizable. Workaround options: (1) try a simpler base field with smaller atlas; (2) hand-author atlas.png + .bgs.bytes; (3) use Memoria's `FieldCreatorScene` in-game editor; (4) compare cloned atlas.png byte-for-byte against the original from p0data*.bin to localize the bug.
- Field 50 still skipped by the debug warp (Session 1 carry-over).
- We should eventually document this MINT workflow for the community (qhimm thread / Discord) — the only public reference for FF9 custom-field minting.

**Next concrete step (Session 3 — repurposed as "fix the atlas / pick a clean base"):**

1. **Diagnose the atlas bug.** Quick test: byte-compare the exported `atlas.png` from HW vs the original 1357 atlas inside one of the `p0data*.bin` bundles. If different → HW's extraction is the bug. If identical → the `.bgs.bytes` UV references are off.
2. **Try a different base field.** Clone something simpler (e.g., a small intro screen) using the same MINT workflow. If THAT renders correctly, the bug is specific to 1357's atlas; if it doesn't, the bug is in HW's clone-path generally.
3. **If atlas is hopeless: bypass HW's atlas extraction.** Use Memoria's `FieldCreatorScene` (`[Debug] StartFieldCreator=1` in Memoria.ini) to interactively set up a field's BG + walkmesh from scratch, then save. This is the engine-author's intended path for custom fields.
4. **Once a custom field renders cleanly**, return to the Session 4 plan (add NPCs/dialogue/encounters), this time targeting our minted field rather than 1357.

### 2026-05-28 — Session 3 — Atlas bug confirmed systemic; HW clone path declared dead-end

**Done:**
- Minted second custom field (4001 / `CUSTOM_FIELD_002`) cloned from field 109 (Alex/Wpn. Shop — a normal playable interior) as an A/B against the 1357 clone.
- Same integration flow: 13 files into `FF9CustomMap/`, second `FieldScene` line in `DictionaryPatch.txt`, field 70 warp redirected from `Field(4000)` → `Field(4001)`. HW Save Steam Mod preserved everything cleanly.
- Tested in-game and got conclusive A/B results.

**Human verified:**
- Both NPCs from cloned field 109 spawn (Librarian-style shopkeeper + Lindblum_ManA / "Ryan").
- Player object is rendered as Vivi but party state shows Zidane (field 109's `Main_Init` calls `InitObject(19, 0) // Vivi` since the canonical Wpn. Shop entry is Vivi-context).
- Dialog showed "Zidane: Her name is Mikoto. She's kinda like my little sister." — end-game Pandemonium/Bran Bal text, not Wpn. Shop dialog. Means our `textid 1073` parameter is pointing at the WRONG text block.
- **Atlas BG is fragmented in the same way as the 1357 clone** — recognizable Wpn. Shop tiles in wrong UV positions.

**What this proves:**
- **Atlas-UV bug is systemic to HW's `Export as Custom Field` clone path**, not 1357-specific. Both bases produced the same fragmented render.
- `textid` parameter must match the base field's actual text block (HW defaults to 1073 regardless of base).
- Cloned scripts inherit the base field's character-spawn assumptions — model mismatch is expected when warping into a Vivi-context field with a Zidane-context party.
- HW author is retired → bugs won't get patched upstream.
- All Session 3 gotchas captured in project memory `project-ff9-mint-gotchas`.

**Strategic call:** HW's batch-clone path is officially declared a dead-end for actual authoring. It's still useful as a PROOF that the engine accepts custom field IDs (which it does). For real authoring we pivot to Memoria's `FieldCreatorScene` — the engine-author's intended workflow.

**Playtesting bonus finding (post-test exploration in field 4001):**
- The cloned field 4001 inherits field 109's exits as-is (Region6 → `Field(103)` Alexandria/Square; Region7 → `Field(110)` Alexandria/Synthesist), so the player can walk OUT of our broken custom field into the **live main game**.
- Both Alex/Square (103) and Alex/Synthesist (110) **rendered normally** when entered this way.
- From Alex/Square, walking back into the original Wpn. Shop loads field 109 — which **also renders normally**.
- **Implication:** the bug is NOT in the engine's render pipeline or in field 109's base data. The original game data is intact. Only the HW-cloned `FBG_N57_CUSTOM_FIELD_002/atlas.png` (or the cloned `.bgs.bytes` UV references) is corrupt. HW is doing something wrong during extraction/repack, full stop.
- **Side effect, useful for future testing:** our debug warp through Prima Vista now drops you into a sequence that's effectively "load into a broken custom field, walk one screen, you're in the live game as Vivi." A weird but workable backdoor.

**Open issues / risks:**
- Atlas-UV bug in HW clone — accepted, working around via FieldCreatorScene instead of fixing. NEW info: it's narrowly in HW's extraction/repack of the atlas.png and/or .bgs.bytes — not in the engine or base data.
- Field 50 still skipped by debug warp (carry-over from S1)
- We have TWO test custom fields (4000, 4001) registered. Both broken but both prove the registration works. Can clean up later or leave as artifacts.
- The cloned 4001 has inherited exits to live game fields — handy for testing, but means the "debug warp" now lets the player escape into real game content. Not blocking; note for cleanup.

**Session 4 hypothesis worth testing alongside FieldCreatorScene:**
- Try changing the DictionaryPatch line to map our custom scriptid to the **original field's BG identifiers** (e.g. `FieldScene 4001 2 ALXC_MAP103_AC_WPS_0 CUSTOM_FIELD_002 <textid>`). If Memoria resolves the BG via mapid and the script via fieldid independently, this might let us **borrow the working BG from the base game** while still running our cloned script — bypassing HW's broken atlas extraction entirely. Cheap test, would be conclusive.

**Next concrete step (Session 4 — FieldCreatorScene exploration):**

1. **Enable Memoria's in-game field editor.** Edit `Memoria.ini`: under `[Debug]`, set `Enabled = 1` and `StartFieldCreator = 1`.
2. **Launch the game.** Instead of the title screen, you should land in the FieldCreatorScene editor UI (per `FieldCreatorScene.cs` source).
3. **Explore the editor.** It has panels for: Information, SetupCamera, SetupOverlay, SetupAnimation, SetupWalkmesh, Save. It loads `.obj` walkmeshes from `MemoriaFieldCreator/CustomFields/<name>/`.
4. **Goal of S4:** prove we can create a minimal custom field via FieldCreatorScene that renders cleanly (no atlas bug). If yes, that's our authoring path forward — Session 5+ becomes "make a real room."
5. **If FieldCreatorScene also has issues,** fall back to either (a) hand-authoring the BG/atlas/.bgs files following the format spec, or (b) study Trance Seek's MemoriaDV source for any custom-field tricks.

When done with FieldCreatorScene exploration, remember to set `StartFieldCreator = 0` to restore normal game launch.

### 2026-05-28 — Session 4 — BG-borrow solution PROVEN; complete custom-field path achieved

**Done:**
- Diagnosed Session 3's black-screen risk before it could recur: read the Memoria `FieldScene` DictionaryPatch parser (`DataPatchers.cs:413`) + `AssetManagerUtil.cs:230`. Found the BG lookup name is built as `"FBG_N" + areaID` with NO zero-padding, while the loader reads exactly 2 chars for the area code and all vanilla names are 2-digit.
- First BG-borrow attempt used field 109's area (1) → built `FBG_N1_...` → lookup failed → BG missing → field 109 script crashed in `EventEngine.ProcessEvents` → black screen. Confirmed the leading-zero limitation: single-digit areas (00–09) can't be expressed through the directive.
- Pivoted to field 1357 (Hangar) as the borrowed BG: area 11 (two digits, safe), minimal script (no overlay/tile crash risk), known-good BG. DictionaryPatch line: `FieldScene 4000 11 LDBM_MAP203_LB_HNG_0 CUSTOM_FIELD_001 1073`. Warp pointed back to `Field(4000)`.

**Human verified:**
- **Field 4000 rendered the Hangar cleanly — no atlas fragmentation.** This is a brand-new custom field ID, running our cloned script, registered by our DictionaryPatch line, displaying real base-game art.
- Log showed only the benign `invalidFieldMapID` transition noise (same as every clean render since S1).

**What this proves — the complete working path:**
- We can **mint a custom field (new ID + custom script + our own NPCs/dialogue/encounters/exits) that reuses any existing field's working background art**, by pointing the `FieldScene` directive's areaID+mapid at a real base-game BG.
- The atlas bug in HW's clone path is fully sidestepped — we never use HW's broken atlas.
- Full recipe + the area-ID-≥10 gotcha captured in project memory `project-ff9-bg-borrow-solution`.
- The ONLY thing not solved is truly novel painted BG art — which is a Hard-Constraint §2 human/art task anyway. For a playable custom room, BG-borrow is everything we need.

**Strategic state:** All major unknowns are now resolved. We can build a real custom room. FieldCreatorScene exploration becomes OPTIONAL (only needed if we later want novel art). The phased plan can resume at "bring the room to life."

**Open issues / risks:**
- `Save Steam Mod` may overwrite `DictionaryPatch.txt` — we keep a tracked copy at `mod/FF9CustomMap-DictionaryPatch.txt` and must re-verify/re-apply after each HW save until we confirm whether HW preserves it.
- Debug warp still active (field 70 → 4000); field 50 opening still skipped. Carry-over.
- Two custom fields registered (4000 working via BG-borrow, 4001 broken/unused). Clean up 4001 eventually or leave as artifact.

**Next concrete step (Session 5 — build the actual room on field 4000):**

1. **Decide the room's identity** — what is this room, narratively? Pick a borrowed BG that fits (any area-≥10 field's art). Hangar is fine as a placeholder.
2. **Fix the textid** so dialogue we author resolves correctly — confirm 1073 is the right text block for our script, or assign our own.
3. **Author content in the cloned script** (`mod/` copy of field 4000's `.eb` source, edited via HW import): replace the inherited Main_Init with a clean one (correct player object = Zidane, suppress the Error Env Play popup), add 1–2 NPCs (LibrarianA pattern from `reference/field-0109-alexandria-wpn-shop.txt`), a line of dialogue, a region trigger.
4. **Add an encounter** + `BtlEncountBGMMetaData.txt` entry + battle-background dictionary entry (per [CLAUDE.md §4](CLAUDE.md)).
5. **Wire a real entrance/exit** to/from an existing world field (Session 5 of the original plan).
6. Each change = one commit + one in-game verification, per the build/test loop.

### 2026-05-28 — Session 5 — Goal clarified to NOVEL painted BGs; FieldCreatorScene unblocked

**Goal correction:** User's real goal is **novel painted backgrounds with custom geometry** (Path B), not reusing existing art. BG-borrow (S4) was just proving field plumbing. This supersedes S4's "FieldCreatorScene is optional."

**Done:**
- Source dive (`BGSCENE_DEF.cs`) found Memoria's intended BG pipelines: PSD/atlas import ([Export]/[Import] Field=1, Moguri's method) and the `.bgx` "pure Memoria scene" (text overlays+depth / cameras + per-overlay PNGs, keyed by field name; supports `USE_BASE_SCENE`). Both have Memoria build the atlas itself → bypass HW's broken atlas.
- Research agent corroborated: Moguri repainted over existing overlay structure (proven); novel geometry via FieldCreatorScene is code-supported but community-unproven.
- Enabled `[Debug] Enabled=1 + StartFieldCreator=1` (ini backed up; snapshot in `mod/`).
- **Found + fixed a real FieldCreatorScene bug.** Editor launched but loading a field black-screened. Diagnosis: `ExportMemoriaBGX` writes overlay PNGs with a directory-less path → they land in the game ROOT, while the `.bgx` reads them from its own folder. Confirmed 103 stray `FBG_*_*.png` in game root, 0 in field folders. Likely why nobody has publicly used this editor. Workaround: moved all PNGs into their `InternalFields/<name>/` folders.
- Captured 5 real `.bgx` scene definitions to `reference/bgx-samples/` and documented the full format.

**Human verified (editor now works):**
- Cargo Room renders with walkmesh overlay; character model drags around the navmesh.
- Right-mouse pan works; zoom is the "Distance Factor" slider in Setup Cameras (not scroll).
- **Setup Walkmesh** panel: per-walkpath flags (Active by default / Alternate footstep / Prevent NPC / Prevent PC pathing); green = walkable-floor viz.
- **Setup Cameras** panel: Camera selector, "Select Anchors" toggle, Distance Factor slider, Reset, + the 5-point anchor instructions.

**What this proves:** FieldCreatorScene is fully functional on this install (after the PNG-path workaround). Path B (novel geometry) is viable. The `.bgx` format is simple and hand-authorable.

**The novel-custom-field recipe (target for next sessions):**
1. HUMAN paints a background (one flat image for everything-behind-player, or separate layers for foreground depth pieces). Hard Constraint §2: human owns the art.
2. Author a walkmesh: Blender → `.obj` (each walkable region a separate `o` object). Place at `MemoriaFieldCreator/CustomFields/<name>/<name>.obj`.
3. Author/derive a `.bgx` referencing the painted PNG(s) as OVERLAYs (Position incl. Z-depth, Size, Image, Shader) + one CAMERA. Place at `CustomFields/<name>/<name>.bgx` with the PNG(s).
4. In-editor: Load Custom Field <name>, use 5-point anchor (walkmesh vertex ↔ background point ×5) + Distance Factor to align the camera, set overlay depths, Save (ExportField → writes `.bgi.bytes` + `.bgx`).
5. **Apply the PNG-path workaround** after Save (ExportField has the same bug — PNGs dump to game root; move them next to the saved `.bgx`).
6. Integrate `CustomFields/<name>/` output into `FF9CustomMap/StreamingAssets/.../FieldMaps/<name>/` + register via `DictionaryPatch FieldScene` + point a warp at it. Test in-game.

**Open issues / risks:**
- FieldCreatorScene PNG-path bug — workaround required after every editor export/save (move PNGs next to the `.bgx`). Candidate to report upstream / patch in our Memoria clone.
- `[Debug] StartFieldCreator=1` means the game ALWAYS boots into the editor — set back to 0 to play normally.
- Loading an internal field we haven't dumped yet will black-screen (fresh PNG dump to root) — load, quit, relocate PNGs, reload. Only the 5 dumped fields currently work cleanly.
- Walkmesh authoring in Blender is unproven by us — `.obj` → `ConvertToBGI` is code-supported but we haven't round-tripped it.

**Next concrete step (Session 6):**
1. **Confirm the SAVE path end-to-end with a trivial custom field** before involving Blender/painting: in the editor, Load an internal field, immediately Save it as a custom field (e.g. `CUSTOM_FIELD_TEST`), apply the PNG-path workaround, then Load Custom Field to confirm it round-trips. Proves ExportField works.
2. **Then author a minimal NOVEL field:** simplest viable = one flat painted BG overlay + a flat rectangular walkmesh (Blender `.obj`) + one camera aligned via 5-point anchor. Human paints + models; we wire the `.bgx`/paths.
3. Integrate into `FF9CustomMap` + `DictionaryPatch` + warp; verify in-game.
4. Consider documenting the PNG-path bug + workaround for the community (qhimm / Moogles & Mods Discord) — we may be the first to get this editor working.
