# Dream World IX 1.0.0b12 — custom 3D models + custom overworld

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* content — and faithfully
forking the real game — for the [Memoria engine](https://github.com/Albeoris/Memoria) (Steam/GOG FF9). Author a
whole custom field from a declarative `field.toml`, **fork any of FF9's ~674 real fields**, and now **import,
edit, and mint 3D models** and **reshape or extend the overworld** — most of it with **no engine changes at all**.

> The biggest content release yet: two new pillars. Everything below is authored offline from a copy of the
> game you own and, unless noted, runs **DLL-free**.

## What's new since 1.0.0b11

### 🧍 Custom 3D models — a whole new pillar (DLL-free)

Export a real FF9 character/field model, edit it in Blender, and put it back in the game.

- **`ff9mapkit model-gltf <GEO> --out m.glb`** — export any model to a Blender-openable **glTF**: rigged,
  textured, with its idle/walk/run clips. (`ff9mapkit models` lists them by name.)
- **`ff9mapkit model-import <edited.glb> --deploy <mod>`** — bring a Blender-edited model back. **One edited
  `.glb` round-trips the mesh *and* any changed animation clips.** Auto-detects the source, re-rigs if Blender
  changed the topology, and writes back only the clips you actually edited.
- **Animation editing** — edit keyframes in Blender (or hand-edit clip JSON with `ff9mapkit model-anim`) and
  play them in-game. Edit-detection is robust to Blender's re-sampling and to messy multi-import scenes.
- **`ff9mapkit model-mint`** — add brand-new model ids (additive custom models, `SetModel` targets).
- **Blender add-on** — one-click **Import/Export FF9 Model** buttons in the *3D Model* panel; the add-on writes
  the `.glb` and hands you the exact CLI command to run.
- Faithful across the model set: per-mesh bind correction (divergent-SMR characters), per-part named export
  (multi-mesh characters like Garnet), and story-evolved appearance handling.
- **Tutorial:** [ff9mapkit/docs/ANIMATION_EDITING.md](ff9mapkit/docs/ANIMATION_EDITING.md) and
  [ff9mapkit/docs/CUSTOM_MODELS.md](ff9mapkit/docs/CUSTOM_MODELS.md).

### 🗺️ Custom overworld — reshape and extend the world map

- **`world-terrain`** — reshape walkable land (hill / crater / ridge / flatten) by editing the stock mesh.
- **`world-reclaim` / `world-coast`** — turn ocean cells into walkable land and carry a **faithful real
  coastline** (animated beach/sea/foam) — the foundation for new continents. *(needs the engine bundle.)*
- **`world-entrance`** — author an overworld entrance from scratch: a `!` on the map that warps into a field,
  optionally with a **modelled Blender building** that renders, blocks the player cleanly, and round-trips.
- **`world-encounters` / `world-encounter-rate`** — re-table overworld monsters and retune encounter frequency.
- **Texturing** — texture new geometry from a learned UV palette, reskin atlas tiles, or paint new atlas art.
- **`world-rename-markers` / `[startup] reveal_markers` / `world-environment`** — rename/reveal minimap markers
  and author weather/effects.
- **F6 debug menu on the overworld** — live position/cell/disc readout, teleport, vehicle-mode swap, disc switch.

### 🔧 F6 in-game debug menu

- Redesigned into a clean 4-tab menu (Go / Cheats / Flags / Time) with a **unified pin list** (field warps +
  overworld spot teleports), pinnable/favorite warps, and overworld↔field warp/escape.
- New **"Reload + anims"** button — clears the clip cache so a re-deployed `.anim` shows on reload without a
  full relaunch (the animation-edit fast path).

## Engine bundle (required for forked fields + the new overworld features)

A **novel** field and the whole **custom-models** pillar run on **stock, unmodified Memoria**. A **forked** field
needs the fork-fidelity patch set (the **s23–s33** suite, unchanged). **New this release:** the bundle adds
**s34** (a loose overworld-mesh override) — required for `world-reclaim`/`world-coast`/`world-entrance` — plus
the overworld F6 tooling. The installer's "engine patches" task installs `dwix-custom-memoria-1.0.0b12.zip`; or
grab it from the assets below and run `ff9mapkit setup --install-engine <that-zip>`. See
[ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md).

## Getting started

- **Easiest (Windows):** run `DreamWorldIX-Setup.exe` from the assets below. No Python needed.
- **Terminal:** `uv tool install ff9mapkit[gui,assets,save]` (or `pip install …`), then `ff9mapkit setup`.
- **Already installed?** `uv tool upgrade ff9mapkit` (or the in-app **Upgrade & restart**, or re-run the installer).
- **[SETUP.md](SETUP.md)** — install, updating, the dev loop, your first field.

## Provenance

Dream World IX **ships no Final Fantasy IX game data.** It operates only on assets read from a copy of the game
you legally own. Unofficial, fan-made, not affiliated with or endorsed by Square Enix.

## License

[MIT](LICENSE) (© 2026 GameJawnsInc) — the Dream World IX / `ff9mapkit` source. The bundled engine patches modify
[Memoria](https://github.com/Albeoris/Memoria) (MIT, © Albeoris).
