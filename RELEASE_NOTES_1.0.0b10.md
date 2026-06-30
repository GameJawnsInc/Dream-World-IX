# Dream World IX 1.0.0b10 — Themes, Preferences & About, one-click upgrade

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* fields — and
faithfully forking the real ones — for the [Memoria engine](https://github.com/Albeoris/Memoria)
(Steam/GOG FF9). Author a whole custom field from a single declarative `field.toml` and compile it into
a drop-in mod — or **fork any of FF9's ~674 real fields** and carry their content faithfully.

> Still an **early public beta**. A Workspace settings pass: a **theme picker** with several popular
> schemes, a **Preferences** and **About** dialog, and a one-click **Upgrade & restart** for installed
> copies.

## What's new since 1.0.0b9

### Themes
The Workspace ships **seven** colour themes — the original **Light** and **Dark** plus **Nord**,
**Dracula**, **Solarized Dark**, **Solarized Light**, and **Gruvbox Dark**. Pick one in **Preferences ▸
Theme**; it applies **live** as you choose and is remembered across launches (and across a
`uv tool upgrade`). "Match system" follows your Windows light/dark setting. The light schemes were tuned
to be easy on the eyes (soft surfaces, not glaring white).

### Preferences & About
A new **⚙ menu** on the toolbar (also reachable from the Ctrl-K palette) opens:
- **Preferences** — the theme picker, plus the daily update-check toggle (installed copies).
- **About** — version, install mode, the provenance/license note, and links to the project, PyPI, and the
  issue tracker.

### One-click update (installed copies)
When a newer release is out, the update dialog now offers an **Upgrade & restart** button: it closes the
app, runs `uv tool upgrade ff9mapkit` in a terminal window, and reopens — no manual command needed. (The
copy-the-command path is still there, and a source checkout is still pointed at `git pull`.)

### Fixes
- The installer's Finished page no longer clips its message.
- Various contrast/legibility tweaks across the new palettes.

## Engine bundle (required for forked fields)

A **novel** field runs on **stock, unmodified Memoria**. A **forked** field needs the fork-fidelity patch
set — **unchanged** since the earlier betas (the **s23–s33** suite). The installer's "engine patches" task
installs `dwix-custom-memoria-1.0.0b10.zip` for you; or grab it from the assets below and run
`ff9mapkit setup --install-engine <that-zip>`, or follow
[ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md).

## Getting started

- **Easiest (Windows):** run `DreamWorldIX-Setup.exe` from the assets below. No Python needed.
- **Terminal:** `uv tool install ff9mapkit[gui,assets,save]` (or `pip install …`), then `ff9mapkit setup`.
- **Already on b9?** `uv tool upgrade ff9mapkit` (or re-run the installer).
- **[SETUP.md](SETUP.md)** — install, updating/uninstalling, the dev loop (incl. `FF9_REPO`), your first field.

## Provenance

Dream World IX **ships no Final Fantasy IX game data.** It operates only on assets read from a copy of the
game you legally own. Unofficial, fan-made, not affiliated with or endorsed by Square Enix.

## License

[MIT](LICENSE) (© 2026 GameJawnsInc) — the Dream World IX / `ff9mapkit` source. The bundled engine patches
modify [Memoria](https://github.com/Albeoris/Memoria) (MIT, © Albeoris).

---

See **[Known issues](ff9mapkit/docs/KNOWN_ISSUES.md)** and
**[Troubleshooting](ff9mapkit/docs/TROUBLESHOOTING.md)**.
