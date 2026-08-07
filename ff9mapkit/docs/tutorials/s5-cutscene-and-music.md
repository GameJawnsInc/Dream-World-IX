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

[[tutorial.ui]]
label = "Suggest a test room…"
widget = "import_field.rooms_btn"
```

A **cutscene** is the one thing the other forms can't express — steps that run *in order*, with
player control locked while they do. This step adds a minimal one, plus the field's music.

**Starting from:** any one deployed room of the build. To recreate it cold: fork a vetted room
(**Suggest a test room…**) and deploy it ([S1](s1-fork-and-deploy.md)); S4's caution about side
builds applies.

## 1. A scene on entry

Open the **Cutscene** tab (Author rail, next to Behavior). Its left rail lists every scene of
the field — none yet, so press **Add a scene**:

![The Cutscene tab — the scene rail, the step ladder, and the step editor open](../../../docsite/assets/shots/editor-cutscene_light.png)

Build a three-step narration: press **＋ Step**, pick a **Type**, fill **Value**, press
**Apply** —

1. **Say (dialogue)** — a line; the window blocks until dismissed,
2. a wait — a pause in frames (30 ≈ one second),
3. another **Say (dialogue)**.

After each Apply the editor stays open and moves to the next row, so a conversation types
straight through. **＋ Step** inserts after whichever row is selected — you can go back and
write a line into the middle later; a row's **pencil** unfolds it for editing (click again to
fold), **↑ ↓ ⧉ ✕** reorder, duplicate, and remove it. As you type a **Say**, the preview
underneath shows where the line will break on the FF9 screen — the game never wraps text
itself.

Under **Settings**, leave **Play once** checked: the scene plays a single time ever, guarded
by a save-persistent flag allocated automatically — the same mechanism as S4's chest. Control
locks for the duration on its own.

Deploy, **~ → Reload**, walk in. **What you should see:** the party stops, the lines play in
order, control returns — and a second visit skips the scene (the once-flag at work; to watch it
again during authoring, deploy again and reload — a redeploy starts the field's state fresh in
the **Test slot**, [S1](s1-fork-and-deploy.md)'s name for this same scratch id).

A scene can also drive NPCs — walk them, turn them, have them speak — by naming them under
**Cast** in **Settings**: the stage below the ladder then shows every walk on the room's
floor, **Check the staging** (right column) warns about any walk that would stall the scene,
and **▶ Storyboard** scrubs the scene beat by beat. Gated to story beats (**Requires beat** /
**Then set beat**) a set of scenes becomes FF9's own story-event dispatch — one `[[cutscene]]`
block per beat, all visible in the rail. Everything is in
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
