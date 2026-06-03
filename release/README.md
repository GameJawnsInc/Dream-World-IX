# FF9CustomMap — "Vivi's Return" (custom field demo)

A small custom-field mod for **Final Fantasy IX (Steam) + Memoria**: two hand-built rooms
(an exterior hut and its interior) reachable from **Alexandria Main Street**, with an NPC,
dialogue, a random encounter, and a door round-trip. Authored entirely with
[`ff9mapkit`](../ff9mapkit) — minted field IDs, custom camera + walkmesh, painted backgrounds.

**Runs on stock (unmodified) Memoria** — it ships no engine DLLs. (Two optional engine
quality-of-life fixes are proposed separately as upstream Memoria PRs; the mod does not need them.)

## Requirements
- Final Fantasy IX (Steam)
- [Memoria](https://github.com/Albeoris/Memoria) installed (via `Memoria.Patcher.exe`)

## Install
1. Copy the `FF9CustomMap/` folder into your game install, next to `FF9_Launcher.exe`
   (`…/steamapps/common/FINAL FANTASY IX/FF9CustomMap/`), or install it through the Memoria
   Mod Manager.
2. Make sure `FF9CustomMap` is **enabled** and high in the mod load order (it overrides one
   base field — Alexandria Main Street — to add the door).
3. Launch via `FF9_Launcher.exe`.

## How to reach it
Play to **Alexandria / Main Street** (early in Disc 1). A new **door** on the street leads into
the hut exterior (field 4000); the hut's door leads to the interior (4002), and back. There's a
talkable NPC and a winnable random encounter inside.

## What's inside (for modders)
- `DictionaryPatch.txt` — registers the two custom fields (`4000 HUT_EXT`, `4002 HUT_INT`).
- `BattlePatch.txt` — battle music for the interior encounter (Evil Forest scene → Battle theme).
- `StreamingAssets/.../FieldMaps/FBG_N11_HUT_EXT|HUT_INT/` — each room's `.bgx` scene + `.bgi`
  walkmesh + painted PNG layers.
- `StreamingAssets/.../field/<lang>/EVT_HUT_EXT|HUT_INT.eb.bytes` — the field event scripts.
- `StreamingAssets/.../field/<lang>/evt_alex1_at_street_a.eb.bytes` — overrides Alexandria Main
  Street to add the entrance door (the only base field this mod touches).
- `FF9_Data/embeddedasset/text/<lang>/field/1073.mes` — the NPC's dialogue (added at a high TXID;
  base text untouched).

Set `<Author>` in `ModDescription.xml` before redistributing.
