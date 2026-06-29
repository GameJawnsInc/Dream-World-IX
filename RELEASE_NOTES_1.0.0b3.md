# Dream World IX 1.0.0b3 — pip-installable, plus SPS effects, cutscenes & chests

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* fields — and
faithfully forking the real ones — for the [Memoria engine](https://github.com/Albeoris/Memoria)
(Steam FF9). Author a whole custom field from a single declarative `field.toml` and compile it into a
drop-in mod — or **fork any of FF9's ~674 real fields** and carry their content faithfully.

> Still an **early public beta**. Engine work is largely in-game proven; the newest gates ship with the
> honesty caveat below. Bug reports and field-authoring questions are welcome.

## What's new since 1.0.0b2

### Easier to install
- **Now on PyPI.** `pip install ff9mapkit` — or `pip install ff9mapkit[gui,assets,save]` for the
  desktop GUI + the fork/import commands + save editing. The headline fork feature is one extra:
  `ff9mapkit[assets]` (pulls UnityPy).
- **One-click Windows installer.** A small `DreamWorldIX-Setup.exe` bootstraps everything via
  [`uv`](https://docs.astral.sh/uv/) — **no system Python required**. Prefer the terminal? The same
  path is `uv tool install ff9mapkit[gui,assets,save]`. The installer redistributes nothing but its own
  code (dependencies are fetched from PyPI on the user's machine), keeping the distribution
  license-clean.
- **`ff9mapkit-workspace`** — the PySide6 Workspace now has a console-less launcher and a Start-Menu
  shortcut.

### New authoring pillars
- **SPS particle-effect authoring — no engine rebuild.** Browse, re-skin, edit, and author field
  particle effects (`[[sps]]` / `[[sps_edit]]`): a round-trip-proven `.sps` codec, curated effect
  templates, walkmesh-auto-grounded placement, a from-scratch creator, and a GUI "Effects" section plus
  an Info Hub browser with previews.
- **Multi-actor cutscenes on verbatim forks.** A director-model **conductor** choreographs several
  actors (animated walk included) inside a faithfully-forked field.
- **More verbatim-fork authoring.** Layer your own content onto a `--verbatim` fork: `[music]` to
  replace a field's BGM, `[[npc]] opens_shop`, `[[npc]]` talk → branch-menu choices, and readable
  props (`dialogue =`).

### Content & tooling
- **Treasure chests (`[[chest]]`)** on both the verbatim and from-scratch paths — real openable, savable
  chests with model variants (F0–F3), flag-by-name, story-gated appearance, and facing.
- **Shared story-flag tiers** — name a flag once and share it across a campaign, or across a whole
  multi-campaign **journey**, with GUI editors and a documented flag-scope hierarchy; the journey-global
  tier now gates members correctly (lint matches build).
- Blender-placed entities surface their `scene.toml` position read-only in the Workspace.

## Engine bundle (required for forked fields)

A **novel** field runs on **stock, unmodified Memoria**. A **forked** field needs the fork-fidelity
patch set — **unchanged from 1.0.0b2** (the **s23–s33** suite). Download
`dwix-custom-memoria-1.0.0b3.zip` from the assets below (identical to the 1.0.0b2 engine build) and
follow [ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md). Disc-1 gates plus the s30/s31
walk+occlusion and s33 menu-LOCATION fixes are in-game proven; the late-disc s29 softlock gates, s32,
and the s33 sibling sweeps ship unverified (identity-safe for real fields) and are being playtested as
those zones are forked.

## Getting started

- **[FORKING_FF9.md](FORKING_FF9.md)** — a guided GUI walkthrough: fork a slice of FF9, change a line of
  dialogue, and play it back.
- **[SETUP.md](SETUP.md)** — install, prerequisites, the dev loop, and your first field.
- **[ff9mapkit/docs/](ff9mapkit/docs/)** — the full toolkit reference.

## Provenance

Dream World IX **ships no Final Fantasy IX game data.** It operates only on assets read from a copy of
the game you legally own. Unofficial, fan-made, not affiliated with or endorsed by Square Enix.

## License

[MIT](LICENSE) (© 2026 GameJawnsInc) — the Dream World IX / `ff9mapkit` source. The bundled engine
patches modify [Memoria](https://github.com/Albeoris/Memoria) (MIT, © Albeoris).

---

See **[Known issues](ff9mapkit/docs/KNOWN_ISSUES.md)** and
**[Troubleshooting](ff9mapkit/docs/TROUBLESHOOTING.md)**.
