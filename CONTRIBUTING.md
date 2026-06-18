# Contributing to Dream World IX

Thanks for taking a look! **Dream World IX** is an early **public beta** of a toolkit for building
brand-new *Final Fantasy IX* fields — and faithfully forking the real ones — for the
[Memoria engine](https://github.com/Albeoris/Memoria). The engine work is in-game proven, but the
docs and tooling still have rough edges.

At this stage the most valuable contributions are **bug reports** and **field-authoring / forking
questions** — both are genuinely welcome. If something black-screens, lands off the walkmesh, or a
fork doesn't play the way you expected, please tell us; that feedback is what shapes the beta.

## Reporting a bug

Open a [GitHub issue](../../issues/new/choose) using the **bug report** template, and include:

- the output of **`ff9mapkit doctor`** (it reports your install + whether templates are extracted);
- the **field id** involved (the real id you forked, and/or the custom id you deployed to);
- the **exact command** you ran (copy/paste it, including flags);
- **steps to reproduce**, and what you expected vs. what happened.

For a visual or in-game bug (alignment, a camera drift, something rendering wrong), **a few seconds
of screen capture is worth a thousand words** — the toolkit can't see the running game, so a clip
often turns a guessing game into a one-line fix. Attach it to the issue if you can.

## Dev setup

Run from the **package directory** (`ff9mapkit/`, where `pyproject.toml` lives), not the repo root:

```powershell
cd ff9mapkit
pip install -e ".[dev,save,gui]"   # dev = pytest, save = pycryptodome, gui = PySide6
pip install UnityPy                 # separate install; needed to read FF9's p0data*.bin
ff9mapkit extract-templates         # one-time: regenerate base assets from YOUR install
py -m pytest -n 6                   # the offline test suite
```

A few notes:

- **Python ≥ 3.11** is required.
- `ff9mapkit extract-templates` regenerates the base assets the kit builds against from a copy of
  the game **you legally own** — the repo ships zero game data. Until it runs, the byte-level tests
  skip (the pure-logic tests always run) and byte-level commands print a "run extract-templates"
  message. `ff9mapkit doctor` reports install + template status.
- `ff9mapkit <cmd>` and `py -m ff9mapkit <cmd>` are equivalent.

The full setup (game-path resolution, the extras, the dev loop) is in **[SETUP.md](SETUP.md)** —
read it first.

## Project layout

| Path | What it is |
|---|---|
| `ff9mapkit/ff9mapkit/` | The Python package (the toolkit itself). |
| `apps/` | The desktop **Workspace** GUI (PySide6). |
| `tools/` | The build/deploy dev-loop scripts. |
| `ff9mapkit/docs/` | The documentation set. |

## Provenance rule (please read)

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
