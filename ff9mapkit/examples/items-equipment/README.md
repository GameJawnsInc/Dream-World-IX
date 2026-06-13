# Items & equipment — the no-DLL showcase

One `field.toml` that exercises **every** item/equipment lever the kit ships, each a pure **data patch on
stock Memoria — no engine DLL**. This is the recreatable record of the `items_equipment` lane's in-game
proofs (each block below was verified in real gameplay; see `git log` + memory `project-ff9-items-equipment`).

## What each block tunes — and the channel it ships through

| Block | Lands in | Lever |
|---|---|---|
| `[[weapon]]` | `Data/Items/Weapons.csv` (ItemAttack) | `power`, `elements`, `category` (class), `status_index` + `rate` (Soul-Blade status) |
| `[[armor]]` | `Data/Items/Armors.csv` (ItemDefence) | `p_def` / `p_eva` / `m_def` / `m_eva` |
| `[[item]]` | `Data/Items/Items.csv` (ItemInfo) | `price`, `sell`, `equippable_by` (who can equip), `teaches` (abilities taught while equipped) |
| `[[equip_bonus]]` | `Data/Items/Stats.csv` (ItemStats) | equip stat bonuses (`strength`/`magic`/…) + elemental affinity; the level-up-growth input |
| `[[synthesis]]` | `Data/Items/Synthesis.csv` (FF9MIX_DATA) | a custom synthesis shop (recipes) + a `Menu(2,id)` press-shop opener |
| `[[item_effect]]` | `Data/Items/ItemEffects.csv` (ItemEffect) | what a consumable DOES (`power` heal/damage, `rate`, `element`, `status`, `for_dead`) |
| `[[item_text]]` | `TextPatch.txt` (a `>DATABASE` find/replace) | an item's menu **name** + **help/battle description** |

All but the synthesis press-shop are **mod-global** — they ship CSV / `TextPatch.txt` deltas into the mod
folder, so they take effect game-wide and you do **not** need to visit field 4003 (it's just the delivery
vehicle, and it hosts the synthesis shop you walk into).

## Run it

```sh
ff9mapkit lint examples/items-equipment/items_equipment.field.toml

# Build + deploy reversibly into the test slot (writes the CSV/TextPatch deltas + a revert script):
py tools/deploy_field.py examples/items-equipment/items_equipment.field.toml --id 4003

# Item CSVs + TextPatch.txt load ONCE at engine startup (not field load) -> RELAUNCH to apply (F6 Reload won't).
```

**What to see** (after a relaunch, with an F6-give of the items where noted):
- **Mage Masher** — Attack jumps to 99, now Fire-elemental, costs 1 gil, grants **+30 Magic** when equipped,
  and **teaches Soul Blade** (appears in Zidane's Skill command while equipped; gone when unequipped).
- **The Ogre** — equip it (it teaches Soul Blade) and use Soul Blade in battle: the enemy **shrinks** (Mini),
  proving the re-pointed weapon status.
- **Broadsword** — now appears in **Zidane's** weapon-equip list (vanilla: Steiner/Marcus/Blank only).
- **Bone Wrist** — equip on Zidane: **Strength +50** in the status menu.
- **Synthesis** — warp to 4003 (F6 → Warp → 4003), walk into the back, press: a **Synthesis** shop opens with a
  net-new recipe (Mythril Dagger ← Mage Masher + Potion), proving it's the kit's.
- **Potion** — heals exactly **15** in battle / **10** in the field (Power×15 / Power×10), and its menu reads
  **"Mega Potion"** / **"Restores 15 HP."** — the effect retune and the text retune agree.

## Revert (back to vanilla item data + text)

```sh
py tools/scroll_out/revert_deploy_4003.py    # restores the base Weapons/Armors/Items/Stats/ItemEffects/
                                             # Synthesis CSVs, removes TextPatch.txt, drops field 4003
```

The deploy writes into the mod folder (default `FF9CustomMap`); nothing here ships Square-Enix bytes — the
base CSV rows are read **live** from your install at build time and only the changed rows are emitted, and the
`TextPatch.txt` carries only the author's strings + the resolved item id.
