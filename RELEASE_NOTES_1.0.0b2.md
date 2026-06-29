# Dream World IX 1.0.0b2 — verbatim-fork spatial authoring + engine refresh

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* fields — and
faithfully forking the real ones — for the [Memoria engine](https://github.com/Albeoris/Memoria)
(Steam FF9). Author a whole custom field from a single declarative `field.toml` and compile it into a
drop-in mod — or **fork any of FF9's ~674 real fields** and carry their content faithfully.

> Still an **early public beta**. Engine work is largely in-game proven; the newest gates ship with the
> honesty caveat below. Bug reports and field-authoring questions are welcome.

## What's new since 1.0.0b1

- **Place additive content on a verbatim fork, visually.** An imported verbatim fork now exports its
  spatial markers (NPC/gateway/event) from Blender **without touching the real `.bgi`** — keeping the
  multi-floor walkmesh byte-exact instead of round-tripping it through `.obj` (which strands floors).
- **Spatial editor = name + position only.** The model/dialogue is authored in the `field.toml` (the
  Workspace), joined by name. The Workspace flags a scene-placed NPC/marker that has **no definition**
  ("needs definition" node + one-click **Define**), and a **Refresh (F5)** picks up a Blender re-export
  without re-opening the field. A bare NPC (no model) now lints as a player-clone.
- **Blender add-on 0.9.20.**
- **Refreshed engine bundle (`dwix-custom-memoria-1.0.0b2.zip`)** — the full fork-fidelity set
  **s23–s33** (was s23/s24/s29): scripted-walk positions + overlay occlusion (s30/s31), name-keyed
  control/menu/offset gates (s32), and `fldMapNo`-argument lookups incl. the authorable in-field
  LOCATION name (s33).

## Engine bundle (required for forked fields)

A **novel** field runs on **stock, unmodified Memoria**. A **forked** field needs the fork-fidelity
patches: **download `dwix-custom-memoria-1.0.0b2.zip` from the assets below** and follow
[ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md). Disc-1 gates plus the s30/s31 walk+occlusion and
s33 menu-LOCATION fixes are in-game proven; the late-disc s29 softlock gates, s32, and the s33 sibling
sweeps ship unverified (identity-safe for real fields) and are being playtested as those zones are forked.

## Getting started

- **[FORKING_FF9.md](FORKING_FF9.md)** — a guided GUI walkthrough: fork a slice of FF9, change a line
  of dialogue, and play it back.
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
