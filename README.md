# Dream World IX

**A toolkit for building brand-new playable *Final Fantasy IX* content — and faithfully forking
the real game — on the [Memoria engine](https://github.com/Albeoris/Memoria) (Steam/GOG FF9).**

The core: author a complete custom **field** — camera, walkmesh, painted background, NPCs,
dialogue, gateways, encounters, events, story branching, cutscenes — from a single declarative
`field.toml`, compiled into a drop-in Memoria mod; or **fork any of FF9's ~674 real fields** with
their content carried faithfully. Around it: custom **3D battle backgrounds** and battle tuning,
multi-field **campaigns** and **journeys** (New Game → a selectable arc of forked game slices),
**items/equipment/shops**, custom **3D character models** (Blender round-trip), **custom playable
characters**, **overworld** authoring (terrain, coastlines, entrances), custom **music/SFX**, and
save/story-state tooling.

> **Public beta.** The engine work is in-game proven; expect rough edges in docs and tooling. Bug
> reports and authoring questions: see [Contributing](CONTRIBUTING.md).

The project is **Dream World IX**; the Python package is **`ff9mapkit`** (`pip install ff9mapkit`,
`import ff9mapkit`).

---

## Start here

- **[SETUP.md](SETUP.md)** — install (installer / PyPI / source), configuration, verification.
- **[Tutorials](ff9mapkit/docs/tutorials/README.md)** — single-goal walkthroughs: first fork,
  original-art field, campaigns, journeys, the GUI, battle maps, custom models.
- **[ff9mapkit/README.md](ff9mapkit/README.md)** — toolkit overview and command families.
- **[FEATURES.md](ff9mapkit/docs/FEATURES.md)** — the full capability list.
- **[Troubleshooting](ff9mapkit/docs/TROUBLESHOOTING.md)** · **[Known issues](ff9mapkit/docs/KNOWN_ISSUES.md)**

### Quickstart

Non-developers: the Windows installer (`DreamWorldIX-Setup.exe`, see
[Releases](https://github.com/GameJawnsInc/Dream-World-IX/releases) and
[installer/](installer/README.md)) installs everything, including the optional engine bundle.
From a terminal:

```powershell
pip install "ff9mapkit[assets]"        # or, from a checkout: cd ff9mapkit; pip install -e ".[assets]"
ff9mapkit setup                        # find the FF9 install, extract base assets, report engine status
ff9mapkit import <field> --out myroom --verbatim    # fork a real field — or `new` for original art
```

Prerequisites (Python 3.11+, a legally-owned Steam or GOG FF9 with Memoria) and the optional
extras are in **[SETUP.md](SETUP.md)**.

## What's in here

| Path | What it is |
|---|---|
| [`ff9mapkit/`](ff9mapkit/) | The Python toolkit (package `ff9mapkit`), its `docs/`, and worked `examples/`. |
| [`apps/`](apps/) | The desktop **Workspace** GUI (PySide6). |
| [`tools/`](tools/) | Repo-checkout dev-loop scripts (test-slot deploy, revert). |
| [`installer/`](installer/) | The Windows `uv`-bootstrap installer. |
| [`memoria-patches/`](memoria-patches/) | Engine patches (see *Engine* below). |
| [`release/`](release/) | A complete kit-authored example mod (build oracle for the test suite). |
| [`SETUP.md`](SETUP.md) | Setup + CLI reference. |

## Engine

A **novel** field (from-scratch art or borrowing a real field's background) runs on a **stock,
unmodified Memoria install** — as do custom battle backgrounds, custom 3D models, and custom
music/SFX. No engine patching required.

A **forked** field also runs on stock Memoria for its *physical* layer (scene, walkmesh, camera,
objects), but FF9 hardcodes some behaviors against the original field's id — narrow-map
letterboxing, after-battle and off-mesh fixes — and those need the bundled engine patch set
(`memoria-patches/`, `s23`–`s34`) for fork fidelity. Overworld mesh authoring (terrain, land
reclaim, coasts, water, entrances) requires the `s34` mesh-override patch. The shipped engine
bundle (`dwix-custom-memoria-*.zip`, installable via `ff9mapkit setup --install-engine`) contains
these patches plus the **F6 debug menu** (`s22`) — an in-game warp/cheat/flag/time tool available
in fields, battles, and on the overworld. Details: **[ENGINE.md](ff9mapkit/docs/ENGINE.md)**.

## Legal & provenance

**Dream World IX is an unofficial, fan-made toolkit. It is not affiliated with, endorsed by, or
sponsored by Square Enix.** FINAL FANTASY IX is a trademark of Square Enix Holdings Co., Ltd.

This project **ships no Final Fantasy IX game data.** It is an authoring tool — like a ROM-hack
patcher, it operates only on assets read from **a copy of the game you legally own**, and it does
not distribute or enable piracy. The base assets it needs are regenerated from *your* install via
`ff9mapkit extract-templates`. See **[DISCLAIMER.md](DISCLAIMER.md)** and
**[Provenance](ff9mapkit/docs/PROVENANCE.md)**.

## License & credits

[MIT](LICENSE) (© 2026 GameJawnsInc) — covers the **Dream World IX / `ff9mapkit` source code
only**. It grants no rights to FINAL FANTASY IX game data, which belongs to Square Enix.

Built on the [Memoria engine](https://github.com/Albeoris/Memoria) (MIT, © Albeoris); the bundled
engine patches modify Memoria — see [`memoria-patches/`](memoria-patches/). Claude Code was used
extensively as a coding agent during development.
