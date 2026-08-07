# C4 — The GUI ↔ CLI bridge

```toml
[tutorial]
track = "C"
step = 4
builds_on = ["c1-cli-fork-edit-deploy"]
goal = "Map every Workspace action to its CLI verb, using the Output console as the reference."
requires = ["game", "gui", "assets"]

[[tutorial.ui]]
label = "Import field"
widget = "import_field.import_btn"

[[tutorial.ui]]
label = "Point New Game here"
widget = "build_deploy.set_ng"
```

The Workspace and the CLI are one engine with two front doors. This step makes the mapping
explicit, so either surface can be used where it is strongest — forms for browsing catalogs and
positions, the terminal for repetition and scripting.

**Starting from:** C1's fork open in the Workspace — any field project works.

## 1. The console is the reference

Every job the Workspace runs — fork, lint, build, deploy — streams into the **Output** console
with a timestamped head line. Watching it while clicking is the authoritative mapping: the
console shows what actually ran, on the current version, for the exact buttons pressed.

Working with it: **Ctrl+F** searches the log; the **Jobs** menu lists past jobs newest-first and
jumps to one, selecting its span — so the Copy button copies just that job's output. A job's
output pasted next to its CLI equivalent is the bridge in one screen.

Do the round trip once, concretely: press **Check** on the open project and read the job the
Output console just logged — it names the lint it ran and the file it ran on. Then run the CLI
twin on the same file:

```powershell
ff9mapkit lint myroom\MYROOM.field.toml
```

**What you should see:** the same findings, line for line — the page's claim verified rather
than asserted.

## 2. The mapping

The core actions, GUI → terminal:

| Workspace action | CLI |
|---|---|
| Assets ▸ Import → **Import field** | `ff9mapkit import <donor> --out <dir> --verbatim` |
| Editor forms + **Ctrl-S** | editing the `field.toml` directly ([C2](c2-field-toml-by-hand.md)) |
| **Check** / Problems | `ff9mapkit lint <field.toml>` |
| Build tab → **Test slot** + Deploy | `py tools\deploy_field.py <field.toml> --id <N>` (repo checkout) |
| Build tab → **Install to game** | `ff9mapkit deploy <field.toml> --apply` (dry-run without `--apply`) |
| Build tab → **Point New Game here** | `ff9mapkit newgame <id>` |
| Campaign deploy | `ff9mapkit deploy-campaign <campaign.toml> --apply` |
| Journey deploy | `ff9mapkit deploy-journey <journeys.toml> --apply` |
| Form editor outside the Workspace | `ff9mapkit edit <field.toml>` |

Spot checks, runnable as-is:

```powershell
ff9mapkit lint myroom\MYROOM.field.toml
ff9mapkit deploy myroom\MYROOM.field.toml
ff9mapkit deploy myroom\MYROOM.field.toml --apply
```

The deploy verbs are dry-run by default — the first `deploy` prints what would change, the
`--apply` writes it. The full flag set for any verb: `ff9mapkit <verb> -h`, or the generated
CLI reference.

## 3. Round-tripping is safe

Both surfaces edit the same files, so mixing them is normal: fork in the terminal, position the
NPC in the Workspace (the Inspector shows the art), then script batch deploys in the terminal.
A file changed outside the Workspace shows up on reopen — the file is the truth, not either
front end.

**Track C ends here.** The competence is the same as the core track's; the surface is
interchangeable.

## Where to next

- Deeper feature tracks: [the tutorials index](README.md) lists the how-tos and what each needs.
- The complete verb list, generated from the parser: the CLI reference (SETUP §7 in the repo,
  `reference/cli/` on the site).
- Automation depth — slots, reverts, relaunch rules: [C3](c3-deploy-automation.md).
