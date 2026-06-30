# Dream World IX 1.0.0b11 — maintenance release

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* fields — and
faithfully forking the real ones — for the [Memoria engine](https://github.com/Albeoris/Memoria)
(Steam/GOG FF9). Author a whole custom field from a single declarative `field.toml` and compile it into
a drop-in mod — or **fork any of FF9's ~674 real fields** and carry their content faithfully.

> A small maintenance release. **No new features since 1.0.0b10** — it's primarily a version bump (which
> also lets the b10 one-click **Upgrade & restart** verify against a live newer release).

## What's new since 1.0.0b10

- Version bump only; no functional changes. See the
  [1.0.0b10 notes](https://github.com/GameJawnsInc/Dream-World-IX/releases) for the themes, Preferences &
  About dialogs, and the one-click updater.

## Engine bundle (required for forked fields)

A **novel** field runs on **stock, unmodified Memoria**. A **forked** field needs the fork-fidelity patch
set — **unchanged** since the earlier betas (the **s23–s33** suite). The installer's "engine patches" task
installs `dwix-custom-memoria-1.0.0b11.zip` for you; or grab it from the assets below and run
`ff9mapkit setup --install-engine <that-zip>`, or follow
[ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md).

## Getting started

- **Easiest (Windows):** run `DreamWorldIX-Setup.exe` from the assets below. No Python needed.
- **Terminal:** `uv tool install ff9mapkit[gui,assets,save]` (or `pip install …`), then `ff9mapkit setup`.
- **Already on b10?** `uv tool upgrade ff9mapkit` (or use the in-app **Upgrade & restart**, or re-run the installer).
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
