# FF9CustomMap — "Vivi's Return" (custom field demo)

A small custom-field mod for **Final Fantasy IX (Steam) + Memoria**: two hand-built rooms
(an exterior hut, field 4000, and its interior, field 4002), with an NPC, dialogue, a random
encounter, and a door round-trip between them. Authored entirely with
[`ff9mapkit`](../ff9mapkit) — minted field IDs, custom camera + walkmesh, painted backgrounds.
These rooms are a build-oracle (a from-scratch "can we make a field?" proof); the mod registers
only the two custom fields and touches no base field.

**Runs on stock (unmodified) Memoria** — it ships no engine DLLs. (Two optional engine
quality-of-life fixes are proposed separately as upstream Memoria PRs; the mod does not need them.)

## Requirements
- Final Fantasy IX (Steam)
- [Memoria](https://github.com/Albeoris/Memoria) installed (via `Memoria.Patcher.exe`)

## Install
1. Copy the `FF9CustomMap/` folder into your game install, next to `FF9_Launcher.exe`
   (`…/steamapps/common/FINAL FANTASY IX/FF9CustomMap/`), or install it through the Memoria
   Mod Manager.
2. Make sure `FF9CustomMap` is **enabled** and high in the mod load order. (It adds two new
   field IDs and overrides no base field.)
3. Launch via `FF9_Launcher.exe`.

## How to reach it
The two custom fields aren't wired into the base game's progression, so you reach them one of two
ways:
- **Dev engine (F6 debug menu):** in-game press **F6 → Warp to field → 4000** (hut exterior).
  The hut's door leads to the interior (4002), and back.
- **Point New Game at the hut:** run `py tools/retarget_newgame_warp.py 4000` (repoints the
  field-70 opening override's `Field()` warp at field 4000, all 7 languages — pure mod, no DLL),
  then relaunch and start a New Game.

Field 4000 is the hut exterior, 4002 the interior; there's a talkable NPC and a winnable random
encounter inside.

## What's inside (for modders)
- `DictionaryPatch.txt` — registers the two custom fields (`4000 HUT_EXT`, `4002 HUT_INT`).
- `BattlePatch.txt` — battle music for the interior encounter (Evil Forest scene → Battle theme).
- `StreamingAssets/.../FieldMaps/FBG_N11_HUT_EXT|HUT_INT/` — each room's `.bgx` scene + `.bgi`
  walkmesh + painted PNG layers.
- `StreamingAssets/.../field/<lang>/EVT_HUT_EXT|HUT_INT.eb.bytes` — the field event scripts
  (per language; the only event scripts this mod ships — no base field is overridden).
- `FF9_Data/embeddedasset/text/<lang>/field/1073.mes` — the NPC's dialogue (added at a high TXID;
  base text untouched).

Set `<Author>` in `ModDescription.xml` before redistributing.
