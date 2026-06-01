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
