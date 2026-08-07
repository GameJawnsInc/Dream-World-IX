# C2 — `field.toml` by hand

```toml
[tutorial]
track = "C"
step = 2
builds_on = ["c1-cli-fork-edit-deploy"]
goal = "Read and write the project file directly — the file every form and command has been editing."
requires = ["game", "assets"]
```

A field project is one TOML file. The Workspace forms, `ff9mapkit edit`, and the Blender add-on
all write the same file this step reads and edits by hand.

**Starting from:** C1's fork (`myroom\MYROOM.field.toml`). Any field project works.

## 1. What the import wrote

Open `myroom\MYROOM.field.toml`. The parts every field has:

```toml
[field]
id = 30001            # the custom field id (>= 4000; scratch band 30000+; avoid 9000-9012 -- reserved for the engine's world-map dispatchers; keep <= 32767, the fldMapNo Int16 ceiling)
name = "MYROOM"       # names the script + background folder
area = 11             # must be >= 10 (the loader reads exactly two digits)
```

A verbatim fork also carries a `[verbatim_eb]` block — its link to the donor's real event
script. Leave it alone; your content layers on top of it.

`[field]`, plus a camera and a walkmesh (carried by the fork's sidecars), is a complete,
buildable field. Everything else is optional blocks.

## 2. The one syntax rule that matters

TOML has two block shapes and the kit uses both:

- `[encounter]` — single brackets: **one per field** (a table). Writing it twice is an error.
- `[[npc]]` — double brackets: **repeatable** (an array of tables). Each `[[npc]]` block is one
  more NPC.

Which shape a block takes is in its reference heading — [`FORMAT.md`](../FORMAT.md) writes
`[[npc]]` and `[encounter]` exactly as you must.

## 3. The core track, as text

Everything the core track built through forms (S2–S6) is these blocks. What follows is a
reference specimen, not a walked exercise — [S3](s3-gateways.md)–[S6](s6-encounters.md) remain
the walkthrough for any block that misbehaves. A compact field carrying all of it:

```toml
[[npc]]
name = "Guide"
preset = "vivi"
pos = [-700, -900]
dialogue = "This line is not in the original game."
requires_flag = "chest_potion"     # S4's gate: appears only after the chest

[[gateway]]
to = 30002                         # S3: walk-out warp to the second room
entrance = 0
zone = [[300, -400], [700, -400], [700, -800], [300, -800]]

[[chest]]
pos = [0, 80]
item = ["Potion", 1]
flag = "chest_potion"              # S4: the save-persistent opened-bit

[[flag]]
name = "chest_potion"
index = 8720                       # safe band [8712, 16320)

[cutscene]                         # S5: three steps, control locked, plays once
once = true
steps = [
  { say = "The hut is silent..." },
  { wait = 30 },
  { say = "...for now." },
]

[encounter]                        # S6: random battles
scene = "BSC_EF_R007"
freq = 64

[music]
song = 9                           # S5: field BGM (9 = Vivi's Theme)
```

Reading a block cold: look its name up in the [reference](../FORMAT.md) — every key, default,
and constraint is documented per block.

## 4. Edit, lint, deploy

Hand edits go through the same pipeline as everything else:

```powershell
ff9mapkit lint myroom\MYROOM.field.toml
py tools\deploy_field.py myroom\MYROOM.field.toml --id 30001
```

`lint` catches the mistakes hand editing invites — off-walkmesh positions, a flag index in a
reserved band, a `requires_flag` nothing sets, a malformed zone — before the game runs. And the
round trip holds: open the file in the Workspace and the forms show your hand edits; save a
form and the TOML changes under you.

## 5. The optional scene split

One file is the default. For Blender-heavy work a project can split into `<x>.scene.toml`
(spatial: cameras, walkmesh, layers, positions — owned and overwritten by the add-on) and
`<x>.field.toml` (logic: dialogue, conditions, events — yours). `build` overlays scene onto
logic by entity `name`, so a re-export never clobbers a script. Details:
[the split in the reference](../FORMAT.md#two-files-scene-spatial--field-logic).

## Next

- [C3 — Deploy automation](c3-deploy-automation.md): slots, reverts, relaunch rules.
- The complete block-by-block reference: [`FORMAT.md`](../FORMAT.md).
