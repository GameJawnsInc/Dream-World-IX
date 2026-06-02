# FF9 Map Kit (`ff9mapkit`)

Author **novel custom field maps** for *Final Fantasy IX* (Steam, via the
[Memoria engine](https://github.com/Albeoris/Memoria)) from a single declarative
`field.toml`, compiled into a drop-in Memoria mod.

> **Status: under construction (v0.1.0).** This is the productized form of a proven,
> in-game-verified pipeline for minting brand-new playable FF9 fields with custom camera
> angles, painted backgrounds, walkmeshes, NPCs, dialogue, gateways, and encounters. The
> output runs on a **stock, unmodified Memoria install** — no engine patching required.

## What it does

Given a `field.toml` describing one field — its camera, painted background layers, walkmesh,
NPCs, dialogue, gateways, encounter, and music — `ff9mapkit build` emits everything a custom
field needs:

- the background scene (`.bgx` camera + overlay PNGs) and walkmesh (`.bgi`),
- the field event script (`.eb`) for all seven languages,
- dialogue text (`.mes`),
- and the `DictionaryPatch` / `BattlePatch` registration + `ModDescription.xml`.

## What stays a human task

By design the kit does **not** paint background art or model walkmesh geometry — those are
creative/3D tasks. Instead it gives you a **pixel-accurate paint guide** for your chosen
camera angle and converts your hand-modeled `.obj` walkmesh to the engine's `.bgi` format.

## Quickstart (preview)

```bash
pip install -e .
export FF9_GAME_PATH="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
ff9mapkit doctor          # verify paths
ff9mapkit build field.toml
```

See `docs/FORMAT.md` for the `field.toml` schema and `docs/PIPELINE.md` for the full
authoring workflow (these land with Phase 6).
