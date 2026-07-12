# 09 — Custom battle background

Fork one of FF9's 3D battle maps ("BBG"), retexture or reshape it, and fight in it. A battle map
is a real textured 3D mesh — unlike a field's painted plane — and ships as a loose FBX that
Memoria loads from the mod folder: **stock engine, no DLL**.

**Prerequisites:** the kit set up with UnityPy ([SETUP.md](../../../SETUP.md)); Blender only if
editing geometry. Lever reference (fight tuning, cameras, minted scenes):
[BATTLE_DESIGN.md](../BATTLE_DESIGN.md).

## 1. Pick and fork a donor

```powershell
ff9mapkit battle-list                            # browse the real BBGs
ff9mapkit battle-import BBG_B013 --out my_map    # fork -> battle.toml + BBG_B013.fbx + image#.png
```

The project holds the geometry (`.fbx`), its textures (`image#.png`), and a `battle.toml`:

```toml
[battlemap]
bbg = "BBG_B013"        # the slot this map ships as; keeping the donor slot OVERRIDES that real map
fbx = "BBG_B013.fbx"
# repoint_scene = 67    # optional: point an EXISTING battle scene's background at this bbg
```

## 2. Edit

- **Textures:** repaint the `image#.png` files in place.
- **Geometry:** edit the FBX in Blender — the add-on's **Import/Export Battle Map** round-trips
  it engine-faithfully. The mesh objects must keep their `Group_0/2/4/8` names (additive / ground
  / minus / sky render groups).

Because `bbg` names the donor slot, the edited map replaces that background for **every** battle
that uses it. To mint an independently triggerable battle instead (own enemies, stats, rewards,
camera), fork the gameplay too: `battle-import <bbg> --fork-scene <scene>` and tune the `[scene]`
block — see [BATTLE_DESIGN.md](../BATTLE_DESIGN.md).

## 3. Build and deploy

```powershell
ff9mapkit battle-build my_map\battle.toml --out dist
py tools\deploy_battle.py my_map\battle.toml --trigger-field 4003   # repo checkout; reversible
```

`--trigger-field` repoints a deployed field's encounter at the battle for testing. Without the
repo tools, install the built mod folder and register it in `Memoria.ini [Mod] FolderNames` +
`Priorities` (same order) as usual.

An FBX/texture override needs **no relaunch** (re-enter the battle); a `BattlePatch.txt` change
(`repoint_scene`, scene tuning) needs one.

## 4. Verify

Trigger the battle (walk the encounter field, or start any fight that uses the donor slot). The
edited geometry/textures render in combat; the camera sweeps through the modified scene.
