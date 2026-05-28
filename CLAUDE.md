# CLAUDE.md — FF9 Custom Map Mod (Memoria Engine)

> This file is read automatically at the start of every Claude Code session.
> Read it fully before doing anything. Update the **Session Log** at the end of
> every session. Treat the **Hard Constraints** as non-negotiable.

---

## 1. Project goal

Add a new, playable field ("room") to *Final Fantasy IX* (Steam) using the
**Memoria Engine**, then wire it into the game with working entrances/exits,
NPCs, dialogue, and at least one encounter.

**Chosen strategy: REPURPOSE, don't mint.** We take an existing field the game
doesn't need, gut its event script, and rebuild it as our new room. This avoids
two unsolved problems: registering a brand-new field ID, and authoring a
walkmesh from scratch to match new art. Do **not** attempt a from-scratch field
ID unless explicitly told to.

Working target field (the throwaway we repurpose): **field `1357` — `L. Castle/Hangar`** (chosen in Session 0). Zero `Field()`/`PreloadField()` cross-refs in any other field script, smallest payload of all 817 fields (4.7 KB), already has Zidane init wired up, and no NPCs/regions/exits of its own to gut. Tradeoff accepted: gutting it will break the Lindblum Castle hangar cutscene that uses it (the only known consumer, via C# code — see `Memoria/Assembly-CSharp/Global/Field/Map/NarrowMapList.cs:487`).

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
