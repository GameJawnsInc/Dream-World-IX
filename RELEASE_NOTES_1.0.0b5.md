# Dream World IX 1.0.0b5 — finds your FF9 anywhere (Steam + GOG)

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* fields — and
faithfully forking the real ones — for the [Memoria engine](https://github.com/Albeoris/Memoria)
(Steam/GOG FF9). Author a whole custom field from a single declarative `field.toml` and compile it into
a drop-in mod — or **fork any of FF9's ~674 real fields** and carry their content faithfully.

> Still an **early public beta**. Engine work is largely in-game proven; the newest gates ship with the
> honesty caveat below. Bug reports and field-authoring questions are welcome.

## What's new since 1.0.0b4

### Auto-detects your FF9 install anywhere — Steam **and** GOG ★
- The install detector now mirrors Memoria's own: it reads the **per-game Steam and GOG registry keys**,
  so it finds FF9 **on any drive or a custom-named Steam library** (not just the three default paths), and
  it supports the **GOG** release (FF9 arrived on GOG in Jan 2026 — same Unity port).
- Fallback layers (a Steam `libraryfolders.vdf` scan, then default folders) cover the edge cases, and every
  detected folder is validated as a real, moddable install.
- The **Microsoft Store / Xbox Game Pass** version is correctly skipped — it's a different, non-Unity,
  DRM-locked build that can't be modded; use the Steam or GOG release.

Net effect: `ff9mapkit setup` (and the installer's auto-setup) now "just works" for far more people — no
manual `--game` path for anyone whose Steam library lives on a second drive, or who bought FF9 on GOG.

### Fork fidelity
- `--native` / synthesized forks now auto-emit `ForkDonorPatch.txt`, so fork-gated engine behavior (the
  s23–s33 suite) applies to them as it does for verbatim forks.
- Cutscene/ATE cleanup: the multi-actor conductor's verbatim `exit_warp` is in-game proven; the deprecated
  held-banner ATE was removed.

## Engine bundle (required for forked fields)

A **novel** field runs on **stock, unmodified Memoria**. A **forked** field needs the fork-fidelity patch
set — **unchanged** (the **s23–s33** suite). Download `dwix-custom-memoria-1.0.0b5.zip` from the assets
below and follow [ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md) — or run
`ff9mapkit setup --install-engine <that-zip>`. Disc-1 gates plus the s30/s31 walk+occlusion and s33
menu-LOCATION fixes are in-game proven; the late-disc s29 softlock gates, s32, and the s33 sibling sweeps
ship unverified (identity-safe for real fields) and are being playtested as those zones are forked.

## Getting started

- **Easiest (Windows):** run `DreamWorldIX-Setup.exe` from the assets below. No Python needed — it installs
  the toolkit and runs `ff9mapkit setup` (detect your FF9 install + extract base assets) for you.
- **Terminal:** `uv tool install ff9mapkit[gui,assets,save]` (or `pip install …`), then `ff9mapkit setup`.
- **[FORKING_FF9.md](FORKING_FF9.md)** — a guided GUI walkthrough: fork a slice of FF9, change a line of
  dialogue, and play it back.  ·  **[SETUP.md](SETUP.md)** — install, the dev loop, and your first field.

## Provenance

Dream World IX **ships no Final Fantasy IX game data.** It operates only on assets read from a copy of the
game you legally own. Unofficial, fan-made, not affiliated with or endorsed by Square Enix.

## License

[MIT](LICENSE) (© 2026 GameJawnsInc) — the Dream World IX / `ff9mapkit` source. The bundled engine patches
modify [Memoria](https://github.com/Albeoris/Memoria) (MIT, © Albeoris).

---

See **[Known issues](ff9mapkit/docs/KNOWN_ISSUES.md)** and
**[Troubleshooting](ff9mapkit/docs/TROUBLESHOOTING.md)**.
