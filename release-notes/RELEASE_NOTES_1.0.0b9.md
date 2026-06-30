# Dream World IX 1.0.0b9 — Workspace UX polish + an opt-in update check

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* fields — and
faithfully forking the real ones — for the [Memoria engine](https://github.com/Albeoris/Memoria)
(Steam/GOG FF9). Author a whole custom field from a single declarative `field.toml` and compile it into
a drop-in mod — or **fork any of FF9's ~674 real fields** and carry their content faithfully.

> Still an **early public beta**. A quality-of-life pass on the **Workspace** GUI, plus a new opt-in
> **update check** so installed copies can tell when a newer release is out.

## What's new since 1.0.0b8

### Opt-in update check
The Workspace now shows its **version** in the title bar and in a clickable chip in the status bar. On a
first launch (installed copies only) it asks whether to check pypi.org **once a day** for a newer release —
only the version number is fetched, no personal data. When an update is out, the chip lights up; clicking
it shows the exact `uv tool upgrade ff9mapkit` command (with a Copy button + a link to PyPI) and a manual
*Check for updates*. Running from a source checkout, it stays quiet and — if you do check — points you to
`git pull` instead of the upgrade command.

### Workspace UX polish
- **Scrolling no longer changes your dropdowns.** A stray mouse-wheel over a combo box used to silently
  flip its value while you scrolled a panel (worst on the save editors) — an app-wide guard stops that.
  Click into a control to change it with the wheel.
- **Safer Revert.** The Build & Deploy *Revert* button is now destination-aware: it stays active only for
  the reversible test-slot deploy, and explains why a direct *Install to game* has no automatic undo.
- **Campaign Map legend + tooltips.** The map gained a legend for the node colours / edge styles, a
  per-node tooltip (status + fork mode + "double-click to open"), and a pointing-hand cursor over nodes.
- **Clearer copy throughout** — distinguishing tooltips on the toolbar *Check* / *Lint* actions, de-jargoned
  help (save-editor equipment/abilities, the "Window tail" pointer codes, the "mint-only" qualifiers), the
  retired "worktree" wording dropped, and a handful of small affordance fixes.

### Installer
The Finished page now reflects whether the engine-patches task actually ran.

## Engine bundle (required for forked fields)

A **novel** field runs on **stock, unmodified Memoria**. A **forked** field needs the fork-fidelity patch
set — **unchanged** since the earlier betas (the **s23–s33** suite). The installer's "engine patches" task
installs `dwix-custom-memoria-1.0.0b9.zip` for you; or grab it from the assets below and run
`ff9mapkit setup --install-engine <that-zip>`, or follow
[ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md).

## Getting started

- **Easiest (Windows):** run `DreamWorldIX-Setup.exe` from the assets below. No Python needed.
- **Terminal:** `uv tool install ff9mapkit[gui,assets,save]` (or `pip install …`), then `ff9mapkit setup`.
- **Already on b8?** `uv tool upgrade ff9mapkit` (or re-run the installer).
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
