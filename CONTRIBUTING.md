# Contributing to Dream World IX

**Dream World IX** is an early **public beta** of a toolkit for building
brand-new *Final Fantasy IX* fields — and faithfully forking the real ones — for the
[Memoria engine](https://github.com/Albeoris/Memoria).

At this stage the most valuable contributions are **bug reports** and **field-authoring / forking
questions**. If something black-screens, lands off the walkmesh, or a fork doesn't play the way you
expected, open an issue.

## Reporting a bug

Open a [GitHub issue](https://github.com/GameJawnsInc/Dream-World-IX/issues/new/choose) using the **bug report** template, and include:

- the output of **`ff9mapkit doctor`** (it reports your install + whether templates are extracted);
- the **field id** involved (the real id you forked, and/or the custom id you deployed to);
- the **exact command** you ran (copy/paste it, including flags);
- **steps to reproduce**, and what you expected vs. what happened.

For a visual or in-game bug (alignment, a camera drift, something rendering wrong), attach **a few
seconds of screen capture** to the issue — the toolkit cannot see the running game, so a short clip
is the most direct evidence for diagnosing the problem.

## Dev setup

Run from the **package directory** (`ff9mapkit/`, where `pyproject.toml` lives), not the repo root:

```powershell
cd ff9mapkit
pip install -e ".[dev,save,gui,assets]"  # dev = pytest, save = pycryptodome, gui = PySide6, assets = UnityPy
ff9mapkit extract-templates              # one-time: regenerate base assets from YOUR install
py -m pytest -n 6                        # the offline test suite
```

A few notes:

- **Python ≥ 3.11** is required.
- `ff9mapkit extract-templates` regenerates the base assets from a copy of the game **you legally
  own** — the repo ships zero game data. Until it runs, the byte-level tests skip (the pure-logic
  tests always run). See [SETUP.md](SETUP.md) for the details.
- `ff9mapkit <cmd>` and `py -m ff9mapkit <cmd>` are equivalent.

The full setup (game-path resolution, the extras, the dev loop) is in **[SETUP.md](SETUP.md)**.

## Project layout

| Path | What it is |
|---|---|
| `ff9mapkit/ff9mapkit/` | The Python package (the toolkit itself). |
| `ff9mapkit/blender/` | The Blender add-on (package `ff9mapkit_blender`, with its own tests). |
| `apps/` | The desktop **Workspace** GUI (PySide6). |
| `tools/` | The build/deploy dev-loop scripts. |
| `memoria-patches/` | The engine patch suite (the F6 debug menu `s22` + the fork-donor remap patches `s23`–`s34`). |
| `ff9mapkit/docs/` | The documentation set. |

## Provenance rule

**Never commit FINAL FANTASY IX game bytes or decompiled field scripts.** The repo ships **zero**
Square Enix data, and it must stay that way. In practice that means: do **not** check in
`*.eb.bytes`, `*.bgx`, `*.bgi.bytes`, `*.mes`, decompiled / disassembled field scripts, or any
extracted game asset — these are derived from your own install at runtime, not distributed.

Before opening a pull request, double-check your diff contains no game bytes. If you're unsure
whether something counts, ask in the PR. The details are in
[`ff9mapkit/docs/PROVENANCE.md`](ff9mapkit/docs/PROVENANCE.md) and the project's
[DISCLAIMER.md](DISCLAIMER.md).

## Conduct

Be kind, assume good faith, and keep it about the work. Harassment or hostility isn't welcome here.
Issues or discussions that cross that line may be closed or moderated.
