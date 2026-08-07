# What can I do?

Every card below is one thing the toolkit can put in your mod: what it gives you, the couple of
steps that try it, and where to go deeper. All of it is in-game proven. Browse the whole list, or
press **Shuffle** for a random card — again for another.

<p class="wcid-bar">
<button id="wcid-shuffle" type="button">Shuffle — show me one</button>
<button id="wcid-all" type="button" hidden>Show the whole list</button>
</p>

The exhaustive capability inventory, subsystem by subsystem, is
[FEATURES.md](ff9mapkit/docs/FEATURES.md); the guided path is
[the core track](ff9mapkit/docs/tutorials/README.md) (terminal-native:
[Track C](ff9mapkit/docs/tutorials/c1-cli-fork-edit-deploy.md)).

## Fork a real FF9 room

**You get:** any of the game's ~674 screens as an editable project of your own — art, walkable
floor, and camera carried faithfully, running under your own field id.

**Try it:** Workspace → **Assets ▸ Import** → **Suggest a test room…** → **Import field**, then
**Deploy** and warp to it in-game (`~` → Warp to field).

**Go deeper:** [S1 — Fork and deploy a field](ff9mapkit/docs/tutorials/s1-fork-and-deploy.md).

## Put a talking NPC anywhere

**You get:** your own character standing in the room, speaking your line in FF9's real dialogue
window — with the wrap previewed before the game ever shows it.

**Try it:** Editor → **NPCs** → add an entry (name, model preset, dialogue, position) → **F9** →
`~` → Reload field.

**Go deeper:** [S2 — Add an NPC and dialogue](ff9mapkit/docs/tutorials/s2-add-an-npc.md).

## Walk-through doors between your rooms

**You get:** two (or twenty) of your rooms connected both ways — walk into the doorway zone,
fade, arrive in the other room.

**Try it:** Editor → **Gateways** → destination id + a four-corner zone at the doorway; mirror
one back.

**Go deeper:** [S3 — Connect two fields with gateways](ff9mapkit/docs/tutorials/s3-gateways.md).

## A chest that stays looted

**You get:** save-persistent story state — a chest opens once and stays open across saves, and
NPCs, doors, or events can appear or unlock because of it.

**Try it:** Editor → **Chest** (position, reward, opened-flag) → gate an NPC's
**Appears when flag set** on the same flag.

**Go deeper:** [S4 — Story flags](ff9mapkit/docs/tutorials/s4-story-flags.md).

## A cutscene that plays once

**You get:** ordered scene steps — dialogue, pauses, actors walking and turning — with player
control locked while they run, guarded by an automatic play-once flag.

**Try it:** the **Cutscene** tab → **Add a scene** → a few Say/wait steps → deploy and walk in.

**Go deeper:** [S5 — A cutscene and music](ff9mapkit/docs/tutorials/s5-cutscene-and-music.md).

## Your own soundtrack

**You get:** any FF9 track as a field's BGM — or a custom audio file of yours, transcoded and
minted into the mod as a new looping song.

**Try it:** Editor → **Music** → pick a song id (Browse… lists them by name), or point
**File (custom track)** at a wav/mp3/ogg.

