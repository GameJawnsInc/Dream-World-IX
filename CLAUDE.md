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

**Lever (a) DONE — multi-floor fields now import COHERENT (human-verified "flawless"); the "stacking" was a real positioning bug.** Started as a readability task (color-code the floors), but color-by-floor *revealed* the floors were genuinely **mis-positioned**, not just cluttered. Root cause: a real `.bgi` stores **each FLOOR's verts CORNER-ORIGIN in the floor's OWN frame** (disjoint vertex sets, each 0-based; GRGR's 7 floors = 41+6+19+31+36+20+16 = 169 = total), and **`floor.org` tiles the floors** — I was applying only the single header `orgPos`, piling the disjoint floors on top of each other. Fix: **`BgiWalkmesh.world_verts()` = `vert + orgPos + floor.org` per vert.** Verified: every GRGR vert lands EXACTLY inside the header `[minPos,maxPos]`, and the 7 floors tile into a coherent centred tunnel (centroids x≈0, z −1555..1191). **Single-floor fields have `floor.org=(0,0,0)` → GLGV byte-identical** (bounds/spawn unchanged). Wired through the footprint, extract bounds/spawn, the Blender mesh + the view-offset fit; supersedes the single-offset `cam.walkmesh_world_offset`. Plus **color-by-floor** in Blender (`bridge.walkmesh_floor_ids` → per-face material + viewport Solid/Material) for legibility, and **stopped flattening** the imported mesh (real world height). Add-on **v0.5.10**; 122 tests pass; GLGV preserved. **Verified in Blender: GRGR's 7 floors assemble into a coherent connected tunnel.** Tagged `KNOWN_GOOD-s16-multifloor`.

**Scope now:** the importer handles **both simple AND complex multi-floor fields** — the "simple fields only" caveat is lifted. **Multi-floor loop CLOSED in-game (human-verified "good"):** deployed the GRGR fork (7 floors) to field 4003, dropped Vivi at world `(-367,-1009)` (from `vert+orgPos+floor.org`), and she's **planted on the central floor** in real gameplay + talks; player spawns on-floor. So `vert+orgPos+floor.org` is the engine's content frame for multi-floor fields too, not just Blender. Tagged `KNOWN_GOOD-s16-multifloor-ingame`. **Re-validated in-game across 3 multi-floor fields:** GRGR (7 floors), BRMC (3 floors, "perfect" — its old "not deep enough" was the stacking bug; the tiled floors now run deep), BMVL (4 floors, "looks great" — was "way off" before). All render + align + Vivi-on-floor. (BMVL placed Vivi behind a desk so dialogue was unreachable — a content-placement quirk of the auto-placer picking the far floor vert, not a frame issue; real authoring places NPCs in reachable spots via the Blender art view.) Remaining: (c) editable-art v1b; the kit's `extract`/`build` docs could note the per-floor write side for the exporter.

### 2026-06-04 — Session 17 — EXPORTER: faithful multi-floor `.bgi` writer (offline-proven + in-game validated)

**The write side of the toolkit now matches the read side.** Built `bgi.build` — a general multi-floor, WORLD-frame walkmesh writer that is the exact inverse of the importer (`BgiWalkmesh.world_verts`): emits verts in world coords with `orgPos=0` + every `floor.org=0`, so the engine renders them verbatim. **Confirmed from engine source (`WalkMesh.cs:53,141,227`): `world = vert + floor.org + bgi.orgPos`** (collision uses `*.cur`, equal for static fields).

**Done (offline, 132 tests):**
- `bgi.build(verts, faces, floor_ids=...)`; `load_obj_floors` (one floor per `o`/`g`); Blender export maps each material slot → a floor. `build_flat` kept byte-identical (legacy header `(0,0,300)`) so the calibrated flat-room pipeline is unchanged.
- **Round-trip proven**: import → export → re-import reproduces world positions EXACTLY + topology + floor partition (hut 1-floor, editor 3-floor).
- **Ripped two false assumptions** (user's ask): the bogus `bgi.py` "NO orgPos shift / ZERO offset" comment (the engine DOES apply orgPos+floor.org) and the dead `cam.walkmesh_world_offset` (superseded single-offset model).
- New `[walkmesh] frame = "world"` option (single-floor obj/quad → org=0); default legacy unchanged. Engine facts: `minPos`/`maxPos` runtime-UNUSED; `charPos` = debug spawn; `curPos`/`floor.cur` diverge only for moving platforms.

**Human verified IN-GAME (GLGV_EXP = field 4003):** GLGV forked as a full CUSTOM SCENE (not borrow) whose `.bgi` was RE-EXPORTED via `bgi.build` (org=0; world positions match the real GLGV walkmesh **delta=0**) + real camera + composited art. **"looked good"** — renders + walkable + walkmesh aligned. (Vivi off-screen = the known auto-placer coordinate quirk, content not exporter.) → **the exporter is engine-validated.** Tagged `KNOWN_GOOD-s17-exporter`.

**FOUND (deferred — needs in-game recalibration, §2):** the novel-room path's `orgPos=(0,0,300)` + `CHARACTER_GROUND_OFFSET_Z=298` are a near-cancelling **double-count** — the char-offset has been compensating for the +300z the writer injects, not a real 3D-char residual; the cancellation is camera-dependent (likely the off-angle back-edge drift). Ripping it (org=0 + offset≈0) would simplify + probably fix off-angle drift, but moves verified geometry → flagged for a future playtest (the second test option offered this session).

**Occlusion (user Q):** the composited-art custom-scene fork loses per-overlay occlusion because `compose_background` MERGES the field's depth-layered overlays into ONE flat layer — NOT an atlas-unpacking limit. Fix = **multi-layer extract** (one `[[layers]]` per overlay at its real `.bgs` depth; the kit already supports per-layer z — e.g. the hut front wall occludes the player). That's the "editable-art v1b" next step.

**Carry-over:** field 4003 = GLGV_EXP (revert `py tools/scroll_out/revert_deploy.py`). Debug New-Game→Alexandria warp still active.

### 2026-06-04 — Session 17 (cont) — Editable-art v1b: occlusion-preserving custom-scene fork PROVEN in-game

**Forking a real field as a fully EDITABLE custom scene — WITH occlusion — now works.** The first GLGV_EXP (flat composite) lost per-overlay occlusion because `compose_background` merges every overlay into ONE back layer. Fix = `extract.extract_layers()`: group the field's overlays by DEPTH, write one transparent full-canvas PNG per distinct depth, emit one `[[layers]]` each. Depth+position come straight from Memoria's OWN `.bgx` exporter (`BGSCENE_DEF.cs:606`): `z = scene.orgZ + overlay.orgZ + min(sprite.depth)`, `position = scene.org{X,Y} + overlay.org{X,Y} + min(spriteOff)`. **No kit-schema change** — `[[layers]]` already supports per-layer position/size/z (the same mechanism a painted room's front-wall occluder uses). Opaque-only first pass (skips additive light/shadow; GLGV has 0 blend overlays → complete for GLGV).

**Human verified IN-GAME (GLGV_EXP = field 4003: 5 depth layers z=698/873/1182/3398/4088 + the re-exported walkmesh + GLGV's real camera):** renders ✓, **occlusion restored — foreground pieces draw OVER the player** ✓, matches the borrow version ✓, walkmesh aligned + Vivi talks ✓ (user: "good" ×4). → the editable-art (v1b) custom-scene fork is engine-validated; any single layer (e.g. `layer_00698.png`) can be repainted without touching the rest. Tagged `KNOWN_GOOD-s17-editable-art`.

**Next options:** generalize into a CLI (`ff9mapkit import --editable <field>` → the occlusion-preserving custom scene for any field, walkmesh re-exported + layers + camera); a second pass for additive light/shadow overlays (blend shaders); Blender repaint loop; or the deferred `orgPos(0,0,300)`≈`character_offset 298` cleanup. Carry-over: field 4003 = GLGV_EXP (multi-layer); revert `py tools/scroll_out/revert_deploy.py`.

### 2026-06-04 — Session 17 (cont 2) — `import --editable` PRODUCTIZED (CLI; offline-validated by equivalence)

The GLGV editable-fork proof is now a first-class command: **`ff9mapkit import --editable <field>`** forks ANY exported field into a fully editable custom scene. `extract.write_editable_project()` = re-export the walkmesh (world frame, `_world_walkmesh_obj_text` + `[walkmesh] frame="world"`) + `extract_layers()` (per-depth repaintable art, occlusion preserved) + reuse the real camera → a custom-scene `field.toml`. No in-game re-test needed: **dogfooded** `import --editable glgv_map792_gv_rm1` builds to the SAME scene as the in-game-proven GLGV_EXP (5 depths 698/873/1182/3398/4088, walkmesh org=0). BG-borrow `import` unchanged (art-reuse fork). Docs: PIPELINE.md "fork a real field" section. 133 tests (+1 multifloor world-obj round-trip). The full **import↔export round trip is now a two-line CLI** (`import --editable` → edit → `build`).

### 2026-06-04 — Session 17 (cont 3) — Stress test: blend pass + multi-floor connectivity fix + walkmesh-editing spec

**Stressed `import --editable` across blend-heavy + multi-floor fields; found + fixed two real edge cases, both in-game-validated, and specced the remaining gap.**
- **Light/shadow (blend) pass.** Offline sweep found opaque-only extraction dropped GRGR's **5 of 7** overlays. `extract_layers` now groups overlays by **(depth, shader)** and emits ALL of them; shader from Memoria's own `.bgx` exporter (`BGSCENE_DEF.cs:611`): `Abr_None` opaque, else `Abr_{min(3,alpha)}` (additive/subtractive); the `.bgx` importer honors `Shader:` (`cs:321`). Sweep: GRGR 2→7 layers, BRMC/BMVL +2, GLGV unchanged. **In-game: GRGR torch glows + shadows render — user "the lights look good."**
- **Multi-floor connectivity bug — FOUND in-game, FIXED.** GRGR rendered but the player was **trapped on the central floor** (couldn't reach the side tunnels). Cause: re-export via `.obj`→`bgi.build` rebuilds neighbor links by **shared vertex INDEX**, but FF9 floors use **disjoint vertex sets** → cross-floor seams vanish. Fix: `[walkmesh] bgi = "<file>"` mode ships a real walkmesh **verbatim**; `import --editable` uses it (GRGR: 468 links intact, all 7 floors reachable). **In-game: "everything is connected again."** `bgi.build` re-export stays for authoring NEW geometry. Tagged `KNOWN_GOOD-s17-multifloor-fork`.
- **Honesty locked in.** The `.bgi` codec is lossless; only the `.obj` intermediate drops the adjacency graph (which isn't a function of geometry). Build-time guard `BgiWalkmesh.reachable_floors()` (BFS over `tri.nbr`) → `build` warns on stranded floors (turns the in-game trap into a build warning). Tests assert the known loss. **Spec for editable multi-floor reshaping** (`.obj` + position-keyed adjacency sidecar, v1 shipped / v2-v3 designed): `ff9mapkit/docs/WALKMESH_EDITING.md`. 136 tests. Memory `project-ff9-import-frame` updated.

### 2026-06-04 — Session 17 (cont 4) — Floor-seam RESEARCH: spec validated game-wide + a guard bug fixed

**Researched + smoke-tested the v2 floor-seam design against ALL 674 fields before anyone builds it — all offline (engine source + p0data), squarely Claude-ownable.**
- **Engine source (`WalkMesh.cs`):** `BuildFromBGI` **copies `tri.nbr` verbatim; never recomputes from geometry** → the `.bgi` links ARE the connectivity, and the kit's `reachable_floors()` BFS models it exactly. Cross-floor links are just `nbr` entries pointing across floors (edge convention `GetVertexIdxForEdge` == kit `SLOT_PAIRS`).
- **Game-wide sweep (`tools/sweep_seams.py`):** 674 fields, **550 multi-floor (1–23 floors)**. **Floors ALWAYS disjoint-vertex (674/674)** → `rebuild_neighbors` can never recover a cross-floor seam (verbatim ship is the only correct fork, confirmed). 5983 seams: **0 shared-index, 5956 coincident, 27 bridge — all in ONE field** (`udft_map120`, 23-floor vertical shaft: same X/Z, different Y). **Seam edge flags ALWAYS 0** → no edge-flag carry needed. Net: **v2 is simpler than drafted** (drop `[[edge_flag]]`; `[[seam]]` 3D-position keys cover coincident + vertical-bridge).
- **Reconcile smoke test (`tools/smoke_reconcile.py`):** prototyped extract-seams + position-keyed reconcile; **reproduces the original's EXACT cross-floor link set** (missing=0, link-set identical) on 3/4/7/23-floor fields → the v2 design is sound.
- **Found + fixed a v1 guard bug:** connectivity ≠ reachability — UDFT walk-reaches only **9/23** floors (rest are script/warp-reached). My build reachability warning would false-positive on a *correct* verbatim UDFT fork. Fix: the guard now **skips verbatim `[walkmesh] bgi`** (authoritative original) and only checks (re)built obj/quad/auto walkmeshes. Tests: `_for_obj` warns, `_for_verbatim_bgi` doesn't. 137 tests.
- Spec updated with a "Research findings" section; memory `project-ff9-import-frame` updated. Tools `analyze_seams.py`/`sweep_seams.py`/`smoke_reconcile.py` committed. **Conclusion: the position-key v2 design is validated end-to-end offline; ready to build when wanted.**

### 2026-06-04 — Session 17 (cont 5) — v2 BUILT: seam sidecar + reconcile (editable multi-floor walkmesh)

**Built the v2 reshape path** so a forked multi-floor walkmesh can have its GEOMETRY edited while keeping cross-floor connectivity (the research de-risked it; this ships it). All offline, 140 tests.
- **Codec:** `BgiWalkmesh.extract_seams()` (cross-floor seams as sorted WORLD-position edge pairs) + `apply_seams(seams)` (re-link by position; sets nbr+edgeClone like rebuild_neighbors; returns linked/missing/misses).
- **Export:** `import --editable` now also writes `walkmesh.links.toml` (seams + `[header]` active_floor/tri + char_pos) for multi-floor forks. Default still ships `[walkmesh] bgi` verbatim (lossless); the field.toml documents the one-swap to the reshape path.
- **Build:** `[walkmesh] obj + links` → `bgi.build` (geometry + intra-floor links) then `_apply_links` reconciles the seams by position + restores header; **warns** (doesn't silently mis-link) on a moved/deleted seam. Reachability guard already gates to (re)built meshes.
- **Per research:** `[[edge_flag]]` omitted (seam flags always 0 game-wide); 3D position keys cover coincident + vertical-bridge.
- **Dogfooded on real 7-floor GRGR:** sidecar = 33 seams; switching to obj+links builds **7/7 floors reachable, no warnings.** Tests: extract/apply round-trip, build-obj+links reconciles, broken-seam warns. Docs (WALKMESH_EDITING.md v2→DONE, FORMAT.md `links` row, PIPELINE n/a) + memory updated. Tagged `KNOWN_GOOD-s17-walkmesh-v2`.

**Note:** v2 is OFFLINE-proven (reconcile reproduces the original's exact links + the dogfood builds connected). An actual *reshaped* multi-floor field hasn't been walked in-game yet — the reconcile is exact for unedited seams, so the next real test is a human editing a fork's floor interior + playing it. v3 remaining: anim carry, `walkmesh verify` CLI, Blender seam viz/re-anchor.

### 2026-06-04 — Session 17 (cont 6) — Build-time validation for user-EDITED forks (catch mistakes offline)

**Hardened the import→edit→re-export path so an altered fork fails LOUDLY at build, not silently in-game** (the only §2-legal lever — I can't see the game). All offline, 144 tests.
- **`bgi.build` ERRORS on broken geometry:** empty mesh (no verts/faces), or a face referencing an out-of-range vertex index — clear messages instead of a cryptic crash (catches mis-edited `.obj`s).
- **Content-placement WARNING — the big one** (catches the recurring in-game pain: Vivi off-screen / behind-desk / player-in-exit-zone): `BgiWalkmesh.point_on_walkmesh(x,z)` (top-down point-in-triangle over `world_verts`) → `build` warns when an NPC / player spawn / gateway-zone-centre sits **off the walkmesh**. Verified **no false-positive** on real in-game-OK content (GRGR Vivi (-367,-1009)→floor 3, spawn (404,127)→floor 0; (9000,9000)→off). Honest limit: catches OFF-mesh, not on-mesh-but-blocked.
- **Zero-area-triangle WARNING:** `degenerate_tris()` flags collinear verts → IsInQuad dead zones (the bug we hit in gateway work), gated to (re)built meshes.
- All wired into `build_field` warnings (content always for custom scenes; degenerate/reachability gated to non-verbatim). Docs: PIPELINE.md "the build checks your work". Tests: bad-geometry rejects, point/degenerate behavior, off-walkmesh warns, on-walkmesh doesn't. Tagged `KNOWN_GOOD-s17-edit-validation`.

### 2026-06-04 — Session 17 (cont 7) — Off-walkmesh guard made UNIVERSAL (borrow forks too)

**Closed the gap: the off-walkmesh content warning now covers BG-borrow forks** — the common case — not just custom scenes. A borrow fork ships no walkmesh (engine uses the borrowed field's real one), but `import` already wrote the extracted `walkmesh.bgi` next to the field.toml, so the build validates content against it.
- `build._borrow_walkmesh(project)` loads `[walkmesh] reference` (if set) else the sibling `walkmesh.bgi` (zero-config convention); `build_field`'s borrow branch runs `_validate_content_placement` against it.
- `write_field_project` (borrow import) now emits a `[walkmesh] reference = "walkmesh.bgi"` block (clearly labeled validation-only, not shipped); `validate()` checks the reference file exists.
- Tests: borrow fork warns on an off-mesh NPC (via `reference` AND via the sibling convention), no warning on-mesh. 147 tests; no vendor change. Tagged `KNOWN_GOOD-s17-borrow-validation`.

### 2026-06-04 — Session 17 (cont 8) — Art/layer sanity: the last common edit is guarded

**Completed the "every common fork edit is validated" goal** — added a repaint check, so the build's validation layer now covers content placement (NPC/spawn/gateway), walkmesh geometry/connectivity/seams, AND art. All offline, 149 tests.
- **The real repaint bug = aspect-ratio mismatch:** the engine maps a layer's PNG onto a `size`-logical quad (BGSCENE overlay mesh), so a repaint at a different aspect is non-uniformly STRETCHED / misaligned. `build._validate_layer_art` warns when a layer PNG's aspect != its `size` aspect (size defaults to the camera canvas; convention = PNG size×4). `_png_size` reads the PNG IHDR header directly — **no PIL dependency** (build stays stdlib).
- Wired into the custom-scene build block (after content placement). Tests: wrong-aspect PNG warns, size×4 PNG doesn't. PIPELINE.md "the build checks your work" updated. Tagged `KNOWN_GOOD-s17-art-validation`.

**The build-time validation suite (the full "altered export" safety net) is now:** geometry errors (empty/bad-index) · content off the walkmesh (all forks) · stranded floors · broken seams · zero-area tris · layer aspect mismatch · camera pitch range. Every common edit a user makes to a fork is caught offline before playtest — the strongest §2-legal guard, since I can't see the game.

### 2026-06-04 — Session 18 — v2 multi-floor RESHAPE proven in-game (last offline-only gap closed)

**The one part of the import→edit→re-export toolkit that was only OFFLINE-proven — reshaping a multi-floor fork's geometry while keeping cross-floor connectivity (v2 seam sidecar) — is now IN-GAME verified.**

**Aside first (user Q: "did we build a general GTE↔3D converter or is it FF9-specific?"):** answered from the code. **General kernel** (textbook, would port to any pinhole system): `cam.project/decompose/synth_r_t` (the PSX GTE RTPT *is* a fixed-point pinhole projection; decompose/synthesize = standard extrinsic/intrinsic recovery) + `bridge.blender_cam_to_ff9`/`ff9_cam_to_blender` (a change-of-basis between two camera conventions + FOV↔focal). **FF9-specific shell** (the actual product value): `K_VSCALE=14/15` (FF9's anisotropic vertical-focal baked into orientation row 1), Int16/Int32 fixed-point byte-faithfulness (`.bgx`/`.bgs` format), the double y-flip `F`, `to_canvas`/`compute_offset` (Memoria FieldMap composite offsets, incl. the −112), `COLLISION_RADIUS_W=48` + `CHARACTER_GROUND_OFFSET_Z=298` (engine quirks). Verdict: a "FF9 field camera ↔ Blender camera" bridge — skeleton general, calibration is the product. Easy port to another PSX-GTE game (swap K, keep fixed-point); to a modern engine the kernel is just standard camera math that already exists everywhere.

**Done (no kit code change — used the existing CLI + v2 path, proving it in the live engine):**
- Forked GRGR central (`grgr_map420_gr_cen_0`, 7 floors) via `ff9mapkit import --editable` → custom scene (7 art layers, 5 light/shadow) + `walkmesh.obj` + the 33-seam `walkmesh.links.toml`.
- **Baseline check** (reshape path on UNEDITED geometry): switched the field.toml to `[walkmesh] obj + links + frame="world"` → build → **7/7 floors reachable, no warnings** (so any later break = the reshape, not the path).
- **The reshape:** moved floor-0's +x/+z boundary vertex (1-based 16) `(944,521) → (1340,627)` directly in `walkmesh.obj` (outward along the centroid ray; verified non-degenerate, no triangle flip). Rebuilt via obj+links. Offline: **7/7 floors still reachable** (seams reconciled by world-position, endpoints unmoved) + the extended corner is walkable (`point_on_walkmesh(1100,560)/(1250,600) → floor 0`, previously off-floor).
- Deployed reversibly to field 4003 via `tools/deploy_field.py` (interior-door repoint, backups, `tools/scroll_out/revert_deploy.py`).

**Human verified (real gameplay):** renders (Gargan Roo + lights/occlusion) ✓; **"I can walk further"** (reshaped platform) ✓; **"I can still 'feel' the ramps along the stairs to the tunnels"** — cross-floor connectivity to BOTH side tunnels intact ✓. → the v2 position-keyed seam reconcile holds through a real geometry edit in the live engine, not just offline. **This was the last unproven piece of the fork→edit→build pipeline.**

**Found (flagged, NOT fixed — user chose "Quick CLI proof first"):** the **Blender add-on's import→export path isn't wired for editable multi-floor reshape**: (1) Import only loads a single `background.png`, not the per-depth `layer_*.png` → art dropped on re-export; (2) Export writes `[walkmesh] obj` but NOT `links` + `frame="world"` → a reshaped multi-floor mesh strands floors; (3) Export hardcodes `character_offset=298` onto a forked real field (already in the engine frame) → would shift it. Fixing this = the natural next task to make the *Blender* reshape loop work end-to-end (the CLI loop already does).

**Convenience (debug-only):** `tools/alex_fast_warp.py` — repoints Alexandria's hut door `Field(4000)→Field(4003)` (skips the 2 hut hops) + moves the New-Game spawn (block B / entrance 231, located by byte-stride signature since earlier edits shifted the offsets +6) onto the door `(0,332)→(−250,2100)`. New Game → spawn at door → step in → 4003. Reversible (`tools/scroll_out/revert_alex_fast_warp.py`). Real exits 101/107/114 untouched.

**Engine/game state:** Session-12 dev engine (New-Game→100 + boosters). Live FF9CustomMap: field 100 door now → 4003 + spawn-at-door (fast-warp); field 4003 = GRGR_EDIT reshaped fork (revert `tools/scroll_out/revert_deploy.py`); 4000/4002 hut rooms intact. Tagged `KNOWN_GOOD-s18-reshape-ingame`.

**Next options:** (a) wire the Blender editable-multi-floor reshape path (the 3 gaps above) so the visual loop matches the CLI; (b) collision-radius-edge content warning (on-mesh-but-near-edge); (c) v3 walkmesh (`walkmesh verify` CLI, Blender seam viz); (d) revert the test field + fast-warp and move to other content/release work.

### 2026-06-05 — Session 18 (cont) — Blender editable-fork reshape VERIFIED in-game (full CLI parity)

**The offline parity work is now in-game-proven.** User installed add-on v0.6.0, ran `ff9mapkit import grgr_map420_gr_cen_0 --editable`, **Import Field** in Blender, reshaped a floor, **Export Field**, deployed to 4003, and walked it: renders (real Gargan Roo art), the reshape is present + walkable, and **all 7 floors still connect**. So the Blender front-end now round-trips an editable multi-floor fork identically to the CLI — both loops proven in the live engine.

**Blender export confirmed correct:** the exported toml was `[walkmesh] obj + links + frame="world"` (no character_offset) + per-depth `[[layers]]` with shaders + preserved `camera.bgx` — exactly the parity code. Build: no warnings, 7/7 reachable.

**Also fixed a deploy-tool footgun (`tools/deploy_field.py`, commit `8a182cc`):** it had (a) run "the newest `revert_*.py`", which picked up `revert_alex_fast_warp.py` and undid the Alexandria shortcut — now it runs ONLY its own `revert_deploy.py` so the fast-warp (which points at 4003) survives field deploys; and (b) asserted a `Field(≠4003)` existed in the interior door — crashing when a prior deploy already left it 4003 — now idempotent (already-4003 = no-op). Surfaced exactly because this was the first deploy *after* the fast-warp existed.

**Light-map preview caveat (cosmetic):** additive light/shadow layers show flat in Blender's viewport (its background images don't additive-blend) but render additive in-game (the shader is carried through export→build, asserted by `test_editable_fork`). Not a correctness issue.

**State:** field 4003 = the Blender-reshaped GRGR (7/7 floors); Alexandria fast-warp active (door→4003 + spawn at door); add-on v0.6.0. Tagged `KNOWN_GOOD-s18-blender-reshape-parity`. The import→edit→re-export toolkit is now complete + in-game-proven from BOTH the CLI and Blender.

**Next options:** collision-radius edge content warning (on-mesh-but-near-edge); v3 walkmesh (`walkmesh verify` CLI, Blender seam viz); or revert the test field + fast-warp and move to other content/release work.

### 2026-06-05 — Session 18 (cont) — Collision-radius edge warning (offline tooling)

Added the last build-time placement guard: content **on** the walkmesh but within the player's collision radius (`cam.COLLISION_RADIUS_W` ≈ 48u = `bgiRad*4`) of a **wall** — the near-miss the point-in-walkmesh test passes but the player's centre can't actually reach. New `BgiWalkmesh.distance_to_boundary(x,z)` (min XZ distance to a no-neighbor edge of the floor the point is on; a cross-floor **seam** is not a wall). `build` warns **advisory** for NPCs + player spawn; **gateways are exempt** (an exit zone is edge-placed by design → would false-positive on every door). 4 tests; 157 pass; vendor synced. Commit `53db6bd`. Offline tooling, no in-game change → no tag.

**Validation suite now:** geometry errors (empty/bad-index) · content off the walkmesh (all forks) · content within the collision radius of an edge (NPC/spawn, advisory) · stranded floors · broken seams · zero-area tris · layer aspect mismatch · camera pitch range.

**Next options:** v3 walkmesh (`walkmesh verify` CLI, Blender seam viz); revert the test field + fast-warp + move to content/release work.

### 2026-06-05 — Session 18 (cont) — Walkmesh v3 (partial): `walkmesh verify` CLI + Blender seam overlay

Two v3 walkmesh tools (offline; bpy seam overlay awaits a glance in Blender per §2):
- **`ff9mapkit walkmesh verify <path>`** — runs the whole check suite standalone, no build. A `.field.toml` resolves the walkmesh exactly as build does (custom-scene obj/quad/bgi, or a BG-borrow fork's `reference`/sibling `walkmesh.bgi`) + runs content-placement + layer + reachability/degenerate checks; a raw `.bgi` reports geometry (floors, walk-reachable, stranded, seams, degenerate, bounds). Exits 1 on any warning (scriptable). Factored `build_field`'s reachability/degenerate block into `_validate_walkmesh_geometry`; added `_walkmesh_stats` + `verify_walkmesh`. Verified on the live GRGR fork (7/7 floors, 33 seams, clean) + raw `.bgi`.
- **Blender `FF9_Seams` overlay** — importing an editable multi-floor fork builds a bright amber wireframe of the cross-floor **seam edges** (`bridge.seam_edges_blender`, `show_in_front`, `hide_select`) so you can see which edges NOT to move when reshaping; panel note + import message report the count; auto-removed for single-floor forks. Add-on → **v0.6.1**.
- 161 tests (4 new: verify clean/off-mesh, seam-edges multi/single-floor); vendor synced; `docs/WALKMESH_EDITING.md` §5/§6 marked v3-partial. Commit `b5c59c5`. Offline → no tag.

**Remaining v3 (open):** anim/moving-platform carry; a Blender "re-anchor seam" operator + "suggest seams" for newly-added floors.

### 2026-06-05 — Session 18 (cont) — From-scratch path smoke-tested + polished; quad/floor offset bug fixed (in-game)

Re-exercised the **from-scratch** authoring path (`new` → `build`), unused for a while. Findings + fixes, in-game confirmed ("SMOKE is clear"):
- **First-run cliff:** `new` then `build` hard-errored on missing art. Fix: `new` now scaffolds pure-stdlib **placeholder art** (`scene/placeholder.py`: solid backdrop + perspective checkerboard floor matched to the template camera) + derives the walkmesh quad from that camera frame → a fresh scaffold BUILDS + is walkable immediately; human replaces the PNGs. Commit `5065a33`.
- **Walkmesh-vs-floor offset bug (real):** the explicit-`quad` path defaulted `character_offset` to **0**, but `bgi.quad`/`build_flat` injects `org=(0,0,300)`; the AUTO path defaults the offset to 298 which **cancels** the +300 (why painted rooms aligned), so the quad path left +300 uncancelled → walkmesh ~300u toward the floor's back (the user's asymmetric "back overshoots / front undershoots" under perspective). Fix: quad path now defaults `character_offset` to `CHARACTER_GROUND_OFFSET_Z`, matching auto. Verified offline (walkmesh canvasY 204.9/431.6 vs floor 205/432) + in-game. Commit `13b1c54`. 163 tests.
- This re-surfaced the **Session-17 deferred double-count** (`org=300` + `offset=298` near-cancel) as a genuine hack, and the user's question — *did we ever pin how real maps relate walkmesh↔painted floor?* The honest answer: we nailed the projection (`to_canvas`, exact) but never empirically measured the dev convention / character-planting offset (298 was a 40°-only calibration). Next: a **solid measurement plan** (below) to replace the guesswork — being careful, since past eyeball-fits (sx/sy) misled.

Tagged `KNOWN_GOOD-s18-from-scratch`.

### 2026-06-05 — Session 18 (cont) — Character offset MEASURED = 0 (engine probe); the 298/300 was an artifact

**Cracked the long-standing "character-vs-floor offset" with hard data instead of eyeball-fits (the user explicitly wanted no more guesswork).** Result: **there is NO real character offset** — the old `CHARACTER_GROUND_OFFSET_Z=298` was purely the partner of the legacy `org=(0,0,300)` builder artifact (the Session-17 double-count).

**Method (engine probe, the rigorous route):**
- Source dive corrected a stale assumption: `PSX.ConvertCameraPsx2Unity` is DEAD (commented out). The field char MODEL is positioned by its **vertex shader's GTE** (`FieldMapActor.txt`: `_MatrixRT`/`_ViewDistance`/perspective-divide/`_OffsetX/Y`/`_MulX/Y`, writes `oPos` directly) — the SAME GTE the floor/walkmesh use (`FieldMap_Abr_None.txt` is just `mvp*v0` on C#-placed canvas verts). So the model is NOT positioned by the Unity camera's `WorldToScreenPoint` — my first probe column (VP) was off-screen garbage precisely because of that. Confirmed the real mechanism before trusting any number.
- Added a temporary `FF9PROBE` to `FieldMapActorController.HonoLateUpdate` (player on field 4003: log world `P`, GTE `projectedPos`, `WorldToScreenPoint`/`Viewport`, screen/cam mapping), rebuilt the engine (VS18 BuildTools `/p:SolutionDir=...\Memoria\`, auto-deploys; backed up the S12 DLL first), user walked a **`to_canvas`-painted 200u grid** (`tools/build_offset_calib.py`, world-frame walkmesh org=0, no offset, cyan cross = world origin) at **48° then 30°**. Removed the probe + rebuilt clean (verified `FF9PROBE` gone from the deployed DLL).
- **Data:** feet land on the painted grid at the player's true world `P` at every spot, both pitches — e.g. 30° read world `(-900,0)` vs probe `P=(-900,0,0)`; 48° read `(+920,+200)` vs `P=(926,230)`. Offset = **0 within ±~½ cell**, i.e. ≤~30u vs the 298 we'd baked in (10× smaller). Pitch-independent.

**Why this matches the shaders:** char + floor share the GTE projection → char renders at `to_canvas(worldP)` = where the floor for `P` is painted → walkmesh-in-true-world-coords == painted floor, no fudge. The HONEST model is `[walkmesh] frame="world"` (org=0, no offset), exact at any angle — what OFFCAL used.

**Fix (forward, low-risk — does NOT touch verified geometry):** `ff9mapkit new` now scaffolds `[walkmesh] frame="world"` (org=0, no character offset). The legacy quad/auto path + `CHARACTER_GROUND_OFFSET_Z=298` are KEPT for back-compat: the real hut `.bgi` ships `org=(0,0,300)` (the byte-golden `test_build_flat_delegates_byte_identical_to_legacy` proves it) and its art is aligned to that +300, so existing rooms/examples stay self-consistent. Only NEW scaffolds use the honest model. Corrected the `cam.CHARACTER_GROUND_OFFSET_Z` docstring to the measured truth. Commit `9972a47`; 163 tests.

**Engine/game state:** clean S12 engine redeployed (probe removed; fade-cache + booster intact). Field 4003 = OFFCAL 30° grid (revert `tools/scroll_out/revert_deploy.py`); Alexandria fast-warp active. No KNOWN_GOOD tag (measurement + offline kit change; the in-game proof was the OFFCAL grid, already validated).

**Deferred (optional, needs care + a playtest):** fully ripping the org=300/offset=298 double-count from the LEGACY path (so all rooms are convention-B `org=0`) would require re-aligning the hut example's art — "moves verified geometry," so left alone. New work should just use `frame="world"`.

### 2026-06-05 — Session 18 (cont) — Legacy double-count RIPPED + PIL dropped from the guide (cleanups, in-game smoke-tested)

Acting on the measured offset=0 + user's "no need for legacy stuff":
- **Ripped the org=300/character_offset double-count.** `build.resolve_walkmesh` now builds EVERY authored walkmesh in true world coords (org=0, no shift) — the honest model. Removed `_shift_toward_camera` + the character_offset usage (the `character_offset`/`frame` keys are accepted-but-ignored for back-compat). `frame="world"` is the default behavior now. `bgi.build_flat`/`bgi.quad` (org=300) KEPT only as codec functions — the byte-golden + importer/exporter reproduce real fields' org. Scaffold, Blender from-scratch export, and the scroll-demo example emit `frame="world"` instead of `character_offset`.
- **Dropped PIL from the guide.** `guide.render_paint_guide`/`render_paint_template` are now pure-stdlib (reuse `placeholder._png_rgba` + a new `placeholder.draw_line` + `_fill_quad`; `_height_segments` replaces the PIL `_draw_height_guides`). Coordinate labels dropped (the CLI prints them). Kit core (guide/build/pack/placeholder) is PIL-free; only `extract.py`'s editable-art compositing lazy-imports PIL (fork-only).
- Tests updated to the honest model (walkmesh verbatim, no shift); 163 pass; vendor synced. Offline: hut_int rebuilds to ~2u of its old position.

**Human verified (in-game):** deployed a PLAIN-`quad` room (no frame, no character_offset — the exact default path the rip changed) to field 4003; character spawns on the cyan cross + stays centered on the grid cells while walking ("looks good"). So the org=0 default is correct and `character_offset` is confirmed unneeded — no regression. Tagged `KNOWN_GOOD-s18-honest-walkmesh`. Commit `4311b0d`.

**Engine/game state:** clean S12 engine (probe removed). Field 4003 = the plain-quad OFFCAL grid (test field; revert `tools/scroll_out/revert_deploy.py`). Alexandria fast-warp active.

**Agenda remaining (user asked):** (a) multi-camera switch-zones — the last unbuilt camera-movement feature (scene format already parses N cameras; needs bgx.build N-cams + per-layer camera + a SETCAM switch-zone injector); (b) productize/ship — replace the debug warp with a story-positioned entrance, package, the open Memoria PR #1433; (c) more content (rooms/story/encounters). Camera/geometry/art/import/export pipeline is COMPLETE + measured-correct.

### 2026-06-05 — Session 18 (cont) — Multi-camera: dev convention captured from real fields (Phase 0)

User: build multi-camera switch-zones, learning the convention from live-game imports (not guessing). Researched the mechanism + the dev pattern from real fields before authoring.

**Mechanism (engine source):** the active camera is purely SCRIPT-driven — opcode `SETCAM 0x7E "SetFieldCamera"(camID)` (1 arg) → `FieldMap.SetCurrentCameraIndex` (`DoEventCode.cs:1936`, `FieldMap.cs:383`), which swaps the active BG GameObject + the per-camera `projectedWalkMesh` + offsets. There is NO automatic per-triangle/region camera switch. `camIdx` starts at 0. (The :1940 special-cases are dev bug-fixes for camera "flapping" on maps 153/1214/1806 — proof that sloppy overlapping switch zones flap.)

**Dev convention (real field — Gargan Roo/Passage, id 951 / test2_261):** camera switching is the GATEWAY-region mechanism repurposed:
- `RegionN_Init`: `SetRegion((x,z)×4)` — a quad zone (identical to gateway regions).
- `RegionN_Range` (the player-in-zone trigger, func tag 2): `ifnot IsMovementEnabled return` then `if (flag != target) { ...; SetFieldCamera(target); set flag = target }`.
- A PAIR of zones at the boundary (one sets cam 1 crossing in, one sets cam 0 crossing back), gated by a STATE FLAG (`VAR_GlobUInt8_24`) so each fires only on the transition → no flapping. That flag is the anti-flap discipline the engine bug-fix patched for fields that lacked it.
- `Main_Reinit` (entry-0 tag-10): `if (flag) SetFieldCamera(1)` — restores the correct camera on re-entry (e.g. after battle).

**Scene side (already supported):** `.bgx`/`bgs` already model N cameras + per-overlay `CameraId` (which camera's BG each layer belongs to). `bgx.Overlay.camera_id` + `BgxScene.cameras()` (list) exist; `bgs.parse_cameras` reads N. GAPS: `bgx.build` takes ONE camera (needs N); `bgs.parse_overlays` doesn't yet capture `camNdx` (study-only).

**Implementation plan:**
- P1 (scene): `bgx.build` accept `cameras: list[Cam]` (write N CAMERA blocks); layer schema `[[layers]] camera = N` → `overlay.camera_id`; `build.resolve_camera` returns N for a `[[camera]]` array (single-camera path unchanged).
- P2 (script): `content/camera.py` switch-zone injector — clone the gateway region template, but the Range body = `if flag!=target { SetFieldCamera(target); flag=target }`; + inject the flag-restore into Main_Reinit (the tag-10 reinit we already add for encounters). field.toml `[[camera_zone]] to_camera=N zone=[...]`.
- P3 (in-game): author a 2-camera test field (borrow two real GRGR cameras + a switch-zone pair), deploy, verify the camera switches as the player crosses + restores on re-entry.

Captured in project memory `project-ff9-camera-math` (multi-camera section).

### 2026-06-05 — Session 18 (cont) — Multi-camera P1+P2 BUILT (byte-exact from real game); in-game test deployed

**Built the whole multi-camera feature offline, grounded byte-for-byte in real FF9 bytecode, and deployed an in-game test (awaiting playtest, Hard-Constraint §2).** 171 tests pass.

**Import-driven grounding (the user's ask — "solve authorship the way the devs did"):** extracted the REAL camera-switch region from `evt_gargan_gr_lef_0` (Gargan Roo, field 951's sibling) straight out of `p0data7.bin` (events live at `assets/resources/commonasset/eventengine/eventbinary/field/<lang>/`, 818 us fields) and disassembled it. Decoded the field-script **expression sub-language** (opcode `0x05` + a `0x7F`-terminated RPN stack): push var `<class><idx>` (`0xD5`=GlobUInt8, `0xC5`=GlobBool), push const `0x7D <i16>`, ops `0x0E`=NOT / `0x20`=`==` / `0x2C`=assign; conditional jumps `0x02`=jump-if-false (the `if` skip, operand=body byte-len) / `0x03`=jump-if-true (the `ifnot`). The dev switch convention: a forward+reverse **region pair** gated by `VAR_GlobUInt8_24`, each doing `SetFieldCamera` + flag-set + per-camera `SetControlDirection` + `InitRegion(other)` + `TerminateEntry(255)`; `Main_Reinit` restores on re-entry. (Engine: `SETCAM 0x7E`→`SetCurrentCameraIndex`; the `0x71 BGCACTIVE`/scroll path is separate.)

**Built (committed; the kit's first AUTHORED-LOGIC injector):**
- `content/region.py` — the general flag-gated **conditional region** primitive: `set_var`/`cond_truthy`/`cond_not`/`cond_eq`/`if_block`/`MOVEMENT_GATE` + `set_region`/`build_region_entry`/`inject_region`. Reproduces the real-field bytes EXACTLY (tested), incl. the full Gargan forward-zone Range body byte-for-byte (43/43). This same primitive generalizes to chests/story-flags (`if (!done){ give; done=1 }`).
- `opcodes.set_field_camera` (0x7E), `opcodes.terminate_entry` (0x1C).
- `content/camera.inject_camera_switch` — the dev 2-camera pattern (forward/reverse zones + per-camera control direction derived from yaw + a load-time init entry that resets the flag so state is consistent on every load; no reinit needed for a no-battle room).
- **build wiring:** `resolve_camera`→`resolve_cameras` (single `[camera]` stays BYTE-IDENTICAL; `[[camera]]` array → N cams → N CAMERA blocks via `bgx.build(list)`); per-layer `camera` → `overlay.camera_id`; `[[camera_zone]]` injects the switch (control dir auto-derived per camera); `validate()` + `camera_cfgs()` for dict-vs-list. `docs/FORMAT.md` schema added.

**In-game test DEPLOYED (field 4003 = MULTICAM, reachable via the New-Game→Alexandria→hut-door warp):** `tools/build_multicam_test.py` — one flat floor, camera 0 (cyan, head-on) ↔ camera 1 (orange, yaw 35°), each with its own `to_canvas` calibration grid + a green switch-zone outline. Walk into green → cut to the other camera (colour + re-projected grid = unmistakable proof); walking straight after = per-camera control-direction proof; cross back = reverse + anti-flap. Revert: `py tools/scroll_out/revert_deploy.py`.

**Commits:** `multicam P2: conditional-region + flag primitives + camera-switch injector`; `multicam P2: field.toml wiring`; `multicam P2: FORMAT.md schema + in-game test-field builder`.

**Human verified (real gameplay): "good" ✅** — the 2-camera switch WORKS in-game: loads on the cyan head-on camera; crossing the green zone CUTS to the orange yaw-35 camera (colour + re-projected grid); movement stays screen-correct after the cut (per-camera control direction); and it cuts back. Multi-camera switch zones proven end-to-end. **Tagged `KNOWN_GOOD-s18-multicam`.** Findings folded into project memory `project-ff9-camera-math` (multi-camera section) — incl. the decoded field-script EXPRESSION sub-language (opcode 0x05 RPN: var classes, const, NOT/==/assign, if/ifnot jumps), reusable for chests/story-flags via the same `content/region.py` conditional-region primitive.

**Open / next:** field 4003 = MULTICAM test grid (revert `py tools/scroll_out/revert_deploy.py`). v2 (open) = 3+ cameras / Main_Reinit camera-restore for battle fields. The general `content/region.py` conditional region is now available to author **chests / story flags / one-shot events** (`if (!done){ give; done=1 }`) — the natural next script-capability lever.

### 2026-06-05 — Session 18 (cont) — EVENTS: cashed in the conditional-region primitive (chests/flags/triggers)

**Cashed in the multicam conditional-region primitive as the broad script-capability expansion the user wanted: one-shot field EVENTS — walk-in triggers that give items/gil, show messages, set story flags, optionally once.** Built + tested offline (175 tests); in-game test deployed (awaiting playtest, §2).

**Grounded (import-driven):** decoded a REAL treasure handler from `p0data7.bin` — `AddItem(id,count)` (0x48) + `SetTextVariable(0,id)` (0x66) + a "received X" `WindowSync`. Added `opcodes.add_item` (0x48 `[id:2,count:1]`) + `add_gil` (0xCE `[gil:3]`), both round-trip-verified.

**Built:**
- `content/event.py` — walk-in event triggers on `content/region.py`: compose a body from `message`/`give_item`/`give_gil`/`set_flag`, fire it from a region, optionally ONCE (gated by a persistent GlobBool — `if (!flag){ body; flag=1 }`, the same shape as the camera switch). `inject_events` batches any N events through ONE arming code-entry, so they don't each eat a Main_Init `Wait` filler (the blank only has 2).
- **build wiring:** `[[event]]` schema (`zone`/`message`/`give_item`/`gil`/`set_flag`/`once`/`flag`); `collect_dialogue`→`collect_text` (NPC dialogue + event messages share the `.mes`, NPCs first → golden hut/multicam builds byte-identical); validate + off-walkmesh placement check. `docs/FORMAT.md` documents it. "once" flags default to GlobBool base 200 (author overrides for a shipped mod).

**In-game test DEPLOYED** (`tools/build_event_test.py` → field 4003 = EVENTROOM, via the Alexandria→hut-door warp): a GOLD zone = ONCE (`AddItem(232,1)` + 1000 gil + message; re-enter → nothing) and a CYAN zone = REPEATABLE (ambient line every time), on a grid floor with the zones + spawn outlined. Revert `py tools/scroll_out/revert_deploy.py`.

**Commits:** `events: cash in the conditional-region primitive ([[event]] one-shot triggers)`; test builder.

**AWAITING PLAYTEST.** Look for: (1) walk into GOLD → message + (menu) a new item + gil up 1000; (2) re-enter GOLD → NOTHING (proves once); (3) walk into CYAN → the line fires EVERY time (proves repeatable + no-flag). Report each. Then the kit has the full content stack: rooms → cameras (incl. multi) → NPCs/dialogue → gateways → encounters → **events (chests/flags/triggers)**.

**Human verified (real gameplay): "looks good" ✅** — events work in-game: walk into the GOLD zone → message + (menu) a new item + 1000 gil; re-enter → nothing (the `once` GlobBool holds); CYAN repeatable line fires on entry. **Tagged `KNOWN_GOOD-s18-events`.** User noted (precisely, accepted): a `once=false` event is LEVEL-triggered — closing its window while still inside the zone re-pops it immediately (FF9's region tag-2 fires every frame you tread the quad; `TreadQuad` is a pure position test, no edge detection — confirmed in `EventCollision.cs`/`TreadQuad.cs`). `once=true` (chests/one-time lines) is unaffected. Documented in FORMAT.md + event.py; a true "once-per-visit" (re-arm on leave) is a noted future enhancement (needs a leave-detecting zone, like the camera-switch toggle).

**The kit's content stack is now complete + in-game-proven:** rooms → cameras (single / scrolling / **multi-camera**) → walkmesh (incl. import/reshape) → NPCs/dialogue → gateways → encounters → **events (chests / gil / story flags / triggers)**. Enough to author a real, populated FF9 area end-to-end.

### 2026-06-05 — Session 18 (cont) — STORY LOGIC / branching (flag-gated NPCs / gateways / events) + activation-overflow fix

**Built branching — content that gains state from story flags — and answered the user's architecture question first** (script limits: we MINT fields by name = unbounded; the `.eb` is bounded only by u16 offsets [~64KB/255 entries] = never hit; the real "stock memory" is the **2048-byte save-backed `gEventGlobal`** flag array, shared with the base game → pick a free range; Memoria ADDS save-persisted unbounded `gScriptVector`/`gScriptDictionary` stores = the "extend past stock" path). Captured for the user.

**Built (offline, 180 tests; grounded in the conditional-region primitive):**
- `region.flag_gate(idx, require_set)` — an `ifnot(flag) return` prologue (same expr/jump primitive).
- `[[npc]] requires_flag` / `requires_flag_clear` — prepend the gate to the Init → a gated-out NPC returns before CreateObject (no model, absent). The standard FF9 show/hide-by-story pattern.
- `[[gateway]] requires_flag` — prepend to the Range (last func → safe insert) → a locked door that only exits when the flag matches.
- `[[event]] requires_flag` + the existing `set_flag` — a switch sets a flag; NPCs/doors/events read it.
- **Activation-overflow fix `edit.activate`** (the blocker): the blank has only 2 `Wait` fillers but a story field (NPC+gateway+event) needs 3+ activations. `activate()` overwrites a Wait when free, else INSERTS the `Init*` call into Main_Init (safe — entry-0's other func is an empty placeholder, the `enable_camera_services` mechanism). ALL injectors route through it; **within-budget builds stay byte-identical** (golden hut / multicam / events unchanged), over-budget builds now work. Verified: a NPC+gateway+event field round-trips (2 InitObject + 1 InitRegion over Waits + 1 InitCode inserted).
- FORMAT.md: `requires_flag` rows + a "Story flags & branching" section.

**In-game test DEPLOYED** (`tools/build_story_test.py` → field 4003 = STORYROOM): a GOLD switch zone sets flag 200; while clear, a GUARD (magenta marker) is ABSENT and the back DOOR (cyan) is LOCKED; flip the switch → guard appears + door unlocks (→ Alexandria). Revert `py tools/scroll_out/revert_deploy.py`.

**Commits:** `story logic: flag-gated NPCs / gateways / events + activation-overflow fix`; test builder.

**AWAITING PLAYTEST.** (1) Guard absent + door does nothing on entry; (2) walk into GOLD → "*CLICK*"; (3) guard now present + talks; (4) walk into the door → now exits to Alexandria. Report each. With this, the kit authors real *stateful* areas (switches, locked doors, story-gated NPCs).

**Human verified (real gameplay): story logic COMPLETE ✅.** First test: switch + door worked, but the flag-gated NPC didn't appear in-visit ("no Vivi") — diagnosed precisely: a gateway's gate is in its `_Range` (re-checked every step → live), but the NPC's gate is in its Init (runs once at spawn → only updates on re-entry). User chose **live reveal**; fix = the `set_flag` event also `InitObject`s NPCs gated on that flag (engine source confirms re-InitObject `DisposeObj`s the old actor + re-runs Init with the flag set — clean replace, no ghost). Re-test: **"good"** — switch fires → message → guard appears live + talks → door unlocks. **Tagged `KNOWN_GOOD-s18-story-logic`.**

**The kit now authors fully STATEFUL areas:** an event sets a GlobBool story flag; NPCs (`requires_flag`), gateways (locked doors), and other events react — **live in-room AND across visits**. Combined with the complete content stack (rooms → cameras incl. multi → walkmesh import/reshape → NPCs/dialogue → gateways → encounters → events → **branching**), `ff9mapkit` covers the full breadth of FF9 field scenario authoring. Activation-overflow fix (`edit.activate`: Wait-or-insert) means content-rich fields are no longer capped by the blank's 2 Wait slots.

### 2026-06-05 — Session 18 (cont) — Multi-camera v2: N cameras (area model) + after-battle restore

**Generalized multi-camera from the v1 2-camera pair to ANY number of cameras, + added the after-battle camera restore the user asked for.** Offline, 182 tests; in-game test deployed (awaiting playtest).

**Area model (replaces the v1 forward/reverse toggle):** the state flag (GlobUInt8_24) holds the CURRENT camera index; each `[[camera_zone]]` owns the floor area where its camera is active and, when entered with flag != that camera, switches to it + stores it + re-tunes movement (SetControlDirection for that camera's yaw). Flag-guarded → no re-fire while standing; non-overlapping zones can't flap. Scales to N (FF9 ships ≤4). An init code-entry resets flag=0 + arms all zones on load. `content.camera.inject_camera_zones` + `region.if_not_block` (cond + jump-if-true).

**After-battle restore:** `add_camera_restore` puts a per-camera `if (flag==K) { SetFieldCamera(K); SetControlDirection }` chain in Main_Reinit (tag 10). On battle return Main_Init doesn't run (flag not reset), so this re-applies the camera + movement. Wired when a field has camera_zones + encounters.

**Build/validation:** dropped the v1 'single 2-camera pair' rule; `[[camera_zone]]` now just needs valid `to_camera` + a 4/5-pt zone. The TWOCAM build still passes via the area model. FORMAT.md updated (area model + non-overlap caveat + restore note).

**In-game test DEPLOYED** (`tools/build_tricam_test.py` → field 4003 = TRICAM): floor split into 3 X-bands — LEFT=cam2 (green, yaw −25), MID=cam0 (cyan, yaw 0, spawn), RIGHT=cam1 (orange, yaw +25) — + encounters (freq 160) to test the restore. Revert `py tools/scroll_out/revert_deploy.py`.

**Commit:** `multicam v2: N cameras (area model) + after-battle camera restore` (+ test builder).

**AWAITING PLAYTEST.** (1) Walk left↔mid↔right → the view cuts among 3 cameras (tint + perspective), WASD stays correct; (2) trigger a battle on the orange RIGHT band, win → camera restored to orange (not reset to cyan). Report each.

**Human verified (real gameplay): multicam v2 COMPLETE ✅ (all 4).** 3-camera switching across the bands (tint + perspective cut), WASD screen-correct on each, AND the after-battle restore (won a battle on the orange camera → returned still on orange, not reset). **Tagged `KNOWN_GOOD-s18-multicam-v2`.** N-camera area model + after-battle restore both proven in-game. This was the last camera-movement feature on the roadmap.

### 2026-06-05 — Session 18 (cont) — Two-file authoring (Godot-style): scene.toml (spatial) + field.toml (logic)

**User's roadmap call: don't cram scripting into Blender. Split *where things are* (Blender) from *what they do* (text), like Godot.** Built Phase 1 — the scene/logic decoupling — CLI-first (proven) then Blender.

**The problem (grounded):** Blender's Export wrote a *fresh* `field.toml`, so hand-authored dialogue/events got clobbered on every re-export. The fix is clean ownership, not a scripting UI in Blender.

**Architecture:** `<x>.scene.toml` (Blender-owned, overwritten: camera/walkmesh/layers/spawn/camera_zone + each entity's name+pos/zone) overlays `<x>.field.toml` (yours: `[field]` + per-entity logic by name). `build` merges by entity name (scene = spatial keys, field = logic). Single-file field.tomls (no scene sibling) build unchanged — purely additive.

**CLI (committed, tested):** `FieldProject.load` auto-discovers a sibling `<x>.scene.toml` (or explicit `[scene] file`) and `_merge_scene`/`_merge_entities` overlays it. **Golden equivalence test: the split build == the single-file build byte-for-byte** (.eb all langs, .bgx, .bgi, .mes) + merge unit tests. FORMAT.md "Two files" section.

**Blender (add-on v0.7.0, committed; needs in-Blender verify per §2):** Export Field now writes `<name>.scene.toml` (spatial) EVERY time + scaffolds `<name>.field.toml` (logic stub) ONLY if absent — re-export never clobbers your script. All 3 export paths route through `_write_split_files`; bpy-free `bridge.scene_toml`/`field_logic_stub`/`_entity_scene_blocks`. Dry-run test: split export → real builder → talkable NPC (pos from scene, dialogue from logic); scene.toml carries no logic values. 187 tests; README updated.

**Roadmap (agreed):** P1 decouple surfaces ✅ (this). P2 = logic ergonomics in TOML (story/flag linter, validation, scaffolds). P3 (later) = a sequential format for cutscenes (the one thing declarative TOML is bad at: ordered move/wait/say/pan/branch).

**AWAITING (Blender, not in-game):** install `dist/ff9mapkit_blender-0.7.0.zip`, Export a field → confirm `<name>.scene.toml` + `<name>.field.toml` both appear; add a line of dialogue to the field.toml; re-export → field.toml preserved, scene.toml refreshed; `ff9mapkit build <name>.field.toml` → works.

**Human verified (real gameplay): the WHOLE two-file pipeline works in the user's hands ✅.** User authored field `jawnland` entirely through the new workflow — Blender (pose camera, design walkmesh, place NPC marker) → Export = `jawnland.scene.toml` (spatial) + `jawnland.field.toml` (logic stub) → hand-edited Vivi's dialogue in the field.toml → the **Tkinter GUI** (`tools/ff9_build_gui.pyw`) built + deployed it to test field 4003 → in-game: **walkmesh lines up with the Blender design, Vivi is in his placed spot saying the authored dialogue.** Re-export confirmed it doesn't clobber the field.toml edits. Black background only because no painted layer was added (expected — art is the next optional step). **Tagged `KNOWN_GOOD-s18-two-file-authoring`.** The scene/logic split + the GUI front-end are both in-game-proven, self-service. Roadmap P1 done in practice.

### 2026-06-05 — Session 18 (cont) — Roadmap P2: logic linter + tighter validation (offline)

**P2 of the authoring roadmap — "logic ergonomics in text," so the script side stays safe as rooms grow.** All offline (192 tests).
- `build.lint_logic(project)` — story/flag sanity on the merged project: a `requires_flag` (appears/fires when SET) that **no event ever sets** → dead content; an explicit flag index that **collides with an auto-allocated `once` flag** (base 200+); **duplicate entity names** (ambiguous scene↔field merge). Folded into `build` warnings.
- `validate()` tightened: an `[[npc]]` with no position / a `[[gateway]]` with no `to` now **error cleanly** instead of crashing the build (matters for the two-file split, where pos comes from the scene).
- Surfaced standalone: **`ff9mapkit lint <field.toml>`** (exits 1 on any issue) + a **"Check logic"** button in the GUI (`tools/ff9_build_gui.pyw`) that lints without building.
- FORMAT.md "Story flags" documents it. `jawnland` lints clean.

**Roadmap status:** P1 (scene/logic split, CLI+Blender) ✅ verified in-game (jawnland). P2 (logic linter) ✅ offline. P3 (sequential cutscene format) = later, when ordered move/wait/say/pan/branch is needed.

### 2026-06-05 — Session 18 (cont) — Roadmap P3: cutscenes v1 (ordered, control-locked sequencer)

**P3 — the last authoring gap: cutscenes (ordered actions, which declarative content can't express).** v1 shipped offline (196 tests); in-game test deployed.
- `content/cutscene.py`: a `[cutscene]` compiles to a code entry whose function runs an ORDERED sequence with control disabled (`DisableMove`…`EnableMove`), optionally once (flag-gated, default GlobBool 230), armed on field entry via `InitCode`. v1 steps = `say` (WindowSync), `wait` (Wait), `set_flag` — the controller-level actions that need no per-actor context.
- build: `[cutscene]` schema + validate (steps list, one action each) + `collect_text` gathers `say` lines into the `.mes` + `lint_logic` accounts for cutscene `set_flag`/once-flag. `opcodes.DISABLE_MOVE` (0x2D). FORMAT.md `[cutscene]` section.
- **v2 (deferred):** actor movement / animation / camera pans — `Walk` (0x23), `RunAnimation` (0x40), `MoveCamera` (0x6F) target a specific object's context, so they need the sequence to run in that actor's entry. The vocabulary is mapped; the sequencer + trigger + control-lock (the hard architecture) is done.

**In-game test DEPLOYED** (`tools/cutscene_out/cs.field.toml` → field 4003 = CUTSCENE): on entry, control locks + a text sequence plays + a flag sets + control returns; a back gateway (→ hut interior) lets you leave + re-enter to confirm it plays ONCE. Revert `py tools/scroll_out/revert_deploy.py`.

**Roadmap COMPLETE:** P1 scene/logic split ✅ (in-game), P2 logic linter ✅, P3 cutscenes ✅ (v1). The authoring toolkit now spans spatial (Blender) + logic (text, linted) + sequences (cutscenes).

**AWAITING PLAYTEST.** (1) On entry: control LOCKED, text boxes play in order, then control returns. (2) Walk to the BACK → exit → re-enter → cutscene does NOT replay (control immediate). Watch for: doesn't play / not locked (can move during text) / out of order / replays on re-entry.

### 2026-06-05 — Session 18 (cont) — IMPORTANT FIX: story/once flags must be SAVE-PERSISTENT (Global), not Map

**In-game the cutscene replayed on re-entry → found a fundamental flag bug affecting ALL persistent content (chest "once", story flags, cutscene "once").** We'd only ever tested "once" WITHIN a visit; the first reload test exposed it.

**Root cause (engine source):** a var token byte = `0xC0 | (VariableType<<2) | VariableSource`. The SOURCE decides persistence — **Global (src 0)** read/writes the save-backed `gEventGlobal` (persists across field reloads + saves); **Map (src 1)** is a PER-FIELD array WIPED on every field load (`EvaluateValueExpression`: Global→`gEventGlobal`, Map→`GetMapVar()`). The kit used `0xC5` = Map+Bit → every flag reset on reload. (HW naming is inverted: HW "GlobBool" = engine Map = transient; HW "GenBool" = engine Global = persistent.)

**Fix:** `region.GLOB_BOOL` 0xC5 → **0xC4** (Global+Bit, persistent); kept `MAP_BOOL`=0xC5 for the dev-repro. Flag bases moved high in gEventGlobal, clear of base-game flags (which sit low): `EVENT_FLAG_BASE` 200→**8000**, cutscene default 230→**8100**. `region._push_var` now emits the engine long-index encoding (`class|0x20` + 2-byte LE) for indices >0xFF. **Camera flag stays Map+Byte (0xD5)** — transient by design (reset per load + restored via tag-10 within a load; verified). 196 tests; FORMAT.md Story-flags rewritten. CUTSCENE (4003) redeployed: once-flag now `GlobalBool[8100]`.

**Implication:** this also fixes event `once` chests (they'd have re-looted on revisit) + all `requires_flag`/`set_flag` story state to actually persist. Re-verify the cutscene once-on-reentry, then the toolkit's persistence is solid.

**AWAITING RE-PLAYTEST (CUTSCENE 4003):** enter → cutscene plays (control locked) → leave via the back gateway → re-enter → it should NOT replay (control immediate). (May need a fresh entry; the old Map flag is gone, the new Global flag starts clear.)

**Human verified (real gameplay): persistent-flag fix WORKS ✅ — "that fixed it."** The cutscene now plays once and does NOT replay on re-entry (the once-flag survives the field reload now that it's in the save-backed Global scope). This also means event `once` chests stay looted + `requires_flag`/`set_flag` story state persists across visits (the latent bug we'd never caught). **Tagged `KNOWN_GOOD-s18-cutscenes` (cutscenes v1 + persistent flags, in-game verified).**

**Orientation lesson (user correction):** I mislabeled the exit as "back" — for these (pitch-down, no-yaw) cameras, **more-negative z = FRONT (toward the camera / bottom of screen)**; less-negative z = back (top). The gateway at z≈−880..−1000 rendered at the front. Use the paint guide's BL/BR/FR/FL corner labels rather than guessing front/back from raw z.

**Roadmap COMPLETE + in-game-verified:** P1 scene/logic split, P2 logic linter, P3 cutscenes v1 — plus the persistent-flag correctness fix. Full authoring toolkit: spatial (Blender) + logic (text, linted, save-persistent flags) + sequences (cutscenes), with a GUI front-end.

### 2026-06-05 — Session 18 (cont) — v2 cutscenes: ACTOR movement (walk/turn) — built + deployed (AWAITING PLAYTEST)

**Built the v2 cutscene layer — a named NPC walks/turns/animates during a control-locked scene** (the iconic "a character walks in and talks"). Deployed an in-game test to field 4003; **not yet playtested** (Hard-Constraint §2).

**The architecture decision (grounded in engine source + a real-cutscene decode).** Read every relevant `DoEventCode` handler + had an agent decode real walk cutscenes (Gargan/Kuja, Treno/Pub, Conde Petie). Key facts: base FF9 has **no targeted walk** — `Walk`(0x23)/`RunAnimation`(0x40)/`Turn` act on the **executing object** (`gExec`); the targeted "Ex" ops (`MOVE_EX`/`AANIM_EX`) are **custom Memoria codes** (enum > 0x100, ungrounded, not in the kit tables) — avoided. The canonical game pattern is a director (Main_Loop) driving an NPC's walk function via `RunScript*` + `RunScriptSync`(0x14, targets by **UID**; `Obj` ctor: `uid==0 → sid`=slot). Plain `Walk` **self-blocks** its own function until arrival (`MoveToward_mixed → stay()`), so steps stay ordered. `MoveInstantXZY`(0xA1) **negates Z** (`destZ = -getv2()`; CreateObject/Walk don't) — a real gotcha. Player UID = 250.

**Chosen design (simplest, lowest-risk): bake the choreography into the actor NPC's Init.** A `[cutscene] actor = "<npc>"` compiles its steps and splices them into that NPC's Init, just before its RETURN, as `if (!once) { DisableMove; <steps>; EnableMove; once=1 }`. Everything runs in the NPC's own context (`gExec` == the NPC) so `Walk`/`RunAnimation`/`Turn` act on it with **base opcodes only** — no director entry, no `RunScript`/UID targeting, no script-level mechanics I can't verify offline. `say`/`wait`/`set_flag` interleave (they're global). Replay-safe: CreateObject stays at the NPC's rest `pos`; the gate skips the choreography on revisit. Narration cutscenes (no `actor`) are **unchanged** (the proven v1 standalone director).

**Grounded BYTE-FOR-BYTE in shipping data.** Extracted a real field (`evt_mage_bv_gvy_1`, Bran Bal) from p0data7 and disassembled it with the kit: `InitWalk`=`25`, `SetWalkSpeed(15)`=`26 00 0f`, `WaitAnimation`=`41`, `TurnTowardObject(10,16)`=`51 00 0a 10`, `WaitTurn`=`50` all appear verbatim, and **`our walk() encoder == a real Walk's bytes`** (entry6 tag-15 is a real walk function: `InitWalk → Walk → … TimedTurn` — exactly our choreography shape). The engine ships these bytes, so it accepts them.

**Built (committed `5970564` kit, `fb05d92` test builder):**
- `eb/opcodes.py`: `init_walk`/`walk`/`set_walk_speed`/`move_instant_xzy`(Z-negated)/`run_animation`/`wait_animation`/`turn_instant`/`timed_turn`/`turn_toward_object`/`wait_turn`/`disable_move`/`enable_move`.
- `content/cutscene.py`: actor step builders (`actor_walk`/`actor_teleport`/`actor_animation`/`actor_turn`/`actor_face`), `compile_steps` (all step types), `build_choreography` (the gated block).
- `content/npc.py`: `inject_npc(..., intro=)` splices the choreography into the Init (rebuilds the func table; no-intro = byte-identical).
- `build.py`: `[cutscene] actor` wiring (compile choreography → that NPC's `intro`; skip the v1 director); validate actor steps + that the actor names a real NPC.
- `docs/FORMAT.md`: actor-cutscene section + step table + the rest-position/replay note.
- **205 tests pass** (9 new; golden NPC/cutscene/event byte-identity preserved). Disasm of the built test field confirms the spliced choreography: `if(!8100) JMP_FALSE(36) { DisableMove; InitWalk; Walk(0,-450); TurnTowardObject(250); WaitTurn; WindowSync(501); InitWalk; Walk(0,-900); EnableMove; flag=1 }` then the Init's RETURN.

**In-game test DEPLOYED** (`tools/build_cutscene_actor_test.py` → field 4003 = CUTSCENE2, via the hut interior door): Vivi (magenta cross) walks forward to the green cross, faces the player, says "...hi.", walks back to his spot — control locked. First test deliberately uses **walk + face + say only** (no teleport/animation — the two least-grounded steps) to isolate the core. Revert: `py tools/scroll_out/revert_deploy.py`.

**PLAYTEST 1 — FAILED (entry-circle softlock), FIXED + redeployed.** On entry Vivi walked in a CIRCLE (user: "a player-character bug too that plays sometimes when exiting gateways — runs in a circle when the map loads then stops"), never reached the target exactly, the dialogue never fired, and control stayed LOCKED (softlock). User asked: "is there a warm-up period before assigning commands?" — yes. **Root cause** (confirmed in engine + the blank Main_Init disasm): the choreography fired from the NPC Init *during the field entry transition* — Main_Init does `EnableMove` then `FadeFilter(7,16,...)` (a 16-frame fade) + the smooth-frame-updater settles actor positions for the first frames, so a `Walk` issued then circles and the **synchronous** Walk never converges → hang. Real entry cutscenes avoid this with a Main_Loop `Wait(...)` before driving actors (test2_690 `Wait(100)`, test2_425 `Wait(3)`). **Fix (commit `df00665`):** `build_choreography` now emits `DisableMove; Wait(warmup); <steps>; EnableMove` — the actor stands still (player locked, can't wander) until the field settles, then walks cleanly. Default **30 frames** (~1s, > the 16-frame fade); tunable via `[cutscene] warmup = N`. 206 tests; redeployed to 4003.

**PLAYTEST 2 — FAILED (walk arcs/orbits), FIXED + redeployed.** Vivi STILL circled and couldn't reach the cross. User's decisive diagnosis: "Vivi spawns looking towards the camera… there may be a turn rate/radius if he needs to move to the green cross directly behind him." **Confirmed in `MoveToward_mixed`:** Walk moves the actor at full `speed` each frame but rotates `movingAngle` toward the target by only ~`omega`/frame (~11°), so a walk to a point BEHIND the actor becomes a wide ARC (radius ≈ speed/omega ≈ 150u) and, for a nearby point-behind, ORBITS it forever → the synchronous Walk never converges → softlock. (My test also had the z-convention backwards again — Vivi faced the camera and I'd put the target behind him.) **Fix (commit `1dc8a88`):** `cutscene.actor_walk` now emits `TurnTowardPosition(x,z)` + `WaitTurn` BEFORE `InitWalk`+`Walk` — the actor pivots IN PLACE to face the destination first, then walks straight (no arc; converges from any facing; no-op when already facing). Added `opcodes.turn_toward_position` (0x9B, uses posZ directly, no Z-negation). Fixed the test coords (Vivi at BACK facing camera → walks FORWARD to greet [no turn] → walks BACK [180° about-face, exercises the fix]). Disasm-verified the spliced sequence: `DisableMove; Wait(30); TurnTowardPosition(0,-800); WaitTurn; InitWalk; Walk(0,-800); TurnTowardObject(250); WaitTurn; WindowSync(501); TurnTowardPosition(0,-450); WaitTurn; InitWalk; Walk(0,-450); EnableMove; flag=1`. 206 tests; redeployed to 4003.

**Lesson (z-convention, the 3rd time):** for these pitch-down cameras, **more-negative z = FRONT (toward camera/bottom of screen)**, less-negative = back; NPCs spawn **facing the camera** (toward -z/front), so a forward walk = toward more-negative z. Use the paint guide's BL/BR/FR/FL labels; don't guess.

**PLAYTEST 3 — PARTIAL: forward walk + face + "...hi." WORKED; the ~180° walk-back gave "no pivot, no control return" (softlock). FIXED + redeployed.** Cause (`StartTurn`/`ProcessTurn`): a BIG turn takes the ANIMATED path (`ExecAnim(actor.turnl)`); if that turn animation doesn't drive the rotation to completion, the turning flag (128) never clears → `WaitTurn` `stay()`s forever. The forward walk's pre-turn was a no-op and the face-player turn was small (instant branch) — both fine; only the 180° animated pre-turn hung. **Fix (commit `aaf6df4`):** dropped the animated pre-turn from `actor_walk`; instead it cranks `SetWalkTurnSpeed`(omega) to **255** so the Walk ITSELF rotates ~179°/frame toward the target and goes straight — converges to a point directly behind, deterministic at exactly 180°, no `WaitTurn`, no animated turn. Added `opcodes.set_walk_turn_speed` (0x55). Disasm-verified: `DisableMove; Wait(30); SetWalkTurnSpeed(255); InitWalk; Walk(0,-800); TurnTowardObject(250); WaitTurn; WindowSync(501); SetWalkTurnSpeed(255); InitWalk; Walk(0,-450); EnableMove; flag=1`. 206 tests; redeployed.

**PLAYTEST 4 — PASS ✅ ("all good - went as planned. instant turn").** Full v2 actor cutscene works in real gameplay: control locks → ~1s beat → Vivi **walks forward** to greet → **faces the player** → says "...hi." → **spins ~180° (instant turn via omega=255) and walks back** to his spot → **control returns**; talk → "Oh! You're finally here…"; re-enter → he just stands (plays once). **Tagged `KNOWN_GOOD-s18-cutscene-actor`.**

**v2 actor cutscenes COMPLETE + in-game-verified.** A `[cutscene] actor = "<npc>"` makes that NPC walk / face / talk during a control-locked, once-gated scene — authored declaratively, spliced into the NPC's Init (gExec = the NPC), grounded byte-for-byte in real FF9 data, zero Hades Workshop. **Two engine gotchas cracked (in memory `project-ff9-eb-script-tooling`):** (1) **entry warm-up** — issuing an actor command during the field's entry fade/smooth-updater settle makes it circle + the synchronous walk hang; emit `DisableMove; Wait(~30); …` first. (2) **walk turn-radius** — `Walk` moves at full speed while rotating only ~omega/frame, so a walk to a point BEHIND the actor orbits forever; crank `SetWalkTurnSpeed(255)` so the walk turns tightly + goes straight (do NOT use an animated `TimedTurn`/`TurnTowardPosition`+`WaitTurn` pre-turn — it HANGS at ~180° when the actor's turn animation doesn't complete → flag-128 never clears → softlock). New kit surface: `cutscene.actor_walk`/`actor_teleport`/`actor_animation`/`actor_turn`/`actor_face` + `[cutscene] actor`/`warmup`; opcodes `walk`/`init_walk`/`set_walk_speed`/`set_walk_turn_speed`/`move_instant_xzy`/`run_animation`/`wait_animation`/`turn_instant`/`timed_turn`/`turn_toward_object`/`turn_toward_position`/`wait_turn`.

**Carry-over:** field 4003 = CUTSCENE2 test (revert `py tools/scroll_out/revert_deploy.py`). Debug New-Game→Alexandria warp still active.

**Next (optional v2 follow-ups, NOT yet in-game-tested):** `animation` (a wave/emote — kit supports it; needs a verified Vivi anim id) and `teleport` walk-in from off-screen (carries the `MoveInstantXZY` Z-negation). Or move on to other content/release work.

### 2026-06-05 — Session 18 (cont) — v2 cutscene POLISH: teleport walk-in + emote animation (built + deployed, AWAITING PLAYTEST)

Both deferred v2 follow-ups, grounded + built:
- **Animation** — `{ animation = <id> }` = `RunAnimation(id) + WaitAnimation`. The id must be a ONE-SHOT anim valid for the NPC's model (a looping/invalid id → WaitAnimation waits forever). **Grounded** a Vivi (model 8 / animset 61 — our exact preset) anim id from real field 790's Vivi entry: **7302 = Talk_3_1** (used there as `RunAnimation(7302)+WaitAnimation`, so a confirmed one-shot). Other confirmed Vivi ids: 6693/6698/6702 (Look_Down), 7312/7320 (Talk_3).
- **Teleport walk-in** — `{ teleport = [x,z] }` = `MoveInstantXZY(x,z)` (Z-negated, source-confirmed) **+ `SetPathing(1)`** (0xA8; MoveInstantXZY DISABLES walkmesh collision, SetPathing(1) re-enables it — the real `Vivi_18` walk-in pattern). `build_choreography` emits a **leading teleport BEFORE the warm-up** (instant + safe during the entry transition) so the actor settles off-screen instead of flashing at its spawn, then warms up + walks in.
- New opcode `set_pathing`(0xA8). 208 tests. Disasm-verified the showcase: `DisableMove; MoveInstantXZY(-1150,-800); SetPathing(1); Wait(30); SetWalkTurnSpeed(255); InitWalk; Walk(0,-800); TurnTowardObject(250); WaitTurn; RunAnimation(7302); WaitAnimation; WindowSync(501); EnableMove; flag=1`. The teleport's MoveInstantXZY x/z decode to (-1150,-800) (Z-negation correct).

**In-game test redeployed (4003 = CUTSCENE2):** Vivi appears at the cyan LEFT cross (teleport), walks in to his magenta spot, faces the player, plays the Talk_3_1 gesture, says "Oh! You're finally here…"/"...hi.". `tools/build_cutscene_actor_test.py` rewritten for this; FORMAT.md notes the one-shot-anim caveat.

**PLAYTEST (polish) — FAILED, FIXED + redeployed.** Screenshot showed Vivi warp + double-walk on entry, then fail to land on the target (script never finished). **Cause:** my "leading teleport before the warm-up" optimization put `MoveInstantXZY` DURING the field entry transition, where the smooth-frame-updater fights it (erratic warp/slide; the follow-up walk started from a bad state and never converged → synchronous Walk hung). **Fix:** reverted it — ALL actor commands (teleport included) run AFTER the warm-up Wait (the whole point of the warm-up). Restructured the test so Vivi starts at his HOME (left, `CreateObject` there → no spawn-flash), walks in to greet, faces, emotes (`RunAnimation 7302`), says a line, then **teleports home** (teleport now fires at the very end, field fully settled = safe; verifies the mechanic + Z). Disasm: `DisableMove; Wait(30); SetWalkTurnSpeed(255); InitWalk; Walk(0,-800); TurnTowardObject(250); WaitTurn; RunAnimation(7302); WaitAnimation; WindowSync(501); MoveInstantXZY(-1150,-800); SetPathing(1); EnableMove`. 208 tests; redeployed. (Lesson: the warm-up gates EVERY actor command, not just walks — a teleport mid-transition is just as broken.)

**PLAYTEST — walk reaches the spot now; Vivi GLIDES in his idle anim (no walk anim).** Cause (`ProcessEvents`:239-251): the engine swaps idle→walk while an actor moves ONLY when `animFlag & (afExec|afLower|afFreeze)` is 0 (or exactly `afExec|afLower`); a player-cloned NPC's idle leaves `afExec` set → swap blocked → glides in idle. **Fix:** `actor_walk` emits `StopAnimation` (0x42 → `DefaultAnim` clears the flags) before `InitWalk`+`Walk`, so the auto walk-anim swap fires. `opcodes.stop_animation`. **Reload loop (user ask):** set the test cutscene `once = false` → re-entering the field replays it (walk out the back door + back in), no game restart. 208 tests; redeployed.

**PLAYTEST — StopAnimation did NOT fix the glide; scene LOCKED at the face-turn + Vivi still slides; user (rightly) wants the reload hotkey.** Two responses:

**(1) ENGINE: F6 reload-current-field dev hotkey — BUILT + DEPLOYED.** `FieldMap.HonoLateUpdate`: F6 → `SetNextMap(current) + loc.map.nextMode=1 + FF9StateSystem.attr|=8` (the proven `Field()`-opcode reload path) → re-runs Main_Init (replays `once=false` cutscenes, re-creates NPCs) + escapes any cutscene softlock. Built via VS18 BuildTools (`/p:SolutionDir=...\Memoria\`, auto-deploys x64+x86; pre-build DLLs backed up `backups/Assembly-CSharp.dll.*.preReload.*`). Patch `memoria-patches/s18-field-reload-hotkey.patch`. Dev engine only (the shipped mod is engine-independent).

**(2) SCENE: made NON-BLOCKING so it can't softlock.** The lock was `WaitTurn` (face) / `WaitAnimation` (emote) never returning — the player-cloned NPC's walk/turn anims don't drive them to completion (same root as the glide). The kit now NEVER uses `WaitTurn`/`WaitAnimation`: `actor_turn`=`TurnInstant` (instant facing, no anim needed), `actor_face`=`TurnTowardObject` (no wait), `actor_animation`=`RunAnimation`+fixed `Wait(40)`. Test uses `turn=0` (instant face front). 208 tests; redeployed.

**OPEN — the deeper anim-playback puzzle:** non-idle anims (walk auto-swap, animated turn) don't engage for a player-cloned NPC even with anims correctly set (walk 571/run 419/turnl 917, verified) + `StopAnimation`. The glide persists; unknown if `RunAnimation` (the emote) plays at all. NOT yet root-caused. Now diagnosable fast via F6.

**PLAYTEST RESULT (decisive):** F6 reload ✓; instant turn (`TurnInstant`) ✓ visible; teleport ✓; walk MOVES + converges ✓; dialogue ✓; **no softlock** ✓. BUT **no skeletal animation EVER plays** — Vivi glides (no walk cycle) and `RunAnimation 7302` (emote) shows nothing. So it's not the walk-swap specifically: the model's transform updates (move/rotate) but its ANIMATOR never plays a clip.

**Root traced (`FieldMapActorController`):** non-player actors animate via `PlayAnimationViaEventScript()` → plays `actor.anim`'s clip only `if (this.animation.GetClip(name) != null)` (`this.animation = this.model.GetComponent<Animation>()`). Our NPC's clips aren't there/playing. Clips are loaded by `AnimationFactory.AddAnimWithAnimatioName(go, ...)` in the `Set*Animation`/`RunAnimation` handlers; `SetModel`'s 2nd arg is HEAD HEIGHT, not an animset; `SetModel` has an early `return 0 if charArray.ContainsKey(po.uid)` that skips `AddFieldChar`. **Likely root: our NPC is CLONED FROM THE PLAYER OBJECT** — the player animates from input via a different path, and the clone's model/animator isn't set up for script-driven clip playback. NOT yet fixed (can't validate the model/animator setup offline).

**DECISION POINT (asked the user):** (A) accept the functional cutscene; or (B) pursue the animated-NPC fix. **User chose (B).**

**ROOT CAUSE — FOUND via a 2nd engine probe (`ANIMPROBE2` in `ProcessEvents`), decisive.** Probe logged our NPC (uid=2) over time: during the cutscene **`state=2`, `animFrame=0` (frozen)**; the instant it ended, **`state=1`, `animFrame=5,15,… (advancing)`**. `ProcessAnime` (which advances `animFrame`) only runs when **`obj.state == stateRunning (1)`** — and an object's **Init executes at `state=2`**. Our choreography was baked into the NPC's **Init**, so its frames never advanced → glide + frozen emote. **The player-clone was innocent** (component + all clips were `ok` per the 1st probe); the model + transform updated fine, only the skeletal frames were frozen. Real FF9 cutscenes run actor actions OUTSIDE the Init (in a function that executes at state 1) for exactly this reason.

**FIX (committed):** prepend the choreography to the NPC's **LOOP (tag 1)**, not its Init — the loop runs at `state=1`, so frames advance. Always gated (the loop runs every frame): **GLOB flag** for `once=true` (plays once ever), **transient MAP flag** for `once=false` (replays each visit — keeps the F6 iteration loop). `npc.inject_npc(intro=)` now targets tag 1; `cutscene.once_flag_for` picks the flag class. Disasm-verified: Init (tag 0) = setup only (no DisableMove); Loop (tag 1) = `if(!mapBit80){ DisableMove; Wait(30); SetWalkTurnSpeed; StopAnimation; InitWalk; Walk; TurnInstant; RunAnimation(7302); Wait(40); WindowSync; MoveInstantXZY; SetPathing; EnableMove; flag=1 }` then the loop body. 208 tests. Probes (`ANIMPROBE`/`ANIMPROBE2`) still in the engine to confirm the fix (remove after).

**PLAYTEST — ANIMATIONS WORK ✅** (user: "animations are good"; screenshots show Vivi mid-walk + mid-emote). The loop-placement fix is correct. One remaining bug: **the teleport-home landed at the wrong Z** (player could walk over Vivi). Root: `MoveInstantXZY` (POS3) ends with `SetActorPosition(po, destX, destZ, destY)` = `po.x=arg1, po.y=destZ(-arg2), po.z=destY(arg3)` — so despite the "XZY" name the bytecode args are **(worldX, −worldY, worldZ)**; arg3 is the world depth Z, arg2 is the negated height. My encoder had **Y and Z swapped** (put −z in arg2), so Vivi landed at z≈0 (back edge). **Fixed:** `move_instant_xzy(x, z, y)` → `encode(0xA1, x, -y, z)`; teleport(-1150,-800) now → world (-1150, 0, -800). Disasm-verified. **Engine cleaned:** the two anim probes removed + rebuilt (F6 reload hotkey kept). 208 tests; redeployed.

**PLAYTEST (final v2 check) — PASS ✅ ("all clear").** Vivi walks in (animated walk cycle), turns, emotes, says "...hi.", then teleports back onto the cyan cross (correct Z now — Zidane can't walk over him), control returns. **v2 cutscenes COMPLETE + in-game-verified: walk + animation + turn + say + teleport, all animated + correctly placed**, authored declaratively in the kit (`[cutscene] actor = "<npc>"`), zero Hades Workshop. Tagged `KNOWN_GOOD-s18-cutscene-polish`.

**The decisive lesson (now in memory `project-ff9-eb-script-tooling`): actor choreography MUST run in the NPC's LOOP (tag 1), not its Init (tag 0).** `ProcessAnime` (advances `animFrame`) only runs when `obj.state == stateRunning(1)`; an object's Init executes at `state=2`, so Init-spliced choreography moves the transform but FREEZES the skeleton (glide, no emote). Proved with an in-engine `animFrame` probe (`state=2 animFrame=0` during, `state=1 animFrame=5,15…` after). The loop runs every frame → the block is always flag-gated (GLOB for `once=true`, transient MAP for `once=false`/dev-replay). Other gotchas folded in: warm-up `Wait(30)` before the first step (entry-transition settle); `SetWalkTurnSpeed(255)` to avoid the walk-to-point-behind orbit/softlock; NEVER `WaitTurn`/`WaitAnimation` for a player-cloned NPC (clips don't complete them → softlock) — use instant turns + a fixed `Wait(40)` anim hold; `MoveInstantXZY` args = (worldX, −worldY, worldZ) + `SetPathing(1)` after; `animation` ids must be one-shot (Vivi 7302=Talk_3_1). Plus the **F6 reload-current-field dev hotkey** (`memoria-patches/s18-field-reload-hotkey.patch`) that made the iteration loop fast.

**Engine/game state:** clean S12 dev engine + F6 hotkey (probes removed). Field 4003 = CUTSCENE2 actor-cutscene test (once=false, replays per visit); revert `py tools/scroll_out/revert_deploy.py`. Debug New-Game→Alexandria warp still active. 208 tests pass.

**The full content + scripting stack is now COMPLETE and in-game-proven:** rooms → cameras (single / scrolling / multi) → walkmesh (author / import / reshape) → NPCs / dialogue → gateways → encounters → events (chests / gil / flags) → story branching → **cutscenes (narration v1 + actor walk/turn/emote/teleport v2)** — authored declaratively (`field.toml` + Blender), linted, save-persistent flags, all in Python, zero Hades Workshop.

**Next options:** (a) author a real, populated demo area end-to-end with the full stack (narrative content); (b) wire a story-positioned real-playthrough entrance + release-cleanup pass (remove debug warp, package); (c) Blender front-end support for cutscenes/events (the script side is text-authored today); (d) multi-camera v2 follow-ons or other polish.

### 2026-06-06 — Session 19 — Authorship-suite UX: Blender event markers + a FORM-BASED logic editor (offline-built, AWAITING human verify)

**User goal:** complete the authorship suite — "everything available to place in Blender" + "an easier way to edit scripts (accessible to people who don't wanna edit TOML)". User chose (AskUserQuestion) the **form-based desktop editor** over all-in-Blender / web / node-graph. The architecture that fell out: **Blender = where things are (spatial); a Tkinter editor = what they do (logic)**, keeping the proven `scene.toml` (Blender-owned) / `field.toml` (logic) split. All offline (Hard-Constraint §2: I can't run the Blender or Tk UI — the human verifies; the non-UI cores are fully unit-tested).

**Done (234 tests pass; bpy-free + tk-free cores tested, UIs py_compiled):**
- **Blender event-zone markers (add-on v0.8.0).** New `FF9_Event` marker (amber zone quad like a gateway) + operator + panel button + props (name/message/set_flag/once). Export splits it exactly like NPCs/gateways: the **zone → scene.toml**, the **actions → field.toml** stub, merged by name (the kit's `_ENTITY_LISTS` already had `"event"`). bpy-free `bridge.events_to_toml` + scene/field-split helpers; 3 offline tests. Rebuilt `dist/ff9mapkit_blender-0.8.0.zip`. So Blender now places NPC / gateway / **event** / spawn.
- **The form-based logic editor (`ff9mapkit edit`).** Ships in-kit at `ff9mapkit/editor/`:
  - `model.py` (tk-free): `dumps()` = a dependency-free, round-trip-safe TOML writer (`tomllib.loads(dumps(d)) == d`, proven on a representative doc + every bundled example) + `FieldDoc` that edits/saves the **logic file only**, never the Blender scene, with a `merged()` view that reuses `build._merge_scene` so what you see == what `build` compiles. 8 tests.
  - `forms.py` (tk-free): spec-driven field definitions + parsers + entity↔form round-trip + cutscene-step helpers. 13 tests.
  - `app.py` (Tkinter): a tree of logic sections (Field / Encounter / Music / Cutscene / NPCs / Gateways / Events), a generic spec-form panel, add/delete entities, a reorderable **cutscene step editor**, and **Check logic / Build to game / Build & Test(4003) / Revert** (reuses `build_mod` + `validate`/`lint_logic` + the dev deploy tools when present). The `_apply` glue is tested headlessly (2 tests).
  - CLI `ff9mapkit edit [field.toml]` + `tools/ff9_editor.pyw` double-click launcher. README + Blender README updated.
- Commits: `blender: event-zone markers`, `editor: model layer`, `editor: form-based field-logic editor`, `suite: add-on v0.8.0 + docs`.

**Deliberately deferred (not yet built):** Blender **camera-switch zones + multi-camera posing** (the last "place in Blender" item — multi-camera *posing* is the hardest Blender piece, and it only makes sense paired with camera-zone markers; the editor intentionally punts all camera/spatial to Blender). Tracked as the next task.

**AWAITING HUMAN VERIFY (two independent things):**
1. **The editor:** run `py tools/ff9_editor.pyw` (or `ff9mapkit edit ff9mapkit/examples/vivi-hut/hut_int.field.toml`). Open an example, edit dialogue / add an event / add a cutscene with steps, Save, Check logic, and (optionally) Build & Test(4003). Confirm the UI works and the saved field.toml builds + plays.
2. **Blender event markers:** install `ff9mapkit/blender/dist/ff9mapkit_blender-0.8.0.zip` (Get Extensions → Install from Disk), drop an **Event** marker, set message/set_flag, Export → `ff9mapkit build` → walk into the zone in-game (chest/lever fires).

**Next:** after verify — Blender camera-zones + multi-camera posing (task #55); then final docs/packaging polish (task #60).

**FIRST PLAYTEST → black screen → root cause was the TEST HARNESS, not the editor/cutscene (FIXED).** User edited the bundled vivi-hut example (id **4002**), added cutscene steps, Build & Test → black screen; reverted. Diagnosis:
- The cutscene `.eb` builds CLEAN (disasm-verified, 288 instr) — not the bug.
- `tools/deploy_field.py` appended the field.toml's OWN id/name to DictionaryPatch. The example is id 4002, so it registered `FieldScene 4002 …` and left the **4003 slot (where the door points) unregistered → black screen**. Worse: the example is NAMED `HUT_INT`, so the deploy overwrote `EVT_HUT_INT` + `FBG_N11_HUT_INT`, and the generated revert (name==HUT_INT) **restored then immediately `unlink`'d EVT_HUT_INT + `rmtree`'d the scene** → it DELETED the live "Vivi's House" interior (4002).
- **Fix (committed):** `deploy_field.py` now forces the test build to **id 4003 + name `TESTROOM`** (in-memory; the on-disk field.toml is untouched), so ANY field tests safely in the 4003 sandbox with zero collision against a live field. The revert is consequently safe too (operates on TESTROOM). Verified offline (the HUT_INT example → `FieldScene 4003 11 TESTROOM TESTROOM 1073`) and via a clean live re-deploy.
- **Restored the live interior** (scene from `release/`, script from the `*-EVT_HUT_INT.eb.bytes.preDEPLOY.20260606-135930` backups, all 7 langs) — verified whole (10 entries: player + talking Vivi + gateway; real `floor.png`/`walls.png`; both HUT DictionaryPatch lines). Also removed the stale buggy `revert_deploy.py` (the deploy auto-runs the prior revert first, and the old HUT_INT one re-deleted the interior on the retry).
- **Lesson (handover mistake):** never edit the *bundled example* in place — the editor's Save rewrote the byte-exact golden oracle `hut_int.field.toml` (restored via `git checkout`). Author on a COPY or via `ff9mapkit new` / a Blender export. (Candidate hardening: the editor could refuse to save over a file under `examples/`/site-packages.)

**A working cutscene test is now deployed to 4003 (TESTROOM):** Alexandria (fast-warp door) → TESTROOM → a narration cutscene plays on entry. Revert with `py tools/scroll_out/revert_deploy.py`.

**Second miss → another GOTCHA (not a bug): the once-flag was already SET.** First redeploy used `once=true` (the narration default), which gates on the **save-persistent GLOB flag 8100** — the SAME default the S18 CUTSCENE/CUTSCENE2 tests used, so the user's save already had 8100 set → the cutscene skipped ("already played"). The editor's cutscene was built + armed correctly all along (disasm-confirmed: `Main_Init InitCode[3,0]` arms an entry-3 director `if(!8100){DisableMove; say; wait; say; EnableMove; 8100=1}`). Redeployed with **`once=false`** → the director is UNGATED (replays every entry, transient MAP path). **Testing lesson:** for iterative cutscene/event testing use `once=false` (replays), or a fresh New Game, or a distinct `flag` index — a `once=true` test won't replay once its persistent flag is set. This is the user's pending re-verify.

**Third miss → REAL bug, FIXED: narration cutscene didn't lock player control.** A narration cutscene (no actor) runs in a separate code entry armed by `InitCode` in Main_Init — but Main_Init calls `EnableMove` (+ a fade) AFTER that `InitCode`, so the director's `DisableMove` was immediately overridden → the player kept control during the text. (Actor cutscenes avoid this by living in the NPC's LOOP, which only runs after Init completes — which is why they locked correctly in S18.) Fix (`content/cutscene.build_body`): prepend a brief reorder `Wait` (`REORDER_WAIT=2`) so the director yields, Main_Init reaches its `EnableMove` (first frame), then the director's `DisableMove` is the LAST control-setter and the lock sticks. ~2 frames = imperceptible. Tests updated (235 pass); redeployed to 4003 (disasm-confirmed director = `Wait → DisableMove → say → wait → say → EnableMove`). **Offline-validated; awaiting the user's in-game confirm that control now locks.** (Fallback if timing still loses: move narration into Main_Loop/entry-0 tag-1 like the actor path — no code for that yet.)

**VERIFIED IN-GAME ("that did the trick").** Control now locks through the narration cutscene, then returns. **The form-based logic editor is therefore proven END-TO-END in the user's hands:** open a field.toml → edit logic in forms → add a cutscene with steps → Save → Build & Test → in 4003 the cutscene plays AND locks control. Tagged `KNOWN_GOOD-s19-editor-verified`. Three fixes landed off this one playtest thread: (1) `deploy_field.py` sandboxes any field into the 4003 slot (id+name) — no more black-screen/clobber; (2) testing gotcha documented (a `once=true` cutscene/event won't replay once its save-persistent flag is set — use `once=false`/New Game/distinct flag); (3) narration cutscenes lock control (reorder `Wait` past Main_Init's `EnableMove`). Live state: 4003 = the once=false cutscene TESTROOM (revert `py tools/scroll_out/revert_deploy.py`); the real "Vivi's House" interior (4002) restored + intact.

**Authorship-suite status:** ✅ form editor (`ff9mapkit edit`) — built + in-game-verified. ✅ Blender event-zone markers (`FF9_Event`) — built + offline-tested (in-Blender verify still pending). ⏳ remaining for "everything in Blender": camera-switch zones + multi-camera posing (task #55). ⏳ final docs/packaging (task #60).

**Blender MULTI-CAMERA built (add-on v0.9.0; offline-validated, AWAITING in-Blender + in-game verify).** The last "everything in Blender" item. The kit side ([[camera]] array + [[camera_zone]] + per-layer camera) was already in-game-proven (S18 TRICAM); this is the Blender front-end. **P1 (bpy-free bridge, tested):** `cameras_borrow_toml` (a `[[camera]]` array, each entry borrowing one EXACT posed `.bgx` — the build resolves each independently to N cameras, index 0 = default), `camera_zones_to_toml` (`[[camera_zone]]` to_camera+zone), `layers_to_toml` per-layer `camera` (0 omitted, so single-camera output unchanged). A full build dry-run (2 borrowed cameras + a switch zone) asserts the built scene `.bgx` has 2 CAMERA blocks + the script has a `SETCAM` (0x7E). **P2 (bpy UI):** Camera box gets a **Yaw** field + **Add Camera** (each FF9 camera tagged `ff9_cam` index, posed from the panel; select one to edit); **Cam Zone** marker (`FF9_CamZone`, blue quad + `ff9_to_camera`, enabled only with 2+ cameras); per-layer **cam** index in the layer rows; the from-scratch export branches single (`[camera] borrow camera.bgx`, unchanged) vs multi (write `cameraK.bgx` each + `[[camera]]` array + per-layer camera + `[[camera_zone]]`). Emits the proven tricam shape. 237→ tests pass; bpy py_compiles; zip rebuilt → `dist/ff9mapkit_blender-0.9.0.zip`. Commits: `blender(multicam) P1`/`P2`. **Open:** scroll+multicam combo not supported (rare); multi-camera only on the from-scratch (non-fork) export.

**VERIFIED IN-GAME ("all clear").** User posed 2 cameras + Cam Zones + per-camera layers in Blender, exported, deployed to 4003, and the view cuts between camera angles correctly. Two UX fixes shipped during verify: **v0.9.1** — `Add Camera` double-linked the object (`_link_active` now idempotent + no redundant link) → fixed the "already in collection" RuntimeError; and **Pose Camera** now targets the SELECTED camera (+ sets scene.camera) so each camera is editable independently (click camera → set Yaw/Pitch → Pose), with the panel readout following the selected camera. **v0.9.2** — added a **Read Camera** button (`FF9MK_OT_read_camera`) that loads the selected camera's pitch/distance/FOV/yaw into the panel (the user's "sync on select" request; a reliable explicit button rather than a global selection handler I can't verify offline). Add-on zip → `dist/ff9mapkit_blender-0.9.2.zip`. **Blender now authors the FULL spatial vocabulary in-game-proven: camera (single/scroll/multi) · walkmesh (author/import/reshape) · layers · NPC · gateway · event · spawn · cam-zone.** "Everything in Blender" is DONE. Tagged `KNOWN_GOOD-s19-blender-multicam`.

**Authorship suite — BOTH original asks complete + in-game-verified:** (1) easier script editing → `ff9mapkit edit` form editor; (2) everything placeable in Blender → all markers + multi-camera. Remaining: final docs/packaging polish (task #60).

**Blender `FF9_Event` marker VERIFIED IN-GAME.** User installed add-on v0.8.0, did New Scene → Set Spawn → Add Event (message "Works!") → Export → deployed to 4003 via `deploy_field.py` (and confirmed the `ff9_build_gui` "Test field 4003" path routes through the same fixed sandbox deploy). Walked into the amber zone → message fired. **Confirmed intended:** an event does NOT lock player control (it's a walk-in `WindowSync` trigger — standard chest/lever behavior); cutscenes are the control-locking primitive. (A future opt-in `lock` on events is possible if a freezing trigger is ever wanted.) So Blender now places NPC / gateway / **event** / spawn, all in-game-proven. Live: 4003 = the EVTTEST/TESTROOM event room (black bg, New-Scene; revert `py tools/scroll_out/revert_deploy.py`).

### 2026-06-06 — Session 19 (cont) — Polish pass + regression hardening (offline; release plan deferred)

User reordered: do the **polish pass + regression testing now**, circle back on the release plan after. Hard constraint, verbatim: **"DO NOT MAKE ANYTHING PUBLIC."** All offline, kit-codebase only — no live-game change, no public actions (PR #1433 untouched, no push). Plan in `~/.claude/plans/sunny-zooming-bonbon.md` (rewritten for polish). Three read-only audits (tests / docs+version / code-quality) scoped it: tests already healthy (kit 237 + blender 47), no TODO/FIXME, legacy hacks already well-documented — the real surface was version incoherence, stale docs, an editor footgun, and a thin `doctor`.

**Done (5 commits on `master`; each = one change → suite green → commit):**
- **Version → 0.9.3, lockstep** (`de15dbb`): kit was stuck at 0.1.0 ("under construction"), add-on at 0.9.2. Bumped all 5 sites (pyproject, `ff9mapkit/__init__`, add-on `build_addon.py`/`__init__ bl_info`/`blender_manifest.toml`), repackaged `ff9mapkit_blender-0.9.3.zip`, deleted 18 stale dist zips. User chose 0.9.3 lockstep (pre-1.0 = clearly not-yet-public).
- **Docs refresh** (`517b6c0`): dropped the README "under construction" banner for an honest 0.9.3 + a "what's in the box" feature list; added `import`/`list-fields` rows (+ `walkmesh verify`) to the commands table; marked multi-camera **supported** in PIPELINE.md (was "Still future"); bumped Blender doc version refs (0.3.0/0.4.5 → 0.9.3). Staleness grep across shipped `*.md` → clean.
- **Editor save-guard** (`8505bd5`): new pure tk-free `model.protected_reason(path)` wired into `app.py` on_save/on_new — refuses to overwrite a bundled example / installed-package file / anything under site-packages (the exact footgun that clobbered the golden `hut_int.field.toml` this session). on_save now returns `False` when blocked so Build/Test aborts.
- **`doctor` pre-flight** (`05ff473`): reports kit version + UnityPy availability up front (even when the game path isn't configured) + a StreamingAssets check.
- **Regression hardening** (+3 tests): save-guard unit test (`test_editor_model.py`) + a **form-spec ↔ builder coherence guard** (`test_editor_integration.py`, `232bebf`) — drives entities through the editor's forms layer (`entity_to_values`→`build_entity`, asserting no key drops) and then the REAL builder, so the hand-written forms can't silently drift from the compiler.

**Regression baseline (offline, my lane):** full suite **kit 240 + blender 47 = 287 green** (was 284; +1 save-guard, +2 coherence); golden byte-exact guards + vendor drift guard all pass after the version bump; `py -m ff9mapkit doctor` → `ff9mapkit 0.9.3`, UnityPy present, StreamingAssets found; add-on repackages to 0.9.3. Code/`.toml` grep for `0.1.0`/`0.9.2` → none. Working tree clean (only untracked dev noise: `backups/*.preDEPLOY.*`, `human_testing/`, the gitignored dist zip). **Completes task #60.**

**No in-game test needed** (polish is non-gameplay). Live game state unchanged: dev engine + Alexandria fast-warp + field 4003 = the EVTTEST event room (carry-over). **Next: the deferred RELEASE PLAN** — and at that point the live-game cleanup (debug warp removal, stock-engine restore, `release/FF9CustomMap` repackage) + any public actions are decided with the user.

### 2026-06-06 — Session 19 (cont) — Editor noob-friendliness + import tested on REAL fields (release still deferred)

User (post version-bump): polish the **script editor** for clarity/noob-friendliness, and **test importing actual in-game scripts** ("never checked if they're importable"). All offline, no public actions, no live-game change.

**Importability — tested for the first time, found + fixed a big gap:**
- The `import → edit → build` flow works end-to-end on a real field: forked GLGV (borrow) → opened the generated `field.toml` via `FieldDoc` → added an NPC → Save preserved the spatial sections (single-file project) → validate + build clean. Editable mode also works (no in-game pre-export needed).
- **Breadth sweep (one field per map code, 51 codes):** surfaced that ~10 codes live in **single-digit areas (0-9)** — Alexandria (ALXC/ALXT), ship interiors (TSHP/BSHP/CSHP), Evil Forest, Ice Cavern, airship, UDFT… — and import was emitting `field.toml`s that **fail to build** (the area-≥10 engine limit: `FBG_N<area>` is read as exactly 2 chars, so 0-9 black-screen). A large fraction of the game was effectively un-importable with a confusing downstream error.
- **Fix (`14c72e8`, `extract.py`):** **editable** forks remap a low source area → safe `>=10` (a custom scene ships its own art under `FBG_N<area>_<name>`, so the area is just a folder key; confirmed an area-11 ALXC fork builds `FBG_N11_ALXC_EDIT`) with a NOTE comment; **borrow** refuses a low-area field up front with a clear "use `--editable`" message (borrow MUST match the real area, so 0-9 genuinely can't borrow). New `safe_custom_area()` helper + `MIN_CUSTOM_AREA=10` + 1 offline test (extract's UnityPy import is lazy, so the rule is testable without game data).
- Note (not fixed): `list-fields alex` → 0 hits because the map code is `ALXC`, not "alex" — field names are cryptic map-codes; a discoverability aid is a possible future nicety.

**Editor UX pass (`b2d131d`):** made `ff9mapkit edit` approachable cold — an **empty-state Welcome panel** (what it edits, the Blender-vs-editor split, where `field.toml`s come from, the workflow, what "(+)" means), a **Help button + dialog** with the same tour, **de-jargoned inline help** on every field (`name` "-> FBG_N<area>…" → "short tag like MY_ROOM"; `area` notes "lower areas don't render"; NPC `preset` "the easy path", custom model warns it needs anims in the `.toml`), and Open/New now **land on the Field form** instead of leaving the welcome up. Forms help-text is tk-free (round-trip tests unaffected); the `app.py` UI is **human-verify per the can't-run-Tk constraint** — user should open the editor and eyeball the Welcome/Help once.

**Regression:** full suite **kit 241 + blender 47 = 288 green** (+1 editor save-guard from the prior entry already counted; this pass added the area-rule test). Commits: `14c72e8` (import area handling), `b2d131d` (editor UX). Live game untouched; release still deferred.

**`py -m ff9mapkit` namespace-shadow bug — found via the user + FIXED (`cb3a0ba`).** User ran `py -m ff9mapkit import … --editable` from the repo PARENT `C:\gd\FFIX` and got `ImportError: cannot import name '__version__' from 'ff9mapkit' (unknown location)`. Root cause: the repo's doubled folder name (`C:\gd\FFIX\ff9mapkit\ff9mapkit\`) means from `C:\gd\FFIX` the cwd's `ff9mapkit\` child (project dir, no `__init__.py`) loads as an empty PEP-420 **namespace package**, shadowing the real install (editable reinstall did NOT help; Python 3.14). Also found the editable install metadata was stale at 0.1.0. Fix: `__main__.py` runs at the real package path, so it now detects the shadow (`pkg.__file__ is None`) and inserts the real package dir on `sys.path` + purges the namespace from `sys.modules` before importing the CLI. Verified `py -m ff9mapkit --version` → 0.9.3 from `C:\gd\FFIX`, and the user's exact (typo'd-but-unique-substring) command imports cleanly. +1 portable subprocess regression test (`tests/test_cli_entry.py`: empty sibling `ff9mapkit/` dir). README note: if the `ff9mapkit` command isn't on PATH, use `py -m ff9mapkit <cmd>`. Suite now **kit 242 + blender 47 = 289**.

### 2026-06-06 — Session 19 (cont) — `import` now extracts CONTENT (gateways/BGM/encounters/movement), not just art

**User Q "why does import drop the existing gateways?"** → answered (import only read the spatial layer; it never parsed the source `.eb`) and the user said: build gateway import + "think of other things we currently skip… feasible + useful." Picked the four single-opcode, unambiguous patterns (all chosen via AskUserQuestion: **all extras + emit LIVE**): gateways, field BGM, encounters, movement-direction. NPCs/dialogue/cutscenes deliberately stay author-fresh (lossy/contextual).

**Grounded byte-for-byte** by disassembling a real field's `.eb` (Alexandria/Main St, `tests/fixtures/alex100-us.eb.bytes`) + the kit's region template:
- **FBG → event-script name** is bakeable + authoritative (no suffix guessing): Memoria's `EventEngineUtils.eventIDToFBGID` (id→`FBG_N..`) + `FF9DBAll.EventDB` (id→`EVT_..`) are both keyed by field id → join on id. `_regen_fieldtable.py` bakes `ff9mapkit/_fieldtable.py` `FBG_TO_EVT = {fbg_lower: [field_id, "EVT_.."]}` (**676 field maps**; 818 FBG ids − 142 world/special with no field event). Event binaries live in **p0data7** at `…/eventbinary/field/<lang>/EVT_<name>.eb.bytes`.
- **Exit-region byte pattern:** an entry holding BOTH `SetRegion` (0x29) and `Field` (0x2B). Zone = SetRegion points, each packed **x = v&0xFFFF, z = v>>16 (signed i16)**; real exits use 4 points or 5 with the last doubled (the kit's IsInQuad-safe convention). Target = `Field` arg. **Entrance = the i16 assigned to var `D8:02` right before `Field`** (`05 D8 02 7D <i16> 2C 7F`) — exactly the kit's gateway-template `REL_ENTRANCE`/`REL_FIELD` offsets. Also: BGM = `RunSoundCode(0, song)` (0xC5, code 0 = song_play); encounter = `SetRandomBattles` (0x3C) + `SetRandomBattleFrequency` (0x57); movement = `SetControlDirection` (0x67, TWIST).

**Built (offline; commits `13d0960` table+scanner, `871d5c0` loader+wiring, docs):**
- `eventscan.py` — reads gateways/music/encounter/control-direction out of a `.eb` (inverse of the `content/*` injectors). Verified against alex100: finds its 3 real exits (101/107/114, entrance 200) **+ the door we injected in Session 12** (→4000), BGM 9, head-on movement, no encounter. Round-trips against the kit's own injectors too.
- `extract.extract_event_script` (FBG→event table → p0data7 events-bundle, cached `.ff9mapkit-events-bundle.txt`, never raises) + `_imported_content_toml` → both `write_field_project` (borrow) & `write_editable_project` (editable) emit **LIVE** `[[gateway]]`/`[encounter]`/`[music]` + `[camera] control_direction`, gateways with a "retarget — these are real field ids" note. Falls back to the old commented stub when no event mapping. CLI prints the imported content. **Zero new builder work** — all four land on existing in-game-proven schemas. 254 kit tests (+12).

**Offline end-to-end PROVEN against the real game (read-only, no launch):** `import glgv_map792_gv_rm1_0` → field.toml with its **2 real exits** (→2350 ent 20, →2351 ent 21), real **encounter** (scenes [210,210,210,349] freq 104), **BGM 110**, movement 0 — and it **`build`s** clean. (The Blender import/editable path is unaffected — content lives in the logic `field.toml`, which Blender export preserves.)

**AWAITING IN-GAME (user):** import a real field (borrow), `build` + deploy to 4003, walk into an exit → it should warp to the real destination; confirm encounters trigger + BGM plays. Then the fork keeps the real place's exits/battles/music out of the box. **Next options:** multi-camera *switch-zone* extraction (the deferred ~8% case); or back to the release plan.

### 2026-06-06 — Session 19 (cont) — Instant New-Game warp + engine reduced to STOCK + F6 (in-game verified)

**Two deliverables, both in-game-verified.** (1) A command **dashboard** (`deploy-dashboard.html`, repo root) — click-to-copy of the everyday commands; arg'd commands open a fill-in form (labels + help + live preview), no-arg ones copy on click. (2) **Instant New-Game warp into 4003**, then **reduced the dev engine to stock + only the F6 hotkey** so the mod is fully stock-Memoria-releasable (user goal: stop depending on Memoria / PRs).

**Engine inventory + the PR (answered for the user):** 4 local Assembly-CSharp edits existed — `BGSCENE_DEF` fade-cache, `SettingsState` booster-auto-on, `EventEngine.Initialize` New-Game→100, `FieldMap` F6. **The shipped mod needed NONE of them** (content + the battle-return fade [`.eb` tag-10 FadeFilter] are mod files). **PR #1433 (FieldCreatorScene PNG path) is irrelevant to us** — it fixes the in-game editor's `ExportMemoriaBGX`; the `[Export] Field=1` path `--editable` import relies on is a *separate* function (`FieldSceneExporter` → `FieldMaps/<FBG>/OverlayN.png`) that never calls it. So we owe Memoria nothing.

**Decision (user):** keep ONLY F6 in the dev engine → drop the other 3. Reverted them in the clone (`git checkout`, kept `FieldMap.cs`), rebuilt (`msbuild … '-p:SolutionDir=C:\gd\FFIX\Memoria\'`, auto-deploys x64+x86; verified fade-cache marker gone, New-Game back to stock `fldMapNo=70`, F6 intact). Backed up the 4-edit DLL first (`backups/Assembly-CSharp.dll.4edit-dev.*`). Deployed engine now = base `6b8bb2d5` + F6 only.

**The warp (`tools/newgame_warp.py`, pure-mod, reversible `tools/scroll_out/revert_newgame_warp.py`):** appends a code entry that does the **proven field-70 fade+Field transition** (verbatim block: DisableMove; DisableMenu; FadeFilter; Wait(25); set D8:2=entrance; PreloadField; Field), activated by a **shift-free overwrite** of an executed instruction in Main_Init.
- **Dev-engine mode (default):** field 100 (where the dev engine sent New Game) → Field(4003), gated on entrance 231 so the hut-return (204)/normal arrivals are untouched.
- **`--stock` mode (now live):** field 70 (stock New-Game opening) → `Field(100, 231)` → field 100 sets up the party + runs its →4003 warp → 4003. **Why the double-hop:** `EventEngine.NewGame()` does NOT create the party (verified in source) — field 100's script does, so routing through it keeps a normal party (a direct field-70→4003 would land party-less).

**Two bugs cracked en route (both in memory `project-ff9-eb-script-tooling`):**
1. **Dead-code activation.** First attempt overwrote a Main_Init `Wait` that sits right after `op_01` — which is the engine's **unconditional JMP** (undocumented in `DoEventCode` alongside 0x02/0x03/0x06), so it was skipped and the warp never fired (New Game → normal Alexandria). Fix: activate at an instruction inside the **InitRegion cluster** (proven executed — the door's InitRegion lives there), before that jump.
2. **Party not from NewGame().** `NewGame()` only clears state + picks the field; the party comes from the entered field's script → the stock warp must route through field 100.

**Human verified (in-game):** New Game on the stock+F6 engine → ~200ms opening + ~200ms Alexandria (the two field loads/fades of the double-hop) → **4003**. User: insignificant wait, accepted as-is (removing the Alexandria flash = skipping field 100 = losing the party). Tagged `KNOWN_GOOD-s19-stock-f6-warp`.

**State:** dev engine = stock + F6 (mod is engine-independent / stock-releasable). Warp deployed `--stock` (field 70→100→4003). Boosters now manual (ini cheats + F1/F3; auto-on dropped). `s12-engine-edits.patch` no longer deployed (kept as record + the 4-edit DLL backup); only `s18-field-reload-hotkey.patch` (F6) is live. PR #1433 left as-is (not needed).

### 2026-06-06 — Session 19 (cont) — Release-readiness pass: capture the breadth (docs/examples, offline)

User's goal: make `ff9mapkit` a **stellar release** and **capture the breadth** of the (large) feature set. All offline/docs, no game change. Done + committed:
- **`docs/FEATURES.md`** — the canonical capability matrix (every feature, ✓ in-game-verified markers, a **before/now** comparison table, honest "not in scope"). Linked top of README.
- **`docs/gallery/`** — captioned scaffold + a 13-shot checklist (user drops in screenshots/GIFs by filename).
- **`docs/TECHNICAL.md`** — the depth/credibility write-up of the hard problems (the projection invariant `k=14/15`, exact scale-1 canvas map, measured-zero character offset, byte-exact `.eb` authoring, the `vert+orgPos+floor.org` walkmesh frame, import via the source-baked FBG→event table, the engine gotchas).
- **`docs/TUTORIAL.md`** — "your first field in ~10 minutes" (fork → NPC → lint → build → reach via a gateway).
- **`LICENSE`** (MIT, author `GameJawnsInc`) — code-only, with an explicit note that FF9 game data isn't covered/redistributed. `CHANGELOG.md` (Keep-a-Changelog; 0.9.3 state + toward-1.0 gate).
- **`examples/SHOWCASE/`** — one buildable field exercising most of the content stack (NPC+dialogue, flag-gated NPC reveal, chest event w/ item+gil+flag, encounter+BGM, narration cutscene) + `examples/README.md` index + a build **regression test** (`tests/test_showcase.py`). 257 tests pass.

**User recalibration (noted):** dropped the "owe Memoria nothing" framing — be a good community citizen (credit Albeoris/Memoria generously; a clean showcase + scoped contributions are how an unknown account becomes a known quantity). The user is a pro dev using Claude Code to move fast; the release doubles as a credibility/portfolio piece.

**Remaining before a public 1.0 (NOT done):**
1. **PROVENANCE GATE** (the real blocker): stop bundling FF9-derived bytes (`data/blank_field/*.eb`, `region_template.bin`, `tests/fixtures/*`) — build a "bring your own install" extractor that pulls them from the user's game; needs the user's go (bigger task). Until then, **do not publish the repo as-is** (it contains Square Enix data).
2. Gallery **screenshots** (user-owned) + the **YouTube video** (outline earmarked in chat; not started).
3. `0.9.3 → 1.0.0` bump when shipped. The 2 Memoria upstream items: PR #1433 (FieldCreatorScene) left open/irrelevant; nothing else to submit.

**`KNOWN_GOOD-s19-stock-f6-warp`** remains the current tag (no in-game change this pass).

### 2026-06-06 — Session 19 (cont) — PROVENANCE GATE CLEARED: repo ships zero SE game data + privacy scan clean

**The release blocker is solved.** `ff9mapkit` now contains **no Final Fantasy IX game bytes** — it regenerates the few base assets it needs from the user's OWN install, like a "bring your own ROM" tool. All offline, Claude-owned; 253 kit tests pass. Commit `b214773` on `master`.

**What was game-derived + how it's handled now (validated against the live install):**
- **blank field** (956B/lang, every built field's base) ← field 1357 (Hangar) cleaned: **92.6% copied from the user's file, only ~3–39B/lang are our edits**.
- **exit-region template** (272B) ← `ALEX3_AT_WEAPON` (`fbg_n01_alxt_map031_at_wpn_0`, the real "field 109") exit region: **98.2% copy, 5B edits**. (The old "field 109" was the HW filename; the real source is ALEX3_AT_WEAPON, found by brute-force diff over all 818 fields.)
- **test fixtures** ← regenerated from identified sources: `alex100-us` = **vanilla** `ALEX1_AT_STREET_A` + the kit's own door injection (no AlternateFantasy bytes; eventscan oracle unchanged); `grgr.bgx` = real GRGR camera; `multifloor.bgi` = a real **3-floor** walkmesh (`tshp_map008_th_upr_0`) that round-trips byte-exact + is seam-clean (GRGR's 7-floor has 2 padding bytes the codec drops, so it failed the round-trip test → swapped).
- **build goldens** (the hut, which embeds the blank) → compared by **SHA-256** in the manifest, not shipped bytes.

**What ships instead (all ours, no game bytes):** copy/insert **patches** (`data/provenance/*.patch`) + a SHA-256 **manifest**. New `ff9mapkit/provision.py` (patch codec + extraction orchestration; loaders read a gitignored cache + raise a clear "run extract-templates") + maintainer `data/_regen_provenance.py` (authors the patches from a vanilla install, asserts byte-exact reproduction). New CLI **`ff9mapkit extract-templates`** + a `doctor` "templates: extracted/NOT" line.

**Airtight INVARIANT (guarded + tested):** no patch insert run ≥4 bytes ever duplicates a run present in the source field — so even the per-language field name is *copied* (referenced by offset), never shipped. `make_patch` decomposes inserts to enforce it (`provision.patch_game_runs` audits; `_regen_provenance` asserts). Proven: the jp patch's 35B Shift-JIS name insert → 0 after the fix.

**Verified at every layer:** (1) `git ls-files` — the only tracked binary is `hut_ext.bgi.bytes` (OUR 232B quad from `bgi.quad()`, not game data) + example/placeholder PNGs; no `blank_field`/`region_template`/fixtures tracked. (2) **A built wheel contains zero game bytes** (`package-data` restricted to `data/provenance/*`, so a wheel can't bundle FF9 bytes even on a machine where extract-templates has run). (3) `extract-templates` regenerates all 11 blobs + self-verifies against the manifest. (4) `conftest.py` skips the byte-level suite cleanly (pointer to extract-templates) when templates absent — pure-logic suite (cam math, editor, provision codec) still runs offline; `tests/test_provision.py` (5 tests) covers the patch codec + invariant.

**`_fieldtable.py` kept** (676 field-name identifiers) — derived from **Memoria's open-source** tables (not the game), the same data Memoria publishes; documented in `docs/PROVENANCE.md`. Flagged as the one gray area; user's call.

**Docs:** new `docs/PROVENANCE.md` (rationale + the airtight guarantee + setup); README quickstart adds `extract-templates`; ENGINE.md/CHANGELOG updated. `.gitignore` makes game-derived data un-committable by default (`*.eb.bytes`/`*.bgx`/`*.bgi.bytes` ignored except our hut quad) + ignores `blender/human_testing/` scratch.

**Privacy scan (the follow-up) — CLEAN.** Whole tracked tree + commit history + untracked-not-ignored files: no personal email (gmail absent everywhere), no secrets/keys/tokens, no real name, no Steam IDs, no other-user paths, no tracked personal config. **Git commits already use the GitHub noreply identity** (`122755272+GameJawnsInc@users.noreply.github.com`) — no real name/email leaks via history. Only identifiers present: the intentional `GameJawnsInc` handle + `skaki` in paths (user said skaki is fine). Per the user, skaki paths were excluded from scope.

**Note (out of scope, flagged):** `release/` + `mod/` (the FFIX dev repo's actual FF9CustomMap mod) contain game-derived *mod* content by nature — that's normal mod-distribution territory (any FF9 mod modifies game data), distinct from the toolkit. The provenance fix is about the **toolkit** not shipping game data; the mod is the user's call if they ever publish the whole FFIX repo (vs just `ff9mapkit/`).

**Remaining before a public 1.0:** gallery screenshots (user-owned) + the YouTube video (earmarked); `0.9.3 → 1.0.0` bump when shipped. The provenance blocker is now cleared — `ff9mapkit/` is safe to publish (it contains no SE data and no private info). **Standing constraint still in force: nothing pushed/made public.**

### 2026-06-07 — Session 20 — Dialogue wrap + animation catalog + cutscene-movement (markers→paths→auto-path) + editor/Blender round-trip; F6 hot-reload

Big "cutscene/explorable/interactable" polish session — all kit-side (Claude-owned), each piece in-game verified by the user. 306 kit + 50 blender tests. Commits land per-feature; kit `0.9.4`, add-on `0.9.5`.

**Dialogue auto-wrap (in-game ✓).** Cracked from source: FF9 field dialogue does NOT auto-wrap — the font is a *runtime dynamic TrueType* (`EncryptFontManager` → `Font.CreateDynamicFontFromOSFont`, default bundled `TBUDGoStd-Bold`, overridable in `Memoria.ini [Font]`), measured by Unity per-install, so pixel-exact wrapping is impossible offline. Built a PROPORTIONAL relative-glyph-width model (`content/text.py` `measure`/`wrap_text`, `[dialogue] wrap`, default 28) that breaks long lines; short lines stay byte-identical (goldens safe). Respects manual `\n`/`[PAGE]`; build warns on an unbreakable over-wide word. (User confirmed FF9 overflows off-screen; I'd been wrong that it wrapped.)

**Animation catalog (in-game ✓ "that worked").** `FF9DBAll.AnimationDB` is the id↔name table (`7302 = ANH_MAIN_F0_VIV_TALK_3_1`); the name token = the model (`VIV`/`ZDN`/`GRN`/`STN`/`FRJ`/`KUI`/`EIK`/`SLM`). `AnimationFactory` loads a clip by name→folder `GEO_<g>_<f>_<tok>` on demand → any `_<tok>_` anim plays on that model. Baked `_animdb.py` (MAIN-character anims, from Memoria source like `_fieldtable`) + `ff9mapkit animations <preset>` CLI; cutscene `animation = "glad"` resolves via the actor's preset.

**Cutscene-movement reliability arc (the headline; all 3 increments in-game ✓).** Engine truth (`EventEngine.MoveToward.cs` + `WalkMesh.Collision`): a field walk is straight-line + SYNCHRONOUS, so a blocked walk presses the obstacle forever and softlocks. Collision distance = `4·collRadA + 4·collRadB`; the kit's chars get `collRad=24` (field-1357 player-init `RADIUS` 0x4B, inherited by clones — READ from the built .eb, not the engine default 16) → a 192u box. `disdif = dx²+dz²−r²`.
  - **(1) Markers + stall checks:** `[[marker]]` named points + `@player`/`@npc` refs in `walk`/`teleport`; a walk TO an object auto-stops ~232u short (`cam.OBJECT_COLLISION_W=96`); build WARNS (off-floor target / target-in-a-box / path-crosses-wall / path-through-a-character — exact point-segment test). `tools/deploy_field.py` + F6 each step.
  - **(2) Multi-waypoint `path`:** `{ path = ["a","b","c"] }` = consecutive validated legs, to route around obstacles by hand.
  - **(3) Auto-pathing:** `content/pathfind.py` grid-A* over the walkmesh (≥ controller radius from walls, ≥ 192 from each character) + string-pull → a plain `walk` routes around walls AND characters automatically; clear walks untouched (byte-identical); only a bad target or a truly unroutable walk still warns; explicit `path` stays exact.
  Two real bugs the user caught mid-arc: walk-to-@player still stalled (collRad was 24 not 16 → fixed the constant), then the next leg stalled (path THROUGH the player's box → added the point-segment object check).

**F6 hot-reload loop (in-game ✓ — big workflow win).** Discovered F6 (our dev-engine reload hotkey) RE-READS the current field's mod files from disk on the field reload — script (.eb), text (.mes), scene/walkmesh/art all refresh. So the dev loop is now **edit → `deploy_field.py` → F6, NO relaunch** (only the first deploy of a session needs one relaunch to register field 4003; BattlePatch + engine DLL also need relaunch; F6 reloads only the field you're in). Documented in `tools/deploy_field.py`.

**Blender `FF9_Waypoint` markers (in-game ✓; add-on 0.9.4).** Place named movement points visually → `scene.toml [[marker]]`; a cutscene references them by name. (`marker` joined `_ENTITY_LISTS` so it merges; bridge/ops/ui + tests.)

**Script-builder (editor) overhaul (kit 0.9.4; forms unit-tested, Tk user-verified).** Caught the form editor up to the kit: **Markers** + **Dialogue** sections; cutscene steps brought current — `path` step + `walk`/`teleport`/`animation` accept NAMES (markers/@player/gesture) not just numbers, with a live per-step-type hint; one-line purpose under every section header (`SECTION_HELP`) + refreshed Help dialog.

**Blender Import round-trip (in-game ✓; add-on 0.9.5).** Import used to load only camera+walkmesh+spawn, so a re-opened project lost its content and a forked field's extracted gateways never showed. Now Import re-creates NPC/waypoint/gateway/event markers (+ spawn) from the field.toml (+ a sibling `scene.toml` for positions); `bridge.merge_import_entities` (bpy-free, tested) + `ff9_verts_to_blender` for placement; named entities dedupe.

**Engine/game state:** dev engine (S12 build + F6 hotkey). Field 4003 = the last movement test deploy; debug New-Game→Alexandria warp still active. The full content+scripting stack (rooms → cameras → walkmesh import/reshape → NPCs/dialogue[speaker/tail/wrap] → gateways → encounters → events → branching → cutscenes[narration + actor walk/path/auto-path/animation-by-name]) is authorable from Blender (spatial) + the form editor (logic) + CLI, with a no-relaunch F6 loop.

**Next options:** dialogue **choices** (`[CHOO]` — the missing interaction/puzzle primitive); scripted camera pans in cutscenes; moving/animated objects (doors/platforms); or the release-cleanup pass (debug warp removal, package, the open Memoria PR #1433). Standing constraint: nothing public.

### 2026-06-07 — Session 21 — Modern editor UI + dialogue CHOICES (NPC + zone) end-to-end

Two user asks, both fully landed + in-game-verified: (1) modernize the Field Editor's look; (2) build dialogue **choices** — the interaction/puzzle primitive — and push it through every pipeline (CLI/build → form editor → Blender), iterating on in-game feedback. All offline-tested (kit **337** + blender **53**), each piece human-verified in real gameplay. Commits `e79150b`→`2756b1e`.

**Modern Field Editor (`ff9mapkit edit`, commit `e79150b`; kit 0.9.5).** New `editor/theme.py`: a `clam`-based theme that **auto-matches Windows light/dark** (reads `HKCU…AppsUseLightTheme`, safe light fallback) — flat widgets, Segoe UI, an accent on Save / Build&Test, roomier tree, a severity-colour-tagged console log. No new dep (palettes + OS probe are tk-free + headless-tested). User: "validated."

**Dialogue choices — the whole feature (the bulk of the session).** `[[choice]]`: a menu that **branches** on the pick. Grounded byte-for-byte in a real FF9 shop (field 817) + Memoria source.
- **Mechanism:** a synchronous `WindowSync` whose `.mes` text is `prompt` then option rows after `[CHOO][MOVE=18,0]`; the picked row lands in `ETb.sChoose`, read by the expression sysvar token **`B_SYSVAR` 0x7A code 9** (`GetSysvar(9)==GetChoose()`). The kit branches `if (GetChoose()==i){…}` via `region.cond_sysvar_eq` (extends the proven movement-gate sysvar read). New `content/choice.py` (`branch`/`region_body`/`speak_body`/`option_body`); `region.push_sysvar`/`cond_sysvar_eq`. (`77ed477`)
- **NPC choice:** `[[choice]] npc="<name>"` → talking replaces the NPC's plain `_SpeakBTN` with the branch (`npc.inject_npc(speak_body=…)`).
- **`give_item` by NAME** (`fd4269e`): baked `_itemdb.py` from Memoria's `RegularItem` enum + `items.resolve` (name|id, fuzzy) + CLI `ff9mapkit items`. **232 = Sapphire, Potion = 236** — the old `[232,1]` in tests/stubs was the Sapphire footgun; `give_item=["Potion",1]` now. Build/lint error on an unknown item name.
- **`gil` can subtract** (`079e3ef`): `AddGil` (0xCE) is UNSIGNED → a negative wrapped to a max-gil add. Added `RemoveGil` (0xCF); `give_gil` picks by sign (`gil=-100` charges 100).
- **Movement locks during the menu** (`937e700`): the engine does NOT block field movement for an open dialog, so the d-pad drove BOTH cursor + character. `speak_body` now `DisableMove…EnableMove` (real shops do this; the menu still navigates because choice input comes from the dialog system, not field control).
- **Zone-triggered choices (a lever)** (`9317fb4` → `3e90119`): `[[choice]] zone=[…]`. CRITICAL crash fix (`11cff1d`): a `walk`-tread once-flag must be **GLOB**, not MAP — `EventContext.mapvar = new Byte[80]`, so a high index (8200) in MAP space is out of bounds → **hard crash**. Then the design pivot (`3e90119`): default `trigger="action"` = **press-action-in-quad (region tag 3)**, the FF9 lever/sign mechanism. Edge-triggered by the button → can't loop, needs no gate flag, re-usable, and **"decline" is non-destructive**. `trigger="walk"` keeps the auto-pop tread path (tag 2, flag-gated; `once` true/false via an Init flag-reset). Region tags: **tag 2 = tread (every frame), tag 3 = interact (press; `IsQuadTalkable` is true by default for a plain region)**. `region.build_region_entry/inject_region` gained `tag` + `init_body`/`init_extra`.
- **One-shot lever** (`24702fa`/`a368de4`/`2756b1e`): the composable pattern — the consuming option's `set_flag` + the choice's `requires_flag_clear` on that flag (same flag usually drives the door it opens). A spent lever **fully disappears**: the consuming option `TerminateEntry`s the region (no leftover interaction-prompt bubble) and the Init only `SetRegion`s while the flag is clear (`region.gated_set_region`) → gone on revisits too. **GOTCHA:** TerminateEntry must run **AFTER `EnableMove`** (built as `region_body + if(flag) TerminateEntry + RETURN`) — terminating inside an option (before EnableMove) kills the entry early and **freezes the player**.
- **Editor + Blender:** editor `CHOICE_SPEC` (npc/zone/trigger/once/prompt/options sub-editor w/ reorder; `ITEMCOUNT` kind for `give_item` by name); model serializer writes nested `[[choice.options]]` round-trip-safe (`7543075`/`b5fc931`). Blender preserves a hand-authored `[[choice]]` through re-export (logic file never clobbered) + the scaffold stub now hints a `[[choice]]` and uses `["Potion",1]` (add-on **0.9.6**, `44fce6d`). FORMAT.md fully documents `[[choice]]`.

**Engine facts captured (fold into memory `project-ff9-eb-script-tooling`):** `B_SYSVAR`=0x7A (reads next byte as a `GetSysvar` code; code 9 = `GetChoose`); choice text = `[CHOO][MOVE=18,0]` rows; **`EventContext.mapvar` is only 80 bytes — high flag indices MUST be GLOB**; region **tag 2 = tread / tag 3 = press-interact** (`CheckQuadInput`→`Request(obj,1,3)`, `IsQuadTalkable` default-true); **`ProcessCode` steps running functions regardless of `usercontrol`** (so DisableMove inside a region doesn't stall it); **TerminateEntry before EnableMove freezes the player**.

**Engine/game state:** dev engine (S12 build + F6 hotkey). Field 4003 = the one-shot LEVER test (action-trigger, `requires_flag_clear=8001`); revert `py tools/scroll_out/revert_deploy.py`. Debug New-Game→Alexandria warp active. Tagged `KNOWN_GOOD-s21-choices`.

**Next (the list, agreed):**
1. **Dev-engine "reset save state" hotkey** — alongside F6's field-reload, a key that clears `gEventGlobal` (story/once flags) + optionally restores a snapshot of inventory/gil, so testing flag-gated content (levers/chests/story gates) doesn't need a New Game each time (this session's recurring friction).
2. **Dig into the pre-choose configs** — `[PCHC]`/`[PCHM]` text tags + `EnableDialogChoices` (0x7C `CHOOSEPARAM`): grey-out / disable specific choice options, set the default/cancel row. Wire into `[[choice]]` (e.g. `option.enabled_flag` / a disabled state) while we're still tweaking choices.
3. Then: scripted camera pans in cutscenes; moving/animated objects; or the release-cleanup pass. Standing constraint: nothing public.

### 2026-06-07 — Session 21 (cont) — Dev-engine "reset save state" hotkey (F10) + F6/F10 input-reliability fix

**Done (engine, both in-game verified):**
- **F10 = reset save state + reload field.** Mirrors `EventEngine.NewGame()`'s flag reset: `Array.Clear(gEventGlobal)` (the 2048-byte save-backed story/once flag array, `EventState.cs:10`) + `gScriptVector.Clear()`/`gScriptDictionary.Clear()` (Memoria's persistent script stores), then the F6 reload path (`SetNextMap(fldMapNo)` + `loc.map.nextMode=1` + `attr|=8`). Re-arms once-gated content (levers, chests, cutscenes, `requires_flag` gates) WITHOUT a New Game; inventory/gil/party untouched. User verified: pull the lever → F10 → lever returns.
- **Fixed F6/F10 intermittent "dead press" (+ booster error SFX).** Root cause: the hotkeys read `UnityEngine.Input.GetKeyDown` in `FieldMap.HonoLateUpdate`, which runs on `HonoBehaviorSystem`'s ~30fps logical tick (`TargetFrameTime=0.0333` + frame-skip, dispatch at `HonoBehaviorSystem.cs:147`), while `GetKeyDown` is true for exactly ONE render frame → at 60+fps the keydown frame usually isn't a tick frame and is dropped (~4 presses to land, matching the report). The "error sound on dead presses" was the tell: `UIKeyTrigger`'s F6→LvMax handler (`UIKeyTrigger.cs:278`) fires reliably every press (plays `FF9SFX_Play(102)` when the cheat is off) while the throttled reload didn't. **Fix:** moved both hotkeys into `UIKeyTrigger.Update()` (per-render-frame MonoBehaviour) on `UnityXInput.Input.GetKeyDown` (the same proven path as the boosters), gated on `UIState.FieldHUD`, intercepted BEFORE `HandleBoosterButton()` so F6 no longer also fires the LvMax SFX. `FieldMap.HonoLateUpdate` reverted to stock. User verified: F6/F10 fire on every press, no dead presses, no error sound.

**Engine facts captured:** `HonoBehavior.HonoLateUpdate`/`HonoUpdate` run on the throttled ~30fps logical tick, NOT per render frame — never read `Input.GetKeyDown` there (it misses). Read dev hotkeys in a real MonoBehaviour `Update()` (e.g. `UIKeyTrigger`) via `UnityXInput.Input`. F-keys F1–F8 are booster cheats, F9/F12 taken (TurboDialog etc.); F10 is free.

**Engine/game state:** dev engine = stock `6b8bb2d5` + F6 reload + F10 reset, both in `UIKeyTrigger` (Release, 5,502,464 B, x64==x86). Backups `backups/Assembly-CSharp.dll.{x64,x86}.f6f10-reliable.20260607-044423`. Patch `memoria-patches/s21-dev-hotkeys-f6-f10.patch` (UIKeyTrigger.cs; supersedes s18). Field 4003 = one-shot LEVER test. Tagged `KNOWN_GOOD-s21-reset-hotkey`. (Restore the no-edit engine: `tools/restore_memoria_dll.py baseline`; true stock = re-run patcher.)

**Next:** pre-choose configs — `[PCHC]`/`[PCHM]` text tags + `EnableDialogChoices` (CHOOSEPARAM 0x7C): grey-out/disable specific `[[choice]]` options + set the default/cancel row.

### 2026-06-07 — Session 21 (cont) — Pre-choose config (default / cancel / hide) — built, probed, in-game verified

**Built `[[choice]]` pre-choose config + cracked two engine bugs with an in-engine probe (user's call). In-game verified.** New `[[choice]] default = N` (highlighted row), `cancel = N` (row B/Cancel picks; -1/omit = last), `[[choice.options]] disabled = true` (removes the row). Mechanism (Memoria `Dialog.SetupChoose` + `ETb.SetChooseParam`, grounded in field-100's ATE menu): `EnableDialogChoices` opcode (CHOOSEPARAM `0x7C`, args `[mask:2, default:1]`) sets the availability bitmask (bit i = row i on, LSB-first) + default; a `[PCHM=count,cancel]` text tag tells the dialog to APPLY the mask (hide disabled rows), `[PCHC=count,cancel]` sets count/cancel/default without disabling. `GetChoose()` returns the ABSOLUTE row index regardless of disables, so the per-option branch is unaffected.

**Two engine facts cracked via a temporary `[FF9PRECHOOSE]` probe** (logged CHOOSEPARAM args → `SetChooseParam` → `NewMesWin` reset → `GetChoose` → `SetupChoose`; rebuilt Release, user ran the repro, read `Memoria.log`, then removed the probe + rebuilt clean):
1. **Sign bug (the real default failure):** the all-on mask `0xFFFF` is sign-extended by `getv2` to `-1`, and `SetChooseParam`'s loop is `while (availMask > 0)` → with `-1` it never runs → `sChooseInit` falls to 0 → default collapsed to row 0 (even with NO disabled rows). **Fix: emit the exact positive bitmask `(1<<n)-1`, never `0xFFFF`.** Default now honored.
2. **default + disabled can't combine (engine limitation, NOT fixable kit-side):** `SetChooseParam` converts the absolute default → AVAILABLE-row index, but `Dialog` consumes `DefaultChoice` as ABSOLUTE (+ a disabled→`active.Min()` remap), so a default at/after a hidden row falls back to the first available row. `lint_logic` now WARNS on this combo. Also: a `disabled` row is HIDDEN (FF9 builds no widget — not greyed-and-visible); corrected the docs.

**Human verified (in-game):** default=2 → "Third" highlighted every open ✓; cancel=0 → B picks "First" ✓; a `disabled` row is removed from the menu ✓. Tagged `KNOWN_GOOD-s21-prechoose`.

**Kit:** `opcodes.enable_dialog_choices` (0x7C), `content.choice.pre_choose` (returns setup opcode + `[PCHC]`/`[PCHM]` tag) + `setup` param on `region_body`/`speak_body`, build wiring (NPC + zone choice paths + collect_text tag), `validate` (default/cancel range, not-all-disabled) + `lint_logic` (unhonorable default warning), editor `CHOICE_SPEC` default/cancel + `disabled` option, FORMAT.md. 348 tests. Commits `4a792fe`→`af4d787`. Engine unchanged (probe removed; clean F6/F10 Release redeployed). Field 4003 = the default+cancel demo (revert `py tools/scroll_out/revert_deploy.py`).

**Next (v2 — the genuinely useful disable):** flag-gated hide — a row hidden UNTIL a story flag is set ("show *Use the key* only once you have it"). Needs the runtime-mask path scoped during this dig: build the mask in a scratch var from flags (`set_var` + `if(flag) or_var`, ops `B_OR_LET`/`B_PLUS_LET` confirmed) and pass it as an EXPRESSION arg to `EnableDialogChoices` (gArgFlag bit + bare-RPN `<var-token> 0x7F`; `encode(..., arg_flags=1)` already supports it). Var tokens: GLOB UInt16 scratch = `0xDC` (VariableType.UInt16=7). Verify the expression-arg byte format against a real field first.

### 2026-06-07 — Session 21 (cont) — Choices v2: flag-gated hide (option visible until/once a story flag) — real-field-verified + in-game

**Built the genuinely-useful disable: `[[choice.options]] requires_flag = N` (row hidden UNTIL flag N set) / `requires_flag_clear = N` (hidden ONCE set). In-game verified incl. F10 reset.** The kit builds the availability mask AT RUNTIME from story flags and passes it to `EnableDialogChoices` as an EXPRESSION arg.

**Verified byte-for-byte against a REAL field first (user's explicit ask).** Mapped the HW exports' `EnableDialogChoices( VAR | const )` usages → field IDs (manifest is HW-index→field-ID, so test2_NNN ≠ field NNN), extracted **field 407 (Dali/Storage Area, `fbg_n08_udft_map122_uf_sto_0`)** from p0data, disassembled its CHOOSEPARAM bytes — the moogle-mail menu builds its mask exactly this way:
```
05 d9 21 7d 02 00 3f 7f          VAR_MapInt16#33 |= 2        (B_OR_LET = 0x3F)
7c 01 d9 21 7d 04 00 26 7f 00    EnableDialogChoices(VAR | 4, 0)   (gArgFlag=01 -> arg0 is an EXPRESSION)
7c 03 .. (arg `d6 09 7f` = a BARE var + 0x7F)                       (bare-var expression-arg is valid)
```
So confirmed: opcode arg N is an expression iff gArgFlag bit N set (the `[op][gArgFlag][args]` byte after every opcode, `EventEngine.getv1/getv2`→`CalcExpr`); expression-arg = bare RPN terminated `0x7F` (NO leading `0x05`); `B_OR`=0x26, `B_OR_LET`=0x3F. Var byte-mapping (`EBin.GetVariableValueInternal`): Byte/Int16/UInt16 index = a direct BYTE offset into the 2048-byte gEventGlobal (Bit index = bit number) — and a **UInt16 read via the expression path is UNSIGNED** (no `0xFFFF`→-1 trap).

**Kit (real-field-grounded):** `region.GLOB_UINT16=0xDC` + `MASK_SCRATCH_IDX=2040` (high byte offset, clear of base vars + the 8000+ bit-flags; F10-reset-safe since rebuilt each open) + `or_var`(0x3F) + `var_expr` (bare-var expr-arg); `opcodes.enable_dialog_choices_var` (arg_flags=1); `choice.dynamic_mask_setup` (set_var base + `if(flag) or_var` per gated bit + EnableDialogChoices expr-arg) + `pre_choose` 3-mode (flag-gated→runtime mask, static-hide→literal partial mask, default/cancel→all-on `(1<<n)-1`). validate (no both requires set+clear) + lint (a `requires_flag` with no setter = dead; gated rows extend the default warning) + editor option fields + FORMAT.md. 353 tests (+5).

**Human verified (in-game):** CONSOLE first shows only Buy/Leave; walking the SWITCH (an event set_flag=8001) reveals "Use the Gate Key"; **F10 reset re-hides it.** Tagged `KNOWN_GOOD-s21-prechoose-v2`. Commits `aafdaab` (v2) + test builder. (Benign UX note: the switch's message is a synchronous window, so its set_flag lands after you close it — standard "you got X → then it's yours"; not a choice issue.)

**The choice system is now COMPLETE end-to-end:** NPC/zone triggers → branch → reply/item/gil/flag → default/cancel row → static hide → **flag-gated hide**. Field 4003 = the flaggate test (revert `py tools/scroll_out/revert_deploy.py`).

### 2026-06-07 — Session 21 (cont) — Reward-event conventions matched to real FF9 + chest niceties + F10 control-fix

**Made our reward events byte-faithful to FF9's own treasure-chest convention (user's "import/export truthiness" goal), all grounded against real fields + in-game-verified.**

**Convention pass (grounded in Dali/Storage field 407, Cleyra/Sandpit 1102, …):** a real chest is `if (GetItemCount<99) { if (!opened) { opened=1; AddItem; SetTextVariable; window-7 "Received <item>!" } }` — i.e. **dedup-flag set FIRST, effects before the acknowledgement message**. Two kit fixes to match:
1. **set_flag before the message** (`build.py` event body): an event doesn't lock movement, so a set_flag AFTER the message only landed when the player closed the window (they could walk off first). Moved set_flag (+ live-reveal) ahead of the message. User: "good reorder."
2. **once-flag first** (`event_range_body`): was `if(!once){ body; once=1 }`; flipped to `if(!once){ once=1; body }` to match the chest (dedup lands the instant the event fires).

**Chest niceties (both real-field-verified byte-for-byte, in-game-confirmed — a Potion chest gives via the item-get window, once, F10 re-arms):**
- **`[[event]] received = true`** (give_item) → the canonical FF9 item-get window: `SetTextVariable(0, item)` (0x66) + `WindowSync(7, 0, txid)` with text `"Received [ITEM=0]!"`. Window type 7 = the special acquisition box; `[ITEM=0]` renders `GetItemName(textvar[0])`.
- **`[[event]] require_space = true`** (give_item) → `if (GetItemCount(item) < 99) { … }` wrapping the whole reward (space-check OUTERMOST), so a full bag skips it AND leaves the once-flag unset (retryable).

**Engine facts cracked (fold into memory `project-ff9-eb-script-tooling`):** base **`GetItemCount` = expression fn token `0x64`** (pops an item-id const, pushes the held count; NOT Memoria's custom `flexible_varfunc`/`ITEM_FULL_COUNT`); **`B_LT = 0x18`**; **`SetTextVariable` = 0x66** argsize [1,2]; **`[ITEM=n]` text tag** = `ETb.GetItemName(gMesValue[n])` (variable-slot, fed by SetTextVariable); **WindowSync window-type 7** = the item-get box. All match real field 407 bytes exactly (`05 7d ec 00 64 7d 63 00 18 7f` = `GetItemCount(236)<99`; `66 00 00 ec 00` = `SetTextVariable(0,236)`).

**F10 control-fix (dev hotkey):** pressing F10 while STANDING IN a tread zone (chest) fired that zone once on reload — F10/F6 soft-reload (`SetNextMap`+`nextMode=1`) keeps the player at the carried position, and the tread check (gated only on `usercontrol`) won the race before Main_Init repositioned to spawn. Fix: `EventEngine.SetUserControl(false)` before the reload; Main_Init re-enables control after positioning. User: "clean — no extra potion, F10 resets the state, F6 blocks it from further uses." Engine: F6 reload + F10 reset + this fix, all in `UIKeyTrigger` (Release, 5,502,464 B); patch `memoria-patches/s21-dev-hotkeys-f6-f10.patch`.

**Kit surface:** `region.cond_item_count_lt`/`or_var`/`var_expr`/`GLOB_UINT16`/`MASK_SCRATCH_IDX` + tokens (T_LT 0x18, T_ITEMCOUNT 0x64, T_OR_ASSIGN 0x3F); `opcodes.set_text_variable`/`enable_dialog_choices`/`enable_dialog_choices_var`; `content.choice.pre_choose`/`dynamic_mask_setup`; `event_range_body(space_item=)` + once-first; build wiring + validate + lint; editor fields; FORMAT.md. **356 tests.** Commits `5fcaa12`(once-first) `c15dc74`(chest niceties) + F10 control-fix. Tagged `KNOWN_GOOD-s21-chest-niceties`.

**Game state:** dev engine (F6 reload + F10 reset + control-fix). Field 4003 = the chest test (revert `py tools/scroll_out/revert_deploy.py`). Debug New-Game→Alexandria warp active. The kit's content stack (rooms → cameras → walkmesh → NPCs/dialogue → gateways → encounters → events[chest-faithful] → choices[+flag-gated hide] → branching → cutscenes) is COMPLETE, real-field-grounded, and in-game-proven.

**Next options:** author a real populated demo area with the full stack; a second connected room; or the release-cleanup pass. Standing constraint: nothing public.

### 2026-06-07 — Session 22 — Ladder import: 3 shapes validated in-game + the warp-plumbing saga

**The faithful-ladder import is fully proven end-to-end — all 3 real-ladder shapes climb in real gameplay.** And the entire multi-hour "black screen" ordeal turned out to be the New-Game DEBUG WARP, never the ladder/kit/4003.

**Ladder import — productized + validated (all 3 shapes):** `eventscan.scan_ladders` extracts a ladder's zone + the VERBATIM climb function + the concurrent `STARTSEQ` helper-sequences it launches; `import` emits `[[ladder]] zone + climb=<sidecar>` (+ `.seqN.bin` sidecars); `build`/`content.ladder.inject_ladder` grafts the climb onto the player entry + a tread/action region + grafts the seqs at free slots and remaps the climb's `STARTSEQ` args. Validated in real gameplay:
- **no-`STARTSEQ`** (CPMP / Conde Petie Mtn Path) — bidirectional ✓
- **`STARTSEQ`+pitch** (Treno residence, the forward-lean) — earlier ✓
- **`STARTSEQ`-non-pitch** (GZML / Gizamaluke exit) — bidirectional ✓, and climbing up walks out the **imported gateway** into real field 704 (gateway import also proven).

**Kit fix — imported ladder zones must span BOTH ends (commit `34fa037`, 373 tests):** a faithfully-imported real `SetRegion` zone only covers the side the player normally approaches from; in a FORK the player can end up at either end → no "!" at the far end → can't climb back. Hit exactly on CPMP: climb DOWN worked, UP didn't — the bottom landing (z=-363) sat below the imported zone (z[-210,1369]). Fix: `extract` now auto-unions the real zone with the climb's `SetupJump` landing points (+150u margin) → bidirectional out of the box. New `content.ladder.climb_landings` / `widen_zone_for_climb` (+ test). `SetupJump`(0xE2) dests are ABSOLUTE world (X, −Y, Z) per the engine. GZML's zone already covered both ends (short near-vertical ladder), so it tested the seq-graft, not the zone.

**THE WARP-PLUMBING SAGA (the real lesson — every black screen this session):** New Game → black, repeatedly, on CPMP/CPMP_LAD/etc. Engine-probed it: a try/catch around `EBin.commandDefault2`'s `DoEventCode()` call logging `gExec.sid` + `_lastIP` + `fldMapNo` (+ a `MAPJUMP`/Field-warp logger in `DoEventCode`), swallowing to avoid the hard crash. Result: `map=100` — an `InvalidCastException` in **field 100 (Alexandria)**, NOT field 4003. The ladder/CPMP/4003 were correct the whole time; **4003 had never once been reached** — the warp died in field 100 every launch. Two root causes, both stale debug hacks:
1. **Field 100 (Alexandria) is a debug-hack pileup:** a dead `Field(4004)` to an UNREGISTERED field + an entrance-spawn sitting INSIDE a gateway zone that fires on spawn → `(PosObj)`/cast crash. (Confirmed: DictionaryPatch only had 4000/4002/4003; `MAPJUMP from=100 to=4004`.)
2. **Field 70 had TWO warp instructions** — an inline `Field(4000)` (entrance 0) AND an entry-3 `InitCode` `Field(100,231)`. The LIVE one was entry-3 (→ broken field 100); my first byte-patches hit the DEAD inline one, so the warp kept dragging back into Alexandria. Fix: byte-patched BOTH field-70 warps → `Field(4003)` directly, bypassing Alexandria entirely. **4003 loaded first try.**

**Reusable lessons (fold into memory):**
- When a custom field "black-screens after the warp," **probe the ACTUAL crashing field** — it may be the warp SOURCE/intermediate, not the destination. `Memoria.log` `invalidFieldMapID` is benign transition noise; an `InvalidCastException` in `DoEventCode`/`ProcessEvents` is a SCRIPT crash.
- **Engine probe pattern:** try/catch in `commandDefault2` around `DoEventCode()` logging `gExec.sid`/`_lastIP`/`fldMapNo` + swallow → pinpoints the exact crashing object/opcode without a hard crash; add a `MAPJUMP` log in `DoEventCode` to dump the field→field warp chain.
- A field can have **multiple `Field()` warp instructions** in different entries/branches — patch the LIVE one (verify via the MAPJUMP chain, not by reading the disasm alone).
- An unregistered `Field(N)` (no DictionaryPatch line) or a player **spawn placed inside a gateway zone** (fires on spawn before the player object is ready) cast-crashes the field.
- `.eb` byte-patches to the lang-identical CODE region (offset ≥ ~128, after the 84-byte name) apply at the SAME offset in all 7 languages.

**Engine state:** clean **pre-probe** DLLs restored (x64+x86; probes removed via `git checkout` of EBin.cs/EventEngine.cs/DoEventCode.cs + restoring `backups/Assembly-CSharp.dll.*.preProbe.20260607-184356`); **F6/F10 dev hotkeys kept** (UIKeyTrigger.cs). Memoria clone is probe-free.

**Carry-over / state:** debug New-Game warp = field 70 → `Field(4003)` direct (BOTH warps repointed; backups `backups/*-evt_alex1_ts_opening.eb.bytes.{preWarpFix,direct4003,entry3-4003}.*`). Field 4003 = GZML ladder test (revert `tools/scroll_out/revert_deploy.py`). **Field 100 (Alexandria) is still broken** (dead `Field(4004)` + spawn-in-gateway) — irrelevant while the warp bypasses it, but a real-playthrough wiring would need it rebuilt. Title-fade on borrowed fields (cosmetic) deferred. Standing constraint still in force: **nothing public**.

**Next options:** (a) emulate-generic position-aware bidirectional climb (#71) for forks with no real climb to copy; (b) title-fade suppression on borrowed fields; (c) rebuild the debug warp plumbing cleanly (or a real story entrance) — the field 70/100 hacks are fragile; (d) back to broader kit/content.

### 2026-06-08 — Session 22 (cont) — Navigable-ladder BOUNDARY CASES: top=gateway + re-entry-on-vine (in-game verified) + `insert_in_function`

Closed the two boundary cases of the navigable vine (ladder whose TOP exits via a gateway, and returning spawns you ON the vine). Each fix came from **studying the original (field 706 / `EVT_GIZ_TO_WORLD`)** rather than guessing — the user's repeated steer. All in-game verified; the kit gained a reusable structural-edit primitive.

**Bug 1 — the gateway "fired a battle" (the real cause of every top=gateway black-screen).** I had encoded `preload_field` as opcode **`0x2A` — which is `Battle`, not PreloadField**. So the climb's top transition emitted `Battle(5, top_field)`, using the destination FIELD ID as a **battle-scene id**: `4003`/`4002` (invalid scene) → `HonoluluBattleMain.InitBattleScene` null-ref crash (black); `100` (valid scene) → a real Dragonfly battle that killed the player. The self-loop + broken-4002 detours were the SAME `Battle` op with bad scene ids. **FF9's real PreloadField is `0xFD` (HINT), "ignored in the non-PSX versions" — a no-op on Steam**; field 70's actual warp is `Field(0x2B)` alone. Fix: removed `preload_field`; the gateway transition is `FadeFilter(6,24,…) + Wait(25) + set D8:2 + Field + TerminateEntry` (Wait(25) essential — omit it and Field fires mid-fade → black destination). A test asserts NO `0x2A` is ever emitted. Commit `4717c18`. Also added a build guard: `top_field == this field's id` is a no-op self-loop → rejected (`d9f2964`). LESSON: **verify an opcode's value against the engine tables before encoding it** — don't trust a self-set "expect".

**Bug 2 — broken-destination black-screen.** Warping the gateway to field **4002 (Vivi's Hut interior)** black-screened: 4002 is **registered** (DictionaryPatch + `EVT_HUT_INT`) but its **scene folder `FBG_N11_HUT_INT/` is gone** (a live-mod regression from the editor-test deploy incident). A registered-but-scene-missing field can't load. Warp gateways at **valid** fields (base-game, or fully-built custom). Proved the transition by pointing the top at the clean real field 706 → "i'm in the normal Gizamaluke's Grotto."

**The re-entry mechanism — studied from 706, NO warm-up timer (the key correction).** Decoded 706's player entry (14) + Main_Loop. The climb (tag 11) is invoked from TWO callers: a **base region** (action-press mount, `RunScriptSync(2,250,11)`) AND **Main_Loop** (`entry 0 tag 1`: `if (D8:2==9999) RunScriptSync(2,14,11)` then EnableMove/EnableMenu). The player **Init places you on the vine** for the re-entry entrance (`if(entrance==9999)` block, right after `DefinePlayerCharacter`: `AddCharacterAttribute(4)` + `MoveInstantXZY` + `SetPathing(0)` + climb anim) — it runs **as the player object is created, before the first render**, so the base spawn is never shown. My first attempt placed you from a *post-Init code entry* with a `Wait` → "spawn at base THEN warp up." The user: "what does the actual game use?" → **no timer; it places in the Init.** The climb's **mount-gate** (`if (selfY >= -500) jump-on-mount; else skip-to-loop`, selfY = `-worldY`) lets the SAME climb function handle base-mount (low selfY) and re-entry (placed high, selfY < −500 → skip mount → loop → climb down). Fix: splice the placement INTO the player Init (after `DefinePlayerCharacter`), run the climb from a post-Init code entry (706's Main_Loop). In-game: spawn on the vine already climbing, hold Down to climb off, control returns at the base. Commits `1d13252`,`c3da570`.

**New primitive `edit.insert_in_function`** (the reusable win): inserts bytes INTO a non-last function and **fixes the intra-entry func-table `fpos` of the later funcs** — the gap plain `insert_bytes` leaves (it only fixes the entry table, not sibling funcs). Refuses if a relative jump straddles the insert point. The jump-safe spot used: after `DefinePlayerCharacter`, before the Init's `EnableMove` tail — every tail jump AND its RETURN target are after the point, so they shift together (relative operands preserved). Verified all 7 langs disassemble cleanly post-splice; +1 fpos-fix test (33 ladder tests, 401 suite). This unlocks **faithful authorship paths** — placing logic inside the right function at the right time (as the devs do), not bolting on post-init code entries.

**Git note:** the user created branch **`infohub-catalog`** (their Info Hub feature: `catalog.py`/`_animdb_all.py`/`_modeldb.py`/`cli.py`/`test_catalog.py`, commit `4770c41` = master + 1) and a session got auto-switched onto it. My ladder work is all on **master** (`c3da570`); switched back to master, left `infohub-catalog` untouched. (The earlier "catalog test flakes" were that branch's code bleeding into the shared tree — now isolated.)

**Carry-over / state:** on `master`. Field 4003 = GZML re-entry test; debug New-Game warp = field 70 → `Field(4003, entrance 11)` (the re-entry entrance — New Game drops you on the vine). Field 100 (Alexandria) + field 4002 (hut interior scene) still broken (separate cleanups). Standing constraint: **nothing public.**

### 2026-06-08 — Session 22 (cont) — Ladder SHAPE dimension complete: slant + flexible input + multi-rung (all in-game)

Worked through the ladder research's remaining catalogued items, each studied-from-the-original then in-game-verified on the GZML borrow (New-Game→entrance-11 warp). The navigable-ladder shape dimension is now done: **vertical ✓, slant ✓, bent ✓.**

- **SLANT (X/Z linear in height) — verified.** The generator's line equation `base + (selfY−anchor)·slope/slope_den` already covered slant; we'd only ever walked vertical. A +600-X slanted vine: user confirmed "up and to the right makes sense" (ascent) + the descent drifts back along the diagonal. The kernel handles a diagonal exactly like vertical.
- **Off-walkmesh-landing lesson + build validation.** First slant test floor-dismounted at the top → landed off GZML's borrowed walkmesh (which only covers the base) → "fall into a non-navigable area." GZML's real vine top is the world-map exit, NOT a floor, so a floor-dismount there was unfaithful anyway. Fix: gateway/re-entry top (no top floor needed). Banked it: `build._validate_content_placement` now warns when a navigable ladder's `floor_landing`/`top_landing` is off the walkmesh (skipped for a gateway/worldmap top). Commit `4010b35`.
- **FLEXIBLE INPUT (`dirs` list) — verified.** Generalized the climb input to an explicit `[[mask,"up"|"down"], …]` first-match-wins list, expressing the real TRNO/UDFT binding (Up AND Left climb up; Down|Right down) the old `up_mask/down_mask/right_alias` shorthand couldn't. Back-compat byte-identical (asserted) → goldens unchanged. User confirmed all four keys. Commit `ebec08e`.
- **MULTI-RUNG (`rungs` list, bent vine) — verified.** The last literal shape. Decoded the real Cleyra ladder (`CLIR_MAP380` / `EVT_CLEYRA2_LADDER`): it IS a B_KEY navigable climb (the `0x59` is an expression token, not a standalone op — first scan missed it) with **3 `MoveInstantXZY` snaps selected by selfY band**. Recreated as: one navigable loop + a **piecewise snap** that picks the segment whose selfY band holds the target. `rungs=[[x,z,y],…]` (≥2 pts → N−1 segments) overrides bottom/top; 1-segment rungs is byte-identical to the bottom/top form (goldens safe); the re-entry spawn lands on the **bent path** (`_point_on_rungs`), not the chord. User confirmed the in-game "3-point movement" (a "^" vine: X drifts right to the mid bend then left — the piecewise reversal). Commit `22e999a`.

**New `edit.insert_in_function` primitive (earlier this session)** + the dirs/rungs work are all offline-validated (393 tests) with the golden byte-exact builds untouched. Each in-game test deployed via `tools/deploy_field.py` → field 4003 + F6.

**WORLDMAP top-action — also verified (the full top-action triad).** GZML's real vine (706 / `EVT_GIZ_TO_WORLD`) genuinely exits to the world map (a disc/progress-keyed switch over `WorldMap(9000..9012)`); our generator emits the single-target form. `top_action="worldmap"`, `top_worldmap=9000` (the default Gizamaluke→overworld entry): user climbed up → `WorldMap(9000)` → **spawned on the overworld, walkable, combat works** — cleaner than the game-owned-arrival caveat feared. (No kit change; the worldmap branch was already built.) So **all three top-actions floor/gateway/worldmap are now in-game-verified.**

**Research status — ladder catalogue essentially complete:** SHAPE dimension (vertical/slant/bent) ✓, ALL top-actions (floor/gateway/worldmap) ✓, re-entry ✓, flexible input ✓, landing validation ✓ — all in-game on GZML. Only remainders need a floor-at-*both*-ends field (CPMP/TRNO), not GZML: **two-way mount** (#5, mount from either end by approach height) + **per-end dismount anims** (#3). Test fields: `tools/scroll_out/ladtest_gzml/GZML_{SLANT,INPUT,BENT,WORLDMAP}.field.toml`.

**Carry-over / state:** on `master`, 393 tests. Field 4003 = GZML_WORLDMAP (revert `tools/scroll_out/revert_deploy.py`). Debug New-Game warp field 70 → `Field(4003, entrance 11)`. Standing constraint: **nothing public.**

### 2026-06-08 — Session 23 — Info Hub catalog + `[[npc]]` model-by-name + the F6 DEBUG MENU (merged from the `infohub-catalog` worktree)

Built on a separate `infohub-catalog` git worktree (so master's parallel ladder work was undisturbed), then **merged into `master`** (`5bc50bd`, clean auto-merge — only `build.py` overlapped and merged automatically). All offline-validated; the debug-menu engine changes are in-game-verified by the user.

**⚠ DEV HOTKEYS CHANGED — the old single-purpose F6/F10 are REPLACED by ONE tabbed F6 DEBUG MENU. Do NOT reference "F6 = reload / F10 = reset" anymore.** Press **F6** in the field → an IMGUI popup (`Ff9mkDebugMenu.cs`, toggled from `UIKeyTrigger.Update`; patch `memoria-patches/s22-debug-menu-f6.patch`, supersedes `s18`/`s21`), resolution-scaled + draggable, pauses field input while open. Tabs:
- **Warp** — *Reload field* (the old F6: re-reads the field's mod files from disk — `.eb`/`.mes`/scene) · warp to any **registered custom field** (auto-listed from `eventIDToFBGID`, id ≥ 4000) or a typed id → hop between per-branch 4003/5000/5001 slots live.
- **Move** — teleport to a typed (x,z) · **RIGHT-CLICK the field** to copy the floor (x,z) under the cursor to the system clipboard + the teleport boxes (reuses FF9's own click-to-move walkmesh math — paste straight into a `field.toml`).
- **Cheats** — booster toggles (the old F1–F4: Speed / ATB / Attack9999 / No-encounters) · full-heal party · give item (`ff9item.FF9Item_Add_Generic`) · add gil.
- **Flags** — get/set/clear a `gEventGlobal` story flag by index (matches the kit's `set_flag`: VariableType.Bit → `gEventGlobal[N>>3]` bit `N&7`) · **snapshot/restore** the whole flag state · reset-all (the old F10).
- **Time** — 0.25–4× time-scale (slow-mo/fast for inspecting cutscenes/movement).

Force-encounter is the one deferred item (starting a battle from arbitrary field state is risky + untestable). **Dev loop unchanged:** edit → `tools/deploy_field.py <toml> [--id N]` → **F6 → Warp/Reload** (only the first deploy of a session needs a relaunch; an engine-DLL rebuild needs a relaunch).

**`tools/deploy_field.py --id N`** — per-branch custom-field SLOTS (e.g. 5000s) so two worktrees keep separate live test fields in the one shared install (per-id revert; default 4003 stays the New-Game auto-warp target); reach any via the F6 menu's Warp.

**Info Hub reference catalogs** (`ff9mapkit/catalog.py` + baked `_modeldb`/`_animdb_all`/`_scenedb`, identifier-only from Memoria source, provenance-clean): browse models / animations / battle scenes by name; the **model→animation join** (`animations_for_model`) via the (group, token) name share — engine-verified that the engine resolves an anim id → NAME → clip (`AnimationDB.GetValue` → `AddAnimWithAnimatioName`), so the catalog's min-id-per-name pick is SOUND. CLI `ff9mapkit models|scenes|catalog`. Hardened with offline lock-in tests (the hub join == the build's own resolver for all 8 playables; every field-form model has a non-empty join; min-id determinism) + a PROVENANCE.md table.

**`[[npc]] model` accepts a GEO name** (`"GEO_NPC_F0_BAR"`, resolved via the catalog) as well as a raw id; `validate()` errors on an unresolvable model NAME (a clean message instead of a build crash), `lint_logic()` warns on an unknown raw model id / `[[npc]] anims` id / numeric cutscene `animation` id. Additive — raw-int + preset paths byte-identical, so golden builds unchanged. (FORMAT.md fixed: `animset` is the model's HEAD HEIGHT, not an animation set; `anims` = the gestures, list via `ff9mapkit models <name>`.)

**Tests:** kit 148 offline + 20 catalog/npc green on the merged tree. Memory `project-ff9-eb-script-tooling` updated — its F6 section now documents the debug menu and supersedes the old hotkey note.

**Carry-over / state:** on `master` (`5bc50bd`); `infohub-catalog` worktree synced to it. The F6 debug menu + Attack9999-auto-on are the DEV engine only (the shipped mod is engine-independent). Field 4003 = the shared test slot; New-Game warp unchanged from the ladder session. Standing constraint: **nothing public.**
