# Dream World IX 1.0.0b4 — one-command setup + richer cutscenes

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* fields — and
faithfully forking the real ones — for the [Memoria engine](https://github.com/Albeoris/Memoria)
(Steam FF9). Author a whole custom field from a single declarative `field.toml` and compile it into a
drop-in mod — or **fork any of FF9's ~674 real fields** and carry their content faithfully.

> Still an **early public beta**. Engine work is largely in-game proven; the newest gates ship with the
> honesty caveat below. Bug reports and field-authoring questions are welcome.

## What's new since 1.0.0b3

### One-command onboarding ★
- **`ff9mapkit setup`** does the whole bring-your-own-install step in a single command: it finds your FF9
  install, remembers it in `~/.ff9mapkit.toml`, regenerates the base assets (`extract-templates`), and
  reports the Memoria engine status.
- **The installer runs it for you.** A new user who runs `DreamWorldIX-Setup.exe` with FF9 in a standard
  Steam location ends up **fully set up with zero manual commands** — install, and you're authoring.
- **`ff9mapkit setup --install-engine <dwix-custom-memoria.zip>`** installs the engine bundle (needed only
  for *forked* fields) — it backs up your original DLLs first and is fully reversible. (No `Memoria.ini`
  editing is needed for mod folders: Memoria auto-detects them.)
- **Robustness for installed users:** the toolkit now keeps its generated assets in a per-user folder, so a
  `uv tool upgrade` no longer makes you re-run `extract-templates`.

### Installer hardening
- Fixed a silent failure where the bootstrap could install `uv` but not the toolkit.
- Fixed `os error 448 / untrusted mount point` under Inno Setup 6.7+ (Windows RedirectionGuard vs. uv's
  managed-Python junction).
- The installer's Finished page now shows your next steps.

### Authoring
- **Multi-actor cutscenes** gained **player-walk** (move the controlled character within the conductor) and
  **parallel beats** (`with_prev` — actions that fire together).
- **Active Time Events:** the **forced grey ATE** (unskippable) warp-in is authorable end to end.

## Engine bundle (required for forked fields)

A **novel** field runs on **stock, unmodified Memoria**. A **forked** field needs the fork-fidelity patch
set — **unchanged from 1.0.0b2/b3** (the **s23–s33** suite). Download `dwix-custom-memoria-1.0.0b4.zip` from
the assets below (identical to the prior engine build) and follow
[ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md) — or just run
`ff9mapkit setup --install-engine <that-zip>`. Disc-1 gates plus the s30/s31 walk+occlusion and s33
menu-LOCATION fixes are in-game proven; the late-disc s29 softlock gates, s32, and the s33 sibling sweeps
ship unverified (identity-safe for real fields) and are being playtested as those zones are forked.

## Getting started

- **Easiest (Windows):** run `DreamWorldIX-Setup.exe` from the assets below. No Python needed.
- **Terminal:** `uv tool install ff9mapkit[gui,assets,save]` (or `pip install ff9mapkit[gui,assets,save]`),
  then `ff9mapkit setup`.
- **[FORKING_FF9.md](FORKING_FF9.md)** — a guided GUI walkthrough: fork a slice of FF9, change a line of
  dialogue, and play it back.
- **[SETUP.md](SETUP.md)** — install, prerequisites, the dev loop, and your first field.

## Provenance

Dream World IX **ships no Final Fantasy IX game data.** It operates only on assets read from a copy of the
game you legally own. Unofficial, fan-made, not affiliated with or endorsed by Square Enix.

## License

[MIT](LICENSE) (© 2026 GameJawnsInc) — the Dream World IX / `ff9mapkit` source. The bundled engine patches
modify [Memoria](https://github.com/Albeoris/Memoria) (MIT, © Albeoris).

---

See **[Known issues](ff9mapkit/docs/KNOWN_ISSUES.md)** and
**[Troubleshooting](ff9mapkit/docs/TROUBLESHOOTING.md)**.