**Go deeper:** [S5 §2](ff9mapkit/docs/tutorials/s5-cutscene-and-music.md#2-field-music) ·
[custom music & SFX](ff9mapkit/docs/FEATURES.md#audio--video).

## Random battles, your pick

**You get:** encounters in your field against any of the game's battle pools, at a frequency you
set — with the after-battle return handled for you.

**Try it:** Editor → **Encounter** → a battle scene (`BSC_EF_R007` is the weakest) + a
frequency → deploy, walk, fight.

**Go deeper:** [S6 — Random encounters](ff9mapkit/docs/tutorials/s6-encounters.md).

## Ship your mod as a zip

**You get:** a campaign — your rooms as one unit, New Game landing in it — packaged as a plain
zip a friend drops into their FF9 install, no toolkit on their machine.

**Try it:** **Campaign → New Campaign…** → add your fields → **Point New Game here** →
**Package (zip)…**.

**Go deeper:** [S7 — Package a campaign](ff9mapkit/docs/tutorials/s7-package-a-campaign.md).

## A real save point

**You get:** the genuine moogle save menu — Save, Tent, Mognet, Mog Shop — in your field, with
save-and-reload proven to work.

**Try it:** add a `[[savepoint]]` zone in the Editor or the TOML; deploy; step on the "!" spot.

**Go deeper:** [SAVEPOINT.md](ff9mapkit/docs/SAVEPOINT.md).

## Your moogle joins Mognet

**You get:** your save moogle as a real identity in FF9's letter network — it sends letters,
receives them, and the rest of the world's moogles know it exists.

**Try it:** add a `[savepoint.mognet]` table (name + letters) to a save point.

**Go deeper:** [SAVEPOINT.md](ff9mapkit/docs/SAVEPOINT.md).

## Branching dialogue choices

**You get:** a choice menu on an NPC or a floor zone — each option with its own reply and
item/gil/story-flag effects, so conversations can matter.

**Try it:** add a `[[choice]]` block naming the options and their effects; deploy and talk.

**Go deeper:** [DIALOGUE.md](ff9mapkit/docs/DIALOGUE.md) ·
[`FORMAT.md`](ff9mapkit/docs/FORMAT.md).

## NPCs that live their own lives

**You get:** patrols, work shifts, chases, alarms, fleeing, mutual combat — designer behavior
trees compiled to pure field bytecode, no engine changes.

**Try it:** add a `[behavior]` block to an NPC, then:

```bash
ff9mapkit behavior lint myroom\MYROOM.field.toml
```

**Go deeper:** [BEHAVIOR.md](ff9mapkit/docs/BEHAVIOR.md).

## A 13th playable character

**You get:** a genuinely new party member alongside all twelve canon characters — own name,
stats, battle model, and command menu; recruited in-game and save-persistent. Zero engine
changes.

**Try it:** one `[[playable]]` block (name, borrow, recruit) → deploy → relaunch → New Game.

**Go deeper:** [Tutorial 15 — a new playable character](ff9mapkit/docs/tutorials/15-playable-character.md).

## Reshape any character model

**You get:** every FF9 model round-trippable through Blender — mesh, skeleton, textures,
animations — and back into the game as a loose override or a new minted id.

**Try it:**

```bash
ff9mapkit model-gltf GEO_MAIN_B0_006 --out vivi.glb
```

Edit in Blender, then `model-import` it back.

**Go deeper:** [Tutorial 10 — Edit a character model](ff9mapkit/docs/tutorials/10-custom-model.md).

## A creature that never existed

**You get:** an original mesh, rig, and animation set on a freshly minted model id, placed in a
field as an NPC — built from procedural Python or Blender, no donor model.

**Try it:** run tutorial 12's worked script — it builds one end to end.

**Go deeper:** [Tutorial 12 — Create a creature from scratch](ff9mapkit/docs/tutorials/12-creature-from-scratch.md).

## Recolour a summon's whole cinematic

**You get:** a stock summon's palette — creature and scenery both — and its camera pose
re-authored in place: same bytes everywhere else, shipped as a reversible mod override.

**Try it:** `summon-reskin` (colors) and `summon-rescore` (camera), each from a small spec toml.

**Go deeper:** [Tutorial 14 — Recolour and reframe a stock summon](ff9mapkit/docs/tutorials/14-summon-reskin-rescore.md).

## Your model on a summon's bones

**You get:** a custom creature wearing a stock summon's real skeleton, motion, and cinematic
camera — your model cast as an eidolon.

**Try it:** the `summon-export` → Blender → `summon-import` round-trip.

**Go deeper:** [Tutorial 11 — Transplant a model onto a summon](ff9mapkit/docs/tutorials/11-summon-transplant.md).

## New land on the world map

**You get:** whole new islands and continents on FF9's overworld — real coastline pieces fused
into an archipelago, walkable, drawn on the in-game map, iterated with a one-second reload.

**Try it:** deploy the shipped archipelago layout and teleport to it.

**Go deeper:** [Tutorial 16 — A custom continent](ff9mapkit/docs/tutorials/16-custom-continent.md).

## A custom battle arena

**You get:** a real 3D battle background forked to an editable FBX — retexture or reshape it in
Blender and fight in the result, on the stock engine.

**Try it:** `battle-import` a scene, edit, `battle-build`, fight.

**Go deeper:** [Tutorial 09 — Custom battle background](ff9mapkit/docs/tutorials/09-battle-background.md).

## Rebalance the game in four lines

**You get:** declarative difficulty — enemy scaling, damage multipliers by side, second-wind
death rules, the low-HP threshold — each a small TOML table, flag-gateable for an in-game
"hard mode" switch.

**Try it:** add `[difficulty]` or `[rebalance]` to a field and fight.

**Go deeper:** [SCRIPTS_DLL.md](ff9mapkit/docs/SCRIPTS_DLL.md).

## Invent a battle formula

**You get:** damage math FF9 never shipped — drain attacks, %-max-HP hits, or arbitrary C# — as
a mod-owned scripts DLL, with no engine rebuild.

**Try it:** give a custom ability `script = { template = "drain_hp" }` and cast it.

**Go deeper:** [SCRIPTS_DLL.md](ff9mapkit/docs/SCRIPTS_DLL.md).

## Play it with a friend

**You get:** two-player co-op — each player walks the same field and sees the other in real
time, with battle slots grantable to the guest. Experimental, and each save stays each
player's own.

**Try it:**

```bash
ff9mapkit coop host
```

The friend runs `coop join` with the printed session code.

**Go deeper:** [FEATURES.md §Multiplayer](ff9mapkit/docs/FEATURES.md#multiplayer-experimental).

## A field from a picture you painted

**You get:** your own painted background as a playable field — camera-matched, depth-layered,
with a walkable floor traced over the art.

**Try it:** paint (or pick) an image, trace the floor, let the kit solve the camera.

**Go deeper:** [Tutorial 03 — Original-art field](ff9mapkit/docs/tutorials/03-original-art-field.md).

## Fork a whole region of the game

**You get:** a connected slice of real FF9 — a town, a dungeon, a story arc — imported as one
campaign, every room and door intact.

**Try it:**

```bash
ff9mapkit import-chain <door-field> --whole-zone
```

**Go deeper:** [Tutorial 04 — Fork a region into a campaign](ff9mapkit/docs/tutorials/04-campaign.md).

## Chocobo Hot & Cold in your forest

**You get:** the real digging minigame — timer, prize pool, "Kweh!" — running in a forest fork
of your own, with prizes you choose.

**Try it:** fork a chocobo forest verbatim, add a `[chocobo]` block with your prize table.

**Go deeper:** [the `[chocobo]` reference](ff9mapkit/docs/FORMAT.md#chocobo-optional--chocobo-hot--cold-prize-pool--timer) ·
[FEATURES.md §Fields](ff9mapkit/docs/FEATURES.md#fields).

## Your own shops

**You get:** item shops and synthesis shops with stock you curate, opened from an NPC line —
plus custom weapons, armor, and item text to sell in them.

**Try it:** add a `[[shop]]` block and point an NPC's `opens_shop` at it.

**Go deeper:** [the `[[shop]]` reference](ff9mapkit/docs/FORMAT.md#shop--a-custom-shop-inventory--opener) ·
[tune weapons, armor & items](ff9mapkit/docs/FORMAT.md#weapon--armor--item--equip_bonus--tune-existing-item-stats-optional-repeatable).
