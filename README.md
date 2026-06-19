# Dream World IX

**A toolkit for building brand-new playable *Final Fantasy IX* fields — and faithfully forking
the real ones — for the [Memoria engine](https://github.com/Albeoris/Memoria) (Steam FF9).**

Author a whole custom field — camera, walkmesh, painted background, NPCs, dialogue, gateways,
encounters, events, story branching, cutscenes — from a single declarative `field.toml`, and
compile it into a drop-in mod. Or **fork any of FF9's ~674 real fields** and carry their content
faithfully. Likely the first practical reference for FF9 custom-field authoring.

> **Public beta.** This is an early public release — the engine work is in-game proven, but expect
> rough edges in the docs and tooling. Bug reports and field-authoring questions are welcome (see
> [Contributing](CONTRIBUTING.md)).

The project is **Dream World IX**; the Python toolkit at its heart is the package **`ff9mapkit`**
(that name is unchanged — you `pip install` and `import` it as `ff9mapkit`).

---

## Start here

- **[SETUP.md](SETUP.md)** — install, configure, the dev loop, and your first field. **Read this first.**
- **[ff9mapkit/README.md](ff9mapkit/README.md)** — the toolkit overview and command families.
- **[ff9mapkit/docs/TUTORIAL.md](ff9mapkit/docs/TUTORIAL.md)** — a focused ~10-minute first-field walkthrough.
- **[ff9mapkit/docs/FEATURES.md](ff9mapkit/docs/FEATURES.md)** — the full capability list.
- **[Troubleshooting](ff9mapkit/docs/TROUBLESHOOTING.md)** & **[Known issues](ff9mapkit/docs/KNOWN_ISSUES.md)** — when something breaks or behaves unexpectedly.

### Quickstart

```powershell
cd ff9mapkit                                              # the package directory
pip install -e .
py -m ff9mapkit doctor                                    # verify it found your FF9 install
py -m ff9mapkit import <field> --out myroom --verbatim    # fork a real field — or `new` for original art
```

Full prerequisites (Python 3.11+, owning FF9 on Steam, the one-time `extract-templates`, the optional
GUI/save/dev extras) are in **[SETUP.md](SETUP.md)**.

## What's in here

| Path | What it is |
|---|---|
| [`ff9mapkit/`](ff9mapkit/) | The Python toolkit (package `ff9mapkit`), its `docs/`, and worked `examples/`. |
| [`apps/`](apps/) | The desktop **Workspace** GUI (PySide6). |
| [`tools/`](tools/) | The build/deploy dev-loop scripts. |
| [`memoria-patches/`](memoria-patches/) | Engine patches (see *Engine* below). |
| [`release/`](release/) | The showcase mod (a complete kit-authored field). |
| [`SETUP.md`](SETUP.md) | Setup + quickstart + CLI reference. |

## Engine

A **novel** field (built from scratch or borrowing a real field's background art) runs on a **stock,
unmodified Memoria install** — no engine patching required.

A **forked** field runs on stock Memoria for its *physical* layer (scene, walkmesh, camera, objects),
but a handful of behaviors keyed to the original field's id — narrow-map letterboxing, a few
after-battle / off-mesh fixes — need the small bundled engine patch set (`memoria-patches/`,
`s23`/`s24`/`s29`) for fork fidelity. The showcase opening ships with that custom Memoria build
(disc-1 gates are in-game proven; the newest late-disc gates are still being playtested). See
**[ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md)** for exactly what's stock vs. enhanced.

## Legal & provenance

**Dream World IX is an unofficial, fan-made toolkit. It is not affiliated with, endorsed by, or
sponsored by Square Enix.** FINAL FANTASY IX is a trademark of Square Enix Holdings Co., Ltd.

This project **ships no Final Fantasy IX game data.** It is an authoring tool — like a ROM-hack
patcher, it operates only on assets read from **a copy of the game you legally own**, and it does
not distribute or enable piracy. The base assets it needs are regenerated from *your* install via
`ff9mapkit extract-templates`. See **[DISCLAIMER.md](DISCLAIMER.md)** and the detailed
**[Provenance](ff9mapkit/docs/PROVENANCE.md)** writeup.

## License

[MIT](LICENSE) (© 2026 GameJawnsInc) — covers the **Dream World IX / `ff9mapkit` source code only**.
It grants no rights to FINAL FANTASY IX game data, which belongs to Square Enix. The bundled engine
patches modify [Memoria](https://github.com/Albeoris/Memoria) (MIT, © Albeoris) — see
[`memoria-patches/`](memoria-patches/).

## About

I make games — including an FFIX-inspired RPG of my own — so this started as the tool I wanted while
learning how FF9's fields actually work. The aim was to build a new room the way the game's creators
did: paint a background against a 3D-derived guide, then walk on geometry projected through the same
camera — so authoring a field feels like level design rather than blind byte-hacking. Built on (and
grateful for) the [Memoria engine](https://github.com/Albeoris/Memoria) — none of this is possible
without it.
