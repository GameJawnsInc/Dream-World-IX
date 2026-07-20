# 01 — First fork: a real field with your own NPC

Fork one of FF9's ~674 real fields onto a custom field id, add an NPC with new dialogue, and play
it. No painting, no Blender — the fork carries the real field's art, walkmesh, camera, exits,
encounters, and music.

**Prerequisites:** the kit set up ([SETUP.md](../../../SETUP.md) §1–2) with the `assets` extra
(UnityPy). Verify with `ff9mapkit doctor` — it must report the game install found and
`templates : extracted`. If `ff9mapkit` is not on PATH, `py -m ff9mapkit <cmd>` is identical.

## 1. Pick a donor field

```powershell
ff9mapkit list-fields glgv          # filter by zone code: iccv, grgr, alxt, trno, vgdl, ...
```

Zone codes are FBG-folder substrings; `ff9mapkit find-field treno` resolves friendly place names
to fields when the code isn't known.

Optionally preview what a fork will and won't reproduce before committing to a donor:

```powershell
ff9mapkit fork-report glgv_map792_gv_rm1_0 --explain
```

`fork-report` classifies the donor (static roster vs. story-driven), lists its story gates, and
suggests a `[startup]` beat where relevant. See [FORK_REPORT.md](../FORK_REPORT.md).

## 2. Fork it

```powershell
ff9mapkit import glgv_map792_gv_rm1_0 --out myroom --name MYROOM --verbatim
```

This writes `myroom\MYROOM.field.toml` plus the scene sidecars (atlas, walkmesh, and — for
`--verbatim` — the donor's real event script and text). The command prints the **walkmesh bounds**;
content you add must sit inside them.

- `--verbatim` ships the donor's whole real script and dialogue: real doors, story gating, real
  NPC behavior. Drop it for a plain BG-borrow (real art and walkmesh under a synthesized script) —
  simpler to edit, less faithful. The full mode comparison is in
  [FORK_FIDELITY.md](../FORK_FIDELITY.md).
- The default custom field id is `4003` (`--id N` to change; custom ids are 4000–9899 and must be
  unique across every installed mod folder — see [GLOBAL_RESOURCES.md](../GLOBAL_RESOURCES.md)).

## 3. Add an NPC

Open `myroom\MYROOM.field.toml` and add an `[[npc]]` block, keeping `pos` inside the printed
walkmesh bounds:

```toml
[[npc]]
name = "Guide"
preset = "vivi"              # place a cast model by name; `ff9mapkit archetypes` lists them
pos = [-700, -900]           # world (x, z) — inside the printed walkmesh bounds
dialogue = "This line is not in the original game."
```

On a verbatim fork the donor's script keeps running; the `[[npc]]` is layered on top of it.
`ff9mapkit edit myroom\MYROOM.field.toml` opens the same file in a form editor.

## 4. Lint, build, install

```powershell
ff9mapkit lint myroom\MYROOM.field.toml
ff9mapkit build myroom\MYROOM.field.toml --out dist\MyFirstField --mod-name MyFirstField
```

`lint` runs every offline validator (off-walkmesh content, wall clearance, dead flags, layer
geometry). `build` writes the complete Memoria mod directly into `--out`. Install it:

1. Copy `dist\MyFirstField\` into the FF9 install directory (next to `FF9_Launcher.exe`).
2. Add `"MyFirstField"` to **both** the `FolderNames` and `Priorities` lists under `[Mod]` in
   `Memoria.ini`, same position in each (game + launcher closed). The Memoria Launcher rewrites
   `FolderNames` from `Priorities` at every Play click, so a `FolderNames`-only edit silently
   reverts. (Launching once also auto-detects the folder — the hand edit just controls the order.)

## 5. Reach it in-game

Two routes:

- **New Game override (stock Memoria):**

  ```powershell
  ff9mapkit newgame 4003 --mod-folder MyFirstField
  ```

  Launch the game → New Game lands on field 4003 (the opening FMV is preserved). The command
  prints a `revert_newgame_from_stock.py` script — run it to restore the normal New Game
  (`newgame <other-id> --retarget` re-points rather than reverts).

- **debug menu (~) (custom engine bundle):** if the Dream World IX engine bundle is installed
  (`ff9mapkit setup --install-engine <zip>`, see [ENGINE.md](../ENGINE.md)), launch once so the
  new id registers, then press **~ → Go → Warp to field → 4003** from anywhere.

Verify: the field renders, the NPC is present, and talking to it shows the new line.

## Next

- Iterate faster (no relaunch per change): [02 — The dev loop](02-dev-loop.md)
- Add choices and cutscenes: [08 — Dialogue choices & a cutscene](08-dialogue-cutscene.md)
- Everything a `field.toml` can declare: [FORMAT.md](../FORMAT.md)
