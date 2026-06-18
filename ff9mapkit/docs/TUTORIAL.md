# Your first custom field in ~10 minutes

The fastest path from nothing to walking around your own field in-game. It uses **import** (fork a
real field) so you skip painting for now — you get a real-looking room immediately and learn the
loop. When you want fully original art, the from-scratch workflow is in [PIPELINE.md](PIPELINE.md).

**You need:** Python 3.11+, a legally-owned Steam FF9 with [Memoria](https://github.com/Albeoris/Memoria)
installed, and (for import) `pip install UnityPy`.

---

## 1. Install + sanity check (1 min)

```bash
cd ff9mapkit             # the package dir, where pyproject.toml lives (no pyproject at the repo root)
pip install -e .
export FF9_GAME_PATH="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
ff9mapkit extract-templates   # one time per checkout — regenerates base assets from your install
ff9mapkit doctor              # should find your install + report UnityPy present + templates extracted
```
(If the `ff9mapkit` command isn't on your PATH, use `py -m ff9mapkit …` — identical.)

Full setup, extras (`gui`/`save`/`dev`), game-path resolution, and the dev loop →
**[SETUP.md](../../SETUP.md)** (repo root).

## 2. Pick a field to fork (1 min)

```bash
ff9mapkit list-fields glgv        # or: alex, treno, grgr, … (map codes)
```
Copy a field name from the list, e.g. `glgv_map792_gv_rm1_0`.

## 3. Fork it (1 min)

```bash
ff9mapkit import glgv_map792_gv_rm1_0 --out myroom --name MYROOM
```
You now have `myroom/MYROOM_FORK.field.toml` (+ `camera.bgx`, `walkmesh.bgi`). It already renders the
real field's art, walkmesh, camera, and even its exits/encounters/music. The command prints the
**walkmesh bounds** — note them; your content must sit inside.

## 4. Drop in an NPC with your own line (3 min)

Open the `.field.toml` and uncomment the `[[npc]]` block (put `pos` inside the walkmesh bounds):

```toml
[[npc]]
name = "Greeter"
archetype = "vivi"
pos = [800, 200]          # within the printed walkmesh bounds
dialogue = "Welcome to the room I just made."
```
Prefer not to touch TOML? `ff9mapkit edit myroom/MYROOM_FORK.field.toml` does it in a form.

Then check it before building:
```bash
ff9mapkit lint myroom/MYROOM_FORK.field.toml      # flags off-walkmesh content, dead flags, etc.
```

## 5. Build into a mod (1 min)

```bash
ff9mapkit build myroom/MYROOM_FORK.field.toml --out dist/MyFirstField --mod-name MyFirstField
```
That writes a complete Memoria mod into `dist/MyFirstField/`. Copy that folder into the game install,
add its name to `Memoria.ini` under `[Mod] FolderNames` (the folder name must match the `--mod-name`),
and relaunch — a copied folder isn't read until it's enabled there.

## 6. Reach it in-game (2–3 min)

On stock Memoria the portable way to reach a new field is a gateway from a field you can already walk to.
(If you run the dev engine, the F6 debug menu can Warp straight to the id instead.)

Your field exists but needs a door. Fork that field too, add a gateway into yours, and ship it as an
override:

```bash
ff9mapkit import <a-field-you-can-reach> --out entry
```
In `entry/<NAME>.field.toml`, add a gateway pointing at your field's id (forks default to `4003`):

```toml
[[gateway]]
to = 4003                                  # your field's [field] id
zone = [[-200, 200], [200, 200], [200, 400], [-200, 400]]   # a spot the player walks over
```
Placing that zone is easiest visually in the **[Blender add-on](../blender/README.md)** (drop a
Gateway marker), but hand coords inside the walkmesh work too. Build it the same way, copy into the
game, launch, walk onto the zone — and you're in your room talking to your NPC.

---

## What you just learned

The whole loop is `import` (or `new`) → edit `field.toml` → `lint` → `build` → drop in the game. From
here:
- **Original art:** [PIPELINE.md](PIPELINE.md) — paint over the generated guide, wire the layers.
- **More content:** [FORMAT.md](FORMAT.md) — encounters, events, story flags, cutscenes, multi-camera.
- **Everything at a glance:** [FEATURES.md](FEATURES.md).
