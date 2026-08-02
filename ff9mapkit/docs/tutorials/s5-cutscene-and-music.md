# S5 — A cutscene and music

```toml
[tutorial]
track = "S"
step = 5
builds_on = ["s4-story-flags"]
goal = "An entry cutscene that plays once, over a music pick of your own."
requires = ["game", "gui", "assets"]

[[tutorial.ui]]
label = "Play once"
widget = "form:cutscene.once"

[[tutorial.ui]]
label = "Cast"
widget = "form:cutscene.actors"

[[tutorial.ui]]
label = "Requires beat"
widget = "form:cutscene.requires_scenario"

[[tutorial.ui]]
label = "Then set beat"
widget = "form:cutscene.set_scenario"

[[tutorial.ui]]
label = "Field BGM song id"
widget = "form:music.song"

[[tutorial.ui]]
label = "File (custom track)"
widget = "form:music.file"
```

A **cutscene** is the one thing the other forms can't express — steps that run *in order*, with
player control locked while they do. This step adds a minimal one, plus the field's music.

**Starting from:** any room of the S3/S4 pair.

## 1. A scene on entry

In the Editor, open the **Cutscene** section:

![The cutscene form — ordered steps with per-step type and value](../../../docsite/assets/shots/editor-cutscene_light.png)

Build a three-step narration with the step editor on the right — pick a **Type**, fill
**Value**, press **Add step**:

1. **Say (dialogue)** — a line; the window blocks until dismissed,
2. a wait — a pause in frames (30 ≈ one second),
3. another **Say (dialogue)**.

**Add step** inserts after whichever row is selected, so you can go back and write a line into the
middle later; **Update selected** rewrites the row you have picked. As you type a **Say**, the pane
underneath shows where the line will break on the FF9 screen — the game never wraps text itself.

Leave **Play once** checked: the scene plays a single time ever, guarded by a save-persistent
flag allocated automatically — the same mechanism as S4's chest. Control locks for the duration
on its own.

Deploy, **~ → Reload**, walk in. **What you should see:** the party stops, the lines play in
order, control returns — and a second visit skips the scene (the once-flag at work; to watch it
again during authoring, deploy again and reload — a redeploy starts the field's state fresh in
the **Test slot**, [S1](s1-fork-and-deploy.md)'s name for this same scratch id).

A scene can also drive NPCs — walk them, turn them, have them speak — by naming them under
**Cast**; gated to story beats (**Requires beat** / **Then set beat**) it becomes FF9's own
story-event dispatch. Both are in
[`[cutscene]` in the reference](../FORMAT.md#cutscene--cutscene-optional).

## 2. Field music

The **Music** section sets the field's BGM:

- **Field BGM song id** — any of FF9's tracks (Browse… lists them by name). Plays on entry and
  resumes after battles. Hot-reloads with the normal loop.
- **File (custom track)** — a wav/mp3/ogg path; the build transcodes it and mints a new song id
  into the mod. Note: custom audio loads at game **startup**, so this one needs a full game
  restart to hear — ~ reload is not enough.

Deploy, reload (or restart for a custom file). **What you should hear:** the selected track
under your scene.

## Next

- [S6 — Random encounters](s6-encounters.md).
- Every step kind, cast scenes, ATEs, the story dispatch:
  [`[cutscene]`](../FORMAT.md#cutscene--cutscene-optional) · [`[music]`](../FORMAT.md#music-optional).
