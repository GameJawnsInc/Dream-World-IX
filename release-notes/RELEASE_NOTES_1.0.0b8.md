# Dream World IX 1.0.0b8 — dev mode on an installed copy + a clearer installer finish

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* fields — and
faithfully forking the real ones — for the [Memoria engine](https://github.com/Albeoris/Memoria)
(Steam/GOG FF9). Author a whole custom field from a single declarative `field.toml` and compile it into
a drop-in mod — or **fork any of FF9's ~674 real fields** and carry their content faithfully.

> Still an **early public beta**. A small follow-up to b7 — quality-of-life for developers + an installer
> wording fix.

## What's new since 1.0.0b7

### The installed Workspace can use the dev loop against a checkout
If you have both an installed copy and a source checkout, the installed `ff9mapkit-workspace` can now light
up the **dev test slot (4003) + F6 reload loop**: set the **`FF9_REPO`** environment variable to your Dream
World IX repo (or just launch the Workspace from inside the checkout) and reopen. Without it, the installed
Workspace stays in end-user mode (Build → *Install to game*, campaign/journey deploy, *Set New Game*) — the
dev-only test slot is hidden, now with a tooltip explaining how to enable it.

### Installer Finished page wording fix
The Finished page no longer points at "the setup window above" (the bootstrap window closes when it
finishes, so there's nothing above by then). It now tells you to run **`ff9mapkit setup`** to check the
engine status, or **`ff9mapkit setup --install-engine`** to apply the patches.

## Engine bundle (required for forked fields)

A **novel** field runs on **stock, unmodified Memoria**. A **forked** field needs the fork-fidelity patch
set — **unchanged** (the **s23–s33** suite). The installer's "engine patches" task installs
`dwix-custom-memoria-1.0.0b8.zip` for you; or grab it from the assets below and run
`ff9mapkit setup --install-engine <that-zip>`, or follow
[ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md).

## Getting started

- **Easiest (Windows):** run `DreamWorldIX-Setup.exe` from the assets below. No Python needed.
- **Terminal:** `uv tool install ff9mapkit[gui,assets,save]` (or `pip install …`), then `ff9mapkit setup`.
- **Already on b7?** `uv tool upgrade ff9mapkit` (or re-run the installer).
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
