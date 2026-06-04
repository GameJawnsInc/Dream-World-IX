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

### 2026-05-28 — Session 6 — Borrowed-camera walkmesh PROVEN; custom room core solved

**The breakthrough:** A novel flat-floor field's hard problem is the CAMERA, not the walkmesh. The editor's 5-point anchor is mathematically degenerate for a flat floor (all walkmesh verts y=0 → rank-deficient solve → 5th point blows the matrix up → walkmesh flies off-screen). Confirmed in source (`PointScreenAnchor.PerformAnchorOnCamera` + `Math3D.SolveMatrixEquation`). Dead end. **Solution: borrow a real room's matched camera + walkmesh region instead of solving one.**

**Done:**
- Read the projection pipeline (`PSX.CalculateGTE_RTPT_POS`, `BGCAM_DEF.GetMatrixRT`, `FieldMapActor` shader) + the anchor solver — diagnosed the flat-floor degeneracy precisely.
- Had user Load Internal Field `FBG_N21_GRGR_MAP420_GR_CEN_0` (cleanest sample: symmetric ~50° 3/4 tilt, 7 overlays) and Save as custom field `ROOM01_BASE` → harvested its REAL matched camera + walkmesh.
- Found our prior placeholder camera was a de-tuned GRGR (wrong Position.Y -160 vs -248, Range 320×267 vs 384×448, Viewport) — a big reason alignment failed before. Preserved GRGR's verbatim camera + real walkmesh in `mod/custom-room-01/borrowed-grgr/`.
- Swapped GRGR's walkmesh for a rectangle inside its framed region (X±800, Z -900..300, 3×3 grid), kept GRGR's camera + real bg, deleted stale `.bgi.bytes`. One-variable test.

**Human verified (screenshot):** Real GRGR bg renders; rectangular custom walkmesh lies **flat on the floor in correct perspective**; Zidane **stands on it naturally** and moves in-plane. ✅

**What this proves:** custom walkmesh + borrowed matched camera = a correctly-rendered, walkable custom floor. The editor's broken anchor is fully bypassed. Core of a playable custom room. Recipe + canvas facts in project memory `project-ff9-novel-bg-pipeline` (Session 6 section).

**Canvas facts for art wiring:** logical canvas 384×448; PNGs 4× upscaled (full layer 1536×1792). Overlay Position=top-left logical px (Y down), Size=px/4, Z=depth (smaller=in front of char). Floor sits canvas Y~240-416.

**Open issues / risks:**
- `[Debug] StartFieldCreator=1` still set — game boots into editor; reset to 0 to play.
- ROOM01_BASE proven only in the EDITOR — not yet in actual gameplay via DictionaryPatch + warp.

**Next concrete step (Session 7):** Pick one — (A) **Art swap:** human paints a full-canvas 1536×1792 background matched to GRGR's perspective (floor lower ~40%; optional separate foreground layer w/ small Z for front-wall occlusion), I wire it into a `.bgx` with GRGR's camera + our rect walkmesh. (B) **Prove in-game:** register the custom field (DictionaryPatch FieldScene) + point the field-70 warp at it + confirm it loads in real gameplay, not just the editor.

### 2026-05-28 — Session 7 — FULLY PLAYABLE custom room IN-GAME (complete end-to-end)

**Chose (B) prove in-game — and nailed it.** A minted custom field (id 4000) with a borrowed GRGR camera + our own rectangular walkmesh now renders, moves, and is fully walkable in REAL gameplay. Likely the first fully-playable minted custom field with custom geometry in FF9.

