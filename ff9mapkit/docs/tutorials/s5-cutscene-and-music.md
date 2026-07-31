# S5 — A cutscene and music

```toml
[tutorial]
track = "S"
step = 5
builds_on = ["s4-story-flags"]
goal = "An entry cutscene that plays once, over a music pick of your own."
requires = ["game", "gui", "assets"]
```

A **cutscene** is the one thing the other forms can't express — steps that run *in order*, with
player control locked while they do. This step adds a minimal one, plus the field's music.

**Starting from:** any room of the S3/S4 pair.

## 1. A scene on entry

In the Editor, open the **Cutscene** section:

![The cutscene form — ordered steps with per-step type and value](../../../docsite/assets/shots/editor-cutscene_light.png)

Build a three-step narration with the step editor on the right — pick a **Type**, fill
**Value**, press **Add / Update**:

1. **Say (dialogue)** — a line; the window blocks until dismissed,
2. a wait — a pause in frames (30 ≈ one second),
3. another **Say (dialogue)**.

Leave **Play once** checked: the scene plays a single time ever, guarded by a save-persistent
flag allocated automatically — the same mechanism as S4's chest. Control locks for the duration
on its own.

Deploy, **~ → Reload**, walk in. **What you should see:** the party stops, the lines play in
order, control returns — and a second visit skips the scene (the once-flag at work; to watch it
again during authoring, deploy again and reload — a redeploy starts the field's state fresh in
the scratch slot).

A scene can also drive NPCs — walk them, turn them, have them speak — by naming them under
**Cast**; gated to story beats (**Requires beat** / **Then set beat**) it becomes FF9's own
story-event dispatch. Both are in
[`[cutscene]` in the reference](../FORMAT.md#cutscene--cutscene-optional).

## 2. Field music

The **Music** section sets the field's BGM:

- **Song id** — any of FF9's tracks (Browse… lists them by name). Plays on entry and resumes
  after battles. Hot-reloads with the normal loop.
- **Your own audio file** — a wav/mp3/ogg path; the build transcodes it and mints a new song id
  into the mod. Note: custom audio loads at game **startup**, so this one needs a full game
  restart to hear — ~ reload is not enough.

Deploy, reload (or restart for a custom file). **What you should hear:** the selected track
under your scene.

## Next

- [S6 — Random encounters](s6-encounters.md).
- Every step kind, cast scenes, ATEs, the story dispatch:
  [`[cutscene]`](../FORMAT.md#cutscene--cutscene-optional) · [`[music]`](../FORMAT.md#music-optional).
