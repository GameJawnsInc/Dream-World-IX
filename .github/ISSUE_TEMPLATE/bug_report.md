---
name: Bug report
about: Something the toolkit did wrong — a crash, a wrong output, or a field that misbehaves in-game
title: "[bug] "
labels: bug
---

> Dream World IX is a fan-made authoring toolkit and ships **no** Final Fantasy IX game data.
> Please do not paste FF9 game bytes (decompiled scripts, `.eb`/`.mes`/`.bgx`/`.bgi` contents)
> into an issue — describe the problem instead. See [PROVENANCE](../../ff9mapkit/docs/PROVENANCE.md).

### What happened

A clear description of the bug.

### What you expected

What you thought should happen instead.

### Exact command

The exact command you ran (copy/paste, including flags):

```
py -m ff9mapkit ...
```

### `doctor` output

The output of `py -m ff9mapkit doctor` (it reports the kit version, the resolved game install,
the mod root, and whether templates are extracted):

```
(paste here)
```

### Field

- **Field id** (the `--id`, or the real field you forked):
- **Novel or forked?** novel (from-scratch / BG-borrow) **or** forked — and if forked, which mode
  (`--editable` / `--native` / `--verbatim`).

### Environment

- **OS:** (e.g. Windows 11)
- **Python version:** (`py --version`)
- **ff9mapkit version:** (from `doctor`, or `py -m ff9mapkit --version`)

### Screen capture (for in-game / visual bugs)

If the bug is visual or positional — wrong placement, off-mesh content, a misaligned camera, a
black screen — a few seconds of screen capture is the single most useful thing you can attach. The
toolkit can't see the running game, so a clip is often the difference between a guess and a fix.

### Anything else

Logs (`Memoria.log`), a minimal `field.toml`, or other context.
