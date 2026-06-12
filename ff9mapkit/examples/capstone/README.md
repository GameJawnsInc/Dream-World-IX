# Starting-state capstone

A **New Game that boots directly into a custom field** with its starting **beat, party, bag, and gear**
all seeded from one entry `field.toml`. This is the narrative-state north star made concrete: not "fork a
field and walk around at scenario-zero," but "start a fresh game and land in the right beat, as the right
party, holding the right things."

## The four channels (one field, one mod folder)

| Block | Lands in | Read by the engine at | Owner |
|---|---|---|---|
| `[startup]` | the field `.eb` (prepended to `Main_Init`) | field load — ScenarioCounter + a `gEventGlobal` bit | story_flags |
| `[party]` | the field `.eb` (prepended to `Main_Init`) | field load — `B_PARTYADD` adds to the menu/battle roster | story_flags |
| `[start_inventory]` | `StreamingAssets/Data/Items/InitialItems.csv` | **New Game** (`ff9item.FF9Item_Init`) | items_equipment |
| `[[equipment]]` | `StreamingAssets/Data/Characters/DefaultEquipment.csv` | **New Game** (`ff9play.FF9Play_Init`) | items_equipment |

`build`/`deploy_field` compose all four automatically — the two `.eb` levers at script synthesis, the two
CSVs at the mod-write stage — from this single entry field. The CSVs are **read only at a true New Game**,
so the proof is a New Game, not an F6 warp (which skips them).

## Why `[party]` adds Steiner + Freya but *not* Zidane

At New Game `FF9Play_Init` seeds **Zidane into party slot 0** (slots 1–3 = `NONE`) and builds every PLAYER
struct with its `DefaultEquipment` row. So `[party]` adds the **others** on top (re-adding Zidane would
duplicate the slot), and a member added by `[party]` **joins wearing its `[[equipment]]` gear** — Steiner
walks in with Excalibur + Genji because his PLAYER struct was built with that delta at new-game init.

## Run it

```sh
ff9mapkit lint  examples/capstone/capstone.field.toml

# Deploy to field 4003 in the highest-priority mod folder (the New-Game override warps Field(4003) and
# lives there; InitialItems.csv is highest-priority-wins, so it must not be shadowed by a higher folder):
py tools/deploy_field.py examples/capstone/capstone.field.toml --id 4003 --mod-folder FF9CustomMap

# Seamless entry: the field-70 override (evt_alex1_ts_opening) warps Field(4003); strip its opening FMV:
py tools/skip_opening_fmv.py        # idempotent — reports "already clean" if done

# Relaunch, then New Game.
```

**What to see:** the title screen → (no opening FMV) → field 4003. Party menu = **Zidane / Steiner / Freya**,
Steiner wearing **Excalibur + Genji Helmet + Genji Armor**; the bag holds the custom items (incl. an
Excalibur — unmistakably not a real new-game bag); **F6 → Flags** shows ScenarioCounter `2600` and bit
`8512` set. One New Game proves all four channels.

The entry mechanism is engine-independent (a stock-Memoria mod field-70 override; the only custom DLL is the
F6 debug menu) — see memory `project-ff9-new-game-entry`. The placeholder art is the kit's own (copied from
`examples/SHOWCASE`); repaint `art/*.png` to taste.