**Done (all on branch `session7-ingame-custom-scene`):**
- Traced the runtime load path: `BGSCENE_DEF.LoadResources` auto-uses `FieldMaps/<FBG>/<FBG>.bgx` if present (pure-Memoria scene); walkmesh loads from `<FBG>.bgi.bytes` via `BGI_DEF.LoadBGI`. Both keyed by the FBG name.
- Assembled `FF9CustomMap/.../FieldMaps/FBG_N11_ROOM01_BASE/` = `.bgx` (GRGR cam + overlays) + 7 PNGs + our `.bgi.bytes`. DictionaryPatch field 4000 → `FieldScene 4000 11 ROOM01_BASE CUSTOM_FIELD_001 1073` (unique name, no real-field collision). `StartFieldCreator=0`.
- **Fixed movement rotation:** binary-patched the TWIST opcode `SetControlDirection -60,-60 → -1,-1` (=0°, standard WASD) in all 7 language `EVT_CUSTOM_FIELD_001.eb.bytes` (`67 00 C4 C4 → 67 00 FF FF`). The -60 was the Hangar tuning; GRGR's camera is yaw-free.
- **Fixed walkmesh "invisible walls":** `ConvertToBGI` links triangle neighbors unreliably (order-sensitive Edge equality) → diagonal became a wall, trapping the player in a triangle. Wrote `tools/bgi_fix_neighbors.py` to rebuild ALL neighbor links + edgeClones from shared-vertex analysis (convention reverse-engineered from HW's working walkmesh). Re-deployed the patched `.bgi`.

**Human verified (in real gameplay, step by step):**
- Custom room renders clean (GRGR Alexandria-castle bg placeholder; minor 1px overlay-seam tearing). ✅
- Party normal (Zidane), menu works. ✅
- WASD standard (W up / S down / A left / D right) after the TWIST fix. ✅
- **Entire rectangle walkable, diagonal no longer blocks, perimeter still stops you** after the .bgi neighbor fix. ✅

**What this proves — the complete novel-custom-field recipe (all in project memory `project-ff9-novel-bg-pipeline`, Session 7 section):** mint field ID → borrow a real room's matched camera + framed region → author a custom walkmesh `.obj` in that region → editor Save to get `.bgi.bytes` → run `bgi_fix_neighbors.py` → assemble `FieldMaps/<FBG>/` (.bgx + PNGs + .bgi.bytes) + DictionaryPatch + warp → set TWIST for the camera. Reproducible.

**Open issues / risks (carry-over cleanup):**
- Debug warp field 70→4000 still active; field 50 opening still skipped.
- `StartFieldCreator` toggles between 0 (play) and 1 (editor) each walkmesh iteration — friction; `bgi_fix_neighbors.py` reduces editor trips.
- Minor 1px overlay-seam tearing (cosmetic, deferred).
- Branch `session7-ingame-custom-scene` not yet merged.

**Next concrete step (Session 8):** Now it's all content. (1) Human paints real BG art matched to GRGR's camera (1536×1792, floor lower ~40%, optional foreground layer w/ small Z for occlusion) → I wire into the `.bgx`. (2) Then NPCs/dialogue/triggers in the script, an encounter + BtlEncountBGMMetaData + battle-bg dict entry, and a real entrance/exit to a world field. Consider documenting this recipe for the community (qhimm / Moogles & Mods) — likely the first public FF9 fully-playable minted custom field.

### 2026-05-29 — Session 8 — Human-painted art + walkmesh-to-floor alignment + occlusion ALL working in-game

**The room is now visually real.** Field 4000 renders the human's own painted layers (back/floor/front PNGs), the walkmesh is aligned to the painted floor, movement is correct, and the front wall correctly occludes the player. Complete novel-art custom room, in real gameplay.

**Done:**
- Wired the human's 3 painted RGBA layers into `FBG_N11_ROOM01_BASE.bgx` as overlays: back (Position 0,0,4000 Size 384,314), floor (0,165,3000 Size 384,283), front (0,385,8 Size 384,63). Shader `PSX/FieldMap_Abr_None` (texkills alpha<0.1 → respects painted transparency). Kept the GRGR matched camera verbatim.
- **Solved walkmesh↔floor alignment by direct `.bgi` editing (no editor round-trips).** Built `tools/bgi_set_quad4.py` (4 arbitrary corners, y=0, recomputes tri centers) + reused `bgi_fix_neighbors.py`. Iterated the trapezoid against user screenshots until it matched the painted floor.
- **Derived the projection numerically** from `PSX.CalculateGTE_RTPT_POS` + `BGCAM_DEF.GetMatrixRT` + the GRGR camera, then FIT it to two user calibration points (walkmesh z=340 → painted-canvas Y165 floor seam; z=−1188 → canvas Y273 floor front). Resulting closed form: `screenY(z) = (0.7109375·z + 248)·497/(0.6477051·z + 5018) − 112`, then `canvasY ≈ −0.9247·screenY + 104.89`. This lets me solve for the exact z of any painted-canvas row — no more guessing. Used it to push the front edge to z=−3344 = canvas Y448 (floor bottom, under the wall). Final verts: v0(−1142,0,340) v1(−3,0,340) [back] v2(1465,0,−3344) v3(−1799,0,−3344) [front].

**Human verified (real gameplay):**
- Renders the painted art clean. ✅
- Walkmesh matches the visible floor ("you nailed it fitting the visible orange floor"). ✅
- Player walks down under the front wall and the **front wall PNG draws over him — occlusion works**. ✅
- He stays on-screen, visible until hidden by the wall (expected). ✅

**What this proves:** the full novel-custom-field pipeline is DONE — mint ID → borrow matched camera → human paints layers → wire overlays w/ depth → align walkmesh to painted floor via the projection formula → fix neighbors → occlusion via a near-Z foreground overlay. Geometry/art/movement/occlusion all solved. Captured in project memory `project-ff9-novel-bg-pipeline` (Session 8 section). Tagged `KNOWN_GOOD-s8-room-playable`.

**Open issues / risks (carry-over):**
- Debug warp field 70→4000 still active; field 50 opening still skipped. (Cleanup before any release.)
- On entry: inherited 1357-script junk fires a "Nothing more inside." popup over black before the room loads — to be removed when we author a clean `Main_Init`.
- Minor 1px overlay-seam tearing (cosmetic, deferred).
- Branch `session7-ingame-custom-scene` still not merged.

### 2026-05-29 — Session 9 — Clean entry DONE; content-script pipeline (edit-1357 → reclone) proven

**Done:**
- Removed the inherited "Error Env Play()" / "Nothing more inside." entry popup and baked the movement fix into source. **Key discovery: HW does NOT track minted custom fields (4000) in its Fields panel** — they exist only as our DictionaryPatch line + mod-folder `EVT_CUSTOM_FIELD_001.eb`. So the script pipeline for our custom field is: **edit the base field it was cloned from (1357) in HW → "Export as Custom Field" (which writes straight into `FF9CustomMap`) → it regenerates `EVT_CUSTOM_FIELD_001.eb`**. No runtime text→.eb path exists (DataPatchers.cs:441 always loads the compiled `.eb`).
- User edited field 1357's `Main_Init` inline in HW: deleted both `WindowAsync(6,0,62)` popup blocks + `SetControlDirection(-60,-60)→(-1,-1)`. Re-exported.
- **Built an `.eb` opcode verifier** from Memoria's `EventEngineUtils` tables (opArgCount/opArgSize). Key opcodes: TWIST=0x67 `SetControlDirection` (`67 00 FF FF` = -1,-1), MESN=0x20 `WindowAsync` (`20 00 06 00 3E 00` = (6,0,62)), MESVALUE=0x66, RAISE=0x8E, WAITMES=0x54. Verified all 7 languages: TWIST(-1,-1)=1, TWIST(-60,-60)=0, WindowAsync=0. DictionaryPatch unaffected (HW shows the area-57 line in its dialog but did NOT overwrite our file).

**Human verified (real gameplay):** Clean load — **no popup**, standard WASD movement, room renders. ✅ Tagged `KNOWN_GOOD-s9-clean-entry`.

**Notes for content work:**
- The reclone overwrites `FF9CustomMap` content but NOT our `FBG_N11_ROOM01_BASE` art (HW writes a separate unused `FBG_N57_...`). Re-verify DictionaryPatch after each export (keep `mod/FF9CustomMap-DictionaryPatch.txt` as the source of truth).
- Do NOT "Save Steam Mod" after editing 1357 (that would push 1357 edits to the live Hangar) — "Export as Custom Field" alone is enough.
- **Open question for NPCs/dialogue:** field 4000 uses MES text id **1073** (borrowed/shared base-game text — Session 3 found it resolves to unrelated end-game lines). Authoring our own dialogue needs either our own MES or a remapped mesID. Resolve when adding the first NPC.

**Next concrete step:** First NPC on field 1357 (→ reclone): a `#HW newentry` with `_Init` (SetModel/CreateObject/idle anim/position) + `_SpeakBTN` (TurnTowardObject + dialogue window), using the LibrarianA pattern in `reference/field-0109-alexandria-wpn-shop.txt`. Sort out the text/MES plumbing as part of it.

---

#### (Original Session 9 plan — content)
Geometry is locked; everything left is script/data I can own.
1. **Clean `Main_Init`:** remove the inherited popup, confirm player object = Zidane, set the room's flags/state cleanly on entry. **(DONE — see Session 9 above.)**
2. **First NPC** (LibrarianA pattern from `reference/field-0109-alexandria-wpn-shop.txt`): SetModel + CreateObject + idle anim + a `_SpeakBTN` with one line of our dialogue.
3. **Region trigger** that pops a window (proves trigger plumbing).
4. **Encounter** + `BtlEncountBGMMetaData.txt` entry + battle-background dictionary entry.
5. **Real entrance/exit** wiring to a world field (replaces the debug warp).
Each = one commit + one in-game verification. Decide the room's narrative identity first (drives NPCs/dialogue/encounter theme/where it connects).

### 2026-05-29 — Session 9 (cont) — Python `.eb` injection PROVEN; HW out of the script loop

**The unlock:** we can now author field-script content (NPC entries, and by extension dialogue/triggers/exits) **directly into the compiled `.eb` in Python, fully byte-verified, with NO Hades Workshop.** First in-game-confirmed Python-injected NPC.

**Why HW was abandoned for scripts:** importing a *new* NPC entry into field 1357 + "Export as Custom Field" produced a CORRUPT `.eb` (disassembler-confirmed: size unchanged 956, entry1=Zidane `type` 2→255, entry2 off=512 overlapping entry1, NPC func table `fpos=33168` out of range). HW reused 1357's 10-slot entry table (empty slots parked at off=512) and overwrote the player object instead of appending. HW's custom-field export can MODIFY existing functions (the clean-entry edit worked) but cannot ADD an entry. Author is retired → won't be fixed.

**Tools built (reusable, in `tools/`):**
- `eb_disasm.py` — full field `.eb` disassembler. Parses Memoria's `EventEngineUtils` opcode tables (`opArgCount`/`opArgSize`) + `DoEventCode` opcode names *directly from source* (no transcription). Walks BinaryScript→Entry→Function→Code. **Key format facts:** header 44B + PSX name 84B → entry table at offset 128 (10 slots × 8B: off2,sz2,loc1,fl1,pad2); entry = type1,funcCount1,[tag2,fpos2]×fc, then code; **`funcBasePos = entryStart+2`** (fpos measured from BEFORE the func table); 2-byte opcodes prefixed 0xFF. Key opcodes: InitObject(NEW3)=0x09 args[1,1]; Wait=0x22 args[1] (3B `22 00 NN`); SetModel(MODEL)=0x2F args[2,1]; CreateObject(POS)=0x1D args[2,2]; SetStandAnimation(AIDLE)=0x33 arg[2]; DefinePlayerCharacter(CC)=0x2C (0 args); NOP(NOTHING)=0x00; WindowSync(MES)=0x1F args[1,1,2]; WindowAsync(MESN)=0x20; TWIST=0x67.
- `eb_inject_npc.py` — injects an NPC object entry WITHOUT shifting bytecode: clones the known-good Zidane object entry (file 640..956, 316B) as entry2, NOPs its DefinePlayerCharacter, repositions (x@658/z@666), appends it + sets entry2's table slot (off,sz), and **spawns it by overwriting one Main_Init `Wait(2)` (offset 458, `22 00 02`) with `InitObject(2,0)` (`09 02 00`) — identical length, so no shift and no jump relocation.** Asserts expected bytes per-file before patching (all 7 langs share identical bytecode regions).

**Human verified (real gameplay):** a second (static) Zidane stands in the room at (400,−1400); player Zidane controllable, movement/occlusion intact, no crash. ✅ Tagged `KNOWN_GOOD-s9-npc-injected`.

**Open for next steps:**
- The injected NPC is a placeholder using the **Zidane model** (guaranteed-valid anims). To make it a real NPC: swap model→21 (LibrarianA) + patch its 5 anim IDs (Stand 2494/Walk 2501/Run 2501/Left 2499/Right 2497); footstep RunModelCode is inert for an idle NPC.
- **Talk dialogue still needs the text/MES plumbing solved** — field 4000 reads MES id **1073** (a shared base-game block); custom lines need our own MES or a remapped mesID. This + assembling a `_SpeakBTN` (has conditionals/expressions) is the next real problem.
- Carry-over: debug warp field 70→4000 active; field 50 opening skipped.

### 2026-05-29 — Session 9 (cont 2) — Custom TALKING NPC (Vivi + our dialogue) — full content pipeline DONE

**The whole content pipeline now works end-to-end, in real gameplay, zero Hades Workshop:** a custom NPC (Vivi) with correct model+animations, a working talk trigger, and **our own authored dialogue line** ("I miss you Zidane").

**Done (all via `tools/eb_inject_npc.py` + a mod MES file):**
- **Talk trigger:** added a `_SpeakBTN` (funcTag 3) to the injected NPC entry — `WindowSync(1,128,<textid>) ; return(0x04)`. The injector rebuilds the NPC entry with 3 functions (Init/Loop/SpeakBTN), recomputing the func table (func0/func1 shift +4 for the extra slot). Human-verified: facing the NPC + action opens a dialogue window. ✅
- **Vivi model+anims:** injector `vivi` preset — SetModel(8,61) + patch the 5 anim-setter args to Vivi's (Stand 148/Walk 571/Run 419/Left 917/Right 918) in-place in the cloned func0. Human-verified: NPC is Vivi, idles correctly. ✅
- **Custom dialogue TEXT — SOLVED.** Field text loads cumulatively across mods from `<mod>/FF9_Data/embeddedasset/text/<lang>/field/<mesID>.mes` (FF9TextTool.ImportStrtWithCumulativeModFiles → AssetManager.LoadStringMultiple; base processed last, so base wins per-index). The `.mes` format supports explicit `[TXID=<n>]` indices. So: drop a mod `1073.mes` with our line at a **high index the base block doesn't use** → base text untouched, our entry added. Content (all 7 langs): `_[TXID=500][STRT=10,1][TAIL=UPR]I miss you Zidane[ENDN]` (leading non-`[STRT=` char so the TXID is parsed as a re-index, not entry 0 — verified by simulating ExtractSentense: produces ONLY index 500). Repointed the NPC's `WindowSync` 62→500. Human-verified: NPC says "I miss you Zidane", window positioned fine. ✅

**Tagged `KNOWN_GOOD-s9-talking-npc`.** Recipe in project memory `project-ff9-eb-script-tooling` (custom-text section).

**What's proven now (the full custom-room toolkit):** mint field → borrow camera → human art + walkmesh + occlusion → clean entry → inject NPCs (any model+anims) → talk triggers → **custom dialogue text** — all in Python, all verified by `eb_disasm.py` before deploy, no HW for any of it.

**Next (to make it a real, reachable place):** replace the debug warp (field 70→4000) with a real entrance from a world field + an exit back; optional encounter (+BtlEncountBGMMetaData + battle-bg dict) and more NPCs/triggers.

### 2026-05-29 — Session 10 — Novel-camera MATH cracked (Phase 1: read/decompose/synthesize ANY camera)

**Strategic pivot (user's call):** Stepped back to ask what we're really building. User chose to **crack the novel-camera math** — author a camera for ANY angle from scratch, instead of only borrowing a real room's matched camera (the Session-6 workaround, forced because the editor's 5-point anchor solver is mathematically degenerate for flat floors). This is the gate to truly arbitrary novel geometry+perspective.

**Done (all offline, no game — pure code/data/math, squarely in my lane; only final in-game alignment is Hard-Constraint §2 human's):**
- Read the exact projection pipeline from Memoria source: `PSX.CalculateGTE_RTPT_POS` (PSX.cs), `BGCAM_DEF.GetMatrixRT`/`ReadData` (BGCAM_DEF.cs), the `.bgx` CAMERA parser + exporter (BGSCENE_DEF.cs). **Confirmed player/walkmesh screen position = `CalculateGTE_RTPT_POS(worldPos, identity, GetMatrixRT(), proj, centerOffset)` — `FieldMapActor.cs:121`** (localRTS = identity). The projection that places the player is exactly the one that must place the walkmesh on the painted floor.
- **Found the invariant (the whole secret):** `R_ff9 = diag(1, k, 1)·R_ortho`, R_ortho a proper orthonormal rotation, **k = 14/15 = 0.93333… a global constant** baked into orientation-matrix row 1 (vertical-focal aspect correction; the GTE has one projection distance H for both axes). Verified across 6 real cameras (GRGR, TSHP×2, BSHP, GZML, TRNO) spanning 3/4-tilt, 90° yaw, oblique, inverted: row0 & row2 norms ≈ 1.000, **row1 norm ≈ 0.9333 every time**, mean 0.933332.
- Built `tools/cam_lib.py` (pure stdlib): exact GTE `project()`, `decompose()` (recovers k, orthonormal R_ortho, camera world pos C, R_view, FOV), `synth_r_t()` (inverse: byte-faithful Int16 r[][]+t[] from C/R_ortho/H), `.bgx` parse/format. Derived `t = -R_ff9·(F·C)` ⇔ `C = -F·R_ff9⁻¹·t` (F = diag(1,-1,1) y-flip).
- Built `tools/test_cameras.py` (6 cameras hardcoded). **ALL CHECKS PASS:** ortho_err ~1e-4 (quantization), det +1 for all (proper rotations), synthesis round-trips r/t to ≤1 Int16, clean pinhole form reproduces engine GTE projection to ~1e-13. GRGR floor cross-check reproduces Session 8 calibration (z=340→screen.y 46.46; z=−1188→−69.79).

**What this proves:** read / decompose / re-synthesize ANY FF9 camera, byte-faithful + projection-exact, zero in-game iteration. The Session-6 dead end (degenerate editor solver) is fully bypassed. Captured in project memory `project-ff9-camera-math`. (No KNOWN_GOOD tag — nothing shipped to game yet; this is offline tooling.)

**What's left:**
- **Phase 2 (for novel ART):** canvas↔GTE-screen linear map (scale `a` + offsets) → emit the exact Blender camera (lens/sensor/resolution) whose render aligns with the GTE projection. Session 8 found GRGR's vertical map ≈ −0.929·screenY_raw + ~208 on the logical 384×448 canvas; Phase 2 = DERIVE `a` from camera params (read FieldMap camera/Unity-cam + overlay placement) and reproduce that number.
- **Phase 3 (human, in-game):** decisive proof. Lowest-risk first test = regenerate an existing camera via `synth_r_t`, confirm room UNCHANGED in-game (validates write path in real engine, isolates synth from art). Then a true novel angle with matching art (needs Phase 2).

**Human verified (in-game, user chose route B):** regenerated room 4000's camera via the new tool (`tools/regenerate_room_camera.py`: read .bgx → decompose to C=(0,3651,-3454)/pitch 49.6°/FOV 42.2° → `synth_r_t` → rewrite). OrientationMatrix byte-identical; Position z 5018→5019. **User confirmed the room renders UNCHANGED** → the synthesis write-path is engine-valid, not just Python-valid. Original backed up at `backups/FBG_N11_ROOM01_BASE.bgx.20260529-185605`. Tagged `KNOWN_GOOD-s10-camera-synth`.

**Next concrete step:** Phase 2 — derive the canvas↔GTE-screen linear map (scale `a` + offsets) from FieldMap camera/Unity-cam + overlay-placement source, validated by reproducing Session 8's GRGR vertical map (≈ −0.929·screenY_raw + ~208 on the 384×448 canvas). That yields the exact Blender camera (lens/sensor/resolution) for matching novel art → unblocks Phase 3b (a true novel angle, human paints to match, verified in-game).

### 2026-05-29 — Session 10 (cont) — Phase 2 cracked: the canvas↔screen map (reproduces Session 8 to <0.1px)

**Done (offline, from source — read FieldMap.cs camera setup, the FieldMapActor `.txt` vertex shader, and BGSCENE_DEF CreateScene_Background/OverlayGo):**
- **Found the real projection offset** the engine passes to the GTE (`FieldMapActor.cs:121` → `FF9.projectionOffset`, built in `FieldMap.cs:393-406`): `offX = centerOffset.x + w/2 − HalfFieldWidth`, `offY = −centerOffset.y − h/2 + HalfFieldHeight`. For GRGR = (32, −112). **The `−112` is exactly Session 8's mystery constant.** My `cam_lib.project()` had been using raw centerOffset — corrected (added `compute_offset` + `project_screen`).
- **Depth** confirmed from the shader (`mad r2.x, r2.x, 0.25, _DepthOffset`) + FieldMapActor.cs:122: `result.z/4 + depthOffset`.
- **Canvas map derived:** `canvasX = projectedPos.x + HalfFieldWidth`, `canvasY = −projectedPos.y + HalfFieldHeight` (clean scale-1 both axes), times a SINGLE global ortho scale `s` (the "FieldMap Camera" ortho scale — a Unity prefab value not in C# source, hence the same for every room). **Session 8's two trusted floor points pin `s = 0.929` cleanly through the origin** (canvasY 164.93 vs 165; 272.93 vs 273 — both exactly 0.929·derived, no separate intercept; likely 13/14 = 0.92857).
- Added to `cam_lib.py`: `compute_offset`, `project_screen`, `depth`, `to_canvas(P)` (world→painted-canvas px), `solve_z_for_canvasY(row)` (inverse — auto-replaces Session 8's hand-fitted walkmesh placement). `test_cameras.py` now reproduces Session 8 to <0.1px AND all 6 camera checks still pass.

**What this gives us:** for ANY authored camera angle, I can now tell the human exactly where the floor/walls/features will sit on the painted canvas, and place the walkmesh on their painted floor automatically — no per-room hand-calibration (Session 8 did this by hand for one camera; now it's a formula for all).

**Open (small):** pin `s` precisely (0.929 vs 13/14) and confirm it's truly global, via ONE clean in-game calibration: place walkmesh verts at known (x,0,z), human reports the exact canvas pixel the feet rest on, 3-4 well-spaced points. `s=0.929` already works (Session 8 used it); this just refines + de-risks for novel rooms.

**Next concrete step:** Phase 3b — build a TRUE novel-angle room: I author a new camera (e.g. different pitch/yaw), use `to_canvas`/`solve_z_for_canvasY` to give the human a paint guide + place the walkmesh, human paints art to match, verify alignment in-game. (Optionally do the clean `s`-calibration as part of the same playtest.)

### 2026-05-31 — Session 10 (cont) — Phase 2 + 3b DONE: novel-angle camera authored, calibrated, walkable in-game

**The whole novel-camera goal is now achieved end-to-end.** A brand-new camera angle (65° top-down, vs the old room's 49.6°), authored from scratch via the math, with a walkmesh that lands pixel-accurate on the projected floor — confirmed in real gameplay. Likely the first FF9 custom field at a from-scratch-authored camera angle.

**Done:**
- **Phase 2 (canvas↔screen map) cracked from source + CALIBRATED in-game.** Read the actor shader (`FieldMapActor.txt`) + `FieldMap.cs` camera setup + `BGSCENE_DEF` overlay placement. EXACT pieces: projectionOffset = `(cx + w/2 − HalfFieldW, −cy − h/2 + HalfFieldH)` (the engine passes THIS to the GTE, not raw centerOffset; its `−112` is Session 8's mystery constant); depth = `result.z/4 + depthOffset`; overlay world placement `(canvasX − HalfW, HalfH − canvasY)`.
- **Built `tools/cam_lib.py` canvas API:** `compute_offset`, `project_screen`, `depth`, `to_canvas`, `solve_z_for_canvasY`.
- **Built a clean in-game calibration** (`tools/build_room02_calib.py`): a perspective checkerboard floor as the BG + a walkmesh of the SAME world corners, deployed as field 4000 via a DictionaryPatch mapid swap (`ROOM01_BASE → ROOM02_TD`; room01 untouched, one-line revert). Iterated against the player walking to each edge:
  1. top/bottom gaps → vertical scale **sy = 0.889** (least-squares; Session 8's 0.929 was a freehand back-fit, ~4% off).
  2. sides uniformly shifted → my X scaled about the canvas CORNER not the MIDPOINT → **center X at w/2**.
  3. sides then symmetric-over → X scale ≠ Y scale → horizontal scale **sx = 0.926**. The field ortho camera is non-square.
- Final map: `canvasX = w/2 + sx·(projX − offX)`, `canvasY = sy·(−projY + HalfH)`. All 6 camera checks still pass.

**Human verified (in real gameplay, step by step):** renders the steeper top-down ✓; spawns on the floor ✓; WASD correct ✓; after the sx/sy + centering fixes, **all four walkmesh edges land on the drawn floor lines — "nailed it"** ✓.

**What this completes:** the full novel-custom-field pipeline now includes ARBITRARY camera angles. Recipe: author camera (`synth_r_t` from pitch/yaw/pos/FOV) → frame the floor + emit a pixel-accurate paint guide (`to_canvas`/`solve_z_for_canvasY`) → build the walkmesh in that frame → human paints to the guide → walkmesh aligns. Captured in project memory `project-ff9-camera-math` (Phase 2/3b sections). Tagged `KNOWN_GOOD-s10-novel-camera`.

**Open issues / risks (carry-over):**
- Field 4000 currently loads the ROOM02_TD **calibration grid** (not room01's painted art). To restore the talking-Vivi room: revert the DictionaryPatch line `ROOM02_TD → ROOM01_BASE` (or `backups/DictionaryPatch.txt.20260529-194021`).
- Debug warp field 70→4000 still active; field 50 opening still skipped.
- Both axes' scales (sx=0.926, sy=0.889) pinned on ONE camera (room02). Assumed global (the FieldMap Camera is one prefab) — re-confirm opportunistically on a different angle.

**Next concrete step:** paint the REAL steeper-top-down room. I regenerate a clean paint guide for the deployed walkmesh (fixed corners, calibrated map) → human paints floor + walls to it → I swap the grid BG for the painted layers (same camera/walkmesh) + add depth overlays for occlusion → verify in-game. Then content (NPCs/dialogue/exits) as in the room01 pipeline.

### 2026-05-31 — Session 10 (cont) — Calibration validated across the REAL FF9 angle range

**Done:** Stress-tested the canvas calibration with checkerboard grid rooms at multiple pitches (each = field 4000 via DictionaryPatch mapid swap, global `sx=0.926/sy=0.889`, NO re-tuning):
- **room02 (65°):** all four edges pixel-perfect.
- **room03 (75°):** sides + front perfect, but back drifts ~1/8–1/4 sq (feet past the line). Investigated hard — ruled out body-height (computed) and depth-coupling (fit it; would throw the front off ~200px). It's a small pitch-dependent vertical nonlinearity at steep/far edges.
- **Found the REAL range:** decomposing the 6 real FF9 cameras, downward pitch spans ~0–48° (GRGR steepest ~48°, most 15–28°). So 65° and 75° are both STEEPER than anything FF9 ships — we'd been stress-testing out of range.
- **room04 (48°, the real steep end = GRGR's angle):** back edge "a little short, reasonable" (user-accepted); sides/front good.

**Conclusion:** the back-edge residual is ZERO at the 65° calibration point and grows away from it (48°=slightly short, 75°=clearly past) — a real but small pitch-dependent term. It's REASONABLE across the entire real FF9 range (≤48°) and irrelevant in practice (back edge = wall, occlusion-hidden). `sx` is global on every tested angle. For a dead-on back at a chosen angle, re-pin `sy` with one grid check at that pitch. **Calibration declared good for all real-range rooms.** Tagged `KNOWN_GOOD-s10-calib-validated`.

**Carry-over:** field 4000 currently loads ROOM04_TD calibration grid. To restore the talking-Vivi painted room: revert DictionaryPatch `ROOM04_TD → ROOM01_BASE`. Debug warp 70→4000 still active.

**Next:** PAINT the real room. User picks the angle (real range ≤48° for FF9 authenticity, or 65° steeper — both calibrated). I emit a pixel-accurate paint guide for that camera + the walkmesh; human paints floor+walls; I wire the painted layers (same camera/walkmesh) + depth overlays for occlusion; verify in-game. Then NPCs/dialogue/exits.

### 2026-05-31 — Session 11 — Two painted hut rooms connected (gateways) + first working encounter w/ after-battle fix

**Massive content session. Built "Vivi's Return" (exterior 4000) + "Vivi's House" (interior 4002): two human-painted 48° rooms, a working door round-trip, Vivi NPC, and the game's first random encounter on a minted custom field — including cracking the post-battle softlock.**

**Done (all in-game verified):**
- **Interior layout:** repositioned player spawn + Vivi via `tools/build_interior.py` (clean script → inject Vivi → move player → inject exit gateway). Reproducible.
- **Gateways (round-trip):** `tools/eb_inject_gateway.py` clones field 109's exit region. Door (exterior back → 4002) + exit (interior front → 4000). **3 gotchas cracked** (memory `project-ff9-gateway-regions`): (1) region triggers only run when `usercontrol==1` (the `GetUserControl()` gate in ProcessEvents); (2) `IsInQuad` (TreadQuad.cs) tests a FAN of consecutive vertex-triplets, NOT the real polygon — 3 collinear points ⇒ a zero-area triangle ⇒ a DEAD ZONE; fix = convex quad with the last vertex DOUBLED (offline-sim verified 210/210 coverage); (3) the player must REACH the zone (place it where he demonstrably stands, not just inside the walkmesh). Isolation method that cracked the "exit won't fire": diff vs the working door (byte-identical ⇒ not the region) → mirror door exactly (no Vivi, entry 2) → raw-warp vs gateway entry → spawn-covering zone FIRED ⇒ it was reach/placement, not mechanism. **Bisect variables, don't theorize.**
- **Exit walk-out:** `CalculateExitPosition`+`ExitField` walk the player toward the polygon's q[0]→q[1] edge; point ORDER controls direction (front edge first = walk forward, no "circle"). Centre-exit "running in place" = walk target too far for the fade (deferred, cosmetic).
- **Encounter:** `tools/eb_inject_encounter.py` appends a type-0 code entry `{SetRandomBattles(1,67×4); SetRandomBattleFrequency(255); return}`, activated via `InitCode(3,0)` over a Wait filler. Scene 67 = Evil Forest/Trail (game's first/weakest battle; user-corrected from my Ice-Cavern guess). Triggers, correct enemies, winnable, XP. ✓
- **Post-battle softlock — FIXED.** Returning to a custom field after battle froze (renders, no control). Root cause (Memoria source via a research subagent): `EnterBattleEnd()` suspends all objects; they only resume when entry-0's **tag-10 "Main_Reinit"** returns at level 0 (→ `ExitBattleEnd`). Cutscene-cloned fields (1357) lack tag 10. Fix `tools/eb_add_reinit.py`: re-lays-out the .eb to add an entry-0 tag-10 func `EnableMove; return` (grows func table, shifts entry0 code +4, relocates entries 1+). Disasm-verified, in-game-confirmed: **control restored after battle.** Memory `project-ff9-encounters`.

**Human verified:** round-trip door in/out both ways; Vivi placement; battle triggers + winnable; **control returns after battle**; repeatable (limited only by solo-Zidane HP, not a bug). Tagged `KNOWN_GOOD-s11-interior-layout`, `KNOWN_GOOD-s11-encounter-return`.

**Open / deferred:** battle music silent (needs `BtlEncountBgmMetaData.txt` mod entry); battle-return fade slow (custom-field atlas rebuild each load); centre-exit run-in-place animation; debug warp 70→4000 still active (field 50 opening skipped); encounter frequency maxed (can lower); not yet wired into the real game world.

**Next:** options — battle BGM; lower encounter frequency; wire a real-world entrance (replace debug warp); more NPCs/story/dialogue; polish (transition/seam). The full custom-field toolkit (mint → camera → paint → walkmesh → NPCs → dialogue → gateways → encounters w/ clean return) is now COMPLETE and reproducible in Python.

### 2026-06-01 — Session 12 — Local Memoria engine build stood up; fade-cache + booster edits built & deployed (NOT yet playtested)

**Context:** Two pains (slow battle-return fade; slow test battles) both needed engine changes. User OK'd the recompile path, then went to sleep with: *"if you get through Phase A and feel confident, feel free to continue. I'll review in the morning."* So this was an autonomous, offline-only session — no in-game verification yet. Plan file: `C:\Users\skaki\.claude\plans\sunny-zooming-bonbon.md`.

**Done (all offline; recipe + gotchas in project memory `project-ff9-memoria-build`):**
- **Stood up a local Memoria build.** MSBuild = VS18 BuildTools (amd64). Copied the Unity/framework ref DLLs from the game's `x64\FF9_Data\Managed\` into `Memoria\References\` (the repo set is encrypted in `Dependencies.7z`). **Key build quirk:** build the csproj with `/p:SolutionDir=C:\gd\FFIX\Memoria\` (trailing `\`) — without it `$(SolutionDir)` is undefined → `FrameworkPathOverride` breaks → machine v4.0 mscorlib conflicts (CS1703/CS0433) in Memoria.Prime/UnityEngine.UI. (Global `/p:NoStdLib` is the WRONG fix — breaks XInputDotNetPure.)
- **Version-matched to the install.** `Memoria.log` → installed Memoria compile-date = **2025-07-13**; that's the assembly auto-date, not a tag. Checked out the nearest `main` commit **`6b8bb2d5`** so the rebuilt `Assembly-CSharp.dll` is API-compatible with the installed `Memoria.Prime.dll` (canary main is ~10 months of drift — avoided).
- **⚠ Discovered the build AUTO-DEPLOYS.** The csproj `AfterBuild` runs `Memoria.MSBuild.Deploy`, which finds the game via `FF9_Launcher.exe` and copies the built `Assembly-CSharp.dll`/`Memoria.Prime.dll`/`UnityEngine.UI.dll` into BOTH `x64\`+`x86\` Managed — no backup kept. The baseline (unmodified) rebuild deployed before I could snapshot the original; backed it up immediately after (`backups/*.baseline-rebuild-6b8bb2d5.*`). True original recoverable only by re-running the Memoria patcher.
- **Two engine edits built + deployed** (`memoria-patches/s12-fade-cache+booster-autoenable.patch`):
  - **Fade fix** — `BGSCENE_DEF.cs`: static `Dictionary<String,Texture2D> MemoriaOverlayTextureCache`; the overlay `Image` op reuses a decoded texture by path (self-heals on Unity-null). Kills the per-load PNG re-decode behind the slow/see-through fade. The static ref also keeps overlay textures alive across the battle scene change (UnloadUnusedAssets skips referenced assets; `memoriaImage` is never explicitly Destroyed — verified).
  - **Fast test battles** — `SettingsState.cs` ctor + `Initial()`: seed `IsBoosterButtonActive[1]=Cheats.SpeedMode`, `[3]=Cheats.Attack9999` so the ini-enabled boosters start ON (no F1/F3 each launch). `[4]` NoRandomEncounter left off (want encounters to test the fade).
- **Offline-verified:** clean compile (0 errors); `MemoriaOverlayTextureCache` present in the deployed DLL metadata; game x64+x86 copies byte-identical to build output (5,502,464 B). In-game behavior NOT verified (user asleep).

**Deployed engine state:** edited `Assembly-CSharp.dll` (fade-cache + booster) + baseline-rebuild `Memoria.Prime`/`UnityEngine.UI` + original `XInputDotNetPure`/`Newtonsoft.Json`. Memoria clone left at detached `6b8bb2d5` + the 2 uncommitted edits.

**Earlier this session (before the build):** Flattened the exterior rear layer `ground.png` opaque over user-chosen #2d4739 to kill the fade see-through *appearance* (committed `4be67bd`; user: "looks better now visually" — but the fade was still slow, which is what this engine work fixes).

**Revert/bisect for the morning:** `py tools/restore_memoria_dll.py baseline` swaps the engine back to the no-edits rebuild (isolates my edits from the rebuild itself). Full original = re-run the patcher. Do NOT Steam-"verify integrity" (reverts the Managed DLLs).

**NEXT (needs the human):** Playtest. (1) Game launches & field 4000 behaves normally? (rebuild sanity). (2) Battle-return + door re-entry fade fast & not see-through? (cache). (3) Battles instantly fast with no F-keys? (booster). Report per-item; if anything's broken, run the restore script and say so. Open questions left in chat.

### 2026-06-01 — Session 12 (cont) — Engine build verified; battle music, fade, BGM, New-Game skip, cold-start all SOLVED in-game

Human playtested everything from the overnight build forward; all verified. Big polish session — the room is now a clean, fast, audio-complete experience.

**Done + human-verified (newest commits):**
- **Engine build works in-game** (`820ad51`): fade texture-cache + booster auto-enable rebuild launches & plays normally. Baseline-rebuild is the no-edits revert (`tools/restore_memoria_dll.py baseline`); true original = re-run patcher.
- **See-through fade FIXED** (`4be67bd`): flattened the exterior rear layer (`ground.png`) opaque over user-chosen #2d4739 — surround no longer shows black through the fade. (Appearance fix; the *slowness* was separate ↓.)
- **Slow battle-return fade FIXED — it was a TIMED fade, not perf** (`87ada84`): `BattleResultUI` fires `FF9Wipe_FadeInEx(256)` = a 256-frame timed fade; normal fields' Main_Init issues a quick `FadeFilter(~16)` to override it, but after BATTLE the field runs tag-10 (Main_Reinit), and ours was bare `EnableMove;return`. Fix: `tools/eb_reinit_add_fade.py` prepends `FadeFilter(2,16,0,0,0,0)` to tag-10. The engine texture-cache turned out NOT to be the fade fix (kept anyway, harmless). Memory updated (`project-ff9-encounters`).
- **Battle music FIXED** (`5667230`): `BattlePatch.txt` `Music:` takes the akao **song-play** id, NOT the music-file number — `Music: 6` played Game Over; **`Music: 0`** = Battle Theme. (Same id-space gotcha bit field BGM ↓.)
- **Field BGM = Vivi's Theme** (`300b240`): `RunSoundCode(0, 9)` (`ff9fldsnd_song_play(9)` → music008) added via `tools/eb_add_field_music.py` to the encounter init-entry (on room entry) + tag-10 (after battle). Song id **9**, not file-number 8 (verified vs real fields 100/103). Human: plays on entry + resumes after battle. ✓
- **New Game → field 4000 directly** (`f3f32af`): skips the opening FMV (debug build). Human-confirmed.
- **Cold-start (laggy first map) FIXED via mod file-lists** (`b25f6ac`): root cause was ~9,700 listless mod files → disk-bound asset lookups (`AssetManager` `File.Exists` fallback when `AssetList` empty). One `UseFileList=2` indexing launch generated `ModFileList.txt` for all mods → back to `=1` + **deleted FF9CustomMap's list** (our active mod stays disk-truth = no stale-list footgun; static Moguri/AF lists give HashSet lookups). Map load now fast.
- **Superspeed off-by-default but F1-toggleable** (`ea5d544` + `c292567`): dropped the SpeedMode auto-enable in `SettingsState` (kept Attack9999 auto-on); ini `SpeedMode=1` keeps the F1 hotkey live. Human: F1 toggles. ✓
- **Residual ~8s TITLE lag diagnosed + accepted** (`c292567`): added a temporary frame-hitch logger to `SceneDirector.Update`, captured the profile → ~2-3.7s asset-bundle stall (Moguri/OS-cache variable) + ~6s of dead-regular **GC-flat** ~400ms stalls = **shader/asset compile warm-up** (persists with Moguri OFF → not Moguri, not our field). Title-screen only, never touches gameplay → accepted. Logger removed; engine clean. Memory `project-ff9-memoria-build` covers the build/auto-deploy/version-match gotchas.

**Tags:** `KNOWN_GOOD-s12-fade-fixed`, `-s12-music+newgame`, `-s12-vivi-theme`, `-s12-polish` (current clean engine).

**Engine state (deployed):** Assembly-CSharp = base `6b8bb2d5` + fade texture-cache + Attack9999 auto-on (SpeedMode off/F1-toggle). Patch: `memoria-patches/s12-engine-edits.patch`. ini: `UseFileList=1` (+ static mod lists), `SpeedMode=1`, `Attack9999=1`.

**Carry-over / cleanup before any release:** debug New-Game→4000 skip + field-70 warp still active (field 50 opening skipped); custom field not yet wired into a normal playthrough; engine is a debug build (boosters auto-on).

**Next concrete step:** **wire the real-world entrance** — a gateway from an existing world field into 4000 + an exit back (replacing the debug New-Game skip), so the room is reachable in a normal playthrough. Then optional content (more NPCs/story, a second encounter) and the release cleanup pass.

### 2026-06-01 — Session 12 (cont) — Custom room WIRED INTO ALEXANDRIA (round trip, in-game verified)

**The room is now reachable from the real game world.** Field 4000 ↔ Alexandria Main Street (field 100) round trip works in gameplay: walk out the room's left exit → arrive in Alexandria → walk up the street to a well-placed door → back in the room. Tagged `KNOWN_GOOD-s12-alexandria-entrance`.

**Done:**
- Confirmed `evt_alex1_at_street_a` = **field 100 (Alexandria/Main Street)** by exit fingerprint (its exits `Field(101)/(107)/(114)` match the HW export of field 100). AlternateFantasy ships this `.eb` on disk → **no Hades Workshop needed**; edit AF's copy + deploy as a higher-priority **FF9CustomMap override** (FF9CustomMap is first in FolderNames + listless = disk-truth, so it wins and needs no ModFileList entry).
- Built `tools/wire_alexandria.py`: full-range (entry-count-aware) gateway injector. Clones field 109's proven exit-region TEMPLATE (272 B), appends into a free entry slot, and activates via `InitRegion(slot,0)` inserted at a **jump-safe** offset (grow containing entry + shift later entries; internal fpos are relative so unchanged).
  - **EXIT** HUT 4000 → `Field(100)` ent 204: slot 4, `InitRegion(4,0)` inserted after `InitRegion(2,0)` @465 (HUT Main_Init has NO jumps → trivially safe). Zone = left side of room, clear of the front-center 4002 door. **Entrance 204 = the value field 107 uses to enter 100** → player arrives at a real walkable spot (bottom of Main St).
  - **DOOR** field 100 → `Field(4000)` ent 0: slot 18, `InitRegion(18,0)` inserted after `InitRegion(11,0)` @743 (jump-safe — the only two Main_Init jumps target 752/841, both *past* the insert). Zone = center-left mid-street, away from the 3 existing exits + the from-107 spawn.
- Verified post-inject (disasm): original exits (101/107/114) + cutscene entry 19 intact; all 7 langs identical size (1550 / 13799). Backups: `backups/*.prealexit.*` (HUT) / `*.afbase.*` (field 100).

**Human verified (in-game):** exit-out works; **Alexandria walkable on arrival** (no full cutscene hijack — the festival is flag-gated off); spawn at the normal bottom-of-walkway point; **door back "worked and well placed."** ✅

**Two benign quirks — user chose to LEAVE AS-IS:** entering field 100 via the debug round trip shows (a) **Vivi as the on-screen avatar** (field 100 is the early-game festival field — you canonically control Vivi there; our debug party is Zidane, so model=Vivi but menu=Zidane) and (b) an **"Error Env Play() Slot=0" popup** (a leftover dev *placeholder string* baked into many base fields' text tables — found in `1073.mes`, `121.mes`, `124.mes`, …; NOT an engine error and NOT our code; field 100 surfaces it from its out-of-context festival audio/NPC setup). Neither crashes. Both are **debug-context artifacts** — a story-positioned Disc-4 entrance runs field 100's town-mode (Zidane, no festival, no popup), and our door region runs unconditionally so it works in both modes. Polish deferred to the release pass.

**Open / carry-over:** debug New-Game→4000 skip still active (the round trip currently starts *in the room*, not Alexandria); field 50 opening skipped; engine is a debug build (Attack9999 auto-on). The field-100 override door is permanent in any future real playthrough (intended).

**Next:** options — (a) more room content (NPCs/story/dialogue, a second encounter); (b) a story-positioned *real-playthrough* entrance (replace the New-Game→4000 skip); or (c) begin the release-cleanup pass (remove debug warp, retune door if needed, revisit the quirks).

### 2026-06-01 — Session 12 (cont) — Real-playthrough Alexandria entrance: New Game → walk in → room (fully polished)

**New Game now lands you in a clean, walkable Alexandria and you reach the room by walking to a door** — no more New-Game→room skip. Full in-game-verified loop: New Game → Alexandria (Vivi's Theme, bottom-of-walkway spawn) → walk up to the door → room 4000 → interior 4002 → room → back out the door, **stepping out right at the Alexandria door**. Tagged `KNOWN_GOOD-s12-alex-entrance-polished`.

**Engine (rebuilt + auto-deployed each step; patch `memoria-patches/s12-engine-edits.patch`):**
- New-Game target `EventEngine.Initialize.NewGame()`: `fldMapNo` 4000 → **100** (Alexandria/Main St; opening FMV still skipped).
- Set `EventState.FieldEntrance = 231` in NewGame() so field 100 enters via a **non-festival** branch. (Default entrance 0 triggers the festival ticket cutscene, which **softlocks** out of context — Vivi loops his pick-up anim, no control.)

**Field 100 (FF9CustomMap override of AF's `evt_alex1_at_street_a.eb`, all 7 langs; tools in `tools/`):**
- **Festival gating decoded** (`Main_Init` switch @587): entrances **201/231/204 → normal/walkable** branch; **anything else → festival** (InitCode 14 + ticket cutscene). So only those three values are safe; the "default" block is the festival path.
- **Player-init position switch** (entry 19 @10805): 201→block A (top), 231→block B, 204→block C. Each block sets `D9(0)=X,D9(4)=Z,D9(6)=dir` then `CreateObject`.
- **Door-spawn + decouple:** block C (204) repainted to the door (−250, 2100) for the **4000→100 return**; block B (231) repainted to the bottom-of-walkway (0, 332) for **New Game** → the two spawns are independent. (`alex_door_spawn` / `alex_newgame_spawn.py`.) Side effect: real arrivals from fields 107/114 now land at the door/bottom — debug-only paths, acceptable.
- **Popups suppressed:** the two `WindowAsync(6,0,68)` calls showed a leftover dev placeholder ("Error Env Play() Slot=0/1") on re-entry — NOPed cleanly (`field100: suppress…`).
- **Music:** Alexandria was silent on cold entry (its `RunSoundCode(1792,9)` resume-variant no-ops when the song was never loaded). Added `RunSoundCode(0, 9)` (song_play, Vivi's Theme = field 100's canonical Disc-1 track) — same call the room uses, so street↔room is seamless. (`alex_add_music.py`.)

**Human verified (in real gameplay, step by step):** New Game → walkable Alexandria ✓; door round-trip both ways ✓; step out **at** the door on return ✓; New-Game spawn decoupled to the bottom ✓; no popups ✓; Vivi's Theme plays in Alexandria + seamless into the room ✓.

**Open / carry-over (release cleanup):** debug **New-Game→100** skip still active (the opening FMV/field 50/70 is bypassed) — a real story-positioned entrance would replace it (and would naturally run field 100's *story* mode rather than our debug-warped state); engine is a debug build (Attack9999 auto-on); the field-100 block-B/C repaints + door + music are permanent overrides (fine for the mod, but they alter real 107/114→100 arrivals).

**Next:** (a) more room content (NPCs/story/dialogue, 2nd encounter); or (b) the release-cleanup pass.

### 2026-06-02 — Session 13 — Tier 1 toolkit: `ff9mapkit` built end-to-end (offline-validated)

**User's strategic pivot:** productize everything we've learned into a distributable toolkit so *other people* can author their own FF9 custom fields. Approved plan in `~/.claude/plans/sunny-zooming-bonbon.md`; built all 7 phases. New self-contained package at `C:\gd\FFIX\ff9mapkit\` on branch **`tier1-mapkit`** (NOT merged). **No game files touched — nothing to playtest yet.**

**The product:** pip-installable `ff9mapkit` that compiles a declarative **`field.toml`** into a complete drop-in Memoria mod (background scene `.bgx`+PNGs, walkmesh `.bgi`, 7-lang event `.eb`, dialogue `.mes`, DictionaryPatch/BattlePatch/ModDescription). CLI: `doctor / new / guide / camera / walkmesh / disasm / build / pack`. **Runs on stock (unmodified) Memoria** — zero runtime engine dependency.

**Done (committed per phase; 50 passing tests; validated entirely offline via golden-master byte-equality — honors Hard-Constraint §2 "can't verify in-game"):**
- **P0** package skeleton + `config.py` (path resolution via `$FF9_GAME_PATH`/`~/.ff9mapkit.toml`/`--game` — kills the ~12 hardcoded-path tools) + `binutils`.
- **P1** the `.eb` library: `model` (parse↔serialize **byte-identical**, 28/28 room scripts round-trip; per-lang bytes are ONLY the name field [44..69], bytecode is lang-identical), consolidated `edit.insert_bytes`/`append_entry`/symbolic locators (parity-checked vs legacy), `disasm` over **opcode tables baked from Memoria source** (`_optables.py`, no runtime source dep), `opcodes` encoders (all match the original tools' exact bytes).
- **P2** scene libs: `cam` (camera math verbatim + regression suite), `bgi` (**byte-faithful walkmesh codec** — round-trips the 232B HUT *and* the 5030B editor multi-floor field; **pure-Python `obj_to_bgi`/`quad` reproduce the HUT walkmesh byte-exact**, removing the editor's ConvertToBGI dependency + bad neighbor links), `bgx` (scene text format), `guide` (camera-from-pitch/fov → frame floor → paint guide + walkmesh corners).
- **P3** generalized content injectors (`npc/gateway/encounter/reinit/music/text`) on `EbScript`, NO hardcoded offsets (opcodes located via disasm). **Reproduces the in-game-verified Vivi-hut INTERIOR `.eb` BYTE-FOR-BYTE** (1555 bytes).
- **P4** `field.toml` schema + `build.py`. `examples/vivi-hut/hut_int.field.toml` compiles to the **byte-exact** `EVT_HUT_INT.eb` (all 7 langs) + exact DictionaryPatch line + Session-9 `.mes` + valid scene/walkmesh.
- **P5** `pack.py`: custom-id namespace (`>=4000`, per-mod 100-blocks via `suggest_base`), `pack` (zip), `new` (scaffold).
- **P6** docs: `FORMAT.md`, `PIPELINE.md` (human paint + Blender-walkmesh steps), `ENGINE.md`, README + example README.
- **P7** 2 clean debug-free **upstream PRs** for Memoria in `memoria-patches/upstream/` (overlay-texture-cache fade fix + FieldCreatorScene PNG-export-path one-liner) — both **verified to `git apply` cleanly to pristine HEAD**, individually + stacked. UPSTREAM.md has rationale/submission; the New-Game warp + booster auto-enable are deliberately excluded.

**Key decisions (user-chosen):** project format = **TOML**; engine = **zero runtime dependency + upstream the polish fixes** as PRs.

**IN-GAME PROOF — DONE (Hard-Constraint §2 human-verified).** Built a NET-NEW field **`4003/TESTROOM`** entirely with `ff9mapkit build` (reusing the interior's art + borrowed camera + walkmesh, Vivi placed left, gateway back out), deployed it additively (backups + a one-command `examples/toolkit-test/revert.py`), and reached it via a temporary interior-door repoint (`4002→4003`). **Human verified in real gameplay:** renders cleanly, Vivi on the left + talks, movement works, gateway back works. (First pass caught a *content* bug — I spawned the player inside the exit zone → instant kick-out — fixed by one line in `field.toml` [`spawn -1900 → -1100`] + rebuild, then re-verified. Exactly the author-mistake-fixable-in-TOML loop the kit is for.) Test reverted; game back to the known-good 3-field state. **The toolkit is now end-to-end proven: a field built entirely by `ff9mapkit` loads, renders, runs an NPC + custom dialogue, moves, and gateways in real Memoria.**

**Open / next:**
- Submit the 2 Memoria PRs (needs the user's GitHub fork).
- Distribution polish: bundled blank-field/region templates are game-derived — for a clean public release, extract the blank from the user's own install instead (noted in ENGINE.md).
- Branches `tier1-mapkit` (this) and `session7-ingame-custom-scene` (older) both unmerged.
- **Tier 2** (Blender add-on for visual camera/walkmesh authoring) is the natural follow-on; `scene.cam`/`guide` are ready for it.

### 2026-06-02 — Session 13 (cont) — Tier 1 MERGED + Tier 2 (Blender add-on) built (offline-validated)

**Done:**
- **Merged `tier1-mapkit` → `master`** (fast-forward; the toolkit is now on master).
- **Built the Tier-2 Blender add-on** (`ff9mapkit/blender/`, branch **`tier2-blender`**, NOT merged) — a *front-end* that visually authors the camera + walkmesh and exports `camera.bgx` + `walkmesh.obj` + a `field.toml` for `ff9mapkit build` (the proven Tier-1 builder stays the source of truth). Targets Blender **4.2+/5.x** (user has 5.1).
  - **P1 — the crux, offline-validated:** `bridge.py` (bpy-FREE) maps a Blender camera ↔ FF9 `cam.Cam` (coordinate map M + camera-basis conventions, built on `cam.decompose`/`synth_r_t`) + `mesh_to_ff9_obj`. `tests/test_bridge.py`: **all 6 real cameras round-trip r/t within 1** through Blender params and back, + a semantic anchor (a pure-Blender look-down camera → FF9 camera at the right position/pitch, floor centered + right-side-up).
  - **Supported-range guidance (user's ask):** `cam.SUPPORTED_PITCH_DEG=(0,50)` (covers GRGR's 49.6, the steepest real camera) + `pitch_deg()`/`pitch_warning()`; **advisory, non-blocking** warning surfaced in the add-on panel AND backported to `ff9mapkit guide`/`camera`/`build`. (Synthesis is exact at any pitch; only the *paint-guide back edge* drifts past the real range — re-pin `S_CANVAS_Y` with one grid check for a dead-on steep angle.)
  - **P2:** vendored the pure-stdlib scene math (cam/bgi/bgx/guide) so the add-on is self-contained in Blender; `build_addon.py` zips it; a drift-guard test keeps vendor byte-identical to `ff9mapkit/scene/*`.
  - **P3:** the `bpy` add-on — `ops.py` (Setup FF9 Scene / Pose Camera / Compute Paint Guide / Export Field) + `ui.py` (N-panel w/ live FF9 readout + range warning) + `blender_manifest.toml` + `bl_info`. All `py_compile` clean.
  - **P4:** `blender/README.md` (install + workflow + "render is a placement aid, paint guide is truth" + range note) + an **end-to-end dry-run** test: a bridged Blender camera + mesh → `camera.bgx`/`walkmesh.obj`/`field.toml` → compiled by the REAL `ff9mapkit build` into a valid mod. **13 blender tests + 59 kit tests pass.**

**Constraint honored:** I cannot run Blender, so the *math* is validated offline (round-trip + dry-run); the **`bpy` UI itself is unverified by me** — the user installs the add-on and verifies the UI + the final in-game alignment (Hard-Constraint §2).

**Open / next:**
- **Tier-2 in-Blender test (the human step):** `python ff9mapkit/blender/build_addon.py` → Install from Disk in Blender 5.1 → Setup FF9 Scene → confirm the camera readout is sane → model a flat walkmesh → Export → `ff9mapkit build` the emitted `field.toml` → confirm in-game the walkmesh lands on the floor for a visually-posed camera. Fast pre-check: pose a camera to match a known field, `ff9mapkit camera camera.bgx` reports the expected pitch/FOV.
- Merge `tier2-blender` once UI-verified; submit the 2 Memoria PRs (needs GitHub fork).

**Tier-2 in-Blender test — DONE (human-verified) + MERGED.** Two install/UI bugs fixed first: (1) the add-on must be packaged as a Blender **extension** (flat zip, `blender_manifest.toml` at root, install via **Get Extensions → Install from Disk**) — the legacy nested/Add-ons path reported "Modules Installed ()" on 5.1; (2) an invalid panel icon (`CON_CAMERASOLVED` → `VIEW_CAMERA`) crashed the panel draw. After those, **user confirmed in Blender 5.1**: Setup FF9 Scene runs clean, the live FF9 pitch/FOV readout is sane, Pose Camera + Compute Paint Guide + Export Field all work, and `ff9mapkit build` compiled the Blender-exported `field.toml` into a valid mod ("all clear"). **`tier2-blender` merged → `master`** (fast-forward). Tagged `KNOWN_GOOD-s13-tier2-verified`. (Still optional/deeper: shape a real floor + paint to the guide + confirm walkmesh-on-floor alignment in-game.)

**Deeper in-game alignment test — DONE (Blender-authored room walked in-game).** User posed a **pitch-35** camera by eye in Blender (1.5×-scaled default walkmesh), exported; I auto-generated a checkerboard floor keyed to that camera (`to_canvas`) + a bright walk-edge outline, built field **4003/BLENDERROOM**, deployed it reachable via the interior-door repoint (`4002→4003`, backups + `blendertest/revert_blender_test.py`). **Human in real gameplay:** floor renders in correct perspective, player stands on it naturally, **sides + front walk-edges pixel-match the drawn outline** → the Blender→FF9 camera bridge is validated end-to-end in-game. **Back edge slightly mismatched** — this is the documented Session-10 canvas-`sy` back-edge residual (pitch-dependent, worst far from ~48–65°; 35° is flatter so it shows), exactly what the supported-range warning flags; NOT a bridge bug (sides+front being exact proves the camera). Also fixed a Blender clip-visibility nuisance (FF9-scale cameras sit >1000 units away → default far-clip culled the scene; now clip_end=100000 on Pose/Setup). Escape hatch for a dead-on back at a given pitch: re-pin `S_CANVAS_Y` from one grid check (per `project-ff9-camera-math`).

### 2026-06-02 — Session 13 (cont) — Back-edge anomaly CRACKED: canvas map is EXACT scale-1 (collision radius was the culprit)

**The "back edge a bit short" residual that haunted every painted room since Session 8 is SOLVED — and it was never a map error.** User chose "B-sharp": instrument the engine to log the noise-free world→canvas projection, since the map was proven linear. Done end-to-end, offline-validated to **0.0005 px**.

**Method (in-engine probe, since I can't eyeball-measure):** added a temporary one-shot debug block to `FieldMapActor.HonoLateUpdate` (field 4003 only) that logged, via the live engine, (a) the GTE `world→viewport` for a 13×3 floor grid and (b) the painted **overlay quad's 4 corners → viewport** directly. Rebuilt/redeployed Memoria (`'-p:SolutionDir=...\Memoria\'`, auto-deploys x64+x86), user walked in 3×, I read `Memoria.log`. Then removed the probe + rebuilt clean (verified deployed DLL has no `FF9PROBE`, fade-cache intact).

**The finding (decisive):** the overlay system places painted-canvas pixel `(cx,cy)` at FieldMap-world `(cx-HalfFieldWidth, HalfFieldHeight-cy)` (BGSCENE_DEF.CreateScene_OverlayGo, **scale 1**), and the actor/walkmesh sits at its GTE `(px,py)`; both render through ONE ortho FieldMap camera (overlay corners + actor share the IDENTICAL viewport affine to 5 digits). So a world point lands under canvas `(cx,cy)` exactly when `(px,py)==(cx-HalfW, HalfH-cy)`. With px,py = raw projection + engine offset, the HalfField terms cancel → **EXACT scale-1 map, no fudge:**
```
canvasX = rawProj.x + range.w/2 ;  canvasY = range.h/2 - rawProj.y
```
`to_canvas` rewritten to this reproduces the probe to 0.0005px across the grid (committed `b656616`, 64 tests pass, vendor synced).

**Why the old sx=0.926/sy=0.889 "worked" yet always drifted at the back:** they were an EYEBALL fit that silently absorbed the player **COLLISION RADIUS** — `FieldMap` sets the controller radius to `bgiRad*4` ≈ **48 world units**, so the player CENTRE stops ~48u inside any painted edge, *most visible at the foreshortened back*. That constant-world inset reads as a pitch-dependent canvas error, so every room was "a touch short at the back". It's PHYSICS, not the map. New constant `cam.COLLISION_RADIUS_W = 48.0`; extend the walkmesh ~48u past the painted floor if the player should reach the visual edge. The map + synthesis are now **exact at any pitch**; `SUPPORTED_PITCH_DEG` downgraded to an authenticity advisory (the back-edge-drift rationale is retired).

**Bonus bug found (and why the probe still worked):** field 4003/BLENDERROOM is currently BROKEN — its scene load throws `InvalidCastException` (Memoria.log:29), `LoadEBG`'s try/catch swallows it, and the engine keeps the PREVIOUS field's (interior `HUT_INT`) scene+camera while `fldMapNo=4003`. So the probe measured the interior's 48° camera — fine, the canvas map is camera-INDEPENDENT, so it validated anyway. Confirmed by the probe's overlay Z's (4000 floor / 3000 walls) matching HUT_INT exactly, not BLENDERROOM (4001/4000). BLENDERROOM got desynced by my earlier partial manual `.bgx`/`floor.png` swap. **Lesson (memory `project-ff9-camera-math`):** a custom field that throws on scene-load silently renders the field you came from; grep Memoria.log for cast/asset errors when a custom BG "looks like the previous room".

**Engine/game state:** clean probe-free Memoria redeployed (= Session-12 fade-cache + booster build). Debug New-Game→100 warp + interior-door→4003 repoint still active; **field 4003 currently broken** (renders the interior) — revert via `blendertest/revert_blender_test.py` or rebuild fresh. No KNOWN_GOOD tag (offline tooling fix; nothing new shipped to a working in-game state this session).

**Next (optional capstone):** rebuild BLENDERROOM cleanly via `ff9mapkit build` (consistent .bgx+.bgi+grid via the new scale-1 map, walkmesh extended ~48u past the floor) → user walks to each edge → feet land exactly on the line (now that the radius is accounted for) → visual confirmation of the closed-form map in real gameplay. The map itself is already proven (0.0005px vs the engine), so this is confirmation-only.

### 2026-06-02 — Session 13 (cont) — In-game capstone: character-ground offset found; full alignment model COMPLETE

**The "back-edge anomaly" is fully, cleanly cracked — both halves.** Built a fresh calibration room (field 4003, 40° camera, checkerboard floor via the new scale-1 `to_canvas`, walkmesh via `ff9mapkit build`) and walked it. Result + root cause:

- **The canvas MAP is exact (scale-1), triple-confirmed:** the engine probe (0.0005px), the deployed walkmesh verts projecting EXACTLY onto the painted floor lines, and **sides pixel-perfect in-game**.
- **The residual was a CHARACTER offset, not a map error.** First pass: feet sat a uniform **~0.6 checker cell** above the paint (back overshoot = front undershoot = same amount; sides fine). Root cause (from source): FF9 draws the field **background + walkmesh via the 2D GTE projection** (what `to_canvas` models, exact) but the **character MODEL via a separate 3D perspective camera** (`PSX.ConvertCameraPsx2Unity`) — the classic FF9 3D-char-vs-2D-BG vertical mismatch. The character's feet sit a ~constant world amount toward the far edge of its 2D ground point.
- **Fix = a constant, not a scale.** Shifted the walkmesh **~298 world-u toward the camera** (= 0.6 cell @40°); **user: "looking very precise"** — back edge now symmetric with front/sides. This constant is **exactly what the old per-pitch `sx/sy` SCALE was approximating** — and since a scale can only match a constant at one point, that's precisely what produced the years-old "back-edge drift." Mystery fully explained.

**The complete, separated alignment model (now in `ff9mapkit`):**
1. `cam.to_canvas` — scale-1, exact — where a world point appears on the painted canvas. Used for **art/overlay placement + the paint guide**.
2. `cam.CHARACTER_GROUND_OFFSET_Z = 298` — slide the **walkmesh** toward the camera by this so the 3D character looks planted on the 2D floor. `build.resolve_walkmesh` applies it to the **auto-framed** walkmesh by default; explicit obj/quad default **0** (Blender-authored coords + golden byte-exact tests untouched); override via `[walkmesh] character_offset`.
3. `cam.COLLISION_RADIUS_W ≈ 48` (`bgiRad*4`) — separate, smaller physics inset (player centre can't reach the walkmesh edge); extend the walkmesh ~48u past the floor to let the player reach the visual edge.

**Commits:** `b656616` (exact scale-1 map), `39f048f` (capstone builder), `134e035` (character offset + kit wiring). 64 tests pass (golden byte-exact reproductions intact). Memory `project-ff9-camera-math` updated with both halves.

**Engine/game state:** clean probe-free Memoria (Session-12 build). Field 4003 is the capstone calibration room (40° grid, walkmesh char-shifted) reachable via the interior door (4002→4003). Debug New-Game→100 warp still active. Revert the test field with `blendertest/revert_blender_test.py`.

**Open / next:** the char offset (298) was pinned at 40° — it's a 3D-vs-2D mismatch so it may vary with pitch; re-confirm/​re-pin opportunistically for a steep room (the kit makes this a one-line `[walkmesh] character_offset`). Then: clean up the debug warp + retire the calibration field, and the kit's geometry pipeline (camera + paint guide + walkmesh + character planting) is production-complete.

### 2026-06-03 — Session 14 — Blender Tier-2 Phase 1: visual authoring loop (in-game verified)

**Back-edge anomaly fully closed (Session 13 cont):** the painted-canvas map is EXACT scale-1 (`canvasX = rawProj.x + w/2`, `canvasY = h/2 − rawProj.y`, proven 0.0005px vs an in-engine probe + walkmesh verts landing on the painted lines), and the old per-pitch `sx/sy` were a SCALE approximating a CONSTANT character-ground offset (FF9 3D-char vs 2D-BG, `cam.CHARACTER_GROUND_OFFSET_Z=298`, applied to walkmesh placement) — that constant-vs-scale mismatch was the years-old "back-edge drift." `cam.COLLISION_RADIUS_W≈48` is a separate physics inset. Tagged `KNOWN_GOOD-s13-canvas-map-cracked`.

**Cleanup:** reverted the calibration field; removed dead dev-journey fields (broken HW clones 4001/CUSTOM_FIELD_001/002 + calib grids ROOM02/03/04_TD, archived to a gitignored zip). Live mod = 4000 HUT_EXT + 4002 HUT_INT (+ ROOM01_BASE art archive).

**Blender Tier-2 Phase 1 — DONE, human-verified in-game.** The add-on is now a full visual front-end:
- **viewport floor guide** (wireframe grid + markers where the painted floor lands) and **walkmesh starts ON the floor frame** (+ "Reset Walkmesh to Floor" after re-posing) — fixed the "walkmesh vs grid in a weird place" confusion.
- **painted-art backdrop**: Add/Clear Background Layer load painted PNGs as FF9-camera background images (model the walkmesh against the art); foreground layers (small z) preview IN FRONT (occlusion preview).
- **Export Paint Template** button: rasterizes a transparent 1536×1792 trace-over template (floor outline + perspective grid) into a Blender image, no PIL/subprocess. Also a CLI: `ff9mapkit guide --from-bgx <cam.bgx> --template --png`.
- **export** emits real `[[layers]]` (PNGs copied) + `[walkmesh] character_offset` so 3D chars look planted.
- Taught the user the FF9 field model (painted picture + invisible walkmesh + char on top; layers share one canvas; draw order by z, smaller=in front).

**Human verified (real gameplay):** built a hand-painted room in Blender (pose camera → Export Paint Template → paint back+front layers → Add Layer → reshape walkmesh → Export → `ff9mapkit build` → deploy), walked into it as field 4003/MY_ROOM, and the painted background + Blender walkmesh + **front-layer occlusion** all render correctly. "success." All offline-validated (71 tests; bpy-free bridge + dry-runs); the bpy UI is human-verified.

**Engine/game state:** clean Session-12 engine. MY_ROOM (4003) is the Blender test room, reachable via the interior door (revert: `ff9mapkit/blender/debug_proj/revert_myroom.py`). Debug New-Game→Alexandria warp still active.

**Next:** Blender Tier-2 **Phase 2** — NPC / gateway / spawn markers (Empties) → real `[[npc]]`/`[[gateway]]`/`[player]` in the field.toml, so Blender rooms get content + a real exit. Then Phase 3 (docs + repackage). Commits this session: `b656616 39f048f 134e035 9d31aed b5e242b b053772 47e7f89 82c6c5c 73b380f 89f93da`.

### 2026-06-03 — Session 14 (cont) — Bounds smoke test: concave walkmeshes + yawed cameras (all in-game verified)

**Stress-tested the Blender→`ff9mapkit` pipeline at its limits** (user: "we got one success, but we need to test the bounds"). Each test deployed as field 4003/MY_ROOM via the interior-door repoint; each in-game verified. The geometry+camera pipeline holds across the bounds — with one real bug + one real gap found and fixed.

**Done + human-verified:**
- **Steep pitch (65°):** char-offset 298 still plants. "great."
- **Concave L-walkmesh** (`tools/build_lshape_test.py`, corner-notch): navigation (front walkable, inner corner smooth, notch blocked, confined) ✓; planting ✓ with `character_offset=298` — the uniform shift works on non-rectangular geometry (`rebuild_neighbors` handles concave tri-fans).
- **Concave U-walkmesh** (`tools/build_ushape_test.py`, back-center bay, walkable wraps around it, TWO inner corners): all 4 checks ✓. (User's "bay edge ½-square off" = my test floor.png coloring the checker by fine-cell *center* vs the boundary at `zmid`; the walkmesh vertex is exactly at `zmid` → coordinate-perfect. Pure test-art quantization, not a kit issue.)
- **Yawed camera (45°)** (`tools/build_yaw_test.py`) — the last unverified bound. TWO findings, both fixed (commit `fc4b6d8`, 95 tests pass, 22 new):
  1. **`make_camera` yaw bug:** it composed `rot_y(yaw)·rot_x` (pre-multiply). The GTE applies R *after* the y-flip F, so pre-multiply did NOT keep the origin centred — any yaw flung the floor off-screen (origin → canvas x≈2575 at yaw 45). Fix: **`R = rot_x(pitch)·rot_y(−yaw)`** (post-multiply); origin stays at the canvas centre at every yaw. In-game: floor renders as a centered rotated quad, walkmesh aligned.
  2. **Movement gap:** the kit hardcoded the control-direction (TWIST `0x67`) to 0°, so on a yawed camera "W" pushed world-+Z (rendered up-left), not up-screen — confirmed exactly by painted world-axis arrows. Fix: the builder now **auto-derives the control value from the camera yaw** — `value = round(yaw/360·256)−1`, the inverse of the engine's `(v+1)/256·360` (`FieldState.SetTwistAD`). After: W goes straight up the screen ✓. This is what real FF9 yawed-camera fields ship (decomposed the 6 real cameras: TSHP1 ≈ −90°, GZML0 ≈ −24° — the game sets TWIST per camera). Front-facing cameras derive −1 (= blank default) → all existing fields byte-identical; also covers Blender-posed cameras (exported as a borrowed `.bgx`) and borrowed real-field cameras. `[camera] control_direction` overrides.
- **Graceful-failure bounds (offline):** shallow-pitch-above-horizon and Int16-overflow walkmesh both raise clear errors.

**New kit surface:** `scene.cam.yaw_deg`; `content.movement` (`control_value_for_angle` + shift-free in-place `set_control_direction`); `build.resolve_control_value` wiring. Vendor cam/guide synced. `tools/build_{lshape,ushape,yaw}_test.py` bounds-test builders (their `*_out/` output gitignored). Worth folding the yaw findings into project memory `project-ff9-camera-math`.

**Engine/game state:** clean Session-12 engine. MY_ROOM (4003) currently holds the **yaw-45 calibration grid** (last bounds test) — revert with `ff9mapkit/blender/debug_proj/revert_myroom.py`. Debug New-Game→Alexandria warp still active.

**Next:** Blender Tier-2 **Phase 2** (NPC/gateway/spawn Empties → field.toml), or revert MY_ROOM and pick the next direction.

### 2026-06-03 — Session 14 (cont) — Blender Tier-2 Phase 2: visual content markers (in-game verified)

**Place NPCs / gateways / the player spawn in the Blender viewport instead of hand-editing TOML — end-to-end verified in real gameplay.** Commit `1c01788`; 99 kit + 23 blender tests pass.

**Done:**
- New **Content** panel (`ops.py`/`ui.py`): *Add NPC* drops an Empty (`FF9_NPC`, custom props `ff9_preset`/`ff9_dialogue`/`ff9_name`); *Add Gateway* drops a wire quad whose 4 floor corners are the exit zone (props `ff9_to`/`ff9_entrance`; first edge = walk-out direction); *Set Spawn* places the single `FF9_Spawn`. All snap to the FF9 floor (Blender z=0). Panel shows a marker tally + inline custom-prop editors for the selected marker.
- **Export** reads every tagged marker, maps its Blender world pos → FF9 floor (x,z) via the existing bridge (y↔z swap), and emits real `[[npc]]` / `[[gateway]]` / `[player]` blocks (absent → the old commented hints).
- **bpy-free formatters** in `bridge.py` (`npcs_to_toml`/`gateways_to_toml`/`player_to_toml`/`marker_floor_pos`, TOML-escaped) → unit-testable without Blender. `test_content_markers.py`: coord mapping, valid-TOML round-trip, + a full dry-run building an NPC(preset+dialogue)+gateway+spawn through the real builder (dialogue→.mes confirmed). README workflow updated.

**Human verified (real gameplay):** authored an NPC + gateway + spawn visually in Blender → Export → `ff9mapkit build` → walked the loop as MY_ROOM (4003): NPC (Vivi) appears + talks ("Hello."), spawn correct, gateway exits to Alexandria (entrance 204, walkable). **"the markers I placed are accurately represented"** — so the known `character_offset`-not-applied-to-markers gap is imperceptible for point markers (≈⅓ tile); not worth fixing.

**Deploy gotcha (shared text):** custom fields 4000/4002/4003 all use text_block 1073, and the kit hardcodes dialogue at TXID 500 (`DEFAULT_BASE_TXID`) → collision. For the multi-field DEV mod, **merged** MY_ROOM's line at TXID 501 into the live `1073.mes` (kept the hut's 500 "I miss you Zidane") and repointed MY_ROOM's `WindowSync` 500→501. (For the kit's intended one-field-per-mod distribution there's no collision; per-field text namespacing would be the kit-level fix if multi-field-per-mod ever matters.) mes backups: `backups/<lang>-1073.mes.20260603-phase2`.

**Engine/game state:** clean Session-12 engine. MY_ROOM (4003) now holds the Blender Phase-2 room (NPC+gateway+spawn) via the interior door; revert with `ff9mapkit/blender/debug_proj/revert_myroom.py` (note: it doesn't strip the harmless TXID-501 mes entry). Debug New-Game→Alexandria warp still active.

**Next:** Blender Tier-2 **Phase 3** (docs + repackage the add-on), or revert MY_ROOM and start the release-cleanup pass (remove the debug warp, package, prep the 2 Memoria upstream PRs).

### 2026-06-03 — Session 14 (cont) — Camera-movement docs + release-cleanup pass (mod packaged; PRs prepped, NOT opened)

**Done:**
- **Camera-movement docs** folded into `ff9mapkit/docs/PIPELINE.md` ("Camera movement & bigger environments"): FF9 fields are fixed-perspective pre-renders (never re-rendered); "movement" = scrolling the view across a larger-than-screen painting (`SceneService2DScroll/3DScroll`) OR switching between multiple per-field cameras (confirmed: Treno shop ships 2 CAMERA blocks; most fields 1); cutscene pans are scripted over the pre-render. Kit supports one fixed camera/screen today; scroll + multi-cam are scoped future features; **chain single-screen rooms via gateways for a bigger space now** (what FF9 itself does).
- **Reverted MY_ROOM (4003)** test field → clean 2-room state (4000 HUT_EXT + 4002 HUT_INT, interior door→4000); restored the live `1073.mes` from the phase2 backup (dropped the test TXID-501 entry; hut's 500 "I miss you Zidane" intact).
- **Packaged the release mod** `release/FF9CustomMap` (+ `FF9CustomMap-ViviReturn-v1.zip`, gitignored): the 2 rooms (.bgx/.bgi/painted PNGs) + the 3 event scripts (rooms + the Alexandria Main St door override `evt_alex1_at_street_a`) + `1073.mes` + DictionaryPatch/BattlePatch/ModDescription + a README. **Dropped the dev cruft:** unreferenced `ROOM01_BASE` art + the debug opening/cargo overrides (`evt_alex1_ts_opening` still holds the old field-70→4000 warp; `_ts_cargo_0`). **Engine-independent — runs on stock Memoria** (the actual fade fix is the .eb tag-10 FadeFilter, part of the mod, NOT the engine cache).
- **Upstream PRs prepped + verified, NOT opened** (per user): both `memoria-patches/upstream/` patches confirmed against pristine `main`@`6b8bb2d5` — PR1 (overlay texture cache) base blob matches HEAD exactly + reverse-applies as the exact deployed diff; PR2 (FieldCreatorScene PNG path) forward-applies cleanly on an independent region. Patches are CRLF (match the Windows repo); noted `--ignore-whitespace` for LF/CI. UPSTREAM.md updated.

**Human verified (in-game):** after the cleanup, the **Alexandria door round-trip still works in town-mode** — New Game → walkable Alexandria (entrance 231 = the non-festival/town branch, the path a real town-mode visit uses) → door → hut exterior (4000) → interior (4002) → back out at the door; NPC + encounter intact. "all clear." This validates the **release reachability path** (the festival/entrance-0 branch is a locked cutscene where the door wouldn't/shouldn't fire).

**Engine decision (user's call): KEEP the dev engine.** The debug New-Game→Alexandria warp + auto-boosters stay on the local install (handy for continued dev + the instant warp-to-room test). The **shipped package is already debug-free by construction** (engine edits aren't mod files), so the release is clean regardless. Local engine restore (→ stock, removing the warp + the field-50/70 opening overrides so New Game plays the normal opening) deferred to whenever a true player-experience test is wanted: `tools/restore_memoria_dll.py baseline` + delete the live `evt_alex1_ts_opening`/`_ts_cargo_0` overrides.

**Engine/game state:** dev engine (Session-12 build: New-Game→100 warp + boosters + fade-cache) — KEPT. Live FF9CustomMap = clean 2-room state + Alexandria door (+ leftover `ROOM01_BASE` art + debug opening/cargo overrides still on disk, excluded from the release package). Branch `master`.

**Next options:** Blender Tier-2 **Phase 3** (finalize add-on docs/version/repackage); a 2nd connected room (chain via gateway) to demo the multi-room approach; in-room **scrolling** or **multi-camera** as a new kit feature; open the upstream PR (needs the user's GitHub fork + go-ahead); or the local engine→stock restore + a true-player-experience playthrough when desired.

### 2026-06-03 — Session 14 (cont) — Upstream PRs reviewed: cut to ONE (texture-cache dropped as misjustified)

Walked the two prepped Memoria PRs with the user, one at a time. **Result: ONE PR to submit, not two.**
- **PR1 (overlay texture cache) — DROPPED.** User correctly challenged its description: it claimed to fix a "slow, see-through fade," but per the Session-12 log the fade was actually fixed by the field's `.eb` tag-10 `FadeFilter` + flattening the painted art — and the cache was explicitly "kept anyway, harmless." Re-read source to be precise: `FieldMap` builds a fresh `BGSCENE_DEF` per field entry (`FieldMap.cs:430`) and `ProcessMemoriaOverlay` (`:197`) re-decodes each overlay PNG via `LoadFromDisc`, so the cache is purely an **unmeasured load-time micro-optimization** for pure-`.bgx` re-entry. The user's "clear it on gateway?" idea would empty it before every load → ~zero benefit. Decision: don't upstream an optimization we can't justify with evidence + whose stated rationale we disproved. Patch kept for reference at `memoria-patches/deferred-overlay-texture-cache.patch` (revisit only if real perf issues appear). **Lesson: audit a PR's *claims* against what the code/diff actually does before submitting — the fade story was early-days confusion.**
- **PR2 (FieldCreatorScene PNG export path) — KEPT, verified, approved.** A genuine one-line **bug** fix: `ExportMemoriaBGX` passes the bare `fileName` (no dir) to `ExportMemoriaBGXOverlay`, so overlay PNGs write to the process CWD (game root) while the `.bgx` `Image:` ref (bare, via `Path.GetFileName`) loads from the field folder → field black-screens. Confirmed exactly in source (`:518/524/533/561-564/610-612`); fix = pass `folder + fileName`. Renamed to `memoria-patches/upstream/fieldcreator-png-export-path.patch`; `UPSTREAM.md` rewritten as a single PR with paste-ready title/description + the "considered & dropped" note. Forward-applies clean to pristine `main`@`6b8bb2d5`.

**Status:** `memoria-patches/upstream/` = ONE submission (FieldCreatorScene fix) + UPSTREAM.md.

**PR OPENED (user approved + forked):** **https://github.com/Albeoris/Memoria/pull/1433** — "Fix FieldCreatorScene export writing overlay PNGs to the game root instead of the field folder" (base `main` ← `GameJawnsInc:fix-fieldcreator-png-export-path`, 1 file, +4/−1). Opened via `gh` from a fresh clone of the fork at `C:/gd/memoria-pr` (separate from the dev `Memoria/` tree). The fix line was byte-identical on current upstream `main` (blob `1e42a31d`), so it applied clean. Awaiting maintainer review; the `memoria-pr` clone is kept around for easy follow-up pushes if changes are requested. **This is our first upstream contribution to Memoria.**

### 2026-06-03 — Session 14 (cont) — Blender Tier-2 Phase 3: add-on docs/version finalize (offline, no game change)

**Done (docs/version/packaging only — Claude-owned per Hard-Constraint §2; nothing in-game-visible, so no playtest):** the add-on had shipped two feature waves since v0.1.0 with no version bump or doc refresh — Phase 1 (viewport floor guide, Export Paint Template, paint-art backdrop layers) and Phase 2 (NPC/gateway/spawn content markers). Finalized:
- **Bumped the add-on to 0.3.0** across all three version sites (`blender_manifest.toml`, `__init__.py` `bl_info`, `build_addon.py` `VERSION`) and repackaged the extension zip (`dist/ff9mapkit_blender-0.3.0.zip`; vendor re-synced, drift-guard clean). The main `ff9mapkit` CLI/library stays on its own track (0.1.0) — untouched.
- **Filled the README workflow gaps:** it never documented `Export Paint Template`, `Add/Clear Background Layer` (load painted art as a backdrop to model against; occlusion via small z), or `Reset Walkmesh to Floor`. Reworked the workflow to mirror the actual panel order (Setup → Camera → Walkmesh → Background Art → Content → Export).
- **Cross-linked** the Blender add-on from `docs/PIPELINE.md` as the visual front-end for the camera + walkmesh steps.
- 99 tests pass (kit + blender). Commit `e59b074`.

**Engine/game state:** unchanged from the prior entry — dev engine (Session-12 build); live FF9CustomMap = clean 2-room state (4000 HUT_EXT + 4002 HUT_INT) + Alexandria door. No new in-game state → no KNOWN_GOOD tag. Branch `master`.

**Next options:** a 2nd connected room (chain via gateway) to demo the multi-room approach; in-room **scrolling** or **multi-camera** as a new kit feature; respond to PR #1433 maintainer feedback; or the local engine→stock restore + a true-player-experience playthrough.

### 2026-06-03 — Session 15 — SCROLLING fields: in-game proven + landed in the kit (Phases 0-2)

**User goal:** bigger, more immersive rooms — larger-than-screen fields where the view pans to follow the player (FF9 streets/corridors). Approved plan (`~/.claude/plans/sunny-zooming-bonbon.md`): **scrolling first, then multi-camera; kit/field.toml first, Blender later.**

**The engine already does the panning — it's almost all data.** Source dive (3 Explore agents + targeted reads) established:
- `FieldMap.SceneService3DScroll` (`FieldMap.cs:1959`) auto-pans `curVRP` to follow the player, clamped to the camera's `vrpMin/Max` — but **gated on the field `Active` flag** (`IsActive => flags & FieldMapFlags.Active`, `:2385`).
- `Active` is set by the script opcode **`BGCACTIVE 0x71` "EnableCameraServices"** (`EventEngine.DoEventCode.cs:1858`; args isActive/frameCount/sinusOrLinear). The blank/1357-cloned field never calls it.
- `.bgx` `Range:` = full painting size; `Viewport:` = scroll clamp (`BGSCENE_DEF.cs:389,398`). **Scroll bounds = `(HalfNative, w-HalfNative, HalfNative_h, h-HalfNative_h)`** (`FieldMap.cs:1111-1114`); HalfNative = 160×112 = the kit's `HALF_FIELD_W/H`. For a 384×448 screen this is the kit's existing `DEFAULT_VIEWPORT` (no real scroll).
- **Focal length must stay normal for a wider painting:** build `proj` from the visible WINDOW width (384), only widen `Range` — else a 768-wide painting doubles the FOV. (`make_camera` couples proj↔range_w, so the spike borrowed a hand-built camera; the kit now has `window_width` to express this.)

**Phase 0 — scroll spike (in-game PROVEN).** `tools/build_scroll_test.py` built a 768×448 (2×-wide) checkerboard room with numbered landmark columns + a flat walkmesh spanning it, `Viewport (160,608,112,336)`, and `BGCACTIVE(1,0,0)` injected into Main_Init. Deployed reversibly as field **4003/SCROLL01** via the interior-door repoint (`Field(4000)→Field(4003)`, all 7 langs, same-length patch) + merged DictionaryPatch line; dry-validated (camera/geometry/build/inject/repoint) before touching the game. **Human verified: the view scrolls to follow the player, the floor + walkmesh + character pan together aligned, and it clamps at the edges** ("everything looks good"). The "off by 1 square top/bottom" is the existing `character_offset`/collision-radius constant (spike used `character_offset=0` for a clean read), NOT a scroll issue. → `BGCACTIVE` enables scroll on a minted field; the bounds formula is correct; no calibration needed.

**Phases 1-2 — landed in the kit (offline, 108 tests, normal fields byte-identical):**
- `cam.scroll_bounds(range_wh)` (in-game-proven formula).
- `guide`: paint guide/template + frame size now key off `cam.range`, so a wide painting gets a full-size guide.
- `content/camera.enable_camera_services` (injects `BGCACTIVE` via `edit.insert_bytes` into Main_Init).
- `build`: `[camera.scroll] enabled` → auto scroll viewport + `BGCACTIVE` inject; `[camera] window_width`/`proj` decouple focal from a wide `Range`; layers default to the canvas size. `docs/FORMAT.md` updated; Blender vendor re-synced. The declarative path reproduces the spike's camera (Range 768×448 / Viewport 160,608,112,336 / proj 498) + `BGCACTIVE` in all langs.
- Commits `bd65d46` (spike tool), `46963dc` (kit support). Field 4003 currently holds the SCROLL01 spike grid (revert: `py tools/scroll_out/revert_scroll_test.py`).

**Phase 3 — painted scrolling room DONE (human-verified in-game).** Added **height guides** to the paint guide first (user's ask — "too hard to eyeball perspective from just a floor grid"): `guide.render_paint_guide/template` now draw world-accurate vertical poles at the floor corners/mid-edges + back-wall height rings + a room-box (ceiling) outline + labeled height ticks (`wall_height` param, auto = floor depth). Then `tools/make_scroll_demo.py` generated a full-size paint guide for a 2×-wide room; **user painted** `back.png` (checker floor + orange walls in perspective + teal surround) + `front.png` (a hanging-lamp foreground occluder). `tools/deploy_scroll_demo.py` built it via the kit (BGCACTIVE auto-injected) + deployed reversibly as field **4003/SCROLLDEMO** via the interior-door repoint. **User: "perfect"** — renders right, scrolls across the full 2× width with floor/walls/player aligned, **walls read as a believable room volume** (the height-guide payoff), the **lamp occludes the player** (front layer z=8), movement + `character_offset=298` planting correct. The full scrolling pipeline (kit support + height-guided paint guide + painted in-game room) is COMPLETE. Commits `a8f3fbf`/`76cba83`/`6b7f464`/`239ad48`; PIPELINE.md/ENGINE.md updated (scrolling now "supported"); `examples/scroll-demo/` is the worked example. Tagged `KNOWN_GOOD-s15-scrolling`. Field 4003 holds SCROLLDEMO (revert: `py tools/scroll_out/revert_scroll_demo.py`).

**Next — multi-camera** (the planned later effort): N painted backgrounds + script-driven `SETCAM 0x7E` switch zones (the scene format already parses N cameras + per-overlay CameraId; the engine auto-projects the walkmesh per camera). Or Blender front-end support for scrolling (deferred per the plan), or wire the scroll room into real content.

### 2026-06-03 — Session 15 (cont) — Blender scrolling support (add-on v0.4.0; offline-validated, awaiting in-Blender verify)

**Brought scrolling to the Blender add-on** (user: "Blender scrolling support next"), mirroring the kit's `[camera.scroll]`. bpy-free bridge fully tested (115 tests, 7 new); the bpy UI is authored for the human to verify in Blender (Hard-Constraint §2 — I can't run Blender).

**Done:**
- **bridge.py (bpy-free):** `window_width` param on `blender_cam_to_ff9`/`ff9_cam_to_blender` (decouple focal from a wide Range — a 768-wide painting must NOT double the FOV; default = range width so normal fields are untouched). `scroll_floor_frame` solves the half-width to fill the wide canvas; `_height_segments` (poles/back-rings/ceiling box, PNG px) added to `paint_template_lines` which now sizes to `c.range` (full painting); `floor_guide_geometry` emits a `wall_verts`/`wall_edges` wireframe. Tests: scrolling camera round-trips with focal preserved, template sizing+height, fill-width, + a **scroll-export → real `ff9mapkit build` dry-run** asserting wide Range + Viewport `160,608,112,336` + `BGCACTIVE` in all langs.
- **ops.py/ui.py:** "Scrolling room" toggle + Canvas W/H props; `_pose_camera`/`active_camera_to_ff9` scrolling-aware (proj from the 384 screen, `scroll_bounds` viewport, `window_width=384`); the Paint Template op rasterizes the height segments; `_rebuild_floor_guide` adds the vertical wall wireframe to the viewport; Add Layer resolution follows the canvas; `_field_toml` emits `[camera.scroll] enabled = true` (the borrowed wide-Range `camera.bgx` carries the rest). `py_compile` clean.
- **Packaging/docs:** add-on bumped **0.4.0** (3 sites + zip); README scrolling section + height-guide note. Vendor re-synced (drift-guard green). Commit `3cadcbf`.

**Next — the human step:** `py ff9mapkit/blender/build_addon.py` → install `dist/ff9mapkit_blender-0.4.0.zip` (Get Extensions → Install from Disk) → tick **Scrolling room**, set Canvas 768×448 → Setup/Pose → confirm the wide floor guide + height wireframe → Export → `ff9mapkit build` → optional in-game check. Then **multi-camera** remains the last planned camera-movement feature.

**Blender scrolling — VERIFIED in-game (add-on v0.4.1).** User installed it, authored a scrolling room (768-wide camera + a reshaped wide walkmesh), exported, built via the CLI, and **the deploy scrolled correctly in-game** ("the deploy worked"). Two first-run usability bugs found + fixed along the way (v0.4.1, commit `c19b9bb`): (1) **Export path** — Blender 5.x rejects the `//` blend-relative prefix on the StringProperty (red field) and it silently fell back to `~/ff9field`; default is now a plain `ff9field` resolved next to the `.blend` in `_resolve_out_dir` (no reliance on `bpy.path.abspath('//')`). (2) **CLI** — the installed `ff9mapkit` console script's Scripts dir wasn't on PATH; added `ff9mapkit/__main__.py` so **`py -m ff9mapkit build …`** works anywhere (also `pip install -e ff9mapkit`). Gotcha for users: the add-on only bakes in background art that's a **saved PNG added via Add Background Layer** — texture-painted-but-unsaved Blender images are skipped (the user's first paintover was a 384-wide guide-on-gray, wrong for a 768 scroll room). `tools/deploy_user_scroll.py` (commit, LF note) deploys a Blender export on its own walkmesh + a matched checker + regenerates a correct full-width guide, for testing before the art is painted. The Blender scrolling feature is COMPLETE + in-game-verified.

**Open with the user:** circle back to the walkmesh adjustment + paint a real wide background for their room (wide guide is in `…/debug_proj/scroll_test/paint_*_WIDE.png`). Then **multi-camera** is the last planned camera-movement feature.

**Fully closed out (in-game verified):** user painted a real wide background (back+front layers, 3072×1792) + reshaped the walkmesh to a trapezoid, and it renders + scrolls + occludes correctly on field 4003 ("all clear"). Three more first-run add-on fixes shipped (v0.4.2 `76cb8bb`, v0.4.3 `de70c63`): **Clear Background Layers** now also turns off `show_background_images` + clears the FF9 camera by name + tags a redraw (the camera preview persisted before); **Export** calls `obj.update_from_editmode()` so a walkmesh reshaped in Edit Mode exports its CURRENT shape (Blender keeps live edits in the bmesh until you leave Edit Mode — the trapezoid first exported as the stale rectangle). New general `tools/deploy_field.py <toml>` builds+deploys any field.toml to 4003 reversibly (reverts the prior 4003 test first). Field 4003 holds the user's painted trapezoid MY_ROOM; revert via `py tools/scroll_out/revert_deploy.py`. **Blender scrolling = production-verified end to end.** Next: multi-camera, or more content.

### 2026-06-04 — Session 16 — IMPORT ANY FF9 FIELD (Tier-3): offline p0data extraction → BG-borrow fork, proven in-game

**The headline capability landed: fork ANY of FF9's ~800 fields as an editable custom field — extracting its real camera + walkmesh + identity straight from the game data offline, with zero in-game/HW step — then drop your own content on it.** Proven end-to-end in real gameplay.

**How it started (the user's two questions):**
- *"Can I get a grasp on the design extremes the devs used?"* → mined all 817 HW field scripts (`reference/test2/`): camera yaw (SetControlDirection) is overwhelmingly head-on (545× zero) with a smooth tail to ~±90° and rare ±180°; **multi-camera is rare — ~8% of fields (56 use 2 cams, 8 use 3, 1 uses 4, max 4)**; scroll extents (SetCameraBounds) run from 1× screen up to ~2× each axis (640×224 streets, 320×560 towers, 624×416 plazas) — exactly what our scrolling already covers.
- *"If we build the full extractor, could the editor build from any level?"* → **yes.** Decomposed "a level" into camera (clean) + walkmesh (clean) + art (reuse = free via BG-borrow; repaint = heavy tail) + behavior (author fresh, don't import).

**The spike (proved the linchpin, committed `6d825c5`):** FF9's field assets live in `StreamingAssets/p0data*.bin` = **UnityRaw 5.2.3 assetbundles** (UnityPy reads them; `py -m pip install UnityPy`). Field assets at `assets/resources/fieldmaps/<fbg>/` = `atlas.png` (Texture2D art) + `<fbg>.bgi.bytes` (walkmesh) + `<fbg>.bgs.bytes` (scene+cameras, per-language). **62 fields in one bundle; ~800 across the BG bundles (p0data141/15/…).** Cross-check was decisive: the camera decoded from GRGR's binary `.bgs` matched the engine's own `.bgx` export **byte-for-byte on every field** (proj 497, orient matrix, position, range, depth, viewport), and `decompose` → GRGR's exact pitch 49.6/FOV 42.2.

**Format facts (verified):** `BGSCENE_DEF` header (little-endian): `u16 sceneLength,depthBitShift,animCount,overlayCount,lightCount,cameraCount` then `u32 animOffset,overlayOffset,lightOffset,cameraOffset` then 12×i16 bounds — so **cameraCount@offset 10, cameraOffset@24 (absolute)**. Each `BGCAM_DEF` = **52 bytes**: `u16 proj; i16 r[3][3] (÷4096); i32 t[3]; i16 centerOffset[2]; i16 w,h; i16 vrpMinX,vrpMaxX,vrpMinY,vrpMaxY; i32 depthOffset`. Maps 1:1 onto the kit's `cam.Cam`.

**Built (the import pipeline, all committed):**
- `scene/bgs.py` (`b5b1ccd`): parse a real field's binary `.bgs` cameras (the 52-byte struct). Round-trip + real-GRGR-value tests, no game data shipped.
- `extract.py` (`229f02c`): `extract_field(name)` pulls cameras (via bgs) + walkmesh/player-start (via bgi) + area/mapid from any field, offline. UnityPy **lazy-imported** → core kit stays pure-stdlib. `write_field_project(name, name=…)` emits a ready-to-edit BG-borrow `field.toml` + `camera.bgx`.
- `build.py` BG-borrow mode (`bc15846`): `[field] borrow_bg = "<real mapid>"` → emits `FieldScene <id> <area> <MAPID> <name> <textid>` and ships **only the custom script** (no scene); the engine renders the real field's art+walkmesh+camera (proven Session-4 path). **Purely additive — 121 kit tests pass, golden builds byte-identical.**
- `tools/deploy_field.py` fixes (`6f13974`,`5a8505a`): borrow line's script name is dict **field 4** (not 3 — they coincided only when mapid==name); skip the empty borrow scene copy; **deploy + restore the dialogue `.mes`** (text block = dict field 5).

**Human verified (real gameplay, GRGR_FORK = field 4003):**
- Bare fork → **renders the real Gargan Roo cleanly + walkable** ("looks good"). The whole field was produced offline from p0data.
- + a `[[npc]]` Vivi with a custom line → **Vivi appears on the real GRGR floor and says "So this is Gargan Roo… it feels different, now that you're here."** ("good"). Full fork-then-author loop, from a ~20-line `field.toml`.

**The recipe:** `extract.write_field_project("<field>", name="<FORK>")` → edit the `field.toml` (add `[[npc]]`/`[[gateway]]`/`[[encounter]]`/dialogue within the reported walkmesh bounds) → `ff9mapkit build` → deploy. Art is **reuse-only** for now (BG-borrow renders the real art; editable repaint = the v1b atlas→composite decode, deferred).

**User steer (important):** *"don't fret so much on saving the state of these authored scenes… I just want to demonstrate functionality."* → move faster, stop being precious about preserving test scenes/painted layers; keep the LIVE install revertible (good hygiene) but don't agonize over authored artifacts.

**Open / next:**
- Carry-over: field 4003 = `GRGR_FORK` (Vivi) deployed; revert `py tools/scroll_out/revert_deploy.py`. Debug New-Game→Alexandria warp still active.
- UnityPy is now an extraction dependency (lazy; core kit unaffected).
- Remaining for the full Tier-3: a real `ff9mapkit import <field>` **CLI command** + a cached **field→bundle index** (so no bundle hint); the **camera-preset/survey library** (the other deliverable — all ~800 cameras → archetype presets + faithfulness ranges, now trivial given the extractor); **editable-art v1b** (atlas+overlay → composite PNG layers, OR lean on Memoria's PSD export); docs + project-memory capture of the p0data format.

Tagged `KNOWN_GOOD-s16-import-field`.

### 2026-06-04 — Session 16 (cont) — `ff9mapkit import` CLI + Blender "Import FF9 Field" (fork-and-author in Blender, in-game verified)

**Finished the import tool + wired it into Blender: fork any of 674 real fields, import into Blender, place content visually, export → walkable in-game.** User goal "finish the tool so we can try to get it working in Blender" — done end to end.

**CLI (`097e573`):** `ff9mapkit import <field>` (full FBG / bare mapid / unique substring) → ready-to-edit BG-borrow `field.toml` + `camera.bgx` + `walkmesh.bgi`, in ~2s. `ff9mapkit list-fields <pat>` to discover. Backed by a cached **field→bundle index** (`build_field_index`: scans all p0data bundles' container paths ONCE, ~10s, → `.ff9mapkit-field-index.json` next to the bundles; then instant). **674 importable field backgrounds** across 51 map codes (LDBM 70, ALXC 60, ALXT 38, TRNO/TSHP/CYSW/…). Auto-derives the fork name `<MAPID-first-token>_FORK`.

**Blender add-on v0.5.x (`ab15898` + polish `…`):** new **Import FF9 Field** operator — point it at an `ff9mapkit import` folder; it parses `camera.bgx` → poses the real camera, `walkmesh.bgi` → an editable Blender mesh (`bridge.bgi_walkmesh_to_blender`, bpy-free + round-trip tested), sets `borrow_bg` (so Export emits a borrow `field.toml`), drops an FF9_Spawn at the field's start, and remembers the project dir so the EXACT extracted `camera.bgx` is preserved on export. Place NPC/gateway/spawn markers → **Export Field** → borrow `field.toml`. UI: "New Scene / Import Field" + a "forked from …" banner.

**Human-verified IN-GAME (the whole loop, no text editing):** imported real Gargan Roo in Blender → dropped a Vivi NPC empty at `[866,537]` + typed "YIPPEEE" → Export → `deploy_field.py` (now also deploys the dialogue `.mes`) → walked field 4003: **Vivi stood where placed in the Blender viewport and said the line.** ("it worked in game.")

**Camera-PREVIEW polish (two real bugs, user-confirmed fixed):**
- v0.5.1: the matched FF9 camera was shown through Blender's default **1920×1080 landscape**; Setup/Pose/Import now set render resolution to the field canvas (384×448 portrait / scroll canvas).
- v0.5.2: imported walkmesh sat in a CORNER. Root cause (diagnosed offline): a real `.bgi`'s verts are in a **corner-origin local frame** (`x[0,4170] y[0,2135] z[0,1502]`, and NOT flat — GRGR has real height) while the extracted **camera is in the centred world frame**; the engine reconciles them via the BGI `orgPos`/`curPos`, but the Blender pose didn't, so the camera aimed off the floor. Fix: a **position-only camera reframe** — slide the camera so its view axis hits the walkmesh centroid (yaw/pitch + the preserved `camera.bgx` untouched → in-game movement/camera unaffected; markers stay in the working export frame). User: "looks great."

**New surface:** `scene/bgs.py`, `extract.py` (`extract_field`/`write_field_project`/`build_field_index`/`resolve_field`/`list_fields`), `build.py` `borrow_bg` mode, CLI `import`/`list-fields`, `bridge.bgi_walkmesh_to_blender`, Blender Import operator + borrow export. UnityPy is the only new dep (lazy — core kit + Blender stay stdlib/bpy). 122 kit + 32 blender tests pass.

**Honest gaps (deferred):** the imported Blender preview is BARE (no field art behind the walkmesh) — that's the **editable-art v1b** (atlas+overlays → composite PNG layers, OR Memoria's PSD export). Real walkmesh height shows as 3D geometry (correct, just not a flat plane). Borrow mode = reuse art only (can't repaint yet).

**Honest gaps (deferred):** the imported Blender preview is BARE (no field art behind the walkmesh) — that's the **editable-art v1b** (atlas+overlays → composite PNG layers, OR Memoria's PSD export). Real walkmesh height shows as 3D geometry (correct, just not a flat plane). Borrow mode = reuse art only (can't repaint yet).

**Carry-over:** field 4003 = `GRGR_FORK` (Blender-authored YIPPEEE NPC) deployed; revert `py tools/scroll_out/revert_deploy.py`. Debug New-Game→Alexandria warp still active. UnityPy required for extraction (`py -m pip install UnityPy`).

Tagged `KNOWN_GOOD-s16-blender-import`.

### 2026-06-04 — Session 16 (cont) — Import walkmesh FRAME cracked (universal `vert + orgPos`); simple-field fork validated in-game

**The headline:** the rule that places an imported real field's walkmesh on its painted art is **universal: `world_vert = vert + orgPos`** — and a SIMPLE-walkmesh field (GLGV / Gizamaluke's Grotto) now forks end-to-end and is **walkable + content-correct in real gameplay**. User's scope caveat (kept honest): this is proven for *simple single-floor fields*, NOT yet complex multi-floor ones.

**The frame problem + the long path to it (all offline, art-as-ground-truth via the user's eyes):**
- A real `.bgi` stores walkmesh verts **CORNER-ORIGIN** (0-based, e.g. GRGR x[0,4170]); the header **`orgPos` (== `minPos`) is the world position of that corner**, so `world_vert = vert + orgPos`. Verified universal: `vert + orgPos == [minPos, maxPos]` for every sampled field (GRGR/BMVL/GLGV/BRMC/TRNO), and `FieldMapActor` projects the player/walkmesh in WORLD via the camera, so `cam.to_canvas(vert + orgPos)` is exactly where the walkmesh appears in-game. **Confirmed in-art: GLGV at `+orgPos` "nailed it."**
- **Detours that were WRONG (so don't repeat):** (1) a uniform `orgPos/2` slide (eyeballed "f52" — it can't fix x and z in opposite directions); (2) plain `f0`/raw (looked right on GRGR only because GRGR's spawn dot is a world coord that sits on-screen at *either* framing, and GRGR's 7 overlapping floors read as a "stack" at *any* frame — complexity, not framing); (3) an `f0`-vs-`+org` auto-DETECTOR (on-canvas heuristic ties on simple fields and chose wrong — GLGV needed `+org` but it picked `f0`). The clean answer is just **always `+org`**; detector deleted.
- **Art-placement check (ruled out as the culprit):** `FieldSceneExporter.cs:255` places each exported `Overlay*.png` PSD layer at **`(curX, curY)`**, NOT `orgX/orgY + minSpriteOff`. For GRGR these coincide (`curX==orgX`, `minOffX==0`) so the composited backdrop was already correct — the misalignment was the walkmesh frame, not the art.
- **`charPos` (debug spawn) is itself per-field** — sometimes corner (GRGR), sometimes already world (GLGV: `charPos.x=-856` is outside the corner vert range), and often sits in a **gated off-screen tunnel** (a real walkmesh runs far past the visible screen). New spawn logic: prefer `charPos` only if in-bounds AND on-camera; else spawn at the **centre of the ON-CAMERA walkmesh**; else centroid.

**Tools (committed; 122 tests green):** `cam.walkmesh_world_offset(org)` (the rule, with the rationale baked into the docstring for the exporter). `extract.extract_field`/`compose_background` auto-apply `+orgPos` to the footprint, walkmesh, reported bounds, and spawn (now on-camera). `bridge.bgi_walkmesh_to_blender(bytes, offset)` + `walkmesh_frame_offset` (Blender import shifts the mesh into world; kit-built walkmeshes default offset 0 so golden tests are untouched). Add-on bumped to **v0.5.7**. Commits `609a06a`(f0 detour) `666f7b3`(detector detour) `4b15a92`(**the rule**) `67cdfda`(robust spawn+v0.5.7) `068bdbd`(on-camera spawn).

**Human verified IN-GAME (GLGV_FORK = field 4003, deployed via the interior door):** grotto renders clean ✓; walkable ✓; **Vivi stands ON the painted floor** at walkmesh `(3082,273)` ✓; dialogue ✓; spawn now lands **on-camera** (auto-fixed from the off-screen tunnel). First arbitrary forked field (one we'd never touched) taken fork → `+org` frame → author NPC → in-game with content landing where placed.

**Honest scope (user's correction — do NOT overclaim "fork-any-field"):**
- ✅ **Simple single-floor walkmesh fields** (GLGV: 1 floor, 51 verts, scrolling, area 36) — reliable end-to-end.
- ⚠️ **Complex multi-floor fields** (GRGR's 7 floors) import with a CORRECT frame but read as a dense **stack** in Blender — not yet legible/authorable. (Floors are distinct/tiled, just densely packed in projection + a wireframe.) Next-lever candidate: color-by-floor + keep real 3D height so they're orbitable.
- ⚠️ **BRMC** "walkmesh doesn't go deep enough" — unconfirmed whether a real residual or just its walkable area being a subset of the painted room.
- ⚠️ **Blender 3D-camera cosmetic offset** — head-on fields (GLGV pitch ~1°) need a small Blender-view nudge (user calibrated GLGV ≈ Blender `Z+42` = FF9 height); it's the FF9 3D-char-vs-2D-BG / pinhole≈GTE residual. **Cosmetic for content** (NPCs key off floor x,z, which the exact `to_canvas` footprint nails); not folded in.

**Carry-over:** field 4003 = `GLGV_FORK` (Vivi on floor) deployed; revert `py tools/scroll_out/revert_deploy.py`. Debug New-Game→Alexandria warp still active. Add-on dist = `ff9mapkit_blender-0.5.7.zip`. Diagnostics in `tools/grgr_*.py` (GRGR frame/floor analysis), `tools/scroll_out/p0spike/*.png` (offline footprint comparisons, gitignored).

**Next options:** (a) complex-field readability (color-by-floor + real-3D in Blender) to extend past simple fields; (b) derive the per-camera Blender-view cosmetic offset; (c) editable-art v1b; (d) other content/world-wiring work.

Tagged `KNOWN_GOOD-s16-import-frame`.

**Lever (b) DONE — per-camera Blender-view offset auto-derived (human-verified "flawless").** Blender's pinhole camera ≠ FF9's exact 2D-BG projection (`cam.to_canvas`), so the imported walkmesh lands a few px off the painted art — worst for head-on cameras (the user hand-calibrated GLGV ≈ Blender `Z+42.188`). `bridge.walkmesh_view_offset(bgi_bytes, c)` **fits the 3D offset `D` offline** (coordinate-descent: Blender-pinhole vs `to_canvas` over the floor verts; modelled `_blender_pixel` reproduces Blender's sensor_fit=HORIZONTAL projection). Derived GLGV `Z=+42.8` (matches the user's +42.188), BRMC `+33.8` (pure height), GRGR `(−2.8, 125, 80)` (tilted → height+depth). **Applied as `camera.location -= D`** (object+D ≡ camera−D), so the VIEW aligns while the walkmesh + content stay in the raw engine frame — content unaffected (the tilted-camera `D` has a depth term that would corrupt content if moved on the mesh). Also **stopped flattening** the imported mesh (keep real world height, which the fit + matched camera assume; GRGR's floor is at world-Y −2135). Add-on **v0.5.8**; commit (view-offset) on master. **Verified in Blender: GLGV lands on the floor out-of-the-box, no manual nudge.** Tagged `KNOWN_GOOD-s16-view-offset`. Remaining levers: (a) complex-field readability, (c) editable-art v1b.
