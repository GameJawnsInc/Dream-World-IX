# Dream World IX 1.0.0b6 — the GUI works when installed

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* fields — and
faithfully forking the real ones — for the [Memoria engine](https://github.com/Albeoris/Memoria)
(Steam/GOG FF9). Author a whole custom field from a single declarative `field.toml` and compile it into
a drop-in mod — or **fork any of FF9's ~674 real fields** and carry their content faithfully.

> Still an **early public beta**. Engine work is largely in-game proven; the newest gates ship with the
> honesty caveat below. Bug reports and field-authoring questions are welcome.

## What's new since 1.0.0b5

### The Workspace GUI now works for installed users ★
Previously the desktop **Build & Deploy** and **Import** tabs assumed you were running from a source
checkout, so they failed on an installed copy (the `.exe`, `pip`, or `uv` install) — exactly the people
the one-click installer is for. Fixed:
- **Build → "Install to game"** and **"Build only"** now work installed (they were starting in a folder
  that doesn't exist on a non-repo install).
- **Forking from the Import tab** writes to a discoverable `~/Dream World IX` folder instead of deep
  inside the package, and runs cleanly.
- The **dev-only deploy paths** (the test-slot + F6 reload loop, and reversible campaign/journey/battle
  deploys) are part of the *development* workflow and aren't shipped with an installed copy — so for an
  installed copy the field target now **defaults to "Install to game"**, the test-slot option is clearly
  marked *dev repo only*, and those actions show a helpful "use Install to game, then reach it via a
  gateway / New Game" message instead of a cryptic error.

If you installed via the `.exe` / `pip` / `uv`: fork a field on **Import**, then **Build & Deploy →
Install to game** drops it into your FF9 folder where Memoria picks it up automatically.

## Engine bundle (required for forked fields)

A **novel** field runs on **stock, unmodified Memoria**. A **forked** field needs the fork-fidelity patch
set — **unchanged** (the **s23–s33** suite). Download `dwix-custom-memoria-1.0.0b6.zip` from the assets
below and follow [ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md), or run
`ff9mapkit setup --install-engine <that-zip>`. Disc-1 gates plus the s30/s31 walk+occlusion and s33
menu-LOCATION fixes are in-game proven; the late-disc s29 softlock gates, s32, and the s33 sibling sweeps
ship unverified (identity-safe for real fields) and are being playtested as those zones are forked.

## Getting started

- **Easiest (Windows):** run `DreamWorldIX-Setup.exe` from the assets below. No Python needed — it installs
  the toolkit and runs `ff9mapkit setup` (detect your FF9 install + extract base assets) for you.
- **Terminal:** `uv tool install ff9mapkit[gui,assets,save]` (or `pip install …`), then `ff9mapkit setup`.
- **[FORKING_FF9.md](FORKING_FF9.md)** — a guided GUI walkthrough.  ·  **[SETUP.md](SETUP.md)** — install,
  the dev loop, and your first field.

## Provenance

Dream World IX **ships no Final Fantasy IX game data.** It operates only on assets read from a copy of the
game you legally own. Unofficial, fan-made, not affiliated with or endorsed by Square Enix.

## License

[MIT](LICENSE) (© 2026 GameJawnsInc) — the Dream World IX / `ff9mapkit` source. The bundled engine patches
modify [Memoria](https://github.com/Albeoris/Memoria) (MIT, © Albeoris).

---

See **[Known issues](ff9mapkit/docs/KNOWN_ISSUES.md)** and
**[Troubleshooting](ff9mapkit/docs/TROUBLESHOOTING.md)**.
