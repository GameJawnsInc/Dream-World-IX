# 15 — A new playable character (`[[playable]]`)

```toml
[tutorial]
track = "D"
goal = "Recruit a genuinely new party member — its own name, stats, and command menu — with zero engine changes."
requires = ["game", "repo"]
```

This adds a **new engine `CharacterId`** — a 13th party member alongside all 12 canon characters,
not a reskin of an existing slot. It has its own name, its own stats, its own save presence, and
(optionally) its own battle model, animations, portrait, and command menu. The whole thing is
data: CSV rows, a name directive, and one recruit op in the field script — **no DLL, stock
Memoria**. The only exception is a custom battle *formula* (`script`), which uses the
Scripts-DLL channel.

**Starting from:** any field project of your own — the core track's room ([S1](s1-fork-and-deploy.md))
or C1's fork both work. The shipped proof field
[`examples/thirteenth-character/`](../../examples/thirteenth-character/iviv.field.toml) is the
worked reference for everything below; read it alongside this page, but author in your own
project rather than editing the bundled example in place.

## 1. Define and recruit — one block

Add to your `field.toml`:

```toml
[[playable]]
name = "Iviv"            # the menu/battle name (no ';' or '#')
borrow = "vivi"          # clone a canon character's stats + rig as the starting point
recruit = true           # join the party when this field loads
stats = { magic = 40 }   # optional overrides on the cloned stats
```

- **`borrow`** is required: the new character starts as a clone of a canon character's stats,
  equip set, and battle rig — Vivi gives a mage, Steiner a knight. Everything diverges from
  there.
- **`recruit = true`** prepends a real party-add to the field's init script, so the character
  joins the moment the field loads. Without it the character exists but never joins.
- The engine id defaults to `12`, the first custom slot; a second `[[playable]]` block takes
  `id = 13`, and the kit auto-allocates every band (stats rows, presets, commands) so custom
  characters never collide. Every key: [`[[playable]]` in the
  reference](../FORMAT.md#playable--a-brand-new-custom-playable-character).

```powershell
ff9mapkit lint myroom\MYROOM.field.toml
```

## 2. Deploy — the order matters

```powershell
py tools\deploy_field.py myroom\MYROOM.field.toml --id 30001
```

The deploy carries the character's CSV rows and name lines alongside the field, reversibly. Then,
in exactly this order:

1. **Relaunch FF9.** The character rows load at **startup / New-Game init** — the debug menu's
   Reload field re-reads only the field's own files and will not pick them up.
2. **New Game.** The engine builds its roster from the loaded rows, so the new id must be present
   when the party is initialized.
3. **~ → Warp to field** → your id. The field's init recruits the character on load.

## 3. Verify — the three proofs

The claim "a real party member" decomposes into three checks, each observable:

1. **Appears** — open the party menu: the character is its own entry, with its own name and the
   overridden stats. Equip, Status, and Ability all open on it.
2. **Fights** — if the room has encounters ([S6](s6-encounters.md) arms them in one form), the
   character takes its place in the battle line and acts with its own commands.
3. **Saves** — save at a save point, reload that save from the title: the character is still in
   the party. Persistence rides Memoria's extra save block, and a save made with a custom
   character still loads on a stock engine (the extra member is dropped, nothing corrupts).

The shipped proof field wires all three into one room (encounters + a save point); deploying it
as-is is the fastest end-to-end check:

```powershell
py tools\deploy_field.py ff9mapkit\examples\thirteenth-character\iviv.field.toml --id 30001
```

## 4. Two standing caveats

- **Never open the in-game rename screen for a custom character.** That engine screen has a
  hardcoded boundary below the custom band; opening it for id 12 overwrites Zidane's name. The
  character's name comes from the deploy — there is no reason to open it.
- **Fields render only the party leader.** The new character shows in the menu and in battle,
  not as a walking follower in the field. Expected engine behavior, not a bug.

## 5. Going further — each one block-level, all optional

- **Its own battle look** — `custom_battle_model = true` mints an independent, editable copy of
  the borrowed battle model bound to the new character, so reshaping or recoloring it in Blender
  ([tutorial 10](10-custom-model.md)'s loop) never touches the donor. Add
  `custom_battle_anims = true` and the 34 battle motions become the character's own editable
  clips too — `ff9mapkit playable-anims` exports them to Blender with named actions and routes
  the edits back:

  ```powershell
  ff9mapkit playable-anims myroom\MYROOM.field.toml --export anims.glb
  ```

- **A menu portrait** — `portrait = "art/face.png"` (a 132×190 PNG) puts a custom avatar in the
  party menu, via a loose atlas override.
- **Its own command menu** — a `[playable.abilities]` table gives the character its own preset:
  stock commands by name, or a minted one-of-a-kind command with a curated spell pool, including
  custom abilities cloned from stock donors and retuned (power, element, MP, inflicted
  statuses). The proof field's "Spark" command mixes Black and White Magic — something no canon
  character does — plus two custom spells.

All of these are worked, commented, and in-game proven in the example's
[`iviv.field.toml`](../../examples/thirteenth-character/iviv.field.toml); the key tables live in
[the reference](../FORMAT.md#playable--a-brand-new-custom-playable-character).

## Next

- The example's [README](../../examples/thirteenth-character/README.txt) — the full proof recipe,
  including the Blender animation-edit loop.
- [Tutorial 10 — Edit a character model](10-custom-model.md): the mesh/texture round-trip the
  custom battle model plugs into.
- Battle-side depth (formulas, tuning): [BATTLE_DESIGN.md](../BATTLE_DESIGN.md) ·
  [SCRIPTS_DLL.md](../SCRIPTS_DLL.md).
