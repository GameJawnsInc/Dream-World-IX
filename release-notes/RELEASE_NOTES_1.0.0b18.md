# Dream World IX 1.0.0b18 — a third world map, dungeons drawn by hand, and summons of your own

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* content — and faithfully forking the real game — for the [Memoria engine](https://github.com/Albeoris/Memoria) (Steam/GOG FF9). This is the largest release the project has shipped: nearly 1,600 commits over 18 days, with an 8,200-test suite running green nightly. The headlines: the engine can now host a **genuinely new third world map** that is neither of FF9's two overworlds; you can **draw a multi-room dungeon by hand** — floors traced on artwork, rooms sketched on a grid — and walk it in-game minutes later; a **custom summon** pipeline went from research to cast-proven (recolour a real eidolon, or build your own from scratch); a **Fort Condor-style siege minigame** became one declarable TOML block; forks can finally **boot mid-story** instead of at scenario zero; and every one of FF9's ~9,700 event scripts now **round-trips through editable source code**.

> Warp onto a world map that never existed, sail your own ferry line between islands you minted, sketch a dungeon over your own photographs and hand a friend the mod, teach the save moogle's world a new legend in the Folklore codex, wire a countdown siege with hireable defenders, repaint Shiva magenta and cast her — then print your save's completion report from the command line.

**Upgrading? Three things behave differently:**
- **The in-game debug menu moved from F6 to `~`** (tilde/backquote) — stock Memoria already binds F6 to its LvMax cheat, and the old intercept was swallowing it. The menu is not gone; it's on the key next to `1`.
- **Co-op's wire protocol bumped (v10 → v11): a b17 engine and a b18 engine deliberately refuse to pair.** Both machines must upgrade together. Co-op stays OFF unless `[Netsync]` is configured.
- **Background-art edits now hot-reload** (change a PNG, `~` → Reload field). This *removes* b17's overlay-texture cache — its advertised "smoother fades" were never confirmed, and the cache was serving stale art for the whole session. If a fade regression appears, please report it.

## Contents

- [A third world map (experimental)](#-a-genuinely-new-third-world-map-experimental)
- [The Southern Ring — a composed overworld, with ferries](#-the-southern-ring--a-whole-overworld-composed-from-one-file)
- [Draw a dungeon by hand](#-draw-a-dungeon-by-hand)
- [Cutscene authoring & richer dialogue](#-cutscene-authoring--richer-dialogue)
- [Boot a fork mid-story](#-boot-a-fork-mid-story)
- [Custom summons](#-custom-summons-recolour-the-real-ones-or-cast-your-own)
- [Siege battles, unit AI & living HUDs](#-siege-battles-unit-ai--living-huds)
- [The completion Journal](#-the-completion-journal)
- [The Folklore codex](#-the-folklore-codex-engine-bundle)
- [Overworld tooling: faster, safer, honest](#-overworld-tooling-faster-safer-honest)
- [Field scripting & fork fidelity](#-field-scripting--fork-fidelity)
- [Workspace GUI](#-workspace-gui)
- [Co-op, honestly](#-co-op-honestly-experimental)
- [Fixes & hardening](#-fixes--hardening)
- [Engine bundle](#engine-bundle)
- [Getting started](#getting-started) · [Provenance](#provenance) · [License](#license)

## What's new since v1.0.0b17

### 🌍 A genuinely new third world map *(experimental)*

> ⚠️ **Experimental** — the full loop is in-game proven (walk a field, step out onto the new world, walk back in), but growing new landmasses is still an active defect-and-fix craft: expect an occasional visible seam or stretched water at a freshly grown coastline, and expect the vocabulary to keep moving.

FF9 ships exactly two overworld asset trees (disc 1 and disc 4). The b18 engine bundle can now host a **third**: any world id in a reserved band (9013–9099) gets a complete synthetic world disc minted at runtime, with its own terrain/texture namespace so nothing it does can ever touch the real world's files.

- **Two starting modes** — a **blank** world (true all-sea canvas: build a continent from nothing with the `world-*` verbs) or a **clone** of the stock world (reshape the real map non-destructively in a sandbox). Stock's coordinate-keyed landmarks (the Water Shrine, the Daguerreo bridge, the quicksand cells) are suppressed on a blank world so your continent doesn't inherit them; Mist is off by default on the new world.
- **Registered like everything else** — a new `WorldScene <id> <name>` DictionaryPatch directive, exactly parallel to `FieldScene`/`BattleScene`. Every piece is inert until you deliberately arm it: no `WorldScene` line, no ids in the band, no change to a normal game.
- **A real place already lives there** — the project's proving ground is world 9013: a two-biome landmass with a desert junction, mountain carries, and a working field↔world entrance loop ("!"-confirm on the way out, deterministic arrival on the way back).
- *In-game proven (2026-07-30 → 2026-08-05)* — clone mode, the mist toggle, and the full 9013 round trip ("! showed and warped me back, the loop works"); the latest landmass-growth round passed with two filed defects, whose fix is in this release but awaits its own playtest.

### ⛵ The Southern Ring — a whole overworld composed from one file

The overworld verbs stopped being one-off commands and became a **composition system** — and the proof is a complete, playable region: a hub town, a ferry hall, four quays, islands, forest encounters, and a boat you can sail anywhere and land.

- **`world-fuse` runs whole layouts** — one TOML can now declare `[[island]]`, `[[mountain]]`, `[[forest]]`, `[[hill]]`, `[[coastnav]]` and `[[rim_retile]]` tables alongside placements, executed in a fixed lawful order regardless of where they appear in the file. Re-composing the same file writes **zero changed bytes** — a `world_manifest.json` records every file's checksum and refuses to clobber anything that drifted (`--allow-overwrite` to override).
- **A real ferry line** — `[[ferry]]` / `[[ferry.destination]]` give a moored ship a working departure menu; `depart_code` arms symmetric origin-port departures, and the scene ladder stages the full voyage: boarding, a scripted camera flight, arrival at the destination quay, with the minimap arriving in the correct state. The boat itself supports wake, land-anywhere, and a boarding standoff.
- **Encounters on your land** — `world-encounters` stamps real encounter tables onto composed terrain, and an authored table can now legitimately have holes: unlisted terrain means *no battle*, instead of silently rolling the zone's last row.
- *In-game proven (through 2026-08-01)* — the Ring's entire ratified board closed in-game: hub, hall, ferry, pressure plates, forest encounters, and all five boat behaviors, each round owner-confirmed; the scene-ladder rungs (rig cinema, the voyage, origin-port departures) all closed with owner quotes.

### 🏰 Draw a dungeon by hand

The click-authoring arc grew into a full visual pipeline: trace a floor onto any image, click content onto real FF9 artwork, and now **sketch a whole multi-room dungeon** and get it wired, gated, and deployable.

- **The Floorplan tab** — draw rooms on a grid (rectangles or not), snap walls and corners so rooms genuinely share them, and compose: every room becomes a field, doors become gateways, and the whole dungeon deploys as one unit. Recomposing **merges** — NPCs, doors, layers and art you added to a room survive a layout change instead of being overwritten. Rooms too wide for one screen scroll; rooms too big to render are refused with the limit named. A live validity gate runs as you draw (~0.6s, down from ~17s).
- **The Place tab** — click NPCs, props, and trigger regions directly onto a field's own background art, now including fields you made yourself (not just forks of real ones). Trigger regions draw as shapes on the art. *Placement onto forked real rooms is playtest-confirmed;* ⚠ placing into a *floorplan-composed* room is offline-verified only so far, and the composer's automatic per-room camera fit awaits its first playtest — check framing on a wide room.
- **The Trace tab / `image-field`** — hand-trace a floor polygon over any image (your own photo included) and get a walkable field; foreground cut-outs let an actor pass *behind* parts of the picture. The projection math is in-game proven on a real photograph; the verb still labels itself `[EXPERIMENTAL]` because the end-to-end flow has rough edges — expect to correct the traced walkmesh by hand, and export cut-outs at the background's own frame/aspect (the exact depth flip-line hasn't been read in-game yet).
- *In-game proven (2026-07-29 → 2026-07-31)* — the owner drew, composed, deployed and walked a multi-room dungeon ("Step 7 passes"); prop + NPC placement on a verbatim fork confirmed; the occluder mechanism confirmed deployed and occluding.

### 🎬 Cutscene authoring & richer dialogue

- **A dedicated Cutscene tab** *(new, and newer than its coverage)* — the Workspace's Author rail gains a full cutscene surface: a scene rail, a step ladder (the accordion — one window, playtest-shaped), a stage view, and a beat storyboard. It went through real GUI playtest rounds and carries ~105 tests, but no cutscene authored end-to-end through the tab has been confirmed in-game yet — check the written TOML before you build on it. (The compiler underneath is the *strongest* part of the lane: cutscenes authored in `field.toml` compile and play correctly, and `turn` steps now animate the stock way instead of snapping.)
- **Several text windows at once** — dialogue can open multiple windows simultaneously, synchronize text to cutscene beats, and colour individual words with FF9's own palette codes; all idioms censused from stock fields, not invented.
- **`[[text_table]]` — a field's own string banks** — declare named row banks and pull a row into any line with `[TEXT=<name>,slot]`; the build allocates real text ids and refuses an unknown name at build time. This is how a line can say a Treasure-Hunter rank letter or a hunt winner's name.
- **NPCs finally face where you tell them** — `[[npc]] face` was documented but never wired: every authored NPC shipped facing south. Fixed, with the layout probe now rendering facing arrows so you catch it offline.

### 📖 Boot a fork mid-story

The narrative-state engine's first proven rungs shipped: a forked field no longer has to start at scenario zero.

- **`story-seed <field> --beat <N|name>`** — ask the kit what story state a field needs at a given beat and it writes the `[startup]` (scenario, flags, words) and `[party]` blocks for you; `--beats` lists a field's known beats. Derived from the game's own dispatch data, not hand-curated guesses.
- **The proof played a whole morning** — New Game → hub pick → a derived mid-story boot played the entire Dali morning sequence and handed off to the real game at the zone edge.
- *In-game proven (2026-08-03)* — all three playtest slots owner-confirmed, plus a calibration playtest. The deeper beat model (per-beat NPC rosters everywhere, full timeline replay) is deliberately shelved for now — this release ships the proven core.

### 🔥 Custom summons: recolour the real ones, or cast your own

A research arc that closed spectacularly: the kit can now edit a stock eidolon's cinematic **in place**, and the from-scratch pipeline cast a homemade summon in a real battle.

- **`summon-reskin` / `summon-rescore`** — recolour a summon's palette, repaint its texels (`export-art` hands you the true composed art; `[[reskin.texel]]` puts your paint-over back), retime its sequence, or reframe its camera — all against the real `.seq`/SFX substrate, no engine rebuild. *Cast-proven across the whole tier:* magenta Shiva on screen, the texel brand reading hard-edged on both wings, seven owner casts on the scenery lane.
- **The custom-summon ladder** — `summon-export` / `summon-rig-ref` / `summon-import` / `summon-deploy` / `summon-seq-lint`: your own creature model, sequence, effects and audio, cast in battle. *Rungs 1–7 all in-game proven in one session (2026-07-21);* the last two polish rungs are paused at the owner's call.
- **`[[summon]]` — the declarative transplant** *(experimental)* — swap your own model onto a stock summon's cast as ordinary TOML. The underlying transplant was proven by hand; this productized block has not itself been cast in-game yet, and its default hybrid lane (posing your model from the native summon's live skeleton, engine patch s58) has **never been seen running** — it ships inert and self-disables on first fault. Treat it as the frontier it is.
- **For summon modders: the probe suite** — the engine bundle carries an instrumentation family (off by default, `[SfxProbe] Enabled`) that dumps how a stock summon actually renders: per-frame camera matrices, the creature's real transforms, the raw primitive stream, UV/texel ranges. It's the tooling that made all of the above tractable, and it ships so you can use it too.

### ⚔️ Siege battles, unit AI & living HUDs

- **`[siege]` — a tower-defense minigame in one block** — lanes, waves on a real countdown, hireable defenders with prices and a buy button (`[[behavior.pool]]`), real FF9 battles fired by unit AI, win/lose theater. Ships as a worked example in `examples/siege/`. *Owner-ratified in-game ("all good, siege plays the same after relaunch"), including surviving a relaunch.*
- **Behavior trees grew up** — `[behavior] timer` starts FF9's own on-screen countdown and `time_below`/`time_above` branch AI on it; a unit action can start a genuine battle; `npcs = [...]` class rows stamp one tree onto many actors; pooled units hire and respawn. The v2 substrate (`[[behavior.scan]]` group/nearest queries) is in-game proven on its announce ladder, ⚠ with the rung-1 `group`/`engage` layer bench-measured rather than playtested, and one known quirk: a dead unit's position mirror freezes (it keeps being counted).
- **The Workspace Behavior tab** — archetype stamp cards, a "never selects — row N wins first" dead-branch chip, and **▶ Simulate**: an offline tick-stepper that runs your tree without the game.
- **Live numbers on a field with no engine patch** — `[[qte]]` reaction rounds, `[[numeric_input]]` steppers, `[[gauge]]` bars, and `[[behavior.hud]]` strips (gil, timer, HP) — built from stock text-window machinery, because FF9 has no number opcode at all.
- **The turbo fix** — FF9's turbo-dialog key (F9, on by default, no indicator) was silently auto-answering all of the above: QTEs resolved themselves on frame 1, steppers submitted their starting value. Every minted window in those lanes now suppresses the synthetic press. *All three lanes owner-confirmed via in-game F9 A/B.* Known cost: while a HUD strip is on screen, dialogue turbo-skip in that field is mostly off.

### 📜 The completion Journal

- **`journal report`** reads a real save and prints 48 completion rows — story beat, Treasure Hunter points *and rank*, chocographs found and dug, beaches, Stellazzio, ragtime, cards and collector level, Mognet delivery state, gil, key items, play time. `journal diff` shows what one session accomplished. Every row cites the engine source its read was derived from; denominators come from the engine's own achievement targets, never a wiki.
- **The in-game dashboard** — the same catalog drives a seven-page lectern dashboard on a field, live numbers, running on **stock** Memoria. *Owner-confirmed in-game on the bench field.* ⚠ The two newest touches — live *string* rows (the rank letter, the hunt winner's name) and hiding rows that lack a live read — are built and gated but not yet playtested.
- Deliberately not shipped: a chest counter. FF9 keeps no per-chest registry at any price — the Journal refuses to fake one.

### 📚 The Folklore codex *(engine bundle)*

A new **Folklore** row in FF9's main menu opens a real codex: a key-item-style list with category paging and the stock "New!" bang, `???` for locked entries — and a detail pane whose top window renders a **live, animated 3D creature**, idling and slowly rotating on a turntable, auto-framed to its own motion volume. Entries unlock as you play; content is authored entirely DLL-free through the `[[folklore]]` block. Off by default (`Memoria.ini [Folklore] Enabled=1`), bit-identical vanilla when off. *The most playtest-hardened engine feature in the release — 16+ owner-confirmed rounds, which along the way fixed a stock Memoria menu bug.*

### 🗺️ Overworld tooling: faster, safer, honest

The overworld arsenal matured from frontier verbs into an instrumented, guard-railed system.

- **The relaunch tax was self-imposed — and is gone.** Geometry edits apply via a scene reload (`~` → World → Reload overworld, or step through any field): deploy → reload → look, about a second. All geometry verbs now print the honest apply note; relaunch is reserved for registration lines and DLL changes. `docs/OVERWORLD_RECIPES.md` collects the proven command sequences.
- **`world-render`** — rasterize your deployed overworld to PNGs the way the engine draws it (unlit, nearest-filtered, game-eye culling), from auto-derived vantage rigs — see your island without launching the game. Byte-faithful: the committed bench cameras render pixel-identical.
- **A deploy ledger and an ownership rule** — every world write logs one JSON line (`world-ledger` reads it back, `--drift` audits), parks a timestamped backup, and the kit **refuses to overwrite bytes it didn't write** — protection for anyone running multiple mods or sessions against one install.
- **New guardrails, each minted by a real failure** — `world-terrain` refuses one-way slopes the player can descend but never climb out of (the soft-lock pit); relief and island builds census for a second walkable floor stacked under the ground (the walk-under-the-lawn class); transplant builds run a junction differential and an orphan-tile census with an auto-redress option; coast morphs now work on desert/brush tops and shallow-fronted shores instead of refusing them.
- **Read-only instruments** — `world-donors` catalogs carriable donor terrain (with the falsified-lanes banner carrying research verdicts to the call site so you don't re-walk dead ends); `world-readback` decodes what's actually deployed; `world-locate` now names places from the engine's real dispatch data (Alexandria's tiles no longer file under Qu's Marsh).
- *In-game proven continuously through the arc* — the hot-reload loop, the Ring and Path-D geometry this tooling built, and the guardrail thresholds re-derived from the engine's own walk step.

### 🧵 Field scripting & fork fidelity

- **Every event script is now editable source** — `eb-src` decompiles any of FF9's ~9,700 field/battle/world event binaries to annotated `.ebs` source; `eb-asm` assembles it back **byte-exact**, and `--against` splices an edit into a donor script. A standing gate round-trips the entire corpus. *In-game proven: a source-edited chest gave the edited reward.*
- **Forks carry more of the donor's truth** — a fatal class fixed (donor rumble/preload data resolving under the fork's minted name hung cutscene actors mid-scene), plus 73 more hardcoded engine gates swept for opening-campaign donors: compulsory ATEs, SPS visibility, the telescope, minigame and achievement gates.
- **Better authoring honesty** — `lint` catches misspelled keys the build silently ignores; `[encounter] scene` names are validated at lint time instead of dying at build; the `received` event shows the real item-get box; ladders, jumps and moving platforms keep tightening against stock bytes.
- **`ff9mapkit deploy`** — install and revert one authored field straight from the packaged kit, no cloned repo needed, with a generated per-id revert script.

### 🖥️ Workspace GUI

- **Preview an animation before you attach it** — the Models tab lists every clip a model can play and plays it (scrubber, frame counter); NPC movement clips, prop poses and cutscene animation steps pick from lists instead of raw ids.
- **The Floorplan, Place, Trace, Behavior and Cutscene tabs** are covered in their sections above — collectively the app's biggest expansion yet.
- **Dozens of interaction fixes** from playtested polish rounds: drags that survive a background check landing mid-gesture, shared walls that stay shared when a corner moves, an Info Hub help badge that renders at 150% text size, GUI-minted defaults that are real or loudly invalid, and the form editor no longer stricter than the format it edits.

### 🎮 Co-op, honestly *(experimental)*

Co-op keeps its b17 label — experimental — and this release both **proves more of it** and is candid about the rest.

- **Newly two-machine proven** — a following guest now travels through doors *with* the host (the host announces its field transition instead of the guest chasing a position broadcast), holds still and watches dialogue scenes from the host's spot, and is blocked from chests, NPC talks, menus and card games while following; a ~2–3s relay hiccup no longer tears the session down or despawns the ghost; battle exits stopped crashing; play-style edits keep the live session.
- **Built but NOT yet proven — and not in this bundle** — host-driven dialogue/choice **lockstep** (each side still advances its own text windows; the lockstep round is written and reviewed but has never run, and its engine patch is deliberately held out of the b18 bundle until it proves).
- **Known rough edges** — automatic teleport-to-host failed its acceptance test and ships **off** (use F11, which is proven); the held-L3 gamepad teleport has never been tried on a real pad; the Workspace Co-op tab has never driven a real session end-to-end (the CLI path has — fall back to `coop host`/`coop join` if the GUI won't pair).
- **Both machines must run the b18 bundle** — the wire protocol bumped and mixed versions refuse to pair, by design.

### 🔧 Fixes & hardening

An unusually broad fix load beyond what's called out above, condensed:

- **Timed battles no longer end the instant they start** when a countdown reaches zero during the ending theater; a battle-return could double-charge a defeat; several `[siege]` economy edge cases closed.
- **The debug menu's Flags tab stopped calling a save-corrupting band "safe"** — its labels now match the kit's real flag map (the safe band starts at 8712; 8512–8711 is stock Mognet payload that ordinary play overwrites), and the treasure-hunter readout shows the real H..S rank.
- **The nightly test gate grew a skip ceiling** — a green run silently skipping a whole test family now fails the ledger instead of reading as healthy; the world-mesh writers refuse a topology divergence at the write seam; four Hypothesis property suites joined the mesh editor.
- **Machine-state leaks scrubbed from committed artifacts** — harvested GUI inventories now pin their environment-dependent labels so another machine's deploy count can't masquerade as a UI change.
- **Provenance hardening** — the gate that keeps Square-Enix bytes out of the repo grew a world chapter and an atlas-laundering guard; templates still regenerate only from your own install.

## Engine bundle

**The engine bundle is REBUILT this release** — `dwix-custom-memoria-1.0.0b18.zip`, a from-source build of the full patch stack on the same pinned Memoria base. What's new since b17's bundle:

- **The Folklore codex** (menu + live portrait rig) and **the third-world substrate** (the `WorldScene` directive, the sentinel disc, clone/blank modes).
- **The debug menu on `~`** with wider warp reach, vehicle physics rows, and corrected flag-band labels.
- **Co-op field-follow + link reliability** (wire v11 — see the co-op section's pairing rule).
- **Four overworld black-screen/dead-script classes closed** — minted-vehicle constructor crashes, missing-anim script kills, the cargo-ship flight circling forever, camera rigs teleporting the player; plus honest encounter-table holes and the degenerate-spawn fallback moved off a sea coordinate onto verified walkable land (the Dali plain).
- **Fork-fidelity gates** for donor rumble data and 73 more hardcoded engine sites.
- **The summon probe suite** (`[SfxProbe]`, off by default) and the inert experimental summon hybrid drive (`[SfxHybrid]`, off, unproven).
- **Removed: the b17 overlay-texture cache (s35)** — see the upgrade notes at the top; art edits hot-reload now.
- One deliberate change to vanilla behavior: 22 stray stock tiles (a censused, map-wide-unique set) become encounter-silent under the encounter-table-hole rule.

**Do you need it?** Same rule as ever: a **novel** field runs on **stock** Memoria — save points, Mognet, death rules, behavior trees, the HUD lanes, the Journal dashboard, the GUI and the Blender add-on all need no engine patches. A **forked** field, the overworld verbs, co-op, Folklore, and the third world need the bundle. The bundle is reproducible by anyone from `memoria-patches/` (that folder's README is the per-patch status map; [ENGINE.md](https://github.com/GameJawnsInc/Dream-World-IX/blob/master/ff9mapkit/docs/ENGINE.md) has the build how-to).

## Getting started

- **Windows:** grab the installer `.exe` from the release assets — it bootstraps everything, and can optionally install the engine patches (backed-up, version-aware).
- **From PyPI:** `uv tool install "ff9mapkit[gui,assets,save]"` then `ff9mapkit setup` (detects your FF9 install, saves config, extracts base templates, and reports Memoria status).
- **Already installed?** `uv tool upgrade ff9mapkit`.
- Full walkthrough, prerequisites, and the CLI reference: [SETUP.md](../SETUP.md). The Blender add-on is at **0.9.29**.

## Provenance

Dream World IX ships **NO** FINAL FANTASY IX game data. It operates only on a copy of the game **you** already own, reading and patching your local install at build time. Base templates are regenerated from your own install via `ff9mapkit extract-templates`; no Square-Enix bytes are distributed. This is an unofficial, fan-made toolkit and is **not affiliated with, endorsed by, or associated with Square Enix**.

## License

Dream World IX / `ff9mapkit` is released under the **MIT License** (© 2026 GameJawnsInc). The bundled engine patches modify [Memoria](https://github.com/Albeoris/Memoria), which is likewise MIT-licensed (© Albeoris).
