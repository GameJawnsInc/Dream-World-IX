# Dream World IX 1.0.0b7 — installer installs the engine, the GUI deploys when installed, an app icon

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* fields — and
faithfully forking the real ones — for the [Memoria engine](https://github.com/Albeoris/Memoria)
(Steam/GOG FF9). Author a whole custom field from a single declarative `field.toml` and compile it into
a drop-in mod — or **fork any of FF9's ~674 real fields** and carry their content faithfully.

> Still an **early public beta**. Engine work is largely in-game proven; the newest gates ship with the
> honesty caveat below. Bug reports and field-authoring questions are welcome.

## What's new since 1.0.0b6

### The installer can install the engine patches for you ★
Forking real fields needs the patched Memoria build. The Windows installer now **bundles** it and offers
an opt-in **"engine patches"** task that installs it for you — no separate download or manual DLL copy:
- It **backs up** your original Memoria DLLs first (under `<game>\dwix-engine-backups\`), and **never**
  touches `Memoria.ini` (Memoria auto-detects mod folders).
- It's **version-aware**: if our patched build is already in place it skips; if you later update or
  re-patch Memoria (which reverts our DLLs), just re-run it to reapply.
- If Memoria isn't installed yet it **degrades gracefully** — it tells you how to apply it later instead
  of erroring.

Prefer the terminal? `ff9mapkit setup --install-engine <dwix-custom-memoria-1.0.0b7.zip>` does the same.

### The Workspace GUI now deploys campaigns + journeys when installed ★
Previously an installed copy (`.exe` / `pip` / `uv`) could **build** a campaign or journey but couldn't
**deploy** it (those ran the repo's `tools/`). Now the multi-field deploys work from an installed copy:
- **Build & Deploy → campaign "Deploy to game"** and the whole **journey** flow (preview / deploy /
  re-apply links, with single-folder + New-Game options) install straight into your FF9 folder.
- **"Set New Game"** points New Game at any deployed field.
- All reversible — snapshots + a one-click **Revert** go to a per-user cache.

New CLI commands back these: **`ff9mapkit deploy-campaign`**, **`deploy-journey`**, and
**`ff9mapkit newgame <id>`** (all dry-run by default).

### A proper app icon
The Workspace, the installer, and the Start-Menu shortcut now carry a Dream World IX icon.

### Updating & uninstalling
- **Update:** `uv tool upgrade ff9mapkit` (or re-run a newer `DreamWorldIX-Setup.exe` — it upgrades in
  place, no uninstall first).
- **Uninstall:** Add/Remove Programs → "Dream World IX". It leaves `uv` + its Python, your
  `%LOCALAPPDATA%\ff9mapkit` data, and any engine patches applied to your **game** in place — the
  uninstaller points you at `<game>\dwix-engine-backups\` to restore stock Memoria if you want.

## Engine bundle (required for forked fields)

A **novel** field runs on **stock, unmodified Memoria**. A **forked** field needs the fork-fidelity patch
set — **unchanged** (the **s23–s33** suite). The installer's "engine patches" task installs
`dwix-custom-memoria-1.0.0b7.zip` for you; or grab it from the assets below and run
`ff9mapkit setup --install-engine <that-zip>`, or follow
[ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md). Disc-1 gates plus the s30/s31 walk+occlusion and
s33 menu-LOCATION fixes are in-game proven; the late-disc s29 softlock gates, s32, and the s33 sibling
sweeps ship unverified (identity-safe for real fields) and are being playtested as those zones are forked.

## Getting started

- **Easiest (Windows):** run `DreamWorldIX-Setup.exe` from the assets below. No Python needed — it installs
  the toolkit, runs `ff9mapkit setup` (detect FF9 + extract base assets), and can install the engine patches.
- **Terminal:** `uv tool install ff9mapkit[gui,assets,save]` (or `pip install …`), then `ff9mapkit setup`.
- **[FORKING_FF9.md](FORKING_FF9.md)** — a guided GUI walkthrough.  ·  **[SETUP.md](SETUP.md)** — install,
  the dev loop, updating/uninstalling, and your first field.

## Provenance

Dream World IX **ships no Final Fantasy IX game data.** It operates only on assets read from a copy of the
game you legally own. Unofficial, fan-made, not affiliated with or endorsed by Square Enix.

## License

[MIT](LICENSE) (© 2026 GameJawnsInc) — the Dream World IX / `ff9mapkit` source. The bundled engine patches
modify [Memoria](https://github.com/Albeoris/Memoria) (MIT, © Albeoris).

---

See **[Known issues](ff9mapkit/docs/KNOWN_ISSUES.md)** and
**[Troubleshooting](ff9mapkit/docs/TROUBLESHOOTING.md)**.
