# C1 — The CLI: fork, edit, deploy

```toml
[tutorial]
track = "C"
step = 1
goal = "The core-track competence, terminal-native: fork a room, add an NPC, deploy, reload in-game."
requires = ["game", "assets"]
```

Everything the Workspace does routes through the `ff9mapkit` command line; this step does the
core track's S1–S2 directly in the terminal. If `ff9mapkit` is not on PATH, `py -m ff9mapkit
<cmd>` is identical.

**Starting from:** a set-up toolkit ([Setup](../../../SETUP.md) §1–§2, with the `assets` extra).
Verify:

```powershell
ff9mapkit doctor
```

It must report the game install found and `templates : extracted`.

## 1. Pick a donor field

```powershell
ff9mapkit list-fields glgv          # filter by zone code: iccv, grgr, alxt, trno, vgdl, ...
```

Zone codes are FBG-folder substrings; `ff9mapkit find-field treno` resolves friendly place names
when the code isn't known. To see what a fork will and won't reproduce before committing:

```powershell
ff9mapkit fork-report glgv_map792_gv_rm1_0 --explain
```

## 2. Fork it

```powershell
ff9mapkit import glgv_map792_gv_rm1_0 --out myroom --name MYROOM --verbatim
```

This writes `myroom\MYROOM.field.toml` plus the scene sidecars — and, with `--verbatim` (the
truest mode), the donor's real event script and text. The command prints the **walkmesh
bounds**; content you add must sit inside them.

## 3. Add the NPC — in the file

The forms the Workspace showed in S2 were writing TOML; here is the same NPC written directly.
Open `myroom\MYROOM.field.toml` and add:

```toml
[[npc]]
name = "Guide"
preset = "vivi"              # a cast model by name; `ff9mapkit archetypes` lists them
pos = [-700, -900]           # world (x, z) — inside the printed walkmesh bounds
dialogue = "This line is not in the original game."
```

On a verbatim fork the donor's script keeps running; the `[[npc]]` is layered on top.
(`ff9mapkit edit myroom\MYROOM.field.toml` opens the same file in the form editor — the two
surfaces edit one file.)

## 4. Lint

```powershell
ff9mapkit lint myroom\MYROOM.field.toml
```

Every offline validator: off-walkmesh content, wall clearance, dead flags, layer geometry. A
clean lint is the offline half of verification — the in-game look still decides.

## 5. Deploy and reload

From a repo checkout, the test-slot deploy:

```powershell
py tools\deploy_field.py myroom\MYROOM.field.toml --id 30001
```

Pass `--id` explicitly — it names the slot the deploy owns (without it, the shared default slot
is used). The script reverts the slot's previous deploy first and writes a
`revert_deploy_30001.py` to undo this one.

The first deploy of a new id needs one game relaunch (it registers the id). After that, the
loop from S2 applies unchanged:

**edit → deploy → ~ → Go → Reload field → look.**

Verify in-game: the field renders, the NPC is present, talking to it shows the line. To undo:

```powershell
py tools\scroll_out\revert_deploy_30001.py
```

On an installed copy without a repo checkout, deploy by building a mod folder instead —
[tutorial 01 §4–5](01-first-fork.md) covers the build + `Memoria.ini` registration route and the
New Game override.

## The bridge back to the GUI

Every Workspace action streams the verbs it runs into the Output console — watching it while
clicking is the fastest way to map the GUI onto the CLI. The reverse holds too: anything built
here opens in the Workspace (**Open Save** → the `field.toml`).

## Next

- C2 — `field.toml` by hand: what every form was writing *(not yet written; the
  [reference](../FORMAT.md) covers the format block by block)*.
- Deploy internals — slots, reverts, mod-folder resolution, relaunch rules:
  [02 — The dev loop](02-dev-loop.md).
- The full first-fork walkthrough with install-folder registration:
  [01 — First fork](01-first-fork.md).
