# NN — What the reader will have built by the end

```toml
[tutorial]
# Stripped by the Manual build; renders as chips under the title. GitHub shows this block as-is.
goal = "One sentence: the concrete thing this tutorial produces."
requires = ["game", "gui"]        # keys: game, templates, gui, assets, engine-bundle, blender, repo
# time = "20 min"                 # optional; only claim it if measured

# Every GUI control the prose names, declared here. The build verifies each against the
# harvested inventory (docsite/assets/ui-inventory.json): wrong/renamed/vanished label = build
# error. Three widget shapes:
#   a ribbon-tab control  -> the attr path, the same vocabulary shots.toml callouts use
#   a dialog control      -> "dlg:<dialog>", scoped to the dialog (the label is the identity)
#   an editor form field  -> "form:<section>.<field key>", naming exactly one field of one form
[[tutorial.ui]]
label = "Import field"
widget = "import_field.import_btn"

[[tutorial.ui]]
label = "Appears when flag set"
widget = "form:npc.requires_flag"
```

One or two sentences of orientation: what this builds on ([tutorial NN](NN-slug.md)) and what the
reader should already have open.

## 1. First act

Steps in numbered lists. **Bold** every UI control name, and declare each bolded control above.
Every `ff9mapkit` command goes in a `bash` fence — the build validates verbs and flags against
the real CLI, so write commands exactly as runnable:

```bash
ff9mapkit lint my.field.toml
```

Embed figures as plain image links into the shot assets (GitHub renders the light PNG; the site
upgrades to a theme-swapping, callout-overlaid figure). Declare the figure in `docsite/shots.toml`
with `used_by` pointing here, then run `py docsite/shots.py <name>`:

![Alt text that works as the caption](../../../docsite/assets/shots/SHOTNAME_light.png)

## 2. Verify

End every act with what the reader should SEE — the tutorial's own gate. Offline checks first
(`ff9mapkit lint`, the Problems console), the in-game check last, stated honestly (a build that
succeeds is not a field that works).

## Next

- The following tutorial in the ladder: [NN+1 — name](NN+1-slug.md)
- The reference for what was just used: [`field.toml` reference](../FORMAT.md)
