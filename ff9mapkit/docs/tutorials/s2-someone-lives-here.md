# S2 — Someone lives here

```toml
[tutorial]
track = "S"
step = 2
builds_on = ["s1-stand-in-the-game"]
goal = "Add an NPC with your own dialogue line, and make the edit → deploy → reload loop a reflex."
requires = ["game", "gui", "assets"]
```

The room from S1 is empty. This step gives it a resident — and teaches the loop every later step
runs on: change one thing, deploy, reload in-game, look.

**Starting from:** the S1 fork open in the Workspace. To mint it fresh: **Assets ▸ Import** →
**Suggest a test room…** → **Import field** (two minutes; see [S1](s1-stand-in-the-game.md)).

## 1. Add the NPC

Select the field's node in the left-hand tree → the **Editor** tab shows its forms. Open the
**NPCs** section and add an entry:

![An NPC entry in the Editor forms — name, model, dialogue with the live wrap preview, position, and story-flag gates](../../../docsite/assets/shots/editor-npc_light.png)

- **Name** — any label; it names the entry in the tree.
- **Preset** — who it looks like; **Browse…** opens the catalog with portraits.
- **Dialogue** — the line spoken on talk. The preview under the box renders it in FF9's real
  window geometry, so overflow is visible *before* the game shows it.
- **Position** — where it stands. The Inspector on the right shows the field art with its
  walkable bounds; a position outside the mesh gets a lint finding, not a silent no-show.

**Ctrl-S** saves. The **Problems** console (bottom) lints live — a clean save here is the
offline half of the proof, no more: offline checks never replace looking at the game.

## 2. Deploy and look

**Ship ▸ Build & Deploy** → **Deploy** (**F9** does save-all + deploy in one press). In the
game: **~ → Reload field**. No relaunch — the id is already registered from S1.

**What you should see:** the NPC standing at the chosen spot; talking to it opens your line,
wrapped exactly as the preview showed.

## 3. The loop, named

That was the whole development cycle: **edit → Deploy (F9) → ~ Reload → look.** Two habits keep
it honest, and both come from hard-won experience:

- **One change per reload.** When something breaks, the last edit is the suspect — a batch of
  edits has no suspect.
- **The status bar keeps score.** The `game: in sync` / `game: N ahead` chip says whether the
  running game matches the open project; the change list behind it answers "what did I change
  since the last deploy?"

## Next

- [S3 — A door of your own](s3-a-door-of-your-own.md): a second room and gateways between them.
- Every NPC knob this step skipped: [`[[npc]]` in the reference](../FORMAT.md#npc-optional-repeatable).
