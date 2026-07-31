# Dream World IX Manual

Build brand-new FINAL FANTASY IX content — fields, campaigns, worlds, characters, battles — from
declarative TOML, a Python CLI, and a desktop Workspace. This manual is the explorable form of the
repository's documentation: same sources, plus a generated reference and auto-generated GUI
screenshots.

## Pick a task

| I want to… | Start here |
|---|---|
| Set the toolkit up | [Setup](SETUP.md) |
| Build my first mod (GUI, start here) | [S1 — Fork and deploy a field](ff9mapkit/docs/tutorials/s1-fork-and-deploy.md) · [the core track](ff9mapkit/docs/tutorials/README.md) |
| Do the same from the terminal (CLI) | [C1 — The CLI: fork, edit, deploy](ff9mapkit/docs/tutorials/c1-cli-fork-edit-deploy.md) |
| Learn the edit → deploy → reload loop | [Tutorial 02 — the dev loop](ff9mapkit/docs/tutorials/02-dev-loop.md) |
| Build a field from scratch, with original art | [Tutorial 03 — an original-art field](ff9mapkit/docs/tutorials/03-original-art-field.md) |
| Chain fields into a campaign or journey | [Tutorial 04](ff9mapkit/docs/tutorials/04-campaign.md) · [Tutorial 05](ff9mapkit/docs/tutorials/05-journey.md) |
| Write dialogue and cutscenes | [Tutorial 08](ff9mapkit/docs/tutorials/08-dialogue-cutscene.md) |
| Add custom 3D models or a new playable character | [Tutorial 10](ff9mapkit/docs/tutorials/10-custom-model.md) · [Tutorial 12](ff9mapkit/docs/tutorials/12-creature-from-scratch.md) |
| Look up a `field.toml` block | [`field.toml` reference](ff9mapkit/docs/FORMAT.md) |
| Look up a CLI verb | [CLI reference](reference/cli/index.html) |
| Fix something that broke | [Troubleshooting](ff9mapkit/docs/TROUBLESHOOTING.md) · [Known issues](ff9mapkit/docs/KNOWN_ISSUES.md) |

## The three authoring surfaces

- **`field.toml`** — the declarative language: one file describes a field's camera, walkmesh,
  NPCs, dialogue, gateways, events. The [reference](ff9mapkit/docs/FORMAT.md) documents every
  block.
- **The CLI** — `ff9mapkit` with over a hundred subcommands for importing, building, linting, and
  deploying. The [CLI reference](reference/cli/index.html) is generated from the argument parser
  itself, so it cannot drift from the code.
- **The Workspace** — the desktop GUI over the same engine. GUI tutorial screenshots in this
  manual are rendered by the toolkit's own headless harness and regenerate on demand, so they
  track the real interface.

## How this manual stays honest

Reference pages are generated from the toolkit's own code where possible, prose pages are the
repository's canonical markdown, and every internal link and anchor is verified at build time —
a broken link fails the build.
